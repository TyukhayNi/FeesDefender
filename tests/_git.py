"""Git para los guards: si el comando falla, el guard PARA — nunca lee el vacío como respuesta.

Un guard que enumera con `git` y no mira el código de salida pasa en verde sin haber mirado nada
cuando `git` falla: en una copia sin `.git` (la de los revisores de Codex), sin `git` en el PATH o
con el índice roto. Lo vio la R1 de Codex de los estados medidos (2026-09-26) en `_md_trackeados`,
y la frontera eran cinco sitios (plan `docs/superpowers/plans/2026-09-26-git-que-falla-en-voz-alta.md`).

Algunos comandos usan el código de salida como RESPUESTA —`git grep` devuelve 1 sin coincidencias;
`git check-ignore`, 1 si la ruta no está ignorada—, así que cada llamada dice cuáles son válidos en
vez de exigir siempre un 0.

**Y el código no basta** (R1/H-04 de esa pieza, reproducido con git 2.53): git puede no leer un
fichero, decirlo por stderr —`failed to stat`, `unable to access`— y salir con un código que es
respuesta. Por eso un stderr no vacío también PARA. Medido el 2026-09-26: las consultas de los
guards no escriben nada por stderr en un árbol sano, así que la regla no hace ruido; si un día git
avisa de algo inocuo, el rojo lleva su texto y se clasifica entonces, con la evidencia delante.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def git(*args: str, cwd: Path, rc_validos: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[str]:
    """Ejecuta `git <args>` en `cwd` y PARA el test si no se pudo, si el código no es válido o si
    git avisó por stderr de algo que no pudo hacer."""
    orden = "git " + " ".join(args)
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           encoding="utf-8", errors="replace")
    except OSError as e:
        pytest.fail(f"{orden}: no se pudo ejecutar ({e}). El guard no ha mirado nada, y eso no es "
                    "un verde.")
    if r.returncode not in rc_validos:
        pytest.fail(f"{orden} falló (rc={r.returncode}): {r.stderr.strip()[:500]}. El guard no ha "
                    "mirado nada, y eso no es un verde.")
    if r.stderr.strip():
        pytest.fail(f"{orden} salió con {r.returncode} pero avisó por stderr: "
                    f"{r.stderr.strip()[:500]}. Su respuesta puede estar incompleta, y leerla como "
                    "completa no es un verde.")
    return r


def trackeados(cwd: Path, *patrones: str) -> list[str]:
    """Las rutas trackeadas bajo `cwd`, filtradas por `patrones` si se dan.

    Con `-z`: sin él, git entrecomilla y escapa en octal las rutas con bytes no ASCII
    (`core.quotePath`), y la ruta que se devolvía no existía en disco."""
    return [p for p in git("ls-files", "-z", *patrones, cwd=cwd).stdout.split("\0") if p]
