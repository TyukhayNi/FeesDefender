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
from scripts._mutex_cli import (
    AVISO_FUERA_DE_CASO, CasoOcupado, MutexPerdidoEnCli, caso_de_ruta, sostener, w_code_de,
    w_code_de_ruta,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atomiza 03_Email a 01_Procesado/Emails.")
    parser.add_argument("--ref", help="case_id o W-code del expediente")
    parser.add_argument("--src", help="ruta a 00_Input/03_Email (alternativa a --ref)")
    parser.add_argument("--out", help="ruta de salida (con --src)")
    parser.add_argument("--entrega", help="sella una entrega con esta descripción tras atomizar")
    args = parser.parse_args(argv)

    if args.ref:
        # MEJORAS #126: `w_code_de` resuelve la referencia ANTES de leer `_caso.md` (un W-code
        # no es nombre de carpeta: R1/H-03).
        w, aviso = w_code_de(args.ref), None
    elif args.src and args.out:
        # `--src/--out` NO significa «sin caso» (R1/H-04): el destino documentado es
        # `<caso>/01_Procesado/Emails`. Si cae bajo un caso del catálogo, su mutex. Y «fuera de
        # todo caso» solo se dice si de verdad no hay caso (R2/H-01): un caso sin W-code recibe
        # el aviso de identidad ausente, que es otro problema.
        w = w_code_de_ruta(args.out)
        aviso = AVISO_FUERA_DE_CASO if caso_de_ruta(args.out) is None else None
    else:
        parser.error("usa --ref, o --src junto con --out")
        return 2

    def _avisar(msg: str) -> None:
        print(msg, file=sys.stderr)

    try:
        # El bloque cubre el motor Y el sello: las dos escrituras de este CLI.
        with sostener(w, avisar=_avisar, que="la atomización de correo", aviso_sin_w_code=aviso):
            if args.ref:
                report = P.atomize_case(args.ref)
                out_dir = P.emails_out_dir(args.ref)
            else:
                report = P.atomize_dir(args.src, args.out)
                out_dir = args.out

            if not report.publicado:
                # No se ha escrito NADA (rama transitoria, spec §4.3): un resumen en ceros por
                # stdout + la nota solo en stderr es indistinguible de un caso sin correo. Y
                # sellar una entrega aquí llamaría `sellar_entrega` -> `mkdir(parents=True)`,
                # creando el árbol que el motor acaba de negarse a crear (o sellando uno viejo
                # como si fuera de esta corrida). Se imprime en stdout, se salta `--entrega` y
                # se devuelve 1 para que cualquier cosa que lea el exit code no lea éxito.
                print("ATOMIZACIÓN NO PUBLICADA: no se ha escrito nada en esta corrida.")
                for n in report.notas:
                    print(f"  NOTA: {n}")
                for e in report.errores:
                    print(f"  ERROR: {e}", file=sys.stderr)
                return 1

            print(report.resumen())
            for n in report.notas:
                print(f"  NOTA: {n}", file=sys.stderr)
            for e in report.errores:
                print(f"  ERROR: {e}", file=sys.stderr)
            if args.entrega:
                dest = P.sellar_entrega(out_dir, args.entrega)
                print(f"Entrega sellada en: {dest}")
            return 0
    except CasoOcupado as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    except MutexPerdidoEnCli as exc:
        print(f"[ERROR] {exc} Artefactos: 01_Procesado/Emails/ de este caso.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
