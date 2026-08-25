"""El bundle del plugin no puede atarse a una maquina ni a un perfil de Windows.

Contexto (2026-08-25, decision E.6.1). El marketplace `despacho-tyukhay` pasa a
publicarse en un repo dedicado, asi que lo que hoy es una carpeta local
gitignorada empieza a ser **material distribuido**. El control de secretos previo
al primer push encontro cuatro rastros de `C:\\Users\\<perfil>` en el bundle, por
tres mecanismos distintos:

1. `plugins/email_export_mcp/run_server.bat` cableaba el interprete **absoluto**
   del perfil que lo escribio. Es la «bomba A.6-ter» del handoff de migracion, que
   se parcheo en la copia del perfil destino y **no en esta fuente**, de modo que
   cada build la reproducia.
2. `plugins/expedientes_xl/dxt-build/` viajaba dentro: es el subproducto de la
   OTRA via de empaquetado (la extension DXT), y su `manifest.json` cablea
   interprete y `PYTHONPATH` del perfil que lo genero.
3. `__pycache__/*.pyc` — que el empaquetador **ya** excluia desde el 2026-06-22.
   Los del arbol eran residuo de EJECUCION (fechados 12 h despues del build),
   porque el marketplace de tipo `directory` apunta a `dist/plugin` y los servers
   corrian desde ahi. Un `.pyc` lleva dentro la ruta absoluta de compilacion.

Estos tests fijan el contrato que nada comprobaba. La capa sintetica ejercita el
filtro con las tres clases de contaminante presentes a proposito; la capa real es
la regresion de los dos defectos arreglados ese dia.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import package_plugin

# Un bundle publicable no menciona el directorio de perfiles de Windows. Se busca
# en BYTES y no en texto porque un `.pyc` lo lleva compilado dentro.
RASTRO_DE_PERFIL = rb"C:\Users"


def _ficheros(raiz: Path) -> list[Path]:
    return [p for p in raiz.rglob("*") if p.is_file()]


def _sin_rastro(bundle: Path) -> list[str]:
    """Ficheros del bundle que llevan una ruta absoluta de perfil dentro."""
    return [
        str(p.relative_to(bundle))
        for p in _ficheros(bundle)
        if RASTRO_DE_PERFIL in p.read_bytes()
    ]


# ---------------------------------------------------------------------------
# Capa sintetica: el filtro, con los tres contaminantes puestos a proposito
# ---------------------------------------------------------------------------

@pytest.fixture
def fuentes(tmp_path: Path) -> Path:
    """Arbol de fuentes minimo que contiene las TRES clases de contaminante."""
    root = tmp_path / "repo"
    src = root / "plugin-src"
    (src / ".claude-plugin").mkdir(parents=True)
    (src / "marketplace.json").write_text('{"name": "x"}', encoding="utf-8")
    (src / ".claude-plugin" / "plugin.json").write_text('{"version": "0"}', encoding="utf-8")
    (src / ".mcp.json").write_text("{}", encoding="utf-8")

    xl = root / "plugins" / "expedientes_xl"
    xl.mkdir(parents=True)
    (xl / "server.py").write_text("# limpio\n", encoding="utf-8")
    # (1) residuo de compilacion, con la ruta absoluta dentro
    (xl / "__pycache__").mkdir()
    (xl / "__pycache__" / "server.cpython-314.pyc").write_bytes(
        b"\x00\x00" + RASTRO_DE_PERFIL + rb"\perfil\repo\server.py"
    )
    # (2) subproducto de la otra via de empaquetado
    (xl / "dxt-build").mkdir()
    (xl / "dxt-build" / "manifest.json").write_text(
        r'{"command": "C:\\Users\\perfil\\python.exe"}', encoding="utf-8"
    )
    (xl / "dxt-build" / "expedientes-xl.dxt").write_bytes(b"PK\x03\x04binario")

    eem = root / "plugins" / "email_export_mcp"
    eem.mkdir(parents=True)
    # (3) el wrapper, aqui ya en su forma portable
    (eem / "run_server.bat").write_text(
        '@echo off\r\n"%PYEXE%" "%~dp0server.py"\r\n', encoding="utf-8"
    )

    skills = root / ".claude" / "skills"
    for nombre in package_plugin.SKILLS:
        (skills / nombre).mkdir(parents=True)
        (skills / nombre / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    return root


@pytest.fixture
def bundle_sintetico(fuentes: Path, tmp_path: Path, monkeypatch) -> Path:
    out = tmp_path / "dist" / "plugin"
    monkeypatch.setattr(package_plugin, "ROOT", fuentes)
    monkeypatch.setattr(package_plugin, "SRC", fuentes / "plugin-src")
    monkeypatch.setattr(package_plugin, "SKILLS_DIR", fuentes / ".claude" / "skills")
    monkeypatch.setattr(package_plugin, "OUT", out)
    monkeypatch.setattr(package_plugin, "PLUGIN", out / "feesdefender")
    return package_plugin.build()


def test_el_bundle_sintetico_se_ensambla_de_verdad(bundle_sintetico: Path):
    """Guarda anti-vacuidad: sin esto, un build que no copia nada pasaria todo."""
    presentes = {str(p.relative_to(bundle_sintetico)) for p in _ficheros(bundle_sintetico)}
    assert Path(".claude-plugin/marketplace.json").as_posix() in {
        Path(p).as_posix() for p in presentes
    }
    posix = {Path(p).as_posix() for p in presentes}
    assert "feesdefender/.claude-plugin/plugin.json" in posix
    assert "feesdefender/.mcp.json" in posix
    assert "feesdefender/expedientes_xl/server.py" in posix
    assert "feesdefender/email_export_mcp/run_server.bat" in posix
    for nombre in package_plugin.SKILLS:
        assert f"feesdefender/skills/{nombre}/SKILL.md" in posix


def test_el_filtro_deja_fuera_el_residuo_de_compilacion(bundle_sintetico: Path):
    """Frontera 1: `__pycache__` y `*.pyc` no viajan."""
    posix = [p.relative_to(bundle_sintetico).as_posix() for p in _ficheros(bundle_sintetico)]
    assert not [p for p in posix if "__pycache__" in p or p.endswith(".pyc")]


def test_el_filtro_deja_fuera_el_subproducto_dxt(bundle_sintetico: Path):
    """Frontera 2: `dxt-build/` es de la otra via de empaquetado y no viaja."""
    posix = [p.relative_to(bundle_sintetico).as_posix() for p in _ficheros(bundle_sintetico)]
    assert not [p for p in posix if "dxt-build" in p or p.endswith(".dxt")]


def test_el_bundle_sintetico_no_lleva_rutas_absolutas_de_perfil(bundle_sintetico: Path):
    """El contrato que engloba a los tres mecanismos, medido en bytes."""
    assert _sin_rastro(bundle_sintetico) == []


# ---------------------------------------------------------------------------
# Capa real: la regresion de los dos defectos arreglados el 2026-08-25
# ---------------------------------------------------------------------------

def test_el_bundle_real_es_publicable(tmp_path: Path, monkeypatch):
    """Ensambla desde las fuentes REALES: es lo que se subiria al repo dedicado.

    Habria cazado los dos defectos del 2026-08-25 —el interprete absoluto del
    `run_server.bat` y el `dxt-build/` viajando— antes del primer push.
    """
    out = tmp_path / "dist" / "plugin"
    monkeypatch.setattr(package_plugin, "OUT", out)
    monkeypatch.setattr(package_plugin, "PLUGIN", out / "feesdefender")
    bundle = package_plugin.build()

    assert _ficheros(bundle), "el build real no copio nada; el test seria vacuo"
    sucios = _sin_rastro(bundle)
    assert sucios == [], f"el bundle ataria el plugin a un perfil: {sucios}"
