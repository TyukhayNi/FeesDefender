from __future__ import annotations

import json
from pathlib import Path

# Súbela cuando cambie la lógica de extracción/render para invalidar el caché.
# 2 (2026-08-04): los PDF pasan por el motor de la sala de máquina
# (`MEJORAS #87`). Sin este bump, los adjuntos ya procesados conservarían el
# texto del extractor viejo — incluido el `sin_texto` de los escaneados largos.
CONTENIDO_VERSION = 2
_ESTADO = "_contenido_estado.json"


def cargar_estado(adjuntos_dir: Path) -> dict:
    p = adjuntos_dir / _ESTADO
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if data.get("contenido_version") != CONTENIDO_VERSION:
        return {}
    return data.get("files", {})


def guardar_estado(adjuntos_dir: Path, files: dict) -> None:
    payload = {"contenido_version": CONTENIDO_VERSION, "files": files}
    (adjuntos_dir / _ESTADO).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
