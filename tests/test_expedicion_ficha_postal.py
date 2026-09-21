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


# ---------------------------------------------------------------------------------
# H-06 (revisión adversarial r2). `clientes_contrarios` separa el nombre en tres
# campos (docs/CRM_SUDESPACHO_ATLAS.md § clientes_contrarios): "nombre", "1apellido",
# "2apellido". El código leía solo "nombre" y el requerido salía con únicamente su
# nombre de pila en una comunicación jurídica irreversible. Las fixtures de arriba
# usan "X" -- un solo token, sin apellidos -- así que no lo revelaban: se cubre aquí
# con nombre y apellidos por separado, como los devuelve el CRM real.
# ---------------------------------------------------------------------------------

@pytest.mark.parametrize("parte,esperado", [
    ({"nombre": "ANA", "1apellido": "LOPEZ", "2apellido": "GIL"}, "ANA LOPEZ GIL"),
    ({"nombre": "ANA", "1apellido": "LOPEZ", "2apellido": ""}, "ANA LOPEZ"),
    ({"nombre": "ANA", "1apellido": "LOPEZ"}, "ANA LOPEZ"),  # 2apellido AUSENTE, no solo vacío
    ({"nombre": "ROTULOS DEL LEVANTE SL", "1apellido": "", "2apellido": ""},
     "ROTULOS DEL LEVANTE SL"),
    ({"nombre": "  ANA   MARIA  ", "1apellido": " LOPEZ  GIL ", "2apellido": ""},
     "ANA MARIA LOPEZ GIL"),
])
def test_nombre_completo_de_compone_desde_los_campos_separados_del_crm(parte, esperado):
    """Persona física con los dos apellidos, con uno solo, con el segundo ausente (no
    solo vacío), razón social sin apellidos (convención de la casa: nombre completo en
    mayúsculas, apellidos vacíos), y espacios sobrantes normalizados."""
    assert exp.nombre_completo_de(parte) == esperado


def test_ficha_postal_compone_nombre_y_apellidos_no_solo_el_nombre_de_pila():
    """El defecto H-06: el burofax salía dirigido a "ANA" en vez de "ANA LOPEZ GIL"."""
    parte = {"nombre": "ANA", "1apellido": "LOPEZ", "2apellido": "GIL",
             "direccion": "C 1", "poblacion": "P", "provincia": "Barcelona", "cp": "08001"}
    f = exp.ficha_postal(parte)
    assert f["nombre"] == "ANA LOPEZ GIL"


def test_ficha_postal_con_un_solo_apellido():
    """El segundo apellido puede faltar; no debe dejar hueco ni espacio de más."""
    parte = {"nombre": "ANA", "1apellido": "LOPEZ", "2apellido": "",
             "direccion": "C 1", "poblacion": "P", "provincia": "Barcelona", "cp": "08001"}
    assert exp.ficha_postal(parte)["nombre"] == "ANA LOPEZ"


def test_ficha_postal_razon_social_sin_apellidos_pasa_nombre_tal_cual():
    """Convención de la casa: la razón social va completa y en mayúsculas en `nombre`,
    con los dos apellidos vacíos. Ahí no hay nada que concatenar."""
    parte = {"nombre": "ROTULOS DEL LEVANTE SL", "1apellido": "", "2apellido": "",
             "direccion": "Av Sur 9", "poblacion": "Sevilla", "provincia": "Sevilla",
             "cp": "41001"}
    assert exp.ficha_postal(parte)["nombre"] == "ROTULOS DEL LEVANTE SL"


def test_ficha_postal_a_atencion_hereda_el_nombre_completo_no_solo_el_de_pila():
    """El fallback de `a_atencion` (cuando el CRM no trae persona de contacto distinta)
    debe heredar el nombre YA compuesto, no solo el nombre de pila."""
    parte = {"nombre": "ANA", "1apellido": "LOPEZ", "2apellido": "GIL",
             "direccion": "C 1", "poblacion": "P", "provincia": "Barcelona", "cp": "08001"}
    assert exp.ficha_postal(parte)["a_atencion"] == "ANA LOPEZ GIL"
