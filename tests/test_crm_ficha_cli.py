from pathlib import Path
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

    link_ev.assert_called_once_with("606")
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
