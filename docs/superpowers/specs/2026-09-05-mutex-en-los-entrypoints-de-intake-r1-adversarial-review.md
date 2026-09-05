---
tipo: revision-adversarial
objeto: "diseño «El mutex del caso lo pide quien escribe» rev. 1 (MEJORAS #126, PLAN fila #17, PR #292)"
objeto_rev: "1"
commit: "7e3a0f4"
ronda: "1"
revisor: Codex
veredicto: REQUIERE-REVISION
marcador_nonce: q8zn
sha256_informe: 0343e99dea069b62d93b059212fbf2f73f732c9aaa9935932350f5126d18ffa4
adjudicado_en: docs/superpowers/specs/2026-09-05-mutex-en-los-entrypoints-de-intake-design.md §7
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1 sobre un DISEÑO.** Primera de las dos rondas que la pieza
> compra por radio de daño (decide quién escribe sobre el árbol del caso); la segunda irá sobre el
> diff. El §1 conserva la voz del revisor sin una coma cambiada; el §2 es la evidencia que
> verifiqué yo. **La adjudicación NO está aquí:** va en el §7 del diseño, que pasa a **rev. 2**.
>
> **Objeto:** una copia externa del árbol en `7e3a0f4` montada con `git archive`; el objeto es el
> spec y el resto del árbol la fuente. Codex `gpt-6-astra`; verificó el hash del objeto al abrir
> y al cerrar (coinciden con el que calculé yo) y declaró que no acredita genealogía.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:q8zn -->

Higiene inicial CONFORME: `C:\t\rev126_design\rev` contenía exclusivamente `MANDATO.md`; no se encontró ni leyó ningún otro fichero preexistente en ese directorio.

# R1 adversarial del diseño MEJORAS #126 — fila #17

## 1. Objeto y huella de apertura

Objeto único: `../head/docs/superpowers/specs/2026-09-05-mutex-en-los-entrypoints-de-intake-design.md`, rev. 1. Las referencias de fuente que siguen son relativas a `../head/`, con numeración de líneas de esa copia. No se revisa una implementación del helper: todavía no existe.

SHA-256 al abrir, calculado antes de leer el diseño:

`fe8caf47f9a69b2ba7512c7b3a611672bd942f3c7a8984ab7d174d29da3883e9`

Se trabajó sin escribir en `head/`. Las ejecuciones usaron `./scratch_head/`, copia externa creada después de comprobar la higiene; los datos sintéticos y temporales quedaron bajo este workdir. El mandato específico de revisión prevalece sobre el flujo ordinario de desarrollo de `AGENTS.md`/`CLAUDE.md`: no se hicieron cambios de proyecto, commits, cierre de sesión del repo ni consultas al CRM real.

## 2. Resumen en tres líneas

La reserva del export queda fuera del bloque descrito y puede crear un lote y una traza aun con el caso ocupado.
La identidad necesita contratos distintos para `--ref`, casos existentes y altas; `--src/--out` conserva una vía real de escritura sin mutex.
Los 17 tests existentes pasan y el censo mide 88; la ampliación de E4 es incompatible y E7–E13 necesitan precisar cobertura, aislamiento y sincronización.

## 3. Hallazgos

### H-01 — ALTO — El bloque del export comienza después de una escritura

**Diseño:** §3.2, fila `export_label_emails.main`, y garantía de cero bytes de §2.

**Fuente:** `scripts/export_label_emails.py:64` llama a `email_dest_dir(case_id)` antes de `export_label` en la línea 65. `core/email_export.py:1433` devuelve `reservar_lote(...)`; `core/intake_lotes.py:94` llama a `dir_intake` y la línea 96 hace literalmente `destino.mkdir(parents=True, exist_ok=False)`. Además, `core/case_manager.py:1234` pasa por `guard_escritura`, que puede ejecutar `append_event` en la línea 1212 cuando desvía a bandeja.

**Reproducción:** `sondas.py` toma el mutex con la primitiva, llama a `email_dest_dir` y después intenta `sostenido`: el lote ya existe cuando llega `CaseBusy`. `sondas_extra.py` repite la reserva con estado `prestado`: aparecen `_pendiente_checkin/email/00_Input/2026-09-05_email_01/` y `00_Input/_intake_log.jsonl`.

