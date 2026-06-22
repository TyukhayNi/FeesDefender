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
