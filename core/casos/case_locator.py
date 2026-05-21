"""Localización de expedientes con tolerancia a layout flat y por ciudades.

Única puerta de entrada para resolver rutas de expedientes. Tolera dos layouts:

- **Flat (legacy):** ``CASOS_ROOT/<case_id>/``
- **Por ciudades:** ``CASOS_ROOT/<Ciudad>/<case_id>/``

Plan: ``docs/PLAN_SUBDIVISION_CIUDADES.md`` (Fase 1).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from core.ciudades import CIUDADES, es_carpeta_de_sistema

_FALLBACK_CITY = "_Sin clasificar"
_CITY_NAMES: frozenset[str] = frozenset(CIUDADES) | {_FALLBACK_CITY}


def _root() -> Path:
    from core.config import settings
    return settings.casos_root


def path_for(case_id: str) -> Path:
    """Devuelve la ruta a un expediente, buscando en flat y luego por ciudades.

    Si el expediente no existe en ninguna ubicación, devuelve la ruta flat
    (compatible con creación de casos nuevos).
    """
    root = _root()
    flat = root / case_id
    if flat.is_dir():
        return flat
    for city in sorted(CIUDADES):
        candidate = root / city / case_id
        if candidate.is_dir():
            return candidate
    candidate = root / _FALLBACK_CITY / case_id
    if candidate.is_dir():
        return candidate
    return flat


def path_for_ciudad(case_id: str, ciudad: str) -> Path:
    """Calcula la ruta esperada de un expediente en una ciudad concreta.

    No comprueba existencia — uso principal: creación de casos nuevos
    y migración.
    """
    return _root() / ciudad / case_id


def move_to_city(
    case_id: str,
    ciudad_destino: str,
    motivo: str,
    usuario: str,
) -> Path:
    """Mueve un expediente a una carpeta de ciudad.

    Ejecuta atómicamente:
    1. Mover carpeta.
    2. Actualizar metadato ``ciudad`` en ``_caso.md``.
    3. Escribir audit log.

    Si falla el paso 2 o 3, revierte el movimiento de carpeta.

    Raises:
        ValueError: motivo menor de 10 caracteres.
        FileNotFoundError: caso no encontrado.
    """
    import shutil

    if len((motivo or "").strip()) < 10:
        raise ValueError("El motivo debe tener al menos 10 caracteres.")

    src = path_for(case_id)
    if not src.is_dir():
        raise FileNotFoundError(f"Caso '{case_id}' no encontrado.")

    dest = path_for_ciudad(case_id, ciudad_destino)
    if src == dest:
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))

    try:
        _update_ciudad_metadata(dest, ciudad_destino)
        append_audit_log({
            "operacion": "reasignar_ciudad",
            "case_id": case_id,
            "ciudad_origen": src.parent.name if src.parent != _root() else "(raíz)",
            "ciudad_destino": ciudad_destino,
            "motivo": motivo.strip(),
            "usuario": usuario,
        })
    except Exception:
        shutil.move(str(dest), str(src))
        raise

    return dest


def _update_ciudad_metadata(case_dir: Path, ciudad: str) -> None:
    """Actualiza el campo ``ciudad`` en el frontmatter de ``_caso.md``."""
    import yaml

    index = case_dir / "00_Input" / "_caso.md"
    if not index.exists():
        return
    text = index.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return
    parts = text.split("---", 2)
    if len(parts) < 3:
        return
    fm = yaml.safe_load(parts[1]) or {}
    fm["ciudad"] = ciudad
    meta = fm.get("meta")
    if isinstance(meta, dict):
        meta["ciudad"] = ciudad
    new_text = "---\n" + yaml.dump(fm, allow_unicode=True, default_flow_style=False) + "---" + parts[2]
    index.write_text(new_text, encoding="utf-8")


def list_cases(ciudad: str | None = None) -> Iterator[Path]:
    """Itera directorios de expedientes.

    Sin argumento: devuelve todos (flat + por ciudades).
    Con ``ciudad``: solo los de esa ciudad.
    """
    root = _root()
    if not root.is_dir():
        return
    if ciudad is not None:
        city_dir = root / ciudad
        if city_dir.is_dir():
            yield from sorted(
                (p for p in city_dir.iterdir() if p.is_dir()),
                key=lambda p: p.name,
            )
        return

    seen: set[str] = set()
    for p in sorted(root.iterdir(), key=lambda p: p.name):
        if not p.is_dir():
            continue
        if es_carpeta_de_sistema(p.name):
            continue
        if p.name in _CITY_NAMES:
            for child in sorted(p.iterdir(), key=lambda c: c.name):
                if child.is_dir() and child.name not in seen:
                    seen.add(child.name)
                    yield child
        else:
            if p.name not in seen:
                seen.add(p.name)
                yield p


def all_cities_present() -> list[str]:
    """Devuelve las ciudades que tienen al menos un expediente."""
    root = _root()
    result: list[str] = []
    for city in sorted(_CITY_NAMES):
        city_dir = root / city
        if city_dir.is_dir() and any(c.is_dir() for c in city_dir.iterdir()):
            result.append(city)
    return result


def append_audit_log(entry: dict) -> None:
    """Añade una entrada JSONL al log de auditoría ``_audit/relocations.jsonl``."""
    import json
    from datetime import datetime, timezone

    audit_dir = _root() / "_audit"
    audit_dir.mkdir(exist_ok=True)
    log_path = audit_dir / "relocations.jsonl"
    entry.setdefault("ts", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
