# Arquitectura de FeesGuard

## Capas

```
┌─────────────────────────────────────┐
│ UI: Streamlit / CLI Typer            │  ← solo orquesta llamadas al core
├─────────────────────────────────────┤
│ Core: pipeline + módulos            │  ← lógica de negocio
│   case_manager · sync · inventory    │
│   extractor · markdown_generator     │
│   scorer · viability · demanda       │
│   linker · llm                       │
├─────────────────────────────────────┤
│ Datos: data/CASOS/{case_id}/        │  ← fuente de verdad (.md)
└─────────────────────────────────────┘
```

## Flujo de un caso

1. **Alta** — `case_manager.ensure_case` crea la estructura.
2. **Sync** — `sync.pull` trae los originales desde el remoto rclone a
   `00_INPUT/`.
3. **Inventario** — `inventory.scan` produce `00_INPUT/_inventory.json`.
4. **Extracción** — `extractor.extract_all` genera `01_PROCESADO/raw_text/*.txt`.
5. **Markdown** — `markdown_generator.build` envuelve cada texto en `.md` con
   frontmatter trazable.
6. **Scoring** — `scorer.score` puntúa relevancia (heurística + LLM) y emite
   `02_ANALISIS/scoring.md` y `documentos_top.md`.
7. **Análisis** — `viability.analyze` corre cuatro prompts (`viabilidad`,
   `hechos_atomicos`, `prueba_indexada`, `contradicciones`).
8. **Demanda** — `demanda_generator.draft_demanda` produce
   `04_OUTPUT_PREDEMANDA/demanda.md`.
9. **Enlazado** — `linker.crosslink` cruza todos los `.md` con `[[wikilinks]]`.

Cada paso es ejecutable de forma aislada y el pipeline es idempotente.

## Trazabilidad

Todo `.md` generado por LLM lleva en frontmatter:

```yaml
case_id: EV-2026-001
tipo: viabilidad
fase: 03_DECISION
fecha: 2026-04-25T10:31:11
model: llama3
prompt_id: viabilidad
prompt_hash: <sha256 del prompt renderizado>
fuentes: [doc1, doc2, ...]
```

Esto permite reproducir cualquier output: con el mismo `prompt_hash`, el
mismo modelo y los mismos `.md` fuente, se obtiene un resultado equivalente
(salvo el componente estocástico del LLM, controlado por temperatura baja).

## Aislamiento por caso

`case_id` es la unidad de aislamiento. El core no asume rutas absolutas: todo
se compone a partir de `settings.casos_root`. Esto es lo que prepara el salto
de MVP local a SaaS multi-tenant: en producción, `CASOS_ROOT` se monta por
cliente, sin tocar el core.

## Confidencialidad

- LLM **siempre** local (Ollama). El core no envía nada a la nube.
- Los datos sensibles solo viven en `data/CASOS/`, que está en `.gitignore`.
- `90_NOTAS_PERSONALES/` está protegido: ningún módulo del core lo lee ni lo
  escribe.

## No-objetivos

- **No** clasifica documentos manualmente. Si la heurística falla, se afina el
  scoring; no se sube la fricción al usuario.
- **No** sustituye al criterio del abogado. El sistema produce borradores y
  análisis: la decisión jurídica es humana.
- **No** depende de Obsidian. Los `[[wikilinks]]` son una conveniencia para
  navegación; el sistema funciona igual sin Obsidian.
