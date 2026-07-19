# Diseño — Motor de atomización fina de WhatsApp (`core/whatsapp_atomize/`)

> Spec de diseño. Aprobado por Nikolai 2026-06-25 (brainstorming).
> Motor **genérico**, no específico de caso. Caso de verificación: chats reales de
> **W-02VND1 (BaRS1 — [inmueble])** / BaRS1, que ya tienen WhatsApp media depositada.
> Hermano de `core/email_atomize/`: mismo espíritu (lo plano se queda, lo enterrado se
> promueve; cero misatribución), modelo de datos propio del formato WhatsApp.

## 1. Contexto y objetivo

El parser puro `core/whatsapp_export.parse_chat` ya descompone un `_chat.txt` en mensajes
atómicos (`WhatsAppMessage`: timestamp, autor, texto, adjunto, sistema). Lo que **no**
existe es el equivalente WhatsApp de `email_atomize`: una fuente de verdad legible y
citable, con reconstrucción de contenido enterrado, atribución de identidad con confianza,
y dedup de multimedia.

Nuevo paquete `core/whatsapp_atomize/` que lee de `00_Input/02_Whatsapp/` (el `_chat.txt` +
media que deposita `core.whatsapp_intake`) y produce, en `01_Procesado/Whatsapp/`:

- por cada chat, **un `.md` legible con mensajes numerados** (`MSG-00042`), citable como
  prueba — el grano del átomo (decisión de diseño, §5);
- atoms `.md` propios **solo para el contenido enterrado promovido** (§6);
- adjuntos **deduplicados por sha256** con ficha (§8);
- `corpus.jsonl` (índice de máquina), `_registro.json` (IDs congelados),
  índices humanos (§9).

**Arquitectura 3 capas (CLAUDE.md):** la lógica vive en `core/whatsapp_atomize/`; el CLI
`scripts/atomize_whatsapp.py` solo orquesta. **Nunca toca `00_Input`** (crudo inmutable);
re-ejecutar es idempotente.

**Las cuatro dimensiones de paridad con `email_atomize`** (alcance aprobado):
átomo citable por mensaje · reconstrucción de enterrados · atribución de identidad ·
reconstrucción multimedia.

## 2. Realidad del formato WhatsApp (condiciona el diseño)

A diferencia del correo, el export de WhatsApp **no** es un contenedor con cabeceras
estructurales. Tres consecuencias que el diseño asume como hechos:

| Hecho del formato | Implicación de diseño |
|---|---|
| Un "mensaje" puede ser `ok` o un emoji; un chat trae fácilmente miles | Un `.md` por mensaje sería ruido ingobernable → el grano del átomo es **el chat numerado**, no el mensaje (§5). |
| Un **reenvío** solo expone quién reenvió, **nunca el autor original** | El reenvío puro se **marca**, no se reconstruye; no se inventa autor (§6). |
| El texto de un email/mensaje a veces va **pegado** en el cuerpo (con cabecera `De:/Para:` o "El … escribió:") | Ahí sí hay autoría enterrada recuperable → body-scan reutilizado de `email_atomize` (§6, §7-reuso). |
| El **fragmento citado** de un *reply* solo aparece de forma poco fiable (iOS, a veces) | Tratamiento mínimo en v1: ligar por match exacto dentro del chat, o nada (§6). |
| El verbatim es el propio `_chat.txt`; no hay un contenedor que re-emitir byte-idéntico | El verbatim se **referencia** (sha256 del `_chat.txt` en el registro); el `.md` numerado es **vista derivada** (§10). |

## 3. Arquitectura del módulo

Paquete `core/whatsapp_atomize/`, cada unidad con una responsabilidad. El parser puro
`core/whatsapp_export.py` **se reutiliza tal cual** (no se duplica ni se modifica).

- `model.py` — dataclasses: `RegistroMensajeWA`, `AtomEnterrado`, `SegmentoEnterradoWA`
  (cola de revisión). Importa `AdjuntoUnico`/`AdjuntoRef` de `email_atomize.model`.
- `ids.py` — IDs congelados (`MSG-NNNNN`/`ATT-NNNNN`), carga/guardado de `_registro.json`,
  mapa `fingerprint → ID` y `sha256 → ID`.
- `identidades.py` — mapa `autor_export → Persona+rol` desde `identidades.yaml` (campo
  `identificadores`); misma forma `Persona`/`Identidades` que `email_atomize`, clave por
  identificador WhatsApp en vez de email (§7).
- `reconstruccion.py` — detección de enterrados: reenviado, email/mensaje pegado
  (body-scan reutilizado), quote de reply. Confianza + cola de revisión (§6).
- `adjuntos.py` — liga `adjunto_ref` a los bytes presentes, sha256, dedup en `AdjuntoUnico`,
  marca ausentes (§8).
- `render.py` — `<chat>__LECTURA.md` numerado + `enterrados/MSG-*.md` + índices + ficha de
  adjuntos. Reutiliza el patrón de banner "AUTORÍA POR VERIFICAR".