**Esperado:** rechazar al segundo escritor sin alterar el árbol del caso. **Observado:** envolver solamente `export_label(...)`, como especifica la tabla, llega tarde; en un caso disponible deja al menos un directorio y en uno prestado también bytes de protocolo. La expresión «tras resolve_ref» permite una implementación correcta, pero «alrededor de export_label» deja una frontera contradictoria que debe resolverse expresamente.

**Cambio necesario:** meter `email_dest_dir` y `export_label` en el mismo bloque; E7 debe observar también la reserva y los directorios. `resolve_ref` sí puede permanecer fuera: en este flujo solo enumera y lee (`core/casos/case_locator.py:226`), comprobado también por instantánea con hashes.

### H-02 — MEDIO — La adquisición del alta no se resuelve con el helper propuesto

**Diseño:** §§3.1, 3.2 y 6; afirmación de que `ensure_case` se une al mutex y duda sobre su modo `libre`.

**Fuente:** `scripts/sync_sudespacho.py:160` y `:247` llaman a `ensure_case` sin `modo` ni `id_go`. El valor por defecto es `modo="libre"` (`core/case_manager.py:479`); solo la rama `if es_v1` de la línea 528 consulta `vigente` en la 541. La primera creación está en la línea 668. Para el alta v1, las líneas 533–540 exigen una identidad explícita y rechazan derivarla del nombre. El helper heredado lee `caso_path(case_id)/00_Input/_caso.md` (`scripts/migrar_layout_intake.py:161`); al faltar el caso captura `OSError` y devuelve `None`. `LocalWorkspaceMissing` hereda de `FileNotFoundError` (`core/casos/workspace_model.py:169`): no hay aquí un traceback inevitable por el caso ausente.

**Reproducción:** `sondas.py` hace fallar cualquier llamada a `vigente` y ejecuta `ensure_case` por defecto: crea el caso, sin consultar el mutex, y persiste `meta.id_go: null`. `sondas_extra.py` rodea ese alta con el helper existente: avisa, entrega `None` y crea el caso igualmente, aunque el nombre contenga `(W-ALT001)`.

**Esperado:** saber qué protege el `pull --case <cid>` cuando tiene que crear el caso. **Observado:** para un caso existente y con metadato, un mutex externo protege correctamente la llamada en modo libre; no hay una segunda adquisición ni una unión realizada por `ensure_case`. Para el alta, el helper no dispone de identidad y el CLI tampoco aporta una. La política general de «sin W-code avisa y sigue» permite continuar, pero entonces esta ruta queda sin protección y no debe describirse como cerrada por mover el `with` delante.

**Cambio necesario:** declarar el alta por estos comandos como excepción sin identidad, si esa es la decisión, o definir una fuente explícita de identidad anterior a cualquier escritura y su paso al alta. Cambiar únicamente a `modo="v1"` no sirve: sin `id_go` falla. No se propone inferirlo silenciosamente del nombre. E3 vigente prueba otro contrato: `modo="v1", id_go=W` (`tests/test_entrypoints_mutex.py:139`).

### H-03 — ALTO — Falta resolver `--ref` antes de entrar en un helper que solo acepta `case_id`

**Diseño:** §3.1, firma de `sostener(case_id)` y traslado de `w_code_de`; §3.2, rama `atomize_emails --ref`.

**Fuente:** `scripts/migrar_layout_intake.py:161` usa `caso_path(case_id)`, que busca nombres de directorio, no referencias (`core/casos/case_locator.py:43`). Por el contrario, el motor de atomización sí aplica `resolve_ref` en `core/email_atomize/pipeline.py:433` y `:438`. El CLI actual entrega `args.ref` directamente al motor (`scripts/atomize_emails.py:26`).

**Reproducción:** con carpeta `Caso sintetico (W-PROBE1)` y `meta.id_go=W-PROBE1`, `_w_code_de(CID)` devuelve `W-PROBE1`, pero `_w_code_de("W-PROBE1")` devuelve `None`. `resolve_ref("W-PROBE1")` devuelve correctamente `CID`.

**Esperado:** `atomize_emails --ref W-PROBE1` bloquea si el caso está ocupado. **Observado:** si el nuevo envoltorio recibe el argumento que hoy recibe el motor, cae en «sin W-code» y el motor resuelve después el caso real y escribe. El diseño prescribe resolución previa para export, pero no para atomize; el traslado literal del helper no la añade.

