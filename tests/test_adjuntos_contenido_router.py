from pathlib import Path

from core.adjuntos_contenido.router import extraer, IMG_DECORATIVA_MAX


def test_imagen_pequena_es_decorativa(tmp_path: Path):
    p = tmp_path / "icon.png"
    p.write_bytes(b"x" * 1024)  # < 50KB
    ext = extraer(p, "image/png")
    assert ext.metodo == "omitido"
    assert ext.ok is True
    assert "decorativa" in ext.motivo


def test_imagen_grande_va_a_vision(tmp_path: Path):
    p = tmp_path / "foto.jpg"
    p.write_bytes(b"x" * (IMG_DECORATIVA_MAX + 1))
    ext = extraer(p, "image/jpeg")
    assert ext.metodo == "vision"
    assert ext.vision_estado == "pendiente"


def test_emz_y_zip_omitidos(tmp_path: Path):
    for nombre, mime in [("a.emz", "application/octet-stream"), ("c.zip", "application/zip")]:
        p = tmp_path / nombre
        p.write_bytes(b"x" * (60 * 1024))
        ext = extraer(p, mime)
        assert ext.metodo == "omitido"
        assert ext.ok is True


def test_no_soportado_es_omitido_sin_excepcion(tmp_path: Path):
    p = tmp_path / "raro.xyz"
    p.write_bytes(b"contenido")
    ext = extraer(p, "application/octet-stream")
    assert ext.metodo == "omitido"
    assert "sin extractor" in ext.motivo


def test_rtf_extrae_texto_alta_confianza(tmp_path: Path):
    p = tmp_path / "burofax.rtf"
    p.write_text(r"{\rtf1\ansi Hola burofax\par}", encoding="ascii")
    ext = extraer(p, "application/rtf")
    assert ext.metodo == "rtf"
    assert ext.confianza == "alta"
    assert "Hola" in ext.texto


def test_docling_se_marca_por_verificar(tmp_path: Path, monkeypatch):
    p = tmp_path / "escaneado.pdf"
    p.write_bytes(b"%PDF-1.4 fake")
    monkeypatch.setattr("core.adjuntos_contenido.router._extract_one",
                        lambda ruta: ("texto OCR", "docling"))
    ext = extraer(p, "application/pdf")
    assert ext.metodo == "docling"
    assert ext.confianza == "por-verificar"


def test_sin_texto_marca_no_ok(tmp_path: Path, monkeypatch):
    p = tmp_path / "escaneado.pdf"
    p.write_bytes(b"%PDF-1.4 fake")
    monkeypatch.setattr("core.adjuntos_contenido.router._extract_one",
                        lambda ruta: ("", "sin_texto"))
    ext = extraer(p, "application/pdf")
    assert ext.metodo == "sin_texto"
    assert ext.ok is False
