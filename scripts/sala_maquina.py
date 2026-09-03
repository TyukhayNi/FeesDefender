"""CLI de la Sala de máquina: OCR+MD de un expediente (skill organizar-sala-maquina).

Uso:
  python -m scripts.sala_maquina plan  "<case_id>"            # solo propuesta
  python -m scripts.sala_maquina apply "<case_id>" [--vision] [--force]
"""
from __future__ import annotations

import contextlib
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

def _registrar_atomizado(case_dir: Path, case_id: str, details: dict) -> None:
    """Emite `atomizado_email`; un fallo de log nunca aborta el OCR.

    B0-1: recibe el `case_dir` para que el evento caiga JUNTO A LOS BYTES. Con
    `--case-dir` los documentos van a la copia local, y hasta la Fase 1 el evento
    se iba a `CASOS_ROOT`: custodia partida en dos.
    """
    try:
        append_event(case_dir, "atomizado_email", case_id=case_id, details=details)
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


#: Base relativa de los derivados de la sala de máquina, con `/` como manda la costura.
_REL_SALA = "01_Procesado/02_Sala de máquina"


def _deposito_sala(ws):
    """La capacidad de escritura de los derivados, **ligada al workspace resuelto**.

    Es lo que convierte a `sala_maquina` en el **primer cliente de producción** de
    `core/casos/escritura.deposito()`. Hasta hoy la costura tenía cero llamadores: estaba
    construida, probada con 18 tests y 12 mutantes, y no la usaba nadie — la misma
    enfermedad que el mutex antes de 3A.

    **Pasa el `workspace`, y ahí está todo el asunto.** Sin él, `deposito()` resolvería el
    caso contra el catálogo y escribiría en el **canon** aunque se esté trabajando sobre
    una copia prestada: es el `H18-01` que este trabajo cierra.

    **No cambia el destino de nada.** `sala_maquina` ya escribía en `ws.working_root`; lo
    que gana es la contención de la base y la declaración del mutex. Decirlo importa
    porque un cliente que parece mover bytes y no los mueve es peor que ninguno.

    ## No hay red: si la costura no entrega capacidad, esto ABORTA

    Las dos versiones anteriores degradaban a la vía directa. La primera con un
    `except Exception`, que convertía cualquier bug mío en un `None` mudo. La segunda con
    un `except` estrecho de dos errores de identidad — y **R25/H25-05 mostró por qué eso
    seguía estando mal**: `IdentidadDiscordante` no significa «falta namespace», significa
    **no se ha demostrado qué caso se está escribiendo**. Degradarla salta exactamente la
    comprobación que acaba de fallar, y con el cierre de H25-01 habría convertido la nueva
    garantía en un bypass.

    Aquí no hay que proteger la pantalla de nadie: `sala_maquina` es una CLI que se corre a
    mano. Abortar con el error a la vista es la conducta correcta, y es la que el resto del
    entrypoint ya tiene para `CaseBusy` y `MutexPerdido`.
    """
    from core.casos import escritura

    return escritura.deposito(ws.case_ref, _REL_SALA, "sala_maquina",
                              clase="derivado", modo="libre", workspace=ws)


def _guardar_estado(case_dir: Path, shas: set[str], *,
                    intentos: dict[str, int] | None = None,
                    hashes: dict[str, list] | None = None,
                    dep=None) -> None:
    """Persiste el estado. `intentos`/`hashes` a `None` = conservar lo que hubiera.

    Conservar y no vaciar importa: `reforzar` y otros caminos llaman aquí sin saber nada
    de la caché, y vaciarla haría que la corrida siguiente rehashease el caso entero.

    `dep`: capacidad de `_deposito_sala`. `None` = la vía directa de siempre, que los
    tests existentes usan y que sigue siendo el camino cuando no hay workspace.
    """
    payload = {
        "procesados": sorted(shas),
        "intentos": _intentos_previos(case_dir) if intentos is None else
                    {k: v for k, v in sorted(intentos.items()) if v},
        "hashes": _cache_hashes(case_dir) if hashes is None else hashes,
    }
    cuerpo = json.dumps(payload, ensure_ascii=False, indent=2)
    if dep is not None:
        dep.escribir_texto(_STATE, cuerpo)
        return
    d = sm._sala_maquina_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / _STATE).write_text(cuerpo, encoding="utf-8")


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


