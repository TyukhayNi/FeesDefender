from core import sala_maquina as sm


def test_clasificar_ruta_por_extension():
    assert sm.clasificar_ruta(".pdf") == "pdf"
    assert sm.clasificar_ruta(".PDF") == "pdf"
    assert sm.clasificar_ruta(".jpg") == "imagen"
    assert sm.clasificar_ruta(".heic") == "imagen"
    assert sm.clasificar_ruta(".eml") == "nativo"
    assert sm.clasificar_ruta(".txt") == "nativo"
    assert sm.clasificar_ruta(".docx") == "nativo"
    assert sm.clasificar_ruta(".mp4") == "sin_soporte"


def test_ocr_quality_texto_limpio_es_ok():
    texto = ("El arrendatario reclama la devolución de los honorarios de "
             "intermediación conforme al artículo veinte de la Ley de "
             "Arrendamientos Urbanos. " * 5)
    estado, motivo = sm.ocr_quality(texto, n_pags=1)
    assert estado == "ok"
    assert motivo == ""


def test_ocr_quality_vacio_es_empty():
    estado, _ = sm.ocr_quality("   ", n_pags=3)
    assert estado == "empty"


def test_ocr_quality_gibberish_es_low():
    # Muchos chars, pero tokens sin vocales / no léxicos (OCR ruidoso).
    basura = "xkq zzt brrr wgh nkk xcv " * 40
    estado, motivo = sm.ocr_quality(basura, n_pags=1)
    assert estado == "low"
    assert "gibberish" in motivo


def test_ocr_quality_baja_densidad_es_low():
    # Texto legible pero muy poco para 10 páginas (escaneado semivacío).
    # NOTA autorrevisión: el literal del plan ("Firmado en Barcelona. Conforme.",
    # 31 chars) cae por debajo de _MIN_CHARS=40 y da "empty" en vez de "low"
    # (contradice su propio docstring/intención). Se alarga el texto manteniendo
    # la intención (legible, pero insuficiente para 10 páginas) sin tocar los
    # umbrales de la implementación.
    estado, _ = sm.ocr_quality(
        "Firmado en Barcelona a fecha indicada. Todo conforme, sin observaciones adicionales.",
        n_pags=10,
    )
    assert estado == "low"
