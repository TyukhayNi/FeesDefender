# Diseño — Vista procesal del expediente en `05_Procedimiento`

_Brainstorming Claude Code · FeesDefender · 2026-07-27_
_**v3.1 — §11 cerrada: no queda ninguna decisión abierta.** Incorpora el viaje de ida y vuelta del
flujo de régimen (§1.1, con `eco_crm`) y el hueco sin dueño de la documental numerada (§7)._
_**v3 — reescrita tras la revisión adversarial de Codex (veredicto NO SHIP, 25 hallazgos).**
Los 25 se aceptaron en sustancia, con seis ajustes de severidad y dos recortes de alcance; la
adjudicación hallazgo → sección está en §10. Informe y handoff:
`docs/superpowers/handoffs/2026-07-27-vista-procesal-codex-informe.md` y
`…-codex-review.md`._
_Origen: petición de Nikolai sobre el expediente judicial CRM **487** (caso `W-02MA0R`) —
«que en Procedimiento acabe la demanda de monitorio con documentos en una carpeta, en otra la
contestación al monitorio, en otra la demanda de juicio ordinario con documentos, en otro
contestación y en otra el resto de los escritos»._
_Precedentes: `docs/INTEGRACION_SUDESPACHO.md` §13 (árbol `05_CRM`), `PLAN.md`
`[SIGUIENTE-REORG-05CRM]` (buckets planos D5/D6), `docs/MEJORAS_FUTURAS.md` («Criterio de COPIA a
la sala — CERRADO por Nikolai 2026-07-19»)._

## 0. Estado de las decisiones (cerradas con Nikolai)

| Decisión | Resuelto |
|---|---|
| **Alcance** | Herramienta **reutilizable** en `core/` + CLI `plan`/`apply` + tests. No script puntual, no skill |
| **Dónde se construye la vista** | Solo en `05_Procedimiento`. **`00_Input/05_CRM` no se toca** |
| **Qué es la vista** | El **inventario de la fase procesal**, no una proyección del CRM. `origen: crm` o `origen: despacho` (§1) |
| **Identidad de los documentos CRM** | **Opción B (2026-07-27):** registro de **ocurrencias** nuevo y regenerable (`core/ocurrencias_crm.py`). **NO se modifica `core/intake_manifest.py`** — §2.1 |
| **Precedencia de fuentes** | **CRM > ocurrencias > manifiesto de intake.** El manifiesto queda **fuera de la ruta de confianza** de la vista: sigue siendo índice de contenido para el dedup y nada más |
| **Escritos propios** | Conservan el nombre que les puso `escritos-judiciales`. La herramienta **no renombra** lo que no ha creado |
| **Nomenclatura (solo `origen: crm`)** | Escrito rector `00_`, documentos con su numeración del pleito (`D-02_`), escritos sueltos por fecha de lote (`AAAA-MM-DD_`) |
| **Ubicación del mapping** | `05_Procedimiento/_mapa_procesal.yaml` |
| **Deriva (doc_id nuevos)** | Van a `sin_asignar:`; **`apply` aborta** mientras no esté vacío. Nunca se adivina la carpeta |
| **Qué fichero se copia** | Se decide desde **`_cobertura.json`** (método declarado), no desde la existencia de artefactos — §2.4 |
| **Documentos en los dos procedimientos** | Se copian en **ambas** carpetas, con la numeración de cada pleito. Reparto por `doc_id`, no por SHA (§4.2) |
| **`01_OCR/` no se universaliza** | Se mantiene, justificado por **semántica, fidelidad y coste** — no por «pérdida de custodia», que era un argumento sobreactuado (§2.4) |
| **Índice para el letrado** | `<carpeta>/_index.md`, con un **reconciliador propio** de filas `CRM:<doc_id>` (§2.3) |
| **Sala de lectura** | Los procesales **no** van a `01_Procesado/Sala lectura`, y la exclusión es **operativa** (por SHA/ocurrencia), no narrativa (§7, §8) |
| **Qué alimenta la vista** | **Lo que se presentó en el pleito**: documentos del CRM y escritos del despacho. **No** la materia prima de `00_Input` (Drive, WhatsApp, correo), que es la vista de «qué pasó» y vive en la sala de lectura |
| **Viaje de ida y vuelta (régimen)** | La carpeta es el **origen**: convertimos y OCRizamos ahí, subimos al CRM, y al bajar vuelve lo que ya teníamos. El eco se **declara** con `eco_crm`, no se detecta por huella (§1.1) |
| **Imágenes** | Con texto → PDF buscable; sin texto → original. **Sin ejercitar**: cero imágenes en el `05_CRM` del piloto (§11.1) |
| **`escritos-judiciales`** | **Pregunta la carpeta de fase** y escribe ahí. No puede deducir monitorio vs ordinario |
| **Override de cobertura** | Se declara en el mapa (`sin_cobertura_ok`), se registra en `_intake_log.jsonl` con actor |

## 1. El flujo real, en los dos sentidos

El CRM es **donde el despacho centraliza todos los documentos procesales**, y el canal por el que
llegan al procurador. `05_Procedimiento` es el banco de trabajo del letrado. Los documentos cruzan
en las dos direcciones:

| Fase | Dirección | Qué se mueve |
|---|---|---|
| Preparación de la demanda | **carpeta → CRM** | La demanda y sus documentos se generan en la carpeta y se suben al CRM |
| Vida del pleito | **CRM ← juzgado/contrario** | Contestación, documentos de contrario, decretos, cédulas, tasas |
| Preparación del juicio o de la audiencia previa | **CRM → carpeta** | Demanda y contestación juntas. La contestación siempre baja; la demanda solo si el caso es anterior a FeesDefender |

- **`origen: crm`** — el documento vive en `00_Input/05_CRM`. Se **copia** con nombre canónico.
- **`origen: despacho`** — lo generó `escritos-judiciales` y **ya está** en la carpeta. Se
  **registra**, no se copia ni se renombra.

Con `origen: despacho` los escritos propios quedan **inventariados** en vez de tolerados como
«ajenos»: la lista de ajenos recupera su sentido de alarma.

**Caso piloto W-02MA0R:** los 70 documentos son `origen: crm` (la demanda es anterior a
FeesDefender). La rama `despacho` no se ejercita aquí; se implementa porque es el camino de régimen.

