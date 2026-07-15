# PLAN — FeesDefender

Bitácora de planificación compartida entre Nikolai y Cowork (PC). Edición de
código: solo Claude Code. Aquí van prioridades, decisiones e ideas.

Estado del proyecto y bitácora de cierre de sesión: ver `STATUS.md` (repo).
Backlog técnico (ideas, bugs latentes, mejoras diferidas): ver
`docs/MEJORAS_FUTURAS.md`. Las entradas se promueven aquí cuando tienen
disparador concreto (caso real, bug bloqueante o decisión de Nikolai),
con referencia al número original (`MEJORAS #NN`).
Historial de commits: `git log`. Acceso móvil: app de GitHub (lectura).

---

## ✅ MÁXIMA PRIORIDAD — CERRADA (ambos ítems completados 2026-07-07)

> Los dos bloques que abrían aquí (`[SIGUIENTE-CONTROLES-ANTIFUGA]` y `[BIBLIOTECA-CHECKOUT]`)
> están **completados y mergeados**. **No hay tarea de código en cola** (lo confirma `STATUS.md`
> [SIGUIENTE]). La próxima sesión elige el siguiente frente de las secciones `[SIGUIENTE-…]` de
> abajo según prioridad de Nikolai. Se conservan aquí marcados ✅ (patrón del repo).

---

## [SIGUIENTE-INFRA-POST-VALERO] Roadmap de infraestructura tras la sesión VALERO (2026-07-14)

