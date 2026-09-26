"""Los hechos que un envío acredita, derivados de su histórico (spec §6.1, §6.2)."""
from __future__ import annotations

from datetime import datetime

import pytest

from core import expedicion_certificada as exp


def _historico(*pares):
    return [exp.estado_de({"codigo": c, "titulo": "", "fecha": f, "detalle": None})
            for c, f in pares]


def _envio(**kw):
    base = dict(id_envio="006x", tipo="c", asunto="W-04AKM2 - OVC",
                destinatario="x@y.es", id_personalizado="W-04AKM2 - OVC",
                fecha_envio=datetime.fromisoformat("2026-09-10T18:26:08+02:00"),
                historico=_historico((5, "2026-09-10T18:26:10+02:00")))
    base.update(kw)
    return exp.EnvioObservado(**base)


def test_la_recepcion_es_la_MAS_TEMPRANA_no_la_ultima():
    """M-1, el hallazgo que justifica leer el histórico.

    El burofax 006catfpdv6 quedó en 19 el 17-09, pero fue entregado (17) el 14-09.
    El art. 17.2 cuenta desde la recepción: tomar la del último estado desplaza el
    mes del art. 17.4 tres días.
    """
    e = _envio(tipo="b", historico=_historico(
        (12, "2026-09-14T07:47:23+02:00"),
        (17, "2026-09-14T11:31:08+02:00"),
        (19, "2026-09-17T13:00:52+02:00")))
    assert e.recibido_en == datetime.fromisoformat("2026-09-14T11:31:08+02:00")


def test_el_acceso_es_su_propia_fecha_y_no_arrastra_la_recepcion():
    e = _envio(historico=_historico(
        (21, "2026-09-11T19:00:23+02:00"),
        (20, "2026-09-12T23:03:43+02:00")))
    assert e.recibido_en == datetime.fromisoformat("2026-09-11T19:00:23+02:00")
    assert e.accedido_en == datetime.fromisoformat("2026-09-12T23:03:43+02:00")


def test_un_envio_en_curso_no_acredita_nada():
    e = _envio(historico=_historico((5, "2026-09-10T18:26:10+02:00"),
                                    (27, "2026-09-10T18:26:11+02:00")))
    assert e.recibido_en is None and e.accedido_en is None and e.cerrado_en is None


def test_el_rechazo_se_registra_con_fecha_y_no_como_error():
    """§6.3: el 28 tiene valor afirmativo (art. 7.4, art. 395.1 LEC)."""
    e = _envio(historico=_historico((28, "2026-09-15T10:00:00+02:00")))
    assert e.cerrado_en == datetime.fromisoformat("2026-09-15T10:00:00+02:00")
    assert e.recibido_en is None


def test_cosechable_solo_en_el_maximo_de_su_canal():
    """La EEC culmina en 20; el burofax, en 19. Antes, el hecho puede mejorar."""
    eec_21 = _envio(historico=_historico((21, "2026-09-11T19:00:23+02:00")))
    eec_20 = _envio(historico=_historico((20, "2026-09-12T23:03:43+02:00")))
    buro_17 = _envio(tipo="b", historico=_historico((17, "2026-09-14T11:31:08+02:00")))
    buro_19 = _envio(tipo="b", historico=_historico((19, "2026-09-17T13:00:52+02:00")))
    assert not eec_21.cosechable and eec_20.cosechable
    assert not buro_17.cosechable and buro_19.cosechable


def test_un_cierre_sin_entrega_tambien_es_cosechable():
    """Un 42 no mejora: el certificado ya es definitivo."""
    assert _envio(tipo="b",
                  historico=_historico((42, "2026-09-15T18:11:00+02:00"))).cosechable


def test_un_codigo_desconocido_NO_hace_cosechable_y_se_declara():
    e = _envio(historico=_historico((999, "2026-09-15T10:00:00+02:00")))
    assert not e.cosechable
    assert e.desconocidos == (999,)


