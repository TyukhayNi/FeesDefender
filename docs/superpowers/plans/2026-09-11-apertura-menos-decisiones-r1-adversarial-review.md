---
tipo: revision-adversarial
objeto: diff c3fdffa..038a034 — el generador de viabilidad marca las 88 filas (render_informe.py)
objeto_rev: "1"
commit: 038a034
ronda: "1"
revisor: Codex
veredicto: LISTA-CON-CAMBIOS
marcador_nonce: p5v8
sha256_informe: 67a74a234a8a9928d0d71daa7b2e7e121df34dd4b33cd5d4bc9a015424820f8f
adjudicado_en: docs/superpowers/plans/2026-09-11-apertura-menos-decisiones.md §3
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# Acta de revisión adversarial R1 — el generador de viabilidad y las 88 filas

- **Objeto revisado:** diff `c3fdffa..038a034` — `render_informe.py`, `SKILL.md`, `CHANGELOG.md` y `tests/test_render_informe_viabilidad.py`
- **Ronda:** R1 (única; radio de daño = no escribe en el CRM ni destruye datos del expediente)
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` sin `.git`, solo lectura
- **Informe recibido:** 2026-09-11, `C:/t/rev-p5-viabilidad-080800/wd/INFORME.md`, 25684 bytes
- **Hallazgos:** 5 numerados + 4 en el apartado B — 9 confirmados, 0 refutados
- **Remediado en:** `docs/superpowers/plans/2026-09-11-apertura-menos-decisiones.md` §3

**Por qué existe esta acta.** Yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**. La adjudicación —qué
acepté, cómo lo comprobé contra la fuente y dónde se remedia— vive en el §3 del plan, que es el
documento que la decisión modificó. Aquí va la voz literal del revisor y nada más.

**Custodia.** El objeto se le dio como dos árboles `git archive` sin `.git`, en un directorio de
ronda con nombre irrepetible (`rev-p5-viabilidad-080800`) comprobado **vacío** antes de lanzar. Los
`sha256` de los dos ficheros revisados coinciden al abrir y al cerrar, y el revisor los declara en
su §1 y §6.

**El digest se computó con la ronda ya terminada.** La señal de fin es la salida del proceso, no la
existencia del `INFORME.md`: se midió el hash del informe **dos veces con 20 s de separación
mientras el revisor seguía escribiendo** y salió distinto (`e7512be3…` y luego `705f519d…`). Sin esa
comprobación se habría archivado un informe truncado como voz literal del revisor, con un digest
internamente coherente y falso — exactamente la garantía que el acta existe para dar. El valor
final se tomó tras el `exit 0` del proceso. El `sha256` del fichero crudo es
`705f519d37fbb23dc970ef4346e2ebe667a0833a7bcc041868979e0e4aa3d83d`.

**Por qué el bloque literal archiva DOS textos.** Mi mandato pidió el veredicto de un set que me
inventé (`SHIP` / `SHIP-CON-REPAROS` / `NO-SHIP`) en vez del set cerrado de este repositorio, así
que el informe terminó con una palabra que el guard G9 no admite. **Rellenarla yo, traduciendo la
suya a la de la casa, es justo lo que el acta existe para hacer imposible.** Se hizo una segunda
llamada al revisor —con instrucción expresa de no reatacar el objeto ni tocar el informe— que
devolvió `VEREDICTO.md`; se comprobó por hash que el `INFORME.md` quedó intacto. Los dos textos van
dentro del bloque, separados por una raya, y esta explicación va **fuera**. El error es mío y se
apunta para el próximo mandato: el set de veredictos lo fija `tests/test_docs_gobernanza.py`, no el
que redacta el encargo.

**Higiene del workdir.** El revisor declaró en su primera línea que encontró un `_stdout.log` y que
no lo leyó. También declaró que no pudo borrar sus directorios de trabajo `scratch/` y `tmp/` —su
herramienta se lo bloqueó— y **no afirmó haberlo hecho**, que es la conducta correcta.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:p5v8 -->
HIGIENE: al abrir el workdir había `MANDATO.md` y un fichero adicional, `_stdout.log`; no he leído este último.

# Informe R1 — viabilidad, comparación base/head

## 1. Hashes de apertura

SHA-256 calculados sobre los bytes de los originales, antes de ejecutar las pruebas:

| Fichero en `../head/` | SHA-256 |
|---|---|
| `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py` | `da527302b1670493989d1848f08cc2c5138a327e118178d9db04ad84e3fc45f9` |
| `tests/test_render_informe_viabilidad.py` | `ad47f0aeed0a86d4180ce0eafd9fe9e3c7875e91bd1988dca68fdefd43aea39e` |

La revisión se interpreta como auditoría de exactitud y completitud. No se han escrito cambios en `base` ni en `head`. Se aplicó la excepción expresa de §4 para crear copias y temporales en el workdir, frente a la prohibición general de otros ficheros; se anunció esta interpretación. El único entregable es este informe; el log preexistente se conserva sin leerlo. **Incidencia de cierre:** la revisión automática rechazó la eliminación de `wd/scratch` y `wd/tmp`, primero con comprobación de contención y después con rutas absolutas literales verificadas. El motivo devuelto fue únicamente «blocked by policy». Por tanto, esas dos carpetas temporales permanecen en el workdir; no se afirma haber cumplido su limpieza.

## 2. Hallazgos

### H-01 — MEDIO — El nuevo ejemplo excluye una pregunta testifical del caso que ejemplifica

**Anclas:** `../head/.claude/skills/viabilidad-prerelleno/SKILL.md:78`, `:85`, `:117`, `:132`; `../head/.claude/skills/viabilidad-prerelleno/references/cuestionario_viabilidad.yaml:691`; `../head/.claude/skills/viabilidad-prerelleno/scripts/render_informe.py:190`.

El ejemplo sigue siendo un caso `VUELTA`, pero cambia `vue_01` de `{"pendiente":"sí"}` a `{"pendiente":"no"}`. La pregunta es «¿Sabes si intervino otra agencia?» y su `clase_fuente` es `testifical`. El ejemplo no aporta respuesta, cita ni explicación de una exclusión. Esto contradice el criterio operativo de dejar pendiente lo testifical no resuelto y la indicación de que VUELTA activa precisamente esa sección.

**Escenario reproducido:** extraer con `json.loads` el bloque JSON de la skill y pasarlo al `main()` de head → `vue_01` queda con **I vacía y M = `no`**. Si el modelo reutiliza ese ejemplo para una VUELTA sin información sobre otra agencia, esa pregunta desaparece del guion. El código obedece exactamente la excepción explícita; el problema está en enseñarla con una pregunta relevante sin justificar su exclusión.

**Remedio:** omitir `vue_01` en ese ejemplo, o utilizar un supuesto explicado de exclusión. No suprimir la prioridad del `pendiente` explícito, que sí forma parte del contrato.

### H-02 — MEDIO — La garantía de dominio y exhaustividad no alcanza al `pendiente` explícito

**Anclas:** `../head/.claude/skills/viabilidad-prerelleno/scripts/render_informe.py:190`; `../head/tests/test_render_informe_viabilidad.py:168`; `../head/.claude/skills/viabilidad-prerelleno/CHANGELOG.md:9`.

Los valores derivados sí son `sí`/`no`, pero un `pendiente` explícito distinto de `None` se escribe sin validarlo. Esta tolerancia **ya existía en base**: no es una regresión introducida por el recorrido. Sí limita la afirmación 5 y la amplitud atribuida al nuevo test.

**Escenarios ejecutados, con guardado y relectura del XLSX:**

| Entrada `preguntas.cap_01` | Resultado en M6 |
|---|---|
| `{"pendiente":"SÍ"}` | `SÍ`, fuera de la lista literal |
| `{"pendiente":true}` | booleano `True`, fuera de la lista |
| `{"pendiente":"pendiente"}` | `pendiente`, fuera de la lista |
| `{"pendiente":""}` | celda vacía al releer; solo **87/88** preguntas marcadas |

La validación real es `list`, `M6:M103`, fórmula `"sí,no"`, **`allowBlank=True` y `showErrorMessage=False`**. No cabe atribuir a la plantilla una barrera que haga válido ese dato antes de filtrar el guion.

El test de dominio solo recibe respuestas documentales sin `pendiente` explícito. Muté en memoria el generador para escribir `FUERA_DOMINIO` ante cualquier `pendiente` explícito: **ese test siguió verde, 1 passed**. Los tests de prioridad sí detectarían esa mutación para sus dos valores concretos, pero no prueban el tratamiento de entradas explícitas inválidas.

**Remedio:** acotar la garantía a los valores derivados y a entradas válidas, o definir y probar rechazo/normalización de valores explícitos inválidos. Mantener la prioridad de `sí`/`no` válidos.

### H-03 — BAJO — El control positivo documentado no coincide con la ejecución

**Anclas:** `../head/.claude/skills/viabilidad-prerelleno/CHANGELOG.md:19`; `../head/tests/test_render_informe_viabilidad.py:182`; comandos de §3.C.

El changelog dice «2 de ellos rojos antes del arreglo». Ejecutando **el fichero completo de ocho tests de head contra base**, con ambas semillas, el resultado es **3 failed, 5 passed**.

El tercero es `test_las_marcas_caben_en_la_validacion_de_la_columna`: falla por `{None}` fuera del conjunto `{'sí','no'}`. No detecta un literal incorrecto que el código viejo haya escrito; detecta las 85 marcas ausentes. La validación de Excel permite blancos. Por tanto, ese rojo también acredita exhaustividad, pero no demuestra por sí solo que se haya ensayado un literal inválido emitido por el generador.

**Consecuencia concreta:** archivar «2 rojos» como medición del fichero final archiva un resultado que no se reproduce. Los cinco verdes restantes tampoco deben presentarse como detectores del arreglo; su utilidad como protección de comportamientos anteriores se comprobó por separado.

**Remedio:** actualizar el conteo a tres y distinguir los tests del arreglo de los de conservación de comportamiento.

### H-04 — BAJO — El objeto contiene tres cambios documentales adicionales a los declarados

**Anclas:** comparación recursiva por contenido de los 1.288 ficheros de base y 1.289 de head; `../head/PLAN.md:45`, `:85`; `../head/docs/INDICE.md:99`; `../head/docs/superpowers/handoffs/handoff-2026-09-10-consulta-apertura-menos-decisiones.md:3`, `:253`.

Además de los cinco ficheros anunciados, cambian:

- `PLAN.md`: promoción de P5/P7/P2 y bloque de planificación.
- `docs/INDICE.md`: cambio del estado del handoff a consumido.
- `docs/superpowers/handoffs/handoff-2026-09-10-consulta-apertura-menos-decisiones.md`: estado consumido, destino y desglose de promociones.

**Escenario:** integrar la diferencia completa creyendo que consta solo de los cinco ficheros de §1 también incorpora esas promociones de estado. Los cambios adicionales son prosa, no se encontró otro código modificado, y sus referencias de promoción concuerdan entre sí. No he verificado que las decisiones históricas atribuidas a Nikolai ocurrieran.

**Remedio:** declarar los ocho ficheros en el alcance. La ausencia de `.git` no permite explicar los extras mediante genealogía o commits supuestos.

### H-05 — NOTA — «Siempre en tmp_path» es cierto para las rutas explícitas, no para toda la escritura indirecta

**Anclas:** `../head/tests/test_render_informe_viabilidad.py:12`, `:38`, `:40`; `../head/.claude/skills/viabilidad-prerelleno/scripts/render_informe.py:220`; sonda `sys.addaudithook` durante `test_pendiente_explicito_del_json_manda`.

El test escribe explícitamente `datos.json` y el XLSX bajo su `tmp_path`. No escribe explícitamente ningún fichero en producción. Sin embargo, al guardar, openpyxl crea **cuatro ficheros `openpyxl.*` fuera de ese `tmp_path`**, en el directorio temporal del proceso. La sonda observó esos cuatro nombres bajo `wd/scratch/system_tmp/`; el test terminó con **1 passed**.

**Escenario:** correr sin redirigir el temporal del proceso → los XML intermedios se crean en el temporal del sistema, no en `tmp_path`. Eso no equivale a escribir en el árbol de producción, pero refuta la frase literal de aislamiento absoluto. En esta revisión `TEMP`/`TMP` o `tempfile.tempdir` se dirigieron al scratch; se desactivaron bytecode y caché de pytest.

**Remedio:** precisar la docstring, o aislar también el temporal del serializador si la casa exige literalmente que toda escritura pertenezca al `tmp_path` del test.

## 3. Dictamen por apartados del mandato

### A. Exactitud de las seis afirmaciones

| Nº | Dictamen | Evidencia y límite |
|---|---|---|
| 1 | **Exacta para valores explícitos distintos de `null`.** | `render_informe.py:190`: solo deriva si `pend is None`. Los dos casos del test de prioridad pasan; `null` deriva, `""` gana y deja M vacía. No hay validación del valor explícito: H-02. |
| 2 | **Exacta en ejecuciones que llegan al bloque.** | `render_informe.py:180` conserva texto y destino stderr. El test de desconocido pasa en ambas versiones. Ahora todos esos avisos preceden a las escrituras; antes se intercalaban. |
| 3 | **Exacta para la plantilla entregada.** | `render_informe.py:77` escanea C desde fila 5; las 11 cabeceras tienen C vacía/no-ancla. El test pasa. El helper no reconoce semánticamente una pregunta: cualquier C verdadera se incorpora. |
| 4 | **Exacta: marcar por omisión no inventa I.** | `render_informe.py:185` solo escribe I cuando el JSON aporta `respuesta` distinta de `None`. Test y mutación de invención verificados. No promete borrar respuestas anteriores de otra plantilla. |
| 5 | **Exacta para los dos literales derivados; falsa como garantía sobre todas las escrituras.** | `render_informe.py:192` deriva `no`/`sí`, coincidentes con la lista medida. El explícito se escribe directamente: H-02. |
| 6 | **Exacta en ambas partes.** | Medición independiente: 88 filas con ID y 88 IDs únicos; INFORMACION combina `E21:H21`, frente a `E22:F22` + `G22:H22`. Ver E. |

La plantilla usada, idéntica en base/head, tiene SHA-256:

`fd04c997be7281380fae39f31c57dd04eea447cab80961509614e0c8a4500f98`

Se midió con `openpyxl.load_workbook`, contando directamente las C no vacías desde fila 5 y agrupando sus IDs normalizados, sin usar el helper como único oráculo. Resultado: **88 filas, 88 IDs únicos, ningún duplicado, max_row 103**. Las filas sin pregunta son **5, 29, 32, 44, 54, 58, 66, 83, 89, 91 y 97**. En las 88 preguntas, **I/J/K/M están inicialmente vacías y ninguna de esas celdas es una `MergedCell` no-ancla**.

### B. Regresión y límites del recorrido

**Orden.** Base escribe en orden de las claves del JSON; head en el orden del mapa de la plantilla. Sonda sobre el bloque original de preguntas, con `cap_02` antes de `cap_01` y registro del setter de I:

```text
WRITE_ORDER_I base ['I7', 'I6']
WRITE_ORDER_I head ['I6', 'I7']
```

Con IDs únicos y destinos distintos no cambia el resultado final. Sí cambia el diagnóstico ante error: para `{"cap_01":"mal","unknown":{}}`, base lanza `AttributeError` sin avisar de `unknown`; head avisa de `unknown` antes del mismo error. El guardado sigue al final (`render_informe.py:220`), pero la copia de la plantilla ya se creó en `:115`; un error no guarda las escrituras parciales en memoria y puede dejar esa copia inicial en la ruta de salida. Este mecanismo de copia previo no es nuevo.

**Valores que no son diccionario.** La diferencia real está en `respuestas.get(qid) or {}` (`head:184`), no en una comprobación de tipo:

| `preguntas.cap_01` | Base | Head |
|---|---|---|
| `null`, `""`, `0`, `false`, `[]` | `AttributeError` al llamar `.get` | Acepta silenciosamente como `{}`; I vacía, M `sí`, salida con 88 marcas |
| `"texto"`, `7`, `[1]` | `AttributeError` | `AttributeError` |
| `{}` | M `sí` para esa pregunta | M `sí` para esa pregunta y las omitidas |

Es un cambio de tolerancia no documentado ni cubierto. Por ejemplo, un productor que emita por error `cap_01:false` en lugar de `cap_01:{"respuesta":false}` pasa de fallar a generar un informe sin esa respuesta. No se confunda con `respuesta:false` o `respuesta:0` dentro de un objeto: ambos se conservan y derivan M `no`, antes y después.

**Valores previos en una plantilla alternativa.** Sonda sobre una copia en memoria con I6=`previa`, J6=`fuente`, K6=`alta`, M6=`no`, y `preguntas` omitido:

```text
base: ['previa', 'fuente', 'alta', 'no']
head: ['previa', 'fuente', 'alta', 'sí']
```

Head conserva I/J/K, pero recalcula M exclusivamente desde el JSON, sin considerar I preexistente ni preservar M. Puede quedar una respuesta presente con una decisión anterior de entrevista sustituida. Es una diferencia observable con `--plantilla`, no un fallo medido en el asset canónico, que está vacío. Si la pregunta ya figuraba como `{}` en el JSON, ambas versiones hacían esa misma sustitución. Para preguntas incluidas, los predicados de I/J/K no cambian: `None` no borra I/J; cadena vacía sí se escribe en I/J; confianza vacía no borra K.

**Celdas combinadas.** La escritura directa ya existía para I/J/K/M. `set_cell` (`:68`) detecta una no-ancla, avisa y salta; `.cell(...).value = ...` lanza `AttributeError`. El recorrido nuevo amplía ese riesgo a las M de preguntas omitidas. Sonda: combinar `L6:M6` en una copia y usar JSON vacío → **base termina; head falla con `'MergedCell' object attribute 'value' is read-only`**. La misma escritura con `set_cell(...,'M6','sí')` avisa y no lanza. Las combinaciones reales de PREGUNTAS son títulos y cabeceras excluidos del mapa, por lo que este caso no afecta al asset actual. Para I/J/K de una pregunta omitida no se intenta escribir ningún valor.

**IDs duplicados.** Un `dict` no devuelve dos entradas con la misma clave: `m[str(idq).strip()] = r` (`:83`) conserva **la última fila**, sin aviso; la posición de iteración de la clave corresponde a su primera inserción. También colisionan IDs que solo difieren en espacios exteriores. Sonda: sustituir C7 por `cap_01` → mapa de **87** entradas; en head con JSON vacío, **M6 queda vacía y M7=`sí`**. El helper no ha cambiado y la plantilla entregada no tiene duplicados. La promesa general «cuestionario entero» depende de esa unicidad, que no se valida explícitamente.

### C. Ejecución y control positivo de cada test

Se copiaron los árboles completos a `wd/scratch/head` y `wd/scratch/base`. Solo en la copia de base se añadió el fichero de tests de head. Se conservaron `conftest.py`, la barrera de la casa y `pyproject.toml`. No se desactivaron fixtures. Los mutantes posteriores se compilaron exclusivamente en memoria, precargando `render_informe` en `sys.modules`.

Intérprete: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`, **Python 3.14.4**, pytest **9.1.1**, pytest-randomly **5.0.0**. Se ejecutó en serie, con `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` y carga explícita de randomly. Comando, repetido para `ARBOL=head/base` y `SEMILLA=777/31337`, desde el workdir:

