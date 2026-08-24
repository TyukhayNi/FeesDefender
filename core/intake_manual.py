"""Intake manual de documentos subidos desde la UI.

Cada entrega manual es su propio lote ``00_Input/<AAAA-MM-DD>_manual_<NN>/``
(MEJORAS #54, spec rev 2, T6), con su ``_manifiesto.yaml`` (albarán forense de
la entrega). Legacy: casos no migrados conservan ``00_Input/04_Manual/`` (cajón
fijo, sin lotes) — ``list_files`` sigue leyéndolo para no perder visibilidad de
esos ficheros.

Cubre cualquier upload manual desde la pestaña «Casos» de la UI: demandas
judiciales (defensiva), documentos sueltos, paquetes ZIP. La UI llama a
``save_file``/``extract_zip`` con el nombre y los bytes del archivo
(``UploadedFile.name`` + ``UploadedFile.read()`` en Streamlit), de modo que
este módulo no depende de Streamlit.

Reglas de idempotencia:

- ``save_file``/``extract_zip`` sobrescriben si el archivo ya existe DENTRO
  del mismo lote (el equipo puede reintentar una entrega sin abrir otra).
- ``list_files`` devuelve lista vacía si no hay lotes ni carpeta legacy.

Histórico: este módulo es la sucesión de ``intake_demanda`` (refactor
intake v2, 2026-05-08). El destino se cambió de ``05_Demanda judicial/`` a
``04_Manual/`` por coherencia con la arquitectura v2, y de ``04_Manual/`` a
lotes por fecha (MEJORAS #54) para que cada entrega manual tenga su propio
albarán forense en vez de mezclarse en un cajón único.
"""

from __future__ import annotations

from pathlib import Path

from .config import CRM_SUBDIR, INTAKE_CONTROL_FILES, caso_path, settings
from .intake_manifest import IntakeManifest, compute_sha256_bytes
from .intake_utils import safe_zip_extract


# ---------------------------------------------------------------------------
# Constantes internas
# ---------------------------------------------------------------------------

_MANUAL_SUBDIR = "04_Manual"  # legacy: casos no migrados a lotes.
# Lista ÚNICA en config.INTAKE_CONTROL_FILES (MEJORAS #54 T1).
_CONTROL_FILES: frozenset[str] = INTAKE_CONTROL_FILES


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _manual_dir(case_id: str) -> Path:
    """Devuelve la ruta legacy ``00_Input/04_Manual/`` del caso (sin crearla)."""
    return caso_path(case_id) / "00_Input" / _MANUAL_SUBDIR


def _registrar_en_lote(case_id: str, lote: Path, rel: str, content: bytes,
                       *, origen: str) -> None:
    """Registra un ítem en M9 (dedup cross-fuente) y lo anexa al albarán del lote."""
    from . import intake_lotes

    sha = compute_sha256_bytes(content)
    with IntakeManifest(case_id) as manifest:
        dup = manifest.duplicado_de_para(sha, len(content))
        manifest.register(sha, f"{Path(lote).name}/{rel}", source="manual")
    intake_lotes.anexar_items(lote, [intake_lotes.ItemManifiesto(
        relpath=rel, sha256=sha, size=len(content),
        tipo_contenido=intake_lotes.clasificar_tipo_contenido(rel),
        duplicado_de=dup)], origen=origen)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def abrir_lote_manual(case_id: str, *, origen: str = "manual") -> Path:
    """Reserva un lote ``manual`` (una entrega). La UI agrupa un clic en UN lote."""
    from .intake_lotes import reservar_lote
    return reservar_lote(case_id, "manual", origen)


def save_file(case_id: str, filename: str, content: bytes,
              *, lote: Path | None = None) -> Path:
    """Guarda un archivo en un lote manual (``00_Input/<lote>/``).

    Sin ``lote``, abre uno propio (una entrega de un fichero). Con ``lote``,
    deposita en él — así la UI agrupa varios ficheros de un mismo clic en UN
    solo lote. Registra el ítem en M9 (dedup cross-fuente) y lo anexa al
    albarán forense del lote (``_manifiesto.yaml``).

    Args:
        case_id:  Identificador del caso (debe existir en ``casos_root``).
        filename: Nombre del archivo con extensión (p. ej. ``demanda.pdf``).
        content:  Contenido binario del archivo.
        lote:     Directorio del lote donde depositar (de ``abrir_lote_manual``
            o ``intake_lotes.reservar_lote``). Si ``None``, se abre uno.

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

    if lote is None:
        lote = abrir_lote_manual(case_id)
    lote = Path(lote)
    dest = lote / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    _registrar_en_lote(case_id, lote, filename, content, origen="ui_manual")
    return dest


def extract_zip(case_id: str, content: bytes,
                *, lote: Path | None = None) -> list[Path]:
    """Extrae un ZIP en un lote manual (``00_Input/<lote>/``).

    Cada entrada del ZIP se guarda relativa al directorio de destino,
    respetando la estructura interna de carpetas. Las rutas se sanean para
    evitar path traversal (entradas con ``..`` o rutas absolutas se omiten).
    Sin ``lote``, abre uno propio; con ``lote``, deposita en él (ver
    ``save_file``). Cada fichero extraído se registra en M9 y se anexa al
    albarán del lote.

    Args:
        case_id: Identificador del caso (debe existir en ``casos_root``).
        content: Bytes del archivo ZIP.
        lote:    Directorio del lote donde extraer. Si ``None``, se abre uno.

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

    if lote is None:
        lote = abrir_lote_manual(case_id)
    lote = Path(lote)
    lote.mkdir(parents=True, exist_ok=True)

    extraidos = sorted(safe_zip_extract(content, lote))
    for p in extraidos:
        rel = p.relative_to(lote).as_posix()
        _registrar_en_lote(case_id, lote, rel, p.read_bytes(), origen="ui_manual")
    return extraidos


