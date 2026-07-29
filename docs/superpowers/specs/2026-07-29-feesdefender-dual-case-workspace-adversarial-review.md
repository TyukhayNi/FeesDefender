# Revisión adversarial — FeesDefender dual: expediente activo local/Drive

**Fecha:** 2026-07-29.
**Revisor:** Claude Code (Opus 5), en solo lectura.
**Objeto:** `2026-07-29-feesdefender-dual-case-workspace-design.md` **rev. 1**
(commit `8d9c96c`, rama `codex/feesdefender-dual-spec`), contrastada contra el
código, scripts, plugins y skills vigentes en ese mismo commit.
**Mandato:** §19 de la SPEC (10 puntos a refutar) + los 10 bloques de encargo de
Nikolai (modelo de estados, resolución, `_caso.md`, `_intake_log.jsonl`, cero
escritura, `_pendiente_checkin/`, registro local, plugins/skills/runtimes,
opción 2 frente a 3, fases y criterios).

**Veredicto: REQUIERE REVISIÓN.**

La arquitectura es correcta y la opción 2 está bien elegida. Lo que no estaba
listo era el **contrato**: cuatro huecos impedían escribir el plan de la Fase 1
sin fabricar deuda, y hay una vía de escritura al canon (el plugin y las skills)
que la frontera de entrypoints Python no puede cerrar por construcción.

**Adjudicación:** todos los B0 y los A **aceptados**; corregidos en la **rev. 2**
de la SPEC (su §20 los mapea uno a uno). Los M van a
`docs/MEJORAS_FUTURAS.md` #101-#103.

**Nota de método.** Se intentó delegar el barrido mecánico a Gemini vía `agy`
(CLAUDE.md: la revisión adversarial de código es delegable). Devolvió
*"Individual quota reached"*, así que **todos los hallazgos se verificaron
directamente contra el fuente**, con fichero y línea. Es la disciplina de
`feedback-agy-review-adjudicar-severidad`: un revisor sin cupo no refuta, deja
sin verificar.

---

## B0 — bloqueaban escribir el plan

### B0-1. `--case-dir` en la Fase 1 sin migrar `intake_log` parte en dos la trazabilidad y crea carpetas fantasma en Drive

**SPEC:** §12 Fase 1, §11.4, §5.3.
**Código:** `core/intake_log.py:145-201`, `core/config.py:547-550`,
`core/casos/case_locator.py:26-43`, `scripts/sala_maquina.py:303,358`.

**Afirmación atacada:** que la Fase 1 pueda entregar el resolver y `--case-dir`
de forma aislada, dejando `append_event` para «poder escribir en el workspace ya
resuelto» sin asignarle fase.

**Contraejemplo:**

1. Fase 1 entrega `--case-dir C:\Users\…\Desktop\BaRS9 - … - (W-02ZZZZ) - …`.
2. `scripts/sala_maquina.py` (no migrado hasta la Fase 3) recibe el `case_dir` y
   escribe OCR/MD ahí — correcto.
3. En `sala_maquina.py:303` llama
   `append_event(case_id, "procesado_sala_maquina", …)`.
4. `append_event` → `log_path(case_id)` → `caso_path(case_id)` → `path_for`, que
   **no conoce el workspace** y, si no encuentra la carpeta, **devuelve la ruta
   flat inexistente** (`case_locator.py:43`).
5. `intake_log.py:185` ejecuta `path.parent.mkdir(parents=True, exist_ok=True)`
   → **crea `CASOS_ROOT/<case_id>/00_Input/` en el Drive compartido** y escribe
   ahí el evento.

**Impacto:** los bytes van al local y la custodia al canon: el split brain exacto
que la SPEC existe para impedir, producido por la propia Fase 1. Además fabrica
un expediente fantasma en la unidad de E&V (el bug ya ocurrido con W-02ZIIF,
documentado en `tests/test_sala_maquina_ejecutar.py:838` y en el docstring de
`sala_maquina.py:127-147`).

**Corrección mínima:** declarar `core.intake_log` componente de **Fase 1**;
`append_event` exige el workspace o el log ya resuelto; `log_path(case_id)` se
retira; `--case-dir` no se publica antes.

---

### B0-2. La reconciliación por prefijo del `_intake_log.jsonl` no tiene baseline, ni representación comparable

**SPEC:** §6.3 párrafo final, §4.8, §14.3.
**Código:** `core/config.py:391-399` (`MERGE_EXCLUSIONS` incluye
`_intake_log.jsonl`), `scripts/repository_cli.py:330-345` (`inventario_local`
salta las exclusiones), `repository_cli.py:475-484` (el manifest se construye
desde ese inventario), `repository_cli.py:736-767` (`_append_evento_drive`),
`core/intake_log.py:204-230` (`read_events`).

