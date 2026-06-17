# -*- coding: utf-8 -*-
"""Tests de la logica pura de scripts/check_skills.py (frescura de skills)."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def _load_check_skills():
    spec = importlib.util.spec_from_file_location(
        "check_skills", _REPO / "scripts" / "check_skills.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cs = _load_check_skills()


# --- changelog_stale ---------------------------------------------------------

def test_changelog_stale_fuente_sin_changelog():
    changed = {".claude/skills/foo/SKILL.md"}
    assert cs.changelog_stale(changed, ["foo"]) == ["foo"]


def test_changelog_stale_fuente_y_changelog_ok():
    changed = {
        ".claude/skills/foo/SKILL.md",
        ".claude/skills/foo/CHANGELOG.md",
    }
    assert cs.changelog_stale(changed, ["foo"]) == []


def test_changelog_stale_solo_changelog_no_avisa():
    changed = {".claude/skills/foo/CHANGELOG.md"}
    assert cs.changelog_stale(changed, ["foo"]) == []


def test_changelog_stale_ignora_logs():
    # los logs (datos de uso) no cuentan como 'fuente'
    changed = {".claude/skills/foo/logs/uso.jsonl"}
    assert cs.changelog_stale(changed, ["foo"]) == []


def test_changelog_stale_varias_skills():
    changed = {
        ".claude/skills/foo/SKILL.md",          # foo: fuente sin changelog
        ".claude/skills/bar/SKILL.md",          # bar: fuente + changelog -> ok
        ".claude/skills/bar/CHANGELOG.md",
    }
    assert cs.changelog_stale(changed, ["foo", "bar", "baz"]) == ["foo"]


# --- package_stale -----------------------------------------------------------

def _mk_skill(tmp_path: Path, name: str) -> Path:
    d = tmp_path / ".claude" / "skills" / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("x", encoding="utf-8")
    return d


def test_package_stale_sin_paquete(tmp_path):
    d = _mk_skill(tmp_path, "foo")
    dist = tmp_path / "dist"
    dist.mkdir()
    assert cs.package_stale([d], dist, lambda rel: True) == ["foo"]


def test_package_stale_paquete_fresco(tmp_path):
    d = _mk_skill(tmp_path, "foo")
    dist = tmp_path / "dist"
    dist.mkdir()
    pkg = dist / "foo.skill"
    pkg.write_text("zip", encoding="utf-8")
    # el paquete es mas nuevo que la fuente
    src_mtime = (d / "SKILL.md").stat().st_mtime
    os.utime(pkg, (src_mtime + 10, src_mtime + 10))
    assert cs.package_stale([d], dist, lambda rel: True) == []


def test_package_stale_fuente_modificada(tmp_path):
    d = _mk_skill(tmp_path, "foo")
    dist = tmp_path / "dist"
    dist.mkdir()
    pkg = dist / "foo.skill"
    pkg.write_text("zip", encoding="utf-8")
    # el paquete es VIEJO respecto a la fuente
    src_mtime = (d / "SKILL.md").stat().st_mtime
    os.utime(pkg, (src_mtime - 10, src_mtime - 10))
    assert cs.package_stale([d], dist, lambda rel: True) == ["foo"]
