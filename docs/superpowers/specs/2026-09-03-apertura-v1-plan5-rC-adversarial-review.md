---
tipo: revision-adversarial
objeto: "diff REMEDIADO del Plan 5: el cableado de la secuencia de V1"
objeto_rev: "rama claude/expediente-apertura-orquestado-cd68c3, commit 80edd24"
commit: 80edd24
ronda: "C"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: k9tz
sha256_informe: 932c77af0d8fd040dccd86042b827211471676931f95033fdea4e993bc058bf6
adjudicado_en: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md §7
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revision adversarial R-C.** El §1 conserva la voz del revisor sin una coma
> cambiada; la **adjudicacion** vive en el **§7 del plan**. Es la ronda del **diff
> REMEDIADO**: el objeto es `80edd24`, no el `5cdf7da` que vio R-B.
>
> **TERCERA ronda sobre la misma pieza, autorizada expresamente por Nikolai el 2026-09-03**
> («codex tiene cupo, relanzalo»). El techo duro del presupuesto la prohibe sin esa
> autorizacion, y aqui consta.
>
> **La independencia queda RESTABLECIDA:** el revisor es **Codex**, no el sustituto de R-B.
> Sondeado antes de montar el objeto con un `exec` de una linea —leccion de esta misma
> sesion, en la que Codex murio a mitad de R-B tras quemar ~153.000 tokens sin dejar
> informe—.
>
> Veredicto `NO-SHIP`: **7 hallazgos** — 2 CRITICOS, 2 ALTOS, 3 MEDIOS. Adjudicados:
> **7 confirmados, 0 refutados.**
>
> **El hallazgo que justifica la ronda entera:** HC-02 es un defecto **INTRODUCIDO POR LA
> REMEDIACION** de R-B. Al sacar la publicacion del bloque de mutex para no afirmar un
> exito que la perdida del lease desmiente, se abrio una ventana **sin exclusion ninguna**:
> el revisor midio la intercalacion `R1 abre / R1 libera / R2 abre / R1 cierra`, que deja
> el fichero con la ronda R1 y **borra la evidencia de que R2 sigue en curso**. Y el
> comentario que el autor habia escrito cuatro lineas encima decia, correctamente, que
> «escribir sin mutex es la violacion que el mutex existe para impedir».
>
> **Esta ronda EJECUTO:** 105 pruebas contractuales, los 31 mutantes enumerados, y
> **mutantes propios** —uno de intercalacion de rondas que sobrevivio— mas sondas que
> forzaron un `OSError` en el evento forense y una perdida de lease diferida.
>
> **Prueba de no mutacion:** el objeto (`DIFF.patch`) conservo el `sha256`
> `dfde85d4a7bf5c930a36bde497b1ea4f6703b8bbfc1284f841b9b4bda7057ca3` al abrir y al cerrar.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:k9tz -->

NO-SHIP

Se formulan 7 hallazgos: 2 críticos, 2 altos y 3 medios. Pesan decisivamente que una pérdida del lease no detiene las publicaciones y que la remediación trasladó el cierre después de liberar el mutex, donde una ronda tardía puede borrar la evidencia de la siguiente. También puede quedar un estado terminal sin evento forense, y la contaminación cruzada detectada continúa como `ok`. Las 105 pruebas contractuales y los 31 mutantes enumerados pasan, pero un mutante propio de intercalación sobrevivió y el arnés omite tres ids originales del §3. La suite completa tuvo tres fallos ambientales reproducidos idénticamente en `base/`; el orden aleatorio, la corrida viva y las deudas declaradas quedaron SIN VERIFICAR.

---

# Revisión adversarial R-C — Plan 5 de apertura V1

## 1. Objeto y evidencia

Objeto revisado: árbol `../head/` en el commit declarado `80edd24`, contrastado con
`../base/` (`origin/main`) y con `DIFF.patch` (23 ficheros, +2294/−48 según el mandato).
No se reclamó historia Git: ninguna copia contiene `.git`.

- SHA-256 de apertura de `DIFF.patch`:
  `dfde85d4a7bf5c930a36bde497b1ea4f6703b8bbfc1284f841b9b4bda7057ca3`.
