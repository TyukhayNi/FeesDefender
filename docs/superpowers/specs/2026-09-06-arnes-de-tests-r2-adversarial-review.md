---
tipo: revision-adversarial
objeto: "diff completo b707df5..91a0600 — el arnés de tests: paralelismo, propiedades, snapshots y cobertura del diff (PLAN fila #22)"
objeto_rev: "1"
commit: "91a0600"
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: m4tz
sha256_informe: 34e62dcfcc4f58ac97fbfdaa9ab6428fc291e39a365f82c1ea8484f4cd726ca3
adjudicado_en: docs/superpowers/plans/2026-09-06-arnes-de-tests-paralelismo-y-propiedades.md §8
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R2 sobre el DIFF COMPLETO.** Segunda ronda de la pieza, y
> **escalada autorizada expresamente por Nikolai**: el presupuesto por radio de daño era de
> una, ya consumida sobre `34ee6c0`. Después la rama creció de 3 commits (+557) a 7
> (+2.639) — casi el 80% sin revisar, incluido un refactor de la verja que gobierna todos
> los cierres. Le di el dato sin argumentar a favor, porque argumentarlo es el sesgo que la
> regla del 2026-08-26 vigila; la decisión es suya y la tomó.
>
> El §1 conserva la voz del revisor **sin una coma cambiada**; el §2 es la evidencia que
> verifiqué yo. **La adjudicación NO está aquí:** va en el §8 del plan, que pasa a rev. 3.
>
> **Objeto:** copias externas de `b707df5` y `91a0600` con `git archive`, más el parche
> (`sha256 d6374195…2b1f904`) y el informe de R1 (`faf1cdb9…4f5c1e`). Los tres conservan su
> hash al cerrar.
>
> **Doble mandato, y el segundo es el que casi nunca se hace:** atacar en fresco lo que R1
> no vio, **y comprobar si mis ocho remediaciones eran reales o cosméticas**. Su veredicto:
> 4 REAL, 1 REAL-con-límites, **3 INCOMPLETAS**.
>
> **El diff REMEDIADO (`4875c53`) no se ha vuelto a revisar**, y se dice.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:m4tz -->

HIGIENE: al abrir el directorio de revisión había `_stdout.log` además de `MANDATO.md`; no leí ese fichero ni lo utilicé como evidencia.

# Informe adversarial R2 — diff completo

## Objeto, integridad y método

Revisión del 2026-09-06. Entradas: `base/`, `head/`, `diff.patch` e `INFORME_R1.md` bajo `C:\t\rev_arnes_r2_20260906_163538`. Los commits `b707df5` y `91a0600` son **declarados**: los archivos exportados no permiten acreditar genealogía.

**EJECUTADO:** inventario SHA-256 de los 1.219 ficheros de base y 1.227 de head; exactamente 19 ficheros diferentes, los del parche, +2.639/−24. Reconstruí los 19 head aplicando los hunks a base en memoria: todos coinciden textualmente. Esta comparación normaliza CRLF/LF: el parche tiene LF y los árboles contienen CRLF. Los inventarios de integridad, en cambio, calculan hashes de los **bytes**, sin normalización. El hash inicial del parche coincide con el mandato. El del informe R1 es `faf1cdb9339a6592ec00c4a7162c81ca884c75d8294d21226cd52620dc4f5c1e`, también coincidente.

Todas las ejecuciones y mutaciones se hicieron en copias propias `rev/s`, `rev/m`, `rev/q`, `rev/r` y `rev/h`. No escribí en las entradas `base/` o `head/`. Los índices y commits creados en las copias son **sintéticos**, con hooks desactivados localmente; sirven para probar los guards y restauraciones, no para acreditar procedencia. El informe queda fuera de los árboles revisados.

