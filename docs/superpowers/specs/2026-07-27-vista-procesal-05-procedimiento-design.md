# Diseño — Vista procesal del expediente en `05_Procedimiento`

_Brainstorming Claude Code · FeesDefender · 2026-07-27_
_Origen: petición de Nikolai sobre el expediente judicial CRM **487** (caso `W-02MA0R`) —
«que en Procedimiento acabe la demanda de monitorio con documentos en una carpeta, en otra la
contestación al monitorio, en otra la demanda de juicio ordinario con documentos, en otro
contestación y en otra el resto de los escritos»._
_Precedentes: `docs/INTEGRACION_SUDESPACHO.md` §13 (árbol `05_CRM`), `PLAN.md`
`[SIGUIENTE-REORG-05CRM]` (buckets planos D5/D6), `core/intake_manifest.py` (dedup M9)._

## 0. Estado de las decisiones (cerradas con Nikolai, 2026-07-27)

| Decisión | Resuelto |
|---|---|
| **Alcance** | Herramienta **reutilizable** en `core/` + CLI `plan`/`apply` + tests. No script puntual, no skill |
| **Dónde se construye la vista** | Solo en `05_Procedimiento`. **`00_Input/05_CRM` no se toca**: sigue siendo espejo fiel de cómo está archivado el expediente en el CRM |
| **Qué es la vista** | El **inventario de la fase procesal**, no una proyección del CRM. Un documento puede venir del CRM (`origen: crm`) o haberlo generado el despacho (`origen: despacho`) — ver §1.1 |
| **Escritos propios** | Conservan el nombre que les puso `escritos-judiciales`. La herramienta **no renombra** un fichero que no ha creado ella; los registra en su sitio |
| **Nomenclatura (solo `origen: crm`)** | Orden procesal: escrito rector `00_`, documentos con su numeración del pleito (`D-02_`), escritos sueltos por fecha de lote (`AAAA-MM-DD_`) |
| **Ubicación del mapping** | `05_Procedimiento/_mapa_procesal.yaml` — dentro del árbol que **sí** sincroniza al Drive en el checkin |
| **Deriva (doc_id nuevos)** | Van a `sin_asignar:`; **`apply` aborta** mientras ese bloque no esté vacío. Nunca se adivina la carpeta |
| **Idempotencia** | `apply` solo toca lo que figura en su propio `_MANIFIESTO_PROCESAL.json`. Escritos generados y `Jurisprudencia/` son inalcanzables por construcción |
| **Resolución `doc_id` → fichero** | Opción **B**: persistir el `doc_id` en la entrada canónica del manifiesto de intake (hoy solo vive en los alias) |
| **Índice para el letrado** | El que ya existe: `<carpeta>/_index.md` de `registrar_outputs.py`. **No se inventa un segundo índice humano** — ver §2.3 |
| **Qué fichero se copia** | El **PDF buscable** de la sala de máquina (`01_OCR/<slug>.pdf`) cuando existe; el crudo cuando no; y el crudo **con aviso** si el documento es `sin_soporte`. Es el criterio que Nikolai ya cerró el 2026-07-19 para la sala de lectura, aplicado aquí. Ver §2.4 |
| **`01_OCR/` no se universaliza** | Sigue siendo artefacto de custodia («a esto le añadimos capa de texto»), no almacén de todo. La capa universal es `03_MD/`. Razonado en §2.4 para que no se «arregle» después |
| **`.doc` sin MD ni OCR** | Hueco real: `clasificar_ruta` lo manda a `sin_soporte`. Afecta a la demanda del ordinario del caso piloto. Se cierra con `MEJORAS #61` (LibreOffice headless), **promovido a `PLAN.md` el 2026-07-27**. No bloquea esta pieza |
| **Documentos presentados en los dos procedimientos** | Se copian en **ambas** carpetas, con la numeración de cada pleito. El reparto es por `doc_id`, no por SHA: cada carpeta queda completa y legible sin salir de ella (§4.2) |
| **Sala de lectura** | Los procesales **no** van a `01_Procesado/Sala lectura`. `05_Procedimiento` ya es la sala de lectura del letrado para la fase procesal (§7) |

## 1. El flujo real, en los dos sentidos (contexto de Nikolai, 2026-07-27)

El CRM es **el sitio donde el despacho centraliza todos los documentos procesales**, y también
el canal por el que llegan al procurador. `05_Procedimiento` es el banco de trabajo del letrado.
Los documentos cruzan en las dos direcciones:

