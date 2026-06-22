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
  version: "1.0"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: experimental
  requires: []
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# intake-expediente

Deposita ficheros en `00_Input/<fuente>/` de un expediente del Drive, dirigido desde
Claude, **con trazabilidad**. Todo lo que toca bytes va **server-side** por el conector
`expedientes-xl` (los bytes nunca pasan por el modelo). La trazabilidad (evento `upload_*`)
se construye con el helper puro `scripts/traza.py` y se escribe con `append_text`.

## Requisitos
- Conector MCP **expedientes-xl** disponible (Plan 1), acotado a la raíz del Drive del
  despacho. Si no está, no se puede depositar — avisa.
- El fichero a subir debe estar **ya en un disco que el conector alcanza** (déjalo en
  `…/EXPEDIENTES - TYUKHAY LEGAL/_ingest/`). Ficheros grandes NO viajan por el chat;
  los pequeños (< tope) pueden entrar por `write_file_base64`.

## Fuentes y destino (`00_Input/`)
`01_Drive EV` · `02_Whatsapp/<rol>` · `03_Email` · `04_Manual` · `05_CRM` ·
`06_Entrevistas/<AAAA-MM-DD>_<rol>_<apellido>`. El evento `upload_*` se elige por fuente:
WhatsApp→`upload_whatsapp`, email→`upload_email`, entrevista→`upload_entrevista`, resto
manual→`upload_manual`.

## Procedimiento
1. **Resuelve el caso y la fuente.** Confirma la subcarpeta destino de `00_Input/`.
2. **Deposita (server-side):** `.zip`/`.tar` → `extract_archive(archivo, 00_Input/<fuente>/)`;
   fichero suelto → `copy_path`; binario pequeño solo en el chat → `write_file_base64`.
3. **Hashea** cada fichero depositado con `hash_path` (SHA-256 server-side).
4. **Dedup (aviso, no bloqueo):** lee `00_Input/_intake_log.jsonl` (si existe) y, con
   `traza.is_duplicate(log, sha)`, marca los que ya constaban. No re-deposita el crudo.
5. **Dispara la traza:** ejecuta `traza.build_upload_event(case_id, event, files=[{path,
   sha256}…], actor, ts)` (el `path` relativo a `00_Input/`, posix; `ts` ISO; `actor` =
   quien sube) → te devuelve la línea JSONL → escríbela con `append_text` a
   `00_Input/_intake_log.jsonl`.
6. **Reporta:** ficheros depositados por fuente, hashes, duplicados marcados.

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
