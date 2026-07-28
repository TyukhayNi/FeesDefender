"""Tests del helper ``_compose_informe_filename`` (sesión 7, 2026-05-11;
política de nombre revisada el 2026-07-28 por MAX_PATH de Office).

Decide el nombre del fichero del informe de viabilidad en ``02_Analisis/``:

- ``case_id`` con formato CRM nuevo (``<equipo> - <dirección> (<id_go>) -
  <sufijo>``) y con ID GO resoluble → ``"Informe viabilidad - <id_go>.xlsx"``.
- ``case_id`` con formato legacy (``EV-2026-001``), o sin ID GO resoluble
  (``(SIN REFERENCIA)``) → fallback ``"_informe_viabilidad.xlsx"``.

**Por qué solo el ID GO y no el case_id completo** (2026-07-28): el fichero
vive en ``<CASOS>/<ciudad>/<case_id>/02_Analisis/``, así que repetir el
case_id en el nombre no añade información y cuesta ~85 caracteres. Con el
case_id completo, el informe de W-02XOR7 alcanzaba 269 caracteres de ruta y
**Excel se negaba a abrirlo**: Office no es long-path aware y se rinde en 260
aunque el sistema de ficheros admita más (``LongPathsEnabled=1``). El ID GO
mantiene la identidad del caso cuando el fichero viaja suelto (adjunto a un
correo) a coste de 8 caracteres.

Saneamiento de caracteres prohibidos en Windows (``/ \\ : * ? " < > |``)
por defensa, aunque en la práctica el case_id no debería contenerlos.
"""

from __future__ import annotations

from pathlib import Path

from core.case_manager import (
    RUTA_OFFICE_MAX,
    _avisar_si_ruta_larga,
    _compose_informe_filename,
    _find_informe_existente,
    _parse_id_go_from_case_id,
    _sanitize_filename_segment,
)

# Los case_id reales llevan la dirección del inmueble. Aquí se sustituye por
# relleno conservando la **longitud exacta**, que es lo único que reproduce el
# bug; la identidad del caso la da el W-code, como manda la higiene de datos
# del proyecto (`docs/SEGURIDAD_DATOS.md`).
CASE_ID_XOR7 = f"BaRS8 - {'X' * 35} (W-02XOR7) - Negativa oferta aceptada"  # 81 car.
CASE_ID_TH0W = f"VaRS3 - {'X' * 57} (W-02TH0W) - Negativa oferta"           # 94 car.
CASE_ID_SIN_REF = f"SaRS1 - {'X' * 29} - (SIN REFERENCIA) - Otros"


# ---------------------------------------------------------------------------
# 1. Formato CRM nuevo → nombre con solo el ID GO
# ---------------------------------------------------------------------------

def test_case_id_crm_nuevo_usa_solo_el_id_go():
    case_id = "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
    assert _compose_informe_filename(case_id) == "Informe viabilidad - W-030LFT.xlsx"


def test_case_id_crm_nuevo_otro_equipo():
    case_id = "MaRS15 - Calle Mayor 5 (W-012345) - Negativa Oferta"
    assert _compose_informe_filename(case_id) == "Informe viabilidad - W-012345.xlsx"


def test_id_go_explicito_tiene_prioridad_sobre_el_del_case_id():
    """``ensure_case`` conoce el ``id_go`` efectivo del frontmatter; si difiere
    del que arrastra el case_id, manda el explícito."""
    case_id = f"BaRS8 - {'X' * 35} (W-000000) - Negativa oferta aceptada"
    assert _compose_informe_filename(case_id, "W-02XOR7") == \
        "Informe viabilidad - W-02XOR7.xlsx"


def test_id_go_explicito_invalido_cae_al_del_case_id():
    case_id = "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
    assert _compose_informe_filename(case_id, "no-es-un-id") == \
        "Informe viabilidad - W-030LFT.xlsx"


def test_case_id_con_acentos_y_ordinales_no_contamina_el_nombre():
    """Acentos y ordinales del case_id ya no llegan al nombre del fichero."""
    case_id = "BaRS6 - Avda. Diagonal 1ª planta (W-AAA000) - Bad Debt"
    assert _compose_informe_filename(case_id) == "Informe viabilidad - W-AAA000.xlsx"


# ---------------------------------------------------------------------------
# 2. Fallbacks → nombre simple con underscore inicial
# ---------------------------------------------------------------------------

def test_case_id_legacy_ev_devuelve_fallback():
    assert _compose_informe_filename("EV-2026-001") == "_informe_viabilidad.xlsx"


def test_case_id_legacy_otro_formato_devuelve_fallback():
    assert _compose_informe_filename("TEST-CASE-1") == "_informe_viabilidad.xlsx"


def test_case_id_vacio_devuelve_fallback():
    assert _compose_informe_filename("") == "_informe_viabilidad.xlsx"


def test_crm_nuevo_sin_referencia_devuelve_fallback():
    """Caso real (SaRS1): formato CRM nuevo pero sin ID GO asignado. Mejor el
    fallback que un ``Informe viabilidad - SIN REFERENCIA.xlsx``."""
    assert _compose_informe_filename(CASE_ID_SIN_REF) == "_informe_viabilidad.xlsx"


# ---------------------------------------------------------------------------
# 3. Extracción del ID GO
# ---------------------------------------------------------------------------

def test_parse_id_go_extrae_del_parentesis():
    assert _parse_id_go_from_case_id(CASE_ID_XOR7) == "W-02XOR7"


def test_parse_id_go_tolera_espacio_antes_del_parentesis():
    """Convención real inconsistente: unos case_ids llevan ``- (W-...)``."""
    assert _parse_id_go_from_case_id(
        f"BaRS3 - {'X' * 22} - (W-02MA0R) - Bad debt"
    ) == "W-02MA0R"


