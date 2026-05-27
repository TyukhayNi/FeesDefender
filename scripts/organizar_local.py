"""CLI: organiza localmente los documentos del Drive E&V de un caso.

Clasifica con un LLM local (Ollama) los documentos en bruto de
``00_Input/01_Drive EV/`` y produce una vista navegable en ``_organizado/``.

Uso:
  # 1) Proponer (no toca _organizado/). Revisa luego 07_AI cowork/_plan_reorganizacion.md
  python -m scripts.organizar_local "BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta" --plan

  # 2) Materializar la vista desde el plan (posiblemente editado a mano)
  python -m scripts.organizar_local "BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta" --execute

  # Otros: --dry-run, --refresh, --rebuild, --renumerar

Requiere Ollama corriendo (`ollama serve`) y el modelo descargado
(`ollama pull qwen2.5:14b-instruct-q4_K_M`). No hay fallback a APIs externas:
los originales con PII nunca salen del entorno local del despacho.
"""

from __future__ import annotations

import json

import typer

from core import local_organizer as org

app = typer.Typer(
    add_completion=False,
    help="Organiza localmente los documentos del Drive E&V (clasificación con Ollama).",
)


@app.command()
def main(
    case_id: str = typer.Argument(..., help="ID del caso (formato CRM)."),
    plan: bool = typer.Option(False, "--plan", help="Clasifica y escribe la propuesta editable."),
    execute: bool = typer.Option(False, "--execute", help="Materializa la vista desde el plan editado."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Como --execute pero sin escribir nada."),
    refresh: bool = typer.Option(False, "--refresh", help="Clasifica solo documentos nuevos (por SHA)."),
    rebuild: bool = typer.Option(False, "--rebuild", help="Borra _organizado/ y rehace desde cero."),
    renumerar: bool = typer.Option(False, "--renumerar", help="Reasigna prefijos NN en orden actualizado."),
) -> None:
    modos = [plan, execute, dry_run, refresh, rebuild, renumerar]
    if sum(bool(m) for m in modos) != 1:
        typer.echo("Indica exactamente un modo: --plan | --execute | --dry-run | --refresh | --rebuild | --renumerar")
        raise typer.Exit(2)

    try:
        if plan:
            res = org.planificar(case_id)
        elif execute:
            res = org.ejecutar_plan(case_id)
        elif dry_run:
            res = org.ejecutar_plan(case_id, dry_run=True)
        elif refresh:
            res = org.refrescar(case_id)
        elif rebuild:
            res = org.reconstruir(case_id)
        else:
            res = org.renumerar(case_id)
    except org.OrganizadorError as exc:
        typer.echo(f"✗ {exc}")
        raise typer.Exit(1)

    typer.echo(json.dumps(res, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    app()
