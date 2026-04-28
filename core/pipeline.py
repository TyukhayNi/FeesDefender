"""Orquestador del pipeline.

Ejecuta los pasos en orden y deja en `07_AI cowork/_pipeline_log.md` un
resumen estructurado de cada ejecución (paso, resultado, errores recoverables).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import case_manager, demanda_generator, extractor, inventory, linker
from . import markdown_generator, scorer, sync, viability
from .config import caso_path
from .utils import now_iso, write_md


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str = ""
    artifact: str | None = None


@dataclass
class PipelineRun:
    case_id: str
    started_at: str = field(default_factory=now_iso)
    finished_at: str | None = None
    steps: list[StepResult] = field(default_factory=list)


def _safe(name: str, fn: Callable[[], str | None]) -> StepResult:
    try:
        artifact = fn()
        return StepResult(name=name, ok=True, artifact=str(artifact) if artifact else None)
    except Exception as exc:  # noqa: BLE001
        return StepResult(name=name, ok=False, detail=f"{type(exc).__name__}: {exc}")


def run(
    case_id: str,
    *,
    drive_remote_path: str | None = None,
    do_sync: bool = True,
    do_demanda: bool = True,
) -> PipelineRun:
    pr = PipelineRun(case_id=case_id)

    pr.steps.append(_safe(
        "ensure_case",
        lambda: case_manager.ensure_case(case_id, drive_remote_path=drive_remote_path),
    ))

    if do_sync and drive_remote_path:
        pr.steps.append(_safe(
            "sync.pull",
            lambda: sync.pull(case_id, remote_path=drive_remote_path).bytes_copied,
        ))
    else:
        pr.steps.append(StepResult("sync.pull", ok=True, detail="omitido"))

    pr.steps.append(_safe("inventory.scan", lambda: inventory.scan(case_id)))
    pr.steps.append(_safe(
        "extractor.extract_all",
        lambda: f"{len(extractor.extract_all(case_id))} archivos",
    ))

    def _markdown_step() -> str:
        results = extractor.extract_all(case_id)
        markdown_generator.build(case_id, results)
        return f"{len(results)} .md"

    pr.steps.append(_safe("markdown_generator.build", _markdown_step))
    pr.steps.append(_safe("scorer.score", lambda: scorer.score(case_id)))
    pr.steps.append(_safe("viability.analyze", lambda: viability.analyze(case_id)))

    if do_demanda:
        pr.steps.append(_safe("demanda.draft", lambda: demanda_generator.draft_demanda(case_id)))

    pr.steps.append(_safe("linker.crosslink", lambda: f"{linker.crosslink(case_id)} archivos modificados"))

    pr.finished_at = now_iso()
    _write_log(pr)
    return pr


def _write_log(pr: PipelineRun) -> Path:
    log_dir = caso_path(pr.case_id) / "07_AI cowork"
    log_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Ejecución de pipeline — {pr.started_at}",
        "",
        f"- Caso: `{pr.case_id}`",
        f"- Inicio: {pr.started_at}",
        f"- Fin: {pr.finished_at}",
        "",
        "| Paso | OK | Detalle |",
        "|---|---|---|",
    ]
    for s in pr.steps:
        ok = "✅" if s.ok else "❌"
        detail = s.detail or s.artifact or ""
        lines.append(f"| `{s.name}` | {ok} | {detail} |")
    fm = {"case_id": pr.case_id, "tipo": "pipeline_log", "fase": "07_AI cowork", "fecha": pr.started_at}
    return write_md(log_dir / "_pipeline_log.md", fm, "\n".join(lines))
