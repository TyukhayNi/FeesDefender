# -*- coding: utf-8 -*-
"""Telemetría de uso de las skills procesales (helper canónico, mejora continua).

HELPER CANÓNICO en ``.claude/skills/_shared/``, copiado byte a byte a cada skill
por ``scripts/sync_skill_helpers.py``. Stdlib pura, autónomo (ejecutable dentro
de un ``.skill`` empaquetado, también en móvil).

Escribe una línea JSON por evento en ``<logdir>/uso.jsonl`` (o
``<logdir>/<ref>_<fase>.jsonl`` para checklists pre/post). Cada línea:
``{ts (ISO-8601 UTC), skill, version, ref, accion, archivos, metricas}``.

Resolución del directorio de logs (en orden):
  1. Variable de entorno ``FEESDEFENDER_SKILL_LOGS`` → ``<base>/<skill>/``.
  2. Repo detectado subiendo desde el script (marcador ``pyproject.toml``) →
     ``<repo>/data/_skill_logs/<skill>/``.
  3. *Fallback* portable (móvil / skill instalada suelta): ``../logs/`` de la skill.

Best-effort: si el log falla, avisa por stderr pero **nunca** rompe la generación.

Uso CLI:
  python registrar_uso.py <skill> <ref> <accion> [--archivos a.docx b.docx]
                          [--metricas '{"testigos": 3}'] [--fase pre|post|uso]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()


def _detectar_repo() -> Path | None:
    """Sube desde el script buscando el marcador del repo (``pyproject.toml``)."""
    for parent in _HERE.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def log_dir(skill: str) -> Path:
    """Resuelve el directorio de logs para ``skill`` según el orden documentado."""
    env = os.environ.get("FEESDEFENDER_SKILL_LOGS")
    if env:
        return Path(env) / skill
    repo = _detectar_repo()
    if repo is not None:
        return repo / "data" / "_skill_logs" / skill
    # Fallback portable: la carpeta logs/ de la propia skill (../logs desde scripts/).
    return _HERE.parent.parent / "logs"


def skill_version(skill_dir: Path | None = None) -> str:
    """Lee ``version:`` del frontmatter de ``SKILL.md`` (../SKILL.md). Def. '0.0'."""
    base = skill_dir or _HERE.parent.parent
    skill_md = base / "SKILL.md"
    if not skill_md.exists():
        return "0.0"
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return "0.0"
    in_fm = False
    for line in text.splitlines():
        if line.strip() == "---":
            if in_fm:
                break
            in_fm = True
            continue
        if in_fm and line.lower().startswith("version:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'") or "0.0"
    return "0.0"


def log(
    skill: str,
    ref: str,
    accion: str,
    *,
    archivos: list[str] | None = None,
    metricas: dict | None = None,
    fase: str = "uso",
    version: str | None = None,
) -> Path | None:
    """Anexa un evento JSONL. Devuelve la ruta escrita, o ``None`` si falló (best-effort)."""
    try:
        d = log_dir(skill)
        d.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "skill": skill,
            "version": version if version is not None else skill_version(),
            "ref": ref,
            "accion": accion,
            "archivos": archivos or [],
            "metricas": metricas or {},
        }
        fichero = "uso.jsonl" if fase == "uso" else f"{ref}_{fase}.jsonl"
        path = d / fichero
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return path
    except Exception as e:  # best-effort: nunca rompe la generación del .docx
        print(f"[registrar_uso] aviso: no se pudo registrar ({e})", file=sys.stderr)
        return None


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Registra un evento de uso de una skill (JSONL).")
    p.add_argument("skill")
    p.add_argument("ref")
    p.add_argument("accion")
    p.add_argument("--archivos", nargs="*", default=None)
    p.add_argument("--metricas", default=None, help="JSON con métricas del evento.")
    p.add_argument("--fase", default="uso", choices=["uso", "pre", "post"])
    args = p.parse_args(argv)
    metricas = json.loads(args.metricas) if args.metricas else None
    path = log(args.skill, args.ref, args.accion, archivos=args.archivos,
               metricas=metricas, fase=args.fase)
    if path:
        print(f"[registrar_uso] {args.fase} -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
