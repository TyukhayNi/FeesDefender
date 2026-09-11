---
tipo: revision-adversarial
objeto: diff 0702f49..b051e96 — verificar_apertura (core + CLI + tests)
objeto_rev: "1"
commit: b051e96
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: p2r1
sha256_informe: e80fb1ca91f5bdbba5ca6e79b4c184a3a42700f1c1e4869601dcf47bcd4099c8
adjudicado_en: docs/superpowers/plans/2026-09-11-apertura-menos-decisiones.md §7
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# Acta de revisión adversarial R1 — `verificar_apertura`

- **Objeto revisado:** diff `0702f49..b051e96` — `core/verificar_apertura.py`, `scripts/verificar_apertura.py` y su fichero de tests
- **Ronda:** R1 (única por la regla del 2026-08-26: el comando es de solo lectura y no puede destruir nada)
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` sin `.git`, solo lectura
- **Informe recibido:** 2026-09-11, `C:/t/rev-p2-103713/wd/INFORME.md`, 34192 bytes
- **Hallazgos:** 13 — 7 ALTOS, 4 MEDIOS, 2 BAJOS; **13 confirmados, 0 refutados**
- **Remediado en:** `docs/superpowers/plans/2026-09-11-apertura-menos-decisiones.md` §7

**Por qué existe esta acta.** Yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**.

**Qué se le pidió, y es lo que devolvió.** El mandato puso en el centro una sola pregunta —
«¿puede este verificador decir *ok* de un expediente roto?»— y le pidió construir expedientes
rotos de formas que el autor no hubiera previsto. Los siete ALTOS son exactamente eso, cada uno
con su entrada concreta y su salida medida.

**Custodia.** Dos árboles `git archive` sin `.git`, en un directorio de ronda con nombre
irrepetible comprobado vacío antes de lanzar. Los `sha256` de los tres ficheros revisados
coinciden al abrir y al cerrar. El digest se computó tras el `exit 0` del proceso. Esta vez el
mandato declaró los permisos sin contradecirse —el error que costó pytest a la R1 de la pieza
anterior— y el revisor ejecutó las cuatro corridas, mutantes dirigidos uno a uno, y una
instrumentación de los eventos `open` de escritura durante los 33 tests.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:p2r1 -->
HIGIENE: al abrir el workdir contenía MANDATO.md y el fichero adicional _stdout.log; no leí el contenido de _stdout.log.

# Revisión adversarial R1 — verificar_apertura

Objeto: copias congeladas `../base/` y `../head/`, sin `.git`. Revisión de exactitud y completitud. Todas las ejecuciones y mutaciones se realizaron sobre copias o árboles sintéticos dentro de `C:/t/rev-p2-103713/wd`; no se modificaron los objetos revisados. El mandato puntual prevalece sobre las instrucciones generales de cambiar de directorio al repositorio de desarrollo y actualizar su estado: aquí no se hizo ninguna de esas escrituras. No se delegó trabajo.

## 1. Hashes de apertura

SHA-256, bytes originales de `head`:

| Fichero | SHA-256 |
|---|---|
| core/verificar_apertura.py | 3fc983fcd00f342b712175aeb083fa1c814742f1811c96044dcf699db8f40687 |
| scripts/verificar_apertura.py | e65bd09a3c1c337fee4f93ae6c43e438dee9e1ca92843789e543a1eb97dbd521 |
| tests/test_verificar_apertura.py | e959e47d41b0d3a9afcc06661561340bff5df850bb77f4fb9892e77887929803 |

`C:/Program Files/Git/usr/bin/diff.exe -ru ../base ../head`, salida 1 (diferencias, no error), confirmó **exactamente** los cuatro ficheros declarados: tres nuevos y el plan modificado. Ningún otro cambio. Inventario: head 1.297 ficheros / 29.182.158 bytes; base 1.294 / 29.137.205. No se acredita genealogía de commits.

## 2. Hallazgos

### H-01 — ALTO — Datos ilegales desaparecen antes del conteo y C3 devuelve ok

**Anclas:** `core/verificar_apertura.py:382`, `:394`, `:165` y `:168`.

Entrada medida: `_cobertura.json = [1, "broken", null]`, catálogo `[]`. Resultado: `ok`, «0 documentos lógicos y 0 entradas del catálogo», evidencia `filas_cobertura=0`. Variante inversa: cobertura `[]`, YAML `- bad\n- rows\n` → el mismo `ok`. Mixta: `[{"slug":"a"},42]` y catálogo `[{slug: a}]` → `ok`, una fila en vez de dos.

Ambos lectores descartan elementos que no son diccionarios. La evidencia deja de representar la entrada; corrupción de esquema se transforma en catálogo/cobertura vacíos o completos. Debería informarse `fallo` por forma inválida, conservando el número de elementos descartados. Control de contraste: un YAML **diccionario**, `{slug: a}`, sí da `fallo` («otra forma»).

### H-02 — ALTO — La resta de hijos acepta padres inexistentes, numéricos o autorreferentes

**Ancla:** `core/verificar_apertura.py:165`; contrato de tipo en `core/sala_maquina.py:191` (`parent_slug: str`, slug del bundle).

Entradas independientes: `[{"slug":"a","parent_slug":"a"}]`, `[{"slug":"a","parent_slug":17}]` y `[{"slug":"a","parent_slug":"missing"}]`, siempre con catálogo `[]`. Las tres dan `ok`, evidencia `filas_cobertura=1`, `hijos_de_bundle=1`, `documentos_logicos=0`.

Un valor verdadero convertido a texto basta para descontar un documento: no se acredita que exista un padre ni un bundle válido. El documento puede desaparecer íntegramente del catálogo y el verificador bendecirlo. `None` y espacios se normalizan a raíz y con una entrada dan `ok`; esa tolerancia por sí sola no demuestra pérdida, a diferencia de los tres casos anteriores.

### H-03 — MEDIO — Igual cardinalidad no acredita que se haya catalogado lo procesado

**Ancla:** `core/verificar_apertura.py:168`.

Cobertura `[{"slug":"a"},{"slug":"b"}]`, catálogo `[{"slug":"x"},{"slug":"x"}]` → `ok`, «2 documentos lógicos y 2 entradas del catálogo». Ni `a` ni `b` están catalogados y hay un duplicado.

**Distinción de alcance:** cumple la igualdad numérica literal del plan (`plan:127`), pero no la promesa general de verificar el resultado del expediente. Es un límite del diseño además de la implementación; no afirmo que el plan ya exigiera igualdad de identidades. Si se conserva este alcance, el nombre/detalle del control debe dejar claro que solo acredita cardinalidad.

### H-04 — ALTO — C5 acepta marcas inválidas y 88 copias de la misma pregunta

**Anclas:** `core/verificar_apertura.py:244`, `:248`, `:251`, `:262`, `:370`. Dominio real de marcas: `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py:89`, `:92`, `:95`.

Dos entradas separadas, hoja `PREGUNTAS`, filas 6–93:

- C contiene `q0`…`q87`, I vacía y M contiene `basura` en todas: `ok`, 88 preguntas, cero sin marcar.
- C contiene **88 veces `q0`**, I vacía, M `sí`: mismo resultado `ok`.

La primera no contiene ninguna marca admitida (`sí`/`no`, con normalización `si` en el generador); la segunda solo contiene una identidad de pregunta. Se cuenta no-vacío y número de filas, sin dominio ni unicidad. La comprobación no demuestra «las 88 preguntas». Estos defectos sobreviven a los controles positivos existentes, que solo crean IDs únicos y marcas válidas o vacías.

### H-05 — ALTO — Un espejo imposible de leer se presenta como ausencia de W-codes ajenos

**Anclas:** `core/verificar_apertura.py:309`, `:312`, `:324`.

Entrada real en Windows: `03_MD/ajeno.md` contiene `W-04AAAA`; mantuve un handle `CreateFileW` abierto sin compartir lectura. Control independiente: `read_text()` lanza `PermissionError(13, 'Permission denied')`. Mientras dura el bloqueo, C8 devuelve **`ok`, «ninguno en 0 espejos»**. No se usó un doble para este resultado.

También medidos: una carpeta llamada `03_MD/a.md` → `ok` con cero leídos; un único espejo en `03_MD/nested/a.md` → igual salida. El primero es una forma inválida; el segundo muestra que solo recorre el primer nivel (el productor habitual genera un layout plano). Inyección separada de `PermissionError` al listar `03_MD` mediante `os.scandir` → el glob de Python 3.14 termina vacío y también da `ok`.

No haber podido leer no es prueba negativa de contaminación. Debe quedar error de lectura verificable; no basta con el contador cero para contrarrestar el estado `ok`.

### H-06 — ALTO — Una ruta estructural ocupada por un fichero se trata como apertura pendiente

**Anclas:** `core/verificar_apertura.py:149`, `:188`, `:299`.

Entrada: carpeta de caso existente y `01_Procesado` **fichero regular** con texto `not a directory`. Informe medido: las cuatro locales `pendiente`, cinco `sin_implementar`, cero fallos. Los detalles dicen que los productores no han corrido. El CLI deriva salida 0 de esa combinación (`scripts/verificar_apertura.py:87`).

Aquí no falta meramente una etapa: existe una colisión de tipo que impide construir sus subdirectorios. Las guardas `is_file/is_dir` confunden ausencia con estructura inválida. Debería señalarse `fallo` por esa colisión, preservando `pendiente` para la ausencia legítima.

### H-07 — ALTO — El W-code corto anunciado por el CLI no se resuelve

**Anclas:** `scripts/verificar_apertura.py:54`, `:59`; `core/casos/case_locator.py:121` (buscar) y `:226` (resolve_ref).

Entrada: raíz sintética con `Caso (W-TEST01)/00_Input/_caso.md`, frontmatter `meta.id_go: W-TEST01`. Solo se sustituyó `_root()` por esa raíz: **buscar no estaba falseado**. `--case-id W-TEST01` → salida **2**, «Caso no encontrado»; `--case-id "Caso (W-TEST01)"` → salida 0 e informe de nueve controles.

`buscar` busca el nombre literal de carpeta; el CLI no llama a la resolución de referencias. La ayuda y el ejemplo anuncian ambas formas. Los tests del CLI sustituyen precisamente `buscar` (`tests/test_verificar_apertura.py:381`), por lo que no ejercen esta integración. No es un caso inexistente: es una referencia admitida que no se traduce.

### H-08 — ALTO — La guarda transversal confunde texto con un control positivo ejecutado

**Ancla:** `tests/test_verificar_apertura.py:361`–`:367`.

Reproduje primero el control del autor: C9 retorna siempre `Resultado("cuantia_coherente", "Cuantía", OK, "implementada")`, sin test nuevo. La guarda cae con `['cuantia_coherente']`.

Sobre ese **mismo mutante**, añadí esta forma legítima de documentar un test pendiente:

```python
@pytest.mark.skip(reason="CRM pendiente")
def test_c9_control(tmp_path):
    c = _caso(tmp_path)
    r = _r(c, "cuantia_coherente")
    assert r.estado == va.FALLO
