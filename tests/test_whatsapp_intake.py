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


class TestDepositExport:
    def _ensure_case(self):
        importlib.reload(case_manager)
        case_manager.ensure_case("WA-2026-001", titulo="Caso WhatsApp test")
        return "WA-2026-001"

    def test_deposita_verbatim_y_conserva_zip(self):
        from core import intake_lotes, whatsapp_intake

        importlib.reload(whatsapp_intake)
        case_id = self._ensure_case()

        content = _make_zip({"_chat.txt": _CHAT_TXT, "IMG-1.jpg": b"jpgdata"})
        res = whatsapp_intake.deposit_export(
            case_id, "02_Grupo operacion", content, zip_name="Grupo Valldaura.zip"
        )

        assert res.skipped_dedup is False
        # chat_dir = <lote>/<rol>/<chat> — el lote conserva la subcarpeta de rol
        # (verbatim §4).
        lote_dir = res.chat_dir.parent.parent
        assert intake_lotes.PATRON_LOTE.match(lote_dir.name).group(2) == "whatsapp"
        assert res.chat_dir == lote_dir / "02_Grupo operacion" / "Grupo Valldaura"
        assert (res.chat_dir / "_chat.txt").read_bytes() == _CHAT_TXT
        assert (res.chat_dir / "IMG-1.jpg").read_bytes() == b"jpgdata"
        assert (res.chat_dir / "_export_original.zip").exists()

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

    def test_reimportar_mismo_zip_se_salta(self):
        from core import whatsapp_intake

        importlib.reload(whatsapp_intake)
        case_id = self._ensure_case()

        content = _make_zip({"_chat.txt": _CHAT_TXT, "IMG-1.jpg": b"jpgdata"})
        first = whatsapp_intake.deposit_export(
            case_id, "03_Otros", content, zip_name="dup.zip"
        )
        assert first.skipped_dedup is False

        second = whatsapp_intake.deposit_export(
            case_id, "03_Otros", content, zip_name="dup.zip"
        )
        assert second.skipped_dedup is True
        assert second.files_written == []


# ---------------------------------------------------------------------------
# deposit_export → lote (MEJORAS #54, T5)
# ---------------------------------------------------------------------------

def test_deposit_crea_lote_con_manifiesto(tmp_casos_root):
    from core import intake_lotes, whatsapp_intake
    case_id = "EV-WA-LOTE"
    case_manager.ensure_case(case_id, titulo="wa")
    content = _make_zip({"_chat.txt": _CHAT_TXT, "IMG-001.jpg": b"img"})
    res = whatsapp_intake.deposit_export(case_id, "03_Otros", content, zip_name="chat.zip")
    # chat_dir = <lote>/<rol>/<chat> — el lote conserva la subcarpeta de rol (verbatim §4)
    lote_dir = res.chat_dir.parent.parent
    assert intake_lotes.PATRON_LOTE.match(lote_dir.name).group(2) == "whatsapp"
    assert res.chat_dir.parent.name == "03_Otros"
    man = intake_lotes.leer_manifiesto(lote_dir)
    assert man["fuente"] == "whatsapp"
    rels = {i["relpath"] for i in man["items"]}
    assert "03_Otros/chat/_chat.txt" in rels
    assert "03_Otros/chat/_export_original.zip" in rels   # sí entra (spec §5)


def test_duplicado_cross_lote_se_copia_y_anota(tmp_casos_root):
    from core import intake_lotes, whatsapp_intake
    from core.intake_manifest import IntakeManifest, compute_sha256_bytes
    case_id = "EV-WA-DUP"
    case_manager.ensure_case(case_id, titulo="wa")
    # La misma imagen ya entró por un lote manual anterior (registrada en M9).
    with IntakeManifest(case_id) as m:
        m.register(compute_sha256_bytes(b"img"),
                   "2026-06-10_manual_01/IMG-001.jpg", source="manual")
    content = _make_zip({"_chat.txt": _CHAT_TXT, "IMG-001.jpg": b"img"})
    res = whatsapp_intake.deposit_export(case_id, "03_Otros", content, zip_name="chat.zip")
    assert not res.skipped_dedup
    assert (res.chat_dir / "IMG-001.jpg").exists()        # SE COPIA igualmente (§6)
    man = intake_lotes.leer_manifiesto(res.chat_dir.parent.parent)
    item = next(i for i in man["items"] if i["relpath"].endswith("IMG-001.jpg"))
    assert item["duplicado_de"] == "2026-06-10_manual_01/IMG-001.jpg"


def test_zip_identico_sigue_dedup_de_canal_sin_lote_nuevo(tmp_casos_root):
    from core import config, whatsapp_intake
    case_id = "EV-WA-IDEM"
    case_manager.ensure_case(case_id, titulo="wa")
    content = _make_zip({"_chat.txt": _CHAT_TXT})
    r1 = whatsapp_intake.deposit_export(case_id, "03_Otros", content, zip_name="chat.zip")
    r2 = whatsapp_intake.deposit_export(case_id, "03_Otros", content, zip_name="chat.zip")
    assert r2.skipped_dedup and r2.chat_dir == r1.chat_dir
    input_dir = config.caso_path(case_id) / "00_Input"
    lotes = [d for d in input_dir.iterdir() if d.name.endswith("_whatsapp_01")
             or "_whatsapp_" in d.name]
    assert len(lotes) == 1                                # no se abrió un segundo lote
