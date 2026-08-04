"""Los CLI de sync del CRM bajan por el pull v2 y no encadenan el motor jubilado.

Dos defectos del mismo fichero, medidos el 2026-08-04 (`MEJORAS #113`):

1. **`--run-pipeline` llamaba a `pipeline.run`** —el motor viejo: Docling, tope de 30
   páginas, salida a `raw_text/` + `MD/` legacy— en cuatro sitios. El `help` de
   `intake_judicial` prometía literalmente «OCR → MD». Quien lo usara creyendo que
   procesaba el expediente producía artefactos del motor que la sala de máquina vino a
   sustituir.
2. **`pull`, `sync_all` y `scheduled_sync` usaban `pull_expediente` (v1)**, que escribe
   en `00_Input/sudespacho_<id>/`. Ese layout tiene tres consecuencias, y las tres son
   este fichero:
   - `is_legacy_intake_v1` lo declara «congelado» y `pull_expediente_v2` **se niega a
     correr** sobre él → un `pull` inutiliza el caso para `intake_judicial`. Y la carpeta
     se crea con `mkdir` **antes** de bajar el primer byte, así que basta un pull que
     falle o que se salte por marcador.
   - Queda fuera de las fuentes que declara `organizar-sala-lectura` (`01_Drive EV`,
     `05_CRM` + cajones legacy).
   - **Se salta el guard de escritura del caso prestado**: `_pendiente_checkin` solo
     aparece en v2, así que un pull v1 sobre un caso en checkout escribe en el árbol
     vivo — la ruta de pérdida de datos que cerraron los PR #156/#160, con este call
     site sin cubrir.

`pull_expediente` (v1) **no se retira**: `scripts/bulk_pull_expedientes.py` lo usa y
tiene sus propios tests. Lo que se cierra aquí es que los tres comandos de sync lo
llamen.

Grupo 1 (dobles) fija el cableado y la superficie del CLI; grupo 2 corre el **motor v2
real** con un cliente CRM falso, porque un doble del pull dejaría verde justamente el
layout que es el defecto. Datos SIEMPRE sintéticos: sin red, sin `G:`, sin rclone.
"""

from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

import pytest
from typer.testing import CliRunner

import scripts.scheduled_sync as sched
import scripts.sync_sudespacho as cli

runner = CliRunner()

CASE_ID = "BaRS9 - Falsa 1 (W-TEST99) - Vuelta"
EXPEDIENTE = "648"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def caso(tmp_casos_root, monkeypatch):
    """Un caso vacío bajo un CASOS_ROOT temporal, con el CRM neutralizado.

    Recarga los módulos que resuelven rutas, con la misma cautela que
    `test_pull_expediente_v2.py`: `sync_sudespacho` NO se recarga (otros ficheros
    ligan sus nombres al importar y un reload los desincronizaría).
    """
    from core import (case_manager, intake_log, intake_manifest, ocurrencias_crm,
                      sync_sudespacho)
    importlib.reload(case_manager)
    importlib.reload(intake_log)
    importlib.reload(intake_manifest)
    importlib.reload(ocurrencias_crm)

    case_manager.ensure_case(CASE_ID, titulo="Caso de prueba")

    # La validación preventiva de referencia habla con el CRM: fuera.
    monkeypatch.setattr(cli, "verify_expediente_referencia",
                        lambda *a, **k: {"crm_unreachable": True, "match": True})
    return sync_sudespacho


@pytest.fixture
def espias(monkeypatch):
    """Sustituye los DOS pulls por espías; devuelve (llamadas_v1, llamadas_v2)."""
    from core import sync_sudespacho as ss
    v1: list[tuple] = []
    v2: list[tuple] = []

    def fake_v1(case_id, expediente_id, **kw):
        v1.append((case_id, expediente_id, kw))
        raise AssertionError("pull v1: escribe el layout congelado sudespacho_*/")

    def fake_v2(case_id, expediente_id, **kw):
        v2.append((case_id, expediente_id, kw))
        return ss.PullResultV2(case_id=case_id, expediente_id=str(expediente_id),
                               element=kw.get("element", "expedientes_judiciales"),
                               documents_total_crm=3, documents_written=3)

    monkeypatch.setattr(cli, "pull_expediente", fake_v1, raising=False)
    monkeypatch.setattr(cli, "pull_expediente_v2", fake_v2, raising=False)
    monkeypatch.setattr(sched, "pull_expediente", fake_v1, raising=False)
    monkeypatch.setattr(sched, "pull_expediente_v2", fake_v2, raising=False)
    return v1, v2


