"""Layer B — reconstrucción de autoría enterrada en reenvíos/citas INLINE.

Diseño detallado y aprobado en ``docs/superpowers/specs/2026-06-25-email-atomize-layerb-design.md``.
Directriz primaria: **cero misatribución** — un remitente se afirma solo desde un bloque de
cabecera inline parseable; todo lo más débil va a la cola de revisión. Módulo puro (sin I/O).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parseaddr, parsedate_to_datetime
from zoneinfo import ZoneInfo

from core.email_export import _slug_descripcion

_TZ = ZoneInfo("Europe/Madrid")

# Identidades vigiladas (hook Fase 3; vacío en Fase 2 = no-op). Para identidades.yaml:
#   PersonaUno = {per01a@example.invalid, per01c@example.invalid}; per01b@example.invalid = CANDIDATO (tope media,
#   no se confirma aquí); ignacio@despacho-ab.example = parte relacionada, persona DISTINTA.
IDENTIDADES_VIGILADAS: set[str] = set()

_MIN_CUERPO = 24   # cuerpos normalizados < 24 chars nunca dirigen colapso/upgrade


@dataclass
class Anclaje:
    de: str = ""
    de_nombre: str = ""
    fecha_iso: str = "0000-00-00"
    fecha_dt: object | None = None
    asunto: str = ""


# ---------------------------------------------------------------------------
# Normalizador único + fingerprint (DD §5)
# ---------------------------------------------------------------------------

_RE_QUOTE_MARK = re.compile(r"(?m)^\s*>+\s?")
_RE_SIG = re.compile(
    r"(?im)^(?:--\s?$|enviado desde mi.*|sent from my.*|obtener outlook.*|get outlook.*)"
)
_RE_WS = re.compile(r"\s+")


def normaliza_cuerpo(texto: str) -> str:
    """El ÚNICO normalizador de cuerpo (lo usan fingerprint_a y fingerprint_b)."""
    t = _RE_QUOTE_MARK.sub("", texto or "")
    m = _RE_SIG.search(t)
    if m:
        t = t[: m.start()]
    t = _RE_WS.sub(" ", t)
    t = unicodedata.normalize("NFKC", t).casefold()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return t.strip()


def es_cuerpo_colapsable(cuerpo_norm: str) -> bool:
    """Solo cuerpos con sustancia (≥24 chars) pueden dirigir colapso/upgrade de fidelidad."""
    return len(cuerpo_norm) >= _MIN_CUERPO


def _material(remitente: str, fecha_iso: str, asunto: str, cuerpo_norm: str) -> str:
    fecha_dia = fecha_iso if fecha_iso and fecha_iso != "0000-00-00" else ""
    cuerpo_sha = hashlib.sha256(cuerpo_norm.encode("utf-8")).hexdigest()
    return "\x1f".join([(remitente or "").strip().lower(), fecha_dia,
                        _slug_descripcion(asunto or ""), cuerpo_sha])


def fingerprint_b(anc: Anclaje | None, cuerpo_norm: str) -> str:
    """Identidad de contenido de un segmento citado. Día-granular (absorbe jitter tz)."""
    remitente = anc.de if anc else ""
    fecha = anc.fecha_iso if anc else "0000-00-00"
    asunto = anc.asunto if anc else ""
    material = _material(remitente, fecha, asunto, cuerpo_norm)
    return "fp:" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def fingerprint_a(m) -> str:
    """Mismo algoritmo sobre un mensaje de Capa A (para el puente del upgrade)."""
    material = _material(m.de, m.fecha_iso, m.asunto, normaliza_cuerpo(m.cuerpo))
    return "fp:" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def cuerpo_sha_de(cuerpo_norm: str) -> str:
    return hashlib.sha256(cuerpo_norm.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Parseo de anclaje: sender/date/subject desde el bloque de cabecera (DD §3)
# ---------------------------------------------------------------------------

# Meses ES+CA (claves ascii-folded, minúscula): full + abreviaturas.
_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
    "gener": 1, "febrer": 2, "marc": 3, "maig": 5, "juny": 6, "juliol": 7, "agost": 8,
    "setembre": 9, "novembre": 11, "desembre": 12,
    "gen": 1, "mai": 5, "set": 9, "des": 12,
}
_RE_FECHA_DE = re.compile(r"(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})")
_RE_FECHA = re.compile(r"(\d{1,2})\s+([a-z]+)\.?\s+(\d{4})")
_RE_FECHA_NUM = re.compile(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})")
_RE_LABEL = re.compile(
    r"(?im)^\s*(de|from|enviado|sent|fecha|date|para|to|asunto|subject|cc|cco|bcc)\s*:\s*(.*)$"
)
_RE_ADDR = re.compile(r"<\s*([^<>\s]+@[^<>\s]+)\s*>")
_RE_APPLE = re.compile(r"(?i)^\s*(?:el|on)\s+(.+?)(?:,|\s+a\s+las\s+|\s+a\s+les\s+|\s+at\s+)")


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii").lower()


def _parse_fecha(s: str) -> tuple[str, object | None]:
    """``(fecha_iso, datetime|None)`` desde texto libre ES/CA/numérico/RFC. Día-preciso."""
    f = _fold(s)
    for rx in (_RE_FECHA_DE, _RE_FECHA):
        m = rx.search(f)
        if m:
            mon = _MESES.get(m.group(2))
            if mon:
                day, year = int(m.group(1)), int(m.group(3))
                try:
                    dt = datetime(year, mon, day, tzinfo=_TZ)
                    return f"{year:04d}-{mon:02d}-{day:02d}", dt
                except ValueError:
                    pass
    m = _RE_FECHA_NUM.search(f)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            dt = datetime(y, mo, d, tzinfo=_TZ)
            return f"{y:04d}-{mo:02d}-{d:02d}", dt
        except ValueError:
            pass
    try:
        dt = parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        dt = None
    if dt is not None:
        local = dt.astimezone(_TZ) if dt.tzinfo else dt.replace(tzinfo=_TZ)
        return local.strftime("%Y-%m-%d"), local
    return "0000-00-00", None


def _addr_o_nombre(raw: str) -> tuple[str, str]:
    """``(de, de_nombre)`` desde un valor De:/From:. Nunca inventa una dirección."""
    nombre, addr = parseaddr(raw or "")
    if "@" in addr:
        return addr.lower(), (nombre or "").strip()
    # sin dirección real: conservar el display, dirección vacía
    return "", (nombre or addr or raw or "").strip()


def _parse_label(texto: str) -> "Anclaje | None":
    labels: dict[str, str] = {}
    for k, v in _RE_LABEL.findall(texto):
        labels.setdefault(k.lower(), v.strip())
    de_raw = labels.get("de") or labels.get("from") or ""
    fecha_raw = (labels.get("enviado") or labels.get("sent") or labels.get("fecha")
                 or labels.get("date") or "")
    asunto = labels.get("asunto") or labels.get("subject") or ""
    if not (de_raw or fecha_raw or asunto):
        return None
    de, de_nombre = _addr_o_nombre(de_raw)
    fecha_iso, fecha_dt = _parse_fecha(fecha_raw) if fecha_raw else ("0000-00-00", None)
    return Anclaje(de=de, de_nombre=de_nombre, fecha_iso=fecha_iso, fecha_dt=fecha_dt, asunto=asunto)


def _parse_apple(texto: str) -> "Anclaje | None":
    m_addr = _RE_ADDR.search(texto)
    de = m_addr.group(1).lower() if m_addr else ""
    de_nombre = ""
    if m_addr:
        # nombre = texto antes de <addr>, tras la última coma
        prev = texto[: m_addr.start()].rstrip()
        de_nombre = prev.split(",")[-1].strip()
    m_date = _RE_APPLE.search(texto)
    fecha_iso, fecha_dt = _parse_fecha(m_date.group(1)) if m_date else ("0000-00-00", None)
    if not de and fecha_iso == "0000-00-00":
        return None
    return Anclaje(de=de, de_nombre=de_nombre, fecha_iso=fecha_iso, fecha_dt=fecha_dt, asunto="")


def parsear_anclaje(texto: str, estilo: str) -> "Anclaje | None":
    """Sender/date/subject SOLO desde el bloque de cabecera del segmento (nunca de prosa)."""
    if estilo in ("apple_es", "apple_en", "gmail_attr"):
        return _parse_apple(texto)
    return _parse_label(texto)
