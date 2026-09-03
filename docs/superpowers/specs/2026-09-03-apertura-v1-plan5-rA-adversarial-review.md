---
tipo: revision-adversarial
objeto: "diseno del Plan 5: el cableado de la secuencia de V1 y el E2E"
objeto_rev: "rama claude/expediente-apertura-orquestado-cd68c3, commit a95326e"
commit: a95326e
ronda: "A"
revisor: Codex
veredicto: NO-EJECUTABLE
marcador_nonce: q7km
sha256_informe: 3f13587776311b538e8b170ec0683f4db35003b1197ae64449853b454cb8ef83
adjudicado_en: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md §5
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revision adversarial R-A.** El §1 conserva la voz del revisor sin una coma
> cambiada; la **adjudicacion** vive en el **§5 del plan**
> (`docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md`). Es la ronda de
> **DISENO**: se corrio **antes de escribir una linea de codigo**, que es para lo que existe.
>
> Veredicto `NO-EJECUTABLE`: **12 hallazgos** — 4 CRITICOS, 6 ALTOS, 1 MEDIO, 1 BAJO.
> Adjudicados: **12 confirmados, 0 refutados**, y uno de ellos (HA-03) **elevado por el
> adjudicador** de ALTO a CRITICO.
>
> **Esta ronda EJECUTO.** El revisor reprodujo los adaptadores propuestos con dobles y midio
> que el de Drive no llama a la custodia (`custodia_calls= []`) y que el del CRM devuelve
> `hecha` con `errors` dentro; aplico las piezas del plan al trinquete del censo y lo puso en
> 84/83; corrio el mutante F12 aislado y lo dejo VIVO; paso la fixture del E2E por el lector
> real de metadatos y obtuvo `{}`; y reprodujo la perdida de mutex bajo un `typer.Exit(0)`.
> Los cuatro criticos salieron de ejecutar, no de leer.
>
> **El informe y el veredicto llegaron como dos ficheros** porque el mandato pidio la palabra
> del conjunto cerrado por separado, para que el `veredicto:` del frontmatter conste literal en
> el bloque archivado y no lo rellene el adjudicado. Los dos se archivan aqui, en ese orden.
>
> **Prueba de no mutacion:** el objeto conservo el `sha256`
> `ba0fccbd7b48b61adacb3cbce87cab95e94810ca2660bc371a48c48d9002fc0d` al abrir y al cerrar.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:q7km -->

NO-EJECUTABLE

El plan omite custodia en Drive, declara hechos pulls CRM fallidos, puede salir 0 tras perder el mutex y aplaza precondiciones que la spec hace constitutivas de V1. Además, su arnés deja vivo F12 y su E2E no ejecuta realmente el CRM ni demuestra punto fijo material. Ejecutarlo tal cual produciría una vertical incorrecta e incompleta respecto de lo que promete.

---

# Revisión adversarial R-A — Plan 5 de apertura V1

## 1. Objeto y evidencia

Objeto revisado: `../head/docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md`, copia congelada sin `.git` del commit declarado `a95326e`.

**Prueba de no mutación.** SHA-256 al abrir: `ba0fccbd7b48b61adacb3cbce87cab95e94810ca2660bc371a48c48d9002fc0d`. SHA-256 al cerrar: `ba0fccbd7b48b61adacb3cbce87cab95e94810ca2660bc371a48c48d9002fc0d`. Son idénticos. No se escribió en `../head/`; las ejecuciones con escritura se hicieron sobre una copia efímera en el workdir, retirada antes de redactar este informe.

