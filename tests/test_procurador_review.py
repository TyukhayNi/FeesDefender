"""Tests de F2.1 — cola de revisión + registro de auditoría (terna §18.9).

La terna es el requisito duro del plan §18.9: por cada decisión de la bandeja
se persiste *propuesta-del-robot vs. acción-confirmada vs. quién-y-cuándo*. Sin
ese registro el check-2 (F6) no tiene contra qué comparar.
"""

from __future__ import annotations

import pytest

from core.intake_log import set_actor
from core.procurador_intake import (
    AttachmentProposal,
    IntakeProposal,
    IntakeSignals,
    MatchResult,
)
from core.procurador_review import (
    HumanAction,
    ReviewDecision,
    ReviewItem,
    RobotProposal,
    TransicionInvalida,
    compute_divergence,
    from_intake_proposal,
    read_decisions,
    record_decision,
    transicionar,
)


def _proposal_alta() -> RobotProposal:
    """Propuesta típica de confianza alta (match exacto por Su ref)."""
    return RobotProposal(
        email_id="m1",
        expediente_id=532,
        confianza="alta",
        carpeta_id=1,
        carpeta="General",
        attachment_names={"adj.pdf": "2026-06-12 - Auto - nombramiento.pdf"},
    )


def test_confirmar_sin_cambios_no_divergencia():
    """Confirmar la propuesta tal cual → cero divergencia (el robot acertó)."""
    proposal = _proposal_alta()
    action = HumanAction(tipo="confirmar")
    assert compute_divergence(proposal, action) == []


def test_cambiar_expediente_marca_divergencia():
    """Reasignar a otro expediente → divergencia en expediente_id (§18.3 item 4)."""
    proposal = _proposal_alta()
    action = HumanAction(tipo="confirmar", expediente_id=999)
    assert compute_divergence(proposal, action) == ["expediente_id"]


def test_cambiar_carpeta_marca_divergencia():
    """Cambiar la carpeta destino → divergencia en carpeta_id."""
    proposal = _proposal_alta()
    action = HumanAction(tipo="confirmar", carpeta_id=308)
    assert compute_divergence(proposal, action) == ["carpeta_id"]


def test_descartar_match_alta_es_divergencia():
    """Descartar un correo que el robot emparejó (alta) es un override (§18.3 item 4)."""
    proposal = _proposal_alta()
    action = HumanAction(tipo="descartar")
    assert compute_divergence(proposal, action) == ["descartado"]


def test_descartar_sin_match_no_es_divergencia():
    """Descartar cuando el robot no propuso expediente → coinciden, sin divergencia."""
    proposal = RobotProposal(
        email_id="m2", expediente_id=None, confianza="ninguna",
        carpeta_id=None, carpeta=None,
    )
    action = HumanAction(tipo="descartar")
    assert compute_divergence(proposal, action) == []


def test_renombrar_adjunto_marca_divergencia():
    """Editar el nombre propuesto de un adjunto → divergencia identificando el fichero."""
    proposal = _proposal_alta()
    action = HumanAction(
        tipo="confirmar",
        attachment_names={"adj.pdf": "2026-06-12 - Auto - otro nombre.pdf"},
    )
    assert compute_divergence(proposal, action) == ["attachment:adj.pdf"]


# ---------------------------------------------------------------------------
# Persistencia de la terna (§18.9)
# ---------------------------------------------------------------------------

def test_record_decision_persiste_la_terna(tmp_path):
    """Registrar una decisión persiste las tres patas y devuelve la divergencia."""
    store = tmp_path / "audit.jsonl"
    proposal = _proposal_alta()
    action = HumanAction(tipo="confirmar", expediente_id=999)

    dec = record_decision(
        proposal, action,
        quien="paola", cuando="2026-06-12T10:00:00+02:00",
        store_path=store,
    )

    assert isinstance(dec, ReviewDecision)
    assert dec.quien == "paola"
    assert dec.cuando == "2026-06-12T10:00:00+02:00"
    assert dec.divergencia == ["expediente_id"]

    entries = read_decisions(store)
    assert len(entries) == 1
    e = entries[0]
    assert e["quien"] == "paola"
    assert e["cuando"] == "2026-06-12T10:00:00+02:00"
    assert e["propuesta"]["email_id"] == "m1"
    assert e["propuesta"]["expediente_id"] == 532
    assert e["accion"]["tipo"] == "confirmar"
    assert e["accion"]["expediente_id"] == 999
    assert e["divergencia"] == ["expediente_id"]


