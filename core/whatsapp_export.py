"""Parser puro de exports de WhatsApp («Exportar chat»).

Capa SIN red ni IO: convierte el texto de un ``_chat.txt`` en una lista de
``WhatsAppMessage``.  Núcleo reutilizable por la Fase A (subida UI) y la
futura Fase B (adaptador email).  Tolera los formatos iOS (corchetes) y
Android (guion), años de 2/4 cifras y horas 12/24h.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
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
    #: La referencia TAL COMO la escribe el export, con sus marcas invisibles; `adjunto_ref`
    #: es la limpia. El nombre en disco se resuelve con las dos (`resolver_adjunto`, R1/H-04).
    adjunto_ref_crudo: str | None = None


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


def _adjunto(texto_linea: str) -> tuple[str, str] | None:
    """`(limpia, cruda)` del adjunto referenciado en una línea, si lo hay."""
    m = _RE_ADJ_IOS.search(texto_linea)  # sin anclar: cubre documentos con preámbulo
    if not m:
        m = _RE_ADJ_ANDROID.match(texto_linea)
    if m:
        crudo = m.group(1).strip()
        return _limpiar_ref(crudo), crudo
    if _RE_ADJ_BARE.match(texto_linea):
        return "<archivo adjunto>", "<archivo adjunto>"
    if _RE_MEDIA_OMITTED.match(texto_linea):
        return "<Media omitted>", "<Media omitted>"
    return None


def _adjunto_ref(texto_linea: str) -> str | None:
    """Extrae el nombre (limpio) del adjunto referenciado en una línea, si lo hay."""
    par = _adjunto(texto_linea)
    return par[0] if par else None


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
        adj = _adjunto(texto_msg)
        cur = WhatsAppMessage(
            timestamp=_parse_dt(date_str, time_str),
            autor=autor,
            texto=texto_msg,
            adjunto_ref=adj[0] if adj else None,
            es_sistema=autor is None,
            adjunto_ref_crudo=adj[1] if adj else None,
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

#: Lo que el propio canal escribe JUNTO al chat (`whatsapp_intake.deposit_export`). Solo
#: eso es un derivado nuestro: un nombre que empiece por `_` puede venir en el export
#: (R1/H-01: excluirlos todos rechazaba el export entero, zip original incluido).
DERIVADOS = frozenset({"_chat_recortado.txt"})


def elegir_chat(textos: Mapping[str, str], presentes: Iterable[str] = (), *,
                custodia: bool = True) -> str | None:
    """El fichero de chat de un export, con UNA regla para todo el canal (MEJORAS #285).

    El intake aceptaba cualquier `.txt` y el atomizador solo `_chat.txt`, así que el chat
    de un export Android en español —`Chat de WhatsApp con <contacto>.txt`— se depositaba y
    se quedaba fuera de la atomización (W-0462E1: 173 mensajes). `textos` es
    `{nombre: texto}` —lo que no sea `.txt` se ignora— y `presentes`, los nombres de todos
    los ficheros del export. En este orden:

    1. `_chat.txt` si está, aunque el parser no lo entienda (como hasta ahora);
    2. si no, entre los `.txt` que `parse_chat` interpreta, **el chat es el que tiene
       pruebas de serlo** (R1/H-02: «el primero que se interprete» dejaba ganar a un
       `.txt` adjunto con una sola línea con forma de mensaje). Se descartan los que otra
       conversación del export cita como adjunto —un export reenviado, un acta— y, de los
       que quedan, gana el que cita más ficheros que vienen en el export; a igualdad, el
       de más mensajes; a igualdad, el primero por orden alfabético;
    3. si ninguno se interpreta y `custodia` es cierto, el primer `.txt`: el intake no deja
       de depositar por no entender. El atomizador llama con `custodia=False` (R1/H-03):
       para él, un `.txt` que no es una conversación no es un chat;
    4. `None` si no hay candidato.

    Queda un caso que la regla no puede decidir, y se dice: un export SIN ficheros en el
    que un `.txt` adjunto no citado tenga más mensajes que el propio chat. El depósito
    conserva igual todos los bytes; lo que se equivocaría es la etiqueta.
    """
    if CHAT_TXT in textos:
        return CHAT_TXT
    txts = sorted(n for n in textos
                  if n.lower().endswith(".txt") and PurePath(n).name not in DERIVADOS)
    conversaciones = {n: msgs for n in txts if (msgs := parse_chat(textos[n]))}
    if conversaciones:
        citados = {_limpiar_ref(r) for msgs in conversaciones.values()
                   for r in referencias_adjuntos(msgs)}
        no_citadas = [n for n in conversaciones
                      if _limpiar_ref(PurePath(n).name) not in citados]
        en_export = {_limpiar_ref(PurePath(p).name) for p in presentes}

        def _pruebas(n: str) -> tuple[int, int]:
            refs = {_limpiar_ref(r) for r in referencias_adjuntos(conversaciones[n])}
            return len(refs & en_export), len(conversaciones[n])

        # `max` devuelve el PRIMER máximo en orden de iteración, y `txts` va ordenado:
        # a igualdad de pruebas gana el primero por orden alfabético.
        return max(no_citadas or list(conversaciones), key=_pruebas)
    if custodia and txts:
        return txts[0]
    return None


def resolver_adjunto(ref: str, nombres: Iterable[str], crudo: str | None = None) -> str | None:
    """El nombre EN DISCO del adjunto que un mensaje cita, o `None` si no se puede decir.

    R1/H-04: limpiar la referencia (`MEJORAS #236`) no puede ligarla a otros bytes. Se busca
    primero el nombre tal como lo citó el chat —con sus marcas—, después el limpio, y solo
    entonces por nombre limpio a ambos lados, y únicamente si identifica UN fichero: con
    dos candidatos, el adjunto queda sin resolver en vez de ligarse a uno de ellos.
    """
    nombres = list(nombres)
    exactos = set(nombres)
    for n in (crudo, ref):
        if n and n in exactos:
            return n
    limpio = _limpiar_ref(ref)
    candidatos = [n for n in nombres if _limpiar_ref(n) == limpio]
    return candidatos[0] if len(candidatos) == 1 else None


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
