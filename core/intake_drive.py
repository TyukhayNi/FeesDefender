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
        --drive-skip-shortcuts --ignore-size --ignore-checksum --inplace \\
        --local-encoding {_LOCAL_ENCODING} \\
        --retries 3 --retries-sleep 5s \\
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
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .case_manager import register_drive_ev
from .config import INTAKE_CONTROL_FILES, caso_path, settings
from .utils import now_iso


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_DRIVE_EV_INPUT_SUBDIR = "01_Drive EV"
_PULL_MARKER = ".pulled"

# Ficheros de control del intake que NUNCA son documento (marcadores de
# idempotencia / inventario interno). Pública: la consumen otros módulos
# (p.ej. scripts.abrir_caso.hash_tree_local) para excluirlos del ledger
# forense (_intake_log.jsonl) sin duplicar el literal. Lista ÚNICA en
# config.INTAKE_CONTROL_FILES (MEJORAS #54 T1).
CONTROL_FILES: frozenset[str] = INTAKE_CONTROL_FILES

# Encoding del backend local de rclone para el destino (montaje de Google
# Drive for Desktop en G:\). Es el conjunto estándar de Windows MÁS LeftSpace
# y LeftPeriod: las carpetas E&V contienen ficheros cuyo nombre empieza por un
# espacio (p.ej. " NIE Pasaporte Charlotte.jpg", " ENCARGO DE VENTA NO
# EXCLUSIVA + PBC ANEXO 1.pdf" en VaRS2 - Doctor Angelico 4 - W-02V09K). El
# default de rclone NO codifica el espacio/punto inicial, así que el sistema
# de ficheros virtual de Drive Desktop rechaza la escritura con "The parameter
# is incorrect" (error 87 de Windows) y un único fichero así provoca
# `rclone exit 1` aunque el resto se haya copiado bien. Con LeftSpace/LeftPeriod
# rclone codifica el carácter inicial a su forma visible segura (U+2420 ␠ para
# el espacio) y lo decodifica al releer, de modo que el fichero se crea y
# round-trip-ea correctamente. NOTA: --local-encoding SUSTITUYE al default por
# completo; por eso esta cadena replica el set Windows entero antes de añadir
# los dos tokens nuevos. Cierra [SIGUIENTE-DRIVE-PULL-PARAMETER-INCORRECT].
_LOCAL_ENCODING = (
    "Slash,BackSlash,Colon,Question,Asterisk,Pipe,DoubleQuote,Dot,"
    "SquareBracket,LtGt,Ctl,RightSpace,RightPeriod,InvalidUtf8,"
    "LeftSpace,LeftPeriod"
)

# Backoff (segundos) para reintentar get_drive_folder_info cuando la Drive API
# devuelve 403/429 con reason == rateLimitExceeded. La cuota global del OAuth
# client compartido de rclone (project 202264815644) se reinicia cada minuto;
# los backoffs cubren ese escenario sin bloquear la UI más de ~17 s en total.
_RATE_LIMIT_BACKOFF_SECONDS: tuple[float, ...] = (2.0, 5.0, 10.0)