**Cambio necesario:** establecer quién normaliza la referencia y hacerlo antes de consultar `_caso.md`; usar esa identidad resuelta durante la operación. E8 debe montar una carpeta cuyo nombre sea distinto de W, como ya hace `monta_caso`, para que el fallo no se oculte. Es un defecto de especificación del cableado, no una afirmación de haber probado el futuro helper.

### H-04 — ALTO — `--src/--out` no significa «sin caso»

**Diseño:** §3.2 y E11, exclusión de esta rama porque «sin caso: no hay qué sostener».

**Fuente:** el propio argumento `--src` anuncia una ruta a `00_Input/03_Email` (`scripts/atomize_emails.py:20`). Las líneas 28–30 pasan rutas libres a `P.atomize_dir`; las 54–55 también permiten sellar. El motor presupone el layout de un caso al derivar `case_dir = out.parent.parent` (`core/email_atomize/pipeline.py:110`). Crea la salida en `:130`, publica documentos en `:165`, poda con `unlink` en `:220` y guarda el registro en `:272`. El sello crea y copia en `core/email_atomize/entregas.py:46`.

**Reproducción:** con un mutex ajeno vigente, ejecutar `main(["--src", <caso>/00_Input/03_Email, "--out", <caso>/01_Procesado/Emails, "--entrega", "sonda"])` devuelve 0 y genera mensajes, corpus, `_registro.json` y una entrega con `_SELLO.md`. Está registrado en `sondas_resultado.json`.

**Esperado:** la regla de §2 cubre un escritor bajo el árbol de un caso identificable. **Observado:** la sintaxis alternativa permite escribir exactamente en ese árbol; añadir un aviso no proporciona exclusión. No he medido qué porcentaje de usos reales emplea estas rutas, pero el layout está expresamente documentado y el contraejemplo es ejecutable.

**Cambio necesario:** distinguir rutas realmente externas de destinos pertenecientes a casos; proteger o rechazar estos últimos, o declarar de forma inequívoca esta excepción a la garantía y su deuda. Si solo `--src` está dentro del caso y toda la salida está fuera, la lectura del origen no equivale a una escritura en él: el hallazgo se apoya en el destino y el sellado dentro del caso.

### H-05 — MEDIO — La pérdida del mutex tiene traducción, pero no una política completa de ejecución

**Diseño:** §3.1 (`MutexPerdidoEnCli`), §3.2 (`sync_all`) y E12–E13.

**Fuente:** `core/casos/case_mutex.py:505` declara literalmente «No se preempta codigo Python arbitrario a mitad». El latido solo marca la pérdida (`:610`); la salida puede lanzar `MutexPerdido` (`:655`). `mutex_sesion.sostenido` cede el control en `core/casos/mutex_sesion.py:161` y limpia el mapa en `:190`. Los motores revisados no consultan la sesión antes de cada escritura. El bucle actual de `sync_all` solo captura errores de Sudespacho (`scripts/sync_sudespacho.py:354`); no contiene política para el nuevo error de pérdida.

**Reproducción:** dentro de `sostenido`, `session.marcar_perdido()` no impide una escritura posterior; la excepción llega al salir y el mapa queda vacío. La sonda comprueba el límite de la primitiva, sin simular una caducidad real ni un robo del lease.

**Esperado:** decidir si una pérdida aborta el barrido, cómo se informa y cuándo se deja de invocar motores. **Observado:** el diseño especifica saltar un `CasoOcupado`, pero no el destino ni el código de salida de `MutexPerdidoEnCli`. Si el `with` engloba todos los expedientes de un caso y no hay comprobaciones, el cuerpo puede continuar con expedientes posteriores de ese mismo caso hasta abandonar el bloque. Si la pérdida sí se propaga, las capturas actuales no la manejan: aborta con excepción sin el cierre de CLI prometido.

**Cambio necesario:** fijar una política explícita para pérdida, probarla en todos los CLI y en el barrido, y precisar que sostener el contexto no aporta cancelación instantánea ni rollback. Si se conserva el alcance sin tocar motores, declarar ese límite. Además, copiar literalmente el texto de `sala_maquina` remite a `_cobertura.md` (`scripts/sala_maquina.py:574`), que estos motores no generan; el aviso debe señalar los artefactos pertinentes.