| Fase | Dirección | Qué se mueve |
|---|---|---|
| Preparación de la demanda | **carpeta → CRM** | La demanda y sus documentos se generan en la carpeta del caso y se suben al CRM: para el procurador y para que el gestor documental los centralice |
| Vida del pleito | **CRM ← juzgado/contrario** | Contestación, documentos de contrario, decretos, cédulas, tasas: se archivan en el CRM |
| Preparación del juicio o de la audiencia previa | **CRM → carpeta** | Hacen falta demanda y contestación juntas en la carpeta. La contestación siempre baja del CRM; la demanda baja **solo si es un caso anterior a FeesDefender** |

De ahí que la vista procesal **no sea una proyección del CRM**: es el inventario de la fase, y
cada entrada declara su procedencia.

- **`origen: crm`** — el documento vive en `00_Input/05_CRM` (lo trajo el intake). Se **copia** a
  su carpeta procesal con el nombre canónico de §3.
- **`origen: despacho`** — lo generó `escritos-judiciales` y **ya está** en la carpeta procesal.
  Se **registra**, no se copia ni se renombra: conserva el nombre con el que quedó anotado en el
  manifiesto de outputs del caso.

Consecuencia de diseño, y no menor: con `origen: despacho` los escritos propios pasan a estar
**inventariados** en vez de tolerados como «ajenos». La lista de ajenos recupera su sentido de
alarma — lo que aparece ahí es lo que nadie ha declarado.

**Caso piloto W-02MA0R:** la demanda se preparó antes de FeesDefender, así que sus 70 documentos
son todos `origen: crm`. La rama `despacho` no se ejercita aquí; se implementa porque es el
camino de régimen y porque reservarla después obligaría a migrar el esquema del mapa.

### 1.1 El problema concreto: el CRM no archiva por fase procesal

El expediente 487 tiene **dos procedimientos** (monitorio y, tras la oposición, ordinario) y
**70 documentos** en el gestor documental del CRM. El CRM no los archiva por fase procesal:

| `id_carpeta` | Label CRM | Docs | Bucket que le asigna hoy `resolve_bucket` |
|---|---|---|---|
| 306 | CIVIL | 38 | `99_Otros` |
| 307 | DEMANDA | 15 | `01_Demanda` |
| 304 | DEMANDA | 8 | *(sin mapear)* → `99_Sin categoria/487` |
| 1 | General | 5 | `99_Otros` |
| 312 | DOCUMENTOS | 2 | `99_Otros` |
| 303 | MONITORIO | 1 | `99_Otros` |
| 63 | Documentacion RGPD LOPD | 1 | `99_Otros` |

El grueso (38) está volcado en un cajón genérico «CIVIL». **Ningún mapeo de `id_carpeta` puede
desenredar eso**: la información de a qué fase pertenece cada documento no está en la carpeta
del CRM. Está, en cambio, en el **lote de presentación** (`modified_at`), que agrupa con
nitidez los escritos con sus documentos.

Dos herramientas existentes se descartaron por razones verificadas:

- **`bucket_override` (D11)** solo se consulta en el momento de escribir un documento nuevo.
  Sobre 69 ficheros ya en disco no hace nada.
- **`scripts/migrate_05crm_buckets.py`** trata `99_Otros` como bucket terminal
  (`KNOWN_BUCKETS`): un fichero ya depositado ahí es no-op. Sí sirve, y se usará, para el
  fallback `99_Sin categoria/487`.

## 2. Arquitectura

Tres piezas con una responsabilidad cada una:

### 2.1 `core/intake_manifest.py` — persistir el `doc_id` en la entrada canónica

`register(sha256, relative_path, *, source, **alias_details)` recibe hoy el `doc_id` dentro de
`alias_details`, pero **solo lo persiste si se crea un alias** — es decir, solo cuando el
documento es un duplicado de otro ya presente. Cuando el hash es nuevo (el caso normal: 62 de
los 70) el `doc_id` se descarta.

Consecuencia: el manifiesto sabe el `doc_id` de una copia duplicada pero no el de la copia
buena. `doc_id → ruta` es incontestable para la mayoría del expediente.

**Cambio:** al crear la entrada, persistir `doc_id`, `source` y `modified_at` en el propio
entry, junto a `primary_path`. Retrocompatible: las entradas antiguas sin esos campos siguen
siendo válidas y los adquieren en la siguiente pasada del pull (idempotente y barata —
verificado hoy: 70 documentos reconciliados en segundos, `documents_written: 0`).

**Resolución completa `doc_id` → ruta.** Una entrada canónica solo puede llevar **un** `doc_id`;
los demás documentos con el mismo contenido cuelgan como alias. El resolutor debe por tanto
buscar en **ambos sitios**: el `doc_id` del entry y los `doc_id` de sus `aliases`. Ambos
devuelven el `primary_path` cuando el alias no tiene copia física propia.

