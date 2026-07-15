"""Tests del cerebro del split (core/split_documental)."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests._pdf_fixtures import build_pdf


def test_build_pdf_pagina_en_blanco_sin_texto(tmp_path: Path):
    # 3 páginas: texto, BLANCA ([]), texto
    pdf = build_pdf(tmp_path / "b.pdf", [["CEDULA DE EMPLAZAMIENTO", "Juzgado"], [], ["FACTURA", "Total 100"]])
    from pypdf import PdfReader
    with PdfReader(str(pdf)) as r:
        assert len(r.pages) == 3
        assert len((r.pages[1].extract_text() or "").strip()) < 10  # la blanca ~0 chars
        assert "CEDULA" in (r.pages[0].extract_text() or "").upper()


from core.split_documental import Segmento, DocLogico, segmentar_por_blancos


def test_segmentar_colapsa_blancos_y_bordes():
    # 8 págs, blancas en {3, 6, 7}. Blancos iniciales/finales/consecutivos no crean vacíos.
    assert segmentar_por_blancos(8, {3, 6, 7}) == [(1, 2), (4, 5), (8, 8)]


def test_segmentar_sin_blancos_un_solo_rango():
    assert segmentar_por_blancos(5, set()) == [(1, 5)]


def test_segmentar_todo_blanco_vacio():
    assert segmentar_por_blancos(3, {1, 2, 3}) == []


from core.split_documental import _primeras_lineas, clasificar


def test_primeras_lineas_filtra_cortas_y_limita():
    txt = "CEDULA DE EMPLAZAMIENTO\nab\nJuzgado de Instancia\nlinea3\nlinea4\nlinea5\nlinea6"
    out = _primeras_lineas(txt, n=3)
    assert out == ["CEDULA DE EMPLAZAMIENTO", "Juzgado de Instancia", "linea3"]  # 'ab' (<3) fuera


def test_clasificar_usa_marcador_judicial():
    textos = ["CÉDULA DE EMPLAZAMIENTO\nJuzgado", "otra pagina"]
    assert clasificar(textos, 1, 1) == "CEDULA_EMPLAZAMIENTO"


def test_clasificar_sin_marcador_devuelve_documento():
    textos = ["texto anodino sin marcadores reconocibles"]
    assert clasificar(textos, 1, 1) == "DOCUMENTO"


import pytest as _pytest
from core.split_documental import TIPOS_EXTRA_EV


@_pytest.mark.parametrize("linea,esperado", [
    ("PREVENCIÓN DE BLANQUEO DE CAPITALES", "DOC_PBC"),
    ("CONTRATO DE ARRAS PENITENCIALES", "DOC_ARRAS"),
    ("DOCUMENTO DE RESERVA", "DOC_RESERVA"),
])
def test_marcadores_ev_clasifican(linea, esperado):
    assert clasificar([linea], 1, 1) == esperado


def test_tipos_extra_ev_no_vacio():
    assert len(TIPOS_EXTRA_EV) >= 3


from core.split_documental import cobertura_tinta, paginas_en_blanco, _texto_por_pagina


def test_cobertura_tinta_blanca_vs_texto(tmp_path):
    pdf = build_pdf(tmp_path / "t.pdf", [["MUCHO TEXTO EN ESTA PAGINA " * 5], []])
    tinta_texto = cobertura_tinta(pdf, 1)
    tinta_blanca = cobertura_tinta(pdf, 2)
    assert tinta_blanca < tinta_texto
    assert tinta_blanca < 0.008  # la blanca por debajo del umbral


def test_paginas_en_blanco_detecta_la_delimitadora(tmp_path):
    # La página de contenido real tiene >10 chars: la reja barata de caracteres
    # (UMBRAL_CHARS_BLANCO) la excluye sin rasterizar. Solo la hoja en blanco (~0 chars)
    # llega al detector de tinta. Un contenido de 1 palabra sería un caso irreal.
    pdf = build_pdf(tmp_path / "b.pdf", [["CEDULA DE EMPLAZAMIENTO"], [], ["FACTURA", "Total 100"]])
    textos = _texto_por_pagina(pdf)
    assert paginas_en_blanco(pdf, textos) == {2}
