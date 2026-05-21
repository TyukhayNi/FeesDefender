"""Auditoría de naming de carpetas en los Shared Drives de Engel & Völkers.

Recorre todos los Shared Drives mapeados en ``core.config.DRIVE_EV_TEAM_IDS``,
lista las primeras N carpetas de cada uno, y aplica ``parse_ev_folder_name``
a cada nombre. Reporta los equipos cuyo naming no encaja con el patrón
esperado «Dirección - W-XXXXXX[ - <consultor captador>]».

NO modifica nada. Solo lectura.

Reutiliza ``_get_drive_access_token`` (con renovación proactiva) y la lógica
de retry on rate-limit ya implementadas en ``core/intake_drive.py``.

Uso::

    python -m scripts.audit_ev_folder_names               # todos los equipos
    python -m scripts.audit_ev_folder_names --limit 10    # 10 carpetas/drive
    python -m scripts.audit_ev_folder_names --team BaRS1  # filtrado
    python -m scripts.audit_ev_folder_names --json        # + reporte JSON

Códigos de salida:

* 0  → todos los nombres parsean OK.
* 1  → al menos un nombre falla en al menos un equipo (revisar regex).
* 2  → error de token / sin acceso / configuración mal.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Forzar UTF-8 en stdout (PowerShell con `2>&1 | …` por defecto cae en cp1252
# y peta con caracteres Unicode). Defensivo: si reconfigure falla, sigue
# adelante con ASCII puro en los separadores.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Importar core.config primero para que dotenv cargue .env.
from core.config import DRIVE_EV_TEAM_IDS  # noqa: E402
from core.intake_drive import (  # noqa: E402
    _RATE_LIMIT_BACKOFF_SECONDS,
    _get_drive_access_token,
    _is_rate_limit_response,
    parse_ev_folder_name,
)

_DRIVE_API_FILES = "https://www.googleapis.com/drive/v3/files"

# Regex laxo para detectar candidatos a carpeta-expediente: nombre que
# contenga la cadena W-XXXXXX en cualquier parte. NO valida la estructura
# completa — eso lo hace `parse_ev_folder_name` después. Sirve para filtrar
# ruido (carpetas estructurales como "PROPIEDADES", "S1", "Otros tutoriales")
# antes de aplicar el regex estricto.
_W_ID_PROBE = re.compile(r"\bW-[A-Z0-9]{5,8}\b", re.IGNORECASE)

# Cuántos resultados pedir a Drive API por drive (antes del filtro local).
# Las raíces de los Shared Drives de E&V mezclan carpetas estructurales y
# carpetas-expediente; pedir un page grande aumenta la probabilidad de
# capturar muestras representativas tras el filtro.
_DRIVE_API_PAGE_SIZE = 50


def _list_drive_folders(
    drive_id: str,
    access_token: str,
    *,
    limit: int,
) -> tuple[list[dict] | None, str | None]:
    """Lista las primeras `limit` carpetas (no eliminadas) de un Shared Drive.

    Returns:
        (folders, error_msg). Si ``folders`` es None, ``error_msg`` describe
        el motivo (auth, red, rate-limit persistente, etc.).
    """
    try:
        import httpx
    except ImportError:
        return None, "httpx no instalado"

    # En E&V las carpetas-expediente W-XXXXXX NO viven necesariamente en la
    # raíz del Shared Drive — varios drives (p.ej. BaRS1) las tienen anidadas
    # bajo carpetas estructurales como "PROPIEDADES", "S1" o "Otros tutoriales".
    # Por eso buscamos por NOMBRE (`name contains 'W-'`) a cualquier
    # profundidad y luego filtramos en Python con `_W_ID_PROBE`. `pageSize`
    # se eleva sobre `limit` para tener candidatos suficientes tras el filtro.
    params = {
        "corpora": "drive",
        "driveId": drive_id,
        "q": (
            "mimeType='application/vnd.google-apps.folder' "
            "and trashed=false "
            "and name contains 'W-'"
        ),
        "fields": "files(id,name)",
        "pageSize": str(_DRIVE_API_PAGE_SIZE),
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
        "orderBy": "name",
    }
    headers = {"Authorization": f"Bearer {access_token}"}

    attempts = (0.0,) + _RATE_LIMIT_BACKOFF_SECONDS
    last_status: int | None = None
    for delay in attempts:
        if delay > 0:
            time.sleep(delay)
        try:
            r = httpx.get(_DRIVE_API_FILES, params=params, headers=headers, timeout=10)
        except Exception as exc:  # noqa: BLE001
            return None, f"httpx error: {type(exc).__name__}: {exc}"
        last_status = r.status_code
        if r.status_code == 200:
            try:
                return r.json().get("files", []), None
            except Exception as exc:  # noqa: BLE001
                return None, f"JSON inválido: {exc}"
        if not _is_rate_limit_response(r):
            # Cualquier no-200 no-rate-limit es terminal (401/403/404/500…).
            body_excerpt = (r.text or "")[:200].replace("\n", " ")
            return None, f"HTTP {r.status_code}: {body_excerpt}"

    return None, f"rate-limit persistente (último status {last_status})"


def audit(
    team_filter: str | None,
    limit: int,
) -> tuple[dict, int]:
    """Ejecuta la auditoría. Devuelve (reporte, exit_code)."""
    token = _get_drive_access_token()
    if not token:
        sys.stderr.write(
            "[ERROR] No se pudo obtener access_token de gdrive_ev.\n"
            "Verifica con: rclone config show gdrive_ev  | rclone about gdrive_ev:\n"
        )
        return {}, 2

    # Dedupe: varios equipos comparten Shared Drive ID.
    drive_to_teams: dict[str, list[str]] = defaultdict(list)
    for code, did in DRIVE_EV_TEAM_IDS.items():
        if did is None:
            continue
        if team_filter and code != team_filter:
            continue
        drive_to_teams[did].append(code)

    if not drive_to_teams:
        if team_filter:
            sys.stderr.write(
                f"[ERROR] Equipo '{team_filter}' no existe en DRIVE_EV_TEAM_IDS "
                "o no tiene Shared Drive ID asociado.\n"
            )
        else:
            sys.stderr.write("[ERROR] DRIVE_EV_TEAM_IDS está vacío.\n")
        return {}, 2

    report: dict = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "limit_per_drive": limit,
        "total_drives": len(drive_to_teams),
        "drives": [],
    }
    total_ok = 0
    total_fail = 0
    drives_error = 0

    # Ordenamos por el primer equipo (alfabético) para output determinista.
    for drive_id, codes in sorted(
        drive_to_teams.items(), key=lambda kv: sorted(kv[1])[0]
    ):
        teams_label = " / ".join(sorted(codes))
        folders, err = _list_drive_folders(drive_id, token, limit=limit)

        drive_entry: dict = {
            "drive_id": drive_id,
            "teams": sorted(codes),
            "error": err,
            "items": [],
        }

        print(f"\n=== {teams_label}  ({drive_id})")
        if err:
            print(f"  [ERROR] {err}")
            drives_error += 1
            report["drives"].append(drive_entry)
            continue

        # Filtro local: solo nombres que parezcan carpeta-expediente
        # (contienen W-XXXXXX). Descarta carpetas estructurales como
        # "PROPIEDADES", "S1", "Otros tutoriales".
        candidates = [
            f for f in (folders or [])
            if _W_ID_PROBE.search(f.get("name", ""))
        ]

        if not candidates:
            print(
                f"  (sin candidatos con patrón W-XXXXXX entre "
                f"{len(folders or [])} carpetas devueltas por la API)"
            )
            report["drives"].append(drive_entry)
            continue

        muestra = candidates[:limit]
        print(f"  ({len(muestra)} carpeta(s)-expediente, de {len(candidates)} candidatas)")
        for f in muestra:
            name = f.get("name", "")
            direccion, w_id = parse_ev_folder_name(name)
            ok = bool(direccion and w_id)
            mark = "[OK]  " if ok else "[FAIL]"
            print(f"  {mark} {name!r}")
            print(f"         dir={direccion!r}  W-ID={w_id!r}")
            drive_entry["items"].append({
                "name": name,
                "direccion": direccion,
                "w_id": w_id,
                "ok": ok,
            })
            if ok:
                total_ok += 1
            else:
                total_fail += 1
        report["drives"].append(drive_entry)

    report["total_ok"] = total_ok
    report["total_fail"] = total_fail
    report["drives_with_error"] = drives_error

    print("\n" + "=" * 60)
    print(
        f"  RESUMEN: {total_ok} OK / {total_fail} fallos "
        f"sobre {total_ok + total_fail} carpetas-expediente auditadas"
    )
    print(f"  Drives analizados: {len(drive_to_teams)}  ({drives_error} con error)")
    print("=" * 60)

    if total_fail > 0:
        print(
            "\nCarpetas con parse fallido (revisar regex de parse_ev_folder_name):"
        )
        for d in report["drives"]:
            for it in d["items"]:
                if not it["ok"]:
                    print(f"  - [{' / '.join(d['teams'])}] {it['name']!r}")

    return report, (1 if total_fail > 0 else 0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audita parse_ev_folder_name sobre las primeras N carpetas de "
            "cada Shared Drive de DRIVE_EV_TEAM_IDS."
        ),
    )
    parser.add_argument("--team", help="Filtrar a un solo equipo (p.ej. BaRS1).")
    parser.add_argument(
        "--limit", type=int, default=5,
        help="Nº de carpetas por drive (default 5).",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Guarda el reporte JSON en data/_audit/.",
    )
    args = parser.parse_args()

    report, code = audit(team_filter=args.team, limit=args.limit)

    if args.json and report:
        out_dir = ROOT / "data" / "_audit"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = out_dir / f"ev_folder_audit_{ts}.json"
        out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n[JSON] {out}")

    sys.exit(code)


if __name__ == "__main__":
    main()
