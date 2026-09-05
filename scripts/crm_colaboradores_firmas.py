"""CLI local: leer las firmas de los correos de un expediente y proponer los datos que
faltan en las fichas de colaborador del CRM.

Dos comandos, y el orden importa:

    python -m scripts.crm_colaboradores_firmas report --case-id W-XXXXXX
    python -m scripts.crm_colaboradores_firmas apply  --case-id W-XXXXXX --confirmar

`report` **no escribe nada**: deja un informe en `01_Procesado/_firmas_colaboradores.md`
para que Nikolai lo lea. `apply` mete lo aprobado en `00_Input/_ficha_crm.yaml`, y es
`python -m scripts.crm_ficha` quien lo lleva al CRM. Ninguno de los dos escribe en el
CRM directamente: un solo camino de escritura.

El informe lleva PII (telefonos de personas), asi que vive en `data/CASOS/` y nunca se
commitea.
"""
from __future__ import annotations

from pathlib import Path

import typer
import yaml

from core.casos import case_locator
from core.email_firmas import (VEREDICTO_CONFLICTO, VEREDICTO_ENCONTRADO,
                               VEREDICTO_FIRMA_SIN_CAMPO, VEREDICTO_NO_LEIBLE,
                               VEREDICTO_SIN_FIRMA, Consolidado, extraer_de_directorio)
from core.sudespacho_relations import get_colaborador, resolver_parte

app = typer.Typer(add_completion=False,
                  help="Firmas de correo -> datos que faltan en las fichas de colaborador")


@app.callback()
def _callback() -> None:
    """Firmas de correo -> datos que faltan en las fichas de colaborador.

    Un `@app.command()` UNICO colapsa en Typer a un CLI sin subcomando (invocable
    sin nombrar `report`): medido con Typer 0.21.2, la condicion que fuerza el modo
    grupo es `registered_callback or registered_groups or len(commands) > 1`
    (`typer/main.py:get_command`). Hoy solo existe `report` -- `apply` es la Task
    10 -- asi que sin este callback (aunque no haga nada) `report --case-id X`
    fallaria con "Got unexpected extra argument (report)". Se fuerza el modo grupo
    ahora para que la interfaz de linea de comandos no cambie de forma cuando
    `apply` se anada.
    """


_INFORME = "_firmas_colaboradores.md"

_CABECERA = """\
<!-- GENERADO por scripts.crm_colaboradores_firmas — NO editar a mano. -->
# Firmas de colaboradores — {caso}

Leido de los `.eml` de `00_Input/`. **Este informe no ha escrito nada en el CRM.**

Como leer los veredictos:

| Veredicto | Significa |
|---|---|
| `ENCONTRADO` | El dato se leyo, y la columna «Origen» dice de donde |
| `FIRMA_SIN_CAMPO` | Hay firma de esa persona y **no trae ese campo**. Una de las dos plantillas corporativas de E&V no incluye movil, asi que esto **no** significa que no lo tenga |
| `CONFLICTO` | Dos valores distintos y ninguno decide. **No se propone nada** |

**El CARGO es el campo menos fiable de este informe, y se dice aqui en vez de callarlo.**
No tiene etiqueta en ninguna plantilla: se deduce por POSICION, como la linea siguiente a
la del nombre, y la linea del nombre se reconoce porque va en negrita. Medido sobre un
expediente real, sale vacio en dos firmas que si lo traen, por dos causas distintas: una
plantilla escribe el nombre **sin negrita**, y en otra la linea del nombre queda **fuera
de la ventana** del bloque. Asi que aqui `FIRMA_SIN_CAMPO` en el cargo significa «no supe
leerlo», no «no lo tiene». El cargo **no se escribe en el CRM** —no existe ese campo—,
solo se muestra para que lo confirmes tu. Detalle en `MEJORAS_FUTURAS`.

"""


def _caso_dir(case_id: str) -> tuple[str, Path]:
    resolved = case_locator.resolve_ref(case_id)
    case_dir = case_locator.buscar(resolved)
    if case_dir is None or not (case_dir / "00_Input" / "_caso.md").is_file():
        typer.echo(f"[ERROR] Caso no encontrado: {case_id!r} (resuelto: {resolved!r})",
                   err=True)
        raise typer.Exit(code=1)
    return resolved, case_dir


