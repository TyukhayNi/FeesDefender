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


# --------------------------- guardarraíles de etiqueta ---------------------------

# Etiquetas de sistema: nunca se crean/aplican/quitan. La fuente de verdad es el
# campo `type == "system"` de la API; esta blocklist es una red defensiva por si
# una etiqueta no aparece en el listado.
SYSTEM_LABELS = frozenset({
    "INBOX", "SENT", "DRAFT", "TRASH", "SPAM",
    "IMPORTANT", "STARRED", "UNREAD", "CHAT",
})


def _is_system_label_ref(ref: str) -> bool:
    """True si `ref` (id o nombre) es una etiqueta de sistema por convención."""
    r = (ref or "").strip().upper()
    return r in SYSTEM_LABELS or r.startswith("CATEGORY_")


def _list_labels_raw(service) -> list[dict]:
    resp = service.users().labels().list(userId="me").execute()
    return resp.get("labels", [])


def _resolve_user_label(service, label: str) -> dict:
    """Resuelve `label` (id o nombre) a un dict de etiqueta de USUARIO. Fail-closed:
    ValueError si está vacío, si no existe, o si es de sistema (por type o por
    convención de id/nombre)."""
    target = (label or "").strip()
    if not target:
        raise ValueError("label vacío.")
    labels = _list_labels_raw(service)
    by_id = [l for l in labels if l.get("id") == target]
    by_name = [l for l in labels if l.get("name") == target]
    match = by_id[0] if by_id else (by_name[0] if by_name else None)
    if match is None:
        raise ValueError(
            f"Etiqueta no encontrada: {label!r}. Las etiquetas de usuario se crean "
            f"explícitamente con create_label; no se crean al aplicar.")
    if (match.get("type") or "").strip().lower() == "system" \
            or _is_system_label_ref(match.get("id", "")) \
            or _is_system_label_ref(match.get("name", "")):
        raise ValueError(
            f"Etiqueta de sistema no permitida: {match.get('id')} "
            f"({match.get('name')}). Solo etiquetas de usuario.")
    return match


def _guard_create_name(name: str) -> str:
    n = (name or "").strip()
    if not n:
        raise ValueError("name vacío.")
    if _is_system_label_ref(n):
        raise ValueError(f"Nombre reservado de etiqueta de sistema: {name!r}.")
    return n


def _modify_target(service, *, target_id: str, target_type: str,
                   add: Optional[list[str]] = None,
                   remove: Optional[list[str]] = None) -> dict:
    """Aplica addLabelIds/removeLabelIds a un mensaje o hilo. target_type inválido
    → ValueError (fail-closed)."""
    body: dict = {}
    if add:
        body["addLabelIds"] = add
    if remove:
        body["removeLabelIds"] = remove
    tt = (target_type or "").strip().lower()
    if tt == "message":
        return (service.users().messages()
                .modify(userId="me", id=target_id, body=body).execute())
    if tt == "thread":
        return (service.users().threads()
                .modify(userId="me", id=target_id, body=body).execute())
    raise ValueError(f"target_type debe ser 'message' o 'thread', no {target_type!r}.")


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

    # ------------------------------- etiquetado -------------------------------

    @mcp.tool()
    def create_label(account: str, name: str) -> dict:
        """Crea la etiqueta de USUARIO `name` en `account`. IDEMPOTENTE: si ya
        existe, devuelve su id sin recrearla. Rechaza nombres de etiqueta de
        sistema. Devuelve {account, id, name, created}."""
        clean = _guard_create_name(name)
        service = service_factory(account)
        for l in _list_labels_raw(service):
            if l.get("name") == clean:
                return {"account": account, "id": l.get("id"),
                        "name": l.get("name"), "created": False}
        created = service.users().labels().create(
            userId="me", body={"name": clean}).execute()
        return {"account": account, "id": created.get("id"),
                "name": created.get("name", clean), "created": True}

    @mcp.tool()
    def apply_label(account: str, label: str, target_id: str,
                    target_type: str = "message") -> dict:
        """Aplica la etiqueta de USUARIO `label` (id o nombre EXISTENTE) al mensaje
        o hilo `target_id`. `target_type`: 'message' | 'thread'. El correo permanece
        en Inbox (no se archiva). `label` inexistente → error (crear es explícito con
        create_label). Devuelve {account, label_id, label_name, target_id,
        target_type, action, label_ids}."""
        service = service_factory(account)
        match = _resolve_user_label(service, label)
        resp = _modify_target(service, target_id=target_id, target_type=target_type,
                              add=[match["id"]])
        return {"account": account, "label_id": match["id"],
                "label_name": match.get("name"), "target_id": target_id,
                "target_type": target_type.strip().lower(), "action": "apply",
                "label_ids": resp.get("labelIds", [])}

    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
