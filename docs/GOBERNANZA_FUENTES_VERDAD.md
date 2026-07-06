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
| 5 | Cola de prioridad / "MÁXIMA PRIORIDAD" | `PLAN.md` **y** `STATUS.md` (×2) | Es el fallo que perdió el `[CRITICO-PRESIGNED-DOWNLOAD-BUG]`: vivía en STATUS pero no en la cola de PLAN |
| 6 | Specs y planes de diseño | `docs/PLAN_*.md` (11) **y** `docs/superpowers/{specs,plans}` (45) | Dos hogares para lo mismo; un spec nuevo no sabe dónde nacer |
| 7 | Referencia sudespacho común | `INTEGRACION_SUDESPACHO.md` §14 apunta a **otro repo** (`../ElContable/...`) | Fuente de verdad cross-repo sin garantía de que el vecino exista |

## Modelo objetivo: un hecho → un hogar

| Categoría de hecho | Hogar canónico único | Los demás… |
|---|---|---|
| Estado fáctico + bitácora de cierre | `STATUS.md` | — |
| Cola priorizada de trabajo | `PLAN.md` | STATUS borra "Próximas tareas" / "MÁXIMA PRIORIDAD" y enlaza |
| Backlog técnico | `docs/MEJORAS_FUTURAS.md` | (ya cableado) |
| Estructura de carpetas del caso | `core/config.py::CASO_SUBDIRS` | README + ARQUITECTURA + STATUS enlazan; ningún `.md` la transcribe |
| Taxonomía de tipos de caso | `core/config.py::TIPOS_CASO_*` | STATUS enlaza; se borra la tabla en prosa |
| Arquitectura y mapa de dependencias | `docs/ARQUITECTURA.md` | STATUS borra "Arquitectura v2" y enlaza |
| Decisiones cerradas / callejones | `PLAN.md` (Resuelto) + `docs/DEAD_ENDS.md` | — |
| Specs y planes de fase | un solo directorio (recomendado: `docs/superpowers/`) | los `docs/PLAN_*.md` vivos se migran o se marcan `[HISTÓRICO]` |
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

**Fase 3 — consolidación (decisión de Nikolai)**

6. Elegir un solo hogar para specs/planes; migrar o marcar `[HISTÓRICO]` los
   `docs/PLAN_*.md`.
7. Vendorizar la referencia común de sudespacho dentro del repo.

## Enforcement

- Regla nueva en `CLAUDE.md` §Planificación: *"Estructura de carpetas y taxonomía
  de casos se documentan solo en `core/config.py`. Ningún `.md` las transcribe;
  enlazan."*
- El test guard de la Fase 2 convierte la regla en algo verificable, no en buena
  voluntad.

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
