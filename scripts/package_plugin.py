"""Ensambla el plugin `feesdefender` en dist/plugin/ desde la SSOT.

Copia: plugin-src/ (metadatos) + plugins/expedientes_xl/ (conector) + las skills
del despacho que se distribuyen con el plugin (intake-expediente,
exportar-correos-etiqueta). Salida gitignored y reproducible.
Uso: python -m scripts.package_plugin
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "plugin-src"
SKILLS_DIR = ROOT / ".claude" / "skills"
# Skills empaquetadas en el plugin (SSOT en .claude/skills/).
SKILLS = ("intake-expediente", "exportar-correos-etiqueta")
# Conectores MCP: (carpeta_fuente, nombre_destino)
CONECTORES = (
    ("expedientes_xl", "expedientes_xl"),
    ("email_export_mcp", "email_export_mcp"),
)
OUT = ROOT / "dist" / "plugin"
PLUGIN = OUT / "feesdefender"

# Nada que ate el bundle a una maquina o a un perfil debe viajar:
#   * `__pycache__`/`*.pyc`: residuo de ejecucion, y el .pyc lleva DENTRO la ruta
#     absoluta con la que se compilo. Excluido desde el primer dia (2026-06-22).
#   * `dxt-build`: subproducto de la OTRA via de empaquetado (la extension DXT de
#     Claude Desktop). Su `manifest.json` cablea el interprete y el PYTHONPATH del
#     perfil que lo genero, y ademas arrastra un .dxt de 29 KB que el marketplace
#     no usa. El propio handoff v5 lo clasifica como «subproducto, no tocar».
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "dxt-build")


def _copytree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=_IGNORE)


def build() -> Path:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / ".claude-plugin").mkdir(parents=True)
    (PLUGIN / ".claude-plugin").mkdir(parents=True)
    # marketplace.json -> dist/plugin/.claude-plugin/
    shutil.copy2(SRC / "marketplace.json", OUT / ".claude-plugin" / "marketplace.json")
    # plugin.json -> dist/plugin/feesdefender/.claude-plugin/
    shutil.copy2(SRC / ".claude-plugin" / "plugin.json", PLUGIN / ".claude-plugin" / "plugin.json")
    # .mcp.json -> dist/plugin/feesdefender/
    shutil.copy2(SRC / ".mcp.json", PLUGIN / ".mcp.json")
    # conectores -> dist/plugin/feesdefender/<conector>/
    for src_name, dst_name in CONECTORES:
        _copytree(ROOT / "plugins" / src_name, PLUGIN / dst_name)
    # skills -> dist/plugin/feesdefender/skills/<skill>/
    for skill in SKILLS:
        _copytree(SKILLS_DIR / skill, PLUGIN / "skills" / skill)
    return OUT


if __name__ == "__main__":
    out = build()
    print(f"[package_plugin] plugin ensamblado -> {out}")
