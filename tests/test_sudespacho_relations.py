"""Tests de core/sudespacho_relations.py — solo lógica pura, sin red."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import pytest

import httpx

from core.sudespacho_relations import (
    EV_MMC_SPAIN_ID,
    NuevoColaborador,
    SudespachoRelationsError,
    _autocomplete,
    _create_colaborador_legacy,
    _extract_id,
    _link_element,
    _link_rest,
    _link_rest_or_legacy,
    _list_colaboradores_rest,
    _rest_post_colaborador,
    _rest_search_expedientes,
    _LINK_CLIENTE_PATH,
    _LINK_COLABORADOR_PATH,
    _REFERENCIA_PROP_BY_ELEMENT,
    _REST_CREATE_COLABORADOR,
    _SAVEADD_COLABORADOR_PATH,
    create_colaborador,
    ensure_colaborador_vinculado,
    find_colaborador_by_email,
    find_expediente_by_referencia,
    find_expediente_judicial_by_referencia,
    list_expedientes_judiciales_candidatos,
    wcode_match,
    link_colaborador,
    link_ev_mmc,
    load_all_colaboradores,
    normalize_referencia,
    search_colaboradores_for_ui,
    verify_expediente_referencia,
    _extract_w_code,
    _rest_search_por_texto,
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


def _html_colaboradores(rows: list[dict]) -> str:
    """HTML con filas de colaboradores para mockear _search_colaboradores_html.

    Genera la estructura que espera _ROW_RE + _TD_RE:
      <tr id="fila_colaboradores_{id}"> con 6 <td>, name en [3], email en [5].
    """
    parts = ["<table>"]
    for row in rows:
        parts.append(f'<tr id="fila_colaboradores_{row["id"]}">')
        parts.append("<td>0</td><td>1</td><td>2</td>")
        parts.append(f'<td>{row["name"]}</td>')
        parts.append("<td>4</td>")
        parts.append(f'<td>{row["email"]}</td>')
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


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
# find_expediente_by_referencia / find_expediente_judicial_by_referencia
#
# Desde 2026-06-12 ambas usan REST (element_registries + filtro like sobre el
# W-code), NO el autocomplete legacy (que devuelve body vacío contra el CRM
# real — ver docs/DEAD_ENDS.md "Frontal heredado"). Los tests mockean
# httpx.get (patrón de tests/test_verify_referencia.py).
# ---------------------------------------------------------------------------

@pytest.fixture
def _api_key(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test_key_abc")


def _rest_items_prop(prop: str, *rows: tuple[str, str | None]) -> dict:
    """Respuesta REST element_registries con (id, <prop>) por fila."""
    items = []
    for eid, ref in rows:
        vals = []
        if ref is not None:
            vals.append({"property": {"name": prop}, "value": ref})
        items.append({"id": str(eid), "values": vals})
    return {"totalItems": len(items), "items": items}


def test_find_expediente_extrajudicial_match_exacto(_api_key):
    """REST devuelve el candidato con referencia exacta → su id."""
    ref = "MaRS2 - Gran Via 40 - (W-0001) - Dev. Reserva"
    payload = _rest_items_prop(
        _REFERENCIA_PROP_BY_ELEMENT["extrajudiciales"], ("600", ref),
    )
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get_response(payload)):
        result = find_expediente_by_referencia(ref)
    assert result == "600"


def test_find_expediente_extrajudicial_usa_property_camelcase(_api_key):
    """El filtro extrajudicial usa la property CamelCase Referencia_Cliente."""
    ref = "MaRS2 - Gran Via 40 - (W-02NV4W) - Vuelta"
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        return _mock_get_response(
            _rest_items_prop("Referencia_Cliente", ("500", ref))
        )

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        result = find_expediente_by_referencia(ref)
    assert result == "500"
    assert "element_registries/extrajudiciales" in captured["url"]
    assert "expedientes_judiciales" not in captured["url"]
    assert ("properties[0]", "Referencia_Cliente") in captured["params"]
    assert ("filterGroup[filterGroups][0][filters][0][property]",
            "Referencia_Cliente") in captured["params"]
    # filtra por el W-code con operador like
    assert ("filterGroup[filterGroups][0][filters][0][value]", "W-02NV4W") in captured["params"]
    assert ("filterGroup[filterGroups][0][filters][0][operator]", "like") in captured["params"]


def test_find_expediente_judicial_usa_property_lowercase_y_slug(_api_key):
    """El filtro judicial usa referencia_cliente (lowercase) y el slug judicial."""
    ref = "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        return _mock_get_response(
            _rest_items_prop("referencia_cliente", ("649", ref))
        )

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        result = find_expediente_judicial_by_referencia(ref)
    assert result == "649"
    assert "element_registries/expedientes_judiciales" in captured["url"]
    assert ("properties[0]", "referencia_cliente") in captured["params"]
    assert ("filterGroup[filterGroups][0][filters][0][value]", "W-030LFT") in captured["params"]


def test_find_expediente_no_encontrado_devuelve_none(_api_key):
    """REST no devuelve candidatos → None."""
    payload = _rest_items_prop(_REFERENCIA_PROP_BY_ELEMENT["extrajudiciales"])
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get_response(payload)):
        result = find_expediente_by_referencia("Caso (W-99999) Que No Existe")
    assert result is None


def test_find_expediente_candidato_mismo_wcode_pero_no_exacto_es_none(_api_key):
    """Candidatos que comparten W-code pero con referencia distinta NO son
    el mismo expediente → None (evita falso positivo de duplicado)."""
    payload = _rest_items_prop(
        _REFERENCIA_PROP_BY_ELEMENT["expedientes_judiciales"],
        ("487", "BaRS3 - Torrent 41 - (W-02MA0R) - Vuelta - COMPRADOR"),
        ("488", "BaRS3 - Torrent 41 - (W-02MA0R) - Bad debt"),
    )
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get_response(payload)):
        result = find_expediente_judicial_by_referencia(
            "BaRS3 - Torrent 41 - (W-02MA0R) - Otra cosa distinta"
        )
    assert result is None


def test_find_expediente_match_tolera_doble_espacio_acento_y_case(_api_key):
    """El match es normalizado: doble espacio / acento / mayúsculas casan
    igual (valor real de la guarda de dedup)."""
    payload = _rest_items_prop(
        _REFERENCIA_PROP_BY_ELEMENT["expedientes_judiciales"],
        ("444", "bars6 - Gran Vía 8 - (W-02NV4W)  - vuelta"),
    )
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get_response(payload)):
        result = find_expediente_judicial_by_referencia(
            "BaRS6 - Gran Via 8 - (W-02NV4W) - Vuelta"
        )
    assert result == "444"


def test_find_expediente_sin_wcode_usa_texto_completo(_api_key):
    """Sin W-code, filtra por el texto completo (fallback)."""
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["params"] = params
        return _mock_get_response(
            _rest_items_prop("Referencia_Cliente", ("200", "EV-2026-001"))
        )

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        result = find_expediente_by_referencia("EV-2026-001")
    assert result == "200"
    assert ("filterGroup[filterGroups][0][filters][0][value]", "EV-2026-001") in captured["params"]


def test_find_expediente_sin_api_key_devuelve_none(monkeypatch):
    """Sin SUDESPACHO_API_KEY → None, sin lanzar."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "")
    result = find_expediente_by_referencia("Caso (W-02MA0R)")
    assert result is None


