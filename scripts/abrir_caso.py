"""CLI local: abrir un expediente E&V (alta + intake + CRM) en una pasada.

Orquestador fino sobre el cerebro puro core.abrir_caso. Único módulo con I/O.
El intake soporta varias fuentes vía --fuente (una por invocación; reentrante):
drive_ev (default, pull rclone), manual (carpeta o .zip), whatsapp (export .zip)
y email (export de etiqueta Gmail).

Para montar solo el esqueleto (sin intake ni CRM), usa `scripts/init_caso.py`.

Uso:
  python -m scripts.abrir_caso --w-code W-02Z2NR --ciudad Barcelona \\
      --tipo-caso VUELTA --codigo-caso BaRS11 --sufijo "Vuelta" \\
      --direccion "Passeig Marítim, 30 - Castelldefels (08860)" \\
      --folder-id <id> --team-id <shared-drive>
  python -m scripts.abrir_caso ... --fuente manual --src <carpeta|.zip>
  python -m scripts.abrir_caso ... --fuente whatsapp --src <.zip> --rol "03_Otros"
  python -m scripts.abrir_caso ... --fuente email --cuenta <gmail> --label <etiqueta>

Intake incremental (identidad desde _caso.md, sin repetir los 6 flags):
  python -m scripts.abrir_caso --case-id W-02Z2NR --fuente manual --src <carpeta|.zip>
  python -m scripts.abrir_caso --case-id W-02Z2NR --fuente email --cuenta <gmail> --label <etiqueta>
"""
from __future__ import annotations

import dataclasses
import hashlib
import zipfile
from pathlib import Path

import typer

from core import abrir_caso as brain
from core import (
    alta_crm_politica, case_manager, config, email_export, intake_drive, intake_log,
    intake_manual, sudespacho_create, sudespacho_relations, whatsapp_intake,
)
from core import apertura_v1 as av1
from core import apertura_v1_estado as estado_v1
from core.casos import case_locator, mutex_sesion
from core.casos.workspace_model import CaseRef
from core.ciudades import CIUDADES
# `now_iso_utc` y NO `now_iso`: la primitiva del mutex rechaza a proposito un instante sin
# offset, porque un timestamp naive se lee en hora LOCAL y el lease se calcularia mal.
from core.utils import file_sha256, now_iso_utc

app = typer.Typer(add_completion=False, help="Abrir un expediente E&V en una pasada")

_ELEMENT_EXTRAJUDICIAL = "extrajudiciales"

#: Nombres de las etapas de V1, en orden. Es tambien el vocabulario de `--hasta`.
ETAPAS_V1 = ("drive", "crm", "sala_maquina")

#: Intentos que la sala de maquina da a un documento antes de saltarlo. Se lee del
#: motor y no se copia: un numero a mano aqui se pudre cuando alli cambie.
from core.sala_maquina import MAX_INTENTOS as SM_MAX_INTENTOS  # noqa: E402


class AbortarApertura(Exception):
    """El intake no puede seguir. **No termina el proceso: lo decide el entrypoint.**

    Existe por `MEJORAS #142`. Las funciones de intake lanzaban `typer.Exit` desde DENTRO
    del bloque de mutex, y eso rompe la propiedad que R12/H12-04 construyo: el `finally`
    de `case_mutex.tomado` **lanza** `MutexPerdido` si el bloque sale limpio y solo lo
    **anota** si hay una excepcion en vuelo. Con un `Exit` en vuelo la perdida de exclusion
    quedaba en una nota que Typer descarta al formatear la salida: invisible.

    Una excepcion de dominio no arregla eso por si sola —sigue estando en vuelo— y por eso
    el handler de `main` **imprime las notas** antes de traducirla a un codigo de salida.
    Lo que si arregla es que quien decide terminar el proceso vuelva a ser el entrypoint.
    """

    def __init__(self, codigo: int = 1):
        super().__init__(f"apertura abortada (codigo {codigo})")
        self.codigo = codigo


def hash_tree_local(root: Path, *, prefijo: str) -> dict[str, str]:
    """SHA-256 recursivo de todos los ficheros bajo root.

    Devuelve {"<prefijo>/<relpath posix>": sha256hex}. Si root no existe, {}.
    """
    if not root.is_dir():
        return {}
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.name in intake_drive.CONTROL_FILES:
            continue
        rel = p.relative_to(root).as_posix()
        out[f"{prefijo}/{rel}"] = file_sha256(p)
    return out


_FUENTES_CLI = ("drive_ev", "manual", "whatsapp", "email")
_MODOS = ("libre", "v1")
_FUENTES_V1 = ("drive_ev",)


def _inventario_desde_hashes(raiz: Path, base: str, hashes: dict[str, str]) -> list[dict]:
    """Inventario {relpath, sha256, size} a partir de {base/rel: sha}.

    `raiz` es la raíz **EFECTIVA** bajo la que viven las claves: el `00_Input` del destino
    que decidió el guard, que con un caso prestado es el de la bandeja.

    Antes recomponía `case_dir / "00_Input" / clave`, o sea la ruta **intencionada**
    (R14/H14-02, CRÍTICO). Con desvío eso es un `FileNotFoundError` o —peor— el tamaño de
    un fichero homónimo del canon, y entonces bytes, hash, manifiesto y evento dejan de
    describir el mismo destino. Eso no es cobertura pendiente: es una afirmación forense
    falsa, y por eso la ronda prohibió diferirlo.
    """
    return [
        {"relpath": k[len(base) + 1:], "sha256": v,
         "size": (raiz / k).stat().st_size}
        for k, v in hashes.items()
    ]


def _intake_generico(
    case_dir: Path, case_id: str, fuente: str, hashes: dict[str, str], *, base: str,
    dry_run: bool, raiz_hashes: Path | None = None,
) -> None:
    """Camino de custodia orquestado (drive_ev, manual): plan → (dry-run) →
    reconcile → append_event. `hashes` cubre SOLO lo recién depositado.

    `base` es el cajón espejo (drive_ev) o el nombre del lote ya reservado
    (fuentes de entrega); la cadena de custodia toma la fuente de `fuente`,
    no del primer segmento de la ruta.

    `raiz_hashes` es la raíz **efectiva** bajo la que viven las claves de `hashes`
    (R14/H14-02). Su default es la canónica —el comportamiento de siempre— y cada
    llamador que pueda ser desviado por el guard pasa la suya. Es aditivo a propósito:
    la vía que no puede desviarse no tiene que enterarse de nada.

    **El evento se queda en el log CANÓNICO** aunque los bytes se desvíen, y eso es
    deliberado: `_intake_log.jsonl` es fila #13 del §25, clase protocolo, exenta del
    desvío. Es también donde el guard deja su propio `pendiente_checkin`, así que las dos
    mitades de la historia quedan en el mismo sitio y en orden.
    """
    inventario = _inventario_desde_hashes(
        raiz_hashes if raiz_hashes is not None else case_dir / "00_Input", base, hashes)
    plan = brain.plan_intake(inventario, intake_log.read_events(case_id), fuente,
                             lote=None if fuente == "drive_ev" else base)
    if dry_run:
        typer.echo(f"[dry-run] {len(plan.depositables)} depositables, "
                   f"{len(plan.items) - len(plan.depositables)} omitidos")
        return
    n_dup = sum(1 for i in plan.items if i.dup)
    n_zero = sum(1 for i in plan.items if i.zero)
    typer.echo(f"Intake: {len(plan.depositables)} depositables, "
               f"{n_dup} duplicados omitidos, {n_zero} de 0 bytes omitidos")
    rec = brain.reconcile(plan, hashes)
    if not rec.ok:
        typer.echo(f"[ERROR] Reconciliación falló: faltan={rec.faltantes} "
                   f"mismatch={rec.mismatches} extra={rec.extras}", err=True)
        raise AbortarApertura(1)   # MEJORAS #142: no se termina el proceso bajo el mutex
    if plan.con_sha:
        # B0-1: `_intake_generico` ya tiene el `case_dir`, asi que el evento cae
        # junto a los documentos que acaba de ingerir.
        intake_log.append_event(case_dir, brain.FUENTE_A_EVENTO[fuente], case_id=case_id,
                                details={"count": len(plan.con_sha), "files": plan.con_sha})


