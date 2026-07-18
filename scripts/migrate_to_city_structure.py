"""Migración de CASOS_ROOT a estructura por ciudades.

Dos modos:

    python -m scripts.migrate_to_city_structure plan
    python -m scripts.migrate_to_city_structure apply migration_plan.csv

Plan: ``docs/superpowers/plans/PLAN_SUBDIVISION_CIUDADES.md`` (Fase 4).
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import typer

app = typer.Typer(help="Migración de CASOS_ROOT a estructura por ciudades.")


def _detect_city(case_name: str) -> tuple[str | None, str | None]:
    """Detecta ciudad a partir del prefijo del case_id."""
    from core.case_manager import _parse_equipo_from_case_id
    from core.ciudades import ciudad_de_equipo

    prefix = _parse_equipo_from_case_id(case_name)
    if not prefix:
        return None, None
    city = ciudad_de_equipo(prefix)
    return prefix, city


def _flat_cases() -> list[Path]:
    """Devuelve los expedientes que están en la raíz (flat) de CASOS_ROOT."""
    from core.casos.case_locator import _CITY_NAMES, _root
    from core.ciudades import es_carpeta_de_sistema

    root = _root()
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.iterdir()
        if p.is_dir()
        and not es_carpeta_de_sistema(p.name)
        and p.name not in _CITY_NAMES
    )


@app.command()
def plan() -> None:
    """Genera un CSV con el plan de migración (sin mover nada)."""
    from core.config import settings

    cases = _flat_cases()
    if not cases:
        typer.echo("No hay casos flat en la raíz. Nada que planificar.")
        raise typer.Exit()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_dir = settings.casos_root / "_audit"
    audit_dir.mkdir(exist_ok=True)
    out_path = audit_dir / f"migration_plan_{ts}.csv"

    rows: list[dict] = []
    for p in cases:
        prefix, city = _detect_city(p.name)
        rows.append({
            "expediente": p.name,
            "prefijo": prefix or "",
            "ciudad_detectada": city or "",
            "ciudad_final": city or "_Sin clasificar",
            "accion": "mover",
            "observaciones": "" if city else "prefijo no reconocido",
        })

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    typer.echo(f"Plan generado: {out_path}")
    typer.echo(f"  {len(rows)} expediente(s) a migrar.")

    by_city: dict[str, int] = {}
    for r in rows:
        by_city[r["ciudad_final"]] = by_city.get(r["ciudad_final"], 0) + 1
    for city, count in sorted(by_city.items()):
        typer.echo(f"  → {city}: {count}")

    typer.echo("\nRevisa el CSV y ajusta 'ciudad_final' si es necesario.")
    typer.echo(f"Luego: python -m scripts.migrate_to_city_structure apply \"{out_path}\"")


@app.command()
def apply(
    csv_path: Path = typer.Argument(..., help="Ruta al CSV del plan de migración"),
) -> None:
    """Ejecuta la migración según el CSV del plan."""
    from core.casos.case_locator import append_audit_log, move_to_city, path_for
    from core.config import settings

    if not csv_path.exists():
        typer.echo(f"CSV no encontrado: {csv_path}")
        raise typer.Exit(code=1)

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        typer.echo("CSV vacío. Nada que migrar.")
        raise typer.Exit()

    to_move = [r for r in rows if r.get("accion", "").strip().lower() == "mover"]
    to_skip = [r for r in rows if r.get("accion", "").strip().lower() != "mover"]

    typer.echo(f"Plan: {len(to_move)} movimiento(s), {len(to_skip)} omitido(s).")

    by_city: dict[str, int] = {}
    for r in to_move:
        city = r["ciudad_final"]
        by_city[city] = by_city.get(city, 0) + 1
    for city, count in sorted(by_city.items()):
        typer.echo(f"  → {city}: {count}")

    # Pre-flight: snapshot
    audit_dir = settings.casos_root / "_audit"
    audit_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = audit_dir / f"snapshot_pre_migration_{ts}.json"
    snapshot = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "cases": [
            {"name": r["expediente"], "current_path": str(path_for(r["expediente"]))}
            for r in to_move
        ],
    }
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    typer.echo(f"\nSnapshot pre-migración: {snapshot_path}")

    # Confirmación literal
    confirm = typer.prompt(
        "Escribe MIGRAR para confirmar la ejecución (cualquier otra cosa cancela)"
    )
    if confirm.strip() != "MIGRAR":
        typer.echo("Cancelado.")
        raise typer.Exit()

    ok = 0
    skipped = 0
    errors: list[str] = []

    for r in to_move:
        case_id = r["expediente"]
        city = r["ciudad_final"]
        current = path_for(case_id)

        if current.parent.name == city:
            typer.echo(f"  ⏭ {case_id} — ya en {city}")
            skipped += 1
            continue

        try:
            move_to_city(
                case_id, city,
                motivo=f"migracion_inicial ({ts})",
                usuario="migrate_script",
            )
            typer.echo(f"  ✅ {case_id} → {city}")
            ok += 1
        except Exception as exc:
            msg = f"{case_id}: {exc}"
            typer.echo(f"  ❌ {msg}")
            errors.append(msg)

    typer.echo(f"\nResultado: {ok} movidos, {skipped} ya en destino, {len(errors)} errores.")
    if errors:
        for e in errors:
            typer.echo(f"  ERROR: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