def test_find_expediente_red_caida_devuelve_none(_api_key):
    """Red caída → None, sin lanzar (degrada como list_expedientes_*)."""
    with patch("core.sudespacho_relations.httpx.get",
               side_effect=httpx.ConnectError("timeout")):
        result = find_expediente_judicial_by_referencia("Caso (W-02MA0R)")
    assert result is None


def test_find_expediente_ignora_client_legacy(_api_key):
    """El parámetro `client` se conserva por compatibilidad pero se ignora:
    la búsqueda es REST y NO toca el cliente legacy."""
    legacy = _mock_client()
    ref = "MaRS2 - X - (W-0001) - Vuelta"
    payload = _rest_items_prop("Referencia_Cliente", ("777", ref))
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get_response(payload)):
        result = find_expediente_by_referencia(ref, client=legacy)
    assert result == "777"
    legacy._client.get.assert_not_called()
    legacy.__exit__.assert_not_called()


# ---------------------------------------------------------------------------
# _rest_search_expedientes — helper REST genérico
# ---------------------------------------------------------------------------

def test_rest_search_expedientes_element_desconocido_devuelve_vacio(_api_key):
    assert _rest_search_expedientes("elemento_inexistente", "Caso (W-0001)") == []


def test_rest_search_expedientes_parsea_label_de_la_property(_api_key):
    """El label devuelto es el valor de la property de referencia del CRM."""
    payload = _rest_items_prop(
        "referencia_cliente",
        ("487", "BaRS3 - Torrent 41 - (W-02MA0R) - Vuelta - COMPRADOR"),
        ("488", "BaRS3 - Torrent 41 - (W-02MA0R) - Bad debt"),
    )
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get_response(payload)):
        out = _rest_search_expedientes(
            "expedientes_judiciales",
            "BaRS3 - Torrent de les Flors 41 - (W-02MA0R) - Bad debt",
        )
    assert out == [
        {"id": "487", "label": "BaRS3 - Torrent 41 - (W-02MA0R) - Vuelta - COMPRADOR"},
        {"id": "488", "label": "BaRS3 - Torrent 41 - (W-02MA0R) - Bad debt"},
    ]


# ---------------------------------------------------------------------------
# wcode_match
# ---------------------------------------------------------------------------

def test_wcode_match_mismo_wcode_distinto_sufijo():
    """Misma finca (W-02MA0R), sufijo divergente Drive vs CRM → match."""
    assert wcode_match(
        "BaRS3 - Torrent de les Flors 41 - (W-02MA0R) - Bad debt",
        "BaRS3 - Torrent de les Flors 41 - (W-02MA0R) - Vuelta - COMPRADOR",
    ) is True


