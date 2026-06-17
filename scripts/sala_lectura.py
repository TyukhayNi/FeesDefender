"""CLI de la sala de lectura (F4-F6). Disparo: clasificar/aplicar/render/poblar/organizar."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import typer  # noqa: E402

from core import sala_lectura  # noqa: E402

app = typer.Typer(help="Organiza la sala de lectura de 01_Procesado.")


@app.command()
def clasificar(case: str = typer.Option(..., "--case")):
    r = sala_lectura.clasificar_caso(case)
    typer.echo(f"Deterministas: {r['n_deterministas']} | Residuo: {r['n_residuo']}")
    if r["n_residuo"]:
        typer.echo(
            f"Rellena la worklist y corre 'aplicar': "
            f"01_Procesado/_revisar/{sala_lectura.WORKLIST_NAME}"
        )


@app.command()
def aplicar(case: str = typer.Option(..., "--case")):
    r = sala_lectura.aplicar_clasificacion(case)
    typer.echo(f"Aplicadas: {r['n_aplicadas']}")


@app.command()
def render(case: str = typer.Option(..., "--case")):
    paths = sala_lectura.render_indices(case)
    typer.echo("Generado: " + ", ".join(p.name for p in paths))


@app.command()
def poblar(case: str = typer.Option(..., "--case")):
    r = sala_lectura.poblar_sala_lectura(case)
    typer.echo(f"Acciones: {r['acciones']}")


@app.command()
def organizar(case: str = typer.Option(..., "--case")):
    r = sala_lectura.organizar(case)
    if r["detenido_por_residuo"]:
        typer.echo(
            f"Detenido: {r['n_residuo']} doc(s) en revision. "
            f"Rellena la worklist y vuelve a correr 'organizar'."
        )
    else:
        typer.echo(f"Sala de lectura organizada. Acciones: {r['acciones']}")


if __name__ == "__main__":
    app()
