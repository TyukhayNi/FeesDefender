"""Parsing rico de cabeceras RFC822 para la atomización.

Extiende lo que ofrece ``email_export.parse_headers`` (date/subject/from/to/message-id):
direcciones con nombre, listas (to/cc), enhebrado (in-reply-to/references→hilo), resultados
de autenticación (dkim/spf/dmarc) y dispositivo emisor (X-Mailer/User-Agent).
"""
from __future__ import annotations

import email
import re
from dataclasses import dataclass, field
from email import policy
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from zoneinfo import ZoneInfo

_TZ = ZoneInfo("Europe/Madrid")
_SIN_FECHA = "0000-00-00"


def _norm_mid(v: str) -> str:
    return (v or "").strip().strip("<>").strip()


@dataclass
class Cabeceras:
    rfc_message_id: str = ""
    in_reply_to: str = ""
    hilo: str = ""
    asunto: str = ""
    de: str = ""
    de_nombre: str = ""
    para: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    fecha_iso: str = _SIN_FECHA
    hora: str = ""
    fecha_tz: str = ""
    auth: dict = field(default_factory=dict)
    emisor_dispositivo: str = ""


def _addrs(msg, campo: str) -> list[str]:
    vals = msg.get_all(campo, [])
    return [a.lower() for _n, a in getaddresses(vals) if a]


def _fecha(msg) -> tuple[str, str, str]:
    raw = msg.get("date")
    if not raw:
        return _SIN_FECHA, "", ""
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return _SIN_FECHA, "", ""
    if dt is None:
        return _SIN_FECHA, "", ""
    if dt.tzinfo is not None:
        local = dt.astimezone(_TZ)
    else:
        local = dt
    return local.strftime("%Y-%m-%d"), local.strftime("%H%M"), local.isoformat()


def _refs_root(msg) -> str:
    refs = msg.get("references")
    if refs:
        ids = re.findall(r"<([^>]+)>", refs)
        if ids:
            return ids[0].strip()
    irt = _norm_mid(msg.get("in-reply-to") or "")
    if irt:
        return irt
    return _norm_mid(msg.get("message-id") or "")


def _auth(msg) -> dict:
    out: dict[str, str] = {}
    val = " ".join(msg.get_all("authentication-results", []))
    for k in ("dkim", "spf", "dmarc"):
        m = re.search(rf"\b{k}\s*=\s*([a-zA-Z]+)", val)
        if m:
            out[k] = m.group(1).lower()
    return out


def _dispositivo(msg) -> str:
    for h in ("x-mailer", "user-agent"):
        v = msg.get(h)
        if v:
            return str(v).strip()
    return ""


def parse_cabeceras(raw: bytes) -> Cabeceras:
    msg = email.message_from_bytes(raw, policy=policy.default)
    de_nombre, de = parseaddr(msg.get("from") or "")
    fecha_iso, hora, fecha_tz = _fecha(msg)
    return Cabeceras(
        rfc_message_id=_norm_mid(msg.get("message-id") or ""),
        in_reply_to=_norm_mid(msg.get("in-reply-to") or ""),
        hilo=_refs_root(msg),
        asunto=str(msg.get("subject") or "").strip(),
        de=(de or "").lower(),
        de_nombre=(de_nombre or "").strip(),
        para=_addrs(msg, "to"),
        cc=_addrs(msg, "cc"),
        fecha_iso=fecha_iso,
        hora=hora,
        fecha_tz=fecha_tz,
        auth=_auth(msg),
        emisor_dispositivo=_dispositivo(msg),
    )
