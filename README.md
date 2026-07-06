# FeesDefender

**Sistema integral de defensa de honorarios** — análisis y preparación
automatizada de reclamaciones de honorarios de intermediación inmobiliaria
(cliente principal: Engel & Völkers). Diseñado en fase MVP para un único
abogado y arquitectado para escalar a producto interno y SaaS.

> **Este README orienta; no es la fuente de verdad.** El estado vigente, la
> arquitectura y la cola de trabajo mandan sobre lo que leas aquí:
>
> - **Estado y bitácora**: `STATUS.md`
> - **Cola de trabajo priorizada**: `PLAN.md`
> - **Arquitectura, mapa de dependencias y flujo**: `docs/ARQUITECTURA.md`
> - **Estructura de carpetas y taxonomía de casos**: `core/config.py` (canónico)
>
> El proyecto arrancó como el MVP descrito aquí y ha crecido por encima de él
> (intake desde el CRM sudespacho, atomización de correo/WhatsApp, skills del
> despacho). Si algo en este README contradice los documentos anteriores,
> mandan ellos.

## Arquitectura

Tres capas estrictamente separadas:

1. **Interfaz** (`streamlit_app.py` + CLIs en `scripts/`): orquesta llamadas al
   core, sin lógica de negocio propia.
2. **Core** (`core/`): lógica de procesamiento, análisis y generación.
   Reutilizable como librería, independiente de la UI.
3. **Datos** (`data/CASOS/<Ciudad>/<case_id>/`): fuente de verdad en ficheros
   `.md` con frontmatter trazable. Sin base de datos externa. Gitignored.

El flujo del pipeline, el mapa de dependencias y el backend LLM se documentan en
`docs/ARQUITECTURA.md`. La estructura de carpetas de cada caso y la taxonomía de
tipos de caso se definen en `core/config.py` (`CASO_SUBDIRS`, `TIPOS_CASO_*`) —
no se transcriben aquí para no duplicar la verdad.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                   # editar con tus rutas y credenciales

# UI
streamlit run streamlit_app.py
```

Variables de entorno y credenciales: `.env.example` y la sección "Credenciales"
de `STATUS.md`. Comandos de apertura/cierre de sesión y atajos: `CLAUDE.md`.

## Principios

- Los `.md` son la fuente de verdad. Nada importante vive solo en memoria ni en
  la UI.
- Separación total UI / core / datos. La UI solo orquesta llamadas al core.
- Automatizar todo lo repetitivo. El abogado no clasifica documentos a mano.
- Explicabilidad: cada `.md` generado por LLM incluye en su frontmatter el
  `prompt_id`, `model` y `prompt_hash` que lo produjeron.
- Confidencialidad: los datos sensibles se anonimizan antes del análisis,
  `data/CASOS/` está en `.gitignore` y `90_NOTAS_PERSONALES/` no la toca ningún
  módulo del core.
- Diseño orientado a SaaS: el `case_id` es la unidad de aislamiento; el core no
  asume ruta única.
