"""CLI: anonimiza todos los documentos de un caso.

Uso:
  python -m scripts.anonimizar_caso "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
  python -m scripts.anonimizar_caso EV-2026-001 --tipo "Juicio Verbal" --politica REPROCESAR

Diseñado para uso independiente del pipeline general (`run_pipeline`):
útil cuando se quiere re-anonimizar tras añadir un PDF nuevo a 00_Input/
sin reejecutar todo el análisis.
"""

from __future__ import annotations

import json

import typer

from core.anon import anonimizar_caso

app = typer.Typer(
    add_completion=False,
    help="Anonimiza documentos de 00_Input/ → 06_Anonimizado/.",
)


@app.command()
def main(
    case_id: str = typer.Argument(..., help="ID del caso (validado por validate_case_id)."),
    tipo: str = typer.Option(
        "Juicio Ordinario", "--tipo", "-t",
        help="Tipo de procedimiento (metadato del frontmatter, no condiciona la anonimización).",
    ),
    politica: str = typer.Option(
        "SALTAR", "--politica", "-p",
        help="SALTAR (idempotente, default) o REPROCESAR (ignora skip).",
    ),
    auto_ocr: bool = typer.Option(
        False, "--auto-ocr",
        help="Si un PDF no tiene capa de texto, aplica OCR a una copia temporal "
             "y reintenta (no modifica el original). Requiere ocrmypdf + tesseract.",
    ),
) -> None:
    typer.echo(f"▶ Anonimizando caso {case_id}...")
    res = anonimizar_caso(case_id, tipo_proc=tipo, politica=politica, auto_ocr=auto_ocr)

    summary = {
        "case_id":        res["case_id"],
        "n_documentos":   res["n_documentos"],
        "n_procesados":   res["n_procesados"],
        "n_skipped":      res["n_skipped"],
        "n_errores":      res["n_errores"],
        "mapa_caso_path": str(res["mapa_caso_path"]),
        "log_path":       str(res["log_path"]),
        "errores":        res["errores"],
    }
    typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))

    if res["n_errores"] > 0:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
