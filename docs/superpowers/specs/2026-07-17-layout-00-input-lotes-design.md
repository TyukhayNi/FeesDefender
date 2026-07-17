# Layout de `00_Input` por lote de intake — spec de diseño (rev 2)

**Fecha:** 2026-07-17 (rev 2; la rev 1 del mismo día fue sometida a revisión adversarial en sesión).
**Origen:** `docs/MEJORAS_FUTURAS.md` #54 (decisión de arquitectura pendiente, anotada 2026-07-13
tras la fricción de intake tri-canal en W-02XOR7 / BaRS8).
**Decide:** modelo A revisado — **lotes por entrega** para los canales de entrega + **cajones-espejo
estables** para los canales de sincronización. Incorpora cuatro decisiones de Nikolai (2026-07-17):
espejos fuera del modelo de lotes; M9 como índice único de dedup; los duplicados se copian
igualmente; la migración remapea los registros aguas abajo.

**Qué cambió respecto a rev 1.** La revisión adversarial (50 hallazgos; 18 con verificación
independiente, 0 refutados) tumbó cuatro supuestos: (1) no todos los escritores son «cambiar un
rel_base» — dos canales son syncs incrementales con estado anclado al cajón; (2) ya existen dos
mecanismos de dedup vivos (M9 + shas del `_intake_log`) que rev 1 ignoraba; (3) «no copiar el
duplicado» rompía a los consumidores que leen disco por vecindad; (4) la migración dejaba
huérfanos los registros por-ruta (cobertura OCR, M9, catálogo). Además se completó el inventario
de consumidores (rev 1 omitía 4 escritores y 5 lectores) y se corrigieron vocabulario y símbolos.

**Alcance de esta spec.** Solo el layout de `00_Input`: convención de lote, esquema de manifiesto,
dedup cross-lote, contrato de lectura `fuente_de`, migración de los puntos de intake y el
descubrimiento mínimo de los lectores, y migración bajo demanda de casos ya abiertos. **No** cubre
la clasificación fina de `email_atomize` / `sala_maquina` / el motor de sala de lectura — eso es
objeto de specs de seguimiento para #55 y #56, que consumen esta decisión como terreno resuelto.

---

## 1. Problema

`00_Input` codifica hoy un único árbol de 6 cajones fijos (`config.INPUT_SUBDIRS`: `01_Drive EV`,
`02_Whatsapp`, `03_Email`, `04_Manual`, `05_CRM`, `06_Entrevistas`), pensados para el eje
**procedencia** (canal). En la práctica hay tres ejes ortogonales — procedencia, tipo de contenido
y lote de entrega — y un árbol de un solo nivel no puede representar limpiamente los tres.
Consecuencia observada en W-02XOR7: WhatsApps y correos que venían *dentro* de un pull de Drive
cayeron en `01_Drive EV` en vez de sus cajones propios, y una grabación de Meet fue a `04_Manual`
por no existir ruta a `06_Entrevistas` desde el CLI.

Matiz que rev 1 no hacía explícito: la corrección de la misclasificación *intra-canal* (los
WhatsApps dentro del pull de Drive) no la aporta el layout sino el **metadato** — en cualquier
modelo, lo que dice «esto es un WhatsApp aunque llegara por Drive» es el manifiesto/catálogo. El
layout resuelve el eje de **lote** (entregas que no se pisan entre sí) y deja de forzar los otros
dos ejes al árbol.

## 2. Decisión

**Modelo A revisado — lotes por entrega + espejos estables.** Hay dos semánticas de canal, y cada
una recibe la forma que le corresponde:

- **Canales de entrega** (`whatsapp`, `email`, `manual`, `entrevista`): cada intake (evento de
  entrega) es su propia subcarpeta `00_Input/<AAAA-MM-DD>_<fuente>_<NN>/`, con el contenido
  copiado **verbatim** y un `_manifiesto.yaml` (albarán de la entrega). Append-only: una entrega
  nunca pisa otra.
