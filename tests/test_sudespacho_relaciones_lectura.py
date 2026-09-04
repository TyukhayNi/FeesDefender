"""Lectura de las relaciones de un expediente: `get_relaciones`.

Contrato descubierto sondeando el CRM en vivo el 2026-09-04 (W-02Q38C / exp 634).
La ruta de lectura NO es `relation_element` —que responde 405 `Allow: POST, PUT,
DELETE`— sino `GET /api/related_register/{element}/{id}`.

La trampa del formato, medida y no supuesta: `registries` llavea por id, pero la
lista de la clave `N` **arrastra todos los registros anteriores**; el propio es el
que casa por `id`. Aplanar todas las entradas triplica los vínculos.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.sudespacho_relations import (
    SudespachoRelationsError,
    _REST_RELATED_REGISTER_PATH,
    get_relaciones,
)


def _valor(nombre: str, valor: str) -> dict:
    return {"property": {"name": nombre}, "value": valor}


def _registro(rid: str, nombre: str, email: str = "") -> dict:
    vals = [_valor("nombre", nombre)]
    if email:
        vals.append(_valor("email", email))
    return {"isPrimary": False, "id": rid, "values": vals}


def _respuesta(bloques: list[dict], status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = bloques
    r.text = str(bloques)
    return r


#: La forma EXACTA que devolvió el CRM para el expediente 634: tres colaboradores
#: cuyas listas acumulan 1, 2 y 3 entradas respectivamente.
_ACUMULADO = [
    {
        "element": "clientes_propios",
        "registries": {"2": [_registro("2", "EV MMC SPAIN, S.L.U.")]},
    },
    {
        "element": "clientes_contrarios",
        "registries": {"1108": [_registro("1108", "ALBERTO CAMPRUBI CORDAL")]},
    },
    {
        "element": "colaboradores",
        "registries": {
            "40": [_registro("40", "JORDI CARBONELL", "jordi@ev.com")],
            "61": [
                _registro("40", "JORDI CARBONELL", "jordi@ev.com"),
                _registro("61", "FERRAN PLAZAS", "ferran@ev.com"),
            ],
            "466": [
                _registro("40", "JORDI CARBONELL", "jordi@ev.com"),
                _registro("61", "FERRAN PLAZAS", "ferran@ev.com"),
                _registro("466", "AURELIA MORENO", "aurelia@ev.com"),
            ],
        },
    },
    {"element": "facturas", "registries": {}},
]


@pytest.fixture()
def _api_key(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "k-de-prueba")


# ---------------------------------------------------------------------------
# Frontera 1: se cuenta UN vínculo por clave, no uno por entrada
# ---------------------------------------------------------------------------

def test_desacumula_no_cuenta_una_vez_por_entrada(_api_key):
    """Las listas acumuladas del servidor NO deben inflar el recuento.

    Con el cuerpo real del exp 634 hay 3 colaboradores. Aplanar todas las
    entradas daría 6 y triplicaría al primero: ése es el mutante que mata.
    """
    with patch("httpx.get", return_value=_respuesta(_ACUMULADO)):
        rel = get_relaciones("extrajudiciales", "634")

    assert [r["id"] for r in rel["colaboradores"]] == ["40", "61", "466"]
    assert len(rel["colaboradores"]) == 3


# ---------------------------------------------------------------------------
# Frontera 2: el registro de la clave K es el que CASA por id, no el ultimo
# ---------------------------------------------------------------------------

def test_elige_el_registro_que_casa_por_id_no_el_ultimo(_api_key):
    """Si el servidor deja de acumular —o acumula al reves— el vinculo sigue bien.

    `lista[-1]` acierta solo mientras el arrastre ponga el propio al final. La
    propiedad real es «el registro de la clave K es aquel cuyo id es K».
    """
    invertido = [{
        "element": "colaboradores",
        "registries": {
            "466": [
                _registro("466", "AURELIA MORENO", "aurelia@ev.com"),
                _registro("61", "FERRAN PLAZAS", "ferran@ev.com"),
            ],
        },
    }]
    with patch("httpx.get", return_value=_respuesta(invertido)):
        rel = get_relaciones("extrajudiciales", "634")

    assert len(rel["colaboradores"]) == 1
    assert rel["colaboradores"][0]["nombre"] == "AURELIA MORENO"


def test_si_ninguna_entrada_casa_por_id_no_inventa_el_vinculo(_api_key):
    """Una clave sin registro propio no se rellena con un registro ajeno."""
    huerfano = [{
        "element": "colaboradores",
        "registries": {"999": [_registro("40", "JORDI CARBONELL", "jordi@ev.com")]},
    }]
    with patch("httpx.get", return_value=_respuesta(huerfano)):
        rel = get_relaciones("extrajudiciales", "634")

    assert rel["colaboradores"] == [{"id": "999"}]


# ---------------------------------------------------------------------------
# Frontera 3: los elementos SIN vinculos no se confunden con vinculos
# ---------------------------------------------------------------------------

def test_elemento_relacionable_sin_vinculos_queda_vacio(_api_key):
    """`facturas` es relacionable y no tiene ninguna: lista vacia, no ausencia."""
    with patch("httpx.get", return_value=_respuesta(_ACUMULADO)):
        rel = get_relaciones("extrajudiciales", "634")

    assert rel["facturas"] == []
    assert rel["clientes_propios"][0]["nombre"] == "EV MMC SPAIN, S.L.U."


# ---------------------------------------------------------------------------
# Frontera 4: los valores se aplanan a {property: value}
# ---------------------------------------------------------------------------

def test_aplana_los_valores_junto_al_id(_api_key):
    with patch("httpx.get", return_value=_respuesta(_ACUMULADO)):
        rel = get_relaciones("extrajudiciales", "634")

    assert rel["clientes_contrarios"] == [
        {"id": "1108", "nombre": "ALBERTO CAMPRUBI CORDAL"}
    ]


# ---------------------------------------------------------------------------
# Frontera 5: la ruta es related_register, y un no-200 es error
# ---------------------------------------------------------------------------

def test_usa_la_ruta_related_register(_api_key):
    with patch("httpx.get", return_value=_respuesta([])) as g:
        get_relaciones("extrajudiciales", "634")

    url = g.call_args[0][0]
    assert url.endswith(_REST_RELATED_REGISTER_PATH.format(
        element="extrajudiciales", exp_id="634"))
    assert "/api/related_register/" in url
    assert "/api/relation_element/" not in url


def test_status_no_200_levanta(_api_key):
    with patch("httpx.get", return_value=_respuesta({"detail": "nope"}, status=500)):
        with pytest.raises(SudespachoRelationsError, match="500"):
            get_relaciones("extrajudiciales", "634")


def test_sin_api_key_levanta_valueerror(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "")
    with pytest.raises(ValueError, match="SUDESPACHO_API_KEY"):
        get_relaciones("extrajudiciales", "634")
