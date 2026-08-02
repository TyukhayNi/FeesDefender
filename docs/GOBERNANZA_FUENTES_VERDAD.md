---
titulo: Gobernanza de las fuentes de verdad
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-05
---

# Gobernanza de las fuentes de verdad — FeesDefender

> Propuesta de unificación y gobernanza ligera. Extiende, sin contradecirlas,
> las decisiones ya cerradas en `PLAN.md`:
> `[CRITICO-FUENTES-VERDAD-PLANIFICACION]` (2026-05-29, bitácora al repo) e
> `[IDEA-GOBERNANZA-DOCS]` (2026-06-10, malla de referencias cruzadas).

## Principio rector

**Cada hecho tiene un único hogar. Todo lo demás enlaza, no copia.**

Si un dato está en el código, la prosa no lo transcribe: lo referencia. Si un
dato es de estado, vive en `STATUS.md` y nadie más lo repite. La regla ya
gobierna la *planificación*; este documento la extiende a **estructura,
taxonomía y arquitectura**, donde hoy quedan copias que se contradicen.

## Drift detectado

| # | Hecho | Copias hoy | Problema |
|---|---|---|---|
| 1 | Nombre del producto | README dice *"FeesGuard"*; el resto *"FeesDefender"* | El primer archivo que lee un recién llegado está desactualizado |
| 2 | Pipeline y stack | README: Ollama/`llama3`, 9 pasos, `00_INPUT` | Describe un MVP ya pivotado (intake CRM + atomización + skills). Contradice `STATUS.md` y `ARQUITECTURA.md` |
| 3 | Estructura de carpetas del caso | README + `ARQUITECTURA.md` + `STATUS.md` (×2) + `config.CASO_SUBDIRS` | 4 prosas + el código. Además choca la convención: README `00_INPUT`, real `00_Input` (regla CLAUDE.md: tipo oración) |
| 4 | Taxonomía de tipos de caso | `core/config.py` (`TIPOS_CASO_*`) **y** `STATUS.md` en prosa | El código es canónico; la prosa se desincroniza sola |
| 5 | Cola de prioridad / "MÁXIMA PRIORIDAD" + estado de ítems | `PLAN.md` **y** `STATUS.md` (×2) | Perdió el `[CRITICO-PRESIGNED-DOWNLOAD-BUG]` (vivía en STATUS, no en la cola de PLAN). **Reincidió 2026-07-08** con `[BIBLIOTECA-CHECKOUT]`: STATUS decía "mergeada", PLAN seguía en "sin commitear" → Cowork leyó el estado obsoleto. Cerrado con hogar único (arriba) + guardarraíl en `session_close` (ver Enforcement) |
| 6 | Specs y planes de diseño | `docs/PLAN_*.md` (11) **y** `docs/superpowers/{specs,plans}` (45) | Dos hogares para lo mismo; un spec nuevo no sabe dónde nacer |
| 7 | Referencia sudespacho común | `INTEGRACION_SUDESPACHO.md` §14 apunta a **otro repo** (`../ElContable/...`) | Fuente de verdad cross-repo sin garantía de que el vecino exista |

## Modelo objetivo: un hecho → un hogar