- **Canales espejo** (`01_Drive EV`, `05_CRM`): conservan **cajón fijo** y su semántica actual de
  sincronización incremental — rclone copiando sobre el mismo directorio + marcador `.pulled`
  (`core/intake_drive.py:196-229`), pull v2 del CRM con `reconcile()` sobre M9
  (`core/sync_sudespacho.py:1351`). **No forman lotes** (decisión Nikolai 2026-07-17). Un espejo
  no es una entrega: es el estado actual de un origen que sigue vivo, y su eficiencia depende de
  comparar contra lo ya bajado. Carpeta virgen por corrida = re-descarga completa en cada pull
  (rclone) o, peor, skip silencioso del sync CRM vía M9 dejando el cajón vacío (verificado sobre
  `core/sync_sudespacho.py:1560`).

**Por qué A y no B ni el híbrido rechazado:** B (cajones fijos + routing por tipo en el ingest)
mitigaría el síntoma pero no la causa — sigue forzando tres ejes a uno y añade lógica
content-aware en la entrada. El híbrido rechazado en rev 1 (cajón de nivel 1 + lote de nivel 2)
conservaba la ambigüedad («¿a qué cajón va esto?») un nivel más abajo. **Este modelo no es ese
híbrido**: aquí no hay ambigüedad de destino — cada canal tiene exactamente una forma, determinada
por su semántica (entrega → lote, sync → espejo), no por el contenido de lo que llega.

**Coste de migración, corregido.** Sigue siendo cierto que `dir_intake(case_id, rel_base, origen)`
recibe `rel_base` como parámetro (`core/case_manager.py:719-739`) y que el guard §6
(`guard_escritura` / bandeja `_pendiente_checkin`) no cambia. Pero rev 1 subestimó el coste: los
escritores de entrega tienen acoplamientos más allá del rel_base (estado incremental del export de
email, doble cálculo de ruta en whatsapp, vías de `scripts/abrir_caso.py` que no pasan por
`dir_intake`), y el inventario de consumidores estaba incompleto. El inventario completo y el
destino de cada uno: §8.

## 3. Alcance de la migración

- **Casos nuevos:** nacen directamente con este modelo.
- **Casos existentes:** **no se tocan de oficio.** Se migran solo si vuelven a recibir un intake
  activo, vía el script de la sección 7 (migración bajo demanda, no barrido masivo), que además
  **remapea los registros aguas abajo** (§7.4). Coherente con la regla del despacho de promover
  solo con disparador concreto y con la invariante "`00_Input` append-only".

## 4. Convención de nombre de lote

```
00_Input/<AAAA-MM-DD>_<fuente>_<NN>/
```

