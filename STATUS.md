# STATUS — FeesDefender

> **Fuente de verdad única del proyecto.**
> Actualizar al cerrar cada sesión con `python -m scripts.session_close`.

**Última actualización:** 2026-05-12 (sesión 12) — **H2 del plan SaRS1 cerrado: split + troceo manual de los 2 PDFs OCR**. Commit `3e759e3`. El split automático de `core/anon/separar.py::separar_pdf_pipeline` generó solo **2 piezas** frente a las 4 lógicamente esperadas (cédula, decreto, demanda, anexos): PDF1 → 1 pieza DEMANDA pp 1-35 (con observación "pp 1-5 absorbidas por cuerpo de DEMANDA"); PDF2 → 1 pieza DOCUMENTO pp 1-39 ("sin marcadores detectados"). Causa raíz: (a) el OCR transcribió la cabecera "CÉDULA DE EMPLAZAMIENTO" del PDF1 pp 1 como `"_ 1 Sección Civil del Tribunal de Instancia de Santander..."` (subrayado + espacio reemplazando el título oficial), y la regla `CEDULA_EMPLAZAMIENTO` exige el marcador en las 3 primeras líneas como portada → no matcheó; (b) "DECRETO" en pp 3-5 aparece solo en texto corrido ("Así por este Decreto lo acuerdo, mando y firmo"), no como cabecera oficial; (c) `TIPOS_SUPER_ABSORBENTES` (`DEMANDA, SENTENCIA, CONTESTACION, OPOSICION`) absorbe las páginas previas al primer marcador detectado cuando ese marcador es un super-absorbente, lo que llevó a las pp 1-5 al cuerpo de DEMANDA; (d) en el PDF2 el OCR de pp 1-20 está muy fragmentado (texto invertido en muchas líneas, pp 20-21 saltadas según señales H1), de modo que los marcadores `DOC_ANEXO`/`DOC_EMAIL`/`DOC_PODER_NOTARIAL` no aparecen como portada limpia. **Troceo manual aplicado** con `pypdf.PdfWriter` (script ad-hoc temporal en `%TEMP%`, no versionado): PDF1 → `01_CEDULA_EMPLAZAMIENTO_01.pdf` (pp 1-2) + `02_DECRETO_01.pdf` (pp 3-5) + `03_DEMANDA_01.pdf` (pp 6-35); PDF2 → `01_DOC_ANEXO_01.pdf` (pp 1-39) como **bloque único** (decisión informada y confirmada por el usuario: trocear por DOC numerado sería frágil con OCR pp 1-20 ruidoso; la calidad del output anonimizado no se ve afectada porque el motor opera token a token y el mapa de entidades es compartido entre piezas). Output en `00_Input/04_Manual/_split/Demanda_Std_{1,2}_ocr/`, cada subcarpeta con su `indice.json` (campo `modo: "troceo_manual_H2"` + nota explicativa). Sanity check páginas 74/74 OK. 4 criterios §5.4 marcados. **Esqueleto `07_AI cowork/_revision_anon_SaRS1.md` creado** con plantilla Anexo A (metadatos del caso, sección H1 OCR, sección H2 split con bitácora, placeholder H4 anonimización, tabla forense vacía para H5, sección decisiones, sección resumen para `MEJORAS_FUTURAS.md`); 2 incidencias categoría SPLIT documentadas para retroalimentar H5. Ruta crítica del plan ahora puede saltar directamente a **H4** (H3 ya estaba cerrado en sesión 11). Caso vive en `data/CASOS/` (`.gitignore`) — el split y el fichero de revisión no se versionan; solo se actualiza `docs/PLAN_SaRS1_anon_pipeline.md §14` (trazabilidad).

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
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
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
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
python -m scripts.session_close
# Si los tests pasan:
git add -A
git commit -m "<mensaje que Claude propuso>"
```

---

## Estado general

| Ítem | Estado |
|------|--------|
| Tests | ✅ 483/483 (Anonimizador absorbido: +51 — 2026-05-07; sufijo captador Drive: +2 — 2026-05-11 s4; Numero_Expediente extrajudicial: +10 — 2026-05-11 s6; tests v2 dedicados paso 8: +113 — 2026-05-11 s7; rename informe_viabilidad: +9 — 2026-05-11 s7; verify_expediente_referencia: +15 — 2026-05-11 s8; categoría OTROS + clientes propios: +22 — 2026-05-11 s9; deanonimizar `_mapa_caso.json` 4 niveles: +13 — 2026-05-12 s11) |
| SaRS1 — H2 split + troceo manual | ✅ 2026-05-12 s12 — split automático generó 2 piezas vs 4 lógicas (cédula+decreto absorbidos por DEMANDA; PDF2 sin marcadores); troceo manual `pypdf` → 4 piezas (`01_CEDULA_EMPLAZAMIENTO_01.pdf` + `02_DECRETO_01.pdf` + `03_DEMANDA_01.pdf` + `01_DOC_ANEXO_01.pdf`); sanity 74/74; `07_AI cowork/_revision_anon_SaRS1.md` con 2 incidencias SPLIT para H5 |
| `core/anon/deanonimizar.py` _localizar_mapa 4 niveles | ✅ 2026-05-12 s11 — legacy adyacente + `_para_IA` + `06_Anonimizado/_mapa_caso.json` + fallback frontmatter `mapa_caso_path`/`mapa_entidades`; firma pública y CLI intactas; +13 tests dedicados |
| URL Drive E&V opcional | ✅ 2026-05-11 s10 — campo ya no bloqueante en judicial ni extrajudicial; auto-fill + pull rclone condicionados a presencia |
| Categoría "Otros casos" | ✅ 2026-05-11 s9 — `TIPOS_CASO_OTROS` + `POSICION_OTROS`; sin tag verde de asunto ni tag lila de valoración por defecto |
| Clientes propios E&V | ✅ 2026-05-11 s9 — `CLIENTES_PROPIOS_EV` (EV_MMC_SPAIN=2, ENGEL_VOLKERS_SPAIN=27); `link_ev_mmc[_judicial]` parametrizado |
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

**[SIGUIENTE-DRIVE-TOKEN]** Renovación proactiva del access_token de
`gdrive_ev` en `core/intake_drive.py::_get_drive_access_token()`. Hoy lee
el `access_token` tal cual del JSON de `rclone.conf` sin comprobar el
campo `expiry`. Si pasa >1h sin que rclone ejecute ninguna operación, el
token está caducado y la Drive API devuelve 401 → el auto-fill falla en
silencio. Lo salva el keep-alive diario (`scheduled_sync._keepalive_gdrive_ev`),
pero un fin de semana largo o un Streamlit recién abierto tras inactividad
prolongada lo rompen. Fix: parsear `expiry` (ISO 8601 con offset), comparar
con `now()`, si vencido lanzar `rclone about gdrive_ev:` y releer.

**[SIGUIENTE-DRIVE-NAMING-AUDIT]** Auditar `DRIVE_EV_TEAM_IDS` por equipos
cuyas carpetas siguen un naming distinto del esperado. Hoy hemos visto que
`SeRS6` añade `- <consultor captador>` al final. Posible que otros equipos
usen prefijos numéricos (`393.` en Sevilla), abreviaturas distintas, o
naming sin guion antes del W-XXXXXX. Un script ad-hoc que liste las
primeras 5 carpetas de cada Shared Drive de `DRIVE_EV_TEAM_IDS` y aplique
`parse_ev_folder_name` revelaría falsos negativos antes de que aparezcan
en producción.

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

---

### ⚠️ MÁXIMA PRIORIDAD — abrir próxima sesión por aquí

**[SIGUIENTE-SaRS1-PIPELINE]** (plan trazado el 2026-05-12)

Desarrollo multi-hilo del procesamiento documental del caso SaRS1
(Castelar 37-39, Santander) + inauguración del primer fixture
gold-standard de anonimización. **7 hilos planificados**, cada uno
autocontenido (contexto, pre-condiciones, comandos, criterios de
aceptación, entregables) en `docs/PLAN_SaRS1_anon_pipeline.md`.

Ruta crítica: H1 → H2 → H4 → H5 → H6 → H7. H3 (adaptación de
`core/anon/deanonimizar.py` al `_mapa_caso.json`) es paralelizable.

**H1, H2, H3 y H4 cerrados el 2026-05-12.**

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

Próximo hilo a abrir: **H5** (verificación forense + creación del fixture
gold-standard `tests/fixtures/anon/SaRS1/`). Detalle completo en §8 del plan
maestro. Pre-condición: H4 cerrado ✓. Tiempo estimado: 45-90 min. Es el hilo más
manual del bucle de mejora continua — leer todo el output anonimizado, rellenar
la tabla del Anexo A categorizando errores (FN/FP/MAP/SPLIT/OCR), corregir
manualmente el `_mapa_caso.json` para los FP críticos (especialmente el bloque
N2 detectado en H4: muchas cabeceras jurídicas etiquetadas como nombres),
alimentar `docs/MEJORAS_FUTURAS.md` con las mejoras detectadas, y fijar el caso
como primer fixture gold-standard. Decisión inicial en H5 paso 5.1: política del
directorio `tests/fixtures/anon/SaRS1/` respecto a git (pendiente C1 del plan).

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

## Estructura de carpetas en Google Drive (reorganizada 2026-04-28)

```
G:\Unidades compartidas\
├── DESPACHO - PRODUCCION\
│   └── Base datos expedientes\    ← código FeesDefender (git → GitHub TyukhayNi/FeesDefender)
│       ├── core/  scripts/  tests/  prompts/  docs/
│       ├── streamlit_app.py
│       └── .env                   ← local, nunca a GitHub
│
└── EXPEDIENTES - TYUKHAY LEGAL\
    └── CASOS\                     ← expedientes reales (acceso equipo: Paola, Ana)
        ├── _PLANTILLA/
        └── {case_id}/
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
pytest -q   →   100% passed (2026-05-06, sesión 2)
```
Módulos cubiertos: `case_manager`, `inventory`, `utils`,
`sync_sudespacho` (+26 nuevos: REST gdocu), `sync_sudespacho_legacy` (+8 nuevos: JWT refresh),
`sudespacho_relations` (+8 REST colaboradores, +12 REST relation_element, +2 retry 401),
`sudespacho_create` (+31 nuevos: REST extrajudicial + judicial, tags, payloads, REST-first fallback, +3 retry 401),
`intake_drive` (+5 nuevos: `get_drive_folder_info` token OK/sin token/API 401/rclone falla/nombre vacío).
