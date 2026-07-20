"""CLI: atlas del CRM sudespacho — descubrimiento exhaustivo, re-ejecutable.

Diseño: `docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md`.

Uso:

    # Fase A (pública, sin credenciales): inventario de endpoints del OpenAPI
    python -m scripts.crm_atlas discover --phase a

    # Fase B (x-api-key en el entorno): esquema por elemento
    python -m scripts.crm_atlas discover --phase all

    # reintentar solo los elementos degradados de una corrida previa
    python -m scripts.crm_atlas discover --phase all --resume
"""

from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path

import typer

from core.crm_atlas import (
    PUBLIC_BASE_URL,
    atlas_client,
    auth_healthcheck,
    build_atlas_phase_a,
    build_atlas_phase_b,
    discover_element,
    fetch_elements,
    fetch_oas3,
    is_resolved,
    load_previous_atlas,
    quarantine_person_enums,
    render_digest,
    render_markdown,
    scan_atlas_for_pii,
)
from core.utils import now_iso_utc

app = typer.Typer(add_completion=False, help="Atlas del CRM sudespacho (descubrimiento).")


@app.callback()
def _main() -> None:
    """Descubre y persiste la superficie del CRM sudespacho como atlas re-ejecutable."""


# Rutas por defecto (relativas a la raíz del repo)
DEFAULT_ATLAS_JSON = Path("docs/crm_atlas/atlas.json")
DEFAULT_ATLAS_MD = Path("docs/CRM_SUDESPACHO_ATLAS.md")
DEFAULT_DIGEST = Path("docs/crm_atlas/atlas.digest.md")

CONCURRENCY = 4


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


@app.command()
def discover(
    phase: str = typer.Option("a", help="Fase: 'a' (pública) | 'b' | 'all'."),
    base_url: str = typer.Option(PUBLIC_BASE_URL, help="Host de la API."),
    tenant: str = typer.Option("tnm", help="Etiqueta de tenant."),
    atlas_json: Path = typer.Option(DEFAULT_ATLAS_JSON, help="Ruta del atlas.json (gitignorado)."),
    atlas_md: Path = typer.Option(DEFAULT_ATLAS_MD, help="Ruta del render Markdown."),
    digest_md: Path = typer.Option(DEFAULT_DIGEST, help="Ruta del digest de deriva."),
    dev_links: bool = typer.Option(True, help="Enlazar cada operación al portal de docs."),
    stamp_time: bool = typer.Option(False, help="Sellar generated_at (UTC). Default OFF para diff limpio."),
    resume: bool = typer.Option(False, help="Fase B: reintentar solo los elementos degradados del atlas previo."),
) -> None:
    """Descubre la superficie del CRM y persiste .md + digest (atlas.json local, gitignorado)."""
    if phase not in {"a", "b", "all"}:
        typer.echo("❌ --phase debe ser 'a', 'b' o 'all'.")
        raise typer.Exit(code=2)

    # --- Fase A: inventario de endpoints (público) ---
    typer.echo(f"→ Fase A: OpenAPI de {base_url}/api/docs.json …")
    spec = fetch_oas3(base_url)
    atlas = build_atlas_phase_a(
        spec, tenant=tenant, base_url=base_url,
        generated_at=now_iso_utc() if stamp_time else None, dev_links=dev_links,
    )
    summ = atlas["summary"]
    typer.echo(f"   {summ['total_operations']} ops · {summ['total_path_keys']} paths · "
               f"{len(summ['by_tag'])} módulos")

    # --- Fase B: esquema por elemento (x-api-key) ---
    if phase in {"b", "all"}:
        typer.echo("→ Fase B: autenticando (x-api-key) …")
        with atlas_client(base_url) as client:
            auth_healthcheck(client)  # fail-fast: 401/403 global aborta aquí
            slugs = fetch_elements(client)
            typer.echo(f"   {len(slugs)} elementos en el catálogo.")
            resolved: dict = {}
            if resume:
                prev = load_previous_atlas(atlas_json)
                if prev:
                    resolved = {e["slug"]: e for e in prev.get("elements", []) if is_resolved(e)}
                    typer.echo(f"   --resume: {len(resolved)} resueltos se conservan; reintento el resto.")
            todo = [s for s in slugs if s not in resolved]

            def _safe_discover(slug: str) -> dict:
                try:
                    return discover_element(client, slug)
                except Exception:  # noqa: BLE001 — un elemento no tumba la corrida
                    return {"slug": slug, "fields": [], "relations": None, "enums": {},
                            "field_types_no_enumerados": {},
                            "probes": {"fields": "failed", "relations": "failed", "enums": "failed"}}

            results = list(resolved.values())
            with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
                results.extend(ex.map(_safe_discover, todo))
        atlas = build_atlas_phase_b(atlas, results, tenant=tenant)
        pb = atlas["meta"]["phase_b"]
        typer.echo(f"   {pb['elements_ok']}/{pb['elements_total']} resueltos · "
                   f"{pb['elements_degraded']} degradados")

        # --- GATE anti-PII (antes de CUALQUIER escritura) ---
        moved = quarantine_person_enums(atlas)
        if moved:
            typer.echo(f"   ⚠️ {moved} enums Select con pinta de persona → cuarentena (valores no volcados).")
        email_hits = [h for h in scan_atlas_for_pii(atlas) if h.endswith(": email")]
        if email_hits:
            typer.echo("❌ Gate PII: EMAIL detectado en el atlas — NO se escribe nada:")
            for h in email_hits[:10]:
                typer.echo(f"     · {h}")
            raise typer.Exit(code=1)
        if pb.get("circuit_broken"):
            typer.echo("❌ Circuit-breaker: >50% de elementos degradados (fallo probablemente "
                       "global) — NO se escribe.")
            raise typer.Exit(code=1)

    # --- Escritura (único camino, tras el gate) ---
    _write_text(atlas_json, json.dumps(atlas, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    _write_text(atlas_md, render_markdown(atlas))
    _write_text(digest_md, render_digest(atlas))
    typer.echo(f"   → {atlas_json}")
    typer.echo(f"   → {atlas_md}")
    typer.echo(f"   → {digest_md}")


if __name__ == "__main__":
    app()