def test_record_decision_es_append(tmp_path):
    """Dos decisiones → dos líneas, en orden cronológico."""
    store = tmp_path / "audit.jsonl"
    record_decision(_proposal_alta(), HumanAction(tipo="confirmar"),
                    quien="ana", cuando="2026-06-12T09:00:00+02:00", store_path=store)
    record_decision(_proposal_alta(), HumanAction(tipo="descartar"),
                    quien="paola", cuando="2026-06-12T11:00:00+02:00", store_path=store)
    entries = read_decisions(store)
    assert [e["quien"] for e in entries] == ["ana", "paola"]


def test_record_decision_actor_por_defecto(tmp_path):
    """Sin ``quien`` explícito, se resuelve desde el actor activo (login)."""
    store = tmp_path / "audit.jsonl"
    set_actor("nikolai")
    try:
        dec = record_decision(_proposal_alta(), HumanAction(tipo="confirmar"),
                              cuando="2026-06-12T12:00:00+02:00", store_path=store)
        assert dec.quien == "nikolai"
    finally:
        set_actor(None)


def test_read_decisions_store_inexistente(tmp_path):
    """Leer un store que no existe → lista vacía, sin reventar."""
    assert read_decisions(tmp_path / "no_existe.jsonl") == []


# ---------------------------------------------------------------------------
# Puente F1 → F2: IntakeProposal (lo que produce el matcher) → RobotProposal
# ---------------------------------------------------------------------------

def test_from_intake_proposal_mapea_los_campos():
    """El RobotProposal recoge expediente/confianza/carpeta/nombres del matcher F1."""
    intake = IntakeProposal(
        signals=IntakeSignals(su_ref="13/2026", num_expediente=13, serie_expediente="2026"),
        match=MatchResult(expediente_id=532, confianza="alta"),
        attachments=[
            AttachmentProposal(
                original_filename="adj.pdf",
                proposed_name="2026-06-12 - Auto - nombramiento.pdf",
                tipo="Auto", fecha="2026-06-12", descripcion="nombramiento",
                confianza=0.9,
            ),
        ],
        carpeta_sugerida="General",
        carpeta_id=1,
    )

    robot = from_intake_proposal("m1", intake)

    assert isinstance(robot, RobotProposal)
    assert robot.email_id == "m1"
    assert robot.expediente_id == 532
    assert robot.confianza == "alta"
    assert robot.carpeta_id == 1
    assert robot.carpeta == "General"
    assert robot.attachment_names == {"adj.pdf": "2026-06-12 - Auto - nombramiento.pdf"}


# ---------------------------------------------------------------------------
# F2.2 — máquina de estados de la cola de revisión
# ---------------------------------------------------------------------------

def _item_pendiente() -> ReviewItem:
    return ReviewItem(email_id="m1", proposal=_proposal_alta(), estado="pendiente")


def test_item_nace_pendiente_por_defecto():
    """Un correo que el robot conserva entra a la bandeja como pendiente."""
    item = ReviewItem(email_id="m1", proposal=_proposal_alta())
    assert item.estado == "pendiente"
    assert item.motivo_descarte is None


def test_pendiente_a_confirmado():
    """Confirmar mueve pendiente → confirmado (estado terminal)."""
    item = transicionar(_item_pendiente(), "confirmar")
    assert item.estado == "confirmado"


def test_pendiente_a_descartado_con_motivo():
    """Descartar mueve pendiente → descartado y guarda el motivo (vista Descartados)."""
    item = transicionar(_item_pendiente(), "descartar", motivo="descartado_humano")
    assert item.estado == "descartado"
    assert item.motivo_descarte == "descartado_humano"


def test_descartado_a_pendiente_por_recuperar():
    """La secretaria recupera un descartado → vuelve a pendiente (§6) y limpia el motivo."""
    descartado = ReviewItem(
        email_id="m1", proposal=_proposal_alta(),
        estado="descartado", motivo_descarte="ruido_llm",
    )
    item = transicionar(descartado, "recuperar")
    assert item.estado == "pendiente"
    assert item.motivo_descarte is None


def test_transicionar_no_muta_el_original():
    """La transición es pura: devuelve un item nuevo, no muta el de entrada."""
    original = _item_pendiente()
    transicionar(original, "confirmar")
    assert original.estado == "pendiente"


def test_confirmado_es_terminal():
    """No se puede salir de confirmado."""
    confirmado = ReviewItem(email_id="m1", proposal=_proposal_alta(), estado="confirmado")
    with pytest.raises(TransicionInvalida):
        transicionar(confirmado, "descartar")


def test_descartado_no_va_directo_a_confirmado():
    """Un descartado debe recuperarse antes de poder confirmarse (reabre triaje, §6)."""
    descartado = ReviewItem(email_id="m1", proposal=_proposal_alta(), estado="descartado")
    with pytest.raises(TransicionInvalida):
        transicionar(descartado, "confirmar")