Intérprete `$PY`: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`, Python 3.14.4. Versiones medidas: pytest 9.1.1, xdist 3.8.0, pytest-randomly 5.0.0, Hypothesis 6.167.1, pytest-cov 7.1.0, syrupy 6.0.0 y diff-cover 10.5.1. Los dos últimos faltaban en el intérprete; el intento de `pip --target` falló por red restringida. Copié esos paquetes y sus metadatos desde el venv local existente a `rev/deps`, utilizado mediante `PYTHONPATH`. **No modifiqué el intérprete compartido.**

Se distinguen **EJECUTADO**, **LECTURA** y **SIN VERIFICAR**. Una sonda con corredor simulado se identifica como tal. Los tiempos no son un benchmark limpio: hubo ejecuciones independientes concurrentes en copias diferentes. Se conservaron scripts, logs y JUnit junto al informe; los comandos comunes y el inventario están en `run_review.py`.

## Hallazgos

### H-01 — MEDIO — El grupo serializa los escritores del localizador, pero deja lectores concurrentes del mismo árbol

**Ubicación:** `tests/test_guard_localizador.py:62,143-151`; lectores fuera del grupo en `tests/test_entrypoints_mutex.py:206-209`, `tests/test_escritura_censo.py:297-301`, `tests/test_guard_no_borrado_crm.py:43,101-105` y `tests/test_intake_control_por_ubicacion.py:159-166`.

**Qué está mal:** otro worker puede enumerar una sonda de `core/` y abrirla después de que el localizador la haya borrado, incluso con `--dist loadgroup`.

**EJECUTADO:** dos tests originales, en dos workers, conservando fuentes, asertos y la marca del autor. El plugin externo `race_plugin.py` únicamente impone esta intercalación posible: escritor crea la sonda → lector enumera → escritor analiza y borra → lector abre el listado ya obtenido. No introduce ni elimina entradas del listado.

```powershell
& $PY -m pytest tests/test_guard_localizador.py::test_el_contador_detecta_una_escotilla_sintetica tests/test_entrypoints_mutex.py::test_e5_ningun_modulo_de_core_adquiere_el_mutex -o addopts= -q --tb=short -n 2 --dist loadgroup -p no:randomly -p no:cacheprovider -p race_plugin --basetemp=../br --junit-xml=../race.xml
```

Desde `rev/r`, con el directorio del plugin en `PYTHONPATH` y `REVIEW_BARRIER=rev/race`. Salida de `race.log`:

```text
tests\test_entrypoints_mutex.py:209:
    arbol = ast.parse(io.open(p, encoding="utf-8").read(), filename=str(p))
E   FileNotFoundError: [Errno 2] No such file or directory: 'core\\_zz_guard_probe_tmp.py'
1 failed, 1 passed in 13.45s
```

Las corridas normales del localizador y las dos suites completas sin instrumentación no reprodujeron esta carrera. **No atribuyo al resultado anterior un verde por sonda ajena nuevo**: demuestra un rojo por desaparición de fichero. La agrupación sí cierra las colisiones internas de R1; la frontera completa incluye los lectores. Aislar el árbol de las sondas elimina esa interacción; serializar solo a quien escribe no lo hace.

### H-02 — MEDIO — El detector AST omite un escritor existente y acepta una marca que no marca ningún test

**Ubicación:** `tests/test_guard_aislamiento_paralelo.py:66-120`; escritor omitido en `tests/test_case_mutex_r11.py:307-329`.

**Qué está mal:** el detector reconoce una sintaxis concreta de asignación y una referencia a `xdist_group`, en lugar de acreditar la escritura y la aplicación de la marca que promete comprobar.

**EJECUTADO sobre el código actual:** `test_una_junction_al_repo_se_rechaza` hace:

```python
destino = Path(config.settings.project_root) / "no_deberia_escribirse"
destino.mkdir(exist_ok=True)
# ...
destino.rmdir()
```

La auditoría de la suite en dos workers registró `os.mkdir` y `os.rmdir` en la raíz de la copia para ese test, que pasó. El detector devuelve `[]` y `_declara_grupo_xdist` devuelve `False` (`domain_probe.log`). Por tanto, la afirmación de unicidad respecto del **árbol compartido del repositorio** no se sostiene. Esta segunda escritura es en su raíz, no en `core/`; no he observado otra colisión concreta provocada por ese directorio.

**EJECUTADO, sondas de `probe_review.py units`:** el control `p=ROOT/'core'/'x.py'; p.write_text('x')` se detecta; las ocho variantes siguientes devuelven `[]`: escritura sobre `(ROOT/'core'/'x.py')` directamente, alias transitivo, asignación anotada, `ROOT.joinpath(...)`, `p.open('w')`, escritura mediante helper, método sobre `ROOT` y `Path('core/x.py')` relativo al cwd. No hace falta un analizador interprocedimental perfecto para advertir que estas formas ordinarias quedan fuera de su promesa.

Además:

```text
_declara_grupo_xdist("unused = pytest.mark.xdist_group\n") -> True
```

No hay llamada, decorador ni `pytestmark`. Una marca aplicada a un solo test también satisface la comprobación para todo el fichero. El detector puede dar verde sin que los tests escritores estén agrupados. Su enumeración tampoco es la colección de pytest: hoy los 265 ficheros son planos y empiezan por `test_`, pero el `glob` no cubriría subdirectorios ni el patrón predeterminado `*_test.py`.

### H-03 — MEDIO — El guard de lanzadores sigue pudiendo pasar gracias a texto que no es argumento de pytest

**Ubicación:** `tests/test_guard_aislamiento_paralelo.py:176-242`.

**Qué está mal:** concatena cadenas de todas las listas y llamadas del fichero y no comprueba cada orden que realmente lanza pytest.

**EJECUTADO:** se dirigió el guard original a un fichero sintético con:

```python
def launch():
    subprocess.run(['python', '-m', 'pytest', '-n', 'auto'])
    print('--dist loadgroup')
