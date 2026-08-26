---
tipo: revision-adversarial
objeto: "diseño del Plan 3A-bis: la fila #5, la clase C1 y las tres piezas"
objeto_rev: "rama claude/feesdefender-plan3-decision-batches-844080, commit 34cdf6a"
commit: 34cdf6a
ronda: "16"
revisor: Codex
veredicto: NO-EJECUTABLE
marcador_nonce: q4mz
sha256_informe: c1c821f9f9de9b331f16ec67ba13e4a900147778aae9db525d362f40c8bc3602
adjudicado_en: docs/superpowers/plans/2026-08-26-apertura-v1-plan3a-bis-fila5.md §7
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R16.** El §1 conserva la voz del revisor sin una coma
> cambiada; la **adjudicación** vive en el **§7 del plan**
> (`docs/superpowers/plans/2026-08-26-apertura-v1-plan3a-bis-fila5.md`). Es la ronda de **DISEÑO**: se corrió **antes de escribir
> una línea de código**, que es para lo que existe.
>
> Veredicto `NO-EJECUTABLE`: **13 hallazgos** — 4 CRÍTICOS, 4 ALTOS, 3 MEDIOS, 2 BAJOS. Adjudicados: **13 confirmados,
> 0 refutados.**
>
> **Esta ronda EJECUTÓ.** El revisor corrió una sonda determinista, 146 tests focalizados y el resto de la suite salvo cinco módulos MCP que no coleccionan por dependencia ausente, y midió el comportamiento en vez de
> deducirlo. Los críticos salieron de las sondas.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:q4mz -->

NO-EJECUTABLE

## Resumen

Revisé el plan completo, el Plan 3A (§1.2, Task 6 parcial y §6), la spec §25 fila #5 y el código indicado.
Ejecuté una sonda determinista sobre copia, 146 tests focalizados y la suite restante hasta el 100 % excluyendo cinco módulos MCP que no coleccionan.
La afirmación central de B es falsa en producción: `buscar()` solo devuelve el catálogo, no la copia local registrada; la propia prueba vigente simula lo contrario registrando el canon como checkout.
La fila #5 sigue sin mutex en Streamlit, y dos pulls concurrentes dejaron el marcador con unos IDs y la ficha con otros.
La reconciliación del skip tampoco valida que los IDs del marcador coincidan con los argumentos: medí un skip que devolvió IDs nuevos sobre bytes marcados con IDs anteriores.
La primitiva atómica no satisface F4: una escritura de lock entre su lectura y su `os.replace` se perdió en la sonda, exactamente el riesgo que el criterio de salida declara cerrado.
Además, el no-op público ante `_caso.md` ausente convierte un pull correcto en sello perdido sin aplazamiento, y C-bis no define cómo devuelve su deuda al frontal.
El plan necesita revisión de diseño antes de producir código; los defectos no son detalles de implementación ni quedan cubiertos por sus quince fronteras.

## Hallazgos

### H16-01 — La regla B no distingue una copia local real

- **Severidad:** CRÍTICO.
- **Qué afirma el plan:** «`sellar ⟺ NOT decision.desviar AND NOT es_copia_prestada(case_id)`» y «`buscar` resuelve por catálogo y puede devolver una copia local» (§1, líneas 52-54; §4-B, líneas 219-229).
- **Por qué está mal:** `core/casos/case_locator.py:121-143` busca exclusivamente bajo `settings.casos_root`; no consulta `WorkspaceRegistry`. `es_copia_prestada` toma esa ruta de catálogo y la compara con las rutas locales del registro (`core/case_manager.py:835-847`). Una copia real está fuera del catálogo por contrato (`core/case_manager.py:803-831`; `core/casos/workspace_registry.py:149-155`), de modo que las rutas no coinciden. Sonda ejecutada: `PROBE_B_RESOLVED=<...>/casos/Caso prueba`, `PROBE_B_LOCAL=<...>/checkout-local`, `PROBE_B_ES_COPIA False`. Los nueve tests de `tests/test_guard_copia_prestada.py` pasan porque su helper registra `caso_path(case_id)` —el canon— como `local_path` (`:81-87`), no una copia externa real. `pull_drive_ev` también empieza por `localizar(case_id)` (`core/intake_drive.py:185-196`), así que no opera sobre un checkout fuera de `CASOS_ROOT`. `FEESDEFENDER_OFFLINE` tampoco se consulta en ese camino; la ambigüedad robusta vive en `CaseCatalog`/`CaseWorkspaceResolver`, que B no usa (`core/casos/case_catalog.py:56-76`; `core/casos/workspace_resolver.py:64-108`).
- **Consecuencia práctica:** el supuesto tercer estado no es alcanzable por el camino diseñado. Un checkout local real se rechaza/no se localiza o se opera contra el canon; la conjunción puede autorizar el sello sobre la copia equivocada y no cierra los casos offline, ambiguos ni fuera del catálogo.

