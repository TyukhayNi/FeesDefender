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
    # El gate de montaje se fija ABIERTO. Sin esto, en `expedientes_xl` este
    # test no medía lo que dice medir: con G:/H: caídos el wrapper moría en el
    # gate y nunca llegaba a resolver intérprete — 1 rojo con los drives abajo
    # y 23/23 verdes con los drives arriba el mismo día (2026-09-07). Los
    # wrappers sin gate ignoran estas variables.
    env["FEESDEFENDER_PROBE_G"] = str(vacio)
    env["FEESDEFENDER_PROBE_H"] = str(vacio)

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


# ---------------------------------------------------------------------------
# El gate de montaje (poll-until-mount) y su costura de prueba
# ---------------------------------------------------------------------------
# Por que existe esto, medido el 2026-09-07 en las dos direcciones y el mismo
# dia, sin tocar una linea de codigo: con G:/H: caidos este fichero daba 1 rojo;
# con los drives montados, 23/23 verdes. El motivo es que
# `test_sin_interprete_capaz_el_wrapper_FALLA_RUIDOSAMENTE` mide la resolucion
# del interprete, pero en `expedientes_xl` ese codigo solo se alcanza pasando
# antes el gate de montaje, que el test NO controlaba. Sin montaje el wrapper
# moria en el gate y el guard leia otra cosa de la que creia leer.
#
# El arreglo facil habria sido anadir el mensaje del gate a la lista blanca de
# palancas. Eso es cerrar el ejemplo por TERCERA vez: la primera version exigia
# UNA palanca y se amplio a DOS cuando `email-export` la puso roja por morir
# antes. La frontera es que el test controle toda precondicion capaz de desviar
# al wrapper de la propiedad que mide.


def _tiene_gate_de_montaje(texto: str) -> bool:
    """No todos los wrappers esperan montajes: `email_export_mcp` arranca directo."""
    return ":waitloop" in texto.lower()


def _wrappers_con_gate() -> list[Path]:
    return [w for w in _wrappers() if _tiene_gate_de_montaje(w.read_text(encoding="utf-8"))]


def _correr_con_sondas(wrapper: Path, tmp_path: Path, sonda_g: Path, sonda_h: Path):
    """Ejecuta una COPIA del wrapper con el gate gobernado y el interprete envenenado.

    El interprete se envenena siempre para que los dos modos de muerte sean
    distinguibles por el mensaje: morir en el gate dice `PROBE_`, morir
    resolviendo interprete dice `FEESDEFENDER_PYTHON`. Y el PATH se vacia para
    que, si el gate se abriera por error, el wrapper no LANCE el server y se
    quede colgado en el pipe hasta el timeout: un guard que se cuelga en vez de
    dar rojo no es un guard.
    """
    raiz = tmp_path / f"corrida-{sonda_g.name}-{sonda_h.name}"
    raiz.mkdir()
    copia = raiz / "run_server.bat"
    shutil.copy2(wrapper, copia)
    vacio = raiz / "vacio"
    vacio.mkdir()

    env = dict(os.environ)
    env["FEESDEFENDER_PROBE_G"] = str(sonda_g)
    env["FEESDEFENDER_PROBE_H"] = str(sonda_h)
    env["FEESDEFENDER_PROBE_MAXTRIES"] = "1"
    env["FEESDEFENDER_PYTHON"] = str(raiz / "no-existe-python.exe")
    env["FEESDEFENDER_ROOT"] = str(raiz / "no-existe-raiz")
    env["USERPROFILE"] = str(vacio)
    env["LOCALAPPDATA"] = str(vacio)
    env["APPDATA"] = str(vacio)
    env["PATH"] = str(vacio)

    return subprocess.run(
        ["cmd", "/c", str(copia)],
        capture_output=True, encoding="utf-8", errors="replace",
        env=env, timeout=120, cwd=str(raiz), input="",
    )


def _murio_en_el_gate(r) -> bool:
    return r.returncode != 0 and "PROBE_" in r.stderr


def _llego_a_resolver_interprete(r) -> bool:
    return "FEESDEFENDER_PYTHON" in r.stderr


def test_hay_wrappers_con_gate_que_auditar() -> None:
    """Hermano de `test_hay_wrappers_que_auditar`: si el detector deja de
    reconocer el gate, los guards de abajo pasarian VACIOS y en verde."""
    assert _wrappers_con_gate(), [p.parent.name for p in _wrappers()]


