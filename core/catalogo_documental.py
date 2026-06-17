"""Catálogo documental canónico: indice_documental.yaml.

Fuente de verdad documental por caso. Alimenta INDICE.md / CRONOLOGIA.md
(renders de solo lectura, fases futuras). Cada documento de 00_Input/
tiene exactamente una entrada.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from .config import caso_path
from .inventory import load as load_inventory
from .utils import now_iso

CATALOG_FILENAME = "indice_documental.yaml"

_SOURCE_MAP = {
    "01_Drive EV": "drive_ev",
    "02_Whatsapp": "whatsapp",
    "03_Email": "email",
    "04_Manual": "manual",
    "05_CRM": "crm",
    "06_Entrevistas": "entrevistas",
}


@dataclass
class CatalogEntry:
    id_doc: str
    ruta_relativa: str
    nombre_original: str
    tipo_documental: str | None = None
    fecha_doc: str | None = None
    parte: str | None = None
    fuente: str = ""
    estado: str = "original"
    hash: str = ""
    fecha_indexado: str = ""
    parent_id: str | None = None
    orden_en_bundle: int | None = None


def _catalog_path(case_id: str) -> Path:
    return caso_path(case_id) / "01_Procesado" / CATALOG_FILENAME


def _map_source(inventory_source: str) -> str:
    return _SOURCE_MAP.get(inventory_source, inventory_source)


def load_catalog(case_id: str) -> list[CatalogEntry]:
    path = _catalog_path(case_id)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not data:
        return []
    return [CatalogEntry(**entry) for entry in data]


def build_catalog(case_id: str) -> Path:
    inv = load_inventory(case_id)
    path = _catalog_path(case_id)

    existing = load_catalog(case_id) if path.exists() else []
    existing_by_hash = {e.hash: e for e in existing if e.hash}

    now = now_iso()
    entries: list[CatalogEntry] = []

    for f in inv["files"]:
        sha = f.get("sha256", "")
        if sha and sha in existing_by_hash:
            entries.append(existing_by_hash[sha])
            continue

        entries.append(CatalogEntry(
            id_doc=sha[:12] if sha else f["rel_path"],
            ruta_relativa=f["rel_path"],
            nombre_original=f["name"],
            fuente=_map_source(f.get("source", "manual")),
            hash=sha,
            fecha_indexado=now,
        ))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(
            [asdict(e) for e in entries],
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path
