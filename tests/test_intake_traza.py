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