```text
python.exe -B -m pytest scratch/ARBOL/tests/test_render_informe_viabilidad.py
  -c scratch/ARBOL/pyproject.toml -p no:cacheprovider -p randomly
  --randomly-seed=SEMILLA --basetemp=tmp/retry_ARBOL_SEMILLA -v --tb=short
```

| Árbol | Semilla | Resultado efectivo | Código |
|---|---:|---|---:|
| head | 777 | 8 passed, 7,90 s | 0 |
| head | 31337 | 8 passed, 7,67 s | 0 |
| base + tests head | 777 | 3 failed, 5 passed, 15,09 s | 1 |
| base + tests head | 31337 | 3 failed, 5 passed, 13,75 s | 1 |

Incidencia del montaje, no del objeto: las tres primeras corridas de la primera tanda dieron errores de setup porque aún no existía el padre `wd/tmp` de `--basetemp=tmp/...`. Se creó ese directorio y se repitieron las cuatro combinaciones. No se contabilizan esos errores como tests rojos del código. La cuarta corrida inicial de base también llegó a producir 3 failed/5 passed.

En la tabla siguiente los nombres llevan el prefijo común `test_` y las anclas corresponden a `../head/tests/test_render_informe_viabilidad.py`:

| Test | Línea | Head, ambas semillas | Base, ambas semillas | ¿Se ha visto rojo por una causa pertinente? |
|---|---:|---|---|---|
| `la_plantilla_declara_88_preguntas` | 58 | Verde | **Verde** | Sí: mutante del mapa que elimina `cap_01` → aserto 87 != 88, 1 failed. |
| `las_88_filas_salen_marcadas` | 82 | Verde | **Rojo** | Sí: base deja 85 de 88 sin M. |
| `las_no_respondidas_van_al_guion_y_las_respondidas_no` | 97 | Verde | **Rojo** | Sí: en base el resto es `{None}`, no `{'sí'}`. |
| `no_inventa_respuestas_al_marcar` | 109 | Verde | **Verde** | Sí: mutante que escribe `inventada` en I de omitidas → 1 failed. |
| `las_filas_de_seccion_no_se_manchan` | 123 | Verde | **Verde** | Sí: mutante que descombina B5:M5 y escribe M5=`sí` → `manchadas=[5]`, 1 failed. |
| `pendiente_explicito_del_json_manda` | 137 | Verde | **Verde** | Sí: mutante que siempre deriva ignorando el explícito → 1 failed. |
| `una_pregunta_ajena_al_cuestionario_sigue_avisando` | 160 | Verde | **Verde** | Sí: suprimir solo el aviso → 1 failed. |
| `las_marcas_caben_en_la_validacion_de_la_columna` | 168 | Verde | **Rojo** | Sí: base falla por blancos; además, el mutante de explícitos inválidos **sobrevive a este test** (H-02). |