Es legítimo que **dos `doc_id` distintos resuelvan al mismo fichero de origen** — es el caso del
`TASA ORDINARIO` presentado dos veces (38060 y 39526, byte-idénticos). Si el letrado los asigna
a la misma carpeta, producen dos copias con nombre distinto (fechas de lote distintas), lo que
refleja fielmente que hubo dos presentaciones. Solo si el nombre final coincidiera se dispara la
puerta 3.

### 2.2 `core/procedimiento.py` (nuevo) — el cerebro

Puro sobre el árbol del caso, **sin red**. La fuente de qué documentos existen es el manifiesto
local, no el CRM: el intake trae, esto organiza. Así el módulo se testea sin mockear HTTP.

- `plan(case_id, expediente_id) -> PlanProcesal` — lee manifiesto + YAML y devuelve el diff.
- `apply(plan) -> ResultadoProcesal` — ejecuta y escribe el manifiesto procesal.

### 2.3 Dos artefactos, dos papeles — no dos índices

`05_Procedimiento` **ya tiene un índice humano**: `registrar_outputs.py` escribe
`<destino>/_index.md` con la tabla Fichero / Tipo / Perspectiva / Fecha / Fuentes / Estado,
append idempotente por fichero, y añade wikilinks a `## Navegación` de `00_Input/_caso.md`. Lo
usan `escritos-judiciales`, `cendoj-descarga` y `preparacion-litigio-civil`.

Un segundo índice generado por esta herramienta sería un competidor, no una mejora. El reparto:

| Artefacto | Papel | Público |
|---|---|---|
| `<carpeta>/_index.md` | **Índice de la carpeta**: qué hay, de qué tipo, de cuándo, en qué estado | El letrado |
| `05_Procedimiento/_MANIFIESTO_PROCESAL.json` | **Ledger de propiedad**: qué ficheros creó `apply` y por tanto qué puede destruir | La máquina |

`apply` **extiende `_index.md`** con las mismas columnas para los documentos que deposita
(`tipo` = fase procesal, `perspectiva` = `actora`/`demandada`/`juzgado` según de quién sea el
escrito, `fuentes` = `CRM:<doc_id>`), reutilizando el formato del helper en vez de duplicarlo. El
JSON no se le presenta a nadie: es contabilidad interna.

**Ficheros de control fuera del escaneo.** `_index.md`, `_MANIFIESTO_PROCESAL.json` y los
`_*.md`/`_*.json` de control nunca cuentan como «ajenos»: si contaran, la lista de alarma nacería
con ruido permanente y dejaría de servir. Se ignoran igual que `sala_maquina.inventariar` ignora
los suyos vía `_IGNORAR`.

### 2.4 Qué fichero se copia: el buscable, no el crudo

La sala de máquina **ya procesa los procesales**: `sala_maquina.inventariar()` recorre `00_Input`
recursivamente, así que los documentos de `05_CRM` ya tienen su PDF buscable y su espejo
Markdown en `01_Procesado/02_Sala de máquina/{01_OCR,03_MD}`.

La ruta de esa salida es **derivable, no hay que adivinarla**:
`slug = utils.output_slug(rel_path, sha256)` = `slugify(<stem>)__<sha256[:8]>`, y ambos datos
—`rel_path` y `sha256`— ya están en el manifiesto de intake. El PDF buscable vive en
`01_Procesado/02_Sala de máquina/01_OCR/<slug>.pdf`.

**Esta regla no es nueva: es el criterio que Nikolai ya cerró el 2026-07-19** para la sala de
lectura (`docs/MEJORAS_FUTURAS.md`, «Criterio de COPIA a la sala — CERRADO»): PDF nativo /
`.docx` / `.txt` / foto → **crudo**; PDF o imagen **escaneada** → **OCR**; email → MD legible +
adjuntos; y «**el MD suelto NUNCA sustituye a un documento visual**» (firmas, sellos, fotos,
tablas). Aquí se aplica el mismo criterio a la vista procesal, no se inventa otro. De su cuarta
regla se sigue, además, que el MD **no** acompaña al PDF en `05_Procedimiento` (§7).

**Regla de origen, de tres ramas y determinista:**

1. Si existe `01_OCR/<slug>.pdf` → se copia **ese**. Es la versión con capa de texto de un
   documento escaneado.
2. Si no existe pero el documento tiene MD con `ocr_quality` distinto de `sin_soporte` → se copia
   el crudo de `05_CRM`. La ausencia de artefacto en `01_OCR/` significa que OCRmyPDF no regeneró
   porque **el PDF ya traía texto**: el crudo ya es buscable.
3. Si el documento es **`sin_soporte`** (no hay MD ni OCR) → se copia el crudo **y se avisa**. Es un
   documento que el letrado puede abrir pero que ningún LLM puede leer. Ver el aviso abajo.

Así el letrado busca dentro del documento sin salir de la carpeta, que es el objetivo de toda la
pieza. El `sha256` que el ledger registra es el **del fichero copiado**, no el del crudo.

