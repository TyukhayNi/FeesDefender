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


def test_sin_refs_a_docs_plan_legacy():
    """Tras la reubicacion, ningun fichero trackeado debe citar docs/PLAN_*.md
    en la raiz de docs/ (ahora viven en docs/superpowers/plans/)."""
    import subprocess
    r = subprocess.run(
        ["git", "grep", "-l", "-E", r"docs/PLAN_[A-Za-z]"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    # git grep devuelve 1 (sin match) => vacio => OK.
    ofensores = [
        ln for ln in r.stdout.splitlines()
        if ln and "test_docs_gobernanza.py" not in ln
        and "docs/superpowers/plans/2026-07-18-gobernanza-planificacion.md" not in ln
        # Excepcion documentada (D5, 2026-07-18): esta linea cita
        # ../ElContable/docs/PLAN_DESCUBRIMIENTO_API_FacturacionEV.md, un plan
        # de OTRO repo (El Contable), no uno de los 11 docs/PLAN_*.md movidos
        # aqui. Coincide con el patron por casualidad (mismo prefijo
        # "docs/PLAN_"); no existe en este repo y no se reubica.
        and "docs/superpowers/specs/2026-07-13-mcp-sudespacho-design.md" not in ln
    ]
    assert not ofensores, f"referencias a docs/PLAN_* sin actualizar: {ofensores}"
