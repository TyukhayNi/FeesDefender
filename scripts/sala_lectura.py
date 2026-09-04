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
    sin_texto = sala_lectura.residuo_sin_texto(case)

    # **Tres estados, no uno.** Hasta el 2026-09-04 esto decía «Sin residuo con texto
    # extraído. Nada que preparar» tanto cuando no había residuo como cuando había 99 y
    # ninguno tenía espejo. La frase era cierta y por eso costó caro: mandó a buscar el
    # defecto donde no estaba. Un mensaje que no distingue «no hay» de «no pude mirar»
    # cuesta sesiones enteras y nunca aparece en un backlog, porque no rompe nada.
    if not docs and not sin_texto:
        # **La afirmación se deriva del CATÁLOGO, no de que las dos listas salgan vacías.**
        #
        # Historia, porque la segunda versión de esto también estaba mal. La R2 levantó que
        # `_filas_worklist` devuelve `[]` cuando el fichero no existe, así que los dos
        # métodos de residuo salían vacíos y esto afirmaba «todo el catálogo está
        # clasificado» con documentos SIN clasificar dentro — falso, y con salida 0. Lo
        # arreglé preguntando `sin_tipo and not hay_worklist`, o sea **remediando el
        # ejemplo**. El propio informe señalaba la frontera en la frase siguiente: los
        # brazos del `if` «son disjuntos sobre sus dos listas, no exhaustivos sobre el
        # estado documental», y anotaba por LECTURA un estado más: una fila de worklist
        # cuyo hash no está en el catálogo se descarta en silencio en los dos métodos
        # (`core/sala_lectura.py`, el `if e is None: continue` de ambos). Con la worklist
        # presente pero rancia —documentos reemplazados en `00_Input`, hashes que ya no
        # casan— `hay_worklist` es `True`, y la versión anterior volvía a mentir.
        #
        # Así que la condición no enumera causas: **si el catálogo tiene documentos sin
        # tipo, esta frase no se puede decir**, venga el vacío de donde venga. La causa solo
        # decide qué se aconseja, nunca si se afirma ni el código de salida.
        sin_tipo = [e for e in catalogo_documental.load_catalog(case)
                    if not e.tipo_documental]
        if sin_tipo:
            hay_worklist = (sala_lectura._revisar_dir(case)
                            / sala_lectura.WORKLIST_NAME).exists()
            causa = ("la worklist existe pero ninguna de sus filas casa con el catálogo "
                     "(hashes rancios: el material de 00_Input cambió después)"
                     if hay_worklist else
                     "la worklist no existe todavía")
            typer.echo(
                f"[AVISO] {len(sin_tipo)} doc(s) del catálogo están sin clasificar y "
                f"{causa}.\n"
                "        No es que no haya residuo: es que nadie lo ha calculado.\n"
                "        Corre primero:  python -m scripts.sala_lectura clasificar "
                '--case "<case_id>"',
                err=True)
            raise typer.Exit(code=1)
        typer.echo("Sin residuo: todo el catálogo está clasificado. Nada que preparar.")
        return
    if not docs:
        typer.echo(
            f"[AVISO] {len(sin_texto)} doc(s) en residuo y NINGUNO tiene texto extraído.\n"
            "        No es que no haya nada que clasificar: es que no hay nada que leer.\n"
            "        ¿Has corrido la sala de máquina?  "
            "python -m scripts.sala_maquina apply \"<case_id>\"",
            err=True,
        )
        for d in sin_texto:
            typer.echo(f"  - [{d['hash'][:8]}] {d['nombre_original']}  (sin espejo MD)")
        raise typer.Exit(code=1)

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
    # Y lo que se SALTA se dice, aunque haya salido lista. Con 88 de 99 legibles el listado
    # salía y nadie se enteraba de que 11 se habían quedado fuera.
    if sin_texto:
        typer.echo(
            f"\n[AVISO] {len(sin_texto)} doc(s) del residuo se quedan fuera por no tener "
            "texto extraído (sin espejo MD):", err=True)
        for d in sin_texto:
            typer.echo(f"  - [{d['hash'][:8]}] {d['nombre_original']}")
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
    if r.get("sin_material"):
        # No es un exito ni un fallo: es que no habia material catalogable, y decirlo
        # con la frase del exito («Sala de lectura organizada. Acciones: {}») es lo que
        # hacia indistinguible una sala vacia de una sala que no hacia falta montar.
        if r.get("motivo") == "sin_extension_relevante":
            typer.echo(
                f"Sin material catalogable: {r.get('n_omitidos')} fichero(s) en 00_Input, "
                "ninguno con extensión relevante. No se ha montado ninguna sala.")
        else:
            typer.echo("00_Input está vacío: no hay nada que organizar todavía.")
        return
    if r["detenido_por_residuo"]:
        typer.echo(
            f"Detenido: {r['n_residuo']} doc(s) en revision. "
            f"Rellena la worklist y vuelve a correr 'organizar'."
        )
    else:
        typer.echo(f"Sala de lectura organizada. Acciones: {r['acciones']}")


if __name__ == "__main__":
    app()