**De dónde sale la señal de fiabilidad.** Del **frontmatter de `03_MD/<slug>.md`**
(`sala_maquina._escribir_md`): `ocr_quality` (`ok`|`low`|`empty`), `ocr` (bool), `chars`,
`text_sha256`. La señal viaja EN el MD; **no** hay que parsear `_cobertura.md`. `plan` reporta los
documentos asignados cuyo `ocr_quality` no sea `ok`, y los `sin_soporte` aparte: no bloquea —el
fichero se copia igual y el letrado lo puede leer— pero deja constancia de que su texto no es
explotable.

**`01_OCR/` no se universaliza.** Es tentador hacer que contenga un PDF buscable de *todos* los
documentos para tener una sola regla; **no se hace**, y queda escrito aquí para que nadie lo
«arregle» más adelante: (a) `01_OCR/` es un **artefacto de custodia** — significa «a este documento
le añadimos una capa de texto»; llenarlo de copias idénticas al crudo destruye esa información, que
es relevante a efectos de prueba; (b) para los nativos (`.eml`, `.xlsx`, `.docx`) no existe PDF y
habría que sintetizarlo, añadiendo un paso y un riesgo de fidelidad; (c) duplicaría ~65 PDF por
caso en Drive. La capa universal es **`03_MD/`**, no `01_OCR/`.

**El hueco real: `sin_soporte`.** La capa universal solo es universal si `03_MD/` cubre todo, y hoy
no lo hace: `clasificar_ruta` manda a `sin_soporte` cualquier extensión fuera de `.pdf`, `_EXTS_IMAGEN`
y `_EXTS_NATIVO`. **`.doc` (Word binario) está fuera** —la lista tiene `.docx` y `.rtf` pero no
`.doc`— así que no tiene ni MD ni OCR. En el caso piloto son 2 de 69 ficheros, y uno es
**`ordinario_vuelta_comprador.doc`: la demanda del juicio ordinario**, que en el CRM existe *solo*
en ese formato, sin gemelo PDF. Cerrarlo es `MEJORAS #61` (conversión LibreOffice headless
`soffice --convert-to` aguas arriba de `clasificar_ruta`), **promovido a `PLAN.md` el 2026-07-27**
con este caso como disparador. **Dependencia:** la vista procesal funciona sin ese arreglo —copia el
crudo y avisa—, pero la preparación de la audiencia previa de W-02MA0R lo necesita.

**Orden de ejecución que esto impone:** la sala de máquina corre **antes** de la vista procesal.
Si se ejecuta al revés, la vista se llena de crudos sin capa de texto. `plan` lo avisa cuando la
sala de máquina no ha corrido para el caso (no hay `02_Sala de máquina/`), sin bloquear: el
resultado sigue siendo correcto, solo menos útil.

**Copia desactualizada tras un re-OCR.** Si la sala de máquina vuelve a correr y produce un
`01_OCR/<slug>.pdf` distinto, la copia en `05_Procedimiento` queda vieja y sería **silenciosamente
incorrecta**. Se detecta comparando el `sha256` del ledger con el del fichero de origen vigente; si
difieren, el documento entra en `copiar` y se sobrescribe. No se añade un tipo de acción nuevo: una
copia desactualizada es una copia pendiente.

### 2.5 `scripts/procedimiento.py` — CLI

Subcomandos `plan` y `apply`, patrón ya establecido en el repo (`sala_maquina`,
`migrate_05crm_buckets`). `plan` no escribe nada salvo, si se le pide, el YAML inicial.

## 3. Contrato del mapping

`05_Procedimiento/_mapa_procesal.yaml`:

```yaml
version: 1
expediente_crm: '487'
carpetas:
  "01_Monitorio - Demanda y documentos":
    - {origen: crm, doc_id: '33428', orden: '00',   descripcion: demanda_monitorio}
    - {origen: crm, doc_id: '33435', orden: 'D-02', descripcion: contrato_mediacion}
  "03_Ordinario - Demanda y documentos":
    # Caso en régimen: la demanda la generó el despacho y ya está en la carpeta.
    - {origen: despacho, fichero: DEMANDA_W-02MA0R.docx}
  "05_Otros escritos":
    - {origen: crm, doc_id: '35653', orden: '2025-10-16', descripcion: decreto_admite_a_tramite_emplaza_ddo}
sin_asignar:
  - {doc_id: '41219', fichero: justif_presentacion_escr_pide_compa_telemat.pdf, lote: '2026-05-29T12:07'}
```

`origen` es obligatorio y solo admite `crm` o `despacho`. Cada rama exige sus campos y **la
clave de unicidad es distinta**, porque un escrito del despacho todavía no tiene `doc_id` en el
CRM:

