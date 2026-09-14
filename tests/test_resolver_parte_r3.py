"""R3 de P6 — frontera E: pedido, recibido y total NO son la misma información.

La R2 remedió la paginación subiendo el límite de 5 a 50 y parando si llegaban 50 o más. La
R3 midió que eso cubre **un** truncamiento —el que delata la longitud— y no el otro: si el
servidor devuelve menos de lo pedido pero el propio cuerpo declara que hay más, la guarda de
longitud no muerde y se concluye «todas descartadas» sobre una página incompleta. En una rama
que **autoriza crear** una ficha, concluir «todas» sobre una parte es el defecto entero.

La señal existía y se tiraba: `_buscar_registros` descartaba `totalItems`/`hydra:totalItems`
antes de que nadie pudiera mirarlos.

Adjudicación: `docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md` §8.
"""
from __future__ import annotations

import pytest

from core import sudespacho_relations as sr


class _Resp:
    def __init__(self, payload, status=200):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


def _http(monkeypatch, payload, status=200):
    """Dobla el transporte, no `_buscar_registros`: el defecto vive DENTRO de esa función."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test_key_abc")
    monkeypatch.setattr(sr.httpx, "get", lambda *a, **kw: _Resp(payload, status))


def _fichas(n, *, desde=1):
    return [{"id": str(i), "values": [{"property": {"name": "nif_cif"}, "value": f"X{i}"}]}
            for i in range(desde, desde + n)]


# ---------------------------------------------------------------------------
# La señal que se tiraba
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("clave", ["totalItems", "hydra:totalItems"])
def test_la_consulta_conserva_el_total_que_el_cuerpo_declara(monkeypatch, clave):
    """Las dos formas del listado según el `Accept` traen el total con nombre distinto."""
    _http(monkeypatch, {"items": _fichas(5), clave: 6})
    c = sr._buscar_registros("clientes_contrarios", "email", "a@b.c", limite=50)
    assert c.ok and len(c.registros) == 5
    assert c.total_declarado == 6


def test_sin_total_declarado_no_se_inventa_uno(monkeypatch):
    """**«No consta» no es «no hay más».** Si el cuerpo no declara total, el campo queda en
    `None` y `truncada` es False: no se afirma incompletitud sin evidencia, igual que no se
    afirma exhaustividad sin ella."""
    _http(monkeypatch, {"items": _fichas(3)})
    c = sr._buscar_registros("clientes_contrarios", "email", "a@b.c", limite=50)
    assert c.total_declarado is None
    assert c.truncada is False


@pytest.mark.parametrize("trae, total, truncada", [
    (5, 6, True),      # el cuerpo dice que hay una más de las que mandó
    (49, 51, True),
    (5, 5, False),     # completa, y cabía
    (3, 0, False),     # un total absurdo no se usa para afirmar incompletitud
])
def test_una_pagina_sabe_decir_si_esta_truncada(monkeypatch, trae, total, truncada):
    _http(monkeypatch, {"items": _fichas(trae), "totalItems": total})
    c = sr._buscar_registros("clientes_contrarios", "email", "a@b.c", limite=50)
    assert c.truncada is truncada


def test_el_total_llega_como_FLOAT_y_se_entiende(monkeypatch):
    """**Medido en vivo el 2026-09-14**, no supuesto: el CRM devuelve `"totalItems": 20834.0`,
    un float, no un entero. Una comprobación por `isinstance(x, int)` lo habría descartado y la
    guarda no habría mordido nunca — una guarda inerte con aspecto de protección."""
    _http(monkeypatch, {"items": _fichas(5), "totalItems": 6.0})
    c = sr._buscar_registros("clientes_contrarios", "email", "a@b.c", limite=50)
    assert c.total_declarado == 6
    assert c.truncada is True


def test_un_total_ilegible_no_rompe_la_consulta(monkeypatch):
    """`_buscar_registros` **nunca lanza**: ese contrato no se debilita por añadirle un campo."""
    _http(monkeypatch, {"items": _fichas(2), "totalItems": "muchas"})
    c = sr._buscar_registros("clientes_contrarios", "email", "a@b.c", limite=50)
    assert c.ok and len(c.registros) == 2
    assert c.total_declarado is None


# ---------------------------------------------------------------------------
# Y la decisión que la consume
# ---------------------------------------------------------------------------


def test_un_buzon_truncado_no_autoriza_crear(monkeypatch):
    """El caso del informe: NIF sin coincidencia y un email que devuelve cinco fichas con NIF
    distinto **declarando que hay seis**. Antes se concluía «todas descartadas → crear» sin
    haber visto la sexta, que podría ser la parte y debería bloquear el alta."""
    llamadas = []

    def fake(elemento, propiedad, valor, *, operador="equal", limite=5, properties=()):
        llamadas.append(propiedad)
        if propiedad == "email":
            return sr.Consulta(registros=_fichas(5), total_declarado=6)
        return sr.Consulta(registros=[])

    monkeypatch.setattr(sr, "_buscar_registros", fake)
    r = sr.resolver_parte("clientes_contrarios", nif="9.999.999-R", email="a@b.c")
    assert not r.resuelta
    assert "truncada" in r.motivo or "no se puede afirmar" in r.motivo
    assert "email" in llamadas


def test_un_buzon_completo_y_pequeno_sigue_resolviendo(monkeypatch):
    """La guarda nueva no puede bloquear lo que antes resolvía bien: si el cuerpo declara que
    las que mandó son todas, la conclusión «todas descartadas» sí está acreditada."""
    def fake(elemento, propiedad, valor, *, operador="equal", limite=5, properties=()):
        if propiedad == "email":
            return sr.Consulta(registros=_fichas(2), total_declarado=2)
        return sr.Consulta(registros=[])

    monkeypatch.setattr(sr, "_buscar_registros", fake)
    r = sr.resolver_parte("clientes_contrarios", nif="9.999.999-R", email="a@b.c")
    assert r.resuelta, r.motivo
