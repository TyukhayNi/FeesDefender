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


#: Forma MEDIDA sobre el exp 634 el 2026-09-04: tres colaboradores cuyas listas acumulan
#: 1, 2 y 3 entradas. El bloque `facturas` de abajo es **sintético**, no medido — el
#: servidor real NO envía los hijos sin vínculos. Se conserva a propósito para fijar que
#: un bloque vacío, SI llega, se respeta; y va marcado porque una fixture que se presenta
#: como medida y trae material inventado es un defecto de procedencia, no un detalle.
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
    # --- sintético a partir de aquí (ver nota de arriba) ---
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

def test_un_bloque_vacio_que_llegue_se_respeta(_api_key):
    """Si el servidor manda un hijo sin vinculos, sale con lista vacia — no se descarta.

    Ojo con lo que este test NO dice: el CRM real **no manda** los hijos sin vinculos,
    asi que un `{}` de vuelta NO permite distinguir «relacionable y sin ninguno» de «no
    relacionable». Eso lo responde `GET /api/view/config/{element}/relations`, y el
    docstring de `get_relaciones` lo declara asi.
    """
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

    # La peticion es la URL Y su autenticacion: sin esto, un mutante que vacie las
    # cabeceras sobrevive a todo el fichero y el fallo aparece en produccion como 401.
    headers = g.call_args.kwargs["headers"]
    assert headers["x-api-key"] == "k-de-prueba"
    assert headers["Accept"] == "application/json"
    assert g.call_args.kwargs["timeout"]


def test_status_no_200_levanta(_api_key):
    with patch("httpx.get", return_value=_respuesta({"detail": "nope"}, status=500)):
        with pytest.raises(SudespachoRelationsError, match="500"):
            get_relaciones("extrajudiciales", "634")


def test_sin_api_key_levanta_valueerror(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "")
    with pytest.raises(ValueError, match="SUDESPACHO_API_KEY"):
        get_relaciones("extrajudiciales", "634")


# ---------------------------------------------------------------------------
# Frontera 6 (R1 / H-06): toda forma inesperada del cuerpo es «NO PUDE LEER»
#
# El defecto que R1 encontro aqui es el mismo que este cambio existe para arreglar,
# un nivel mas abajo: el parser devolvia vacio ante cuerpos que no entendia, y un
# `{}` es indistinguible de «este expediente no tiene relaciones». Un llamador que
# verifica vinculos con eso concluye «faltan todos» — o, peor, «no hay nada que
# comprobar». Ahora cada forma desconocida levanta.
# ---------------------------------------------------------------------------

class TestCuerpoConFormaInesperada:

    @pytest.mark.parametrize("cuerpo, pista", [
        pytest.param({"element": "x"}, "la raíz es dict", id="raiz-dict"),
        pytest.param(None, "la raíz es NoneType", id="raiz-none"),
        pytest.param(["no soy un bloque"], "el bloque 0 es str", id="bloque-no-dict"),
        pytest.param([{"registries": {}}], "no nombra su `element`", id="bloque-sin-element"),
        pytest.param([{"element": 7, "registries": {}}], "no nombra su `element`",
                     id="element-no-str"),
        pytest.param([{"element": "colaboradores", "registries": []}],
                     "es list, no un objeto", id="registries-lista-vacia"),
        pytest.param([{"element": "colaboradores", "registries": [{"id": "1"}]}],
                     "es list, no un objeto", id="registries-lista-llena"),
        pytest.param([{"element": "colaboradores", "registries": {"1": "no soy lista"}}],
                     "no es una lista", id="entradas-no-lista"),
    ])
    def test_levanta_en_vez_de_devolver_vacio(self, _api_key, cuerpo, pista):
        with patch("httpx.get", return_value=_respuesta(cuerpo)):
            with pytest.raises(SudespachoRelationsError) as exc:
                get_relaciones("extrajudiciales", "634")
        assert pista in str(exc.value)
        assert "no pude leer" in str(exc.value).lower()

    def test_registries_ausente_o_none_si_es_vacio_legitimo(self, _api_key):
        """Distinto de una forma rara: `registries` ausente es «sin vinculos», no error."""
        cuerpo = [{"element": "colaboradores"},
                  {"element": "facturas", "registries": None}]
        with patch("httpx.get", return_value=_respuesta(cuerpo)):
            rel = get_relaciones("extrajudiciales", "634")
        assert rel == {"colaboradores": [], "facturas": []}


def test_dos_bloques_del_mismo_elemento_se_ACUMULAN(_api_key):
    """R1 / H-06: el segundo bloque pisaba al primero y afirmaba cero vinculos.

    Que el servidor no lo haga hoy no es la cuestion: perder un vinculo por
    sobreescritura silenciosa es exactamente lo que no puede pasar en la pieza que
    verifica vinculos.
    """
    cuerpo = [
        {"element": "colaboradores", "registries": {"1": [_registro("1", "ANA")]}},
        {"element": "colaboradores", "registries": {"2": [_registro("2", "BEA")]}},
    ]
    with patch("httpx.get", return_value=_respuesta(cuerpo)):
        rel = get_relaciones("extrajudiciales", "634")

    assert [r["id"] for r in rel["colaboradores"]] == ["1", "2"]


# ---------------------------------------------------------------------------
# Frontera 7 (R1 / H-05): esta capa COPIA los valores, no los juzga
# ---------------------------------------------------------------------------

def test_conserva_los_valores_falsy(_api_key):
    """`False`, `0` y `""` son datos. Filtrarlos borra la diferencia entre «campo
    vacio» y «campo ausente», que es justo lo que un verificador necesita ver."""
    cuerpo = [{"element": "colaboradores", "registries": {"40": [{
        "id": "40",
        "values": [
            _valor("nombre", "ANA"),
            {"property": {"name": "email"}, "value": ""},
            {"property": {"name": "activo"}, "value": False},
            {"property": {"name": "orden"}, "value": 0},
        ],
    }]}}]
    with patch("httpx.get", return_value=_respuesta(cuerpo)):
        rel = get_relaciones("extrajudiciales", "634")

    assert rel["colaboradores"] == [
        {"id": "40", "nombre": "ANA", "email": "", "activo": False, "orden": 0}
    ]
