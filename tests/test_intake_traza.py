import json
from pathlib import Path

import pytest

import importlib.util

_TRAZA = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "intake-expediente" / "scripts" / "traza.py"
_spec = importlib.util.spec_from_file_location("intake_traza", _TRAZA)
traza = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(traza)


def test_build_upload_event_estructura():
    line = traza.build_upload_event(
        case_id="BaRS1",
        event="upload_whatsapp",
        files=[{"path": "02_Whatsapp/00_Consultor propietario/chat/_chat.txt", "sha256": "abc123"}],
        actor="nikolai",
        ts="2026-06-22T10:00:00",
    )
    entry = json.loads(line)
    assert entry["ts"] == "2026-06-22T10:00:00"
    assert entry["actor"] == "nikolai"
    assert entry["event"] == "upload_whatsapp"
    assert entry["case_id"] == "BaRS1"
    assert entry["details"]["count"] == 1
    assert entry["details"]["files"][0]["sha256"] == "abc123"
    assert line.endswith("\n")


def test_build_upload_event_rechaza_evento_invalido():
    with pytest.raises(ValueError):
        traza.build_upload_event(
            case_id="X", event="evento_inventado", files=[], actor="a", ts="t"
        )


def test_is_duplicate_detecta_hash_previo():
    log = "".join([
        traza.build_upload_event(case_id="C", event="upload_manual",
                                  files=[{"path": "04_Manual/a.pdf", "sha256": "HASH_A"}],
                                  actor="a", ts="t1"),
        traza.build_upload_event(case_id="C", event="upload_email",
                                  files=[{"path": "03_Email/b.eml", "sha256": "HASH_B"}],
                                  actor="a", ts="t2"),
    ])
    assert traza.is_duplicate(log, "HASH_A") is True
    assert traza.is_duplicate(log, "HASH_NUEVO") is False


def test_is_duplicate_log_vacio_o_corrupto():
    assert traza.is_duplicate("", "X") is False
    assert traza.is_duplicate("no es json\n{tampoco\n", "X") is False


def test_paridad_eventos_subconjunto_de_core():
    from core import intake_log
    assert traza.UPLOAD_EVENTS <= intake_log.INTAKE_EVENTS, (
        "traza.UPLOAD_EVENTS tiene eventos que core.intake_log.INTAKE_EVENTS no reconoce"
    )


def test_paridad_shape_con_core(tmp_path, monkeypatch):
    """La línea de traza tiene las MISMAS claves que core.append_event escribe.

    `caso_path` delega en case_locator; para aislar el test de esa maquinaria,
    le pasamos el arbol del caso directamente (Task 8: `append_event` recibe
    el destino, asi que ya no hace falta parchear la resolucion de rutas).
    """
    import json as _json
    from core import intake_log

    # Ya no hace falta parchear nada para redirigir: `append_event` acepta el
    # arbol del caso, que es justo el punto del Task 8 (B0-1). Antes habia que
    # sustituir `log_path` porque la ruta se resolvia SIEMPRE por `CASOS_ROOT`.
    caso = tmp_path / "CASO_PARIDAD"
    (caso / "00_Input").mkdir(parents=True)
    logf = caso / "00_Input" / "_intake_log.jsonl"

    intake_log.append_event(
        caso, "upload_manual", case_id="CASO_PARIDAD",
        details={"count": 1, "files": [{"path": "04_Manual/a.pdf", "sha256": "H"}]},
        actor="a", ts="t",
    )
    core_entry = _json.loads(logf.read_text(encoding="utf-8").splitlines()[0])

    traza_entry = _json.loads(traza.build_upload_event(
        case_id="CASO_PARIDAD", event="upload_manual",
        files=[{"path": "04_Manual/a.pdf", "sha256": "H"}], actor="a", ts="t",
    ))

    assert set(core_entry.keys()) == set(traza_entry.keys())
    assert set(core_entry["details"].keys()) == set(traza_entry["details"].keys())
    assert core_entry == traza_entry
