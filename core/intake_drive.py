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
from .config import caso_path, settings
from .intake_control import es_fichero_de_protocolo
from .utils import now_iso


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_DRIVE_EV_INPUT_SUBDIR = "01_Drive EV"
_PULL_MARKER = ".pulled"


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
# vencido), `obtener_token_drive` fuerza un refresh proactivo vía
# `rclone about gdrive_ev:` (que usa el refresh_token y reescribe la conf).
_TOKEN_EXPIRY_MARGIN = timedelta(minutes=5)

#: Lo que se le da a `rclone config show` y a `rclone about` para leer y renovar el token. No
#: tardan lo mismo siempre: 0,1 s en reposo y 3,9-6,7 s con otra corrida de rclone en marcha
#: (medido en las aperturas de W-02UIQU y W-02Y2J6, 2026-09-25). Con 5 s el timeout se tragaba
#: como «no hay token» y el alta abortaba diciendo «token/red» con el token vigente
#: (`MEJORAS #296`). Un rclone colgado de verdad cuesta ahora 30 s, y se dice.
_TIMEOUT_RCLONE_TOKEN = 30

#: Lo que `rclone config show` escribe, con código 0, si el remote no existe (medido con rclone
#: real el 2026-09-26): el código de salida no lo dice.
_REMOTE_INEXISTENTE = "couldn't find type of fs"

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
    #: Ficheros del destino que el recorrido de custodia **no pudo leer** (`MEJORAS #214`).
    #: **Lo rellena la custodia, no el pull**: `scripts/abrir_caso._intake_drive_ev` lo
    #: adjunta tras hashear el destino. Un `()` que venga de `pull_drive_ev` a pelo
    #: significa «nadie lo ha verificado», no «todo cuadró» — quien lo lea sin pasar por
    #: la custodia está leyendo un campo que nadie ha rellenado.
    custodia_sin_verificar: tuple = ()


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

# El W-code DELANTE (`MEJORAS #301`): «W-02UIQU - <dirección> - <consultor>», con guion o con un
# espacio tras el código. Lo usa la plaza de Santander y no solo ella: el censo del 2026-09-26
# sobre 53 unidades contó 231 carpetas así (185 con guion detrás, 46 con espacio), y ninguna
# parseaba. La dirección es lo que queda hasta el ÚLTIMO « - », que es el consultor si lo hay:
# la misma convención que en el orden de siempre. Solo separa el guion rodeado de espacios —el
# «1-2» de un piso no—.
_EV_FOLDER_W_DELANTE_RE = re.compile(
    r"^(W-[A-Z0-9]{5,8})\b\s*(?:[-–]\s+|\s+|$)(.*)$",
    re.IGNORECASE,
)
_SEPARADOR_DE_TRAMO_RE = re.compile(r"\s+[-–]\s+")


def parse_ev_folder_name(folder_name: str) -> tuple[str, str]:
    """Extrae dirección e ID GO del nombre de carpeta W-XXXXXX de E&V.

    Formatos: «Dirección del inmueble - W-XXXXXX[ - consultor]» y, con el W-code delante,
    «W-XXXXXX - Dirección[ - consultor]» (`MEJORAS #301`). Un W-code en medio sin guion delante
    no se interpreta: el censo los encontró con paréntesis, `_` y fechas alrededor, y ahí el
    prefijo no es una dirección, así que se pide el flag.

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

        parse_ev_folder_name("W-02UIQU - Calle Mayor 5 - Ana P")
        # → ("Calle Mayor 5", "W-02UIQU")
    """
    nombre = folder_name.strip()
    m = _EV_FOLDER_RE.match(nombre)
    if m:
        return m.group(1).strip(), m.group(2).upper()
    m = _EV_FOLDER_W_DELANTE_RE.match(nombre)
    if m:
        tramos = [x.strip() for x in _SEPARADOR_DE_TRAMO_RE.split(m.group(2).strip()) if x.strip()]
        direccion = " - ".join(tramos[:-1]) if len(tramos) >= 2 else "".join(tramos)
        return direccion, m.group(1).upper()
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


