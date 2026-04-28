"""CLI: descarga masiva de expedientes desde sudespacho.net filtrados por cliente.

Recorre el listado paginado del frontal heredado, filtra por cliente
(por defecto: "EV MMC SPAIN, S.L.U.") y descarga el Gestor Documental
de cada uno al árbol local. Idempotente: cada expediente lleva su
propio marcador `.pulled` en `00_INPUT/sudespacho/`.

Uso típico:

    # Solo listar, no descargar (dry-run)
    python -m scripts.bulk_pull_expedientes \\
        --cliente "EV MMC SPAIN, S.L.U." --dry-run

    # Descargar todos los EV MMC SPAIN
    python -m scripts.bulk_pull_expedientes \\
        --cliente "EV MMC SPAIN, S.L.U."

    # Limitar a primeros N para una prueba
    python -m scripts.bulk_pull_expedientes \\
        --cliente "EV MMC SPAIN, S.L.U." --limit 10

    # Tirar contra otro elemento
    python -m scripts.bulk_pull_expedientes \\
        --cliente "EV MMC SPAIN, S.L.U." \\
        --element expedientes_extrajudiciales \\
        --element-url expedientesextrajudiciales

Convención de naming del case_id:
  EV-{serie_expediente}-{num_expediente:0>3}   (default --prefix EV)
  ej.: expediente con num=29 serie=2026 → EV-2026-029.

El script genera además un `_index.json` en CASOS_ROOT con metadatos
de todos los expedientes descargados/listados para servir como índice
del corpus.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import typer

from core import case_manager
from core.config import settings
from core.sync_sudespacho import pull_expediente, SudespachoError
from core.sync_sudespacho_legacy import (
    ExpedienteListEntry,
    SudespachoLegacyClient,
    SudespachoLegacyError,
)
from core.utils import slugify

app = typer.Typer(add_completion=False, help="Bulk pull de expedientes desde sudespacho.net")


def _case_id_for(entry: ExpedienteListEntry, prefix: str) -> str:
    """Construye un case_id local descriptivo y único.

    Patrón:
        {prefix}-{serie}-{exp_id}__{slug-de-referencia}

    Ejemplos:
        EV-2026-649__barr3_roser_39_w_030lft_art_20_lau
        EV-2026-650__mars10_francisco_largo_caballero_20_p4_w_030q92_bd
        EV-2026-615   (sin referencia → fallback al id)

    El prefijo `{prefix}-{serie}-{exp_id}` garantiza unicidad y orden
    cronológico al listar carpetas. El slug de la referencia añade
    descripción (inmueble, código catastral, tipo de caso). Se capa
    a 60 caracteres para que el path total no exceda el límite de
    Windows (260).
    """
    serie = entry.serie_expediente or datetime.now().strftime("%Y")
    base = f"{prefix}-{serie}-{entry.expediente_id}"
    ref = (entry.referencia_cliente or "").strip()
    if not ref or ref == "-":
        return base
    slug = slugify(ref, max_length=60)
    if not slug:
        return base
    return f"{base}__{slug}"


def _write_index(rows: list[dict]) -> Path:
    out = settings.casos_root / "_bulk_index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(rows),
        "expedientes": rows,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


@app.command("list")
def list_only(
    cliente: str = typer.Option("EV MMC SPAIN, S.L.U.", "--cliente",
                                help="Substring para filtrar la columna Cliente"),
    element: str = typer.Option("expedientes_judiciales", "--element"),
    element_url: str = typer.Option(None, "--element-url",
                                    help="Segmento URL del elemento (default: sin guiones bajos)"),
    num_results: int = typer.Option(50, "--num-results",
                                    help="Tamaño de página del listado (más alto = menos requests)"),
    limit: int = typer.Option(None, "--limit", help="Tope de expedientes a listar"),
) -> None:
    """Lista los expedientes del cliente sin descargar nada. Imprime tabla."""
    try:
        with SudespachoLegacyClient() as cli:
            count = 0
            typer.echo(
                f"{'EXP_ID':<6} {'FECHA':<11} {'POS':<10} "
                f"{'CONTRAPARTE':<35} CASE_ID"
            )
            typer.echo("-" * 170)
            for entry in cli.iter_all_expedientes(
                element=element, element_url=element_url,
                num_results=num_results, cliente_filter=cliente,
            ):
                case_id = _case_id_for(entry, prefix="EV")
                typer.echo(
                    f"{entry.expediente_id:<6} "
                    f"{(entry.fecha_alta or '-'):<11} "
                    f"{(entry.posicion_procesal or '-'):<10} "
                    f"{(entry.contraparte or '-')[:35]:<35} "
                    f"{case_id}"
                )
                count += 1
                if limit and count >= limit:
                    break
            typer.echo("-" * 170)
            typer.echo(f"Total filtrados: {count}")
    except SudespachoLegacyError as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1)


@app.command("pull")
def pull_all(
    cliente: str = typer.Option("EV MMC SPAIN, S.L.U.", "--cliente"),
    element: str = typer.Option("expedientes_judiciales", "--element"),
    element_url: str = typer.Option(None, "--element-url"),
    num_results: int = typer.Option(50, "--num-results"),
    limit: int = typer.Option(None, "--limit"),
    prefix: str = typer.Option("EV", "--prefix",
                               help="Prefijo del case_id local (EV-{serie}-{num})"),
    skip_pull: bool = typer.Option(False, "--skip-pull/--no-skip-pull",
                                   help="No descargar documentos, solo crear case_id e índice"),
    force: bool = typer.Option(False, "--force/--no-force",
                               help="Re-descarga aunque el marcador exista"),
    sleep_s: float = typer.Option(0.5, "--sleep-s",
                                  help="Pausa entre expedientes para no saturar el frontal"),
) -> None:
    """Descarga el Gestor Documental de cada expediente filtrado."""
    rows: list[dict] = []
    n_pulled = 0
    n_failed = 0
    n_skipped = 0

    try:
        legacy = SudespachoLegacyClient()
    except SudespachoLegacyError as exc:
        typer.echo(f"❌ Cliente legacy no disponible: {exc}")
        raise typer.Exit(code=1)

    try:
        for entry in legacy.iter_all_expedientes(
            element=element, element_url=element_url,
            num_results=num_results, cliente_filter=cliente,
        ):
            if limit is not None and len(rows) >= limit:
                break
            case_id = _case_id_for(entry, prefix=prefix)
            row = {
                "case_id": case_id,
                "expediente_id": entry.expediente_id,
                "element": element,
                "fecha_alta": entry.fecha_alta,
                "posicion_procesal": entry.posicion_procesal,
                "num_expediente": entry.num_expediente,
                "serie_expediente": entry.serie_expediente,
                "referencia": entry.referencia_cliente,
                "cliente": entry.cliente,
                "contraparte": entry.contraparte,
                "status": "pending",
                "error": None,
            }

            # Crear estructura del caso
            try:
                case_manager.ensure_case(
                    case_id,
                    titulo=entry.referencia_cliente
                           or f"Expediente {entry.expediente_id}",
                    cliente=entry.cliente,
                    contraparte=entry.contraparte,
                    drive_remote_path=f"sudespacho:{entry.expediente_id}",
                )
            except Exception as exc:  # noqa: BLE001
                row["status"] = "case_error"
                row["error"] = str(exc)
                rows.append(row)
                n_failed += 1
                typer.echo(f"❌ {case_id} (exp {entry.expediente_id}): {exc}")
                continue

            if skip_pull:
                row["status"] = "case_only"
                rows.append(row)
                n_skipped += 1
                typer.echo(f"📁 {case_id} (exp {entry.expediente_id}) caso creado")
                continue

            # Descargar Gestor Documental
            try:
                result = pull_expediente(
                    case_id, entry.expediente_id,
                    legacy_client=legacy,
                    element=element,
                    force=force,
                )
            except (SudespachoError, SudespachoLegacyError) as exc:
                row["status"] = "pull_error"
                row["error"] = str(exc)
                rows.append(row)
                n_failed += 1
                typer.echo(f"❌ {case_id} (exp {entry.expediente_id}): {exc}")
                continue

            row["status"] = "ok"
            row["documents_downloaded"] = result.documents_downloaded
            row["documents_total"] = result.documents_total
            row["bytes_downloaded"] = result.bytes_downloaded
            if result.errors:
                row["errors"] = result.errors
            rows.append(row)
            n_pulled += 1
            typer.echo(
                f"✅ {case_id} (exp {entry.expediente_id}): "
                f"{result.documents_downloaded} docs, "
                f"{result.bytes_downloaded // 1024} KB"
            )
            if sleep_s > 0:
                time.sleep(sleep_s)
    finally:
        legacy.__exit__(None, None, None)
        index_path = _write_index(rows)
        typer.echo("=" * 60)
        typer.echo(
            f"Resumen: {n_pulled} ok, {n_failed} con error, "
            f"{n_skipped} solo caso. Índice: {index_path}"
        )


if __name__ == "__main__":
    app()
