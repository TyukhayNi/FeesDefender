---
titulo: STATUS — cola de prioridad histórica (pre 2026-07)
estado: histórico
dueño: Nikolai Tyukhay
fecha_archivado: 2026-07-05
---

# Cola de prioridad histórica de STATUS.md (sesiones 4–24, may 2026)

> Extraída de `STATUS.md` el 2026-07-05 (Fase 1 de la gobernanza de fuentes
> de verdad, `docs/GOBERNANZA_FUENTES_VERDAD.md`). La cola de trabajo **viva**
> es `PLAN.md`. Esto se conserva solo como referencia histórica: contiene
> ítems ya resueltos (✅/tachados) y algunos hilos abiertos antiguos
> (familia `[SIGUIENTE-DRIVE-*]`, `[SIGUIENTE-ANON-WARMUP]`,
> `[SIGUIENTE-VIABILIDAD-BAD-DEBT]`, `[SIGUIENTE-CUMPLIMIENTO-RIA-RGPD]`, etc.).
> Si algún hilo abierto sigue vivo, promoverlo a `PLAN.md` con disparador
> concreto (regla de promoción de `CLAUDE.md`).

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
Causa raíz confirmada con `rclone -vv` sobre BaRS1 ([inmueble] - W-02VND1):
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
`docs/superpowers/plans/PLAN_PRERELLENO_LLM_VIABILIDAD.md`. **Decisiones cerradas (D1-D5)**:
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

~~**[SIGUIENTE-ORGANIZADOR-UI]**~~ ✅ 2026-05-30 (sesión 28) — Botón "🤖 Organizar localmente" entregado: expander en la pestaña «Casos» con flujo Proponer→Aplicar, semáforo de precondiciones (`core.local_organizer.estado_precondiciones`), métricas, disclaimer PII y `help=` en todos los controles. +5 tests. Smoke manual de UI pendiente (no automatizable). **[SIGUIENTE]** real ahora: `[SIGUIENTE-ORGANIZADOR-VALIDACION]` — validar el organizador end-to-end sobre el piloto BaRS1 (`python -m scripts.organizar_local "BaRS1 - [inmueble] - (W-02VND1) - Vuelta" --plan` → revisar `07_AI cowork/_plan_reorganizacion.md` → `--execute`), o usar ya el botón nuevo desde la app.

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
`docs/superpowers/plans/PLAN_SUBDIVISION_CIUDADES.md`. 11 decisiones cerradas, 7 fases.

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
aceptación, entregables) en `docs/superpowers/plans/PLAN_SaRS1_anon_pipeline.md`.

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
limpia: leer `STATUS.md` + sección H<N> de `docs/superpowers/plans/PLAN_SaRS1_anon_pipeline.md`.

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

Plan completo en `docs/superpowers/plans/PLAN_BITACORA_CASOS.md`. 10 decisiones cerradas,
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

