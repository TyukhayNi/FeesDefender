"""CLI: sincronizar un expediente desde sudespacho.net al `00_Input/` local.

Uso:

    # Validar credencial API REST (x-api-key)
    python -m scripts.sync_sudespacho check

    # Validar cookie de sesión legacy (PHPSESSID)
    python -m scripts.sync_sudespacho check_legacy

    # Lectura del expediente como elemento (API REST, metadatos)
    python -m scripts.sync_sudespacho show --expediente 12345

    # Descargar todos los documentos del expediente al caso local
    # (vía frontal heredado — listado + descarga)
    python -m scripts.sync_sudespacho pull \\
        --case EV-2026-001 \\
        --expediente 12345

    # Descarga + pipeline completo
    python -m scripts.sync_sudespacho pull \\
        --case EV-2026-001 --expediente 12345 --run-pipeline

    # Forzar re-descarga aunque exista marcador
    python -m scripts.sync_sudespacho pull \\
        --case EV-2026-001 --expediente 12345 --force
"""

from __future__ import annotations

import json

import typer

from core import case_manager, pipeline
from core.judicial_intake import intake_demanda_contestacion
from core.sudespacho_relations import verify_expediente_referencia
from core.sync_sudespacho import (
    SudespachoClient,
    SudespachoError,
    pull_expediente,
)
from core.sync_sudespacho_legacy import (
    SudespachoLegacyClient,
    SudespachoLegacyError,
)

app = typer.Typer(add_completion=False, help="Sincronización con sudespacho.net")


@app.command()
def check() -> None:
    """Valida credenciales contra la API REST nueva (x-api-key)."""
    try:
        with SudespachoClient() as cli:
            ok = cli.healthcheck()
    except SudespachoError as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1)
    if ok:
        typer.echo("✅ Credenciales API REST OK")
    else:
        typer.echo("❌ La API REST rechaza la credencial o no responde")
        raise typer.Exit(code=1)


@app.command()
def check_legacy() -> None:
    """Valida cookie de sesión PHP del frontal heredado."""
    try:
        with SudespachoLegacyClient() as cli:
            ok = cli.healthcheck()
    except SudespachoLegacyError as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1)
    if ok:
        typer.echo("✅ Sesión legacy OK (CSRF token recuperado)")
    else:
        typer.echo("❌ Cookie PHPSESSID inválida o expirada")
        raise typer.Exit(code=1)


@app.command()
def show(
    expediente: str = typer.Option(..., "--expediente"),
    element: str = typer.Option(None, "--element"),
) -> None:
    """Muestra el expediente como elemento (metadatos)."""
    try:
        with SudespachoClient() as cli:
            exp = cli.get_expediente(expediente, element=element)
    except SudespachoError as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1)
    typer.echo(json.dumps(
        {
            "expediente_id": exp.expediente_id,
            "element": exp.element,
            "referencia": exp.referencia,
            "titulo": exp.titulo,
            "raw": exp.raw,
        },
        ensure_ascii=False, indent=2,
    ))


