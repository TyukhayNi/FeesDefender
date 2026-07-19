---
tipo: handoff
estado: consumido
consumido_por: "spec 2026-07-16-mcp-drive-disco-local-design.md + build PR #52"
migrado: "2026-07-19 (regla MEJORAS #77 / GOBERNANZA §5)"
---

# Right-sizing V1 — MCP "Drive como disco" (spec rev 2)

> Handoff para el hilo del spec. Objeto: `docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-design.md`
> (**rev 2**), con el catálogo `2026-07-16-mcp-drive-disco-local-catalogo-funciones.md` como fuente auxiliar.
> Método: análisis multi-agente Fable (4 lentes independientes — flujos reales, guardas,
> fiscal de sospechosos, cazador de huecos — + 3 refutadores adversariales por hueco;
> 13 agentes, evidencia grepeada en `.claude/skills/`, `core/`, `docs/DEAD_ENDS.md` y la
> memoria del proyecto). Encargo: el V1 MÁS PEQUEÑO que sea correcto y respete CLAUDE.md.
> No-negociables intactos: §2 tiers, §6.2 hidratación fail-closed, §6.4 anti-escape de atajos.

---

## 0. Decisión estructural: `H:` solo-lectura en V1

Ningún flujo real escribe hoy en `H:` (Drive E&V): `core/intake_drive.py` hace PULL
E&V→local; checkout/checkin van exclusivamente contra `gdrive_tl` (G:); las salas y el
export de correos escriben todos en G:. Declarar `H:` read-only en V1:
(a) elimina el gate §6.6 entero, (b) elimina el staging de `.tmp` fuera del área
sincronizada de §6.1, (c) reduce a cero el riesgo de mutación propagada a terceros —
sin perder ningún flujo. El gate §6.6 se reintroduce en V2 cuando exista el primer
flujo que escriba en H:.

Además, §6.6 tal como está redactado cubre «unidades de G: compartidas externamente», y
`EXPEDIENTES - TYUKHAY LEGAL` es visible para E&V → el gate literal gravaría **cada
`append_text` del intake actual**. Señal adicional de mal dimensionado.

---

## 1. Tabla keep / defer / cut — TOOLS

