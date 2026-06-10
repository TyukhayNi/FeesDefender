"""Tests dedicados — routing del CRM a buckets planos (reorg 2026-06-10, D5/D6).

Funciones bajo test:

- ``core.case_manager._bucket_for``: función pura rama-canónica → bucket plano,
  con exclusión explícita de ``Preliminares`` y anti-sobrecaptura de la
  etiqueta-hoja ``Demanda``/``Oposicion``.
- ``core.case_manager.crm_branch_path``: resuelve la ruta destino dentro de
  ``00_Input/05_CRM/`` con estrategia híbrida de 3 niveles (id_mapping →
  label_heuristic → fallback) y aplana la rama resuelta con ``_bucket_for``.

Antes de la reorg el destino era la rama profunda (``Civil/1ª Instancia/
Declarativo/Demanda``); ahora es un bucket plano de un nivel (``01_Demanda``).
``crm_branch_path`` por sí misma NO debe materializar nada — sanity check
explícito al final.
"""

from __future__ import annotations

import importlib

import pytest


# ---------------------------------------------------------------------------
# Fixture local — recarga case_manager para que tome el casos_root del tmp.
# ---------------------------------------------------------------------------

@pytest.fixture
def cm(tmp_casos_root):
    """Devuelve ``core.case_manager`` recargado tras el reload de config."""
    from core import case_manager as _cm

    importlib.reload(_cm)
    return _cm


# ---------------------------------------------------------------------------
# 0. _bucket_for — función pura rama-canónica → bucket (D6)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "rama, bucket",
    [
        # Ramas con bucket dedicado
        ("Civil/1ª Instancia/Declarativo/Demanda", "01_Demanda"),
        ("Civil/1ª Instancia/Declarativo/Oposicion", "02_Contestacion"),
        ("Civil/1ª Instancia/Monitorio/Demanda", "03_Monitorio_Demanda"),
        ("Civil/1ª Instancia/Monitorio/Oposicion", "04_Monitorio_Oposicion"),
        # Preliminares — exclusión explícita (hoja + rama intermedia)
        ("Civil/Preliminares/Demanda", "05_Diligencias_Preliminares"),
        ("Civil/Preliminares", "05_Diligencias_Preliminares"),
        # Resto → 99_Otros
        ("General", "99_Otros"),
        ("Civil", "99_Otros"),
        ("Civil/1ª Instancia", "99_Otros"),
        ("Civil/1ª Instancia/Declarativo", "99_Otros"),
        ("Civil/1ª Instancia/Documentacion RGPD LOPD", "99_Otros"),
        ("Civil/1ª Instancia/Documentos", "99_Otros"),
        ("Civil/Apelacion", "99_Otros"),
        ("Civil/Ejecucion", "99_Otros"),
        ("Penal/1ª Instancia/Instruccion/Denuncia", "99_Otros"),
        ("Penal/Apelacion", "99_Otros"),
    ],
)
def test_bucket_for_mapea_rama_a_bucket(cm, rama, bucket):
    assert cm._bucket_for(rama) == bucket


def test_bucket_for_preliminares_demanda_no_va_a_01(cm):
    """Anti-sobrecaptura clave (D6): la "demanda" de Preliminares NUNCA es 01_Demanda."""
    assert cm._bucket_for("Civil/Preliminares/Demanda") == "05_Diligencias_Preliminares"
    assert cm._bucket_for("Civil/Preliminares/Demanda") != "01_Demanda"


def test_bucket_for_tolera_acentos_y_capitalizacion(cm):
    """``_normalize_label`` neutraliza acentos/mayúsculas en la rama."""
    assert cm._bucket_for("CIVIL/1ª Instancia/DECLARATIVO/DEMANDA") == "01_Demanda"
    assert cm._bucket_for("Civil/Preliminares/DEMANDA") == "05_Diligencias_Preliminares"


