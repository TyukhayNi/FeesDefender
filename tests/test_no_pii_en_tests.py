"""Guard anti-regresión: ningún fichero de `tests/` ni `core/` debe contener PII real.

Reutiliza la lógica del leak-guard (`scripts/precommit_leak_guard.py`) con la blocklist
real (`data/_saneado/replacements.txt`, gitignored). Desde `MEJORAS #161` (2026-09-05) la
lista se resuelve también desde el checkout principal del repositorio, así que este test
CORRE en los worktrees y no solo en la raíz. Donde no exista en ninguna raíz (p. ej. CI sin
el secret `PII_BLOCKLIST`), el test se salta y lo dice — el escaneo efectivo corre donde la
lista está disponible: el PC del abogado y los hooks pre-commit/pre-push.

Complementa a los hooks: si alguien commitea con `--no-verify`, la suite lo caza.
Doctrina y encaje: docs/SEGURIDAD_DATOS.md (principios 3 y 7).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.precommit_leak_guard import cargar_blocklist, escanear

REPO = Path(__file__).resolve().parent.parent
DIRS = ("tests", "core")


def _ficheros_versionables() -> list[str]:
    out: list[str] = []
    for d in DIRS:
        base = REPO / d
        if not base.exists():
            continue
        for fp in base.rglob("*"):
            if not fp.is_file():
                continue
            if "__pycache__" in fp.parts or fp.suffix == ".pyc":
                continue
            out.append(str(fp.relative_to(REPO)).replace("\\", "/"))
    return out


def test_no_pii_real_en_tests_ni_core():
    if not cargar_blocklist(REPO):
        pytest.skip(
            "blocklist no disponible (data/_saneado/replacements.txt); "
            "el guard corre donde la lista existe (PC + hooks pre-commit/pre-push)"
        )
    problemas = escanear(_ficheros_versionables(), REPO)
    assert not problemas, "PII real detectada en tests/ o core/:\n" + "\n".join(problemas)
