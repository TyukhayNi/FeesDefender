"""Tests de core.procurador_search — búsqueda/lectura del CRM para el combobox F2."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.procurador_search import (
    fetch_expediente_datos,
    recompute_coincidencias,
    search_expedientes,
)


def _mock_legacy_client():
    client = MagicMock()
    client._check_session = MagicMock()
    client.__exit__ = MagicMock(return_value=False)
    return client


def _mock_get(json_data, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data
    return r


def test_search_expedientes_mapea_value_a_id():
    """El id del expediente es el campo `value` del autocomplete; label se conserva."""
    client = _mock_legacy_client()
    client._client.get.return_value = _mock_get(
        [{"id": 1, "label": "13 - 2026 · ACME", "value": "532", "data": []},
         {"id": 2, "label": "14 - 2026 · OTRO", "value": "533", "data": []}]
    )
    out = search_expedientes("ACME", client=client)
    assert out == [
        {"id": "532", "label": "13 - 2026 · ACME"},
        {"id": "533", "label": "14 - 2026 · OTRO"},
    ]


def test_search_expedientes_element_judicial_por_defecto():
    """Por defecto busca en expedientes_judiciales (el caso de procuradores)."""
    client = _mock_legacy_client()
    client._client.get.return_value = _mock_get([])
    search_expedientes("algo", client=client)
    url = client._client.get.call_args[0][0]
    assert "expedientes_judiciales" in url


def test_search_expedientes_element_override():
    """Se puede buscar en extrajudiciales / clientes (🔴 toggle)."""
    client = _mock_legacy_client()
    client._client.get.return_value = _mock_get([])
    search_expedientes("algo", element="clientes", client=client)
    url = client._client.get.call_args[0][0]
    assert "clientes" in url


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
