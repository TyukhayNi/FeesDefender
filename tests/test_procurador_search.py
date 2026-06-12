"""Tests de core.procurador_search — búsqueda/lectura del CRM para el combobox F2."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.procurador_search import (
    ELEMENTOS_BUSCABLES,
    fetch_expediente_datos,
    recompute_coincidencias,
    search_expedientes,
)


@pytest.fixture
def _api_key(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test_key_abc")


def _mock_get(json_data, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data
    return r


def _items_multi(*rows):
    items = []
    for eid, props in rows:
        vals = [{"property": {"name": k}, "value": v} for k, v in props.items()]
        items.append({"id": str(eid), "values": vals})
    return {"totalItems": len(items), "items": items}


def test_clientes_fuera_de_elementos_buscables():
    """`clientes` se retiró: no tiene referencia ni alimenta recompute."""
    assert "clientes" not in ELEMENTOS_BUSCABLES
    assert "expedientes_judiciales" in ELEMENTOS_BUSCABLES


def test_search_termino_vacio_no_toca_red():
    with patch("core.sudespacho_relations.httpx.get") as g:
        assert search_expedientes("   ") == []
        g.assert_not_called()


def test_search_por_texto_mapea_id_y_label(_api_key):
    """Búsqueda libre → REST OR-like; devuelve [{id,label}] con ref del procurador."""
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get(_items_multi(
                   ("487", {"referencia_cliente": "BaRS3 - Torrent 41 (W-02MA0R)",
                            "referencia_procurador": "P-2025/3447"}),
               ))):
        out = search_expedientes("Torrent")
    assert out == [{"id": "487",
                    "label": "BaRS3 - Torrent 41 (W-02MA0R)  ·  P-2025/3447"}]


def test_search_num_serie_dedup_id_en_ambas_ramas(_api_key):
    """Un id que aparece por texto Y por num/serie sale UNA sola vez."""
    def _get(url, *, params, headers, timeout):
        # Ambas ramas (texto y num/serie) devuelven el MISMO expediente 487.
        return _mock_get(_items_multi(
            ("487", {"num_expediente": "63", "serie_expediente": "2024",
                     "referencia_cliente": "BaRS3 - Torrent 41 (W-02MA0R)"}),
        ))

    with patch("core.sudespacho_relations.httpx.get", side_effect=_get):
        out = search_expedientes("63/2024")
    assert out == [{"id": "487", "label": "BaRS3 - Torrent 41 (W-02MA0R)"}]
    assert len(out) == 1


def test_search_num_serie_dispara_rama_numerica_y_fusiona(_api_key):
    """'63/2024' → texto (sin hits) + num/serie (hit 487), fusionado sin duplicar."""
    def _get(url, *, params, headers, timeout):
        es_num = ("filterGroup[filterGroups][0][filters][0][property]",
                  "num_expediente") in params
        if es_num:
            return _mock_get(_items_multi(
                ("487", {"num_expediente": "63", "serie_expediente": "2024",
                         "referencia_cliente": "BaRS3 - Torrent 41 (W-02MA0R)"}),
            ))
        return _mock_get(_items_multi())  # la búsqueda por texto no encuentra "63/2024"

    with patch("core.sudespacho_relations.httpx.get", side_effect=_get):
        out = search_expedientes("63/2024")
    assert out == [{"id": "487", "label": "BaRS3 - Torrent 41 (W-02MA0R)"}]


def test_search_ano_barra_num_no_dispara_rama_numerica(_api_key):
    """'2025/7449' (ref de procurador, año delante) NO va a num/serie, solo texto."""
    llamadas: list = []

    def _get(url, *, params, headers, timeout):
        llamadas.append(params)
        return _mock_get(_items_multi(
            ("487", {"referencia_cliente": "BaRS3 - Torrent 41 (W-02MA0R)",
                     "referencia_procurador": "2025/7449"}),
        ))

    with patch("core.sudespacho_relations.httpx.get", side_effect=_get):
        out = search_expedientes("2025/7449")
    # Solo una llamada (texto); ninguna con equal num_expediente
    assert len(llamadas) == 1
    assert all(("filterGroup[filterGroups][0][filters][0][property]",
                "num_expediente") not in p for p in llamadas)
    assert out == [{"id": "487",
                    "label": "BaRS3 - Torrent 41 (W-02MA0R)  ·  2025/7449"}]


def test_search_alias_extrajudicial_normaliza_slug(_api_key):
    captured: dict = {}

    def _get(url, *, params, headers, timeout):
        captured["url"] = url
        return _mock_get(_items_multi())

    with patch("core.sudespacho_relations.httpx.get", side_effect=_get):
        search_expedientes("algo", element="expedientes_extrajudiciales")
    assert "element_registries/extrajudiciales" in captured["url"]


def test_search_sin_api_key_devuelve_vacio(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "")
    assert search_expedientes("Torrent") == []


def test_fetch_expediente_datos_parsea_values_por_id():
    """Lee los _MATCH_PROPERTIES del expediente vía element_registries (REST)."""
    client = MagicMock()
    client.__exit__ = MagicMock(return_value=False)
    client._client.get.return_value = _mock_get({
        "hydra:member": [{
            "id": 532,
            "values": [
                {"property": {"name": "num_expediente"}, "value": 13},
                {"property": {"name": "serie_expediente"}, "value": "2026"},
                {"property": {"name": "juzgado"}, "value": "JPI 4 Valencia"},
                {"property": {"name": "ignorada"}, "value": "x"},
            ],
        }]
    })
    datos = fetch_expediente_datos(532, client=client)
    assert datos["id"] == 532
    assert datos["num_expediente"] == 13
    assert datos["juzgado"] == "JPI 4 Valencia"
    assert "ignorada" not in datos                 # solo _MATCH_PROPERTIES


def test_fetch_expediente_datos_sin_resultado():
    """Expediente inexistente / HTTP no-200 → dict vacío (no rompe la tarjeta)."""
    client = MagicMock()
    client.__exit__ = MagicMock(return_value=False)
    client._client.get.return_value = _mock_get({"hydra:member": []}, status=200)
    assert fetch_expediente_datos(999, client=client) == {}


def test_fetch_expediente_datos_http_no_200():
    """HTTP != 200 → dict vacío (degrada, no rompe la tarjeta)."""
    client = MagicMock()
    client.__exit__ = MagicMock(return_value=False)
    client._client.get.return_value = _mock_get({}, status=404)
    assert fetch_expediente_datos(999, client=client) == {}


def test_recompute_coincidencias_delega_en_check_signal_matches():
    """Reconstruye IntakeSignals desde el dict persistido y recomputa coincidencias."""
    signals_dict = {
        "num_expediente": 13, "serie_expediente": "2026",
        "juzgado": "Juzgado de Primera Instancia nº 4 de Valencia",
        "num_asunto": "123/2025", "tipo_procedimiento": "ordinario",
    }
    datos_expediente = {
        "id": 532, "num_expediente": 13, "serie_expediente": "2026",
        # Token-match: comparte 'juzgado','primera','instancia','valencia' (4/4 ≥ 70%)
        "juzgado": "Juzgado Primera Instancia 4 Valencia",
        "num_asunto": "123 / 2025",
        "tipo_procedimiento": "Juicio ordinario",
    }
    out = recompute_coincidencias(signals_dict, datos_expediente)
    assert set(out) == {"num_expediente", "serie_expediente", "juzgado",
                        "num_asunto", "tipo_procedimiento"}


def test_recompute_coincidencias_parcial():
    """Solo num/serie coinciden → solo esos dos."""
    signals_dict = {"num_expediente": 13, "serie_expediente": "2026", "juzgado": "X"}
    datos = {"num_expediente": 13, "serie_expediente": "2026", "juzgado": "Y distinto"}
    out = recompute_coincidencias(signals_dict, datos)
    assert set(out) == {"num_expediente", "serie_expediente"}


def test_recompute_coincidencias_sin_datos():
    """datos_expediente vacío → sin coincidencias (no rompe)."""
    assert recompute_coincidencias({"num_expediente": 13}, {}) == []
