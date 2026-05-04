"""Compartir carpetas del Drive engelvoelkers.com con el equipo tyukhay.legal.

Dos modos de operación:

1. **Compartición directa** — Drive API v3 (``permissions.create``).
   Usa el ``access_token`` del remote ``gdrive_ev`` en rclone.conf.
   Puede fallar si:
     · el token está expirado (reclama un re-pull de rclone para refrescarlo),
     · la cuenta no tiene permiso de compartición en ese Shared Drive, o
     · la política de dominio de engelvoelkers.com bloquea compartir con externos.
   En cualquiera de esos casos devuelve el error en ``ShareResult.error``.

2. **Mensaje de solicitud** — ``build_request_email(folder_url)`` construye
   el texto del email listo para copiar/enviar a un compañero de E&V que sí
   tenga permisos de compartición. Siempre disponible, sin dependencias.

Configuración:
  - Ruta de rclone.conf: env var ``RCLONE_CONF`` (default Windows).
  - Remote a usar: ``gdrive_ev`` (fijo, igual que en intake_drive.py).
"""

from __future__ import annotations

import configparser
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Emails fijos del equipo tyukhay.legal a quienes compartir la carpeta E&V
TEAM_EMAILS: tuple[str, ...] = (
    "ana.velastegui@tyukhay.legal",
    "paola.barreto@tyukhay.legal",
    "sergio.pinol@tyukhay.legal",
)

# Remoto rclone con credenciales engelvoelkers.com (debe coincidir con intake_drive.py)
_GDRIVE_EV_REMOTE = "gdrive_ev"

# Ruta por defecto de rclone.conf — sobreescribible con RCLONE_CONF en .env
_RCLONE_CONF_DEFAULT = Path(r"C:\Users\tnm33\AppData\Roaming\rclone\rclone.conf")
_RCLONE_CONF: Path = Path(os.getenv("RCLONE_CONF", str(_RCLONE_CONF_DEFAULT)))

# Drive API v3
_DRIVE_API_PERMISSIONS = "https://www.googleapis.com/drive/v3/files/{file_id}/permissions"


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

@dataclass
class ShareResult:
    """Resultado de compartición para un email concreto."""
    email: str
    success: bool
    error: str = ""


@dataclass
class ShareFolderResult:
    """Resultado agregado de compartición de una carpeta con el equipo."""
    folder_id: str
    results: list[ShareResult] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return bool(self.results) and all(r.success for r in self.results)

    @property
    def any_ok(self) -> bool:
        return any(r.success for r in self.results)

    @property
    def n_ok(self) -> int:
        return sum(1 for r in self.results if r.success)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def share_folder_with_team(
    folder_id: str,
    *,
    role: str = "reader",
) -> ShareFolderResult:
    """Comparte la carpeta con los emails del equipo tyukhay.legal.

    Llama a ``permissions.create`` en Drive API v3 usando el ``access_token``
    almacenado en rclone.conf para el remote ``gdrive_ev``.

    Args:
        folder_id: ID de la carpeta en el Drive engelvoelkers.com.
        role:      Permiso a conceder: ``'reader'``, ``'commenter'`` o ``'writer'``.

    Returns:
        :class:`ShareFolderResult` con el resultado por cada email.

    Raises:
        ShareDriveConfigError: si no se puede leer el token de rclone.conf.
    """
    access_token = _read_access_token()

    result = ShareFolderResult(folder_id=folder_id)
    url = _DRIVE_API_PERMISSIONS.format(file_id=folder_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    for email in TEAM_EMAILS:
        body = {
            "type": "user",
            "role": role,
            "emailAddress": email,
        }
        try:
            resp = httpx.post(
                url,
                headers=headers,
                json=body,
                params={"sendNotificationEmail": "false"},
                timeout=15.0,
            )
            if resp.status_code in (200, 201):
                result.results.append(ShareResult(email=email, success=True))
            else:
                # Intentar extraer el mensaje de error de Google
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text[:300])
                except Exception:
                    err_msg = resp.text[:300]
                result.results.append(ShareResult(
                    email=email,
                    success=False,
                    error=f"HTTP {resp.status_code}: {err_msg}",
                ))
        except httpx.TimeoutException:
            result.results.append(ShareResult(
                email=email,
                success=False,
                error="Timeout al llamar a Drive API (>15 s).",
            ))
        except Exception as exc:
            result.results.append(ShareResult(
                email=email,
                success=False,
                error=str(exc),
            ))

    return result


def build_request_email(folder_url: str) -> str:
    """Construye el mensaje de solicitud de compartición para enviar a compañeros de E&V.

    Args:
        folder_url: URL completa de la carpeta W-XXXXXX en Google Drive.

    Returns:
        Texto del email listo para copiar.
    """
    emails_str = "\n".join(f"  · {e}" for e in TEAM_EMAILS)
    return (
        "Hola compañeros,\n\n"
        "Por favor, compartir la carpeta de esta propiedad con mi equipo.\n\n"
        f"Enlace a la carpeta: {folder_url}\n\n"
        "Emails a añadir:\n"
        f"{emails_str}\n\n"
        "Necesitan el acceso para preparar la reclamación de los honorarios/"
        "la defensa contra la demanda.\n\n"
        "Gracias por vuestra ayuda.\n\n"
        "Nikolai Tyukhay\n"
        "Abogado\n"
        "EV MMC SPAIN, S.L.U."
    )


def is_token_likely_valid() -> bool:
    """Comprueba si el access_token en rclone.conf parece vigente.

    Devuelve False si no se puede leer o si el campo ``expiry`` indica
    que ya ha caducado. No garantiza que Google lo acepte (puede haberse
    revocado), pero evita llamadas inútiles.
    """
    try:
        token = _read_token_data()
        expiry_raw = token.get("expiry", "")
        if not expiry_raw:
            return True  # sin campo expiry → asumimos válido
        # rclone guarda el expiry como RFC3339 con nanosegundos opcionales:
        # "2026-05-04T14:32:00.123456789Z"
        expiry_clean = expiry_raw.split(".")[0].rstrip("Z") + "+00:00"
        expiry_dt = datetime.fromisoformat(expiry_clean)
        return expiry_dt > datetime.now(timezone.utc)
    except Exception:
        return True  # en caso de duda, intentar


# ---------------------------------------------------------------------------
# Excepción
# ---------------------------------------------------------------------------

class ShareDriveConfigError(RuntimeError):
    """No se puede leer la configuración necesaria para compartir."""


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _read_rclone_config() -> configparser.ConfigParser:
    if not _RCLONE_CONF.exists():
        raise ShareDriveConfigError(
            f"rclone.conf no encontrado: {_RCLONE_CONF}.\n"
            "Configura RCLONE_CONF en .env si está en una ruta distinta."
        )
    cp = configparser.ConfigParser()
    cp.read(_RCLONE_CONF, encoding="utf-8")
    if _GDRIVE_EV_REMOTE not in cp:
        raise ShareDriveConfigError(
            f"Remote '{_GDRIVE_EV_REMOTE}' no encontrado en rclone.conf."
        )
    return cp


def _read_token_data() -> dict:
    cp = _read_rclone_config()
    raw = cp[_GDRIVE_EV_REMOTE].get("token", "{}")
    return json.loads(raw)


def _read_access_token() -> str:
    token = _read_token_data()
    access_token = token.get("access_token", "")
    if not access_token:
        raise ShareDriveConfigError(
            f"access_token vacío en rclone.conf (remote '{_GDRIVE_EV_REMOTE}'). "
            "Ejecuta un `rclone ls gdrive_ev:` para refrescar el token."
        )
    return access_token
