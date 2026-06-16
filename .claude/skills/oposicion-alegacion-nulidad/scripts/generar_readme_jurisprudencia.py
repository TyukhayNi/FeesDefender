#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera references/jurisprudencia/README.md a partir de indice_jurisprudencia.json.
El índice es la fuente única de verdad; el README no se edita a mano.
Uso: python generar_readme_jurisprudencia.py [indice.json] [README.md]
"""
import json, os, sys

CENDOJ = ("TS", "AP Madrid", "AP Oviedo", "AP Cantabria", "AP Granada", "AP Valencia")


def _row(e):
    of = "PDF" if e["archivo_oficial"] else ("enlace" if e["enlace_oficial"] else "—")
    return (f'| {e["num_resolucion"]} | {e["ecli"]} | {e["fecha"]} | '
            f'{e["aplica"]} | {e["tipo_md"]} | {of} | {e["tema"]} |')


def generar(indice_path, out_path):
    R = json.load(open(indice_path, encoding="utf-8"))["resoluciones"]
    es = [e for e in R if e["tribunal"] in CENDOJ]
    tj = [e for e in R if e["tribunal"] == "TJUE"]
    L = [
        "# Biblioteca de jurisprudencia — skill `oposicion-alegacion-nulidad`", "",
        "**Este README se genera desde `indice_jurisprudencia.json` (fuente única de "
        "verdad). No editar a mano: editar el JSON y regenerar.**", "",
        "Estructura:", "",
        "- `sentencias_oficiales/` — **PDF oficiales del CGPJ** (para aportar en sala). Solo CENDOJ.",
        "- `sentencias_md/` — **copias de trabajo en texto** (verbatim o ficha) para localizar y citar ágilmente.",
        "- `indice_jurisprudencia.json` — control de artefactos (metadatos, rutas, estado).", "",
        "Regla de uso: para **argumentar/citar**, lee `sentencias_md`; para **aportar**, usa el "
        "PDF de `sentencias_oficiales` (CENDOJ) o el enlace oficial (TJUE). No entrecomilles como "
        "literal lo marcado `ficha`.", "",
        f"## CENDOJ — STS / SAP ({len(es)})", "",
        "| Resolución | ECLI | Fecha | Aplica | md | Oficial | Tema |",
        "|---|---|---|---|---|---|---|",
    ]
    L += [_row(e) for e in es]
    L += ["", f"## TJUE — Directiva 93/13 ({len(tj)})", "",
          "Sin PDF oficial local (decisión: anclar por ECLI + enlace EUR-Lex). Texto íntegro solo "
          "para la cadena de no integración; resto en ficha de síntesis.", "",
          "| Asunto | ECLI | Fecha | Aplica | md | Oficial | Tema |",
          "|---|---|---|---|---|---|---|"]
    L += [_row(e) for e in tj]
    no = ", ".join(f'{e["num_resolucion"]}' for e in R if e["aplica"] == "no")
    pa = ", ".join(f'{e["num_resolucion"]}' for e in R if e["aplica"] == "parcial")
    L += ["", "## Notas", "",
          f"- **No aplican / descartadas**: {no}.",
          f"- **Aplicabilidad parcial**: {pa}.",
          "- EUR-Lex no imprime el ECLI en el cuerpo; se hace constar por CELEX (verificado en URL/título).", ""]
    open(out_path, "w", encoding="utf-8").write("\n".join(L))
    return len(es), len(tj)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    juris = os.path.join(os.path.dirname(here), "references", "jurisprudencia")
    ind = sys.argv[1] if len(sys.argv) > 1 else os.path.join(juris, "indice_jurisprudencia.json")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(juris, "README.md")
    n, m = generar(ind, out)
    print(f"README generado: {n} CENDOJ + {m} TJUE")
