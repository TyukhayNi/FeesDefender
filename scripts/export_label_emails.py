"""CLI: exporta una etiqueta Gmail al expediente como ``.eml`` fieles + adjuntos.

Reserva un LOTE nuevo en ``00_Input/<AAAA-MM-DD>_email_<NN>/`` con
``core.email_export.email_dest_dir(ref)`` (guard §6 incluido) y delega TODO el
trabajo en el motor ``core.email_export.export_label`` (la lógica vive en el
core; este CLI solo orquesta). Idempotente: una corrida sin novedad no deja
lote vacío. Solo lectura sobre Gmail.

Uso:
    python -m scripts.export_label_emails --ref W-02VND1 \
        --account nikolai.tyukhay@engelvoelkers.com \
        --label "01. CONTING/01. EXTRAJUD/01. BARCELONA/BaRS1 - [inmueble] - (W-02VND1)"

Ejecución LOCAL: necesita el token OAuth en ``~/.gmail-mcp/tokens/<cuenta>.json``
(reutilizado de gmail-ro) y acceso de escritura a ``G:``. Desde Cowork no corre.

Salida en ASCII (gotcha cp1252 en PowerShell, CLAUDE.md).
"""

from __future__ import annotations

import argparse
import sys

from core.casos.case_locator import resolve_ref
from scripts._mutex_cli import CasoOcupado, MutexPerdidoEnCli, sostener, w_code_de
from core.email_export import ExportReport, email_dest_dir, export_label


def _print_report(report: ExportReport, dest) -> None:
    print(f"[export-label] destino: {dest}")
    print(f"[export-label] {report.resumen()}")
    if report.errors:
        print("[export-label] ERRORES:")
        for err in report.errors:
            print(f"  - {err}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Exporta una etiqueta Gmail al expediente (.eml fieles + adjuntos)."
    )
    parser.add_argument("--ref", required=True,
                        help="case_id del caso o W-code (p. ej. W-02VND1); se resuelve al case_id canónico.")
    parser.add_argument("--account", required=True, help="Cuenta Gmail (p. ej. ...@engelvoelkers.com).")
    parser.add_argument("--label", required=True, help="Nombre EXACTO de la etiqueta (ruta completa).")
    parser.add_argument("--extraer-adjuntos", dest="extraer_adjuntos", action="store_true",
                        help="Extrae los adjuntos a subcarpetas fechadas (por defecto: plano, solo .eml).")
    parser.add_argument("--workers", type=int, default=8,
                        help="Descargas en paralelo (default 8; 1 = secuencial).")
    parser.add_argument("--force", action="store_true",
                        help="Ignora el índice _exported_ids.json y vuelve a bajar todo.")
    parser.add_argument("--no-aplanar-emails", dest="aplanar",
                        action="store_false", default=True,
                        help="No aplanar los emails reenviados como .eml adjunto "
                             "(por defecto SÍ se aplanan a primer nivel).")
    parser.add_argument("--no-resolver-enlaces", dest="resolver_enlaces",
                        action="store_false", default=True,
                        help="No rescatar ficheros enlazados a Drive/Gmail en el cuerpo "
                             "(por defecto SÍ se rescatan los binarios de descarga directa).")
    args = parser.parse_args(argv)

    case_id = resolve_ref(args.ref)
    if case_id != args.ref:
        print(f"[export-label] ref '{args.ref}' resuelta al caso '{case_id}'.")
    # El mutex del caso se sostiene desde ANTES de la primera escritura —y la primera escritura
    # es `email_dest_dir`, que reserva el lote con un `mkdir` (R1/H-01 de MEJORAS #126)— hasta
    # el final del export. Ocupado → código 2 y cero bytes.
    try:
        with sostener(w_code_de(case_id), avisar=lambda m: print(m, file=sys.stderr),
                      que="el export de correo"):
            dest = email_dest_dir(case_id)
            report = export_label(
                args.account, args.label, dest,
                case_id=case_id, extract_attachments=args.extraer_adjuntos,
                max_workers=args.workers, force=args.force,
                flatten_nested_emails=args.aplanar,
                resolve_drive_links=args.resolver_enlaces,
            )
    except CasoOcupado as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    except MutexPerdidoEnCli as exc:
        print(f"[ERROR] {exc} Artefactos: el lote de correo de esta corrida bajo 00_Input/.",
              file=sys.stderr)
        return 2
    _print_report(report, dest)
    if report.intake_logged:
        print("[export-label] traza forense: evento upload_email + hashes en el manifest.")
    return 1 if report.errors and report.written == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
