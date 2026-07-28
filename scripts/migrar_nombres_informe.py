"""CLI del renombrado de informes de viabilidad al nombre corto (2026-07-28).

Los informes llevaban el ``case_id`` completo en el nombre dentro de una
carpeta que ya se llama ``case_id``, así que la ruta pasaba de los 260
caracteres que tolera Office y Excel no los abría. Este script los pasa al
nombre corto (``Informe viabilidad - <id_go>.xlsx``).

Solo renombra: nunca abre ni modifica el contenido de un ``.xlsx``, nunca
sobrescribe un destino existente y no toca las carpetas con más de un informe
humano (las reporta para que decidas tú cuál es el vigente).

Uso:
    python -m scripts.migrar_nombres_informe                 # dry-run (por defecto)
    python -m scripts.migrar_nombres_informe --apply         # aplica
    python -m scripts.migrar_nombres_informe --casos-root "G:/..."   # otra raíz
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from core.config import settings
from core.migrar_nombres_informe import (
    AMBIGUO,
    COLISION,
    RENOMBRAR,
    RUTA_OFFICE_MAX,
    YA_CORRECTO,
    aplicar,
    plan_renombrado,
    resumen,
)

_ICONO = {RENOMBRAR: "→", YA_CORRECTO: "=", COLISION: "!", AMBIGUO: "?"}


def _imprimir_plan(plan: list) -> None:
    for estado in (RENOMBRAR, COLISION, AMBIGUO, YA_CORRECTO):
        entradas = [e for e in plan if e.estado == estado]
        if not entradas:
            continue
        print(f"\n[{estado.upper()}]  {len(entradas)}")
        for e in entradas:
            print(f"  {_ICONO[estado]} {e.origen.name}  ({e.largo_origen})")
            if e.destino is not None and estado != YA_CORRECTO:
                print(f"      {e.destino.name}  ({e.largo_destino})")
            if e.detalle:
                print(f"      {e.detalle}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--apply", action="store_true",
        help="aplica el renombrado (por defecto solo muestra el plan)",
    )
    parser.add_argument(
        "--casos-root", type=Path, default=settings.casos_root,
        help="raíz de CASOS (por defecto, la de core.config.settings)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not args.casos_root.is_dir():
        print(f"ERROR: no existe la raíz de casos: {args.casos_root}", file=sys.stderr)
        return 2

    print(f"Raíz de casos: {args.casos_root}")
    print(f"Presupuesto de ruta para Office: {RUTA_OFFICE_MAX} caracteres")

    plan = plan_renombrado(args.casos_root)
    if not plan:
        print("No se han encontrado informes de viabilidad.")
        return 0

    _imprimir_plan(plan)
    conteo = resumen(plan)
    print(
        f"\nResumen: {conteo[RENOMBRAR]} a renombrar, "
        f"{conteo[YA_CORRECTO]} ya correctos, {conteo[COLISION]} colisiones, "
        f"{conteo[AMBIGUO]} ambiguos, "
        f"{conteo['fuera_de_presupuesto']} fuera de presupuesto tras el plan."
    )

    if not args.apply:
        print("\n(dry-run — nada se ha tocado. Repite con --apply para aplicar.)")
        return 0

    aplicadas = aplicar(plan)
    print(f"\nAplicado: {len(aplicadas)} renombrados.")
    pendientes = conteo[COLISION] + conteo[AMBIGUO]
    if pendientes:
        print(f"Quedan {pendientes} casos que requieren tu decisión (ver arriba).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
