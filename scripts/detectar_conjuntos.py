"""Detector de conjunto (D9) — ejecución on-demand sobre un expediente.

Lista los documentos del Gestor Documental vía REST (trae ``fechamodificacion``
gracias a D10), detecta lotes cabecera+prueba (``core.conjunto_detector``) e
imprime un resumen. Con ``--log`` emite los eventos al ``_intake_log.jsonl`` del
caso (``conjunto_detectado`` / ``pendiente_revision``); por defecto es dry-run.

NO toca el CRM remoto ni mueve ficheros: solo detecta y propone. La persistencia
de la relación cabecera↔anexo (parent_id) se difiere a
``[SIGUIENTE-CATALOGO-DOCUMENTAL]``.

Uso:
    python -X utf8 -m scripts.detectar_conjuntos --expediente 444
    python -X utf8 -m scripts.detectar_conjuntos --expediente 444 --case "BaRS6 ..." --log
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.conjunto_detector import detect_bundles, log_bundle_proposals  # noqa: E402
from core.sync_sudespacho import SudespachoClient  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Detector de conjunto (D9)")
    ap.add_argument("--expediente", required=True, help="ID del expediente CRM")
    ap.add_argument("--element", default=None, help="Tipo de expediente (default: cfg)")
    ap.add_argument("--case", default=None, help="case_id para emitir eventos (con --log)")
    ap.add_argument("--log", action="store_true", help="Emitir eventos al log del caso")
    args = ap.parse_args()

    with SudespachoClient() as client:
        docs = client.list_gdocu_docs_rest(args.expediente, element=args.element)

    props = detect_bundles(docs)
    print(f"[D9] expediente={args.expediente}: {len(docs)} docs, {len(props)} lote(s)")
    print("-" * 78)
    for p in sorted(props, key=lambda x: -len(x.member_doc_ids)):
        tag = "ALTA" if p.confidence == "alta" else "BAJA->revision"
        print(f"[{tag:14}] {p.timestamp[:19]}  n={len(p.member_doc_ids):>2}  "
              f"bucket={p.bucket}  cabecera={p.header_doc_id}")
        if p.misfiled_doc_ids:
            print(f"                 prueba mal archivada: {list(p.misfiled_doc_ids)}")
        print(f"                 {p.reason}")
    print("-" * 78)

    if args.log:
        if not args.case:
            print("ERROR: --log requiere --case <case_id>")
            return 2
        n = log_bundle_proposals(args.case, props)
        print(f"[D9] {n} evento(s) escritos en el log de {args.case!r}")
    else:
        print("[D9] dry-run (sin --log): no se ha escrito ningun evento")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
