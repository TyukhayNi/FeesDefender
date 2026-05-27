"""Tests de utilidades de frontmatter / slugify."""

from __future__ import annotations

import pytest

from core.utils import build_frontmatter, read_md, slugify, validate_case_id, write_md


def test_slugify_lower_y_separadores():
    assert slugify("Nota de Encargo — Calle Real, 12") == "nota_de_encargo_calle_real_12"


@pytest.mark.parametrize("case_id", [
    "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU",          # captación (W-XXXXXX)
    "SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros",  # OTROS
    "EV-2026-001",                                            # heredado
])
def test_validate_case_id_acepta_formatos_validos(case_id):
    assert validate_case_id(case_id) == case_id


def test_validate_case_id_rechaza_formato_invalido():
    with pytest.raises(ValueError):
        validate_case_id("caso sin formato")


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
