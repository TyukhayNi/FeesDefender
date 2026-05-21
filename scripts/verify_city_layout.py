"""Verificación del filesystem post-migración por ciudades.

Comprueba dos invariantes del plan ``docs/PLAN_SUBDIVISION_CIUDADES.md`` §10:

1. **Sin huérfanos en raíz**: ninguna carpeta-expediente vive directamente
   bajo ``CASOS_ROOT/`` — todas deben estar bajo una ciudad o ``_Sin
   clasificar``. ``_PLANTILLA``, ``_audit`` y similares son carpetas de
   sistema (prefijo ``_``) y se excluyen.

2. **Metadato coherente**: para cada expediente bajo ``<Ciudad>/<case_id>/``,
   el campo ``ciudad`` del frontmatter de ``00_Input/_caso.md`` debe
   coincidir con la carpeta padre. Si falta ``_caso.md`` se reporta como
   warning (no es bloqueante — el caso puede ser muy temprano y aún no
   haber pasado por ``register_expediente``).

Uso:

    python -m scripts.verify_city_layout

Sale con código 0 si todo OK, código 1 si hay incidencias.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from core.casos.case_locator import _CITY_NAMES
from core.ciudades import es_carpeta_de_sistema
from core.config import settings


def _leer_ciudad_caso_md(case_dir: Path) -> str | None:
    """Devuelve el campo ``ciudad`` del frontmatter de ``_caso.md`` o None."""
    index = case_dir / "00_Input" / "_caso.md"
    if not index.exists():
        return None
    text = index.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    fm = yaml.safe_load(parts[1]) or {}
    ciudad = fm.get("ciudad")
    if ciudad:
        return ciudad
    meta = fm.get("meta")
    if isinstance(meta, dict):
        return meta.get("ciudad")
    return None


def verify(root: Path) -> tuple[list[str], list[str]]:
    """Devuelve (errores, avisos) tras recorrer ``root``."""
    errores: list[str] = []
    avisos: list[str] = []

    if not root.is_dir():
        return [f"CASOS_ROOT no existe: {root}"], []

    huerfanos = [
        p.name for p in root.iterdir()
        if p.is_dir()
        and not es_carpeta_de_sistema(p.name)
        and p.name not in _CITY_NAMES
    ]
    for h in huerfanos:
        errores.append(f"HUÉRFANO en raíz: {h!r} — debería estar bajo una ciudad")

    for city_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if city_dir.name not in _CITY_NAMES:
            continue
        for case_dir in sorted(p for p in city_dir.iterdir() if p.is_dir()):
            ciudad_md = _leer_ciudad_caso_md(case_dir)
            if ciudad_md is None:
                avisos.append(
                    f"SIN _caso.md: {city_dir.name}/{case_dir.name}"
                )
                continue
            if ciudad_md != city_dir.name:
                errores.append(
                    f"INCOHERENTE: {city_dir.name}/{case_dir.name} — "
                    f"_caso.md dice ciudad={ciudad_md!r}"
                )

    return errores, avisos


def main() -> int:
    root = settings.casos_root
    print(f"Verificando layout de {root}...")
    errores, avisos = verify(root)

    if avisos:
        print(f"\n{len(avisos)} aviso(s):")
        for a in avisos:
            print(f"  - {a}")

    if errores:
        print(f"\n{len(errores)} error(es):")
        for e in errores:
            print(f"  - {e}")
        print("\nFAIL — el filesystem no cumple los invariantes de la Fase 6.")
        return 1

    print("\nOK — layout coherente (sin huérfanos, metadatos cuadran).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
