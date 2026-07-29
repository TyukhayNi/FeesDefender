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
8. **Un fallo de LECTURA del protocolo no es contenido vacío.** Si no se puede
   leer ``_caso.md`` o ``_intake_log.jsonl``, no se escribe, no se libera el lock
   y se sale con 4. Antes se devolvía ``{}``/``[]`` y el push posterior destruía
   los metadatos del caso o el historial forense completo (ver ``ProtocoloIOError``).
   Lo mismo vale para el **listado** de la bandeja: un ``lsjson`` que no se puede
   parsear no es una bandeja vacía, y no autoriza a liberar el lock.
9. **Un fallo de ESCRITURA del protocolo no se reporta como éxito.** Los retornos
   de los ``copyto`` del lock y del log se ignoraban, así que un fallo de red al
   liberar dejaba el caso ``prestado`` en el Drive mientras esta CLI imprimía
   «✓ VERDE … lock liberado» y devolvía 0. Ahora ambos lanzan ``ProtocoloIOError``
   y el ciclo termina en 4 sin afirmar nada que no haya pasado. La frontera es
   deliberada: **estado de protocolo** (lock, log de custodia) es fatal;
   **corroboración** (evidencia del merge, redundancia del ``MANIFEST`` en Drive)
   es un aviso ruidoso que no bloquea, porque los bytes del caso ya están donde
   deben y bloquear dejaría el caso prestado por algo accesorio.

Códigos de salida: ``0`` ok · ``1`` error de la operación · ``2`` abortado sin
efectos (caso no disponible, carrera de lock perdida, ruta local ausente) · ``3``
gate humano pendiente (borrados sin ``--yes``) · ``4`` **no se pudo leer el
protocolo o registrar la traza: estado indeterminado, lock conservado,
recuperación necesaria**.

Nota de alcance: las funciones PURAS (parseo, validación, semáforo, construcción
de comandos, plan) están cubiertas por tests, y desde 2026-07-29 hay además
tests de **orquestación** de ``cmd_checkout``/``cmd_checkin`` con un doble de
rclone (``tests/test_repository_cli_guard_pull.py``; el banco completo llega con
la Fase 0 de la arquitectura dual). Lo que sigue SIN cubrir: rclone real, el
Drive real y la cuota de API. El piloto validó el ciclo a mano y Cowork
re-correrá los evals de la skill. La CLI y la skill comparten el mismo cerebro y
los mismos flags.
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


class ProtocoloIOError(RuntimeError):
    """No se pudo LEER un fichero de protocolo (``_caso.md`` / ``_intake_log.jsonl``).

    Se distingue de «no existe»: un fichero ausente es un estado legítimo (caso
    nuevo sin log), pero un fallo de lectura NO puede tratarse como contenido
    vacío. Tratarlo así destruía datos: ``estado_de_fm({})`` vale ``disponible``,
    así que un pull fallido del ``_caso.md`` hacía que el caso pareciera libre y el
    push posterior lo degradaba a un stub sin ``id_go``; y en el log, un pull
    fallido reemplazaba todo el historial por la línea nueva.

    Política: *fail closed* — no se muta, no se libera el lock, y el operador
    recibe el código de salida 4 (recuperación necesaria).
    """


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
    vetados: int = 0,
) -> str:
    """Devuelve ``"verde"`` / ``"amarillo"`` / ``"rojo"`` (semáforo del checkin).

    - ROJO: fallo sistémico de copia (no borrar nada).
    - AMARILLO: hay conflictos por resolver, la verificación encontró
      diferencias, o un grupo indivisible quedó vetado (revisar; lo sobrescrito
      está en ``_merge_backups/``).
    - VERDE: copia hecha, verificación limpia, sin conflictos y sin vetos.

    ``vetados`` no puede omitirse del amarillo: el caso que motivó el veto (N6c)
    es precisamente uno **sin** conflictos, y salir verde liberaría el lock sin
    que nadie supiera que la mitad del grupo se quedó sin subir.
    """
    if copia_fallo_sistemico:
        return "rojo"
    if conflictos > 0 or vetados > 0 or not verificacion_limpia:
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


