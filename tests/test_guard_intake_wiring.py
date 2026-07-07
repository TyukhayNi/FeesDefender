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


# ---------------------------------------------------------------------------
# Email (email_dest_dir es el resolver de destino de escritura)
# ---------------------------------------------------------------------------

def test_email_dest_dir_disponible_normal(tmp_casos_root):
    # NO se recarga email_export: contaminaría a test_email_export (liga nombres
    # al importar). dir_intake/caso_path resuelven contra los settings actuales.
    from core import email_export
    case_manager.ensure_case("EV-2026-001", titulo="x")
    d = email_export.email_dest_dir("EV-2026-001")
    assert d.as_posix().endswith("00_Input/03_Email")
    assert "_pendiente_checkin" not in d.as_posix()


def test_email_dest_dir_prestado_desvia(tmp_casos_root):
    from core import email_export, intake_log
    case_id = _caso_prestado()
    d = email_export.email_dest_dir(case_id)
    assert d.as_posix().endswith("_pendiente_checkin/email/00_Input/03_Email")
    assert any(e["event"] == "pendiente_checkin" for e in intake_log.read_events(case_id))


# ---------------------------------------------------------------------------
# CRM pull (sync_sudespacho.pull_expediente_v2) — cliente fake inyectado
# ---------------------------------------------------------------------------

class _FakeCRMClient:
    """Cliente REST mínimo para ejercitar el pull sin red."""
    def __init__(self, ss):
        self._ss = ss

    def list_gdocu_docs_rest(self, expediente_id, element=None):
        return [self._ss.GdocuDocInfo(
            doc_id="1", filename="doc.pdf", id_carpeta="1",
            id_carpeta_label="General", mime="application/pdf", size=3, raw={})]

    def get_presigned_download_url(self, doc_id, expediente_id, element=None):
        return "http://fake/url"

    def _download_url_raw(self, url):
        return b"pdf"


def test_crm_pull_prestado_desvia_a_bandeja(tmp_casos_root):
    # NO se recarga sync_sudespacho: contaminaría a test_sync_sudespacho (liga
    # nombres al importar y no se re-recarga). caso_path resuelve contra los
    # settings actuales (mismo mecanismo que usan sus propios tests).
    from core import sync_sudespacho as ss, intake_log
    case_id = _caso_prestado()
    from core.config import caso_path
    res = ss.pull_expediente_v2(case_id, "648", client=_FakeCRMClient(ss))
    assert res.documents_written == 1
    caso = caso_path(case_id)
    # El doc está en la bandeja, no en el árbol vivo 05_CRM/.
    bandeja_crm = caso / "_pendiente_checkin" / "crm" / "00_Input" / "05_CRM"
    assert any(bandeja_crm.rglob("*.pdf"))
    vivo_crm = caso / "00_Input" / "05_CRM"
    pdfs_vivos = [p for p in vivo_crm.rglob("*.pdf")] if vivo_crm.exists() else []
    assert not pdfs_vivos
    assert any(e["event"] == "pendiente_checkin" for e in intake_log.read_events(case_id))


def test_crm_pull_disponible_escribe_en_arbol_vivo(tmp_casos_root):
    from core import sync_sudespacho as ss, intake_log
    case_id = "EV-2026-001"
    case_manager.ensure_case(case_id, titulo="x")
    from core.config import caso_path
    res = ss.pull_expediente_v2(case_id, "648", client=_FakeCRMClient(ss))
    assert res.documents_written == 1
    caso = caso_path(case_id)
    assert any((caso / "00_Input" / "05_CRM").rglob("*.pdf"))
    assert not (caso / "_pendiente_checkin").exists()
