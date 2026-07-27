"""Tests del detector de «OCR ciego bajo el sello» (`scripts/detectar_ocr_ciego.py`).

La huella que busca: página con ráster grande y texto corto (el sello de firma),
dentro de un PDF que SÍ trae capa de texto. Los dos falsos positivos que el
detector debe evitar están cubiertos abajo: la página de texto denso y el
documento sin capa de texto en origen.
"""
from __future__ import annotations

import pytest

from scripts.detectar_ocr_ciego import (
    MAX_CHARS_PAGINA, analizar_caso, filas_ok, perfilar,
)

pytest.importorskip("fpdf")
pytest.importorskip("PIL")

SELLO = "Firmado digitalmente por LexNET"
CUERPO = "CLAUSULA SEXTA HONORARIOS DE INTERMEDIACION. " * 40


def _png_escaneo(destino, ancho=1200, alto=1700):
    """Ráster suficientemente grande para contar como escaneo (> MIN_PX_RASTER)."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (ancho, alto), "white")
    ImageDraw.Draw(img).text((40, 40), "texto que solo vive en el bitmap", fill="black")
    img.save(destino)
    return destino


def _pdf(destino, paginas):
    """`paginas`: lista de (ruta_png_o_None, texto_real_o_None)."""
    from fpdf import FPDF

    pdf = FPDF(unit="pt", format="A4")
    pdf.set_auto_page_break(False)
    for imagen, texto in paginas:
        pdf.add_page()
        if imagen is not None:
            pdf.image(str(imagen), x=0, y=0, w=595, h=842)
        if texto is not None:
            pdf.set_font("helvetica", size=8)
            pdf.set_xy(30, 40)
            pdf.multi_cell(535, 10, texto)
    pdf.output(str(destino))
    return destino


def test_marca_la_pagina_escaneada_que_solo_tiene_sello(tmp_path):
    png = _png_escaneo(tmp_path / "escaneo.png")
    pdf = _pdf(tmp_path / "mixto.pdf", [(png, SELLO), (None, CUERPO)])

    perfil = perfilar(pdf)

    assert perfil is not None
    assert perfil.n_pags == 2
    assert perfil.paginas_saltadas == [1], "la pág. 1 (ráster + sello) es la que --skip-text salta"
    assert perfil.chars_fuente > 0


def test_no_marca_la_pagina_de_texto_denso(tmp_path):
    """Un escaneo con cuerpo ya recuperado no es sospechoso, aunque lleve ráster."""
    png = _png_escaneo(tmp_path / "escaneo.png")
    pdf = _pdf(tmp_path / "denso.pdf", [(png, CUERPO)])

    perfil = perfilar(pdf)

    assert perfil is not None
    assert len(CUERPO.strip()) > MAX_CHARS_PAGINA
    assert perfil.paginas_saltadas == []


def test_documento_sin_capa_de_texto_no_es_candidato(tmp_path):
    """Falso positivo clásico (DNIs, capturas): sin capa de texto en origen el
    documento fue por la ruta OCR y se OCR-izó entero — no hay pérdida posible."""
    png = _png_escaneo(tmp_path / "escaneo.png")
    solo_imagen = _pdf(tmp_path / "solo_imagen.pdf", [(png, None)])

    perfil = perfilar(solo_imagen)
    assert perfil is not None
    assert perfil.chars_fuente == 0
    assert perfil.paginas_saltadas == [1], "la huella de página sí está…"

    case_dir = _montar_caso(tmp_path, "solo_imagen.pdf", solo_imagen)
    candidatos, descartes = analizar_caso(case_dir)

    assert candidatos == [], "…pero el discriminante de capa de texto lo descarta"
    assert descartes["sin_capa_de_texto"] == 1


def test_reconstruye_las_filas_desde_el_frontmatter_si_falta_cobertura(tmp_path):
    """Casos anteriores a `_cobertura.json` (ver #84): se leen los MD de 03_MD/."""
    png = _png_escaneo(tmp_path / "escaneo.png")
    pdf = _pdf(tmp_path / "mixto.pdf", [(png, SELLO)])
    case_dir = _montar_caso(tmp_path, "mixto.pdf", pdf, con_cobertura=False)

    filas = filas_ok(case_dir)

    assert [f["slug"] for f in filas] == ["mixto__aaaaaaaa"]
    candidatos, _ = analizar_caso(case_dir)
    assert len(candidatos) == 1


def _montar_caso(tmp_path, rel_path, pdf_origen, *, con_cobertura=True):
    """Expediente mínimo con el PDF en 00_Input/ y su rastro en la Sala de máquina."""
    import json
    import shutil

    case_dir = tmp_path / "caso"
    entrada = case_dir / "00_Input"
    entrada.mkdir(parents=True)
    shutil.copy(pdf_origen, entrada / rel_path)

    sm_dir = case_dir / "01_Procesado" / "02_Sala de máquina"
    slug = f"{pdf_origen.stem}__aaaaaaaa"
    if con_cobertura:
        sm_dir.mkdir(parents=True)
        (sm_dir / "_cobertura.json").write_text(json.dumps([{
            "slug": slug, "rel_path": rel_path, "metodo": "ocr", "estado": "ok",
        }]), encoding="utf-8")
    else:
        (sm_dir / "03_MD").mkdir(parents=True)
        (sm_dir / "03_MD" / f"{slug}.md").write_text(
            f"---\nextractor: ocr\nocr_quality: ok\nsource_path: {rel_path}\n---\n\ncuerpo\n",
            encoding="utf-8")
    return case_dir
