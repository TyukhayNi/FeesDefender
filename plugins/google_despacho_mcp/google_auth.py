"""Autenticación OAuth y gestión de cuentas para el MCP google-despacho.

SCOPE F2: drive (lectura + escritura). El alcance se fija aquí y NO se
parametriza, para que ampliarlo exija una edición consciente de este fichero.

Config (por defecto ~/.google-despacho, override GOOGLE_DESPACHO_HOME):
    $GOOGLE_DESPACHO_HOME/
        credentials.json              <- secreto OAuth de cliente (App de escritorio); lo aportas tú
        tokens/
            cuenta@dominio.com.json   <- token por cuenta (autogenerado)

Un solo credentials.json para ambas cuentas (R2: un único proyecto Cloud).
"""
from __future__ import annotations

import os
from pathlib import Path

# Los paquetes de Google se importan de forma perezosa dentro de las funciones
# (patrón de core/gmail_source.py) para que el módulo sea importable sin ellos
# (tests bajo .venv).

# Alcance F2: Drive completo (lectura + escritura + permisos). `drive` subsume
# `drive.readonly`, así que las tools de lectura de F1 siguen funcionando. Se fija
# aquí y NO se parametriza: ampliarlo exige edición consciente + reautorización de
# cada cuenta. `drive.file` NO sirve (solo ficheros creados por la app; F2 toca
# expedientes existentes).
SCOPES = ["https://www.googleapis.com/auth/drive"]


def config_home() -> Path:
    home = os.environ.get("GOOGLE_DESPACHO_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".google-despacho"
    base.mkdir(parents=True, exist_ok=True)
    (base / "tokens").mkdir(parents=True, exist_ok=True)
    return base


def credentials_path() -> Path:
    return config_home() / "credentials.json"


def tokens_dir() -> Path:
    return config_home() / "tokens"


def _token_path(email: str) -> Path:
    return tokens_dir() / f"{email}.json"


def list_account_emails() -> list[str]:
    return sorted(p.stem for p in tokens_dir().glob("*.json"))


def load_credentials(email: str) -> Credentials:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    path = _token_path(email)
    if not path.exists():
        raise FileNotFoundError(
            f"La cuenta '{email}' no está autenticada. "
            f"Ejecuta: python plugins/google_despacho_mcp/google_cli.py add"
        )
    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json())
    if not creds or not creds.valid:
        raise RuntimeError(
            f"Las credenciales de '{email}' no son válidas. Reautentica: "
            f"python plugins/google_despacho_mcp/google_cli.py add"
        )
    return creds


def build_service(email: str):
    """Construye el cliente de la API de Drive v3 para una cuenta."""
    from googleapiclient.discovery import build

    creds = load_credentials(email)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# --- Operaciones interactivas (uso desde el CLI, NUNCA desde el servidor MCP) ---

def add_account() -> str:
    """Lanza el flujo OAuth en el navegador y guarda el token de una cuenta.

    Devuelve la dirección de correo autenticada (resuelta vía about.get).
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds_file = credentials_path()
    if not creds_file.exists():
        raise FileNotFoundError(
            f"No existe {creds_file}. Descarga el secreto OAuth de cliente "
            f"(tipo 'App de escritorio') desde Google Cloud Console y guárdalo ahí."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")

    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    about = service.about().get(fields="user(emailAddress)").execute()
    email = about["user"]["emailAddress"]

    _token_path(email).write_text(creds.to_json())
    return email


def remove_account(email: str) -> bool:
    """Elimina el token local. No revoca en Google (hazlo en la cuenta)."""
    path = _token_path(email)
    if path.exists():
        path.unlink()
        return True
    return False
