"""Las costuras de V1, contratadas por el extremo que CONSUME.

Remedia la frontera de fondo de la R-B (L6-01..L6-04, L2-02, L3-03): todos los tests de
adaptador inyectaban el colaborador (`intake=`, `pull=`, `correr=`, `etapas=`), y eso los
dejaba ciegos al otro extremo. Medido por dos lentes con sus propios mutantes: se podia
hacer que `apply()` dejara de devolver el status, que la custodia dejara de reenviar
`force`, o que `main` pasara `hasta=None`, **sin un solo test rojo**.

Regla que estos tests encarnan: en una pieza de cableado, al menos un test por costura
recorre el camino por DEFECTO y afirma el efecto donde el valor se consume.
"""
import json

import pytest

from core import apertura_v1 as av1
from core.intake_drive import DriveIntakeResult
from scripts import abrir_caso as cli


# --------------------------------------------------------------------------
# Costura 1: `etapa_sala_maquina` -> `sala_maquina.apply` -> el status
# --------------------------------------------------------------------------

@pytest.mark.parametrize("status,estado", [
    ("ok", "hecha"), ("parcial", "hecha"), ("fallo", "fallo"), (None, "hecha"),
])
def test_costura_el_status_de_apply_llega_por_el_camino_POR_DEFECTO(status, estado,
                                                                   monkeypatch):
    """L6-01. Sin `correr=`: si `apply` deja de devolver su status, toda la maquina de
    estados del §24 D4 queda muerta en produccion y ningun test lo notaba."""
    from scripts import sala_maquina

    monkeypatch.setattr(sala_maquina, "apply", lambda case_id=None, **k: status)

    class _Ident:
        case_id = "C"
        w_code = "W-000000"

    r = cli.etapa_sala_maquina(_Ident())
    assert r.estado == estado
    assert bool(r.pendientes) is (status == "parcial")


def test_costura_apply_recibe_EL_caso_y_no_otro(monkeypatch):
    """L6-10. El doble tenia contador y no espia de valor: apuntar `apply` a otro caso
    sobrevivia."""
    from scripts import sala_maquina

    vistos = []
    monkeypatch.setattr(sala_maquina, "apply",
                        lambda case_id=None, **k: vistos.append(case_id) or "ok")

    class _Ident:
        case_id = "BaXX9 - Otro (W-999999) - X"
        w_code = "W-999999"

    cli.etapa_sala_maquina(_Ident())
    assert vistos == ["BaXX9 - Otro (W-999999) - X"]


# --------------------------------------------------------------------------
# Costura 2: `_intake_drive_ev` -> `pull_drive_ev` -> `force`
# --------------------------------------------------------------------------

def test_costura_la_custodia_REENVIA_force_a_quien_lo_consume(tmp_path, monkeypatch):
    """L6-02/L6-03. HA-03 se probaba en el llamador, no donde el parametro se consume:
    `_intake_drive_ev` podia dejar de reenviar `force` sin un solo rojo. Y su `return res`
    podia volverse `None` — que haria fallar SIEMPRE la etapa de Drive — y sobrevivia."""
    vistos = {}

    def _pull(case_id, folder_id, team_id, *, force=False):
        vistos.update(case_id=case_id, folder_id=folder_id, force=force)
        destino = tmp_path / "00_Input" / "01_Drive EV"
        destino.mkdir(parents=True, exist_ok=True)
        return DriveIntakeResult(case_id=case_id, team_id=team_id, folder_id=folder_id,
                                 target_dir=destino, files_after=0, skipped=False)

    monkeypatch.setattr(cli.intake_drive, "pull_drive_ev", _pull)
    monkeypatch.setattr(cli, "_intake_generico", lambda *a, **k: None)

    class _Ident:
        case_id = "C"
        w_code = "W-000000"

    res = cli._intake_drive_ev(_Ident(), tmp_path, "FID", "TID",
                               dry_run=False, force=True)
    assert vistos["force"] is True, "la custodia no reenvia `force` al pull"
    assert res is not None, "la custodia no devuelve el resultado: la etapa fallaria siempre"
    assert res.folder_id == "FID"


# --------------------------------------------------------------------------
# Costura 3: `main` -> `secuencia_v1` -> `hasta`, y el registro durable
# --------------------------------------------------------------------------

@pytest.fixture()
def caso_v1(tmp_path, monkeypatch):
    """Raiz de casos aislada. Mismo montaje que `test_abrir_caso_modo_v1.casos_root`:
    `settings` es un dataclass CONGELADO, asi que se desvia el localizador."""
    from core.casos import case_locator
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    return root


