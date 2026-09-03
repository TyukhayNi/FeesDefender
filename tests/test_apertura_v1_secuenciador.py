"""El secuenciador de V1: estados, orden y punto de parada.

Spec: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md
§21.3 (V1 nunca es `completo`), §21.4 criterio 13, §24 D4 (las tres salidas).
Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md
"""
import pytest

from core import apertura_v1 as av1


def test_vocabulario_de_estados_cerrado():
    assert av1.EstadoV1.COMPLETO == "completo"
    assert av1.EstadoV1.PREPARADO_CON_PENDIENTES == "preparado_con_pendientes"
    assert av1.EstadoV1.BLOQUEADO == "bloqueado"


def test_un_fallo_bloquea_aunque_no_haya_pendientes():
    assert av1.estado_de([], hubo_fallo=True) == av1.EstadoV1.BLOQUEADO


def test_sin_pendientes_y_sin_fallo_seria_completo():
    """La regla pura admite `completo`. Lo que lo impide en V1 es el pendiente
    permanente del test siguiente, no un `return` cableado aqui."""
    assert av1.estado_de([], hubo_fallo=False) == av1.EstadoV1.COMPLETO


def test_con_pendientes_es_preparado_con_pendientes():
    p = av1.Pendiente(codigo="x", detalle="lo que sea")
    assert av1.estado_de([p], hubo_fallo=False) == av1.EstadoV1.PREPARADO_CON_PENDIENTES


def test_f3_el_pendiente_de_fuentes_v3_es_permanente_y_por_eso_v1_nunca_es_completo():
    """F3. Si esta lista se vaciara, V1 podria declararse `completo` mintiendo:
    Gmail y LeadHub son de V3 y V1 no las consulta (spec §21.3)."""
    assert av1.PENDIENTE_FUENTES_V3.codigo == "fuentes_v3_sin_consultar"
    assert av1.estado_de([av1.PENDIENTE_FUENTES_V3],
                         hubo_fallo=False) == av1.EstadoV1.PREPARADO_CON_PENDIENTES
