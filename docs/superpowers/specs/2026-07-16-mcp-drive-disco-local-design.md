# Spec — MCP "Drive como disco" (montaje local GDFD)

> Diseño formal. **rev 3 (2026-07-16)** — right-sizing a V1 tras: 5 rondas adversariales
> (Gemini ×4 + Perplexity + Fable con CLAUDE.md), tanda de verificación en disco, handoff
> de right-sizing (13 agentes) y verificación del handoff contra el repo (8 agentes,
> 2 críticos confirmados 4/4 y 2/2). Estado: **aprobado para plan de implementación**.
> Catálogo función-a-función: `2026-07-16-mcp-drive-disco-local-catalogo-funciones.md`.
> Handoff de right-sizing: `../handoff-2026-07-16-rightsizing-mcp-drive-v1.md`.
> Memoria: `project-mcp-drive-disco-local`.

## Estatus epistémico

**[EMP]** = inferencia empírica verificada en ESTE montaje (2026-07-16), no documentada
por Google. **[DOC]** = respaldado por fuentes (DFIR / advisories). **[F0]** = a validar
en fase 0. La corrección del diseño **nunca** depende de un [EMP]/[F0] sin fallback.

---

## 1. Objetivo

Que Cowork Desktop (y Claude Code) opere **dos Google Drive montadas localmente** por
GDFD —`G:` (despacho, Tyukhay) y `H:` (cliente, E&V)— **como un disco**: leer, listar,
buscar, copiar, escribir; a velocidad de disco para lo cacheado y **sin el conector
nativo por API** (lento, con reautenticación por cuenta).

**Objetivo adicional (custodia):** integridad y trazabilidad — SHA-256 local, auditoría
append-only. La confirmación de subida a la nube **no** es objetivo de este servidor
(receta de skill sobre `google-despacho`, ver §5.1).

**No-objetivos:** contenido de Google Docs nativos, permisos/sharing, versiones,
comentarios, papelera → `google-despacho` (API).

**Realidad del montaje [EMP]:** `H:` = Stream puro, **100 % COLD** (79.225 ficheros,
caché ~0) → toda lectura de `H:` es descarga on-first-access. `G:` = Stream-con-caché,
**26 % COLD** (36.167 de 138.168; caché 21,9 GB). **`G:` NO es Mirror** (los Shared
Drives siempre se transmiten). Mapeo cuentas DriveFS: `105219…`=H:, `109893…`=G:.

---

## 2. Alcance — zonas por *tier* con carve-out de protocolo

La clasificación de tier se resuelve sobre **ruta canónica** (`resolve()` +
`relative_to`), **por patrón de segmento**, **después** de resolver atajos (§6.4), y se
aplica en **origen ∧ destino** de toda operación **y por cada nodo visitado en las
operaciones recursivas** (cláusula de travesía, abajo).

**Tier 0 — Prohibida (ni lectura):**
- Segmento `90_Notas personales` / `90_NOTAS_PERSONALES`. Nunca al modelo (regla dura
  de `CLAUDE.md`). *El checkout rclone ya la excluye en sus 3 llamadas — la poda que
  este tier generaliza.*

**Tier 1 — Forense-inmutable (lectura; mutación solo por protocolo):**
- Segmento `00_Input` (original forense) y backups (`G:\Otros ordenadores` + lista
  BACKUP configurable: `BACKUP`, `BACKUP MADRID`, `TWBCN-Backup2`, …).
- Semántica: **inmutabilidad de lo depositado**, no "cero escritura":
  - **Crear ficheros NUEVOS** bajo `00_Input` → permitido con precondición
    destino-inexistente (modo no-overwrite). *(El intake deposita en
    `00_Input/<fuente>/` — verificado `intake-expediente/SKILL.md:74-79`,
    `core/case_manager.py:971`.)*
  - **Carve-out de ficheros de protocolo** (ancla: **`MERGE_EXCLUSIONS`** de
    `core/config.py:305-313`, la fuente única real): `_caso.md` (editable por protocolo
    — el lock de checkout/checkin es un edit, `case_manager.py:605-652`),
    `_intake_log.jsonl` (append-only; el checkin además lo reescribe con la unión del
    merge), `MANIFEST_CHECKOUT.json`, `AUDITLOG_MERGE_*.jsonl`.
  - Toda otra sobrescritura/edit/move/rename de lo existente bajo Tier 1 → **rechazo**.
  - `copy` con **origen** Tier 1 y destino Tier 2 → legítimo (solo muta el destino).
