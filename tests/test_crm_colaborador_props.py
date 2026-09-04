"""El contrato de `colaboradores` en el CRM, y la ficha que ya existe se COMPLETA.

El contrato no se supone: se le pidió al CRM el 2026-09-04 con una property inventada,
y su HTTP 500 lo enumera (método del §14.6 de INTEGRACION_SUDESPACHO.md):

    ccc, cp, direccion, email, fax, iva, movil, nacionalidad, nif_cif, nombre,
    notas, poblacion, provincia, telefono1, telefono2, telefono3, tipo, web

O sea: la property del NIF es `nif_cif`, igual que en el contrario. No `nif`.
"""
from unittest.mock import MagicMock, patch

import pytest


class FugaDeRedEnTest(BaseException):
    """No hereda de Exception a proposito: ningun `except Exception` puede tragarsela.

    `_completar_colaborador_existente` no lanza por diseno (perder el vinculo por no
    poder escribir un telefono seria peor que quedarse sin el telefono), asi que un
    AssertionError se lo tragaria su propio `except Exception` y la guarda quedaria
    INERTE mientras la escritura sale al tenant real.
    """


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    def _prohibido(metodo):
        def _f(*a, **k):
            destino = a[0] if a else k.get("url", "?")
            raise FugaDeRedEnTest(
                f"httpx.{metodo} salio a la red en un test ({destino!r}); "
                "mockea la funcion de core que la usa"
            )
        return _f

    for metodo in ("get", "post", "put", "delete", "patch", "request"):
        monkeypatch.setattr(f"httpx.{metodo}", _prohibido(metodo))


def test_la_guarda_de_red_no_es_atrapable_por_except_Exception():
    """Si esto falla, la guarda de este fichero es decorativa."""
    assert issubclass(FugaDeRedEnTest, BaseException)
    assert not issubclass(FugaDeRedEnTest, Exception)


class TestElContratoDeColaboradores:

    def test_el_NIF_del_colaborador_se_busca_por_nif_cif(self):
        """`nif` no existe en colaboradores: el CRM devuelve 500 y enumera el contrato."""
        from core.sudespacho_relations import _PROP_NIF
        assert _PROP_NIF["colaboradores"] == "nif_cif"

    def test_resolver_parte_consulta_la_property_nif_cif(self):
        """La frontera de verdad: que la property viaje a la consulta, no que el dict lo diga."""
        from core.sudespacho_relations import Consulta, resolver_parte
        buscar = MagicMock(return_value=Consulta(registros=[]))
        with patch("core.sudespacho_relations._buscar_registros", buscar):
            resolver_parte("colaboradores", nif="12345678Z", email="")

        # _buscar_registros(elemento, propiedad, valor, *, ...) — posicional real
        # (core/sudespacho_relations.py:~955): "propiedad" es el 2º positional
        # (índice 1), no el 3º. Ajustado tras verificar la firma real, por indicación
        # del brief (la aserción de abajo es la frontera de verdad, no esta extracción).
        propiedades = [c.kwargs.get("propiedad", (c.args + (None, None))[1])
                       for c in buscar.call_args_list]
        assert "nif_cif" in propiedades, f"consultó {propiedades!r}"
        assert "nif" not in propiedades


class TestLeerLaFichaDelColaborador:

    def test_pide_las_properties_explicitamente(self, monkeypatch):
        """El GET plano da HTTP 500: `?properties=` es obligatorio ([APER-26])."""
        from core import sudespacho_relations as sr

        capturado = {}

        class _R:
            status_code = 200

            @staticmethod
            def json():
                return {"values": [{"property": {"name": "movil"}, "value": "612345678"}]}

        def _get(url, **kw):
            capturado["url"] = url
            return _R()

        monkeypatch.setenv("SUDESPACHO_API_KEY", "k")
        monkeypatch.setattr(sr.httpx, "get", _get)
        plano = sr.get_colaborador("466")

        assert "/api/element_register/colaboradores/466" in capturado["url"]
        assert "properties=" in capturado["url"]
        assert plano == {"movil": "612345678"}

    def test_pide_TODO_el_conjunto_escribible_no_solo_lo_que_cambia(self, monkeypatch):
        """GET completo -> merge -> PUT completo: correcto si el PUT es parcial Y si es
        de reemplazo. Para `colaboradores` no esta medido cual de los dos es."""
        from core import sudespacho_relations as sr

        capturado = {}

        class _R:
            status_code = 200

            @staticmethod
            def json():
                return {"values": []}

        monkeypatch.setenv("SUDESPACHO_API_KEY", "k")
        monkeypatch.setattr(sr.httpx, "get",
                            lambda url, **kw: capturado.update(url=url) or _R())
        sr.get_colaborador("466")

        for prop in ("nombre", "email", "movil", "telefono1", "nif_cif"):
            assert prop in capturado["url"], f"falta {prop} en el GET"

    def test_una_property_que_el_CRM_no_tiene_NO_se_pide(self):
        """El contrato lo enumero el CRM. `nif` no esta, y pedirla da 500."""
        from core.sudespacho_relations import _PROPS_COLABORADOR
        assert "nif" not in _PROPS_COLABORADOR
        assert "nif_cif" in _PROPS_COLABORADOR
        assert "cargo" not in _PROPS_COLABORADOR, "no existe: `tipo` es un Select cerrado"

    def test_un_HTTP_no_200_levanta(self, monkeypatch):
        from core import sudespacho_relations as sr

        class _R:
            status_code = 500
            text = "boom"

        monkeypatch.setenv("SUDESPACHO_API_KEY", "k")
        monkeypatch.setattr(sr.httpx, "get", lambda *a, **k: _R())
        with pytest.raises(sr.SudespachoRelationsError, match="500"):
            sr.get_colaborador("466")


class TestEscribirLaFichaDelColaborador:

    def test_es_PUT_al_endpoint_del_registro(self, monkeypatch):
        from core import sudespacho_relations as sr

        capturado = {}

        class _R:
            status_code = 200

            @staticmethod
            def json():
                return {"values": [{"property": {"name": "movil"}, "value": "612345678"}]}

        def _put(url, **kw):
            capturado.update(url=url, json=kw.get("json"))
            return _R()

        monkeypatch.setenv("SUDESPACHO_API_KEY", "k")
        monkeypatch.setattr(sr.httpx, "put", _put)
        sr.update_colaborador("466", {"movil": "612345678"})

        assert capturado["url"].endswith("/api/element_register/colaboradores/466")
        assert capturado["json"] == {"movil": "612345678"}

    def test_cambios_vacio_es_un_error_del_llamador(self):
        from core import sudespacho_relations as sr
        with pytest.raises(ValueError, match="cambios"):
            sr.update_colaborador("466", {})
