"""Frontal CLI de la biblioteca de casos: ``checkout`` / ``checkin``.

    python -m scripts.repository_cli checkout <case_id> --local <dir> --remote-path <ruta>
    python -m scripts.repository_cli checkin  <case_id> --local <dir> --remote-path <ruta> [--yes]

Orquesta el **cerebro** puro (``core.repository_checkout``: plan de merge de 3
vías, validación de transiciones, mutación del lock) y el **músculo** (rclone
contra el remote ``gdrive_tl`` — cuenta del despacho, Shared Drive EXPEDIENTES -
TYUKHAY LEGAL). Es el frontal de los 4 usuarios (Nikolai, Paola, Ana, Sergio);
independiente de Streamlit.

**Comportamiento único compartido con la skill ``checkin-caso``** (la lógica de
``assets/merge_template.cmd`` es la referencia validada en el piloto W-02VND1 /
W-02THLJ, 2026-07-07): ``--checksum``, ``--backup-dir`` a
``gdrive_tl:_merge_backups/<W>_<TS>``, exclusiones de protocolo, copia ciega de
``90_Notas personales`` (cortesía; bajo D5 normalmente no viaja),
``rclone check --one-way --fast-list``, y semáforo VERDE/AMARILLO/ROJO.

Requisitos del piloto codificados como invariantes (INFORME_PILOTO §Hallazgos):
1. rclone corre SIEMPRE en la máquina del usuario (aquí), nunca en Cowork.
2. Remote ``gdrive_tl`` + ``team_drive``; IDs de carpeta antes que rutas.
3. Inventarios se validan por CONTENIDO (JSON parseable + no vacío), nunca por
   exit code a secas (``validar_inventario_texto``).
4. Vista congelada del montaje → nombres de artefacto únicos con timestamp.
5. **Nunca** tubería de PowerShell: ``subprocess`` con ``encoding="utf-8"`` y
   ``--log-file`` (la tubería PS corrompe UTF-8 vía CP850 y pierde acentos).
6. ``--fast-list`` en todos los listados post-merge (cuota API).
7. Re-ejecución desde cero converge (``--checksum`` salta lo ya hecho).

Nota de alcance (MVP): las funciones PURAS (parseo, validación, semáforo,
construcción de comandos, plan) están cubiertas por tests. La orquestación real
contra el Drive no se ha ejecutado en vivo en esta sesión: el piloto la validó a
mano y Cowork re-correrá los evals de la skill. La CLI y la skill comparten el
mismo cerebro y los mismos flags.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from core import repository_checkout as rc
from core.config import (
    PENDIENTE_CHECKIN_SUBDIR,
    RCLONE_REMOTE_TL,
    TEAM_DRIVE_TL,
    settings,
)
from core.utils import now_iso_utc, ts_compacto


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class InventarioInvalido(RuntimeError):
    """El inventario de rclone no es JSON válido o está vacío (hallazgo 3)."""


# ---------------------------------------------------------------------------
# Helpers PUROS — parseo de inventario
# ---------------------------------------------------------------------------

def parse_inventario_lsjson(texto: str) -> dict[str, dict[str, Any]]:
    """Convierte la salida de ``rclone lsjson -R --hash`` en un inventario.

    Devuelve ``{ruta_relativa: {"hash": md5|None, "size": int}}`` omitiendo
    directorios. ``hash`` es ``None`` para Google-native (sin MD5). Las rutas se
    normalizan a separador POSIX.
    """
    data = json.loads(texto)
    inv: dict[str, dict[str, Any]] = {}
    for item in data:
        if item.get("IsDir"):
            continue
        ruta = str(item.get("Path", "")).replace("\\", "/")
        if not ruta:
            continue
        md5 = (item.get("Hashes") or {}).get("md5") or None
        inv[ruta] = {"hash": md5, "size": item.get("Size", 0)}
    return inv


def validar_inventario_texto(texto: str) -> dict[str, dict[str, Any]]:
    """Valida y parsea un inventario por CONTENIDO (hallazgo 3 del piloto).

    rclone contra una unidad sin acceso puede terminar con exit 0 y salida
    vacía/truncada. Se exige JSON parseable y al menos una entrada. Lanza
    :class:`InventarioInvalido` en otro caso.
    """
    try:
        inv = parse_inventario_lsjson(texto)
    except (json.JSONDecodeError, TypeError) as exc:
        raise InventarioInvalido(f"Inventario no es JSON válido: {exc}") from exc
    if not inv:
        raise InventarioInvalido(
            "Inventario vacío: rclone pudo terminar sin acceso a la unidad. "
            "Comprobar la cuenta del remote (rclone backend drives <remote>:)."
        )
    return inv


# ---------------------------------------------------------------------------
# Helpers PUROS — semáforo
# ---------------------------------------------------------------------------

def clasificar_semaforo(
    *,
    conflictos: int,
    copia_fallo_sistemico: bool,
    verificacion_limpia: bool,
) -> str:
    """Devuelve ``"verde"`` / ``"amarillo"`` / ``"rojo"`` (semáforo del checkin).

    - ROJO: fallo sistémico de copia (no borrar nada).
    - AMARILLO: hay conflictos por resolver o la verificación encontró
      diferencias (revisar; lo sobrescrito está en ``_merge_backups/``).
    - VERDE: copia hecha, verificación por hash limpia y sin conflictos.
    """
    if copia_fallo_sistemico:
        return "rojo"
    if conflictos > 0 or not verificacion_limpia:
        return "amarillo"
    return "verde"


# ---------------------------------------------------------------------------
# Helpers PUROS — construcción de comandos rclone
# ---------------------------------------------------------------------------

def _rclone_bin() -> str:
    return settings.rclone_binary or "rclone"


def remote_arg(
    remote: str,
    team_drive: str,
    path: str = "",
    folder_id: str | None = None,
) -> str:
    """Compone el argumento de remote rclone con ``team_drive`` (IDs > rutas).

    Ejemplos:
        ``gdrive_tl,team_drive=ID:CASOS/x``
        ``gdrive_tl,team_drive=ID,root_folder_id=FID:``  (folder por ID)
    """
    base = f"{remote},team_drive={team_drive}"
    if folder_id:
        base += f",root_folder_id={folder_id}"
    return f"{base}:{path}"


def _exclusiones_rclone() -> list[str]:
    """Args ``--exclude`` de protocolo (MERGE_EXCLUSIONS) + ``desktop.ini``."""
    args: list[str] = ["--exclude", "desktop.ini"]
    for pat in rc.MERGE_EXCLUSIONS:
        args += ["--exclude", pat]
    return args


def build_copy_cmd(
    *,
    origen: str,
    destino: str,
    backup_dir: str,
    log_file: str,
    transfers: int = 4,
) -> list[str]:
    """Comando ``rclone copy`` local→Drive con los flags validados en el piloto."""
    return [
        _rclone_bin(), "copy", origen, destino,
        "--checksum", "--drive-skip-shortcuts",
        "--transfers", str(transfers),
        *_exclusiones_rclone(),
        "--backup-dir", backup_dir,
        "--log-level", "INFO", "--log-file", log_file,
    ]


def build_check_cmd(
    *,
    local: str,
    destino: str,
    log_file: str,
) -> list[str]:
    """Comando ``rclone check --one-way --fast-list`` (verificación por hash)."""
    return [
        _rclone_bin(), "check", local, destino,
        "--one-way", "--drive-skip-shortcuts", "--fast-list",
        *_exclusiones_rclone(),
        "--log-level", "INFO", "--log-file", log_file,
    ]


def build_lsjson_cmd(destino: str) -> list[str]:
    """Comando ``rclone lsjson -R --hash --fast-list`` (inventario del Drive)."""
    return [
        _rclone_bin(), "lsjson", destino,
        "-R", "--hash", "--fast-list", "--drive-skip-shortcuts",
    ]


def build_copyto_cmd(*, origen: str, destino: str) -> list[str]:
    """Comando ``rclone copyto`` para un único fichero (p. ej. ``_caso.md``)."""
    return [_rclone_bin(), "copyto", origen, destino, "--drive-skip-shortcuts"]


def build_moveto_cmd(*, origen: str, destino: str) -> list[str]:
    """Comando ``rclone moveto`` de un fichero (borrado/renombrado → backup-dir).

    ``rclone copy`` NO borra en el destino; los borrados (caso 5) y el origen de
    los renombrados (caso 9) se propagan moviendo el fichero al ``--backup-dir``
    (queda recuperable, D2) — nunca con un borrado ciego ni con ``sync``.
    """
    return [_rclone_bin(), "moveto", origen, destino, "--drive-skip-shortcuts"]


def nombre_auditlog(ts: str) -> str:
    return f"AUDITLOG_MERGE_{ts}.jsonl"


def planificar_integracion_bandeja(paths) -> list[dict]:
    """Plan PURO de integración de la bandeja `_pendiente_checkin/` (CP10, §6).

    Dada la lista de rutas del Drive, para cada fichero de la bandeja
    (``_pendiente_checkin/<origen>/<rel...>``) calcula su destino ``<rel>``. Si
    ``<rel>`` ya existe (recién mergeado), se trata como intake NUEVO y va a
    ``<padre>/_reingesta_<base>`` (nunca sobrescribe, §6). Ignora lo que no es
    bandeja. Determinista: mismo input → mismo plan.

    Returns:
        Lista de ``{"origen": ruta_bandeja, "destino": rel, "colision": bool}``.
    """
    pref = PENDIENTE_CHECKIN_SUBDIR + "/"
    bandeja = sorted(p for p in paths if p.startswith(pref))
    ocupados = {p for p in paths if not p.startswith(pref)}
    plan: list[dict] = []
    for p in bandeja:
        partes = p.split("/")
        # p = _pendiente_checkin/<origen>/<rel...>  → rel = partes[2:]
        if len(partes) < 3:
            continue
        target_rel = "/".join(partes[2:])
        if target_rel in ocupados:
            padre, _, base = target_rel.rpartition("/")
            destino_rel = f"{padre}/_reingesta_{base}" if padre else f"_reingesta_{base}"
            colision = True
        else:
            destino_rel = target_rel
            colision = False
        ocupados.add(destino_rel)
        plan.append({"origen": p, "destino": destino_rel, "colision": colision})
    return plan


def backup_dir_arg(remote: str, wcode: str, ts: str, team_drive: str | None = None) -> str:
    """Ruta del ``--backup-dir`` (fuera del árbol de destino, lección 10).

    Debe estar en el MISMO remote que el destino: si el destino usa la cadena de
    conexión ``remote,team_drive=ID:`` (Shared Drive), el backup-dir tiene que
    llevar el mismo ``team_drive`` o rclone falla ("has to be on the same
    remote as destination").
    """
    prefijo = f"{remote},team_drive={team_drive}" if team_drive else remote
    return f"{prefijo}:_merge_backups/{wcode}_{ts}"


# ---------------------------------------------------------------------------
# Inventario LOCAL (I/O) — MD5 para paridad con el Drive
# ---------------------------------------------------------------------------

def _md5(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        while blk := f.read(chunk):
            h.update(blk)
    return h.hexdigest()


def inventario_local(root: Path) -> dict[str, dict[str, Any]]:
    """Inventario MD5 del árbol local, omitiendo ``MERGE_EXCLUSIONS`` (§5).

    Se usa MD5 (no SHA-256) para comparar con los hashes de la Drive API y con
    el baseline del ``MANIFEST_CHECKOUT.json``. Las rutas son relativas a
    ``root`` con separador POSIX.
    """
    inv: dict[str, dict[str, Any]] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rc.esta_excluido(rel):
            continue
        inv[rel] = {"hash": _md5(p), "size": p.stat().st_size}
    return inv


# ---------------------------------------------------------------------------
# Runner de rclone (I/O) — subprocess UTF-8, jamás pipe de PowerShell
# ---------------------------------------------------------------------------

def run_rclone(cmd: list[str]) -> subprocess.CompletedProcess:
    """Ejecuta rclone capturando stdout/stderr con ``encoding="utf-8"``.

    NUNCA se canaliza por PowerShell (`| Out-File`): la captura es un pipe de SO
    a Python decodificado en UTF-8, que es lo que prescribe el hallazgo 5 del
    piloto. En Windows, ``text=True`` sin encoding decodifica con cp1252 y trunca
    tildes → por eso se fija ``encoding="utf-8", errors="replace"``.
    """
    return subprocess.run(
        cmd, capture_output=True, encoding="utf-8", errors="replace", check=False,
    )


# ---------------------------------------------------------------------------
# Reportes (I/O)
# ---------------------------------------------------------------------------

def render_delta(plan: list[rc.AccionMerge]) -> str:
    """DELTA_PREVIO.md (CP3): plan de merge legible, borrados listados aparte."""
    resumen = rc.resumen_plan(plan)
    lineas = ["# DELTA previo al checkin (plan de merge 3 vías)", ""]
    lineas.append(
        f"- Copiar (local→Drive): {resumen[rc.ACCION_COPY_LOCAL]}\n"
        f"- Preservar (solo Drive): {resumen[rc.ACCION_PRESERVE_DRIVE]}\n"
        f"- Renombrar (mover en Drive): {resumen[rc.ACCION_RENAME]}\n"
        f"- Borrar en Drive (a papelera): {resumen[rc.ACCION_DELETE_DRIVE]}\n"
        f"- Conflictos (decisión manual): {resumen[rc.ACCION_CONFLICT]}\n"
    )
    borrados = [a for a in plan if a.accion == rc.ACCION_DELETE_DRIVE]
    if borrados:
        lineas.append("\n## Borrados propuestos (requieren confirmación explícita)\n")
        for a in borrados:
            lineas.append(f"- `{a.ruta}` — {a.motivo}")
    conflictos = [a for a in plan if a.accion == rc.ACCION_CONFLICT]
    if conflictos:
        lineas.append("\n## Conflictos (el checkin NO los resuelve solo)\n")
        for a in conflictos:
            lineas.append(f"- `{a.ruta}` — {a.motivo}")
    return "\n".join(lineas) + "\n"


# ===========================================================================
# Orquestación (I/O) — checkout / checkin
#
# No se ejecuta contra el Drive en los tests (I/O externo). Delega toda decisión
# en el cerebro y usa rclone con los flags validados. Recuperación ante fallo:
# re-ejecutar desde cero (doctrina §4.4).
# ===========================================================================

def cmd_checkout(args: argparse.Namespace) -> int:
    remote = args.remote or RCLONE_REMOTE_TL
    team = args.team_drive or TEAM_DRIVE_TL
    destino = remote_arg(remote, team, args.remote_path or "", args.folder_id)
    local = Path(args.local)
    ts = now_iso_utc()
    user = args.user or _usuario_por_defecto()
    maquina = socket.gethostname()

    print(f"[checkout] {args.case_id}")
    print(f"  remote : {destino}")
    print(f"  local  : {local}")
    work = _tmp_dir()

    # CP0: leer el lock del Drive (pull _caso.md) y comprobar disponibilidad.
    fm_drive = _pull_caso_md(destino, work)
    estado = rc.estado_de_fm(fm_drive)
    if estado != "disponible":
        lock = rc.leer_lock_de_fm(fm_drive)
        print(f"  ✗ El caso NO está disponible (estado={estado}, "
              f"lo tiene {lock.get('checkout_user')}). Abortado.")
        return 2

    if args.dry_run:
        print("  [dry-run] disponible → se adquiriría el lock y se copiaría "
              "Drive→local (excluyendo protocolo/notas). Nada escrito.")
        return 0

    # Adquirir lock (§2.2): escribir prestado + nonce, esperar el sync lag,
    # releer por API y confirmar que el nonce ganador es el propio.
    nonce = _nonce()
    rc.validar_transicion(estado, "prestado")
    rc.aplicar_lock_prestado(fm_drive, user=user, timestamp=ts, nonce=nonce,
                             maquina=maquina, notas=args.notas)
    _push_caso_md(fm_drive, destino, work)
    time.sleep(_SYNC_LAG_S)
    fm_check = _pull_caso_md(destino, work)
    if not rc.verificar_nonce(fm_check, nonce):
        ganador = rc.leer_lock_de_fm(fm_check).get("checkout_user")
        print(f"  ✗ Otro checkout ganó la carrera del lock (usuario={ganador}). "
              f"Abortado sin copiar.")
        return 2
    print(f"  ✓ lock adquirido (nonce {nonce[:6]}…).")

    # Copiar Drive→local (excluyendo protocolo + notas, §3/§5). El log va al dir
    # temporal (el destino local puede no existir aún → rclone no crearía el log ahí).
    local.mkdir(parents=True, exist_ok=True)
    log_file = str(work / f"checkout_{ts_compacto(ts)}.log")
    cmd = [
        _rclone_bin(), "copy", destino, str(local),
        "--checksum", "--drive-skip-shortcuts", "--transfers", "4",
        *_exclusiones_rclone(),
        "--log-level", "INFO", "--log-file", log_file,
    ]
    res = run_rclone(cmd)
    if res.returncode != 0:
        # Rollback del lock: no dejar el caso 'prestado' sin copia local útil
        # (evita el estado atascado del runbook §7.1). La re-ejecución converge.
        rc.aplicar_lock_cancelado(fm_check)
        _push_caso_md(fm_check, destino, work)
        print(f"  ✗ rclone copy falló (rc={res.returncode}). Lock revertido a "
              f"disponible. Ver {log_file}\n{res.stderr[-500:] if res.stderr else ''}")
        return 1

    # Baseline: MANIFEST_CHECKOUT.json desde el inventario local + subida al Drive
    # (debe sobrevivir a la muerte del Desktop, §3.3).
    inv = inventario_local(local)
    manifest = {"generado": ts, "n_ficheros": len(inv), "inventario": inv}
    manifest_path = local / "MANIFEST_CHECKOUT.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    run_rclone(build_copyto_cmd(
        origen=str(manifest_path),
        destino=_remoto(destino, "MANIFEST_CHECKOUT.json")))

    # Evento forense case_checkout en el _intake_log.jsonl del Drive.
    _append_evento_drive(destino, work, case_id=args.case_id,
                         event="case_checkout", actor=user,
                         details=rc.evento_checkout_details(
                             user=user, timestamp=ts, nonce=nonce, maquina=maquina,
                             ruta_local=str(local), n_ficheros=len(inv),
                             manifest_hash=_md5(manifest_path)))
    print(f"  ✓ MANIFEST_CHECKOUT.json ({len(inv)} ficheros) subido + case_checkout registrado.")
    return 0


def cmd_checkin(args: argparse.Namespace) -> int:
    remote = args.remote or RCLONE_REMOTE_TL
    team = args.team_drive or TEAM_DRIVE_TL
    destino = remote_arg(remote, team, args.remote_path or "", args.folder_id)
    local = Path(args.local)
    ts = now_iso_utc()
    tsc = ts_compacto(ts)

    print(f"[checkin] {args.case_id}")
    if not local.exists():
        print(f"  ✗ Ruta local inexistente: {local} (runbook §7.1: señalar nueva "
              f"ruta o cancelar checkout).")
        return 2
    work = _tmp_dir()

    # CP1: inventarios L / D / B (validados por contenido).
    inv_local = inventario_local(local)
    ls = run_rclone(build_lsjson_cmd(destino))
    try:
        inv_drive = validar_inventario_texto(ls.stdout)
    except InventarioInvalido as exc:
        print(f"  ✗ Inventario de Drive inválido: {exc}")
        return 1
    inv_base = _leer_manifest(local)

    # CP3: plan de merge 3 vías → DELTA_PREVIO.md. Se escribe en el dir temporal
    # (NO en el caso): así los artefactos del protocolo no contaminan el
    # inventario del propio merge ni el de checkins posteriores.
    plan = rc.plan_merge(inv_local, inv_drive, inv_base)
    delta_path = work / "DELTA_PREVIO.md"
    delta_path.write_text(render_delta(plan), encoding="utf-8")
    resumen = rc.resumen_plan(plan)
    print("  plan:", resumen)
    print(f"  DELTA: {delta_path}")

    borrados = [a for a in plan if a.accion == rc.ACCION_DELETE_DRIVE]
    conflictos = [a for a in plan if a.accion == rc.ACCION_CONFLICT]

    if args.dry_run:
        print("  [dry-run] DELTA_PREVIO.md escrito. Nada tocado.")
        return 0

    # Gate humano (CP3): borrados requieren confirmación explícita (--yes).
    if borrados and not args.yes:
        print(f"  ⚠ {len(borrados)} borrado(s) propuesto(s). Revisa el DELTA "
              f"y relanza con --yes para confirmar. Nada tocado.")
        return 3

    # CP4/CP5/CP6: copia + backup + borrados (a papelera vía backup-dir). El
    # backup-dir va en el MISMO remote (con team_drive) que el destino.
    backup = backup_dir_arg(remote, args.wcode or args.case_id, tsc, team_drive=team)
    log_file = str(work / nombre_auditlog(tsc))
    copia = run_rclone(build_copy_cmd(
        origen=str(local), destino=destino, backup_dir=backup, log_file=log_file))
    copia_fallo = copia.returncode != 0

    # CP6: propagar borrados (caso 5) y origen de renombrados (caso 9). rclone
    # copy no borra: se mueve el fichero al backup-dir (recuperable, D2). Solo
    # los confirmados por el gate --yes. NUNCA si la copia falló (no borrar sobre
    # un merge incompleto): abortar y dejar que la re-ejecución converja.
    borrado_fallo = False
    if copia_fallo:
        print(f"  ✗ rclone copy falló (rc={copia.returncode}); NO se borra nada. "
              f"Re-ejecuta el checkin (converge). Ver {log_file}")
        return 1
    for a in plan:
        origen_borrado = None
        if a.accion == rc.ACCION_DELETE_DRIVE:
            origen_borrado = a.ruta
        elif a.accion == rc.ACCION_RENAME and a.ruta_origen:
            origen_borrado = a.ruta_origen
        if origen_borrado:
            mv = run_rclone(build_moveto_cmd(
                origen=_remoto(destino, origen_borrado),
                destino=f"{backup}/{origen_borrado}"))
            if mv.returncode != 0:
                borrado_fallo = True
                print(f"  ⚠ no se pudo mover a backup: {origen_borrado} (rc={mv.returncode})")

    # CP8: verificación por hash (no por exit code).
    check_log = str(work / f"check_{tsc}.log")
    chk = run_rclone(build_check_cmd(local=str(local), destino=destino, log_file=check_log))
    verificacion_limpia = chk.returncode == 0 and not borrado_fallo

    semaforo = clasificar_semaforo(
        conflictos=len(conflictos),
        copia_fallo_sistemico=copia_fallo,
        verificacion_limpia=verificacion_limpia,
    )
    print(f"  semáforo: {semaforo.upper()}")

    if semaforo != "verde":
        # CP7: si hay conflictos → estado 'conflicto' (el local SE CONSERVA);
        # el AMARILLO no libera el lock. El ROJO tampoco.
        if conflictos:
            fm = _pull_caso_md(destino, work)
            rc.aplicar_estado(fm, "conflicto")
            _push_caso_md(fm, destino, work)
            print(f"  → estado 'conflicto' escrito en el Drive; el local se conserva. "
                  f"Resolver los {len(conflictos)} conflicto(s) (ver DELTA_PREVIO.md) "
                  f"y reintentar el checkin.")
        print(f"  NO se libera el lock. Revisa {log_file} / {check_log}.")
        return 0 if semaforo == "amarillo" else 1

    # CP9: subir el AUDITLOG (último artefacto) a 07_AI cowork/merge_<TS>/.
    _upload_evidencia(destino, tsc, [log_file, check_log])

    # Evento forense case_checkin en el _intake_log.jsonl del Drive.
    _append_evento_drive(destino, work, case_id=args.case_id, event="case_checkin",
                         actor=args.user or _usuario_por_defecto(),
                         details=rc.evento_checkin_details(
                             user=args.user or _usuario_por_defecto(), timestamp=ts,
                             copiados=resumen[rc.ACCION_COPY_LOCAL],
                             preservados=resumen[rc.ACCION_PRESERVE_DRIVE],
                             borrados=resumen[rc.ACCION_DELETE_DRIVE],
                             conflictos=0, renombrados=resumen[rc.ACCION_RENAME],
                             resultado="verde", auditlog=nombre_auditlog(tsc)))

    # CP10: integrar la bandeja _pendiente_checkin/ (escrituras del pipeline
    # durante el préstamo) y vaciarla (§6).
    integrados, colisiones = _integrar_bandeja(destino)
    if integrados:
        print(f"  ✓ bandeja integrada: {integrados} fichero(s)"
              + (f", {colisiones} como _reingesta_ (colisión, sin sobrescribir)" if colisiones else ""))

    # CP11: liberar el lock en el Drive (prestado → disponible).
    fm = _pull_caso_md(destino, work)
    estado_actual = rc.estado_de_fm(fm)
    rc.validar_transicion(estado_actual, "disponible")
    rc.aplicar_lock_liberado(fm, timestamp=ts, auditlog=nombre_auditlog(tsc))
    _push_caso_md(fm, destino, work)
    print(f"  ✓ VERDE. AUDITLOG subido, case_checkin registrado, lock liberado "
          f"(estado → disponible).")
    return 0


# ---------------------------------------------------------------------------
# Helpers de I/O del lock del Drive (pull/push de _caso.md)
# ---------------------------------------------------------------------------

# Espera del write-then-verify del lock (sync lag conocido del Drive, §2.2).
_SYNC_LAG_S = 4


def _tmp_dir() -> Path:
    """Directorio temporal para los ficheros transitorios del protocolo.

    El pull/push de `_caso.md` y `_intake_log.jsonl` NO debe dejar residuos en
    la carpeta del caso (contaminarían el inventario del próximo checkin).
    """
    return Path(tempfile.mkdtemp(prefix="fd_biblio_"))


def _remoto(destino: str, relpath: str) -> str:
    """Compone una ruta remota bajo `destino` (respetando el `:` del remote)."""
    base = destino if destino.endswith("/") or destino.endswith(":") else destino + "/"
    return base + relpath


def _caso_md_remoto(destino: str) -> str:
    """Ruta remota del `_caso.md` (bajo `00_Input/`) para copyto."""
    return _remoto(destino, "00_Input/_caso.md")


def _integrar_bandeja(destino: str) -> tuple[int, int]:
    """CP10: integra la bandeja `_pendiente_checkin/` del Drive y la vacía (§6).

    Mueve cada fichero de la bandeja a su ruta original (o a ``_reingesta_*`` si
    colisiona, sin sobrescribir), según ``planificar_integracion_bandeja``, y
    limpia los directorios vacíos. Devuelve ``(integrados, colisiones)``.
    """
    ls = run_rclone(build_lsjson_cmd(destino))
    try:
        inv = parse_inventario_lsjson(ls.stdout)
    except (json.JSONDecodeError, TypeError):
        return (0, 0)
    plan = planificar_integracion_bandeja(set(inv))
    integrados = colisiones = 0
    for item in plan:
        mv = run_rclone(build_moveto_cmd(
            origen=_remoto(destino, item["origen"]),
            destino=_remoto(destino, item["destino"])))
        if mv.returncode == 0:
            colisiones += int(item["colision"])
            integrados += 1
        else:
            print(f"  ⚠ no se pudo integrar de la bandeja: {item['origen']} (rc={mv.returncode})")
    if plan:
        # Limpiar los directorios vacíos de la bandeja.
        run_rclone([_rclone_bin(), "rmdirs", _remoto(destino, PENDIENTE_CHECKIN_SUBDIR),
                    "--drive-skip-shortcuts"])
    return (integrados, colisiones)


def _upload_evidencia(destino: str, tsc: str, files: list[str]) -> None:
    """Sube los logs de evidencia a `07_AI cowork/merge_<TS>/` (CP9)."""
    for f in files:
        p = Path(f)
        if p.exists():
            run_rclone(build_copyto_cmd(
                origen=str(p), destino=_remoto(destino, f"07_AI cowork/merge_{tsc}/{p.name}")))


def _append_evento_drive(
    destino: str,
    work_dir: Path,
    *,
    case_id: str,
    event: str,
    details: dict,
    actor: str | None = None,
) -> None:
    """Añade un evento al `_intake_log.jsonl` del Drive por unión (pull→append→push).

    El log es append-only. Como el checkin/checkout ostenta el lock, es el único
    escritor: pull del log actual, append de la línea nueva (schema
    ``{ts, actor, event, case_id, details}``, igual que ``intake_log``), push.
    """
    log_remoto = _remoto(destino, "00_Input/_intake_log.jsonl")
    tmp_in = work_dir / f"_log_pull_{ts_compacto()}.jsonl"
    run_rclone(build_copyto_cmd(origen=log_remoto, destino=str(tmp_in)))
    lineas: list[str] = []
    if tmp_in.exists():
        lineas = [ln for ln in tmp_in.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    entry = {
        "ts": now_iso_utc(),
        "actor": actor or _usuario_por_defecto(),
        "event": event,
        "case_id": case_id,
        "details": details,
    }
    lineas.append(json.dumps(entry, ensure_ascii=False))
    tmp_out = work_dir / f"_log_push_{ts_compacto()}.jsonl"
    tmp_out.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    run_rclone(build_copyto_cmd(origen=str(tmp_out), destino=log_remoto))


def _pull_caso_md(destino: str, work_dir: Path) -> dict:
    """Descarga `_caso.md` del Drive y devuelve su frontmatter parseado ({} si no hay)."""
    from core.utils import read_md
    work_dir.mkdir(parents=True, exist_ok=True)
    tmp = work_dir / f"_caso_drive_{ts_compacto()}.md"
    res = run_rclone(build_copyto_cmd(origen=_caso_md_remoto(destino), destino=str(tmp)))
    if res.returncode != 0 or not tmp.exists():
        return {}
    try:
        fm, _ = read_md(tmp)
        return fm if isinstance(fm, dict) else {}
    except Exception:
        return {}


def _push_caso_md(fm: dict, destino: str, work_dir: Path) -> None:
    """Escribe el `_caso.md` mutado y lo sube al Drive (copyto)."""
    from core.utils import read_md, write_md
    tmp = work_dir / f"_caso_push_{ts_compacto()}.md"
    # Conservar el cuerpo si lo teníamos; si no, cuerpo mínimo.
    cuerpo = ""
    prev = work_dir.glob("_caso_drive_*.md")
    for p in prev:
        try:
            _, cuerpo = read_md(p)
            break
        except Exception:
            pass
    write_md(tmp, fm, cuerpo or "# Caso\n")
    run_rclone(build_copyto_cmd(origen=str(tmp), destino=_caso_md_remoto(destino)))


def _leer_manifest(local: Path) -> dict[str, dict[str, Any]]:
    """Baseline B desde ``MANIFEST_CHECKOUT.json`` ({} si no existe → merge 2 vías)."""
    mf = local / "MANIFEST_CHECKOUT.json"
    if not mf.exists():
        return {}
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
        inv = data.get("inventario")
        return inv if isinstance(inv, dict) else {}
    except Exception:
        return {}


def _nonce() -> str:
    import secrets
    return secrets.token_hex(8)


def _usuario_por_defecto() -> str:
    from core.intake_log import get_actor
    return get_actor()


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="feesdefender",
        description="Biblioteca de casos: checkout/checkin Desktop↔Drive (rclone gdrive_tl).",
    )
    sub = p.add_subparsers(dest="comando", required=True)

    for nombre in ("checkout", "checkin"):
        sp = sub.add_parser(nombre)
        sp.add_argument("case_id")
        sp.add_argument("--local", required=True, help="Ruta de la copia local del caso.")
        sp.add_argument("--remote-path", default="", help="Ruta en el Drive (CASOS/ciudad/...).")
        sp.add_argument("--folder-id", default=None, help="Folder ID del Drive (preferible a la ruta).")
        sp.add_argument("--remote", default=None, help="Remote rclone (default gdrive_tl).")
        sp.add_argument("--team-drive", default=None, help="Shared Drive ID (default TEAM_DRIVE_TL).")
        sp.add_argument("--user", default=None, help="Usuario del checkout (default actor).")
        sp.add_argument("--dry-run", action="store_true")
        if nombre == "checkout":
            sp.add_argument("--notas", default=None)
        if nombre == "checkin":
            sp.add_argument("--wcode", default=None, help="W-code para nombrar el backup-dir.")
            sp.add_argument("--yes", action="store_true", help="Confirma borrados propuestos (CP3).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.comando == "checkout":
        return cmd_checkout(args)
    if args.comando == "checkin":
        return cmd_checkin(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
