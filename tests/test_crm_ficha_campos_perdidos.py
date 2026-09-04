"""Tres campos del contrario que el YAML traia y el CRM nunca recibia.

Medido el 2026-09-04 sobre el `_ficha_crm.yaml` de W-02Q38C, que trae `cp` y `provincia`
escritos: `NuevoClienteContrario` no tenia esos campos y `_contrario_de` no los leia, asi
que se **descartaban en silencio** al cargar la ficha. Y `telefono1` existe en el elemento
`clientes_contrarios` del CRM sin que nada lo alimentara.

Un dato que se escribe, se guarda en el repositorio del caso y no llega a su destino es
peor que un dato ausente: parece que esta puesto.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.crm_ficha import cargar_ficha_yaml
from core.sudespacho_relations import (
    NuevoClienteContrario,
    _rest_post_cliente_contrario,
    provincia_canonica,
)


def _ficha(tmp_path, extra: str = ""):
    y = tmp_path / "_ficha_crm.yaml"
    y.write_text(
        "contrario:\n  nombre: ANA\n  apellido1: LOPEZ\n  nif: 12345678Z\n"
        "  direccion: CALLE FALSA 1\n  poblacion: BARCELONA\n"
        "  cp: '08019'\n  provincia: Barcelona\n  telefono: '931112233'\n" + extra,
        encoding="utf-8")
    return cargar_ficha_yaml(y)


class TestElYAMLYaNoPierdeCampos:

    def test_cp_provincia_y_telefono_se_LEEN(self, tmp_path):
        c = _ficha(tmp_path).contrario
        assert c.cp == "08019"
        assert c.provincia == "Barcelona"
        assert c.telefono == "931112233"

    def test_el_telefono_se_normaliza_como_el_movil(self, tmp_path):
        c = _ficha(tmp_path, "").contrario
        assert c.telefono == "931112233"
        otro = NuevoClienteContrario(nombre="X", telefono="+34 931 11 22 33")
        assert otro.telefono == "931112233"


class TestLosCamposLLEGAN:
    """Leerlos del YAML no basta: hay que comprobar que viajan en el POST."""

    @staticmethod
    def _payload(**kw):
        resp = MagicMock()
        resp.status_code = 201
        resp.json.return_value = {"id": 1}
        with patch("httpx.post", return_value=resp) as post, \
             patch.dict("os.environ", {"SUDESPACHO_API_KEY": "k"}):
            _rest_post_cliente_contrario(NuevoClienteContrario(nombre="ANA", **kw))
        return post.call_args.kwargs["json"]

    def test_cp_y_telefono_viajan_con_el_nombre_de_property_del_CRM(self):
        p = self._payload(cp="08019", telefono="931112233")
        assert p["cp"] == "08019"
        assert p["telefono1"] == "931112233", "el CRM lo llama telefono1, no telefono"

    def test_la_provincia_viaja_con_el_LITERAL_del_enum(self):
        """La convencion del despacho es MAYUSCULAS; el Select exige `Barcelona`."""
        assert self._payload(provincia="BARCELONA")["provincia"] == "Barcelona"

    def test_una_provincia_que_no_existe_NO_se_manda(self):
        """Mandarla la descartaria el Select en silencio y el campo quedaria vacio."""
        assert "provincia" not in self._payload(provincia="Barchelona")


class TestProvinciaCanonica:

    @pytest.mark.parametrize("escrito, esperado", [
        ("Barcelona", "Barcelona"),
        ("BARCELONA", "Barcelona"),
        ("barcelona", "Barcelona"),
        ("  Barcelona  ", "Barcelona"),
        ("ALAVA", "Álava"),          # el enum lleva tilde y la ficha no tiene por que
        ("a coruña", "A Coruña"),
        ("LAS PALMAS", "Las Palmas"),  # dos palabras: no puede partirse
    ])
    def test_tolera_caja_tildes_y_espacios(self, escrito, esperado):
        assert provincia_canonica(escrito) == esperado

    @pytest.mark.parametrize("no_existe", ["", "   ", "Barchelona", "Lisboa", "08019"])
    def test_lo_que_no_es_una_provincia_devuelve_None(self, no_existe):
        assert provincia_canonica(no_existe) is None

    def test_estan_las_52(self):
        from core.sudespacho_relations import _PROVINCIAS
        assert len(_PROVINCIAS) == 52
        assert len(set(_PROVINCIAS)) == 52, "hay provincias repetidas en la lista"
