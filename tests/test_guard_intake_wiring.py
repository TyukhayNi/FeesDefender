"""Guard de escritura §6 cableado en los puntos de intake (DISEÑO_V2).

Cuando el caso está `prestado`/`conflicto`, toda escritura de intake se desvía a
``_pendiente_checkin/<origen>/...`` (con evento) en lugar del árbol vivo; cuando
está `disponible`, escritura normal. Aquí se cubren los puntos de intake que
escriben bytes en el caso. Datos sintéticos.
"""

from __future__ import annotations

import importlib
import io
import zipfile

import pytest

from core import case_manager


@pytest.fixture(autouse=True)
def _reload(tmp_casos_root):
    from core import config as cfg
    importlib.reload(cfg)
    importlib.reload(case_manager)


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


_CHAT = b"8/1/24, 10:32 - Juan: Hola\n"


def _caso_prestado(case_id="EV-2026-001"):
    case_manager.ensure_case(case_id, titulo="Caso guard")
    case_manager.escribir_lock(case_id, user="Nikolai Tyukhay",
                               timestamp="2026-07-07T09:45:12Z", nonce="n")
    return case_id


# ---------------------------------------------------------------------------
# WhatsApp
# ---------------------------------------------------------------------------

def test_whatsapp_disponible_escribe_normal(tmp_casos_root):
    from core import whatsapp_intake, intake_log
    importlib.reload(intake_log); importlib.reload(whatsapp_intake)
    case_id = "EV-2026-001"
    case_manager.ensure_case(case_id, titulo="Caso guard")
    content = _make_zip({"_chat.txt": _CHAT})
    res = whatsapp_intake.deposit_export(case_id, "03_Otros", content, zip_name="chat.zip")
    assert "_pendiente_checkin" not in res.chat_dir.as_posix()
    assert "02_Whatsapp" in res.chat_dir.as_posix()


def test_whatsapp_prestado_desvia_a_bandeja(tmp_casos_root):
    from core import whatsapp_intake, intake_log
    importlib.reload(intake_log); importlib.reload(whatsapp_intake)
    case_id = _caso_prestado()
    content = _make_zip({"_chat.txt": _CHAT})
    res = whatsapp_intake.deposit_export(case_id, "03_Otros", content, zip_name="chat.zip")
    assert "_pendiente_checkin/whatsapp/" in res.chat_dir.as_posix()
    # Los ficheros existen en la bandeja, no en el árbol vivo.
    from core.config import caso_path
    assert res.chat_dir.exists()
    vivo = caso_path(case_id) / "00_Input" / "02_Whatsapp" / "03_Otros"
    assert not any(vivo.rglob("*.txt")) if vivo.exists() else True
    # Evento de desvío registrado.
    assert any(e["event"] == "pendiente_checkin" for e in intake_log.read_events(case_id))
