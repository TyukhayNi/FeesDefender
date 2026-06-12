"""F2.1 — Cola de revisión + registro de auditoría de la bandeja de procuradores.

Implementa el **requisito duro §18.9** del plan: por cada decisión de la bandeja
se persiste la terna *propuesta-del-robot vs. acción-confirmada vs.
quién-y-cuándo*. Sin ese registro el check-2 (F6) no tiene contra qué comparar.

Es lógica de core (la UI Streamlit de F2.3 orquesta). **Dry-run:** registrar una
decisión NO escribe en el CRM; solo persiste la intención en el log de auditoría
(la escritura real es F3). El store es global (los correos se revisan antes de
asignar caso), vive en ``data/_aprendizaje/`` y lleva PII → gitignored.

RGPD: excepción acotada SOLO a este flujo. Ver
``docs/PLAN_INTAKE_PROCURADORES_EMAIL.md`` §18.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .config import settings
from .intake_log import get_actor
from .utils import now_iso

if TYPE_CHECKING:
    from .procurador_intake import IntakeProposal


# ---------------------------------------------------------------------------
# DTOs de la terna (§18.9)
# ---------------------------------------------------------------------------

@dataclass
class RobotProposal:
    """La pata *propuesta-del-robot* de la terna: lo que F1 propuso para un correo."""
    email_id: str
    expediente_id: int | None
    confianza: str                       # "alta" | "dudosa" | "ninguna"
    carpeta_id: int | None
    carpeta: str | None
    attachment_names: dict[str, str] = field(default_factory=dict)


def from_intake_proposal(email_id: str, proposal: IntakeProposal) -> RobotProposal:
    """Construye la pata *propuesta-del-robot* desde el ``IntakeProposal`` de F1.

    Es el contrato F1→F2: lo que el matcher propone se congela como snapshot para
    la terna, antes de que el humano actúe en la bandeja.
    """
    return RobotProposal(
        email_id=email_id,
        expediente_id=proposal.match.expediente_id,
        confianza=proposal.match.confianza,
        carpeta_id=proposal.carpeta_id,
        carpeta=proposal.carpeta_sugerida,
        attachment_names={
            a.original_filename: a.proposed_name for a in proposal.attachments
        },
    )


@dataclass
class HumanAction:
    """La pata *acción-confirmada* de la terna: lo que el humano decidió.

    ``tipo`` ∈ {"confirmar", "descartar"}. Para "confirmar", los campos override
    a ``None`` significan "acepto el valor del robot"; un valor no nulo sustituye
    al del robot (corrección).
    """
    tipo: str
    expediente_id: int | None = None
    carpeta_id: int | None = None
    carpeta: str | None = None
    attachment_names: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# Divergencia (corazón del check-2, §18.3)
# ---------------------------------------------------------------------------

def compute_divergence(proposal: RobotProposal, action: HumanAction) -> list[str]:
    """Campos en los que la decisión humana difiere de la propuesta del robot.

    Lista vacía = el robot acertó (señal de que se puede auto-aprobar, §18.6).

    - "descartar": divergencia ``["descartado"]`` solo si el robot SÍ había
      propuesto expediente (descartar un match es un override; descartar lo que el
      robot no emparejó coincide con él).
    - "confirmar": cada override no nulo que difiera del valor del robot suma una
      entrada (``expediente_id`` / ``carpeta_id`` / ``attachment:<fichero>``).
    """
    if action.tipo == "descartar":
        return ["descartado"] if proposal.expediente_id is not None else []

    div: list[str] = []
    if action.expediente_id is not None and action.expediente_id != proposal.expediente_id:
        div.append("expediente_id")
    if action.carpeta_id is not None and action.carpeta_id != proposal.carpeta_id:
        div.append("carpeta_id")
    if action.attachment_names is not None:
        for fname, new_name in action.attachment_names.items():
            if new_name != proposal.attachment_names.get(fname):
                div.append(f"attachment:{fname}")
    return div


# ---------------------------------------------------------------------------
# Registro de la terna (§18.9) — persistencia JSONL append-only
# ---------------------------------------------------------------------------

@dataclass
class ReviewDecision:
    """La terna completa §18.9: propuesta-robot vs. acción-confirmada vs. quién-y-cuándo."""
    propuesta: RobotProposal
    accion: HumanAction
    quien: str
    cuando: str
    divergencia: list[str] = field(default_factory=list)


def audit_log_path() -> Path:
    """Store global de auditoría de la bandeja (PII → gitignored).

    Vive en ``data/_aprendizaje/`` junto al resto de artefactos de intake. Es
    global (los correos se revisan antes de asignar caso), a diferencia del log
    por-caso ``00_Input/_intake_log.jsonl``.
    """
    return settings.project_root / "data" / "_aprendizaje" / "intake_audit.jsonl"


def record_decision(
    proposal: RobotProposal,
    action: HumanAction,
    *,
    quien: str | None = None,
    cuando: str | None = None,
    store_path: Path | str | None = None,
) -> ReviewDecision:
    """Registra una decisión de la bandeja persistiendo la terna (§18.9).

    **Dry-run:** NO escribe en el CRM; solo persiste la intención en el log de
    auditoría. La escritura real es F3.

    Args:
        proposal: lo que F1 propuso (pata *propuesta-del-robot*).
        action: lo que decidió el humano (pata *acción-confirmada*).
        quien: actor. Default = actor activo (``get_actor()``, reusado del log
            por-caso; la UI lo fija con el login por persona, §18.8).
        cuando: timestamp ISO. Default ``now_iso()``.
        store_path: override del store (tests). Default ``audit_log_path()``.

    Returns:
        La ``ReviewDecision`` con la divergencia ya computada.
    """
    quien = quien or get_actor()
    cuando = cuando or now_iso()
    divergencia = compute_divergence(proposal, action)

    decision = ReviewDecision(
        propuesta=proposal,
        accion=action,
        quien=quien,
        cuando=cuando,
        divergencia=divergencia,
    )

    path = Path(store_path) if store_path is not None else audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    entry: dict[str, Any] = {
        "cuando": cuando,
        "quien": quien,
        "propuesta": asdict(proposal),
        "accion": asdict(action),
        "divergencia": divergencia,
    }
    line = json.dumps(entry, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())

    return decision


def read_decisions(store_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Lee todas las decisiones del log de auditoría, en orden cronológico.

    Líneas corruptas se saltan (resiliencia a crashes). Store inexistente → [].
    """
    path = Path(store_path) if store_path is not None else audit_log_path()
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                out.append(entry)
    return out


