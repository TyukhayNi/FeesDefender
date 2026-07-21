"""Guard de sincronía: el `version` del frontmatter de organizar-sala-lectura
debe coincidir con la primera entrada del CHANGELOG. Motivo (backlog
robustez-velocidad ítem 2): el frontmatter quedó en 1.9 mientras el CHANGELOG
iba por 1.10 — un subagente corrió v1.8 creyéndose v1.9 (A/B invalidado).

Alcance intencionadamente acotado a esta skill: los CHANGELOG del resto del
despacho no usan un encabezado uniforme «## X.Y» (varios llevan la fecha
primero), así que un guard repo-wide daría falsos positivos ajenos a este trabajo.
"""
from __future__ import annotations

import re
from pathlib import Path

_SKILL = Path(__file__).resolve().parent.parent / ".claude/skills/organizar-sala-lectura"


def _version_frontmatter() -> str:
    txt = (_SKILL / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r'^\s*version:\s*"?([0-9][0-9.]*)"?\s*$', txt, re.M)
    assert m, "no se encontró `version:` en el frontmatter de SKILL.md"
    return m.group(1)


def _version_changelog() -> str:
    txt = (_SKILL / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r'^##\s+([0-9][0-9.]*)\b', txt, re.M)
    assert m, "no se encontró un encabezado `## X.Y` en el CHANGELOG"
    return m.group(1)


def test_version_frontmatter_coincide_con_changelog():
    assert _version_frontmatter() == _version_changelog(), (
        f"frontmatter={_version_frontmatter()} != changelog={_version_changelog()} "
        "— actualiza ambos al mismo número")
