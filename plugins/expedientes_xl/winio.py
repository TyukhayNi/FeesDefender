r"""E/S robusta en Windows/GDFD: escritura atómica (tmp+nonce MISMO directorio +
os.replace — nunca %TEMP%: cross-device rename falla con EXDEV), reintentos ante
ERROR_SHARING_VIOLATION (~$ de Office) y prefijo \\?\ para MAX_PATH."""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")

_BACKOFF = (0.5, 1.0, 2.0)


class SharingViolation(Exception):
    """Fichero bloqueado por otro proceso (probablemente editado por un humano)."""


def long_path(p: Path) -> str:
    """Prefijo ``\\\\?\\`` solo para rutas absolutas: de unidad (``G:\\...``)
    o UNC (``\\\\server\\share\\...`` → ``\\\\?\\UNC\\...``). Las relativas
    se devuelven sin tocar (el prefijo las rompería)."""
    s = str(p)
    if s.startswith("\\\\?\\"):
        return s
    if len(s) >= 3 and s[1] == ":" and s[2] == "\\" and s[0].isalpha():
        return "\\\\?\\" + s
    if s.startswith("\\\\"):
        return "\\\\?\\UNC\\" + s[2:]
    return s


_LONG_PATH_UMBRAL = 248


def _abrible(p: Path | str) -> str:
    r"""Ruta apta para operaciones de fichero: prefijo \\?\ solo cuando roza
    MAX_PATH (mismo patrón que readops._abrible)."""
    s = str(p)
    return long_path(Path(s)) if len(s) >= _LONG_PATH_UMBRAL else s


def retry_sharing(fn: Callable[[], T]) -> T:
    ultimo: PermissionError | None = None
    for i, espera in enumerate(_BACKOFF):
        try:
            return fn()
        except PermissionError as e:
            if getattr(e, "winerror", None) != 32:
                raise
            ultimo = e
            if i < len(_BACKOFF) - 1:
                time.sleep(espera)
    raise SharingViolation(
        "Bloqueado tras 3 reintentos: probablemente lo está editando un humano"
    ) from ultimo


def atomic_write_bytes(dst: Path, data: bytes) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=dst.name + ".", suffix=".tmp", dir=_abrible(dst.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        retry_sharing(lambda: os.replace(_abrible(tmp), _abrible(dst)))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return len(data)


def atomic_write_text(dst: Path, text: str) -> int:
    return atomic_write_bytes(dst, text.encode("utf-8"))
