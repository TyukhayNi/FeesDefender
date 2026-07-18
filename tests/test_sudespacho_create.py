"""Tests para funciones de creación y mapeo de tags en sudespacho."""

import pytest
from unittest.mock import patch, MagicMock

from core.sudespacho_create import (
    tag_rojo_equipo,
    tag_azul_de_codigo,
    TAG_ROJO_BaRS11,
    TAG_AZUL_BARCELONA,
    TAG_AZUL_MADRID,
    merge_expediente_update,
    get_expediente,
    update_expediente,
    SudespachoCreateError,
)


def test_tag_rojo_equipo_conocido():
    assert tag_rojo_equipo("BaRS11") == TAG_ROJO_BaRS11


def test_tag_rojo_equipo_desconocido_es_none():
    assert tag_rojo_equipo("ZzZZ99") is None


@pytest.mark.parametrize("codigo,esperado", [
    ("BaRS11", TAG_AZUL_BARCELONA),
    ("BaCR1", TAG_AZUL_BARCELONA),
    ("MaRS2", TAG_AZUL_MADRID),
])
def test_tag_azul_de_codigo(codigo, esperado):
    assert tag_azul_de_codigo(codigo) == esperado


def test_tag_azul_de_codigo_prefijo_desconocido_es_none():
    assert tag_azul_de_codigo("ZzRS1") is None


def test_merge_expediente_update_preserva_numero_y_aplica_cambios():
    actual = {"Numero_Expediente": "49", "Notas": "viejo", "Referencia_Cliente": "X"}
    out = merge_expediente_update(actual, {"Notas": "nuevo"})
    assert out["Numero_Expediente"] == "49"     # preservado
    assert out["Notas"] == "nuevo"              # cambiado
    assert out["Referencia_Cliente"] == "X"     # intacto


def test_merge_expediente_update_no_deja_numero_a_cero():
    # Aunque los cambios intenten ponerlo a "0", se preserva el actual.
    actual = {"Numero_Expediente": "49", "Notas": "v"}
    out = merge_expediente_update(actual, {"Numero_Expediente": "0", "Notas": "n"})
    assert out["Numero_Expediente"] == "49"


def test_merge_expediente_update_lanza_si_actual_sin_numero_valido():
    with pytest.raises(ValueError):
        merge_expediente_update({"Numero_Expediente": "0"}, {"Notas": "n"})
    with pytest.raises(ValueError):
        merge_expediente_update({"Notas": "n"}, {"Notas": "n2"})


def test_merge_expediente_update_lanza_si_numero_es_none():
    # Regresión: cuando la API devuelve None (clave presente pero valor nulo),
    # str(None) → "None" que pasa la validación incorrectamente.
    # Debe lanzar ValueError igual que absent/empty/"0".
    with pytest.raises(ValueError):
        merge_expediente_update({"Numero_Expediente": None, "Notas": "v"}, {"Notas": "n"})


def test_get_expediente_hace_get_con_api_key():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": 606, "Numero_Expediente": "49"}
    with patch("core.sudespacho_create._get_api_key", return_value="K"), \
         patch("core.sudespacho_create.httpx.get", return_value=resp) as mget:
        rec = get_expediente("606")
    assert rec["Numero_Expediente"] == "49"
    url = mget.call_args.args[0]
    assert url.endswith("/api/element_register/extrajudiciales/606")
    assert mget.call_args.kwargs["headers"]["x-api-key"] == "K"


def test_update_expediente_round_trip_preserva_numero():
    getresp = MagicMock(status_code=200)
    getresp.json.return_value = {"Numero_Expediente": "49", "Notas": "viejo", "Referencia_Cliente": "X"}
    putresp = MagicMock(status_code=200)
    putresp.json.return_value = {"Numero_Expediente": "49", "Notas": "nuevo", "Referencia_Cliente": "X"}
    with patch("core.sudespacho_create._get_api_key", return_value="K"), \
         patch("core.sudespacho_create.httpx.get", return_value=getresp), \
         patch("core.sudespacho_create.httpx.put", return_value=putresp) as mput:
        out = update_expediente("606", {"Notas": "nuevo"})
    body = mput.call_args.kwargs["json"]
    assert body["Numero_Expediente"] == "49"    # el PUT reenvía el número
    assert body["Notas"] == "nuevo"
    assert out["Notas"] == "nuevo"


def test_get_expediente_error_lanza():
    resp = MagicMock(status_code=404, text="not found")
    resp.json.side_effect = ValueError
    with patch("core.sudespacho_create._get_api_key", return_value="K"), \
         patch("core.sudespacho_create.httpx.get", return_value=resp):
        with pytest.raises(SudespachoCreateError):
            get_expediente("999")