@app.command()
def pull(
    case: str = typer.Option(..., "--case", help="case_id local (ej. EV-2026-001)"),
    expediente: str = typer.Option(..., "--expediente", help="ID del expediente en sudespacho"),
    element: str = typer.Option(None, "--element",
                                help="Slug del tipo: expedientes_judiciales | extrajudiciales"),
    titulo: str = typer.Option(None, "--titulo"),
    referencia: str = typer.Option(None, "--referencia",
                                   help="Referencia CRM (ej. 'BaRR3 - Roser 39 - Art 20 LAU')"),
    cliente: str = typer.Option(None, "--cliente"),
    contraparte: str = typer.Option(None, "--contraparte"),
    force: bool = typer.Option(False, "--force/--no-force",
                               help="Re-descarga aunque exista marcador previo"),
    incremental: bool = typer.Option(False, "--incremental/--no-incremental",
                                     help="Solo descarga docs nuevos respecto al último pull"),
    run_pipeline: bool = typer.Option(False, "--run-pipeline/--no-run-pipeline"),
) -> None:
    """Descarga el expediente al caso local (subcarpeta sudespacho_{id}/).

    Modos:
      (default)     Skip si .pulled existe. Para pull inicial.
      --incremental Solo descarga docs nuevos. Para actualizaciones periódicas.
      --force       Re-descarga todo aunque .pulled exista.
    """
    case_manager.ensure_case(
        case,
        titulo=titulo or f"Expediente sudespacho {expediente}",
        referencia_crm=referencia,
        cliente=cliente,
        contraparte=contraparte,
    )

    elem = element or "expedientes_judiciales"

    # Registrar el expediente en el índice del caso (idempotente)
    case_manager.register_expediente(case, expediente, elem)

    # Validación preventiva — referencia local ↔ CRM (incidencia BaRR3,
    # sesión 2026-05-11). Pre-pull para que el usuario aborte antes de
    # descargar documentos contaminados. La validación nunca aborta —
    # mostramos warning visible y permitimos continuar.
    # Se usa --referencia si se ha pasado; si no, el case_id como referencia
    # esperada (es lo que la UI envía como `referencia_cliente` al crear).
    try:
        _ref_check = verify_expediente_referencia(
            expediente, elem,
            expected_referencia=referencia or case,
        )
    except Exception as _ve:  # noqa: BLE001 — defensivo
        typer.echo(f"ℹ️  Validación referencia CRM no ejecutada: {_ve}")
    else:
        if _ref_check["crm_unreachable"]:
            typer.echo(
                "ℹ️  Validación referencia CRM omitida — endpoint no accesible."
            )
        elif not _ref_check["match"]:
            _crm_ref = _ref_check.get("crm_referencia") or "(vacía)"
            _exp_ref = _ref_check.get("expected_referencia") or "(sin referencia local)"
            typer.echo(
                f"⚠️  Referencia desalineada CRM ↔ caso local.\n"
                f"   Expediente CRM ID {expediente}: referencia_cliente = {_crm_ref!r}\n"
                f"   Caso local {case}: esperado = {_exp_ref!r}\n"
                "   Si el ID está mal, aborta (Ctrl+C) y revisa _caso.md."
            )
        else:
            typer.echo("✓ Referencia CRM coincide con caso local.")

    try:
        result = pull_expediente(
            case, expediente,
            element=elem,
            force=force,
            incremental=incremental,
        )
    except (SudespachoError, SudespachoLegacyError) as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1)

    typer.echo(json.dumps({
        "case_id": result.case_id,
        "expediente_id": result.expediente_id,
        "documents_total": result.documents_total,
        "documents_downloaded": result.documents_downloaded,
        "bytes_downloaded": result.bytes_downloaded,
        "folders_processed": result.folders_processed,
        "errors": result.errors,
    }, ensure_ascii=False, indent=2))

    if run_pipeline:
        pr = pipeline.run(case, do_sync=False, do_demanda=True)
        for s in pr.steps:
            typer.echo(f"  {'✅' if s.ok else '❌'} {s.name}: {s.detail or s.artifact or ''}")


