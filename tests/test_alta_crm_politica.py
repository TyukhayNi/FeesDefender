"""La politica de duplicados del CRM es UNA y vive en el core.

Diseno: `docs/superpowers/specs/2026-09-05-alta-ui-politica-compartida-design.md` §3.1 y §5.

La CLI (`scripts/abrir_caso.py::_alta_crm`) y el formulario «Nuevo caso» de
`streamlit_app.py` consumen `decidir`; ninguno la reimplementa. Los mutantes P1-P7 son
los del §5 del diseno; P8 son los tests de `test_crm_dedup_expediente.py`, que siguen
verdes sin tocarlos. Ninguna llamada de red: `DuplicadosExpediente` se construye a mano.
"""

from __future__ import annotations

import pytest

from core import alta_crm_politica as politica
from core.sudespacho_relations import DuplicadosExpediente


EXTRA = "extrajudiciales"
JUD = "expedientes_judiciales"


class TestLasReglasEnOrden:

    def test_P1_un_wcode_en_el_crm_VINCULA(self):
        d = politica.decidir(DuplicadosExpediente(por_wcode=[(EXTRA, "648")]), forzar=False)
        assert d.accion == politica.VINCULAR
        assert d.candidatos == ((EXTRA, "648"),)
        assert "648" in d.motivo

    def test_P2_dos_frentes_VINCULA_con_los_dos_en_orden_y_nunca_crea(self):
        dup = DuplicadosExpediente(por_wcode=[(JUD, "700"), (EXTRA, "648")])
        for forzar in (False, True):
            d = politica.decidir(dup, forzar=forzar)
            assert d.accion == politica.VINCULAR
            assert d.candidatos == ((JUD, "700"), (EXTRA, "648"))

    def test_P3_lo_no_comprobado_sin_forzar_BLOQUEA_con_la_lista_literal(self):
        notas = ["W-code en extrajudiciales (HTTP 500)", "direccion en expedientes_judiciales (red)"]
        d = politica.decidir(DuplicadosExpediente(sin_comprobar=list(notas)), forzar=False)
        assert d.accion == politica.BLOQUEAR
        assert d.sin_comprobar == tuple(notas)
        assert d.candidatos == ()

    def test_P4_lo_no_comprobado_forzado_CREA_y_lo_deja_escrito(self):
        notas = ["W-code en extrajudiciales (HTTP 500)", "direccion en expedientes_judiciales (red)"]
        d = politica.decidir(DuplicadosExpediente(sin_comprobar=list(notas)), forzar=True)
        assert d.accion == politica.CREAR
        for nota in notas:
            assert any(a.startswith(politica.SIN_COMPROBAR) and nota in a for a in d.avisos), d.avisos
        # Lo que no se miro sigue constando como tal, no se disuelve en el aviso.
        assert d.sin_comprobar == tuple(notas)

    def test_P5_wcode_e_incierto_a_la_vez_VINCULA(self):
        """§3.1.1: si el W-code ya esta, crear otro es el dano; la incertidumbre no manda."""
        dup = DuplicadosExpediente(
            por_wcode=[(EXTRA, "648")],
            sin_comprobar=["W-code en expedientes_judiciales (HTTP 500)"])
        for forzar in (False, True):
            d = politica.decidir(dup, forzar=forzar)
            assert d.accion == politica.VINCULAR
            assert d.candidatos == ((EXTRA, "648"),)
            # Y lo no comprobado se sigue diciendo.
            assert d.sin_comprobar == ("W-code en expedientes_judiciales (HTTP 500)",)

    def test_P6_solo_direccion_CREA_con_aviso(self):
        d = politica.decidir(DuplicadosExpediente(por_direccion=[(EXTRA, "700")]), forzar=False)
        assert d.accion == politica.CREAR
        assert any("mismo direccion" in a and "700" in a for a in d.avisos), d.avisos
        assert not any(a.startswith(politica.SIN_COMPROBAR) for a in d.avisos)

    def test_P7_vacio_CREA_sin_avisos(self):
        d = politica.decidir(DuplicadosExpediente(), forzar=False)
        assert d.accion == politica.CREAR
        assert d.avisos == ()
        assert d.sin_comprobar == ()
        assert d.candidatos == ()

    def test_la_decision_es_inmutable(self):
        d = politica.decidir(DuplicadosExpediente(), forzar=False)
        with pytest.raises(Exception):
            d.accion = politica.VINCULAR  # type: ignore[misc]