- `fuente` ∈ `{whatsapp, email, manual, entrevista}` — es `FUENTE_A_SUBDIR`
  (`core/abrir_caso.py:14-17`) **menos `drive_ev`** (espejo, no forma lotes). Corrección de rev 1:
  aquel vocabulario incluía `crm` afirmando que era «el mismo que FUENTE_A_SUBDIR hoy» — falso por
  partida doble (`crm` nunca estuvo en ese mapa, y ahora es espejo). `entrevista` se mantiene en el
  vocabulario aunque hoy no tiene escritor (`_FUENTES_CLI` no la expone,
  `scripts/abrir_caso.py:60`; su alta la gobierna #53) — reservar el nombre evita otra migración.
- **Canónico singular:** `entrevista`. `_SOURCE_MAP` usa hoy el plural `entrevistas`
  (`core/catalogo_documental.py:28`); se normaliza al singular cuando §8 toque ese mapa.
- `<AAAA-MM-DD>` es la fecha del intake (no de contenido), fecha ISO al frente.
- `NN` es un contador de 2 dígitos que sube si ya existe un lote de la misma fuente el mismo día.
  Dos reglas nuevas que rev 1 no tenía:
  - **Reserva atómica:** el nombre se reserva creando el directorio con mkdir atómico (si ya
    existe, se prueba `NN+1`). Cubre dos sesiones concurrentes (Code + Cowork sobre el mismo caso
    *disponible*: ningún lock las cubre — `decidir_escritura` permite sin más,
    `core/repository_checkout.py:509`).
  - **El contador mira también la bandeja:** cuenta los lotes de `00_Input/` **y** de
    `_pendiente_checkin/*/` (un intake sobre caso prestado se desvía ahí con su nombre de lote; si
    el contador no los viera, el checkin fusionaría dos lotes homónimos fichero a fichero).
- Dentro del lote, el contenido se copia **verbatim** (p. ej. un lote de WhatsApp conserva sus
  subcarpetas de rol, `00_Consultor propietario/` etc.). Con la regla de duplicados de §6 el
  verbatim es real: nunca faltan bytes.

Ejemplo: un WhatsApp exportado el 2026-07-17 para W-02XOR7 se deposita en
`00_Input/2026-07-17_whatsapp_01/00_Consultor propietario/<chat>/`.

## 5. Esquema de `_manifiesto.yaml` por lote

Cada lote lleva un `_manifiesto.yaml` en su raíz:

```yaml
fuente: whatsapp                  # vocabulario §4
fecha_intake: "2026-07-17"        # fecha del evento de entrega
origen: "abrir_caso_cli"          # quién/qué disparó el intake
items:
  - relpath: "00_Consultor propietario/chat_maria/_chat.txt"
    sha256: "8059c4220..."
    size: 48213
    tipo_contenido: whatsapp
  - relpath: "00_Consultor propietario/chat_maria/IMG-001.jpg"
    sha256: "a1b2c3d4..."
    size: 204981
    tipo_contenido: imagen
    duplicado_de: "2026-06-10_manual_01/IMG-001.jpg"  # anotación; el fichero SE COPIA igual (§6)
# los ítems de lotes email llevan además: message_id: "<CAF+xyz@mail.gmail.com>"
```

- El manifiesto es el **albarán forense de la entrega**: qué llegó, cuándo, por qué canal, con qué
  huellas. **No es fuente de dedup ni índice de búsqueda** (§6) — así no compite ni con
  `_intake_log.jsonl` ni con M9.
- `tipo_contenido` es un clasificador **nuevo, por extensión**, con **vocabulario propio del eje
  tipo**: `pdf`, `imagen`, `video`, `audio`, `docx`, `txt`, `eml`, `whatsapp` (solo `_chat.txt`),
  `otros`. Corrige dos defectos de rev 1: (a) su ejemplo remitía al vocabulario de
  `_SOURCE_MAP`, que es el eje de *procedencia* que la propia spec ordenaba no confundir; (b)
  faltaban `eml` (el canal email entero) y `audio` (el sistema ya maneja `_AUDIO_EXTS`,
  `core/whatsapp_intake.py:21`). Función nueva: `clasificar_tipo_contenido(path) -> str`.
- `message_id` (solo ítems `.eml`): identidad del correo, para el dedup tri-canal (§6).
- **Ficheros de control fuera del manifiesto:** `.pulled`, `.synced`, `_inventory.json`,
  `_exported_ids.json` y análogos no son documentos y no entran. La lista pasa a ser única en
  `config`, unificando las dos copias divergentes de hoy (`core/inventory.py:47` y
  `core/intake_manual.py:37`). `_export_original.zip` de WhatsApp **sí** entra: es el export
  original, contenido forense.
- `_intake_log.jsonl` sigue existiendo **sin cambios de esquema**. Corrección de rev 1: el log
  **sí** lleva detalle por ítem (`details.files[].sha256`, que `core/abrir_caso.py:142-149` ya
  consume para dedup). Log (diario de eventos del caso) y manifiesto (albarán por entrega)
  conviven porque responden preguntas distintas; **ninguno de los dos es la fuente de dedup**.

## 6. Dedup cross-lote

**Fuente única: M9.** `00_Input/_intake_hashes.json` (`core/intake_manifest.py`) ya es el índice
de huellas del caso, con `register()`/`lookup()`/`reconcile()` y **tres consumidores vivos**
(`core/whatsapp_intake.py:145`, pull CRM `core/sync_sudespacho.py:~1473-1533`,
`core/email_export.py`). Los escritores de lote consultan `lookup(sha)` antes de escribir cada
ítem y lo registran al depositarlo. Rev 1 proponía «recorrer los manifiestos, sin índice aparte»
ignorando que el índice aparte ya existía: eso no evitaba una segunda fuente de verdad — creaba la
tercera (decisión Nikolai 2026-07-17: M9 único).

**Dedup de correos por Message-ID.** Requisito de #54 que rev 1 perdió: el mismo correo llegado
por dos canales (etiqueta Gmail y dentro del pull de Drive) casi nunca es byte-idéntico → sha256
no lo detecta; el Message-ID sí. M9 se extiende con un campo opcional `message_id` por entrada y
lookup por él — mismo criterio que el dedup intra-canal ya existente de `email_export`
(Message-ID con respaldo sha).

**Duplicado detectado → el fichero se copia igualmente**, y se anota
`duplicado_de: <lote>/<relpath>` en el manifiesto (decisión Nikolai 2026-07-17). El metadato
informa; no suprime bytes. Razón: los consumidores leen disco por vecindad —
`whatsapp_atomize._leer_media` resuelve la media por `iterdir()` de la carpeta del chat
(`core/whatsapp_atomize/pipeline.py:38-43`), el OCR de sala de máquina camina ficheros físicos —
y el «verbatim» de §4 deja de ser verdad si faltan ficheros. La propuesta de rev 1 (no copiar)
convertía #55/#56 de specs de seguimiento en prerequisito.

**Bordes con regla (rev 1 no los tenía):**
- Fichero de tamaño 0: nunca se marca duplicado (su sha constante relacionaría cosas sin relación).
- Mismo sha dos veces dentro del mismo lote: se copia y se anota igual (duplicado intra-lote).
- Espejos: sin cambio — su dedup sigue siendo el propio sync (rclone / reconcile M9), como hoy.

## 7. Migración bajo demanda de casos existentes

Comando `python -m scripts.migrar_layout_intake <case_id>`:

1. **Solo cajones de entrega:** envuelve `02_Whatsapp`, `03_Email`, `04_Manual` y
   `06_Entrevistas` (los que tengan contenido) en lotes sintéticos
   `<fecha_estimada>_<fuente>_01`. **`01_Drive EV` y `05_CRM` no se tocan** (espejos, §2). Rev 1
   envolvía los 6 cajones, lo que rompía los dos syncs.
2. **Estructura del lote sintético:** el *contenido* del cajón pasa a la raíz del lote (las
   subcarpetas de rol de WhatsApp/Email se conservan tal cual). El cajón queda vacío y no se
   borra.
3. **Fecha estimada:** `fecha_intake` = la más antigua entre (a) las fechas ISO presentes en
   nombres de fichero (nomenclatura del despacho `AAAA-MM-DD_…`) y (b) el mtime, sobre el
   contenido del cajón; marcada `fecha_intake_estimada: true`. Rev 1 no definía el criterio.
4. **Remapeo de los registros por-ruta** (decisión Nikolai 2026-07-17): al mover, el script
   reescribe ruta vieja→nueva en:
   - `00_Input/_intake_hashes.json` (`primary_path` relativo a `00_Input`,
     `core/intake_manifest.py:27`);
   - `01_Procesado/02_Sala de máquina/_cobertura.json` — la cobertura acumulativa fusiona **por
     `rel_path`** (`core/sala_maquina.py:157-185`); sin remapeo, un caso ya procesado se
     re-OCRearía entero (W-02VND1: 668 docs, horas de cómputo) y la cobertura quedaría con filas
     huérfanas;
   - `01_Procesado/indice_documental.yaml` (rutas del catálogo).
5. **Protocolo intacto:** `_caso.md`, `_intake_log.jsonl` y `_intake_hashes.json` viven en la raíz
   de `00_Input` y no se tocan. (Corrección de rev 1: «`00_Input/` vacío al alta» era literalmente
   falso; la formulación correcta es «sin cajones de entrega» — la raíz conserva el protocolo.)
6. **Guard/lock:** si el caso está `prestado` o `conflicto`, la migración **aborta** con mensaje
   claro (desviar medio árbol a la bandeja no tiene sentido); se corre tras el checkin.
7. Se dispara **solo** cuando el caso recibe un intake nuevo — nunca de oficio ni en barrido. No
   borra los cajones vacíos que queden (limpiarlos queda fuera de esta spec).

## 8. Migración de consumidores (inventario completo)

Rev 1 listaba 4 escritores y 2 lectores; el barrido adversarial encontró 9 y 7. Destino de cada
uno:

### Escritores de entrega (migran a lote)

- `core/whatsapp_intake.py` — rel_base de lote en los **dos** puntos donde hoy calcula el cajón
  (`:138` ruta física vía `dir_intake`, `:152` relpath para el registro M9).
- `core/email_export.py` — `email_dest_dir` (`:1301`; rev 1 citaba `dir_email`, símbolo
  inexistente) pasa a lote por corrida, **con re-anclaje del estado de canal** (sin esto, cada
  re-export re-bajaría la etiqueta entera y fragmentaría la cronología):
  - el índice de export (`_exported_ids.json`, hoy dentro del cajón, `:1073-1082`) se muda a la
    raíz de `00_Input` como fichero de protocolo;
  - la idempotencia por Message-ID deja de escanear el cajón (`existing_message_ids`,
    `:781-793`) y consulta M9/`message_id` (§6);
  - `INDICE.md`/`CRONOLOGIA.md` pasan a regenerarse **cross-lote** en `01_Procesado/Emails/`
    (son artefactos derivados, no crudo; hoy se regeneran por-cajón, `:1276-1298`).
- `scripts/abrir_caso.py` + `core/abrir_caso.py` — las vías manual/email que hoy **no** pasan por
  `dir_intake` (`scripts/abrir_caso.py:129`) se re-cablean por él; la cadena de custodia deja de
  parsear el primer segmento de la ruta como cajón (`core/abrir_caso.py:170`) y toma la fuente del
  plan; `FUENTE_A_SUBDIR` se sustituye por el vocabulario §4.
- `core/intake_manual.py` — `_MANUAL_SUBDIR` (`:36`; escritor real de la UI Streamlit de
  Paola/Ana, omitido en rev 1) → lote `manual`. Su paso 7b hacia `05_CRM` no cambia (espejo).
- Skill `intake-expediente` (Cowork; `SKILL.md:44`, deposita en los cajones vía `expedientes-xl`)
  — se actualiza al modelo de lote y se **re-empaqueta el `.skill`** (superficie que no se
  actualiza con el repo).

### Escritores que NO cambian (espejos)

`core/intake_drive.py`, `core/sync_sudespacho.py` (pull v2), `core/judicial_intake.py`,
`save_file_crm_branch`, y `core/local_organizer.py` (opera dentro de `01_Drive EV`,
`local_organizer.py:60`).

### Contrato único de lectura de fuente (el suelo que pisan #55/#56)

Función core nueva `fuente_de(rel_path) -> str`, resuelta por este orden:

1. primer segmento espejo → `01_Drive EV` → `drive_ev`; `05_CRM` → `crm`;
2. primer segmento con patrón de lote `AAAA-MM-DD_<fuente>_<NN>` → `<fuente>` (el nombre manda; el
   manifiesto aporta el detalle por ítem);
3. primer segmento cajón legacy → `_SOURCE_MAP` (casos no migrados);
4. fichero en raíz → `manual`.

Sustituye a las **tres convenciones dispersas** de hoy: `core/inventory.py::_source_of`
(`:50-58`), `core/catalogo_documental.py::_map_source` (`:58`) y
`.claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py::_fuente` (`:28-30`, cuyo
fallback `"manual"` convertiría todos los lotes en `manual` si no se migrara).

### Lectores — descubrimiento mínimo EN alcance

(Que *encuentren* el material en lotes; su clasificación fina sigue siendo #55/#56.)

- `core/whatsapp_atomize` — `descubrir_chats` está clavado a `00_Input/02_Whatsapp`
  (`pipeline.py:22`; omitido en rev 1 tanto de §8 como del diferido §10): pasa a descubrir chats
  en lotes `whatsapp` + cajón legacy.
- `core/email_atomize` — descubre `.eml` con glob sobre el cajón fijo (`extract.py:51-53` vía su
  caller): ídem, lotes `email` + legacy.
- `core/sala_maquina.py` — no rompe (inventaría `00_Input/` recursivo); su clasificación por
  manifiesto es #55/#56.
- Skills lectoras que enumeran cajones en su texto (`organizar-sala-lectura`, `triaje-viabilidad`,
  `viabilidad-prerelleno`, `preparacion-audiencia-previa`, `exportar-correos-etiqueta`):
  actualización de texto + re-empaquetado; se inventarían en el plan.

### Scaffolding de `ensure_case` (eager→lazy solo en entregas)

Dejan de crearse al alta los cajones de entrega y sus roles (`core/case_manager.py:274-280`).
`01_Drive EV` también pasa a lazy (`intake_drive` ya hace `mkdir(parents=True)`, `:197`). La base
`05_CRM` se mantiene como hoy (D7). Corrección de rev 1: presentaba D7 como precedente de «lazy
total» — impreciso: D7 crea la base `05_CRM` **eager** (`_ensure_crm_tree_dirs`,
`case_manager.py:283`) y solo sus buckets son lazy. `00_Input/` al alta queda **sin cajones de
entrega**, no vacío: la raíz conserva `_caso.md` y los ficheros de protocolo.

## 9. Testing

1. Nombre de lote: formato `AAAA-MM-DD_fuente_NN`, colisión mismo día sube `NN`, reserva por mkdir
   atómico bajo concurrencia, y el contador cuenta también los lotes de la bandeja
   `_pendiente_checkin`.
2. Manifiesto: round-trip de esquema, exclusión de ficheros de control, `message_id` presente en
   ítems de lotes email.
3. Dedup vía M9: sha repetido cross-lote → **se copia** + `duplicado_de`; mismo correo con bytes
   distintos y mismo Message-ID → `duplicado_de`; fichero vacío no marca; espejos no afectados.
4. Migración (§7) sobre fixture con los 4 cajones de entrega poblados **+ espejos poblados**:
   espejos intactos, protocolo de raíz intacto, remapeo verificado de
   `_cobertura.json`/`_intake_hashes.json`/catálogo (round-trip: la cobertura previa sigue casando
   tras migrar, sin filas huérfanas), abort limpio con caso prestado.
5. Email incremental con lotes: un re-export no re-descarga lo ya exportado (índice de canal) y la
   cronología cross-lote sale completa.
6. Tests existentes cuyo contrato cambia (inventario explícito, no sorpresa del plan):
   `TestEnsureCaseCrea04Manual` (`tests/test_intake_manual.py:232-237`) se invierte; los rel_base
   de `tests/test_guard_intake_wiring.py` se actualizan; `test_smoke_paso7` (base `05_CRM`) **no**
   cambia.

## 10. Fuera de alcance (explícito)

- Clasificación fina de los lectores por manifiesto (#55, #56) — aquí solo el contrato
  `fuente_de` y el descubrimiento mínimo de §8.
- Escritor de la fuente `entrevista` (#53).
- Limpieza de cajones de entrega vacíos tras la migración bajo demanda.
- Barrido retroactivo de todos los casos existentes.
- Cambios de esquema en `_intake_log.jsonl`.

---

**Registro de revisión.** Rev 1 (commit `e93fbd9`, rama `claude/pending-improvements-list-0e255e`,
nunca mergeada): modelo A puro (6 fuentes incl. espejos), dedup por recorrido de manifiestos,
no-copia de duplicados, migración de los 6 cajones sin remapeo. Rev 2 (esta): tras revisión
adversarial de 2026-07-17 (6 lentes, 50 hallazgos, 0 refutados de 18 verificados) + 4 decisiones
de Nikolai del mismo día. **Sustituye íntegramente a rev 1.**