- SHA-256 de cierre de `DIFF.patch`:
  `dfde85d4a7bf5c930a36bde497b1ea4f6703b8bbfc1284f841b9b4bda7057ca3`.
- Se leyeron `head/CLAUDE.md`, `head/AGENTS.md`, las restricciones globales, §3 y la
  Task 8b del plan; §§11–14, 21 y 24 de la spec; el diff; el código real afectado y sus
  productores, consumidores y tests; y los homólogos pertinentes de `base/`.
- No se leyeron §5 ni §6 del plan ni ficheros cuyo nombre contiene
  `adversarial-review`.
- `head/` y `base/` se mantuvieron en solo lectura. Toda ejecución se hizo sobre copias
  desechables bajo el workdir, con `PYTHONDONTWRITEBYTECODE=1`, sin cacheprovider y con
  `--basetemp` corto y relativo fuera del árbol copiado.

Comandos ejecutados y salida literal relevante (se abrevia únicamente la lista repetitiva
de nodeids o puntos):

```text
Get-FileHash .\DIFF.patch -Algorithm SHA256
OPEN_SHA256=dfde85d4a7bf5c930a36bde497b1ea4f6703b8bbfc1284f841b9b4bda7057ca3
```

La primera ejecución puso por error el basetemp dentro de la copia. La verja del propio
proyecto la rechazó; no se usó como evidencia contra el diff:

```text
python -m pytest ... -p no:cacheprovider --basetemp=bt
5 failed
<Result WorkspaceUnderCatalogRoot('[WORKSPACE_UNDER_CATALOG_ROOT]')>
EXIT=1
```

Corregida una sola variable (`--basetemp=../../bt`), la suite contractual quedó verde:

```text
python -m pytest -q --tb=short -p no:cacheprovider --basetemp=../../bt \
  tests/test_apertura_v1_secuenciador.py tests/test_apertura_v1_etapas.py \
  tests/test_apertura_v1_cableado.py tests/test_apertura_v1_estado.py \
  tests/test_apertura_v1_e2e.py tests/test_apertura_v1_costuras.py \
  tests/test_apertura_v1_control_files.py tests/test_abrir_caso_modo_v1.py
........................................................................ [ 68%]
.................................                                        [100%]
EXIT=0

python -m pytest --collect-only <los ocho ficheros anteriores>
105 tests collected in 1.26s
EXIT=0
```

El arnés oficial se ejecutó completo, no solo se inspeccionó:

```text
PYTEST_ADDOPTS=--basetemp=../../mb python -m tests._mutantes_plan5
F1: MUERTO por su frontera (2 rojo/s)
...
F34-control-registro: MUERTO por su frontera (2 rojo/s)
F28: MUERTO por su frontera (1 rojo/s)

31/31 mutantes muertos, cada uno SOLO por su frontera.
EXIT=0
```

Se introdujo en la copia un mutante R-C que, entre la salida del mutex y
`estado_v1.cerrar`, abría una segunda ronda. Los mismos 105 tests siguieron verdes:

```text
python -m pytest <los ocho ficheros contractuales> --basetemp=../../rcm
........................................................................ [ 68%]
.................................                                        [100%]
EXIT=0
```

La intercalación se reprodujo además directamente contra el estado durable:

```text
R1_abre -> R2_abre -> R1_cierra
FINAL ronda_id=R1 terminada=t3 estado=preparado_con_pendientes
R2_PERDIDA=True
```

Dos sondas propias midieron el momento de las escrituras:

```text
tests/test_rc_probe.py::test_rc_el_cuerpo_escribe_aunque_la_perdida_solo_aflore_al_salir PASSED
tests/test_rc_probe.py::test_rc_el_cierre_durable_ocurre_con_el_contexto_ya_liberado PASSED
2 passed in 0.76s
EXIT=0

tests/test_rc_probe2.py::test_rc_fallo_del_evento_deja_estado_cerrado_sin_evento PASSED
1 passed in 0.75s
EXIT=0
```

