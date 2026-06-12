"""CLI thin de ingesta de correos de procuradores -> cola de la bandeja (dry-run).

Robot del plan §3: trae los buzones del despacho, corre el matcher F1 y puebla la
cola de revision (``core.procurador_review``). NO escribe en el CRM. La
confirmacion humana es la pestana Streamlit «Bandeja de correos» (F2.3b).

Uso:
    python -m scripts.intake_procuradores [--once] [--query "..."] [--account a@b]

Scheduling: se delega al SO / skill `schedule` (no demonio propio). El gotcha de
PHPSESSID (~24 min) NO afecta a este runner (usa REST x-api-key).

Salida en ASCII (gotcha cp1252 en PowerShell, CLAUDE.md).
"""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

from core.gmail_source import BUZONES_DESPACHO, DEFAULT_QUERY, fetch_and_run
from core.procurador_runner import ReviewItem


def resumen_recuentos(items: list[ReviewItem]) -> dict[str, Any]:
    """Agrega los items procesados por estado y (pendientes) por confianza."""
    pendientes = Counter(i.proposal.confianza for i in items if i.estado == "pendiente")
    descartados = Counter(
        i.motivo_descarte or "sin_motivo" for i in items if i.estado == "descartado"
    )
    return {
        "total": len(items),
        "pendiente": dict(pendientes),
        "descartado": dict(descartados),
    }


def _print_resumen(res: dict[str, Any]) -> None:
    p = res["pendiente"]
    d = res["descartado"]
    print(f"[intake-procuradores] procesados: {res['total']}")
    print(
        "  a bandeja (pendiente): "
        f"alta={p.get('alta', 0)} dudosa={p.get('dudosa', 0)} ninguna={p.get('ninguna', 0)}"
    )
    if d:
        detalle = " ".join(f"{k}={v}" for k, v in sorted(d.items()))
        print(f"  descartados: {detalle}")
    else:
        print("  descartados: 0")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingesta de correos de procuradores (dry-run).")
    parser.add_argument("--once", action="store_true",
                        help="Una sola pasada (default; reservado para futuro modo loop).")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Query Gmail.")
    parser.add_argument("--account", action="append", default=None,
                        help="Cuenta a sondear (repetible). Default: buzones del despacho.")
    args = parser.parse_args(argv)

    accounts = tuple(args.account) if args.account else BUZONES_DESPACHO
    items = fetch_and_run(accounts, query=args.query)
    _print_resumen(resumen_recuentos(items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
