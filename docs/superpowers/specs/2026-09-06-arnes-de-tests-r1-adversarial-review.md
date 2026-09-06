---
tipo: revision-adversarial
objeto: "diff b707df5..34ee6c0 — el arnés de tests: paralelismo con xdist, doctrina de dos semillas y property tests con hypothesis (PLAN fila #22)"
objeto_rev: "1"
commit: "34ee6c0"
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: q7vk
sha256_informe: faf1cdb9339a6592ec00c4a7162c81ca884c75d8294d21226cd52620dc4f5c1e
adjudicado_en: docs/superpowers/plans/2026-09-06-arnes-de-tests-paralelismo-y-propiedades.md §4
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1 sobre el DIFF.** Única ronda de la pieza: el radio de daño no
> alcanza a decidir quién escribe sobre qué copia ni a destruir datos de cliente. El §1 conserva la
> voz del revisor **sin una coma cambiada**; el §2 es la evidencia que verifiqué yo. **La
> adjudicación NO está aquí:** va en el §4 del plan, que pasa a rev. 2.
>
> **Objeto:** copias externas de `b707df5` (base) y `34ee6c0` (head) extraídas con `git archive`,
> más el parche (`sha256 c34606eb…4de79ed`). El revisor recomputó ese hash al abrir y al cerrar y
> ambos coinciden con el declarado en el mandato: el objeto no se tocó.
>
> **Esta ronda pudo EJECUTAR, y eso la cambia entera.** El Python de sistema no tenía `pytest-xdist`
> ni `hypothesis` ni `pytest-randomly`, y sin ellos habría sido una revisión de *lectura* sobre un
> diff que consiste enteramente en mediciones. Se instalaron los tres expresamente antes de lanzarla.
> El hallazgo H-01 —el único ALTO— salió de correr, no de leer.
>
> **El diff REMEDIADO (`691f5e4`) no se ha vuelto a revisar**, y se dice.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:q7vk -->

HIGIENE: al abrir el directorio de revisión había `_stdout.log` además de `MANDATO.md`; no leí ese fichero ni lo utilicé como evidencia.

# Informe adversarial R1 — arnés de tests

## Objeto, método y límites

