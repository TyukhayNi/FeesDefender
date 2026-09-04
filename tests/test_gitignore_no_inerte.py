"""Ningun fichero listado en el `.gitignore` VERSIONADO puede estar TRACKEADO.

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

**La palabra que hace el trabajo es VERSIONADO.** `git check-ignore` no responde solo por
el `.gitignore` del repo: tambien aplica `.git/info/exclude` y `core.excludesFile`, que son
**preferencias de una maquina**. Una regla local que ignora algo trackeado a proposito no
es un defecto del repositorio y no se arregla tocandolo. Sin esa distincion, el guard se
pone rojo en la maquina de quien tenga `*.md` en su fichero global y acusa a cientos de
ficheros correctos — y un guard que acusa reglas sanas se acaba borrando.
"""

from __future__ import annotations

import os
import re
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

# Neutraliza `core.excludesFile` para la consulta: el ultimo `-c` gana. `.git/info/exclude`
# NO se puede desactivar por configuracion, y por eso hace falta ademas el filtro por
# fuente de `_ignorados`. Medido el 2026-09-04.
_SIN_EXCLUDES_GLOBALES = ("-c", "core.excludesFile=")

# `-v` imprime `<fuente>:<linea>:<patron>\t<ruta>`. La fuente puede ser una ruta absoluta
# de Windows y llevar `:`, asi que se ancla por el `:<digitos>:` que la cierra.
_RE_FUENTE = re.compile(r"^(.*?):(\d+):(.*)$")