| `origen` | Campos exigidos | Clave | Nombre en destino |
|---|---|---|---|
| `crm` | `doc_id`, `orden`, `descripcion` | `crm:<doc_id>` | `<orden>_<descripcion>.<ext>` (§3, abajo) |
| `despacho` | `fichero` | `despacho:<fichero>` | **el que ya tiene** — no se renombra |

El nombre final de un fichero `crm` es **`<orden>_<descripcion>.<ext>`**. Cada carpeta queda
internamente coherente: las de documentos ordenadas por número de documento del pleito, la de
escritos por fecha. Un escrito del despacho conserva su nombre y convive con esa numeración: es
el precio aceptado de no tocar ficheros que generó otra herramienta.

`plan` **propone** `orden` y `descripcion`:

- `orden` ← número de documento si el nombre del CRM lo lleva (`D 02` → `D-02`,
  `D 02-A` → `D-02A`, `002_DOC 1` → `D-01`).
- Si no lo lleva y la carpeta es una de las cuatro procesales (`01`–`04`), el documento es el
  **escrito rector** de esa carpeta y `orden` ← `00`. Si en una misma carpeta hubiera más de un
  candidato a escrito rector, ambos reciben `00` y la **puerta 3** (colisión de nombre final) se
  dispara para que el letrado desambigüe. No se elige por antigüedad ni por ninguna otra regla
  implícita.
- Si no lo lleva y la carpeta es `05_Otros escritos` —que no tiene escrito rector— `orden` ←
  fecha del lote (`AAAA-MM-DD`).
- `descripcion` ← slug del nombre del CRM, minúsculas, sin acentos ni signos.

`plan` **nunca propone la carpeta**. Esa es la decisión del letrado y va a `sin_asignar` hasta
que la tome.

## 4. Flujo

### 4.1 El diff y su aplicación

**`plan`** emite el diff completo:

| Categoría | Significado |
|---|---|
| `copiar` | Entrada `crm` sin fichero en destino, **o con una copia desactualizada** (el `sha256` del ledger no coincide con el del origen vigente tras un re-OCR — §2.4) |
| `mover` | Entrada `crm` con carpeta u `orden` distintos a los del manifiesto procesal |
| `registrar` | Entrada `despacho` presente en su carpeta y aún no inventariada. **No copia ni renombra** |
| `borrar` | En el manifiesto procesal, ya no en el YAML. Solo alcanza a entradas `crm`: un fichero del despacho nunca se borra, se desregistra |
| `sin_asignar` | En el manifiesto de intake para ese expediente, ausente del YAML |
| `ajenos` | Dentro de las cinco carpetas y no declarado en el YAML — se reportan, **no se tocan**. Son los candidatos naturales a `origen: despacho` |

**`apply`** ejecuta y escribe `05_Procedimiento/_MANIFIESTO_PROCESAL.json`:

```json
{"generado": "<ISO>", "version": 1, "expediente_crm": "487",
 "ficheros": {
   "01_Monitorio - Demanda y documentos/00_demanda_monitorio.pdf":
     {"origen": "crm", "doc_id": "33428", "sha256": "...",
      "origen_rel": "05_CRM/99_Sin categoria/487/demanda_monitorio_comprador.pdf"},
   "03_Ordinario - Demanda y documentos/DEMANDA_W-02MA0R.docx":
     {"origen": "despacho"}
 }}
```

Ese manifiesto es la frontera de lo que `apply` puede destruir, y **solo alcanza a las entradas
`crm`**: borrar un fichero registrado como `despacho` está prohibido por construcción — si sale
del YAML se desregistra y se queda donde está. Todo lo demás en `05_Procedimiento`
—`Jurisprudencia/`, notas, cualquier fichero no declarado— queda fuera de su alcance.

### 4.2 El mismo documento en dos procedimientos: se copia en las dos carpetas

En una reclamación que pasa por monitorio y, tras la oposición, por ordinario, buena parte de la
documental se aporta **dos veces**, con numeración distinta en cada pleito. Verificado sobre el
487: **69 ficheros físicos, 61 SHA-256 distintos** — siete documentos aparecen en más de un sitio.

| Documento | Monitorio | Ordinario | Además |
|---|---|---|---|
| Contrato de mediación | D 02 | D 02 | |
| Reconocimiento gestión honorarios | D 03 | D 06 | |
| Nota informativa Activa Assets | D 04 | D 07 | |
| Oferta de compra | D 05 | D 08 | **DOC 4 de la contestación de contrario** |
| Factura | D 07 «debida» | D 12 «errada» | |
| Requerimiento extrajudicial | D 08 | D 14 | |
| Decreto de admisión a trámite | — | — | archivado dos veces en el CRM |

