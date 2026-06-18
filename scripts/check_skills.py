#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chequeo de frescura y conformidad de las skills del despacho — **modo AVISO**.

Pega en un solo sitio las comprobaciones que hoy estaban dispersas o no existian,
para que los olvidos tipicos al editar una skill se vean en el cierre y no se
escapen (caso real: editar ``SKILL.md`` sin actualizar ``CHANGELOG.md`` ni
reempaquetar el ``.skill``). No bloquea: informa. ``--strict`` devuelve exit 1 si
hay avisos (uso manual; nunca en hooks).

Comprueba, por skill propia (excluye genericas de terceros y la plantilla):
  1. CHANGELOG desincronizado: la skill tiene fuente cambiada (working tree o
     ultimo commit) pero su ``CHANGELOG.md`` no se toco en ese mismo cambio.
  2. ``.skill`` caducado: algun fichero fuente de la skill es mas nuevo que su
     ``dist/skills/<skill>.skill`` (o el paquete no existe). ``--repackage-stale``
     reempaqueta esas skills.
  3. Drift de helpers: copias bundleadas != canonico ``_shared`` (reusa
     ``sync_skill_helpers.check``).
  4. Conformidad de identidad: frontmatter (rol/naturaleza/license/version),
     reusando ``validate_skills.validar_skill``.

Uso:
  python scripts/check_skills.py                  # informe (exit 0)
  python scripts/check_skills.py --repackage-stale # ademas reempaqueta los .skill caducados
  python scripts/check_skills.py --strict          # exit 1 si hay cualquier aviso
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_SKILLS = _REPO / ".claude" / "skills"
_DIST = _REPO / "dist" / "skills"

# Genericas de terceros (Anthropic): no las gobierna el estandar del despacho.
_GENERICAS = {"docx", "pdf", "xlsx", "pptx"}


