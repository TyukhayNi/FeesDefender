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
# (?:\s+el)? — Outlook ES/CA emite la etiqueta de fecha como "Enviado el:" / "Enviat el:";
# el sufijo (NO capturador) deja el grupo 1 como la etiqueta desnuda. Aplica a toda etiqueta
# (inocuo: " el:" solo aparece tras Enviado/Enviat). No quitar — rompe el parseo de fecha y
# trunca el anclaje (ver spec 2026-06-25-email-atomize-enviado-el-fix-design.md).
_RE_LABEL = re.compile(
    r"(?im)^\s*(de|from|enviado|enviat|sent|fecha|date|para|to|asunto|subject|cc|cco|bcc)"
    r"(?:\s+el)?\s*:\s*(.*)$"
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
    """``(de, de_nombre)`` desde un valor De:/From:. Nunca inventa una dirección.
    Prefiere el <addr> literal: robusto ante display-names con coma ("Apellido, Nombre <addr>"),
    que rompen parseaddr (interpreta la coma como separador de direcciones). Sin <addr> → parseaddr."""
    raw = raw or ""
    m = _RE_ADDR.search(raw)
    if m:
        addr = m.group(1).lower()
        nombre = raw[: m.start()].strip().strip('"').strip().rstrip("<").strip()
        return addr, nombre
    nombre, addr = parseaddr(raw)
    if "@" in addr:
        return addr.lower(), (nombre or "").strip()
    # sin dirección real: conservar el display, dirección vacía
    return "", (nombre or addr or raw).strip()


def _parse_label(texto: str) -> "Anclaje | None":
    labels: dict[str, str] = {}
    for k, v in _RE_LABEL.findall(texto):
        labels.setdefault(k.lower(), v.strip())
    de_raw = labels.get("de") or labels.get("from") or ""
    fecha_raw = (labels.get("enviado") or labels.get("enviat") or labels.get("sent")
                 or labels.get("fecha") or labels.get("date") or "")
    asunto = labels.get("asunto") or labels.get("subject") or ""
    if not (de_raw or fecha_raw or asunto):
        return None
    de, de_nombre = _addr_o_nombre(de_raw)
    fecha_iso, fecha_dt = _parse_fecha(fecha_raw) if fecha_raw else ("0000-00-00", None)
    return Anclaje(de=de, de_nombre=de_nombre, fecha_iso=fecha_iso, fecha_dt=fecha_dt, asunto=asunto)


_RE_ATTR_FIN = re.compile(r"(?i)(escrib(?:i[oó])|wrote|va\s+escriure)\s*:\s*$")

# --- body-scan de remitente desde el CUERPO de la cita (it. 2; spec
# 2026-06-25-email-atomize-bodyscan-remitente-design.md §1.2). Cero misatribución:
# un remitente se afirma SOLO desde un <addr> literal de la cabeza acotada del cuerpo. ---
_RE_FWD_INTRO = re.compile(
    r"(?im)^\s*(?:inicio del mensaje reenviado|begin forwarded message"
    r"|---+\s*(?:mensaje reenviado|forwarded message|mensaje original|original message))\s*:?\s*$")
_RE_DE_LABEL_ANY = re.compile(r"(?im)^\s*(?:de|from)(?:\s+el)?\s*:")  # ve 'De:' AUNQUE el valor vaya envuelto
_RE_APPLE_FIN_M = re.compile(r"(?im)(?:escrib(?:i[oó])|wrote|va\s+escriure)\s*:\s*$")  # conteo correcto (re.M)
# La UNIDAD de atribución Apple: desde un "El/On" a inicio de línea hasta el terminus
# ("escribió:/wrote:/va escriure:"), DOTALL no-greedy (absorbe el <addr> envuelto en varias
# líneas). Liga el <addr> del remitente a esta unidad, no a toda la cabeza: un <addr> extraviado
# ANTES del "El" (firma/aviso legal) queda fuera y no roba el remitente.
_RE_APPLE_UNIDAD = re.compile(
    r"(?is)(?:^|\n)[ \t]*(?:el|on)\b.*?(?:escrib(?:i[oó])|wrote|va\s+escriure)[ \t]*:")
_MAX_LINEAS_SCAN = 16  # ventana del INICIO; (c) con cabecera completa envuelta cabe (ver §6 calibración)


def _parse_apple(texto: str) -> "Anclaje | None":
    # Exigir ESTRUCTURA de atribución ("El/On …" o línea que acaba en "escribió:/wrote:")
    # antes de fiarse de un <addr>: un email suelto en una cita NO es una atribución.
    m_date = _RE_APPLE.search(texto)
    if m_date is None and not _RE_ATTR_FIN.search((texto or "").strip()):
        return None
    # Ligar el remitente a la UNIDAD de atribución (del "El/On" al "escribió:/wrote:"), no a todo
    # el texto: un <addr> extraviado ANTES del "El" (firma/aviso legal) no debe robar el remitente.
    # Selección con guarda de multiplicidad: el <addr> del remitente se afirma SOLO si la unidad
    # contiene EXACTAMENTE 1 dirección. 0 = solo display-name; >1 = remitente+destinatario ambiguo.
    mu = list(_RE_APPLE_UNIDAD.finditer(texto or ""))
    unidad = mu[-1].group(0) if mu else (texto or "")
    addrs = _RE_ADDR.findall(unidad)
    de = addrs[0].lower() if len(addrs) == 1 else ""
    de_nombre = ""
    if de:
        m_addr = _RE_ADDR.search(unidad)
        prev = unidad[: m_addr.start()].rstrip()
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


def atribucion_en_cuerpo(texto: str) -> "Anclaje | None":
    """Body-scan de remitente: levanta una atribución (Apple "El …/On … escribió:" o bloque
    De:/Fecha:/Asunto: envueltos) desde la CABEZA del cuerpo de una cita (spec §1.2).

    Vector de máxima misatribución del motor: por eso es deliberadamente conservador.
    Un remitente se afirma SOLO desde un <addr> literal ligado a la clave ``de``/``from`` o a
    la unidad de atribución Apple; cualquier ambigüedad → ``None`` → el segmento sigue en cola.
    """
    # G1 — pre-filtro: sin <addr> literal → jamás (aborta los 48 antes de toda inferencia).
    if not _RE_ADDR.search(texto or ""):
        return None
    # G2 — acotar al INICIO: saltar blancos + UNA sola línea-intro de reenvío + blancos que la
    # sigan; escanear solo la ventana _MAX_LINEAS_SCAN. Nunca el cuerpo entero (evita cazar la
    # atribución de un mensaje citado más profundo más abajo).
    lines = (texto or "").splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and _RE_FWD_INTRO.match(lines[i]):
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
    cabeza = "\n".join(lines[i : i + _MAX_LINEAS_SCAN])
    if not cabeza.strip():
        return None
    # G3 — unicidad / anti-apilamiento PRIMERO, sobre la vista des-envuelta. _RE_DE_LABEL_ANY ve
    # los 'De:' envueltos que _n_cabeceras NO ve; _RE_APPLE_FIN_M cuenta atribuciones Apple (re.M).
    n_apple = len(_RE_APPLE_FIN_M.findall(cabeza))
    n_de = len(_RE_DE_LABEL_ANY.findall(cabeza))
    if (n_apple + n_de) > 1:
        return None  # varias atribuciones apiladas → AMBIGUO → cola
    # Distinguir forma y parsear (orden importa; replica parsear_anclaje sobre la cabeza acotada).
    anc = None
    # (a)/(b) — Apple. Ligar el <addr> del remitente a la UNIDAD de atribución (del "El/On" al
    # "escribió:/wrote:"), no a toda la cabeza: un <addr> extraviado ANTES del "El" (firma/aviso
    # legal) no debe robar el remitente. La forma (b) (addr envuelto) cabe: la unidad es DOTALL.
    if _RE_APPLE.search(cabeza) or _RE_ATTR_FIN.search(cabeza.strip()):
        unidades = list(_RE_APPLE_UNIDAD.finditer(cabeza))
        if unidades:
            unidad = unidades[-1].group(0)  # la atribución terminal (la más cercana al cuerpo)
            # G4 (re-ligada a la UNIDAD, no a la línea): exactamente 1 <addr> en la unidad. 0 = sin
            # remitente en la atribución; >1 = remitente+destinatario ambiguo → cola. Más estricta.
            if len(_RE_ADDR.findall(unidad)) != 1:
                return None
            anc = _parse_apple(unidad)
    # (c) — bloque De:/Fecha:/Asunto:. El <addr> sale SOLO de la clave de/from (G5).
    if anc is None:
        anc = _parse_label(cabeza)
    # G5/G1 — exigir remitente real: el body-scan NUNCA devuelve un Anclaje sin ``de``.
    if anc is None or not anc.de:
        return None
    return anc


# --- it.3: promoción del INTERIOR REENVIADO + parse c′ (spec
# 2026-06-25-email-atomize-interior-reenviado-cprime-design.md §1). Cero misatribución: el <addr>
# del remitente del interior se afirma SOLO desde la franja De:→primera-etiqueta, con tope
# obligatorio + unicidad + guarda de delegación; cualquier duda → ("","") → el interior no se promueve. ---
# Marcador de reenvío EXPLÍCITO, line-anchored, tolerante a guiones/nbsp de cierre y forma bare
# (el _RE_FWD_INTRO de it.2 FALLA con "---------- Forwarded message ---------" por los guiones de cierre).
_RE_FWD_MARK = re.compile(
    r"(?im)^[\s\-]*(?:inicio del mensaje reenviado|begin forwarded message|forwarded message"
    r"|mensaje reenviado|mensaje original|original message)[\s\-:]*$")
# Etiqueta GENÉRICA (incluye Reply-To/Responder a/Destinatario/…): cierra la franja del remitente.
# Acotada a 1-30 chars de "palabra" + ':' para no tragar el cuerpo prosa.
_RE_GEN_LABEL = re.compile(r"(?im)^\s*[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 ._-]{0,30}:")
# Fórmula de delegación/relay: el <addr> NO es del autor nombrado → no se afirma remitente.
# Incluye p.p. (per procura) / p.o. (por orden) y 'vía' con tilde (verificación adversarial it.3).
_RE_DELEGACION = re.compile(
    r"(?i)(?:\ben nombre de\b|\bon behalf of\b|\bv[ií]a\b|\bpor orden de\b|\bp\.\s*p\.|\bp\.\s*o\.)")


def _addr_remitente_cprime(lines: "list[str]", de_idx: int) -> "tuple[str, str]":
    """Liga el ``<addr>`` del REMITENTE a la franja ``De:``→primera-etiqueta (forma c′: el valor del
    ``De:`` es un nombre/bare y el ``<addr>`` va envuelto en líneas siguientes). Devuelve
    ``(de, de_nombre)``; ``("", "")`` ante cualquier duda (prime directive: cero misatribución)."""
    # tope = primera línea POSTERIOR al De: que sea una etiqueta genérica (incl. Reply-To/Para/Fecha…).
    tope = de_idx + 1
    while tope < len(lines) and not _RE_GEN_LABEL.match(lines[tope]):
        tope += 1
    if tope == len(lines):
        return "", ""                       # sin etiqueta de cierre → la franja tragaría el cuerpo
    franja = "\n".join(lines[de_idx:tope])
    if _RE_DELEGACION.search(franja):
        return "", ""                       # delegación/relay: el <addr> no es del autor nombrado
    addrs = _RE_ADDR.findall(franja)
    if len(addrs) != 1:
        return "", ""                       # 0 = solo nombre; >1 = ambiguo (remitente+otro)
    de = addrs[0].lower()
    m = _RE_ADDR.search(franja)
    prev = re.sub(r"(?i)^\s*(?:de|from)(?:\s+el)?\s*:", "", franja[: m.start()], count=1)
    de_nombre = prev.replace("<", " ").strip().strip('"').strip().rstrip(",").strip()
    return de, de_nombre


_RE_EMAIL_FRAG = re.compile(r"^[<>,\s]*[^@\s<>]+@[^@\s<>]+[>,\s]*$")


def _cuerpo_interior(lines: "list[str]", de_idx: int) -> str:
    """Cuerpo del interior reenviado SIN su cabecera c′ (De:/Fecha:/Asunto:/Para:/Cc: + valores
    envueltos). Poda con etiquetas CONOCIDAS (``_RE_ANYLABEL``, no genéricas — para no tragar
    saludos que terminan en ':') + fragmentos de envoltura. Poda CONSISTENTE entre wraps distintos
    del mismo interior → ``cuerpo_sha`` estable (dedup entre portadores redundantes)."""
    i, n = de_idx, len(lines)
    while i < n:
        l = lines[i]
        s = l.strip()
        if _RE_ANYLABEL.match(l):                         # etiqueta conocida (De/Fecha/Asunto/Para/Cc/…)
            i += 1
            continue
        if s in ("<", ">", "<,", ">,") or s.endswith("<"):  # fragmento de envoltura / dest. partido
            i += 1
            continue
        if _RE_ADDR.search(l) or _RE_EMAIL_FRAG.match(s):    # email bare/bracketed (valor envuelto)
            i += 1
            continue
        # línea de NOMBRE (display) entre etiqueta y <addr>: ≤6 palabras, sin '.'/'!'/'?' final, y
        # seguida INMEDIATAMENTE (≤2 líneas) por un '<' SOLO o un <addr> envuelto → parte del valor
        # De:/destinatario. Exigir el wrap real (no un '@' cualquiera) evita comerse un saludo corto
        # cuyo cuerpo mencione un email poco después (hallazgo de la verificación adversarial it.3).
        if (s and len(s.split()) <= 6 and s[-1] not in ".!?"
                and any(lines[k].strip() == "<" or _RE_EMAIL_FRAG.match(lines[k].strip())
                        for k in range(i + 1, min(i + 3, n)))):
            i += 1
            continue
        break                                              # primera línea de prosa = inicio del cuerpo
    return "\n".join(lines[i:]).strip()


def _interior_reenviado(texto: str) -> "tuple[Anclaje, str] | None":
    """Desanida UN interior reenviado del cuerpo de un segmento ya reconstruido (spec §1.4).
    Acotado por marcador de reenvío EXPLÍCITO (``_RE_FWD_MARK``); UN solo nivel (no recursión).
    Devuelve ``(Anclaje_del_interior, cuerpo_del_interior)`` o ``None``. El remitente se afirma SOLO
    desde un ``<addr>`` literal ligado al ``De:`` del interior (Apple unidad o franja c′)."""
    if not texto:
        return None
    mk = _RE_FWD_MARK.search(texto)
    if mk is None:
        return None                                   # G-MARK: marcador de reenvío explícito obligatorio
    post = texto[mk.end():].splitlines()
    i = 0
    while i < len(post) and not post[i].strip():
        i += 1
    post = post[i:]
    if not post:
        return None
    vent = post[: _MAX_LINEAS_SCAN]                    # ventana solo para apilamiento + parseo de cabecera
    cab = "\n".join(vent)
    # G-APILAMIENTO: >1 atribución en la ventana → ambiguo → cola (garantiza 1 nivel, no recursión).
    if len(_RE_APPLE_FIN_M.findall(cab)) + len(_RE_DE_LABEL_ANY.findall(cab)) > 1:
        return None
    # Solo interiores con bloque De:/Fecha:/Asunto: (incl. forma c′). Los interiores en forma Apple
    # ("El…escribió:") tras un marcador NO se desanidan (no ocurren en el corpus real; §6) → cola:
    # evita el hueco de poda de la cabecera Apple con <addr> envuelto.
    de_idx = next((k for k, ln in enumerate(vent) if _RE_DE_LABEL_ANY.match(ln)), None)
    if de_idx is None:
        return None
    # G-DELEGACION (unificada, ambas ramas inline+c′): franja De:→primera-etiqueta; si trae fórmula
    # de delegación/relay ("en nombre de"/"on behalf of"/"vía"/"por orden de"/"p.p."/"p.o.") → cola.
    # Cierra el hueco hallado por la verificación adversarial: el path inline (<addr> en la línea De:)
    # pasaba por _parse_label/_addr_o_nombre SIN guarda de delegación → afirmaba el relay.
    tope = de_idx + 1
    while tope < len(vent) and not _RE_GEN_LABEL.match(vent[tope]):
        tope += 1
    if _RE_DELEGACION.search("\n".join(vent[de_idx:tope])):
        return None
    anc = _parse_label(cab)
    if anc is None:
        return None
    if not anc.de:                                    # forma c′: <addr> envuelto → lookahead acotado
        de, de_nombre = _addr_remitente_cprime(vent, de_idx)
        if de:
            anc.de, anc.de_nombre = de, de_nombre
    if not anc.de:
        return None                                   # G5: nunca se afirma remitente sin <addr> literal
    cuerpo = _cuerpo_interior(post, de_idx)            # poda la cabecera c′ propia (cuerpo_sha estable)
    if not cuerpo.strip():
        return None
    return anc, cuerpo


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
    # Trozos de firma descartados del veto de `_sandwich`, y SOLO cuando esa exclusion cambio
    # el veredicto (spec 2026-07-29 §5.1). Transporta la traza hasta `reconstruir`.
    firma_excluida: int = 0

_RE_FWD_LINE = re.compile(
    r"(?i)^\s*-{2,}\s*(forwarded message|mensaje reenviado|reenviado|begin forwarded message"
    r"|original message|mensaje original)")
_RE_APPLE_ES_LINE = re.compile(r"(?i)^\s*el\s+.+?\s+(?:escribi[oó]|va\s+escriure)\s*:\s*$")
_RE_APPLE_EN_LINE = re.compile(r"(?i)^\s*on\s+.+?\s+wrote\s*:\s*$")
_RE_DEFROM_LINE = re.compile(r"(?i)^\s*(?:de|from)\s*:\s*\S")
# ver nota en _RE_LABEL sobre (?:\s+el)?
_RE_2ND_LABEL = re.compile(
    r"(?i)^\s*(enviado|enviat|sent|fecha|date|para|to|asunto|subject|cc|cco|bcc)(?:\s+el)?\s*:")
# ver nota en _RE_LABEL sobre (?:\s+el)?
_RE_ANYLABEL = re.compile(
    r"(?i)^\s*(de|from|enviado|enviat|sent|fecha|date|para|to|asunto|subject|cc|cco|bcc)(?:\s+el)?\s*:")


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
    texto = texto or ""
    if _cabecera_head(texto) is None:
        return texto.strip()
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

# --- Contenedor de firma (spec 2026-07-29 §3) ------------------------------------------
# El predicado es ESTRUCTURAL: se escribe sobre `class`/`id`, nunca sobre el texto. Una lista
# de palabras ya se descarto por fragil y medida: 7 de 21 trozos se escapaban porque eran solo
# el NOMBRE de la persona. `gmail_signature` es el unico marcador necesario — medido sobre el
# corpus real: anadir "signature" o "firma" a esta tupla NO cambia ningun veredicto, porque los
# 28 trozos de firma de la muestra ya caen bajo `gmail_signature` (cubre tambien
# `gmail_signature_prefix` por ser subcadena). La tupla es el punto de extension cuando
# aparezca un cliente que marque su firma de otra forma.
_SIG_MARKERS = ("gmail_signature",)

_TOK_CITA = "Q"      # contenedor de cita
_TOK_AUTOR = "A"     # texto fuera de la cita
_TOK_FIRMA = "S"     # texto fuera de la cita PERO bajo un contenedor de firma


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
        self._tags: list[tuple[str, bool, bool]] = []   # (tag, es_contenedor, es_firma)
        self._skip = 0                        # >0 dentro de <style>/<script>/<head>
        self.tokens_total = 0                 # tokens de texto enrutado (chequeo conservación)
        self._sigdepth = 0                    # >0 dentro de un contenedor de firma
        self.firma_trozos = 0                 # trozos de autor marcados como firma

    @staticmethod
    def _is_container(tag: str, attrs: list) -> bool:
        if tag == "blockquote":
            return True
        d = dict(attrs)
        return "divrplyfwdmsg" in (d.get("id") or "").lower()

    @staticmethod
    def _is_signature(tag: str, attrs: list) -> bool:
        d = dict(attrs)
        val = f"{d.get('class') or ''} {d.get('id') or ''}".lower()
        return any(m in val for m in _SIG_MARKERS)

    def _anchor_actual(self) -> str | None:
        return " ".join(p.strip() for p in self._pending_parts).strip() or None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._SKIP_TAGS:
            self._skip += 1
            self._tags.append((tag, False, False))
            return
        cont = self._is_container(tag, attrs)
        if cont and self.qdepth >= self._MAX_DEPTH:
            cont = False  # tope de profundidad: absorbe el contenido en el segmento actual
        sig = self._is_signature(tag, attrs)
        self._tags.append((tag, cont, sig))
        if sig:
            self._sigdepth += 1
        if cont:
            self.qdepth += 1
            self.seq.append(_TOK_CITA)
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
            t, cont, sig = self._tags[k]
            if t == tag:
                # Las entradas POR ENCIMA de k quedaron huerfanas (etiquetas sin cerrar dentro de
                # este elemento). Se dan por cerradas SOLO en la dimension `sig`: sin esto, el
                # ambito de una firma sobrevive a su propio elemento y un cierre suelto posterior
                # lo devuelve a 0, con lo que `firma_fiable` vuelve a ser True mientras hay texto
                # de autor marcado como firma -> veto correcto levantado. Es la misma direccion
                # prohibida que cierra el guard de `segmentar_html`, por una via que el guard no
                # ve (el desbalance no llega al final del documento).
                # `cont`/`qdepth` NO se tocan a proposito: cambiarlos moveria la segmentacion de
                # correos que hoy funcionan, y la Capa A tiene que quedar byte-identica.
                for j in range(k + 1, len(self._tags)):
                    tj, cj, sj = self._tags[j]
                    if sj:
                        self._sigdepth = max(0, self._sigdepth - 1)
                        self._tags[j] = (tj, cj, False)
                del self._tags[k]
                if t in self._SKIP_TAGS:
                    self._skip = max(0, self._skip - 1)
                elif cont:
                    self.qdepth = max(0, self.qdepth - 1)
                    if self.seg_stack:
                        self.seg_stack.pop()
                    self._pending_parts = []   # texto tras una cita cerrada no es anclaje de la anterior
                if sig:
                    self._sigdepth = max(0, self._sigdepth - 1)
                break

    def handle_data(self, data: str) -> None:
        if self._skip or not data.strip():
            return
        self.tokens_total += len(data.split())
        if self.qdepth == 0 or not self.seg_stack:   # guard: nunca se cae texto al vacío
            self.author_parts.append(data)           # el enrutado NO cambia (spec §3)
            if self._sigdepth:
                self.seq.append(_TOK_FIRMA)
                self.firma_trozos += 1
            else:
                self.seq.append(_TOK_AUTOR)
        else:
            self.seg_stack[-1]["body"].append(data)
        self._pending_parts.append(data)


def _sandwich(seq: list[str], *, firma_como_autor: bool = False) -> bool:
    """¿Hay texto de autor (A) ENTRE dos citas (Q)? = respuesta intercalada en HTML.

    Los trozos bajo un contenedor de firma llegan como ``_TOK_FIRMA`` y NO cuentan como texto
    de autor (spec 2026-07-29 §3): la firma de E&V va linea a linea en su propio elemento y en
    los hilos de Gmail queda ENTRE dos citas. La exclusion es ADITIVA — si queda un trozo de
    autor real, esto sigue devolviendo True (medido: 4 de los 7 portadores vetados de la muestra
    lo siguen estando).

    *firma_como_autor* recupera el veredicto de ANTES de la exclusion. Sus dos usos: saber si la
    exclusion cambio el veredicto (para emitir la traza, §5.1) y el guard fail-closed de
    `segmentar_html` cuando la firma queda sin cerrar.
    """
    seen_q = seen_a_after_q = False
    for t in seq:
        if t == _TOK_CITA:
            if seen_a_after_q:
                return True
            seen_q = True
        elif seen_q and (t == _TOK_AUTOR or (firma_como_autor and t == _TOK_FIRMA)):
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
    # FAIL-CLOSED (hallazgo B0 de la revision adversarial, reproducido): si al cerrar el
    # documento queda un contenedor de firma SIN CERRAR, `_sigdepth` nunca volvio a 0 y TODO el
    # texto de autor posterior quedo marcado como firma. Excluirlo del veto levantaria un veto
    # CORRECTO -- la unica direccion en la que esta regla NO puede fallar (spec §3). Cuando la
    # firma no es fiable, sus trozos vuelven a contar como autor.
    # `HTMLParser.close()` no sintetiza cierres ni lanza excepcion, asi que el fallback a texto
    # plano de arriba no cubre este caso.
    # Medido: la firma queda abierta en 1 de 271 correos reales (0 de 24 en la prueba de
    # Gmail, 1 de 247 en W-02VND1) y el guard NO cuesta ni un portador desbloqueado: 3 con
    # guard y 3 sin guard. El defecto estaba armado y no habia disparado.
    # (La cifra de «20 de 271» de una primera medicion era FALSA: se midio con un conjunto
    # de marcadores mas ancho que el que se implementa. Corregida por la revision de rama.)
    firma_fiable = p._sigdepth == 0
    if _sandwich(p.seq, firma_como_autor=not firma_fiable):
        # Se declara SOLO cuando el desbalance es lo que sostiene el veto; si no, seria ruido
        # en el 7 % de correos que cierran con la firma abierta sin consecuencia.
        mot = "" if firma_fiable or _sandwich(p.seq) else "firma_sin_cerrar"
        return Segmentacion(autor=_html_a_texto(html), ancestros=[],
                            respuesta_intercalada=True, motivo=mot)
    autor = "\n".join(t.strip() for t in p.author_parts).strip()
    ancestros = [
        Segmento(texto="\n".join(t.strip() for t in s["body"]).strip(),
                 anclaje_texto=s["anchor"], profundidad=s["depth"], estilo="html_quote",
                 estructural=True)
        for s in p.segments
    ]
    # Traza (spec §5.1): SOLO cuando la exclusion de firma cambio el veredicto, no en cada correo
    # con firma. Llegar aqui implica que la exclusion no sostiene ningun veto — NO implica
    # `firma_fiable` (con `_sigdepth > 0` y sin sandwich tambien se llega, y entonces esto da 0).
    firma_excluida = p.firma_trozos if _sandwich(p.seq, firma_como_autor=True) else 0
    # Conservación de tokens (DD §2.4): todo texto enrutado debe repartirse entre autor y
    # segmentos. Si diverge (bug de enrutado), NO segmentar: portador entero a revisión.
    # `firma_excluida` SI se arrastra a esta rama: la exclusion cambio el veredicto de `_sandwich`
    # aunque la conservacion vete despues por otra razon, y el puntero de `conservacion_tokens` no
    # informa de ese cambio (hallazgo A de la revision adversarial, aceptado).
    repartidos = len(autor.split()) + sum(len(a.texto.split()) for a in ancestros)
    if p.tokens_total and abs(repartidos - p.tokens_total) > 0.05 * p.tokens_total:
        return Segmentacion(autor=_html_a_texto(html), ancestros=[],
                            motivo="conservacion_tokens", firma_excluida=firma_excluida)
    return Segmentacion(autor=autor, ancestros=ancestros, respuesta_intercalada=False,
                        firma_excluida=firma_excluida)


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


def _emitir_interior(texto_exterior_original, seg, m_a, identidades) -> "Segmento | None":
    """it.3 §1.5 — desanida UN interior reenviado del cuerpo del exterior (acotado por marcador
    explícito) y devuelve un ``Segmento`` sintético, o ``None``. Lee SIEMPRE el texto del exterior
    pre-poda. El interior topa a ``media-reconstruida`` (límite de cuerpo no autenticado por DOM)."""
    inter = _interior_reenviado(texto_exterior_original or "")
    if inter is None:
        return None
    anc_i, cuerpo_i = inter
    # G-NO-DUP-EXT: el interior no es el MISMO mensaje que el exterior (identidad de mensaje de+fecha,
    # NO de-inequality — que mataría el testigo: Eva reenvía su propio correo del 7-jul el 23-jul).
    if anc_i.de == seg.de and anc_i.fecha_iso == seg.fecha_iso:
        return None
    ambigua_i = _n_cabeceras(cuerpo_i) > 1                       # G-AMBIGUA-INTERIOR (hereda G6)
    conf_i, mot_i = clasificar(anc_i, m_a.fecha_iso, estructural=False, ambigua=ambigua_i)
    if conf_i in ("media-reconstruida", "alta-reconstruida"):   # estructural=False ⇒ jamás alta; defensivo
        conf_i, mot_i = "media-reconstruida", "interior_reenviado"
    # Identidad candidata (no confirmada) → cap a media + ruta identidades_vigiladas (routing heredado).
    if anc_i.de in identidades.candidatas and conf_i == "media-reconstruida":
        conf_i, mot_i = "media", "identidad_candidata"
    cuerpo_norm_i = normaliza_cuerpo(cuerpo_i)
    mm_i = _RE_INLINE_MID.search(cuerpo_i)
    return Segmento(
        texto=cuerpo_i, estilo="interior_reenviado", estructural=False,
        profundidad=seg.profundidad + 1, de=anc_i.de, de_nombre=anc_i.de_nombre,
        fecha_iso=anc_i.fecha_iso, asunto=anc_i.asunto, confianza=conf_i, motivo=mot_i,
        cuerpo_sha=cuerpo_sha_de(cuerpo_norm_i), fingerprint=fingerprint_b(anc_i, cuerpo_norm_i),
        portador_msg_id=m_a.msg_id, rfc_message_id=(mm_i.group(1).strip() if mm_i else ""),
        en_revision=True)


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
    if seg_total.firma_excluida:
        # spec 2026-07-29 §5.1: la correccion del veto deja rastro. Solo se emite cuando la
        # exclusion CAMBIO el veredicto (lo garantiza `firma_excluida`), no en cada correo con
        # firma.
        res.punteros.append(SegmentoEnterrado(
            portador_msg_id=m_a.msg_id, estilo="firma_excluida_del_veto", confianza="info",
            motivo=f"trozos_firma={seg_total.firma_excluida}", extracto=""))
    for seg in seg_total.ancestros:
        texto_exterior_original = seg.texto   # [G-CAPTURA] it.3: copia pre-poda para desanidar el interior
        anc = parsear_anclaje(seg.anclaje_texto or "", seg.estilo)
        levantada_del_cuerpo = False
        if anc is None:
            # Fallback cabecera-en-cuerpo: SOLO el bloque contiguo al inicio del segmento
            # (nunca 'De:'/'From:' dispersos por el cuerpo → evita fabricar remitente).
            head = _cabecera_head(seg.texto)
            anc = _parse_label(head) if head else None
            levantada_del_cuerpo = anc is not None
        # Body-scan acotado (it. 2): SOLO si seguimos sin REMITENTE atribuible. Trigger por
        # disyunción (anc is None OR not anc.de) → cubre el anclaje vacío Y el estructural que
        # parseó solo fecha. Nunca pisa una atribución que ya dio ``de`` (gana el anchor legítimo).
        if (anc is None or not anc.de) and seg.texto:
            anc_body = atribucion_en_cuerpo(seg.texto)
            if anc_body is not None:
                anc = anc_body
                levantada_del_cuerpo = True   # gobierna confianza (§3) y ambigüedad
        # Ambigüedad: varias cabeceras apiladas en el bloque de anclaje → no se puede ligar el
        # cuerpo a UN remitente. Cubre tanto la cabecera levantada del cuerpo como un bloque no
        # estructural que parsear_anclaje resolvió al primer "De:" (evita fabricar remitente con
        # el routing de media-reconstruida). En lo estructural la profundidad ya separa mensajes.
        ambigua = _n_cabeceras(seg.texto) > 1 and (levantada_del_cuerpo or not seg.estructural)
        conf, motivo = clasificar(anc, m_a.fecha_iso, estructural=seg.estructural, ambigua=ambigua)
        # Atribución levantada del cuerpo: el límite de cuerpo no está autenticado por estructura
        # DOM. Nunca alta-reconstruida; tope media-reconstruida (cierra el hueco blockquote-DOM-con-
        # cita-interior). Subsume el fallback _cabecera_head preexistente: todo lo levantado del
        # cuerpo topa a media-reconstruida (coherente y más seguro).
        if levantada_del_cuerpo and conf == "alta-reconstruida":
            conf, motivo = "media-reconstruida", "atribucion_cuerpo"
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
        # it.3 — desanidar UN interior reenviado del cuerpo del exterior (atom ADICIONAL; el exterior
        # NO se toca). Acotado por marcador explícito; dedup por fingerprint en el pipeline.
        seg_i = _emitir_interior(texto_exterior_original, seg, m_a, identidades)
        if seg_i is not None:
            if seg_i.confianza in ("alta-reconstruida", "media-reconstruida"):
                res.candidatos.append(seg_i)
            else:
                res.punteros.append(SegmentoEnterrado(
                    portador_msg_id=m_a.msg_id, estilo=seg_i.estilo, profundidad=seg_i.profundidad,
                    de=seg_i.de, fecha_iso=seg_i.fecha_iso, confianza=seg_i.confianza,
                    motivo=seg_i.motivo, extracto=(seg_i.texto or "")[:200],
                    fingerprint=seg_i.fingerprint))
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