**Decisión: el reparto es por `doc_id`, no por SHA.** Cada carpeta recibe su copia física con la
numeración de su propio pleito. Abrir `01_Monitorio - Demanda y documentos` da el bloque completo
tal como se presentó; abrir `03_Ordinario - Demanda y documentos`, el suyo. **El letrado lee un
procedimiento entero sin salir de su carpeta**, que es el requisito.

La deduplicación por contenido sería aquí un error de diseño, no un ahorro: colapsaría dos
aportaciones procesales distintas —con numeración, fecha y función distintas— en un solo fichero, y
obligaría a saltar entre carpetas para reconstruir un bloque. El coste real de no deduplicar en
este caso son siete PDF.

Consecuencia para el ledger: dos entradas del `_MANIFIESTO_PROCESAL.json` pueden compartir
`sha256` y `origen_rel` apuntando a rutas de destino distintas. Es legítimo y no debe tratarse como
colisión: la puerta 3 solo mira el **nombre final**.

## 5. Puertas de fallo

`apply` aborta, con la lista concreta de casos, si:

1. **`sin_asignar` no está vacío.** Decisión pendiente del letrado.
2. **Un `doc_id` del YAML no existe en el manifiesto de intake.** Mapping obsoleto respecto al
   crudo.
3. **Dos entradas producen el mismo nombre final.** Resuelve dos situaciones reales del 487: el
   `TASA ORDINARIO` duplicado (doc_id 38060 y 39526, byte-idénticos, un solo fichero en disco) y
   la segunda copia de la oposición al monitorio (39885, cinco meses posterior). No se
   desambiguan solas: se ponen delante del letrado.
4. **Falta en disco un fichero de origen.** Para una entrada `crm`, el crudo está incompleto y
   hay que re-ejecutar el intake antes.
5. **Falta el fichero de una entrada `despacho`** en la carpeta que declara. O no se ha generado
   todavía, o se movió a mano. La herramienta no lo busca por el árbol ni lo inventa.
6. **`origen` ausente o distinto de `crm`/`despacho`**, o falta el campo que esa rama exige
   (`doc_id` en `crm`, `fichero` en `despacho`).

Ninguna puerta escribe fuera de las cinco carpetas.

## 6. Tests

**Sobre `plan`** (manifiesto sintético, sin red): asignación completa sin diff; `sin_asignar` no
vacío bloquea; colisión de nombre final; `doc_id` fantasma; huérfano a borrar; re-ejecución
no-op; fichero ajeno reportado y no tocado.

**Sobre `origen: despacho`:** una entrada `despacho` se registra sin copiarse ni renombrarse;
deja de contarse como ajena; retirarla del YAML la desregistra **sin borrar el fichero**; y una
entrada `despacho` cuyo fichero no está en su carpeta dispara la puerta 5. Más el caso mixto: una
carpeta con entradas de los dos orígenes y una colisión entre el nombre de un fichero del
despacho y el nombre canónico de un documento del CRM.

**Sobre el arreglo del manifiesto:** `doc_id` persistido en la entrada canónica; entrada
antigua sin `doc_id` sigue resolviendo y lo adquiere al re-registrar.

**Sobre el origen buscable (§2.4):** con `01_OCR/<slug>.pdf` presente se copia ese y el `sha256`
del ledger es el suyo, no el del crudo; sin artefacto en `01_OCR/` se copia el crudo; un cambio del
`01_OCR/<slug>.pdf` tras un re-OCR reabre el documento como `copiar` y sobrescribe; sin
`02_Sala de máquina/` la herramienta avisa y sigue. **Tercera rama:** un documento sin MD ni OCR
(`.doc`, u otra extensión fuera de los tres conjuntos de `clasificar_ruta`) se copia crudo y se
reporta como `sin_soporte`, sin bloquear. Y la señal de fiabilidad se lee del **frontmatter del
MD**, no de `_cobertura.md`: un `ocr_quality` `low`/`empty` se reporta y el documento se copia igual.

**Sobre los artefactos (§2.3):** `_index.md` y `_MANIFIESTO_PROCESAL.json` **no** aparecen nunca en
`ajenos`; `apply` añade a `_index.md` una fila por documento depositado y no duplica filas al
re-ejecutar.

**Sobre el duplicado entre procedimientos (§4.2):** dos `doc_id` con el mismo SHA asignados a
carpetas distintas producen **dos ficheros**, uno en cada carpeta, con el nombre de su pleito; el
ledger admite dos entradas con igual `sha256` y distinto destino sin que salte la puerta 3.

**Regresión con datos reales del 487:** el mapping completo produce 9 / 5 / 15 / 12 / 29 y cubre
los 70 documentos exactamente una vez. Y sobre los siete SHA compartidos: cada carpeta procesal
queda con su bloque completo, de modo que el monitorio se puede leer entero sin abrir la del
ordinario.

