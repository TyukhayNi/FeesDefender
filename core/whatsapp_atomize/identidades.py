"""Mapa autor_export → (persona_id, nombre, rol) desde el identidades.yaml del caso.

Lee el MISMO fichero que core.email_atomize.identidades pero el campo `identificadores`
(autor_export de WhatsApp: número o alias de contacto), no `direcciones` (emails).
"""
from __future__ import annotations

from pathlib import Path

import yaml

_ESTADOS = {"confirmada", "candidata"}


def cargar_identidades_wa(case_dir: Path | str) -> dict[str, tuple[str, str, str]]:
    """Devuelve {identificador_lower: (persona_id, nombre, rol)}. Sin fichero → {}."""
    path = Path(case_dir) / "identidades.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mapa: dict[str, tuple[str, str, str]] = {}
    for raw in (data.get("personas") or []):
        if not isinstance(raw, dict):
            continue
        pid = str(raw.get("id") or "").strip()
        if not pid:
            continue
        nombre = str(raw.get("nombre") or "")
        rol = str(raw.get("rol") or "")
        for d in (raw.get("identificadores") or []):
            if not isinstance(d, dict):
                continue
            valor = str(d.get("valor") or "").strip().lower()
            estado = str(d.get("estado") or "").strip().lower()
            if valor and estado in _ESTADOS:
                mapa[valor] = (pid, nombre, rol)
    return mapa
