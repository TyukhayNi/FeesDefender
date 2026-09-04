from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from core import case_manager
from core.casos import case_locator
from scripts import crm_ficha as cli


@pytest.fixture
def caso_con_ficha(tmp_path, monkeypatch):
    """CASOS_ROOT en tmp, un caso con expediente extrajudicial registrado y un _ficha_crm.yaml."""
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)

    case_id = "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
    case_manager.ensure_case(
        case_id, titulo=case_id, referencia_crm=case_id,
        tipo_caso="VUELTA", ciudad="Barcelona", direccion="Falsa 1", id_go="W-000AAA",
    )
    case_manager.register_expediente(case_id, "606", "extrajudiciales")

    ficha = case_locator.path_for(case_id) / "00_Input" / "_ficha_crm.yaml"
    ficha.write_text(
        "contrario:\n  nombre: JUAN\n  apellido1: PEREZ\n  nif: 00000000T\n"
        "  movil: '+34 600 111 222'\n"
        "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.example\n"
        "notas_html: '<p>Vuelta</p>'\n",
        encoding="utf-8",
    )
    return case_id


def test_crm_ficha_orquesta_todo(caso_con_ficha, monkeypatch):
    link_ev = MagicMock()
    ensure_c = MagicMock(return_value=("1099", True))
    ensure_col = MagicMock(return_value=("776", False))
    upd = MagicMock(return_value={"Numero_Expediente": "49", "Notas": "<p>Vuelta</p>"})
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado", ensure_c)
    monkeypatch.setattr("scripts.crm_ficha.ensure_colaborador_vinculado", ensure_col)
    monkeypatch.setattr("scripts.crm_ficha.update_expediente", upd)
    # GET de verificación: devuelve algo plausible
    monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                        MagicMock(return_value={"Numero_Expediente": "49"}))

    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
    assert r.exit_code == 0, r.output

    link_ev.assert_called_once_with("606", cliente_propio_id="2")
    assert ensure_c.call_args.args[0] == "606"          # exp_id
    assert ensure_c.call_args.args[1].apellido1 == "PEREZ"
    assert ensure_col.call_args.args[0] == "606"
    assert upd.call_args.args[0] == "606"
    assert upd.call_args.args[1] == {"Notas": "<p>Vuelta</p>"}


def test_crm_ficha_dry_run_no_escribe(caso_con_ficha, monkeypatch):
    link_ev = MagicMock()
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock())
    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--dry-run"])
    assert r.exit_code == 0, r.output
    link_ev.assert_not_called()


def test_crm_ficha_sin_yaml_falla(caso_con_ficha, monkeypatch):
    # Borrar el yaml
    (case_locator.path_for(caso_con_ficha) / "00_Input" / "_ficha_crm.yaml").unlink()
    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
    assert r.exit_code != 0
    assert "_ficha_crm.yaml" in r.output


def test_crm_ficha_sin_expediente_falla(tmp_path, monkeypatch):
    root = tmp_path / "CASOS"; root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_id = "BaRS11 - Falsa 2 (W-000BBB) - Vuelta"
    case_manager.ensure_case(case_id, titulo=case_id, referencia_crm=case_id,
                             tipo_caso="VUELTA", ciudad="Barcelona", direccion="Falsa 2", id_go="W-000BBB")
    (case_locator.path_for(case_id) / "00_Input" / "_ficha_crm.yaml").write_text(
        "notas_html: x\n", encoding="utf-8")
    r = CliRunner().invoke(cli.app, ["--case-id", "W-000BBB", "--yes"])
    assert r.exit_code != 0
    assert "expediente" in r.output.lower()


def test_crm_ficha_cliente_propio_engel_volkers_vincula_id_27(tmp_path, monkeypatch):
    """_ficha_crm.yaml con cliente_propio: ENGEL_VOLKERS_SPAIN debe vincular id 27, no el default (id 2)."""
    root = tmp_path / "CASOS"; root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_id = "BaRS11 - Falsa 3 (W-000CCC) - Otros"
    case_manager.ensure_case(
        case_id, titulo=case_id, referencia_crm=case_id,
        tipo_caso="OTROS", ciudad="Barcelona", direccion="Falsa 3", id_go="W-000CCC",
    )
    case_manager.register_expediente(case_id, "607", "extrajudiciales")
    ficha = case_locator.path_for(case_id) / "00_Input" / "_ficha_crm.yaml"
    ficha.write_text("cliente_propio: ENGEL_VOLKERS_SPAIN\nnotas_html: x\n", encoding="utf-8")

    link_ev = MagicMock()
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock(return_value={}))
    monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                        MagicMock(return_value={"Numero_Expediente": "1"}))

    r = CliRunner().invoke(cli.app, ["--case-id", "W-000CCC", "--yes"])
    assert r.exit_code == 0, r.output
    link_ev.assert_called_once_with("607", cliente_propio_id="27")


def test_crm_ficha_falla_limpio_si_writer_revienta_mid_run(caso_con_ficha, monkeypatch):
    """Si un writer revienta a mitad del secuenciado (tras link_ev_mmc OK), debe fallar
    limpio (spec §7.4: tolerancia a caída como _alta_crm — avisa, no revienta), no dejar
    burbujear la excepción cruda ni imprimir un traceback."""
    link_ev = MagicMock()
    ensure_c = MagicMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado", ensure_c)

    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])

    assert r.exit_code != 0
    assert r.exception is None or isinstance(r.exception, SystemExit)
    assert "Traceback" not in r.output
    link_ev.assert_called_once()
    assert "[ERROR]" in r.output
    assert "re-ejecutar" in r.output.lower() and "dedup" in r.output.lower()


