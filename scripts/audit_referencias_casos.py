"""Auditoría preventiva: detecta casos con referencia local desalineada del CRM.

Origen (2026-05-11): incidencia BaRR3 — el caso local
``BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU`` tenía registrado en
``_caso.md`` el expediente CRM ID 648 cuando el expediente real era 649.
ID 648 era un expediente de prueba (HAR ``judicial_648.har``, 2026-04-26).
Para detectar otros casos con el mismo problema antes de procesarlos,
recorremos todos los ``_caso.md`` del repositorio, leemos los expedientes
vinculados, y comparamos su ``referencia_cliente`` en el CRM contra el
``case_id`` local (o ``meta.referencia_crm`` si está más alineado con la
referencia esperada).

NO modifica nada. Solo lectura.

Uso:
    python -m scripts.audit_referencias_casos
    python -m scripts.audit_referencias_casos --case BaRR3 - ...   # un caso

Salida:
    Una tabla en consola + un fichero JSON con el detalle por caso/expediente
    en ``data/probes/audit_referencias_<timestamp>.json`` para análisis
    posterior.

Códigos de salida:
    0 → todos los casos OK o solo "crm_unreachable" (revisar credenciales).
    1 → al menos un caso con mismatch detectado.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import typer  # noqa: E402

# Importar core.config primero para que dotenv cargue .env
from core.config import settings  # noqa: E402
from core.case_manager import get_case_status  # noqa: E402
from core.sudespacho_relations import verify_expediente_referencia  # noqa: E402
from core.utils import read_md  # noqa: E402

app = typer.Typer(add_completion=False, help="Auditoría de referencias caso ↔ CRM")


def _read_caso_meta(caso_dir: Path) -> dict:
    """Devuelve el dict ``meta`` del frontmatter de ``_caso.md`` (o {})."""
    index = caso_dir / "00_Input" / "_caso.md"
    if not index.exists():
        return {}
    try:
        fm, _ = read_md(index)
    except Exception:  # noqa: BLE001
        return {}
    meta = fm.get("meta") if isinstance(fm, dict) else None
    return meta if isinstance(meta, dict) else {}


def _resolve_expected_referencia(case_id: str, meta: dict) -> str:
    """Devuelve la referencia esperada para el expediente.

    Política: la UI envía el ``case_id`` como ``referencia_cliente`` en el
    payload de creación REST (verificado en ``streamlit_app.py``, sesión
    2026-05-11). Por tanto, la referencia esperada por defecto ES el
    ``case_id``. Si ``meta.referencia_crm`` está presente y difiere, se usa
    como fallback (compatibilidad con casos creados via CLI con
    ``--referencia`` explícita).
    """
    referencia_crm = (meta.get("referencia_crm") or "").strip()
    if referencia_crm and referencia_crm != case_id.strip():
        return referencia_crm
    return case_id


def _audit_case(case_dir: Path) -> dict:
    """Audita un caso. Devuelve dict con: case_id, expedientes [..], summary."""
    case_id = case_dir.name
    meta = _read_caso_meta(case_dir)
    expected_ref = _resolve_expected_referencia(case_id, meta)

    status = get_case_status(case_id)
    expedientes_local = status.get("expedientes", [])

    detalles: list[dict] = []
    for exp in expedientes_local:
        exp_id = str(exp.get("id", "")).strip()
        elem   = str(exp.get("element", "")).strip()
        if not exp_id or not elem:
            detalles.append({
                "expediente_id":  exp_id or None,
                "element":        elem or None,
                "status":         "entry_invalido",
                "detail":         "Entry sin id o element en _caso.md",
                "match":          None,
                "crm_referencia": None,
            })
            continue

        result = verify_expediente_referencia(
            exp_id, elem,
            expected_referencia=expected_ref,
        )
        if result["crm_unreachable"]:
            status_lbl = "crm_unreachable"
        elif result["match"]:
            status_lbl = "ok"
        else:
            status_lbl = "mismatch"

        detalles.append({
            "expediente_id":       exp_id,
            "element":             result["element"],
            "status":              status_lbl,
            "match":               result["match"],
            "crm_referencia":      result["crm_referencia"],
            "expected_referencia": expected_ref,
            "crm_unreachable":     result["crm_unreachable"],
            "found":               result["found"],
        })

    n_mismatch     = sum(1 for d in detalles if d["status"] == "mismatch")
    n_ok           = sum(1 for d in detalles if d["status"] == "ok")
    n_unreachable  = sum(1 for d in detalles if d["status"] == "crm_unreachable")
    n_invalid      = sum(1 for d in detalles if d["status"] == "entry_invalido")

    return {
        "case_id":              case_id,
        "expected_referencia":  expected_ref,
        "expedientes":          detalles,
        "summary": {
            "ok":              n_ok,
            "mismatch":        n_mismatch,
            "crm_unreachable": n_unreachable,
            "entry_invalido":  n_invalid,
            "total":           len(detalles),
        },
    }


def _list_case_dirs(casos_root: Path, only_case: str | None) -> list[Path]:
    if not casos_root.exists():
        return []
    if only_case:
        target = casos_root / only_case
        return [target] if target.exists() else []
    return sorted(
        p for p in casos_root.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )


def _print_summary(reports: list[dict]) -> None:
    typer.echo("")
    typer.echo("=" * 78)
    typer.echo("Auditoría referencias CRM ↔ caso local")
    typer.echo("=" * 78)
    n_cases_mismatch = 0
    for rep in reports:
        cs = rep["summary"]
        emoji = "✅" if cs["mismatch"] == 0 else "⚠️"
        if cs["mismatch"] > 0:
            n_cases_mismatch += 1
        typer.echo(
            f"{emoji} {rep['case_id']:<60s} "
            f"ok={cs['ok']:>2}  mismatch={cs['mismatch']:>2}  "
            f"unreachable={cs['crm_unreachable']:>2}  total={cs['total']:>2}"
        )
        for d in rep["expedientes"]:
            if d["status"] == "mismatch":
                typer.echo(
                    f"     ⚠️  exp #{d['expediente_id']} ({d['element']})\n"
                    f"          esperado:  {d['expected_referencia']!r}\n"
                    f"          en CRM:    {d['crm_referencia']!r}"
                )
            elif d["status"] == "entry_invalido":
                typer.echo(
                    f"     ⚠️  entry inválido en _caso.md: {d.get('detail')}"
                )
    typer.echo("")
    typer.echo(f"Casos con mismatch: {n_cases_mismatch} / {len(reports)}")
    typer.echo("=" * 78)


def _write_probe_json(reports: list[dict]) -> Path:
    probes_dir = settings.project_root / "data" / "probes"
    probes_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = probes_dir / f"audit_referencias_{ts}.json"
    out.write_text(
        json.dumps(reports, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out


@app.command()
def main(
    case: str = typer.Option(
        None, "--case",
        help="Auditar un único caso (por case_id exacto). Si se omite, audita todos.",
    ),
    fail_on_mismatch: bool = typer.Option(
        True, "--fail-on-mismatch/--no-fail-on-mismatch",
        help="Devolver código de salida 1 si hay algún mismatch (default: True).",
    ),
) -> None:
    """Audita todos los _caso.md del repositorio contra el CRM."""
    casos_root = settings.casos_root
    if not casos_root.exists():
        typer.echo(f"❌ casos_root no existe: {casos_root}")
        raise typer.Exit(code=2)

    case_dirs = _list_case_dirs(casos_root, case)
    if not case_dirs:
        typer.echo(f"❌ no se encontraron casos en {casos_root}"
                   + (f" (filtro: {case!r})" if case else ""))
        raise typer.Exit(code=2)

    reports = [_audit_case(d) for d in case_dirs]
    _print_summary(reports)

    out = _write_probe_json(reports)
    typer.echo(f"Detalle JSON: {out}")

    n_mismatch = sum(r["summary"]["mismatch"] for r in reports)
    if fail_on_mismatch and n_mismatch > 0:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
