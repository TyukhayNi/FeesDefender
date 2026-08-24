"""El modo de ejecución de `abrir_caso`: vocabulario cerrado y puertas de V1.

Spec: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md
§24 D3 — el discriminante de V1 y el dueño de la secuencia son el mismo objeto.
"""
import inspect

import pytest
from typer.testing import CliRunner

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
