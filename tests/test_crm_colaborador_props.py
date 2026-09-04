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


class TestElColaboradorExistenteSeCOMPLETA:
    """Espejo del contrario (R1/H-07 del PR #275). El caso normal es que YA exista:
    el mismo consultor aparece en todos los casos de su Market Center."""

    @staticmethod
    def _datos():
        from core.sudespacho_relations import NuevoColaborador
        return NuevoColaborador(nombre="ANA", email="ana@engelvoelkers.example",
                                movil="612345678", telefono="912345678",
                                nif="12345678Z")

    def test_lo_que_falta_en_el_CRM_se_rellena(self):
        from core.sudespacho_relations import ensure_colaborador_vinculado
        actualizar = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"nombre": "ANA", "email": "", "movil": "",
                                 "telefono1": "", "nif_cif": ""}), \
             patch("core.sudespacho_relations.update_colaborador", actualizar), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            cid, creado = ensure_colaborador_vinculado("600", self._datos())

        assert (cid, creado) == ("466", False)
        cambios = actualizar.call_args.args[1]
        assert cambios["movil"] == "612345678"
        assert cambios["telefono1"] == "912345678", "el fijo va a telefono1"
        assert cambios["nif_cif"] == "12345678Z", "nif_cif, no nif"
        assert "cargo" not in cambios, "no existe esa property en el CRM"
        assert "tipo" not in cambios, "es un Select cerrado: un puesto ahi la corrompe"

    def test_lo_que_el_CRM_YA_tiene_no_se_pisa(self):
        """La ficha local aporta datos; no manda sobre lo que E&V corrigio alli."""
        from core.sudespacho_relations import ensure_colaborador_vinculado
        actualizar = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"email": "otra@engelvoelkers.example",
                                 "movil": "600000000", "telefono1": "930000000",
                                 "nif_cif": "87654321X"}), \
             patch("core.sudespacho_relations.update_colaborador", actualizar), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            ensure_colaborador_vinculado("600", self._datos())

        actualizar.assert_not_called()

    def test_rellena_SOLO_el_hueco_y_deja_el_resto(self):
        """El caso real medido en W-02Q38C: movil puesto, telefono1 vacio."""
        from core.sudespacho_relations import ensure_colaborador_vinculado
        actualizar = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"email": "ana@engelvoelkers.example",
                                 "movil": "600000000", "telefono1": "",
                                 "nif_cif": ""}), \
             patch("core.sudespacho_relations.update_colaborador", actualizar), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            ensure_colaborador_vinculado("600", self._datos())

        cambios = actualizar.call_args.args[1]
        assert set(cambios) == {"telefono1", "nif_cif"}
        assert "movil" not in cambios, "el CRM ya tenia uno distinto: no se toca"

    def test_un_valor_en_blanco_del_CRM_cuenta_como_VACIO(self):
        """Un campo con espacios es un campo vacio, no un dato que respetar. Y `None`
        tampoco: el CRM devuelve nulos en las properties sin valor."""
        from core.sudespacho_relations import ensure_colaborador_vinculado
        actualizar = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"movil": "   ", "telefono1": None}), \
             patch("core.sudespacho_relations.update_colaborador", actualizar), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            ensure_colaborador_vinculado("600", self._datos())

        cambios = actualizar.call_args.args[1]
        assert cambios["movil"] == "612345678"
        assert cambios["telefono1"] == "912345678"

    def test_si_no_se_puede_LEER_la_ficha_no_se_pierde_el_VINCULO(self):
        """Completar es un extra: perder el vinculo por un telefono seria peor."""
        from core.sudespacho_relations import ensure_colaborador_vinculado
        vincular = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   side_effect=RuntimeError("500")), \
             patch("core.sudespacho_relations.link_colaborador", vincular), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            cid, creado = ensure_colaborador_vinculado("600", self._datos())

        assert (cid, creado) == ("466", False)
        vincular.assert_called_once()

    def test_si_no_se_puede_ESCRIBIR_tampoco_se_pierde_el_VINCULO(self):
        from core.sudespacho_relations import ensure_colaborador_vinculado
        vincular = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"movil": "", "telefono1": ""}), \
             patch("core.sudespacho_relations.update_colaborador",
                   side_effect=RuntimeError("400")), \
             patch("core.sudespacho_relations.link_colaborador", vincular), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            cid, creado = ensure_colaborador_vinculado("600", self._datos())

        assert (cid, creado) == ("466", False)
        vincular.assert_called_once()

    def test_al_CREAR_uno_nuevo_no_se_completa_nada(self):
        """El POST ya lleva los campos: un PUT detras seria una peticion regalada."""
        from core.sudespacho_relations import ensure_colaborador_vinculado
        leer = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value=None), \
             patch("core.sudespacho_relations.create_colaborador", return_value="999"), \
             patch("core.sudespacho_relations.get_colaborador", leer), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            cid, creado = ensure_colaborador_vinculado("600", self._datos())

        assert (cid, creado) == ("999", True)
        leer.assert_not_called()


class TestLasDosJurisdiccionesSeCompletanIGUAL:
    """R1/H-05 midio que anadir algo al camino extrajudicial y olvidar el judicial es
    el modo de fallo recurrente de este modulo. El gancho va en el resolvedor
    COMPARTIDO, asi que esta simetria no es una coincidencia que haya que mantener."""

    @staticmethod
    def _datos():
        from core.sudespacho_relations import NuevoColaborador
        return NuevoColaborador(nombre="ANA", email="ana@engelvoelkers.example",
                                movil="612345678")

    def test_el_judicial_tambien_completa(self):
        from core.sudespacho_relations import ensure_colaborador_vinculado_judicial
        actualizar = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"movil": ""}), \
             patch("core.sudespacho_relations.update_colaborador", actualizar), \
             patch("core.sudespacho_relations.link_colaborador_judicial", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            ensure_colaborador_vinculado_judicial("700", self._datos())

        assert actualizar.call_args.args[1]["movil"] == "612345678"

    def test_las_dos_pasan_por_el_MISMO_resolvedor(self):
        """La frontera estructural: sin esto, alguien puede copiar el gancho en vez de
        compartirlo y el siguiente cambio vuelve a olvidar una de las dos ramas."""
        from core.sudespacho_relations import (ensure_colaborador_vinculado,
                                               ensure_colaborador_vinculado_judicial)
        resolver = MagicMock(return_value=("466", False))
        with patch("core.sudespacho_relations._resolver_o_crear_colaborador", resolver), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.link_colaborador_judicial", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            ensure_colaborador_vinculado("600", self._datos())
            ensure_colaborador_vinculado_judicial("700", self._datos())

        assert resolver.call_count == 2, "las dos jurisdicciones lo usan"
