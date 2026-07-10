"""CLI local: abrir un expediente E&V (alta + intake drive_ev + CRM) en una pasada.

Orquestador fino sobre el cerebro puro core.abrir_caso. Único módulo con I/O.

Uso:
  python -m scripts.abrir_caso --w-code W-02Z2NR --ciudad Barcelona \\
      --tipo-caso VUELTA --codigo-caso BaRS11 --sufijo "Vuelta" \\
      --direccion "Passeig Marítim, 30 - Castelldefels (08860)" \\
      --folder-id <id> --team-id <shared-drive>
"""
from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import typer

from core import abrir_caso as brain
from core import case_manager, config, intake_drive, intake_log, sudespacho_create
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


def _inventario_desde_hashes(case_dir: Path, subdir: str, hashes: dict[str, str]) -> list[dict]:
    """Inventario {relpath, sha256, size} a partir de {subdir/rel: sha}."""
    return [
        {"relpath": k[len(subdir) + 1:], "sha256": v,
         "size": (case_dir / "00_Input" / k).stat().st_size}
        for k, v in hashes.items()
    ]


def _intake_generico(
    case_dir: Path, case_id: str, fuente: str, hashes: dict[str, str], *, dry_run: bool
) -> None:
    """Camino de custodia orquestado (drive_ev, manual): plan → (dry-run) →
    reconcile → append_event. `hashes` cubre SOLO lo recién depositado."""
    inventario = _inventario_desde_hashes(case_dir, brain.FUENTE_A_SUBDIR[fuente], hashes)
    plan = brain.plan_intake(inventario, intake_log.read_events(case_id), fuente)
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
        intake_log.append_event(case_id, brain.FUENTE_A_EVENTO[fuente],
                                details={"count": len(plan.con_sha), "files": plan.con_sha})


def _intake_drive_ev(ident, case_dir: Path, folder_id, team_id, *, dry_run: bool) -> None:
    intake_drive.pull_drive_ev(ident.case_id, folder_id, team_id)
    subdir = brain.FUENTE_A_SUBDIR["drive_ev"]
    hashes = hash_tree_local(case_dir / "00_Input" / subdir, prefijo=subdir)
    _intake_generico(case_dir, ident.case_id, "drive_ev", hashes, dry_run=dry_run)


def _despachar_intake(fuente, ident, case_dir, *, folder_id, team_id, src, rol,
                      cuenta, label, dry_run):
    if fuente == "drive_ev":
        _intake_drive_ev(ident, case_dir, folder_id, team_id, dry_run=dry_run)
    else:
        raise typer.Exit(code=1)  # ramas manual/whatsapp/email: tareas posteriores


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


@app.command()
def main(
    w_code: str = typer.Option(..., "--w-code"),
    ciudad: str = typer.Option(..., "--ciudad"),
    tipo_caso: str = typer.Option(..., "--tipo-caso"),
    codigo_caso: str = typer.Option(..., "--codigo-caso"),
    sufijo: str = typer.Option(..., "--sufijo"),
    direccion: str = typer.Option(..., "--direccion"),
    folder_id: str | None = typer.Option(None, "--folder-id"),
    team_id: str | None = typer.Option(None, "--team-id"),
    fuente: str = typer.Option("drive_ev", "--fuente", help="drive_ev|manual|whatsapp|email"),
    src: str | None = typer.Option(None, "--src", help="manual/whatsapp: carpeta o .zip"),
    rol: str | None = typer.Option(None, "--rol", help="whatsapp: rol_subdir"),
    cuenta: str | None = typer.Option(None, "--cuenta", help="email: cuenta gmail"),
    label: str | None = typer.Option(None, "--label", help="email: etiqueta"),
    cuantia: float = typer.Option(0.0, "--cuantia"),
    crm: str = typer.Option("api", "--crm", help="api|skip"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes", help="auto-confirma el gate CRM"),
) -> None:
    if ciudad not in CIUDADES:
        typer.echo(f"[ERROR] Ciudad desconocida: {ciudad}", err=True)
        raise typer.Exit(code=1)

    if fuente not in _FUENTES_CLI:
        typer.echo(f"[ERROR] Fuente desconocida: {fuente}. Válidas: {_FUENTES_CLI}", err=True)
        raise typer.Exit(code=1)

    # 5.1 identidad + colisión
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

    # 5.2 esqueleto
    case_manager.ensure_case(
        ident.case_id, titulo=ident.case_id, referencia_crm=ident.case_id,
        tipo_caso=tipo_caso, ciudad=ciudad, direccion=direccion,
    )
    case_dir = case_locator.path_for(ident.case_id)

    # 5.3-5.7 intake por fuente
    _despachar_intake(
        fuente, ident, case_dir,
        folder_id=folder_id, team_id=team_id, src=src, rol=rol,
        cuenta=cuenta, label=label, dry_run=dry_run,
    )
    if dry_run:
        typer.echo(f"[dry-run] esqueleto en {case_dir}; se omiten log de intake y alta CRM")
        raise typer.Exit(code=0)

    _alta_crm(ident, cuantia=cuantia, crm_mode=crm, yes=yes)

    typer.echo(f"OK Caso abierto: {ident.case_id}")


if __name__ == "__main__":
    app()
