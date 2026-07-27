"""Cableado de la escalera de OCR en la Sala de máquina (MEJORAS #90, (a)).

Tres cosas que antes no pasaban:

1. El camino OCR usa la **escalera**, no `ocr_pdf` a pelo con `--skip-text`.
2. Un PDF que pasa el gate de «ya es digital» pero esconde páginas ciegas baja
   igualmente a la escalera, en modo **conservador** (peldaño 2: no reescribe el
   texto de las páginas digitales). Sin esto la escalera sería inalcanzable justo
   para la patología que la motivó: un escaneo con pie de firma de LexNET supera
   `_texto_suficiente` (~228 char/pág frente a un umbral de 40) y nunca llegaba
   a OCRmyPDF.
3. Si la escalera se degrada, el documento sale `low` — **nunca `ok`**.
"""
from pathlib import Path

import pytest

from core import sala_maquina as sm
from core.anon.ocr import ResultadoEscalera
from core.utils import file_sha256

_DENSO = "Estipulacion cuarta sobre honorarios de intermediacion inmobiliaria pactados. "
_SELLO = "Firmado electronicamente por LexNET"


def _imagen(ancho: int, alto: int):
    from PIL import Image
    return Image.new("RGB", (ancho, alto), (205, 205, 205))


def _pdf(path: Path, paginas: list[tuple[str, tuple[int, int] | None]]) -> Path:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path))
    for texto, raster in paginas:
        if raster is not None:
            c.drawImage(ImageReader(_imagen(*raster)), 0, 0, width=595, height=842)
        if texto:
            c.drawString(40, 800, texto[:180])
        c.showPage()
    c.save()
    return path


def _caso(tmp_path: Path, nombre: str, paginas) -> tuple[Path, sm.DocPlan]:
    case = tmp_path / "EV-2026-001"
    src = _pdf(case / "00_Input" / "01_Drive EV" / nombre, paginas)
    sha = file_sha256(src)
    return case, sm.DocPlan(rel_path=f"01_Drive EV/{nombre}", sha256=sha, ext=".pdf",
                            ruta="pdf", slug=f"{src.stem}__{sha[:8]}")


def test_el_camino_ocr_invoca_la_escalera(tmp_path, monkeypatch):
    case, d = _caso(tmp_path, "escaneado.pdf", [("", (1200, 1600))])
    visto = {}

    def _fake(entrada, salida, **kw):
        visto["conservador"] = kw.get("conservador", False)
        _pdf(Path(salida), [(_DENSO * 3, (1200, 1600))])
        return ResultadoEscalera(Path(salida), "redo")

    monkeypatch.setattr(sm, "ocr_pdf_escalera", _fake)

    cob = sm.ejecutar(case, [d], case_id="EV-2026-001")

    assert visto["conservador"] is False        # escaneado: se permite el peldaño 1
    assert cob[0].metodo == "ocr" and cob[0].ocr is True


def test_un_documento_degradado_nunca_sale_ok(tmp_path, monkeypatch):
    """La escalera recuperó una página y perdió otra: queda texto ciego. Que el
    promedio del resto lo tape es exactamente el fallo que #90 describe."""
    case, d = _caso(tmp_path, "cuentas.pdf", [("", (1200, 1600)), ("", (1200, 1600))])

    def _fake(entrada, salida, **kw):
        _pdf(Path(salida), [(_DENSO * 3, (1200, 1600)), (_DENSO * 3, (1200, 1600))])
        return ResultadoEscalera(Path(salida), "paginas", paginas_ocr=(1,),
                                 paginas_fallidas=(2,), degradado=True,
                                 nota="texto ciego NO recuperado en 1 página(s)")

    monkeypatch.setattr(sm, "ocr_pdf_escalera", _fake)

    cob = sm.ejecutar(case, [d], case_id="EV-2026-001")

    assert cob[0].estado == "low"
    assert "ciego" in cob[0].nota


def test_la_nota_deja_traza_del_peldano_usado(tmp_path, monkeypatch):
    case, d = _caso(tmp_path, "tasacion.pdf", [("", (1200, 1600))])

    def _fake(entrada, salida, **kw):
        _pdf(Path(salida), [(_DENSO * 3, (1200, 1600))])
        return ResultadoEscalera(Path(salida), "paginas", paginas_ocr=(1,),
                                 nota="peldaño 2: 1 página(s) ciega(s) re-OCR-izadas aparte")

    monkeypatch.setattr(sm, "ocr_pdf_escalera", _fake)

    cob = sm.ejecutar(case, [d], case_id="EV-2026-001")

    assert cob[0].estado == "ok"
    assert "peldaño 2" in cob[0].nota


def test_pdf_digital_con_paginas_ciegas_baja_a_la_escalera_conservadora(tmp_path, monkeypatch):
    # Portada digital densa + 3 páginas escaneadas con solo el pie de firma:
    # `_texto_suficiente` dice "digital" y hasta ahora se iba por pypdf.
    case, d = _caso(tmp_path, "cuentas_anuales.pdf",
                    [(_DENSO * 3, None)] + [(_SELLO, (1200, 1600))] * 3)
    visto = {}

    def _fake(entrada, salida, **kw):
        visto["conservador"] = kw.get("conservador")
        _pdf(Path(salida), [(_DENSO * 3, None)] + [(_DENSO * 3, (1200, 1600))] * 3)
        return ResultadoEscalera(Path(salida), "paginas", paginas_ocr=(2, 3, 4))

    monkeypatch.setattr(sm, "ocr_pdf_escalera", _fake)

    cob = sm.ejecutar(case, [d], case_id="EV-2026-001")

    assert visto["conservador"] is True         # capa de texto real: no reescribirla
    assert cob[0].metodo == "ocr" and cob[0].estado == "ok"


def test_pdf_digital_limpio_sigue_yendo_por_pypdf_sin_ocr(tmp_path, monkeypatch):
    case, d = _caso(tmp_path, "encargo.pdf", [(_DENSO * 3, None), (_DENSO * 3, None)])

    def _boom(*a, **k):
        raise AssertionError("un PDF digital sin páginas ciegas no debe OCR-izarse")

    monkeypatch.setattr(sm, "ocr_pdf_escalera", _boom)

    cob = sm.ejecutar(case, [d], case_id="EV-2026-001")

    assert cob[0].metodo == "pypdf" and cob[0].ocr is False and cob[0].estado == "ok"


def test_la_calidad_por_pagina_degrada_el_buscable_aunque_la_escalera_no(tmp_path, monkeypatch):
    """La escalera dice «recuperado», pero el buscable sigue con 2 de 6 páginas
    mudas. El promedio pasaría; la señal por página no."""
    case, d = _caso(tmp_path, "informe.pdf", [("", (1200, 1600))] * 6)

    def _fake(entrada, salida, **kw):
        _pdf(Path(salida), [(_DENSO * 3, None)] * 4 + [("", (1200, 1600))] * 2)
        return ResultadoEscalera(Path(salida), "redo")

    monkeypatch.setattr(sm, "ocr_pdf_escalera", _fake)

    cob = sm.ejecutar(case, [d], case_id="EV-2026-001")

    assert cob[0].estado == "low"
    assert "sin texto" in cob[0].nota
