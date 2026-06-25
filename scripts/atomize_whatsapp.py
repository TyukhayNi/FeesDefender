"""CLI fino del motor de atomización de WhatsApp. Orquesta core.whatsapp_atomize."""
from __future__ import annotations

import argparse
import json

from core.whatsapp_atomize.pipeline import atomize_whatsapp_case
from core.whatsapp_atomize.propuesta_identidades import preparar_propuesta


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Atomización fina de WhatsApp")
    sub = parser.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("atomize", help="Atomiza los chats del caso")
    pa.add_argument("case_id")
    pp = sub.add_parser("proponer-identidades", help="Reúne autores+muestras (lectura pura)")
    pp.add_argument("case_id")
    args = parser.parse_args(argv)

    if args.cmd == "atomize":
        resumen = atomize_whatsapp_case(args.case_id)
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
    elif args.cmd == "proponer-identidades":
        print(json.dumps(preparar_propuesta(args.case_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
