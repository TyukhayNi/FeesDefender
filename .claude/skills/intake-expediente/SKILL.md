---
name: intake-expediente
description: >-
  Deposita ficheros (de cualquier tipo y tamaño: PDFs, emails .eml, exports de
  WhatsApp .zip, transcripciones de entrevistas, fotos, vídeos) en la carpeta
  00_Input de un expediente FeesDefender del Drive, DIRIGIDO desde Claude
  (Cowork o Claude Code), y dispara la trazabilidad forense (evento upload_* en
  _intake_log.jsonl con hash SHA-256 por fichero). Usa el conector MCP
  expedientes-xl para todo lo que toca bytes (extraer/copiar/hashear server-side,
  sin que pasen por el modelo). Úsala cuando el usuario diga "sube esto al caso",
  "deposita este zip", "mete estos PDFs en el expediente", "ingesta este export
  de WhatsApp", "añade este email al caso". NO organiza la sala de lectura (eso
  es organizar-sala-lectura) NI valora viabilidad (triaje-viabilidad). NO procesa
  por fuente (MIME del email, OCR del PDF): eso es el pipeline local.
metadata:
  rol: input
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.1"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: experimental
  requires: []
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# intake-expediente

Deposita ficheros en un **lote** `00_Input/<AAAA-MM-DD>_<fuente>_<NN>/` de un expediente
del Drive, dirigido desde Claude, **con trazabilidad**. Todo lo que toca bytes va **server-side** por el conector
`expedientes-xl` (los bytes nunca pasan por el modelo). La trazabilidad (evento `upload_*`)
se construye con el helper puro `scripts/traza.py` y se escribe con `append_text`.

## Requisitos
- Conector MCP **expedientes-xl** disponible (Plan 1), acotado a la raíz del Drive del
  despacho. Si no está, no se puede depositar — avisa.
- El fichero a subir debe estar **ya en un disco que el conector alcanza** (déjalo en
  `…/EXPEDIENTES - TYUKHAY LEGAL/_ingest/`). Ficheros grandes NO viajan por el chat;
  los pequeños (< tope) pueden entrar por `write_file_base64`.

## Fuentes y destino (`00_Input/`)
`00_Input/` tiene dos formas de canal: **lotes de entrega** `<AAAA-MM-DD>_<fuente>_<NN>/`
(fuentes `whatsapp`, `email`, `manual`, `entrevista`; cada lote lleva `_manifiesto.yaml` con
`tipo_contenido` por ítem) y **cajones espejo** fijos `01_Drive EV/` y `05_CRM/` (sync
incremental). Los casos antiguos no migrados conservan los cajones `02_Whatsapp/`,
`03_Email/`, `04_Manual/`, `06_Entrevistas/`: leer AMBAS formas. La fuente de un fichero se
deriva de su primer segmento de ruta (espejo → lote → cajón legacy → raíz=manual).

**Esta skill CREA el lote:** el depósito dirigido resuelve el directorio
`<AAAA-MM-DD>_<fuente>_<NN>` (NN = siguiente al mayor existente ese día para esa fuente; lo
crea si no existe), deposita los ficheros **verbatim** dentro y escribe su
`_manifiesto.yaml`. Los cajones espejo (`01_Drive EV/`, `05_CRM/`) **NO** reciben depósitos
de esta skill, salvo el flujo CRM ya documentado (sync, no depósito dirigido). El evento
`upload_*` se elige por fuente: WhatsApp→`upload_whatsapp`, email→`upload_email`,
entrevista→`upload_entrevista`, resto manual→`upload_manual`.

## Autonomía y gate único

La skill **no inserta preguntas de aclaración** ni pide permiso fichero a fichero. Tiene
**un solo gate humano**: la **propuesta de clasificación** (Paso 2). Tras tu OK ejecuta
todo de una pasada **sin más preguntas**.