# Margen de seguridad antes de la expiración nominal del access_token de
# `gdrive_ev`. Si el token vence en menos de este intervalo (o ya está
# vencido), `_get_drive_access_token` fuerza un refresh proactivo vía
# `rclone about gdrive_ev:` (que usa el refresh_token y reescribe la conf).
_TOKEN_EXPIRY_MARGIN = timedelta(minutes=5)

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
    # `localizar` ya lanza el error estructurado del §10, y su mensaje NO lleva
    # la ruta local — el `FileNotFoundError` que habia aqui interpolaba
    # `settings.casos_root`, que el §16 prohibe.
    from core.casos.case_locator import localizar
    case_dir = localizar(case_id)

    # Guard de escritura (DISEÑO_V2 §6): si el caso está prestado/conflicto, el
    # pull se desvía a _pendiente_checkin/drive_ev/... (con evento) en vez del
    # árbol vivo. Si está disponible, destino normal.
    from .case_manager import dir_intake

    target_dir = dir_intake(case_id, f"00_Input/{_DRIVE_EV_INPUT_SUBDIR}", "drive_ev")
    target_dir.mkdir(parents=True, exist_ok=True)

    marker = target_dir / _PULL_MARKER

    # --- Idempotencia: skip si .pulled existe, no se fuerza, y el pull
    # previo terminó OK (rclone_returncode==0). Si el último intento falló
    # (returncode != 0), reintentamos automáticamente sin que el usuario
    # tenga que borrar `.pulled` a mano. Esto evita el modo "pull eternamente
    # bloqueado" cuando un fallo transitorio dejó el marker con un error.
    if marker.exists() and not force:
        # Markers legacy sin `rclone_returncode` (p.ej. `{}`) se tratan como
        # éxito para preservar la idempotencia histórica. Solo se reintenta
        # cuando el marker registra explícitamente returncode != 0.
        prev_returncode: int = 0
        try:
            prev = json.loads(marker.read_text(encoding="utf-8"))
            if isinstance(prev, dict):
                rc = prev.get("rclone_returncode", 0)
                prev_returncode = int(rc) if isinstance(rc, (int, str)) and str(rc).lstrip("-").isdigit() else 0
        except (OSError, json.JSONDecodeError):
            # `.pulled` ilegible / corrupto → tratar como pull previo OK.
            prev_returncode = 0

        if prev_returncode == 0:
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
    # --drive-skip-shortcuts: omite cualquier acceso directo en la jerarquía
    # de la carpeta (los Shared Drive de E&V suelen contener shortcuts a
    # ficheros que el usuario corporativo ha perdido al rotar de cuenta o
    # al ser borrados; sin este flag, un único dangling shortcut provoca
    # rclone exit 1 aunque el resto de ficheros se haya copiado bien).
    #
    # --ignore-size + --ignore-checksum + --inplace: el destino vive en un
    # Shared Drive montado por Google Drive for Desktop (G:\Unidades
    # compartidas\…). Drive Desktop intercepta la escritura: cuando rclone
    # finaliza el `.partial` y lo renombra al fichero final, Drive Desktop
    # reescribe metadatos y `stat()` devuelve un tamaño ligeramente
    # superior al del origen (observado +128, +268 bytes en sesión 21,
    # 2026-05-19, caso BaRS10). Eso dispara "corrupted on transfer: sizes
    # differ" aunque los bytes se hayan transferido al 100%. La integridad
    # real está garantizada por TLS de Drive API en ambos extremos; los
    # tres flags conjuntos suprimen la verificación post-transfer (size +
    # checksum) y eliminan el rename `.partial → final` que es el evento
    # que más confunde a Drive Desktop.
    #
    # --retries 3 / --retries-sleep 5s: cubre errores transitorios de la
    # Drive API (rateLimitExceeded, 5xx). --low-level-retries (default 10)
    # cubre blips de TCP; los --retries cubren el ciclo completo.
    # Cierra [SIGUIENTE-DRIVE-RCLONE-RETRIES] de STATUS.md.
    remote = settings.drive_ev_remote   # "gdrive_ev" por defecto
    cmd = [
        settings.rclone_binary,
        "copy",
        f"{remote}:",
        str(target_dir),
        "--drive-team-drive", team_id,
        "--drive-root-folder-id", folder_id,
        "--drive-skip-shortcuts",
        "--ignore-size",
        "--ignore-checksum",
        "--inplace",
        "--local-encoding", _LOCAL_ENCODING,
        "--retries", "3",
        "--retries-sleep", "5s",
        "--stats-one-line-date",
        "--log-level", "INFO",
    ]

    errors: list[str] = []
    returncode = 0

    try:
        # encoding='utf-8' + errors='replace': los nombres de fichero
        # catalanes/españoles de las carpetas E&V traen caracteres no
        # decodificables con cp1252 (default Windows), lo que producía
        # stderr vacío en los errores de rclone. 'replace' garantiza
        # captura sin lanzar UnicodeDecodeError.
        result = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
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


@dataclass
class DriveFileInfo:
    """Metadatos básicos de un fichero de Google Drive (Parte 2 — rescate de enlaces)."""
    file_id: str
    name: str
    mime_type: str
    size: int | None
    md5: str | None
    modified_time: str | None
    drive_id: str | None


def _parse_rclone_token_block(stdout: str) -> dict | None:
    """Extrae el dict JSON de la línea ``token = {...}`` de ``rclone config show``.

    Devuelve None si no encuentra la línea o si el JSON no parsea.
    """
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped.startswith("token"):
            continue
        parts = stripped.split("=", 1)
        if len(parts) != 2:
            continue
        try:
            data = json.loads(parts[1].strip())
        except Exception:
            return None
        return data if isinstance(data, dict) else None
    return None


