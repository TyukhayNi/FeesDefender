"""Tests de las operaciones de ESCRITURA de drive_ops con FakeService inyectado."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # para google_despacho_fakes
from google_despacho_fakes import FakeService  # noqa: E402

from plugins.google_despacho_mcp import drive_ops  # noqa: E402


def test_create_file_texto_devuelve_id_y_hash():
    svc = FakeService(files={"create": {
        "id": "n1", "name": "log.jsonl", "mimeType": "text/plain",
        "webViewLink": "https://drive/n1",
    }})
    out = drive_ops.create_file(svc, name="log.jsonl", parent_id="P1", text="hola\n")
    assert out["id"] == "n1"
    assert out["web_view_link"] == "https://drive/n1"
    assert out["sha256"] == hashlib.sha256("hola\n".encode("utf-8")).hexdigest()
    _, kw = svc.recorded("files")[0]
    assert kw["body"]["name"] == "log.jsonl"
    assert kw["body"]["parents"] == ["P1"]
    assert kw["supportsAllDrives"] is True
    assert "webViewLink" in kw["fields"]


def test_create_file_texto_supera_tope():
    svc = FakeService(files={"create": {"id": "n1"}})
    with pytest.raises(ValueError):
        drive_ops.create_file(svc, name="x", parent_id="P1", text="x" * 20,
                              max_text_bytes=10)


def test_upload_file_hashea_los_bytes_del_disco(tmp_path):
    data = b"%PDF-1.4 binario"
    src = tmp_path / "doc.pdf"
    src.write_bytes(data)
    svc = FakeService(files={"create": {
        "id": "u1", "name": "doc.pdf", "mimeType": "application/pdf",
        "webViewLink": "https://drive/u1",
    }})
    out = drive_ops.upload_file(svc, local_path=str(src), parent_id="P1")
    assert out["id"] == "u1"
    assert out["sha256"] == hashlib.sha256(data).hexdigest()
    _, kw = svc.recorded("files")[0]
    assert kw["body"]["name"] == "doc.pdf"
    assert kw["body"]["parents"] == ["P1"]
    assert "media_body" in kw