```

Resultado: guarda verde; selección ejecutada **2 passed, 1 skipped** (incluye el control C8). Con `@pytest.mark.xfail(strict=True, reason="CRM pendiente")`: **2 passed, 1 xfailed**; el test se ejecuta pero C9 sigue incapaz de fallar. Con el mismo ejemplo dentro de una cadena triple-comillada, sin definir test alguno: **2 passed**. Los tres sobreviven; no hay control positivo real de C9.

Es también sensible a presentación: sustituir las comillas dobles por simples solo en la llamada del control positivo C8 conserva su comportamiento y su test verde, pero deja roja la guarda. La búsqueda literal no demuestra ejecución, resultado, ni siquiera existencia de una función test. El mutante matado por el autor es real, pero insuficiente para sostener la garantía escrita.

### H-09 — MEDIO — W-code propio elegido por primera aparición, no por la identidad entre paréntesis

**Anclas:** `core/verificar_apertura.py:397`–`:400` y `:315`.

Carpeta `Relacionado W-04AAAA - Caso (W-TEST01)`; espejo con `W-04AAAA`. Resultado: `ok`; evidencia `propio=W-04AAAA`. El código anterior al identificador del caso se convierte en referencia y el ajeno queda exento del barrido. La docstring afirma que el código va entre paréntesis, pero la implementación busca la primera coincidencia en cualquier posición. Una identidad ambigua debe declararse o resolverse por fuente canónica; no elegirse silenciosamente.

### H-10 — MEDIO — W-codes partidos por maquetación no se detectan

**Anclas:** `core/verificar_apertura.py:282`, `:315`.

Caso `W-TEST01`, espejo con `Documento W-\n04AAAA` → `ok`, un espejo leído, ningún ajeno. `W‐04AAAA` (guion U+2010) también → `ok`. La extracción de texto puede separar un identificador; la mayúscula no normaliza ni la separación ni el guion. Alcance: son variantes visuales del identificador; la regex solo contrata la grafía ASCII contigua. No sostengo que busque dentro del PDF binario.

Control correcto: `w-test01` → `ok`; `w-04aaaa` → `fallo`, ajeno `W-04AAAA`. Las minúsculas ordinarias sí están cubiertas.

### H-11 — MEDIO — Empate de mtime selecciona por nombre un informe bueno y oculta el roto

**Anclas:** `core/verificar_apertura.py:221`, `:232`, `:256`.

En `02_Analisis`, `Informe viabilidad A bueno.xlsx` tiene 88 marcas; `Informe viabilidad Z malo.xlsx` tiene 88 filas sin marca ni respuesta. Fijé a ambos `st_mtime=2000`. C5 elige A y da `ok`. La selección es determinista por orden léxico de `sorted` y el primer máximo, **no acredita cuál es la versión vigente**. El texto de éxito ni siquiera nombra el fichero elegido; el JSON sí lo hace en evidencia.

Controles: bueno más reciente → `ok`; malo más reciente → `fallo` con 88 huecos. No afirmo que la existencia de una versión vieja mala obligue a fallar: el defecto es resolver un empate sin una regla de vigencia ni declarar la ambigüedad.

### H-12 — BAJO — La prosa conserva una salida persistida que no existe

**Anclas:** `docs/superpowers/plans/2026-09-11-apertura-menos-decisiones.md:119`–`:120`, `:163`–`:168`, `:187`; `scripts/verificar_apertura.py:13`–`:25`, `:66`–`:87`.

Escenario: ejecutar el CLI sobre un caso e ir a consultar el `estado.json` o el evento forense prometidos en «Forma». La medición de escrituras del core y CLI da **cero**, y el árbol sintético mantiene idéntico inventario y hashes. Solo existe stdout; el código no persiste esos resultados. El apartado posterior (b) sí reconoce la decisión, pero el contrato en presente quedó contradictorio.

La decisión de no escribir `_apertura_v1.json` coincide con el código. La ruta `00_Input/_apertura_v1.json` existe en `core/apertura_v1_estado.py:44`. «Nadie lo leería» debe referirse a los resultados nuevos: el fichero de rondas ya tiene `leer()`; no acredita la ausencia universal de consumidores de ese fichero. Finalmente «Las cuatro de red» (`:187`) contradice la tabla de cinco. Esto no es un fallo del motor, pero sí de exactitud documental.

### H-13 — BAJO — «Todo en tmp_path» omite temporales de openpyxl

**Anclas:** `tests/test_verificar_apertura.py:12`, `:279`, `:341`.

Instrumenté los eventos `open` de escritura durante el cuerpo de cada uno de los 33 tests. Cinco tests de C5 que serializan un workbook abrieron un temporal `openpyxl.*` **fuera de su tmp_path**, en el directorio de temporales del proceso. En esta revisión estaba redirigido a `wd/tmp/os`, por lo que no hubo escritura en los árboles congelados ni fuera del workdir por estas llamadas.

Tests: hoja PREGUNTAS ausente, todas marcadas, respuesta sin marca, cambio de número de preguntas y filas en blanco. La frase «ningún test escribe en producción» es compatible con lo medido; «Todo se monta en tmp_path» no lo es literalmente. El contador y la lista corresponden a cuerpos de test, no a una auditoría universal de toda dependencia nativa.

## 3. Dictamen de las diez afirmaciones (§2 / A)

| # | Dictamen y evidencia |
|---|---|
| 1 | **ACREDITADA en su alcance de módulo/CLI sobre expediente.** Solo lectores, `load_workbook(read_only=True)`, sin mutex ni reparación. Sonda combinada: cero aperturas para escritura durante `verificar` y CLI, árbol idéntico después. Se desactivó bytecode; no se afirma que el intérprete nunca cree cachés con otra configuración. |
| 2 | **ACREDITADA para el camino normal; no universal en el sentido “siempre 4”.** Tuple de nueve en core:335, bucle:357, `comprobadas`:89 excluye `sin_implementar`. Caso vacío: 4/9. Ver apartado de honestidad para dependencias y excepciones. |
| 3 | **ACREDITADA como política.** `pendiente` no entra en `fallos` (core:85) y CLI:87 sale 0. Los tests normales y su mutante lo comprueban. H-06 muestra una corrupción indebidamente clasificada como pendiente. |
| 4 | **ACREDITADA la resta; insuficiente la validación.** Test del bundle, tests:134: cuatro filas, tres hijos, un lógico y una entrada → ok. Mutante `logicos=filas` muerto. H-02 delimita padres inválidos. |
| 5 | **ACREDITADA con precisión terminológica.** core:195–207: cero bytes produce fallo. Sigue figurando en `presentes` y además en `vacios`; “ausente” significa mismo efecto, no idéntica evidencia a un fichero inexistente. Test:203 y mutante muertos. |
| 6 | **PARCIAL.** core:251 comprueba I o M no vacías; 37 huecos → fallo; 90 marcadas → pendiente, tests:292/308/320. No valida marcas ni identidades (H-04), ni demuestra que un cambio de conteo sea un cambio de plantilla. |
| 7 | **ACREDITADA la lectura de texto y pendiente sin propio** (core:302, :311, :315; tests:234, :250). No acredita totalidad del barrido: H-05, H-09 y H-10. |
| 8 | **ACREDITADA para excepciones `Exception` que llegan al bucle.** core:360; test:107 y mutante. El informe conserva nueve resultados. No todas las excepciones llegan: las de lectura de C8 se silencian. El ID/título del control que revienta cambia al nombre de función (core:362). `BaseException` no se captura; no se considera defecto no capturar interrupción del usuario. |
| 9 | **PARCIAL.** CLI:60–62/:87 implementa 2/1/0, y tests:385/:394/:429 lo miden. H-07: puede devolver 2 para un caso existente solicitado con la forma de referencia anunciada. No hay garantía general 0/1/2 para errores del localizador fuera del bucle. |
| 10 | **ACREDITADA la existencia de cuatro controles positivos y la muerte del mutante del autor; REFUTADA la garantía transversal.** Los 33 tests detectaron sus mutantes dirigidos; H-08 demuestra tres supervivencias adicionales. No se acredita la ejecución histórica del autor, sino su reproducción independiente. |

### B. Prueba integrada de falso verde y fronteras adicionales

Construí `tmp/combined/Caso (W-TEST01)` con cobertura `[1,"roto"]`; catálogo YAML `- roto`; tres MD de sala con solo un encabezado; XLSX PREGUNTAS con `q0` repetido en C6:C93, I vacía y `basura` en M6:M93; espejo `ajeno.md` con `W-\n04AAAA`. CLI con nombre completo y localizador real contra raíz sintética:

```text
4 de 9 comprobaciones ejecutadas — 4 ok, 0 pendiente(s), 0 fallo(s)
exit_code = 0
```

Las cinco no implementadas sí se advierten. Por tanto, **no dice nueve verificadas**, pero sí da por buenas las cuatro locales de un expediente roto. Este resultado responde afirmativamente a la pregunta central, sin apoyarse solo en una lectura del diff. C4 cumple su contrato limitado de presencia y bytes, aunque un encabezado no demuestre contenido útil.

Otras entradas medidas, no elevadas todas a hallazgo independiente:

| Entrada concreta | Salida | Interpretación |
|---|---|---|
| PREGUNTAS con 88 IDs en B6:B93 y sin respuestas/marcas | pendiente; «todas marcadas», 0 preguntas | No ha reconocido las preguntas. Pendiente por layout desconocido es defendible; afirmar que todas están marcadas y que la plantilla cambió no está probado. |
| Solo cuatro IDs sin marcar en C1:C4 | pendiente, 0 preguntas | El escaneo empieza en fila 5; mismo límite. |
| 88 IDs en C y ninguna celda más allá de C (`max_column=3`) | fallo, 88 sin marcar | Control correcto: `iter_rows(max_col=13)` rellena las columnas ausentes. No hubo IndexError. |
| 87 IDs con marca sí | pendiente, 87 | Es la política explícita, no hallazgo por sí solo. No distingue una eliminación accidental de pregunta de un nuevo cuestionario. |
| Carpeta `02_SALA DE MÁQUINA`, MD con ajeno | fallo | Las mayúsculas de rutas funcionan en este Windows. No extrapolo a FS sensible a mayúsculas. |
| Nombre de sala con á en NFD (`a` + U+0301), mismo MD | pendiente, «no hay 03_MD» | No normaliza Unicode. El árbol existe bajo otra secuencia de código; el verificador no inspecciona su contenido. |
| Nombre `02_Sala` + NBSP + `de máquina`, mismo MD | pendiente | Igual límite de rutas canónicas; no se confunde NBSP con espacio. |
| `03_MD/a.md` enlace simbólico a un fichero ajeno dentro del workdir | fallo, W-04AAAA | Sigue el enlace y lee el destino. No demuestra confinamiento al expediente ni se ensayaron destinos externos. |
| Carpeta de espejos no listable (error inyectado en scandir) | ok, cero espejos | Cubierto en H-05; no equivale a haber probado una ACL real sobre toda la raíz del caso. |

### C. Honestidad del informe

- **Qué cuenta:** resultados `ok`, `pendiente` y `fallo`, no lecturas exitosas de artefactos. Sobre caso vacío hay cuatro comprobaciones de ausencia y el 4/9 es coherente con esa definición; no significa cuatro artefactos validados.
- **Excepción local:** sustituir C3 por una función que lanza `RuntimeError("boom")` deja 4/9 y nueve resultados. Una comprobación intentada y fallida sigue contándose; no hay inflación frente a las cuatro locales intentadas. El ID pasa a `boom` (en una excepción real sería el nombre `c3_cobertura_vs_catalogo`), perdiendo el ID estable.
- **Excepción de un stub:** sustituir C1 por esa misma función, exactamente la clase de escenario del test:115, da **5/9**. Es un intento adicional fallido, no cinco comprobaciones implementadas. La frase universal “4 de 9 incluso cuando una revienta” no se sostiene; el test de contención no exige el conteo. No se observó un camino normal de los cinco stubs constantes que lance por sí mismo.
- **Dependencia ausente:** inyectar `ImportError` de openpyxl cuando hay un XLSX da C5 `sin_implementar`, **3/9** y seis huecos. Es una degradación explícita y honesta (core:225–229), omitida por la simplificación “siempre 4”. Sin XLSX, devuelve pendiente antes de importar.
- **Flags:** medí las cuatro combinaciones de `--json` y `--solo-problemas`. Texto, con o sin filtro: aparece el aviso literal «NO construidas todavía» / «SIN VERIFICAR». JSON, con o sin filtro: ese aviso literal no aparece, pero conserva las nueve filas, los cinco estados `sin_implementar`, sus motivos y el resumen. No es ocultación semántica de los huecos; sí refuta “aviso literal SIEMPRE”. En JSON `--solo-problemas` no filtra.
- **JSON frente a texto:** JSON incluye `evidencia`; texto solo título/detalle/resumen. El fichero de viabilidad elegido y los contadores detallados son visibles en JSON, no siempre en texto. Los estados coinciden; ambos heredan la evidencia falsa por filtrado de H-01 y el falso “ninguno” de H-05. No existe un estado global `ok`; existen estados por control y salida 0, que significa cero fallos detectados, no apertura completa.

### E. Prosa y alcance construido

Las cuatro locales y los cinco stubs coinciden con las nueve filas del plan. Censo, hashes remotos y CRM precisan consultar fuentes externas para cumplir ese contraste; no se verificó red ni la preparación real de esas APIs. Los motivos de aplazamiento están expresos en los stubs. La falta de un consumidor de **estos resultados nuevos** es compatible con no persistirlos; no es una demostración de que nadie lea el fichero de rondas existente.

El apartado (b) describe correctamente la ausencia de persistencia; H-12 identifica el párrafo antiguo que quedó afirmándola. El apartado (c) excede lo que prueba su guarda (H-08). «Cierran cuatro falsos OK» solo es defendible para los escenarios concretos cubiertos por los tests: la sonda integrada reproduce el mismo modo de fallo fuera de esos ejemplos. El motivo del mutex es arquitectónico: el módulo de estado durable escribe y no convierte en solo lectura a quien lo llame; esta revisión no revalida toda la gobernanza de mutex del repositorio.

## 4. Resultados de ejecución (§D)

Intérprete: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`. Ejecución final desde el workdir, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, `TMP`/`TEMP=wd/tmp/os`; caché de pytest desactivada. Padres de temporales creados antes. Ningún test se ejecutó sobre los árboles congelados.

