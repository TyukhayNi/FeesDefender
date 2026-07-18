"""Tests de utilidades de frontmatter / slugify."""

from __future__ import annotations

import pytest

from core.utils import (
    build_frontmatter,
    neutralizar_case_id,
    normalize_es_phone,
    read_md,
    slugify,
    validate_case_id,
    write_md,
)


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


# ---------------------------------------------------------------------------
# neutralizar_case_id — MEJORAS_FUTURAS.md §23
# ---------------------------------------------------------------------------


class TestNeutralizarCaseId:
    @pytest.mark.parametrize("entrada, esperado", [
        # Formato OTROS con "(SIN REFERENCIA)" y guion antes de la referencia.
        (
            "SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros",
            "SaRS1 - [DIRECCION] (SIN REFERENCIA) - Otros",
        ),
        # Formato CRM estándar: referencia W-XXXXXX pegada a la dirección.
        (
            "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU",
            "BaRR3 - [DIRECCION] (W-030LFT) - Art 20 LAU",
        ),
        # Dirección con un " - " interno: la captura llega hasta la referencia.
        (
            "MaXX9 - Av. de la Paz, 1 - 3, Madrid (W-ABC123) - Devolución",
            "MaXX9 - [DIRECCION] (W-ABC123) - Devolución",
        ),
    ])
    def test_neutraliza_direccion_formato_nuevo(self, entrada, esperado):
        assert neutralizar_case_id(entrada) == esperado

    def test_resultado_sigue_siendo_case_id_valido(self):
        """El id neutralizado debe seguir pasando validate_case_id."""
        original = "SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros"
        neutralizado = neutralizar_case_id(original)
        assert validate_case_id(neutralizado) == neutralizado

    def test_formato_heredado_no_se_toca(self):
        assert neutralizar_case_id("EV-2026-001") == "EV-2026-001"

    @pytest.mark.parametrize("entrada", ["", "   ", "cadena suelta sin estructura"])
    def test_entradas_no_reconocidas_se_devuelven_intactas(self, entrada):
        assert neutralizar_case_id(entrada) == entrada

    def test_idempotente(self):
        """Neutralizar un id ya neutralizado no lo corrompe."""
        original = "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
        una_vez = neutralizar_case_id(original)
        assert neutralizar_case_id(una_vez) == una_vez


# ---------------------------------------------------------------------------
# normalize_es_phone — B3 (apertura de expediente)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,esperado", [
    ("+34 600 123 456", "600123456"),
    ("600123456", "600123456"),
    ("0034600123456", "600123456"),
    ("+34600123456", "600123456"),
    ("934 567 890", "934567890"),
    ("34600123456", "600123456"),
    ("(+34) 600-123-456", "600123456"),
    ("", ""),
])
def test_normalize_es_phone(raw, esperado):
    assert normalize_es_phone(raw) == esperado


def test_normalize_es_phone_idempotente():
    for raw in ["+34 600 123 456", "600123456", "0034600123456"]:
        una = normalize_es_phone(raw)
        assert normalize_es_phone(una) == una


def test_normalize_es_phone_extranjero_no_se_mutila():
    # No es +34: no se convierte en un ES de 9 dígitos erróneo.
    assert normalize_es_phone("+33 6 12 34 56 78") == "+33612345678"
