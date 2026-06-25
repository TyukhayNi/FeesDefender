"""OCR por página a baja resolución (robustez OCR, #39).

Docling/RapidOCR hace `std::bad_alloc` al preprocesar páginas escaneadas de alta
resolución (visto en W-02VND1: escritura/poderes notariales de 16-17 págs). La
solución es renderizar cada página a baja resolución y OCR-izarla por separado,
tolerando que alguna página falle. Aquí se testea el ensamblado y la tolerancia
a fallos con dependencias inyectadas (sin OCR real, rápido).
"""

from __future__ import annotations


def test_ocr_images_concatena_paginas():
    from core.ocr_per_page import ocr_images
    out = ocr_images(["p0", "p1"], ocr_image=lambda im: {"p0": "hola", "p1": "mundo"}[im])
    assert "hola" in out and "mundo" in out


def test_ocr_images_tolera_fallo_de_pagina():
    """Una página que revienta (p. ej. OOM) NO debe tumbar el documento entero;
    se salta y se conserva el texto de las demás."""
    from core.ocr_per_page import ocr_images

    def fake_ocr(im):
        if im == "mala":
            raise RuntimeError("bad_alloc simulado")
        return {"buena1": "primera", "buena2": "segunda"}[im]

    out = ocr_images(["buena1", "mala", "buena2"], ocr_image=fake_ocr)
    assert "primera" in out
    assert "segunda" in out  # la página posterior a la fallida sigue OCR-izándose


def test_ocr_images_reporta_progreso():
    from core.ocr_per_page import ocr_images
    vistos = []
    ocr_images(
        ["a", "b"],
        ocr_image=lambda im: im.upper(),
        on_page=lambda i, chars: vistos.append((i, chars)),
    )
    assert vistos == [(0, 1), (1, 1)]
