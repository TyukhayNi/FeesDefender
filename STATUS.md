# STATUS — FeesDefender

> **Fuente de verdad única del proyecto.**
> Actualizar al cerrar cada sesión con `python -m scripts.session_close`.

**Última actualización:** 2026-06-15 (sesión 45, consulta — proyecto sala de lectura) — **Sesión de consulta, sin cambios de código ni tests.** El usuario preguntó qué proyecto consiste en montar la "sala de lectura para el abogado". Respondido: es la **Sala de lectura de `01_Procesado`** (HANDOFF Cowork 2026-06-12, plan fino en `docs/PLAN_SALA_LECTURA_01_PROCESADO.md`, entrada `[SIGUIENTE-SALA-LECTURA-01]` en `PLAN.md`). Recordado el acoplamiento estratégico clave: **construirla obliga a construir antes el catálogo `indice_documental.yaml`** (`[SIGUIENTE-CATALOGO-DOCUMENTAL]`, el cimiento), y las 5 decisiones abiertas de §G del plan. **Suite intacta: verde (935 passed / 58 skipped).** **[SIGUIENTE]** sin cambios.

**Anterior (2026-06-15, sesión 44, investigación API CRM — relación correo↔expediente):** **Sesión de investigación pura, sin cambios de código.** Objetivo: identificar qué endpoint del CRM relaciona correos y sus adjuntos con un expediente, a partir de capturas del explorador de API (otro hilo lo prueba contra el CRM real). **Descartados como auxiliares** los seis endpoints del primer listado (`AccountLinks`, `DownloadAttachment` —solo bajada de bytes—, `MailPermissions`, `MailRecipients`, `Mail` GET, "Fix emails permissions from legacy"): ninguno vincula. **Candidato fuerte: el recurso `MailRoundcube`** (CRUD completo POST/GET/PUT/DEL/PATCH en el swagger estilo API-Platform de `api-crm-commons-pro`), que encaja con el contrato ya documentado en §7 de `docs/PLAN_INTAKE_PROCURADORES_EMAIL.md` (vinculación vía `PUT`/`PATCH` del recurso de correo con `mailRelations: [{element, elementId, mail}]` + `attachmentGdocu: [{identifier}]`). **Pendiente de confirmar** (en el otro hilo): inspeccionar el *body schema* del `PUT`/`PATCH` de `MailRoundcube` para verificar que expone `mailRelations`/`element`+`elementId` y `attachmentGdocu`, y fijar la ruta exacta (p. ej. `/api/mail_roundcubes/{id}`) + el host (`api-crm-commons` vs `nest-mail-commons`) → decide el flujo de auth (x-api-key vs JWT, §7 línea 167). Alimenta directamente **F3** (escritura en el CRM). Nota de la pista añadida a §7 del plan de intake. **Suite intacta: 935 passed, 58 skipped** (no se tocó código; exit 0 en tres corridas). **Captura en vivo complementaria (Chrome MCP, esta sesión):** confirmado que **`nest-mail-commons-pro` rechaza la `x-api-key` de api-crm (HTTP 500); usa el JWT de sesión** (responde la pregunta abierta de §7 línea 167) — el módulo de correo es **Roundcube en iframe cross-origin** y el write del relate/adjuntar **no se capta desde el frame superior, no es AppSync (0 frames WS) ni el `PUT /api/mail/{id}` REST de nest-mail**; en cambio **la búsqueda de expediente y el listado de carpetas SÍ son api-crm REST** (x-api-key, ya en F2). Refuerza que **`MailRoundcube` (api-crm) es el camino a confirmar**. Detalle en `DEAD_ENDS.md` (sección "Módulo de correo nest-mail/Roundcube"). **Próximo paso concreto F3a:** exportar un **HAR de DevTools** (`docs/captura/relate_email_F3.har`, "Save all as HAR with content") de un relate+adjuntar manual → fija ruta/host/body-schema reales del write (iframe incluido) → decidir camino: (A) replicar REST (MailRoundcube/x-api-key, ideal) / (B) `PUT /api/mail/{id}` nest-mail JWT+refresh / (C) robot prepara + humano relaciona 1 clic. ⚠️ **Limpiar en el CRM** los relates de prueba de la captura (PRUEBA BORRAR en SeRR1/Num 13, PRUEBA 2 BORRAR en MaRS9 + adjuntos). Operativa lateral: cambios ajenos de sesiones concurrentes (scripts `preparacion-audiencia-previa`, plantillas viabilidad, `docs/CONVENCIONES_DESPACHO.md`, `docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md`, drafts de skills) **dejados intactos** (commit acotado a STATUS.md + plan de intake). **[SIGUIENTE]:** **F3 — escritura en el CRM**: confirmar el body schema de `MailRoundcube` PUT/PATCH, resolver el auth, y hacer relate correo↔expediente + adjuntar al gestor documental en un expediente de prueba (mismo requisito duro de traza §18.9). Luego F4 (renombrado adjuntos+OCR+aprendizaje), F5 (grabaciones), F6 (check-2).

**Anterior (2026-06-12, sesión 43, intake procuradores F2 — UI Streamlit + CLI + consolidación REST):** **F2 cerrada de punta a punta y fusionada a `main`.** Vía brainstorming→spec→plan→subagent-driven (spec+calidad por tarea; specs/plan en `docs/superpowers/`). **UI** «Bandeja de correos» (5ª pestaña de `streamlit_app.py`): login por persona `set_actor` + cabecera de triaje con recuentos + 3 tarjetas 🟢/🟡/🔴 con checks verdes por dato coincidente + combobox de reasignación (REST) + acciones→`transicionar`/`record_decision`/`upsert_queue_item` + vista Descartados con Recuperar; orquesta el core, **dry-run** (no escribe en el CRM). **CLI** thin `scripts/intake_procuradores.py` sobre `fetch_and_run` (recuentos por estado/confianza/motivo; scheduling delegado al SO/`schedule`). **Core:** `RobotProposal` ensanchado para que la tarjeta se renderice sin llamar al CRM — persiste `signals`/`datos_expediente`/`coincidencias` en la cola, computados por `from_intake_proposal` (la comparación reusa `_check_signal_matches`, que ya existía); nuevos `fetch_expediente_datos` (lectura por id, REST) + `recompute_coincidencias` (checks al reasignar) en `core/procurador_search.py`. **Bug crítico cazado en review (corregido):** la reasignación del combobox se perdía entre reruns de Streamlit (en 🟡 se descartaba silenciosamente la corrección; en 🔴 el Confirmar quedaba deshabilitado para siempre) → persistido en `st.session_state` por `email_id` (`3b24f45`). **Consolidación:** otra sesión había migrado `search_expedientes` a REST (el autocomplete legacy devuelve body vacío contra el CRM real; sus tests pasaban solo por mock) en `feat/search-expedientes-rest`; **fusionada por fast-forward sin reimplementar** (búsqueda por `referencia_cliente`+`referencia_procurador`+nº/serie, sin `clientes`; contrario/autos fuera de alcance, `MEJORAS_FUTURAS.md` §31). Commits propios `9490eca`(T1)/`945030b`+`1300719`(T3)/`15df2f2`(T4)/`1f336dc`+`c3bc790`(T5 CLI)/`cbfafba`+`3b24f45`(T6 UI)/`f6c88ea`(planificación); fusionados además REST (7 commits), intake-judicial `6049fa9` y aislamiento `5b4038e`. **Merge `feat/intake-procuradores-f2-ui`→`main` (FF), rama borrada.** **Suite: 935 passed, 58 skipped.** **[SIGUIENTE]:** **F3 — escritura en el CRM** (relate correo↔expediente + adjuntar al gestor documental; resolver auth nest-mail `x-api-key` vs JWT; mismo requisito duro de traza §18.9 que F2). Luego F4 (renombrado adjuntos+OCR+aprendizaje), F5 (grabaciones), F6 (check-2). **⚠️ Gotcha de concurrencia:** esta sesión compartió working tree y rama checked-out con otra sesión activa → sus commits caían en mi rama; gestionado con merge-base/FF y commits acotados. Operativa lateral: cambios sin commitear ajenos (viabilidad `data/_plantillas/*`, `docs/CONVENCIONES_DESPACHO.md`, `docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md`, skills drafts) **dejados intactos** (commit de cierre acotado a STATUS.md).

**Anterior (2026-06-12, sesión 42, planificación — sala de lectura `01_Procesado`):** **Revisado el HANDOFF de Cowork para la sala de lectura y registrado el plan de ejecución.** Plan fino autocontenido en `docs/PLAN_SALA_LECTURA_01_PROCESADO.md` (handoff aprobado verbatim + §0 con lectura del repo) y entrada `[SIGUIENTE-SALA-LECTURA-01]` en la cola de `PLAN.md`. **Tres acoplamientos detectados contra el código real:** (1) la sala de lectura **es** `[SIGUIENTE-CATALOGO-DOCUMENTAL]` — `INDICE.md`/`CRONOLOGIA.md` se renderizan desde `indice_documental.yaml`, que no existe; construir la sala obliga a construir el catálogo (cimiento), al que falta añadir `parent_id`/`orden_en_bundle`. (2) `_manifiesto.jsonl` del handoff solapa con `00_Input/_intake_hashes.json` (`IntakeManifest`) ya existente → inclinación: catálogo único, no un tercer artefacto. (3) el clasificador Scaleway (Tarea 7) lee documento en claro → misma excepción RGPD acotada que el intake de procuradores; el DPA con Scaleway bloquea solo la Tarea 7, no el cimiento. **Aterrizaje:** el «grifo de MD en claro» (Tarea 2) no es código nuevo, es re-enrutar `markdown_generator.build` a `01_Procesado/MD/`; el `conjunto_detector` ya existe y se reaprovecha como proveedor de propuestas de bundle. Sin cambios de código; suite verde (914 passed / 58 skipped). **[SIGUIENTE]** cerrar con Nikolai: ¿catálogo único vs manifiesto aparte? y ¿promover `[SIGUIENTE-CATALOGO-DOCUMENTAL]` de backlog a cola? Luego Fase 0 (doble `extract_all`) → Fase 1 (catálogo `indice_documental.yaml`).

**Anterior (2026-06-12, sesión 41, intake judicial — guard W-code + auto-resolución de expediente):** **Arreglado el botón «Traer expediente» del intake judicial, que bajaba a ciegas lo que se tecleara.** Incidencia real: con el placeholder `"649"` (un ID *real* = Roser 39, W-030LFT) el usuario bajó 31 documentos de otra finca al caso Torrent de les Flors (W-02MA0R); limpiados los docs + desregistrado el `id:649` de `_caso.md`. **Fix (UI + core, TDD):** (1) **guard** previo a descargar — `verify_expediente_referencia` + nuevo `wcode_match` bloquean si el ID no comparte W-code con el caso (con casilla de override para excepciones); validado en real: #649→BLOQUEA, #487→PASA con nota de divergencia de nombre. (2) **auto-resolución** — botón «🔎 Buscar expediente en el CRM» lista candidatos por W-code (`list_expedientes_judiciales_candidatos`) para confirmar y rellenar el ID, en vez de teclearlo. (3) placeholder peligroso `"649"`→`"p. ej. 487"`. **Hallazgo de fondo:** el autocomplete legacy devuelve vacío contra el CRM real → `find_expediente*_by_referencia` migradas a REST `element_registries` (filtro `like` sobre el W-code, `+_rest_search_expedientes`); anotado en DEAD_ENDS. Suite 914 verdes. **[SIGUIENTE]** decidir nombre canónico del caso Torrent (local «Bad debt» vs CRM #487 «Vuelta - COMPRADOR»).

**Anterior (2026-06-12, sesión 40, intake procuradores F2 — backend + adaptador Gmail):** **Todo el backend de F2 (bandeja de revisión) construido con TDD, dry-run, y el adaptador Gmail verificado en real.** 5 piezas, en orden: **F2.1** `core/procurador_review.py` — terna §18.9 (`RobotProposal`/`HumanAction`/`ReviewDecision`) + `compute_divergence` (corazón del check-2: detecta si el humano cambió expediente/carpeta/nombre o descartó un match) + log de auditoría JSONL append-only (`record_decision`/`read_decisions`, flush+fsync, reusa `get_actor` de `intake_log`) + puente F1→F2 `from_intake_proposal`. **F2.2** máquina de estados de cola (pendiente/confirmado/descartado; `transicionar` puro con `replace`; confirmado terminal; descartado solo sale por `recuperar` → reabre triaje §6; `MOTIVOS_DESCARTE`). **F2.3a** store de cola (`upsert_queue_item`/`load_queue`, JSONL append-only con fold a último por `email_id`, anti-duplicado §4, filtro por estado, reconstruye `ReviewItem` anidado). **Runner** `core/procurador_runner.py` — `process_email` (correo→ReviewItem; enrutado §6: remitente no-procurador / es_ruido sin Su ref / sin señal alguna → descartado recuperable, sin hard-drop; resto incl. sin-match con señales 🔴 → pendiente; `es_ruido` advisory) + `run_intake` (lote, dedup contra cola y dentro del lote = mismo Message-ID en 4 buzones); extractor/matcher inyectables (testeable sin red). **Adaptador Gmail** `core/gmail_source.py` — `gmail_message_to_email` (parser MIME recursivo, base64url, **Message-ID como `email_id`** estable entre buzones §4), `fetch_emails` (read-only, `service` inyectable, reutiliza tokens OAuth de `~/.gmail-mcp/tokens/<cuenta>.json` formato google-auth, refresca y reescribe), `fetch_and_run` (multi-buzón → `run_intake` único). **Verificado LIVE read-only** contra `procesal@tyukhay.legal`: 5 correos reales parseados (Message-ID + cuerpo + fecha OK; 2 procuradores reconocidos) — auth+refresh+API+parseo confirmados de punta a punta. Commits `a80afeb` (F2.1) → `00ee3b8` (F2.2) → `7b03759` (F2.3a) → `3bedb22` (runner) → `95082f1` (adaptador). Stores nuevos **gitignored** (`data/_aprendizaje/intake_audit.jsonl` = terna; `intake_cola.jsonl` = cola; PII). Deps nuevas en `requirements.txt`: `google-api-python-client` + `google-auth` (quien monte el entorno: `pip install -r requirements.txt`). **+37 tests TDD** (`test_procurador_review.py` 22, `test_procurador_runner.py` 8, `test_gmail_source.py` 7). **Suite: 899 passed, 58 skipped** (orden determinista `-p no:randomly`). **[SIGUIENTE]:** única pieza pendiente de F2 = **UI Streamlit** (pestaña "Bandeja de correos": cabecera de triaje + 3 tarjetas 🟢/🟡/🔴 + login por persona vía `set_actor` + acciones → `transicionar`+`record_decision`+`upsert_queue_item` + vista Descartados con "Recuperar"; orquesta el core, dry-run). Luego F3 (escritura CRM, auth nest-mail), F4 (renombrado adjuntos+OCR), F5 (grabaciones), F6 (check-2). Falta también un CLI/scheduler thin que llame a `fetch_and_run` periódicamente (§3). **⚠️ Gotcha:** correr la suite completa **muta el working tree** — `test_sync_es_idempotente` (`tests/test_skill_helpers_sync.py`) llama a `sync.sync()` y reescribe `.claude/skills/*/scripts/*.py`; aparecen como `M` tras los tests sin que nadie los tocara (flake de aislamiento bajo `pytest-randomly`; chip de tarea abierto para arreglarlo). Operativa lateral: cambios concurrentes de viabilidad (`data/_plantillas/*`, `_skills_drafts/`, `docs/CONVENCIONES_DESPACHO.md`, `docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md`, etc.) **dejados intactos** (commit acotado a STATUS.md + PLAN.md).

**Anterior (2026-06-12, sesión 39, intake procuradores F1 — medición y cierre):** **F1 Matcher MEDIDO sobre correos reales y COMMITEADO.** Sobre el F1 de la sesión previa (`core/llm_cloud.py` conector LLM cloud Scaleway+Mistral Small 3.2; `core/procurador_intake.py` extractor de señales + matcher por `num_expediente`/`serie_expediente` + propuesta de nombres de adjuntos), esta sesión midió la tasa de acierto contra **2 lotes reales de `procesal@tyukhay.legal` (20 correos / 7 procuradores)** y arregló los fallos detectados. **Resultado final: 100% su_ref extraída y 100% match ALTA** en ambos lotes. Commits `f904d72` (F1 base) → `6a811ef` (sufijo subserie + es_ruido advisory) → `0309c0a` (sufijo robusto a formato CRM inconsistente) → `de7b176` (plan: diseño check-2 + entrada PLAN) → `30a1a4e` (plan: vista Descartados). Credencial: `LLM_CLOUD_API_KEY` (var de entorno de usuario Windows, proyecto Scaleway "FeesDefender - Intake - Procesal"). **Hallazgos y arreglos:** (1) **sufijo de subserie** (`-N`/`-P`/`-E`): el CRM lo guarda DENTRO de `serie_expediente` y de forma INCONSISTENTE (`"2023-n"`, `"2021-p"`, pero también `"2022 - n"` con espacios); los procuradores lo escriben `-N`/` N`/` - N`. `serie_expediente` pasó de `int` a `str`; `_parse_su_ref` canoniza a `aaaa-x`; `_search_by_num_serie` filtra por `num_expediente` en servidor (la API `element_registries` **solo soporta `equal`/`not-equal`, NO `contains`** — ver DEAD_ENDS) y casa la serie en cliente con `_norm_serie` (minúscula, sin espacios). (2) **`es_ruido` era bloqueante** → un falso positivo descartaba una actuación real; ahora es **advisory** (no corta la búsqueda si hay Su ref resoluble; señal `es_ruido_advisory`) + prompt afinado. (3) Recordatorios y respuestas de hilo se relacionan a su expediente (plan §2); renombrado de adjuntos validado en smoke (`Auto`/`DiOr`/`Decr` + probatorio `D NN`). **Decisión de diseño para F2** (plan §6/§16.11): el filtro/ruido NO hace hard-drop → **vista "Descartados"** que revisa la secretaria, con "Recuperar → bandeja" (descarte reversible y auditable). **Diseño "check-2" (control de calidad del archivo) incorporado a la planificación** (`de7b176`): `docs/PLAN_INTAKE_PROCURADORES_EMAIL.md` §18 nueva (control por excepción en 3 capas: Ana 100% → auto-chequeo determinista —invariante de Su ref, cobertura, carpeta por defecto, adjuntos— → cola de Paola + muestra ~10% → resumen semanal a Nikolai, solo lectura) + fase **F6** en §15; **requisito duro §18.9 anclado en F2/F3:** el log de la bandeja debe **nacer** capturando la terna *propuesta-robot / acción-confirmada / quién-y-cuándo*, o el check-2 no tiene contra qué comparar. `PLAN.md`: creada la entrada `[SIGUIENTE-INTAKE-PROCURADORES-EMAIL]` (antes ausente). **Harness reproducible:** `scripts/eval_matcher_batch.py` (dataset/tag por argv); datasets y resultados con PII (`scripts/intake_batch_dataset*.json`, `data/_aprendizaje/intake_eval_*.json`) **gitignored**. Scratch de la sesión previa sin commitear (no míos): `scripts/debug_search.py`, `scripts/debug_search2.py`, `scripts/test_llm_connection.py`. **Tests +9** (sufijo guion/espacio, es_ruido advisory, serie CRM con espacios, filtro num-only). **Suite: 862 passed, 58 skipped.** **[SIGUIENTE-INTAKE-PROCURADORES-EMAIL]:** (1) **F2 — bandeja Streamlit** (3 tarjetas 🟢/🟡/🔴 + login + log de auditoría + **vista Descartados**); (2) F3 — escritura en CRM (resolver auth nest-mail `x-api-key` vs JWT); (3) rama `dudosa`/multi-match no apareció en 20 correos (rara — la cubre la red de seguridad de F2). Operativa lateral: cambios sin commitear ajenos (viabilidad `data/_plantillas/*`, `docs/CONVENCIONES_DESPACHO.md`, `docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md`, skills drafts) **dejados intactos**.

**Anterior (2026-06-12, sesión 38, skills):** **Plan v3 `skills_registro_y_mejora` ENTREGADO (13 fases).** Commits `a0f97c6`→`a8da548` (13, pusheados). **Parte I — guardado y registro en expediente:** helper canónico `.claude/skills/_shared/registrar_outputs.py` (doble registro: manifiesto `<destino>/_index.md` + wikilinks en `## Navegación` de `_caso.md`; idempotente, atómico, guardia contra `90_Notas personales`, subcarpeta `05_Procedimiento/Jurisprudencia`; modo ad-hoc sin `_caso.md`). `scripts/sync_skill_helpers.py` copia byte a byte los `_shared/*.py` a cada skill (test de no-drift); `scripts/package_skill.py` empaqueta a `.skill` (excluye `node_modules`/`__pycache__`/datos de `logs`). Integrado en `escritos-judiciales` (Fase 0 + guardado/registro por tipo→destino), `cendoj-descarga` (Paso 7-bis: jurisprudencia con ROJ/ECLI a `05_Procedimiento/Jurisprudencia`), `preparacion-juicio-oral` (**vendorizada al repo** desde `despacho-skills/`, sin `node_modules`; registro en Fase 6) y `preparacion-audiencia-previa` (migrada al helper canónico). **Escenario particular:** `_shared/scaffold_caso.py` monta el **mismo árbol `CASO_SUBDIRS`** + `_caso.md` mínimo (`tipo_expediente: particular`, sin campos E&V); `preparacion-litigio-civil/scripts/scaffold_expediente.py` reescrito para usarlo (maestros `PREPARACION_/HECHOS_` a `02_Analisis/`); **no divergencia con el core garantizada por test** (`CASO_SUBDIRS` aquí == `core.config`). **Parte II — mejora continua:** `_shared/registrar_uso.py` (telemetría JSONL; resuelve `FEESDEFENDER_SKILL_LOGS`→`data/_skill_logs/<skill>`→fallback `logs/`; inyecta `version`); `version: "1.0"` + `## Changelog` en las 5 procesales; `scripts/capturar_delta.py` (delta borrador↔`_FIRMADO` con python-docx+difflib → `<ref>_delta.md`); `_shared/programar_revision.py` (revisión vía skill `schedule`: **AP+3 / juicio+7 / escrito+15**); checklists pre/post generalizados; `scripts/motor_mejora.py` (umbral 5+ usos con post → `MEJORAS_<skill>.md` con propuestas ancladas a datos; handoff a Code). **RGPD:** `data/_skill_logs/` **gitignored** (refs reales + texto de escritos en los deltas; nunca a origin ni a `.skill`). Gobernanza en `docs/MEJORA_CONTINUA_SKILLS.md`; backlog del core en `MEJORAS_FUTURAS.md` #30 (que el core lea `<subdir>/_index.md` y resuelva los wikilinks). **Tests +41** en 8 ficheros nuevos; **suite verde** (verja rápida), gold SaRS1 intacto. `.skill` de las 5 procesales regenerados en `dist/skills/` (gitignored). **[SIGUIENTE]:** (1) **reinstalar las skills re-importándolas en Cowork/claude.ai** (el servidor es la fuente de verdad; el disco se revierte con el sync); (2) si el servidor tiene una `preparacion-juicio-oral` más nueva que la copia local vendorizada, re-sincronizar y re-aplicar el registro; (3) el primer ciclo real de mejora se cerrará al acumular 5+ usos con su checklist post. Operativa lateral: cambios sin commitear ajenos (viabilidad-prerelleno, `PLAN.md`, `data/_plantillas/*`, `docs/CONVENCIONES_DESPACHO.md`, etc.) **dejados intactos** (commits acotados a los ficheros de esta entrega).

