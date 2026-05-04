"""Lee el formulario de alta judicial y extrae todos los tags del grupo judicial.

Uso:
    python -m scripts.audit_judicial_tags

Salida en consola: tabla nombre | ID | token completo
Fichero: docs/judicial_tags_actuales.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

try:
    import httpx
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx

_HOST = os.getenv("SUDESPACHO_LEGACY_HOST", "tnm.sudespacho.net")
_PHPSESSID = os.getenv("SUDESPACHO_LEGACY_PHPSESSID", "")
_FORM_URL = f"https://{_HOST}/expedientesjudiciales/add/elemento/expedientes_judiciales"
_OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "judicial_tags_actuales.json"

_COLOR_LABEL = {
    "#528800": "VERDE",
    "#5229a3": "LILA",
    "#a32929": "ROJO",
    "#5b9bd1": "AZUL",
}


def main() -> None:
    if not _PHPSESSID:
        print("❌ SUDESPACHO_LEGACY_PHPSESSID no está configurada en .env")
        sys.exit(1)

    print(f"Conectando a {_FORM_URL} ...")
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            _FORM_URL,
            headers={"Cookie": f"PHPSESSID={_PHPSESSID}"},
            follow_redirects=True,
        )

    if resp.status_code != 200 or "/login" in str(resp.url):
        print(f"❌ Sesión expirada o error HTTP {resp.status_code}.")
        print("   Renueva SUDESPACHO_LEGACY_PHPSESSID en .env")
        sys.exit(1)

    html = resp.text

    # Buscar el bloque del <select> campo_2486
    block = re.search(
        r'id=["\']campo_2486["\'][^>]*>(.*?)</select>',
        html,
        re.DOTALL | re.IGNORECASE,
    )

    if block:
        # Extraer <option value="TOKEN">NOMBRE</option> dentro del select
        opts = re.findall(
            r'<option[^>]+value="(#[0-9a-fA-F]{6}___\d+)"[^>]*>\s*([^<]+?)\s*</option>',
            block.group(1),
            re.IGNORECASE,
        )
    else:
        # Fallback: buscar todos en el HTML
        opts = re.findall(
            r'<option[^>]+value="(#[0-9a-fA-F]{6}___\d+)"[^>]*>\s*([^<]+?)\s*</option>',
            html,
            re.IGNORECASE,
        )

    if not opts:
        print("⚠️  No se encontraron tags. Comprueba que la sesión es válida.")
        sys.exit(1)

    # Agrupar por color
    by_color: dict[str, list[dict]] = {}
    for token, nombre in opts:
        color = token.split("___")[0]
        tag_id = token.split("___")[1]
        label = _COLOR_LABEL.get(color, color)
        by_color.setdefault(label, []).append(
            {"id": tag_id, "nombre": nombre.strip(), "token": token, "color": color}
        )

    total = sum(len(v) for v in by_color.values())
    print(f"\n{'='*72}")
    print(f"  TAGS JUDICIALES — {total} tags encontrados")
    print(f"{'='*72}\n")

    for label in ("VERDE", "LILA", "ROJO", "AZUL"):
        tags = sorted(by_color.get(label, []), key=lambda x: x["nombre"])
        if not tags:
            continue
        hex_color = [k for k, v in _COLOR_LABEL.items() if v == label][0]
        print(f"── {label} ({hex_color}) — {len(tags)} tags ──")
        for t in tags:
            print(f"  {t['id']:>4}  {t['nombre']:<40}  {t['token']}")
        print()

    # Guardar JSON
    all_tags = [t for tags in by_color.values() for t in tags]
    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"total": total, "tags": sorted(all_tags, key=lambda x: (x["color"], x["nombre"]))},
                  f, ensure_ascii=False, indent=2)
    print(f"✅ JSON guardado en {_OUTPUT.name}")
    print()

    # Constantes listas para copiar
    print(f"{'='*72}")
    print("  CONSTANTES — copia en core/sudespacho_create.py")
    print(f"{'='*72}\n")

    for label in ("VERDE", "LILA", "ROJO", "AZUL"):
        tags = sorted(by_color.get(label, []), key=lambda x: x["nombre"])
        if not tags:
            continue
        hex_color = [k for k, v in _COLOR_LABEL.items() if v == label][0]
        print(f"# -- {label} ({hex_color}) --")
        for t in tags:
            safe = re.sub(r"[^A-Z0-9]", "_", t["nombre"].upper())
            safe = re.sub(r"_+", "_", safe).strip("_")
            const = f"J_TAG_{label}_{safe}"
            print(f'{const:<58} = "{t["token"]}"   # {t["nombre"]}')
        print()


if __name__ == "__main__":
    main()
