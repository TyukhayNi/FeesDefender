"""CLI de la sala de lectura (F4-F6). Disparo: clasificar/aplicar/render/poblar/organizar."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import typer  # noqa: E402

from core import catalogo_documental, inventory, sala_lectura  # noqa: E402
from core.casos import case_locator  # noqa: E402

app = typer.Typer(help="Organiza la sala de lectura de 01_Procesado.")


def _ref(case: str) -> str:
    """Resuelve `--case` al `case_id` canónico, aceptando también el W-code.

    `abrir_caso` y `sala_maquina` aceptan `W-02JSVZ`; esta CLI no, porque llamaba a
    `caso_path` (o sea `path_for`) sin pasar por `resolve_ref`, y abortaba con
    `LocalWorkspaceMissing` **tras derivar además una ciudad equivocada** —resolver una
    referencia que no entiende en vez de rechazarla (`MEJORAS #151`). `resolve_ref`
    devuelve el `ref` tal cual si no lo encuentra, así que un `case_id` completo pasa
    exactamente igual que antes.
    """
    return case_locator.resolve_ref(case)


@app.command()
def catalogo(case: str = typer.Option(..., "--case")):
    """(Re)construye indice_documental.yaml desde 00_Input (inventario + catálogo).

    Idempotente: preserva por hash lo ya clasificado y solo añade documentos
    nuevos. No necesita OCR ni MD/ — es el primer paso de la sala de lectura."""
    case = _ref(case)
    inventory.scan(case)
    catalogo_documental.build_catalog(case)
    n = len(catalogo_documental.load_catalog(case))
    typer.echo(f"Catálogo: {n} entradas")


@app.command()
def clasificar(case: str = typer.Option(..., "--case")):
    case = _ref(case)
    # Guarda: sin catálogo poblado, clasificar_caso escribiría una worklist
    # vacía silenciosamente. Si está vacío, se (re)construye primero.
    if not catalogo_documental.load_catalog(case):
        inventory.scan(case)
        catalogo_documental.build_catalog(case)
        typer.echo(
            f"Catálogo vacío → construido: "
            f"{len(catalogo_documental.load_catalog(case))} entradas."
        )
    r = sala_lectura.clasificar_caso(case)
    typer.echo(f"Deterministas: {r['n_deterministas']} | Residuo: {r['n_residuo']}")
    if r["n_residuo"]:
        typer.echo(
            f"Rellena la worklist y corre 'aplicar': "
            f"01_Procesado/_revisar/{sala_lectura.WORKLIST_NAME}"
        )


@app.command()
def aplicar(case: str = typer.Option(..., "--case")):
    case = _ref(case)
    r = sala_lectura.aplicar_clasificacion(case)
    typer.echo(f"Aplicadas: {r['n_aplicadas']}")


@app.command()
def render(case: str = typer.Option(..., "--case")):
    case = _ref(case)
    paths = sala_lectura.render_indices(case)
    typer.echo("Generado: " + ", ".join(p.name for p in paths))


@app.command()
def poblar(case: str = typer.Option(..., "--case")):
    case = _ref(case)
    r = sala_lectura.poblar_sala_lectura(case)
    typer.echo(f"Acciones: {r['acciones']}")


@app.command("preparar-residuo")
def preparar_residuo(case: str = typer.Option(..., "--case")):
    """Lista el residuo y la ruta de su texto extraído (MD/) para que Claude-en-sesión
    lo clasifique y rellene la worklist. Lectura pura: no llama a ningún LLM ni
    escribe nada (modo por defecto del despacho, sin coste de API)."""
    case = _ref(case)
    docs = sala_lectura.preparar_residuo(case)
    if not docs:
        typer.echo("Sin residuo con texto extraído. Nada que preparar.")
        return
    typer.echo(f"{len(docs)} doc(s) en residuo. Lee cada MD y rellena la worklist:")
    for d in docs:
        # **TODOS los espejos, no solo el primero.** El core concatena los segmentos de un
        # bundle partido y devuelve `md_paths`; imprimir solo `md_path` hacía que el flujo
        # humano que este mismo comando prescribe («lee cada MD») clasificara el documento
        # con información incompleta. Lo levantó la R1 adversarial.
        rutas = d.get("md_paths") or [d["md_path"]]
        typer.echo(f"  - [{d['hash'][:8]}] {d['nombre_original']}")
        for r in rutas:
            typer.echo(f"        {r}")
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
    case = _ref(case)
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
    case = _ref(case)
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