def test_parse_id_go_sin_id_devuelve_none():
    assert _parse_id_go_from_case_id(CASE_ID_SIN_REF) is None
    assert _parse_id_go_from_case_id("") is None


# ---------------------------------------------------------------------------
# 4. La ruta resultante cabe en el presupuesto de Office
# ---------------------------------------------------------------------------

_DRIVE_CASOS = "G:/Unidades compartidas/EXPEDIENTES - TYUKHAY LEGAL/CASOS"


def test_el_caso_que_rompio_excel_ahora_cabe():
    """Regresión del bug real: W-02XOR7 daba 269 caracteres y Excel no lo abría."""
    case_dir = Path(f"{_DRIVE_CASOS}/Barcelona/{CASE_ID_XOR7}")
    destino = case_dir / "02_Analisis" / _compose_informe_filename(CASE_ID_XOR7)
    # La ruta original medía 269; el nombre largo era el 40 % del total.
    assert len(str(case_dir / "02_Analisis" / f"Informe viabilidad - {CASE_ID_XOR7}.xlsx")) == 269
    assert len(str(destino)) <= RUTA_OFFICE_MAX, \
        f"{len(str(destino))} caracteres: sigue fuera del presupuesto de Office"


def test_el_caso_mas_largo_del_drive_tambien_cabe():
    """VaRS3 es el peor case_id real: 94 caracteres de case_id."""
    case_dir = Path(f"{_DRIVE_CASOS}/Valencia/{CASE_ID_TH0W}")
    destino = case_dir / "02_Analisis" / _compose_informe_filename(CASE_ID_TH0W)
    assert len(str(destino)) <= RUTA_OFFICE_MAX


# ---------------------------------------------------------------------------
# 5. Guardarraíl de longitud de ruta (avisa, no aborta)
# ---------------------------------------------------------------------------

def test_avisar_si_ruta_larga_calla_con_ruta_corta(caplog):
    assert _avisar_si_ruta_larga(Path("G:/x/corta.xlsx")) is False
    assert caplog.records == []


def test_avisar_si_ruta_larga_avisa_y_no_lanza(caplog):
    larga = Path("G:/" + "d" * (RUTA_OFFICE_MAX + 10) + "/informe.xlsx")
    assert _avisar_si_ruta_larga(larga) is True
    assert any("Excel" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# 6. Detección de informe preexistente (evita duplicar la plantilla)
# ---------------------------------------------------------------------------

def test_find_informe_existente_detecta_el_nombre_nuevo(tmp_path):
    (tmp_path / "Informe viabilidad - W-02XOR7.xlsx").write_bytes(b"x")
    found = _find_informe_existente(tmp_path)
    assert found is not None and found.name == "Informe viabilidad - W-02XOR7.xlsx"


def test_find_informe_existente_detecta_el_nombre_largo_legacy(tmp_path):
    """Casos ya abiertos antes del 2026-07-28 llevan el case_id completo. Hay que
    reconocerlos o ``ensure_case`` dejaría una segunda plantilla en blanco al lado
    del informe que el abogado ya ha trabajado."""
    legacy = f"Informe viabilidad - {CASE_ID_XOR7}.xlsx"
    (tmp_path / legacy).write_bytes(b"x")
    found = _find_informe_existente(tmp_path)
    assert found is not None and found.name == legacy


def test_find_informe_existente_detecta_el_fallback_y_el_nombre_manual(tmp_path):
    (tmp_path / "_informe_viabilidad.xlsx").write_bytes(b"x")
    assert _find_informe_existente(tmp_path) is not None

    otro = tmp_path / "otro"
    otro.mkdir()
    # Nombre puesto a mano en el Drive (caso real BaRS8, en mayúsculas)
    (otro / f"INFORME VIABILIDAD {CASE_ID_XOR7}.xlsx").write_bytes(b"x")
    assert _find_informe_existente(otro) is not None


def test_find_informe_existente_ignora_el_informe_llm(tmp_path):
    """El informe LLM es un artefacto paralelo: no debe impedir que se copie la
    plantilla del informe humano."""
    (tmp_path / "Informe viabilidad LLM - W-02XOR7.xlsx").write_bytes(b"x")
    assert _find_informe_existente(tmp_path) is None


def test_find_informe_existente_ignora_el_cuestionario_y_carpeta_vacia(tmp_path):
    assert _find_informe_existente(tmp_path) is None
    (tmp_path / "_cuestionario_viabilidad.xlsx").write_bytes(b"x")
    assert _find_informe_existente(tmp_path) is None
    assert _find_informe_existente(tmp_path / "no-existe") is None


# ---------------------------------------------------------------------------
# 7. Saneamiento de caracteres prohibidos
# ---------------------------------------------------------------------------

def test_sanitize_filename_segment_es_idempotente_sobre_strings_limpios():
    s = "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
    assert _sanitize_filename_segment(s) == s


def test_sanitize_filename_segment_sustituye_prohibidos_por_espacio():
    s = 'a/b\\c:d*e?f"g<h>i|j'
    out = _sanitize_filename_segment(s)
    for ch in '/\\:*?"<>|':
        assert ch not in out


def test_nombre_final_nunca_lleva_caracteres_prohibidos():
    case_id = "BaRR3 - C/Mayor 5 (W-XXX000) - Tipo*?"
    out = _compose_informe_filename(case_id)
    for ch in '/\\:*?"<>|':
        assert ch not in out, f"Carácter prohibido {ch!r} presente: {out!r}"
    assert out == "Informe viabilidad - W-XXX000.xlsx"
