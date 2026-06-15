# Diseño — Intake de chats de WhatsApp

*Fecha: 2026-06-15 · Autor: Nikolai + Claude Code · Estado: aprobado, pendiente de plan de implementación.*

## 1. Problema y objetivo

Los consultores de Engel & Völkers (y, en menor medida, clientes directos)
comunican datos de asuntos de honorarios por **WhatsApp**: tanto en
**conversaciones 1-a-1** con consultores como en **grupos** (por Market Center o
por operación). Hoy ese material no entra al expediente de forma trazable; vive
en el móvil.

**Objetivo:** habilitar la ingesta de chats de WhatsApp al árbol del caso
(`00_Input/02_Whatsapp/`) de forma trazable y con control humano, para que el
pipeline genérico (extractor → markdown → anon) y `viabilidad-prerelleno` puedan
consumirlos.

**Restricción de origen (decisión clave).** No se accede a WhatsApp por API ni
por automatización del cliente (la WhatsApp Business Cloud API de Meta no sirve
para ingerir el histórico de un grupo, y la automatización no oficial de WhatsApp
Web viola los ToS y arriesga el baneo del número del despacho). Lo que entra
siempre es el resultado de **«Exportar chat»** de WhatsApp —un `_chat.txt` +
adjuntos, normalmente empaquetado en un `.zip`— que llega **reenviado por email o
exportado a fichero**, y se ingiere **desde la UI de Streamlit**.

## 2. Alcance y fases

Se construye en fases (decisión: «C en fases, arrancando por A»):

- **Fase A (este spec):** subida del export por la **UI de Streamlit**. Parser del
  formato de exportación + glue de depósito + expander en el tab Casos. Cierra el
  caso «lo subo yo / Paola».
- **Fase B (posterior, fuera de este spec):** adaptador de email — reconocer
  correos «Exportar chat → email» en `procesal@`, parsear el adjunto con el
  **mismo** parser de Fase A, y enviarlos a una bandeja de revisión estilo
  procuradores. No requiere retrabajo del núcleo.

El **`.zip`** es el formato de entrada de primera clase (es lo que WhatsApp produce
al «incluir multimedia»); también se admite `_chat.txt` suelto + media sueltos.

## 3. Arquitectura

Coherente con la arquitectura de 3 capas (UI → Core → Datos):

```
Streamlit (UI)  →  core/whatsapp_intake.py (glue)  →  core/whatsapp_export.py (parser puro)
   uploader            deposita en 02_Whatsapp/            _chat.txt → mensajes
                       + IntakeManifest + _intake_log           (sin red, sin IO)
```

### 3.1. Andamiaje ya existente (no se crea, se alimenta)

- Destino `00_Input/02_Whatsapp/` con subcarpetas por rol ya definido en
  `core/config.py` (`WHATSAPP_SUBDIRS`): `00_Consultor propietario`,
  `01_Consultor buscador`, `02_Grupo operacion`, `03_Otros`.
- `IntakeManifest` ya acepta `source="whatsapp"` (`core/intake_manifest.py`).
- El log de intake ya tiene el evento `upload_whatsapp` (`core/intake_log.py`).
- `core/intake_manual.extract_zip` ya extrae `.zip` con saneado anti
  path-traversal — patrón reutilizable.
- `core/inventory.py` solo inventaría extensiones de `_RELEVANT_EXTS`; **`.zip`,
  `.opus`, `.ogg` NO están en la lista** → el pipeline los ignora automáticamente
  (no los OCRiza). Esto hace seguro conservar el zip original y depositar audios
  sin que el extractor los toque.

## 4. `core/whatsapp_export.py` — parser puro (núcleo reutilizable)

Capa **pura**: sin red, sin IO, totalmente testeable. Es el núcleo que la Fase B
(email) reutilizará sin cambios.

### 4.1. API

- `parse_chat(texto: str) -> list[WhatsAppMessage]`
- `filter_by_date_range(msgs, desde, hasta) -> list[WhatsAppMessage]`
- `referencias_adjuntos(msgs) -> list[str]` — nombres de adjunto referenciados en
  el texto (para el cruce de adjuntos faltantes, §5.2).

```python
@dataclass
class WhatsAppMessage:
    timestamp: datetime | None   # None si la línea no parsea fecha (mensaje de sistema atípico)
    autor: str | None            # None en mensajes de sistema
    texto: str                   # cuerpo (multilínea ya unido)
    adjunto_ref: str | None      # nombre de fichero referenciado, si lo hay
    es_sistema: bool             # "cifrado de extremo a extremo", "se unió usando...", etc.
```

### 4.2. Formatos que debe tolerar

- **iOS** (corchetes): `[15/1/24 10:32:05] Juan Pérez: Hola`
- **Android** (guion): `15/1/2024, 10:32 - Juan Pérez: Hola`
- Años de **2 y 4 cifras**; horas en **12h y 24h**.
- **Mensajes multilínea**: las líneas que no empiezan por marca de fecha se unen
  al mensaje anterior.
- **Mensajes de sistema** (`es_sistema=True`): cifrado de extremo a extremo,
  altas/bajas del grupo, cambios de asunto, etc.
- **Referencias a adjunto**: `IMG-…-WA0001.jpg (archivo adjunto)`,
  `<adjunto: …>`, `‎<archivo adjunto>` (con caracteres de control invisibles de
  WhatsApp), `<Media omitted>`/`Multimedia omitido`.

