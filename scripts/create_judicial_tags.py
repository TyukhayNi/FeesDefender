"""Crea los tags que faltan en el grupo judicial (grupo 2) de sudespacho.

Uso:
    python -m scripts.create_judicial_tags [--dry-run]

En --dry-run imprime las líneas de constante que se crearían sin tocar el CRM.

Grupos a crear:
    Ciudad (azul #5b9bd1): MADRID, BARCELONA, VALENCIA, BILBAO,
                           SEVILLA, SAN SEBASTIÁN, SANTANDER
    Equipo (rojo #a32929): BiRS1, BiRS2, SaRS1, SeRS6, SSRR1, SSRS1,
                           VaRS5, BaCS10, MaRS11, MaRS12, MaRS13

Al terminar, el script imprime las líneas listas para añadir a
core/sudespacho_create.py bajo las secciones J_TAG_AZUL_* / J_TAG_ROJO_*.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Añadir raíz del proyecto al path cuando se ejecuta como script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.sudespacho_relations import (
    SudespachoRelationsError,
    create_tag_judicial,
)
from core.sync_sudespacho_legacy import SudespachoLegacyClient


# ---------------------------------------------------------------------------
# Tags a crear
# ---------------------------------------------------------------------------

CIUDAD_AZUL = [
    "MADRID",
    "BARCELONA",
    "VALENCIA",
    "BILBAO",
    "SEVILLA",
    "SAN SEBASTIÁN",
    "SANTANDER",
]

EQUIPO_ROJO = [
    "BiRS1",
    "BiRS2",
    "SaRS1",
    "SeRS6",
    "SSRR1",
    "SSRS1",
    "VaRS5",
    "BaCS10",
    "MaRS11",
    "MaRS12",
    "MaRS13",
]

COLOR_AZUL = "#5b9bd1"
COLOR_ROJO = "#a32929"


# ---------------------------------------------------------------------------
# Helpers para generar las constantes Python
# ---------------------------------------------------------------------------

def _var_name_ciudad(nombre: str) -> str:
    """'SAN SEBASTIÁN' → 'J_TAG_AZUL_SAN_SEBASTIAN'"""
    clean = (
        nombre
        .replace("Á", "A").replace("É", "E").replace("Í", "I")
        .replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N")
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        .replace(" ", "_")
    )
    return f"J_TAG_AZUL_{clean.upper()}"


def _var_name_equipo(nombre: str) -> str:
    """'MaRS11' → 'J_TAG_ROJO_MaRS11'"""
    return f"J_TAG_ROJO_{nombre}"


def _const_line(var: str, color: str, tag_id: str) -> str:
    return f'{var:<45} = "{color}___{tag_id}"'


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool) -> None:
    results: dict[str, dict[str, str]] = {
        "ciudad_azul": {},
        "equipo_rojo": {},
    }
    errors: list[str] = []

    if dry_run:
        print("=== DRY RUN — no se toca el CRM ===\n")
        print("# Líneas que se añadirían a core/sudespacho_create.py:\n")
        print("# -- Ciudad azul --")
        for nombre in CIUDAD_AZUL:
            var = _var_name_ciudad(nombre)
            print(f'# {_const_line(var, COLOR_AZUL, "????")}  # "{nombre}"')
        print("\n# -- Equipo rojo --")
        for nombre in EQUIPO_ROJO:
            var = _var_name_equipo(nombre)
            print(f'# {_const_line(var, COLOR_ROJO, "????")}  # "{nombre}"')
        return

    # Sesión compartida para todas las llamadas
    with SudespachoLegacyClient() as client:
        print(f"[INFO] Sesión legacy activa: {client._host}")

        print("\n--- Tags de ciudad (azul) ---")
        for nombre in CIUDAD_AZUL:
            try:
                tag_id = create_tag_judicial(nombre, COLOR_AZUL, client=client)
                results["ciudad_azul"][nombre] = tag_id
                var = _var_name_ciudad(nombre)
                print(f"  ✓ {nombre:<20} → ID={tag_id}  ({var})")
            except SudespachoRelationsError as exc:
                errors.append(f"CIUDAD '{nombre}': {exc}")
                print(f"  ✗ {nombre:<20} → ERROR: {exc}")

        print("\n--- Tags de equipo (rojo) ---")
        for nombre in EQUIPO_ROJO:
            try:
                tag_id = create_tag_judicial(nombre, COLOR_ROJO, client=client)
                results["equipo_rojo"][nombre] = tag_id
                var = _var_name_equipo(nombre)
                print(f"  ✓ {nombre:<20} → ID={tag_id}  ({var})")
            except SudespachoRelationsError as exc:
                errors.append(f"EQUIPO '{nombre}': {exc}")
                print(f"  ✗ {nombre:<20} → ERROR: {exc}")

    # Guardar JSON de resultados
    out_json = Path(__file__).parent.parent / "docs" / "judicial_tags_creados.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[INFO] IDs guardados en {out_json}")

    # Imprimir constantes listas para pegar
    print("\n" + "=" * 65)
    print("# CONSTANTES PARA core/sudespacho_create.py")
    print("=" * 65)

    if results["ciudad_azul"]:
        print("\n# -- Ciudad (azul, #5b9bd1) — añadir tras J_TAG_AZUL_VaCS1 --")
        for nombre, tag_id in results["ciudad_azul"].items():
            var = _var_name_ciudad(nombre)
            print(_const_line(var, COLOR_AZUL, tag_id))

    if results["equipo_rojo"]:
        print("\n# -- Equipo (rojo, #a32929) — añadir en sección J_TAG_ROJO_* --")
        for nombre, tag_id in results["equipo_rojo"].items():
            var = _var_name_equipo(nombre)
            print(_const_line(var, COLOR_ROJO, tag_id))

    if errors:
        print(f"\n[ERRORES] {len(errors)} tag(s) no creados:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"\n[OK] {len(results['ciudad_azul']) + len(results['equipo_rojo'])} tags creados sin errores.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra qué se crearía")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
