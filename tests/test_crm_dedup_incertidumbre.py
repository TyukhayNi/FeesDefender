"""Lo que pasa cuando el CRM NO responde, o responde de forma ambigua.

Estas son las fronteras que R1 encontro abiertas, y todas comparten una forma: la
version revisada colapsaba **«no lo se»** en **«no hay»**, y desde ahi escribia. Un 500
durante una apertura hacia concluir «esta parte no existe» y creaba una ficha duplicada
(H-01); hacia concluir «no hay expediente con este W-code» y daba de alta otro (H-02).
La proteccion desaparecia en silencio y **justo cuando algo fallaba**.

**Politica, decidida por Nikolai el 2026-09-04: fallar CERRADO.** Si no se pudo
comprobar, no se crea ni se vincula, se dice que no se pudo mirar, y `--force` es la
unica salida — explicita.

Los dobles de aqui reproducen los estados que los tests de la primera version **no
ejercian** (R1/H-10): consulta caida, varios resultados, y cuerpo con forma rara.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.sudespacho_relations import (
    ConflictoDeIdentidad,
    Consulta,
    IdentidadSinComprobar,
    NuevoClienteContrario,
    NuevoColaborador,
    buscar_expedientes_duplicados,
    ensure_colaborador_vinculado,
    ensure_colaborador_vinculado_judicial,
    ensure_contrario_vinculado,
    resolver_parte,
)


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "k-de-prueba")


def _reg(rid: str, ref: str | None = None, prop: str = "Referencia_Cliente") -> dict:
    """Registro con la forma REAL del CRM: id + values, no solo id."""
    d: dict = {"id": rid}
    if ref is not None:
        d["values"] = [{"property": {"name": prop}, "value": ref}]
    return d


# ===========================================================================
# H-01: una consulta caida NO autoriza crear
# ===========================================================================

class TestUnaConsultaCaidaNoEsAusencia:

    def test_resolver_parte_declara_lo_que_no_pudo_mirar(self):
        caida = Consulta(ok=False, motivo="HTTP 500")
        with patch("core.sudespacho_relations._buscar_registros", return_value=caida):
            r = resolver_parte("clientes_contrarios", nif="12345678Z", email="a@b.com")

        assert r.id is None
        assert r.sin_comprobar, "un 500 tiene que constar, no colapsar en «no existe»"
        assert not r.resuelta

    def test_el_contrario_NO_se_crea_si_no_se_pudo_comprobar(self):
        """El defecto medido por R1: 500 en las dos consultas -> crear + vincular."""
        crear, vincular = MagicMock(), MagicMock()
        with patch("core.sudespacho_relations._buscar_registros",
                   return_value=Consulta(ok=False, motivo="HTTP 500")), \
             patch("core.sudespacho_relations.create_cliente_contrario", crear), \
             patch("core.sudespacho_relations.link_contrario", vincular):
            with pytest.raises(IdentidadSinComprobar) as exc:
                ensure_contrario_vinculado(
                    "634", NuevoClienteContrario(nombre="A", nif="12345678Z",
                                                 email="a@b.com"))

        assert "HTTP 500" in str(exc.value)
        crear.assert_not_called()
        vincular.assert_not_called()

    def test_el_colaborador_tampoco(self):
        crear = MagicMock()
        with patch("core.sudespacho_relations._buscar_registros",
                   return_value=Consulta(ok=False, motivo="red")), \
             patch("core.sudespacho_relations.create_colaborador", crear), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()):
            with pytest.raises(IdentidadSinComprobar):
                ensure_colaborador_vinculado(
                    "634", NuevoColaborador(nombre="ANA", email="ana@ev.com",
                                            nif="11111111H"))
        crear.assert_not_called()

    def test_sin_api_key_es_SIN_COMPROBAR_no_ausencia(self, monkeypatch):
        """Sin clave no se puede mirar. Antes eso se leia como «no existe»."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "")
        r = resolver_parte("clientes_contrarios", nif="12345678Z")
        assert r.sin_comprobar and r.id is None


