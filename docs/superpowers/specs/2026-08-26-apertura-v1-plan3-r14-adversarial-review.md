---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-08-26-apertura-v1-plan3-write-set.md
objeto_rev: "rev. 1 — el diseño común de 3A/3B/3C"
commit: 7c55a13
ronda: "14"
revisor: Codex
veredicto: NO-EJECUTABLE
marcador_nonce: h8rt
sha256_informe: 7a0707142d381a6a3e2fbe3dc04d79c9d53cc099884563b5ec6d4031e91ada9b
adjudicado_en: docs/superpowers/plans/2026-08-26-apertura-v1-plan3-write-set.md §0
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R14.** El §1 conserva literalmente la voz del revisor; la
> adjudicación vive en el **§0 del plan**.
>
> **Primera ronda de este plan, corrida sobre el DISEÑO y antes de escribir una línea de
> código.** Veredicto `NO-EJECUTABLE`: **9 hallazgos, 9 confirmados, 0 refutados** — 3
> CRÍTICOS, 5 ALTOS, 1 BAJO.
>
> **El que justifica la ronda entera:** el plan indexaba el mutex por el W-code que
> `_w_code_de` extrae del **nombre de la carpeta**, cuando la identidad canónica del
> catálogo es `meta.id_go` del `_caso.md` — y el docstring de `CaseRef` dice literalmente
> que el nombre de carpeta «es una presentación y no basta como identidad». Nadie comprueba
> que las dos concuerden, así que un caso cuya carpeta diga `(W-ABC)` y cuyo `_caso.md`
> declare `id_go: W-XYZ` admite **dos lockfiles**: dos procesos escribiendo el mismo
> expediente, los dos creyéndose protegidos. El plan existía para cerrar exactamente eso.
>
> **Y el hallazgo que más dice de cómo fallo:** el plan se autoconcedía un presupuesto de
> «cuatro rondas en vez de seis» contando esta R14 como ronda de diseño de las tres tandas,
> cuando el documento solo especifica 3A —de 3B hay una lista de filas y de 3C una frase—.
> Una ronda no puede revisar mecanismos ausentes. Es el sesgo que `CLAUDE.md` ya nombra:
> cuando mi propia regla de parada me obliga a algo que no me conviene, redefino la
> contabilidad en vez de aceptarla.
>
> **Limitaciones declaradas por el revisor, y se conservan:** no pudo acreditar que la copia
> corresponde al commit `7c55a13` (el `git archive` no lleva metadatos Git), no pudo ejecutar
> `filelock` (ausente en su entorno) ni un `fork` real (host Windows, `spawn`), y no pudo
> reproducir mi censo de «~85 primitivas» porque el plan no publicaba ni el algoritmo ni la
> lista de ficheros. Las tres las declara **SIN VERIFICAR**, no refutadas.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:h8rt -->
# R14 — revisión adversarial del diseño del Plan 3 (Codex, 2026-08-26)

Veredicto: NO-EJECUTABLE
sha256 del documento al abrir: 87d0b3a9de4191582c7192f205573710e0a43f8bbdde6046d73be23ab01c90fb
sha256 del documento al cerrar: 87d0b3a9de4191582c7192f205573710e0a43f8bbdde6046d73be23ab01c90fb
Comandos ejecutados:

- `Get-FileHash -Algorithm SHA256` al abrir y al cerrar sobre el documento revisado.
- `git -C ../r14-objeto rev-parse HEAD` — falló: la copia no contiene metadatos Git utilizables.
- `Get-Content`, `Select-String`, `Get-ChildItem` y numeración PowerShell para leer y cruzar el plan, la spec §§24-25, `case_mutex.py`, `case_manager.py`, `case_locator.py`, `intake_log.py`, `repository_checkout.py`, los planes 1 y 2, el plan de Fase 1, `CLAUDE.md` y fuentes de los productores.
- `rg` — intento fallido: no está instalado; el barrido se rehízo con `Select-String` y AST.
- Python 3.14.7 con `-B`: inventario AST de llamadas al guard, `dir_intake`, `append_event`, relojes y primitivas de escritura; sondas puras de `_w_code_de` y `_w_code_valido` extraídas de su AST, sin importar ni escribir el repo.
- Dos intentos de importación directa para la sonda de identidad fallaron antes de ejecutar (`core` fuera de `sys.path`; después, dependencia `httpx` ausente). Se sustituyeron por la extracción AST anterior.
- `python -B -c` para comprobar plataforma y `multiprocessing`: `os.name == "nt"`, método `spawn`.
- `importlib.util.find_spec`: `filelock=False`, `httpx=False`, `pytest=True`.

