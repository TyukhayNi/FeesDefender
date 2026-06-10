# PLAN — FeesDefender

Bitácora de planificación compartida entre Nikolai y Cowork (PC). Edición de
código: solo Claude Code. Aquí van prioridades, decisiones e ideas.

Estado del proyecto y bitácora de cierre de sesión: ver `STATUS.md` (repo).
Historial de commits: `git log`. Acceso móvil: app de GitHub (lectura).

---

## ⚠️ MÁXIMA PRIORIDAD — abrir la próxima sesión por aquí

### ✅ [CRITICO-PRESIGNED-DOWNLOAD-BUG] RESUELTO 2026-06-10 — descarga del Gestor Documental

La descarga REST está arreglada (era la **Fase 0** de
`[SIGUIENTE-INTAKE-JUDICIAL-AUTO]`, abajo). Causa raíz: el CRM redesplegó el
módulo `App\Upload` y rompió **ambos** endpoints de presigned-URL
(`/api/files/presigned_download_url` → 400 IRI; `/api/documents/presigned_urls/s3/download`
→ 500 controlador no registrado). Endpoint vivo: `GET /api/documents/{id}/downloadUri`
→ campo `presignedDownloadUrl`. `get_presigned_download_url` reescrito; 31/31 docs
del exp. 649 verificados byte a byte. Detalle completo y diagnóstico en
`docs/DEAD_ENDS.md` (entrada marcada ✅ RESUELTO). **Próximo paso real:** Fases 1-4
de `[SIGUIENTE-INTAKE-JUDICIAL-AUTO]`.

---

## [SIGUIENTE-INTAKE-JUDICIAL-AUTO] Intake automático de demanda y contestación desde el CRM
*Añadido 2026-06-10 (sesión Cowork). Implementación: Claude Code. Engloba y resuelve `[CRITICO-PRESIGNED-DOWNLOAD-BUG]` como su Fase 0.*

**Objetivo:** intake end-to-end de los dos documentos judiciales clave de un
expediente —demanda y contestación— desde el Gestor Documental del CRM hasta el
árbol del caso, sin el workaround manual (descarga SPA + expander Streamlit).
Flujo: localizar expediente judicial → identificar demanda y contestación →
descargar → depositar en cajón CRM → encadenar pipeline (anon → MD → frontier)
con dedup (M9) y log (M10, `_intake_log.jsonl`).

**Contexto verificado (sesión Cowork 2026-06-10, lectura de `core/sync_sudespacho.py`):**
- Listado OK: `list_gdocu_docs_rest` (`GET /api/element_registries/gdocu`) →
  `GdocuDocInfo(doc_id, filename, id_carpeta, id_carpeta_label, mime, size, raw)`;
  `id_carpeta_label` trae etiquetas tipo `"CIVIL"`.
- Descarga ROTA: `get_presigned_download_url` usa `ENDPOINTS["presigned_download_url"]`
  = `/api/files/presigned_download_url/{doc_id}` → HTTP 400. Es el bug crítico.
- PISTA: existe declarado pero **sin usar** `ENDPOINTS["presigned_download"]` =
  `/api/documents/presigned_urls/{service}/download/{documentId}` (`service="s3"`),
  mencionado en el docstring de cabecera → primer candidato a probar.
- Demanda/contestación viven en namespace `expedientes_judiciales` (ids no
  comparables con `expedientes_extrajudiciales`). Banco de pruebas: expediente 649 (BaRR3, 26 docs).

**Fases:**
- **Fase 0 (bloqueante) — desbloquear descarga.** ✅ HECHA (2026-06-10). La ruta
  alternativa del plan (`presigned_urls/s3/download`) **también estaba rota** (500);
  el endpoint vivo es `GET /api/documents/{id}/downloadUri` → `presignedDownloadUrl`.
  `get_presigned_download_url` reescrito, `docs/DEAD_ENDS.md` actualizado.
  Cierre cumplido: **31/31** docs del expediente 649 (creció desde 26) ✓.
- **Fase 1 — identificación.** ✅ HECHA. `core/judicial_classifier.py`:
  heurística regex source-locked **solo por `filename`** (la `id_carpeta_label`
  resultó demasiado gruesa — las carpetas DEMANDA/OPOSICION del CRM contienen
  toda la prueba; descubierto en el e2e del 649). Colapso de duplicados
  .pdf/.docx. Casos 0/múltiples → `[PENDIENTE revisión letrado]`, nunca adivina.
  Hook `llm_fn` inyectable pero **sin LLM por defecto** (decisión de Nikolai;
  RGPD: ningún nombre con PII sale del entorno).
