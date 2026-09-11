"""CLI local: el «OK» del EXPEDIENTE, no el del paso.

Uso:
  python -m scripts.verificar_apertura --case-id W-XXXXXX [--json] [--solo-problemas]

**No escribe nada**: ni en el expediente, ni en el CRM, ni en Drive. No pide el mutex y
no repara. Un verificador que arregla lo que encuentra deja de poder decir qué encontró.

La lógica vive en `core/verificar_apertura.py`; aquí solo el IO y la salida.

## Por qué NO escribe en `_apertura_v1.json`, que es lo que el diseño contrataba

El §5 del plan decía «cada comprobación emite `ok | pendiente | fallo` al `estado.json` y
al evento forense». No se ha hecho, y se dice en vez de dejarlo a medias:

1. Ese fichero vive en `00_Input/` del caso, así que escribirlo **exige el mutex**
   (`MEJORAS #126`) y convertiría un verificador de solo lectura en un escritor — con lo
   que dejaría de poder correrse mientras otra cosa trabaja sobre el caso, que es
   justamente cuando más falta hace.
2. **Nadie lo leería.** Persistir un estado que ningún consumidor consulta es la pieza
   construida que nadie encadena, el defecto que esta misma tanda de trabajo destapó dos
   veces.

Cuando exista el consumidor —la ficha de cierre de la acción 12, o V2 leyendo el
resultado para decidir si sigue—, se cablea entonces, con su mutex y su test.

## El código de salida

`0` si no hay ningún `fallo`; `1` si lo hay. `pendiente` **no** es fallo: un expediente a
medias tiene que poder verificarse sin que el comando grite, o el rojo deja de significar
algo. Y `sin_implementar` tampoco: no es un resultado del expediente, es un hueco de esta
herramienta.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import typer

from core import verificar_apertura as va
from core.casos import case_locator

app = typer.Typer(add_completion=False,
                  help="Verificar una apertura por RESULTADO, no por status")

_MARCA = {va.OK: "ok        ", va.PENDIENTE: "pendiente ",
          va.FALLO: "FALLO     ", va.SIN_IMPLEMENTAR: "(sin impl)"}


@app.command()
def main(
    case_id: str = typer.Option(..., "--case-id", help="W-code o case_id completo"),
    json_out: bool = typer.Option(False, "--json", help="Informe en JSON"),
    solo_problemas: bool = typer.Option(
        False, "--solo-problemas", help="Solo los fallos y pendientes"),
) -> None:
    base = case_locator.buscar(case_id)
    if base is None:
        typer.echo(f"[ERROR] Caso no encontrado: {case_id!r}", err=True)
        raise typer.Exit(code=2)

    informe = va.verificar(base)

    if json_out:
        typer.echo(json.dumps(
            {"case_dir": informe.case_dir, "resumen": informe.resumen,
             "resultados": [dataclasses.asdict(r) for r in informe.resultados]},
            ensure_ascii=False, indent=2))
    else:
        typer.echo(f"Expediente: {Path(informe.case_dir).name}\n")
        for r in informe.resultados:
            if solo_problemas and r.estado in (va.OK, va.SIN_IMPLEMENTAR):
                continue
            typer.echo(f"  [{_MARCA[r.estado]}] {r.titulo}")
            typer.echo(f"               {r.detalle}")
        typer.echo(f"\n{informe.resumen}")
        # El hueco se dice SIEMPRE, aunque se hayan filtrado las líneas: un resumen que
        # solo cuenta lo que miró es el falso «OK» que este comando viene a cerrar.
        huecos = [r for r in informe.resultados if r.estado == va.SIN_IMPLEMENTAR]
        if huecos:
            typer.echo(f"({len(huecos)} comprobación(es) NO construidas todavía: "
                       f"{', '.join(r.id for r in huecos)} — su estado real queda "
                       "SIN VERIFICAR, no «correcto»)")

    raise typer.Exit(code=1 if informe.fallos else 0)


if __name__ == "__main__":
    app()
