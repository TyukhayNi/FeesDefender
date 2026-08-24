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
    errores = cli.validar_modo("v1", crm="api", fuente="drive_ev", folder_id="FID")
    assert len(errores) == 1
    assert "--crm skip" in errores[0]


def test_v1_admite_crm_skip():
    assert cli.validar_modo("v1", crm="skip", fuente="drive_ev",
                            folder_id="FID") == []


def test_v1_rechaza_el_default_de_crm():
    """Omitir --crm deja `api` por default: en v1 eso ABORTA, no se corrige en silencio.

    El plan traía aquí `assert default or True`, que no puede fallar nunca.
    La aserción que muerde es leer el default REAL de la opción Typer: si alguien lo
    cambiara a `skip`, la omisión pasaría en silencio y este test lo dice.
    """
    default_crm = inspect.signature(cli.main).parameters["crm"].default.default
    assert default_crm == "api"
    assert cli.validar_modo("v1", crm=default_crm, fuente="drive_ev",
                            folder_id="FID") != []


@pytest.mark.parametrize("fuente", ["email", "manual", "whatsapp"])
def test_v1_rechaza_fuentes_ajenas(fuente):
    errores = cli.validar_modo("v1", crm="skip", fuente=fuente, folder_id="FID")
    assert len(errores) == 1
    assert fuente in errores[0]


def test_v1_admite_drive_ev():
    assert cli.validar_modo("v1", crm="skip", fuente="drive_ev",
                            folder_id="FID") == []


def test_v1_acumula_los_errores():
    errores = cli.validar_modo("v1", crm="api", fuente="email", folder_id="FID")
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
    """Sin --modo, nada cambia: `email` y el default de crm siguen admitidos.

    R6/H6-08: la version anterior solo comprobaba la AUSENCIA de dos frases, y
    pasaba con `validar_modo` devolviendo `["BROKEN"]` y el CLI saliendo 1
    (reproducido al adjudicar). Lo que muerde es el codigo de salida y la
    secuencia observable, no que falte un texto.
    """
    llamadas = []
    monkeypatch.setattr(cli.case_manager, "ensure_case",
                        lambda *a, **k: llamadas.append("ensure_case"))
    monkeypatch.setattr(cli, "_despachar_intake",
                        lambda *a, **k: llamadas.append("intake"))
    monkeypatch.setattr(cli, "_alta_crm", lambda *a, **k: llamadas.append("crm"))

    res = runner.invoke(cli.app, [
        "--fuente", "email", "--cuenta", "x@y.z", "--label", "L", *_IDENT,
    ])

    assert res.exit_code == 0, res.output
    assert llamadas == ["ensure_case", "intake", "crm"], res.output
    assert "Modo desconocido" not in res.output
    assert "--modo v1" not in res.output


# ---------------------------------------------------------------------------
# R6 - remedios de los hallazgos confirmados al adjudicar (2026-08-24).
# Acta: docs/superpowers/specs/2026-08-24-apertura-v1-plan1-r6-adversarial-review.md
# ---------------------------------------------------------------------------


def test_v1_rechaza_force_sin_case_id():
    """H6-02 (CRITICO). Criterio 33 del §14, que el §21.4 mete en los 24 de V1:
    "--force nunca crea una carpeta sombra". La politica de colision de la spec
    admite --force SOLO para reutilizar el caso canonico ya resuelto por
    --case-id, asi que la puerta lo rechaza cuando no hay --case-id.
    """
    errores = cli.validar_modo("v1", crm="skip", fuente="drive_ev",
                               force=True, folder_id="FID")
    assert len(errores) == 1
    assert "--force" in errores[0]


def test_v1_admite_force_con_case_id():
    """No se deroga la capacidad: con --case-id el case_id queda pineado al ya
    verificado, y ahi --force no puede producir sombra."""
    assert cli.validar_modo("v1", crm="skip", fuente="drive_ev",
                            force=True, case_id="W-TEST01", folder_id="FID") == []


def test_v1_rechaza_dry_run():
    """H6-03. `_intake_drive_ev` llama a `pull_drive_ev` ANTES de consultar
    dry_run, y el corte sale 0 antes del log: una corrida effectful e incompleta
    etiquetada como V1. D3 hace al modo dueno del orden COMPLETO."""
    errores = cli.validar_modo("v1", crm="skip", fuente="drive_ev",
                               dry_run=True, folder_id="FID")
    assert len(errores) == 1
    assert "--dry-run" in errores[0]


