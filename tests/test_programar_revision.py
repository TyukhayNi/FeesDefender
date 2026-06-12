# -*- coding: utf-8 -*-
"""Tests de _shared/programar_revision.py (F11): plazos por tipo de acto + descriptor."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_HELPER = (
    Path(__file__).resolve().parents[1]
    / ".claude" / "skills" / "_shared" / "programar_revision.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("programar_revision_shared", _HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pr = _load()


def test_plazos_por_tipo_de_acto():
    assert pr.fecha_revision("ap", "2026-07-01") == "2026-07-04"      # +3
    assert pr.fecha_revision("juicio", "2026-07-01") == "2026-07-08"  # +7
    assert pr.fecha_revision("escrito", "2026-07-01") == "2026-07-16" # +15


def test_tipo_invalido():
    with pytest.raises(ValueError, match="tipo-acto"):
        pr.fecha_revision("recurso", "2026-07-01")


def test_descriptor_y_fichero(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    desc, destino = pr.programar(
        "escritos-judiciales", "W-1", "escrito", "2026-07-01",
        borrador="C:/x/05_Procedimiento/DEMANDA.docx",
    )
    assert desc["fireAt"] == "2026-07-16"
    assert desc["taskId"] == "revision-escritos-judiciales-W-1"
    assert "checklist_post" in desc["prompt"]
    assert "capturar_delta.py" in desc["prompt"]  # borrador → incluye el delta
    assert destino.name == "W-1_schedule.json"
    en_disco = json.loads(destino.read_text(encoding="utf-8"))
    assert en_disco["fireAt"] == "2026-07-16"


def test_descriptor_sin_borrador_omite_delta(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    desc, _ = pr.programar("preparacion-juicio-oral", "W-9", "juicio", "2026-07-01")
    assert desc["fireAt"] == "2026-07-08"
    assert "capturar_delta.py" not in desc["prompt"]
