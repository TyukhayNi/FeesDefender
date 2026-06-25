# Diseño — Fase 2 de contenido de adjuntos (`core/adjuntos_contenido`)

- **Fecha:** 2026-06-25
- **Estado:** aprobado (brainstorming) — pendiente de plan de implementación
- **Disparador:** carpeta `01_Procesado/Emails/adjuntos/` del caso BaRS1 — Tibidabo 8 (W-02VND1)
  con 162 adjuntos únicos cuyos sidecars `.md` (generados por `core.email_atomize`)
  dejan `## Descripción → (pendiente; OCR en fase 2)`.

## 1. Contexto y motivación

`core.email_atomize._escribe_adjunto` ([core/email_atomize/pipeline.py:246](../../../core/email_atomize/pipeline.py))
escribe, por cada adjunto único, el binario `<base>.<ext>` y un sidecar `<base>.md`
con cabecera **"GENERADO por core.email_atomize — NO editar"** y una sección
`## Descripción` con el literal `(pendiente; OCR en fase 2)`. Ese sidecar **se
regenera en cada corrida** de la atomización (pipeline idempotente).

La "fase 2" prometida es la extracción del **contenido** de cada adjunto. El objetivo
es que el expediente sea legible sin abrir cada binario y que el texto fiel alimente
análisis aguas abajo (viabilidad, búsqueda, anonimización).

Decisión de producto (brainstorming): por cada adjunto, **texto fiel completo +
resumen corto**. Capacidad **reutilizable** (módulo `core/` con tests), no un script
puntual. Capa LLM (resumen + descripción de imágenes) **desacoplada y en sesión por
defecto** (sin API de pago; ver memoria `feedback-claude-en-sesion-vs-api-pago`),
con enchufe futuro para Scaleway (`reference-scaleway-llm`).

## 2. Objetivos y no-objetivos

**Objetivos**
- Extraer texto fiel del máximo de adjuntos, reutilizando el motor ya existente.
- Producir un `<base>.contenido.md` por adjunto (frontmatter + resumen + texto).
- Extracción incremental y reanudable (caché por sha256), idempotente.
- Dejar una cola explícita para la capa LLM (resumen, visión) y para OCR diferido.

**No-objetivos**
- No modificar la lógica PDF/OCR existente de `core/extractor.py` ni de `core/anon/`.
- No llamar a ninguna API de pago por defecto.
- No procesar exports de WhatsApp `.zip` (tienen su propio pipeline de intake).
- No tocar el binario ni el sidecar `<base>.md` de `email_atomize`.
- No escribir en `00_Input/` ni en `90_NOTAS_PERSONALES/`.

## 3. Arquitectura (enfoque A: módulo encadenable)

Módulo delgado `core/adjuntos_contenido/` que **consume la salida** de
`email_atomize` (`01_Procesado/Emails/`) y **reutiliza `core.extractor._extract_one`**
(función pura `Path → (texto, método)`) para todos los tipos que ese ya cubre.
No se integra dentro de `atomize_dir` para no acoplar OCR caro a la atomización ni
complicar su idempotencia.

### Hallazgo de reutilización
`core/extractor.py` ([_extract_one](../../../core/extractor.py)) ya resuelve:
PDF (pypdf con heurística de densidad para detectar escaneados → Docling/OCR con
guarda de páginas anti-OOM), `.docx` (Docling, fallback python-docx), `.htm/.html`,
`.csv/.xls/.xlsx` (pandas → CSV), `.eml/.msg`, `.txt/.md`. Tiene estado incremental
por sha256 (`_extract_state.json`) y versionado lógico (`EXTRACTOR_VERSION`).

