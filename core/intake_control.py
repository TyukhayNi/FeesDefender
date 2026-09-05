"""Ficheros de protocolo de `00_Input/`: por dónde están, no por cómo se llaman.

Diseño: `docs/superpowers/specs/2026-09-05-ficheros-de-protocolo-por-ubicacion-design.md`
(rev. 2, `MEJORAS #149`). Hasta el 2026-09-05 el registro era un conjunto de *basenames*
(`config.INTAKE_CONTROL_FILES`) que nueve consumidores aplicaban a cualquier profundidad, y
eso tenía las dos caras del mismo defecto: un adjunto del cliente llamado `_inventory.json`
desaparecía del inventario probatorio, y los cuatro ficheros que el propio repo escribe sin
declararlos salían en la red de calidad como documentos sin soporte. El intento de arreglarlo
declarando más nombres se revirtió el 2026-09-04: la migración borraba un adjunto homónimo.

**La frontera:** el repo escribe cada fichero de protocolo en UNA ubicación que él mismo
fija. Un homónimo en cualquier otro sitio es documento del cliente y se conserva, se
inventaría y se hashea como tal. Este módulo es la única pregunta que los consumidores hacen:
:func:`es_fichero_de_protocolo` sobre la ruta **relativa a `00_Input/`**.

Es un contrato para CLASIFICAR, no para borrar: nada de lo que deriva de aquí autoriza a
borrar un fichero sin demostrar, en el momento de borrarlo y por hash, que es idéntico a otro
que se conserva (`scripts/migrar_layout_intake.py`).

Este módulo no importa nada de `core` a propósito: `core.config` deriva de él el registro por
nombre que se conserva por compatibilidad, y `core.intake_lotes` toma de aquí `PATRON_LOTE`.
"""
from __future__ import annotations

import re

#: Forma de un lote de entrega: `<AAAA-MM-DD>_<fuente>_<NN>` (`MEJORAS #54`). Vive aquí y
#: `core.intake_lotes` lo re-exporta, porque el registro de protocolo lo necesita y
#: `intake_lotes` importa `config`, que importa este módulo.
PATRON_LOTE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})_(whatsapp|email|manual|entrevista)_(\d{2,})$"
)

#: Protocolo en la RAÍZ de `00_Input/`. Escritores: `case_manager` (`_caso.md`),
#: `intake_log`, `intake_manifest`, `inventory`, `email_export` (estado de canal),
#: `apertura_v1_estado`, `ocurrencias_crm`, y el letrado o `crm_colaboradores_firmas`
#: (`_ficha_crm.yaml`, §9 del runbook).
RAIZ: frozenset[str] = frozenset({
    "_caso.md", "_intake_log.jsonl", "_intake_hashes.json", "_inventory.json",
    "_exported_ids.json", "_resolved_links.json", "_apertura_v1.json",
    "_ficha_crm.yaml", "_ocurrencias_crm.json",
})

#: Temporales de escritura atómica en la raíz, por su prefijo REAL (R1/H-05): un huérfano
#: de `mkstemp`/`os.replace` tampoco es documento. `.apertura_v1.` (`apertura_v1_estado`),
#: `._caso.` (`case_manager`), `._intake_hashes.` (`intake_manifest` y el temporal de
#: `migrar_layout_intake`), `._ocurrencias_crm.json.` (`ocurrencias_crm`).
RAIZ_PREFIJOS: tuple[str, ...] = (
    ".apertura_v1.", "._caso.", "._intake_hashes.", "._ocurrencias_crm.json.",
)

#: Protocolo a profundidad 2, SOLO en el directorio que su escritor usa (R1/H-04): un
#: `_manifiesto.yaml` en `CarpetaRara/` es un documento de fuente manual.
ENTREGA: tuple[tuple[re.Pattern[str], str], ...] = (
    (PATRON_LOTE, "_manifiesto.yaml"),                     # intake_lotes.escribir_manifiesto
    (re.compile(r"^01_Drive EV$"), ".pulled"),             # intake_drive
    (re.compile(r"^sudespacho_\d+$"), ".pulled"),          # sync_sudespacho.pull_expediente (legacy)
    (re.compile(r"^drive$"), ".synced"),                   # core/sync (pipeline legacy)
    # Estado de canal en su hogar LEGACY (R1/H-02): `email_export` sigue leyéndolo de aquí
    # como fallback en los casos no migrados, y la migración no tiene disparador automático.
    (re.compile(r"^03_Email$"), "_exported_ids.json"),
    (re.compile(r"^03_Email$"), "_resolved_links.json"),
)

#: Directorios enteros que son producto derivado del repo bajo `00_Input/`, no documental
#: (R1/H-05): `local_organizer` copia ahí documentos de `01_Drive EV/` con otro nombre, y la
#: sala de máquina los procesaba dos veces.
DIRECTORIOS: tuple[str, ...] = ("01_Drive EV/_organizado",)

_DRIVE_WINDOWS = re.compile(r"^[A-Za-z]:")


def _partes(rel_path: str) -> list[str] | None:
    """Componentes de `rel_path` normalizado, o None si no es una ruta relativa sana."""
    if not rel_path:
        return None
    p = rel_path.replace("\\", "/")
    if p.startswith("/") or _DRIVE_WINDOWS.match(p):
        return None
    partes = [c for c in p.split("/") if c not in ("", ".")]
    if not partes or ".." in partes:
        return None
    return partes


def es_fichero_de_protocolo(rel_path: str) -> bool:
    """`rel_path` relativo a `00_Input/`, con `/` o `\\`.

    - Absoluta, vacía o con `..`: False (un documento en un sitio raro se inventaría, no se
      esconde).
    - Profundidad 1: nombre en `RAIZ`, o prefijo en `RAIZ_PREFIJOS`.
    - Profundidad 2: (directorio, nombre) casa con algún par de `ENTREGA`.
    - Cualquier profundidad: los primeros componentes forman un `DIRECTORIOS` de protocolo.
    - Lo demás: documento.

    Los nombres se comparan sin distinguir mayúsculas (el disco del despacho es Windows y
    `_CASO.MD` es el mismo fichero que `_caso.md`); los directorios, tal como los escribe el
    repo.
    """
    partes = _partes(rel_path)
    if partes is None:
        return False
    nombre = partes[-1].casefold()
    if len(partes) == 1:
        return nombre in RAIZ or any(nombre.startswith(pre) for pre in RAIZ_PREFIJOS)
    for d in DIRECTORIOS:
        dparts = d.split("/")
        if len(partes) > len(dparts) and partes[: len(dparts)] == dparts:
            return True
    if len(partes) == 2:
        directorio = partes[0]
        return any(pat.match(directorio) and nombre == n for pat, n in ENTREGA)
    return False


def nombres_registrados() -> frozenset[str]:
    """Los basenames que aparecen en el registro (`RAIZ` ∪ nombres de `ENTREGA`). Existe
    para que `config.INTAKE_CONTROL_FILES` siga siendo un dato derivado y no una segunda
    lista; **no clasifica nada**: la pregunta es :func:`es_fichero_de_protocolo`."""
    return RAIZ | frozenset(n for _, n in ENTREGA)
