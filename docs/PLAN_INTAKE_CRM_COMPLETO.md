# PLAN — Intake CRM completo a `05_CRM` + OCR/anon + contador de solapamientos

> **Para retomar en un hilo nuevo.** Documento autocontenido. Decisión cerrada
> con Nikolai el 2026-06-10. Implementación pendiente (Claude Code).
> Identificador de backlog: `[SIGUIENTE-INTAKE-CRM-COMPLETO]`.

## Objetivo

Que el cajón `00_Input/05_CRM/` de un caso quede **físicamente completo** (todo
el expediente del gestor documental del CRM, demanda + contestación + prueba +
procesales), y que esos documentos pasen por **OCR → markdown → anonimización**
para trabajar con LLM sobre ellos. Hoy el intake judicial solo baja
demanda+contestación, y el dedup M9 puede dejar `05_CRM` incompleto.

## Decisiones cerradas (sesión 2026-06-10)

1. **Bajar TODO el expediente** a `05_CRM` (no solo demanda+contestación), con
   la demanda/contestación **etiquetadas** (clasificador como tagging, no filtro).
2. **`05_CRM` físicamente completo**: el pull del CRM escribe copia física
   **aunque** un documento sea byte-idéntico a uno ya presente de otra fuente
   (Drive E&V). M9 sigue **anotando la procedencia/alias**, solo deja de
   **suprimir** la copia física en `05_CRM`.
3. **Contador de solapamientos**: instrumentar cuántos docs del CRM son
   byte-idénticos a otros ya presentes (para decidir con datos si el
   "dedup en extracción" merece construirse).
4. **OCR/anon con el pipeline actual** (caso entero, incremental). NO se
   construye scoping por subcarpeta ahora.
5. **Dedup elegante (mover dedup del intake a la extracción) = APLAZADO**: solo
   se construye si el contador demuestra que hay solapamiento real significativo.
6. Bundle de análisis **mezclado** con el del caso (no bundle procesal aparte).

## Contexto verificado (código actual, leído 2026-06-10)

- **Descarga ya arreglada** (sesión 33): `get_presigned_download_url` usa
  `GET /api/documents/{id}/downloadUri` → `presignedDownloadUrl`. Commits
  `ecf70ec`, `1242a1a`, `ec37fc4`, `597c2f5`. Ver `STATUS.md` (sesión 33) y
  `docs/DEAD_ENDS.md` (entrada ✅ RESUELTO).
- **`pull_expediente_v2`** (`core/sync_sudespacho.py`) ya baja todo a
  `05_CRM/<rama>/` con routing (`crm_branch_path`), dedup M9
  (`IntakeManifest.register`), log M10 y estado D8. Acepta `only_doc_ids` (None =
  todo). Acepta `client`, `actor`.
- **`IntakeManifest.register(sha, rel, *, source, **alias)`**
  (`core/intake_manifest.py`) devuelve `("write", rel)` si el SHA es nuevo, o
  `("skip", primary)` si ya existe (y registra `rel` como alias si difiere del
  primary). El **skip físico** es lo que deja `05_CRM` incompleto.
- **`intake_demanda_contestacion`** (`core/judicial_intake.py`) lista → clasifica
  → pull acotado (`only_doc_ids={demanda,contestación}`). El clasificador
  (`core/judicial_classifier.py`) es heurístico por filename (sin LLM).
- **Pipeline** (`core/pipeline.py::run`): caso entero. Pasos:
  `inventory.scan` → `extractor.extract_all` (OCR Docling, **incremental por
  hash** desde s32) → `markdown_generator.build` → `scorer` → `viability` →
  `demanda` → `anon.anonimizar_caso` (si `do_anonimizar=True`). NO hay dedup por
  contenido aguas abajo.
- **`inventory.scan`** recorre `00_Input/` con `rglob("*")` y calcula `sha256`
  por fichero → `05_CRM` se inventaría con su hash ya disponible.
- **`extractor.extract_all`** produce `01_Procesado/raw_text/{slug}.txt` por
  documento; estado en `_extract_state.json` (hash de origen por doc).
  Dos paths con el mismo contenido → dos slugs → dos `.txt`/`.md`/anon (= el
  duplicado que el dedup aplazado eliminaría).
- **`INTAKE_EVENTS`** (`core/intake_log.py`) es un set CERRADO (hoy 15 eventos).
  Añadir uno obliga a actualizar `tests/test_intake_log.py`
  (`test_intake_events_es_frozenset_con_15_eventos` y la lista canónica).

