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


def _etapa(nombre, estado="hecha", pendientes=(), registro=None):
    def correr():
        if registro is not None:
            registro.append(nombre)
        return av1.EtapaResultado(nombre=nombre, estado=estado,
                                  detalle=f"{nombre}: {estado}",
                                  pendientes=tuple(pendientes))
    return av1.Etapa(nombre=nombre, correr=correr)


def test_las_etapas_corren_en_orden():
    visto = []
    r = av1.secuenciar([_etapa("a", registro=visto), _etapa("b", registro=visto),
                        _etapa("c", registro=visto)])
    assert visto == ["a", "b", "c"]
    assert [e.nombre for e in r.etapas] == ["a", "b", "c"]


def test_f1_un_fallo_detiene_la_secuencia():
    """F1. La etapa posterior NO corre: si corriera, escribiria sobre un caso cuyo
    paso anterior fracaso."""
    visto = []
    r = av1.secuenciar([_etapa("a", registro=visto),
                        _etapa("b", estado="fallo", registro=visto),
                        _etapa("c", registro=visto)])
    assert visto == ["a", "b"]
    assert [e.nombre for e in r.etapas] == ["a", "b"]


def test_f2_un_fallo_deja_el_resultado_bloqueado():
    r = av1.secuenciar([_etapa("a", estado="fallo")])
    assert r.estado == av1.EstadoV1.BLOQUEADO


def test_f3_una_corrida_impecable_sigue_siendo_preparado_con_pendientes():
    """F3 en el secuenciador: aunque las tres etapas salgan `hecha` y sin pendientes
    propios, el permanente esta en la lista."""
    r = av1.secuenciar([_etapa("a"), _etapa("b"), _etapa("c")])
    assert r.estado == av1.EstadoV1.PREPARADO_CON_PENDIENTES
    assert av1.PENDIENTE_FUENTES_V3 in r.pendientes


def test_los_pendientes_de_las_etapas_se_acumulan():
    p = av1.Pendiente(codigo="crm_sin_expediente", detalle="no hay expediente")
    r = av1.secuenciar([_etapa("a", pendientes=[p]), _etapa("b")])
    assert p in r.pendientes


def test_f4_hasta_para_DESPUES_de_la_etapa_nombrada():
    """F4. `--hasta drive` significa «traeme el Drive y para ahi»."""
    visto = []
    r = av1.secuenciar([_etapa("a", registro=visto), _etapa("b", registro=visto),
                        _etapa("c", registro=visto)], hasta="b")
    assert visto == ["a", "b"]
    assert r.parada == "b"


def test_f5_un_hasta_desconocido_es_error_y_no_corre_nada():
    """F5. Tragarse el nombre y correr entero es la guarda inerte: el operador pidio
    parar y la secuencia hizo lo contrario sin decirlo."""
    visto = []
    with pytest.raises(av1.EtapaDesconocida):
        av1.secuenciar([_etapa("a", registro=visto)], hasta="drve")
    assert visto == []


def test_sin_hasta_la_parada_es_none():
    r = av1.secuenciar([_etapa("a")])
    assert r.parada is None


def test_un_estado_de_etapa_fuera_del_vocabulario_es_error_de_programacion():
    with pytest.raises(ValueError, match="fuera del vocabulario"):
        av1.EtapaResultado(nombre="a", estado="casi", detalle="x")
