"""Keep-alive de la sesión PHP de sudespacho.

Lanza un hilo daemon que hace un GET liviano al frontal heredado cada
INTERVAL_S segundos, evitando que el servidor PHP cierre la sesión por
inactividad (~24 min).

El hilo es singleton a nivel de proceso: `ensure_started()` es idempotente
y seguro para llamarse en cada rerender de Streamlit.

Estado compartido:
    last_ping   dict  {"ts": datetime | None, "ok": bool | None, "err": str}
"""
from __future__ import annotations

import threading
import time
from datetime import datetime

import httpx

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

INTERVAL_S = 14 * 60          # 14 min — margen sobre el timeout de 24 min
_PING_PATH  = "/tnm/gestion/extrajudiciales"   # URL actualizada 2026-05-04
_TIMEOUT_S  = 10

# ---------------------------------------------------------------------------
# Estado compartido (módulo-level, seguro entre rerenders de Streamlit)
# ---------------------------------------------------------------------------

last_ping: dict = {"ts": None, "ok": None, "err": ""}
_started  = False
_lock     = threading.Lock()


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

def _worker() -> None:
    """Bucle infinito que pinga el frontal PHP cada INTERVAL_S segundos."""
    while True:
        time.sleep(INTERVAL_S)
        _ping_once()


def _ping_once() -> None:
    """Ejecuta un GET al frontal PHP y actualiza last_ping."""
    try:
        # Importar aquí para evitar ciclos y leer .env en el momento del ping.
        from core.sync_sudespacho_legacy import SudespachoLegacyConfig
        cfg = SudespachoLegacyConfig.from_env()

        cookies = {"PHPSESSID": cfg.phpsessid}
        if cfg.jwt_token:
            cookies["@token"] = cfg.jwt_token
        if cfg.refresh_token:
            cookies["@refreshToken"] = cfg.refresh_token

        r = httpx.get(
            f"https://{cfg.host}{_PING_PATH}",
            cookies=cookies,
            timeout=_TIMEOUT_S,
            follow_redirects=True,
        )
        # Si el servidor devuelve la landing de E-plan, la sesión ha expirado.
        ok = r.status_code == 200 and "E-plan" not in r.text[:500]
        last_ping["ok"]  = ok
        last_ping["err"] = "" if ok else "Sesión expirada — renueva desde el sidebar"
    except Exception as exc:
        last_ping["ok"]  = False
        last_ping["err"] = str(exc)[:120]

    last_ping["ts"] = datetime.now()


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def ensure_started() -> None:
    """Garantiza que el hilo keep-alive está corriendo. Idempotente."""
    global _started
    with _lock:
        if not _started:
            t = threading.Thread(target=_worker, daemon=True, name="phpsessid-keepalive")
            t.start()
            _started = True


def ping_now() -> None:
    """Fuerza un ping inmediato (útil tras renovar la sesión manualmente)."""
    threading.Thread(target=_ping_once, daemon=True).start()