## Hallazgos

### H14-01 — La identidad textual permite dos mutex para un mismo expediente — CRÍTICO
**Qué:** `_w_code_de` no obtiene la identidad canónica del caso: toma el primer `W-…` entre paréntesis del nombre de carpeta, o acepta un W-code suelto. En cambio, el catálogo considera canónico `meta.id_go`. No hay comprobación de que ambos coincidan. Un caso cuya carpeta contenga `(W-ABC)` y cuyo `_caso.md` declare `id_go: W-XYZ` puede ser abierto por el camino canónico con `W-ABC` y por un workspace registrado con `W-XYZ`. Ambos valores pasan `_w_code_valido` y producen dos lockfiles. Dos procesos pueden entonces escribir simultáneamente en el mismo expediente creyéndose ambos protegidos. El caso dual también existe: dos carpetas distintas con el mismo token textual pero `id_go` distintos colapsan innecesariamente al mismo mutex.
**Dónde:** `core/casos/case_locator.py:78-103,226-258`; `core/casos/case_catalog.py:56-95`; `core/casos/workspace_resolver.py:157-168`; `core/casos/case_mutex.py:126-133,239-250`.
**Por qué es un defecto:** D2 exige indexar por identidad canónica. Indexar por una heurística del nombre rompe justamente la exclusión cuando las dos representaciones divergen. La unicidad de `meta.id_go` evita dos metadatos iguales, pero no valida nombre frente a metadato y por ello no cierra este caso.
**Cómo lo verifiqué:** lectura de las dos rutas de resolución y sonda ejecutada sobre las funciones literales extraídas del AST. `_w_code_de('BaA - (W-ABC) - (W-XYZ)')` devolvió `W-ABC`; `_w_code_valido` lo aceptó. `W-XYZ` también fue aceptado como namespace distinto. La fuente del resolver por ruta toma, en cambio, `entrada.w_code` del registro.
**Remedio que propondría:** hacer que la adquisición reciba un `CaseRef` ya resuelto y use exclusivamente su W-code canónico validado; para altas, usar el W-code explícito antes de crear la carpeta. Añadir una invariancia de entrada que rechace nombre, registro y `meta.id_go` discordantes, con una prueba que recorra las vías por identidad y por ruta y exija el mismo `ruta_del_lock`.

### H14-02 — 3A publica una cadena de custodia calculada sobre el árbol equivocado — CRÍTICO
**Qué:** la fila #6 ya deposita en el destino efectivo devuelto por el guard, pero `_intake_drive_ev` ignora ese destino y calcula los hashes desde `case_dir/00_Input/01_Drive EV`, la ruta canónica. Después usa esos hashes para reconciliar y emitir el evento de intake. El plan incluye #8 en 3A, la deja expresamente abierta hasta 3C y aun así permite cerrar y desplegar 3A. En un caso desviado, los bytes nuevos quedan sin hash y el log puede atribuir al pull bytes viejos del canon.
**Dónde:** `core/intake_drive.py:191-199,304-322`; `scripts/abrir_caso.py:78-116`; `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1753-1755,1767-1774,1802-1808`.
**Por qué es un defecto:** no es solo cobertura aplazada. Produce una afirmación forense falsa: bytes, hash, manifiesto y evento dejan de describir el mismo destino. Eso es corrupción de la cadena de custodia y materializa exactamente el agujero que la costura pretende cerrar.
**Cómo lo verifiqué:** seguí el valor `target_dir` desde `dir_intake` hasta el pull y, por separado, el `case_dir` fijo usado por `hash_tree_local` y por `_inventario_desde_hashes`. Las dos ramas solo coinciden cuando no hay desvío. La spec exige expresamente que la cadena siga el destino efectivo.
**Remedio que propondría:** mover el cierre de #8 a la misma unidad atómica que #6 y #7; `pull_drive_ev` debe devolver el destino efectivo y el orquestador debe hashear exactamente ese `Path`. 3A no debe tener criterio de salida ni ser desplegable mientras esa prueba E2E de los cuatro planos falle.

