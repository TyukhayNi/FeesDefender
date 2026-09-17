"""Lecturas de la API: paginación, filtros y el nombre del adjunto en base64url."""
from __future__ import annotations

import base64
import datetime as dt
import json
from decimal import Decimal

import pytest

from core import codicert
from tests._dobles.fake_codicert import FakeCliente

FICHA = codicert.Ficha(token="t", vence=dt.datetime.max.replace(tzinfo=dt.timezone.utc))


def test_credito_devuelve_decimal_y_no_float():
    cliente = FakeCliente({("GET", "/usuarios/credito"): (200, {"estado": "OK", "datos": {"credito": 398.1388}})})
    c = codicert.credito(FICHA, entorno="produccion", cliente=cliente)
    assert c == Decimal("398.1388") and isinstance(c, Decimal)


def test_credito_con_valor_no_numerico_levanta_codicert_error():
    """Hallazgo de revisión: la guarda comprobaba `isinstance(datos, dict)` y que la
    clave existiera, pero no que el VALOR fuera numérico. `{"credito": None}` la
    pasaba y `Decimal(str(None))` reventaba con `decimal.InvalidOperation` crudo,
    fuera del contrato del módulo (solo falla con `CodicertError`)."""
    cliente = FakeCliente({("GET", "/usuarios/credito"): (200, {"estado": "OK", "datos": {"credito": None}})})
    with pytest.raises(codicert.CodicertError):
        codicert.credito(FICHA, entorno="produccion", cliente=cliente)


def test_listar_pide_longitud_100_y_no_menos_de_10():
    cliente = FakeCliente({("GET", "/envios"): (200, {
        "estado": "OK", "datos": [], "pagina": 1, "longitud": 100, "total": 0, "totalPaginas": 0})})
    list(codicert.listar(FICHA, entorno="sandbox", cliente=cliente))
    assert cliente.llamadas[0][2]["params"]["longitud"] == 100


def test_listar_con_longitud_en_filtros_no_sobrescribe_la_reservada():
    """Hallazgo de revisión: `{"longitud": ..., "pagina": ..., **filtros}` deja que
    un `longitud` en `filtros` gane sobre el valor fijo del módulo. Medido: el
    servidor rechaza `longitud` por debajo de 10, así que un llamador que pase
    `longitud=5` no debe poder tumbar la paginación."""
    cliente = FakeCliente({("GET", "/envios"): (200, {
        "estado": "OK", "datos": [], "pagina": 1, "longitud": 100, "total": 0, "totalPaginas": 0})})
    list(codicert.listar(FICHA, entorno="sandbox", cliente=cliente, longitud=5))
    assert cliente.llamadas[0][2]["params"]["longitud"] == 100


class _RespuestaPagina:
    """Respuesta ad hoc con un cuerpo JSON ya construido, para `_ClientePorPagina`."""

    def __init__(self, cuerpo):
        self.status_code = 200
        self._cuerpo = cuerpo

    def json(self):
        return self._cuerpo


class _RespuestaCuerpoCorrupto:
    """Respuesta ad hoc cuyo `.json()` explota, como un cuerpo corrupto de verdad.

    Mismo idioma que `test_codicert_token.py`: el doble compartido
    (`FakeCliente`/`_Respuesta`) devuelve JSON ya construido y no puede fallar al
    parsear.
    """

    status_code = 200  # el fallo es el cuerpo, no el transporte

    def json(self):
        raise json.JSONDecodeError("cuerpo corrupto", "", 0)


class _ClientePorPagina:
    """Cliente ad hoc: sirve una respuesta distinta según el número de página.

    `FakeCliente` mapea por `(método, sufijo)` y devuelve SIEMPRE la misma respuesta
    para esa clave, así que no sirve para un guion que cambie por llamada (aquí,
    página 1 válida y página 2 corrupta/distinta). No se toca el doble compartido:
    este cliente vive solo en este fichero.
    """

    def __init__(self, respuestas_por_pagina):
        self._respuestas = respuestas_por_pagina
        self.llamadas = []

    def request(self, metodo, url, **kw):
        self.llamadas.append((metodo, url, kw))
        return self._respuestas[kw["params"]["pagina"]]