Se revisaron los árboles externos `base` y `head` bajo `C:\t\rev_arnes_20260906_134806\`, declarados como `b707df5` y `34ee6c0`. No contienen historial Git: **no acredito esos commits ni su genealogía**. Sí comprobé el contenido: inventarié 1.219 ficheros de base y 1.221 de head por SHA-256, encontré exactamente los diez ficheros del parche y reconstruí sus versiones head aplicando en memoria los hunks a base. La reconstrucción coincidió en los diez casos. El hash inicial del parche coincidió con el declarado.

Todas las ejecuciones y mutaciones se hicieron en copias propias bajo `C:\Users\tnm33\AppData\Local\Temp\r1arnes0906\`. Los árboles recibidos permanecieron como entradas de solo lectura. La única escritura mía en el directorio de revisión es este informe. Para los tests que consultan Git se creó un índice **sintético** en la copia; para el arnés se creó también un commit sintético que permite su restauración. Esto es preparación de ejecución, no prueba de procedencia. Un primer intento de crear ese commit activó un hook global y fue bloqueado por el sandbox; después se deshabilitaron los hooks únicamente en el Git de la copia.

En los comandos, `$PY` es `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`. Intérprete empleado: Python 3.14.4. Versiones comprobadas: pytest 9.1.1, pytest-xdist 3.8.0, Hypothesis 6.167.1, pytest-randomly 5.0.0, psutil 7.2.2, spaCy 3.8.13 y presidio-analyzer 2.2.359; `os.cpu_count()` = 12; psutil informa 10 núcleos físicos y la función instalada de `xdist` resuelve `auto` a **10 workers**, sin override de entorno. Esto difiere de los doce workers de la medición declarada. No se instalaron paquetes ni se cambiaron dependencias para poner verde.

Distingo **EJECUTADO**, **LECTURA** y **SIN VERIFICAR**. Los tiempos de las corridas completas no reproducen un benchmark limpio del autor: el entorno es distinto y hubo sondeos concurrentes durante parte de la primera corrida paralela. El benchmark de subconjuntos se programó después de acabar las suites completas.

## Hallazgos

### H-01 — ALTO — El paralelismo expone sondas compartidas y permite un verde por contenido ajeno

**Ubicación:** `scripts/session_close.py:555-556` y los otros comandos nuevos con `-n auto`; superficie preexistente que pasan a ejecutar en paralelo: `tests/test_guard_localizador.py:116-145`.

**Qué está mal:** los tests escriben y borran nombres fijos bajo `core/`, compartidos por todos los workers; las fixtures de `conftest.py` no aíslan esos ficheros.

**EJECUTADO, sin modificar los tests:** desde el scratch:

```powershell
& $PY -m pytest p/tests/test_guard_localizador.py -c p/pyproject.toml -o addopts= -q -n 4 -p no:randomly -p no:cacheprovider --basetemp=bg --tb=short
```

Salida relevante:

```text
FAILED ...::test_la_escotilla_legacy_no_crece
AssertionError: la escotilla `strict=False` crecio a 1 (techo 0): ['core/_zz_guard_probe_param.py:1']
FAILED ...::test_el_contador_distingue_los_casos[d = caso_path('W-X')-0]
AssertionError: d = caso_path('W-X')
assert 1 == 0
2 failed, 7 passed in 28.78s
```

**También reproduje el agujero de verde que pide A.** Ejecuté dos parametrizaciones originales en dos workers, añadiendo solamente una barrera de sincronización alrededor de `_llamadas_con_escotilla`: ambos tests escriben su sonda antes de leer y ninguno la borra hasta que ambos hayan terminado el recorrido. No se cambiaron ni los inputs ni los asertos ni el analizador. Es una intercalación posible del acceso al mismo fichero, forzada para hacerla reproducible. El script es `run_guard_barrier.py` y el plugin de instrumentación `guard_barrier.py`, ambos conservados en el scratch.

```text
2 passed in 19.68s
exit 0
worker gw0:
  expected_source = d = caso_path('W-X', strict=False)
  observed_source = d = path_for('W-X', strict=False)
  hits = ['core/_zz_guard_probe_param.py:1']
worker gw1:
  expected_source = d = path_for('W-X', strict=False)
  observed_source = d = path_for('W-X', strict=False)
  hits = ['core/_zz_guard_probe_param.py:1']
```

El primer test pasa sin analizar su propio caso. Igualar el conteo y el resultado no detecta esto. La reproducción controlada selecciona un subconjunto para forzar el reparto entre workers; **no afirmo haber observado esa intercalación concreta en una corrida completa sin instrumentación**. Sí prueba que los tests no son independientes y que la afirmación general de seguridad en paralelo carece de esta condición. La lectura de `xdist.scheduler.load.LoadScheduling.check_schedule` instalado confirma que reparte bloques de índices pendientes, sin garantizar que un fichero permanezca en un único worker. El defecto de aislamiento era preexistente; su exposición por el nuevo modo paralelo pertenece al diff.

Remedio a adjudicar: aislar el árbol/sonda que escanea cada test y los lectores concurrentes, o declarar y justificar su ejecución conjunta en un mismo worker. Separar solamente los nombres de las sondas no basta para el guard que escanea todo `core/`.

### H-02 — MEDIO — El arnés reparado no reproduce «0 mal apuntados, 5 de 9»

**Ubicación:** `tests/_mutantes_propiedades_utils.py:108-116`, `:184-203`.

**Qué está mal:** M06 omite un test que legítimamente lo mata, y la salida real cuenta seis mutantes exclusivos del fichero de propiedades frente al fichero de ejemplos seleccionado.

**EJECUTADO:** en la copia `h`, con índice/commit sintéticos restaurables y el código del arnés sin modificar:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_ADDOPTS='--basetemp=bt -p no:cacheprovider'
& $PY -m tests._mutantes_propiedades_utils
```

