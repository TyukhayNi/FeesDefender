"""E2E de la secuencia de V1 sobre un arbol de caso real en disco, sin PII y sin OCR.

Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md, Task 10.
Criterio 14 del §14 de la spec: punto fijo.

**Se doblan SOLO los limites** —rclone, la API del CRM y el OCR— y no las etapas: doblar
`etapa_sala_maquina` entera saltaria el adaptador, que es una de las piezas bajo prueba.
Y cada doble lleva ESPIA, porque un test que no comprueba que llamo no distingue
«funciono» de «no se ejecuto» (HA-10 de la R-A).
"""
import json

import pytest

from core import apertura_v1 as av1
from core.intake_drive import DriveIntakeResult
from scripts import abrir_caso as cli

CASE_ID = "BaXX1 - Prueba (W-000000) - NEGATIVA_OFERTA"


@pytest.fixture()
def caso(tmp_path):
    """Esquema REAL: `read_case_meta` devuelve `fm["meta"]`, no el frontmatter entero
    (`core/casos/case_locator.py:222`). La rev. 1 de este test escribia las claves en el
    nivel superior, el lector devolvia `{}` y el E2E pasaba en verde SIN tocar el CRM."""
    d = tmp_path / CASE_ID
    (d / "00_Input").mkdir(parents=True)
    (d / "00_Input" / "_caso.md").write_text(
        "---\n"
        "meta:\n"
        f"  case_id: {CASE_ID}\n"
        "  id_go: W-000000\n"
        "  tipo_caso: NEGATIVA_OFERTA\n"
        "  ciudad: Barcelona\n"
        "  sudespacho_expedientes:\n"
        "    - id: '648'\n"
        "      element: extrajudiciales\n"
        "      input_dir: sudespacho_648\n"
        "---\n",
        encoding="utf-8")
    return d


def test_la_fixture_es_legible_por_el_lector_real(caso):
    """El guardarrail de HA-10: si esto falla, el resto del E2E prueba la rama `saltada`
    y pasa en verde sin tocar el CRM."""
    from core.casos import case_locator
    meta = case_locator.read_case_meta(caso)
    assert meta.get("sudespacho_expedientes"), "el lector real no ve el expediente"


class _Ident:
    case_id = CASE_ID
    w_code = "W-000000"


class _ResCRM:
    blocked_legacy_v1 = False
    documents_total_crm = 3
    documents_written = 3
    documents_failed = 0
    errors: list = []


@pytest.fixture()
def dobles(caso, monkeypatch):
    llamadas = {"drive": 0, "crm": 0, "ocr": 0}
    #: Lo que los dobles VIERON. No se afirma dentro del doble: `etapa_drive` y
    #: `etapa_crm` capturan `Exception`, asi que un `assert` ahi dentro se lo traga el
    #: codigo bajo prueba y se convierte en un `fallo` de etapa. Una asercion que el
    #: sujeto puede tragarse no puede fallar. Lo destapo el arnes de mutacion: el mutante
    #: F16 sobrevivia a un test que decia comprobar `force`.
    visto = {"force": [], "element": []}

    def _intake(ident, case_dir, folder_id, team_id, *, dry_run, force):
        llamadas["drive"] += 1
        visto["force"].append(force)
        return DriveIntakeResult(case_id="C", team_id="T", folder_id="F",
                                 target_dir=caso / "00_Input" / "01_Drive EV",
                                 files_after=2, skipped=False)

    def _pull(case_id, expediente_id, *, element):
        llamadas["crm"] += 1
        visto["element"].append(element)
        return _ResCRM()

    def _apply(case_id=None, **kw):
        from scripts.sala_maquina import ResultadoApply
        llamadas["ocr"] += 1
        return ResultadoApply(status_atomizacion="ok")

    from core import sync_sudespacho
    from scripts import sala_maquina
    monkeypatch.setattr(cli, "_intake_drive_ev", _intake)
    monkeypatch.setattr(sync_sudespacho, "pull_expediente_v2", _pull)
    monkeypatch.setattr(sala_maquina, "apply", _apply)
    llamadas["_visto"] = visto
    return llamadas