- **Fase 2 — routing + pipeline.** ✅ HECHA. `core/judicial_intake.py`
  reutiliza `pull_expediente_v2` (nuevo param `only_doc_ids`) → dedup M9, log
  M10, routing `crm_branch_path`, estado D8. Solo baja demanda+contestación;
  `documents_total_crm` sigue siendo el total real. Pipeline encadenado por el
  caller (`--run-pipeline` / checkbox).
- **Fase 3 — disparo.** ✅ HECHA. CLI `intake-judicial --case --expediente
  [--run-pipeline]` + **botón** en el tab Casos de Streamlit
  («⚖️ Intake judicial automático»).
- **Fase 4 — tests y cierre.** ✅ HECHA. Tests del clasificador (con etiquetas
  reales del 649 como regresión) + orquestador. E2E real: demanda 40022
  auto-depositada, contestación marcada pendiente (2 candidatos). Suite verde.

**Decisiones cerradas (2026-06-10, con Nikolai):**
- Clasificación: heurística por `filename` (la etiqueta de carpeta NO dispara).
  **Sin LLM** — la ambigüedad va a revisión del letrado (RGPD-local).
- Disparo: **CLI + botón Streamlit**.

---

## Aparcado mientras el bloque crítico no se cierre

- `[SIGUIENTE-ORGANIZADOR-UI]` — **DESCARTADO 2026-06-07** (Ollama demasiado
  lento e impreciso). Sustituido por `[SIGUIENTE-CATALOGO-DOCUMENTAL]`;
  ver "Notas de la sesión Cowork 2026-06-07" abajo.
- `[SIGUIENTE-SUBDIVISION-CIUDADES]` — refactor `CASOS_ROOT` por ciudades
  (Fase 1).
- `[SIGUIENTE-SaRS1-PIPELINE]` H6 — subida manual gdocu expediente 659 +
  entrega a Claude frontier (depende del pull, lógicamente atado al
  bloque crítico).

---

## Resuelto

### [CRITICO-FUENTES-VERDAD-PLANIFICACION] — RESUELTO 2026-05-29

**Resolución (sesión Cowork 2026-05-29):** auditadas las fuentes de verdad de
planificación y consolidadas. La bitácora (`PLAN.md`, `STATUS.md`, historial de
commits) deja de vivir en Drive y pasa al **repo como única fuente de verdad**.

Decisiones cerradas:
- `PLAN.md` (raíz del repo) — cola priorizada compartida; la editan Cowork (PC)
  y Claude Code. Cowork móvil queda fuera del lazo hasta que exista un conector
  MCP de GitHub (hoy **no existe en el registry**; la vía OAuth/GitHub App no la
  soporta el flujo de conector personalizado y Docker+PAT es solo escritorio).
- `STATUS.md` (raíz del repo) — estado fáctico + bitácora de cierre, escrito por
  Claude Code.
- Historial: `git log`. Se **deprecan** `ESTADO.md` y `commits.log` como
  artefactos separados en Drive (duplicación + lag PC→nube generaba divergencia;
  el conector Drive de Cowork solo soporta create, no update → duplicados).
- Acceso móvil: app de GitHub (lectura); edición ocasional vía GitHub web.
- Drive queda solo para expedientes jurídicos (`CASOS_ROOT`) y entregables.

Regla documentada en `CLAUDE.md` §"Planificación y estado". La carpeta Drive
`Proyectos/FeesDefender/` la archiva Nikolai manualmente.

<details>
<summary>Problema original (apuntado 2026-05-28) — para trazabilidad</summary>

Convivían varias fuentes donde se registraban prioridades, decisiones, estado y
planes; el solapamiento generaba riesgo de drift, duplicación de la verdad y de
arrancar por una prioridad obsoleta. Fuentes detectadas: `PLAN.md` (Drive),
`STATUS.md` (repo) / `ESTADO.md` (Drive), `CLAUDE.md`, `README.md`,
`docs/PLAN_*.md`, `docs/MEJORAS_FUTURAS.md`, `docs/DEAD_ENDS.md`,
`bitacora/commits.log` (Drive), memoria de Cowork, project instructions de Cowork,
`docs/INTEGRACION_SUDESPACHO.md`. Riesgo ya materializado: el
`[CRITICO-PRESIGNED-DOWNLOAD-BUG]` vivía en `STATUS.md` pero no en la cola de
máxima prioridad, y hubo que rescatarlo a mano el 2026-05-28.

</details>

---

## Notas de la sesión Cowork 2026-05-28

- Verificado el pipeline de intake CRM: pull v2 implementado, CLIs en
  `scripts/sync_sudespacho.py` (`pull`, `sync_all`), `scripts/bulk_pull_expedientes.py`,
  `scripts/scheduled_sync.py`. NO hay botón en la UI Streamlit para lanzar
  el pull — solo CLI.
