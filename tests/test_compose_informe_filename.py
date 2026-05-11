"""Tests del helper ``_compose_informe_filename`` (sesión 7, 2026-05-11).

Decide el nombre del fichero del informe de viabilidad en
``02_Analisis/``:

- ``case_id`` con formato CRM nuevo (``<equipo> - <dirección>
  (<id_go>) - <sufijo>``) → ``"Informe viabilidad - <case_id>.xlsx"``.
- ``case_id`` con formato legacy (``EV-2026-001``) → fallback
  ``"_informe_viabilidad.xlsx"``.

Saneamiento de caracteres prohibidos en Windows (``/ \\ : * ? " < > |``)
por defensa, aunque en la práctica el case_id no debería contenerlos.
"""

from __future__ import annotations

from core.case_manager import (
    _compose_informe_filename,
    _sanitize_filename_segment,
)


# ---------------------------------------------------------------------------
# 1. Formato CRM nuevo → nombre con case_id completo
# ---------------------------------------------------------------------------

def test_case_id_crm_nuevo_devuelve_nombre_completo():
    case_id = "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
    expected = f"Informe viabilidad - {case_id}.xlsx"
    assert _compose_informe_filename(case_id) == expected


def test_case_id_crm_nuevo_otro_equipo():
    case_id = "MaRS15 - Calle Mayor 5 (W-012345) - Negativa Oferta"
    assert _compose_informe_filename(case_id) == \
        "Informe viabilidad - MaRS15 - Calle Mayor 5 (W-012345) - Negativa Oferta.xlsx"


def test_case_id_crm_nuevo_con_acentos_y_ordinales():
    """Acentos y ordinales (`º`, `ª`) son válidos en nombres de fichero Windows."""
    case_id = "BaRS6 - Avda. Diagonal 1ª planta (W-AAA000) - Bad Debt"
    out = _compose_informe_filename(case_id)
    assert out == f"Informe viabilidad - {case_id}.xlsx"


# ---------------------------------------------------------------------------
# 2. Formato legacy → fallback simple
# ---------------------------------------------------------------------------

def test_case_id_legacy_ev_devuelve_fallback():
    assert _compose_informe_filename("EV-2026-001") == "_informe_viabilidad.xlsx"


def test_case_id_legacy_otro_formato_devuelve_fallback():
    assert _compose_informe_filename("TEST-CASE-1") == "_informe_viabilidad.xlsx"


def test_case_id_vacio_devuelve_fallback():
    assert _compose_informe_filename("") == "_informe_viabilidad.xlsx"


# ---------------------------------------------------------------------------
# 3. Saneamiento de caracteres prohibidos
# ---------------------------------------------------------------------------

def test_sanea_caracteres_prohibidos_en_case_id():
    """Si el case_id (formato nuevo) contiene caracteres prohibidos en Windows,
    se sustituyen por espacio. En la práctica esto no debería pasar — defensa."""
    case_id = "BaRR3 - C/Mayor 5 (W-XXX000) - Tipo*?"
    out = _compose_informe_filename(case_id)
    # No quedan caracteres prohibidos en el nombre final
    for ch in '/\\:*?"<>|':
        assert ch not in out, f"Carácter prohibido {ch!r} presente: {out!r}"
    # Empieza con el prefijo descriptor
    assert out.startswith("Informe viabilidad - ")
    assert out.endswith(".xlsx")


def test_sanitize_filename_segment_es_idempotente_sobre_strings_limpios():
    s = "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
    assert _sanitize_filename_segment(s) == s


def test_sanitize_filename_segment_sustituye_prohibidos_por_espacio():
    s = 'a/b\\c:d*e?f"g<h>i|j'
    out = _sanitize_filename_segment(s)
    for ch in '/\\:*?"<>|':
        assert ch not in out
