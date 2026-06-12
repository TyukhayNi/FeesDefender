# -*- coding: utf-8 -*-
"""Tests del scaffolding de expedientes de particulares (escenario B, plan v3 F6).

Garantiza la **no divergencia** entre el camino de apertura del core E&V y el de
la skill ``preparacion-litigio-civil``: mismo árbol (``CASO_SUBDIRS``) y un
``_caso.md`` mínimo, válido y sin campos E&V. Incluye un e2e mínimo: scaffolding
de un particular → registro de un escrito → manifiesto + Navegación.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SHARED = _REPO / ".claude" / "skills" / "_shared"
_LITIGIO = _REPO / ".claude" / "skills" / "preparacion-litigio-civil" / "scripts"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


scaffold_caso = _load(_SHARED / "scaffold_caso.py", "scaffold_caso_shared")
ro = _load(_SHARED / "registrar_outputs.py", "registrar_outputs_shared2")


def test_caso_subdirs_no_diverge_del_core():
    from core import config as cfg

    assert scaffold_caso.CASO_SUBDIRS == cfg.CASO_SUBDIRS


def test_scaffold_crea_exactamente_caso_subdirs(tmp_path):
    base = scaffold_caso.scaffold(tmp_path / "exp", titulo="Asunto X")
    creados = {p.name for p in base.iterdir() if p.is_dir()}
    assert creados == set(scaffold_caso.CASO_SUBDIRS)


def test_caso_md_minimo_valido_y_sin_ev(tmp_path):
    base = scaffold_caso.scaffold(
        tmp_path / "exp", titulo="Asunto X", case_id="REF-1",
        cliente="ANA", contraparte="LUIS", organo="JPI 1", cuantia="1.000 €",
    )
    from core.utils import read_md

    fm, body = read_md(base / "00_Input" / "_caso.md")
    assert fm["tipo_expediente"] == "particular"
    assert fm["tipo"] == "caso_index"
    assert fm["case_id"] == "REF-1"
    # Sin campos E&V en el frontmatter mínimo.
    for campo_ev in ("drive", "sudespacho_expedientes", "drive_ev_team_id", "meta"):
        assert campo_ev not in fm
    assert "## Navegación" in body  # presente y vacía, lista para registrar_outputs


def test_scaffold_idempotente_no_sobrescribe(tmp_path):
    base = scaffold_caso.scaffold(tmp_path / "exp", titulo="Primero", case_id="REF-1")
    caso = base / "00_Input" / "_caso.md"
    caso.write_text(caso.read_text(encoding="utf-8") + "\n- [[demanda]]\n", encoding="utf-8")
    # Segunda llamada con otro título: no debe pisar el _caso.md existente.
    scaffold_caso.scaffold(tmp_path / "exp", titulo="Segundo", case_id="REF-2")
    texto = caso.read_text(encoding="utf-8")
    assert "Primero" in texto and "Segundo" not in texto
    assert "[[demanda]]" in texto


def test_e2e_particular_scaffold_y_registro(tmp_path):
    base = scaffold_caso.scaffold(tmp_path / "exp", titulo="Asunto X", case_id="REF-9")
    ro.registrar(str(base), [{
        "fichero": "DEMANDA_REF-9.docx", "tipo": "demanda", "perspectiva": "actora",
        "destino": "05_Procedimiento", "fuentes": ["preparacion"], "estado": "borrador",
    }])
    assert (base / "05_Procedimiento" / "_index.md").exists()
    caso = (base / "00_Input" / "_caso.md").read_text(encoding="utf-8")
    assert "[[DEMANDA_REF-9]]" in caso


def test_litigio_scaffold_cli_pone_maestros_en_02_analisis(tmp_path):
    base = tmp_path / "exp"
    r = subprocess.run(
        [sys.executable, str(_LITIGIO / "scaffold_expediente.py"),
         "--base-dir", str(base), "--tipo-escrito", "demanda",
         "--referencia", "REF-CLI", "--parte-representada", "ANA PÉREZ",
         "--posicion", "actor", "--contraparte", "LUIS GIL"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 0, r.stderr
    assert (base / "02_Analisis" / "PREPARACION_DEMANDA.md").exists()
    assert (base / "02_Analisis" / "HECHOS_DEMANDA.md").exists()
    assert (base / "00_Input" / "_caso.md").exists()
    # No quedan rastros del árbol antiguo.
    assert not (base / "00_PREPARACION").exists()
    assert not (base / "05_BORRADORES").exists()