- Confirmado el workaround manual vigente para meter requerimientos y
  respuestas a requerimientos descargados manualmente del CRM: usar
  expander "📂 Subir al árbol CRM" (con rama canónica) o, como atajo,
  "📄 Demanda / documentos judiciales" (cajón `04_Manual/`). Ambos
  entran al ciclo anon → MD → frontier por igual; el primero deja además
  rastro en `_intake_log.jsonl`.
- Subido `[CRITICO-PRESIGNED-DOWNLOAD-BUG]` a máxima prioridad — antes
  estaba documentado en `STATUS.md` pero no en cabeza de cola.
- Apuntado `[CRITICO-FUENTES-VERDAD-PLANIFICACION]` — auditoría meta del
  proceso de desarrollo, motivada por la observación de Nikolai de que
  conviven demasiadas fuentes de verdad. **Resuelto el 2026-05-29** (ver arriba).

## Notas de la sesión Cowork 2026-06-07

### Decisión — Organización documental por caso

**1. Organizador local con Ollama → DESCARTADO** (`[SIGUIENTE-ORGANIZADOR-UI]`).
Ollama (Qwen 2.5 14B) demasiado lento e impreciso para esta tarea. La ventaja
de "local" (privacidad/coste) no compensa aquí: ya se anonimiza antes y ya hay
LLM cloud en el pipeline; nombres y estructura no son el payload sensible.
Coste de mantenimiento alto para usuarias no técnicas (fallos silenciosos) y la
vista `_organizado/` duplica almacenamiento.

**2. Sustituto → `[SIGUIENTE-CATALOGO-DOCUMENTAL]`: catálogo YAML canónico +
`INDICE.md` derivado.**

- `indice_documental.yaml` en la raíz del caso = fuente de verdad canónica,
  propiedad del código. Lo consumen pipeline, sync CRM, bitácora y (futuro)
  El Auditor.
- `INDICE.md` auto-renderizado desde ese YAML, de **solo lectura** (cabecera
  "no editar a mano"), para humanos (Paola, Ana, Marta E&V).
- Las ediciones entran por UI/pipeline, **nunca tocando el YAML a mano** (evita
  mojibake/encoding y conflictos de escritura concurrente).
- **Excluir siempre `90_NOTAS_PERSONALES/`** del indexado. El YAML convive con
  la nomenclatura de carpetas, no la sustituye.
- Esquema mínimo por entrada: `id_doc`, `ruta_relativa`, `nombre_original`,
  `tipo_documental`, `fecha_doc`, `parte` (propietario/buscador/tercero),
  `fuente` (E&V/cliente/juzgado), `estado` (original/anonimizado/borrador),
  `hash`, `fecha_indexado`.
- El desorden de carpetas heredado, si es masivo, se trata con un **script de
  migración puntual**, no con una feature permanente.

Patrón YAML→render coherente con el renderer YAML→XLSX de plantillas de
viabilidad. Implementación: Claude Code.

### Idea técnica — `[IDEA-SKIP-INCREMENTAL-EXTRACCION]`

**Origen**: consulta de Nikolai (sesión Cowork 2026-06-07) sobre qué pasa al
relanzar el pipeline con intake ya parcialmente OCRizado/markdowneado/anonimizado.

**Hallazgos al leer el código**:
- `extractor.extract_all` y `markdown_generator.build` **no son idempotentes**:
  reprocesan y sobrescriben todo `01_Procesado/` en cada corrida, exista o no.
  Solo `core/anon` salta por hash (`origen_sha256` en frontmatter, política
  `SALTAR`/`REPROCESAR`).
- **Bug de eficiencia**: `core/pipeline.py` llama a `extract_all` **dos veces**
  por corrida — paso `extractor.extract_all` y de nuevo dentro de
  `_markdown_step`. El OCR (Docling, el único paso caro) se ejecuta el doble de
  lo necesario, se toquen o no los documentos.

**TODO para Claude Code** (por orden de valor/riesgo, de mayor a menor):

- [ ] **1. Arreglar la doble llamada a `extract_all`** en `core/pipeline.py`
  (gana 50 % de OCR, riesgo cero). Cachear el resultado y pasárselo a
  `markdown_generator.build` en vez de reextraer. **Hacerlo aunque se descarte
  el resto.**
- [ ] **2. Skip incremental en extracción** por `sha256` del origen + versión de
  extractor (invalidar si cambia el backend Docling), reutilizando el patrón de
  `core/anon`, con `--force`.
- [ ] **3. Markdown que siga a la extracción**: regenerar solo el `.md` de los
  archivos realmente reextraídos. Trivial una vez la extracción devuelve cuáles
  saltó.

**Matiz de coherencia**: la regla de `CLAUDE.md` "Pipeline idempotente:
re-ejecutar nunca toca `00_Input/`" significa "no muta inputs", no "salta lo ya
hecho". El skip refuerza esa idempotencia, no la rompe. Implementación: Claude Code.