def _intake_drive_ev(ident, case_dir: Path, folder_id, team_id, *,
                     dry_run: bool,
                     force: bool = False) -> intake_drive.DriveIntakeResult:
    """Pull de Drive E&V + cadena de custodia sobre el destino EFECTIVO (R14/H14-02).

    **El dato que hacía barato el arreglo: `DriveIntakeResult` ya traía `target_dir`.**
    El destino que eligió el guard venía de vuelta en el resultado y este llamador lo
    tiraba para recomponer la ruta canónica a mano. No faltaba información: se descartaba.
    """
    try:
        res = intake_drive.pull_drive_ev(ident.case_id, folder_id, team_id, force=force)
    except intake_drive.DriveIntakeError as exc:
        # R15/H15-06: un `rclone` no cero puede haber copiado PARTE del árbol, y esos bytes
        # se quedan en el expediente. Antes la excepción subía sin que nada los inventariase,
        # así que quedaban depositados y **sin un solo evento** que dijera qué llegó ni que
        # la operación había fallado. Custodia partida en dos.
        #
        # Se emite `pull_drive_ev` con `status: fallo` —el vocabulario de `INTAKE_EVENTS` es
        # cerrado y no se añade un evento a la ligera; el patrón `status` ya lo usa
        # `contenido_adjuntos`— y se relanza. Registrar lo parcial NO es declararlo un
        # intake correcto: el status lo dice y el comando sigue fallando.
        parcial = getattr(exc, "result", None)
        destino = getattr(parcial, "target_dir", None)
        if destino is not None:
            hashes = hash_tree_local(destino, prefijo=brain.SUBDIR_DRIVE_EV)
            intake_log.append_event(
                case_dir, "pull_drive_ev", case_id=ident.case_id,
                details={"status": "fallo", "count": len(hashes),
                         "files": [{"path": k, "sha256": v} for k, v in hashes.items()],
                         "rclone_returncode": getattr(parcial, "rclone_returncode", None)})
            typer.echo(
                f"[ERROR] el pull falló y quedaron {len(hashes)} ficheros parciales; "
                f"registrados en el log con status=fallo antes de abortar", err=True)
        raise

    subdir = brain.SUBDIR_DRIVE_EV
    # `target_dir` es `<algo>/00_Input/01_Drive EV`, así que su padre es la raíz bajo la
    # que resuelven las claves `01_Drive EV/...`. Con el caso disponible es el `00_Input`
    # del caso; con el caso prestado, el de la bandeja.
    hashes = hash_tree_local(res.target_dir, prefijo=subdir)
    _intake_generico(case_dir, ident.case_id, "drive_ev", hashes, base=subdir,
                     dry_run=dry_run, raiz_hashes=res.target_dir.parent)
    # Lo devuelve para que el secuenciador de V1 pueda informar sin rodear esta funcion:
    # la custodia (hashes del destino EFECTIVO, reconciliacion y el registro de los bytes
    # parciales de un pull fallido) vive aqui, y un adaptador que la esquive la deroga.
    return res


def _inventario_local(src: Path) -> list[dict]:
    """Inventario {relpath, sha256, size} de un origen local (carpeta o .zip),
    SIN copiar. Usado por el dry-run de manual."""
    items: list[dict] = []
    if src.is_dir():
        for p in sorted(src.rglob("*")):
            if p.is_file():
                items.append({"relpath": p.relative_to(src).as_posix(),
                              "sha256": file_sha256(p), "size": p.stat().st_size})
    elif zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as zf:
            for m in zf.infolist():
                if m.is_dir():
                    continue
                data = zf.read(m)
                items.append({"relpath": m.filename,
                              "sha256": hashlib.sha256(data).hexdigest(), "size": m.file_size})
    else:
        raise FileNotFoundError(f"--src no es carpeta ni .zip: {src}")
    return items