def test_wcode_match_distinto_wcode():
    """Caso del 649: W-030LFT (Roser) ≠ W-02MA0R (Torrent) → NO match."""
    assert wcode_match(
        "BaRS3 - Torrent de les Flors 41 - (W-02MA0R) - Bad debt",
        "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU",
    ) is False


def test_wcode_match_case_insensitive():
    assert wcode_match("ref (w-02ma0r)", "otra (W-02MA0R)") is True


def test_wcode_match_falta_wcode():
    assert wcode_match("sin codigo", "tampoco tiene") is False
    assert wcode_match("(W-02MA0R)", None) is False
    assert wcode_match(None, None) is False


# ---------------------------------------------------------------------------
# list_expedientes_judiciales_candidatos
# ---------------------------------------------------------------------------

def _rest_items(*rows: tuple[str, str | None]) -> dict:
    """Respuesta REST element_registries con (id, referencia_cliente) por fila."""
    items = []
    for eid, ref in rows:
        vals = []
        if ref is not None:
            vals.append({"property": {"name": "referencia_cliente"}, "value": ref})
        items.append({"id": str(eid), "values": vals})
    return {"totalItems": len(items), "items": items}


def test_candidatos_judiciales_por_wcode(monkeypatch):
    """Busca por W-code vía REST (like) y devuelve TODOS los candidatos."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test_key_abc")
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        return _mock_get_response(_rest_items(
            ("487", "BaRS3 - Torrent 41 - (W-02MA0R) - Vuelta - COMPRADOR"),
            ("488", "BaRS3 - Torrent 41 - (W-02MA0R) - Bad debt"),
        ))

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        out = list_expedientes_judiciales_candidatos(
            "BaRS3 - Torrent de les Flors 41 - (W-02MA0R) - Bad debt"
        )
    assert out == [
        {"id": "487", "label": "BaRS3 - Torrent 41 - (W-02MA0R) - Vuelta - COMPRADOR"},
        {"id": "488", "label": "BaRS3 - Torrent 41 - (W-02MA0R) - Bad debt"},
    ]
    # filtró por el W-code (no por la referencia completa) sobre el endpoint judicial
    assert "expedientes_judiciales" in captured["url"]
    assert ("filterGroup[filterGroups][0][filters][0][value]", "W-02MA0R") in captured["params"]
    assert ("filterGroup[filterGroups][0][filters][0][operator]", "like") in captured["params"]


def test_candidatos_judiciales_sin_api_key_devuelve_vacio(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "")
    out = list_expedientes_judiciales_candidatos("Caso (W-99999)")
    assert out == []


def test_candidatos_judiciales_red_caida_devuelve_vacio(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test_key_abc")
    with patch("core.sudespacho_relations.httpx.get",
               side_effect=httpx.ConnectError("timeout")):
        out = list_expedientes_judiciales_candidatos("Caso (W-02MA0R)")
    assert out == []


def test_candidatos_judiciales_sin_wcode_usa_texto_completo(monkeypatch):
    """Sin W-code, busca por el texto completo (fallback)."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test_key_abc")
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["params"] = params
        return _mock_get_response(_rest_items())

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        out = list_expedientes_judiciales_candidatos("Caso sin codigo W")
    assert out == []
    assert ("filterGroup[filterGroups][0][filters][0][value]", "Caso sin codigo W") in captured["params"]


# ---------------------------------------------------------------------------
# find_colaborador_by_email
# ---------------------------------------------------------------------------

def test_find_colaborador_por_email(monkeypatch):
    """Búsqueda por email exacto vía REST API — devuelve el ID del colaborador."""
    colabs = [
        {"id": "301", "label": "Maria Garcia  ·  maria.garcia@engelvoelkers.com", "email": "maria.garcia@engelvoelkers.com"},
    ]
    with patch("core.sudespacho_relations._list_colaboradores_rest", return_value=colabs):
        result = find_colaborador_by_email("maria.garcia@engelvoelkers.com")
    assert result == "301"


def test_find_colaborador_email_vacio():
    """Email vacío devuelve None sin llamar a la red."""
    result = find_colaborador_by_email("")
    assert result is None


def test_find_colaborador_no_encontrado(monkeypatch):
    """Si la lista REST no contiene el email, devuelve None."""
    colabs = [
        {"id": "301", "label": "Otro Colab  ·  otro@engelvoelkers.com", "email": "otro@engelvoelkers.com"},
    ]
    with patch("core.sudespacho_relations._list_colaboradores_rest", return_value=colabs):
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
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)  # fuerza path legacy
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
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)  # fuerza path legacy
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
    """REST falla (JWT ausente) → fallback legacy OK."""
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)  # fuerza fallback
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
    """REST falla (JWT ausente) → fallback legacy devuelve respuesta sin ID → error."""
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)  # fuerza fallback
    client = _mock_client()
    client.post_form.return_value = {"resultado": False}
    datos = NuevoColaborador(nombre="Test", email="test@test.com")
    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        with pytest.raises(SudespachoRelationsError, match="no se pudo extraer"):
            create_colaborador(datos)


