"""Tests del módulo separar + renombrar + OCR + imagen_a_pdf — Fase 2.

Tests sin dependencia de PDF reales: validan las funciones puras de
detección (``detectar_tipo``), las constantes de configuración (tipos
super-absorbentes, agrupables), el comportamiento idempotente de
``renombrar_carpeta`` y la disponibilidad opcional de OCR.

Para tests con PDFs reales (separar_pdf_pipeline end-to-end), usar
``test_anon_integration.py`` que se introduce en Fase 3.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pytest

from core.anon import (
    imagen_a_pdf,
    ocr_disponible,
    ocr_pdf,
    renombrar_carpeta,
    separar_pdf_pipeline,
)
from core.anon.exceptions import PDFVacioError
from core.anon.separar import (
    MAX_PAGINAS_SIN_MARCADOR,
    PATRON_NUM_DOC,
    TIPOS_AGRUPABLES,
    TIPOS_ABSORBE_SIN_NUMERO,
    TIPOS_DOCUMENTO,
    TIPOS_SUPER_ABSORBENTES,
    detectar_segmentos,
    detectar_tipo,
    separar_pdf,
)

# Genera y procesa PDFs reales (core/anon). Lento; solo con --runslow.
pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Helpers para construir PDFs de prueba con capa de texto real
# ---------------------------------------------------------------------------

_LOG_MUDO = logging.getLogger("test_separar")
_LOG_MUDO.addHandler(logging.NullHandler())


def _build_pdf(path: Path, pages: list[list[str]]) -> Path:
    """Construye un PDF con una página por sublista; cada string es una línea.

    Usa fpdf2 (dependencia ya presente) para generar una capa de texto real
    que pdfminer puede extraer, sin necesidad de fixtures binarios.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    for lineas in pages:
        pdf.add_page()
        pdf.set_font("helvetica", size=14)
        y = 20
        for ln in lineas:
            pdf.set_xy(15, y)
            pdf.cell(0, 8, ln)
            y += 12
    pdf.output(str(path))
    return path


def _build_pdf_vacio(path: Path) -> Path:
    """Construye un PDF válido pero de 0 páginas."""
    from pypdf import PdfWriter

    with open(path, "wb") as f:
        PdfWriter().write(f)
    return path


def _origen_no_bloqueado(path: Path) -> bool:
    """True si el PDF de origen puede renombrarse (no hay handle abierto).

    En Windows, un PDF con un handle de fichero abierto no se puede renombrar
    ni borrar: ésta es exactamente la operación que un paso posterior del
    pipeline (mover/sobrescribir el origen) haría y que fallaba con
    PermissionError cuando se filtraba un handle.
    """
    tmp = path.with_suffix(path.suffix + ".movecheck")
    try:
        path.replace(tmp)
        tmp.replace(path)
        return True
    except PermissionError:
        return False
from core.anon.renombrar import (
    mejor_fecha,
    quitar_sufijo_anonimizado,
    tiene_prefijo_fecha,
)


# ---------------------------------------------------------------------------
# Detección de tipo documental
# ---------------------------------------------------------------------------