def _depositar_manual(case_id: str, src: Path, lote: Path) -> list[str]:
    """Deposita el origen en el LOTE (vía intake_manual: guard+M9+manifiesto) y
    devuelve los relpath (posix) depositados en ESTA pasada."""
    if zipfile.is_zipfile(src):
        paths = intake_manual.extract_zip(case_id, src.read_bytes(), lote=lote)
        return [p.relative_to(lote).as_posix() for p in paths]
    if src.is_dir():
        depositados: list[str] = []
        for p in sorted(src.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(src).as_posix()
            intake_manual.save_file_en_lote(case_id, lote, rel, p.read_bytes())
            depositados.append(rel)
        return depositados
    raise FileNotFoundError(f"--src no es carpeta ni .zip: {src}")


def _intake_manual(ident, case_dir: Path, src_str: str, *, dry_run: bool) -> None:
    src = Path(src_str)
    if dry_run:
        try:
            inv = _inventario_local(src)
        except FileNotFoundError as exc:
            typer.echo(f"[ERROR] {exc}", err=True)
            raise AbortarApertura(1) from exc   # MEJORAS #142
        plan = brain.plan_intake(inv, intake_log.read_events(ident.case_id), "manual",
                                 lote="<fecha>_manual_NN")
        typer.echo(f"[dry-run] manual: {len(plan.depositables)} depositables, "
                   "se depositaría en un lote nuevo <fecha>_manual_NN (sin ejecutar)")
        return
    lote = intake_manual.abrir_lote_manual(ident.case_id, origen="abrir_caso_cli")
    try:
        rels = _depositar_manual(ident.case_id, src, lote)
    except FileNotFoundError as exc:
        typer.echo(f"[ERROR] {exc}", err=True)
        raise AbortarApertura(1) from exc   # MEJORAS #142
    hashes = {f"{lote.name}/{rel}": file_sha256(lote / rel) for rel in rels}
    # `lote` ya es el directorio EFECTIVO (`abrir_lote_manual` pasa por el guard), así que
    # los hashes de arriba siempre fueron correctos. Lo que no lo era es el inventario, que
    # resolvía contra la ruta canónica: la vía manual tenía el mismo defecto que #8, latente
    # y sin fila propia en el §25. Se cierra aquí porque es el MISMO arreglo.
    _intake_generico(case_dir, ident.case_id, "manual", hashes, base=lote.name,
                     dry_run=False, raiz_hashes=lote.parent)


def _intake_whatsapp(ident, src_str: str, rol: str, *, dry_run: bool) -> None:
    src = Path(src_str)
    if not src.is_file():
        typer.echo(f"[ERROR] --src no existe: {src}", err=True)
        raise AbortarApertura(1)   # MEJORAS #142
    if dry_run:
        typer.echo(f"[dry-run] whatsapp: se depositaría {src.name} en rol {rol} (sin ejecutar)")
        return
    res = whatsapp_intake.deposit_export(
        ident.case_id, rol, src.read_bytes(), zip_name=src.name)
    if getattr(res, "skipped_dedup", False):
        typer.echo("WhatsApp: export ya importado (dedup), nada nuevo")
    else:
        typer.echo(f"WhatsApp depositado en {getattr(res, 'chat_dir', '?')}")


def _intake_email(ident, case_dir: Path, cuenta: str, label: str, *, dry_run: bool,
                  extraer_adjuntos: bool = False) -> None:
    """Exporta la etiqueta Gmail del caso a un lote nuevo de ``00_Input``.

    ``extraer_adjuntos`` saca además cada adjunto como fichero suelto junto al
    ``.eml`` (que conserva los suyos embebidos, byte-fieles). Importa porque la sala
    de máquina lee ``00_Input``: sin extraer, un adjunto que llegue SOLO por correo
    —sin copia en el Drive— no se OCR-ea ni aparece en la sala de lectura
    (``MEJORAS #68.a``). El default no cambia: activarlo mueve la superficie de dedup
    de todo intake futuro, así que es decisión explícita de quien abre el caso.
    """
    if dry_run:
        extra = " (extrayendo adjuntos)" if extraer_adjuntos else ""
        typer.echo(f"[dry-run] email: se exportaría la etiqueta {label!r} de {cuenta} "
                   f"a un lote nuevo 00_Input/<fecha>_email_NN{extra} (sin ejecutar)")
        return
    dest = email_export.email_dest_dir(ident.case_id)     # reserva el lote (T8)
    email_export.export_label(cuenta, label, dest, case_id=ident.case_id,
                              extract_attachments=extraer_adjuntos)
    typer.echo(f"Email: etiqueta {label!r} exportada a {dest}")


def _validar_flags(fuente, *, folder_id, team_id, src, rol, cuenta, label) -> None:
    """Exige los flags propios de la fuente y rechaza los ajenos (fail-fast)."""
    requeridos = {
        "drive_ev": [],
        "manual": [("--src", src)],
        "whatsapp": [("--src", src), ("--rol", rol)],
        "email": [("--cuenta", cuenta), ("--label", label)],
    }[fuente]
    faltan = [n for n, v in requeridos if not v]
    if faltan:
        typer.echo(f"[ERROR] Fuente {fuente}: faltan flags {faltan}", err=True)
        raise AbortarApertura(1)

    ajenos = {
        "drive_ev": [("--src", src), ("--rol", rol), ("--cuenta", cuenta), ("--label", label)],
        "manual": [("--rol", rol), ("--cuenta", cuenta), ("--label", label),
                   ("--folder-id", folder_id), ("--team-id", team_id)],
        "whatsapp": [("--cuenta", cuenta), ("--label", label),
                     ("--folder-id", folder_id), ("--team-id", team_id)],
        "email": [("--src", src), ("--rol", rol),
                  ("--folder-id", folder_id), ("--team-id", team_id)],
    }[fuente]
    presentes = [n for n, v in ajenos if v]
    if presentes:
        typer.echo(f"[ERROR] Fuente {fuente}: flags ajenos a la fuente {presentes}", err=True)
        raise AbortarApertura(1)

    if fuente == "whatsapp" and rol not in config.WHATSAPP_SUBDIRS:
        typer.echo(f"[ERROR] rol inválido: {rol}. Válidos: {config.WHATSAPP_SUBDIRS}", err=True)
        raise AbortarApertura(1)


def _despachar_intake(fuente, ident, case_dir, *, folder_id, team_id, src, rol,
                      cuenta, label, dry_run, extraer_adjuntos=False):
    """Despacha el intake de UNA fuente. **Ya no valida flags**: eso corre antes del
    mutex (`MEJORAS #142`), porque fallar por un flag mal puesto no necesita el lock
    adquirido y hacerlo dentro convertia el fallo en un `Exit` bajo exclusion."""
    if fuente == "drive_ev":
        _intake_drive_ev(ident, case_dir, folder_id, team_id, dry_run=dry_run)
    elif fuente == "manual":
        _intake_manual(ident, case_dir, src, dry_run=dry_run)
    elif fuente == "whatsapp":
        _intake_whatsapp(ident, src, rol, dry_run=dry_run)
    elif fuente == "email":
        _intake_email(ident, case_dir, cuenta, label, dry_run=dry_run,
                      extraer_adjuntos=extraer_adjuntos)
    else:
        raise AbortarApertura(1)  # red de seguridad: _FUENTES_CLI ya filtra el valor


def etapa_drive(ident, case_dir: Path, *, folder_id, team_id, intake=None):
    """Etapa 1 de V1: materializar la carpeta de Drive E&V, con custodia.

    **Pasa por `_intake_drive_ev` y no por `pull_drive_ev`**: la custodia —hashes sobre el
    destino efectivo, reconciliacion, y registro de los bytes parciales de un pull
    fallido— vive ahi, y es el resultado de R14/H14-02 y R15/H15-06. Un adaptador que la
    rodea la deroga en silencio.

    **`force=True` siempre.** La tabla de riesgos de la spec llama al skip por `.pulled`
    «falso punto fijo»: en V1 la consulta remota se hace en cada ronda, y `rclone`
    transfiere solo lo que difiere.
    """
    _intake = intake or _intake_drive_ev
    try:
        res = _intake(ident, case_dir, folder_id, team_id, dry_run=False, force=True)
    except Exception as exc:  # noqa: BLE001 — el estado de V1 es el producto, no la traza
        return av1.EtapaResultado(nombre="drive", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")
    if res.errors or res.rclone_returncode != 0:
        return av1.EtapaResultado(
            nombre="drive", estado="fallo",
            detalle=f"rclone rc={res.rclone_returncode}; errores={res.errors}")
    if res.skipped:
        # Con `force=True` esto no deberia poder pasar. Si pasa, el marcador `.pulled`
        # volvio al camino y la ronda NO consulto Drive: decirlo `saltada` seria firmar
        # el falso punto fijo que la spec prohibe.
        return av1.EtapaResultado(
            nombre="drive", estado="fallo",
            detalle="la consulta remota no se hizo: el pull devolvio `skipped` pese a "
                    "pedirse con force=True")
    # `files_after` cuenta SOLO el primer nivel del destino (`core/intake_drive.py:120`),
    # y los documentos de un caso viven en subcarpetas. Reportarlo era decir «0 ficheros»
    # justo despues de depositar dos — medido en la corrida real sobre W-02Q38C el
    # 2026-09-03. Un proxy en vez de la cosa, otra vez.
    try:
        total = sum(1 for p in res.target_dir.rglob("*")
                    if p.is_file() and p.name not in intake_drive.CONTROL_FILES)
    except OSError as exc:
        return av1.EtapaResultado(
            nombre="drive", estado="hecha",
            detalle=f"consultado, pero no se pudo contar el destino: {exc}")
    return av1.EtapaResultado(
        nombre="drive", estado="hecha",
        detalle=f"consulta remota hecha; {total} documento(s) en el destino")


#: Vocabulario cerrado de ramas del CRM. `_ELEMENT_EXTRAJUDICIAL` ya existe arriba y lo
#: usa el alta: aqui se reutiliza, no se inventa.
_ELEMENT_JUDICIAL = "expedientes_judiciales"
ELEMENTS_CRM = frozenset({_ELEMENT_EXTRAJUDICIAL, _ELEMENT_JUDICIAL})


def traducir_pull_crm(res) -> tuple[str, str, tuple]:
    """`PullResultV2` -> (estado, detalle, pendientes). Tres ramas, las tres alcanzables.

    **Reescrita tras la R-B, y la leccion es el orden de las preguntas.** La version
    anterior leia `errors` primero y lo trataba como fatal. Pero el PRODUCTOR
    (`core/sync_sudespacho.pull_expediente_v2`) mete en `errors` el aviso de un gestor
    documental **vacio** —que no es un error— y ademas incrementa `documents_failed` en el
    mismo bloque que su `errors.append`. Resultado medido: las ramas de «vacio confirmado»
    y «documentos fallidos» eran INALCANZABLES, y un expediente sin documentos dejaba V1
    `bloqueado` sin correr el OCR.

    **Quien clasifica es el productor**, via `sync_sudespacho.es_gestor_vacio`: la forma en
    que codifica «vacio» es suya, y replicarla aqui la duplicaria.

    **Y un cambio de criterio propio:** unos documentos que no se descargan dejan el espejo
    del CRM incompleto. La version anterior seguia con un pendiente; para prueba documental
    de un litigio eso es peor que parar, asi que ahora **bloquea** y el operador re-corre.
    """
    from core import sync_sudespacho

    if getattr(res, "blocked_legacy_v1", False):
        return "fallo", "el expediente esta bloqueado por el legado v1", ()
    if sync_sudespacho.es_gestor_vacio(res):
        return ("saltada", "el gestor documental del expediente esta vacio",
                (av1.Pendiente(
                    codigo="crm_gestor_vacio",
                    detalle="El expediente existe en el CRM y su gestor documental no "
                            "tiene documentos. No es un fallo; es que no hay nada."),))
    errores = list(getattr(res, "errors", []) or [])
    if errores:
        return "fallo", f"el pull devolvio errores: {errores}", ()
    return "hecha", f"{getattr(res, 'documents_written', 0)} documento(s) escritos", ()


def etapa_crm(ident, case_dir: Path, *, leer_meta=None, pull=None):
    """Etapa 2 de V1: pull del expediente CRM ya registrado.

    **El `element` sale del `ExpedienteLink`, pertenece al vocabulario cerrado, y la rama
    judicial aborta.** El criterio 38 pide los dos cruces: el obvio —que un caso judicial
    no entre por la via extrajudicial— y el que produce el default de
    `core/sync_sudespacho.py:1356`, que es el inverso y el que nadie prueba.
    """
    from core import sync_sudespacho

    _leer = leer_meta or case_locator.read_case_meta
    _pull = pull or sync_sudespacho.pull_expediente_v2

    try:
        meta = _leer(case_dir)
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="crm", estado="fallo",
                                  detalle=f"no se pudo leer _caso.md: {exc}")

    links = list(meta.get("sudespacho_expedientes") or [])
    if not links:
        return av1.EtapaResultado(
            nombre="crm", estado="saltada",
            detalle="sin expediente CRM registrado en _caso.md",
            pendientes=(av1.Pendiente(
                codigo="crm_sin_expediente",
                detalle="El caso no tiene expediente CRM vinculado, asi que no hay nada "
                        "que pullar. El alta CRM es de V2."),))

    # Las tres puertas de la rama se comprueban ANTES de pullar nada: con dos expedientes
    # vinculados, descubrir el segundo invalido a mitad dejaria el primero ya escrito.
    for link in links:
        el = link.get("element")
        if not el:
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"el expediente {link.get('id')!r} no declara `element` en "
                        f"_caso.md. No se adivina: el default del pull es judicial.")
        if el not in ELEMENTS_CRM:
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"`element` fuera del vocabulario: {el!r}; validos: "
                        f"{sorted(ELEMENTS_CRM)}")
        if el == _ELEMENT_JUDICIAL:
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"el expediente {link.get('id')!r} es de la rama judicial, que "
                        f"sigue bloqueada: V1 no tiene adaptador judicial verificado.")

    hechos, pendientes, vacios = [], [], 0
    for link in links:
        try:
            res = _pull(ident.case_id, str(link["id"]), element=link["element"])
        except Exception as exc:  # noqa: BLE001
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"pull de {link['id']} fallo: {type(exc).__name__}: {exc}")
        estado, detalle, pend = traducir_pull_crm(res)
        if estado == "fallo":
            return av1.EtapaResultado(nombre="crm", estado="fallo",
                                      detalle=f"{link['id']}: {detalle}")
        if estado == "saltada":
            vacios += 1
        hechos.append(f"{link['id']} ({detalle})")
        pendientes.extend(pend)

    # `saltada` solo si TODOS lo fueron: un expediente vacio junto a otro con documentos
    # es una etapa hecha.
    estado = "saltada" if vacios == len(links) else "hecha"
    return av1.EtapaResultado(nombre="crm", estado=estado,
                              detalle="; ".join(hechos), pendientes=tuple(pendientes))


