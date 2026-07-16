"""Auditoría de operaciones mutantes: JSONL append-only FUERA del volumen Drive
(patrón _intake_log.jsonl). Best-effort: no rompe la operación si el log falla."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _ruta_log() -> Path:
    env = os.environ.get("XL_AUDIT_PATH")
    if env:
        return Path(env)
    base = os.environ.get("LOCALAPPDATA", str(Path.home()))
    return Path(base) / "FeesDefender" / "xl_audit.jsonl"


def log_op(op: str, ruta: str, resultado: str, motivo: str = "", **extra) -> None:
    ev = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
          "op": op, "ruta": ruta, "resultado": resultado, "motivo": motivo, **extra}
    try:
        dst = _ruta_log()
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except OSError as e:  # pragma: no cover - best effort
        print(f"[xl-audit] no se pudo escribir el log: {e}", file=sys.stderr)