def test_bucket_for_demanda_solo_declarativo_va_a_01(cm):
    """Solo Declarativo/Demanda → 01; Monitorio/Demanda → 03 (no sobre-captura)."""
    assert cm._bucket_for("Civil/1ª Instancia/Declarativo/Demanda") == "01_Demanda"
    assert cm._bucket_for("Civil/1ª Instancia/Monitorio/Demanda") == "03_Monitorio_Demanda"


# ---------------------------------------------------------------------------
# 1. Lookup directo por id_carpeta (CARPETA_ID_TO_PATH) → bucket
# ---------------------------------------------------------------------------

def test_id_mapping_307_va_a_01_demanda(cm, tmp_casos_root):
    """id_carpeta="307" (Declarativo/Demanda) → bucket 01_Demanda."""
    cm.ensure_case("EV-2026-CRM-1")
    path, kind = cm.crm_branch_path("EV-2026-CRM-1", id_carpeta="307")
    expected = (
        tmp_casos_root / "EV-2026-CRM-1" / "00_Input" / "05_CRM" / "01_Demanda"
    )
    assert path == expected
    assert kind == "id_mapping"


def test_id_mapping_308_va_a_02_contestacion(cm, tmp_casos_root):
    """id_carpeta="308" (Declarativo/Oposicion) → bucket 02_Contestacion."""
    cm.ensure_case("EV-2026-CRM-308")
    path, kind = cm.crm_branch_path("EV-2026-CRM-308", id_carpeta="308")
    expected = (
        tmp_casos_root / "EV-2026-CRM-308" / "00_Input" / "05_CRM" / "02_Contestacion"
    )
    assert path == expected
    assert kind == "id_mapping"


def test_id_mapping_380_va_a_05_preliminares(cm, tmp_casos_root):
    """id_carpeta="380" (Preliminares/Demanda) → 05_Diligencias_Preliminares, NO 01_Demanda."""
    cm.ensure_case("EV-2026-CRM-380")
    path, kind = cm.crm_branch_path("EV-2026-CRM-380", id_carpeta="380")
    expected = (
        tmp_casos_root / "EV-2026-CRM-380" / "00_Input" / "05_CRM"
        / "05_Diligencias_Preliminares"
    )
    assert path == expected
    assert kind == "id_mapping"
    assert path.name != "01_Demanda"


def test_id_mapping_1_va_a_99_otros(cm, tmp_casos_root):
    """id_carpeta="1" (General) → bucket 99_Otros."""
    cm.ensure_case("EV-2026-CRM-2")
    path, kind = cm.crm_branch_path("EV-2026-CRM-2", id_carpeta="1")
    expected = tmp_casos_root / "EV-2026-CRM-2" / "00_Input" / "05_CRM" / "99_Otros"
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
    path_padded, kind_padded = cm.crm_branch_path("EV-2026-CRM-4", id_carpeta=" 307 ")
    path_clean, _ = cm.crm_branch_path("EV-2026-CRM-4", id_carpeta="307")
    assert path_padded == path_clean
    assert kind_padded == "id_mapping"


# ---------------------------------------------------------------------------
# 2. Heurística por label (única vs ambigua, normalización) → bucket
# ---------------------------------------------------------------------------

def test_label_heuristic_unica_denuncia_va_a_99_otros(cm, tmp_casos_root):
    """"Denuncia" es único en CRM_TREE → label_heuristic; Penal → 99_Otros."""
    cm.ensure_case("EV-2026-CRM-5")
    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-5", id_carpeta=None, id_carpeta_label="Denuncia",
    )
    expected = (
        tmp_casos_root / "EV-2026-CRM-5" / "00_Input" / "05_CRM" / "99_Otros"
    )
    assert path == expected
    assert kind == "label_heuristic"


def test_label_heuristic_preliminares_va_a_05(cm, tmp_casos_root):
    """label "Preliminares" (único nodo intermedio) → 05_Diligencias_Preliminares."""
    cm.ensure_case("EV-2026-CRM-PRE")
    path, kind = cm.crm_branch_path("EV-2026-CRM-PRE", id_carpeta_label="Preliminares")
    expected = (
        tmp_casos_root / "EV-2026-CRM-PRE" / "00_Input" / "05_CRM"
        / "05_Diligencias_Preliminares"
    )
    assert path == expected
    assert kind == "label_heuristic"


