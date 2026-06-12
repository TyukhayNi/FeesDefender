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
    load_queue,
    read_decisions,
    record_decision,
    transicionar,
    upsert_queue_item,
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


# ---------------------------------------------------------------------------
# F2.3a — store de la cola (persistir/cargar ReviewItems)
# ---------------------------------------------------------------------------

def test_upsert_y_load_reconstruye_review_item(tmp_path):
    """Persistir un item y cargarlo lo reconstruye como ReviewItem con su RobotProposal."""
    store = tmp_path / "cola.jsonl"
    item = ReviewItem(
        email_id="m1", proposal=_proposal_alta(), estado="pendiente",
        remitente="proc-f@colegio-proc.example", asunto="Notificación", fecha="2026-06-12",
    )
    upsert_queue_item(item, store_path=store)

    cola = load_queue(store_path=store)
    assert len(cola) == 1
    cargado = cola[0]
    assert isinstance(cargado, ReviewItem)
    assert isinstance(cargado.proposal, RobotProposal)
    assert cargado.email_id == "m1"
    assert cargado.estado == "pendiente"
    assert cargado.proposal.expediente_id == 532
    assert cargado.remitente == "proc-f@colegio-proc.example"


def test_upsert_mismo_email_id_no_duplica_y_gana_el_ultimo(tmp_path):
    """Anti-duplicado §4: re-upsert del mismo email_id actualiza, no duplica."""
    store = tmp_path / "cola.jsonl"
    item = ReviewItem(email_id="m1", proposal=_proposal_alta(), estado="pendiente")
    upsert_queue_item(item, store_path=store)
    # tras una transición, se vuelve a persistir el mismo correo
    upsert_queue_item(transicionar(item, "confirmar"), store_path=store)

    cola = load_queue(store_path=store)
    assert len(cola) == 1
    assert cola[0].estado == "confirmado"


def test_load_queue_filtra_por_estado(tmp_path):
    """La bandeja principal carga pendientes; la vista Descartados, descartados."""
    store = tmp_path / "cola.jsonl"
    upsert_queue_item(ReviewItem(email_id="a", proposal=_proposal_alta(), estado="pendiente"), store_path=store)
    upsert_queue_item(ReviewItem(email_id="b", proposal=_proposal_alta(), estado="descartado", motivo_descarte="ruido_llm"), store_path=store)
    upsert_queue_item(ReviewItem(email_id="c", proposal=_proposal_alta(), estado="pendiente"), store_path=store)

    pendientes = load_queue(estado="pendiente", store_path=store)
    descartados = load_queue(estado="descartado", store_path=store)
    assert {i.email_id for i in pendientes} == {"a", "c"}
    assert {i.email_id for i in descartados} == {"b"}
    assert descartados[0].motivo_descarte == "ruido_llm"


def test_load_queue_store_inexistente(tmp_path):
    """Cargar una cola que no existe → lista vacía."""
    assert load_queue(store_path=tmp_path / "no.jsonl") == []


# ---------------------------------------------------------------------------
# Contexto de la tarjeta persistido en la cola (§18.6)
# ---------------------------------------------------------------------------

def test_from_intake_proposal_copia_contexto_de_la_tarjeta():
    """from_intake_proposal congela señales + datos_expediente + coincidencias."""
    signals = IntakeSignals(
        su_ref="13/2026", num_expediente=13, serie_expediente="2026",
        contrario="ACME S.L.", juzgado="JPI nº 4 de Valencia",
        num_asunto="123/2025", tipo_procedimiento="ordinario",
        tipo_actuacion="auto",
    )
    match = MatchResult(
        expediente_id=532, confianza="alta",
        datos_expediente={"id": 532, "num_expediente": 13, "serie_expediente": "2026",
                          "juzgado": "JPI 4 Valencia"},
        senales_usadas=["su_ref", "num_expediente", "serie_expediente"],
    )
    proposal = IntakeProposal(signals=signals, match=match, attachments=[],
                              carpeta_sugerida="General", carpeta_id=1)

    robot = from_intake_proposal("m1", proposal)

    assert robot.signals["su_ref"] == "13/2026"
    assert robot.signals["contrario"] == "ACME S.L."
    assert "raw_llm" not in robot.signals          # no se persiste el JSON del LLM
    assert robot.datos_expediente["num_expediente"] == 13
    # coincidencias = solo los nombres de campo (sin tokens de control "su_ref")
    assert set(robot.coincidencias) == {"num_expediente", "serie_expediente"}


def test_robot_proposal_contexto_default_vacio():
    """Construir un RobotProposal sin contexto → dicts/listas vacías (retrocompat)."""
    robot = RobotProposal(email_id="m9", expediente_id=None, confianza="ninguna",
                          carpeta_id=None, carpeta=None)
    assert robot.signals == {}
    assert robot.datos_expediente == {}
    assert robot.coincidencias == []


def test_cola_round_trip_conserva_contexto(tmp_path):
    """upsert + load preserva señales/datos/coincidencias del snapshot."""
    store = tmp_path / "cola.jsonl"
    robot = RobotProposal(
        email_id="m1", expediente_id=532, confianza="alta", carpeta_id=1,
        carpeta="General",
        signals={"su_ref": "13/2026", "contrario": "ACME S.L."},
        datos_expediente={"id": 532, "juzgado": "JPI 4 Valencia"},
        coincidencias=["num_expediente"],
    )
    item = ReviewItem(email_id="m1", proposal=robot, estado="pendiente",
                      remitente="p@x.com", asunto="13/2026", fecha="2026-06-12")
    upsert_queue_item(item, store_path=store)

    loaded = load_queue(store_path=store)
    assert len(loaded) == 1
    p = loaded[0].proposal
    assert p.signals["contrario"] == "ACME S.L."
    assert p.datos_expediente["juzgado"] == "JPI 4 Valencia"
    assert p.coincidencias == ["num_expediente"]


def test_cola_load_item_viejo_sin_contexto(tmp_path):
    """Un item persistido SIN los campos nuevos se relee con defaults vacíos."""
    store = tmp_path / "cola.jsonl"
    # Línea "vieja": proposal sin signals/datos_expediente/coincidencias.
    store.write_text(
        '{"email_id": "m1", "estado": "pendiente", "proposal": '
        '{"email_id": "m1", "expediente_id": 5, "confianza": "alta", '
        '"carpeta_id": 1, "carpeta": "General", "attachment_names": {}}}\n',
        encoding="utf-8",
    )
    loaded = load_queue(store_path=store)
    assert loaded[0].proposal.signals == {}
    assert loaded[0].proposal.datos_expediente == {}
    assert loaded[0].proposal.coincidencias == []
