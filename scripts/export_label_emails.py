"""CLI: exporta una etiqueta Gmail al expediente como ``.eml`` fieles + adjuntos.

Resuelve el destino con ``core.casos.case_locator.path_for(ref)`` →
``00_Input/03_Email/`` y delega TODO el trabajo en el motor
``core.email_export.export_label`` (la lógica vive en el core; este CLI solo
orquesta). Idempotente. Solo lectura sobre Gmail.

Uso:
    python -m scripts.export_label_emails --ref W-02VND1 \
        --account nikolai.tyukhay@engelvoelkers.com \
        --label "01. CONTING/01. EXTRAJUD/01. BARCELONA/BaRS1 - Tibidabo 8 - (W-02VND1)"

Ejecución LOCAL: necesita el token OAuth en ``~/.gmail-mcp/tokens/<cuenta>.json``
(reutilizado de gmail-ro) y acceso de escritura a ``G:``. Desde Cowork no corre.

Salida en ASCII (gotcha cp1252 en PowerShell, CLAUDE.md).
"""

from __future__ import annotations

import argparse

from core.casos.case_locator import path_for, resolve_ref
from core.email_export import ExportReport, export_label


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
    args = parser.parse_args(argv)

    case_id = resolve_ref(args.ref)
    if case_id != args.ref:
        print(f"[export-label] ref '{args.ref}' resuelta al caso '{case_id}'.")
    dest = path_for(case_id) / "00_Input" / "03_Email"
    report = export_label(
        args.account, args.label, dest,
        case_id=case_id, extract_attachments=args.extraer_adjuntos,
        max_workers=args.workers, force=args.force,
    )
    _print_report(report, dest)
    if report.intake_logged:
        print("[export-label] traza forense: evento upload_email + hashes en el manifest.")
    return 1 if report.errors and report.written == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