# ---------------------------------------------------------------------------
# _rest_post_colaborador (confirmado 2026-05-06, HAR judicial_648.har)
# ---------------------------------------------------------------------------

def test_rest_post_colaborador_201(monkeypatch):
    """REST devuelve 201 → ID extraído correctamente."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    datos = NuevoColaborador(
        nombre="Ana López",
        email="ana.lopez@engelvoelkers.com",
        movil="+34 600 111 222",
    )
    resp = _make_httpx_response({"id": 780, "message": "Created!"}, status=201)
    with patch("core.sudespacho_relations.httpx.post", return_value=resp) as mock_post:
        colab_id = _rest_post_colaborador(datos)
    assert colab_id == "780"
    # Verificar URL y body enviados
    call_args = mock_post.call_args
    assert _REST_CREATE_COLABORADOR in call_args[0][0]
    payload = call_args[1]["json"]
    assert payload["nombre"] == "Ana López"
    assert payload["email"] == "ana.lopez@engelvoelkers.com"
    assert payload["movil"] == "+34 600 111 222"
    # nif vacío → no se incluye en payload
    assert "nif_cif" not in payload


def test_rest_post_colaborador_payload_campos_opcionales_omitidos(monkeypatch):
    """Campos opcionales vacíos no se incluyen en el payload REST."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    datos = NuevoColaborador(nombre="Solo Nombre", email="", movil="", nif="")
    resp = _make_httpx_response({"id": 781, "message": "Created!"}, status=201)
    with patch("core.sudespacho_relations.httpx.post", return_value=resp) as mock_post:
        _rest_post_colaborador(datos)
    payload = mock_post.call_args[1]["json"]
    assert payload == {"nombre": "Solo Nombre"}


def test_rest_post_colaborador_payload_nif_y_telefono(monkeypatch):
    """nif → nif_cif, telefono → telefono1 en el payload REST."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    datos = NuevoColaborador(
        nombre="Pedro Martín",
        email="pedro@test.com",
        nif="12345678A",
        telefono="912345678",
    )
    resp = _make_httpx_response({"id": 782, "message": "Created!"}, status=201)
    with patch("core.sudespacho_relations.httpx.post", return_value=resp) as mock_post:
        _rest_post_colaborador(datos)
    payload = mock_post.call_args[1]["json"]
    assert payload.get("nif_cif") == "12345678A"    # campo REST correcto
    assert payload.get("telefono1") == "912345678"  # campo REST correcto
    assert "nif" not in payload
    assert "telefono" not in payload


def test_rest_post_colaborador_apikey_ausente(monkeypatch):
    """Sin SUDESPACHO_API_KEY → ValueError (capturado por create_colaborador como fallback)."""
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)
    datos = NuevoColaborador(nombre="Test", email="test@test.com")
    with pytest.raises(ValueError, match="SUDESPACHO_API_KEY"):
        _rest_post_colaborador(datos)


# ---------------------------------------------------------------------------
# create_colaborador — estrategia REST-first + fallback
# ---------------------------------------------------------------------------

def test_create_colaborador_rest_first_ok(monkeypatch):
    """JWT presente → REST usado, legacy no llamado."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    datos = NuevoColaborador(nombre="REST Colaborador", email="rest@test.com")
    with patch(
        "core.sudespacho_relations._rest_post_colaborador",
        return_value="900",
    ) as mock_rest:
        colab_id = create_colaborador(datos)
    assert colab_id == "900"
    mock_rest.assert_called_once_with(datos)