**Ficheros leídos.** Leí completo el plan; de la spec canónica, en particular §§13, 14, 21, 24 y 25; `CLAUDE.md`; y los módulos y pruebas señalados por el mandato: `scripts/abrir_caso.py`, `scripts/sala_maquina.py`, `core/casos/mutex_sesion.py`, `core/casos/case_mutex.py`, `core/casos/escritura.py`, `core/intake_drive.py`, `core/sync_sudespacho.py`, `core/intake_log.py`, `core/case_manager.py`, `tests/test_escritura_censo.py`, `tests/test_abrir_caso_modo_v1.py` y `tests/test_sala_maquina_cableado_atomize.py`. Para seguir llamadas y citas también leí los pasajes pertinentes de `core/casos/case_locator.py`, `core/email_atomize/pipeline.py` y `core/adjuntos_contenido/pipeline.py`. Confirmé que `core/apertura_v1.py` no existe en la copia.

**Comandos y resultados relevantes.** Se usó `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider` y `--basetemp` corto fuera de la raíz de la copia ejecutada.

1. Línea base de las pruebas ya existentes:

   ```text
   python -m pytest tests/test_abrir_caso_modo_v1.py tests/test_escritura_censo.py -q -p no:cacheprovider --basetemp=../informe/t0
   ............................... [100%]
   EXIT=0
   ```

2. Reproducción local de las piezas y tests F1–F14 descritos por el plan, antes de mutar:

   ```text
   ............... [100%]
   EXIT=0
   ```

3. Adaptadores propuestos, con dobles que devuelven éxito de Drive y un `PullResultV2` fallido:

   ```text
   drive_estado= hecha custodia_calls= []
   crm_estado_con_errors= hecha
   ```

   La primera línea prueba que el camino propuesto no llama a `_intake_drive_ev`; la segunda, que `errors` no gobierna el resultado CRM.

4. Trinquete de escrituras después de aplicar literalmente las piezas relevantes del plan:

   ```text
   FAILED test_el_censo_solo_baja
   el censo ... SUBIÓ a 84 (techo 83)
   FAILED test_el_techo_no_esta_holgado
   el censo real es 84 y el techo dice 83
   EXIT=1
   ```

   En la copia sin cambios, el mismo detector dio `TOTAL 83 TECHO 83`.

5. Mutación F12 reproducida aisladamente:

   ```text
   tests/test_apertura_v1_etapas.py::test_f10_f12_...[None-hecha-False] . [100%]
   EXIT=0
   ```

   Es decir, el mutante F12 sobrevive. Un lanzamiento agregado duplicado interfirió con su propia restauración y se descartó como evidencia; F12 se repitió solo y de forma limpia. No afirmo aislamiento dinámico de los otros trece mutantes.

6. Fixture E2E propuesta, pasada por el lector real de metadatos:

   ```text
   {}
   ```

7. `--hasta` con el código propuesto:

   ```text
   validar_hasta_erroneo= []
   parcial_estado= preparado_con_pendientes etapas= ['drive']
   pendientes= ['fuentes_v3_sin_consultar'] parada= drive
   ```

8. Pérdida de mutex con el `typer.Exit(0)` dentro del bloque, usando el gestor real y una raíz temporal:

   ```text
   TIPO= Exit EXIT_CODE= 0
   NOTES= ['[mutex] ademas, el mutex se perdio durante la operacion: RuntimeError']
   ```

9. Cifras verificadas: el censo vigente es 83; hay cero apariciones de `preparado_con_pendientes` en `core/`, `scripts/` y `tests/`; el recuento `now_iso`/`now_iso_utc` es 43/5; `INTAKE_EVENTS` contiene 33 valores, no 27. La afirmación de «103 referencias a `scripts.abrir_caso`» no fue reproducible: el barrido del archivo devolvió 53 apariciones exactas en 19 ficheros; el token más ancho `abrir_caso` devolvió 657 apariciones en 64 ficheros.

**SIN VERIFICAR.** No se ejecutó la apertura real W-02Q38C ni se accedió con éxito a Drive o Sudespacho. No se ejecutó la suite completa ni las dos semillas: el Python indicado no tiene `pytest-randomly` (`find_spec('pytest_randomly') -> None`). Tampoco se verificó dinámicamente que cada mutante distinto de F12 mate exactamente —y solo— el conjunto declarado; el propio arnés no puede medir esa propiedad. Un primer ensayo con `--basetemp=t` dentro de la raíz de la copia produjo rojos de las barreras que prohíben registro/locks bajo el repo; se descartaron como falsos rojos y no sustentan ningún hallazgo.

