"""`id_crm` vive en el core: con él no se busca ni se crea (spec rev. 3 §3 A.4, R2/H-06).

La rev. 1 del plan vinculaba por id desde la orquestación, un segundo camino de escritura que
no heredaba el completado; y aceptaba `id_crm` tres commits antes de que nadie lo consumiera, con
lo que esa parte seguía el camino de CREACIÓN. La rama va en los dos resolutores del core.
"""
from unittest.mock import MagicMock

import pytest

from core import sudespacho_relations as sr


class NoDebiaLlamarse(BaseException):
    """Fuera de `Exception`: ningún `except Exception` del código bajo prueba se la traga."""


@pytest.fixture
def sin_busqueda_ni_alta(monkeypatch):
    def _prohibido(nombre):
        def _f(*a, **k):
            raise NoDebiaLlamarse(f"{nombre} no debía llamarse con id_crm")
        return _f
    for n in ("resolver_parte", "_resolver_colaborador", "create_cliente_contrario",
              "create_colaborador"):
        monkeypatch.setattr(f"core.sudespacho_relations.{n}", _prohibido(n))


def test_con_id_crm_el_contrario_no_se_busca_ni_se_crea_y_se_completa(sin_busqueda_ni_alta,
                                                                       monkeypatch):
    completar = MagicMock()
    monkeypatch.setattr("core.sudespacho_relations._completar_contrario_existente", completar)
    datos = sr.NuevoClienteContrario(nombre="ANA", id_crm="1128")
    assert sr.resolver_contrario_existente(datos) == "1128"
    assert sr._resolver_o_crear_contrario(datos) == ("1128", False)
    completar.assert_called_once_with("1128", datos)


def test_con_id_crm_el_colaborador_tampoco(sin_busqueda_ni_alta, monkeypatch):
    completar = MagicMock()
    monkeypatch.setattr("core.sudespacho_relations._completar_colaborador_existente", completar)
    datos = sr.NuevoColaborador(nombre="ANA", id_crm="776")
    assert sr.resolver_colaborador_existente(datos) == "776"
    assert sr._resolver_o_crear_colaborador(datos) == ("776", False)
    completar.assert_called_once_with("776", datos)


def test_sin_id_crm_se_resuelve_como_siempre(monkeypatch):            # control positivo
    resolver = MagicMock(return_value=sr.ResolucionParte(id="1099", por="nif"))
    monkeypatch.setattr("core.sudespacho_relations.resolver_parte", resolver)
    assert sr.resolver_contrario_existente(
        sr.NuevoClienteContrario(nombre="JUAN", nif="00000000T")) == "1099"
    resolver.assert_called_once_with("clientes_contrarios", nif="00000000T", email="")


def test_un_dto_sin_id_crm_lo_tiene_vacio():                          # control positivo
    """El campo nuevo tiene defecto: nadie que construya los DTOs sin él cambia de conducta."""
    assert sr.NuevoClienteContrario(nombre="A").id_crm == ""
    assert sr.NuevoColaborador(nombre="A").id_crm == ""