Comando del fichero nuevo, para cada semilla S:

```text
python.exe -m pytest copy_head/tests/test_verificar_apertura.py --randomly-seed=S -p no:cacheprovider --basetemp=tmp/retryS -o addopts='' -q
```

| Ejecución | Resultado |
|---|---|
| Head, semilla 777 | 33 passed, 13,47 s; salida 0 |
| Head, semilla 31337 | 33 passed, 4,32 s; salida 0 |
| Base + mismo fichero nuevo, semilla 777 | 0 tests ejecutados; 1 error de colección por ImportError, salida 2 |
| Base + mismo fichero nuevo, semilla 31337 | 0 tests ejecutados; 1 error de colección por ImportError, salida 2; 43,07 s |
| Instrumentación de escrituras del fichero nuevo, 777 | 33 passed, 25,72 s; cinco tests con temporales openpyxl fuera de tmp_path |
| Un mutante dirigido por test, 777 | **33 failed, cero verdes**, 22,11 s; fallos de asertos/expectativa, no errores de colección |

**El control sobre base no equivale a “33 tests rojos”.** El import de core se hace en la línea 19 del fichero de tests; la colección aborta antes de ejecutar cualquiera. Ninguno pasa ni queda independientemente refutado por esa corrida.

Incidencia de entorno conservada: las primeras dos corridas desde `copy_head` con `--basetemp=../tmp/...` produjeron 33 errores de setup (`WinError 5` al crear la ruta); no fallos del producto. Volver al workdir y usar `tmp/...` resolvió el problema sin cambiar fuente, tests, plugins ni permisos. Dos primeros intentos de suite completa con esa disposición se interrumpieron por el mismo error repetido; no se cuentan como corridas completas. No atribuyo una causa interna más específica del sandbox que la diferencia efectivamente medida.

