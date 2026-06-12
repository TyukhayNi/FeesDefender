#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Motor de mejora continua: agrega telemetría + post + deltas → MEJORAS_<skill>.md (F12).

Lo ejecuta Cowork por **umbral**: cuando una skill acumula ≥ N (def. 5) usos
reales en ``uso.jsonl`` con su ``<ref>_post.jsonl`` correspondiente. Agrega las
tres señales (uso, checklists post, deltas borrador↔firmado), detecta patrones
recurrentes y produce ``<store>/<skill>/MEJORAS_<skill>.md``: propuestas
concretas de cambio al ``SKILL.md``, **cada una anclada al dato que la motiva**
(ref + fichero de log/delta).

Es un *handoff*: Claude Code revisa el informe, aplica las mejoras aprobadas al
``SKILL.md``, sube ``version`` y anota el ``## Changelog`` citando la evidencia.

Lee del store central (``data/_skill_logs/<skill>/``, gitignored — datos de
expediente). No modifica ningún ``SKILL.md``: solo escribe el informe.

Uso:
  python scripts/motor_mejora.py <skill> [--umbral 5] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_RESUMEN_RE = re.compile(r"(\d+)\s+añadidos.*?(\d+)\s+suprimidos.*?(\d+)\s+reescritos")


def _store_dir(skill: str) -> Path:
    env = os.environ.get("FEESDEFENDER_SKILL_LOGS")
    base = Path(env) if env else _REPO / "data" / "_skill_logs"
    return base / skill


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def cargar(skill: str) -> dict:
    d = _store_dir(skill)
    usos = _read_jsonl(d / "uso.jsonl")
    posts: dict[str, list[dict]] = {}
    for f in sorted(d.glob("*_post.jsonl")):
        ref = f.name[: -len("_post.jsonl")]
        posts[ref] = _read_jsonl(f)
    deltas: dict[str, dict] = {}
    for f in sorted(d.glob("*_delta.md")):
        ref = f.name[: -len("_delta.md")]
        m = _RESUMEN_RE.search(f.read_text(encoding="utf-8"))
        if m:
            deltas[ref] = {"anadido": int(m.group(1)), "suprimido": int(m.group(2)),
                           "reescrito": int(m.group(3)), "fichero": f.name}
    refs_uso = {u.get("ref") for u in usos if u.get("ref")}
    refs_con_post = sorted(r for r in refs_uso if r in posts)
    return {"dir": d, "usos": usos, "posts": posts, "deltas": deltas,
            "refs_uso": refs_uso, "refs_con_post": refs_con_post}


def _metricas_post(posts: dict[str, list[dict]]) -> dict:
    resultados: Counter = Counter()
    alegaciones: list[tuple[str, str]] = []   # (texto, ref)
    valoraciones: list[float] = []
    for ref, entradas in posts.items():
        for e in entradas:
            m = e.get("metricas") or {}
            if m.get("resultado"):
                resultados[str(m["resultado"]).lower()] += 1
            if m.get("alegacion_no_prevista"):
                alegaciones.append((str(m["alegacion_no_prevista"]).strip(), ref))
            v = m.get("valoracion")
            if isinstance(v, (int, float)):
                valoraciones.append(float(v))
    return {"resultados": resultados, "alegaciones": alegaciones, "valoraciones": valoraciones}