La fiabilidad del parseo de locale es la parte delicada → **TDD** con fixtures de
exports reales iOS y Android en español.

## 5. `core/whatsapp_intake.py` — glue de depósito (source-locked)

Capa de pegamento; **no depende de Streamlit** (recibe bytes + nombre, como
`intake_manual`).

### 5.1. Depósito

- Destino: `00_Input/02_Whatsapp/<subcarpeta de rol>/<nombre saneado del chat>/`.
- Se deposita **verbatim**: el `_chat.txt` + **todos** los adjuntos multimedia que
  contenga el export, **sin filtrar por tipo** (imágenes, PDFs, audios, vídeo,
  vCard, stickers/gifs incluidos). Anclaje a fuente: no se decide en la ingesta
  qué es prueba y qué es ruido.
- La **conversación entera** se deposita (no se recorta el original).
- El **`.zip` original** se conserva como `_export_original.zip` en la carpeta del
  chat, como artefacto de procedencia / cadena de custodia. Queda excluido del
  pipeline por extensión (§3.1).
- Reutiliza el saneado anti path-traversal de `extract_zip`.

### 5.2. Detección de adjuntos faltantes

WhatsApp **trunca** los media en el export (incluye solo un subconjunto; el resto
quedan referenciados en el `_chat.txt` pero el fichero no está en el zip). El glue
cruza `referencias_adjuntos(msgs)` vs ficheros presentes y reporta
**«faltan N adjuntos que WhatsApp no incluyó en el export»**, para que el letrado
sepa si pedir un re-export. No es un error: es información.

### 5.3. Dedup y contabilidad

- **Dedup de importación a nivel de entrega:** el **hash del `.zip`** gobierna el
  dedup — re-subir el mismo export se detecta antes de extraer nada.
- Cada fichero interno se registra en `IntakeManifest` con `source="whatsapp"`
  (dedup fino por hash).
- Se emite el evento `upload_whatsapp` en `_intake_log.jsonl`.

### 5.4. Filtrado por rango de fechas (opcional)

Si en la UI se aplica un rango, se deposita **además** un `_chat_recortado.txt`
junto al original (nunca en lugar de él), generado con `filter_by_date_range`.

### 5.5. Audio diferido

Los audios de voz (`.opus`/`.ogg`) se depositan como ficheros pero **no se
transcriben** en Fase A (el pipeline no los procesa; quedan ignorados por
extensión). La transcripción es una fase posterior (análoga a la F5 «Grabaciones»
del intake de procuradores), fuera de alcance.

## 6. UI Streamlit (Fase A)

Expander «📲 Importar chat de WhatsApp» en el tab Casos, gemelo del de intake
manual:

1. Subir `.zip` (o `_chat.txt` + media sueltos).
2. Elegir **caso** (existente o nuevo) y **subcarpeta de rol** (`WHATSAPP_SUBDIRS`).
3. **Previsualización** de los mensajes parseados: nº de mensajes, rango de fechas
   detectado, conteo de adjuntos presentes, conteo de adjuntos faltantes (§5.2),
   conteo de audios pendientes de transcripción (§5.5).
4. (Opcional) rango de fechas para `_chat_recortado.txt`.
5. **Confirmar** → depósito (§5).

Dry-run + confirmación humana, como el resto del intake. La UI solo orquesta; toda
la lógica vive en el core.

## 7. RGPD

- La ingesta de Fase A **no llama a ningún LLM**: parseo + depósito deterministas.
- El contenido de WhatsApp con PII solo pasaría por LLM cloud UE aguas abajo
  (viabilidad/pipeline) bajo la **misma excepción acotada** ya documentada para el
  intake (Scaleway UE); no deroga la regla general del resto del repo.

## 8. Tests

- **Parser (`whatsapp_export`):** TDD con fixtures reales iOS y Android en español
  — formatos de fecha, multilínea, mensajes de sistema, referencias a adjuntos,
  filtrado por rango.
- **Glue (`whatsapp_intake`):** con `tmp_path` — depósito verbatim, conservación
  del zip original, registro en manifest (`source="whatsapp"`), emisión del evento
  `upload_whatsapp`, dedup por hash de zip, detección de adjuntos faltantes,
  saneado anti path-traversal.
- Suite verde tras cada fase.

## 9. Decisiones cerradas

- Modo de captura: **export manual de WhatsApp**, vía UI Streamlit (Fase A) y email
  (Fase B). NO API de Meta ni automatización de WhatsApp Web.
- `.zip` como formato de entrada principal.
- Se guardan **todos** los adjuntos multimedia sin filtrar por tipo.
- Se conserva el **`.zip` original** como artefacto de procedencia; su hash es la
  llave de dedup de importación.
- Conversación **entera** como fuente; recorte por fechas solo opcional y aditivo.
- **Detección y aviso** de adjuntos que WhatsApp omitió en el export.
- Audio **diferido** (sin transcripción en Fase A).

## 10. Fuera de alcance

- Fase B (adaptador de email) — spec aparte; reutiliza el parser.
- Transcripción de audio.
- Emparejamiento automático a un expediente (en «caso nuevo» no hay expediente que
  casar; el letrado elige el caso en la UI).
- Cualquier acceso programático a WhatsApp.
