"""Tests para funciones de creación y mapeo de tags en sudespacho."""

import pytest
from unittest.mock import patch, MagicMock

from core.sudespacho_create import (
    tag_rojo_equipo,
    tag_azul_de_codigo,
    TAG_ROJO_BaRS11,
    TAG_ROJO_BaPD1,
    TAG_AZUL_BARCELONA,
    TAG_AZUL_MADRID,
    _parse_values,
    get_expediente,
    update_expediente,
    SudespachoCreateError,
)


def test_tag_rojo_equipo_conocido():
    assert tag_rojo_equipo("BaRS11") == TAG_ROJO_BaRS11


def test_tag_rojo_equipo_desconocido_es_none():
    assert tag_rojo_equipo("ZzZZ99") is None


def test_tag_rojo_equipo_bapd1_resuelve():
    """El código canónico "BaPD1" (que B5 auto-deriva de la unidad "Barcelona -
    PD1") debe resolver su tag rojo extrajudicial. Regresión del alias FD
    corregido BaDP1->BaPD1 (2026-07-18): antes tag_rojo_equipo("BaPD1") era None
    y un alta PD de Barcelona perdía el tag rojo en silencio."""
    assert tag_rojo_equipo("BaPD1") == TAG_ROJO_BaPD1
    assert tag_rojo_equipo("BaPD1") is not None


@pytest.mark.parametrize("codigo,esperado", [
    ("BaRS11", TAG_AZUL_BARCELONA),
    ("BaCR1", TAG_AZUL_BARCELONA),
    ("MaRS2", TAG_AZUL_MADRID),
])
def test_tag_azul_de_codigo(codigo, esperado):
    assert tag_azul_de_codigo(codigo) == esperado


def test_tag_azul_de_codigo_prefijo_desconocido_es_none():
    assert tag_azul_de_codigo("ZzRS1") is None


def _values_body(campos: dict) -> dict:
    """Construye un body {values:[...]} en la forma real del GET/PUT-detalle."""
    return {
        "id": 606,
        "isPrimary": False,
        "groupsAccessRegister": [],
        "usersAccessRegister": [],
        "values": [
            {"property": {"name": nombre}, "value": valor}
            for nombre, valor in campos.items()
        ],
    }


def test_parse_values_aplana_lista_a_dict():
    body = {
        "values": [
            {"property": {"name": "Notas"}, "value": "x"},
            {"property": {"name": "Numero_Expediente"}, "value": "49"},
        ]
    }
    assert _parse_values(body) == {"Notas": "x", "Numero_Expediente": "49"}


def test_parse_values_admite_property_como_string_suelto():
    body = {"values": [{"property": "Notas", "value": "x"}]}
    assert _parse_values(body) == {"Notas": "x"}


def test_parse_values_sin_values_da_dict_vacio():
    assert _parse_values({}) == {}


def test_get_expediente_hace_get_con_properties_y_api_key():
    resp = MagicMock(status_code=200)
    resp.json.return_value = _values_body({"Numero_Expediente": "49", "Notas": "viejo"})
    with patch("core.sudespacho_create._get_api_key", return_value="K"), \
         patch("core.sudespacho_create.httpx.get", return_value=resp) as mget:
        rec = get_expediente("606")
    assert rec == {"Numero_Expediente": "49", "Notas": "viejo"}
    url = mget.call_args.args[0]
    assert url.startswith(
        "https://api-crm-commons-pro.sudespacho.biz/api/element_register/extrajudiciales/606?properties="
    )
    assert "Numero_Expediente" in url
    assert mget.call_args.kwargs["headers"]["x-api-key"] == "K"


def test_get_expediente_error_lanza():
    resp = MagicMock(status_code=500, text="Undefined array key properties")
    resp.json.side_effect = ValueError
    with patch("core.sudespacho_create._get_api_key", return_value="K"), \
         patch("core.sudespacho_create.httpx.get", return_value=resp):
        with pytest.raises(SudespachoCreateError):
            get_expediente("999")


def test_update_expediente_envia_solo_cambios_flat_sin_get_previo():
    putresp = MagicMock(status_code=200)
    putresp.json.return_value = _values_body({"Numero_Expediente": "49", "Notas": "nuevo"})
    with patch("core.sudespacho_create._get_api_key", return_value="K"), \
         patch("core.sudespacho_create.httpx.get") as mget, \
         patch("core.sudespacho_create.httpx.put", return_value=putresp) as mput:
        out = update_expediente("606", {"Notas": "nuevo"})
    mget.assert_not_called()  # PUT parcial: no hace falta GET→merge previo
    assert mput.call_args.kwargs["json"] == {"Notas": "nuevo"}
    url = mput.call_args.args[0]
    assert url == "https://api-crm-commons-pro.sudespacho.biz/api/element_register/extrajudiciales/606"
    assert out == {"Numero_Expediente": "49", "Notas": "nuevo"}


def test_update_expediente_cambios_vacio_lanza_value_error():
    with pytest.raises(ValueError):
        update_expediente("606", {})


def test_update_expediente_error_lanza():
    resp = MagicMock(status_code=404, text="not found")
    resp.json.side_effect = ValueError
    with patch("core.sudespacho_create._get_api_key", return_value="K"), \
         patch("core.sudespacho_create.httpx.put", return_value=resp):
        with pytest.raises(SudespachoCreateError):
            update_expediente("606", {"Notas": "x"})
