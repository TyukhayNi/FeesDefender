#!/usr/bin/env python3
"""Servidor MCP `gmail-multiaccount` — LECTURA + ETIQUETADO de Gmail multicuenta.

Antes solo lectura (scope gmail.readonly). Ahora añade ETIQUETADO: crear una
etiqueta de usuario, y aplicar/quitar una etiqueta a un mensaje o hilo. El scope
OAuth es `gmail.modify` (subsume readonly; NO permite borrado permanente).

Guardarraíles (fail-closed): solo etiquetas de USUARIO (rechaza etiquetas de
sistema: INBOX/SENT/DRAFT/TRASH/SPAM/IMPORTANT/STARRED/UNREAD/CHAT y CATEGORY_*);
`account` obligatorio en toda escritura (sin fan-out); sin borrado (de mensajes o
etiquetas), sin envío/borradores, sin archivar, sin marcar leído/no leído.

Selección de cuenta: las tools de LECTURA aceptan `account` (email) y pueden
omitirlo para consultar TODAS las cuentas (cada resultado se etiqueta con su
cuenta). Las tools de ESCRITURA exigen `account` explícito.

get_attachment escribe a disco (confinable con GMAIL_DL_ROOT): es una lectura en
Gmail cubierta por el scope; el destino puede acotarse a una raíz.
"""
from __future__ import annotations

import base64
import os
import sys
from email.utils import parsedate_to_datetime
from typing import Callable, Optional

from mcp.server.fastmcp import FastMCP

# Import dual-modo: como paquete (tests) o standalone (Claude Desktop).
try:
    from . import gmail_auth
except ImportError:  # ejecución directa: python server.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gmail_auth  # type: ignore  # noqa: E402


# ----------------------------- utilidades internas -----------------------------

_HEADERS_OF_INTEREST = ("From", "To", "Cc", "Subject", "Date")


def _decode_b64url(data: str) -> str:
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", "replace")
    except Exception:
        return ""


def _extract_body(payload: dict) -> str:
    """Extrae el cuerpo en texto, recorriendo las partes y priorizando text/plain."""
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})

    if mime == "text/plain" and body.get("data"):
        return _decode_b64url(body["data"])

    parts = payload.get("parts", [])
    if parts:
        for part in parts:
            text = _extract_body(part)
            if text and part.get("mimeType", "").startswith("text/plain"):
                return text
        for part in parts:
            if part.get("mimeType", "").startswith("text/"):
                text = _extract_body(part)
                if text:
                    return text
        for part in parts:
            text = _extract_body(part)
            if text:
                return text

    if mime.startswith("text/") and body.get("data"):
        return _decode_b64url(body["data"])
    return ""


def _headers_dict(payload: dict) -> dict:
    out = {}
    for h in payload.get("headers", []):
        name = h.get("name", "")
        if name in _HEADERS_OF_INTEREST:
            out[name] = h.get("value", "")
    return out


