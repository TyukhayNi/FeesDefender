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
import datetime as _dt
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from core import codicert as _cod
from core import expedicion_certificada as exp
from core.ciudades import CIUDADES, ciudad_de_equipo

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
    armados a mano—: `main()` lo resuelve con `codicert.credenciales` y lo pasa
    aquí. Sin él (los tests de este módulo nunca lo pasan) se declara sin
    resolver, nunca se inventa un valor.
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


def entorno_real(*, plaza: str, entorno: str) -> exp.EntornoExpedicion:
    """Montaje de producción del puerto. Los tests de este módulo NUNCA lo usan.

    Resuelve credenciales, pide la `Ficha` UNA sola vez y envuelve el transporte
    con la superficie reducida que `ejecutar` consume (`credito()`, `listar()`,
    `enviar_burofax(**kw)`, `enviar_eec(**kw)`), sin exponer la `Ficha` misma.
    Rellena también `plaza` y `entorno`, que `ejecutar` contrasta contra el plan
    para no ejecutar en un entorno distinto del que se planificó.

    En sandbox se usa la credencial del sandbox (`plaza=None` en `credenciales`);
    en producción, la de la plaza.
    """
    usuario, clave = _cod.credenciales(None if entorno == "sandbox" else plaza, entorno=entorno)
    ficha = _cod.acceso(usuario, clave, entorno=entorno)

    class _Transporte:
        """Superficie mínima que `ejecutar` consume. No expone la `Ficha`."""

        def credito(self) -> Decimal:
            return _cod.credito(ficha, entorno=entorno)

        def listar(self, **filtros: Any) -> list[dict]:
            return list(_cod.listar(ficha, entorno=entorno, **filtros))

        def enviar_burofax(self, **kw: Any) -> str:
            return _cod.enviar_burofax(ficha, entorno=entorno, **kw)

        def enviar_eec(self, **kw: Any) -> str:
            return _cod.enviar_eec(ficha, entorno=entorno, **kw)

    def partes_de(w_code: str) -> list[dict]:
        """Las partes contrarias del expediente, leídas del CRM.

        Resuelve el `exp_id` numérico del elemento ``extrajudiciales`` por el
        índice local/Drive del caso (``_caso.md``) —igual que
        ``scripts/crm_ficha.py::_exp_id_de``— y lee sus relaciones con
        `sudespacho_relations.get_relaciones`. `clientes_contrarios` ya trae los
        campos que `destinatarios_de` necesita (spec §5): nombre, dirección,
        población, provincia, cp, email, móvil.
        """
        from core import case_manager, sudespacho_relations

        exp_id = next(
            (
                str(elemento.get("id"))
                for elemento in case_manager.get_case_status(w_code)["expedientes"]
                if isinstance(elemento, dict) and elemento.get("element") == "extrajudiciales"
            ),
            None,
        )
        if exp_id is None:
            raise exp.ExpedicionError(
                f"{w_code}: no tiene expediente 'extrajudiciales' registrado en el "
                "índice local del caso (_caso.md). No se puede resolver a quién "
                "notificar."
            )
        relaciones = sudespacho_relations.get_relaciones("extrajudiciales", exp_id)
        return relaciones.get("clientes_contrarios", [])

    return exp.EntornoExpedicion(
        codicert=_Transporte(),
        partes_de=partes_de,
        ahora=lambda: _dt.datetime.now(_dt.timezone.utc),
        raiz=Path.cwd(),
        plaza=plaza,
        entorno=entorno,
    )


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
        # Se resuelve aparte de `entorno_real` (que la vuelve a resolver por su
        # cuenta; sin coste de red: `credenciales` solo lee `.env`/entorno) porque
        # el plan tiene que enseñar el usuario emisor en su cabecera (spec §8) y
        # `entorno_real` no lo expone -- solo expone el transporte ya envuelto,
        # para no filtrar la `Ficha`.
        usuario, _clave = _cod.credenciales(None if entorno == "sandbox" else plaza,
                                            entorno=entorno)
        entorno_exp = entorno_real(plaza=plaza, entorno=entorno)
        plan = exp.planificar(args.w_code, args.tipo, [Path(d) for d in args.docs],
                              entorno_exp=entorno_exp, plaza=plaza, entorno=entorno,
                              ordinal=args.ordinal)
        print(render_plan(plan, usuario=usuario))
        if args.orden == "plan":
            return 0
        ids = exp.ejecutar(plan, exp.Confirmacion(digest=args.confirmar), entorno_exp=entorno_exp)
    except (exp.ExpedicionError, _cod.CodicertError) as err:
        print(f"\nERROR: {err}", file=sys.stderr)
        return 1

    print("\nENVIADO:", ", ".join(ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