def _guardar_cobertura(case_dir: Path, cob: list[sm.DocCobertura], *, dep=None) -> None:
    """`dep`: capacidad de `_deposito_sala`. `None` = la vía directa de siempre."""
    cuerpo = json.dumps(sm.cobertura_a_dicts(cob), ensure_ascii=False, indent=2)
    if dep is not None:
        dep.escribir_texto(_COBERTURA, cuerpo)
        return
    d = sm._sala_maquina_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / _COBERTURA).write_text(cuerpo, encoding="utf-8")


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


def _identidad_actor() -> tuple[str, str]:
    """Costura: `(usuario, maquina)`. Inyectable, como manda el §7."""
    import socket

    from core.intake_log import get_actor
    return get_actor(), socket.gethostname()


def _registro_de_workspaces(ahora: str):
    """Costura: el registro real. Los tests la sustituyen por uno en `tmp_path`."""
    from core.casos.workspace_registry import WorkspaceRegistry, raiz_por_defecto
    return WorkspaceRegistry(raiz_por_defecto(), ahora=ahora)


def _drive_accesible() -> bool:
    """¿Se puede confiar HOY en el estado compartido del canon? (§7.2.9-10)

    Hasta el Task 10 esto era el literal `True` en la llamada al resolver, y por eso
    **toda la rama offline del §7.2.9-10 era código muerto en producción**: el modo
    sin Drive existía en el diseño, tenía tests unitarios en el resolver y ningún
    entrypoint podía llegar a él. La fila 8 de la matriz del §14.1 —«runtime sin
    acceso → error, Drive intacto»— solo era inducible mintiéndole al resolver.

    La condición es **una sola y explícita**: `FEESDEFENDER_OFFLINE=1`, el control del
    operador —«estoy sin la unidad del despacho, trabaja contra mi checkout y no
    publiques»—, que es exactamente la declaración que el §7.1.5 pide para retirar las
    capacidades de canon.

    **La segunda condición que escribí y hubo que retirar, porque conviene no repetirla.**
    Añadí «…o la raíz del catálogo no está montada», con `Path(settings.casos_root).is_dir()`.
    Suena más listo y es **peor por dos razones que la suite midió en la primera corrida**:

    1. **Divergencia de fuente de verdad.** El catálogo localiza por `case_locator._root()`
       y esa comprobación miraba `settings.casos_root`. Tres tests parchean `_root` sin
       tocar el entorno, así que el catálogo encontraba el caso y la comprobación decía
       que no había Drive: el resolver se iba a `_offline` y abortaba con
       `RUNTIME_CANNOT_ACCESS_WORKSPACE` un caso perfectamente disponible.
    2. **Falso negativo en producción.** `data/CASOS` no existe en un clon limpio ni en
       un worktree, así que en cualquier máquina sin `CASOS_ROOT` apuntando a un montaje
       vivo **toda** invocación se habría ido al modo offline en silencio.

    Y no hacía falta: si la raíz no se puede leer, `catalogo.localizar` ya lanza
    `LocalWorkspaceMissing` unas líneas más arriba. Lo que aquí se decide es otra cosa
    —si el estado compartido es *de fiar*—, y de eso el único que sabe es el operador.

    Lo que **no** hace, y se declara: no distingue un montaje de Drive Stream con
    caché rancia de uno fresco. Esa es la comprobación que el §7.2 llama revalidar el
    nonce, y vive en el ciclo de checkout, no aquí.
    """
    import os

    return (os.getenv("FEESDEFENDER_OFFLINE") or "").strip() != "1"