def test_costura_main_PASA_el_hasta_a_la_secuencia(caso_v1, monkeypatch):
    """L6-04. `hasta=hasta` -> `hasta=None` sobrevivia: el flag podia quedar INERTE y el
    informe diria «corrida completa» donde el operador pidio parar."""
    visto = {}

    def _falsa(ident, case_dir, *, folder_id, team_id, hasta=None, etapas=None):
        visto["hasta"] = hasta
        return av1.ResultadoV1(
            estado=av1.EstadoV1.PREPARADO_CON_PENDIENTES,
            etapas=(av1.EtapaResultado(nombre="drive", estado="hecha", detalle="d"),),
            pendientes=(av1.PENDIENTE_FUENTES_V3,), parada="drive",
            no_ejecutadas=("crm", "sala_maquina"))

    monkeypatch.setattr(cli, "secuencia_v1", _falsa)

    from typer.testing import CliRunner
    CliRunner().invoke(cli.app, [
        "--modo", "v1", "--crm", "skip",
        "--w-code", "W-000000", "--ciudad", "Barcelona",
        "--tipo-caso", "BAD_DEBT", "--codigo-caso", "BaXX8",
        "--sufijo", "Bad debt", "--direccion", "Prueba 1",
        "--folder-id", "FID", "--team-id", "TID", "--hasta", "drive", "--yes",
    ])
    assert visto.get("hasta") == "drive", (
        "`main` no propaga --hasta: el flag queda inerte y nadie se enteraria")


# --------------------------------------------------------------------------
# Costura 4: `main` -> el proceso. Codigo de salida, evento y estado durable.
# --------------------------------------------------------------------------

def _correr_main(monkeypatch, resultado, extra=()):
    """Conduce `main --modo v1` hasta el final con la secuencia doblada."""
    from typer.testing import CliRunner
    monkeypatch.setattr(cli, "secuencia_v1", lambda *a, **k: resultado)
    return CliRunner().invoke(cli.app, [
        "--modo", "v1", "--crm", "skip",
        "--w-code", "W-000000", "--ciudad", "Barcelona",
        "--tipo-caso", "BAD_DEBT", "--codigo-caso", "BaXX7",
        "--sufijo", "Bad debt", "--direccion", "Prueba 2",
        "--folder-id", "FID", "--team-id", "TID", "--yes", *extra,
    ])


def _resultado(estado):
    return av1.ResultadoV1(
        estado=estado,
        etapas=(av1.EtapaResultado(nombre="drive", estado="hecha", detalle="d"),),
        pendientes=(av1.PENDIENTE_FUENTES_V3,), parada=None, no_ejecutadas=())


@pytest.mark.parametrize("estado,codigo", [
    (av1.EstadoV1.BLOQUEADO, 1),
    (av1.EstadoV1.PREPARADO_CON_PENDIENTES, 0),
])
def test_costura_el_estado_gobierna_el_CODIGO_DE_SALIDA_DEL_PROCESO(estado, codigo,
                                                                    caso_v1, monkeypatch):
    """L1-03. `codigo_de_salida` se probaba como funcion pura: borrar la salida de `main`
    dejaba todo verde. Un script que invoque la secuencia lee el codigo del PROCESO."""
    res = _correr_main(monkeypatch, _resultado(estado))
    assert res.exit_code == codigo, res.output


def test_costura_main_EMITE_el_evento_y_cierra_la_ronda(caso_v1, monkeypatch):
    """L1-05/L1-06. F13 contrataba la pertenencia del nombre al set cerrado, no la
    EMISION: `registrar_cierre_v1(...) -> pass` no mataba nada. Y nada exigia que `main`
    usara el estado durable, asi que `_apertura_v1.json` podia no existir nunca."""
    res = _correr_main(monkeypatch, _resultado(av1.EstadoV1.PREPARADO_CON_PENDIENTES))
    assert res.exit_code == 0, res.output

    casos = [d for d in caso_v1.rglob("00_Input") if d.is_dir()]
    assert casos, "el esqueleto del caso no se creo"
    entrada = casos[0]

    log = entrada / "_intake_log.jsonl"
    assert log.is_file(), "no se emitio ningun evento"
    eventos = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l]
    cierres = [e for e in eventos if e["event"] == "apertura_v1_terminada"]
    assert cierres, "la corrida no dejo el evento de cierre en el log forense"
    assert cierres[-1]["details"]["estado"] == "preparado_con_pendientes"

    durable = entrada / "_apertura_v1.json"
    assert durable.is_file(), "no se escribio el estado durable por ronda"
    ronda = json.loads(durable.read_text(encoding="utf-8"))
    assert ronda["terminada"], "la ronda quedo abierta tras una corrida con exito"
    assert ronda["estado"] == "preparado_con_pendientes"
    assert ronda["etapas"] == {"drive": "hecha"}
