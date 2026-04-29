"""Tests de core/sudespacho_relations.py — solo lógica pura, sin red."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import pytest

from core.sudespacho_relations import (
    EV_MMC_SPAIN_ID,
    NuevoColaborador,
    SudespachoRelationsError,
    _autocomplete,
    _extract_id,
    _link_element,
    _LINK_CLIENTE_PATH,
    _LINK_COLABORADOR_PATH,
    _SAVEADD_COLABORADOR_PATH,
    create_colaborador,
    ensure_colaborador_vinculado,
    find_colaborador_by_email,
    find_expediente_by_referencia,
    link_colaborador,
    link_ev_mmc,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_client(*, csrf="test_csrf_token_32chars_xxxxx999", phpsessid="test"):
    """Construye un SudespachoLegacyClient mockeado."""
    client = MagicMock()
    client.get_csrf_token.return_value = csrf
    client._check_session = MagicMock()
    client.__exit__ = MagicMock(return_value=False)
    return client


def _mock_get_response(json_data, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data
    return r


def _mock_post_response(status=200, text="<html>OK</html>"):
    r = MagicMock()
    r.status_code = status
    r.text = text
    return r


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

def test_ev_mmc_spain_id():
    """EV MMC SPAIN, S.L.U. debe tener ID fijo = '2'."""
    assert EV_MMC_SPAIN_ID == "2"


# ---------------------------------------------------------------------------
# _extract_id
# ---------------------------------------------------------------------------

def test_extract_id_campo_dato():
    assert _extract_id({"resultado": True, "dato": "42"}) == "42"


def test_extract_id_campo_id():
    assert _extract_id({"id": "99"}) == "99"


def test_extract_id_no_dict():
    assert _extract_id("string_rara") is None


def test_extract_id_dato_no_numerico():
    assert _extract_id({"dato": "abc"}) is None


def test_extract_id_fallback_miembro():
    assert _extract_id({"miembro": "123"}) == "123"


# ---------------------------------------------------------------------------
# _autocomplete
# ---------------------------------------------------------------------------

def test_autocomplete_devuelve_resultados():
    client = _mock_client()
    client._client.get.return_value = _mock_get_response(
        [{"id": 1, "label": "49 - 2026", "value": "600", "data": []}]
    )
    results = _autocomplete("extrajudiciales", "TEST-CAPTURA", client)
    assert len(results) == 1
    assert results[0]["value"] == "600"
    client._client.get.assert_called_once()
    url_arg = client._client.get.call_args[0][0]
    assert "extrajudiciales" in url_arg
    assert "TEST-CAPTURA" in url_arg


def test_autocomplete_sin_resultados():
    client = _mock_client()
    client._client.get.return_value = _mock_get_response([])
    results = _autocomplete("colaboradores", "noexiste@ejemplo.com", client)
    assert results == []


def test_autocomplete_error_http():
    client = _mock_client()
    r = _mock_get_response(None, status=500)
    r.json.side_effect = Exception("no json")
    client._client.get.return_value = r
    r.status_code = 500
    with pytest.raises(SudespachoRelationsError, match="HTTP 500"):
        _autocomplete("extrajudiciales", "algo", client)


# ---------------------------------------------------------------------------
# find_expediente_by_referencia
# ---------------------------------------------------------------------------

def test_find_expediente_encontrado(monkeypatch):
    client = _mock_client()
    client._client.get.return_value = _mock_get_response(
        [{"id": 1, "label": "49 - 2026", "value": "600", "data": []}]
    )
    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        result = find_expediente_by_referencia("TEST-CAPTURA-FEESDEFENDER")
    assert result == "600"


def test_find_expediente_no_encontrado(monkeypatch):
    client = _mock_client()
    client._client.get.return_value = _mock_get_response([])
    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        result = find_expediente_by_referencia("Caso Que No Existe")
    assert result is None


def test_find_expediente_con_client_externo():
    """Si se pasa client externo, no se llama a SudespachoLegacyClient()."""
    client = _mock_client()
    client._client.get.return_value = _mock_get_response(
        [{"id": 1, "label": "x", "value": "777", "data": []}]
    )
    result = find_expediente_by_referencia("ref", client=client)
    assert result == "777"
    client.__exit__.assert_not_called()  # cliente externo no se cierra


# ---------------------------------------------------------------------------
# find_colaborador_by_email
# ---------------------------------------------------------------------------

def test_find_colaborador_por_email(monkeypatch):
    client = _mock_client()
    client._client.get.return_value = _mock_get_response(
        [{"id": 1, "label": "Maria Garcia", "value": "301", "data": []}]
    )
    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        result = find_colaborador_by_email("maria.garcia@engelvoelkers.com")
    assert result == "301"


def test_find_colaborador_email_vacio():
    """Email vacío devuelve None sin llamar a la red."""
    result = find_colaborador_by_email("")
    assert result is None


def test_find_colaborador_no_encontrado(monkeypatch):
    client = _mock_client()
    client._client.get.return_value = _mock_get_response([])
    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        result = find_colaborador_by_email("nuevo@example.com")
    assert result is None


# ---------------------------------------------------------------------------
# _link_element
# ---------------------------------------------------------------------------

def test_link_element_ok():
    client = _mock_client()
    r = _mock_post_response(200)
    r.json.return_value = {"resultado": True, "info": "Seleccionando registros", "acumulaDatos": {"clientes_propios": ["2"]}}
    client._post_form.return_value = r
    _link_element(_LINK_CLIENTE_PATH, "600", "2", client)
    client._post_form.assert_called_once()
    path_arg = client._post_form.call_args[0][0]
    assert "600" in path_arg
    assert "saveselect" in path_arg  # endpoint correcto (no "select")
    body_arg = client._post_form.call_args[0][1]
    body_keys = [k for k, v in body_arg]
    assert "seleccionado[]" in body_keys
    assert "numeroresultados_listado" in body_keys
    items = [(k, v) for k, v in body_arg if k == "seleccionado[]"]
    assert items[0][1] == "2"


def test_link_element_fallo_http():
    client = _mock_client()
    client._post_form.return_value = _mock_post_response(500)
    with pytest.raises(SudespachoRelationsError, match="HTTP 500"):
        _link_element(_LINK_CLIENTE_PATH, "600", "2", client)


def test_link_element_resultado_false():
    """Si el JSON devuelve resultado=false, debe lanzar error."""
    client = _mock_client()
    r = _mock_post_response(200)
    r.json.return_value = {"resultado": False}
    client._post_form.return_value = r
    with pytest.raises(SudespachoRelationsError, match="resultado=false"):
        _link_element(_LINK_CLIENTE_PATH, "600", "2", client)


# ---------------------------------------------------------------------------
# link_ev_mmc
# ---------------------------------------------------------------------------

def test_link_ev_mmc(monkeypatch):
    client = _mock_client()
    r = _mock_post_response(200)
    r.json.return_value = {"resultado": True, "acumulaDatos": {"clientes_propios": [EV_MMC_SPAIN_ID]}}
    client._post_form.return_value = r
    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        link_ev_mmc("600")
    path_arg = client._post_form.call_args[0][0]
    assert "clientes_propios" in path_arg
    assert "saveselect" in path_arg
    assert "600" in path_arg
    items = [(k, v) for k, v in client._post_form.call_args[0][1] if k == "seleccionado[]"]
    assert items[0][1] == EV_MMC_SPAIN_ID


# ---------------------------------------------------------------------------
# link_colaborador
# ---------------------------------------------------------------------------

def test_link_colaborador(monkeypatch):
    client = _mock_client()
    r = _mock_post_response(200)
    r.json.return_value = {"resultado": True, "acumulaDatos": {"colaboradores": ["301"]}}
    client._post_form.return_value = r
    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        link_colaborador("600", "301")
    path_arg = client._post_form.call_args[0][0]
    assert "colaboradores" in path_arg
    assert "saveselect" in path_arg
    assert "600" in path_arg
    items = [(k, v) for k, v in client._post_form.call_args[0][1] if k == "seleccionado[]"]
    assert items[0][1] == "301"


# ---------------------------------------------------------------------------
# create_colaborador
# ---------------------------------------------------------------------------

def test_create_colaborador_ok(monkeypatch):
    client = _mock_client()
    client.post_form.return_value = {"resultado": True, "dato": "402", "wfcontroller": "colaboradores"}
    datos = NuevoColaborador(nombre="Ana López", email="ana.lopez@engelvoelkers.com", movil="+34 600 111 222")
    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        colab_id = create_colaborador(datos)
    assert colab_id == "402"
    client.post_form.assert_called_once()
    path_arg = client.post_form.call_args[0][0]
    assert path_arg == _SAVEADD_COLABORADOR_PATH
    # Verificar que los campos clave están en el body
    body = client.post_form.call_args[0][1]
    body_dict = {}
    for k, v in body:
        body_dict[k] = v
    assert body_dict.get("campo_1086__colaboradores") == "Ana López"
    assert body_dict.get("campo_1080__colaboradores") == "ana.lopez@engelvoelkers.com"
    assert body_dict.get("campo_1083__colaboradores") == "+34 600 111 222"
    assert body_dict.get("ajax") == "true"


def test_create_colaborador_sin_id_en_respuesta(monkeypatch):
    client = _mock_client()
    client.post_form.return_value = {"resultado": False}
    datos = NuevoColaborador(nombre="Test", email="test@test.com")
    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        with pytest.raises(SudespachoRelationsError, match="no se pudo extraer"):
            create_colaborador(datos)


# ---------------------------------------------------------------------------
# ensure_colaborador_vinculado
# ---------------------------------------------------------------------------

def test_ensure_colaborador_existente(monkeypatch):
    """Si el colaborador ya existe, no se crea — solo se vincula."""
    client = _mock_client()
    # Autocomplete encuentra al colaborador
    client._client.get.return_value = _mock_get_response(
        [{"id": 1, "label": "Existente", "value": "301", "data": []}]
    )
    # Link OK — saveselect devuelve JSON con resultado:true
    r = _mock_post_response(200)
    r.json.return_value = {"resultado": True, "acumulaDatos": {"colaboradores": ["301"]}}
    client._post_form.return_value = r

    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        colab_id, created = ensure_colaborador_vinculado(
            "600",
            NuevoColaborador(nombre="Existente", email="existente@engelvoelkers.com"),
        )

    assert colab_id == "301"
    assert created is False
    client.post_form.assert_not_called()  # no se llamó a create


def test_ensure_colaborador_nuevo(monkeypatch):
    """Si el colaborador no existe, se crea y luego se vincula."""
    client = _mock_client()
    # Primera llamada GET: autocomplete no encuentra nada
    client._client.get.return_value = _mock_get_response([])
    # post_form: saveadd devuelve nuevo ID
    client.post_form.return_value = {"resultado": True, "dato": "999"}
    # _post_form: saveselect link OK — devuelve JSON
    r = _mock_post_response(200)
    r.json.return_value = {"resultado": True, "acumulaDatos": {"colaboradores": ["999"]}}
    client._post_form.return_value = r

    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        colab_id, created = ensure_colaborador_vinculado(
            "600",
            NuevoColaborador(nombre="Nuevo Consultor", email="nuevo@engelvoelkers.com"),
        )

    assert colab_id == "999"
    assert created is True
    client.post_form.assert_called_once()   # saveadd llamado
    client._post_form.assert_called_once()  # link llamado


def test_ensure_colaborador_email_vacio(monkeypatch):
    """Colaborador sin email: no se puede buscar, se crea directamente."""
    client = _mock_client()
    # Sin email no hay búsqueda, va directamente a create
    client.post_form.return_value = {"resultado": True, "dato": "888"}
    r = _mock_post_response(200)
    r.json.return_value = {"resultado": True, "acumulaDatos": {"colaboradores": ["888"]}}
    client._post_form.return_value = r

    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        colab_id, created = ensure_colaborador_vinculado(
            "600",
            NuevoColaborador(nombre="Sin Email", email=""),
        )

    assert colab_id == "888"
    assert created is True
    # No se llamó a autocomplete (email vacío → find_colaborador_by_email devuelve None sin GET)
    client._client.get.assert_not_called()
