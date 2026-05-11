# STATUS — FeesDefender

> **Fuente de verdad única del proyecto.**
> Actualizar al cerrar cada sesión con `python -m scripts.session_close`.

**Última actualización:** 2026-05-11 (sesión 4) — **Fix auto-fill Drive E&V para carpetas con sufijo captador.** Causa raíz: `_EV_FOLDER_RE` en `core/intake_drive.py` exigía `\s*$` después del `W-XXXXXX`, lo que rompía nombres con sufijo posterior como `393. Hacienda Vadillo - W-02RRO3 - Natalia Trujillano` (sufijo = nombre del consultor que captó la propiedad, NO del cliente — patrón habitual en los Shared Drives de E&V). El auto-fill resolvía correctamente ciudad y equipo desde `driveId` (`0ABSFVWC_PfdBUk9PVA` → `SeRS6`) pero devolvía `("", "")` para dirección + ID GO en silencio. Fix: regex relajado a `^(.*?)\s*[-–]\s*(W-[A-Z0-9]{5,8})\b` (sin `$`, con `\b` de límite de palabra) — descarta cualquier sufijo posterior. Tests +2 dedicados (`test_parse_folder_sufijo_consultor_captador`, `test_parse_folder_sufijo_con_guion_largo`) en verde. Diagnóstico reproducible con `scripts/diag_drive_autofill.py` (nuevo) — reproduce paso a paso la cadena auto-fill (parse_drive_url → rclone access_token → Drive API v3 → parse_ev_folder_name → lookup DRIVE_EV_TEAM_IDS) y señala dónde rompe. Memoria persistente nueva `reference_nomenclatura_carpetas_drive_ev.md` documenta el patrón real `<dir> - W-XXXXXX [- <captador>]` y la advertencia de no usar el sufijo como dato del cliente ni para auto-rellenar `nc_mail_captador`.

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
| Tests | ✅ ~289/289 (Anonimizador absorbido: +51 — 2026-05-07; sufijo captador Drive: +2 — 2026-05-11) |
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
**Expediente CRM REAL:** **649** (`expedientes_judiciales`) ← pendiente intake
**Expediente erróneamente vinculado:** 648 ← NO es Roser, es otro caso del CRM (a identificar y desvincular)
**Docs descargados:** 5 archivos, 5,35 MB ← contaminados con expediente 648, BORRAR

**⚠️ Acción pendiente antes de lanzar pipeline:**
```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
Remove-Item -Recurse -Force "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU\00_INPUT\sudespacho"
python -m scripts.run_pipeline "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
```

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

---

### ⚠️ MÁXIMA PRIORIDAD — abrir próxima sesión por aquí

**[SIGUIENTE-INTAKE-V2-PASO-7]** (sesión 3 cerró pasos 1-6 el 2026-05-08)

Pasos 1-6 implementados (ver "Última actualización" arriba). Quedan los
pasos 7, 8 y 9 del plan original. La planificación completa sigue en
memoria persistente `project_intake_estructura_v2.md`. Las decisiones
del paso 6 (plantillas) están en `project_plantillas_viabilidad.md`.

**Paso 7 — subdivisión 7a + 7b:**

**7a. `core/case_manager.ensure_case` — integración estructura v2 + plantillas:**

- Crear todas las ramas del `CRM_TREE` en `00_Input/05_CRM/` (D1 — eager).
  Recorrido recursivo del árbol anidado, `mkdir(exist_ok=True)` en cada nodo.
- Crear `00_Input/06_Entrevistas/` (vacía).
- Si `tipo_caso ∈ INFORME_VIABILIDAD_TIPOS` → copiar
  `data/_plantillas/cuestionario_viabilidad.xlsx` →
  `02_Analisis/_cuestionario_viabilidad.xlsx`.
- Siempre: copiar `data/_plantillas/ficha_operacion.xlsx` →
  `02_Analisis/_ficha_operacion.xlsx`.
- Pre-relleno mínimo al copiar (vía openpyxl):
  · `OPERACION!REF` ← `<equipo> - <direccion> (<id_go>)` parseado del case_id + meta.
  · `OPERACION!FECHA` ← fecha de creación.
  · Captador/buscador ← desde `_caso.md` cuando estén disponibles.
- Idempotencia estricta: si los archivos destino ya existen, NO sobrescribir.

**7b. `streamlit_app.py` — UI v2:**

- **Selector actor en sidebar (M10)**: radio o selectbox `[Nikolai, Paola, Ana, otros]`,
  persistente en `st.session_state["actor"]`. Llamada `intake_log.set_actor(...)`
  al inicio de cada request (después de `st.set_page_config`).
