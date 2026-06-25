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
from .identidades import Identidades
from .model import RegistroMensaje, SegmentoEnterrado

_TZ = ZoneInfo("Europe/Madrid")

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
    # ES (full + abreviaturas)
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
    # CA (full + abreviaturas)
    "gener": 1, "febrer": 2, "marc": 3, "maig": 5, "juny": 6, "juliol": 7, "agost": 8,
    "setembre": 9, "novembre": 11, "desembre": 12,
    "gen": 1, "mai": 5, "set": 9, "des": 12,
    # EN (full + abreviaturas) — gmail/Outlook en inglés
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "apr": 4, "aug": 8, "dec": 12,
}
_RE_FECHA_DE = re.compile(r"(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})")
_RE_FECHA = re.compile(r"(\d{1,2})\s+([a-z]+)\.?\s+(\d{4})")           # DMY: 14 may 2024
_RE_FECHA_MDY = re.compile(r"([a-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})")     # MDY: May 10, 2024
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
    m = _RE_FECHA_MDY.search(f)   # inglés "May 10, 2024"
    if m:
        mon = _MESES.get(m.group(1))
        if mon:
            day, year = int(m.group(2)), int(m.group(3))
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
        # Solo aceptar numérico cuando el ORDEN día/mes es inequívoco (día>12 = dd/mm europeo).
        # Si ambos ≤12 es ambiguo → NO se trata como fecha verificada (no debe dirigir alta).
        if d > 12 and mo <= 12:
            try:
                dt = datetime(y, mo, d, tzinfo=_TZ)
                return f"{y:04d}-{mo:02d}-{d:02d}", dt
            except ValueError:
                pass
        else:
            return "0000-00-00", None  # fecha numérica ambigua → sin verificar
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


_RE_ATTR_FIN = re.compile(r"(?i)(escrib(?:i[oó])|wrote|va\s+escriure)\s*:\s*$")


def _parse_apple(texto: str) -> "Anclaje | None":
    # Exigir ESTRUCTURA de atribución ("El/On …" o línea que acaba en "escribió:/wrote:")
    # antes de fiarse de un <addr>: un email suelto en una cita NO es una atribución.
    m_date = _RE_APPLE.search(texto)
    if m_date is None and not _RE_ATTR_FIN.search((texto or "").strip()):
        return None
    m_addr = _RE_ADDR.search(texto)
    de = m_addr.group(1).lower() if m_addr else ""
    de_nombre = ""
    if m_addr:
        prev = texto[: m_addr.start()].rstrip()
        de_nombre = prev.split(",")[-1].strip()
    # Buscar la fecha en TODA la atribución (salta el día de la semana: "El mar, 14 may 2024…",
    # "On Fri, May 10, 2024…") en vez de quedarse con el primer fragmento antes de la coma.
    fecha_iso, fecha_dt = _parse_fecha(texto)
    if not de and fecha_iso == "0000-00-00":
        return None
    return Anclaje(de=de, de_nombre=de_nombre, fecha_iso=fecha_iso, fecha_dt=fecha_dt, asunto="")


def parsear_anclaje(texto: str, estilo: str) -> "Anclaje | None":
    """Sender/date/subject SOLO desde el bloque de cabecera del segmento (nunca de prosa)."""
    if not texto:
        return None
    if estilo in ("apple_es", "apple_en", "gmail_attr", "html_quote"):
        return _parse_apple(texto) or _parse_label(texto)
    return _parse_label(texto)


# ---------------------------------------------------------------------------
# Segmentación de texto plano (DD §2.0, §2.2)
# ---------------------------------------------------------------------------

@dataclass
class Segmento:
    texto: str = ""
    anclaje_texto: str | None = None
    profundidad: int = 0
    estilo: str = ""
    estructural: bool = False
    # rellenados por reconstruir(): confianza/motivo/de/fecha/fingerprint/cuerpo_sha/en_revision
    confianza: str = ""
    motivo: str = ""
    de: str = ""
    de_nombre: str = ""
    fecha_iso: str = "0000-00-00"
    asunto: str = ""
    fingerprint: str = ""
    cuerpo_sha: str = ""
    en_revision: bool = False
    portador_msg_id: str = ""
    rfc_message_id: str = ""


@dataclass
class Segmentacion:
    autor: str = ""
    ancestros: list = field(default_factory=list)
    respuesta_intercalada: bool = False
    motivo: str = ""

