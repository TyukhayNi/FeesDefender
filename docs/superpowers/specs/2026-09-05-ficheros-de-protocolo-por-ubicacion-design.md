---
tipo: spec
estado: en-revision
creado: 2026-09-05
objeto: "MEJORAS #149 — los ficheros de protocolo se identifican por nombre a cualquier profundidad; el contrato es por ubicación"
rev: "2"
---

# Ficheros de protocolo: por dónde están, no por cómo se llaman

> **Rev. 2 (2026-09-05), tras la R1 adversarial sobre la rev. 1: `REQUIERE-REVISION`, once
> hallazgos, los once confirmados.** Tres ALTOS: la comparación por hash estaba en el plan y el
> borrado se decide en la fase 1 y se ejecuta en la fase 2 sin releer (H-01, con sonda que
> reproduce la pérdida); el registro dejaba fuera la ubicación **legacy** del estado de canal
> (`03_Email/_exported_ids.json`) y reintroducía el síntoma de `#149` en los casos no migrados
> (H-02); y «ningún consumidor» era falso porque `scripts/abrir_caso.py` sigue clasificando por
> basename recursivo (H-03). Lo que cambia: el registro pasa a **pares (directorio, nombre)** con
> los cajones legacy dentro (§3.1), la migración comprueba por hash **dos veces** y nunca borra
> lo que no acaba de comparar (§3.4), los consumidores son nueve y los alias por basename se
> retiran (§3.3), y el §5 declara qué tests cambian de expectativa. Adjudicación en el **§8**;
> voz del revisor, literal, en el acta hermana `…-r1-adversarial-review.md`.
>
> **Rev. 1 (2026-09-05).** Diseño para cerrar `MEJORAS #149` **sin repetir el 2026-09-04**: aquel
> día se declararon cuatro nombres más en `INTAKE_CONTROL_FILES` y la R1 adversarial lo tumbó con
> un CRÍTICO (una migración que borra un adjunto legítimo homónimo) y dos ALTOS; se revirtió
> entero (`4cd71dd`). La causa estaba escrita en la propia entrada: **el contrato es por ubicación,
> no por nombre**. Origen inmediato: acción 7 del informe de Codex «Acciones para mejorar el alta
> de expedientes» (2026-09-05, fuera del repo).

## 1. El problema, medido

`core/config.INTAKE_CONTROL_FILES` es un **conjunto de basenames** (`.pulled`, `.synced`,
`_inventory.json`, `_exported_ids.json`, `_resolved_links.json`, `_apertura_v1.json`) y **nueve**
consumidores lo aplican a cualquier profundidad de `00_Input/` (siete en la rev. 1; la R1 añadió
los dos de `scripts/abrir_caso.py`):

| Consumidor | Cómo excluye | Efecto medido o demostrado |
|---|---|---|
| `core/inventory.scan` | `path.name in _CONTROL_FILES` y `path.name.startswith("_caso")`, sobre `rglob` | un adjunto llamado `_inventory.json` en un lote desaparece del inventario |
| `core/intake_manual.list_files` (y `list_crm_branch_files`, donde el filtro es un no-op a profundidad ≥ 3) | `p.name not in _CONTROL_FILES` | ídem |
| `core/intake_drive._count_files` (no recursivo: solo la raíz de `01_Drive EV/`) | `p.name not in CONTROL_FILES` | recuento del pull |
| `core/intake_lotes.items_desde_disco` | `p.name in INTAKE_CONTROL_FILES or p.name == MANIFIESTO_LOTE`, sobre `rglob` | **R1 2026-09-04, ALTO:** un adjunto `_manifiesto.yaml` anidado desaparece del albarán forense del lote |
| `core/email_export.export_label` | igual, para decidir si el lote quedó vacío | ídem |
| `core/sala_maquina._es_control(nombre)` | nombre ∈ registro ∪ `{_intake_log.jsonl}` o prefijo `.apertura_v1.` | la asimetría de `#149`: lo **declarado** se excluye bien y lo **no declarado** entra en `_cobertura` como `sin_soporte` (`_intake_hashes.json`, `<lote>/_manifiesto.yaml`, medido en W-02JSVZ) |
| `scripts/abrir_caso.hash_tree_local` | `p.name in intake_drive.CONTROL_FILES`, sobre `rglob` de `01_Drive EV/` | alimenta el ledger forense del evento `pull_drive_ev`: un adjunto homónimo queda fuera del hash-ledger |
| `scripts/abrir_caso.etapa_drive` (recuento V1) | mismo filtro recursivo | el informe de la etapa |
| `scripts/migrar_layout_intake` | `hijo.name in INTAKE_CONTROL_FILES` bajo `03_Email/` → mover a la raíz; si ya hay uno, **`unlink()` sin comparar bytes** | **R1 2026-09-04, CRÍTICO:** con `_ficha_crm.yaml` declarado, un adjunto legítimo así llamado se trata como estado de canal y se **borra**; **ALTO:** el homónimo anidado se mueve fuera del `mapping` M9 y sus referencias forenses quedan rancias |