## 2. Hallazgos

### HA-01 — CRÍTICO

**Qué es:** el plan declara aplazadas precondiciones y criterios constitutivos de V1, pero sigue prometiendo construir y cerrar V1.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:48-81,1717-1737`; spec `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1286-1314,1390-1424,1434-1455,1724-1726,1812-1818`.

**Por qué importa:** la spec hace predecesores el write-set decidido, el espejo versionado, `operations`/`estado.json`, generaciones, snapshots y reconciliación de crashes. El plan los sustituye por «la idempotencia que cada etapa ya tiene». Tras un crash entre publicaciones locales, o con una fuente saltada por marcador, puede quedar una fase verde sobre entradas obsoletas y la siguiente corrida no sabe qué invalidar. Eso es software incompleto respecto de los criterios 2, 10, 14, 41, 42, 47 y 48 que el propio §21.4 incluye en V1.

**Cómo lo comprobé:** leído y contrastado contra la spec; los fallos concretos de Drive y CRM se ejecutaron en HA-02/HA-04.

**Qué haría falta:** ejecutar antes los bloques que la spec hace precondición —o modificar formalmente la spec y el alcance prometido— y aportar pruebas de generación, crash, reconciliación y los cuatro planos del workspace. Una tabla de «deuda aceptada» en el plan no deroga la fuente canónica.

### HA-02 — CRÍTICO

**Qué es:** `etapa_drive` llama directamente a `pull_drive_ev` y omite la cadena de custodia existente de `_intake_drive_ev`.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:496-504,571-603`; código `scripts/abrir_caso.py:136-175`; `core/intake_drive.py:337-340`; spec `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1304-1305`.

**Por qué importa:** en un pull correcto no se calculan hashes, no se ejecutan `plan_intake`/`reconcile` y no se emite el evento de intake. En un `DriveIntakeError` con bytes parciales se pierde además el registro especial de esos bytes que `_intake_drive_ev` hace antes de relanzar. La secuencia puede declarar Drive `hecha` sin cumplir custodia, o `fallo` dejando material no inventariado.

**Cómo lo comprobé:** ejecutado sobre copia; resultado: `drive_estado= hecha custodia_calls= []`.

**Qué haría falta:** adaptar la costura existente, no saltársela; hacer que devuelva un resultado consumible preservando hashing, reconciliación, destino efectivo y evento parcial, con pruebas que espíen esas cuatro consecuencias.

### HA-03 — ALTO

**Qué es:** el supuesto «punto fijo» usa `.pulled` para no consultar Drive, exactamente lo que el criterio 10 prohíbe.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:63-66,501-504,596-602,1602-1629,1681-1703`; código `core/intake_drive.py:201-229`; spec `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:868-873,1399-1405`.

**Por qué importa:** si aparece o cambia un documento remoto después del primer pull, la segunda apertura ve `.pulled`, no consulta Drive, reporta `saltada` y conserva derivados obsoletos. Igualdad del token de estado no demuestra punto fijo material.

**Cómo lo comprobé:** leído; la alcanzabilidad de `res.skipped=True` está implementada en producción en `core/intake_drive.py:206-228`.

**Qué haría falta:** consulta remota real por ronda y espejo versionado con generación/tombstones; el E2E debe introducir una novedad remota simulada y demostrar invalidación y regeneración.

### HA-04 — CRÍTICO

**Qué es:** el adaptador CRM ignora el contenido de `PullResultV2` y marca `hecha` toda llamada que no lance.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:690-715,765-776`; código `core/sync_sudespacho.py:1287-1318,1423-1452,1454-1460,1645-1669`; spec `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:902-906,926,1406-1409`.

**Por qué importa:** `pull_expediente_v2` comunica por retorno `blocked_legacy_v1`, errores de cliente/listado, gestor vacío, descargas fallidas y errores de `update_pull_state`. Con cualquiera de ellos el adaptador propuesto construye `estado="hecha"`; después corre sala de máquina sobre un CRM ausente o parcial y V1 puede salir 0.