@dataclass(frozen=True)
class TokenDrive:
    """El access_token de `gdrive_ev`, o el motivo de que no lo haya.

    `motivo` es una frase para el operador —vacía cuando hay token— y **nunca** lleva nada de la
    salida de rclone, que escribe el token y el `client_secret` en claro.
    """
    token: str | None
    motivo: str = ""


def _leer_bloque_token(remote: str = "gdrive_ev") -> tuple[dict | None, str]:
    """El bloque `token = {...}` de `rclone config show <remote>`, o por qué no se pudo leer.

    El único sitio que lanza esa orden: sirve a la lectura inicial y a la de después de
    renovar, que hasta `MEJORAS #296` eran dos copias con su propio timeout de 5 s.
    """
    orden = f"`rclone config show {remote}`"
    try:
        r = subprocess.run(
            ["rclone", "config", "show", remote],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=_TIMEOUT_RCLONE_TOKEN,
        )
    except FileNotFoundError:
        return None, "rclone no está instalado o no está en el PATH"
    except subprocess.TimeoutExpired:
        return None, (f"{orden} tardó más de {_TIMEOUT_RCLONE_TOKEN} s (¿otra corrida de rclone "
                      "en marcha?)")
    except Exception as exc:                                   # noqa: BLE001
        return None, f"{orden} falló ({type(exc).__name__})"
    salida = r.stdout or ""
    if r.returncode != 0:
        return None, f"{orden} salió con código {r.returncode}"
    if _REMOTE_INEXISTENTE in salida:
        return None, f"el remote `{remote}` no existe en la configuración de rclone"
    datos = _parse_rclone_token_block(salida)
    if not datos:
        return None, f"el remote `{remote}` no tiene un bloque `token` legible (¿falta el login?)"
    return datos, ""