### 1.1 El viaje de ida y vuelta: la carpeta es el origen (Nikolai, 2026-07-27)

En un caso con FeesDefender activo el recorrido de un documento propio es este:

1. La conversión del material bruto a PDF —una conversación de WhatsApp, un correo, una foto— se
   hace **en la carpeta del caso**, no en el CRM. Ahí es donde adquiere su capa de texto.
2. La demanda y sus documentos numerados **suben** al CRM, para el procurador y para centralizar.
3. Al preparar la audiencia previa o el juicio, **bajan** otra vez a la carpeta.
4. Pero **ya estaban ahí**: la carpeta fue el origen de la subida, y ya venían buscables.

Cuatro consecuencias de diseño:

**(a) El eco del CRM se declara, no se detecta.** Un documento propio existe por dos vías: el
fichero de la carpeta (nuestro, con su nombre) y el documento del CRM (con su `doc_id`) que vuelve
al bajar. Sin declararlo, la vista lo mostraría **dos veces**. La entrada `despacho` del mapa lleva
por eso un campo `eco_crm` con el `doc_id` del que es original (§3). No se intenta detectar por
huella: si el CRM reenvuelve el PDF al almacenarlo el SHA cambia y ninguna comparación automática lo
pillaría.

**(b) En régimen el intake es acotado, no `--full`.** Del CRM solo hace falta lo que no tenemos: la
contestación, los documentos de contrario, decretos, cédulas y tasas. `--full` es para los casos
anteriores a FeesDefender, como el piloto.

**(c) El original nuestro manda.** Para un documento que existe por las dos vías, el fichero que se
queda en la carpeta es **el nuestro** —es el que preparamos y presentamos—, y el `doc_id` del CRM es
el metadato que lo ata al pleito. La copia del CRM es un artefacto de tránsito.

**(d) El OCR se hace una vez, antes de subir.** Para esos documentos la sala de máquina deja de ser
requisito previo de la vista: llegan buscables de fábrica. Sigue siendo necesaria para lo que baja del
CRM sin capa de texto (lo del contrario y lo del juzgado).

**Y `sin_asignar` se convierte en la herramienta de trabajo del letrado:** lo que aparece ahí es, o
algo nuevo del juzgado o del contrario —se asigna a su carpeta—, o el eco de un fichero propio —se
declara con `eco_crm`—. No hay una tercera posibilidad.

### 1.2 El problema: el CRM no archiva por fase procesal

Dos procedimientos (monitorio y, tras la oposición, ordinario) y **70 documentos** en el gestor:

| `id_carpeta` | Label CRM | Docs | Bucket que le asigna hoy `resolve_bucket` |
|---|---|---|---|
| 306 | CIVIL | 38 | `99_Otros` |
| 307 | DEMANDA | 15 | `01_Demanda` |
| 304 | DEMANDA | 8 | *(sin mapear)* → `99_Sin categoria/487` |
| 1 | General | 5 | `99_Otros` |
| 312 | DOCUMENTOS | 2 | `99_Otros` |
| 303 | MONITORIO | 1 | `99_Otros` |
| 63 | Documentacion RGPD LOPD | 1 | `99_Otros` |

El grueso (38) está en un cajón genérico «CIVIL». **Ningún mapeo de `id_carpeta` desenreda eso**: la
fase no está en la carpeta del CRM. Sí está, en cambio, en el **lote de presentación**
(`modified_at`), que agrupa los escritos con sus documentos.

Cifras verificadas del piloto (Codex, 2026-07-27, contra el expediente): **70 `doc_id` lógicos, 69
ficheros físicos, 61 SHA-256 distintos, 65 PDF + 2 DOC + 2 RTF**. La última corrida del pull dio
**62 `dedup_skipped` + 8 `cross_source_overlap`, 0 fallos** — no «62 hashes nuevos», que era una
lectura errónea de la métrica en la v1 de este documento.

Dos herramientas existentes se descartaron por razones verificadas:

- **`bucket_override` (D11)** solo se consulta al escribir un documento nuevo. Sobre 69 ficheros ya
  en disco no hace nada.
- **`scripts/migrate_05crm_buckets.py`** trata `99_Otros` como bucket terminal: un fichero ya
  depositado ahí es no-op. Sí sirve para el fallback `99_Sin categoria/487`.

## 2. Arquitectura

Cuatro piezas: el registro de ocurrencias, el cerebro, el CLI, y la lista blanca de
`registrar_outputs`.

### 2.1 `core/ocurrencias_crm.py` (nuevo) — identidad de los documentos del CRM

**Por qué un registro nuevo y no un cambio en `intake_manifest`.** El manifiesto de intake está
indexado por SHA-256, con `primary_path` + `aliases`. Ese modelo **no puede representar dos
documentos distintos del CRM con el mismo contenido y la misma ruta**, y el caso piloto lo
demuestra: los `doc_id` 39526 y 38060 (`TASA ORDINARIO`, presentada dos veces) comparten SHA y
comparten `primary_path`, de modo que no se crea alias y **ninguno de los dos IDs queda
persistido**. Verificado además: **ninguna** de las 92 entradas canónicas del manifiesto del piloto
conserva `doc_id` ni `expediente_id`, y el pull idempotente **no** los rellena — el fichero no se
reescribió siquiera.

Se descartó reescribir `intake_manifest` (opción A) por alcance: lo consumen el pull del CRM, el
export de correo, los atomizadores de email y WhatsApp y el intake de Drive E&V, y obligaría a
migrar el manifiesto de todos los casos abiertos. Queda como refactor con su propio spec y su propio
disparador (§7).

**Contrato.** `00_Input/_ocurrencias_crm.json`:

```json
{
  "version": 1,
  "generado": "<ISO>",
  "ocurrencias": {
    "crm:487:36797": {
      "source": "crm",
      "expediente_id": "487",
      "doc_id": "36797",
      "filename": "ORDINARIO - VUELTA - COMPRADOR.doc",
      "modified_at": "2025-12-03T09:38:03.000+01:00",
      "id_carpeta": "307",
      "path": "05_CRM/01_Demanda/ordinario_vuelta_comprador.doc",
      "sha256": "…",
      "estado": "active"
    }
  }
}
```