### H16-02 — La fila #5 sigue sin el mutex exigido y admite resultados partidos

- **Severidad:** CRÍTICO.
- **Qué afirma el plan:** «C1» y el criterio de salida aseguran que no se pisa el lock, pero la estructura de tareas solo migra registradores, conserva la decisión y añade avisos (§§2, 4 y Tasks 2-6).
- **Por qué está mal:** la fuente canónica exige la fila #5 «bajo mutex» (`docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1765-1767`) y Plan 3A repite que las filas de protocolo pasan por la costura más mutex (`docs/superpowers/plans/2026-08-26-apertura-v1-plan3-write-set.md:416-425`). El bis no incluye `mutex_sesion`/`escritura` en File Structure (`:314-325`) ni frontera que exija adquisición. Los pulls Streamlit de `streamlit_app.py:511` y `:2398`, y el sello directo de `:2172`, no están dentro de `sostenido()`; el único pull protegido observado es el de `scripts/abrir_caso.py:649-671`. Sonda con dos hilos, rclone doblado y orden intercalado: `PROBE_C_CONCURRENT_ERRORS []`, `PROBE_C_CONCURRENT_MARKER TEAM-B FOLDER-B`, `PROBE_C_CONCURRENT_FICHA TEAM-A FOLDER-A`.
- **Consecuencia práctica:** dos pulls reales o un pull y otro escritor pueden terminar correctamente y dejar bytes/marcador vinculados a una carpeta y `_caso.md` vinculado a otra. El diseño contradice la decisión V1 y no serializa sus propios artefactos.

### H16-03 — F4 y el criterio de salida son incompatibles con la primitiva elegida

- **Severidad:** CRÍTICO.
- **Qué afirma el plan:** «un lock escrito entre la lectura y la escritura del sello no se pisa» (F4, línea 284) y «El lock de otra máquina no se pisa en la carrera del §1» (criterio 2, línea 373).
- **Por qué está mal:** `_atomic_write_caso_md` hace `read_md`, muta y después `os.replace`, «sin lock, sin versionado» (`core/case_manager.py:1195-1241`). Una escritura ajena entre `:1226` y `:1241` se sobrescribe. Lo medí inyectando un lock `prestado` con nonce `LOCK-ENTRE-READ-Y-WRITE` después de la lectura y antes del replace: resultado `PROBE_F4_ESTADO_FINAL disponible` y `PROBE_F4_NONCE_FINAL None`. El propio §«SIN VERIFICAR» admite la ventana (`plan:391-396`), pero la trata como riesgo residual mientras F4 la declara cerrada.
- **Consecuencia práctica:** construir A tal cual puede seguir borrando el lock de otra máquina; el test propuesto solo estrecharía el punto de inyección y daría una garantía que la primitiva no ofrece.

### H16-04 — C-1 puede sellar IDs de una carpeta que nunca produjo los bytes

- **Severidad:** CRÍTICO.
- **Qué afirma el plan:** «el *skip* por marcador con `rc == 0` reconcilia la ficha» (§4-C, líneas 240-247; F10).
- **Por qué está mal:** el skip lee únicamente `rclone_returncode`; no compara `team_id` ni `folder_id` del marcador con los argumentos (`core/intake_drive.py:206-229`). Un marcador ilegible o JSON corrupto también se trata como éxito (`:207-218`). Sonda: marcador `TEAM-ANTERIOR/FOLDER-ANTERIOR`, llamada `TEAM-NUEVO/FOLDER-NUEVO`; rclone no se ejecutó, y el resultado fue `PROBE_C_SKIP True`, `PROBE_C_MARKER_IDS TEAM-ANTERIOR FOLDER-ANTERIOR`, `PROBE_C_RESULT_IDS TEAM-NUEVO FOLDER-NUEVO`. C-1 manda sellar los IDs de la llamada en ese camino. `force=True` evita el skip, pero no corrige la falta de contrato del camino ordinario.
- **Consecuencia práctica:** la ficha puede afirmar que los documentos pertenecen a un Shared Drive/folder que jamás se descargó. Un marcador corrupto pasa de ser una decisión histórica tolerante a convertirse en evidencia positiva para mutar el canon.