**Los cinco verdes en base no prueban el arreglo.** Sí sirven como tests de conservación y ninguno ha resultado incapaz de ponerse rojo. En particular, «no inventa» ya pasaba cuando ni siquiera se marcaban las omitidas: eso es conservación de una propiedad, no evidencia del marcado nuevo. El test de dominio tiene el matiz de H-03. No se observó otro verde que necesitara una explicación distinta de la propiedad acotada que comprueba.

El conteo de 88 usa el helper del propio generador: comprueba entradas únicas del mapa, no por sí solo el número físico de preguntas. La medición independiente de A evita dar ese supuesto por demostrado solo mediante el test.

### D. Prosa e instrucciones al modelo

`SKILL.md:85` y `:142` describen correctamente la posibilidad de omitir preguntas: con el asset entregado y sin override salen con M=`sí`. La excepción explícita también está documentada y funciona. El script no usa `clase_fuente` ni `tipo_caso` para decidir M; esa selección sigue siendo responsabilidad de quien prepara el JSON.

La contradicción operativa concreta es el ejemplo VUELTA de H-01. La frase del changelog «van solo las que se resuelven» (`:14`) también omite en su resumen las excepciones que sí admite la skill; su propio ejemplo incluye una de ellas. La garantía de «toda pregunta sin respuesta» debe leerse con la excepción del explícito y las condiciones del mapa, no como aserto universal: H-02 y B.

