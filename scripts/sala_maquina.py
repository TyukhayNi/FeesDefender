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
from core.casos import case_locator
from core.config import caso_path
from core.intake_log import append_event

app = typer.Typer(add_completion=False)

_STATE = "_sala_maquina_state.json"
_COBERTURA = "_cobertura.json"


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


def _cobertura_previa(case_dir: Path) -> list[sm.DocCobertura]:
    """Cobertura estructurada persistida (`_cobertura.json`); `[]` si no hay."""
    f = sm._sala_maquina_dir(case_dir) / _COBERTURA
    if not f.exists():
        return []
    return sm.cobertura_desde_dicts(json.loads(f.read_text(encoding="utf-8")))


def _guardar_cobertura(case_dir: Path, cob: list[sm.DocCobertura]) -> None:
    d = sm._sala_maquina_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / _COBERTURA).write_text(
        json.dumps(sm.cobertura_a_dicts(cob), ensure_ascii=False, indent=2),
        encoding="utf-8")


def _escribir_cobertura_md(case_dir: Path, cob: list[sm.DocCobertura]) -> None:
    """Vista humana derivada del registro estructurado (`_revisar/_cobertura.md`)."""
    revisar = case_dir / "01_Procesado" / "_revisar"
    revisar.mkdir(parents=True, exist_ok=True)
    (revisar / "_cobertura.md").write_text(sm.render_cobertura(cob), encoding="utf-8")


def _exigir_vision_cableada() -> None:
    """Preflight de `--vision`: aborta EN ALTO si no hay transcriptor cableado.

    Antes esto era un no-op silencioso (el stub lanzaba y `_reforzar_con_vision` lo
    tragaba dejando una nota 'refuerzo vision falló…' por documento, aparentando un
    intento real). Ahora se avisa antes de procesar nada (fallo de VALERO).
    """
    if not sm.vision_cableada():
        typer.echo(
            "ERROR: --vision requiere un transcriptor cableado y aquí no lo hay.\n"
            "El CLI local no puede invocar la sesión Claude por sí mismo: usa el "
            "flujo de la skill organizar-sala-maquina (que inyecta el transcriptor), "
            "o corre sin --vision.")
        raise typer.Exit(2)


def _construir_plan(case_dir: Path, force: bool):
    previo = set() if force else _estado_previo(case_dir)
    return sm.plan(sm.inventariar(case_dir), previo)


def _exitosos_por_bundle(cob_delta: list[sm.DocCobertura]) -> set[str]:
    """Shas FÍSICOS marcables como "hecho" en el estado idempotente.

    Agrupa la cobertura por el sha del fichero de ORIGEN (`parent_sha256`, con
    fallback a `sha256` para filas no-split: nativo/imagen/passthrough) y marca un
    bundle hecho solo si TODOS sus documentos lógicos salieron `ok`/`low`. Así (a)
    el estado usa el sha que `plan()` consulta para el *skip* (no el `seg_sha256` de
    un segmento, que haría re-split en cada corrida) y (b) un bundle con un segmento
    fallido NO se marca hecho → se reintenta en la siguiente corrida.
    """
    from collections import defaultdict
    por_fisico: dict[str, list[sm.DocCobertura]] = defaultdict(list)
    for c in cob_delta:
        por_fisico[c.parent_sha256 or c.sha256].append(c)
    return {sha for sha, filas in por_fisico.items()
            if all(f.estado in ("ok", "low") for f in filas)}


def _resolver_caso(case_id: str) -> tuple[str, Path]:
    """Resuelve `case_id` (case_id canónico o W-code) a su carpeta real.

    `caso_path`/`path_for` solo entienden layout flat o por ciudad buscando
    ``case_id`` COMO NOMBRE DE CARPETA — nunca resuelven un W-code
    (``meta.id_go``). Sin este paso, un W-code puro no encontraba el caso
    real y `path_for` caía a su fallback flat inexistente: la corrida seguía
    en silencio con plan vacío ("0 documentos" reportado como éxito) y
    creaba ahí una carpeta fantasma (bug reproducido 2026-07-22, W-02ZIIF).
    Mismo patrón que ``scripts/atomize_emails.py``/``scripts/crm_ficha.py``.
    """
    case_id = case_locator.resolve_ref(case_id)
    case_dir = caso_path(case_id)
    if not (case_dir / "00_Input").is_dir():
        typer.echo(
            f"[ERROR] Caso no encontrado: {case_id!r} (ruta resuelta sin "
            f"00_Input: {case_dir}). Comprueba el case_id o W-code.",
            err=True,
        )
        raise typer.Exit(code=1)
    return case_id, case_dir


