"""Sondeo recursivo del árbol del Gestor Documental de un expediente.

Pregunta: dado que ``list_gdocu_docs_rest`` devuelve solo el ``id_carpeta``
numérico y un ``label`` con el nodo hoja (insuficiente para reconstruir
la jerarquía), ¿el endpoint ``/api/folders/gdocu/{parent}`` permite
construir el árbol completo recurriendo desde la raíz?

Salida:
    - Imprime el árbol en consola con indentación.
    - Construye el mapping ``id_carpeta → ruta jerárquica completa``.
    - Cruza con los IDs reales de ``list_gdocu_docs_rest`` para confirmar
      que cada doc puede mapearse a una rama.
    - Persiste todo en ``data/probes/gdocu_tree_<expediente>_<ts>.json``.

Uso:
    python -m scripts.probe_gdocu_tree 657 expedientes_judiciales
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.sync_sudespacho import SudespachoClient  # noqa: E402


def walk(client: SudespachoClient, expediente_id: str, element: str,
         parent: str = "0", path: list[str] | None = None,
         out: dict[str, dict] | None = None) -> dict[str, dict]:
    """Recorre recursivamente el árbol Gdocu desde `parent` y rellena `out`
    con `{folder_id: {"name": ..., "path": [...], "parent": ...}}`.
    """
    if path is None:
        path = []
    if out is None:
        out = {}

    folders = client.list_gdocu_folders(
        expediente_id=expediente_id,
        element=element,
        parent=parent,
    )
    for f in folders:
        full_path = path + [f.name or f"<sin_nombre_{f.folder_id}>"]
        out[f.folder_id] = {
            "name": f.name,
            "parent": parent,
            "path": full_path,
            "raw": f.raw,
        }
        # Recursión: pedir hijos de esta carpeta
        walk(client, expediente_id, element,
             parent=f.folder_id, path=full_path, out=out)
    return out


def print_tree(tree: dict[str, dict]) -> None:
    """Imprime el árbol con indentación."""
    # Construir índice padre → hijos
    children: dict[str, list[str]] = {}
    for fid, info in tree.items():
        children.setdefault(info["parent"], []).append(fid)

    def _recurse(parent_id: str, depth: int = 0) -> None:
        for fid in sorted(children.get(parent_id, []), key=lambda x: int(x) if x.isdigit() else 0):
            info = tree[fid]
            indent = "  " * depth
            print(f"{indent}[{fid}] {info['name']}")
            _recurse(fid, depth + 1)

    print_tree_root = "0"  # El parent raíz suele ser '0'
    _recurse(print_tree_root, 0)


def main() -> int:
    expediente_id = sys.argv[1] if len(sys.argv) > 1 else "657"
    element = sys.argv[2] if len(sys.argv) > 2 else "expedientes_judiciales"

    print(f"[probe-tree] expediente={expediente_id} element={element}")
    print("[probe-tree] recorriendo árbol Gdocu desde raíz (parent=0)...")

    with SudespachoClient() as client:
        tree = walk(client, expediente_id, element)
        # Cross-check: pedir los docs y verificar que cada id_carpeta está en el árbol
        docs = client.list_gdocu_docs_rest(
            expediente_id=expediente_id, element=element
        )

    print(f"[probe-tree] {len(tree)} carpetas en el árbol")
    print()
    print("=" * 80)
    print("ÁRBOL COMPLETO")
    print("=" * 80)
    print_tree(tree)

    print()
    print("=" * 80)
    print("CRUCE: id_carpeta de cada doc vs. árbol")
    print("=" * 80)
    huerfanos: list[str] = []
    for d in docs:
        info = tree.get(d.id_carpeta or "")
        if info is None:
            huerfanos.append(d.id_carpeta or "<None>")
            print(f"  ⚠  doc {d.doc_id} ({d.filename[:50]})  →  id_carpeta={d.id_carpeta}  NO ENCONTRADO en árbol")
        else:
            ruta = " / ".join(info["path"])
            print(f"  ✓  doc {d.doc_id} ({d.filename[:50]})  →  {ruta}")

    if huerfanos:
        print(f"\n[probe-tree] ⚠  {len(set(huerfanos))} id_carpeta(s) huérfana(s): {sorted(set(huerfanos))}")
        print("[probe-tree] estos docs caerán en `99_Sin categoria/<expediente_id>/` con el refactor.")

    out_dir = ROOT / "data" / "probes"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"gdocu_tree_{expediente_id}_{ts}.json"
    out_path.write_text(
        json.dumps(
            {
                "expediente_id": expediente_id,
                "element": element,
                "tree": tree,
                "docs": [
                    {
                        "doc_id": d.doc_id,
                        "filename": d.filename,
                        "id_carpeta": d.id_carpeta,
                        "id_carpeta_label": d.id_carpeta_label,
                    }
                    for d in docs
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n[probe-tree] persistido → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
