"""Regresion del arranque del wrapper `expedientes-xl`.

Bug de despliegue (2026-07-19): `run_server.bat` arrancaba el server como script
suelto (`python "%SRV%"`), que crashea con
`ImportError: attempted relative import with no known parent package` porque los
modulos hermanos (readops/fsops) usan `from . import ...` sin fallback (solo
`server.py` lo tiene). Bajo Claude Desktop el server moria al arrancar y Cowork no
conectaba. La suite verde no lo veia: los tests importan el server COMO PAQUETE
(`from plugins.expedientes_xl import server`), nunca ejercen la invocacion del wrapper.

Fix: el wrapper invoca el server como PAQUETE (`python -m expedientes_xl.server`),
que da contexto de paquete y resuelve todos los imports relativos de una vez.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BAT = ROOT / "plugins" / "expedientes_xl" / "run_server.bat"
PKG_PARENT = ROOT / "plugins"


def test_wrapper_bat_invoca_como_modulo():
    """El .bat arranca via `python -m expedientes_xl.server`, no como script suelto."""
    txt = BAT.read_text(encoding="utf-8")
    assert "-m expedientes_xl.server" in txt, "el wrapper debe invocar el server como modulo"
    # No debe reaparecer la invocacion como script suelto (regresion del bug 2026-07-19).
    assert '"%SRV%"' not in txt, "no invocar `python \"%SRV%\"` (script suelto)"


def test_server_arranca_como_modulo_sin_importerror():
    """`python -m expedientes_xl.server` resuelve los imports de paquete y llega a
    `_parse_argv` (imprime 'Uso:' sin args). Si los imports relativos se rompen,
    saldria ImportError ANTES de eso. Guarda contra romper de nuevo el arranque real."""
    pytest.importorskip("mcp")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PKG_PARENT) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run(
        [sys.executable, "-m", "expedientes_xl.server"],
        capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=60,
    )
    assert "attempted relative import" not in r.stderr
    assert "ImportError" not in r.stderr
    assert "Uso:" in r.stderr  # llego a _parse_argv => imports resolvieron


def test_wrapper_bat_no_lanza_un_interprete_sin_verificar():
    """El .bat lanza un interprete RESUELTO y VERIFICADO, no `python` pelado.

    Regresion del bug 2026-07-19 (2a parte): `python` pelado resolvia al stub de la
    Microsoft Store (`...\\WindowsApps\\python.exe`) en el PATH que ve Claude Desktop
    (PATH persistente, no el del terminal) -> el server salia -> 'Server disconnected'.

    El 2026-08-31 esta asercion cambio de FORMA, no de fondo. Comprobaba
    `"WindowsApps" in txt`: que el wrapper esquivara **ese** interprete malo por su
    nombre. Y volvio a pasar lo mismo con otro interprete distinto: un
    `pip install --user mcp` sin pin trajo mcp 2.0.0, que retiro
    `mcp.server.fastmcp`, y el wrapper lanzo tranquilamente un python que no era el
    stub y tampoco podia arrancar el server. La frontera no era «no lanzar el stub»
    sino «no lanzar un interprete cuya CAPACIDAD no se ha comprobado». Eso es lo que
    se exige aqui, y para todos los wrappers en `tests/test_mcp_wrappers.py`.
    """
    txt = BAT.read_text(encoding="utf-8")
    # La invocacion final usa el interprete resuelto, no `python` pelado.
    assert '"%PYEXE%" -m expedientes_xl.server' in txt, "invocar el interprete resuelto %PYEXE%"
    # Y ese interprete se prueba por capacidad ANTES de lanzar el server.
    assert "import mcp.server.fastmcp" in txt, (
        "el wrapper debe comprobar que %PYEXE% puede importar la API que usa el server"
    )


def test_main_no_escanea_las_bd_antes_de_run(monkeypatch):
    """El arranque (main) difiere el descubrimiento del oraculo: NO debe correr
    descubrir_cuentas (escaneo de las BD DriveFS de G:/H:) antes de .run().

    Bug de despliegue (2026-07-20): main() escaneaba las BD ANTES de .run(),
    retrasando el `initialize` MCP ~8-11s (medido en mcp.log; descubrir_cuentas
    ~2s en caliente, mucho mas en frio) -> Claude Desktop marcaba el server
    'failed' (badge cosmetico, MEJORAS #74). La suite verde no lo veia: los tests
    construian Oracle directamente, nunca ejercian el arranque de main(). Fix:
    LazyOracle difiere el escaneo al primer uso, fuera del handshake."""
    pytest.importorskip("mcp")
    from plugins.expedientes_xl import server
    from plugins.expedientes_xl import oracle as oracle_mod

    eventos = []

    def descubrir_espia(drivefs, roots):
        eventos.append("descubrir")
        return {}, {}

    monkeypatch.setattr(oracle_mod, "descubrir_cuentas", descubrir_espia)
    monkeypatch.setattr(server.FastMCP, "run", lambda self: eventos.append("run"))
    monkeypatch.setattr(sys, "argv", ["server.py", "--rw", "G:\\", "--ro", "H:\\"])

    server.main()

    assert "run" in eventos, "main debe arrancar el server (.run())"
    assert "descubrir" not in eventos, (
        f"el descubrimiento del oraculo no debe correr en el arranque: {eventos}")