def test_label_heuristic_case_insensitive(cm):
    """label="DENUNCIA" debe matchear igual que "Denuncia" (mismo bucket)."""
    cm.ensure_case("EV-2026-CRM-6")
    path_upper, kind_upper = cm.crm_branch_path("EV-2026-CRM-6", id_carpeta_label="DENUNCIA")
    path_lower, _ = cm.crm_branch_path("EV-2026-CRM-6", id_carpeta_label="denuncia")
    path_title, _ = cm.crm_branch_path("EV-2026-CRM-6", id_carpeta_label="Denuncia")
    assert path_upper == path_lower == path_title
    assert kind_upper == "label_heuristic"


def test_label_heuristic_normaliza_acentos_va_a_99_otros(cm, tmp_casos_root):
    """label="Documentación RGPD LOPD" (acento) → matchea rama única → 99_Otros."""
    cm.ensure_case("EV-2026-CRM-7")
    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-7", id_carpeta_label="Documentación RGPD LOPD",
    )
    expected = (
        tmp_casos_root / "EV-2026-CRM-7" / "00_Input" / "05_CRM" / "99_Otros"
    )
    assert path == expected
    assert kind == "label_heuristic"


def test_label_heuristic_ambigua_apelacion_cae_a_fallback(cm, tmp_casos_root):
    """"Apelacion" aparece en Civil y Penal → ambigua → fallback."""
    cm.ensure_case("EV-2026-CRM-8")
    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-8", id_carpeta_label="Apelacion", expediente_id="999",
    )
    expected = (
        tmp_casos_root / "EV-2026-CRM-8" / "00_Input" / "05_CRM"
        / "99_Sin categoria" / "999"
    )
    assert path == expected
    assert kind == "fallback"


def test_label_heuristic_ambigua_demanda_cae_a_fallback(cm):
    """"Demanda" aparece 3 veces (Declarativo, Monitorio, Preliminares) → fallback.

    La etiqueta-hoja pura sobre-captura: por eso el routing es por ID, no por
    label, para las ramas con bucket dedicado.
    """
    cm.ensure_case("EV-2026-CRM-9")
    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-9", id_carpeta_label="Demanda", expediente_id="777",
    )
    assert "99_Sin categoria" in path.as_posix()
    assert path.name == "777"
    assert kind == "fallback"


def test_label_heuristic_ambigua_oposicion_cae_a_fallback(cm):
    """"Oposicion" aparece 2 veces (Declarativo, Monitorio) → fallback."""
    cm.ensure_case("EV-2026-CRM-OPO")
    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-OPO", id_carpeta_label="Oposicion", expediente_id="778",
    )
    assert kind == "fallback"
    assert path.name == "778"


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
        "EV-2026-CRM-11", id_carpeta_label="EsteLabelNoExiste", expediente_id="42",
    )
    assert kind == "fallback"


# ---------------------------------------------------------------------------
# 3. Fallback (con y sin expediente_id) — sin cambios respecto a v1
# ---------------------------------------------------------------------------

def test_fallback_con_expediente_id(cm, tmp_casos_root):
    """Sin id ni label → fallback bajo 99_Sin categoria/<expediente_id>."""
    cm.ensure_case("EV-2026-CRM-12")
    path, kind = cm.crm_branch_path("EV-2026-CRM-12", expediente_id="648")
    expected = (
        tmp_casos_root / "EV-2026-CRM-12" / "00_Input" / "05_CRM"
        / "99_Sin categoria" / "648"
    )
    assert path == expected
    assert kind == "fallback"


def test_fallback_sin_expediente_id(cm, tmp_casos_root):
    """expediente_id=None → fallback a 99_Sin categoria sin subcarpeta."""
    cm.ensure_case("EV-2026-CRM-13")
    path, kind = cm.crm_branch_path("EV-2026-CRM-13")
    expected = (
        tmp_casos_root / "EV-2026-CRM-13" / "00_Input" / "05_CRM" / "99_Sin categoria"
    )
    assert path == expected
    assert kind == "fallback"