**Cómo lo comprobé:** ejecutado con un retorno que contenía `errors=['list_gdocu_docs_rest: 500']`; resultado: `crm_estado_con_errors= hecha`.

**Qué haría falta:** definir la tabla completa de traducción de `PullResultV2` (incluidos vacío confirmado frente a error, legado bloqueado y documentos fallidos), verificar resultado y no solo excepción, y mutar cada rama.

### HA-05 — ALTO

**Qué es:** el plan cierra el ejemplo del default judicial, no la propiedad bidireccional ni la discrepancia de referencia/elemento exigidas por el criterio 38.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:630-641,652-677,757-774,1426-1433`; spec `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1413-1422`; código `core/case_manager.py:58-63`.

**Por qué importa:** el adaptador solo exige que `element` sea no vacío y luego confía en el link. Admite un literal desconocido y también un link judicial en un caso extrajudicial —o el cruce inverso—, sin contrastarlo con la identidad/rama del caso. F7 prueba solo un extrajudicial frente al default judicial; no hay las dos pruebas separadas que la spec ordena, ni preflight de referencia antes de escribir.

**Cómo lo comprobé:** leído. La prueba dinámica de cruces reales queda SIN VERIFICAR.

**Qué haría falta:** vocabulario cerrado, regla que derive la rama esperada de datos independientes del propio link, comprobación de referencia y elemento antes del pull, y tests separados de ambos cruces con cero escrituras.

### HA-06 — ALTO

**Qué es:** `--hasta` permite producir efectos antes de validar un nombre erróneo y registra una parada parcial como `apertura_v1_terminada`.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:441-473,1294-1330`; código vigente `scripts/abrir_caso.py:530-539,636-663`; spec `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1680-1689`.

**Por qué importa:** `--hasta drve` pasa la puerta temprana y solo falla dentro de `secuenciar`, después de identidad, mutex y `ensure_case`; en un caso nuevo ya creó el esqueleto. Con `--hasta drive`, el resultado contiene solo esa etapa y únicamente el pendiente V3, pero `main` emite incondicionalmente `apertura_v1_terminada` y sale 0: CRM y sala ni corrieron ni figuran como pendientes.

**Cómo lo comprobé:** ejecutado: `validar_hasta_erroneo=[]`; la parada tras Drive devolvió `preparado_con_pendientes`, una sola etapa y solo `fuentes_v3_sin_consultar`.

**Qué haría falta:** validar el vocabulario de `--hasta` en la puerta anterior a todo efecto; dar a una parada solicitada semántica durable propia, sin evento de terminación falsa, o enumerar explícitamente las fases V1 no ejecutadas.

### HA-07 — CRÍTICO

**Qué es:** lanzar `typer.Exit` dentro del `with mutex_sesion.sostenido(...)` puede convertir una pérdida del mutex en una nota sobre un exit 0.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:1321-1330`; código `core/casos/mutex_sesion.py:159-190`; `core/casos/case_mutex.py:615-659`.

**Por qué importa:** para `preparado_con_pendientes`, `codigo_de_salida` devuelve 0. Si el lease se pierde durante la operación, `case_mutex.tomado` preserva por diseño el error ya en vuelo y solo añade una nota. Como ese «error» es el `typer.Exit(0)` introducido por el plan, el proceso sigue saliendo 0 después de haber perdido exclusión; el evento de terminación ya se escribió además antes de comprobar la liberación. `CaseBusy` al adquirir tampoco se convierte en uno de los tres estados.

**Cómo lo comprobé:** ejecutado con el gestor real: `TIPO=Exit EXIT_CODE=0` y la pérdida solo apareció en `__notes__`.

**Qué haría falta:** salir del bloque normalmente, dejar que su cierre/revalidación termine, y solo entonces emitir el exit; capturar `CaseBusy`/`MutexPerdido` en la frontera CLI y asignar estado/exit no cero sin certificar una terminación anterior.

### HA-08 — ALTO

**Qué es:** aplazar 3C contradice literalmente D4 y vuelve automática una poda irreversible que antes era una ejecución deliberada.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:59-66,924-938`; spec `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1706-1722`; código `core/email_atomize/pipeline.py:220,267`; `core/adjuntos_contenido/pipeline.py:109`.