_RE_FWD_LINE = re.compile(
    r"(?i)^\s*-{2,}\s*(forwarded message|mensaje reenviado|reenviado|begin forwarded message"
    r"|original message|mensaje original)")
_RE_APPLE_ES_LINE = re.compile(r"(?i)^\s*el\s+.+?\s+(?:escribi[oó]|va\s+escriure)\s*:\s*$")
_RE_APPLE_EN_LINE = re.compile(r"(?i)^\s*on\s+.+?\s+wrote\s*:\s*$")
_RE_DEFROM_LINE = re.compile(r"(?i)^\s*(?:de|from)\s*:\s*\S")
_RE_2ND_LABEL = re.compile(
    r"(?i)^\s*(enviado|sent|fecha|date|para|to|asunto|subject|cc|cco|bcc)\s*:")
_RE_ANYLABEL = re.compile(
    r"(?i)^\s*(de|from|enviado|sent|fecha|date|para|to|asunto|subject|cc|cco|bcc)\s*:")


def _es_quote(l: str) -> bool:
    return l.lstrip().startswith(">")


def _quote_depth(l: str) -> int:
    pref = re.match(r"^[\s>]*", l).group()
    return pref.count(">")


def _marca_linea(lines: list[str], i: int) -> str | None:
    l = lines[i]
    if _RE_FWD_LINE.match(l):
        return "fwd_line"
    if _RE_APPLE_ES_LINE.match(l):
        return "apple_es"
    if _RE_APPLE_EN_LINE.match(l):
        return "apple_en"
    if _RE_DEFROM_LINE.match(l):
        for j in range(i + 1, min(i + 5, len(lines))):
            if _RE_2ND_LABEL.match(lines[j]):
                return "outlook_es"
    return None


def _cabecera_head(texto: str) -> str | None:
    """Bloque de cabecera CONTIGUO al inicio del texto (tras blancos): solo si arranca con un
    run de líneas-etiqueta que contiene De/From + una 2ª etiqueta. None si el inicio es prosa.

    Evita la fabricación de remitente desde 'De:'/'From:' dispersos en mitad del cuerpo (la
    vía de misatribución que destapó la revisión adversarial)."""
    lines = texto.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    head = []
    j = i
    while j < len(lines) and _RE_ANYLABEL.match(lines[j]):
        head.append(lines[j])
        j += 1
    if not head or not any(_RE_DEFROM_LINE.match(h) for h in head):
        return None
    if not any(_RE_2ND_LABEL.match(h) for h in head):
        return None
    return "\n".join(head)


def _cuerpo_sin_cabecera(texto: str) -> str:
    """Cuerpo citado SIN el bloque de cabecera contiguo al inicio (De:/Enviado:/…).

    En la segmentación de texto plano (``outlook_es``/``fwd_line``/apple) las líneas-etiqueta
    quedan en ``seg.texto`` además de en el anclaje, a diferencia de la rama HTML —donde el
    ``<blockquote>`` ya es cuerpo puro—. Para que el puente de fidelidad (cuerpo_sha) y el
    fingerprint del segmento usen el MISMO cuerpo que un .eml limpio de Capa A, se retira ese
    encabezado. Si el texto no arranca por un bloque de cabecera, se devuelve tal cual.
    El anclaje, ``_n_cabeceras`` y ``_cabecera_head`` siguen leyendo ``seg.texto`` íntegro:
    esta limpieza solo alimenta el contenido, no la atribución ni la guarda de ambigüedad."""
    if _cabecera_head(texto) is None:
        return (texto or "").strip()
    lines = texto.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines) and _RE_ANYLABEL.match(lines[i]):
        i += 1
    return "\n".join(lines[i:]).strip()


def _n_cabeceras(texto: str) -> int:
    """Nº de bloques de cabecera (De/From + 2ª etiqueta en ≤4 líneas) en el texto. >1 = varios
    reenvíos apilados → atribución AMBIGUA (no se puede ligar el cuerpo a un único remitente)."""
    lines = texto.splitlines()
    n = 0
    for i, l in enumerate(lines):
        if _RE_DEFROM_LINE.match(l):
            for j in range(i + 1, min(i + 5, len(lines))):
                if _RE_2ND_LABEL.match(lines[j]):
                    n += 1
                    break
    return n