- En backups no aplica carve-out alguno: solo lectura.

**Tier 2 — Workspace (mutable):**
- El resto de `G:`. **`H:` es SOLO-LECTURA en V1** (decisión estructural: ningún flujo
  real escribe ficheros en H: — verificado; la única mutación existente sobre E&V es
  `permissions.create` vía API en `core/share_drive.py`, fuera del ámbito FS de este
  MCP). Consecuencia: el gate de mutación-en-compartido y el staging especial de
  temporales quedan **V2**, cuando exista el primer flujo que escriba en H:.

**Cláusula de travesía (crítico 5.2, confirmado):** en toda operación recursiva
(`tree`/`copy_dir`/`hash_tree`/`search_content`/`read_multiple`/`extract_archive`) el
tier se **re-evalúa por CADA ruta visitada** (origen y destino efectivos, canónicos):
nodo Tier 0 → **poda del subárbol** + registro en auditoría; destino efectivo Tier 1
(fuera de carve-out) → **aborto**. *(Hoy `fsops.copy_tree` usa
`shutil.copytree(dirs_exist_ok=True)` — sobrescribe en silencio y no conoce zonas
[`fsops.py:113`]; esta cláusula es la guarda ausente.)*

**SIN borrado** en ningún tier (`delete_path` se retira de la superficie).

---

## 3. Arquitectura

### 3.1 Un único servidor FS
**Consolidar extendiendo `expedientes-xl` (Python).** Las lecturas necesitan guardas
propias del montaje (tiers, hidratación, atajos, `.g*`) que el `server-filesystem`
(Node) no puede aprender → se **jubila `expedientes`**; `expedientes-xl` es la base y
conserva sus nombres de tool (las skills de intake/checkout/checkin no cambian).
Resultado: **1 servidor FS + 1 API (`google-despacho`)**.

### 3.2 Concurrencia (right-sized)
- **Cap global** de E/S pesada: un **semáforo** (el único fallo observado: 2 pipelines
  pesados desmontan `G:`). Sin mutex por-ruta (inefectivo: Code y Cowork son **procesos
  stdio separados**; la serialización que importa ya existe — lock por nonce en
  `_caso.md`).
- Temporales con **nonce** (`mkstemp`); cubre la concurrencia real entre procesos.
- Workers con **timeout que responde** (el canal MCP contesta aunque la E/S siga) e
  hilos daemon. La **cancelación-que-aborta-E/S queda V2**, solo si se **observa**
  acumulación de hilos (no implementable limpio en Python/Windows; el escenario
  generador ya lo suprimen §6.2 + cap + timeouts).

### 3.3 Arranque
Wrapper poll-until-mount para **ambas** unidades (sondear una hoja poblada de cada una)
antes de arrancar, timeout por debajo del handshake MCP. (Fallo observado 2 veces;
Claude Desktop elimina entradas MCP que fallan al arrancar.)

---

## 4. Oráculo de hidratación

**[EMP/DOC]** Estado inferible de la BD interna
`%LOCALAPPDATA%\Google\DriveFS\<idCuenta>\metadata_sqlite_db`:
`item_properties.key='content-entry'` presente ⇒ bytes en `content_cache`. Las APIs de
Windows mienten (atributos `Normal`; `GetCompressedFileSizeW`=lógico; sin flag
`is_cloud_only`). Corroborado por DFIR (CyberEngage).

### 4.1 Diseño (tool #45 `hydration_status`)
- **HOT** ⟺ `content-entry` en BD **∧** blob presente en `content_cache` (validación
  cruzada; falso-HOT degrada a COLD).
- Lectura de la BD viva: **API de backup online de SQLite** (`Connection.backup()`
  desde `mode=ro`). **[EMP] verificado**: `integrity_check=ok` en 1,6 s, sin lock de
  GDFD. (File-copy del trío WAL: no atómico → corrupción intermitente; `immutable=1`:
  ignora el `-wal` → obsoleto. Ambos descartados.)
- **Caché TTL del snapshot (~5 s), obligatoria**: `backup()` se ejecuta **una vez por
  ráfaga**, todas las validaciones de la ráfaga leen el snapshot en RAM. Sin ella,
  50 operaciones × 1,6 s ≈ 80 s de thrashing antes de leer un byte → timeout del LLM.
- **Oráculo OPCIONAL, fail-closed**: BD privada/frágil/PII. Caído o esquema cambiado →
  estado "desconocido" = **tratar como COLD** (§6.2). Sin el oráculo, fail-closed
  castraría los árboles calientes legítimos — por eso el oráculo es **habilitador de
  V1**, no un lujo.
