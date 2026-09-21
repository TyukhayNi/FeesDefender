"""Clasificación de los estados certificados de Codicert (spec §1.3 + medición M-2)."""
from __future__ import annotations

from datetime import datetime

import pytest

from core import expedicion_certificada as exp


def test_los_cuatro_que_acreditan_recepcion():
    """17, 19, 20 y 21 son recepción acreditada (spec §6.2)."""
    for codigo in (17, 19, 21):
        assert exp.clasificar(codigo) == exp.RECEPCION, codigo
    # el 20 es recepción Y acceso; se clasifica por lo más fuerte
    assert exp.clasificar(20) == exp.ACCESO


def test_el_27_no_es_recepcion():
    """«Entregado en el servidor» es el servidor, no el destinatario (spec §1.3)."""
    assert exp.clasificar(27) == exp.EN_CURSO


def test_los_seis_codigos_medidos_el_2026_09_21():
    """M-2: vivos en producción y ausentes del spec §1.3. Ninguno es terminal."""
    for codigo in (3, 8, 11, 12, 14, 31):
        assert exp.clasificar(codigo) == exp.EN_CURSO, codigo


def test_los_cierres_sin_entrega():
    for codigo in (28, 40, 42):
        assert exp.clasificar(codigo) == exp.SIN_ENTREGA


def test_un_codigo_que_nadie_ha_medido_NO_se_trata_como_benigno():
    """La regla de la casa: «no lo sé» no es «no hay».

    Un código desconocido no puede caer en `EN_CURSO` por defecto: eso lo haría
    indistinguible de un envío que progresa, y un cierre nuevo de la plataforma
    pasaría por «aún en camino» para siempre.
    """
    assert exp.clasificar(999) == exp.DESCONOCIDO
    assert exp.DESCONOCIDO not in (exp.EN_CURSO, exp.RECEPCION,
                                   exp.ACCESO, exp.SIN_ENTREGA)


def test_estado_de_parsea_la_forma_medida():
    """M-7: cada entrada de /estados es {codigo,titulo,fecha,detalle}."""
    e = exp.estado_de({"codigo": 20, "titulo": "Leído",
                       "fecha": "2026-09-12T23:03:43+02:00",
                       "detalle": "El destinatario x@y.es leyó la comunicación"})
    assert e.codigo == 20
    assert e.titulo == "Leído"
    assert e.fecha == datetime.fromisoformat("2026-09-12T23:03:43+02:00")
    assert e.familia == exp.ACCESO


def test_estado_de_exige_codigo_entero():
    """Un `codigo` que no es entero no se convierte en silencio."""
    with pytest.raises(exp.ExpedicionError, match="codigo"):
        exp.estado_de({"codigo": "veinte", "titulo": "?",
                       "fecha": "2026-09-12T23:03:43+02:00"})


def test_estado_de_exige_fecha_con_zona():
    """Sin offset no se puede comparar con nada: se para, no se asume UTC."""
    with pytest.raises(exp.ExpedicionError, match="zona|offset"):
        exp.estado_de({"codigo": 20, "titulo": "Leído",
                       "fecha": "2026-09-12T23:03:43"})