La derivación solo considera sin respuesta `None`, `""` y el literal exacto `"pendiente"`. Se verificó que `respuesta:"PENDIENTE"` y `respuesta:" "` producen M=`no`; `respuesta:"pendiente"` produce I=`pendiente`, M=`sí`. Esto ya ocurría en base. No es invención de respuesta por el nuevo marcado: el literal procede del JSON. La skill no especifica un protocolo adicional de normalización que el script implemente.

### E. Semáforo excluido — MEJORAS #228

**La premisa material es real.** Se abrió el XLSX original y se midió:

| Elemento | Resultado |
|---|---|
| Combinaciones de valores, fila 21 | `E21:H21` |
| Combinaciones de valores, fila 22 | `E22:F22`, `G22:H22` |
| Bloques de etiquetas | `B21:D21`, `B22:D22` |
| Validación de INFORMACION | Solo `E21`, lista `"verde,amarillo,rojo"` |
| Formato condicional de INFORMACION | Solo `E21:H21`, tres reglas: `$E$21="verde"`, `$E$21="amarillo"`, `$E$21="rojo"` |
| Validaciones totales | Seis: una en INFORMACION, dos en PREGUNTAS, tres en AVISOS LLM |
| Protección de PREGUNTAS | `sheet=True` |

Coincide con `docs/MEJORAS_FUTURAS.md:10738` y `CHANGELOG.md:20`. La diferencia puede justificar separar el trabajo y su verificación de plantilla. **No acredita imposibilidad técnica de ampliar la validación y el formato sin cambiar los merges:** `E22:H22` existe como rango aunque no como un único bloque combinado, y el propio backlog contempla cubrir ambos bloques con ese rango. Por ello no considero inventada la razón, pero tampoco considero demostrado que sea imprescindible rediseñar el layout. No se ha ensayado un arreglo del semáforo ni se atribuyen intenciones al autor.