- **Defaults (no se preguntan):** el original en `_ingest/` se **deja intacto** y se reporta
  (el crudo no se toca ni se borra; para retirarlo, pídelo aparte). Los **duplicados**
  (sha256 ya en el log) y los ficheros de **0 bytes** se **señalan en la propuesta** —antes
  de copiar—, no se pregunta a mitad de ejecución.
- **El diálogo de permiso por-llamada del conector MCP** (que en Cowork salta por cada tool)
  es ajuste del **cliente**, no de la skill: actívalo **una vez** ("Permitir siempre" en
  Claude Desktop/Cowork) para cero diálogos durante la ejecución.

## Procedimiento

1. **Prepara (sin copiar nada).** Resuelve el caso. Para cada fichero de `_ingest/` decide
   **fuente** (`whatsapp`/`email`/`manual`/`entrevista`; los espejos `01_Drive EV`/`05_CRM`
   NO se depositan desde aquí), **evento** `upload_*` y **nombre canónico**
   (`AAAA-MM-DD_descripcion`). Calcula su **sha256** con `hash_path` (server-side) para
   detectar **duplicados** (vs `00_Input/_intake_log.jsonl`, con `traza.is_duplicate`) y
   **0 bytes**. NO deposites todavía.
2. **(GATE) Propón la clasificación y ESPERA.** Tabla por fichero:
   `fichero → fuente → lote destino (00_Input/<AAAA-MM-DD>_<fuente>_<NN>) → nombre canónico
   → evento`, marcando **duplicado**, **0 bytes** y **sin fecha**. El `NN` propuesto es el
   siguiente al mayor lote de esa fuente ya existente ese día (o `01` si no hay ninguno).
   Cabecera: «nada copiado aún». **Espera OK explícito.** Si piden ajustes, reclasifica y
   vuelve a proponer.
3. **(tras OK) Ejecuta de una pasada, sin más preguntas:** resuelve/crea el lote
   `00_Input/<AAAA-MM-DD>_<fuente>_<NN>/` (crea el directorio si no existe) y deposita
   server-side dentro **verbatim** (`.zip`/`.tar` → `extract_archive`; suelto → `copy_path`;
   binario pequeño atrapado en el chat → `write_file_base64`); **salta** los duplicados;
   escribe/actualiza `_manifiesto.yaml` del lote (`fuente`, `fecha_intake`, `origen`, `items`
   con `relpath`, `sha256`, `tipo_contenido` por ítem); construye la línea con
   `traza.build_upload_event(case_id, event, files=[{path, sha256}…], actor, ts)` (`path`
   relativo a `00_Input/`, posix; `ts` ISO; `actor` = quien sube) y escríbela con
   `append_text` en `00_Input/_intake_log.jsonl`.
4. **Reporta:** lote(s) creados/reutilizados por fuente, depositados, hashes, duplicados
   saltados, 0-byte avisados.

## Qué NO hace (límites de capa)
- **NO** escribe el `_intake_hashes.json` (IntakeManifest): esa dedup pesada (aliases/
  reconcile/atómica) se reconcilia en **local con `core/`** (CLI/Streamlit), no se
  reimplementa aquí (evita drift). El evento de auditoría sí queda registrado.
- **NO** procesa por fuente (MIME del `.eml`, OCR del PDF, adjuntos faltantes de WhatsApp):
  eso es el pipeline local. Lo depositado lo recoge `inventory.scan` en la siguiente corrida.
- **NO** toca `90_Notas personales/` ni organiza la sala de lectura.

## Gotchas
- **El conector hace el trabajo de bytes.** Nunca leas el binario al contexto para
  hashear/copiar: usa `hash_path`/`copy_path`/`extract_archive`.
- **`traza.py` es puro** (sin IO): en Cowork lo ejecutas para OBTENER la línea, y la
  escribe el conector. Si añades un evento nuevo, debe estar en `core.intake_log.INTAKE_EVENTS`
  (lo vigila `tests/test_intake_traza.py::test_paridad_eventos_subconjunto_de_core`).
- **Sin PII en los paths** del evento más allá del nombre de fichero ya existente.
