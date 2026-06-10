"""Tests dedicados v2 — paso 8 del refactor intake v2.

Módulo bajo test: ``core.intake_log`` (M10 — log forense append-only).

Cobertura ampliada respecto a ``test_smoke_paso7.py`` (que cubría una
línea ``upload_manual`` happy path):

- Schema completo del evento + ``ts``/``actor`` overrides.
- Rechazo de eventos desconocidos (set cerrado ``INTAKE_EVENTS``).
- Singleton de actor (thread-safe) + reset + override por llamada.
- ``_default_actor``: env var > ``os.getlogin()`` > "system".
- ``read_events`` con log vacío, múltiples entradas y líneas corruptas.
- ``log_path`` no crea el archivo.
- ``os.fsync`` se invoca en cada ``append_event`` (resiliencia a crashes
  según M10-Q4).
- ``INTAKE_EVENTS`` sanity (13 eventos documentados).
"""

from __future__ import annotations

import importlib
import json
import re

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def il(tmp_casos_root):
    """Devuelve ``core.intake_log`` recargado tras el reload de config."""
    from core import intake_log as _il

    importlib.reload(_il)
    return _il


@pytest.fixture
def cm(tmp_casos_root):
    """``case_manager`` recargado — para crear el caso antes de loggear."""
    from core import case_manager as _cm

    importlib.reload(_cm)
    return _cm


@pytest.fixture(autouse=True)
def _reset_actor_singleton():
    """Resetea el singleton ``_actor`` antes y después de cada test.

    El singleton es proceso-global; sin reset, ``set_actor("X")`` en un
    test contamina los siguientes (y al ``test_smoke_paso7`` si se mezclan
    en la misma run).
    """
    from core import intake_log as _il
    _il.set_actor(None)
    yield
    _il.set_actor(None)


