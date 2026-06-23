"""Utilidades compartidas del subsistema de intake.

Centraliza patrones que antes estaban duplicados en varios módulos:

- :func:`sanitize_filename` — nombre de fichero seguro en Windows (4 variantes).
- :func:`decode_base64url` — decodificación de base64url de Gmail con padding tolerante.
- :func:`safe_zip_members` — lectura de ZIP en memoria sin path traversal.
- :func:`safe_zip_extract` — extracción de ZIP a disco sin path traversal.
"""

from __future__ import annotations

import base64
import io
import re
import zipfile
from pathlib import Path

# Caracteres prohibidos en Windows más control chars (0x00-0x1f).
# Usado en modo "file" y "folder".
_RE_FS_INVALIDO = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Conjunto de chars prohibidos para modo "segment" (reemplaza con espacio,
# preserva acentos y paréntesis — pensado para case_id y rutas de informe).
_FORBIDDEN_SEGMENT_CHARS = '/\\:*?"<>|'


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------


def sanitize_filename(
    name: str,
    *,
    mode: str = "file",
    fallback: str = "_",
) -> str:
    """Nombre de fichero o carpeta seguro en Windows.

    Args:
        name: Cadena de entrada (puede estar vacía o ser ``None``-equivalente).
        mode: Estrategia de saneado:
            ``"file"``    — sustituye con ``_`` los chars prohibidos en Windows y
                           los de control (0x00–0x1f). Elimina puntos iniciales y
                           finales. Devuelve ``fallback`` si el resultado queda vacío.
            ``"folder"``  — igual que ``"file"`` pero además reemplaza ``..`` por
                           ``_`` (útil para nombres de carpeta que vienen de ZIPs
                           o exports de terceros).
            ``"segment"`` — sustituye los chars prohibidos por **espacios** y
                           preserva acentos y paréntesis. Para segmentos derivados
                           del case_id que forman parte de un nombre de fichero.
        fallback: Valor de retorno si el resultado tras el saneado queda vacío
                  (solo aplica en modos ``"file"`` y ``"folder"``).

    Returns:
        Cadena saneada.
    """
    if mode == "segment":
        s = name or ""
        for ch in _FORBIDDEN_SEGMENT_CHARS:
            s = s.replace(ch, " ")
        return s.strip()

    # Modos "file" y "folder"
    base = name or ""
    if mode == "folder":
        base = base.replace("..", "_")
    clean = _RE_FS_INVALIDO.sub("_", base).strip().strip(".").strip()
    return clean or fallback


# ---------------------------------------------------------------------------
# decode_base64url
# ---------------------------------------------------------------------------


def decode_base64url(data: str, *, as_bytes: bool = False) -> str | bytes:
    """Decodifica base64url de Gmail con padding tolerante.

    Args:
        data: Cadena en base64url (puede tener padding incompleto).
        as_bytes: Si ``True`` devuelve los bytes crudos; si ``False`` (defecto)
                  devuelve la cadena UTF-8 con ``errors='replace'``.

    Returns:
        Bytes o str decodificados; vacío (``b""`` / ``""``) si ``data`` es falsy.
    """
    if not data:
        return b"" if as_bytes else ""
    pad = "=" * (-len(data) % 4)
    decoded = base64.urlsafe_b64decode(data + pad)
    return decoded if as_bytes else decoded.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# safe_zip_members
# ---------------------------------------------------------------------------


def safe_zip_members(content: bytes) -> dict[str, bytes]:
    """Lee un ZIP en memoria → ``{nombre_base: bytes}`` sin path traversal.

    Ignora entradas de directorio, rutas absolutas y cualquier componente
    ``".."`` o vacío. La clave del dict es solo el nombre base (sin subdirectorio).

    Args:
        content: Bytes del fichero ZIP.

    Returns:
        Diccionario ``{nombre_fichero: bytes_del_fichero}``.

    Raises:
        zipfile.BadZipFile: Si ``content`` no es un ZIP válido.
    """
    members: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for info in zf.infolist():
            if info.filename.endswith("/"):
                continue
            parts = Path(info.filename).parts
            if any(p in ("..", "") or Path(p).is_absolute() for p in parts):
                continue
            members[Path(info.filename).name] = zf.read(info)
    return members


# ---------------------------------------------------------------------------
# safe_zip_extract
# ---------------------------------------------------------------------------


def safe_zip_extract(content: bytes, dest_dir: Path) -> list[Path]:
    """Extrae un ZIP a ``dest_dir`` de forma segura (sin path traversal).

    Preserva la estructura de subdirectorios del ZIP, pero descarta cualquier
    entrada que escape de ``dest_dir`` (``..``, rutas absolutas, componentes
    vacíos). ``dest_dir`` debe existir antes de llamar a esta función.

    Args:
        content: Bytes del fichero ZIP.
        dest_dir: Directorio de destino (debe existir).

    Returns:
        Lista de ``Path`` de los ficheros escritos, en orden de extracción.

    Raises:
        zipfile.BadZipFile: Si ``content`` no es un ZIP válido.
    """
    extracted: list[Path] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for member in zf.infolist():
            if member.filename.endswith("/"):
                continue
            member_path = Path(member.filename)
            try:
                if any(
                    part in ("..", "") or Path(part).is_absolute()
                    for part in member_path.parts
                ):
                    continue
                safe_rel = member_path
            except Exception:
                continue
            dest = dest_dir / safe_rel
            # Doble comprobación: el destino resuelto debe seguir dentro de dest_dir.
            try:
                dest.resolve().relative_to(dest_dir.resolve())
            except ValueError:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(member))
            extracted.append(dest)
    return extracted