Reglas:

- Clave `<source>:<expediente_id>:<doc_id>`. **El ámbito por expediente es parte de la clave**: un
  caso admite varios expedientes CRM y no deben mezclarse.
- **Varias ocurrencias pueden compartir `sha256` y `path`.** Es el caso de la tasa, y es legítimo.
- **Un `doc_id` tiene exactamente una ocurrencia `active`.** Si su contenido cambia, la anterior pasa
  a `estado: superseded` y se conserva; el histórico nunca se confunde con lo vigente.
- Lo **escribe el pull** (`pull_expediente_v2`), que es el único que sabe dónde depositó cada
  documento. Es **derivado y regenerable**: re-ejecutar el pull lo reconstruye, y el pull es
  idempotente y barato (70 documentos en segundos, verificado).
- **Nunca se resuelve por «primer match»** ni recorriendo el manifiesto.

**Precedencia declarada: CRM > ocurrencias > manifiesto de intake.** Si las ocurrencias discrepan
del `pull_state`, se regenera desde el CRM; no se corrige a mano.

**Consecuencia buscada:** `_intake_hashes.json` sale de la ruta de confianza de la vista. En el
piloto contiene 31 entradas cuya ruta no existe —y que además pertenecen a **otro expediente**, ver
§9.1— y esa contaminación **no puede envenenar una vista que no lo lee**.

Cambio mínimo en el pull: pasar `info.modified_at` y escribir el registro de ocurrencias. **No** se
toca el esquema de `intake_manifest`.

### 2.2 `core/procedimiento.py` (nuevo) — el cerebro

Puro sobre el árbol del caso, **sin red**. Lee ocurrencias, cobertura y el YAML del letrado;
devuelve un diff; lo aplica.

- `plan(case_id, expediente_id) -> PlanProcesal`
- `apply(plan) -> ResultadoProcesal`

### 2.3 Índice y ledger: dos artefactos, dos papeles

`05_Procedimiento` **ya tiene un índice humano**: `registrar_outputs.py` escribe
`<destino>/_index.md` (Fichero / Tipo / Perspectiva / Fecha / Fuentes / Estado) y añade wikilinks a
`## Navegación` de `_caso.md`. Lo usan siete skills.

| Artefacto | Papel | Público |
|---|---|---|
| `<carpeta>/_index.md` | **Índice de la carpeta** | El letrado |
| `05_Procedimiento/_MANIFIESTO_PROCESAL.json` | **Ledger de propiedad**: qué creó `apply` y qué puede tocar | La máquina |

**El `registrar()` completo del helper no sirve**, y no se usa: solo **añade** filas por nombre de
fichero (mover o borrar deja filas fantasma) y además escribe wikilinks en `_caso.md`, que aquí no
queremos. Se construye un **reconciliador propio** que:

- gestiona **solo** filas cuya columna `Fuentes` sea `CRM:<doc_id>`;
- actualiza, mueve y elimina esas filas por clave lógica, no por nombre;
- **preserva intactas** las filas del despacho y cualquier fila manual;
- **no** toca `## Navegación` de `_caso.md`;
- delimita su bloque con marcadores explícitos, para que el bloque manual y el generado sean
  distinguibles a ojo y por herramienta.

**Ficheros de control fuera del escaneo de ajenos.** `_index.md`, `_MANIFIESTO_PROCESAL.json`,
`_mapa_procesal.yaml` y cualquier `_*.md`/`_*.json` de control no cuentan nunca como ajenos: si
contaran, la lista de alarma nacería con ruido permanente.

### 2.4 Qué fichero se copia: lo dice la cobertura, no la existencia de artefactos

**El criterio no es nuevo.** Nikolai lo cerró el 2026-07-19 (`docs/MEJORAS_FUTURAS.md`, «Criterio de
COPIA a la sala — CERRADO»): PDF nativo / `.docx` / `.txt` / foto → **crudo**; PDF o imagen
**escaneada** → **OCR**; **email → MD atomizado + adjuntos originales** (el `.eml` es custodia, no
lectura); y «**el MD suelto NUNCA sustituye a un documento visual**». Aquí se aplica el mismo
criterio, **por clase documental**, no una regla única.

**La fuente de estado es `_cobertura.json`, no la presencia de ficheros.** Inferir «no hay
`01_OCR/` ⇒ el crudo ya tenía texto» es falso en tres escenarios reales: un OCR borrado, una
extracción por visión (que produce MD sin PDF buscable) y un estado idempotente obsoleto.
`_cobertura.json` persiste ya todo lo necesario: `metodo` (`pypdf`|`ocr`|`nativo`|`sin_soporte`|
`error`), `estado` (`ok`|`low`|`empty`|`sin_soporte`), `chars`, `ocr`, `sha256` **del origen**,
`parent_slug`, `parent_sha256`, `role`, `paginas` y `tipo`. Y `cobertura_desde_dicts` tolera claves
desconocidas, así que ampliarlo más adelante no rompe nada.

**Selector por clase documental** (la clase sale de `metodo` + extensión del origen):

| Clase | Se copia | Verificación exigida |
|---|---|---|
| PDF con texto (`metodo: pypdf`) | crudo | SHA del crudo == `cobertura.sha256` |
| PDF o imagen escaneada (`metodo: ocr`) | `01_OCR/<slug>.pdf` | el artefacto **debe existir** y su ruta derivarse de `slug`; si falta → **bloqueo** |
| Nativo textual `.docx`/`.rtf`/`.txt` (`metodo: nativo`) | crudo | SHA del crudo == `cobertura.sha256` |
| Email `.eml` | **MD atomizado + adjuntos**, no el `.eml` | resolución vía `email_atomize`; **fuera de v1** (§7) |
| Imagen **con** texto (`estado: ok`/`low`) | `01_OCR/<slug>.pdf` | nota en el índice si la calidad es `low` |
| Imagen **sin** texto (`estado: empty`) | crudo | es una foto de algo, no de una página: el PDF no aporta nada |
| `metodo: sin_soporte` | crudo **con aviso** | ni MD ni OCR: el letrado lo abre, ningún LLM lo lee |
| Sin cobertura para un documento soportado | — | **bloqueo**, salvo override explícito que registre «crudo no buscable» |