def _workspace_legacy(case_id: str, case_dir: Path):
    """`CaseWorkspace` sobre una ruta que el catálogo NO conoce.

    Es la costura que conserva ~28 sitios de test —y el override por entorno que
    el §7.3 admite mientras queden componentes `legacy_unresolved`—. No es un
    agujero de autorización: si el canon no conoce el caso, **no hay lock que
    respetar**. El bloqueo solo puede existir donde hay algo que bloquear.
    """
    from core.casos.workspace_model import (CaseRef, CaseWorkspace, WorkspaceMode)
    return CaseWorkspace(
        case_ref=CaseRef(case_id=case_id, w_code=_wcode_o_none(case_id)),
        mode=WorkspaceMode.LOCAL_SCRATCH,
        working_root=case_dir, canonical_ref=None,
        checkout_user=None, checkout_maquina=None, checkout_nonce=None,
        checkout_timestamp=None,
        validado_en="", procedencia="legacy_unresolved",
    )


def _wcode_o_none(case_id: str) -> str | None:
    from core.casos.case_locator import _w_code_de
    return _w_code_de(case_id or "")


def _arg_o_none(valor):
    """Normaliza los sentinelas de Typer a `None`.

    Los tests de este repo invocan las funciones de comando DIRECTAMENTE (idiom
    del repo, ya declarado en `apply`), y entonces los defaults llegan como
    `OptionInfo`/`ArgumentInfo` en vez de `None`. Sin esto, un `--case-dir` no
    pasado parecia pasado y la puerta de exclusion mutua se disparaba siempre.
    """
    return valor if isinstance(valor, (str, Path)) else None


def _resolver_workspace(case_id: str | None, case_dir: str | None):
    """**¿Dónde se trabaja, y está permitido?** Sustituye a `_resolver_caso`.

    Antes esto resolvía una ruta y escribía sin preguntar a nadie: si el caso
    estaba prestado a otra máquina, el motor arrancaba igual y dejaba
    `_segmentacion.md`, estado, cobertura y evento sobre una copia que otro tenía
    en curso. Ahora la resolución **y la autorización** las da el resolver.

    Las dos formas de decir «este caso» son mutuamente excluyentes (§7.3):
    `--case-dir` es la selección explícita; la identidad, la vía ordinaria.
    """
    from core.casos.case_catalog import CaseCatalog
    from core.casos.workspace_model import (CaseRef, LocalWorkspaceMissing,
                                            WorkspaceError)
    from core.casos.workspace_resolver import CaseWorkspaceResolver
    from core.utils import now_iso

    case_id, case_dir = _arg_o_none(case_id), _arg_o_none(case_dir)
    if case_id and case_dir:
        typer.echo("[ERROR] --case-dir y la identidad del caso son mutuamente "
                   "excluyentes: elige una.", err=True)
        raise typer.Exit(code=2)
    if not case_id and not case_dir:
        typer.echo("[ERROR] falta el caso: pasa su case_id/W-code o --case-dir.",
                   err=True)
        raise typer.Exit(code=2)

    ahora = now_iso()
    usuario, maquina = _identidad_actor()
    catalogo = CaseCatalog()
    registro = _registro_de_workspaces(ahora)
    resolver = CaseWorkspaceResolver(catalogo, registro, usuario=usuario,
                                     maquina=maquina, ahora=ahora)

    drive_ok = _drive_accesible()

    if case_dir:
        try:
            ws = resolver.resolver_por_ruta(Path(case_dir), drive_accesible=drive_ok)
        except WorkspaceError as exc:
            typer.echo(f"[ERROR] {exc}", err=True)
            raise typer.Exit(code=2) from exc
        return ws.case_ref.case_id or Path(case_dir).name, ws

    case_id = case_locator.resolve_ref(case_id)
    ref = CaseRef(case_id=case_id, w_code=_wcode_o_none(case_id))

    # Se pregunta PRIMERO al catálogo. Si el canon no conoce el caso no hay lock
    # que respetar, y se conserva el binding del módulo (`legacy_unresolved`).
    try:
        catalogo.localizar(ref)
    except LocalWorkspaceMissing:
        # …salvo que ESTA máquina sí lo conozca. Sin esta rama, el trabajo offline
        # por identidad era inalcanzable (R8/H8-04, verificado en vivo): con la unidad
        # desmontada, `catalogo.localizar` falla, `caso_path` falla detrás y el usuario
        # recibe «Caso no encontrado» **teniendo el checkout delante**. El §7.2.9-10
        # existe justo para eso, y el resolver ya lo implementa (`_solo_local`): lo que
        # faltaba era que alguien le pasara la pregunta.
        #
        # No altera la precedencia que el Task 9 fijó: el catálogo sigue mandando
        # cuando conoce el caso. Esta rama solo se abre donde el canon calla, y ahí el
        # registro es más específico que el binding del módulo — que es el último
        # recurso, no el primero.
        if registro.buscar(ref):
            try:
                ws = resolver.resolver_por_identidad(ref, drive_accesible=drive_ok)
            except WorkspaceError as exc:
                typer.echo(f"[ERROR] {exc}", err=True)
                raise typer.Exit(code=2) from exc
            return case_id, ws
        try:
            case_dir_legacy = caso_path(case_id)
        except FileNotFoundError:
            typer.echo(f"[ERROR] Caso no encontrado: {case_id!r}. "
                       f"Comprueba el case_id o W-code.", err=True)
            raise typer.Exit(code=1)
        if not (case_dir_legacy / "00_Input").is_dir():
            typer.echo(
                f"[ERROR] Caso no encontrado: {case_id!r} (resuelto, pero sin "
                f"00_Input). Comprueba el case_id o W-code.", err=True)
            raise typer.Exit(code=1)
        return case_id, _workspace_legacy(case_id, case_dir_legacy)

    try:
        ws = resolver.resolver_por_identidad(ref, drive_accesible=drive_ok)
    except WorkspaceError as exc:
        # Código 2 y cero bytes: el motor no ha arrancado.
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=2) from exc
    return case_id, ws