def test_create_colaborador_rest_falla_fallback_legacy(monkeypatch):
    """REST falla → fallback legacy devuelve ID correctamente."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    client = _mock_client()
    client.post_form.return_value = {"resultado": True, "dato": "901"}
    datos = NuevoColaborador(nombre="Fallback Colaborador", email="fallback@test.com")
    with patch(
        "core.sudespacho_relations._rest_post_colaborador",
        side_effect=SudespachoRelationsError("REST caído"),
    ):
        with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
            colab_id = create_colaborador(datos)
    assert colab_id == "901"
    client.post_form.assert_called_once()


# ---------------------------------------------------------------------------
# ensure_colaborador_vinculado
# ---------------------------------------------------------------------------

def test_ensure_colaborador_existente(monkeypatch):
    """Si el colaborador ya existe, no se crea — solo se vincula."""
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)  # fuerza path legacy
    client = _mock_client()
    colabs_rest = [
        {"id": "301", "label": "Existente  ·  existente@engelvoelkers.com", "email": "existente@engelvoelkers.com"},
    ]
    # Única llamada a _post_form: saveselect (link)
    r_link = _mock_post_response(200)
    r_link.json.return_value = {"resultado": True, "acumulaDatos": {"colaboradores": ["301"]}}
    client._post_form.return_value = r_link

    with patch("core.sudespacho_relations._list_colaboradores_rest", return_value=colabs_rest):
        with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
            colab_id, created = ensure_colaborador_vinculado(
                "600",
                NuevoColaborador(nombre="Existente", email="existente@engelvoelkers.com"),
            )

    assert colab_id == "301"
    assert created is False
    client.post_form.assert_not_called()  # no se llamó a create (post_form público)
    assert client._post_form.call_count == 1  # solo link (búsqueda es REST)


def test_ensure_colaborador_nuevo(monkeypatch):
    """Si el colaborador no existe, se crea y luego se vincula."""
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)  # fuerza path legacy
    client = _mock_client()
    # REST no devuelve el colaborador (lista vacía → None)
    colabs_rest: list[dict] = []
    # _post_form: saveselect (link) — devuelve JSON
    r_link = _mock_post_response(200)
    r_link.json.return_value = {"resultado": True, "acumulaDatos": {"colaboradores": ["999"]}}
    client._post_form.return_value = r_link
    # post_form público: saveadd devuelve nuevo ID
    client.post_form.return_value = {"resultado": True, "dato": "999"}

    with patch("core.sudespacho_relations._list_colaboradores_rest", return_value=colabs_rest):
        with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
            colab_id, created = ensure_colaborador_vinculado(
                "600",
                NuevoColaborador(nombre="Nuevo Consultor", email="nuevo@engelvoelkers.com"),
            )

    assert colab_id == "999"
    assert created is True
    client.post_form.assert_called_once()    # saveadd llamado una vez
    assert client._post_form.call_count == 1  # solo link (búsqueda es REST)


def test_ensure_colaborador_email_vacio(monkeypatch):
    """Colaborador sin email: no se puede buscar, se crea directamente (ruta legacy)."""
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)  # fuerza fallback legacy
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


# ---------------------------------------------------------------------------
# _list_colaboradores_rest
# ---------------------------------------------------------------------------

def _make_httpx_response(data: dict, status: int = 200) -> MagicMock:
    """Mock de httpx.Response para _list_colaboradores_rest."""
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data
    r.text = str(data)
    return r


def _hydra_page(members: list[dict], total: int) -> dict:
    """Respuesta hydra:Collection con los miembros dados."""
    return {
        "hydra:member": members,
        "hydra:totalItems": total,
    }


def _member(id_: str, nombre: str, email: str = "") -> dict:
    values = [{"property": {"name": "nombre"}, "value": nombre}]
    if email:
        values.append({"property": {"name": "email"}, "value": email})
    return {"id": id_, "values": values}


def test_list_colaboradores_rest_una_pagina(monkeypatch):
    """Lista de colaboradores en una sola página devuelve todos los registros."""
    page_data = _hydra_page(
        [
            _member("301", "Maria Garcia", "maria@ev.com"),
            _member("302", "Juan López"),
        ],
        total=2,
    )
    with patch("httpx.get", return_value=_make_httpx_response(page_data)):
        result = _list_colaboradores_rest()
    assert len(result) == 2
    assert result[0]["id"] == "301"
    assert "maria@ev.com" in result[0]["label"]
    assert result[0]["email"] == "maria@ev.com"
    assert result[1]["id"] == "302"
    assert result[1]["email"] == ""


def test_list_colaboradores_rest_sin_nombre_ignorado(monkeypatch):
    """Miembros sin campo 'nombre' se ignoran."""
    page_data = _hydra_page(
        [
            {"id": "303", "values": [{"property": {"name": "email"}, "value": "solo@email.com"}]},
            _member("304", "Con Nombre"),
        ],
        total=2,
    )
    with patch("httpx.get", return_value=_make_httpx_response(page_data)):
        result = _list_colaboradores_rest()
    assert len(result) == 1
    assert result[0]["id"] == "304"


def test_list_colaboradores_rest_http_error(monkeypatch):
    """Error de red lanza SudespachoRelationsError."""
    with patch("httpx.get", side_effect=httpx.ConnectError("timeout")):
        with pytest.raises(SudespachoRelationsError, match="REST GET colaboradores"):
            _list_colaboradores_rest()


def test_list_colaboradores_rest_status_error(monkeypatch):
    """HTTP 401 lanza SudespachoRelationsError."""
    r = _make_httpx_response({}, status=401)
    with patch("httpx.get", return_value=r):
        with pytest.raises(SudespachoRelationsError, match="HTTP 401"):
            _list_colaboradores_rest()


def test_list_colaboradores_rest_multi_pagina(monkeypatch):
    """Con total > PAGE_SIZE, las páginas restantes se descargan en paralelo
    y el resultado final contiene los registros de todas las páginas en orden."""
    page1 = _hydra_page(
        [_member("1", "Ana Uno", "ana@ev.com")],
        total=1001,   # fuerza 3 páginas con PAGE_SIZE=500
    )
    page2 = _hydra_page(
        [_member("2", "Bob Dos", "bob@ev.com")],
        total=1001,
    )
    page3 = _hydra_page(
        [_member("3", "Carla Tres", "carla@ev.com")],
        total=1001,
    )

    responses = {1: page1, 2: page2, 3: page3}

    def _fake_get(url, *, params, headers, timeout):
        page_num = int(params["page"])
        return _make_httpx_response(responses[page_num])

    with patch("httpx.get", side_effect=_fake_get):
        result = _list_colaboradores_rest()

    assert len(result) == 3
    ids = {r["id"] for r in result}
    assert ids == {"1", "2", "3"}


# ---------------------------------------------------------------------------
# load_all_colaboradores / search_colaboradores_for_ui
# ---------------------------------------------------------------------------

def test_load_all_colaboradores_delega_rest(monkeypatch):
    """load_all_colaboradores() devuelve la lista completa de REST."""
    colabs = [{"id": "301", "label": "X  ·  x@ev.com", "email": "x@ev.com"}]
    with patch("core.sudespacho_relations._list_colaboradores_rest", return_value=colabs):
        result = load_all_colaboradores()
    assert result == colabs


def test_search_colaboradores_for_ui_filtra_por_termino(monkeypatch):
    """search_colaboradores_for_ui filtra en cliente por término en label."""
    colabs = [
        {"id": "301", "label": "Maria Garcia  ·  maria@ev.com", "email": "maria@ev.com"},
        {"id": "302", "label": "Juan López  ·  juan@ev.com", "email": "juan@ev.com"},
    ]
    with patch("core.sudespacho_relations._list_colaboradores_rest", return_value=colabs):
        result = search_colaboradores_for_ui("maria")
    assert len(result) == 1
    assert result[0]["id"] == "301"


def test_search_colaboradores_for_ui_termino_corto(monkeypatch):
    """Términos de menos de 2 caracteres devuelven lista vacía sin llamar a REST."""
    with patch("core.sudespacho_relations._list_colaboradores_rest") as mock_rest:
        result = search_colaboradores_for_ui("a")
    assert result == []
    mock_rest.assert_not_called()


# ---------------------------------------------------------------------------
# _link_rest (REST sin PHPSESSID, confirmado 2026-05-06)
# ---------------------------------------------------------------------------

def _mock_httpx_post_201():
    """Mock de httpx.post que devuelve 201 "Created!"."""
    r = MagicMock()
    r.status_code = 201
    r.text = '"Created!"'
    return r


def test_link_rest_ok(monkeypatch):
    """_link_rest() envía POST correcto con x-api-key y acepta 201."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    mock_resp = _mock_httpx_post_201()

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        _link_rest("extrajudiciales", "600", ["right.clientes_propios.2"])

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    # URL correcta
    assert "relation_element/extrajudiciales/600" in call_kwargs[0][0]
    # Body correcto
    assert call_kwargs[1]["json"] == ["right.clientes_propios.2"]
    # Auth x-api-key (clave estática)
    headers = call_kwargs[1]["headers"]
    assert headers["x-api-key"] == "test-api-key"
    assert headers["Content-Type"] == "application/json"