La ruta del artefacto OCR se **deriva** (`slug = utils.output_slug(rel_path, sha256)` →
`01_Procesado/02_Sala de máquina/01_OCR/<slug>.pdf`), pero eso es una **verificación**, no una
inferencia de estado: quien dice que hay OCR es `metodo`, y si el artefacto no está donde debe, se
bloquea en vez de degradar en silencio.

**Bundles.** Un bundle produce MD **por segmento**, no necesariamente un MD padre. Se resuelve y se
agrupa por **`parent_sha256`** —que la cobertura ya persiste— y la calidad del conjunto es **la peor
de sus segmentos**. Nunca se busca un MD padre por slug derivado.

**Buscabilidad: promesa acotada.** La heurística de suficiencia es **global** (`>100` caracteres y
`>40` char/página de media). En el piloto, **8 de 65 PDF la superan conteniendo páginas de menos de
40 caracteres**, cinco con al menos una página vacía, y dos escrituras de 74 páginas pasan con 38
páginas cada una bajo el umbral. Por tanto **este diseño no promete buscabilidad íntegra**: promete
«texto global suficiente» y **reporta la calidad declarada** (`estado`, `chars`). La detección por
página y su OCR selectivo es un cambio de la sala de máquina y sale como mejora propia (§9.2).

**Procedencia doble en el ledger.** Se guarda el SHA del **crudo** y el del **fichero copiado**, más
de qué se derivó. Sin eso no hay cadena de custodia del artefacto.

**`01_OCR/` no se universaliza.** Se mantiene la decisión, con la justificación corregida: (a)
**semántica** — `01_OCR/` significa «a este documento le añadimos capa de texto», y llenarlo de
copias idénticas al crudo borra esa distinción; (b) **fidelidad** — para los nativos (`.eml`,
`.xlsx`, `.docx`) no existe PDF y habría que sintetizarlo; (c) **coste** — duplicar los 65 PDF del
piloto son al menos otros 40.683.521 bytes en Drive. *No* se argumenta «pérdida de custodia»: la
custodia sobrevive mientras se conserven el original y sus hashes. La capa universal es `03_MD/`.

**El hueco de `sin_soporte`.** `clasificar_ruta` manda a `sin_soporte` toda extensión fuera de
`.pdf`, `_EXTS_IMAGEN` y `_EXTS_NATIVO`. **`.doc` está fuera** (la lista tiene `.docx` y `.rtf`): ni
MD ni OCR. En el piloto son 2 de 69, y uno es **`ordinario_vuelta_comprador.doc` (`doc_id` 36797):
la demanda del juicio ordinario**, que en el CRM existe *solo* así. Se cierra con `MEJORAS #61`
(LibreOffice headless), promovido a `PLAN.md` como `[SIGUIENTE-DOC-LIBREOFFICE]`.

**Transición de artefacto (`reemplazar`).** Cuando el origen vigente de una identidad lógica cambia
de clase —`.doc` → PDF de LibreOffice, crudo → OCR, OCR → crudo, o una regeneración de OCR con SHA
distinto— el destino cambia de bytes y **puede cambiar de extensión**. Se define una acción
**`reemplazar`** por `logical_key`, atómica, que verifica el SHA anterior, escribe el nuevo destino
con la **extensión real del artefacto** y retira el destino anterior. Sin esta acción, un `.doc`
convertido dejaría dos ficheros y un ledger inconsistente.

**Orden que impone:** la sala de máquina corre **antes**. En el piloto **no ha corrido** (`01_Procesado`
está vacío), de modo que hoy la vista se construiría íntegra desde crudo, incluidos 7 PDF sin texto y
los 2 `.doc`. `plan` **bloquea por documento** los soportados sin cobertura vigente, con override
explícito que queda registrado.

### 2.5 `scripts/procedimiento.py` — CLI

Subcomandos `plan` y `apply`, patrón de `sala_maquina` y `migrate_05crm_buckets`. `plan` no escribe
nada salvo con `--escribir-mapa`.

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
    - {origen: despacho, fichero: DEMANDA_W-02MA0R.docx}
    # Documento propio que ya viajó al CRM y ha vuelto: se declara su eco (§1.1a)
    - {origen: despacho, fichero: D-04_chat_whatsapp.pdf, eco_crm: '40725'}
sin_asignar:
  - {doc_id: '41219', fichero: justif_presentacion_escr_pide_compa_telemat.pdf, lote: '2026-05-29T12:07'}
```

| `origen` | Campos exigidos | Opcionales | Clave lógica | Nombre en destino |
|---|---|---|---|---|
| `crm` | `doc_id`, `orden`, `descripcion` | `sin_cobertura_ok` | `crm:<expediente_id>:<doc_id>` | `<orden>_<descripcion>.<ext del artefacto>` |
| `despacho` | `fichero` | `eco_crm` | `despacho:<fichero>` | **el que ya tiene** |

**`eco_crm`** declara que el `doc_id` indicado es la copia del CRM de este fichero propio. Efecto:
ese `doc_id` **no aparece en `sin_asignar` ni se copia**, y el ledger anota la correspondencia. Es el
mecanismo que evita ver la demanda dos veces en régimen (§1.1a).

`plan` **propone** `orden` y `descripcion`: número de documento si el nombre del CRM lo lleva
(`D 02` → `D-02`, `D 02-A` → `D-02A`, `DOC 3` → `D-03`); `00` si no lo lleva y la carpeta es una de
las cuatro procesales (escrito rector); la fecha del lote si la carpeta es `05_Otros escritos`. Si
dos entradas de una carpeta reclaman `00`, **ambas lo reciben** y la colisión de nombre final lo pone
delante del letrado: no se elige por antigüedad ni por ninguna regla implícita. `plan` **nunca**
propone la carpeta.

### 3.1 Validación del mapping

Se rechaza, con la entrada concreta señalada:

- carpeta fuera de las cinco de la lista blanca;
- `origen` ausente o distinto de `crm`/`despacho`; falta del campo que su rama exige;
- **clave lógica duplicada** (`crm:<exp>:<doc_id>` o `despacho:<fichero>`);
- `fichero` que no sea un **basename** (contiene separadores de directorio);
- **traversal** o cualquier ruta que, resuelta, escape de `05_Procedimiento/<carpeta>/`;
- ruta absoluta;
- **nombres reservados de Windows** (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`);
- puntos o espacios finales en el nombre;
- **colisión tras `casefold()`** (Windows no distingue mayúsculas: `Demanda.pdf` y `demanda.pdf` son
  el mismo fichero);