### H16-05 — El no-op público hace que el aplazamiento se pierda en silencio

- **Severidad:** ALTO.
- **Qué afirma el plan:** A conserva «el no-op cuando el caso no existe o falta `_caso.md`» (§4-A, líneas 183-188), mientras B define el sellado solo por disponibilidad y C afirma que la deuda viaja al resultado.
- **Por qué está mal:** un directorio de caso existente sin `_caso.md` pasa `localizar`; `_read_fm` lo interpreta como estado `disponible` (`core/case_manager.py:694-713`), por lo que el guard no desvía. Tras rclone correcto, `register_drive_ev` retorna sin escribir por su contrato (`:479-485`). Sonda: `PROBE_C_SIN_FICHA_SKIPPED False`, `PROBE_C_SIN_FICHA_MARKER True`, `PROBE_C_SIN_FICHA_INDEX False`. La conjunción de B da “sellar”, no “aplazar”, y el registrador no devuelve confirmación.
- **Consecuencia práctica:** el pull se reporta correcto, existe un marcador de éxito y no existe sello ni aviso. El siguiente pull ordinario vuelve por skip y repite el mismo no-op: C simula un consumidor, pero no acredita que haya consumido nada.

### H16-06 — C-bis promete un aviso sin definir ningún canal para producirlo

- **Severidad:** ALTO.
- **Qué afirma el plan:** «`streamlit_app.py:2172` […] si el caso no está disponible en el canon, no sella y avisa» (§4-C-bis, líneas 267-270).
- **Por qué está mal:** `register_drive_ev` devuelve `None` en éxito, idempotencia y no-op (`core/case_manager.py:467-515`); los campos `registro_aplazado*` solo se añaden a `DriveIntakeResult`, que no existe en esta vía. El bloque directo atrapa cualquier excepción y hace `pass` (`streamlit_app.py:2165-2178`), y en el mismo `try` llama también a `cache_drive_folder_info`, otra mutación de `_caso.md` que C-bis no clasifica. Además, el sello ocurre antes del pull (`:2165-2172` frente a `:2380-2417`), por lo que puede quedar adelantado aunque rclone falle.
- **Consecuencia práctica:** Task 5 no especifica una conducta implementable que distinga “sellado”, “idempotente”, “no existe ficha” y “aplazado”; el frontal puede seguir callando exactamente la deuda que C3 exige hacer visible.

### H16-07 — El E2E propuesto no prueba la fuente canónica ni sus cuatro planos

- **Severidad:** ALTO.
- **Qué afirma el plan:** «por cada uno de los tres estados […] doblar los dos destinos (canon y bandeja)» (Task 6, líneas 357-360).
- **Por qué está mal:** la spec exige comparar cuatro planos: árbol/canon, llamadas externas, estado local de aplicación y estado de canal (`spec:1800-1808`); Plan 3A también lo exige (`plan 3A:423-425,437-445`). El bis reduce la prueba a dos rutas. Además, una copia local prestada no es la bandeja: es un tercer árbol fuera de `CASOS_ROOT`, precisamente el que el código no resuelve (H16-01). No hay frontera para `FEESDEFENDER_OFFLINE`, `AmbiguousCase`, registro ausente/ilegible, ruta externa, marcador corrupto, IDs divergentes, `force`, dos pulls concurrentes o adquisición del mutex.
- **Consecuencia práctica:** el criterio puede quedar verde sin demostrar que el canon no cambió, que no hubo llamada externa indebida, que el estado local es coherente o que el camino de checkout existe realmente.

### H16-08 — El guard AST no cierra la clase C1 que el plan dice cerrar