### Idea de gobernanza documental — `[IDEA-GOBERNANZA-DOCS]`

**Origen**: misma sesión 2026-06-07. Al revisar cómo se relacionan `CLAUDE.md`,
`PLAN.md` y `docs/MEJORAS_FUTURAS.md` se constató que el conocimiento es **radial**
(todo cuelga de `CLAUDE.md`), no en malla: `PLAN.md` y `MEJORAS_FUTURAS.md` **no
se referencian entre sí** y no existe camino definido para "promover" una idea de
`MEJORAS_FUTURAS.md` (backlog técnico, hoy acotado a `anon`) a `PLAN.md` (cola
priorizada accionable).

**Propuesta**:
- Añadir referencia cruzada explícita entre `PLAN.md` y `MEJORAS_FUTURAS.md`.
- Decidir el alcance de `MEJORAS_FUTURAS.md`: ¿sigue siendo solo de `core/anon`
  (entonces `[IDEA-SKIP-INCREMENTAL-EXTRACCION]` vive en `PLAN.md`) o se amplía a
  backlog técnico de todo el repo?
- Definir en `CLAUDE.md` una regla de promoción idea→tarea (cuándo y cómo una
  entrada de `MEJORAS_FUTURAS.md` entra en la cola de `PLAN.md`).

Implementación (edición de `CLAUDE.md`/docs): Claude Code. Edición de `PLAN.md`:
compartida.

## TODO — Refactor de `hechos_atomicos`: extractor source-locked
*Sesión Cowork 2026-05-29*

**Decisión**: sustituir el prompt LLM único actual (`core/viability.py::analyze` → `02_Analisis/hechos_atomicos.md`) por un extractor en tres capas (E + B + C) que deposita un `08_Para frontier/_hechos.md` 100 % citado.

**Motivación**: el prompt actual es no determinista, no obliga a anclar cada hecho a un span literal del documento fuente y contradice la regla source-locked del despacho (skill `verificacion-anclada-fuente`). El frontier hoy recibe un `.md` que ningún verificador puede auditar.

**Arquitectura objetivo**

- **Capa C — extractor estructurado por `tipo_caso`**: esquema fijo de hechos esperados (hoja encargo, oferta, aceptación/rechazo, incumplimiento, reclamación previa, etc.) por cada `tipo_caso` de `TIPOS_CASO_ALL`. Function calling / JSON schema sobre `06_Anonimizado/`. Huecos como `[PENDIENTE]`. Reaprovecha la ontología del cuestionario de viabilidad (82 preguntas) y las plantillas YAML de `data/_plantillas/`.
- **Capa E — extracción por documento**: para cada `.md` en `06_Anonimizado/` se generan claims residuales fuera del esquema. Contexto pequeño = menos alucinación; ningún claim cruza documentos.
- **Capa B — verificador de spans**: cada claim emerge como `(paráfrasis, span_literal, doc, página, párrafo)`. Si el `span_literal` no aparece en el documento citado (con tolerancia OCR razonable), el claim se descarta automáticamente. Cero hechos sin anclaje verificable.

**Output**: `08_Para frontier/_hechos.md` con (i) ficha estructurada del `tipo_caso` y (ii) hechos adicionales por documento. Frontmatter neutralizado sin `case_id` literal (coherente con H5b SaRS1).

**Pasos sugeridos**

1. Definir esquemas de hechos por `tipo_caso` en `data/_plantillas/hechos/`, reaprovechando campos del cuestionario.
2. Implementar capa C (function calling / structured output; Sonnet para campos relacionales, Haiku para campos atómicos).
3. Implementar capa E (extracción doc-a-doc con cita obligatoria).
4. Implementar capa B (verificador de spans con normalización: lowercase + colapso espacios + remoción puntuación; match exacto sobre cadena normalizada, sin Levenshtein, para no aceptar paráfrasis disfrazadas).
5. Integrar como paso del `core/pipeline.py` después de anonimización, antes de `08_Para frontier/`.
6. Tests E2E sobre BaRS1 + SaRS1: cobertura sobre hechos clave + 0 falsos positivos sin anclaje.
7. Decidir: deprecar `hechos_atomicos.md`/`contradicciones.md`/`prueba_indexada.md` legacy en bloque, o mantenerlos como vista interna durante transición. Inclinación Cowork: deprecar — la duplicación crea divergencia.

**Decisiones pendientes (cerrar antes de implementar)**

- Modo del verificador en CI sobre casos en producción: ¿informativo o bloqueante? Inclinación: informativo en primera fase, bloqueante una vez estabilizado.
- Granularidad del span: ¿párrafo entero, oración, o N caracteres alrededor del hecho? Inclinación: oración completa por defecto, ampliable a párrafo si el hecho es relacional.

**Dependencia con la migración Drive → repo**: ninguna. Pueden ejecutarse en paralelo.
