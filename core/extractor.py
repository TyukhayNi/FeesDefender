"""Extracción de texto a partir de los archivos de `00_Input/`.

Estrategia de extracción por extensión:
  - .pdf, .docx, .html, .pptx → Docling (cuando está disponible)
  - .pdf fallback             → pypdf
  - .docx fallback            → python-docx
  - .txt, .md                 → lectura plana (con detección de encoding)
  - .csv, .xlsx               → pandas → CSV plano
  - .eml                      → email.message_from_binary_file

Cada extracción produce un archivo `01_Procesado/raw_text/{slug}.txt` con el
texto extraído. La fase siguiente (`markdown_generator`) lo envuelve en `.md`
con frontmatter.
"""

from __future__ import annotations

import gc
import json
from dataclasses import dataclass
from pathlib import Path

import chardet

from .config import caso_path
from .inventory import load as load_inventory
from .utils import slugify


# Versión lógica del extractor. Súbela cuando cambie la lógica de extracción
# (p. ej. el backend Docling) para invalidar el cache de skip incremental y
# forzar una reextracción de todos los documentos en la próxima corrida.
# v2: PDFs con capa de texto se extraen con pypdf (sin Docling/OCR) para evitar
#     el OOM/segfault de RapidOCR en PDFs largos (visto en BaRS1, Atles de
#     plànols.pdf, 128 págs). Docling/OCR solo para escaneados, con guarda de
#     nº de páginas.
EXTRACTOR_VERSION = 2

_STATE_FILENAME = "_extract_state.json"

# Nº máximo de páginas que se enviarán a Docling/OCR para un PDF escaneado.
# Por encima, se omite el OCR (se marca como sin texto) en lugar de arriesgar un
# OOM/segfault de RapidOCR. Los escaneados reales del flujo son cortos.
MAX_OCR_PAGINAS = 30


class ExtractionError(RuntimeError):
    pass


@dataclass
class ExtractionResult:
    rel_path: str
    output_path: Path
    chars: int
    method: str
    skipped: bool = False  # True si se reutilizó el .txt previo (no se reextrajo)


# --- Backends opcionales ----------------------------------------------------

def _docling_converter():
    """``DocumentConverter`` con el modelo de estructura de tablas DESACTIVADO.

    El modelo TableFormer de Docling es el componente más pesado en memoria y,
    en equipos con poca RAM libre, provoca OOM y mata el proceso (visto en el
    exp. 444: ``Unable to allocate ... Stage table failed``). Desactivar
    ``do_table_structure`` **no pierde el texto** de las tablas —se sigue
    capturando vía OCR/texto—, solo deja de reconstruir la rejilla de celdas en
    markdown, irrelevante para la anonimización y el análisis. Reduce
    drásticamente el pico de memoria.
    """
    from docling.datamodel.base_models import InputFormat  # type: ignore
    from docling.datamodel.pipeline_options import PdfPipelineOptions  # type: ignore
    from docling.document_converter import (  # type: ignore
        DocumentConverter,
        PdfFormatOption,
    )

    opts = PdfPipelineOptions()
    opts.do_table_structure = False
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )


def _try_docling(path: Path) -> str | None:
    try:
        conv = _docling_converter()
    except Exception:
        return None
    try:
        result = conv.convert(str(path))
        return result.document.export_to_markdown()
    except Exception:
        return None
    finally:
        # Liberar modelos/imágenes entre documentos: en equipos con poca RAM la
        # acumulación entre docs es lo que termina disparando el OOM.
        del conv
        gc.collect()


def _try_pypdf(path: Path) -> str | None:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return None
    try:
        reader = PdfReader(str(path))
        return "\n\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return None


def _pdf_num_paginas(path: Path) -> int | None:
    """Nº de páginas de un PDF (pypdf). None si no se puede leer."""
    try:
        from pypdf import PdfReader  # type: ignore
        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def _texto_suficiente(text: str | None, n_pags: int | None) -> bool:
    """¿La capa de texto de pypdf basta (PDF con texto, no escaneado)?

    Heurística conservadora: al menos 100 caracteres y, si se conoce el nº de
    páginas, una densidad mínima (~40 char/pág) que descarta los PDFs escaneados
    (capa de texto vacía o residual) sin descartar PDFs de texto reales.
    """
    t = (text or "").strip()
    if len(t) < 100:
        return False
    if n_pags and n_pags > 0:
        return (len(t) / n_pags) >= 40
    return True


def _try_docx(path: Path) -> str | None:
    try:
        import docx  # type: ignore
    except Exception:
        return None
    try:
        d = docx.Document(str(path))
        return "\n".join(p.text for p in d.paragraphs)
    except Exception:
        return None


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    enc = chardet.detect(raw).get("encoding") or "utf-8"
    return raw.decode(enc, errors="replace")


def _try_pandas_table(path: Path) -> str | None:
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return None
    try:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
        return df.to_csv(index=False)
    except Exception:
        return None


