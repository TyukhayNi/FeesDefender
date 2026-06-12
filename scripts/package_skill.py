#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Empaqueta una skill en un fichero ``.skill`` (zip) listo para instalar.

Un ``.skill`` es un zip cuyo contenido cuelga de una carpeta raíz con el nombre
de la skill (``<skill>/SKILL.md`` …). Antes de empaquetar se ejecuta
``sync_skill_helpers.sync()`` para que los helpers bundleados estén frescos.

Se excluye todo lo que no debe viajar en el paquete: ``node_modules/``,
``__pycache__/``, ``*.pyc``, ``*.bak*``, ficheros temporales y el contenido de
``logs/`` salvo ``logs/README.md`` (los logs llevan datos de expediente y nunca
se empaquetan — política RGPD del despacho).

Salida: ``dist/skills/<skill>.skill`` (``dist/`` está en .gitignore).

Uso:
  python scripts/package_skill.py <skill_dir> [--out <dir>]
  python scripts/package_skill.py --all          # todas las skills con SKILL.md
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import zipfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_DEFAULT_OUT = _REPO / "dist" / "skills"

# Dirs candidatos cuando se usa --all.
_SKILL_ROOTS = (
    _REPO / ".claude" / "skills",
    _REPO / "_skills_drafts",
)

_EXCLUDE_DIRS = {"node_modules", "__pycache__", ".git", ".pytest_cache"}


def _load_sync():
    spec = importlib.util.spec_from_file_location(
        "sync_skill_helpers", _REPO / "scripts" / "sync_skill_helpers.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _incluir(rel: Path) -> bool:
    parts = set(rel.parts)
    if parts & _EXCLUDE_DIRS:
        return False
    name = rel.name
    if name.endswith((".pyc", ".tmp")) or ".bak" in name:
        return False
    if name.startswith("._") or name.startswith("~$"):
        return False
    # logs/: solo viaja el README.md (los datos de uso/deltas nunca se empaquetan).
    if "logs" in rel.parts and name != "README.md":
        return False
    return True


def package(skill_dir: Path, out_dir: Path) -> Path:
    skill_dir = skill_dir.resolve()
    if not (skill_dir / "SKILL.md").exists():
        raise ValueError(f"{skill_dir} no contiene SKILL.md (no es una skill).")
    out_dir.mkdir(parents=True, exist_ok=True)
    nombre = skill_dir.name
    destino = out_dir / f"{nombre}.skill"

    n = 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(skill_dir.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(skill_dir)
            if not _incluir(rel):
                continue
            z.write(f, arcname=str(Path(nombre) / rel))
            n += 1
    try:
        mostrado = destino.relative_to(_REPO)
    except ValueError:
        mostrado = destino
    print(f"[package_skill] {nombre}.skill - {n} ficheros -> {mostrado}")
    return destino


def _todas_las_skills() -> list[Path]:
    dirs: list[Path] = []
    for root in _SKILL_ROOTS:
        if not root.exists():
            continue
        for d in sorted(root.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                dirs.append(d)
    return dirs


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Empaqueta una skill en .skill (zip).")
    p.add_argument("skill_dir", nargs="?", help="Carpeta de la skill a empaquetar.")
    p.add_argument("--all", action="store_true", help="Empaqueta todas las skills con SKILL.md.")
    p.add_argument("--out", default=str(_DEFAULT_OUT), help="Carpeta de salida (def. dist/skills).")
    args = p.parse_args(argv)

    # Refresca los helpers bundleados antes de empaquetar.
    _load_sync().sync()

    out_dir = Path(args.out)
    if args.all:
        for d in _todas_las_skills():
            package(d, out_dir)
        return 0
    if not args.skill_dir:
        p.error("indica <skill_dir> o usa --all")
    package(Path(args.skill_dir), out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
