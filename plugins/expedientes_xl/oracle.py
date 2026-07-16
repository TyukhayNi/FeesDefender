"""Oráculo de hidratación HOT/COLD sobre la BD interna de GDFD.

OPCIONAL y fail-closed: si la BD no está o el esquema cambió, todo es UNKNOWN
(los guards lo tratan como COLD). Snapshot vía SQLite online backup API con
caché TTL (~5 s): un backup() por ráfaga, no por operación (anti-thrashing).
Spec §4.1. La BD es privada de Google: NUNCA depender de ella para corrección.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
from pathlib import Path

_VIRTUALES = {"unidades compartidas", "mi unidad", "otros ordenadores"}


def _varints(blob: bytes) -> set[int]:
    """Decodifica varints (protobuf-like) de un blob de `content-entry`.

    Heurística de cruce: los content_id embebidos en el blob suelen coincidir
    con nombres de fichero en la caché de contenido local (`content_cache`).
    """
    out: set[int] = set()
    val = shift = 0
    for b in blob:
        val |= (b & 0x7F) << shift
        if b & 0x80:
            shift += 7
        else:
            if val > 1000:
                out.add(val)
            val = shift = 0
    return out


class Oracle:
    def __init__(self, dbs: dict[str, Path], cache_dirs: dict[str, Path],
                 ttl: float | None = None) -> None:
        self._dbs = {k: Path(v) for k, v in dbs.items()}
        self._cache_dirs = {k: Path(v) for k, v in cache_dirs.items()}
        self._ttl = ttl if ttl is not None else float(os.environ.get("XL_ORACLE_TTL", "5"))
        self._snap: dict[str, tuple[float, sqlite3.Connection | None, str | None]] = {}
        self._cache_names: dict[str, tuple[float, frozenset[str]]] = {}
        self.refresh_count = 0

    def _snapshot(self, root: str) -> sqlite3.Connection | None:
        ahora = time.monotonic()
        cacheado = self._snap.get(root)
        if cacheado and ahora - cacheado[0] < self._ttl:
            return cacheado[1]
        con: sqlite3.Connection | None = None
        tmp: str | None = None
        src: sqlite3.Connection | None = None
        dst: sqlite3.Connection | None = None
        try:
            src = sqlite3.connect(f"file:{self._dbs[root]}?mode=ro", uri=True, timeout=8)
            fd, tmp = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            dst = sqlite3.connect(tmp)
            src.backup(dst)
            src.close()
            con = dst
            self.refresh_count += 1
        except (sqlite3.Error, OSError, KeyError):
            # Oráculo caído -> UNKNOWN (fail-closed en guards). Limpieza best-effort:
            # cerrar handles a medias y borrar el temporal (en Windows exige dst
            # cerrado primero); esta rama nunca debe lanzar.
            for handle in (dst, src):
                if handle is not None:
                    try:
                        handle.close()
                    except sqlite3.Error:
                        pass
            if tmp is not None:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            con, tmp = None, None
        if cacheado:
            if cacheado[1] is not None and cacheado[1] is not con:
                try:
                    cacheado[1].close()
                except sqlite3.Error:
                    pass
            if cacheado[2] is not None and cacheado[2] != tmp:
                try:
                    os.unlink(cacheado[2])  # tras cerrar la conexión (Windows)
                except OSError:
                    pass
        self._snap[root] = (ahora, con, tmp)
        return con

    def _root_de(self, path: Path) -> str | None:
        s = str(path)
        for root in self._dbs:
            if s.upper().startswith(root.upper()):
                return root
        return None

    def _resolver(self, con: sqlite3.Connection, path: Path) -> int | None:
        """stable_id del path por ascendencia de títulos; None = no resoluble."""
        segs = [p for p in path.parts[1:] if p.lower() not in _VIRTUALES]
        if not segs:
            return None
        leaf = segs[-1]
        ancestros = [s.lower() for s in segs[:-1]]
        if not ancestros:
            # Fichero directo en la raíz (tras quitar niveles virtuales): sin
            # ancestros no hay verificación de ubicación posible — cualquier leaf
            # homónimo casaría vacuamente. Fail-closed: UNKNOWN (trade-off: los
            # ficheros a nivel de raíz nunca se resuelven por el oráculo).
            return None
        candidatos = [r[0] for r in con.execute(
            "SELECT stable_id FROM items WHERE local_title = ? AND is_tombstone = 0 AND trashed = 0",
            (leaf,))]
        resueltos = []
        for sid in candidatos:
            cadena: list[str] = []
            actual = sid
            for _ in range(64):  # tope de profundidad
                fila = con.execute(
                    "SELECT p.parent_stable_id, i.local_title FROM stable_parents p "
                    "JOIN items i ON i.stable_id = p.parent_stable_id "
                    "WHERE p.item_stable_id = ?", (actual,)).fetchone()
                if fila is None:
                    break
                actual = fila[0]
                cadena.append((fila[1] or "").lower())
            # la cadena (leaf->raíz) debe contener los ancestros del path como sufijo
            if cadena[: len(ancestros)] == list(reversed(ancestros)):
                resueltos.append(sid)
        return resueltos[0] if len(resueltos) == 1 else None

    def _nombres_cache(self, root: str) -> frozenset[str]:
        ahora = time.monotonic()
        c = self._cache_names.get(root)
        if c and ahora - c[0] < self._ttl:
            return c[1]
        nombres: set[str] = set()
        base = self._cache_dirs.get(root)
        if base and base.is_dir():
            for r, _dirs, files in os.walk(base):
                nombres.update(files)
        fz = frozenset(nombres)
        self._cache_names[root] = (ahora, fz)
        return fz

    def status(self, path: Path) -> str:
        root = self._root_de(path)
        if root is None:
            return "UNKNOWN"
        con = self._snapshot(root)
        if con is None:
            return "UNKNOWN"
        try:
            sid = self._resolver(con, path)
            if sid is None:
                return "UNKNOWN"
            fila = con.execute(
                "SELECT value FROM item_properties WHERE item_stable_id = ? AND key = 'content-entry'",
                (sid,)).fetchone()
            if fila is None:
                return "COLD"
            if os.environ.get("XL_ORACLE_STRICT") == "1":
                ids = _varints(fila[0])
                nombres = self._nombres_cache(root)
                if not any(str(i) in nombres for i in ids):
                    return "COLD"
            return "HOT"
        except Exception:
            # La BD de GDFD es dato externo NO fiable: cualquier fallo (esquema
            # cambiado, valores malformados, tipos inesperados) -> UNKNOWN,
            # nunca una excepción hacia el llamante (fail-closed total).
            return "UNKNOWN"

    def subtree_cold_stats(self, path: Path) -> tuple[int, int] | None:
        """(n_cold, n_total) de FICHEROS bajo `path`, recursivo; None = no resoluble/caído."""
        root = self._root_de(path)
        if root is None:
            return None
        con = self._snapshot(root)
        if con is None:
            return None
        try:
            sid = self._resolver(con, path)
            if sid is None:
                return None
            pendientes, ficheros = [sid], []
            while pendientes:
                actual = pendientes.pop()
                for hijo, es_dir in con.execute(
                    "SELECT p.item_stable_id, i.is_folder FROM stable_parents p "
                    "JOIN items i ON i.stable_id = p.item_stable_id "
                    "WHERE p.parent_stable_id = ? AND i.is_tombstone = 0 AND i.trashed = 0",
                        (actual,)):
                    (pendientes if es_dir else ficheros).append(hijo)
            if not ficheros:
                return (0, 0)
            marca = ",".join("?" * len(ficheros))
            hot = con.execute(
                f"SELECT count(DISTINCT item_stable_id) FROM item_properties "
                f"WHERE key='content-entry' AND item_stable_id IN ({marca})",
                ficheros).fetchone()[0]
            return (len(ficheros) - hot, len(ficheros))
        except Exception:
            # Misma doctrina fail-closed que status(): dato externo no fiable.
            return None


def descubrir_cuentas(drivefs_dir: Path, roots: dict[str, Path]
                      ) -> tuple[dict[str, Path], dict[str, Path]]:
    """Mapea letra->BD casando nombres de unidades compartidas contra local_title.

    Casa (>=2 nombres de carpeta bajo `<raíz>\\Unidades compartidas`) contra
    `items.local_title` de cada `metadata_sqlite_db` de cuenta (subdirectorios
    numéricos de `drivefs_dir`). Cuenta sin match para una letra -> se omite
    (el oráculo de esa letra queda caído -> UNKNOWN, fail-closed).
    """
    dbs: dict[str, Path] = {}
    caches: dict[str, Path] = {}
    if not Path(drivefs_dir).is_dir():
        return dbs, caches
    cuentas = [d for d in drivefs_dir.iterdir()
               if d.is_dir() and d.name.isdigit() and (d / "metadata_sqlite_db").exists()]
    for root, base in roots.items():
        uc = Path(base) / "Unidades compartidas"
        marcadores = [p.name for p in uc.iterdir() if p.is_dir()][:10] if uc.is_dir() else []
        if len(marcadores) < 2:
            continue
        for cuenta in cuentas:
            try:
                con = sqlite3.connect(f"file:{cuenta / 'metadata_sqlite_db'}?mode=ro",
                                      uri=True, timeout=8)
                hits = sum(
                    1 for m in marcadores
                    if con.execute("SELECT 1 FROM items WHERE local_title=? LIMIT 1",
                                   (m,)).fetchone())
                con.close()
            except sqlite3.Error:
                continue
            if hits >= 2:
                dbs[root] = cuenta / "metadata_sqlite_db"
                caches[root] = cuenta / "content_cache"
                break
    return dbs, caches
