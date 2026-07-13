"""Autenticación OAuth y gestión de cuentas para el MCP gmail-multiaccount.

SCOPE ÚNICO: gmail.modify (lectura + etiquetado). `gmail.modify` subsume
`gmail.readonly` → las tools de lectura siguen funcionando; y NO permite borrado
permanente ni IMAP/SMTP total (eso exige mail.google.com), por lo que el borrado
queda descartado a nivel de scope, no solo de tools. El alcance se fija aquí y NO
se parametriza: ampliarlo exige una edición consciente de este fichero +
reautorización de cada cuenta.

Config (por defecto ~/.gmail-mcp, override GMAIL_MCP_HOME):
    $GMAIL_MCP_HOME/
        credentials.json          <- secreto OAuth de cliente (App de escritorio); lo aportas tú
        tokens/
            cuenta@dominio.com.json   <- token por cuenta (autogenerado)
"""
from __future__ import annotations

import os
from pathlib import Path

# Los paquetes de Google se importan de forma perezosa dentro de las funciones
# (patrón de google_despacho_mcp/google_auth.py) para que el módulo sea importable
# sin ellos (tests bajo .venv).

# Alcance: gmail.modify. Se fija aquí y NO se parametriza.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def config_home() -> Path:
    """Directorio raíz de configuración."""
    home = os.environ.get("GMAIL_MCP_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".gmail-mcp"
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
    """Devuelve las direcciones de las cuentas con token guardado."""
    return sorted(p.stem for p in tokens_dir().glob("*.json"))


def load_credentials(email: str):
    """Carga (y refresca si procede) las credenciales de una cuenta autenticada."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    path = _token_path(email)
    if not path.exists():
        raise FileNotFoundError(
            f"La cuenta '{email}' no está autenticada. "
            f"Ejecuta: python -m plugins.gmail_mcp.gmail_cli add"
        )
    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json())
    if not creds or not creds.valid:
        raise RuntimeError(
            f"Las credenciales de '{email}' no son válidas. Reautentica: "
            f"python -m plugins.gmail_mcp.gmail_cli add"
        )
    return creds


def build_service(email: str):
    """Construye el cliente de la API de Gmail v1 para una cuenta."""
    from googleapiclient.discovery import build

    creds = load_credentials(email)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# --- Operaciones interactivas (uso desde el CLI, NUNCA desde el servidor MCP) ---

def add_account() -> str:
    """Lanza el flujo OAuth en el navegador y guarda el token de una cuenta.

    Devuelve la dirección de correo autenticada (resuelta vía getProfile).
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

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    profile = service.users().getProfile(userId="me").execute()
    email = profile["emailAddress"]

    _token_path(email).write_text(creds.to_json())
    return email


def remove_account(email: str) -> bool:
    """Elimina el token local. No revoca en Google (hazlo en la cuenta)."""
    path = _token_path(email)
    if path.exists():
        path.unlink()
        return True
    return False