### H-06 — MEDIO — Ampliar solo el `parametrize` de E4 hace fallar a los llamadores correctos

**Diseño:** §4, «E4 (ampliado)» con helper, migración y los tres nuevos módulos.

**Fuente:** `tests/test_entrypoints_mutex.py:168` solo examina llamadas cuyo nombre sea `sostenido`; la línea 175 exige que haya alguna y la 176 valida `now_iso_utc`. Los nuevos llamadores ejecutarían `sostener`, sin pasar reloj, porque lo decide el helper.

**Reproducción:** pasar a E4 un módulo mínimo con `with sostener("caso", avisar=print)` produce `AssertionError: ... no llama a sostenido(...): el entrypoint no adquiere nada`.

**Esperado:** el guard acepta delegación correcta y mata el mutante `now_iso`. **Observado:** el test actual no sigue imports ni llamadas y rechaza esa delegación. También fallará para migración después de retirar su adquisición directa.

**Cambio necesario:** verificar el reloj en los adquirentes reales (`abrir_caso`, `sala_maquina`, `_mutex_cli`) y verificar por separado el uso y la duración del helper en sus llamadores. No debilitar el assert hasta volverlo vacuo. E5 no impide el helper en `scripts/`.

### H-07 — MEDIO — Los espías propuestos no cubren todas las fronteras que dicen cerrar

**Diseño:** §4, E7–E12 y mutantes por cada uno de los cinco comandos/rutas.

**Fuente:** `_instantanea` solo almacena tamaños de ficheros (`tests/test_entrypoints_mutex.py:55`); ignora directorios y contenido de igual longitud. Hay una reserva antes del motor de export (`scripts/export_label_emails.py:64`) y un sello después del motor de atomización (`scripts/atomize_emails.py:55`). `intake_judicial` tiene llamadas propias a `ensure_case` y `register_expediente` (`scripts/sync_sudespacho.py:247` y `:252`).

**Reproducción:** cambiar un fichero de `aa` a `bb` y crear un directorio vacío conserva exactamente `_instantanea`, aunque una instantánea con hashes y directorios sí cambia. La reserva de H-01 puede pasar inadvertida reutilizando ese helper para E7 con un caso disponible.

**Esperado:** cero escrituras antes de adquirir y mutex durante toda escritura, con un mutante por ruta. **Observado:** E7–E10 no incluyen una prueba de ocupado específica para `intake_judicial`; quitar solo su bloque no tiene por qué ponerlos en rojo. E12 comprueba la sesión en el espía del motor, pero eso no prueba que también abarque la reserva, el registro o `sellar_entrega`. Quitar el bloqueo solo del sello podría pasar. E9 con `ensure_case` sustituido demuestra «no llamado», no bytes realmente creados por ese motor.

**Cambio necesario:** instantánea de nombres, directorios y contenido; pruebas específicas de ocupado y sesión vigente en reserva, alta/registro y sellado; caso con más de un expediente para el barrido; comprobación de liberación tras éxito, ocupado y excepción. Los dobles son apropiados para aislar red, pero debe distinguirse qué demuestra cada aserción.

### H-08 — MEDIO — E13 es viable en Windows, pero faltan el mecanismo de inyección y una barrera

**Diseño:** §4, dos procesos con motor que duerme dos segundos «inyectado por variable de entorno de test».

**Fuente:** `scripts/atomize_emails.py:17` acepta `main(argv)` y `:61` convierte el retorno en salida de proceso; no hay lectura de una variable de test ni motor configurable por entorno en ese script o `core/email_atomize/pipeline.py`. `core/config.py:31` fija `CASOS_ROOT` al importar. El aislamiento adicional de locks está en `tests/conftest.py:179`; no se deriva de `CASOS_ROOT`. `CliRunner` se usa para las apps Typer, mientras atomize y export usan `argparse`.

**Reproducción:** un arnés externo de sonda en Windows lanza dos procesos reales, envuelve el CLI actual con `_bajo_mutex` existente y comunica `READY` después de adquirir; mantiene al primero dentro hasta que termina el segundo. Resultados 0 y 2, con `CASOS_ROOT` y registro de locks sintéticos compartidos. Es evidencia de viabilidad del arnés, NO una ejecución del futuro E13 ni del helper nuevo.

