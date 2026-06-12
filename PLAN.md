# PLAN — FeesDefender

Bitácora de planificación compartida entre Nikolai y Cowork (PC). Edición de
código: solo Claude Code. Aquí van prioridades, decisiones e ideas.

Estado del proyecto y bitácora de cierre de sesión: ver `STATUS.md` (repo).
Backlog técnico (ideas, bugs latentes, mejoras diferidas): ver
`docs/MEJORAS_FUTURAS.md`. Las entradas se promueven aquí cuando tienen
disparador concreto (caso real, bug bloqueante o decisión de Nikolai),
con referencia al número original (`MEJORAS #NN`).
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

## [SIGUIENTE-INTAKE-PROCURADORES-EMAIL] Intake automático de correos de procuradores → Sudespacho
*Diseño cerrado con Nikolai 2026-06-12. Plan fino autocontenido: `docs/PLAN_INTAKE_PROCURADORES_EMAIL.md`. Implementación: Claude Code.*

**Objetivo.** Sentido inverso del intake actual: archivar en el CRM los correos de
procuradores (y contestaciones a correos del despacho), relacionarlos con su
expediente y subir adjuntos con nombre legible, con red de seguridad humana antes
de escribir. Llave de emparejamiento = *Su ref* (= `num_expediente/serie`,
serie=año). **RGPD — excepción acotada SOLO a este flujo:** usa LLM cloud UE
(Scaleway/Mistral Small 3.2); no deroga la regla general del resto del repo.

**Estado por fases (detalle en el doc §15):**
- **F1 — Matcher (read-only).** ✅ HECHA (s39, 2026-06-12). `core/llm_cloud.py`
  (conector LLM cloud intercambiable) + `core/procurador_intake.py` (señales LLM +
  match por num/serie vía REST + propuesta de nombres). Validado e2e contra correos
  reales (ProcuradoraF 21/25→exp #532, Castañeda 33/2024→exp #455, ambos confianza
  ALTA). API `element_registries` usa `hydra:member`. Volumen ~7 correos/día,
  ~€0.10/mes. Tests +77; suite **853 passed, 58 skipped**. **Commits `f904d72`,
  `6a811ef`** (F1 base + fix match por su_ref con sufijo de subserie y `es_ruido`
  advisory).
- **F2 — Bandeja (Streamlit).** 🔶 BACKEND ✅ / UI ⬜. **Backend completo (s40, dry-run, TDD):**
  `core/procurador_review.py` (terna §18.9 + divergencia + log auditoría + máquina de
  estados de cola + store de cola), `core/procurador_runner.py` (process_email +
  run_intake, enrutado §6, dedup §4), `core/gmail_source.py` (adaptador Gmail
  verificado live read-only). Commits `a80afeb`/`00ee3b8`/`7b03759`/`3bedb22`/`95082f1`.
  El **requisito duro §18.9** quedó cumplido: la terna se captura en `record_decision`.
  **Pendiente:** la **UI Streamlit** (pestaña "Bandeja": 3 tarjetas 🟢/🟡/🔴 + login por
  persona `set_actor` + acciones→`transicionar`/`record_decision`/`upsert_queue_item` +
  vista Descartados) — orquesta el core, sin lógica nueva. Y un CLI/scheduler thin que
  llame a `fetch_and_run` periódicamente (§3).
- **F3 — Escritura en el CRM.** ⬜ Resolver auth nest-mail (x-api-key vs JWT);
  relate + adjuntar en expediente de prueba. Mismo requisito de traza que F2.
- **F4 — Renombrado + OCR + aprendizaje.** ⬜ Contenido del adjunto → nombre; store
  de correcciones few-shot (§10).
- **F5 — Grabaciones.** ⬜ Descarga de enlaces (WeTransfer caduca) + fallback manual.
- **F6 — Control de calidad del archivo (check 2).** ⬜ Capa de auditoría por
  excepción (auto-chequeo determinista + cola de Paola + resumen semanal a Nikolai).
  **Diseño cerrado 2026-06-12, doc §18.** Depende de F2/F3 (consume la terna de traza).