def _intercalada_plain(texto: str) -> bool:
    """Autor escribió ENTRE citas (sándwich): texto de autor no etiqueta/marcador entre dos
    líneas citadas. La cola de autor tras la última cita (firma) no cuenta."""
    lines = texto.splitlines()
    qi = [i for i, l in enumerate(lines) if _es_quote(l)]
    if not qi:
        return False
    for i in range(qi[0] + 1, qi[-1]):
        l = lines[i]
        if (l.strip() and not _es_quote(l) and _marca_linea(lines, i) is None
                and _RE_ANYLABEL.match(l) is None):
            return True
    return False


def _pasada_segmentos(texto: str) -> tuple[list[Segmento], str]:
    lines = texto.splitlines()
    segs: list[dict] = []
    autor_lines: list[str] = []
    cur: dict | None = None
    header_depth = 0
    i, n = 0, len(lines)

    def _flush() -> None:
        nonlocal cur
        if cur is not None:
            segs.append(cur)
            cur = None

    while i < n:
        l = lines[i]
        estilo = _marca_linea(lines, i)
        if estilo:
            _flush()
            header_depth += 1
            anclaje = [l]
            j = i + 1
            if estilo in ("outlook_es", "fwd_line"):
                while j < n and _RE_ANYLABEL.match(lines[j]):
                    anclaje.append(lines[j])
                    j += 1
            cur = {"estilo": estilo, "depth": header_depth, "estructural": False,
                   "anclaje": "\n".join(anclaje), "body": list(anclaje)}
            i = j
            continue
        if _es_quote(l):
            if cur is not None and cur["estilo"] != "quote_gt":
                cur["body"].append(l)                  # cita dentro de un bloque de cabecera
            else:
                d = _quote_depth(l)
                if not (cur is not None and cur["estilo"] == "quote_gt" and cur["depth"] == d):
                    _flush()
                    cur = {"estilo": "quote_gt", "depth": d, "estructural": True,
                           "anclaje": None, "body": []}
                cur["body"].append(l)
            i += 1
            continue
        if cur is None:
            autor_lines.append(l)
        else:
            cur["body"].append(l)
        i += 1
    _flush()

    ancestros = [
        Segmento(texto="\n".join(s["body"]).strip(), anclaje_texto=s["anclaje"],
                 profundidad=s["depth"], estilo=s["estilo"], estructural=s["estructural"])
        for s in segs
    ]
    return ancestros, "\n".join(autor_lines).strip()


def segmentar_texto(texto: str) -> Segmentacion:
    """Segmenta un cuerpo de texto plano en autor + ancestros (DD §2.2). Guarda intercalada
    primero: si el autor escribió entre citas, NO se segmenta (cero misatribución)."""
    if _intercalada_plain(texto):
        return Segmentacion(autor=texto.strip(), ancestros=[], respuesta_intercalada=True)
    ancestros, autor = _pasada_segmentos(texto)
    return Segmentacion(autor=autor, ancestros=ancestros, respuesta_intercalada=False)


# ---------------------------------------------------------------------------
# Segmentación HTML (DD §2.1, §2.0, §2.4) — stdlib html.parser, sin deps
# ---------------------------------------------------------------------------

from html.parser import HTMLParser  # noqa: E402