# ---------------------------------------------------------------------------
# 4. Composición de estrategias (id desconocido + label útil/ambiguo)
# ---------------------------------------------------------------------------

def test_id_desconocido_label_unico_usa_label_heuristic(cm, tmp_casos_root):
    """id="9999" no en mapping + label único ("Fase oral", Penal) → 99_Otros."""
    cm.ensure_case("EV-2026-CRM-14")
    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-14", id_carpeta="9999", id_carpeta_label="Fase oral",
        expediente_id="50",
    )
    expected = (
        tmp_casos_root / "EV-2026-CRM-14" / "00_Input" / "05_CRM" / "99_Otros"
    )
    assert path == expected
    assert kind == "label_heuristic"


def test_id_desconocido_label_ambiguo_cae_a_fallback(cm):
    """id no en mapping + label ambiguo → fallback (id_mapping NO gana)."""
    cm.ensure_case("EV-2026-CRM-15")
    path, kind = cm.crm_branch_path(
        "EV-2026-CRM-15", id_carpeta="9999", id_carpeta_label="Apelacion",
        expediente_id="123",
    )
    assert kind == "fallback"
    assert path.name == "123"


# ---------------------------------------------------------------------------
# 4b. Override local doc_id → bucket (D11) — por encima de la carpeta del CRM
# ---------------------------------------------------------------------------

def _write_override(cm, case_id: str, mapping: dict) -> None:
    """Escribe un frontmatter mínimo con ``bucket_override`` en _caso.md."""
    import yaml as _yaml
    idx = cm.caso_path(case_id) / "00_Input" / "_caso.md"
    idx.parent.mkdir(parents=True, exist_ok=True)
    fm = {"bucket_override": mapping}
    idx.write_text(
        "---\n" + _yaml.safe_dump(fm, allow_unicode=True) + "---\n# Caso\n",
        encoding="utf-8",
    )


def test_read_bucket_overrides_lee_mapa(cm):
    cm.ensure_case("EV-OV-1")
    _write_override(cm, "EV-OV-1", {"40020": "02_Contestacion", "40021": "01_Demanda"})
    ov = cm.read_bucket_overrides("EV-OV-1")
    assert ov == {"40020": "02_Contestacion", "40021": "01_Demanda"}


def test_read_bucket_overrides_ignora_bucket_invalido(cm):
    """Un bucket que no existe se descarta (no crearía una carpeta espuria)."""
    cm.ensure_case("EV-OV-2")
    _write_override(cm, "EV-OV-2", {"1": "carpeta_inventada", "2": "01_Demanda"})
    ov = cm.read_bucket_overrides("EV-OV-2")
    assert ov == {"2": "01_Demanda"}


def test_read_bucket_overrides_vacio_sin_campo(cm):
    cm.ensure_case("EV-OV-3")
    assert cm.read_bucket_overrides("EV-OV-3") == {}


def test_override_gana_a_la_carpeta_del_crm(cm, tmp_casos_root):
    """doc_id en el override → su bucket, AUNQUE id_carpeta resolviera a otro."""
    cm.ensure_case("EV-OV-4")
    _write_override(cm, "EV-OV-4", {"40020": "02_Contestacion"})
    # id_carpeta=307 resolvería a 01_Demanda; el override manda.
    path, kind = cm.crm_branch_path(
        "EV-OV-4", id_carpeta="307", doc_id="40020",
    )
    expected = (
        tmp_casos_root / "EV-OV-4" / "00_Input" / "05_CRM" / "02_Contestacion"
    )
    assert path == expected
    assert kind == "override"


def test_override_acepta_doc_id_int(cm):
    cm.ensure_case("EV-OV-5")
    _write_override(cm, "EV-OV-5", {"40020": "01_Demanda"})
    p_int, k_int = cm.crm_branch_path("EV-OV-5", id_carpeta="308", doc_id=40020)
    assert k_int == "override"
    assert p_int.name == "01_Demanda"