# ---------------------------------------------------------------------------
# Schema básico y append+read
# ---------------------------------------------------------------------------

ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def test_append_event_crea_log_y_persiste_schema(il, cm, tmp_casos_root):
    cm.ensure_case("LOG-1")
    il.set_actor("Nikolai Tyukhay")

    path = il.append_event(
        "LOG-1", "link_expediente",
        details={"expediente_id": "648", "element": "expedientes_judiciales"},
    )

    assert path == tmp_casos_root / "LOG-1" / "00_Input" / "_intake_log.jsonl"
    assert path.is_file()

    lines = [
        ln for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert len(lines) == 1
    entry = json.loads(lines[0])

    assert set(entry.keys()) == {"ts", "actor", "event", "case_id", "details"}
    assert entry["event"] == "link_expediente"
    assert entry["actor"] == "Nikolai Tyukhay"
    assert entry["case_id"] == "LOG-1"
    assert entry["details"] == {
        "expediente_id": "648", "element": "expedientes_judiciales",
    }
    assert ISO8601_RE.match(entry["ts"])


def test_append_event_details_default_dict_vacio(il, cm):
    cm.ensure_case("LOG-2")
    il.set_actor("Ana Solange Velastegui")
    il.append_event("LOG-2", "upload_manual")

    events = il.read_events("LOG-2")
    assert len(events) == 1
    assert events[0]["details"] == {}


def test_append_event_multiples_lineas_en_orden(il, cm):
    cm.ensure_case("LOG-3")
    il.set_actor("Karen Paola Barreto")

    il.append_event("LOG-3", "link_expediente", details={"i": 1})
    il.append_event("LOG-3", "pull_crm", details={"i": 2})
    il.append_event("LOG-3", "dedup_skipped", details={"i": 3})

    events = il.read_events("LOG-3")
    assert [e["event"] for e in events] == [
        "link_expediente", "pull_crm", "dedup_skipped",
    ]
    assert [e["details"]["i"] for e in events] == [1, 2, 3]


def test_append_event_crea_subcarpeta_00_input_si_falta(il, tmp_casos_root):
    """``append_event`` debe crear ``00_Input/`` si no existe.

    Útil en escenarios de migración / casos creados sin ``ensure_case``.
    """
    case_root = tmp_casos_root / "LOG-NO-INPUT"
    case_root.mkdir()  # no creamos 00_Input

    il.append_event("LOG-NO-INPUT", "upload_manual")

    log = case_root / "00_Input" / "_intake_log.jsonl"
    assert log.is_file()


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------

def test_append_event_actor_override(il, cm):
    cm.ensure_case("LOG-4")
    il.set_actor("Nikolai Tyukhay")

    il.append_event(
        "LOG-4", "upload_manual",
        actor="Marta Reynares",   # override puntual
    )

    events = il.read_events("LOG-4")
    assert events[0]["actor"] == "Marta Reynares"
    # El singleton no debe haber cambiado tras el override
    assert il.get_actor() == "Nikolai Tyukhay"


def test_append_event_ts_override(il, cm):
    cm.ensure_case("LOG-5")
    ts = "2026-05-11T10:00:00"
    il.append_event("LOG-5", "upload_manual", ts=ts)

    events = il.read_events("LOG-5")
    assert events[0]["ts"] == ts


# ---------------------------------------------------------------------------
# Validación de evento
# ---------------------------------------------------------------------------

def test_append_event_rechaza_evento_desconocido(il, cm):
    cm.ensure_case("LOG-6")

    with pytest.raises(ValueError, match="Evento desconocido"):
        il.append_event("LOG-6", "evento_que_no_existe")


def test_append_event_acepta_todos_los_eventos_canonicos(il, cm):
    """Smoke: cada uno de los 13 ``INTAKE_EVENTS`` se puede escribir."""
    cm.ensure_case("LOG-7")
    for event in il.INTAKE_EVENTS:
        il.append_event("LOG-7", event)

    events = il.read_events("LOG-7")
    assert {e["event"] for e in events} == set(il.INTAKE_EVENTS)


# ---------------------------------------------------------------------------
# Singleton de actor — set_actor / get_actor
# ---------------------------------------------------------------------------

def test_set_actor_y_get_actor(il):
    il.set_actor("Sergio Piñol")
    assert il.get_actor() == "Sergio Piñol"


def test_set_actor_none_resetea_al_default(il, monkeypatch):
    """``set_actor(None)`` vuelve al default (env > os.getlogin > "system")."""
    monkeypatch.setenv("FEESDEFENDER_ACTOR", "default-env")
    il.set_actor("Override")
    assert il.get_actor() == "Override"

    il.set_actor(None)
    assert il.get_actor() == "default-env"


def test_set_actor_string_vacio_o_whitespace_resetea(il, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_ACTOR", "default-env")
    il.set_actor("X")
    il.set_actor("")
    assert il.get_actor() == "default-env"

    il.set_actor("X")
    il.set_actor("   ")
    assert il.get_actor() == "default-env"


def test_set_actor_normaliza_whitespace(il):
    il.set_actor("   Marta Reynares   ")
    assert il.get_actor() == "Marta Reynares"


# ---------------------------------------------------------------------------
# _default_actor — env var, os.getlogin, fallback
# ---------------------------------------------------------------------------

def test_default_actor_lee_env_var_feesdefender(il, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_ACTOR", "Bot CI")
    assert il._default_actor() == "Bot CI"


def test_default_actor_normaliza_whitespace_en_env(il, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_ACTOR", "  CI Bot  ")
    assert il._default_actor() == "CI Bot"


def test_default_actor_sin_env_usa_getlogin(il, monkeypatch):
    """Sin ``FEESDEFENDER_ACTOR`` → ``os.getlogin()`` (no asserto el valor)."""
    monkeypatch.delenv("FEESDEFENDER_ACTOR", raising=False)
    actor = il._default_actor()
    assert isinstance(actor, str) and actor    # str no vacía


def test_default_actor_fallback_system_si_getlogin_falla(il, monkeypatch):
    """Si ``os.getlogin()`` lanza OSError → fallback "system"."""
    monkeypatch.delenv("FEESDEFENDER_ACTOR", raising=False)

    def fake_getlogin():
        raise OSError("no tty")

    monkeypatch.setattr("core.intake_log.os.getlogin", fake_getlogin)
    assert il._default_actor() == "system"


# ---------------------------------------------------------------------------
# read_events — lectura, vacíos, líneas corruptas
# ---------------------------------------------------------------------------

def test_read_events_log_inexistente(il, cm):
    cm.ensure_case("LOG-8")
    assert il.read_events("LOG-8") == []


def test_read_events_log_vacio(il, cm):
    cm.ensure_case("LOG-9")
    il.log_path("LOG-9").write_text("", encoding="utf-8")
    assert il.read_events("LOG-9") == []


def test_read_events_salta_lineas_corruptas(il, cm):
    """JSON inválido o no-dict → línea se salta silenciosamente."""
    cm.ensure_case("LOG-10")
    il.set_actor("Tester")

    il.append_event("LOG-10", "upload_manual", details={"i": 1})
    # Inyectamos basura intermedia
    with open(il.log_path("LOG-10"), "a", encoding="utf-8") as f:
        f.write("esto no es json\n")
        f.write('"solo un string"\n')   # JSON válido pero no dict
        f.write("null\n")               # JSON válido pero no dict
        f.write("\n")                   # línea en blanco
    il.append_event("LOG-10", "upload_manual", details={"i": 2})

    events = il.read_events("LOG-10")
    assert [e["details"]["i"] for e in events] == [1, 2]


# ---------------------------------------------------------------------------
# log_path — sólo computa, no crea
# ---------------------------------------------------------------------------

def test_log_path_no_crea_el_archivo(il, cm, tmp_casos_root):
    cm.ensure_case("LOG-11")
    path = il.log_path("LOG-11")
    assert path == tmp_casos_root / "LOG-11" / "00_Input" / "_intake_log.jsonl"
    assert not path.exists()


# ---------------------------------------------------------------------------
# fsync — resiliencia a crashes (M10-Q4)
# ---------------------------------------------------------------------------

def test_append_event_invoca_fsync_por_cada_escritura(il, cm, monkeypatch):
    """``os.fsync`` debe llamarse exactamente 1 vez por cada ``append_event``.

    Protege contra una regresión silenciosa: si alguien elimina la línea
    ``f.flush(); os.fsync(...)``, la prueba documental dejaría de ser
    resistente a crashes y este test fallaría.
    """
    cm.ensure_case("LOG-12")
    fsync_calls: list[int] = []

    real_fsync = il.os.fsync

    def counting_fsync(fd):
        fsync_calls.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr("core.intake_log.os.fsync", counting_fsync)

    il.append_event("LOG-12", "upload_manual")
    il.append_event("LOG-12", "upload_manual")
    il.append_event("LOG-12", "upload_manual")

    assert len(fsync_calls) == 3


# ---------------------------------------------------------------------------
# INTAKE_EVENTS — sanity
# ---------------------------------------------------------------------------

def test_intake_events_es_frozenset_con_15_eventos(il):
    assert isinstance(il.INTAKE_EVENTS, frozenset)
    assert len(il.INTAKE_EVENTS) == 15


def test_intake_events_contiene_los_canonicos(il):
    """Eventos documentados en project_intake_estructura_v2.md (M10-Q1).

    Los dos últimos (intake_judicial, pendiente_revision) se añadieron con
    el intake judicial automático (2026-06-10).
    """
    expected = {
        "link_expediente",
        "unlink_expediente",
        "pull_crm",
        "pull_drive_ev",
        "upload_manual",
        "upload_email",
        "upload_whatsapp",
        "upload_entrevista",
        "dedup_skipped",
        "category_unknown",
        "overwrite_doc",
        "delete_doc",
        "migrate_v1_v2",
        "intake_judicial",
        "pendiente_revision",
    }
    assert il.INTAKE_EVENTS == expected
