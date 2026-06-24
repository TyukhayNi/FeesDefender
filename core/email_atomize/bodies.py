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

from . import _segmenter

_RE_TAG = re.compile(r"<[^>]+>")
_RE_BR = re.compile(r"(?i)<br\s*/?>")
_RE_BLOCK = re.compile(r"(?i)</(p|div|tr|li|h[1-6])>")
_RE_MULTINL = re.compile(r"\n{3,}")
_RE_MOJI = re.compile(r"Ã[\x80-\xbf\xa1-\xff]|Â[\xa0-\xbf]|�")

_STUB_MAX = 3   # un text/plain de <=3 chars no-espacio se considera muñón


@dataclass
class Cuerpo:
    texto: str
    formato_original: str            # "plain" | "html" | "plain+html"
    charset_recuperado: bool = False
    mojibake_marcado: bool = False
    cuerpo_recortado_cita: bool = False
    respuesta_intercalada: bool = False
    base_sin_recortar: str | None = None   # cuerpo base sin recortar (solo si conservar_resto)
    resto_citado: str | None = None        # cola citada recortada (solo si conservar_resto)


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


def extraer_cuerpo(raw: bytes, *, conservar_resto: bool = False) -> Cuerpo:
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
    # Corte autor/cita por la autoridad ÚNICA compartida (también la usa Layer B).
    autor, resto, intercalada = _segmenter.cortar_autor(base)
    cuerpo = Cuerpo(
        texto=autor, formato_original=formato, charset_recuperado=recuperado,
        mojibake_marcado=moji, cuerpo_recortado_cita=resto is not None,
        respuesta_intercalada=intercalada,
    )
    if conservar_resto:
        cuerpo.base_sin_recortar = base
        cuerpo.resto_citado = resto
    return cuerpo