def rutas_a_copiar(plan) -> list[str]:
    """Rutas que el checkin SUBE a Drive: solo ``COPY_LOCAL`` y destino de ``RENAME``.

    El merge honra el plan por-fichero: ``PRESERVE_DRIVE`` y ``CONFLICT`` NO se
    suben (el Drive conserva su versión). Se usa como ``--files-from`` del copy y
    del check — así una copia en bloque no pisa lo que el plan decidió preservar
    ni auto-resuelve conflictos.
    """
    return [a.ruta for a in plan if a.accion in (rc.ACCION_COPY_LOCAL, rc.ACCION_RENAME)]


def build_copy_cmd(
    *,
    origen: str,
    destino: str,
    backup_dir: str,
    log_file: str,
    transfers: int = 4,
    files_from: str | None = None,
) -> list[str]:
    """Comando ``rclone copy`` local→Drive con los flags validados en el piloto.

    Con ``files_from`` (lista de rutas del plan) la copia se acota a esos
    ficheros — honra el merge de 3 vías por-fichero.
    """
    cmd = [
        _rclone_bin(), "copy", origen, destino,
        "--checksum", "--drive-skip-shortcuts",
        "--transfers", str(transfers),
    ]
    # rclone RECHAZA --files-from junto con --exclude/--include/--filter ("file
    # filtering rules cannot be used with --files-from"). Con files_from la lista
    # ya es exacta y autoritativa → no se añaden exclusiones.
    if files_from:
        cmd += ["--files-from", files_from]
    else:
        cmd += _exclusiones_rclone()
    cmd += [
        "--backup-dir", backup_dir,
        "--log-level", "INFO", "--log-file", log_file,
    ]
    return cmd