@app.command()
def plan(case_id: str):
    """Muestra la propuesta (Preview); no escribe nada salvo el manifiesto de
    segmentación propuesto (gate editable) de los bundles multi-documento detectados."""
    case_id, case_dir = _resolver_caso(case_id)
    p = _construir_plan(case_dir, force=False)
    nuevos = [d for d in p if not d.skip]
    typer.echo(f"Caso: {case_id}")
    for ruta in ("pdf", "imagen", "nativo", "sin_soporte"):
        n = sum(1 for d in nuevos if d.ruta == ruta)
        if n:
            typer.echo(f"  {ruta}: {n}")

    # Pre-detección de bundles (Preview del split): informa de los PDFs multi-documento
    # y deja su manifiesto de segmentación propuesto (editable) para que el letrado lo
    # ajuste antes de `apply`. Solo corre sobre PDFs ya buscables (con capa de texto);
    # los escaneados sin OCR aún se segmentan en `apply`, tras el OCR (asimetría
    # documentada en el SKILL). El gate sigue vigente: `apply` respeta el manifiesto si
    # existe y solo lo crea si falta.
    from core import split_documental as split
    sm_dir = sm._sala_maquina_dir(case_dir)
    for d in nuevos:
        if d.ruta != "pdf":
            continue
        src = case_dir / "00_Input" / d.rel_path
        try:
            segmentos, blancos = split.detectar(src)
        except Exception:
            continue
        if len(segmentos) > 1:
            carpeta = sm.destino_seguro(sm_dir / "02_Documentos" / d.slug, case_dir)
            if not split.manifiesto_existe(carpeta):
                split.escribir_manifiesto(carpeta, split.construir_manifiesto(
                    d.rel_path, d.sha256, segmentos, blancos))
            typer.echo(f"  bundle {d.rel_path}: {len(segmentos)} documentos → revisa "
                       f"{carpeta / '_segmentacion.md'} y ajusta antes de apply")

    typer.echo(f"  (saltados por sha ya procesado: {sum(1 for d in p if d.skip)})")


@app.command()
def apply(case_id: str, vision: bool = False, force: bool = False):
    """Ejecuta OCR+MD y escribe la Sala de máquina + cobertura + log."""
    case_id, case_dir = _resolver_caso(case_id)
    if vision:
        _exigir_vision_cableada()          # preflight: aborta antes de procesar
    p = _construir_plan(case_dir, force=force)
    cob_delta = sm.ejecutar(case_dir, p, case_id=case_id, vision=vision, force=force)

    # Cobertura ACUMULATIVA: una corrida incremental procesa solo el delta, así que
    # la cobertura debe fusionarse con la persistida (si no, se pierden las filas de
    # corridas anteriores — bug de VALERO). Con --force, foto fresca (previa=[]):
    # nada se saltó, la corrida es autoritativa (simétrico con el estado).
    previa = [] if force else _cobertura_previa(case_dir)
    cob = sm.fusionar_cobertura(previa, cob_delta)
    _guardar_cobertura(case_dir, cob)
    _escribir_cobertura_md(case_dir, cob)

    # El estado idempotente solo cuenta lo que produjo salida real (ok/low): un
    # PDF cifrado/bloqueado NO se marca "resuelto", así se reintenta en la
    # siguiente corrida normal de apply (sin --force). Se calcula sobre el DELTA
    # de esta corrida, no sobre la cobertura fusionada.
    #
    # Con --force el plan trae TODOS los documentos (nada se saltó), así que el
    # estado nuevo debe reflejar SOLO los éxitos de esta corrida: no se une con el
    # estado en disco, que puede marcar "resuelto" un documento que ahora falla
    # (p. ej. tras cambiar el motor OCR) → si se uniera, la siguiente corrida
    # normal lo saltaría, contradiciendo "un fallo se reintenta sin --force".
    exitosos = _exitosos_por_bundle(cob_delta)
    procesados = exitosos if force else (_estado_previo(case_dir) | exitosos)
    _guardar_estado(case_dir, procesados)
    append_event(case_id, "procesado_sala_maquina", details={
        "count": len(cob_delta),
        "files": [{"path": c.rel_path, "sha256": c.sha256, "slug": c.slug,
                   "metodo": c.metodo, "estado": c.estado} for c in cob_delta],
    })
    dudosos = [c for c in cob if c.estado != "ok"]
    typer.echo(f"Sala de máquina actualizada: {len(cob)} documentos, {len(dudosos)} a revisar.")
    typer.echo("Siguiente paso sugerido: organizar-sala-lectura sobre este caso.")