| Categoría de hecho | Hogar canónico único | Los demás… |
|---|---|---|
| Estado fáctico + bitácora de cierre | `STATUS.md` | — |
| Cola priorizada de trabajo | `PLAN.md` | STATUS borra "Próximas tareas" / "MÁXIMA PRIORIDAD" y enlaza |
| **Estado de ciclo de vida de un ítem** (pendiente / en curso / `✅` + hash del PR) | `PLAN.md` | STATUS narra por sesión y enlaza por etiqueta, **no** es donde se lee el estado actual |
| Rama, worktree, "sin commitear", "mergeado" | **git** (`git log`, `for-each-ref`) | `PLAN.md`/`STATUS.md` **no** los restatan como prosa; al cerrar un ítem se cita solo el hash del PR |
| Flujo git y protocolo de cierre | `docs/FLUJO_GIT.md` | `CLAUDE.md`, `STATUS.md` y el comando `/cierre` enlazan; no repiten el procedimiento |
| Backlog técnico | `docs/MEJORAS_FUTURAS.md` | (ya cableado) |
| Estructura de carpetas del caso | `core/config.py::CASO_SUBDIRS` | README + ARQUITECTURA + STATUS enlazan; ningún `.md` la transcribe |
| Taxonomía de tipos de caso | `core/config.py::TIPOS_CASO_*` | STATUS enlaza; se borra la tabla en prosa |
| Arquitectura y mapa de dependencias | `docs/ARQUITECTURA.md` | STATUS borra "Arquitectura v2" y enlaza |
| Decisiones cerradas / callejones | `PLAN.md` (Resuelto) + `docs/DEAD_ENDS.md` | — |
| Specs y planes de fase | `docs/superpowers/{specs,plans}/` (hogar de los nuevos) | los `docs/PLAN_*.md` legacy se quedan donde están, etiquetados con `estado:` e indexados en `docs/INDICE.md` (no se migran) |
| Convenciones jurídicas / estilo | `docs/CONVENCIONES_DESPACHO.md` + `data/_estilo/contrato_estilo.md` | — |
| Referencia sudespacho común | copia canónica congelada **dentro** de este repo | `INTEGRACION_SUDESPACHO.md` enlaza a la copia local |
| Skills del despacho | `.claude/skills/` (ya decidido) | `_skills_drafts/` → `_skills_ARCHIVO/` o borrar |

## Ejecución por fases

**Fase 1 — bajo riesgo, alto valor (una sesión)**

1. Reescribir `README.md`: FeesGuard→FeesDefender; sustituir "Pipeline/stack" por
   6 líneas + enlaces a `STATUS.md` y `ARQUITECTURA.md`. El README pasa de
   describir a orientar.
2. Borrar de `STATUS.md` las secciones de cola/prioridad y sustituir por un
   puntero a `PLAN.md`. Cierra el agujero que ya provocó un bug perdido.
3. Renombrar `_skills_drafts/` → `_skills_ARCHIVO/` (o eliminar si está muerto).

**Fase 2 — prosa → puntero al código (una sesión)**

4. En `STATUS.md`, reemplazar tablas de taxonomía y las dos estructuras de
   carpetas por enlaces a `core/config.py`. Añadir al mapa de dependencias de
   `ARQUITECTURA.md` la regla "estructura/taxonomía solo en `config.py`".
5. Test guard `tests/test_docs_no_duplican_taxonomia.py` que falle si las claves
   `TIPOS_CASO_*` aparecen literales en `.md`.

**Fase 3 — consolidación (decisión de Nikolai) — HECHA/REVISADA 2026-07-05**

6. **Specs/planes — decisión: etiquetar, no mover.** Migrar físicamente los 11
   `docs/PLAN_*.md` a `docs/superpowers/` es puro *churn* y rompe enlaces, así que
   se descartó. En su lugar: (a) frontmatter `estado:` en cada `PLAN_*.md`
   (`vigente`/`historico`/`aparcado`/`revisar`); (b) `docs/INDICE.md` como índice
   único de ciclo de vida; (c) regla fijada — **los specs nuevos nacen en
   `docs/superpowers/{specs,plans}/`**; los `PLAN_*.md` son legacy y no se crean más.
7. **Vendorizar la referencia sudespacho — DESCARTADO.** El SSOT del equipo
   (`docs/ARQUITECTURA_RELACIONES.md`) define esa referencia como **fuente externa
   compartida** con El Contable y El Auditor (`../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md`),
   fusionada en `docs/INTEGRACION_SUDESPACHO.md §14`. Meterla dentro de este repo
   rompería esa decisión cross-proyecto deliberada. Se mantiene externa.

> **Reconciliación con `docs/ARQUITECTURA_RELACIONES.md` (SSOT):** ese documento,
> creado en paralelo, es el **mapa canónico SSOT** del proyecto (código, plugin,
> skills, estado, sudespacho). Este documento (gobernanza) aporta el *diagnóstico
> de drift*, el plan por fases y las recomendaciones ligeras; para "dónde vive cada
> artefacto", la referencia es la tabla SSOT de `ARQUITECTURA_RELACIONES.md`. No se
> duplican: se complementan.