def test_sin_override_resolucion_normal(cm):
    """doc_id no presente en el override → resolución estándar por id_carpeta."""
    cm.ensure_case("EV-OV-6")
    _write_override(cm, "EV-OV-6", {"99999": "01_Demanda"})
    path, kind = cm.crm_branch_path("EV-OV-6", id_carpeta="308", doc_id="40020")
    assert kind == "id_mapping"
    assert path.name == "02_Contestacion"


def test_override_con_dict_preleido(cm, tmp_casos_root):
    """El caller puede pasar el mapa ya leído (evita I/O por-doc en el pull)."""
    cm.ensure_case("EV-OV-7")
    path, kind = cm.crm_branch_path(
        "EV-OV-7", id_carpeta="307", doc_id="500",
        overrides={"500": "99_Otros"},
    )
    assert kind == "override"
    assert path.name == "99_Otros"


# ---------------------------------------------------------------------------
# 5. Invariantes generales
# ---------------------------------------------------------------------------

def test_path_siempre_bajo_05_crm(cm, tmp_casos_root):
    """En todos los kinds el path queda bajo <case>/00_Input/05_CRM/."""
    cm.ensure_case("EV-2026-CRM-16")
    crm_root = tmp_casos_root / "EV-2026-CRM-16" / "00_Input" / "05_CRM"
    casos = [
        cm.crm_branch_path("EV-2026-CRM-16", id_carpeta="307"),
        cm.crm_branch_path("EV-2026-CRM-16", id_carpeta="308"),
        cm.crm_branch_path("EV-2026-CRM-16", id_carpeta="380"),
        cm.crm_branch_path("EV-2026-CRM-16", id_carpeta="1"),
        cm.crm_branch_path("EV-2026-CRM-16", id_carpeta_label="Denuncia"),
        cm.crm_branch_path("EV-2026-CRM-16", expediente_id="999"),
        cm.crm_branch_path("EV-2026-CRM-16"),  # sin nada
    ]
    for path, _kind in casos:
        try:
            path.resolve().relative_to(crm_root.resolve())
        except ValueError:
            pytest.fail(f"Path fuera de 05_CRM/: {path}")


def test_buckets_son_de_un_solo_nivel(cm, tmp_casos_root):
    """Los destinos resueltos por ID/label son buckets planos (un segmento)."""
    cm.ensure_case("EV-2026-CRM-FLAT")
    crm_root = tmp_casos_root / "EV-2026-CRM-FLAT" / "00_Input" / "05_CRM"
    for idc in ("307", "308", "380", "1"):
        path, _ = cm.crm_branch_path("EV-2026-CRM-FLAT", id_carpeta=idc)
        rel = path.relative_to(crm_root)
        assert len(rel.parts) == 1, f"bucket no plano para id {idc}: {rel}"


def test_crm_branch_path_no_crea_directorios(cm, tmp_casos_root):
    """``crm_branch_path`` es resolución pura — no debe crear nada en disco."""
    cm.ensure_case("EV-2026-CRM-17")
    fallback_dir = (
        tmp_casos_root / "EV-2026-CRM-17" / "00_Input" / "05_CRM"
        / "99_Sin categoria" / "NUEVO-EXP-ID"
    )
    assert not fallback_dir.exists()
    path, kind = cm.crm_branch_path("EV-2026-CRM-17", expediente_id="NUEVO-EXP-ID")
    assert kind == "fallback"
    assert path == fallback_dir
    assert not fallback_dir.exists()


def test_id_mapping_no_crea_bucket(cm, tmp_casos_root):
    """Resolver a bucket por ID tampoco materializa el directorio (lazy)."""
    cm.ensure_case("EV-2026-CRM-18")
    bucket_dir = (
        tmp_casos_root / "EV-2026-CRM-18" / "00_Input" / "05_CRM" / "01_Demanda"
    )
    path, kind = cm.crm_branch_path("EV-2026-CRM-18", id_carpeta="307")
    assert path == bucket_dir
    assert kind == "id_mapping"
    assert not bucket_dir.exists()
