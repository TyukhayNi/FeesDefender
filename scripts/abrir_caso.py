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
    case_manager, config, email_export, intake_drive, intake_log, intake_manual,
    sudespacho_create, whatsapp_intake,
)
from core.casos import case_locator
from core.ciudades import CIUDADES
from core.utils import file_sha256

app = typer.Typer(add_completion=False, help="Abrir un expediente E&V en una pasada")

_ELEMENT_EXTRAJUDICIAL = "extrajudiciales"


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


def _inventario_desde_hashes(case_dir: Path, base: str, hashes: dict[str, str]) -> list[dict]:
    """Inventario {relpath, sha256, size} a partir de {base/rel: sha}."""
    return [
        {"relpath": k[len(base) + 1:], "sha256": v,
         "size": (case_dir / "00_Input" / k).stat().st_size}
        for k, v in hashes.items()
    ]


def _intake_generico(
    case_dir: Path, case_id: str, fuente: str, hashes: dict[str, str], *, base: str,
    dry_run: bool,
) -> None:
    """Camino de custodia orquestado (drive_ev, manual): plan → (dry-run) →
    reconcile → append_event. `hashes` cubre SOLO lo recién depositado.

    `base` es el cajón espejo (drive_ev) o el nombre del lote ya reservado
    (fuentes de entrega); la cadena de custodia toma la fuente de `fuente`,
    no del primer segmento de la ruta.
    """
    inventario = _inventario_desde_hashes(case_dir, base, hashes)
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
        raise typer.Exit(code=1)
    if plan.con_sha:
        # B0-1: `_intake_generico` ya tiene el `case_dir`, asi que el evento cae
        # junto a los documentos que acaba de ingerir.
        intake_log.append_event(case_dir, brain.FUENTE_A_EVENTO[fuente], case_id=case_id,
                                details={"count": len(plan.con_sha), "files": plan.con_sha})


def _intake_drive_ev(ident, case_dir: Path, folder_id, team_id, *, dry_run: bool) -> None:
    intake_drive.pull_drive_ev(ident.case_id, folder_id, team_id)
    subdir = brain.SUBDIR_DRIVE_EV
    hashes = hash_tree_local(case_dir / "00_Input" / subdir, prefijo=subdir)
    _intake_generico(case_dir, ident.case_id, "drive_ev", hashes, base=subdir, dry_run=dry_run)


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
            raise typer.Exit(code=1)
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
        raise typer.Exit(code=1)
    hashes = {f"{lote.name}/{rel}": file_sha256(lote / rel) for rel in rels}
    _intake_generico(case_dir, ident.case_id, "manual", hashes, base=lote.name, dry_run=False)


def _intake_whatsapp(ident, src_str: str, rol: str, *, dry_run: bool) -> None:
    src = Path(src_str)
    if not src.is_file():
        typer.echo(f"[ERROR] --src no existe: {src}", err=True)
        raise typer.Exit(code=1)
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
        raise typer.Exit(code=1)

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
        raise typer.Exit(code=1)

    if fuente == "whatsapp" and rol not in config.WHATSAPP_SUBDIRS:
        typer.echo(f"[ERROR] rol inválido: {rol}. Válidos: {config.WHATSAPP_SUBDIRS}", err=True)
        raise typer.Exit(code=1)


def _despachar_intake(fuente, ident, case_dir, *, folder_id, team_id, src, rol,
                      cuenta, label, dry_run, extraer_adjuntos=False):
    _validar_flags(fuente, folder_id=folder_id, team_id=team_id, src=src, rol=rol,
                   cuenta=cuenta, label=label)
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
        raise typer.Exit(code=1)  # red de seguridad: _FUENTES_CLI ya filtra el valor


def _alta_crm(
    ident: "brain.Identidad",
    *,
    cuantia: float,
    crm_mode: str,
    yes: bool,
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
        return []
    errores: list[str] = []
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

    # 5.2 esqueleto (idempotente; con --case-id el caso ya existe)
    case_manager.ensure_case(
        ident.case_id, titulo=ident.case_id, referencia_crm=ident.case_id,
        tipo_caso=ident.tipo_caso, ciudad=ciudad, direccion=ident.direccion, id_go=ident.w_code,
    )
    case_dir = case_locator.path_for(ident.case_id)

    # 5.3-5.7 intake por fuente
    _despachar_intake(
        fuente, ident, case_dir,
        folder_id=folder_id, team_id=team_id, src=src, rol=rol,
        cuenta=cuenta, label=label, dry_run=dry_run,
        extraer_adjuntos=extraer_adjuntos,
    )
    if dry_run:
        typer.echo(f"[dry-run] esqueleto en {case_dir}; se omiten log de intake y alta CRM")
        raise typer.Exit(code=0)

    _alta_crm(ident, cuantia=cuantia, crm_mode=crm, yes=yes)

    typer.echo(f"OK Caso abierto: {ident.case_id}")


if __name__ == "__main__":
    app()
