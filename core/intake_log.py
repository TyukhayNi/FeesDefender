"""Log append-only de eventos de intake (M10).

Por cada caso, una línea JSON por evento en
``00_Input/_intake_log.jsonl``. Trazabilidad forense para prueba documental:
quién hizo qué, cuándo y con qué efecto sobre el repositorio del caso.

Decisiones cerradas (memoria persistente: ``project_intake_estructura_v2.md``):

- M10-Q1: 17 tipos de evento permitidos (constante ``INTAKE_EVENTS``).
- M10-Q2: schema común ``{ts, actor, event, case_id, details}`` con
  ``details`` específico por evento.
- M10-Q3: actor resuelto desde un singleton thread-safe (``set_actor`` /
  ``get_actor``). La UI Streamlit sincroniza el actor desde
  ``st.session_state['actor']`` al inicio de cada request (paso 7).
- M10-Q4: ``flush()`` + ``os.fsync()`` tras cada escritura. Append en modo
  ``"a"``. JSONL es resiliente a crashes en escrituras parciales.
- M10-Q5: sin rotación de archivos (rotar por año si llega a ser problema).
- M10-Q6: sin vista UI dedicada — auditoría = abrir el ``.jsonl`` con editor.
- M10-Q7: solo eventos automáticos del código. Anotaciones manuales del
  abogado van a ``90_Notas personales/``, no al log.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .config import caso_path
from .utils import now_iso


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Tipos de evento permitidos (M10-Q1). Set cerrado: añadir un nuevo evento
# aquí + documentar el shape de ``details`` en project_intake_estructura_v2.md
# antes de emitirlo desde el código.
INTAKE_EVENTS: frozenset[str] = frozenset({
    "link_expediente",      # vincular un expediente CRM al caso
    "unlink_expediente",    # desvincular (rara — typo, expediente incorrecto, etc.)
    "pull_crm",             # pull de docs vía sync_sudespacho
    "pull_drive_ev",        # pull de docs vía intake_drive (rclone gdrive_ev)
    "upload_manual",        # upload manual a 04_Manual/
    "upload_email",         # ingest de hilo email a 03_Email/...
    "upload_whatsapp",      # ingest de export WhatsApp a 02_Whatsapp/...
    "upload_entrevista",    # subida grabación + transcripción a 06_Entrevistas/...
    "dedup_skipped",        # M9: doc skipped por SHA-256 ya presente, alias registrado
    "category_unknown",     # crm_branch_path → fallback (M5)
    "overwrite_doc",        # sobrescritura de un fichero existente
    "delete_doc",           # borrado explícito de un fichero
    "migrate_v1_v2",        # migración manual de un caso v1 (sudespacho_*/) a v2
    "intake_judicial",      # intake acotado demanda+contestación (resumen)
    "pendiente_revision",   # rol (demanda/contestación) no resuelto → revisión letrado
    "cross_source_overlap", # doc byte-idéntico a otro ya presente, escrito igualmente (physical_complete)
    "conjunto_detectado",   # D9: lote cabecera+prueba detectado por timestamp ∩ patrón D NN (alta confianza)
})


_LOG_FILENAME = "_intake_log.jsonl"


# ---------------------------------------------------------------------------
# Actor activo (singleton thread-safe)
# ---------------------------------------------------------------------------

# La UI Streamlit lee st.session_state['actor'] al inicio de cada request y
# llama set_actor(). Fuera de Streamlit (CLI / tests / scripts), get_actor()
# resuelve el actor por defecto desde FEESDEFENDER_ACTOR o os.getlogin().

_actor_lock = threading.Lock()
_actor: str | None = None


def _default_actor() -> str:
    """Actor por defecto cuando no se ha llamado ``set_actor()``.

    Orden de resolución:

    1. Variable de entorno ``FEESDEFENDER_ACTOR`` (útil en CI / scripts /
       tareas programadas).
    2. ``os.getlogin()`` — usuario del sistema operativo.
    3. ``"system"`` — fallback genérico.
    """
    env_actor = os.getenv("FEESDEFENDER_ACTOR")
    if env_actor and env_actor.strip():
        return env_actor.strip()
    try:
        return os.getlogin()
    except (OSError, AttributeError):
        return "system"


def set_actor(actor: str | None) -> None:
    """Fija el actor activo (thread-safe).

    Pasar ``None`` o cadena vacía resetea al default. La UI Streamlit
    llama esta función en cada request con el valor del selector
    "Yo soy: Nikolai / Paola / Ana" (M10-Q3).
    """
    global _actor
    with _actor_lock:
        if isinstance(actor, str) and actor.strip():
            _actor = actor.strip()
        else:
            _actor = None


def get_actor() -> str:
    """Devuelve el actor activo. Si ``set_actor`` no se ha llamado, default."""
    with _actor_lock:
        actor = _actor
    return actor or _default_actor()


# ---------------------------------------------------------------------------
# API pública: escritura y lectura
# ---------------------------------------------------------------------------

def log_path(case_id: str) -> Path:
    """Ruta absoluta al log JSONL del caso. No crea el archivo."""
    return caso_path(case_id) / "00_Input" / _LOG_FILENAME


def append_event(
    case_id: str,
    event: str,
    *,
    details: dict[str, Any] | None = None,
    actor: str | None = None,
    ts: str | None = None,
) -> Path:
    """Añade una línea al log JSONL del caso (M10).

    El archivo se crea si no existe. Cada llamada hace ``flush + fsync``
    para resistir crashes (M10-Q4).

    Args:
        case_id: ID del caso. La carpeta ``00_Input/`` se crea si no existe.
        event: Tipo de evento (debe estar en ``INTAKE_EVENTS``).
        details: Payload específico del evento. Default ``{}``. Debe ser
            JSON-serializable.
        actor: Override explícito del actor. Default ``get_actor()``.
        ts: Override explícito del timestamp ISO-8601. Default ``now_iso()``.

    Returns:
        Path al log.

    Raises:
        ValueError: si ``event`` no está en ``INTAKE_EVENTS``.
        TypeError: si ``details`` no es JSON-serializable.
    """
    if event not in INTAKE_EVENTS:
        raise ValueError(
            f"Evento desconocido: {event!r}. "
            f"Eventos válidos: {sorted(INTAKE_EVENTS)}"
        )

    path = log_path(case_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry: dict[str, Any] = {
        "ts": ts or now_iso(),
        "actor": actor or get_actor(),
        "event": event,
        "case_id": case_id,
        "details": details or {},
    }
    line = json.dumps(entry, ensure_ascii=False)

    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())

    return path


def read_events(case_id: str) -> list[dict[str, Any]]:
    """Lee y parsea todas las entradas del log del caso.

    Útil para tests y auditoría manual. Sin enforcement de schema sobre los
    eventos leídos — devuelve cada línea como dict tal cual se persistió.
    Las líneas corruptas se saltan silenciosamente (resiliencia a crashes).

    Returns:
        Lista de eventos en orden cronológico (= orden de escritura).
        Lista vacía si el log no existe o está vacío.
    """
    path = log_path(case_id)
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
