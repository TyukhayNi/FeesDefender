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
