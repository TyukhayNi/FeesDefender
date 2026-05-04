# STATUS — FeesDefender

> **Fuente de verdad única del proyecto.**
> Actualizar al cerrar cada sesión con `python -m scripts.session_close`.

**Última actualización:** 2026-05-04 (Bloque B colaboradores REST: `_list_colaboradores_rest()` implementado en `sudespacho_relations.py`; búsqueda colaboradores migrada a REST — elimina dependencia PHPSESSID; bug fix paginación (`fetched_this_page < PAGE_SIZE`); tests actualizados (find/ensure mockean `_list_colaboradores_rest`); 8 tests nuevos → 146 total; sidebar instrucciones corregidas (Application→Cookies); 3 entradas DEAD_ENDS.md añadidas)

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
| Tests | ✅ 146/146 (8 nuevos: _list_colaboradores_rest, load_all_colaboradores, search_colaboradores_for_ui) |
| Pipeline | ✅ Ejecutado end-to-end (BaRR3, 2026-04-28, 9/9 pasos OK, ~9 min) |
| Primer caso real | ✅ Creado, docs descargados |
| Taxonomía de casos | ✅ Actualizada en config.py |
| `sudespacho_create.py` | ✅ Extrajudicial + ✅ Judicial (2026-05-04) — DTO, tags completos, notas, helper |
| `list_gdocu_docs_rest` + `download_document_rest` | ✅ Implementado 2026-05-04 — sin PHPSESSID (solo x-api-key) |
| `pull_expediente` REST-first | ✅ Implementado 2026-05-04 — fallback legacy automático si REST falla |
| `core/intake_demanda.py` | ✅ save_file(), extract_zip() (path traversal sanitizado), list_files() (2026-05-04) |
| `core/share_drive.py` | ✅ share_folder_with_team() via Drive API v3 + build_request_email() (2026-05-04) |
| `05_Demanda judicial` | ✅ Añadida a INPUT_SUBDIRS — ensure_case() la crea automáticamente (2026-05-04) |
| `case_manager.get_drive_ev_ids()` | ✅ Lee folder_id del frontmatter de _caso.md (2026-05-04) |
| UI intake demanda | ✅ Tab Casos — expander upload+unzip ZIP automático (2026-05-04) |
| UI compartir carpeta | ✅ Tab Casos — expander directo (Drive API) + mensaje solicitud (2026-05-04) |
| `sudespacho_relations.py` | ✅ Extrajudicial + ✅ Judicial (2026-04-30) — deduplicación, link cliente/contrario/procurador, link colaborador, create_tag |
| Endpoint saveselect | ✅ Confirmado 2026-04-29 — cliente+colaborador persistidos en exp 600 |
| `core/intake_drive.py` | ✅ Completo — pull rclone gdrive_ev, marker .pulled, 27 tests |
| UI Drive E&V | ✅ Integrado en tab Nuevo caso + tab Casos (caso existente) |
| Nombres automáticos desde email | ✅ _email_to_nombre() — sin campos manuales |
| Tooltips UI | ✅ help= en todos los campos interactivos de streamlit_app.py |
| Toggle judicial UI | ✅ streamlit_app.py — radio Extrajudicial/Judicial, § 3b con NIG + tipo procedimiento, handler bifurcado (2026-05-04) |
| browser-cookie3 | ✅ PHPSESSID renovación automática desde Chrome en SudespachoLegacyConfig.from_env() (2026-05-04) |
| Renovación proactiva JWT (`_proactive_refresh_if_needed`) | ✅ Implementado 2026-05-04 |
| Detección E-plan (`_is_eplan_landing`, `_get_csrf_token`) | ✅ Implementado 2026-05-04 |
| `_try_renew_php_session` | ✅ Implementado 2026-05-04 — confirmado insuficiente sin PHPSESSID válido |
| `_update_env_field` (escribe .env + os.environ) | ✅ Implementado 2026-05-04 |
| Sidebar session_state (expander persistente) | ✅ Fix 2026-05-04 |
| UI `_email_input_with_crm` + botón 🔍 | ✅ Implementado — búsqueda migrada a REST (sin PHPSESSID); verificación end-to-end pendiente |
| `run_app.bat` | ✅ Lanzador para usuarios finales (Paola, Ana) |
| Tags CRM verificados | ✅ 87 extrajudicial (2026-04-28) + 88 judicial con nuevos (2026-05-04) |
| Notas de expediente | ✅ 13 NOTA_* alineadas con Manual 1.1.4 |
| `session_close.py` | ✅ Simplificado — solo pytest, sin interactividad |
| `docs/DEAD_ENDS.md` | ✅ 8 callejones documentados (+ SPA login NO crea PHPSESSID, 2026-05-04) |
| `docs/INTEGRACION_SUDESPACHO.md` | ✅ Actualizado 2026-05-04: REST cubre listing+descarga; 3 nuevos endpoints; gotcha #4 corregido |
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
**Expediente:** 648 (`expedientes_judiciales`)
**Docs descargados:** 5 archivos, 5,35 MB