La suite completa se recogió y ejecutó:

```text
python -m pytest --collect-only -p no:cacheprovider
3880 tests collected in 15.68s
EXIT=0

python -m pytest -q --tb=short -p no:cacheprovider --basetemp=../../full_bt
3 failed, 77 skipped, 10 xfailed
EXIT=1
```

Los tres rojos fueron el wrapper `expedientes_xl` sin intérprete y dos tests de
`session_close` que exigen que exista el venv dentro del repo. Se repitieron sobre una
copia de `base/` y dieron literalmente `FFF [100%]`, los mismos tres nodeids y `EXIT=1`.
Por tanto son limitaciones de las copias entregadas (sin `.venv`) y del `PATH` vaciado por
el test, no regresiones del diff.

Quedó **SIN VERIFICAR** el orden aleatorio: el intérprete no tiene `pytest-randomly` (la
sesión enumeró solo `anyio`, `Faker` y `cov`). También quedan sin verificar la corrida real
sobre un expediente vivo y las diez deudas que el mandato declara abiertas; no se
reciclan aquí como hallazgos.

## 2. Hallazgos

### HC-01 — CRÍTICO — la pérdida del lease no detiene las escrituras del cuerpo

**Qué es.** `main` no conserva la `SesionMutex` que cede el contexto ni consulta
`perdido()`/`revalidar()` antes de publicar; la renovación puede marcar la sesión perdida
y Drive, CRM u OCR continúan escribiendo hasta que la pérdida aflora al salir.

**Dónde.** `scripts/abrir_caso.py:934-963`; `core/casos/case_mutex.py:600-617,655-660`;
`core/casos/case_mutex.py:509-513`.

**Por qué importa.** Si falla la renovación o cambia el nonce durante una etapa larga, el
lease puede vencer y otro proceso entrar. El primero sigue mutando el mismo expediente y
solo después informa `bloqueado`: ya hubo dos escritores, con riesgo de manifiestos,
derivados y logs incoherentes. La sonda con pérdida diferida dejó material escrito y salió
1. El test vigente de F26 solo hace que el contexto lance antes de `yield`
(`tests/test_abrir_caso_modo_v1.py:331-338`), por lo que no cubre este camino.

**Cómo se comprobó.** Leído y ejecutado; sonda R-C reproducible, verde porque acredita el
comportamiento defectuoso.

**Qué hace falta.** Publicación a staging y commit solo tras revalidar titularidad, o una
primitiva que haga indivisible «revalidar → publicar → liberar». Añadir una prueba con
pérdida después de `yield` y un segundo titular real; la expectativa debe ser cero
publicaciones posteriores a la pérdida.

### HC-02 — CRÍTICO — el cierre fuera del mutex puede borrar la ronda siguiente

**INTRODUCIDO POR LA REMEDIACIÓN.** Al sacar `estado_v1.cerrar` y el evento del bloque, se
cerró el ejemplo «no escribir si `__exit__` denuncia pérdida», pero se abrió una ventana
después de liberar el lock. Una segunda ejecución puede adquirirlo y abrir R2; el cierre
tardío de R1 reemplaza después `_apertura_v1.json` sin CAS.

**Dónde.** `scripts/abrir_caso.py:993-1007`; `core/apertura_v1_estado.py:99-111`.

**Por qué importa.** La secuencia medida `R1 abre → R1 libera → R2 abre → R1 cierra` acaba
con `ronda_id=R1` y `R2_PERDIDA=True`. Se pierde precisamente la evidencia de que R2 sigue
en curso; una tercera ejecución ve una ronda cerrada y no avisa. El mutante que insertó
esa intercalación sobrevivió a los 105 tests contractuales.

**Cómo se comprobó.** Leído, mutado y ejecutado; no es una inferencia de diff.

**Qué hace falta.** Un cierre condicionado al `ronda_id` actualmente persistido (CAS) y
una relación indivisible con la liberación, más un test de dos rondas intercaladas. Mover
sin más el `typer.Exit` no basta: el punto seguro debe publicar antes de ceder exclusión y
salir del proceso después.