- destino que sea **symlink o reparse point**;
- segmento o ruta absoluta que exceda el límite (§3.2).

### 3.2 Longitud de ruta

`descripcion` se propone truncada a 60 caracteres, pero **60 no es una garantía**: en el piloto la
ruta proyectada llega a **248 caracteres** con `D-99A_<60>.docx` y a **253** con fecha en la carpeta
más larga, sobre un límite práctico de 259 — seis caracteres de margen. Y el expediente **ya
contiene** una ruta local de **301 caracteres** (346 bajo la raíz de Drive), verificado, de modo que
la cadena de herramientas ya depende de soporte de rutas largas.

Por tanto: **preflight dinámico** de cada ruta absoluta y de cada segmento, con **truncado con
sufijo hash estable** cuando no quepa. No se confía en un tope fijo aplicado solo a `descripcion`.

## 4. Flujo

### 4.1 Puerta de integridad, diff y aplicación

**Antes del diff**, `plan` cruza: `pull_state.documents_total_crm`, `pull_state.doc_ids`, las
ocurrencias `active`, las rutas existentes en disco, los SHA actuales y los errores del último pull.

`plan` emite:

| Categoría | Significado |
|---|---|
| `copiar` | Entrada `crm` sin fichero en destino |
| `reemplazar` | El origen vigente cambió de bytes, de clase o de extensión (§2.4) |
| `mover` | Entrada `crm` con carpeta u `orden` distintos a los del ledger |
| `registrar` | Entrada `despacho` presente en su carpeta y no inventariada. **No copia ni renombra** |
| `borrar` | En el ledger, ya no en el YAML. **Solo entradas `crm`** |
| `desregistrar` | Entrada `despacho` que sale del YAML: se retira del inventario, **el fichero se queda** |
| `sin_asignar` | Ocurrencia `active` del expediente ausente del YAML **y no declarada como `eco_crm`** de ninguna entrada `despacho` |
| `avisos` | Calidad `low`/`empty`, `sin_soporte`, override de cobertura, sala de máquina no ejecutada |
| `ajenos` | Fichero no declarado dentro de las cinco carpetas — se reporta, **no se toca** |

**`apply` es transaccional**, en este orden: (1) preflight completo —incluida la puerta de propiedad
de §5— sobre todas las operaciones; (2) copia a temporales **en el mismo volumen**; (3) verificación
de tamaño y SHA de lo escrito; (4) reemplazos y movimientos atómicos; (5) borrados **al final**; (6)
ledger escrito atómicamente como **último commit**. **Un diff vacío produce cero escrituras**,
incluido el campo `generado` del ledger. *Fuera de v1:* journal y recuperación automática tras fallo
parcial — se documenta cómo re-ejecutar `plan` para reconciliar, que con el ledger como último commit
es determinista.

Ledger `05_Procedimiento/_MANIFIESTO_PROCESAL.json`, por destino:

```json
{"logical_key": "crm:487:36797",
 "origen": "crm",
 "raw_path": "05_CRM/01_Demanda/ordinario_vuelta_comprador.doc",
 "raw_sha256": "…",
 "source_kind": "converted",
 "source_path": "01_Procesado/02_Sala de máquina/01_OCR/<slug>.pdf",
 "source_sha256": "…",
 "destination_sha256": "…"}
```

### 4.2 El mismo documento en dos procedimientos: se copia en las dos carpetas

Verificado sobre el 487: **69 ficheros físicos, 61 SHA distintos** — siete grupos repetidos (seis
pares y un triplete).

| Documento | Monitorio | Ordinario | Además |
|---|---|---|---|
| Contrato de mediación | D 02 | D 02 | |
| Reconocimiento gestión honorarios | D 03 | D 06 | |
| Nota informativa Activa Assets | D 04 | D 07 | |
| Oferta de compra | D 05 | D 08 | **DOC 4 de la contestación de contrario** |
| Factura | D 07 «debida» | D 12 «errada» | |
| Requerimiento extrajudicial | D 08 | D 14 | |
| Decreto de admisión a trámite | — | — | archivado dos veces en el CRM |

**El reparto es por `doc_id`, no por SHA.** Cada carpeta recibe su copia con la numeración de su
pleito: **el letrado lee un procedimiento entero sin salir de su carpeta**, que es el requisito.
Deduplicar por contenido sería un error de diseño, no un ahorro: colapsaría dos aportaciones
procesales con numeración, fecha y función distintas. El coste son siete PDF.

Consecuencia para el ledger: dos entradas pueden compartir `raw_sha256` y `raw_path` con destinos
distintos. Es legítimo; la puerta de colisión mira solo el **nombre final**.

## 5. Puertas de fallo

`apply` aborta, con la lista concreta de casos:

**Integridad de las fuentes**

1. Registro de ocurrencias **ausente, corrupto o de versión desconocida**. Un error de carga
   **nunca** se convierte en `{}` ni en «cero documentos».
2. Falta una ocurrencia para un `doc_id` del `pull_state`, o hay ocurrencias `active` fuera del
   `pull_state`.
3. Un `doc_id` con más de una ocurrencia `active`, o histórico sin marcar `superseded`.
4. Ruta de origen ausente en disco.
5. Documento soportado **sin cobertura vigente**, o artefacto declarado por `metodo` y **ausente**
   (§2.4), salvo override explícito registrado.

**Decisión del letrado**

6. `sin_asignar` no vacío.
7. Una entrada `despacho` cuyo fichero no está en la carpeta que declara.
7-bis. Un `eco_crm` que apunta a un `doc_id` **sin ocurrencia `active`** en el expediente, o a uno
   que **ya está asignado** como entrada `crm` (sería el mismo documento por dos vías declaradas).

**Contrato del mapa**

8. Cualquiera de las validaciones de §3.1.
9. Dos entradas que producen el **mismo nombre final** (cubre el `TASA ORDINARIO` duplicado y la
   segunda copia de la oposición al monitorio).

