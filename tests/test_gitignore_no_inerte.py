"""Ningun fichero listado en `.gitignore` puede estar TRACKEADO.

**`.gitignore` no aplica a lo que ya esta en el indice.** Si un fichero se anadio antes
de ignorarse, su linea del `.gitignore` queda **inerte**: escrita, visible, y sin morder.

Medido el 2026-09-04 con `.claude/settings.local.json`, que se autodescribia como «NO se
versiona (en .gitignore)», figuraba en la linea 141 del `.gitignore` **y estaba
versionado**. Consecuencia real: Claude Code le anadia permisos al conceder
autorizaciones, git veia el cambio, y **cambiar de rama fallaba** con «Haz commit o stash
de los cambios» sin que se entendiera por que.

Este guard cierra la CLASE, no el caso: al correrlo por primera vez destapo cuatro
`.claude/skills/*/logs/README.md` en la misma trampa, ignorados de verdad por la regla
`logs/` y trackeados a proposito. Su trackeo era deliberado, asi que la excepcion se
declaro en el `.gitignore` — que es donde se lee — y no borrando los ficheros.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

NUL = "\0"

# `check-ignore` devuelve 0 si algun path esta ignorado y 1 si ninguno lo esta. Cualquier
# otro codigo es un fallo de git (repo invalido, bandera no soportada), y ahi el guard
# tiene que GRITAR: su salida vacia se leeria como «no hay nada ignorado» y el guard
# quedaria verde por no haber podido mirar. Ver
# [[feedback-guarda-inerte-comprobar-el-otro-valor]].
_RC_VALIDOS = (0, 1)


def _git(args: list[str], repo: Path, entrada: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, input=entrada,
        capture_output=True, encoding="utf-8", errors="replace",
    )


def _ls_files(repo: Path = REPO) -> list[str]:
    """Rutas trackeadas del repo.

    Se separan por NUL y no por saltos de linea porque una ruta puede llevar espacios y
    porque asi no depende del modo texto. (El `\\r` de Windows NO es un problema aqui:
    medido el 2026-09-04, `git ls-files` sale con LF y Python lo normaliza en modo texto.
    La primera version de este guard atribuia al `\\r` cinco positivos que en realidad
    tenian dos causas distintas, ninguna relacionada — ver el test de la negacion.)
    """
    proc = _git(["ls-files", "-z"], repo)
    if proc.returncode != 0:
        raise RuntimeError(f"git ls-files fallo (rc={proc.returncode}): {proc.stderr.strip()}")
    return [p for p in proc.stdout.split(NUL) if p.strip()]


def _ignorados(rutas: list[str], repo: Path = REPO) -> list[str]:
    """Las rutas que el `.gitignore` ignora DE VERDAD.

    La decision se le pide a git **sin `-v`**, que es la unica forma autoritativa: `-v`
    cambia la semantica de «rutas excluidas» a «rutas que emparejan algun patron de
    exclusion», y una **negacion es un patron de exclusion**. Con `-v`, `.env.example`
    aparecia como ignorado acusado por su propio rescate (`!.env.example`) — el guard
    producia un informe falso, que es peor que no tenerlo.

    `--no-index` responde por las REGLAS y no por el estado del indice: sin el, un fichero
    trackeado nunca sale como ignorado y este guard seria vacuo por construccion.
    """
    if not rutas:
        return []
    proc = _git(
        ["check-ignore", "--no-index", "--stdin", "-z"], repo, entrada=NUL.join(rutas)
    )
    if proc.returncode not in _RC_VALIDOS:
        raise RuntimeError(
            f"git check-ignore fallo (rc={proc.returncode}): {proc.stderr.strip()}"
        )
    return [p for p in proc.stdout.split(NUL) if p.strip()]


def _regla_culpable(ruta: str, repo: Path = REPO) -> str:
    """Fuente:linea:patron de la regla que decide, solo para el mensaje de fallo."""
    proc = _git(["check-ignore", "--no-index", "-v", ruta], repo)
    campos = [c for c in proc.stdout.strip().split("\t") if c]
    return campos[0] if campos else "(regla no identificada)"


def test_ninguna_regla_de_gitignore_es_inerte():
    """Un fichero trackeado que el `.gitignore` dice ignorar es una regla que no muerde."""
    trackeados = _ls_files()
    assert trackeados, "git ls-files vacio: el guard no esta mirando nada"

    inertes = [f"{r}  <- {_regla_culpable(r)}" for r in _ignorados(trackeados)]

    assert not inertes, (
        "estos ficheros estan TRACKEADOS y ademas el .gitignore dice ignorarlos, "
        "asi que esas reglas son inertes y el fichero estorbara al cambiar de rama:\n  "
        + "\n  ".join(inertes)
        + "\n\nRemedio A — si el fichero NO debe versionarse: `git rm --cached <fichero>` "
        "(lo deja en disco) y commitea; si su contenido servia de plantilla, conservala "
        "como `<fichero>.example`.\n"
        "Remedio B — si el trackeo es DELIBERADO: declara la excepcion en el propio "
        "`.gitignore`, que es donde se lee. OJO: un `!ruta` a secas NO basta cuando lo "
        "que excluye es un patron de DIRECTORIO (`logs/`), porque git no re-incluye un "
        "fichero cuyo padre esta excluido. Hay que rescatar el directorio, re-excluir su "
        "contenido y negar el fichero — las tres lineas. Ver la excepcion de "
        "`.claude/skills/*/logs/README.md` en el `.gitignore` como modelo."
    )


def test_una_negacion_no_cuenta_como_regla_inerte():
    """Regresion: `.env.example` esta trackeado a proposito y su negacion lo rescata.

    Es el falso positivo que produjo la primera version de este guard. Si alguien vuelve
    a tomar la decision desde `-v`, este test se pone rojo antes de que el informe del
    otro acuse a cuatro reglas sanas.
    """
    sonda = ".env.example"
    assert sonda in _ls_files(), "la sonda dejo de estar trackeada; elige otra"

    # La decision: NO esta ignorado.
    assert _ignorados([sonda]) == [], (
        f"{sonda} deberia estar rescatado por `!{sonda}` y sale como ignorado"
    )
    # Y sin embargo SI empareja un patron de exclusion, que es lo que confundia a `-v`.
    assert "!" in _regla_culpable(sonda), (
        "la sonda ya no esta cubierta por un patron con negacion; este test dejo de "
        f"probar lo que dice probar: {_regla_culpable(sonda)!r}"
    )


@pytest.fixture()
def repo_lab(tmp_path: Path) -> Path:
    """Un repo de mentira con la trampa ya montada: trackeado Y cubierto por la regla.

    Existe porque el repo real, cuando el guard esta verde, **no contiene ningun ejemplo
    del defecto** — y un test que solo mira el repo real no puede probar que la funcion
    que decide muerde. Aqui se fabrica el caso a proposito.
    """
    (tmp_path / ".gitignore").write_text(
        "secreto.txt\n.env.*\n!.env.example\n", encoding="utf-8"
    )
    for nombre in ("secreto.txt", ".env.example", "limpio.txt"):
        (tmp_path / nombre).write_text("x\n", encoding="utf-8")
    _git(["init", "-q", "."], tmp_path)
    # `-f` es imprescindible: es justo lo que hace un dia alguien sin darse cuenta, y lo
    # que deja la regla inerte.
    _git(["add", "-f", "secreto.txt", ".env.example", "limpio.txt"], tmp_path)
    return tmp_path


def test_la_decision_muerde_sobre_un_fichero_trackeado_e_ignorado(repo_lab: Path):
    """El mutante que cierra: quitarle `--no-index` a la decision la deja siempre vacia.

    Sin la bandera, git calla ante un path que esta en el indice y `_ignorados` devuelve
    `[]` para todo — el guard quedaria verde por no mirar nada, y ningun test que consulte
    a git por su cuenta lo notaria. Este si, porque pasa por la funcion que decide.
    """
    assert "secreto.txt" in _git(["ls-files"], repo_lab).stdout, "el laboratorio no trackeo la sonda"

    assert _ignorados(["secreto.txt"], repo=repo_lab) == ["secreto.txt"]
    # Y la asimetria que hace necesaria la bandera, medida en el mismo laboratorio.
    sin_bandera = _git(["check-ignore", "--stdin", "-z"], repo_lab, entrada="secreto.txt")
    assert not sin_bandera.stdout.strip(), (
        "check-ignore SIN --no-index ya reporta ficheros trackeados: revisa si la "
        f"decision sigue necesitando la bandera. Salida: {sin_bandera.stdout!r}"
    )


def test_la_decision_respeta_la_negacion_en_laboratorio(repo_lab: Path):
    """El otro mutante: decidir desde `-v` acusa al fichero con su propio rescate.

    `.env.example` esta trackeado, empareja `.env.*` y lo salva `!.env.example`. La
    decision tiene que decir que NO esta ignorado; `-v` decia que si.
    """
    assert _ignorados([".env.example", "limpio.txt"], repo=repo_lab) == []
    assert "!" in _regla_culpable(".env.example", repo=repo_lab)


def test_el_guard_grita_si_git_no_puede_responder():
    """Una salida vacia porque git fallo NO puede leerse como «no hay nada ignorado».

    El modo de fallo que cierra: `check-ignore` contra algo que no es un repo devuelve
    rc=128 y stdout vacio. Sin control de codigo de salida, el guard quedaria verde por
    no haber podido mirar.
    """
    fuera = Path(REPO.anchor)  # la raiz del disco no es un repositorio git
    with pytest.raises(RuntimeError, match="check-ignore fallo"):
        _ignorados([".env"], repo=fuera)
