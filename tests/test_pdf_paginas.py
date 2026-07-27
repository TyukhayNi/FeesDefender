"""Perfilado por página: el discriminante de «página ciega» (MEJORAS #90).

Una página ciega es la que esconde un escaneo a página completa bajo una capa
de texto mínima (el pie de firma de LexNET). Es el discriminante que valida el
detector `scripts/detectar_ocr_ciego` y el que decide qué páginas aísla el
peldaño 2 de la escalera de OCR.
"""
from pathlib import Path

import pytest

from core import pdf_paginas as pp


def _imagen(ancho: int, alto: int):
    from PIL import Image
    return Image.new("RGB", (ancho, alto), (200, 200, 200))


def _pdf(path: Path, paginas: list[tuple[str, tuple[int, int] | None]]) -> Path:
    """PDF de N páginas: cada una con `texto` y, opcionalmente, un ráster WxH."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path))
    for texto, raster in paginas:
        if raster is not None:
            c.drawImage(ImageReader(_imagen(*raster)), 0, 0, width=595, height=842)
        if texto:
            c.drawString(40, 800, texto)
        c.showPage()
    c.save()
    return path


def test_perfilar_paginas_da_chars_y_raster_por_pagina(tmp_path):
    pdf = _pdf(tmp_path / "mixto.pdf", [
        ("Contrato de mediacion entre las partes firmantes del encargo.", None),
        ("Firmado electronicamente por LexNET", (1200, 1600)),
    ])

    perfil = pp.perfilar_paginas(pdf)

    assert [p.numero for p in perfil] == [1, 2]
    assert perfil[0].raster_px == 0
    assert perfil[0].chars > 40
    assert perfil[1].raster_px >= pp.MIN_PX_RASTER


def test_paginas_ciegas_marca_el_escaneo_bajo_el_sello(tmp_path):
    pdf = _pdf(tmp_path / "sellado.pdf", [
        ("Portada digital con texto de cuerpo suficiente para no ser sospechosa.", None),
        ("Firmado electronicamente por LexNET", (1200, 1600)),
    ])

    ciegas = pp.paginas_ciegas(pp.perfilar_paginas(pdf))

    assert ciegas == [2]


def test_paginas_ciegas_no_marca_una_pagina_con_raster_y_cuerpo_real(tmp_path):
    cuerpo = "Estipulacion sobre honorarios de intermediacion inmobiliaria. " * 12
    pdf = _pdf(tmp_path / "escaneo_ocrizado.pdf", [(cuerpo[:600], (1200, 1600))])

    ciegas = pp.paginas_ciegas(pp.perfilar_paginas(pdf))

    assert ciegas == []


def test_perfilar_paginas_devuelve_vacio_si_el_pdf_es_ilegible(tmp_path):
    roto = tmp_path / "roto.pdf"
    roto.write_bytes(b"no soy un pdf")

    assert pp.perfilar_paginas(roto) == []


def test_tiene_rasteres_es_el_gate_barato_del_perfilado(tmp_path):
    """Solo metadato (`/Width`×`/Height`): permite no extraer el texto página a
    página en el caso común —un PDF nativo sin escaneos— donde no hay nada ciego
    que buscar."""
    digital = _pdf(tmp_path / "digital.pdf", [("Texto nativo del documento.", None)])
    escaneado = _pdf(tmp_path / "escaneado.pdf", [("", (1200, 1600))])

    assert pp.tiene_rasteres(digital) is False
    assert pp.tiene_rasteres(escaneado) is True


def test_tiene_acroform_distingue_el_formulario_rellenable(tmp_path):
    from pypdf import PdfReader, PdfWriter

    plano = _pdf(tmp_path / "plano.pdf", [("texto suficiente para la pagina", None)])
    assert pp.tiene_acroform(plano) is False

    con_form = tmp_path / "form.pdf"
    w = PdfWriter()
    w.append(PdfReader(str(plano)))
    w.set_need_appearances_writer(True)      # crea /AcroForm en el /Root
    with con_form.open("wb") as fh:
        w.write(fh)
    assert pp.tiene_acroform(con_form) is True
