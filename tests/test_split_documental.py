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
