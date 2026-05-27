"""Smoke test del wrapper OCR (core/anon/ocr.py).

Cubre el bug §11 de docs/MEJORAS_FUTURAS.md: el wrapper invocaba
``ocrmypdf.ocr`` con la firma incorrecta (input como kwarg + language como
cadena). Verifica end-to-end que un PDF sin capa de texto sale con texto
extraíble tras pasar por ``ocr_pdf``.

Se salta si falta ocrmypdf o tesseract en el entorno (CI sin binarios).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from core.anon.ocr import ocr_disponible, ocr_pdf

_TESSERACT = shutil.which("tesseract") is not None
pytestmark = pytest.mark.skipif(
    not (ocr_disponible() and _TESSERACT),
    reason="Requiere ocrmypdf + tesseract instalados.",
)


def _pdf_sin_texto(destino: Path, texto: str = "FACTURA") -> Path:
    """Genera un PDF de una página formada solo por una imagen con texto.

    El PDF no tiene capa de texto (es una imagen), justo el caso que motiva
    el OCR. Usa Pillow (dependencia ya presente del módulo anon).
    """
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1200, 400), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 120)
    except OSError:
        font = ImageFont.load_default()
    draw.text((60, 120), texto, fill="black", font=font)
    img.save(destino, "PDF", resolution=200.0)
    return destino


def test_ocr_pdf_extrae_texto(tmp_path: Path) -> None:
    entrada = _pdf_sin_texto(tmp_path / "scan.pdf", texto="FACTURA")
    salida = tmp_path / "scan_ocr.pdf"

    resultado = ocr_pdf(entrada, salida, idiomas="spa")

    assert resultado.exists()
    from pypdf import PdfReader

    texto = PdfReader(str(resultado)).pages[0].extract_text() or ""
    assert "factura" in texto.lower()
