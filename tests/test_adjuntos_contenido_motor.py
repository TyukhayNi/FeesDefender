"""Un PDF adjunto se lee con el MISMO motor que uno suelto (`MEJORAS #87`, pieza 3).

La divergencia medida el 2026-08-04, con el mismo PDF entrando por las dos puertas:

| | suelto en Drive (sala de máquina) | adjunto a un correo |
|---|---|---|
| motor | `ocr_pdf_escalera`, **sin tope de páginas** | `extractor._extract_one`: pypdf, y Docling solo si ≤30 pp |
| escaneado de >30 pp | se OCR-iza | **`sin_texto`: cero texto** |
| páginas ciegas bajo sello (`#90`) | se detectan y bajan a la escalera | no se miran |
| etiqueta de calidad | `ocr_quality` + por página | `confianza: alta` si el motor no fue Docling |

La última fila era la peor: un escaneado con pie de LexNET sale por pypdf y se etiqueta
**`confianza: alta`** — la etiqueta miente exactamente en el caso que `#90` costó tres
semanas medir.

El adaptador (`sala_maquina.texto_de_pdf`) vive en la sala de máquina **a propósito**: es
donde ya viven la escalera, el discriminante de página ciega y `ocr_quality`. Meterlo en un
módulo nuevo habría creado una tercera superficie en vez de unificar dos. La convergencia
que queda —que `_ocr_y_extraer` lo use también— es entonces un refactor local dentro de un
solo módulo.

La escalera se dobla en todos los tests: correr OCRmyPDF de verdad los haría lentos y
dependientes de Tesseract. Lo que se comprueba es el ENRUTADO y las etiquetas, que es donde
estaba el defecto; que la escalera funcione ya lo cubren sus propios tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core import sala_maquina as sm
from core.adjuntos_contenido import router
from core.adjuntos_contenido.estado import CONTENIDO_VERSION
from core.anon.ocr import ResultadoEscalera


def _pdf(tmp_path: Path, nombre="anexo.pdf") -> Path:
    p = tmp_path / nombre
    p.write_bytes(b"%PDF-1.4 escaneo")
    return p


@pytest.fixture
def escalera(monkeypatch):
    """Doble de la escalera: registra las llamadas y devuelve lo que se le diga."""
    llamadas: list[dict] = []

    def hacer(*, texto: str, degradado: bool = False, nota: str = "",
              persiste: bool = True):
        def fake(entrada, salida, *, conservador=False, **kw):
            llamadas.append({"entrada": Path(entrada), "conservador": conservador})
            if persiste:
                Path(salida).parent.mkdir(parents=True, exist_ok=True)
                Path(salida).write_bytes(b"%PDF-1.4 buscable")
                ruta = Path(salida)
            else:
                ruta = Path(entrada)
            monkeypatch.setattr(sm, "_try_pypdf", lambda p: texto)
            return ResultadoEscalera(ruta=ruta, peldano="redo",
                                     degradado=degradado, nota=nota)
        monkeypatch.setattr(sm, "ocr_pdf_escalera", fake)
        return llamadas
    return hacer


# ---------------------------------------------------------------------------
# El adaptador
# ---------------------------------------------------------------------------

def test_un_escaneado_largo_ya_no_devuelve_cero_texto(tmp_path, monkeypatch, escalera):
    """El agujero de >30 páginas, que en el camino de adjuntos daba `sin_texto`."""
    pdf = _pdf(tmp_path)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")        # escaneado: sin capa
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 48)  # >30
    monkeypatch.setattr(sm, "_paginas_ciegas", lambda p: [])
    escalera(texto="CUENTAS ANUALES " * 200)

    r = sm.texto_de_pdf(pdf)

    assert r.metodo == "ocr" and r.ocr is True
    assert r.estado == "ok"
    assert "CUENTAS ANUALES" in r.texto


def test_un_pdf_digital_limpio_no_paga_ocr(tmp_path, monkeypatch):
    """Lo que NO hay que romper: el caso mayoritario sigue saliendo por pypdf."""
    pdf = _pdf(tmp_path)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "CONTRATO DE ARRENDAMIENTO " * 40)
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 3)
    monkeypatch.setattr(sm, "_paginas_ciegas", lambda p: [])

    def prohibido(*a, **k):
        raise AssertionError("un PDF digital limpio no debe pasar por la escalera")

    monkeypatch.setattr(sm, "ocr_pdf_escalera", prohibido)

    r = sm.texto_de_pdf(pdf)

    assert (r.metodo, r.ocr, r.estado) == ("pypdf", False, "ok")


def test_el_sello_de_lexnet_baja_a_la_escalera_en_modo_conservador(
        tmp_path, monkeypatch, escalera):
    """`#90`: trae capa de texto (el pie de firma) y esconde páginas ciegas.

    El modo conservador es lo que no reescribe las páginas digitales.
    """
    pdf = _pdf(tmp_path)
    # ~250 char/pág: la densidad REAL del pie de firma de LexNET medida en `#90` era
    # ~228, contra un umbral de 40. Por eso el documento pasa el gate de «digital» con el
    # cuerpo perdido, y por eso el discriminante tiene que ser la página ciega y no la
    # densidad. Con menos densidad este test pasaría por la rama de escaneado y no
    # probaría el modo conservador, que es lo que dice probar.
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "Firmado electrónicamente " * 250)
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 25)
    monkeypatch.setattr(sm, "_paginas_ciegas", lambda p: [3, 4, 5])
    llamadas = escalera(texto="BALANCE Y CUENTA DE PERDIDAS Y GANANCIAS " * 100)

    r = sm.texto_de_pdf(pdf)

    assert llamadas and llamadas[0]["conservador"] is True
    assert r.metodo == "ocr"
    assert "BALANCE" in r.texto


def test_la_escalera_degradada_nunca_sale_ok(tmp_path, monkeypatch, escalera):
    """Contrato de `ResultadoEscalera.degradado`: queda texto ciego sin recuperar."""
    pdf = _pdf(tmp_path)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 10)
    monkeypatch.setattr(sm, "_paginas_ciegas", lambda p: [2])
    escalera(texto="TEXTO ABUNDANTE Y LEGIBLE " * 100, degradado=True,
             nota="quedan 2 páginas ciegas")

    r = sm.texto_de_pdf(pdf)

    assert r.estado == "low", "degradado + ok es justo el silencio de #90"
    assert "ciegas" in r.nota


def test_si_el_ocr_falla_se_conserva_lo_que_hubiera_y_se_dice(tmp_path, monkeypatch):
    """Un PDF cifrado o corrupto: no se pierde el residuo, y el motivo viaja."""
    pdf = _pdf(tmp_path)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "Sello de registro")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 12)
    monkeypatch.setattr(sm, "_paginas_ciegas", lambda p: [1])

    def boom(*a, **k):
        raise RuntimeError("PDF cifrado")

    monkeypatch.setattr(sm, "ocr_pdf_escalera", boom)

    r = sm.texto_de_pdf(pdf)

    assert r.ocr is False
    assert "PDF cifrado" in r.nota
    assert r.texto == "Sello de registro"      # no se tira el residuo


# ---------------------------------------------------------------------------
# El router de adjuntos
# ---------------------------------------------------------------------------

def test_el_adjunto_pdf_pasa_por_el_motor_de_la_sala_de_maquina(
        tmp_path, monkeypatch, escalera):
    pdf = _pdf(tmp_path)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 48)
    monkeypatch.setattr(sm, "_paginas_ciegas", lambda p: [])
    escalera(texto="ANEXO DOCUMENTAL " * 200)

    def prohibido(*a, **k):
        raise AssertionError("un PDF ya no baja por extractor._extract_one")

    monkeypatch.setattr(router, "_extract_one", prohibido)

    ext = router.extraer(pdf, "application/pdf")

    assert ext.ok and ext.metodo == "ocr"
    assert ext.confianza == "alta"
    assert ext.ocr is True


def test_la_confianza_sale_de_la_calidad_no_del_nombre_del_motor(
        tmp_path, monkeypatch, escalera):
    """El defecto de etiqueta: `alta` porque «no fue Docling», con el cuerpo perdido."""
    pdf = _pdf(tmp_path)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 30)
    monkeypatch.setattr(sm, "_paginas_ciegas", lambda p: [4])
    escalera(texto="TEXTO RECUPERADO PARCIAL " * 80, degradado=True,
             nota="quedan páginas ciegas")

    ext = router.extraer(pdf, "application/pdf")

    assert ext.confianza == "por-verificar", (
        "un documento con texto ciego sin recuperar no puede etiquetarse `alta`")
    assert "ciegas" in ext.motivo


def test_un_pdf_sin_texto_recuperable_lo_declara_con_su_motivo(tmp_path, monkeypatch,
                                                              escalera):
    pdf = _pdf(tmp_path)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 8)
    monkeypatch.setattr(sm, "_paginas_ciegas", lambda p: [])
    escalera(texto="", nota="ningún peldaño recuperó texto")

    ext = router.extraer(pdf, "application/pdf")

    assert (ext.ok, ext.metodo) == (False, "sin_texto")
    assert "ningún peldaño" in ext.motivo


def test_los_tipos_que_la_escalera_no_cubre_siguen_con_el_extractor(tmp_path, monkeypatch):
    """Docling sigue siendo el primario de `.docx`/`.pptx`/`.html`.

    Retirarlo por «unificar» dejaría formatos sin cobertura — lo advertía `#87`.
    """
    docx = tmp_path / "escrito.docx"
    docx.write_bytes(b"PK\x03\x04 fake")
    monkeypatch.setattr(router, "_extract_one", lambda p: ("CONTESTACIÓN A LA DEMANDA", "docling"))

    ext = router.extraer(docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    assert ext.metodo == "docling"
    assert ext.confianza == "por-verificar"
    assert ext.ocr is False


def test_la_version_del_cache_subio(tmp_path):
    """Sin bump, los adjuntos ya procesados conservarían el texto del motor viejo."""
    assert CONTENIDO_VERSION >= 2