### HC-03 — ALTO — puede quedar estado «cerrado» sin evento forense de cierre

**Qué es.** La finalización hace primero `estado_v1.cerrar` y después
`registrar_cierre_v1`; si el append del log falla, el JSON ya afirma que la ronda terminó,
pero no existe `apertura_v1_terminada` y la siguiente ejecución no detecta nada pendiente.

**Dónde.** `scripts/abrir_caso.py:1002-1008`; `scripts/abrir_caso.py:538-552`.

**Por qué importa.** Un disco lleno, ACL o error de append deja dos fuentes de verdad en
desacuerdo. La sonda forzó `OSError` en el evento y obtuvo salida 1, JSON con
`terminada != None` y `estado=preparado_con_pendientes`, y ausencia total del JSONL. Se
pierde trazabilidad forense sin el aviso que sí existe para una ronda abierta.

**Cómo se comprobó.** Ejecutado con `test_rc_fallo_del_evento_deja_estado_cerrado_sin_evento`.

**Qué hace falta.** Definir una única fuente autoritativa o un protocolo durable en dos
fases que reconcilie el segundo efecto. Un fallo del evento no puede dejar terminal el
estado sin una marca reintentable.

### HC-04 — ALTO — la contaminación cruzada detectada no bloquea V1

**Qué es.** La atomización guarda una posible contaminación en `report.notas`, pero el
status solo mira `publicado` y `errores`; con notas y cero errores devuelve `ok`, continúa
el OCR y V1 declara la etapa hecha sin pendiente.

**Dónde.** `scripts/sala_maquina.py:618-643,648`;
`scripts/abrir_caso.py:519-535`; `tests/test_sala_maquina_cableado_atomize.py:239-252`.

**Por qué importa.** Un correo cuyo asunto o adjunto nombra un W-code ajeno produce
«posible contaminación cruzada», pero la secuencia automática no ofrece al operador el
momento de abortar que presupone el comentario: procesa el material y puede mezclar
derivados de dos casos. Contradice el gate bloqueante de la spec
(`docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:802-807`).
El test vigente codifica expresamente `status: "ok"` con la nota ajena y pasó.

**Cómo se comprobó.** Leído y ejecutado el test productor (`1 passed`, `EXIT=0`).

**Qué hace falta.** Un campo estructurado de contaminación en `AtomizeReport` y una
traducción explícita a `fallo/bloqueado` antes del OCR; no decidir por texto de `notas`.

### HC-05 — MEDIO — «el productor clasifica» está cerrado solo para el adaptador V1

**Qué es.** `es_gestor_vacio()` reconoce correctamente el vacío actual del productor,
pero la clasificación sigue siendo un prefijo dentro de `errors` y otros consumidores de
`PullResultV2` no preguntan al productor: unos presentan error real como warning y otros
terminan anunciando éxito.

**Dónde.** `core/sync_sudespacho.py:1321-1345`;
`scripts/sync_sudespacho.py:202-222,365-376`;
`scripts/scheduled_sync.py:192-228,236-239`;
`core/judicial_intake.py:160-186`.

**Por qué importa.** Un fallo de listado o descarga retornado en `errors` no incrementa
`total_errors` en el sync programado, y `sync_all` acaba imprimiendo «Sync completado»;
el vacío confirmado también sigue viajando como error/warning. El mismo sum type implícito
continúa reinterpretándose consumidor por consumidor.

**Cómo se comprobó.** Leído mediante barrido de todos los usos de `PullResultV2` y
`.errors`; para el camino V1 se ejecutaron los casos de vacío, error adicional y legado.

**Qué hace falta.** Incorporar al resultado un discriminante tipado (`ok`,
`vacio_confirmado`, `fallida`, `parcial`, `legacy`) producido una sola vez y migrar todos
sus consumidores. El helper optativo cierra el caso de V1, no la propiedad del repo.

### HC-06 — MEDIO — el 31/31 omite fronteras del §3 y encubre un cambio contractual