def _parse_iso_expiry(value: str) -> datetime:
    """Parsea un timestamp ISO 8601 (con offset o ``Z``) a ``datetime`` UTC.

    rclone escribe ``expiry`` con precisión nanosegundo (hasta 9 dígitos en
    la fracción) y offset numérico, p.ej. ``2026-05-19T10:23:45.123456789+02:00``.
    Python <3.11 sólo admite hasta 6 dígitos en la fracción y no acepta el
    sufijo ``Z`` en ``datetime.fromisoformat``; ambos casos se normalizan aquí.

    Raises:
        ValueError: si el string no parsea como datetime ISO 8601.
    """
    raw = value.strip()
    # Truncar la fracción de segundos a 6 dígitos (microsegundos) preservando
    # el sufijo de zona horaria si lo hay.
    if "." in raw:
        head, _, tail = raw.partition(".")
        frac, tz = tail, ""
        for i, ch in enumerate(tail):
            if not ch.isdigit():
                frac, tz = tail[:i], tail[i:]
                break
        if len(frac) > 6:
            frac = frac[:6]
        raw = f"{head}.{frac}{tz}" if frac else f"{head}{tz}"
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _get_drive_access_token() -> str | None:
    """Devuelve un access_token OAuth vigente del remote ``gdrive_ev``.

    Lee el bloque ``token = {...}`` que rclone almacena en ``rclone.conf``
    para el remote ``gdrive_ev`` y, si el campo ``expiry`` indica que el
    access_token está caducado o vence dentro de :data:`_TOKEN_EXPIRY_MARGIN`,
    fuerza un refresh proactivo ejecutando ``rclone about gdrive_ev:``. Esta
    operación trivial obliga a rclone a usar el ``refresh_token`` para emitir
    un nuevo access_token y reescribir la conf. Tras el refresh, releemos el
    bloque y devolvemos el nuevo access_token.

    Comportamiento defensivo:

    - ``expiry`` ausente o malformado → devuelve el access_token tal cual
      (preserva el comportamiento previo a la renovación proactiva; el
      keep-alive diario mitiga el riesgo en producción).
    - Refresh falla (rclone devuelve != 0 o lanza excepción) → ``None``.
      No devolvemos el access_token caducado: sabemos que dará 401.
    - Lectura inicial falla → ``None``.

    Esta función NO lanza excepciones — todos los fallos se silencian y se
    devuelve ``None`` para que el auto-fill (callers como
    :func:`get_drive_folder_info`) degrade limpiamente.
    """
    # --- 1ª lectura del bloque token ---------------------------------------
    try:
        result = subprocess.run(
            ["rclone", "config", "show", "gdrive_ev"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except Exception:
        return None

    token_data = _parse_rclone_token_block(result.stdout or "")
    if not token_data:
        return None

    access_token = token_data.get("access_token") or None
    expiry_raw = token_data.get("expiry")

    # --- Sin expiry o malformado: comportamiento legado --------------------
    if not expiry_raw:
        return access_token
    try:
        expiry_dt = _parse_iso_expiry(expiry_raw)
    except Exception:
        return access_token

    # --- Vigente con margen suficiente -------------------------------------
    now = datetime.now(timezone.utc)
    if expiry_dt - now > _TOKEN_EXPIRY_MARGIN:
        return access_token

    # --- Caducado o a punto de caducar: forzar refresh ---------------------
    try:
        refresh = subprocess.run(
            ["rclone", "about", "gdrive_ev:"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except Exception:
        return None
    if refresh.returncode != 0:
        return None

    # --- Releer el bloque tras el refresh ----------------------------------
    try:
        result2 = subprocess.run(
            ["rclone", "config", "show", "gdrive_ev"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except Exception:
        return None

    token_data2 = _parse_rclone_token_block(result2.stdout or "")
    if not token_data2:
        return None
    return token_data2.get("access_token") or None


def _is_rate_limit_response(resp) -> bool:
    """Detecta si una respuesta httpx corresponde a un rate-limit de la Drive API.

    Reconoce los códigos de Google API (403/429) cuando el body incluye
    ``reason == rateLimitExceeded`` (cuota global del OAuth client compartido
    de rclone) o ``userRateLimitExceeded`` (cuota por usuario). Es defensivo:
    si el body no parsea como JSON o no tiene la estructura esperada, asume
    que NO es rate-limit (para no entrar en un bucle de reintentos contra un
    error permanente como 403 PERMISSION_DENIED legítimo).
    """
    if resp.status_code not in (403, 429):
        return False
    try:
        body = resp.json()
    except Exception:
        return False
    errors = body.get("error", {}).get("errors", []) if isinstance(body, dict) else []
    for err in errors:
        reason = err.get("reason", "") if isinstance(err, dict) else ""
        if reason in ("rateLimitExceeded", "userRateLimitExceeded"):
            return True
    return False


def get_drive_folder_info(folder_id: str) -> DriveFolderInfo | None:
    """Obtiene nombre y Shared Drive ID de una carpeta del Drive E&V.

    Usa la API REST de Google Drive (v3) con el access_token del remote
    ``gdrive_ev`` almacenado en rclone.conf. Devuelve None si el token
    está expirado, la carpeta no existe o cualquier error de red.

    El token se renueva automáticamente cada vez que rclone hace un pull;
    si ha caducado, el auto-fill simplemente no se activa (no es un error
    bloqueante).

    **Retry on rate-limit**: cuando la Drive API devuelve 403/429 con
    ``reason == rateLimitExceeded`` (síntoma típico de la cuota global
    compartida del OAuth client de rclone), reintenta con backoff exponencial
    según ``_RATE_LIMIT_BACKOFF_SECONDS``. Si tras agotar los reintentos
    sigue rate-limited, devuelve None.

    Args:
        folder_id: ID de la carpeta Google Drive (extraído de la URL).

    Returns:
        DriveFolderInfo(name, drive_id), o None si no se pudo obtener.
    """
    access_token = _get_drive_access_token()
    if not access_token:
        return None

    # Secuencia de esperas: 0 (primer intento, sin sleep) + backoffs.
    attempts = (0.0,) + _RATE_LIMIT_BACKOFF_SECONDS

    try:
        import httpx
    except ImportError:
        return None

    last_resp = None
    for delay in attempts:
        if delay > 0:
            time.sleep(delay)
        try:
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
        except Exception:
            return None

        last_resp = r
        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                return None
            name = data.get("name", "")
            drive_id = data.get("driveId", "")
            if name:
                return DriveFolderInfo(name=name, drive_id=drive_id)
            return None

        # No-200: si es rate-limit, reintentar; cualquier otro fallo (401, 404,
        # 500…) es no-recuperable y termina inmediatamente con None.
        if not _is_rate_limit_response(r):
            return None
        # Es rate-limit → seguir al siguiente backoff.

    # Agotados los reintentos sin obtener 200.
    return None


def get_shared_drive_name(drive_id: str) -> str | None:
    """Obtiene el nombre de una unidad compartida (Shared Drive) de Google Drive.

    Usa la API REST de Google Drive (v3) con el access_token del remote
    ``gdrive_ev``. Devuelve None si el token está expirado, la unidad
    compartida no existe o cualquier error de red.

    **Retry on rate-limit**: cuando la Drive API devuelve 403/429 con
    ``reason == rateLimitExceeded``, reintenta con backoff exponencial
    según ``_RATE_LIMIT_BACKOFF_SECONDS``. Si tras agotar los reintentos
    sigue rate-limited, devuelve None.

    Args:
        drive_id: ID del Shared Drive (obtenido de folder's driveId).

    Returns:
        Nombre del Shared Drive (str), o None si no se pudo obtener.
    """
    # Guard: drive_id vacío
    if not drive_id:
        return None

    access_token = _get_drive_access_token()
    if not access_token:
        return None

    try:
        import httpx
    except ImportError:
        return None

    # Secuencia de esperas: 0 (primer intento, sin sleep) + backoffs.
    attempts = (0.0,) + _RATE_LIMIT_BACKOFF_SECONDS

    for delay in attempts:
        if delay > 0:
            time.sleep(delay)
        try:
            r = httpx.get(
                f"https://www.googleapis.com/drive/v3/drives/{drive_id}",
                params={"fields": "name"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )
        except Exception:
            return None

        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                return None
            name = data.get("name", "")
            if name:
                return name
            return None

        # No-200: si es rate-limit, reintentar; cualquier otro fallo (401, 404,
        # 500…) es no-recuperable y termina inmediatamente con None.
        if not _is_rate_limit_response(r):
            return None
        # Es rate-limit → seguir al siguiente backoff.

    # Agotados los reintentos sin obtener 200.
    return None


def get_drive_folder_info_cached(
    folder_id: str,
    case_id: str | None = None,
) -> DriveFolderInfo | None:
    """Como :func:`get_drive_folder_info`, pero lee primero del cache en ``_caso.md``.

    Si *case_id* se proporciona, intenta leer ``drive_ev_folder_name`` y
    ``drive_ev_drive_id`` del frontmatter del caso. En caso de hit, devuelve
    sin llamar a la Drive API. En caso de miss o si *case_id* es None, llama
    a la API y, si tiene éxito y *case_id* fue proporcionado, persiste el
    resultado en ``_caso.md`` para futuros pulls.
    """
    if case_id:
        from core.case_manager import get_cached_drive_folder_info, cache_drive_folder_info

        cached_name, cached_drive_id = get_cached_drive_folder_info(case_id)
        if cached_name:
            return DriveFolderInfo(name=cached_name, drive_id=cached_drive_id or "")

    info = get_drive_folder_info(folder_id)

    if info and case_id:
        from core.case_manager import cache_drive_folder_info
        cache_drive_folder_info(case_id, info.name, info.drive_id)

    return info


def get_drive_folder_name(folder_id: str) -> str | None:
    """Obtiene el nombre de una carpeta de Drive E&V dado su folder_id.

    .. deprecated::
        Usar :func:`get_drive_folder_info` o :func:`get_drive_folder_info_cached`.

    Returns:
        Nombre de la carpeta, o None si no se pudo obtener.
    """
    info = get_drive_folder_info(folder_id)
    return info.name if info else None


# ---------------------------------------------------------------------------
# Drive REST a nivel de FICHERO (Parte 2 — rescate de enlaces a Drive)
# ---------------------------------------------------------------------------

def get_drive_file_info(file_id: str) -> "DriveFileInfo | None":
    """Metadatos de un fichero del Drive E&V (``files.get``), o ``None`` si falla.

    Reutiliza el access_token de ``gdrive_ev`` (refresh + rate-limit ya resueltos en
    :func:`_get_drive_access_token`). Degradación limpia: ``None`` ante 401/403/404,
    red caída, token ausente o ``httpx`` no disponible. Reintenta con backoff solo ante
    rate-limit (cuota compartida del OAuth client de rclone).
    """
    access_token = _get_drive_access_token()
    if not access_token:
        return None
    try:
        import httpx
    except ImportError:
        return None

    for delay in (0.0,) + _RATE_LIMIT_BACKOFF_SECONDS:
        if delay > 0:
            time.sleep(delay)
        try:
            r = httpx.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                params={
                    "fields": "id,name,mimeType,size,md5Checksum,modifiedTime,driveId",
                    "supportsAllDrives": "true",
                },
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
        except Exception:
            return None
        if r.status_code == 200:
            try:
                d = r.json()
            except Exception:
                return None
            raw_size = d.get("size")
            try:
                size = int(raw_size) if raw_size is not None else None
            except (TypeError, ValueError):
                size = None
            return DriveFileInfo(
                file_id=d.get("id", file_id),
                name=d.get("name", ""),
                mime_type=d.get("mimeType", ""),
                size=size,
                md5=d.get("md5Checksum"),
                modified_time=d.get("modifiedTime"),
                drive_id=d.get("driveId"),
            )
        if not _is_rate_limit_response(r):
            return None  # 401/404/permiso/5xx no recuperable
    return None


def download_drive_media(file_id: str) -> bytes | None:
    """Descarga byte-fiel del contenido de un fichero Drive (``files.get?alt=media``).

    Solo para binarios (un doc nativo de Google devuelve error; no se llama para esos).
    Devuelve los bytes, o ``None`` ante cualquier fallo (mismo patrón de degradación y
    retry de rate-limit que :func:`get_drive_file_info`). Timeout amplio: ficheros grandes.
    """
    access_token = _get_drive_access_token()
    if not access_token:
        return None
    try:
        import httpx
    except ImportError:
        return None

    for delay in (0.0,) + _RATE_LIMIT_BACKOFF_SECONDS:
        if delay > 0:
            time.sleep(delay)
        try:
            r = httpx.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                params={"alt": "media", "supportsAllDrives": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=60,
            )
        except Exception:
            return None
        if r.status_code == 200:
            return r.content
        if not _is_rate_limit_response(r):
            return None
    return None


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
    return sum(
        1
        for p in directory.iterdir()
        if p.is_file() and p.name not in CONTROL_FILES
    )
