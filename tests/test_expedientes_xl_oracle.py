import sqlite3
import shutil
import tempfile
from pathlib import Path
import pytest
from plugins.expedientes_xl.oracle import Oracle, descubrir_cuentas

SCHEMA = """
CREATE TABLE items (stable_id INTEGER PRIMARY KEY, id TEXT, trashed INT DEFAULT 0,
  is_folder INT DEFAULT 0, is_tombstone INT DEFAULT 0, file_size INT DEFAULT 0,
  local_title TEXT, team_drive_stable_id INT);
CREATE TABLE item_properties (item_stable_id INT, key TEXT, value);
CREATE TABLE stable_parents (item_stable_id INT, parent_stable_id INT, local_title_hash TEXT);
CREATE TABLE shortcut_details (shortcut_stable_id INT, target_stable_id INT, target_mime_type TEXT);
"""

@pytest.fixture
def mini_db(tmp_path):
    db = tmp_path / "metadata_sqlite_db"
    con = sqlite3.connect(db)
    con.executescript(SCHEMA)
    # Árbol: TD (10) / Caso (20) / 00_Input (30) / hot.pdf (40), cold.pdf (50)
    filas = [(10, "td1", 1, "EXPEDIENTES - TYUKHAY LEGAL", None),
             (20, "c1", 1, "Caso X", 10), (30, "i1", 1, "00_Input", 10),
             (40, "h1", 0, "hot.pdf", 10), (50, "c2", 0, "cold.pdf", 10)]
    for sid, cid, isf, title, td in filas:
        con.execute("INSERT INTO items(stable_id,id,is_folder,local_title,team_drive_stable_id) VALUES (?,?,?,?,?)",
                    (sid, cid, isf, title, td))
    for hijo, padre in [(20, 10), (30, 20), (40, 30), (50, 30)]:
        con.execute("INSERT INTO stable_parents VALUES (?,?,'')", (hijo, padre))
    con.execute("INSERT INTO item_properties VALUES (40,'content-entry',X'0801')")
    con.commit(); con.close()
    cache = tmp_path / "content_cache"; cache.mkdir()
    return db, cache

def test_snapshot_ttl_no_repite_backup(mini_db, monkeypatch):
    db, cache = mini_db
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)
    con1 = o._snapshot("G:\\")
    con2 = o._snapshot("G:\\")
    assert con1 is con2 and o.refresh_count == 1
    assert con1.execute("SELECT count(*) FROM items").fetchone()[0] == 5

def test_snapshot_caido_devuelve_none(tmp_path):
    o = Oracle({"G:\\": tmp_path / "no_existe"}, {"G:\\": tmp_path}, ttl=5)
    assert o._snapshot("G:\\") is None


@pytest.fixture
def mkstemp_registrado(tmp_path, monkeypatch):
    """Redirige tempfile.mkstemp a tmp_path y registra las rutas creadas."""
    creados = []
    real_mkstemp = tempfile.mkstemp

    def _mkstemp(suffix=""):
        fd, ruta = real_mkstemp(suffix=suffix, dir=str(tmp_path))
        creados.append(ruta)
        return fd, ruta

    monkeypatch.setattr(tempfile, "mkstemp", _mkstemp)
    return creados


def test_refresh_borra_tmp_anterior(mini_db, mkstemp_registrado):
    db, cache = mini_db
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=0)  # ttl=0 -> refresco siempre
    con1 = o._snapshot("G:\\")
    con2 = o._snapshot("G:\\")
    assert con1 is not con2 and o.refresh_count == 2
    assert len(mkstemp_registrado) == 2
    assert not Path(mkstemp_registrado[0]).exists()  # tmp del snapshot anterior borrado
    assert Path(mkstemp_registrado[1]).exists()      # tmp del snapshot vigente sigue


def test_fallo_backup_limpia_tmp(mini_db, mkstemp_registrado, monkeypatch):
    db, cache = mini_db

    class SrcRoto:
        def backup(self, dst):
            raise sqlite3.Error("backup roto a mitad")

        def close(self):
            pass

    real_connect = sqlite3.connect

    def connect_falso(*args, **kwargs):
        if kwargs.get("uri"):
            return SrcRoto()
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", connect_falso)
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=5)
    assert o._snapshot("G:\\") is None
    assert o.refresh_count == 0
    # el temporal creado para el dst del backup fallido no queda huérfano
    assert len(mkstemp_registrado) == 1
    assert not Path(mkstemp_registrado[0]).exists()


def test_status_hot_cold_unknown(mini_db):
    db, cache = mini_db
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)
    base = r"G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\Caso X\00_Input"
    assert o.status(Path(base + r"\hot.pdf")) == "HOT"
    assert o.status(Path(base + r"\cold.pdf")) == "COLD"
    assert o.status(Path(base + r"\no_existe.pdf")) == "UNKNOWN"
    assert o.status(Path(r"Z:\fuera\x.pdf")) == "UNKNOWN"   # raíz sin BD


def test_status_oraculo_caido_unknown(tmp_path):
    o = Oracle({"G:\\": tmp_path / "no"}, {"G:\\": tmp_path}, ttl=5)
    assert o.status(Path(r"G:\Mi unidad\a.pdf")) == "UNKNOWN"


def test_status_ambiguo_unknown(mini_db):
    db, cache = mini_db
    con = __import__("sqlite3").connect(db)
    # duplicar el leaf bajo el MISMO padre (30 = 00_Input): ambos candidatos
    # casan la ascendencia completa -> 2 resueltos -> fail-closed
    con.execute("INSERT INTO items(stable_id,id,is_folder,local_title) VALUES (60,'d',0,'hot.pdf')")
    con.execute("INSERT INTO stable_parents VALUES (60,30,'')")
    con.commit(); con.close()
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)
    base = r"G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\Caso X\00_Input"
    assert o.status(Path(base + r"\hot.pdf")) == "UNKNOWN"  # 2 candidatos -> fail-closed