def _try_email(path: Path) -> str | None:
    try:
        import email  # std lib
        from email import policy
    except Exception:
        return None
    try:
        with path.open("rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
        parts = [
            f"De: {msg.get('From')}",
            f"Para: {msg.get('To')}",
            f"Fecha: {msg.get('Date')}",
            f"Asunto: {msg.get('Subject')}",
            "",
        ]
        body = msg.get_body(preferencelist=("plain", "html"))
        if body is not None:
            parts.append(body.get_content())
        return "\n".join(parts)
    except Exception:
        return None


# --- Orquestador ------------------------------------------------------------

def _extract_one(path: Path) -> tuple[str, str]:
    ext = path.suffix.lower()

    if ext == ".pdf":
        # pypdf primero: si el PDF trae capa de texto suficiente, se usa y se
        # EVITA Docling/OCR (cuyo RapidOCR revienta con bad_alloc/segfault en
        # PDFs largos — no es excepción Python, mata el proceso). Solo se OCR-iza
        # lo escaneado (capa de texto vacía/residual), y con guarda de páginas.
        pytext = _try_pypdf(path)
        npags = _pdf_num_paginas(path)
        if pytext and _texto_suficiente(pytext, npags):
            return pytext, "pypdf"
        if npags is None or npags <= MAX_OCR_PAGINAS:
            if (text := _try_docling(path)):
                return text, "docling"
        # Escaneado demasiado largo para OCR seguro, o Docling no disponible:
        # devolver lo que diera pypdf (aunque sea poco); si nada, marcar vacío.
        if pytext:
            return pytext, "pypdf"
        return "", "sin_texto"

    if ext in {".docx", ".html", ".htm", ".pptx"}:
        if (text := _try_docling(path)):
            return text, "docling"

    if ext == ".docx":
        if (text := _try_docx(path)):
            return text, "python-docx"

    if ext in {".txt", ".md", ".html", ".htm"}:
        return _read_text_file(path), "raw"

    if ext in {".csv", ".xlsx", ".xls"}:
        if (text := _try_pandas_table(path)) is not None:
            return text, "pandas"

    if ext in {".eml", ".msg"}:
        if (text := _try_email(path)):
            return text, "email"

    raise ExtractionError(f"No hay extractor disponible para {path.name} ({ext})")


def _load_state(state_path: Path) -> dict:
    """Estado de extracción previo, por `rel_path`. Vacío si no existe o si
    la versión del extractor cambió (invalida todo el cache)."""
    if not state_path.exists():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if data.get("extractor_version") != EXTRACTOR_VERSION:
        return {}
    return data.get("files", {})


def _save_state(state_path: Path, files: dict) -> None:
    payload = {"extractor_version": EXTRACTOR_VERSION, "files": files}
    state_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def extract_all(case_id: str, *, force: bool = False) -> list[ExtractionResult]:
    """Extrae el texto de los archivos de `00_Input/` a `01_Procesado/raw_text/`.

    Skip incremental: si el hash del origen no cambió desde la última
    extracción (y la versión del extractor es la misma), reutiliza el `.txt`
    ya generado en lugar de reextraer —el OCR vía Docling es el paso caro—.
    `force=True` ignora el skip y reextrae todo.

    Cada `ExtractionResult` lleva `skipped=True` cuando se reutilizó el `.txt`
    previo, para que el paso de markdown solo regenere lo realmente reextraído.
    """
    inv = load_inventory(case_id)
    case_dir = caso_path(case_id)
    out_dir = case_dir / "01_Procesado" / "raw_text"
    out_dir.mkdir(parents=True, exist_ok=True)

    state_path = out_dir / _STATE_FILENAME
    prev = {} if force else _load_state(state_path)

    input_dir = case_dir / "00_Input"
    results: list[ExtractionResult] = []
    new_state: dict = {}

    for f in inv["files"]:
        rel = f["rel_path"]
        src = input_dir / rel
        if not src.exists():
            continue
        slug = slugify(Path(rel).stem)
        out = out_dir / f"{slug}.txt"
        src_sha = f.get("sha256", "")

        cached = prev.get(rel)
        if (
            not force
            and src_sha
            and cached is not None
            and cached.get("source_sha256") == src_sha
            and out.exists()
        ):
            results.append(ExtractionResult(
                rel_path=rel,
                output_path=out,
                chars=cached.get("chars", 0),
                method=cached.get("method", "cache"),
                skipped=True,
            ))
            new_state[rel] = cached
            _save_state(state_path, new_state)
            continue

        try:
            text, method = _extract_one(src)
        except ExtractionError:
            continue
        out.write_text(text, encoding="utf-8")
        results.append(ExtractionResult(
            rel_path=rel,
            output_path=out,
            chars=len(text),
            method=method,
            skipped=False,
        ))
        new_state[rel] = {
            "source_sha256": src_sha,
            "method": method,
            "chars": len(text),
        }
        # Persistir el estado tras CADA documento: el OCR es caro y el proceso
        # puede morir (OOM en equipos con poca RAM). Guardar incrementalmente
        # hace la extracción reanudable —un relanzamiento salta lo ya hecho en
        # lugar de empezar de cero—. El fichero de estado es pequeño; el coste
        # de reescribirlo por doc es despreciable frente al del OCR.
        _save_state(state_path, new_state)

    _save_state(state_path, new_state)
    return results