class TestDetectarTipo:
    """Cada portada de tipo se identifica correctamente desde sus líneas."""

    def test_demanda_por_encabezamiento(self) -> None:
        lineas = [
            "AL JUZGADO DE PRIMERA INSTANCIA Nº 15 DE BARCELONA",
            "DEMANDA DE JUICIO ORDINARIO",
            "PROCURADORA: Dña. María López García",
        ]
        tipo, prio, num = detectar_tipo(lineas)
        assert tipo == "DEMANDA"
        assert prio >= 9
        assert num is None

    def test_sentencia_por_cabecera_oficial(self) -> None:
        lineas = [
            "SENTENCIA Nº 234/2025",
            "EN NOMBRE DEL REY",
            "Magistrado: Ilmo. Sr. D. José Pérez",
        ]
        tipo, prio, num = detectar_tipo(lineas)
        assert tipo == "SENTENCIA"

    def test_doc_factura_con_numero_explicito(self) -> None:
        lineas = ["DOC 5", "FACTURA"]
        tipo, prio, num = detectar_tipo(lineas)
        assert tipo == "DOC_FACTURA"
        assert num == 5

    def test_auto_solo_si_es_cabecera(self) -> None:
        # "los autos" en texto corrido NO debe disparar AUTO
        lineas = [
            "Que vistos los presentes autos por el Magistrado",
            "se procede a dictar la siguiente resolución",
        ]
        tipo, prio, num = detectar_tipo(lineas)
        assert tipo != "AUTO"

    def test_pagina_sin_marcadores(self) -> None:
        lineas = [
            "El presente escrito se refiere a la cuestión",
            "que ya quedó planteada en los antecedentes.",
        ]
        tipo, prio, num = detectar_tipo(lineas)
        assert tipo is None
        assert num is None

    def test_lineas_vacias(self) -> None:
        assert detectar_tipo([]) == (None, 0, None)

    def test_detectar_tipo_tipos_extra_none_identico(self) -> None:
        # Con tipos_extra=None debe dar EXACTAMENTE lo mismo que sin el argumento.
        lineas = ["CÉDULA DE EMPLAZAMIENTO", "Juzgado de Instancia"]
        assert detectar_tipo(lineas) == detectar_tipo(lineas, tipos_extra=None)

    def test_detectar_tipo_inyecta_marcador_ev(self) -> None:
        extra = [{"tipo": "DOC_PBC", "prioridad": 7,
                  "marcadores": ["PREVENCION DE BLANQUEO", "PREVENCIÓN DE BLANQUEO"],
                  "exige_inicio": True}]
        lineas = ["PREVENCIÓN DE BLANQUEO DE CAPITALES"]
        tipo, prio, _ = detectar_tipo(lineas, tipos_extra=extra)
        assert tipo == "DOC_PBC"
        # Sin inyección, ese marcador no existe → no lo clasifica como PBC
        assert detectar_tipo(lineas)[0] != "DOC_PBC"


# ---------------------------------------------------------------------------
# Constantes de la lógica DEMANDA super-absorbente
# ---------------------------------------------------------------------------

class TestConstantesAbsorcion:
    def test_super_absorbentes_incluyen_demanda(self) -> None:
        # Clave: la demanda absorbe menciones a contrato/factura sin num_doc
        assert "DEMANDA" in TIPOS_SUPER_ABSORBENTES
        assert "SENTENCIA" in TIPOS_SUPER_ABSORBENTES

    def test_doc_contrato_en_absorbe_sin_numero(self) -> None:
        assert "DOC_CONTRATO" in TIPOS_ABSORBE_SIN_NUMERO
        assert "DOC_FACTURA" in TIPOS_ABSORBE_SIN_NUMERO

    def test_extracto_bancario_es_agrupable(self) -> None:
        # Una tarjeta puede tener 50 páginas — un solo segmento
        assert "DOC_EXTRACTO_BANCARIO" in TIPOS_AGRUPABLES

    def test_max_paginas_sin_marcador_calibrado(self) -> None:
        # El threshold es 60 según el original — verificar que no se cambia
        # accidentalmente al refactorizar
        assert MAX_PAGINAS_SIN_MARCADOR == 60

    def test_tipos_documento_completos(self) -> None:
        # El catálogo del original tiene 16 tipos
        tipos = {d["tipo"] for d in TIPOS_DOCUMENTO}
        for esperado in [
            "DEMANDA", "CONTESTACION", "OPOSICION",
            "SENTENCIA", "AUTO", "DECRETO", "CEDULA_EMPLAZAMIENTO",
            "DOC_PODER_NOTARIAL", "DOC_CONTRATO", "DOC_FACTURA",
        ]:
            assert esperado in tipos


# ---------------------------------------------------------------------------
# Patrón de número de documento
# ---------------------------------------------------------------------------

class TestPatronNumDoc:
    @pytest.mark.parametrize("texto, esperado", [
        ("DOC 5", 5),
        ("DOC. 12", 12),
        ("Documento nº 3", 3),
        ("DOC N. 7", 7),
        ("documento 22", 22),
    ])
    def test_extrae_numero(self, texto, esperado) -> None:
        m = PATRON_NUM_DOC.search(texto)
        assert m is not None
        assert int(m.group(1)) == esperado

    def test_no_matchea_texto_corrido(self) -> None:
        # "documentos" en plural NO debe matchear con un número detrás
        assert PATRON_NUM_DOC.search("varios documentos importantes") is None


# ---------------------------------------------------------------------------
# Renombrar — estructura plana FeesDefender
# ---------------------------------------------------------------------------