### Mutaciones dirigidas: método y resultado por test

Cada cuerpo original de test se ejecutó contra **una** variante de producción. El plugin de revisión compila el código mutado en el módulo correspondiente antes de la llamada y restaura el diccionario del módulo después; no modifica los asertos del autor. Se conservaron las 33 variantes de fuente en el andamiaje. Una muerte solo demuestra sensibilidad a ese mutante, no exhaustividad. `OK→FALLO`, `FALLO→OK` y `PENDIENTE→OK` de la tabla se limitan a la función C indicada; los mutantes especiales se especifican.

| Test | Mutante de producción | Resultado |
|---|---|---|
| `test_c3_FALLA_con_un_catalogo_ilegible` | c3_cobertura_vs_catalogo: retornos FALLO → OK | MUERTO |
| `test_c3_FALLA_con_un_cobertura_json_ilegible` | c3_cobertura_vs_catalogo: retornos FALLO → OK | MUERTO |
| `test_c3_FALLA_cuando_faltan_documentos_en_el_catalogo` | c3_cobertura_vs_catalogo: retornos FALLO → OK | MUERTO |
| `test_c3_los_hijos_de_bundle_NO_cuentan` | no restar hijos de bundle | MUERTO |
| `test_c3_ok_cuando_los_documentos_logicos_cuadran` | c3_cobertura_vs_catalogo: retornos OK → FALLO | MUERTO |
| `test_c3_pendiente_si_falta_el_catalogo_pero_hay_cobertura` | c3_cobertura_vs_catalogo: retornos PENDIENTE → OK | MUERTO |
| `test_c3_pendiente_si_la_sala_de_maquina_no_ha_corrido` | c3_cobertura_vs_catalogo: retornos PENDIENTE → OK | MUERTO |
| `test_c3_un_catalogo_VACIO_no_es_ilegible` | c3_cobertura_vs_catalogo: retornos FALLO → OK | MUERTO |
| `test_c4_FALLA_con_dos_de_cuatro` | c4_artefactos_de_la_sala: retornos FALLO → OK | MUERTO |
| `test_c4_ok_con_los_cuatro` | c4_artefactos_de_la_sala: retornos OK → FALLO | MUERTO |
| `test_c4_pendiente_sin_sala` | c4_artefactos_de_la_sala: retornos PENDIENTE → OK | MUERTO |
| `test_c4_un_artefacto_VACIO_cuenta_como_ausente` | c4_artefactos_de_la_sala: retornos FALLO → OK | MUERTO |
| `test_c5_FALLA_con_filas_en_blanco` | c5_viabilidad_completa: retornos FALLO → OK | MUERTO |
| `test_c5_FALLA_si_el_xlsx_esta_corrupto` | c5_viabilidad_completa: retornos FALLO → OK | MUERTO |
| `test_c5_FALLA_si_el_xlsx_no_tiene_hoja_PREGUNTAS` | c5_viabilidad_completa: retornos FALLO → OK | MUERTO |
| `test_c5_ok_con_todas_marcadas` | c5_viabilidad_completa: retornos OK → FALLO | MUERTO |
| `test_c5_pendiente_si_la_plantilla_cambia_de_numero` | c5_viabilidad_completa: retornos PENDIENTE → OK | MUERTO |
| `test_c5_pendiente_sin_informe` | c5_viabilidad_completa: retornos PENDIENTE → OK | MUERTO |
| `test_c5_una_respuesta_sin_marca_NO_es_un_hueco` | ignorar respuestas; exigir marca | MUERTO |
| `test_c8_FALLA_con_un_wcode_ajeno_DENTRO_del_texto` | c8_sin_wcodes_ajenos: retornos FALLO → OK | MUERTO |
| `test_c8_ok_sin_ajenos` | c8_sin_wcodes_ajenos: retornos OK → FALLO | MUERTO |
| `test_c8_pendiente_si_no_hay_referencia_contra_la_que_comparar` | c8_sin_wcodes_ajenos: retornos PENDIENTE → OK | MUERTO |
| `test_c8_pendiente_sin_espejos` | c8_sin_wcodes_ajenos: retornos PENDIENTE → OK | MUERTO |
| `test_cada_comprobacion_implementada_PUEDE_decir_fallo` | C9 implementada OK sin control positivo | MUERTO |
| `test_cli_caso_inexistente_sale_con_2` | caso ausente → exit 0 | MUERTO |
| `test_cli_dice_SIEMPRE_lo_que_no_ha_comprobado` | ocultar aviso con filtro | MUERTO |
| `test_cli_json_lleva_las_nueve_con_su_evidencia` | omitir C9 del JSON | MUERTO |
| `test_cli_sale_con_0_con_pendientes_pero_sin_fallos` | CLI siempre 1 | MUERTO |
| `test_cli_sale_con_1_si_hay_un_fallo` | CLI siempre 0 | MUERTO |
| `test_el_informe_enumera_SIEMPRE_las_nueve` | omitir C9 | MUERTO |
| `test_sin_implementar_NO_cuenta_como_comprobada` | contar sin_implementar como comprobada | MUERTO |
| `test_un_estado_inventado_revienta_al_construir` | permitir estado inventado | MUERTO |
| `test_una_comprobacion_que_revienta_no_tumba_el_informe` | excepción → OK | MUERTO |

