"""Probe puntual (D10): descubrir el slot/nombre de la fecha de modificación
en el listado REST /api/element_registries/gdocu.

El listado actual (`list_gdocu_docs_rest`) solo pide properties[2,4,9,11]
(nombrefinal/mime/tamano/id_carpeta) → ninguna fecha. Este probe añade
slots extra con varios nombres candidatos y vuelca qué propiedades devuelve
realmente el CRM para los primeros docs, para confirmar cuál trae un
timestamp usable antes de cablearlo al DTO.

Uso:
    python -X utf8 -m scripts.probe_gdocu_fecha 444
    python -X utf8 -m scripts.probe_gdocu_fecha 444 expedientes_judiciales
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.sync_sudespacho import SudespachoClient, ENDPOINTS  # noqa: E402

# Nombres candidatos para la fecha de modificación (validados contra el error
# 500 del CRM, que enumera las propiedades existentes).
CANDIDATES = {
    20: "fechamodificacion",
}


def main() -> int:
    expediente_id = sys.argv[1] if len(sys.argv) > 1 else "444"
    element = sys.argv[2] if len(sys.argv) > 2 else "expedientes_judiciales"

    base_params: dict = {
        "properties[2]":  "nombrefinal",
        "properties[11]": "id_carpeta",
        "filterGroup[condition]":                                 "AND",
        "filterGroup[filterGroups][0][filters][0][operator]":     "associated",
        "filterGroup[filterGroups][0][filters][0][value]":        str(expediente_id),
        "filterGroup[filterGroups][0][filters][0][property]":     f"left.{element}.id",
        "filterGroup[filterGroups][0][condition]":                "AND",
        "itemsPerPage":   100,
        "return_totals":  "true",
        "page": 1,
    }
    for idx, name in CANDIDATES.items():
        base_params[f"properties[{idx}]"] = name

    path = ENDPOINTS["element_registries"].format(element="gdocu")
    print(f"[probe-fecha] expediente={expediente_id} element={element}")
    print(f"[probe-fecha] candidatos: {CANDIDATES}")

    from core.sync_sudespacho import SudespachoError  # noqa: E402
    with SudespachoClient() as client:
        try:
            payload = client._get_json(path, **base_params)  # noqa: SLF001
        except SudespachoError as exc:
            # El 500 enumera las propiedades válidas: capturar la lista completa.
            print("[probe-fecha] ERROR del CRM (útil — lista propiedades válidas):")
            print(str(exc))
            return 1

    members = payload.get("hydra:member") if isinstance(payload, dict) else None
    if not members:
        # intentar otras claves de colección
        if isinstance(payload, list):
            members = payload
        else:
            members = (payload or {}).get("member") or []
    print(f"[probe-fecha] {len(members)} documentos recibidos\n")

    # Volcar las propiedades presentes en los primeros 5 docs.
    names_seen: set[str] = set()
    for member in members[:5]:
        doc_id = member.get("id")
        print(f"· doc_id={doc_id}")
        for v in (member.get("values") or []):
            pname = (v.get("property") or {}).get("name") or v.get("name")
            if not pname:
                continue
            names_seen.add(pname)
            print(f"    {pname!r:24} value={v.get('value')!r}  label={v.get('label')!r}")
        print()

    print("=" * 70)
    print("PROPIEDADES DEVUELTAS (unión sobre los 5 primeros docs):")
    for n in sorted(names_seen):
        flag = "  <-- CANDIDATA FECHA" if "fecha" in n.lower() or "updated" in n.lower() else ""
        print(f"    {n}{flag}")

    # Persistir crudo para análisis offline.
    out_dir = ROOT / "data" / "probes"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"gdocu_fecha_{expediente_id}.json"
    out_path.write_text(
        json.dumps(members[:5], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[probe-fecha] crudo (5 docs) → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