@contextlib.contextmanager
def _bajo_mutex(ws, case_id: str):
    """Sostiene el mutex del caso mientras el subcomando trabaja (Plan 3A, Task 5).

    **Este es el sitio donde el mutex paga lo que costó.** El dolor medido que justificó
    la decisión D2 es literalmente éste: relanzar `apply` sin saber si la corrida anterior
    terminó, con dos procesos escribiendo OCR y estado sobre el mismo expediente. Hasta
    ahora el mutex existía, tenía cuatro rondas de revisión y no lo llamaba nadie.

    Se adquiere en los **dos** modos, no solo en `v1`: el modo que se usa hoy es `libre`,
    así que restringirlo a `v1` habría dejado el dolor medido sin cubrir.

    **Sin W-code no hay namespace**, y ahí se avisa en vez de abortar. Es el mismo
    trinquete de la frontera C1 de la costura: cerrar en falso una vía que hoy funciona le
    rompe el día al equipo, y declarar el hueco permite contarlo y cerrarlo después.
    """
    from core.casos import mutex_sesion
    from core.casos.workspace_model import CaseBusy, CaseRef, MutexPerdido
    # `now_iso_utc` y NO `now_iso`: la primitiva rechaza un instante sin offset porque
    # uno naïve se lee en hora local y el lease se calcularía mal.
    from core.utils import now_iso_utc

    w = getattr(getattr(ws, "case_ref", None), "w_code", None)
    if not w:
        typer.echo(
            "[aviso] este caso no declara W-code, así que la corrida NO va bajo el mutex: "
            "otro proceso de esta máquina podría estar escribiendo el mismo expediente",
            err=True)
        yield None
        return
    try:
        with mutex_sesion.sostenido(CaseRef(w_code=w), ahora_fn=now_iso_utc) as sesion:
            yield sesion
    except CaseBusy as exc:
        # Código 2 y cero bytes, igual que el resto de abortos de este entrypoint: el
        # motor no ha arrancado. Un traceback aquí sería un fallo de producto, porque
        # «otra corrida está en curso» es información útil, no un error de programación.
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=2) from exc
    except MutexPerdido as exc:
        # Distinto de `CaseBusy` en el mensaje **y en lo que significa**: aquí el motor SÍ
        # arrancó y el lease se perdió a mitad —lease vencido, reloj movido, o alguien
        # borró el lock—, así que puede haber trabajo a medio publicar. Sin esta rama el
        # usuario recibía un traceback al final de un OCR largo, que es el peor momento
        # posible para tener que interpretar una excepción.
        typer.echo(
            f"[ERROR] {exc}. El mutex se perdió DURANTE la corrida, así que el "
            f"resultado puede estar a medias: revisa `_cobertura.md` antes de fiarte, y "
            f"comprueba si otro proceso entró.", err=True)
        raise typer.Exit(code=2) from exc