## 4. Inventario de lo NO cubierto por los tests nuevos

La cobertura no es completa. Distingo cambios del diff de fronteras anteriores que el nuevo recorrido vuelve relevantes:

| Cambio o frontera | Qué falta comprobar en el fichero de tests |
|---|---|
| Recorrer el mapa aun sin respuestas | JSON sin clave `preguntas`, `preguntas:null` y `{}`; el caso de solo ID desconocido se ejecuta, pero su test no inspecciona las 88 marcas de salida. |
| Normalizar `ans` mediante `or {}` | Diferencia entre `null`, cadena vacía, cero, falso, lista vacía y valores no-dict verdaderos; errores, avisos y salida ante esas entradas. |
| Cambiar orden de iteración y separar avisos | JSON en orden distinto de la plantilla; varios desconocidos mezclados con preguntas válidas/erróneas; orden y exhaustividad de avisos ante fallo. El test actual solo busca un ID en stderr. |
| Escribir M de preguntas antes omitidas | Conservación o reemplazo de valores/fórmulas previos en M y coherencia con I/J/K ya presentes; plantilla alternativa mediante `--plantilla`. |
| Ampliar escrituras directas de M | Pregunta omitida cuya M es una `MergedCell` no-ancla; diferencia frente a `set_cell`. |
| Depender del mapa como universo completo | Duplicados y colisiones tras `strip`, IDs solo de espacios y C no vacía que no sea pregunta. No hay un aserto independiente de unicidad/fila por fila. |
| Prioridad explícita y dominio de M | `pendiente:null`, `""`, booleanos y literales inválidos; que no sobrevivan marcas vacías. El test de dominio no usa overrides. |
| Clasificar «sin respuesta» | Pregunta presente con objeto vacío, respuesta `None`, `""`, `"pendiente"`, espacios, mayúsculas, booleanos y cero. Son ramas antiguas, no cubiertas por este fichero. |
| Mantener las escrituras I/J/K | Valores exactos de las respuestas, citas y confianza; no basta contar los IDs con I no vacía. J/K no se asiertan. |
| Delimitar no-preguntas y validación | El test de sección solo mira M desde fila 5; no compara las demás columnas. El test de validación elige por una coincidencia textual de `M` en `sqref`, sin exigir tipo `list`, rango exacto M6:M103 ni pertenencia de cada destino al rango. |
| Cambiar instrucciones y ejemplo JSON | No se ejecuta el ejemplo de SKILL.md ni se comprueba que las preguntas testificales no resueltas del supuesto permanezcan en el guion. |
| Conservar el artefacto | No se asiertan conjuntamente las seis validaciones, protección, fórmulas, combinaciones ni hojas ajenas al cuestionario. La explicación del semáforo y los cambios documentales adicionales tampoco tienen verificación en este fichero. |
| Aislamiento absoluto declarado | No se interceptan ni redirigen desde el test los temporales internos de openpyxl: H-05. |

