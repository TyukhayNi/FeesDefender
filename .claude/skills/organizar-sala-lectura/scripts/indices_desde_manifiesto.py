"""Deriva INDICE.md (por categoría, fecha DESC; "07. RECLAMACIONES" sub-agrupada
por subcategoria_crm) y CRONOLOGIA.md (fecha ASC; 0000-00-00 y fechas
aproximadas (*) al final) del `_MANIFIESTO.md`. Determinista, idempotente,
stdlib puro (sin `core/` ni `yaml`). El LLM ya no transcribe ~350 líneas de
markdown por corrida (backlog robustez-velocidad, ítem 8): escribe solo el
`_MANIFIESTO.md` y ejecuta este script.
"""
from __future__ import annotations

import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifiesto_parser  # noqa: E402

_GEN = "<!-- GENERADO — NO EDITAR A MANO -->"
_RECLAMACIONES = "07. RECLAMACIONES"
_SIN_FECHA = "0000-00-00"
_SIN_CATEGORIA = "08. PENDIENTE DE CLASIFICAR"


def _fecha_limpia(fecha: str) -> str:
    return (fecha or "").replace("(*)", "").strip()


def _es_fecha_incierta(fecha: str) -> bool:
    f = (fecha or "").strip()
    return (not f) or f.startswith(_SIN_FECHA) or "(*)" in f


def _linea(f: dict) -> str:
    nombre = f.get("nombre_canonico") or ""
    orig = (f.get("ruta_original") or "").replace("\\", "/").rsplit("/", 1)[-1]
    fecha = f.get("fecha") or _SIN_FECHA
    return f"- {fecha} · [{nombre}]({nombre}) — original: {orig}"


def _subcat(f: dict) -> str:
    return (f.get("subcategoria_crm") or "").strip() or "correspondencia"


def construir_indice(filas: list[dict]) -> str:
    def clave_desc(f: dict):
        return (0 if _es_fecha_incierta(f.get("fecha", "")) else 1, _fecha_limpia(f.get("fecha", "")))

    por_cat: dict[str, list[dict]] = {}
    for f in filas:
        por_cat.setdefault((f.get("categoria") or _SIN_CATEGORIA).strip(), []).append(f)

    out = [_GEN, "", "# Índice documental", ""]
    for cat in sorted(por_cat):
        out += [f"## {cat}", ""]
        grupo = por_cat[cat]
        if cat == _RECLAMACIONES and any((f.get("subcategoria_crm") or "").strip() for f in grupo):
            por_sub: dict[str, list[dict]] = {}
            for f in grupo:
                por_sub.setdefault(_subcat(f), []).append(f)
            for sub in sorted(por_sub):
                out += [f"### {sub}", ""]
                out += [_linea(f) for f in sorted(por_sub[sub], key=clave_desc, reverse=True)]
                out += [""]
        else:
            out += [_linea(f) for f in sorted(grupo, key=clave_desc, reverse=True)]
            out += [""]
    return "\n".join(out).rstrip() + "\n"


def construir_cronologia(filas: list[dict]) -> str:
    def clave_asc(f: dict):
        return (1 if _es_fecha_incierta(f.get("fecha", "")) else 0, _fecha_limpia(f.get("fecha", "")))

    out = [_GEN, "", "# Cronología", ""]
    out += [_linea(f) for f in sorted(filas, key=clave_asc)]
    return "\n".join(out).rstrip() + "\n"


def derivar(manifiesto: Path, out_dir: Path) -> tuple[Path, Path]:
    filas = manifiesto_parser.parse_manifiesto(Path(manifiesto).read_text(encoding="utf-8"))
    indice = Path(out_dir) / "INDICE.md"
    crono = Path(out_dir) / "CRONOLOGIA.md"
    indice.write_text(construir_indice(filas), encoding="utf-8")
    crono.write_text(construir_cronologia(filas), encoding="utf-8")
    return indice, crono


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("uso: indices_desde_manifiesto.py <_MANIFIESTO.md> <sala_dir>")
        return 2
    derivar(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