**Esperado:** contención real y resultado determinista. **Observado:** con solo dos segundos de sueño, un arranque lento permite que el segundo entre después de liberar y ambos terminen 0 legítimamente. Una variable de entorno por sí sola no instala un monkeypatch en un intérprete nuevo de Windows. Un motor sustituido que solo duerme tampoco prueba integridad de publicación.

**Cambio necesario:** precisar un bootstrap de test en cada hijo, sin asumir herencia de mocks; señal de mutex adquirido, retención hasta observar el rechazo del otro, timeouts y limpieza en `finally`; mismo registro de locks y misma raíz de casos, fuera del árbol de la copia; `cwd`/ruta de importación explícitos, `sys.executable`, argumentos como lista y decodificación UTF-8. Usar datos sintéticos con salida esperada y comprobar que el perdedor no escribe. El hook debe quedar definido en el alcance; no se necesita una puerta de test en producción si el bootstrap externo puede hacer la inyección. Probar pérdida/caída requiere otro escenario y no queda cubierto por la contención de E13.

### H-09 — MEDIO — La tabla «medida» no describe todos los escritores y atribuye una traza inexistente

**Diseño:** §1, tabla de destinos, y §§3.3/5, inmovilidad de motores y cobertura excluida.

**Fuente y contraste:**

| Flujo | Lo que falta o sobra en la tabla | Fuente |
|---|---|---|
| Export | También escribe `00_Input/_resolved_links.json`, el albarán `_manifiesto.yaml` del lote y `01_Procesado/Emails/INDICE.md` y `CRONOLOGIA.md`; puede usar bandeja | `core/email_export.py:1075`, `:1096`, `:1099`, `:1372`, `:1382`, `:1418`; `core/intake_lotes.py:94` |
| Atomize | La ruta `01_Procesado/Emails/` es correcta; contiene registro, mensajes, adjuntos, corpus, revisiones, vistas y, con flag, `_entregas/.../_SELLO.md`. También poda. No hay emisión de `_intake_log.jsonl` en este CLI/motor/sellado | `core/email_atomize/pipeline.py:130`, `:165`, `:220`, `:242`, `:249`, `:263`, `:272`; `core/email_atomize/entregas.py:46`, `:69` |
| Pull e intake judicial | `ensure_case` en modo libre crea estructura fuera de `00_Input` y puede copiar/prerrellenar el informe de viabilidad y, según metadatos persistidos, el cuestionario en `02_Analisis` | `core/case_manager.py:674`, `:683`, `:772`, `:775`, `:782` |
| Pull v2, también desde sync-all/judicial | Escribe `00_Input/_ocurrencias_crm.json`, con temporal y reemplazo, antes de descargar documentos. También puede desviar documentos a bandeja | `core/sync_sudespacho.py:1505`, `:1517`, `:1532`, `:1673`; `core/ocurrencias_crm.py:70`, `:137` |

**Reproducción:** el CLI de atomización con un `.eml` sintético y sello genera derivados y no crea `_intake_log.jsonl`. Un `pull_expediente_v2` con cliente doble que devuelve cero documentos crea `_ocurrencias_crm.json` y `_intake_log.jsonl`, y actualiza el índice existente. No se usó el CRM real. La copia de plantillas se constató en código; no se atribuye a la sonda haber encontrado/copiado todas las plantillas posibles.

**Esperado:** un mapa de escrituras fiable para fijar el bloque y sus comprobaciones. **Observado:** la tabla omite destinos relevantes y mezcla la traza de la sala de máquina con la del CLI fino: quien emite `atomizado_email` es `scripts/sala_maquina.py:43`, no `scripts/atomize_emails.py`.

**Cambio necesario:** corregir el inventario y separar las variantes de sync. Añadir el mutex no crea automáticamente esa traza ni hace que todos los motores del core «exijan» sesión: E5 prohíbe adquirir en core, no comprueba una exigencia universal.

## 4. Respuesta a cada punto del mandato §3

