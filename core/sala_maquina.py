"""Cerebro + orquestador de la Sala de máquina (skill organizar-sala-maquina).

Convierte el crudo de 00_Input/ en 01_Procesado/02_Sala de máquina/:
  01_OCR/     PDFs buscables (OCRmyPDF)   03_MD/  markdown legible   raw_text/  intermedio

NO usa pipeline.run() ni la rama Docling/30pp de extractor. OCR aguas arriba con
OCRmyPDF (sin tope de páginas); reutiliza solo los helpers deterministas sanos del
extractor. Ver docs/superpowers/specs/2026-07-09-organizar-sala-maquina-design.md.
"""
from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from core.extractor import (
    _try_pypdf, _pdf_num_paginas, _texto_suficiente,
    _try_email, _try_rtf, _try_ics, _try_pandas_table, _try_docx, _read_text_file,
)
from core.anon.ocr import ocr_pdf
from core.anon.imagen_a_pdf import convertir as convertir_imagen
from core.utils import file_sha256, now_iso, output_slug, text_sha256, write_md

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
    metodo: str          # pypdf | ocr | nativo | sin_soporte | error
    estado: str          # ok | low | empty | sin_texto | sin_soporte
    chars: int = 0
    ocr: bool = False
    nota: str = ""
    sha256: str = ""     # sha del origen: cadena de custodia (spec §7/§10) + estado idempotente


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


def _celda(valor: str) -> str:
    """Sanea '|' para que no rompa el nº de columnas de una fila Markdown.

    Se sustituye por '/' en vez de escapar con '\\|': el escape depende de que
    el renderer de tablas Markdown lo respete, y cualquier parseo naive por
    '|' (incl. el de este propio módulo si algo relee `_cobertura.md`) seguiría
    contando una columna de más.
    """
    return str(valor).replace("|", "/")


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
            f"| {_celda(d.slug)} | {_celda(d.rel_path)} | {d.metodo} | {d.estado} | "
            f"{d.chars} | {'sí' if d.ocr else '—'} | {_celda(d.nota)} |"
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


_NATIVO_EXTRACTORES = {
    ".eml": _try_email,
    ".rtf": _try_rtf,
    ".ics": _try_ics,
    ".csv": _try_pandas_table,
    ".xlsx": _try_pandas_table,
    ".xls": _try_pandas_table,
    ".docx": _try_docx,
}
_NATIVO_TEXTO_PLANO = {".txt", ".md", ".html", ".htm"}


def _extraer_nativo(src: Path, ext: str) -> str:
    """Texto de un fichero nativo, por extensión (helpers SANOS de extractor).

    Nunca la rama Docling/30pp de `extractor._extract_one` (spec §5.1) — solo los
    `_try_*` deterministas y `_read_text_file` para texto plano.
    """
    e = ext.lower()
    if e in _NATIVO_TEXTO_PLANO:
        return _read_text_file(src)
    fn = _NATIVO_EXTRACTORES.get(e)
    if fn is None:
        return ""
    return fn(src) or ""


_VISION_RENDER_SCALE = 2   # factor de render pypdfium2 → ~144 dpi (72·2), legible para visión