# metodos con páginas renderizables: solo estos se benefician del refuerzo por
# visión (nativo/sin_soporte/error no tienen un PDF que renderizar página a página).
_REFORZABLES = ("pypdf", "ocr")


@app.command()
def reforzar(case_id: str):
    """Re-procesa con visión SOLO los documentos dudosos ya conocidos y persiste.

    Cierra el ciclo que en VALERO hubo que hacer a mano: coge los `low`/`empty` con
    páginas renderizables de la cobertura, los pasa por `ejecutar(vision=True)`, y
    reescribe MD + estado + cobertura. Exige el transcriptor cableado (flujo skill/
    sesión); el CLI pelado aborta en el preflight.
    """
    case_id, case_dir = _resolver_caso(case_id)
    _exigir_vision_cableada()
    previa = _cobertura_previa(case_dir)
    if not previa:
        typer.echo("Nada que reforzar: no hay cobertura. Corre `apply` primero.")
        return
    objetivos = {c.rel_path for c in previa
                 if c.estado in ("low", "empty") and c.metodo in _REFORZABLES}
    if not objetivos:
        typer.echo("0 documentos a reforzar (ningún dudoso con páginas renderizables).")
        return

    # estado_previo=set() → nada se salta; filtramos el plan a los objetivos, que se
    # re-procesan íntegros (reutiliza `ejecutar`; re-OCR-iza, decisión del diseño).
    plan = [d for d in sm.plan(sm.inventariar(case_dir), estado_previo=set())
            if d.rel_path in objetivos]
    if not plan:
        # Los dudosos están en la cobertura previa pero ya no en 00_Input (borrados
        # o renombrados). Sin este guard se reescribiría cobertura/estado idénticos
        # y se emitiría un evento forense count=0 (ruido en el log de custodia).
        typer.echo(f"Los {len(objetivos)} documentos dudosos ya no están en "
                   "00_Input (borrados o renombrados); nada que reforzar.")
        return
    cob_delta = sm.ejecutar(case_dir, plan, case_id=case_id, vision=True)

    cob = sm.fusionar_cobertura(previa, cob_delta)
    _guardar_cobertura(case_dir, cob)
    _escribir_cobertura_md(case_dir, cob)

    exitosos = _exitosos_por_bundle(cob_delta)
    _guardar_estado(case_dir, _estado_previo(case_dir) | exitosos)
    append_event(case_id, "procesado_sala_maquina", details={
        "modo": "reforzar",
        "count": len(cob_delta),
        "files": [{"path": c.rel_path, "sha256": c.sha256, "slug": c.slug,
                   "metodo": c.metodo, "estado": c.estado} for c in cob_delta],
    })
    mejorados = sum(1 for c in cob_delta if c.estado == "ok")
    dudosos = [c for c in cob if c.estado != "ok"]
    typer.echo(f"Reforzados {len(cob_delta)} documentos ({mejorados} ahora ok); "
               f"{len(dudosos)} a revisar.")


if __name__ == "__main__":
    app()
