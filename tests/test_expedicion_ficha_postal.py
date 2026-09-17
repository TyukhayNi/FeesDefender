"""La ficha del destinatario postal: traducción de provincia y validación antes de gastar."""
from __future__ import annotations

import pytest

from core import expedicion_certificada as exp


@pytest.mark.parametrize("crm,codicert", [
    ("Alicante", "Alacant"), ("Valencia", "València"), ("Castellón", "Castelló"),
    ("Álava", "Araba"), ("Guipúzcoa", "Gipuzkoa"), ("Vizcaya", "Bizkaia"),
    ("Baleares (Illes)", "Islas Baleares"),
])
def test_las_siete_provincias_que_no_casan_se_traducen(crm, codicert):
    assert exp.provincia_codicert(crm) == codicert


def test_las_otras_cuarenta_y_cinco_pasan_tal_cual():
    assert exp.provincia_codicert("Barcelona") == "Barcelona"
    assert exp.provincia_codicert("Madrid") == "Madrid"


def test_una_provincia_vacia_se_rechaza_en_el_plan_y_no_en_el_422():
    with pytest.raises(exp.ExpedicionError):
        exp.ficha_postal({"nombre": "X", "direccion": "C 1", "poblacion": "P",
                          "provincia": "", "cp": "08001"})


def test_un_domicilio_sin_direccion_se_rechaza():
    with pytest.raises(exp.ExpedicionError):
        exp.ficha_postal({"nombre": "X", "direccion": "", "poblacion": "P",
                          "provincia": "Barcelona", "cp": "08001"})


def test_la_ficha_postal_lleva_pais_espana_siempre():
    f = exp.ficha_postal({"nombre": "X", "direccion": "C 1", "poblacion": "P",
                          "provincia": "Valencia", "cp": "46001"})
    assert f["pais"] == "España" and f["provincia"] == "València"


@pytest.mark.parametrize("bruto,esperado", [
    ("665130883", "34665130883"), ("34665130883", "34665130883"),
    ("+34 665 130 883", "34665130883"), ("665 130 883", "34665130883"),
    ("0034665130883", "34665130883"), ("0034 665 130 883", "34665130883"),
])
def test_el_movil_se_normaliza_con_prefijo(bruto, esperado):
    assert exp.movil_normalizado(bruto) == esperado


@pytest.mark.parametrize("bruto", ["933010203", "", None, "600", "no es un movil", "0034933010203"])
def test_lo_que_no_es_un_movil_espanol_devuelve_None(bruto):
    assert exp.movil_normalizado(bruto) is None


def test_nombre_con_solo_espacios_genera_fallback_correcto():
    """El fallback '(sin nombre)' debe activarse con cadena de espacios."""
    with pytest.raises(exp.ExpedicionError) as exc:
        exp.ficha_postal({"nombre": "   ", "direccion": "C 1", "poblacion": "P",
                          "provincia": "Barcelona", "cp": "08001"})
    assert "(sin nombre)" in str(exc.value)