## 7. Alcance

**Entra** (además de todo lo anterior): ampliar `DESTINOS_VALIDOS` de `registrar_outputs.py` con
las cinco carpetas. Hoy su lista blanca es `CASO_SUBDIRS` + `05_Procedimiento/Jurisprudencia`, de
modo que un escrito generado **no puede** registrarse en `03_Ordinario - Demanda y documentos`.
En el flujo de régimen (§1.1) ese es el camino normal, no una excepción.

**Queda fuera de v1:**

- Que `plan` proponga la carpeta (adivinar la fase procesal). La asignación es del letrado.
- Cualquier modificación de `00_Input/05_CRM`.
- **Los procesales no entran en la sala de lectura** (`01_Procesado/Sala lectura`). Decisión de
  Nikolai, y con dos razones: `05_Procedimiento` **ya es la sala de lectura del letrado** para la
  fase procesal, y la sala de lectura la monta una skill prompt-driven sobre `00_Input` con otra
  taxonomía (las categorías comerciales de E&V: activación, ofertas, arras, facturación…), que no
  describe un pleito. Duplicarlos allí daría dos vistas del mismo material compitiendo. **Hay que
  dejarlo escrito también en la skill `organizar-sala-lectura`**, o la próxima vez que se monte la
  sala de lectura de un caso con pleito volverán a colarse.
- Copiar el espejo Markdown junto al PDF. El MD es ayuda de máquina y duplicaría el número de
  ficheros en la carpeta de trabajo del letrado. Si se pide, la forma sería un `_texto/` por
  carpeta, opt-in.
- **La subida carpeta → CRM.** Es la otra mitad del flujo de §1.1 y es un proyecto propio, no un
  fleco de este: los endpoints están inventariados en el atlas (`POST /api/documents`,
  `POST /api/documents/single-document/import`,
  `GET /api/documents/presigned_urls/{service}/upload/{n}`) pero **el core solo lee** —
  `list_gdocu_docs_rest` y `download_document_rest`. Falta auth de escritura, el flujo de
  presigned upload, la elección de carpeta en el gestor documental, idempotencia por hash y el
  vínculo con el procurador. → `docs/MEJORAS_FUTURAS.md`.
- **El duplicado `.docx` / `.pdf` que el flujo de régimen va a crear.** Nuestra demanda sube al
  CRM, el CRM puede guardarla convertida (`POST /api/documents/convert/doc-to-pdf`), y un pull
  posterior la baja como documento nuevo. Mismo documento, dos ficheros, **SHA distinto por el
  cambio de formato**: ningún dedup por hash lo detecta, y acabaría como una entrada `crm` junto a
  la entrada `despacho` del original. En v1 el letrado lo verá y decidirá; la detección
  automática (por nombre, por par de formatos, o marcando en el mapa qué `doc_id` del CRM es el
  eco de qué fichero del despacho) se diseña cuando exista la subida.

## 8. Impacto en las skills del despacho

Revisión del cableado real (2026-07-27). Nueve skills afectadas, en cuatro grupos.

### 8.1 Cambian comportamiento

| Skill | Cambio |
|---|---|
| `organizar-sala-lectura` | Declarar que los documentos procesales **no** entran en `01_Procesado/Sala lectura` (§7). Sin esto se duplican la próxima vez que se monte la sala de lectura de un caso con pleito |
| `preparacion-audiencia-previa` | Hoy lee «la documental procesal del expediente» **sin ruta**: la tiene que buscar. Pasa a rutas deterministas — demanda en `03_Ordinario - Demanda y documentos`, contestación en `04_Ordinario - Contestacion`, monitorio en `01`/`02` |
| `preparacion-juicio-oral` | Igual: lee demanda y contestación y guarda en `05_Procedimiento` |
| `escritos-judiciales` | Su tabla de destinos manda todo a `05_Procedimiento` raíz. Con `DESTINOS_VALIDOS` ampliado (§7) puede depositar en la carpeta de fase. **Decisión abierta:** ¿destino por defecto la carpeta procesal, o preguntar al letrado? |

**Aviso a retirar.** `preparacion-audiencia-previa` afirma que «`05_Procedimiento` y el manifiesto
son convención nueva; FeesDefender (core) aún no la lee», y lo repite en
`references/manifiesto_y_registro.md`. Este diseño es precisamente lo que hace que el core la lea
y la escriba: si el aviso se queda, contradice al código.

### 8.2 Sincronización del helper (mecánico, pero el recuento importa)

`registrar_outputs.py` está replicado en **siete** skills: `cendoj-descarga`,
`contestacion-honorarios-art20-lau`, `escritos-judiciales`, `oposicion-alegacion-nulidad`,
`preparacion-audiencia-previa`, `preparacion-juicio-oral`, `preparacion-litigio-civil`.
`scripts/sync_skill_helpers.py` cubre esas siete exactas y `tests/test_skill_helpers_sync.py` lo
ejecuta en `--check` exigiendo copias byte-idénticas.