Y el lado contrario del mismo defecto: cuatro ficheros que **el propio repo escribe** en `00_Input/`
no están en el registro y salen en la red de calidad como documentos sin soporte:

| Fichero | Quién lo escribe | Dónde |
|---|---|---|
| `_intake_hashes.json` | `core/intake_manifest` | `00_Input/` |
| `_manifiesto.yaml` | `core/intake_lotes` (vía `email_export`, `whatsapp_intake`, `intake_manual`, `migrar_layout_intake`) | raíz de **cada lote** |
| `_ficha_crm.yaml` | a mano (§9 del runbook) y `scripts/crm_colaboradores_firmas.py` | `00_Input/` |
| `_ocurrencias_crm.json` | `core/ocurrencias_crm` (`REGISTRO_REL = "00_Input/_ocurrencias_crm.json"`) | `00_Input/` |

Declararlos por nombre reproduce el CRÍTICO. No declararlos deja la red de calidad con ruido en el
sitio exacto donde se mira lo que el OCR no pudo leer.

## 2. La frontera

**Un fichero es de protocolo por dónde está, no por cómo se llama.** El repo escribe cada uno en
una ubicación que él mismo fija; un homónimo en cualquier otro sitio es un documento del cliente y
se conserva, se inventaría y se hashea como tal. El registro pasa de «nombres» a **«nombre en
directorio»**, y los consumidores dejan de preguntar por el basename para preguntar por la ruta
relativa a `00_Input/`.

Y es un contrato **para clasificar**, no para borrar: nada de lo que esta pieza toca borra un
fichero sin haber demostrado **en el momento de borrarlo**, por hash, que es idéntico a otro que
se conserva (R1/H-01: comprobarlo antes, en el plan, no basta).

## 3. Diseño

### 3.1. El registro, por pares (directorio, nombre) — `core/intake_control.py`

```python
#: Protocolo en la RAÍZ de `00_Input/`. Escritores: case_manager, intake_log, intake_manifest,
#: inventory, email_export (estado de canal), apertura_v1_estado, ocurrencias_crm, y el letrado
#: o `crm_colaboradores_firmas` (`_ficha_crm.yaml`).
RAIZ: frozenset[str] = frozenset({
    "_caso.md", "_intake_log.jsonl", "_intake_hashes.json", "_inventory.json",
    "_exported_ids.json", "_resolved_links.json", "_apertura_v1.json",
    "_ficha_crm.yaml", "_ocurrencias_crm.json",
})
#: Temporales de escritura atómica en la raíz, por su prefijo real (R1/H-05): un huérfano
#: tampoco es documento. `_caso` (case_manager), `apertura_v1` (apertura_v1_estado),
#: `_intake_hashes` (intake_manifest), `_ocurrencias_crm.json` (ocurrencias_crm).
RAIZ_PREFIJOS: tuple[str, ...] = (".apertura_v1.", "._caso.", "._intake_hashes.",
                                  "._ocurrencias_crm.json.")
#: Protocolo a profundidad 2, SOLO en el directorio que su escritor usa (R1/H-04): un
#: `_manifiesto.yaml` en `CarpetaRara/` es un documento de fuente manual.
ENTREGA: tuple[tuple[re.Pattern, str], ...] = (
    (PATRON_LOTE,                 "_manifiesto.yaml"),     # intake_lotes.escribir_manifiesto
    (re.compile(r"^01_Drive EV$"), ".pulled"),             # intake_drive
    (re.compile(r"^sudespacho_\d+$"), ".pulled"),          # sync_sudespacho.pull_expediente (legacy)
    (re.compile(r"^drive$"),       ".synced"),             # core/sync (pipeline legacy)
    # Estado de canal en su hogar LEGACY (R1/H-02): `email_export` sigue leyéndolo de aquí
    # como fallback en los casos no migrados, y la migración no tiene disparador automático.
    (re.compile(r"^03_Email$"),    "_exported_ids.json"),
    (re.compile(r"^03_Email$"),    "_resolved_links.json"),
)
#: Directorios enteros que son producto derivado del repo bajo `00_Input/`, no documental
#: (R1/H-05): `local_organizer` copia ahí documentos de `01_Drive EV/` con otro nombre, y
#: la sala de máquina los procesaba dos veces.
DIRECTORIOS: tuple[str, ...] = ("01_Drive EV/_organizado",)
```