1. **Primera escritura.** Export: el bloque debe empezar antes de `email_dest_dir`; hay `mkdir` y, según estado, log antes del motor (H-01). `resolve_ref` es lectura en la ruta examinada. Atomize: envolver `atomize_case` antes de entrar protege su primera escritura, `IDS.load_registro(out)`; `emails_out_dir` solo localiza/compone una ruta. El bloque debe mantenerse hasta terminar el sello y conservar la salida temprana `publicado=False`, que impide sellar (`scripts/atomize_emails.py:35`). Pull/judicial: colocar el mutex antes de `ensure_case` es suficientemente temprano para las escrituras rastreadas; incluye alta, registro y motor. Sync-all: listar casos y leer `_caso.md` antes del bloque no escribe; envolver todos los `pull_expediente_v2` del caso incluye ocurrencias, M9, estado y log. No debe empezar después de la primera llamada del bucle.

2. **Reentrancia y alta.** Un CLI con mutex externo puede ejecutar `ensure_case` en modo libre sin autobloquearse; comprobado. El modo libre no exige ni se une. E3 prueba exigencia v1 con identidad explícita. Para un alta por `--case`, el lector de `_caso.md` devuelve `None` y se continúa sin protección si se conserva el fallback. El nombre con W-code no remedia la falta de `meta.id_go` ni lo rellena automáticamente. Véanse H-02/H-03.

3. **Sync-all por caso.** `case_manager.list_cases` devuelve nombres (`core/case_manager.py:994`), y `caso_path` busca esos nombres tanto planos como por ciudad (`core/casos/case_locator.py:43`); el helper heredado puede leer la identidad de cada caso existente. No hay un fallo demostrado de resolución en ese flujo normal. Si la adquisición falla por `CaseBusy`, `gestor.__enter__()` falla antes de insertar en `_SESIONES` (`core/casos/mutex_sesion.py:155`); se comprobó mapa vacío. Capturar `CasoOcupado` fuera del contexto de cada caso permite saltarlo limpio. En pérdida, el `finally` elimina la sesión al terminar el último préstamo, pero falta decidir el curso del barrido y la salida de CLI (H-05). No se ejecutó el `sync_all` futuro.

4. **Rutas sin referencia.** No equivalen a ausencia de caso. Se reprodujo escritura y sello bajo un caso ocupado (H-04). No se midió frecuencia de uso. El origen dentro del caso, por sí solo, no es una escritura; el destino dentro sí lo es.

5. **Helper, E5, E4 e importación.** `scripts/_mutex_cli.py` no rompe E5, que recorre solo `core/` (`tests/test_entrypoints_mutex.py:194`). Debe usar `mutex_sesion.sostenido`, no la primitiva: el guard global prohíbe `tomado/adquirir` en producción fuera de sus capas (`tests/test_escritura_censo.py:272`). E4 no se puede ampliar solo por parametrización (H-06). El guion bajo inicial es válido en un módulo Python: `from scripts._mutex_cli import sostener` o el import relativo correspondiente funciona con `python -m scripts.x`, con la raíz del proyecto importable. No se ejecutó ese import concreto porque el fichero no existe. No debe confundirse con `import _mutex_cli` como módulo de nivel superior.

6. **Censo y techo 88.** Medición real: 88, con los guards pasando. Reubicar adquisición, añadir `with`, avisos por consola y resúmenes en memoria no añade por sí mismo escrituras documentales fuera de la costura. Las escrituras de lock ya están implementadas en las primitivas. No hay base para exigir subir el techo. Sin embargo, `PRODUCTORES` es una lista explícita (`tests/test_escritura_censo.py:26`) que no incluye los tres CLI ni el futuro helper: un 88 verde no descubriría un log nuevo allí. Conviene declarar que `bloqueados_por_mutex` es memoria/salida y que no se introduce una nueva escritura de protocolo; si se añade, debe censarse y justificarse. Tampoco debe añadirse una traza a atomize solo para hacer verdadera la tabla sin reconocer ese cambio de alcance.

