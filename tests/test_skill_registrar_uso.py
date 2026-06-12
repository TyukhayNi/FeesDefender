# -*- coding: utf-8 -*-
"""Tests del helper canónico de telemetría ``_shared/registrar_uso.py`` (F9).

Cubre (plan v3 §14): línea JSONL bien formada; resolución de
``FEESDEFENDER_SKILL_LOGS`` y fallback; nombres de fichero por fase; lectura de
``version`` del frontmatter.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_HELPER = (
    Path(__file__).resolve().parents[1]
    / ".claude" / "skills" / "_shared" / "registrar_uso.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("registrar_uso_shared", _HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ru = _load()


def test_logdir_usa_env(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    d = ru.log_dir("escritos-judiciales")
    assert d == tmp_path / "store" / "escritos-judiciales"


def test_logdir_repo_por_defecto(monkeypatch):
    monkeypatch.delenv("FEESDEFENDER_SKILL_LOGS", raising=False)
    d = ru.log_dir("cendoj-descarga")
    # En el repo (hay pyproject.toml) → data/_skill_logs/<skill>.
    assert d.parts[-3:] == ("data", "_skill_logs", "cendoj-descarga")


def test_log_escribe_jsonl_bien_formado(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    path = ru.log(
        "escritos-judiciales", "W-1", "generar_demanda",
        archivos=["DEMANDA_W-1.docx"], metricas={"hechos": 5}, version="1.0",
    )
    assert path is not None and path.name == "uso.jsonl"
    linea = path.read_text(encoding="utf-8").strip()
    obj = json.loads(linea)
    assert obj["skill"] == "escritos-judiciales"
    assert obj["ref"] == "W-1"
    assert obj["accion"] == "generar_demanda"
    assert obj["archivos"] == ["DEMANDA_W-1.docx"]
    assert obj["metricas"] == {"hechos": 5}
    assert obj["version"] == "1.0"
    assert obj["ts"].endswith("+00:00")  # UTC ISO-8601


def test_fase_pre_post_nombre_fichero(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    p_pre = ru.log("preparacion-juicio-oral", "W-9", "checklist", fase="pre")
    p_post = ru.log("preparacion-juicio-oral", "W-9", "checklist", fase="post")
    assert p_pre.name == "W-9_pre.jsonl"
    assert p_post.name == "W-9_post.jsonl"


def test_append_no_pisa(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    ru.log("cendoj-descarga", "W-1", "descarga")
    ru.log("cendoj-descarga", "W-2", "descarga")
    path = tmp_path / "store" / "cendoj-descarga" / "uso.jsonl"
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_skill_version_lee_frontmatter(tmp_path):
    skill_dir = tmp_path / "mi-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: mi-skill\nversion: 2.3\n---\n\n# Mi skill\n", encoding="utf-8"
    )
    assert ru.skill_version(skill_dir) == "2.3"


def test_skill_version_default_sin_campo(tmp_path):
    skill_dir = tmp_path / "mi-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: x\n---\n\n# x\n", encoding="utf-8")
    assert ru.skill_version(skill_dir) == "0.0"