# ===========================================================================
# H-04: el respaldo no puede tapar un criterio caido
# ===========================================================================

def test_el_respaldo_del_colaborador_no_corre_si_el_NIF_no_se_pudo_mirar():
    """R1/H-04: con el NIF caido, el respaldo por email vinculaba OTRA ficha."""
    def _busca(elemento, propiedad, valor, **kw):
        if propiedad in ("nif", "nif_cif"):
            return Consulta(ok=False, motivo="HTTP 500")
        return Consulta()

    respaldo = MagicMock(return_value="999")
    with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca), \
         patch("core.sudespacho_relations.find_colaborador_by_email", respaldo), \
         patch("core.sudespacho_relations.link_colaborador", MagicMock()):
        with pytest.raises(IdentidadSinComprobar):
            ensure_colaborador_vinculado(
                "634", NuevoColaborador(nombre="ANA", email="ana@x.example",
                                        nif="11111111H"))

    respaldo.assert_not_called(), "el respaldo tapo el criterio que no se pudo comprobar"


# ===========================================================================
# H-03: la identidad no puede depender del ORDEN
# ===========================================================================

class TestNadaSeDecidePorOrdenDeLlegada:

    @staticmethod
    def _con(ids_nif, ids_mail):
        def _busca(elemento, propiedad, valor, **kw):
            fuente = ids_nif if propiedad in ("nif", "nif_cif") else ids_mail
            return Consulta(registros=[{"id": i} for i in fuente])
        return _busca

    @pytest.mark.parametrize("orden", [["111", "222"], ["222", "111"]])
    def test_varios_resultados_por_un_criterio_es_AMBIGUO_en_los_dos_ordenes(self, orden):
        """Medido por R1: con [111,222] habia conflicto y con [222,111] no, para el
        MISMO estado del CRM. Ahora los dos ordenes dan el mismo veredicto."""
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=self._con(orden, ["222"])):
            r = resolver_parte("clientes_contrarios", nif="X", email="a@b.com")

        assert r.ambiguo == ("111", "222")
        assert r.id is None and r.conflicto is None

    def test_un_solo_criterio_con_dos_fichas_tampoco_elige(self):
        """Antes vinculaba `111` en silencio por venir primero."""
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=self._con(["111", "222"], [])):
            r = resolver_parte("clientes_contrarios", nif="X")
        assert r.id is None and r.ambiguo == ("111", "222")

    def test_conjuntos_que_se_SOLAPAN_resuelven_por_la_interseccion(self):
        """No es conflicto: las dos vias contienen la misma ficha."""
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=self._con(["222"], ["222"])):
            r = resolver_parte("clientes_contrarios", nif="X", email="a@b.com")
        assert (r.id, r.por, r.conflicto) == ("222", "nif", None)

    def test_conjuntos_DISJUNTOS_siguen_siendo_conflicto(self):
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=self._con(["111"], ["999"])):
            r = resolver_parte("clientes_contrarios", nif="X", email="a@b.com")
        assert r.conflicto == ("111", "999") and r.id is None


# ===========================================================================
# H-05: el colaborador JUDICIAL resuelve igual que el extrajudicial
# ===========================================================================

def test_el_colaborador_judicial_tambien_para_ante_el_conflicto():
    """R1/H-05: era email-only y ni deduplicaba por NIF ni veia el conflicto."""
    def _busca(elemento, propiedad, valor, **kw):
        ids = ["111"] if propiedad in ("nif", "nif_cif") else ["999"]
        return Consulta(registros=[{"id": i} for i in ids])

    crear, vincular = MagicMock(), MagicMock()
    with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca), \
         patch("core.sudespacho_relations.create_colaborador", crear), \
         patch("core.sudespacho_relations.link_colaborador_judicial", vincular):
        with pytest.raises(ConflictoDeIdentidad):
            ensure_colaborador_vinculado_judicial(
                "700", NuevoColaborador(nombre="ANA", email="a@b.com", nif="11111111H"),
                client=MagicMock())

    crear.assert_not_called()
    vincular.assert_not_called()


