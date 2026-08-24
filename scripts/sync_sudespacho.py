"""CLI: sincronizar un expediente desde sudespacho.net al `00_Input/` local.

Uso:

    # Validar credencial API REST (x-api-key)
    python -m scripts.sync_sudespacho check

    # Validar cookie de sesión legacy (PHPSESSID)
    python -m scripts.sync_sudespacho check_legacy

    # Lectura del expediente como elemento (API REST, metadatos)
    python -m scripts.sync_sudespacho show --expediente 12345

    # Descargar todos los documentos del expediente al caso local
    # (API REST; depositados en 00_Input/05_CRM/<rama>/)
    python -m scripts.sync_sudespacho pull \\
        --case EV-2026-001 \\
        --expediente 12345

Procesar lo descargado NO es parte de este CLI: el motor documental es la sala de
máquina (`python -m scripts.sala_maquina apply "<case_id>"`). Hasta el 2026-08-04 estos
comandos traían un flag `--run-pipeline` que llamaba a `core.pipeline.run` —el motor
jubilado: Docling con tope de 30 páginas y salida a `raw_text/` + `MD/` legacy— mientras
su ayuda prometía «OCR → MD». Se retiró: `MEJORAS #113`.

El pull es **idempotente por hash** (manifiesto M9), así que no hay `--force` ni
`--incremental`: volver a llamarlo salta lo que ya está.
"""

from __future__ import annotations

import json

import typer

from core import case_manager
from core.judicial_intake import intake_demanda_contestacion
from core.sudespacho_relations import verify_expediente_referencia
from core.sync_sudespacho import (
    SudespachoClient,
    SudespachoError,
    pull_expediente_v2,
)
from core.sync_sudespacho_legacy import (
    SudespachoLegacyClient,
    SudespachoLegacyError,
)

app = typer.Typer(add_completion=False, help="Sincronización con sudespacho.net")


def _siguiente_paso(case: str, *, con_anonimizacion: bool = False) -> None:
    """Señaliza el motor documental. Este CLI descarga; no procesa.

    Retirar `--run-pipeline` sin decir con qué se sustituye convertiría una promesa
    falsa en un silencio, que era el otro defecto del mismo fichero (`MEJORAS #113`).
    """
    typer.echo("\n▶ Siguiente paso — este comando descarga, NO procesa:")
    typer.echo(f'    python -m scripts.sala_maquina apply "{case}"')
    if con_anonimizacion:
        typer.echo("  Y si el caso necesita la capa tapada para el LLM externo:")
        typer.echo(f'    python -m scripts.anonimizar_caso "{case}"')