def _load(mod_name: str):
    spec = importlib.util.spec_from_file_location(mod_name, _HERE / f"{mod_name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def skill_dirs() -> list[Path]:
    """Carpetas de skills propias con SKILL.md (excluye _shared/_plantilla y genericas)."""
    return sorted(
        d for d in _SKILLS.iterdir()
        if d.is_dir() and not d.name.startswith("_") and d.name not in _GENERICAS
        and (d / "SKILL.md").exists()
    )


# --- 1. CHANGELOG desincronizado --------------------------------------------

def _git_changed_files() -> set[str]:
    """Ficheros tocados en working tree + staged + ultimo commit (rutas con '/')."""
    changed: set[str] = set()

    def run(args: list[str]) -> list[str]:
        try:
            r = subprocess.run(
                ["git", *args], cwd=_REPO, capture_output=True,
                text=True, encoding="utf-8", errors="replace",
            )
        except FileNotFoundError:
            return []
        return r.stdout.splitlines() if r.returncode == 0 else []

    for ln in run(["status", "--porcelain"]):
        ruta = ln[3:] if len(ln) > 3 else ln
        if " -> " in ruta:  # rename: nos quedamos el destino
            ruta = ruta.split(" -> ", 1)[1]
        if ruta.strip():
            changed.add(ruta.strip().strip('"').replace("\\", "/"))
    for ruta in run(["show", "--name-only", "--pretty=format:", "HEAD"]):
        if ruta.strip():
            changed.add(ruta.strip().replace("\\", "/"))
    return changed


def changelog_stale(changed: set[str], skills: list[str]) -> list[str]:
    """Skills con fuente cambiada pero sin tocar su CHANGELOG.md en ese cambio.

    Funcion pura sobre el conjunto de rutas cambiadas (rutas relativas al repo,
    con '/'). 'Fuente' = cualquier fichero de la skill que no sea CHANGELOG.md ni
    este bajo logs/.
    """
    stale: list[str] = []
    for name in skills:
        base = f".claude/skills/{name}/"
        fuente = changelog = False
        for ruta in changed:
            if not ruta.startswith(base):
                continue
            rel = ruta[len(base):]
            if rel == "CHANGELOG.md":
                changelog = True
            elif not rel.startswith("logs/"):
                fuente = True
        if fuente and not changelog:
            stale.append(name)
    return stale


# --- 2. .skill caducado ------------------------------------------------------

def _source_mtime(skill_dir: Path, incluir) -> float:
    """mtime maximo de los ficheros que viajarian en el .skill."""
    latest = 0.0
    for f in skill_dir.rglob("*"):
        if not f.is_file():
            continue
        if not incluir(f.relative_to(skill_dir)):
            continue
        latest = max(latest, f.stat().st_mtime)
    return latest


def package_stale(skills: list[Path], dist_dir: Path, incluir) -> list[str]:
    """Skills cuyo .skill falta o es mas viejo que su fuente."""
    stale: list[str] = []
    for d in skills:
        pkg = dist_dir / f"{d.name}.skill"
        if not pkg.exists() or pkg.stat().st_mtime < _source_mtime(d, incluir):
            stale.append(d.name)
    return stale


# --- 5. Drift de taxonomía ---------------------------------------------------

def taxonomia_drift(destinos=None) -> list[str]:
    """Devuelve los destinos cuya taxonomía generada NO coincide con la copia en disco
    (alguien editó la copia a mano en vez del canon). Aviso, no bloqueante."""
    import scripts.sync_taxonomia_skills as sync
    from pathlib import Path
    objetivos = destinos if destinos is not None else sync.DESTINOS
    drift: list[str] = []
    for d in objetivos:
        d = Path(d)
        actual = d.read_text(encoding="utf-8") if d.exists() else None
        # Generar en un temporal hermano para comparar sin tocar el real
        tmp = d.with_suffix(d.suffix + ".sync_check")
        sync.generar(tmp)
        esperado = tmp.read_text(encoding="utf-8")
        tmp.unlink()
        if actual != esperado:
            drift.append(str(d))
    return drift


# --- informe -----------------------------------------------------------------

def report(repackage: bool = False) -> int:
    """Imprime el informe. Devuelve el numero total de avisos."""
    vs = _load("validate_skills")
    ssh = _load("sync_skill_helpers")
    pk = _load("package_skill")

    dirs = skill_dirs()
    nombres = [d.name for d in dirs]

    cl_stale = changelog_stale(_git_changed_files(), nombres)
    pkg_stale = package_stale(dirs, _DIST, pk._incluir)
    drift = ssh.check()

    helpers = vs._canonical_helpers()
    operacion = vs._operacion_dirs()
    id_gaps = {
        d.name: avisos for d in dirs
        if (avisos := vs.validar_skill(d, helpers, operacion))
    }

    tax_drift = taxonomia_drift()
    if tax_drift:
        print("AVISO taxonomía desincronizada (corre scripts/sync_taxonomia_skills.py):")
        for d in tax_drift:
            print(f"  - {d}")

    print("Chequeo de skills (modo AVISO) - no bloquea.\n")
    print(f"  CHANGELOG sin actualizar : {', '.join(cl_stale) or 'ninguna'}")
    print(f"  .skill caducado          : {', '.join(pkg_stale) or 'ninguna'}")
    print(f"  Drift de helpers         : {len(drift)} fichero(s)")
    print(f"  Identidad incompleta     : {', '.join(id_gaps) or 'ninguna'}")
    print(f"  Drift de taxonomía       : {len(tax_drift)} fichero(s)")

    if repackage and pkg_stale:
        print("\n  Reempaquetando .skill caducados:")
        for name in pkg_stale:
            pk.package(_SKILLS / name, _DIST)

    total = len(cl_stale) + len(pkg_stale) + len(drift) + len(id_gaps) + len(tax_drift)
    if total:
        print(f"\n{total} aviso(s). Detalle de identidad: python scripts/validate_skills.py")
    else:
        print("\nTodo en orden.")
    return total


def main(argv: list[str]) -> int:
    total = report(repackage="--repackage-stale" in argv)
    return 1 if ("--strict" in argv and total) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