**Afirmación atacada:** que exista un «baseline protocolario» contra el que
comparar el prefijo.

**Contraejemplo:**

1. `MANIFEST_CHECKOUT.json` se genera desde `inventario_local(local)`, que en la
   línea 342 descarta todo lo que casa `MERGE_EXCLUSIONS` → **el manifest no
   contiene ni el hash ni el tamaño del `_intake_log.jsonl`**. No hay baseline
   del log en ningún artefacto.
2. Aunque se añadiera: `_append_evento_drive` **no hace append**, hace pull →
   `splitlines()` → filtra líneas en blanco → `"\n".join(lineas) + "\n"` → push
   (`repository_cli.py:754-767`). El fichero canónico se **reescribe entero** en
   cada evento, con `errors="replace"` (línea 756): un byte no decodificable se
   convierte en `U+FFFD` de forma permanente y el final de línea se normaliza.
3. Del otro lado, `read_events` (`intake_log.py:222-227`) **descarta en
   silencio** las líneas no parseables.

Resultado: comparar por bytes da divergencia falsa en cada checkin (paso 2);
comparar por eventos parseados **oculta** la línea parcial de un crash (paso 3),
que es precisamente el escenario que el mandato §19.3 pide cubrir.

**Impacto:** la Fase 2 no puede implementar §6.3. O bloquea siempre, o pierde
evidencia sin avisar — en un log cuyo propósito declarado es prueba documental.

**Corrección mínima:** baseline del log como artefacto propio del protocolo
(hash + nº de líneas); comparación por identidad de evento
`(ts, actor, event, hash(details))`; cola no parseable **bloqueante**; el canon
deja de reescribirse (append real).

---

### B0-3. Las skills de checkout/checkin son una segunda implementación del protocolo y no pueden escribir el registro local

**SPEC:** §9.3, §12 Fase 5, §15.
**Código:** `.claude/skills/checkout-caso/SKILL.md:27,35,39-41,55,62,72`;
`.claude/skills/checkin-caso/SKILL.md`;
`plugins/expedientes_xl/tiers.py:31-32,95-101`.

**Afirmación atacada:** que las skills ya comparten el cerebro y que basta con
darles una tool común en la Fase 5.

**Contraejemplo:**

1. La skill declara «paridad con la CLI» (línea 27) pero **ejecuta el protocolo
   ella misma en prosa**: genera nonce, escribe `estado_repositorio: prestado` en
   el `_caso.md` del Drive, espera el sync lag, relee (39-41) y registra
   `case_checkout` «vía conector `expedientes-xl` `append_text`» con `ruta_local`
   (55) — el campo que §6.1 manda retirar.
2. El registro privado (§6.2) lo escribe **solo la CLI Python** (Fase 2). La
   skill no lo conoce ni puede alcanzarlo desde Cowork.
3. Tras la Fase 2, un checkout desde Cowork deja Drive `prestado` con nonce y
   máquina correctos y **sin entrada en el registro**.
4. En el PC, cualquier entrypoint migrado resuelve por identidad: §7.2 paso 5
   exige «una entrada local con el mismo caso, titular, máquina y nonce»; no la
   hay → paso 7 → **bloqueo**. El titular queda bloqueado en su propio checkout.
5. §15 lo cataloga como «checkout anterior sin registro» que «requiere
   `--case-dir` y una operación explícita de adopción». La vía normal de trabajo
   de Cowork se convierte en una fábrica de checkouts inadoptables durante tres
   fases.

**Impacto:** dos implementaciones vivas del protocolo con estados incompatibles,
y el `ruta_local` que §6.1 retira sigue publicándose por la vía de la skill.

**Corrección mínima:** decidir antes de la Fase 1 entre (a) la skill deja de
adquirir el lock y aborta donde la CLI no llega, o (b) la Fase 2 define un
registro que la skill pueda escribir y verificar. *(La rev. 2 elige (a).)*

---

### B0-4. `decidir_escritura` es una única función pura del estado: «denegar lo nuevo y desviar lo legacy» no es implementable

**SPEC:** §11.1, §3.2, §12 Fase 2.
**Código:** `core/repository_checkout.py:541-577`; consumidores
`core/case_manager.py:705,729-741`, `core/intake_lotes.py:73-100`,
`core/intake_manual.py:260`, `core/intake_drive.py:193`,
`core/email_export.py:1421-1431`.

