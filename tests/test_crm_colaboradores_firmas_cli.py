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


def _aplica(extra=None):
    return CliRunner().invoke(cli.app, ["apply", "--case-id", "W-000AAA", *(extra or [])])


def _ficha(caso):
    return case_locator.path_for(caso) / "00_Input" / "_ficha_crm.yaml"


class TestApplyNecesitaConfirmacion:

    def test_sin_confirmar_no_toca_el_fichero(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        antes = _ficha(caso).read_text(encoding="utf-8")
        r = _aplica()
        assert r.exit_code == 0, r.output
        assert _ficha(caso).read_text(encoding="utf-8") == antes
        assert "confirmar" in r.output.lower()

    def test_sin_confirmar_SI_dice_lo_que_haria(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        r = _aplica()
        assert "612345678" in r.output


class TestApplyRellenaSoloElHueco:

    def test_rellena_movil_y_telefono_vacios(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        r = _aplica(["--confirmar"])
        assert r.exit_code == 0, r.output

        import yaml
        datos = yaml.safe_load(_ficha(caso).read_text(encoding="utf-8"))
        col = datos["colaboradores"][0]
        assert col["movil"] == "612345678"
        assert col["telefono"] == "931112233"

    def test_NO_pisa_un_valor_que_ya_estaba(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n"
            "    movil: '600000000'\n", encoding="utf-8")
        _aplica(["--confirmar"])

        import yaml
        col = yaml.safe_load(_ficha(caso).read_text(encoding="utf-8"))["colaboradores"][0]
        assert col["movil"] == "600000000", "lo que Nikolai escribio manda"
        assert col["telefono"] == "931112233", "el hueco si se rellena"

    def test_una_clave_PREPARADA_y_vacia_se_rellena(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n"
            "    movil:\n", encoding="utf-8")
        _aplica(["--confirmar"])

        import yaml
        col = yaml.safe_load(_ficha(caso).read_text(encoding="utf-8"))["colaboradores"][0]
        assert col["movil"] == "612345678"

    def test_el_cargo_NO_se_escribe_en_el_YAML(self, caso):
        """No hay campo de cargo en el CRM: escribirlo aqui seria dejarlo muerto."""
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        _aplica(["--confirmar"])
        assert "cargo" not in _ficha(caso).read_text(encoding="utf-8")

    def test_los_telefonos_se_escriben_ENTRE_COMILLAS(self, caso):
        """Sin comillas, `movil: 0612345678` lo relee YAML como un entero octal y el
        cero inicial no se recupera. `_escalar` lo RECHAZA, asi que romperia el CLI."""
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        _aplica(["--confirmar"])
        texto = _ficha(caso).read_text(encoding="utf-8")
        assert "'612345678'" in texto or '"612345678"' in texto

    def test_el_YAML_resultante_lo_puede_leer_cargar_ficha_yaml(self, caso):
        """La prueba por RESULTADO: que el siguiente eslabon lo acepte."""
        from core.crm_ficha import cargar_ficha_yaml
        _ficha(caso).write_text(
            "contrario:\n  nombre: JUAN\ncolaboradores:\n  - nombre: ANA\n"
            "    email: ana@engelvoelkers.com\n", encoding="utf-8")
        _aplica(["--confirmar"])

        ficha = cargar_ficha_yaml(_ficha(caso))
        col = ficha.colaboradores[0]
        assert (col.movil, col.telefono) == ("612345678", "931112233")


class TestApplyNoDaDeAltaANadie:
    """La §4 del spec: la lista de colaboradores la pone Nikolai."""

    def test_un_email_que_firma_y_NO_esta_en_la_lista_no_se_anade(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: BERTA\n    email: berta@engelvoelkers.com\n",
            encoding="utf-8")
        _aplica(["--confirmar"])

        import yaml
        datos = yaml.safe_load(_ficha(caso).read_text(encoding="utf-8"))
        emails = [c.get("email") for c in datos["colaboradores"]]
        assert emails == ["berta@engelvoelkers.com"]
        assert "ana@engelvoelkers.com" not in str(datos["colaboradores"])

    def test_sin_ficha_yaml_no_se_crea_una(self, caso):
        assert not _ficha(caso).exists()
        r = _aplica(["--confirmar"])
        assert r.exit_code == 1
        assert not _ficha(caso).exists()
        assert "_ficha_crm.yaml" in r.output


class TestApplyNoEscribeEnElCRM:

    def test_no_llama_a_ninguna_escritura_del_CRM(self, caso, monkeypatch):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        actualizar = MagicMock()
        monkeypatch.setattr("core.sudespacho_relations.update_colaborador", actualizar)
        monkeypatch.setattr("core.sudespacho_relations.create_colaborador", MagicMock())
        _aplica(["--confirmar"])
        actualizar.assert_not_called()


class TestElConflictoNoSeAplica:

    def test_un_conflicto_no_escribe_nada_en_el_YAML(self, caso):
        """Dos .eml con moviles distintos para la misma persona."""
        lote = case_locator.path_for(caso) / "00_Input" / "2026-08-14_email_01"
        (lote / "dos.eml").write_text(_EML.replace("612 34 56 78", "600 00 00 00"),
                                      encoding="utf-8")
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        _aplica(["--confirmar"])

        import yaml
        col = yaml.safe_load(_ficha(caso).read_text(encoding="utf-8"))["colaboradores"][0]
        assert not col.get("movil"), "en conflicto no se propone valor"
