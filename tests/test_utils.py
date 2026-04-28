"""Tests de utilidades de frontmatter / slugify."""

from __future__ import annotations

from core.utils import build_frontmatter, read_md, slugify, write_md


def test_slugify_lower_y_separadores():
    assert slugify("Nota de Encargo — Calle Real, 12") == "nota_de_encargo_calle_real_12"


def test_round_trip_frontmatter(tmp_path):
    p = tmp_path / "demo.md"
    write_md(p, {"case_id": "X", "tipo": "demo", "lista": [1, 2, 3]}, "# Hola\n\nMundo")
    meta, body = read_md(p)
    assert meta["case_id"] == "X"
    assert meta["lista"] == [1, 2, 3]
    assert "Hola" in body


def test_build_frontmatter_unicode():
    fm = build_frontmatter({"titulo": "Reclamación de honorarios — E&V"})
    assert "Reclamación" in fm