@app.command()
def intake_judicial(
    case: str = typer.Option(..., "--case", help="case_id local (ej. 'BaRR3 - Roser 39 (W-030LFT) - Art 20 LAU')"),
    expediente: str = typer.Option(..., "--expediente", help="ID del expediente JUDICIAL en sudespacho"),
    element: str = typer.Option("expedientes_judiciales", "--element"),
    referencia: str = typer.Option(None, "--referencia", help="Referencia CRM (validación preventiva)"),
    run_pipeline: bool = typer.Option(False, "--run-pipeline/--no-run-pipeline",
                                      help="Encadena el pipeline (anon → MD → frontier) tras el intake"),
) -> None:
    """Intake acotado: localiza, clasifica y deposita SOLO la demanda y la
    contestación del expediente judicial en el árbol del caso.

    A diferencia de `pull` (que baja todo el expediente), este comando descarga
    únicamente los dos documentos procesales clave, identificados por heurística
    sobre el nombre/etiqueta del CRM. Los roles ambiguos (0 o varios candidatos)
    se marcan para revisión del letrado y NO se descargan.
    """
    case_manager.ensure_case(
        case,
        titulo=f"Expediente judicial sudespacho {expediente}",
        referencia_crm=referencia,
    )
    case_manager.register_expediente(case, expediente, element)

    try:
        result = intake_demanda_contestacion(
            case, expediente, element=element,
        )
    except SudespachoError as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1)

    if result.blocked_legacy_v1:
        typer.echo("⛔ Caso con estructura v1 (sudespacho_*/) — intake bloqueado.")
        for e in result.errors:
            typer.echo(f"   {e}")
        raise typer.Exit(code=2)

    typer.echo(json.dumps({
        "case_id": result.case_id,
        "expediente_id": result.expediente_id,
        "demanda_doc_id": result.demanda_doc_id,
        "contestacion_doc_id": result.contestacion_doc_id,
        "pendientes_revision": result.pendientes,
        "documents_written": result.pull.documents_written if result.pull else 0,
        "documents_skipped_dedup": result.pull.documents_skipped_dedup if result.pull else 0,
        "errors": result.errors,
    }, ensure_ascii=False, indent=2))

    # Detalle legible de cada rol
    if result.classification:
        for rr in (result.classification.demanda, result.classification.contestacion):
            icon = "✅" if rr.status == "ok" else ("⚠️" if rr.status == "ambiguous" else "—")
            sel = rr.selected.filename if rr.selected else "(sin selección)"
            typer.echo(f"  {icon} {rr.role}: {rr.status} → {sel}")
            if rr.status != "ok" and rr.candidates:
                for c in rr.candidates:
                    typer.echo(f"       · candidato {c.doc_id}: {c.filename}")

    if result.pendientes:
        typer.echo(
            f"\n📋 {len(result.pendientes)} rol(es) [PENDIENTE revisión letrado]: "
            f"{', '.join(result.pendientes)}. "
            "Súbelos a mano con el expander «📂 Subir al árbol CRM» si procede."
        )

    if run_pipeline and result.pull and result.pull.documents_written:
        pr = pipeline.run(case, do_sync=False, do_demanda=True)
        for s in pr.steps:
            typer.echo(f"  {'✅' if s.ok else '❌'} {s.name}: {s.detail or s.artifact or ''}")


@app.command()
def sync_all(
    incremental: bool = typer.Option(True, "--incremental/--no-incremental",
                                     help="Solo descarga docs nuevos (default: True)"),
    run_pipeline: bool = typer.Option(False, "--run-pipeline/--no-run-pipeline"),
) -> None:
    """Sincroniza TODOS los casos activos con sus expedientes registrados.

    Recorre data/CASOS/, lee los expedientes vinculados en _caso.md,
    y ejecuta pull incremental para cada uno. Diseñado para tarea programada.
    """
    from core.config import caso_path, settings
    import yaml as _yaml

    casos = case_manager.list_cases()
    if not casos:
        typer.echo("No hay casos en data/CASOS/")
        return

    total_new = 0
    errors_global: list[str] = []

    for case_id in casos:
        index = caso_path(case_id) / "00_Input" / "_caso.md"
        if not index.exists():
            continue

        text = index.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        _, fm_raw, _ = text.split("---", 2)
        fm = _yaml.safe_load(fm_raw) or {}
        expedientes = fm.get("sudespacho_expedientes") or []

        if not expedientes:
            continue

        typer.echo(f"\n📂 {case_id}")
        for exp in expedientes:
            exp_id = str(exp.get("id", ""))
            elem = exp.get("element", "expedientes_judiciales")
            if not exp_id:
                continue

            try:
                result = pull_expediente(
                    case_id, exp_id,
                    element=elem,
                    incremental=incremental,
                    force=False,
                )
            except (SudespachoError, SudespachoLegacyError) as exc:
                msg = f"  ❌ {exp_id}: {exc}"
                typer.echo(msg)
                errors_global.append(f"{case_id}/{exp_id}: {exc}")
                continue

            new = result.documents_downloaded
            total_new += new
            status = f"+{new} docs" if new else "sin cambios"
            icon = "🆕" if new else "✓"
            typer.echo(f"  {icon} {elem} {exp_id}: {status}")
            if result.errors:
                for e in result.errors:
                    typer.echo(f"     ⚠️  {e}")

            if run_pipeline and new:
                pr = pipeline.run(case_id, do_sync=False, do_demanda=False)
                for s in pr.steps:
                    typer.echo(f"     {'✅' if s.ok else '❌'} {s.name}")

    typer.echo(f"\n✅ Sync completado — {total_new} doc(s) nuevos en {len(casos)} caso(s)")
    if errors_global:
        typer.echo(f"⚠️  {len(errors_global)} error(s):")
        for e in errors_global:
            typer.echo(f"   {e}")


if __name__ == "__main__":
    app()
