"""CLI de la Sala de máquina: OCR+MD de un expediente (skill organizar-sala-maquina).

Uso:
  python -m scripts.sala_maquina plan  "<case_id>"            # solo propuesta
  python -m scripts.sala_maquina apply "<case_id>" [--vision] [--force]
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import typer

from core import sala_maquina as sm
from core.adjuntos_contenido import pipeline as contenido
from core.casos import case_locator
from core.config import caso_path
from core.email_atomize import pipeline as atomize
from core.intake_log import append_event
from core import split_documental as split
from core.utils import now_iso

app = typer.Typer(add_completion=False)

_STATE = "_sala_maquina_state.json"
_COBERTURA = "_cobertura.json"

_SEP = "=" * 72

_BANNER_FALLO_ATOMIZE = (
    f"\n{_SEP}\n"
    "AVISO: la atomización de correo FALLÓ ({tipo}: {exc}).\n"
    "El OCR continúa (no depende de ella), pero `01_Procesado/Emails` puede haber\n"
    "quedado a medias con el registro de IDs sin salvar (MEJORAS #99): revísalo antes\n"
    f"de citar MSG-ids nuevos.\n{_SEP}"
)

def _registrar_atomizado(case_id: str, details: dict) -> None:
    """Emite `atomizado_email`; un fallo de log nunca aborta el OCR."""
    try:
        append_event(case_id, "atomizado_email", details=details)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"AVISO: no se pudo registrar el evento atomizado_email: {exc}", err=True)


def _leer_estado(case_dir: Path) -> dict:
    """Estado completo: `procesados` (éxitos), `intentos` (fallos) y `hashes` (caché).

    Tolerante al esquema viejo (solo `procesados`): un caso ya procesado por el motor
    anterior estrena caché vacía y contadores a cero, que es lo correcto — no hay de
    dónde sacar los mtime de entonces.
    """
    f = sm._sala_maquina_dir(case_dir) / _STATE
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8")) or {}
    except (json.JSONDecodeError, OSError):
        # Estado ilegible: se trata como ausente. Se paga una corrida completa, que es
        # el lado seguro — lo contrario sería saltarse documentos por un fichero roto.
        return {}


def _estado_previo(case_dir: Path) -> set[str]:
    return set(_leer_estado(case_dir).get("procesados", []))


def _intentos_previos(case_dir: Path) -> dict[str, int]:
    crudo = _leer_estado(case_dir).get("intentos", {})
    return {k: int(v) for k, v in crudo.items()} if isinstance(crudo, dict) else {}


def _cache_hashes(case_dir: Path) -> dict[str, list]:
    crudo = _leer_estado(case_dir).get("hashes", {})
    return crudo if isinstance(crudo, dict) else {}


def _guardar_estado(case_dir: Path, shas: set[str], *,
                    intentos: dict[str, int] | None = None,
                    hashes: dict[str, list] | None = None) -> None:
    """Persiste el estado. `intentos`/`hashes` a `None` = conservar lo que hubiera.

    Conservar y no vaciar importa: `reforzar` y otros caminos llaman aquí sin saber nada
    de la caché, y vaciarla haría que la corrida siguiente rehashease el caso entero.
    """
    d = sm._sala_maquina_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "procesados": sorted(shas),
        "intentos": _intentos_previos(case_dir) if intentos is None else
                    {k: v for k, v in sorted(intentos.items()) if v},
        "hashes": _cache_hashes(case_dir) if hashes is None else hashes,
    }
    (d / _STATE).write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8")


def _resumir_tiempos(tiempos: list[dict], ms_total: int, ms_inv: int,
                     n_hasheados: int, n_inventariados: int) -> None:
    """Resumen por consola. Es el consumidor inmediato del rastro.

    Se imprime siempre, incluso cuando no se procesó ni un documento: ese es justo el
    caso que contesta la pregunta —una re-corrida sin cambios donde el inventario es el
    100 % del coste—.
    """
    typer.echo(
        f"  tiempos: total {ms_total/1000:.1f} s · inventario {ms_inv/1000:.1f} s "
        f"({n_hasheados} de {n_inventariados} ficheros hasheados)")
    if not tiempos:
        return
    por_metodo: dict[str, list[int]] = {}
    for t in tiempos:
        por_metodo.setdefault(t["metodo"] or "sin_fila", []).append(t["ms"])
    reparto = " · ".join(
        f"{m}: {sum(v)/1000:.1f} s ({len(v)})"
        for m, v in sorted(por_metodo.items(), key=lambda kv: -sum(kv[1])))
    typer.echo(f"  por método: {reparto}")
    lentos = sorted(tiempos, key=lambda t: -t["ms"])[:5]
    if lentos and lentos[0]["ms"] > 0:
        typer.echo("  más lentos: " + " · ".join(
            f"{t['rel_path']} {t['ms']/1000:.1f} s" for t in lentos))


def _registrar_tiempos(case_dir: Path, lineas: list[dict]) -> None:
    """Añade el rastro de tiempos a `_tiempos.jsonl`. Append-only a propósito.

    Comparar dos corridas ES el uso del artefacto —«¿duele la primera o la re-corrida?»—,
    así que sobrescribirlo lo anularía. Un fallo escribiéndolo nunca aborta nada: es
    instrumentación, no resultado.
    """
    try:
        d = sm._sala_maquina_dir(case_dir)
        d.mkdir(parents=True, exist_ok=True)
        with (d / "_tiempos.jsonl").open("a", encoding="utf-8") as fh:
            for linea in lineas:
                fh.write(json.dumps(linea, ensure_ascii=False) + "\n")
    except OSError as exc:
        typer.echo(f"AVISO: no se pudo escribir el rastro de tiempos: {exc}", err=True)


def _cobertura_previa(case_dir: Path) -> list[sm.DocCobertura]:
    """Cobertura estructurada persistida (`_cobertura.json`).

    Si falta —caso procesado antes de que ese fichero existiera (#84)— se reconstruye
    del frontmatter de `03_MD/` en vez de devolver `[]`: con `[]`, la fusión de una
    corrida incremental reducía el registro al delta y `_escribir_cobertura_md` borraba
    el resto del `_cobertura.md` (169 filas → 2 en W-02XOR7, medido el 2026-07-30).
    """
    sm_dir = sm._sala_maquina_dir(case_dir)
    f = sm_dir / _COBERTURA
    if not f.exists():
        cob = sm.reconstruir_cobertura_desde_md(sm_dir)
        if cob:
            # Parcial por construcción: los `sin_soporte` no dejan MD, así que su fila
            # solo vivía en la vista `_cobertura.md` y se pierde igual. Decirlo, no
            # presentar como total un arreglo que no lo es.
            typer.echo(
                f"AVISO: sin `_cobertura.json`; {len(cob)} filas RECONSTRUIDAS del "
                f"frontmatter de 03_MD/ (sin sha de origen ni campos de bundle). Los "
                f"documentos que no dejaron MD (p. ej. `sin_soporte`) no son "
                f"reconstruibles: para un registro completo, `apply --force` del caso.",
                err=True)
        return cob
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
    """Plan + `(cache_nueva, ms_inventario, n_hasheados, agotados)`.

    **Un solo seam a propósito.** La primera versión de esto dejaba un
    `_construir_plan` fino para los tests y un `_construir_plan_medido` para producción;
    `test_atomiza_antes_de_construir_el_plan_de_ocr` lo cazó en el acto — su doble se
    quedó fuera del camino real y el test dejó de verificar el orden sin ponerse rojo por
    ello. Un seam que solo pisan los tests es una comprobación que miente.

    El inventario es el coste fijo de CADA corrida —hoy rehashea `00_Input` entero, 2,6 GB
    en W-02VND1, aunque no haya nada nuevo—, así que se mide aparte del OCR: son las dos
    cifras que separan «duele la primera corrida» de «duelen las re-corridas».
    """
    previo = set() if force else _estado_previo(case_dir)
    intentos = {} if force else _intentos_previos(case_dir)
    agotados = frozenset(sha for sha, n in intentos.items() if n >= sm.MAX_INTENTOS)
    cache = _cache_hashes(case_dir)
    t0 = time.perf_counter()
    inventario, cache_nueva = sm.inventariar_cacheado(case_dir, cache)
    ms = int((time.perf_counter() - t0) * 1000)
    n_hasheados = sum(1 for rel, v in cache_nueva.items() if cache.get(rel) != v)
    return (sm.plan(inventario, previo, agotados), cache_nueva, ms, n_hasheados, agotados)


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


def _exigir_integridad(case_dir: Path, cob: list[sm.DocCobertura],
                       procesados: set[str]) -> None:
    """Aborta si la corrida dejó la Sala de máquina incoherente (spec §7.3).

    `procesados` son los slugs de los documentos que esta corrida procesó, tomados del
    PLAN y no de las filas resultantes. La diferencia es justo el caso para el que se
    escribe el guard: cuando un bundle revienta, `ejecutar` aísla el fallo y emite UNA
    fila de error con el slug del documento físico y **sin `parent_slug`**, así que un
    alcance derivado de las filas saldría vacío y el guard se quedaría ciego.

    Corre DESPUÉS de persistir: abortar antes de escribir perdería justo las filas que el
    guard existe para proteger, y dejaría el disco sin registro de lo que sí se publicó.
    Salida 3 (distinta de la 2 de los errores de uso y preflight): el operador debe poder
    distinguir «no empecé» de «terminé mal».
    """
    fallos = sm.verificar_integridad_bundles(case_dir, cob, procesados)
    if not fallos:
        return
    typer.echo("ERROR: la Sala de máquina quedó incoherente tras esta corrida "
               "(cobertura y artefactos no se corresponden):", err=True)
    for f in fallos:
        typer.echo(f"  - {f}", err=True)
    typer.echo("La cobertura y el estado SÍ se han persistido: revisa los segmentos "
               "citados antes de volver a lanzar.", err=True)
    raise typer.Exit(3)


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


def _atomizar_correo(case_id: str, case_dir: Path) -> None:
    """Atomiza el correo del caso ANTES del OCR (cableado, spec 2026-07-27 §4).

    Garantiza por código el orden intake → atomización → sala de máquina, en vez de
    dejarlo en la memoria del operador, y hace correr el detector de contaminación
    cruzada en toda corrida. Recibe el `case_dir` YA resuelto y compone las rutas desde
    él: no vuelve a localizar el caso (§4.6).

    Lo que este paso NO promete: que `01_Procesado/Emails` quede fresco y consumible
    sin comprobar nada. El motor no poda `adjuntos/` ni publica de forma atómica
    (`MEJORAS #99`), así que el consumidor DEBE leer el `status` del evento
    `atomizado_email`.
    """
    fuentes = atomize.emails_src_dirs_de_caso(case_dir)
    out = atomize.emails_out_dir_de_caso(case_dir)
    n = atomize.contar_eml(fuentes)

    # No-op estricto: sin correo Y sin árbol previo no se llama al motor — `atomize_dir`
    # crearía `mensajes/`/`adjuntos/` y sembraría carpetas vacías en todo caso sin
    # correo. Con árbol previo SÍ se llama, para que la retirada genuina se refleje.
    if n == 0 and not out.exists():
        return

    details: dict[str, object] = {"details_schema": 2, "eml_en_disco": n}
    try:
        report = atomize.atomize_dir(fuentes, out, case_dir=case_dir)
    except Exception as exc:  # noqa: BLE001 — el OCR no depende de la atomización
        # Fallo BLANDO para el OCR (una corrida dura ~1h40 y no depende de esto) pero
        # DURO para el registro: sin evento, este cableado convertiría una avería hoy
        # ruidosa (traceback del CLI manual) en silenciosa. No se fabrican contadores:
        # si el motor no terminó, el payload no finge saber cuántos mensajes hay.
        details["status"] = "fallo"
        details["errores"] = [f"{type(exc).__name__}: {exc}"]
        typer.echo(_BANNER_FALLO_ATOMIZE.format(tipo=type(exc).__name__, exc=exc), err=True)
    else:
        details["status"] = ("fallo" if not report.publicado
                             else "parcial" if report.errores else "ok")
        details.update({
            "eml_leidos": report.eml_leidos,
            "publicado": report.publicado,
            "poda_omitida": report.poda_omitida,
            "mensajes": report.mensajes,
            "adjuntos_unicos": report.adjuntos_unicos,
            "reconstruidos_b": report.reconstruidos_b,
            "citas_a_revision": report.citas_a_revision,
            "upgrades": report.upgrades,
            "notas": list(report.notas),
            "errores": list(report.errores),
            "fallos_lectura": list(report.fallos_lectura),
        })
        if not report.publicado:
            # `report.publicado is False` no es un "atomizado (fallo)": no se escribió NADA
            # (el árbol anterior queda intacto). Decirlo "atomizado" con un resumen en ceros
            # es indistinguible de una corrida vacía real (hallazgo 7 de la revisión final).
            typer.echo(f"Correo NO atomizado (no publicado): {report.resumen()}")
        else:
            typer.echo(f"Correo atomizado ({details['status']}): {report.resumen()}")
        for nota in report.notas:
            # Contaminación cruzada por W-code y vistas rotas: a stderr, ANTES del OCR,
            # para que el operador pueda abortar y limpiar `00_Input`.
            typer.echo(f"NOTA: {nota}", err=True)

    # Se emite ANTES de arrancar el OCR: si la corrida larga muere, el rastro ya está
    # en disco. Un fallo de log tampoco aborta el OCR.
    _registrar_atomizado(case_id, details)


def _adjuntos_dir_de(case_dir: Path) -> Path:
    """Carpeta de adjuntos del árbol atomizado. Un solo sitio que la componga."""
    return atomize.emails_out_dir_de_caso(case_dir) / "adjuntos"


def _procesar_adjuntos(case_id: str, case_dir: Path) -> None:
    """Extrae el texto de los adjuntos de correo. Cableado de `MEJORAS #87`, pieza 1.

    Hasta el 2026-08-04 `core.adjuntos_contenido` **no tenía ningún llamador** fuera de su
    propio paquete: la única vía era `python -m core.adjuntos_contenido <case_id>`, a mano,
    y ninguna skill ni el RUNBOOK la mencionaban. El contenido de los adjuntos, por tanto,
    no existía en el árbol de ningún caso.

    Va DESPUÉS de atomizar (los adjuntos solo existen en disco tras atomizar) y ANTES del
    OCR (si la corrida larga muere, el rastro del contenido ya está escrito). Se le pasa la
    RUTA y no el `case_id`: `procesar_caso` volvería a localizar el caso —`apply` ya lo
    resolvió— y en un checkout apuntaría al árbol equivocado.

    Fallo BLANDO para el OCR, DURO para el registro: mismo criterio que la atomización.
    """
    adjuntos_dir = _adjuntos_dir_de(case_dir)
    if not adjuntos_dir.is_dir():
        return                              # no-op estricto: sin correo no hay adjuntos

    details: dict = {}
    try:
        report = contenido.procesar_dir(adjuntos_dir)
    except Exception as exc:  # noqa: BLE001 — el OCR no depende de esto
        details = {"status": "fallo", "errores": [f"{type(exc).__name__}: {exc}"]}
        typer.echo(
            f"AVISO: el contenido de los adjuntos FALLÓ ({type(exc).__name__}: {exc}). "
            f"El OCR continúa; las fichas de `adjuntos/` se quedan sin texto.", err=True)
    else:
        details = {
            "status": "parcial" if report.errores else "ok",
            "extraidos": report.extraidos, "omitidos": report.omitidos,
            "sin_texto": report.sin_texto, "saltados": report.saltados,
            "podados": report.podados,
            "pendientes_vision": report.pendientes_vision,
            "errores": list(report.errores),
        }
        typer.echo(
            f"Adjuntos ({details['status']}): {report.extraidos} con texto, "
            f"{report.sin_texto} sin texto, {report.omitidos} omitidos, "
            f"{report.saltados} ya hechos, {report.pendientes_vision} a visión")
        for e in report.errores:
            typer.echo(f"NOTA (adjuntos): {e}", err=True)

    try:
        append_event(case_id, "contenido_adjuntos", details=details)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"AVISO: no se pudo registrar el evento contenido_adjuntos: {exc}",
                   err=True)


@app.command()
def plan(case_id: str):
    """Muestra la propuesta (Preview); no escribe nada salvo el manifiesto de
    segmentación propuesto (gate editable) de los bundles multi-documento detectados."""
    case_id, case_dir = _resolver_caso(case_id)
    # `plan` es preview: descarta la caché en vez de persistirla (no escribe estado) y
    # se queda solo con el plan y el recuento de agotados, que sí hay que declarar.
    p, _cache, _ms, _n, agotados = _construir_plan(case_dir, force=False)
    nuevos = [d for d in p if not d.skip]
    if agotados:
        typer.echo(f"  {len(agotados)} documento(s) con intentos agotados (se saltan; "
                   f"--force o --solo para reintentar)")
    # Los adjuntos NO se procesan en preview, pero callar cuántos hay esconde el coste que
    # `apply` va a pagar — y ese coste es nuevo desde que se cableó (`MEJORAS #87`).
    _adj_dir = _adjuntos_dir_de(case_dir)
    if _adj_dir.is_dir():
        n_adj = len(contenido.descubrir(_adj_dir))
        if n_adj:
            typer.echo(f"  adjuntos: {n_adj} (se extraerá su texto en apply)")
    typer.echo(f"Caso: {case_id}")
    for ruta in ("pdf", "imagen", "nativo", "sin_soporte"):
        n = sum(1 for d in nuevos if d.ruta == ruta)
        if n:
            typer.echo(f"  {ruta}: {n}")

    # Preview del cableado: `plan` NO atomiza (es preview), solo informa de lo que
    # `apply` atomizará, con el MISMO contador que usa `apply` (spec §4.7).
    n = atomize.contar_eml(atomize.emails_src_dirs_de_caso(case_dir))
    if n:
        typer.echo(f"  correo: {n} .eml (se atomizarán en apply)")

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
def apply(case_id: str, vision: bool = False, force: bool = False,
          solo: list[str] = typer.Option(
              None, "--solo",
              help="Ruta relativa de 00_Input a reprocesar aunque su sha ya esté hecho "
                   "(repetible). Nada más se toca. Para D1 de MEJORAS #90.")):
    """Ejecuta OCR+MD y escribe la Sala de máquina + cobertura + log."""
    # Los tests del CLI invocan estas funciones directamente (idiom del repo), así que
    # sin llamada de typer `solo` llega como OptionInfo, no como lista.
    rutas = list(solo) if isinstance(solo, list) else []
    if rutas and force:
        typer.echo(
            "ERROR: --solo y --force no se combinan. --force es autoritativo sobre el "
            "caso entero (cobertura fresca y estado reescrito); --solo es incremental y "
            "acotado. Mezclarlos borraría la cobertura y el estado de los documentos no "
            "pedidos.", err=True)
        raise typer.Exit(2)
    case_id, case_dir = _resolver_caso(case_id)
    if vision:
        _exigir_vision_cableada()          # preflight: aborta antes de procesar
    _atomizar_correo(case_id, case_dir)   # cableado: atomizar ANTES del OCR (spec §4)
    _procesar_adjuntos(case_id, case_dir)  # cableado: contenido de adjuntos (MEJORAS #87)
    t_corrida = time.perf_counter()
    try:
        p_bruto, cache_nueva, ms_inv, n_hasheados, agotados = \
            _construir_plan(case_dir, force=force)
        p = sm.acotar_plan(p_bruto, rutas)
    except ValueError as exc:              # errata en --solo: parar antes de OCR-izar
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(2) from exc

    # `--solo` desmarca el skip de lo pedido, incluidos los agotados: es la vía de escape
    # explícita, igual que `--force`.
    if agotados:
        typer.echo(
            f"AVISO: {len(agotados)} documento(s) con {sm.MAX_INTENTOS} intentos agotados "
            f"se saltan y NO se han vuelto a procesar. Si son TODOS los del caso, "
            f"sospecha del motor (¿está OCRmyPDF instalado?) antes de forzar. "
            f"Reintento: --force, o --solo <ruta>.", err=True)

    # Cobertura ACUMULATIVA: una corrida incremental procesa solo el delta, así que
    # la cobertura debe fusionarse con la persistida (si no, se pierden las filas de
    # corridas anteriores — bug de VALERO). Con --force, foto fresca (previa=[]):
    # nada se saltó, la corrida es autoritativa (simétrico con el estado).
    # Se lee AQUÍ, antes de procesar, porque el preflight la necesita como baseline de
    # identidades y porque leerla dos veces duplicaría su aviso de reconstrucción.
    previa = [] if force else _cobertura_previa(case_dir)
    try:
        sm.preflight_manifiestos(case_dir, p, previa, force=force)
    except split.ManifestValidationError as exc:
        typer.echo(f"ERROR: manifiesto de segmentación inválido; no se ha procesado "
                   f"nada.\n{exc}", err=True)
        raise typer.Exit(2) from exc

    tiempos: list[dict] = []

    def _medir(doc, ms: int, filas) -> None:
        tiempos.append({
            "tipo": "documento", "slug": doc.slug, "rel_path": doc.rel_path,
            "ruta": doc.ruta, "ms": ms,
            "metodo": filas[0].metodo if filas else "",
            "estado": filas[0].estado if filas else "",
            "segmentos": len(filas),
            "paginas": filas[0].paginas if filas else "",
        })

    cob_delta = sm.ejecutar(case_dir, p, case_id=case_id, vision=vision, force=force,
                            on_documento=_medir)

    # La corrida es AUTORITATIVA sobre lo que reprocesa (spec §6.1): sus filas previas se
    # descartan. El conjunto sale del PLAN, no de las filas, porque cuando un documento
    # falla no hay filas suyas que mirar.
    cob = sm.fusionar_cobertura(previa, cob_delta,
                                rel_paths_reprocesados={d.rel_path for d in p if not d.skip})
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

    # Contador de intentos (`MEJORAS #84`): +1 a cada documento que se procesó y NO
    # salió resuelto; se BORRA al primer éxito, para que un fallo transitorio no deje
    # deuda acumulada. Sin esto, un documento que no se resuelve vuelve a pagar OCR real
    # en cada corrida, para siempre.
    intentos = {} if force else dict(_intentos_previos(case_dir))
    for d in p:
        if d.skip:
            continue
        if d.sha256 in exitosos:
            intentos.pop(d.sha256, None)
        else:
            intentos[d.sha256] = intentos.get(d.sha256, 0) + 1
    _guardar_estado(case_dir, procesados, intentos=intentos, hashes=cache_nueva)
    append_event(case_id, "procesado_sala_maquina", details={
        "count": len(cob_delta),
        "files": [{"path": c.rel_path, "sha256": c.sha256, "slug": c.slug,
                   "metodo": c.metodo, "estado": c.estado} for c in cob_delta],
    })
    _exigir_integridad(case_dir, cob, {d.slug for d in p if not d.skip})
    dudosos = [c for c in cob if c.estado != "ok"]
    typer.echo(f"Sala de máquina actualizada: {len(cob)} documentos, {len(dudosos)} a revisar.")

    ms_total = int((time.perf_counter() - t_corrida) * 1000)
    _registrar_tiempos(case_dir, tiempos + [{
        "tipo": "corrida", "ts": now_iso(), "case_id": case_id,
        "ms_total": ms_total, "ms_inventario": ms_inv,
        "ficheros_hasheados": n_hasheados, "ficheros_inventariados": len(cache_nueva),
        "documentos_procesados": len(tiempos), "agotados": len(agotados),
        "force": bool(force), "solo": len(rutas),
    }])
    _resumir_tiempos(tiempos, ms_total, ms_inv, n_hasheados, len(cache_nueva))
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

    # `reforzar` es el otro comando que entra en `_split_o_md`, no acepta `--force` y no
    # tenía válvula propia: con un manifiesto legacy, `validar_manifiesto` lanzaba dentro
    # de `ejecutar`, el fallo quedaba aislado y la corrida cerraba en salida 3 DESPUÉS de
    # haber escrito.
    try:
        sm.preflight_manifiestos(case_dir, plan, previa)
    except split.ManifestValidationError as exc:
        typer.echo(f"ERROR: manifiesto de segmentación inválido; no se ha reforzado "
                   f"nada.\n{exc}", err=True)
        raise typer.Exit(2) from exc

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
    _exigir_integridad(case_dir, cob, {d.slug for d in plan})
    mejorados = sum(1 for c in cob_delta if c.estado == "ok")
    dudosos = [c for c in cob if c.estado != "ok"]
    typer.echo(f"Reforzados {len(cob_delta)} documentos ({mejorados} ahora ok); "
               f"{len(dudosos)} a revisar.")


if __name__ == "__main__":
    app()