**Propiedad del destino** — «está en el ledger» **no basta** para destruir. Antes de `mover`,
`borrar` o `reemplazar`:

10. el destino debe **existir**;
11. debe ser **fichero regular**, no symlink ni reparse point;
12. su **SHA actual** debe coincidir con el `destination_sha256` del ledger — si el letrado sustituyó
    el fichero a mano, se aborta;
13. un destino existente **no registrado** se trata como ajeno y aborta;
14. un fichero con `origen: despacho` **nunca** entra en una operación destructiva.

Ninguna puerta escribe fuera de las cinco carpetas.

## 6. Tests

**Identidad y ocurrencias:** dos `doc_id` con mismo SHA y mismo path (la tasa); dos `doc_id` con
mismo SHA y rutas distintas; un `doc_id` cuyo contenido cambia (anterior a `superseded`); ocurrencias
de dos expedientes en el mismo caso, sin mezclarse.

**Integridad:** registro corrupto; registro con rutas ausentes; `pull_state` con IDs sin ocurrencia;
ocurrencia `active` fuera del `pull_state`.

**Cobertura y origen:** `metodo: pypdf` → crudo; `metodo: ocr` → artefacto, y **bloqueo** si falta;
`metodo: sin_soporte` → crudo con aviso; sin cobertura → bloqueo, y override que lo registra; bundle
resuelto por `parent_sha256` con la peor calidad de sus segmentos; MD por visión sin PDF buscable.

**Transiciones:** crudo → OCR; `.doc` → PDF con **cambio de extensión**; regeneración de OCR con SHA
distinto; OCR → crudo.

**Propiedad:** destino sustituido a mano tras escribirse el ledger; destino ajeno con el nombre
canónico; intento de borrado sobre un fichero `despacho`.

**Mapa:** traversal; nombre reservado de Windows; colisión `casefold`; `fichero` con directorios;
clave lógica duplicada; ruta que excede el límite y su truncado con sufijo hash.

**Transacción e idempotencia:** re-ejecución sin cambios con **cero escrituras**; fallo a mitad de
`apply` y reconciliación por `plan`.

**Índice:** movimiento y borrado con reconciliación correcta de `_index.md`, preservando filas del
despacho y sin tocar `## Navegación`.

**Biblioteca:** conflicto de mapa durante el checkin sin subir ledger ni PDF; borrado remoto del
ledger sin resurrección.

**Regresión del piloto:** el reparto 9/5/15/12/29 **queda pendiente de validación** hasta incorporar
un fixture anonimizado con los 70 `doc_id` (§11). No se afirma como verificado.

## 7. Alcance

**Entra:** ampliar `DESTINOS_VALIDOS` de `registrar_outputs.py` con las cinco carpetas, para que un
escrito generado se registre en su fase (camino normal del flujo de §1).

**Queda fuera de v1:**

- Que `plan` proponga la carpeta. La asignación es del letrado.
- Cualquier modificación de `00_Input/05_CRM`.
- **La reescritura de `intake_manifest` al modelo de ocurrencias** (opción A). Disparador para
  reabrirla: que una segunda fuente necesite ocurrencias — el candidato natural es la subida
  carpeta → CRM, que tendrá que reconciliar lo que subimos con lo que el CRM devuelve.
- **La preparación de la documental numerada.** En el flujo de régimen (§1.1) la carpeta es el
  origen, pero **hoy nada produce el `D-04_chat_whatsapp.pdf`**: `escritos-judiciales` genera el
  escrito, no sus documentos; la sala de máquina convierte y OCRiza pero deja el resultado en
  `01_Procesado/02_Sala de máquina`, sin numerar y sin condición de documento del pleito. El salto de
  «material bruto de `00_Input`» a «documento numerado listo para aportar» es **manual** y no tiene
  dueño. Esta pieza lo acepta sin problema como `origen: despacho`, pero alguien tiene que ponerlo.
  Es un proyecto propio, con su propia decisión sobre quién numera y con qué criterio. →
  `MEJORAS_FUTURAS.md`.
- **La subida carpeta → CRM.** Es la otra mitad del flujo de §1 y un proyecto propio: los endpoints
  están inventariados (`POST /api/documents`, `/api/documents/single-document/import`,
  `GET /api/documents/presigned_urls/{service}/upload/{n}`) y **el cliente documental de `core` solo
  lee** —`list_gdocu_docs_rest`, `download_document_rest`—, aunque otros módulos de `core` ya
  escriben en el CRM con `x-api-key` (`sudespacho_create.py`, `sudespacho_relations.py`). Lo que
  falta es el flujo documental, no la autenticación. → `MEJORAS_FUTURAS.md`.
- **El duplicado `.docx`/`.pdf`** que el flujo de régimen creará: nuestra demanda sube, el CRM puede
  guardarla convertida, y un pull posterior la baja como documento nuevo con **SHA distinto** por el
  cambio de formato. Ningún dedup por hash lo detecta. En v1 el letrado lo ve y decide.
- **La resolución de emails** (`.eml` → MD atomizado + adjuntos). El criterio está cerrado pero
  requiere entrar en `email_atomize`; el piloto no tiene emails en el CRM.
- **Detección de texto por página** y OCR selectivo: cambio de la sala de máquina (§9.2).
- Copiar el espejo Markdown junto al PDF. El MD es ayuda de máquina y el criterio del 2026-07-19 dice
  que no sustituye a un documento visual.
- **Los procesales no entran en la sala de lectura** (`01_Procesado/Sala lectura`). Y la exclusión
  debe ser **operativa**: `organizar-sala-lectura` lee todo `00_Input`, así que se excluye por las
  **ocurrencias y los SHA crudos** del mapa, no con una instrucción narrativa; y solo se retiran
  derivados cuya trazabilidad acredite que son de esta vista.

## 8. Impacto en las skills

**Doce** skills afectadas, no nueve.

### 8.1 Cambian comportamiento (6)

