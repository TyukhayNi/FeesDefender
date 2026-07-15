"""Helpers para construir PDFs de prueba con capa de texto real (sin fixtures binarios).

Reutiliza el patrón de ``tests/test_anon_separar._build_pdf`` (fpdf2). Una sublista
vacía ``[]`` produce una página SIN texto (delimitador en blanco para el detector).
"""
from __future__ import annotations

from pathlib import Path


def build_pdf(path: Path, pages: list[list[str]]) -> Path:
    """Construye un PDF: una página por sublista; cada string es una línea.

    ``[]`` ⇒ página en blanco (add_page sin celdas). Devuelve la ruta.
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
