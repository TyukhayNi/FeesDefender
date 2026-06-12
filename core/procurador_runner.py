"""F2.4 — Runner de ingesta de correos de procuradores → cola de la bandeja.

El "robot independiente" del plan §3: dado un lote de correos entrantes, corre el
matcher F1 (``core.procurador_intake``) y puebla la cola de revisión
(``core.procurador_review``). **Dry-run:** NO escribe en el CRM; solo deja items
en la cola para que una persona los confirme en la bandeja (F2.3b).

La fuente de correo (gmail / IMAP) se inyecta como un iterable de ``EmailMessage``
— el adaptador real es glue fino y queda fuera de este módulo, que así es
testeable sin red. El extractor de señales y el matcher también se inyectan.

RGPD: excepción acotada SOLO a este flujo. Ver
``docs/PLAN_INTAKE_PROCURADORES_EMAIL.md`` §3-§6.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .procurador_intake import (
    IntakeProposal,
    extract_signals,
    is_procurador_email,
    match_expediente,
)
from .procurador_review import (
    ReviewItem,
    RobotProposal,
    from_intake_proposal,
    load_queue,
    upsert_queue_item,
)


@dataclass
class EmailMessage:
    """Correo entrante mínimo para el runner."""
    email_id: str
    from_addr: str
    subject: str
    body: str
    date: str | None = None
    mailbox: str | None = None
    attachment_texts: list[str] = field(default_factory=list)


def _descartado(email: EmailMessage, motivo: str) -> ReviewItem:
    """Construye un item descartado (a la vista Descartados §6, sin hard-drop)."""
    return ReviewItem(
        email_id=email.email_id,
        proposal=RobotProposal(
            email_id=email.email_id,
            expediente_id=None,
            confianza="ninguna",
            carpeta_id=None,
            carpeta=None,
        ),
        estado="descartado",
        motivo_descarte=motivo,
        remitente=email.from_addr,
        asunto=email.subject,
        fecha=email.date,
    )


def process_email(
    email: EmailMessage,
    *,
    extract_fn=extract_signals,
    match_fn=match_expediente,
    llm_config=None,
    sudo_client=None,
) -> ReviewItem:
    """Procesa un correo → ``ReviewItem`` (sin escribir en el CRM).

    El extractor (``extract_fn``) y el matcher (``match_fn``) se inyectan para
    testear sin red; por defecto son los de F1.
    """
    if not is_procurador_email(email.from_addr):
        return _descartado(email, "remitente_no_procurador")

    signals = extract_fn(
        email.subject, email.body,
        attachment_texts=email.attachment_texts or None,
        llm_config=llm_config,
    )

    # es_ruido es ADVISORY (F1): solo descarta si además NO hay Su ref resoluble.
    if signals.es_ruido and not signals.su_ref:
        return _descartado(email, "ruido_llm")

    match = match_fn(signals, sudo_client=sudo_client)

    # Sin ninguna señal de triaje ni match → nada que hacer en la bandeja.
    if not _has_triage_signal(signals) and match.expediente_id is None:
        return _descartado(email, "sin_su_ref_ni_hilo")

    # Pendiente: alta / dudosa / sin-match-con-señales (tarjeta 🔴) — la persona
    # decide en la bandeja. El renombrado de adjuntos llega en F4.
    proposal = IntakeProposal(
        signals=signals,
        match=match,
        attachments=[],
        carpeta_sugerida=None,
        carpeta_id=None,
    )
    return ReviewItem(
        email_id=email.email_id,
        proposal=from_intake_proposal(email.email_id, proposal),
        estado="pendiente",
        motivo_descarte=None,
        remitente=email.from_addr,
        asunto=email.subject,
        fecha=email.date,
    )


def _has_triage_signal(signals) -> bool:
    """¿El correo trae alguna señal para triar? (Su ref, contrario, juzgado, autos)."""
    return any((
        signals.su_ref,
        signals.contrario,
        signals.juzgado,
        signals.num_asunto,
    ))


def run_intake(
    emails,
    *,
    store_path=None,
    extract_fn=extract_signals,
    match_fn=match_expediente,
    llm_config=None,
    sudo_client=None,
) -> list[ReviewItem]:
    """Procesa un lote de correos y los persiste en la cola. **Dry-run.**

    Anti-duplicado §4: salta los ``email_id`` ya presentes en la cola y los
    repetidos dentro del mismo lote (el mismo correo llega a los 4 buzones del
    despacho). El ``email_id`` debe ser el Message-ID RFC (estable entre buzones).

    Returns:
        Los items realmente procesados en esta corrida (sin los saltados).
    """
    vistos = {i.email_id for i in load_queue(store_path=store_path)}
    procesados: list[ReviewItem] = []
    for email in emails:
        if email.email_id in vistos:
            continue
        item = process_email(
            email,
            extract_fn=extract_fn,
            match_fn=match_fn,
            llm_config=llm_config,
            sudo_client=sudo_client,
        )
        upsert_queue_item(item, store_path=store_path)
        vistos.add(email.email_id)
        procesados.append(item)
    return procesados
