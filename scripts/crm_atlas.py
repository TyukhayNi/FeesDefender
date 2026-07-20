"""CLI: atlas del CRM sudespacho — descubrimiento exhaustivo, re-ejecutable.

Diseño: `docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md`.

Uso:

    # Fase A (pública, sin credenciales): inventario de endpoints del OpenAPI
    python -m scripts.crm_atlas discover --phase a

    # sin sello de tiempo (diff limpio en corridas sin cambios sustantivos)
    python -m scripts.crm_atlas discover --phase a --no-stamp-time

    # sincronizar copia al repo hermano El Contable si está al lado
    python -m scripts.crm_atlas discover --phase a --also-elcontable
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer

from core.crm_atlas import (
    PUBLIC_BASE_URL,
    build_atlas_phase_a,
    fetch_oas3,
    render_markdown,
)
from core.utils import now_iso

app = typer.Typer(add_completion=False, help="Atlas del CRM sudespacho (descubrimiento).")


@app.callback()
def _main() -> None:
    """Descubre y persiste la superficie del CRM sudespacho como atlas re-ejecutable."""

# Rutas por defecto (relativas a la raíz del repo)
DEFAULT_ATLAS_JSON = Path("docs/crm_atlas/atlas.json")
DEFAULT_ATLAS_MD = Path("docs/CRM_SUDESPACHO_ATLAS.md")
ELCONTABLE_ATLAS_DIR = Path("../ElContable/docs/crm_atlas")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


@app.command()
def discover(
    phase: str = typer.Option("a", help="Fase: 'a' (pública) | 'b' | 'all'."),
    base_url: str = typer.Option(PUBLIC_BASE_URL, help="Host de la API (público para Fase A)."),
    tenant: str = typer.Option("tnm", help="Etiqueta de tenant para el atlas."),
    atlas_json: Path = typer.Option(DEFAULT_ATLAS_JSON, help="Ruta del atlas.json."),
    atlas_md: Path = typer.Option(DEFAULT_ATLAS_MD, help="Ruta del render Markdown."),
    dev_links: bool = typer.Option(True, help="Enlazar cada operación al portal de docs."),
    stamp_time: bool = typer.Option(True, help="Sellar generated_at (usar --no-stamp-time para diff limpio)."),
    also_elcontable: bool = typer.Option(False, help="Copiar el atlas a ../ElContable/docs/crm_atlas."),
) -> None:
    """Descubre la superficie del CRM y persiste atlas.json + Markdown."""
    if phase not in {"a", "b", "all"}:
        typer.echo("❌ --phase debe ser 'a', 'b' o 'all'.")
        raise typer.Exit(code=2)
    if phase in {"b", "all"}:
        typer.echo("⏳ Fase B (esquema por elemento, x-api-key) aún no implementada. "
                   "Esta entrega cubre la Fase A (pública).")
        if phase == "b":
            raise typer.Exit(code=1)

    typer.echo(f"→ Fase A: descargando OpenAPI de {base_url}{'' if base_url.endswith('/') else ''}/api/docs.json …")
    spec = fetch_oas3(base_url)
    atlas = build_atlas_phase_a(
        spec,
        tenant=tenant,
        base_url=base_url,
        generated_at=now_iso() if stamp_time else None,
        dev_links=dev_links,
    )
    summ = atlas["summary"]

    _write_text(atlas_json, json.dumps(atlas, ensure_ascii=False, indent=2) + "\n")
    _write_text(atlas_md, render_markdown(atlas))

    typer.echo(
        f"✅ {summ['total_operations']} operaciones · {summ['total_paths']} paths · "
        f"{len(summ['by_tag'])} módulos"
    )
    typer.echo("   " + " · ".join(f"{m} {n}" for m, n in summ["by_method"].items()))
    typer.echo(f"   → {atlas_json}")
    typer.echo(f"   → {atlas_md}")

    if also_elcontable:
        if ELCONTABLE_ATLAS_DIR.parent.parent.exists():
            dst_json = ELCONTABLE_ATLAS_DIR / atlas_json.name
            dst_md = ELCONTABLE_ATLAS_DIR / atlas_md.name
            _write_text(dst_json, json.dumps(atlas, ensure_ascii=False, indent=2) + "\n")
            _write_text(dst_md, render_markdown(atlas))
            typer.echo(f"   → copiado a El Contable: {dst_json} (commit aparte en ese repo)")
        else:
            typer.echo("   ⚠️  ../ElContable no encontrado al lado; se omite la copia.")


if __name__ == "__main__":
    app()