**Qué es.** `MUTANTES` salta de F18 a F21 y no contiene F26: faltan F19, F20 y F26 como
fronteras originales. F20 reaparece parcialmente como F33 y F26 tiene tests, pero no sus
mutantes contractuales. Además, el código y el test cambiaron F19 de «hecha con pendiente»
a `fallo` sin cambiar ni adjudicar el §3.

**Dónde.** `tests/_mutantes_plan5.py:176-234,262-278`;
`tests/test_apertura_v1_etapas.py:174-193`;
`scripts/abrir_caso.py:399-416`;
`docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md:191-200`.

**Por qué importa.** «31/31 de la lista» es cierto; «cada frontera del §3» no. En
particular, una descarga CRM parcial hoy bloquea donde la fuente contratada pide continuar
con pendiente. Que bloquear sea quizá más prudente no autoriza al diff a cambiar su propia
fuente: necesita adjudicación.

**Cómo se comprobó.** Arnés ejecutado completo y lista enumerada por id.

**Qué hace falta.** Adjudicar F19 contra la spec, actualizar el contrato si procede y
añadir mutantes identificables para F19, F20 y F26. El resumen debe comparar también el
conjunto esperado de ids, no solo `len(MUTANTES)`.

### HC-07 — MEDIO — el supuesto punto fijo material del E2E es vacuo

**Qué es.** El fixture sustituye enteros `_intake_drive_ev`, `pull_expediente_v2` y
`sala_maquina.apply`; ninguno escribe material. La foto compara entonces el mismo
`_caso.md` inicial y excluye el único fichero que sí cambia, el log.

**Dónde.** `tests/test_apertura_v1_e2e.py:66-98,131-150`.

**Por qué importa.** El test pasa aunque cualquiera de los productores reales regenere o
duplique bytes en la segunda ronda. Los espías demuestran llamadas, no punto fijo material;
por eso tampoco detectó el mutante de la segunda ronda de HC-02.

**Cómo se comprobó.** Leído, ejecutado y sometido al mutante R-C, que sobrevivió.

**Qué hace falta.** Doblar límites más profundos (red/OCR) y dejar que los adaptadores
reales escriban artefactos locales, o hacer que los dobles materialicen una fotografía
estable cuyo cambio en segunda ronda ponga el test rojo. Incluir el estado durable en la
observación del `main` real.

## 3. Las cuatro fronteras, una por una

1. **«El productor clasifica, el adaptador pregunta»: cerrada solo en el ejemplo.** Para
   el adaptador V1, `es_gestor_vacio` reconoce el único aviso de vacío y rechaza vacío más
   cualquier error adicional; los tests contra el productor real pasan. La propiedad de
   repo no está cerrada: los consumidores citados en HC-05 siguen leyendo `.errors` sin
   el discriminante.
2. **«Un fichero de control se declara en todos los registros»: cerrada para el fichero
   actual.** `_apertura_v1.json` está en `INTAKE_CONTROL_FILES`, `MERGE_EXCLUSIONS`, el
   carve-out del plugin y el inventario de sala derivado del canónico; el prefijo temporal
   está también en el registro de prefijos y en merge/plugin. `inventory`,
   `hash_tree_local`, `intake_lotes`, `intake_manual`, `intake_drive` y `email_export`
   consumen el canónico o quedan acotados a cajones donde el control no vive;
   `local_organizer` excluye nombres `_`/`.`. No apareció un quinto registro exacto de
   `00_Input` que requiera añadir el basename. El guard no puede quedar vacío en silencio:
   `tests/test_apertura_v1_control_files.py:58-62` afirma ambas colecciones.
3. **«Si se perdió la exclusión no se escribe nada»: no cerrada.** Tras una pérdida
   detectada durante el cuerpo, las etapas continúan escribiendo (HC-01). Tras una salida
   limpia, se libera y luego se escriben JSON y log sin exclusión (HC-02). Si
   `estado_v1.cerrar` falla, no se emite evento y queda la ronda abierta, pero la excepción
   no se traduce; el `PermissionError` concreto ya estaba declarado abierto y no se cuenta
   otra vez. Más peligroso y no declarado: si falla el evento después, queda estado
   cerrado sin log (HC-03).