### H14-03 — La unión entre hilos no define quién mantiene vivo el `tomado()` — CRÍTICO
**Qué:** `tomado()` liga el hilo de latido y la liberación al `finally` del context manager que adquirió. El diseño nuevo permite que otro hilo se una a la misma sesión, pero solo prueba que el bloque interno sale antes que el externo. No cubre la secuencia permitida por M7: hilo A adquiere, hilo B se une, A sale mientras B sigue dentro. Si A cierra su `tomado()`, detiene el latido y libera el lock bajo B; si no lo cierra, el plan no dice quién ni cómo lo cerrará cuando salga el último usuario.
**Dónde:** `core/casos/case_mutex.py:577-625,630-660`; `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1649-1660`.
**Por qué es un defecto:** M3 habla de anidamiento léxico y M7 de unión entre hilos como si fueran la misma topología. No lo son. En la secuencia anterior, B puede seguir escribiendo después de liberado el mutex y otro proceso puede entrar: falsa garantía de exclusión mutua.
**Cómo lo verifiqué:** traza de estados contra la implementación real de `tomado()`: `parar.set()`, `hilo.join()` y `liberar()` se ejecutan al salir del adquirente, sin conocer prestatarios externos. No existe todavía código de `mutex_sesion` que pueda someterse a prueba dinámica, pero el caso contradice el ciclo de vida que la envoltura promete conservar.
**Remedio que propondría:** modelar propietario de recurso y prestatarios por separado. El recurso subyacente debe cerrarlo el último prestatario, no el primer context manager que adquirió; la transición 1→0 debe ser atómica y esperar/rechazar nuevas uniones durante el cierre. Añadir una frontera propia con dos hilos y barreras en el orden `A entra → B entra → A sale → B verifica/escribe → B sale`, además de la variante con excepción de A.

### H14-04 — El mapa de sesión omite una parte del namespace: `raiz` — ALTO
**Qué:** el lock real se identifica por `(raiz normalizada, W-code)`, pero el diseño declara `_SESIONES` indexado solo por W-code. Las APIs nuevas conservan `raiz`, y `SesionMutex.revalidar()` consulta la raíz almacenada en la sesión. Una llamada para el mismo W-code bajo otra raíz no puede coexistir en ese mapa: o se une y afirma titularidad sobre el lock equivocado, o se rechaza una operación independiente sin contrato que lo autorice. M5 solo prueba W-codes diferentes.
**Dónde:** `core/casos/case_mutex.py:191-250,495-525,538-574`.
**Por qué es un defecto:** `raiz` no es decoración de test: cambia el fichero que materializa la exclusión. Omitirla de la clave hace inejecutable la firma prometida o convierte `vigente(w, raiz=B)` en una garantía sobre `raiz=A`.
**Cómo lo verifiqué:** comparé `ruta_del_lock`, que compone la raíz, con los campos de `SesionMutex` y su `revalidar`, que relee `self.raiz`. El conjunto M1-M7 no contiene el caso “mismo W-code, raíz distinta”. M1/M6 y M3/M4 sí son ramas distintas (éxito/fallo y salida normal/excepcional); el defecto no se arregla fusionando esos tests, sino añadiendo esta frontera.
**Remedio que propondría:** clave canónica `(raiz_de_locks(raiz) normalizada, w_code canónico)` en `_SESIONES`, y la misma clave en `vigente`; probar raíz igual expresada de dos formas equivalentes y dos raíces realmente distintas.

### H14-05 — La costura devuelve una ruta, pero no obliga a escribir en ella y el guard propuesto no puede detectarlo — ALTO
**Qué:** el diseño deja la autorización separada del efecto: `destino()` devuelve un `Path` y el llamador conserva plena capacidad de componer otro. El Task 6 promete un censo AST de escrituras que “no pasan” por la costura, pero el propio plan admite que una llamada seguida de escritura en otra ruta pasa el censo. La fila #8 demuestra que no es hipotético. Tampoco se incorporan las pruebas E2E por productor que exige §25.4.
**Dónde:** `core/case_manager.py:775-839`; `core/intake_drive.py:191-199`; `scripts/abrir_caso.py:112-116`; `tests/test_guard_localizador.py:56-90`; `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1800-1810`.
**Por qué es un defecto:** la costura no cierra el agujero; lo mueve a una convención del llamador. El precedente del localizador cuenta una forma sintáctica local (`strict=False`). No demuestra flujo de datos y no puede justificar que el `Path` autorizado sea el consumido por `mkdir`, `open`, `rclone`, `os.replace` o helpers intermedios. Llegar a “cero” en ese censo no implica cobertura semántica.
**Cómo lo verifiqué:** inspeccioné el guard permanente usado como precedente y reconstruí por AST las llamadas actuales: tres a `guard_escritura`, tres a `dir_intake` y 16 a `append_event`. El ejemplo concreto #8 pasa por `dir_intake` dentro de `pull_drive_ev` y después vuelve a `case_dir`, justo el patrón que el censo propuesto declara invisible.
**Remedio que propondría:** hacer que la costura ejecute el efecto o entregue una capacidad de escritura que no exponga la raíz canónica, y añadir tests de integración por cada fila que doblen ambos destinos y prueben cuál cambió. Si se conserva un guard AST, debe ser solo un trinquete sintáctico complementario, no la prueba de cierre.

