# Arquitectura — FeesDefender

## Capas

```
┌─────────────────────────────────────┐
│ UI: Streamlit / CLI Typer            │  ← solo orquesta llamadas al core
├─────────────────────────────────────┤
│ Core: pipeline + módulos            │  ← lógica de negocio
│   case_manager · sync · inventory    │
│   sync_sudespacho · sync_sudespacho_legacy
│   sudespacho_create · sudespacho_relations
│   intake_drive                       │  ← pull Drive E&V (rclone gdrive_ev)
│   extractor · markdown_generator     │
│   scorer · viability · demanda       │
│   linker · llm · pipeline            │
├─────────────────────────────────────┤
│ Datos: data/CASOS/{case_id}/        │  ← fuente de verdad (.md)
└─────────────────────────────────────┘
```

## Flujo de un caso

1. **Alta** — `case_manager.ensure_case` crea la estructura de carpetas.
2. **Sync** — `sync_sudespacho.pull_expediente` descarga docs del CRM a `00_INPUT/sudespacho_{id}/`.
3. **Inventario** — `inventory.scan` produce `00_INPUT/_inventory.json`.
4. **Extracción** — `extractor.extract_all` genera texto en `01_PROCESADO/`.
5. **Markdown** — `markdown_generator.build` envuelve cada texto en `.md` con frontmatter trazable.
6. **Scoring** — `scorer.score` puntúa relevancia (heurística + LLM) y emite `02_ANALISIS/scoring.md`.
7. **Análisis** — `viability.analyze` corre cuatro prompts en cadena.
8. **Demanda** — `demanda_generator.draft_demanda` produce `04_OUTPUT_PREDEMANDA/demanda.md`.
9. **Enlazado** — `linker.crosslink` cruza todos los `.md` con `[[wikilinks]]`.

Cada paso es ejecutable de forma aislada. El pipeline es **idempotente**: re-ejecutar nunca toca `00_INPUT/` ni `90_NOTAS_PERSONALES/`.

---

## Mapa de dependencias

> Cuando modifiques un fichero, actualiza también los que aparecen en la columna derecha.

| Si modificas... | También actualiza... |
|---|---|
| `core/config.py` — tipos de caso (`TIPO_*`) | `core/sudespacho_create.py` (constantes `TAG_VERDE_*`, `NOTA_*`, `tag_defaults_for_tipo_caso`), `core/scorer.py` (`KEYWORD_WEIGHTS`), `prompts/scoring.md` |
| `core/config.py` — `CASO_SUBDIRS` | `tests/test_case_manager.py`, `docs/ARQUITECTURA.md` (sección estructura de carpetas) |
| `core/sudespacho_create.py` — campos CRM o endpoints | `docs/INTEGRACION_SUDESPACHO.md` (secciones afectadas) |
| `core/sudespacho_create.py` — constantes `NOTA_*` | `docs/INTEGRACION_SUDESPACHO.md` sección 10 (notas de expediente) |
| `core/sudespacho_create.py` — constantes `TAG_*` | `docs/INTEGRACION_SUDESPACHO.md` sección 8 (sistema de tags) |
| `core/case_manager.py` — `CaseMeta`, `ExpedienteLink` | `tests/test_case_manager.py`, `core/pipeline.py` si consume esos campos |
| `prompts/*.md` | Invalidar frontmatter `prompt_hash` en `.md` generados existentes (re-ejecutar pipeline sobre casos afectados) |
| `core/pipeline.py` — orden de pasos | `docs/ARQUITECTURA.md` sección "Flujo de un caso", `STATUS.md` sección Pipeline |
| `core/intake_drive.py` — campos `CaseMeta` | `core/case_manager.py` (`drive_ev_team_id`, `drive_ev_folder_id`), `tests/test_intake_drive.py` |
| Añadir módulo nuevo en `core/` | `core/__init__.py`, `docs/ARQUITECTURA.md` diagrama de capas, `STATUS.md` inventario |
| Añadir script en `scripts/` | `STATUS.md` sección "Cómo arrancar", `pyproject.toml` si tiene entry point |
| Añadir prompt en `prompts/` | `STATUS.md` inventario, `core/viability.py` o módulo que lo consume |

---

## Convención de commits

Formato: `tipo(scope): descripción concisa en imperativo`

**Tipos:**

| Tipo | Cuándo |
|---|---|
| `feat` | nueva funcionalidad |
| `fix` | corrección de bug o error (incluido error jurídico) |
| `test` | añadir o corregir tests |
| `docs` | solo documentación |
| `chore` | limpieza, refactor, renombrado, reorganización |
| `prompt` | cambio en ficheros de `prompts/` |
| `data` | cambio en plantillas de datos (`_PLANTILLA/`, `.env.example`) |

**Scopes frecuentes:**

`sudespacho_create`, `sync_sudespacho`, `case_manager`, `pipeline`, `scorer`, `viability`, `demanda`, `extractor`, `streamlit`, `docs`, `tests`, `config`

**Ejemplos:**

```
feat(sudespacho_create): add NOTA_* constants + tag_defaults_for_tipo_caso
fix(sudespacho_create): correct art. 20.4 → 20.1 LAU in NOTA_LAU_20
feat(case_manager): implement multi-expediente architecture
test(sync_sudespacho): add test_pull_incremental
docs(arquitectura): add dependency map and commit convention
chore(config): rename FeesGuard → FeesDefender throughout
prompt(viability): reinforce nexo causal jurisprudence
```

---

## Trazabilidad de outputs LLM

Todo `.md` generado por LLM lleva en frontmatter:

```yaml
case_id: BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU
tipo: viabilidad
fase: 03_DECISION
fecha: 2026-04-28T10:31:11
model: llama3
prompt_id: viabilidad
prompt_hash: <sha256 del prompt renderizado>
fuentes: [doc1.md, doc2.md]
quality_score: null   # rellenar tras revisión humana (1-5)
```

El campo `quality_score` (null por defecto) se rellena manualmente tras revisar el output. Es la base para iterar prompts con datos reales en lugar de hacerlo a ciegas.

---

## Aislamiento por caso

`case_id` es la unidad de aislamiento. El core no asume rutas absolutas: todo se compone a partir de `settings.casos_root`. Esto prepara el salto a SaaS multi-tenant: en producción, `CASOS_ROOT` se monta por cliente.

---

## Confidencialidad

- LLM **siempre** local (Ollama). El core no envía nada a la nube.
- Los datos sensibles solo viven en `data/CASOS/`, que está en `.gitignore`.
- `90_NOTAS_PERSONALES/` protegida: ningún módulo del core la lee ni la escribe.

---

## No-objetivos

- **No** clasifica documentos manualmente. Si la heurística falla, se afina el scoring.
- **No** sustituye al criterio del abogado. El sistema produce borradores y análisis.
- **No** depende de Obsidian. Los `[[wikilinks]]` son una conveniencia opcional.