def etapa_sala_maquina(ident, *, correr=None):
    """Etapa 3 de V1: atomizacion del correo depositado + OCR y espejos MD.

    La maquina de estados es la del §24 D4: el motor NO cambia —el OCR sigue aunque la
    atomizacion falle, y eso no se regresa— y lo que cambia es el RESULTADO de V1, que si
    lo refleja.

    El import va dentro: `scripts/sala_maquina` arrastra el motor de OCR y el atomizador,
    y pagarlo en cada arranque del modo `libre` seria una regresion para sus llamadores.
    """
    def _correr():
        from scripts import sala_maquina
        return sala_maquina.apply(case_id=ident.case_id)

    try:
        res = (correr or _correr)()
    except typer.Exit as exc:
        codigo = getattr(exc, "exit_code", 0) or 0
        if codigo:
            return av1.EtapaResultado(
                nombre="sala_maquina", estado="fallo",
                detalle=f"la sala de maquina salio con codigo {codigo}")
        res = None
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="sala_maquina", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")

    status = getattr(res, "status_atomizacion", None)
    # `MEJORAS #144`: los documentos que el OCR no pudo procesar tienen que APARECER en
    # los pendientes. Antes se imprimian y nada mas, asi que el evento forense decia
    # «preparado con pendientes» enumerando pendientes ajenos a la documental.
    agotados = int(getattr(res, "documentos_agotados", 0) or 0)

    pendientes = []
    if agotados:
        pendientes.append(av1.Pendiente(
            codigo="ocr_documentos_agotados",
            detalle=f"{agotados} documento(s) llevan {SM_MAX_INTENTOS} intentos de "
                    f"procesado agotados y la sala de maquina los salta: su texto NO esta "
                    f"en el corpus. Hay que mirarlos a mano. Reintento: "
                    f"`sala_maquina apply --force`, o `--solo <ruta>`."))

    if status == "fallo":
        return av1.EtapaResultado(
            nombre="sala_maquina", estado="fallo",
            detalle="la atomizacion del correo fallo (§24 D4: bloquea el cierre de V1)",
            pendientes=tuple(pendientes))
    if status == "parcial":
        pendientes.append(av1.Pendiente(
            codigo="atomizacion_parcial",
            detalle="La atomizacion publico con errores o con poda omitida: "
                    "`01_Procesado/Emails` no esta completo. Ver el evento "
                    "`atomizado_email` en `_intake_log.jsonl`."))
        return av1.EtapaResultado(
            nombre="sala_maquina", estado="hecha",
            detalle="OCR hecho; atomizacion PARCIAL",
            pendientes=tuple(pendientes))
    base = ("OCR hecho; sin correo que atomizar" if status is None
            else "OCR hecho; atomizacion ok")
    if agotados:
        base += f"; {agotados} documento(s) con intentos agotados"
    return av1.EtapaResultado(nombre="sala_maquina", estado="hecha", detalle=base,
                              pendientes=tuple(pendientes))


def registrar_cierre_v1(case_dir: Path, ident, resultado) -> None:
    """Deja el estado de V1 en el log forense del caso.

    Es el unico rastro DURABLE de la corrida: la pantalla se pierde, el `.jsonl` no.
    """
    intake_log.append_event(
        case_dir, "apertura_v1_terminada", case_id=ident.case_id,
        details={
            "estado": resultado.estado,
            "parada": resultado.parada,
            "pendientes": [p.codigo for p in resultado.pendientes],
            "etapas": [{"nombre": e.nombre, "estado": e.estado}
                       for e in resultado.etapas],
        },
    )


def codigo_de_salida(estado: str) -> int:
    """`bloqueado` sale distinto de 0: quien invoque la secuencia tiene que poder
    distinguir «termino con pendientes» de «no termino»."""
    return 1 if estado == av1.EstadoV1.BLOQUEADO else 0


