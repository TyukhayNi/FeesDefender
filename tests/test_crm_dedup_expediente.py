"""Comprobacion de expediente duplicado antes del alta, en las DOS jurisdicciones.

Encargo de Nikolai (2026-09-04). Tres criterios y **no valen lo mismo**:

- **W-code (id GO): BLOQUEA.** Identifica la operacion de E&V; repetirlo es casi
  siempre un error.
- **Direccion y contrario: AVISAN.** Dan falsos positivos legitimos — una vuelta y una
  bad debt del mismo inmueble son dos expedientes distintos y correctos, y el mismo
  propietario aparece en varias operaciones.

Asimetria del CRM medida el 2026-09-04, y es la trampa del modulo: la referencia se
llama **`Referencia_Cliente`** en `extrajudiciales` y **`referencia_cliente`** en
`expedientes_judiciales`. Pedir la mayuscula al judicial da HTTP 500.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.sudespacho_relations import (
    _PROP_REFERENCIA,
    Consulta,
    buscar_expedientes_duplicados,
)


def _reg(rid: str, ref: str, prop: str = "Referencia_Cliente") -> dict:
    """Registro con la forma REAL del CRM: `id` + `values`.

    Los dobles de la primera version devolvian `{"id": ...}` a secas, y por eso no
    ejercian la confirmacion exacta del W-code (R1/H-06 y H-10): cualquier resultado
    del `like` se elevaba a bloqueo y el test pasaba igual.
    """
    return {"id": rid, "values": [{"property": {"name": prop}, "value": ref}]}


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "k-de-prueba")


def _sin_nada(*a, **k):
    return Consulta()


class TestLosCriteriosNoValenLoMismo:

    def test_el_wcode_BLOQUEA(self):
        def _busca(elemento, propiedad, valor, **kw):
            if elemento == "extrajudiciales" and "W-02Q38C" in valor:
                return Consulta(registros=[
                    _reg("634", "BaRS11 - Xabec 8 (W-02Q38C) - Negativa")])
            return Consulta()
        with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca):
            d = buscar_expedientes_duplicados(w_code="W-02Q38C", direccion="Xabec 8")
        assert d.bloquea is True
        assert d.por_wcode == [("extrajudiciales", "634")]

    def test_la_direccion_solo_AVISA(self):
        """Dos expedientes en la misma calle son legitimos: vuelta y bad debt."""
        def _busca(elemento, propiedad, valor, **kw):
            if elemento == "extrajudiciales" and "Xabec" in valor:
                return Consulta(registros=[_reg("700", "Otro (W-OTRO1) - Vuelta")])
            return Consulta()
        with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca):
            d = buscar_expedientes_duplicados(w_code="W-NUEVO", direccion="Xabec 8")
        assert d.bloquea is False
        assert d.por_direccion and d.avisos

    def test_el_contrario_solo_AVISA(self):
        """El mismo propietario aparece en varias operaciones. No es duplicado."""
        with patch("core.sudespacho_relations._buscar_registros", side_effect=_sin_nada), \
             patch("core.sudespacho_relations.get_relaciones",
                   return_value={"extrajudiciales": [{"id": "634"}]}):
            d = buscar_expedientes_duplicados(
                w_code="W-NUEVO", direccion="Otra 1", contrario_id="1108")
        assert d.bloquea is False
        assert d.por_contrario == [("extrajudiciales", "634")]

    def test_sin_coincidencias_no_bloquea_ni_avisa(self):
        with patch("core.sudespacho_relations._buscar_registros", side_effect=_sin_nada):
            d = buscar_expedientes_duplicados(w_code="W-NUEVO", direccion="Otra 1")
        assert d.bloquea is False and not d.avisos


class TestLasDosJurisdicciones:

    def test_busca_en_extrajudicial_Y_en_judicial(self):
        vistos = []

        def _busca(elemento, propiedad, valor, **kw):
            vistos.append((elemento, propiedad))
            return Consulta()
        with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca):
            buscar_expedientes_duplicados(w_code="W-X", direccion="Y")

        assert ("extrajudiciales", "Referencia_Cliente") in vistos
        assert ("expedientes_judiciales", "referencia_cliente") in vistos

    def test_el_nombre_de_la_propiedad_NO_es_el_mismo(self):
        """Si alguien unifica los dos nombres, el judicial devuelve HTTP 500."""
        assert _PROP_REFERENCIA["extrajudiciales"] == "Referencia_Cliente"
        assert _PROP_REFERENCIA["expedientes_judiciales"] == "referencia_cliente"

    def test_un_wcode_en_JUDICIAL_tambien_bloquea(self):
        def _busca(elemento, propiedad, valor, **kw):
            if elemento == "expedientes_judiciales" and "W-02Q38C" in valor:
                return Consulta(registros=[
                    _reg("700", "MaRS2 (W-02Q38C) - Ordinario", "referencia_cliente")])
            return Consulta()
        with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca):
            d = buscar_expedientes_duplicados(w_code="W-02Q38C", direccion="Z")
        assert d.bloquea is True
        assert d.por_wcode == [("expedientes_judiciales", "700")]


class TestElOperadorYLosDatosQueFaltan:

    def test_usa_like_y_no_contains(self):
        """`contains` no existe en este CRM: el 404 enumera los operadores validos."""
        ops = []

        def _busca(elemento, propiedad, valor, *, operador="equal", **kw):
            ops.append(operador)
            return Consulta()
        with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca):
            buscar_expedientes_duplicados(w_code="W-X", direccion="Y")
        assert ops and set(ops) == {"like"}

    def test_sin_direccion_no_busca_por_direccion(self):
        """Una direccion vacia buscaria `like %%` y traeria el catalogo entero."""
        valores = []

        def _busca(elemento, propiedad, valor, **kw):
            valores.append(valor)
            return Consulta()
        with patch("core.sudespacho_relations._buscar_registros", side_effect=_busca):
            buscar_expedientes_duplicados(w_code="W-X", direccion="")
        assert all("W-X" in v for v in valores), valores

    def test_la_lectura_del_contrario_caida_no_tumba_la_comprobacion(self):
        """Un aviso que no se puede calcular es un aviso ausente, no un fallo."""
        with patch("core.sudespacho_relations._buscar_registros", side_effect=_sin_nada), \
             patch("core.sudespacho_relations.get_relaciones",
                   side_effect=RuntimeError("500")):
            d = buscar_expedientes_duplicados(
                w_code="W-X", direccion="Y", contrario_id="1108")
        assert d.bloquea is False
        assert d.por_contrario == []
        assert any("contrario" in s.lower() for s in d.sin_comprobar)


# ---------------------------------------------------------------------------
# El cableado: sin llamador, la comprobacion no protege nada
# ---------------------------------------------------------------------------

class TestElAltaLoUSA:
    """Una pieza construida que nadie encadena no defiende ningun caso real."""

    @staticmethod
    def _ident():
        from core import abrir_caso as brain
        return brain.Identidad(
            codigo="BaRS11", direccion="Xabec 8", w_code="W-02Q38C", sufijo="Vuelta",
            case_id="BaRS11 - Xabec 8 (W-02Q38C) - Vuelta", posicion="actora",
            tipo_caso="VUELTA", w_code_duplicado=False, codigo_duplicado=False,
            requiere_confirmacion=False, colisiones=(),
        )

    def test_un_wcode_ya_en_el_CRM_ABORTA_el_alta(self, monkeypatch, capsys):
        import scripts.abrir_caso as cli
        from core.sudespacho_relations import DuplicadosExpediente

        monkeypatch.setattr(cli.case_manager, "get_case_status",
                            lambda cid: {"expedientes": []})
        monkeypatch.setattr(cli.sudespacho_relations, "buscar_expedientes_duplicados",
                            lambda **k: DuplicadosExpediente(
                                por_wcode=[("extrajudiciales", "634")]))
        crear = _Espia()
        monkeypatch.setattr(cli.sudespacho_create, "create_expediente", crear)

        # NO `typer.Exit`: `_alta_crm` corre bajo el mutex y terminar el proceso ahi
        # rompe la propiedad de MEJORAS #142. Se aborta y decide el entrypoint.
        with pytest.raises(cli.AbortarApertura) as exc:
            cli._alta_crm(self._ident(), cuantia=1.0, crm_mode="api", yes=True)
        assert exc.value.codigo == 1
        assert crear.llamadas == 0, "se dio de alta pese al duplicado"
        assert "W-02Q38C" in capsys.readouterr().err

    def test_un_aviso_NO_aborta(self, monkeypatch, capsys):
        """Direccion y contrario avisan. Si abortaran, `--force` seria rutina."""
        import scripts.abrir_caso as cli
        from core.sudespacho_relations import DuplicadosExpediente

        monkeypatch.setattr(cli.case_manager, "get_case_status",
                            lambda cid: {"expedientes": []})
        monkeypatch.setattr(cli.sudespacho_relations, "buscar_expedientes_duplicados",
                            lambda **k: DuplicadosExpediente(
                                por_direccion=[("extrajudiciales", "700")]))
        crear = _Espia(devuelve="801")
        monkeypatch.setattr(cli.sudespacho_create, "create_expediente", crear)
        monkeypatch.setattr(cli.case_manager, "register_expediente", lambda *a, **k: None)

        cli._alta_crm(self._ident(), cuantia=1.0, crm_mode="api", yes=True)
        assert crear.llamadas == 1
        assert "AVISO" in capsys.readouterr().out

    def test_lo_que_no_se_pudo_comprobar_ABORTA_el_alta(self, monkeypatch, capsys):
        """Politica de Nikolai (2026-09-04): fallar CERRADO.

        R1/H-02: antes esto seguia adelante con un aviso y creaba el expediente. La
        proteccion desaparecia justo cuando algo habia fallado.
        """
        import scripts.abrir_caso as cli
        from core.sudespacho_relations import DuplicadosExpediente

        monkeypatch.setattr(cli.case_manager, "get_case_status",
                            lambda cid: {"expedientes": []})
        monkeypatch.setattr(cli.sudespacho_relations, "buscar_expedientes_duplicados",
                            lambda **k: DuplicadosExpediente(
                                sin_comprobar=["W-code en extrajudiciales (HTTP 500)"]))
        crear = _Espia(devuelve="801")
        monkeypatch.setattr(cli.sudespacho_create, "create_expediente", crear)
        monkeypatch.setattr(cli.case_manager, "register_expediente", lambda *a, **k: None)

        with pytest.raises(cli.AbortarApertura) as exc:
            cli._alta_crm(self._ident(), cuantia=1.0, crm_mode="api", yes=True)
        assert exc.value.codigo == 1
        assert crear.llamadas == 0, "se dio de alta sin poder comprobar el duplicado"
        assert "HTTP 500" in capsys.readouterr().err

    def test_con_force_se_da_de_alta_declarando_lo_no_comprobado(self, monkeypatch, capsys):
        """`--force` es la salida explicita, y deja constancia de lo que no se miro."""
        import scripts.abrir_caso as cli
        from core.sudespacho_relations import DuplicadosExpediente

        monkeypatch.setattr(cli.case_manager, "get_case_status",
                            lambda cid: {"expedientes": []})
        monkeypatch.setattr(cli.sudespacho_relations, "buscar_expedientes_duplicados",
                            lambda **k: DuplicadosExpediente(
                                sin_comprobar=["W-code en extrajudiciales (HTTP 500)"]))
        crear = _Espia(devuelve="801")
        monkeypatch.setattr(cli.sudespacho_create, "create_expediente", crear)
        monkeypatch.setattr(cli.case_manager, "register_expediente", lambda *a, **k: None)

        cli._alta_crm(self._ident(), cuantia=1.0, crm_mode="api", yes=True, force=True)
        salida = capsys.readouterr().out
        assert crear.llamadas == 1
        assert "--force" in salida and "HTTP 500" in salida


class _Espia:
    def __init__(self, devuelve="900"):
        self.llamadas = 0
        self._d = devuelve

    def __call__(self, *a, **k):
        self.llamadas += 1
        return self._d
