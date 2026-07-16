import sqlite3
import tempfile
from pathlib import Path
import pytest
from plugins.expedientes_xl.oracle import Oracle

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
