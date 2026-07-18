#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validador de conformidad de las skills del despacho — **modo AVISO**.

Se corre a mano (``python scripts/validate_skills.py``). **No bloquea** commits ni
hay hook/CI: solo informa de no conformidades respecto al estándar de
``.claude/skills/_shared/_plantilla-skill/`` (ejes ``rol``/``naturaleza``,
identidad, licencia, helpers canónicos del módulo OPERACIÓN).

Es un *termómetro*: con el retrofit de identidad diferido (ver PLAN.md), muchas
skills aún no declararán ``rol``/``naturaleza`` — el validador lo refleja sin
romper nada. Siempre devuelve **exit 0**.

Uso:
  python scripts/validate_skills.py            # informe legible
  python scripts/validate_skills.py --strict   # exit 1 si hay avisos (para uso manual; NO en hooks)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_SKILLS = _REPO / ".claude" / "skills"

# Skills genéricas de terceros (Anthropic): no las gobierna el estándar del despacho.
_GENERICAS = {"docx", "pdf", "xlsx", "pptx"}

_ROLES = {"transversal", "fase", "cliente", "output", "input", "procesado"}
_NATURALEZAS = {"atomica", "orquestadora"}
_ESTADOS = {"vigente", "deprecada", "experimental"}

# Reutiliza la fuente única de targets/helpers del sincronizador.
sys.path.insert(0, str(_HERE))
import sync_skill_helpers as ssh  # noqa: E402


def _canonical_helpers() -> list[str]:
    return [p.name for p in ssh._shared_helpers()]


def _operacion_dirs() -> set[str]:
    """Nombres de skill que reciben helpers canónicos (módulo OPERACIÓN)."""
    nombres = set()
    for rel in ssh._TARGETS:
        # rel == ".claude/skills/<skill>/scripts"
        nombres.add(Path(rel).parent.name)
    return nombres


def _leer_frontmatter(skill_md: Path) -> tuple[dict | None, str | None]:
    """Devuelve (frontmatter_dict, error). El dict es {} si no hay bloque."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"no se pudo leer SKILL.md ({e})"
    if not text.startswith("---"):
        return {}, "SKILL.md sin bloque frontmatter"
    partes = text.split("---", 2)
    if len(partes) < 3:
        return {}, "frontmatter sin cierre '---'"
    try:
        data = yaml.safe_load(partes[1]) or {}
    except yaml.YAMLError as e:
        return None, f"frontmatter YAML inválido ({e})"
    if not isinstance(data, dict):
        return None, "frontmatter no es un mapa"
    return data, None


def validar_skill(skill_dir: Path, helpers: list[str], operacion: set[str]) -> list[str]:
    """Devuelve la lista de avisos (vacía = conforme)."""
    avisos: list[str] = []
    nombre = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"falta SKILL.md"]

    fm, err = _leer_frontmatter(skill_md)
    if err:
        avisos.append(err)
    if not fm:
        return avisos or ["frontmatter vacío"]

    if fm.get("name") != nombre:
        avisos.append(f"name='{fm.get('name')}' ≠ carpeta '{nombre}'")
    desc = fm.get("description")
    if not desc:
        avisos.append("falta description")
    elif len(str(desc)) > 1024:
        avisos.append(f"description > 1024 chars ({len(str(desc))})")
    if desc and re.search(r"<[^>\s][^>]*>", str(desc)):
        avisos.append("description contiene etiqueta(s) tipo XML `<...>` (Cowork rechaza la importación)")
    if "license" not in fm:
        avisos.append("falta 'license' de primer nivel")

    meta = fm.get("metadata")
    if not isinstance(meta, dict):
        avisos.append("falta bloque 'metadata'")
        meta = {}

    rol = meta.get("rol")
    if rol is None:
        avisos.append("metadata.rol ausente (eje pendiente de retrofit)")
    elif rol not in _ROLES:
        avisos.append(f"metadata.rol='{rol}' no válido ({sorted(_ROLES)})")
    nat = meta.get("naturaleza")
    if nat is None:
        avisos.append("metadata.naturaleza ausente (eje pendiente de retrofit)")
    elif nat not in _NATURALEZAS:
        avisos.append(f"metadata.naturaleza='{nat}' no válido ({sorted(_NATURALEZAS)})")

    if "version" not in meta:
        avisos.append("metadata.version ausente")
    elif not isinstance(meta["version"], str):
        avisos.append(f"metadata.version sin comillas (interpretado como {type(meta['version']).__name__})")
    estado = meta.get("status")
    if estado is not None and estado not in _ESTADOS:
        avisos.append(f"metadata.status='{estado}' no válido ({sorted(_ESTADOS)})")

    # Módulo OPERACIÓN: helpers canónicos presentes.
    if nombre in operacion:
        scripts = skill_dir / "scripts"
        for h in helpers:
            if not (scripts / h).exists():
                avisos.append(f"módulo OPERACIÓN: falta scripts/{h}")
    return avisos


def main(argv: list[str]) -> int:
    helpers = _canonical_helpers()
    operacion = _operacion_dirs()
    skills = sorted(
        d for d in _SKILLS.iterdir()
        if d.is_dir() and not d.name.startswith("_") and d.name not in _GENERICAS
        and (d / "SKILL.md").exists()
    )
    total_avisos = 0
    conformes = 0
    print("Validación de skills (modo AVISO) — no bloquea commits.\n")
    for d in skills:
        avisos = validar_skill(d, helpers, operacion)
        marca = "OK " if not avisos else "!! "
        etiqueta = " [OPERACIÓN]" if d.name in operacion else ""
        print(f"{marca}{d.name}{etiqueta}")
        for a in avisos:
            print(f"     - {a}")
        total_avisos += len(avisos)
        conformes += 0 if avisos else 1
    print(f"\n{conformes}/{len(skills)} skills conformes · {total_avisos} avisos en total.")
    if "--strict" in argv:
        return 1 if total_avisos else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