class TestRenombrarCarpeta:
    def test_aplica_prefijo_fecha(self, tmp_path: Path) -> None:
        # Documento con fecha clara en el cuerpo
        md = tmp_path / "demanda.md"
        md.write_text(
            "Documento presentado el 14 de marzo de 2024 ante el juzgado.",
            encoding="utf-8",
        )

        renombrados = renombrar_carpeta(tmp_path, log=lambda *a: None)
        assert len(renombrados) == 1
        origen, destino = renombrados[0]
        assert destino.name == "20240314 - demanda.md"
        assert destino.exists()
        assert not md.exists()  # el original ya no está

    def test_idempotente_segunda_pasada(self, tmp_path: Path) -> None:
        md = tmp_path / "20240101 - escrito.md"
        md.write_text("contenido", encoding="utf-8")

        renombrados = renombrar_carpeta(tmp_path, log=lambda *a: None)
        # No se renombra: ya tiene prefijo
        assert renombrados == []
        assert md.exists()

    def test_quita_sufijo_anonimizado(self, tmp_path: Path) -> None:
        md = tmp_path / "auto_anonimizado.md"
        md.write_text(
            "Auto de fecha 5 de febrero de 2023 dictado en Barcelona.",
            encoding="utf-8",
        )

        renombrados = renombrar_carpeta(tmp_path, log=lambda *a: None)
        assert len(renombrados) == 1
        _, destino = renombrados[0]
        assert "_anonimizado" not in destino.name
        assert destino.name == "20230205 - auto.md"

    def test_ignora_archivos_auxiliares(self, tmp_path: Path) -> None:
        # Ficheros que empiezan por _ son auxiliares (índices, mapas)
        (tmp_path / "_mapa_caso.json").write_text("{}", encoding="utf-8")
        (tmp_path / "_pipeline_log.md").write_text(
            "Procesado el 14 de marzo de 2024.", encoding="utf-8"
        )

        renombrados = renombrar_carpeta(tmp_path, log=lambda *a: None)
        # Ninguno se renombra
        assert renombrados == []
        assert (tmp_path / "_mapa_caso.json").exists()
        assert (tmp_path / "_pipeline_log.md").exists()

    def test_renombra_mapa_json_asociado(self, tmp_path: Path) -> None:
        md = tmp_path / "demanda_anonimizado.md"
        md.write_text(
            "Demanda de fecha 14 de marzo de 2024.", encoding="utf-8"
        )
        mapa = tmp_path / "demanda_mapa.json"
        mapa.write_text('{"mapa": {}}', encoding="utf-8")

        renombrar_carpeta(tmp_path, log=lambda *a: None)
        # El _mapa.json sigue al .md renombrado
        assert (tmp_path / "20240314 - demanda.md").exists()
        assert (tmp_path / "20240314 - demanda_mapa.json").exists()
        assert not mapa.exists()


# ---------------------------------------------------------------------------
# mejor_fecha — umbral parametrizable
# ---------------------------------------------------------------------------

class TestMejorFecha:
    def test_umbral_por_defecto_descarta_fechas_recientes(self) -> None:
        # 1 día atrás: dentro del umbral default (30 días) → descartado
        hoy = date(2026, 5, 7)
        ayer_str = "6 de mayo de 2026"
        texto = f"Resolución dictada el {ayer_str}."
        resultado = mejor_fecha(texto, hoy=hoy)
        assert resultado is None

    def test_umbral_personalizado_admite_fechas_recientes(self) -> None:
        # Mismo input, umbral 0 → SÍ admite fechas hasta hoy
        hoy = date(2026, 5, 7)
        ayer_str = "6 de mayo de 2026"
        texto = f"Resolución dictada el {ayer_str}."
        resultado = mejor_fecha(texto, hoy=hoy, dias_umbral=0)
        assert resultado is not None
        assert resultado[0] == date(2026, 5, 6)

    def test_fecha_antigua_siempre_admitida(self) -> None:
        hoy = date(2026, 5, 7)
        texto = "Sentencia de 14 de marzo de 2024."
        resultado = mejor_fecha(texto, hoy=hoy)
        assert resultado is not None
        assert resultado[0] == date(2024, 3, 14)


# ---------------------------------------------------------------------------
# Helpers de stem
# ---------------------------------------------------------------------------

class TestQuitarSufijoYPrefijo:
    def test_quitar_sufijo_anonimizado(self) -> None:
        assert quitar_sufijo_anonimizado("demanda_anonimizado") == "demanda"
        assert quitar_sufijo_anonimizado("demanda") == "demanda"

    def test_tiene_prefijo_fecha(self) -> None:
        assert tiene_prefijo_fecha("20240314 - demanda")
        assert tiene_prefijo_fecha("20240314- demanda")  # sin espacio
        assert not tiene_prefijo_fecha("demanda")
        assert not tiene_prefijo_fecha("demanda 2024")


# ---------------------------------------------------------------------------
# OCR — disponibilidad
# ---------------------------------------------------------------------------