def _propuestas(skill: str, data: dict, post_m: dict) -> list[str]:
    props: list[str] = []
    # 1. Alegaciones/objeciones no previstas recurrentes (≥2) → incorporar al SKILL.md.
    norm: Counter = Counter()
    ejemplos: dict[str, list[str]] = {}
    for texto, ref in post_m["alegaciones"]:
        k = texto.lower()
        norm[k] += 1
        ejemplos.setdefault(k, []).append(ref)
    for k, n in norm.most_common():
        if n >= 2:
            refs = ", ".join(sorted(set(ejemplos[k])))
            props.append(
                f"**Incorporar al SKILL.md una alegación/objeción recurrente no prevista** "
                f"({n} casos): «{k}». Evidencia: posts de {refs}."
            )
    # 2. Resultados adversos dominantes → revisar criterio.
    res = post_m["resultados"]
    adversos = res.get("inadmitido", 0) + res.get("desestimado", 0)
    favorables = res.get("admitido", 0) + res.get("estimado", 0)
    if adversos and adversos >= favorables:
        props.append(
            f"**Revisar criterio**: resultados adversos ({adversos}) ≥ favorables ({favorables}). "
            f"Analizar qué alegaciones/pruebas no cuelan (ver posts y deltas)."
        )
    # 3. Escritos muy reescritos → revisar plantilla/cláusula.
    reescritos = sorted(data["deltas"].items(), key=lambda kv: kv[1]["reescrito"], reverse=True)
    for ref, dd in reescritos:
        if dd["reescrito"] >= 3:
            props.append(
                f"**Plantilla/cláusula candidata a ajuste**: la ref `{ref}` tuvo "
                f"{dd['reescrito']} párrafos reescritos por el letrado. Revisar patrones "
                f"en `{dd['fichero']}` y codificarlos en el SKILL.md."
            )
    # 4. Valoración media baja.
    vs = post_m["valoraciones"]
    if vs and (sum(vs) / len(vs)) < 3.0:
        props.append(
            f"**Valoración media baja** ({sum(vs)/len(vs):.1f}/5 en {len(vs)} actos). "
            f"Revisar los flancos señalados en los checklists post."
        )
    if not props:
        props.append("_Sin patrones accionables con los datos actuales. Acumular más usos/post._")
    return props


def render(skill: str, data: dict, post_m: dict, umbral: int, listo: bool) -> str:
    n = len(data["refs_con_post"])
    L: list[str] = [
        f"# Propuestas de mejora — {skill}",
        "",
        "> Generado por `scripts/motor_mejora.py`. Handoff a Claude Code: revisar, "
        "aplicar al `SKILL.md` las aprobadas, subir `version` y anotar el "
        "`## Changelog` citando la evidencia. Datos de expediente: no compartir.",
        "",
        f"- Usos totales: {len(data['usos'])}",
        f"- Refs con checklist post: {n} (umbral {umbral} → "
        f"{'LISTO' if listo else 'aún no'})",
        f"- Deltas disponibles: {len(data['deltas'])}",
        "",
        "## Señales agregadas",
        "",
        f"- Resultados: {dict(post_m['resultados']) or '—'}",
        f"- Valoración media: "
        + (f"{sum(post_m['valoraciones'])/len(post_m['valoraciones']):.1f}/5"
           if post_m["valoraciones"] else "—"),
        f"- Alegaciones no previstas registradas: {len(post_m['alegaciones'])}",
        "",
        "## Deltas por ref (reescrituras del letrado)",
        "",
    ]
    if data["deltas"]:
        L.append("| Ref | Añadido | Suprimido | Reescrito | Fichero |")
        L.append("|---|---|---|---|---|")
        for ref, dd in sorted(data["deltas"].items(), key=lambda kv: kv[1]["reescrito"], reverse=True):
            L.append(f"| {ref} | {dd['anadido']} | {dd['suprimido']} | {dd['reescrito']} | `{dd['fichero']}` |")
    else:
        L.append("_Sin deltas (aún no hay versiones _FIRMADO procesadas)._")
    L += ["", "## Propuestas (ancladas a datos)", ""]
    L += [f"{i}. {p}" for i, p in enumerate(_propuestas(skill, data, post_m), 1)]
    return "\n".join(L).rstrip() + "\n"


def ejecutar(skill: str, umbral: int = 5, force: bool = False) -> tuple[Path | None, bool]:
    data = cargar(skill)
    listo = len(data["refs_con_post"]) >= umbral
    if not listo and not force:
        print(f"[motor_mejora] {skill}: {len(data['refs_con_post'])}/{umbral} usos con post. "
              f"No se genera informe (usa --force para forzarlo).")
        return None, listo
    post_m = _metricas_post(data["posts"])
    data["dir"].mkdir(parents=True, exist_ok=True)
    destino = data["dir"] / f"MEJORAS_{skill}.md"
    destino.write_text(render(skill, data, post_m, umbral, listo), encoding="utf-8")
    print(f"[motor_mejora] informe -> {destino}")
    return destino, listo


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Genera MEJORAS_<skill>.md por umbral de uso.")
    p.add_argument("skill")
    p.add_argument("--umbral", type=int, default=5)
    p.add_argument("--force", action="store_true", help="Genera aunque no se alcance el umbral.")
    args = p.parse_args(argv)
    ejecutar(args.skill, args.umbral, args.force)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
