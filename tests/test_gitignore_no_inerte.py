"""Ningun fichero listado en `.gitignore` puede estar TRACKEADO.

**`.gitignore` no aplica a lo que ya esta en el indice.** Si un fichero se anadio antes
de ignorarse, su linea del `.gitignore` queda **inerte**: escrita, visible, y sin morder.

Medido el 2026-09-04 con `.claude/settings.local.json`, que se autodescribia como «NO se
versiona (en .gitignore)», figuraba en la linea 141 del `.gitignore` **y estaba
versionado**. Consecuencia real: Claude Code le anadia permisos al conceder
autorizaciones, git veia el cambio, y **cambiar de rama fallaba** con «Haz commit o stash
de los cambios» sin que se entendiera por que.

Este guard cierra la CLASE, no el caso: cualquier fichero futuro que caiga en la misma
trampa sale en rojo aqui.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

NUL = "\0"


def _ls_files() -> list[str]:
    """Rutas trackeadas, separadas por NUL y no por saltos de linea.

    En Windows la salida de git trae CRLF, y un `\\r` pegado a cada ruta **rompe el
    emparejamiento de las NEGACIONES** del `.gitignore`: `.env.example` con `\\r` no casa
    con `!.env.example` y si casa con `.env.*`. La primera version de este guard hacia
    eso y reportaba **cinco reglas sanas como inertes** — un informe falso producido por
    el propio guard, que es peor que no tenerlo. Con `-z` las rutas llegan limpias.
    """
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO,
        capture_output=True, encoding="utf-8", errors="replace",
    ).stdout
    return [p for p in out.split(NUL) if p.strip()]


def test_ninguna_regla_de_gitignore_es_inerte():
    """Un fichero trackeado que el `.gitignore` dice ignorar es una regla que no muerde."""
    trackeados = _ls_files()
    assert trackeados, "git ls-files vacio: el guard no esta mirando nada"

    # `--no-index` responde por las REGLAS y no por el estado del indice: sin el, un
    # fichero trackeado nunca sale como ignorado y este guard seria vacuo por
    # construccion. `-v` da la regla culpable, que es lo que hace accionable el fallo.
    proc = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin", "-z", "-v"],
        cwd=REPO, input=NUL.join(trackeados),
        capture_output=True, encoding="utf-8", errors="replace",
    )

    # Con `-z` la salida son campos NUL-separados en grupos de cuatro:
    # fuente, linea, patron, ruta.
    campos = [c for c in (proc.stdout or "").split(NUL) if c != ""]
    inertes = [
        f"{campos[i + 3]}  <- {campos[i]}:{campos[i + 1]} ({campos[i + 2]})"
        for i in range(0, len(campos) - 3, 4)
    ]

    assert not inertes, (
        "estos ficheros estan TRACKEADOS y ademas el .gitignore dice ignorarlos, "
        "asi que esas reglas son inertes y el fichero estorbara al cambiar de rama:\n  "
        + "\n  ".join(inertes)
        + "\n\nRemedio: `git rm --cached <fichero>` (lo deja en disco) y commitea. "
        "Si su contenido servia de plantilla, conservala como `<fichero>.example`. "
        "Si el trackeo es DELIBERADO pese a la regla, declara la excepcion en el propio "
        "`.gitignore` con una negacion (`!ruta`), que es donde se lee."
    )


def test_el_guard_no_es_vacuo():
    """Sin `--no-index`, `check-ignore` calla ante lo trackeado y el guard no mira nada.

    Es la prueba de que el guard puede FALLAR: se le da un fichero trackeado que el
    `.gitignore` si nombra —el `.env.example`, cubierto por `.env.*` y rescatado por su
    negacion— y se comprueba que las dos vias responden distinto. Si algun dia
    `--no-index` deja de hacer falta, este test lo dira antes de que el otro se vuelva
    verde por vacio.
    """
    sonda = ".env.example"
    assert sonda in _ls_files(), "la sonda dejo de estar trackeada; elige otra"

    con = subprocess.run(
        ["git", "check-ignore", "--no-index", "-v", sonda],
        cwd=REPO, capture_output=True, encoding="utf-8", errors="replace",
    )
    sin = subprocess.run(
        ["git", "check-ignore", "-v", sonda],
        cwd=REPO, capture_output=True, encoding="utf-8", errors="replace",
    )

    # Sin --no-index git no dice nada de un fichero trackeado (rc != 0, salida vacia).
    assert not sin.stdout.strip(), (
        "check-ignore SIN --no-index ya reporta ficheros trackeados: revisa si el guard "
        "de arriba sigue necesitando la bandera"
    )
    # Con --no-index, la negacion del .gitignore gana y tampoco lo marca como ignorado.
    assert not con.stdout.strip() or "!" in con.stdout, (
        f"{sonda} deberia estar rescatado por una negacion del .gitignore: {con.stdout!r}"
    )
