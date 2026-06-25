"""OCR por página a baja resolución — robusto frente a OOM (MEJORAS #39).

Docling/RapidOCR hace `std::bad_alloc` al preprocesar páginas escaneadas de alta
resolución (visto en W-02VND1: escritura y poderes notariales de 16-17 páginas).
La estrategia aquí es renderizar **cada página por separado a baja resolución**
(``scale`` ≈ 2.0 → ~144 DPI) y OCR-izarla de forma independiente, tolerando que
una página concreta falle sin tumbar el documento entero.

`ocr_images` es la lógica pura (dependencia de OCR inyectable, testeable sin OCR
real). `render_pdf_pages` y `ocr_pdf_per_page` enchufan pypdfium2 + RapidOCR
(engine torch, el mismo backend que usa Docling) con sus valores por defecto.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

# Engine RapidOCR cargado una sola vez (la carga de modelos es cara).
_ENGINE = None


def _engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr import EngineType, RapidOCR
        _ENGINE = RapidOCR(params={
            "Det.engine_type": EngineType.TORCH,
            "Cls.engine_type": EngineType.TORCH,
            "Rec.engine_type": EngineType.TORCH,
        })
    return _ENGINE


def _default_ocr_image(img) -> str:
    import numpy as np
    res = _engine()(np.array(img))
    txts = getattr(res, "txts", None)
    return " ".join(txts) if txts else ""


def ocr_images(
    images: Iterable,
    *,
    ocr_image: Callable = _default_ocr_image,
    on_page: Callable[[int, int], None] | None = None,
) -> str:
    """OCR-iza una secuencia de imágenes y concatena el texto por página.

    Tolerante a fallos: si el OCR de una página lanza (p. ej. un error de memoria
    recuperable), esa página aporta cadena vacía y se continúa con las siguientes.
    `on_page(indice, n_chars)` recibe el progreso por página.
    """
    parts: list[str] = []
    for i, img in enumerate(images):
        try:
            txt = ocr_image(img)
        except Exception:  # noqa: BLE001 — una página mala no tumba el documento
            txt = ""
        parts.append(txt)
        if on_page:
            on_page(i, len(txt))
    return "\n\n".join(parts).strip()


def render_pdf_pages(pdf_path: Path | str, scale: float = 2.0) -> Iterable:
    """Genera una imagen PIL por página del PDF, renderizada a ``scale`` (baja
    resolución para acotar la memoria y evitar el OOM de RapidOCR)."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        for i in range(len(pdf)):
            yield pdf[i].render(scale=scale).to_pil().convert("RGB")
    finally:
        pdf.close()


def ocr_pdf_per_page(
    pdf_path: Path | str,
    *,
    scale: float = 2.0,
    on_page: Callable[[int, int], None] | None = None,
) -> str:
    """OCR de un PDF página a página a baja resolución. Devuelve el texto concatenado."""
    return ocr_images(render_pdf_pages(pdf_path, scale), on_page=on_page)