def _format_message(msg: dict, include_body: bool = True) -> dict:
    payload = msg.get("payload", {})
    headers = _headers_dict(payload)
    result = {
        "id": msg.get("id"),
        "thread_id": msg.get("threadId"),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "cc": headers.get("Cc", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "snippet": msg.get("snippet", ""),
        "labels": msg.get("labelIds", []),
    }
    if include_body:
        result["body"] = _extract_body(payload)
    return result


def _resolve_accounts(account: Optional[str], lister: Callable[[], list[str]]) -> list[str]:
    if account:
        return [account]
    accounts = lister()
    if not accounts:
        raise RuntimeError(
            "No hay cuentas conectadas. Añade alguna con: "
            "python -m plugins.gmail_mcp.gmail_cli add"
        )
    return accounts


def _iter_attachment_parts(payload: dict):
    """Recorre el árbol MIME y produce cada 'part' que sea un adjunto real."""
    stack = [payload]
    while stack:
        part = stack.pop()
        for child in part.get("parts", []) or []:
            stack.append(child)
        body = part.get("body", {}) or {}
        if (part.get("filename") or body.get("attachmentId")) and (
            body.get("attachmentId") or body.get("data")
        ):
            yield part


def _resolve_dest(dest_path: str) -> str:
    """Resuelve y valida la ruta de destino de descarga. Si GMAIL_DL_ROOT está
    definida, el destino debe quedar dentro de esa raíz (realpath contra
    symlink-escape)."""
    dest = os.path.realpath(os.path.expanduser(dest_path))
    root = os.environ.get("GMAIL_DL_ROOT")
    if root:
        root_abs = os.path.realpath(os.path.expanduser(root))
        try:
            inside = os.path.commonpath([root_abs, dest]) == root_abs
        except ValueError:
            inside = False  # unidades distintas en Windows
        if not inside:
            raise ValueError(f"Destino fuera de GMAIL_DL_ROOT ({root_abs}): {dest}")
    return dest


def build_server(
    *,
    service_factory: Callable[[str], object] | None = None,
    account_lister: Callable[[], list[str]] | None = None,
) -> FastMCP:
    """Construye el servidor. `service_factory`/`account_lister` son puntos de
    inyección para tests; en producción se toman de gmail_auth."""
    if service_factory is None:
        service_factory = gmail_auth.build_service
    if account_lister is None:
        account_lister = gmail_auth.list_account_emails

    mcp = FastMCP("gmail-multiaccount")

    # ------------------------------- lectura -------------------------------

    @mcp.tool()
    def list_accounts() -> list[str]:
        """Lista las direcciones de Gmail conectadas a este servidor."""
        return account_lister()

    @mcp.tool()
    def search_messages(query: str, account: Optional[str] = None,
                        max_results: int = 20) -> list[dict]:
        """Busca mensajes con la sintaxis de búsqueda de Gmail. Omite `account`
        para buscar en TODAS las cuentas (cada resultado se etiqueta con la suya).
        Devuelve metadatos y snippet (sin cuerpo); usa read_message para el íntegro."""
        results: list[dict] = []
        for acc in _resolve_accounts(account, account_lister):
            service = service_factory(acc)
            resp = (service.users().messages()
                    .list(userId="me", q=query, maxResults=max_results).execute())
            for ref in resp.get("messages", []):
                full = (service.users().messages()
                        .get(userId="me", id=ref["id"], format="metadata",
                             metadataHeaders=list(_HEADERS_OF_INTEREST)).execute())
                item = _format_message(full, include_body=False)
                item["account"] = acc
                results.append(item)
        return results

    @mcp.tool()
    def read_message(message_id: str, account: str) -> dict:
        """Lee un mensaje completo, incluido el cuerpo en texto."""
        service = service_factory(account)
        full = (service.users().messages()
                .get(userId="me", id=message_id, format="full").execute())
        item = _format_message(full, include_body=True)
        item["account"] = account
        return item

    @mcp.tool()
    def read_thread(thread_id: str, account: str) -> dict:
        """Lee un hilo completo con todos sus mensajes ordenados por fecha."""
        service = service_factory(account)
        thread = (service.users().threads()
                  .get(userId="me", id=thread_id, format="full").execute())
        messages = [_format_message(m, include_body=True)
                    for m in thread.get("messages", [])]

        def _sort_key(m: dict):
            try:
                return parsedate_to_datetime(m["date"])
            except Exception:
                return None

        messages.sort(key=lambda m: (_sort_key(m) is None, _sort_key(m)))
        return {"thread_id": thread_id, "account": account, "messages": messages}

    @mcp.tool()
    def list_labels(account: Optional[str] = None) -> dict:
        """Lista las etiquetas de una cuenta (o de todas si se omite `account`).
        Devuelve, por cuenta, una lista de {id, name} ordenada por nombre. El id es
        necesario para apply_label/remove_label."""
        out: dict[str, list[dict]] = {}
        for acc in _resolve_accounts(account, account_lister):
            service = service_factory(acc)
            resp = service.users().labels().list(userId="me").execute()
            out[acc] = sorted(
                ({"id": l.get("id"), "name": l.get("name", "")}
                 for l in resp.get("labels", [])),
                key=lambda d: d["name"],
            )
        return out

    @mcp.tool()
    def list_attachments(message_id: str, account: str) -> list[dict]:
        """Lista los adjuntos de un mensaje (sin descargarlos). Por adjunto:
        filename, mime_type, size (bytes) y attachment_id."""
        service = service_factory(account)
        full = (service.users().messages()
                .get(userId="me", id=message_id, format="full").execute())
        out: list[dict] = []
        for part in _iter_attachment_parts(full.get("payload", {})):
            body = part.get("body", {}) or {}
            out.append({
                "filename": part.get("filename", ""),
                "mime_type": part.get("mimeType", ""),
                "size": body.get("size", 0),
                "attachment_id": body.get("attachmentId", ""),
            })
        return out

    @mcp.tool()
    def get_attachment(message_id: str, attachment_id: str, account: str,
                       dest_path: str, max_bytes: int = 50_000_000) -> dict:
        """Descarga un adjunto a disco (base64url -> fichero). dest_path confinable
        con GMAIL_DL_ROOT. Devuelve ruta absoluta y tamaño en bytes."""
        dest = _resolve_dest(dest_path)
        service = service_factory(account)
        att = (service.users().messages().attachments()
               .get(userId="me", messageId=message_id, id=attachment_id).execute())
        size = att.get("size", 0)
        if max_bytes and size and size > max_bytes:
            raise ValueError(
                f"Adjunto de {size} bytes supera max_bytes ({max_bytes}). "
                f"Sube el límite explícitamente si de verdad lo quieres.")
        raw = base64.urlsafe_b64decode(att.get("data", "").encode("utf-8"))
        if max_bytes and len(raw) > max_bytes:
            raise ValueError(f"Adjunto de {len(raw)} bytes supera max_bytes ({max_bytes}).")
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(raw)
        return {"path": dest, "bytes": len(raw), "account": account}

    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
