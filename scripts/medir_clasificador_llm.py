#!/usr/bin/env python3
"""Mide el clasificador documental por LLM contra el catálogo REAL de los expedientes.

**Para qué existe.** Antes de cablear la clasificación automática en la corrida de
apertura hay que saber si acierta. El `indice_documental.yaml` de cada expediente es
**verdad conocida** —lo revisó el letrado—, así que sirve de banco de pruebas sin
construir nada ni tocar ningún caso.

**Qué NO es:** no es un test y no corre en la suite. Sale a la red (LLM de pago) y lee
de `CASOS_ROOT`, que es el Drive del despacho. Se invoca a mano.

**Solo lectura.** No escribe en ningún expediente.

Uso:
    python -m scripts.medir_clasificador_llm --por-caso 15 --limite 75
    python -m scripts.medir_clasificador_llm --ciudad Barcelona --salida medicion.json

Cifra de referencia (2026-09-14, `mistral-small-3.2-24b-instruct-2506` vía Scaleway):
**10 aciertos de 75 documentos (13%) en 6 expedientes**, y **52 de los 62 clasificados
con confianza >= 0.8 estaban MAL**. Cualquier cambio de modelo o de prompt se compara
contra eso.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import yaml

from core import config
from core.sala_lectura import make_llm_cloud_chat_fn

#: Lo que se le da a leer al modelo. Es el mismo tope que usa `make_llm_cloud_chat_fn`.
MAX_CHARS = 6000
#: Umbral por encima del cual la clasificación se aceptaría sin revisión humana.
UMBRAL = 0.8


def catalogo_de(caso: Path) -> dict[str, str]:
    """`{prefijo8_del_hash: categoria}` del `indice_documental.yaml`.

    **La forma es una LISTA de entradas**, no un dict con clave `documentos` — se
    comprobó abriéndolo. Y el enlace con los espejos MD es el **hash**: sus nombres
    acaban en `__<8 primeros del hash>.md`. Emparejar por nombre NO vale, porque el MD
    lleva el nombre canónico y el catálogo el original.
    """
    for y in caso.rglob("indice_documental.yaml"):
        try:
            d = yaml.safe_load(y.read_text(encoding="utf-8")) or []
        except (OSError, yaml.YAMLError):
            return {}
        if isinstance(d, dict):
            d = d.get("documentos") or d.get("items") or []
        out: dict[str, str] = {}
        for it in d:
            if isinstance(it, dict) and it.get("hash") and it.get("categoria"):
                out[str(it["hash"])[:8].lower()] = str(it["categoria"])
        return out
    return {}


def _norm(x: object) -> str:
    """Compara categorías ignorando el prefijo numérico y la caja."""
    return re.sub(r"^\d+\.\s*", "", str(x or "")).strip().upper()


def medir(raiz: Path, *, limite: int, por_caso: int, chat_fn=None) -> list[dict]:
    fn = chat_fn or make_llm_cloud_chat_fn()
    filas: list[dict] = []
    for caso in sorted((p for p in raiz.iterdir() if p.is_dir()),
                       key=lambda p: -p.stat().st_mtime):
        cat = catalogo_de(caso)
        md_dir = caso / "01_Procesado" / "02_Sala de máquina" / "03_MD"
        if not cat or not md_dir.is_dir():
            continue
        n_caso = 0
        for md in sorted(md_dir.glob("*.md")):
            if len(filas) >= limite or (por_caso and n_caso >= por_caso):
                break
            verdad = cat.get(md.stem.rsplit("__", 1)[-1].lower())
            if not verdad:
                continue
            try:
                texto = md.read_text(encoding="utf-8", errors="replace")[:MAX_CHARS]
            except OSError:
                continue
            t0 = time.time()
            try:
                out = fn({"hash": md.stem, "nombre_original": md.name,
                          "fuente": "medicion", "fecha_pista": "",
                          "md_path": str(md), "md_text": texto}) or {}
            except Exception as exc:  # noqa: BLE001
                out = {"error": f"{type(exc).__name__}: {exc}"[:120]}
            n_caso += 1
            filas.append({"caso": caso.name[:26], "doc": md.stem[:40],
                          "verdad": verdad, "predicho": out.get("tipo"),
                          "confianza": out.get("confianza"),
                          "seg": round(time.time() - t0, 2),
                          "error": out.get("error")})
        if len(filas) >= limite:
            break
    return filas


def informe(filas: list[dict]) -> dict:
    """Las tres cifras que deciden. **La tercera es la que importa.**"""
    ok = [f for f in filas if _norm(f["verdad"]) == _norm(f["predicho"])]
    alta = [f for f in filas
            if isinstance(f["confianza"], (int, float)) and f["confianza"] >= UMBRAL]
    ok_alta = [f for f in alta if _norm(f["verdad"]) == _norm(f["predicho"])]
    return {
        "documentos": len(filas),
        "casos": len({f["caso"] for f in filas}),
        "aciertos": len(ok),
        "con_confianza_alta": len(alta),
        "aciertos_con_confianza_alta": len(ok_alta),
        # Mal Y convencido: un umbral no protege de esto, porque el número con el que
        # filtrarías es justo el que miente.
        "mal_con_confianza_alta": len(alta) - len(ok_alta),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ciudad", default="Barcelona")
    ap.add_argument("--limite", type=int, default=75)
    ap.add_argument("--por-caso", type=int, default=15,
                    help="documentos por expediente. 75 de UN caso no son una muestra, "
                         "son un caso: repartirlos es lo que hace la cifra defendible")
    ap.add_argument("--salida", default="")
    args = ap.parse_args()

    raiz = Path(config.settings.casos_root) / args.ciudad
    if not raiz.is_dir():
        raise SystemExit(f"no existe {raiz}")

    filas = medir(raiz, limite=args.limite, por_caso=args.por_caso)
    r = informe(filas)
    if not filas:
        raise SystemExit("cero documentos emparejados: revisa el catálogo y los MD")

    print(f"documentos medidos      : {r['documentos']} en {r['casos']} expediente(s)")
    print(f"ACIERTO global          : {r['aciertos']}/{r['documentos']} = "
          f"{100 * r['aciertos'] // r['documentos']}%")
    print(f"con confianza >= {UMBRAL}    : {r['con_confianza_alta']}")
    if r["con_confianza_alta"]:
        print(f"  de esos, aciertan     : {r['aciertos_con_confianza_alta']}")
        print(f"  MAL con confianza alta: {r['mal_con_confianza_alta']}  <-- los peligrosos")
    print(f"tiempo medio por doc    : "
          f"{round(sum(f['seg'] for f in filas) / len(filas), 2)} s")

    print("\ndesacuerdos (los primeros):")
    for f in [x for x in filas if _norm(x["verdad"]) != _norm(x["predicho"])][:8]:
        print(f"  [{f['confianza']}] real={f['verdad']!r} -> dijo={f['predicho']!r}")

    if args.salida:
        Path(args.salida).write_text(
            json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\ndetalle en {args.salida}")


if __name__ == "__main__":
    main()