`config.INTAKE_CONTROL_FILES` **se conserva derivado** (unión de los nombres de `RAIZ` y
`ENTREGA`) **y no clasifica nada**: su comentario lo dice y un test comprueba con `git grep` que
sus únicos lectores son los que el §3.3 deja (R1/H-07). La rev. 1 decía que lo «espejan»
`MERGE_EXCLUSIONS` y el plugin, y es falso: `MERGE_EXCLUSIONS` es un contrato del checkin que
**deliberadamente** no excluye `_intake_hashes.json` ni `_ocurrencias_crm.json` (viajan en
`GRUPOS_MERGE`); el único espejo con guard es `apertura_v1_estado.FICHEROS_CONTROL` ⊂
`MERGE_EXCLUSIONS` ∩ `PROTOCOL_EDIT`. Nadie debe «arreglar» ese espejo añadiendo nombres.

Los tres alias por basename —`intake_drive.CONTROL_FILES`, `inventory._CONTROL_FILES`,
`intake_manual._CONTROL_FILES`— **se retiran**: un registro por nombre que sobrevive «para los
guards» es el proxy que causó la reversión del 2026-09-04 con otro nombre.

### 3.2. Una sola pregunta: `es_fichero_de_protocolo(rel_path)`

```python
def es_fichero_de_protocolo(rel_path: str) -> bool:
    """`rel_path` relativo a `00_Input/`, con `/` o `\\`.
    - Absoluta, vacía o con `..`: False (un documento en un sitio raro se inventaría, no se esconde).
    - Profundidad 1: nombre en RAIZ, o prefijo en RAIZ_PREFIJOS.
    - Profundidad 2: (directorio, nombre) casa con algún par de ENTREGA.
    - Cualquier profundidad: el primer o los dos primeros componentes forman un DIRECTORIO
      de protocolo (`01_Drive EV/_organizado/...`).
    - Lo demás: documento."""
```

Lo que **no** es protocolo, a propósito: un fichero de la raíz con `_` inicial que no esté en
`RAIZ` (`00_Input/_nota_suelta.pdf` es documental de fuente `manual`: `intake_lotes.fuente_de`);
`.pulled`, `.synced`, `_inventory.json` o `_exported_ids.json` **dentro de un lote o de un cajón
legacy donde ningún escritor los pone** (`04_Manual/_inventory.json`, `<lote>/.pulled`); y
cualquier fichero de E&V con punto inicial bajo `01_Drive EV/<sub>/` (el propio `intake_drive`
documenta que esos nombres existen).

### 3.3. Los nueve consumidores preguntan por la ruta

