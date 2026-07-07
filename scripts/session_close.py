#!/usr/bin/env python3
"""
FeesDefender — Verificacion de tests pre-commit
=================================================
Ejecutar como parte del cierre de sesion desde PowerShell:

    cd "C:\\Users\\tnm33\\Dev\\FeesDefender"
    python -m scripts.session_close && git add <rutas> && git commit -m "<mensaje>"
    # (nunca `git add -A`: grapa solo las rutas del cambio)

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


def _git_count(rango: list[str]) -> int:
    """Nº de commits en un rango tipo 'A..B'. 0 si git falla o el rango es vacío."""
    out = _git_lines(["rev-list", "--count", *rango])
    return int(out[0]) if out and out[0].isdigit() else 0


def _trabajo_sin_publicar() -> list[tuple[str, int, str]]:
    """Ramas locales con commits que NO están en el archivo central (origin).

    Devuelve tuplas (rama, n_commits, tipo) donde tipo es:
      - 'sin_publicar': la rama tiene upstream y va n commits por delante.
      - 'nunca_subida': la rama no tiene upstream y tiene n commits sobre origin/main.
    Solo consultas locales a git; sin red ni credenciales.
    """
    filas: list[tuple[str, int, str]] = []
    fmt = "%(refname:short)\t%(upstream:short)"
    for ln in _git_lines(["for-each-ref", "--format=" + fmt, "refs/heads"]):
        partes = ln.split("\t")
        rama = partes[0]
        upstream = partes[1] if len(partes) > 1 and partes[1] else ""
        if upstream:
            n = _git_count([f"{upstream}..{rama}"])
            if n:
                filas.append((rama, n, "sin_publicar"))
        else:
            n = _git_count([f"origin/main..{rama}"])
            if n:
                filas.append((rama, n, "nunca_subida"))
    return filas


def _avisar_publicacion() -> None:
    """AVISO no bloqueante: trabajo grapado (commits) que no ha llegado a origin.

    No consulta la red ni comprueba si existe el PR (eso exigiría credenciales):
    solo detecta commits locales sin publicar y recuerda la vía rama + PR.
    """
    actual = (_git_lines(["branch", "--show-current"]) or [""])[0]
    filas = _trabajo_sin_publicar()
    print("\n" + "-" * 40)
    print("Trabajo sin publicar")
    if not filas:
        print(f"Rama actual: {actual} - sin commits sin publicar. Nada que llevar al archivo.")
        return
    print("[!] Tienes trabajo que NO esta en el archivo central (origin):")
    for rama, n, tipo in filas:
        marca = " (rama nunca subida)" if tipo == "nunca_subida" else ""
        aqui = "  <- estas aqui" if rama == actual else ""
        plural = "commit" if n == 1 else "commits"
        print(f"  -> {rama}: {n} {plural} sin publicar{marca}{aqui}")
    print("Recuerda: 'main' no admite entradas directas.")
    print("Publica con: rama + PR (debe pasar 'leak-scan' antes de fusionar).")


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

    # Aviso de trabajo sin publicar (modo AVISO, no bloquea el cierre).
    try:
        _avisar_publicacion()
    except Exception as e:  # el aviso nunca debe romper el cierre
        print(f"[aviso] no se pudo comprobar trabajo sin publicar: {e}")


if __name__ == "__main__":
    main()