| Skill | Cambio |
|---|---|
| `organizar-sala-lectura` | Exclusión **operativa** de los procesales por ocurrencia/SHA (§7) |
| `preparacion-audiencia-previa` | Hoy lee «la documental procesal» **sin ruta**. Pasa a rutas deterministas: demanda en `03_Ordinario`, contestación en `04_Ordinario`, monitorio en `01`/`02`. **Y hay que retirar su aviso** de que «FeesDefender (core) aún no lee `05_Procedimiento`», repetido en `references/manifiesto_y_registro.md`: este diseño lo invalida |
| `preparacion-juicio-oral` | Igual: lee demanda y contestación, guarda en `05_Procedimiento` |
| `escritos-judiciales` | Con `DESTINOS_VALIDOS` ampliado, **pregunta la carpeta de fase y escribe ahí** (§11.2). No puede deducir monitorio vs ordinario: es conocimiento del caso |
| `contestacion-honorarios-art20-lau` | **Reclasificada**: lee la documental del pleito, no es solo sincronización de helper |
| `oposicion-alegacion-nulidad` | **Reclasificada**: idem |

### 8.2 Handoff

`organizar-sala-maquina` sugiere `organizar-sala-lectura` al terminar. Cuando el caso tiene pleito
debe sugerir **la vista procesal antes** que la sala de lectura.

### 8.3 Sincronización del helper (mecánico)

`registrar_outputs.py` está replicado en **siete** skills: `cendoj-descarga`,
`contestacion-honorarios-art20-lau`, `escritos-judiciales`, `oposicion-alegacion-nulidad`,
`preparacion-audiencia-previa`, `preparacion-juicio-oral`, `preparacion-litigio-civil`.
`scripts/sync_skill_helpers.py` cubre esas siete y `tests/test_skill_helpers_sync.py` las verifica en
`--check`. La verificación correcta es esa, no comparar hashes a mano.

### 8.4 Solo documentación

`preparacion-litigio-civil`: su árbol describe `05_Procedimiento/ ← escritos generados`; ahora también
recibe documental del CRM.

**`engel-volkers` no se toca**: enumera las raíces del expediente y no necesita replicar el árbol
interno.

### 8.5 Biblioteca: mapa, ledger y ficheros son una unidad de merge

No cambian de comportamiento, pero los artefactos nuevos necesitan sitio en la taxonomía de
`core/config.py`, y **no pueden sincronizarse por separado**:

- `_mapa_procesal.yaml` es **maestro** (decisión del letrado) → tabla general de 3 vías, como
  `identidades.yaml`.
- `_MANIFIESTO_PROCESAL.json` y `_ocurrencias_crm.json` son **derivados regenerables**.
- **Grupo de dependencia:** un conflicto en el mapa **bloquea la subida** del ledger y de los PDF de
  la vista. El ledger solo se regenera después de aceptar una versión concreta del mapa.
- **`Drive ausente + baseline presente` debe ser conflicto**, no `COPY_LOCAL`: si no, un derivado
  borrado en Drive resucita desde local.

## 9. Hallazgos colaterales

### 9.1 Contaminación entre expedientes (incidente, no defecto de diseño)

`00_Input/_intake_hashes.json` del caso `W-02MA0R` contiene 92 entradas, de las que **solo 61 tienen
`primary_path` existente**. Las 31 restantes **no son histórico de este caso: apuntan a documentos de
`BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU`** — `expose_ingles_calle_roser_39`,
`oposicion_demanda_calle_roser_articulo_20_lau`, una factura con nombre de pila de una persona — y
usan rutas de bucket `02_Contestacion/` que en este caso **no existe**.

Es la **cuarta recurrencia** del patrón «documentos de otros casos colados», cuyo remedio establecido
por Nikolai es **borrar, no cuarentena**. Requiere tarea propia: averiguar el origen (manifiesto
sembrado desde otro caso, o pull con `case_id` equivocado), comprobar si el caso Roser perdió
entradas, y sanear. **Este diseño lo neutraliza para la vista** al sacar el manifiesto de la ruta de
confianza (§2.1), pero no lo arregla.

### 9.2 Para `MEJORAS_FUTURAS.md`

- **Detección de texto por página** y OCR selectivo en la sala de máquina: 8 de 65 PDF del piloto
  pasan la heurística global con páginas ciegas; dos escrituras de 74 páginas tienen 38 cada una bajo
  el umbral.
- **Métricas del pull**: separar `physical_files_written`, `overlap_copies_written` y
  `bytes_written`. `documents_written: 0` **no** significa «cero efectos físicos» — en la corrida del
  2026-07-27, con el caso prestado, el guard desvió **8 PDF y 4.997.915 bytes** a
  `_pendiente_checkin` mientras la métrica decía cero.
- **El intake durante un checkout pierde el pull state**: `00_Input/_caso.md` está en
  `MERGE_EXCLUSIONS`; lo que se escriba en él durante un préstamo lo descarta el checkin. Afecta
  también al checkout abierto de `W-02VND1`.
- **Puntero obsoleto**: el texto humano de `_caso.md` sigue diciendo
  `expedientes_judiciales ID 487 → 00_Input/sudespacho_487/`; los documentos están en
  `00_Input/05_CRM`.

### 9.3 Sustantivo, para el letrado

- Falta el documento **«D 01»** en los dos bloques: el monitorio va de D 02 a D 08, el ordinario de
  D 02 a D 14. O no se subió al CRM, o hay un hueco frente a lo presentado en el juzgado.
- **Dos identidades documentales** del cruce por SHA: el `D 07 - FACTURA DEBIDA` del monitorio es
  byte-idéntico al `D 12 - FACTURA ERRADA 23.595 EUROS` del ordinario (la correcta es la D 13, 25.410 €,
  que es la cuantía); y el `DOC 4 - COMPROMISO DE COMPRA CONDICIONADO AL PRECIO` que **aporta el
  contrario** es byte-idéntico a nuestra `D 08 - OFERTA COMPRA`. Conviene tenerlas localizadas antes
  de la audiencia previa.

## 10. Adjudicación de la revisión adversarial

Los 25 hallazgos se aceptan en sustancia. Seis ajustes de severidad y dos recortes de alcance.

