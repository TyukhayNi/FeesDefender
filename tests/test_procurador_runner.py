"""Tests de F2.4 — runner de ingesta (correo → cola de la bandeja).

El runner es el "robot independiente" del plan §3: trae correos, corre el
matcher F1 y puebla la cola (dry-run, NO escribe en el CRM). El extractor de
señales y el matcher se inyectan para testear sin red.

Reglas de estado (plan §6):
- Remitente no procurador → descartado / remitente_no_procurador (Descartados).
- es_ruido sin Su ref resoluble → descartado / ruido_llm.
- Resto (incl. sin match = tarjeta 🔴 "sin expediente") → pendiente.
- Descarte automático NUNCA es hard-drop: va a la cola como descartado.
"""

from __future__ import annotations

from core.procurador_intake import IntakeSignals, MatchResult
from core.procurador_review import load_queue
from core.procurador_runner import EmailMessage, process_email, run_intake


def _no_llm(*_a, **_k):
    raise AssertionError("no debería invocarse el LLM en este camino")


def test_remitente_no_procurador_va_a_descartados():
    """Un correo de un remitente desconocido se descarta (sin tocar el LLM)."""
    email = EmailMessage(
        email_id="m1",
        from_addr="newsletter@randomshop.com",
        subject="Ofertas de verano",
        body="...",
    )
    item = process_email(email, extract_fn=_no_llm, match_fn=_no_llm)

    assert item.estado == "descartado"
    assert item.motivo_descarte == "remitente_no_procurador"
    assert item.email_id == "m1"


def _fake_extract(signals: IntakeSignals):
    return lambda *a, **k: signals


def _fake_match(match: MatchResult):
    return lambda *a, **k: match


def test_procurador_match_alta_queda_pendiente():
    """Procurador con Su ref que casa un expediente → pendiente (tarjeta 🟢)."""
    email = EmailMessage("m1", "proc-f@colegio-proc.example", "Notificación 21/25", "cuerpo")
    signals = IntakeSignals(su_ref="21/25", num_expediente=21, serie_expediente="2025")
    match = MatchResult(expediente_id=532, confianza="alta")
    item = process_email(email, extract_fn=_fake_extract(signals), match_fn=_fake_match(match))

    assert item.estado == "pendiente"
    assert item.motivo_descarte is None
    assert item.proposal.expediente_id == 532
    assert item.proposal.confianza == "alta"
    assert item.remitente == "proc-f@colegio-proc.example"
    assert item.asunto == "Notificación 21/25"


def test_procurador_ruido_sin_suref_va_a_descartados():
    """Procurador pero es_ruido y sin Su ref → descartado / ruido_llm (recuperable)."""
    email = EmailMessage("m2", "proc-f@colegio-proc.example", "Saludo", "feliz navidad")
    signals = IntakeSignals(su_ref=None, es_ruido=True)
    match = MatchResult(confianza="ninguna", senales_usadas=["es_ruido"])
    item = process_email(email, extract_fn=_fake_extract(signals), match_fn=_fake_match(match))

    assert item.estado == "descartado"
    assert item.motivo_descarte == "ruido_llm"


def test_procurador_suref_sin_match_queda_pendiente():
    """Su ref presente pero sin expediente → pendiente (tarjeta 🔴, humano asigna)."""
    email = EmailMessage("m3", "proc-f@colegio-proc.example", "Autos 99/2099", "cuerpo")
    signals = IntakeSignals(su_ref="99/2099", num_expediente=99, serie_expediente="2099")
    match = MatchResult(confianza="ninguna", senales_usadas=["su_ref_sin_match"])
    item = process_email(email, extract_fn=_fake_extract(signals), match_fn=_fake_match(match))

    assert item.estado == "pendiente"
    assert item.proposal.confianza == "ninguna"


def test_procurador_sin_senal_alguna_va_a_descartados():
    """Procurador pero sin ninguna señal de triaje → descartado / sin_su_ref_ni_hilo."""
    email = EmailMessage("m4", "proc-f@colegio-proc.example", "", "ok")
    signals = IntakeSignals()  # todo None, es_ruido False
    match = MatchResult(confianza="ninguna")
    item = process_email(email, extract_fn=_fake_extract(signals), match_fn=_fake_match(match))

    assert item.estado == "descartado"
    assert item.motivo_descarte == "sin_su_ref_ni_hilo"


# ---------------------------------------------------------------------------
# F2.4 — orquestador de lote (run_intake) + dedup §4
# ---------------------------------------------------------------------------

def test_run_intake_puebla_la_cola(tmp_path):
    """Procesa un lote mixto y lo persiste: procurador→pendiente, ajeno→descartado."""
    store = tmp_path / "cola.jsonl"
    emails = [
        EmailMessage("m1", "proc-f@colegio-proc.example", "21/25", "cuerpo"),
        EmailMessage("m2", "ads@randomshop.com", "Ofertas", "cuerpo"),
    ]
    signals = IntakeSignals(su_ref="21/25", num_expediente=21, serie_expediente="2025")
    items = run_intake(
        emails, store_path=store,
        extract_fn=_fake_extract(signals),
        match_fn=_fake_match(MatchResult(expediente_id=532, confianza="alta")),
    )

    assert {i.email_id: i.estado for i in items} == {"m1": "pendiente", "m2": "descartado"}
    assert len(load_queue(store_path=store)) == 2


def test_run_intake_dedup_no_reprocesa_lo_ya_en_cola(tmp_path):
    """Un correo ya en la cola no se reprocesa en la siguiente corrida (anti-duplicado §4)."""
    store = tmp_path / "cola.jsonl"
    signals = IntakeSignals(su_ref="21/25", num_expediente=21, serie_expediente="2025")
    ex, ma = _fake_extract(signals), _fake_match(MatchResult(expediente_id=532, confianza="alta"))

    run_intake([EmailMessage("m1", "proc-f@colegio-proc.example", "21/25", "c")], store_path=store, extract_fn=ex, match_fn=ma)
    nuevos = run_intake(
        [EmailMessage("m1", "proc-f@colegio-proc.example", "21/25", "c"),
         EmailMessage("m3", "proc-f@colegio-proc.example", "21/25", "c")],
        store_path=store, extract_fn=ex, match_fn=ma,
    )

    assert {i.email_id for i in nuevos} == {"m3"}        # m1 saltado
    assert len(load_queue(store_path=store)) == 2        # m1 + m3, sin duplicar


def test_run_intake_dedup_dentro_del_mismo_lote(tmp_path):
    """El mismo email_id repetido en el lote (4 buzones) se procesa una sola vez (§4)."""
    store = tmp_path / "cola.jsonl"
    signals = IntakeSignals(su_ref="21/25", num_expediente=21, serie_expediente="2025")
    ex, ma = _fake_extract(signals), _fake_match(MatchResult(expediente_id=532, confianza="alta"))

    items = run_intake(
        [EmailMessage("m1", "proc-f@colegio-proc.example", "21/25", "c", mailbox="ana"),
         EmailMessage("m1", "proc-f@colegio-proc.example", "21/25", "c", mailbox="paola")],
        store_path=store, extract_fn=ex, match_fn=ma,
    )
    assert len(items) == 1
    assert len(load_queue(store_path=store)) == 1
