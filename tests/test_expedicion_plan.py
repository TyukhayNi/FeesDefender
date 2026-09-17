"""Quién recibe qué: un burofax por domicilio, correo y SMS por requerido."""
from __future__ import annotations

from decimal import Decimal

import pytest

from core import expedicion_certificada as exp

ANA = {"nombre": "ANA LOPEZ", "direccion": "C Mayor 1", "poblacion": "Madrid",
       "provincia": "Madrid", "cp": "28001", "email": "ana@x.es", "movil": "665130883"}
LUIS = {"nombre": "LUIS PEREZ", "direccion": "C Mayor 1", "poblacion": "Madrid",
        "provincia": "Madrid", "cp": "28001", "email": "luis@x.es", "movil": "677000111"}
OTRO = {"nombre": "MAR GIL", "direccion": "Av Sur 9", "poblacion": "Sevilla",
        "provincia": "Sevilla", "cp": "41001", "email": "mar@x.es", "movil": "688222333"}


def _canales(envios):
    return sorted(e.canal for e in envios)


def test_un_requerido_da_tres_envios():
    envios, ausencias = exp.destinatarios_de([ANA])
    assert _canales(envios) == ["burofax", "correo", "sms"] and ausencias == []


def test_dos_requeridos_en_el_MISMO_domicilio_comparten_burofax():
    envios, _ = exp.destinatarios_de([ANA, LUIS])
    assert _canales(envios) == ["burofax", "correo", "correo", "sms", "sms"]
    postal = next(e for e in envios if e.canal == "burofax")
    assert postal.destinatario["nombre"] == "ANA LOPEZ Y LUIS PEREZ"


def test_dos_domicilios_distintos_son_dos_burofaxes():
    envios, _ = exp.destinatarios_de([ANA, OTRO])
    assert _canales(envios).count("burofax") == 2


def test_un_requerido_sin_movil_declara_la_ausencia_y_no_inventa_canal():
    sin_movil = {**ANA, "movil": "933010203"}
    envios, ausencias = exp.destinatarios_de([sin_movil])
    assert _canales(envios) == ["burofax", "correo"]
    assert any("sin canal SMS" in a for a in ausencias)


def test_un_requerido_SIN_NINGUN_canal_detiene_el_plan():
    mudo = {"nombre": "NADIE", "direccion": "", "poblacion": "", "provincia": "", "cp": "",
            "email": "", "movil": ""}
    with pytest.raises(exp.ExpedicionError) as e:
        exp.destinatarios_de([mudo])
    assert "NADIE" in str(e.value)


def test_el_coste_suma_la_tarifa_por_canal():
    envios, _ = exp.destinatarios_de([ANA, LUIS])
    assert exp.coste_de(envios) == (exp.TARIFA["burofax"]
                                    + 2 * exp.TARIFA["correo"] + 2 * exp.TARIFA["sms"])


def test_el_coste_es_decimal_y_el_burofax_pesa_veinte_veces_el_correo():
    assert isinstance(exp.TARIFA["burofax"], Decimal)
    assert exp.TARIFA["burofax"] > 20 * exp.TARIFA["correo"]


def test_el_asunto_y_el_cuerpo_NO_nombran_la_oferta_ni_sus_terminos():
    asunto, cuerpo = exp.texto_de("W-04AKM2")
    junto = f"{asunto} {cuerpo}".lower()
    for prohibido in ("oferta vinculante", "ovc", "€", "%"):
        assert prohibido not in junto
    assert "W-04AKM2" in asunto


def test_el_texto_nombra_el_expediente_que_es_lo_permitido():
    asunto, _ = exp.texto_de("W-02W9BO")
    assert "W-02W9BO" in asunto


def test_doble_espacio_interno_no_parte_el_mismo_domicilio_en_dos():
    """"C Mayor 1" y "C  Mayor 1" (doble espacio, defecto tipico de captura del CRM) son
    el mismo domicilio: deben compartir UN burofax, no generar uno de mas (hallazgo 1)."""
    con_doble_espacio = {**LUIS, "direccion": "C  Mayor 1"}
    envios, _ = exp.destinatarios_de([ANA, con_doble_espacio])
    assert _canales(envios).count("burofax") == 1


def test_sobre_conjunto_guarda_nombre_conjunto_y_atencion_individual():
    """En un sobre conjunto "nombre" lleva a los dos requeridos, pero "a_atencion" queda
    para la persona de contacto individual: no debe perderse tras la union (hallazgo 2)."""
    envios, _ = exp.destinatarios_de([ANA, LUIS])
    postal = next(e for e in envios if e.canal == "burofax")
    assert postal.destinatario["nombre"] == "ANA LOPEZ Y LUIS PEREZ"
    assert postal.destinatario["a_atencion"] == "ANA LOPEZ"


def test_un_w_code_que_contiene_ovc_por_azar_no_bloquea_el_texto():
    """"W-0OVC12" lleva "ovc" de casualidad: es un identificador de expediente, no
    prosa del motor, y no debe bloquear la comunicacion (hallazgo 3)."""
    asunto, cuerpo = exp.texto_de("W-0OVC12")
    assert "W-0OVC12" in asunto
    assert "W-0OVC12" in cuerpo


def test_la_guarda_de_prohibidos_sigue_saltando_sobre_el_texto_compuesto():
    """La guarda no se desactiva al aplicarse solo a la plantilla: sigue vetando
    "calendario" (ausente antes) y "plazo" a secas (antes acotado a la frase exacta
    "plazo de aceptacion") (hallazgo 3)."""
    with pytest.raises(exp.ExpedicionError):
        exp._asegurar_sin_prohibidos("un texto que fija un plazo de pago")
    with pytest.raises(exp.ExpedicionError):
        exp._asegurar_sin_prohibidos("un texto con un calendario de cobro")


def test_el_sms_lleva_correo_solo_si_la_parte_tiene_email():
    """Mandar un campo vacio a la API es peor que omitirlo (hallazgo 4)."""
    envios, _ = exp.destinatarios_de([ANA])
    sms_con_email = next(e for e in envios if e.canal == "sms")
    assert sms_con_email.destinatario["correo"] == "ana@x.es"

    sin_email = {**ANA, "email": ""}
    envios_sin, _ = exp.destinatarios_de([sin_email])
    sms_sin_email = next(e for e in envios_sin if e.canal == "sms")
    assert "correo" not in sms_sin_email.destinatario
