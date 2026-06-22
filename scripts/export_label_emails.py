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
    parser.add_argument("--ref", required=True, help="Referencia del caso (p. ej. W-02VND1).")
    parser.add_argument("--account", required=True, help="Cuenta Gmail (p. ej. ...@engelvoelkers.com).")
    parser.add_argument("--label", required=True, help="Nombre EXACTO de la etiqueta (ruta completa).")
    args = parser.parse_args(argv)

    dest = email_dest_dir(args.ref)
    report = export_label(args.account, args.label, dest, case_id=args.ref)
    _print_report(report, dest)
    if report.intake_logged:
        print("[export-label] traza forense: evento upload_email + hashes en el manifest.")
    return 1 if report.errors and report.written == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