**Por qué importa:** cada apertura V1 pasará por `sala_maquina.apply`. Si desaparece un correo del corpus activo o cambia la fotografía de entrada, la poda puede borrar mensajes, vistas o contenidos derivados sin archivarlos. Que el crudo de `00_Input` siga intacto no conserva el histórico de la transformación ni cierra la regla de D4; automatizarla aumenta frecuencia y radio de daño.

**Cómo lo comprobé:** leído; los tres `unlink()` existen en las líneas citadas. No ejecuté una poda con datos reales.

**Qué haría falta:** archivar o inactivar antes de cablear la ejecución automática, con una prueba por cada `unlink` retirado que demuestre recuperabilidad en `99_Versiones anteriores`.

### HA-09 — ALTO

**Qué es:** el arnés de mutación no puede verificar su propia regla de «exactamente el test declarado» y F12 sobrevive.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:1366-1369,1450-1454,1466-1497,1515-1518`.

**Por qué importa:** `_correr` ejecuta únicamente el `nodeid` declarado; por construcción no observa qué otros tests mata el mutante. F3 y F4 ya tienen pruebas duplicadas en Tasks 1/2 y 2/8, pero el arnés jamás las compara. Peor, F12 solo cambia el texto de `detalle`; su test afirma `estado` y presencia de pendientes, no el detalle, de modo que queda verde. El cierre esperado `14/14` es imposible con el código escrito.

**Cómo lo comprobé:** leído y ejecutado. F12 aislado terminó `EXIT=0`, por tanto VIVO. El aislamiento de los otros trece queda SIN VERIFICAR.

**Qué haría falta:** un mutante F12 que realmente introduzca el pendiente prometido; ejecutar por mutante el conjunto contractual completo y comparar el conjunto exacto de nodeids rojos, no un único booleano. F8 también debería mutar a la adivinanza judicial prometida, no limitarse a retirar la guarda y caer por `KeyError`.

### HA-10 — ALTO

**Qué es:** el llamado E2E no recorre el CRM ni demuestra punto fijo material.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:1536-1539,1557-1567,1575-1630`; código lector `core/casos/case_locator.py:198-223`.

**Por qué importa:** la fixture escribe `sudespacho_expedientes` en el frontmatter superior, pero `read_case_meta` devuelve exclusivamente el dict `meta`; por tanto devuelve `{}` y `etapa_crm` toma la rama `saltada`. El test no afirma que el doble CRM se llamara. Además sustituye Drive, CRM y toda `etapa_sala_maquina`; la supuesta segunda ronda solo compara el string de estado y un contador falso de `skipped`, sin digest del árbol, manifiestos, generaciones, eventos ni crashes.

**Cómo lo comprobé:** ejecuté el frontmatter propuesto contra `read_case_meta`; devolvió `{}`.

**Qué haría falta:** fixture con el esquema real; dobles solo en límites remotos/OCR, no en las etapas; spies de las llamadas; comparación material del árbol y controles; casos de intake tardío, ruta desviada, descarga parcial, matriz workspace y crash por frontera que el criterio 14 enumera.

### HA-11 — MEDIO