def test_crm_ficha_cliente_propio_desconocido_falla_sin_escribir(tmp_path, monkeypatch):
    """Un cliente_propio no mapeado debe fallar limpio (sin traceback) y no vincular el default."""
    root = tmp_path / "CASOS"; root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_id = "BaRS11 - Falsa 4 (W-000DDD) - Otros"
    case_manager.ensure_case(
        case_id, titulo=case_id, referencia_crm=case_id,
        tipo_caso="OTROS", ciudad="Barcelona", direccion="Falsa 4", id_go="W-000DDD",
    )
    case_manager.register_expediente(case_id, "608", "extrajudiciales")
    ficha = case_locator.path_for(case_id) / "00_Input" / "_ficha_crm.yaml"
    ficha.write_text("cliente_propio: NO_EXISTE\nnotas_html: x\n", encoding="utf-8")

    link_ev = MagicMock()
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock())

    r = CliRunner().invoke(cli.app, ["--case-id", "W-000DDD", "--yes"])
    assert r.exit_code != 0
    assert "Traceback" not in r.output  # falla limpia, no una excepción sin capturar
    assert "cliente_propio desconocido" in r.output.lower()
    link_ev.assert_not_called()


# ---------------------------------------------------------------------------
# Guarda de red: `get_relaciones` sale al CRM de verdad, y la API key vive en el
# entorno de usuario de Windows — sin esto, correr la suite en el PC de Nikolai
# golpearia el tenant real. Los tests que quieran una lectura concreta la
# sobreescriben; los demas obtienen «no se pudo leer», que el CLI trata como
# SIN VERIFICAR y no como fallo.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _sin_red_en_relaciones(monkeypatch):
    def _prohibido(*a, **k):
        raise AssertionError(
            "get_relaciones salio a la red en un test; mockealo explicitamente"
        )
    monkeypatch.setattr("scripts.crm_ficha.get_relaciones", _prohibido)


# ---------------------------------------------------------------------------
# Verificacion POR RESULTADO de los vinculos (2026-09-04)
#
# Hasta hoy el CLI remataba con «verificar partes visualmente en el CRM» porque
# `INTEGRACION_SUDESPACHO.md` daba por hecho que la API no sabe leer relaciones.
# Si sabe: `GET /api/related_register/{element}/{id}`.
# ---------------------------------------------------------------------------

class TestVerificacionPorLectura:
    """El 201 no prueba el vinculo; la lectura si, y debe mandar sobre el status."""

    @staticmethod
    def _escrituras_en_verde(monkeypatch):
        monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", MagicMock())
        monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado",
                            MagicMock(return_value=("1099", False)))
        monkeypatch.setattr("scripts.crm_ficha.ensure_colaborador_vinculado",
                            MagicMock(return_value=("776", False)))
        monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock(return_value={}))
        monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                            MagicMock(return_value={"Numero_Expediente": "49"}))

    def test_todo_vinculado_dice_VERIFICADA(self, caso_con_ficha, monkeypatch):
        self._escrituras_en_verde(monkeypatch)
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [{"id": "2"}],
            "clientes_contrarios": [{"id": "1099"}],
            "colaboradores": [{"id": "776"}],
        })
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 0, r.output
        assert "VERIFICADA por lectura" in r.output
        assert "visualmente" not in r.output
        assert "[ok] clientes_contrarios id=1099" in r.output

    def test_un_vinculo_ausente_TUMBA_la_corrida(self, caso_con_ficha, monkeypatch):
        """La escritura dijo OK por su 201; la lectura dice que no esta. Manda la lectura."""
        self._escrituras_en_verde(monkeypatch)
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [{"id": "2"}],
            "clientes_contrarios": [{"id": "1099"}],
            "colaboradores": [],                      # el 776 no llego
        })
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 1, r.output
        assert "[FALTA] colaboradores id=776" in r.output
        assert "DESMIENTE" in r.output
        assert "VERIFICADA" not in r.output

    def test_el_cliente_propio_tambien_se_verifica(self, caso_con_ficha, monkeypatch):
        """Es el unico vinculo que no devuelve id: si no se comprueba, nadie lo mira."""
        self._escrituras_en_verde(monkeypatch)
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [],                   # EV MMC no quedo vinculado
            "clientes_contrarios": [{"id": "1099"}],
            "colaboradores": [{"id": "776"}],
        })
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 1, r.output
        assert "[FALTA] clientes_propios id=2" in r.output

    def test_lectura_caida_es_SIN_VERIFICAR_no_fallo(self, caso_con_ficha, monkeypatch):
        """Un revisor que no corre no refuta: se declara la cobertura ausente."""
        self._escrituras_en_verde(monkeypatch)

        def _boom(el, i):
            raise RuntimeError("sin cupo")
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", _boom)

        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 0, r.output
        assert "SIN VERIFICAR" in r.output
        assert "VERIFICADA por lectura" not in r.output