def _git(
    args: list[str] | tuple[str, ...],
    repo: Path,
    entrada: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, input=entrada, env=env,
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


def _regla(ruta: str, repo: Path = REPO, env: dict[str, str] | None = None) -> str:
    """El campo `<fuente>:<linea>:<patron>` de la regla que DECIDE sobre `ruta`."""
    proc = _git(
        [*_SIN_EXCLUDES_GLOBALES, "check-ignore", "--no-index", "-v", ruta], repo, env=env
    )
    campos = [c for c in proc.stdout.strip().split("\t") if c]
    return campos[0] if campos else ""


def _fuente(campo: str) -> str:
    m = _RE_FUENTE.match(campo)
    return m.group(1) if m else ""


def _ignorados(
    rutas: list[str],
    repo: Path = REPO,
    trackeados: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> list[str]:
    """Las rutas que un `.gitignore` VERSIONADO del repo ignora de verdad.

    Dos capas, y las dos hacen falta:

    1. **La decision** se le pide a git **sin `-v`**, que es la unica forma autoritativa:
       `-v` cambia la semantica de «rutas excluidas» a «rutas que emparejan algun patron
       de exclusion», y una **negacion es un patron de exclusion**. Con `-v`,
       `.env.example` aparecia como ignorado acusado por su propio rescate
       (`!.env.example`) — el guard producia un informe falso, que es peor que no tenerlo.
       `--no-index` responde por las REGLAS y no por el estado del indice: sin el, un
       fichero trackeado nunca sale como ignorado y este guard seria vacuo por
       construccion.

    2. **La atribucion**: solo cuenta si la regla que decide vive en un `.gitignore`
       **trackeado**. `core.excludesFile` se anula por `-c`; `.git/info/exclude` no se
       puede anular, y se descarta porque su fuente no esta versionada. Tambien descarta
       un `.gitignore` local sin commitear: la clase que este guard vigila son las reglas
       que el repositorio **reparte**, no las que una maquina aplica.

    Medido el 2026-09-04: un `.gitignore` versionado tiene MAS precedencia que
    `.git/info/exclude` —gana incluso cuando este intenta rescatar con una negacion—, asi
    que una regla inerte del repo no puede quedar enmascarada por una exclusion local.
    El filtro no abre falsos negativos por esa via.
    """
    if not rutas:
        return []
    proc = _git(
        [*_SIN_EXCLUDES_GLOBALES, "check-ignore", "--no-index", "--stdin", "-z"],
        repo, entrada=NUL.join(rutas), env=env,
    )
    if proc.returncode not in _RC_VALIDOS:
        raise RuntimeError(
            f"git check-ignore fallo (rc={proc.returncode}): {proc.stderr.strip()}"
        )
    candidatos = [p for p in proc.stdout.split(NUL) if p.strip()]
    if not candidatos:
        return []

    versionados = set(_ls_files(repo) if trackeados is None else trackeados)
    return [
        r for r in candidatos
        if _fuente(_regla(r, repo, env=env)) in versionados
    ]


def test_ninguna_regla_de_gitignore_es_inerte():
    """Un fichero trackeado que el `.gitignore` dice ignorar es una regla que no muerde."""
    trackeados = _ls_files()
    assert trackeados, "git ls-files vacio: el guard no esta mirando nada"

    inertes = [
        f"{r}  <- {_regla(r)}" for r in _ignorados(trackeados, trackeados=trackeados)
    ]

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
        "`.claude/skills/**/logs/README.md` en el `.gitignore` como modelo.\n"
        "Este guard solo acusa reglas de un `.gitignore` TRACKEADO: si lo que te ignora "
        "el fichero es tu `.git/info/exclude` o tu `core.excludesFile`, no sale aqui y no "
        "hay nada que arreglar en el repositorio."
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
    assert "!" in _regla(sonda), (
        "la sonda ya no esta cubierta por un patron con negacion; este test dejo de "
        f"probar lo que dice probar: {_regla(sonda)!r}"
    )


def test_los_readme_de_telemetria_estan_rescatados_y_la_telemetria_no():
    """La excepcion del `.gitignore` acota lo que dice acotar, sobre el repo real.

    Los `.jsonl` de esas carpetas llevan referencias `W-XXXXXX` de asuntos reales
    (`docs/SEGURIDAD_DATOS.md`): que sigan ignorados es la mitad que importa de la
    excepcion, y la que un `!` mal puesto rompe sin que nadie lo note.
    """
    for skill in sorted((REPO / ".claude" / "skills").glob("*/logs")):
        rel = skill.relative_to(REPO).as_posix()
        assert _ignorados([f"{rel}/README.md"]) == [], f"{rel}/README.md deberia estar rescatado"
        for ruido in ("uso.jsonl", "W-000000_post.jsonl", "otro.md"):
            assert _ignorados([f"{rel}/{ruido}"]) == [f"{rel}/{ruido}"], (
                f"{rel}/{ruido} deberia seguir IGNORADO: la excepcion se ha ido de alcance"
            )


@pytest.fixture()
def repo_lab(tmp_path: Path) -> Path:
    """Un repo de mentira con la trampa ya montada: trackeado Y cubierto por la regla.

    Existe porque el repo real, cuando el guard esta verde, **no contiene ningun ejemplo
    del defecto** — y un test que solo mira el repo real no puede probar que la funcion
    que decide muerde. Aqui se fabrica el caso a proposito.

    **El aislamiento se acredita ANTES de tocar ningun indice, y no se supone.** Si
    `git init` falla y `tmp_path` cae debajo de otro repositorio, el `git add -f`
    siguiente escribe en el indice del PADRE: el guard escrito para detectar
    contaminacion del indice contaminaria uno de verdad, y con los cinco tests en verde.
    Reproducido el 2026-09-04 rompiendo el `init` a proposito.
    """
    init = _git(["init", "-q", "."], tmp_path)
    assert init.returncode == 0, f"git init fallo en el laboratorio: {init.stderr.strip()}"

    top = _git(["rev-parse", "--show-toplevel"], tmp_path)
    assert top.returncode == 0, f"el laboratorio no es un repo: {top.stderr.strip()}"
    assert os.path.samefile(top.stdout.strip(), tmp_path), (
        "el laboratorio NO esta aislado: git resuelve a "
        f"{top.stdout.strip()!r} y no a {str(tmp_path)!r}. Se aborta antes de `add -f` "
        "para no escribir en el indice de otro repositorio."
    )

    (tmp_path / ".gitignore").write_text(
        "secreto.txt\n.env.*\n!.env.example\n", encoding="utf-8"
    )
    for nombre in ("secreto.txt", ".env.example", "limpio.txt", "local.txt", "info.txt"):
        (tmp_path / nombre).write_text("x\n", encoding="utf-8")
    # `-f` es imprescindible: es justo lo que hace un dia alguien sin darse cuenta, y lo
    # que deja la regla inerte.
    add = _git(
        ["add", "-f", ".gitignore", "secreto.txt", ".env.example", "limpio.txt",
         "local.txt", "info.txt"],
        tmp_path,
    )
    assert add.returncode == 0, f"git add fallo en el laboratorio: {add.stderr.strip()}"
    return tmp_path


def test_la_decision_muerde_sobre_un_fichero_trackeado_e_ignorado(repo_lab: Path):
    """El mutante que cierra: quitarle `--no-index` a la decision la deja siempre vacia.

    Sin la bandera, git calla ante un path que esta en el indice y `_ignorados` devuelve
    `[]` para todo — el guard quedaria verde por no mirar nada, y ningun test que consulte
    a git por su cuenta lo notaria. Este si, porque pasa por la funcion que decide.
    """
    assert "secreto.txt" in _ls_files(repo_lab), "el laboratorio no trackeo la sonda"

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
    assert "!" in _regla(".env.example", repo=repo_lab)


def test_una_exclusion_LOCAL_no_es_una_regla_inerte_del_repo(repo_lab: Path):
    """Un `core.excludesFile` o un `.git/info/exclude` son preferencias de una maquina.

    Sin este filtro, quien tenga `*.md` en su fichero global de exclusiones ve el guard
    rojo acusando a cientos de ficheros correctamente trackeados, con un mensaje que le
    dice que arregle el repositorio. Es el ruido que hace que un guard se desactive.

    Se comprueban las DOS fuentes, porque se neutralizan de forma distinta: la global por
    `-c core.excludesFile=`, y `info/exclude` —que no admite anulacion— por su fuente.
    """
    globales = repo_lab / "excludes_de_esta_maquina.txt"
    globales.write_text("local.txt\n", encoding="utf-8")
    _git(["config", "core.excludesFile", str(globales)], repo_lab)

    info = repo_lab / ".git" / "info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "exclude").write_text("info.txt\n", encoding="utf-8")

    # Precondicion: git SI las aplica. Sin esto el test podria pasar por no haberlas
    # configurado bien, que es el mismo verde-por-no-mirar que persigue el guard.
    crudo = _git(
        ["check-ignore", "--no-index", "--stdin", "-z"], repo_lab,
        entrada=NUL.join(["local.txt", "info.txt"]),
    ).stdout
    assert {p for p in crudo.split(NUL) if p.strip()} == {"local.txt", "info.txt"}, (
        "git no esta aplicando las exclusiones locales; el test no prueba lo que dice"
    )

    assert _ignorados(["local.txt", "info.txt"], repo=repo_lab) == [], (
        "una exclusion local se esta contando como regla inerte del repositorio"
    )
    # Y el repo sigue acusando lo suyo: el filtro no puede haber apagado el guard.
    assert _ignorados(["secreto.txt"], repo=repo_lab) == ["secreto.txt"]


def test_la_excepcion_alcanza_una_skill_anidada(tmp_path: Path):
    """Las reglas reales del repo, sobre un layout de skill que hoy no existe.

    Con `*` en vez de `**` la excepcion cubre exactamente un nivel de skill, asi que una
    skill agrupada (`skills/grupo/alpha/`) no quedaria rescatada aunque el caso sea el
    mismo. Se prueba con las tres lineas copiadas del `.gitignore` del repo, y a la vez
    que la telemetria sigue ignorada a las dos profundidades.
    """
    reglas = [
        l.strip() for l in (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
        # Sin descartar los comentarios se cuela la propia prosa que explica la excepcion:
        # el comentario menciona «skills» y «logs» y colaba como cuarta regla.
        if not l.lstrip().startswith("#") and "skills" in l and "logs" in l
    ]
    assert len(reglas) == 3, f"la excepcion del .gitignore ya no son tres lineas: {reglas}"

    _git(["init", "-q", "."], tmp_path)
    (tmp_path / ".gitignore").write_text("logs/\n" + "\n".join(reglas) + "\n", encoding="utf-8")

    rescatados = [".claude/skills/alpha/logs/README.md",
                  ".claude/skills/grupo/alpha/logs/README.md"]
    ignorados = [".claude/skills/alpha/logs/uso.jsonl",
                 ".claude/skills/grupo/alpha/logs/uso.jsonl",
                 ".claude/skills/alpha/logs/sub/README.md",
                 "otro/logs/README.md"]
    for r in rescatados + ignorados:
        p = tmp_path / r
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x\n", encoding="utf-8")

    def ignora(r: str) -> bool:
        return _git(["check-ignore", "--no-index", "-q", r], tmp_path).returncode == 0

    assert [r for r in rescatados if ignora(r)] == [], "la excepcion no alcanza a una skill anidada"
    assert [r for r in ignorados if not ignora(r)] == [], "la excepcion se fue de alcance"


def test_el_guard_grita_si_git_no_puede_responder(tmp_path: Path):
    """Una salida vacia porque git fallo NO puede leerse como «no hay nada ignorado».

    El modo de fallo que cierra: `check-ignore` fuera de todo repositorio devuelve rc=128
    y stdout vacio. Sin control de codigo de salida, el guard quedaria verde por no haber
    podido mirar.

    El «fuera de todo repositorio» se **acredita**, no se supone: `GIT_CEILING_DIRECTORIES`
    corta la busqueda hacia arriba, asi que no depende de que el directorio no tenga
    ningun ancestro versionado. Usar la raiz del disco parecia equivalente y no lo es —
    solo significa raiz de la unidad, y una maquina con `C:\\.git` o un contenedor con `/`
    inicializado daria un rojo falso.
    """
    entorno = {**os.environ, "GIT_CEILING_DIRECTORIES": str(tmp_path.parent)}
    fuera = _git(["rev-parse", "--show-toplevel"], tmp_path, env=entorno)
    assert fuera.returncode != 0, (
        f"la precondicion no se cumple: {tmp_path} SI esta en un repositorio git"
    )

    with pytest.raises(RuntimeError, match="check-ignore fallo"):
        _ignorados([".env"], repo=tmp_path, trackeados=[], env=entorno)