```text
base: verde
M01: SOLO LA PROPIEDAD
M02: AMBOS
M03: AMBOS
M04: AMBOS
M05: SOLO LA PROPIEDAD
[X ] M06 ... <<SOLO LA PROPIEDAD>>
    propiedad mata 1: test_el_guard_rechaza_el_vacio_y_las_posiciones_relativas
    MAL APUNTADO, tambien mata 1: test_lo_que_pasa_el_guard_es_un_solo_componente
M07: SOLO LA PROPIEDAD
M08: SOLO LA PROPIEDAD
M09: SOLO LA PROPIEDAD
mal apuntados o supervivientes: 1
mutantes que SOLO caza la propiedad: 6 de 9
EXIT=1
```

Los nueve mutantes murieron; el rojo de M06 es de la expectativa del arnés. Al quitar el rechazo de vacío, `exigir_componente_de_ruta("")` devuelve `""` y también viola la propiedad del componente aceptado. El defecto es verificable sin probabilidades ni conjeturas sobre separadores de Windows.

Otra inexactitud del manifiesto: M08 incluye como esperado `test_el_guard_rechaza_el_vacio_y_las_posiciones_relativas`, pero sus ocho entradas ya se rechazan por vacío o por `.`/`..` antes de llegar a la guarda de espacios. Quité solamente la guarda de espacios y ejecuté ese test: **`1 passed in 5.75s`**. El algoritmo exige algún test esperado, no todos los descritos como «DEBEN morir»; no denuncia esa expectativa imposible.

### H-03 — MEDIO — La instrumentación confunde ausencia de `FAILED` con ejecución válida/completa

**Ubicación:** `tests/_mutantes_propiedades_utils.py:134-157`, `:184-203`.

**Qué está mal:** `_corre()` descarta returncode, errores y completitud; después el arnés deduce tanto «base verde» como ausencia de cobertura de ejemplos de un conjunto parcial de líneas `FAILED`.

**EJECUTADO, caso 1:** importé el arnés en una copia y fijé `FICHEROS=('missing_review_file.py',)`. `_corre()` ejecutó pytest real y devolvió **`set()`**, indistinguible de su base verde, aunque no se ejecutó ningún test. El código de error y stderr se pierden.

**EJECUTADO, caso 2:** apliqué el M02 original en la copia y ejecuté el mismo comando de `_corre()` heredando `PYTEST_ADDOPTS='-x --basetemp=../bx -p no:cacheprovider'`. Salida:

```text
M02 with PYTEST_ADDOPTS=-x: exit 1
.F
FAILED tests/test_propiedades_utils.py::test_normalize_es_phone_nunca_devuelve_prefijo_de_pais
stopping after 1 failures
classification= SOLO LA PROPIEDAD
```

M02 es **AMBOS** en la corrida completa de H-02: lo mata también `test_utils.py::test_normalize_es_phone[0034600123456-600123456]`. Con `-x` ese ejemplo no llega a ejecutarse, pero el clasificador lo transforma en una victoria exclusiva. No se atribuye este escenario a la configuración por defecto del autor: es una condición reproducida que el arnés hereda y no controla.

**EJECUTADO, caso 3:** en la copia de archivo exportado, antes de crear un Git sintético, el comando solicitado imprimió `base: verde`, escribió el primer mutante y terminó con:

```text
fatal: not a git repository (or any of the parent directories): .git
subprocess.CalledProcessError: Command '['git', 'checkout', '--', '.']' returned non-zero exit status 128.
EXIT=1
```

`git status` había fallado, pero `main()` solo miró su stdout vacío. El arnés necesita Git y eso se documenta; el defecto adicional es empezar a mutar sin validar que la restauración sea posible. Repuse manualmente el fichero de la copia antes de la siguiente prueba.

Se necesita distinguir ejecución inválida, incompleta y completa; conservar returncode/errores; comprobar el conjunto ejecutado; y validar el preflight Git antes de la primera escritura. Un JUnit estructurado ayuda, pero tampoco sustituye a comprobar completitud.

### H-04 — MEDIO — Las propiedades dejan sin medir conservación y aceptación de entradas válidas

**Ubicación:** `tests/test_propiedades_utils.py:109-140`, `:204-265`; manifiesto de mutantes correspondiente.

**Qué está mal:** se comprueba una salida normalizada solo por idempotencia/ausencia de dos prefijos, y el guard solo por restricciones sobre lo aceptado y rechazo de entradas inválidas; faltan las direcciones positivas que impiden borrar todo o rechazar todo.