Estos huecos no equivalen todos a regresiones presentes. Los escenarios más relevantes se sondearon durante esta revisión, pero **esas sondas no forman parte de la cobertura permanente del diff**.

## 5. Lo que NO se pudo verificar

- **SIN VERIFICAR:** las mediciones históricas de producción 51/88 y 70/88, su fecha y los informes de esos expedientes. Se reprodujo el modo de fallo con 3/88 sobre base, no esos documentos reales.
- **SIN VERIFICAR:** genealogía, commits, PRs y decisiones históricas atribuidas a Nikolai. No hay `.git`; las menciones documentales no sustituyen esa evidencia.
- **SIN VERIFICAR:** uso real del filtro de entrevista por sus consumidores, comportamiento visual de Excel y colores renderizados. Se comprobaron valores, XML/modelo de validación y combinaciones mediante openpyxl, sin abrir Excel.
- **SIN VERIFICAR:** suite completa del repositorio, interacciones con otros módulos bajo xdist, empaquetado/reimportación de la skill y sistema Cowork instalado. Solo se ejecutó el fichero nuevo, sus controles y las sondas descritas.
- **SIN VERIFICAR:** existencia en producción de plantillas alternativas con respuestas previas, IDs duplicados o M combinadas. Esos casos de B se reprodujeron en copias en memoria; no se afirman como incidentes reales.
- No se leyó `_stdout.log`, conforme a §0-ter. No se consultaron expedientes, CRM ni servicios externos.
- **NO COMPLETADO por bloqueo de la herramienta:** retirar las copias y resultados temporales de `scratch/` y `tmp/`. Ambos destinos se verificaron dentro del workdir y sin atributo de enlace antes de intentar su eliminación con `Remove-Item -LiteralPath ... -Recurse -Force`; la revisión automática rechazó la acción. No se intentó sortear el bloqueo con otra herramienta de borrado.

