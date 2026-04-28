# Guía de desarrollo

## Setup local

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Ollama
ollama pull llama3                     # o el modelo que uses

# rclone (opcional, para sync con Drive)
rclone config                          # crear remoto "gdrive"
```

## Ejecutar

```bash
# UI
streamlit run streamlit_app.py

# CLI
python -m scripts.init_caso EV-2026-001 --drive gdrive:Casos/EV-2026-001
python -m scripts.run_pipeline EV-2026-001
```

## Tests

```bash
pytest -q
```

## Estilo

- Python 3.11+, type hints obligatorios.
- `ruff` configurado en `pyproject.toml`.
- Funciones públicas con docstring breve en español.

## Añadir un nuevo análisis (.md)

1. Crear el prompt en `prompts/<id>.md` con variables `{{case_id}}` y
   `{{contexto}}`.
2. Añadir en `core/viability.py` una entrada al `analyze()` o crear un módulo
   propio si la fase es distinta.
3. El frontmatter del `.md` debe incluir `prompt_id`, `model`, `prompt_hash`
   y `fuentes`.

## Añadir un dominio nuevo (no-honorarios)

1. Duplicar `prompts/` en `prompts/<dominio>/` y ajustar.
2. En `core/scorer.py`, mover `KEYWORD_WEIGHTS` a un dict cargado desde JSON
   por dominio.
3. Añadir un campo `dominio` al frontmatter de `_caso.md`.

## Convenciones de nombres

- `case_id`: `XX-AAAA-NNN` (ej. `EV-2026-001`, `MED-2026-014`).
- Slugs: minúsculas, snake_case, sin tildes (función `slugify`).
- Archivos `.md` clave: nombres canónicos (no inventarlos): `viabilidad`,
  `hechos_atomicos`, `prueba_indexada`, `contradicciones`, `demanda`,
  `requerimiento_previo`, `scoring`, `documentos_top`.