def secuencia_v1(ident, case_dir, *, folder_id, team_id, hasta=None, etapas=None):
    """El orden completo de V1 (spec §24 D3): Drive -> CRM -> sala de maquina.

    La atomizacion del correo depositado va DENTRO de la tercera, que es donde el cableado
    de 2026-07-27 la puso; por eso el gotcha del runbook —atomizar y pull antes del OCR—
    se cumple por construccion y no por memoria del operador.

    `etapas` es el punto de inyeccion de los tests. En produccion se construyen aqui.
    """
    if etapas is None:
        etapas = [
            av1.Etapa("drive", lambda: etapa_drive(
                ident, case_dir, folder_id=folder_id, team_id=team_id)),
            av1.Etapa("crm", lambda: etapa_crm(ident, case_dir)),
            av1.Etapa("sala_maquina", lambda: etapa_sala_maquina(ident)),
        ]
    return av1.secuenciar(etapas, hasta=hasta)


def _informar_v1(resultado) -> None:
    """El informe en pantalla. Lo durable es el evento; esto es para el operador."""
    typer.echo("")
    typer.echo(f"=== Apertura V1: {resultado.estado} ===")
    for e in resultado.etapas:
        typer.echo(f"  [{e.estado:>7}] {e.nombre}: {e.detalle}")
    for n in resultado.no_ejecutadas:
        typer.echo(f"  [no corre] {n}")
    if resultado.parada:
        typer.echo(f"  (parada pedida tras la etapa {resultado.parada!r})")
    for p in resultado.pendientes:
        typer.echo(f"  PENDIENTE {p.codigo}: {p.detalle}")


def _alta_crm(
    ident: "brain.Identidad",
    *,
    cuantia: float,
    crm_mode: str,
    yes: bool,
    force: bool = False,
) -> None:
    """5.9 alta CRM con gate + idempotencia (§8: no re-dar de alta si ya hay un
    extrajudicial registrado para este caso) + tolerancia a caída (§9)."""
    if crm_mode != "api":
        typer.echo("CRM omitido (--crm skip): referencia pendiente + TODO")
        return

    expedientes = case_manager.get_case_status(ident.case_id)["expedientes"]
    ya_registrado = any(
        isinstance(e, dict) and e.get("element") == _ELEMENT_EXTRAJUDICIAL
        for e in expedientes
    )
    if ya_registrado:
        typer.echo(
            f"CRM ya registrado (element={_ELEMENT_EXTRAJUDICIAL}), "
            "no se re-da de alta"
        )
        return

    # El chequeo de arriba mira el `_caso.md` LOCAL. Si ese registro se perdio —o el
    # caso se abrio en otra maquina— el CRM puede tener ya el expediente y esto crearia
    # un duplicado en el CRM del cliente. Se pregunta al CRM.
    dup = sudespacho_relations.buscar_expedientes_duplicados(
        w_code=ident.w_code, direccion=ident.direccion,
    )

    # La regla (crear / vincular / bloquear) NO vive aqui: vive en
    # `core/alta_crm_politica.decidir`, que comparte con el formulario «Nuevo caso». Esta
    # funcion solo la traduce a la pantalla de la CLI. Las dos politicas que aplica, por
    # si alguien busca donde se decidieron:
    #   - **fallar cerrado** ante lo que no se pudo consultar (Nikolai, 2026-09-04; R1/H-02
    #     midio que antes se seguia adelante y la proteccion desaparecia justo cuando algo
    #     fallaba). `--force` es la salida explicita y deja escrito lo que no se miro.
    #   - **el W-code manda** sobre la incertidumbre: si ya esta en el CRM, se vincula y
    #     no se crea, se haya podido consultar el resto o no.
    decision = alta_crm_politica.decidir(dup, forzar=force)

    for aviso in decision.avisos:
        if aviso.startswith(alta_crm_politica.SIN_COMPROBAR):
            typer.echo(f"[AVISO] --force: se da de alta {aviso}")
        else:
            typer.echo(f"[AVISO] posible expediente relacionado ({aviso}). "
                       "No bloquea: el mismo inmueble o la misma parte pueden tener varios.")

    if decision.accion == alta_crm_politica.BLOQUEAR:
        for nota in decision.sin_comprobar:
            typer.echo(f"  - sin comprobar: {nota}", err=True)
        typer.echo(
            "[ERROR] No se pudo comprobar si este expediente ya existe en el CRM, asi "
            "que no se da de alta: crearlo a ciegas puede duplicarlo. Reintenta cuando "
            "el CRM responda, o pasa --force si sabes que no existe.",
            err=True,
        )
        raise AbortarApertura(1)

    if decision.accion == alta_crm_politica.VINCULAR:
        donde = ", ".join(f"{el} #{i}" for el, i in decision.candidatos)
        typer.echo(
            f"[ERROR] El CRM ya tiene un expediente con el id GO {ident.w_code}: {donde}. "
            "No se da de alta otro. Si de verdad hacen falta dos, vincula el existente "
            "con `register_expediente` o crealo a mano en el CRM.",
            err=True,
        )
        # MEJORAS #142: `_alta_crm` corre BAJO el mutex, asi que no puede terminar el
        # proceso — un `typer.Exit` en vuelo hace que la perdida de exclusion quede en
        # una nota que Typer descarta. Lo caza el guard de
        # `tests/test_abrir_caso_exit_bajo_mutex.py`, que me cazo a mi al cablear esto.
        raise AbortarApertura(1)

    payload = brain.crm_payload(ident, cuantia=cuantia)  # lee ident.tipo_caso (fd7a39f)
    typer.echo(f"CRM -> alta extrajudicial ref={payload.referencia_cliente} "
               f"posicion={payload.posicion} tags={payload.tags} cuantia={payload.cuantia}")
    if not (yes or typer.confirm("¿Dar de alta en el CRM?")):
        typer.echo("CRM omitido (declinado por el usuario): referencia pendiente + TODO")
        return

    try:
        exp_id = sudespacho_create.create_expediente(payload)
        case_manager.register_expediente(ident.case_id, exp_id, _ELEMENT_EXTRAJUDICIAL)
        typer.echo(f"OK CRM id={exp_id}")
    except Exception as exc:
        typer.echo(
            f"[AVISO] Alta CRM falló ({exc!r}): Drive+intake ya completados, "
            "referencia_crm queda pendiente + TODO."
        )


def _autoderivar_drive_ev(
    *, folder_id, tipo_caso, team_id, codigo_caso, sufijo,
):
    """B5: en --fuente drive_ev, deriva team_id/codigo_caso/sufijo omitidos.

    - sufijo: puro, del tipo_caso (no necesita la Drive API).
    - team_id: driveId de la carpeta (--folder-id).
    - codigo_caso: nombre de la unidad compartida -> config.codigo_de_unidad.

    Los flags explícitos SIEMPRE ganan (solo se rellena lo que viene None).
    Degrada limpio: lo que no se pueda derivar queda None y lo caza el chequeo
    de flags de identidad con un error claro.
    """
    if sufijo is None and tipo_caso:
        sufijo = config.sufijo_de_tipo_caso(tipo_caso)
        typer.echo(f"[auto] --sufijo del tipo_caso: {sufijo!r}")

    if folder_id and (team_id is None or codigo_caso is None):
        info = intake_drive.get_drive_folder_info(folder_id)
        if info is None:
            typer.echo("[auto] No se pudo leer la carpeta de Drive (token/red); "
                       "pasa los flags que falten explícitos.")
            return team_id, codigo_caso, sufijo
        if team_id is None and info.drive_id:
            team_id = info.drive_id
            typer.echo(f"[auto] --team-id del driveId: {team_id}")
        if codigo_caso is None:
            drive_id_eff = team_id or info.drive_id
            unidad = intake_drive.get_shared_drive_name(drive_id_eff) if drive_id_eff else None
            derivado = config.codigo_de_unidad(unidad) if unidad else None
            if derivado:
                codigo_caso = derivado
                typer.echo(f"[auto] --codigo-caso de la unidad {unidad!r}: {codigo_caso}")
            else:
                typer.echo(f"[auto] No pude derivar --codigo-caso de la unidad {unidad!r}; "
                           "pásalo explícito.")
    return team_id, codigo_caso, sufijo


