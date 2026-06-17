"""Tests del glue de ingesta de WhatsApp (core.whatsapp_intake)."""
from __future__ import annotations

import importlib
import io
import zipfile

import pytest

from core import case_manager


def _make_zip(files: dict[str, bytes]) -> bytes:
    """ZIP en memoria {nombre: contenido}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


_CHAT_TXT = (
    "8/1/24, 10:32 - Juan: Hola\n"
    "8/1/24, 10:33 - Juan: IMG-1.jpg (archivo adjunto)\n"
    "8/1/24, 10:34 - Juan: nota.opus (archivo adjunto)\n"
    "9/1/24, 11:00 - Ana: DOC-2.pdf (archivo adjunto)\n"
).encode("utf-8")


@pytest.fixture(autouse=True)
def _reload_config(tmp_casos_root, monkeypatch):
    from core import config as cfg

    importlib.reload(cfg)
    importlib.reload(case_manager)


def test_analyze_cuenta_mensajes_adjuntos_y_faltantes():
    from core import whatsapp_intake

    importlib.reload(whatsapp_intake)

    content = _make_zip({"_chat.txt": _CHAT_TXT, "IMG-1.jpg": b"\xff\xd8jpgdata"})
    prev = whatsapp_intake.analyze(content, zip_name="WhatsApp Chat - Juan.zip")

    assert prev.chat_name == "WhatsApp Chat - Juan"
    assert prev.n_mensajes == 4
    assert prev.adjuntos_presentes == ["IMG-1.jpg"]
    assert set(prev.adjuntos_faltantes) == {"DOC-2.pdf", "nota.opus"}
    assert prev.rango_fechas is not None
    assert prev.rango_fechas[0].day == 8 and prev.rango_fechas[1].day == 9


def test_analyze_cuenta_audios():
    from core import whatsapp_intake

    importlib.reload(whatsapp_intake)

    content = _make_zip(
        {
            "_chat.txt": _CHAT_TXT,
            "IMG-1.jpg": b"x",
            "nota.opus": b"audio",
        }
    )
    prev = whatsapp_intake.analyze(content, zip_name="chat.zip")
    assert prev.audios == ["nota.opus"]


def test_analyze_sin_chat_txt_falla():
    from core import whatsapp_intake

    importlib.reload(whatsapp_intake)

    content = _make_zip({"IMG-1.jpg": b"x"})
    with pytest.raises(ValueError, match="_chat.txt"):
        whatsapp_intake.analyze(content, zip_name="chat.zip")