class _QuoteHTMLParser(HTMLParser):
    """Detecta contenedores de cita (blockquote + Outlook divRplyFwdMsg) y su anidamiento.

    gmail_quote/gmail_attr/OutlookMessageHeader NO cuentan como nivel: su texto fluye como
    autor/anclaje (el ``pending`` previo a un contenedor es su atribución).
    """

    _MAX_DEPTH = 8                      # tope de anidamiento (DD §2.1)
    _SKIP_TAGS = {"style", "script", "head"}
    # Elementos de bloque: marcan frontera de párrafo → el anclaje es el ÚLTIMO bloque previo
    # al contenedor (p. ej. el div.gmail_attr), no la suma de todos los párrafos del autor.
    _BLOCK_TAGS = {"div", "p", "table", "tr", "td", "ul", "ol", "li",
                   "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.qdepth = 0
        self.author_parts: list[str] = []
        self.segments: list[dict] = []
        self.seg_stack: list[dict] = []
        self._pending_parts: list[str] = []   # texto previo a un contenedor (anclaje), acumulado
        self.seq: list[str] = []              # "Q"/"A" para el test de sándwich (intercalada)
        self._tags: list[tuple[str, bool]] = []
        self._skip = 0                        # >0 dentro de <style>/<script>/<head>
        self.tokens_total = 0                 # tokens de texto enrutado (chequeo conservación)

    @staticmethod
    def _is_container(tag: str, attrs: list) -> bool:
        if tag == "blockquote":
            return True
        d = dict(attrs)
        return "divrplyfwdmsg" in (d.get("id") or "").lower()

    def _anchor_actual(self) -> str | None:
        return " ".join(p.strip() for p in self._pending_parts).strip() or None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._SKIP_TAGS:
            self._skip += 1
            self._tags.append((tag, False))
            return
        cont = self._is_container(tag, attrs)
        if cont and self.qdepth >= self._MAX_DEPTH:
            cont = False  # tope de profundidad: absorbe el contenido en el segmento actual
        self._tags.append((tag, cont))
        if cont:
            self.qdepth += 1
            self.seq.append("Q")
            seg = {"depth": self.qdepth, "anchor": self._anchor_actual(), "body": []}
            self.segments.append(seg)
            self.seg_stack.append(seg)
            self._pending_parts = []
        elif tag in self._BLOCK_TAGS:
            self._pending_parts = []   # nuevo bloque → el anclaje es solo el bloque anterior

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        pass  # void elements (br/hr/img) no abren contenedor

    def handle_endtag(self, tag: str) -> None:
        for k in range(len(self._tags) - 1, -1, -1):
            t, cont = self._tags[k]
            if t == tag:
                del self._tags[k]
                if t in self._SKIP_TAGS:
                    self._skip = max(0, self._skip - 1)
                elif cont:
                    self.qdepth = max(0, self.qdepth - 1)
                    if self.seg_stack:
                        self.seg_stack.pop()
                    self._pending_parts = []   # texto tras una cita cerrada no es anclaje de la anterior
                break

    def handle_data(self, data: str) -> None:
        if self._skip or not data.strip():
            return
        self.tokens_total += len(data.split())
        if self.qdepth == 0 or not self.seg_stack:   # guard: nunca se cae texto al vacío
            self.author_parts.append(data)
            self.seq.append("A")
        else:
            self.seg_stack[-1]["body"].append(data)
        self._pending_parts.append(data)


def _sandwich(seq: list[str]) -> bool:
    """¿Hay texto de autor (A) ENTRE dos citas (Q)? = respuesta intercalada en HTML."""
    seen_q = seen_a_after_q = False
    for t in seq:
        if t == "Q":
            if seen_a_after_q:
                return True
            seen_q = True
        elif t == "A" and seen_q:
            seen_a_after_q = True
    return False


def segmentar_html(html: str) -> Segmentacion:
    from .bodies import _html_a_texto
    p = _QuoteHTMLParser()
    try:
        p.feed(html)
        p.close()
    except Exception:  # noqa: BLE001 — HTML malformado → fallback a plano
        return segmentar_texto(_html_a_texto(html))
    if _sandwich(p.seq):
        return Segmentacion(autor=_html_a_texto(html), ancestros=[], respuesta_intercalada=True)
    autor = "\n".join(t.strip() for t in p.author_parts).strip()
    ancestros = [
        Segmento(texto="\n".join(t.strip() for t in s["body"]).strip(),
                 anclaje_texto=s["anchor"], profundidad=s["depth"], estilo="html_quote",
                 estructural=True)
        for s in p.segments
    ]
    # Conservación de tokens (DD §2.4): todo texto enrutado debe repartirse entre autor y
    # segmentos. Si diverge (bug de enrutado), NO segmentar: portador entero a revisión.
    repartidos = len(autor.split()) + sum(len(a.texto.split()) for a in ancestros)
    if p.tokens_total and abs(repartidos - p.tokens_total) > 0.05 * p.tokens_total:
        return Segmentacion(autor=_html_a_texto(html), ancestros=[],
                            motivo="conservacion_tokens")
    return Segmentacion(autor=autor, ancestros=ancestros, respuesta_intercalada=False)


def _html_part(raw: bytes) -> str:
    from core.email_export import iter_body_text
    for texto, es_html in iter_body_text(raw):
        if es_html:
            return texto
    return ""


def segmentar(raw: bytes) -> Segmentacion:
    """Punto de entrada: HTML si existe (caso dominante 120/138), si no texto plano."""
    from .bodies import extraer_cuerpo
    html = _html_part(raw)
    if html.strip():
        return segmentar_html(html)
    c = extraer_cuerpo(raw, conservar_resto=True)
    return segmentar_texto(c.base_sin_recortar or c.texto)


# ---------------------------------------------------------------------------
# Clasificación de confianza + guardas anti-misatribución (DD §4)
# ---------------------------------------------------------------------------

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _email_valido(s: str) -> bool:
    return bool(_RE_EMAIL.match((s or "").strip()))


def clasificar(
    anc: "Anclaje | None", fecha_portador_iso: str, *, estructural: bool, ambigua: bool,
    discrepancia: bool = False, mojibake: bool = False,
) -> tuple[str, str]:
    """``(confianza, motivo)``. Prime directive: cualquier predicado fallido demota un
    nivel, NUNCA redondea hacia arriba. ``alta-reconstruida`` reservada a atribución de
    cabecera verificada y estructural; lo demás → revisión. Matiz: un bloque completo no
    estructural (``email_ok`` + ``fecha_ok``, sin ambigüedad ni discrepancia) devuelve
    ``media-reconstruida`` (peldaño intermedio, autoría por verificar), de modo que el
    «lo demás → revisión» ya no es absoluto."""
    if anc is None or not (anc.de or (anc.fecha_iso and anc.fecha_iso != "0000-00-00")
                           or anc.asunto):
        return "baja", "sin_cabecera"
    if mojibake:
        return "baja", "mojibake"
    email_ok = _email_valido(anc.de)
    fecha_ok = bool(anc.fecha_iso and anc.fecha_iso != "0000-00-00")
    # Guarda dura: fecha de la cita POSTERIOR al portador → imposible, nunca alta.
    if (fecha_ok and fecha_portador_iso and fecha_portador_iso != "0000-00-00"
            and anc.fecha_iso > fecha_portador_iso):
        return "media", "fecha_incoherente"
    if not email_ok and not fecha_ok:
        return "baja", "sin_remitente_ni_fecha"
    if email_ok and fecha_ok and not ambigua and not discrepancia:
        if estructural:
            return "alta-reconstruida", "ok"
        return "media-reconstruida", "no_estructural"
    motivos = []
    if not email_ok:
        motivos.append("sin_email")
    if not fecha_ok:
        motivos.append("sin_fecha")
    if not estructural:
        motivos.append("no_estructural")
    if ambigua:
        motivos.append("ambiguedad_profundidad")
    if discrepancia:
        motivos.append("discrepancia_html_plano")
    return "media", ",".join(motivos) or "media"


# ---------------------------------------------------------------------------
# Orquestador: reconstruir + índice Capa A + construir_b (DD §6, §7, §9)
# ---------------------------------------------------------------------------

_RE_INLINE_MID = re.compile(r"(?im)^\s*message-id\s*:\s*<([^>]+)>")


@dataclass
class ReconResult:
    intercalada: bool = False
    candidatos: list = field(default_factory=list)   # Segmento (alta-reconstruida | media-reconstruida)
    punteros: list = field(default_factory=list)      # SegmentoEnterrado (media/baja)


class Indice:
    """Índice de Capa A para el puente de fidelidad: cuerpo_sha→msg_id y rfc_mid→msg_id."""

    def __init__(self) -> None:
        self._sha: dict[str, str] = {}
        self._mid: dict[str, str] = {}

    def por_cuerpo_sha(self, cuerpo_norm: str) -> str | None:
        return self._sha.get(cuerpo_sha_de(cuerpo_norm))

    def por_mid(self, rfc_message_id: str) -> str | None:
        return self._mid.get((rfc_message_id or "").strip())

    def resolver(self, seg: "Segmento") -> str | None:
        if seg.rfc_message_id:
            hit = self._mid.get(seg.rfc_message_id.strip())
            if hit:
                return hit
        norm = normaliza_cuerpo(seg.texto)
        if es_cuerpo_colapsable(norm):
            return self._sha.get(cuerpo_sha_de(norm))
        return None


def indice_layer_a(mensajes: list) -> Indice:
    idx = Indice()
    for m in mensajes:
        norm = normaliza_cuerpo(m.cuerpo)
        if es_cuerpo_colapsable(norm):
            idx._sha.setdefault(cuerpo_sha_de(norm), m.msg_id)
        if m.rfc_message_id:
            idx._mid.setdefault(m.rfc_message_id.strip(), m.msg_id)
    return idx


def reconstruir(m_a, raw: bytes, identidades: "Identidades | None" = None) -> ReconResult:
    """Segmenta el portador, atribuye/clasifica cada cita y separa candidatos (alta) de
    punteros (media/baja → revisión). NO asigna MSG-id (eso lo hace el pipeline).

    ``identidades`` aporta las identidades del caso (vigiladas/candidatas). Sin él → genérico.
    """
    if identidades is None:
        identidades = Identidades()
    seg_total = segmentar(raw)
    res = ReconResult(intercalada=seg_total.respuesta_intercalada)
    if seg_total.motivo:   # p.ej. conservacion_tokens → portador entero a revisión, sin segmentar
        res.punteros.append(SegmentoEnterrado(
            portador_msg_id=m_a.msg_id, estilo="carrier", confianza="info",
            motivo=seg_total.motivo, extracto=""))
    for seg in seg_total.ancestros:
        anc = parsear_anclaje(seg.anclaje_texto or "", seg.estilo)
        levantada_del_cuerpo = False
        if anc is None:
            # Fallback cabecera-en-cuerpo: SOLO el bloque contiguo al inicio del segmento
            # (nunca 'De:'/'From:' dispersos por el cuerpo → evita fabricar remitente).
            head = _cabecera_head(seg.texto)
            anc = _parse_label(head) if head else None
            levantada_del_cuerpo = anc is not None
        # Ambigüedad: varias cabeceras apiladas en el bloque de anclaje → no se puede ligar el
        # cuerpo a UN remitente. Cubre tanto la cabecera levantada del cuerpo como un bloque no
        # estructural que parsear_anclaje resolvió al primer "De:" (evita fabricar remitente con
        # el routing de media-reconstruida). En lo estructural la profundidad ya separa mensajes.
        ambigua = _n_cabeceras(seg.texto) > 1 and (levantada_del_cuerpo or not seg.estructural)
        conf, motivo = clasificar(anc, m_a.fecha_iso, estructural=seg.estructural, ambigua=ambigua)
        # Identidad candidata (no confirmada) → nunca alta (decisión Nikolai).
        if conf == "alta-reconstruida" and anc and anc.de in identidades.candidatas:
            conf, motivo = "media", "identidad_candidata"
        # El cuerpo de CONTENIDO es la cita sin su bloque de cabecera contiguo. En texto plano
        # ese encabezado quedaba en seg.texto (a diferencia del <blockquote> HTML, ya puro); sin
        # retirarlo, cuerpo_sha/fingerprint no casarían nunca con un .eml limpio de Capa A y el
        # puente de fidelidad (upgrade/dedup) jamás dispararía. La ambigüedad y el anclaje ya se
        # resolvieron arriba sobre seg.texto íntegro; el inline Message-ID se busca antes de podar.
        mm = _RE_INLINE_MID.search(seg.texto)
        seg.rfc_message_id = mm.group(1).strip() if mm else ""
        seg.texto = _cuerpo_sin_cabecera(seg.texto)
        cuerpo_norm = normaliza_cuerpo(seg.texto)
        seg.de = anc.de if anc else ""
        seg.de_nombre = anc.de_nombre if anc else ""
        seg.fecha_iso = anc.fecha_iso if anc else "0000-00-00"
        seg.asunto = anc.asunto if anc else ""
        seg.confianza = conf
        seg.motivo = motivo
        seg.cuerpo_sha = cuerpo_sha_de(cuerpo_norm)
        seg.fingerprint = fingerprint_b(anc, cuerpo_norm)
        seg.portador_msg_id = m_a.msg_id
        watched = bool(seg.de) and seg.de in identidades.vigiladas
        seg.en_revision = watched or conf in ("media", "baja", "media-reconstruida")
        if conf in ("alta-reconstruida", "media-reconstruida"):
            res.candidatos.append(seg)
        else:
            res.punteros.append(SegmentoEnterrado(
                portador_msg_id=m_a.msg_id, estilo=seg.estilo, profundidad=seg.profundidad,
                de=seg.de, fecha_iso=seg.fecha_iso, confianza=conf, motivo=motivo,
                extracto=(seg.texto or "")[:200], fingerprint=seg.fingerprint))
    return res


def construir_b(seg: "Segmento", seg_msg_id: str, m_portador) -> RegistroMensaje:
    return RegistroMensaje(
        msg_id=seg_msg_id, rfc_message_id=seg.rfc_message_id, fecha_iso=seg.fecha_iso,
        de=seg.de, de_nombre=seg.de_nombre, asunto=seg.asunto, cuerpo=seg.texto,
        capa="B", confianza=seg.confianza, reconstruido_desde_cita=True,
        reconstruido_de=m_portador.msg_id, fingerprint=seg.fingerprint,
        procedencia=[{"citado_en": m_portador.msg_id, "profundidad": seg.profundidad}],
        en_revision=seg.en_revision, fuente="email",
        fecha_inferida=(seg.fecha_iso == "0000-00-00"),
    )