- **Expander "Subir documentos al árbol CRM"** en pestaña "Casos": selector
  jerárquico (selectbox encadenados) sobre `CRM_TREE`, file uploader con
  multiples files. Destino: `00_Input/05_CRM/<rama_seleccionada>/`. Cada upload
  emite evento `upload_manual` o equivalente al log M10.
- **Tooltips** (`help=`) en todos los campos nuevos.
- Decisión pendiente: ¿el botón actual de upload manual sigue apuntando solo a
  `04_Manual/` o se ofrece elección entre `04_Manual/` y árbol CRM?

**Después: paso 8 (tests v2) y paso 9 (commit + STATUS final).**

**Paso 8 — tests v2 dedicados:**

Tests pendientes en `tests/`:
- `test_crm_branch_path.py` — id_mapping, label_heuristic (única vs ambigua),
  fallback con expediente_id, normalización (mayúsculas/acentos).
- `test_pull_state_atomic.py` — schema D8 vacío→pulled, escritura atómica
  (simulación crash entre temp y replace), idempotencia, mutación de errors.
- `test_dedup_manifest.py` — register hash nuevo/duplicado, alias añadido,
  reconcile con primary perdido, manifest corrupto (recovery).
- `test_intake_log.py` — append + read, actor por defecto vs set_actor,
  rechazo de evento desconocido, fsync efectivo (smoke).
- `test_legacy_v1_detection.py` — detecta `sudespacho_*/`, ignora otras subdirs.
- `test_pull_expediente_v2.py` — flujo completo con cliente mockeado, bloqueo
  legacy, dedup, fallback `category_unknown`, integración con `update_pull_state`.
- `test_render_plantillas.py` — smoke: YAML válido → XLSX se genera sin error,
  hoja `_meta` con hash; `_StrictBoolLoader` no convierte `si`/`no` a bool.
- `test_ensure_case_v2.py` — crea árbol CRM, crea `06_Entrevistas/`, copia
  ficha siempre, copia cuestionario solo si tipo aplicable, idempotencia.

**Paso 9 — STATUS final + commit (Momento 4 del protocolo de cierre).**

Investigación pendiente NO bloqueante: query correcta del endpoint
`/api/folders/gdocu/...` (ver `docs/DEAD_ENDS.md`). Si se descubre, migrar
`CARPETA_ID_TO_PATH` hardcodeado a auto-construcción dinámica.

---

**[CRITICO-INTAKE-EXPEDIENTE-INCORRECTO]** (detectado 2026-05-07, fin de sesión)

El caso `BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU` tiene asociado en
`_caso.md` el expediente CRM **ID 648**, pero el ID real del caso Roser
en el CRM `tnm.sudespacho.net` es **649**. Los 5 documentos en
`00_Input/sudespacho_648/` NO pertenecen a Roser — pertenecen a otro
expediente.

Trabajo a hacer al inicio de próxima sesión:

1. **Identificar el expediente real con ID 648 en el CRM** — abrir
   `tnm.sudespacho.net` y consultar a qué cliente y referencia
   corresponde el ID 648. Documentar el resultado.
2. **Borrar `data/CASOS/BaRR3 - .../00_Input/sudespacho_648/`** — los
   documentos están contaminados (no son del caso). Limpiar también la
   entrada `sudespacho_expedientes` del frontmatter de `_caso.md`.
3. **Investigar la causa raíz**: ¿cómo se asoció 648 al caso Roser?
   Posibilidades a revisar:
   - El usuario tecleó el ID a mano al crear el caso (input incorrecto).
   - Había un mapeo automático `referencia → ID` que ha devuelto el
     siguiente disponible.
   - `find_expediente_judicial_by_referencia` en
     `core/sudespacho_relations.py` no filtró bien al buscar el ID.
4. **Hacer pull correcto del expediente 649** para Roser via
   `core/intake_drive.py` o `pull_expediente`. Verificar que los 5
   documentos descargados son los reales del caso.
5. **Auditar otros casos** del repositorio: ¿hay más casos con el ID CRM
   incorrecto? Script ad-hoc que recorra `data/CASOS/*/00_Input/_caso.md`
   y compruebe la coherencia `referencia ↔ ID` consultando el CRM.
6. **Si se confirma fallo en la lógica** del intake (no error humano),
   añadir validación: tras crear / vincular un expediente, leer
   `referencia` desde el CRM y compararla con la del caso local. Lanzar
   warning visible en UI si no coinciden.

Bloqueante para usar Anonimizador sobre BaRR3 — los .md anonimizados se
generarían sobre datos del expediente equivocado.

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
