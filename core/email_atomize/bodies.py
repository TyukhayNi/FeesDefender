"""Extracción y limpieza del cuerpo: solo lo que escribió el autor.

Reglas (spec §6): preferir text/plain; HTML→texto si el plano está vacío/muñón; recuperación
de charset condicional (solo si el sniff de mojibake dispara y el round-trip reduce marcas);
recortar la cola citada (top/bottom-posting) salvo respuesta intercalada (se conserva íntegra).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

from core.email_export import iter_body_text

_RE_TAG = re.compile(r"<[^>]+>")
_RE_BR = re.compile(r"(?i)<br\s*/?>")
_RE_BLOCK = re.compile(r"(?i)</(p|div|tr|li|h[1-6])>")
_RE_MULTINL = re.compile(r"\n{3,}")
_RE_MOJI = re.compile(r"Ã[\x80-\xbf\xa1-\xff]|Â[\xa0-\xbf]|�")

# Encabezados de cita típicos (es/en) que marcan el inicio de la cola citada.
_RE_CITA_HDR = re.compile(
    r"^\s*(el .+escribi[oó]:|on .+wrote:|-{2,}\s*(mensaje original|original message"
    r"|forwarded message|reenviado).*|de\s*:.*\n.*(enviado|asunto)\s*:)",
    re.IGNORECASE | re.MULTILINE,
)
_STUB_MAX = 3   # un text/plain de <=3 chars no-espacio se considera muñón


@dataclass
class Cuerpo:
    texto: str
    formato_original: str            # "plain" | "html" | "plain+html"
    charset_recuperado: bool = False
    mojibake_marcado: bool = False
    cuerpo_recortado_cita: bool = False
    respuesta_intercalada: bool = False


def _html_a_texto(html: str) -> str:
    t = _RE_BR.sub("\n", html)
    t = _RE_BLOCK.sub("\n", t)
    t = _RE_TAG.sub("", t)
    t = unescape(t)
    return _RE_MULTINL.sub("\n\n", t).strip()


def _recupera_charset(texto: str) -> tuple[str, bool]:
    """Si hay mojibake y el round-trip cp1252→utf-8 REDUCE marcas, aplicarlo."""
    antes = len(_RE_MOJI.findall(texto))
    if antes == 0:
        return texto, False
    try:
        fix = texto.encode("cp1252", errors="strict").decode("utf-8", errors="strict")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto, False
    if len(_RE_MOJI.findall(fix)) < antes:
        return fix, True
    return texto, False


def _es_linea_citada(linea: str) -> bool:
    return linea.lstrip().startswith(">")


def _limpia_cita(texto: str) -> tuple[str, bool, bool]:
    """Devuelve (texto_limpio, recortado, intercalada).

    Intercalada: hay líneas citadas (>) seguidas de líneas de autor MÁS ABAJO → conservar
    íntegro. Top/bottom-posting: la cola citada es un bloque final contiguo → recortarla
    (incluyendo su encabezado "El … escribió:").
    """
    lineas = texto.splitlines()
    quoted_idx = [i for i, l in enumerate(lineas) if _es_linea_citada(l)]
    if not quoted_idx:
        # buscar encabezado de cita sin '>' (reenvíos): recortar desde ahí
        m = _RE_CITA_HDR.search(texto)
        if m and m.start() > 0:
            return texto[: m.start()].rstrip(), True, False
        return texto.strip(), False, False
    # ¿hay líneas de autor (no vacías, no citadas) DESPUÉS de la primera cita?
    primera = quoted_idx[0]
    autor_despues = any(
        l.strip() and not _es_linea_citada(l) and not _RE_CITA_HDR.match(l)
        for l in lineas[primera + 1:]
    )
    if autor_despues:
        return texto.strip(), False, True  # intercalada: no recortar
    # cola citada al final: recortar desde el encabezado de cita si existe, si no desde la
    # primera línea citada.
    corte = primera
    m = _RE_CITA_HDR.search(texto)
    if m:
        # recortar por el encabezado si cae antes del primer '>'
        pre = texto[: m.start()].count("\n")
        corte = min(corte, pre)
    limpio = "\n".join(lineas[:corte]).rstrip()
    return limpio, True, False


def extraer_cuerpo(raw: bytes) -> Cuerpo:
    plano = ""
    html = ""
    for texto, es_html in iter_body_text(raw):
        if es_html and not html:
            html = texto
        elif not es_html and not plano:
            plano = texto
    if len(plano.replace(" ", "").strip()) > _STUB_MAX:
        base, formato = plano, "plain"
    elif html:
        base, formato = _html_a_texto(html), "html"
    else:
        base, formato = plano, "plain"
    base, recuperado = _recupera_charset(base)
    moji = len(_RE_MOJI.findall(base)) > 0
    limpio, recortado, intercalada = _limpia_cita(base)
    return Cuerpo(
        texto=limpio, formato_original=formato, charset_recuperado=recuperado,
        mojibake_marcado=moji, cuerpo_recortado_cita=recortado,
        respuesta_intercalada=intercalada,
    )