def _renderizar_paginas(pdf_path: Path):
    """Renderiza cada página de un PDF a imagen PIL (para el refuerzo `--vision`)."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        return [pagina.render(scale=_VISION_RENDER_SCALE).to_pil() for pagina in doc]
    finally:
        doc.close()


def _transcribir_vision(imgs) -> str:
    """Punto de inyección del refuerzo `--vision` (Claude). Sin llamada real aquí:

    quien active `--vision` debe monkeypatchear esta función (test) o cablearla al
    modelo (CLI/skill) — nunca se llama a ningún modelo desde este módulo (spec §5,
    D3: off por defecto, sin llamadas reales embebidas en el cerebro).
    """
    raise NotImplementedError(
        "Refuerzo de vision no cableado: monkeypatchear sala_maquina._transcribir_vision"
    )


def _reforzar_con_vision(pdf_path: Path, texto: str, estado: str, nota: str) -> tuple[str, str, str]:
    """Si `estado` es dudoso, intenta mejorar `texto` con transcripción de visión.

    Nunca lanza: un fallo de render o de transcripción deja el documento tal cual
    (con nota) — el refuerzo es un extra opcional, no debe tumbar el documento
    (aislamiento por documento, spec §9).
    """
    try:
        imgs = _renderizar_paginas(pdf_path)
        extra = (_transcribir_vision(imgs) or "").strip()
    except Exception as e:
        motivo = f"refuerzo vision falló: {e}"
        return texto, estado, f"{nota} · {motivo}" if nota else motivo
    if not extra:
        return texto, estado, nota
    nuevo_texto = f"{texto}\n\n{extra}".strip() if texto.strip() else extra
    nuevo_estado, nuevo_nota = ocr_quality(nuevo_texto, _pdf_num_paginas(pdf_path))
    if nuevo_estado == "ok":
        return nuevo_texto, nuevo_estado, nuevo_nota or "reforzado con vision"
    # sigue dudoso tras el refuerzo: deja constancia de que SÍ se intentó visión
    # (si no, la cobertura no distingue "no se intentó" de "se intentó y no bastó").
    sufijo = "reforzado con vision, sigue dudoso"
    return nuevo_texto, nuevo_estado, f"{nuevo_nota} · {sufijo}" if nuevo_nota else sufijo


def _aplicar_vision(fuente_render: Path, texto: str, estado: str, nota: str,
                    vision: bool) -> tuple[str, str, str]:
    """Gate ÚNICO del refuerzo `--vision`: refuerza solo si está activado y el
    documento salió dudoso (`low`/`empty`). Usado por AMBOS caminos (OCR y
    pypdf-digital) para no duplicar la condición.
    """
    if vision and estado in ("low", "empty"):
        return _reforzar_con_vision(fuente_render, texto, estado, nota)
    return texto, estado, nota


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


def _ocr_y_extraer(case_dir: Path, sm_dir: Path, case_id: str, d: DocPlan,
                    entrada: Path, vision: bool) -> DocCobertura:
    """OCRmyPDF sobre `entrada` → PDF buscable persistido en 01_OCR/ → texto → MD.

    Compartido por el camino PDF escaneado y el camino imagen/`.heic` (ambos
    terminan en "aplícale OCR a un PDF"; solo cambia de dónde sale ese PDF).
    """
    ocr_out = destino_seguro(sm_dir / "01_OCR" / f"{d.slug}.pdf", case_dir)
    try:
        buscable = ocr_pdf(entrada, ocr_out)
    except Exception as e:  # OCRError incl. cifrado/corrupto/firmado
        return DocCobertura(d.slug, d.rel_path, "ocr", "empty", 0, True, f"OCR falló: {e}", d.sha256)
    texto = _try_pypdf(buscable) or ""
    estado, nota = ocr_quality(texto, _pdf_num_paginas(buscable))
    texto, estado, nota = _aplicar_vision(buscable, texto, estado, nota, vision)
    _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, "ocr", True, estado)
    return DocCobertura(d.slug, d.rel_path, "ocr", estado, len(texto), True, nota, d.sha256)


def ejecutar(case_dir: Path, docs: list[DocPlan], *, case_id: str,
             vision: bool = False) -> list[DocCobertura]:
    """Recorre el plan escribiendo 01_OCR/, raw_text/, 03_MD/. Devuelve cobertura.

    Rutas (spec §5): PDF con capa de texto → pypdf sin OCR; PDF escaneado o
    imagen/`.heic` → `imagen_a_pdf` (si aplica) → OCRmyPDF → PDF buscable
    persistido en 01_OCR/ → texto; nativo (`.eml`/`.docx`/`.txt`/...) → helpers
    deterministas de `extractor`, sin tocar 01_OCR/. `--vision` (opcional, off
    por defecto) refuerza `low`/`empty` renderizando páginas con pypdfium2.

    (`docs`, no `plan`: evita tapar la función pública `plan()` del módulo.)
    """
    case_dir = Path(case_dir)
    sm_dir = _sala_maquina_dir(case_dir)
    cobertura: list[DocCobertura] = []

    for d in docs:
        if d.skip:
            continue
        # spec §9: aislar el fallo por documento. Un error en uno (lock ~$ de
        # Office, disco lleno, PDF corrupto que revienta pypdf) se registra en
        # cobertura y NO aborta el lote — así apply() siempre llega a escribir
        # _cobertura.md, el estado y el evento de log.
        try:
            src = case_dir / "00_Input" / d.rel_path
            if d.ruta == "pdf":
                texto = _try_pypdf(src) or ""
                npags = _pdf_num_paginas(src)
                if texto and _texto_suficiente(texto, npags):
                    estado, nota = ocr_quality(texto, npags)
                    texto, estado, nota = _aplicar_vision(src, texto, estado, nota, vision)
                    _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, "pypdf", False, estado)
                    cobertura.append(DocCobertura(d.slug, d.rel_path, "pypdf", estado, len(texto), False, nota, d.sha256))
                    continue
                # escaneado → OCRmyPDF (sin tope de páginas)
                cobertura.append(_ocr_y_extraer(case_dir, sm_dir, case_id, d, src, vision))
            elif d.ruta == "imagen":
                # imagen/.heic → PDF intermedio (no persistido: solo el buscable
                # tras OCR va a 01_OCR/, spec §5) → mismo camino OCR que un escaneado.
                with tempfile.TemporaryDirectory() as tmp:
                    intermedio = Path(tmp) / f"{d.slug}__imagen.pdf"
                    try:
                        convertir_imagen(src, intermedio)
                    except Exception as e:  # Pillow/pillow-heif ausente, imagen corrupta...
                        cobertura.append(DocCobertura(
                            d.slug, d.rel_path, "sin_soporte", "sin_soporte", 0, False,
                            f"conversión a PDF falló: {e}", d.sha256))
                        continue
                    cobertura.append(_ocr_y_extraer(case_dir, sm_dir, case_id, d, intermedio, vision))
            elif d.ruta == "nativo":
                texto = _extraer_nativo(src, d.ext) or ""
                estado, nota = ocr_quality(texto, None)
                _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, "nativo", False, estado)
                cobertura.append(DocCobertura(d.slug, d.rel_path, "nativo", estado, len(texto), False, nota, d.sha256))
            else:
                cobertura.append(DocCobertura(d.slug, d.rel_path, "sin_soporte", "sin_soporte", 0, False, "sin soporte para esta extensión", d.sha256))
        except Exception as e:  # cualquier fallo del documento: no tumbar el lote
            cobertura.append(DocCobertura(d.slug, d.rel_path, "error", "empty", 0, False, f"fallo al procesar: {e}", d.sha256))
            continue
    return cobertura


_IGNORAR = {"_intake_log.jsonl", "_inventory.json", ".pulled", ".synced"}


def inventariar(case_dir: Path) -> list[dict]:
    """Lista 00_Input/ (recursivo) con sha256 y ext. Ignora ficheros de control.

    NO excluye 90_Notas personales aquí (lo hace plan(), único punto de verdad),
    pero sí los ficheros de control del intake.
    """
    root = Path(case_dir) / "00_Input"
    out: list[dict] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name in _IGNORAR:
            continue
        out.append({
            "rel_path": p.relative_to(root).as_posix(),
            "sha256": file_sha256(p),
            "ext": p.suffix.lower(),
        })
    return out
