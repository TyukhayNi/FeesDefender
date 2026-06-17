"""Conversión del texto extraído a `.md` con frontmatter trazable.

Por cada archivo procesado escribe `01_Procesado/MD/{slug}.md`. El frontmatter
incluye la procedencia (`source_path`), el `extractor` usado y un resumen
cuantitativo (`chars`, `tokens_estim`).
"""

from __future__ import annotations

from pathlib import Path

from .config import caso_path
from .extractor import ExtractionResult
from .utils import now_iso, slugify, text_sha256, write_md


def _estimate_tokens(text: str) -> int:
    # heurística rápida sin tokenizer dependiente
    return max(1, len(text) // 4)


def build(
    case_id: str, results: list[ExtractionResult], *, force: bool = False
) -> list[Path]:
    out_dir = caso_path(case_id) / "01_Procesado" / "MD"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for r in results:
        slug = slugify(Path(r.rel_path).stem)
        out = out_dir / f"{slug}.md"
        # Skip incremental: si la extracción reutilizó el .txt (no cambió) y
        # el .md ya existe, no se regenera.
        if not force and r.skipped and out.exists():
            paths.append(out)
            continue
        text = r.output_path.read_text(encoding="utf-8")
        meta = {
            "case_id": case_id,
            "tipo": "documento_procesado",
            "fase": "01_Procesado",
            "fecha": now_iso(),
            "source_path": r.rel_path,
            "extractor": r.method,
            "chars": r.chars,
            "tokens_estim": _estimate_tokens(text),
            "sha256_text": text_sha256(text),
        }
        body = (
            f"# {Path(r.rel_path).name}\n\n"
            f"> Texto extraído de `{r.rel_path}` mediante `{r.method}`.\n\n"
            f"---\n\n"
            f"{text.strip()}\n"
        )
        write_md(out, meta, body)
        paths.append(out)

    return paths
