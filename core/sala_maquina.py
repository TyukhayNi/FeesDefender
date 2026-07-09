"""Cerebro + orquestador de la Sala de máquina (skill organizar-sala-maquina).

Convierte el crudo de 00_Input/ en 01_Procesado/02_Sala de máquina/:
  01_OCR/     PDFs buscables (OCRmyPDF)   03_MD/  markdown legible   raw_text/  intermedio

NO usa pipeline.run() ni la rama Docling/30pp de extractor. OCR aguas arriba con
OCRmyPDF (sin tope de páginas); reutiliza solo los helpers deterministas sanos del
extractor. Ver docs/superpowers/specs/2026-07-09-organizar-sala-maquina-design.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.utils import output_slug

_EXTS_IMAGEN = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic", ".heif", ".webp", ".bmp", ".gif"}
_EXTS_NATIVO = {".eml", ".txt", ".md", ".rtf", ".ics", ".csv", ".xlsx", ".xls", ".docx", ".html", ".htm"}


def clasificar_ruta(ext: str) -> str:
    """Enruta por extensión: 'pdf' | 'imagen' | 'nativo' | 'sin_soporte'."""
    e = ext.lower()
    if e == ".pdf":
        return "pdf"
    if e in _EXTS_IMAGEN:
        return "imagen"
    if e in _EXTS_NATIVO:
        return "nativo"
    return "sin_soporte"


_MIN_CHARS = 40                 # < esto para el documento entero = empty
_MIN_DENSIDAD = 40              # char/pág mínima (alineado con extractor._texto_suficiente)
_MAX_GIBBERISH = 0.40           # > 40% de tokens sin vocal = OCR ruidoso
_TOKEN_RE = re.compile(r"[^\W\d_]{2,}", re.UNICODE)   # tokens alfabéticos (incl. tildes/cirílico)
_VOCALES = set("aeiouáéíóúàèìòùüïAEIOUÁÉÍÓÚÀÈÌÒÙÜÏаэеёиоуыюяАЭЕЁИОУЫЮЯ")


def _ratio_gibberish(text: str) -> float:
    """Fracción de tokens alfabéticos (≥2 letras) que NO tienen ninguna vocal.

    Un OCR ruidoso produce tiras consonánticas ('xkq', 'brrr'); las palabras
    reales en spa/cat/rus casi siempre llevan vocal. 0.0 si no hay tokens.
    """
    tokens = _TOKEN_RE.findall(text)
    if not tokens:
        return 1.0
    sin_vocal = sum(1 for t in tokens if not (set(t) & _VOCALES))
    return sin_vocal / len(tokens)


def ocr_quality(text: str, n_pags: int | None) -> tuple[str, str]:
    """Estado de calidad del texto extraído: ('ok'|'low'|'empty', motivo).

    Tres señales (spec §5.2): densidad char/pág, ratio de gibberish, léxico.
    No aborta: solo clasifica para la worklist de revisión humana.
    """
    t = (text or "").strip()
    if len(t) < _MIN_CHARS:
        return "empty", "sin texto o residual"
    gib = _ratio_gibberish(t)
    if gib > _MAX_GIBBERISH:
        return "low", f"gibberish {gib:.0%} (OCR ruidoso o idioma no soportado)"
    if n_pags and n_pags > 0 and (len(t) / n_pags) < _MIN_DENSIDAD:
        return "low", f"densidad baja ({len(t) // max(n_pags,1)} char/pág)"
    return "ok", ""


_EXCLUIR_PREFIJOS = ("90_Notas personales/", "90_Notas personales\\")


@dataclass
class DocPlan:
    rel_path: str
    sha256: str
    ext: str
    ruta: str            # pdf | imagen | nativo | sin_soporte
    slug: str            # output_slug (slug__sha8)
    skip: bool = False


@dataclass
class DocCobertura:
    slug: str
    rel_path: str
    metodo: str          # pypdf | ocr | nativo | sin_soporte
    estado: str          # ok | low | empty | sin_texto | sin_soporte
    chars: int = 0
    ocr: bool = False
    nota: str = ""


def plan(inventario: list[dict], estado_previo: set[str]) -> list[DocPlan]:
    """Puro: enruta cada fichero y marca skip si su sha ya fue procesado.

    Excluye 90_Notas personales/ (zona del abogado, invariante del proyecto).
    """
    out: list[DocPlan] = []
    for f in inventario:
        rel = f["rel_path"]
        if rel.startswith(_EXCLUIR_PREFIJOS):
            continue
        sha = f["sha256"]
        out.append(DocPlan(
            rel_path=rel,
            sha256=sha,
            ext=f["ext"],
            ruta=clasificar_ruta(f["ext"]),
            slug=output_slug(rel, sha),
            skip=sha in estado_previo,
        ))
    return out