| Consumidor | Cambio |
|---|---|
| `inventory.scan` | `es_fichero_de_protocolo(path.relative_to(input_dir))`; desaparece `startswith("_caso")` (`_caso.md` y `._caso.*` están en el registro; el `_caso.md.bak_<ts>` de `migrate_05crm_buckets` pasa a `skipped` por extensión, como hoy en la sala de máquina) |
| `intake_manual.list_files` | ídem con la ruta relativa a `00_Input/`; `list_crm_branch_files` igual (a profundidad ≥ 3 es un no-op y se dice en el comentario) |
| `intake_drive._count_files` | `es_fichero_de_protocolo(f"01_Drive EV/{p.name}")`; sigue no recursivo |
| `intake_lotes.items_desde_disco` | `es_fichero_de_protocolo(f"{lote_dir.name}/{rel}")`: solo el `_manifiesto.yaml` **de la raíz del lote** queda fuera del albarán. El lote desviado a la bandeja conserva su nombre, así que la regla no cambia |
| `email_export.export_label` | ídem para decidir si el lote quedó vacío |
| `sala_maquina._es_control(rel)` | la firma pasa de nombre a ruta relativa; en `inventariar_cacheado` se calcula `rel` **antes** de filtrar (hoy va después). `_IGNORAR` desaparece |
| `scripts/abrir_caso.hash_tree_local` y el recuento de `etapa_drive` | `es_fichero_de_protocolo(f"{prefijo}/{rel}")` — tienen el prefijo `01_Drive EV` a mano |
| `scripts/migrar_layout_intake` | §3.4 |
| `core/crm_ficha_validacion.es_fichero_de_control(rel)` | **delega** en `es_fichero_de_protocolo` para las filas de `_cobertura` (su `rel_path` es relativo a `00_Input/`) y conserva por nombre solo lo que no vive en `00_Input/` (`_cobertura.*`, `_sala_maquina_state.json`, `_registro.json`, `_tiempos.jsonl`). La rev. 1 lo dejaba «como está» por «redundante e inofensivo», y la R1 (H-08) demostró que con el §3.3 se convertía en el sitio donde el adjunto homónimo **desaparece**: una fila documental saltada no cuenta como ilegible, y un `SIN_COMPROBAR` pasa a `NO_ENCONTRADO` |

### 3.4. La migración no borra lo que no acaba de comparar

`scripts/migrar_layout_intake.py` mueve los cajones legacy a lotes. Dos de los ficheros de
`03_Email/` son estado de canal cuyo hogar desde `MEJORAS #54` es la raíz: `_exported_ids.json` y
`_resolved_links.json`, **solo directamente bajo `03_Email/`** (el par de `ENTREGA`). Reglas, y
**dónde** se aplican (R1/H-01: el plan no mira la raíz; la fase 1 decide por `destino.exists()`;
la fase 2 borra sin releer):

1. Se identifican por el par (directorio, nombre), no por pertenencia a un conjunto de basenames:
   `03_Email/hilo/_exported_ids.json` es un adjunto, se mueve al lote con todo lo demás y **entra
   en el `mapping` M9** (cierra el ALTO del homónimo anidado). `_mapping_documental` aplica la misma
   regla.
2. **En el plan** (`plan_migracion`, también con `--dry-run`): para cada estado de canal legacy se
   mira si la raíz ya lo tiene y se compara por `sha256`. Distintos → el plan **aborta** nombrando
   los dos ficheros, antes de mover nada: son dos estados de canal de momentos distintos y decidir
   cuál vale es del operador. Idénticos o ausente → el plan lo anota (`mover` / `duplicado`).
3. **En la fase 1**: si la raíz tiene el fichero y el plan lo anotó como `mover` (apareció entre el
   plan y la ejecución), se aborta antes de mover: la fase 1 es reversible y no se ha tocado nada.
4. **En la fase 2, en el momento del `unlink()`**: se relee el `sha256` del anidado y del de la raíz.
   Si la raíz ya no existe o difiere (un `email_export` concurrente añadió ids), **no se borra** y
   se reporta: dejar el fichero en su cajón es seguro y no exige rollback. Solo se borra lo que
   acaba de demostrarse idéntico.

El rollback de la fase 1 sigue siendo completo: ninguna de las cuatro reglas añade una mutación en
fase 1. El temporal del script (`_intake_hashes.json.tmp`, sin punto inicial) pasa a la forma
`._intake_hashes.<pid>.tmp` para casar con `RAIZ_PREFIJOS`.

### 3.5. Lo que no se toca, y por qué (con su regla, para que nadie lo dé por cubierto)

- `MERGE_EXCLUSIONS` y `plugins/expedientes_xl/tiers.PROTOCOL_*`: contratos por basename del
  checkin y del MCP, con sus guards. No cambian.
- Clasificadores por regla propia sobre `00_Input/` que **no** cambian: `core/anon/api.py`
  (excluye cualquier segmento con `_` inicial a cualquier profundidad: allí un adjunto
  `_ficha_crm.yaml` sigue fuera de la anonimización), `core/local_organizer.py` (`_`/`.` inicial,
  no recursivo), `core/sync.py` y `core/sync_sudespacho.py` (su propio marcador),
  `scripts/migrate_05crm_buckets.py` (script puntual con frozenset propio; sus `.bak_<ts>` y
  `_migration_05crm_<ts>.json` en la raíz quedan como documentos `skipped` por extensión).