@pytest.mark.parametrize("wrapper", _wrappers_con_gate(), ids=lambda p: p.parent.name)
@pytest.mark.skipif(os.name != "nt", reason="los wrappers son .bat de cmd")
def test_cada_sonda_del_gate_ES_GOBERNABLE_por_separado(wrapper: Path, tmp_path: Path) -> None:
    """Experimento DIFERENCIAL: tres corridas identicas salvo una sonda.

    Por que diferencial y no una sola corrida — esto lo levanto el arnes de
    mutacion, no el diseno. La primera version apuntaba las DOS sondas a algo
    inexistente y exigia morir en el gate; borrar el override de `PROBE_G`
    SOBREVIVIA, porque el gate es un AND y bastaba con que `PROBE_H` siguiera
    funcionando. El test exigia «al menos un override vivo», no «los dos».

    Y por que diferencial y no absoluto: el gate lee el sistema de ficheros, asi
    que NINGUNA corrida suelta prueba nada por si misma — en una maquina con los
    drives montados, un override ignorado se ve igual que uno respetado. Lo que
    no depende de la maquina es la DIFERENCIA: si un override se ignorara, las
    tres corridas harian lo mismo (lo que dictaran los drives reales) y las tres
    aserciones no podrian cumplirse a la vez. Es la forma del experimento del
    2026-08-31 con el `2>>`: dos ejecuciones identicas salvo la variable.
    """
    existe = tmp_path / "montado"
    existe.mkdir()
    no_existe_g = tmp_path / "sin-montar-G"
    no_existe_h = tmp_path / "sin-montar-H"

    abierto = _correr_con_sondas(wrapper, tmp_path, existe, existe)
    sin_g = _correr_con_sondas(wrapper, tmp_path, no_existe_g, existe)
    sin_h = _correr_con_sondas(wrapper, tmp_path, existe, no_existe_h)

    nombre = wrapper.relative_to(ROOT)
    assert _llego_a_resolver_interprete(abierto), (
        f"{nombre}: con las dos sondas apuntadas a un directorio que existe, el "
        f"wrapper NO llego a resolver interprete -> el gate no se abre desde el "
        f"entorno. stderr={abierto.stderr[:400]!r}"
    )
    assert _murio_en_el_gate(sin_g) and not _llego_a_resolver_interprete(sin_g), (
        f"{nombre}: la sonda G apuntada a algo inexistente no cerro el gate -> "
        f"FEESDEFENDER_PROBE_G no se respeta. stderr={sin_g.stderr[:400]!r}"
    )
    assert _murio_en_el_gate(sin_h) and not _llego_a_resolver_interprete(sin_h), (
        f"{nombre}: la sonda H apuntada a algo inexistente no cerro el gate -> "
        f"FEESDEFENDER_PROBE_H no se respeta. stderr={sin_h.stderr[:400]!r}"
    )
    for r in (abierto, sin_g, sin_h):
        assert not r.stdout.strip(), (
            f"{nombre}: escribio en stdout, que es el pipe JSON-RPC de MCP -> "
            f"{r.stdout[:200]!r}"
        )


@pytest.mark.parametrize("wrapper", _wrappers_con_gate(), ids=lambda p: p.parent.name)
@pytest.mark.skipif(os.name != "nt", reason="los wrappers son .bat de cmd")
def test_el_gate_respeta_el_tope_de_intentos(wrapper: Path, tmp_path: Path) -> None:
    """Con el tope en 1, el wrapper no llega a esperar ni una vez.

    Sin esta asercion `FEESDEFENDER_PROBE_MAXTRIES` seria un knob de produccion
    que nadie prueba —el arnes de mutacion lo confirmo: borrarlo sobrevivia—, y
    la rapidez del test de arriba seria un accidente del PATH vacio en vez de una
    propiedad. Se mide por la huella de la espera: el wrapper espera con `ping`,
    que con el PATH vaciado no existe, asi que cada intento deja su queja en
    stderr. Con el tope respetado hay como mucho una; sin el, veinticuatro.
    """
    existe = tmp_path / "montado"
    existe.mkdir()
    r = _correr_con_sondas(wrapper, tmp_path, tmp_path / "sin-montar", existe)
    quejas = r.stderr.lower().count("ping")
    assert quejas <= 1, (
        f"{wrapper.relative_to(ROOT)}: {quejas} intentos de espera con el tope "
        f"en 1 -> FEESDEFENDER_PROBE_MAXTRIES no se respeta. "
        f"stderr={r.stderr[:400]!r}"
    )


@pytest.mark.parametrize("wrapper", _wrappers_con_gate(), ids=lambda p: p.parent.name)
def test_el_gate_de_montaje_sigue_apuntando_a_produccion_por_defecto(wrapper: Path) -> None:
    """La costura no puede cambiar a donde mira el wrapper cuando NADIE la usa.

    Un override cuyo default se hubiera ido a otro sitio dejaria los guards de
    arriba verdes y el conector roto en la maquina de verdad, que es el peor
    reparto posible. Se comprueba sobre las SENTENCIAS, no sobre el texto crudo:
    un default correcto escrito dentro de un `REM` no vale.
    """
    sentencias = _sentencias(wrapper.read_text(encoding="utf-8"))
    defaults = [
        s for s in sentencias
        if s.upper().startswith('SET "PROBE_') and "FEESDEFENDER_PROBE" not in s.upper()
    ]
    assert defaults, f"{wrapper.relative_to(ROOT)}: no asigna PROBE_* por defecto"
    unidas = " ".join(defaults)
    for esperado in ("G:", "H:"):
        assert esperado in unidas, (
            f"{wrapper.relative_to(ROOT)}: el default de las sondas ya no nombra "
            f"{esperado} -> apuntaria a otro sitio en produccion. {defaults}"
        )
