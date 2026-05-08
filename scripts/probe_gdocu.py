"""Sondeo del endpoint REST /api/element_registries/gdocu.

Objetivo: capturar el formato exacto de la respuesta para el campo
``id_carpeta`` y su ``label`` — necesario para implementar
``crm_branch_path()`` (M4) en el refactor v2 del intake.

Pregunta clave a resolver:
    ¿El ``label`` de la carpeta contiene la jerarquía completa
    ("CIVIL > 1ª INSTANCIA > DECLARATIVO > DEMANDA") o solo el nodo hoja
    ("DEMANDA")?

Salida:
    - Imprime resumen por consola.
    - Guarda respuesta completa en
      ``data/probes/gdocu_<expediente>_<timestamp>.json`` (gitignored).

Uso:
    python -m scripts.probe_gdocu 657 expedientes_judiciales

Defaults: expediente=657, element=expedientes_judiciales (caso real abierto
en la sesión de planificación del refactor 2026-05-08).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# Permitir ejecutar el script tanto vía -m como directamente.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.sync_sudespacho import SudespachoClient, GdocuDocInfo  # noqa: E402


def main() -> int:
    expediente_id = sys.argv[1] if len(sys.argv) > 1 else "657"
    element = sys.argv[2] if len(sys.argv) > 2 else "expedientes_judiciales"

    print(f"[probe] expediente={expediente_id} element={element}")
    print("[probe] llamando GET /api/element_registries/gdocu ...")

    with SudespachoClient() as client:
        docs: list[GdocuDocInfo] = client.list_gdocu_docs_rest(
            expediente_id=expediente_id,
            element=element,
            items_per_page=100,
        )

    print(f"[probe] {len(docs)} documentos recibidos")
    print()
    print("=" * 80)
    print("RESUMEN POR DOCUMENTO")
    print("=" * 80)
    for d in docs:
        print(f"\n· doc_id={d.doc_id}")
        print(f"  filename:         {d.filename}")
        print(f"  id_carpeta:       {d.id_carpeta!r}")
        print(f"  id_carpeta_label: {d.id_carpeta_label!r}")
        print(f"  mime:             {d.mime!r}")
        print(f"  size:             {d.size}")

    # Mostrar el raw del primer doc — es donde están todas las propiedades
    # tal y como las devuelve el CRM, sin parseo.
    if docs:
        print()
        print("=" * 80)
        print("RAW DEL PRIMER DOCUMENTO (estructura tal cual llega del CRM)")
        print("=" * 80)
        print(json.dumps(docs[0].raw, ensure_ascii=False, indent=2))

    # Persistir la respuesta completa para análisis offline
    out_dir = ROOT / "data" / "probes"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"gdocu_{expediente_id}_{ts}.json"
    out_path.write_text(
        json.dumps(
            [
                {
                    "doc_id": d.doc_id,
                    "filename": d.filename,
                    "id_carpeta": d.id_carpeta,
                    "id_carpeta_label": d.id_carpeta_label,
                    "mime": d.mime,
                    "size": d.size,
                    "raw": d.raw,
                }
                for d in docs
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n[probe] respuesta completa → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
