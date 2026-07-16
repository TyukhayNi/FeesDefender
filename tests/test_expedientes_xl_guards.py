from pathlib import Path
import pytest
from plugins.expedientes_xl.guards import (
    FileNotHydrated, GDocBloqueado, check_gdoc, guard_file, guard_tree,
)

class FakeOracle:
    def __init__(self, status="HOT", stats=(0, 10)):
        self._status, self._stats = status, stats
    def status(self, path): return self._status
    def subtree_cold_stats(self, path): return self._stats

def test_check_gdoc_bloquea():
    for ext in (".gdoc", ".gsheet", ".gslides"):
        with pytest.raises(GDocBloqueado, match="google-despacho"):
            check_gdoc(Path(f"G:/x{ext}"))
    check_gdoc(Path("G:/x.pdf"))  # no lanza

def test_guard_file_cold_grande_aborta(tmp_path, monkeypatch):
    monkeypatch.setenv("XL_HYDRATION_MAX_FILE_MB", "0")  # todo es "grande"
    f = tmp_path / "grande.bin"; f.write_bytes(b"x" * 10)
    with pytest.raises(FileNotHydrated) as ei:
        guard_file(FakeOracle("COLD"), f)
    assert str(f) in ei.value.omitidos
    with pytest.raises(FileNotHydrated):
        guard_file(FakeOracle("UNKNOWN"), f)   # fail-closed
    guard_file(FakeOracle("HOT"), f)            # HOT pasa

def test_guard_file_cold_pequeno_pasa(tmp_path, monkeypatch):
    monkeypatch.setenv("XL_HYDRATION_MAX_FILE_MB", "10")
    f = tmp_path / "peq.bin"; f.write_bytes(b"x")
    guard_file(FakeOracle("COLD"), f)  # pequeño: se permite (descarga corta)

def test_guard_tree_por_conteo(tmp_path, monkeypatch):
    monkeypatch.setenv("XL_TREE_MAX_COLD", "5")
    with pytest.raises(FileNotHydrated, match="51"):
        guard_tree(FakeOracle(stats=(51, 100)), tmp_path)
    guard_tree(FakeOracle(stats=(2, 100)), tmp_path)

def test_guard_tree_oraculo_caido_failclosed(tmp_path, monkeypatch):
    monkeypatch.setenv("XL_TREE_MAX_MB", "0")   # árbol siempre "grande"
    (tmp_path / "a.bin").write_bytes(b"x" * 10)
    with pytest.raises(FileNotHydrated):
        guard_tree(FakeOracle(stats=None), tmp_path)
