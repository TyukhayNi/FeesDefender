"""Generación del borrador de demanda.

Lee `viabilidad.md`, `hechos_atomicos.md`, `prueba_indexada.md` y
`contradicciones.md`, los pasa al prompt `demanda` y escribe
`04_OUTPUT_PREDEMANDA/demanda.md`. También genera, si procede,
`requerimiento_previo.md` con el prompt `requerimiento`.
"""

from __future__ import annotations

from pathlib import Path

from .config import caso_path
from .llm import LLMError, run_prompt
from .utils import now_iso, read_md, write_md

_INPUTS = [
    ("viabilidad", "03_DECISION/viabilidad.md"),
    ("hechos_atomicos", "02_ANALISIS/hechos_atomicos.md"),
    ("prueba_indexada", "02_ANALISIS/prueba_indexada.md"),
    ("contradicciones", "02_ANALISIS/contradicciones.md"),
]


def _load_context(case_id: str) -> str:
    base = caso_path(case_id)
    parts: list[str] = []
    for tag, rel in _INPUTS:
        p = base / rel
        if not p.exists():
            continue
        _, body = read_md(p)
        parts.append(f"## {tag}\n\n{body.strip()}\n")
    if not parts:
        raise FileNotFoundError(
            "Faltan análisis previos. Ejecuta primero el pipeline hasta `viability`."
        )
    return "\n\n".join(parts)


def _generate(case_id: str, prompt_id: str, filename: str, fase: str) -> Path:
    contexto = _load_context(case_id)
    out_dir = caso_path(case_id) / fase
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        resp = run_prompt(prompt_id, case_id=case_id, contexto=contexto)
        body = resp.text
        model = resp.model
        prompt_hash = resp.prompt_hash
    except LLMError as exc:
        body = f"_LLM no disponible:_ {exc}"
        model = "n/a"
        prompt_hash = "n/a"

    fm = {
        "case_id": case_id,
        "tipo": prompt_id,
        "fase": fase,
        "fecha": now_iso(),
        "model": model,
        "prompt_id": prompt_id,
        "prompt_hash": prompt_hash,
    }
    return write_md(out_dir / filename, fm, body)


def draft_demanda(case_id: str) -> Path:
    return _generate(case_id, "demanda", "demanda.md", "04_OUTPUT_PREDEMANDA")


def draft_requerimiento(case_id: str) -> Path:
    return _generate(case_id, "requerimiento", "requerimiento_previo.md", "04_OUTPUT_PREDEMANDA")
