#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sincroniza los helpers canónicos ``.claude/skills/_shared/*.py`` a cada skill.

Las skills empaquetadas (``.skill``) deben ser autónomas: no pueden importar
``core/`` ni depender de ``_shared/`` en tiempo de ejecución. Por eso la fuente
única vive en ``.claude/skills/_shared/`` y se **copia byte a byte** a la carpeta
``scripts/`` de cada skill objetivo (y del draft de audiencia previa).

El test ``tests/test_skill_helpers_sync.py`` ejecuta este script en modo
``--check`` y exige que todas las copias sean byte-idénticas a su fuente.

Uso:
  python scripts/sync_skill_helpers.py            # copia (sincroniza)
  python scripts/sync_skill_helpers.py --check     # solo verifica; exit 1 si hay drift
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SHARED = _REPO / ".claude" / "skills" / "_shared"

# Carpetas ``scripts/`` que reciben los helpers canónicos. Rutas relativas al
# repo. Una entrada cuyo *skill padre* no existe aún (p. ej. preparacion-juicio-
# oral antes de versionarla) se omite silenciosamente.
_TARGETS: tuple[str, ...] = (
    ".claude/skills/escritos-judiciales/scripts",
    ".claude/skills/cendoj-descarga/scripts",
    ".claude/skills/preparacion-litigio-civil/scripts",
    ".claude/skills/preparacion-juicio-oral/scripts",
    ".claude/skills/preparacion-audiencia-previa/scripts",
)


def _shared_helpers() -> list[Path]:
    return sorted(p for p in _SHARED.glob("*.py") if p.name != "__init__.py")


def _target_dirs() -> list[Path]:
    """Targets cuyo skill padre existe (la carpeta scripts/ puede no existir aún)."""
    dirs: list[Path] = []
    for rel in _TARGETS:
        d = _REPO / rel
        if d.parent.exists():  # el skill padre existe
            dirs.append(d)
    return dirs


def sync() -> list[Path]:
    """Copia cada helper a cada target. Devuelve la lista de ficheros escritos."""
    helpers = _shared_helpers()
    written: list[Path] = []
    for d in _target_dirs():
        d.mkdir(parents=True, exist_ok=True)
        for h in helpers:
            dest = d / h.name
            if not dest.exists() or dest.read_bytes() != h.read_bytes():
                shutil.copy2(h, dest)
            written.append(dest)
    return written


def check() -> list[str]:
    """Devuelve descripciones de drift (vacío = todo sincronizado)."""
    helpers = _shared_helpers()
    drift: list[str] = []
    for d in _target_dirs():
        for h in helpers:
            dest = d / h.name
            if not dest.exists():
                drift.append(f"FALTA  {dest.relative_to(_REPO)}")
            elif dest.read_bytes() != h.read_bytes():
                drift.append(f"DIFIERE {dest.relative_to(_REPO)}")
    return drift


def main(argv: list[str]) -> int:
    if "--check" in argv:
        drift = check()
        if drift:
            print("[sync_skill_helpers] DRIFT detectado:", file=sys.stderr)
            for d in drift:
                print(f"  - {d}", file=sys.stderr)
            print("Ejecuta: python scripts/sync_skill_helpers.py", file=sys.stderr)
            return 1
        print("[sync_skill_helpers] OK: todas las copias byte-idénticas.")
        return 0
    written = sync()
    print(f"[sync_skill_helpers] sincronizados {len(written)} ficheros:")
    for w in written:
        print(f"  - {w.relative_to(_REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
