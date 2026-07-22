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
from collections import Counter
from pathlib import Path

_RC_PORT = 15572
_RC_URL = f"http://localhost:{_RC_PORT}"


def _rc_activo() -> bool:
    """La RC API de rclone es POST-only (un GET a `core/pid` devuelve 404,
    confirmado en vivo contra rclone v1.73.5 con `curl`) — con `urlopen` sin
    `method` explícito (GET por defecto) esta comprobación SIEMPRE fallaba,
    así que `levantar_rcd_si_falta` nunca detectaba un rcd ya activo y
    agotaba el timeout de 10s. Bug real (sesión 2026-07-21, W-02VUDR)."""
    try:
        req = urllib.request.Request(f"{_RC_URL}/core/pid", data=b"{}", method="POST")
        urllib.request.urlopen(req, timeout=2)
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


def copiar_renombrar(
    remote: str, src_relpath: str, dst_relpath: str, *,
    timeout: float = 60, async_: bool = False,
) -> dict:
    """Una llamada `operations/copyfile` sobre el `rcd` ya levantado. `remote`
    es el nombre del remote rclone CON el `:` final (p. ej. `gdrive_tl:`);
    las rutas son relativas a ese remote. Lanza si rclone devuelve error — el
    llamador (`copiar_manifiesto`) decide si es fatal o solo esa fila.

    `timeout` en segundos, parametrizable (ítem 14): una copia server-side
    grande pero legítima (p. ej. 1,1 GB en W-02VUDR) puede tardar más de los
    60s por defecto y no debe contarse como fallida solo por eso. Con
    `async_=True`, rclone encola el job en background y esta llamada vuelve
    de inmediato con `{"jobid": N, ...}` — el llamador debe esperar el
    resultado con `esperar_job(jobid)`."""
    payload = {
        "srcFs": remote, "srcRemote": src_relpath,
        "dstFs": remote, "dstRemote": dst_relpath,
    }
    if async_:
        payload["_async"] = True
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_RC_URL}/operations/copyfile", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def esperar_job(jobid, *, timeout_total: float = 1800, intervalo: float = 2.0) -> dict:
    """Polling de `POST job/status` hasta que el job encolado por
    `copiar_renombrar(..., async_=True)` termine (ítem 14 — copias grandes
    en background sin bloquear el `timeout` síncrono de la llamada HTTP).
    Lanza `RuntimeError` si el job termina sin éxito (incluye el `error` de
    rclone en el mensaje), o `TimeoutError` si supera `timeout_total`
    segundos sin terminar. Duerme `intervalo` segundos entre sondeos."""
    inicio = time.monotonic()
    while True:
        body = json.dumps({"jobid": jobid}).encode("utf-8")
        req = urllib.request.Request(
            f"{_RC_URL}/job/status", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            estado = json.loads(resp.read())
        if estado.get("finished"):
            if not estado.get("success", False):
                raise RuntimeError(f"job {jobid} falló: {estado.get('error', 'sin detalle')}")
            return estado
        if time.monotonic() - inicio > timeout_total:
            raise TimeoutError(f"job {jobid} no terminó en {timeout_total}s")
        time.sleep(intervalo)


def _cargar_progreso(path) -> set[str]:
    """`dst` ya copiados OK según el log JSONL (reanudación). Tolerante a un log
    ausente o a líneas corruptas (una corrida muerta puede dejar media línea)."""
    p = Path(path)
    if not p.exists():
        return set()
    ok: set[str] = set()
    for linea in p.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            reg = json.loads(linea)
        except ValueError:
            continue
        if not isinstance(reg, dict):
            continue  # línea JSON válida pero no-objeto (lista/número) — corrupción externa
        if reg.get("estado") == "ok" and reg.get("dst"):
            ok.add(reg["dst"])
    return ok


def _anota_progreso(path, dst: str, estado: str, error: str = "") -> None:
    """Anota una fila de progreso al log JSONL (append-only)."""
    reg = {"dst": dst, "estado": estado}
    if error:
        reg["error"] = error
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(reg, ensure_ascii=False) + "\n")