**Afirmación atacada:** que la bandeja pueda quedar «solo como compatibilidad»
sin mantener dos políticas activas (mandato §19.6).

**Contraejemplo:** `decidir_escritura(estado, ruta, origen)` decide
**exclusivamente por `estado`**; no recibe, y no puede recibir, la información
«esto es contenido preexistente» frente a «esto es una mutación nueva». Solo hay
dos configuraciones posibles:

- **Dejarlo desviando:** en las Fases 3-6, cualquier llamador no migrado (UI
  Streamlit, `intake_manual`, `intake_drive`, lotes de correo) sigue escribiendo
  en el árbol de Drive, dentro de `_pendiente_checkin/`, mientras la copia
  operativa es la local. La bandeja es un directorio del caso canónico: son bytes
  nuevos en el canon durante un préstamo.
- **Voltearlo a denegar en la Fase 2:** se voltea para **todos** los llamadores a
  la vez (es un único punto de estrangulamiento). Es lo correcto, pero rompe
  funcionalidad el día del merge y la SPEC no lo dice ni prevé bandera.

**Impacto:** la SPEC permitía las dos lecturas, y la cómoda mantenía el split
brain durante toda la migración.

**Corrección mínima:** §11.1 declara que la Fase 2 cambia `decidir_escritura` a
denegar para todo estado no-`disponible` —`conflicto` incluido— y para todos los
llamadores simultáneamente; `pendiente_checkin` deja de emitirse; criterio de
retirada = cero ficheros en la bandeja verificado por inventario, en PR aparte.

---

## A — corregir antes de implementar la fase afectada

### A-1. Todas las mutaciones del lock son sobrescrituras ciegas; el doble checkout sigue siendo posible

**SPEC:** §8.2, invariantes 1 y 11, §14.3.
**Código:** `scripts/repository_cli.py:785-799` (`_push_caso_md` = `copyto` sin
compare-and-swap), `441-453` (adquisición), `469-470` (rollback), `628-630`
(conflicto), `659-663` (liberación); `core/repository_checkout.py:222-233`.

**Contraejemplo (dos checkouts válidos simultáneos):**

- `t=0` A hace CP0: lee `disponible`.
- `t=0,5` B hace CP0: lee `disponible` (el push de A aún no ha ocurrido).
- `t=1` A escribe `nonce_A`.
- `t=5` A relee: ve `nonce_A` → «lock adquirido», empieza a copiar.
- `t=6` B escribe el frontmatter **que pulló en `t=0,5`** con `nonce_B`:
  `_push_caso_md` no compara nada, así que **borra el lock de A**.
- `t=10` B relee: ve `nonce_B` → «lock adquirido». Copia.

Los dos tienen copia local escribible; Drive dice B. A no vuelve a mirar el lock
hasta el checkin, donde sale `LOCK_MISMATCH` con horas de trabajo dentro. El
sleep de 4 s (`_SYNC_LAG_S`) no cierra la ventana: la agranda quien pulle antes.
Además, el rollback de la línea 469 aplica `aplicar_lock_cancelado` **sin
verificar que el nonce vigente sigue siendo el propio**, con lo que un fallo de
rclone de A puede liberar el lock de B.

**Impacto:** invariante 1 refutado en el protocolo que la SPEC hereda sin tocar.
Concuerda con `MEJORAS #93` (fallo A: un lock que falla en silencio induce
confianza).

**Corrección mínima:** re-verificación del nonce **después de materializar y
antes de emitir `case_checkout`**; write-then-verify y refuse-if-not-mine en
**toda** mutación del lock; imposible por contrato pushear un lock cuya lectura
previa sea `prestado` con otro nonce.

---

### A-2. El orden real del checkin libera el lock con la bandeja sin verificar y duplica `case_checkin` al reintentar

**SPEC:** §8.5 pasos 5-7, invariante 8, §14.2.
**Código:** `scripts/repository_cli.py:598-607` (CP8 verifica por hash **solo**
lo subido por el plan), `641-649` (`case_checkin`), `651-656`
(`_integrar_bandeja`), `658-663` (liberación), `697-724` (la integración solo
imprime avisos si falla).

**Contraejemplo:** caso prestado; durante el préstamo un pipeline no migrado
depositó `_pendiente_checkin/email/2026-07-29_email_01/x.eml` en Drive.

1. CP1-CP5 calculan y aplican el plan; la bandeja está en `MERGE_EXCLUSIONS`, así
   que **no aparece en el DELTA ni en el plan**.
