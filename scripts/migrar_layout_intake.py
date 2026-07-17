"""Migración BAJO DEMANDA de un caso al layout de lotes (spec §7, MEJORAS #54).

Se dispara SOLO cuando el caso recibe un intake nuevo — nunca de oficio ni en
barrido. Envuelve los cajones de entrega en lotes sintéticos y remapea los
registros aguas abajo (M9, cobertura OCR, catálogo). Espejos y protocolo
intactos. Correr TRAS el checkin si el caso estaba prestado.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer
import yaml

from core import config, intake_log, intake_lotes, migrar_layout
from core.case_manager import leer_estado_repositorio
from core.config import caso_path

app = typer.Typer(add_completion=False)


class CasoPrestadoError(RuntimeError):
    """El caso está prestado/conflicto: migrar tras el checkin (§7.6)."""


def _json_atomico(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
                   encoding="utf-8")
    tmp.replace(path)


def migrar(case_id: str, *, dry_run: bool) -> list[migrar_layout.MovimientoCajon]:
    estado = leer_estado_repositorio(case_id)
    if estado in ("prestado", "conflicto"):
        raise CasoPrestadoError(
            f"El caso está '{estado}': la migración se corre tras el checkin "
            "(desviar medio árbol a la bandeja no tiene sentido, spec §7.6).")
    base = caso_path(case_id) / "00_Input"
    plan = migrar_layout.plan_migracion(base)
    if dry_run or not plan:
        return plan

    mapping_total: dict[str, str] = {}
    for mov in plan:
        cajon_dir, lote_dir = base / mov.cajon, base / mov.lote
        lote_dir.mkdir(parents=True, exist_ok=False)
        for hijo in sorted(cajon_dir.iterdir()):
            if (mov.cajon == "03_Email"
                    and hijo.name in config.INTAKE_CONTROL_FILES):
                # estado de canal → raíz de 00_Input (hogar desde #54), no al lote
                destino = base / hijo.name
                if not destino.exists():
                    shutil.move(str(hijo), str(destino))
                else:
                    hijo.unlink()          # ya consolidado en la raíz
                continue
            shutil.move(str(hijo), str(lote_dir / hijo.name))
        intake_lotes.escribir_manifiesto(
            lote_dir, fuente=mov.fuente, fecha_intake=mov.lote[:10],
            origen="migracion_layout",
            items=intake_lotes.items_desde_disco(lote_dir),
            fecha_intake_estimada=True)
        mapping_total.update(mov.mapping)

    remapeados: dict[str, int] = {}
    m9_path = base / "_intake_hashes.json"
    if m9_path.is_file():
        data = json.loads(m9_path.read_text(encoding="utf-8") or "{}")
        data, remapeados["m9"] = migrar_layout.remap_paths(data, mapping_total)
        _json_atomico(m9_path, data)
    cob_path = (caso_path(case_id) / "01_Procesado" / "02_Sala de máquina"
                / "_cobertura.json")
    if cob_path.is_file():
        rows = json.loads(cob_path.read_text(encoding="utf-8") or "[]")
        rows, remapeados["cobertura"] = migrar_layout.remap_cobertura(rows, mapping_total)
        _json_atomico(cob_path, rows)
    cat_path = caso_path(case_id) / "01_Procesado" / "indice_documental.yaml"
    if cat_path.is_file():
        entries = yaml.safe_load(cat_path.read_text(encoding="utf-8")) or []
        entries, remapeados["catalogo"] = migrar_layout.remap_catalogo(
            entries, mapping_total)
        cat_path.write_text(
            yaml.dump(entries, allow_unicode=True, default_flow_style=False,
                      sort_keys=False), encoding="utf-8")

    intake_log.append_event(case_id, "migracion_layout_intake", details={
        "lotes": [m.lote for m in plan], "remapeados": remapeados})
    return plan


@app.command()
def main(case_id: str, dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    try:
        plan = migrar(case_id, dry_run=dry_run)
    except CasoPrestadoError as exc:
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=1)
    if not plan:
        typer.echo("Nada que migrar: sin cajones de entrega con contenido.")
        return
    for mov in plan:
        typer.echo(f"{'[dry-run] ' if dry_run else ''}{mov.cajon} → {mov.lote} "
                   f"({len(mov.mapping)} ficheros)")


if __name__ == "__main__":
    app()