**Anterior (2026-06-10, sesión 37):** **`[SIGUIENTE-REORG-05CRM]` SEGUNDA TANDA ENTREGADA (D9, D10, D11).** Commit `46dfdcc` (pusheado). **(D10 — bloqueante de D9)** la query REST `list_gdocu_docs_rest` (`core/sync_sudespacho.py`) ahora pide `properties[12]="fechamodificacion"` y el DTO `GdocuDocInfo` gana el campo `modified_at` (ISO-8601 con offset). Nombre/formato de la propiedad confirmados **en vivo** contra el 444 (`scripts/probe_gdocu_fecha.py`; 97/97 docs con fecha; el 500 del CRM ante un nombre inválido enumera las propiedades válidas). **(D9 — detector de conjunto)** `core/conjunto_detector.py`: clusteriza por `modified_at` idéntico (subida en lote) ∩ patrón de prueba `\bD\s*\d+…-` (numeración de la actora; el demandado/contestación NO la usan — **pregunta abierta resuelta** contra el 444); cabecera = el doc del lote SIN patrón (*odd-one-out*; en el 444 es `ORDINARIO - VUELTA VENDEDOR - VALLDAURA.doc`, **no** "DEMANDA" → el keyword procesal es solo desempate); bucket por cabecera o consenso unánime de los miembros; baja confianza → `pendiente_revision`, sin adivinar. **Solo emite propuestas** (eventos `conjunto_detectado` —nuevo, INTAKE_EVENTS 16→17— / `pendiente_revision`); **persistencia de `parent_id`/`orden_en_bundle` DIFERIDA** a `[SIGUIENTE-CATALOGO-DOCUMENTAL]` (el catálogo `indice_documental.yaml` **no existe** aún; decisión de Nikolai: no construirlo a medias). Validado contra el 444 real (3 lotes: 21 docs→01_Demanda, 16→05_Diligencias_Preliminares, 2→99_Otros; 0 misrouting). CLI on-demand `scripts/detectar_conjuntos.py --expediente <id>` (dry-run; `--log --case` para emitir). NO toca el CRM remoto ni mueve ficheros. **(D11 — override local)** el letrado fuerza el bucket de un doc mal archivado editando `bucket_override` (mapa `doc_id: bucket`) en el frontmatter de `_caso.md`; `crm_branch_path` lo consulta **antes** que la carpeta del CRM (nuevo `kind=="override"`, solo buckets válidos), sin tocar el CRM remoto; cableado en `pull_expediente_v2` (lectura única por corrida). Refactor: `resolve_bucket` como **fuente única** de la resolución carpeta→bucket (compartida por `crm_branch_path` y el detector). **⚠️ Concurrencia:** el core de D9/D11 en `core/case_manager.py` (`resolve_bucket`, `read_bucket_overrides`, override) **ya quedó committeado en `ed1fff4`** al barrerlo un `git add -A` de la sesión concurrente que entregó el Drive-folder-cache (s36); el commit `46dfdcc` recoge el resto. **⚠️ Ajeno y roto:** `core/sudespacho_relations.py` + `tests/test_sudespacho_relations.py` están modificados en el working tree por trabajo concurrente (al inicio de esta sesión NO lo estaban) y rompen la colección de pytest por un **import circular** — NO se tocaron ni commitearon; **revisar aparte**. **Tests:** +3 D10 (`test_sync_sudespacho`), +~13 D9 (`test_conjunto_detector` nuevo), +7 D11 (`test_crm_branch_path`), `test_intake_log` (17 eventos). **Suite verde: 652 passed, 58 skipped** (verja rápida, con `--ignore=tests/test_sudespacho_relations.py`); gold SaRS1 intacto. Docs: `INTEGRACION_SUDESPACHO.md` §13.8 (D9/D10/D11) y `MEJORAS_FUTURAS.md` #29 (detector hecho, persistencia diferida). **[SIGUIENTE]**: (1) persistencia `parent_id` de D9 cuando exista `[SIGUIENTE-CATALOGO-DOCUMENTAL]`; (2) follow-up del intake manual (bucketizar `intake_manual` vía `_bucket_for`, ripple a UI) — requiere OK de Nikolai; (3) arreglar el import circular ajeno de `sudespacho_relations`. Operativa lateral: cambios sin commitear ajenos (viabilidad: `data/_plantillas/*`, `_skills_drafts/`, `docs/CONVENCIONES_DESPACHO.md`, `docs/ejemplos/`, etc.) dejados intactos.

**Anterior (2026-06-10, sesión 36):** **`[SIGUIENTE-DRIVE-FOLDER-CACHE]` ENTREGADO.** Cache de `folder_id → (name, drive_id)` en `_caso.md` para eliminar llamadas repetidas a la Drive API. `CaseMeta` gana dos campos: `drive_ev_folder_name` y `drive_ev_drive_id`, persistidos en el frontmatter de `_caso.md`. Nuevas funciones: `get_cached_drive_folder_info(case_id)` y `cache_drive_folder_info(case_id, folder_name, drive_id)` en `core/case_manager.py`; `get_drive_folder_info_cached(folder_id, case_id=None)` en `core/intake_drive.py` (lee cache primero, llama a la API solo en miss, persiste el resultado). `streamlit_app.py`: el auto-fill exitoso del formulario "Nuevo caso" guarda `folder_name` en `session_state` y lo persiste en `_caso.md` al crear el caso. **Tests +7** en `tests/test_intake_drive.py`. Suite verde: **613 passed, 58 skipped** (verja rápida); gold SaRS1 intacto. **[SIGUIENTE]** natural: conectar `get_drive_folder_info_cached` en la pestaña "Casos" de Streamlit y en `pull_drive_ev` para aprovechar el cache en re-pulls. Los pendientes previos siguen vigentes — SEGUNDA TANDA de `[SIGUIENTE-REORG-05CRM]` (D9, D10, D11) y `[SIGUIENTE-INTAKE-CRM-COMPLETO]`. Operativa lateral: el repo conserva cambios sin commitear ajenos a esta sesión (plantillas viabilidad, `_skills_drafts/`, `docs/CONVENCIONES_DESPACHO.md`, D10 `sync_sudespacho.py`, `scripts/probe_gdocu_fecha.py`, etc.) que se dejaron intactos (commit acotado a los 4 ficheros del cache).

