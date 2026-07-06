# -*- coding: utf-8 -*-
"""Programa la revisión post-acto de una skill (helper canónico, mejora continua).

Generaliza a todas las skills procesales el patrón de
``preparacion-juicio-oral/scripts/schedule_post_juicio.js``: emite un descriptor
de tarea para la skill ``schedule`` que, llegada la fecha, pide a Cowork rellenar
el checklist *post* y correr ``scripts/capturar_delta.py``.

Plazos por tipo de acto (decisión del despacho, plan v3 §16):
  · audiencia previa (``ap``)   → fecha_acto + 3 días
  · juicio (``juicio``)         → fecha_acto + 7 días
  · escrito (``escrito``)       → presentación + 15 días (o al detectar _FIRMADO)

Stdlib pura, autónomo (bundleable). Escribe el descriptor en
``<store>/<skill>/<ref>_schedule.json`` y lo imprime para activarlo con la skill
``schedule``. Best-effort: si la escritura falla, avisa pero no rompe nada.

Uso:
  python programar_revision.py <skill> <ref> --tipo-acto ap|juicio|escrito
                               --fecha 2026-07-01 [--borrador ruta/ESCRITO.docx]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

_HERE = Path(__file__).resolve()

DIAS_POR_ACTO: dict[str, int] = {"ap": 3, "juicio": 7, "escrito": 15}


def _store_dir(skill: str) -> Path:
    env = os.environ.get("FEESDEFENDER_SKILL_LOGS")
    if env:
        return Path(env) / skill
    for parent in _HERE.parents:
        if (parent / "pyproject.toml").exists():
            return parent / "data" / "_skill_logs" / skill
    return _HERE.parent.parent / "logs"


def fecha_revision(tipo_acto: str, fecha_evento: str) -> str:
    if tipo_acto not in DIAS_POR_ACTO:
        raise ValueError(f"tipo-acto no válido: {tipo_acto!r}. Usa: {', '.join(DIAS_POR_ACTO)}")
    base = date.fromisoformat(fecha_evento)
    return (base + timedelta(days=DIAS_POR_ACTO[tipo_acto])).isoformat()


def construir_descriptor(skill: str, ref: str, tipo_acto: str, fecha_evento: str,
                         borrador: str | None) -> dict:
    fire_at = fecha_revision(tipo_acto, fecha_evento)
    delta = ""
    if borrador:
        delta = (f" Si existe la versión firmada, corre "
                 f"`python scripts/capturar_delta.py {skill} {ref} --borrador \"{borrador}\"`.")
    prompt = (
        f"Revisión post-{tipo_acto} de la skill {skill} (ref {ref}). "
        f"(1) Rellena el checklist post y regístralo: "
        f"`python scripts/registrar_uso.py {skill} {ref} checklist_post --fase post "
        f"--metricas '<json>'`. "
        f"(2) Anota qué fijó realmente el juez / prueba admitida o inadmitida / "
        f"pregunta no prevista / valoración del acto.{delta}"
    )
    return {
        "taskId": f"revision-{skill}-{ref}",
        "fireAt": fire_at,
        "tipo_acto": tipo_acto,
        "skill": skill,
        "ref": ref,
        "fecha_evento": fecha_evento,
        "description": f"Revisión post-{tipo_acto} ({skill} · {ref}) — cierre del bucle de mejora",
        "prompt": prompt,
    }


def programar(skill: str, ref: str, tipo_acto: str, fecha_evento: str,
              borrador: str | None = None) -> tuple[dict, Path | None]:
    descriptor = construir_descriptor(skill, ref, tipo_acto, fecha_evento, borrador)
    try:
        d = _store_dir(skill)
        d.mkdir(parents=True, exist_ok=True)
        destino = d / f"{ref}_schedule.json"
        destino.write_text(json.dumps(descriptor, ensure_ascii=False, indent=2), encoding="utf-8")
        return descriptor, destino
    except Exception as e:  # best-effort
        print(f"[programar_revision] aviso: no se pudo escribir el descriptor ({e})", file=sys.stderr)
        return descriptor, None


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Programa la revisión post-acto (skill schedule).")
    p.add_argument("skill")
    p.add_argument("ref")
    p.add_argument("--tipo-acto", required=True, choices=sorted(DIAS_POR_ACTO))
    p.add_argument("--fecha", required=True, help="Fecha del acto/presentación (YYYY-MM-DD).")
    p.add_argument("--borrador", default=None, help="Ruta del borrador, para el delta posterior.")
    args = p.parse_args(argv)
    descriptor, destino = programar(args.skill, args.ref, args.tipo_acto, args.fecha, args.borrador)
    print(f"[programar_revision] revisión el {descriptor['fireAt']} (+{DIAS_POR_ACTO[args.tipo_acto]}d)")
    if destino:
        print(f"[programar_revision] descriptor -> {destino}")
    print("\nActiva la tarea con la skill `schedule` usando este prompt:")
    print(descriptor["prompt"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