- **Severidad:** ALTO.
- **Qué afirma el plan:** «Los tres registradores son las únicas mutaciones del fichero que no [usan `_atomic_write_caso_md`]» y el trinquete basta con exigir un único llamador de `_write_case_index` (§2, líneas 90-98; F3-bis).
- **Por qué está mal:** `core/casos/case_locator.py:322-341` (`_update_ciudad_metadata`, llamado por `move_to_city`) lee y reescribe `_caso.md` directamente desde una foto mediante `index.write_text`; `scripts/migrate_05crm_buckets.py:334-339` también lo reescribe con `write_md`. El guard propuesto cuenta llamadores de `_write_case_index`, así que ambos lo pasan. En el propio `case_manager`, `_atomic_write_caso_md` tiene seis usos de producción: `ensure_case`, cuatro transiciones de lock y `update_pull_state` (`:425,750,771,789,799,1386`), no la descripción exhaustiva del plan.
- **Consecuencia práctica:** el plan declara cerrada una propiedad global que su guard no observa; otra mutación por snapshot puede volver a pisar el lock sin romper F3-bis.

### H16-09 — La regresión del cuerpo está incompleta y su precedente factual es falso

- **Severidad:** MEDIO.
- **Qué afirma el plan:** «una línea de cortesía» puede quedar obsoleta y «`estado`, `cliente`, `cuantía`, `tipo_caso`, `dirección` y `ciudad` ya se mutan por `_atomic_write_caso_md` sin refrescar el cuerpo» (§4-A, líneas 196-205).
- **Por qué está mal:** `register_expediente` también proyecta `sudespacho_expedientes` al cuerpo bajo `## Expedientes sudespacho` (`core/case_manager.py:113-116,159-215`), por lo que A deja obsoleta una sección completa, no solo la línea Drive. Los usos actuales de la primitiva actualizan `tipo_caso`, `direccion`, `id_go`, `ciudad`, locks y estado de pull (`case_manager.py:404-425,726-799,1330-1386`); no encontré mutadores atómicos de `cliente`, `cuantia` o `estado` general. El cuerpo tiene contratos activos: navegación y wikilinks (`.claude/skills/_shared/registrar_outputs.py:149-174`; `tests/test_skill_registrar_outputs.py:64-88`), crosslinking (`core/linker.py:18-60`) y preservación explícita en CP11 (`scripts/repository_cli.py:1137-1177`; `tests/test_repository_cli_guard_pull.py:149-162`).
- **Consecuencia práctica:** quien ejecute el plan no sabe qué proyecciones humanas se acepta dejar obsoletas; la justificación minimiza un cambio visible y cita como precedente mutaciones que no existen.

### H16-10 — Pieza A no conserva el comportamiento de un fichero sin frontmatter

- **Severidad:** MEDIO.
- **Qué afirma el plan:** «El contrato público de los tres se conserva» y cada mutator toca «solo sus claves» (§4-A, líneas 175-194).
- **Por qué está mal:** hoy, si `_caso.md` existe pero no empieza por `---`, cada registrador toma `fm={}` y reconstruye un índice completo mediante `CaseMeta` + `_write_case_index` (`core/case_manager.py:180-215,487-515,602-629`). `_atomic_write_caso_md` en cambio obtiene `fm={}` y conserva el texto entero como cuerpo (`core/utils.py:204-212`; `case_manager.py:1226-1241`). Un mutator limitado a las claves de la tabla solo puede crear, por ejemplo, `meta.drive_ev_*`; no reconstruye los campos superiores `case_id`, `tipo`, `fase`, `fecha`, `estado`, `ciudad`, etc. que hoy produce `_write_case_index` (`:144-155`).
- **Consecuencia práctica:** sobre un fichero legacy sin frontmatter, la misma llamada pública pasa de reparar/reconstruir un índice completo a dejar un índice parcial. El plan no declara esa ruptura ni una frontera que la detecte.

### H16-11 — Los mutantes no son uno por frontera y el recuento no cuadra

- **Severidad:** MEDIO.
- **Qué afirma el plan:** «Un mutante por frontera» y «un mutante que mate más tests […] está mal apuntado» (§5, líneas 274-277), con salida «quince fronteras, quince mutantes» (`:377`).
- **Por qué está mal:** F1 y F2 proponen el mismo cambio —volver a `_write_case_index`—, que simultáneamente borra clave ajena y cuerpo (`core/case_manager.py:109-156`), por lo que necesariamente mata ambas fronteras. Forzar `sellar=True` (F5) también viola F6; devolver `registro_aplazado=False` (F8) suprime el aviso condicionado y puede matar F12. A las quince numeradas se añade F3-bis «con su propia prueba de mutación» (`plan:297-299`): son dieciséis mutaciones declaradas, no quince.
- **Consecuencia práctica:** el arnés exigido por el propio plan abortaría por sobremuerte o el informe de mutación atribuiría una muerte a una propiedad distinta de la que dice probar.