- `corpus.py` — `corpus.jsonl` + `_registro.json` con meta "generado / no editar".
- `pipeline.py` — `atomize_whatsapp_case(case_id)`; `scripts/atomize_whatsapp.py` es un CLI
  fino encima.

## 4. Modelo de datos

`RegistroMensajeWA` (lo esencial):

- `msg_id` (`MSG-00042`, **congelado** por `_registro.json`);
- `fingerprint` (hash estable de `timestamp + autor_export + texto`, llave de idempotencia);
- `fecha_iso`, `hora` (local del export; WhatsApp no exporta zona horaria), `chat_id`;
- `autor_export` (lo que trae el chat: nombre de contacto o número);
- `persona_id`, `rol` (resueltos vía `identidades`; vacío = genérico), `de_confianza`;
- `texto` (verbatim del mensaje), `es_sistema`, `es_reenviado`;
- `adjunto` (`AdjuntoRef` reutilizado);
- flags de reconstrucción: `contiene_enterrado`, `en_revision`, `responde_a` (MSG-id o "").

`AtomEnterrado` — una unidad reconstruida promovida a `.md` propio:

- `enterrado_id`, `portador_msg_id` (de qué mensaje del chat salió);
- `anclaje` (`de`, `de_nombre`, `fecha_iso` — del body-scan), `extracto`, `confianza`,
  `en_revision=True`.

`SegmentoEnterradoWA` — fila de la cola de revisión (puntero a contenido detectado como
candidato pero **no** promovido por ambigüedad), espejo de `email_atomize.SegmentoEnterrado`.

## 5. Grano del átomo — chat numerado + atoms solo para enterrados

Decisión central (aprobada). El chat se renderiza como **un `.md` legible con mensajes
numerados** (`MSG-00001`…), citable por índice. Se promueven a `.md`/atom propio **solo** las
unidades reconstruidas (§6). Es la traslación fiel del espíritu de `email_atomize`: lo plano
se queda en su sitio, lo enterrado se promueve. Evita la explosión de ficheros (un `.md` por
"ok"/emoji) y el ruido en el corpus.

## 6. Reconstrucción de enterrados — tres reglas por confianza

| Fenómeno | Detección | Acción | Confianza |
|---|---|---|---|
| **Email/mensaje pegado** | `atribucion_en_cuerpo(texto)` devuelve `Anclaje` | Promueve a `AtomEnterrado` (`.md` propio), banner "AUTORÍA POR VERIFICAR", `en_revision=True`, fila en cola | media |
| **Reenviado puro** | marcador "‎Reenviado"/"Forwarded"/"Reenviado muchas veces" | Marca `es_reenviado`; banner "reenviado por X — **origen no expuesto por WhatsApp**". NO inventa autor original | — (hecho) |
| **Quote de reply** | fragmento citado (iOS, best-effort) | Si liga por match exacto a un MSG-id del mismo chat → anota `responde_a`. Si no liga → nada | baja |

**Prime directive (heredado):** el motor jamás afirma un autor que no esté literalmente en el
cuerpo. El reenvío puro es el límite del formato y se respeta. El quote de reply es
deliberadamente mínimo en v1 (el export no lo trae de forma fiable); ampliable si un caso lo
pide.

## 7. Identidad — auto-propuesta + gate + persistencia

Flujo de tres pasos (aprobado):

1. **Propuesta** — subcomando `proponer-identidades` (Claude-en-sesión, **sin API de pago**;
   ver [[feedback-claude-en-sesion-vs-api-pago]]): reúne los `autor_export` distintos del chat
   + muestras de sus mensajes; Claude propone un borrador de `identidades.yaml` (persona, rol
   `propietario`/`buscador`/`E&V`/`tercero`, alias duplicados del mismo autor unificados).
2. **Gate único** — el letrado revisa/corrige el yaml. No hay preguntas por-fichero.
3. **Persistencia** — `identidades.yaml` en la raíz del caso, reutilizable en re-corridas.

**`identidades.yaml` compartido con `email_atomize`.** Una persona física tiene email *y*
WhatsApp; no se registra dos veces. La `Persona` gana un campo opcional `identificadores` (los
`autor_export` de WhatsApp, con estado `confirmada`/`candidata` igual que las `direcciones`).
`whatsapp_atomize/identidades.py` lee `identificadores`; `email_atomize` lee `direcciones`
(emails) e **ignora el campo nuevo** que no conoce (`desde_dict` no rechaza claves extra a
nivel de persona) → **cero cambios en `email_atomize`**. Un actor, un registro, dos motores.

## 8. Adjuntos

`adjunto_ref` (nombre referenciado en el chat) se liga a los bytes presentes en el zip/carpeta
del export. sha256 de cada fichero; dedup en `AdjuntoUnico` (mismo fichero referenciado por
varios mensajes o chats = una sola ficha, con su catálogo de apariciones). Los marcadores
`<Media omitted>` / fichero referenciado ausente → adjunto **marcado ausente**, no aborta.
Dedup por **sha256**, nunca por nombre.