```

Resultado en `probes_units.log`:

```text
launcher without flag + print: GUARD PASSED
['--dist loadgroup', 'python', '-m', 'pytest', '-n', 'auto']
two launchers, second without flag: GUARD PASSED
```

La segunda sonda contiene dos órdenes reales: solo la primera lleva `--dist loadgroup`. El guard también pasa. En Markdown se agregan igualmente todos los bloques, por lo que una orden correcta puede tapar otra incorrecta.

El cambio a AST **sí excluye los comentarios** que originaron el defecto anterior, pero no cierra la asociación entre argumentos y comando. Los lanzadores actuales llevan el flag; no afirmo que hoy falte en ellos ni que este bypass haga pasar toda la suite: `test_session_close_verja.py` contiene comprobaciones independientes de las órdenes del script. El defecto confirmado es de este guard de regresión.

### H-04 — MEDIO — El test que afirma demostrar el rojo del snapshot nunca consulta el snapshot

**Ubicación:** `tests/test_email_atomize_render_snapshot.py:31-36,137-152`.

**Qué está mal:** demuestra que un reemplazo cambia una cadena y que dos llamadas al render coinciden, pero no que syrupy rechace una salida modificada.

**EJECUTADO:** la función original pasa si se le entrega un objeto cuyo `__eq__` lanza `AssertionError('SNAPSHOT WAS CONSULTED')`; jamás lo usa:

```text
negative snapshot self-test with bomb oracle: PASSED
```

También muté el render real en la copia, cambiando `fm.append(f"fuente: {m.fuente}")` por `fm.append("fuente: MUTADO")`, y ejecuté todo el fichero:

```text
2 snapshots failed. 3 snapshots passed.
FAILED ...::test_render_md_forma_completa
FAILED ...::test_render_md_forma_minima
2 failed, 5 passed in 5.77s
```

El test de “SE_PONE_ROJO” está entre los cinco verdes. Evidencia en `snapshot_mutated.log` y `probes_snapshots.log`; reproducción en `probe_review.py snapshots`.

Los cinco snapshots **sí muerden**, y esta revisión lo ha comprobado. Lo que es decorativo es la supuesta demostración permanente de esa propiedad. Debe ejercitar una comparación con referencia archivada y verificar su rechazo, o describirse únicamente como prueba del reemplazo y del determinismo entre llamadas.

### H-05 — MEDIO — El preflight acepta un fichero que Git no podrá restaurar

**Ubicación:** `tests/_mutantes_propiedades_utils.py:278-314,338,346-381`.

**Qué está mal:** estar dentro de un worktree y tener `git status` vacío no demuestra que cada fichero mutable exista en el índice.

**EJECUTADO con el arnés completo:** en una copia con commit sintético se retiró `core/utils.py` del índice mediante `git rm --cached`, se añadió su ruta a `.git/info/exclude` y se confirmó la retirada. El fichero permaneció íntegro en disco y los tests base pudieron importarlo. El preflight pasó, el primer mutante se escribió, y tanto el `finally` como `atexit` fallaron:

```text
base: verde (36 tests)
error: pathspec 'core/utils.py' did not match any file(s) known to git
subprocess.CalledProcessError: Command '['git', 'checkout', '--', 'core/utils.py']' returned non-zero exit status 1.
Exception ignored in atexit callback ...
safety_ignored_source exit 1 unchanged False
```

Logs: `safety_ignored_source.log`, `probes_safety_resume.log`; montaje en `probe_safety.py`. Repuse manualmente los bytes después. La ausencia total de Git, en cambio, **sí se rechaza antes de mutar**, con salida 2 y hash intacto.

La comprobación debería acreditar la fuente de restauración de **cada fichero** antes de escribir, o conservar y restaurar sus bytes desde una copia propia. No basta con volver a ejecutar el mismo `checkout` fallido al salir.

**Prueba de interrupción, con alcance explícito:** `signal.raise_signal(SIGTERM)` dentro del proceso, al entrar en la corrida mutada, ejecuta el handler y restaura: `exit 130 unchanged True`. Al terminar externamente el proceso real a mitad mediante `Popen.terminate()` en Windows: `exit 1 restored False`. Se esperó al hijo pytest y se repuso la copia manualmente. `TerminateProcess` no ejecuta handlers Python; tampoco `atexit` cubre `os._exit`. La afirmación “por donde sea” y la explicación de `:317-326` sobre señales son excesivas. **No exijo que un handler pueda interceptar una terminación forzosa**: debe declararse ese límite o protegerse la ejecución desde fuera del proceso/copia mutada.

### H-06 — MEDIO — Se repite el hueco del preflight de dependencias con syrupy y pytest-cov

**Ubicación:** `scripts/session_close.py:449-451,495-496,569-575`; fixture nueva en `tests/test_email_atomize_render_snapshot.py:98-152`.

**Qué está mal:** la verja vuelve a presentar como tests fallando una medición que no puede realizar por faltar una dependencia que ahora necesita.

**EJECUTADO con el intérprete indicado, sin añadir `rev/deps` a `PYTHONPATH` y sin desinstalar nada:** `deps_que_faltan()` devuelve `[]`. Se llamó a `correr_la_verja` sobre el fichero de snapshots, con `--basetemp=../bmissing` y dos workers auto mediante `PYTEST_XDIST_AUTO_NUM_WORKERS=2`. El pytest real devuelve seis errores de fixture `snapshot` ausente y el cierre imprime:

```text
deps missing= []
ERROR ...::test_render_indice_adjuntos_forma_completa
ERROR ...::test_render_correos_lectura_forma_completa
ERROR ...::test_render_md_forma_completa
ERROR ...::test_render_revision_las_tres_colas
ERROR ...::test_el_snapshot_SE_PONE_ROJO_si_cambia_la_salida
ERROR ...::test_render_md_forma_minima
[X] Tests fallando con la semilla 777 - commit abortado.
RESULT= semilla 777
```

Evidencia completa: `missing_syrupy.log`. Es el mismo tipo de diagnóstico incorrecto que motivó H-05 de R1, aunque aquí la ausencia se manifiesta en setup de fixture.

**LECTURA:** `pytest_cov` tampoco está en el preflight, pese a que `--cov` se ha vuelto obligatorio en la primera corrida. Su ausencia produciría argumentos no reconocidos. **SIN VERIFICAR con pytest-cov realmente ausente**: estaba instalado. La falta de `diff_cover`, por separado, puede seguir siendo aviso porque esa medición es opcional; no necesita bloquear la suite.

### H-07 — BAJO — El detector de comentarios acusa patrones legítimos y confunde espacios iniciales con un comentario

**Ubicación:** `tests/test_gitignore_no_inerte.py:392-411`.

**Qué está mal:** un `#` fuera del comienzo de línea no hace inválido un patrón, y `strip()` altera precisamente la posición que determina si la línea es comentario.

