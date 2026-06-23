"""F2 — Adaptador Gmail: fuente de correo real para el runner de ingesta.

Dos capas:

- **Pura (testeable, sin red):** ``gmail_message_to_email`` parsea la respuesta de
  ``users.messages.get(format='full')`` → ``EmailMessage``.
- **Fetch (glue):** ``fetch_emails`` carga las credenciales OAuth por cuenta
  (``~/.gmail-mcp/tokens/<cuenta>.json``, formato ``google.oauth2.credentials``),
  refresca si caducó, lista mensajes por query y los parsea. Requiere
  ``google-api-python-client`` + ``google-auth`` (import perezoso para no
  acoplar la capa pura ni los tests).

Clave del §4: ``email_id`` = cabecera **Message-ID** (estable entre los 4 buzones
del despacho), NO el id por-cuenta de Gmail — así el mismo correo recibido en
varias bandejas se deduplica a uno.

RGPD: excepción acotada SOLO a este flujo. Los tokens nunca pasan por el LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .intake_utils import decode_base64url
from .procurador_intake import extract_signals, match_expediente
from .procurador_runner import EmailMessage, ReviewItem, run_intake

# Tokens del MCP gmail-ro (reutilizados; formato google-auth).
GMAIL_TOKENS_DIR = Path.home() / ".gmail-mcp" / "tokens"

# Buzones del despacho (procesal@ reenvía a los 4 abogados; ver plan §4).
# El mismo Message-ID en varios buzones se dedup en run_intake.
BUZONES_DESPACHO: tuple[str, ...] = (
    "procesal@tyukhay.legal",
)

# Query Gmail por defecto: no leídos, excluyendo categorías de ruido evidente.
DEFAULT_QUERY = "is:unread -category:promotions -category:social"


# ---------------------------------------------------------------------------
# Capa pura — parseo de un mensaje de la Gmail API
# ---------------------------------------------------------------------------

def _headers_dict(payload: dict[str, Any]) -> dict[str, str]:
    """Cabeceras del payload como dict en minúscula (case-insensitive)."""
    return {
        (h.get("name") or "").lower(): (h.get("value") or "")
        for h in payload.get("headers", [])
    }


def _decode_b64url(data: str) -> str:
    """Decodifica el body base64url de Gmail (con padding tolerante)."""
    return decode_base64url(data)


def _extract_text_plain(payload: dict[str, Any]) -> str:
    """Recorre el árbol MIME y devuelve el primer ``text/plain`` decodificado."""
    if payload.get("mimeType") == "text/plain":
        data = (payload.get("body") or {}).get("data")
        if data:
            return _decode_b64url(data)
    for part in payload.get("parts", []) or []:
        txt = _extract_text_plain(part)
        if txt:
            return txt
    return ""


def gmail_message_to_email(raw: dict[str, Any], *, mailbox: str | None = None) -> EmailMessage:
    """Convierte un mensaje ``format='full'`` de la Gmail API en ``EmailMessage``."""
    payload = raw.get("payload") or {}
    headers = _headers_dict(payload)
    msg_id = headers.get("message-id", "").strip().strip("<>").strip()
    return EmailMessage(
        email_id=msg_id or raw.get("id", ""),
        from_addr=headers.get("from", ""),
        subject=headers.get("subject", ""),
        body=_extract_text_plain(payload).strip(),
        date=headers.get("date") or None,
        mailbox=mailbox,
    )


# ---------------------------------------------------------------------------
# Capa de fetch — credenciales + llamada a la Gmail API
# ---------------------------------------------------------------------------

_GMAIL_READONLY = "https://www.googleapis.com/auth/gmail.readonly"


def _load_credentials(account: str, *, tokens_dir: Path = GMAIL_TOKENS_DIR):
    """Carga las credenciales OAuth de una cuenta y las refresca si caducaron.

    Reutiliza el token del MCP gmail-ro (formato ``google.oauth2.credentials``).
    Si se refrescan, se reescribe el fichero para no re-autenticar cada vez.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_path = tokens_dir / f"{account}.json"
    if not token_path.exists():
        raise FileNotFoundError(
            f"No hay token para {account!r} en {tokens_dir}. "
            "Autoriza la cuenta con el MCP gmail-ro primero."
        )
    creds = Credentials.from_authorized_user_file(str(token_path))
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _build_service(creds):
    """Construye el cliente de la Gmail API (sin caché de discovery)."""
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def fetch_emails(
    account: str = "procesal@tyukhay.legal",
    *,
    query: str = DEFAULT_QUERY,
    max_results: int = 50,
    tokens_dir: Path = GMAIL_TOKENS_DIR,
    service: Any = None,
) -> list[EmailMessage]:
    """Trae correos de una cuenta que casan ``query`` → lista de ``EmailMessage``.

    Solo lectura. ``service`` se inyecta en tests (boundary de red); en producción
    se construye desde el token de la cuenta. NO marca nada como leído ni escribe
    en Gmail.
    """
    if service is None:
        service = _build_service(_load_credentials(account, tokens_dir=tokens_dir))

    msgs = service.users().messages()
    listing = msgs.list(userId="me", q=query, maxResults=max_results).execute()

    out: list[EmailMessage] = []
    for ref in listing.get("messages", []) or []:
        raw = msgs.get(userId="me", id=ref["id"], format="full").execute()
        out.append(gmail_message_to_email(raw, mailbox=account))
    return out


def fetch_and_run(
    accounts: tuple[str, ...] = BUZONES_DESPACHO,
    *,
    query: str = DEFAULT_QUERY,
    store_path: Path | str | None = None,
    tokens_dir: Path = GMAIL_TOKENS_DIR,
    fetch_fn=fetch_emails,
    extract_fn=extract_signals,
    match_fn=match_expediente,
    llm_config=None,
    sudo_client=None,
) -> list[ReviewItem]:
    """Robot de ingesta (§3): trae de todos los buzones, combina y puebla la cola.

    Combina los correos de todas las cuentas en un único lote y llama a
    ``run_intake`` UNA vez, de modo que el dedup §4 colapsa el mismo Message-ID
    recibido en varios buzones. **Dry-run:** no toca el CRM.

    Devuelve los ``ReviewItem`` producidos por ``run_intake`` en esta ejecución.
    ``fetch_fn`` se inyecta en tests; en producción es ``fetch_emails`` (red).
    """
    todos: list[EmailMessage] = []
    for account in accounts:
        todos.extend(fetch_fn(account, query=query, tokens_dir=tokens_dir))
    return run_intake(
        todos,
        store_path=store_path,
        extract_fn=extract_fn,
        match_fn=match_fn,
        llm_config=llm_config,
        sudo_client=sudo_client,
    )
