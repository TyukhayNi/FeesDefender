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
    # Recibo de la actuación de apertura (V2). Sin declararlo aquí, la sala de máquina
    # lo inventariaba con hash y extensión JSON **como un documento del expediente del
    # cliente** (R2/H-05). Es protocolo: lo escribe `scripts/abrir_caso.etapa_actuacion`
    # y solo lo lee ella para no crear una segunda actuación al relanzar.
    "_recibo_actuacion.json",
    # JSON de la 1a pasada de viabilidad (`core/viabilidad_json.escribir`, MEJORAS #262).
    # Sin declararlo aquí, una relanzada de `etapa_viabilidad` (que corre en 7a posición,
    # DESPUÉS de `sala_maquina`) hashea el JSON de la corrida anterior y lo inventaría
    # como documento probatorio del cliente: baja a la sala de máquina igual que un PDF
    # del expediente (C2 de la revisión de conjunto, 2026-09-15).
    "_viabilidad.json",
})

#: Temporales de escritura atómica en la raíz, por su prefijo REAL (R1/H-05): un huérfano
#: de `mkstemp`/`os.replace` tampoco es documento. `.apertura_v1.` (`apertura_v1_estado`),
#: `._caso.` (`case_manager`), `._intake_hashes.` (`intake_manifest` y el temporal de
#: `migrar_layout_intake`), `._ocurrencias_crm.json.` (`ocurrencias_crm`),
#: `_viabilidad.json.` (`viabilidad_json.escribir`: `tempfile.mkstemp(prefix=f"{destino.name}.")`
#: sobre `_viabilidad.json` — un huérfano si el proceso muere entre el `os.link` y el
#: `unlink` del temporal, mismo hueco que los otros tres, cubierto aquí igual).
RAIZ_PREFIJOS: tuple[str, ...] = (
    ".apertura_v1.", "._caso.", "._intake_hashes.", "._ocurrencias_crm.json.",
    "_viabilidad.json.",
)

#: Lo que `scripts/migrate_05crm_buckets.py` deja en la raíz: su bitácora
#: (`_migration_05crm_<ts>.json`) y las copias de seguridad de lo que migra
#: (`src.with_suffix(src.suffix + f".bak_{ts}")` sobre `_caso.md` y `_intake_hashes.json`), con
#: `ts = strftime("%Y%m%dT%H%M%S")`. Hasta el 2026-09-26 los apartaba del inventario CLI su
#: lista blanca de extensiones, no este registro, y la sala de máquina —que no tiene lista— los
#: inventariaba como documentos (`MEJORAS #316`).
#:
#: **Nombre entero, no prefijo** (R1/H-10 del #408): un temporal de `mkstemp` lleva un sufijo
#: al azar y solo se puede reconocer por su principio, pero este escritor pone un sello fijo, y
#: con `startswith` un `_caso.md.bak_prueba.pdf` del cliente en la raíz salía del inventario. Se
#: casan con el nombre ya en `casefold()`, como el resto del registro.
RAIZ_PATRONES: tuple[re.Pattern[str], ...] = (
    re.compile(r"_migration_05crm_\d{8}t\d{6}\.json"),
    re.compile(r"_caso\.md\.bak_\d{8}t\d{6}"),
    re.compile(r"_intake_hashes\.json\.bak_\d{8}t\d{6}"),
)

#: Protocolo a profundidad 2, SOLO en el directorio que su escritor usa (R1/H-04): un
#: `_manifiesto.yaml` en `CarpetaRara/` es un documento de fuente manual.
#: Los directorios se casan SIN distinguir mayúsculas (R2/H-03): el disco del despacho es
#: Windows, y si existe `01_drive ev/` el escritor que pide `01_Drive EV/.pulled` escribe
#: DENTRO de aquélla; `rglob` devuelve después la caja almacenada, y con una comparación
#: exacta el marcador que el repo acaba de escribir pasaba por documento. La identidad que
#: importa es la física, no la textual.
ENTREGA: tuple[tuple[re.Pattern[str], str], ...] = (
    (PATRON_LOTE, "_manifiesto.yaml"),                     # intake_lotes.escribir_manifiesto
    (re.compile(r"^01_Drive EV$", re.IGNORECASE), ".pulled"),      # intake_drive
    (re.compile(r"^sudespacho_\d+$", re.IGNORECASE), ".pulled"),   # sync_sudespacho.pull_expediente (legacy)
    (re.compile(r"^drive$", re.IGNORECASE), ".synced"),            # core/sync (pipeline legacy)
    # Estado de canal en su hogar LEGACY (R1/H-02): `email_export` sigue leyéndolo de aquí
    # como fallback en los casos no migrados, y la migración no tiene disparador automático.
    (re.compile(r"^03_Email$", re.IGNORECASE), "_exported_ids.json"),
    (re.compile(r"^03_Email$", re.IGNORECASE), "_resolved_links.json"),
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
    - Profundidad 1: nombre en `RAIZ`, prefijo en `RAIZ_PREFIJOS`, o nombre entero en
      `RAIZ_PATRONES`.
    - Profundidad 2: (directorio, nombre) casa con algún par de `ENTREGA`.
    - Cualquier profundidad: los primeros componentes forman un `DIRECTORIOS` de protocolo.
    - Lo demás: documento.

    Nombres Y directorios se comparan sin distinguir mayúsculas: el disco del despacho es
    Windows, donde `_CASO.MD` es el mismo fichero que `_caso.md` y `01_drive ev/` la misma
    carpeta que `01_Drive EV/` (R2/H-03: la rev. 2 del diseño comparaba el directorio tal como
    lo escribe el repo, y el marcador que el propio repo acababa de escribir en una carpeta
    preexistente con otra caja entraba en el inventario probatorio).
    """
    partes = _partes(rel_path)
    if partes is None:
        return False
    nombre = partes[-1].casefold()
    if len(partes) == 1:
        return (nombre in RAIZ or any(nombre.startswith(pre) for pre in RAIZ_PREFIJOS)
                or any(pat.fullmatch(nombre) for pat in RAIZ_PATRONES))
    partes_cf = [c.casefold() for c in partes]
    for d in DIRECTORIOS:
        dparts = [c.casefold() for c in d.split("/")]
        if len(partes) > len(dparts) and partes_cf[: len(dparts)] == dparts:
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