### Unidades
1. **`pipeline.py`** — orquestador. `procesar_caso(case_id, *, ocr=False, forzar=False)`:
   - **Descubre** adjuntos únicos escaneando `adjuntos/`: empareja cada binario con
     su sidecar `<base>.md` y parsea `att_id / sha256 / tipo / mensajes`.
   - Consulta el estado incremental (sha256) → salta lo ya `ok` salvo `forzar`.
   - **Enruta** por tipo (ver §5).
   - Escribe `<base>.contenido.md` (vía `render.py`) y actualiza `_contenido_estado.json`.
   - Devuelve `ContenidoReport(extraidos, omitidos, pendientes_ocr,
     pendientes_resumen, pendientes_vision, errores)`.
2. **`render.py`** — construye el `.contenido.md` (frontmatter + `## Resumen` + `## Texto`).
3. **`resumen.py`** — capa LLM desacoplada: protocolo `Resumidor`
   (`resumir(texto) -> str`, `describir_imagen(path) -> str`); impl. por defecto
   **NO-OP** (deja "pendiente", no llama a nada); `aplicar_resumenes(case_id, resumidor)`
   que la sesión invoca para rellenar la cola. Enchufe futuro para Scaleway.
4. **Mejora dirigida en `core/extractor.py`** (código que se está tocando): añadir
   `_try_rtf` (burofax `.rtf`, alto valor) y soporte `.ics`. Beneficia también al
   pipeline principal. **No** se toca la rama PDF/OCR.
5. **Entrada CLI**: `python -m core.adjuntos_contenido <case_id>` + `procesar_caso`.

## 4. Formato de `<base>.contenido.md`

Fichero propio, separado del sidecar de `email_atomize`.

```markdown
---
# GENERADO por core.adjuntos_contenido — texto fiel determinista; el RESUMEN puede ser de IA (marcado).
att_id: ATT-00053
nombre_original: Contrato honorarios profesionales.pdf
tipo: application/pdf
sha256: 12ece1…3166
metodo_extraccion: pypdf        # pypdf | docling | python-docx | pandas | rtf | ics | vision | omitido | sin_texto
ocr_aplicado: false
caracteres: 4231
confianza: alta                 # alta | baja-ocr | por-verificar | omitido
resumen_estado: pendiente       # pendiente | hecho
vision_estado: n/a              # n/a | pendiente | hecho   (solo imágenes)
mensajes: [MSG-00050, MSG-00133]
---

## Resumen
_(pendiente; capa LLM en sesión)_

## Texto
<texto fiel extraído, sin retoques>
```

- El **texto** es siempre determinista y fiel; nunca lo genera un modelo.
- El **resumen** es opcional, marcado como IA, rellenable por la capa en sesión.
- `confianza: por-verificar` para OCR de baja densidad (mismo criterio que
  `media-reconstruida` en email_atomize).

## 5. Alcance por tipo de fichero

| Tratamiento | Tipos | Resultado |
|---|---|---|
| Texto fiel (`_extract_one`) | `.pdf` con texto, `.docx`, `.htm/.html`, `.xls/.xlsx/.xlsm`, `.csv` | `## Texto` completo |
| Texto fiel (extractor nuevo) | `.rtf` (burofax), `.ics` (invitaciones) | `## Texto` |
| OCR opt-in (`ocr=True`) | `.pdf` escaneado (planos, tasación, certificados) | `## Texto` + `por-verificar`; sin flag → `sin_texto` + `pendiente_ocr` |
| Visión (capa LLM en sesión) | `.jpg/.png` que sean fotos/planos reales | `## Resumen` con descripción; `vision_estado` |
| Omitido | `.emz`, decorativos (logos, emojis, iconos, firmas, por tamaño + `A.es_decorativo`), `.zip` (WhatsApp) | `metodo: omitido` + motivo, **nunca falla** |

Regla de oro: un tipo no soportado **se marca, no rompe la corrida**.

## 6. Idempotencia y trazabilidad

- **Estado incremental por sha256** en `adjuntos/_contenido_estado.json`
  (`{version, files: {sha256: {metodo, chars, ok, resumen_estado, vision_estado}}}`).
  Re-correr salta lo `ok` salvo `forzar`. Se persiste tras cada adjunto (reanudable).
