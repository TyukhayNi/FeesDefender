from pathlib import Path
import pytest
from plugins.expedientes_xl.winio import (
    SharingViolation, atomic_write_bytes, atomic_write_text, long_path, retry_sharing,
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

def test_abrible_prefija_solo_rutas_largas(tmp_path):
    from plugins.expedientes_xl.winio import _abrible
    corta = tmp_path / "c.txt"
    assert _abrible(corta) == str(corta)                # corta: sin tocar
    larga = Path("C:\\" + "a" * 300 + "\\f.txt")
    assert _abrible(larga) == "\\\\?\\" + str(larga)    # larga: prefijada


def test_atomic_write_funciona_con_umbral_long_path_forzado(tmp_path, monkeypatch):
    """Fuerza la rama long_path (\\\\?\\) de atomic_write sin necesitar una ruta
    real >= MAX_PATH: mkstemp dir= y os.replace reciben la ruta prefijada."""
    import plugins.expedientes_xl.winio as w
    monkeypatch.setattr(w, "_LONG_PATH_UMBRAL", 1)
    f = tmp_path / "doc.txt"
    atomic_write_text(f, "v1")
    assert atomic_write_text(f, "v2") == 2              # reemplazo por la rama prefijada
    assert f.read_text(encoding="utf-8") == "v2"
    assert [p.name for p in tmp_path.iterdir()] == ["doc.txt"]  # sin tmp huérfanos


def test_long_path_prefija():
    assert long_path(Path(r"G:\Mi unidad\a.txt")).startswith("\\\\?\\")
    ya = "\\\\?\\G:\\a"
    assert long_path(Path(ya)) == ya

def test_long_path_unc():
    assert long_path(Path(r"\\server\share\a.txt")) == "\\\\?\\UNC\\server\\share\\a.txt"

def test_long_path_relativa_sin_tocar():
    assert long_path(Path(r"carpeta\a.txt")) == "carpeta\\a.txt"

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

def test_retry_sharing_agota_y_relanza(monkeypatch):
    import plugins.expedientes_xl.winio as w
    sleeps = []
    monkeypatch.setattr(w.time, "sleep", lambda s: sleeps.append(s))
    intentos = {"n": 0}
    ultima = {}
    def fn():
        intentos["n"] += 1
        e = PermissionError("locked"); e.winerror = 32
        ultima["e"] = e
        raise e
    with pytest.raises(SharingViolation) as exc:
        retry_sharing(fn)
    assert intentos["n"] == 3
    assert exc.value.__cause__ is ultima["e"]
    # sin sleep inútil tras el último intento fallido
    assert sleeps == [0.5, 1.0]

def test_retry_sharing_otro_winerror_propaga(monkeypatch):
    import plugins.expedientes_xl.winio as w
    monkeypatch.setattr(w.time, "sleep", lambda s: None)
    intentos = {"n": 0}
    def fn():
        intentos["n"] += 1
        e = PermissionError("acceso denegado"); e.winerror = 5
        raise e
    with pytest.raises(PermissionError):
        retry_sharing(fn)
    assert intentos["n"] == 1
