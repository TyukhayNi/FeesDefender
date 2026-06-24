from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import headers as H


def _raw(**hdrs) -> bytes:
    m = EmailMessage()
    for k, v in hdrs.items():
        m[k.replace("_", "-")] = v
    m.set_content("hola")
    return m.as_bytes()


def test_parse_direcciones_y_listas():
    raw = _raw(
        Message_ID="<a@x>", Subject="Asunto", Date="Thu, 12 Jun 2026 10:30:00 +0200",
        From="PersonaUno <per01c@example.invalid>", To="uno@x, Dos <dos@x>", Cc="tres@x",
        In_Reply_To="<prev@x>", References="<root@x> <prev@x>",
    )
    c = H.parse_cabeceras(raw)
    assert c.rfc_message_id == "a@x"
    assert c.de == "per01c@example.invalid"
    assert c.de_nombre == "PersonaUno"
    assert c.para == ["uno@x", "dos@x"]
    assert c.cc == ["tres@x"]
    assert c.asunto == "Asunto"
    assert c.in_reply_to == "prev@x"
    assert c.fecha_iso == "2026-06-12"
    assert c.hora == "1030"            # Europe/Madrid
    assert c.hilo == "root@x"          # raíz de References


def test_hilo_fallback_a_propio_message_id():
    raw = _raw(Message_ID="<solo@x>", Subject="X", Date="Thu, 12 Jun 2026 10:00:00 +0200",
               From="a@x", To="b@x")
    c = H.parse_cabeceras(raw)
    assert c.hilo == "solo@x"


def test_auth_y_dispositivo():
    raw = _raw(
        Message_ID="<a@x>", Subject="X", Date="Thu, 12 Jun 2026 10:00:00 +0200",
        From="a@x", To="b@x", X_Mailer="iPhone Mail (21G93)",
        Authentication_Results="mx.google.com; dkim=pass; spf=pass; dmarc=pass",
    )
    c = H.parse_cabeceras(raw)
    assert c.auth["dkim"] == "pass"
    assert c.auth["spf"] == "pass"
    assert c.auth["dmarc"] == "pass"
    assert "iPhone" in c.emisor_dispositivo