def test_v1_exige_folder_id():
    """H6-04. `_validar_flags` no pide nada para drive_ev, asi que sin
    --folder-id el pull recibe None DESPUES de que `pull_drive_ev` haya hecho
    `target_dir.mkdir(...)`. V1 materializa Drive: sin ese dato no hay V1."""
    errores = cli.validar_modo("v1", crm="skip", fuente="drive_ev")
    assert len(errores) == 1
    assert "--folder-id" in errores[0]


def test_v1_acumula_todos_los_errores():
    """Las cinco reglas se acumulan; la puerta no para en la primera."""
    errores = cli.validar_modo("v1", crm="api", fuente="email",
                               force=True, dry_run=True)
    assert len(errores) == 5, errores


def test_v1_aborta_antes_de_la_autoderivacion_y_de_la_identidad(casos_root, monkeypatch):
    """H6-07 (el mutante que sobrevivio a mi propia prueba de mutacion).

    Mi bomba original solo cubria `ensure_case`, `_despachar_intake` y
    `_alta_crm`: una puerta desplazada por debajo de la resolucion de identidad
    y de la autoderivacion de Drive dejaba los 14 tests VERDES (reproducido al
    adjudicar). D3 exige abortar antes de la autoderivacion de identidad y de
    toda lectura remota, asi que las bombas tienen que estar TAMBIEN ahi.
    """
    def explota(nombre):
        def _b(*a, **k):
            raise AssertionError("efecto anterior a la puerta: " + nombre)
        return _b

    for obj, attr in (
        (cli, "_autoderivar_drive_ev"),      # lee la Drive API
        (cli, "_derivar_team_id"),           # lee la Drive API
        (cli.brain, "resolver_identidad"),   # autoderivacion de identidad
        (cli.case_locator, "list_cases"),    # lectura de disco
        (cli.case_locator, "resolve_ref"),   # resolucion de --case-id
        (cli.case_manager, "ensure_case"),
        (cli, "_despachar_intake"),
        (cli, "_alta_crm"),
    ):
        monkeypatch.setattr(obj, attr, explota(attr))

    res = runner.invoke(cli.app, [
        "--modo", "v1", *_IDENT, "--folder-id", "FID", "--team-id", "TID",
    ])

    assert res.exit_code == 1
    assert "--crm skip" in res.output
    assert list(casos_root.iterdir()) == []


def test_v1_force_no_crea_carpeta_sombra(casos_root, monkeypatch):
    """H6-02, la regresion de extremo a extremo: con el W-code ya presente,
    --force NO debe llegar a `ensure_case` con un case_id distinto."""
    (casos_root / "Barcelona" / "BaOLD - Anterior (W-TEST01) - Bad debt").mkdir(parents=True)
    llamadas = []
    monkeypatch.setattr(cli.case_manager, "ensure_case",
                        lambda *a, **k: llamadas.append(("ensure_case", a[0])))
    monkeypatch.setattr(cli, "_despachar_intake", lambda *a, **k: llamadas.append("intake"))
    monkeypatch.setattr(cli, "_alta_crm", lambda *a, **k: llamadas.append("crm"))

    res = runner.invoke(cli.app, [
        "--modo", "v1", "--crm", "skip", "--fuente", "drive_ev", "--force",
        "--w-code", "W-TEST01", "--ciudad", "Barcelona",
        "--tipo-caso", "BAD_DEBT", "--codigo-caso", "BaNEW",
        "--sufijo", "Bad debt", "--direccion", "Calle Nueva 2",
        "--folder-id", "FID", "--team-id", "TID",
    ])

    assert res.exit_code == 1, res.output
    assert llamadas == [], llamadas


def test_v1_cero_llamadas_remotas_de_alta(casos_root, monkeypatch):
    """§21.4, criterio 34: el criterio negativo pide un SPY que acredite cero
    llamadas remotas de alta, no parchear `_alta_crm` entero - que es lo que
    hacian mis tests y es mas grueso que el contrato."""
    remotas = []
    monkeypatch.setattr(cli.sudespacho_create, "create_expediente",
                        lambda *a, **k: remotas.append("create_expediente"))
    monkeypatch.setattr(cli.case_manager, "ensure_case", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_despachar_intake", lambda *a, **k: None)

    res = runner.invoke(cli.app, [
        "--modo", "v1", "--crm", "api", "--fuente", "drive_ev",
        *_IDENT, "--folder-id", "FID", "--team-id", "TID",
    ])

    assert res.exit_code == 1
    assert remotas == []