def build_check_cmd(
    *,
    local: str,
    destino: str,
    log_file: str,
    files_from: str | None = None,
) -> list[str]:
    """Comando ``rclone check --one-way --fast-list`` (verificación por hash).

    Con ``files_from`` verifica SOLO los ficheros subidos (los COPY_LOCAL/RENAME):
    los ``PRESERVE_DRIVE`` difieren de local a propósito y no deben marcar
    diferencia.
    """
    cmd = [
        _rclone_bin(), "check", local, destino,
        "--one-way", "--drive-skip-shortcuts", "--fast-list",
    ]
    # --files-from no admite --exclude (ver build_copy_cmd).
    if files_from:
        cmd += ["--files-from", files_from]
    else:
        cmd += _exclusiones_rclone()
    cmd += ["--log-level", "INFO", "--log-file", log_file]
    return cmd


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
        f"- Vetados por grupo indivisible: {resumen[rc.ACCION_VETO_GRUPO]}\n"
    )
    vetados = [a for a in plan if a.accion == rc.ACCION_VETO_GRUPO]
    if vetados:
        lineas.append(
            "\n## Vetados por grupo indivisible (N6)\n\n"
            "Iban a subir, pero un fichero de su grupo no está consistente. Suben los "
            "tres juntos o no sube ninguno: reconcilia el grupo y reintenta.\n"
        )
        for a in vetados:
            lineas.append(f"- `{a.ruta}` — {a.motivo}")
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
    # Un fallo de lectura NO es «caso disponible»: se aborta sin tocar un byte.
    pull = _pull_caso_md(destino, work)
    if pull is None:
        print("  ✗ No se pudo LEER el _caso.md del Drive (¿red, permisos, ruta?). "
              "Abortado sin tocar nada: escribir el lock aquí sobrescribiría los "
              "metadatos canónicos del caso.")
        return 4
    fm_drive, cuerpo_drive = pull
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
    try:
        _push_caso_md(fm_drive, destino, work, cuerpo=cuerpo_drive)
    except ProtocoloIOError as exc:
        print(f"  ✗ {exc}\n  Abortado: no hay lock y no se copió nada. Reintenta "
              f"cuando el remote responda.")
        return 4
    time.sleep(_SYNC_LAG_S)
    pull_check = _pull_caso_md(destino, work)
    if pull_check is None:
        # El lock se escribió pero no se puede verificar. No se copia y NO se
        # cancela: cancelar exigiría demostrar que el nonce vigente es el propio,
        # y eso es justo lo que no se ha podido leer.
        print("  ✗ El lock se escribió pero NO se pudo releer el _caso.md para "
              "verificar el nonce. Lock CONSERVADO, nada copiado. Comprueba el "
              "estado del caso en el Drive antes de reintentar.")
        return 4
    fm_check, cuerpo_check = pull_check
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
        try:
            _push_caso_md(fm_check, destino, work, cuerpo=cuerpo_check)
        except ProtocoloIOError as exc:
            # Doble fallo: la copia no salió Y tampoco se pudo revertir el lock. No
            # se puede afirmar que quedó revertido, que es lo que hacía antes.
            print(f"  ✗ rclone copy falló (rc={res.returncode}) y ADEMÁS no se pudo "
                  f"revertir el lock: {exc}\n  El caso sigue 'prestado' en el Drive: "
                  f"cancela el checkout explícitamente o reintenta. Ver {log_file}")
            return 4
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
    res_mf = run_rclone(build_copyto_cmd(
        origen=str(manifest_path),
        destino=_remoto(destino, "MANIFEST_CHECKOUT.json")))
    if res_mf.returncode != 0:
        # El baseline que el checkin lee es el LOCAL; el del Drive es la redundancia
        # del §3.3 (sobrevivir a la muerte del Desktop). Se pierde esa red, no la
        # función: aviso ruidoso, sin bloquear un checkout ya completo.
        print(f"  ⚠ MANIFEST_CHECKOUT.json no se pudo subir al Drive "
              f"(rc={res_mf.returncode}). El baseline LOCAL existe y el checkin "
              f"funcionará desde esta máquina, pero se ha perdido la copia de "
              f"respaldo del §3.3: si este PC muere, el checkin no tendrá baseline.")

    # Evento forense case_checkout en el _intake_log.jsonl del Drive.
    try:
        _append_evento_drive(destino, work, case_id=args.case_id,
                             event="case_checkout", actor=user,
                             details=rc.evento_checkout_details(
                                 user=user, timestamp=ts, nonce=nonce, maquina=maquina,
                                 ruta_local=str(local), n_ficheros=len(inv),
                                 manifest_hash=_md5(manifest_path)))
    except ProtocoloIOError as exc:
        # La copia local es válida y el lock es nuestro; lo que falta es la traza.
        # No se revierte (el trabajo local sirve) y no se finge éxito.
        print(f"  ⚠ {exc}\n  El checkout está hecho (copia local + MANIFEST) pero el "
              f"evento case_checkout NO quedó registrado. Regístralo antes del "
              f"checkin: la custodia del expediente lo exige.")
        return 4
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
    # N6: miembros de un grupo indivisible que iban a subir y no suben porque un
    # hermano del grupo no está consistente. `plan_merge` ya los degradó, así que
    # `rutas_a_copiar` los excluye solo; aquí se reportan y bloquean el verde.
    vetados = [a for a in plan if a.accion == rc.ACCION_VETO_GRUPO]
    if vetados:
        print(f"  ⚠ {len(vetados)} fichero(s) vetado(s) por grupo indivisible "
              f"(no se suben; ver DELTA):")
        for a in vetados:
            print(f"      {a.ruta}")

    if args.dry_run:
        print("  [dry-run] DELTA_PREVIO.md escrito. Nada tocado.")
        return 0

    # Gate humano (CP3): borrados requieren confirmación explícita (--yes).
    if borrados and not args.yes:
        print(f"  ⚠ {len(borrados)} borrado(s) propuesto(s). Revisa el DELTA "
              f"y relanza con --yes para confirmar. Nada tocado.")
        return 3

    # CP4/CP5: copia por PLAN — solo COPY_LOCAL + destino de RENAME (--files-from).
    # PRESERVE_DRIVE y CONFLICT NO se suben: el Drive conserva su versión (no se
    # auto-resuelve el conflicto ni se pisa lo que solo cambió en Drive). El
    # backup-dir va en el MISMO remote (con team_drive) que el destino.
    backup = backup_dir_arg(remote, args.wcode or args.case_id, tsc, team_drive=team)
    log_file = str(work / nombre_auditlog(tsc))
    a_copiar = rutas_a_copiar(plan)
    copia_fallo = False
    files_from = None
    if a_copiar:
        files_from = str(work / f"copiar_{tsc}.txt")
        Path(files_from).write_text("\n".join(a_copiar) + "\n", encoding="utf-8")
        copia = run_rclone(build_copy_cmd(
            origen=str(local), destino=destino, backup_dir=backup,
            log_file=log_file, files_from=files_from))
        copia_fallo = copia.returncode != 0
    else:
        # Nada que subir (solo preservar/conflicto/skip). Log mínimo para CP9.
        Path(log_file).write_text("sin ficheros que copiar (plan sin COPY_LOCAL/RENAME)\n",
                                  encoding="utf-8")

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

    # CP8: verificación por hash de lo SUBIDO (no por exit code). Solo los
    # COPY_LOCAL/RENAME: los PRESERVE_DRIVE difieren de local a propósito.
    check_log = str(work / f"check_{tsc}.log")
    if a_copiar:
        chk = run_rclone(build_check_cmd(local=str(local), destino=destino,
                                         log_file=check_log, files_from=files_from))
        verificacion_limpia = chk.returncode == 0 and not borrado_fallo
    else:
        Path(check_log).write_text("sin ficheros que verificar\n", encoding="utf-8")
        verificacion_limpia = not borrado_fallo

    semaforo = clasificar_semaforo(
        conflictos=len(conflictos),
        copia_fallo_sistemico=copia_fallo,
        verificacion_limpia=verificacion_limpia,
        vetados=len(vetados),
    )
    print(f"  semáforo: {semaforo.upper()}")

    if semaforo != "verde":
        if vetados and not conflictos:
            # N6c: no hay conflicto que resolver — el grupo quedó descuadrado
            # porque el Drive tiene otra versión de un miembro. Se reconcilia
            # regenerando en local contra la versión del Drive, no a mano.
            print(f"  → {len(vetados)} fichero(s) sin subir por grupo indivisible. "
                  f"Baja la versión del Drive del miembro bloqueante, regenera en "
                  f"local y reintenta el checkin. NO se libera el lock.")
        # CP7: si hay conflictos → estado 'conflicto' (el local SE CONSERVA);
        # el AMARILLO no libera el lock. El ROJO tampoco.
        if conflictos:
            pull_c = _pull_caso_md(destino, work)
            if pull_c is None:
                print("  ✗ Hay conflictos pero NO se pudo leer el _caso.md para marcar "
                      "el estado. No se escribe nada en el Drive (hacerlo con un "
                      "frontmatter vacío destruiría los metadatos del caso). El local "
                      "se conserva y el lock sigue tomado.")
                print(f"  NO se libera el lock. Revisa {log_file} / {check_log}.")
                return 4
            fm, cuerpo_fm = pull_c
            rc.aplicar_estado(fm, "conflicto")
            try:
                _push_caso_md(fm, destino, work, cuerpo=cuerpo_fm)
            except ProtocoloIOError as exc:
                print(f"  ✗ Hay conflictos y NO se pudo marcar el estado en el Drive: "
                      f"{exc}\n  El caso sigue 'prestado' y el local se conserva. "
                      f"Reintenta el checkin cuando el remote responda.")
                print(f"  NO se libera el lock. Revisa {log_file} / {check_log}.")
                return 4
            print(f"  → estado 'conflicto' escrito en el Drive; el local se conserva. "
                  f"Resolver los {len(conflictos)} conflicto(s) (ver DELTA_PREVIO.md) "
                  f"y reintentar el checkin.")
        print(f"  NO se libera el lock. Revisa {log_file} / {check_log}.")
        return 0 if semaforo == "amarillo" else 1

    # CP9: subir el AUDITLOG (último artefacto) a 07_AI cowork/merge_<TS>/.
    evidencia_fallida = _upload_evidencia(destino, tsc, [log_file, check_log])
    if evidencia_fallida:
        print(f"  ⚠ No se pudo subir la evidencia del merge al Drive "
              f"({', '.join(evidencia_fallida)}). El merge está hecho y verificado, "
              f"pero `ultimo_checkin_auditlog` apuntará a un fichero que no llegó: "
              f"consérvalo en local ({log_file}).")

    # Evento forense case_checkin en el _intake_log.jsonl del Drive.
    try:
        _append_evento_drive(destino, work, case_id=args.case_id, event="case_checkin",
                             actor=args.user or _usuario_por_defecto(),
                             details=rc.evento_checkin_details(
                                 user=args.user or _usuario_por_defecto(), timestamp=ts,
                                 copiados=resumen[rc.ACCION_COPY_LOCAL],
                                 preservados=resumen[rc.ACCION_PRESERVE_DRIVE],
                                 borrados=resumen[rc.ACCION_DELETE_DRIVE],
                                 conflictos=0, renombrados=resumen[rc.ACCION_RENAME],
                                 resultado="verde", auditlog=nombre_auditlog(tsc)))
    except ProtocoloIOError as exc:
        # Los bytes ya están arriba y verificados, pero sin traza no se cierra el
        # ciclo: no se integra la bandeja ni se libera el lock. Re-ejecutar converge.
        print(f"  ⚠ {exc}\n  El merge está subido y verificado, pero el evento "
              f"case_checkin NO quedó registrado: NO se libera el lock ni se integra "
              f"la bandeja. Re-ejecuta el checkin (converge).")
        return 4

    # CP10: integrar la bandeja _pendiente_checkin/ (escrituras del pipeline
    # durante el préstamo) y vaciarla (§6).
    try:
        integrados, colisiones = _integrar_bandeja(destino)
    except ProtocoloIOError as exc:
        print(f"  ⚠ {exc}\n  El merge está subido, verificado y registrado, pero la "
              f"bandeja no se pudo integrar: NO se libera el lock. Re-ejecuta el "
              f"checkin (converge).")
        return 4
    if integrados:
        print(f"  ✓ bandeja integrada: {integrados} fichero(s)"
              + (f", {colisiones} como _reingesta_ (colisión, sin sobrescribir)" if colisiones else ""))

    # CP11: liberar el lock en el Drive (prestado → disponible).
    pull_lib = _pull_caso_md(destino, work)
    if pull_lib is None:
        print("  ⚠ El merge está subido y verificado y el evento registrado, pero NO "
              "se pudo leer el _caso.md para liberar el lock. El caso sigue 'prestado' "
              "en el Drive. Re-ejecuta el checkin cuando el remote responda: converge "
              "y solo quedará por liberar el lock.")
        return 4
    fm, cuerpo_lib = pull_lib
    estado_actual = rc.estado_de_fm(fm)
    rc.validar_transicion(estado_actual, "disponible")
    rc.aplicar_lock_liberado(fm, timestamp=ts, auditlog=nombre_auditlog(tsc))
    try:
        _push_caso_md(fm, destino, work, cuerpo=cuerpo_lib)
    except ProtocoloIOError as exc:
        # Este era el camino peor: se imprimía «VERDE … lock liberado» y se devolvía
        # 0 con el caso todavía `prestado` en el Drive.
        print(f"  ⚠ {exc}\n  El merge está subido, verificado y registrado, pero el "
              f"caso sigue 'prestado' en el Drive. Re-ejecuta el checkin cuando el "
              f"remote responda: converge y solo quedará por liberar el lock.")
        return 4
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
    except (json.JSONDecodeError, TypeError) as exc:
        # Antes devolvía (0, 0), indistinguible de «la bandeja estaba vacía», y el
        # checkin seguía hasta LIBERAR EL LOCK creyendo que no quedaba nada por
        # integrar. Mismo patrón que el guard del pull: un listado que no se pudo
        # leer no es un listado vacío.
        raise ProtocoloIOError(
            f"No se pudo listar el Drive para integrar la bandeja "
            f"({PENDIENTE_CHECKIN_SUBDIR}/): {exc}. No se libera el lock: podría "
            f"quedar contenido sin integrar."
        ) from exc
    if ls.returncode != 0:
        raise ProtocoloIOError(
            f"El listado del Drive para la bandeja terminó con rc={ls.returncode}. "
            f"No se libera el lock."
        )
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


