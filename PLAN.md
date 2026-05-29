# PLAN — FeesDefender

Bitácora de planificación compartida entre Nikolai y Cowork (PC). Edición de
código: solo Claude Code. Aquí van prioridades, decisiones e ideas.

Estado del proyecto y bitácora de cierre de sesión: ver `STATUS.md` (repo).
Historial de commits: `git log`. Acceso móvil: app de GitHub (lectura).

---

## ⚠️ MÁXIMA PRIORIDAD — abrir la próxima sesión por aquí

### [CRITICO-PRESIGNED-DOWNLOAD-BUG] Arreglar descarga del Gestor Documental del CRM

**Detectado:** 2026-05-11 (s8), durante pull v2 del expediente 649 de BaRR3.
**Estado:** abierto, **bloquea pull v2 en todos los casos**.
**Subido a máxima prioridad:** 2026-05-28 a petición de Nikolai (sesión Cowork).
**Detalle completo:** `STATUS.md` líneas 769-810 y `docs/DEAD_ENDS.md`
→ "GET /api/files/presigned_download_url/{doc_id}".

#### Síntoma

El endpoint REST `GET /api/files/presigned_download_url/{doc_id}` devuelve
HTTP 400 para todos los documentos del expediente 649 (26/26 fallos
consecutivos). Body:

    {"@context":"/api/contexts/Error","@type":"hydra:Error",
     "hydra:title":"An error occurred",
     "hydra:description":"Unable to generate an IRI for \"App\\Upload\\Infrastructure\\ApiPlatform\\DTO\\Download\""

Es un error del framework API Platform del backend PHP de sudespacho.
El listado `/api/element_registries/gdocu` funciona y devuelve los 26 docs
con metadatos. Solo la descarga está rota.

Confirmado **operativo el 2026-05-04**, confirmado **roto el 2026-05-11**.

#### Consecuencia

Ningún caso puede completar pull v2 hasta resolverlo. BaRR3 vinculado al
expediente correcto 649 pero sin docs locales. Workaround actualmente en
uso: descarga manual desde la SPA sudespacho.net + subida vía el expander
"📂 Subir al árbol CRM" del tab Casos de Streamlit (paso 7b refactor
intake v2).

#### Pasos a ejecutar en la próxima sesión de Claude Code

1. Capturar HAR de la SPA descargando un doc del expediente 649 desde
   sudespacho.net manualmente: Chrome DevTools → Network → click sobre
   un doc del Gestor Documental → guardar HAR. El usuario sí puede
   descargar desde la web, luego la SPA usa ruta distinta o auth diferente.
2. Comparar el payload con `download_document_rest` en
   `core/sync_sudespacho.py`.
3. Si la ruta REST ha cambiado (renombrado / reorganización del módulo
   Upload del backend), actualizar el endpoint en `download_document_rest`.
4. Si la SPA usa frontal legacy PHP para descargar (`/views/gdocu/...`),
   implementar fallback en `pull_expediente_v2` con PHPSESSID
   (re-introducir la dependencia eliminada el 2026-05-04 para listar +
   descargar, manteniendo la auth REST para crear/vincular).
5. Tests de regresión sobre el expediente 649 hasta lograr 26/26 ✓.

#### Criterios de cierre

- `python -m scripts.sync_sudespacho pull --case <caso BaRR3> --expediente 649 --force`
  baja los 26 documentos sin errores.
- El intake v2 deposita los docs en `00_Input/05_CRM/<rama canónica>/` con
  dedup M9 y log M10 operativos.
- `docs/DEAD_ENDS.md` actualizado con la resolución (causa raíz +
  endpoint definitivo).

---

## Aparcado mientras el bloque crítico no se cierre

- `[SIGUIENTE-ORGANIZADOR-UI]` — botón "Organizar localmente" en
  Streamlit (organizador local Ollama).
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
