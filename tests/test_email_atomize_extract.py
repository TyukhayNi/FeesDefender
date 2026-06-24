from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import extract as E


def _msg(mid: str, subject: str, body: str = "cuerpo") -> EmailMessage:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "a@x"
    m["To"] = "b@x"
    m.set_content(body)
    return m


def test_avistamiento_top_level(tmp_path):
    raw = _msg("<a@x>", "Solo").as_bytes()
    p = tmp_path / "2026-06-12_solo.eml"
    p.write_bytes(raw)
    avist = list(E.iter_avistamientos(tmp_path))
    assert len(avist) == 1
    a = avist[0]
    assert a.message_id == "a@x"
    assert a.profundidad == 0
    assert a.eml_origen == "2026-06-12_solo.eml"
    assert a.raw == raw


def test_desciende_en_rfc822_embebido(tmp_path):
    hijo = _msg("<hijo@x>", "Hijo")
    padre = _msg("<padre@x>", "Padre")
    padre.add_attachment(
        hijo.as_bytes(), maintype="message", subtype="rfc822", filename="adj.eml"
    )
    p = tmp_path / "2026-06-12_padre.eml"
    p.write_bytes(padre.as_bytes())
    avist = list(E.iter_avistamientos(tmp_path))
    mids = sorted(a.message_id for a in avist)
    assert mids == ["hijo@x", "padre@x"]
    hijo_av = next(a for a in avist if a.message_id == "hijo@x")
    assert hijo_av.profundidad == 1
    assert hijo_av.ruta_anidacion == ["padre@x"]
