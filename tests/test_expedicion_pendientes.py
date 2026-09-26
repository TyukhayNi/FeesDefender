"""Por qué un envío no se cosecha: cuatro motivos y no uno (M-21)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core import expedicion_certificada as exp

#: La hora del barrido real del 2026-09-26.
LEIDA = datetime(2026, 9, 26, 6, 26, 56, tzinfo=timezone.utc)


def _envio(id_envio="006x", tipo="c", *pares):
    historico = tuple(exp.estado_de({"codigo": c, "titulo": "", "fecha": f, "detalle": None})
                      for c, f in pares)
    return exp.EnvioObservado(
        id_envio=id_envio, tipo=tipo, asunto="W-04AKM2 - OVC", destinatario="x@y.es",
        id_personalizado="W-04AKM2 - OVC",
        fecha_envio=datetime.fromisoformat("2026-06-01T10:00:00+02:00"),
        historico=historico)


def _hace(dias, segundos=0):
    return (LEIDA - timedelta(days=dias, seconds=segundos)).isoformat()


def test_lo_cosechable_no_tiene_motivo():
    assert _envio("006a", "c", (20, _hace(3))).pendiente_por(LEIDA) is None


def test_en_curso_y_reciente_puede_mejorar():
    e = _envio("006a", "c", (17, _hace(12)), (14, _hace(11)), (21, _hace(11)))
    assert e.pendiente_por(LEIDA) == exp.PUEDE_MEJORAR


def test_el_burofax_que_se_quedo_en_17_esta_estancado():
    """M-19, `006bgjupt2a`: entregado (17) y 88 días sin el 19. En los otros siete el 19
    llegó entre 1,3 y 29,1 días después."""
    e = _envio("006bgjupt2a", "b", (3, _hace(91)), (8, _hace(91)), (11, _hace(90)),
               (12, _hace(89)), (17, _hace(88)))
    assert e.pendiente_por(LEIDA) == exp.ESTANCADO
    assert e.dias_quieto(LEIDA) == 88


def test_la_frontera_de_los_40_dias():
    """Exactamente 40 días quieto todavía puede mejorar; un segundo más, no (D-3)."""
    justo = _envio("006a", "b", (17, _hace(40)))
    pasado = _envio("006b", "b", (17, _hace(40, segundos=1)))
    assert justo.pendiente_por(LEIDA) == exp.PUEDE_MEJORAR
    assert pasado.pendiente_por(LEIDA) == exp.ESTANCADO


def test_sin_historico_lo_quieto_se_cuenta_desde_el_envio():
    e = _envio("006a", "c")
    assert e.ultimo_evento() == e.fecha_envio
    assert e.pendiente_por(LEIDA) == exp.ESTANCADO


def test_lo_quieto_se_cuenta_desde_el_ULTIMO_evento_no_desde_el_primero():
    e = _envio("006a", "b", (3, _hace(80)), (31, _hace(60)), (12, _hace(10)))
    assert e.dias_quieto(LEIDA) == 10
    assert e.pendiente_por(LEIDA) == exp.PUEDE_MEJORAR


def test_el_codigo_sin_clasificar_se_dice_antes_que_lo_quieto():
    """Un 999 de hace cien días no es «estancado»: es algo que nadie ha clasificado, y eso
    se arregla en el código, no esperando."""
    e = _envio("006a", "c", (999, _hace(100)))
    assert e.pendiente_por(LEIDA) == exp.CODIGO_SIN_CLASIFICAR


def test_el_canal_sin_clasificar_se_dice_primero():
    """M-18, `006bkxe0q63`: 17 → 20 hace 80 días, en un canal que F2 no conoce."""
    e = _envio("006bkxe0q63", "s", (17, _hace(80)), (20, _hace(80)))
    assert e.pendiente_por(LEIDA) == exp.CANAL_SIN_CLASIFICAR


def test_pendientes_por_agrupa_en_el_orden_de_lo_que_hay_que_hacer():
    envios = (
        _envio("006m", "c", (17, _hace(5))),                    # puede mejorar
        _envio("006e", "b", (17, _hace(88))),                   # estancado
        _envio("006k", "c", (20, _hace(2))),                    # cosechable: fuera
        _envio("006d", "c", (999, _hace(1))),                   # código sin clasificar
        _envio("006s", "s", (17, _hace(80)), (20, _hace(80))),  # canal sin clasificar
    )
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=envios, leida_en=LEIDA)
    grupos = e.pendientes_por()
    assert list(grupos) == list(exp.MOTIVOS_PENDIENTE)
    assert {m: [x.id_envio for x in v] for m, v in grupos.items()} == {
        exp.CANAL_SIN_CLASIFICAR: ["006s"], exp.CODIGO_SIN_CLASIFICAR: ["006d"],
        exp.ESTANCADO: ["006e"], exp.PUEDE_MEJORAR: ["006m"]}
    # un estancado NO culminó: la expedición no está completa
    assert e.completa is False and len(e.pendientes) == 4


def test_pendientes_por_solo_trae_los_motivos_que_tienen_envios():
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(_envio("006m", "c", (17, _hace(5))),), leida_en=LEIDA)
    assert list(e.pendientes_por()) == [exp.PUEDE_MEJORAR]


def test_la_expedicion_exige_saber_cuando_se_leyo():
    """D-4: sin la hora de la lectura no se sabe qué está quieto; no hay valor por defecto."""
    with pytest.raises(TypeError):
        exp.Expedicion(id_personalizado="W-1 - OVC", entorno="produccion")
    with pytest.raises(exp.ExpedicionError, match="zona"):
        exp.Expedicion(id_personalizado="W-1 - OVC", entorno="produccion",
                       leida_en=datetime(2026, 9, 26))


def test_cada_motivo_tiene_su_nombre_y_su_explicacion():
    assert set(exp.QUE_SIGNIFICA) == set(exp.ETIQUETA) == set(exp.MOTIVOS_PENDIENTE)
    assert len(exp.MOTIVOS_PENDIENTE) == len(set(exp.MOTIVOS_PENDIENTE)) == 4
