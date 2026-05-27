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


def _pdf_sin_texto(destino: Path, palabra_clave: str = "FACTURA") -> Path:
    """Genera un PDF de una página formada solo por una imagen con texto.

    El PDF no tiene capa de texto (es una imagen), justo el caso que motiva
    el OCR. Renderiza un párrafo de varias líneas (>100 caracteres) para que
    OCR sea fiable bajo deskew + rotate-pages y supere el umbral de texto
    mínimo del extractor. Usa Pillow (dependencia ya presente del módulo anon).
    """
    from PIL import Image, ImageDraw, ImageFont

    lineas = [
        f"{palabra_clave} DE PRUEBA NUMERO 12345",
        "Este documento es un contrato de ejemplo",
        "para verificar el reconocimiento optico de",
        "caracteres en el pipeline de anonimizacion.",
        "Importe total: mil doscientos euros con IVA.",
    ]
    img = Image.new("RGB", (1654, 1000), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 56)
    except OSError:
        font = ImageFont.load_default()
    y = 90
    for ln in lineas:
        draw.text((90, y), ln, fill="black", font=font)
        y += 110
    img.save(destino, "PDF", resolution=200.0)
    return destino


def test_ocr_pdf_extrae_texto(tmp_path: Path) -> None:
    entrada = _pdf_sin_texto(tmp_path / "scan.pdf", palabra_clave="FACTURA")
    salida = tmp_path / "scan_ocr.pdf"

    resultado = ocr_pdf(entrada, salida, idiomas="spa")

    assert resultado.exists()
    from pypdf import PdfReader

    texto = PdfReader(str(resultado)).pages[0].extract_text() or ""
    assert "factura" in texto.lower()


def test_auto_ocr_integracion(tmp_path: Path, monkeypatch) -> None:
    """anonimizar_documento con auto_ocr=True procesa un PDF escaneado.

    Sin el flag debe marcar OCR_REQUERIDO; con el flag, OCR a copia temporal
    y anonimiza, dejando el original intacto. (Usa el pipeline completo, que
    requiere también Presidio + modelos spaCy instalados en el entorno.)
    """
    from core.anon import api as anon_api

    case_dir = tmp_path / "caso"
    drive = case_dir / "00_Input" / "01_Drive EV"
    drive.mkdir(parents=True)
    monkeypatch.setattr(anon_api, "caso_path", lambda cid: case_dir)

    src = _pdf_sin_texto(drive / "escaneado.pdf", palabra_clave="CONTRATO")
    case_id = "EV-2099-001"

    sin = anon_api.anonimizar_documento(case_id, src)
    assert sin["alertas"] == ["OCR_REQUERIDO"]

    con = anon_api.anonimizar_documento(case_id, src, auto_ocr=True)
    assert con["ok"] is True
    assert con["ruta_md"] is not None and con["ruta_md"].exists()
    # El original sigue intacto (cadena de custodia).
    assert src.exists()