- Selección de BD por unidad: `105219…`→H:, `109893…`→G: (detectar por marcador, no
  hardcodear).

---

## 5. Superficie V1 (~21 tools)

Todas pasan tier (§2) y las guardas (§6) que correspondan.

**Leer**: `read_text` (con parámetros `head`/`tail`) · `read_multiple`.
**Navegar**: `list_dir` (con parámetro `sizes`) · `tree` · `get_metadata` ·
`resolve_shortcut` (§6.4) · `hydration_status` (#45).
**Buscar**: `search_name` · `search_content` (grep; con guarda §6.2 y poda Tier 0;
promovida por decisión explícita del usuario — regla de promoción de `CLAUDE.md`).
**Escribir** (Tier 2 / carve-out Tier 1; atómico §6.1): `create_dir` · `write_text` ·
`edit_text` · `append_text` · `write_file_base64`.
**Copiar**: `copy_path` · `copy_dir` (travesía §2 + guarda de árbol frío §6.2).
**Comprimir**: `extract_archive`.
**Integridad**: `hash_path` · `hash_tree`.

**V2 (diferido; promoción solo por disparador concreto — regla de `CLAUDE.md`):**
`move`/`rename` (doctrina de la casa: copia, nunca mueve; `move_file` marcado
destructivo) · `batch_rename` (si entra: pelado — dry-run + continue-on-error + informe
old→new en auditoría; **sin** journal/rollback: falsa transaccionalidad, la doctrina de
recuperación real es re-ejecutar-converge) · `create_zip` · `du` como tool (la lógica
interna ya la usa §6.2) · `verify_manifest` (duplica `rclone check --one-way` del
checkin, y el MANIFEST llavea por MD5 de rclone, no SHA-256) · escritura en `H:` + gate
de mutación-en-compartido + staging de temporales · cancelación-real de workers.

**CUT (sin disparador previsible):** `free_space` (semántica coja: caché ≠ cuota de
nube; el dato de caché queda interno a §6.2) · `confirm_sync` (#46, ver §5.1) ·
`map_owner`/`device_fingerprint` (#47/#48: especulativos; la custodia máquina↔acción ya
existe — `checkout_maquina` en el lock + evento `case_checkout`) · rango de bytes (#4) ·
leer-binario-al-modelo (#5) · `delete` · timestamps · ACL · symlinks · watch · ejecutar.

### 5.1 Confirmación de subida (ex-#46) — receta de skill, no tool
No hay señal local fiable de "pendiente de subir" (verificado: `local-content-checksum`
no existe; `dirty-handle` transitorio; heurística de timestamps inviable para custodia —
toques fantasma, drift). El estado determinista vive en el protobuf cerrado de
`operations`. Si un flujo lo exige: **skill** que tras escribir haga polling
`google-despacho.get_file_metadata` (`md5Checksum`/`modifiedTime`) con backoff. El MD5
solo valida transferencia nube==local; **el hash de custodia es el SHA-256 local**.
Nota para el intake: el evento `upload_*` acredita **depósito local verificado por
SHA-256**; la subida la garantiza GDFD (y `rclone check` cuando se retiran originales).

---

## 6. Guardas transversales

### 6.1 Escritura atómica
Nunca in-place: escribir a temporal **con nonce en la MISMA carpeta destino** y
`os.replace()`. (En `%TEMP%`/C: fallaría con **EXDEV** — no hay rename atómico entre
volúmenes.) Precedente de la casa: `registrar_outputs.py` usa temp+`os.replace`.
**[EMP/F0]** Protege la integridad **local**; **no** evita conflict-copies de la nube si
un tercero edita la versión web a la vez (límite inherente de GDFD; se documenta).
Con `H:` read-only, la visibilidad breve del temporal solo afecta a `G:` (aceptada:
los flujos actuales ya escriben ahí directo).

### 6.2 Guarda de hidratación — fail-closed
Antes de leer bytes >10 MB o de operar sobre un árbol:
- **HOT** → adelante. **COLD grande** → abortar `ERROR_FILE_NOT_HYDRATED` (el usuario
  fija offline en la UI de Drive o autoriza descarga; **`attrib +P` NO funciona en GDFD**
  — retirado, verificado por convergencia). **DESCONOCIDO** (oráculo caído) → tratar
  como COLD.
- Árboles: abortar si superan **volumen lógico (~150 MB) O conteo (~50 COLD)** — lo que
  salte primero (evita el rate-limit 403 por ráfaga de hidrataciones).
- Umbrales (10 MB / 150 MB / 50) = **defaults configurables** [F0]; la calibración no
  bloquea el arranque. **Sin silencios**: el error lista lo omitido.

### 6.3 Resolución de atajos + tier (anti-escape)
`resolve_shortcut` resuelve el `.lnk` (→ `\.shortcut-targets-by-id\<id>\` [EMP]) o
`shortcut_details` (BD). El destino se **re-clasifica por tier** y se valida contra la
raíz: fuera de `G:`/`H:`, o Tier 0, o (mutación) Tier 1 → **bloquear y registrar**.

### 6.4 Bloqueo de extensiones propietarias
`.gdoc`/`.gsheet`/`.gslides`: la lectura FS da `ERROR_INVALID_FUNCTION` a nivel kernel
[EMP] → interceptar y desviar a exportación por `google-despacho`.

### 6.5 Robustez de E/S Windows
Backoff exponencial (0,5/1/2 s) ante `ERROR_SHARING_VIOLATION` (`~$` de Office; si
persiste → "editado por humano") · prefijo `\\?\` para `MAX_PATH` · timeouts amplios en
lectura (un COLD <10 MB pasa §6.2 y puede tardar minutos).

### 6.6 Auditoría
**`.jsonl` append-only fuera del volumen Drive** (patrón `_intake_log.jsonl`; nunca DB).
Toda mutación registra: timestamp, actor, operación, ruta, resultado, motivo. **Hash
antes/después SOLO cuando la operación ya toca bytes**; en ops de solo-metadatos no se
exige (forzaría hidratación — rompería §6.2). Las podas Tier 0 y abortos también se
registran.

---

## 7. Seguridad y PII
Tier 0 = `90_Notas personales` nunca al modelo (incluida travesía). Tier 1 = original
forense y backups sin mutación (salvo carve-out de protocolo). `H:` sin escritura en V1.
Path traversal / escape por atajos: §2 + §6.3. La lectura amplia de PII (Tiers 1-2) es
decisión explícita del usuario, trazada para mutaciones.

---

## 8. Interacción con lo existente y despliegue
- **`expedientes`**: se jubila. **`expedientes-xl`**: base del consolidado; nombres
  conservados; `delete_path` retirado. **`google-despacho`**: intacto.
- El **checkin autoritativo sigue por rclone** (no cambia nada).
- **Secuencia de despliegue** (evita desincronización Code↔Cowork): (1) servidor
  consolidado instalado; (2) validar en Claude Code; (3) re-empaquetar/re-importar
  skills en Cowork; (4) solo entonces migrar `organizar-sala-lectura` (usa nombres de
  `expedientes`) y jubilar `expedientes`. Nunca skill migrada con server viejo.

---

## 9. Fase 0 (spikes previos al código dependiente)
1. **Conflict-copies de `os.replace` en GDFD**: escribir en `G:`, replace, observar
   Drive web con/sin edición concurrente. Fija la redacción final de §6.1.
2. **Calibración de umbrales** §6.2 con casos reales.
3. **Selección de BD por unidad** (marcador robusto cuenta↔letra).

**Cerrados por verificación (2026-07-16):** `backup()` viable · `attrib +P` no fuerza
hidratación (retirado) · #46 sin señal local (→ receta skill) · #4 descartado ·
advisory GHSA-hc55-p739-j48w parcheado en `2025.7.1`, instalado `2026.1.14` → cubierto ·
`G:` no es Mirror (26 % COLD) · `H:` 100 % COLD · críticos 5.1/5.2 del handoff
confirmados contra el repo (4/4 y 2/2 refutadores fracasados).

---

## 10. Evidencia
Sondas y citas: catálogo asociado §Evidencia + handoff de right-sizing + resultados del
workflow de verificación (2026-07-16): intake deposita en `00_Input/<fuente>/`
(SKILL.md:74-79); `_caso.md` e `_intake_log.jsonl` en `00_Input`
(`case_manager.py:106`, `intake_log.py:131-133`); `MERGE_EXCLUSIONS`
(`config.py:305-313`); `copytree(dirs_exist_ok=True)` (`fsops.py:113`); checkout excluye
`90_Notas personales/**` ×3 (`checkout_template.cmd:10-25`); `share_drive.py:127` muta
permisos E&V vía API (único write a E&V, fuera de ámbito FS); H: 0 HOT / G: 102.001 HOT.
