"""Cerebro PURO del sistema de biblioteca (Merge Desktop→Drive + checkout).

Lógica determinista y sin I/O: validación de transiciones de estado, cálculo
del plan de merge de 3 vías (tabla canónica de 9 casos, DISEÑO_V2 §4.1),
guard de escritura del pipeline (§6) y constructores de eventos para
``_intake_log.jsonl``.

**CERO I/O contra Drive.** Este módulo no conoce rclone, ni conectores, ni el
sistema de ficheros: recibe inventarios (datos) y devuelve acciones (datos).
El movimiento de bytes y la lectura/escritura del lock los hace el frontal
(``scripts/repository_cli.py`` con rclone, o las skills de Cowork). Así la
arquitectura de 3 capas se respeta (capa Core = decide; frontal = ejecuta) y
el algoritmo central es testeable como función pura.

Arquitectura: cerebro (aquí) / músculo (rclone) / frontales (CLI, skills).
Definiciones (estados, exclusiones, derivados): ``core.config`` (SSOT).

Vocabulario de inventario
-------------------------
Un *inventario* es un ``dict[str, Entrada]`` indexado por **ruta relativa** al
caso (separador ``/``). Cada ``Entrada`` es un ``dict`` ``{"hash": str|None,
"size": int}``. ``hash is None`` marca un fichero **Google-native** (Docs/Sheets
sin MD5): no se puede comparar por hash → se preserva siempre.

- ``L`` = inventario local (copia de trabajo, ahora).
- ``D`` = inventario del Drive (ahora, leído por API).
- ``B`` = baseline del checkout (``MANIFEST_CHECKOUT.json``).
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import PurePosixPath
from typing import Any

from .config import (
    DERIVADOS_REGENERABLES,
    ESTADO_REPO_DEFAULT,
    ESTADO_REPO_DISPONIBLE,
    ESTADO_REPO_PRESTADO,
    MERGE_EXCLUSIONS,
    PENDIENTE_CHECKIN_SUBDIR,
    TRANSICIONES_PERMITIDAS,
)

# ---------------------------------------------------------------------------
# Acciones del plan de merge (constantes)
# ---------------------------------------------------------------------------

ACCION_SKIP = "SKIP"                     # sin cambios
ACCION_COPY_LOCAL = "COPY_LOCAL"         # local → Drive
ACCION_PRESERVE_DRIVE = "PRESERVE_DRIVE"  # dejar Drive como está
ACCION_CONFLICT = "CONFLICT"             # divergencia real, decisión manual
ACCION_DELETE_DRIVE = "DELETE_DRIVE"     # borrar en Drive (a papelera, con confirmación)
ACCION_RENAME = "RENAME"                 # renombrado detectado por hash: mover, no duplicar

# Acciones que mutan el Drive (útil para el frontal y para el resumen del plan).
ACCIONES_MUTAN_DRIVE: frozenset[str] = frozenset({
    ACCION_COPY_LOCAL,
    ACCION_DELETE_DRIVE,
    ACCION_RENAME,
})


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class TransicionInvalida(ValueError):
    """Transición de estado del repositorio no permitida (DISEÑO_V2 §2)."""


# ---------------------------------------------------------------------------
# 1. Máquina de estados
# ---------------------------------------------------------------------------

def validar_transicion(origen: str, destino: str) -> None:
    """Valida una transición de estado del repositorio.

    Lanza :class:`TransicionInvalida` si ``origen`` no es un estado conocido o
    si ``destino`` no está entre las transiciones permitidas desde ``origen``
    (``TRANSICIONES_PERMITIDAS``, SSOT en ``config``). No devuelve nada cuando
    la transición es legal.

    Las *condiciones adjuntas* (checkin verificado, cancelación con
    confirmación explícita, resolución registrada en ``CONFLICTOS_RESUELTOS.md``)
    NO las comprueba esta función: son responsabilidad del frontal/CLI. Aquí
    solo vive la tabla.
    """
    permitidos = TRANSICIONES_PERMITIDAS.get(origen)
    if permitidos is None:
        raise TransicionInvalida(
            f"Estado de repositorio desconocido: {origen!r}. "
            f"Estados válidos: {sorted(TRANSICIONES_PERMITIDAS)}"
        )
    if destino not in permitidos:
        raise TransicionInvalida(
            f"Transición no permitida: {origen!r} → {destino!r}. "
            f"Desde {origen!r} solo se permite: {permitidos}"
        )


# ---------------------------------------------------------------------------
# Mutadores PUROS del lock (frontmatter → frontmatter)
# ---------------------------------------------------------------------------
#
# Fuente ÚNICA de la mutación del lock, compartida por:
#   - `case_manager` (aplica sobre el `_caso.md` del árbol local vía
#     `_atomic_write_caso_md`);
#   - el frontal CLI (aplica sobre el `_caso.md` del Drive: pull → mutar → push).
# No hacen I/O ni validan la transición (eso lo hace el caller con
# `validar_transicion`): solo escriben campos en `fm["meta"]`.

# Campos del lock con su valor por defecto (subconjunto de CaseMeta §2.3).
LOCK_FIELDS: dict[str, Any] = {
    "estado_repositorio": ESTADO_REPO_DEFAULT,
    "checkout_user": None,
    "checkout_timestamp": None,
    "checkout_nonce": None,
    "checkout_maquina": None,
    "checkout_notas": None,
    "ultimo_checkin_timestamp": None,
    "ultimo_checkin_auditlog": None,
}


def _meta_de(fm: dict[str, Any]) -> dict[str, Any]:
    """Devuelve `fm["meta"]` creándolo si falta (mutación in-place)."""
    meta = fm.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        fm["meta"] = meta
    return meta


def estado_de_fm(fm: dict[str, Any]) -> str:
    """Estado del lock leído del frontmatter. `"disponible"` por defecto."""
    if not isinstance(fm, dict):
        return ESTADO_REPO_DEFAULT
    meta = fm.get("meta")
    if not isinstance(meta, dict):
        return ESTADO_REPO_DEFAULT
    return meta.get("estado_repositorio") or ESTADO_REPO_DEFAULT


def leer_lock_de_fm(fm: dict[str, Any]) -> dict[str, Any]:
    """Devuelve los campos del lock con defaults (nunca lanza)."""
    meta = fm.get("meta") if isinstance(fm, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    lock = dict(LOCK_FIELDS)
    for k in lock:
        if meta.get(k) is not None:
            lock[k] = meta[k]
    if not lock["estado_repositorio"]:
        lock["estado_repositorio"] = ESTADO_REPO_DEFAULT
    return lock


def aplicar_lock_prestado(
    fm: dict[str, Any],
    *,
    user: str,
    timestamp: str,
    nonce: str,
    maquina: str | None = None,
    notas: str | None = None,
) -> dict[str, Any]:
    """Escribe el lock de checkout (estado `prestado` + campos `checkout_*`).

    NO escribe la ruta local (§2.2): solo el hostname en `checkout_maquina`.
    El caller valida la transición antes de llamar.
    """
    meta = _meta_de(fm)
    meta["estado_repositorio"] = ESTADO_REPO_PRESTADO
    meta["checkout_user"] = user
    meta["checkout_timestamp"] = timestamp
    meta["checkout_nonce"] = nonce
    meta["checkout_maquina"] = maquina
    meta["checkout_notas"] = notas
    return fm


def aplicar_lock_liberado(
    fm: dict[str, Any],
    *,
    timestamp: str,
    auditlog: str | None = None,
) -> dict[str, Any]:
    """Libera el lock (estado `disponible`, limpia `checkout_*`, marca checkin)."""
    meta = _meta_de(fm)
    meta["estado_repositorio"] = ESTADO_REPO_DISPONIBLE
    meta["checkout_user"] = None
    meta["checkout_timestamp"] = None
    meta["checkout_nonce"] = None
    meta["checkout_maquina"] = None
    meta["checkout_notas"] = None
    meta["ultimo_checkin_timestamp"] = timestamp
    if auditlog is not None:
        meta["ultimo_checkin_auditlog"] = auditlog
    return fm


def aplicar_lock_cancelado(fm: dict[str, Any]) -> dict[str, Any]:
    """Cancela el checkout (estado `disponible`, limpia `checkout_*`) sin checkin."""
    meta = _meta_de(fm)
    meta["estado_repositorio"] = ESTADO_REPO_DISPONIBLE
    for k in ("checkout_user", "checkout_timestamp", "checkout_nonce",
              "checkout_maquina", "checkout_notas"):
        meta[k] = None
    return fm


def aplicar_estado(fm: dict[str, Any], estado: str) -> dict[str, Any]:
    """Fija `estado_repositorio` sin tocar el resto (p. ej. `→ conflicto`)."""
    _meta_de(fm)["estado_repositorio"] = estado
    return fm


def verificar_nonce(fm_drive: dict[str, Any], nonce_propio: str) -> bool:
    """Confirma que el nonce ganador del lock del Drive es el propio (§2.2).

    Tras escribir el lock y esperar el sync lag, el frontal relee ``_caso.md``
    del Drive (por API) y llama aquí con el frontmatter parseado. Devuelve
    ``True`` solo si ``meta.checkout_nonce`` coincide con ``nonce_propio``. Si
    otro usuario ganó la carrera, devuelve ``False`` y el frontal aborta limpio.
    """
    meta = fm_drive.get("meta") if isinstance(fm_drive, dict) else None
    if not isinstance(meta, dict):
        return False
    return meta.get("checkout_nonce") == nonce_propio


# ---------------------------------------------------------------------------
# 2. Exclusiones del merge (§5)
# ---------------------------------------------------------------------------

def _norm(relpath: str) -> str:
    """Normaliza a separador POSIX y sin barra inicial."""
    return relpath.replace("\\", "/").lstrip("/")


def esta_excluido(relpath: str) -> bool:
    """True si la ruta la gestiona el protocolo, no el sync (``MERGE_EXCLUSIONS``).

    Semántica de patrones (estilo rclone ``--exclude``):
    - Patrón sin ``/``: casa por **basename** en cualquier nivel del árbol
      (así ``_caso.md`` casa ``00_Input/_caso.md``).
    - Patrón ``dir/**``: casa cualquier ruta bajo ``dir/`` (y el propio ``dir``).
    - Otro patrón con ``/``: fnmatch sobre la ruta completa.
    """
    rp = _norm(relpath)
    base = rp.rsplit("/", 1)[-1]
    for pat in MERGE_EXCLUSIONS:
        if "/" not in pat:
            if fnmatch(base, pat):
                return True
        elif pat.endswith("/**"):
            prefijo = pat[:-3]  # "dir/"
            if rp == prefijo.rstrip("/") or rp.startswith(prefijo):
                return True
        elif fnmatch(rp, pat):
            return True
    return False


def _es_derivado(relpath: str) -> bool:
    return _norm(relpath).rsplit("/", 1)[-1] in DERIVADOS_REGENERABLES


# ---------------------------------------------------------------------------
# 3. Plan de merge de 3 vías (§4.1 + §4.2)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AccionMerge:
    """Una acción del plan de merge sobre un fichero (ruta relativa al caso)."""
    ruta: str
    accion: str
    motivo: str
    caso_tabla: int | None = None      # 1..9 de la tabla canónica (§4.1); None para §4.2/9-native
    ruta_origen: str | None = None     # RENAME: ruta antigua en Drive a mover
    google_native: bool = False        # True si es Docs/Sheets sin MD5


def _hash(entrada: dict[str, Any] | None) -> str | None:
    return entrada.get("hash") if entrada else None


def plan_merge(
    local: dict[str, dict[str, Any]],
    drive: dict[str, dict[str, Any]],
    base: dict[str, dict[str, Any]],
) -> list[AccionMerge]:
    """Calcula el plan de merge de 3 vías (entrada: 3 inventarios; salida: acciones).

    Función PURA y determinista: mismos inventarios → mismo plan. Aplica la
    tabla canónica de 9 casos (§4.1), la excepción de derivados regenerables
    (§4.2), la regla de Google-native (preservar) y la detección de renombrados
    por hash (caso 9). Omite los ficheros de ``MERGE_EXCLUSIONS`` (§5): los
    gestiona el protocolo.

    Idempotencia (§4.4): tras aplicar el plan, re-ejecutar con el mismo baseline
    converge a SKIP (la comparación por hash hace que lo ya hecho se salte).

    Los ``SKIP`` no se incluyen en el plan (ruido): el frontal solo actúa sobre
    lo que aparece. Un fichero sin acción = SKIP implícito.

    Returns:
        Lista de :class:`AccionMerge` en orden estable (por ruta), sin SKIP.
    """
    acciones: list[AccionMerge] = []

    # Índice hash→rutas del Drive, para detectar renombrados (caso 9).
    drive_por_hash: dict[str, list[str]] = {}
    for ruta, ent in drive.items():
        h = _hash(ent)
        if h is not None:
            drive_por_hash.setdefault(h, []).append(ruta)

    # -- Pre-pasada de renombrados (caso 9). Debe ir ANTES del bucle general:
    #    si no, la ruta ANTIGUA (que ordena antes) se emitiría como DELETE_DRIVE
    #    antes de que la ruta nueva la reclame. Un renombrado local aparece como
    #    "nuevo en local" (no en base, no en Drive) cuyo hash existe en Drive bajo
    #    OTRA ruta huérfana (no en local). Mover en Drive, no duplicar.
    consumidas_por_rename: set[str] = set()   # rutas Drive origen del rename
    emitidas_como_rename: set[str] = set()     # rutas local destino ya emitidas
    for ruta in sorted(local):
        if esta_excluido(ruta):
            continue
        if ruta in base or ruta in drive:
            continue
        hL = _hash(local[ruta])
        if hL is None:
            continue
        candidatos = [
            r for r in drive_por_hash.get(hL, [])
            if r != ruta and r not in local and r not in consumidas_por_rename
        ]
        if candidatos:
            origen = sorted(candidatos)[0]
            consumidas_por_rename.add(origen)
            emitidas_como_rename.add(ruta)
            acciones.append(AccionMerge(
                ruta=ruta, accion=ACCION_RENAME,
                motivo=f"Renombrado detectado por hash (antes {origen!r})",
                caso_tabla=9, ruta_origen=origen,
            ))

    todas = sorted(set(local) | set(drive) | set(base))

    for ruta in todas:
        if esta_excluido(ruta):
            continue
        if ruta in consumidas_por_rename or ruta in emitidas_como_rename:
            continue

        L, D, B = local.get(ruta), drive.get(ruta), base.get(ruta)
        hL, hD, hB = _hash(L), _hash(D), _hash(B)

        # -- Google-native en Drive: sin MD5, no se puede mergear → preservar.
        if D is not None and hD is None:
            acciones.append(AccionMerge(
                ruta=ruta, accion=ACCION_PRESERVE_DRIVE,
                motivo="Google-native (sin MD5): se preserva la versión Drive",
                google_native=True,
            ))
            continue

        # -- Derivados regenerables (§4.2): local gana salvo que Drive cambiara.
        if _es_derivado(ruta) and L is not None:
            if D is None:
                acciones.append(AccionMerge(
                    ruta=ruta, accion=ACCION_COPY_LOCAL,
                    motivo="Derivado regenerable: local gana (no existe en Drive)",
                ))
            elif B is not None and hD == hB:
                acciones.append(AccionMerge(
                    ruta=ruta, accion=ACCION_COPY_LOCAL,
                    motivo="Derivado regenerable: local gana (Drive intacto)",
                ))
            elif hL == hD:
                pass  # ya idénticos → SKIP implícito
            else:
                acciones.append(AccionMerge(
                    ruta=ruta, accion=ACCION_CONFLICT,
                    motivo="Derivado regenerable pero Drive cambió durante el préstamo",
                ))
            continue

        # -- Tabla general de 3 vías (§4.1).
        accion = _decidir_tabla_general(ruta, L, D, B, hL, hD, hB)
        if accion is not None:
            acciones.append(accion)

    acciones.sort(key=lambda a: a.ruta)
    return acciones


def _decidir_tabla_general(
    ruta: str,
    L: dict | None, D: dict | None, B: dict | None,
    hL: str | None, hD: str | None, hB: str | None,
) -> AccionMerge | None:
    """Aplica la tabla canónica de 9 casos a un fichero. Devuelve None para SKIP."""
    presente_L, presente_D, presente_B = L is not None, D is not None, B is not None

    # Ambos presentes, con baseline.
    if presente_L and presente_D and presente_B:
        cambio_L = hL != hB
        cambio_D = hD != hB
        if not cambio_L and not cambio_D:
            return None  # caso 1: SKIP
        if cambio_L and not cambio_D:
            return AccionMerge(ruta, ACCION_COPY_LOCAL, "Solo cambió local", caso_tabla=2)
        if not cambio_L and cambio_D:
            return AccionMerge(ruta, ACCION_PRESERVE_DRIVE, "Solo cambió Drive (Marta/pipeline)", caso_tabla=3)
        # ambos cambiaron
        if hL == hD:
            return None  # convergieron al mismo contenido → SKIP (anti-fatiga, §4.4)
        return AccionMerge(ruta, ACCION_CONFLICT, "Divergencia real: ambos lados cambiaron", caso_tabla=4)

    # Ambos presentes, sin baseline (nuevos en los dos lados).
    if presente_L and presente_D and not presente_B:
        if hL == hD:
            return None  # mismo fichero añadido en ambos → SKIP
        return AccionMerge(ruta, ACCION_CONFLICT, "Creado distinto en local y en Drive", caso_tabla=4)

    # Solo local, con baseline: Drive lo borró durante el préstamo.
    if presente_L and not presente_D and presente_B:
        return AccionMerge(
            ruta, ACCION_CONFLICT,
            "Drive borró un fichero que sigue en local: decisión manual", caso_tabla=6,
        )

    # Solo local, sin baseline: nuevo en local (caso 7). El renombrado ya se
    # descartó antes; aquí es un alta genuina.
    if presente_L and not presente_D and not presente_B:
        return AccionMerge(ruta, ACCION_COPY_LOCAL, "Fichero nuevo en local", caso_tabla=7)

    # Ausente en local, con baseline (borrado local).
    if not presente_L and presente_B:
        if presente_D:
            if hD == hB:
                return AccionMerge(ruta, ACCION_DELETE_DRIVE, "Borrado en local; Drive intacto (confirmación)", caso_tabla=5)
            return AccionMerge(ruta, ACCION_CONFLICT, "Borraste algo que Drive cambió", caso_tabla=6)
        return None  # borrado en ambos lados → SKIP

    # Ausente en local, sin baseline, presente en Drive: nuevo en Drive (caso 8).
    if not presente_L and presente_D and not presente_B:
        return AccionMerge(ruta, ACCION_PRESERVE_DRIVE, "Nuevo en Drive durante el préstamo", caso_tabla=8)

    return None


def resumen_plan(plan: list[AccionMerge]) -> dict[str, int]:
    """Cuenta acciones por tipo (para el DELTA/reporte y el evento de checkin)."""
    resumen = {
        ACCION_COPY_LOCAL: 0,
        ACCION_PRESERVE_DRIVE: 0,
        ACCION_CONFLICT: 0,
        ACCION_DELETE_DRIVE: 0,
        ACCION_RENAME: 0,
    }
    for a in plan:
        if a.accion in resumen:
            resumen[a.accion] += 1
    return resumen


# ---------------------------------------------------------------------------
# 4. Guard de escritura del pipeline (§6)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionEscritura:
    """Decisión del guard para una escritura al caso en Drive (DISEÑO_V2 §6)."""
    permitido: bool               # True → escribir en la ruta normal
    desviar: bool                 # True → escribir en la bandeja _pendiente_checkin
    ruta_bandeja: str | None      # ruta relativa dentro del caso (si desviar)
    evento: str | None            # evento de _intake_log.jsonl a emitir (si desviar)
    motivo: str


def decidir_escritura(
    estado: str,
    ruta_relativa: str,
    origen: str,
    *,
    es_protocolo: bool = False,
) -> DecisionEscritura:
    """Decide si una escritura al caso en Drive procede o se desvía a la bandeja.

    Regla (§6): si el caso está ``prestado`` o en ``conflicto``, toda escritura
    del pipeline/UI/intake se desvía a ``_pendiente_checkin/<origen>/<ruta>`` con
    un evento ``pendiente_checkin`` en el log; nadie se bloquea, nada se pierde.
    El propio PROTOCOLO (lock, log, bandeja) está EXENTO (``es_protocolo=True``).

    Args:
        estado: estado_repositorio vigente del caso (leído de ``_caso.md`` Drive).
        ruta_relativa: ruta destino relativa al caso (separador ``/``).
        origen: fuente de la escritura (``"intake"``, ``"email"``, ``"crm"``,
            ``"pipeline"``…). Da nombre a la subcarpeta de la bandeja.
        es_protocolo: True si la escritura es del propio protocolo (exenta).

    Returns:
        :class:`DecisionEscritura`.
    """
    if es_protocolo or estado == ESTADO_REPO_DISPONIBLE:
        return DecisionEscritura(
            permitido=True, desviar=False, ruta_bandeja=None, evento=None,
            motivo="protocolo exento" if es_protocolo else "caso disponible",
        )
    # prestado o conflicto (o cualquier estado no-disponible): desviar.
    rp = _norm(ruta_relativa)
    ruta_bandeja = str(PurePosixPath(PENDIENTE_CHECKIN_SUBDIR) / origen / rp)
    return DecisionEscritura(
        permitido=False, desviar=True, ruta_bandeja=ruta_bandeja,
        evento="pendiente_checkin",
        motivo=f"caso {estado}: escritura desviada a la bandeja",
    )


# ---------------------------------------------------------------------------
# 5. Constructores de eventos para _intake_log.jsonl
# ---------------------------------------------------------------------------

def evento_checkout_details(
    *,
    user: str,
    timestamp: str,
    nonce: str,
    maquina: str | None,
    ruta_local: str,
    n_ficheros: int,
    manifest_hash: str,
) -> dict[str, Any]:
    """Payload ``details`` del evento ``case_checkout`` (§3).

    La ruta local COMPLETA vive aquí (log forense), no en ``_caso.md`` (visible
    para E&V) — DISEÑO_V2 §2.2 / gobernanza §3.
    """
    return {
        "user": user,
        "checkout_timestamp": timestamp,
        "checkout_nonce": nonce,
        "checkout_maquina": maquina,
        "ruta_local": ruta_local,
        "n_ficheros": n_ficheros,
        "manifest_hash": manifest_hash,
    }


def evento_checkin_details(
    *,
    user: str,
    timestamp: str,
    copiados: int,
    preservados: int,
    borrados: int,
    conflictos: int,
    renombrados: int,
    resultado: str,
    auditlog: str,
) -> dict[str, Any]:
    """Payload ``details`` del evento ``case_checkin`` (resumen del plan, §4)."""
    return {
        "user": user,
        "checkin_timestamp": timestamp,
        "copiados": copiados,
        "preservados": preservados,
        "borrados": borrados,
        "conflictos": conflictos,
        "renombrados": renombrados,
        "resultado": resultado,
        "auditlog": auditlog,
    }


def evento_pendiente_details(
    *,
    origen: str,
    ruta_bandeja: str,
    ruta_original: str,
) -> dict[str, Any]:
    """Payload ``details`` del evento ``pendiente_checkin`` (guard, §6)."""
    return {
        "origen": origen,
        "ruta_bandeja": ruta_bandeja,
        "ruta_original": ruta_original,
    }
