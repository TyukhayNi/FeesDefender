"""Análisis de viabilidad de la reclamación.

Lee el `documentos_top.md`, concatena los `.md` referenciados (limitando tokens
estimados), llama al prompt `viabilidad` y escribe `03_Decision/viabilidad.md`.
También extrae hechos atómicos y contradicciones en archivos separados.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import caso_path
from .llm import LLMError, run_prompt
from .utils import now_iso, read_md, write_md

_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_MAX_CONTEXT_CHARS = 18_000  # margen prudente para llama3 8k contexto


def _gather_top_context(case_id: str) -> tuple[str, list[str]]:
    top_path = caso_path(case_id) / "02_Analisis" / "documentos_top.md"
    if not top_path.exists():
        return "", []
    _, body = read_md(top_path)
    slugs = _LINK_RE.findall(body)
    proc_dir = caso_path(case_id) / "01_Procesado" / "MD"

    chunks: list[str] = []
    used: list[str] = []
    total = 0
    for slug in slugs:
        md = proc_dir / f"{slug}.md"
        if not md.exists():
            continue
        _, content = read_md(md)
        snippet = f"\n\n## {slug}\n\n{content.strip()}\n"
        if total + len(snippet) > _MAX_CONTEXT_CHARS:
            break
        chunks.append(snippet)
        used.append(slug)
        total += len(snippet)

    return "".join(chunks), used


def _run_and_save(case_id: str, prompt_id: str, filename: str, fase: str, contexto: str, used: list[str]) -> Path:
    out_dir = caso_path(case_id) / fase
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        resp = run_prompt(prompt_id, case_id=case_id, contexto=contexto)
        body = resp.text
        model = resp.model
        prompt_hash = resp.prompt_hash
    except LLMError as exc:
        body = f"_LLM no disponible:_ {exc}\n\nContexto considerado:\n\n" + contexto[:1500]
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
        "fuentes": used,
    }
    return write_md(out_dir / filename, fm, body)


def analyze(case_id: str) -> dict[str, Path]:
    contexto, used = _gather_top_context(case_id)
    if not contexto:
        raise FileNotFoundError(
            "No hay 02_Analisis/documentos_top.md. Ejecuta antes el scoring."
        )

    return {
        "viabilidad": _run_and_save(case_id, "viabilidad", "viabilidad.md", "03_Decision", contexto, used),
        "hechos_atomicos": _run_and_save(case_id, "hechos_atomicos", "hechos_atomicos.md", "02_Analisis", contexto, used),
        "contradicciones": _run_and_save(case_id, "contradicciones", "contradicciones.md", "02_Analisis", contexto, used),
        "prueba_indexada": _run_and_save(case_id, "prueba_indexada", "prueba_indexada.md", "02_Analisis", contexto, used),
    }
