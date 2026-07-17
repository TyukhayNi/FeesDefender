"""Deriva indice_documental.yaml (SSOT) del _MANIFIESTO.md que escribe la skill.

Determinista, idempotente. Self-contained (corre en Cowork sin core/). El test del
repo verifica que CAMPOS_EMITIDOS ⊆ core.catalogo_documental.CatalogEntry (anti-drift).
El LLM NO escribe YAML: lo escribe este helper.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# Duplica (self-contained, sin `core/`) el contrato único core.intake_lotes.fuente_de
# (spec §8, MEJORAS #54 T11). El test anti-drift `test_fuente_skill_sin_drift_con_core`
# compara `_fuente` contra `fuente_de` — mantener ambos en sincronía a mano.
_PATRON_LOTE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(whatsapp|email|manual|entrevista)_(\d{2,})$")
_SOURCE_MAP = {
    "01_Drive EV": "drive_ev", "02_Whatsapp": "whatsapp", "03_Email": "email",
    "04_Manual": "manual", "05_CRM": "crm", "06_Entrevistas": "entrevista",
}
# Columnas del _MANIFIESTO.md (orden fijo).
_COLS = ["sha256", "ruta_original", "nombre_canonico", "tipo", "fecha", "parte", "parent_id"]
# Campos que el helper escribe en el catálogo (subconjunto de CatalogEntry).
CAMPOS_EMITIDOS = [
    "id_doc", "ruta_relativa", "nombre_original", "tipo_documental", "fecha_doc",
    "parte", "fuente", "estado", "hash", "parent_id", "nombre_canonico",
]


def _fuente(ruta_rel: str) -> str:
    partes = ruta_rel.replace("\\", "/").lstrip("/").split("/")
    if len(partes) < 2:
        return "manual"
    top = partes[0]
    m = _PATRON_LOTE.match(top)
    if m:
        return m.group(2)
    return _SOURCE_MAP.get(top, "manual")


def _parse_filas(texto: str) -> list[dict]:
    filas = []
    for line in texto.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        celdas = [c.strip() for c in s.strip("|").split("|")]
        if len(celdas) != len(_COLS):
            continue
        if celdas[0] == "sha256" or set(celdas[0]) <= {"-"}:
            continue
        filas.append(dict(zip(_COLS, celdas)))
    return filas


def derivar(manifiesto: Path, salida: Path) -> Path:
    filas = _parse_filas(Path(manifiesto).read_text(encoding="utf-8"))
    entradas = []
    for f in filas:
        rel = f["ruta_original"]
        sha = f["sha256"]
        entradas.append({
            "id_doc": sha[:12] if sha else rel,
            "ruta_relativa": rel,
            "nombre_original": rel.replace("\\", "/").rsplit("/", 1)[-1],
            "tipo_documental": f["tipo"] or None,
            "fecha_doc": f["fecha"] or None,
            "parte": f["parte"] or None,
            "fuente": _fuente(rel),
            "estado": "original",
            "hash": sha,
            "parent_id": f["parent_id"] or None,
            "nombre_canonico": f["nombre_canonico"] or None,
        })
    Path(salida).write_text(
        yaml.dump(entradas, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return Path(salida)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("uso: manifiesto_a_catalogo.py <_MANIFIESTO.md> <indice_documental.yaml>")
        return 2
    derivar(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
