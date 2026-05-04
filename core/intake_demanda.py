"""Intake de documentos judiciales subidos manualmente desde la UI.

Destino local: ``00_Input/05_Demanda judicial/`` dentro del caso.

Uso principal: expedientes defensivos (DEVOLUCION_RESERVA, LAU_20,
RESPONSABILIDAD_PROFESIONAL) en los que la demanda llega por email al
abogado y se sube manualmente desde la pestaña «Casos» de la UI.

La UI llama a ``save_file()`` con el nombre y los bytes del archivo
(``UploadedFile.name`` + ``UploadedFile.read()`` en Streamlit), de modo
que este módulo no depende de Streamlit.

Reglas de idempotencia:
  - ``save_file`` sobreescribe si el archivo ya existe (el abogado puede
    actualizar una versión de la demanda sin renombrarlo).
  - ``list_files`` devuelve lista vacía si la carpeta no existe aún.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from .config import caso_path, settings


# ---------------------------------------------------------------------------
# Constantes internas
# ---------------------------------------------------------------------------

_DEMANDA_SUBDIR = "05_Demanda judicial"
_CONTROL_FILES: frozenset[str] = frozenset({".pulled", "_inventory.json", ".synced"})


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _demanda_dir(case_id: str) -> Path:
    """Devuelve la ruta a 00_Input/05_Demanda judicial/ del caso (sin crearla)."""
    return caso_path(case_id) / "00_Input" / _DEMANDA_SUBDIR


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def save_file(case_id: str, filename: str, content: bytes) -> Path:
    """Guarda un archivo en ``00_Input/05_Demanda judicial/``.

    Crea el directorio si no existe. Si ya existe un archivo con el mismo
    nombre, lo sobreescribe (el abogado puede subir versiones actualizadas).

    Args:
        case_id:  Identificador del caso (debe existir en ``casos_root``).
        filename: Nombre del archivo con extensión (p. ej. ``demanda.pdf``).
        content:  Contenido binario del archivo.

    Returns:
        Ruta absoluta al archivo guardado.

    Raises:
        FileNotFoundError: si el caso no existe en ``casos_root``.
        ValueError: si ``filename`` está vacío o contiene separadores de ruta.
    """
    if not filename or filename != Path(filename).name:
        raise ValueError(
            f"Nombre de archivo no válido: {filename!r}. "
            "Usa solo el nombre del archivo, sin rutas."
        )

    case_dir = caso_path(case_id)
    if not case_dir.exists():
        raise FileNotFoundError(
            f"El caso '{case_id}' no existe en {settings.casos_root}. "
            "Llama a ensure_case() antes de save_file()."
        )

    dest_dir = _demanda_dir(case_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / filename
    dest.write_bytes(content)
    return dest


def extract_zip(case_id: str, content: bytes) -> list[Path]:
    """Extrae un ZIP en ``00_Input/05_Demanda judicial/``.

    Cada entrada del ZIP se guarda relativa al directorio de destino,
    respetando la estructura interna de carpetas. Las rutas se sanean para
    evitar path traversal (entradas con ``..`` o rutas absolutas se omiten).

    Args:
        case_id: Identificador del caso (debe existir en ``casos_root``).
        content: Bytes del archivo ZIP.

    Returns:
        Lista de ``Path`` de los archivos extraídos, ordenada.

    Raises:
        FileNotFoundError: si el caso no existe en ``casos_root``.
        zipfile.BadZipFile: si ``content`` no es un ZIP válido.
    """
    case_dir = caso_path(case_id)
    if not case_dir.exists():
        raise FileNotFoundError(
            f"El caso '{case_id}' no existe en {settings.casos_root}. "
            "Llama a ensure_case() antes de extract_zip()."
        )

    dest_dir = _demanda_dir(case_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    extracted: list[Path] = []

    import io
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for member in zf.infolist():
            # Saltarse directorios puros
            if member.filename.endswith("/"):
                continue

            # Sanear la ruta: descartar TODA la entrada si contiene "..",
            # componentes absolutos o caracteres nulos — no se intenta rescatar.
            member_path = Path(member.filename)
            try:
                # Rechazar si algún componente es peligroso
                if any(
                    part in ("..", "") or Path(part).is_absolute()
                    for part in member_path.parts
                ):
                    continue
                safe_rel = member_path
            except Exception:
                continue

            dest = dest_dir / safe_rel
            # Doble comprobación: el destino resuelto debe seguir dentro de dest_dir
            try:
                dest.resolve().relative_to(dest_dir.resolve())
            except ValueError:
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(member))
            extracted.append(dest)

    return sorted(extracted)


def list_files(case_id: str) -> list[Path]:
    """Lista los archivos en ``00_Input/05_Demanda judicial/`` del caso.

    Excluye archivos de control internos (``.pulled``, ``_inventory.json``, etc.).
    Devuelve lista vacía si el directorio no existe o no hay archivos.

    Args:
        case_id: Identificador del caso.

    Returns:
        Lista de ``Path`` ordenada alfabéticamente.
    """
    d = _demanda_dir(case_id)
    if not d.exists():
        return []
    return sorted(
        p for p in d.iterdir()
        if p.is_file() and p.name not in _CONTROL_FILES
    )