def test_el_canal_sale_del_tipo_medido():
    """M-7: 'b' → Burofax, 'c' → Entrega Electrónica Certificada."""
    assert exp.CANAL_DE_TIPO["b"] == "burofax"
    assert exp.CANAL_DE_TIPO["c"] == "electronico"
    assert _envio(tipo="b").canal == "burofax"


def test_la_expedicion_agrega_sin_inventar_un_reloj_comun():
    """§6.1: el nivel expedición es comodidad de informe, SIN efecto jurídico."""
    a = _envio(id_envio="006a", historico=_historico((20, "2026-09-12T23:03:43+02:00")))
    b = _envio(id_envio="006b", historico=_historico((21, "2026-09-11T19:00:23+02:00")))
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(a, b))
    assert e.completa is False           # b aún puede mejorar
    assert {x.id_envio for x in e.pendientes} == {"006b"}
    assert {x.id_envio for x in e.cosechables} == {"006a"}


def test_una_expedicion_VACIA_no_esta_completa():
    """Un censo vacío no es una expedición terminada (spec §5.2)."""
    assert exp.Expedicion(id_personalizado="W-1 - OVC",
                          entorno="produccion").completa is False


def test_el_22_sin_ningun_aviso_entregado_cierra_sin_entrega():
    """M-17, `006bij47xan`: el SMS no llegó nunca y el recordatorio falló.

    Decisión de Nikolai (2026-09-26): se cierra sin entrega y se cosecha como prueba del
    intento. Sin la regla no se cosecharía nunca: la plataforma no caduca lo que no entregó.
    """
    e = _envio(historico=_historico((3, "2026-07-01T12:05:33+02:00"),
                                    (14, "2026-07-02T13:00:45+02:00"),
                                    (22, "2026-07-04T13:00:50+02:00")))
    assert e.cerrado_en == datetime.fromisoformat("2026-07-04T13:00:50+02:00")
    assert e.cosechable
    assert e.recibido_en is None and e.accedido_en is None
    assert e.desconocidos == ()


@pytest.mark.parametrize("indicio", [17, 19, 20, 21, 27])
def test_el_22_NO_cierra_si_algun_aviso_llego(indicio):
    """Si el primer aviso llegó —al buzón, al contenido o al servidor—, el requerido aún
    puede leer: el 22 del recordatorio no cierra nada y se espera al 40 (D-1)."""
    e = _envio(historico=_historico((5, "2026-09-01T10:00:00+02:00"),
                                    (indicio, "2026-09-01T10:00:05+02:00"),
                                    (14, "2026-09-02T11:00:00+02:00"),
                                    (22, "2026-09-02T11:00:05+02:00")))
    assert e.cerrado_en is None
    assert e.cosechable is (indicio == 20)   # el 20 culmina por sí mismo


def test_un_indicio_que_llega_DESPUES_del_22_tambien_lo_anula():
    """El acuse puede llegar tarde (M-17: en el sandbox el 17 llegó después del 20). La
    regla mira el histórico entero, no solo lo anterior al 22."""
    e = _envio(historico=_historico((3, "2026-07-01T12:05:33+02:00"),
                                    (14, "2026-07-02T13:00:45+02:00"),
                                    (22, "2026-07-04T13:00:50+02:00"),
                                    (17, "2026-07-05T09:00:00+02:00")))
    assert e.cerrado_en is None and not e.cosechable


def test_el_40_cierra_aunque_hubiera_un_22_antes():
    e = _envio(historico=_historico((17, "2026-06-17T16:30:04+02:00"),
                                    (14, "2026-06-18T17:00:33+02:00"),
                                    (22, "2026-06-18T17:00:43+02:00"),
                                    (40, "2026-07-17T16:29:58+02:00")))
    assert e.cerrado_en == datetime.fromisoformat("2026-07-17T16:29:58+02:00")
    assert e.cosechable