Mutantes adicionales de la guarda: C9 siempre OK sin test → muerto; C9 siempre OK + control `skip` → sobrevive; + control `xfail(strict=True)` → sobrevive; + ejemplo en cadena → sobrevive. El cambio de comillas del control válido de C8 produce un falso rojo en la guarda. Son resultados diferentes del 33/33 anterior y no deben agregarse para presentar una tasa engañosa.

### Suite completa de head

Comando por semilla: `python.exe -m pytest copy_head/tests --randomly-seed=S -p no:cacheprovider --basetemp=tmp/fullretryS -o addopts='' -q --tb=short -n 4`, con `CASOS_ROOT` y registro de workspaces redirigidos dentro de `wd/tmp`. Se conservaron los tests y la configuración de skips del repositorio; no se añadieron exclusiones para poner verde. Resultados y límites incorporados a continuación.

| Semilla | Resultado de la corrida completa | Salida |
|---|---|---|
| 777 | **21 failed, 5093 passed, 90 skipped, 10 xfailed**, 528,90 s | 1 |
| 31337 | **21 failed, 5093 passed, 90 skipped, 10 xfailed**, 460,33 s | 1 |

Total en cada corrida: **5.214 casos**. Seis snapshots aprobados en cada una. Los 33 tests nuevos están incluidos; no se suman otra vez al total. No se usó `--runslow`: los skips son los de la configuración y del entorno, no pruebas ejecutadas y superadas.