## Paso 1 — `05_CRM` completo + bajar todo + contador (CÓDIGO)

### 1.1 `core/sync_sudespacho.py`

- `PullResultV2`: añadir campo `documents_overlap: int = 0` (copias byte-idénticas
  escritas igualmente por `physical_complete`).
- `pull_expediente_v2(..., only_doc_ids=None, physical_complete: bool = False)`:
  - En el bucle de docs, tras `action, primary_rel = manifest.register(...)`:
    - `action == "write"` → escribir (como ahora), `documents_written += 1`.
    - `action == "skip"`:
      - **si `physical_complete` y `rel_path != primary_rel`** (solapamiento
        cross-source real): escribir igualmente el fichero físico en
        `final_target`; `documents_overlap += 1`; emitir evento
        `cross_source_overlap` con `{expediente_id, doc_id, sha256,
        primary_path, written_path}`. (El alias ya lo registró `register`.)
      - **si no** (comportamiento actual): `documents_skipped_dedup += 1`,
        evento `dedup_skipped`.
      - Nota: si `rel_path == primary_rel` (re-pull mismo path) → no escribir
        (idempotente, el fichero ya está); no cuenta como overlap.
  - Incluir `documents_overlap` en el detalle del evento `pull_crm`.
- Mantener `_resolve_name_collision` antes de escribir (ya está): si existe con
  el mismo SHA → mismo target (sobrescritura segura); si distinto → sufijo `__N`.

### 1.2 `core/intake_log.py`

- Añadir `"cross_source_overlap"` a `INTAKE_EVENTS` (15 → 16). Comentario:
  "doc byte-idéntico a otro ya presente, escrito igualmente (physical_complete)".

### 1.3 `core/judicial_intake.py`

- `intake_demanda_contestacion(..., full: bool = False)`:
  - Clasificar SIEMPRE (tagging).
  - `if full`: `only_doc_ids = None`, `physical_complete = True` (baja todo,
    completo). Los roles ambiguos pasan a ser **informativos** (todo se baja
    igual); seguir emitiendo `pendiente_revision` como aviso, sin bloquear.
  - `else`: comportamiento actual (`only_doc_ids = {seleccionados}`,
    `physical_complete = False`).
  - `IntakeJudicialResult`: añadir `full: bool` y `documents_overlap`.
  - Evento `intake_judicial`: incluir `full` y `documents_overlap`.

### 1.4 `scripts/sync_sudespacho.py`

- Subcomando `intake-judicial`: añadir flag `--full/--no-full` (default
  `--no-full`). Pasar `full` a `intake_demanda_contestacion`. Mostrar en el
  resumen `documents_total_crm`, `documents_written`, `documents_overlap`.
- Para Paso 2: cuando `--run-pipeline` esté activo, llamar a `pipeline.run` con
  `do_anonimizar=True` (hoy llama con `do_demanda=True` y sin anon). Considerar
  flag `--anonimizar` y pasar `politica`/`tipo_proc`.

### 1.5 `streamlit_app.py`

- En el expander «⚖️ Intake judicial automático»: checkbox **"Descargar
  expediente completo (no solo demanda+contestación)"** → pasa `full=True`.
  Mostrar conteo total/escritos/solapamientos en el resultado.

## Paso 2 — OCR / markdown / anonimización (ENTREGADO 2026-06-10)

> **Estado: ENTREGADO.** Cableado del pipeline existente (sin lógica de negocio
> nueva). `intake-judicial --run-pipeline` ahora llama a
> `pipeline.run(case, do_sync=False, do_demanda=False, do_anonimizar=anonimizar,
> politica_anonimizar=politica, tipo_proc_anonimizar=tipo_proc)`. Nuevos flags
> CLI: `--anonimizar/--no-anonimizar` (default ON), `--politica` (default
> `SALTAR`), `--tipo-proc` (default `Juicio Ordinario`). El gate dispara también
> con `documents_overlap` (no solo `documents_written`). Streamlit: el checkbox
> «Encadenar pipeline» ahora ejecuta con `do_anonimizar=True, do_demanda=False`
> (antes llamaba `do_demanda=True` SIN anon — bug corregido). `inventory.scan`
> ya excluye `90_NOTAS_PERSONALES/` por construcción: solo recorre `00_Input/` y
> esa carpeta es hermana en la raíz del caso, nunca se escanea (sin cambio).
> Suite verde; gold fixture SaRS1 intacto (no se tocó el motor de anon).

