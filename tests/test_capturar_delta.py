# -*- coding: utf-8 -*-
"""Tests de scripts/capturar_delta.py (F10): detecta añadido/suprimido/reescrito."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

docx = pytest.importorskip("docx")

_CAP = Path(__file__).resolve().parents[1] / "scripts" / "capturar_delta.py"


def _load():
    spec = importlib.util.spec_from_file_location("capturar_delta_mod", _CAP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cd = _load()


def _docx(path: Path, parrafos: list[str]):
    d = docx.Document()
    for p in parrafos:
        d.add_paragraph(p)
    d.save(str(path))


def test_detecta_anadido_suprimido_reescrito(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    borrador = tmp_path / "ESCRITO.docx"
    firmado = tmp_path / "ESCRITO_FIRMADO.docx"
    _docx(borrador, ["HECHO PRIMERO comun", "Parrafo que se suprime", "Texto original a reescribir"])
    _docx(firmado, ["HECHO PRIMERO comun", "Texto REESCRITO por el letrado", "Parrafo nuevo anadido"])

    destino = cd.capturar("escritos-judiciales", "W-1", borrador, None)
    assert destino.name == "W-1_delta.md"
    texto = destino.read_text(encoding="utf-8")
    assert "Parrafo nuevo anadido" in texto       # añadido
    assert "Parrafo que se suprime" in texto       # suprimido
    assert "Texto REESCRITO por el letrado" in texto  # reescrito
    assert "material de expediente" in texto.lower()


def test_firmado_derivado_del_borrador(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    borrador = tmp_path / "DEMANDA.docx"
    _docx(borrador, ["uno", "dos"])
    _docx(tmp_path / "DEMANDA_FIRMADO.docx", ["uno", "dos", "tres"])
    destino = cd.capturar("escritos-judiciales", "W-2", borrador, None)  # firmado auto
    assert "tres" in destino.read_text(encoding="utf-8")


def test_falta_firmado_es_error(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    borrador = tmp_path / "X.docx"
    _docx(borrador, ["a"])
    with pytest.raises(FileNotFoundError, match="firmada"):
        cd.capturar("escritos-judiciales", "W-3", borrador, None)


def test_sin_cambios_delta_vacio(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    b = tmp_path / "I.docx"
    f = tmp_path / "I_FIRMADO.docx"
    _docx(b, ["igual uno", "igual dos"])
    _docx(f, ["igual uno", "igual dos"])
    texto = cd.capturar("escritos-judiciales", "W-4", b, None).read_text(encoding="utf-8")
    assert "0 añadidos · 0 suprimidos · 0 reescritos" in texto
