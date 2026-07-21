"""Copia+renombra en bloque vía `rclone rcd` (RC API), evitando el reinicio
del "pacer" de cuota que sufre `rclone.exe` invocado una vez por fichero
(sesión 2026-07-21, W-02VUDR: una sola copia server-side tardó 110s por 6
reintentos `403 Quota exceeded` del cliente OAuth COMPARTIDO de rclone).

PRERREQUISITO (bloqueante, manual): un client_id/client_secret OAuth PROPIO
del despacho configurado en `rclone config` para el remote usado — sin esto
este módulo solo reordena el problema, no lo resuelve (sigue compartiendo
cuota global).

Self-contained (stdlib únicamente, sin `requests` ni `core/`): habla con la
RC API de un `rclone rcd` ya levantado (o lo levanta como subproceso si no
detecta uno activo). Endpoint y parámetros verificados en vivo el
2026-07-21 contra rclone v1.73.5 — no son una suposición.
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request

_RC_PORT = 15572
_RC_URL = f"http://localhost:{_RC_PORT}"


def _rc_activo() -> bool:
    try:
        urllib.request.urlopen(f"{_RC_URL}/core/pid", timeout=2)
        return True
    except Exception:
        return False


def levantar_rcd_si_falta() -> subprocess.Popen | None:
    """Arranca `rclone rcd` en background si no hay uno ya escuchando en
    `_RC_PORT`. Devuelve el `Popen` (para poder cerrarlo después) o `None` si
    ya había uno activo — no lo tocamos, puede ser de otra corrida."""
    if _rc_activo():
        return None
    proc = subprocess.Popen(
        ["rclone", "rcd", "--rc-no-auth", "--rc-addr", f"localhost:{_RC_PORT}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        if _rc_activo():
            break
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("rclone rcd no respondió tras 10s")
    return proc


def copiar_renombrar(remote: str, src_relpath: str, dst_relpath: str) -> dict:
    """Una llamada `operations/copyfile` sobre el `rcd` ya levantado. `remote`
    es el nombre del remote rclone CON el `:` final (p. ej. `gdrive_tl:`);
    las rutas son relativas a ese remote. Lanza si rclone devuelve error — el
    llamador (`copiar_manifiesto`) decide si es fatal o solo esa fila."""
    body = json.dumps({
        "srcFs": remote, "srcRemote": src_relpath,
        "dstFs": remote, "dstRemote": dst_relpath,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{_RC_URL}/operations/copyfile", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def copiar_manifiesto(
    remote: str, pares: list[tuple[str, str]],
) -> tuple[list[str], list[tuple[str, str]]]:
    """`pares` = [(src_relpath, dst_relpath), ...] ya decididos por la
    clasificación (Paso 1-3 de la skill). Copia TODOS dentro del MISMO
    proceso `rcd` — el pacer se mantiene estable entre llamadas, a
    diferencia de invocar `rclone.exe` una vez por fichero. Devuelve
    `(ok, fallidos)`; un fallo individual NO aborta el resto."""
    ok: list[str] = []
    fallidos: list[tuple[str, str]] = []
    for src, dst in pares:
        try:
            copiar_renombrar(remote, src, dst)
            ok.append(dst)
        except Exception as exc:  # noqa: BLE001 — un fallo no aborta el resto
            fallidos.append((dst, str(exc)))
    return ok, fallidos