class TestReutilizarElExpedienteLocal:
    """§3.2.2: si el caso local ya tiene expediente, el formulario no crea otro."""

    def test_prefiere_el_elemento_pedido(self):
        exps = [{"id": "700", "element": "judiciales"}, {"id": "648", "element": EXTRA}]
        e = politica.expediente_local_para_alta(exps, EXTRA)
        assert e is not None and e["id"] == "648"

    def test_casa_el_alias_del_frontmatter(self):
        """El formulario registra `judiciales`; el CRM lo llama `expedientes_judiciales`."""
        exps = [{"id": "700", "element": "judiciales"}]
        e = politica.expediente_local_para_alta(exps, JUD)
        assert e is not None and e["id"] == "700"

    def test_si_no_hay_del_elemento_pedido_devuelve_el_que_haya(self):
        """Un W-code con expediente judicial no recibe otro extrajudicial desde el
        formulario: se reutiliza el que hay y se dice de que jurisdiccion es."""
        exps = [{"id": "700", "element": JUD}]
        e = politica.expediente_local_para_alta(exps, EXTRA)
        assert e is not None and e["id"] == "700"

    def test_ignora_entradas_sin_id_o_sin_elemento_reconocible(self):
        exps = [{"element": EXTRA}, {"id": "1", "element": "colaboradores"}, "basura", None]
        assert politica.expediente_local_para_alta(exps, EXTRA) is None

    def test_vacio_es_none(self):
        assert politica.expediente_local_para_alta([], EXTRA) is None


class TestElementoCanonico:

    @pytest.mark.parametrize("alias,canon", [
        ("judiciales", JUD), (JUD, JUD), (EXTRA, EXTRA), ("expedientes_extrajudiciales", EXTRA),
    ])
    def test_traduce_los_alias_del_frontmatter(self, alias, canon):
        assert politica.elemento_canonico(alias) == canon

    def test_lo_desconocido_es_none(self):
        assert politica.elemento_canonico("colaboradores") is None
        assert politica.elemento_canonico("") is None
        assert politica.elemento_canonico(None) is None


class TestLaCLILaConsume:
    """Una politica en el core que la CLI no llame protege solo al formulario."""

    @staticmethod
    def _ident():
        from core import abrir_caso as brain
        return brain.Identidad(
            codigo="BaRS11", direccion="Xabec 8", w_code="W-02Q38C", sufijo="Vuelta",
            case_id="BaRS11 - Xabec 8 (W-02Q38C) - Vuelta", posicion="actora",
            tipo_caso="VUELTA", w_code_duplicado=False, codigo_duplicado=False,
            requiere_confirmacion=False, colisiones=(),
        )

    def test_alta_crm_obedece_a_decidir_y_no_a_su_propia_lectura(self, monkeypatch):
        """Con un `dup` LIMPIO, si `decidir` dice bloquear, la CLI aborta: la regla
        vive en `decidir`, no en `_alta_crm`."""
        import scripts.abrir_caso as cli

        monkeypatch.setattr(cli.case_manager, "get_case_status",
                            lambda cid: {"expedientes": []})
        monkeypatch.setattr(cli.sudespacho_relations, "buscar_expedientes_duplicados",
                            lambda **k: DuplicadosExpediente())
        vistas = []

        def _decidir(dup, *, forzar):
            vistas.append(forzar)
            return politica.DecisionAltaCRM(
                accion=politica.BLOQUEAR, sin_comprobar=("inyectado",), motivo="prueba")
        monkeypatch.setattr(cli.alta_crm_politica, "decidir", _decidir)
        llamadas = []
        monkeypatch.setattr(cli.sudespacho_create, "create_expediente",
                            lambda *a, **k: llamadas.append(1) or "1")

        with pytest.raises(cli.AbortarApertura):
            cli._alta_crm(self._ident(), cuantia=1.0, crm_mode="api", yes=True, force=True)
        assert vistas == [True], "`--force` tiene que llegar a `decidir` como `forzar`"
        assert llamadas == []