7. **E7–E13.** E7/E8 son montables invocando `main([...])` y capturando stdout/stderr; deben aportar todos los argumentos obligatorios de export. E9/E10 deben usar `CliRunner.invoke(app, ...)`; los nombres reales expuestos por Typer son `pull`, `intake-judicial` y `sync-all`, comprobados con `--help`. E11 es ejecutable pero, tal como está, fija el bypass de H-04. E12 necesita más puntos de observación que la llamada al motor. La ampliación literal de E4 falla. E13 es viable con un arnés de procesos y aislamiento previo al import, pero no con la mera presuposición de un mock heredado o dos segundos de solapamiento (H-08). Faltan ocupado en judicial, alta nueva, reserva/sello, pérdida y limpieza; véase H-07. La primitiva adquirida en el mismo test simula un titular ajeno al mapa de sesiones, como explica E1; eso no sustituye a la prueba interproceso.

8. **UI.** Queda una vía real sin mutex: `streamlit_app.py:782` reserva el destino y `:785` invoca directamente `export_label`. También registra expediente en `:1071` y llama a `_intake_judicial` en `:1076`, que llega a `pull_expediente_v2` (`core/judicial_intake.py:162`/`:179`). La búsqueda no encontró llamadas directas a `atomize_case` ni `pull_expediente_v2` en `streamlit_app.py`, ni adquisición de mutex allí: no deben atribuirse esas llamadas directas al fichero. §§3.3 y 5 sí excluyen y declaran la UI, correctamente. Lo que debe acotarse es la frase de §1 «cierra ese hueco por el otro lado»: desde la UI el export todavía puede competir con migración. No se midió si la UI se usa tanto como los CLI, ni se propone incluirla en el cambio por decisión del revisor.

9. **Tabla medida.** No es exacta: faltan índices derivados y estado de enlaces del export, ocurrencias del CRM, bandejas y efectos de `ensure_case`; sobra la atribución del log al CLI de atomización. Detalle y fuentes en H-09. M9 es `_intake_hashes.json`, no un segundo fichero distinto con ese nombre; sus escrituras transitorias y reemplazos están en `core/intake_manifest.py:181`.

## 5. Qué ejecuté

- Inspección inicial de nombres con `Get-ChildItem -Force`; hashes del objeto con `Get-FileHash -Algorithm SHA256`; lecturas numeradas y búsquedas en la fuente. `rg` no está instalado: el intento falló y se usó `Select-String`. No se consultó Internet.
- Copia de `../head` a `./scratch_head`; no se importó ni ejecutó Python desde `head/`.
- Desde `scratch_head`, con `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1` y `PYTHONIOENCODING=utf-8`:

```text
C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest -q -p no:cacheprovider --basetemp=../pytest_base tests/test_entrypoints_mutex.py tests/test_escritura_censo.py
```

Resultado: **17 tests pasaron, código 0**. El `basetemp` relativo queda dentro del workdir de revisión y fuera de la copia del árbol.

- `python ../sondas.py`: código 0; comprueba resolución, reserva bajo ocupación, salida por rutas con sello, alta libre y sesión externa, pérdida marcada, límite de E4 y de la instantánea, censo 88 y contención real entre dos procesos mediante wrapper de sonda sobre el helper existente. Evidencia: `./sondas.py` y `./sondas_resultado.json`.
- `python ../sondas_extra.py`: código 0; reserva en caso prestado con log, pull con cliente doble vacío, alta bajo el helper heredado sin identidad y ayuda del CLI Typer en subprocess. Evidencia: `./sondas_extra.py` y `./sondas_extra_resultado.json`.
- Las sondas son del revisor y solo usan datos sintéticos. No son tests incorporados a la fuente ni una implementación de `_mutex_cli`.

## 6. Sin verificar y límites

- No existe implementación del diseño: no se ejecutaron E7–E13 futuros ni sus mutantes. Las reproducciones prueban propiedades del código existente y contraejemplos al contrato propuesto.
- No se ejecutó la suite completa, OCR, descargas reales de Gmail/CRM, UI de Streamlit, sincronización entre máquinas ni concurrencia con datos del despacho. No se verificaron las cifras históricas de OCR, las cuatro rondas/17 mutantes citados ni la frecuencia real de uso de cada vía.
- La pérdida se inyectó mediante `marcar_perdido`, no causando fallos reales de red, reloj o latido. Se probó la limpieza del mapa de la primitiva/capa existente y la contención interproceso del arnés; no se probó la futura traducción de excepciones ni una publicación transaccional que el diseño tampoco implementa.
- El resultado 0/2 de los dos procesos corresponde al wrapper externo con el helper de migración existente. No certifica el nuevo cableado de atomize. No se hizo una campaña estadística de flakiness.
- El hash de cierre certifica el objeto revisado. No se tomó un manifiesto de hashes de todo `head/` al abrir: la ausencia de cambios en el resto se sustenta en las operaciones realizadas, todas de lectura sobre esa ruta, no en un digest agregado.
- No se evalúa `crm_ficha.py`, reservado a otra sesión. Las exclusiones expresas UI y entre máquinas se respetan; se señalan para evitar atribuir cierre global al alcance CLI.
- El veredicto es la conclusión de esta revisión del diseño; la adjudicación corresponde a Claude contra la fuente.

