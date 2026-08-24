"""El modo de ejecución de `abrir_caso`: vocabulario cerrado y puertas de V1.

Spec: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md
§24 D3 — el discriminante de V1 y el dueño de la secuencia son el mismo objeto.
"""
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
