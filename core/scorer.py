"""Scoring de relevancia probatoria.

Tres modos (configurables por `SCORING_MODE`):
  - heuristic: keyword matching + ponderación por tipo de documento
  - llm:       prompt al LLM local por documento
  - hybrid:    heurística como prefiltro + LLM solo sobre top 2*K

Salidas:
  - `02_Analisis/scoring.md`         (tabla razonada)
  - `02_Analisis/documentos_top.md`  (los K más relevantes con enlaces)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import caso_path, settings
from .llm import LLMError, run_prompt
from .utils import now_iso, read_md, slugify, write_md

# Términos clave del dominio "honorarios de intermediación inmobiliaria".
# El sistema está diseñado para extenderse a otros dominios sustituyendo este
# diccionario por uno cargado dinámicamente.
KEYWORD_WEIGHTS: dict[str, float] = {
    "encargo": 3.0,
    "exclusiva": 3.5,
    "intermediación": 4.0,
    "intermediacion": 4.0,
    "honorarios": 5.0,
    "comisión": 4.0,
    "comision": 4.0,
    "compraventa": 3.0,
    "reserva": 2.5,
    "señal": 2.0,
    "arras": 3.0,
    "vendedor": 2.0,
    "comprador": 2.0,
    "engel": 2.0,
    "völkers": 2.0,
    "volkers": 2.0,
    "nota de encargo": 5.0,
    "hoja de visita": 4.0,
    "factura": 3.0,
    "burofax": 2.5,
    "requerimiento": 2.5,
    "whatsapp": 1.5,
    "correo": 1.0,
    "email": 1.0,
}


@dataclass
class DocScore:
    md_path: Path
    rel_source: str
    score: float
    reasons: list[str]


_WORD_RE = re.compile(r"\b[\w'\-áéíóúüñç]+\b", flags=re.IGNORECASE)


def _heuristic_score(text: str) -> tuple[float, list[str]]:
    text_lower = text.lower()
    score = 0.0
    reasons: list[str] = []
    for term, weight in KEYWORD_WEIGHTS.items():
        n = text_lower.count(term)
        if n:
            score += n * weight
            reasons.append(f"`{term}` ×{n}")
    # Penalización suave para documentos muy cortos
    if len(text) < 600:
        score *= 0.8
        reasons.append("texto corto (×0.8)")
    return round(score, 2), reasons


def _llm_score(case_id: str, md_path: Path, text: str) -> tuple[float, list[str]]:
    try:
        resp = run_prompt(
            "scoring",
            case_id=case_id,
            documento=md_path.name,
            texto=text[:6000],
        )
    except LLMError as exc:
        return 0.0, [f"llm_error: {exc}"]
    # Espera primera línea: "score: X.X"; resto: razones
    score = 0.0
    reasons: list[str] = []
    for line in resp.text.splitlines():
        line = line.strip()
        if line.lower().startswith("score:"):
            try:
                score = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("-"):
            reasons.append(line.lstrip("- ").strip())
    return score, reasons or [resp.text[:200]]


def _iter_processed(case_id: str):
    proc = caso_path(case_id) / "01_Procesado" / "MD"
    for md in sorted(proc.glob("*.md")):
        meta, body = read_md(md)
        if meta.get("tipo") != "documento_procesado":
            continue
        yield md, meta, body


def score(case_id: str, *, mode: str | None = None, top_k: int | None = None) -> Path:
    mode = (mode or settings.scoring_mode).lower()
    top_k = top_k or settings.scoring_top_k

    docs: list[DocScore] = []
    for md, meta, body in _iter_processed(case_id):
        if mode == "heuristic":
            s, reasons = _heuristic_score(body)
        elif mode == "llm":
            s, reasons = _llm_score(case_id, md, body)
        else:  # hybrid
            s, reasons = _heuristic_score(body)
            # afinamos los más prometedores con LLM
            if s > 0:
                ls, lreasons = _llm_score(case_id, md, body)
                s = round(0.5 * s + 0.5 * ls, 2)
                reasons.extend(f"llm: {r}" for r in lreasons)
        docs.append(DocScore(md, meta.get("source_path", md.name), s, reasons))

    docs.sort(key=lambda d: d.score, reverse=True)

    # scoring.md (tabla razonada completa)
    out_dir = caso_path(case_id) / "02_Analisis"
    out_dir.mkdir(parents=True, exist_ok=True)

    table_lines = ["| # | Documento | Score | Motivos |", "|---|---|---|---|"]
    for i, d in enumerate(docs, 1):
        link = f"[[{d.md_path.stem}]]"
        reasons = "; ".join(d.reasons[:5]) or "—"
        table_lines.append(f"| {i} | {link} `{d.rel_source}` | {d.score} | {reasons} |")

    fm = {
        "case_id": case_id,
        "tipo": "scoring",
        "fase": "02_Analisis",
        "fecha": now_iso(),
        "modo": mode,
        "top_k": top_k,
        "n_docs": len(docs),
    }
    body = "# Scoring de relevancia\n\n" + "\n".join(table_lines)
    scoring_md = write_md(out_dir / "scoring.md", fm, body)

    # documentos_top.md
    top = docs[:top_k]
    top_lines = [f"# Documentos top {top_k}", ""]
    for i, d in enumerate(top, 1):
        top_lines.append(
            f"{i}. [[{d.md_path.stem}]] — score **{d.score}** "
            f"(`{d.rel_source}`)"
        )
    write_md(
        out_dir / "documentos_top.md",
        {**fm, "tipo": "documentos_top"},
        "\n".join(top_lines),
    )

    return scoring_md