**Anterior (2026-06-10, sesión 35):** **`[IDEA-GOBERNANZA-DOCS]` resuelta: malla de referencias cruzadas PLAN↔MEJORAS_FUTURAS + regla de promoción backlog→cola.** Tres ediciones: (1) `docs/MEJORAS_FUTURAS.md` retitulado de "Mejoras futuras del módulo `core/anon/`" a "Mejoras futuras — backlog técnico" (alcance ampliado a todo el repo, de facto ya era así desde las entradas #26-#29); cabecera con referencia cruzada a `PLAN.md` y convención de marcado `[PROMOVIDO → PLAN.md]`. (2) `PLAN.md` cabecera ampliada con referencia al backlog y convención `MEJORAS #NN`; `[IDEA-GOBERNANZA-DOCS]` marcado ✅ resuelto. (3) `CLAUDE.md` §"Planificación y estado": nueva entrada para `docs/MEJORAS_FUTURAS.md` en la lista de fuentes + regla de promoción (disparador concreto: caso real, bug bloqueante o decisión de Nikolai; nunca por anticipación ni completitud de diseño). Sesión de gobernanza documental pura, cero cambios de código. Suite sin cambios (671 passed, 58 skipped; flaky preexistente `test_llm_local` por Ollama ausente). **[SIGUIENTE]**: los pendientes de la sesión 34 siguen vigentes — SEGUNDA TANDA de `[SIGUIENTE-REORG-05CRM]` (D9, D10, D11) y `[SIGUIENTE-INTAKE-CRM-COMPLETO]`. Operativa lateral: el repo conserva cambios sin commitear ajenos a esta sesión (plantillas viabilidad, `_skills_drafts/`, `docs/CONVENCIONES_DESPACHO.md`, `core/` con cambios de sesiones Cowork, `scripts/probe_gdocu_fecha.py`, etc.) que se dejaron intactos (commit acotado a los 3 ficheros de gobernanza).

**Anterior (2026-06-10, sesión 34):** **`[SIGUIENTE-REORG-05CRM]` PRIMERA TANDA ENTREGADA (D8, D6, D7, D12-D13, D14) + expediente 444 migrado.** Aplanado de `00_Input/05_CRM/` del árbol profundo del CRM (hasta 4 niveles + ~20 carpetas vacías) a **buckets planos de un nivel** (`01_Demanda`, `02_Contestacion`, `03_Monitorio_Demanda`, `04_Monitorio_Oposicion`, `05_Diligencias_Preliminares`, `99_Otros` + fallback `99_Sin categoria/<exp>`). Motivo: límite de ruta Windows (260) sobre Drive + desorden de carpetas vacías. **(Paso 0 / D8 — bloqueante)** `CARPETA_ID_TO_PATH` (`core/config.py`) poblado con los IDs reales del tenant, verificados por **doble verificación UI (Nikolai) + REST**: `308`→`Civil/1ª Instancia/Declarativo/Oposicion`, `380`→`Civil/Preliminares/Demanda`. Confirmado que `id_carpeta` es taxonomía **global del tenant** (307 aparece en 657 y 444). Descubrimiento vía minería de los eventos `category_unknown` de toda la data real (solo había 2 IDs sin mapear) + probe REST `get_document_metadata`; el endpoint de árbol `/api/folders/gdocu/{parent}` sigue siendo dead end (§13.3) y `/api/documents/{id}` no trae `categoria`/parent para una hoja ambigua → la rama solo se cierra en UI. **(D6)** función pura `core/case_manager._bucket_for(rama_canonica)` con **exclusión explícita de Preliminares** (su "demanda" NUNCA cae en `01_Demanda`), aplicada dentro de `crm_branch_path` (id_mapping + label_heuristic; routing por rama completa, no por etiqueta-hoja que sobre-captura). **(D7)** andamiaje *lazy*: `_ensure_crm_tree_dirs` crea solo `05_CRM/`, los buckets se materializan al escribir (las escrituras del pull/intake ya hacen `mkdir`); deroga el D1 eager. `05_Procedimiento` (D15) documentado. **(D12-D13)** `scripts/migrate_05crm_buckets.py` (typer `plan`/`apply`, dry-run por defecto): mueve in situ sin re-bajar ni re-OCR; re-llave `_intake_hashes.json` (físicos + alias-only) + `_extract_state.json` por `rel_path` (preserva cache OCR; los `.txt` no se mueven, slug=stem); detecta colisión de stem (sufijo `__1`, sin robar el `.txt` → solo ese re-OCRiza); refresca `by_carpeta`; journal reversible + `.bak`. **Expediente 444 (BaRS6 Vuelta) migrado**: 96 docs → {`01_Demanda`:23, `05_Diligencias_Preliminares`:31 (18 huérfanos del 380 + 13 de Preliminares), `99_Otros`:42}, **0 colisiones, 0 re-OCR**, árbol profundo eliminado. **(D14)** `test_crm_branch_path.py` reescrito (buckets + anti-sobrecaptura + unit de `_bucket_for`), `test_pull_expediente_v2.py` + `test_smoke_paso7.py` (eager→lazy) actualizados, `test_migrate_05crm_buckets.py` nuevo (idempotencia + preservación OCR vía `extract_all` skip + colisión de stem); `test_dedup_manifest.py` y `test_judicial_intake.py` revisados (agnósticos a ruta, sin cambios). **Suite verde: 671 passed, 58 skipped** (verja rápida); gold SaRS1 intacto (`--runslow` verde). Docs: `docs/INTEGRACION_SUDESPACHO.md` §13.5 (tabla con 308/380 + nota taxonomía global) y §13.6 (buckets planos) reescritas; `PLAN.md` ítem `[SIGUIENTE-REORG-05CRM]` marcado primera tanda ✅. **[SIGUIENTE]**: SEGUNDA TANDA — D9 (detector de conjunto por timestamp CRM + patrón `D NN`), D10 (traer fecha de modificación del CRM, su requisito), D11 (override local doc_id→bucket). **Follow-up detectado (fuera de las 15 decisiones, decisión de Nikolai):** el intake manual (`intake_manual.save_file_crm_branch`/`list_crm_branch_files` + selector `CRM_TREE` en `streamlit_app.py:630`) sigue escribiendo a la rama profunda; convendría bucketizarlo vía `_bucket_for` para no recrear el árbol que la migración elimina (no se tocó por ripple a UI + ~6 tests no listados en D14). Operativa lateral: el repo conserva cambios sin commitear ajenos a esta sesión (plantillas viabilidad, `_skills_drafts/`, `docs/CONVENCIONES_DESPACHO.md`, etc.) que se dejaron **intactos** (commit acotado a los ficheros de la reorg).

**Anterior (2026-06-10, sesión 33):** **`[SIGUIENTE-INTAKE-JUDICIAL-AUTO]` ENTREGADO (Fases 0→4) + `[CRITICO-PRESIGNED-DOWNLOAD-BUG]` RESUELTO.** **(Fase 0 — descarga del CRM, el bug crítico)** Diagnóstico contra el expediente 649 (`scripts/diag_presigned_download.py`, 9 rutas candidatas + cruce con la spec OAS3): el CRM redesplegó el módulo `App\Upload` y rompió **los dos** endpoints de presigned-URL — `/api/files/presigned_download_url/{id}` (400 "Unable to generate an IRI for `DTO\Download`") y `/api/documents/presigned_urls/s3/download/{id}` (500 "controller not registered", la ruta alternativa que sugería el plan, también caída). Endpoint vivo: **`GET /api/documents/{id}/downloadUri`** → campo `presignedDownloadUrl`. `core/sync_sudespacho.py::get_presigned_download_url` reescrito para usarlo (firma intacta → 0 cambios en `download_document_rest`/`pull_expediente_v2`); `_extract_url_from_doc` reconoce `presignedDownloadUrl`. Verificación e2e: **31/31** docs del 649 byte a byte (`scripts/_verify_pull_649.py`). Commit `ecf70ec`. **(Fases 1-4 — intake judicial automático)** Nuevo flujo que baja SOLO la demanda y la contestación de un expediente judicial al árbol del caso, sin el workaround manual. **Clasificador** `core/judicial_classifier.py`: heurística regex source-locked **solo por `filename`** — el e2e reveló que `id_carpeta_label` es inservible como disparador (las carpetas DEMANDA/OPOSICION del CRM contienen TODA la prueba D01-D16, no solo la pieza procesal; disparaba 3 demandas y 18 contestaciones falsas). Colapsa duplicados .pdf/.docx; 0/múltiples candidatos → `[PENDIENTE revisión letrado]`, nunca adivina. **Sin LLM** (decisión de Nikolai por RGPD: ningún nombre con PII —hay nombres de personas y direcciones en los filenames— sale del entorno; hook `llm_fn` inyectable queda para el futuro). **Orquestador** `core/judicial_intake.py::intake_demanda_contestacion`: lista → clasifica → pull acotado reutilizando `pull_expediente_v2` (nuevo param `only_doc_ids`, conserva `documents_total_crm` real) → dedup M9, log M10, routing `crm_branch_path`, estado D8. Eventos nuevos `intake_judicial` + `pendiente_revision` (INTAKE_EVENTS pasa de 13 a 15). **Disparo**: CLI `python -m scripts.sync_sudespacho intake-judicial --case <ref> --expediente <id> [--run-pipeline]` + botón «⚖️ Intake judicial automático» en el tab Casos de Streamlit. **E2E real 649**: demanda 40022 auto-identificada y depositada en `05_CRM/Civil/1ª Instancia/Declarativo/Demanda/`, contestación marcada pendiente (2 candidatos distintos 40625/40405). **Tests +17** (`tests/test_judicial_classifier.py` 11 con etiquetas reales del 649 como regresión, `tests/test_judicial_intake.py` 4, `tests/test_sync_sudespacho.py` +2). Suite verde: **626 passed, 58 skipped** (verja rápida). **[SIGUIENTE]**: cuando Nikolai resuelva una contestación marcada pendiente, basta subirla con el expander «📂 Subir al árbol CRM». Posible mejora futura: desempate de ambigüedad (carpeta o LLM local) si el volumen de pendientes molesta. Operativa lateral: el repo conserva cambios sin commitear ajenos a esta sesión (plantillas viabilidad, `_skills_drafts/`, etc.) que se dejaron intactos (commits acotados).

**Anterior (2026-06-07, sesión 32):** **Cerrada `[IDEA-SKIP-INCREMENTAL-EXTRACCION]` de `PLAN.md` (3 tareas): el pipeline deja de duplicar el OCR + skip incremental por hash en extracción y markdown.** (Tarea 1) `core/pipeline.py` llamaba a `extractor.extract_all` **dos veces** por corrida (paso de extracción + de nuevo dentro de `_markdown_step`), ejecutando el OCR (Docling, el único paso caro) el doble de lo necesario, se tocaran o no los documentos. Ahora se extrae una sola vez y el paso de markdown reutiliza ese resultado (`markdown_generator.build` ya lo aceptaba como parámetro). Riesgo cero: si la extracción falla, `extraction` queda vacío y el error real ya se registra en su propio paso `extractor.extract_all`. Commit `13362b3`. (Tareas 2+3) `extract_all(case_id, *, force=False)` salta los documentos cuyo `sha256` de origen (provisto ya por `_inventory.json`) no cambió desde la última corrida, reutilizando el `.txt` previo en vez de reextraer; estado persistido en `01_Procesado/raw_text/_extract_state.json` (hash de origen + método + chars por documento) con constante `EXTRACTOR_VERSION` para invalidar todo el cache si cambia la lógica de extracción (p. ej. el backend Docling). `ExtractionResult` gana el campo `skipped`; `markdown_generator.build(case_id, results, *, force=False)` regenera solo el `.md` de lo realmente reextraído (o si el `.md` falta). Patrón de skip por hash reutilizado de `core/anon`. Firmas retrocompatibles (parámetro `force` keyword-only): el único call-site —`pipeline`— no cambia. Commit `ceb1be1`. **Tests +4**: `tests/test_pipeline.py` (1, regresión de la llamada única a `extract_all` + reutilización del mismo resultado) + `tests/test_extractor_skip.py` (3: skip por hash, reextracción al cambiar el origen, `force`, invalidación por `EXTRACTOR_VERSION`, markdown selectivo). Suite global verde **668/668**. Ambos commits en origin. **[SIGUIENTE]**: smoke real (relanzar el pipeline dos veces sobre un caso con documentos y verificar que la 2ª corrida salta el OCR) — necesita caso real + revisión humana. El **`[CRITICO-PRESIGNED-DOWNLOAD-BUG]`** sigue siendo la **máxima prioridad** de `PLAN.md` (descarga del Gestor Documental del CRM rota, bloquea pull v2). Operativa lateral: el repo conserva cambios sin commitear ajenos a esta sesión (`PLAN.md`, `docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md`, `data/_aprendizaje/metricas.json`, `docs/ejemplos/`) que se dejaron intactos (commits acotados a los ficheros de la sesión). **(Continuación s32 — velocidad de la suite de tests)** La verja de cierre tardaba ~3,5 min porque corría siempre el suite completo, dominado por un único test (regresión gold SaRS1, ~195s) más los de OCR/NLP real, cuando casi ninguna sesión toca el motor. Introducido marcador `@pytest.mark.slow` (registrado en `pyproject.toml` + plumbing `--runslow` en `tests/conftest.py`: `pytest_addoption`/`pytest_configure`/`pytest_collection_modifyitems`) sobre los tests que requieren el motor NLP real (Presidio+spaCy), OCR real (tesseract) o PDF pesado de `core/anon/`: `test_anon_regresion_SaRS1`, `test_anon_ocr`, `test_anon_integration`, `test_anon_separar`. `test_anon_basic` y `test_anon_fixes_review` se quedan rápidos (no cargan Presidio, por diseño) como red de seguridad ágil del motor. `scripts/session_close.py` activa `--runslow` **automáticamente** cuando el commit toca `core/anon/` (detección git: `status --porcelain` del working tree + ficheros del último commit), de modo que la regresión de PII corre siempre que cambia el motor sin depender de que nadie se acuerde; override manual `--runslow`/`RUN_SLOW=1`. De paso, salida del script pasada a ASCII (evita el crash `UnicodeEncodeError` cp1252 en PowerShell, memoria `feedback_powershell_utf8_seguro`). **Medido:** cierre rápido (cambios fuera de `core/anon/`) **~71s** vs ~215-330s antes; `--runslow` **668/668 en ~3:20** (cobertura completa intacta). Sin tests nuevos (solo gating). Commit `f1a16e5`. **Decisión:** se descarta por ahora paralelizar con `pytest-xdist` (bajaría a ~15-20s) — rendimientos decrecientes frente al riesgo de fallos intermitentes en el gate, que es la red de seguridad de PII; reconsiderar si los 71s estorban en la práctica. El cuello restante de los 71s no es el motor NLP (ya gateado) sino `test_llm_local` (~22s, timeouts reales contra Ollama ausente) + el volumen de 600+ tests rápidos.

**Anterior (2026-06-07, sesión 31):** **MEJORAS_FUTURAS §23 cerrada (case_id con PII en el frontmatter) + saneo del doc de mejoras desactualizado.** Al planificar un lote de 3 fugas de PII de prioridad alta (#13 direcciones, #15 emails con `@` OCR, #23 case_id) se descubrió que #13 y #15 — y también #3, #4, #12, #14, #19 — **YA estaban implementadas** desde s26-s27, pero `MEJORAS_FUTURAS.md` no se había actualizado y las seguía listando como abiertas (STATUS.md s27 sí las daba por cerradas). De las tres, solo **§23** seguía abierta. (§23) Nuevo `neutralizar_case_id` en `core/utils.py`: parsea el formato nuevo `<prefijo> - <dirección> (<ref>) - <categoría>` (regex `_CASE_ID_NEW_PARTES`, captura perezosa hasta el primer paréntesis de referencia) y sustituye el tramo de dirección por `[DIRECCION]`, conservando prefijo/referencia/categoría — el id resultante sigue pasando `validate_case_id`; formato heredado (`EV-2026-001`) o no reconocido se devuelve intacto. `core/anon/api.py::_build_md_anonimizado` la aplica al construir el frontmatter, de modo que los `.md` de `06_Anonimizado/` dejan de exponer el domicilio literal cuando se entregan a un LLM externo (flujo H6) — **elimina la necesidad del parche manual tipo `_h5b`**. Verificado que la deanonimización NO consume el `case_id` del frontmatter (localiza el mapa por ruta/`mapa_caso_path`), así que el cambio es seguro. **Tests +9** en `tests/test_utils.py` (`TestNeutralizarCaseId`: formato nuevo con/sin guion antes de la ref, dirección con `-` interno, id neutralizado sigue válido, formato heredado intacto, 3 entradas no reconocidas, idempotencia). **Fixture gold SaRS1 regenerado** vía `python -m scripts.regen_fixture_sars1 --promote`: el diff toca SOLO la línea `case_id:` de los 4 `.md`; el `_mapa_caso.json` NO cambia (reversibilidad intacta). Suite global verde **664/664**. Commit `a88f573` en origin. (Saneo del doc) `MEJORAS_FUTURAS.md` marca ahora `✅ RESUELTO` en §3, §4, §12, §13, §14, §15, §19 (cerradas en s26-s27) y §23 (esta sesión), cada una con su ubicación en código. **[SIGUIENTE]** de prioridad alta **realmente** abiertos tras el saneo: §17 (cabeceras procesales como FP de nombres), §21 (re-OCR de páginas degradadas), §27 (retención/purga de PII en claro en disco), §8 (NER cirílico) — todos de sesión dedicada. Operativa lateral: el repo tenía cambios sin commitear ajenos a esta sesión (`PLAN.md`, `docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md`, `data/_aprendizaje/metricas.json`, `docs/ejemplos/`) que **se dejaron intactos** (commit acotado a los 4 ficheros de la sesión).

**Anterior (2026-05-30, sesión 30):** **Tres bugs de revisión de código en `core/anon/separar.py` cerrados + refactor del lector de líneas LTChar.** Hallazgos de code review ajenos al núcleo del anonimizador (commit `a5b2418` en origin). (1) **Fugas de handles en Windows**: `pdfminer.extract_pages` mantiene el PDF abierto hasta agotar el generador; si el bucle se cortaba por excepción, el origen quedaba bloqueado y un mover/borrar posterior fallaba con `PermissionError` (verificado empíricamente: pdfminer SÍ bloquea a mitad de iteración; `pypdf` lee a memoria y no bloquea). Fix: `contextlib.closing` sobre el generador + `PdfReader` en context manager en `detectar_segmentos`, `separar_pdf` y los fallbacks de `separar_pdf_pipeline`/`procesar`. (2) **PDF de 0 páginas**: el fallback creaba un segmento `1-0` → `range(0,0)` → PDF vacío registrado en `indice.json` como documento real; guarda nueva `total_pag==0`/segmento sin páginas → `PDFVacioError` (excepción nueva en `core/anon/exceptions.py`, exportada en la fachada). (3) **Salida parcial**: si `writer.write` fallaba a mitad quedaban PDFs truncados sin índice; ahora escritura atómica (temporal + `Path.replace`) con limpieza del conjunto parcial en error. **Calidad**: la reconstrucción de líneas LTChar (recoger_chars + agrupado por Y + espaciado por X), duplicada en `separar.py` y `anonimizar.py`, se extrajo a `core/anon/pdf_lineas.py`; salida **byte-idéntica** confirmada por la regresión gold SaRS1. **Tests +nuevas clases** en `tests/test_anon_separar.py` (handles liberados en happy-path y en error simulado, PDF de 0 págs, escritura atómica con limpieza, helper compartido) usando PDFs reales generados al vuelo con `fpdf`; `test_anon_separar.py` 40/40, regresión SaRS1 verde, suite global verde (exit 0). **[SIGUIENTE]** sin nuevos pendientes abiertos por esta sesión. Operativa lateral: se elevó el modo de permisos global a `bypassPermissions` (fuera del repo, a petición del usuario).

**Anterior (2026-05-30, sesión 29):** **Bug de intake Drive `[SIGUIENTE-DRIVE-PULL-PARAMETER-INCORRECT]` cerrado (caso VaRS2).** El pull rclone fallaba con `exit 1: The parameter is incorrect` (error 87 Windows) en 2 ficheros. Diagnóstico con `rclone lsjson -R`: la causa real NO era un Google Doc nativo (hipótesis (a) del item, descartada) sino el **espacio inicial en el nombre** de ` NIE Pasaporte Charlotte.jpg` (image/jpeg) y ` ENCARGO DE VENTA NO EXCLUSIVA + PBC ANEXO 1.pdf` (application/pdf) — el encoding por defecto del backend `local` de rclone codifica el espacio/punto FINAL pero no el INICIAL, y el FS virtual de Google Drive for Desktop (destino `G:\`) rechaza crear ese nombre. **Fix** en `core/intake_drive.py::pull_drive_ev`: flag `--local-encoding` con el set Windows completo + `LeftSpace,LeftPeriod` (constante `_LOCAL_ENCODING`); rclone codifica el espacio inicial a `␠` (U+2420) de forma reversible. Validado con dry-run (no recopia el resto) + ejecución real (4 ficheros, RC=0). Caso VaRS2 desbloqueado y `.pulled` saneado a returncode 0. **Tests +1** (`test_pull_comando_incluye_local_encoding_leftspace`). Entrada nueva en `docs/DEAD_ENDS.md`. Suite global verde (exit 0). Commit `88c0884` en origin. **[SIGUIENTE]** real abierto en intake Drive: `[SIGUIENTE-DRIVE-SHARE-404]` (compartir carpeta con colaboradores falla HTTP 404 en caso BaRS10). Sesión operativa lateral: el usuario activó permisos automáticos globales en `~/.claude/settings.json` (fuera del repo).

**Anterior (2026-05-30, sesión 28):** **Botón «🤖 Organizar localmente» en Streamlit entregado.** Cierra `[SIGUIENTE-ORGANIZADOR-UI]` (la tarea de máxima prioridad). Nuevo expander en la pestaña «Casos» (`tab_casos`) que orquesta el organizador local (`core/local_organizer.py`) en 2 pasos **Proponer → Aplicar** (reflejo del CLI `--plan`/`--execute`). La lógica vive en el core (arquitectura 3 capas): función pública nueva `estado_precondiciones(case_id) -> Precondiciones` (dataclass `drive_ok`, `n_docs`, `anon_ok`, `ollama_ok`, `plan_existe`, `modelo` + propiedad `listo_para_planificar`); el `health_check` de Ollama solo se invoca si Drive+anonimizado están listos (no golpea el servicio en casos no candidatos). UI: semáforo de precondiciones con mensajes accionables (faltan docs → Pull Drive; falta anonimizado → Pipeline/CLI; Ollama caído → `ollama serve` + `ollama pull <modelo>`); botón **Proponer** deshabilitado salvo `listo_para_planificar`, con métricas de resumen (docs / alta confianza ≥0.80 / pendientes / confianza media); botón **Aplicar** deshabilitado salvo que exista `_plan_reorganizacion.md`, con resumen de acciones (COPY/MOVED/SKIP_UNCHANGED) + correcciones registradas + disclaimer fijo de PII en `_organizado/`. Coste 0 (LLM local); todos los controles con `help=` (feedback_ui_tooltips). **Tests +5** en `tests/test_local_organizer.py` (`estado_precondiciones`: todo OK / sin documentos —no consulta a Ollama— / sin anonimizado / Ollama caído / `plan_existe` tras planificar) → 16/16 en el módulo. Suite global verde (exit 0). Sin tests automatizados de la UI (smoke manual pendiente: `run_app.bat` → pestaña Casos → «🤖 Organizar localmente» sobre BaRS1). **[SIGUIENTE]** natural: validación end-to-end del organizador sobre el piloto BaRS1 (`[SIGUIENTE-ORGANIZADOR-VALIDACION]`).

**Anterior (2026-05-27, sesión 27):** **Bug OCR resuelto + `auto_ocr` + campaña de mejoras del motor de anonimización (7 cerradas) + Ollama operativo.** (OCR) `core/anon/ocr.py` §11 corregido (firma de `ocrmypdf.ocr`: input posicional + `language` como lista) y §1 `auto_ocr` integrado en `anonimizar_documento`/`anonimizar_caso` (OCR a copia temporal sin tocar el original) + flag `--auto-ocr`. (Motor anon — todas con test y validadas contra el gold fixture SaRS1 vía `scripts/regen_fixture_sars1.py`, herramienta nueva de regen+diff): **§12** `validate_case_id` admite OTROS `(SIN REFERENCIA)`; **§3+§4** recorte de span al nombre limpio + variantes masculinas en `PALABRAS_EXCLUIDAS`; **§19** el NIG ya no se anonimiza como `[CUENTA]`; **§15** emails con `@` corrompido por OCR (pasada case-sensitive, sin tragar URLs públicas); **§14** variantes OCR del cliente E&V → etiqueta canónica única (derivadas de `_caso.md`, tabla `VARIANTES_OCR_CLIENTE` en config); **§13** direcciones postales españolas (patrón `DIRECCION` con `\b`; capta `CALLE CASTELAR 37-39` del actor y variantes OCR). Las 4 fugas de PII de prioridad ALTA quedan cerradas. Suite completa verde. (Ollama) instalado 0.24.0 (winget), modelo `qwen2.5:14b-instruct-q4_K_M` descargado, `health_check()` = True. BaRS1 anonimizado (32/37; los 5 restantes son planos/catastro sin texto, quedan OCR_PENDIENTE). **[SIGUIENTE-ORGANIZADOR-VALIDACION]** ahora DESBLOQUEADO: con Ollama arriba y BaRS1 anonimizado, validar el organizador (`python -m scripts.organizar_local "BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta" --plan` → revisar `07_AI cowork/_plan_reorganizacion.md` → `--execute`). **[SIGUIENTE-ANON-MEJORAS]**: quedan mejoras NO críticas del motor (orden sugerido): FP/legibilidad §17 (cabeceras procesales), §18 (topónimos de vías), §20 (consolidación por tildes), §16 (coherencia intra-caso); luego §23 (frontmatter expone case_id), §6 (tipo proc desde CRM), §22 (listado explícito de docs), §2 (split automático); y dos grandes para sesión dedicada: §8 (NER ruso + filtro anti-cirílico, descarga de modelo) y §21 (re-OCR ante degradación). Flujo para tocar el motor: cambio + test sintético + `regen_fixture_sars1` (diff-review) + `--promote` + regresión verde (ver memoria `reference_gold_fixture_sars1.md`). **[SIGUIENTE-ORGANIZADOR-UI]** (Streamlit) sigue pendiente, ver más abajo.

**Anterior (2026-05-21, sesión 24):** **Paquete de migración Cowork → Claude Code entregado**. Sesión puramente operativa, cero código del proyecto modificado. Motivación: pain point recurrente del flujo Cowork — todo comando PowerShell lo ejecuta manualmente Nikolai (memoria `feedback_powershell_cd.md`), añade fricción significativa en sesiones largas de desarrollo, y el mount Linux del sandbox desfasa lecturas de ficheros recién escritos (gotcha conocido). Decisión operativa: **código del repo se mueve a Claude Code (CLI nativo Windows, PowerShell directo); Cowork queda para trabajo legal — escritos `.docx`, comunicaciones a clientes, investigación CENDOJ, análisis de casos sin tocar código**. Paquete autocontenido en `docs/migracion_claude_code/` (15 ficheros, reversible, no toca el repo hasta que el usuario aplique los pasos): (1) `README.md` con guía paso a paso, equivalencias Cowork↔Claude Code, rollback; (2) `CLAUDE.md` para raíz del repo — reglas duras, gotchas (PHPSESSID, rclone flags obligatorios, UTF-8 en PowerShell y subprocess Windows, Streamlit cache sentinels solo en éxito), arquitectura 3 capas, formato Sala 1ª TS, terminología propietario/buscador, lista de referencias rápidas a `docs/`; (3) `settings/settings.json` versionado con `allow` (tests, scripts, git, edits en `core/`/`scripts/`/`tests/`/`docs/`), `deny` (`data/CASOS/**`, `**/90_NOTAS_PERSONALES/**`, `.env*`, `rm -rf`), `ask` (`git push --force`, `git reset --hard`), `env` (`PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`); (4) `settings/settings.local.json` plantilla para overrides personales (gitignored); (5) `commands/` con 7 slash commands operativos del día a día — `/status`, `/tests`, `/cierre`, `/renovar-php`, `/pull-rclone` (con flags blindados `--drive-skip-shortcuts --ignore-size --ignore-checksum --inplace --retries 3`), `/health-check`, `/sync-crm` con pre-vuelo PHPSESSID; (6) `skills/copiar_skills.ps1` que copia 6 skills relevantes (`preparacion-litigio-civil`, `escritos-judiciales`, `cendoj-descarga`, `docx`, `xlsx`, `pdf`) desde la instalación local de Cowork a `.claude/skills/` del repo, con fallback `Get-ChildItem $env:APPDATA\Claude -Recurse -Filter SKILL.md` si la ruta canónica ha cambiado; (7) `hooks/README.md` con 3 hooks opcionales propuestos (pre-commit tests si toca `core/`, post-edit warn `data/CASOS/`, pre-tool check PHPSESSID) — recomendación explícita de **no añadirlos al arranque**; (8) `mcp_servers.json` plantilla con bloques `*_disabled` para filesystem, sudespacho (pendiente wrapper), gdrive, gmail — ninguno necesario para arrancar. Suite global verde sin cambios (546/546). Próximo paso operativo cuando el usuario decida aplicar: instalar Claude Code (`npm install -g @anthropic-ai/claude-code`), copiar `CLAUDE.md` a raíz, copiar `.claude/`, ejecutar `copiar_skills.ps1`, añadir `.claude/settings.local.json` y `.claude/mcp_servers.json` al `.gitignore`, `claude` desde PowerShell. Reversible con `Remove-Item -Recurse -Force .\.claude` + `Remove-Item .\CLAUDE.md` (el paquete `docs/migracion_claude_code/` se queda intacto en el repo para volver a aplicar la migración cuando quieras). Cero código del proyecto FeesDefender modificado en esta sesión.

**Anterior (2026-05-21, sesión 23):** **Análisis cruzado del handoff externo de pipeline de anonimización vs estado real de `core/anon/`**. Sesión puramente analítica sin cambios de código. El handoff (conversación previa del 2026-05-20 describiendo un pipeline basado en Presidio + markitdown + docling + ocrmypdf + Piiranha + recognizers ES personalizados + marcado de firmas/sellos/manuscritos) se contrastó con el estado vivo del proyecto. Conclusión: la mayoría ya está en producción (Presidio singleton con es_lg+ca_sm+en_lg, anon sobre Markdown, mapa reversible `_mapa_caso.json`, idempotencia SHA-256, OCR `spa+cat+rus`, recognizers de procedimentales y no-anonimización, fixture gold-standard SaRS1, plan RIA+RGPD entregado en s15). Aportes reales filtrados a `docs/MEJORAS_FUTURAS.md`: (1) **§8 NER ruso re-calibrada a prioridad alta** — incluye desactivación condicional del filtro anti-cirílico de `extraer_texto_pdf` (descarta páginas con ratio < 65 % caracteres legibles, eliminando documentos cirílicos nativos en silencio) vía flag `modo_cirilico=False` que también carga `ru_core_news_md`. Comportamiento por defecto inalterado (cumple `feedback_anon_logica_intacta`). (2) **§24 nueva** — conversor multi-formato `core/anon/conversor.py` (markitdown DOCX/XLSX/PPTX/HTML/MSG/JPG/PNG + docling PDFs complejos), criterio de disparo: primer caso real con prueba en formato no soportado. (3) **§25 nueva** — marcado `[FIRMA]`/`[SELLO]`/`[MANUSCRITO]`/`[ILEGIBLE]`/`[FIGURA]` sobre docling, capa 1 (`[FIGURA]` genérico) con la integración inicial, capa 2 (distinción firma/sello/manuscrito) diferida; bloqueada por §24. **Descartado** del handoff por análisis: Piiranha-v1 (solapa con spaCy_lg, duplica RAM, sin evidencia de mejora), empaquetado Docker (monousuario Windows+Streamlit), split automático "no implementar" (`separar.py` ya existe y se usa en SaRS1 H2), validación independiente sobre muestra (cubierta por fixture SaRS1), OpenAI Privacy Filter (nunca evaluado). Memoria persistente nueva: `project_handoff_anon_20260520.md` con la conclusión cruzada — para que la próxima sesión no me presente el handoff como diseño fresco. Orden de prioridad operativa fijado: primero cerrar SaRS1 H6.3 + H7 (única tarea en vuelo desde s17), luego §8 cirílico (único agujero del pipeline que el flujo manual no puede tapar), §24 y §25 esperan a caso real disparador. Suite global verde sin cambios (546/546 desde s20). Cero código del proyecto modificado en esta sesión.

**Anterior (2026-05-19, sesión 20):** **Renovación proactiva del access_token de `gdrive_ev` + script de auditoría de naming Drive E&V**. Dos entregas que cierran riesgos del intake Drive remanentes de la s19. (1) `core/intake_drive.py::_get_drive_access_token` deja de leer el `access_token` a ciegas del bloque `token = {...}` que rclone almacena en `rclone.conf`: ahora parsea el campo `expiry` (ISO 8601 con offset, tolerando la precisión nanosegundo que escribe rclone), lo normaliza a UTC vía nuevo helper `_parse_iso_expiry` (también nuevo `_parse_rclone_token_block`), y si el token vence dentro de los próximos 5 min (constante `_TOKEN_EXPIRY_MARGIN`) o ya está vencido, fuerza un refresh proactivo lanzando `rclone about gdrive_ev:` — operación trivial que obliga a rclone a usar el `refresh_token` y reescribir la conf. Tras el refresh releemos el bloque y devolvemos el nuevo access_token. Comportamiento defensivo: expiry ausente/malformado → devuelve el access_token tal cual (preserva el comportamiento previo a la renovación); refresh falla → `None` (no propaga un token caducado conocido); cualquier excepción de subprocess → `None`. Aprovechado el cambio para corregir `text=True` → `encoding="utf-8", errors="replace"` (memoria `feedback_subprocess_utf8_windows.md`). **Tests +14** en `tests/test_intake_drive.py`: clase `TestGetDriveAccessToken` (8 casos — vigente, caducado refresca y devuelve nuevo, dentro de margen refresca, refresh returncode≠0 devuelve None, refresh lanza TimeoutExpired devuelve None, expiry malformado defensivo, expiry ausente defensivo, config show falla, token block ausente) + `TestParseIsoExpiry` (5 casos — offset positivo, sufijo Z, precisión nanosegundo truncada a 6 dígitos, naive asumido UTC, string inválido lanza). Suite global verde (~546/546). (2) `scripts/audit_ev_folder_names.py` nuevo: recorre Shared Drives de `DRIVE_EV_TEAM_IDS` deduplicados, consulta Drive API v3 con `q = "mimeType='folder' and trashed=false and name contains 'W-'"` y `pageSize=50`, filtra localmente con regex laxo `_W_ID_PROBE = r"\bW-[A-Z0-9]{5,8}\b"` para descartar carpetas estructurales como `PROPIEDADES`/`S1`/`Otros tutoriales`, toma los primeros N candidatos y aplica `parse_ev_folder_name`. Reutiliza el helper saneado `_get_drive_access_token` + `_is_rate_limit_response` + `_RATE_LIMIT_BACKOFF_SECONDS`. Output tabular ASCII (sin Unicode en separadores, `sys.stdout.reconfigure(encoding="utf-8")` defensivo para PowerShell con `2>&1 |`) y opción `--json` que guarda reporte en `data/_audit/ev_folder_audit_<ts>.json`. CLI: `--team <code>`, `--limit N`, `--json`. **Hallazgo importante** del test rápido sobre BaRS1: las 3 primeras carpetas raíz del Shared Drive (`PROPIEDADES`, `S1`, `Otros tutoriales`) NO son carpetas-expediente — las W-XXXXXX están **anidadas** bajo carpetas estructurales. Esto invalida la hipótesis del briefing inicial ("listar primeras 5 carpetas de la raíz") y motivó el filtro local con regex laxo. La ejecución completa de la auditoría queda pendiente para próxima sesión. **8 mejoras nuevas de robustez del intake Drive** añadidas a "Próximas tareas — No bloqueantes" tras revisión sistemática de puntos de fallo: OAuth client propio en GCP (elimina cuota compartida del project 202264815644), cache `folder_id → (name, drive_id)` en `_caso.md` (reduce llamadas API >80% en producción), `--retries 3 --retries-sleep 5s` en rclone copy, mensajes de error específicos por status code en `get_drive_folder_info`, health-check pre-flight unificado, logging estructurado `data/_audit/drive_intake.jsonl`, alertas keep-alive, validación periódica de `DRIVE_EV_TEAM_IDS`. **Pendientes diferidas a próxima sesión**: ejecución de la auditoría completa sobre los 19 Shared Drives únicos (script ya listo) + validación empírica del flag `--drive-skip-shortcuts` (tarea [SIGUIENTE-DRIVE-SHORTCUTS-LEGITIMOS] sin avance en s20).

**Anterior (2026-05-19, sesión 19):** **Fix `rclone exit 1` por dangling shortcut en carpetas E&V + captura UTF-8 de stderr en Windows**. Cierre de `[SIGUIENTE-PULL-RCLONE-EXIT1]`. Dos cambios mínimos en `core/intake_drive.py::pull_drive_ev`: (1) flag `--drive-skip-shortcuts` añadido al comando rclone — las carpetas W-XXXXXX del Drive E&V contienen accesos directos heredados de consultores rotados cuyo target ha perdido permisos; sin el flag, un único shortcut roto provocaba `rclone exit 1` aunque los demás 40+ ficheros se hubieran copiado bien (la pieza de gestión documental del pipeline quedaba vacía en `.pulled` con `rclone_returncode=1`); con el flag, los shortcuts (válidos o danglers) se omiten silenciosamente y el pull es exitoso para todos los ficheros nativos. Trade-off conocido: shortcuts E&V legítimos hacia ficheros *fuera* del Shared Drive no se traen; aceptable porque el uso típico apunta dentro del mismo drive (rclone los recorre igual de forma recursiva). (2) `subprocess.run` cambia `text=True` por `encoding="utf-8", errors="replace"` — en Windows el `text=True` decodifica con cp1252 del sistema; cuando rclone emite a stderr nombres de fichero con tildes catalanas malformadas (`pla╠Çnols`) o normalización NFD, el stream se truncaba a `""` antes de llegar a Python y el error real se perdía, dejando solo `rclone exit 1: ` en el `.pulled`; con UTF-8 + replace la captura es íntegra y diagnosticable. Diagnóstico reproducible: ejecutar `rclone copy gdrive_ev: <target> --drive-team-drive <id> --drive-root-folder-id <id> -vv` desde PowerShell — revela los `NOTICE: Dangling shortcut "<file>" detected` + `ERROR : Failed to copy: failed to open source object: can't read dangling shortcut`. **Caso real desbloqueado**: BaRS1 - Tibidabo 8 - (W-02VND1) — 41/41 ficheros (137 MiB) bajados manualmente desde `%TEMP%\test_bars1\` a `00_Input/01_Drive EV/` tras saneo de `.pulled` (returncode=0, errors=[]). El shortcut roto en raíz era `Atles de planòls.pdf` (existe homónimo válido dentro de `Planos/`, sí copiado). Pre-existente: solo había `RONCESVALLES Mantenimiento.pdf` + `.pulled` corrupto (Streamlit se cortó tras el primer fichero por el exit 1). **Tests**: `tests/test_intake_drive.py` 43/43 verde sin cambios (los mocks de `subprocess.run` ignoran args/kwargs, el añadido del flag no afecta). Suite global verde. **Entradas nuevas en `docs/DEAD_ENDS.md`**: "rclone copy sobre carpeta E&V con dangling shortcut" + "`subprocess.run(text=True)` en Windows con stderr no decodificable" — ambas con sección Solución aplicada. **Pendiente abierto**: smoke manual end-to-end desde la UI (crear un caso E&V cualquiera, verificar pull terminado con `rclone_returncode=0`) — no automatizable.

**Anterior (2026-05-12, sesión 18):** **Fix auto-fill Drive E&V resiliente a rate-limit de la Drive API**. Tres capas: (1) `core/intake_drive.get_drive_folder_info` añade retry con backoff exponencial 2/5/10 s ante 403/429 cuando el body trae `reason ∈ {rateLimitExceeded, userRateLimitExceeded}` — síntoma típico de la cuota global del OAuth client compartido de rclone (project_number 202264815644). Errores no recuperables (401, 404, 500, 403 sin reason de rate-limit como `insufficientPermissions`) terminan en 1 solo intento. Worst-case añadido a la UI: ~17 s. Helper `_is_rate_limit_response` aislado y defensivo ante JSON malformado (si el body no parsea, asume NO rate-limit para no entrar en bucle de reintentos contra error permanente). (2) En `streamlit_app.py` el bloque de auto-fill solo marca el sentinel `_nc_drive_autofilled_fid` tras éxito — antes lo marcaba siempre, dejando cacheado un intento fallido durante toda la sesión sin retry posible (causa raíz del bug reportado: F5 lo arreglaba porque limpiaba `session_state`). Cuando la llamada falla se setea `_nc_drive_autofill_failed` (no-sticky entre reruns) que dispara un `st.warning` visible con botón "🔄 Reintentar auto-fill". (3) **+5 tests** en `tests/test_intake_drive.py::TestGetDriveFolderInfoRetry` cubriendo recover en 2º intento (403 y 429), agotamiento de los 4 intentos totales (1+3 backoffs), no-retry para 403 con `insufficientPermissions`, no-retry para 500. **Suite global verde (524/524).** **Pendiente abierto en esta sesión**: el auto-fill funciona end-to-end con la URL `https://drive.google.com/drive/u/2/folders/1OReG4jZzwh6-l5j5AKYL_8Jpc5a6fzCX` (Montsant 34 - Montcada i Reixac - W-0466A1, BaRS8), pero el **pull rclone subsiguiente falla con `rclone exit 1`** sin stderr surfaced en la UI. Bug nuevo apuntado en "Próximas tareas — No bloqueantes" como `[SIGUIENTE-PULL-RCLONE-EXIT1]`. Memoria persistente nueva: `feedback_streamlit_cache_solo_en_exito.md` (regla general: nunca marcar sentinel de cache antes de validar éxito del side effect — aplicable a cualquier bloque Streamlit con API/IO).

**Anterior (2026-05-12, sesión 17):** **H6 paso 6.1 + 6.2 cerrados + reorganización expediente SaRS1 + H5b parche cobertura**. Sesión operativa sobre el caso SaRS1 sin tocar código del proyecto. Cinco bloques: (1) **H6 paso 6.1 cerrado**: 4 piezas split (cédula 2pp + decreto 3pp + demanda 30pp + anexos 39pp) subidas manualmente al gdocu del expediente judicial 659 vía SPA sudespacho.net, todas alojadas en rama raíz `General/` (decisión usuario: simplificación por bajo volumen documental; no se usaron subcarpetas semánticas Civil → 1ª Instancia → Declarativo). Decisión actualizada de tipo subida: **opción (b)** — solo piezas split, sin OCR completos ni originales sin OCR (descarte de duplicados por el usuario tras propuesta inicial opción a). Caveat OCR pp 1-20 del DOC_ANEXO se incluye tal cual en los .md anonimizados con advertencia explícita al frontier en el prompt (**opción a**). Documentos pre-existentes en gdocu (2): `ESCR PROCU-PERSONAMIENTO.pdf` + `JUSTIF APUD-ACTA.PDF` (de personación procesal, no parte de H6). (2) **H6 paso 6.2 preparado**: prompt para Claude frontier redactado en `07_AI cowork/_prompt_frontier_H6.md` con contexto del caso (E&V Spain S.L.U. demandada en juicio ordinario LPH 249.1.8 sobre instalación no autorizada de equipos de aire acondicionado en patio comunitario, cuantía 18.000 €) + 4 .md adjuntos + caveat OCR del anexo + estructura procesal Sala 1ª TS (hechos, fundamentos jurídicos, alegaciones a las pretensiones del actor, suplico) + reglas de honestidad (no inventar jurisprudencia, conservar etiquetas anonimizadas, placeholders `[CITAR JURISPRUDENCIA SOBRE: ...]` y `[VERIFICAR EN EXPEDIENTE: ...]`) + extensión 15-25 pp + formato markdown. (3) **Reorganización del expediente SaRS1**: separación clara de input/output del LLM externo — `08_Borradores/` renombrada a `09_Borradores/` (output frontier + deanonimizados de H7 + .docx final); nueva `08_Para frontier/` como drop zone canónica de input al LLM externo (4 .md anonimizados copiados de `06_Anonimizado/` SIN frontmatter del motor + `_PROMPT.md` + `README.md` con contrato de la carpeta). Por decisión del plan §9.3 ninguna de las dos se cabla en `core/config.py::INPUT_SUBDIRS` (flujo borrador-iterativo no estabilizado). (4) **H5b — Parche cobertura ampliada** (sub-hilo abierto durante H6 por insuficiencia detectada): sanity check de PII residual previo a exposición al frontier detectó **37 hits no cubiertos por H5** — 4 case_id en frontmatter, 3 "Pedro San Martín" FP intencional (avenida del Tribunal de Santander, restaurada por H5 fila 1, aceptable), 30 FN reales (11 variantes "Castelar 37-39" con formatos OCR diversos `CASTELAR, 37-39`, `CASTELAR NÚMERO 37-39`, `Castelar n”37-39`, `Castelar N0 37-39`, `calle Castelar; Este`, etc.; 6 variantes muy degradadas del cliente `Engeléwolkers`, `Engelavólkers`, `Engel %: Vólkers`, `Vólkers` suelto, `[NOMBRE_22] £: VÓLKERS SPAIN`, etc.; 6 emails del despacho actor con `@` corrompido como E/O/G/C — `abogadosEdelriomiera.es`, `ebogadosOdelriomiera.es`, `abogadosGdelriomiera.es`; 2 URLs corporativas no marcadas en H5 — `www.delriomiera.es`, `www.engelvoelkers.com`; 1 "Adelaida Peñil" parcial residual; 2 propietarias **nuevas no detectadas en H5** por compartir primer nombre con personajes ya etiquetados — "Adelaida Gómez Sainz" ≠ procuradora Peñil, "Mercedes Pita Wonenburger" ≠ presidenta Cacho). Script `07_AI cowork/_h5b_sars1_cobertura_completa.py` (no versionado, mismo patrón H2/H4/H5): backup `.bak.h5b` + ampliación mapa (45 etiquetas, +5 entidades nuevas incluyendo **categoría URL nueva** con `[URL]`=delriomiera.es y `[URL_2]`=engelvoelkers.com) + 16 reglas FN_RULES_H5B (operan **solo sobre body**, conservan frontmatter del motor para H7) + regeneración de `08_Para frontier/` con frontmatter neutralizado (case_id literal queda fuera del LLM externo) + verificación final. 35 sustituciones FN aplicadas (1 CED, 3 DEC, 5 DEM, 26 ANX). **1 hit residual línea 708 DEM** cubierto por parche puntual posterior (regla H5b no contemplaba cierre Markdown `**` entre separador `£:` y "VÓLKERS"). Sanity final: **0 hits PII residuales** (excluyendo los 3 "Pedro San Martín" FP intencional documentado). Etiquetas totales en `08_Para frontier/`: **169** (subida desde 101 post-H5). (5) **H6 paso 6.3 pendiente** (no completado en esta sesión): entrega al frontier + recepción borrador. Operativa para próxima sesión: pegar `08_Para frontier/_PROMPT.md` en conversación nueva de Claude.ai web o app/Cowork con perfil distinto del repo FeesDefender (acceso de carpeta solo a `08_Para frontier/`), adjuntar 4 .md, recibir borrador → guardar como `09_Borradores/contestacion_demanda_SaRS1_v1_anonimizado.md`. **Lección operativa** descubierta esta sesión y documentada en `docs/DEAD_ENDS.md`: PowerShell `Add-Content -Value (Get-Content -Raw)` **sin** `-Encoding UTF8` produce double-encoding cuando el sistema usa codificación de página Win-1252 (lee UTF-8 como Win-1252, escribe como UTF-8 → mojibake "decisiÃƒÂ³n" en lugar de "decisión"); fix: usar `[System.IO.File]::ReadAllText/WriteAllText/AppendAllText` con `UTF8Encoding($false)` siempre que se manipulen ficheros UTF-8 desde PowerShell. **Mejora futura** añadida a `docs/MEJORAS_FUTURAS.md`: el motor (`core/anon/api.py`) escribe en el frontmatter de `06_Anonimizado/*.md` un `case_id` literal con la dirección PII; H5b mitigó stripeando frontmatter al copiar a `08_Para frontier/`, pero la mitigación a futuro debería ser anonimizar el case_id en el frontmatter del motor o tener un modo "para frontier". Suite global verde sin cambios (sigue 519/519 desde s16 — Fase 0 subdivisión ciudades). Cero código del proyecto FeesDefender modificado en esta sesión — todo el trabajo de H5b vive en el caso bajo `07_AI cowork/` (ignorado por git al no estar en data/CASOS/ ni en el proyecto). Memoria persistente actualizada: `project_sars1_anon_pipeline.md` con cierre H5b + nueva estructura 08/09; nueva `feedback_powershell_utf8_seguro.md` con la regla del mojibake.
**Anterior (2026-05-21, sesión 24, hilo despliegue E&V):** **Plan de hospedaje del Streamlit para E&V redactado** + **script de migración del repo a SSD local listo**. Sesión puramente de planificación: cero cambios de código, suite sin tocar. Dos productos: (1) `docs/PLAN_DESPLIEGUE_EV.md` — arquitectura VPS Hetzner CX22 EU (~€5/mes) + Cloudflare Tunnel (sin puertos expuestos) + Cloudflare Access (auth + MFA gratis ≤50 users); rol nuevo `ev_team_leader` (lectura sobre sus casos + alta de nuevos asuntos vía formulario, queda con tag `pending_review=true`); matriz de permisos por rol (admin / despacho / ev_team_leader) con filtro hermético en el core, no en la UI; migración `data/CASOS` al servidor con backup dual rclone (Drive operativo + Backblaze B2 cifrado en cliente con `rclone crypt`); 6 fases (0 pre-requisitos, 1 infraestructura VPS+Tunnel+Access, 2 datos, 3 dev auth+vista E&V+alta, 4 cumplimiento RGPD/RIA+anexo despacho↔E&V, 5 piloto Marta + apertura 1-2 Team Leaders); calendario tentativo s25-s32; camino crítico no técnico = anexo de tratamiento despacho↔E&V (despacho responsable, E&V destinatario no encargado, qué datos exactos verán, base legal interés legítimo + información en hoja de encargo, plazos, notificación brechas). (2) `scripts/migrate_repo_local.ps1` — automatiza migración del repo de Drive a `C:\Repos\FeesDefender` + push a GitHub privado; 10 pasos idempotentes (pre-checks repo+git+suite, grep rutas hardcoded `G:\Unidades compartidas`, configurar remoto, push, clone, `.venv`, deps, `.env` parcheando `CASOS_ROOT` a Drive en UTF-8 sin BOM, suite verde desde local, resumen siguientes pasos); independiente del despliegue E&V; resuelve lentitud Claude Code/pytest sobre Drive (ortogonal a Fases 0-5). TODO list: 7 tareas creadas (Fase A independiente "Mover repo a local + GitHub privado" + Fases 0-5 del despliegue E&V con dependencias secuenciales y Fase 4 paralela a Fase 3). Memoria persistente nueva: `project_despliegue_ev_streamlit.md` (+ entrada en `MEMORY.md`). Decisión clave: la migración del repo a local (Fase A) y el despliegue E&V (Fases 0-5) son ortogonales; Fase A puede ejecutarse cuando se quiera para ganar velocidad inmediata en Claude Code.

**Anterior (2026-05-12, sesión 15):** **Plan de adecuación RIA + RGPD entregado**. Documento `Plan adecuacion FeesDefender - RIA RGPD.docx` (26 pp., A4, formato del despacho — Times New Roman 12, márgenes 2,5 cm, interlineado 1,5, justificado, párrafos numerados, citas 10 pt cursiva con sangría 1 cm) en la raíz del proyecto. Dos partes: (I) Memorando ejecutivo con calificación cerrada — FeesDefender es sistema de IA del art. 3.1 RIA, NO prohibido (art. 5), NO alto riesgo (Anexo III.8.a no aplica — usuario es despacho de abogados, no autoridad judicial; considerando 61 RIA), SÍ sometido a transparencia art. 50 RIA y alfabetización art. 4 RIA (vigente 02/02/2025); despacho = proveedor + responsable del despliegue; Anthropic = proveedor de modelo de uso general (cap. V RIA) + encargado del tratamiento (art. 28 RGPD); transferencia internacional vía DPF + SCCs subsidiarias; supervisión humana significativa → no opera art. 22 RGPD; (II) Documentación base — RAT con dos tratamientos, matriz de obligaciones RIA + RGPD, estructura EIPD, cláusulas modelo arts. 13, 14 y 28, política de gobernanza IA y supervisión humana, régimen de secreto profesional. Plan en cuatro fases con calendario alineado a la aplicación escalonada del RIA (02/02/2025, 02/08/2025, 02/08/2026, 02/08/2027). Acciones del usuario en Fase 0 (fuera del repo): firma DPA Anthropic, verificación DPF, opt-out entrenamiento, sanción formal del plan. Sin cambios de código en esta sesión. Ítem `[SIGUIENTE-CUMPLIMIENTO-RIA-RGPD]` añadido a STATUS.md "Próximas tareas — No bloqueantes" con seis piezas técnicas para sesión dedicada: (1) `docs/CUMPLIMIENTO.md` checklist vivo de la matriz del Anexo B; (2) ampliar `core/intake_log.py` con eventos de cumplimiento (`dpa_renewed`, `formacion_realizada`, `eipd_revisada`, `brecha_detectada`, `prompt_modificado`, `anon_bypass` con justificación obligatoria); (3) banner permanente en UI Streamlit con aviso art. 50.4 RIA; (4) metadato XMP "Generated-By: FeesDefender — Tyukhay Legal" en todos los `.docx` generados (art. 50.2 RIA); (5) `scripts/cumplimiento_check.py` semanal vía Task Scheduler (DPA vigente, formación dentro del año, smoke anonimizador, ACTORES_DESPACHO consistente, sesiones CRM sanas); (6) traslado del `.docx` del plan a `docs/cumplimiento/Plan_Adecuacion_v1.docx` para trazabilidad por commits. Suite sin cambios desde s14 (483/483). Memoria persistente nueva: `project_cumplimiento_ria_rgpd.md` (+ entrada en `MEMORY.md`).

**Anterior (2026-05-12, sesión 14):** **Plan de subdivisión de `CASOS_ROOT` por ciudades trazado**. Documento completo en `docs/PLAN_SUBDIVISION_CIUDADES.md`: 11 puntos de decisión cerrados con sugerencia razonada en cada uno, 7 fases de implementación (Fase 0 extracción `_CIUDADES` a `core/config/ciudades.py`; Fase 1 `case_locator` con tolerancia legacy + refactor de call-sites; Fase 2 campo `ciudad` en `_caso.md`; Fase 3 acción "Reasignar ciudad" en UI con audit log; Fase 4 migración inicial con script `--plan`/`--apply` y rollback; Fase 5 docs; Fase 6 verificación), inventario de los 6 casos existentes y catálogo aprobado de las 7 ciudades (Barcelona, Bilbao, Madrid, San Sebastián, Santander, Sevilla, Valencia). Decisiones operativas clave: nombres con tilde tal cual (`San Sebastián`), detección prefijo→ciudad derivada de `_EQUIPOS_POR_CIUDAD`, fallback `_Sin clasificar`, regla "prefijo `_` = carpeta de sistema", audit log JSONL en `_audit/relocations.jsonl`, refactor `case_locator` obligatorio antes de migrar nada. Sesión puramente de planificación: cero cambios de código, suite sigue 483/483. Próximo paso: arrancar Fase 0.

**Anterior (2026-05-12, sesión 13):** **H5 del plan SaRS1 cerrado: verificación forense + primer fixture gold-standard del proyecto**. Sesión más manual del bucle de mejora continua. **Tabla forense completa** en `07_AI cowork/_revision_anon_SaRS1.md` con 63 filas categorizadas (8 FN bloqueantes, 38 FP de cabeceras estructurales y ruido OCR, 8 MAP de variantes consolidables, 2 SPLIT ya resueltos en H2, 2 OCR no recuperables) — eleva las 7 notas sueltas de H4 a entradas formales y añade los FN críticos detectados (dirección actor `Castelar 37-39` sin etiquetar en 12 sitios, variantes OCR del cliente `ENGEL 8 VÖLKERS`, emails con `@` corrompido a `Q`/`O`, variantes parciales del abogado actor + despacho actor). **3 decisiones de apertura fijadas**: D-H5-1 fixture local-only en `.gitignore` (Pendiente C1 §13 cerrado con opción a), D-H5-2 camino quirúrgico vía script auxiliar Python (NO `REPROCESAR` — el motor regeneraría los mismos FP sin tocar regex/listas, regla D8 + memoria `feedback_anon_logica_intacta`), D-H5-3 OCR del PDF2 pp 1-20 marcado "no recuperable en H5" + entrada alta prioridad en `MEJORAS_FUTURAS.md` (opción ii: H5 es bucle de mejora, no rescate de output). **Script ad-hoc** `07_AI cowork/_h5_sars1_corregir_mapa.py` (no versionado, mismo patrón que H2/H4): backup `.bak.h5` + reconstrucción `_mapa_caso.json` (155 → ~50 etiquetas; eliminación FP, consolidación MAP, adición FN) + sustituciones en los 4 `.md` + log `_h5_correccion_log.txt`. Idempotente. **Fixture gold-standard** en `tests/fixtures/anon/SaRS1/` con `input/` (PDFs OCR-izados + piezas split) + `expected/` (snapshot del MOTOR pre-H5 desde los `.bak.h5` — referencia de regresión sin contradicción con D8) + `expected_corregido/` (output post-H5 como documentación de la dirección de mejora, no como assert) + `REVISION.md` (copia del fichero forense). `.gitignore` actualizado con regla `tests/fixtures/anon/`. Script auxiliar `_h5_sars1_crear_fixture.ps1` no versionado. **Test de regresión nuevo** `tests/test_anon_regresion_SaRS1.py` con `pytestmark = pytest.mark.skipif` colectivo si fixture no presente; reproduce H4 (4 piezas con mapa compartido), monkey-patchea `validate_case_id` (workaround bug §12) y `caso_path` (evita contaminación de `data/CASOS/`), compara `.md` por igualdad (normalizando `fecha:`) y mapa filtrando campos volátiles. **`docs/MEJORAS_FUTURAS.md` enriquecido** con 10 entradas nuevas (puntos 13-22): FN regex DIRECCION (13, alta), FN pre-carga variantes clientes propios (14, alta), FN tolerancia `@` corrompido en EMAIL (15, alta), FN coherencia intra-caso de nombres parciales (16, media), FP lista negra de cabeceras procesales (17, alta), FP toponímicos calle/avenida vs personas (18, media), FP regex CUENTA descartar NIG (19, media), MAP deduplicación tolerante a tildes (20, media), OCR política de re-OCR automático ante degradación (21, alta), refactor `anonimizar_caso` admitir listado explícito de documentos (22, media). **Próximo hilo: H6** (subida manual al CRM gdocu del expediente 659 + entrega a Claude frontier para borrador de contestación a la demanda). Pre-condición H6: usuario ejecuta los dos scripts `_h5_sars1_corregir_mapa.py` (Python) y `_h5_sars1_crear_fixture.ps1` (PowerShell) y confirma tests verdes (incluido nuevo `test_anon_regresion_SaRS1` que pasará en skip o verde según fixture local).

**Anterior (2026-05-12, sesión 12):** **H2 del plan SaRS1 cerrado: split + troceo manual de los 2 PDFs OCR**. Commit `3e759e3`. El split automático de `core/anon/separar.py::separar_pdf_pipeline` generó solo **2 piezas** frente a las 4 lógicamente esperadas (cédula, decreto, demanda, anexos): PDF1 → 1 pieza DEMANDA pp 1-35 (con observación "pp 1-5 absorbidas por cuerpo de DEMANDA"); PDF2 → 1 pieza DOCUMENTO pp 1-39 ("sin marcadores detectados"). Causa raíz: (a) el OCR transcribió la cabecera "CÉDULA DE EMPLAZAMIENTO" del PDF1 pp 1 como `"_ 1 Sección Civil del Tribunal de Instancia de Santander..."` (subrayado + espacio reemplazando el título oficial), y la regla `CEDULA_EMPLAZAMIENTO` exige el marcador en las 3 primeras líneas como portada → no matcheó; (b) "DECRETO" en pp 3-5 aparece solo en texto corrido ("Así por este Decreto lo acuerdo, mando y firmo"), no como cabecera oficial; (c) `TIPOS_SUPER_ABSORBENTES` (`DEMANDA, SENTENCIA, CONTESTACION, OPOSICION`) absorbe las páginas previas al primer marcador detectado cuando ese marcador es un super-absorbente, lo que llevó a las pp 1-5 al cuerpo de DEMANDA; (d) en el PDF2 el OCR de pp 1-20 está muy fragmentado (texto invertido en muchas líneas, pp 20-21 saltadas según señales H1), de modo que los marcadores `DOC_ANEXO`/`DOC_EMAIL`/`DOC_PODER_NOTARIAL` no aparecen como portada limpia. **Troceo manual aplicado** con `pypdf.PdfWriter` (script ad-hoc temporal en `%TEMP%`, no versionado): PDF1 → `01_CEDULA_EMPLAZAMIENTO_01.pdf` (pp 1-2) + `02_DECRETO_01.pdf` (pp 3-5) + `03_DEMANDA_01.pdf` (pp 6-35); PDF2 → `01_DOC_ANEXO_01.pdf` (pp 1-39) como **bloque único** (decisión informada y confirmada por el usuario: trocear por DOC numerado sería frágil con OCR pp 1-20 ruidoso; la calidad del output anonimizado no se ve afectada porque el motor opera token a token y el mapa de entidades es compartido entre piezas). Output en `00_Input/04_Manual/_split/Demanda_Std_{1,2}_ocr/`, cada subcarpeta con su `indice.json` (campo `modo: "troceo_manual_H2"` + nota explicativa). Sanity check páginas 74/74 OK. 4 criterios §5.4 marcados. **Esqueleto `07_AI cowork/_revision_anon_SaRS1.md` creado** con plantilla Anexo A (metadatos del caso, sección H1 OCR, sección H2 split con bitácora, placeholder H4 anonimización, tabla forense vacía para H5, sección decisiones, sección resumen para `MEJORAS_FUTURAS.md`); 2 incidencias categoría SPLIT documentadas para retroalimentar H5. Ruta crítica del plan ahora puede saltar directamente a **H4** (H3 ya estaba cerrado en sesión 11). Caso vive en `data/CASOS/` (`.gitignore`) — el split y el fichero de revisión no se versionan; solo se actualiza `docs/PLAN_SaRS1_anon_pipeline.md §14` (trazabilidad).

**Anterior (2026-05-12, sesión 11):** **H3 del plan SaRS1 cerrado: `deanonimizar.py` reconoce `_mapa_caso.json`**. `core/anon/deanonimizar.py::_localizar_mapa` extendida a **4 niveles** de búsqueda del mapa de entidades: (1) legacy `<base>_mapa.json` adyacente al .md — Expedientes Seguros original, prioridad alta por retrocompatibilidad; (2) legacy `_para_IA` ↔ `_anonimizados` — layout antiguo; (3) **nuevo** `06_Anonimizado/_mapa_caso.json` del ancestro inmediato — formato FeesDefender escrito por `core/anon/api.anonimizar_caso` vía `core/anon/mapa_caso.guardar_mapa_caso`; (4) **nuevo** fallback por frontmatter del propio .md (`mapa_caso_path` o alias `mapa_entidades`, acepta path absoluto o relativo al .md). Helper aislado `_mapa_desde_frontmatter` con import diferido de `core.utils.read_md` para no acoplar el módulo al resto del core. Firma pública (`deanonimizar`, `deanonimizar_texto`) y CLI intactas; cero cambio en el formato JSON consumido (la clave `"mapa": etiqueta→valor` es la misma en legacy `<doc>_mapa.json` y en el nuevo `_mapa_caso.json`). Constantes `_SUBDIR_ANONIMIZADO="06_Anonimizado"` y `_MAPA_CASO_FILENAME="_mapa_caso.json"` replicadas localmente en `deanonimizar.py` (en lugar de importadas desde `core/anon/mapa_caso.py`) — sincronización documentada como dependencia explícita en `docs/ARQUITECTURA.md`. **Tests +13** dedicados en `tests/test_deanonimizar_mapa_caso.py` cubriendo los 4 niveles + edge cases. **Suite global verde** (criterio H3.4 ≥475/475 superado). Sin tocar regex/listas/thresholds del motor (memoria `feedback_anon_logica_intacta`). `docs/PLAN_SaRS1_anon_pipeline.md` §14 actualizada (H3 → Cerrado 2026-05-12). H3 desbloquea H7 (deanonimización del borrador frontier sobre los .md anonimizados de `06_Anonimizado/`).

**Anterior (2026-05-11, sesión 10):** **URL Drive E&V deja de ser obligatoria**. Pequeño fix UX en `streamlit_app.py` tab Nuevo caso: el campo "URL carpeta W-XXXXXX" ya no exige asterisco ni bloquea la creación del expediente cuando está vacío, ni en modo extrajudicial ni en judicial. Comportamiento: si se rellena, sigue habilitando el auto-fill (ciudad/equipo/dirección/ID GO desde el folder ID) y el pull rclone posterior; si se omite, el usuario rellena dirección, ID GO y ciudad manualmente y se omite el pull del Drive. Resto del flujo (`register_drive_ev`, pull rclone) ya estaba blindado con `if _pre_url` y `if _drive_url_val` — sin cambios. Tooltip del campo reescrito para reflejar la opcionalidad. Commit `83f7e67` ya en remoto. Suite global 470/470 verde (sin tests automatizados de la UI; smoke manual pendiente de validación end-to-end por el usuario).

**Anterior (2026-05-11, sesión 9):** **Categoría "Otros casos" + selector cliente propio E&V**. Añadida categoría comodín OTROS (`TIPOS_CASO_OTROS` + `POSICION_OTROS` en `core/config.py`) para casos de E&V no relacionados con defensa o reclamación de honorarios. Mapping `CLIENTES_PROPIOS_EV` con `EV_MMC_SPAIN` (ID=2, default histórico) y `ENGEL_VOLKERS_SPAIN` (ID=27, sociedad matriz — ver https://tnm.sudespacho.net/tnm/ficheros/clientes-propios/27); helpers `cliente_propio_id()` / `cliente_propio_label()` / `CLIENTE_PROPIO_DEFAULT`. `core/sudespacho_relations.link_ev_mmc[_judicial]` aceptan kwarg `cliente_propio_id=` (default `"2"` → cero regresiones en tests previos). `core/sudespacho_create.tag_defaults_for_tipo_caso[_judicial]` devuelven `[]` cuando `posicion == POSICION_OTROS` (sin tag verde de asunto ni tag lila de valoración por defecto); nueva `NOTA_OTROS`. `streamlit_app.py` tab Nuevo caso muestra OTROS en el selector de tipo y, cuando se elige, despliega selector "Cliente propio E&V" con ambas sociedades — la elección se propaga a `link_ev_mmc[_judicial]`. `_NOTAS["OTROS"]` cableado. Posición procesal CRM para OTROS: ACTOR por defecto (criterio: E&V suele consultar como parte que reclama). `docs/INTEGRACION_SUDESPACHO.md` §10.1 actualizado con ID 27 + nota sobre que el tag CRM "OTROS" no existe aún en sudespacho.net — dar de alta manualmente si se quiere filtrar por él en el frontal. **Tests +22** (`test_otros_y_clientes_propios.py`: taxonomía OTROS, helpers de clientes, parametrización `link_ev_mmc`, regresión BAD_DEBT). **Suite global: 470/470 verde**. Herramienta auxiliar nueva `scripts/diag_cliente_propio.py` para auditar `clientes_propios` del tenant (no usada en código de producción).

**Anterior (2026-05-11, sesión 8):** **Incidencia BaRR3 cerrada + validación referencia local↔CRM + auditoría preventiva + hallazgo bug presigned_download_url**. Diagnóstico cruzado vía REST + frontmatter + INTEGRACION_SUDESPACHO.md confirmó la causa raíz del caso BaRR3 ← expediente 648: el ID 648 era un expediente **real de BaRR1** (Collserola 53 Bis - Bad Debt, num_expediente=28, fecha_alta=2026-04-13), usado el 2026-04-26 como cobaya para capturar HARs (`judicial_648.har`, `INTEGRACION_SUDESPACHO.md` línea 870: *"Pull real expediente 648: 5 docs, 5,35 MB"*). El pull se ejecutó contra el case_id local BaRR3 (que era el case_id activo en desarrollo); los 5 docs de BaRR1 quedaron en `BaRR3/00_Input/sudespacho_648/`. El expediente real de Roser es **649** (`BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU   `, con trailing whitespace del CRM, tolerado por validator vía `.strip()`). No es bug runtime — es contaminación por testing manual durante desarrollo. **Validación preventiva implementada**: `core/sudespacho_relations.fetch_referencia_cliente` + `verify_expediente_referencia` consultan REST `/api/element_registries/<element>` filtrando por id y comparan `referencia_cliente` del CRM contra la esperada local. Wireadas en `streamlit_app.py` (tab Nuevo caso, post-`register_expediente`) y `scripts/sync_sudespacho.py` (CLI pull, pre-descarga). Nunca lanza; muestra `st.warning`/`typer.echo` si mismatch, `st.info` si crm_unreachable, `st.caption` si match. `_REFERENCIA_PROP_BY_ELEMENT` mapea slug → propiedad (`referencia_cliente` lowercase judicial, `Referencia_Cliente` CamelCase extrajudicial; alias `judiciales`/`extrajudiciales` aceptados). **15 tests** dedicados en `tests/test_verify_referencia.py` (match, mismatch, crm_no_disponible, CamelCase extrajudicial, alias judiciales, sin api_key, HTTP 500, red caída, id_no_aparece, tolerancia a espacios, sensibilidad a mayúsculas, expected_referencia None). **Suite global: 448/448 verde**. **Auditoría preventiva** `scripts/audit_referencias_casos.py` reveló 3 anomalías en el repo: (1) BaRR3 ← 648 (contaminación, ahora limpio); (2) MaRS15 ← 653, 654, 655, 656 (4 IDs fantasma no existentes en CRM — probables residuos de intentos de creación fallidos en sesión 2026-05-06, ahora limpios); (3) MaRS2 ← 597 (drift tipográfico — vínculo correcto, solo difería el espaciado y mayúsculas; resuelto editando `referencia_cliente` en sudespacho.net manualmente + sincronizando `meta.referencia_crm` local). Auditoría final: **0/4 mismatches**. Scripts nuevos: `scripts/diag_expediente_648.py` (con fallback de `properties[]` para tolerar schemas del tenant que rechazan propiedades), `scripts/remove_expediente_link.py` (helper depurador del bloque `sudespacho_expedientes`), `scripts/limpieza_post_audit.py` (orquestador one-shot de la limpieza) y shim `scripts/limpieza_post_audit.ps1` minimal (Python maneja UTF-8 nativo; PS 5.1 sin BOM choca con no-ASCII). **Hallazgo crítico nuevo**: el endpoint REST `GET /api/files/presigned_download_url/{doc_id}` devuelve **HTTP 400 "Unable to generate an IRI for App\\Upload\\Infrastructure\\ApiPlatform\\DTO\\Download"** para los 26 documentos del expediente 649 — bug del backend PHP (API Platform). El listado `gdocu` funciona; la descarga no. Confirmado operativo el 2026-05-04, roto a 2026-05-11. Bloquea pulls v2 hasta resolución. Documentado en `docs/DEAD_ENDS.md`. **Lateral**: namespaces id de `expedientes_judiciales` y `extrajudiciales` son independientes (id=597 existe en ambos, son expedientes distintos).

**Anterior (2026-05-11, sesión 7):** **Paso 8 del refactor intake v2 cerrado** + **rename de nomenclatura "ficha_operacion" → "informe_viabilidad"** (decisión del usuario en la misma sesión). 113 + 9 tests verdes (122 totales del paso 8). Suite global ~441/441. **Rename**: la plantilla `data/_plantillas/ficha_operacion.{yaml,xlsx}` pasa a `informe_viabilidad.{yaml,xlsx}` (rename físico ejecutado en PowerShell). En cada caso nuevo, el destino se llama `Informe viabilidad - <case_id>.xlsx` cuando el case_id sigue formato CRM nuevo (`BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU.xlsx`), o `_informe_viabilidad.xlsx` como fallback para case_ids legacy. Helper `_compose_informe_filename(case_id)` en `core/case_manager.py` + sanitize defensivo de caracteres prohibidos en Windows. Comando CLI: `python -m scripts.render_plantillas informe` (antes `ficha`). Casos ya existentes con `_ficha_operacion.xlsx` en disco se dejan tal cual — no migración automática. 9 tests nuevos en `tests/test_compose_informe_filename.py` + 5 tests adaptados en `test_smoke_paso7.py` + 1 constante renombrada en `test_render_plantillas.py`. Paso 8 (tests v2 originales): Ficheros: `test_crm_branch_path.py` (17 — resolución híbrida 3 niveles, ambigüedad, fallback, normalización Unicode), `test_legacy_v1_detection.py` (10 — guard positivo/negativo, case-sensitivity, fichero vs dir), `test_intake_log.py` (23 — schema M10, validación evento, singleton actor, fsync, líneas corruptas), `test_pull_state_atomic.py` (17 — schema D8, idempotencia, simulación de crash en `os.replace`), `test_dedup_manifest.py` (21 — register, reconcile, context manager con/sin excepción, atomicidad save), `test_render_plantillas.py` (14 — smoke estructural, `_meta` con hash, contrato `_StrictBoolLoader`), `test_pull_expediente_v2.py` (11 — integración happy/fallback/legacy/dedup/idempotencia/errores). Dead end nuevo añadido a `docs/DEAD_ENDS.md`: `importlib.reload(core.sync_sudespacho)` desde fixture rompe los imports top-level cacheados de `tests/test_sync_sudespacho.py` (descubierto al primer run del fichero 7; fix: recargar solo `case_manager` + `intake_log` + `intake_manifest`). Decisiones técnicas de organización de tests, mocking duck-typed (`FakeSudespachoClient`), fixtures locales por fichero — documentadas en docstrings de cada testfile. Pendiente: smoke manual UI Streamlit (sidebar M10 + tab Casos expander árbol CRM + tab Nuevo caso con plantillas pre-rellenadas — no automatizable sin navegador) + commit final.

**Anterior (2026-05-11, sesión 6):** **Fix `Numero_Expediente=0` en creación de expedientes extrajudiciales REST.** Causa raíz: el endpoint `POST /api/element_register/extrajudiciales` auto-asigna `Numero_Expediente` de forma INTERMITENTE — confirmado empíricamente con ID 605 (serie 2026, quedó en 0) vs ID 606 (creado consecutivamente, asignado correctamente a 49). `_build_rest_payload_extrajudicial` enviaba `"Numero_Expediente": "0"` y dependía de la auto-asignación del servidor. Fix: replicada la estrategia que se aplicó al judicial el 2026-05-07 — nueva función `_get_next_num_expediente_extrajudicial(year)` (consulta `/api/element_registries/extrajudiciales` con `properties[]+equal+totalItems`, propiedad `Numero_Expediente` en CamelCase, devuelve `max+1`), invocada antes de construir el payload. Si la consulta falla → mantiene `"0"` (comportamiento previo como fallback, no se empeora). Diagnóstico empírico ejecutado vía `scripts/diag_num_extrajudicial.py` (nuevo) — replica la query y muestra detalle de `Numero_Expediente` por expediente + max+1. Tests +10: 7 dedicados a `_get_next_num_expediente_extrajudicial` (max+1, primer expediente=1, ignora vacíos/0, error API/red/sin key → None, valida `properties[]+equal+CamelCase+endpoint`), 3 al builder (mantiene 0 si query falla, calcula valor si exitosa, regresión "no es 0 si query exitosa"); fixtures autouse mockean la nueva GET en `TestBuildRestPayloadExtrajudicial`, `TestCreateExpedienteRest` y `TestCreateExpedienteRestFirst` para que los tests no hagan red real. Memoria `reference_sudespacho_api.md` actualizada con el caso del endpoint intermitente. Caso real ID 605 corregido manualmente por el usuario a Numero_Expediente=50; futuras creaciones desde la UI ya enviarán correlativo correcto.

**Anterior (2026-05-11, sesión 5):** **Refactor intake v2 paso 7 implementado (7a + 7b)**. **7a**: `core/case_manager.ensure_case` v2 — crea árbol `CRM_TREE` eager bajo `00_Input/05_CRM/`, copia `data/_plantillas/ficha_operacion.xlsx` a `02_Analisis/_ficha_operacion.xlsx` (siempre) y `cuestionario_viabilidad.xlsx` si `tipo_caso ∈ INFORME_VIABILIDAD_TIPOS`, pre-rellena REF (`<equipo> - <direccion> (<id_go>)` solo si los tres están presentes) y FECHA en la ficha. `CaseMeta` con `tipo_caso`; persistencia en `_caso.md` con actualización vía `_atomic_write_caso_md` si el kwarg difiere del persistido (D-7a-4). Idempotencia estricta. Helpers nuevos: `_parse_equipo_from_case_id`, `_ensure_crm_tree_dirs`, `_copy_plantilla`, `_prerellenar_ficha`, `_find_label_row`. `register_expediente` preserva ahora los campos v2 (`drive_ev_team_id/folder_id`, `direccion`, `id_go`, `tipo_caso`) al reconstruir `CaseMeta` (bug latente arreglado de paso). **7b**: `core/config.ACTORES_DESPACHO` (5 personas: Nikolai Tyukhay, Karen Paola Barreto, Sergio Piñol, Ana Solange Velastegui, Marta Reynares). `core/intake_manual.save_file_crm_branch` + `list_crm_branch_files` (saneamiento filename + branch_path + doble check `resolve().relative_to`). `streamlit_app.py` con: sidebar M10 al inicio (selector actor + `intake_log.set_actor` cada render, default por substring match contra `os.getlogin()`), expander "📂 Subir al árbol CRM" en tab Casos (selectores encadenados sobre `CRM_TREE`, opción "—" para fijar nodo intermedio como destino, sin descompresión de ZIPs, evento `upload_manual` con `details.destination 05_CRM/<rama>/<file>`), y cableado `tipo_caso/direccion/id_go` en la llamada a `ensure_case` desde "Nuevo caso". Tests: `tests/test_smoke_paso7.py` 17/17 verde (smoke programático del core: ensure_case con todos los tipos, árbol CRM eager, pre-relleno REF/FECHA con y sin id_go, idempotencia preservando edición del abogado, reclasificación, save_file_crm_branch happy path + General + sobrescritura + path traversal + filename inválido + caso inexistente, list_crm_branch_files, intake_log.append_event upload_manual a 05_CRM con actor, sanity ACTORES_DESPACHO); suite global sigue verde. Decisiones D-7a-1 a D-7a-7 y D-7b-1 a D-7b-9 cerradas en memoria `project_intake_estructura_v2.md` para no redecidir. Pendiente: paso 8 (tests v2 dedicados restantes para `crm_branch_path`, `pull_state_atomic`, `dedup_manifest`, `intake_log` exhaustivo, `legacy_v1_detection`, `pull_expediente_v2`, `render_plantillas`), paso 9 (commit final), smoke manual UI Streamlit (sidebar + expander árbol CRM + flujo Nuevo caso con tipo NEGATIVA_OFERTA — no automatizable sin navegador).

**Anterior (2026-05-11, sesión 4):** **Fix auto-fill Drive E&V para carpetas con sufijo captador.** Causa raíz: `_EV_FOLDER_RE` en `core/intake_drive.py` exigía `\s*$` después del `W-XXXXXX`, lo que rompía nombres con sufijo posterior como `393. Hacienda Vadillo - W-02RRO3 - Natalia Trujillano` (sufijo = nombre del consultor que captó la propiedad, NO del cliente — patrón habitual en los Shared Drives de E&V). El auto-fill resolvía correctamente ciudad y equipo desde `driveId` (`0ABSFVWC_PfdBUk9PVA` → `SeRS6`) pero devolvía `("", "")` para dirección + ID GO en silencio. Fix: regex relajado a `^(.*?)\s*[-–]\s*(W-[A-Z0-9]{5,8})\b` (sin `$`, con `\b` de límite de palabra) — descarta cualquier sufijo posterior. Tests +2 dedicados (`test_parse_folder_sufijo_consultor_captador`, `test_parse_folder_sufijo_con_guion_largo`) en verde. Diagnóstico reproducible con `scripts/diag_drive_autofill.py` (nuevo) — reproduce paso a paso la cadena auto-fill (parse_drive_url → rclone access_token → Drive API v3 → parse_ev_folder_name → lookup DRIVE_EV_TEAM_IDS) y señala dónde rompe. Memoria persistente nueva `reference_nomenclatura_carpetas_drive_ev.md` documenta el patrón real `<dir> - W-XXXXXX [- <captador>]` y la advertencia de no usar el sufijo como dato del cliente ni para auto-rellenar `nc_mail_captador`.

**Anterior (2026-05-08, sesión 3):** **Refactor intake v2 implementado pasos 1-6** (de 9 del plan). **Paso 1**: `docs/INTEGRACION_SUDESPACHO.md` §13 (árbol gestor documental — estrategia híbrida + mappings empíricos + dead end endpoint árbol). **Paso 2**: `core/config.py` — `CRM_TREE` anidado, `CARPETA_ID_TO_PATH` (`"1"→General`, `"307"→Civil/1ª Instancia/Declarativo/Demanda`), `INPUT_SUBDIRS` reescrito (sin `05_Demanda judicial`, con `05_CRM` + `06_Entrevistas`), `ENTREVISTA_ROLES`, `INFORME_VIABILIDAD_TIPOS` (7 tipos), constantes `CRM_SUBDIR`, `CRM_FALLBACK_PATH`, `ENTREVISTAS_SUBDIR`. **Paso 3**: `core/case_manager.py` — `crm_branch_path()` (estrategia híbrida 3 niveles, devuelve `(Path, kind)`), `is_legacy_intake_v1()`, `_atomic_write_caso_md()` (`temp + os.replace`), `read_pull_state()` / `update_pull_state()` (schema D8 — `linked_at`, `last_sync`, `documents_total_crm`, `doc_ids`, `by_carpeta`, `errors`); `CaseMeta` extendido con `direccion` + `id_go`. **Paso 4a**: `core/intake_log.py` — M10 log append-only JSONL con 13 tipos de evento (`link_expediente`, `pull_crm`, `dedup_skipped`, `category_unknown`, etc.), actor singleton thread-safe (`set_actor`/`get_actor`), `flush + os.fsync` por escritura. **Paso 4b**: `core/intake_manifest.py` — M9 dedup cross-source SHA-256 con `IntakeManifest` context manager, `reconcile()` (promueve aliases si primary perdido), política skip + aliases. Manifest en `00_Input/_intake_hashes.json`. **Paso 4c**: `core/sync_sudespacho.pull_expediente_v2()` — REST + `crm_branch_path` + manifest M9 + log M10 + state D8; bloquea casos legacy v1; sin flags `force`/`incremental` (manifest hace dedup natural). `pull_expediente` v1 intacto (compat con tests existentes). **Paso 5**: `core/intake_demanda.py` reescrito como `core/intake_manual.py` (destino `04_Manual/`); shim deprecado y tests del shim eliminados por usuario; `streamlit_app.py` actualizado (7 sustituciones). **Paso 6**: `data/_plantillas/cuestionario_viabilidad.yaml` (11 secciones, 82 entries), `data/_plantillas/ficha_operacion.yaml` (7 bloques, 14 hitos con `regla_derivacion` canónica, observaciones automáticas), `scripts/render_plantillas.py` (Typer YAML→XLSX con `_StrictBoolLoader` para resolver `si`/`no` como string en YAML 1.1); XLSX generados y validados visualmente. Camino 3 (derivación automática cuestionario→ficha) cerrado conceptualmente, infraestructura lista — implementación de derivación = horizonte 3 (`core/viabilidad.py`, no implementado). Detalle en memoria persistente `project_plantillas_viabilidad.md`. Pendiente paso 7 (`ensure_case` con copia condicional de plantillas + UI Streamlit con selector actor M10 + expander upload árbol CRM), paso 8 (tests v2 dedicados), paso 9 (commit final).

**Anterior (2026-05-08, sesión 2):** Planificación completa del **refactor v2 de `00_Input/`** cerrada. Acordados D1–D12 + M1–M10 (memoria persistente: `project_intake_estructura_v2.md`). Estructura nueva: árbol del gestor documental del CRM como `05_CRM/` (subcarpeta fija con ramas `General/`, `Civil/`, `Penal/`); `06_Entrevistas/<fecha>_<rol>_<apellido>/` con grabación + transcripción; `_informe_viabilidad.xlsx` en `02_Analisis/` (copiado condicional según tipo de caso); eliminación de `05_Demanda judicial/` (absorbida en `05_CRM/Civil/.../Demanda/`) y `sudespacho_{id}/` dinámica (absorbida en `05_CRM/`). Estado del pull migra de `.pulled` a frontmatter de `_caso.md` (schema D8). Mejoras adicionales: dedup cross-source SHA-256 con manifest `_intake_hashes.json` (M9), log append-only `_intake_log.jsonl` con 13 tipos de evento (M10), fallback `99_Sin categoria/<expediente_id>/` (M5). Casos antiguos congelados (D9). Verificaciones cerradas: V1 (estrategia híbrida `CARPETA_ID_TO_PATH` adoptada), V2 (anonimizador recursivo OK), V3 (Civil + Penal + General). Implementación pendiente — sesión dedicada.

**Anterior (2026-05-08, sesión 1):** Sesión administrativa: borrados los dos casos de prueba `MaRR2 - XXXX - (XXXX) - Bad debt` y `TEST-2026-001` del Drive `EXPEDIENTES - TYUKHAY LEGAL\CASOS\` (CRM ya saneado por usuario antes de la sesión). Las constantes `MaRR2` en `core/sudespacho_create.py`, `core/config.py` y `streamlit_app.py` se mantienen — son tags y folder IDs del equipo "Madrid Residential Rentals 2" del CRM, no referencias al expediente borrado. Estado del proyecto sin cambios respecto a 2026-05-07.

**Anterior (2026-05-07):** **⚠️ INCIDENCIA CRÍTICA detectada al cierre**: el caso `BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU` tiene asociado el expediente CRM **ID 648** cuando el ID real del caso Roser es **649**. Documentos descargados en `00_Input/sudespacho_648/` NO corresponden a Roser — pertenecen a otro expediente del CRM. Resolver al inicio de la próxima sesión (ver [CRITICO-INTAKE-EXPEDIENTE-INCORRECTO] al inicio de Próximas tareas). **Absorción del Anonimizador cerrada (Fases 0-4 ejecutadas)**. Los módulos `_herramientas/` de Expedientes Seguros (`anonimizar.py` v3.10, `separar.py` v1.0, `deanonimizar.py`, `imagen_a_pdf.py`, `renombrar.py`) están absorbidos en `core/anon/` de FeesDefender. La fachada `core/anon/api.py` (`anonimizar_caso`, `anonimizar_documento`) integra el motor con el resto del core. Mapa compartido por caso en `06_Anonimizado/_mapa_caso.json`. Step `do_anonimizar` añadido al pipeline general y a la UI Streamlit. Singleton NLP en `core/anon/nlp_engine.py` evita recargar 1.5 GB de modelos en cada documento. Health check completo en `scripts/health_check.py`. 51 tests nuevos verdes (`test_anon_basic.py` 8 + `test_anon_separar.py` 31 + `test_anon_integration.py` 12). Suite global limpia. `procesar_carpeta.py` y `gestionar_expediente.py` quedan obsoletos por diseño.

---

## ⚡ Checklist de apertura de sesión

Ejecutar siempre antes de empezar a trabajar:

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
git log --oneline -5                             # ¿qué cambió desde la última sesión?
python -m pytest -q --tb=no                     # ¿sigue verde?
python -m scripts.sync_sudespacho check-legacy  # ¿PHPSESSID válida? (Claude la renueva automáticamente)
.\run_app.bat                                    # arrancar Streamlit (o doble clic en el .bat)
```

Luego leer la sección **[SIGUIENTE]** en "Próximas tareas" más abajo.

---

## ⚡ Protocolo de cierre de sesión

**Momento 1 — Claude presenta en el chat (sin acción del usuario):**

Claude revisa y comunica:
- [ ] Tests: ¿alguno nuevo o modificado? ¿estado esperado?
- [ ] Dead ends: ¿hubo callejón nuevo? → entrada propuesta para `docs/DEAD_ENDS.md`
- [ ] Dependencias: ¿algún fichero modificado activa la tabla de `docs/ARQUITECTURA.md`?
- [ ] STATUS.md: texto exacto de fecha + resumen + tareas completadas + [SIGUIENTE]
- [ ] Memoria: ¿hay decisión de arquitectura o patrón nuevo que guardar?
- [ ] Commit: mensaje propuesto

**Momento 2 — Usuario revisa y aprueba** ("sí" en el chat)

**Momento 3 — Claude ejecuta** todos los cambios de ficheros (STATUS.md, DEAD_ENDS.md, memoria)

**Momento 4 — Usuario pega una sola línea en PowerShell:**

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m scripts.session_close
# Si los tests pasan:
git add -A
git commit -m "<mensaje que Claude propuso>"
```

---

## Estado general

| Ítem | Estado |
|------|--------|
| Tests | ✅ 668/668 (Anonimizador absorbido: +51 — 2026-05-07; sufijo captador Drive: +2 — 2026-05-11 s4; Numero_Expediente extrajudicial: +10 — 2026-05-11 s6; tests v2 dedicados paso 8: +113 — 2026-05-11 s7; rename informe_viabilidad: +9 — 2026-05-11 s7; verify_expediente_referencia: +15 — 2026-05-11 s8; categoría OTROS + clientes propios: +22 — 2026-05-11 s9; deanonimizar `_mapa_caso.json` 4 niveles: +13 — 2026-05-12 s11; subdivisión ciudades Fase 0: +36 — 2026-05-12 s16; retry rate-limit Drive API: +5 — 2026-05-12 s18; renovación proactiva access_token gdrive_ev: +14 — 2026-05-19 s20; subdivisión ciudades Fase 1 case_locator: +41 — 2026-05-21 s25; subdivisión ciudades Fase 4 script migración: +9 — 2026-05-21 s25; neutralizar_case_id §23: +9 — 2026-06-07 s31; doble OCR pipeline + skip incremental extracción/markdown: +4 — 2026-06-07 s32) |
| Plan subdivisión CASOS_ROOT por ciudades | ✅ 2026-05-21 s25 — Fases 0-6 cerradas. Fase 0 (s16): `core/ciudades.py` extraído. Fase 1 (s25): `core/casos/case_locator.py` + refactor de call-sites en `core/case_manager`, `core/config`, `scripts/{audit_referencias_casos,scheduled_sync,sync_sudespacho}`. Fase 2 (s25): campo `ciudad` en `CaseMeta`/`_caso.md` y en `ensure_case`. Fase 3 (s25): validación blanda prefijo↔ciudad en UI Streamlit (alta) + expander «🏙️ Reasignar ciudad» en tab Casos + pestaña admin con histórico `relocations.jsonl` (visible solo para Nikolai). Fase 4 (s25): `scripts/migrate_to_city_structure.py` + migración inicial ejecutada (9 expedientes en 5 ciudades; audit log + snapshot rollback en `_audit/`). Fase 5 (s25): `docs/ARQUITECTURA.md` y `README.md` actualizados. Fase 6 (s25): `scripts/verify_city_layout.py` (0 errores, 0 avisos sobre los 9 expedientes); idempotencia del script de migración confirmada; smoke manual de UI «Reasignar ciudad» confirmado por el usuario el 2026-05-21. Plan cerrado al 100 %. |
| SaRS1 — H2 split + troceo manual | ✅ 2026-05-12 s12 — split automático generó 2 piezas vs 4 lógicas (cédula+decreto absorbidos por DEMANDA; PDF2 sin marcadores); troceo manual `pypdf` → 4 piezas (`01_CEDULA_EMPLAZAMIENTO_01.pdf` + `02_DECRETO_01.pdf` + `03_DEMANDA_01.pdf` + `01_DOC_ANEXO_01.pdf`); sanity 74/74; `07_AI cowork/_revision_anon_SaRS1.md` con 2 incidencias SPLIT para H5 |
| SaRS1 — H5b parche cobertura | ✅ 2026-05-12 s17 — script `_h5b_sars1_cobertura_completa.py` cubre 37 hits PII residuales que H5 dejó (+5 entidades nuevas incluyendo categoría `[URL]`/`[URL_2]`; 16 reglas FN ampliadas; 35 sustituciones automáticas + 1 parche puntual); 169 etiquetas totales en `08_Para frontier/` (+68 vs H5); 0 hits PII residuales tras parche; frontmatter del motor neutralizado en copia al frontier |
| SaRS1 — H6 pasos 6.1 + 6.2 | ✅ 2026-05-12 s17 — 4 piezas split subidas a gdocu exp 659 rama `General/` (decisión opción b — sin duplicados); prompt frontier redactado en `07_AI cowork/_prompt_frontier_H6.md` con estructura Sala 1ª TS + reglas anti-alucinación; reorganización del expediente: `08_Borradores/`→`09_Borradores/`, nueva `08_Para frontier/` drop zone canónica del LLM externo |
| `core/anon/deanonimizar.py` _localizar_mapa 4 niveles | ✅ 2026-05-12 s11 — legacy adyacente + `_para_IA` + `06_Anonimizado/_mapa_caso.json` + fallback frontmatter `mapa_caso_path`/`mapa_entidades`; firma pública y CLI intactas; +13 tests dedicados |
| URL Drive E&V opcional | ✅ 2026-05-11 s10 — campo ya no bloqueante en judicial ni extrajudicial; auto-fill + pull rclone condicionados a presencia |
| Categoría "Otros casos" | ✅ 2026-05-11 s9 — `TIPOS_CASO_OTROS` + `POSICION_OTROS`; sin tag verde de asunto ni tag lila de valoración por defecto |
| Clientes propios E&V | ✅ 2026-05-11 s9 — `CLIENTES_PROPIOS_EV` (EV_MMC_SPAIN=2, ENGEL_VOLKERS_SPAIN=27); `link_ev_mmc[_judicial]` parametrizado |
| Tipo de caso `DEVOLUCION_HONORARIOS` | ✅ 2026-05-12 — Defensivo, cajón general no-LAU (compraventa, intermediación mercantil, encargos no residenciales). Tags CRM ya existían (verde ext #126 + jud #55); ahora cableado en `TIPOS_CASO_DEFENSIVA` + `_NOTAS` UI + tests (`TestDevolucionHonorarios`). Queda fuera de `INFORME_VIABILIDAD_TIPOS` por coherencia con LAU_20/DEVOLUCION_RESERVA. |
| Validación referencia local↔CRM | ✅ 2026-05-11 s8 — `core/sudespacho_relations.fetch_referencia_cliente` + `verify_expediente_referencia`; wireadas en UI (post-register_expediente) y CLI (pre-pull); 15 tests verdes |
| Auditoría preventiva | ✅ 2026-05-11 s8 — `scripts/audit_referencias_casos.py`; 0/4 mismatches tras limpieza |
| BaRR3 — incidencia | ✅ Cerrada 2026-05-11 s8 — 648 era de BaRR1, contaminación limpiada; pull v2 de 649 listó 26 docs pero los downloads fallan (bug backend, ver abajo) |
| `core/intake_log.py` | ✅ M10 implementado 2026-05-08 — 13 tipos evento JSONL, actor singleton thread-safe |
| `core/intake_manifest.py` | ✅ M9 implementado 2026-05-08 — manifest SHA-256, IntakeManifest, reconcile, política skip + aliases |
| `core/intake_manual.py` | ✅ Sucesor de intake_demanda.py (2026-05-08) — destino `04_Manual/` |
| `core/sync_sudespacho.pull_expediente_v2` | ✅ 2026-05-08 — REST + crm_branch_path + manifest M9 + log M10 + state D8; bloquea legacy v1 |
| `core/case_manager.crm_branch_path` | ✅ 2026-05-08 — estrategia híbrida 3 niveles, devuelve `(Path, kind)` |
| `core/case_manager.update_pull_state` | ✅ 2026-05-08 — schema D8, atómica via `_atomic_write_caso_md` |
| `core/case_manager.is_legacy_intake_v1` | ✅ 2026-05-08 — detector glob `sudespacho_*/` |
| `core/config.py` v2 | ✅ 2026-05-08 — CRM_TREE, CARPETA_ID_TO_PATH, INPUT_SUBDIRS reescrito, ENTREVISTA_ROLES, INFORME_VIABILIDAD_TIPOS |
| `data/_plantillas/` | ✅ 2026-05-08 — cuestionario + ficha YAMLs canónicos + XLSX generados; camino 3 (derivación automática) |
| `scripts/render_plantillas.py` | ✅ 2026-05-08 — Typer YAML→XLSX con `_StrictBoolLoader` |
| `core/anon/` | ✅ Absorbido de Expedientes Seguros (2026-05-07) — `anonimizar.py` (4 fases NLP intactas, 300+ palabras excluidas, lista blanca operadores jurídicos), `separar.py` (16 tipos documentales + DEMANDA super-absorbente), `deanonimizar.py`, `imagen_a_pdf.py` (con EXIF transpose), `renombrar.py` (estructura plana), `ocr.py` (NUEVO, wrapper Python ocrmypdf), `mapa_caso.py` (NUEVO, mapa compartido por caso), `nlp_engine.py` (NUEVO, singleton Presidio+spaCy), `api.py` (NUEVO, fachada). |
| Pipeline `do_anonimizar` | ✅ 2026-05-07 — flag `do_anonimizar: bool = False` en `pipeline.run`; checkbox "Anonimizar" en UI Streamlit (col4); CLI `python -m scripts.anonimizar_caso CASE_ID`. |
| Output anonimizado | ✅ `06_Anonimizado/<slug>.md` con frontmatter YAML FeesDefender + `_mapa_caso.json`. Idempotencia por SHA-256 del origen. Política `SALTAR`/`REPROCESAR`. Log en `07_AI cowork/_anonimizador_log.md`. |
| Health check anon | ✅ `scripts/health_check.py` — comprueba deps Python, modelos spaCy, Tesseract+idiomas, Ghostscript, smoke test Presidio. |
| Pipeline | ✅ Ejecutado end-to-end (BaRR3, 2026-04-28, 9/9 pasos OK, ~9 min) |
| Primer caso real | ✅ Creado, docs descargados |
| Taxonomía de casos | ✅ Actualizada en config.py |
| `sudespacho_create.py` | ✅ REST-first + x-api-key (2026-05-06): extrajudicial + judicial sin PHPSESSID ni JWT; fallback legacy automático |
| Auth REST escritura: `x-api-key` estática | ✅ 2026-05-06 — Opción A confirmada: POST create/link acepta x-api-key. JWT eliminado de `_rest_post`, `_rest_post_colaborador`, `_link_rest`. Sistema 100% estable. |
| Keep-alive `gdrive_ev` | ✅ 2026-05-06 — `_keepalive_gdrive_ev()` en `scheduled_sync.py`; previene caducidad OAuth a 6 meses |
| `list_gdocu_docs_rest` + `download_document_rest` | ✅ Implementado 2026-05-04 — sin PHPSESSID (solo x-api-key) |
| `pull_expediente` REST-first | ✅ Implementado 2026-05-04 — fallback legacy automático si REST falla |
| `core/intake_demanda.py` | ✅ save_file(), extract_zip() (path traversal sanitizado), list_files() (2026-05-04) |
| `core/share_drive.py` | ✅ share_folder_with_team() via Drive API v3 + build_request_email() (2026-05-04) |
| `05_Demanda judicial` | ✅ Añadida a INPUT_SUBDIRS — ensure_case() la crea automáticamente (2026-05-04) |
| `case_manager.get_drive_ev_ids()` | ✅ Lee folder_id del frontmatter de _caso.md (2026-05-04) |
| UI intake demanda | ✅ Tab Casos — expander upload+unzip ZIP automático (2026-05-04) |
| UI compartir carpeta | ✅ Tab Casos — expander directo (Drive API) + mensaje solicitud (2026-05-04) |
| `sudespacho_relations.py` | ✅ REST-first (2026-05-06): 6 `link_*` via `POST /api/relation_element/` sin PHPSESSID; fallback legacy automático |
| Endpoint saveselect | ✅ Confirmado 2026-04-29 — cliente+colaborador persistidos en exp 600 |
| `core/intake_drive.py` | ✅ Completo — pull rclone gdrive_ev, marker .pulled, `DriveFolderInfo`, `get_drive_folder_info`, 32 tests |
| UI Drive E&V | ✅ Drive URL al inicio del formulario; auto-fill ciudad + equipo + dirección + ID GO desde driveId; caché limpia al cambiar modo Judicial↔Extrajudicial (2026-05-06) |
| Nombres automáticos desde email | ✅ _email_to_nombre() — sin campos manuales |
| Tooltips UI | ✅ help= en todos los campos interactivos de streamlit_app.py |
| Sidebar sesión CRM | ✅ Eliminado 2026-05-06 — keepalive y renovación manual retirados; x-api-key no requiere gestión de sesión en UI |
| Toggle judicial UI | ✅ streamlit_app.py — radio Extrajudicial/Judicial, § 3b con NIG + tipo procedimiento, handler bifurcado (2026-05-04) |
| browser-cookie3 | ✅ PHPSESSID renovación automática desde Chrome en SudespachoLegacyConfig.from_env() (2026-05-04) |
| Renovación proactiva JWT (`_proactive_refresh_if_needed`) | ✅ Implementado 2026-05-04 |
| Detección E-plan (`_is_eplan_landing`, `_get_csrf_token`) | ✅ Implementado 2026-05-04 |
| `_try_renew_php_session` | ✅ Implementado 2026-05-04 — confirmado insuficiente sin PHPSESSID válido |
| `_update_env_field` (escribe .env + os.environ) | ✅ Implementado 2026-05-04 |
| Sidebar session_state (expander persistente) | ✅ Fix 2026-05-04 |
| UI `_email_input_with_crm` + botón 🔍 | ✅ End-to-end verificado 2026-05-04 — fix preset-key, búsqueda REST instantánea tras pre-calentamiento |
| `run_app.bat` | ✅ Lanzador para usuarios finales (Paola, Ana) |
| Tags CRM verificados | ✅ 96 extrajudicial auditados + 10 nuevos mapeados (2026-05-06) |
| Notas de expediente | ✅ 13 NOTA_* alineadas con Manual 1.1.4 |
| `session_close.py` | ✅ Simplificado — solo pytest, sin interactividad |
| `docs/DEAD_ENDS.md` | ✅ 8 callejones documentados (+ SPA login NO crea PHPSESSID, 2026-05-04) |
| `docs/INTEGRACION_SUDESPACHO.md` | ✅ Actualizado 2026-05-06: endpoints REST creación confirmados + mapping propiedades CamelCase vs lowercase + dead ends saveselect |
| `docs/ARQUITECTURA.md` | ✅ Mapa de dependencias + convención commits |
| Protocolo de sesión | ✅ 4 momentos — Claude presenta → aprueba → ejecuta → PS |
| Task Scheduler | ⏳ Pendiente configurar |

---

## Arquitectura v2 — Decisiones tomadas (2026-04-28)

### Flujo de intake por tipo de caso

| Tipo | Trigger | Fuente documentos |
|------|---------|-------------------|
| Bad Debt | Marta Reynares comparte carpeta Drive operación | Drive engelvoelkers.com (W-XXXXXX) |
| Negativas / Vueltas / Incumplimiento | Nikolai crea expediente en CRM | Drive engelvoelkers.com (W-XXXXXX) |
| Defensiva (demandado) | Demanda llega por email a nikolai.tyukhay@engelvoelkers.com | Upload manual desde UI Streamlit |

### Drop Zone para documentos E&V

- Remoto rclone `gdrive_ev` ✅ configurado 2026-04-28 con `nikolai.tyukhay@engelvoelkers.com`.
  - Token en `C:\Users\tnm33\AppData\Roaming\rclone\rclone.conf` (no va a git).
  - Cowork no soporta múltiples cuentas Google — rclone es la solución definitiva.
- **Estructura de carpetas E&V:** no es canónica — cada equipo tiene su árbol propio.
  - Patrón general: `Shared Drive (ej. "Barcelona - S1") → [subcarpetas variables] → W-XXXXXX/`
  - Solución: trabajar con **folder ID** (no rutas), extraído de la URL de la carpeta.
- **Diseño `intake_drive.py`:**
  - `_caso.md` almacena: `drive_ev_team_id` (Shared Drive ID) + `drive_ev_folder_id` (carpeta W-XXXXXX).
  - Usuario pega la URL de la carpeta W-XXXXXX en el formulario Streamlit → se extrae el folder_id.
  - Comando rclone: `rclone copy "gdrive_ev:" dest/ --drive-team-drive <team_id> --drive-root-folder-id <folder_id>`

### Output anonimizado

- Destino: `07_ANONIMIZADO/` en cada caso local.
- Subida al Drive de `tyukhay.legal` para acceso del equipo con sus LLMs.
- Anonymizer: integrar proyecto externo de anonimización ya en desarrollo (no construir desde cero).

### Creación expediente en sudespacho ✅

- **Semiautomática**: FeesDefender prepara datos → botón "Crear en sudespacho" que el usuario confirma.
- Endpoint: `POST /extrajudiciales/saveadd/elemento/extrajudiciales` (frontal legacy, form-urlencoded).
- Implementado en `core/sudespacho_create.py`. Referencia completa en `docs/INTEGRACION_SUDESPACHO.md`.
- **Tags CRM mapeados** ✅ — 87 tags auditados, IDs constantes en `sudespacho_create.py`.
- **`tag_defaults_for_tipo_caso(tipo_caso)`** ✅ — devuelve [tag_verde, tag_lila] según posición procesal.
- **13 `NOTA_*`** ✅ — plantillas de notas de expediente alineadas con Manual 1.1.4.
- Pendiente: integrar en UI Streamlit (pestaña "Nuevo Caso").

### Roles de intake

- Bad Debt y Negativas: Paola / Ana (cuando reciben notificación de Marta o de Nikolai).
- Defensiva: Nikolai (cuando recibe la demanda en su cuenta corporativa).
- Futuro: dar acceso a la UI a todo el equipo para que suban documentos ellos mismos.

---

## Taxonomía de casos (confirmada 2026-04-28)

### Posición actora — Engel reclama (7 tipos)

| Clave interna | Tag CRM | Descripción |
|---------------|---------|-------------|
| BAD_DEBT | BAD DEBT | Impago de factura de honorarios |
| NEGATIVA_OFERTA | NEGATIVA OFERTA | Cliente rechaza la oferta en condiciones del encargo |
| NEGATIVA_ARRAS | NEGATIVA ARRAS | Cliente rechaza firmar arras tras aceptar oferta |
| NEGATIVA_ESCRITURA | NEGATIVA ESCRITURA | Cliente rechaza firmar escritura tras firmar arras |
| NEGATIVA_CONTRATO_ARRENDAMIENTO | NEGATIVA CONTRATO ARRENDAMIENTO | Cliente rechaza formalizar contrato de arrendamiento |
| VUELTA | VUELTA | Cliente cierra la operación sin la agencia aprovechando su gestión |
| INCUMPLIMIENTO_EXCLUSIVA | INCUMPLIMIENTO EXCLUSIVA | Cliente incumple pacto de exclusividad del encargo |

### Posición defensiva — Engel demandado (3 tipos)

| Clave interna | Tag CRM | Descripción |
|---------------|---------|-------------|
| RESPONSABILIDAD_PROFESIONAL | RESPONSABILIDAD PROFESIONAL | Cliente reclama daños por negligencia de la agencia |
| DEVOLUCION_RESERVA | DEVOLUCION RESERVA | Cliente reclama devolución de reserva o compromiso de seriedad |
| LAU_20 | LAU 20 | Arrendatario reclama devolución honorarios (art. 20.1 LAU) |

---

## Primer caso real

**Case ID:** `BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU`
**Cliente:** EV MMC SPAIN, S.L.U.
**Expediente CRM REAL:** **649** (`expedientes_judiciales`) — referencia_cliente en CRM: `BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU   ` (con 3 espacios trailing del CRM; tolerados por `verify_expediente_referencia` vía `.strip()`).
**Estado intake (2026-05-11 s8):** vinculado y validado en `_caso.md`; árbol `00_Input/05_CRM/` creado; 26 documentos detectados en el gestor documental del CRM pero **download bloqueado** por bug del backend `presigned_download_url` (ver `[CRITICO-PRESIGNED-DOWNLOAD-BUG]` abajo y `docs/DEAD_ENDS.md`).
**Historial incidencia (cerrada):** el ID 648 estaba mal vinculado en `_caso.md` desde 2026-04-26. Causa raíz: 648 era un expediente **real de BaRR1** (Collserola 53 Bis, Bad Debt) usado como cobaya para capturar HARs de los endpoints judiciales; el pull se ejecutó contra el case_id local BaRR3 y los 5 docs de BaRR1 contaminaron `sudespacho_648/`. Limpiado 2026-05-11 s8 (carpeta borrada, frontmatter saneado).

---

## Próximas tareas (orden de prioridad)

### No bloqueantes (sesión 4, 2026-05-11)

**[SIGUIENTE-DRIVE-SHARE-404]** (sesión 21, 2026-05-19) — La función de
compartir la carpeta del expediente con colaboradores del despacho desde la
UI falla con **HTTP 404 "File not found"** cuando se invoca contra carpetas
anidadas dentro de Shared Drives propios del despacho. Caso reproductor:
`BaRS10 - Diagonal Ponent 22-24 - (W-02J1KW) - Vuelta`, carpeta
`https://drive.google.com/drive/folders/16ds7GahMmCBe1cbzUAva5GYrT7UqwAXi`,
intento de compartir con `ana.velastegui@tyukhay.legal`,
`paola.barreto@tyukhay.legal` y `sergio.pinol@tyukhay.legal` — los tres
devuelven `HTTP 404: File not found: 16ds7GahMmCBe1cbzUAva5GYrT7UqwAXi`.
La UI ofrece como fallback "Generar mensaje de solicitud" para los emails
que fallaron. Hipótesis a verificar en próxima sesión: (a) la llamada a
`permissions.create` de Drive API no incluye `supportsAllDrives=true`
y/o `supportsTeamDrives=true` cuando el target vive en Shared Drive
distinto del de E&V; (b) el OAuth client de `gdrive_ev` no tiene scope
suficiente sobre el Shared Drive `EXPEDIENTES - TYUKHAY LEGAL` (es un
drive distinto al de E&V — credencial podría estar autorizada solo para
los teamDriveIds de E&V); (c) el `folderId` 16ds...wAXi resuelve a un
shortcut/atajo en lugar de a la carpeta real (improbable porque la URL es
de carpeta), pero merece sanity check. Diagnóstico mínimo: probar la
llamada manualmente desde PowerShell con el access_token de `gdrive_ev`
+ `?supportsAllDrives=true` y comparar respuesta. **No resolver en esta
sesión** — solo registrado para próxima.

~~**[SIGUIENTE-DRIVE-PULL-PARAMETER-INCORRECT]**~~ ✅ 2026-05-30 (sesión 29) —
**Causa raíz confirmada con `rclone lsjson -R`: espacio inicial en el nombre
del fichero**, NO un Google Doc nativo (la hipótesis (a) queda descartada).
Los 2 ficheros que fallaban eran ` NIE Pasaporte Charlotte.jpg` (image/jpeg) y
` ENCARGO DE VENTA NO EXCLUSIVA + PBC ANEXO 1.pdf` (application/pdf), ambos con
un espacio al principio del nombre. El encoding por defecto del backend `local`
de rclone codifica el espacio/punto FINAL (`RightSpace`/`RightPeriod`) pero no
el INICIAL, y el FS virtual de Google Drive for Desktop (destino `G:\`) rechaza
crear un nombre con espacio inicial con error 87 de Windows. **Fix aplicado en
`core/intake_drive.py::pull_drive_ev`**: flag `--local-encoding` con el set
Windows completo + `LeftSpace,LeftPeriod` (constante `_LOCAL_ENCODING`). rclone
codifica el espacio inicial a `␠` (U+2420) de forma reversible. Validado por
dry-run + ejecución real (4 ficheros, RC=0); caso VaRS2 desbloqueado y `.pulled`
saneado a returncode 0. +1 test de regresión
(`test_pull_comando_incluye_local_encoding_leftspace`). Entrada nueva en
`docs/DEAD_ENDS.md`. **Histórico del diagnóstico previo** (s22, 2026-05-20):
tres síntomas en el log de rclone, reproducibles en los 3 intentos
(attempts 1/3, 2/3, 3/3):

  1. `NIE Pasaporte Charlotte.jpg: Failed to copy: The parameter is incorrect.`
  2. `ENCARGO DE VENTA NO EXCLUSIVA + PBC ANEXO 1: Failed to copy: The parameter is incorrect.`
     (sin extensión visible en el log — sospecha: Google Doc nativo, no descargable
     como blob salvo con `--drive-export-formats`)
  3. `CEE/Qualificacio-435039.pdf: Duplicate object found in source - ignoring`
     (no causa fallo en sí, solo NOTICE; pero indica que la carpeta `CEE/`
     tiene el mismo fichero referenciado dos veces — posible shortcut
     legítimo apuntando al original, lo cual entronca con
     `[SIGUIENTE-DRIVE-SHORTCUTS-LEGITIMOS]`)

Hipótesis a verificar (por orden de probabilidad):

  (a) **Google Doc nativo sin extensión** — `ENCARGO DE VENTA NO EXCLUSIVA + PBC ANEXO 1`
      es el único item del log sin extensión; encaja con un Google Doc/Sheet/Slide
      nativo. rclone necesita `--drive-export-formats docx,xlsx,pptx,pdf` para
      bajarlo como blob; sin el flag falla con "parameter is incorrect" porque
      intenta copiar bytes que no existen como tal.
  (b) **Carácter problemático en `NIE Pasaporte Charlotte.jpg`** — visualmente
      limpio, pero podría contener un non-breaking space (U+00A0) o un combining
      diacritic invisible en el nombre. Inspeccionar el byte stream del nombre
      vía Drive API antes de descartar.
  (c) **Shortcut legítimo** — el flag `--drive-skip-shortcuts` añadido en s19
      omite TODOS los shortcuts; si E&V usa shortcuts para enlazar documentos
      compartidos (NIE, PBC), podríamos estar perdiendo ficheros legítimos +
      generando el error 87 al intentar acceder a una URL en lugar de un blob.
  (d) **Path largo en destino** — el nombre completo
      `…ENCARGO DE VENTA NO EXCLUSIVA + PBC ANEXO 1` dentro de un path ya
      profundo (`G:\Unidades compartidas\…\VaRS2 - Doctor Angelico, 4 - (W-02V09K) - Devolucion honorarios\00_Input\01_Drive EV\…`)
      podría rozar el límite MAX_PATH=260 de Windows. Improbable porque otros
      ficheros largos pasan, pero merece sanity check con `\\?\` prefix.

Diagnóstico mínimo para próxima sesión:

  - `rclone lsjson gdrive_ev:<folder-id-VaRS2> --drive-skip-shortcuts=false -R`
    para ver mimeType + shortcutDetails de los 3 items conflictivos.
  - Si `mimeType=application/vnd.google-apps.document` confirma hipótesis (a):
    añadir `--drive-export-formats docx,xlsx,pptx,pdf` al comando de
    `pull_drive_ev` y test dedicado.
  - Si aparece `shortcutDetails`: replantear `--drive-skip-shortcuts` —
    quizá filtrar solo dangling, no todos (cruza con
    `[SIGUIENTE-DRIVE-SHORTCUTS-LEGITIMOS]`).

**Workaround temporal**: el caso VaRS2 está creado localmente; el intake del
Drive se completará manualmente o tras el fix. No bloquea la apertura del
expediente. **No resolver en esta sesión** — solo registrado.

~~**[SIGUIENTE-DRIVE-DESKTOP-CORRUPTED]**~~ ✅ 2026-05-19 (sesión 21) —
`rclone exit 1: corrupted on transfer: sizes differ` reproducido sobre el
caso BaRS10 (Diagonal Ponent 22-24 - W-02J1KW, Shared Drive
`EXPEDIENTES - TYUKHAY LEGAL`). 17 ficheros con destino **más grande** que
origen en deltas variables (+128 B, +268 B…) tras `100%, 11.593 MiB/s, ETA 0s`.
Causa raíz: el destino vive en un Shared Drive de Tyukhay Legal montado por
Google Drive for Desktop; rclone lo trata como `Local file system at //?/G:/...`
pero Drive Desktop intercepta la escritura y al renombrar `.partial → final`
reescribe metadatos, por lo que `stat()` devuelve un tamaño superior y la
verificación post-transfer aborta como "corrupted on transfer" pese a que
los bytes son íntegros. Fix aplicado en `core/intake_drive.py::pull_drive_ev`:
`--ignore-size --ignore-checksum --inplace --retries 3 --retries-sleep 5s`
añadidos al comando rclone. `--inplace` evita además el rename intermedio
que es el evento que más confunde a Drive Desktop. Integridad real
garantizada extremo a extremo por Drive API + TLS en ambos remotes (no se
pierde nada al desactivar la verificación local). 1 entrada nueva en
`docs/DEAD_ENDS.md`. Cierra de paso `[SIGUIENTE-DRIVE-RCLONE-RETRIES]` que
estaba pendiente. **Pendiente smoke**: re-lanzar pull BaRS10 desde la UI y
confirmar `rclone_returncode=0` en `.pulled`.

~~**[SIGUIENTE-PULL-RCLONE-EXIT1]**~~ ✅ 2026-05-19 (sesión 19) —
Causa raíz confirmada con `rclone -vv` sobre BaRS1 (Tibidabo 8 - W-02VND1):
**dangling shortcut** en raíz de la carpeta E&V (acceso directo a un fichero
borrado o sin permisos del consultor captador) — un único shortcut roto
basta para que rclone devuelva exit 1 aunque los 40+ ficheros restantes se
hayan copiado correctamente. El stderr llegaba vacío al `.pulled` por un
bug paralelo: `subprocess.run(text=True)` decodifica con cp1252 en Windows
y se rompía al encontrar tildes catalanas malformadas (`pla╠Çnols`) en los
nombres de fichero. Fix aplicado en `core/intake_drive.py::pull_drive_ev`:
flag `--drive-skip-shortcuts` + `encoding="utf-8", errors="replace"`. Caso
real BaRS1 desbloqueado manualmente (41/41 ficheros, 137 MiB). 2 entradas
nuevas en `docs/DEAD_ENDS.md` con el patrón y la mitigación. Tests
`test_intake_drive.py` 43/43 verde. Smoke end-to-end UI pendiente.

~~**[SIGUIENTE-DRIVE-TOKEN]**~~ ✅ 2026-05-19 (sesión 20) —
`core/intake_drive.py::_get_drive_access_token` reescrita con renovación
proactiva basada en `expiry`. Helpers nuevos `_parse_rclone_token_block` y
`_parse_iso_expiry` (tolera ISO 8601 nanosegundo + sufijo Z). Margen de
seguridad 5 min antes del vencimiento dispara `rclone about gdrive_ev:`
para forzar refresh vía `refresh_token` y releer. Defensivo: expiry
ausente/malformado preserva comportamiento legado; refresh fallido → None
(no propaga token caducado conocido). `text=True` reemplazado por
`encoding="utf-8", errors="replace"` (memoria `feedback_subprocess_utf8_windows.md`).
+14 tests dedicados (`TestGetDriveAccessToken` 8 + `TestParseIsoExpiry` 5
+ los existentes intactos). Suite global verde.

**[SIGUIENTE-DRIVE-NAMING-AUDIT]** (parcial s20, 2026-05-19) — Script
`scripts/audit_ev_folder_names.py` creado: recorre `DRIVE_EV_TEAM_IDS`
deduplicados por Shared Drive ID, consulta Drive API v3 con `name contains 'W-'`
+ filtro local `_W_ID_PROBE` (regex laxo `\bW-[A-Z0-9]{5,8}\b`) y aplica
`parse_ev_folder_name` a los candidatos. Reutiliza el helper saneado de
`[SIGUIENTE-DRIVE-TOKEN]`. CLI con `--team`, `--limit`, `--json` (reporte
en `data/_audit/ev_folder_audit_<ts>.json`). **Hallazgo del test rápido
sobre BaRS1**: las carpetas-expediente NO están en raíz del Shared Drive —
están **anidadas** bajo carpetas estructurales (PROPIEDADES, S1, Otros
tutoriales). Hipótesis original del briefing ("listar primeras 5 carpetas
de la raíz") invalidada; script rediseñado para buscar a cualquier
profundidad. **Pendiente**: ejecutar `python -m scripts.audit_ev_folder_names --json`
sobre los 19 Shared Drives únicos y revisar el reporte; si aparecen patrones
nuevos de naming, ampliar `_EV_FOLDER_RE` + tests dedicados (no tocar regex
sin evidencia, regla D8 + memoria `feedback_anon_logica_intacta` aplicada
también aquí por extensión).

**[SIGUIENTE-DRIVE-SHORTCUTS-LEGITIMOS]** (sesión 19, 2026-05-19; sin avance en s20)
Monitorizar si en las próximas aperturas de expedientes E&V se detectan
ficheros que existen en el Drive original pero NO en `00_Input/01_Drive EV/`
tras el pull. El flag `--drive-skip-shortcuts` añadido en s19 omite TODOS
los accesos directos, no solo los dangling. Hipótesis no validada: E&V usa
shortcuts dentro del mismo Shared Drive (rclone los recorre igual de forma
recursiva), pero si algunos consultores usan shortcuts hacia ficheros de
otros drives o de "Mi unidad" personal, esos ficheros no se traerán al
caso local. Detección posible: (a) script ad-hoc que compare `_inventory.json`
post-pull con listado manual del Drive vía Web; (b) reemplazar el flag por
post-procesamiento del stderr — detectar si todos los errores son
"dangling shortcut" y, si al menos 1 fichero se transfirió, tratar exit 1
como éxito (alternativa quirúrgica documentada en `docs/DEAD_ENDS.md`).
Sin caso confirmado de pérdida en s19/s20 — bajar prioridad si en 10
aperturas no se observa el síntoma.

---

#### Refuerzo del intake Drive E&V — mejoras priorizadas (s20, 2026-05-19)

Tras revisión sistemática de puntos de fallo del intake Drive, se identifican
8 mejoras adicionales. Orden recomendado por relación impacto/esfuerzo:

~~**[SIGUIENTE-DRIVE-RCLONE-RETRIES]**~~ ✅ 2026-05-19 (sesión 21) —
`--retries 3 --retries-sleep 5s` añadidos a `core/intake_drive.py::pull_drive_ev`
junto al fix de Drive Desktop (siguiente entrada). `--low-level-retries`
(default) cubre blips de TCP; los nuevos `--retries` cubren errores
transitorios sostenidos de la Drive API (500/503/429).

**[SIGUIENTE-DRIVE-ERROR-MESSAGES]** (impacto medio, esfuerzo bajo)
Mensajes de error específicos por status code en `get_drive_folder_info`:
hoy todos los no-200 caen en el mismo `return None`. Distinguir y loguear
en `.pulled` (campo nuevo `auth_diagnosis`): 401 → token revocado, sugerir
`rclone config reconnect gdrive_ev:`; 403 + reason `storageQuotaExceeded`
→ cuenta E&V llena; 403 + reason `insufficientFilePermissions` → folder_id
sin permiso del usuario corporativo; 404 → folder_id mal escrito; 5xx →
reintento (ya cubierto). Useful para diagnóstico desde la UI sin reproducir.

**[SIGUIENTE-DRIVE-FOLDER-CACHE]** (impacto alto, esfuerzo bajo)
Cache de `folder_id → (name, drive_id)` en `_caso.md`. Hoy cada llamada a
`get_drive_folder_info(folder_id)` golpea la Drive API. Tras la primera
resolución exitosa, persistir `meta.drive_ev_folder_name` y
`meta.drive_ev_drive_id` en `_caso.md`; en pulls posteriores leer del
fichero local. Reduce llamadas a la API en >80% en producción y reduce
dependencia de la cuota compartida del OAuth client de rclone.

**[SIGUIENTE-DRIVE-INTAKE-LOG]** (impacto bajo runtime, alto post-mortem)
Logging estructurado `data/_audit/drive_intake.jsonl`. Cada `pull_drive_ev`
añade una línea con `{timestamp, case_id, team_id, folder_id, returncode,
files_after, duration_ms, error_summary}`. Sin esto, cualquier caída pasada
se pierde porque `.pulled` se sobrescribe en cada pull. Append-only, mismo
patrón que `core/intake_log.py` M10. Útil para correlacionar caídas con
cambios de cuota / rotaciones de token / horarios.

**[SIGUIENTE-DRIVE-KEEPALIVE-ALERTS]** (impacto bajo, esfuerzo bajo)
Alertas del keep-alive diario de `gdrive_ev`. Hoy
`scheduled_sync._keepalive_gdrive_ev` falla en silencio. Si falla 2
ejecuciones consecutivas → registrar en `data/_audit/keepalive_failures.jsonl`
y mostrar banner rojo en la UI Streamlit al arrancar. Depende de
[SIGUIENTE-DRIVE-INTAKE-LOG] como infraestructura común de logging.

**[SIGUIENTE-DRIVE-HEALTH-CHECK]** (impacto medio, esfuerzo bajo)
Health-check pre-flight unificado: `python -m scripts.health_check_drive`
que verifique en orden: (1) binario rclone, (2) remote gdrive_ev configurado,
(3) bloque token presente con expiry parseable, (4) `rclone about gdrive_ev:`
responde, (5) `drives.list` API responde, (6) los Shared Drive IDs de
`DRIVE_EV_TEAM_IDS` siguen existiendo (lo cubre [SIGUIENTE-DRIVE-TEAM-IDS-WATCH]
si se implementa). Reusable desde la UI Streamlit como botón de diagnóstico
para Paola/Ana.

**[SIGUIENTE-DRIVE-TEAM-IDS-WATCH]** (impacto bajo, esfuerzo bajo)
Validación periódica de `DRIVE_EV_TEAM_IDS`. Script cron-driven semanal
que ejecuta `rclone backend drives gdrive_ev:` y compara con el dict
estático de `core/config.py`. Si E&V crea/elimina/renombra un equipo, lo
detectamos en 7 días en vez de cuando un usuario abra el caso correspondiente.
Output: diff en `data/_audit/team_ids_drift_<fecha>.json` + banner en UI
si hay deltas.

**[SIGUIENTE-DRIVE-NATIVE-RCLONE]** (impacto alto, esfuerzo medio-alto)
Migrar `pull_drive_ev` a copia Drive→Drive nativa, eliminando Google Drive
for Desktop como intermediario. Hoy rclone copia desde `gdrive_ev:` a
`G:\Unidades compartidas\…`, donde Drive Desktop intercepta cada escritura;
los flags `--ignore-size --ignore-checksum --inplace` añadidos en s21
suprimen los falsos positivos de la verificación post-transfer (ver
`docs/DEAD_ENDS.md`), pero la integridad local depende de la Drive API en
ambos extremos. Solución limpia: configurar un segundo remote rclone
`gdrive_tnm` con la cuenta `nikolai.tyukhay@tyukhay.legal` y reescribir el
comando como `rclone copy gdrive_ev: gdrive_tnm:CASOS/<case_id>/00_Input/01_Drive\ EV/`.
Beneficios: (a) integridad verificable de extremo a extremo por Drive API,
(b) elimina el doble ancho de banda (descarga local + reupload de Drive
Desktop), (c) funciona aunque Drive Desktop esté pausado / desconectado /
en error de sincronización, (d) los ficheros aparecen en `G:\` por sync de
Drive Desktop sin intervención. Trabajo: `rclone config` nuevo
(`gdrive_tnm`), refactor de `pull_drive_ev` (destino remoto en vez de
local), ajuste de tests (los actuales asumen path local), decidir el
mapeo `CASOS/<case_id>/…` en el Drive de destino, considerar dependencia
de cuota OAuth de la cuenta de destino. Combina muy bien con
`[SIGUIENTE-DRIVE-OAUTH-PROPIO]` (OAuth propio podría usarse para ambos
remotes).

**[SIGUIENTE-DRIVE-OAUTH-PROPIO]** (impacto MUY alto, esfuerzo medio)
OAuth client propio en GCP. Hoy rclone usa el `client_id` compartido del
project `202264815644` — cuota global por minuto repartida entre todos los
usuarios de rclone del mundo. Cuando satura, no hay mitigación desde
nuestro lado (los backoffs de la s18 alargan, no resuelven). Crear OAuth
Client ID propio (consola GCP, gratis) y registrarlo en `rclone config`
elimina la cuota compartida. Lo natural es hacerlo dentro del proyecto GCP
de E&V (la Service Account pendiente de
`project_gdrive_ev_auth.md`) o, si E&V demora, un proyecto GCP propio del
despacho. Es la palanca de mayor impacto sobre la disponibilidad del
intake Drive a medio plazo.

**[SIGUIENTE-VIABILIDAD-BAD-DEBT]** (decisión del usuario 2026-05-11 s7)
Incluir BAD_DEBT en `INFORME_VIABILIDAD_TIPOS` para que `ensure_case`
también copie el cuestionario + ficha de viabilidad al crear casos de
impago. Hoy el set excluye BAD_DEBT, LAU_20 y DEVOLUCION_RESERVA por
decisión de producto previa; el usuario rectifica para BAD_DEBT. A
confirmar antes de implementar: (1) ¿se reutilizan las 11 secciones
actuales del cuestionario o se adapta a BAD_DEBT (preguntas sobre
devengo de factura, vencimiento, impagos previos)? (2) ¿LAU_20 y
DEVOLUCION_RESERVA también? Cambio mínimo si se reutiliza tal cual:
añadir `"BAD_DEBT"` al `frozenset` en `core/config.py` + test smoke
específico. Detalle completo en memoria `project_plantillas_viabilidad.md`.

**[SIGUIENTE-VIABILIDAD-LLM]** (plan trazado el 2026-05-19 s22)
Pre-relleno LLM del informe de viabilidad usando los documentos del Drive
E&V volcados en el intake. Plan completo en
`docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md`. **Decisiones cerradas (D1-D5)**:
camino cuestionario→derivación a ficha; disparo manual vía botón Streamlit;
clasificador LLM previo sobre el Drive; Claude Haiku (clasificador) +
Sonnet (extractor) sobre docs anonimizados con el pipeline SaRS1; output
paralelo `Informe viabilidad LLM - <case_id>.xlsx` que NUNCA sobrescribe
el informe humano. **Estimación**: 9-12 sesiones (consistente con
horizonte 3 de `project_plantillas_viabilidad.md`). **Recomendación**:
arrancar solo por **Fase 1** (pre-procesado del Drive E&V — OCR → MD →
anonimización en `02_Analisis/_llm/`). Aporta valor independiente del LLM
(permite llevar manualmente los docs anonimizados a Claude.ai como en
SaRS1 H6) y desbloquea cualquier Fase 2-5 posterior. **Bloqueado por**
tres decisiones de Fase 0 que viven en el plan como `[PENDIENTE]`:
inclusión de BAD_DEBT (mismo pendiente de `[SIGUIENTE-VIABILIDAD-BAD-DEBT]`),
modelo del clasificador (Haiku vs Ollama vía `.env`) y prioridad de
arreglar los bugs `MEJORAS_FUTURAS §11` (OCR kwargs) y `§12` (validate_case_id
rechaza `(SIN REFERENCIA)`). No bloquean Fase 1 si el primer caso de
validación es uno con OCR ya hecho y con ID GO formal.

**[SIGUIENTE-CUMPLIMIENTO-RIA-RGPD]** (sesión 12, 2026-05-12) Plan de
adecuación de FeesDefender al Reglamento (UE) 2024/1689 (RIA) y al
Reglamento (UE) 2016/679 (RGPD) redactado y entregado como
`Plan adecuacion FeesDefender - RIA RGPD.docx` en la raíz del proyecto.
26 pp., formato del despacho, dos partes: memorando ejecutivo (calificación
del sistema bajo RIA — no alto riesgo, sí transparencia art. 50 y
alfabetización art. 4 — roles RGPD, GAP, hoja de ruta) y documentación
base (RAT, matriz obligaciones, EIPD, cláusulas arts. 13/14/28,
política de gobernanza IA, secreto profesional). Conclusión: FeesDefender
no es sistema de alto riesgo, pero requiere adecuación formal en cuatro
fases con calendario alineado a la aplicación escalonada del RIA
(02/02/2025, 02/08/2025, 02/08/2026, 02/08/2027). Acciones del usuario
(Fase 0, fuera del repo): firma DPA Anthropic, verificación DPF, opt-out
de entrenamiento. **Implementación técnica pendiente en sesión dedicada**:
(1) crear `docs/CUMPLIMIENTO.md` como checklist vivo de la matriz del
Anexo B; (2) ampliar `core/intake_log.py` con eventos de cumplimiento
(`dpa_renewed`, `formacion_realizada`, `eipd_revisada`, `brecha_detectada`,
`prompt_modificado`, `anon_bypass` con justificación obligatoria);
(3) banner permanente en UI Streamlit con aviso art. 50.4 RIA + recordatorio
de anonimización obligatoria; (4) metadato XMP "Generated-By: FeesDefender —
Tyukhay Legal" en todos los `.docx` generados (art. 50.2 RIA); (5)
`scripts/cumplimiento_check.py` semanal vía Task Scheduler (DPA vigente,
formación dentro del año, smoke anonimizador, ACTORES_DESPACHO consistente,
sesiones CRM sanas) con output `cumplimiento_<fecha>.md`; (6) mover el
`.docx` del plan a `docs/cumplimiento/Plan_Adecuacion_v1.docx` para
trazabilidad por commits. Detalle completo en memoria
`project_cumplimiento_ria_rgpd.md`.

---

### ⚠️ MÁXIMA PRIORIDAD — abrir próxima sesión por aquí

~~**[SIGUIENTE-ORGANIZADOR-UI]**~~ ✅ 2026-05-30 (sesión 28) — Botón "🤖 Organizar localmente" entregado: expander en la pestaña «Casos» con flujo Proponer→Aplicar, semáforo de precondiciones (`core.local_organizer.estado_precondiciones`), métricas, disclaimer PII y `help=` en todos los controles. +5 tests. Smoke manual de UI pendiente (no automatizable). **[SIGUIENTE]** real ahora: `[SIGUIENTE-ORGANIZADOR-VALIDACION]` — validar el organizador end-to-end sobre el piloto BaRS1 (`python -m scripts.organizar_local "BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta" --plan` → revisar `07_AI cowork/_plan_reorganizacion.md` → `--execute`), o usar ya el botón nuevo desde la app.

Alcance (referencia histórica del diseño, ya implementado):
- **Ubicación**: página del caso, sección de análisis/intake.
- **Validaciones previas** (deshabilitar el botón si fallan, con mensaje claro):
  - Caso pulled: `00_Input/01_Drive EV/` con documentos.
  - `06_Anonimizado/` poblado (si no, enlazar a "Anonimizar" primero).
  - `core.llm_local.health_check()` True. Si Ollama está down, mostrar aviso accionable (`ollama serve` + `ollama pull qwen2.5:14b-instruct-q4_K_M`) y deshabilitar.
- **Flujo en 2 pasos** (refleja el CLI `--plan` → `--execute`):
  1. "Proponer" → `local_organizer.planificar(case_id)`. Spinner por fase. Resumen: nº docs, % alta confianza (≥0.80), pendientes, confianza media. Enlace para abrir `07_AI cowork/_plan_reorganizacion.md` (revisión humana editable).
  2. "Aplicar" → `local_organizer.ejecutar_plan(case_id)`. Resumen de acciones (COPY/MOVED/SKIP_UNCHANGED), correcciones registradas, enlace `computer://` para abrir `00_Input/01_Drive EV/_organizado/`.
- **Disclaimer fijo**: la vista `_organizado/` contiene PII (copias de originales) — material interno, no compartir con externos.
- **Coste**: 0 (LLM local). No mostrar estimación de coste API.
- **Regla del proyecto**: todo control Streamlit lleva `help=` con descripción del comportamiento (feedback_ui_tooltips).
- **Tests**: smoke test de que el handler invoca `planificar`/`ejecutar_plan` con el `case_id` correcto (mock del core).

Referencia: handoff de Cowork "organizador local con Ollama" Fase 5 (UI) + memoria `project_organizador_local_ollama.md`. Modos avanzados del CLI (`--refresh/--rebuild/--renumerar`) pueden quedar fuera del MVP del botón.

**[SIGUIENTE-SUBDIVISION-CIUDADES]** (plan trazado el 2026-05-12 s14; Fase 0 cerrada el 2026-05-12 s16)

Subdivisión de `CASOS_ROOT` por ciudades. Plan en
`docs/PLAN_SUBDIVISION_CIUDADES.md`. 11 decisiones cerradas, 7 fases.

**Fase 0 cerrada (s16)** — commit en rama `feature/subdivision-ciudades`:

- `core/ciudades.py` creado con `CIUDADES`,
  `TAG_AZUL_CIUDAD_EXTRAJUDICIAL/_JUDICIAL`,
  `EQUIPOS_POR_CIUDAD_EXTRAJUDICIAL/_JUDICIAL`,
  `EQUIPOS_EXTRAJUDICIAL/_JUDICIAL`, `ciudad_de_equipo(codigo)`,
  `es_carpeta_de_sistema(nombre)`.
- Decisión técnica: ubicación final `core/ciudades.py` (no
  `core/config/ciudades.py` como decía el plan original) para evitar
  refactor del paquete `core.config` fuera de scope. Plan actualizado.
- `streamlit_app.py`: definiciones locales L842-1036 sustituidas por
  imports (~200 líneas eliminadas; cero cambios funcionales).
- `tests/test_config_ciudades.py`: 13 funciones (36 casos
  parametrizados) — catálogo canónico, mappings por contexto,
  derivación código→ciudad para los 6 casos vivos + 3 ciudades de
  muestreo + 4 códigos asimétricos extra-only/judicial-only,
  coherencia cross-context, regla guion bajo. Suite global 519/519 ✓.

**Próxima sesión — arrancar Fase 1**:

`core/casos/case_locator.py` con tolerancia legacy + refactor masivo
de call-sites en `core/case_manager.py`, `core/sync_sudespacho.py`,
`scripts/init_caso.py`, `scripts/sync_sudespacho.py`,
`scripts/bulk_pull_expedientes.py`, `scripts/scheduled_sync.py`,
`tests/conftest.py`. Fase 1 es la pesada (estimado: 2 sesiones
cowork). Detalle en §5 del plan.

Pre-condición antes de Fase 4 (migración real): backup manual de
`CASOS_ROOT` (snapshot Drive o `rclone copy` a ubicación fría).

**Paralelo pendiente:** [SIGUIENTE-SaRS1-PIPELINE] H6 sigue abierto
(subida manual al CRM gdocu del expediente 659 + entrega a Claude
frontier). Si bloqueado por bug `presigned_download_url` o por la
agenda del usuario, dar prioridad a la subdivisión.

---

**[SIGUIENTE-SaRS1-PIPELINE]** (plan trazado el 2026-05-12)

Desarrollo multi-hilo del procesamiento documental del caso SaRS1
(Castelar 37-39, Santander) + inauguración del primer fixture
gold-standard de anonimización. **7 hilos planificados**, cada uno
autocontenido (contexto, pre-condiciones, comandos, criterios de
aceptación, entregables) en `docs/PLAN_SaRS1_anon_pipeline.md`.

Ruta crítica: H1 → H2 → H4 → H5 → H6 → H7. H3 (adaptación de
`core/anon/deanonimizar.py` al `_mapa_caso.json`) es paralelizable.

**H1-H5 + H5b cerrados el 2026-05-12. H6 pasos 6.1 y 6.2 cerrados; paso 6.3 pendiente.**

- **H1**: `_caso.md` corregido (cliente E&V Spain ID 27 + observación DEMANDADO en
  `meta.observaciones`). `verify_expediente_referencia` → `match: True`. OCR `spa`
  aplicado a los 2 PDFs (35 pp + 39 pp) vía `python -m ocrmypdf` por bug latente en
  wrapper `core/anon/ocr.py` (documentado en `docs/MEJORAS_FUTURAS.md §11`). Output
  en `00_Input/04_Manual/_ocr/`. Originales intactos. Señales OCR para H5 anotadas
  en tabla §14 del plan.
- **H2** (commit `3e759e3`): split automático insuficiente (2 piezas vs 4 lógicas;
  el OCR transcribió "CÉDULA DE EMPLAZAMIENTO" como `"_ 1 Sección Civil..."` y la
  regla `TIPOS_SUPER_ABSORBENTES` absorbió cédula+decreto bajo DEMANDA; PDF2 sin
  marcadores cayó al fallback `DOCUMENTO`). Troceo manual con `pypdf` (script ad-hoc
  temporal en `%TEMP%`, no versionado): PDF1 → `01_CEDULA_EMPLAZAMIENTO_01.pdf`
  (pp 1-2) + `02_DECRETO_01.pdf` (pp 3-5) + `03_DEMANDA_01.pdf` (pp 6-35); PDF2 →
  `01_DOC_ANEXO_01.pdf` (pp 1-39) como bloque único (OCR muy degradado en pp 1-20;
  troceo por DOC numerado descartado por riesgo de cortes mal puestos; calidad del
  output anonimizado no afectada por mapa compartido). Output en
  `00_Input/04_Manual/_split/Demanda_Std_{1,2}_ocr/`. Sanity 74/74 OK. Esqueleto
  `07_AI cowork/_revision_anon_SaRS1.md` creado con plantilla Anexo A + bitácora
  del split + 2 incidencias categoría SPLIT documentadas para H5.
- **H3** (commit `d22febd`): `core/anon/deanonimizar.py::_localizar_mapa` extendida
  a 4 niveles (legacy adyacente, legacy `_para_IA`, mapa de caso
  `06_Anonimizado/_mapa_caso.json`, fallback frontmatter `mapa_caso_path`/
  `mapa_entidades`). Firma pública y CLI intactas. 13 tests dedicados
  (`tests/test_deanonimizar_mapa_caso.py`) verdes; suite global verde
  (~483 tests). `docs/ARQUITECTURA.md` actualizada con 2 filas de dependencias.
  Sin tocar regex/listas/thresholds del motor.
- **H4** (sin commit; H4 no toca código del proyecto): **Opción B** del plan
  (Opción A inviable: `_listar_documentos` en `core/anon/api.py` L318-334 ignora
  cualquier path con parte que empiece por `_`, incluido `_split/`). Script ad-hoc
  en `%TEMP%\h4_sars1_anon.py` (no versionado, mismo patrón que el troceo manual
  de H2) que replica `anonimizar_caso` con listado explícito de las 4 piezas de
  `_split/` y mapa compartido. **4/4 procesados, 0 errores, ~5 min**. Output en
  `06_Anonimizado/{01_cedula_emplazamiento_01,02_decreto_01,03_demanda_01,01_doc_anexo_01}.md`
  + `_mapa_caso.json`. Entidades nuevas: cédula 13, decreto 10, demanda 35, anexo 126.
  **Side-fix documentado**: destapado segundo bug latente — `core/utils.py::_CASE_ID_NEW`
  exige `(W-XXXXXX)` y rechaza `(SIN REFERENCIA)` (categoría OTROS introducida en s9).
  Workaround H4: monkey-patch local en el script ad-hoc. Bug registrado como punto 12
  en `docs/MEJORAS_FUTURAS.md` para hilo dedicado. 7 notas sueltas categorizadas
  (1 MAP, 4 FP, 1 OCR, 1 FP regex) anotadas en `07_AI cowork/_revision_anon_SaRS1.md`
  como input retroactivo para H5.
- **H5** (sin commit pendiente al cierre de la sesión 13 hasta que el usuario
  ejecute los dos scripts ad-hoc y confirme tests verdes): tabla forense
  completa con 63 filas (8 FN bloqueantes, 38 FP, 8 MAP, 2 SPLIT, 2 OCR);
  3 decisiones fijadas (D-H5-1 fixture local-only en `.gitignore` opción a,
  D-H5-2 camino quirúrgico vía script auxiliar Python, D-H5-3 OCR PDF2 pp 1-20
  marcado no recuperable + alta prioridad en MEJORAS_FUTURAS); script
  `_h5_sars1_corregir_mapa.py` (mapa reconstruido 155→~50 etiquetas + 4 .md
  corregidos + log); fixture `tests/fixtures/anon/SaRS1/` con input + expected
  (snapshot motor pre-H5) + expected_corregido (post-H5 docu) + REVISION.md;
  `tests/test_anon_regresion_SaRS1.py` con skip colectivo si fixture ausente;
  10 entradas nuevas en `MEJORAS_FUTURAS.md` (puntos 13-22) cubriendo FN/FP/
  MAP/OCR + refactor de `anonimizar_caso`; `.gitignore` con regla
  `tests/fixtures/anon/`.

- **H5b** (sin commit pendiente — vive en el caso, ignorado por git): sub-hilo
  abierto durante H6 por insuficiencia detectada en sanity de PII previo a
  exposición al frontier (37 hits residuales). Script
  `07_AI cowork/_h5b_sars1_cobertura_completa.py` aplica delta sobre H5:
  ampliación mapa (+5 entidades incluyendo categoría URL nueva
  `[URL]`/`[URL_2]`), 16 reglas FN_RULES_H5B (operan solo sobre body,
  conservan frontmatter del motor para H7), regeneración de
  `08_Para frontier/` con frontmatter neutralizado. 35 sustituciones FN
  automáticas + 1 parche puntual (línea 708 DEM, regla no contemplaba `**`
  Markdown entre separador y "VÓLKERS"). 2 propietarias nuevas detectadas
  (Adelaida Gómez Sainz, Mercedes Pita Wonenburger) que H5 había pasado
  por alto por compartir primer nombre con personajes ya etiquetados.
  Sanity final: 0 hits PII (excluyendo "Pedro San Martín" FP intencional
  documentado). 169 etiquetas totales en `08_Para frontier/` (+68 vs H5).
- **H6 paso 6.1** (cerrado 2026-05-12 17:37): 4 piezas split (cédula 2pp +
  decreto 3pp + demanda 30pp + anexos 39pp) subidas al gdocu del expediente
  judicial 659, todas en rama raíz `General/` (decisión opción b: solo
  piezas split, sin OCR completos ni originales sin OCR; descarte de
  duplicados). Documentos pre-existentes en gdocu (no parte de H6):
  `ESCR PROCU-PERSONAMIENTO.pdf` (16:47) + `JUSTIF APUD-ACTA.PDF` (16:48).
- **H6 paso 6.2** (cerrado): prompt frontier redactado en
  `07_AI cowork/_prompt_frontier_H6.md`. Estructura procesal Sala 1ª TS +
  reglas anti-alucinación con placeholders explícitos
  `[CITAR JURISPRUDENCIA SOBRE: ...]` y `[VERIFICAR EN EXPEDIENTE: ...]`.
- **Reorganización del expediente SaRS1** durante H6: `08_Borradores/`
  renombrada a `09_Borradores/` (output frontier + deanonimizados); nueva
  `08_Para frontier/` como drop zone canónica de input al LLM externo (4 .md
  anonimizados copiados de `06_Anonimizado/` SIN frontmatter del motor +
  `_PROMPT.md` + `README.md` con contrato de la carpeta). Por decisión del
  plan §9.3 ninguna de las dos se cabla en
  `core/config.py::INPUT_SUBDIRS`.

Próximo paso a abrir: **H6 paso 6.3** (entrega al frontier + recepción
borrador). Operativa: pegar `08_Para frontier/_PROMPT.md` en conversación
nueva de Claude.ai web o app/Cowork con perfil distinto del repo
FeesDefender (acceso de carpeta solo a `08_Para frontier/`), adjuntar
4 .md, recibir borrador → guardar como
`09_Borradores/contestacion_demanda_SaRS1_v1_anonimizado.md`. Estimación
30-90 min según iteraciones con el modelo.

Cada hilo es una sesión nueva de Cowork con ventana de contexto
limpia: leer `STATUS.md` + sección H<N> de `docs/PLAN_SaRS1_anon_pipeline.md`.

---

**[SIGUIENTE-INTAKE-V2-SMOKE-UI]** (sesión 7 cerró el paso 8 el 2026-05-11)

Pasos 1-8 implementados. 113 tests v2 dedicados verdes (ver "Última
actualización" arriba). Queda solo el **smoke manual de la UI Streamlit**
(no automatizable sin navegador) + el commit final (paso 9).

**Smoke manual UI — abrir Streamlit y verificar:**
1. Sidebar — aparece "¿Quién eres?" arriba; default = "Nikolai Tyukhay" si
   `os.getlogin()` no matchea; al cambiar, los eventos del log reflejan el
   actor seleccionado.
2. Tab Casos → "📂 Subir al árbol CRM" — selectores encadenados llegan a
   ramas profundas (Civil → 1ª Instancia → Declarativo → Demanda); el
   uploader guarda en disco bajo `00_Input/05_CRM/<rama>/`; el log JSONL
   recibe `upload_manual` con `actor + destination + filename + size_bytes`.
3. Tab Nuevo caso → crear caso ficticio con tipo NEGATIVA_OFERTA + dirección
   + ID GO: tras crear, `02_Analisis/_ficha_operacion.xlsx` tiene REF y FECHA
   pre-rellenadas, `02_Analisis/_cuestionario_viabilidad.xlsx` está presente,
   y `_caso.md.meta` contiene `tipo_caso`, `direccion`, `id_go`.

Investigación pendiente NO bloqueante: query correcta del endpoint
`/api/folders/gdocu/...` (ver `docs/DEAD_ENDS.md`). Si se descubre, migrar
`CARPETA_ID_TO_PATH` hardcodeado a auto-construcción dinámica.

---

**[CRITICO-PRESIGNED-DOWNLOAD-BUG]** (detectado 2026-05-11 s8, durante pull v2 del expediente 649 de BaRR3)

El endpoint REST `GET /api/files/presigned_download_url/{doc_id}` devuelve
**HTTP 400** para todos los documentos del expediente 649 (26/26 fallos
consecutivos) con body:

```
{"@context":"/api/contexts/Error","@type":"hydra:Error",
 "hydra:title":"An error occurred",
 "hydra:description":"Unable to generate an IRI for \"App\\Upload\\Infrastructure\\ApiPlatform\\DTO\\Download\""
```

Es un error del framework API Platform en el backend PHP (no autenticación,
no parseo del cliente — el listado `gdocu` funciona perfectamente y
devuelve los 26 documentos con metadatos). Confirmado **operativo el 2026-05-04**
en `reference_sudespacho_api.md` y STATUS sesión 2026-05-04 (*"REST elimina
PHPSESSID para docs: `/api/element_registries/gdocu` + `/api/files/presigned_download_url/{doc_id}` confirmados sin PHPSESSID"*).
Confirmado **roto el 2026-05-11**.

**Consecuencia:** ningún caso puede completar pull v2 hasta que se resuelva.
BaRR3 ha quedado vinculado al expediente correcto 649 pero sin docs locales.

**Trabajo a hacer en próxima sesión (NUEVO HILO):**

1. **Capturar HAR de la SPA descargando un doc del expediente 649** desde
   sudespacho.net manualmente (Chrome DevTools → Network → click sobre un
   doc del gestor documental → guardar HAR). El usuario sí puede descargar
   desde la web — la SPA usa ruta distinta o auth diferente.
2. **Comparar payload con `download_document_rest`** en `core/sync_sudespacho.py`.
3. **Si la ruta REST ha cambiado** (renombrado/reorganización del módulo
   Upload del backend), actualizar el endpoint en `download_document_rest`.
4. **Si la SPA usa frontal legacy PHP** para descargar (`/views/gdocu/...`),
   implementar fallback en `pull_expediente_v2` con PHPSESSID (re-introducir
   la dependencia que habíamos eliminado el 2026-05-04 para listar+descargar,
   manteniendo la auth REST para crear/vincular).

**Workaround inmediato** mientras no se resuelve: el usuario puede descargar
los docs manualmente desde la SPA y subirlos al árbol `00_Input/05_CRM/<rama>/`
usando el expander "📂 Subir al árbol CRM" del tab Casos de Streamlit (paso
7b del refactor intake v2).

Detalle completo en `docs/DEAD_ENDS.md` → "GET /api/files/presigned_download_url/{doc_id}".

---

**[CRITICO-INTAKE-EXPEDIENTE-INCORRECTO]** ✅ Cerrado 2026-05-11 s8.

- Causa raíz identificada: el ID 648 era un expediente real de **BaRR1**
  (Collserola 53 Bis, BD), usado el 2026-04-26 como cobaya para capturar
  HARs de los endpoints judiciales (`judicial_648.har`,
  `INTEGRACION_SUDESPACHO.md` línea 870). El pull se ejecutó contra el
  case_id local BaRR3; los 5 docs de BaRR1 contaminaron `sudespacho_648/`.
  No es bug runtime — es contaminación por testing manual durante el
  desarrollo del flujo de pull.
- Limpieza: `BaRR3/00_Input/sudespacho_648/` borrada; entrada 648 eliminada
  del frontmatter (`scripts/remove_expediente_link.py`, atomic write);
  expediente correcto 649 vinculado y validado.
- Auditoría preventiva sobre los 4 casos del repo destapó además: MaRS15
  con 4 IDs fantasma (653-656, no existen en CRM, probable residuo de
  intentos fallidos en sesión 2026-05-06 — limpiados) y MaRS2 con drift
  tipográfico en `referencia_cliente` (resuelto editando el CRM
  manualmente + sincronizando `meta.referencia_crm` local). Auditoría
  final: **0/4 mismatches**.
- Validación preventiva implementada: `verify_expediente_referencia`
  consulta el CRM tras `register_expediente` y avisa si el case_id local
  no coincide con `referencia_cliente`. Wireada en UI (Streamlit) y CLI
  (sync_sudespacho pull). 15 tests verdes. Documentación en commit
  `3fa7e23` (main).

---

**[SIGUIENTE-BITACORA]** (plan trazado el 2026-05-21 s24)

Bitácora razonada por caso. Cada sesión de trabajo con LLM sobre un
caso produce un resumen estructurado (qué hicimos, decisiones tomadas,
dudas pendientes, documentos generados) que se anexa a un único
`BITACORA.md` en la raíz del caso. No archiva el chat crudo — solo el
proceso de razonamiento, que es donde está el valor.

Plan completo en `docs/PLAN_BITACORA_CASOS.md`. 10 decisiones cerradas,
6 fases (3 en ruta crítica, ~3 sesiones cowork estimadas).

**Arrancar por F1**: módulo `core/bitacora/` aislado (fachada
`generar_entrada(case_id, transcripcion) -> Path`, prompt Haiku
fijo, atomic write con append en cabeza, tests dedicados con mock
de la llamada al modelo). F2-F4 (extractor Cowork + slash command +
hook al `/cierre`) van después.

**Pre-condición F2**: investigación previa sobre el formato JSON
de sesiones Cowork y cómo identificar la sesión activa (2-4 h sobre
3-5 sesiones reales recientes).

**Fuera de alcance del plan — apunte para el futuro**: red de seguridad
opcional consistente en tarea programada que zipea
`%APPDATA%\Claude\local-agent-mode-sessions\` a una carpeta gitignored
fuera del proyecto. Anotada en §9 del plan. No es parte del MVP de la
bitácora.

---


1. ~~Capturar POST creación expediente extrajudicial~~ ✅ 2026-04-28
2. ~~Mapear IDs de tags CRM~~ ✅ 2026-04-28 — 87 tags, `sudespacho_create.py`
3. ~~Añadir `tag_defaults_for_tipo_caso()` y 13 `NOTA_*`~~ ✅ 2026-04-28
4. ~~Crear protocolo de sesión: `session_close.py`, `DEAD_ENDS.md`, mapa dependencias~~ ✅ 2026-04-28
5. ~~Protocolo de cierre definitivo: 4 momentos, session_close.py simplificado, sin interactividad~~ ✅ 2026-04-28
6. ~~Limpiar `sudespacho/` residual y ejecutar pipeline end-to-end en caso real~~ ✅ 2026-04-28 — 9/9 pasos OK, ~9 min.
7. ~~`core/sudespacho_relations.py` — deduplicación, link cliente (EV MMC), link/create colaborador~~ ✅ 2026-04-29 — 25 tests, endpoint saveselect confirmado en producción.
8. ~~Integrar `link_ev_mmc` + `ensure_colaborador_vinculado` en UI Streamlit pestaña "Nuevo Caso"~~ ✅ 2026-04-29 — nombres derivados automáticamente de emails; colaboradores vinculados tras crear expediente.
9. ~~Módulo `core/intake_drive.py` + integración UI~~ ✅ 2026-04-29 — pull Drive E&V en tab Nuevo caso y tab Casos; auto-resolución Shared Drive ID; 27 tests.
10. ~~Tooltips `help=` en toda la UI~~ ✅ 2026-04-29 — todos los campos interactivos cubiertos; ruta eliminada del listado de casos.
11. ~~**[NUEVO-HILO-EMAIL]**~~ ✅ 2026-05-04 — Renovación JWT implementada; sidebar session_state fix; botón 🔍 implementado. Test end-to-end pendiente hasta resolver PHPSESSID.
2. ~~**[NUEVO-HILO-AUDITORIA]**~~ ✅ 2026-05-04 — REST elimina PHPSESSID para docs: `/api/element_registries/gdocu` + `/api/files/presigned_download_url/{doc_id}` confirmados sin PHPSESSID. Auth legacy ahora requiere 3 cookies. SPA login NO crea PHPSESSID. Docs actualizados. Verificación 🔍 pendiente ([TAREA-3]).
3. ~~**[SIGUIENTE-B]**~~ ✅ 2026-05-06 — Colaborador de prueba ID=777 ("TEST FEESDEFENDER BORRAR") borrado manualmente del CRM tnm.sudespacho.net.
12. **[SIGUIENTE-UI]** Declarar dependencias en `pyproject.toml` (ya existe `run_app.bat`).
13. ~~**[SIGUIENTE-J-TAGS]**~~ ✅ 2026-05-04 — Tags ciudad (IDs 297-303) y equipos faltantes (304-313) creados manualmente en CRM + constantes añadidas a `sudespacho_create.py`.
14. ~~**[SIGUIENTE-J-TEAMS]**~~ ✅ 2026-05-04 — Ver punto anterior.
15. ~~**[SIGUIENTE-J-UI]**~~ ✅ 2026-05-04 — Toggle Extrajudicial/Judicial en `streamlit_app.py`: radio, `_J_EQUIPOS_POR_CIUDAD`, `_J_CIUDADES`, § 3b con NIG + tipo procedimiento, handler bifurcado llamando a `create_expediente_judicial()`.
16. ~~**[SIGUIENTE]** Auditar creación expediente en SPA~~ ✅ 2026-05-06 — Confirmado REST+JWT sin PHPSESSID. `create_expediente()` y `create_expediente_judicial()` migrados a REST-first. Tests en `test_sudespacho_create_rest.py`.
17. ~~**[SIGUIENTE-B-COLAB]**~~ ✅ 2026-05-04 — botón 🔍 end-to-end verificado.
18. **[SIGUIENTE-SHARE]** Probar compartición directa carpeta E&V: tab Casos → expander "Compartir carpeta E&V" → botón "⚡ Compartir directamente". Si falla por token expirado, ejecutar `rclone ls gdrive_ev:` para refrescarlo.
16. ~~**[SIGUIENTE-J-TESTS]**~~ ✅ 2026-05-06 — `test_sudespacho_create_rest.py` cubre REST extrajudicial + judicial (payloads, tags, REST-first + fallback).
17. ~~**[SIGUIENTE]** Ejecutar `pytest -q`~~ ✅ 2026-05-06 — 178/178 en verde.
18. ~~**[SIGUIENTE-REST-RELATIONS]**~~ ✅ 2026-05-06 — ver arriba.
19. ~~**[SIGUIENTE]**~~ ✅ 2026-05-06 — Caso MaRS15 local creado (idempotente); URL Drive guardada en `_caso.md`; CRM falló por JWT expirado; pull rclone falló por token `gdrive_ev` caducado. Checks de existencia (carpeta + expediente CRM) implementados en UI. Pendiente completar CRM + pull tras renovar sesión.
20. ~~**[SIGUIENTE]** Renovación automática JWT...~~ ✅ 2026-05-06 — `_try_refresh_jwt_post` + retry loop 401 implementados en create y relations. Cuando `@refreshToken` también expira: instrucción manual clara en UI. Confirmado: no existe endpoint login programático en REST API (ver DEAD_ENDS.md).
21. ~~**[SIGUIENTE]** Completar MaRS15: renovar sesión CRM~~  ✅ 2026-05-06 — Expediente judicial creado; EV MMC + 2 colaboradores vinculados. Pendiente: vincular `juanluis.garcia@engelvoelkers.com` manualmente en CRM + pull rclone gdrive_ev.
22. ~~**[SIGUIENTE]** Migrar creación de colaboradores a REST~~ ✅ 2026-05-06 — `POST /api/element_register/colaboradores` confirmado (HAR). `_rest_post_colaborador()` + REST-first en `create_colaborador()`. 10 tests nuevos. Flujo nuevo caso 100% independiente de PHPSESSID. Colaborador ID=780 pendiente borrar del CRM.
23. ~~**[SIGUIENTE]**~~ ✅ 2026-05-06 — x-api-key para escritura REST confirmada (Opción A). Migración completa. 221 tests.
24. ~~**[SIGUIENTE]**~~ ✅ 2026-05-06 — Verificación end-to-end sin JWT/PHPSESSID confirmada. Auto-fill extrajudicial corregido. 10 tags mapeados. Sidebar eliminado.
25. ~~**[SIGUIENTE]** Fix num_expediente=0 en judiciales~~ ✅ 2026-05-07 — `_get_next_num_expediente_judicial()` implementado; payload judicial usa correlativo real. 10 tests nuevos.
26. ~~**[SIGUIENTE]** Fix v2 num_expediente judicial~~ ✅ 2026-05-07 — Diagnóstico via `apiCrm` SPA: 3 bugs en la función (properties[], equal, totalItems). Fix aplicado + tests actualizados. ~222 tests.
27. ~~**[LIMPIEZA-CASOS-PRUEBA]**~~ ✅ 2026-05-08 — Borrados del Drive los dos expedientes de prueba: `MaRR2 - XXXX - (XXXX) - Bad debt` y `TEST-2026-001` (CRM ya saneado manualmente por el usuario antes de la sesión). Acción: `Remove-Item -Recurse -Force` sobre `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\<carpeta>`. Verificadas las 4 referencias en código (`streamlit_app.py`, `core/config.py`, `core/sudespacho_create.py`, `docs/INTEGRACION_SUDESPACHO.md`): todas son constantes del equipo CRM "Madrid Residential Rentals 2" y se conservan. `TEST-2026-001` no aparecía en ningún archivo del repositorio.
27. **[SIGUIENTE]** ⬅️ Verificar en CRM que el próximo expediente judicial desde UI tiene número correlativo correcto (≠0). Luego: testear caso EXTRAJUDICIAL desde UI: pegar URL Drive E&V → verificar auto-fill → crear en CRM → confirmar → borrar. Luego: pull rclone gdrive_ev para MaRS15 (ejecutar `rclone ls gdrive_ev:` primero). Luego: `[SIGUIENTE-SHARE]` probar compartición directa carpeta E&V.
18. ~~**[SIGUIENTE-REST-RELATIONS]**~~ ✅ 2026-05-06 — `POST /api/relation_element/` confirmado HTTP 201 con Bearer JWT. 6 `link_*` migradas a REST-first + fallback legacy. 12 tests nuevos. `.env` actualizado.
11. ~~**[NIKOLAI]** Conectar cuenta `nikolai.tyukhay@engelvoelkers.com` en Cowork~~ ✅ 2026-04-28 — rclone `gdrive_ev` configurado; Cowork no soporta multi-cuenta, rclone es la solución definitiva.
12. **[SIGUIENTE-C]** Módulo `core/intake_drive.py`:
   - Inputs: `case_id`, `drive_ev_team_id`, `drive_ev_folder_id` (extraído de URL W-XXXXXX)
   - Ejecuta: `rclone copy "gdrive_ev:" 00_INPUT/manual/ --drive-team-drive <team_id> --drive-root-folder-id <folder_id>`
   - Actualiza `_caso.md` con los IDs y marca `.pulled` en `00_INPUT/manual/`
   - Tests: `test_intake_drive.py` con mock de rclone
   - UI: campo "URL carpeta Drive E&V" en formulario Streamlit "Nuevo Caso" → extrae team_id + folder_id automáticamente
9. ~~**[Nuevo hilo]** Módulo `core/anonymizer.py` — integrar proyecto externo de anonimización.~~ ✅ 2026-05-07 — Absorbido como `core/anon/` (no `core/anonymizer.py`). 5 fases ejecutadas (0-4). Pendiente Fase 5: migración de casos antiguos de Expedientes Seguros (re-procesar vs copiar tal cual — decisión del usuario antes de empezar). Ver `docs/MEJORAS_FUTURAS.md` para los 10 puntos identificados durante la integración (no bloqueantes).
10. **[Nuevo hilo]** Subida output anonimizado al Drive tyukhay.legal.
11. ~~**[SIGUIENTE-ANON-FASE5]** Migración de los expedientes ya procesados en `G:\...\Expedientes Seguros\Expedientes\`.~~ ✅ Decisión 2026-05-07: los casos antiguos se borran, no se migran. La nueva fachada `core/anon/api.py` parte de cero. Borrado físico de `G:\...\Expedientes Seguros\` queda como acción manual del usuario.
12. **[SIGUIENTE-ANON-WARMUP]** Decidir si activar warmup proactivo de modelos NLP al arrancar Streamlit. Pendiente de uso real del flujo combinado FeesDefender + Anonimizador. Si la rutina típica del usuario incluye "abrir Streamlit y anonimizar casi siempre", activar el warmup en background (ahorra 20-40 s la primera vez). Si las sesiones Streamlit suelen ser para crear casos / gestionar CRM sin tocar el anonimizador, mantenerlo desactivado (cargar 1.5 GB de RAM por si acaso es desproporcionado). Implementación: 5 líneas al inicio de `streamlit_app.py` justo después de `st.set_page_config`, usando `threading.Thread(target=warmup_nlp, daemon=True).start()`. Decisión tomar tras observar varias sesiones reales en producción.
11. Configurar Windows Task Scheduler para `scheduled_sync.py` (diario 08:00).
12. Reforzar `prompts/viabilidad.md` con jurisprudencia sobre nexo causal.
13. Tests adicionales: `test_linker`, `test_scorer`, `test_pipeline`.
14. **[Evaluación]** Backend LLM: valorar sustitución de Ollama/llama3 por Claude API (Haiku) para análisis. Equipo tiene i7-1255U sin GPU discreta — inferencia local en CPU muy lenta. Alternativas: (a) modelo cuantizado `llama3:8b-instruct-q4_0`, (b) Claude Haiku vía API (mínimo coste por caso, sin carga local).

---

## Credenciales / variables de entorno críticas

- `SUDESPACHO_LEGACY_PHPSESSID` — caduca por inactividad del servidor PHP (~24 min). La SPA (`/tnm`) **no** renueva la sesión PHP. Para obtener PHPSESSID válido: necesita sesión PHP activa. Ver [NUEVO-HILO-AUDITORIA].
- `SUDESPACHO_LEGACY_JWT` — caduca en 1h. Renovación proactiva implementada (`_proactive_refresh_if_needed`). Renovación manual: sidebar Streamlit → 🔄 → pegar token de DevTools Console: `copy(localStorage.getItem('token'))`.
- `SUDESPACHO_LEGACY_REFRESH_TOKEN` — long-lived. Usar para renovar JWT antes de expiración.
- `SUDESPACHO_API_KEY` — API REST, estable.
- `SUDESPACHO_LEGACY_HOST` — `tnm.sudespacho.net` (fijo).
- `DRIVE_OUTPUT_FOLDER_ID` — carpeta Drive tyukhay.legal para output anonimizado (pendiente configurar).
- `DRIVE_EV_ROOT_FOLDER_ID` — carpeta raíz Drive engelvoelkers.com para intake E&V (pendiente cuenta corporativa).

---

## Estructura de carpetas (repo separado de Drive 2026-05-27)

```
C:\Users\tnm33\Dev\
└── FeesDefender\                  ← código FeesDefender (git → GitHub TyukhayNi/FeesDefender)
    ├── core/  scripts/  tests/  prompts/  docs/
    ├── streamlit_app.py
    └── .env                       ← local, nunca a GitHub

G:\Unidades compartidas\
└── EXPEDIENTES - TYUKHAY LEGAL\
    └── CASOS\                     ← expedientes reales (acceso equipo: Paola, Ana)
        ├── _PLANTILLA/
        └── {case_id}/

(Bitácora y planificación: PLAN.md + STATUS.md en el repo. Historial: git log.
 La carpeta Drive Proyectos\FeesDefender\ quedó archivada el 2026-05-29.)
```

**Variables de entorno afectadas:**
- `CASOS_ROOT=G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS` — ya actualizado en `.env`

**⚠️ Pendiente:** mover la carpeta `CASOS\` desde `DESPACHO - PRODUCCION\` al nuevo Shared Drive `EXPEDIENTES - TYUKHAY LEGAL\`:
```powershell
Move-Item "G:\Unidades compartidas\DESPACHO - PRODUCCION\CASOS" "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS"
```

---

## Arquitectura multi-expediente (implementada 2026-04-26)

- Una subcarpeta `sudespacho_{id}/` por expediente en `00_INPUT/`.
- Marcador `.pulled` JSON: `{doc_ids, last_sync, by_carpeta}`.
- 3 modos pull: skip (default) / incremental / force.
- `register_expediente(case_id, exp_id, element)` — registra en `_caso.md` frontmatter.
- `scheduled_sync.py` — itera todos los casos, pull incremental, log en `06_AI_COWORK/`.

---

## Estructura de carpetas de un caso (v2 — con anonimizado)

```
data/CASOS/{case_id}/
├── 00_INPUT/
│   ├── _caso.md
│   ├── sudespacho_{id}/      ← pull desde CRM
│   └── manual/               ← docs subidos manualmente / intake Drive
├── 01_PROCESADO/
├── 02_ANALISIS/
├── 03_DECISION/
├── 04_OUTPUT_PREDEMANDA/
├── 05_PROCEDIMIENTO/
├── 06_AI_COWORK/
├── 07_ANONIMIZADO/           ← Markdown sin PII → Drive tyukhay.legal → LLMs online
└── 90_NOTAS_PERSONALES/      ← zona del abogado, intocable
```

---

## Tests — última ejecución

```
pytest -q   →   verde / exit 0 (2026-05-30, sesión 28)
```
Sesión 28: `+5` tests en `test_local_organizer.py` (`estado_precondiciones`) → 16/16 en el módulo.
Módulos cubiertos: `case_manager`, `inventory`, `utils`,
`sync_sudespacho` (+26 nuevos: REST gdocu), `sync_sudespacho_legacy` (+8 nuevos: JWT refresh),
`sudespacho_relations` (+8 REST colaboradores, +12 REST relation_element, +2 retry 401),
`sudespacho_create` (+31 nuevos: REST extrajudicial + judicial, tags, payloads, REST-first fallback, +3 retry 401),
`intake_drive` (+5 nuevos: `get_drive_folder_info` token OK/sin token/API 401/rclone falla/nombre vacío).