def test_link_rest_sin_apikey_lanza_value_error(monkeypatch):
    """Sin SUDESPACHO_API_KEY, _link_rest() lanza ValueError."""
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)
    with pytest.raises(ValueError, match="SUDESPACHO_API_KEY"):
        _link_rest("extrajudiciales", "600", ["right.clientes_propios.2"])


def test_link_rest_http_no_201_lanza_error(monkeypatch):
    """HTTP != 201 de POST relation_element lanza SudespachoRelationsError."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    r = MagicMock()
    r.status_code = 401
    r.text = '{"code":401,"message":"Expired JWT Token"}'

    with patch("httpx.post", return_value=r):
        with pytest.raises(SudespachoRelationsError, match="HTTP 401"):
            _link_rest("extrajudiciales", "600", ["right.clientes_propios.2"])


def test_link_rest_error_de_red_lanza_error(monkeypatch):
    """Error de conexión httpx lanza SudespachoRelationsError."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    with patch("httpx.post", side_effect=httpx.ConnectError("timeout")):
        with pytest.raises(SudespachoRelationsError, match="REST POST relation_element"):
            _link_rest("extrajudiciales", "600", ["right.clientes_propios.2"])


def test_link_rest_multiples_relaciones(monkeypatch):
    """_link_rest() pasa correctamente un array con múltiples relaciones."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    mock_resp = _mock_httpx_post_201()
    relations = ["right.clientes_propios.2", "right.colaboradores.50"]

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        _link_rest("extrajudiciales", "591", relations)

    assert mock_post.call_args[1]["json"] == relations



# ---------------------------------------------------------------------------
# _link_rest_or_legacy
# ---------------------------------------------------------------------------

def test_link_rest_or_legacy_rest_wins(monkeypatch):
    """Si REST devuelve 201, no se llama a _link_element (legacy)."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    client = _mock_client()

    with patch("core.sudespacho_relations._link_rest") as mock_rest:
        mock_rest.return_value = None  # REST ok
        _link_rest_or_legacy(
            "extrajudiciales", "600",
            ["right.clientes_propios.2"],
            _LINK_CLIENTE_PATH, "2", client,
        )

    mock_rest.assert_called_once_with("extrajudiciales", "600", ["right.clientes_propios.2"])
    client._post_form.assert_not_called()