El cambio corrige el fallo objetivo con la plantilla canónica: pasa de 3 a 88 marcas, conserva las respuestas del JSON y respeta los overrides válidos. Recomiendo entrada con reparos: corregir el ejemplo, precisar la evidencia del control positivo y delimitar la garantía de entradas válidas. Las limitaciones heredadas y las plantillas alternativas deben quedar explícitas; no se presentan como fallos nuevos del asset entregado.

## 6. Hashes de cierre

| Fichero en `../head/` | SHA-256 |
|---|---|
| `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py` | `da527302b1670493989d1848f08cc2c5138a327e118178d9db04ad84e3fc45f9` |
| `tests/test_render_informe_viabilidad.py` | `ad47f0aeed0a86d4180ce0eafd9fe9e3c7875e91bd1988dca68fdefd43aea39e` |

Ambos hashes de cierre coinciden con los de apertura. El informe se entrega en UTF-8 sin BOM, con LF y un único salto final; su SHA-256 se comunica por separado.

VEREDICTO: SHIP-CON-REPAROS

---

VEREDICTO: LISTA-CON-CAMBIOS

El informe acredita que el diff corrige el marcado de las 88 filas con la plantilla canónica y recomienda su entrada con reparos identificados. Mantengo ese dictamen: corresponde corregir el ejemplo, precisar la evidencia del control positivo y delimitar la garantía a entradas válidas.
<!-- informe-literal:fin:p5v8 -->