def _anota_progreso_seguro(path, dst: str, estado: str, error: str = "") -> None:
    """Envoltorio tolerante de `_anota_progreso`: un fallo al ESCRIBIR el log
    (`PermissionError` por antivirus/Drive-sync en Windows, directorio padre
    inexistente, disco lleno) es una incidencia de I/O del log, no de la copia
    — nunca debe abortar el batch ni reclasificar una copia ya exitosa como
    fallida. La copia y el log son preocupaciones independientes (revisión
    Task 5, defecto Important)."""
    try:
        _anota_progreso(path, dst, estado, error)
    except Exception:  # noqa: BLE001 — best-effort, un fallo de log no es fatal
        pass


def validar_pares(pares: list[tuple[str, str]]) -> None:
    """Aborta ANTES de tocar Drive si dos orígenes escriben el MISMO destino
    (`dst_relpath` duplicado) — uno pisaría al otro sin rastro. Backlog
    robustez-velocidad ítem 3: único modo de fallo que puede hacer DESAPARECER
    un documento sin que ningún check posterior lo cace."""
    dups = sorted(d for d, n in Counter(dst for _, dst in pares).items() if n > 1)
    if dups:
        raise ValueError(
            "destinos duplicados en el plan de copia (colisión de nombre_canonico): "
            + ", ".join(dups) + " — desambigua con _2/_3 antes de copiar")


def copiar_manifiesto(
    remote: str, pares: list[tuple[str, str]], *, progreso_path=None,
    gestionar_rcd: bool = True, timeout: float = 60, usar_async: bool = False,
) -> tuple[list[str], list[tuple[str, str]]]:
    """`pares` = [(src_relpath, dst_relpath), ...] ya decididos por la
    clasificación (Paso 1-3 de la skill). Copia TODOS dentro del MISMO proceso
    `rcd` — el pacer se mantiene estable entre llamadas, a diferencia de
    invocar `rclone.exe` una vez por fichero. Devuelve `(ok, fallidos)`;
    un fallo individual NO aborta el resto.

    Con `progreso_path`, escribe un log JSONL append por fila y REANUDA: los
    `dst` ya `ok` en un log previo se cuentan como copiados y se saltan (ítem 9
    — una corrida muerta a mitad no re-copia lo ya hecho). Un fallo al
    ESCRIBIR ese log (antivirus/Drive-sync en Windows, disco lleno) nunca
    aborta el batch ni reclasifica una copia ya exitosa como fallida — la
    anotación va por `_anota_progreso_seguro` y fuera del `try` de la copia.

    Con `gestionar_rcd=True` (default) arranca el `rcd` si falta y lo cierra
    al terminar SOLO si lo arrancó esta misma llamada (ítem 14 — no deja un
    `rcd` huérfano en `:15572`, ni toca uno ajeno que ya estuviera activo).
    `usar_async=True` encola cada copia y espera su job con `esperar_job`
    (pensado para ficheros grandes); `timeout` es el tope síncrono por
    llamada HTTP cuando no se usa async."""
    validar_pares(pares)
    ya_ok = _cargar_progreso(progreso_path) if progreso_path else set()
    ok: list[str] = []
    fallidos: list[tuple[str, str]] = []
    proc = levantar_rcd_si_falta() if gestionar_rcd else None
    try:
        for src, dst in pares:
            if dst in ya_ok:
                ok.append(dst)
                continue
            try:
                if usar_async:
                    r = copiar_renombrar(remote, src, dst, timeout=timeout, async_=True)
                    esperar_job(r.get("jobid"))
                else:
                    copiar_renombrar(remote, src, dst, timeout=timeout)
            except Exception as exc:  # noqa: BLE001 — un fallo de copia no aborta el resto
                fallidos.append((dst, str(exc)))
                if progreso_path:
                    _anota_progreso_seguro(progreso_path, dst, "fallido", str(exc))
                continue
            ok.append(dst)
            if progreso_path:
                _anota_progreso_seguro(progreso_path, dst, "ok")
    finally:
        if proc is not None:
            proc.terminate()
    return ok, fallidos