**⚠️ Acción pendiente antes de lanzar pipeline:**
```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
Remove-Item -Recurse -Force "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU\00_INPUT\sudespacho"
python -m scripts.run_pipeline "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
```

---

## Próximas tareas (orden de prioridad)

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
3. **[SIGUIENTE-B]** Borrar colaborador de prueba ID=777 ("TEST FEESDEFENDER BORRAR") del CRM tnm.sudespacho.net manualmente.
12. **[SIGUIENTE-UI]** Declarar dependencias en `pyproject.toml` (ya existe `run_app.bat`).
13. ~~**[SIGUIENTE-J-TAGS]**~~ ✅ 2026-05-04 — Tags ciudad (IDs 297-303) y equipos faltantes (304-313) creados manualmente en CRM + constantes añadidas a `sudespacho_create.py`.
14. ~~**[SIGUIENTE-J-TEAMS]**~~ ✅ 2026-05-04 — Ver punto anterior.
15. ~~**[SIGUIENTE-J-UI]**~~ ✅ 2026-05-04 — Toggle Extrajudicial/Judicial en `streamlit_app.py`: radio, `_J_EQUIPOS_POR_CIUDAD`, `_J_CIUDADES`, § 3b con NIG + tipo procedimiento, handler bifurcado llamando a `create_expediente_judicial()`.
16. **[SIGUIENTE]** ⬅️ **Crear caso DEVOLUCION_RESERVA desde la UI** — Abrir Streamlit, seleccionar "Judicial", rellenar los datos del caso que recibió E&V, pulsar "⚡ Crear caso + enviar a sudespacho".
17. **[SIGUIENTE-B-COLAB]** ⬅️ **Verificar end-to-end botón 🔍 colaboradores** en Streamlit: abrir app → "Nuevo Caso" → campo email colaborador → teclear término → confirmar que aparecen sugerencias. Ya no requiere PHPSESSID (migrado a REST con x-api-key).
18. **[SIGUIENTE-SHARE]** Probar compartición directa carpeta E&V: tab Casos → expander "Compartir carpeta E&V" → botón "⚡ Compartir directamente". Si falla por token expirado, ejecutar `rclone ls gdrive_ev:` para refrescarlo.
16. **[SIGUIENTE-J-TESTS]** Tests para `create_expediente_judicial()`, `build_form_data_judicial()` y funciones de relación judicial.
11. ~~**[NIKOLAI]** Conectar cuenta `nikolai.tyukhay@engelvoelkers.com` en Cowork~~ ✅ 2026-04-28 — rclone `gdrive_ev` configurado; Cowork no soporta multi-cuenta, rclone es la solución definitiva.
12. **[SIGUIENTE-C]** Módulo `core/intake_drive.py`:
   - Inputs: `case_id`, `drive_ev_team_id`, `drive_ev_folder_id` (extraído de URL W-XXXXXX)
   - Ejecuta: `rclone copy "gdrive_ev:" 00_INPUT/manual/ --drive-team-drive <team_id> --drive-root-folder-id <folder_id>`
   - Actualiza `_caso.md` con los IDs y marca `.pulled` en `00_INPUT/manual/`
   - Tests: `test_intake_drive.py` con mock de rclone
   - UI: campo "URL carpeta Drive E&V" en formulario Streamlit "Nuevo Caso" → extrae team_id + folder_id automáticamente
9. **[Nuevo hilo]** Módulo `core/anonymizer.py` — integrar proyecto externo de anonimización.
10. **[Nuevo hilo]** Subida output anonimizado al Drive tyukhay.legal.
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
pytest -q   →   146 passed (2026-05-04)
```
Módulos cubiertos: `case_manager`, `inventory`, `utils`,
`sync_sudespacho` (+26 nuevos: REST gdocu), `sync_sudespacho_legacy`,
`sudespacho_relations` (+8 nuevos: REST colaboradores).