### H16-12 — La afirmación absoluta sobre la imposibilidad de reparar ignora `force`

- **Severidad:** BAJO.
- **Qué afirma el plan:** «si el primer sellado falla o no ocurre por cualquier motivo, nada lo repone jamás» (§3.1, líneas 162-167).
- **Por qué está mal:** el retorno anticipado está condicionado por `not force` (`core/intake_drive.py:206`). Con `force=True`, se ejecuta rclone y, si devuelve 0, se alcanza `register_drive_ev` (`:231-322`).
- **Consecuencia práctica:** la motivación exagera el defecto y F10 no fija la diferencia contractual entre reparación ordinaria y reparación forzada.

### H16-13 — Dos cifras/descripciones de código son inexactas

- **Severidad:** BAJO.
- **Qué afirma el plan:** «La usan las cinco transiciones del lock y el `ensure_case`» y `dir_intake` compone el destino en «literalmente dos líneas» (§2 y §4-B).
- **Por qué está mal:** hay cuatro transiciones de lock que llaman a `_atomic_write_caso_md` (`core/case_manager.py:750,771,789,799`), más `ensure_case` (`:425`) y `update_pull_state` (`:1386`). `dir_intake` ocupa `:912-916` para resolver base, consultar guard y bifurcar. Las líneas citadas para los tres registradores (`:215,515,629`) sí son exactas: son sus llamadas al constructor, no sus definiciones.
- **Consecuencia práctica:** no cambia por sí solo la decisión, pero desacredita el censo que sirve de premisa al trinquete y debe corregirse antes de ejecutar el plan.

## Lo que verifiqué y resultó CORRECTO

- Los tres registradores actuales destruyen claves ajenas y cuerpo al reconstruir: sonda `PROBE_A_CLAVE_AJENA False`, `PROBE_A_NOTA_MANUAL False`; código `core/case_manager.py:109-156,159-215,467-515,583-629`.
- Sus dos no-ops, comparaciones idempotentes y estampado de `meta.actualizado_en` existen en las líneas citadas; `_atomic_write_caso_md` también estampa `meta.actualizado_en` cuando `meta` es dict (`:1231-1234`).
- El skip con marcador `rc == 0` retorna antes del sellado (`core/intake_drive.py:206-229,320-322`).
- Hay tres llamadores productivos de `pull_drive_ev` (`scripts/abrir_caso.py:144`; `streamlit_app.py:511,2398`), un sello directo (`streamlit_app.py:2172`) y un solo llamador productivo de `get_drive_ev_ids` (`streamlit_app.py:1286`).
- CP11 relee `_caso.md` pegado al push y conserva su cuerpo (`scripts/repository_cli.py:885-910,1137-1177`).
- `_caso.md` está en `MERGE_EXCLUSIONS` y la bandeja se integra por CP10 (`core/config.py:391-399`; `scripts/repository_cli.py:872-910,951-992`).
- El censo corregido es 83: `tests/test_escritura_censo.py:49-75`; sus tests pasaron.
- Pasaron 128 tests focalizados de intake/no-op/caso/checkin y 18 de censo/guard. La suite restante llegó al 100 %: solo dos fallos de wrapper MCP por la dependencia ausente descrita abajo.

## Lo que NO pude verificar

- **Suite con semillas 777 y 31337:** el intérprete indicado no tiene `pytest-randomly`; `--randomly-seed=777` fue rechazado y `pip show pytest-randomly` devolvió “Package(s) not found”.
- **Suite completa sin exclusiones:** cinco módulos no coleccionan porque falta `mcp.server.fastmcp` (`test_email_export_mcp_server.py`, `test_expedientes_xl_integracion.py`, `test_expedientes_xl_server.py`, `test_gmail_mcp_server.py`, `test_google_despacho_server.py`). Al excluirlos, solo fallaron dos tests de `test_expedientes_xl_wrapper.py` por la misma dependencia. No atribuyo esos fallos al plan.
- **rclone/Drive real y dos máquinas físicas:** no se usaron. Las carreras se indujeron sin `sleep`, con hilos y subprocess doblado sobre la copia; prueban el orden de I/O local, no la red real.
- **Los quince mutantes propuestos:** no existe todavía el diff; solo pude demostrar estáticamente que varios cambios propuestos afectan más de una frontera.
- **Genealogía del archive respecto de `34cdf6a`:** la copia no contiene `.git`; verifiqué contenido y hashes, no ascendencia Git.