**EJECUTADO con Git real en un repositorio sintético, sin exclusiones globales:**

| Regla | Ruta consultada | Detector | `git check-ignore --no-index -v` |
|---|---|---|---|
| `foo#bar` | `foo#bar` | denuncia comentario | rc 0, regla efectiva |
| `file[#]name` | `file#name` | denuncia comentario | rc 0, regla efectiva |
| `foo\#bar` | `foo#bar` | no denuncia | rc 0, regla efectiva |
| `build/ # comment` | `build/a` | denuncia | rc 1, no ignora |
| `   # text` | `   # text` | omite como comentario | rc 0, patrón literal |

Salidas conservadas en `probes_units.log`. La gramática oficial especifica comentario cuando la línea empieza con `#`, admite escapes y clases de caracteres: [Git, gitignore — Pattern format](https://git-scm.com/docs/gitignore#_pattern_format).

Ignorar `\#` escapado es razonable; deducir de ello que todo `#` no escapado es comentario erróneo no lo es. Si se desea una convención interna más restrictiva, hay que declararla como tal y contemplar los patrones con corchetes. No hay actualmente una regla legítima acusada en el `.gitignore` recibido; el falso positivo se demuestra con entradas válidas. La corrección de `.hypothesis/` de R1 sí funciona.

### H-08 — BAJO — El parser de cobertura depende de un resumen entero único y no valida el estado del proceso

**Ubicación:** `scripts/session_close.py:500-509,530-546`.

**Qué está mal:** solo reconoce porcentajes enteros y toma la primera coincidencia, aun si hay otro resumen o un código de salida de error.

**EJECUTADO con diff-cover 10.5.1 real**, sobre `s/coverage.xml` y el parche recibido mediante `--diff-file=../../diff.patch`:

```text
Total:   55 lines
Missing: 4 lines
Coverage: 92%
```

La misma orden con `--total-percent-float` devuelve `Coverage: 92.73%`; ambas salen con código 0. El parser reconoce el entero y devuelve `None` para una salida decimal. Archivos: `diffcover_integer.log`, `diffcover_decimal.log`; el entero confirma la cifra final declarada por el autor.

**EJECUTADO con entradas sintéticas:** `Coverage: 100%\nCoverage: 0%\n` se interpreta como 100. Un corredor simulado que devuelve `stdout='Coverage: 100%\n'`, `stderr='fatal: failed\n'`, `returncode=2` produce `[OK] 100%`. No se comprobó una versión distinta que emita esos dos resúmenes ni un fallo real de diff-cover con esa combinación de stdout y returncode.

El comando actual sin opciones adicionales usa enteros y funciona en la versión medida. Este hallazgo es de robustez del aviso, no un 92% falso observado. Una salida estructurada o un parseo de decimal con control de returncode y ambigüedad evitaría convertir una medición válida en “no se pudo medir” y una inválida en “OK”.

### H-09 — BAJO — La orden anunciada para reproducir un rojo pierde `--runslow`

**Ubicación:** `scripts/session_close.py:565-575`; test de reproducción en `tests/test_session_close_verja.py:96-108`.

**Qué está mal:** la ejecución recibe los argumentos extra, pero el mensaje de reproducción los descarta.

**EJECUTADO con corredor simulado de salida 1:** `correr_la_verja(['--runslow'], corredor=...)` imprime únicamente:

```text
python -m pytest -q --tb=short -n auto --dist loadgroup --randomly-seed=777
```

Evidencia en `probes_units.log`. Si el fallo es de un test lento, esa orden lo omite. También pierde los flags de cobertura de la primera corrida. El test que pretende contratar la reproducción solo comprueba semilla y `loadgroup` y no prueba este caso.

La extracción **no perdió el argumento en la corrida real**: `orden_de_pytest(..., extra=pytest_args)` lo conserva, y hay un test para ese cableado. La pérdida está en la receta nueva de diagnóstico. **SIN VERIFICAR mediante un fallo lento real** en esta R2; no se ejecutó la suite con `--runslow`.

### H-10 — BAJO — La propiedad positiva del componente nunca prueba nombres de un carácter

**Ubicación:** `tests/test_propiedades_utils.py:329-354`.

**Qué está mal:** el generador concatena siempre dos bordes, de modo que una regresión que rechace todos los componentes válidos de longitud uno pasa las diez propiedades.

**EJECUTADO:** añadí únicamente lo siguiente al principio de `exigir_componente_de_ruta`, en la copia, y restauré después:

```python
if len(valor) == 1:
    raise ValueError("review")
```

```text
python -m pytest tests/test_propiedades_utils.py -o addopts= -q --tb=short -p no:randomly -p no:cacheprovider --hypothesis-seed=777 --basetemp=../bq
10 passed in 17.53s
EXIT=0
```

La implementación original acepta `exigir_componente_de_ruta('a', campo='probe') == 'a'`. Evidencia: `property_single_char.log`, `domain_probe.log`, `probe_review.py properties`.

También sobrevive a las diez propiedades un `return ''` restringido a entradas `+33...` (`property_foreign.log`, 10 passed), pero el ejemplo preexistente de extranjero sí protege esa dirección del contrato. **No se mutó la suite completa con estos dos mutantes adicionales**: no se afirma que ningún test de todo el repositorio los mate. La limitación confirmada es de las propiedades; la corrección positiva de R1 sí aporta cobertura real y mata sus tres mutantes anteriores.

## Respuesta al mandato A–E y cobertura ejecutada

### A. Aislamiento y estado compartido

Comando del localizador desde `s`, sustituyendo N por 4, 2 y 8:

```powershell
& $PY -m pytest tests/test_guard_localizador.py -q --tb=short -n N --dist loadgroup --randomly-seed=777 -p no:cacheprovider --basetemp=../bg --junit-xml=../guard_nN.xml
```

| Corrida | Tests | Resultado | Pared medida |
|---|---:|---|---:|
| Localizador, n=4 | 9 | 9 passed | 21,98 s |
| Localizador, n=2 | 9 | 9 passed | 12,16 s |
| Localizador, n=8 | 9 | 9 passed | 27,75 s |
| Suite, n=4, seed 777, con cobertura | 4.693 | 4.601 passed, 3 failed, 79 skip, 10 xfail | 265,33 s |
| Suite, n=8, seed 31337 | 4.693 | 4.601 passed, 3 failed, 79 skip, 10 xfail | 211,41 s |
| Suite auditada, n=2, seed 777 | 4.693 | 4.600 passed, 4 failed, 79 skip, 10 xfail | pytest: 343,18 s |

Los dos JUnit de las suites sin instrumentación contienen **exactamente los mismos identificadores y el mismo estado individual**, no solo el mismo total. Los nueve del localizador pasan en ambas. Sus comandos están en `run_review.py`: `tests -q --tb=short -n N --dist loadgroup --randomly-seed=S -p no:cacheprovider --basetemp=../bs[2] --junit-xml=../suiteS.xml`; la primera añade `--cov=core --cov=scripts --cov-report=xml`.

Los tres rojos comunes son los dos tests que exigen un `.venv` existente en el checkout exportado y `test_mcp_wrappers.py::test_sin_interprete_capaz_el_wrapper_FALLA_RUIDOSAMENTE[expedientes_xl]`, cuyo stderr contiene `"ping" no se reconoce`. No los atribuyo al diff. El verde íntegro del autor en su entorno queda **SIN VERIFICAR** aquí.

La tercera suite instrumentó eventos de escritura y comparó al salir de cada test las claves del entorno y las identidades de módulos **ya cargados**. Se usó `audit_plugin.py`; los logs no vuelcan valores del entorno. Encontró las sondas del localizador y el directorio de H-02; también escrituras de Hypothesis en su caché compartida `.hypothesis`. Esto acredita escrituras ejecutadas, no todas las ramas posibles ni procesos hijos no instrumentados. **No hubo módulos previamente cargados que quedasen sustituidos o retirados** en esa medición; no se consideran fuga los imports nuevos normales.

Además encontró dos alteraciones persistentes del entorno, preexistentes y fuera del diff: `test_sync_sudespacho_legacy.py:307-328` deja `SUDESPACHO_LEGACY_JWT` y `NEW_FIELD` con valores sintéticos. El helper `_update_env_field` escribe `os.environ`; `monkeypatch.delenv(..., raising=False)` no registra restauración cuando la clave ya estaba ausente. La auditoría lo detectó después del teardown. **No se reprodujo un fallo de otro test causado por esas claves**. Son estado entre tests del mismo worker, no memoria compartida entre procesos. El detector AST nuevo declara expresamente no cubrir entorno/cachés; no le atribuyo una promesa distinta.

**Incidencias de preparación, excluidas como defectos del producto:** la primera corrida del arnés usó el temporal predeterminado, inaccesible (`PermissionError` en `Temp/pytest-of-tnm33`), y abortó antes de mutar; se corrigió el `addopts` únicamente en la copia para usar `--basetemp=../bm`. En el Git sintético de la copia auditada incluí por error 180 archivos de `.hypothesis` producidos por mis sondas previas. Eso provocó el cuarto rojo de la tabla, `test_ninguna_regla_de_gitignore_es_inerte`. Tras retirarlos **solo del índice de la copia**, el test original pasó (`1 passed`, `audit_setup_recheck.log`). No presento esa suite de cuatro rojos como una corrida limpia ni oculto la causa propia.

El muestreo normal favorece el remedio interno; H-01 demuestra por qué no acredita aislamiento universal. H-02 y H-03 contestan por separado las dos mitades del guard.

### B. Snapshots, determinismo, PII y contratos

**EJECUTADO:** el fichero completo pasa tres veces, fijando tanto `PYTHONHASHSEED` como `--randomly-seed` a 1, 777 y 31337: en cada una, `7 passed`, `5 snapshots passed`. No actualicé la referencia. La mutación de `fuente` y el oráculo que lanza se describen en H-04.

**LECTURA de los cuatro renderizadores y del corpus:** las entradas se construyen en orden fijo; no se usa reloj ni locale; las cadenas generadas usan `\n`. Las listas y diccionarios de la fixture tienen orden definido. `watched` se usa para pertenencia, no para emitir el orden del set. `render_md` conserva el orden de los diccionarios suministrados y algunas colas conservan el de las listas: eso no introduce azar en esta fixture, aunque no prueba invariancia frente a reordenar datos de entrada equivalentes. Las semillas de pytest por sí solas no habrían probado el hash aleatorio; por eso varié ambos.

**Inspección completa del `.ambr`:** no encontré PII de caso real ni rutas absolutas. Contiene `PersonaUno`, buzones `example.invalid`, identificadores RFC sintéticos `a@x`/`b@x`, nombres genéricos de adjuntos y fechas fijas. No he identificado un dato real que deba retirarse.

Los ficheros preexistentes de contratos y renderizadores **no se borraron ni modificaron**: el inventario de diferencias lo acredita. **EJECUTADO para comprobar que todavía muerden:** sustituir `if m.respuesta_intercalada:` por `if False:` pone rojo `test_email_atomize_render.py::test_render_marca_flags_solo_si_true`, en su aserto `"respuesta_intercalada: true" in md_con` (`1 failed`, `contract_flags_mutant.log`). Los contratos sobre banners de autoría y selección de reconstruidos siguen presentes. No he mutado individualmente cada contrato de firma/cita/adjuntos; no certifico con una sola sonda todos sus asertos.

### C. Verja, diff-cover y decisiones de medición

**Comparación con base:** siguen el preflight, la detección de cambios en `core/anon/`, el forzado `--runslow`/`RUN_SLOW`, la transmisión de argumentos a pytest, la parada con salida no cero y los avisos posteriores. El comportamiento total no es idéntico, porque deliberadamente ahora hay paralelismo, dos semillas y cobertura. No encontré pérdida del modo lento en la ejecución al extraer la función. H-09 afecta a la receta de reproducción, no al cableado real. Las pruebas de la nueva verja se ejecutaron dentro de las suites.

La cobertura obtenida por la primera corrida, aplicada al parche recibido, mide 55 líneas relevantes y cuatro ausentes, `scripts/session_close.py:710-713`: **92%** entero. Se usó `--diff-file`, porque el commit y `origin/main` de las copias son sintéticos. El encabezado que diff-cover imprime por defecto no acredita ninguna rama remota. No se ejecutó `session_close.main()` como cierre operativo completo ni sus acciones auxiliares contra un repositorio vivo.

El aviso con umbral 90 es **coherente** con los otros avisos no bloqueantes del script y con la política escrita. No hay evidencia para afirmar que vaya a ser ignorado por las personas; tampoco es una condición automática de aceptación. No lo convierto en un defecto por preferir otra política. El valor 90 no se deriva estadísticamente de haber medido 92/93; es una elección operativa con esa holgura.

Medir solo la primera semilla ofrece cobertura **de esa corrida**, no necesariamente la unión de ambas. Orden, cachés y ejemplos de Hypothesis pueden cambiar líneas ejecutadas aun con tests verdes. La afirmación “es la misma con cualquier orden” es más fuerte que lo demostrado por el test, que solo cuenta flags. **SIN VERIFICAR:** no comparé dos XML de cobertura entre semillas para cuantificar una diferencia real de este repo. No presento una pérdida concreta de cobertura como reproducida.

Dos semillas fijas mantienen reproducibilidad y una segunda distribución, pero repetir siempre esas dos deja de ampliar la muestra de órdenes para una colección estable. Una semilla aleatoria **registrada también es reproducible**. El alcance de aceptación depende además del número de workers y del estado/selección; no solo del entero de semilla. No afirmo que dos fijas sean intrínsecamente peores en toda situación: una puede preservar una regresión conocida. Mantener semillas conocidas y añadir rotación sería una decisión de coste/cobertura, no una corrección funcional demostrada aquí.

### D. `.gitignore`

H-07 contiene la comparación con la gramática y con Git real. La regla actual `.hypothesis/` funciona; `coverage.xml` también está en línea propia. El guard de comentarios no es un parser de esa gramática y tiene falsos positivos válidos. Por otra vía, `_gitignores_trackeados` no comprueba el returncode de `git ls-files` y podría entregar lista vacía si falla; es **LECTURA**, no una corrida independiente de fallo inyectado en esta R2.

### E. Propiedades y arnés de mutación

**EJECUTADO:** `python -m tests._mutantes_propiedades_utils` sobre la copia `m`, con Git sintético restaurable y el arnés recibido sin modificar. Único ajuste de configuración para esta corrida: temporal relativo en `pyproject.toml` de la copia.

```text
base: verde (36 tests)
M01 SOLO LA PROPIEDAD
M02 AMBOS
M03 AMBOS
M04 AMBOS
M05 SOLO LA PROPIEDAD
M06 SOLO LA PROPIEDAD
M07 SOLO LA PROPIEDAD
M08 SOLO LA PROPIEDAD
M09 SOLO LA PROPIEDAD
M10 AMBOS
M11 AMBOS
M12 SOLO LA PROPIEDAD
mal apuntados, supervivientes o mediciones invalidas: 0
mutantes que SOLO caza la propiedad: 7 de 12
  ^ «solo» = frente a tests/test_utils.py, que es lo unico que compara este arnes.
EXIT=0 WALL=262.74
```

La lista por mutante resume los rótulos `[ok]` del log; las últimas cuatro líneas son la salida literal. **12/12 muertos y 0 mal apuntados reproducido.** M07 avisa de que `test_lo_que_pasa_el_guard_es_un_solo_componente` no murió en esta corrida: se ve la expectativa no satisfecha, sin ocultarla. El rechazo explícito de `.`/`..` sí lo mata.

**EJECUTADO sobre los caminos que motivaron R1:** un fichero inexistente devuelve `Corrida(total=0, codigo=4, valida=False)`, distinto de verde. Con M02 y `PYTEST_ADDOPTS=-x` heredado se ejecutan los 36 tests y se registran tres rojos, incluidas dos propiedades y el ejemplo `0034600123456`: mantiene la clasificación AMBOS (`corrida_addopts_x_real.log`). El entorno heredado ya no recorta esa ejecución. La comprobación de completitud compara el **número**, no la identidad del conjunto; no he reproducido aquí una selección distinta con igual tamaño que falsee un resultado.

La restauración en ausencia de Git, con fuente ignorada, por señal cooperativa y por terminación externa está medida en H-05. Al terminar se verificaron intactos los bytes originales de `core/utils.py` en todas las copias, tras las reposiciones manuales declaradas. Un intento preliminar adicional de mutación fue rechazado por permisos antes de escribir; la prueba de `-x` se repitió en otra copia y completó. No se cuenta ese intento como mutante aplicado.

**Dominio del teléfono:** se midió que `34 34 600111222` devuelve `3434600111222`, y `34 +34 600111222` devuelve `34+34600111222`. El generador positivo excluye ambas formas según la condición de longitud de la implementación. Esto deja sin promesa positiva esos prefijos repetidos, aunque las propiedades anchas sí pueden generarlos. No he convertido esa restricción explícita en un defecto nuevo de producción: quitar todo `34` sin atender a longitud también podría mutilar datos, y la función es conservadora y no valida longitud. Sí debe evitarse leer el título “salga como salga vestido” como cobertura de cualquier combinación de prefijos. `0034 +34 600111222` se normaliza correctamente, `341234567` se conserva y un extranjero `+33...` queda intacto salvo separadores. H-10 aporta mutantes adicionales que sobreviven a las propiedades, con su alcance acotado.

## Veredicto por cada remediación de R1

El informe original contiene **seis H numerados y dos observaciones adjudicadas como hallazgos en las secciones E y G**. Estos son los ocho; no invento H-07/H-08 en R1.

| R1 | Evaluación | Evidencia y límite |
|---|---|---|
| H-01, colisión de sondas | **INCOMPLETA** | La agrupación interna es real: 9/9 con n=2/4/8 y en las suites. Sigue una carrera con lectores fuera del grupo, reproducida en H-01 de R2. |
| H-02, manifiesto mal apuntado | **REAL** | M06 incluye la propiedad que faltaba; M08 retira la expectativa imposible. El arnés recibido da 12 muertos y 0 mal apuntados; las expectativas que no mueren se avisan. |
| H-03, medición inválida/parcial y restauración | **INCOMPLETA** | JUnit, returncode, neutralización de `-x` y rechazo de ausencia de Git sí funcionan. No se acredita que cada fuente sea restaurable; H-05 deja una mutación real y el atexit falla también. Las terminaciones forzosas quedan fuera de la garantía. |
| H-04, propiedades solo negativas | **REAL, con límites** | Las positivas matan los tres mutantes antes supervivientes, M10–M12, y ejercitan conservación/aceptación. H-10 identifica otro hueco; no considero cosmética toda la incorporación por no agotar el dominio. |
| H-05, dependencias no detectadas | **INCOMPLETA** | `hypothesis` y `pytest_randomly` están añadidos realmente. La superficie ampliada vuelve a dejar fuera dependencias obligatorias; falta de syrupy reproducida en H-06. |
| H-06, regla `.hypothesis` inerte | **REAL** | Comentario separado y regla efectiva. El detector añadido tiene defectos propios (H-07), que no deshacen la corrección de esa regla. |
| Sección E, sobre-anuncio de exclusividad | **REAL en la salida** | El resumen final acota explícitamente el 7/12 a `tests/test_utils.py` y reconoce que otros ejemplos matan cinco. La cabecera todavía emplea “suite de ejemplos” de manera amplia: conviene alinearla, pero la salida exigida sí está acotada. |
| Sección G, aceptación con dos semillas | **REAL** | La función corre 777 y 31337, conserva extras y se detiene ante el primer retorno no cero; sus tests están ejecutados. Fijar siempre las mismas semillas limita la exploración, pero ya no hay una única corrida presentada como dos. |

## Cierre

El motivo de NO-SHIP no son los rojos ambientales ni una exigencia de cobertura absoluta. Persisten una frontera de paralelismo incompleta, guards que certifican condiciones que no comprueban, y una ruta del arnés que vuelve a mutar sin restauración disponible. Los snapshots reales y las propiedades nuevas aportan cobertura; eso no valida las garantías más amplias de sus instrumentos.

**EJECUTADO al cerrar:** los inventarios SHA-256 completos de base y head coinciden con los iniciales; el parche conserva su hash. La adjudicación corresponde al autor contra la fuente y estas reproducciones.

SHA-256 de `diff.patch` al abrir: `d6374195dc4828abff1ed6d6f10f7f97abc7866311b4c9acc325a7d042b1f904`
SHA-256 de `diff.patch` al cerrar: `d6374195dc4828abff1ed6d6f10f7f97abc7866311b4c9acc325a7d042b1f904`
VEREDICTO: NO-SHIP

<!-- informe-literal:fin:m4tz -->

## 2. Evidencia verificada por mí

Cada hallazgo se adjudicó **contra la fuente**. Lo que reproduje yo, en el repo vivo:

- **H-04**, el más embarazoso y el más fácil de comprobar: pasé a
  `test_el_snapshot_SE_PONE_ROJO_si_cambia_la_salida` un oráculo cuyo `__eq__` lanza. **El
  test pasó**, o sea que nunca consultaba el snapshot. Confirmado.
- **H-02**: `_declara_grupo_xdist("unused = pytest.mark.xdist_group")` devolvía `True`, y mi
  detector de escrituras veía **1 de 6** formas ordinarias. Medí las seis.
- **H-01**: el censo con el detector reforzado da **2 escritores de 265**, exactamente los
  dos que el revisor nombra —el suyo (`test_case_mutex_r11.py`) incluido—. Tras el arreglo
  de raíz, **0 de 265**, y los ficheros afectados pasan con `-n 2/4/8` y orden aleatorio
  **sin** `--dist loadgroup`.
- **H-07**: los cinco casos de su tabla contrastados con mi detector reescrito; los cinco
  coinciden ahora con el comportamiento real de git.
- **H-10**: el mutante `if len(valor) == 1: raise` es ahora M13 del arnés y muere.

**Lo que NO verifiqué, y por tanto no doy por probado:** sus mediciones de tiempo (su
entorno resuelve `-n auto` a 10 workers y usa el Python de sistema), su reproducción de la
carrera lector/escritor —que exigía un plugin de barrera propio— y si M01 es exclusivo
frente a la suite entera. Esto último sigue **sin medir por ninguno de los dos**, y por eso
la salida del arnés acota la etiqueta a `tests/test_utils.py`.

Los tres rojos ambientales de sus corridas (dos tests que exigen un `.venv` real en el
checkout exportado, y el del wrapper que necesita `ping`) los declaró él mismo como límites
de su entorno y **no los imputó al diff**. Comparto esa lectura. También declaró, sin que
nadie se lo pidiera, un cuarto rojo causado por su propia preparación —180 ficheros de
`.hypothesis` colados en su índice sintético— y lo excluyó explicando la causa.