**Pendientes de decisión (doc §17 + §18.11):** ¿confirmar en bloque las de alta de
inicio? · auth nest-mail · plazos de escalado de la cola por tipo · tamaño de muestra
(default 10%) · lista de "tipos con plazo".

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

**Siguiente acordado — `[SIGUIENTE-INTAKE-CRM-COMPLETO]` (sesión 2026-06-10):**
bajar TODO el expediente del CRM a `05_CRM` físicamente completo (sin que el
dedup M9 lo deje incompleto) + OCR/markdown/anonimización con el pipeline actual
+ contador de solapamientos byte-idénticos (para decidir con datos si el "dedup
en extracción" merece construirse, que queda APLAZADO). Plan fino autocontenido
para hilo nuevo: **`docs/PLAN_INTAKE_CRM_COMPLETO.md`**.

**Siguiente acordado — `[SIGUIENTE-DEDUP-GUARD-ROBUSTO]` (apuntado 2026-06-10):**
guarda para **no duplicar expedientes ni en el CRM ni en el Drive** al crear un
caso. Hoy es frágil a variaciones tipográficas de la referencia/nombre.

- **Problema detectado (2026-06-10):** el botón «Crear caso + enviar a sudespacho»
  NO bloquea el expediente 444 porque su `referencia_cliente` en el CRM tiene un
  **doble espacio** (`(W-02NV4W)  - Vuelta`) y el case_id estándar lleva uno solo
  → la búsqueda exacta `find_expediente_judicial_by_referencia` devuelve `None` →
  **crearía un expediente duplicado**.
- **Qué hacer:**
  1. **Guarda CRM** (`core/sudespacho_relations.py`,
     `find_expediente_*_by_referencia` / `verify_expediente_referencia`):
     comparar referencias **normalizadas** (espacios repetidos colapsados, sin
     acentos, sin distinción de mayúsculas; reutilizar `_normalize_label`).
  2. **Guarda Drive** (`core/intake_drive.py`): aplicar la misma normalización al
     emparejar caso ↔ carpeta E&V por nombre/referencia, para no crear/pullar a
     una carpeta duplicada (revisar dónde se hace el match).
  3. **UI** (`streamlit_app.py` ~L1675): el aviso «no se creará un expediente
     duplicado» es **engañoso** — mira el `_caso.md` local y NO impide la
     creación; la única protección real es la búsqueda en el CRM. Corregir el
     texto y/o hacer que la guarda CRM realmente bloquee.
- **Riesgo si no se hace:** expedientes/carpetas duplicados, caros de deshacer.

---

## [SIGUIENTE-INTAKE-ENTREVISTAS] Intake dedicado de entrevistas (transcripción Meet) en `06_Entrevistas/`
*Promovido 2026-06-10 (sesión Cowork) por decisión de Nikolai. `MEJORAS #26`. Implementación: Claude Code.*

**Objetivo.** Cablear la subida de la entrevista de viabilidad (grabada en Google
Meet, transcripción automática) al árbol del caso, hoy sin conectar.

**Estado verificado (repo, 2026-06-10).** El andamiaje existe pero está muerto:
`ensure_case` crea `00_Input/06_Entrevistas/`; `ENTREVISTA_ROLES`
(`core/config.py`) y la convención `<AAAA-MM-DD>_<rol>_<apellido>/` están
definidas pero **ningún código las consume ni valida**; el evento
`upload_entrevista` (`core/intake_log.py`) y el source `"entrevista"`
(`core/intake_manifest.py`) están declarados pero **nunca se emiten**. No existe
`core/intake_entrevista*.py` ni uploader en Streamlit. El paso 7 del refactor v2
solo cableó el expander de subida a `05_CRM`. Hoy la entrevista solo entra si el
letrado deja manualmente la transcripción en la carpeta, sin dedup ni traza.

**Solución (ya recogida en `docs/MEJORAS_FUTURAS.md` §26).** No requiere
transcripción local (Whisper): Meet ya entrega texto. Dos piezas:

1. **Función de ingesta** (`core/intake_entrevista.py` nuevo o ampliación de
   `core/intake_manual.py`): dado rol ∈ `ENTREVISTA_ROLES`, apellido, fecha y el
   Doc de Meet, crea `06_Entrevistas/<AAAA-MM-DD>_<rol>_<apellido>/`, coloca la
   transcripción exportada a `.docx`/`.txt`, la registra en el manifest con
   `source="entrevista"` y emite el evento `upload_entrevista`. Validar rol contra
   `ENTREVISTA_ROLES` y sanear el path como en `save_file_crm_branch`.
2. **Disparo en la UI** (expander/botón en el tab Casos de Streamlit), análogo al
   de `05_CRM`.

Una vez el `.docx`/`.txt` está en `00_Input/06_Entrevistas/`, el pipeline genérico
(inventory → extractor → markdown → anon) ya lo procesa. La 2ª pasada de
`viabilidad-prerelleno` (leer la transcripción para cerrar huecos testificales)
queda fuera de alcance de este bloque.

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

### ✅ Idea de gobernanza documental — `[IDEA-GOBERNANZA-DOCS]` RESUELTO 2026-06-10

Implementada la malla de referencias cruzadas y regla de promoción:
- `docs/MEJORAS_FUTURAS.md` retitulado a "backlog técnico" (alcance: todo el repo).
- Cabecera de `MEJORAS_FUTURAS.md` con referencia a `PLAN.md` y convención
  `[PROMOVIDO → PLAN.md]`.
- Cabecera de `PLAN.md` con referencia a `docs/MEJORAS_FUTURAS.md` y convención
  `MEJORAS #NN`.
- Regla de promoción documentada en `CLAUDE.md` §"Planificación y estado":
  disparador concreto (caso real, bug bloqueante, decisión de Nikolai).

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

---

## [SIGUIENTE-REORG-05CRM] Aplanado de `05_CRM` por buckets procesales + detector de conjunto
*Añadido 2026-06-10 (sesión Cowork). 15 decisiones aprobadas por Nikolai. Implementación: Claude Code. Capa de nombrado/bundles (D1-D3) documentada en `docs/MEJORAS_FUTURAS.md` #28-#29.*

> **✅ PRIMERA TANDA COMPLETADA 2026-06-10 (Claude Code).**
> - [x] **Paso 0 / D8** — `CARPETA_ID_TO_PATH` poblado: `308`→Declarativo/Oposicion,
>   `380`→Preliminares/Demanda. Descubiertos vía `category_unknown`, doble
>   verificación UI (Nikolai) + REST. Solo había 2 IDs no mapeados en toda la
>   data real. El endpoint de árbol es dead end (§13.3); rama ambigua se cierra en UI.
> - [x] **D6** — `_bucket_for(rama_canonica)` (pura) + exclusión Preliminares,
>   aplicada en `crm_branch_path` (`core/case_manager.py`). Routing por rama
>   completa, no por etiqueta-hoja.
> - [x] **D7** — andamiaje *lazy*: `_ensure_crm_tree_dirs` crea solo `05_CRM/`;
>   los buckets se materializan al escribir. **D15** documentado (05_Procedimiento).
> - [x] **D12-D13** — `scripts/migrate_05crm_buckets.py` (in situ, sin re-bajar
>   ni re-OCR; re-llave manifest + extract_state; colisión de stem; by_carpeta;
>   journal + .bak). **Expediente 444 migrado**: 96 docs → {01_Demanda:23,
>   05_Diligencias_Preliminares:31, 99_Otros:42}, 0 colisiones, 0 re-OCR.
> - [x] **D14** — `test_crm_branch_path.py` reescrito (buckets + anti-sobrecaptura
>   + unit de `_bucket_for`), `test_pull_expediente_v2.py` y `test_smoke_paso7.py`
>   actualizados, `test_migrate_05crm_buckets.py` nuevo. `test_dedup_manifest.py`
>   y `test_judicial_intake.py` revisados (agnósticos a ruta, sin cambios).
>   Suite verde; gold SaRS1 intacto.
>
> **✅ SEGUNDA TANDA COMPLETADA 2026-06-10 (Claude Code, sesión 35).**
> - [x] **D10** — `fechamodificacion` traída al listado REST
>   (`properties[12]`) + campo `modified_at` en el DTO `GdocuDocInfo`.
>   Nombre/formato confirmados **en vivo** contra el 444
>   (`scripts/probe_gdocu_fecha.py`; 97/97 docs con fecha). ISO-8601 con offset.
> - [x] **D9** — detector de conjunto (`core/conjunto_detector.py`): clúster por
>   `modified_at` idéntico ∩ patrón `\bD\s*\d+…-`; cabecera = odd-one-out sin
>   patrón (en el 444 es `ORDINARIO…VALLDAURA.doc`, **no** "DEMANDA" → keyword
>   solo como desempate); bucket por cabecera o consenso; baja confianza →
>   `pendiente_revision`. **Solo emite propuestas** (eventos `conjunto_detectado`
>   / `pendiente_revision`); **persistencia de `parent_id` DIFERIDA** a
>   `[SIGUIENTE-CATALOGO-DOCUMENTAL]` (catálogo `indice_documental.yaml` **no
>   existe** — decisión de Nikolai: no construirlo a medias). Validado contra el
>   444 real (3 lotes, 0 misrouting). CLI on-demand
>   `scripts/detectar_conjuntos.py`. Nuevo evento `conjunto_detectado` (INTAKE_EVENTS 16→17).
> - [x] **D11** — override local `doc_id→bucket` en `bucket_override` del
>   frontmatter de `_caso.md`, respetado por `crm_branch_path` por encima de la
>   carpeta del CRM (`kind == "override"`), sin tocar el CRM remoto. Cableado en
>   el pull (lectura única por corrida). Refactor: `resolve_bucket` como fuente
>   única de la resolución carpeta→bucket (compartida con el detector).
> - **Pregunta abierta resuelta:** confirmado contra el 444 que **solo la prueba
>   de la actora usa `D NN`**; cabecera y contestación NO → la cabecera se
>   detecta como el doc sin patrón.
> - **Tests:** +3 D10, +~13 D9 (`test_conjunto_detector` nuevo), +7 D11,
>   `test_intake_log` (17 eventos). **Suite: 652 passed, 58 skipped** (verja
>   rápida, EXCLUYENDO `test_sudespacho_relations.py` — ver ⚠️). Gold SaRS1 intacto.
> - **⚠️ Ajeno a esta tanda:** `core/sudespacho_relations.py` + su test están
>   modificados en el working tree por trabajo concurrente (no por esta sesión;
>   al inicio NO estaban modificados) y rompen la colección de pytest por import
>   circular. No se tocaron ni commitearon — revisar aparte.
>
> **Pendiente (TERCERA TANDA / futuro):** persistencia `parent_id` de D9 cuando
> exista `[SIGUIENTE-CATALOGO-DOCUMENTAL]`. Follow-up del intake manual (abajo)
> sigue sin abordar (requiere OK de Nikolai por ripple a UI).
>
> **Follow-up detectado (fuera de las 15 decisiones, decisión de Nikolai):** el
> intake **manual** (`intake_manual.save_file_crm_branch` + `list_crm_branch_files`
> + selector `CRM_TREE` en `streamlit_app.py:630`) sigue escribiendo a la rama
> profunda elegida en la UI; convendría bucketizarlo también (vía `_bucket_for`)
> para no recrear el árbol profundo que la migración elimina. No se tocó por
> estar fuera del alcance de la primera tanda (ripple a UI + ~6 tests de
> `test_smoke_paso7.py` no listados en D14).

**Objetivo.** Sustituir el árbol profundo del CRM en `00_Input/05_CRM/` (hasta 4
niveles + ~20 carpetas vacías de andamiaje) por una estructura plana de un nivel
con buckets procesales. Motivos: límite de ruta de Windows (260 car.) sobre un
Drive ya largo, y desorden de carpetas vacías. La estructura de `05_CRM` es
**solo navegación humana del input**: el pipeline (`extractor` →
`markdown_generator` → `anon`) aplana a un output por documento con slug
stem-only (`extractor.py:214`), independiente de la subcarpeta de origen.

**Árbol confirmado (D5).**

```
05_CRM/
├── 01_Demanda/                  ← Declarativo/Demanda (demanda + su prueba documental)
├── 02_Contestacion/             ← Declarativo/Oposicion (un solo bucket aunque haya varios demandados — D5b)
├── 03_Monitorio_Demanda/        ← Monitorio/Demanda (petición inicial + docs)
├── 04_Monitorio_Oposicion/      ← Monitorio/Oposicion (+ docs)
├── 05_Diligencias_Preliminares/ ← Preliminares/Demanda (solicitud de DP + docs)
├── 99_Otros/                    ← resto PLANO por fecha (procesales, resoluciones, Apelación, Ejecución, General, Documentos, RGPD/LOPD, Penal…)
└── 99_Sin categoria/<exp>/      ← fallback cuando id_carpeta no resuelve (ya existe hoy)
```

**Decisiones aprobadas (registro).**

- **D5 — Aplanar a 1 nivel** con el árbol de arriba. Cada bucket mapea 1:1 a una
  hoja real de `CRM_TREE`; se aplana el andamiaje intermedio
  (`Civil/1ª Instancia/Declarativo/…`), no las hojas con significado.
- **D6 — Routing por rama canónica completa, no por etiqueta-hoja.** Función pura
  `_bucket_for(rama_canónica)` aplicada en `crm_branch_path` (`case_manager.py:524`,
  único punto de routing, invocado en `sync_sudespacho.py:1444`). `Preliminares`
  en **lista de exclusión explícita**: su "demanda" (solicitud de DP) **nunca**
  cae en `01_Demanda` → va a `05_Diligencias_Preliminares`. Etiqueta-hoja pura
  sobre-captura (`"Demanda"` casa 3 ramas, `"Oposicion"` 2 → hoy ambas caen a
  fallback, confirmado por `test_crm_branch_path.py`).
- **D7 — Cambiar también el andamiaje** (`_scaffold_crm_tree`,
  `case_manager.py:841`): crear solo los buckets en uso o ir *lazy*
  (crear-al-escribir). Tocar solo el routing dejaría las carpetas vacías.
- **D8 — Requisito previo (paso 0): poblar `CARPETA_ID_TO_PATH`** con los
  `id_carpeta` reales del tenant para las ramas procesales (hoy solo 2 IDs
  mapeados; las etiquetas son ambiguas → casi todo cae a `99_Sin categoria`).
  Descubrimiento progresivo vía evento `category_unknown` ya existente. **Sin
  esto, aplanar es cosmética.** Doble verificación UI + API.
- **D9 — Detector de conjunto** para reagrupar cabecera + prueba **mal archivadas**:
  clúster por *timestamp de modificación del CRM idéntico* (subida en lote) ∩
  *patrón de nomenclatura* `D\s*\d+\s*-` (numeración de prueba del despacho; admite
  sub-índice `22-C`/`22-D`). Se ancla cada lote a su cabecera (`DEMANDA…`/
  `CONTESTACION…`) por cercanía temporal y se asigna al bucket de la cabecera.
  Clústeres de baja confianza → `pendiente_revision`, sin adivinar. La relación
  se persiste como `parent_id` en `indice_documental.yaml` (MEJORAS #29) →
  sobrevive aunque los ficheros queden físicamente dispersos.
- **D10 — Requisito previo de D9: traer la fecha de modificación del CRM.** Hoy
  NO se pide: la query REST solo trae `nombrefinal`/`mime`/`tamano`/`id_carpeta`
  (`sync_sudespacho.py:649-653`) y `GdocuDocInfo` no tiene campo de fecha
  (`:297-303`). Descubrir el índice de esa propiedad y añadir el campo al DTO.
- **D11 — Override local `doc_id → bucket`** editable por el letrado (en
  `_caso.md` o YAML del caso), respetado por encima de la carpeta del CRM, **sin
  tocar el CRM remoto**. Parche inmediato para el mal archivo.
- **D12 — Migrar in situ, NO re-bajar.** El re-pull no migra limpiamente: el
  dedup es por hash (`IntakeManifest.register`), así que un re-pull sin resetear
  manifest devuelve el `primary_path` viejo → con `physical_complete=True`
  duplica (copia vieja + nueva), con `False` no mueve. Migración: mover ficheros
  + reescribir `00_Input/_intake_hashes.json` (rel viejo→nuevo, o borrarlo y dejar
  que `reconcile()` reconstruya desde disco) + re-llavear
  `01_Procesado/raw_text/_extract_state.json` (clave = `rel_path`,
  `extractor.py:218`; los `.txt` NO se mueven, slug = stem) + `inventory.scan`.
  Así `extract_all` hace skip y **no re-OCRiza** los 96 docs del 444. Script
  puntual, no feature.
- **D13 — Pre-migración:** detectar **colisiones de stem** entre ramas que
  confluyan al mismo bucket (forzarían `__1` vía `_resolve_name_collision` →
  cambio de slug → re-OCR; o renombrar también el `.txt`). Refrescar `by_carpeta`
  en el frontmatter de `_caso.md` (queda rancio tras migrar).
- **D14 — Tests.** Asumir cambio de semántica de conteos (`documents_overlap`
  baja, `documents_skipped_dedup` sube — no es bug). Reescribir
  `test_crm_branch_path.py` (expectativas profundas → buckets + tests
  anti-sobrecaptura: `Preliminares/Demanda`→`05_…`, `Declarativo/Oposicion`→
  `02_…`, `Monitorio/Demanda`→`03_…`); actualizar `test_pull_expediente_v2.py` y
  `test_dedup_manifest.py` (claves `by_carpeta` + conteos); revisar
  `test_judicial_intake.py` (mayormente agnóstico a ruta). Añadir unit de
  `_bucket_for()` y test del script de migración (idempotencia + preservación de
  cache OCR + colisión de stem). El gold fixture **SaRS1 no se toca** (es upstream
  del anon; confirmar ejecutando la suite).
- **D15 — `05_Procedimiento`** (carpeta funcional de fase, hoy inerte: nadie
  escribe en ella; solo la crea el scaffolding y la barre `linker.py:19`).
  Mantener su rol semántico de **work-product del letrado para el litigio en
  curso**, diferenciado del espejo crudo del CRM (`00_Input/05_CRM/`). Documentar
  su propósito (hoy no consta). Aplicarle el criterio *lazy* de D7. Anotar la
  duplicidad del "05" (`00_Input/05_CRM` vs `05_Procedimiento`) como cosmética de
  baja prioridad.

**Capa de nombrado/bundles (D1-D3) → `docs/MEJORAS_FUTURAS.md`:** D1 (prefijo ISO
`AAAA-MM-DD`) y D2 (alcance solo `06_Anonimizado`/`INDICE.md`, identidad =
`id_doc`/hash) amplían #28; D3 (bundles cabecera-anexo por `parent_id` en el
catálogo, no subcarpeta física) es #29. D4: fuente única de verdad documental;
no se parchea el motor de anonimización (D8 histórico / `feedback_anon_logica_intacta`).

**Lo que NO se toca (F):** motor de anonimización, `separar.py`, `linker.py`,
independencia de `01_Procesado`/`06_Anonimizado` respecto a `05_CRM`, y la
decisión ya cerrada de descartar el organizador Ollama / vista `_organizado/`.

**Orden de ejecución recomendado.** Paso 0 (D8 descubrir IDs del tenant) →
routing `_bucket_for` + exclusión Preliminares (D6) + andamiaje lazy (D7) →
migración in situ del 444 preservando OCR (D12-D13) → tests (D14). El detector de
conjunto (D9) y su requisito (D10) y el override (D11) pueden ir en una segunda
tanda. Medir antes la ruta más larga real del 444: aplanar `05_CRM` solo ahorra
~30 car.; si no basta para cruzar 260, combinar con rutas largas `\\?\` o acortar
el ensamblado de nombre.

**Pregunta abierta (no bloquea):** confirmar contra una carpeta de contestación
real si el **demandado usa el mismo prefijo `D NN`** u otro, para afinar D9.