## SHA-256 del documento revisado

- **Al abrir:** `743DD039A8F1DAB2F06CAB4EF368503BC07973B30278BF36CACAC44D3552E6A1`
- **Al cerrar:** `743DD039A8F1DAB2F06CAB4EF368503BC07973B30278BF36CACAC44D3552E6A1`

<!-- informe-literal:fin:q4mz -->

## 2. Evidencia verificada por el adjudicador

**Contra la fuente, no contra el informe.** Lo que el adjudicador comprobó por su cuenta antes de
aceptar los críticos:

1. **H16-01** — `es_copia_prestada` es **inerte en producción**: `buscar()` solo mira bajo `CASOS_ROOT` y el registro solo contiene rutas fuera de él, así que la comparación no puede casar. Sonda del revisor: `PROBE_B_ES_COPIA False`. **Reproducido por el adjudicador** con una copia local real registrada fuera del catálogo: `es_copia_prestada = False`.
2. **H16-02** — la fila #5 sigue sin el mutex que la spec exige; dos pulls concurrentes dejaron marcador y ficha con ids distintos (`PROBE_C_CONCURRENT_MARKER TEAM-B`, `PROBE_C_CONCURRENT_FICHA TEAM-A`).
3. **H16-03** — F4 es incompatible con `_atomic_write_caso_md`: lock inyectado entre la lectura y `os.replace` → `PROBE_F4_ESTADO_FINAL disponible`, `PROBE_F4_NONCE_FINAL None`. **Verificado además contra el propio documento**, que declara la ventana abierta en su §«SIN VERIFICAR» mientras F4 la declara cerrada.
4. **H16-04** — el skip por marcador no compara los ids del marcador con los argumentos: `PROBE_C_MARKER_IDS TEAM-ANTERIOR`, `PROBE_C_RESULT_IDS TEAM-NUEVO`.

**Lo que el revisor verificó y resultó CORRECTO**, y que coincide con lo que el plan ya había
medido:

- los tres registradores destruyen claves ajenas y cuerpo (`PROBE_A_CLAVE_AJENA False`, `PROBE_A_NOTA_MANUAL False`) — coincide con la medición del §1 del plan;
- el skip con marcador `rc == 0` retorna antes del sellado;
- tres llamadores de `pull_drive_ev`, un sello directo, y **un** solo llamador de `get_drive_ev_ids`;
- el censo corregido es **83**, y sus tests pasan.

**Lo que el revisor NO pudo verificar, y se declara como tal** (no como refutado): su intérprete no
tiene `pytest-randomly`, así que **la suite con las dos semillas (777 y 31337) queda SIN VERIFICAR
por su parte**; cinco módulos MCP no coleccionan por una dependencia ausente de su entorno; y sin
`.git` no puede acreditar la genealogía del archive, solo su contenido y su hash.

## 3. Cadena del acta

- `marcador_nonce: q4mz`, un par de marcadores en orden, el nonce no aparece fuera de ellos
  salvo en el frontmatter y en esta línea.
- `sha256_informe` recomputado al archivar sobre el bloque literal canonicalizado:
  `c1c821f9f9de9b331f16ec67ba13e4a900147778aae9db525d362f40c8bc3602`.
- **Objeto no mutado:** el revisor operó sobre un `git archive` sin `.git` y reportó el `sha256` del
  documento revisado **al abrir y al cerrar**, coincidentes. Ésa es la prueba de no-mutación que
  sustituye al `git status` limpio.
- **Aviso de método, de esta sesión:** al calcular el digest de la R20 obtuve un valor y dos minutos
  después otro — el revisor **seguía escribiendo**. La presencia de `INFORME.md` no es la señal de
  fin; lo es la salida del proceso. Un digest solo significa algo sobre un fichero terminado.
