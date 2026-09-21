"""Quién recibe qué: un burofax por domicilio, correo y SMS por requerido."""
from __future__ import annotations

from decimal import Decimal

import pytest

from core import expedicion_certificada as exp

# H-06 (revisión adversarial r2): el CRM real de `clientes_contrarios` separa nombre y
# apellidos en tres campos (docs/CRM_SUDESPACHO_ATLAS.md § clientes_contrarios) y NUNCA
# junta el nombre completo en "nombre". Estas fixtures antes ponían "ANA LOPEZ" entero en
# "nombre" -- una forma que el CRM no produce -- y ese doble tapaba el defecto: los tests
# pasaban aunque el código solo leyera "nombre". Separados, "ANA" + "LOPEZ" siguen
# componiendo "ANA LOPEZ": los mismos asertos de más abajo prueban ahora la composición
# real (nombre_completo_de), no una coincidencia de fixture.
ANA = {"nombre": "ANA", "1apellido": "LOPEZ", "2apellido": "", "direccion": "C Mayor 1",
       "poblacion": "Madrid", "provincia": "Madrid", "cp": "28001", "email": "ana@x.es",
       "movil": "665130883"}
LUIS = {"nombre": "LUIS", "1apellido": "PEREZ", "2apellido": "", "direccion": "C Mayor 1",
        "poblacion": "Madrid", "provincia": "Madrid", "cp": "28001", "email": "luis@x.es",
        "movil": "677000111"}
OTRO = {"nombre": "MAR", "1apellido": "GIL", "2apellido": "", "direccion": "Av Sur 9",
        "poblacion": "Sevilla", "provincia": "Sevilla", "cp": "41001", "email": "mar@x.es",
        "movil": "688222333"}


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


def test_H16_ningun_requerido_en_absoluto_detiene_el_plan():
    """Hallazgo H-16 (revisión adversarial r2): se rechazaba un requerido SIN
    canales, pero no la AUSENCIA de requeridos. `get_relaciones` puede devolver
    legítimamente ninguna relación -- un expediente sin contrarios vinculados en el
    CRM --, y `partes_de` lo convierte en `[]`. Antes, `destinatarios_de([])`
    devolvía `([], [])` sin avisar: coste cero y cero envíos se aceptaban como un
    plan ejecutable, y ejecutarlo salía con éxito y "ENVIADO: " vacío."""
    with pytest.raises(exp.ExpedicionError) as e:
        exp.destinatarios_de([])
    mensaje = str(e.value).lower()
    assert "requerido" in mensaje or "contrario" in mensaje
    assert "crm" in mensaje


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
    "plazo de aceptacion") (hallazgo 3).

    Este test comprueba la LÓGICA del helper (`_asegurar_sin_prohibidos`), pero lo
    llama DIRECTAMENTE -- no prueba que `texto_de` de verdad lo invoque. Ver
    `test_H14_texto_de_recorre_la_guarda_de_verdad_no_solo_el_helper` más abajo para
    esa conexión (hallazgo H-14, revisión adversarial r2)."""
    with pytest.raises(exp.ExpedicionError):
        exp._asegurar_sin_prohibidos("un texto que fija un plazo de pago")
    with pytest.raises(exp.ExpedicionError):
        exp._asegurar_sin_prohibidos("un texto con un calendario de cobro")


def test_H14_texto_de_recorre_la_guarda_de_verdad_no_solo_el_helper(monkeypatch):
    """Hallazgo H-14 (medio, acotado; revisión adversarial r2): el test de arriba
    acredita la lógica de `_asegurar_sin_prohibidos`, pero llamándolo DIRECTO --
    nunca recorre la conexión desde `texto_de`, que es la función pública que
    compone el texto real. Reproducido por el revisor: sustituir SOLO la línea
    `_asegurar_sin_prohibidos(...)` dentro de `texto_de` por `pass` deja la guarda
    desconectada de cualquier texto generado, y las 128 pruebas del ámbito -- test de
    arriba incluido -- seguían en verde.

    Aquí se inyecta un término prohibido en la PLANTILLA que `texto_de` usa de
    verdad (monkeypatch del módulo, no una plantilla nueva inventada a mano) y se
    llama a la función PÚBLICA: si se desconecta esa llamada, este test -- y solo
    este -- se pone en rojo."""
    monkeypatch.setattr(exp, "_CUERPO_TPL", "<p>Esto fija un plazo de pago para {w_code}</p>")
    with pytest.raises(exp.ExpedicionError):
        exp.texto_de("W-04AKM2")


def test_el_sms_lleva_correo_solo_si_la_parte_tiene_email():
    """Mandar un campo vacio a la API es peor que omitirlo (hallazgo 4)."""
    envios, _ = exp.destinatarios_de([ANA])
    sms_con_email = next(e for e in envios if e.canal == "sms")
    assert sms_con_email.destinatario["correo"] == "ana@x.es"

    sin_email = {**ANA, "email": ""}
    envios_sin, _ = exp.destinatarios_de([sin_email])
    sms_sin_email = next(e for e in envios_sin if e.canal == "sms")
    assert "correo" not in sms_sin_email.destinatario


# ---------------------------------------------------------------------------------
# H-06 (revisión adversarial r2). El código leía solo "nombre" -- el nombre de pila --
# en vez de componer nombre + apellidos como los separa `clientes_contrarios`
# (docs/CRM_SUDESPACHO_ATLAS.md). ANA y LUIS arriba solo llevan un apellido (para que
# los asertos de siempre seguían valiendo), así que aquí se fuerzan los DOS apellidos
# de cada uno para que el defecto -- "ANA Y LUIS" en vez del nombre completo de cada
# requerido -- no pueda esconderse detrás de un fixture con un solo apellido.
# ---------------------------------------------------------------------------------

def test_sobre_conjunto_compone_el_nombre_completo_de_cada_requerido():
    """El defecto: el sobre conjunto salía como "ANA Y LUIS" -- solo los nombres de
    pila -- en vez de con los apellidos de cada requerido."""
    ana_dos_apellidos = {**ANA, "1apellido": "LOPEZ", "2apellido": "GIL"}
    luis_dos_apellidos = {**LUIS, "1apellido": "PEREZ", "2apellido": "RUIZ"}
    envios, _ = exp.destinatarios_de([ana_dos_apellidos, luis_dos_apellidos])
    postal = next(e for e in envios if e.canal == "burofax")
    assert postal.destinatario["nombre"] == "ANA LOPEZ GIL Y LUIS PEREZ RUIZ"
    assert postal.destinatario["a_atencion"] == "ANA LOPEZ GIL"


def test_correo_y_sms_llevan_el_nombre_completo_no_solo_el_de_pila():
    """Misma causa que el sobre conjunto: el payload de correo/SMS y su etiqueta
    también leían solo "nombre". Con un segundo apellido debe llegar completo a los
    dos, no solo a la ficha postal."""
    ana_dos_apellidos = {**ANA, "1apellido": "LOPEZ", "2apellido": "GIL"}
    envios, _ = exp.destinatarios_de([ana_dos_apellidos])
    correo = next(e for e in envios if e.canal == "correo")
    sms = next(e for e in envios if e.canal == "sms")
    assert correo.destinatario["nombre"] == "ANA LOPEZ GIL"
    assert sms.destinatario["nombre"] == "ANA LOPEZ GIL"
    assert "ANA LOPEZ GIL" in correo.etiqueta
    assert "ANA LOPEZ GIL" in sms.etiqueta
