"""Cerebro puro de la migración bajo demanda a lotes (spec §7, MEJORAS #54).

Envuelve los cajones de ENTREGA con contenido en lotes sintéticos y calcula
el remapeo viejo→nuevo para los registros aguas abajo (M9, cobertura OCR,
catálogo). Los ESPEJOS (01_Drive EV, 05_CRM) no se tocan JAMÁS.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CAJONES_ENTREGA = {
    "02_Whatsapp": "whatsapp", "03_Email": "email",
    "04_Manual": "manual", "06_Entrevistas": "entrevista",
}
_FECHA_EN_NOMBRE = re.compile(r"^(\d{4}-\d{2}-\d{2})_")


@dataclass(frozen=True)
class MovimientoCajon:
    cajon: str
    fuente: str
    lote: str
    mapping: dict[str, str]     # rel viejo → rel nuevo (relativos a 00_Input/)


def estimar_fecha(cajon_dir: Path) -> str:
    """fecha_intake estimada (§7.3): mín(fechas ISO en nombres, mtimes)."""
    candidatas: list[str] = []
    for p in cajon_dir.rglob("*"):
        if not p.is_file():
            continue
        m = _FECHA_EN_NOMBRE.match(p.name)
        if m:
            candidatas.append(m.group(1))
        candidatas.append(
            datetime.fromtimestamp(p.stat().st_mtime).date().isoformat())
    return min(candidatas) if candidatas else datetime.now().date().isoformat()


def plan_migracion(input_dir: Path) -> list[MovimientoCajon]:
    """Un lote sintético <fecha>_<fuente>_01 por cajón de entrega CON contenido."""
    movimientos: list[MovimientoCajon] = []
    for cajon, fuente in CAJONES_ENTREGA.items():
        d = input_dir / cajon
        ficheros = [p for p in d.rglob("*") if p.is_file()] if d.is_dir() else []
        if not ficheros:
            continue
        lote = f"{estimar_fecha(d)}_{fuente}_01"
        mapping = {
            f"{cajon}/{p.relative_to(d).as_posix()}":
            f"{lote}/{p.relative_to(d).as_posix()}"
            for p in sorted(ficheros)
        }
        movimientos.append(MovimientoCajon(cajon, fuente, lote, mapping))
    return movimientos


def remap_paths(data: dict, mapping: dict[str, str]) -> tuple[dict, int]:
    """Reescribe primary_path/aliases[].path del M9 (§7.4a). Muta y devuelve."""
    n = 0
    for entry in data.values():
        p = entry.get("primary_path")
        if p in mapping:
            entry["primary_path"] = mapping[p]
            n += 1
        for alias in entry.get("aliases") or []:
            if isinstance(alias, dict) and alias.get("path") in mapping:
                alias["path"] = mapping[alias["path"]]
                n += 1
    return data, n


def remap_cobertura(rows: list[dict], mapping: dict[str, str]) -> tuple[list[dict], int]:
    """Reescribe rel_path de _cobertura.json (§7.4b)."""
    n = 0
    for row in rows:
        if row.get("rel_path") in mapping:
            row["rel_path"] = mapping[row["rel_path"]]
            n += 1
    return rows, n


def remap_catalogo(entries: list[dict], mapping: dict[str, str]) -> tuple[list[dict], int]:
    """Reescribe ruta_relativa del catálogo (§7.4c), con o sin prefijo 00_Input/."""
    n = 0
    for e in entries:
        ruta = e.get("ruta_relativa") or ""
        sin_prefijo = ruta[len("00_Input/"):] if ruta.startswith("00_Input/") else ruta
        if sin_prefijo in mapping:
            nuevo = mapping[sin_prefijo]
            e["ruta_relativa"] = f"00_Input/{nuevo}" if ruta.startswith("00_Input/") else nuevo
            n += 1
    return entries, n