## Enforcement

- Regla nueva en `CLAUDE.md` §Planificación: *"Estructura de carpetas y taxonomía
  de casos se documentan solo en `core/config.py`. Ningún `.md` las transcribe;
  enlazan."*
- El test guard de la Fase 2 convierte la regla en algo verificable, no en buena
  voluntad.
- **Guardarraíl de coherencia PLAN.md ↔ git (2026-07-08, cierra el Drift #5).**
  `scripts/session_close._avisar_plan_desfasado` (con la lógica pura
  `_plan_items_desfasados`, testeada en `tests/test_session_close_aviso.py`) avisa
  al cerrar —sin bloquear— si `PLAN.md` afirma trabajo pendiente (`sin commitear`,
  `rama de trabajo`, `a la espera de OK`…) en una rama que git ya no conoce
  (mergeada + podada). Convierte "acuérdate de actualizar PLAN.md al mergear" en
  una comprobación que corre sola en el cierre.

---

## Tres recomendaciones de gobernanza ligera

El hilo común: convertir gobernanza en **o un test que ya corre, o un campo que
se lee de un vistazo** — nunca en una norma que hay que recordar.

### 1. Presupuesto de tamaño + rotación de `STATUS.md`

`STATUS.md` crece sin fin porque `session_close` le añade cada cierre (hoy ~1.100
líneas / 253 KB). Separar **estado vigente** (arriba, poca cosa) del **histórico
de cierres**; el histórico se mueve a `docs/bitacora/YYYY.md` cuando STATUS supera
~400 líneas. Un fichero de estado de 253 KB deja de leerse y por eso los hechos
acaban copiándose. *Guardarraíl:* cortar y pegar al archivo del año, sin base de
datos ni changelog automático; el `git log` ya es el histórico fino.

### 2. Automatizar solo los 3-4 invariantes que más duelen

El mapa de dependencias de `ARQUITECTURA.md` ("si tocas X, actualiza Y") depende
de la memoria. No automatizarlo entero (eso sería sobreingeniería): elegir los
pocos invariantes de coste cero en test y dejar el resto como prosa. Candidatos:
README no dice "FeesGuard" ni contradice el stack; taxonomía/estructura no
transcritas en ningún `.md`; `_plantillas/*.yaml` y su `.xlsx` regenerados en el
mismo commit. *Guardarraíl:* engancharlos donde ya corre automatización
(`scripts/session_close`, que ya valida suite verde), no un linter ni CI aparte.

### 3. Ciclo de vida explícito para los docs

Hay ~24 docs en `docs/` + 45 en `superpowers/` y 11 `PLAN_*.md` de los que no se
sabe cuáles siguen vivos. Añadir a cada doc frontmatter `estado: vigente |
histórico | deprecado` + `dueño:` y un único `docs/INDICE.md` que los liste. Al
deprecar no se borra: se marca. El problema no es que sobren docs, es que no se
distingue el vivo del muerto. *Guardarraíl:* un campo de frontmatter y un índice
de una tabla; nada de sitio de documentación. Si acaso, el índice lo autorrenderiza
el mismo patrón YAML→render de las plantillas.

### 4. Higiene de PII en la bitácora del repo → movido a `SEGURIDAD_DATOS.md`

**Diagnóstico (que originó esta recomendación).** La bitácora (`STATUS.md`, `PLAN.md`,
`docs/`), que vive en el repo desde 2026-05-29, acumulaba **dato personal de terceros**
(correos de contrapartes/letrados/agentes, direcciones, nombres) mezclado con
sintéticos de test. No es la prueba (fuera, en `data/CASOS/`), pero es dato RGPD.

**La regla ya no vive aquí.** Su hogar canónico es ahora
[`docs/SEGURIDAD_DATOS.md`](SEGURIDAD_DATOS.md) (principio 7: *referenciar por
`W-XXXXX`, no reproducir*), junto con el resto de la doctrina de fugas de PII/secretos,
los controles y el runbook. Este §4 solo apunta.

**Caveats — resueltos.** Ambos quedaron cerrados el 2026-07-06/07:
- El riesgo dependía de que el repo fuera público → **puesto en privado**.
- La limpieza retroactiva del historial (`git filter-repo`) —que aquí se dejaba como
  "decisión aparte"— **se ejecutó** (Fase 2 del saneado: purga del HAR + `data/_audit/`,
  pseudonimización, repo recreado). Ver `PLAN.md [SANEADO-PII-FASE-2]`.

### 5. Handoffs — andamios efímeros de traspaso

Un **handoff** es un documento **efímero** de traspaso de contexto para arrancar una tarea en otra
sesión/agente. **No es fuente de verdad**: su contenido durable se promueve a spec/plan/runbook/código
(las SSOT); el handoff es el andamio, no el hogar del dato. Regla (aprobada 2026-07-19, `MEJORAS #77`):

- **Ubicación única:** `docs/superpowers/handoffs/`. Lo que deba sobrevivir a la sesión va al **repo,
  nunca a `scratchpad`** (scratchpad solo para andamios de usar-y-tirar intra-sesión). Excepción heredada:
  los stress-tests de la Cronología viven agrupados en `docs/superpowers/specs/cronologia-handoffs/`.
- **Nombre:** `handoff-AAAA-MM-DD-<tema-kebab>.md`. Excepción heredada, la única: el pre-regla
  `prompt_handoff_expedientes_seguros.md` (2026-05-07) conserva su nombre. Las excepciones de nombre
  se declaran **aquí**, no en la vista derivada del `INDICE`; el guard de
  `tests/test_docs_gobernanza.py` lleva la misma lista, así que añadir una obliga a tocar las dos.
- **Estado en el frontmatter (hogar único del estado):** `estado: activo | consumido | historico` +
  `creado`, `origen`, `destino`, `consumido_por` (el spec/plan/PR/runbook donde acabó su contenido durable).
  Campos **añadidos** son libres (p. ej. `revisor`/`veredicto`/`spec` en los handoffs de revisión
  adversarial recibida): el §5 fija un mínimo obligatorio, no un vocabulario cerrado.
- **Qué NO es un handoff:** las revisiones adversariales **producidas dentro del proyecto** como acta
  de adjudicación de un spec no son handoffs; viven junto a su spec como
  `docs/superpowers/specs/AAAA-MM-DD-<tema>-adversarial-review.md` y no llevan este frontmatter.
- **El informe de una revisión adversarial va al ACTA, no al handoff** (decisión de Nikolai,
  2026-08-02). Vale para el informe de una revisión **de un spec, un plan o un diff**, venga de
  dentro o de fuera: su hogar es el acta, con marcadores y `sha256_informe`. El handoff sigue siendo
  el andamio del **traspaso de contexto que no es un informe de revisión**. Contrato:
  `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` §3.1.
  - **Esto acota la decisión anterior** (2026-07-30, sobre los tres
    `handoff-2026-07-27-vista-procesal-codex-*`), que declaraba handoff todo informe **recibido de un
    agente externo**. Chocaba con el contrato, y ninguno de los dos documentos lo decía.
  - **Conjunto cerrado que se queda como está**, sin renombrar ni convertir: los tres de vista
    procesal y `handoff-2026-08-01-identidad-segmento-codex-review{,-2}.md`. **Cinco.**
  - **Y lo que eso cuesta, dicho:** esos cinco **no llevan digest y no pueden llevarlo**. El hash
    solo prueba origen si se calcula al recibir y se contrasta con el del revisor; ese momento pasó.
    Sellarlos ahora sería el revisado firmando su propia transcripción. Su integridad la sostiene
    solo el historial de git. **No son «excepción histórica»:** dos entraron el 2026-08-01.
- **Ciclo de vida:** `activo` (creado, sin consumir) → `consumido` (la tarea arrancó y su contenido durable
  ya vive en su SSOT; se rellena `consumido_por`) → `historico` (se conserva por trazabilidad). El
  `docs/INDICE.md §Handoffs` es **vista derivada** (lista/enlaza), NO el hogar del estado. Un `activo`
  abandonado se borra en un cierre; los `consumido/historico` se conservan con su puntero (como el ledger
  `## Cerrados` de `PLAN.md`).
