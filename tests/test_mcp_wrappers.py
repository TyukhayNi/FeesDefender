r"""Guards de los wrappers de arranque de los conectores MCP del despacho.

Por qué existen, medido el 2026-08-31: los tres conectores (`google-despacho`,
`expedientes-xl`, `email-export`) llevaban caídos en Claude Code por DOS defectos
que ningún test veía.

1. **Redirección en la línea del intérprete.** Los `.bat` terminaban en
   ``python server.py 2>>"%LOG%"``. Con esa redirección Claude Code da
   ``CONNECTION_CLOSED`` y el server muere en ``stdout.flush()`` con
   ``OSError 22`` sin haber recibido ni ``initialize``; sin ella, conecta. El
   experimento de control fueron dos `.bat` idénticos salvo el ``2>>``. Claude
   Desktop lo toleraba, y de ahí venía la regla de oro antigua —«jamás `1>`, solo
   `2>>`»— que resultó ser justo la trampa.

2. **Intérprete resuelto por ruta que existe, no por capacidad.** Los `.bat`
   cogían ``%LOCALAPPDATA%\Python\bin\python.exe`` o el primer python del PATH.
   El 2026-08-23 un ``pip install --user mcp`` sin pin trajo mcp 2.0.0; 2.0 retiró
   ``mcp.server.fastmcp``, que es la API que usan estos servers, y los tres
   murieron a la vez y en silencio.

**Y por qué la primera versión de estos guards no valía** (R1 adversarial,
2026-08-31): cerraban el ejemplo, no la frontera. El revisor ejecutó el helper con
contraejemplos y salieron verdes wrappers claramente defectuosos —basta una línea
``exit /b 0`` o un ``:: comentario`` detrás del lanzamiento para que el guard mire
otra línea—, y rojo un wrapper correcto con un ``echo`` final. Y las tres
comprobaciones textuales se burlaban con una subcadena: ``REM import
mcp.server.fastmcp`` satisfacía la de capacidad, ``set PYEXE=python.exe`` esquivaba
la del fallback, y ``mcp>=1,<20`` pasaba la del pin **admitiendo 2.0**. Esta versión
comprueba propiedades: parsea el `.bat` de verdad, evalúa los especificadores con
``packaging``, y añade un guard **de comportamiento** que ejecuta el wrapper con el
entorno envenenado y exige que falle ruidosamente en vez de lanzar.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"

# `expedientes_mcp` es el server Node jubilado (lo sustituyó expedientes_xl): no
# lo declara `plugin-src/.mcp.json` ni ninguna config viva, así que no se le
# exigen los guards. Confirmado en la R1 revisando `.claude.json`,
# `claude_desktop_config.json` y `extensions-installations.json`.
JUBILADOS = {"expedientes_mcp"}

# La versión que rompió todo. Un especificador que la admita no vale como pin.
VERSION_QUE_ROMPE = Version("2.0.0")


def _wrappers() -> list[Path]:
    return sorted(
        p for p in PLUGINS.glob("*/run_server.bat") if p.parent.name not in JUBILADOS
    )


def _requirements() -> list[Path]:
    """Todos los requirements del repo, no solo los de los conectores.

    La R1 encontró que `requirements-dev.txt` seguía diciendo `mcp>=1.28` —sin
    techo— y que es justo el fichero que puebla el venv que los wrappers
    PREFIEREN: el glob viejo, limitado a `plugins/*/requirements.txt`, pasaba
    verde sobre la causa raíz intacta.
    """
    return sorted({*ROOT.glob("requirements*.txt"), *PLUGINS.glob("*/requirements.txt")})


def _es_comentario(linea: str) -> bool:
    """`REM`, `@REM` y la forma-label `::`, que cmd también trata como comentario."""
    s = linea.strip()
    if s.startswith("::"):
        return True
    s = s[1:].lstrip() if s.startswith("@") else s
    return s.upper() == "REM" or s.upper().startswith("REM ") or s.upper().startswith("REM\t")


def _sentencias(texto: str) -> list[str]:
    """Sentencias ejecutables del .bat, con las continuaciones `^` ya unidas.

    Un `.bat` no es una lista de líneas: `^` al final continúa la sentencia, y
    `REM`/`@REM`/`::` no ejecutan nada. El helper viejo ignoraba las tres cosas.
    """
    fisicas = texto.splitlines()
    unidas: list[str] = []
    pendiente = ""
    for ln in fisicas:
        if _es_comentario(ln) and not pendiente:
            continue
        cuerpo = ln.rstrip()
        if cuerpo.endswith("^"):
            pendiente += cuerpo[:-1] + " "
            continue
        unidas.append((pendiente + cuerpo).strip())
        pendiente = ""
    if pendiente:
        unidas.append(pendiente.strip())
    return [s for s in unidas if s]


def _sentencia_de_lanzamiento(texto: str) -> str:
    """La sentencia que lanza el server: la que invoca el intérprete resuelto.

    Devuelve la ÚLTIMA que lo hace. Que además sea la última ejecutable del
    fichero lo comprueba su propio test, no este helper: si lo diera por supuesto,
    volvería el verde falso de la primera versión.
    """
    lanzamientos = [s for s in _sentencias(texto) if _RE_INVOCA_INTERPRETE.search(s)]
    assert lanzamientos, "el wrapper no invoca ningún intérprete resuelto"
    return lanzamientos[-1]


# Invocación del intérprete resuelto al principio de la sentencia: `"%PYEXE%" ...`
# o `"%NODE%" ...`. La sonda de capacidad también lo invoca, pero eso lo distingue
# el test por posición, no por regex.
_RE_INVOCA_INTERPRETE = re.compile(r'^"%(?:PYEXE|NODE)%"')

# Redirecciones y tuberías de cmd. Se busca el operador, no el carácter `>` a
# secas: la primera versión daba rojo con un `echo fin 1>&2` legítimo en otra
# línea, y no veía un `<` ni un `|`.
_RE_REDIRECCION = re.compile(r"(?<!\^)(?:\d?>>?|<|\|)")


def test_hay_wrappers_que_auditar() -> None:
    """Si el glob deja de encontrar wrappers, los otros guards pasarían vacíos."""
    assert len(_wrappers()) >= 3, [p.name for p in _wrappers()]


def test_hay_requirements_que_auditar() -> None:
    """Hermano del anterior para el corpus de requirements."""
    nombres = [str(p.relative_to(ROOT)) for p in _requirements()]
    assert "requirements-dev.txt" in nombres, nombres
    assert len(nombres) >= 4, nombres


@pytest.mark.parametrize("wrapper", _wrappers(), ids=lambda p: p.parent.name)
def test_el_lanzamiento_es_la_ultima_sentencia(wrapper: Path) -> None:
    """Nada ejecutable detrás del intérprete: ni `exit /b`, ni limpieza, ni `::`.

    No es cosmética. Si hay algo detrás, el `.bat` puede morir antes que el server
    o, peor, el guard de la redirección mira otra sentencia y pasa verde sobre un
    lanzamiento sucio — que es exactamente el contraejemplo de la R1.
    """
    sentencias = _sentencias(wrapper.read_text(encoding="utf-8"))
    assert _RE_INVOCA_INTERPRETE.search(sentencias[-1]), (
        f"{wrapper.relative_to(ROOT)}: la última sentencia ejecutable no lanza el "
        f"server -> {sentencias[-1]!r}"
    )


@pytest.mark.parametrize("wrapper", _wrappers(), ids=lambda p: p.parent.name)
def test_el_lanzamiento_no_redirige(wrapper: Path) -> None:
    """Ninguna redirección ni tubería en la sentencia que lanza el server."""
    sentencia = _sentencia_de_lanzamiento(wrapper.read_text(encoding="utf-8"))
    m = _RE_REDIRECCION.search(sentencia)
    assert m is None, (
        f"{wrapper.relative_to(ROOT)}: la sentencia de lanzamiento contiene "
        f"{m.group(0)!r}, y eso da CONNECTION_CLOSED en Claude Code -> {sentencia!r}"
    )


@pytest.mark.parametrize("wrapper", _wrappers(), ids=lambda p: p.parent.name)
def test_la_capacidad_se_prueba_EJECUTANDO(wrapper: Path) -> None:
    """La sonda de capacidad está en una sentencia ejecutable, no en un comentario.

    La primera versión buscaba la subcadena en el fichero entero, así que un
    `REM import mcp.server.fastmcp` la satisfacía sin ejecutarse nunca.
    """
    texto = wrapper.read_text(encoding="utf-8")
    lanzamiento = _sentencia_de_lanzamiento(texto)
    sondas = [
        s for s in _sentencias(texto)
        if "import mcp.server.fastmcp" in s and s != lanzamiento
    ]
    assert sondas, (
        f"{wrapper.relative_to(ROOT)}: ninguna sentencia EJECUTABLE anterior al "
        "lanzamiento prueba que el intérprete pueda importar mcp.server.fastmcp "
        "(un REM no cuenta, y el propio lanzamiento tampoco)"
    )


@pytest.mark.parametrize("requirements", _requirements(), ids=lambda p: p.parent.name + "/" + p.name)
def test_el_pin_de_mcp_excluye_de_verdad_la_2(requirements: Path) -> None:
    """Se EVALÚA el especificador, no se busca la subcadena `<2`.

    `mcp>=1,<20` y `mcp>=1,<2.1` contienen `<2` y admiten 2.0.0. Comprobado con
    `packaging` en la R1.
    """
    for linea in requirements.read_text(encoding="utf-8").splitlines():
        spec = linea.split("#", 1)[0].strip()
        if not spec or not re.match(r"^mcp\b", spec, re.IGNORECASE):
            continue
        req = Requirement(spec)
        assert VERSION_QUE_ROMPE not in req.specifier, (
            f"{requirements.relative_to(ROOT)}: `{spec}` admite mcp "
            f"{VERSION_QUE_ROMPE}, que retiró mcp.server.fastmcp"
        )


@pytest.mark.parametrize("wrapper", _wrappers(), ids=lambda p: p.parent.name)
@pytest.mark.skipif(os.name != "nt", reason="los wrappers son .bat de cmd")
def test_sin_interprete_capaz_el_wrapper_FALLA_RUIDOSAMENTE(wrapper: Path, tmp_path: Path) -> None:
    """Guard de COMPORTAMIENTO: el wrapper no lanza lo que no ha comprobado.

    Los tres guards de arriba son textuales y, por tanto, burlables en principio.
    Este ejecuta el wrapper de verdad con el entorno envenenado —ningún candidato
    capaz alcanzable— y exige la propiedad que de verdad importa: **salir con
    código distinto de 0 y decir por qué en stderr**, en vez de arrancar un
    intérprete incapaz que muere sin explicar nada, que es lo que pasó en agosto.

    El wrapper se copia a `tmp_path` para que `%~dp0..\\..\\.venv` no encuentre el
    venv real del repo, y se apuntan `USERPROFILE`, `LOCALAPPDATA` y `PATH` a
    directorios vacíos. No se ejecuta desde el árbol para no tocar nada.
    """
    copia = tmp_path / "run_server.bat"
    shutil.copy2(wrapper, copia)
    vacio = tmp_path / "vacio"
    vacio.mkdir()

    env = dict(os.environ)
    env["FEESDEFENDER_PYTHON"] = str(tmp_path / "no-existe-python.exe")
    env["FEESDEFENDER_ROOT"] = str(tmp_path / "no-existe-raiz")
    env["USERPROFILE"] = str(vacio)
    env["LOCALAPPDATA"] = str(vacio)
    env["APPDATA"] = str(vacio)
    env["PATH"] = str(vacio)

    r = subprocess.run(
        ["cmd", "/c", str(copia)],
        capture_output=True, encoding="utf-8", errors="replace",
        env=env, timeout=120, cwd=str(tmp_path), input="",
    )
    assert r.returncode != 0, (
        f"{wrapper.relative_to(ROOT)}: sin ningún intérprete capaz el wrapper "
        f"devolvió 0. stdout={r.stdout[:400]!r}"
    )
    assert r.stderr.strip(), (
        f"{wrapper.relative_to(ROOT)}: falló en silencio; sin mensaje en stderr "
        "nadie puede diagnosticarlo (fue el modo de fallo de agosto)"
    )
    # No basta con morir: hay que morir DICIENDO QUÉ HACER. Sin esto, un wrapper
    # con un fallback ciego a `python` pasaría el guard, porque cmd escribe su
    # propio «no se reconoce» en stderr y devuelve != 0 — o sea, moriría por
    # accidente y no por diseño, que es indistinguible desde fuera salvo por el
    # diagnóstico.
    #
    # Se acepta cualquiera de las dos palancas porque el wrapper puede morir en
    # dos sitios distintos, y la primera versión de esta asserción exigía sólo
    # `FEESDEFENDER_PYTHON`: `email-export` la puso roja legítimamente, porque con
    # el entorno envenenado muere ANTES, resolviendo la raíz del repo, y ahí la
    # palanca correcta es `FEESDEFENDER_ROOT`. Exigir una palanca concreta era
    # atarse al sitio del fallo en vez de a la propiedad.
    palancas = ("FEESDEFENDER_PYTHON", "FEESDEFENDER_ROOT")
    assert any(p in r.stderr for p in palancas), (
        f"{wrapper.relative_to(ROOT)}: murió sin nombrar ninguna palanca "
        f"accionable {palancas}. stderr={r.stderr[:400]!r}"
    )
    assert not r.stdout.strip(), (
        f"{wrapper.relative_to(ROOT)}: escribió en stdout, que es el pipe "
        f"JSON-RPC de MCP -> {r.stdout[:200]!r}"
    )