- **Versión lógica** `CONTENIDO_VERSION`: subirla invalida el caché y reextrae.
- **Dedup por sha256**: adjuntos idénticos en varios mensajes → una extracción; el
  `.contenido.md` lista todos los `mensajes`.
- **Poda de huérfanos**: un `*.contenido.md` sin sha en el conjunto actual se elimina.
  **Solo toca `*.contenido.md`** — nunca el binario ni el sidecar de email_atomize.
- **No destructivo**: nunca escribe en `00_Input/` ni `90_NOTAS_PERSONALES/`; nunca
  modifica binario ni `<base>.md`. sha256 en frontmatter = evidencia de integridad.
- **Capa LLM separada del caché determinista**: rellenar un resumen no invalida la
  extracción de texto; `resumen_estado`/`vision_estado` en sus propios campos.

## 7. Capa LLM (desacoplada, en sesión por defecto)

- `Resumidor` (protocolo): `resumir(texto) -> str`, `describir_imagen(path) -> str`.
- Impl. por defecto **NO-OP**: deja `## Resumen` en "pendiente" y `resumen_estado:
  pendiente`. Una corrida headless **no** llama a ningún modelo de pago.
- `aplicar_resumenes(case_id, resumidor)`: recorre la cola (`resumen_estado:
  pendiente` / `vision_estado: pendiente`), genera y escribe SOLO la sección
  `## Resumen` (y `vision_estado`), sin tocar `## Texto`. La sesión (Claude Code)
  actúa de `Resumidor` por defecto; Scaleway queda como impl. opcional futura.

## 8. Plan de tests (TDD)

- Extractores nuevos con fixtures mínimas: `.rtf` de una línea → texto; `.ics` con un
  VEVENT → resumen estructurado.
- Router/dispatch: cada mime → método esperado; `.emz`/`.zip`/no soportado →
  `omitido` sin excepción.
- Render: snapshot del `.contenido.md` (frontmatter + secciones; resumen "pendiente").
- Descubrimiento: empareja binario↔sidecar y parsea att_id/sha256/mensajes sobre un
  `adjuntos/` de juguete.
- Incrementalidad: 2ª corrida con sha sin cambios → `skipped`; cambiar
  `CONTENIDO_VERSION` → reextrae.
- Idempotencia: 2ª corrida = salida byte-idéntica (tipos deterministas); poda elimina
  solo `*.contenido.md` huérfanos, respeta binario y sidecar.
- Capa LLM: `Resumidor` NO-OP deja "pendiente"; `aplicar_resumenes` con resumidor fake
  rellena `## Resumen` y marca `hecho` sin tocar `## Texto`.
- OCR: test con `skipif` si no hay `tesseract`/`ocrmypdf` (criterio de `tests/test_anon_ocr.py`).
- Integración: corrida completa sobre un `01_Procesado/Emails/` de juguete con un
  adjunto de cada familia.

## 9. Riesgos y notas

- **Dependencias de extractor nuevo**: `.rtf` necesita un parser (p. ej. `striprtf`);
  confirmar en el venv durante el plan. `.xlsm` vía pandas requiere engine `openpyxl`;
  `.xls` legacy requiere `xlrd`. Si falta dependencia → `omitido` con motivo, no falla.
- **OCR pesado**: por defecto `ocr=False` (marca pendiente). La corrida con OCR se hace
  aparte y reanudable.
- **Imágenes**: distinguir foto real de decorativa reutilizando `A.es_decorativo` +
  umbral de tamaño; en duda, marcar para visión, no omitir silenciosamente.
- **Corrida sobre G:\ (Drive)**: la corrida real sobre W-02VND1 escribe en el Drive del
  despacho; se ejecuta como paso final explícito y autorizado, no en los tests.

## 10. Entregable de validación

Tras implementar y verde la suite, correr `procesar_caso("W-02VND1")` (sin OCR primero)
sobre `01_Procesado/Emails/adjuntos/` y revisar una muestra de `.contenido.md`.
