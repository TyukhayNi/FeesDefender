import json
from pathlib import Path

from plugins.expedientes_xl import audit


def test_log_op_escribe_jsonl(tmp_path, monkeypatch):
    log = tmp_path / "sub" / "audit.jsonl"
    monkeypatch.setenv("XL_AUDIT_PATH", str(log))
    audit.log_op("write_text", r"G:\x.txt", "ok", hash_post="abc")
    audit.log_op("copy_dir", r"G:\y", "tier_violation", motivo="backup")
    lineas = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas) == 2
    ev = json.loads(lineas[0])
    assert ev["op"] == "write_text" and ev["hash_post"] == "abc" and "ts" in ev


def test_log_op_nunca_lanza(tmp_path, monkeypatch):
    # Fallo determinista: mkdir revienta -> log_op debe tragarse el error.
    monkeypatch.setenv("XL_AUDIT_PATH", str(tmp_path / "sub" / "audit.jsonl"))

    def _boom(*a, **k):
        raise OSError("boom")

    monkeypatch.setattr(audit.Path, "mkdir", _boom)
    audit.log_op("x", "y", "z")  # no debe lanzar


def test_log_op_extras_no_serializables(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setenv("XL_AUDIT_PATH", str(log))
    audit.log_op("x", "y", "z", objeto=Path("a/b"), conjunto={1, 2})  # no debe lanzar
    lineas = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas) == 1
    ev = json.loads(lineas[0])
    assert ev["objeto"] == str(Path("a/b"))
    assert ev["conjunto"] == str({1, 2})