class _FakeCRMClient:
    """Cliente REST mínimo: un documento PDF en la rama General.

    Tiene **forma de v2 a propósito**: implementa los tres métodos que invoca
    `pull_expediente_v2` (`list_gdocu_docs_rest`, `get_presigned_download_url`,
    `_download_url_raw`) y NO `download_document_rest`, que es por donde baja v1
    (`sync_sudespacho.py:1092`). Así la propia forma del doble es un guard: si el CLI
    volviera a bajar por v1, estos tests revientan con `AttributeError` en vez de pasar
    por otra vía.

    El `__exit__` sí lo necesitan los dos: ambos pulls cierran a mano el cliente que
    construyen ellos (`:1264` en v1, `:1662` en v2), así que no discrimina.
    """

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None


    def __init__(self, ss):
        self._ss = ss

    def list_gdocu_docs_rest(self, expediente_id, element=None):
        return [self._ss.GdocuDocInfo(
            doc_id="1", filename="demanda.pdf", id_carpeta="1",
            id_carpeta_label="General", mime="application/pdf", size=4, raw={})]

    def get_presigned_download_url(self, doc_id, expediente_id, element=None):
        return "http://fake/url"

    def _download_url_raw(self, url):
        return b"%PDF"

    def close(self):
        pass


@pytest.fixture
def crm_real(caso, monkeypatch):
    """El motor v2 REAL con el cliente CRM falso inyectado."""
    ss = caso
    monkeypatch.setattr(ss, "SudespachoClient", lambda *a, **k: _FakeCRMClient(ss))
    return ss


def _vincular_expediente():
    from core import case_manager
    case_manager.register_expediente(CASE_ID, EXPEDIENTE, "expedientes_judiciales")


# ---------------------------------------------------------------------------
# Grupo 1a — el cableado: qué pull llama cada comando
# ---------------------------------------------------------------------------

def test_pull_usa_el_v2_y_no_el_v1(caso, espias):
    v1, v2 = espias

    res = runner.invoke(cli.app, ["pull", "--case", CASE_ID,
                                  "--expediente", EXPEDIENTE])

    assert res.exit_code == 0, res.output
    assert v1 == []
    assert len(v2) == 1
    assert v2[0][0] == CASE_ID and v2[0][1] == EXPEDIENTE


def test_sync_all_usa_el_v2_y_no_el_v1(caso, espias):
    v1, v2 = espias
    _vincular_expediente()

    res = runner.invoke(cli.app, ["sync-all"])

    assert res.exit_code == 0, res.output
    assert v1 == []
    assert len(v2) == 1


def test_scheduled_sync_usa_el_v2_y_no_el_v1(caso, espias, monkeypatch):
    v1, v2 = espias
    _vincular_expediente()
    # El keep-alive lanza `rclone about` de verdad: la barrera de la suite solo cubre
    # el frontal de la biblioteca, no este script.
    monkeypatch.setattr(sched, "_keepalive_gdrive_ev", lambda log: None)
    # `scheduled_sync` hace `from core.config import settings` al importar, así que su
    # binding sigue apuntando al Settings de antes del tmp CASOS_ROOT.
    from core import config as cfg
    monkeypatch.setattr(sched, "settings", cfg.settings)

    assert sched.run() == 0
    assert v1 == []
    assert len(v2) == 1


# ---------------------------------------------------------------------------
# Grupo 1b — el flag retirado
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("argv", [
    ["pull", "--case", CASE_ID, "--expediente", EXPEDIENTE, "--run-pipeline"],
    ["intake-judicial", "--case", CASE_ID, "--expediente", EXPEDIENTE, "--run-pipeline"],
    ["sync-all", "--run-pipeline"],
])
def test_los_comandos_de_sync_ya_no_aceptan_run_pipeline(caso, espias, argv):
    res = runner.invoke(cli.app, argv)

    assert res.exit_code != 0
    assert "No such option" in res.output


def test_scheduled_sync_ya_no_acepta_run_pipeline(monkeypatch):
    monkeypatch.setattr("sys.argv", ["scheduled_sync", "--run-pipeline"])

    with pytest.raises(SystemExit) as exc:
        sched.main()

    assert exc.value.code == 2


@pytest.mark.parametrize("ruta", [
    "scripts/sync_sudespacho.py",
    "scripts/scheduled_sync.py",
])
def test_ningun_cli_de_sync_menciona_el_motor_jubilado(ruta):
    """Guard estructural: el defecto era la EXISTENCIA del call site.

    Un test de comportamiento no lo cubre — el flag se puede reintroducir en un cuarto
    comando y todos los de arriba seguirían verdes.
    """
    fuente = Path(ruta).read_text(encoding="utf-8")

    assert "pipeline.run(" not in fuente
    assert "import pipeline" not in fuente
    assert "pull_expediente(" not in fuente


