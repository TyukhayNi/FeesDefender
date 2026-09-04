"""Dedup de partes del CRM por NIF **o** email, en judicial y extrajudicial.

Los tres elementos de parte —`clientes_contrarios`, `colaboradores`,
`clientes_propios`— son los MISMOS en las dos jurisdicciones: solo cambia el
expediente padre (verificado el 2026-09-04 sobre las llamadas a `relation_element`).
Por eso la resolucion de identidad no depende del tipo de caso.

**Decision de Nikolai (2026-09-04), y es la que gobierna el diseno:** si el NIF y el
email apuntan a fichas DISTINTAS, la corrida **para y pregunta**. No fusiona dos
personas en silencio, no crea una tercera, y no elige por su cuenta. El NIF manda como
identidad legal cuando no hay conflicto.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.sudespacho_relations import (
    ConflictoDeIdentidad,
    Consulta,
    NuevoClienteContrario,
    NuevoColaborador,
    resolver_parte,
    ensure_contrario_vinculado,
    ensure_contrario_vinculado_judicial,
)


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "k-de-prueba")


def _busca(por_nif=None, por_email=None):
    """Sustituye la busqueda por propiedad: devuelve el id segun el criterio.

    Devuelve `Consulta`, no una lista: desde R1/H-01 el contrato distingue «no hay»
    de «no pude mirar», y un doble que devuelva `[]` a secas no reproduce ninguno de
    los dos estados que importan. Los casos de consulta CAIDA viven en
    `test_crm_dedup_incertidumbre.py`.
    """
    def _f(elemento, propiedad, valor, **kw):
        if propiedad in ("nif_cif", "nif"):
            return Consulta(registros=[{"id": por_nif}] if por_nif else [])
        if propiedad == "email":
            return Consulta(registros=[{"id": por_email}] if por_email else [])
        return Consulta()
    return _f


# ---------------------------------------------------------------------------
# resolver_parte: el NIF manda, el email es respaldo, el conflicto PARA
# ---------------------------------------------------------------------------

class TestResolverParte:

    def test_el_nif_manda_cuando_los_dos_coinciden(self):
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=_busca(por_nif="1108", por_email="1108")):
            r = resolver_parte("clientes_contrarios", nif="12345678Z", email="a@b.com")
        assert (r.id, r.por, r.conflicto) == ("1108", "nif", None)

    def test_el_email_resuelve_cuando_no_hay_ficha_por_nif(self):
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=_busca(por_nif=None, por_email="777")):
            r = resolver_parte("colaboradores", nif="", email="ana@ev.com")
        assert (r.id, r.por) == ("777", "email")

    def test_ninguno_resuelve_es_None_no_error(self):
        """Una parte nueva no es un conflicto: es una parte nueva."""
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=_busca()):
            r = resolver_parte("clientes_contrarios", nif="X", email="x@y.com")
        assert r.id is None and r.por is None and r.conflicto is None

    def test_fichas_DISTINTAS_es_conflicto_y_NO_elige(self):
        """La decision de Nikolai: parar. Ni fusiona, ni crea una tercera."""
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=_busca(por_nif="1108", por_email="999")):
            r = resolver_parte("clientes_contrarios", nif="12345678Z", email="a@b.com")
        assert r.conflicto == ("1108", "999")
        assert r.id is None, "con conflicto NO se resuelve una identidad"

    def test_sin_datos_para_buscar_no_llama_al_CRM(self):
        """Sin NIF ni email no hay nada que deduplicar; no se gasta una peticion."""
        espia = MagicMock(return_value=Consulta())
        with patch("core.sudespacho_relations._buscar_registros", espia):
            r = resolver_parte("clientes_contrarios", nif="  ", email="")
        assert r.id is None
        espia.assert_not_called()


# ---------------------------------------------------------------------------
# El conflicto llega ARRIBA: `ensure_*` levanta en vez de escribir
# ---------------------------------------------------------------------------

class TestElConflictoDetieneLaEscritura:
    """Un conflicto que solo se imprime no para nada: tiene que levantar."""

    def _datos(self):
        return NuevoClienteContrario(nombre="ALBERTO", apellido1="C",
                                     nif="12345678Z", email="a@b.com")

    def test_extrajudicial_levanta_y_no_crea_ni_vincula(self):
        crear = MagicMock()
        vincular = MagicMock()
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=_busca(por_nif="1108", por_email="999")), \
             patch("core.sudespacho_relations.create_cliente_contrario", crear), \
             patch("core.sudespacho_relations.link_contrario", vincular):
            with pytest.raises(ConflictoDeIdentidad) as exc:
                ensure_contrario_vinculado("634", self._datos())

        assert "1108" in str(exc.value) and "999" in str(exc.value)
        crear.assert_not_called()
        vincular.assert_not_called()

    def test_judicial_hace_lo_MISMO(self):
        """`ensure_contrario_vinculado_judicial` no existia: en judicial no habia dedup."""
        crear = MagicMock()
        vincular = MagicMock()
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=_busca(por_nif="1108", por_email="999")), \
             patch("core.sudespacho_relations.create_cliente_contrario", crear), \
             patch("core.sudespacho_relations.link_contrario_judicial", vincular):
            with pytest.raises(ConflictoDeIdentidad):
                ensure_contrario_vinculado_judicial("700", self._datos())

        crear.assert_not_called()
        vincular.assert_not_called()


class TestJudicialYExtrajudicialResuelvenIGUAL:
    """Mismo elemento de parte, misma identidad: solo cambia el expediente padre."""

    def test_el_contrario_existente_se_reutiliza_en_judicial(self):
        vincular = MagicMock()
        crear = MagicMock()
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=_busca(por_nif="1108")), \
             patch("core.sudespacho_relations.create_cliente_contrario", crear), \
             patch("core.sudespacho_relations.link_contrario_judicial", vincular):
            cid, creado = ensure_contrario_vinculado_judicial(
                "700", NuevoClienteContrario(nombre="A", nif="12345678Z"))

        assert (cid, creado) == ("1108", False)
        crear.assert_not_called()
        vincular.assert_called_once_with("700", "1108", client=None)

    def test_el_email_tambien_deduplica_al_contrario(self):
        """Antes el contrario solo deduplicaba por NIF: sin NIF, ficha duplicada."""
        crear = MagicMock()
        with patch("core.sudespacho_relations._buscar_registros",
                   side_effect=_busca(por_email="1108")), \
             patch("core.sudespacho_relations.create_cliente_contrario", crear), \
             patch("core.sudespacho_relations.link_contrario", MagicMock()):
            cid, creado = ensure_contrario_vinculado(
                "634", NuevoClienteContrario(nombre="A", nif="", email="a@b.com"))

        assert (cid, creado) == ("1108", False)
        crear.assert_not_called()