- `email_export.write_indices` sobre un cajón legacy escribe `INDICE.md`/`CRONOLOGIA.md` dentro de
  `03_Email/`: siguen inventariándose como hoy. `sync_sudespacho` escribe `_descarga_bruta.bin`
  en el destino del pull legacy si el zip es inválido: ídem.
- No se migra ningún `_cobertura`, inventario ni manifiesto existente: el siguiente `apply` o
  `scan` los regenera con el contrato nuevo.

## 4. Radio de daño y rondas

La pieza decide **qué es prueba documental** en el inventario, en el ledger forense del pull y en
la red de calidad, y toca el único `unlink()` de un fichero que no es un temporal propio
(R1/H-10 corrige la frase de la rev. 1). Por la regla del 2026-08-26, **dos rondas**: esta sobre
el diseño (hecha: §8) y otra sobre el diff. Codex sin cupo → revisor sustituto de `AGENTS.md`,
independencia declarada más débil.

## 5. Mutantes

`tests/test_intake_control_por_ubicacion.py` (nuevo) y ampliaciones de `test_intake_lotes.py`,
`test_inventory.py`, `test_migrar_layout.py`, `test_apertura_v1_control_files.py`,
`test_abrir_caso_cli.py`, `test_crm_ficha_validacion_r1.py`. Los **(+)** son positivos.

| # | Mutante | Qué debe pasar |
|---|---|---|
| T1 | `<lote>/adjuntos/_ficha_crm.yaml` (adjunto homónimo) | en `inventory.scan`, en el albarán del lote, en `inventariar` de la sala de máquina y en `hash_tree_local`; `00_Input/_ficha_crm.yaml` en ninguno |
| T2 | `<lote>/_manifiesto.yaml` vs `<lote>/x/_manifiesto.yaml` | el primero fuera; el segundo dentro |
| T3 | caso con lote de correo y los cuatro de `#149` en la raíz | `inventariar` devuelve **exactamente** el conjunto literal de `rel_path` documentales del fixture (no «ninguno de protocolo» según el oráculo bajo prueba: R1/H-11 lo señaló circular) |
| T4 | migración con `03_Email/_exported_ids.json` **idéntico** al de la raíz | fase 2 lo borra; el de la raíz sigue |
| T5 | migración con `03_Email/_exported_ids.json` **distinto** del de la raíz | el plan aborta antes de mover nada; `00_Input/` byte a byte como estaba; el mensaje nombra los dos; `--dry-run` da el mismo mensaje sin tocar disco |
| T5b | raíz ausente en el plan y **presente y distinta** al empezar la fase 1 | aborta sin mover |
| T5c | idénticos en el plan y la raíz cambia **antes del `unlink()`** de la fase 2 | no borra; reporta; el resto de la migración termina |
| T6 | `03_Email/hilo/_exported_ids.json` (homónimo anidado) | se mueve al lote **y** aparece en el `mapping` con el que se remapea `_intake_hashes.json` |
| T7 | **ejecutar** cada escritor del repo sobre un caso temporal (`IntakeManifest.save`, `RegistroOcurrencias.save`, `apertura_v1_estado.abrir`, `intake_lotes.escribir_manifiesto`, `email_export._save_export_index`/`_save_resolved_links`, marcador de `intake_drive`, marcador de `sync`, `inventory.scan`, `case_manager._write_case_index`) | `inventariar(case_dir) == []`; y con un fallo inyectado entre el temporal y el `os.replace` de cada escritor atómico, el huérfano tampoco aparece |
| T8 (+) | `01_Drive EV/.pulled`, `sudespacho_648/.pulled`, `drive/.synced`, `03_Email/_exported_ids.json` | protocolo |
| T9 | `CarpetaRara/_manifiesto.yaml`, `01_Drive EV/_manifiesto.yaml`, `01_Drive EV/.synced`, `<lote>/.pulled`, `04_Manual/_inventory.json`, `01_Drive EV/OFERTAS/.pulled`, `01_Drive EV/.Oferta firmada.pdf`, `00_Input/_nota_suelta.pdf` | documento (los cinco primeros **cambian** respecto a hoy, y es lo querido) |
| T10 | `_caso.md`, `._caso.4242.tmp`, `.apertura_v1.x.tmp`, `._intake_hashes.4242.tmp`, `._ocurrencias_crm.json.4242.tmp` en la raíz | protocolo; los mismos nombres a profundidad 3, documento |
| T11 | `("../_caso.md")`, `("C:/x/_caso.md")`, `("")`, y `("01_Drive EV\\.pulled")` | `False` los tres primeros; el cuarto igual que con `/` |
| T12 | `01_Drive EV/_organizado/_audit.jsonl` y una copia de documento dentro de `_organizado/` | protocolo (fuera del inventario de la sala de máquina) |
| T13 | `crm_ficha_validacion`: fila de `_cobertura` con `rel_path = "<lote>/adjuntos/_ficha_crm.yaml"` y estado no legible | cuenta como **ilegible**, no se salta |
| T14 | `git grep` de los lectores de `INTAKE_CONTROL_FILES` | solo los declarados en §3.1 |