def _falta_en_el_crm(email: str) -> tuple[str, dict[str, str]]:
    """`(id o "", ficha)` del colaborador. Nunca lanza: sin CRM, se informa igual.

    Un fallo aqui deja la ficha en blanco y el informe lo dice; no se afirma que el
    campo del CRM este vacio cuando no se pudo mirar.
    """
    try:
        r = resolver_parte("colaboradores", nif="", email=email)
    except Exception:  # noqa: BLE001
        return "", {}
    colab_id = getattr(r, "id", None) or ""
    if not colab_id:
        return "", {}
    try:
        return colab_id, get_colaborador(colab_id)
    except Exception:  # noqa: BLE001
        return colab_id, {}


def _fila(c: Consolidado, colab_id: str, ficha: dict[str, str]) -> str:
    def celda(valor: str, veredicto: str, prop: str) -> str:
        actual = (ficha.get(prop) or "").strip() if ficha else ""
        if veredicto == VEREDICTO_CONFLICTO:
            return "**CONFLICTO** (no se propone)"
        if veredicto == VEREDICTO_FIRMA_SIN_CAMPO:
            return "`FIRMA_SIN_CAMPO`"
        if actual:
            return f"{valor} — el CRM ya tiene `{actual}`, **no se toca**"
        return f"**{valor}** — el CRM lo tiene vacio"

    donde = f"id {colab_id}" if colab_id else "**no existe como colaborador**"
    return (f"| {c.email} | {donde} | {celda(c.movil, c.veredicto_movil, 'movil')} "
            f"| {celda(c.telefono, c.veredicto_telefono, 'telefono1')} "
            f"| {c.cargo or '`' + c.veredicto_cargo + '`'} "
            f"| {', '.join(c.fuentes)} |")


@app.command()
def report(case_id: str = typer.Option(..., "--case-id",
                                       help="case_id canonico o W-code")) -> None:
    """Escribe el informe. NO toca el CRM ni el `_ficha_crm.yaml`."""
    resolved, case_dir = _caso_dir(case_id)
    consolidados, vistos, ilegibles = extraer_de_directorio(case_dir / "00_Input")

    partes = [_CABECERA.format(caso=resolved)]
    partes.append("## Quien firma, y que le falta en el CRM\n")
    partes.append("| Firma de | En el CRM | Movil | Fijo (`telefono1`) | Cargo | Origen |")
    partes.append("|---|---|---|---|---|---|")
    for email in sorted(consolidados):
        colab_id, ficha = _falta_en_el_crm(email)
        partes.append(_fila(consolidados[email], colab_id, ficha))

    candidatos = sorted(vistos - set(consolidados))
    partes.append("\n## Candidatos — SUGERENCIA, no un alta\n")
    partes.append(
        "Estas direcciones de E&V aparecen en los correos del expediente y **no firman "
        "ninguno**. Aparecer en un correo del caso no te hace colaborador del caso: "
        "medido el 2026-09-04 sobre otro expediente, de 7 direcciones en 6 correos solo "
        "3 estaban vinculadas, y estaban ahi por CC o por ser una unidad interna. "
        "**Decide tu**; este informe no da de alta a nadie.\n")
    if candidatos:
        partes.append("| Direccion | Veredicto | En el CRM |")
        partes.append("|---|---|---|")
        for email in candidatos:
            colab_id, _ = _falta_en_el_crm(email)
            partes.append(f"| {email} | `{VEREDICTO_SIN_FIRMA}` | "
                          f"{'id ' + colab_id if colab_id else 'no existe'} |")
    else:
        partes.append("_Ninguna._\n")

    partes.append("\n## Lo que NO se pudo mirar\n")
    if ilegibles:
        partes.append(
            f"**`{VEREDICTO_NO_LEIBLE}`.** Estos ficheros no se pudieron leer. Eso "
            "**no** es que no tengan firma: es que no se sabe.\n")
        partes.extend(f"- `{x}`" for x in ilegibles)
    else:
        partes.append("_Todos los `.eml` se leyeron._\n")

    destino = case_dir / "01_Procesado" / _INFORME
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    typer.echo(f"[OK] Informe: {destino}")
    typer.echo(f"     {len(consolidados)} firmas, {len(candidatos)} candidatos, "
               f"{len(ilegibles)} ilegibles")


#: Que campos del consolidado van al YAML, y con que clave. **`cargo` no esta**: no hay
#: property de cargo en `colaboradores` (el CRM enumero su contrato el 2026-09-04) y
#: escribirlo aqui seria dejar un dato muerto que nadie lleva a ningun sitio.
_AL_YAML = (("movil", "movil"), ("telefono", "telefono"))