**Qué es:** el plan rompe pruebas existentes que ordena ejecutar y contradice su cifra de censo.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:61-64,1138-1155,1321-1346`; pruebas `tests/test_escritura_censo.py:49-75,214-233`; `tests/test_abrir_caso_modo_v1.py:107-128`.

**Por qué importa:** `registrar_cierre_v1` añade un tercer `append_event` a `scripts/abrir_caso.py`, elevando el total de 83 a 84; fallan los dos trinquetes. Además, el test vigente de V1 válida dobla `_despachar_intake`; tras sustituir esa costura por `secuencia_v1`, el doble queda inerte y el test llega al Drive real. El plan exige que ese fichero quede verde pero no lo adapta.

**Cómo lo comprobé:** ejecutado. El detector devolvió 84/83 y dos fallos. En la reproducción del test vigente, la invocación intentó el pull real y falló; la línea base congelada daba 31/31 verdes para los dos ficheros seleccionados.

**Qué haría falta:** hacer pasar el nuevo evento por la política/costura decidida sin aumentar deuda, mantener el techo exacto, y migrar el test existente a la nueva costura de inyección asegurando cero red.

### HA-12 — BAJO

**Qué es:** dos cifras de gobernanza no son reproducibles y una actualización propuesta empeora un contador ya rancio.

**Dónde:** plan `docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:39-40,1131-1135`; código `core/intake_log.py:1-10,38-95`.

**Por qué importa:** `INTAKE_EVENTS` tiene hoy 33 miembros; añadir uno exige 34, no cambiar «27» a «28». Para «103 referencias» no se declara comando ni unidad y los recuentos reproducibles dieron 53 apariciones exactas de `scripts.abrir_caso`, o 657 del token ancho `abrir_caso`. Esas cifras se usan para justificar decisiones y no pueden auditarse.

**Cómo lo comprobé:** ejecutado por import/`len` y barrido textual del archivo. SIN VERIFICAR frente a la historia Git, que la copia deliberadamente no contiene y no se reclama.

**Qué haría falta:** corregir 33→34; declarar comando, patrón, ámbito y unidad del recuento de referencias, o retirar la cifra.

## 3. Lo que NO es un hallazgo

- La afirmación técnica estrecha sobre el proceso aguanta con la implementación actual: `mutex_sesion._SESIONES` es estado de módulo (`core/casos/mutex_sesion.py:58-60`), `sostenido` se une a la sesión vigente (`:132-157`) y `case_mutex.adquirir` rechaza otro lease vivo (`core/casos/case_mutex.py:429-435`). Un subproceso que volviera a adquirir chocaría. No es una imposibilidad arquitectónica universal —podría diseñarse otra capacidad entre procesos—, pero el plan no necesita abrir esa tercera vía.
- `res.skipped` no es guarda inerte: `pull_drive_ev` lo produce en ejecución cuando existe `.pulled` (`core/intake_drive.py:206-228`). El defecto es la semántica de saltar la consulta, no su alcanzabilidad.
- `status is None` tampoco es inerte: `_atomizar_correo` retorna por el no-op sin correo y sin árbol previo (`scripts/sala_maquina.py:595-599`). Mapearlo sin pendiente es coherente para esa rama; lo que no aguanta es el mutante F12.
- `hasta not in nombres` es alcanzable por entrada de usuario y el secuenciador puro la rechaza antes de correr sus etapas. El hallazgo HA-06 es que esa validación llega demasiado tarde respecto del entrypoint completo.
- `sin_element` puede aparecer en metadatos legacy o manuales; no afirmo que sea imposible en producción. Sí es redundante como prueba de «no adivinar» si su mutante solo provoca un `KeyError`, y por eso se critica el mutante, no la existencia de la validación.
- Las citas `core/sync_sudespacho.py:1356` (default judicial), `core/intake_drive.py:206` (marcador), `scripts/sala_maquina.py:578/779` y el censo 83 son correctas en la copia. También se reprodujo el 43/5 de `now_iso` frente a `now_iso_utc`.
- Se confirmó la afirmación de cero apariciones de `preparado_con_pendientes` en `core/`, `scripts/` y `tests/` antes de aplicar el plan.
- La puerta V1 vigente sí se ejecuta antes de identidad y efectos y rechaza CRM distinto de `skip`, fuentes ajenas, `dry_run`, falta de `folder_id` y `force` sin `case_id` (`scripts/abrir_caso.py:423-492,530-539`). El plan no regresa esas guardas por sí mismo.
<!-- informe-literal:fin:q7km -->

## 2. Evidencia verificada por el adjudicador

Cada hallazgo se contrasto contra el codigo del worktree, no contra el informe. Lo verificado
por mi cuenta, con el comando o la lectura que lo sostiene:

- **HA-02.** `scripts/abrir_caso.py:136-175`: `_intake_drive_ev` calcula `hash_tree_local` sobre
  el destino EFECTIVO, llama a `_intake_generico` y, ante `DriveIntakeError`, registra los bytes
  parciales con `status: fallo` antes de relanzar. Mi adaptador se saltaba las tres cosas.
  **Es reincidencia:** esa custodia es justamente lo que R14/H14-02 y R15/H15-06 arreglaron.
- **HA-04.** `core/sync_sudespacho.py:1306-1318`: `PullResultV2` comunica `blocked_legacy_v1`,
  `documents_failed` y `errors` **por retorno**. Y `CLAUDE.md` §14.6 dice, literal, «verificar
  por resultado, nunca por status». Mi adaptador marcaba `hecha` con cualquier retorno.
- **HA-07.** `core/casos/case_mutex.py:615-659`: con `fallo_del_cuerpo=True` la perdida del mutex
  solo se anota sobre la excepcion en vuelo; sin excepcion, se **lanza** `MutexPerdido`. Mi
  `typer.Exit(0)` dentro del bloque convertia el camino ruidoso en una nota y salia 0. Rompe la
  propiedad que R12/H12-04 fijo: «una perdida no se evapora».
- **HA-03, elevado a CRITICO.** El §11 de la spec lista, literalmente:
  «`.pulled` evita volver a Drive | Falso punto fijo | Consulta remota real en cada ronda; cache
  o skip no cuentan como "sin novedad"». Mi plan construia su punto fijo sobre ese skip, y ademas
  lo use como argumento ante Nikolai para preferir la ejecucion desatendida. La spec ya habia
  nombrado el mecanismo como riesgo con su mitigacion.
- **HA-01.** La misma tabla exige `estado.json` atomico «obligatorio desde la primera entrega».
  Aplazar el protocolo durable no es una omision del plan: contradice una linea expresa.
- **HA-10.** `core/casos/case_locator.py:222-223`: `read_case_meta` devuelve `fm.get("meta")`. Mi
  fixture escribia las claves en el nivel superior del frontmatter, asi que el lector devolvia
  `{}` y la etapa CRM tomaba la rama `saltada`: el E2E habria pasado sin probar el CRM.
- **HA-08 — PARCIALMENTE REFUTADO, y la primera version de esta linea era mia y estaba mal.**
  Escribi aqui que una corrida parcial podaba contra un `esperados` incompleto. **La guarda
  existe:** el `unlink` de `mensajes/` esta dentro del `else` de `if report.errores:`
  (`core/email_atomize/pipeline.py:204-220`), y el comentario dice «La poda solo retira huerfanos
  cuando la foto esta completa». Sobrevive solo en `vistas/*.md` (`:262-267`) y en
  `*.contenido.md` (`core/adjuntos_contenido/pipeline.py:107-109`), que no llevan la guarda y donde
  lo perdible es un derivado regenerable, nunca material de cliente. La contradiccion con D4 sigue;
  el riesgo de perdida que le atribui, no.
- **HA-12.** `len(INTAKE_EVENTS)` es **33**, no 27. Y «103 referencias a `scripts.abrir_caso`» no
  es reproducible: `git grep -o` da **53** en **19** ficheros. **La cifra no es mia: es del §24 D3
  de la spec**, que la usa para justificar la decision de modo-frente-a-subcomando. La copie sin
  medirla, que es el defecto por el que aqui figura.

Lo que **no** se verifico y se declara ausente: la corrida real sobre W-02Q38C, el acceso a Drive
y a Sudespacho, la suite completa con dos semillas —el interprete del revisor no tiene
`pytest-randomly`— y el aislamiento dinamico de los trece mutantes distintos de F12.
