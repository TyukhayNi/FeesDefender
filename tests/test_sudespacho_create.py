"""Tests para funciones de creación y mapeo de tags en sudespacho."""

import pytest

from core.sudespacho_create import (
    tag_rojo_equipo,
    tag_azul_de_codigo,
    TAG_ROJO_BaRS11,
    TAG_AZUL_BARCELONA,
    TAG_AZUL_MADRID,
)


def test_tag_rojo_equipo_conocido():
    assert tag_rojo_equipo("BaRS11") == TAG_ROJO_BaRS11


def test_tag_rojo_equipo_desconocido_es_none():
    assert tag_rojo_equipo("ZzZZ99") is None


@pytest.mark.parametrize("codigo,esperado", [
    ("BaRS11", TAG_AZUL_BARCELONA),
    ("BaCR1", TAG_AZUL_BARCELONA),
    ("MaRS2", TAG_AZUL_MADRID),
])
def test_tag_azul_de_codigo(codigo, esperado):
    assert tag_azul_de_codigo(codigo) == esperado


def test_tag_azul_de_codigo_prefijo_desconocido_es_none():
    assert tag_azul_de_codigo("ZzRS1") is None