# ===========================================================================
# H-06: el W-code se confirma EXACTO, no por subcadena
# ===========================================================================

class TestElWcodeSeConfirmaExacto:

    def test_un_codigo_mas_largo_NO_bloquea(self):
        """`like` de W-12345 trae W-123456, que es otra operacion."""
        def _busca(elemento, propiedad, valor, **kw):
            if elemento != "extrajudiciales":
                return Consulta()
            return Consulta(registros=[_reg("700", "Caso distinto (W-123456) - Vuelta")])

        with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca):
            d = buscar_expedientes_duplicados(w_code="W-12345")

        assert d.bloquea is False, "bloqueo un W-code que no era el mismo"

    def test_el_codigo_EXACTO_si_bloquea(self):
        def _busca(elemento, propiedad, valor, **kw):
            if elemento != "extrajudiciales":
                return Consulta()
            return Consulta(registros=[_reg("634", "BaRS11 - Xabec 8 (W-02Q38C) - X")])

        with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca):
            d = buscar_expedientes_duplicados(w_code="W-02Q38C")

        assert d.por_wcode == [("extrajudiciales", "634")] and d.bloquea

    def test_sin_referencia_devuelta_es_SIN_COMPROBAR_no_duplicado(self):
        """No se puede confirmar el codigo: ni se bloquea ni se da por limpio."""
        def _busca(elemento, propiedad, valor, **kw):
            if elemento != "extrajudiciales":
                return Consulta()
            return Consulta(registros=[_reg("700")])   # sin `values`

        with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca):
            d = buscar_expedientes_duplicados(w_code="W-02Q38C")

        assert d.bloquea is False
        assert d.incierto and any("#700" in s for s in d.sin_comprobar)


# ===========================================================================
# H-02: la busqueda de expediente caida NO se presenta como ausencia
# ===========================================================================

def test_una_busqueda_de_expediente_caida_marca_incierto():
    with patch("core.sudespacho_relations._buscar_registros",
               return_value=Consulta(ok=False, motivo="HTTP 500")):
        d = buscar_expedientes_duplicados(w_code="W-02Q38C", direccion="Xabec 8")

    assert d.bloquea is False
    assert d.incierto, "un 500 dejaba `sin_comprobar` VACIO y el alta seguia"
    assert any("W-code" in s for s in d.sin_comprobar)


# ===========================================================================
# H-07: `_buscar_registros` nunca lanza, tampoco con JSON de forma rara
# ===========================================================================

class TestNuncaLanzaEsUnContrato:

    @pytest.mark.parametrize("cuerpo", [[], None, "texto", 42])
    def test_json_de_forma_inesperada_es_ok_False_no_excepcion(self, cuerpo):
        from core.sudespacho_relations import _buscar_registros

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = cuerpo
        with patch("httpx.get", return_value=resp):
            c = _buscar_registros("clientes_contrarios", "nif_cif", "X")

        assert c.ok is False and c.registros == []

    def test_la_red_caida_tampoco_lanza(self):
        from core.sudespacho_relations import _buscar_registros
        import httpx

        with patch("httpx.get", side_effect=httpx.ConnectError("sin red")):
            c = _buscar_registros("clientes_contrarios", "nif_cif", "X")
        assert c.ok is False and "red" in c.motivo


# ===========================================================================
# H-08: el NIF se canoniza antes de consultar
# ===========================================================================

def test_el_nif_viaja_sin_separadores():
    """Medido contra el tenant: el CRM tolera caja y espacios, NO los separadores."""
    vistos = []

    def _busca(elemento, propiedad, valor, **kw):
        vistos.append(valor)
        return Consulta()

    with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca):
        resolver_parte("clientes_contrarios", nif="12.345.678-z")

    assert vistos == ["12345678Z"]