def _upload_evidencia(destino: str, tsc: str, files: list[str]) -> list[str]:
    """Sube los logs de evidencia a `07_AI cowork/merge_<TS>/` (CP9).

    Devuelve los nombres que **no** se pudieron subir. La evidencia es
    corroboración, no el merge: un fallo aquí no puede dejar el caso prestado, pero
    tampoco puede pasar en silencio — antes se ignoraba el retorno y el checkin
    escribía `ultimo_checkin_auditlog` apuntando a un fichero que no llegó.
    """
    fallidos: list[str] = []
    for f in files:
        p = Path(f)
        if p.exists():
            res = run_rclone(build_copyto_cmd(
                origen=str(p), destino=_remoto(destino, f"07_AI cowork/merge_{tsc}/{p.name}")))
            if res.returncode != 0:
                fallidos.append(p.name)
    return fallidos


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
    res = run_rclone(build_copyto_cmd(origen=log_remoto, destino=str(tmp_in)))
    lineas: list[str] = []
    if res.returncode == 0 and tmp_in.exists():
        lineas = [ln for ln in tmp_in.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    else:
        # El pull falló. Antes se seguía con `lineas = []`, y el push de más abajo
        # REEMPLAZABA todo el historial forense del caso por esta única línea.
        # Un log ausente sí es legítimo (caso nuevo); un log ilegible, no.
        existe = _remoto_existe(log_remoto)
        if existe is not False:
            raise ProtocoloIOError(
                f"No se pudo leer el _intake_log.jsonl del Drive (rc={res.returncode}"
                + ("; el fichero SÍ existe" if existe else "; existencia indeterminada")
                + "). No se escribe nada: hacerlo borraría el historial. "
                  "Reintenta cuando el remote responda."
            )
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
    res_push = run_rclone(build_copyto_cmd(origen=str(tmp_out), destino=log_remoto))
    if res_push.returncode != 0:
        # Simétrico al guard del pull: el retorno se ignoraba, así que el caller
        # continuaba —hasta liberar el lock— creyendo registrada una traza que no
        # llegó al Drive.
        raise ProtocoloIOError(
            f"No se pudo subir el _intake_log.jsonl al Drive (rc={res_push.returncode}). "
            f"El evento {event!r} NO quedó registrado."
        )


def _remoto_existe(ruta_remota: str) -> bool | None:
    """¿Existe esa ruta en el remote? ``None`` si no se pudo determinar.

    Contrato verificado con **rclone v1.73.5 (Windows amd64)**: ``lsjson`` de una
    ruta inexistente devuelve **exit 3** (con ``stdout`` = ``"["``, JSON inválido);
    de una existente, exit 0. Cualquier otro código es indeterminación, y la
    indeterminación se trata como fallo (no como ausencia).
    """
    res = run_rclone([_rclone_bin(), "lsjson", ruta_remota, "--drive-skip-shortcuts"])
    if res.returncode == 0:
        return True
    if res.returncode == 3:
        return False
    return None


def _pull_caso_md(destino: str, work_dir: Path) -> tuple[dict, str] | None:
    """Descarga `_caso.md` del Drive → ``(frontmatter, cuerpo)``, o ``None`` si falla.

    ``None`` significa **no se pudo leer** (rclone falló, el fichero no está, o el
    contenido no es parseable). El caller NO puede interpretarlo como caso
    disponible ni como fichero vacío: antes se devolvía ``{}`` para los tres casos y
    ``estado_de_fm({})`` vale ``disponible``, así que un hipo de red bastaba para
    que el checkout creyera el caso libre y sobrescribiera el ``_caso.md`` canónico
    con un stub. Aquí se falla cerrado y decide el caller.

    El **cuerpo** se devuelve junto al frontmatter porque ``_push_caso_md`` lo
    necesita: reconstruirlo por su cuenta era lo que lo degradaba a ``# Caso``.
    """
    from core.utils import read_md
    work_dir.mkdir(parents=True, exist_ok=True)
    tmp = work_dir / f"_caso_drive_{ts_compacto()}.md"
    res = run_rclone(build_copyto_cmd(origen=_caso_md_remoto(destino), destino=str(tmp)))
    if res.returncode != 0 or not tmp.exists():
        return None
    try:
        fm, cuerpo = read_md(tmp)
    except Exception:
        return None
    return (fm if isinstance(fm, dict) else {}), cuerpo


def _push_caso_md(fm: dict, destino: str, work_dir: Path, *, cuerpo: str) -> None:
    """Escribe el `_caso.md` mutado y lo sube al Drive (copyto).

    ``cuerpo`` es **obligatorio** y viene del mismo pull que produjo ``fm``. Antes se
    adivinaba con ``work_dir.glob("_caso_drive_*.md")`` tomando el primero que
    saliera: sin pull previo el cuerpo se perdía (``# Caso``), y con dos pulls en el
    mismo directorio el elegido dependía del orden arbitrario del glob.
    """
    from core.utils import write_md
    tmp = work_dir / f"_caso_push_{ts_compacto()}.md"
    write_md(tmp, fm, cuerpo or "# Caso\n")
    res = run_rclone(build_copyto_cmd(origen=str(tmp), destino=_caso_md_remoto(destino)))
    if res.returncode != 0:
        # El retorno se ignoraba: un push fallido de la LIBERACIÓN dejaba el caso
        # `prestado` en el Drive mientras el checkin imprimía «lock liberado» y
        # devolvía 0. El estado del lock que el caller cree haber escrito no existe.
        raise ProtocoloIOError(
            f"No se pudo subir el _caso.md al Drive (rc={res.returncode}). El estado "
            f"del lock en el Drive NO cambió."
        )


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