2. CP8 verifica por hash únicamente `files_from`. Semáforo verde.
3. Línea 641: se registra `case_checkin` con `resultado="verde"`.
4. Línea 653: `_integrar_bandeja` mueve `x.eml` a su ruta definitiva. Si un
   `moveto` falla, se imprime `⚠` y **el flujo continúa**.
5. Línea 663: el lock se libera.

Se muta el canon **después** de la verificación y **después** del evento de
cierre, y el lock se libera aunque la integración falle a medias. Y si el checkin
se reintenta, `_append_evento_drive` no tiene clave de idempotencia: aparece un
**segundo** `case_checkin` verde en el log forense.

**Corrección mínima:** integrar bandeja → recalcular inventario → verificar por
hash **todo** lo mutado → registrar evento idempotente → liberar. Fallo de
integración bloqueante.

---

### A-3. «Cero escritura» no está definida, y hoy ya hay escrituras al canon que se saltan el guard

**SPEC:** §3.2, §8.4, §14.1, §18.4.
**Código verificado (cuatro vías distintas):**

1. `core/email_export.py:1146-1156,1074-1075`: `_dir_estado_canal` resuelve
   **siempre** `path_for(resolve_ref(case_id)) / "00_Input"` e ignora el `dest`
   recibido; `_save_export_index` y `_save_resolved_links` escriben ahí **sin
   pasar por `decidir_escritura`**. Los `.eml` sí se desvían
   (`intake_lotes.reservar_lote` → `dir_intake`); los dos JSON de estado, no.
2. `core/intake_log.py:185`: `mkdir(parents=True)` sobre la ruta de `caso_path`.
3. `core/catalogo_documental.py:87-91`: `save_catalog` hace `mkdir` +
   `write_text` sin guard.
4. `scripts/sala_maquina.py:223-226,261-266`: el subcomando `plan`, documentado
   como *«no escribe nada»*, **escribe `_segmentacion.md`** en
   `02_Documentos/<slug>/` de cada bundle detectado.

**Contraejemplo:** caso prestado por otro; se exporta la etiqueta Gmail. Los
`.eml` van a la bandeja, pero `_exported_ids.json` y `_resolved_links.json` se
**sobrescriben en `00_Input/` del Drive**. Consecuencias: (a) bytes modificados en
el canon durante el préstamo; (b) el índice de idempotencia queda en Drive y no
en la copia local, así que el titular re-descarga la etiqueta entera en su
siguiente corrida; (c) ninguno de los dos está en `MERGE_EXCLUSIONS`, así que en
el checkin aparecen como «nuevo en Drive» → `PRESERVE_DRIVE`.

**Corrección mínima:** definir «cero escritura» en cuatro planos (árbol del caso;
almacenamiento canónico incluida la creación de directorios y el estado de canal;
servicios externos; estado local de aplicación) e incorporar los cuatro sitios al
§11 como brechas nominadas. `plan` necesita `write_case`.

---

### A-4. `expedientes-xl` puede sobrescribir el `_caso.md` del Drive: la frontera de entrypoints Python no alcanza al plugin

**SPEC:** §9.2, §4.5, mandato §19.1 y §19.5.
**Código:** `plugins/expedientes_xl/tiers.py:31-32`
(`PROTOCOL_EDIT = ("_caso.md", "MANIFEST_CHECKOUT.json")`,
`PROTOCOL_APPEND = ("_intake_log.jsonl", …)`), `tiers.py:70-104` (`check_write`:
Tier 2 permitido sin más; bajo `00_Input`, crear-nuevo permitido y sobrescritura
permitida si el nombre está en `PROTOCOL_EDIT`), `tiers.py:55-61` (`classify` no
conoce estado ni lock), `tiers.py:5-6` (el plugin no importa `core` en runtime,
por diseño).

**Contraejemplo:** caso prestado a la máquina M1. Desde Cowork-PC, una skill
llama `write_text` sobre `G:\…\<caso>\00_Input\_caso.md`. `check_write` clasifica
Tier 1, `exists=True`, nombre ∈ `PROTOCOL_EDIT` → **permitido**. El lock
desaparece o se sustituye. El titular de M1 sigue trabajando y al hacer checkin
obtiene `LOCK_MISMATCH`. En paralelo, `create_dir`/`copy_path` sobre Tier 2
(`01_Procesado`, `05_Procedimiento`) escriben en el canon sin comprobación.

**Impacto:** el disparador de reapertura de la opción 3 que la propia SPEC define
en §13.4 («una auditoría demuestra que la frontera de entrypoint no puede impedir
escrituras fuera de política») **ya se cumple para este runtime**. No obliga a la
opción 3 —el plugin es un punto único y auditable— pero sí a un cambio de
contrato.

