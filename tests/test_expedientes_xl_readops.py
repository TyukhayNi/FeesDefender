from pathlib import Path
import pytest
from plugins.expedientes_xl.readops import read_text, read_multiple, get_metadata, list_dir, iter_tree, tree, search_name, search_content, resolve_shortcut
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

def test_tree_cuenta_omitidos_por_profundidad(sandbox):
    root, zonas, caso = sandbox
    # doc.txt vive en caso/00_Input/ (profundidad 2) → fuera con max_depth=1
    t = tree([root], zonas, str(caso), max_depth=1)
    assert not any(e.endswith("doc.txt") for e in t["entries"])
    assert t["omitidos_profundidad"] >= 1
    # sin límite que muerda: la clave existe siempre y vale 0
    t2 = tree([root], zonas, str(caso))
    assert t2["omitidos_profundidad"] == 0

def test_search_name_case_insensitive(sandbox):
    root, zonas, caso = sandbox
    # patrón en MAYÚSCULAS debe matchear doc.txt (nombre en minúsculas)
    hits = search_name([root], zonas, str(caso), "*.TXT")
    assert any(h.endswith("doc.txt") for h in hits)
    # y nombre en MAYÚSCULAS debe matchear patrón en minúsculas
    (caso / "00_Input" / "INFORME.TXT").write_text("x", encoding="utf-8")
    hits2 = search_name([root], zonas, str(caso), "informe.*")
    assert any(h.endswith("INFORME.TXT") for h in hits2)


class ColdOracle(FakeOracle):
    def __init__(self, cold_names):
        self.cold = cold_names
    def status(self, p):
        return "COLD" if p.name in self.cold else "HOT"


def test_search_content_basico(sandbox):
    root, zonas, caso = sandbox
    res = search_content([root], zonas, FakeOracle(), str(caso), "l3")
    assert res["matches"][0]["line"] == 3 and res["matches"][0]["text"] == "l3"
    assert res["podados"] == 1                       # 90_Notas fuera
    assert not any("secreto" in m["path"] for m in res["matches"])


def test_search_content_omite_cold_grande(sandbox, monkeypatch):
    root, zonas, caso = sandbox
    monkeypatch.setenv("XL_HYDRATION_MAX_FILE_MB", "0")   # todo grande
    res = search_content([root], zonas, ColdOracle({"doc.txt"}), str(caso), "l3")
    assert res["matches"] == []
    assert any(o.endswith("doc.txt") for o in res["omitidos_cold"])


def test_search_content_salta_binarios(sandbox):
    root, zonas, caso = sandbox
    (caso / "bin.dat").write_bytes(b"l3\x00binario")
    res = search_content([root], zonas, FakeOracle(), str(caso), "l3")
    assert not any(m["path"].endswith("bin.dat") for m in res["matches"])


def test_search_content_no_excluye_dotfiles(sandbox):
    root, zonas, caso = sandbox
    # un dotfile legítimo (.gitignore) SÍ entra en la búsqueda: el salto .g*
    # es solo para documentos nativos de Google (por sufijo, via check_gdoc)
    (caso / ".gitignore").write_text("patron_buscado\n", encoding="utf-8")
    res = search_content([root], zonas, FakeOracle(), str(caso), "patron_buscado")
    assert any(m["path"].endswith(".gitignore") for m in res["matches"])


def test_search_content_regex(sandbox):
    root, zonas, caso = sandbox
    res = search_content([root], zonas, FakeOracle(), str(caso), "l[0-9]", regex=True)
    assert any(m["text"] == "l3" for m in res["matches"])


def test_search_content_regex_invalida(sandbox):
    root, zonas, caso = sandbox
    with pytest.raises(ValueError, match="regex inválida"):
        search_content([root], zonas, FakeOracle(), str(caso), "[", regex=True)


def test_resolve_shortcut_revalida(sandbox):
    root, zonas, caso = sandbox
    lnk = caso / "atajo.lnk"; lnk.write_bytes(b"fake")
    ok = resolve_shortcut([root], zonas, str(lnk),
                          _resolver_lnk=lambda p: str(caso / "00_Input" / "doc.txt"))
    assert ok["dentro_sandbox"] is True and ok["tier"] == 1

    fuera = resolve_shortcut([root], zonas, str(lnk),
                             _resolver_lnk=lambda p: r"C:\Windows\System32\cmd.exe")
    assert fuera["dentro_sandbox"] is False and fuera["target"] is None

    tier0 = resolve_shortcut([root], zonas, str(lnk),
                             _resolver_lnk=lambda p: str(caso / "90_Notas personales" / "s.txt"))
    assert tier0["dentro_sandbox"] is False and tier0["target"] is None


def test_resolve_shortcut_nombre_con_comilla(sandbox):
    # Un .lnk cuyo NOMBRE lleva comilla simple se resuelve sin romperse: con el
    # paso de ruta por variable de entorno el lado Python no cita nada.
    root, zonas, caso = sandbox
    lnk = caso / "caso'X.lnk"; lnk.write_bytes(b"fake")
    ok = resolve_shortcut([root], zonas, str(lnk),
                          _resolver_lnk=lambda p: str(caso / "00_Input" / "doc.txt"))
    assert ok["dentro_sandbox"] is True and ok["tier"] == 1


def test_resolve_shortcut_falla_cerrado_en_timeout(sandbox, tmp_path, monkeypatch):
    # Si el resolver lanza (TimeoutExpired/OSError), resolve_shortcut falla
    # cerrado: forma None, audita "resolucion_fallida", ninguna excepción escapa.
    import json
    import subprocess as _sp
    from plugins.expedientes_xl.readops import resolve_shortcut as _rs
    log = tmp_path / "audit.jsonl"
    monkeypatch.setenv("XL_AUDIT_PATH", str(log))
    root, zonas, caso = sandbox
    lnk = caso / "atajo.lnk"; lnk.write_bytes(b"fake")

    def _boom(p):
        raise _sp.TimeoutExpired(cmd="powershell", timeout=15)

    res = _rs([root], zonas, str(lnk), _resolver_lnk=_boom)
    assert res == {"target": None, "dentro_sandbox": False, "tier": None}
    eventos = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
    assert any(e["resultado"] == "resolucion_fallida" for e in eventos)