**EJECUTADO:** mutaciones adicionales aisladas sobre la copia `p`, restaurando después de cada una; pytest con `--hypothesis-seed=777`, `-p no:randomly`, `-p no:cacheprovider` y `--basetemp=b`:

| Mutación | Propiedades ejecutadas | Resultado |
|---|---|---|
| `normalize_es_phone`: `return ""` antes de normalizar | `-k normalize` | `2 passed, 5 deselected in 12.61s` |
| Eliminar solo `elif s.startswith("34") and len(s) == 11` y su cuerpo | `-k normalize` | `2 passed, 5 deselected in 12.70s` |
| `exigir_componente_de_ruta`: `raise ValueError(...)` incondicional | `-k guard` | `3 passed, 4 deselected in 18.26s` |

Esto **no** demuestra que toda la suite acepte esas regresiones: los ejemplos existentes cubren parte de ellas. Sí identifica mutantes obvios ausentes y limita las afirmaciones de las propiedades nuevas. No son siete tests vacuos: varios detectan defectos reales, incluido el prefijo doble; la insuficiencia es específica.

### H-05 — MEDIO — Falta Hypothesis en el preflight de dependencias de colección

**Ubicación:** `scripts/session_close.py:440`, `:511-528`, `:559-561`; import nuevo en `tests/test_propiedades_utils.py:34-35`.

**Qué está mal:** se añade `xdist` para distinguir «no pude medir», pero se omite `hypothesis`, que el nuevo fichero necesita al importarse durante la colección.

**EJECUTADO mediante inyección de ausencia en `importlib.util.find_spec`, sin desinstalar paquetes:**

```text
missing xdist probe ['xdist']
[X] NO SE HA MEDIDO NADA: este interprete no puede importar xdist.
La suite NO ha corrido: esto no dice nada sobre su estado.
exit 2
missing hypothesis probe []
```

La mitad de `xdist` funciona y da el mensaje prometido. Para Hypothesis, la sonda no lo consulta. **LECTURA del flujo posterior:** con ese paquete realmente ausente, su import superior abortaría colección y el resultado no cero de pytest terminaría presentado por `main()` como `[X] Tests fallando - commit abortado`, salida 1. **SIN VERIFICAR con desinstalación real:** no alteré el intérprete compartido. La omisión de la sonda sí está ejecutada y el import obligatorio está en la fuente.

### H-06 — BAJO — El comentario en línea rompe el patrón nuevo de `.gitignore`

**Ubicación:** `.gitignore:18`.

**Qué está mal:** `.hypothesis/          # ...` es un patrón literal completo para Git; no equivale a la regla `.hypothesis/` seguida de un comentario.

**EJECUTADO:** copia del `.gitignore` recibido en un Git sintético limpio, sin exclusiones globales ni `.git/info/exclude` añadidas:

```powershell
git -c core.excludesfile= check-ignore -v --no-index .hypothesis/examples/canary
```

Salida vacía, **exit 1**: la regla nueva no protege esa ruta. El comentario debe ir en su propia línea.

**Limitación que reduce la severidad:** Hypothesis 6.167.1 creó en esta corrida su propio `.hypothesis/.gitignore` con `*`. Esa segunda vía sí ignora la caché; no observé una incorporación de caché a Git ni afirmo una fuga de datos. El defecto confirmado es la regla versionada inoperante.



## Respuesta a A–H y cobertura de las mediciones

### A. Paralelismo, conteo y estado compartido

H-01 responde al caso de verde por otra razón con dos tests existentes. Se revisaron además las fixtures `autouse`, la lectura de `CASOS_ROOT`, el registro de workspaces y la raíz de locks. La variable `FEESDEFENDER_WORKSPACE_REGISTRY` se cambia por test a su `tmp_path`; esos directorios son distintos por worker. `case_locator._root()` lee `core.config.settings` dentro de la función: no sostengo la sospecha de un `settings` capturado allí al importar. No encontré ni reproduje otro verde indebido concreto en esos cuatro mecanismos. Esa ausencia de hallazgo no certifica aislamiento universal.

Comando de las mediciones finales, desde la raíz de la copia `s`:

