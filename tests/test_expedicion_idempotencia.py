"""El registro de intención: un timeout no puede perder un burofax pagado."""
from __future__ import annotations

import pytest

from core import expedicion_certificada as exp


def test_el_registro_NO_persiste_datos_personales(tmp_path):
    """`SEGURIDAD_DATOS` §7: una persona no se escribe a disco por su nombre."""
    ruta = tmp_path / "intencion.jsonl"
    exp.RegistroIntencion(ruta).anotar("burofax", "ANA LOPEZ · ana@correo.es · 34665130883")
    crudo = ruta.read_text(encoding="utf-8")
    for pii in ("ANA LOPEZ", "ana@correo.es", "34665130883"):
        assert pii not in crudo


def test_anotar_antes_del_post_y_cerrar_despues(tmp_path):
    reg = exp.RegistroIntencion(tmp_path / "intencion.jsonl")
    clave = reg.anotar("burofax", "ANA · C Mayor 1")
    assert reg.en_vuelo() and reg.hechos() == set()
    reg.cerrar(clave, "006ar9bel3n")
    assert reg.en_vuelo() == [] and reg.hechos() == {"006ar9bel3n"}


def test_un_en_vuelo_sin_id_sobrevive_al_reinicio(tmp_path):
    ruta = tmp_path / "intencion.jsonl"
    exp.RegistroIntencion(ruta).anotar("burofax", "ANA")
    assert len(exp.RegistroIntencion(ruta).en_vuelo()) == 1


def test_ya_expedido_solo_cuenta_el_id_personalizado_pedido():
    listado = [{"id": "a", "id_personalizado": "W-1 - REQ", "tipo": "b"},
               {"id": "b", "id_personalizado": "W-1 - OVC", "tipo": "b"},
               {"id": "c", "id_personalizado": "W-1 - REQ", "tipo": "ce"}]
    assert exp.ya_expedido(listado, "W-1 - REQ") == {"a", "c"}


def test_la_ovc_NO_se_confunde_con_el_requerimiento_del_mismo_expediente():
    listado = [{"id": "a", "id_personalizado": "W-1 - REQ"}]
    assert exp.ya_expedido(listado, "W-1 - OVC") == set()


def test_un_en_vuelo_pendiente_bloquea_la_ejecucion(tmp_path):
    reg = exp.RegistroIntencion(tmp_path / "i.jsonl")
    reg.anotar("burofax", "ANA")
    with pytest.raises(exp.ExpedicionError) as e:
        reg.exigir_sin_pendientes()
    assert "SIN VERIFICAR" in str(e.value)
