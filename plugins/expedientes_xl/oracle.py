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


class Oracle:
    def __init__(self, dbs: dict[str, Path], cache_dirs: dict[str, Path],
                 ttl: float | None = None) -> None:
        self._dbs = {k: Path(v) for k, v in dbs.items()}
        self._cache_dirs = {k: Path(v) for k, v in cache_dirs.items()}
        self._ttl = ttl if ttl is not None else float(os.environ.get("XL_ORACLE_TTL", "5"))
        self._snap: dict[str, tuple[float, sqlite3.Connection | None]] = {}
        self._cache_names: dict[str, tuple[float, frozenset[str]]] = {}
        self.refresh_count = 0

    def _snapshot(self, root: str) -> sqlite3.Connection | None:
        ahora = time.monotonic()
        cacheado = self._snap.get(root)
        if cacheado and ahora - cacheado[0] < self._ttl:
            return cacheado[1]
        con: sqlite3.Connection | None = None
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
            con = None  # oráculo caído -> UNKNOWN (fail-closed en guards)
        if cacheado and cacheado[1] is not None and cacheado[1] is not con:
            try:
                cacheado[1].close()
            except sqlite3.Error:
                pass
        self._snap[root] = (ahora, con)
        return con
