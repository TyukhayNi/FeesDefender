"""Smoke del CLI de ingesta de procuradores (dry-run, fetch inyectado)."""

from __future__ import annotations

from core.procurador_runner import EmailMessage, ReviewItem
from core.procurador_review import RobotProposal
from scripts.intake_procuradores import resumen_recuentos


def _item(email_id, confianza, estado="pendiente", motivo=None):
    return ReviewItem(
        email_id=email_id,
        proposal=RobotProposal(email_id=email_id, expediente_id=None,
                               confianza=confianza, carpeta_id=None, carpeta=None),
        estado=estado, motivo_descarte=motivo,
    )


def test_resumen_recuentos_agrupa_por_estado_y_confianza():
    items = [
        _item("a", "alta"),
        _item("b", "dudosa"),
        _item("c", "ninguna"),
        _item("d", "ninguna", estado="descartado", motivo="ruido_llm"),
        _item("e", "ninguna", estado="descartado", motivo="remitente_no_procurador"),
    ]
    res = resumen_recuentos(items)
    assert res["total"] == 5
    assert res["pendiente"]["alta"] == 1
    assert res["pendiente"]["dudosa"] == 1
    assert res["pendiente"]["ninguna"] == 1
    assert res["descartado"]["ruido_llm"] == 1
    assert res["descartado"]["remitente_no_procurador"] == 1