**Tests hoy verdes que cambian de expectativa, y por qué** (R1/H-06):
`tests/test_intake_lotes.py::test_manifiesto_round_trip_y_exclusiones` (`<lote>/_exported_ids.json`
y `<lote>/.pulled` pasan a **entrar** en el albarán: ningún escritor los pone ahí; el
`_manifiesto.yaml` sigue fuera); `tests/test_intake_manual.py::test_excluye_archivos_de_control`
(`04_Manual/.pulled`, `_inventory.json`, `.synced` pasan a ser documentos por la misma razón);
`tests/test_intake_lotes.py` líneas 28-35 (la identidad de los tres alias con
`INTAKE_CONTROL_FILES` desaparece con los alias); `tests/test_abrir_caso_cli.py::…hash_tree_local`
(`01_Drive EV/_inventory.json` pasa a **entrar** en el ledger: es un fichero de E&V homónimo, no
protocolo); `tests/test_apertura_v1_control_files.py` (llama a `_es_control` con un basename: sigue
pasando porque un basename es una ruta de profundidad 1, y se reescribe para preguntar a
`es_fichero_de_protocolo` con la ruta real). Un rojo distinto de estos en el diff es una regresión.

## 6. Alcance explícito

- **Toca:** `core/intake_control.py` (nuevo), `core/config.py` (registro derivado y comentario),
  los nueve consumidores del §3.3 y §3.4, `core/crm_ficha_validacion.es_fichero_de_control`,
  tests. Cierra `MEJORAS #149` y declara `#54 T1` (la «lista única» por nombre) sustituida por el
  registro por ubicación.
- **No toca:** `MERGE_EXCLUSIONS`, el plugin, `core/anon`, `local_organizer`, `sync*`,
  `migrate_05crm_buckets`, ni ningún artefacto ya escrito en un expediente.
- **No cubre:** la deduplicación de documentos (`#147`); qué hacer con un fichero de protocolo
  **corrupto** (lo detecta quien lo lee, no quien lo clasifica); y la concurrencia entre la
  migración y un `email_export` sobre el mismo caso más allá de no borrar (el mutex del caso es
  `MEJORAS #126`).

## 7. Lo que la R1 no pudo verificar, y sigue sin verificar

Cuántos casos reales están en layout legacy (`data/CASOS/` y `G:` fuera del alcance del revisor);
la reproducción del CRÍTICO del 2026-09-04 tal como lo describe su acta (leída, no re-ejecutada:
el diff está revertido); y la implementación futura de `es_fichero_de_protocolo`, que la R2 sobre
el diff verificará.

## 8. Adjudicación de la revisión adversarial (Claude Code sesión independiente, 2026-09-05) — REQUIERE-REVISION, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-09-05-ficheros-de-protocolo-por-ubicacion-design.md` rev. 1, commit `ff2ecd4`
- **Ronda:** 1
- **Revisor:** Claude Code (sesión independiente), solo lectura, con dos sondas ejecutadas (`probe_contrato.py`, `probe_carrera_migracion.py`) contra un `CASOS_ROOT` temporal
- **Informe recibido:** `2026-09-05-ficheros-de-protocolo-por-ubicacion-r1-adversarial-review.md`
- **Hallazgos:** 11 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento

**Independencia, declarada más débil.** Codex no tiene cupo; el revisor fue un subagente de
Claude Code sin el contexto de autoría (`AGENTS.md` §«Revisor sustituto»). Autor y revisor son el
mismo modelo. Lo que compensa: el revisor implementó literalmente el enunciado del §3.2 de la
rev. 1 y lo ejecutó contra el árbol, en vez de razonar sobre él, y reprodujo la pérdida de H-01
con una carrera simulada. Yo he vuelto a la fuente para H-01 a H-06 antes de adjudicar. El digest
del informe se recalculó al recibirlo y coincide.

