"""Diagnóstico del bug `Numero_Expediente=0` en extrajudiciales.

Replica la query que tendría que hacer un `_get_next_num_expediente_extrajudicial`
contra el endpoint REST `/api/element_registries/extrajudiciales` y muestra:

  · totalItems devueltos por el endpoint
  · todos los Numero_Expediente encontrados (con sus IDs internos)
  · cuántos están en "0" o vacíos
  · max(Numero_Expediente) actual + cuál sería el siguiente

Permite confirmar empíricamente que el endpoint extrajudicial NO auto-asigna
el número (como sí pensábamos) antes de modificar `_build_rest_payload_extrajudicial`.

Uso:
    python -m scripts.diag_num_extrajudicial             # serie = año actual
    python -m scripts.diag_num_extrajudicial 2025        # serie específica
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from core.sudespacho_create import _REST_BASE, _REST_TIMEOUT, _get_api_key  # noqa: E402


def step(title: str) -> None:
    print()
    print("─" * 78)
    print(title)
    print("─" * 78)


def main() -> int:
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    print(f"Serie objetivo: {year}")

    try:
        api_key = _get_api_key()
    except ValueError as e:
        print(f"❌ {e}")
        return 1

    # ── 1. Query REST con properties[]+equal+totalItems ──────────────────
    step("1. GET /api/element_registries/extrajudiciales (mismo patrón que judicial)")
    url = f"{_REST_BASE}/api/element_registries/extrajudiciales"
    params: list[tuple[str, str]] = [
        ("properties[0]",                                                   "Numero_Expediente"),
        ("properties[1]",                                                   "serie_expediente"),
        ("filterGroup[condition]",                                          "AND"),
        ("filterGroup[filterGroups][0][condition]",                         "AND"),
        ("filterGroup[filterGroups][0][filters][0][operator]",              "equal"),
        ("filterGroup[filterGroups][0][filters][0][value]",                 str(year)),
        ("filterGroup[filterGroups][0][filters][0][property]",              "serie_expediente"),
        ("itemsPerPage",                                                     "500"),
        ("return_totals",                                                    "true"),
    ]
    headers = {"x-api-key": api_key, "Accept": "application/json"}

    try:
        r = httpx.get(url, params=params, headers=headers, timeout=_REST_TIMEOUT)
    except Exception as e:  # noqa: BLE001
        print(f"❌ excepción HTTP: {e!r}")
        return 1

    print(f"   HTTP {r.status_code}")
    if r.status_code != 200:
        print(f"   body: {r.text[:1000]}")
        return 1

    data = r.json()

    # ── 2. Resumen ────────────────────────────────────────────────────────
    step("2. Resumen de la respuesta")
    total_items = data.get("totalItems", "(clave totalItems ausente)")
    items = data.get("items", [])
    print(f"   totalItems (clave reportada): {total_items}")
    print(f"   len(items) recibido:          {len(items)}")
    print(f"   claves nivel raíz:            {list(data.keys())}")

    # ── 3. Extraer Numero_Expediente de cada item ─────────────────────────
    step("3. Detalle de Numero_Expediente por expediente")
    nums: list[tuple[str, str, str]] = []  # (id_item, Numero_Expediente, serie)
    for item in items:
        exp_id = str(item.get("id", "?"))
        num_val = ""
        serie_val = ""
        for val_obj in item.get("values", []):
            prop_name = val_obj.get("property", {}).get("name", "")
            v = str(val_obj.get("value", "")).strip()
            if prop_name == "Numero_Expediente":
                num_val = v
            elif prop_name == "serie_expediente":
                serie_val = v
        nums.append((exp_id, num_val, serie_val))

    nums_ordenados = sorted(
        nums,
        key=lambda t: int(t[1]) if t[1].isdigit() else -1,
    )
    print(f"   {'id':>8}  {'Numero_Expediente':>18}  {'serie':>6}")
    for exp_id, num_val, serie in nums_ordenados:
        flag = "  ⚠️ vacío/0" if num_val in ("", "0") else ""
        print(f"   {exp_id:>8}  {num_val:>18}  {serie:>6}{flag}")

    # ── 4. Análisis ───────────────────────────────────────────────────────
    step("4. Análisis")
    en_cero = [n for n in nums if n[1] in ("", "0")]
    con_valor = [int(n[1]) for n in nums if n[1].isdigit() and n[1] != "0"]
    max_num = max(con_valor) if con_valor else 0

    print(f"   expedientes con Numero_Expediente vacío o 0: {len(en_cero)}")
    print(f"   max(Numero_Expediente) válido:               {max_num}")
    print(f"   siguiente disponible (max+1):                {max_num + 1}")

    if en_cero:
        print()
        print("   ⚠️ Hay expedientes en 0 — confirmado el bug.")
        print("   Si el endpoint auto-asignara, no aparecería ninguno en 0.")
    else:
        print()
        print("   ✅ Todos tienen Numero_Expediente válido.")
        print("   Si el síntoma sigue, el bug no está en la auto-asignación")
        print("   sino en lo que envía el cliente.")

    print()
    print("=" * 78)
    print("Diagnóstico terminado.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