**Diagnóstico de los 21 fallos, sin atribuirlos al diff:** 16 eran lecturas de rutas relativas al cwd en los módulos `test_barrera`, `test_guard_sync_cli_pull_v2`, `test_fake_drive`, `test_entrypoints_mutex` y `test_escritura_censo`. Repetí una selección de 77 casos que contiene todos los 21 fallidos, arrancando el intérprete desde wd y haciendo `os.chdir(copy_head)` antes de pytest (temporales `../tmp/cwd-corrected-S`). No modifiqué los tests ni añadí stubs para satisfacerlos:

| Semilla | Reejecución con cwd de la copia |
|---|---|
| 777 | **5 failed, 71 passed, 1 skipped**, 25,97 s; salida 1 |
| 31337 | **5 failed, 71 passed, 1 skipped**, 21,91 s; salida 1 |

Los 16 fallos por cwd desaparecieron. Los cinco restantes, iguales en ambas semillas, son:

1. `tests/test_gitignore_no_inerte.py::test_una_negacion_no_cuenta_como_regla_inerte`: `git ls-files`, rc 128; no hay `.git`.
2. `tests/test_gitignore_no_inerte.py::test_ninguna_regla_de_gitignore_es_inerte`: mismo requisito.
3. `tests/test_gitignore_no_inerte.py::test_los_readme_de_telemetria_estan_rescatados_y_la_telemetria_no`: `git check-ignore`, rc 128.
4. `tests/test_session_close_no_pude_medir.py::TestLaRutaQueSugiere::test_en_este_repo_encuentra_uno_que_existe`: el buscador de intérprete devuelve None; la copia no contiene el venv que el test presupone.
5. `tests/test_session_close_no_pude_medir.py::TestLaVerja::test_el_mensaje_sugiere_un_interprete_QUE_EXISTE`: mismo presupuesto de venv.

