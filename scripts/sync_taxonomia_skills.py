# scripts/sync_taxonomia_skills.py
"""Genera la referencia de taxonomía de las skills desde el canon.

Fuente: core/config.py::TAXONOMIA_EV (lista cerrada) + data/_prompts/criterio_clasificacion_ev.md
(enrutado PBC por parte + jerarquía de fecha + naming). Destino: la copia en cada skill
(p. ej. .claude/skills/organizar-sala-lectura/references/taxonomia_ev.md). NO editar la
copia a mano: edita el canon y re-genera. El gate de check_skills detecta el drift.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import TAXONOMIA_EV  # noqa: E402

_CANON = ROOT / "data" / "_prompts" / "criterio_clasificacion_ev.md"
# Skills cuya referencia de taxonomía se sincroniza desde el canon.
DESTINOS = [
    ROOT / ".claude" / "skills" / "organizar-sala-lectura" / "references" / "taxonomia_ev.md",
]


def _render() -> str:
    cats = "\n".join(f"- `{c}`" for c in TAXONOMIA_EV)
    canon = _CANON.read_text(encoding="utf-8")
    return (
        "<!-- GENERADO desde data/_prompts/criterio_clasificacion_ev.md + core/config.py::TAXONOMIA_EV "
        "por scripts/sync_taxonomia_skills.py — NO EDITAR A MANO -->\n\n"
        "# Taxonomía E&V + criterio de clasificación (generado)\n\n"
        "## Las categorías (set cerrado = `TAXONOMIA_EV`)\n\n"
        f"{cats}\n\n"
        "(No existe el `02`; se respeta la numeración de E&V.)\n\n"
        f"{canon}"
    )


def generar(destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(_render(), encoding="utf-8")
    return destino


def main() -> int:
    for d in DESTINOS:
        generar(d)
        print(f"taxonomía sincronizada → {d.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
