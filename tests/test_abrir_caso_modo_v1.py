"""El modo de ejecución de `abrir_caso`: vocabulario cerrado y puertas de V1.

Spec: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md
§24 D3 — el discriminante de V1 y el dueño de la secuencia son el mismo objeto.
"""
import inspect

import pytest
from typer.testing import CliRunner

from core.casos import case_locator
from scripts import abrir_caso as cli

runner = CliRunner()


def test_modos_vocabulario_cerrado():
    assert cli._MODOS == ("libre", "v1")


def test_modo_desconocido_es_error():
    errores = cli.validar_modo("V1", crm="skip", fuente="drive_ev")
    assert errores
    assert "modo desconocido" in errores[0].lower()


def test_modo_libre_no_impone_nada():
    assert cli.validar_modo("libre", crm="api", fuente="email") == []


def test_v1_rechaza_crm_api():
    errores = cli.validar_modo("v1", crm="api", fuente="drive_ev")
    assert len(errores) == 1
    assert "--crm skip" in errores[0]


def test_v1_admite_crm_skip():
    assert cli.validar_modo("v1", crm="skip", fuente="drive_ev") == []


def test_v1_rechaza_el_default_de_crm():
    """Omitir --crm deja `api` por default: en v1 eso ABORTA, no se corrige en silencio.

    El plan traía aquí `assert default or True`, que no puede fallar nunca.
    La aserción que muerde es leer el default REAL de la opción Typer: si alguien lo
    cambiara a `skip`, la omisión pasaría en silencio y este test lo dice.
    """
    default_crm = inspect.signature(cli.main).parameters["crm"].default.default
    assert default_crm == "api"
    assert cli.validar_modo("v1", crm=default_crm, fuente="drive_ev") != []


@pytest.mark.parametrize("fuente", ["email", "manual", "whatsapp"])
def test_v1_rechaza_fuentes_ajenas(fuente):
    errores = cli.validar_modo("v1", crm="skip", fuente=fuente)
    assert len(errores) == 1
    assert fuente in errores[0]


def test_v1_admite_drive_ev():
    assert cli.validar_modo("v1", crm="skip", fuente="drive_ev") == []


def test_v1_acumula_los_errores():
    errores = cli.validar_modo("v1", crm="api", fuente="email")
    assert len(errores) == 2


@pytest.fixture
def casos_root(tmp_path, monkeypatch):
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    return root


# El plan escribia `--tipo-caso honorarios`, que no existe: los canonicos son los de
# config.TIPOS_CASO_ALL y el sufijo se deriva de ellos (config.sufijo_de_tipo_caso).
_IDENT = [
    "--w-code", "W-TEST01", "--ciudad", "Barcelona",
    "--tipo-caso", "BAD_DEBT", "--codigo-caso", "BaTEST",
    "--sufijo", "Bad debt", "--direccion", "Calle Falsa 1",
]


def test_v1_aborta_antes_de_crear_el_esqueleto(casos_root, monkeypatch):
    """Sin --crm skip, v1 aborta y NO deja rastro en disco."""
    def explota(*a, **k):
        raise AssertionError("no debia llegar a ejecutarse ningun efecto")

    monkeypatch.setattr(cli.case_manager, "ensure_case", explota)
    monkeypatch.setattr(cli, "_despachar_intake", explota)
    monkeypatch.setattr(cli, "_alta_crm", explota)

    res = runner.invoke(cli.app, [
        "--modo", "v1", *_IDENT, "--folder-id", "FID", "--team-id", "TID",
    ])

    assert res.exit_code == 1
    assert "--crm skip" in res.output
    assert list(casos_root.iterdir()) == []


def test_v1_con_los_flags_correctos_pasa_la_puerta(casos_root, monkeypatch):
    """La puerta no bloquea una invocacion V1 valida: llega al intake."""
    llamadas = []
    monkeypatch.setattr(cli.case_manager, "ensure_case",
                        lambda *a, **k: llamadas.append("ensure_case"))
    monkeypatch.setattr(cli, "_despachar_intake",
                        lambda *a, **k: llamadas.append("intake"))
    monkeypatch.setattr(cli, "_alta_crm", lambda *a, **k: llamadas.append("crm"))

    res = runner.invoke(cli.app, [
        "--modo", "v1", "--crm", "skip", *_IDENT,
        "--folder-id", "FID", "--team-id", "TID",
    ])

    assert res.exit_code == 0, res.output
    assert "ensure_case" in llamadas and "intake" in llamadas


def test_modo_libre_conserva_el_comportamiento(casos_root, monkeypatch):
    """Sin --modo, nada cambia: `email` y el default de crm siguen admitidos."""
    monkeypatch.setattr(cli.case_manager, "ensure_case", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_despachar_intake", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_alta_crm", lambda *a, **k: None)

    res = runner.invoke(cli.app, [
        "--fuente", "email", "--cuenta", "x@y.z", "--label", "L", *_IDENT,
    ])

    assert "Modo desconocido" not in res.output
    assert "--modo v1" not in res.output