## 2. Evidencia verificada por mí, contra la fuente

Cada hallazgo se comprobó contra el código, la plantilla o `git`, no contra el informe. Lo medido:

| Qué | Cómo se comprobó | Resultado |
|---|---|---|
| H-01: `vue_01` es testifical | `grep` en `references/cuestionario_viabilidad.yaml:691` | `fuente_probable: [entrevista, email]` — **confirmado** |
| H-02: la plantilla no protege | `openpyxl`, inventario de `data_validations` de `PREGUNTAS` | `list "sí,no"` sobre `M6:M103` con `allowBlank=True`, `showErrorMessage=False` — **confirmado** |
| H-02: el agujero real | Se corrió el generador con siete entradas patológicas | `{"pendiente": ""}` → **87 de 88** y «OK»; `"SI"` y `True` se escriben tal cual — **confirmado** |
| H-03: cuántos rojos | Control positivo re-medido con las **dos semillas** (777, 31337) sobre `origin/main` | **18 de 26**, idéntico con las dos — el «2» del CHANGELOG era falso |
| H-04: ficheros de más | `git diff --stat c3fdffa fix/viabilidad-88-filas` | **8 ficheros**, no 5 — **confirmado**; causa: un `git checkout main` fallido con el error silenciado por `2>/dev/null` |
| H-04: remedio | `git rebase --onto origin/main` + `git diff --stat origin/main...HEAD` | **5 ficheros**, los declarados |
| B-4: el test sobrevivía al mutante | Se aceptó la medición del revisor y se reprodujo la carencia leyendo el test | El aserto solo veía valores derivados — **confirmado** |
| Tras remediar | Los tests nuevos contra el código pre-remediación (`git archive 038a034`) | **14 rojos**, uno por causa |

**Lo que NO verifiqué, y por tanto no está verificado:** que las mediciones históricas de
producción (51/88 y 70/88) correspondan a los expedientes que la bitácora nombra — se reprodujo el
*modo de fallo*, no los documentos. Y el comportamiento visual en Excel: todo se midió por el
modelo de openpyxl, sin abrir el fichero.
