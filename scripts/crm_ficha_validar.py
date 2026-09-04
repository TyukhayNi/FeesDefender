"""CLI local: comprueba que los datos del `_ficha_crm.yaml` estan en la documental.

Uso:
  python -m scripts.crm_ficha_validar --case-id W-XXXXXX [--solo-problemas]

**No escribe nada**: ni en el YAML, ni en el CRM, ni en el expediente. Solo lee y dice
donde esta cada dato — o donde habria que mirar a mano.

La logica pura vive en `core/crm_ficha_validacion.py`; aqui solo el IO y la salida.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from core.casos import case_locator
from core.crm_ficha import cargar_ficha_yaml
from core.crm_ficha_validacion import (
    ENCONTRADO,
    NO_BUSCABLE,
    NO_ENCONTRADO,
    SIN_COMPROBAR,
    corpus_legible,
    datos_de_ficha,
    resumen,
    validar,
)

app = typer.Typer(add_completion=False,
                  help="Validar el _ficha_crm.yaml contra la documental del expediente")

_SALA = Path("01_Procesado") / "02_Sala de máquina"
_MARCA = {ENCONTRADO: "ok", NO_ENCONTRADO: "FALTA", SIN_COMPROBAR: "sin comprobar",
          NO_BUSCABLE: "DATO MAL FORMADO"}


@app.command()
def main(
    case_id: str = typer.Option(..., "--case-id", help="case_id canónico o W-code"),
    solo_problemas: bool = typer.Option(
        False, "--solo-problemas", help="omite los datos que sí se encontraron"),
) -> None:
    resolved = case_locator.resolve_ref(case_id)
    case_dir = case_locator.buscar(resolved)
    if case_dir is None or not (case_dir / "00_Input" / "_caso.md").is_file():
        typer.echo(f"[ERROR] Caso no encontrado: {case_id!r} (resuelto: {resolved!r})", err=True)
        raise typer.Exit(code=1)

    ficha_path = case_dir / "00_Input" / "_ficha_crm.yaml"
    try:
        ficha = cargar_ficha_yaml(ficha_path)
    except FileNotFoundError:
        typer.echo(f"[ERROR] Falta _ficha_crm.yaml en {case_dir / '00_Input'}", err=True)
        raise typer.Exit(code=1)
    except ValueError as exc:
        typer.echo(f"[ERROR] _ficha_crm.yaml inválido: {exc}", err=True)
        raise typer.Exit(code=2)

    cobertura = case_dir / _SALA / "_cobertura.json"
    if not cobertura.is_file():
        typer.echo(
            f"[ERROR] No hay {cobertura.name}: la sala de máquina no se ha construido, "
            "así que no hay documental legible contra la que validar. Corre primero "
            "`organizar-sala-maquina`.", err=True)
        raise typer.Exit(code=1)

    # R1/H-12: un `_cobertura.json` truncado salia con codigo 1 por `JSONDecodeError`
    # crudo, sin un solo mensaje del CLI. Un fallo de precondicion no puede parecerse a
    # un dato que falta.
    try:
        entradas = json.loads(cobertura.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        typer.echo(f"[ERROR] {cobertura.name} no se puede leer ({exc}). No es que falten "
                   "datos: es que no hay contra qué validar.", err=True)
        raise typer.Exit(code=2)
    if not isinstance(entradas, list):
        typer.echo(f"[ERROR] {cobertura.name} no contiene una lista de documentos.",
                   err=True)
        raise typer.Exit(code=2)
    slugs, ilegibles = corpus_legible(entradas)

    md_dir = case_dir / _SALA / "03_MD"
    corpus: dict[str, str] = {}
    sin_espejo: list[str] = []
    for slug in slugs:
        p = md_dir / f"{slug}.md"
        if p.is_file():
            corpus[p.name] = p.read_text(encoding="utf-8", errors="replace")
        else:
            sin_espejo.append(slug)

    # Un documento marcado legible cuyo espejo no está en disco tampoco se pudo mirar.
    ilegibles = ilegibles + tuple(f"{s} (sin espejo MD)" for s in sin_espejo)

    hallazgos = validar(datos_de_ficha(ficha), corpus, ilegibles=ilegibles)

    typer.echo(f"Ficha:      {ficha_path}")
    typer.echo(f"Corpus:     {len(corpus)} documentos legibles")
    typer.echo(f"Ilegibles:  {len(ilegibles)}")
    typer.echo("")

    for h in hallazgos:
        if solo_problemas and h.ok:
            continue
        marca = _MARCA[h.veredicto]
        if h.ok and not h.dato.discriminante:
            marca = "ok, pero no acredita"
        typer.echo(f"  [{marca}] {h.dato.campo} = {h.dato.valor!r}")
        if h.documentos:
            muestra = ", ".join(h.documentos[:3])
            resto = f" (+{len(h.documentos) - 3})" if len(h.documentos) > 3 else ""
            typer.echo(f"        en: {muestra}{resto}")

    cuenta = resumen(hallazgos)
    typer.echo("")
    typer.echo(f"Resumen: {cuenta[ENCONTRADO]} encontrados · "
               f"{cuenta[NO_ENCONTRADO]} sin aparecer · "
               f"{cuenta[SIN_COMPROBAR]} sin comprobar")
    if cuenta["no_discriminantes"]:
        typer.echo(
            f"         de los encontrados, {cuenta['no_discriminantes']} NO acreditan: "
            "son de una sola palabra (una población, un apellido) y casan con cualquier "
            "tercero del expediente. Encontrarlos no prueba que este dato sea correcto.")

    if cuenta[NO_BUSCABLE]:
        typer.echo("")
        typer.echo("Hay datos de la ficha que no se pueden buscar (un teléfono de menos "
                   "de 9 dígitos, un documento de menos de 4 caracteres). No es que no "
                   "aparezcan: es que están mal escritos en la ficha.")

    if cuenta[SIN_COMPROBAR] and ilegibles:
        typer.echo("")
        typer.echo("No se pudo mirar en estos documentos — revísalos a mano:")
        for ruta in ilegibles:
            typer.echo(f"  - {ruta}")

    # Codigo de salida: 1 solo si algo NO APARECE teniendo todo el corpus legible. Lo
    # que no se pudo comprobar no es un fallo del dato, y tratarlo como tal entrenaria
    # a ignorar el comando en cuanto un DNI escaneado no tenga OCR — que es lo normal.
    if cuenta[NO_ENCONTRADO] or cuenta[NO_BUSCABLE]:
        typer.echo("")
        typer.echo("[ERROR] Hay datos en la ficha que no aparecen en NINGÚN documento "
                   "legible del expediente. Compruébalos antes de escribirlos al CRM.",
                   err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