def _derivar_team_id(folder_id):
    """B5: driveId de la carpeta (= --team-id), o None si no se puede leer."""
    if not folder_id:
        return None
    info = intake_drive.get_drive_folder_info(folder_id)
    return info.drive_id if (info and info.drive_id) else None


def validar_modo(
    modo: str,
    *,
    crm: str,
    fuente: str,
    force: bool = False,
    dry_run: bool = False,
    folder_id: str | None = None,
    case_id: str | None = None,
    hasta: str | None = None,
) -> list[str]:
    """Errores que impiden ejecutar en `modo`. Lista vacía = admisible.

    Pura a propósito: la matriz de combinaciones se prueba sin arrancar el CLI ni
    tocar disco, y el orden —validar ANTES de cualquier efecto— queda demostrable.

    Los cuatro parámetros con default los añadió la remediación de R6: la puerta
    solo mirando `crm` y `fuente` admitía tres invocaciones que V1 prohíbe
    (H6-02, H6-03, H6-04). Llevan default para no regresar a los llamadores del
    modo `libre`, donde la función retorna antes de leerlos.
    """
    if modo not in _MODOS:
        return [f"Modo desconocido: {modo!r}. Válidos: {_MODOS}"]
    if modo == "libre":
        if hasta is not None:
            return ["--hasta solo existe en --modo v1: en `libre` no hay secuencia que "
                    "parar, y aceptarlo en silencio fingiria haberla parado."]
        return []
    errores: list[str] = []
    # HA-06 de la R-A. El vocabulario se valida AQUI y no dentro de `secuenciar`, que
    # corre despues de la identidad, del mutex y de `ensure_case`: en la rev. 1 un typo
    # abortaba con el esqueleto del caso ya creado.
    if hasta is not None and hasta not in ETAPAS_V1:
        errores.append(
            f"--hasta {hasta!r} no es una etapa de V1; validas: {list(ETAPAS_V1)}")
    if crm != "skip":
        errores.append(
            f"--modo v1 no escribe en el CRM: exige --crm skip (recibido: {crm!r}). "
            "El default es `api` y alcanza un POST de alta, así que omitir el flag "
            "también aborta."
        )
    if fuente not in _FUENTES_V1:
        errores.append(
            f"--modo v1 solo admite --fuente {_FUENTES_V1[0]} (recibido: {fuente!r}). "
            "V1 no descubre ni exporta correo: `email` ejecuta email_export.export_label, "
            "que llama a Gmail. La atomización local de V1 actúa sobre correo YA depositado "
            "y la ejecuta la sala de máquina."
        )
    # H6-02 (CRÍTICO). Criterio 33 del §14, que el §21.4 mete en los 24 de V1:
    # «--force nunca crea una carpeta sombra». La política de colisión de la spec
    # admite --force SOLO para reutilizar el caso canónico ya resuelto por
    # --case-id; sin él, `resolver_identidad` esquiva `ColisionCaso` y compone un
    # case_id NUEVO para un W-code que ya existe.
    if force and case_id is None:
        errores.append(
            "--modo v1 no admite --force sin --case-id: con el W-code ya presente "
            "compondría un case_id nuevo y crearía una carpeta sombra, que el "
            "criterio 33 prohibe. El intake incremental entra por --case-id."
        )
    # H6-03. `_intake_drive_ev` llama a `pull_drive_ev` ANTES de consultar
    # dry_run, y el corte sale 0 antes del log de intake: una corrida con
    # efectos e incompleta etiquetada como V1. D3 hace al modo dueño del orden
    # COMPLETO, y el §13 exige que V1 termine en uno de sus tres estados.
    if dry_run:
        errores.append(
            "--modo v1 no admite --dry-run: en drive_ev el pull es real de todos "
            "modos y la corrida sale antes del log de intake, o sea con efectos y "
            "sin terminar en ninguno de los tres estados del contrato."
        )
    # H6-04. `_validar_flags` no exige nada para drive_ev, así que sin
    # --folder-id el pull recibe None DESPUÉS de que `pull_drive_ev` haya hecho
    # `target_dir.mkdir(...)`: se muta antes de detectar el dato que falta.
    # Se exige siempre en v1, no solo con drive_ev, porque drive_ev es su única
    # fuente y toda ejecución V1 materializa Drive E&V.
    if not folder_id:
        errores.append(
            "--modo v1 exige --folder-id: V1 materializa Drive E&V, y sin ese dato "
            "el pull recibe None después de crear el directorio destino."
        )
    return errores


