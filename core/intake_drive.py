"""Intake de documentos desde el Drive de Engel & Völkers.

Copia la carpeta W-XXXXXX del Drive engelvoelkers.com al caso local
mediante rclone, usando el remote `gdrive_ev` (cuenta corporativa E&V).

Configuración rclone (ya configurado con `rclone config`):
    remote: gdrive_ev  — cuenta nikolai.tyukhay@engelvoelkers.com
    token:  C:/Users/tnm33/AppData/Roaming/rclone/rclone.conf (no va a git)

Comando rclone ejecutado:
    rclone copy "gdrive_ev:" "{destino}" \\
        --drive-team-drive {team_id} \\
        --drive-root-folder-id {folder_id} \\
        --stats-one-line-date --log-level INFO

Destino local: `00_Input/01_Drive EV/` dentro del caso.

Marcador de idempotencia: `00_Input/01_Drive EV/.pulled` (JSON)
  {
    "team_id": "...",
    "folder_id": "...",
    "last_sync": "2026-...",
    "rclone_returncode": 0,
    "errors": []
  }

Modos de operación:
  force=False  →  skip si .pulled ya existe (primera descarga)
  force=True   →  re-ejecuta rclone siempre (actualiza docs)

Nota: rclone es idempotente por diseño (solo copia ficheros nuevos/modificados),
por lo que force=True en pulls posteriores solo transfiere deltas.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .case_manager import register_drive_ev
from .config import caso_path, settings
from .utils import now_iso


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_DRIVE_EV_INPUT_SUBDIR = "01_Drive EV"
_PULL_MARKER = ".pulled"

# Regex que cubre los formatos habituales de URL de carpeta Google Drive:
#   https://drive.google.com/drive/folders/{id}
#   https://drive.google.com/drive/u/0/folders/{id}
#   https://drive.google.com/drive/u/0/folders/{id}?usp=sharing
_DRIVE_FOLDER_RE = re.compile(
    r"https://drive\.google\.com/drive(?:/u/\d+)?/folders/([a-zA-Z0-9_-]+)"
)


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

@dataclass
class DriveIntakeResult:
    """Resultado de una operación de pull desde el Drive E&V."""
    case_id: str
    team_id: str
    folder_id: str
    target_dir: Path
    files_after: int       # archivos en destino tras el pull (excluye .pulled)
    skipped: bool          # True si .pulled existía y no se forzó
    rclone_returncode: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def parse_drive_url(url: str) -> str:
    """Extrae el folder_id de una URL de carpeta Google Drive.

    Soporta:
    - https://drive.google.com/drive/folders/{id}
    - https://drive.google.com/drive/u/0/folders/{id}
    - https://drive.google.com/drive/u/0/folders/{id}?usp=sharing&resourcekey=...

    Si `url` no tiene formato URL de Drive pero parece un ID de Google
    (solo alfanumérico + guion + guion_bajo, ≥10 chars), lo devuelve tal cual.

    Raises:
        ValueError: si no puede extraer un folder_id reconocible.
    """
    url = url.strip()

    # Intentar extraer de URL completa
    m = _DRIVE_FOLDER_RE.search(url)
    if m:
        return m.group(1)

    # Aceptar IDs directos (sin prefijo de URL)
    if re.fullmatch(r"[a-zA-Z0-9_-]{10,}", url):
        return url

    raise ValueError(
        f"No se pudo extraer folder_id de la URL: {url!r}\n"
        "Formatos admitidos:\n"
        "  · https://drive.google.com/drive/folders/<id>\n"
        "  · https://drive.google.com/drive/u/0/folders/<id>\n"
        "  · ID directo de carpeta (solo caracteres alfanuméricos, - y _)"
    )


def pull_drive_ev(
    case_id: str,
    folder_id: str,
    team_id: str,
    *,
    force: bool = False,
) -> DriveIntakeResult:
    """Copia la carpeta W-XXXXXX del Drive E&V al caso local.

    Args:
        case_id:   Identificador del caso (debe existir en casos_root).
        folder_id: ID de la carpeta W-XXXXXX en el Drive engelvoelkers.com.
        team_id:   ID del Shared Drive (Team Drive) de E&V que contiene la carpeta.
        force:     Si True, re-ejecuta rclone aunque .pulled ya exista.

    Returns:
        DriveIntakeResult con el resultado de la operación.

    Raises:
        FileNotFoundError: si el caso no existe en casos_root.
        DriveIntakeError:  si rclone devuelve código de error.
    """
    case_dir = caso_path(case_id)
    if not case_dir.exists():
        raise FileNotFoundError(
            f"El caso '{case_id}' no existe en {settings.casos_root}. "
            "Llama a ensure_case() antes de pull_drive_ev()."
        )

    target_dir = case_dir / "00_Input" / _DRIVE_EV_INPUT_SUBDIR
    target_dir.mkdir(parents=True, exist_ok=True)

    marker = target_dir / _PULL_MARKER

    # --- Idempotencia: skip si .pulled existe y no se fuerza ---
    if marker.exists() and not force:
        files_after = _count_files(target_dir)
        return DriveIntakeResult(
            case_id=case_id,
            team_id=team_id,
            folder_id=folder_id,
            target_dir=target_dir,
            files_after=files_after,
            skipped=True,
        )

    # --- Ejecutar rclone ---
    remote = settings.drive_ev_remote   # "gdrive_ev" por defecto
    cmd = [
        settings.rclone_binary,
        "copy",
        f"{remote}:",
        str(target_dir),
        "--drive-team-drive", team_id,
        "--drive-root-folder-id", folder_id,
        "--stats-one-line-date",
        "--log-level", "INFO",
    ]

    errors: list[str] = []
    returncode = 0

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min
        )
        returncode = result.returncode
        if returncode != 0:
            stderr_tail = result.stderr[-2000:] if result.stderr else ""
            errors.append(f"rclone exit {returncode}: {stderr_tail}")
    except subprocess.TimeoutExpired:
        returncode = -1
        errors.append("rclone timeout (>300 s)")
    except FileNotFoundError:
        returncode = -2
        errors.append(
            f"Binario rclone no encontrado: '{settings.rclone_binary}'. "
            "Verifica RCLONE_BINARY en .env o que rclone esté en el PATH."
        )

    # --- Escribir marcador ---
    marker.write_text(
        json.dumps(
            {
                "team_id": team_id,
                "folder_id": folder_id,
                "last_sync": now_iso(),
                "rclone_returncode": returncode,
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # --- Actualizar _caso.md ---
    if returncode == 0:
        register_drive_ev(case_id, team_id, folder_id)

    files_after = _count_files(target_dir)

    result_obj = DriveIntakeResult(
        case_id=case_id,
        team_id=team_id,
        folder_id=folder_id,
        target_dir=target_dir,
        files_after=files_after,
        skipped=False,
        rclone_returncode=returncode,
        errors=errors,
    )

    if errors:
        raise DriveIntakeError(result_obj)

    return result_obj


# ---------------------------------------------------------------------------
# Resolución de nombre de carpeta E&V
# ---------------------------------------------------------------------------

# Patrón: "Dirección del inmueble - W-XXXXXX[ - <consultor captador>]"
# Acepta guion simple o largo, espacios opcionales alrededor.
# El sufijo posterior, cuando aparece, es el nombre del CONSULTOR que captó
# la propiedad (NO el cliente — los Shared Drives de E&V nombran las carpetas
# así). Se descarta para el auto-fill; no se usa como dato del caso.
# Ejemplo: "393. Hacienda Vadillo - W-02RRO3 - Natalia Trujillano"
_EV_FOLDER_RE = re.compile(
    r"^(.*?)\s*[-–]\s*(W-[A-Z0-9]{5,8})\b",
    re.IGNORECASE,
)


def parse_ev_folder_name(folder_name: str) -> tuple[str, str]:
    """Extrae dirección e ID GO del nombre de carpeta W-XXXXXX de E&V.

    Formato esperado: «Dirección del inmueble - W-XXXXXX»

    Returns:
        Tupla (direccion, mls_id). Cadenas vacías si el formato no coincide.

    Examples::

        parse_ev_folder_name("Pedro Lain Entralgo 4 Chalet 4- W-02W4PJ")
        # → ("Pedro Lain Entralgo 4 Chalet 4", "W-02W4PJ")

        parse_ev_folder_name("Gran Via 40, 3º 1ª – W-030LFT")
        # → ("Gran Via 40, 3º 1ª", "W-030LFT")

        parse_ev_folder_name("393. Hacienda Vadillo - W-02RRO3 - Natalia Trujillano")
        # → ("393. Hacienda Vadillo", "W-02RRO3")
        # (el sufijo "Natalia Trujillano" es el consultor captador, no el cliente; se descarta)
    """
    m = _EV_FOLDER_RE.match(folder_name.strip())
    if m:
        return m.group(1).strip(), m.group(2).upper()
    return "", ""


@dataclass
class DriveFolderInfo:
    """Metadatos básicos de una carpeta de Google Drive E&V."""
    name: str           # Nombre de la carpeta (p.ej. "Gran Via 40 - W-030LFT")
    drive_id: str       # ID del Shared Drive que contiene la carpeta


def _get_drive_access_token() -> str | None:
    """Extrae el access_token OAuth del remote gdrive_ev en rclone.conf."""
    import json as _json
    try:
        result = subprocess.run(
            ["rclone", "config", "show", "gdrive_ev"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("token"):
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    token_json = parts[1].strip()
                    access_token = _json.loads(token_json).get("access_token")
                    return access_token or None
    except Exception:
        pass
    return None


def get_drive_folder_info(folder_id: str) -> DriveFolderInfo | None:
    """Obtiene nombre y Shared Drive ID de una carpeta del Drive E&V.

    Usa la API REST de Google Drive (v3) con el access_token del remote
    ``gdrive_ev`` almacenado en rclone.conf. Devuelve None si el token
    está expirado, la carpeta no existe o cualquier error de red.

    El token se renueva automáticamente cada vez que rclone hace un pull;
    si ha caducado, el auto-fill simplemente no se activa (no es un error
    bloqueante).

    Args:
        folder_id: ID de la carpeta Google Drive (extraído de la URL).

    Returns:
        DriveFolderInfo(name, drive_id), o None si no se pudo obtener.
    """
    access_token = _get_drive_access_token()
    if not access_token:
        return None

    try:
        import httpx
        r = httpx.get(
            f"https://www.googleapis.com/drive/v3/files/{folder_id}",
            params={
                "fields": "name,driveId",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            name = data.get("name", "")
            drive_id = data.get("driveId", "")
            if name:
                return DriveFolderInfo(name=name, drive_id=drive_id)
    except Exception:
        pass
    return None


def get_drive_folder_name(folder_id: str) -> str | None:
    """Obtiene el nombre de una carpeta de Drive E&V dado su folder_id.

    .. deprecated::
        Usar :func:`get_drive_folder_info` que también devuelve el driveId.

    Returns:
        Nombre de la carpeta, o None si no se pudo obtener.
    """
    info = get_drive_folder_info(folder_id)
    return info.name if info else None


# ---------------------------------------------------------------------------
# Excepción
# ---------------------------------------------------------------------------

class DriveIntakeError(RuntimeError):
    """Error durante el pull del Drive E&V. Adjunta el DriveIntakeResult parcial."""

    def __init__(self, result: DriveIntakeResult) -> None:
        self.result = result
        msgs = "; ".join(result.errors) if result.errors else "Error desconocido"
        super().__init__(f"pull_drive_ev falló para '{result.case_id}': {msgs}")


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _count_files(directory: Path) -> int:
    """Cuenta archivos en `directory` (no recursivo), excluyendo archivos de control."""
    _CONTROL = {_PULL_MARKER, "_inventory.json", ".synced"}
    return sum(
        1
        for p in directory.iterdir()
        if p.is_file() and p.name not in _CONTROL
    )