def _conteos(dobles):
    """Los contadores, sin la clave de espionaje."""
    return {k: v for k, v in dobles.items() if not k.startswith("_")}


def test_e2e_la_secuencia_recorre_las_tres_etapas_y_las_LLAMA(caso, dobles):
    r = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")

    assert [e.nombre for e in r.etapas] == list(cli.ETAPAS_V1)
    assert [e.estado for e in r.etapas] == ["hecha", "hecha", "hecha"]
    assert _conteos(dobles) == {"drive": 1, "crm": 1, "ocr": 1}
    assert r.estado == av1.EstadoV1.PREPARADO_CON_PENDIENTES
    assert r.no_ejecutadas == ()
    assert dobles["_visto"]["force"] == [True], "V1 consulta Drive en cada ronda"
    assert dobles["_visto"]["element"] == ["extrajudiciales"]


def test_e2e_el_evento_de_cierre_queda_en_el_log(caso, dobles):
    r = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")
    cli.registrar_cierre_v1(caso, _Ident(), r)
    log = caso / "00_Input" / "_intake_log.jsonl"
    ev = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l][-1]
    assert ev["event"] == "apertura_v1_terminada"
    assert ev["details"]["estado"] == "preparado_con_pendientes"
    assert ev["details"]["etapas"] == [
        {"nombre": "drive", "estado": "hecha"},
        {"nombre": "crm", "estado": "hecha"},
        {"nombre": "sala_maquina", "estado": "hecha"}]


def test_e2e_es_punto_fijo_MATERIAL_y_no_solo_de_estado(caso, dobles):
    """Criterio 14. La rev. 1 comparaba el string de estado, que no dice nada: dos
    corridas pueden coincidir en el token y diferir en el arbol. Se compara el arbol."""
    def foto():
        return sorted((p.relative_to(caso).as_posix(), p.stat().st_size)
                      for p in caso.rglob("*") if p.is_file()
                      and p.name != "_intake_log.jsonl")

    primera = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")
    tras_1 = foto()
    segunda = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")
    tras_2 = foto()

    assert primera.estado == segunda.estado
    assert tras_1 == tras_2, "la segunda corrida cambio el arbol: no es punto fijo"
    # Y las tres etapas se CONSULTARON las dos veces: el punto fijo de V1 no es «no
    # mirar», es «mirar y no cambiar nada» (HA-03). Por eso se afirma tambien que las DOS
    # rondas pidieron consulta remota: es la propiedad de HA-03 en el tiempo, no en un
    # instante.
    assert _conteos(dobles) == {"drive": 2, "crm": 2, "ocr": 2}
    assert dobles["_visto"]["force"] == [True, True]
    assert dobles["_visto"]["element"] == ["extrajudiciales", "extrajudiciales"]


def test_e2e_un_fallo_del_crm_bloquea_y_la_sala_no_corre(caso, dobles, monkeypatch):
    from core import sync_sudespacho

    class _Roto(_ResCRM):
        errors = ["list_gdocu_docs_rest: 500"]

    monkeypatch.setattr(sync_sudespacho, "pull_expediente_v2", lambda *a, **k: _Roto())
    r = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")
    assert r.estado == av1.EstadoV1.BLOQUEADO
    assert dobles["ocr"] == 0, "la sala de maquina corrio sobre un CRM incompleto"
    assert r.no_ejecutadas == ("sala_maquina",)


def test_e2e_hasta_drive_no_consulta_el_crm_ni_el_ocr(caso, dobles):
    r = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T", hasta="drive")
    assert _conteos(dobles) == {"drive": 1, "crm": 0, "ocr": 0}
    assert r.no_ejecutadas == ("crm", "sala_maquina")
    assert dobles["_visto"]["force"] == [True]
