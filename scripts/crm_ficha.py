"""CLI local: rellenar la ficha CRM completa de un expediente extrajudicial (B1).

Orquestador fino sobre core: resuelve el caso por --case-id, carga el
``_ficha_crm.yaml`` y ejecuta (idempotente) cliente propio EV + contrario +
colaboradores + Notas, con GET de verificación tras cada escritura.

Uso:
  python -m scripts.crm_ficha --case-id W-XXXXXX [--dry-run] [--yes]

Requiere SUDESPACHO_API_KEY (.env). El _ficha_crm.yaml (PII) vive en
data/CASOS/<caso>/00_Input/ y nunca se commitea.
"""
from __future__ import annotations

import typer

from core import case_manager
from core import config
from core.casos import case_locator
from core.crm_ficha import cargar_ficha_yaml
from core.sudespacho_create import get_expediente, update_expediente
from core.sudespacho_relations import (
    ensure_colaborador_vinculado, ensure_contrario_vinculado, get_relaciones, link_ev_mmc,
)

app = typer.Typer(add_completion=False, help="Rellenar la ficha CRM completa de un expediente")

_ELEMENT_EXTRAJUDICIAL = "extrajudiciales"
_FICHA_YAML = "_ficha_crm.yaml"


def _exp_id_de(case_id: str) -> str | None:
    for e in case_manager.get_case_status(case_id)["expedientes"]:
        if isinstance(e, dict) and e.get("element") == _ELEMENT_EXTRAJUDICIAL:
            return str(e.get("id"))
    return None


@app.command()
def main(
    case_id: str = typer.Option(..., "--case-id", help="case_id canónico o W-code"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes", help="auto-confirma la escritura al CRM"),
) -> None:
    resolved = case_locator.resolve_ref(case_id)
    # `buscar` y no `path_for`: el error legible es el contrato de un CLI.
    case_dir = case_locator.buscar(resolved)
    if case_dir is None or not (case_dir / "00_Input" / "_caso.md").is_file():
        typer.echo(f"[ERROR] Caso no encontrado: {case_id!r} (resuelto: {resolved!r})", err=True)
        raise typer.Exit(code=1)

    exp_id = _exp_id_de(resolved)
    if not exp_id:
        typer.echo(f"[ERROR] El caso {resolved!r} no tiene expediente extrajudicial "
                   "registrado; da de alta primero con abrir_caso --crm api", err=True)
        raise typer.Exit(code=1)

    ficha_path = case_dir / "00_Input" / _FICHA_YAML
    try:
        ficha = cargar_ficha_yaml(ficha_path)
    except FileNotFoundError:
        typer.echo(f"[ERROR] Falta {_FICHA_YAML} en {case_dir / '00_Input'}", err=True)
        raise typer.Exit(code=1)
    except ValueError as exc:
        typer.echo(f"[ERROR] {_FICHA_YAML} inválido: {exc}", err=True)
        raise typer.Exit(code=1)

    try:
        cliente_propio_id = config.cliente_propio_id(ficha.cliente_propio)
    except ValueError:
        typer.echo(
            f"[ERROR] cliente_propio desconocido: {ficha.cliente_propio!r}"
            " (ver core.config.CLIENTES_PROPIOS_EV)", err=True,
        )
        raise typer.Exit(code=1)

    plan = [f"cliente propio {ficha.cliente_propio} (id {cliente_propio_id}) → exp {exp_id}"]
    if ficha.contrario:
        plan.append(f"contrario: {ficha.contrario.apellido1} (dedup NIF)")
    plan += [f"colaborador: {c.email or c.nombre} (dedup email)" for c in ficha.colaboradores]
    if ficha.notas_html:
        plan.append("Notas (update_expediente)")
    typer.echo("Plan ficha CRM:\n  - " + "\n  - ".join(plan))

    if dry_run:
        typer.echo("[dry-run] no se escribe nada.")
        raise typer.Exit(code=0)
    if not (yes or typer.confirm("¿Escribir la ficha en el CRM?")):
        typer.echo("Cancelado.")
        raise typer.Exit(code=0)

    #: Lo que la corrida AFIRMA haber vinculado, para contrastarlo por lectura al final.
    esperado: dict[str, list[str]] = {
        "clientes_propios": [str(cliente_propio_id)],
        "clientes_contrarios": [],
        "colaboradores": [],
    }

    try:
        link_ev_mmc(exp_id, cliente_propio_id=cliente_propio_id)
        typer.echo(f"OK cliente propio {ficha.cliente_propio} (id {cliente_propio_id}) vinculado (exp {exp_id})")

        if ficha.contrario:
            cid, creado = ensure_contrario_vinculado(exp_id, ficha.contrario)
            esperado["clientes_contrarios"].append(str(cid))
            typer.echo(f"OK contrario id={cid} ({'creado' if creado else 'existente'}) vinculado")
        for col in ficha.colaboradores:
            colid, creado = ensure_colaborador_vinculado(exp_id, col)
            esperado["colaboradores"].append(str(colid))
            typer.echo(f"OK colaborador id={colid} ({'creado' if creado else 'existente'}) vinculado")
        if ficha.notas_html:
            update_expediente(exp_id, {"Notas": ficha.notas_html})
            typer.echo("OK Notas actualizadas")
    except Exception as exc:  # noqa: BLE001 — tolerancia a caída (spec §7.4), como _alta_crm
        typer.echo(
            f"[ERROR] Falló una escritura al CRM ({exc!r}). "
            "Re-ejecutar es seguro: contrario/colaboradores deduplican por NIF/email.",
            err=True,
        )
        raise typer.Exit(code=1)

    # Verificación POR RESULTADO. El 201 de `relation_element` no prueba el vínculo, y
    # hasta el 2026-09-04 aquí se remataba con «verificar partes visualmente en el CRM»
    # porque se creía que la API no sabía leer relaciones. Sí sabe: `related_register`.
    try:
        rec = get_expediente(exp_id)
        typer.echo(f"Verificación: expediente {exp_id} "
                   f"Numero_Expediente={rec.get('Numero_Expediente')}")
    except Exception as exc:  # noqa: BLE001 — la verificación no debe tumbar el éxito
        typer.echo(f"[AVISO] GET de verificación falló ({exc!r}); revisa manualmente el CRM")

    try:
        rel = get_relaciones(_ELEMENT_EXTRAJUDICIAL, exp_id)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"[AVISO] No se pudieron LEER las relaciones ({exc!r}); "
                   "los vínculos quedan SIN VERIFICAR, que no es lo mismo que mal.")
        typer.echo(f"OK ficha CRM completada: {resolved}")
        return

    faltan: list[str] = []
    for elemento, ids in esperado.items():
        presentes = {str(v.get("id")) for v in rel.get(elemento, [])}
        for quiero in ids:
            marca = "ok" if quiero in presentes else "FALTA"
            typer.echo(f"  [{marca}] {elemento} id={quiero}")
            if quiero not in presentes:
                faltan.append(f"{elemento} id={quiero}")

    if faltan:
        typer.echo(
            "[ERROR] La lectura DESMIENTE la escritura: no están vinculados -> "
            + ", ".join(faltan)
            + ". Los 'OK ... vinculado' de arriba se apoyaban en el status, no en el "
              "resultado.",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(f"OK ficha CRM completada y VERIFICADA por lectura: {resolved}")


if __name__ == "__main__":
    app()