**Corrección mínima:** la política de zonas incorpora el estado del lock;
`PROTOCOL_EDIT` sobre `_caso.md` se reserva a una tool de protocolo identificada;
cubierto por el test anti-drift que ya sincroniza `tiers.py` con `core.config`.

---

### A-5. El fallback de `path_for` **es** el fallback silencioso a Drive que el invariante 3 prohíbe

**SPEC:** invariante 3, §7.3, §10 (`LOCAL_WORKSPACE_MISSING`).
**Código:** `core/casos/case_locator.py:26-43` y `100-121`;
`scripts/sala_maquina.py:127-147` (guard local añadido tras el bug de W-02ZIIF).

**Contraejemplo:** con la ruta local perdida o movida, un entrypoint **no
migrado** —los hay hasta la Fase 6— resuelve por identidad: `resolve_ref`
devuelve el W-code sin cambios, `path_for` devuelve `CASOS_ROOT/W-02ZZZZ`, y el
primer `mkdir` de cualquier escritor materializa esa carpeta en el Drive. El
sistema no falla: crea un expediente nuevo, vacío y con nombre de W-code, y
sigue.

**Corrección mínima:** modo estricto en Fase 1 (resolver un caso ausente lanza;
crear pasa por función explícita); ningún escritor hace `mkdir` de la raíz del
caso; la prohibición de llamar a `caso_path` alcanza también a los entrypoints
existentes.

---

### A-6. `INTAKE_EVENTS` es un conjunto cerrado que lanza: la Fase 2 no tiene eventos que emitir

**SPEC:** §6.1, §8.6, §8.7, §12 Fase 2.
**Código:** `core/intake_log.py:42-82` (frozenset de 27 eventos), `178-182`
(`raise ValueError`).

**Contraejemplo:** la Fase 2 necesita registrar creación de scratch, promoción
(y su compensación parcial), adopción de un checkout legacy, resolución de
conflicto y el identificador opaco de workspace que sustituye a `ruta_local`.
Ninguno existe: la primera llamada lanza. `pendiente_checkin` existe y debe
retirarse de la emisión sin romper la lectura de logs históricos.

**Corrección mínima:** enumerar los eventos nuevos y su `details` en §6; declarar
`pendiente_checkin` como «solo lectura histórica».

---

### A-7. `local_scratch` no tiene entrypoint: `--case-dir` y `--casos-root` no existen

**SPEC:** §5.2, §7.1, §7.3, §12 Fase 1; antecedente
`2026-07-14-expediente-scratch-design.md` §Alcance punto 2.
**Código:** búsqueda en todo el repo — `--case-dir`: **cero apariciones**;
`--casos-root`: solo `scripts/migrar_nombres_informe.py:60`.
`scripts/sala_maquina.py` no acepta ninguna: resuelve por `case_id` vía
`caso_path` (127-147).

**Contraejemplo:** el Cluster B del diseño de scratch **nunca se construyó**. Hoy
la única forma de correr el pipeline sobre un scratch es el override de
`CASOS_ROOT` por entorno — el mismo que la sesión VALERO usó y que aquel diseño
se propuso eliminar. Si la Fase 1 declara que `CASOS_ROOT` ya no selecciona la
copia operativa y `sala_maquina` no recibe `--case-dir` hasta la Fase 3, **entre
la Fase 1 y la Fase 3 no hay ninguna vía para trabajar un scratch**.

**Corrección mínima:** `CASOS_ROOT` conserva su función de selector para los
componentes `legacy_unresolved`; `--case-dir` en `scripts/sala_maquina` entra en
la Fase 1.

---

### A-8. La identidad no es única: `resolve_ref` resuelve el W-code por orden de escaneo

**SPEC:** §5.1, §7.2, §10 (`AMBIGUOUS_CASE`), §14.3.
**Código:** `core/casos/case_locator.py:100-121` (devuelve el **primero** cuyo
`id_go` casa, sin detección de duplicados), `207-239` (`list_cases` deduplica por
nombre de carpeta), `46-69` (`_id_go_of` devuelve `None` en silencio).

**Contraejemplo:** nada en `repository_cli.py` impide que `--local` apunte
**dentro** de `CASOS_ROOT` (el runbook usa Desktop por convención, no por
control). Un checkout así produce dos carpetas con el mismo `meta.id_go` bajo el
catálogo, y `resolve_ref` devuelve la que ordene antes. Y a partir de la Fase 2
la proyección local del §6.3 crea deliberadamente un segundo `_caso.md` con el
mismo W-code.

