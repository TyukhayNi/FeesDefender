"""Tests dedicados v2 — paso 8 del refactor intake v2.

Función bajo test: ``core.case_manager.is_legacy_intake_v1``.

Detecta si un caso tiene estructura v1 (``00_Input/sudespacho_*/``). Es
el guard que bloquea ``pull_expediente_v2`` (D9) para evitar tocar
expedientes congelados (BaRR3, MaRS15) sin migración manual previa.

Contrato:

- Devuelve ``True`` si existe **alguna** subcarpeta de ``00_Input/`` cuyo
  nombre empieza por ``"sudespacho_"`` (case-sensitive, prefijo literal).
- Devuelve ``False`` en cualquier otro caso, incluyendo casos inexistentes
  y carpetas que solo contienen subdirs v2.
"""

from __future__ import annotations

import importlib

import pytest


# ---------------------------------------------------------------------------
# Fixture local — recarga case_manager para que tome el casos_root del tmp.
# ---------------------------------------------------------------------------

@pytest.fixture
def cm(tmp_casos_root):
    from core import case_manager as _cm

    importlib.reload(_cm)
    return _cm


# ---------------------------------------------------------------------------
# Detección positiva (True)
# ---------------------------------------------------------------------------

def test_carpeta_sudespacho_numerica_vacia_es_legacy(cm, tmp_casos_root):
    cm.ensure_case("CASO-LEG-1")
    (tmp_casos_root / "CASO-LEG-1" / "00_Input" / "sudespacho_123").mkdir()

    assert cm.is_legacy_intake_v1("CASO-LEG-1") is True


def test_carpeta_sudespacho_con_documentos_es_legacy(cm, tmp_casos_root):
    cm.ensure_case("CASO-LEG-2")
    sub = tmp_casos_root / "CASO-LEG-2" / "00_Input" / "sudespacho_648"
    sub.mkdir()
    (sub / "doc.pdf").write_bytes(b"%PDF dummy")
    (sub / ".pulled").write_text("{}", encoding="utf-8")

    assert cm.is_legacy_intake_v1("CASO-LEG-2") is True


def test_varias_subdirs_sudespacho_son_legacy(cm, tmp_casos_root):
    """Caso típico de proyecto v1 con varios expedientes vinculados."""
    cm.ensure_case("CASO-LEG-3")
    base = tmp_casos_root / "CASO-LEG-3" / "00_Input"
    (base / "sudespacho_100").mkdir()
    (base / "sudespacho_101").mkdir()
    (base / "sudespacho_102").mkdir()

    assert cm.is_legacy_intake_v1("CASO-LEG-3") is True


def test_sufijo_no_numerico_tambien_detecta(cm, tmp_casos_root):
    """``startswith("sudespacho_")`` no exige sufijo numérico (contrato literal)."""
    cm.ensure_case("CASO-LEG-4")
    (tmp_casos_root / "CASO-LEG-4" / "00_Input" / "sudespacho_foo").mkdir()

    assert cm.is_legacy_intake_v1("CASO-LEG-4") is True


# ---------------------------------------------------------------------------
# Detección negativa (False)
# ---------------------------------------------------------------------------

def test_caso_v2_recien_creado_no_es_legacy(cm):
    """``ensure_case`` v2 no produce ninguna subcarpeta ``sudespacho_*/``."""
    cm.ensure_case("CASO-V2-1")

    assert cm.is_legacy_intake_v1("CASO-V2-1") is False


def test_caso_con_subdirs_v2_no_es_legacy(cm, tmp_casos_root):
    """04_Manual/, 05_CRM/, 06_Entrevistas/ y _caso.md son todos v2."""
    cm.ensure_case("CASO-V2-2")
    base = tmp_casos_root / "CASO-V2-2" / "00_Input"
    # Sanity: las subdirs v2 las crea ensure_case
    assert (base / "04_Manual").is_dir()
    assert (base / "05_CRM").is_dir()
    assert (base / "06_Entrevistas").is_dir()
    assert (base / "_caso.md").is_file()

    assert cm.is_legacy_intake_v1("CASO-V2-2") is False


def test_mayuscula_inicial_no_matchea(cm, tmp_casos_root):
    """``Sudespacho_123/`` no debe matchear — el prefijo es case-sensitive."""
    cm.ensure_case("CASO-CASE-1")
    (tmp_casos_root / "CASO-CASE-1" / "00_Input" / "Sudespacho_123").mkdir()

    assert cm.is_legacy_intake_v1("CASO-CASE-1") is False


def test_sin_guion_bajo_no_matchea(cm, tmp_casos_root):
    """``sudespachoX/`` (sin _) no debe matchear — el prefijo es literal."""
    cm.ensure_case("CASO-CASE-2")
    (tmp_casos_root / "CASO-CASE-2" / "00_Input" / "sudespachoX").mkdir()

    assert cm.is_legacy_intake_v1("CASO-CASE-2") is False


def test_fichero_con_nombre_sudespacho_no_cuenta(cm, tmp_casos_root):
    """Un fichero (no directorio) llamado sudespacho_X no es legacy."""
    cm.ensure_case("CASO-FILE-1")
    fake = tmp_casos_root / "CASO-FILE-1" / "00_Input" / "sudespacho_123"
    fake.write_bytes(b"no es un directorio")

    assert cm.is_legacy_intake_v1("CASO-FILE-1") is False


def test_caso_inexistente_devuelve_false(cm):
    """Caso que no existe en disco → False (no lanza excepción)."""
    assert cm.is_legacy_intake_v1("CASO-NO-EXISTE") is False
