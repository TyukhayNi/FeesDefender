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


# ---------------------------------------------------------------------------
# deposit_export
# ---------------------------------------------------------------------------
from datetime import datetime

from core.config import caso_path


class TestDepositExport:
    def _ensure_case(self):
        importlib.reload(case_manager)
        case_manager.ensure_case("WA-2026-001", titulo="Caso WhatsApp test")
        return "WA-2026-001"

    def test_deposita_verbatim_y_conserva_zip(self):
        from core import whatsapp_intake

        importlib.reload(whatsapp_intake)
        case_id = self._ensure_case()

        content = _make_zip({"_chat.txt": _CHAT_TXT, "IMG-1.jpg": b"jpgdata"})
        res = whatsapp_intake.deposit_export(
            case_id, "02_Grupo operacion", content, zip_name="Grupo Valldaura.zip"
        )

        assert res.skipped_dedup is False
        chat_dir = (
            caso_path(case_id)
            / "00_Input"
            / "02_Whatsapp"
            / "02_Grupo operacion"
            / "Grupo Valldaura"
        )
        assert res.chat_dir == chat_dir
        assert (chat_dir / "_chat.txt").read_bytes() == _CHAT_TXT
        assert (chat_dir / "IMG-1.jpg").read_bytes() == b"jpgdata"
        assert (chat_dir / "_export_original.zip").exists()

    def test_rol_invalido_falla(self):
        from core import whatsapp_intake

        importlib.reload(whatsapp_intake)
        case_id = self._ensure_case()
        content = _make_zip({"_chat.txt": _CHAT_TXT})
        with pytest.raises(ValueError, match="rol"):
            whatsapp_intake.deposit_export(
                case_id, "99_Inexistente", content, zip_name="x.zip"
            )

    def test_caso_inexistente_falla(self):
        from core import whatsapp_intake

        importlib.reload(whatsapp_intake)
        content = _make_zip({"_chat.txt": _CHAT_TXT})
        with pytest.raises(FileNotFoundError):
            whatsapp_intake.deposit_export(
                "NO-EXISTE", "03_Otros", content, zip_name="x.zip"
            )

    def test_registra_manifest_y_emite_evento(self):
        from core import whatsapp_intake, intake_log
        from core.intake_manifest import IntakeManifest, compute_sha256_bytes

        importlib.reload(whatsapp_intake)
        case_id = self._ensure_case()

        content = _make_zip({"_chat.txt": _CHAT_TXT, "IMG-1.jpg": b"jpgdata"})
        whatsapp_intake.deposit_export(
            case_id, "00_Consultor propietario", content, zip_name="Juan.zip"
        )

        with IntakeManifest(case_id) as m:
            assert m.lookup(compute_sha256_bytes(content)) is not None
            assert m.lookup(compute_sha256_bytes(b"jpgdata")) is not None

        eventos = intake_log.read_events(case_id)
        assert any(e["event"] == "upload_whatsapp" for e in eventos)

    def test_rango_fechas_genera_recortado(self):
        from core import whatsapp_intake

        importlib.reload(whatsapp_intake)
        case_id = self._ensure_case()

        content = _make_zip({"_chat.txt": _CHAT_TXT})
        res = whatsapp_intake.deposit_export(
            case_id,
            "03_Otros",
            content,
            zip_name="c.zip",
            date_range=(datetime(2024, 1, 9), datetime(2024, 1, 9, 23, 59)),
        )
        recortado = res.chat_dir / "_chat_recortado.txt"
        assert recortado.exists()
        assert (res.chat_dir / "_chat.txt").read_bytes() == _CHAT_TXT
