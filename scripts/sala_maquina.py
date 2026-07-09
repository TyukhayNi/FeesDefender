"""CLI de la Sala de máquina: OCR+MD de un expediente (skill organizar-sala-maquina).

Uso:
  python -m scripts.sala_maquina plan  "<case_id>"            # solo propuesta
  python -m scripts.sala_maquina apply "<case_id>" [--vision] [--force]
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from core import sala_maquina as sm
from core.config import caso_path
from core.intake_log import append_event

app = typer.Typer(add_completion=False)

_STATE = "_sala_maquina_state.json"


def _estado_previo(case_dir: Path) -> set[str]:
    f = sm._sala_maquina_dir(case_dir) / _STATE
    if not f.exists():
        return set()
    return set(json.loads(f.read_text(encoding="utf-8")).get("procesados", []))


def _guardar_estado(case_dir: Path, shas: set[str]) -> None:
    d = sm._sala_maquina_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / _STATE).write_text(json.dumps({"procesados": sorted(shas)}, ensure_ascii=False, indent=2),
                            encoding="utf-8")


def _construir_plan(case_dir: Path, force: bool):
    previo = set() if force else _estado_previo(case_dir)
    return sm.plan(sm.inventariar(case_dir), previo)


@app.command()
def plan(case_id: str):
    """Muestra la propuesta (Preview) sin escribir nada."""
    case_dir = caso_path(case_id)
    p = _construir_plan(case_dir, force=False)
    nuevos = [d for d in p if not d.skip]
    typer.echo(f"Caso: {case_id}")
    for ruta in ("pdf", "imagen", "nativo", "sin_soporte"):
        n = sum(1 for d in nuevos if d.ruta == ruta)
        if n:
            typer.echo(f"  {ruta}: {n}")
    typer.echo(f"  (saltados por sha ya procesado: {sum(1 for d in p if d.skip)})")


@app.command()
def apply(case_id: str, vision: bool = False, force: bool = False):
    """Ejecuta OCR+MD y escribe la Sala de máquina + cobertura + log."""
    case_dir = caso_path(case_id)
    p = _construir_plan(case_dir, force=force)
    cob = sm.ejecutar(case_dir, p, case_id=case_id, vision=vision)

    sm_dir = sm._sala_maquina_dir(case_dir)
    revisar = case_dir / "01_Procesado" / "_revisar"
    revisar.mkdir(parents=True, exist_ok=True)
    (revisar / "_cobertura.md").write_text(sm.render_cobertura(cob), encoding="utf-8")

    # El estado idempotente solo cuenta lo que produjo salida real (ok/low): un
    # PDF cifrado/bloqueado NO se marca "resuelto", así se reintenta en la
    # siguiente corrida normal de apply (sin --force).
    exitosos = {c.sha256 for c in cob if c.estado in ("ok", "low")}
    procesados = _estado_previo(case_dir) | exitosos
    _guardar_estado(case_dir, procesados)
    append_event(case_id, "procesado_sala_maquina", details={
        "count": len(cob),
        "files": [{"path": c.rel_path, "sha256": c.sha256, "slug": c.slug,
                   "metodo": c.metodo, "estado": c.estado} for c in cob],
    })
    dudosos = [c for c in cob if c.estado != "ok"]
    typer.echo(f"Sala de máquina actualizada: {len(cob)} documentos, {len(dudosos)} a revisar.")
    typer.echo("Siguiente paso sugerido: organizar-sala-lectura sobre este caso.")


if __name__ == "__main__":
    app()
