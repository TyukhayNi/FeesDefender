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
from pathlib import Path

from core.extractor import _try_pypdf, _pdf_num_paginas, _texto_suficiente
from core.anon.ocr import ocr_pdf
from core.utils import now_iso, output_slug, text_sha256, write_md

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


def render_cobertura(cobertura: list[DocCobertura]) -> str:
    """Puro: Markdown de _cobertura.md. Dudosos (estado != ok) primero."""
    orden = {"empty": 0, "sin_texto": 0, "sin_soporte": 1, "low": 2, "ok": 3}
    filas = sorted(cobertura, key=lambda d: (orden.get(d.estado, 0), d.slug))
    lineas = [
        "<!-- GENERADO — NO EDITAR A MANO -->",
        "# Cobertura de la Sala de máquina",
        "",
        "| documento | origen | método | estado | chars | ocr | nota |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in filas:
        lineas.append(
            f"| {d.slug} | {d.rel_path} | {d.metodo} | {d.estado} | "
            f"{d.chars} | {'sí' if d.ocr else '—'} | {d.nota} |"
        )
    dudosos = [d for d in filas if d.estado != "ok"]
    lineas += ["", f"**{len(dudosos)} de {len(filas)} documentos requieren tu revisión.**", ""]
    return "\n".join(lineas) + "\n"


_ZONAS_VETADAS = ("00_Input", "90_Notas personales")


def destino_seguro(dst: Path, case_dir: Path) -> Path:
    """Devuelve dst si es un destino de escritura permitido; si no, ValueError.

    Invariante del proyecto (M5): jamás escribir en 00_Input/ ni en
    90_Notas personales/. Se comprueba por los componentes de la ruta relativa.
    """
    dst = Path(dst)
    try:
        partes = dst.relative_to(case_dir).parts
    except ValueError:
        raise ValueError(f"Destino fuera del caso: {dst}")
    if partes and partes[0] in _ZONAS_VETADAS:
        raise ValueError(f"Destino en zona vetada {partes[0]!r}: {dst}")
    return dst


def _sala_maquina_dir(case_dir: Path) -> Path:
    return case_dir / "01_Procesado" / "02_Sala de máquina"


def _escribir_md(case_dir, case_id, slug, rel_path, texto, metodo, ocr, estado):
    sm_dir = _sala_maquina_dir(case_dir)
    md_path = destino_seguro(sm_dir / "03_MD" / f"{slug}.md", case_dir)
    raw_path = destino_seguro(sm_dir / "raw_text" / f"{slug}.txt", case_dir)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(texto, encoding="utf-8")
    meta = {
        "case_id": case_id, "tipo": "documento_procesado", "fase": "01_Procesado",
        "fecha": now_iso(), "source_path": rel_path, "extractor": metodo,
        "chars": len(texto), "ocr": ocr, "ocr_quality": estado,
        "text_sha256": text_sha256(texto),
    }
    write_md(md_path, meta, texto)


def ejecutar(case_dir: Path, plan: list[DocPlan], *, case_id: str,
             vision: bool = False) -> list[DocCobertura]:
    """Recorre el plan escribiendo 01_OCR/, raw_text/, 03_MD/. Devuelve cobertura.

    Rutas PDF (F1): pypdf si hay capa de texto suficiente; si no, OCRmyPDF →
    PDF buscable persistido en 01_OCR/ → texto del PDF buscable → MD.
    imagen/nativo se implementan en F2 (aquí producen 'sin_soporte' provisional).
    """
    case_dir = Path(case_dir)
    sm_dir = _sala_maquina_dir(case_dir)
    cobertura: list[DocCobertura] = []

    for d in plan:
        if d.skip:
            continue
        src = case_dir / "00_Input" / d.rel_path
        if d.ruta == "pdf":
            texto = _try_pypdf(src) or ""
            npags = _pdf_num_paginas(src)
            if texto and _texto_suficiente(texto, npags):
                estado, nota = ocr_quality(texto, npags)
                _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, "pypdf", False, estado)
                cobertura.append(DocCobertura(d.slug, d.rel_path, "pypdf", estado, len(texto), False, nota))
                continue
            # escaneado → OCRmyPDF (sin tope de páginas)
            ocr_out = destino_seguro(sm_dir / "01_OCR" / f"{d.slug}.pdf", case_dir)
            try:
                buscable = ocr_pdf(src, ocr_out)
            except Exception as e:  # OCRError incl. cifrado/corrupto/firmado
                cobertura.append(DocCobertura(d.slug, d.rel_path, "ocr", "empty", 0, True, f"OCR falló: {e}"))
                continue
            texto = _try_pypdf(buscable) or ""
            estado, nota = ocr_quality(texto, _pdf_num_paginas(buscable))
            _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, "ocr", True, estado)
            cobertura.append(DocCobertura(d.slug, d.rel_path, "ocr", estado, len(texto), True, nota))
        else:
            # imagen/nativo/sin_soporte → F2
            cobertura.append(DocCobertura(d.slug, d.rel_path, "sin_soporte", "sin_soporte", 0, False, "ruta F2"))
    return cobertura
