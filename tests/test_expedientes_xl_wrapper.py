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
