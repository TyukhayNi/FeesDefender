"""Operaciones de fichero genéricas, acotadas a allowedDirectories.

Sin dependencias de `mcp` ni de `core/`: lógica pura, testeable con pytest.
El saneado anti path-traversal replica el patrón de
`core/intake_manual.extract_zip` (re-implementado autocontenido).
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


class OutsideSandbox(Exception):
    """La ruta resuelta cae fuera de todos los allowedDirectories."""


class TooLarge(Exception):
    """El contenido supera el tope de tamaño permitido."""


def resolve_within(allowed_dirs: list[Path], target: str | Path) -> Path:
    """Resuelve `target` y exige que quede dentro de algún allowedDir.

    Rechaza explícitamente componentes "..", nulos, y rutas cuyo destino
    resuelto (símbolos y symlinks ya colapsados) no esté bajo un allowedDir.
    """
    raw = Path(target)
    if any(part in ("..", "") or "\x00" in part for part in raw.parts):
        raise OutsideSandbox(f"Ruta con componente no permitido: {target!r}")
    resolved = raw.resolve()
    for base in allowed_dirs:
        base_resolved = Path(base).resolve()
        try:
            resolved.relative_to(base_resolved)
            return resolved
        except ValueError:
            continue
    raise OutsideSandbox(f"Ruta fuera del sandbox: {target!r}")


_CHUNK = 1024 * 1024  # 1 MiB


def sha256_file(allowed_dirs: list[Path], path: str | Path) -> str:
    """SHA-256 del fichero, calculado server-side. Devuelve solo el digest."""
    target = resolve_within(allowed_dirs, path)
    h = hashlib.sha256()
    with open(target, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_file(allowed_dirs: list[Path], src: str | Path, dst: str | Path) -> Path:
    """Copia un fichero (no destructivo). src y dst dentro del sandbox."""
    src_p = resolve_within(allowed_dirs, src)
    dst_p = resolve_within(allowed_dirs, dst)
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_p, dst_p)
    return dst_p


def copy_tree(allowed_dirs: list[Path], src: str | Path, dst: str | Path) -> Path:
    """Copia recursiva de un árbol de directorios dentro del sandbox."""
    src_p = resolve_within(allowed_dirs, src)
    dst_p = resolve_within(allowed_dirs, dst)
    shutil.copytree(src_p, dst_p, dirs_exist_ok=True)
    return dst_p
