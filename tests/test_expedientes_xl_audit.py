import json
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


def test_log_op_nunca_lanza(monkeypatch):
    monkeypatch.setenv("XL_AUDIT_PATH", r"Z:\no\existe\audit.jsonl")
    audit.log_op("x", "y", "z")  # no debe lanzar
