"""CLI de la vista procesal de `05_Procedimiento` — pieza 4a (solo lectura).

    python -m scripts.procedimiento informe        --case "<case_id|W-code>" --expediente 540
    python -m scripts.procedimiento borrador-mapa  --case "<case_id|W-code>" --expediente 540

**Ninguno de los dos escribe en el expediente**, así que no se toma el mutex del caso: el
mutex lo pide quien escribe (`MEJORAS #126`), y aquí no escribe nadie. Lo que sí se exige
es la autorización del workspace —`READ_CASE`—, porque leer un caso prestado a otra
máquina sigue necesitando permiso.

`borrador-mapa` emite a `stdout`: redirígelo tú si quieres guardarlo. La herramienta no
deja el borrador dentro del caso a propósito — el mapa es del letrado y no se le sobrescribe.
"""
from __future__ import annotations

import typer

from core import procedimiento as proc
from core.casos.workspace_model import WorkspaceError
from core.procedimiento.mapa import MapaInvalidoError
from core.procedimiento.sede import SedeError
from core.procedimiento.universo import UniversoError

app = typer.Typer(add_completion=False, help=__doc__)

_ERRORES = (WorkspaceError, SedeError, UniversoError, MapaInvalidoError, ValueError)


def _fatal(exc: Exception) -> None:
    typer.echo(f"[ERROR] {exc}", err=True)
    raise typer.Exit(code=2)


@app.command()
def informe(
    case: str = typer.Option(None, "--case", help="case_id o W-code"),
    case_dir: str = typer.Option(None, "--case-dir", help="ruta explícita del caso"),
    expediente: str = typer.Option(..., "--expediente", help="id en el CRM"),
) -> None:
    """Qué hay en el procedimiento, qué falta y qué bloquea. No escribe nada.

    Sale con 0 si la vista está completa y con 1 si no — así encadena en un script.
    """
    try:
        inf = proc.informe(case, expediente, case_dir=case_dir)
    except _ERRORES as exc:
        _fatal(exc)

    typer.echo(f"expediente {inf.expediente_id} — {len(inf.filas)} documento(s) asignados")
    for carpeta, filas in inf.por_carpeta.items():
        if not filas:
            continue
        typer.echo(f"\n  {carpeta}")
        for f in filas:
            cal = f" [{f.calidad}]" if f.calidad else ""
            typer.echo(f"    {f.destino}{cal}   <- {f.rel_origen}")
            for a in f.avisos:
                typer.echo(f"        · {a}")
    for etiqueta, items in (("sin asignar", inf.sin_asignar),
                            ("enumerados y no descargados", inf.solo_listadas),
                            ("incoherencias", inf.incoherencias),
                            ("BLOQUEOS", inf.bloqueos)):
        if items:
            typer.echo(f"\n{etiqueta} ({len(items)}):")
            for x in items:
                typer.echo(f"  - {x}")
    typer.echo(f"\ncompleto: {'sí' if inf.completo else 'no'}")
    raise typer.Exit(code=0 if inf.completo else 1)


@app.command("borrador-mapa")
def borrador_mapa(
    case: str = typer.Option(None, "--case", help="case_id o W-code"),
    case_dir: str = typer.Option(None, "--case-dir", help="ruta explícita del caso"),
    expediente: str = typer.Option(..., "--expediente", help="id en el CRM"),
) -> None:
    """Emite a stdout un mapa de partida, con `orden` y `descripción` propuestos."""
    try:
        typer.echo(proc.borrador_mapa(case, expediente, case_dir=case_dir), nl=False)
    except _ERRORES as exc:
        _fatal(exc)


if __name__ == "__main__":
    app()