No fabriqué un historial ni un venv para volverlos verdes. **No hay suite completa verde acreditada**: la segunda tabla es una reejecución parcial de diagnóstico, no una tercera corrida completa ni un conteo para sumar al anterior. No se ejecutó toda la suite de base para atribuir regresiones globales; sobre base se ejecutó el fichero nuevo copiado, que aborta por importación como se indicó.

## 5. Inventario de lo NO cubierto

- Las cinco comprobaciones remotas están declaradas pero no implementadas: C1, C2, C6, C7 y C9. No verifican ningún dato del caso.
- La suite nueva no cubre esquema completo ni identidad/unicidad de cobertura/catálogo, integridad de padres, marcas fuera de dominio, duplicados de preguntas, selección por mtime, errores de lectura de MD, Unicode, enlaces, colisiones fichero/directorio, ni el localizador real. Varias de esas fronteras sí tienen sondas independientes en esta revisión; no se convierten por ello en regresiones protegidas por el proyecto.
- La guarda no comprueba el registro de tests ejecutados ni su resultado real, ni resiste skip/xfail/documentación. Tampoco ejecuta cada comprobación implementada con un caso positivo elegido por una estructura explícita.
- C4 valida presencia/tamaño, no calidad de los índices, YAML ni enlaces a documentos. C3 solo mide cardinalidad; C8 no busca dentro de PDF, no recorre subcarpetas ni compara cantidad de espejos contra cobertura.
- No se probó exhaustivamente relectura mientras otro proceso cambia los artefactos, eliminación de archivos entre stat/read, permisos ACL sobre toda la raíz, enlaces rotos/ciclos/escapes, archivos enormes, límites de memoria, cifras decimales/fechas/formulas sin caché en Excel, ni todos los nombres posibles de informes.
- No se hizo mutation testing exhaustivo de todas las ramas. Hay 33 mutantes dirigidos y ataques adicionales documentados, no una garantía de completitud del espacio de entradas.