def save_file_en_lote(case_id: str, lote: Path, rel: str, content: bytes) -> Path:
    """Escribe ``<lote>/<rel>`` (``rel`` puede llevar subcarpetas) y registra.

    Hermano de ``save_file`` para callers que ya tienen el lote abierto y
    conocen la ruta relativa exacta (p. ej. el CLI de intake manual). Rechaza
    path traversal exactamente como ``safe_zip_extract``: cualquier componente
    ``".."``, absoluto o vacío hace fallar la llamada.

    Args:
        case_id: Identificador del caso (usado para el registro en M9; el
            caller ya validó la existencia del caso al abrir el lote con
            ``abrir_lote_manual``/``reservar_lote``, que aplica el guard §6).
        lote: Directorio del lote (de ``abrir_lote_manual``/``reservar_lote``).
        rel:  Ruta relativa al lote (puede llevar subdirectorios).
        content: Contenido binario del archivo.

    Returns:
        Ruta absoluta al archivo guardado.

    Raises:
        ValueError: si ``rel`` intenta escapar del lote (path traversal).
    """
    lote = Path(lote)
    rel_path = Path(rel)
    if any(part in ("..", "") or Path(part).is_absolute() for part in rel_path.parts):
        raise ValueError(f"Ruta relativa no válida (path traversal): {rel!r}")

    dest = lote / rel_path
    try:
        dest.resolve().relative_to(lote.resolve())
    except ValueError as exc:
        raise ValueError(f"Ruta relativa escapa del lote: {rel!r}") from exc

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    _registrar_en_lote(case_id, lote, rel_path.as_posix(), content, origen="cli_manual")
    return dest


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

    # `localizar` lanza el error estructurado del §10; el `FileNotFoundError` que
    # habia aqui interpolaba `settings.casos_root`, que el §16 prohibe.
    from core.casos.case_locator import localizar
    case_dir = localizar(case_id)

    # Guard de escritura (DISEÑO_V2 §6): si el caso está prestado/conflicto, el
    # fichero va a la bandeja _pendiente_checkin/crm_manual/ con evento en el log.
    from .case_manager import guard_escritura

    rel = f"00_Input/{CRM_SUBDIR}/{branch.as_posix()}/{filename}"
    decision = guard_escritura(case_id, rel, "crm_manual")
    if decision.desviar:
        dest = case_dir / decision.ruta_bandeja
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return dest

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
    from core.casos.case_locator import buscar
    case_dir = buscar(case_id)
    if case_dir is None:
        return []                      # el caso no existe
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
    """Nivel raíz de cada lote ``manual`` + legacy ``04_Manual`` (casos no migrados).

    Excluye archivos de control internos (``.pulled``, ``_inventory.json``,
    etc.) y el propio ``_manifiesto.yaml`` de cada lote. Devuelve lista vacía
    si no hay ``00_Input/`` todavía.

    Args:
        case_id: Identificador del caso.

    Returns:
        Lista de ``Path`` ordenada.
    """
    from .intake_lotes import MANIFIESTO_LOTE, PATRON_LOTE

    from core.casos.case_locator import buscar
    base = buscar(case_id)
    if base is None:
        return []                      # el caso no existe
    input_dir = base / "00_Input"
    if not input_dir.exists():
        return []                      # el caso existe, `00_Input` no
    bases = [d for d in input_dir.iterdir() if d.is_dir()
             and (m := PATRON_LOTE.match(d.name)) and m.group(2) == "manual"]
    legacy = input_dir / _MANUAL_SUBDIR
    if legacy.is_dir():
        bases.append(legacy)
    out = [p for d in bases for p in d.iterdir()
           if p.is_file() and p.name not in _CONTROL_FILES
           and p.name != MANIFIESTO_LOTE]
    return sorted(out)
