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
from pathlib import Path

import typer

from core import abrir_caso as brain
from core import case_manager, intake_drive, intake_log, sudespacho_create
from core.casos import case_locator

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
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        rel = p.relative_to(root).as_posix()
        out[f"{prefijo}/{rel}"] = h.hexdigest()
    return out


@app.command()
def main(
    w_code: str = typer.Option(..., "--w-code"),
    ciudad: str = typer.Option(..., "--ciudad"),
    tipo_caso: str = typer.Option(..., "--tipo-caso"),
    codigo_caso: str = typer.Option(..., "--codigo-caso"),
    sufijo: str = typer.Option(..., "--sufijo"),
    direccion: str = typer.Option(..., "--direccion"),
    folder_id: str = typer.Option(None, "--folder-id"),
    team_id: str = typer.Option(None, "--team-id"),
    cuantia: float = typer.Option(0.0, "--cuantia"),
    crm: str = typer.Option("api", "--crm", help="api|skip"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes", help="auto-confirma el gate CRM"),
) -> None:
    # 5.1 identidad + colisión
    nombres = [p.name for p in case_locator.list_cases(ciudad)]
    try:
        ident = brain.resolver_identidad(
            codigo=codigo_caso, direccion=direccion, w_code=w_code, sufijo=sufijo,
            tipo_caso=tipo_caso, nombres_existentes=nombres, force=force,
        )
    except brain.ColisionCaso as exc:
        typer.echo(f"[ERROR] {exc}")
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

    # 5.3 pull + hash local (D4)
    intake_drive.pull_drive_ev(ident.case_id, folder_id, team_id)
    subdir = brain.FUENTE_A_SUBDIR["drive_ev"]
    hashes = hash_tree_local(case_dir / "00_Input" / subdir, prefijo=subdir)

    # 5.4 plan
    inventario = [
        {"relpath": k[len(subdir) + 1:], "sha256": v,
         "size": (case_dir / "00_Input" / k).stat().st_size}
        for k, v in hashes.items()
    ]
    plan = brain.plan_intake(inventario, intake_log.read_events(ident.case_id), "drive_ev")
    if dry_run:
        typer.echo(f"[dry-run] {len(plan.depositables)} depositables, "
                   f"{len(plan.items) - len(plan.depositables)} omitidos")
        raise typer.Exit(code=0)

    # 5.6 reconcile
    rec = brain.reconcile(plan, hashes)
    if not rec.ok:
        typer.echo(f"[ERROR] Reconciliación falló: faltan={rec.faltantes} "
                   f"mismatch={rec.mismatches} extra={rec.extras}")
        raise typer.Exit(code=1)

    # 5.7 log forense con sha256
    if plan.con_sha:
        intake_log.append_event(ident.case_id, "pull_drive_ev",
                                details={"count": len(plan.con_sha), "files": plan.con_sha})

    # 5.9 alta CRM con gate
    if crm == "api":
        payload = brain.crm_payload(ident, cuantia=cuantia)  # lee ident.tipo_caso (fd7a39f)
        typer.echo(f"CRM -> alta extrajudicial ref={payload.referencia_cliente} "
                   f"posicion={payload.posicion} tags={payload.tags} cuantia={payload.cuantia}")
        if yes or typer.confirm("¿Dar de alta en el CRM?"):
            exp_id = sudespacho_create.create_expediente(payload)
            case_manager.register_expediente(ident.case_id, exp_id, _ELEMENT_EXTRAJUDICIAL)
            typer.echo(f"OK CRM id={exp_id}")
    else:
        typer.echo("CRM omitido (--crm skip): referencia pendiente + TODO")

    typer.echo(f"OK Caso abierto: {ident.case_id}")


if __name__ == "__main__":
    app()