def _exigir(ws, *caps) -> None:
    """Los subcomandos declaran qué necesitan; el modo decide si lo tienen."""
    from core.casos.workspace_model import CapabilityDenied
    try:
        for cap in caps:
            ws.exigir(cap)
    except CapabilityDenied as exc:
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=2) from exc


def _resolver_caso(case_id: str) -> tuple[str, Path]:
    """Compatibilidad: devuelve `(case_id, case_dir)` como antes.

    Se conserva porque hay llamadores internos y tests que la usan; lo que ya no
    hace es ser la ÚNICA puerta: la autorización vive en `_resolver_workspace`.
    """
    cid, ws = _resolver_workspace(case_id, None)
    return cid, ws.working_root


def _atomizar_correo(case_id: str, case_dir: Path) -> str | None:
    """Atomiza el correo del caso ANTES del OCR (cableado, spec 2026-07-27 §4).

    Devuelve el status de ESTA corrida — `"ok" | "parcial" | "fallo"` — o `None` si no se
    ejecuto (no-op estricto). Lo devuelve ADEMAS de emitirlo en el evento porque el
    consumidor que lee el ultimo `atomizado_email` del log no puede saber si es suyo: en
    una corrida que no atomiza, el ultimo evento es de la corrida anterior.

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
        return None

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
    _registrar_atomizado(case_dir, case_id, details)
    return details.get("status")


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
        # B0-1: junto a los bytes, que es lo que `--case-dir` necesita.
        append_event(case_dir, "contenido_adjuntos", case_id=case_id, details=details)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"AVISO: no se pudo registrar el evento contenido_adjuntos: {exc}",
                   err=True)


@app.command()
def plan(case_id: str = typer.Argument(None),
         case_dir: str = typer.Option(None, "--case-dir",
                                      help="Ruta de la copia local (excluyente "
                                           "con la identidad del caso).")):
    """Propuesta de la Sala de máquina. **ESCRIBE** el manifiesto de segmentación.

    Deja `_segmentacion.md` en los bundles multi-documento detectados (gate
    editable). Se anunciaba como «preview; no escribe nada salvo…», y que un
    comando llamado `plan` escriba en el expediente es de las cosas que hay que
    declarar en la ayuda, no descubrir.
    """
    case_id, ws = _resolver_workspace(case_id, case_dir)
    with _bajo_mutex(ws, case_id):
        from core.casos.workspace_model import Capability
        _exigir(ws, Capability.WRITE_CASE, Capability.GENERATE_DERIVATIVES)
        case_dir = ws.working_root
        # `plan` NO construye la capacidad: no persiste estado ni cobertura, asi que
        # pedirla seria una llamada MUERTA —y una que puede abortar el comando por un
        # resultado que nadie usa—. La primera version la puso aqui por un reemplazo
        # mecanico sobre todas las apariciones de `case_dir = ws.working_root`, sin mirar
        # si el comando escribia (R25/H25-04). Su unico manifiesto, `_segmentacion.md`,
        # sigue por `split.escribir_manifiesto` y queda DECLARADO sin migrar.
        #
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
def apply(case_id: str = typer.Argument(None), vision: bool = False,
          force: bool = False,
          case_dir: str = typer.Option(None, "--case-dir",
                                       help="Ruta de la copia local (excluyente "
                                            "con la identidad del caso)."),
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
    case_id, ws = _resolver_workspace(case_id, case_dir)
    with _bajo_mutex(ws, case_id):
        from core.casos.workspace_model import Capability
        _exigir(ws, Capability.WRITE_CASE, Capability.GENERATE_DERIVATIVES)
        case_dir = ws.working_root
        _dep_sala = _deposito_sala(ws)
        if vision:
            _exigir_vision_cableada()          # preflight: aborta antes de procesar
        status_atomizacion = _atomizar_correo(case_id, case_dir)  # ANTES del OCR (spec §4)
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
        _guardar_cobertura(case_dir, cob, dep=_dep_sala)
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
        _guardar_estado(case_dir, procesados, intentos=intentos,
                        hashes=cache_nueva, dep=_dep_sala)
        # B0-1: `apply`/`reforzar` resuelven el `case_dir` al principio, asi que el
        # evento cae junto a los bytes aunque no lo lleven en la firma. Mi criterio
        # inicial —«lo tiene en la FIRMA»— era demasiado estrecho y dejaba fuera a dos
        # llamadores que si podian migrar.
        append_event(case_dir, "procesado_sala_maquina", case_id=case_id, details={
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
        # Typer ignora el retorno de un comando, asi que el CLI no cambia. Quien lo lee es
        # el secuenciador de V1, que llama a esta funcion directamente (el idiom de los
        # tests de este repo) y necesita el status para la maquina de estados de D4.
        return status_atomizacion


# metodos con páginas renderizables: solo estos se benefician del refuerzo por
# visión (nativo/sin_soporte/error no tienen un PDF que renderizar página a página).
_REFORZABLES = ("pypdf", "ocr")


@app.command()
def reforzar(case_id: str = typer.Argument(None),
             case_dir: str = typer.Option(None, "--case-dir",
                                          help="Ruta de la copia local (excluyente "
                                               "con la identidad del caso).")):
    """Re-procesa con visión SOLO los documentos dudosos ya conocidos y persiste.

    Cierra el ciclo que en VALERO hubo que hacer a mano: coge los `low`/`empty` con
    páginas renderizables de la cobertura, los pasa por `ejecutar(vision=True)`, y
    reescribe MD + estado + cobertura. Exige el transcriptor cableado (flujo skill/
    sesión); el CLI pelado aborta en el preflight.
    """
    case_id, ws = _resolver_workspace(case_id, case_dir)
    with _bajo_mutex(ws, case_id):
        from core.casos.workspace_model import Capability
        _exigir(ws, Capability.WRITE_CASE, Capability.GENERATE_DERIVATIVES)
        case_dir = ws.working_root
        _dep_sala = _deposito_sala(ws)
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
        _guardar_cobertura(case_dir, cob, dep=_dep_sala)
        _escribir_cobertura_md(case_dir, cob)

        exitosos = _exitosos_por_bundle(cob_delta)
        _guardar_estado(case_dir, _estado_previo(case_dir) | exitosos,
                        dep=_dep_sala)
        # B0-1: `apply`/`reforzar` resuelven el `case_dir` al principio, asi que el
        # evento cae junto a los bytes aunque no lo lleven en la firma. Mi criterio
        # inicial —«lo tiene en la FIRMA»— era demasiado estrecho y dejaba fuera a dos
        # llamadores que si podian migrar.
        append_event(case_dir, "procesado_sala_maquina", case_id=case_id, details={
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