**Corrección mínima:** el catálogo devuelve `AMBIGUOUS_CASE` ante W-code
duplicado; la proyección local lleva marca que la excluye del catálogo; el
destino de checkout no puede residir bajo `CASOS_ROOT`.

---

### A-9. El criterio de salida de la Fase 3 no es verificable: no existe doble de Drive/rclone

**SPEC:** §12 Fase 3, §14.2.
**Código:** `scripts/repository_cli.py:403-409` — comentario normativo del propio
módulo: *«No se ejecuta contra el Drive en los tests (I/O externo)»*.
`run_rclone` (352) es el único punto de I/O y no hay puerto inyectable.

**Impacto:** las filas «Drive disponible» y «Checkout ajeno» del ciclo
checkout/checkin no son ejecutables. Precisión sobre qué hay hoy: el cerebro puro
está bien cubierto (`tests/test_repository_checkout.py`, 30 KB) y
`tests/test_repository_cli.py` tiene **27 tests, todos de los helpers puros del
frontal** —constructores de comando rclone, semáforo, parseo de inventario, plan
de integración de la bandeja, render del DELTA—. **Ninguno toca `cmd_checkout` ni
`cmd_checkin`**, y no hay un solo `monkeypatch` de `run_rclone`: la
**orquestación**, que es donde viven A-1, A-2 y B0-2, no tiene test. Los criterios
de salida de las Fases 2 y 3 se podrían «cumplir» sin haber probado ninguna de las
rutas peligrosas.

**Corrección mínima:** sub-SPEC previa (Fase 0): puerto `RcloneRunner` + doble en
memoria con semántica de Drive (retraso de propagación, Google-native sin MD5,
`moveto` fallido, `lsjson` malformado).

---

### A-10. El trabajo offline **sí** puede continuar tras una cancelación legítima, y el conflicto resultante no tiene baseline

**SPEC:** §7.1 paso 5 y párrafo final, §8.7, mandato §19.4.
**Código:** `.claude/skills/checkout-caso/SKILL.md:72` (cancelación unilateral
desde chat), `scripts/repository_cli.py:520` + `802-812` (`_leer_manifest` lee el
baseline del **local**).

**Contraejemplo:**

1. El titular pierde red y sigue trabajando (§7.1.5 lo autoriza). Nada expira.
2. Otro usuario —o el propio titular desde Cowork, siguiendo la línea 72 de la
   skill— **cancela legítimamente** el checkout: Drive vuelve a `disponible`. La
   confirmación de «el trabajo local se descarta» es imposible de obtener.
3. El caso queda `disponible`; terceros escriben en Drive durante días.
4. El titular vuelve y hace checkin: `LOCK_MISMATCH` → conflicto, local
   conservado. Correcto en cuanto a «sin pérdida».
5. Pero el baseline `B` sigue siendo el `MANIFEST_CHECKOUT.json` original: el
   merge de tres vías clasifica todo lo que Drive cambió en el paso 3 como caso 4
   o 6 → **conflicto masivo sin criterio de resolución**.

**Corrección mínima:** la cancelación sin confirmación del titular deja marca en
Drive; el checkin posterior no ofrece merge sino una vía de rescate acotada
(volcar el delta local a un lote de intake nuevo); el trabajo offline productivo
se limita a lo que ese rescate puede recuperar sin ambigüedad.

---

## M — mejoras importantes (no invalidan la arquitectura)

- **M-1. Copia parcial huérfana tras un checkout fallido.**
  `repository_cli.py:457` hace `local.mkdir` antes de copiar; si rclone falla
  (466-473) se revierte el lock pero **no se limpia el árbol parcial**, que
  además no tiene `_caso.md` (está en `MERGE_EXCLUSIONS`) → no es identificable
  ni por `--case-dir` ni por el registro. PII en el Desktop sin trazabilidad.
  → recogido en §16 de la rev. 2.
- **M-2. `checkout_maquina` es el hostname y se publica en el `_caso.md` que E&V
  ve** (`repository_cli.py:418`, `repository_checkout.py:181`). §16 prohíbe rutas,
  no nombres de máquina. → decidido en §6.2 de la rev. 2.
- **M-3. El `CaseWorkspace` no debe cachearse en `st.session_state`** — gotcha
  conocido del repo (sentinels marcados antes del efecto). → `MEJORAS #103`.
- **M-4. La integración de la bandeja produce ficheros `_reingesta_*`** cuando
  colisiona (`repository_cli.py:697-724`) que ningún plan ni verificación cubre y
  que nadie reconcilia. → `MEJORAS #101`.
- **M-5. `errors="replace"` en la lectura del log canónico**
  (`repository_cli.py:756`) corrompe evidencia de forma silenciosa y permanente
  en cada evento. → `MEJORAS #102`.