def test_listar_recorre_todas_las_paginas():
    """Contenido DISTINTO por página (`id` "a" en la 1, "b" en la 2): si `listar`
    confundiera la página 2 con la 1 servida otra vez, este test lo vería como un
    `id` repetido o el orden cambiado. La versión anterior de este test servía el
    mismo cuerpo en las dos llamadas y solo comprobaba conteos — no distinguía dos
    páginas reales de la misma servida dos veces."""
    cliente = _ClientePorPagina({
        1: _RespuestaPagina({"estado": "OK", "datos": [{"id": "a"}], "pagina": 1,
                             "longitud": 100, "total": 2, "totalPaginas": 2}),
        2: _RespuestaPagina({"estado": "OK", "datos": [{"id": "b"}], "pagina": 2,
                             "longitud": 100, "total": 2, "totalPaginas": 2}),
    })
    elementos = list(codicert.listar(FICHA, entorno="sandbox", cliente=cliente))
    assert [e["id"] for e in elementos] == ["a", "b"]
    assert [l[2]["params"]["pagina"] for l in cliente.llamadas] == [1, 2]


def test_listar_con_cuerpo_corrupto_en_pagina_intermedia_levanta_codicert_error():
    """Hallazgo de revisión: `listar` era la única lectura del módulo que llamaba a
    `.json()` sin pasar por `_json_o_vacio`. Con una página 1 válida y una página 2
    de cuerpo corrupto (como el `.json()` que explota de verdad), el
    `JSONDecodeError` crudo llegaba hasta el llamador en vez de `CodicertError`."""
    cliente = _ClientePorPagina({
        1: _RespuestaPagina({"estado": "OK", "datos": [{"id": "a"}], "pagina": 1,
                             "longitud": 100, "total": 2, "totalPaginas": 2}),
        2: _RespuestaCuerpoCorrupto(),
    })
    with pytest.raises(codicert.CodicertError):
        list(codicert.listar(FICHA, entorno="sandbox", cliente=cliente))


def test_listar_con_cuerpo_no_dict_levanta_codicert_error():
    """El cuerpo parsea (es JSON válido) pero no es un objeto: sin guarda de forma,
    `cuerpo.get("datos")` revienta con `AttributeError` crudo, fuera de contrato."""
    cliente = FakeCliente({("GET", "/envios"): (200, ["no", "es", "un", "dict"])})
    with pytest.raises(codicert.CodicertError):
        list(codicert.listar(FICHA, entorno="sandbox", cliente=cliente))


def test_listar_con_total_paginas_no_numerico_levanta_codicert_error():
    """`totalPaginas` no numérico: sin guarda, `pagina >= cuerpo.get("totalPaginas")`
    revienta con `TypeError` crudo, fuera de contrato."""
    cliente = FakeCliente({("GET", "/envios"): (200, {
        "estado": "OK", "datos": [], "pagina": 1, "longitud": 100, "total": 0,
        "totalPaginas": "no-es-un-numero"})})
    with pytest.raises(codicert.CodicertError):
        list(codicert.listar(FICHA, entorno="sandbox", cliente=cliente))


def test_descargar_adjunto_codifica_el_nombre_en_base64url_sin_relleno():
    nombre = "9dc535a2-8053-4732-ab80-6a1d86d90dfd.pdf"
    esperado = base64.urlsafe_b64encode(nombre.encode()).decode().rstrip("=")
    cliente = FakeCliente({("GET", f"/adjuntos/{esperado}"): (200, None, b"%PDF")})
    assert codicert.descargar_adjunto(FICHA, "006x", nombre, entorno="produccion",
                                      cliente=cliente) == b"%PDF"


def test_certificado_devuelve_los_bytes_del_pdf():
    cliente = FakeCliente({("GET", "/certificados/comunicacion/006x"): (200, None, b"%PDF-1.7")})
    assert codicert.certificado(FICHA, "006x", entorno="sandbox", cliente=cliente) == b"%PDF-1.7"


def test_estados_devuelve_la_lista_del_historico():
    cliente = FakeCliente({("GET", "/envios/006x/estados"): (200, {
        "estado": "OK", "datos": [{"codigo": 17, "titulo": "Entregado", "fecha": "2026-09-17T10:00:00+02:00"}]})})
    assert codicert.estados(FICHA, "006x", entorno="sandbox", cliente=cliente)[0]["codigo"] == 17
