"""Diagnóstico del expediente CRM mal vinculado a BaRR3.

Consulta vía REST API (x-api-key, sin PHPSESSID) los expedientes con IDs
indicados por CLI y reporta:

  · referencia_cliente
  · num_expediente / serie_expediente
  · fecha_alta
  · tipo_asunto / tipo_procedimiento
  · cualquier otra propiedad relevante devuelta por el endpoint

Estrategia: el endpoint ``GET /api/element_register/{element}/{id}`` está
bugueado (devuelve 500), así que usamos ``GET /api/element_registries/
{element}`` con ``properties[]`` y filtro por la propiedad ``id`` (operador
``equal``). Si ``id`` no es filtrable como propiedad, caemos a un listado
amplio de la serie del año y se localiza el item por el campo ``id``
del nivel raíz.

Uso:
    python -m scripts.diag_expediente_648                    # consulta 648 y 649
    python -m scripts.diag_expediente_648 648                # solo un ID
    python -m scripts.diag_expediente_648 648 649 700        # varios IDs

NO modifica nada del CRM — solo lectura.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

# Importa core.config indirectamente para que dotenv cargue .env
from core.sudespacho_create import _REST_BASE, _REST_TIMEOUT, _get_api_key  # noqa: E402


# Propiedades a pedir. Solo las CONFIRMADAS en _build_rest_payload_*; cualquier
# nombre fuera de esta lista revienta el endpoint con HTTP 500
# "ElementProperty not found" antes de aplicar el filtro (verificado
# empíricamente 2026-05-11). No incluimos fechas de creación/actualización
# porque no aparecen en los payloads productivos y el endpoint las rechaza
# en varios tenants.
_PROPS_JUDICIAL = [
    "referencia_cliente",
    "num_expediente",
    "serie_expediente",
    "fecha_alta",
    "tipo_asunto",
    "tipo_procedimiento",
    "cuantia",
    "posicion_procesal",
    "NIG",
    "notas",
    "referencia_procurador",
    "referencia_propia",
    "profesional_asignado",
]

_PROPS_EXTRAJUDICIAL = [
    "Referencia_Cliente",
    "Numero_Expediente",
    "serie_expediente",
    "Fecha_alta",
    "cuantia",
    "costas",
    "Asuntos",
    "Notas",
]


def _query_id(element: str, exp_id: int, props: list[str], api_key: str) -> dict | None:
    """Intenta localizar ``exp_id`` en ``element`` filtrando por la propiedad ``id``.

    Si el endpoint devuelve 500 "ElementProperty not found", reintenta con
    progresivamente menos propiedades hasta el mínimo (solo
    ``referencia_cliente`` / ``Referencia_Cliente``). Esto resiste a que el
    schema del tenant evolucione.

    Si el endpoint no soporta filtrar por ``id``, devuelve ``None`` y el
    llamador puede caer al modo "barrido por serie".
    """
    url = f"{_REST_BASE}/api/element_registries/{element}"
    headers = {"x-api-key": api_key, "Accept": "application/json"}

    # Subconjuntos a probar: completo → solo referencia. La intersección
    # mínima debería existir en cualquier tenant.
    minimal = props[:1] if props else []
    intents = [props, minimal] if props != minimal else [props]

    for attempt, props_try in enumerate(intents, start=1):
        params: list[tuple[str, str]] = []
        for i, p in enumerate(props_try):
            params.append((f"properties[{i}]", p))
        params += [
            ("filterGroup[condition]", "AND"),
            ("filterGroup[filterGroups][0][condition]", "AND"),
            ("filterGroup[filterGroups][0][filters][0][operator]", "equal"),
            ("filterGroup[filterGroups][0][filters][0][value]", str(exp_id)),
            ("filterGroup[filterGroups][0][filters][0][property]", "id"),
            ("itemsPerPage", "10"),
            ("return_totals", "true"),
        ]
        try:
            r = httpx.get(url, params=params, headers=headers, timeout=_REST_TIMEOUT)
        except Exception as e:  # noqa: BLE001
            print(f"   ❌ excepción HTTP (intento {attempt}): {e!r}")
            return None
        if r.status_code != 200:
            print(f"   ⚠️ intento {attempt} (props={props_try}) → HTTP {r.status_code}: {r.text[:300]}")
            continue
        data = r.json()
        items = data.get("items", []) or data.get("hydra:member", [])
        for item in items:
            if str(item.get("id", "")) == str(exp_id):
                return item
        # 200 con items vacíos → el filtro no encontró
        return None
    return None


def _query_by_serie(element: str, exp_id: int, props: list[str], api_key: str,
                    years: list[int]) -> dict | None:
    """Fallback: lista expedientes de ``years`` y busca por id.

    Igual estrategia de fallback de propiedades que ``_query_id``.
    """
    url = f"{_REST_BASE}/api/element_registries/{element}"
    headers = {"x-api-key": api_key, "Accept": "application/json"}
    minimal = props[:1] if props else []
    intents = [props, minimal] if props != minimal else [props]

    for year in years:
        for attempt, props_try in enumerate(intents, start=1):
            params: list[tuple[str, str]] = []
            for i, p in enumerate(props_try):
                params.append((f"properties[{i}]", p))
            params += [
                ("filterGroup[condition]", "AND"),
                ("filterGroup[filterGroups][0][condition]", "AND"),
                ("filterGroup[filterGroups][0][filters][0][operator]", "equal"),
                ("filterGroup[filterGroups][0][filters][0][value]", str(year)),
                ("filterGroup[filterGroups][0][filters][0][property]", "serie_expediente"),
                ("itemsPerPage", "500"),
                ("return_totals", "true"),
            ]
            try:
                r = httpx.get(url, params=params, headers=headers, timeout=_REST_TIMEOUT)
            except Exception as e:  # noqa: BLE001
                print(f"   ❌ excepción HTTP año {year} (intento {attempt}): {e!r}")
                continue
            if r.status_code != 200:
                print(f"   ⚠️ serie {year} intento {attempt} → HTTP {r.status_code}: {r.text[:300]}")
                continue
            data = r.json()
            items = data.get("items", []) or data.get("hydra:member", [])
            for item in items:
                if str(item.get("id", "")) == str(exp_id):
                    return item
            # 200 sin match → este año no contiene al exp_id; pasa al siguiente año
            break
    return None


def _format_item(item: dict) -> dict:
    """Convierte el item REST en {prop_name: value} plano."""
    out: dict = {"_id": str(item.get("id", "?"))}
    for v in item.get("values", []) or []:
        name = v.get("property", {}).get("name", "")
        out[name] = v.get("value", "")
    # Incluye campos top-level útiles si están presentes
    for k in ("createdAt", "updatedAt", "created_at", "updated_at"):
        if k in item:
            out[k] = item[k]
    return out


def _consultar_id(exp_id: int, api_key: str) -> None:
    print()
    print("=" * 78)
    print(f"Expediente ID {exp_id}")
    print("=" * 78)
    current_year = datetime.now().year
    years = [current_year, current_year - 1]

    # 1. Probar como judicial
    print(f"\n[judicial] /api/element_registries/expedientes_judiciales (filtro id={exp_id})")
    item = _query_id("expedientes_judiciales", exp_id, _PROPS_JUDICIAL, api_key)
    if item is None:
        print(f"   → no encontrado por id; barriendo series {years}…")
        item = _query_by_serie("expedientes_judiciales", exp_id, _PROPS_JUDICIAL, api_key, years)

    if item is not None:
        print(f"   ✅ encontrado en expedientes_judiciales")
        formatted = _format_item(item)
        print("   " + "─" * 70)
        print(json.dumps(formatted, indent=2, ensure_ascii=False))
        return

    # 2. Probar como extrajudicial
    print(f"\n[extrajudicial] /api/element_registries/extrajudiciales (filtro id={exp_id})")
    item = _query_id("extrajudiciales", exp_id, _PROPS_EXTRAJUDICIAL, api_key)
    if item is None:
        print(f"   → no encontrado por id; barriendo series {years}…")
        item = _query_by_serie("extrajudiciales", exp_id, _PROPS_EXTRAJUDICIAL, api_key, years)

    if item is not None:
        print(f"   ✅ encontrado en extrajudiciales")
        formatted = _format_item(item)
        print("   " + "─" * 70)
        print(json.dumps(formatted, indent=2, ensure_ascii=False))
        return

    print()
    print(f"   ❌ ID {exp_id} no encontrado en expedientes_judiciales NI extrajudiciales "
          f"(series {years}). Posibilidad: serie de otro año, o ID inexistente.")


def main() -> int:
    if len(sys.argv) > 1:
        ids = [int(x) for x in sys.argv[1:]]
    else:
        ids = [648, 649]

    try:
        api_key = _get_api_key()
    except ValueError as e:
        print(f"❌ {e}")
        return 1

    print(f"Consultando {len(ids)} expediente(s): {ids}")
    print(f"Endpoint base: {_REST_BASE}")

    for exp_id in ids:
        _consultar_id(exp_id, api_key)

    print()
    print("=" * 78)
    print("Diagnóstico terminado.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
