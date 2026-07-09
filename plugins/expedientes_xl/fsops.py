"""Operaciones de fichero genéricas, acotadas a allowedDirectories.

Sin dependencias de `mcp` ni de `core/`: lógica pura, testeable con pytest.
El saneado anti path-traversal replica el patrón de
`core/intake_manual.extract_zip` (re-implementado autocontenido).
"""
from __future__ import annotations

import base64
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

DEFAULT_MAX_EXTRACT_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB


def _stream_member(src, dest: Path, budget: list[int]) -> None:
    """Vuelca el file-like `src` a `dest` en chunks, descontando de budget[0].

    Si la descompresión supera el presupuesto, borra el parcial y lanza TooLarge.
    """
    try:
        with open(dest, "wb") as out:
            for chunk in iter(lambda: src.read(_CHUNK), b""):
                budget[0] -= len(chunk)
                if budget[0] < 0:
                    raise TooLarge("La descompresión supera el tope de tamaño")
                out.write(chunk)
    except TooLarge:
        dest.unlink(missing_ok=True)
        raise


def sha256_file(allowed_dirs: list[Path], path: str | Path) -> str:
    """SHA-256 del fichero, calculado server-side. Devuelve solo el digest."""
    target = resolve_within(allowed_dirs, path)
    h = hashlib.sha256()
    with open(target, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_tree(allowed_dirs: list[Path], root: str | Path) -> dict[str, str]:
    """SHA-256 recursivo server-side de todos los ficheros bajo `root`.

    Devuelve {relpath_posix: sha256hex}, relpath relativo a `root`. Determinista
    (el dict se construye en orden ordenado). Salta directorios y **symlinks**
    (defensa: un symlink podría apuntar fuera del sandbox). Si `root` no existe
    o no es directorio, devuelve {}.
    """
    root_p = resolve_within(allowed_dirs, root)
    out: dict[str, str] = {}
    if not root_p.is_dir():
        return out
    for p in sorted(root_p.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(_CHUNK), b""):
                h.update(chunk)
        out[p.relative_to(root_p).as_posix()] = h.hexdigest()
    return out


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
    shutil.copytree(src_p, dst_p, dirs_exist_ok=True, symlinks=True)
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


def _common_top_level(names: list[str]) -> str | None:
    """Único directorio de primer nivel común a TODOS los nombres, o None.

    Devuelve None si algún miembro está en la raíz del archivo (sin carpeta) o
    si hay más de un directorio de primer nivel: en esos casos no hay un wrapper
    inequívoco que quitar.
    """
    tops: set[str] = set()
    for n in names:
        parts = Path(n).parts
        if len(parts) < 2:
            return None
        tops.add(parts[0])
    return tops.pop() if len(tops) == 1 else None


def extract_archive(
    allowed_dirs: list[Path],
    archive: str | Path,
    dest_dir: str | Path,
    max_total_bytes: int = DEFAULT_MAX_EXTRACT_BYTES,
    strip_top_level: bool = False,
) -> list[Path]:
    """Descomprime .zip o .tar(.gz/.bz2) en dest_dir, ambos dentro del sandbox.

    Saneado anti path-traversal por miembro; presupuesto global `max_total_bytes`
    (anti zip-bomb). Si `strip_top_level` y el archivo tiene un ÚNICO directorio de
    primer nivel que envuelve a todos los ficheros, se quita ese wrapper de las
    rutas extraídas. Devuelve los ficheros extraídos (ordenados).
    """
    archive_p = resolve_within(allowed_dirs, archive)
    dest_p = resolve_within(allowed_dirs, dest_dir)
    dest_p.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    budget = [max_total_bytes]

    def _dest_name(name: str, prefix: str | None) -> str | None:
        if prefix is None:
            return name
        rel = Path(name).parts[1:]  # quitar el wrapper
        return str(Path(*rel)) if rel else None

    if zipfile.is_zipfile(archive_p):
        with zipfile.ZipFile(archive_p) as zf:
            file_members = [m for m in zf.infolist() if not m.is_dir()]
            prefix = _common_top_level([m.filename for m in file_members]) if strip_top_level else None
            for member in file_members:
                name = _dest_name(member.filename, prefix)
                if name is None:
                    continue
                dest = _safe_member_dest(dest_p, name)
                if dest is None:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src:
                    _stream_member(src, dest, budget)
                extracted.append(dest)
    elif tarfile.is_tarfile(archive_p):
        with tarfile.open(archive_p) as tf:
            file_members = [m for m in tf.getmembers() if m.isfile()]
            prefix = _common_top_level([m.name for m in file_members]) if strip_top_level else None
            for member in file_members:
                name = _dest_name(member.name, prefix)
                if name is None:
                    continue
                dest = _safe_member_dest(dest_p, name)
                if dest is None:
                    continue
                src = tf.extractfile(member)
                if src is None:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                _stream_member(src, dest, budget)
                extracted.append(dest)
    else:
        raise ValueError(f"No es un archivo zip ni tar: {archive!r}")

    return sorted(extracted)


def write_base64(
    allowed_dirs: list[Path], path: str | Path, content_b64: str, max_bytes: int
) -> int:
    """Escribe un binario desde base64, con tope DURO de tamaño.

    Comprueba el tamaño ANTES de escribir; si supera max_bytes lanza TooLarge.
    Devuelve el número de bytes escritos.
    """
    cleaned = "".join(content_b64.split())
    data = base64.b64decode(cleaned, validate=True)
    if len(data) > max_bytes:
        raise TooLarge(f"{len(data)} bytes supera el tope {max_bytes}")
    dst = resolve_within(allowed_dirs, path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return len(data)


def append_text(allowed_dirs: list[Path], path: str | Path, text: str) -> Path:
    """Anexa texto UTF-8 a un fichero (lo crea si falta). Para .jsonl."""
    dst = resolve_within(allowed_dirs, path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "a", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return dst


def delete_path(allowed_dirs: list[Path], path: str | Path) -> None:
    """Borra un fichero o árbol dentro del sandbox."""
    target = resolve_within(allowed_dirs, path)
    for base in allowed_dirs:
        if target == Path(base).resolve():
            raise OutsideSandbox("No se permite borrar la raíz del sandbox")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink(missing_ok=True)
