# FeesGuard

**Sistema integral de defensa de honorarios** — análisis y preparación
automatizada de reclamaciones de honorarios de intermediación inmobiliaria.
Diseñado en fase MVP para un único abogado y arquitectado para escalar a
producto interno y SaaS.

## Arquitectura

Tres capas estrictamente separadas:

1. **Interfaz** (`streamlit_app.py`): aplicación local Streamlit. No contiene
   lógica de negocio. Llama al core.
2. **Core** (`core/`): lógica de procesamiento, análisis, scoring y generación.
   Independiente de la UI y reutilizable como librería.
3. **Datos** (`data/CASOS/`): fuente de verdad. Carpeta por caso. Archivos `.md`
   en cada fase del expediente. Sin base de datos externa.

La inferencia LLM corre en local mediante **Ollama** (modelo por defecto
`llama3`). Sin IA en la nube por confidencialidad.

## Estructura del repositorio

```
Base datos expedientes/
├── streamlit_app.py            # UI MVP
├── requirements.txt
├── .env.example                # variables: OLLAMA_HOST, MODEL, RCLONE_REMOTE...
├── core/
│   ├── config.py               # carga de .env y rutas
│   ├── case_manager.py         # crear caso, registrar Drive link
│   ├── sync.py                 # rclone copy desde remoto
│   ├── inventory.py            # inventario JSON de archivos
│   ├── extractor.py            # Docling → texto plano
│   ├── markdown_generator.py   # texto → .md con frontmatter
│   ├── scorer.py               # relevancia heurística + LLM
│   ├── viability.py            # análisis de viabilidad
│   ├── demanda_generator.py    # borrador de demanda
│   ├── linker.py               # [[wikilinks]] entre .md
│   ├── llm.py                  # cliente Ollama
│   └── pipeline.py             # orquestador de pasos
├── prompts/                    # plantillas .md de prompts jurídicos
├── data/CASOS/_PLANTILLA/      # esqueleto de carpetas por caso
├── tests/                      # pytest
├── scripts/                    # utilidades CLI (init_caso, run_pipeline...)
└── docs/                       # documentación interna
```

## Estructura de un caso

```
data/CASOS/{case_id}/
├── 00_INPUT/                   # docs originales (sincronizados desde Drive)
├── 01_PROCESADO/               # texto extraído + .md por documento
├── 02_ANALISIS/                # hechos_atomicos.md, prueba_indexada.md, contradicciones.md
├── 03_DECISION/                # viabilidad.md, scoring.md, decision_litigar.md
├── 04_OUTPUT_PREDEMANDA/       # requerimiento previo, borrador de demanda
├── 05_PROCEDIMIENTO/           # escritos posteriores y resoluciones
├── 06_AI_COWORK/               # notas y prompts ad-hoc del abogado con LLM
└── 90_NOTAS_PERSONALES/        # zona del abogado, no tocada por el sistema
```

Cada `.md` lleva frontmatter YAML con `case_id`, `fase`, `fecha`, `fuente` y
`hash` para trazabilidad.

## Pipeline

`core.pipeline.run(case_id)` ejecuta secuencialmente:

1. `case_manager.ensure_case` — crea estructura si no existe
2. `sync.pull` — `rclone copy` desde el remoto Drive a `00_INPUT/`
3. `inventory.scan` — `00_INPUT/_inventory.json`
4. `extractor.extract_all` — Docling → `01_PROCESADO/raw_text/`
5. `markdown_generator.build` — `01_PROCESADO/{slug}.md` con frontmatter
6. `scorer.score` — `02_ANALISIS/scoring.md` y `documentos_top.md`
7. `viability.analyze` — `03_DECISION/viabilidad.md`
8. `demanda_generator.draft` — `04_OUTPUT_PREDEMANDA/demanda.md`
9. `linker.crosslink` — añade `[[wikilinks]]` entre todos los `.md`

Cualquier paso puede ejecutarse aislado. El pipeline es idempotente: re-ejecutar
sobrescribe `02_ANALISIS/` y posteriores, nunca `00_INPUT/` ni
`90_NOTAS_PERSONALES/`.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                   # editar con tus rutas y modelo Ollama
ollama pull llama3                     # modelo por defecto

# Crear y ejecutar un caso
python -m scripts.init_caso "EV-2026-001" --drive "gdrive:Casos/EV-2026-001"
python -m scripts.run_pipeline "EV-2026-001"

# UI
streamlit run streamlit_app.py
```

## Principios

- Los `.md` son la fuente de verdad. Nada importante vive solo en memoria ni en
  la UI.
- Separación total UI / core / datos. La UI solo orquesta llamadas al core.
- Automatizar todo lo repetitivo. El abogado no clasifica documentos a mano.
- Explicabilidad: cada `.md` generado por LLM incluye en su frontmatter el
  `prompt_id`, `model` y `prompt_hash` que lo produjeron.
- Confidencialidad: LLM local. Sin envío de datos a la nube.
- Diseño orientado a SaaS: el `case_id` es la unidad de aislamiento; el core no
  asume ruta única.

## Estado

MVP funcional: creación de casos, estructura, procesamiento básico, generación
de `.md` clave, análisis inicial con LLM local, visualización en Streamlit y
navegación en Obsidian (los `[[wikilinks]]` se generan automáticamente).

## Próximo objetivo

Reforzar el núcleo jurídico: hechos probatorios, nexo causal, viabilidad
afinada, prompts más rigurosos y preparación avanzada de demanda.
