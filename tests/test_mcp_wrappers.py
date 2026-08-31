r"""Guards de los wrappers de arranque de los conectores MCP del despacho.

Por qué existen, medido el 2026-08-31: los tres conectores (`google-despacho`,
`expedientes-xl`, `email-export`) llevaban caídos en Claude Code por DOS
defectos que ningún test veía.

1. **Redirección en la línea del intérprete.** Los `.bat` terminaban en
   ``python server.py 2>>"%LOG%"``. Con esa redirección Claude Code da
   ``CONNECTION_CLOSED`` y el server muere en ``stdout.flush()`` con
   ``OSError 22`` sin haber recibido ni ``initialize``; sin ella, conecta. El
   experimento de control fueron dos `.bat` idénticos salvo el ``2>>``. Claude
   Desktop lo toleraba, y de ahí venía la regla de oro antigua —«jamás 1>, solo
   2>>»— que resultó ser justo la trampa.

2. **Intérprete resuelto por ruta que existe, no por capacidad.** Los `.bat`
   cogían ``%LOCALAPPDATA%\Python\bin\python.exe`` o el primer python del
   PATH. El 2026-08-23 un ``pip install --user mcp`` sin pin trajo mcp 2.0.0 al
   site de usuario; 2.0 retiró ``mcp.server.fastmcp``, que es la API que usan
   estos servers, y los tres murieron a la vez y en silencio.

Estos guards cierran las dos propiedades, no los dos casos: valen para cualquier
wrapper que se añada después.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"

# `expedientes_mcp` es el server Node jubilado (lo sustituyó expedientes_xl):
# no lo lanza ninguna config viva, así que no se le exigen los guards.
JUBILADOS = {"expedientes_mcp"}


def _wrappers() -> list[Path]:
    return sorted(
        p
        for p in PLUGINS.glob("*/run_server.bat")
        if p.parent.name not in JUBILADOS
    )


def _linea_de_lanzamiento(texto: str) -> str:
    """Última línea ejecutable del .bat: la que lanza el server en primer plano."""
    lineas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    ejecutables = [ln for ln in lineas if not ln.upper().startswith("REM")]
    assert ejecutables, "el wrapper no tiene ninguna línea ejecutable"
    return ejecutables[-1]


def test_hay_wrappers_que_auditar() -> None:
    """Si el glob deja de encontrar wrappers, los otros guards pasarían vacíos."""
    assert len(_wrappers()) >= 3, [p.name for p in _wrappers()]


@pytest.mark.parametrize("wrapper", _wrappers(), ids=lambda p: p.parent.name)
def test_la_linea_de_lanzamiento_no_redirige(wrapper: Path) -> None:
    """Ninguna redirección en la línea que lanza el server: rompe el pipe MCP."""
    linea = _linea_de_lanzamiento(wrapper.read_text(encoding="utf-8"))
    assert ">" not in linea, (
        f"{wrapper.relative_to(ROOT)}: la línea de lanzamiento redirige un "
        f"descriptor, y eso da CONNECTION_CLOSED en Claude Code -> {linea!r}"
    )


@pytest.mark.parametrize("wrapper", _wrappers(), ids=lambda p: p.parent.name)
def test_el_interprete_se_verifica_por_capacidad(wrapper: Path) -> None:
    """El wrapper prueba que el intérprete puede importar la API que usa el server."""
    texto = wrapper.read_text(encoding="utf-8")
    assert "import mcp.server.fastmcp" in texto, (
        f"{wrapper.relative_to(ROOT)}: no comprueba que el intérprete pueda "
        "importar mcp.server.fastmcp antes de lanzar el server"
    )


@pytest.mark.parametrize("wrapper", _wrappers(), ids=lambda p: p.parent.name)
def test_sin_fallback_ciego_al_python_del_path(wrapper: Path) -> None:
    """Ningún wrapper cae en `where python` ni en un `PYEXE=python` pelado."""
    texto = wrapper.read_text(encoding="utf-8")
    ejecutable = "\n".join(
        ln for ln in texto.splitlines() if not ln.strip().upper().startswith("REM")
    )
    assert "where python" not in ejecutable, (
        f"{wrapper.relative_to(ROOT)}: resuelve el intérprete con `where python`, "
        "que es como entró mcp 2.0.0 el 2026-08-23"
    )
    assert not re.search(r'set\s+"PYEXE=python"', ejecutable), (
        f"{wrapper.relative_to(ROOT)}: fallback ciego a `python` del PATH"
    )


@pytest.mark.parametrize(
    "requirements",
    sorted(PLUGINS.glob("*/requirements.txt")),
    ids=lambda p: p.parent.name,
)
def test_mcp_pinneado_por_debajo_de_2(requirements: Path) -> None:
    """Quien declare `mcp` lo declara `<2`: 2.0 retiró `mcp.server.fastmcp`."""
    for linea in requirements.read_text(encoding="utf-8").splitlines():
        spec = linea.split("#", 1)[0].strip()
        if not spec or not re.match(r"^mcp\b", spec):
            continue
        assert "<2" in spec, (
            f"{requirements.relative_to(ROOT)}: `{spec}` admite mcp 2.0, que "
            "retiró mcp.server.fastmcp"
        )
