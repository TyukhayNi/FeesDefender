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


FOLDER_MIME = "application/vnd.google-apps.folder"


def test_create_folder():
    svc = FakeService(files={"create": {"id": "c1", "name": "06_Entrevistas",
                                        "mimeType": FOLDER_MIME}})
    out = drive_ops.create_folder(svc, name="06_Entrevistas", parent_id="P1")
    assert out["id"] == "c1"
    _, kw = svc.recorded("files")[0]
    assert kw["body"]["mimeType"] == FOLDER_MIME
    assert kw["body"]["parents"] == ["P1"]


def test_ensure_folder_path_crea_solo_lo_que_falta():
    # "A/B": A ya existe (list la encuentra), B no (list vacío -> create)
    svc = FakeService(files={
        "list": [
            {"files": [{"id": "A1", "name": "A", "mimeType": FOLDER_MIME}]},  # busca A
            {"files": []},                                                    # busca B bajo A1
        ],
        "create": {"id": "B1", "name": "B", "mimeType": FOLDER_MIME},
    })
    out = drive_ops.ensure_folder_path(svc, path="A/B", parent_id="ROOT")
    assert out["id"] == "B1"
    creates = [c for c in svc.recorded("files") if c[0] == "create"]
    assert len(creates) == 1
    assert creates[0][1]["body"]["parents"] == ["A1"]


def test_ensure_folder_path_todo_existe_no_crea():
    svc = FakeService(files={
        "list": [
            {"files": [{"id": "A1", "name": "A", "mimeType": FOLDER_MIME}]},
            {"files": [{"id": "B1", "name": "B", "mimeType": FOLDER_MIME}]},
        ],
    })
    out = drive_ops.ensure_folder_path(svc, path="A/B", parent_id="ROOT")
    assert out["id"] == "B1"
    creates = [c for c in svc.recorded("files") if c[0] == "create"]
    assert creates == []


def test_update_file_content_texto():
    svc = FakeService(files={"update": {"id": "f1", "name": "log.jsonl",
                                        "mimeType": "text/plain"}})
    out = drive_ops.update_file_content(svc, "f1", text="nuevo\n")
    assert out["id"] == "f1"
    assert out["sha256"] == hashlib.sha256(b"nuevo\n").hexdigest()
    _, kw = svc.recorded("files")[0]
    assert kw["fileId"] == "f1"
    assert "media_body" in kw
    assert kw["supportsAllDrives"] is True


def test_update_file_content_desde_ruta(tmp_path):
    src = tmp_path / "x.pdf"
    src.write_bytes(b"PDF")
    svc = FakeService(files={"update": {"id": "f2", "name": "x.pdf"}})
    out = drive_ops.update_file_content(svc, "f2", local_path=str(src))
    assert out["sha256"] == hashlib.sha256(b"PDF").hexdigest()


def test_update_file_content_exige_exactamente_uno():
    svc = FakeService(files={"update": {}})
    with pytest.raises(ValueError):
        drive_ops.update_file_content(svc, "f1")  # ni text ni local_path
    with pytest.raises(ValueError):
        drive_ops.update_file_content(svc, "f1", text="a", local_path="/x")


def test_update_file_metadata_renombra():
    svc = FakeService(files={"update": {"id": "f1", "name": "nuevo.pdf"}})
    out = drive_ops.update_file_metadata(svc, "f1", name="nuevo.pdf")
    assert out["name"] == "nuevo.pdf"
    _, kw = svc.recorded("files")[0]
    assert kw["body"] == {"name": "nuevo.pdf"}
    assert kw["fileId"] == "f1"


def test_move_file_calcula_remove_parents():
    svc = FakeService(files={
        "get": {"id": "f1", "parents": ["OLD"]},
        "update": {"id": "f1", "name": "x", "parents": ["NEW"]},
    })
    out = drive_ops.move_file(svc, "f1", dst_folder_id="NEW")
    assert out["id"] == "f1"
    upd = [c for c in svc.recorded("files") if c[0] == "update"][0][1]
    assert upd["addParents"] == "NEW"
    assert upd["removeParents"] == "OLD"
    assert upd["fileId"] == "f1"


def test_copy_file_con_nuevo_nombre():
    svc = FakeService(files={"copy": {"id": "c1", "name": "copia.pdf",
                                      "webViewLink": "https://drive/c1"}})
    out = drive_ops.copy_file(svc, "f1", dst_folder_id="DST", new_name="copia.pdf")
    assert out["id"] == "c1"
    _, kw = svc.recorded("files")[0]
    assert kw["fileId"] == "f1"
    assert kw["body"]["parents"] == ["DST"]
    assert kw["body"]["name"] == "copia.pdf"
    assert kw["supportsAllDrives"] is True


def test_copy_file_sin_nombre_no_pone_name():
    svc = FakeService(files={"copy": {"id": "c1"}})
    drive_ops.copy_file(svc, "f1", dst_folder_id="DST")
    _, kw = svc.recorded("files")[0]
    assert "name" not in kw["body"]


def test_delete_file_a_papelera_por_defecto():
    svc = FakeService(files={"update": {"id": "f1", "trashed": True}})
    out = drive_ops.delete_file(svc, "f1")
    assert out["trashed"] is True
    _, kw = svc.recorded("files")[0]
    assert kw["body"] == {"trashed": True}
    assert all(c[0] != "delete" for c in svc.recorded("files"))


def test_delete_file_permanente_llama_delete():
    svc = FakeService(files={"delete": {}})
    out = drive_ops.delete_file(svc, "f1", permanent=True)
    assert out["permanently_deleted"] is True
    _, kw = svc.recorded("files")[0]
    assert kw["fileId"] == "f1"
    assert kw["supportsAllDrives"] is True


def test_restore_file_desmarca_trashed():
    svc = FakeService(files={"update": {"id": "f1", "trashed": False}})
    out = drive_ops.restore_file(svc, "f1")
    assert out["trashed"] is False
    _, kw = svc.recorded("files")[0]
    assert kw["body"] == {"trashed": False}


def test_append_text_concatena_y_reescribe():
    svc = FakeService(files={
        "get": {"id": "f1", "name": "log.jsonl", "mimeType": "text/plain", "size": "6"},
        "get_media": b"linea1\n",
        "update": {"id": "f1", "name": "log.jsonl", "mimeType": "text/plain"},
    })
    out = drive_ops.append_text(svc, "f1", "linea2\n")
    assert out["id"] == "f1"
    upd = [c for c in svc.recorded("files") if c[0] == "update"][0][1]
    assert "media_body" in upd


def test_append_text_rechaza_binario():
    svc = FakeService(files={
        "get": {"id": "b1", "name": "x.pdf", "mimeType": "application/pdf", "size": "10"},
    })
    with pytest.raises(ValueError):
        drive_ops.append_text(svc, "b1", "no")
