"""Migración BAJO DEMANDA de un caso al layout de lotes (spec §7, MEJORAS #54).

Se dispara SOLO cuando el caso recibe un intake nuevo — nunca de oficio ni en
barrido. Envuelve los cajones de entrega en lotes sintéticos y remapea los
registros aguas abajo (M9, cobertura OCR, catálogo). Espejos y protocolo
intactos. Correr TRAS el checkin si el caso estaba prestado.

Los movimientos físicos (fase 1) son todo-o-nada: si cualquier ``shutil.move``
o ``mkdir`` falla a mitad de camino (fichero bloqueado, permiso, disco lleno),
se revierte lo ya movido antes de propagar el error. Ningún borrado ocurre en
fase 1: los ficheros de control duplicados (``03_Email``) se dejan en su sitio
y se listan en ``duplicados_a_borrar``; el ``unlink`` real se hace en fase 2,
tras confirmar que la fase 1 completó entera. Así fase 1 es genuinamente
reversible (rollback = solo movimientos, nunca borrados) y M9/cobertura/
catálogo (también fase 2) solo se tocan si la fase 1 completó entera — una
migración a medias nunca deja los registros aguas abajo apuntando a rutas que
ya no existen, ni borra nada.
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


def _write_atomico(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _json_atomico(path: Path, data) -> None:
    _write_atomico(
        path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def _yaml_atomico(path: Path, data) -> None:
    _write_atomico(
        path,
        yaml.dump(data, allow_unicode=True, default_flow_style=False,
                  sort_keys=False))


def _mapping_documental(mov: migrar_layout.MovimientoCajon) -> dict[str, str]:
    """Sub-mapping de ``mov`` excluyendo los ficheros de control del canal
    email, que se desvían a la raíz de 00_Input/ y nunca llegan al lote."""
    if mov.cajon != "03_Email":
        return mov.mapping
    return {k: v for k, v in mov.mapping.items()
            if Path(k).name not in config.INTAKE_CONTROL_FILES}


def migrar(case_id: str, *, dry_run: bool) -> list[migrar_layout.MovimientoCajon]:
    estado = leer_estado_repositorio(case_id)
    if estado in (config.ESTADO_REPO_PRESTADO, config.ESTADO_REPO_CONFLICTO):
        raise CasoPrestadoError(
            f"El caso está '{estado}': la migración se corre tras el checkin "
            "(desviar medio árbol a la bandeja no tiene sentido, spec §7.6).")
    base = caso_path(case_id) / "00_Input"
    plan = migrar_layout.plan_migracion(base)
    if dry_run or not plan:
        return plan

    # --- Fase 1: movimientos físicos, todo-o-nada -------------------------
    hechos: list[tuple[Path, Path]] = []
    lotes_creados: list[Path] = []
    mapping_total: dict[str, str] = {}
    duplicados_a_borrar: list[Path] = []
    try:
        for mov in plan:
            cajon_dir, lote_dir = base / mov.cajon, base / mov.lote
            lote_dir.mkdir(parents=True, exist_ok=False)
            lotes_creados.append(lote_dir)
            for hijo in sorted(cajon_dir.iterdir()):
                if (mov.cajon == "03_Email"
                        and hijo.name in config.INTAKE_CONTROL_FILES):
                    # estado de canal → raíz de 00_Input (hogar desde #54), no al lote
                    destino = base / hijo.name
                    if not destino.exists():
                        shutil.move(str(hijo), str(destino))
                        hechos.append((hijo, destino))
                    else:
                        # ya consolidado en la raíz: el duplicado NO se borra
                        # aquí (Finding 1) — un borrado en fase 1 no sería
                        # reversible por el rollback. Se deja en su sitio y
                        # se borra en fase 2, solo si la fase 1 completa entera.
                        duplicados_a_borrar.append(hijo)
                    continue
                destino = lote_dir / hijo.name
                shutil.move(str(hijo), str(destino))
                hechos.append((hijo, destino))
            mapping_total.update(_mapping_documental(mov))
    except Exception as exc:
        for src, dst in reversed(hechos):
            try:
                shutil.move(str(dst), str(src))
            except Exception:
                pass    # best-effort: seguimos revirtiendo el resto
        for lote_dir in lotes_creados:
            try:
                if lote_dir.is_dir() and not any(lote_dir.iterdir()):
                    lote_dir.rmdir()
            except Exception:
                pass
        raise RuntimeError(f"Migración abortada y revertida: {exc}") from exc

    # --- Fase 2: borrado de duplicados + manifiestos + remaps + evento ----
    # (solo se ejecuta si la fase 1 completó entera)
    for hijo in duplicados_a_borrar:
        hijo.unlink()
    for mov in plan:
        lote_dir = base / mov.lote
        intake_lotes.escribir_manifiesto(
            lote_dir, fuente=mov.fuente, fecha_intake=mov.lote[:10],
            origen="migracion_layout",
            items=intake_lotes.items_desde_disco(lote_dir),
            fecha_intake_estimada=True)

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
        _yaml_atomico(cat_path, entries)

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
    except Exception as exc:
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=1)
    if not plan:
        typer.echo("Nada que migrar: sin cajones de entrega con contenido.")
        return
    for mov in plan:
        n_docs = len(_mapping_documental(mov))
        typer.echo(f"{'[dry-run] ' if dry_run else ''}{mov.cajon} → {mov.lote} "
                   f"({n_docs} ficheros)")


if __name__ == "__main__":
    app()
