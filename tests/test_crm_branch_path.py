"""Tests dedicados v2 — paso 8 del refactor intake v2.

Función bajo test: ``core.case_manager.crm_branch_path``.

Resuelve la ruta destino dentro de ``00_Input/05_CRM/`` para un documento
del CRM mediante estrategia híbrida de 3 niveles (ver §13.4 de
``docs/INTEGRACION_SUDESPACHO.md``):

    1. Lookup directo en ``CARPETA_ID_TO_PATH`` por ``id_carpeta``.
    2. Heurística por ``id_carpeta_label`` si la coincidencia en
       ``CRM_TREE`` es única.
    3. Fallback ``05_CRM/99_Sin categoria/<expediente_id>/``.

Estos tests fijan el contrato. No tocan disco más allá de la creación de
la carpeta del caso vía ``ensure_case`` (necesaria para tener un
``case_dir`` real bajo el que comparar paths). ``crm_branch_path`` por sí
misma NO debe materializar nada — eso queda como sanity check explícito.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixture local — recarga case_manager para que tome el casos_root del tmp.
# ---------------------------------------------------------------------------

@pytest.fixture
def cm(tmp_casos_root):
    """Devuelve ``core.case_manager`` recargado tras el reload de config.

    ``tmp_casos_root`` ya recarga ``core.config``; recargamos también
    ``case_manager`` por simetría con el patrón establecido en
    ``test_smoke_paso7.py`` (defensa frente a capturas accidentales en
    import-time).
    """
    from core import case_manager as _cm

    importlib.reload(_cm)
    return _cm


# ---------------------------------------------------------------------------
# 1. Lookup directo por id_carpeta (CARPETA_ID_TO_PATH)
# ---------------------------------------------------------------------------

def test_id_mapping_307_devuelve_demanda_civil(cm, tmp_casos_root):
    """id_carpeta="307" → Civil/1ª Instancia/Declarativo/Demanda."""
    cm.ensure_case("EV-2026-CRM-1")

    path, kind = cm.crm_branch_path("EV-2026-CRM-1", id_carpeta="307")

    expected = (
        tmp_casos_root
        / "EV-2026-CRM-1"
        / "00_Input"
        / "05_CRM"
        / "Civil"
        / "1ª Instancia"
        / "Declarativo"
        / "Demanda"
    )
    assert path == expected
    assert kind == "id_mapping"


def test_id_mapping_1_devuelve_general(cm, tmp_casos_root):
    """id_carpeta="1" → General (nivel 1 sin hijos)."""
    cm.ensure_case("EV-2026-CRM-2")

    path, kind = cm.crm_branch_path("EV-2026-CRM-2", id_carpeta="1")

    expected = tmp_casos_root / "EV-2026-CRM-2" / "00_Input" / "05_CRM" / "General"
    assert path == expected
    assert kind == "id_mapping"


def test_id_mapping_acepta_int(cm):
    """id_carpeta puede venir como int — se normaliza con str()."""
    cm.ensure_case("EV-2026-CRM-3")

    path_int, kind_int = cm.crm_branch_path("EV-2026-CRM-3", id_carpeta=307)
    path_str, kind_str = cm.crm_branch_path("EV-2026-CRM-3", id_carpeta="307")

    assert path_int == path_str
    assert kind_int == "id_mapping"
    assert kind_str == "id_mapping"


def test_id_mapping_normaliza_whitespace(cm):
    """id_carpeta=" 307 " (con whitespace) → mismo resultado que "307"."""
    cm.ensure_case("EV-2026-CRM-4")

    path_padded, kind_padded = cm.crm_branch_path(
        "EV-2026-CRM-4", id_carpeta=" 307 "
    )
    path_clean, _ = cm.crm_branch_path("EV-2026-CRM-4", id_carpeta="307")

    assert path_padded == path_clean
    assert kind_padded == "id_mapping"


# ---------------------------------------------------------------------------
# 2. Heurística por label (única vs ambigua, normalización)
# ---------------------------------------------------------------------------

def test_label_heuristic_unica_denuncia(cm, tmp_casos_root):
    """"Denuncia" aparece una sola vez en CRM_TREE → label_heuristic gana."""
    cm.ensure_case("EV-2026-CRM-5")

    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-5",
        id_carpeta=None,
        id_carpeta_label="Denuncia",
    )

    expected = (
        tmp_casos_root
        / "EV-2026-CRM-5"
        / "00_Input"
        / "05_CRM"
        / "Penal"
        / "1ª Instancia"
        / "Instruccion"
        / "Denuncia"
    )
    assert path == expected
    assert kind == "label_heuristic"


def test_label_heuristic_case_insensitive(cm, tmp_casos_root):
    """label="DENUNCIA" debe matchear igual que "Denuncia"."""
    cm.ensure_case("EV-2026-CRM-6")

    path_upper, kind_upper = cm.crm_branch_path(
        "EV-2026-CRM-6", id_carpeta_label="DENUNCIA"
    )
    path_lower, _ = cm.crm_branch_path(
        "EV-2026-CRM-6", id_carpeta_label="denuncia"
    )
    path_title, _ = cm.crm_branch_path(
        "EV-2026-CRM-6", id_carpeta_label="Denuncia"
    )

    assert path_upper == path_lower == path_title
    assert kind_upper == "label_heuristic"


def test_label_heuristic_normaliza_acentos(cm, tmp_casos_root):
    """label="Documentación RGPD LOPD" (acento) → matchea "Documentacion RGPD LOPD"."""
    cm.ensure_case("EV-2026-CRM-7")

    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-7",
        id_carpeta_label="Documentación RGPD LOPD",
    )

    expected = (
        tmp_casos_root
        / "EV-2026-CRM-7"
        / "00_Input"
        / "05_CRM"
        / "Civil"
        / "1ª Instancia"
        / "Documentacion RGPD LOPD"
    )
    assert path == expected
    assert kind == "label_heuristic"


def test_label_heuristic_ambigua_apelacion_cae_a_fallback(cm, tmp_casos_root):
    """"Apelacion" aparece en Civil y Penal → ambigua → fallback."""
    cm.ensure_case("EV-2026-CRM-8")

    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-8",
        id_carpeta_label="Apelacion",
        expediente_id="999",
    )

    expected = (
        tmp_casos_root
        / "EV-2026-CRM-8"
        / "00_Input"
        / "05_CRM"
        / "99_Sin categoria"
        / "999"
    )
    assert path == expected
    assert kind == "fallback"


def test_label_heuristic_ambigua_demanda_cae_a_fallback(cm):
    """"Demanda" aparece 3 veces (Declarativo, Monitorio, Preliminares)."""
    cm.ensure_case("EV-2026-CRM-9")

    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-9",
        id_carpeta_label="Demanda",
        expediente_id="777",
    )

    assert "99_Sin categoria" in path.as_posix()
    assert path.name == "777"
    assert kind == "fallback"


def test_label_heuristic_label_vacio_cae_a_fallback(cm):
    """label="" o None → no se intenta heurística → fallback."""
    cm.ensure_case("EV-2026-CRM-10")

    p1, k1 = cm.crm_branch_path("EV-2026-CRM-10", id_carpeta_label="", expediente_id="1")
    p2, k2 = cm.crm_branch_path("EV-2026-CRM-10", id_carpeta_label=None, expediente_id="1")

    assert k1 == "fallback"
    assert k2 == "fallback"
    assert p1 == p2


def test_label_heuristic_label_desconocido_cae_a_fallback(cm):
    """Un label que NO existe en CRM_TREE → fallback (no heurística)."""
    cm.ensure_case("EV-2026-CRM-11")

    _, kind = cm.crm_branch_path(
        "EV-2026-CRM-11",
        id_carpeta_label="EsteLabelNoExiste",
        expediente_id="42",
    )

    assert kind == "fallback"


# ---------------------------------------------------------------------------
# 3. Fallback (con y sin expediente_id)
# ---------------------------------------------------------------------------

def test_fallback_con_expediente_id(cm, tmp_casos_root):
    """Sin id ni label → fallback bajo 99_Sin categoria/<expediente_id>."""
    cm.ensure_case("EV-2026-CRM-12")

    path, kind = cm.crm_branch_path("EV-2026-CRM-12", expediente_id="648")

    expected = (
        tmp_casos_root
        / "EV-2026-CRM-12"
        / "00_Input"
        / "05_CRM"
        / "99_Sin categoria"
        / "648"
    )
    assert path == expected
    assert kind == "fallback"


def test_fallback_sin_expediente_id(cm, tmp_casos_root):
    """expediente_id=None → fallback a 99_Sin categoria sin subcarpeta."""
    cm.ensure_case("EV-2026-CRM-13")

    path, kind = cm.crm_branch_path("EV-2026-CRM-13")

    expected = (
        tmp_casos_root
        / "EV-2026-CRM-13"
        / "00_Input"
        / "05_CRM"
        / "99_Sin categoria"
    )
    assert path == expected
    assert kind == "fallback"


# ---------------------------------------------------------------------------
# 4. Composición de estrategias (id desconocido + label útil/ambiguo)
# ---------------------------------------------------------------------------

def test_id_desconocido_label_unico_usa_label_heuristic(cm, tmp_casos_root):
    """id="9999" no en mapping + label único → label_heuristic gana."""
    cm.ensure_case("EV-2026-CRM-14")

    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-14",
        id_carpeta="9999",
        id_carpeta_label="Fase oral",
        expediente_id="50",
    )

    expected = (
        tmp_casos_root
        / "EV-2026-CRM-14"
        / "00_Input"
        / "05_CRM"
        / "Penal"
        / "1ª Instancia"
        / "Fase oral"
    )
    assert path == expected
    assert kind == "label_heuristic"


def test_id_desconocido_label_ambiguo_cae_a_fallback(cm):
    """id no en mapping + label ambiguo → fallback (id_mapping NO gana)."""
    cm.ensure_case("EV-2026-CRM-15")

    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-15",
        id_carpeta="9999",
        id_carpeta_label="Apelacion",
        expediente_id="123",
    )

    assert kind == "fallback"
    assert path.name == "123"


# ---------------------------------------------------------------------------
# 5. Invariantes generales
# ---------------------------------------------------------------------------

def test_path_siempre_bajo_05_crm(cm, tmp_casos_root):
    """En todos los kinds el path queda bajo <case>/00_Input/05_CRM/."""
    cm.ensure_case("EV-2026-CRM-16")
    crm_root = tmp_casos_root / "EV-2026-CRM-16" / "00_Input" / "05_CRM"

    casos = [
        cm.crm_branch_path("EV-2026-CRM-16", id_carpeta="307"),
        cm.crm_branch_path("EV-2026-CRM-16", id_carpeta="1"),
        cm.crm_branch_path("EV-2026-CRM-16", id_carpeta_label="Denuncia"),
        cm.crm_branch_path("EV-2026-CRM-16", expediente_id="999"),
        cm.crm_branch_path("EV-2026-CRM-16"),  # sin nada
    ]

    for path, _kind in casos:
        # Path debe estar bajo crm_root (resolve para neutralizar . y ..)
        try:
            path.resolve().relative_to(crm_root.resolve())
        except ValueError:
            pytest.fail(f"Path fuera de 05_CRM/: {path}")


def test_crm_branch_path_no_crea_directorios(cm, tmp_casos_root):
    """``crm_branch_path`` es resolución pura — no debe crear nada en disco.

    (La creación física de la rama de fallback ocurre en pull_expediente_v2
    cuando vaya a escribir un fichero; aquí solo se computa el path.)
    """
    cm.ensure_case("EV-2026-CRM-17")
    fallback_dir = (
        tmp_casos_root
        / "EV-2026-CRM-17"
        / "00_Input"
        / "05_CRM"
        / "99_Sin categoria"
        / "NUEVO-EXP-ID"
    )
    assert not fallback_dir.exists()

    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-17", expediente_id="NUEVO-EXP-ID"
    )

    assert kind == "fallback"
    assert path == fallback_dir
    # El path computado existe (la subcarpeta del expediente) NO debe haberse
    # materializado por la llamada.
    assert not fallback_dir.exists()