```powershell
& $PY -m pytest tests -o addopts= -q --tb=short -p no:cacheprovider --basetemp=../bfinal --durations=15 --junit-xml=../<corrida>.xml <opciones>
```

`CASOS_ROOT` y el registro inicial se fijaron a rutas del scratch. `--basetemp` es relativo, fuera del árbol de código y dentro del scratch propio. Los resultados finales son:

| Corrida | Total | Passed | Fallos | Errores | Skip | Xfail | Pared (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Paralelo, semilla 777 | 4663 | 4571 | 3 | 0 | 79 | 10 | 241.03 |
| Serie, semilla 777 | 4663 | 4571 | 3 | 0 | 79 | 10 | 544.60 |
| Paralelo, semilla 31337 | 4663 | 4571 | 3 | 0 | 79 | 10 | 218.69 |
| Paralelo, semilla 777, --runslow | 4663 | 4642 | 4 | 0 | 7 | 10 | 210.10 |

**EJECUTADO:** la comparación de JUnit por `(classname, name)` da los mismos 4.663 identificadores y exactamente el mismo estado por test en serie/777, paralelo/777 y paralelo/31337. En esas corridas rápidas hay tres fallos comunes: los dos tests que exigen un `.venv` real en el checkout y el caso del wrapper de `expedientes_xl` cuyo stderr contiene repetidamente `ping no se reconoce`. Las copias exportadas carecen de ese venv y el escenario del wrapper depende del entorno de ejecución. No imputo esos tres rojos al diff ni los elimino del conteo.

El cuarto fallo de `--runslow` es `test_anon_integration.py::TestAnonimizarDocumento::test_genera_md_con_frontmatter`: Presidio no pudo adquirir un lock bajo la caché `python-tldextract` del perfil del usuario. **EJECUTADO para aislar la causa:** el mismo test, solo y en serie, falló igual (`1 failed in 30.12s`); al repetirlo cambiando únicamente `TLDEXTRACT_CACHE` a `r1arnes0906/tldcache`, pasó (`1 passed in 11.54s`). Comando: `python -m pytest tests/test_anon_integration.py::TestAnonimizarDocumento::test_genera_md_con_frontmatter --runslow -o addopts= -q --tb=short -p no:randomly -p no:cacheprovider --basetemp=../btld`. Por tanto, ese rojo no demuestra una regresión de paralelismo. El verde íntegro del autor no se reprodujo en las corridas completas de este entorno y queda SIN VERIFICAR en su configuración original.

La ejecución con `--runslow` también se completó. No aparecieron mensajes de worker caído, `MemoryError` u OOM en su log. Esto no mide el pico de memoria ni acredita capacidad en otras máquinas.

El total esperado de head es 4.663, pues incorpora siete tests respecto del conteo 4.656 citado para el paralelismo previo. No presento ese incremento como pérdida de conteo. En JUnit, `skipped` incluye los xfail; en la tabla se separan según el resumen de pytest.

**Corridas preliminares excluidas de la comparación:** una terminó con 358 fallos/27 errores porque puse el basetemp dentro de la copia y el registro rechaza expresamente ubicaciones bajo el proyecto. Otra, desde el padre de la copia, terminó con 22 fallos, varios por paths relativos de los propios tests y ausencia de índice/venv. Se corrigió la preparación, sin tocar tests. Una serie preliminar posterior se interrumpió para corregir el cwd; no se cuenta como medición completa. No atribuyo esos rojos de preparación al producto.

### B. `-n auto` fuera de `addopts`

| Subconjunto | Ficheros | Tests | Repetición | Serie (s) | Paralelo auto (s) | Resultado |
|---|---:|---:|---:|---:|---:|---|
| test_email_firmas.py | 1 | 211 | 1 | 9.99 | 33.14 | ambos verdes |
| test_email_firmas.py | 1 | 211 | 2 | 9.52 | 32.65 | ambos verdes |
| test_sala_lectura*.py | 7 | 73 | 1 | 13.11 | 39.00 | ambos verdes |
| test_sala_lectura*.py | 7 | 73 | 2 | 18.89 | 42.70 | ambos verdes |
| test_sala_maquina*.py | 14 | 247 | 1 | 39.63 | 56.13 | ambos verdes |
| test_sala_maquina*.py | 14 | 247 | 2 | 42.81 | 54.33 | ambos verdes |

**EJECUTADO:** cada modo usa el mismo subconjunto y `--randomly-seed=777`, desde `s`, con `-o addopts= -q --tb=short -p no:cacheprovider --basetemp=../bbench`; el paralelo añade `-n auto`. Dos repeticiones, ejecutadas después de las cuatro corridas completas, sin otros tests de esta revisión en paralelo. `bench.py` y `bench_maquina.py` conservan los comandos y los XML; en la segunda repetición de sala de máquina se invirtió el orden de los modos. Se cotejaron también los estados por identificador.
En las tres familias medidas, las dos repeticiones favorecen la serie. No encontré el punto de cruce con estos subconjuntos de 73, 211 y 247 tests. Un umbral para subconjuntos mayores queda SIN VERIFICAR; la mejora de la suite completa no permite fijarlo en un número universal de tests. No refuto la elección de dejar el paralelismo fuera de addopts.

No hay un umbral universal en número de ficheros o tests: importaciones, duración, procesos hijos y reparto de trabajo cambian el punto de cruce. Dejar el paralelismo fuera de `addopts` es compatible con escogerlo para un subconjunto costoso; no obliga a convertir «todo subconjunto» en una regla técnica universal. Los tiempos históricos exactos 17,0/11,9 y 371/94 quedan **SIN VERIFICAR en el entorno original del autor**.

### C. `normalize_es_phone`

**EJECUTADO comparando las dos implementaciones cargadas desde las copias/fuentes y el llamador `limpiar_telefono`:**

| Entrada | Base | Head |
|---|---|---|
| `0034 +34 600 111 222` | `+34600111222` | `600111222` |
| `341234567` | `341234567` | `341234567` |
| `+34 341234567` | `341234567` | `341234567` |
| `+33 341234567` | `+33341234567` | `+33341234567` |
| `0033 341234567` | `0033341234567` | `0033341234567` |
| `+34 003460011` | `003460011` | `60011` |
| `+34 34600111222` | `34600111222` | `600111222` |

El penúltimo es un sobre-recorte construido sobre una entrada no canónica; `limpiar_telefono` en head la rechaza como `""`. No acredité que represente un teléfono español legítimo y **no lo elevo a regresión de producción**. Los nueve dígitos que empiezan por `34` se conservan porque la rama exige longitud 11. Los extranjeros que no empiezan por un prefijo español no entran en el bucle de recorte. **LECTURA:** el bucle termina para toda cadena finita porque cada rama que continúa consume 2, 3 o 4 caracteres; la restante retorna.

La búsqueda de llamadores encontró `core/email_firmas.py:571` y los `__post_init__` de `NuevoColaborador`/`NuevoClienteContrario` en `core/sudespacho_relations.py:231-232,260-261`. Se leyó su contexto; no se hicieron llamadas al CRM. No encontré una regresión no deseada verificable sobre una entrada legítima en esos llamadores. H-04 recoge la conservación que las propiedades no garantizan.

### D. Generadores y posible tautología

**EJECUTADO:** se usaron las estrategias originales con `@seed(777)` y `settings(max_examples=400, database=None, deadline=None)`, sin suprimir los health checks en la sonda:

```text
phone_strategy {'examples': 400, 'double_prefix': 203, 'base_not_idempotent': 159} unique 400
case_strategy {'examples': 400, 'valid': 400} unique 400
```

La cuenta de prefijos repetidos se hizo sobre la cadena sin separadores con `^(?:\+34|0034|34){2}`. Es una medición de esta generación, no una distribución uniforme ni una probabilidad garantizada para cualquier semilla. Refuta la sospecha de cuatro ejemplos o de prefijo doble excepcional. El `.filter()` de tramos libres no dejó vacío el espacio.

**LECTURA y mutación:** reparsar con `_CASE_ID_NEW_PARTES` acopla el parser del test al de producción, pero el aserto no es automáticamente tautológico: compara el hueco de dirección con un literal y los otros tramos con los valores independientes devueltos por el generador. M03 y M04 lo ponen rojo. La estrategia excluye paréntesis y otras variantes de la gramática real; no demuestra universalidad sobre todo `case_id` aceptado. Las carencias concretas reproducidas están en H-04 y en la expectativa inejercitable de M08 de H-02.

### E. Mutación y clasificación

H-02 y H-03 recogen los resultados y los defectos del instrumento. **La sospecha concreta de separadores Windows no se confirma:** `:183-184` contempla ambas variantes y la corrida Windows clasificó las propiedades correctamente. El fallo observado de M06 no procede de `/` frente a `\`.

El comparador mide solo contra `tests/test_utils.py`, como declara `FICHEROS`. No mide el incremento frente a **toda** la suite anterior. Ataqué esa interpretación ampliando únicamente el conjunto de ejemplos con dos ficheros que ya están en base:

```powershell
& $PY -m pytest tests/test_ensure_case_sumidero.py tests/test_ensure_case_sumidero_r2.py -o addopts= -q --tb=short -p no:randomly -p no:cacheprovider --basetemp=../be
```

**EJECUTADO**, restaurando `core/utils.py` entre mutantes:

| Mutante etiquetado «solo propiedad» por el comparador | Ejemplos preexistentes que también lo matan | Resultado |
|---|---|---|
| M05 | componentes con `/` y no dejar carpeta parcial | 3 failed, 20 passed |
| M06 | vacío no convierte la raíz en expediente | 1 failed, 22 passed |
| M07 | componente `.` | 1 failed, 22 passed |
| M08 | espacio final sin andamiaje parcial | 1 failed, 22 passed |
| M09 | caracteres de control | 1 failed, 22 passed |

Por tanto, cinco de los seis «solo propiedad» de esta corrida ya tienen oposición en otros tests de ejemplo. No se debe traducir la etiqueta a exclusividad respecto de la suite completa. Tampoco afirmo que M01 sea exclusivo globalmente: no muté toda la suite contra él. Los mutantes adicionales de H-04 faltan en el manifiesto y la guarda de `34` desnudo no recibe un ataque dedicado.

### F. `session_close` y duraciones

La comprobación de ausencia de `xdist` funciona en la sonda ejecutada; el hueco nuevo es Hypothesis (H-05). **LECTURA de las versiones instaladas:** `xdist.dsession.DSession.worker_testreport` reenvía los reportes de cada worker al hook del controlador; `_pytest.runner.pytest_terminal_summary` reúne todos los reportes con `duration` de `terminalreporter.stats` y los ordena. `--durations=15` no está mostrando solamente un worker. Son las quince fases más lentas reportadas (`setup`/`call`/`teardown`), no una suma del tiempo de pared ni un perfil de memoria. La sobreposición de workers impide sumar esas duraciones y leerlas como tiempo transcurrido.

### G. Doctrina

**LECTURA:** la regla anti-trampa es accionable para una persona: enumera cambios prohibidos para obtener verde y exige parar, contrastar fuente y documentar la decisión. No es un control automático de eliminación/debilitamiento de tests y no se aporta uno en este diff. No encuentro contradicción sustantiva entre esa regla y `docs/FLUJO_GIT.md`.

Sí hay una desconexión operativa: `CLAUDE.md:313-318` exige dos semillas para aceptar, mientras que `session_close.main()` sigue lanzando una única corrida sin semillas fijas y emite «Tests verdes - puedes continuar». El cierre de `docs/FLUJO_GIT.md:51-64` remite a ese script como red local; su apertura `:37-38` conserva el comando en serie. La obligación humana de dos semillas puede cumplirse ejecutando el bloque nuevo aparte, pero seguir únicamente el cierre documentado no acredita haberla cumplido. Lo dejo como carencia de integración de doctrina, no como prueba de que nadie la haya ejecutado.

### H. Qué falta

Además de remediar H-01–H-06 y documentar el alcance de la medición sobre subconjuntos, falta:

- Que el instrumento de mutación pruebe su propio comportamiento con errores de colección, ejecución parcial, ausencia de Git y restauración fallida.
- Que el aumento de cobertura se mida contra el conjunto pertinente de ejemplos anteriores, o que todas las conclusiones mantengan explícitamente la limitación a `test_utils.py`.
- Propiedades positivas de conservación del número y aceptación de componentes válidos, con mutantes que demuestren que se ejercitan.
- Evidencia reproducible de la medición histórica: comandos/semillas, versiones, selección de tests y reportes estructurados comparables. No hay historial en los árboles recibidos que permita reconstruirla.
- Aislar también las cachés de bibliotecas externas: `--basetemp` y las fixtures del registro no confinan por sí solos la caché de `tldextract`, como mostró la corrida lenta.
- Un punto verificable en el flujo de aceptación donde consten ambas semillas; el comando de cierre por sí solo no lo hace.

No propongo reabrir el producto ni cambiar guardas jurídicas/funcionales para arreglar la suite. Los fallos ambientales se declaran como límites de cobertura, no como defectos del diff.

## Cierre de integridad y decisión

**EJECUTADO al cerrar:** los inventarios completos de base y head, con el SHA-256 de cada fichero, coinciden exactamente con los del inicio. El SHA-256 final de `diff.patch` coincide con el inicial y con el declarado. No se usa el Git sintético de las copias como evidencia sobre las entradas.

La recomendación de no enviar este diff se apoya principalmente en el verde por sonda ajena de H-01 y en que la medición de mutación que debía validar el cambio no coincide con la afirmada. La adjudicación corresponde al autor contra las fuentes y las reproducciones anteriores.

SHA-256 de `diff.patch` al abrir: `c34606ebd5abc2604dc79223501c1beb3e6685585fde42c3ae96a46ba4de79ed`
SHA-256 de `diff.patch` al cerrar: `c34606ebd5abc2604dc79223501c1beb3e6685585fde42c3ae96a46ba4de79ed`
VEREDICTO: NO-SHIP

<!-- informe-literal:fin:q7vk -->

## 2. Evidencia verificada por mí

Cada hallazgo se adjudicó **contra la fuente**, no contra el diff ni contra la seguridad con que
viniera redactado. Lo que reproduje yo, en el repo vivo y con su venv:

- **H-01.** `pytest tests/test_guard_localizador.py -n 4` → **3 rojos**, con el venv real y sin
  tocar los tests. Leí además el mecanismo en `tests/test_guard_localizador.py:127-145`: las seis
  parametrizaciones escriben al **mismo** fichero fijo, y el escáner recorre `core/` **entero**, que
  es la frontera de verdad y la razón por la que renombrar sondas no habría bastado.
- **H-04.** Apliqué el mutante `return ""` a `normalize_es_phone` y corrí las propiedades: `2
  passed`. El mutante sobrevive, tal como el informe dice.
- **H-06.** `git check-ignore -v --no-index .hypothesis/examples/canary` → la ruta la ignora
  `.hypothesis/.gitignore:9:*`, es decir el fichero que escribe hypothesis, **no** mi regla.
- **H-02.** Ya lo había medido yo antes de recibir el informe (8 de 9, M06 con expectativa
  estrecha). La mitad que **no** había visto —la expectativa imposible de M08— la comprobé leyendo
  las ocho entradas del test: todas se rechazan antes de llegar a la guarda que M08 retira.
- **Búsqueda de la frontera completa.** Barrido AST sobre `tests/*.py` buscando escrituras sobre
  rutas derivadas de la raíz del repo: **el único fichero coleccionado es
  `test_guard_localizador.py`**. Los cuatro `_mutantes_*.py` también escriben, pero pytest no los
  colecciona (`python_files = test_*.py`), así que no corren dentro de un worker.

**Lo que NO verifiqué, y por tanto no doy por probado:** las mediciones de tiempo del propio revisor
(su entorno resuelve `-n auto` a 10 workers, usa el Python de sistema y pagó una caché de
`tldextract` fría), y si el mutante M01 es exclusivo frente a la **suite entera** — ni él ni yo lo
medimos, y por eso la etiqueta del arnés se acota explícitamente a `tests/test_utils.py`.

Los tres rojos ambientales de sus corridas completas (dos tests que exigen un `.venv` real en el
checkout y el del wrapper de `expedientes_xl` que necesita `ping`) los declaró él mismo como límites
de su entorno y **no los imputó al diff**. Comparto esa lectura: la copia archivada no lleva venv.
