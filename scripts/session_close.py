#!/usr/bin/env python3
"""
FeesDefender — Verificacion de tests pre-commit
=================================================
Ejecutar como parte del cierre de sesion desde PowerShell:

    cd "C:\\Users\\tnm33\\Dev\\FeesDefender"
    python -m scripts.session_close && git add -A && git commit -m "<mensaje>"

Verja de tests por defecto RAPIDA: omite los tests marcados `@pytest.mark.slow`
(motor NLP/OCR real de core/anon/, ~3-4 min). Esos solo se ejecutan cuando:
  - el commit toca `core/anon/` (deteccion automatica via git), o
  - se pasa `--runslow` / la variable de entorno RUN_SLOW=1.

Asi la red de seguridad de anonimizacion (regresion SaRS1, OCR, integracion)
corre siempre que cambia el motor, sin depender de que nadie se acuerde, y el
cierre del dia a dia (cambios fuera de core/anon/) vuela en segundos.

El mensaje de commit lo proporciona Claude en el chat. El resto del protocolo
de cierre (STATUS.md, DEAD_ENDS.md, memoria) lo gestiona Claude directamente.
Ver STATUS.md seccion "Protocolo de cierre de sesion".
"""

import os
import subprocess
import sys
from pathlib import Path
from sys import executable as PYTHON

ROOT = Path(__file__).resolve().parent.parent
_ANON_PREFIX = "core/anon/"


def _git_lines(args: list[str]) -> list[str]:
    """Salida de un comando git, una linea por elemento. [] si git falla."""
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return []
    if r.returncode != 0:
        return []
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def _anon_tocado() -> bool:
    """True si core/anon/ tiene cambios sin commitear o en el ultimo commit."""
    # Cambios en working tree + staged (porcelain: 'XY ruta').
    for ln in _git_lines(["status", "--porcelain"]):
        ruta = ln[3:] if len(ln) > 3 else ln
        if _ANON_PREFIX in ruta.replace("\\", "/"):
            return True
    # Ficheros del ultimo commit (por si ya se commiteo antes de la verja).
    for ruta in _git_lines(["show", "--name-only", "--pretty=format:", "HEAD"]):
        if _ANON_PREFIX in ruta.replace("\\", "/"):
            return True
    return False


def main() -> None:
    force_slow = "--runslow" in sys.argv or os.getenv("RUN_SLOW") == "1"
    runslow = force_slow or _anon_tocado()

    print("FeesDefender - pytest pre-commit")
    print("-" * 40)
    if runslow:
        motivo = "forzado (--runslow/RUN_SLOW)" if force_slow else "core/anon/ tocado"
        print(f"Modo: COMPLETO (incluye tests lentos) - {motivo}")
        pytest_args = ["--runslow"]
    else:
        print("Modo: RAPIDO (omite tests lentos; core/anon/ sin cambios)")
        pytest_args = []

    result = subprocess.run(
        [PYTHON, "-m", "pytest", "-q", "--tb=short", *pytest_args],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("\n[X] Tests fallando - commit abortado.")
        sys.exit(1)
    print("\n[OK] Tests verdes - puedes continuar con git add / commit.")

    # Chequeo de skills (modo AVISO, no bloquea el cierre): CHANGELOG sin
    # actualizar, .skill caducado, drift de helpers, identidad incompleta.
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_skills", ROOT / "scripts" / "check_skills.py"
        )
        cs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cs)
        print("\n" + "-" * 40)
        cs.report(repackage=False)
    except Exception as e:  # el chequeo nunca debe romper el cierre
        print(f"[aviso] no se pudo correr check_skills: {e}")


if __name__ == "__main__":
    main()