# ---------------------------------------------------------------------------
# Grupo 1c — el siguiente paso se señaliza (nada silencioso)
# ---------------------------------------------------------------------------

def test_pull_senala_el_siguiente_paso(caso, espias):
    res = runner.invoke(cli.app, ["pull", "--case", CASE_ID,
                                 "--expediente", EXPEDIENTE])

    assert res.exit_code == 0, res.output
    assert "scripts.sala_maquina apply" in res.output


def test_intake_judicial_senala_la_sala_de_maquina_y_la_anonimizacion(caso, monkeypatch):
    """El flag encadenaba `anon` por defecto; al retirarlo hay que decir con qué.

    Sin esto, retirar el flag convierte una promesa falsa en un silencio, que era
    justamente el otro defecto del mismo fichero.
    """
    from core import judicial_intake

    class _Pull:
        documents_written = 2
        documents_overlap = 0
        documents_total_crm = 2
        documents_skipped_dedup = 0

    class _Res:
        case_id = CASE_ID
        expediente_id = EXPEDIENTE
        full = False
        demanda_doc_id = "1"
        contestacion_doc_id = None
        pendientes: list[str] = []
        errors: list[str] = []
        blocked_legacy_v1 = False
        classification = None
        pull = _Pull()

    monkeypatch.setattr(cli, "intake_demanda_contestacion", lambda *a, **k: _Res())

    res = runner.invoke(cli.app, ["intake-judicial", "--case", CASE_ID,
                                 "--expediente", EXPEDIENTE])

    assert res.exit_code == 0, res.output
    assert "scripts.sala_maquina apply" in res.output
    assert "scripts.anonimizar_caso" in res.output


# ---------------------------------------------------------------------------
# Grupo 2 — contra el MOTOR v2 REAL: el layout congelado deja de nacer
# ---------------------------------------------------------------------------

def test_pull_deposita_en_05_crm_y_no_crea_el_layout_congelado(crm_real, tmp_casos_root):
    res = runner.invoke(cli.app, ["pull", "--case", CASE_ID,
                                 "--expediente", EXPEDIENTE])

    assert res.exit_code == 0, res.output
    caso_dir = tmp_casos_root / CASE_ID
    assert list((caso_dir / "00_Input" / "05_CRM").rglob("*.pdf"))
    assert [p.name for p in (caso_dir / "00_Input").iterdir()
            if p.is_dir() and p.name.startswith("sudespacho_")] == []


def test_pull_sobre_un_caso_legacy_v1_avisa_y_falla(crm_real, tmp_casos_root):
    """El caso ya envenenado: v2 no escribe nada, así que hay que decirlo alto.

    Antes el v1 seguía escribiendo ahí y hundía el caso un poco más.
    """
    (tmp_casos_root / CASE_ID / "00_Input" / "sudespacho_123").mkdir()

    res = runner.invoke(cli.app, ["pull", "--case", CASE_ID,
                                 "--expediente", EXPEDIENTE])

    assert res.exit_code == 2
    assert "sudespacho_" in res.output
    assert "borrar" in res.output.lower()
    # Y no ha depositado nada por la vía vieja.
    caso_dir = tmp_casos_root / CASE_ID
    assert not list((caso_dir / "00_Input" / "sudespacho_123").iterdir())


def test_el_pull_v2_del_cli_respeta_el_guard_del_caso_prestado(crm_real, tmp_casos_root):
    """La consecuencia que motiva la migración, extremo a extremo por el CLI.

    Con el v1 el documento aterrizaba en el árbol vivo aunque el caso estuviera en
    checkout; el guard `_pendiente_checkin` solo existe en v2.
    """
    from core import case_manager
    case_manager.escribir_lock(CASE_ID, user="Nikolai Tyukhay",
                               timestamp="2026-08-04T09:00:00Z", nonce="n")

    res = runner.invoke(cli.app, ["pull", "--case", CASE_ID,
                                 "--expediente", EXPEDIENTE])

    assert res.exit_code == 0, res.output
    caso_dir = tmp_casos_root / CASE_ID
    bandeja = caso_dir / "_pendiente_checkin" / "crm" / "00_Input" / "05_CRM"
    assert list(bandeja.rglob("*.pdf"))
    vivo = caso_dir / "00_Input" / "05_CRM"
    assert not (list(vivo.rglob("*.pdf")) if vivo.exists() else [])