| ID | Codex | Adjudicado | Resuelto en |
|---|---|---|---|
| H1 | BLOQ | Acepto BLOQ | §2.1 (opción B: registro de ocurrencias) |
| H2 | BLOQ | Acepto, ALTA | §2.1 (`expediente_id` en la clave; `modified_at` desde el pull) |
| H3 | ALTA | Acepto, **sube a BLOQ** | §2.1 (se elimina la promesa de backfill: no se toca el manifiesto) |
| H4 | BLOQ | Acepto y **amplío** | §2.1 (precedencia) + §9.1 (incidente) |
| H5 | BLOQ | Acepto | §5.1 |
| H6 | BLOQ | Acepto | §5.10-14 |
| H7 | BLOQ | Acepto, ALTA | §3.1 |
| H8 | BLOQ | **Acepto parcial**, ALTA | §4.1 (transaccional sin journal) |
| H9 | BLOQ | Acepto, ALTA | §2.4 + §5.5 (bloqueo por documento con override) |
| H10 | BLOQ | Acepto | §2.4 (estado desde `_cobertura.json`) |
| H11 | ALTA | Acepto | §2.4 (bundles por `parent_sha256`) |
| H12 | ALTA | Acepto | §2.4 (promesa acotada) + §9.2 (remedio) |
| H13 | ALTA | Acepto | §2.4 (selector por clase documental) |
| H14 | MEDIA | Acepto | §2.4 (justificación corregida) |
| H15 | BLOQ | Acepto | §2.4 + §4.1 (acción `reemplazar`) |
| H16 | BLOQ | Acepto | §8.5 |
| H17 | MEDIA | Acepto, **sube a ALTA** | §9.2 |
| H18 | ALTA | Acepto | §2.3 (reconciliador propio) |
| H19 | ALTA | Acepto, **baja a MEDIA** | §3.2 |
| H20 | MEDIA | Acepto | §8 (doce skills, dos reclasificadas) |
| H21 | ALTA | Acepto | §7 (exclusión operativa) |
| H22 | MEDIA | Acepto | §1.1 |
| H23 | MEDIA | Acepto | §6 (pendiente de fixture) |
| H24 | BAJA | Acepto | pendiente: `PLAN.md:181` |
| H25 | BAJA | Acepto | §7 |

**Cautela sobre el informe:** declara «177 pruebas pasadas, 3 omitidas» como regresión del
repositorio; la suite real son ~2213 funciones de test en 156 ficheros. Nada que dependa de haber
ejecutado la suite queda verificado por esa revisión.

## 11. Decisiones cerradas (2026-07-27) — no queda ninguna abierta

1. **Imágenes.** Regla: imagen **con** texto → PDF buscable, con nota si la calidad es `low`; imagen
   **sin** texto → el original. Pero **fuera de alcance real**: de los 69 ficheros de `05_CRM` del
   piloto, **cero son imágenes** (65 PDF, 2 DOC, 2 RTF). Los `.jpg` viven en Drive, WhatsApp y
   correo, que es **materia prima** de `00_Input`, no documental del pleito. La regla queda escrita y
   **sin ejercitar**, para que haya respuesta el día que aparezca una imagen en el CRM.
2. **Destino de `escritos-judiciales`.** **Pregunta la carpeta de fase y escribe ahí.** No puede
   deducirla: conoce el `tipo` (demanda, contestación, recurso) pero no si el pleito es monitorio u
   ordinario, que es conocimiento del caso. Con `DESTINOS_VALIDOS` ampliado, `registrar_outputs` la
   anota en el `_index.md` de esa carpeta. Un solo sitio, sin movimientos posteriores: `apply` nunca
   tiene que mover un fichero del letrado.
3. **Fixture del piloto.** **Se construye**, con los 70 `doc_id`, y con **pasada de PII previa** —al
   menos un nombre de fichero lleva el nombre de pila de una persona, que va sustituido por
   `<PARTICULAR>`. Es el test de regresión de toda la pieza y deja registrada de forma durable la
   asignación aprobada. Hasta que exista, el reparto 9/5/15/12/29 queda como **pendiente de
   validación** (§6).
4. **Override de cobertura.** Se **declara** en la entrada del mapa (`sin_cobertura_ok: true`) y se
   **registra** al ejercerse en `_intake_log.jsonl` con el actor de `intake_log.get_actor()`. El
   ledger no participa —nadie lo edita a mano— y el log no puede ser donde se autoriza: es
   append-only y su papel es dar fe, no conceder permisos.

### 11.1 Qué garantiza la vista, y qué no

**Garantiza:** que **nada que exista se queda fuera en silencio.** La puerta de `sin_asignar` impide
que `apply` corra mientras haya un documento del expediente sin carpeta, y `05_Otros escritos` es el
cajón que recoge todo lo procesal que no es un escrito rector con sus documentos. Y garantiza el
agrupamiento por carpetas autocontenidas en los dos tipos de caso:

| Bloque | Caso anterior a FeesDefender | Caso en régimen |
|---|---|---|
| Demanda monitorio + documentos | del CRM | de la carpeta (propia) |
| Oposición al monitorio + documentos | del CRM | del CRM (es del contrario) |
| Demanda ordinario + documentos | del CRM | de la carpeta (propia) |
| Contestación + documentos | del CRM | del CRM (es del contrario) |
| Resto de escritos | del CRM | mezcla: escritos propios + resoluciones del CRM |

**No garantiza tres cosas, y conviene decirlas:**

1. **Lo que nunca se subió al CRM no puede aparecer.** Ejemplo vivo en el piloto: **falta el «D 01»**
   en los dos pleitos (monitorio D 02–D 08, ordinario D 02–D 14). La carpeta queda completa respecto
   al CRM, no respecto al juzgado.
2. **En caso nuevo, los documentos numerados de la demanda propia hoy no los produce nadie** (§7). Se
   aceptan como `origen: despacho`, pero entran a mano hasta que exista esa pieza.
3. **Un documento aportado en los dos pleitos aparece en las dos carpetas** — siete casos en el
   piloto. Es deliberado (§4.2).

**Y un aviso de calidad, no de completitud:** en el piloto la demanda del ordinario es un `.doc` sin
texto explotable hasta que entre LibreOffice, hay 7 PDF sin capa de texto y 8 más con páginas ciegas.
Estarán todos en su carpeta y se podrán abrir; lo que no se podrá es buscar dentro de algunos hasta
que corra la sala de máquina.