*Disparador: sesión E2E VALERO (W-02XOR7 / BaRS8) del 2026-07-14 — OCR → sala de máquina → refuerzo por
visión → audiencia previa. La sesión destapó bugs vivos y fricción de fondo. Brainstorming del roadmap y
decisión de arquitectura del Cluster B: `docs/superpowers/specs/2026-07-14-expediente-scratch-design.md`.
Backlog completo (6 clusters) en `docs/MEJORAS_FUTURAS.md` #58-#63. Orden acordado: **A (+C en paralelo) →
B**; D/E/F quedan en backlog. **Actualización: el Cluster A lo completó la sesión paralela (PR #42, `24e69db`); siguiente = C (quick win) o B.***

- [x] **Split de bundles multi-documento — F1 (cerebro) ✅ MERGEADO 2026-07-15 (PR #45, squash `6dba396`).**
  `core/split_documental.py` nuevo (corte por hoja en blanco + fallback marcadores + manifiesto editable +
  `materializar`), `separar.py` tocado solo con el parámetro aditivo `tipos_extra` (congelado, byte-idéntico),
  evento `split_documental`. Construido subagent-driven (11 tareas TDD); revisión final Opus "ready to merge".
  Plan `docs/superpowers/plans/2026-07-14-split-sala-maquina.md` (spec+plan del PR #43). **F2 (integración en
  `core/sala_maquina.py`, Tareas 12-15 + 13B) PENDIENTE** — Cluster A ya en main → desbloqueada; rebasar antes.
  Deferidos F0 (calibración umbrales + fixture página-imagen) y F2 (contratos M-A/M-C) en `MEJORAS_FUTURAS #64`.

- [x] **A — Fiabilidad de la sala de máquina (`MEJORAS #58`) — ✅ HECHA (PR #42, `24e69db`, sesión paralela).** (1) Bug: `apply` incremental
  machaca `_cobertura.md` (`scripts/sala_maquina.py::apply` debe **fusionar** el estado previo, no volcar
  solo `cob`) — pérdida silenciosa de "qué queda por revisar". (2) `--vision` cableado a un transcriptor
  real (preferente la sesión Claude) o que **avise** en vez de no-op (`core/sala_maquina._transcribir_vision`).
  (3) Comando `reforzar` persistente (render→visión→MD+estado+cobertura). *En VALERO la cobertura de 35 filas
  se perdió y el refuerzo de visión hubo que persistirlo a mano.*
- [ ] **B — Expediente scratch (caso de trabajo local) (`MEJORAS #59`).** Stub `_caso.md` mínimo para que las
  skills detecten el caso (E&V, terminología, ubicación) sin Drive/CRM + flags `--case-dir`/`--casos-root` +
  comando de promoción a expediente completo. Resuelve de raíz la mala detección de modo (VALERO cayó en
  "civil genérico"). Diseño aprobado en la spec citada.
- [ ] **C — Campos de `gen_solicitud` (`MEJORAS #60`) — quick win, en paralelo a A.** Petición subsidiaria de
  averiguación de domicilio (art. 156 LEC) como campo + DNI pendiente que renderice limpio. Disparador:
  la testigo compradora (petición de averiguación de domicilio, art. 156 LEC) y la testigo directora de zona (DNI pendiente) en la AP de VALERO.
- Backlog (no promovidos): **#61** ingesta documental robusta (`.doc`/soffice, localizador de página en
  escaneado, extractor de entidades con visión), **#62** entorno Windows (`setup_windows_deps`) + unificar el
  `.bat` de OCR, **#63** sincronización de la providencia/DIOR de señalamiento a `00_Input`.

## [abrir-caso] ✅ F1 + F2a + F3-(A+C) mergeadas; F2b APARCADA; F3-judicial pendiente

*Disparador: encargo de Nikolai (spec v0.1 `SPEC_ABRIR_CASO.md`, fuera del repo). Abrir un expediente
E&V en una pasada (alta + intake + CRM), uniendo piezas ya existentes. Patrón «biblioteca»: cerebro
puro + orquestadores finos. Spec: `docs/superpowers/specs/2026-07-09-abrir-caso-design.md`. Plan F1:
`docs/superpowers/plans/2026-07-09-abrir-caso-f1.md`. Memoria `project-abrir-caso-f1`.*

- [x] **F1 (cerebro puro + CLI local, fuente `drive_ev`) — MERGEADA** (PR #13, squash `9fb0757`).
  `core/abrir_caso.py` (`componer_case_id`/`resolver_identidad`/`plan_intake`/`reconcile`/`crm_payload`)
  + CLI Typer `scripts/abrir_caso.py` (gate CRM, hash SHA-256 local, `--dry-run/--force/--yes/--crm skip`).
  Promovió `intake_drive.CONTROL_FILES`. +29 tests; suite 1599 verde. Decisiones: ambos frentes,
  colisión `ask`, CRM con gate, hash tras el pull, CLI en módulo nuevo.
- [x] **F2a — primitivas del conector — MERGEADA** (PR #16, squash `a66bc3b`). `hash_tree` +
  `strip_top_level` en `plugins/expedientes_xl/` (`fsops.py`+`server.py`+tests). Plan
  `docs/superpowers/plans/2026-07-09-abrir-caso-f2a-conector.md`.
- [x] **F3-(A+C) — fuentes no-Drive + init_caso — MERGEADA** (PR #22, squash `e68f59e`).
  CLI `--fuente manual|whatsapp|email` por delegación a los escritores nativos (`intake_manual`,
  `whatsapp_intake.deposit_export`, `email_export.export_label`), custodia forense uniforme (evento
  `upload_manual` cierra el hueco de que el intake manual no hasheaba). Regla: whatsapp/email auto-logean;
  drive_ev/manual los logea el orquestador (`_intake_generico`). Una fuente por invocación, reentrante.
  **`init_caso.py` se CONSERVA** (atajo ligero solo-esqueleto; sin disparador de deprecación, decisión
  Nikolai). Spec `docs/superpowers/specs/2026-07-10-abrir-caso-f3-fuentes-design.md` · plan
  `docs/superpowers/plans/2026-07-10-abrir-caso-f3-fuentes.md`. +12 tests, leak-scan verde.
- [~] **F2b — skill Cowork `abrir-caso` — APARCADA** 2026-07-10 (decisión Nikolai tras red-team
  adversarial). Bajo ROI (CRM no corre en Cowork, la CLI local ya hace todo, el intake duplicaría
  `intake-expediente`) + huecos de viabilidad (Cowork sin listado/lectura-de-log; handoff exigiría
  tocar `core/`). Hallazgos reutilizables (esp. **`_caso.md` es de dos niveles con el lock en `meta`**)
  en `docs/superpowers/specs/2026-07-10-abrir-caso-f2b-skill-cowork-design.md` (estado: aparcado).
  Reabrir solo con necesidad real de abrir un caso desde Cowork/móvil.
- [ ] **F3-judicial (parte B, diferida)** — expediente **judicial** en el CRM (`NuevoExpedienteJudicial`
  / `create_expediente_judicial` / element `expedientes_judiciales`): superficie grande (juzgado propiedad
  no-relación → 404, autos, procedimiento, partes M2M). Frente propio con disparador de caso judicial real.
- Relacionado: `docs/MEJORAS_FUTURAS.md` **#50** (sección "Relación con el ecosistema" en todas las skills).

## [SIGUIENTE-GOOGLE-MCP] F1 (lectura) ✅ MERGEADA · F2 (escritura+permisos+navegación) ✅ MERGEADA · F3/F4 pendientes

*Disparador: encargo de Nikolai (`ENCARGO_MCP_Google_despacho.md`, fuera del repo). MCP propio
`google-despacho` (Drive + Calendar, multicuenta EV+TL) que suple la mono-cuenta del Drive nativo.*

- Spec APROBADO + revisado: `docs/superpowers/specs/2026-07-08-google-despacho-mcp-design.md`.
  Plan de F1: `docs/superpowers/plans/2026-07-09-google-despacho-mcp-f1.md`. Rama `feat/google-despacho-mcp`.
- Decisiones cerradas: **un MCP por fases F1(lectura)→F2(escritura+permisos)→F3(lote+intake)→F4(Calendar)**;
  entrega **stdio local + `.dxt` + puente de escritorio**; **`expedientes` se queda** (solo candidato a
  retirar el Drive nativo); OAuth reutiliza el proyecto Cloud de Gmail; ubicación `plugins/google_despacho_mcp/`.
- [x] **R2 CERRADA (2026-07-09):** app ya `En producción` (no `Testing`) → caduca-7-días **no aplica**.
  Decisión: **un solo cliente OAuth, External + Producción, SIN split, NO marcar Internal**. §11 R2 del spec.
- [x] **F1 CÓDIGO COMPLETO (2026-07-09, subagent-driven + revisión adversarial):** `plugins/google_despacho_mcp/`
  (`google_auth` scope `drive.readonly`, `drive_ops` puro, `server` FastMCP con 9 tools de lectura + DL-root,
  `google_cli`, `run_server.bat`, README). **29 tests; suite completa 1570 verde.** La revisión adversarial
  cazó y cerró: bypass de DL-root vía symlink (`_resolve_dest` ahora usa `realpath`), mis-atribución de
  procedencia en el fan-out (`{**f, "account": acc}`), hueco de `max_bytes` post-fetch, import-safety en `.venv`.
- [x] **F1 VALIDADA EN VIVO (2026-07-09):** ambas cuentas conectadas (`~/.google-despacho/tokens/`); humo real =
  105 unidades compartidas EV / 10 TL (incl. «EXPEDIENTES - TYUKHAY LEGAL»), recientes, `about.get`, descarga
  (`get_media`→bytes+sha256) y confinamiento DL-root. Cableado en `claude_desktop_config.json`.
- [x] **F1 MERGEADA (2026-07-09):** PR #12 (`4056d6b`), rama+worktree podados; cableada en `claude_desktop_config.json` y **confirmada end-to-end desde Cowork** por el puente (`list_shared_drives` = 10 unidades TL + 5 EV cross-drive). Entrega vía `.dxt` (una entrada cruda en el config NO se expone al motor de tools de la nube).
- [x] **F2 COMPLETA + MERGEADA (2026-07-10):** PR #23 (squash `52a5845`), rama `feat/google-despacho-mcp-f2` podada. Plan `docs/superpowers/plans/2026-07-10-google-despacho-mcp-f2.md`; spec §13. **19 tools** (13 escritura + 3 permisos con guardarraíl `allow_external` + 3 navegación); scope OAuth `drive.readonly`→`drive`; UPLOAD-root simétrico al DL-root; `sha256` sobre bytes enviados. Subagent-driven; **la revisión adversarial del guardarraíl cazó 3 huecos fail-open** (perm_type/role sin normalizar + escalada de permiso externo en `update`) → fail-closed + tests de regresión. **Suite 1685 verde.**
  - [ ] **Operativo tras merge:** reautorizar TL + EV una vez (`python plugins/google_despacho_mcp/google_cli.py add`; scope subió a `drive`) + check de integración manual (§13.6) contra carpeta desechable de Drive.
  - [ ] **INSTALACIÓN EN APP/COWORK — PENDIENTE (sesión 2026-07-15, `claude/multi-drive-connector-install-9d4964`).** Objetivo del usuario: (a) **desinstalar la extensión Gmail solo-lectura obsoleta** (`gmail-ro` = "Gmail despacho (solo lectura)", superada por `gmail-multiaccount`) y (b) **instalar el conector `google-despacho` (Drive multicuenta) en app de escritorio + Cowork**. **Claude Code ✅ HECHO** (registrado `-s user` vía `run_server.bat`, verificado en vivo: `list_shared_drives`=10 unidades TL). **App/Cowork BLOQUEADO por bug de la build de escritorio `1.21459.0.0`**: la pantalla Ajustes→Extensiones se queda en "Cargando extensiones…" (stall del `electron_renderer`, no de red — `can_install`/blocklist completan OK en el log; las extensiones instaladas SÍ cargan y ejecutan). Reiniciar el PC NO lo arregla. **Vía de instalación manual ya preparada (bypass de la pantalla):** el registro vive en `%APPDATA%\Claude\extensions-installations.json` (entrada por extensión; `hash`=sha256 del `.dxt`; molde = `gmail-multiaccount`) + carpeta `%APPDATA%\Claude\Claude Extensions\local.dxt.<org>.<name>\` con el `.dxt` descomprimido. **Ya hecho:** `.dxt` F2 reconstruido (`plugins/google_despacho_mcp/dxt-build/google-despacho.dxt`, sha256 `4fc47d3a…03657`, 28 tools; el viejo empaquetaba F1/9 tools) · carpeta `local.dxt.tyukhay-legal.google-despacho\` YA extraída (residuo inofensivo sin entrada en el JSON) · script `plugins/google_despacho_mcp/dxt-build/instalar_extension.ps1` (fusiona la entrada, filtra el CLI por ruta, backup del JSON). **Falta:** con la **app de escritorio CERRADA** (mata solo procesos con Path `*WindowsApps*Claude*`; el CLI de Claude Code es proceso APARTE `…\claude-code\…\claude.exe` y sobrevive) → correr el `.ps1` (`powershell -ExecutionPolicy Bypass -File …`, la policy bloquea `&`) para registrar `google-despacho` **y** de paso quitar `gmail-ro` (borrar su entrada del JSON + su carpeta) → reabrir la app. Gotcha: escribir el JSON con la app abierta se pierde (clobber al salir). Cambios de esta rama **sin commitear** salvo que se decida PR: `manifest.json` (display_name/description/version→F2 2.0.0) + el `.ps1` + esta nota.
- **F3 (`import_drive_folder` intake EV→TL de una orden) APARCADA 2026-07-10** — sobreingeniería por ahora (decisión de Nikolai). Brainstorming + mapeo del ecosistema HECHOS y spec escrito (§14 del design doc, `dfad021`), pero **NO se construye**. Motivo: la vía existente **ZIP de Drive → `intake-expediente` (EXPEDIENTES-XL `extract_archive`)** cubre la necesidad hoy sin un orquestador cross-cuenta. **Corrección registrada para si se reabre:** los expedientes de origen se buscan en las **unidades compartidas de ENGEL** (cuenta EV), no en el Drive del despacho (el W-code resuelve la carpeta DESTINO en TL). **Disparadores de reapertura:** (a) volumen recurrente que haga tedioso el ZIP manual, (b) necesidad real de hacer el intake desde Cowork **sin PC**, (c) un caso que pinche la vía ZIP. Lote (`copy_tree`/`move_batch`/`delete_batch`) sigue diferido. Detalle en spec §14 (poner banner APARCADO).
- **Fleco de F2 (no de F3):** `download_file_content` (`drive_ops.py:209`) devuelve el mime de ORIGEN tras exportar un Doc nativo (no el de export) y no ajusta la extensión del destino — bug latente menor (sin consumidor tras aparcar F3). En backlog.
- Siguiente en cola: **F4** (Calendar) cuando haya disparador. Retomar por `writing-plans`.

## [SIGUIENTE-MCP-SUDESPACHO] MCP `sudespacho` (CRM del despacho) — F1 lectura: spec HECHO, plan pendiente

*Disparador: `docs/superpowers/handoff-2026-07-13-mcp-sudespacho.md` (brainstorming Cowork) + decisión Nikolai de dar producto rápido y escalable a los compañeros. Primer producto que escala a Ana/Sergio/Paola porque la API REST del CRM ya es nube. Aplica el principio transversal de dos capas (motor determinista + interfaz distribuible).*

- Spec APROBADO en brainstorming: `docs/superpowers/specs/2026-07-13-mcp-sudespacho-design.md`.
- **Decisiones cerradas:** **standalone** (sin `import core`, anti-drift por paridad) · entrega **`.dxt` a Cowork por el puente** · orden **F1 lectura → F2 escritura → F3+** · **Modelo B de credenciales: cuenta personal de cada usuario (Bearer JWT + refresh), NO la `x-api-key`** (hallazgo 2026-07-13: la key es GLOBAL/admin, no ligada a usuario, permisos no modificables, ~100% acceso → inútil para rol/atribución; el JWT personal SÍ respeta la matriz de rol —oculta contabilidad server-side— Y atribuye eventos al usuario; **Modelo A retirado, Modelo C descartado**) · **lista blanca deny-by-default** con TODO el árbol financiero/contable VETADO (2ª barrera) · **BORRADO NUNCA** (triple garantía: sin tool, cliente sin `DELETE`, rol con `Delete` OFF) · tools **genéricas** (`element` como parámetro) · **descubrimiento** por `describe_element` + playbook + catálogo (lectura casi automática, escritura mantiene HAR) · descarga vía `downloadUri` a DL-root (bytes nunca por el modelo; `presigned_download_url` NO es bloqueo, ya resuelto) · ubicación `plugins/sudespacho_mcp/`.
- **Descubrimientos reusados de El Contable** (`../ElContable/docs/`): matriz de permisos por rol (valida Modelo A) · slugs financieros confirmados (conceptos_*, facturas, facturas_proforma) · workaround del bug 500 de detalle (forma `?properties=a,b,c` coma vs `properties[]` array) · host de calendario `api-calendar-commons-pro.sudespacho.biz` · gramática `filterGroup` + enums + colisión `E1`.
- [x] **Gate de auth — mecanismo VERIFICADO EN VIVO (2026-07-13, usuario admin):** REST `element_registries/clientes_propios` → 200; JWT en localStorage con claims `username`+`roles` (atribución + rol); vida 60 min + `refresh_token`; **sin PHPSESSID** (REST = Bearer JWT puro). Modelo B viable.
- [x] **Sesión de verificación en vivo (2026-07-13) — 3 gates cerrados:** (1) **Bug 500** resuelto — forma **coma** `?properties=a,b,c`→200, array→500 (INTEGRACION §8.3 corregido, workaround propagado); (2) **Login** resuelto — no hay endpoint usuario/contraseña (todos 404) → alta por **`refresh_token` pegado**, el plugin no maneja contraseña; (3) **Slugs** resueltos — `abogados_propios`/`abogados_contrarios` (no `abogados`), `extrajudiciales` (no `expedientes_extrajudiciales`), `juzgados` válido; `properties[]` obligatorio también en el listado. Spec+plan actualizados.
- [ ] **PENDIENTES del gate:** (a) prueba de **atribución en escritura** (`created_by`, F2); (b) prueba de **rol que oculta la contabilidad** con un usuario de rol abogado (Nikolai es admin, lo ve todo).
- [ ] **🚩 RIESGO tope de licencia (4 concurrentes) — Nikolai lo CONSULTA con sudespacho (en curso):** confirmar si una sesión JWT del MCP consume licencia (Nikolai+3 compañeros=4, sin margen; entrar expulsó al usuario de soporte). Posible bloqueante del escalado simultáneo (NO de código para F1). Mitigaciones a estudiar: reusar token de sesión web, ampliar licencias, o limitar concurrencia. Puerta de DESPLIEGUE, no de build.
- [ ] **F1 (lectura)** — desglosar por `writing-plans` y construir. Entregables: cliente REST puro + lista blanca/catálogo + `describe_element` + tools de consulta genérica + expedientes/documentos + descarga a DL-root + `.dxt`. Playbook de descubrimiento en `docs/INTEGRACION_SUDESPACHO.md`.
- [ ] **F2 (escritura)** y **F3+** (agenda CRM en escritura, legacy, lote): spec/plan aparte, por disparador.
- [x] **Revisión adversarial del spec (2026-07-13, 4 lentes):** núcleo resiste; correcciones aplicadas a spec+plan (confidencialidad por CAMPO no solo slug + filtro de propiedades; `describe_element` solo-esquema; documentos vía `download_document` a DL-root + `gdocu` en lista blanca + validar elemento-origen; retirada la afirmación "coma esquiva 500" → fallback legacy; `.dxt` autocontenido sin ruta/repo personal; token store atómico+lock+carga tolerante; refresco reactivo a 401 + `_extract` tolerante; descarga con timeout/redirects; no-pérdida-de-datos en F2). **Gates EN VIVO (prerrequisitos de despliegue):** rol abogado oculta contabilidad a nivel slug+campo, endpoint de login, coma-vs-500, escritura con JWT (F2), licencia, vida del refresh_token, verificar slugs. Detalle en spec §13.

### ✅ [SIGUIENTE-CONTROLES-ANTIFUGA] COMPLETA 2026-07-07 — controles de `SEGURIDAD_DATOS.md` implementados
*2026-07-07. Disparador concreto: el incidente de fugas de la Fase 2 (HAR + PII en el historial → una sesión entera de rewrite). La doctrina ya está escrita y cableada (`docs/SEGURIDAD_DATOS.md`, hogar canónico; cableado en el mapa SSOT, INDICE, GOBERNANZA §4 y CLAUDE.md). Todos los controles corren solos: barrera local (`51ecf24`), CI + shape-detection (#1 `48c790f`, #3 `e1ff182`) y prevención server-side ACTIVA (`a79ba90`).*

Estado (según la tabla doctrina→mecanismo de `SEGURIDAD_DATOS.md`):
- [x] **pre-commit local** — `.pre-commit-config.yaml`: gitleaks (secretos; verificado que pilla JWT) + `check-added-large-files` (maxkb=2048, corta el HAR de 22 MB) + `scripts/precommit_leak_guard.py` (rutas vetadas + PII de la blocklist gitignored, con test `tests/test_precommit_leak_guard.py`, 9 verde). Instalado en `pre-commit` y `pre-push`. **Auto-push `post-commit` eliminado** (chocaba con el flujo PR). Commit: `51ecf24`.
- [x] **CI** — `.github/workflows/leak-scan.yml`: gitleaks + leak-guard en cada push/PR. Detección garantizada aunque el push venga de una máquina sin el hook. Opción: secret `PII_BLOCKLIST` para escaneo de PII server-side sin que la lista viva en el repo.
- [x] **Prevención server-side de verdad — ACTIVA (2026-07-07, Nikolai subió a Pro):** branch protection en `main` con `leak-scan` como check OBLIGATORIO + PR requerido + `enforce_admins` + force-push/borrado bloqueados. **Ya no se pushea directo a `main`: rama + PR.** Cubre todas las máquinas y Cowork.
- [x] **Fixtures sintéticas / test-guard — HECHO (2026-07-07).** Al descubrir: el `leak-guard` con la blocklist real halló **0 PII en TODO el árbol trackeado** — Fase 1 ya había pseudonimizado los tests. Los emails de `tests/` son sintéticos (`x.com`, `example.invalid`, `*.example`) o nombres inventados sobre dominios realistas. Deliverable real = el guard anti-regresión `tests/test_no_pii_en_tests.py` (reutiliza `escanear` sobre `tests/`+`core/`; se salta si no hay blocklist, p. ej. CI sin secret). Suite del guard 10 verde.
- Instalar el hook en cada clon/worktree: `pre-commit install && pre-commit install --hook-type pre-push` (incl. la worktree `FeesDefender-email`).

### ✅ [BIBLIOTECA-CHECKOUT] COMPLETA, MERGEADA y VALIDADA EN VIVO 2026-07-07
*2026-07-07. Disparador: diseño v2 congelado (`~/DISEÑO_V2_20260707_MERGE_BIBLIOTECA.md`) + piloto validado en W-02VND1/W-02THLJ. Implementa el sistema de checkout/checkin Desktop↔Drive (biblioteca de casos).*

**MERGEADA a `main` vía 3 PRs** (+ docs): **#4 `061d99e`** (cerebro puro + CLI + guard §6 + CP10 + campos de lock en `CaseMeta` + 4 eventos), **#5 `b67f46d`** (guard §6 en `email_export`/`sync_sudespacho`), **#6 `8dd138c`** (checkin honra el plan por-fichero vía `--files-from`) y **#7 `16cbb54`** (STATUS.md al estado final + gotchas de rclone/checkin en `DEAD_ENDS.md`). Rama `feat/repository-checkout` y worktree `~/Dev/fd-repo-checkout` ya podados. **Validada EN VIVO** contra el Drive real (`gdrive_tl`, casos desechables purgados): checkout, checkin (copia + borrado + renombrado + conflicto→resolución→disponible), bandeja/CP10, write-then-verify del lock, idempotencia. Estado final en `STATUS.md` (bloque «BIBLIOTECA DE CASOS — COMPLETA, MERGEADA y VALIDADA EN VIVO»).

- [x] `core/config.py`: `ESTADOS_REPOSITORIO`, `TRANSICIONES_PERMITIDAS`, `MERGE_EXCLUSIONS`, `DERIVADOS_REGENERABLES`, `PENDIENTE_CHECKIN_SUBDIR`, `RCLONE_REMOTE_TL`/`TEAM_DRIVE_TL` (SSOT de definición, §2/§5).
- [x] `core/repository_checkout.py` **PURO** (cero I/O Drive): `validar_transicion`, `plan_merge` (tabla canónica 9 casos §4.1 + derivados §4.2 + Google-native + renombrado por hash), `decidir_escritura` (guard §6), mutadores puros del lock (fm→fm), `verificar_nonce`, constructores de eventos.
- [x] `core/case_manager.py`: campos de lock en `CaseMeta` (§2.3, retrocompatibles) + helpers `escribir_lock`/`liberar_lock`/`cancelar_checkout`/`marcar_conflicto`/`leer_estado_repositorio`/`leer_lock` (delegan en el cerebro) + `guard_escritura` (guard §6 integrado, emite `pendiente_checkin`). Fix latente: `register_expediente` ahora preserva todos los campos (no resetea el lock).
- [x] `core/intake_log.py`: eventos `case_checkout`/`case_checkin`/`checkout_cancelado`/`pendiente_checkin` (INTAKE_EVENTS 18→22).
- [x] `core/utils.py`: `now_iso_utc()` + `ts_compacto()` (timestamps ISO-UTC con zona para artefactos, §8).
- [x] CLI `scripts/repository_cli.py`: `checkout`/`checkin` orquestando cerebro + rclone (`gdrive_tl` + `team_drive`, subprocess UTF-8 sin pipes, `--checksum`/`--backup-dir`/`--fast-list`, inventario validado por contenido, semáforo). Codifica los 9 hallazgos del piloto.
- [x] Tests `tests/test_repository_checkout.py` (65) + `tests/test_repository_cli.py` (15): transiciones válidas/inválidas, tabla 9 casos, doble checkout rechazado, convergencia (idempotencia), round-trip `_caso.md`, bandeja, guard, parseo lsjson, semáforo, comandos rclone. **Suite completa verde (1556 tests).**
- [x] Guard §6 **cableado** en los writers de intake con destino propio: `intake_manual` (`save_file`→`manual`, `save_file_crm_branch`→`crm_manual`), `whatsapp_intake.deposit_export`→`whatsapp`, `intake_drive.pull_drive_ev`→`drive_ev`. Helper reutilizable `case_manager.dir_intake(case_id, rel_base, origen)` (testeado) → devuelve dir efectivo (bandeja o normal) + evento; cualquier writer lo adopta en 1 línea. Retrocompatible (disponible → normal).
- [x] **CP10 — integración de la bandeja** en el checkin del CLI: `planificar_integracion_bandeja` (puro, testeado) + `_integrar_bandeja` (mueve cada `_pendiente_checkin/<origen>/<rel>` a `<rel>`, o a `_reingesta_<base>` si colisiona — nunca sobrescribe; §6) + `rmdirs` de la bandeja vacía. Se ejecuta antes de CP11.
- [x] Guard §6 en `email_export` y `sync_sudespacho` (pull CRM): **HECHO en PR #5 `b67f46d`** — el guard §6 queda cableado en **TODOS** los writers de intake (manual, whatsapp, drive_ev, email, crm) vía `case_manager.dir_intake`.
- [x] Revisión skill `checkin-caso` (`~/checkin-caso-skill/`, editada la copia local): exclusiones de protocolo COMPLETAS en `.cmd`, evento canónico `case_checkin`, liberación del lock CP11, paridad con la CLI, baseline 3-vías, +2 lecciones, eval 0 actualizado. Cowork re-ejecuta evals antes de instalar.
- [x] Skills **`checkin-caso` (revisada) + `checkout-caso` (nueva)** empaquetadas (`dist_skills/*.skill`, raíz canónica). Cowork las re-importa (skills sueltos, no bundle de plugin).

**Decisiones (Nikolai: "SÍ A TODO", 2026-07-07):** commit + PR ✓; guard cableado en TODOS los writers de intake ✓; reconciliación `90_Notas personales` = copia ciega de cortesía como no-op ✓; ESTADO.md del Drive la actualiza Cowork.

Diferidos: alertas de préstamo >7 días (tarea programada), sección STATUS.md como vista derivada, UI Streamlit; instalar las skills en Cowork.

### ✅ [SANEADO-PII-FASE-2] HECHA 2026-07-06 — Historial git reescrito + repo GitHub recreado (scrub total)
*La Fase 1 (árbol actual) estaba en el `7c27ec5` original; ver memoria `project-saneado-pii-repo`. Esta Fase 2 sacó la PII del HISTORIAL (HAR 22 MB + `data/_audit/` desde el commit inicial `d6051f4`).*

**Ejecutado:**
- [x] Rewrite con `python -m git_filter_repo` sobre **clon `--mirror` aparte** (`~/Dev/fd-rewrite.git`; backup íntegro con PII en `~/Dev/fd-backup.git`): `--force --invert-paths --path docs/_descubrimiento/ --path data/_audit/ --replace-text data/_saneado/replacements.txt` (67 reglas). Nuevo `main` = **`a40b27f`** (494 commits). Verificado: HAR/audit fuera del historial, 0 JWT, 0 PII alta-ID como palabra, pseudónimos presentes. Único cambio de árbol en HEAD vs Fase 1: 2 líneas de prosa meta en `PLAN.md`/`STATUS.md` (mejora).
- [x] **Gate que el plan no cubría (detectado en sesión):** `push --force origin main` NO limpia GitHub — los `refs/pull/*` (10 PRs, server-managed) + la rama `feat` siguen anclando los objetos viejos. **Decisión Nikolai: SCRUB TOTAL = borrar + recrear el repo** (token sin scope `delete_repo`, `gh` no instalado → Nikolai lo hizo en la UI web).
- [x] Push selectivo al repo recreado: `main` (`a40b27f`) + `feat/intake-procuradores-f2-ui` (`58ffaeb`) + `feat/intake-email-consultores` (esta era **local-only sin respaldo** → se reescribió también y se subió limpia como `71f8fee`). Las 6 ramas cloud (todas mergeadas) desaparecen por no re-subirlas. **Remoto final: solo esas 3 ramas, 0 refs de PR, 0 HAR/PII/JWT.**
- [x] Worktrees re-sincronizadas (`reset --hard origin/…` — lo corre Nikolai, está en deny-rule) + `reflog expire`/`gc --prune=now` para purgar la PII del `.git` local (incl. la worktree enlazada `FeesDefender-email`).

**Pendiente (opcional, cosmético — Fase 2a):** barrer nombres del despacho en PROSA distinguiendo prosa (sustituir) de config FUNCIONAL a conservar (`core/config.py ABOGADOS`, `sudespacho_create.abogado_principal`, firma `share_drive.py`, `LICENSE`). En gran parte inútil (el nombre persiste en git author + CRM). Sin disparador → no promovido.

**Avisos post-recreación:** re-invitar colaboradores + reconfigurar branch protection (se pierden al recrear); cualquier otro clon/Cowork debe **re-clonar** (SHAs sin ancestro común); `fd-backup.git` borrable al confirmar el resultado.

**Fallos de baseline — RESUELTOS 2026-07-07:** `test_helpers_sin_drift` (drift de helpers → `sync_skill_helpers.py`); `test_adjuntos_contenido_router` (aislamiento por `reload(extractor)` → captura de `ExtractionError` cualificada por módulo en `router.py`); 2 módulos MCP sin colección (`mcp` instalado + `importorskip`). **Suite `1418 passed, 58 skipped`, verde.**

---

## 🧭 PRINCIPIO TRANSVERSAL — dos capas: motor determinista + interfaz distribuible (plugin)
*Fijado 2026-07-13 (brainstorming Claude Code, Nikolai). Decisión de rumbo sobre cómo escalar el producto a los compañeros (Ana, Sergio, Paola) sin dejar de trabajar el código de FeesDefender. Disparador: el diseño del MCP de CRM sudespacho (`docs/superpowers/specs/2026-07-13-mcp-sudespacho-design.md`) obligó a decidir plugin standalone vs wrap-core.*

**El producto es UNA cosa en DOS capas, no dos tracks que compiten:**
- **Motor determinista (`core/`)** = la capa de confianza y auditoría. Todo lo forense, exacto e irreversible: custodia SHA-256, anonimización (`core/anon` — cero pérdida de lógica), altas en CRM (autoincremento sin duplicar), fidelidad byte de correos. Se mantiene y se sigue trabajando; es el cimiento, no legado a jubilar.
- **Plugins/skills = la interfaz distribuible** que tocan los compañeros. Se reparte por la superficie de Claude (Cowork/Desktop/móvil): se instala y funciona, **sin repo, sin `.venv`, sin `G:`**. El Streamlit local NO escala a terceros porque es un entorno de desarrollador.

**Regla de oro (evita el error caro):** lo irreversible/forense vive en el motor; el plugin lo **dispara**, no lo **reimplementa** "rápido". Si un plugin debe replicar una operación del motor, se blinda con **tests de paridad** contra `core` (patrón §14.6 de `2026-07-08-google-despacho-mcp-design.md`). Corolario de empaquetado: para que un plugin escale a un compañero debe ser **standalone** (`.dxt` autocontenido que él instala con sus credenciales); un plugin acoplado al repo (wrap-core) solo corre en la máquina que tiene el repo.

**Qué escala a los compañeros y qué no (a fecha de hoy):**
- **Escala YA, sin construir nada:** skills puro-LLM + conectores de lectura (Drive/Gmail) — `triaje-viabilidad`, `escritos-judiciales`, `verificacion-anclada-fuente`.
- **Escala con build acotado:** MCP de CRM sudespacho **en lectura** (standalone; la API REST `x-api-key` ya es nube) → candidato a "primer producto rápido" para los compañeros, bajo riesgo.
- **NO escala todavía (se queda en el track local determinista):** OCR, anonimización, atomización de correo y todo lo que hoy exige el pipeline local. Plugin-izarlo para terceros exigiría **hostear el motor** — proyecto aparte, sin disparador hoy.

---

## 🧭 PRINCIPIO TRANSVERSAL — copia al Drive por lote (hidratar→procesar→devolver)
*Fijado 2026-07-07 sobre benchmark medido (Cowork). Fuente: `HANDOFF_benchmark_vias_drive_2026-07-07.md` (integrado y borrable). Números y tabla en `docs/DEAD_ENDS.md` §"Benchmark de vías de copia al Drive". Confirma —no reabre— las decisiones del diseño V2 (merge + biblioteca, doc en Cowork/Drive, no trackeado aquí).*

**Hallazgo rector:** el cuello de botella de trabajar contra el Drive es el **número de operaciones MCP** (~10-15 s fijos cada una), **no los bytes** (202 MB tarda lo mismo que 24 KB). Los ~53 min de la sala fueron 120+ round-trips per-fichero, no volumen.

Tres reglas que gobiernan TODO pipeline de procesado (aplican a `[SIGUIENTE-MOTOR-DOCUMENTAL]`, `[SIGUIENTE-SKILL-EXPEDIENTE-A-MD]`, `[SIGUIENTE-EMAIL-ATOMIZE]`, `[SIGUIENTE-CRONOLOGIA-UNIFICADA]`, `[SIGUIENTE-SALA-UNICA-PLANA]`):

- **(b) REQUISITO de diseño — hidratar→procesar→devolver.** Todo procesado masivo (OCR/MD/anonimizador, atomizadores) se diseña: **copia masiva previa a disco local en un viaje** (`rclone copy` / `copy_dir`, no bucle) → pipeline **contra disco local** → **subida de resultados en un solo lote**. **Nunca** lanzar OCR/lectura contra `G:` en streaming (cada `open()` descarga bajo demanda, con relecturas), ni bucles fichero-a-fichero vía MCP. `create_file` con bytes por el modelo queda descartado para >1 MB.
- **(a) CONTRAINDICACIÓN — el checkout de biblioteca NO acelera sesiones de Cowork.** El overhead por llamada de Cowork se paga igual esté el caso donde esté; el checkout de la biblioteca (diseño V2) aporta a **humanos, pipeline local y trabajo offline**, no a la latencia de Cowork. No justificar el checkout por "acelerar Cowork". *(Offline refuerza el V2: la vuelta de un periodo sin conexión es el caso central del merge 3-vías con baseline; el pin "disponible sin conexión" de Drive for Desktop sincroniza sin lock ni baseline → resuelve por última-escritura o duplicación silenciosa, inaceptable con trazabilidad forense.)*
- **(c) PARCHE PROVISIONAL (hasta que exista el piloto de biblioteca).** Para procesar un caso HOY: `rclone copy` manual del caso a local antes del pipeline y de vuelta al terminar (válido solo si **un único usuario** toca el caso), o **pin offline** de la carpeta antes de procesar.

---

### ✅ [CRITICO-PRESIGNED-DOWNLOAD-BUG] RESUELTO 2026-06-10 — descarga del Gestor Documental

La descarga REST está arreglada (era la **Fase 0** de
`[SIGUIENTE-INTAKE-JUDICIAL-AUTO]`, abajo). Causa raíz: el CRM redesplegó el
módulo `App\Upload` y rompió **ambos** endpoints de presigned-URL
(`/api/files/presigned_download_url` → 400 IRI; `/api/documents/presigned_urls/s3/download`
→ 500 controlador no registrado). Endpoint vivo: `GET /api/documents/{id}/downloadUri`
→ campo `presignedDownloadUrl`. `get_presigned_download_url` reescrito; 31/31 docs
del exp. 649 verificados byte a byte. Detalle completo y diagnóstico en
`docs/DEAD_ENDS.md` (entrada marcada ✅ RESUELTO). **Próximo paso real:** Fases 1-4
de `[SIGUIENTE-INTAKE-JUDICIAL-AUTO]`.

---

## ✅ [SIGUIENTE-SKILL-EXPEDIENTE-A-MD] Skill `organizar-sala-maquina` (ex `expediente-a-md`) — COMPLETA 2026-07-09
*Decisión Nikolai 2026-07-04 (vía lean). CONSTRUIDA y validada 2026-07-09 en rama `feat/organizar-sala-maquina` (PR pendiente de merge → sustituir por hash del squash al mergear). Renombrada `expediente-a-md`→`organizar-sala-maquina` para alinear con el grafo de ecosistema de `abrir-caso` (paraleliza `organizar-sala-lectura`).*

> **HECHA.** Spec `docs/superpowers/specs/2026-07-09-organizar-sala-maquina-design.md` · plan `docs/superpowers/plans/2026-07-09-organizar-sala-maquina.md`. Cerebro `core/sala_maquina.py` + CLI `scripts/sala_maquina.py` + skill `.claude/skills/organizar-sala-maquina/`. 51 tests verdes; revisión adversarial por subagentes (cazó fallo de aislamiento por documento, hueco de custodia `01_OCR/` con `PriorOcrFound`, estado `--force` obsoleto). **Task 14 (corrida real W-02VND1): 668 docs, 0 crashes, 531 `ok`**; los `empty` = 90 fotos + 6 PDFs (candidatos `--vision`), todos en `_cobertura.md` (cero caída silenciosa).

**Qué hace (2 pasos + handoff):**
- [1] `01_Procesado/02_Sala de máquina/01_OCR/` — PDFs **buscables** con **OCRmyPDF** (local, sin tope de páginas).
- [2] `01_Procesado/02_Sala de máquina/03_MD/` — 1 `.md` por documento (+ `raw_text/` intermedio, idempotencia).
- **Handoff:** SUGIERE `organizar-sala-lectura` (puntero atómico, NO encadena).
- `_revisar/_cobertura.md` (red de calidad: densidad+gibberish+idioma). `00_Input`/`90_Notas personales` intocables (guard). Idempotente por sha256.

**Desviaciones vs diseño lean 2026-07-04 (cerradas con Nikolai):** escribe en `02_Sala de máquina/` (no plano) · NO renombra `Sala lectura` (eso es motor F0) · handoff SUGIERE (no encadena) · NO usa `pipeline.run`/Docling (OCRmyPDF aguas arriba → cierra el hueco de >30 pp). Integración de ecosistema diferida al patrón grafo-único (`MEJORAS #50`, otra sesión).

**Motor:** OCRmyPDF base (obligatorio para el PDF buscable — Claude visión no lo genera); **Claude visión (Sonnet 5 / Opus 4.8) = refuerzo OPCIONAL** del MD en páginas duras (manuscrito/tablas).

**Reutiliza:** `core/anon/ocr.py::ocr_pdf` · `imagen_a_pdf` · `extractor` · `markdown_generator` · `catalogo_documental` · `intake_log` · `utils.output_slug` · `pypdfium2` · skill `organizar-sala-lectura`.

**Prerrequisitos para arrancar:**
- [ ] Instalar **OCRmyPDF + Tesseract `spa/cat/rus`** en el PC (imprescindible para [1]).
- [ ] Aportar **un caso real** (o unos PDFs) para el E2E.
- [ ] Build: `render`(pypdfium2) + `SKILL.md` + tests (transcripción mockeada) + `CHANGELOG` + sync helpers `_shared`.

## [SIGUIENTE-MOTOR-DOCUMENTAL] Motor documental unificado (split/OCR/MD) + empaquetado como conector (`MEJORAS #48`)
*Decisión Nikolai 2026-07-03. Disparador concreto: Nikolai quiere empaquetar el motor OCR→split→MD como un conector/plugin reutilizable por los compañeros. Un motor fragmentado y que falla en silencio no se puede empaquetar bien → sanear + fachada + registro de cobertura es la preparación del plugin.*

> **⏸️ APARCADO (2026-07-04).** Nikolai pausa el motor/refactor completo. **Foco actual: skills con código**
> (vía lean — skill que orquesta y llama a motores existentes, p. ej. `ocr-a-md`, sobre el scaffold actual).
> El diseño queda de referencia para retomarlo. Estudio de mercado 2026 + opciones de motor (OSS local
> Docling(MIT)>MinerU(AGPL) / **Mistral OCR cloud+ZDR+DPA como opción de fase de construcción** / Azure
> contenedor para manuscrito, post-anonimización) en §F del doc.

> **Plano completo y memoria de diagnóstico: [`docs/PLAN_MOTOR_DOCUMENTAL.md`](docs/PLAN_MOTOR_DOCUMENTAL.md).**
> Consolida `MEJORAS #21/#24/#39/#42/#43/#41`. **Solo diseño escrito; sin código todavía.**

**Diagnóstico (resumen).** Tres motores de OCR desacoplados (Docling interno · RapidOCR por página vía
script manual · OCRmyPDF en anon), hueco de escaneados >30pp que salen vacíos, banda muerta de umbrales
(100 vs 50 chars), imágenes con tres tratos incompatibles (las `.heic` se caen en el inventario), y
`separar.py` desenganchado del pipeline. Detalle con `file:line` en el doc.

**Decisiones de organización (fijadas 2026-07-03, informadas por Vassal Litigator — ver §G/§H/§I del doc):**
`01_Procesado/01_Sala de lectura/` (humano) + `01_Procesado/02_Sala de máquina/` (máquina, productos numerados `01_OCR/02_Documentos/03_MD`) · id **dual** (`sha8` interno + `doc-NNN` legible) · **registro ÚNICO de caso** estilo Vassal `index.yaml` (vistas humanas derivadas) · **reocr condicional** por `ocr_quality`.

**Decisiones estratégicas (fijadas 2026-07-04 — §L del doc):** (1) **plugin primero, Streamlit parqueado** — distribución vía plugin; (2) **Ollama/LLM local descartado** → motor OCR **FIJADO: OCRmyPDF + `ocr_per_page` torch como reocr** (visión local/cloud fuera); (3) **regla PII relajada temporalmente** — anonimización = **último eslabón**, con **gate de reinstauración del muro `06`** (condiciones: pipeline→MD ✔, sala de máquina ✔, sala de lectura ✔, intake ✔). Resultados tangibles primero.

**Principios rectores (M1–M9 — §M del doc):** M1 golden fixture antes de tocar código · M2 registro primero · M3 walking skeleton · M4 fachada `procesar_expediente()` desde el día uno · M5 `00_Input` intocable (guard/test) · M6 medir el "antes" (documentos ciegos) · M7 Preview→Apply obligatorio · M8 preflight por capacidades (centralizado en `health_check`) · M9 doctor/manifiesto de dependencias.

**Orden de ejecución (fases, resecuenciado §L+§M).**
- [ ] **F(-1) — fundaciones sin riesgo:** golden fixture de W-02VND1 (M1) + auditoría "antes" de documentos ciegos (M6).
- [ ] **F1 — registro ÚNICO de caso** (elevar+extender `indice_documental.yaml` a ámbito caso, esquema estilo Vassal `index.yaml`) + **id dual** (`sha8`+`doc-NNN`) + **fachada fina** `procesar_expediente()` (M4) + vistas humanas derivadas. Piedra angular.
- [ ] **F0 — layout + botón reorganizar:** renombrar `Sala lectura` → `01_Sala de lectura`, crear `02_Sala de máquina/`; **botón `reorganizar_caso`** (`plan`/`apply`, `--todos`, journal reversible estilo `migrate_05crm_buckets`); sello **`layout_version`**; **cablear `--force`**; alinear umbrales, docstring/etiqueta, extensiones + HEIC. Ver §J.
- [ ] **F3 — motor OCR + reocr + espejos:** **OCRmyPDF** → PDF buscable (fijado). **Extractor→MD = decisión aplazada tras la junta; bake-off MinerU vs Docling** sobre fixture + casos duros (escritura/catalán/ruso/tabla/manuscrito), gate hardware(CPU/OOM)/catalán/licencia — MinerU favorito (local, CPU, determinista, tablas+manuscrito, sin PII; si cumple, elimina Claude visión). Persistir en `02_Sala de máquina/{01_OCR,02_Documentos,03_MD}` con espejo de `00_Input/`; dejar de borrar el PDF del OCR en anon. **Validado antes con walking skeleton (M3).** Ver §F/§G.
- [ ] **F4 — conector MCP + empaquetado + botón reformar plugin** (aislamiento por subproceso, versión/modelos pinneados, sin fuga de datos, preservar `core/anon`) + **preflight (M8)** + **doctor/manifiesto (M9)**. **Botón `rebuild_plugin`** mecánico + señalización semántica (handoff `motor_mejora`) + hook de drift (`session-start-hook`). Ver §K.
- [ ] **F-final — anonimización + reinstauración del muro `06`** (gate PII §L) — último eslabón; + faltas restantes (D.2–D.9) según disparador.
- **Transversales:** Preview→Apply (M7) y guard `00_Input` (M5) en todas las fases.

## ✅ [SIGUIENTE-EMAIL-APLANADO-ANIDADOS] Aplanado byte-fiel de emails anidados en el export de etiquetas
*Decisión Nikolai 2026-06-24 (hilo Cowork BaRS1 Tibidabo 8). Disparador concreto: en `03_Email` del caso W-02VND1 no aparecen los emails que viajan adjuntos dentro de otro (p. ej. los del padre `2026-06-08_mails_consulado`). Extiende `[SIGUIENTE-EXPORT-ETIQUETA-EMAIL]` (abajo, ✅).*

> **✅ HECHO 2026-06-24 — Parte 1 (`c492b70`) + Parte 2 (`911bf39`) + fix red de seguridad (`5cbb6eb`).**
> Ambas partes implementadas por TDD, cada una con revisión adversarial (3 lentes) cuyos
> hallazgos HIGH/MEDIUM/LOW se corrigieron en el mismo commit. Suite 1215 verde.
>
> **Reextracción real W-02VND1 EJECUTADA** (`--force --extraer-adjuntos`): 125 → **277 `.eml`**
> a primer nivel; **37 ficheros rescatados** de enlaces (PDFs `Nota simple`/`Nota mercantil`/
> poderes + grabación de la call de 193 MB; 3 carpetas y 11 nativos anotados; 14 firmas
> filtradas; 1 manual). La corrida destapó que el **boundary reusado entre niveles SÍ ocurre**
> (3 padres `jdb_*`, 126 anidados de Apple Mail/Outlook/Nodemailer): el trigger inicial
> (boundary repetido) era demasiado agresivo y los re-serializaba aunque el rebanado byte-fiel
> era correcto → **fix `5cbb6eb`** ancla la red de seguridad a la coincidencia de Message-IDs
> con el parser (byte-fiel si coinciden). **Decisión Nikolai:** los 126 ya almacenados se
> **aceptan re-serializados** (contenido íntegro; el byte-original sigue embebido en el `.eml`
> padre, re-extraíble a demanda); sin rebuild. Residuales en `MEJORAS #44`/`#45`.
> **Pendiente menor:** si el flag afecta a la interfaz, re-empaquetar/re-importar la skill
> `exportar-correos-etiqueta`.

> **Plano completo y listo para ejecutar: `docs/PLAN_email_aplanado_anidados.md`.**
> Todo el código de producción y el bloque de tests están **verificados en sandbox
> (7/7 verde)** antes de redactar el plano. Es la **Parte 1 de 2**.

**Causa raíz.** En `core/email_export.py`, `split_eml` descarta las partes
`message/rfc822` porque `get_payload(decode=True)` devuelve `None` para ellas
(`if payload is None: continue`). Los `.eml` adjuntos quedan solo embebidos en el
padre, sin extraer.

**Qué hay que hacer (resumen; detalle en el plano).** Extraer cada email anidado a
**primer nivel** de `03_Email`, **byte-original** (rebanando los bytes crudos +
decodificando el transfer-encoding; `as_bytes()` NO sirve, normaliza CRLF), nombrado
por sus propias cabeceras, **recursivo** a hojas, **deduplicado** por `Message-ID`,
con el padre conservado en la cronología y la **procedencia** (`forwarded_in`) en el
evento `upload_email` de `_intake_log.jsonl`. Aplanado **por defecto**
(`--no-aplanar-emails` para opt-out). **Red de seguridad:** si el rebanado crudo no
halla nada pero el parser sí ve `message/rfc822`, caer a `as_bytes()` y avisar (nunca
se pierde un email).

**Ficheros.** `core/email_export.py` (nuevas `iter_nested_originals`/`_iter_raw_rfc822`/
`_decode_cte`/`_iter_partes_hoja`/`_payload_message`/`_nested_con_fallback`/
`_aplana_anidados`; reescribir `split_eml`; `ExportReport` +2 contadores; `export_label`
+flag; `_emit_traza` +procedencia) · `scripts/export_label_emails.py` (flag CLI) ·
`tests/test_email_export.py` (bloque verificado + e2e con `_FakeService`).

**Pendiente operativo al cerrar.** Anotar la limitación del *boundary* compartido en
`docs/MEJORAS_FUTURAS.md`; reextraer W-02VND1 con `--force`; dejar `STATUS.md`/`PLAN.md`
al día con el hash del commit; re-empaquetar/re-importar la skill/plugin si el flag
afecta a la interfaz expuesta.

**Parte 2 (✅ HECHA, `911bf39`; plano `docs/PLAN_email_enlaces_drive.md`).** Emails/ficheros
que el consultor reenvía **como enlace a Drive/Gmail** en vez de `.eml` adjunto: se rescatan
byte-fieles vía Drive REST v3 (token `gdrive_ev`). Carpetas y docs nativos solo se anotan en
traza; binarios de descarga directa se descargan verificados por md5 (filtrando firmas); los
`.eml` reentran la Parte 1; otros binarios van a `_enlaces/` del padre (`source="drive_link"`).
Permalinks Gmail vía `format=raw`. Evento forense `upload_drive_link`. Scope `drive` del
remote confirmado en Fase 0. La instrucción operativa a los consultores (reenviar como
adjunto) sigue vigente para el flujo nuevo; la Parte 2 rescata el backlog histórico por enlace.

---

## [SIGUIENTE-EMAIL-ATOMIZE] Motor de atomización de correo (`core/email_atomize/`)
*Diseño aprobado por Nikolai 2026-06-24/25. Spec: `docs/superpowers/specs/2026-06-24-email-atomize-design.md`. Plan Fase 1: `docs/superpowers/plans/2026-06-24-email-atomize-fase1.md`. Implementación: Claude Code.*

Descompone `00_Input/03_Email/*.eml` a nivel de **mensaje atómico** → `01_Procesado/Emails/`
(`.md` por mensaje + frontmatter, adjuntos dedup sha256 + ficha, `corpus.jsonl`, `_registro.json`
con IDs congelados, `CORREOS_LECTURA.md`, `INDICE_ADJUNTOS.md`). Fin: recuperar la autoría
enterrada de PersonaUno (levantar el velo de Tibidabo 8 S.L.). Reutiliza `core.email_export`.

- [x] **Fase 1 — IDs + Capa A (MIME) + salidas.** Paquete `core/email_atomize/` (ids/headers/
  extract/dedup/bodies/attachments/render/corpus/pipeline) + CLI `scripts/atomize_emails.py`.
  +24 tests. **Corrida real W-02VND1: 277 mensajes, 162 adjuntos únicos (72 decorativos), 0
  errores, 0 mojibake, idempotente.** Commits `f468a55`→`04901ba` (spec `e9681c1`, plan `88439a2`).
- [x] **Fase 2 — Capa B (reenvíos/citas INLINE).** Diseño sintetizado por workflow adversarial +
  **revisión adversarial de código** (14 hallazgos confirmados, 8 HIGH, TODOS corregidos). `inline.py`
  + `_segmenter.py` (autoridad única autor/cita); segmentación HTML+plano, atribución SOLO desde
  cabecera contigua parseable (ES+CA+EN), confianza alta-reconstruida/media/baja con guardas
  anti-misatribución (ambigüedad, fecha-coherente, candidata→media, conservación de tokens),
  fingerprint día-granular, upgrade de fidelidad sin tocar Capa A, poda de huérfanos, cola `_revision/`.
  +53 tests. **Corrida real W-02VND1: 277 Capa A BYTE-IDÉNTICOS, +89 Capa B alta (0 misatribuciones
  auditadas), 84 a revisión, 6 upgrades, idempotente; PersonaUno 12 directos + 13 inline PROMOVIDOS
  (autoría enterrada recuperada).** Un bug de fecha enmascaraba el payoff (antes 14/0 → 89/13).
  Spec/plan `2026-06-25-email-atomize-layerb-{design,fase2}.md`.
- [x] **Fase 3 — capa de caso.** _CÓDIGO COMPLETO en `origin/main` (`14d8743`→`5b566ea`), vía subagent-driven + revisión adversarial=SHIP; suite 1255 verde. PENDIENTES (no parte de F3 / siguiente sesión): **Task 7** verificación EN VIVO sobre W-02VND1 en `G:` (nada escrito aún; necesita keywords del `nexo_causal` + autorización) y, en spec/plan SEPARADO, el **recall MSG-00018** + OCR de adjuntos._ `identidades.yaml` (mover `IDENTIDADES_VIGILADAS`; set de PersonaUno
  `per01a@example.invalid`/`per01c@example.invalid` confirmados, `per01b@example.invalid` candidato→tope media,
  `ignacio@despacho-ab.example` parte DISTINTA), mejor parser de fechas ES/CA + niveles
  profundos (subir recall PersonaUno), vistas temáticas (`dossier_del_burgo`, `vista_nexo_causal`),
  `_entregas/` selladas. OCR de adjuntos = posterior.

---

## [SIGUIENTE-CRONOLOGIA-UNIFICADA] Cronología Unificada de Prueba (capa por encima de los atomizadores)
*Diseño aportado por Nikolai 2026-06-25 (hilo Cowork). Spec **v7 — DISEÑO COMPLETO (8 fases, 0–7)**: `docs/superpowers/specs/2026-06-25-cronologia-unificada-design.md`. Banco de pruebas de diseño: W-02VND1 (Tibidabo 8). **Naturaleza: documento de DISEÑO, NO construcción.** Disciplina rectora: skill `verificacion-anclada-fuente`. Implementación: Claude Code en `core/` — **siguiente paso = BUILD, no más diseño.***

**Objetivo.** Fusionar todas las fuentes de prueba de un expediente (correo, WhatsApp,
CRM, entrevistas, documental, registros) en **UNA sola línea de tiempo**, separando lo
que **consta** en la prueba (capa canónica, anclada con pinpoint, estatus A/B) de lo que
se **infiere** de ella (capa derivada: hechos, relato, nexo causal, presunciones 385/386).
Vive **por encima** de los atomizadores por fuente (el motor `core/email_atomize/`,
**congelado**, es el primer adaptador) y **por encima** de `organizar-sala-lectura`
(nivel fichero); no los duplica ni los modifica.

**Decisiones de diseño cerradas (D1–D6 en el spec):**
- **D1 — átomo:** acto datado anclado a fuente (Modelo B, PROV-O Activity/Entity/Agent);
  nunca un hecho del mundo inferido. Confianza en 3 ejes (anclaje A–E · credibilidad ·
  fiabilidad de fuente).
- **D2 — almacén:** híbrido delgado (verbatim **en la fuente**, relación temporal en el
  almacén canónico) + pinpoint doble + `eventos.jsonl` regenerable + `_registro_cronologia.json`
  no-derivable. Salida prevista: `01_Procesado/Cronologia/`.
- **D3 — tres fichas:** Acto · Enlace (primitivo único, absorbe la correlación y las
  contradicciones) · Hecho derivado (alimenta `HECHOS_X.md` con semáforo 🟢🟡🔴 calculado del grafo).
- **D4 — IDs:** dos regímenes — congelados por contenido (`EVT-`/`ATT-`) y asignados/persistidos
  (`ENL-`/`HD-`/`ACT-`/`HIP-`); idempotentes, opacos, 5 dígitos.
- **D5 — actor:** formaliza `identidades.yaml` (identidad única + roles que cuelgan;
  calificaciones del velo = hechos derivados, no flags).
- **D6 — tipología:** categorías de alto nivel CERRADAS; hojas SEMILLA extensibles con gobernanza.

**Decisiones de Fase 3 cerradas (correlación entre fuentes — F3.D1–D5; §7 del spec).** Regla rectora: **intra-fuente DEDUP, inter-fuente CORRELACIÓN (nunca fusión).**
- **F3.D1 — desenlaces:** dos planos ortogonales (actos: Colapso/Correlación/Reconstrucción/Sin relación · artefactos §2.5); **sin nodo `EventoMaterial`** (sería puerta trasera de inferencia); corroboración de CONTENIDO vs CIRCULACIÓN se computan distinto.
- **F3.D2 — señales (S0–S5):** confianza de emparejamiento explicable ≠ fuerza probatoria; peso por rareza/diagnosticidad; bloqueo duro (ancla compartida) + blando (solo candidatea a revisión); flag `riesgo_tergiversacion`. **★ no-fuga:** el semáforo solo usa enlaces `confirmado`.
- **F3.D3 — enrutamiento:** AUTOENLACE (solo S0a-formal + hash idéntico) / COLA (recall-bias, tiers) / NO-PROPUESTO; la contradicción NUNCA se autoenlaza pero salta la compuerta; decisión humana **sticky y persistida** (en `_registro_cronologia.json`).
- **F3.D4 — fórmula del 🟢🟡🔴:** regla **estructural categórica** (no suma ponderada); independencia en 3 grados; diagnosticidad condicional (ACH); cadenas `min` por ruta + convergencia; topes por rival seria/credibilidad/386; salida **propuesta** que el letrado cura.
- **F3.D5 — contradicción:** el sistema **no resuelve**, representa el conflicto (versiones rivales bajo punto controvertido); tres dianas según `matiz_contradiccion` (contenido/credibilidad/autenticidad); degradación una sola vez en el nodo; resolución = evento nuevo.

**Decisiones de Fases 4–7 cerradas (v7 — DISEÑO COMPLETO; §8–§11 del spec).**
- **F4 — tiempo heterogéneo (§8):** la línea ancla el **tiempo del HECHO** (3 tiempos deslindados: no declarativo / narrativo→reconstruido subsidiario / performativo; el tiempo de REGISTRO = procedencia, nunca posición). Cronología = **ORDEN PARCIAL**: proyección a intervalo `[suelo, techo]` EDTF, 5 relaciones derivadas (antes/después/contiene/contenido_en/indeterminado), propagación TCN segura sobre constraints anclados (nunca muta `cuando.fecha`); consumo en prescripción (rango argumental, nunca fecha única), 386 (`requiere_precedencia` bloquea/degrada) y S4. Campos nuevos: solo `requiere_precedencia` + diagnóstico `inconsistencia_temporal_de_fuente`.
- **F5 — arquitectura de ingesta (§9):** **3 capas con frontera tajante** — ATOMIZADOR (por fuente, dueño de bytes; el motor de correo congelado ES el de "correo") · ADAPTADOR/PROYECTOR (delgado, mapea átomo→ficha de acto, emite tokens de actor sin elegir ganador, defaults deterministas nunca inferencia) · NÚCLEO AGNÓSTICO (asigna EVT-id, resuelve identidad, dedup/correla/tiempo/enlaces/vistas). El adaptador **nunca** asigna ids ni correlaciona. Anclaje **al crudo de `00_Input`+hash** (sala de lectura = pista débil); staging multi-fuente; llegadas tardías idempotentes; `90_Notas personales` = prohibición absoluta (ni listar).
- **F6 — vistas y custodia (§10):** entregable humano = `CRONOLOGIA_ACTOS` regenerable **"índice de lectura — NO prueba"** (una entrada/acto, extracto con ventana de contexto, cita = fuente+pinpoint, etiquetas separadas corroboración-de-contenido vs circulación, dossiers temáticos con bloque anti-sesgo); sellado de entrega a `_entregas/<fecha>/` en 3 bloques (prueba aportable con SHA-256 · apoyos demostrativos · manifiesto de custodia transversal), inmutable e incremental; work-product ≠ prueba, nunca mezclados.
- **F7 — alcance del piloto (§11):** primer build = **correo + WhatsApp y nada más** (atomizador+adaptador de WhatsApp para `02_Whatsapp`); objetivo = validar el núcleo agnóstico end-to-end; éxito = 3 hechos-test (correlación-no-fusión por dos canales · identidad atada por teléfono · punto controvertido de contenido y de fecha sin resolver). Ejecución: Claude Code local.

**Material build-ready (handoffs de stress-test) — COMPLETO en el repo 2026-06-25:** `docs/superpowers/specs/cronologia-handoffs/` contiene los **7** handoffs que cita el spec (F3.D4, F3.D5, F4.D1, F4.D2, F5.D1, F5.D2, F6.D1) verbatim + README (son los PROMPTS de revisión adversarial que validaron el diseño; las decisiones sintetizadas viven en el spec §7–§11). **F3.D4 y F3.D5** traen además el **pseudocódigo operativo** (`calcular_estatus_soporte` del 🟢🟡🔴 y `procesar_contradiccion`) — directamente build-ready.

**Estado (DISEÑO).**
- [x] Fase 0 — inventario de fuentes.
- [x] Fase 1 — esquema del evento (D1, D2, D3, D4, D6).
- [x] Fase 2 — identidades (D5).
- [x] **Fase 3 — correlación entre fuentes (F3.D1–D5).** Algoritmo y reglas cerrados (§7 del spec); ver bloque de decisiones arriba.
- [x] **Fase 4 — tiempo heterogéneo (F4.D1–D2).** Tres tiempos del evento + orden parcial / intervalos EDTF (§8 del spec).
- [x] **Fase 5 — arquitectura de ingesta (F5.D1–D2).** Atomizador / adaptador / núcleo agnóstico; anclaje al crudo (§9 del spec).
- [x] **Fase 6 — vistas, entregable humano + custodia (F6.D1–D2).** `CRONOLOGIA_ACTOS` + sellado de entrega (§10 del spec).
- [x] **Fase 7 — alcance del piloto (F7.D1).** Correo + WhatsApp; 3 hechos-test (§11 del spec).

**Siguiente paso = BUILD (diseño COMPLETO).** Cerradas las 8 fases de diseño (0–7), el
siguiente paso ya no es diseñar sino **construir** en `core/` de FeesDefender (Claude Code,
local), incremental (correo + WhatsApp primero), con el motor de correo congelado como
primer adaptador. **Dependencia operativa:** conviene tener el motor de correo terminado
(hoy `[SIGUIENTE-EMAIL-ATOMIZE]` está en Fase 3) antes de arrancar el piloto. La cronología
**consume** sus salidas (`mensajes/*.md`, `corpus.jsonl`, `_registro.json`) y **no lo toca**
(spec congelado).

**Prompt de arranque del BUILD** (registrado 2026-06-25): `docs/superpowers/plans/2026-06-25-cronologia-build-arranque.md`.
**Orden de build** (incremental, con tests en cada paso): (1) motor de correo = primer
atomizador en `core/`, con pasada de medición previa sobre datos reales; (2) esqueleto del
núcleo agnóstico (ficha del acto §3.1, `_registro_cronologia.json`, IDs `EVT-/ATT-/ENL-/HD-/ACT-/HIP-`,
resolución de identidad contra `identidades.yaml`, contrato de staging); (3) adaptador-lector
de correo (solo lectura sobre el motor congelado); (4) atomizador + adaptador de WhatsApp
(`00_Input/02_Whatsapp`, formato iOS); (5) piloto end-to-end correo + WhatsApp → `CRONOLOGIA_ACTOS`
+ dossier del velo, validando los 3 hechos-test (F7.D1). *El arranque cita el spec como
`PLAN_CRONOLOGIA_UNIFICADA.md`; en el repo es `docs/superpowers/specs/2026-06-25-cronologia-unificada-design.md`.*

---

## [SIGUIENTE-SALA-UNICA-PLANA] Sala de lectura única, plana y prompt-driven (todo `00_Input`)
*Decisión cerrada con Nikolai 2026-06-18 (este hilo). RGPD aprobado por el responsable del tratamiento. Spec + plan de implementación DIFERIDOS (Nikolai aportará más contexto desde otro hilo). Enlaces: `MEJORAS #34` (vehículo: skill-Cowork multiusuario), `#35` (bundle WhatsApp chat+media), `#36` (guarda de colisión), `#38` (fecha de contenido vs mtime), `#37`/`#39` (deprecación).*

> **[IMPLEMENTADO y MERGEADO 2026-06-18 — pero con PIVOTE PENDIENTE]** Spec
> `docs/superpowers/specs/2026-06-18-sala-lectura-unica-design.md` + plan
> `docs/superpowers/plans/2026-06-18-sala-lectura-unica.md`. Feature mergeada a `main`
> por FF (13 commits `a53ca42`→`51b6653`, sin push): skill `organizar-sala-lectura`
> v1.3 (plana, todo `00_Input`) + `triaje-viabilidad` v1.1 + canon/sync/gate + helper
> de catálogo + core de sala deprecado. Revisor final APPROVED; suite verde.
> **⚠️ La corrida real en Cowork (BaRS1) tardó ~53 min** — el conector de Drive es
> per-fichero (ver `DEAD_ENDS.md`). **DECISIÓN ABIERTA (manda sobre el resto):** pivotar
> a **motor local plano primario** sobre el montaje `G:` (Drive for Desktop) —filesystem,
> disparo por CLI/Streamlit/skill en Claude Code local—, dejando la skill de Cowork como
> **fallback puro-nube**. **Bloqueado por:** ¿el equipo (Paola incl.) trabaja con el
> montaje `G:`? Si sí → des-deprecar el motor y portar `poblar_sala_lectura` a la
> estructura plana. **Pendiente operativo:** re-import `.skill` v1.3/v1.1 en Cowork.
>
> **✅ Vía rápida lado Claude Code lista (2026-06-22):** MCP filesystem local
> **`expedientes`** sobre `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL`
> (`@modelcontextprotocol/server-filesystem`, global + `cmd /c`, modo Mirror = todo en
> disco). Lectura a velocidad de disco (~1,1 s un caso de 928 ficheros, vs ~53 min por
> el conector). **Permite ya** correr la skill `organizar-sala-lectura` **prompt-driven
> en Claude Code local** sobre el Drive sin el conector per-fichero — desbloquea el lado
> Code del pivote SIN portar todavía el motor Python. NO escribe nada que no se le pida,
> pero el server-filesystem **sí puede escribir/borrar** en `G:` (incluida `90_Notas
> personales` + riesgo de duplicados por el sync de Drive): se asume, no se limitó a
> solo-lectura (decisión de Nikolai 2026-06-22). Montaje
> documentado en `DEAD_ENDS.md` y memoria `reference-expedientes-filesystem-mcp`.
>
> **⚠️ CORRECCIÓN 2026-06-22 — Cowork TAMBIÉN puede usar el MCP local (se creía que no):**
> añadido el mismo server al `mcpServers` de `%APPDATA%\Claude\claude_desktop_config.json`,
> **Cowork cargó la integración `expedientes` y listó 273 ficheros de BaRS1 en segundos.**
> El supuesto "Cowork solo ve Google Drive" era FALSO: **Claude Desktop (app local) hace de
> puente** y lanza los stdio MCP locales en el PC. Los ~53 min fueron por usar el **conector
> remoto** de Drive, no por falta de acceso al disco. **Implicación para este pivote:** la
> sala puede correr rápido en Cowork **en el PC de Nikolai** apuntando la skill al MCP local
> `expedientes` en vez del conector — sin portar el motor Python ni montar servidor remoto.
> **Límite que persiste:** solo donde Claude Desktop corre en el PC con el montaje `G:`;
> Cowork móvil/navegador o las PC de Paola/Ana sin montaje+`mcpServers` seguirían necesitando
> un MCP **remoto** en servidor (ahí sí queda la fase aparte).

**Decisión.** Unificar las **dos** salas de lectura hoy convivientes en `01_Procesado/`
(la `Sala lectura Drive EV` de la skill Cowork —solo Drive EV, por categoría— y la
`Sala lectura` del motor —todo `00_Input`, por fuente—) en **UNA sola `Sala lectura`**,
poseída por la **skill (Cowork, prompt-driven) aplicada a TODO `00_Input`**. El motor
deja de poblar la sala (es un artefacto-hoja: **nada del core la lee**; el pipeline
confidencial extractor→`MD/`→anon→`06`→frontier es independiente y se mantiene).
Resuelve `MEJORAS #34`: Paola y cualquiera la ejecutan desde Cowork sobre el Drive,
sin Python local ni dependencia del PC de Nikolai.

**Estructura canónica (fijada).** Plana, sin slug de categoría, cronológica:
- Fichero: `<AAAA-MM-DD>_<descripcion_guiones_bajos>.ext` (fecha ISO + descripción
  legible, sin PII, sin prefijo de categoría).
- **Documento compuesto** (con anexos) = **subcarpeta** con el mismo nombre del
  principal (`<AAAA-MM-DD>_<descripcion>/`, fecha ISO en la carpeta → se intercala
  cronológicamente), conteniendo el principal + sus anexos (`<principal>_anexo_<N>_…`).
  Documentos sueltos → ficheros planos en la raíz.
- La **taxonomía E&V deja de vivir en las carpetas** y pasa a `INDICE.md` (vista por
  categoría) + `CRONOLOGIA.md` (ascendente) + `_MANIFIESTO.md` (sha256 · original ·
  canónico · categoría · fecha). La **fuente** se conserva en el manifiesto/catálogo
  e índices (no se pierde al quitar las carpetas por fuente).

**Decisiones cerradas (Nikolai, este hilo):**
- **RGPD:** APROBADO que la skill lea **todo `00_Input` en claro** (incl. WhatsApp,
  email, entrevistas), vía Cowork/Claude, ejecutado por Paola y otros. Extiende la
  excepción de `MEJORAS #34` (más fuentes y usuarios); autorizado por el responsable.
- **Catálogo:** se **conserva** `indice_documental.yaml` como SSOT, escrito por un
  helper de la skill (evita la doble verdad con `_MANIFIESTO.md`; deja la puerta a El
  Auditor y a la persistencia de bundles `parent_id`).
- **Bundles:** estructurales en la skill (WhatsApp chat+`media/` `#35`; email
  cuerpo+adjuntos por MIME); los **CRM** quedan "mejor esfuerzo" (Cowork no ve el
  `modified_at` del CRM que usa `conjunto_detector`).
- **Modelo:** la skill se ejecuta con **Sonnet/Haiku, NO Opus** (clasificación atómica;
  hay visto bueno humano y lo ambiguo→`08. PENDIENTE`). Nota de uso en la skill +
  prompt ligero. El grueso de la velocidad lo da el skip incremental (abajo).
- **2ª pasada idempotente (sin duplicar trabajo):** skip por **`md5Checksum`** en
  `_MANIFIESTO.md` (hash de contenido, no nombre). Coste ∝ documentos **nuevos**; si
  no hay nada nuevo → casi instantánea (listar + comparar hashes + re-render índices).
  Respeta ajustes manuales (no pisa lo ya colocado). Incluir el fix de `#38` (la fecha
  de contenido de actos fechados —escrituras, poderes, contratos, burofax— prevalece
  sobre `mtime`, que queda como último recurso marcado).
- **Deprecación:** el camino de sala en el core —`clasificar_caso`/`aplicar_clasificacion`/
  `render_indices`/`poblar_sala_lectura` y **`clasificar_residuo_llm` (`#37`)**— queda
  **superado por la skill** (marcar deprecado, no borrar de golpe). Se conservan los
  fixes de esta sesión (`build_catalog` `45dd5ad`, OCR-OOM `2eeec1a`) porque sirven al
  pipeline confidencial. Reevaluar `#39` (OCR local) ya que la skill esquiva el OCR
  local para la sala (usa la extracción del conector de Drive).

**Lectores de la sala:** `triaje-viabilidad` (la lee; corregir su referencia interna
`02_Sala lectura/` → sala única). `viabilidad-prerelleno` **no se toca** (lee `00_Input`
directo). 

**Reemplaza** el enfoque core de `[SIGUIENTE-SALA-LECTURA-01]` y `[SIGUIENTE-RESIDUO-LLM]`
para la población de la sala (esos quedan como histórico del prototipo que validó el
enfoque y destapó los dos bugs corregidos).

- [ ] **Pendiente:** spec de diseño (`docs/superpowers/specs/`) + plan de implementación
  de la skill. **En espera del contexto adicional de Nikolai (otro hilo).** No empezar hasta entonces.

---

## [SIGUIENTE-RESIDUO-LLM] Clasificador LLM del residuo de intake (`MEJORAS #37`)
*Promovido 2026-06-18 por petición de Nikolai (Cowork). `MEJORAS #37`. Implementación: Claude Code.*

**Objetivo.** Cerrar el único paso humano que queda en la sala de lectura: rellenar
la worklist del residuo `01_Procesado/_revisar/_clasificar.md`. Paso **opcional**
`clasificar_residuo_llm(case_id)` que, SOLO sobre las entradas en residuo (las que
`clasificar_caso` no resolvió por nombre/imagen), lee el `.md` del texto extraído de
cada documento y autorrellena las columnas de la worklist (tipo documental, fecha,
parte, descripción). El letrado valida antes de `aplicar_clasificacion`, que sigue
siendo el **único** camino al catálogo canónico `indice_documental.yaml`.

**Restricciones (heredadas de la arquitectura).** La lógica vive en el core; el LLM
ocupa exactamente el slot humano de la worklist (no inventa estructura). Clasifica
solo lo que ve (regla de la casa: no inventar); lo de baja confianza se deja sin
rellenar (marcado para revisión), no se adivina. No toca la clasificación
determinista ni el esquema de la worklist. Idempotente; no pisa lo ya clasificado
por humano. Reutiliza `core/llm_cloud.py`.

**RGPD (cruza con #34/#27).** Extiende la excepción de lectura en claro por LLM. La
posición concreta (proveedor + qué texto lee + exposición en Streamlit) la fija
Nikolai al abrir el hilo de implementación (decisión abierta, ver hilo de Claude
Code).

**Decisión de Nikolai (2026-06-18):** resolver el residuo **desde Claude-en-sesión**
(ya pagado), **sin API externa de pago** (ni Scaleway ni Claude API) y **sin botón
Streamlit**. Encaja con la excepción RGPD §2 ya autorizada (Claude lee `MD/` en
claro); no abre terreno RGPD nuevo. El conector de pago (`make_llm_cloud_chat_fn`
sobre `core/llm_cloud.py`) queda OPT-IN para el futuro DPA.

- [x] Implementación (`preparar_residuo` + `rellenar_worklist` +
  `clasificar_residuo_llm` con `chat_fn` inyectable obligatorio + adaptador
  `make_llm_cloud_chat_fn` opt-in) + disparo headless (`preparar-residuo` /
  `clasificar-residuo [--connector]` en `scripts/sala_lectura.py`). `742e35a`.
  (No se cabló en `run_pipeline.py` ni Streamlit: forzaría el camino de API,
  contrario a la decisión.)
- [x] Tests (+9, LLM mockeado): residuo rellenado, baja confianza sin rellenar,
  idempotencia, no se pisa celda humana, Tipo/Parte inválidos, doc sin MD omitido,
  chat_fn obligatorio, adaptador llm_cloud. Suite 1008 passed / 58 skipped. `742e35a`.

---

## [SIGUIENTE-SALA-LECTURA-01] Sala de lectura y organización de `01_Procesado`
*Diseño cerrado con Nikolai 2026-06-12 (sesión Cowork, HANDOFF). Plan fino autocontenido: `docs/PLAN_SALA_LECTURA_01_PROCESADO.md` (incluye §0 con notas de Claude Code sobre el estado del repo). Implementación: Claude Code.*

**Objetivo.** Capa humana sobre `01_Procesado`: una **sala de lectura** (documentos
en claro y en orden, por fuente y narrativa) + una **capa de texto** (`MD/`) para
búsqueda. Índices `INDICE.md`/`CRONOLOGIA.md` de solo lectura. Clasificador/fechador
**híbrido** (reglas deterministas → LLM Scaleway solo para el residuo). `00_Input`
intacto; ningún camino de IA accede a `01`. Primera fase = ficheros en
`01_Procesado`; Streamlit y artifact Cowork **diferidos**.

**Acoplamientos detectados al leer el repo (doc §0, fijan la secuencia — no bloquean):**
- **#1 (cimiento):** la sala de lectura **es** `[SIGUIENTE-CATALOGO-DOCUMENTAL]`.
  `INDICE.md`/`CRONOLOGIA.md` se renderizan desde `indice_documental.yaml`, que
  **no existe** (Nikolai: "no construirlo a medias"). Construir la sala obliga a
  construir el catálogo. Falta añadirle `parent_id`/`orden_en_bundle` (D9 / MEJORAS #29).
- **#2:** el `_manifiesto.jsonl` del handoff solapa con `00_Input/_intake_hashes.json`
  (`IntakeManifest`) ya existente. Decisión: ¿catálogo único o tres artefactos?
  Inclinación: **catálogo único**.
- **#3:** el clasificador (Tarea 7) lee documento en claro → **misma excepción RGPD
  acotada** que el intake de procuradores (Scaleway UE). Maximizar reglas
  deterministas (filename, `id_carpeta_label`, `modified_at` ya en el DTO por D10).
  **Bloqueante solo de Tarea 7:** DPA Scaleway.
- **Menor:** apoyarse en `[IDEA-SKIP-INCREMENTAL-EXTRACCION]` #1 (doble `extract_all`)
  para cumplir el criterio de idempotencia; el grifo de MD (Tarea 2) toca el mismo flujo.

**Secuencia propuesta (doc §0.F):**
> - [x] **(0) cerrar doble `extract_all`** — ya cerrado s32; verificado s48.
> - [x] **(1) catálogo `indice_documental.yaml`** — `core/catalogo_documental.py` (`f253a84`).
>   Artefacto independiente; reconciliación con `_intake_hashes.json` **diferida**.
> - [x] **(2) scaffolding `Sala lectura/`+`MD/`+`_revisar/`** — en `ensure_case` (`f253a84`).
> - [x] **(3) grifo de MD en claro a `01_Procesado/MD/`** — `markdown_generator.build` +
>   consumidores `scorer.py`/`viability.py` (`f253a84`).
> - [ ] (4) copiador organizado + bundles (consumiendo `conjunto_detector`)
> - [ ] (5) render de índices
> - [ ] (6) clasificador híbrido (tras DPA)
>
> Cada fase con tests y suite verde.

**Decisiones abiertas (doc §0.G):** catálogo
único vs manifiesto aparte (diferida) · taxonomía documental (la redacta Cowork;
bloquea afinar el clasificador, no el cimiento) · DPA Scaleway (bloquea solo
Tarea 7) · correspondencia suelta.

---

## ✅ [INTAKE-WHATSAPP-FASE-A] Intake de chats de WhatsApp — Fase A (UI Streamlit)
*Diseño aprobado 2026-06-15. Spec: `docs/superpowers/specs/2026-06-15-intake-whatsapp-design.md`. Plan: `docs/superpowers/plans/2026-06-15-intake-whatsapp-fase-a.md`. Implementación: Claude Code, rama `feat/whatsapp-faseA`.*

**Fase A COMPLETA (2026-06-17).** Parser puro `core/whatsapp_export.py` (iOS/Android,
2/4 cifras, 12/24h, multilínea, sistema, adjuntos, filtro por fechas) + glue
`core/whatsapp_intake.py` (analyze + deposit_export, depósito verbatim + zip
original + IntakeManifest dedup por hash + evento `upload_whatsapp`) + expander
«📲 Importar chat de WhatsApp» en el tab Casos de `streamlit_app.py` (multi-zip,
rol por chat, previsualización, aviso de adjuntos faltantes/audios diferidos).
Commits: `3734dcb` → `8b5bb42` → `2db5617` → `1a64fb4` → `aa4904f` → `6963ec5`
→ `3e64dd5` → `cf26b2a` (spec review fix). Tests: +25 (16 parser + 9 glue).
Suite: **955 passed, 58 skipped** (5 fallos preexistentes en
`test_sudespacho_relations.py` — ajenos).

**Fase B (email) y transcripción de audio diferidas** — fuera de alcance de Fase A,
reutilizan el parser sin cambios.

---

## ✅ [ESTILO-DE-LA-CASA] Infraestructura de escritura del despacho (claridad + persuasión + no-IA)
*Plano: `PLANO_Code_skill_estilo_casa.md`. Decisiones de Nikolai + recomendaciones de Code. Implementación: Claude Code, 2026-06-17.*

**COMPLETA (2026-06-17).** Dos capas. **Capa 1:** contrato canónico
`data/_estilo/contrato_estilo.md` (instrucción para modelo; 3 capas + regla de oro
claridad ⟂ precisión —gana la precisión— + opera dentro del formato Sala 1ª TS).
**Capa 2:** skill `pase-de-estilo` (`transversal`/`atomica`, núcleo + identidad, sin
módulos ni telemetría; valida OK; references `claridad_es.md` + `tics_ia_es.md` (81
patrones) + `persuasion_es.md` (34 técnicas) + `registros.md` placeholder; versión
final + tabla de cambios + traza; guardarraíl de reordenación afinado —frase
intra-fundamento permitida, esqueleto solo propuesto—; cita vaga remitida a
`verificacion-anclada-fuente`, no inventa). Test lean con-skill vs baseline:
guardarraíles OK. **Enganche (prosa):** puntero capa 1 + `pase-de-estilo` capa 2 en
las 5 procesales (`escritos-judiciales` —+ línea nueva `verificacion-anclada-fuente`,
único hueco—, `oposicion`, `preparacion-litigio-civil`/`-audiencia-previa`/`-juicio-oral`);
línea always-on en `CLAUDE.md`; módulo **ESTILO + VERIFICACIÓN** en `_plantilla-skill`
(las skills nuevas nacen con ambos concerns en `requires`). `.skill` en `dist/skills/`.
**Pendiente:** reimport en servidor (manual, Cowork/claude.ai); corpus de voz real
(`registros.md`, Fase E, lo aporta Nikolai). **Diferido:** `requires` en las 5 skills
viejas (prosa ahora, retrofit de identidad único futuro); enforcement en
`validate_skills.py`.

---

## [SIGUIENTE-INTAKE-PROCURADORES-EMAIL] Intake automático de correos de procuradores → Sudespacho
*Diseño cerrado con Nikolai 2026-06-12. Plan fino autocontenido: `docs/PLAN_INTAKE_PROCURADORES_EMAIL.md`. Implementación: Claude Code.*

**Objetivo.** Sentido inverso del intake actual: archivar en el CRM los correos de
procuradores (y contestaciones a correos del despacho), relacionarlos con su
expediente y subir adjuntos con nombre legible, con red de seguridad humana antes
de escribir. Llave de emparejamiento = *Su ref* (= `num_expediente/serie`,
serie=año). **RGPD — excepción acotada SOLO a este flujo:** usa LLM cloud UE
(Scaleway/Mistral Small 3.2); no deroga la regla general del resto del repo.

**Estado por fases (detalle en el doc §15):**
- **F1 — Matcher (read-only).** ✅ HECHA (s39, 2026-06-12). `core/llm_cloud.py`
  (conector LLM cloud intercambiable) + `core/procurador_intake.py` (señales LLM +
  match por num/serie vía REST + propuesta de nombres). Validado e2e contra correos
  reales (ProcuradoraF 21/25→exp #532, Castañeda 33/2024→exp #455, ambos confianza
  ALTA). API `element_registries` usa `hydra:member`. Volumen ~7 correos/día,
  ~€0.10/mes. Tests +77; suite **853 passed, 58 skipped**. **Commits `f904d72`,
  `6a811ef`** (F1 base + fix match por su_ref con sufijo de subserie y `es_ruido`
  advisory).
- **F2 — Bandeja (Streamlit).** ✅ BACKEND ✅ / UI ✅. **Backend (s40, dry-run, TDD):**
  `core/procurador_review.py` (terna §18.9 + divergencia + log auditoría + máquina de
  estados de cola + store de cola), `core/procurador_runner.py` (process_email +
  run_intake, enrutado §6, dedup §4), `core/gmail_source.py` (adaptador Gmail
  verificado live read-only). Commits `a80afeb`/`00ee3b8`/`7b03759`/`3bedb22`/`95082f1`.
  El **requisito duro §18.9** quedó cumplido: la terna se captura en `record_decision`.
  **UI + CLI completados** (branch `feat/intake-procuradores-f2-ui`, plan/spec en
  `docs/superpowers/`): contexto de tarjeta persistido en la cola (`9490eca`),
  `fetch_expediente_datos`/`recompute_coincidencias` (`945030b`/`15df2f2`), CLI thin
  `scripts/intake_procuradores.py` sobre `fetch_and_run` (`1f336dc`), pestaña Streamlit
  «Bandeja de correos» (3 tarjetas 🟢/🟡/🔴 + login `set_actor` + acciones→
  `transicionar`/`record_decision`/`upsert_queue_item` + combobox de reasignación +
  vista Descartados) (`cbfafba`/`3b24f45`). **`search_expedientes` migrado a REST**
  (`feat/search-expedientes-rest`, fusionado): el probe contra el CRM real demostró que
  el autocomplete legacy devuelve body vacío (`DEAD_ENDS.md`); búsqueda por
  `referencia_cliente`+`referencia_procurador`+nº/serie, sin `clientes`; búsqueda por
  contrario/autos fuera de alcance (`MEJORAS_FUTURAS.md` §31). Suite **935 passed**.
- **F3 — Escritura en el CRM.** ⬜ Resolver auth nest-mail (x-api-key vs JWT);
  relate + adjuntar en expediente de prueba. Mismo requisito de traza que F2.
- **F4 — Renombrado + OCR + aprendizaje.** ⬜ Contenido del adjunto → nombre; store
  de correcciones few-shot (§10).
- **F5 — Grabaciones.** ⬜ Descarga de enlaces (WeTransfer caduca) + fallback manual.
- **F6 — Control de calidad del archivo (check 2).** ⬜ Capa de auditoría por
  excepción (auto-chequeo determinista + cola de Paola + resumen semanal a Nikolai).
  **Diseño cerrado 2026-06-12, doc §18.** Depende de F2/F3 (consume la terna de traza).

**Pendientes de decisión (doc §17 + §18.11):** ¿confirmar en bloque las de alta de
inicio? · auth nest-mail · plazos de escalado de la cola por tipo · tamaño de muestra
(default 10%) · lista de "tipos con plazo".

---

## [SIGUIENTE-INTAKE-JUDICIAL-AUTO] Intake automático de demanda y contestación desde el CRM
*Añadido 2026-06-10 (sesión Cowork). Implementación: Claude Code. Engloba y resuelve `[CRITICO-PRESIGNED-DOWNLOAD-BUG]` como su Fase 0.*

**Objetivo:** intake end-to-end de los dos documentos judiciales clave de un
expediente —demanda y contestación— desde el Gestor Documental del CRM hasta el
árbol del caso, sin el workaround manual (descarga SPA + expander Streamlit).
Flujo: localizar expediente judicial → identificar demanda y contestación →
descargar → depositar en cajón CRM → encadenar pipeline (anon → MD → frontier)
con dedup (M9) y log (M10, `_intake_log.jsonl`).

**Contexto verificado (sesión Cowork 2026-06-10, lectura de `core/sync_sudespacho.py`):**
- Listado OK: `list_gdocu_docs_rest` (`GET /api/element_registries/gdocu`) →
  `GdocuDocInfo(doc_id, filename, id_carpeta, id_carpeta_label, mime, size, raw)`;
  `id_carpeta_label` trae etiquetas tipo `"CIVIL"`.
- Descarga ROTA: `get_presigned_download_url` usa `ENDPOINTS["presigned_download_url"]`
  = `/api/files/presigned_download_url/{doc_id}` → HTTP 400. Es el bug crítico.
- PISTA: existe declarado pero **sin usar** `ENDPOINTS["presigned_download"]` =
  `/api/documents/presigned_urls/{service}/download/{documentId}` (`service="s3"`),
  mencionado en el docstring de cabecera → primer candidato a probar.
- Demanda/contestación viven en namespace `expedientes_judiciales` (ids no
  comparables con `expedientes_extrajudiciales`). Banco de pruebas: expediente 649 (BaRR3, 26 docs).

**Fases:**
- **Fase 0 (bloqueante) — desbloquear descarga.** ✅ HECHA (2026-06-10). La ruta
  alternativa del plan (`presigned_urls/s3/download`) **también estaba rota** (500);
  el endpoint vivo es `GET /api/documents/{id}/downloadUri` → `presignedDownloadUrl`.
  `get_presigned_download_url` reescrito, `docs/DEAD_ENDS.md` actualizado.
  Cierre cumplido: **31/31** docs del expediente 649 (creció desde 26) ✓.
- **Fase 1 — identificación.** ✅ HECHA. `core/judicial_classifier.py`:
  heurística regex source-locked **solo por `filename`** (la `id_carpeta_label`
  resultó demasiado gruesa — las carpetas DEMANDA/OPOSICION del CRM contienen
  toda la prueba; descubierto en el e2e del 649). Colapso de duplicados
  .pdf/.docx. Casos 0/múltiples → `[PENDIENTE revisión letrado]`, nunca adivina.
  Hook `llm_fn` inyectable pero **sin LLM por defecto** (decisión de Nikolai;
  RGPD: ningún nombre con PII sale del entorno).
- **Fase 2 — routing + pipeline.** ✅ HECHA. `core/judicial_intake.py`
  reutiliza `pull_expediente_v2` (nuevo param `only_doc_ids`) → dedup M9, log
  M10, routing `crm_branch_path`, estado D8. Solo baja demanda+contestación;
  `documents_total_crm` sigue siendo el total real. Pipeline encadenado por el
  caller (`--run-pipeline` / checkbox).
- **Fase 3 — disparo.** ✅ HECHA. CLI `intake-judicial --case --expediente
  [--run-pipeline]` + **botón** en el tab Casos de Streamlit
  («⚖️ Intake judicial automático»).
- **Fase 4 — tests y cierre.** ✅ HECHA. Tests del clasificador (con etiquetas
  reales del 649 como regresión) + orquestador. E2E real: demanda 40022
  auto-depositada, contestación marcada pendiente (2 candidatos). Suite verde.

**Decisiones cerradas (2026-06-10, con Nikolai):**
- Clasificación: heurística por `filename` (la etiqueta de carpeta NO dispara).
  **Sin LLM** — la ambigüedad va a revisión del letrado (RGPD-local).
- Disparo: **CLI + botón Streamlit**.

**Siguiente acordado — `[SIGUIENTE-INTAKE-CRM-COMPLETO]` (sesión 2026-06-10):**
bajar TODO el expediente del CRM a `05_CRM` físicamente completo (sin que el
dedup M9 lo deje incompleto) + OCR/markdown/anonimización con el pipeline actual
+ contador de solapamientos byte-idénticos (para decidir con datos si el "dedup
en extracción" merece construirse, que queda APLAZADO). Plan fino autocontenido
para hilo nuevo: **`docs/PLAN_INTAKE_CRM_COMPLETO.md`**.
- **Paso 1 (bajar todo + `physical_complete` + contador `documents_overlap`) HECHO
  en código** (`pull_expediente_v2`, `intake_demanda_contestacion(full=…)`,
  `intake-judicial --full`); falta cierre formal (`✅` + hash del PR).
- **Paso 2 (procesado) SUPERSEDIDO** por las salas nuevas (no `pipeline.run`); la
  reconsideración formal del motor/ejes queda **aparcada** en
  `[APARCADO-INTAKE-CRM-A-LLM]` (abajo).

**Siguiente acordado — `[SIGUIENTE-DEDUP-GUARD-ROBUSTO]` (apuntado 2026-06-10):**
guarda para **no duplicar expedientes ni en el CRM ni en el Drive** al crear un
caso. Hoy es frágil a variaciones tipográficas de la referencia/nombre.

- **Problema detectado (2026-06-10):** el botón «Crear caso + enviar a sudespacho»
  NO bloquea el expediente 444 porque su `referencia_cliente` en el CRM tiene un
  **doble espacio** (`(W-02NV4W)  - Vuelta`) y el case_id estándar lleva uno solo
  → la búsqueda exacta `find_expediente_judicial_by_referencia` devuelve `None` →
  **crearía un expediente duplicado**.
- **Qué hacer:**
  1. **Guarda CRM** (`core/sudespacho_relations.py`,
     `find_expediente_*_by_referencia` / `verify_expediente_referencia`):
     comparar referencias **normalizadas** (espacios repetidos colapsados, sin
     acentos, sin distinción de mayúsculas; reutilizar `_normalize_label`).
  2. **Guarda Drive** (`core/intake_drive.py`): aplicar la misma normalización al
     emparejar caso ↔ carpeta E&V por nombre/referencia, para no crear/pullar a
     una carpeta duplicada (revisar dónde se hace el match).
  3. **UI** (`streamlit_app.py` ~L1675): el aviso «no se creará un expediente
     duplicado» es **engañoso** — mira el `_caso.md` local y NO impide la
     creación; la única protección real es la búsqueda en el CRM. Corregir el
     texto y/o hacer que la guarda CRM realmente bloquee.
- **Riesgo si no se hace:** expedientes/carpetas duplicados, caros de deshacer.

---

## [APARCADO-INTAKE-CRM-A-LLM] Cadena CRM Gdocu → salas → registros → LLM
*Abierto 2026-07-10 (Nikolai); **APARCADO 2026-07-10** tras re-brainstorming con superpowers.
Doc: `docs/superpowers/specs/2026-07-10-intake-crm-a-llm-design.md` (banner APARCADO, mergeado
PR #19). Detalle del re-brainstorming en el comentario del PR #19.*

**Estado: APARCADA la construcción de los ejes** (decisión de Nikolai). Motivo: el proceso
(intake CRM → sala de máquina → sala de lectura → registros) **no está rodado** para decidir
sobre datos reales; el ROI en €/tiempo del doc (§5.3/§8) es estimación **sin medir**. No se
promueve a plan de implementación.

**Qué conserva valor (mergeado, no se retoca):** el runbook end-to-end y el mapa de estado
verificado del flujo (§1–3 del doc). El §4–8 queda archivado como brainstorming.

**Hallazgos (si se reabre, no re-derivar):** "eficiencia de tokens" no es objetivo (Claude-en-
sesión: solo muerde por caber en contexto); `scorer`→`viability` es **código muerto** sobre el
MD viejo (el flujo vivo es la skill leyendo crudo `00_Input/`); dolor único confirmado =
babysitting de casos grandes, **0 decisiones malas observadas**; de los ejes, **E2 (leer MD) es
el portante**, E3 marginal + gate extra, E4 no toca el babysitting (reutilización aguas abajo),
E5 descartado; anti-correlación sospechada (grandes = testificales, document-dependent =
pequeños y ya caben).

**Si se reabre:** probar **E2-sola, opt-in, disparada por tamaño** — NO el trío E2+E3+E4.
**Disparadores:** (a) un go/no-go real poco fiable por desbordar; (b) volumen suficiente para
medir la distribución de tamaños de caso; (c) haber cronometrado UNA corrida local (intake +
`sala_maquina apply` + lectura).

**Higiene independiente (sigue pendiente, NO aparcada):** cerrar formalmente el Paso 1 de
`[SIGUIENTE-INTAKE-CRM-COMPLETO]` (hecho en código, falta `✅` + hash).

---

## [SIGUIENTE-INTAKE-ENTREVISTAS] Intake dedicado de entrevistas (transcripción Meet) en `06_Entrevistas/`
*Promovido 2026-06-10 (sesión Cowork) por decisión de Nikolai. `MEJORAS #26`. Implementación: Claude Code.*

**Objetivo.** Cablear la subida de la entrevista de viabilidad (grabada en Google
Meet, transcripción automática) al árbol del caso, hoy sin conectar.

**Estado verificado (repo, 2026-06-10).** El andamiaje existe pero está muerto:
`ensure_case` crea `00_Input/06_Entrevistas/`; `ENTREVISTA_ROLES`
(`core/config.py`) y la convención `<AAAA-MM-DD>_<rol>_<apellido>/` están
definidas pero **ningún código las consume ni valida**; el evento
`upload_entrevista` (`core/intake_log.py`) y el source `"entrevista"`
(`core/intake_manifest.py`) están declarados pero **nunca se emiten**. No existe
`core/intake_entrevista*.py` ni uploader en Streamlit. El paso 7 del refactor v2
solo cableó el expander de subida a `05_CRM`. Hoy la entrevista solo entra si el
letrado deja manualmente la transcripción en la carpeta, sin dedup ni traza.

**Solución (ya recogida en `docs/MEJORAS_FUTURAS.md` §26).** No requiere
transcripción local (Whisper): Meet ya entrega texto. Dos piezas:

1. **Función de ingesta** (`core/intake_entrevista.py` nuevo o ampliación de
   `core/intake_manual.py`): dado rol ∈ `ENTREVISTA_ROLES`, apellido, fecha y el
   Doc de Meet, crea `06_Entrevistas/<AAAA-MM-DD>_<rol>_<apellido>/`, coloca la
   transcripción exportada a `.docx`/`.txt`, la registra en el manifest con
   `source="entrevista"` y emite el evento `upload_entrevista`. Validar rol contra
   `ENTREVISTA_ROLES` y sanear el path como en `save_file_crm_branch`.
2. **Disparo en la UI** (expander/botón en el tab Casos de Streamlit), análogo al
   de `05_CRM`.

Una vez el `.docx`/`.txt` está en `00_Input/06_Entrevistas/`, el pipeline genérico
(inventory → extractor → markdown → anon) ya lo procesa. La 2ª pasada de
`viabilidad-prerelleno` (leer la transcripción para cerrar huecos testificales)
queda fuera de alcance de este bloque.

---

## [SIGUIENTE-INTAKE-EXPEDIENTE-AGIL] `intake-expediente` más ágil y con menos diálogos de permiso
*Promovido 2026-06-23 (sesión Cowork) por decisión de Nikolai. `MEJORAS #43`. Implementación: Claude Code (edición de la skill en `.claude/skills/intake-expediente/` + re-empaquetado del `.skill`).*

**Objetivo.** Que el intake desde Cowork (vía `expedientes-xl`) sea más rápido y dispare
menos diálogos de permiso por-llamada. Disparador: intake real del zip W-01VG51 → W-02VND1
(2026-06-23), donde el flujo hizo ~10 llamadas evitables y un round-trip muerto.

**Dos palancas (una es código, la otra es ajuste del cliente):**

1. **Skill (código) — menos llamadas al Drive:**
   - **Una sola pasada**: extraer a staging solo para listar/`hash_path`; tras el OK, copiar
     con **`copy_dir`** cuando todo va a una misma `<fuente>` (en vez de N `copy_path`).
   - **Gate sin OCR**: para escaneados, proponer `sin-fecha_...` por defecto y **no** ofrecer
     extraer fechas en Cowork (rama fuera de capa e inviable; la datación es del pipeline
     local hasta que exista `MEJORAS #42`).
   - **Regla dura**: nunca copiar binarios al mount para leerlos con bash (mount aislado del
     Drive; ver `DEAD_ENDS.md`).
   - Efecto colateral: menos operaciones sobre el Drive ⇒ menos diálogos de permiso si el
     usuario no ha activado "Permitir siempre".

2. **Cliente (NO código) — eliminar los diálogos de raíz:** activar **"Permitir siempre"**
   para el conector `expedientes-xl` en Claude Desktop/Cowork **una vez** → cero diálogos
   durante la ejecución. Es el arreglo definitivo del permiso; ningún cambio de skill lo
   sustituye (la propia skill ya lo documenta como ajuste del cliente). **Acción de Nikolai**,
   no de Claude Code.

- [ ] (1) Editar la skill `intake-expediente` (procedimiento + gotchas) e re-empaquetar `.skill`.
- [ ] (2) Activar "Permitir siempre" para `expedientes-xl` (acción manual de Nikolai).

---

## [SIGUIENTE-GOBERNANZA-FUENTES-VERDAD] Unificar fuentes de verdad (estructura/taxonomía/arquitectura)

Propuesta completa en `docs/GOBERNANZA_FUENTES_VERDAD.md` (disparador: revisión de
scaffolding, s. 2026-07-05). Extiende, sin contradecir,
`[CRITICO-FUENTES-VERDAD-PLANIFICACION]` (2026-05-29) e `[IDEA-GOBERNANZA-DOCS]`
(2026-06-10): la planificación ya está unificada; falta el drift de hechos que la
prosa copia del código.

- [x] **Fase 1** (riesgo cero) — **HECHA 2026-07-05**: README reescrito para orientar
  (FeesGuard→FeesDefender + banner a las fuentes canónicas; sin transcribir estructura/pipeline);
  cola de prioridad de `STATUS.md` archivada en `docs/bitacora/STATUS_cola_historica_pre_2026-07.md`
  (`estado: histórico`) + puntero a `PLAN.md` (STATUS 1117→442 líneas); `_skills_drafts/`→`_skills_ARCHIVO/`
  (`git mv`) + `scripts/package_skill.py` deja de empaquetar ese root. **`core/__init__.py`
  (`__product__`/`__product_long__`/docstring) FeesGuard→FeesDefender — HECHO 2026-07-06** (no lo
  importa ni testea nadie; verificado). Las apariciones `FeesGuard/0.1` en
  `sync_sudespacho_legacy.py`/`DEAD_ENDS.md` son User-Agent HTTP real, **NO tocar** (se dejan).
- [x] **Fase 2** — **HECHA 2026-07-05**: en `STATUS.md`, tabla de taxonomía y estructura
  de carpetas del caso reemplazadas por punteros a `core/config.py` (`TIPOS_CASO_*`,
  `CASO_SUBDIRS`); regla añadida al mapa de dependencias de `docs/ARQUITECTURA.md` (marca
  `[FUENTE ÚNICA]` + lista de espejos documentales legítimos). **Test guard**:
  `tests/test_gobernanza_taxonomia.py` (8 tests, verdes) — **ancla el código como fuente de
  verdad** (fija ACTORA=7, DEFENSIVA=4, OTROS=1, `CASO_SUBDIRS`, mapeo de posición); habría
  cazado el drift real que tenía STATUS ("3 tipos defensivos" cuando el código ya tenía 4).
  HALLAZGO que cambió el diseño: la taxonomía vive legítimamente en ~9 `.md` (skills LLM que
  corren en servidor + referencia CRM + bitácora en prosa), así que un escáner de `.md` daría
  falsos positivos → se descartó a favor del anclaje en código (nombre `test_docs_no_duplican_taxonomia.py`
  del plan original abandonado por eso). Suite NO ejecutada aquí (entorno remoto sin venv; lógica
  del guard validada importando `config`).
- [x] **Fase 3** — **HECHA 2026-07-05**. (a) Specs: decisión de Nikolai = **etiquetar, no mover**
  → frontmatter `estado:` en los 11 `PLAN_*.md`, `docs/INDICE.md` como índice único de ciclo de
  vida, regla fijada (specs nuevos nacen en `docs/superpowers/`). (b) Vendorizar la referencia
  sudespacho: **DESCARTADO** — el SSOT (`docs/ARQUITECTURA_RELACIONES.md`, creado en paralelo) la
  define como fuente externa compartida con El Contable/El Auditor; se mantiene fuera. (c)
  `GOBERNANZA_FUENTES_VERDAD.md` reconciliado con el SSOT (se complementan, no se duplican).
- [ ] **Gobernanza ligera** (recomendaciones, pendientes de arrancar): rotación de `STATUS.md` a
  `docs/bitacora/YYYY.md` (parcial: cola histórica ya archivada en Fase 1); invariantes en
  `session_close`; frontmatter `estado:`/`dueño:` + `docs/INDICE.md` (✅ índice creado en Fase 3).
- [ ] **Higiene de PII en la bitácora** (recomendación nº4, propuesta 2026-07-06 en
  `GOBERNANZA_FUENTES_VERDAD.md §4`). Regla: la bitácora referencia por código `W-xxxxx`, sin correos
  ni nombres de terceros ni direcciones (el dato sensible vive en `data/CASOS/`, fuera del repo).
  Huella medida en tracked docs: correos de terceros de casos reales (PersonaUno, PersonaTres, Prat,
  PersonaCinco…) mezclados con sintéticos de test, y también en **tests/core** (`email_atomize`/`whatsapp_atomize`),
  no solo en la bitácora. **Piezas:** (1) regla going-forward + check opcional en `session_close`;
  (2) **saneamiento retroactivo del historial** (`git filter-repo`).
  - **2026-07-06: repo puesto en PRIVADO** (corta exposición en curso — era público).
  - **Runbook + mapa de redacción entregados a Nikolai** (fuera del repo: contienen la PII a purgar).
    Ejecuta él en su PC (backup → clon fresco → filter-repo → grep+pytest verde → force-push →
    ticket a GitHub Support para cachés/commits colgados + revisar forks).
  - [ ] **TIER 1 (PRIMERO): purgar lo más sensible** — correos, nombres de personas, teléfonos reales.
    Mapa activo. Pendiente de que Nikolai lo ejecute.
  - [ ] **TIER 2 (SEGUNDO PASE, pendiente): direcciones de inmuebles** — incrustadas en case_ids y
    nombres de fichero de fixtures → mayor riesgo de romper tests. Se hace tras validar Tier 1.
  - [ ] **Fixtures sintéticas** para `email_atomize`/`whatsapp_atomize` (nacieron de un caso real) —
    tarea aparte, para que la PII no vuelva a entrar de raíz.

## Aparcado mientras el bloque crítico no se cierre

- `[SIGUIENTE-ORGANIZADOR-UI]` — **DESCARTADO 2026-06-07** (Ollama demasiado
  lento e impreciso). Sustituido por `[SIGUIENTE-CATALOGO-DOCUMENTAL]`;
  ver "Notas de la sesión Cowork 2026-06-07" abajo.
- `[SIGUIENTE-SUBDIVISION-CIUDADES]` — refactor `CASOS_ROOT` por ciudades
  (Fase 1).
- `[SIGUIENTE-SaRS1-PIPELINE]` H6 — subida manual gdocu expediente 659 +
  entrega a Claude frontier (depende del pull, lógicamente atado al
  bloque crítico).

---

## Resuelto

### [CRITICO-FUENTES-VERDAD-PLANIFICACION] — RESUELTO 2026-05-29

**Resolución (sesión Cowork 2026-05-29):** auditadas las fuentes de verdad de
planificación y consolidadas. La bitácora (`PLAN.md`, `STATUS.md`, historial de
commits) deja de vivir en Drive y pasa al **repo como única fuente de verdad**.

Decisiones cerradas:
- `PLAN.md` (raíz del repo) — cola priorizada compartida; la editan Cowork (PC)
  y Claude Code. Cowork móvil queda fuera del lazo hasta que exista un conector
  MCP de GitHub (hoy **no existe en el registry**; la vía OAuth/GitHub App no la
  soporta el flujo de conector personalizado y Docker+PAT es solo escritorio).
- `STATUS.md` (raíz del repo) — estado fáctico + bitácora de cierre, escrito por
  Claude Code.
- Historial: `git log`. Se **deprecan** `ESTADO.md` y `commits.log` como
  artefactos separados en Drive (duplicación + lag PC→nube generaba divergencia;
  el conector Drive de Cowork solo soporta create, no update → duplicados).
- Acceso móvil: app de GitHub (lectura); edición ocasional vía GitHub web.
- Drive queda solo para expedientes jurídicos (`CASOS_ROOT`) y entregables.

Regla documentada en `CLAUDE.md` §"Planificación y estado". La carpeta Drive
`Proyectos/FeesDefender/` la archiva Nikolai manualmente.

<details>
<summary>Problema original (apuntado 2026-05-28) — para trazabilidad</summary>

Convivían varias fuentes donde se registraban prioridades, decisiones, estado y
planes; el solapamiento generaba riesgo de drift, duplicación de la verdad y de
arrancar por una prioridad obsoleta. Fuentes detectadas: `PLAN.md` (Drive),
`STATUS.md` (repo) / `ESTADO.md` (Drive), `CLAUDE.md`, `README.md`,
`docs/PLAN_*.md`, `docs/MEJORAS_FUTURAS.md`, `docs/DEAD_ENDS.md`,
`bitacora/commits.log` (Drive), memoria de Cowork, project instructions de Cowork,
`docs/INTEGRACION_SUDESPACHO.md`. Riesgo ya materializado: el
`[CRITICO-PRESIGNED-DOWNLOAD-BUG]` vivía en `STATUS.md` pero no en la cola de
máxima prioridad, y hubo que rescatarlo a mano el 2026-05-28.

</details>

---

## Notas de la sesión Cowork 2026-05-28

- Verificado el pipeline de intake CRM: pull v2 implementado, CLIs en
  `scripts/sync_sudespacho.py` (`pull`, `sync_all`), `scripts/bulk_pull_expedientes.py`,
  `scripts/scheduled_sync.py`. NO hay botón en la UI Streamlit para lanzar
  el pull — solo CLI.
- Confirmado el workaround manual vigente para meter requerimientos y
  respuestas a requerimientos descargados manualmente del CRM: usar
  expander "📂 Subir al árbol CRM" (con rama canónica) o, como atajo,
  "📄 Demanda / documentos judiciales" (cajón `04_Manual/`). Ambos
  entran al ciclo anon → MD → frontier por igual; el primero deja además
  rastro en `_intake_log.jsonl`.
- Subido `[CRITICO-PRESIGNED-DOWNLOAD-BUG]` a máxima prioridad — antes
  estaba documentado en `STATUS.md` pero no en cabeza de cola.
- Apuntado `[CRITICO-FUENTES-VERDAD-PLANIFICACION]` — auditoría meta del
  proceso de desarrollo, motivada por la observación de Nikolai de que
  conviven demasiadas fuentes de verdad. **Resuelto el 2026-05-29** (ver arriba).

## Notas de la sesión Cowork 2026-06-07

### Decisión — Organización documental por caso

**1. Organizador local con Ollama → DESCARTADO** (`[SIGUIENTE-ORGANIZADOR-UI]`).
Ollama (Qwen 2.5 14B) demasiado lento e impreciso para esta tarea. La ventaja
de "local" (privacidad/coste) no compensa aquí: ya se anonimiza antes y ya hay
LLM cloud en el pipeline; nombres y estructura no son el payload sensible.
Coste de mantenimiento alto para usuarias no técnicas (fallos silenciosos) y la
vista `_organizado/` duplica almacenamiento.

**2. Sustituto → `[SIGUIENTE-CATALOGO-DOCUMENTAL]`: catálogo YAML canónico +
`INDICE.md` derivado.**

- `indice_documental.yaml` en la raíz del caso = fuente de verdad canónica,
  propiedad del código. Lo consumen pipeline, sync CRM, bitácora y (futuro)
  El Auditor.
- `INDICE.md` auto-renderizado desde ese YAML, de **solo lectura** (cabecera
  "no editar a mano"), para humanos (Paola, Ana, Marta E&V).
- Las ediciones entran por UI/pipeline, **nunca tocando el YAML a mano** (evita
  mojibake/encoding y conflictos de escritura concurrente).
- **Excluir siempre `90_NOTAS_PERSONALES/`** del indexado. El YAML convive con
  la nomenclatura de carpetas, no la sustituye.
- Esquema mínimo por entrada: `id_doc`, `ruta_relativa`, `nombre_original`,
  `tipo_documental`, `fecha_doc`, `parte` (propietario/buscador/tercero),
  `fuente` (E&V/cliente/juzgado), `estado` (original/anonimizado/borrador),
  `hash`, `fecha_indexado`.
- El desorden de carpetas heredado, si es masivo, se trata con un **script de
  migración puntual**, no con una feature permanente.

Patrón YAML→render coherente con el renderer YAML→XLSX de plantillas de
viabilidad. Implementación: Claude Code.

### Idea técnica — `[IDEA-SKIP-INCREMENTAL-EXTRACCION]`

**Origen**: consulta de Nikolai (sesión Cowork 2026-06-07) sobre qué pasa al
relanzar el pipeline con intake ya parcialmente OCRizado/markdowneado/anonimizado.

**Hallazgos al leer el código**:
- `extractor.extract_all` y `markdown_generator.build` **no son idempotentes**:
  reprocesan y sobrescriben todo `01_Procesado/` en cada corrida, exista o no.
  Solo `core/anon` salta por hash (`origen_sha256` en frontmatter, política
  `SALTAR`/`REPROCESAR`).
- **Bug de eficiencia**: `core/pipeline.py` llama a `extract_all` **dos veces**
  por corrida — paso `extractor.extract_all` y de nuevo dentro de
  `_markdown_step`. El OCR (Docling, el único paso caro) se ejecuta el doble de
  lo necesario, se toquen o no los documentos.

**TODO para Claude Code** (por orden de valor/riesgo, de mayor a menor):

- [ ] **1. Arreglar la doble llamada a `extract_all`** en `core/pipeline.py`
  (gana 50 % de OCR, riesgo cero). Cachear el resultado y pasárselo a
  `markdown_generator.build` en vez de reextraer. **Hacerlo aunque se descarte
  el resto.**
- [ ] **2. Skip incremental en extracción** por `sha256` del origen + versión de
  extractor (invalidar si cambia el backend Docling), reutilizando el patrón de
  `core/anon`, con `--force`.
- [ ] **3. Markdown que siga a la extracción**: regenerar solo el `.md` de los
  archivos realmente reextraídos. Trivial una vez la extracción devuelve cuáles
  saltó.

**Matiz de coherencia**: la regla de `CLAUDE.md` "Pipeline idempotente:
re-ejecutar nunca toca `00_Input/`" significa "no muta inputs", no "salta lo ya
hecho". El skip refuerza esa idempotencia, no la rompe. Implementación: Claude Code.

### ✅ Idea de gobernanza documental — `[IDEA-GOBERNANZA-DOCS]` RESUELTO 2026-06-10

Implementada la malla de referencias cruzadas y regla de promoción:
- `docs/MEJORAS_FUTURAS.md` retitulado a "backlog técnico" (alcance: todo el repo).
- Cabecera de `MEJORAS_FUTURAS.md` con referencia a `PLAN.md` y convención
  `[PROMOVIDO → PLAN.md]`.
- Cabecera de `PLAN.md` con referencia a `docs/MEJORAS_FUTURAS.md` y convención
  `MEJORAS #NN`.
- Regla de promoción documentada en `CLAUDE.md` §"Planificación y estado":
  disparador concreto (caso real, bug bloqueante, decisión de Nikolai).

## TODO — Refactor de `hechos_atomicos`: extractor source-locked
*Sesión Cowork 2026-05-29*

**Decisión**: sustituir el prompt LLM único actual (`core/viability.py::analyze` → `02_Analisis/hechos_atomicos.md`) por un extractor en tres capas (E + B + C) que deposita un `08_Para frontier/_hechos.md` 100 % citado.

**Motivación**: el prompt actual es no determinista, no obliga a anclar cada hecho a un span literal del documento fuente y contradice la regla source-locked del despacho (skill `verificacion-anclada-fuente`). El frontier hoy recibe un `.md` que ningún verificador puede auditar.

**Arquitectura objetivo**

- **Capa C — extractor estructurado por `tipo_caso`**: esquema fijo de hechos esperados (hoja encargo, oferta, aceptación/rechazo, incumplimiento, reclamación previa, etc.) por cada `tipo_caso` de `TIPOS_CASO_ALL`. Function calling / JSON schema sobre `06_Anonimizado/`. Huecos como `[PENDIENTE]`. Reaprovecha la ontología del cuestionario de viabilidad (82 preguntas) y las plantillas YAML de `data/_plantillas/`.
- **Capa E — extracción por documento**: para cada `.md` en `06_Anonimizado/` se generan claims residuales fuera del esquema. Contexto pequeño = menos alucinación; ningún claim cruza documentos.
- **Capa B — verificador de spans**: cada claim emerge como `(paráfrasis, span_literal, doc, página, párrafo)`. Si el `span_literal` no aparece en el documento citado (con tolerancia OCR razonable), el claim se descarta automáticamente. Cero hechos sin anclaje verificable.

**Output**: `08_Para frontier/_hechos.md` con (i) ficha estructurada del `tipo_caso` y (ii) hechos adicionales por documento. Frontmatter neutralizado sin `case_id` literal (coherente con H5b SaRS1).

**Pasos sugeridos**

1. Definir esquemas de hechos por `tipo_caso` en `data/_plantillas/hechos/`, reaprovechando campos del cuestionario.
2. Implementar capa C (function calling / structured output; Sonnet para campos relacionales, Haiku para campos atómicos).
3. Implementar capa E (extracción doc-a-doc con cita obligatoria).
4. Implementar capa B (verificador de spans con normalización: lowercase + colapso espacios + remoción puntuación; match exacto sobre cadena normalizada, sin Levenshtein, para no aceptar paráfrasis disfrazadas).
5. Integrar como paso del `core/pipeline.py` después de anonimización, antes de `08_Para frontier/`.
6. Tests E2E sobre BaRS1 + SaRS1: cobertura sobre hechos clave + 0 falsos positivos sin anclaje.
7. Decidir: deprecar `hechos_atomicos.md`/`contradicciones.md`/`prueba_indexada.md` legacy en bloque, o mantenerlos como vista interna durante transición. Inclinación Cowork: deprecar — la duplicación crea divergencia.

**Decisiones pendientes (cerrar antes de implementar)**

- Modo del verificador en CI sobre casos en producción: ¿informativo o bloqueante? Inclinación: informativo en primera fase, bloqueante una vez estabilizado.
- Granularidad del span: ¿párrafo entero, oración, o N caracteres alrededor del hecho? Inclinación: oración completa por defecto, ampliable a párrafo si el hecho es relacional.

**Dependencia con la migración Drive → repo**: ninguna. Pueden ejecutarse en paralelo.

---

## [SIGUIENTE-REORG-05CRM] Aplanado de `05_CRM` por buckets procesales + detector de conjunto
*Añadido 2026-06-10 (sesión Cowork). 15 decisiones aprobadas por Nikolai. Implementación: Claude Code. Capa de nombrado/bundles (D1-D3) documentada en `docs/MEJORAS_FUTURAS.md` #28-#29.*

> **✅ PRIMERA TANDA COMPLETADA 2026-06-10 (Claude Code).**
> - [x] **Paso 0 / D8** — `CARPETA_ID_TO_PATH` poblado: `308`→Declarativo/Oposicion,
>   `380`→Preliminares/Demanda. Descubiertos vía `category_unknown`, doble
>   verificación UI (Nikolai) + REST. Solo había 2 IDs no mapeados en toda la
>   data real. El endpoint de árbol es dead end (§13.3); rama ambigua se cierra en UI.
> - [x] **D6** — `_bucket_for(rama_canonica)` (pura) + exclusión Preliminares,
>   aplicada en `crm_branch_path` (`core/case_manager.py`). Routing por rama
>   completa, no por etiqueta-hoja.
> - [x] **D7** — andamiaje *lazy*: `_ensure_crm_tree_dirs` crea solo `05_CRM/`;
>   los buckets se materializan al escribir. **D15** documentado (05_Procedimiento).
> - [x] **D12-D13** — `scripts/migrate_05crm_buckets.py` (in situ, sin re-bajar
>   ni re-OCR; re-llave manifest + extract_state; colisión de stem; by_carpeta;
>   journal + .bak). **Expediente 444 migrado**: 96 docs → {01_Demanda:23,
>   05_Diligencias_Preliminares:31, 99_Otros:42}, 0 colisiones, 0 re-OCR.
> - [x] **D14** — `test_crm_branch_path.py` reescrito (buckets + anti-sobrecaptura
>   + unit de `_bucket_for`), `test_pull_expediente_v2.py` y `test_smoke_paso7.py`
>   actualizados, `test_migrate_05crm_buckets.py` nuevo. `test_dedup_manifest.py`
>   y `test_judicial_intake.py` revisados (agnósticos a ruta, sin cambios).
>   Suite verde; gold SaRS1 intacto.
>
> **✅ SEGUNDA TANDA COMPLETADA 2026-06-10 (Claude Code, sesión 35).**
> - [x] **D10** — `fechamodificacion` traída al listado REST
>   (`properties[12]`) + campo `modified_at` en el DTO `GdocuDocInfo`.
>   Nombre/formato confirmados **en vivo** contra el 444
>   (`scripts/probe_gdocu_fecha.py`; 97/97 docs con fecha). ISO-8601 con offset.
> - [x] **D9** — detector de conjunto (`core/conjunto_detector.py`): clúster por
>   `modified_at` idéntico ∩ patrón `\bD\s*\d+…-`; cabecera = odd-one-out sin
>   patrón (en el 444 es `ORDINARIO…VALLDAURA.doc`, **no** "DEMANDA" → keyword
>   solo como desempate); bucket por cabecera o consenso; baja confianza →
>   `pendiente_revision`. **Solo emite propuestas** (eventos `conjunto_detectado`
>   / `pendiente_revision`); **persistencia de `parent_id` DIFERIDA** a
>   `[SIGUIENTE-CATALOGO-DOCUMENTAL]` (catálogo `indice_documental.yaml` **no
>   existe** — decisión de Nikolai: no construirlo a medias). Validado contra el
>   444 real (3 lotes, 0 misrouting). CLI on-demand
>   `scripts/detectar_conjuntos.py`. Nuevo evento `conjunto_detectado` (INTAKE_EVENTS 16→17).
> - [x] **D11** — override local `doc_id→bucket` en `bucket_override` del
>   frontmatter de `_caso.md`, respetado por `crm_branch_path` por encima de la
>   carpeta del CRM (`kind == "override"`), sin tocar el CRM remoto. Cableado en
>   el pull (lectura única por corrida). Refactor: `resolve_bucket` como fuente
>   única de la resolución carpeta→bucket (compartida con el detector).
> - **Pregunta abierta resuelta:** confirmado contra el 444 que **solo la prueba
>   de la actora usa `D NN`**; cabecera y contestación NO → la cabecera se
>   detecta como el doc sin patrón.
> - **Tests:** +3 D10, +~13 D9 (`test_conjunto_detector` nuevo), +7 D11,
>   `test_intake_log` (17 eventos). **Suite: 652 passed, 58 skipped** (verja
>   rápida, EXCLUYENDO `test_sudespacho_relations.py` — ver ⚠️). Gold SaRS1 intacto.
> - **⚠️ Ajeno a esta tanda:** `core/sudespacho_relations.py` + su test están
>   modificados en el working tree por trabajo concurrente (no por esta sesión;
>   al inicio NO estaban modificados) y rompen la colección de pytest por import
>   circular. No se tocaron ni commitearon — revisar aparte.
>
> **Pendiente (TERCERA TANDA / futuro):** persistencia `parent_id` de D9 cuando
> exista `[SIGUIENTE-CATALOGO-DOCUMENTAL]`. Follow-up del intake manual (abajo)
> sigue sin abordar (requiere OK de Nikolai por ripple a UI).
>
> **Follow-up detectado (fuera de las 15 decisiones, decisión de Nikolai):** el
> intake **manual** (`intake_manual.save_file_crm_branch` + `list_crm_branch_files`
> + selector `CRM_TREE` en `streamlit_app.py:630`) sigue escribiendo a la rama
> profunda elegida en la UI; convendría bucketizarlo también (vía `_bucket_for`)
> para no recrear el árbol profundo que la migración elimina. No se tocó por
> estar fuera del alcance de la primera tanda (ripple a UI + ~6 tests de
> `test_smoke_paso7.py` no listados en D14).

**Objetivo.** Sustituir el árbol profundo del CRM en `00_Input/05_CRM/` (hasta 4
niveles + ~20 carpetas vacías de andamiaje) por una estructura plana de un nivel
con buckets procesales. Motivos: límite de ruta de Windows (260 car.) sobre un
Drive ya largo, y desorden de carpetas vacías. La estructura de `05_CRM` es
**solo navegación humana del input**: el pipeline (`extractor` →
`markdown_generator` → `anon`) aplana a un output por documento con slug
stem-only (`extractor.py:214`), independiente de la subcarpeta de origen.

**Árbol confirmado (D5).**

```
05_CRM/
├── 01_Demanda/                  ← Declarativo/Demanda (demanda + su prueba documental)
├── 02_Contestacion/             ← Declarativo/Oposicion (un solo bucket aunque haya varios demandados — D5b)
├── 03_Monitorio_Demanda/        ← Monitorio/Demanda (petición inicial + docs)
├── 04_Monitorio_Oposicion/      ← Monitorio/Oposicion (+ docs)
├── 05_Diligencias_Preliminares/ ← Preliminares/Demanda (solicitud de DP + docs)
├── 99_Otros/                    ← resto PLANO por fecha (procesales, resoluciones, Apelación, Ejecución, General, Documentos, RGPD/LOPD, Penal…)
└── 99_Sin categoria/<exp>/      ← fallback cuando id_carpeta no resuelve (ya existe hoy)
```

**Decisiones aprobadas (registro).**

- **D5 — Aplanar a 1 nivel** con el árbol de arriba. Cada bucket mapea 1:1 a una
  hoja real de `CRM_TREE`; se aplana el andamiaje intermedio
  (`Civil/1ª Instancia/Declarativo/…`), no las hojas con significado.
- **D6 — Routing por rama canónica completa, no por etiqueta-hoja.** Función pura
  `_bucket_for(rama_canónica)` aplicada en `crm_branch_path` (`case_manager.py:524`,
  único punto de routing, invocado en `sync_sudespacho.py:1444`). `Preliminares`
  en **lista de exclusión explícita**: su "demanda" (solicitud de DP) **nunca**
  cae en `01_Demanda` → va a `05_Diligencias_Preliminares`. Etiqueta-hoja pura
  sobre-captura (`"Demanda"` casa 3 ramas, `"Oposicion"` 2 → hoy ambas caen a
  fallback, confirmado por `test_crm_branch_path.py`).
- **D7 — Cambiar también el andamiaje** (`_scaffold_crm_tree`,
  `case_manager.py:841`): crear solo los buckets en uso o ir *lazy*
  (crear-al-escribir). Tocar solo el routing dejaría las carpetas vacías.
- **D8 — Requisito previo (paso 0): poblar `CARPETA_ID_TO_PATH`** con los
  `id_carpeta` reales del tenant para las ramas procesales (hoy solo 2 IDs
  mapeados; las etiquetas son ambiguas → casi todo cae a `99_Sin categoria`).
  Descubrimiento progresivo vía evento `category_unknown` ya existente. **Sin
  esto, aplanar es cosmética.** Doble verificación UI + API.
- **D9 — Detector de conjunto** para reagrupar cabecera + prueba **mal archivadas**:
  clúster por *timestamp de modificación del CRM idéntico* (subida en lote) ∩
  *patrón de nomenclatura* `D\s*\d+\s*-` (numeración de prueba del despacho; admite
  sub-índice `22-C`/`22-D`). Se ancla cada lote a su cabecera (`DEMANDA…`/
  `CONTESTACION…`) por cercanía temporal y se asigna al bucket de la cabecera.
  Clústeres de baja confianza → `pendiente_revision`, sin adivinar. La relación
  se persiste como `parent_id` en `indice_documental.yaml` (MEJORAS #29) →
  sobrevive aunque los ficheros queden físicamente dispersos.
- **D10 — Requisito previo de D9: traer la fecha de modificación del CRM.** Hoy
  NO se pide: la query REST solo trae `nombrefinal`/`mime`/`tamano`/`id_carpeta`
  (`sync_sudespacho.py:649-653`) y `GdocuDocInfo` no tiene campo de fecha
  (`:297-303`). Descubrir el índice de esa propiedad y añadir el campo al DTO.
- **D11 — Override local `doc_id → bucket`** editable por el letrado (en
  `_caso.md` o YAML del caso), respetado por encima de la carpeta del CRM, **sin
  tocar el CRM remoto**. Parche inmediato para el mal archivo.
- **D12 — Migrar in situ, NO re-bajar.** El re-pull no migra limpiamente: el
  dedup es por hash (`IntakeManifest.register`), así que un re-pull sin resetear
  manifest devuelve el `primary_path` viejo → con `physical_complete=True`
  duplica (copia vieja + nueva), con `False` no mueve. Migración: mover ficheros
  + reescribir `00_Input/_intake_hashes.json` (rel viejo→nuevo, o borrarlo y dejar
  que `reconcile()` reconstruya desde disco) + re-llavear
  `01_Procesado/raw_text/_extract_state.json` (clave = `rel_path`,
  `extractor.py:218`; los `.txt` NO se mueven, slug = stem) + `inventory.scan`.
  Así `extract_all` hace skip y **no re-OCRiza** los 96 docs del 444. Script
  puntual, no feature.
- **D13 — Pre-migración:** detectar **colisiones de stem** entre ramas que
  confluyan al mismo bucket (forzarían `__1` vía `_resolve_name_collision` →
  cambio de slug → re-OCR; o renombrar también el `.txt`). Refrescar `by_carpeta`
  en el frontmatter de `_caso.md` (queda rancio tras migrar).
- **D14 — Tests.** Asumir cambio de semántica de conteos (`documents_overlap`
  baja, `documents_skipped_dedup` sube — no es bug). Reescribir
  `test_crm_branch_path.py` (expectativas profundas → buckets + tests
  anti-sobrecaptura: `Preliminares/Demanda`→`05_…`, `Declarativo/Oposicion`→
  `02_…`, `Monitorio/Demanda`→`03_…`); actualizar `test_pull_expediente_v2.py` y
  `test_dedup_manifest.py` (claves `by_carpeta` + conteos); revisar
  `test_judicial_intake.py` (mayormente agnóstico a ruta). Añadir unit de
  `_bucket_for()` y test del script de migración (idempotencia + preservación de
  cache OCR + colisión de stem). El gold fixture **SaRS1 no se toca** (es upstream
  del anon; confirmar ejecutando la suite).
- **D15 — `05_Procedimiento`** (carpeta funcional de fase, hoy inerte: nadie
  escribe en ella; solo la crea el scaffolding y la barre `linker.py:19`).
  Mantener su rol semántico de **work-product del letrado para el litigio en
  curso**, diferenciado del espejo crudo del CRM (`00_Input/05_CRM/`). Documentar
  su propósito (hoy no consta). Aplicarle el criterio *lazy* de D7. Anotar la
  duplicidad del "05" (`00_Input/05_CRM` vs `05_Procedimiento`) como cosmética de
  baja prioridad.

**Capa de nombrado/bundles (D1-D3) → `docs/MEJORAS_FUTURAS.md`:** D1 (prefijo ISO
`AAAA-MM-DD`) y D2 (alcance solo `06_Anonimizado`/`INDICE.md`, identidad =
`id_doc`/hash) amplían #28; D3 (bundles cabecera-anexo por `parent_id` en el
catálogo, no subcarpeta física) es #29. D4: fuente única de verdad documental;
no se parchea el motor de anonimización (D8 histórico / `feedback_anon_logica_intacta`).

**Lo que NO se toca (F):** motor de anonimización, `separar.py`, `linker.py`,
independencia de `01_Procesado`/`06_Anonimizado` respecto a `05_CRM`, y la
decisión ya cerrada de descartar el organizador Ollama / vista `_organizado/`.

**Orden de ejecución recomendado.** Paso 0 (D8 descubrir IDs del tenant) →
routing `_bucket_for` + exclusión Preliminares (D6) + andamiaje lazy (D7) →
migración in situ del 444 preservando OCR (D12-D13) → tests (D14). El detector de
conjunto (D9) y su requisito (D10) y el override (D11) pueden ir en una segunda
tanda. Medir antes la ruta más larga real del 444: aplanar `05_CRM` solo ahorra
~30 car.; si no basta para cruzar 260, combinar con rutas largas `\\?\` o acortar
el ensamblado de nombre.

**Pregunta abierta (no bloquea):** confirmar contra una carpeta de contestación
real si el **demandado usa el mismo prefijo `D NN`** u otro, para afinar D9.

## [SIGUIENTE-HOMOGENIZACION-SKILLS] Charter + enforcement + retrofit de skills

> Handoff Cowork→Claude Code (2026-06-16). Diseño aprobado por el letrado. **Lo
> ejecuta Claude Code** (Cowork solo planifica). Objetivo: que todas las skills
> —actuales y futuras— compartan lo mejor del estándar y que las mejoras futuras
> se propaguen solas. **NO duplica `docs/MEJORA_CONTINUA_SKILLS.md`: lo
> referencia.** Estado verificado en disco el 2026-06-16.
>
> **ALCANCE REDUCIDO 2026-06-16 (tras crítica de ROI, aprobado por el letrado):**
> no hay escala que justifique la superestructura de gobernanza. Solo se ejecuta
> **corrección + mínimo reutilizable**; el resto se difiere. Ver «Alcance
> revisado» más abajo — manda esa sección sobre el «Plan por fases» original.

### Decisiones del letrado (cerradas)

1. **CHANGELOG.md separado** por skill (no sección `## Changelog` dentro del
   `SKILL.md`). Actualizar el paso 4 de `MEJORA_CONTINUA_SKILLS.md` para que
   apunte a `CHANGELOG.md`.
2. **Biblioteca de jurisprudencia compartida** en `_shared/jurisprudencia/`,
   referida por ECLI (no per-skill: evita N copias del mismo fallo). Migrar la de
   `oposicion`. Tradeoff asumido: menor autonomía de empaquetado.
   **(Ejecución DIFERIDA — ver Alcance: se queda en `oposicion` hasta que una 2.ª
   skill la necesite.)**
3. **Cosecha: se mantiene el modelo actual** (un fichero por sesión, push por
   conector al Drive del despacho; lo ven solo los abogados, no E&V).
   **SALVAGUARDA pendiente:** verificar **una vez** que el ACL de
   `Biblioteca_Skills/` excluye de hecho a los miembros de E&V (p. ej. Marta
   Reynares); en un Shared Drive los miembros heredan acceso a todo. Si los
   incluye, mover a carpeta restringida o a un drive separado.
4. **AGPL — `verificacion-anclada-fuente` se mantiene PURAMENTE INTERNA.**
   (a) conservar licencia + atribución actuales y añadir un `LICENSE` con el texto
   íntegro de la AGPL-3.0 + nota de "modificado por Tyukhay Legal";
   (b) **nunca co-empaquetarla** con skills propietarias (cada skill, su `.skill`);
   (c) **no exponerla por red** en el despliegue E&V (la cláusula §13 obligaría a
   publicar la versión adaptada). Si en el futuro se necesita exponerla, reabrir
   decisión: publicar la adaptada o reescribir una skill propia.
5. **Taxonomía `type` en dos ejes** (hoy mezclados): `rol`
   (transversal | fase | cliente | output) y `naturaleza`
   (atomica | orquestadora).
6. **Gobernanza: bus factor 1** (Nikolai, único aprobador de versiones, tags y
   promoción de jurisprudencia). El gate de calidad es el validador automático,
   no un segundo humano.

### Anatomía canónica (modular: núcleo + módulos por rol)

- **Núcleo (toda skill propia):** `SKILL.md` con frontmatter estándar,
  `CHANGELOG.md`, `LICENSE`, `.gitignore` (excluye telemetría).
- **Módulo OPERACIÓN** (skills que producen outputs en expediente: las 5
  procesales + `viabilidad-prerelleno`): helpers canónicos
  (`registrar_outputs.py`, `registrar_uso.py`, `programar_revision.py`,
  `scaffold_caso.py`) + bucle de `MEJORA_CONTINUA_SKILLS.md`.
- **Módulo EVOLUCIÓN:** `EVOLUCION.md` de 5 fases (plantilla en el charter).
- **Módulo JURISPRUDENCIA + COSECHA** (`oposicion`; candidatas `escritos`,
  `preparacion-*`): índice ECLI como SSOT en `_shared/jurisprudencia/` +
  consolidador + `drive_config.json`.
- **No aplican módulos** a `verificacion-anclada-fuente` (comportamiento
  transversal) ni `engel-volkers` (contexto de cliente): solo núcleo + identidad.

### Frontmatter estándar (esquema)

`name` (==carpeta), `description` (disparadores + "NO usar cuando…"), y bloque
`metadata`: `rol`, `naturaleza`, `jurisdiction`, `area` (lista), `version`
(semver entre comillas), `author`, `organization`, `contact`, `status`
(vigente | deprecada | experimental), `charter_version`, `orchestrates` (lista),
`requires` (lista), `evolucion_fase`. Más `license` de primer nivel. Para
**adaptadas de tercero**: añadir `author_original`, `adapted_by`,
`base_skill_url` y la licencia de origen (no relicenciar nunca a la baja).
`orchestrates`/`requires` hacen el **mapa de relaciones derivable y validable**
(no prosa que se pudre).

### Alcance REVISADO 2026-06-16 (manda sobre el «Plan por fases» original)

Tras crítica de ROI: 9 skills, un autor, uso bajo (ni 5 usos reales aún). No se
construye la superestructura de gobernanza. Solo **corrección** + **mínimo
reutilizable**. Lo demás, diferido a `docs/MEJORAS_FUTURAS.md` hasta que lo pidan
los datos.

**AHORA — valor inmediato:**

- **Ola 1 (correcciones), verifica el estado real en disco:**
  - Reconciliar `oposicion-alegacion-nulidad` a los helpers canónicos: su
    `scripts/log_uso.py` → `registrar_uso.py` (vías dentro de `metricas`);
    sincronizar helpers.
  - Retirar la **doble telemetría**: `preparacion-audiencia-previa/scripts/log_uso.py`
    y `preparacion-juicio-oral/scripts/log_uso.js`.
  - **Corregir el drift de vías** (3 vías viejas → 4 actuales: A nulidad absoluta ·
    B vicio del consentimiento · C incorporación · D contenido/abusividad) en el
    logger, en `EVOLUCION.md` (Fase 1) y en `logs/README.md` de `oposicion`.
  - **AGPL `verificacion-anclada-fuente`:** añadir `LICENSE` con el texto íntegro
    de AGPL-3.0 + nota de modificación (conservar atribución; no co-empaquetar con
    propietarias). Higiene legal barata.
- **Mínimo reutilizable:**
  - `_shared/_plantilla-skill/` — plantilla para que las skills **nuevas** nazcan
    iguales (frontmatter ligero con los dos ejes `rol`/`naturaleza` + módulos).
    Ahorra tiempo real en cada alta.
  - `scripts/validate_skills.py` en **modo AVISO** — se corre a mano, informa de
    no conformidades, **no bloquea** commits. Sin hook, sin CI.

**DIFERIDO a `docs/MEJORAS_FUTURAS.md`** (no construir hasta que los datos lo pidan):

- Charter `_shared/ARQUITECTURA_SKILLS.md`.
- `scripts/new_skill.py` (scaffolder).
- `inventario_skills.json` + `INVENTARIO.md` (termómetro de conformidad).
- `validate_skills.py` en modo **bloqueante** (pre-commit + CI) y la regla blanda
  en `CLAUDE.md`.
- **Retrofit masivo de identidad** (`metadata`+`license`) de las 7 skills (antiguas
  Olas 2-3): se alinean **al tocar cada una**, no en barrido.
- **Generalizar jurisprudencia+cosecha a `_shared/`**: se queda en `oposicion`
  hasta que una 2.ª skill lo necesite.

**Disparador para reabrir lo diferido:** más skills, más manos, o una
inconsistencia que cueste algo real.

**Cierre:** `python scripts/sync_skill_helpers.py` + `python scripts/package_skill.py <skill_dir>`
+ `git commit`/`tag` + re-import en el servidor. Corre la suite (incl.
`test_skill_helpers_sync.py`).

Encaja con el **retrofit diferido** ya decidido (alinear al tocar cada skill),
salvo la **Ola 1**, que conviene ejecutar ya.

### Matriz de conformidad (verificada 2026-06-16)

| Skill | metadata | license | helpers canónicos | bespoke a retirar |
|---|---|---|---|---|
| oposicion-alegacion-nulidad | sí | sí | **NO** | `log_uso.py` → canónico |
| verificacion-anclada-fuente | sí (AGPL) | sí | n/a | — |
| cendoj-descarga | falta | falta | sí | — |
| escritos-judiciales | falta | falta | sí | — |
| preparacion-litigio-civil | falta | falta | sí | — |
| preparacion-audiencia-previa | falta | falta | sí | `log_uso.py` (doble) |
| preparacion-juicio-oral | falta | falta | sí | `log_uso.js` (doble) |
| engel-volkers | falta (`status` suelto, `version` sin comillas) | falta | n/a | — |
| viabilidad-prerelleno | falta (sin `version`) | falta | **NO** | — |

### Reconciliación documental (evitar el tercer doc solapado)

**(Aplica cuando se construya el charter, hoy diferido.)** El charter
**referencia** `MEJORA_CONTINUA_SKILLS.md` (dueño del bucle) y
`EVOLUCION.md` (instancia del módulo). Marcar `despacho-skills/SKILL_AUTHORING.md`
como **superado** por el charter (idealmente, sacar ese repo obsoleto del árbol de
trabajo para que no contamine).

---

## ✅ [SKILL-CONTESTACION-ART20-LAU] Nueva skill `contestacion-honorarios-art20-lau` — entregada e integrada en el repo
*Creada en Cowork (v1.1.0, playbook del asunto W-02THLJ) y distribuida al equipo como `.skill`. Handoff Cowork→Claude Code 2026-07-03. Integración en el repo: Claude Code.*

> **✅ HECHA 2026-07-03 (Claude Code).** La skill se **importó a `.claude/skills/contestacion-honorarios-art20-lau/`** (fuente única de desarrollo, regla CLAUDE.md; antes vivía solo como `.skill` fuera del repo). Integración completa:
> - **Helpers canónicos (task 1):** añadida a `_TARGETS` de `scripts/sync_skill_helpers.py`. El sincronizador la promueve a módulo **OPERACIÓN** y le copia los 4 helpers (`registrar_uso.py` —ya venía byte-idéntico—, `registrar_outputs.py`, `programar_revision.py`, `scaffold_caso.py`), en paridad con `oposicion-alegacion-nulidad`. `sync --check` OK (byte-idénticos); `test_skill_helpers_sync.py` verde.
> - **Telemetría (task 2):** el patrón de detección del helper (`pyproject.toml` hacia arriba) resuelve a `data/_skill_logs/contestacion-honorarios-art20-lau/` (verificado); `uso.jsonl` se crea a demanda en el primer `log()`. Ruta ya cubierta por `.gitignore` (no se versiona telemetría con refs reales). Se añadió `.gitignore` propio a la skill (excluye `logs/*.jsonl|*.json`, conserva `README.md`).
> - **Homogeneización / validador AVISO (task 3):** al vivir en `.claude/skills/`, entra automáticamente en el alcance de `scripts/validate_skills.py`. Único aviso: `metadata.rol`/`metadata.naturaleza` ausentes (usa el eje viejo `type: workflow`) — mismo estado que las demás skills bajo el **retrofit de identidad diferido**; license, version y helpers conformes.
> - **PENDIENTE (v1.1.1, lo hace Cowork cuando Nikolai aporte el PDF):** incorporar **SJPI nº 10 de Barcelona 69/2025 anonimizada** a `references/jurisprudencia/` (+ fila en `INDICE.md`).
> - Observación (fuera de alcance, pre-existente): `registrar_uso.skill_version` no lee `metadata.version` anidado → registra `"0.0"` para esta skill y para `oposicion` por igual. No se toca aquí.

---

## ✅ [SIGUIENTE-EXPORT-ETIQUETA-EMAIL] Exportar etiqueta Gmail → expediente (motor + Streamlit + CLI + skill)
*Decisión Nikolai 2026-06-22 (hilo Cowork BaRS1 Tibidabo 8). Disparador concreto: el volcado de los correos de una etiqueta al expediente es lentísimo vía Cowork (conector solo-texto, sin binarios, tope de tamaño por contexto). Se necesita herramienta reutilizable para TODOS los casos y usable por Paola y Ana.*

> **✅ HITOS 1 y 2 COMPLETOS (2026-06-22, Claude Code).** Motor `core/email_export.py`
> (capa pura `eml_filename`/`split_eml`/dedup `Message-ID` + glue `export_label`) + CLI
> `scripts/export_label_emails.py` + `tests/test_email_export.py` (+14). **Corrida real
> W-02VND1: 122 `.eml` + 348 adjuntos, idempotente (2ª corrida 0/122).** Hito 2: botón
> Streamlit «✉️ Exportar correos por etiqueta» + skill `exportar-correos-etiqueta`
> empaquetada en el plugin (`package_plugin.py`), versión 0.1.0→0.2.0,
> descripciones actualizadas. Suite verde (exit 0). Commit `5088e27` (main, sin push).
> **✅ Hito 3 COMPLETO (2026-06-23, Claude Code).** Conector `email-export` en
> `plugins/email_export_mcp/server.py` (FastMCP, tool `export_label_emails`, inyección
> de deps). Plugin v0.2.0→0.3.0. Tests: `tests/test_email_export_mcp_server.py` (6 verdes).
> Snippet `claude_desktop_config.json` en `plugin-src/README.md`. Commit `b58497f`.
> **Pendiente Nikolai:** copiar snippet al `claude_desktop_config.json` de Cowork y reiniciar Claude Desktop.

**Objetivo.** Dada una etiqueta Gmail de un caso, volcar TODOS sus mensajes como `.eml` fieles (cualquier tamaño) + adjuntos extraídos, organizados cronológicamente con la nomenclatura del despacho (`AAAA-MM-DD_descripcion`), en `00_Input/03_Email/`. Idempotente.

**Arquitectura (UI → Core → Datos; lógica solo en core):**
- `core/email_export.py` — MOTOR. Reutiliza el OAuth de `gmail_source` (`_load_credentials`/`_build_service`; tokens `~/.gmail-mcp/`, sin alta nueva). `labels().list`→labelId; `messages().list(labelIds=[…])` paginado; `messages().get(format='raw')`→`.eml`; capa pura `split_eml(raw)->(.eml,[adjuntos])` + `eml_filename(headers)`; subcarpeta fechada si hay adjuntos; dedup por `Message-ID`; idempotente.
- Streamlit — página/botón "Exportar correos por etiqueta" para **Paola y Ana** (eligen caso+etiqueta y pulsan; corre en el PC con token y `G:`). La UI solo orquesta.
- `scripts/export_label_emails.py` — CLI (`--ref W-XXXXX`, `--account`, `--label`); destino vía `case_locator.path_for`; genera `INDICE.md`/`CRONOLOGIA.md`.
- `.claude/skills/exportar-correos-etiqueta/` — skill (rol:input, atomica) para Cowork/Claude Code; NO confundir con `intake-expediente` (subir sueltos) ni `organizar-sala-lectura`. Empaquetar con `package_skill.py` + re-import.
- `tests/test_email_export.py` — capa pura (nombre canónico, extracción de adjuntos, dedup, idempotencia).

**Validación inicial.** Correr para W-02VND1, etiqueta `01. CONTING/01. EXTRAJUD/01. BARCELONA/BaRS1 - Tibidabo 8 - (W-02VND1)` (cuenta engelvoelkers) → todos los correos organizados en `03_Email`.

**Ejecución/commit/empaquetado:** Claude Code (pytest + token local + git). El OAuth ya está resuelto.

**Estado provisional dejado hoy (2026-06-22, Cowork):** en el Drive de engelvoelkers se creó `00_Originales (W-02VND1)` con 40 `.eml` (los adjuntos de las 8 remesas de Eva/Isabel) + `03_Email/04_Correos organizados (W-02VND1)/INDICE.md` y `CRONOLOGIA.md`. Es provisional y queda sustituido por el export por etiqueta cuando exista.

**Secuencia de entrega (añadido 2026-06-22).**
- **✅ Fase 1 — que funcione para Nikolai en W-02VND1 (PRIORITARIA):** `core/email_export.py` + CLI `scripts/export_label_emails.py` + `tests/test_email_export.py`. Criterio de aceptación: ejecutar el CLI para W-02VND1 deja TODOS los correos de la etiqueta como `.eml` + adjuntos organizados en `00_Input/03_Email/`, idempotente y con la suite verde. Con esto el intake ya es operativo para el abogado. **HECHA — 122 `.eml` + 348 adjuntos, idempotencia verificada.**
- **✅ Fase 2 — usable por Paola y Ana:** página/botón Streamlit sobre el mismo motor + empaquetado de la skill `exportar-correos-etiqueta` y re-import del `.skill`. **HECHA (botón + empaquetado; re-import del `.skill` lo hace Nikolai).**
- El conector `expedientes-xl` NO interviene en este motor (el script escribe en `G:` por filesystem local). Producir `.eml` fieles de toda la etiqueta requiere Gmail API local `format=raw`; por eso la implementación/ejecución es Claude Code.

**Criterio de aceptación / orden (ajuste 2026-06-22):** PRIMERO que funcione para
**Nikolai en W-02VND1 (Tibidabo 8)** — `core/email_export.py` + CLI + corrida real
dejando todos los correos de la etiqueta en su `03_Email` (Hito 1). DESPUÉS, botón
Streamlit para Paola/Ana, skill empaquetada y tests completos (Hito 2). El motor es
el mismo; la UI solo orquesta.

**Distribución = plugin `feesdefender` (decisión 2026-06-22).** La capacidad se entrega
dentro del plugin existente (no uno nuevo): se añade la skill `exportar-correos-etiqueta`
al empaquetado (`scripts/package_plugin.py` copia también esa skill), se sube versión en
`plugin-src/.claude-plugin/plugin.json` (0.1.0→0.2.0) y se actualizan
`marketplace.json`/`README`. Así es instalable y reutilizable en TODOS los casos
(parametrizado por `--ref`/etiqueta). Evolución opcional (Hito 3): exponer el motor como
**herramienta MCP** del plugin (análogo a `expedientes_xl/server.py`, que corre local con
acceso al token `~/.gmail-mcp` y a `G:`) → usable también desde Cowork de escritorio, no
solo Claude Code.
