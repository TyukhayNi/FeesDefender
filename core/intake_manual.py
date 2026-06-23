"""Intake manual de documentos subidos desde la UI.

Destino local: ``00_Input/04_Manual/`` dentro del caso.

Cubre cualquier upload manual desde la pestaña «Casos» de la UI: demandas
judiciales (defensiva), documentos sueltos, paquetes ZIP. La UI llama a
``save_file`` con el nombre y los bytes del archivo
(``UploadedFile.name`` + ``UploadedFile.read()`` en Streamlit), de modo que
este módulo no depende de Streamlit.

Reglas de idempotencia:

- ``save_file`` sobreescribe si el archivo ya existe (el equipo puede
  actualizar una versión sin renombrarlo).
- ``list_files`` devuelve lista vacía si la carpeta no existe aún.

Histórico: este módulo es la sucesión de ``intake_demanda`` (refactor
intake v2, 2026-05-08). El destino se cambió de ``05_Demanda judicial/``
a ``04_Manual/`` por coherencia con la arquitectura v2 (cada fuente con
su carpeta — el árbol CRM ``05_CRM/`` queda reservado a docs descargados
del Gestor Documental sudespacho vía ``sync_sudespacho.pull_expediente_v2``).
"""

from __future__ import annotations

from pathlib import Path

from .config import CRM_SUBDIR, caso_path, settings
from .intake_utils import safe_zip_extract


# ---------------------------------------------------------------------------
# Constantes internas
# ---------------------------------------------------------------------------

_MANUAL_SUBDIR = "04_Manual"
_CONTROL_FILES: frozenset[str] = frozenset({".pulled", "_inventory.json", ".synced"})


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _manual_dir(case_id: str) -> Path:
    """Devuelve la ruta a ``00_Input/04_Manual/`` del caso (sin crearla)."""
    return caso_path(case_id) / "00_Input" / _MANUAL_SUBDIR


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def save_file(case_id: str, filename: str, content: bytes) -> Path:
    """Guarda un archivo en ``00_Input/04_Manual/``.

    Crea el directorio si no existe. Si ya existe un archivo con el mismo
    nombre, lo sobreescribe (versionado por nombre — el equipo puede subir
    versiones actualizadas sin renombrar).

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

    dest_dir = _manual_dir(case_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / filename
    dest.write_bytes(content)
    return dest


def extract_zip(case_id: str, content: bytes) -> list[Path]:
    """Extrae un ZIP en ``00_Input/04_Manual/``.

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

    dest_dir = _manual_dir(case_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    return sorted(safe_zip_extract(content, dest_dir))


def save_file_crm_branch(
    case_id: str,
    branch_path: str,
    filename: str,
    content: bytes,
) -> Path:
    """Guarda un archivo en ``00_Input/05_CRM/<branch_path>/`` (paso 7b).

    Hermano de ``save_file``: misma semántica (sobrescribe si existe,
    crea el directorio si falta) pero el destino es una rama del árbol
    del gestor documental CRM. La rama suele haber sido creada eager
    por ``ensure_case`` (D1), pero ``mkdir(parents=True, exist_ok=True)``
    cubre llamadas defensivas.

    Args:
        case_id: Identificador del caso (debe existir en ``casos_root``).
        branch_path: Ruta canónica con separador ``"/"`` (D11), p. ej.
            ``"Civil/1ª Instancia/Declarativo/Demanda"`` o ``"General"``.
            Saneado contra path traversal: cualquier componente ``".."``,
            absoluto o vacío hace fallar la llamada.
        filename: Nombre del archivo con extensión (sin separadores).
        content: Contenido binario del archivo.

    Returns:
        Ruta absoluta al archivo guardado.

    Raises:
        FileNotFoundError: si el caso no existe en ``casos_root``.
        ValueError: si ``filename`` o ``branch_path`` no son válidos.
    """
    if not filename or filename != Path(filename).name:
        raise ValueError(
            f"Nombre de archivo no válido: {filename!r}. "
            "Usa solo el nombre del archivo, sin rutas."
        )
    if not branch_path or not branch_path.strip():
        raise ValueError("branch_path no puede estar vacío.")

    branch = Path(branch_path.strip())
    for part in branch.parts:
        if part in ("..", "") or Path(part).is_absolute():
            raise ValueError(
                f"branch_path inválido (path traversal): {branch_path!r}"
            )

    case_dir = caso_path(case_id)
    if not case_dir.exists():
        raise FileNotFoundError(
            f"El caso '{case_id}' no existe en {settings.casos_root}. "
            "Llama a ensure_case() antes de save_file_crm_branch()."
        )

    dest_dir = case_dir / "00_Input" / CRM_SUBDIR / branch
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / filename
    # Doble comprobación: el destino resuelto debe seguir dentro de 05_CRM/.
    crm_root = case_dir / "00_Input" / CRM_SUBDIR
    try:
        dest.resolve().relative_to(crm_root.resolve())
    except ValueError as exc:
        raise ValueError(
            f"branch_path escapa de 05_CRM/: {branch_path!r}"
        ) from exc

    dest.write_bytes(content)
    return dest


def list_crm_branch_files(case_id: str, branch_path: str) -> list[Path]:
    """Lista archivos en ``00_Input/05_CRM/<branch_path>/`` (nivel raíz).

    Excluye archivos de control internos. Devuelve lista vacía si el
    directorio no existe.
    """
    case_dir = caso_path(case_id)
    branch = Path(branch_path.strip()) if branch_path else None
    if branch is None:
        return []
    d = case_dir / "00_Input" / CRM_SUBDIR / branch
    if not d.exists():
        return []
    return sorted(
        p for p in d.iterdir()
        if p.is_file() and p.name not in _CONTROL_FILES
    )


def list_files(case_id: str) -> list[Path]:
    """Lista los archivos en ``00_Input/04_Manual/`` del caso.

    Excluye archivos de control internos (``.pulled``, ``_inventory.json``, etc.).
    Devuelve lista vacía si el directorio no existe o no hay archivos.
    Solo nivel raíz: si ``extract_zip`` creó subcarpetas, sus archivos no
    aparecen aquí (el paso 7 de la UI puede mejorarlo si se decide).

    Args:
        case_id: Identificador del caso.

    Returns:
        Lista de ``Path`` ordenada alfabéticamente.
    """
    d = _manual_dir(case_id)
    if not d.exists():
        return []
    return sorted(
        p for p in d.iterdir()
        if p.is_file() and p.name not in _CONTROL_FILES
    )
