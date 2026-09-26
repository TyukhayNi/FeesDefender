"""Git para los guards: si el comando falla, el guard PARA — nunca lee el vacío como respuesta.

Un guard que enumera con `git` y no mira el código de salida pasa en verde sin haber mirado nada
cuando `git` falla: en una copia sin `.git` (la de los revisores de Codex), sin `git` en el PATH o
con el índice roto. Lo vio la R1 de Codex de los estados medidos (2026-09-26) en `_md_trackeados`,
y la frontera eran cinco sitios (plan `docs/superpowers/plans/2026-09-26-git-que-falla-en-voz-alta.md`).

Algunos comandos usan el código de salida como RESPUESTA —`git grep` devuelve 1 sin coincidencias;
`git check-ignore`, 1 si la ruta no está ignorada—, así que cada llamada dice cuáles son válidos en
vez de exigir siempre un 0.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def git(*args: str, cwd: Path, rc_validos: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[str]:
    """Ejecuta `git <args>` en `cwd` y PARA el test si no se pudo o si el código no es válido."""
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
    return r


def trackeados(cwd: Path, *patrones: str) -> list[str]:
    """Las rutas trackeadas bajo `cwd`, filtradas por `patrones` si se dan."""
    return [ln for ln in git("ls-files", *patrones, cwd=cwd).stdout.splitlines() if ln]
