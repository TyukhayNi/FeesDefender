"""Frontal del envío certificado. Es la ÚNICA puerta humana: `plan` enseña, `enviar` gasta.

    python -m scripts.codicert plan   W-04AKM2 --tipo OVC --plaza Madrid --doc A.pdf
    python -m scripts.codicert enviar W-04AKM2 --tipo OVC --plaza Madrid --doc A.pdf --confirmar <digest>

La orden manda sobre la variable (spec §8): producción exige `--entorno produccion`
escrito en la propia orden, aunque `CODICERT_ENTORNO=produccion` esté puesto en el
entorno. Una variable olvidada de una sesión anterior no puede ser lo único que
separe una prueba de un gasto irreversible.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from core import codicert as _cod
from core import expedicion_certificada as exp
from core.ciudades import CIUDADES, ciudad_de_equipo
from core.sudespacho_relations import SudespachoRelationsError

ENTORNOS: tuple[str, ...] = ("sandbox", "produccion")


def entorno_de(*, argumento: str | None) -> str:
    """Resuelve el entorno de ejecución. La orden manda sobre la variable (spec §8).

    Sin `--entorno` en la orden, el resultado es SIEMPRE ``sandbox`` — se ignora a
    propósito ``CODICERT_ENTORNO`` aunque valga ``"produccion"``. Una variable de
    entorno puesta en una sesión anterior y olvidada no puede ser lo único que
    separe una prueba de un gasto irreversible: solo la orden explícita, escrita
    en esta misma invocación, autoriza producción.
    """
    if argumento is None:
        if os.environ.get("CODICERT_ENTORNO") == "produccion":
            print(
                "[aviso] CODICERT_ENTORNO=produccion está puesto, pero sin "
                "--entorno produccion EN LA ORDEN se opera en sandbox: una "
                "variable olvidada no autoriza producción.",
                file=sys.stderr,
            )
        return "sandbox"
    if argumento not in ENTORNOS:
        sys.exit(f"entorno {argumento!r}: son {' | '.join(ENTORNOS)}")
    return argumento


def _plaza_de(valor: str) -> str:
    """Resuelve `--plaza`: admite la ciudad canónica o un código de equipo del CRM.

    Un código de equipo (``"BaRR3"``, ``"MaRS15"``...) es lo que el operador tiene
    a mano y admite menos error tipográfico que escribir la ciudad entera —con su
    tilde, en su caso: "San Sebastián".
    """
    if valor in CIUDADES:
        return valor
    resuelta = ciudad_de_equipo(valor)
    if resuelta is None:
        sys.exit(
            f"plaza {valor!r}: no es una ciudad de {sorted(CIUDADES)} ni un "
            "código de equipo reconocido"
        )
    return resuelta


def render_plan(plan: exp.Plan, *, usuario: str | None = None) -> str:
    """Lo que el humano lee ANTES de que se gaste un céntimo.

    Enseña el entorno en mayúsculas y bien visible, el usuario emisor y la plaza
    (spec §8: "el plan imprime el entorno y el usuario emisor literal en su
    cabecera"), quién recibe qué por qué canal (el aviso de sobre conjunto ya
    viaja dentro de la etiqueta que construye `destinatarios_de`), el asunto y el
    cuerpo literales que leerá el requerido, el coste, el crédito, el margen, las
    ausencias declaradas y el digest con el que se confirma la ejecución.

    `usuario` es el emisor YA resuelto (el `.bd` del Market Center que reclama,
    spec §2.1). `render_plan` no lo resuelve por sí mismo —eso sería tocar
    `.env`/entorno dentro de una función que los tests ejercitan con datos
    armados a mano—: lo resuelve `exp.entorno_real` al montar el transporte y lo
    expone en `entorno_exp.usuario` (hallazgo 5); `main()` lo toma de ahí, sin
    volver a invocar `codicert.credenciales` con los mismos argumentos. Sin él
    (los tests de este módulo nunca lo pasan) se declara sin resolver, nunca se
    inventa un valor.
    """
    lineas = [
        f"EXPEDICIÓN {plan.id_personalizado}   [{plan.entorno.upper()}]",
        f"  usuario emisor ... {usuario or '(sin resolver en esta llamada)'}",
        f"  plaza ............ {plan.plaza}",
        "  documentos ....... " + ", ".join(d.name for d in plan.documentos),
        f"  asunto ........... {plan.asunto}",
        f"  cuerpo ........... {plan.cuerpo}",
        "",
        f"  {'CANAL':<9} DESTINATARIO",
    ]
    for envio in plan.envios:
        lineas.append(f"  {envio.canal:<9} {envio.etiqueta}")
    lineas += [
        "",
        f"  coste estimado ... {plan.coste} €",
        f"  crédito .......... {plan.credito} €",
        f"  margen ........... {plan.credito - plan.coste} €",
    ]
    if not plan.ejecutable:
        lineas.append("  ⛔ NO EJECUTABLE: el crédito no cubre el coste.")
    if plan.ausencias:
        lineas += ["", "  AUSENCIAS DECLARADAS:"] + [f"    · {a}" for a in plan.ausencias]
    lineas += ["", f"  para ejecutarlo:  --confirmar {plan.digest}"]
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codicert", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="orden", required=True)
    for nombre in ("plan", "enviar"):
        s = sub.add_parser(
            nombre,
            help="enseña el plan; no gasta nada" if nombre == "plan"
            else "ejecuta un plan ya confirmado; gasta",
        )
        s.add_argument("w_code", help="expediente, p. ej. W-04AKM2")
        s.add_argument("--tipo", required=True, choices=list(exp.TIPOS_COMUNICACION))
        s.add_argument("--doc", action="append", required=True, dest="docs",
                       help="documento a adjuntar; repetible")
        s.add_argument("--plaza", required=True,
                       help="ciudad canónica o código de equipo (p. ej. Madrid, BaRR3)")
        s.add_argument("--entorno",
                       help="por defecto sandbox; produccion SOLO si se indica aquí")
        s.add_argument("--ordinal", type=int, default=1)
        if nombre == "enviar":
            s.add_argument("--confirmar", required=True, metavar="DIGEST",
                           help="el digest que enseñó `plan`")
    args = parser.parse_args(argv)

    entorno = entorno_de(argumento=args.entorno)
    plaza = _plaza_de(args.plaza)

    try:
        # `entorno_real` resuelve las credenciales UNA sola vez y expone el
        # usuario emisor ya resuelto en `.usuario` (hallazgo 5): antes se
        # resolvían aquí Y otra vez dentro de `entorno_real`, con los mismos
        # argumentos, solo para tener qué enseñar en la cabecera del plan (spec
        # §8).
        entorno_exp = exp.entorno_real(plaza=plaza, entorno=entorno)
        plan = exp.planificar(args.w_code, args.tipo, [Path(d) for d in args.docs],
                              entorno_exp=entorno_exp, plaza=plaza, entorno=entorno,
                              ordinal=args.ordinal)
        print(render_plan(plan, usuario=entorno_exp.usuario))
        if args.orden == "plan":
            return 0
        ids = exp.ejecutar(plan, exp.Confirmacion(digest=args.confirmar), entorno_exp=entorno_exp)
    except (exp.ExpedicionError, _cod.CodicertError, SudespachoRelationsError, ValueError) as err:
        # `entorno_exp.partes_de` (dentro de `planificar`) resuelve el expediente
        # del CRM y puede lanzar `SudespachoRelationsError`, o `ValueError` si
        # falta `SUDESPACHO_API_KEY`. El operador es un abogado: una traza de
        # Python cruda no es lo que debe leer ante un fallo del CRM (hallazgo 2).
        print(f"\nERROR: {err}", file=sys.stderr)
        return 1

    print("\nENVIADO:", ", ".join(ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