## 9. Salida — `01_Procesado/Whatsapp/`

Espejo de `01_Procesado/Emails/`:

- `<chat>__LECTURA.md` — chat numerado legible: por mensaje, `MSG-id`, fecha/hora, autor
  resuelto (persona+rol o `autor_export` crudo), texto, marca de reenviado/adjunto, enlaces a
  los atoms enterrados y a las fichas de adjunto;
- `enterrados/MSG-*.md` — un `.md` por enterrado promovido (banner + anclaje + extracto +
  puntero al portador);
- `INDICE.md` (por chat/tipo) + `CRONOLOGIA.md` (por fecha) + `INDICE_ADJUNTOS.md`;
- `corpus.jsonl` (una línea por mensaje, para búsqueda);
- `_registro.json` (IDs congelados + sha256 del `_chat.txt` verbatim; meta "generado / no
  editar").

## 10. Invariantes y garantías

- **Nunca toca `00_Input`.** El verbatim es el `_chat.txt` original + su sha256 en
  `_registro.json`; el `.md` numerado es vista derivada (no fuente de verdad).
- **Prime directive**: cero misatribución (§6). Todo lo reconstruido lleva banner "por
  verificar" + `en_revision` + fila en la cola de revisión.
- **Sin `identidades.yaml`** → comportamiento genérico (autor crudo), no falla.
- **No regresión en `email_atomize`**: el único cambio que lo roza es exponer
  `atribucion_en_cuerpo` (renombrado de `_atribucion_en_cuerpo`, sin tocar lógica) +
  el campo `identificadores` que ignora. La suite de correo lo confirma.

## 11. Manejo de errores

- Líneas sueltas / multilínea / mensajes de sistema → ya los absorbe `parse_chat`; U+200E
  (LRM) contemplado.
- Media ausente → se marca "ausente", no aborta.
- `identidades.yaml` inválido → `desde_dict` lanza `ValueError` con mensaje claro; el motor
  **no corre con un mapa corrupto** (propaga con contexto).
- Encoding **UTF-8 sin BOM** en todo el IO (regla del proyecto).

## 12. Idempotencia

IDs congelados por fingerprint en `_registro.json`: 2 corridas sin cambios → 0 cambios; chat
ampliado (re-export) → ids viejos estables, mensajes nuevos al final. Mensajes desaparecidos
del re-export → conservados en el registro y marcados ausentes (paridad con email).

## 13. Testing (TDD)

Tests unitarios por módulo (`tests/test_whatsapp_atomize_*.py`), casos clave:

- **Reconstrucción**: email pegado → promueve atom con anclaje correcto + banner; reenvío
  puro → marcado **sin** autor (no misatribución); body-scan con >1 cabecera → `None`, queda
  en cola (hereda las guardas de la función reutilizada).
- **Identidad**: `identidades.yaml` compartido, `whatsapp_atomize` lee `identificadores`;
  **test de no-regresión** de que `email_atomize` ignora ese campo.
- **Idempotencia**: 2 corridas → 0 cambios; ids estables por fingerprint.
- **Adjuntos**: dedup por sha256; faltante marcado.
- **`00_Input` intacto** tras correr.
- **Verificación adversarial sobre datos reales** (en el plan, no en cada test): correr sobre
  un chat real (W-02VND1/BaRS1) y auditar misatribución a mano, igual que en email F4.

## 14. Disparo

- CLI `scripts/atomize_whatsapp.py`: subcomandos `atomize` y `proponer-identidades`.
- Botón Streamlit (tab Casos), espejo del de email si procede — orquesta `core`, sin lógica.

## 15. Reuso de `email_atomize` (resumen)

- Importa `AdjuntoUnico`/`AdjuntoRef` (`model`), la forma `Persona`/`Identidades`
  (`identidades`), el patrón de banner de `render`.
- **Promueve `_atribucion_en_cuerpo` → `atribucion_en_cuerpo`** (API pública): cambio mecánico
  (renombrar símbolo + su único uso interno en `inline.py:956`), sin tocar lógica. Una sola
  fuente de verdad para la función de seguridad jurídica (evita el "drift silencioso" que
  obligó a crear `intake_utils.py`).
- **Evolución (YAGNI, no ahora):** si el acople a `inline.py` molesta, extraer el body-scan +
  helpers a `core/atomize_shared/atribucion.py`.

## 16. Alcance v1 vs. futuro (YAGNI)

- **v1**: las 3 reglas de reconstrucción (quote mínimo), identidad, adjuntos dedup, render
  numerado, corpus, idempotencia.
- **Futuro (sin disparador)**: quote de reply completo; extracción a `atomize_shared`;
  integración con la sala de lectura unificada; OCR de imágenes adjuntas.

## 17. Relación con el backlog

- **Subsume `docs/MEJORAS_FUTURAS.md` #35** (bundles WhatsApp chat+media en la sala de
  lectura): este motor produce la sala fina con creces → se marca superado por este spec.
