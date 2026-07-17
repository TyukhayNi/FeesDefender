"""Zonas (tiers) sobre rutas del montaje GDFD — lógica pura.

Tier 0 (PROHIBIDA): `90_Notas personales` — ni lectura (regla dura de CLAUDE.md).
Tier 1 (FORENSE): `00_Input` (carve-out de protocolo) y backups (sin carve-out).
Tier 2 (WORKSPACE): el resto. Los carve-outs espejan core.config.MERGE_EXCLUSIONS
(sincronía garantizada por test; el plugin no importa core en runtime).
Spec: docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-design.md §2.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from fnmatch import fnmatch
from pathlib import Path


class Tier(IntEnum):
    PROHIBIDA = 0
    FORENSE = 1
    WORKSPACE = 2


class TierViolation(Exception):
    """Operación rechazada por la política de zonas."""


_NOTAS = {"90_notas personales", "90_notas_personales"}
_INPUT = "00_input"

# Carve-out de protocolo bajo 00_Input (espeja core.config.MERGE_EXCLUSIONS)
PROTOCOL_EDIT: tuple[str, ...] = ("_caso.md", "MANIFEST_CHECKOUT.json")
PROTOCOL_APPEND: tuple[str, ...] = ("_intake_log.jsonl", "AUDITLOG_MERGE_*.jsonl")


@dataclass(frozen=True)
class Zonas:
    rw_roots: tuple[Path, ...]
    ro_roots: tuple[Path, ...] = ()
    backup_dirs: tuple[str, ...] = ("Otros ordenadores",)
    backup_shared: tuple[str, ...] = ("BACKUP", "BACKUP MADRID", "TWBCN-Backup2")


def es_backup(zonas: Zonas, path: Path) -> bool:
    parts = list(path.parts)
    lower = [p.lower() for p in parts]
    if any(b.lower() in lower for b in zonas.backup_dirs):
        return True
    for i, p in enumerate(lower):
        if p == "unidades compartidas" and i + 1 < len(parts):
            if parts[i + 1].upper() in {b.upper() for b in zonas.backup_shared}:
                return True
    return False


def classify(zonas: Zonas, path: Path) -> Tier:
    segs = [p.lower() for p in path.parts]
    if any(s in _NOTAS for s in segs):
        return Tier.PROHIBIDA
    if _INPUT in segs or es_backup(zonas, path):
        return Tier.FORENSE
    return Tier.WORKSPACE


def check_read(zonas: Zonas, path: Path) -> None:
    """Rechaza lectura si zona prohibida."""
    if classify(zonas, path) is Tier.PROHIBIDA:
        raise TierViolation(f"Zona prohibida (90_Notas personales): {path}")


def check_write(zonas: Zonas, path: Path, *, exists: bool, append: bool = False) -> None:
    """Rechaza escritura según reglas de zona y protocolo.

    Reglas:
    1. Ruta bajo ro_root → rechazo.
    2. Tier 0 → rechazo.
    3. Backup → rechazo (sin carve-out).
    4. Tier 1 (00_Input): crear-nuevo OK; sobrescribir solo si nombre ∈ PROTOCOL_EDIT
       o (append=True y nombre casa con PROTOCOL_APPEND).
    5. Tier 2 → permitido.
    """
    for ro in zonas.ro_roots:
        try:
            path.resolve().relative_to(Path(ro).resolve())
            raise TierViolation(f"Unidad solo-lectura en V1: {path}")
        except ValueError:
            continue
    tier = classify(zonas, path)
    if tier is Tier.PROHIBIDA:
        raise TierViolation(f"Zona prohibida (90_Notas personales): {path}")
    if tier is Tier.WORKSPACE:
        return
    # Tier 1
    if es_backup(zonas, path):
        raise TierViolation(f"Backup: solo-lectura, sin excepciones: {path}")
    if not exists:
        return  # crear-nuevo bajo 00_Input: permitido (intake)
    nombre = path.name
    if nombre in PROTOCOL_EDIT:
        return
    if append and any(fnmatch(nombre, pat) for pat in PROTOCOL_APPEND):
        return
    raise TierViolation(
        f"00_Input es forense-inmutable: no se sobrescribe lo depositado: {path}"
    )
