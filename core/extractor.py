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
EXTRACTOR_VERSION = 1

_STATE_FILENAME = "_extract_state.json"


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

def _try_docling(path: Path) -> str | None:
    try:
        from docling.document_converter import DocumentConverter  # type: ignore
    except Exception:
        return None
    try:
        conv = DocumentConverter()
        result = conv.convert(str(path))
        return result.document.export_to_markdown()
    except Exception:
        return None


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

    if ext in {".pdf", ".docx", ".html", ".htm", ".pptx"}:
        if (text := _try_docling(path)):
            return text, "docling"

    if ext == ".pdf":
        if (text := _try_pypdf(path)):
            return text, "pypdf"

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

    _save_state(state_path, new_state)
    return results
