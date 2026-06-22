"""Ensambla el plugin `feesdefender` en dist/plugin/ desde la SSOT.

Copia: plugin-src/ (metadatos) + plugins/expedientes_xl/ (conector) +
.claude/skills/intake-expediente/ (skill). Salida gitignored y reproducible.
Uso: python -m scripts.package_plugin
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "plugin-src"
CONECTOR = ROOT / "plugins" / "expedientes_xl"
SKILL = ROOT / ".claude" / "skills" / "intake-expediente"
OUT = ROOT / "dist" / "plugin"
PLUGIN = OUT / "feesdefender"

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")


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
    # conector -> dist/plugin/feesdefender/expedientes_xl/
    _copytree(CONECTOR, PLUGIN / "expedientes_xl")
    # skill -> dist/plugin/feesdefender/skills/intake-expediente/
    _copytree(SKILL, PLUGIN / "skills" / "intake-expediente")
    return OUT


if __name__ == "__main__":
    out = build()
    print(f"[package_plugin] plugin ensamblado -> {out}")