class TestOCRDisponible:
    def test_funcion_existe_y_devuelve_bool(self) -> None:
        # No requerimos que ocrmypdf esté instalado en CI: solo que el
        # detector funcione. En la máquina del despacho devolverá True.
        result = ocr_disponible()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# imagen_a_pdf — exportación correcta
# ---------------------------------------------------------------------------

class TestImagenAPdfExport:
    def test_funcion_es_callable(self) -> None:
        # La fachada __init__ exporta `imagen_a_pdf` (alias de `convertir`)
        assert callable(imagen_a_pdf)


# ---------------------------------------------------------------------------
# separar_pdf_pipeline — exportación correcta
# ---------------------------------------------------------------------------

class TestSepararPipelineExport:
    def test_funcion_es_callable(self) -> None:
        assert callable(separar_pdf_pipeline)


# ---------------------------------------------------------------------------
# OCR — wrapper se importa sin ocrmypdf instalado
# ---------------------------------------------------------------------------

class TestOcrPdfImport:
    def test_funcion_es_callable(self) -> None:
        assert callable(ocr_pdf)


# ---------------------------------------------------------------------------
# Pipeline end-to-end sobre PDFs reales generados al vuelo (Fixes de revisión)
# ---------------------------------------------------------------------------

class TestSepararPipelineHappyPath:
    def test_genera_pdfs_e_indice(self, tmp_path: Path) -> None:
        src = _build_pdf(tmp_path / "exp.pdf", [
            ["CEDULA DE EMPLAZAMIENTO", "Juzgado de Primera Instancia"],
            ["DOC 1", "FACTURA"],
        ])
        out = tmp_path / "salida"

        resultados = separar_pdf_pipeline(src, out, log=_LOG_MUDO)

        # Dos documentos detectados, cada uno su PDF + el índice
        assert len(resultados) == 2
        tipos = {r["tipo"] for r in resultados}
        assert tipos == {"CEDULA_EMPLAZAMIENTO", "DOC_FACTURA"}
        pdfs = sorted(out.glob("*.pdf"))
        assert len(pdfs) == 2
        assert (out / "indice.json").exists()
        assert (out / "indice.txt").exists()
        # No debe quedar ningún temporal de la escritura atómica
        assert list(out.glob("*.tmp")) == []
        # Rangos de página correctos (1 página cada uno)
        assert all(r["n_paginas"] == 1 for r in resultados)

    def test_documento_unico_sin_marcadores(self, tmp_path: Path) -> None:
        # PDF de texto corrido sin ninguna portada → documento único
        src = _build_pdf(tmp_path / "plano.pdf", [
            ["texto corrido sin ninguna portada reconocible"],
            ["segunda pagina igualmente neutra de contenido"],
        ])
        out = tmp_path / "salida"
        resultados = separar_pdf_pipeline(src, out, log=_LOG_MUDO)
        assert len(resultados) == 1
        assert resultados[0]["tipo"] == "DOCUMENTO"
        assert resultados[0]["n_paginas"] == 2


class TestNoFugaDeHandles:
    """El origen no queda bloqueado tras el análisis (Windows PermissionError)."""

    def test_origen_liberado_tras_pipeline(self, tmp_path: Path) -> None:
        src = _build_pdf(tmp_path / "exp.pdf", [
            ["DEMANDA DE JUICIO ORDINARIO", "AL JUZGADO DE PRIMERA INSTANCIA"],
            ["Hechos y fundamentos de la demanda"],
        ])
        separar_pdf_pipeline(src, tmp_path / "salida", log=_LOG_MUDO)
        assert _origen_no_bloqueado(src)

    def test_origen_liberado_si_falla_el_analisis(self, tmp_path: Path, monkeypatch) -> None:
        # Simula una excepción a mitad del bucle de extract_pages: el generador
        # de pdfminer mantiene el PDF abierto y, sin closing(), el origen
        # quedaría bloqueado en Windows.
        src = _build_pdf(tmp_path / "exp.pdf", [
            ["CEDULA DE EMPLAZAMIENTO"],
            ["DOC 1", "FACTURA"],
            ["DOC 2", "FACTURA"],
        ])

        llamadas = {"n": 0}
        real = detectar_segmentos.__globals__["extraer_primeras_lineas"]

        def _explota(pagina, n=5):
            llamadas["n"] += 1
            if llamadas["n"] == 2:
                raise RuntimeError("fallo simulado a mitad del análisis")
            return real(pagina, n)

        monkeypatch.setattr(
            "core.anon.separar.extraer_primeras_lineas", _explota
        )

        with pytest.raises(RuntimeError):
            detectar_segmentos(src, _LOG_MUDO)

        assert _origen_no_bloqueado(src)


