"""Elimina entradas concretas de ``sudespacho_expedientes`` en ``_caso.md``.

Usado para depurar vínculos:
- Contaminados (p. ej. BaRR3 ← 648 cuando 648 pertenece a otro caso).
- Fantasma (p. ej. MaRS15 ← 653-656 cuando esos IDs no existen en el CRM).

Reescribe el frontmatter de forma atómica vía
:func:`core.case_manager._atomic_write_caso_md` (D10). NO toca el árbol
``00_Input/``: solo el ``_caso.md``. El borrado de ``sudespacho_<id>/``
se hace por separado desde PowerShell.

Uso::

    python -m scripts.remove_expediente_link "<CASE_ID>" <ID1> [<ID2> ...]

Ejemplo::

    python -m scripts.remove_expediente_link "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU" 648

Códigos de salida:
    0 si la mutación se ha aplicado (incluso si no había nada que borrar).
    1 si el caso no existe o el frontmatter no se puede leer.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Importa core.config indirectamente para cargar .env via dotenv.
from core.case_manager import _atomic_write_caso_md, caso_path  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print("Uso: python -m scripts.remove_expediente_link <CASE_ID> <ID1> [<ID2> ...]")
        return 1

    case_id = sys.argv[1]
    ids_target: set[str] = {str(x).strip() for x in sys.argv[2:] if str(x).strip()}

    from core.casos.case_locator import buscar
    base = buscar(case_id)
    if base is None:
        print("❌ el caso no existe en el catalogo")
        return 1
    index = base / "00_Input" / "_caso.md"
    if not index.exists():
        # Sin la ruta absoluta (§16).
        print("❌ falta `_caso.md` en el caso")
        return 1

    removed: list[str] = []

    def _mutate(fm: dict) -> dict:
        expedientes = fm.get("sudespacho_expedientes")
        if not isinstance(expedientes, list):
            # Sin lista o lista inválida → nada que borrar; deja el frontmatter como está
            return fm

        new_list: list = []
        for e in expedientes:
            if isinstance(e, dict) and str(e.get("id", "")).strip() in ids_target:
                removed.append(str(e.get("id", "")))
                continue
            new_list.append(e)

        fm["sudespacho_expedientes"] = new_list

        # Mirror en meta (CaseMeta.sudespacho_expedientes serializado por
        # _write_case_index — mantenemos coherencia con el resto del fichero).
        meta_in = fm.get("meta")
        if isinstance(meta_in, dict):
            meta_in["sudespacho_expedientes"] = new_list
            fm["meta"] = meta_in

        return fm

    _atomic_write_caso_md(case_id, _mutate)

    if removed:
        print(f"✓ Eliminadas {len(removed)} entrada(s) {removed} de '{case_id}'")
    else:
        print(f"(nada que borrar para '{case_id}'; IDs {sorted(ids_target)} no estaban presentes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
