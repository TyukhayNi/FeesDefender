"""Lecturas de la API: paginación, filtros y el nombre del adjunto en base64url."""
from __future__ import annotations

import base64
import datetime as dt
from decimal import Decimal

from core import codicert
from tests._dobles.fake_codicert import FakeCliente

FICHA = codicert.Ficha(token="t", vence=dt.datetime.max.replace(tzinfo=dt.timezone.utc))


def test_credito_devuelve_decimal_y_no_float():
    cliente = FakeCliente({("GET", "/usuarios/credito"): (200, {"estado": "OK", "datos": {"credito": 398.1388}})})
    c = codicert.credito(FICHA, entorno="produccion", cliente=cliente)
    assert c == Decimal("398.1388") and isinstance(c, Decimal)


def test_listar_pide_longitud_100_y_no_menos_de_10():
    cliente = FakeCliente({("GET", "/envios"): (200, {
        "estado": "OK", "datos": [], "pagina": 1, "longitud": 100, "total": 0, "totalPaginas": 0})})
    list(codicert.listar(FICHA, entorno="sandbox", cliente=cliente))
    assert cliente.llamadas[0][2]["params"]["longitud"] == 100


def test_listar_recorre_todas_las_paginas():
    pag = {"estado": "OK", "datos": [{"id": "a"}], "pagina": 1, "longitud": 100,
           "total": 2, "totalPaginas": 2}
    cliente = FakeCliente({("GET", "/envios"): (200, pag)})
    assert len(list(codicert.listar(FICHA, entorno="sandbox", cliente=cliente))) == 2
    assert [l[2]["params"]["pagina"] for l in cliente.llamadas] == [1, 2]


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