class TestPDFVacio:
    """Un PDF de 0 páginas no debe emitir un documento vacío."""

    def test_pipeline_pdf_cero_paginas(self, tmp_path: Path) -> None:
        src = _build_pdf_vacio(tmp_path / "vacio.pdf")
        out = tmp_path / "salida"

        with pytest.raises(PDFVacioError):
            separar_pdf_pipeline(src, out, log=_LOG_MUDO)

        # No se generó ningún PDF ni índice fantasma '1-0'
        assert list(out.glob("*.pdf")) == []
        assert not (out / "indice.json").exists()

    def test_separar_pdf_segmento_sin_paginas(self, tmp_path: Path) -> None:
        # Segmento degenerado (pagina_fin < pagina_inicio) sobre un PDF real
        src = _build_pdf(tmp_path / "exp.pdf", [["FACTURA", "DOC 1"]])
        out = tmp_path / "salida"
        out.mkdir()
        seg_malo = [{
            "tipo": "DOCUMENTO", "num_doc": 1,
            "pagina_inicio": 1, "pagina_fin": 0, "lineas_inicio": [],
        }]
        with pytest.raises(PDFVacioError):
            separar_pdf(src, seg_malo, out, _LOG_MUDO)
        assert list(out.glob("*.pdf")) == []


class TestEscrituraAtomica:
    """Si writer.write falla a mitad, no quedan PDFs truncados ni índice."""

    def test_limpieza_si_falla_a_mitad(self, tmp_path: Path, monkeypatch) -> None:
        src = _build_pdf(tmp_path / "exp.pdf", [
            ["CEDULA DE EMPLAZAMIENTO"],
            ["DOC 1", "FACTURA"],
        ])
        out = tmp_path / "salida"

        from pypdf import PdfWriter

        write_real = PdfWriter.write
        estado = {"n": 0}

        def _write_falla(self, stream):
            estado["n"] += 1
            if estado["n"] == 2:
                raise OSError("disco lleno simulado")
            return write_real(self, stream)

        monkeypatch.setattr(PdfWriter, "write", _write_falla)

        with pytest.raises(OSError):
            separar_pdf_pipeline(src, out, log=_LOG_MUDO)

        # El primer PDF promovido se limpió; no hay temporales ni índice
        assert list(out.glob("*.pdf")) == []
        assert list(out.glob("*.tmp")) == []
        assert not (out / "indice.json").exists()


class TestHelperLineasCompartido:
    """El helper de reconstrucción de líneas se comparte entre los dos módulos."""

    def test_separar_y_anonimizar_usan_pdf_lineas(self) -> None:
        import core.anon.pdf_lineas as pl

        assert callable(pl.recoger_chars)
        assert callable(pl.agrupar_en_lineas)

    def test_agrupar_en_lineas_reconstruye_portada(self, tmp_path: Path) -> None:
        from pdfminer.high_level import extract_pages

        from core.anon.pdf_lineas import agrupar_en_lineas, recoger_chars

        src = _build_pdf(tmp_path / "x.pdf", [
            ["CEDULA DE EMPLAZAMIENTO", "Segunda linea de la portada"],
        ])
        pagina = next(extract_pages(str(src)))
        chars: list = []
        recoger_chars(pagina, chars)
        lineas = [t for _y, t in agrupar_en_lineas(chars)]

        assert lineas[0] == "CEDULA DE EMPLAZAMIENTO"
        assert "Segunda linea de la portada" in lineas


def test_detectar_segmentos_acepta_tipos_extra(tmp_path: Path) -> None:
    """``tipos_extra`` se propaga a ``detectar_tipo`` (Task 2) para permitir
    marcadores adicionales (p.ej. E&V) sin tocar el catálogo congelado."""
    from tests._pdf_fixtures import build_pdf

    pdf = build_pdf(tmp_path / "x.pdf", [["ACTIVACION DEL ENCARGO", "cuerpo"]])
    extra = [{"tipo": "DOC_ACTIVACION", "prioridad": 7,
              "marcadores": ["ACTIVACION DEL ENCARGO", "ACTIVACIÓN DEL ENCARGO"],
              "exige_inicio": True}]
    segs = detectar_segmentos(pdf, _LOG_MUDO, tipos_extra=extra)
    assert any(s["tipo"] == "DOC_ACTIVACION" for s in segs)