@app.command()
def apply(
    case_id: str = typer.Option(..., "--case-id", help="case_id canonico o W-code"),
    confirmar: bool = typer.Option(False, "--confirmar",
                                   help="sin esto solo dice lo que haria"),
) -> None:
    """Mete en `_ficha_crm.yaml` lo que la firma dice y el YAML no tiene.

    **No escribe en el CRM**: de ahi al CRM va `python -m scripts.crm_ficha`, que es
    quien tiene el GET -> merge -> PUT.

    **No da de alta a nadie.** Solo toca colaboradores que ya estan en la lista: el
    corpus no sabe quien es colaborador del caso (§4 del spec), y eso lo decide Nikolai.
    """
    resolved, case_dir = _caso_dir(case_id)
    ficha_path = case_dir / "00_Input" / "_ficha_crm.yaml"
    if not ficha_path.is_file():
        typer.echo(f"[ERROR] No existe {ficha_path.name}: escribe primero la lista de "
                   "colaboradores del caso. `apply` rellena huecos, no da de alta.",
                   err=True)
        raise typer.Exit(code=1)

    datos = yaml.safe_load(ficha_path.read_text(encoding="utf-8")) or {}
    if not isinstance(datos, dict):
        typer.echo("[ERROR] _ficha_crm.yaml no es un mapping YAML", err=True)
        raise typer.Exit(code=1)

    consolidados, _, ilegibles = extraer_de_directorio(case_dir / "00_Input")
    colaboradores = datos.get("colaboradores") or []

    cambios: list[str] = []
    for col in colaboradores:
        if not isinstance(col, dict):
            continue
        email = str(col.get("email") or "").strip().lower()
        c = consolidados.get(email)
        if c is None:
            continue
        for campo_c, clave in _AL_YAML:
            valor = getattr(c, campo_c)
            veredicto = getattr(c, f"veredicto_{campo_c}")
            if veredicto != VEREDICTO_ENCONTRADO or not valor:
                continue
            if str(col.get(clave) or "").strip():
                continue          # lo que ya hay manda: no se pisa
            if confirmar:
                col[clave] = valor
            cambios.append(f"{email}: {clave} = {valor}")

    if not cambios:
        typer.echo("[OK] Nada que rellenar: o el CRM ya lo tiene, o la firma no lo trae.")
    for linea in cambios:
        typer.echo(f"  {'ESCRITO' if confirmar else 'SE ESCRIBIRIA'}  {linea}")

    if ilegibles:
        typer.echo(f"[AVISO] {len(ilegibles)} .eml no se pudieron leer: eso NO es que no "
                   "tengan firma. Mira el informe de `report`.")

    if not confirmar:
        typer.echo("\nNada escrito. Repite con --confirmar para aplicarlo.")
        return

    if cambios:
        # QUIEN pone las comillas, dicho con precision porque la version anterior de este
        # comentario mentia. Un telefono sin comillas (`0612345678`) lo relee YAML como un
        # entero octal, el cero inicial se pierde y `core.crm_ficha._escalar` lo RECHAZA
        # con ValueError, a proposito: un dato corrompido en silencio seria peor.
        #
        # Las comillas las pone `yaml.safe_dump` SOLO: su resolver ve que la cadena
        # "612345678" se releeria como int y la cita. Lo unico que hay que garantizar aqui
        # es que el valor llegue como **str** y no como int, porque un int se vuelca sin
        # comillas y ahi si se pierde el cero.
        #
        # Habia debajo un bucle que reemplazaba `f"{clave}: "` por si mismo, con un
        # comentario que decia «se fuerzan entre comillas simples». Era un no-op literal:
        # aparentaba una proteccion que no daba, y el que viniera detras habria confiado
        # en ella. Retirado.
        for col in colaboradores:
            if isinstance(col, dict):
                for _, clave in _AL_YAML:
                    if clave in col and col[clave] is not None:
                        col[clave] = str(col[clave])
        volcado = yaml.safe_dump(datos, allow_unicode=True, default_flow_style=False,
                                 sort_keys=False)
        ficha_path.write_text(volcado, encoding="utf-8")
        typer.echo(f"[OK] {ficha_path} actualizado ({len(cambios)} campos).")
        typer.echo("     Ahora: python -m scripts.crm_ficha --case-id " + resolved)


if __name__ == "__main__":
    app()