def test_status_strict_cruza_con_cache(mini_db, monkeypatch):
    monkeypatch.setenv("XL_ORACLE_STRICT", "1")
    db, cache = mini_db
    con = sqlite3.connect(db)
    # warm.pdf con content-entry cuyo varint decodifica a 2001 (0xD1 0x0F)
    con.execute("INSERT INTO items(stable_id,id,is_folder,local_title) VALUES (70,'w',0,'warm.pdf')")
    con.execute("INSERT INTO stable_parents VALUES (70,30,'')")
    con.execute("INSERT INTO item_properties VALUES (70,'content-entry',X'D10F')")
    con.commit(); con.close()
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)
    base = r"G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\Caso X\00_Input"
    # el blob de hot.pdf (X'0801') no decodifica ningun id >1000 -> sin match -> COLD
    assert o.status(Path(base + r"\hot.pdf")) == "COLD"
    # sin fichero "2001" en la cache -> COLD
    assert o.status(Path(base + r"\warm.pdf")) == "COLD"
    (cache / "2001").write_bytes(b"x")
    o2 = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)  # cache de nombres fresca
    assert o2.status(Path(base + r"\warm.pdf")) == "HOT"


def test_status_strict_blob_malformado_unknown(mini_db, monkeypatch):
    monkeypatch.setenv("XL_ORACLE_STRICT", "1")
    db, cache = mini_db
    con = sqlite3.connect(db)
    # content-entry con valor entero (no BLOB): _varints no puede iterarlo
    con.execute("INSERT INTO items(stable_id,id,is_folder,local_title) VALUES (90,'m',0,'mal.pdf')")
    con.execute("INSERT INTO stable_parents VALUES (90,30,'')")
    con.execute("INSERT INTO item_properties VALUES (90,'content-entry',12345)")
    con.commit(); con.close()
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)
    base = r"G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\Caso X\00_Input"
    assert o.status(Path(base + r"\mal.pdf")) == "UNKNOWN"  # sin excepción hacia fuera


def test_status_raiz_sin_ascendencia_unknown(mini_db):
    db, cache = mini_db
    con = sqlite3.connect(db)
    # leaf único a nivel de raíz de la unidad: sin ancestros no hay verificación
    con.execute("INSERT INTO items(stable_id,id,is_folder,local_title) VALUES (80,'s',0,'solo.pdf')")
    con.commit(); con.close()
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)
    assert o.status(Path(r"G:\solo.pdf")) == "UNKNOWN"  # fail-closed, no vacuo


def test_subtree_cold_stats(mini_db):
    db, cache = mini_db
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)
    base = r"G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\Caso X\00_Input"
    assert o.subtree_cold_stats(Path(base)) == (1, 2)   # cold.pdf de 2 ficheros
    assert o.subtree_cold_stats(Path(r"G:\no\existe")) is None


def test_descubrir_cuentas(mini_db, tmp_path, monkeypatch):
    db, cache = mini_db
    acct = tmp_path / "DriveFS" / "12345"
    acct.mkdir(parents=True)
    (acct / "content_cache").mkdir()
    shutil.copy2(db, acct / "metadata_sqlite_db")
    g = tmp_path / "G"; (g / "Unidades compartidas" / "EXPEDIENTES - TYUKHAY LEGAL").mkdir(parents=True)
    (g / "Unidades compartidas" / "Caso X").mkdir()   # 2º marcador
    dbs, caches = descubrir_cuentas(tmp_path / "DriveFS", {"G:\\": g})
    assert dbs == {"G:\\": acct / "metadata_sqlite_db"}
    assert caches == {"G:\\": acct / "content_cache"}


def test_descubrir_cuentas_bd_corrupta_cierra_handle(mini_db, tmp_path):
    # Cuenta con BD basura junto a la válida: la válida sigue mapeando, sin
    # excepción, Y el fichero basura se puede borrar después (en Windows un
    # handle filtrado haría que os.remove lanzara PermissionError).
    import os
    db, cache = mini_db
    mala = tmp_path / "DriveFS" / "111"
    mala.mkdir(parents=True)
    (mala / "metadata_sqlite_db").write_bytes(b"no es sqlite")
    buena = tmp_path / "DriveFS" / "222"
    buena.mkdir()
    (buena / "content_cache").mkdir()
    shutil.copy2(db, buena / "metadata_sqlite_db")
    g = tmp_path / "G"; (g / "Unidades compartidas" / "EXPEDIENTES - TYUKHAY LEGAL").mkdir(parents=True)
    (g / "Unidades compartidas" / "Caso X").mkdir()
    dbs, caches = descubrir_cuentas(tmp_path / "DriveFS", {"G:\\": g})
    assert dbs == {"G:\\": buena / "metadata_sqlite_db"}
    assert caches == {"G:\\": buena / "content_cache"}
    os.remove(mala / "metadata_sqlite_db")   # handle liberado -> no PermissionError


def test_descubrir_cuentas_sin_drivefs_dir(tmp_path):
    # DriveFS ausente de la máquina (p.ej. Drive no instalado): sin excepción,
    # dicts vacíos -> el oráculo de esa letra queda caído -> UNKNOWN.
    dbs, caches = descubrir_cuentas(tmp_path / "no_existe_DriveFS", {"G:\\": tmp_path})
    assert dbs == {}
    assert caches == {}