def _abortar_si_legacy_v1(result) -> None:
    """Un caso con `00_Input/sudespacho_*/` está congelado y el pull v2 no escribe nada.

    Hasta el 2026-08-04 esto no se veía: el CLI bajaba por el pull v1, que escribía en
    ese mismo layout y así mantenía el caso fuera del intake judicial, de las fuentes
    que declara la sala de lectura y del guard de escritura del caso prestado.
    """
    if not result.blocked_legacy_v1:
        return
    typer.echo("⛔ Caso con estructura v1 de intake — no se ha descargado nada.")
    for e in result.errors:
        typer.echo(f"   {e}")
    typer.echo(
        "   Migración manual (revísala antes de ejecutarla): borrar las carpetas "
        "`00_Input/sudespacho_*/` del caso y repetir este pull; los documentos "
        "volverán a bajar a `00_Input/05_CRM/<rama>/`."
    )
    raise typer.Exit(2)


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
) -> None:
    """Descarga el expediente al árbol del caso: `00_Input/05_CRM/<rama>/`.

    Idempotente por hash (manifiesto M9): re-llamarlo salta lo que ya está, así que no
    hay `--force` ni `--incremental`. Si el caso tiene estructura v1
    (`00_Input/sudespacho_*/`) el pull se bloquea y explica la migración.
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
        result = pull_expediente_v2(case, expediente, element=elem)
    except (SudespachoError, SudespachoLegacyError) as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1)

    _abortar_si_legacy_v1(result)

    typer.echo(json.dumps({
        "case_id": result.case_id,
        "expediente_id": result.expediente_id,
        "documents_total_crm": result.documents_total_crm,
        "documents_written": result.documents_written,
        "documents_skipped_dedup": result.documents_skipped_dedup,
        "documents_overlap": result.documents_overlap,
        "documents_failed": result.documents_failed,
        "by_carpeta": result.by_carpeta,
        "errors": result.errors,
    }, ensure_ascii=False, indent=2))

    _siguiente_paso(case)


@app.command()
def intake_judicial(
    case: str = typer.Option(..., "--case", help="case_id local (ej. 'BaRR3 - Roser 39 (W-030LFT) - Art 20 LAU')"),
    expediente: str = typer.Option(..., "--expediente", help="ID del expediente JUDICIAL en sudespacho"),
    element: str = typer.Option("expedientes_judiciales", "--element"),
    referencia: str = typer.Option(None, "--referencia", help="Referencia CRM (validación preventiva)"),
    full: bool = typer.Option(False, "--full/--no-full",
                              help="Baja el expediente COMPLETO (no solo demanda+contestación), "
                                   "dejando 05_CRM físicamente completo. La clasificación pasa a "
                                   "ser etiquetado: los roles ambiguos se avisan pero no bloquean."),
) -> None:
    """Intake del expediente judicial en el árbol del caso.

    Por defecto (intake acotado) descarga únicamente la demanda y la
    contestación, identificadas por heurística sobre el nombre/etiqueta del
    CRM; los roles ambiguos se marcan para revisión y NO se descargan.

    Con ``--full`` descarga el expediente COMPLETO (todo el gestor documental),
    dejando ``05_CRM`` físicamente completo; la clasificación se usa solo como
    etiquetado y los roles ambiguos se avisan sin bloquear la descarga.
    """
    case_manager.ensure_case(
        case,
        titulo=f"Expediente judicial sudespacho {expediente}",
        referencia_crm=referencia,
    )
    case_manager.register_expediente(case, expediente, element)

    try:
        result = intake_demanda_contestacion(
            case, expediente, element=element, full=full,
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
        "full": result.full,
        "demanda_doc_id": result.demanda_doc_id,
        "contestacion_doc_id": result.contestacion_doc_id,
        "pendientes_revision": result.pendientes,
        "documents_total_crm": result.pull.documents_total_crm if result.pull else 0,
        "documents_written": result.pull.documents_written if result.pull else 0,
        "documents_skipped_dedup": result.pull.documents_skipped_dedup if result.pull else 0,
        "documents_overlap": result.pull.documents_overlap if result.pull else 0,
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

    if result.pull and (result.pull.documents_written or result.pull.documents_overlap):
        _siguiente_paso(case, con_anonimizacion=True)


@app.command()
def sync_all() -> None:
    """Sincroniza TODOS los casos activos con sus expedientes registrados.

    Recorre data/CASOS/, lee los expedientes vinculados en _caso.md y ejecuta el pull
    de cada uno. Idempotente por hash: no hay flag `--incremental`.

    Los casos con estructura v1 (`00_Input/sudespacho_*/`) se reportan como bloqueados y
    NO abortan el barrido: se sigue con los demás y se resumen al final.
    """
    from core.config import caso_path, settings
    import yaml as _yaml

    casos = case_manager.list_cases()
    if not casos:
        typer.echo("No hay casos en data/CASOS/")
        return

    total_new = 0
    errors_global: list[str] = []
    bloqueados: list[str] = []
    tocados: list[str] = []

    for case_id in casos:
        from core.casos.case_locator import buscar
        base = buscar(case_id)
        if base is None:
            continue                   # el caso no existe
        index = base / "00_Input" / "_caso.md"
        if not index.exists():
            continue                   # el caso existe, `_caso.md` no

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
                result = pull_expediente_v2(case_id, exp_id, element=elem)
            except (SudespachoError, SudespachoLegacyError) as exc:
                msg = f"  ❌ {exp_id}: {exc}"
                typer.echo(msg)
                errors_global.append(f"{case_id}/{exp_id}: {exc}")
                continue

            if result.blocked_legacy_v1:
                typer.echo(f"  ⛔ {elem} {exp_id}: caso con estructura v1 — nada descargado")
                if case_id not in bloqueados:
                    bloqueados.append(case_id)
                continue

            new = result.documents_written
            total_new += new
            status = f"+{new} docs" if new else "sin cambios"
            icon = "🆕" if new else "✓"
            typer.echo(f"  {icon} {elem} {exp_id}: {status}")
            if new and case_id not in tocados:
                tocados.append(case_id)
            if result.errors:
                for e in result.errors:
                    typer.echo(f"     ⚠️  {e}")

    typer.echo(f"\n✅ Sync completado — {total_new} doc(s) nuevos en {len(casos)} caso(s)")
    if bloqueados:
        typer.echo(
            f"⛔ {len(bloqueados)} caso(s) con estructura v1 de intake "
            "(`00_Input/sudespacho_*/`), que el pull no toca. Migración manual: borrar "
            "esas carpetas y repetir el pull del caso."
        )
        for c in bloqueados:
            typer.echo(f"   {c}")
    if errors_global:
        typer.echo(f"⚠️  {len(errors_global)} error(s):")
        for e in errors_global:
            typer.echo(f"   {e}")
    if tocados:
        typer.echo("\n▶ Siguiente paso — este comando descarga, NO procesa. Por cada caso:")
        for c in tocados:
            typer.echo(f'    python -m scripts.sala_maquina apply "{c}"')


if __name__ == "__main__":
    app()
