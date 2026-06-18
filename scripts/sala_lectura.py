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


@app.command("preparar-residuo")
def preparar_residuo(case: str = typer.Option(..., "--case")):
    """Lista el residuo y la ruta de su texto extraído (MD/) para que Claude-en-sesión
    lo clasifique y rellene la worklist. Lectura pura: no llama a ningún LLM ni
    escribe nada (modo por defecto del despacho, sin coste de API)."""
    docs = sala_lectura.preparar_residuo(case)
    if not docs:
        typer.echo("Sin residuo con texto extraído. Nada que preparar.")
        return
    typer.echo(f"{len(docs)} doc(s) en residuo. Lee cada MD y rellena la worklist:")
    for d in docs:
        typer.echo(f"  - [{d['hash'][:8]}] {d['nombre_original']}  →  {d['md_path']}")
    typer.echo(
        f"\nWorklist: 01_Procesado/_revisar/{sala_lectura.WORKLIST_NAME}\n"
        "Tras rellenar, corre 'aplicar'."
    )


@app.command("clasificar-residuo")
def clasificar_residuo(
    case: str = typer.Option(..., "--case"),
    connector: bool = typer.Option(
        False, "--connector",
        help="OPT-IN: usa el conector LLM cloud (Scaleway/Mistral) — coste de API "
             "y tratamiento sujeto a DPA. Apagado por defecto.",
    ),
):
    """Autorrellena la worklist del residuo con un clasificador LLM.

    Sin --connector NO llama a ningún API: el modo por defecto es Claude-en-sesión
    (corre primero 'preparar-residuo'). Con --connector usa core/llm_cloud.py."""
    if not connector:
        typer.echo(
            "Modo por defecto: Claude-en-sesión (sin coste de API).\n"
            "Corre 'preparar-residuo --case ...', clasifica leyendo los MD y rellena "
            "la worklist; luego 'aplicar'.\n"
            "Para el conector programático de pago añade --connector."
        )
        raise typer.Exit(code=0)
    chat_fn = sala_lectura.make_llm_cloud_chat_fn()
    r = sala_lectura.clasificar_residuo_llm(case, chat_fn=chat_fn)
    typer.echo(
        f"Docs procesados: {r['n_docs']} | celdas rellenadas: {r['n_celdas']} | "
        f"baja confianza: {r['n_baja_confianza']} | sin texto: {r['n_sin_texto']}. "
        f"Valida la worklist y corre 'aplicar'."
    )


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