def obtener_token_drive() -> TokenDrive:
    """Un access_token OAuth vigente del remote ``gdrive_ev``, o el motivo de que no lo haya.

    Lee el bloque ``token = {...}`` que rclone guarda en ``rclone.conf`` y, si ``expiry`` dice
    que está caducado o vence dentro de :data:`_TOKEN_EXPIRY_MARGIN`, fuerza una renovación con
    ``rclone about gdrive_ev:`` —una orden trivial que obliga a rclone a usar el
    ``refresh_token`` y reescribir la conf— y lo relee.

    Comportamiento defensivo, el de siempre:

    - ``expiry`` ausente o malformado → el access_token tal cual (el keep-alive diario mitiga
      el riesgo).
    - La renovación falla → sin token: el caducado daría 401.

    **Lo que añade `MEJORAS #296`: el motivo.** Hasta el 2026-09-26 todo fallo —rclone lento,
    ausente, un remote inexistente, un token sin bloque— era el mismo ``None``, y quien lo pintaba
    elegía una causa: el alta decía «token/red». Ahora cada salida sin token dice cuál fue.
    """
    datos, motivo = _leer_bloque_token()
    if datos is None:
        return TokenDrive(None, motivo)
    access = datos.get("access_token") or None
    sin_access = "el bloque `token` de `gdrive_ev` no trae access_token"
    expiry_raw = datos.get("expiry")

    # Sin expiry o malformado: comportamiento legado.
    if not expiry_raw:
        return TokenDrive(access, "" if access else sin_access)
    try:
        expiry_dt = _parse_iso_expiry(expiry_raw)
    except Exception:                                          # noqa: BLE001
        return TokenDrive(access, "" if access else sin_access)

    # Vigente con margen suficiente.
    if expiry_dt - datetime.now(timezone.utc) > _TOKEN_EXPIRY_MARGIN:
        return TokenDrive(access, "" if access else sin_access)

    # Caducado o a punto: forzar la renovación.
    try:
        refresh = subprocess.run(
            ["rclone", "about", "gdrive_ev:"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=_TIMEOUT_RCLONE_TOKEN,
        )
    except FileNotFoundError:
        return TokenDrive(None, "rclone no está instalado o no está en el PATH")
    except subprocess.TimeoutExpired:
        return TokenDrive(None, ("el token estaba caducado y renovarlo (`rclone about gdrive_ev:`) "
                                 f"tardó más de {_TIMEOUT_RCLONE_TOKEN} s"))
    except Exception as exc:                                   # noqa: BLE001
        return TokenDrive(None, f"el token estaba caducado y renovarlo falló ({type(exc).__name__})")
    if refresh.returncode != 0:
        return TokenDrive(None, ("el token estaba caducado y la renovación (`rclone about "
                                 f"gdrive_ev:`) salió con código {refresh.returncode}"))

    datos2, motivo2 = _leer_bloque_token()
    if datos2 is None:
        return TokenDrive(None, f"tras renovar el token, {motivo2}")
    access2 = datos2.get("access_token") or None
    return TokenDrive(access2, "" if access2 else f"tras renovar el token, {sin_access}")


def _get_drive_access_token() -> str | None:
    """El access_token vigente de ``gdrive_ev``, o ``None``: :func:`obtener_token_drive` sin el
    motivo. Se conserva para quien solo necesita el token; quien vaya a decirle al operador por
    qué no lo hay, que llame a :func:`obtener_token_drive` (`MEJORAS #296`). No lanza."""
    return obtener_token_drive().token


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


def leer_carpeta_drive(folder_id: str) -> tuple[DriveFolderInfo | None, str]:
    """Nombre y Shared Drive ID de una carpeta del Drive E&V, **o por qué no se pudo leer**.

    Usa la API REST de Google Drive (v3) con el access_token del remote ``gdrive_ev``
    (:func:`obtener_token_drive`). El motivo, vacío si hay carpeta, distingue el token —con su
    causa—, la red, un HTTP que no es 200 y la cuota agotada: el alta decía «token/red» ante
    cualquiera de ellos (`MEJORAS #296`).

    **Retry on rate-limit**: cuando la Drive API devuelve 403/429 con
    ``reason == rateLimitExceeded`` (la cuota global compartida del OAuth client de rclone),
    reintenta con backoff exponencial según ``_RATE_LIMIT_BACKOFF_SECONDS``.
    """
    token = obtener_token_drive()
    if not token.token:
        return None, f"no hay token de `gdrive_ev`: {token.motivo}"
    access_token = token.token

    # Secuencia de esperas: 0 (primer intento, sin sleep) + backoffs.
    attempts = (0.0,) + _RATE_LIMIT_BACKOFF_SECONDS

    try:
        import httpx
    except ImportError:
        return None, "falta el paquete httpx"

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
        except Exception as exc:                               # noqa: BLE001
            return None, f"la Drive API no respondió ({type(exc).__name__})"

        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:                                  # noqa: BLE001
                return None, "la Drive API devolvió una respuesta ilegible"
            name = data.get("name", "")
            if name:
                return DriveFolderInfo(name=name, drive_id=data.get("driveId", "")), ""
            return None, "la Drive API devolvió la carpeta sin nombre"

        # No-200: si es rate-limit, reintentar; cualquier otro fallo (401, 404, 500…) es
        # no-recuperable y termina aquí.
        if not _is_rate_limit_response(r):
            pista = {401: ": el token no vale", 403: ": sin permiso sobre la carpeta",
                     404: ": la carpeta no existe o esta cuenta no la ve"}.get(r.status_code, "")
            return None, f"la Drive API respondió HTTP {r.status_code}{pista}"

    return None, (f"la Drive API siguió limitando por cuota tras {len(attempts)} intentos "
                  "(rateLimitExceeded)")


def get_drive_folder_info(folder_id: str) -> DriveFolderInfo | None:
    """:func:`leer_carpeta_drive` sin el motivo: la carpeta o ``None``.

    Se conserva para quien solo necesita el dato —el auto-fill de Streamlit, el cache de
    ``_caso.md``—; quien vaya a decirle al operador por qué no hay carpeta, que llame a
    :func:`leer_carpeta_drive` (`MEJORAS #296`).
    """
    return leer_carpeta_drive(folder_id)[0]


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
    """Cuenta archivos en `directory` (no recursivo), sin el protocolo de ESE directorio.

    `directory` es `00_Input/01_Drive EV`; su único fichero de protocolo es `.pulled`
    (`intake_control.ENTREGA`, MEJORAS #149). Un `.synced` o un `_inventory.json` ahí son
    ficheros de E&V y cuentan.
    """
    return sum(
        1
        for p in directory.iterdir()
        if p.is_file() and not es_fichero_de_protocolo(f"{directory.name}/{p.name}")
    )