## 6. Lo que NO pude verificar

- Identidad de commits, autoría/genealogía o que el autor ejecutara históricamente las mediciones descritas: **SIN VERIFICAR**, sin `.git`. Sí se reprodujo su mutante concreto.
- Episodios de producción de 2026-09-10, cifras históricas y ocho herramientas reales: **SIN VERIFICAR**; los ejemplos aquí son sintéticos.
- Drive, CRM, red, sincronización rclone y exactitud de los gates organizativos pendientes: **SIN VERIFICAR**, no se contactaron.
- ACL real de denegación sobre la raíz completa del caso: **SIN VERIFICAR**. Se midió un bloqueo real de un fichero y se inyectó un error de listado; no se presentan como la misma prueba.
- Comportamiento de las rutas en Linux/macOS, y visualización/edición interactiva en Excel: **SIN VERIFICAR**.
- Ausencia absoluta de consumidores externos del futuro informe persistido y ausencia de cualquier efecto nativo no capturado por los eventos Python: **SIN VERIFICAR**. El alcance positivo de la lectura es el código inspeccionado, los eventos medidos y los hashes del escenario sintético.
- Causalidad de fallos ajenos en la suite completa: solo puede atribuirse al diff con un control correspondiente sobre base; no se deduce de que aparezcan en esta corrida.

## 7. Hashes de cierre

| Fichero de head | SHA-256 de cierre | Coincide con apertura |
|---|---|---|
| core/verificar_apertura.py | 3fc983fcd00f342b712175aeb083fa1c814742f1811c96044dcf699db8f40687 | SÍ |
| scripts/verificar_apertura.py | e65bd09a3c1c337fee4f93ae6c43e438dee9e1ca92843789e543a1eb97dbd521 | SÍ |
| tests/test_verificar_apertura.py | e959e47d41b0d3a9afcc06661561340bff5df850bb77f4fb9892e77887929803 | SÍ |

**Los tres pares coinciden.** La comprobación es de bytes SHA-256; no solo de fecha o tamaño.

La evidencia aconseja no integrar esta pieza como verificador fiable del resultado del expediente hasta corregir los falsos verdes y la guarda. La adjudicación de cada hallazgo y del remedio corresponde al autor contra la fuente.

VEREDICTO: NO-SHIP
<!-- informe-literal:fin:p2r1 -->

## 2. Evidencia verificada por mí, contra la fuente

La adjudicación razonada, hallazgo a hallazgo, vive en el §7 del plan hermano, que es el documento
que la decisión modificó. Aquí va la voz literal del revisor y nada más.