# ---------------------------------------------------------------------------
# F2.2 — máquina de estados de la cola de revisión
# ---------------------------------------------------------------------------

ESTADOS_COLA: frozenset[str] = frozenset({"pendiente", "confirmado", "descartado"})

# Motivos de descarte (plan §6). El robot auto-descarta a la vista "Descartados"
# sin hard-drop; el humano también puede descartar desde el triaje.
MOTIVOS_DESCARTE: frozenset[str] = frozenset({
    "ruido_llm",                 # el LLM lo marcó es_ruido
    "remitente_no_procurador",   # remitente no reconocido
    "sin_su_ref_ni_hilo",        # sin señal para emparejar
    "descartado_humano",         # la persona lo descartó en el triaje
})


class TransicionInvalida(ValueError):
    """Transición de estado no permitida por la máquina de estados de la cola."""


@dataclass
class ReviewItem:
    """Un correo en la cola de la bandeja: propuesta del robot + estado de revisión.

    ``estado`` ∈ ``ESTADOS_COLA``. ``motivo_descarte`` solo tiene sentido en
    ``descartado`` (de dónde vino → vista "Descartados", §6). Los campos de
    cabecera (remitente/asunto/fecha) son para mostrar en la tarjeta.
    """
    email_id: str
    proposal: RobotProposal
    estado: str = "pendiente"
    motivo_descarte: str | None = None
    remitente: str | None = None
    asunto: str | None = None
    fecha: str | None = None


# Transiciones permitidas: estado actual → {acción: nuevo estado}. ``confirmado``
# es terminal; ``descartado`` solo sale por ``recuperar`` (reabre el triaje, §6),
# nunca directo a ``confirmado``.
_TRANSICIONES: dict[str, dict[str, str]] = {
    "pendiente": {"confirmar": "confirmado", "descartar": "descartado"},
    "descartado": {"recuperar": "pendiente"},
    "confirmado": {},
}


def transicionar(item: ReviewItem, accion: str, *, motivo: str | None = None) -> ReviewItem:
    """Aplica una transición de estado y devuelve un ``ReviewItem`` nuevo (puro).

    Args:
        item: item de la cola.
        accion: "confirmar" | "descartar" | "recuperar".
        motivo: motivo de descarte (solo al descartar; se ignora en el resto).

    Raises:
        TransicionInvalida: si la acción no está permitida desde ``item.estado``.
    """
    permitidas = _TRANSICIONES.get(item.estado, {})
    if accion not in permitidas:
        raise TransicionInvalida(
            f"Transición no permitida: {item.estado!r} --{accion}--> ?"
        )
    nuevo_estado = permitidas[accion]
    nuevo_motivo = motivo if nuevo_estado == "descartado" else None
    return replace(item, estado=nuevo_estado, motivo_descarte=nuevo_motivo)