| Tool | Veredicto | Motivo (evidencia) |
|---|---|---|
| `read_text`, `read_multiple`, `list_dir`, `tree`, `get_metadata`, `search_name`, `create_dir`, `write_text`, `append_text` | **V1** | Callers reales en las 6 skills (sala lectura, intake, checkout/checkin, triaje). Regla por-lote de `DEAD_ENDS.md` (anti-53-min) justifica las variantes de lote/árbol |
| `list_dir_sizes` | **V1** | intake marca 0-bytes en la propuesta antes de copiar |
| `edit_text` | **V1** | el lock de la biblioteca edita `_caso.md` (write-then-verify con nonce) — checkout §2, checkin §4.2 |
| `write_file_base64`, `copy_path`, `copy_dir`, `extract_archive`, `hash_path`, `hash_tree` | **V1** | vías nombradas de intake-expediente; ya existen en `expedientes-xl` con tests |
| `hydration_status` (#45), `resolve_shortcut` | **V1** | forzosos: soportan los no-negociables §6.2 y §6.4 |
| `search_content` | **V1** | única novedad funcional no forzosa: consumidor en triaje-viabilidad (paso 2) + candidato nº1 con decisión explícita de Nikolai (regla de promoción de CLAUDE.md) |
| `read_head_tail` | V2 | no tool separada: **parámetros** `head`/`tail` de `read_text` (como el server-filesystem actual) |
| `du` | V2 | ningún flujo lo pide sobre G:/H: (el `du` del checkin es sobre carpeta local); la lógica interna ya la necesita §6.2 — exponerla luego es trivial |
| `move`, `rename` | V2 | doctrina de la casa = copiar-no-mover (la nomenclatura canónica se aplica al copiar); `move_file` actual marcado destructivo y evitado |
| `batch_rename` | V2 | ningún flujo renombra in-place. Si Nikolai reconfirma su candidato: entra **pelado** (dry-run + informe old→new en el log de auditoría), **sin** journal/rollback §6.3 |
| `create_zip` | V2 | sin caller (la vía ZIP+intake cubre; los ZIP los crea el usuario); reutilizará la guarda de árbol frío que `copy_dir` ya obliga a construir |
| `verify_manifest` (#34) | V2/CUT | duplica `rclone check --one-way` del checkin (validado en producción); **mismatch de dialecto**: `MANIFEST_CHECKOUT.json` llavea por MD5 de rclone, la tool hashearía SHA-256; componible en cliente sobre `hash_tree` |
| `free_space` | **CUT** | semántica coja admitida por el propio spec §4.2 («nunca se usa para prever si una escritura cabe»); si §6.2 necesita el dato, que sea interno |
| `confirm_sync` (#46) | **CUT** | no es tool de este servidor: §5.1 lo define como delegación íntegra a `google-despacho` (polling `files.get`) — es una **receta de skill** de 2 llamadas con tools ya desplegadas. **Contradicción interna del rev 2**: §1 lo declara no-objetivo y §5 lo incluye |
| `map_owner` (#47), `device_fingerprint` (#48) | **CUT** | [F0] especulativos, sin un solo caller; la custodia máquina↔acción ya existe (`checkout_maquina` en lock y evento `case_checkout` de `_intake_log.jsonl`) |

## 2. Tabla keep / defer / cut — GUARDAS E INFRA

| Guarda | Veredicto | Motivo |
|---|---|---|
| §2 tiers | **V1** | no-negociable — pero necesita los dos fixes críticos de §5 de este handoff |
| §6.2 fail-closed | **V1** | no-negociable; base empírica (26% COLD). Umbrales (10 MB/150 MB/50 COLD) como **defaults configurables** — la calibración [F0] no bloquea el arranque; el error debe listar lo omitido |
| §6.4 anti-escape atajos | **V1** | no-negociable; anclado a evidencia ([EMP] `.lnk`→`.shortcut-targets-by-id`) |
| §4.1 oráculo vía `sqlite backup()` | **V1** | **habilitador** de §6.2: sin oráculo, fail-closed castra `copy_dir`/`hash_tree` sobre árboles legítimamente calientes — el MCP nacería inusable. Verificado en vivo (`integrity_check=ok` 1,6 s). Mantener: opcional, caído ⇒ COLD |
| §6.1 atómica + nonce | **V1** | trivial (`mkstemp`); ya doctrina de la casa (`registrar_outputs.py` usa temp+`os.replace`); el nonce cubre la concurrencia real: procesos servidor separados Code↔Cowork |
| §6.5 bloqueo `.g*` → API | **V1** | fallo observado a nivel kernel (`ERROR_INVALID_FUNCTION`); coste = check de extensión |
| §6.7 backoff `~$`, `\\?\` MAX_PATH, timeouts | **V1** | fallos observados: `~$` reales en W-02VND1; nombres de caso largos por convención; un COLD pequeño (<10 MB) pasa §6.2 y puede tardar minutos |
| §6.7 auditoría **JSONL** fuera del volumen | **V1** | custodia = requisito del despacho; patrón `_intake_log.jsonl` ya en producción; hash solo cuando la op toca bytes (ya en rev 2, mantener) |
| §3.2 cap global de E/S pesada | **V1** | único sub-elemento con fallo observado: 2 pipelines pesados desmontan G: (memoria del proyecto). Implementación: un semáforo |
| §3.2 nonce en temporales | **V1** | parte de §6.1, gratis |
| §3.3 poll-until-mount (ambas unidades) | **V1** | fallo observado 2 veces: arranque en frío rompió `expedientes`; Claude Desktop ELIMINA entradas MCP que fallan al arrancar |
| §6.1 staging fuera de sync (H:) | V2 | cae solo con H: read-only |
| §6.6 gate drive compartido | V2 | cae solo con H: read-only; además duplica gates existentes (permission-prompt del harness + visto-bueno a nivel skill) y MCP no tiene canal interactivo (obligaría a two-phase con token) |
| §3.2 cancelación real de workers / zombie threads | V2 | no implementable limpio en Python/Windows (hilo bloqueado en el driver no se mata; la vía real son subprocesos); el escenario generador (lecturas GB colgadas) ya lo suprime §6.2 + cap + timeouts. V1 = timeout que responde y hilo daemon. Promover solo si se OBSERVA acumulación |
| §4.2 doble métrica free_space | V2 | sin consumidor; la mitad "cuota de nube" ya vive en `google-despacho` |
| §6.3 journal/rollback de batch_rename | **CUT** | doble especulación: la tool no tiene flujo Y el rollback puede fallar a mitad con los mismos `ERROR_SHARING_VIOLATION` que lo disparan (falsa transaccionalidad). Doctrina real de recuperación: re-ejecutar converge (checkin, `--checksum`) |
| §3.2 mutex por-ruta/por-caso | **CUT** | inefectivo por arquitectura: cada cliente MCP (Code, Cowork) lanza SU PROPIO proceso stdio — un mutex in-process no serializa nada entre procesos; la serialización que importa ya existe (lock por nonce en `_caso.md`) |
| Auditoría como DB (`mcp_audit.db`) | **CUT** | nadie consulta con queries; JSONL se grepea y se une por líneas (doctrina checkin); DB = esquema+locking+migraciones sin consumidor |

## 3. V1 mínimo (13 líneas)

1. Un servidor (`expedientes-xl` extendido, Python), nombres de tool conservados; `delete_path` jubilado.
2. Lectura: `G:` + `H:` enteras (backups incluidos). Escritura: **solo `G:`**, Tier 2.
3. Tiers §2 con **cláusula de travesía** y **carve-out de protocolo** (fixes críticos, §5).
4. ~21 tools: las 19 con caller real + `hydration_status` + `resolve_shortcut` + `search_content`.
5. `read_head_tail` como parámetros de `read_text`, no tool.
6. §6.2 fail-closed con umbrales configurables; sin silencios (listar lo omitido).
7. Oráculo §4.1 vía `sqlite backup()`, opcional; caído ⇒ tratar como COLD.
8. §6.1 atómica con nonce; §6.5 `.g*`→API; §6.7 backoff/`\\?\`/timeouts.
9. Auditoría: `.jsonl` append-only fuera del volumen (nunca DB).
10. Concurrencia: semáforo global + nonce. Nada más.
11. Arranque poll-until-mount de ambas unidades.
12. El checkin autoritativo sigue por rclone (no cambia nada).
13. Despliegue en la secuencia §8: server → validar en Code → re-importar en Cowork → migrar `organizar-sala-lectura` → jubilar `expedientes`.

## 4. Diferido a V2 (resumen)

Escritura en `H:` + gate §6.6 + staging §6.1; `move`/`rename`/`batch_rename`-pelado;
`create_zip`, `du`, `verify_manifest`, `read_head_tail`-como-tool; cancelación real de
workers (solo si se observa); `confirm_sync` como **receta de skill documentada** sobre
`google-despacho` (cero código de servidor). Promoción por la regla de CLAUDE.md:
disparador concreto, no completitud de diseño.

## 5. CRÍTICOS QUE FALTAN — dos (verificación adversarial 3/3 cada uno)

### 5.1 Tier 1 tal como está redactado mata el intake Y la biblioteca entera
§2 rechaza **toda** escritura cuyo origen o destino tenga segmento `00_Input`, sin
excepción. Pero: el intake deposita **en** `00_Input/<fuente>/` (`copy_path`/
`extract_archive`/`write_file_base64`); el `_intake_log.jsonl` forense vive **en**
`00_Input` (`core/intake_log.py`) y lo escriben intake, checkout y checkin con
`append_text`; y —agravante que emergió en la refutación— **`_caso.md` también vive en
`00_Input`** (`core/case_manager.py`): el lock de checkout/checkin es un `edit` de
fichero existente bajo `00_Input`, rechazado por diseño. §2 contradice frontalmente §8
(«intake/checkout/checkin no cambian»). El catálogo diverge del spec en el punto exacto
(su denylist de escritura era solo backups).

**Fix (una cláusula en §2):** Tier 1 = *inmutabilidad de lo depositado*, no
«cero escritura»:
- crear ficheros NUEVOS bajo `00_Input` con precondición destino-inexistente
  (modo no-overwrite) → permitido;
- carve-out explícito de **ficheros de protocolo** (espeja `core/config.py` PROTOCOL):
  `_caso.md` (lock, editable por protocolo), `_intake_log.jsonl` (append-only; checkin
  además lo reescribe con la unión del merge), `MANIFEST_CHECKOUT.json`;
- toda sobrescritura/edit/move/rename de lo demás existente bajo `00_Input` → rechazo;
- aclarar que `copy` con **origen** Tier 1 y destino Tier 2 es legítimo (solo muta destino).

### 5.2 Las operaciones recursivas solo validan tier en los extremos
§2 aplica el tier «en origen ∧ destino de toda operación» = argumentos de la llamada;
el único re-check de rutas derivadas es §6.4 (atajos). Nada obliga a re-evaluar tier por
nodo visitado en `tree`/`copy_dir`/`hash_tree`/`create_zip`/`search_content`/
`read_multiple`. Consecuencias: (lectura) `search_content` sobre la raíz de un caso
desciende a `90_Notas personales` y devuelve su contenido al modelo — Tier 0 violado;
(escritura) `copy_dir(backup Tier 1 → raíz de caso Tier 2)` pasa la validación de
argumentos y **sobrescribe dentro de `00_Input`** por travesía — el código actual que
§3.1 ordena conservar usa `shutil.copytree(dirs_exist_ok=True)` (sobrescribe en
silencio, `plugins/expedientes_xl/fsops.py`). Los flujos reales ya saben que la poda es
necesaria: checkout excluye `90_Notas personales/**` en sus tres llamadas rclone.

**Fix (una frase en §2, cero tools nuevas):** en toda operación recursiva el tier se
re-evalúa por CADA ruta visitada (origen y destino efectivos, sobre ruta canónica);
nodo Tier 0 → poda del subárbol + registro en auditoría; destino efectivo Tier 1 →
aborto de la operación.

### Candidato REFUTADO (3/3) — no reintroducir
«Recortar `confirm_sync` deja el intake sin detección de pérdida por fallo de sync».
Refutado por: (a) `G:` corre en **Mirror**, no Streaming (evidencia: `mirror_metadata_sqlite.db`,
memoria `project-ocr-pipeline-drive-mirror`) → lo depositado es fichero local durable,
la «evicción de caché» no existe como vector; (b) el intake deja `_ingest/` intacto por
default y los originales viven aguas arriba (Gmail/teléfono/H:); (c) la capacidad ya
existe fuera de este servidor (`google-despacho.get_file_metadata`, mergeado y cableado)
— si un flujo futuro lo exige, es una edición de SKILL.md, no superficie del V1;
(d) el propio spec lo declara no-objetivo en §1. Opcional barato: una línea en la doc
del intake aclarando qué acredita el evento `upload_*` (depósito local verificado por
SHA-256) y qué garantiza la subida (GDFD; y `rclone check` cuando se retiran originales).

## 6. Otras correcciones puntuales al spec (baratas, hacer en la misma pasada)

1. Resolver la **contradicción §1 ↔ §5** sobre `confirm_sync` (retirarlo de §5/§5.1;
   dejar solo la mención de no-objetivo).
2. §5: mover `verify_manifest`, `map_owner`, `device_fingerprint` fuera de la
   superficie V1 (V2/CUT según tabla).
3. §6.3: sustituir journal/rollback por «dry-run + continue-on-error + informe
   old→new persistido» — y solo si `batch_rename` entra.
4. §3.2: reescribir a «cap global (semáforo) + nonce + timeouts»; retirar mutex
   por-ruta y cancelación-que-aborta-E/S (nota: promover si se observa acumulación
   de hilos).
5. §6.7: fijar `.jsonl` como formato de auditoría (eliminar la opción `.db`).
6. §4.2: eliminar `free_space` de la superficie; el dato de caché queda interno a §6.2.
7. Anotar la decisión estructural: `H:` solo-lectura en V1 (§2) y su consecuencia
   (§6.6 y staging §6.1 pasan a V2).

## 7. Nota de procedencia

Ronda Fable (2026-07-16, multi-agente con verificación adversarial). Coincide con la
ronda Opus previa en: crítico de travesía (5.2), H: read-only, recorte de la superficie
forense auxiliar. Discrepa de la ronda Opus en: mata su crítico de checkin/confirm_sync
(dato Mirror); sube a V1 con evidencia `search_content`, `edit_text`, `tree`,
`get_metadata`, `list_dir_sizes`; y encuentra el crítico 5.1 (carve-out de protocolo en
Tier 1) que ninguna ronda anterior vio — el Tier 1 de rev 2 nació de la revisión de
rev 1 y se adoptó sin reconciliar con los flujos que escriben en `00_Input`.
