"""Migración puntual de ``00_Input/05_CRM/`` al esquema de buckets planos (D12-D13).

Reorg `[SIGUIENTE-REORG-05CRM]` (PLAN.md, 2026-06-10). Aplana el árbol profundo
del CRM heredado a los buckets planos de un nivel (`01_Demanda`,
`02_Contestacion`, …, `99_Otros`) **in situ**, sin re-bajar del CRM y sin
re-OCRizar:

- Mueve cada fichero de su rama profunda al bucket que le asigna
  ``case_manager._bucket_for`` (D6).
- Re-llavea ``00_Input/_intake_hashes.json`` (paths rel viejo→nuevo, primary y
  aliases) — preserva el dedup cross-source M9.
- Re-llavea ``01_Procesado/raw_text/_extract_state.json`` por ``rel_path``. Los
  ``.txt`` NO se mueven (slug = stem, invariante al cambio de carpeta), así que
  ``extractor.extract_all`` hace skip y **no re-OCRiza** (cache OCR preservada).
- Detecta colisiones de stem entre ramas que confluyen al mismo bucket (D13):
  si dos ficheros caen al mismo ``bucket/nombre``, sufija el segundo (``__1``)
  y renombra también su ``.txt`` (re-llaveando el state) para no romper la
  cache OCR.
- Re-ejecuta ``inventory.scan`` y refresca ``by_carpeta`` en ``_caso.md``.

La carpeta de fallback (``99_Sin categoria/<exp>``) NO se re-rutea sola: se
pasa explícitamente con ``--fallback`` ``<exp>=<bucket>`` el bucket verificado
(p. ej. para el 444: todos los huérfanos son id_carpeta 380 = Preliminares →
``444=05_Diligencias_Preliminares``). Sin override, esos ficheros se conservan
en su sitio y se reportan.

Idempotente: un fichero ya en un bucket conocido es no-op; re-ejecutar no mueve
nada. Dry-run por defecto.

Uso::

    # Reporte (no mueve nada)
    python -m scripts.migrate_05crm_buckets plan "BaRS6 - Valldaura 88 - (W-02NV4W) - Vuelta" \\
        --fallback 444=05_Diligencias_Preliminares

    # Aplicar (mueve + re-llavea + inventory + by_carpeta)
    python -m scripts.migrate_05crm_buckets apply "BaRS6 - Valldaura 88 - (W-02NV4W) - Vuelta" \\
        --fallback 444=05_Diligencias_Preliminares
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import typer

app = typer.Typer(help="Aplana 00_Input/05_CRM/ a buckets planos (reorg D12-D13).")


# Buckets terminales: un fichero ya bajo uno de estos es no-op (idempotencia).
KNOWN_BUCKETS: frozenset[str] = frozenset({
    "01_Demanda",
    "02_Contestacion",
    "03_Monitorio_Demanda",
    "04_Monitorio_Oposicion",
    "05_Diligencias_Preliminares",
    "99_Otros",
})

_CONTROL_FILES: frozenset[str] = frozenset({".pulled", "_inventory.json", ".synced"})
_STATE_REL = "01_Procesado/raw_text/_extract_state.json"
_MANIFEST_REL = "00_Input/_intake_hashes.json"


@dataclass
class Move:
    old_input_rel: str          # rel a 00_Input, posix (p. ej. "05_CRM/Civil/.../foo.pdf")
    new_input_rel: str          # rel a 00_Input, posix (p. ej. "05_CRM/01_Demanda/foo.pdf")
    old_crm_rel: str            # rel a 05_CRM (p. ej. "Civil/.../foo.pdf")
    new_crm_rel: str            # rel a 05_CRM (p. ej. "01_Demanda/foo.pdf")
    old_txt_slug: str           # slug del .txt de origen (sin .txt)
    new_txt_slug: str           # slug del .txt de destino (igual salvo colisión)
    suffixed: bool = False      # True si se renombró por colisión de stem


@dataclass
class MovePlan:
    case_id: str
    moves: list[Move] = field(default_factory=list)
    noops: list[str] = field(default_factory=list)        # ya en bucket / sin cambio
    keeps: list[str] = field(default_factory=list)         # fallback sin override
    collisions: list[tuple[str, str]] = field(default_factory=list)  # (target, resolved)


# ---------------------------------------------------------------------------
# Lógica pura (importable por los tests)
# ---------------------------------------------------------------------------

def target_bucket_for_rama(rama: str, fallback_buckets: dict[str, str]) -> str | None:
    """Bucket destino para una rama (path de carpeta relativo a 05_CRM).

    Devuelve ``None`` cuando el fichero debe quedarse donde está (fallback sin
    override). Si la rama ya ES un bucket conocido, lo devuelve tal cual
    (no-op idempotente).
    """
    from core.case_manager import _bucket_for

    parts = [p for p in rama.split("/") if p]
    if not parts:
        return "99_Otros"  # fichero suelto en la raíz de 05_CRM
    if parts[0] in KNOWN_BUCKETS:
        return parts[0]
    if parts[0] == "99_Sin categoria":
        exp = parts[1] if len(parts) >= 2 else None
        return fallback_buckets.get(exp) if exp is not None else None
    return _bucket_for(rama)


def build_move_plan(case_id: str, fallback_buckets: dict[str, str] | None = None) -> MovePlan:
    """Construye el plan de movimientos (sin tocar disco) — D13 pre-migración.

    Recorre los ficheros físicos bajo ``00_Input/05_CRM/`` y, para cada uno,
    calcula su bucket destino. Detecta colisiones de stem (dos orígenes → mismo
    ``bucket/nombre``) y las resuelve con sufijo ``__N``, renombrando también el
    ``.txt`` asociado (re-llave del state) para preservar la cache OCR.
    """
    from core.config import caso_path
    from core.utils import slugify

    fallback_buckets = fallback_buckets or {}
    case_dir = caso_path(case_id)
    crm_root = case_dir / "00_Input" / "05_CRM"
    plan = MovePlan(case_id=case_id)
    if not crm_root.exists():
        return plan

    # Nombres ya ocupados por bucket (ficheros que NO se mueven), para que el
    # resolutor de colisiones no pise un fichero existente.
    occupied: dict[str, set[str]] = {}

    files = sorted(
        p for p in crm_root.rglob("*")
        if p.is_file() and p.name not in _CONTROL_FILES
    )

    # Primera pasada: clasificar en move / noop / keep.
    pending: list[tuple[Path, str, str]] = []  # (path, rama, bucket)
    for p in files:
        crm_rel = p.relative_to(crm_root).as_posix()
        rama = p.parent.relative_to(crm_root).as_posix()
        rama = "" if rama == "." else rama
        bucket = target_bucket_for_rama(rama, fallback_buckets)
        if bucket is None:
            plan.keeps.append(crm_rel)
            continue
        if rama == bucket:  # ya en su bucket → no-op idempotente
            occupied.setdefault(bucket, set()).add(p.name)
            plan.noops.append(crm_rel)
            continue
        pending.append((p, rama, bucket))

    # Segunda pasada: asignar nombre destino resolviendo colisiones de stem.
    for p, _rama, bucket in pending:
        crm_rel = p.relative_to(crm_root).as_posix()
        stem, ext = Path(p.name).stem, Path(p.name).suffix
        taken = occupied.setdefault(bucket, set())
        candidate = p.name
        suffixed = False
        n = 1
        while candidate in taken:
            candidate = f"{stem}__{n}{ext}"
            suffixed = True
            n += 1
        taken.add(candidate)
        new_crm_rel = f"{bucket}/{candidate}"
        new_stem = Path(candidate).stem
        if suffixed:
            plan.collisions.append((f"{bucket}/{p.name}", new_crm_rel))
        plan.moves.append(Move(
            old_input_rel=f"05_CRM/{crm_rel}",
            new_input_rel=f"05_CRM/{new_crm_rel}",
            old_crm_rel=crm_rel,
            new_crm_rel=new_crm_rel,
            old_txt_slug=slugify(stem),
            new_txt_slug=slugify(new_stem),
            suffixed=suffixed,
        ))
    return plan


def _remap_alias_only_paths(
    manifest_data: dict,
    moved: dict[str, str],
    fallback_buckets: dict[str, str],
) -> int:
    """Re-llavea paths de 05_CRM en el manifest que NO tienen fichero físico.

    ``moved`` mapea old_input_rel→new_input_rel de los ficheros físicos (con su
    sufijo ya resuelto). Las entradas alias-only (dedup-skipped: el SHA vive en
    otra fuente, no hay fichero en 05_CRM) se remapean por string, sin sufijo.
    """
    changed = 0

    def _remap(path: str) -> str:
        if path in moved:
            return moved[path]
        if not path.startswith("05_CRM/"):
            return path
        crm_rel = path[len("05_CRM/"):]
        rama = crm_rel.rsplit("/", 1)[0] if "/" in crm_rel else ""
        name = crm_rel.rsplit("/", 1)[-1]
        bucket = target_bucket_for_rama(rama, fallback_buckets)
        if bucket is None or rama == bucket:
            return path
        return f"05_CRM/{bucket}/{name}"

    for entry in manifest_data.values():
        primary = entry.get("primary_path", "")
        new_primary = _remap(primary)
        if new_primary != primary:
            entry["primary_path"] = new_primary
            changed += 1
        for alias in entry.get("aliases") or []:
            if not isinstance(alias, dict):
                continue
            ap = alias.get("path", "")
            new_ap = _remap(ap)
            if new_ap != ap:
                alias["path"] = new_ap
                changed += 1
    return changed


def _refresh_by_carpeta(fm: dict, fallback_buckets: dict[str, str]) -> None:
    """Remapea ``by_carpeta`` de cada expediente (claves rama → bucket), sumando.

    Idempotente: una clave que ya es un bucket se conserva.
    """
    for exp in fm.get("sudespacho_expedientes") or []:
        if not isinstance(exp, dict):
            continue
        bc = exp.get("by_carpeta")
        if not isinstance(bc, dict):
            continue
        new_bc: dict[str, int] = {}
        for rama, count in bc.items():
            bucket = target_bucket_for_rama(rama, fallback_buckets)
            if bucket is None:
                bucket = rama  # fallback sin override: se conserva la clave
            new_bc[bucket] = new_bc.get(bucket, 0) + int(count)
        exp["by_carpeta"] = new_bc


def apply_move_plan(
    case_id: str,
    plan: MovePlan,
    fallback_buckets: dict[str, str] | None = None,
) -> dict:
    """Ejecuta el plan: mueve ficheros, re-llavea manifest + state, inventory, by_carpeta.

    Devuelve un dict-resumen. Escribe un journal reversible
    ``00_Input/_migration_05crm_<ts>.json`` y back-ups ``.bak`` de manifest,
    state y _caso.md antes de mutar.
    """
    from core import inventory
    from core.config import caso_path
    from core.utils import read_md, write_md

    fallback_buckets = fallback_buckets or {}
    case_dir = caso_path(case_id)
    input_dir = case_dir / "00_Input"
    crm_root = input_dir / "05_CRM"

    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    summary = {"moved": 0, "will_reocr": 0, "manifest_changed": 0, "errors": []}

    # --- back-ups defensivos -------------------------------------------------
    for rel in (_MANIFEST_REL, _STATE_REL, "00_Input/_caso.md"):
        src = case_dir / rel
        if src.exists():
            shutil.copy2(src, src.with_suffix(src.suffix + f".bak_{ts}"))

    # --- 1. mover ficheros físicos ------------------------------------------
    moved_map: dict[str, str] = {}
    journal: list[dict] = []
    for mv in plan.moves:
        src = crm_root / mv.old_crm_rel
        dst = crm_root / mv.new_crm_rel
        if not src.exists():
            summary["errors"].append(f"origen no existe: {mv.old_crm_rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            summary["errors"].append(f"destino ya existe (colisión no resuelta): {mv.new_crm_rel}")
            continue
        shutil.move(str(src), str(dst))
        moved_map[mv.old_input_rel] = mv.new_input_rel
        journal.append({"from": mv.old_input_rel, "to": mv.new_input_rel, "suffixed": mv.suffixed})
        summary["moved"] += 1
        # Colisión de stem (D13): el fichero sufijado cambia de slug, así que su
        # .txt (compartido con el homónimo en el pipeline) ya no le corresponde.
        # NO se renombra el .txt (sería robárselo al no-sufijado): el sufijado
        # re-OCRiza SOLO él en la próxima corrida (out.exists()==False). El resto
        # conserva su cache. Lo contabilizamos para el reporte.
        if mv.suffixed:
            summary["will_reocr"] += 1

    # --- 2. limpiar carpetas vacías del árbol profundo ----------------------
    _prune_empty_dirs(crm_root)

    # --- 3. re-llavear manifest (físicos + alias-only) -----------------------
    manifest_path = case_dir / _MANIFEST_REL
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        summary["manifest_changed"] = _remap_alias_only_paths(data, moved_map, fallback_buckets)
        manifest_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    # --- 4. re-llavear extract_state por rel_path ---------------------------
    # Formato: {"extractor_version": N, "files": {<rel>: {...}}}. Se re-llavea
    # SOLO el sub-dict `files`, preservando el wrapper de versión (si no, el
    # cache se invalida y se re-OCRiza todo). El slug del .txt = stem, así que
    # un fichero no sufijado conserva su .txt y hace skip; el sufijado (slug
    # nuevo, sin .txt) re-OCRiza solo él.
    state_path = case_dir / _STATE_REL
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        files = state.get("files", {}) if isinstance(state, dict) else {}
        state["files"] = {moved_map.get(k, k): v for k, v in files.items()}
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # --- 5. inventory.scan ---------------------------------------------------
    inventory.scan(case_id)

    # --- 6. refrescar by_carpeta en _caso.md --------------------------------
    caso_md = input_dir / "_caso.md"
    if caso_md.exists():
        fm, body = read_md(caso_md)
        _refresh_by_carpeta(fm, fallback_buckets)
        write_md(caso_md, fm, body)

    # --- journal reversible --------------------------------------------------
    (input_dir / f"_migration_05crm_{ts}.json").write_text(
        json.dumps({"case_id": case_id, "moves": journal}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def _prune_empty_dirs(root: Path) -> None:
    """Borra recursivamente directorios vacíos bajo ``root`` (no borra ``root``)."""
    for d in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        try:
            if not any(d.iterdir()):
                d.rmdir()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_fallback(items: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for it in items or []:
        if "=" not in it:
            raise typer.BadParameter(f"--fallback debe ser <exp>=<bucket>: {it!r}")
        exp, bucket = it.split("=", 1)
        out[exp.strip()] = bucket.strip()
    return out


def _print_plan(plan: MovePlan) -> None:
    typer.echo(f"Caso: {plan.case_id}")
    typer.echo(f"  Movimientos: {len(plan.moves)}")
    for mv in plan.moves:
        flag = "  ⚠ colisión→sufijo" if mv.suffixed else ""
        typer.echo(f"    {mv.old_crm_rel}  →  {mv.new_crm_rel}{flag}")
    if plan.collisions:
        typer.echo(f"  Colisiones de stem resueltas: {len(plan.collisions)}")
    if plan.noops:
        typer.echo(f"  Ya en bucket (no-op): {len(plan.noops)}")
    if plan.keeps:
        typer.echo(f"  Fallback sin override (se conservan): {len(plan.keeps)}")
        for k in plan.keeps:
            typer.echo(f"    (keep) {k}")


@app.command()
def plan(
    case_id: str = typer.Argument(..., help="case_id completo"),
    fallback: list[str] = typer.Option(
        None, "--fallback", help="<exp>=<bucket> para huérfanos de 99_Sin categoria",
    ),
) -> None:
    """Dry-run: muestra el plan de migración sin mover nada."""
    fb = _parse_fallback(fallback)
    p = build_move_plan(case_id, fb)
    _print_plan(p)
    typer.echo("\n(dry-run — nada movido. Usa `apply` para ejecutar.)")


@app.command()
def apply(
    case_id: str = typer.Argument(..., help="case_id completo"),
    fallback: list[str] = typer.Option(
        None, "--fallback", help="<exp>=<bucket> para huérfanos de 99_Sin categoria",
    ),
) -> None:
    """Ejecuta la migración (mueve + re-llavea + inventory + by_carpeta)."""
    fb = _parse_fallback(fallback)
    p = build_move_plan(case_id, fb)
    _print_plan(p)
    if not p.moves:
        typer.echo("\nNada que mover (ya migrado o sin ficheros). Saliendo.")
        raise typer.Exit()
    summary = apply_move_plan(case_id, p, fb)
    typer.echo("\nResultado:")
    for k, v in summary.items():
        typer.echo(f"  {k}: {v}")


if __name__ == "__main__":
    app()
