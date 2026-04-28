"""CLI: crear/asegurar un caso.

El nombre del caso ES la referencia CRM de Engel & Völkers. Es a la vez el
identificador interno y el nombre de la carpeta en data/CASOS/.

Formato: {City}{OpType}{Team} - {Dirección} ({W-ID}) - {Tipo caso}
Ejemplo: "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"

  · Ba    = Barcelona
  · RR    = Residential Rentals
  · 3     = nº de equipo
  · Roser 39, 2º = dirección
  · W-030LFT     = CRM ID de Engel & Völkers
  · Art 20 LAU   = tipología del caso

Uso:
  python -m scripts.init_caso "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
  python -m scripts.init_caso "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU" \\
      --cliente "EV MMC SPAIN, S.L.U." --contraparte "MARTÍNEZ GARCÍA, LAURA"
"""

from __future__ import annotations

import typer

from core import case_manager
from core.utils import validate_case_id

app = typer.Typer(add_completion=False, help="Crear/asegurar un caso")


@app.command()
def main(
    case_id: str = typer.Argument(
        ...,
        help="Referencia CRM: 'BaRR3 - Dirección (W-XXXXXX) - Art XX LAU'",
    ),
    titulo: str = typer.Option(None, "--titulo", help="Título alternativo (opcional)"),
    cliente: str = typer.Option(None, "--cliente"),
    contraparte: str = typer.Option(None, "--contraparte"),
    organo: str = typer.Option(None, "--organo"),
    cuantia: float = typer.Option(None, "--cuantia"),
    drive: str = typer.Option(None, "--drive", help="Ruta rclone, ej: gdrive:Casos/X"),
    drive_link: str = typer.Option(None, "--drive-link"),
) -> None:
    try:
        validate_case_id(case_id)
    except ValueError as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1)

    path = case_manager.ensure_case(
        case_id,
        titulo=titulo or case_id,
        referencia_crm=case_id,        # la referencia CRM es el propio case_id
        cliente=cliente,
        contraparte=contraparte,
        organo=organo,
        cuantia=cuantia,
        drive_remote_path=drive,
        drive_link=drive_link,
    )
    typer.echo(str(path))


if __name__ == "__main__":
    app()
