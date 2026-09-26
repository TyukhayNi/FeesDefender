"""Diagnóstico de auto-fill desde URL de Drive E&V.

Reproduce paso a paso la cadena que ejecuta `streamlit_app.py` cuando el
usuario pega la URL de la carpeta W-XXXXXX, y muestra dónde se rompe.

Uso:
    python -m scripts.diag_drive_autofill "<URL o folder_id>"

Si no se pasa argumento, usa la URL del caso que está dando problemas:
    https://drive.google.com/drive/u/2/folders/1ARbjPzfix-RbYi2o2ZgoZ8W5FMBkP9Oa

**No imprime nada del token** (R1/H-06 de la fila #42, `MEJORAS #296`): hasta el 2026-09-26
escribía los primeros 30 caracteres del access_token, antes y después de renovarlo, y lo leía con
su propia copia de `rclone config show` (5 s; un remote inexistente pasaba por existente, porque
rclone sale con 0). Ahora usa el lector único, `obtener_token_drive`, y dice su motivo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Permite ejecutar sin -m si hace falta
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.config import DRIVE_EV_TEAM_IDS  # noqa: E402
from core.intake_drive import (  # noqa: E402
    obtener_token_drive,
    parse_drive_url,
    parse_ev_folder_name,
)


DEFAULT_URL = (
    "https://drive.google.com/drive/u/2/folders/1ARbjPzfix-RbYi2o2ZgoZ8W5FMBkP9Oa"
)


def step(title: str) -> None:
    print()
    print("─" * 78)
    print(title)
    print("─" * 78)


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    print(f"Input: {url}")

    # ── 1. parse_drive_url ─────────────────────────────────────────────────
    step("1. parse_drive_url(url) — extracción del folder_id")
    try:
        folder_id = parse_drive_url(url)
        print(f"  ✅ folder_id = {folder_id}")
    except ValueError as e:
        print(f"  ❌ {e}")
        return 1

    # ── 2-3. El token de gdrive_ev, con el lector de la pieza (renueva si hace falta) ──
    step("2. Token de gdrive_ev (obtener_token_drive: lee, y renueva si caduca)")
    lectura = obtener_token_drive()
    if not lectura.token:
        print(f"  ❌ sin token: {lectura.motivo}")
        return 1
    # Solo que lo hay: ni un carácter del token, que es una credencial.
    print("  ✅ hay access_token vigente")
    access_token = lectura.token

    # ── 4. Llamada a la Drive API v3 ───────────────────────────────────────
    step("4. GET https://www.googleapis.com/drive/v3/files/{folder_id}")
    try:
        import httpx
        resp = httpx.get(
            f"https://www.googleapis.com/drive/v3/files/{folder_id}",
            params={
                "fields": "id,name,driveId,mimeType,parents",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        print(f"  HTTP {resp.status_code}")
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001
            body = {"_raw": resp.text}
        print(f"  body: {json.dumps(body, ensure_ascii=False, indent=2)}")
        if resp.status_code != 200:
            print("  ❌ La Drive API no devolvió 200 → auto-fill se aborta.")
            return 1
        name = body.get("name", "")
        drive_id = body.get("driveId", "")
    except Exception as e:  # noqa: BLE001
        print(f"  ❌ excepción HTTP: {e!r}")
        return 1

    # ── 5. parse_ev_folder_name ────────────────────────────────────────────
    step("5. parse_ev_folder_name(name) — extracción de dirección + ID GO")
    direccion, mls = parse_ev_folder_name(name)
    print(f"  nombre carpeta : {name!r}")
    print(f"  → dirección    : {direccion!r}")
    print(f"  → ID GO        : {mls!r}")
    if not direccion and not mls:
        print(
            "  ⚠️ El nombre de la carpeta NO encaja con ninguno de los dos patrones\n"
            "     «<dirección> - W-XXXXXX[ - consultor]» ni «W-XXXXXX - <dirección>[ - consultor]»\n"
            "     — el auto-fill de dirección/ID GO no se aplicará."
        )

    # ── 6. Resolución de equipo a partir del driveId ───────────────────────
    step("6. Lookup del Shared Drive en DRIVE_EV_TEAM_IDS")
    print(f"  driveId devuelto por API: {drive_id!r}")
    if not drive_id:
        print("  ⚠️ La API no devolvió driveId — la carpeta podría no estar")
        print("     en un Shared Drive (My Drive personal).")
    else:
        reverse = {v: k for k, v in DRIVE_EV_TEAM_IDS.items()}
        equipo_code = reverse.get(drive_id)
        if equipo_code:
            print(f"  ✅ equipo detectado: {equipo_code}")
        else:
            print("  ❌ El driveId NO está mapeado en DRIVE_EV_TEAM_IDS.")
            print("     → la ciudad y el equipo NO se auto-rellenarán.")
            print("     Posible causa: equipo nuevo no registrado en core/config.py")

    print()
    print("=" * 78)
    print("Diagnóstico terminado.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