### H14-06 — C1 mezcla tres contadores y no tiene transición ejecutable a rechazo — ALTO
**Qué:** C1 habla de una llamada en `libre` que escribe, emite un evento y “suma al censo”; Task 3 mide llegadas dinámicas sin mutex; Task 6 define un censo AST estático de sitios fuera de la costura. No se especifica cuál de ellos gobierna el cambio de polaridad, dónde vive el tope, quién lo reduce ni qué cambio de código hace que `destino(..., modo="libre")` empiece a rechazar cuando llegue a cero. Además, `intake_log` tiene un vocabulario cerrado y no existe un evento “escritura_sin_mutex”. Si ese evento se emite mediante `append_event` una vez migrada la fila #13, vuelve a entrar en C1 sin mutex y recurre; si se escribe por debajo, viola la costura única y la regla “protocolo nunca exento de mutex”.
**Dónde:** `core/intake_log.py:38-75,201-268`; `core/case_manager.py:775-816`; `tests/test_guard_localizador.py:16-25,37-40,82-90`.
**Por qué es un defecto:** no hay mecanismo que convierta el número estático en conducta de producción. El censo puede bajar a cero y C1 seguir permisivo para siempre; o el implementador puede intentar el evento exigido y producir recursión o una excepción por evento desconocido. El precedente citado no invertía conducta automáticamente: el `TECHO_ESCOTILLA` y el default se cambiaron explícitamente.
**Cómo lo verifiqué:** lectura del conjunto cerrado `INTAKE_EVENTS`, de la validación que lanza para eventos desconocidos y del guard de Fase 1. Ese guard solo compara `len(hallados) <= TECHO_ESCOTILLA`; no conecta el conteo a una rama de producción. El orden mutex→guard sí quedó confirmado: `guard_escritura` llama realmente a `append_event` al desviar. No encontré una regresión del orden en sí; el defecto aparece al combinarlo con C1 y con la migración de `append_event`.
**Remedio que propondría:** separar contratos: (a) métrica dinámica solo diagnóstica, (b) censo AST con tope explícito, (c) flag/versionado de polaridad cambiado mediante un task y test propios. Diseñar antes un evento permitido y una vía no recursiva; preferiblemente registrar el intento fuera del log del caso o rechazar sin intentar una escritura auditora no protegida.

