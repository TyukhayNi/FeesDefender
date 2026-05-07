"""CLI: ejecutar el pipeline completo sobre un caso.

Uso:
  python -m scripts.run_pipeline EV-2026-001 --drive gdrive:Casos/EV-2026-001
"""

from __future__ import annotations

import json

import typer

from core import pipeline

app = typer.Typer(add_completion=False, help="Ejecutar pipeline sobre un caso")


@app.command()
def main(
    case_id: str = typer.Argument(...),
    drive: str = typer.Option(None, "--drive"),
    sync: bool = typer.Option(True, "--sync/--no-sync"),
    demanda: bool = typer.Option(True, "--demanda/--no-demanda"),
    anonimizar: bool = typer.Option(False, "--anonimizar/--no-anonimizar"),
    politica_anon: str = typer.Option("SALTAR", "--politica-anon",
                                       help="SALTAR | REPROCESAR"),
) -> None:
    pr = pipeline.run(
        case_id,
        drive_remote_path=drive,
        do_sync=sync,
        do_demanda=demanda,
        do_anonimizar=anonimizar,
        politica_anonimizar=politica_anon,
    )
    summary = {
        "case_id": pr.case_id,
        "started_at": pr.started_at,
        "finished_at": pr.finished_at,
        "steps": [
            {"name": s.name, "ok": s.ok, "detail": s.detail, "artifact": s.artifact}
            for s in pr.steps
        ],
    }
    typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
