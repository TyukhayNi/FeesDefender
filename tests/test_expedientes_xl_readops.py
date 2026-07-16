from pathlib import Path
import pytest
from plugins.expedientes_xl.readops import read_text, read_multiple, get_metadata, list_dir, iter_tree, tree, search_name
from plugins.expedientes_xl.tiers import Zonas, TierViolation
from plugins.expedientes_xl.guards import GDocBloqueado

class FakeOracle:
    def status(self, p): return "HOT"
    def subtree_cold_stats(self, p): return (0, 0)

@pytest.fixture
def sandbox(tmp_path):
    caso = tmp_path / "CASOS" / "Caso1"
    (caso / "00_Input").mkdir(parents=True)
    (caso / "90_Notas personales").mkdir()
    # newline="" evita que write_text traduzca \n -> \r\n en Windows (rompería
    # el size==12 de test_get_metadata, que comprueba bytes en disco).
    (caso / "00_Input" / "doc.txt").write_text("l1\nl2\nl3\nl4\n", encoding="utf-8", newline="")
    (caso / "90_Notas personales" / "secreto.txt").write_text("privado", encoding="utf-8")
    (caso / "hoja.gsheet").write_text("{}", encoding="utf-8")
    zonas = Zonas(rw_roots=(tmp_path,))
    return tmp_path, zonas, caso

def test_read_text_y_head_tail(sandbox):
    root, zonas, caso = sandbox
    f = str(caso / "00_Input" / "doc.txt")
    assert read_text([root], zonas, FakeOracle(), f) == "l1\nl2\nl3\nl4\n"
    assert read_text([root], zonas, FakeOracle(), f, head=2) == "l1\nl2\n"
    assert read_text([root], zonas, FakeOracle(), f, tail=1) == "l4\n"

def test_read_text_bloquea_tier0_y_gdoc(sandbox):
    root, zonas, caso = sandbox
    with pytest.raises(TierViolation):
        read_text([root], zonas, FakeOracle(), str(caso / "90_Notas personales" / "secreto.txt"))
    with pytest.raises(GDocBloqueado):
        read_text([root], zonas, FakeOracle(), str(caso / "hoja.gsheet"))

def test_read_multiple_aisla_errores(sandbox):
    root, zonas, caso = sandbox
    res = read_multiple([root], zonas, FakeOracle(),
                        [str(caso / "00_Input" / "doc.txt"), str(caso / "no_existe.txt")])
    assert res[str(caso / "00_Input" / "doc.txt")].startswith("l1")
    assert res[str(caso / "no_existe.txt")].startswith("ERROR:")

def test_get_metadata(sandbox):
    root, zonas, caso = sandbox
    m = get_metadata([root], zonas, FakeOracle(), str(caso / "00_Input" / "doc.txt"))
    assert m["name"] == "doc.txt" and m["tier"] == 1 and m["hydration"] == "HOT"
    assert m["size"] == 12 and m["is_dir"] is False

def test_list_dir_poda_tier0(sandbox):
    root, zonas, caso = sandbox
    entradas = list_dir([root], zonas, str(caso))
    nombres = [e["name"] for e in entradas if "name" in e]
    assert "00_Input" in nombres and "hoja.gsheet" in nombres
    assert "90_Notas personales" not in nombres
    assert entradas[-1].get("_podados") == 1

def test_read_text_head_tail_cero(sandbox):
    root, zonas, caso = sandbox
    f = str(caso / "00_Input" / "doc.txt")
    assert read_text([root], zonas, FakeOracle(), f, head=0) == ""
    assert read_text([root], zonas, FakeOracle(), f, tail=0) == ""

def test_read_text_cap_trunca_y_tail_real(sandbox, monkeypatch):
    root, zonas, caso = sandbox
    f = str(caso / "00_Input" / "doc.txt")  # 12 bytes: l1\nl2\nl3\nl4\n
    monkeypatch.setenv("XL_READ_MAX_BYTES", "4")
    completo = read_text([root], zonas, FakeOracle(), f)
    assert completo.startswith("l1\nl")
    assert "[TRUNCADO: mostrados 4 de 12 bytes" in completo
    # tail lee desde el FINAL real, no desde el prefijo del cap
    assert read_text([root], zonas, FakeOracle(), f, tail=1) == "l4\n"

def test_list_dir_sizes(sandbox):
    root, zonas, caso = sandbox
    entradas = list_dir([root], zonas, str(caso / "00_Input"), sizes=True)
    doc = next(e for e in entradas if e.get("name") == "doc.txt")
    assert doc["size"] == 12

def test_list_dir_max_entries_trunca(sandbox):
    root, zonas, caso = sandbox
    entradas = list_dir([root], zonas, str(caso), max_entries=1)
    nombres = [e["name"] for e in entradas if "name" in e]
    assert nombres == ["00_Input"]
    assert any(e.get("_truncado") for e in entradas)
    assert entradas[-1].get("_podados") == 1  # _podados sigue siendo el último

def test_get_metadata_bloquea_tier0(sandbox):
    root, zonas, caso = sandbox
    with pytest.raises(TierViolation):
        get_metadata([root], zonas, FakeOracle(),
                     str(caso / "90_Notas personales" / "secreto.txt"))

def test_read_multiple_aisla_tier_violation(sandbox):
    root, zonas, caso = sandbox
    ok = str(caso / "00_Input" / "doc.txt")
    tier0 = str(caso / "90_Notas personales" / "secreto.txt")
    res = read_multiple([root], zonas, FakeOracle(), [ok, tier0])
    assert res[ok].startswith("l1")
    assert res[tier0].startswith("ERROR:")

def test_iter_tree_poda_tier0(sandbox):
    root, zonas, caso = sandbox
    podas = []
    vistos = [p.name for p in iter_tree(zonas, caso, on_prune=podas.append)]
    assert "doc.txt" in vistos and "secreto.txt" not in vistos
    assert len(podas) == 1 and podas[0].name == "90_Notas personales"

def test_tree_estructura(sandbox):
    root, zonas, caso = sandbox
    t = tree([root], zonas, str(caso))
    assert any(e.endswith("doc.txt") for e in t["entries"])
    assert t["podados"] == 1 and t["truncado"] is False

def test_search_name(sandbox):
    root, zonas, caso = sandbox
    hits = search_name([root], zonas, str(caso), "*.txt")
    assert any(h.endswith("doc.txt") for h in hits)
    assert not any("secreto" in h for h in hits)   # Tier 0 podado