| # | Sev. | Hallazgo | Veredicto | Dónde se remedia |
|---|---|---|---|---|
| H-01 | ALTO | la comparación por hash estaba en el plan; la fase 1 decide por `destino.exists()` y la fase 2 borra sin releer | **confirmado** (sonda: el anidado se borró tras cambiar la raíz durante la fase 1) | §2 y §3.4 reglas 2-4: hash en el plan, guarda en fase 1, relectura en el `unlink()`; T5b, T5c |
| H-02 | ALTO | `03_Email/_exported_ids.json` pasaba de excluido a inventariado; `email_export` sigue leyéndolo de ahí y la migración no tiene disparador | **confirmado** (`email_export`: `legacy_cajon = estado_dir / "03_Email"`) | §3.1 pares `("03_Email", …)`; T8 |
| H-03 | ALTO | `scripts/abrir_caso.hash_tree_local` y el recuento V1 clasifican por basename recursivo; «ningún consumidor» era falso | **confirmado** (`p.name in intake_drive.CONTROL_FILES` sobre `rglob`) | §1 (nueve consumidores), §3.3; alias retirados; T1, T9 |
| H-04 | MEDIO | la profundidad 2 admitía cualquier carpeta de primer nivel: `CarpetaRara/_manifiesto.yaml` pasaba a protocolo; `01_Drive EV/.synced` declarado positivo sin escritor | **confirmado** (`test_inventory` fija `CarpetaRara/` como fuente `manual`; `.synced` lo escribe `core/sync` en `drive/`) | §3.1 pares (directorio, nombre); T9 |
| H-05 | MEDIO | censo de escritores incompleto: temporales `._intake_hashes.`, `._ocurrencias_crm.json.`, `_intake_hashes.json.tmp` del script, `_organizado/**`, índices en cajón legacy, `.bak_` | **confirmado** (`intake_manifest`, `ocurrencias_crm` escriben esos temporales) | §3.1 `RAIZ_PREFIJOS` y `DIRECTORIOS`; §3.4 último párrafo; §3.5; T10, T12 |
| H-06 | MEDIO | T12 («los tests siguen verdes») era falso para al menos dos tests | **confirmado** (`test_intake_lotes:104-113`, `test_intake_manual:142-154`) | §5, bloque «tests que cambian de expectativa» |
| H-07 | MEDIO | «`INTAKE_CONTROL_FILES` lo espejan `MERGE_EXCLUSIONS` y el plugin» era falso y peligroso | **confirmado** (`MERGE_EXCLUSIONS` no contiene esos nombres; `_ocurrencias_crm.json` viaja en `GRUPOS_MERGE`) | §3.1: derivado, no clasifica, lectores por `git grep`; alias retirados; T14 |
| H-08 | MEDIO | `crm_ficha_validacion.es_fichero_de_control` no era inofensiva: con §3.3, el adjunto homónimo desaparece del recuento de ilegibles | **confirmado** | §3.3 última fila: delega en `es_fichero_de_protocolo`; T13 |
| H-09 | BAJO | `_listar` no existe; `_count_files` no es recursivo; `rel` se calcula después del filtro | **confirmado** | §1 y §3.3 corregidos |
| H-10 | BAJO | «el único `unlink()` del intake» era más ancho que el código | **confirmado** | §4 |
| H-11 | BAJO | T3 circular; T7 sin mecanismo; faltan mutantes de H-01/H-02/H-04/H-05 y de la lente 5 | **confirmado** | §5: T3 literal, T7 ejecutable, T5b/T5c, T9, T10, T11, T12 |

**Lo que el revisor verificó y resultó correcto** —la tabla del §1 fila a fila, los cuatro no
declarados y dónde se escriben, el censo de raíz y de entrega, la ausencia de manifiestos de
`split_documental` bajo `00_Input/`, que `_cobertura.json` vive fuera, las rutas calculables en
cada consumidor, el `mapping` de `plan_migracion`, el rollback de la fase 1, el guard del plugin y
el presupuesto de rondas— está en el §2 del acta. **Lo que no pudo verificar** está en el §7.
