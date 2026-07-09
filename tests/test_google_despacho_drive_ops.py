"""Tests de drive_ops con FakeService inyectado (sin API viva)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # para google_despacho_fakes
from google_despacho_fakes import FakeService  # noqa: E402

from plugins.google_despacho_mcp import drive_ops  # noqa: E402


def test_list_shared_drives_pagina():
    svc = FakeService(drives={"list": [
        {"drives": [{"id": "d1", "name": "EXPEDIENTES"}], "nextPageToken": "T"},
        {"drives": [{"id": "d2", "name": "OTRA"}]},
    ]})
    out = drive_ops.list_shared_drives(svc)
    assert [d["id"] for d in out] == ["d1", "d2"]
    # segunda llamada llevó el pageToken
    assert svc.recorded("drives")[1][1].get("pageToken") == "T"


def test_search_files_pone_flags_alldrives():
    svc = FakeService(files={"list": {"files": [{"id": "f1", "name": "a.pdf"}]}})
    out = drive_ops.search_files(svc, "name contains 'a'")
    assert out == [{"id": "f1", "name": "a.pdf"}]
    _, kw = svc.recorded("files")[0]
    assert kw["includeItemsFromAllDrives"] is True
    assert kw["supportsAllDrives"] is True
    assert kw["corpora"] == "allDrives"
    assert kw["q"] == "name contains 'a'"
    assert "driveId" not in kw


def test_search_files_por_drive_id_usa_corpora_drive():
    svc = FakeService(files={"list": {"files": []}})
    drive_ops.search_files(svc, "x", drive_id="D123")
    _, kw = svc.recorded("files")[0]
    assert kw["corpora"] == "drive"
    assert kw["driveId"] == "D123"


def test_search_files_respeta_max_results_y_pagina():
    svc = FakeService(files={"list": [
        {"files": [{"id": "1"}, {"id": "2"}], "nextPageToken": "T"},
        {"files": [{"id": "3"}]},
    ]})
    out = drive_ops.search_files(svc, "x", page_size=2, max_results=3)
    assert [f["id"] for f in out] == ["1", "2", "3"]


def test_list_recent_files_ordena_por_modified():
    svc = FakeService(files={"list": {"files": [{"id": "f1"}]}})
    out = drive_ops.list_recent_files(svc, page_size=5)
    assert out == [{"id": "f1"}]
    _, kw = svc.recorded("files")[0]
    assert kw["orderBy"] == "modifiedTime desc"
    assert kw["q"] == "trashed = false"


def test_about_get():
    svc = FakeService(about={"get": {"user": {"emailAddress": "n@tyukhay.legal"}}})
    out = drive_ops.about_get(svc)
    assert out["user"]["emailAddress"] == "n@tyukhay.legal"


def test_get_file_metadata_pide_supports_alldrives():
    svc = FakeService(files={"get": {"id": "f1", "name": "x.pdf", "mimeType": "application/pdf"}})
    out = drive_ops.get_file_metadata(svc, "f1")
    assert out["id"] == "f1"
    _, kw = svc.recorded("files")[0]
    assert kw["fileId"] == "f1"
    assert kw["supportsAllDrives"] is True
    assert "sha256Checksum" in kw["fields"]


def test_get_file_permissions_pagina():
    svc = FakeService(permissions={"list": [
        {"permissions": [{"id": "p1", "type": "user", "role": "writer"}], "nextPageToken": "T"},
        {"permissions": [{"id": "p2", "type": "anyone", "role": "reader"}]},
    ]})
    out = drive_ops.get_file_permissions(svc, "f1")
    assert [p["id"] for p in out] == ["p1", "p2"]
    _, kw0 = svc.recorded("permissions")[0]
    assert kw0["fileId"] == "f1"
    assert kw0["supportsAllDrives"] is True


def test_read_file_content_doc_nativo_exporta_texto():
    svc = FakeService(files={
        "get": {"id": "g1", "name": "Nota", "mimeType": "application/vnd.google-apps.document"},
        "export_media": b"hola mundo",
    })
    out = drive_ops.read_file_content(svc, "g1")
    assert out["text"] == "hola mundo"
    assert out["mime_type"] == "application/vnd.google-apps.document"
    _, kw = svc.recorded("files")[-1]
    assert kw["mimeType"] == "text/plain"


def test_read_file_content_texto_plano():
    svc = FakeService(files={
        "get": {"id": "t1", "name": "a.txt", "mimeType": "text/plain", "size": "5"},
        "get_media": b"plano",
    })
    out = drive_ops.read_file_content(svc, "t1")
    assert out["text"] == "plano"


def test_read_file_content_binario_rechaza():
    svc = FakeService(files={
        "get": {"id": "b1", "name": "x.pdf", "mimeType": "application/pdf", "size": "10"},
    })
    with pytest.raises(ValueError):
        drive_ops.read_file_content(svc, "b1")


def test_download_file_content_binario_escribe_y_hashea(tmp_path):
    import hashlib as _h
    data = b"binario-de-prueba"
    svc = FakeService(files={
        "get": {"id": "b1", "name": "x.bin", "mimeType": "application/octet-stream", "size": str(len(data))},
        "get_media": data,
    })
    dest = tmp_path / "sub" / "x.bin"
    out = drive_ops.download_file_content(svc, "b1", str(dest))
    assert dest.read_bytes() == data
    assert out["bytes"] == len(data)
    assert out["sha256"] == _h.sha256(data).hexdigest()


def test_download_file_content_doc_nativo_default_pdf(tmp_path):
    svc = FakeService(files={
        "get": {"id": "g1", "name": "Doc", "mimeType": "application/vnd.google-apps.document"},
        "export_media": b"%PDF-1.4 fake",
    })
    dest = tmp_path / "doc.pdf"
    drive_ops.download_file_content(svc, "g1", str(dest))
    _, kw = svc.recorded("files")[-1]
    assert kw["mimeType"] == "application/pdf"
    assert dest.read_bytes() == b"%PDF-1.4 fake"


def test_download_file_content_keep_editable_office(tmp_path):
    svc = FakeService(files={
        "get": {"id": "g1", "name": "Doc", "mimeType": "application/vnd.google-apps.document"},
        "export_media": b"docx-bytes",
    })
    dest = tmp_path / "doc.docx"
    drive_ops.download_file_content(svc, "g1", str(dest), keep_editable=True)
    _, kw = svc.recorded("files")[-1]
    assert kw["mimeType"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_download_file_content_supera_max_bytes(tmp_path):
    data = b"x" * 100
    svc = FakeService(files={
        "get": {"id": "b1", "name": "x.bin", "mimeType": "application/octet-stream", "size": "100"},
        "get_media": data,
    })
    with pytest.raises(ValueError):
        drive_ops.download_file_content(svc, "b1", str(tmp_path / "x.bin"), max_bytes=10)


def test_download_file_content_export_supera_max_bytes(tmp_path):
    # Doc nativo: el tamaño real solo se conoce tras exportar → cubre el check post-fetch
    svc = FakeService(files={
        "get": {"id": "g1", "name": "Doc", "mimeType": "application/vnd.google-apps.document"},
        "export_media": b"x" * 100,
    })
    with pytest.raises(ValueError):
        drive_ops.download_file_content(svc, "g1", str(tmp_path / "doc.pdf"), max_bytes=10)


def test_read_file_content_export_supera_max_bytes():
    # Doc nativo exportado a texto: cubre el check post-fetch de max_bytes
    svc = FakeService(files={
        "get": {"id": "g1", "name": "Doc", "mimeType": "application/vnd.google-apps.document"},
        "export_media": b"x" * 100,
    })
    with pytest.raises(ValueError):
        drive_ops.read_file_content(svc, "g1", max_bytes=10)
