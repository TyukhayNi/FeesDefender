"""La ficha del destinatario postal: traducción de provincia y validación antes de gastar."""
from __future__ import annotations

import re

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


# ---------------------------------------------------------------------------------
# H-10 (medio, acotado; revisión adversarial r2). Dos defectos en la misma ficha:
# (1) `ficha_postal` copiaba `movil_normalizado` (once dígitos con el "34" delante)
# tal cual en su campo `telefono`, pero el contrato distingue los dos destinatarios:
# el postal exige `^[67]\d{8}$` -- nueve dígitos, sin prefijo -- mientras que el
# electrónico no tiene patrón y SÍ admite el prefijo (spec §1.1, líneas 154-161).
# (2) el país de entrada no se validaba: se escribía siempre "España", así que un
# domicilio extranjero se convertía en un envío dirigido a España sin ningún aviso.
# El comportamiento REAL del servidor ante un teléfono con prefijo en el campo
# postal no se ha verificado por red: lo que se corrige es el incumplimiento del
# contrato aportado, no una medición nueva contra Codicert.
# ---------------------------------------------------------------------------------

@pytest.mark.parametrize("bruto,esperado", [
    ("600000001", "600000001"), ("34600000001", "600000001"),
    ("+34 600 000 001", "600000001"), ("0034600000001", "600000001"),
])
def test_H10_movil_postal_son_nueve_digitos_sin_prefijo(bruto, esperado):
    """El defecto: `movil_normalizado("600000001")` da "34600000001" -- once
    dígitos --, que incumple `^[67]\\d{8}$`, el patrón documentado para
    `DestinatarioPostal.telefono`. `movil_postal` es la forma que sí lo cumple."""
    assert exp.movil_postal(bruto) == esperado
    assert len(exp.movil_postal(bruto)) == 9


@pytest.mark.parametrize("bruto", ["933010203", "", None, "600", "no es un movil"])
def test_H10_lo_que_no_es_un_movil_espanol_tambien_devuelve_None_en_postal(bruto):
    assert exp.movil_postal(bruto) is None


def test_H10_ficha_postal_usa_el_movil_de_nueve_digitos_no_el_internacional():
    """El defecto reproducido: con móvil "600000001", `ficha_postal` mandaba
    "34600000001" en `telefono` -- el campo postal, que exige nueve dígitos."""
    parte = {"nombre": "X", "direccion": "C 1", "poblacion": "P", "provincia": "Barcelona",
             "cp": "08001", "movil": "600000001"}
    f = exp.ficha_postal(parte)
    assert f["telefono"] == "600000001"
    assert re.match(r"^[67]\d{8}$", f["telefono"])


def test_H10_ficha_postal_sin_movil_no_lleva_campo_telefono():
    parte = {"nombre": "X", "direccion": "C 1", "poblacion": "P", "provincia": "Barcelona",
             "cp": "08001"}
    assert "telefono" not in exp.ficha_postal(parte)


def test_H10_ficha_postal_con_pais_espana_explicito_no_cambia_nada():
    """Un `pais` explícito que SÍ es España (como lo escriba el CRM) no debe
    rechazarse: solo se rechaza lo que NO es España."""
    parte = {"nombre": "X", "direccion": "C 1", "poblacion": "P", "provincia": "Barcelona",
             "cp": "08001", "pais": "España"}
    assert exp.ficha_postal(parte)["pais"] == "España"


def test_H10_ficha_postal_rechaza_un_domicilio_extranjero():
    """El defecto reproducido: una ficha con país Francia, población y provincia
    extranjeras y CP francés se convertía en un envío dirigido a España, sin error.
    Codicert (burofax) solo admite `pais="España"` (spec §1.1): se rechaza en el
    plan, nunca se fabrica el envío erróneo."""
    parte = {"nombre": "X", "direccion": "12 Rue de Rivoli", "poblacion": "Paris",
             "provincia": "Paris", "cp": "75001", "pais": "Francia"}
    with pytest.raises(exp.ExpedicionError) as e:
        exp.ficha_postal(parte)
    mensaje = str(e.value).lower()
    assert "francia" in mensaje
    assert "españa" in mensaje


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
