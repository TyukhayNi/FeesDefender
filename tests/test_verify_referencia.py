"""Tests de la validación preventiva referencia local ↔ CRM.

Origen: incidencia BaRR3 (2026-05-11) — el caso local
"BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU" tenía registrado en
``_caso.md`` el expediente CRM ID 648 cuando el expediente real de Roser
es 649. ID 648 era un expediente de prueba creado durante el desarrollo
el 2026-04-26 (HAR ``judicial_648.har``, "Pull real expediente 648:
5 docs"); el vínculo se quedó colgando en ``_caso.md``.

La validación :func:`core.sudespacho_relations.verify_expediente_referencia`
consulta el CRM tras vincular un expediente y compara la
``referencia_cliente`` devuelta con la esperada localmente.

Cobertura mínima exigida por el usuario:

- ``test_validacion_referencia_match`` — referencias iguales → ``match=True``.
- ``test_validacion_referencia_mismatch`` — referencias distintas →
  ``match=False`` y ``crm_unreachable=False`` (sí se pudo consultar).
- ``test_validacion_referencia_crm_no_disponible`` — CRM caído (red o
  status 500) → ``crm_unreachable=True``, sin excepción.

Se añade también la rama "API key vacía" (otro caso de ``crm_unreachable``)
porque es el más probable en local sin el entorno cargado.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from core.sudespacho_relations import (
    _REFERENCIA_PROP_BY_ELEMENT,
    _normalize_element,
    fetch_referencia_cliente,
    verify_expediente_referencia,
)


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _build_items_response(expediente_id: int | str, prop: str, value: str | None) -> dict:
    """Construye una respuesta REST mínima compatible con
    ``/api/element_registries/<element>`` para un único expediente.

    El parser de :func:`fetch_referencia_cliente` busca el ``id`` en
    ``items[*].id`` y la propiedad en ``items[*].values[*]``. Reproducimos
    esa estructura tal como la devolvía el endpoint el 2026-05-07.
    """
    item: dict = {
        "id": str(expediente_id),
        "values": [],
    }
    if value is not None:
        item["values"].append({
            "property": {"name": prop},
            "value":    value,
        })
    return {
        "totalItems": 1,
        "items": [item],
    }


def _mock_response(json_data: dict, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data
    r.text = ""
    return r


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    """Asegura que la API key tiene valor por defecto en cada test.

    Los tests que necesitan probar el caso "API key vacía" la limpian
    explícitamente. El resto asume entorno productivo.
    """
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test_key_abc")


# ---------------------------------------------------------------------------
# fetch_referencia_cliente — capa baja
# ---------------------------------------------------------------------------

def test_fetch_referencia_judicial_devuelve_valor_y_no_unreachable():
    payload = _build_items_response(
        649,
        prop=_REFERENCIA_PROP_BY_ELEMENT["expedientes_judiciales"],
        value="BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU",
    )
    with patch(
        "core.sudespacho_relations.httpx.get",
        return_value=_mock_response(payload, status=200),
    ):
        ref, unreachable = fetch_referencia_cliente(649, "expedientes_judiciales")
    assert ref == "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
    assert unreachable is False


def test_fetch_referencia_extrajudicial_usa_camelcase():
    """El endpoint extrajudicial usa ``Referencia_Cliente`` (CamelCase) — el
    parser debe pedir esa propiedad, no la versión judicial."""
    payload = _build_items_response(
        500,
        prop=_REFERENCIA_PROP_BY_ELEMENT["extrajudiciales"],
        value="EV-2026-001",
    )
    captured_params: dict = {}

    def _capturing_get(url, *, params, headers, timeout):  # noqa: D401
        captured_params["params"] = params
        return _mock_response(payload, status=200)

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        ref, unreachable = fetch_referencia_cliente(500, "extrajudiciales")

    assert ref == "EV-2026-001"
    assert unreachable is False
    # Verifica que el property[0] pedido sea Referencia_Cliente (CamelCase)
    assert ("properties[0]", "Referencia_Cliente") in captured_params["params"]


def test_fetch_referencia_acepta_alias_judiciales():
    """El slug ``"judiciales"`` (legacy en frontmatter / CLI) se normaliza."""
    payload = _build_items_response(
        700,
        prop="referencia_cliente",
        value="MaRS6 - Calle Mayor 10",
    )
    with patch(
        "core.sudespacho_relations.httpx.get",
        return_value=_mock_response(payload, status=200),
    ):
        ref, unreachable = fetch_referencia_cliente(700, "judiciales")
    assert ref == "MaRS6 - Calle Mayor 10"
    assert unreachable is False


def test_fetch_referencia_element_desconocido_devuelve_unreachable():
    ref, unreachable = fetch_referencia_cliente(648, "elemento_inexistente")
    assert ref is None
    assert unreachable is True


def test_fetch_referencia_sin_api_key_devuelve_unreachable(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "")
    ref, unreachable = fetch_referencia_cliente(648, "expedientes_judiciales")
    assert ref is None
    assert unreachable is True


def test_fetch_referencia_http_500_es_unreachable():
    with patch(
        "core.sudespacho_relations.httpx.get",
        return_value=_mock_response({}, status=500),
    ):
        ref, unreachable = fetch_referencia_cliente(648, "expedientes_judiciales")
    assert ref is None
    assert unreachable is True


def test_fetch_referencia_red_caida_es_unreachable():
    with patch(
        "core.sudespacho_relations.httpx.get",
        side_effect=httpx.ConnectError("timeout"),
    ):
        ref, unreachable = fetch_referencia_cliente(648, "expedientes_judiciales")
    assert ref is None
    assert unreachable is True


def test_fetch_referencia_id_no_aparece_no_es_unreachable():
    """Si el CRM contesta 200 pero items no contiene el ID, no es
    "unreachable" — el CRM funciona, pero el expediente no existe."""
    payload = {"totalItems": 0, "items": []}
    with patch(
        "core.sudespacho_relations.httpx.get",
        return_value=_mock_response(payload, status=200),
    ):
        ref, unreachable = fetch_referencia_cliente(999_999, "expedientes_judiciales")
    assert ref is None
    assert unreachable is False


# ---------------------------------------------------------------------------
# verify_expediente_referencia — contrato público (los 3 tests pedidos)
# ---------------------------------------------------------------------------

def test_validacion_referencia_match():
    """Referencias iguales → match=True."""
    case_id = "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
    payload = _build_items_response(
        649,
        prop=_REFERENCIA_PROP_BY_ELEMENT["expedientes_judiciales"],
        value=case_id,
    )
    with patch(
        "core.sudespacho_relations.httpx.get",
        return_value=_mock_response(payload, status=200),
    ):
        result = verify_expediente_referencia(
            649, "expedientes_judiciales",
            expected_referencia=case_id,
        )

    assert result["match"] is True
    assert result["crm_unreachable"] is False
    assert result["found"] is True
    assert result["crm_referencia"] == case_id
    assert result["expected_referencia"] == case_id
    assert result["expediente_id"] == "649"
    assert result["element"] == "expedientes_judiciales"


def test_validacion_referencia_mismatch():
    """Referencias distintas → match=False, sin excepción."""
    case_id_local   = "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
    referencia_crm  = "OTRO CASO QUE NO ES BARR3"
    payload = _build_items_response(
        648,
        prop=_REFERENCIA_PROP_BY_ELEMENT["expedientes_judiciales"],
        value=referencia_crm,
    )
    with patch(
        "core.sudespacho_relations.httpx.get",
        return_value=_mock_response(payload, status=200),
    ):
        result = verify_expediente_referencia(
            648, "expedientes_judiciales",
            expected_referencia=case_id_local,
        )

    assert result["match"] is False
    assert result["crm_unreachable"] is False
    assert result["found"] is True
    assert result["crm_referencia"] == referencia_crm
    assert result["expected_referencia"] == case_id_local


def test_validacion_referencia_crm_no_disponible():
    """CRM caído → no rompe, devuelve crm_unreachable=True."""
    with patch(
        "core.sudespacho_relations.httpx.get",
        side_effect=httpx.ConnectError("connection refused"),
    ):
        result = verify_expediente_referencia(
            648, "expedientes_judiciales",
            expected_referencia="cualquier cosa",
        )

    assert result["crm_unreachable"] is True
    assert result["match"] is False
    assert result["found"] is False
    assert result["crm_referencia"] is None
    # No se ha lanzado ninguna excepción — la función "nunca lanza".


# ---------------------------------------------------------------------------
# Casos auxiliares de robustez
# ---------------------------------------------------------------------------

def test_validacion_match_es_tolerante_a_espacios():
    """``"  X  "`` ↔ ``"X"`` se consideran match — el CRM podría devolver
    valores con padding y no queremos un falso positivo de mismatch."""
    case_id = "BaRR3 - Roser 39"
    payload = _build_items_response(
        649,
        prop=_REFERENCIA_PROP_BY_ELEMENT["expedientes_judiciales"],
        value=f"  {case_id}  ",
    )
    with patch(
        "core.sudespacho_relations.httpx.get",
        return_value=_mock_response(payload, status=200),
    ):
        result = verify_expediente_referencia(
            649, "expedientes_judiciales",
            expected_referencia=case_id,
        )
    assert result["match"] is True


def test_validacion_match_es_sensible_a_mayusculas():
    """``"barr3"`` ↔ ``"BaRR3"`` NO debe matchear — la referencia es un
    identificador, no texto libre. Si el CRM la cambia, queremos saberlo."""
    payload = _build_items_response(
        649,
        prop=_REFERENCIA_PROP_BY_ELEMENT["expedientes_judiciales"],
        value="barr3 - roser 39",
    )
    with patch(
        "core.sudespacho_relations.httpx.get",
        return_value=_mock_response(payload, status=200),
    ):
        result = verify_expediente_referencia(
            649, "expedientes_judiciales",
            expected_referencia="BaRR3 - Roser 39",
        )
    assert result["match"] is False


def test_validacion_expected_none_no_matchea_aunque_crm_valida():
    """Si el caller no sabe qué referencia esperar (``expected_referencia=None``),
    el resultado nunca es match — pero tampoco lanza."""
    payload = _build_items_response(
        649,
        prop=_REFERENCIA_PROP_BY_ELEMENT["expedientes_judiciales"],
        value="BaRR3 - Roser",
    )
    with patch(
        "core.sudespacho_relations.httpx.get",
        return_value=_mock_response(payload, status=200),
    ):
        result = verify_expediente_referencia(
            649, "expedientes_judiciales",
            expected_referencia=None,
        )
    assert result["match"] is False
    assert result["crm_referencia"] == "BaRR3 - Roser"


# ---------------------------------------------------------------------------
# Sanity de la tabla de alias
# ---------------------------------------------------------------------------

def test_normalize_element_alias_basicos():
    assert _normalize_element("judiciales") == "expedientes_judiciales"
    assert _normalize_element("expedientes_judiciales") == "expedientes_judiciales"
    assert _normalize_element("extrajudiciales") == "extrajudiciales"
    assert _normalize_element("expedientes_extrajudiciales") == "extrajudiciales"
    assert _normalize_element("") is None
    assert _normalize_element("foo") is None
