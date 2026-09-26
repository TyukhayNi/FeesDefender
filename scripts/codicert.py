"""Frontal del envío certificado. Es la ÚNICA puerta humana: `plan` enseña, `enviar` gasta.

    python -m scripts.codicert plan     W-04AKM2 --tipo OVC --plaza Madrid --doc A.pdf
    python -m scripts.codicert enviar   W-04AKM2 --tipo OVC --plaza Madrid --doc A.pdf --confirmar <digest>
    python -m scripts.codicert estado   W-04AKM2 --tipo OVC --plaza Madrid
    python -m scripts.codicert cosechar W-04AKM2 --tipo OVC --plaza Madrid
    python -m scripts.codicert aportable W-04AKM2 --tipo OVC --plaza Madrid

Las dos primeras son F1, `estado` y `cosechar` F2, y `aportable` F3. Solo `enviar`
exige confirmación con digest: es la que gasta 16,97 € y manda una comunicación
irreversible a un tercero. `estado` solo lee; `cosechar` archiva el certificado en el
expediente y lo cuelga del CRM, las dos cosas reversibles — pero corre bajo mutex,
porque dos a la vez subirían el mismo certificado dos veces.

`aportable` deja junto a cada íntegro la versión que va al juzgado —sin las páginas de
condiciones— y su manifiesto. Ni gasta ni sube nada, y corre bajo el MISMO mutex que la
cosecha, porque lee lo que ella escribe.

La orden manda sobre la variable (spec §8): producción exige `--entorno produccion`
escrito en la propia orden, aunque `CODICERT_ENTORNO=produccion` esté puesto en el
entorno. Una variable olvidada de una sesión anterior no puede ser lo único que
separe una prueba de un gasto irreversible.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

from core import codicert as _cod
from core import expedicion_certificada as exp
from core.ciudades import CIUDADES, ciudad_de_equipo
from core.sudespacho_relations import SudespachoRelationsError
from scripts._mutex_cli import CasoOcupado, MutexPerdidoEnCli, sostener

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


def _fecha(f) -> str:
    return f.strftime("%d/%m/%Y %H:%M") if f else "—"


def _dias(n: int) -> str:
    return f"{n} día" if n == 1 else f"{n} días"


def _no_cosechables(expedicion: exp.Expedicion, titulo: str) -> list[str]:
    """Lo no cosechable, con su motivo: es lo que el abogado necesita para saber qué
    hacer (M-21). Antes salía todo bajo «el hecho aún puede mejorar», y de un envío que
    lleva ochenta días quieto eso es falso."""
    grupos = expedicion.pendientes_por()
    if not grupos:
        return []
    lineas = ["", f"  {titulo}"]
    for motivo, envios in grupos.items():
        alerta = "" if motivo == exp.PUEDE_MEJORAR else "⚠️ "
        lineas.append(f"    {alerta}{exp.ETIQUETA[motivo]} — {exp.QUE_SIGNIFICA[motivo]}")
        lineas += [f"      · {e.id_envio} ({e.canal}), "
                   f"{_dias(e.dias_quieto(expedicion.leida_en))} sin moverse" for e in envios]
        if motivo == exp.ESTANCADO:
            lineas += ["      Si el certificado de hoy te sirve, `cosechar --incluir-pendientes`",
                       "      lo baja con su estado en el nombre, sin ocupar el sitio del",
                       "      definitivo. El aportable, solo sobre el definitivo."]
    return lineas


def render_estado(expedicion: exp.Expedicion,
                  partes: list[dict] | Callable[[str], list[dict]]) -> str:
    """Lo que el abogado lee para saber a quién se le ha entregado y cuándo.

    Enseña el nivel REQUERIDO delante y el de envío detrás, en ese orden y no al
    revés: el requerido es el que manda para los plazos (spec §6.1) y el de envío
    es operativo. No se imprime ninguna fecha agregada de expedición — ese nivel no
    tiene efecto jurídico y ponerlo invitaría a usarlo.

    `partes` admite un **callable perezoso** además de la lista ya resuelta, y esa
    es la diferencia que hace que la orden siga sirviendo cuando el expediente no
    está en esta máquina: resolver las partes exige el caso indexado en `CASOS_ROOT`
    y una lectura del CRM, mientras que los envíos y sus estados vienen de Codicert
    y no dependen de ninguna de las dos cosas. Medido corriendo el camino real el
    2026-09-21: con la lista resuelta antes de llamar, `codicert estado` moría entero
    y los tres envíos que Codicert sí tenía no llegaban a verse.
    """
    lineas = [
        f"EXPEDICIÓN {expedicion.id_personalizado}   [{expedicion.entorno.upper()}]",
        "",
        "  POR REQUERIDO (el nivel que cuenta para los plazos):",
    ]
    try:
        resueltas = partes(expedicion.id_personalizado.split(" - ")[0]) \
            if callable(partes) else partes
        requeridos = expedicion.por_requerido(resueltas)
    except Exception as err:  # noqa: BLE001 — el CRM o el catálogo local, indistintos
        requeridos = ()
        lineas += [
            f"    ⚠️ no se pudo resolver: {err}",
            "    Los envíos de abajo SÍ son válidos: vienen de Codicert, que no",
            "    depende del expediente local. Lo que falta es a quién atribuirlos.",
        ]
    for req in requeridos:
        lineas.append(f"    {req.etiqueta}")
        lineas.append(f"      recibido ... {_fecha(req.recibido_en)}")
        lineas.append(f"      accedido ... {_fecha(req.accedido_en)}   (art. 10.2)")
    lineas += ["", f"  {'ENVÍO':<12} {'CANAL':<12} {'ÚLTIMO':<34} COSECHABLE"]
    for e in expedicion.envios:
        ultimo = max(e.historico, key=lambda x: x.fecha) if e.historico else None
        etiqueta = f"{ultimo.codigo} · {ultimo.titulo}" if ultimo else "(sin histórico)"
        lineas.append(f"  {e.id_envio:<12} {e.canal:<12} {etiqueta:<34} "
                      f"{'sí' if e.cosechable else 'no'}")
    lineas += _no_cosechables(expedicion, "PENDIENTES, y por qué no se cosechan:")
    desconocidos = sorted({c for e in expedicion.envios for c in e.desconocidos})
    if desconocidos:
        lineas += [
            "", "  ⚠️ CÓDIGOS DE ESTADO SIN CLASIFICAR: "
            + ", ".join(str(c) for c in desconocidos),
            "     No se tratan como benignos. Míralos en el portal y añádelos",
            "     a `_FAMILIA_DE` en core/expedicion_certificada.py.",
        ]
    canales = sorted({e.tipo for e in expedicion.envios if not e.canal_clasificado})
    if canales:
        lineas += [
            "", "  ⚠️ CANALES SIN CLASIFICAR: tipo " + ", ".join(canales),
            "     No se cosechan y sus fechas no cuentan en «POR REQUERIDO»: no se",
            "     sabe qué acreditan. Añádelos a `CANAL_DE_TIPO` y `_CULMINACION`",
            "     en core/expedicion_certificada.py.",
        ]
    if not expedicion.envios:
        lineas += [
            "", "  Sin envíos con ese identificador en la ventana consultada.",
            "  Eso NO prueba que no se expidiera: un censo vacío no es una ausencia",
            "  (spec §5.2). Comprueba el identificador, el ordinal y la fecha.",
        ]
    return "\n".join(lineas)


def render_cosecha(cosechados, expedicion: exp.Expedicion) -> str:
    """Qué se archivó y qué no —con su motivo—, con el emisor verificado a la vista."""
    lineas = ["COSECHA", ""]
    for c in cosechados:
        marca = "ya estaba" if c.ya_estaba else "nuevo"
        if c.provisional:
            marca += ", PROVISIONAL"
        lineas.append(f"  {c.id_envio}  [{marca}]  gdocu {c.doc_id}")
        lineas.append(f"      emisor ... {c.razon_social_emisor} "
                      f"({c.usuario_emisor or 'usuario no releído en esta corrida'})")
        falta = "" if c.local_presente else "   ⚠️ NO ESTÁ (solo en el CRM)"
        lineas.append(f"      local .... {c.ruta_local}{falta}")
        lineas.append(f"      sha256 ... {c.sha256 or '(de una cosecha anterior)'}")
    lineas += _no_cosechables(expedicion, "NO COSECHADOS, y por qué:")
    if not cosechados:
        lineas.append("  Nada que cosechar todavía.")
    return "\n".join(lineas)


def render_aportables(resultados) -> str:
    """Qué se preparó para el juzgado, qué no y por qué. Ningún envío sin su línea."""
    lineas = ["APORTABLES", ""]
    for r in resultados:
        lineas.append(f"  {r.id_envio}  [{r.estado.upper().replace('_', ' ')}]  {r.canal}")
        if r.ruta_aportable:
            lineas.append(f"      aportable .... {r.ruta_aportable}")
        if r.ruta_manifiesto:
            lineas.append(f"      manifiesto ... {r.ruta_manifiesto}")
        if r.retiradas:
            lineas.append("      retiradas .... páginas "
                          + ", ".join(str(p) for p in r.retiradas) + " del certificado")
        if r.motivo:
            lineas.append(f"      motivo ....... {r.motivo}")
        lineas += [f"      ⚠ {a}" for a in r.avisos]
    if not resultados:
        lineas.append("  Nada que preparar.")
    lineas += ["", "  El aportable NO lleva la firma del prestador: la prueba custodiada",
               "  es el íntegro, con la huella que da su manifiesto.",
               "  Es la IMAGEN de las páginas que se conservan, con su texto leído por OCR:",
               "  sirve para buscar y leer, y el texto fiel es el del íntegro."]
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codicert", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="orden", required=True)
    AYUDA = {
        "plan": "enseña el plan; no gasta nada",
        "enviar": "ejecuta un plan ya confirmado; gasta",
        "estado": "relee en Codicert qué ha recibido cada requerido",
        "cosechar": "baja los certificados, los archiva y los sube al CRM",
        "aportable": "prepara la versión que va al juzgado, sin las condiciones",
    }
    for nombre in ("plan", "enviar", "estado", "cosechar", "aportable"):
        s = sub.add_parser(nombre, help=AYUDA[nombre])
        s.add_argument("w_code", help="expediente, p. ej. W-04AKM2")
        s.add_argument("--tipo", required=True, choices=list(exp.TIPOS_COMUNICACION))
        # `--doc` es del plan de ENVÍO: `estado` y `cosechar` solo leen lo que ya
        # salió, y exigirles los documentos no tendría sentido.
        if nombre in ("plan", "enviar"):
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
        if nombre == "cosechar":
            s.add_argument("--incluir-pendientes", action="store_true",
                           dest="incluir_pendientes",
                           help="baja también el certificado de lo no cosechable (en "
                                "curso, estancado o sin clasificar); su nombre lleva el "
                                "estado, así que no ocupa el sitio del definitivo")
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

        if args.orden == "estado":
            expedicion = exp.refrescar(args.w_code, args.tipo,
                                       entorno_exp=entorno_exp, ordinal=args.ordinal)
            # perezoso a proposito: ver el docstring de `render_estado`
            print(render_estado(expedicion, entorno_exp.partes_de))
            return 0

        if args.orden == "cosechar":
            # Mismo patrón de mutex que `enviar`, con clave PROPIA: `cosechar`
            # escribe en el expediente y en el CRM, y dos terminales a la vez
            # subirían el certificado dos veces -- el registro local no las separa,
            # porque las dos leerían "no está" antes de que ninguna escribiera.
            with sostener(
                    exp.clave_mutex_cosecha(args.w_code, args.tipo, entorno_exp,
                                            args.ordinal),
                    avisar=lambda m: print(m, file=sys.stderr),
                    que="la cosecha de certificados"):
                cosechados = exp.cosechar(
                    args.w_code, args.tipo, entorno_exp=entorno_exp,
                    ordinal=args.ordinal,
                    incluir_pendientes=args.incluir_pendientes)
                expedicion = exp.refrescar(args.w_code, args.tipo,
                                           entorno_exp=entorno_exp,
                                           ordinal=args.ordinal)
            print(render_cosecha(cosechados, expedicion))
            return 0

        if args.orden == "aportable":
            # La MISMA clave que `cosechar`: F3 lee el íntegro que la cosecha escribe
            # en la misma carpeta, y dos a la vez leerían uno a medio escribir.
            with sostener(
                    exp.clave_mutex_cosecha(args.w_code, args.tipo, entorno_exp,
                                            args.ordinal),
                    avisar=lambda m: print(m, file=sys.stderr),
                    que="la preparación de los aportables"):
                resultados = exp.preparar_aportables(
                    args.w_code, args.tipo, entorno_exp=entorno_exp,
                    ordinal=args.ordinal)
            print(render_aportables(resultados))
            return 1 if any(r.estado == exp.PARADO for r in resultados) else 0

        plan = exp.planificar(args.w_code, args.tipo, [Path(d) for d in args.docs],
                              entorno_exp=entorno_exp, plaza=plaza, entorno=entorno,
                              ordinal=args.ordinal)
        print(render_plan(plan, usuario=entorno_exp.usuario))
        if args.orden == "plan":
            return 0
        # H-05 (alto, estructural; revisión adversarial r2): admitir y ejecutar una
        # expedición sin exclusión entre procesos deja pasar dos terminales a la vez
        # -- las dos leen "sin pendientes", las dos ven el listado remoto vacío, las
        # dos mandan. `sostener` es el mismo "único sitio" que ya usan los demás
        # entrypoints (`scripts/_mutex_cli.py`) para el mutex de casos; aquí protege
        # la CUENTA de Codicert con la clave sintética que arma
        # `clave_mutex_expedicion` (cuenta+entorno+expedición, con forma de W-code).
        # `core/expedicion_certificada.ejecutar` EXIGE esta sesión -- nunca la
        # adquiere ella misma -- así que sin este `with` fallaría igual, pero tarde
        # y sin haber cerrado la ventana entre "comprobar" y "ejecutar".
        with sostener(exp.clave_mutex_expedicion(plan),
                     avisar=lambda m: print(m, file=sys.stderr),
                     que="el envío de la expedición"):
            ids = exp.ejecutar(plan, exp.Confirmacion(digest=args.confirmar),
                               entorno_exp=entorno_exp)
    except (exp.ExpedicionError, _cod.CodicertError, SudespachoRelationsError, ValueError) as err:
        # `entorno_exp.partes_de` (dentro de `planificar`) resuelve el expediente
        # del CRM y puede lanzar `SudespachoRelationsError`, o `ValueError` si
        # falta `SUDESPACHO_API_KEY`. El operador es un abogado: una traza de
        # Python cruda no es lo que debe leer ante un fallo del CRM (hallazgo 2).
        print(f"\nERROR: {err}", file=sys.stderr)
        return 1
    except CasoOcupado as exc:
        # Otro proceso de esta máquina ya está ejecutando la MISMA expedición
        # (misma cuenta, entorno y `id_personalizado`): cero bytes escritos por
        # esta invocación. Mismo código de salida que el resto de entrypoints
        # ocupados (`scripts/export_label_emails.py`, `scripts/sync_sudespacho.py`).
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 2
    except MutexPerdidoEnCli as exc:
        print(f"\nERROR: {exc} Artefactos: el registro de intención "
              "(`_codicert_intencion.jsonl`) de esta corrida.", file=sys.stderr)
        return 2

    print("\nENVIADO:", ", ".join(ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
