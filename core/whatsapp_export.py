"""Parser puro de exports de WhatsApp («Exportar chat»).

Capa SIN red ni IO: convierte el texto de un ``_chat.txt`` en una lista de
``WhatsAppMessage``.  Núcleo reutilizable por la Fase A (subida UI) y la
futura Fase B (adaptador email).  Tolera los formatos iOS (corchetes) y
Android (guion), años de 2/4 cifras y horas 12/24h.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePath


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

# Cabecera iOS:  [d/m/yy[,] HH:MM[:SS][ am/pm]] resto  (puede ir precedida de U+200E)
_RE_IOS = re.compile(
    r"^‎?\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]\.?\s*m\.?)?)\]\s*(.*)$",
    re.IGNORECASE,
)


def _parse_header(line: str) -> tuple[str, str, str] | None:
    """Si la línea abre un mensaje, devuelve (fecha, hora, resto). Si no, None."""
    for rx in (_RE_IOS, _RE_ANDROID):
        m = rx.match(line)
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


# ---------------------------------------------------------------------------
# Detección de adjuntos
# ---------------------------------------------------------------------------

# El tag iOS puede ir precedido de un preámbulo (los DOCUMENTOS se exportan como
# `nombre.PDF • N páginas ‎<adjunto: ...>`), así que se busca sin anclar al inicio.
# Las fotos/vídeos empiezan por el tag; ambos casos quedan cubiertos.
_RE_ADJ_IOS = re.compile(r"<adjunto:\s*(.+?)>", re.IGNORECASE)
_RE_ADJ_ANDROID = re.compile(r"^(.+?)\s*\(archivo adjunto\)\s*$", re.IGNORECASE)
# iOS bare attachment marker (no filename): ‎<archivo adjunto>
_RE_ADJ_BARE = re.compile(r"^‎?<archivo adjunto>\s*$", re.IGNORECASE)
# Media omitted by WhatsApp: <Media omitted> / Multimedia omitido
_RE_MEDIA_OMITTED = re.compile(
    r"^‎?(?:<Media omitted>|Multimedia omitido)\s*$", re.IGNORECASE
)


# Marcas de dirección y de orden de bytes que el export pone delante (o detrás) del NOMBRE
# del adjunto, en iOS dentro del propio tag y en Android delante de `(archivo adjunto)`.
# `str.strip()` no las quita —no son espacio en blanco— y con ellas la referencia no casa
# nunca con el fichero en disco (MEJORAS #236: 0 de 39 en W-02V48N). Solo se quitan de los
# BORDES: por dentro, el nombre es el que es.
_MARCAS_INVISIBLES = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff"


def _limpiar_ref(nombre: str) -> str:
    """El nombre del adjunto sin espacios ni marcas invisibles en los bordes.

    Hasta punto fijo: con espacios y marcas alternados (marca, espacio y otra marca
    delante del nombre) una sola pasada de cada `strip` deja una marca dentro."""
    anterior = None
    while anterior != nombre:
        anterior = nombre
        nombre = nombre.strip().strip(_MARCAS_INVISIBLES)
    return nombre


def _adjunto_ref(texto_linea: str) -> str | None:
    """Extrae el nombre del adjunto referenciado en una línea, si lo hay."""
    m = _RE_ADJ_IOS.search(texto_linea)  # sin anclar: cubre documentos con preámbulo
    if m:
        return _limpiar_ref(m.group(1))
    m = _RE_ADJ_ANDROID.match(texto_linea)
    if m:
        return _limpiar_ref(m.group(1))
    if _RE_ADJ_BARE.match(texto_linea):
        return "<archivo adjunto>"
    if _RE_MEDIA_OMITTED.match(texto_linea):
        return "<Media omitted>"
    return None


# ---------------------------------------------------------------------------
# parse_chat
# ---------------------------------------------------------------------------


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
            adjunto_ref=_adjunto_ref(texto_msg),
            es_sistema=autor is None,
        )
        msgs.append(cur)
    return msgs


# ---------------------------------------------------------------------------
# Funciones públicas auxiliares
# ---------------------------------------------------------------------------


def referencias_adjuntos(msgs: list[WhatsAppMessage]) -> list[str]:
    """Nombres de fichero referenciados como adjunto, en orden de aparición."""
    return [m.adjunto_ref for m in msgs if m.adjunto_ref]


#: El nombre del chat en el export de iOS (y en los depósitos legacy).
CHAT_TXT = "_chat.txt"


def elegir_chat(textos: Mapping[str, str]) -> str | None:
    """El fichero de chat de un export, con UNA regla para todo el canal (MEJORAS #285).

    El intake aceptaba cualquier `.txt` y el atomizador solo `_chat.txt`, así que el chat
    de un export Android en español —`Chat de WhatsApp con <contacto>.txt`— se depositaba y
    se quedaba fuera de la atomización (W-0462E1: 173 mensajes). `textos` es
    `{nombre: texto}`; lo que no sea `.txt` se ignora. En este orden:

    1. `_chat.txt` si está, aunque el parser no lo entienda (como hasta ahora);
    2. si no, el primer `.txt` por orden alfabético que `parse_chat` interpreta: un `.txt`
       que se envió como ADJUNTO no le gana al chat por ir antes;
    3. si ninguno se interpreta, el primer `.txt`: custodia antes que parser — el intake
       no deja de depositar por no entender, y el atomizador lo verá como un chat con cero
       mensajes, que sale en su índice en vez de desaparecer;
    4. `None` si no hay ningún `.txt`.

    Los derivados nuestros (los que empiezan por `_`, salvo `_chat.txt`, como el
    `_chat_recortado.txt` del intake) nunca son candidatos.
    """
    if CHAT_TXT in textos:
        return CHAT_TXT
    txts = sorted(n for n in textos
                  if n.lower().endswith(".txt") and not PurePath(n).name.startswith("_"))
    for n in txts:
        if parse_chat(textos[n]):
            return n
    return txts[0] if txts else None


def filter_by_date_range(
    msgs: list[WhatsAppMessage],
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> list[WhatsAppMessage]:
    """Devuelve los mensajes con timestamp dentro de [desde, hasta] (inclusive).

    Los mensajes sin timestamp se descartan (no se puede ubicarlos en el rango).
    """
    out: list[WhatsAppMessage] = []
    for m in msgs:
        if m.timestamp is None:
            continue
        if desde is not None and m.timestamp < desde:
            continue
        if hasta is not None and m.timestamp > hasta:
            continue
        out.append(m)
    return out
