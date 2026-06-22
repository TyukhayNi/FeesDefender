"""Helper PURO de trazabilidad de intake (sin IO, sin import core).

Construye la línea JSONL de un evento `upload_*` espejando el esquema de
`core/intake_log.py::append_event` ({ts, actor, event, case_id, details}).
Puro → ejecutable en el sandbox de Cowork; el agente escribe la línea en el
Drive con el `append_text` del conector expedientes-xl. La paridad con core se
verifica en tests/test_intake_traza.py (gate anti-drift).
"""
from __future__ import annotations

import json
from typing import Any

# Subconjunto de core.intake_log.INTAKE_EVENTS relevante para depósito de ficheros.
# El test de paridad exige que sea subconjunto del set real de core.
UPLOAD_EVENTS: frozenset[str] = frozenset({
    "upload_manual",
    "upload_email",
    "upload_whatsapp",
    "upload_entrevista",
    "pull_drive_ev",
})


def build_upload_event(
    *,
    case_id: str,
    event: str,
    files: list[dict[str, Any]],
    actor: str,
    ts: str,
) -> str:
    """Devuelve la línea JSONL (con '\\n') de un evento de depósito.

    `files`: lista de {"path": <relativo a 00_Input, posix>, "sha256": <hex>}.
    `event`: debe estar en UPLOAD_EVENTS. `ts`: ISO-8601 (lo provee el caller).
    """
    if event not in UPLOAD_EVENTS:
        raise ValueError(f"Evento de depósito desconocido: {event!r}")
    entry = {
        "ts": ts,
        "actor": actor,
        "event": event,
        "case_id": case_id,
        "details": {"count": len(files), "files": files},
    }
    return json.dumps(entry, ensure_ascii=False) + "\n"


def is_duplicate(log_text: str, sha256: str) -> bool:
    """True si `sha256` ya aparece en algún evento de depósito del log JSONL.

    Tolerante a líneas corruptas (las salta), como core.intake_log.read_events.
    """
    if not sha256:
        return False
    for raw in log_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        for f in entry.get("details", {}).get("files", []):
            if isinstance(f, dict) and f.get("sha256") == sha256:
                return True
    return False
