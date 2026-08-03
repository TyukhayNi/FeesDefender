# STATUS — FeesDefender

> **Fuente de verdad única del proyecto.**
> Actualizar al cerrar cada sesión con `python -m scripts.session_close`.

> 🔴 **AVISO A TODO CLON / COWORK / OTRA MÁQUINA (2026-07-07):** el **historial de git fue reescrito** y el repo GitHub **recreado** (saneado de PII, Fase 2). Los SHAs cambiaron por completo y **no hay ancestro común** con el historial anterior → **`git pull`/`fetch` NO reconcilian**. **RE-CLONA desde cero** (`git clone https://github.com/TyukhayNi/FeesDefender.git`) y descarta cualquier copia previa. Nuevo `main` = `a40b27f` (o posterior). Borra este aviso cuando todos los clones estén regenerados.

## Bitácora de cierres → docs/bitacora/2026.md

El histórico de cierres de sesión se rota a `docs/bitacora/AAAA.md`. La última
sesión y el siguiente paso: **cola priorizada** en `PLAN.md` (fila #1). Detalle
fino: `git log`.

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

## ⚡ Protocolo de cierre de sesión → `docs/FLUJO_GIT.md`

El protocolo de cierre —y el flujo git completo (modelo, apertura, poda, recuperación)— vive
en `docs/FLUJO_GIT.md` §4. Ejecutable: `/cierre` (o `python -m scripts.session_close`).
Recordatorio clave: **`main` está protegida** → el cierre va por **rama → PR**, nunca commit
directo; el bloque de cierre va a `docs/bitacora/AAAA.md`, **no** a este fichero.

---

## Estado general

| Ítem | Estado |
|------|--------|
| Tests | ✅ **2.640 passed · 77 skipped · 7 xfailed** (2.724 recogidos) · 0 fallos, 0 errores — **medido el 2026-08-02** sobre `main` (`42d2b39`), 174 s. Los **7 `xfail`** son los defectos del frontal de la biblioteca reproducidos a propósito en la Fase 0 de la arquitectura dual; se arreglan en su Fase 2 (`PLAN.md` fila #3). Histórico por sesión: bitácora de cierres. *(Esta celda mantuvo «668/668» y un changelog de incrementos de mayo-junio hasta el 2026-08-02; el detalle de esos incrementos está en `git log`.)* |
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
| `docs/DEAD_ENDS.md` | ✅ **31 secciones / 57 entradas** (medido 2026-08-02; decía «8 callejones» desde mayo). Consultar **antes** de reintentar algo que falló raro |
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

## Taxonomía de casos → ver `core/config.py`

La taxonomía canónica de tipos de caso vive en `core/config.py`: `TIPOS_CASO_ACTORA` (Engel reclama) y `TIPOS_CASO_DEFENSIVA` (Engel demandado), cada entrada `clave_interna → (tag_crm, descripción)`, más el mapeo de posición procesal (`POSICION_ACTORA`/`DEFENSIVA`/`OTROS`). No se transcribe aquí para no duplicar la verdad: la prosa se desincroniza sola (esta tabla llegó a listar 3 tipos defensivos cuando el código ya tenía 4). Los documentos que sí espejan la taxonomía por necesidad (referencia CRM y skills LLM) están listados en el mapa de dependencias de `docs/ARQUITECTURA.md`.

---

## Primer caso real

**Case ID:** `BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU`
**Cliente:** EV MMC SPAIN, S.L.U.
**Expediente CRM REAL:** **649** (`expedientes_judiciales`) — referencia_cliente en CRM: `BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU   ` (con 3 espacios trailing del CRM; tolerados por `verify_expediente_referencia` vía `.strip()`).
**Estado intake (2026-05-11 s8):** vinculado y validado en `_caso.md`; árbol `00_Input/05_CRM/` creado; 26 documentos detectados en el gestor documental del CRM pero **download bloqueado** por bug del backend `presigned_download_url` (ver `[CRITICO-PRESIGNED-DOWNLOAD-BUG]` abajo y `docs/DEAD_ENDS.md`).
**Historial incidencia (cerrada):** el ID 648 estaba mal vinculado en `_caso.md` desde 2026-04-26. Causa raíz: 648 era un expediente **real de BaRR1** (Collserola 53 Bis, Bad Debt) usado como cobaya para capturar HARs de los endpoints judiciales; el pull se ejecutó contra el case_id local BaRR3 y los 5 docs de BaRR1 contaminaron `sudespacho_648/`. Limpiado 2026-05-11 s8 (carpeta borrada, frontmatter saneado).

---

## Próximas tareas → ver `PLAN.md`

La cola de trabajo **viva y priorizada** es `PLAN.md` (raíz del repo). STATUS.md ya no mantiene una cola propia: hacerlo duplicaba la verdad y provocó que un bug crítico viviera aquí sin estar en la cola de PLAN (`[CRITICO-PRESIGNED-DOWNLOAD-BUG]`, rescatado a mano el 2026-05-28).

El siguiente paso vive en la **cola priorizada** de PLAN.md (fila #1).

La cola histórica pre 2026-07 (sesiones 4–24) se archivó en `docs/bitacora/STATUS_cola_historica_pre_2026-07.md` (`estado: histórico`); conserva ítems resueltos y algún hilo abierto antiguo por si hay que promoverlo a `PLAN.md`.

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

## Estructura de carpetas de un caso → ver `core/config.py`

Las subcarpetas canónicas de cada expediente están en `core/config.CASO_SUBDIRS` (`00_Input`, `01_Procesado`, … `06_Anonimizado`, `07_AI cowork`, `90_Notas personales`) y su detalle (fuentes de intake, terminología propietario/buscador) documentado junto a la constante. Convención de nombres: tipo oración (`06_Anonimizado`, no `06_ANONIMIZADO`). No se transcribe aquí: esta sección llegó a listar `07_ANONIMIZADO` en mayúsculas, una estructura que el código ya no usa.

---

## Tests → fila «Tests» de *Estado general*

**Hogar único de la cifra en este fichero:** la fila **Tests** de la tabla de *Estado
general*, con su fecha de medición. El histórico por sesión vive en la bitácora de
cierres (`docs/bitacora/AAAA.md`); el detalle fino, en `git log`.

```powershell
python -m pytest -q --tb=no
```

> **Por qué este bloque ya no lleva cifra** (2026-08-02): era un **segundo hogar** del
> mismo hecho — decía «verde / exit 0 (2026-05-30, sesión 28)» mientras la tabla de
> arriba decía «668/668» y la suite real iba por 2.724. Dos sitios para el mismo dato
> no son redundancia útil: son un generador de drift. Fundamento:
> `docs/GOBERNANZA_FUENTES_VERDAD.md`. El inventario de módulos cubiertos que vivía
> aquí (mayo de 2026) quedó obsoleto y está en `git log`.
