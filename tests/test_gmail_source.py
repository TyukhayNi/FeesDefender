"""Tests del adaptador Gmail (F2) — parser de mensajes de la API → EmailMessage.

La capa pura (parsear el dict que devuelve ``users.messages.get(format='full')``)
no necesita red ni librerías Google. La capa de fetch (auth + llamada API) es glue
fino y se prueba aparte / a mano contra tokens reales.

Clave del §4: ``email_id`` = cabecera **Message-ID** (estable entre los 4 buzones),
no el id por-cuenta de Gmail — así el mismo correo en varias bandejas se dedup.
"""

from __future__ import annotations

import base64

from core.gmail_source import gmail_message_to_email
from core.procurador_runner import EmailMessage


def _b64url(text: str) -> str:
    """Codifica como la Gmail API (base64url)."""
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def _raw_multipart(message_id: str = "<abc@mail.gmail.com>") -> dict:
    return {
        "id": "gmail-internal-id-1",
        "threadId": "thread-1",
        "internalDate": "1718200000000",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "ProcuradoraF <proc-f@colegio-proc.example>"},
                {"name": "Subject", "value": "Notificación autos 21/25"},
                {"name": "Message-ID", "value": message_id},
                {"name": "Date", "value": "Thu, 12 Jun 2026 10:00:00 +0200"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64url("Cuerpo del correo procesal.")}},
                {"mimeType": "text/html", "body": {"data": _b64url("<p>html</p>")}},
            ],
        },
    }


def test_parsea_cabeceras_y_cuerpo():
    """Extrae from/subject/date, cuerpo text/plain decodificado y Message-ID como email_id."""
    item = gmail_message_to_email(_raw_multipart(), mailbox="procesal@tyukhay.legal")

    assert isinstance(item, EmailMessage)
    assert item.email_id == "abc@mail.gmail.com"          # Message-ID sin <>
    assert item.from_addr == "ProcuradoraF <proc-f@colegio-proc.example>"
    assert item.subject == "Notificación autos 21/25"
    assert item.body == "Cuerpo del correo procesal."
    assert item.date == "Thu, 12 Jun 2026 10:00:00 +0200"
    assert item.mailbox == "procesal@tyukhay.legal"


def test_mensaje_simple_sin_parts():
    """Mensaje text/plain plano (body directo en payload, sin multipart)."""
    raw = {
        "id": "g1",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "x@procuradores-b.example"},
                {"name": "Subject", "value": "Su ref 33/2024"},
                {"name": "Message-ID", "value": "<simple@x>"},
            ],
            "body": {"data": _b64url("Texto plano directo.")},
        },
    }
    item = gmail_message_to_email(raw)
    assert item.body == "Texto plano directo."
    assert item.email_id == "simple@x"
    assert item.date is None


def test_sin_message_id_usa_id_de_gmail():
    """Si no hay cabecera Message-ID, cae al id por-cuenta de Gmail (mejor que nada)."""
    raw = {
        "id": "gmail-fallback-id",
        "payload": {
            "mimeType": "text/plain",
            "headers": [{"name": "From", "value": "x@procuradores-a.example"}],
            "body": {"data": _b64url("cuerpo")},
        },
    }
    item = gmail_message_to_email(raw)
    assert item.email_id == "gmail-fallback-id"


def test_multipart_anidado():
    """multipart/mixed que envuelve un multipart/alternative: encuentra el text/plain."""
    raw = {
        "id": "g2",
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [{"name": "Message-ID", "value": "<nested@x>"}],
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {"mimeType": "text/plain", "body": {"data": _b64url("cuerpo anidado")}},
                        {"mimeType": "text/html", "body": {"data": _b64url("<p>x</p>")}},
                    ],
                },
                {"mimeType": "application/pdf", "filename": "adj.pdf", "body": {"attachmentId": "att1"}},
            ],
        },
    }
    item = gmail_message_to_email(raw)
    assert item.body == "cuerpo anidado"


# ---------------------------------------------------------------------------
# Capa de fetch — orquestación list→get→parse (service inyectado, sin red)
# ---------------------------------------------------------------------------

class _FakeExec:
    def __init__(self, result): self._r = result
    def execute(self): return self._r


class _FakeMessages:
    def __init__(self, listing, msgs):
        self._listing, self._msgs = listing, msgs
        self.got = []
    def list(self, **kw): return _FakeExec(self._listing)
    def get(self, *, userId, id, format):
        self.got.append(id)
        return _FakeExec(self._msgs[id])


class _FakeService:
    """Imita la interfaz fluida de googleapiclient (boundary de red)."""
    def __init__(self, listing, msgs):
        self._messages = _FakeMessages(listing, msgs)
    def users(self):
        outer = self
        class _U:
            def messages(self_inner): return outer._messages
        return _U()


def test_fetch_emails_lista_y_parsea():
    """Lista mensajes, pide cada uno en full, parsea y etiqueta el buzón."""
    from core.gmail_source import fetch_emails
    listing = {"messages": [{"id": "g1"}, {"id": "g2"}]}
    msgs = {"g1": _raw_multipart("<a@x>"), "g2": _raw_multipart("<b@x>")}
    service = _FakeService(listing, msgs)

    out = fetch_emails(account="procesal@tyukhay.legal", service=service)

    assert [e.email_id for e in out] == ["a@x", "b@x"]
    assert all(e.mailbox == "procesal@tyukhay.legal" for e in out)


def test_fetch_emails_sin_mensajes():
    """Listado vacío → lista vacía, sin pedir ningún mensaje."""
    from core.gmail_source import fetch_emails
    service = _FakeService({}, {})
    assert fetch_emails(account="procesal@tyukhay.legal", service=service) == []


# ---------------------------------------------------------------------------
# Puente adaptador → runner: fetch_and_run (multi-buzón + dedup §4)
# ---------------------------------------------------------------------------

def test_fetch_and_run_combina_buzones_y_dedup(tmp_path):
    """Trae de varios buzones, combina y deduplica el mismo Message-ID (§4)."""
    from core.gmail_source import fetch_and_run
    from core.procurador_intake import IntakeSignals, MatchResult
    from core.procurador_review import load_queue

    # El mismo correo (id 'shared@x') llega a procesal y a nikolai; 'solo@x' solo a uno.
    por_buzon = {
        "procesal@tyukhay.legal": [
            EmailMessage("shared@x", "proc-f@colegio-proc.example", "21/25", "c"),
            EmailMessage("solo@x", "proc-f@colegio-proc.example", "22/25", "c"),
        ],
        "nikolai.tyukhay@tyukhay.legal": [
            EmailMessage("shared@x", "proc-f@colegio-proc.example", "21/25", "c"),
        ],
    }
    fake_fetch = lambda account, **kw: por_buzon.get(account, [])
    signals = IntakeSignals(su_ref="21/25", num_expediente=21, serie_expediente="2025")

    procesados = fetch_and_run(
        accounts=("procesal@tyukhay.legal", "nikolai.tyukhay@tyukhay.legal"),
        store_path=tmp_path / "cola.jsonl",
        fetch_fn=fake_fetch,
        extract_fn=lambda *a, **k: signals,
        match_fn=lambda *a, **k: MatchResult(expediente_id=532, confianza="alta"),
    )

    # 'shared@x' una sola vez pese a estar en dos buzones + 'solo@x'
    assert {i.email_id for i in procesados} == {"shared@x", "solo@x"}
    assert len(load_queue(store_path=tmp_path / "cola.jsonl")) == 2