def test_link_rest_or_legacy_fallback_si_rest_falla(monkeypatch):
    """Si REST lanza SudespachoRelationsError, se usa legacy saveselect."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    client = _mock_client()
    r = _mock_post_response(200)
    r.json.return_value = {"resultado": True, "acumulaDatos": {}}
    client._post_form.return_value = r

    with patch("core.sudespacho_relations._link_rest",
               side_effect=SudespachoRelationsError("REST falló")):
        _link_rest_or_legacy(
            "extrajudiciales", "600",
            ["right.clientes_propios.2"],
            _LINK_CLIENTE_PATH, "2", client,
        )

    client._post_form.assert_called_once()


def test_link_rest_or_legacy_fallback_si_no_apikey(monkeypatch):
    """Si SUDESPACHO_API_KEY ausente (ValueError), también usa fallback legacy."""
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)
    client = _mock_client()
    r = _mock_post_response(200)
    r.json.return_value = {"resultado": True}
    client._post_form.return_value = r

    _link_rest_or_legacy(
        "extrajudiciales", "600",
        ["right.clientes_propios.2"],
        _LINK_CLIENTE_PATH, "2", client,
    )

    client._post_form.assert_called_once()


# ---------------------------------------------------------------------------
# link_ev_mmc — REST-first (2026-05-06)
# ---------------------------------------------------------------------------

def test_link_ev_mmc_rest_first(monkeypatch):
    """link_ev_mmc() usa REST cuando JWT está disponible."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    client = _mock_client()

    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        with patch("core.sudespacho_relations._link_rest") as mock_rest:
            mock_rest.return_value = None
            link_ev_mmc("600")

    mock_rest.assert_called_once_with(
        "extrajudiciales", "600", [f"right.clientes_propios.{EV_MMC_SPAIN_ID}"]
    )
    client._post_form.assert_not_called()


