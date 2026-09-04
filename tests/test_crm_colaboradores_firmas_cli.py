"""El informe: que dice la firma, que falta en el CRM, y QUE NO SE PUDO MIRAR.

Un dato que no se pudo leer nunca se convierte en un dato que no existe. Y aparecer en
un correo del expediente no te hace colaborador de ese expediente: eso lo decide
Nikolai, y el informe solo se lo senala.
"""
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from core import case_manager
from core.casos import case_locator
from scripts import crm_colaboradores_firmas as cli

_EML = """\
From: "Otro, Remitente" <otro@engelvoelkers.com>
Subject: x
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0

Hola.

ENGEL&VÖLKERS
*Ana Ejemplo Ficticia*
Asesora Inmobiliaria
Telf: +34 93 111 22 33
Móvil: *612 34 56 78*
ana@engelvoelkers.com
"""


class FugaDeRedEnTest(BaseException):
    """No hereda de Exception: ningun `except Exception` del CLI puede tragarsela."""


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    def _prohibido(metodo):
        def _f(*a, **k):
            raise FugaDeRedEnTest(f"httpx.{metodo} salio a la red en un test")
        return _f
    for metodo in ("get", "post", "put", "delete", "patch", "request"):
        monkeypatch.setattr(f"httpx.{metodo}", _prohibido(metodo))


@pytest.fixture
def caso(tmp_path, monkeypatch):
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_id = "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
    case_manager.ensure_case(
        case_id, titulo=case_id, referencia_crm=case_id, tipo_caso="VUELTA",
        ciudad="Barcelona", direccion="Falsa 1", id_go="W-000AAA",
    )
    lote = case_locator.path_for(case_id) / "00_Input" / "2026-08-14_email_01"
    lote.mkdir(parents=True, exist_ok=True)
    (lote / "uno.eml").write_text(_EML, encoding="utf-8")
    return case_id


def _corre(extra=None):
    return CliRunner().invoke(cli.app, ["report", "--case-id", "W-000AAA", *(extra or [])])


class TestElInformeSeEscribeFueraDelCrudo:

    def test_va_a_01_Procesado_no_a_00_Input(self, caso, monkeypatch):
        """`00_Input` es crudo intocable por la regla de idempotencia de CLAUDE.md."""
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        r = _corre()
        assert r.exit_code == 0, r.output

        destino = case_locator.path_for(caso) / "01_Procesado" / "_firmas_colaboradores.md"
        assert destino.is_file()
        assert not (case_locator.path_for(caso) / "00_Input" / "_firmas_colaboradores.md").exists()

    def test_el_informe_cita_fichero_y_linea(self, caso, monkeypatch):
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        _corre()
        texto = (case_locator.path_for(caso) / "01_Procesado"
                 / "_firmas_colaboradores.md").read_text(encoding="utf-8")
        assert "uno.eml:" in texto, "sin origen, el dato no es verificable"
        assert "612345678" in texto
        assert "931112233" in texto


class TestElInformeDeclaraLoQueNoPudoMirar:

    def test_un_eml_ilegible_SALE_en_el_informe(self, caso, monkeypatch):
        lote = case_locator.path_for(caso) / "00_Input" / "2026-08-14_email_01"
        (lote / "roto.eml").write_bytes(b"\xff\xfe no")
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        _corre()

        texto = (case_locator.path_for(caso) / "01_Procesado"
                 / "_firmas_colaboradores.md").read_text(encoding="utf-8")
        assert "roto.eml" in texto
        assert "NO_LEIBLE" in texto or "no se pudo" in texto.lower()

    def test_el_informe_NUNCA_dice_que_alguien_no_tiene_telefono(self, caso, monkeypatch):
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        _corre()
        texto = (case_locator.path_for(caso) / "01_Procesado"
                 / "_firmas_colaboradores.md").read_text(encoding="utf-8").lower()
        for prohibido in ("no tiene móvil", "no tiene movil", "no tiene teléfono",
                          "sin móvil", "no dispone de"):
            assert prohibido not in texto, f"afirma una ausencia: {prohibido!r}"


class TestLosCandidatosSonSUGERENCIA:
    """Medido: 7 direcciones @ev en los 6 .eml de W-02Q38C, 6 ya son colaboradores y
    solo 3 estan vinculadas al expediente. El corpus NO dice quien es colaborador."""

    def test_una_direccion_vista_que_no_esta_en_la_ficha_sale_como_candidata(
            self, caso, monkeypatch):
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        _corre()
        texto = (case_locator.path_for(caso) / "01_Procesado"
                 / "_firmas_colaboradores.md").read_text(encoding="utf-8")
        assert "otro@engelvoelkers.com" in texto, "el From: aparece, aunque no firme"
        assert "candidat" in texto.lower()

    def test_cada_candidato_lleva_el_veredicto_SIN_FIRMA(self, caso, monkeypatch):
        """«Aparece y no firma» es un veredicto con nombre, no una lista sin etiqueta."""
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        _corre()
        texto = (case_locator.path_for(caso) / "01_Procesado"
                 / "_firmas_colaboradores.md").read_text(encoding="utf-8")
        assert "SIN_FIRMA" in texto

    def test_el_informe_NO_da_de_alta_a_nadie(self, caso, monkeypatch):
        """Ni crea ni vincula: es un informe. El alta la decide Nikolai."""
        crear = MagicMock()
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        monkeypatch.setattr("core.sudespacho_relations.create_colaborador", crear)
        _corre()
        crear.assert_not_called()

    def test_report_NO_escribe_en_el_ficha_crm_yaml(self, caso, monkeypatch):
        """`report` solo informa; escribir es `apply` (Task 10)."""
        ficha = case_locator.path_for(caso) / "00_Input" / "_ficha_crm.yaml"
        ficha.write_text("colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
                         encoding="utf-8")
        antes = ficha.read_text(encoding="utf-8")
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        _corre()
        assert ficha.read_text(encoding="utf-8") == antes


class TestUnCasoQueNoExiste:

    def test_sale_con_error_legible(self, tmp_path, monkeypatch):
        root = tmp_path / "CASOS"
        root.mkdir()
        monkeypatch.setattr(case_locator, "_root", lambda: root)
        r = CliRunner().invoke(cli.app, ["report", "--case-id", "W-NOEXISTE"])
        assert r.exit_code == 1
        assert "no encontrado" in r.output.lower()
