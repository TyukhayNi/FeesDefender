from pathlib import Path
import pytest
from plugins.expedientes_xl.winio import (
    atomic_write_bytes, atomic_write_text, long_path, retry_sharing,
)

def test_atomic_write_crea_y_reemplaza(tmp_path):
    f = tmp_path / "doc.txt"
    assert atomic_write_text(f, "v1") == 2
    assert atomic_write_text(f, "v2-nuevo") == len("v2-nuevo")
    assert f.read_text(encoding="utf-8") == "v2-nuevo"
    # sin temporales huérfanos
    assert [p.name for p in tmp_path.iterdir()] == ["doc.txt"]

def test_atomic_write_no_deja_parcial_si_falla(tmp_path, monkeypatch):
    f = tmp_path / "doc.txt"
    atomic_write_text(f, "estable")
    import plugins.expedientes_xl.winio as w
    monkeypatch.setattr(w.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(OSError):
        atomic_write_text(f, "nuevo")
    assert f.read_text(encoding="utf-8") == "estable"          # destino intacto
    assert [p.name for p in tmp_path.iterdir()] == ["doc.txt"]  # tmp limpiado

def test_long_path_prefija():
    assert long_path(Path(r"G:\Mi unidad\a.txt")).startswith("\\\\?\\")
    ya = "\\\\?\\G:\\a"
    assert long_path(Path(ya)) == ya

def test_retry_sharing_reintenta(monkeypatch):
    import plugins.expedientes_xl.winio as w
    monkeypatch.setattr(w.time, "sleep", lambda s: None)
    intentos = {"n": 0}
    def fn():
        intentos["n"] += 1
        if intentos["n"] < 3:
            e = PermissionError("locked"); e.winerror = 32; raise e
        return "ok"
    assert retry_sharing(fn) == "ok"
    assert intentos["n"] == 3