4. **«Una costura tiene dos extremos»: cerrada solo en los ejemplos enumerados.** Los
   nuevos tests sí recorren el llamador real de cada costura y sustituyen el límite opuesto;
   matan sus mutantes declarados. No cubren las propiedades temporales de la finalización,
   la pérdida después de `yield`, la contaminación estructurada ni un punto fijo material
   real. El mutante intercalado de HC-02 sobrevivió a los 105 tests.

## 4. Lo que NO es un hallazgo

- `es_gestor_vacio` no confunde, para los estados que el productor actual puede crear, un
  fallo de listado, legado o vacío acompañado de otro error con un vacío confirmado.
- La validación previa de todos los `element` evita escribir el primer expediente antes de
  descubrir que un vínculo posterior es judicial, desconocido o carece de `element`.
- `--hasta` se valida antes de efectos y se propaga; la parada enumera las etapas no
  ejecutadas. Los mutantes correspondientes murieron.
- Drive pasa por `_intake_drive_ev`, reenvía `force=True`, no acepta `skipped=True` como
  consulta y conserva la custodia de un pull parcial.
- Una `MutexPerdido` que aflora al salir impide que se ejecute el bloque de finalización;
  no se escribe un falso cierre en ese camino concreto.
- El control `_apertura_v1.json` y su temporal no entran en el inventario probatorio de la
  sala ni en el merge/checkin; el guard de no-vacuidad existe.
- Los tres fallos de la suite completa se reproducen idénticos en `base/`; no son una
  regresión atribuible al diff.
- No se repiten como hallazgos las diez deudas que el mandato declara abiertas.
<!-- informe-literal:fin:k9tz -->

## 2. Evidencia verificada por el adjudicador

- **HC-02 CONFIRMADO leyendo mi propio diff.** La publicacion estaba **fuera** del `with`
  (`scripts/abrir_caso.py`, bloque `if resultado_v1 is not None:` de la rev. anterior), o
  sea sin mutex alguno. Movi la escritura de «dentro del lock, quiza tras perderlo» a
  «definitivamente fuera del lock», que es peor. El comentario contiguo enunciaba la
  propiedad correcta y el codigo hacia lo contrario.
- **HC-01 CONFIRMADO:** `mutex_sesion.sostenido()` **cede la sesion** (`yield
  entrada.sesion`, `core/casos/mutex_sesion.py:161`) y `main` usaba `with` sin `as`, asi
  que `revalidar()`/`perdido()` no se consultaban nunca.
- **HC-03 CONFIRMADO por lectura del orden:** `estado_v1.cerrar` iba antes de
  `registrar_cierre_v1`.
- **Remediado en un solo cambio, porque los tres son una frontera:** `revalidar ->
  publicar -> liberar -> salir`, indivisible. La publicacion vuelve DENTRO del bloque como
  ultimo acto, precedida de `sesion.revalidar()`; el evento forense va **antes** del
  `estado.json` porque el `.jsonl` es append-only y autoritativo; y fuera del bloque queda
  solo informar y salir, con lo que la propiedad de HA-07 se conserva **y ya no hay
  ninguna escritura a ese lado**.
- **Dos cosas que aparecieron al arreglar.** La costura de escritura ya **defendia en
  profundidad**: lanza `EscrituraSinMutex` en modo `v1` sin mutex sostenido, y salta antes
  que la revalidacion nueva. Y hubo que **acotar el guard F25** a `typer.Exit` en vez de
  cualquier `raise`: su propiedad es «no TERMINAR EL PROCESO aqui dentro», y un
  `raise MutexPerdido` deliberado es lo contrario del defecto — prohibirlo bloqueaba el
  arreglo correcto. Queda justificado en el propio test para que no se lea como una
  relajacion de conveniencia.

**Medicion tras remediar: 3.883 tests, 0 fallos con dos semillas (777 y 31337); 31/31
mutantes muertos, cada uno solo por su frontera.**

**HC-04, HC-05, HC-06 y HC-07 quedan ABIERTOS**, confirmados y sin remediar. Ver el §7.