Tras el pull completo, ejecutar el pipeline existente:

```python
pipeline.run(case_id, do_sync=False, do_demanda=False,
             do_anonimizar=True, politica_anonimizar="SALTAR",
             tipo_proc_anonimizar="Juicio Ordinario")
```

`extract_all` es incremental: solo hace OCR de los docs nuevos del CRM. El
anonimizado cae en `06_Anonimizado/` (caso entero). Exponerlo desde el CLI
(`--run-pipeline`/`--anonimizar`) y opcionalmente desde el botón de Streamlit.

**Excluir** `90_NOTAS_PERSONALES/` (regla CLAUDE.md) — confirmar que
`inventory.scan` ya lo salta; si no, añadir a su lista de skip.

## Aplazado — dedup por contenido en la extracción (NO construir aún)

Solo si el contador `documents_overlap` muestra solapamiento alto en casos
reales. Dónde: `extractor.extract_all`. Cómo: usar el `sha256` que ya trae
`_inventory.json`; mantener un mapa `sha → output canónico`; si un SHA ya se
extrajo, **reutilizar** el `.txt` en vez de re-OCR, y que `markdown_generator` /
anon no emitan el duplicado (o lo aliasen). Regla de canónico: preferir la copia
de `05_CRM` en fase procesal.

## Plan de tests

- `tests/test_pull_expediente_v2.py`:
  - `physical_complete=True` + manifest con un SHA preexistente de otra fuente +
    pull del mismo SHA en otra rama → fichero **escrito**, `documents_overlap==1`,
    evento `cross_source_overlap` emitido, alias registrado.
  - `physical_complete=False` (default) → mismo escenario → **skip**,
    `documents_skipped_dedup==1` (regresión del comportamiento actual).
- `tests/test_judicial_intake.py`:
  - `full=True` → `only_doc_ids` None (se piden todos), clasificación etiqueta
    demanda/contestación, `pendientes` informativos (no bloquean), todos escritos.
- `tests/test_intake_log.py`: `INTAKE_EVENTS` ahora 16, incluye
  `cross_source_overlap`.
- Regresión: el **gold fixture SaRS1** NO debería moverse (el cambio es en
  intake, no en el motor anon). Igualmente pasar el flujo regen+diff si se toca
  algo de anon (memoria `reference_gold_fixture_sars1.md`).

## Criterios de cierre

1. Pull completo del 444 → `05_CRM` contiene **los 97 docs físicos** en sus ramas.
2. El resumen reporta `documents_overlap` (medir en un caso con Drive E&V pulled).
3. `pipeline.run(..., do_anonimizar=True)` produce el anonimizado de los docs del
   CRM en `06_Anonimizado/`.
4. Suite verde; INTAKE_EVENTS test actualizado; gold fixture intacto.

## Gotchas del entorno (Windows + PowerShell)

- Ejecutar desde `C:\Users\tnm33\Dev\FeesDefender` con
  `.\.venv\Scripts\python.exe`. Para evitar el crash cp1252 con tildes/flechas:
  `$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"`.
- Tests: `python -m pytest -q --tb=short` (verja rápida ~40-50s;
  los `@pytest.mark.slow` se omiten salvo `--runslow`).
- Commits: automáticos (memoria `feedback_commits_auto`); el hook post-commit
  empuja a origin. Mensaje de commit vía `git commit -F <fichero>` (un here-string
  con `\` o rutas tipo `/download` puede disparar un guard).
- **RGPD**: nada de LLM en la nube con datos de caso, ni metadatos/nombres de
  fichero (memoria `feedback_no_llm_cloud_pii`).

## Relacionado (fuera del alcance de este plan)

`[SIGUIENTE-DEDUP-GUARD-ROBUSTO]` (en `PLAN.md`): guarda para **no duplicar
expedientes ni en el CRM ni en el Drive** al crear un caso (la búsqueda por
referencia es frágil a espacios/acentos; un doble espacio coló un duplicado del
exp. 444). Es un asunto distinto de este plan —aquí deduplicamos *documentos* en
el intake; allí se evitan *expedientes/carpetas* duplicados al crear el caso—
pero conviene tenerlo presente porque toca las mismas integraciones (CRM +
Drive).
