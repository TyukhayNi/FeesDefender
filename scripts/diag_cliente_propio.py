"""Diagnóstico de clientes propios en sudespacho.

⚠️ **ROTO al 2026-05-11** — el endpoint `/api/element_registries/clientes_propios`
devuelve HTTP 404 en el tenant tnm. La colección `clientes_propios` **no**
está expuesta como `element_registries` (sí lo están `expedientes_judiciales`,
`extrajudiciales`, `gdocu`, `colaboradores`). Ver `docs/DEAD_ENDS.md`.

El script se conserva como esqueleto: si en el futuro se descubre el
endpoint correcto (probable `/api/clientes_propios/{id}` o equivalente),
basta con sustituir las URLs en `list_clientes_propios()` y `detalle()`.

Mientras tanto, los IDs conocidos están hardcodeados en
`core.config.CLIENTES_PROPIOS_EV` (EV MMC SPAIN=2,
ENGEL & VÖLKERS SPAIN=27). Para verificar uno nuevo, abrir
`https://tnm.sudespacho.net/tnm/ficheros/clientes-propios/{id}` en el navegador.

Uso (cuando se arregle):
    python -m scripts.diag_cliente_propio              # lista todos
    python -m scripts.diag_cliente_propio 2 27         # detalle de IDs concretos

NO modifica nada — solo lectura.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from core.sudespacho_create import _REST_BASE, _REST_TIMEOUT, _get_api_key  # noqa: E402


def _headers() -> dict[str, str]:
    api_key = _get_api_key()
    if not api_key:
        raise SystemExit("SUDESPACHO_API_KEY no definida en entorno (.env).")
    return {"x-api-key": api_key, "Accept": "application/ld+json"}


def list_clientes_propios() -> list[dict]:
    """Lista todos los clientes propios del tenant."""
    url = f"{_REST_BASE}/api/element_registries/clientes_propios"
    params = {"itemsPerPage": "200"}
    r = httpx.get(url, params=params, headers=_headers(), timeout=_REST_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    items = data.get("items") or data.get("hydra:member") or []
    return items


def detalle(client_id: str) -> dict | None:
    """Devuelve el detalle de un cliente propio si existe."""
    url = f"{_REST_BASE}/api/element_registries/clientes_propios"
    params = {
        "properties[]": "id",
        "filterGroup[id][operator]": "equal",
        "filterGroup[id][value]": str(client_id),
        "itemsPerPage": "5",
    }
    r = httpx.get(url, params=params, headers=_headers(), timeout=_REST_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    items = data.get("items") or data.get("hydra:member") or []
    for item in items:
        if str(item.get("id")) == str(client_id):
            return item
    return None


def main() -> int:
    args = sys.argv[1:]
    if not args:
        items = list_clientes_propios()
        print(f"Total clientes_propios: {len(items)}\n")
        for it in items:
            cid = it.get("id")
            razon = (
                it.get("razon_social")
                or it.get("RazonSocial")
                or it.get("nombre")
                or it.get("Nombre")
                or "(sin razón social)"
            )
            cif = it.get("cif") or it.get("CIF") or ""
            print(f"  ID={cid:>4}  {razon}  {cif}")
        return 0

    for cid in args:
        info = detalle(cid)
        print(f"\n--- clientes_propios/{cid} ---")
        if info is None:
            print("  NO ENCONTRADO")
        else:
            print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