def test_link_colaborador_rest_first(monkeypatch):
    """link_colaborador() usa REST cuando JWT está disponible."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")
    client = _mock_client()

    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        with patch("core.sudespacho_relations._link_rest") as mock_rest:
            mock_rest.return_value = None
            link_colaborador("600", "301")

    mock_rest.assert_called_once_with(
        "extrajudiciales", "600", ["right.colaboradores.301"]
    )
    client._post_form.assert_not_called()


def test_search_colaboradores_for_ui_sin_resultados(monkeypatch):
    """Término que no coincide devuelve lista vacía."""
    colabs = [
        {"id": "301", "label": "Maria Garcia  ·  maria@ev.com", "email": "maria@ev.com"},
    ]
    with patch("core.sudespacho_relations._list_colaboradores_rest", return_value=colabs):
        result = search_colaboradores_for_ui("xyz_no_existe")
    assert result == []


# ---------------------------------------------------------------------------
# normalize_referencia
# ---------------------------------------------------------------------------


class TestNormalizeReferencia:
    def test_collapses_double_space(self):
        assert normalize_referencia("(W-02NV4W)  - Vuelta") == normalize_referencia("(W-02NV4W) - Vuelta")

    def test_strips_whitespace(self):
        assert normalize_referencia("  hello  ") == "hello"

    def test_removes_accents(self):
        assert normalize_referencia("María García") == "maria garcia"

    def test_lowercase(self):
        assert normalize_referencia("BaRS1 - Tibidabo") == "bars1 - tibidabo"

    def test_combined(self):
        assert normalize_referencia("  BaRS1  - Tibidabo  (W-02VND1)  - Vuelta ") == "bars1 - tibidabo (w-02vnd1) - vuelta"

    def test_empty_string(self):
        assert normalize_referencia("") == ""

    def test_preserves_n_tilde(self):
        # ñ → n after NFKD + stripping Mn category
        assert normalize_referencia("Peña") == "pena"

    def test_tabs_and_newlines(self):
        assert normalize_referencia("a\t\tb\nc") == "a b c"


# ---------------------------------------------------------------------------
# _extract_w_code
# ---------------------------------------------------------------------------


class TestExtractWCode:
    def test_standard_case_id(self):
        assert _extract_w_code("BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta") == "W-02VND1"

    def test_no_w_code(self):
        assert _extract_w_code("MaRS2 - Gran Via 40 - Vuelta") is None

    def test_lowercase_w_code(self):
        assert _extract_w_code("(w-02nv4w)") == "w-02nv4w"

    def test_w_code_with_5_chars(self):
        assert _extract_w_code("(W-ABCDE)") == "W-ABCDE"

    def test_w_code_with_8_chars(self):
        assert _extract_w_code("(W-ABCDEF12)") == "W-ABCDEF12"

    def test_empty_string(self):
        assert _extract_w_code("") is None

    def test_w_code_at_start(self):
        assert _extract_w_code("W-0466A1 es el codigo") == "W-0466A1"


# ---------------------------------------------------------------------------
# verify_expediente_referencia — normalized comparison
# ---------------------------------------------------------------------------


class TestVerifyNormalized:
    """verify_expediente_referencia uses normalized comparison."""

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_double_space_matches(self, mock_fetch):
        mock_fetch.return_value = ("(W-02NV4W)  - Vuelta", False)
        result = verify_expediente_referencia(
            "444", "expedientes_judiciales",
            expected_referencia="(W-02NV4W) - Vuelta",
        )
        assert result["match"] is True
        assert result["found"] is True

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_accent_difference_matches(self, mock_fetch):
        mock_fetch.return_value = ("Gran Vía 40", False)
        result = verify_expediente_referencia(
            "500", "extrajudiciales",
            expected_referencia="Gran Via 40",
        )
        assert result["match"] is True

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_case_difference_matches(self, mock_fetch):
        mock_fetch.return_value = ("bars1 - tibidabo", False)
        result = verify_expediente_referencia(
            "100", "extrajudiciales",
            expected_referencia="BaRS1 - Tibidabo",
        )
        assert result["match"] is True

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_genuinely_different_does_not_match(self, mock_fetch):
        mock_fetch.return_value = ("Completely Different", False)
        result = verify_expediente_referencia(
            "100", "extrajudiciales",
            expected_referencia="Not The Same",
        )
        assert result["match"] is False

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_none_crm_ref_does_not_match(self, mock_fetch):
        mock_fetch.return_value = (None, False)
        result = verify_expediente_referencia(
            "100", "extrajudiciales",
            expected_referencia="Something",
        )
        assert result["match"] is False
        assert result["found"] is False

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_crm_unreachable(self, mock_fetch):
        mock_fetch.return_value = (None, True)
        result = verify_expediente_referencia(
            "100", "extrajudiciales",
            expected_referencia="Something",
        )
        assert result["match"] is False
        assert result["crm_unreachable"] is True


# --- _rest_search_por_texto (combobox F2 §18.6) --------------------------

def _items_multi(*rows: tuple[str, dict]) -> dict:
    """Respuesta REST con (id, {prop: value, ...}) por fila."""
    items = []
    for eid, props in rows:
        vals = [{"property": {"name": k}, "value": v} for k, v in props.items()]
        items.append({"id": str(eid), "values": vals})
    return {"totalItems": len(items), "items": items}


def test_rest_texto_judicial_or_like_dos_properties(_api_key):
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        return _mock_get_response(_items_multi(
            ("487", {"referencia_cliente": "BaRS3 - Torrent 41 - (W-02MA0R)",
                     "referencia_procurador": "P-2025/3447"}),
        ))

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        out = _rest_search_por_texto("expedientes_judiciales", "3447")

    assert out == [{"id": "487",
                    "label": "BaRS3 - Torrent 41 - (W-02MA0R)  ·  P-2025/3447"}]
    assert "element_registries/expedientes_judiciales" in captured["url"]
    p = captured["params"]
    assert ("filterGroup[filterGroups][0][condition]", "OR") in p
    assert ("filterGroup[filterGroups][0][filters][0][operator]", "like") in p
    assert ("filterGroup[filterGroups][0][filters][0][value]", "3447") in p
    assert ("filterGroup[filterGroups][0][filters][0][property]", "referencia_cliente") in p
    assert ("filterGroup[filterGroups][0][filters][1][property]", "referencia_procurador") in p
    assert ("filterGroup[filterGroups][0][filters][1][value]", "3447") in p


def test_rest_texto_extrajudicial_solo_referencia_camelcase(_api_key):
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        return _mock_get_response(_items_multi(
            ("500", {"Referencia_Cliente": "MaRS2 - Gran Via 40 - (W-0001)"}),
        ))

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        out = _rest_search_por_texto("extrajudiciales", "Gran Via")

    assert out == [{"id": "500", "label": "MaRS2 - Gran Via 40 - (W-0001)"}]
    assert "element_registries/extrajudiciales" in captured["url"]
    p = captured["params"]
    assert ("filterGroup[filterGroups][0][filters][0][property]", "Referencia_Cliente") in p
    # extrajudicial NO busca por referencia_procurador
    assert all(v != "referencia_procurador" for (_k, v) in p)


def test_rest_texto_normaliza_alias_extrajudicial(_api_key):
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        return _mock_get_response(_items_multi())

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        out = _rest_search_por_texto("expedientes_extrajudiciales", "algo")

    assert out == []
    assert "element_registries/extrajudiciales" in captured["url"]


def test_rest_texto_label_cae_a_procurador_si_no_hay_referencia(_api_key):
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get_response(_items_multi(
                   ("9", {"referencia_procurador": "SP-3599"}),
               ))):
        out = _rest_search_por_texto("expedientes_judiciales", "SP-3599")
    assert out == [{"id": "9", "label": "SP-3599"}]


def test_rest_texto_sin_api_key_devuelve_vacio(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "")
    assert _rest_search_por_texto("expedientes_judiciales", "x") == []


def test_rest_texto_elemento_desconocido_devuelve_vacio(_api_key):
    assert _rest_search_por_texto("clientes", "x") == []


def test_rest_texto_termino_vacio_devuelve_vacio(_api_key):
    assert _rest_search_por_texto("expedientes_judiciales", "   ") == []


def test_rest_texto_http_500_devuelve_vacio(_api_key):
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get_response({}, status=500)):
        assert _rest_search_por_texto("expedientes_judiciales", "x") == []
