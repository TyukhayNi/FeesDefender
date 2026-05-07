"""Tests del módulo separar + renombrar + OCR + imagen_a_pdf — Fase 2.

Tests sin dependencia de PDF reales: validan las funciones puras de
detección (``detectar_tipo``), las constantes de configuración (tipos
super-absorbentes, agrupables), el comportamiento idempotente de
``renombrar_carpeta`` y la disponibilidad opcional de OCR.

Para tests con PDFs reales (separar_pdf_pipeline end-to-end), usar
``test_anon_integration.py`` que se introduce en Fase 3.
"""

from __future__ import annotations

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
from core.anon.separar import (
    MAX_PAGINAS_SIN_MARCADOR,
    PATRON_NUM_DOC,
    TIPOS_AGRUPABLES,
    TIPOS_ABSORBE_SIN_NUMERO,
    TIPOS_DOCUMENTO,
    TIPOS_SUPER_ABSORBENTES,
    detectar_tipo,
)
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
