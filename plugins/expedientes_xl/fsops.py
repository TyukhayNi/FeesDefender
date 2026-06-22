"""Operaciones de fichero genéricas, acotadas a allowedDirectories.

Sin dependencias de `mcp` ni de `core/`: lógica pura, testeable con pytest.
El saneado anti path-traversal replica el patrón de
`core/intake_manual.extract_zip` (re-implementado autocontenido).
"""
from __future__ import annotations

import hashlib
import shutil
import tarfile
import zipfile
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


def _safe_member_dest(dest_dir: Path, member_name: str) -> Path | None:
    """Devuelve el destino saneado de un miembro, o None si debe descartarse.

    Descarta toda entrada con "..", componente absoluto o nulo; doble check
    de que el destino resuelto queda dentro de dest_dir (patrón extract_zip).
    """
    member_path = Path(member_name)
    if any(
        part in ("..", "") or "\x00" in part or Path(part).is_absolute()
        for part in member_path.parts
    ):
        return None
    dest = dest_dir / member_path
    try:
        dest.resolve().relative_to(dest_dir.resolve())
    except ValueError:
        return None
    return dest


def extract_archive(
    allowed_dirs: list[Path], archive: str | Path, dest_dir: str | Path
) -> list[Path]:
    """Descomprime .zip o .tar(.gz/.bz2) en dest_dir, ambos dentro del sandbox.

    Saneado anti path-traversal por miembro: las entradas peligrosas se
    descartan (no se intenta rescatarlas). Devuelve los ficheros extraídos.
    """
    archive_p = resolve_within(allowed_dirs, archive)
    dest_p = resolve_within(allowed_dirs, dest_dir)
    dest_p.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []

    if zipfile.is_zipfile(archive_p):
        with zipfile.ZipFile(archive_p) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                dest = _safe_member_dest(dest_p, member.filename)
                if dest is None:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(member))
                extracted.append(dest)
    elif tarfile.is_tarfile(archive_p):
        with tarfile.open(archive_p) as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                dest = _safe_member_dest(dest_p, member.name)
                if dest is None:
                    continue
                src = tf.extractfile(member)
                if src is None:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read())
                extracted.append(dest)
    else:
        raise ValueError(f"No es un archivo zip ni tar: {archive!r}")

    return sorted(extracted)
