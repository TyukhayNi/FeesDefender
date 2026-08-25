"""Log append-only de eventos de intake (M10).

Por cada caso, una línea JSON por evento en
``00_Input/_intake_log.jsonl``. Trazabilidad forense para prueba documental:
quién hizo qué, cuándo y con qué efecto sobre el repositorio del caso.

Decisiones cerradas (memoria persistente: ``project_intake_estructura_v2.md``):

- M10-Q1: 27 tipos de evento permitidos (constante ``INTAKE_EVENTS``).
- M10-Q2: schema común ``{ts, actor, event, case_id, details}`` con
  ``details`` específico por evento.
- M10-Q3: actor resuelto desde un singleton thread-safe (``set_actor`` /
  ``get_actor``). La UI Streamlit sincroniza el actor desde
  ``st.session_state['actor']`` al inicio de cada request (paso 7).
- M10-Q4: ``flush()`` + ``os.fsync()`` tras cada escritura. Append en modo
  ``"a"``. JSONL es resiliente a crashes en escrituras parciales.
- M10-Q5: sin rotación de archivos (rotar por año si llega a ser problema).
- M10-Q6: sin vista UI dedicada — auditoría = abrir el ``.jsonl`` con editor.
- M10-Q7: solo eventos automáticos del código. Anotaciones manuales del
  abogado van a ``90_Notas personales/``, no al log.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .utils import now_iso


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Tipos de evento permitidos (M10-Q1). Set cerrado: añadir un nuevo evento
# aquí + documentar el shape de ``details`` en project_intake_estructura_v2.md
# antes de emitirlo desde el código.
INTAKE_EVENTS: frozenset[str] = frozenset({
    "link_expediente",      # vincular un expediente CRM al caso
    "unlink_expediente",    # desvincular (rara — typo, expediente incorrecto, etc.)
    "pull_crm",             # pull de docs vía sync_sudespacho
    "pull_drive_ev",        # pull de docs vía intake_drive (rclone gdrive_ev)
    "upload_manual",        # upload manual a 04_Manual/
    "upload_email",         # ingest de hilo email a 03_Email/...
    "upload_drive_link",    # rescate de ficheros enlazados a Drive/Gmail en el cuerpo (Parte 2)
    "upload_whatsapp",      # ingest de export WhatsApp a 02_Whatsapp/...
    "upload_entrevista",    # subida grabación + transcripción a 06_Entrevistas/...
    "dedup_skipped",        # M9: doc skipped por SHA-256 ya presente, alias registrado
    "category_unknown",     # crm_branch_path → fallback (M5)
    "overwrite_doc",        # sobrescritura de un fichero existente
    "delete_doc",           # borrado explícito de un fichero
    "migrate_v1_v2",        # migración manual de un caso v1 (sudespacho_*/) a v2
    "intake_judicial",      # intake acotado demanda+contestación (resumen)
    "pendiente_revision",   # rol (demanda/contestación) no resuelto → revisión letrado
    "cross_source_overlap", # doc byte-idéntico a otro ya presente, escrito igualmente (physical_complete)
    "conjunto_detectado",   # D9: lote cabecera+prueba detectado por timestamp ∩ patrón D NN (alta confianza)
    # Biblioteca de casos (checkout/checkin, DISEÑO_V2 merge+biblioteca):
    "case_checkout",        # adquisición del lock + copia Drive→local (§3)
    "case_checkin",         # merge Desktop→Drive completado y verificado (§4)
    "checkout_cancelado",   # cancelación de checkout: local descartado (§2, §7.1)
    "pendiente_checkin",    # guard §6: escritura desviada a _pendiente_checkin/ (caso prestado)
    "procesado_sala_maquina",  # OCR+MD escritos en 01_Procesado/02_Sala de máquina/
    "split_documental",        # split 1→N de un bundle en 02_Documentos/ (documentos lógicos)
    "migracion_layout_intake",  # migración bajo demanda a lotes (#54): details =
                                 # {"lotes": [nombres], "remapeados": {registro: n}}
    "archivado",                # archivo del expediente inviable (RUNBOOK §10; MEJORAS #70.a):
                                 # details = {"motivo": MAYUSCULAS_GUION_BAJO, "fecha": ISO}
    "contenido_adjuntos",       # extracción del texto de los adjuntos de correo,
                                # encadenada por la sala de máquina (`MEJORAS #87`).
                                # details = {"status": ok|parcial|fallo, "extraidos",
                                # "omitidos", "sin_texto", "saltados", "podados",
                                # "pendientes_vision", "errores"}. En la rama de
                                # excepción SOLO lleva status + errores: si el motor no
                                # terminó, el payload no finge saber cuántos hay.
    "atomizado_email",          # atomización de correo encadenada por la sala de máquina.
                                 # details_schema 2: {"status": ok|parcial|fallo,
                                 # "eml_en_disco", "eml_leidos", "publicado",
                                 # "poda_omitida", + contadores del AtomizeReport si el
                                 # motor terminó}. El status `noop` que existía en el schema
                                 # anterior lo emitía la rama de discrepancia de #98, retirada;
                                 # un evento de schema 2 nunca lo lleva. No lleva "files".
                                 # Sin `details_schema`: forma 1 (claves
                                 # `eml_nivel_superior`/`eml_totales`, retiradas en #98).

    # --- Fase 1 dual: ciclo de vida del workspace (Task 8) -------------------
    # Se declaran aqui aunque su EMISION llegue en fases posteriores: el
    # vocabulario del log es contrato de lectura, y un evento que no se puede
    # nombrar no se puede escribir cuando toque.
    "scratch_creado",                # nace un local_scratch sin canon todavia
    "scratch_promovido",             # el scratch pasa a expediente publicado
    "checkout_adoptado",             # §15: adopcion explicita de un checkout legacy
    "conflicto_resuelto",            # se sale de estado_repositorio=conflicto
    "checkout_cancelado_unilateral", # el lock se cancelo mientras el titular
                                     # trabajaba offline (§8.7)
})


_LOG_FILENAME = "_intake_log.jsonl"


# ---------------------------------------------------------------------------
# Actor activo (singleton thread-safe)
# ---------------------------------------------------------------------------

# La UI Streamlit lee st.session_state['actor'] al inicio de cada request y
# llama set_actor(). Fuera de Streamlit (CLI / tests / scripts), get_actor()
# resuelve el actor por defecto desde FEESDEFENDER_ACTOR o os.getlogin().

_actor_lock = threading.Lock()
_actor: str | None = None


def _default_actor() -> str:
    """Actor por defecto cuando no se ha llamado ``set_actor()``.

    Orden de resolución:

    1. Variable de entorno ``FEESDEFENDER_ACTOR`` (útil en CI / scripts /
       tareas programadas).
    2. ``os.getlogin()`` — usuario del sistema operativo.
    3. ``"system"`` — fallback genérico.
    """
    env_actor = os.getenv("FEESDEFENDER_ACTOR")
    if env_actor and env_actor.strip():
        return env_actor.strip()
    try:
        return os.getlogin()
    except (OSError, AttributeError):
        return "system"


def set_actor(actor: str | None) -> None:
    """Fija el actor activo (thread-safe).

    Pasar ``None`` o cadena vacía resetea al default. La UI Streamlit
    llama esta función en cada request con el valor del selector
    "Yo soy: Nikolai / Paola / Ana" (M10-Q3).
    """
    global _actor
    with _actor_lock:
        if isinstance(actor, str) and actor.strip():
            _actor = actor.strip()
        else:
            _actor = None


def get_actor() -> str:
    """Devuelve el actor activo. Si ``set_actor`` no se ha llamado, default."""
    with _actor_lock:
        actor = _actor
    return actor or _default_actor()


# ---------------------------------------------------------------------------
# API pública: escritura y lectura
# ---------------------------------------------------------------------------

def log_path_de(case_dir: Path) -> Path:
    """Ruta del log JSONL **dentro de un arbol de caso ya resuelto**. No crea nada.

    Sustituye a `log_path(case_id)`, que se **retira** en esta fase (Fase 1, B0-1).
    La diferencia no es de estilo: `log_path(case_id)` resolvia siempre por
    `CASOS_ROOT`, asi que con `--case-dir` los documentos iban a la copia local y
    el evento de custodia al canon. Custodia partida en dos.
    """
    return Path(case_dir) / "00_Input" / _LOG_FILENAME


def _resolver_destino(destino: Any, case_id: str | None) -> tuple[Path, str | None]:
    """`(case_dir, case_id)` a partir de un workspace, una ruta o un `case_id`.

    Las tres formas existen a proposito, y solo la tercera es legado:

    - **`CaseWorkspace`** — la via normal. El `case_id` sale de el, asi que no hay
      forma de que el evento diga un caso y los bytes esten en otro.
    - **`Path`** — un arbol ya resuelto (`--case-dir`). El `case_id` lo pasa el
      llamante, que es quien sabe a que expediente pertenece.
    - **`str`** — `legacy_unresolved` (Fase 4): resuelve por el catalogo. Ya no
      puede fabricar un fantasma —`localizar` es estricto desde el Task 6— pero
      sigue sin poder apuntar a una copia local.
    """
    from pathlib import Path as _P

    ws_root = getattr(destino, "working_root", None)
    if ws_root is not None:                                  # CaseWorkspace
        ref = getattr(destino, "case_ref", None)
        return _P(ws_root), (case_id or getattr(ref, "case_id", None)
                             or getattr(ref, "w_code", None))
    if isinstance(destino, _P):
        return destino, case_id
    if isinstance(destino, str):                             # legacy_unresolved
        from core.casos.case_locator import localizar
        return localizar(destino), case_id or destino
    raise TypeError(
        f"destino debe ser CaseWorkspace, Path o case_id; llego {type(destino).__name__}")


def append_event(
    destino: Any,
    event: str,
    *,
    details: dict[str, Any] | None = None,
    actor: str | None = None,
    ts: str | None = None,
    case_id: str | None = None,
) -> Path:
    """Añade una línea al log JSONL del caso (M10).

    El archivo se crea si no existe. Cada llamada hace ``flush + fsync``
    para resistir crashes (M10-Q4).

    Args:
        destino: **Donde estan los bytes.** Un `CaseWorkspace` (la via normal, lo
            que devuelve el resolver), un `Path` al arbol del caso ya resuelto, o
            un `case_id` en el camino legacy (`legacy_unresolved`, Fase 4).
        event: Tipo de evento (debe estar en ``INTAKE_EVENTS``).
        case_id: Solo para el camino `Path`. Con un `CaseWorkspace` sale de el.
        details: Payload específico del evento. Default ``{}``. Debe ser
            JSON-serializable.
        actor: Override explícito del actor. Default ``get_actor()``.
        ts: Override explícito del timestamp ISO-8601. Default ``now_iso()``.

    Returns:
        Path al log.

    Raises:
        ValueError: si ``event`` no está en ``INTAKE_EVENTS``.
        TypeError: si ``details`` no es JSON-serializable.
    """
    if event not in INTAKE_EVENTS:
        raise ValueError(
            f"Evento desconocido: {event!r}. "
            f"Eventos válidos: {sorted(INTAKE_EVENTS)}"
        )

    case_dir, case_id = _resolver_destino(destino, case_id)

    # B0-1: **no** se crea la raiz del caso. Antes habia un
    # `path.parent.mkdir(parents=True, exist_ok=True)` aqui, y eso convertia un
    # `append_event` sobre un W-code mal escrito en una carpeta fantasma con ese
    # nombre en la unidad COMPARTIDA. Crear un expediente es trabajo de la
    # apertura, no de la auditoria.
    entrada_dir = case_dir / "00_Input"
    if not entrada_dir.is_dir():
        from core.casos.workspace_model import LocalWorkspaceMissing
        raise LocalWorkspaceMissing(
            detalle="no hay `00_Input` en el destino: auditar no crea expedientes")

    path = log_path_de(case_dir)

    entry: dict[str, Any] = {
        "ts": ts or now_iso(),
        "actor": actor or get_actor(),
        "event": event,
        "case_id": case_id,
        "details": details or {},
    }
    line = json.dumps(entry, ensure_ascii=False)

    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())

    return path


def read_events(case_id: str) -> list[dict[str, Any]]:
    """Lee y parsea todas las entradas del log del caso.

    Útil para tests y auditoría manual. Sin enforcement de schema sobre los
    eventos leídos — devuelve cada línea como dict tal cual se persistió.
    Las líneas corruptas se saltan silenciosamente (resiliencia a crashes).

    Returns:
        Lista de eventos en orden cronológico (= orden de escritura).
        Lista vacía si el log no existe o está vacío.
    """
    # Resuelve por `buscar`, que devuelve `None` en vez de lanzar. Conserva su firma
    # a proposito: es un LECTOR, no fabrica nada, asi que nunca causo el B0-1 — y
    # cambiarsela tocaria 46 sitios de test sin cerrar ningun defecto.
    #
    # Este comentario decia «`log_path` pasa por `caso_path`» y era **falso desde la
    # migracion**: el modulo ya no importa `caso_path` (R8/H8-09 lo cazo, junto con la
    # importacion muerta que quedaba en la cabecera). Un comentario que describe un
    # acoplamiento retirado es peor que ninguno: hace que la proxima auditoria del
    # fallback busque donde ya no hay nada.
    from core.casos.case_locator import buscar
    case_dir = buscar(case_id)
    if case_dir is None:
        return []                      # el caso no existe
    return read_events_de(case_dir)


def read_events_de(case_dir: Path) -> list[dict[str, Any]]:
    """Lee el log **de un arbol de caso ya resuelto**. Hermano de `log_path_de`.

    Existe porque sin el la migracion quedaba a medias: `append_event` podia
    escribir junto a los bytes, pero recuperarlo exigia pasar por el catalogo. Con
    `--case-dir` —una copia local que el catalogo NO conoce— eso hacia ilegible lo
    que se acababa de escribir.
    """
    path = log_path_de(case_dir)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                out.append(entry)
    return out
