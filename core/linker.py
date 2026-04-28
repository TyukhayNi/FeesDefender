"""Generación de enlaces `[[wikilink]]` entre los `.md` del caso.

Política: enlazamos por nombre de stem cuando aparece como token aislado en el
cuerpo del documento. No reescribimos enlaces ya presentes. Idempotente.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import caso_path
from .utils import build_frontmatter, now_iso, read_md


def _all_md(case_dir: Path) -> list[Path]:
    out: list[Path] = []
    for sub in ("00_Input", "01_Procesado", "02_Analisis", "03_Decision",
                "04_Output predemanda", "05_Procedimiento", "06_Anonimizado", "07_AI cowork"):
        d = case_dir / sub
        if d.exists():
            out.extend(sorted(d.rglob("*.md")))
    return out


def _link_pattern(stem: str) -> re.Pattern[str]:
    # Match the stem as a whole token, not already inside [[...]]
    return re.compile(
        rf"(?<!\[\[)(?<!\w)({re.escape(stem)})(?!\w)(?!\]\])",
        flags=re.IGNORECASE,
    )


def crosslink(case_id: str) -> int:
    case_dir = caso_path(case_id)
    files = _all_md(case_dir)
    stems = sorted({p.stem for p in files}, key=len, reverse=True)

    edits = 0
    for path in files:
        meta, body = read_md(path)
        original = body
        for stem in stems:
            if path.stem == stem:
                continue
            if len(stem) < 5:  # evita enlazar palabras demasiado genéricas
                continue
            body = _link_pattern(stem).sub(rf"[[{stem}]]", body, count=3)
        if body != original:
            edits += 1
            meta["linker_updated_at"] = now_iso()
            path.write_text(build_frontmatter(meta) + "\n" + body.strip() + "\n", encoding="utf-8")
    return edits
