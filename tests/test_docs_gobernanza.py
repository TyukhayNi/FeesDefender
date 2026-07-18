"""Guards de gobernanza de docs: frontmatter estado: valido en docs/*.md."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_ESTADOS = {"vigente", "historico", "aparcado", "revisar"}
_RE_ESTADO = re.compile(r"^estado:\s*(\S+)\s*$", re.MULTILINE)


def _docs_con_frontmatter():
    """docs/*.md de nivel superior que llevan frontmatter (--- al inicio)."""
    for p in sorted((ROOT / "docs").glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        if txt.startswith("---"):
            yield p, txt


def test_estado_frontmatter_valido():
    malos = []
    for p, txt in _docs_con_frontmatter():
        m = _RE_ESTADO.search(txt)
        if not m or m.group(1) not in _ESTADOS:
            malos.append(p.name)
    assert not malos, f"docs con estado: ausente o invalido: {malos}"