La verificación correcta tras ampliar `DESTINOS_VALIDOS` es `python scripts/sync_skill_helpers.py`
seguido de `--check` y del test, **no** una comprobación de hashes a mano.

### 8.3 Solo documentación

- `preparacion-litigio-civil`: su árbol describe `05_Procedimiento/ ← escritos generados`; ahora
  también recibe documental del CRM.
- `engel-volkers`: enumera la estructura del expediente sin la subdivisión procesal.

### 8.4 Decisiones abiertas

- **`organizar-sala-maquina`**: su paso 6 (handoff) sugiere `organizar-sala-lectura`. Como §2.4
  impone que la sala de máquina corra **antes** de la vista procesal, ese handoff es el sitio
  natural para sugerirla en casos con pleito. Pendiente de decisión de Nikolai.
- **`checkin-caso` / `checkout-caso`**: no cambian de comportamiento, pero los dos ficheros nuevos
  no tienen sitio en la taxonomía de merge de la biblioteca. `MERGE_EXCLUSIONS` no los captura
  (correcto: deben sincronizar) y `DERIVADOS_REGENERABLES` tampoco. Propuesta:
  `_mapa_procesal.yaml` es **maestro** —decisión del letrado— y va por la tabla de 3 vías como
  `identidades.yaml`; `_MANIFIESTO_PROCESAL.json` es **derivado regenerable** y va a «local gana».
  Se resuelve en `core/config.py`; las skills solo lo documentan.

### 8.5 No se tocan

`triaje-viabilidad`, `viabilidad-prerelleno`, `intake-expediente`, `exportar-correos-etiqueta`, la
lógica de `checkout-caso`/`checkin-caso`, y `contestacion-honorarios-art20-lau` /
`oposicion-alegacion-nulidad` más allá de la sincronización del helper: solo citan
`05_Procedimiento` raíz como destino de guardado, que sigue siendo válido.

## 9. Hallazgos colaterales (no son de este diseño)

Registrados aquí porque salieron al construirlo y no deben perderse:

1. **El intake durante un checkout pierde el pull state.** `00_Input/_caso.md` está en
   `MERGE_EXCLUSIONS`: ni baja en el checkout ni sube en el checkin. Cualquier `intake-judicial`
   ejecutado sobre una copia prestada escribe `sudespacho_expedientes`, `doc_ids` y `by_carpeta`
   en un fichero que el checkin descarta. Afecta también al checkout abierto de `W-02VND1`.
   → `docs/MEJORAS_FUTURAS.md`.
2. **`id_carpeta` 304 sin mapear.** Los 8 documentos del fallback son la demanda de monitorio y
   sus documentos. Añadir `"304": "Civil/1ª Instancia/Monitorio/Demanda"` a `CARPETA_ID_TO_PATH`
   beneficia a todo expediente con monitorio. **Pendiente de la doble verificación en la UI del
   CRM** antes de mapearlo.
3. **Sustantivo, para el letrado — dos identidades documentales.** Del cruce por SHA-256 de los 69
   ficheros (§4.2) salen dos que no son mera repetición de documental:
   - El `D 07 - FACTURA DEBIDA` del monitorio es **byte-idéntico** al `D 12 - FACTURA ERRADA
     23.595 EUROS` del ordinario. En el ordinario la factura correcta es la D 13 (25.410 €), que es
     la cuantía del expediente. O el monitorio se presentó sobre la factura equivocada, o uno de
     los dos nombres está mal puesto.
   - El `DOC 4 - COMPROMISO DE COMPRA CONDICIONADO AL PRECIO` que **aporta el contrario en su
     contestación** es byte-idéntico a nuestra `D 08 - OFERTA COMPRA TORRENT` (y a la `D 05 -
     OFERTA COMPRA` del monitorio). Mismo documento, dos calificaciones jurídicas enfrentadas.
   Las dos conviene tenerlas localizadas antes de la audiencia previa.
4. **Sustantivo, para el letrado:** falta el documento «D 01» en ambos bloques — el monitorio va
   de D 02 a D 08, el ordinario de D 02 a D 14. O no se subió al CRM, o hay un hueco frente a lo
   presentado en el juzgado.
5. **La escritura al gestor documental del CRM no existe en el core.** Los endpoints están
   inventariados (§7) pero `core/` solo lee. Es la mitad que falta del flujo de §1.1 y bloquea el
   régimen: sin ella, la demanda que generamos en la carpeta no llega al procurador por esta vía.
   → `docs/MEJORAS_FUTURAS.md`, con prioridad, porque es camino crítico y no mejora opcional.