## 7. Huella de cierre

SHA-256 del objeto al cerrar, recalculado sobre `../head/docs/superpowers/specs/2026-09-05-mutex-en-los-entrypoints-de-intake-design.md`:

`fe8caf47f9a69b2ba7512c7b3a611672bd942f3c7a8984ab7d174d29da3883e9`

Coincide con la huella de apertura.

REQUIERE-REVISION

<!-- informe-literal:fin:q8zn -->

## 2. Evidencia verificada por mí al adjudicar

Los nueve se confirman. Dos los había medido yo antes de recibir el informe, leyendo la fuente
para preparar la implementación:

- **H-01.** `core/email_export.py:1423-1433`: `email_dest_dir` devuelve `reservar_lote(...)`, y
  `core/intake_lotes.py:96` hace `destino.mkdir(...)`; `scripts/export_label_emails.py:64` la
  llama **antes** de `export_label`. La rev. 1 ponía el bloque «alrededor de `export_label`»: el
  `mkdir` quedaba fuera. Y `case_manager.dir_intake` (`:1234`) pasa por `guard_escritura`, que
  registra el desvío a bandeja: en caso prestado hay además bytes de protocolo antes del mutex.
- **H-02.** `core/case_manager.py:479` (`modo="libre"` por defecto) y `:528-545` (solo `v1`
  consulta `vigente` y exige `id_go` explícito, rechazando derivarlo del nombre). `pull` llama a
  `ensure_case` sin `modo` ni `id_go` (`scripts/sync_sudespacho.py:160`). Un caso que no existe no
  tiene `_caso.md`: el helper devuelve `None`. Confirmado; la rev. 2 lo declara excepción.
- **H-03.** `scripts/migrar_layout_intake.py:161` usa `caso_path(case_id)`, que busca nombres de
  carpeta; `resolve_ref` (`core/casos/case_locator.py:226`) es quien resuelve un W-code. Un
  `--ref W-…` habría dado `None` → «avisa y sigue».
- **H-04.** `core/email_atomize/pipeline.py:110`: `case_dir = out.parent.parent`, el motor asume
  el layout del caso; el `--help` del CLI documenta `--src` como `00_Input/03_Email`. La rev. 1
  llamaba a esa rama «sin caso».
- **H-05.** `core/casos/case_mutex.py:505` («No se preempta codigo Python arbitrario a mitad»);
  `scripts/sala_maquina.py:574` cita `_cobertura.md`, que estos motores no escriben.
- **H-06.** `tests/test_entrypoints_mutex.py:168`: `if nombre != "sostenido": continue` — un
  delegante que llame a `sostener` no aparece y la aserción de la línea 175 lo pone rojo.
- **H-07.** `tests/test_entrypoints_mutex.py:55`: `_instantanea` guarda `st_size` por fichero:
  ciega a directorios nuevos y a contenido de igual longitud.
- **H-08.** `scripts/atomize_emails.py` no lee ninguna variable de test; un hijo `subprocess` no
  hereda monkeypatches. Confirmado por lectura.
- **H-09.** `core/email_atomize/pipeline.py:44-51`: `atomizado_email` lo emite el encadenado desde
  `scripts/sala_maquina.py:43`, no el CLI fino; `core/sync_sudespacho.py:1505` escribe
  `_ocurrencias_crm.json` en el pull; `core/email_export.py:1372-1418` escribe los índices de
  `01_Procesado/Emails`. La tabla de la rev. 1 no los tenía.

**Cobertura:** la rev. 2 **no se ha vuelto a revisar**; la R2 irá sobre el diff que la implemente,
y es donde el helper —que aún no existe— se verifica.
