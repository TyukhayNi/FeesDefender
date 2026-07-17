"""Operaciones de fichero genéricas, acotadas a allowedDirectories.

Sin dependencias de `mcp` ni de `core/`: lógica pura, testeable con pytest.
El saneado anti path-traversal replica el patrón de
`core/intake_manual.extract_zip` (re-implementado autocontenido).
"""
from __future__ import annotations

import base64
import hashlib
import os
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

_LONG_PATH_UMBRAL = 248


def _abrible(p: Path) -> str:
    r"""Ruta apta para operaciones de fichero: prefijo \\?\ solo cuando roza
    MAX_PATH (mismo patrón que readops._abrible)."""
    from .winio import long_path

    s = str(p)
    return long_path(p) if len(s) >= _LONG_PATH_UMBRAL else s


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
    with open(_abrible(target), "rb") as fh:
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


def write_text_file(allowed_dirs: list[Path], zonas, path: str | Path, text: str) -> Path:
    """Escribe texto ATÓMICO (tmp+nonce mismo dir) respetando zonas."""
    from .tiers import check_write
    from .winio import atomic_write_text

    dst = resolve_within(allowed_dirs, path)
    check_write(zonas, dst, exists=dst.exists())
    atomic_write_text(dst, text)
    return dst


def edit_text_file(allowed_dirs: list[Path], zonas, path: str | Path, old: str, new: str) -> Path:
    """Reemplaza `old` (exactamente 1 aparición) por `new`, atómico."""
    from .tiers import check_write
    from .winio import atomic_write_text

    dst = resolve_within(allowed_dirs, path)
    if not dst.is_file():
        raise FileNotFoundError(f"No existe: {path}")
    check_write(zonas, dst, exists=True)
    texto = dst.read_text(encoding="utf-8")
    n = texto.count(old)
    if n != 1:
        raise ValueError(f"'{old[:60]}' aparece {n} veces (se exige exactamente 1)")
    atomic_write_text(dst, texto.replace(old, new, 1))
    return dst


def copy_file_v2(allowed_dirs: list[Path], zonas, src: str | Path, dst: str | Path) -> Path:
    """Copia con destino atómico (si existe: tmp+replace) y zonas en ambos extremos.

    El origen pasa `check_gdoc` (spec §6.4): un stub nativo de Google (.gdoc,
    .gsheet, ...) es ilegible por FS y lanza `GDocBloqueado` con la desviación
    a google-despacho.
    """
    from .guards import check_gdoc
    from .tiers import check_read, check_write
    from .winio import retry_sharing

    src_p = resolve_within(allowed_dirs, src)
    dst_p = resolve_within(allowed_dirs, dst)
    check_read(zonas, src_p)
    check_gdoc(src_p)
    check_write(zonas, dst_p, exists=dst_p.exists())
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=dst_p.name + ".", suffix=".tmp", dir=_abrible(dst_p.parent))
    os.close(fd)
    try:
        shutil.copyfile(_abrible(src_p), _abrible(Path(tmp)))
        retry_sharing(lambda: os.replace(_abrible(Path(tmp)), _abrible(dst_p)))
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return dst_p


def copy_tree_v2(allowed_dirs: list[Path], zonas, oracle, src: str | Path, dst: str | Path) -> list[Path]:
    """Copia recursiva con travesía por nodo: poda Tier 0, valida CADA destino
    ANTES de copiar nada (dos pasadas), guarda de árbol frío.

    Los stubs nativos de Google (.gdoc, .gsheet, ...) del origen se OMITEN
    (incopiables a nivel de kernel) en vez de abortar el árbol; cada omisión
    se registra en el audit log (`omitido_gdoc`) — sin silencios.
    """
    from . import audit
    from .guards import GDocBloqueado, check_gdoc, guard_tree
    from .readops import iter_tree
    from .tiers import check_write

    src_p = resolve_within(allowed_dirs, src)
    dst_p = resolve_within(allowed_dirs, dst)
    guard_tree(oracle, src_p)
    plan: list[tuple[Path, Path]] = []
    for f in iter_tree(zonas, src_p):
        try:
            check_gdoc(f)
        except GDocBloqueado:
            audit.log_op("copy_tree_v2", str(f), "omitido_gdoc")
            continue
        destino = dst_p / f.relative_to(src_p)
        check_write(zonas, destino, exists=destino.exists())  # aborta ANTES de copiar
        plan.append((f, destino))
    copiados: list[Path] = []
    for origen, destino in plan:
        copiados.append(copy_file_v2(allowed_dirs, zonas, str(origen), str(destino)))
    return sorted(copiados)


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
        if len(parts) < 2 or parts[0] in ("..", "."):
            return None
        tops.add(parts[0])
    return tops.pop() if len(tops) == 1 else None


def extract_archive(
    allowed_dirs: list[Path],
    archive: str | Path,
    dest_dir: str | Path,
    max_total_bytes: int = DEFAULT_MAX_EXTRACT_BYTES,
    strip_top_level: bool = False,
    member_filter=None,
) -> list[Path]:
    """Descomprime .zip o .tar(.gz/.bz2) en dest_dir, ambos dentro del sandbox.

    Saneado anti path-traversal por miembro; presupuesto global `max_total_bytes`
    (anti zip-bomb). Si `strip_top_level` y el archivo tiene un ÚNICO directorio de
    primer nivel que envuelve a todos los ficheros, se quita ese wrapper de las
    rutas extraídas. Devuelve los ficheros extraídos (ordenados).

    `member_filter(name, dest)`, si se pasa, decide POR MIEMBRO (ya con el nombre
    saneado/sin wrapper y el destino resuelto) si se vuelca (True) o se OMITE
    (False) — antes de tocar bytes. Lo usa el servidor MCP para aplicar zonas/tiers
    por miembro (p. ej. destino Tier 0 o Tier 1 ya existente) sin abortar el resto
    del archivo.
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
                if member_filter is not None and not member_filter(name, dest):
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
                if member_filter is not None and not member_filter(name, dest):
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
