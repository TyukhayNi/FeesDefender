# Arquitectura — FeesDefender

## Capas

```
┌─────────────────────────────────────┐
│ UI: Streamlit / CLI Typer            │  ← solo orquesta llamadas al core
├─────────────────────────────────────┤
│ Core: pipeline + módulos            │  ← lógica de negocio
│   case_manager · sync · inventory    │
│   casos/case_locator                 │  ← resolución de rutas (flat ↔ ciudad)
│   casos/case_catalog                 │  ← qué existe en el canon y qué dice de ello
│   casos/workspace_model · _registry   │  ← modelo puro + copias locales de ESTA máquina
│   casos/workspace_resolver            │  ← SSOT de «sobre qué copia se trabaja» (§7)
│   casos/workspace_adopcion            │  ← puerta explícita del §15 (checkouts legacy)
│   ciudades                           │  ← catálogo cerrado + prefijo→ciudad
│   sync_sudespacho · sync_sudespacho_legacy
│   sudespacho_create · sudespacho_relations
│   intake_drive                       │  ← pull Drive E&V (rclone gdrive_ev)
│   intake_manual · intake_lotes       │  ← upload manual a lote 00_Input/<fecha>_manual_NN/ (MEJORAS #54)
│   intake_log · intake_manifest       │  ← refactor v2 (M10 + M9)
│   intake_control                     │  ← protocolo de 00_Input por UBICACIÓN (MEJORAS #149); config deriva de él
│   anon/ (api · separar · ocr · …)    │  ← absorbido de Expedientes Seguros
│   extractor · markdown_generator     │
│   scorer · viability · demanda       │
│   linker · llm · pipeline            │
├─────────────────────────────────────┤
│ Datos: CASOS_ROOT/<Ciudad>/{case_id}/│  ← fuente de verdad (.md)
│   _audit/relocations.jsonl           │  ← log forense de reasignaciones
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
| `core/config.py` — taxonomía de casos (`TIPOS_CASO_*`) **[FUENTE ÚNICA]** | `tests/test_gobernanza_taxonomia.py` (guard: fija el modelo canónico), `core/sudespacho_create.py` (constantes `TAG_VERDE_*`, `NOTA_*`, `tag_defaults_for_tipo_caso`), `core/scorer.py` (`KEYWORD_WEIGHTS`), `prompts/scoring.md`, y los **espejos documentales** que necesitan la taxonomía inline (corren en servidor, no importan `config`): `docs/INTEGRACION_SUDESPACHO.md` §8, `docs/CONVENCIONES_DESPACHO.md`, `.claude/skills/engel-volkers/SKILL.md`, `.claude/skills/preparacion-audiencia-previa/references/actora_defensiva.md`, `.claude/skills/triaje-viabilidad/references/criterios_triaje.md`. **`STATUS.md` y `README.md` NO transcriben — apuntan a `config.py`.** |
| `core/config.py` — `CASO_SUBDIRS` **[FUENTE ÚNICA]** | `tests/test_gobernanza_taxonomia.py` (guard), `tests/test_case_manager.py`. La estructura de carpetas del expediente **solo** se enumera aquí; `STATUS.md`/`README.md` apuntan a la constante, no la copian. |
| `core/config.py` — `ACTORES_DESPACHO` / `resolve_ui_default_actor` **[FUENTE ÚNICA]** | `tests/test_smoke_paso7.py` (guard de la tupla + los tres casos de `resolve_ui_default_actor`), `streamlit_app.py` (sidebar "¿Quién eres?": desplegable + default). `core/intake_log.get_actor()` es un mecanismo **paralelo, no consumidor** — no valida contra esta tupla (ver `DEAD_ENDS.md` §`FEESDEFENDER_ACTOR`). |
| `core/sudespacho_create.py` — campos CRM o endpoints | `docs/INTEGRACION_SUDESPACHO.md` (secciones afectadas) |
| `core/sudespacho_create.py` — constantes `NOTA_*` | `docs/INTEGRACION_SUDESPACHO.md` sección 10 (notas de expediente) |
| `core/sudespacho_create.py` — constantes `TAG_*` | `docs/INTEGRACION_SUDESPACHO.md` sección 8 (sistema de tags) |
| `core/case_manager.py` — `CaseMeta`, `ExpedienteLink` | `tests/test_case_manager.py`, `core/pipeline.py` si consume esos campos |
| `core/case_manager.py` — `_compose_informe_filename` / `_find_informe_existente` / `RUTA_OFFICE_MAX` **[FUENTE ÚNICA del nombre del informe]** | `core/migrar_nombres_informe.py` (importa el compositor: cambiar el nombre sin migrar deja dos informes por caso), `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py` + su `SKILL.md` (espejo del criterio para el informe **LLM**; corre en servidor, no importa `core`), `tests/test_compose_informe_filename.py`, `tests/test_smoke_paso7.py`. El presupuesto de 240 existe porque **Office se rinde en 260 aunque el FS admita más** (`docs/DEAD_ENDS.md`). |
| `core/crm_atlas.py` — `render_markdown` / `render_digest` | Los artefactos **generados y commiteados** `docs/CRM_SUDESPACHO_ATLAS.md` y `docs/crm_atlas/atlas.digest.md`. Lo canónico es regenerar (`python -m scripts.crm_atlas discover --phase all`, requiere `SUDESPACHO_API_KEY`); **sin corrida en vivo, alinear a mano solo las líneas de cabecera** con lo que ya emite el render (excepción escrita en la propia cabecera). Verja: `tests/test_crm_atlas.py::test_artefacto_atlas_coherente_con_su_fase_b`, que valida el artefacto, no el generador — es el único que caza esta deriva (D1/D2, 2026-07-26). |
| `scripts/repository_cli.py` — el puerto de inyección: campos del `Entorno` (las **ocho** fuentes de no-determinismo), `ENTORNO_REAL`, la firma de `run_rclone(cmd, *, entorno=)` y el parámetro `binario=` de los cinco constructores de comandos **[FUENTE ÚNICA del no-determinismo del frontal]** | `tests/_dobles/fake_drive.py` (`entorno_de_prueba` construye desde `cli.ENTORNO_REAL.con(...)`: un campo nuevo o renombrado lo deja sin fijar y el test se vuelve no determinista en silencio), `tests/_barrera.py` (sustituye los bindings `repository_cli.subprocess` y `.settings`, y **veta `importlib.reload`** del módulo porque restauraría los reales a mitad de suite), y los tres ficheros de orquestación `tests/test_repository_cli_{checkout,checkin,guard_pull}.py` + `…_fallos.py` + `…_defectos.py`, que inyectan por `entorno=`. Cambiar el puerto sin tocar el doble y la barrera **rompe el banco entero** (Fase 0 de la arquitectura dual, PRs #170/#174). Los helpers PUROS (`build_*_cmd`) conservan default a `_rclone_bin()` para no arrastrar los 27 tests que asertan su salida |
| `prompts/*.md` | Invalidar frontmatter `prompt_hash` en `.md` generados existentes (re-ejecutar pipeline sobre casos afectados) |
| `core/pipeline.py` — orden de pasos | `docs/ARQUITECTURA.md` sección "Flujo de un caso", `STATUS.md` sección Pipeline |
| `core/intake_drive.py` — campos `CaseMeta` | `core/case_manager.py` (`drive_ev_team_id`, `drive_ev_folder_id`), `tests/test_intake_drive.py` |
| `core/intake_drive.py` — `get_drive_file_info` / `download_drive_media` (Drive REST a nivel de fichero) | `core/email_export.py` (`_rescata_file`/`_resuelve_enlaces`, rescate de enlaces a Drive — Parte 2), `tests/test_intake_drive.py` |
| `core/intake_log.py` — `INTAKE_EVENTS` | callers que emiten eventos: `core/sync_sudespacho.pull_expediente_v2`, `streamlit_app.py` (expander "📂 Subir al árbol CRM" emite `upload_manual` con `details.destination 05_CRM/...`), `core/email_export.py` (emite `upload_email` y `upload_drive_link`) |
| `core/abrir_caso.py` — cerebro PURO de `abrir-caso` (`resolver_identidad`/`plan_intake`/`reconcile`/`crm_payload`/`descomponer_case_id`) | `scripts/abrir_caso.py` (orquestador CLI; `--case-id` usa `descomponer_case_id` + `case_locator.read_case_meta`), `tests/test_abrir_caso.py`. Depende de `core/config` (`posicion_de_tipo`) y `core/sudespacho_create` (DTO + `tag_defaults_for_tipo_caso`/`tag_rojo_equipo`/`tag_azul_de_codigo`, import perezoso; `crm_payload` enriquece tags equipo/ciudad desde el `codigo`) |
| `core/crm_ficha_validacion.py` — comprueba que los datos del `_ficha_crm.yaml` **están en la documental** del expediente (puro, sin IO). Tres veredictos: `ENCONTRADO` / `NO_ENCONTRADO` / `SIN_COMPROBAR`, más `NO_BUSCABLE` para un valor mal formado | `scripts/crm_ficha_validar.py` (lee `_cobertura.json` + los espejos `03_MD/`), `tests/test_crm_ficha_validacion.py` + `…_r1.py`. Depende de `core/crm_ficha` (`FichaCRMInput`). **Recorta el frontmatter del espejo antes de buscar**: `source_path` lleva el nombre del fichero original, y sin recortarlo el validador acredita datos por cómo se llama el PDF |
| `core/crm_ficha.py` — cerebro de la ficha CRM (`FichaCRMInput` + `cargar_ficha_yaml` de `00_Input/_ficha_crm.yaml`) | `scripts/crm_ficha.py` (orquestador `--case-id`: `link_ev_mmc` + `ensure_*` + `update_expediente`), `tests/test_crm_ficha.py`/`test_crm_ficha_cli.py`. Depende de `core/sudespacho_relations` (DTOs) y `core/sudespacho_create` (`get/update_expediente`) |
| `core/sudespacho_create.py` — `get_expediente`/`update_expediente` (GET `?properties=` + aplana lista `values`; PUT parcial preserva omitidos) | `docs/INTEGRACION_SUDESPACHO.md §10.7` (comportamiento CRM verificado en vivo), `scripts/crm_ficha.py`, `tests/test_sudespacho_create.py` |
| `core/intake_drive.py` — `CONTROL_FILES` (frozenset de ficheros de control a excluir del ledger) | `core/intake_drive._count_files` y `scripts/abrir_caso.py` (`hash_tree_local` los salta para no registrarlos como documentos) |
| `core/intake_manual.py` — `save_file_crm_branch` / `list_crm_branch_files` | `streamlit_app.py` (expander "📂 Subir al árbol CRM" en tab Casos), `core/config.py` (`CRM_TREE`, `CRM_SUBDIR`) si cambia el árbol |
| `core/intake_manifest.py` — schema o reglas reconcile | `core/sync_sudespacho.pull_expediente_v2`, futuros pulls v2 (intake_drive si se migra), `core/email_atomize/{dedup,attachments,inline,entregas}.py` (usan `compute_sha256_bytes`) |
| `core/ocurrencias_crm.py` — esquema de `00_Input/_ocurrencias_crm.json` (clave lógica `crm:<exp>:<doc_id>`, revisiones, estados `listada`/`materializada`/`superseded`) | **Escritor único:** `core/sync_sudespacho.pull_expediente_v2` (`registrar_listada` ANTES del filtro `only_doc_ids`; `registrar_materializada` en el bucle). **Lector previsto:** la vista procesal de `05_Procedimiento` (spec `2026-07-27-vista-procesal-*`, §2.1) — precedencia **CRM > ocurrencias > `_intake_hashes.json`**. NO amplía el manifiesto de intake: este resuelve `doc_id → ruta`, que el manifiesto (indexado por SHA) no puede cuando dos `doc_id` comparten contenido **y** ruta |
| `core/email_export.py` — `iter_nested_originals` / `message_id_of` / `parse_headers` / `split_eml` / `iter_body_text` / `_slug_descripcion` | `core/email_atomize/{extract,inline,bodies,attachments,render,entregas}.py` (motor de atomización a nivel de mensaje los reutiliza; no reimplementa el rebanado byte-fiel ni el slug; `entregas` reutiliza `_slug_descripcion`) |
| `core/email_atomize/` — formato de salida `01_Procesado/Emails/` (frontmatter `.md`, `corpus.jsonl`, `_registro.json` IDs congelados, `_revision/`); contrato de enumeración (`MEJORAS #98`): `eml_origen` = ruta relativa POSIX a la carpeta fuente (para un `.eml` de nivel superior, el nombre pelado); llave de `eml_procesados` en `_registro.json` = `<fuente>/<eml_origen>` (estado DERIVADO, no congelado como `mensajes`/`adjuntos`: se reconstruye desde cero cuando la corrida publica sin errores — gated igual que la poda de `mensajes/` — y solo se apila sobre lo existente cuando la foto es parcial); `AtomizeReport` declara `eml_enumerados`/`eml_leidos`/`publicado`/`poda_omitida` | `scripts/atomize_emails.py` (CLI), futura skill/UI; consumidores aguas abajo que citen `MSG-NNNNN`/`ATT-NNNNN` (deben permanecer estables); spec/plan en `docs/superpowers/{specs,plans}/2026-06-2{4,5}-email-atomize-*.md`, `docs/superpowers/specs/2026-07-28-email-atomize-enumeracion-recursiva-design.md` (`#98`). `scripts/sala_maquina.py::apply` (cableado 2026-07-28: lo llama antes del OCR y declara `status` en `atomizado_email`; spec/plan `docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-design.md`, `docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-adversarial-review.md`, `docs/superpowers/plans/2026-07-28-cableado-atomize-sala-maquina.md`) |
| `core/email_atomize/{identidades,vistas,entregas}.py` — capa de caso F3: esquema de `<caso>/identidades.yaml` + `<caso>/vistas.yaml` (input curado a mano), nuevas salidas `01_Procesado/Emails/{vistas/,_entregas/}`, `SET_ENTREGABLE`/formato `_SELLO.md` | `core/email_atomize/{inline,render,pipeline}.py` (consumen `Identidades` por **inyección**; `pipeline` genera `vistas/` y orquesta `sellar_entrega`), `scripts/atomize_emails.py` (CLI `--entrega`); sin YAML = comportamiento genérico; futura Cronología Unificada (D5 formaliza `identidades.yaml`); spec/plan `docs/superpowers/{specs,plans}/2026-06-25-email-atomize-fase3-capa-caso*.md` |
| **Gramática del W-code en el nombre de carpeta de caso** — `\((W-[A-Z0-9]+)\)`, anclada en los paréntesis para no confundir un segmento de dirección con pinta numérica (`(08860)`) con la referencia | **DUPLICADA A PROPÓSITO en dos sitios: `core/abrir_caso._W_CODE_EN_NOMBRE` y `core/email_atomize/contaminacion.w_code_de_carpeta`.** La duplicación evita que el motor de atomización importe el orquestador de alta (invertiría la dependencia), al precio de que **si la gramática del W-code cambia hay que tocar los DOS**. `contaminacion` usa además una segunda regex, distinta y deliberadamente más permisiva (`W-[A-Z0-9]{4,}` sin paréntesis, case-insensitive), para cazar W-codes AJENOS en asuntos y nombres de adjunto: ahí el falso negativo es el caro |
| `core/email_atomize/contaminacion.py` — detector de contaminación cruzada (capa PURA: `detectar_cruce`/`resumir`/`w_code_de_carpeta`); AVISA vía `AtomizeReport.notas`, nunca excluye | `core/email_atomize/pipeline.py` (gancho al final de `atomize_dir`, tras cerrar Capa B, con el W-code derivado de `case_dir.name`); consumidores que lean `notas` (CLI `scripts/atomize_emails.py` las surfacea a stderr; `scripts/sala_maquina.py::_atomizar_correo` las surfacea a stderr antes del OCR). Cierra el sub-ítem 3 de `PLAN.md [SIGUIENTE-INTAKE-EMAIL-FILTRO]` |
| `core/split_documental._slug_seg` — **contrato de NOMBRES del segmento de bundle**: `{parent_slug}__{doc_id}_{TIPO}`, con el `doc_id` como identidad **persistente** que vive en el manifiesto (`_segmentacion.json`: `doc_id`, `next_doc_id`, `retirados`). El sha del segmento sigue en la cobertura como custodia, **ya no en el nombre** | **Dos espejos que quedaron falsos la primera vez que cambió, y por eso esta fila existe** (hallazgo H-13 de la revisión r1, 2026-08-02): `.claude/skills/organizar-sala-maquina/SKILL.md` (bloque de layout que un agente de Cowork lee para saber qué encontrará en disco) y `docs/superpowers/specs/2026-07-14-split-sala-maquina-design.md` (contrato viejo `{bundle_sha8}__seg{NN}_{TIPO}__{seg_sha8}`, marcado como superado). Consumidores que lo tratan como **opaco** y no hay que tocar: `preclasificar.py` (concatena `f"{fila['slug']}.md"` desde la cobertura) y `scripts/detectar_ocr_ciego.py` (`md.stem`). Contrato vigente: `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md` rev. 4 |
| `core/pdf_paginas.py` — **SSOT del discriminante de «página ciega»** (`MIN_PX_RASTER` / `MAX_CHARS_SELLO` / `paginas_ciegas`): un escaneo a página completa bajo una capa de texto de sello | Tres consumidores que deben compartirlo o el diagnóstico deja de describir al motor: `core/anon/ocr.ocr_pdf_escalera` (peldaño 2, qué páginas aislar), `core/sala_maquina` (`_paginas_ciegas` para el enrutado y `calidad_por_pagina` para la calidad) y `scripts/detectar_ocr_ciego` (cribado read-only). Cambiar un umbral aquí mueve a la vez la worklist de `_cobertura.md` y lo que se re-OCR-iza — ver `MEJORAS #90` |
| `core/case_manager.py` — `crm_branch_path` o reglas derivación | `data/_plantillas/ficha_operacion.yaml` (regla_derivacion canónica), `data/_plantillas/cuestionario_viabilidad.yaml` (campo `respalda`), eventual `core/viabilidad.py` (horizonte 3) |
| `core/config.py` — `CRM_TREE` o `CARPETA_ID_TO_PATH` | `docs/INTEGRACION_SUDESPACHO.md` §13.5 (mappings), `docs/INTEGRACION_SUDESPACHO.md` §13.6 (estructura árbol) |
| `core/anon/mapa_caso.py` — `SUBDIR_ANONIMIZADO` / `MAPA_FILENAME` | `core/anon/deanonimizar.py` (`_SUBDIR_ANONIMIZADO` / `_MAPA_CASO_FILENAME` replicados para evitar acoplar el deanonimizador al resto del core; mantenerlos sincronizados) |
| `core/anon/api.py` — campos del frontmatter del .md anonimizado | `core/anon/deanonimizar.py::_mapa_desde_frontmatter` (lee `mapa_caso_path` / `mapa_entidades` como fallback); añadir el nuevo nombre si se renombra |
| `core/ciudades.py` — catálogo `CIUDADES` o función `ciudad_de_equipo` | `core/casos/case_locator.py` (`_CITY_NAMES` ya lo lee dinámicamente, pero los tests fijan ciudades concretas), `streamlit_app.py` selector ciudad (validación blanda prefijo↔ciudad + expander Reasignar) |
| `core/casos/case_locator.py` — API de resolución de rutas | Toda llamada que componía `settings.casos_root / case_id` (auditar con grep) — `core/case_manager.list_cases`, `core/config.caso_path`, `scripts/{audit_referencias_casos,scheduled_sync,sync_sudespacho}.py`. **Desde la Fase 1 dual, la puerta no es la resolución sino la AUTORIZACIÓN:** `scripts/sala_maquina.py` ya no resuelve por `caso_path` sino por `CaseWorkspaceResolver` (`_resolver_workspace`), y conserva el binding del módulo solo cuando el catálogo **no** conoce el caso (`legacy_unresolved`). El inventario AST de llamadores vive en `scripts/clasificacion_localizador.py`; el censo de `strict=False` lo fija `tests/test_guard_localizador.py` |
| `core/casos/workspace_resolver.py` — la matriz del §7 | Todo entrypoint que escriba en un expediente. Cambiar la matriz obliga a `tests/test_workspace_resolver.py` (18 mutantes, uno por frontera) **y** a `tests/_matriz_contractual.py`, que es donde las nueve filas del §14.1 viven como datos para todos los consumidores |
| `core/intake_log.py` — `append_event` / `read_events_de` | Reciben el `case_dir` **ya resuelto**: el rastro cae junto a los bytes (B0-1). Ya **no** dependen de `config.caso_path`, y ese acoplamiento era el que fabricaba expedientes fantasma. Migrados 7 de 14 llamadores (contado por AST); el resto queda `legacy_unresolved` y no es peligroso porque `caso_path` es estricto desde el Task 6 |
| `core/case_manager.py` — validación del **sumidero del alta** en `ensure_case` (`MEJORAS #153`/`#154`) | `core/utils.py` (`exigir_componente_de_ruta` / `exigir_sin_caracteres_de_ruta`, la gramática), `core/casos/case_locator.py` (**`_CITY_NAMES`**: cambiar el catálogo de ciudades cambia qué altas se aceptan), `core/abrir_caso.py` (`componer_case_id` valida los tres campos antes de concatenar), `tests/test_ensure_case_sumidero.py` + `tests/test_ensure_case_sumidero_r2.py`. **Alcance declarado:** es el sumidero del **alta nominal**, no del árbol de casos — las otras puertas están enumeradas en `MEJORAS #155`–`#158`, y `_contenido_en` existe en vez de `case_mutex._bajo` por `#159`. Diseño **rev. 3**: `docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-design.md`. |
| `core/sala_lectura.py` — **`_MD_SUBDIR` [FUENTE ÚNICA de la ruta de espejos MD]** | **`core/sala_maquina.py`** (`_sala_maquina_dir` + `03_MD`): la constante es el **contrato con quien escribe los MD**, no un detalle interno de la sala de lectura. Componerla por separado en dos sitios ya divergió una vez y dejó **140 enlaces muertos** (`MEJORAS #151`). La fija por comportamiento —no por grep— `tests/test_sala_lectura_espejos_md_resuelven.py`, cuyo fixture usa el literal **a propósito**: anclarlo a la constante deja pasar el mutante. |
| `core/sala_lectura.py` — clasificador/copiador/render (sala de lectura F4–F6) | `core/catalogo_documental.py` (`CatalogEntry` + campos F6/F4), `core/conjunto_detector.py` (bundles CRM), `core/local_organizer.py` (helpers `_sanitize`/`_exif_o_mtime`), `scripts/sala_lectura.py` (CLI), `streamlit_app.py` (botón «📚 Sala de lectura»); taxonomía `TAXONOMIA_EV` en `core/config.py`. **[DEPRECADO 2026-06-18]** el camino de sala del motor queda superado por la skill `organizar-sala-lectura` v1.3 (sala ÚNICA plana sobre todo `00_Input`); el paso `catalogo.build` se quitó del pipeline. Diseño: `docs/superpowers/specs/2026-06-18-sala-lectura-unica-design.md`. ⚠️ **Pivote pendiente** (rendimiento): la skill por el conector de Drive (Cowork) tardó ~53 min — el camino rápido es local sobre `G:` (Drive for Desktop); ver `DEAD_ENDS.md` y `PLAN.md` `[SIGUIENTE-SALA-UNICA-PLANA]`. |
| Catálogo `CIUDADES` cambia (nueva oficina) | Tests `tests/test_case_locator.py` actualizan expectativas; revisar si los expedientes en `_Sin clasificar/` corresponden a la ciudad nueva y reasignar manualmente con `scripts/migrate_to_city_structure.py` o UI «Reasignar ciudad» |
| `data/_plantillas/*.yaml` | regenerar XLSX con `python -m scripts.render_plantillas all` y commitear ambos (YAML + XLSX) |
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

### Jerarquía CASOS_ROOT por ciudades

Desde 2026-05-21 (sesión 25) la raíz está subdividida en carpetas-ciudad: `CASOS_ROOT/<Ciudad>/<case_id>/`. Catálogo cerrado en `core/ciudades.CIUDADES` (Barcelona, Bilbao, Madrid, San Sebastián, Santander, Sevilla, Valencia) + fallback `_Sin clasificar`. Las carpetas con prefijo `_` (`_PLANTILLA`, `_audit`, `_Sin clasificar`) son de sistema — la regla la encapsula `core/ciudades.es_carpeta_de_sistema`.

**`core/casos/case_locator` es la única puerta de entrada para resolver rutas de expedientes.** Nadie en el core compone `settings.casos_root / case_id` directamente; todos pasan por:

- **Las tres intenciones (Fase 1, Task 6).** `path_for` servía a tres preguntas distintas con una sola respuesta, y por eso no había booleano que lo arreglara: `strict=True` rompía el alta de un caso nuevo y `strict=False` conservaba el expediente fantasma. Separadas por nombre —que es lo que las hace auditables con un `grep`, cosa que un flag no permite—:
  - `localizar(case_id)` — el caso **debe** existir; lanza `LocalWorkspaceMissing` si no. No crea nada, ni al fallar.
  - `buscar(case_id)` — «¿está?»; devuelve `None`. Existe por los detectores de ausencia, que con `localizar` habrían cambiado un error legible por una traza.
  - `destino_de_alta(case_id)` — la **única** puerta de creación. Nombrar no es crear: devuelve la ruta y no toca el disco.
- `path_for(case_id, *, strict=True)` — la puerta vieja, hoy **estricta por defecto**. `strict=False` es una escotilla legacy declarada cuyo censo en producción está a **cero** y lo vigila `tests/test_guard_localizador.py`; se retira en la Fase 4.
- `path_for_ciudad(case_id, ciudad)` — calcula la ruta esperada sin chequear existencia (uso interno y migración).
- `move_to_city(case_id, ciudad, motivo, usuario)` — atómico: mover carpeta + actualizar campo `ciudad` en `00_Input/_caso.md` + escribir línea en `_audit/relocations.jsonl`. Rollback automático si falla la actualización del metadato.
- `list_cases(ciudad=None)` — itera todos los expedientes (o los de una ciudad concreta) deduplicando entre raíz plana (legacy) y ciudades.
- `append_audit_log(entry)` — JSONL append-only en `CASOS_ROOT/_audit/relocations.jsonl` con timestamp UTC auto.

El campo `ciudad` se persiste tanto en `meta.ciudad` como en la raíz del frontmatter de `_caso.md`. La detección automática prefijo→ciudad se hace con `core/ciudades.ciudad_de_equipo(codigo)`.

**Segundo nivel `<Ciudad>/<Equipo>/<case_id>` preparado pero no activado.** `case_locator` tolera el catálogo actual; si en el futuro se decide subdividir además por equipo, el refactor de call-sites ya no será necesario — solo cambiar la composición en `path_for_ciudad`.

Histórico operativo: la migración inicial del 2026-05-21 movió 9 expedientes a 5 ciudades (Barcelona, Madrid, Santander, Sevilla, Valencia). Plan completo en `docs/superpowers/plans/PLAN_SUBDIVISION_CIUDADES.md`. Snapshot pre-migración persistido en `_audit/snapshot_pre_migration_20260521_013728.json`.

### El expediente activo puede no estar en `CASOS_ROOT` (arquitectura dual, Fase 1)

`case_locator` contesta **dónde está el expediente en el canon**. No contesta **sobre qué
copia se trabaja**, y confundir las dos preguntas es el defecto que la arquitectura dual
cierra: mientras un caso está prestado a otra máquina, la copia canónica **no** es la
operativa, y un motor que resuelva por ruta escribe encima del trabajo de otro.

Cuatro piezas, cada una con una sola pregunta (spec `2026-07-29-feesdefender-dual-case-workspace-design.md`):

| Pieza | Contesta |
|---|---|
| `casos/case_catalog.CaseCatalog` | qué existe en el canon y qué dice el canon de ello (`localizar`, `estado_compartido`, `bajo_catalogo`, `es_proyeccion_local`) |
| `casos/workspace_registry.WorkspaceRegistry` | qué copias locales conoce **esta** máquina. Un fichero `<w_code>.json` por caso, con una lista dentro; fuera del repo y de `CASOS_ROOT`; **falla cerrado** (`RegistryUnreadable`, nunca `[]`) |
| `casos/workspace_model` | el vocabulario: `CaseRef`, los cinco modos, la matriz de capacidades del §5.4 y los quince errores del §10 |
| `casos/workspace_resolver.CaseWorkspaceResolver` | **la copia operativa y qué está permitido en ella** — la matriz del §7 en una sola pieza. **SSOT de esta decisión** |

Más `casos/workspace_adopcion`, la puerta explícita del §15: un checkout anterior al
registro no se adopta solo, y `verificar_adopcion` **declara lo que no pudo comprobar**
(el nonce vive solo en el Drive, porque `_caso.md` está en `MERGE_EXCLUSIONS`).

**Dependencia retirada: `core/intake_log` ya no pasa por `config.caso_path`.** `append_event`
recibe el `case_dir` **resuelto** y escribe junto a los bytes (`read_events_de` lee lo
mismo). Antes hacía `mkdir(parents=True)` sobre la ruta que devolvía `caso_path`, que es
la fábrica de expedientes fantasma del bug de W-02ZIIF — y la suite llevaba tiempo verde
**protegiéndolo**, con un test que exigía que auditar creara `00_Input`.

**Contrato reutilizable.** La matriz mínima por entrypoint del §14.1 vive **una vez** como
datos en `tests/_matriz_contractual.py` (nueve escenarios, cuatro planos de efecto), y la
consume cada entrypoint migrado. Hoy `scripts/sala_maquina`; en la Fase 3, la vertical de
correo.

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
