"""Script de sincronización programada — FeesDefender.

Diseñado para ejecutarse como tarea programada (Windows Task Scheduler
o similar). Recorre todos los casos activos y descarga los documentos nuevos
de cada expediente vinculado.

**No procesa nada.** El motor documental es la sala de máquina
(`python -m scripts.sala_maquina apply "<case_id>"`), que se ejecuta aparte y a
conciencia: una corrida de OCR puede durar más de una hora y no cabe en una tarea
programada silenciosa. Hasta el 2026-08-04 este script traía un flag `--run-pipeline`
que llamaba al motor jubilado (`core.pipeline.run`: Docling con tope de 30 páginas,
salida a `raw_text/` + `MD/` legacy). Se retiró: `MEJORAS #113`.

Uso:
    python -m scripts.scheduled_sync
    python -m scripts.scheduled_sync --log-file sync.log

Flujo:
    1. Lee data/CASOS/ y encuentra todos los _caso.md con expedientes registrados
    2. Para cada expediente: pull v2 (idempotente por hash del manifiesto M9)
    3. Escribe log en 07_AI cowork/_sync_log.md de cada caso
    4. Imprime resumen por consola, incluidos los casos con estructura v1 bloqueados

Configuración en .env:
    SUDESPACHO_LEGACY_HOST=tnm.sudespacho.net
    SUDESPACHO_LEGACY_PHPSESSID=<valor fresco>     ← refrescar cuando expire
    SUDESPACHO_API_KEY=<api_key>
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Asegurar que el módulo core es importable desde este script
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from core.config import settings
from core.sync_sudespacho import pull_expediente_v2, SudespachoError
from core.sync_sudespacho_legacy import SudespachoLegacyError

try:
    import yaml as _yaml
except ImportError:
    import json as _yaml  # fallback mínimo


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logging(log_file: str | None = None) -> logging.Logger:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        handlers=handlers,
    )
    return logging.getLogger("scheduled_sync")


# ---------------------------------------------------------------------------
# Keep-alive rclone gdrive_ev
# ---------------------------------------------------------------------------

def _keepalive_gdrive_ev(log: logging.Logger) -> None:
    """Hace una llamada ligera a gdrive_ev para mantener el OAuth token activo.

    Google invalida el refresh token si no se usa durante 6 meses.
    Ejecutar esto diariamente previene esa caducidad sin intervención manual.

    Usa `rclone about gdrive_ev:` — solo consulta la cuota de almacenamiento,
    no lista ni descarga ningún fichero. rclone renueva el access token
    automáticamente y persiste el resultado en rclone.conf.

    No interrumpe el sync si falla: solo emite un warning.
    """
    try:
        result = subprocess.run(
            ["rclone", "about", "gdrive_ev:"],
            timeout=30,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log.debug("gdrive_ev keep-alive OK")
        else:
            log.warning(
                "gdrive_ev keep-alive falló (código %d): %s — "
                "puede que el token haya expirado. Ejecutar: "
                "rclone config reconnect gdrive_ev:",
                result.returncode,
                (result.stderr or "").strip()[:200],
            )
    except FileNotFoundError:
        log.warning("rclone no encontrado en PATH — keep-alive gdrive_ev omitido")
    except subprocess.TimeoutExpired:
        log.warning("gdrive_ev keep-alive timeout (30s)")
    except Exception as exc:
        log.warning("gdrive_ev keep-alive error inesperado: %s", exc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_expedientes(case_id: str) -> list[dict]:
    """Lee la lista de expedientes del índice _caso.md."""
    from core.config import caso_path
    index = caso_path(case_id) / "00_Input" / "_caso.md"
    if not index.exists():
        return []
    text = index.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return []
    try:
        _, fm_raw, _ = text.split("---", 2)
        fm = _yaml.safe_load(fm_raw) or {}
    except Exception:
        return []
    return fm.get("sudespacho_expedientes") or []


def _append_sync_log(case_id: str, entries: list[str]) -> None:
    """Añade una entrada al log de sync del caso en 07_AI cowork/."""
    from core.config import caso_path
    log_path = caso_path(case_id) / "07_AI cowork" / "_sync_log.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    block = f"\n## {ts}\n\n" + "\n".join(f"- {e}" for e in entries) + "\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(block)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(*, log_file: str | None = None) -> int:
    """Ejecuta el sync de todos los casos. Devuelve código de salida.

    Solo descarga: el procesado (sala de máquina) va aparte, ver el docstring del módulo.
    """
    log = _setup_logging(log_file)

    if not settings.casos_root.exists():
        log.error("CASOS_ROOT no existe: %s", settings.casos_root)
        return 1

    # Keep-alive del token OAuth de gdrive_ev — previene caducidad por inactividad.
    # Google invalida el refresh token tras 6 meses sin uso; esta llamada diaria
    # lo mantiene vivo sin intervención manual.
    _keepalive_gdrive_ev(log)

    from core.casos.case_locator import list_cases as _list
    casos = sorted(p.name for p in _list())

    if not casos:
        log.info("No hay casos en %s", settings.casos_root)
        return 0

    log.info("Iniciando sync — %d caso(s)", len(casos))
    total_new = 0
    total_errors = 0
    bloqueados: list[str] = []
    tocados: list[str] = []

    for case_id in casos:
        expedientes = _read_expedientes(case_id)
        if not expedientes:
            continue

        log.info("[%s] %d expediente(s)", case_id, len(expedientes))
        case_log: list[str] = []

        for exp in expedientes:
            exp_id = str(exp.get("id", ""))
            elem = exp.get("element", "expedientes_judiciales")
            if not exp_id:
                continue

            try:
                result = pull_expediente_v2(case_id, exp_id, element=elem)
            except (SudespachoError, SudespachoLegacyError) as exc:
                log.error("  [%s] %s/%s → %s", case_id, elem, exp_id, exc)
                case_log.append(f"❌ {elem} {exp_id}: {exc}")
                total_errors += 1
                continue

            if result.blocked_legacy_v1:
                # No cuenta como error del sync: es un caso que necesita migración
                # manual del layout, no un fallo de red ni de credencial.
                log.warning("  [%s] estructura v1 (sudespacho_*/) — nada descargado",
                            case_id)
                case_log.append(f"⛔ {elem} {exp_id}: estructura v1 — nada descargado")
                if case_id not in bloqueados:
                    bloqueados.append(case_id)
                continue

            new_docs = result.documents_written
            total_new += new_docs

            if new_docs:
                log.info("  [%s] %s %s → +%d doc(s)", case_id, elem, exp_id, new_docs)
                case_log.append(
                    f"🆕 {elem} {exp_id}: +{new_docs} doc(s) "
                    f"en {', '.join(sorted(result.by_carpeta))}"
                )
                if case_id not in tocados:
                    tocados.append(case_id)
            else:
                log.debug("  [%s] %s %s → sin cambios", case_id, elem, exp_id)
                case_log.append(f"✓ {elem} {exp_id}: sin cambios")

            for err in result.errors:
                # Filtrar el mensaje de "sin cambios" (no es un error real)
                if "sin cambios" not in err.lower() and "ya descargado" not in err.lower():
                    log.warning("  [%s] ⚠️  %s", case_id, err)

        if case_log:
            try:
                _append_sync_log(case_id, case_log)
            except OSError as exc:
                log.warning("[%s] No se pudo escribir sync log: %s", case_id, exc)

    log.info(
        "Sync completado — %d doc(s) nuevos, %d error(s)",
        total_new, total_errors,
    )
    if bloqueados:
        log.warning(
            "%d caso(s) con estructura v1 (`00_Input/sudespacho_*/`) sin descargar. "
            "Migración manual: borrar esas carpetas y repetir el pull. Casos: %s",
            len(bloqueados), ", ".join(bloqueados),
        )
    if tocados:
        # El procesado NO se encadena aquí (ver docstring del módulo): se deja dicho
        # qué falta por correr, que es lo que antes fingía hacer `--run-pipeline`.
        log.info(
            "Pendiente de procesar en la sala de máquina (aparte): %s",
            ", ".join(tocados),
        )
    return 0 if total_errors == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync incremental de todos los casos activos con sudespacho.net"
    )
    parser.add_argument(
        "--log-file", metavar="PATH",
        help="Escribir log además en este archivo (append)",
    )
    args = parser.parse_args()
    sys.exit(run(log_file=args.log_file))


if __name__ == "__main__":
    main()