### H14-07 — El reparto 3A/3B/3C no cubre las 27 filas y hace imposible el criterio de salida de 3A — ALTO
**Qué:** la partición enumera #4-#13 en 3A, once filas en 3B (#14-#17, #19, #21-#24, #26, #27) y #18/#20 en 3C, con #8 repetida como cierre. Quedan sin tanda explícita #1, #2, #3 y #25. A la vez, 3A exige que “las doce de protocolo” estén declaradas, pero 3A solo contiene ocho filas de protocolo; las otras cuatro (#21, #22, #26, #27) están en 3B. Y 3B no son “los diez derivados”: contiene siete derivados y cuatro protocolos.
**Dónde:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1751-1798`; `core/case_manager.py:219-294,356-375`; `core/sala_maquina.py:448`.
**Por qué es un defecto:** el plan padre prometía las 25 clases que no consultaban el guard; esta partición deja fuera la creación estructural de `ensure_case` y no asigna el destino de archivado. Las filas #1-#3 son además una dependencia real: `ensure_case` crea la raíz antes de que exista un caso que el guard vigente pueda resolver. No basta con decir que el entrypoint sostiene el mutex; incumple la arquitectura “toda escritura pasa por un sitio” y deja sin diseñar cómo trata la costura un alta.
**Cómo lo verifiqué:** rehice la unión de números y la clasificación contra la tabla cerrada de §25. La secuencia real de `abrir_caso` llama `ensure_case` antes de `localizar`, y `ensure_case` crea raíz, subdirectorios y plantillas. El Plan 1 declara expresamente que no toca el write-set, por lo que no hay otra tanda previa que absorba esas filas.
**Remedio que propondría:** publicar una matriz exhaustiva 1-27 con exactamente una tanda responsable y dependencias explícitas. Diseñar una operación de alta distinta del guard de caso existente, bajo el mismo mutex de W-code; mover #25 a 3C de forma expresa; corregir los recuentos y hacer que cada criterio de salida nombre solo filas de su tanda.

### H14-08 — Se consume una ronda de diseño común para dos tandas cuyo diseño no existe — ALTO
**Qué:** la justificación de cuatro rondas cuenta esta R14 como ronda de diseño de 3A, 3B y 3C. Sin embargo, el documento solo especifica interfaces, tareas, tests, mutantes y criterio de salida de 3A. Para 3B hay una lista de filas; para 3C, una frase sobre archivar y cerrar #8. No se define generación, coherencia de agregados, fusión de cobertura, formato/colisión del archivo, atomicidad ni recuperación ante fallo.
**Dónde:** `CLAUDE.md:50-60`; `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1753-1756,1775-1788,1807-1818`.
**Por qué es un defecto:** el presupuesto exige una ronda de diseño para cada pieza que decide quién escribe o puede destruir/corromper datos. Una ronda no puede revisar mecanismos ausentes. Contarla ahora deja 3B/3C sin revisión de diseño o fuerza después una ronda que el propio plan llamará “tercera”.
**Cómo lo verifiqué:** comparé el contenido operativo disponible para 3A con las obligaciones de las filas asignadas a 3B/3C y con la regla literal de `CLAUDE.md`. No hay mecanismo revisable para las obligaciones citadas.
**Remedio que propondría:** o bien completar ahora el diseño común hasta el mismo nivel para las tres tandas, o reconocer tres piezas y dar a cada una diseño+diff. Si el techo impide esto, reducir alcance o pedir la autorización expresa prevista por `CLAUDE.md`; no contabilizar una ausencia como ronda ejecutada.

### H14-09 — La sección «SIN VERIFICAR» es incompleta — BAJO
**Qué:** declara NTP, remediaciones R13 y límite semántico del censo, pero omite al menos: comportamiento tras `fork`; identidad de sesión con raíces distintas; salida del adquirente antes que un prestatario de otro hilo; reproducibilidad del censo de “~85 primitivas en ocho ficheros”; y cobertura real de 3B/3C. También presenta 43 usos de `now_iso` frente a 7 de `now_iso_utc` sin decir que no usa la misma métrica para ambos.
**Dónde:** `core/casos/case_mutex.py:40-43,159-161,577-625`; `CLAUDE.md:40-41`; `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1730-1735`.
**Por qué es un defecto:** varios supuestos sostienen el diseño o su presupuesto y no están verificados ni marcados. Eso hace que “SIN VERIFICAR” parezca exhaustivo cuando no lo es.
**Cómo lo verifiqué:** inventario AST propio: la tabla §25 nombra once ficheros productores efectivos (catorce rutas si se cuentan las referencias legacy de #2), y mi matcher literal de las primitivas enumeradas obtuvo 79 sitios en esos once, no 85. Para el reloj, el patrón de llamada obtuvo 43 apariciones de `now_iso(` y 5 de `now_iso_utc(`; el número 7 solo aparece al contar además otras menciones/imports. No afirmo que 79 sea el censo correcto —el plan no publica algoritmo ni lista de ocho ficheros—; afirmo que su medición no es reproducible como está descrita.
**Remedio que propondría:** añadir comando, raíces, exclusiones y salida versionada de cada censo; usar la misma definición de “uso” para ambos relojes; incorporar explícitamente los límites de hilos, raíces y procesos derivados.

## Lo que NO pude verificar

- No pude acreditar que la copia corresponde al commit `7c55a13d1b1904d1ca6ae4bceea064323b5e2594`: `../r14-objeto` no contiene metadatos Git utilizables. Verifiqué el contenido disponible y su hash, no su genealogía.
- No pude ejecutar la batería de `case_mutex` con `filelock` real porque `filelock` no está instalado. El diseño de `mutex_sesion` aún no tiene código, por lo que tampoco existe una batería M1-M7 que correr.
- No pude ejecutar un `fork` en este host Windows. Comprobé que `multiprocessing` usa `spawn`, que inicia un intérprete nuevo y por tanto no hereda `_SESIONES`. En una plataforma con `fork`, el mapa, nonce y `_PROCESO_UID` se copiarían mientras los hilos de latido no sobreviven; el plan no define `register_at_fork` ni invalidación. Lo marco **SIN VERIFICAR** dinámicamente, no refutado.
- No pude reconstruir el censo de 85 primitivas porque el plan no identifica sus ocho ficheros ni el algoritmo exacto. El inventario alternativo descrito en H14-09 es evidencia de no reproducibilidad, no un censo sustituto adjudicado.
<!-- informe-literal:fin:h8rt -->

## 2. Evidencia verificada por el adjudicador

Lo que comprobé **contra la fuente**, no contra el informe:

- **Cadena del acta:** `marcador_nonce: h8rt`, exactamente un marcador de inicio y uno de
  fin, en orden, y el nonce **no** aparece dentro del informe. `sha256_informe` recomputado
  sobre la canonicalización del §4 y **coincide**.
- **No-mutación del objeto:** `sha256` del documento revisado antes y después de la corrida,
  `87d0b3a9de4191582c7192f205573710e0a43f8bbdde6046d73be23ab01c90fb` en los dos casos. El
  revisor reporta el mismo par. Es prueba más fuerte que un `git status` limpio, porque la
  copia externa es de solo lectura por construcción.
- **H14-07, la aritmética del troceo:** transcribí las 27 clases del §25 con su clase y conté.
  La partición del plan cubre 25 filas y deja **#1, #2, #3 y #25 sin tanda**; 3A contiene **8**
  filas de protocolo y su criterio de salida exigía «las doce»; y 3B es **7 derivados + 4
  protocolos**, no «los diez derivados». Confirmado sin margen de interpretación.
- **H14-01, la identidad:** `CaseCatalog._por_w_code` casa contra `meta.id_go`
  (`core/casos/case_catalog.py:80-95`); `_w_code_de` extrae del nombre de carpeta
  (`core/casos/case_locator.py:78-103`). Y medí además que la gramática de los dos no coincide:
  `_w_code_de` extrae `W-AB` y códigos de 22 caracteres que `_w_code_valido` **rechaza** con
  `ValueError` — un tercer estado de identidad que mi C6 no enumeraba.
- **Lo que refuté de mi propia lectura inicial, antes de escribir esto:** creí que
  `W-abc` y `W-ABC` producirían **dos** lockfiles. Falso: `_w_code_valido` normaliza a
  mayúsculas *antes* de casar y `ruta_del_lock` compone con el valor canónico devuelto, así
  que colisionan en uno. La primitiva está bien; el defecto está en mi plan.
- **H14-02, la cadena de custodia:** `pull_drive_ev` escribe en el `target_dir` que devuelve
  `dir_intake` (`core/intake_drive.py:196`), pero `_intake_drive_ev` hashea
  `case_dir / "00_Input" / subdir` en duro (`scripts/abrir_caso.py:112`). Con desvío, las dos
  ramas no coinciden y el evento describe un árbol donde los bytes no están.
- **H14-06, la recursión:** `INTAKE_EVENTS` es un `frozenset` cerrado
  (`core/intake_log.py:41-75`) sin evento para «escritura sin mutex», y `append_event` lanza
  `ValueError` ante uno desconocido. El evento que mi C1 prometía **no se puede emitir**, y
  emitirlo por `append_event` —que es la fila #13, protocolo, obligada a pasar por la costura—
  recurre. Ese defecto lo introduje yo **en la autorrevisión de este mismo plan**.
- **H14-09, mis números:** con **una sola** definición de uso (llamada con paréntesis) en
  `core/` + `scripts/` salen **43 `now_iso(` frente a 5 `now_iso_utc(`**, no 7. Mi «7»
  contaba además imports y menciones: dos definiciones distintas dentro de una misma
  comparación. Y el censo de primitivas sobre los **11** ficheros que la tabla nombra da
  **80** (el revisor obtuvo 79); mi «~85» salió de **8** ficheros y un patrón que no publiqué.
- **Lo que el revisor NO pudo verificar y por tanto no está refutado:** exclusión real entre
  procesos con `filelock`, comportamiento tras `fork`, y la genealogía de la copia. Consta.
