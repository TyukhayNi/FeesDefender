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
