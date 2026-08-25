"""Contrato unitario de la primitiva de mutex por caso (decisión D2 del §24)."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
AHORA = "2026-08-25T12:00:00Z"
W = "W-MUTEX1"


@pytest.fixture
def raiz(tmp_path):
    return tmp_path / "locks"


def _requisitos() -> dict[str, str]:
    """`{nombre: especificador}` parseado de verdad, no por subcadena.

    `"filelock" in texto` pasaría con el nombre dentro de un comentario o como
    subcadena de otro paquete (R10/H10-10). `packaging` es la única lectura que
    acredita que un clon instalaría algo.
    """
    from packaging.requirements import Requirement
    reqs = {}
    for linea in io.open(RAIZ / "requirements.txt", encoding="utf-8"):
        linea = linea.split("#", 1)[0].strip()
        if not linea:
            continue
        r = Requirement(linea)
        reqs[r.name.lower().replace("_", "-")] = str(r.specifier)
    return reqs


def test_filelock_esta_declarado_con_version_fijada():
    reqs = _requisitos()
    assert "filelock" in reqs, (
        "core/casos/case_mutex.py importa filelock y requirements.txt no lo declara")
    assert ">=3.29" in reqs["filelock"], (
        "la versión se fija: el backend Windows se midió en 3.29.0 y `>=3.12` no lo "
        "reproduce (R10/H10-06)")


def test_psutil_NO_se_declara():
    """Se retiró con el `boot_id` (§0.2). Un requisito sin importador es ruido."""
    assert "psutil" not in _requisitos()
