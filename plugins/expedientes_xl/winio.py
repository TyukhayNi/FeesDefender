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
    s = str(p)
    if s.startswith("\\\\?\\"):
        return s
    return "\\\\?\\" + s


def retry_sharing(fn: Callable[[], T]) -> T:
    ultimo: PermissionError | None = None
    for espera in _BACKOFF:
        try:
            return fn()
        except PermissionError as e:
            if getattr(e, "winerror", None) != 32:
                raise
            ultimo = e
            time.sleep(espera)
    raise SharingViolation(
        "Bloqueado tras 3 reintentos: probablemente lo está editando un humano"
    ) from ultimo


def atomic_write_bytes(dst: Path, data: bytes) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=dst.name + ".", suffix=".tmp", dir=str(dst.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        retry_sharing(lambda: os.replace(tmp, dst))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return len(data)


def atomic_write_text(dst: Path, text: str) -> int:
    return atomic_write_bytes(dst, text.encode("utf-8"))