@app.command()
def main(
    w_code: str | None = typer.Option(None, "--w-code"),
    ciudad: str | None = typer.Option(None, "--ciudad"),
    tipo_caso: str | None = typer.Option(None, "--tipo-caso"),
    codigo_caso: str | None = typer.Option(None, "--codigo-caso"),
    sufijo: str | None = typer.Option(None, "--sufijo"),
    direccion: str | None = typer.Option(None, "--direccion"),
    case_id: str | None = typer.Option(
        None, "--case-id",
        help="Intake incremental: resuelve identidad desde _caso.md (case_id o W-code). "
             "Excluyente con los 6 flags de identidad.",
    ),
    folder_id: str | None = typer.Option(None, "--folder-id"),
    team_id: str | None = typer.Option(None, "--team-id"),
    fuente: str = typer.Option("drive_ev", "--fuente", help="drive_ev|manual|whatsapp|email"),
    modo: str = typer.Option(
        "libre", "--modo",
        help="libre|v1. `v1` es el discriminante de la primera vertical (spec §24 D3): "
             "exige --crm skip y --fuente drive_ev, y valida antes de cualquier efecto."),
    hasta: str | None = typer.Option(
        None, "--hasta",
        help="v1: para DESPUES de esta etapa (drive|crm|sala_maquina). Para reanudar, "
             "relanza con --case-id (los 6 flags de identidad darian ColisionCaso): las "
             "etapas ya hechas se REPITEN, y son idempotentes (Drive vuelve a consultar y "
             "rclone transfiere solo lo que difiere; el pull del CRM se repite; la sala de "
             "maquina no reprocesa lo ya hecho)."),
    src: str | None = typer.Option(None, "--src", help="manual/whatsapp: carpeta o .zip"),
    rol: str | None = typer.Option(None, "--rol", help="whatsapp: rol_subdir"),
    cuenta: str | None = typer.Option(None, "--cuenta", help="email: cuenta gmail"),
    label: str | None = typer.Option(None, "--label", help="email: etiqueta"),
    extraer_adjuntos: bool = typer.Option(
        False, "--extraer-adjuntos",
        help="email: saca cada adjunto como fichero suelto junto al .eml, para que la "
             "sala de máquina lo OCR-ee (un adjunto que llegue SOLO por correo, sin "
             "copia en el Drive, no se procesa sin esto)"),
    cuantia: float = typer.Option(0.0, "--cuantia"),
    crm: str = typer.Option("api", "--crm", help="api|skip"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes", help="auto-confirma el gate CRM"),
) -> None:
    # Puerta del modo (spec §24 D3): se valida ANTES de la identidad, de ensure_case,
    # de todo intake y de toda lectura remota. El orden es la propiedad, no el mensaje.
    errores_modo = validar_modo(
        modo, crm=crm, fuente=fuente,
        force=force, dry_run=dry_run, folder_id=folder_id, case_id=case_id,
        hasta=hasta,
    )
    if errores_modo:
        for e in errores_modo:
            typer.echo(f"[ERROR] {e}", err=True)
        raise typer.Exit(code=1)

    if fuente not in _FUENTES_CLI:
        typer.echo(f"[ERROR] Fuente desconocida: {fuente}. Válidas: {_FUENTES_CLI}", err=True)
        raise typer.Exit(code=1)

    # 5.1 identidad — dos vías excluyentes: --case-id (intake incremental) o los 6 flags.
    flags_ident = [
        ("--w-code", w_code), ("--ciudad", ciudad), ("--tipo-caso", tipo_caso),
        ("--codigo-caso", codigo_caso), ("--sufijo", sufijo), ("--direccion", direccion),
    ]
    if case_id is not None:
        dados = [n for n, v in flags_ident if v is not None]
        if dados:
            typer.echo(f"[ERROR] --case-id es excluyente con los flags de identidad: {dados}", err=True)
            raise typer.Exit(code=1)
        resolved = case_locator.resolve_ref(case_id)
        # `buscar` y no `path_for`: un `--case-id` inexistente tiene que salir
        # por este mensaje, no por una traza. Medido antes de migrar.
        case_dir = case_locator.buscar(resolved)
        if case_dir is None or not (case_dir / "00_Input" / "_caso.md").is_file():
            typer.echo(f"[ERROR] Caso no encontrado para --case-id {case_id!r} "
                       f"(resuelto: {resolved!r})", err=True)
            raise typer.Exit(code=1)
        meta = case_locator.read_case_meta(case_dir)
        tipo_caso_eff, ciudad = meta.get("tipo_caso"), meta.get("ciudad")
        if not tipo_caso_eff or not ciudad:
            typer.echo("[ERROR] _caso.md sin tipo_caso/ciudad; usa los flags de identidad", err=True)
            raise typer.Exit(code=1)
        try:
            codigo_p, direccion_p, w_code_p, sufijo_p = brain.descomponer_case_id(resolved)
        except ValueError:
            typer.echo(
                "[ERROR] --case-id no soporta este formato de case_id "
                f"(usa los 6 flags de identidad): {resolved!r}", err=True,
            )
            raise typer.Exit(code=1)
        ident = brain.resolver_identidad(
            codigo=codigo_p, direccion=direccion_p, w_code=w_code_p, sufijo=sufijo_p,
            tipo_caso=tipo_caso_eff, nombres_existentes=[], force=True,
        )
        # Pin al nombre de carpeta YA VERIFICADO (`resolved`): el round-trip
        # componer(descomponer(...)) normaliza espacios/formato y podría no
        # coincidir byte a byte si la carpeta real no es perfectamente
        # canónica, desviando ensure_case/intake a una carpeta NUEVA (el bug
        # [APER-19] que esta feature previene).
        ident = dataclasses.replace(ident, case_id=resolved)
    else:
        if fuente == "drive_ev":
            team_id, codigo_caso, sufijo = _autoderivar_drive_ev(
                folder_id=folder_id, tipo_caso=tipo_caso,
                team_id=team_id, codigo_caso=codigo_caso, sufijo=sufijo,
            )
        flags_ident_eff = [
            ("--w-code", w_code), ("--ciudad", ciudad), ("--tipo-caso", tipo_caso),
            ("--codigo-caso", codigo_caso), ("--sufijo", sufijo), ("--direccion", direccion),
        ]
        faltan = [n for n, v in flags_ident_eff if v is None]
        if faltan:
            typer.echo(f"[ERROR] faltan flags de identidad {faltan} (o usa --case-id)", err=True)
            raise typer.Exit(code=1)
        if ciudad not in CIUDADES:
            typer.echo(f"[ERROR] Ciudad desconocida: {ciudad}", err=True)
            raise typer.Exit(code=1)
        nombres = [p.name for p in case_locator.list_cases(ciudad)]
        try:
            ident = brain.resolver_identidad(
                codigo=codigo_caso, direccion=direccion, w_code=w_code, sufijo=sufijo,
                tipo_caso=tipo_caso, nombres_existentes=nombres, force=force,
            )
        except brain.ColisionCaso as exc:
            typer.echo(f"[ERROR] {exc}", err=True)
            raise typer.Exit(code=1)
        # `ValueError` sale de `componer_case_id` (`MEJORAS #148`: una dirección con `/`
        # no puede ser una carpeta) y de un `--tipo-caso` desconocido. Sin este `except`
        # las dos salían en traceback, y la primera no salía en absoluto: la corrida
        # terminaba en 0 dejando el intake en una ruta sombra. Muerde ANTES de
        # `ensure_case`, así que no se crea esqueleto alguno.
        except ValueError as exc:
            typer.echo(f"[ERROR] Identidad del caso inválida: {exc}", err=True)
            raise typer.Exit(code=1)
        if ident.requiere_confirmacion and not force:
            typer.echo(f"[AVISO] El código {ident.codigo} ya existe: {ident.colisiones}")
            if not (yes or typer.confirm("¿Crear igualmente con este código?")):
                raise typer.Exit(code=1)

    if ciudad not in CIUDADES:
        typer.echo(f"[ERROR] Ciudad desconocida: {ciudad}", err=True)
        raise typer.Exit(code=1)

    # 5.1.b (B5) drive_ev necesita --team-id para el pull rclone. Se deriva del
    # --folder-id si se omitió — también en la vía --case-id (re-pull), que no
    # pasa por _autoderivar_drive_ev. Si aun así no se resuelve, error limpio
    # (evita el TypeError de rclone con team_id=None). En el camino feliz de 6
    # flags, _autoderivar_drive_ev ya lo fijó y este bloque no vuelve a llamar.
    if fuente == "drive_ev" and team_id is None:
        team_id = _derivar_team_id(folder_id)
        if team_id is not None:
            typer.echo(f"[auto] --team-id del driveId: {team_id}")
        else:
            typer.echo("[ERROR] --fuente drive_ev requiere --team-id: no se pudo "
                       "derivar de --folder-id (sin --folder-id o token/red); "
                       "pásalo explícito.", err=True)
            raise typer.Exit(code=1)

    # 5.2 — a partir de aquí, TODO va bajo el mutex del caso (Plan 3A, Task 5).
    #
    # Este es el punto en que el mutex de #247 empieza a proteger algo: hasta ahora
    # existía, estaba probado y no lo llamaba nadie. El bloque cubre el esqueleto, el
    # intake y el alta CRM, que es la secuencia que D3 pone bajo el dueño del modo.
    #
    # **En los dos modos, no solo en `v1`.** El dolor MEDIDO que justificó D2 es
    # «relanzar el pipeline sobre el mismo caso sin saber si la corrida anterior
    # terminó», y eso pasa en `libre`, que es el modo que se usa hoy. Adquirir solo en
    # `v1` habría dejado el mutex sin proteger nada real otra vez.
    #
    # El reloj va con offset EXPLÍCITO: `case_mutex` rechaza un instante naïve a
    # propósito, y `now_iso` —el mayoritario del repo, 43 usos frente a 5— lo es.
    from core.casos.workspace_model import CaseBusy, MutexPerdido

    # `resultado_v1` se calcula DENTRO del bloque y se consume FUERA (HA-07 de la R-A):
    # `case_mutex.tomado` LANZA `MutexPerdido` si el bloque sale limpio y solo lo ANOTA si
    # hay una excepcion en vuelo. Un `typer.Exit` dentro del `with` convertiria una perdida
    # de exclusion en una salida 0 con el aviso enterrado en una nota del traceback.
    # `MEJORAS #142`: la validacion de flags corre AQUI — fuera del mutex, porque fallar
    # por un flag mal puesto no necesita el lock adquirido y hacerlo dentro dejaba un
    # `typer.Exit` bajo exclusion, que es el defecto entero.
    #
    # **Y despues de resolver identidad, no antes.** Adelantarla del todo cambiaba el
    # diagnostico que ve el operador: con `--fuente manual` y sin flags de identidad, antes
    # decia «faltan los seis flags de identidad» y pasaba a decir solo «falta --src», que
    # es el problema menos fundamental de los dos. Lo midio la ronda de este diff (HD-04):
    # sacar la validacion del lock no autorizaba a reordenar lo que el operador lee.
    try:
        _validar_flags(fuente, folder_id=folder_id, team_id=team_id, src=src, rol=rol,
                       cuenta=cuenta, label=label)
    except AbortarApertura as exc:
        raise typer.Exit(code=exc.codigo) from exc

    resultado_v1 = None
    salida_dry_run = False
    try:
        with mutex_sesion.sostenido(CaseRef(w_code=ident.w_code) if ident.w_code
                                    else CaseRef(case_id=ident.case_id),
                                    ahora_fn=now_iso_utc) as sesion:
            # 5.2 esqueleto (idempotente; con --case-id el caso ya existe)
            case_manager.ensure_case(
                ident.case_id, titulo=ident.case_id, referencia_crm=ident.case_id,
                tipo_caso=ident.tipo_caso, ciudad=ciudad, direccion=ident.direccion,
                id_go=ident.w_code, modo=modo,
            )
            # `localizar` y no `path_for`: el esqueleto acaba de crearse, así que el caso DEBE
            # existir y su ausencia es un fallo, no un valor. Es lo que la clasificación firmada
            # del Task 6 decía para este sitio, y quedó como cabo suelto del 65º cierre; el
            # comportamiento no cambia —`path_for` ya es estricto por defecto— pero el nombre
            # ahora dice qué se espera, que es justo lo que un flag no permite auditar.
            case_dir = case_locator.localizar(ident.case_id)

            if modo == "v1":
                # El estado durable de la spec §11. Se abre ANTES de correr nada: si la
                # corrida muere, lo que queda en disco dice que empezo y no termino.
                previa = estado_v1.leer(case_dir)
                if previa is not None and previa.sin_cerrar():
                    typer.echo(
                        f"[AVISO] la ronda {previa.ronda_id!r} (iniciada "
                        f"{previa.iniciada}) no llego a cerrarse: esta corrida no da por "
                        f"buena su salida.", err=True)
                # Un solo reloj: `ronda_id` e `iniciada` eran dos lecturas y divergian.
                arranque = now_iso_utc()
                ronda = estado_v1.abrir(case_dir, ronda_id=arranque, ahora=arranque)
                resultado_v1 = secuencia_v1(ident, case_dir, folder_id=folder_id,
                                            team_id=team_id, hasta=hasta)
                # **revalidar -> publicar -> liberar**, en ese orden e indivisible.
                #
                # La rev. anterior publicaba FUERA del bloque «para no afirmar un exito
                # que la perdida del lease desmiente», y con eso escribia sin exclusion
                # ninguna: R-C midio la intercalacion `R1 abre / R1 libera / R2 abre / R1
                # cierra`, que deja el fichero con la ronda R1 y BORRA la evidencia de que
                # R2 sigue en curso (HC-02). El comentario de entonces decia, correcto,
                # que «escribir sin mutex es la violacion que el mutex existe para
                # impedir» — y el codigo hacia justo eso cuatro lineas mas abajo.
                #
                # Y `revalidar()` primero porque el gestor cede la sesion y no consultarla
                # deja que una perdida a mitad de una etapa larga pase inadvertida hasta la
                # salida, con dos escritores sobre el mismo expediente (HC-01).
                if not sesion.revalidar():
                    raise MutexPerdido(
                        w_code=getattr(sesion, "w_code", None) or "",
                        detalle="el mutex dejo de ser nuestro antes de publicar el "
                                "resultado: no se escribe nada")
                # El evento forense va PRIMERO (HC-03): el `.jsonl` es append-only y
                # autoritativo, y el `estado.json` es el marcador derivado. Al reves, un
                # append fallido dejaba el estado diciendo «terminada» sin rastro alguno.
                registrar_cierre_v1(case_dir, ident, resultado_v1)
                estado_v1.cerrar(
                    case_dir, ronda, estado=resultado_v1.estado,
                    etapas={e.nombre: e.estado for e in resultado_v1.etapas},
                    ahora=now_iso_utc())
            else:
                # 5.3-5.7 intake por fuente
                _despachar_intake(
                    fuente, ident, case_dir,
                    folder_id=folder_id, team_id=team_id, src=src, rol=rol,
                    cuenta=cuenta, label=label, dry_run=dry_run,
                    extraer_adjuntos=extraer_adjuntos,
                )
                if dry_run:
                    # **El peor de los nueve de `MEJORAS #142`.** Un `Exit(0)` es una
                    # terminacion CON EXITO disfrazada de excepcion, asi que el `finally`
                    # de `case_mutex.tomado` se limitaba a ANOTAR una perdida del lease
                    # sobre ella en vez de lanzarla: anotar una perdida de exclusion sobre
                    # un exito es exactamente la mentira que el mecanismo evita.
                    #
                    # Ahora se marca y se sale FUERA del bloque, con lo que un lease
                    # perdido vuelve a levantar `MutexPerdido` y el operador se entera.
                    typer.echo(
                        f"[dry-run] esqueleto en {case_dir}; se omiten log de intake y alta CRM")
                    salida_dry_run = True
                else:
                    _alta_crm(ident, cuantia=cuantia, crm_mode=crm, yes=yes,
                              force=force)
    except CaseBusy as exc:
        typer.echo(f"=== Apertura: {av1.EstadoV1.BLOQUEADO} ===", err=True)
        typer.echo(f"  otro proceso tiene este caso; espera y reintenta: {exc}", err=True)
        raise typer.Exit(code=codigo_de_salida(av1.EstadoV1.BLOQUEADO))
    except AbortarApertura as exc:
        # El mensaje ya lo imprimio quien aborto. Lo que se anade aqui es lo que Typer
        # descartaba: si el `finally` del mutex anoto una perdida de exclusion sobre esta
        # excepcion, esa nota es lo mas importante de la salida y hay que decirla en voz
        # alta en vez de dejarla en un traceback que nadie ve.
        for nota in getattr(exc, "__notes__", ()) or ():
            typer.echo(f"[AVISO] {nota}", err=True)
        raise typer.Exit(code=exc.codigo) from exc
    except MutexPerdido as exc:
        # NO es lo mismo que `CaseBusy` (R-B/L3-05): aqui puede haber trabajo a medias
        # escrito sin exclusion, y el operador tiene que revisar antes de reintentar.
        typer.echo(f"=== Apertura: {av1.EstadoV1.BLOQUEADO} ===", err=True)
        typer.echo(f"  se PERDIO la exclusion durante la operacion: {exc}", err=True)
        typer.echo("  puede haber trabajo a medias; revisa el caso antes de reintentar.",
                   err=True)
        raise typer.Exit(code=codigo_de_salida(av1.EstadoV1.BLOQUEADO))

    # El registro DURABLE se escribe aqui, fuera del bloque, y solo si el bloque salio
    # limpio (R-B/L3-01, confirmado por cuatro lentes). Dentro, una perdida del lease se
    # anota en vez de lanzarse, asi que el `.jsonl` y el `estado.json` quedaban afirmando
    # un exito que la pantalla desmentia.
    #
    # **Y si se perdio la exclusion no se escribe NADA**, ni siquiera un `bloqueado`:
    # escribir sin mutex es la violacion que el mutex existe para impedir. La ronda queda
    # ABIERTA en disco, y la corrida siguiente la ve `sin_cerrar()` y avisa — que es lo
    # que hace que ese aviso sea el mecanismo y no un adorno.
    # Fuera del bloque queda SOLO lo que no escribe: informar y salir. El `Exit` sigue
    # aqui porque dentro convertiria una perdida del lease en una nota sobre una salida
    # limpia (HA-07 de R-A) — pero ya no hay ninguna escritura a este lado.
    if salida_dry_run:
        raise typer.Exit(code=0)

    if resultado_v1 is not None:
        _informar_v1(resultado_v1)
        raise typer.Exit(code=codigo_de_salida(resultado_v1.estado))

    typer.echo(f"OK Caso abierto: {ident.case_id}")


if __name__ == "__main__":
    app()