---

## A. Resultado del debate opción 2 / opción 3

**La opción 2 sigue siendo la recomendada, y con margen.** No por pureza: por
medición.

- Los motores realmente puros ya reciben rutas y no resuelven nada:
  `atomize.atomize_dir(fuentes, out, case_dir=…)`
  (`scripts/sala_maquina.py:192`), `sm.ejecutar(case_dir, plan, …)` (279),
  `split.detectar(src)` (257), OCR vía OCRmyPDF, `plan_merge` como función pura
  sobre inventarios. Virtualizar el almacenamiento no les aporta nada y les quita
  el `Path` que sus binarios externos exigen. El coste que describe §13.2 es real.
- El argumento débil de §13.1 es otro: **«la autorización queda en la frontera»
  presupone que la frontera es el entrypoint, y hoy no lo es.** El recuento da
  **432 apariciones de `caso_path`/`casos_root`/`resolve_ref`/`path_for` en 80
  ficheros**, y la resolución vive **dentro** de servicios de core que reciben
  `case_id`: `case_manager` (23), `intake_manual` (10), `anon/api` (9),
  `sala_lectura` (7), `email_export` (6), `viability` (4), `catalogo_documental`
  (2), `intake_log` (2)…, más `streamlit_app.py` (9). Migrar significa cambiar la
  firma de esa capa entera.
- **¿Se acerca la inversión a la opción 3?** No. La opción 3 exigiría además
  tocar cada `open`/`rglob`/`shutil`/hash/temporal **dentro** de los motores, que
  es donde está el grueso del código (`core/email_atomize/inline.py` solo son
  49 KB). La opción 2 toca la capa de servicios; la 3 tocaría servicios **y**
  motores. La diferencia sigue siendo de un orden de magnitud. Lo que hay que
  corregir es la retórica, no la decisión.
- **¿Es real la puerta de §13.3?** Sí para el filesystem y para una vista local
  materializada; no para un backend sin ruta, y eso ya estaba admitido. La puerta
  se sostiene porque la selección de caso, el lock, las capacidades y los códigos
  de error quedan estables.
- **Interfaz mínima que falta ahora, y no es YAGNI:** (1) el **puerto de rclone**
  (A-9), sin el cual no hay forma de probar las rutas peligrosas; (2) un
  **`log_sink` asociado al workspace** en lugar de `append_event(case_id)`, que es
  la corrección de B0-1 y exactamente la costura que una futura opción 3
  necesitaría. Todo lo demás (`StorageHandle`, API virtual de ficheros) sí es
  YAGNI: no se crea.
- **Condiciones en las que dejaría de ser la recomendada:** (a) si el checkout
  por skill/plugin no se puede subordinar al protocolo Python y hay que replicar
  la política en tres runtimes —la política dejaría de tener un hogar—; (b) si
  aparece un segundo despacho o tenant sin `G:` montado; (c) si los adaptadores
  por runtime de la Fase 5 empiezan a duplicar lógica material.

---

## B. Cobertura de fases (evaluada sobre la rev. 1)

