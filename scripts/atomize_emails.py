"""CLI fino del motor de atomización de correo.

Uso:
    python -m scripts.atomize_emails --ref W-02VND1
    python -m scripts.atomize_emails --src "<.../03_Email>" --out "<.../Emails>"

Solo orquesta ``core.email_atomize.pipeline`` (la lógica vive en el core).
"""
from __future__ import annotations

import argparse
import sys

from core.email_atomize import pipeline as P


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atomiza 03_Email a 01_Procesado/Emails.")
    parser.add_argument("--ref", help="case_id o W-code del expediente")
    parser.add_argument("--src", help="ruta a 00_Input/03_Email (alternativa a --ref)")
    parser.add_argument("--out", help="ruta de salida (con --src)")
    parser.add_argument("--entrega", help="sella una entrega con esta descripción tras atomizar")
    args = parser.parse_args(argv)

    if args.ref:
        report = P.atomize_case(args.ref)
        out_dir = P.emails_out_dir(args.ref)
    elif args.src and args.out:
        report = P.atomize_dir(args.src, args.out)
        out_dir = args.out
    else:
        parser.error("usa --ref, o --src junto con --out")
        return 2

    print(report.resumen())
    for n in report.notas:
        print(f"  NOTA: {n}", file=sys.stderr)
    for e in report.errores:
        print(f"  ERROR: {e}", file=sys.stderr)
    if args.entrega:
        dest = P.sellar_entrega(out_dir, args.entrega)
        print(f"Entrega sellada en: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
