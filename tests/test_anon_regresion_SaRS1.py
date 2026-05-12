# -*- coding: utf-8 -*-
"""Test de regresión sobre el primer fixture gold-standard del proyecto.

El caso SaRS1 (Castelar 37-39, Santander) es el primer expediente real que
pasa por el motor `core/anon/` íntegro (OCR + split + anonimización). H5
del plan `docs/PLAN_SaRS1_anon_pipeline.md` fija el output del motor a
fecha del commit `d22febd` (cierre de H3) como referencia inmutable de
regresión.

Política del fixture: local-only. El directorio `tests/fixtures/anon/SaRS1/`
está en `.gitignore` (decisión D-H5-1 — opción a del Pendiente C1 del plan
§13). Razón: el fixture contiene PII real del expediente, incluso en los
.md "anonimizados" cuyo `_mapa_caso.json` la incluye. Si el directorio no
está presente localmente, este módulo hace `pytest.skip()` colectivo.

Layout esperado del fixture::

    tests/fixtures/anon/SaRS1/
    ├── input/
    │   ├── Demanda_Std_1_ocr.pdf
    │   ├── Demanda_Std_2_ocr.pdf
    │   └── _split/
    │       ├── Demanda_Std_1_ocr/
    │       │   ├── 01_CEDULA_EMPLAZAMIENTO_01.pdf
    │       │   ├── 02_DECRETO_01.pdf
    │       │   └── 03_DEMANDA_01.pdf
    │       └── Demanda_Std_2_ocr/
    │           └── 01_DOC_ANEXO_01.pdf
    ├── expected/
    │   ├── 01_cedula_emplazamiento_01.md   (output bruto motor, pre-H5)
    │   ├── 02_decreto_01.md
    │   ├── 03_demanda_01.md
    │   ├── 01_doc_anexo_01.md
    │   └── _mapa_caso.json
    ├── expected_corregido/                  (output post-correccion H5; doc)
    │   └── ...
    └── REVISION.md                          (fichero forense del expediente)

El test reproduce H4 (anonimización de las 4 piezas del split con mapa
compartido) y compara con `expected/`. La comparación es página a página
para los .md y entrada a entrada para el mapa, tolerando diferencias en
los metadatos volátiles (timestamps).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

# Localizar fixture relativo a la raíz del proyecto
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = _PROJECT_ROOT / "tests" / "fixtures" / "anon" / "SaRS1"
INPUT_SPLIT_DIR = FIXTURE_DIR / "input" / "_split"
EXPECTED_DIR = FIXTURE_DIR / "expected"

# IDs de pieza esperadas (consistentes con H2/H4 del plan)
PIEZAS_ESPERADAS = [
    (
        "Demanda_Std_1_ocr/01_CEDULA_EMPLAZAMIENTO_01.pdf",
        "01_cedula_emplazamiento_01.md",
    ),
    (
        "Demanda_Std_1_ocr/02_DECRETO_01.pdf",
        "02_decreto_01.md",
    ),
    (
        "Demanda_Std_1_ocr/03_DEMANDA_01.pdf",
        "03_demanda_01.md",
    ),
    (
        "Demanda_Std_2_ocr/01_DOC_ANEXO_01.pdf",
        "01_doc_anexo_01.md",
    ),
]

CASE_ID_REGRESION = "SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros"


def _fixture_disponible() -> bool:
    """True si el fixture local está presente y completo."""
    if not FIXTURE_DIR.is_dir():
        return False
    if not INPUT_SPLIT_DIR.is_dir() or not EXPECTED_DIR.is_dir():
        return False
    for pdf_rel, _md in PIEZAS_ESPERADAS:
        if not (INPUT_SPLIT_DIR / pdf_rel).is_file():
            return False
    if not (EXPECTED_DIR / "_mapa_caso.json").is_file():
        return False
    return True


# Skip colectivo del módulo si el fixture no está localmente disponible.
# Política decidida en H5 (D-H5-1 / Pendiente C1 §13 del plan).
pytestmark = pytest.mark.skipif(
    not _fixture_disponible(),
    reason=(
        "Fixture gold-standard SaRS1 no presente localmente. "
        "Contiene PII real — directorio en .gitignore. "
        "Ver docs/PLAN_SaRS1_anon_pipeline.md §8 (H5) y REVISION.md "
        "del fixture para reconstruirlo."
    ),
)


# ---------------------------------------------------------------------------
# Helpers de normalización para comparación tolerante a metadatos volátiles
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_FECHA_FIELD_RE = re.compile(r"^fecha:\s*.+$", re.MULTILINE)


def _normalizar_md(texto: str) -> str:
    """Elimina campos del frontmatter que son volátiles entre ejecuciones."""
    return _FECHA_FIELD_RE.sub("fecha: <FECHA>", texto)


def _normalizar_mapa(mapa: dict) -> dict:
    """Devuelve solo los campos estables del mapa para comparación."""
    return {
        "mapa": dict(mapa.get("mapa", {})),
        "mapa_directo": dict(mapa.get("mapa_directo", {})),
        "contadores": dict(mapa.get("contadores", {})),
        "protegidos": list(mapa.get("protegidos", [])),
    }


# ---------------------------------------------------------------------------
# Test principal
# ---------------------------------------------------------------------------


def test_anon_regresion_sars1_motor_estable(tmp_path):
    """Regresión del motor sobre las 4 piezas split de SaRS1.

    Reproduce la lógica de H4 del plan (Opción B: listado explícito de
    piezas con mapa compartido — el wrapper `anonimizar_caso` ignora
    `_split/` por la regla de paths con `_`, ver `core/anon/api.py::_listar_documentos`).

    Esperado: cada .md generado coincide con el del fixture `expected/`
    (output bruto del motor a fecha del commit `d22febd` de H3) tras
    normalizar el campo `fecha:` del frontmatter. El `_mapa_caso.json`
    final coincide entrada a entrada en `mapa`, `mapa_directo`,
    `contadores` y `protegidos`.
    """
    # Imports diferidos para evitar coste de spaCy si el módulo entero hace skip.
    from core.anon.api import anonimizar_documento
    from core.anon.mapa_caso import MapaEntidades, guardar_mapa_caso

    # `validate_case_id` rechaza la categoría OTROS (case_id con
    # "(SIN REFERENCIA)") por el bug §12 de MEJORAS_FUTURAS.md, pendiente
    # de hilo dedicado. Aplicamos el mismo monkey-patch local que H4
    # mientras el bug no se arregle.
    import core.anon.api as _api_mod
    original_validate = _api_mod.validate_case_id

    def _validate_passthrough(case_id: str, *args, **kwargs) -> str:  # noqa: ARG001
        return case_id

    _api_mod.validate_case_id = _validate_passthrough

    # El motor escribe el .md a caso_path(case_id) / "06_Anonimizado".
    # Para no contaminar data/CASOS/ con un fixture, monkey-patcheamos
    # caso_path en TODOS los módulos que lo importan vía
    # `from core.case_manager import caso_path` (vinculan referencia
    # local). Hoy son al menos `core.anon.api` y `core.anon.mapa_caso`.
    import core.anon.mapa_caso as _mapa_mod

    salida_tmp = tmp_path / "out_caso"
    salida_tmp.mkdir(parents=True, exist_ok=True)
    (salida_tmp / "06_Anonimizado").mkdir()

    def _caso_path_fake(case_id: str) -> Path:  # noqa: ARG001
        return salida_tmp

    original_caso_path_api = _api_mod.caso_path
    original_caso_path_mapa = _mapa_mod.caso_path
    _api_mod.caso_path = _caso_path_fake
    _mapa_mod.caso_path = _caso_path_fake

    try:
        # Mapa compartido entre piezas (igual que H4).
        mapa = MapaEntidades()

        # Ejecutar el motor sobre las 4 piezas.
        for pdf_rel, md_esperado in PIEZAS_ESPERADAS:
            ruta_pdf = INPUT_SPLIT_DIR / pdf_rel
            res = anonimizar_documento(
                case_id=CASE_ID_REGRESION,
                ruta_origen=ruta_pdf,
                tipo_proc="Juicio Ordinario",
                mapa_caso=mapa,
                politica="REPROCESAR",
            )
            assert res["ok"], (
                f"Anonimización falló para {pdf_rel}: "
                f"alertas={res.get('alertas')} error={res.get('error')}"
            )
            assert res["ruta_md"] is not None
            assert res["ruta_md"].name == md_esperado, (
                f"Slug inesperado: {res['ruta_md'].name} != {md_esperado}"
            )

        # Persistir el mapa al directorio temporal (réplica de H4).
        # Firma real: guardar_mapa_caso(case_id, mapa) -> Path. La ruta se
        # deriva internamente vía caso_path (que monkey-patcheamos arriba),
        # por lo que el .json acaba en salida_tmp/06_Anonimizado/.
        ruta_mapa = guardar_mapa_caso(CASE_ID_REGRESION, mapa)
        assert ruta_mapa.is_file()

        # ---- Comparación contra expected/ ----
        # 1) Cada .md generado vs expected
        for _pdf_rel, md_esperado in PIEZAS_ESPERADAS:
            ruta_generado = salida_tmp / "06_Anonimizado" / md_esperado
            ruta_referencia = EXPECTED_DIR / md_esperado
            assert ruta_generado.is_file(), (
                f"El motor no generó {md_esperado}"
            )
            assert ruta_referencia.is_file(), (
                f"Falta referencia en fixture: {ruta_referencia}"
            )
            texto_gen = _normalizar_md(
                ruta_generado.read_text(encoding="utf-8")
            )
            texto_ref = _normalizar_md(
                ruta_referencia.read_text(encoding="utf-8")
            )
            assert texto_gen == texto_ref, (
                f"Regresión detectada en {md_esperado}. "
                f"Diff de longitud: gen={len(texto_gen)} ref={len(texto_ref)}. "
                f"Si el cambio es intencional, regenerar el fixture "
                f"siguiendo H4+H5 del plan y commitear con justificación."
            )

        # 2) Mapa generado vs expected
        mapa_gen = json.loads(ruta_mapa.read_text(encoding="utf-8"))
        mapa_ref = json.loads(
            (EXPECTED_DIR / "_mapa_caso.json").read_text(encoding="utf-8")
        )
        assert _normalizar_mapa(mapa_gen) == _normalizar_mapa(mapa_ref), (
            "Regresión detectada en _mapa_caso.json. Las entradas mapa/"
            "mapa_directo/contadores/protegidos divergen de la referencia."
        )
    finally:
        _api_mod.validate_case_id = original_validate
        _api_mod.caso_path = original_caso_path_api
        _mapa_mod.caso_path = original_caso_path_mapa