| Requisito | Fase prevista | Código/skill afectado | Hueco |
|---|---|---|---|
| Resolver único por identidad | 1 | `core/casos/case_locator.py`, `core/config.py:547` | Fallback creador de `path_for` (**A-5**) |
| `--case-dir` | 1 | — | **No existe en ningún script (A-7)** |
| Registro local atómico | 1 | nuevo | Las skills no pueden escribirlo (**B0-3**) |
| Auditoría en la copia operativa | sin asignar (§11.4) | `core/intake_log.py:145-201` | **Debe ser Fase 1 (B0-1)** |
| Identidad única / colisiones | 1 (§7.2) | `case_locator.py:100-121` | El catálogo resuelve la ambigüedad en vez de reportarla (**A-8**) |
| Eventos nuevos del ciclo | 2 | `core/intake_log.py:42-82` | Conjunto cerrado: `ValueError` (**A-6**) |
| Proyección de `_caso.md` | 2 | `core/config.py:391-399`, `case_manager` | Dispara `MEJORAS #96`; falta tabla de propiedad de campos |
| Prefijo/sufijo del `_intake_log` | 2 | `repository_cli.py:330-345,736-767`, `intake_log.py:204-230` | **Sin baseline ni representación comparable (B0-2)** |
| Lock: adquirir/revertir/liberar | 2 | `repository_cli.py:441-473,628-663,785-799` | Sin CAS ni re-verify: doble checkout (**A-1**) |
| Orden del checkin y bandeja | 2 | `repository_cli.py:598-663,697-724` | Libera con bandeja sin verificar; duplica evento (**A-2**) |
| Retirada de `_pendiente_checkin/` | 2 | `repository_checkout.py:541-577` + 5 llamadores | **Dos políticas vivas (B0-4)** |
| Promoción de scratch | 2 | `core/abrir_caso.py`, nuevo `promover` | Sin eventos ni compensación definida (**A-6**) |
| Doble de Drive/rclone | ninguna | `repository_cli.py:352-367` | **Sub-SPEC previa imprescindible (A-9)** |
| `scripts/sala_maquina` | 3 | `sala_maquina.py:127-147,223-266,303` | `plan` escribe pese a documentarse como lectura (**A-3**) |
| Atomización + export Gmail | 3 | `email_export.py:1074-1075,1146-1156` | Estado de canal escribe en Drive sin guard (**A-3**) |
| Streamlit | 3 y 4 (solapadas) | `streamlit_app.py` (9 resoluciones; **0** referencias a lock) | Sentinels de `session_state` no tratados (**M-3**) |
| Inventario de entrypoints | 4 | 432 apariciones / 80 ficheros | Es la capa de servicios de core, no las CLIs |
| `expedientes-xl` | 5 | `tiers.py:31-32,70-104` | Puede sobrescribir `_caso.md` del canon (**A-4**) |
| Skills de checkout/checkin | 5 | `checkout-caso/SKILL.md:27-72` | Protocolo duplicado en prosa desde la Fase 2 (**B0-3**) |
| Guardas anti-regresión | 6 | nuevo | Llegan tras cinco fases de convivencia |

---

## C. Preguntas que cambian la arquitectura

1. **¿La skill `checkout-caso` deja de adquirir el lock (y aborta en nube pura),
   o la Fase 2 define un registro que la skill pueda escribir y verificar?**
   Determina si «checkout sin entrada en registro» es un error o un estado
   normal. *(rev. 2: deja de adquirirlo.)*
2. **De los campos de `meta` del `_caso.md`, ¿cuáles son propiedad exclusiva de
   Drive, cuáles del local durante el préstamo, y cuál gana si ambos cambian?**
   `ciudad`, `tipo_caso`, `partes` y `sudespacho_expedientes` son modificables
   desde ambos lados hoy. *(rev. 2: §6.3 exige la tabla; el reparto mínimo queda
   fijado.)*
3. **¿La Fase 2 voltea `decidir_escritura` a denegar para todos los llamadores a
   la vez, aceptando la rotura de los no migrados?** *(rev. 2: sí.)*
4. **¿Se puede exigir que la copia de checkout nunca resida bajo `CASOS_ROOT` y
   que la proyección lleve marca que la excluya del catálogo?** *(rev. 2: sí.)*
5. **¿Cuál es la representación autoritativa del `_intake_log.jsonl` para
   reconciliar: bytes o eventos con identidad estable?** *(rev. 2: eventos.)*
6. **¿«Cero escritura» incluye la creación de directorios y los ficheros de
   estado de canal en el canon?** Si sí, `intake_log`, `email_export` y
   `catalogo_documental` entran antes de la Fase 3. *(rev. 2: sí; `intake_log` a
   Fase 1, los otros dos a Fase 3.)*

---

## D. Conclusión

**¿Podía escribirse el plan de la Fase 1 sobre la rev. 1?** No. Se podía escribir
el de una **Fase 0** (puerto de rclone y su doble) y, en paralelo, la corrección
del contrato. La Fase 1 tal como estaba descrita entregaba `--case-dir` sobre un
`intake_log` que resuelve por `CASOS_ROOT` y crea directorios: entregaba el split
brain en vez de cerrarlo.

**B0 a corregir primero:** B0-1 (`intake_log` a Fase 1), B0-2 (baseline y
representación del log), B0-3 (decisión sobre la skill de checkout), B0-4
(conmutación atómica del guard). **Los cuatro están resueltos en la rev. 2**, cuyo
§20 los mapea a las secciones concretas.

**Afirmaciones de la SPEC que sobrevivieron al ataque:** la elección de la opción
2; el invariante 6 (motores puros conservados); el invariante 7 (protocolo
separado de contenido, ya implementado con artefactos en directorio temporal); el
diagnóstico del §1 y las siete brechas del §11 —todas ciertas, el problema era lo
que faltaba—; el §14.3 (afirmaciones prohibidas), que aplicado al propio código
produjo la mitad de estos hallazgos; y la decisión de no construir bandeja de
aportaciones con un único escritor, que no se pudo impugnar.
