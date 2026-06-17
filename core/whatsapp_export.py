"""Parser puro de exports de WhatsApp («Exportar chat»).

Capa SIN red ni IO: convierte el texto de un ``_chat.txt`` en una lista de
``WhatsAppMessage``.  Núcleo reutilizable por la Fase A (subida UI) y la
futura Fase B (adaptador email).  Tolera los formatos iOS (corchetes) y
Android (guion), años de 2/4 cifras y horas 12/24h.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class WhatsAppMessage:
    """Un mensaje del chat ya parseado."""

    timestamp: datetime | None
    autor: str | None
    texto: str
    adjunto_ref: str | None
    es_sistema: bool


# Cabecera Android:  d/m/yy, HH:MM[ :SS][ am/pm] - resto
_RE_ANDROID = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s+"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]\.?\s*m\.?)?)\s+-\s+(.*)$",
    re.IGNORECASE,
)


def _parse_header(line: str) -> tuple[str, str, str] | None:
    """Si la línea abre un mensaje, devuelve (fecha, hora, resto). Si no, None."""
    m = _RE_ANDROID.match(line)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return None


def _parse_dt(date_str: str, time_str: str) -> datetime | None:
    """Combina fecha (día primero) + hora en un datetime.  None si no parsea."""
    fecha = None
    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            fecha = datetime.strptime(date_str, fmt).date()
            break
        except ValueError:
            continue
    if fecha is None:
        return None
    t = re.sub(r"\s+", "", time_str.strip().lower().replace(".", ""))
    hora = None
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M:%S%p", "%I:%M%p"):
        try:
            hora = datetime.strptime(t, fmt).time()
            break
        except ValueError:
            continue
    if hora is None:
        return None
    return datetime.combine(fecha, hora)


def _split_author(rest: str) -> tuple[str | None, str]:
    """Separa 'Nombre: texto' por el primer ': '.  Sin ': ' → mensaje de sistema."""
    idx = rest.find(": ")
    if idx == -1:
        return None, rest
    return rest[:idx], rest[idx + 2 :]


def parse_chat(texto: str) -> list[WhatsAppMessage]:
    """Parsea el contenido de un ``_chat.txt`` → lista de mensajes."""
    msgs: list[WhatsAppMessage] = []
    cur: WhatsAppMessage | None = None
    for line in texto.splitlines():
        header = _parse_header(line)
        if header is None:
            if cur is not None:
                cur.texto = cur.texto + "\n" + line
            continue
        date_str, time_str, rest = header
        autor, texto_msg = _split_author(rest)
        cur = WhatsAppMessage(
            timestamp=_parse_dt(date_str, time_str),
            autor=autor,
            texto=texto_msg,
            adjunto_ref=None,
            es_sistema=autor is None,
        )
        msgs.append(cur)
    return msgs
