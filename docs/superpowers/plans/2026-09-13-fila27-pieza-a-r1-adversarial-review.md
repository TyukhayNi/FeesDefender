---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-13-fila27-pieza-a-custodia-tolerante.md
objeto_rev: "1"
commit: 436f23d
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: wq7z
sha256_informe: 50866d9eea2e21b1d3d3776daa830b2b105ac96e559cafee62243f273c61baa5
adjudicado_en: docs/superpowers/plans/2026-09-13-fila27-pieza-a-custodia-tolerante.md §6
---

# Acta — R1 adversarial sobre el diff de la pieza A de la fila #27 (`MEJORAS #214`)

Objeto: el **diff** `9098731..436f23d` (el commit de construcción de la pieza A), no un
documento. Se archivaron las dos copias `git archive` de base y head y el `DIFF.patch`
resultante; el revisor trabajó sobre ellas, sin `.git` y sin acceso al repositorio real.

| | |
|---|---|
| Revisor | Codex CLI `0.153.4`, binario `7ac07f4ce733f89a`, `model_reasoning_effort=high` |
| Objeto | `C:/t/obj-fila27A-105434/{base,head}` + `DIFF.patch` |
| `sha256` del diff, al abrir y al cerrar | `42415ac9ff7d3402d206e80d522018348198f197052719f4566cf9635bdaa82e` (idéntico; comprobado por las dos partes) |
| `sha256` del informe | `50866d9eea2e21b1d3d3776daa830b2b105ac96e559cafee62243f273c61baa5` — el **fichero crudo y el bloque canonicalizado coinciden**, así que la cadena se verifica contra la salida del revisor y no solo contra sí misma |
| Veredicto | **NO-SHIP** |
| Hallazgos | 12 (3 `ALTO`, 7 `MEDIO`, 2 `BAJO`) — **12 confirmados, 0 refutados** |

**Dos incumplimientos declarados por el propio revisor, y se archivan sin maquillar.** (1) Su
workdir contenía el `_stdout.log` de su propia corrida además del mandato; enumeró el nombre
y declaró no haberlo leído. (2) Un subagente suyo ejecutó dos controles importando
directamente el `head/` del objeto en vez de una copia; lo detectó él, repitió los dos
controles contra copia y dejó constancia de que la repetición **no borra el incumplimiento**.
Recomputó la integridad del objeto después: 1.310 ficheros en base, 1.311 en head, y solo los
seis del patch difieren. Yo verifiqué por mi lado que el `sha256` del `DIFF.patch` no cambió.

**Un límite que es culpa del mandato, no del revisor.** Le pedí controles positivos «distintos
de los 14 mutantes del autor» sin ponerle los 14 dentro del objeto: vivían en un scratchpad
fuera. Declaró esa comparación **SIN VERIFICAR**, que es lo correcto. Remediado: el arnés vive
ahora en `tests/_mutantes_mejoras_214.py`, dentro del repo, con 23 mutantes.

**Y un error del mandato que hubo que normalizar:** ofrecí un set de veredictos con `LISTA`,
que **no existe** en el vocabulario cerrado del contrato (`SHIP` · `LISTA-CON-CAMBIOS` ·
`REQUIERE-REVISION` · `NO-SHIP` · `NO-EJECUTABLE` · `SIN-VEREDICTO`). El revisor devolvió
`NO-SHIP`, que sí pertenece al set, así que no hubo nada que normalizar — pero el defecto del
mandato queda escrito para no repetirlo.

## 0. Mandato, literal

<!-- mandato-literal:inicio:wq7z -->
# Mandato — Revisión adversarial R1 sobre un DIFF (FeesDefender, fila #27 pieza A / `MEJORAS #214`)

## 0. Quién eres y qué se te pide

Eres el **revisor adversarial** de un cambio de código que otro agente (Claude) acaba de
escribir y que todavía **no está mergeado**. Tu trabajo es **auditarlo con hostilidad técnica**
y devolver hallazgos **anclados a línea**. No eres el juez: quien adjudica cada hallazgo contra
la fuente es Claude. Tu valor está en ver lo que el autor no puede ver porque lo escribió él.

**Solo lectura sobre el objeto.** No modifiques `base/` ni `head/`. Si necesitas ejecutar algo,
**copia a tu workdir** y ejecuta la copia. Al terminar te pediré el `sha256` del objeto otra vez.

## 0-bis. Por qué este mandato está redactado como auditoría de completitud

Parte del cambio son **guardas y declaraciones de custodia**. Te pido que dictamines si su
cobertura es **completa y exacta**, y que construyas **controles positivos** (un caso que la
guarda DEBE detectar) para comprobar que el instrumento mide lo que dice medir. Si alguna
petición te sonara a otra cosa, interprétala como auditoría de completitud y dilo.

## 1. El objeto, congelado

| | |
|---|---|
| Base (`main`, commit `9098731`) | `C:/t/obj-fila27A-105434/base/` |
| Head (el cambio, commit `436f23d`) | `C:/t/obj-fila27A-105434/head/` |
| Diff unificado | `C:/t/obj-fila27A-105434/DIFF.patch` |
| `sha256` del diff **al abrir** | `42415ac9ff7d3402d206e80d522018348198f197052719f4566cf9635bdaa82e` |

Son copias extraídas con `git archive`, **sin `.git`**: no puedes usar `git log`/`blame`, y no
puedes acreditar genealogía. Verifica **contenido y hash**, no procedencia.

**Primera tarea, antes de nada:** recomputa el `sha256` del `DIFF.patch` y di si coincide.

## 2. Qué hace el cambio, en una frase (tesis del autor, que tienes que poner a prueba)

El montaje de Google Drive for Desktop renombra ficheros bajo los pies (añade una extensión
inferida del content-type poco después de que `rclone` escriba el nombre pelado).
`hash_tree_local` en `scripts/abrir_caso.py` **listaba y luego abría**, así que moría con
`FileNotFoundError` y tumbaba la etapa `drive` de la secuencia V1. El cambio la hace tolerante y
—esto es lo que el autor dice que importa— **declara lo que no pudo leer** en vez de tragárselo:
*un fichero que no se pudo leer no ha medido cero.*

## 3. Las siete preguntas que tienes que contestar

Para cada una: **ancla a fichero:línea del `head/`** y di si el hallazgo lo verificaste
**ejecutando** o **leyendo**. Un hallazgo que no puedas anclar no lo incluyas.

**P1 — ¿El inventario de huecos está completo?** Recorre `hash_tree_local` y `_reaparecido`
(`head/scripts/abrir_caso.py`) y enumera **todas** las formas en que un fichero del árbol puede
acabar sin hash. ¿Cada una queda declarada en `sin_verificar`, o alguna desaparece en silencio?
Piensa en: enlaces simbólicos, ficheros que aparecen *después* del listado, nombres con
caracteres que Windows rechaza, un directorio que se vuelve fichero, `os.walk` con
`followlinks`, rutas largas (MAX_PATH), y un `root` que es un fichero y no un directorio.

**P2 — ¿La declaración llega ENTERA a sus tres destinos?** El autor afirma que
`sin_verificar` llega (a) al valor de retorno, (b) a los `details` del evento forense de
`_intake_generico`, y (c) al `Pendiente` de `etapa_drive`. Comprueba la cadena **completa**,
incluyendo el camino del pull fallido (`_intake_drive_ev`, bloque `except DriveIntakeError`).
¿Hay algún camino de producción que llame a `hash_tree_local` y **descarte** la declaración?
Busca todos los llamadores en `head/`, incluidos `streamlit_app.py` y `core/`.

**P3 — ¿El criterio del renombrado es correcto?** `_reaparecido` acepta un candidato `q` si
`q.stem == p.name` y `str(q)` no estaba en el listado del directorio. Dictamina: ¿es exacto?
¿Falla en Windows por mayúsculas/minúsculas? ¿Qué pasa si el montaje añade **dos** extensiones,
o si el nombre original ya termina en punto, o si `p.name` contiene caracteres que `stem`
trata de forma especial? ¿Y si hay un directorio que cumple el criterio? **Construye el caso
que lo rompa y ejecútalo**, o di que no lo encontraste.

**P4 — ¿Los tests prueban lo que dicen?** `head/tests/test_hash_tree_tolerante.py` son 23
tests. Para cada uno pregúntate: **¿pasaría también con el código de `base/`?** Si alguno
pasaría con los dos, no prueba el cambio. Y al revés: ¿hay algún aserto que el autor haya
escrito contra su propia implementación en vez de contra la propiedad (p. ej. comprobando el
texto de un `repr()` en vez del hecho)? Señala los tests tautológicos o frágiles.

**P5 — ¿Hay regresión en los llamadores?** `hash_tree_local` cambió de devolver `dict[str,str]`
a devolver `ArbolLocal`. Localiza **todos** los consumidores en `head/` y dictamina si alguno
quedó leyendo el objeto nuevo como si fuera un dict. Mira en especial
`_inventario_desde_hashes`, que hace `(raiz / k).stat().st_size` sobre las claves: ¿puede
petar con una clave renombrada? ¿Y con la misma carrera un nivel más abajo? ¿Y
`core.abrir_caso.reconcile`, recibe algo distinto de antes?

**P6 — ¿Las tres decisiones declaradas por el autor son correctas?** Están en el mensaje del
commit (dentro de `DIFF.patch` no; te las transcribo):
  1. `hash_tree_local` **no** se muda a `core/` porque el guard AST de
     `head/tests/test_abrir_caso_exit_bajo_mutex.py` exige que esté definida en
     `scripts/abrir_caso.py`. **Verifícalo leyendo el guard**: ¿es cierto, o hay una forma de
     mudarla sin debilitarlo?
  2. `Reconciliacion` **no** gana `sin_verificar`/`completa` porque ningún llamador lo leería.
     ¿Hay algún sitio donde su ausencia produzca una afirmación falsa?
  3. El campo nuevo `custodia_sin_verificar` vive en `DriveIntakeResult` (`core/intake_drive.py`)
     pero **lo rellena la custodia, no el pull**. ¿Puede alguien leerlo tras un
     `pull_drive_ev` a pelo y creer que está verificado? ¿Está esa trampa documentada donde
     hace falta?

**P7 — La suite, ejecutada, con las dos semillas.** Copia `head/` a tu workdir y corre:

```
C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest -q --tb=short -p randomly --randomly-seed=777 --basetemp=bt777
```

y lo mismo con `--randomly-seed=31337`. Ese Python de sistema **tiene** `pytest`, `yaml`,
`dotenv`, `typer`, `httpx`, `filelock`, `xdist`, `hypothesis`, `syrupy`, `pytest-randomly`,
`PIL` y `fitz`. Usa `--basetemp` **relativo y corto** dentro de tu workdir (MAX_PATH tumba
tests que están bien, y tu sandbox no puede crear en `C:\t\`). Di el conteo exacto
(recogidos / fallos / errores / skipped) de cada semilla, y si algún rojo es **de plataforma**
y no del cambio, dilo separado.

**Y el control positivo del arnés:** el autor dice haber matado 14 mutantes. Elige **dos**
mutaciones tuyas, distintas de las suyas, que rompan una propiedad que el cambio afirma, y di
si la suite las detecta. Si sobreviven, ese es un hallazgo.

## 4. Formato del informe

Escribe **`INFORME.md`** en tu workdir (`C:/t/rev-fila27A-105434/`). Estructura:

1. **Verificación de integridad**: `sha256` del diff al abrir y al cerrar.
2. **Qué ejecutaste y qué solo leíste.** Sé explícito: lo que no pudiste ejecutar se declara
   **SIN VERIFICAR**, nunca «correcto».
3. **Hallazgos**, numerados `H-01`, `H-02`…, cada uno con: severidad (`ALTO` / `MEDIO` /
   `BAJO`), ancla `fichero:línea`, qué propiedad rompe, **cómo se manifiesta** (un caso
   concreto de entrada → salida incorrecta), y si lo verificaste ejecutando o leyendo.
4. **Inventario de lo NO cubierto** por tu revisión.
5. **Última línea del informe: el veredicto**, exactamente una de estas cuatro palabras:

```
NO-SHIP
REQUIERE-REVISION
LISTA-CON-CAMBIOS
LISTA
```

## 5. Higiene del workdir

Tu directorio de trabajo debe contener **solo este `MANDATO.md`** cuando empieces. Si
encuentras cualquier otro fichero, **no lo leas**: decláralo en la primera línea de tu informe.

## 6. Lo que NO se te pide

No propongas refactorizaciones de estilo, no reescribas el cambio, no toques el repositorio
real (`C:/Users/tnm33/Dev/FeesDefender`) — trabajas solo sobre las copias. Y no ablandes un
hallazgo por cortesía: el autor prefiere un `NO-SHIP` correcto a un `LISTA` amable.
<!-- mandato-literal:fin:wq7z -->

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:wq7z -->
Higiene inicial: el workdir contenía `MANDATO.md` y también `_stdout.log`; enumeré su nombre y NO leí su contenido.

# Revisión adversarial R1 — fila #27, pieza A / MEJORAS #214

Objeto: las copias congeladas `C:/t/obj-fila27A-105434/{base,head}`. Todas las anclas siguientes son relativas a **head/**, salvo indicación expresa. Esta es una auditoría de completitud de la custodia y de sus controles; la adjudicación corresponde a Claude contra la fuente.

## 1. Integridad

- SHA-256 del diff al abrir: `42415ac9ff7d3402d206e80d522018348198f197052719f4566cf9635bdaa82e`. **Coincide** con el mandato.
- SHA-256 del diff al cerrar: `42415ac9ff7d3402d206e80d522018348198f197052719f4566cf9635bdaa82e`. **Coincide** con la apertura y el mandato.
- `integrity.py` aplicó los hunks en memoria, comprobando contexto y líneas eliminadas, y reconstruyó exactamente el texto de los seis archivos afectados. Comparó además los bytes de todos los archivos de ambos árboles: 1.310 en base, 1.311 en head; únicamente difieren los seis archivos del patch. Evidencia: `integrity.json`.
- **Incumplimiento de ejecución sobre el objeto:** el subagente de mutaciones ejecutó los dos controles originales `witness_m1_head.log` y `witness_m2_head.log` importando `C:/t/obj-fila27A-105434/head/scripts/abrir_caso.py` mediante `PYTHONPATH`. No usó una copia en esos dos controles. Esto contradice el mandato, aunque no ordenara escribir allí, y se comunicó al usuario al descubrirlo. Esos dos resultados se sustituyeron como evidencia de control por una repetición del revisor principal con `PYTHONPATH=C:/t/rev-fila27A-105434/p`, `python -B`, confirmación de `cli.__file__` dentro de `p/`, y ambos testigos juntos: **2 passed**, `evidence/witness_copy.log` / `.xml`. La repetición no borra el incumplimiento original.
- Después de descubrirlo se repitió `integrity.py`: siguen siendo 1.310 / 1.311 archivos, únicamente las seis diferencias previstas, los seis hunks reconstruyen HEAD y los hashes coinciden. No se encontraron directorios `__pycache__` en el objeto HEAD. **No se detectó modificación de contenido ni archivos añadidos al objeto**. No se consultó el repositorio real. No se acredita genealogía ni identidad de commits: los hashes y la correspondencia de contenido no prueban procedencia.

## 2. Qué ejecuté y qué solo leí

Python: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`, Windows. Se usaron copias dentro del workdir. El trabajo mecánico de suites, comparación con base y mutaciones se repartió entre subagentes; la lectura de las cadenas de producción, reproducciones principales y revisión final las realizó el revisor principal.

**Ejecutado:** sondas `probes.py`, `probes_extra.py` y `probes_chain.py` contra la copia `p/`; archivos reales, renombrados reales, enlaces simbólicos reales y errores inyectados en puntos delimitados. Resultados completos en los tres `.json` homónimos. Las sondas de eventos conservan el planificador y la reconciliación reales, sustituyen la consulta del catálogo y capturan la llamada al escritor del evento; no necesitan un caso del despacho. El pull se sustituye por un resultado o excepción sintéticos. También se ejecutaron los controles y suites detallados más abajo.

**Solo lectura:** búsqueda de consumidores en todos los `.py` del objeto; `streamlit_app.py`; el guard AST del mutex; DTO, planificador, reconciliación y secuenciador; documentación pertinente. No se accedió a Google Drive, rclone, CRM ni a expedientes reales. La carrera real de Drive for Desktop queda **SIN VERIFICAR**; sí se ejecutaron carreras deterministas equivalentes en sus límites de I/O.

### P7 — suites completas

Se ejecutó la orden pedida desde `s/` para 777 y desde otra copia idéntica `s2/` para 31337, añadiendo únicamente `--junitxml` para conservar el conteo:

```text
C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest -q --tb=short -p randomly --randomly-seed=777 --basetemp=bt777 --junitxml=../artifacts/pytest-777.xml
C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest -q --tb=short -p randomly --randomly-seed=31337 --basetemp=bt31337 --junitxml=../artifacts/pytest-31337.xml
```

| Semilla | Recogidos / casos JUnit | Pasan | Fallos | Errores | Skipped JUnit | Salida |
|---|---:|---:|---:|---:|---:|---:|
| 777 | 5.391 | 4.894 | 373 | 27 | 97 | 1 |
| 31337 | 5.391 | 4.894 | 373 | 27 | 97 | 1 |

En **ambas semillas**, los 97 skipped se desglosan en **91 `pytest.skip` y 6 `pytest.xfail`**. Una ejecución adicional `--collect-only` confirmó **5.391 recogidos en 291 archivos**, salida 0; coincide con el total de casos JUnit. Evidencia: `artifacts/pytest-collect-only.stdout.log`. No se ha sumado xfail dos veces.

**Separación de plataforma/entorno frente al diff:** se volvieron a ejecutar en una copia de BASE los módulos que contenían los rojos de 777: 748 casos, 373 fallos, 27 errores, 2 skipped y 346 pasan. Los **400 identificadores y estados F/E coinciden exactamente** con HEAD 777 y HEAD 31337; el revisor principal volvió a comparar los XML. No hay rojo exclusivo de HEAD entre los observados en estas dos semillas. Esto no refuta los hallazgos: las sondas fuera de la suite sí los reproducen. La reproducción dirigida sobre BASE usó 777; no se afirma haber corrido la suite completa de BASE con las dos semillas.

| Familia de rojos de 777 | Casos F/E | Atribución y evidencia |
|---|---:|---|
| `WorkspaceUnderCatalogRoot`, directo o envuelto en asertos/salidas | 392 | **Entorno del arnés**, no nueva regresión: temporales bajo la copia del proyecto. `core/casos/case_mutex.py:224` y `:234` prohíben esa ubicación; `core/casos/workspace_registry.py:157` hace lo mismo. Se ejecutó un control HEAD con `--basetemp=../bt-control-outside-s`, aún dentro del workdir pero fuera de la copia del proyecto, y pasó. |
| Suposición de disponer de `.git` | 3 | **Archive sin metadata Git**, anunciado por el mandato. `tests/test_gitignore_no_inerte.py:82`, `:134` invocan `git ls-files` / `git check-ignore`. Reproducido en BASE. |
| Suposición de disponer de `.venv` | 2 | **Entorno**, se usa el Python de sistema. `tests/test_session_close_no_pude_medir.py:132`, `:159`. Reproducido en BASE. |
| Otros asertos preexistentes | 3 | Reproducidos en BASE; **causa raíz SIN VERIFICAR**, no se etiquetan como plataforma por intuición. `tests/test_apertura_v1_costuras.py:140` (`--hasta`), `:292` (orden de eventos/estado); `tests/test_workspace_matriz_contractual.py:352` (doble nunca llamado). |

Logs y XML: `artifacts/pytest-777.*`, `artifacts/pytest-31337.*`, `artifacts/pytest-base-targeted-777.*`; control en `artifacts/pytest-head-control-outside-temp.*`. No se instalaron dependencias, fabricó `.git`/`.venv` ni alteraron las guardas para convertir la suite principal en verde. La primera tentativa del arnés no llegó a ejecutar pytest por un error al ubicar los logs; no se cuenta como suite ejecutada.

### P4 — los 23 tests frente a base

Se copiaron los tests nuevos a una copia de base, **sin cambiar producción**: 3 pasan y 20 fallan, en ambas semillas 777 y 31337. HEAD original: 23 pasan con ambas semillas. Para separar la novedad de interfaz de la propiedad, se ejecutó además HEAD sustituyendo únicamente `hash_tree_local` por el cuerpo de BASE y adaptando solo su anotación y sus dos retornos a `ArbolLocal(hashes=resultado_base)`; los otros canales siguen siendo HEAD. Este experimento dio 8 pasan y 15 fallan con ambas semillas. No se presenta este tercer montaje como BASE íntegro. Se leyeron de nuevo los seis XML: todos tienen 23 casos, cero errores y cero skipped.

Todas las anclas de esta tabla son `tests/test_hash_tree_tolerante.py:línea`. P/F significa pasa/falla **ejecutado**. Artefactos y método detallados en `p4.md`.

| Test y línea | BASE literal | Hash BASE + adaptador, resto HEAD | Qué acredita respecto al cambio |
|---|---|---|---|
| A1 `:86` | F | F | Recuperación de nombre efectivo |
| A2 `:100` | F | F | Registro del renombrado |
| A3 `:111` | F | F | Bytes del candidato recuperado |
| A4 `:124` | F | F | Exclusión de un candidato preexistente con igual capitalización; H-01 no cubierto |
| A5 `:142` | F | F | Declaración de una desaparición |
| A6 `:156` | F | F | Declaración de PermissionError al leer |
| A7 `:180` | F | F | Ambigüedad entre dos candidatos |
| A8 `:201` | F | F | Error de enumeración de subdirectorio |
| A9 `:231` | F | P | Propiedad antigua; el fallo literal es de interfaz |
| A10 `:246` | F | P | Propiedad antigua de raíz ausente; fallo literal de interfaz |
| A11 `:257` | F | F | Exclusión por protocolo efectivo y registro del renombrado |
| A11b `:283` | F | F | Recuperación de candidato no protocolo |
| A12 `:297` | F | P | Exclusión antigua por ubicación; fallo literal de interfaz |
| A13 `:327` | F | P | Canal nuevo al evento, sustituye recorrido y plan; oculta H-02 |
| A14 `:348` | P | P | Ya pasaba antes: ausencia de campos de incidencia en evento limpio |
| A15 `:362` | F | P | Canal nuevo al pendiente con incidencia ya inyectada en DTO |
| A16 `:382` | P | P | Ya pasaba antes: etapa limpia sin pendiente |
| A17 `:398` | P | P | Secuenciador ya propagaba pendientes; no ejerce el hash ni el intake |
| A18 `:414` | F | F | Evento del pull fallido; motivo esperado tautológico |
| A19 `:447` | F | F | Adjuntar incidencia al retorno exitoso; plan ficticio |
| A20 `:484` | F | F | Fallo al releer directorio |
| A21 `:505` | F | F | Fallo al abrir candidato efectivo |
| A22 `:531` | F | F | Error `scandir` de la raíz, posterior al filtro `is_dir` |

Por tanto A14/A16/A17 no distinguen el diff de BASE literal; A9/A10/A12 tampoco distinguen la propiedad una vez adaptada la interfaz. Son pruebas de no regresión, no evidencia independiente de la nueva tolerancia. A13/A15 sí prueban canales nuevos, aunque pasar con el hash antiguo es esperable por sus dobles. Los 23 tests no son 23 controles independientes del arreglo.

Fragilidad adicional: A6 `:173` y A8 `:224` buscan `Permission` en el motivo; A7 `:191` exige `ambig`; A20 `:501` exige `releer`. Los dos primeros fijan una representación textual del error, los otros el diagnóstico actual. Pueden fallar con una representación informativa distinta y también aceptar un texto decorativo que contenga esas palabras; no sustituyen la comprobación de causa y conservación del motivo. A18 `:443` es más grave: copia el motivo observado a la expectativa, por lo que cualquier valor —incluso vacío— satisface ese componente. La explicación de A11b `:284` tampoco es exacta: A11 ya exige el par de renombrado en `:277`, así que no pasaría intacto si se suprime toda adopción. No califico por ello A11b de test inútil.

### P7 — controles positivos propios

Se eligieron dos transformaciones propias, cada una de una sola línea, en copias independientes `m1/` y `m2/`. Se conservaron los diffs en `evidence/m1.diff` y `evidence/m2.diff` y se comprobó que correspondían únicamente a las sustituciones previstas.

| Control | Mutación y ancla HEAD | 23 tests nuevos, semilla 777 | Suite completa, semilla 777 | Testigo independiente |
|---|---|---|---|---|
| M1 | `scripts/abrir_caso.py:179`: `tuple(sin_verificar)` → `tuple(sin_verificar[:1])` | 23 pasan; sobrevive | Sobrevive: 0 diferencias de estado F/E/S frente a HEAD | HEAD pasa; M1 falla porque falta `b.pdf` |
| M2 | `scripts/abrir_caso.py:339`: `motivo: f.motivo` → `motivo: ""`, solo en rescate del pull fallido | 23 pasan; sobrevive | Sobrevive: 0 diferencias de estado F/E/S frente a HEAD | HEAD pasa; M2 falla porque se pierde el motivo |

Los JUnit de HEAD, M1 y M2 tienen 5.391 casos, 373 fallos, 27 errores y 97 skipped. **No se ha confundido el código de salida rojo del entorno con matar un mutante:** coinciden exactamente los 400 casos de fallo/error, y también los 97 skipped. El revisor principal volvió a comparar los 400 estados F/E por identificador contra HEAD y BASE; cero diferencias.

Los testigos `evidence/witness_m1.py` y `evidence/witness_m2.py` permanecieron fuera de `tests/` de las copias y se invocaron aparte, por ruta explícita. Se inspeccionaron sus salidas: cada mutante falla por la aserción prevista. Tras detectar el incumplimiento indicado en §1, el revisor principal repitió los dos controles contra la copia no mutada `p/`, con resultado **2 passed**; esta repetición es la evidencia de control HEAD utilizada aquí. La segunda prueba fija el motivo de entrada y comprueba su conservación; no deriva la expectativa de la salida. Métodos, órdenes, logs y XML: `mutations.md` y `evidence/`.

**Límite de lo acreditado:** ambas mutaciones son propias y distintas entre sí. El objeto no contiene las definiciones de los 14 mutantes de **#214** atribuidos al autor; se solicitó esa lista y no se aportó durante la revisión. El inventario M01–M14 de `tests/_mutantes_mejoras_136.py` es de **#136**, ajeno a esta pieza. Por ello la condición adicional «distintas de las 14 del autor» y la cifra histórica de muertes quedan **SIN VERIFICAR**. No se inventa esa comparación.

## 3. Hallazgos

### H-01 — ALTO — Un candidato preexistente cambia de mayúsculas y se adopta como otro documento

**Anclas:** `scripts/abrir_caso.py:140`, `scripts/abrir_caso.py:200`, `scripts/abrir_caso.py:162`.

**Propiedad rota:** no adoptar un fichero ya listado ni inventar la identidad del desaparecido. `listadas` contiene cadenas y se compara con cadenas, aunque el sistema de archivos de Windows identifica esos nombres sin distinguir mayúsculas.

**Entrada → salida:** directorio con `x` (bytes `ORIGINAL`) y `X.PDF` (bytes `OTHER`). Al intentar hashear `x`, se elimina `x` y se cambia únicamente la capitalización de `X.PDF` a `x.pdf`. Se devuelve el hash de `OTHER` bajo **dos claves**, `01_Drive EV/X.PDF` y `01_Drive EV/x.pdf`, `renombrados=((.../x,.../x.pdf),)` y `sin_verificar=()`. Se ha perdido el documento original y se afirma que reapareció, sin prueba de ello. La exclusión del candidato preexistente se incumple.

**Verificación:** **EJECUTANDO**, `probes.json`, caso `case_existing`; renombrado real en Windows. No depende de una simulación de la comparación de paths.

### H-02 — ALTO — La declaración no llega al ledger cuando no hay depositables

**Anclas:** `scripts/abrir_caso.py:290`, `scripts/abrir_caso.py:293`, `core/abrir_caso.py:165`, `core/abrir_caso.py:169`.

**Propiedad rota:** declarar en el evento lo no verificado, también cuando ningún fichero se pudo leer. La construcción de `details` está dentro de `if plan.con_sha`.

**Entrada → salida:** `_intake_generico(..., hashes={}, sin_verificar=(FicheroSinVerificar(...),), dry_run=False)` con planificador real. Imprime el aviso, `reconcile` da `ok=True` y **no se llama a `append_event`**. Tampoco se registra una incidencia si todos los hashes legibles son duplicados ya presentes en el log o corresponden a archivos de cero bytes: `con_sha` queda vacío por definición. Se ejecutaron las tres entradas y también la cadena `etapa_drive → _intake_drive_ev → _intake_generico` con un único fichero ilegible: devuelve «hecha» con pendiente, pero ningún evento.

**Verificación:** **EJECUTANDO + LEYENDO**, `probes.json`, `only_gap_event=[]` y `reconcile_empty`; `probes_chain.json`, `duplicate`, `zero`, `only_gap_e2e`. El test A13 oculta esta condición porque sustituye el plan por un objeto con `con_sha` artificialmente no vacío (`tests/test_hash_tree_tolerante.py:316`).

### H-03 — ALTO — La misma carrera sigue abortando en el `stat` posterior al hash

**Anclas:** `scripts/abrir_caso.py:229`, `scripts/abrir_caso.py:263`, `scripts/abrir_caso.py:357`, `scripts/abrir_caso.py:541`.

**Propiedad rota:** que un renombrado del montaje no tumbe la etapa y que cualquier hueco quede declarado. El recorrido tolerante termina, pero el inventario vuelve a acceder al nombre sin protección antes de imprimir o registrar incidencias.

**Entrada → salida:** `file_sha256(x)` lee correctamente y el fichero pasa a `x.pdf` antes del `stat`. El árbol contiene el hash de `x`, sin incidencias; `_inventario_desde_hashes` lanza `FileNotFoundError`, `etapa_drive` devuelve `estado='fallo'` y no se produce evento. También se ejecutó con `sub/x`, y después de una recuperación correcta `sub/x → sub/x.pdf` seguida de `sub/x.pdf → sub/x.pdf.jpg`: ambas variantes abortan en el mismo `stat`.

**Verificación:** **EJECUTANDO**, `probes.json:stat_race`, `probes_extra.json:nested/effective_twice`. Una clave efectiva que permanezca estable sí se resuelve correctamente (`stable_key`, tamaño 3); no es un error de prefijo o de tipo. La carrera del `stat` es preexistente, pero deja incompleta la remediación de esta misma cadena. Está identificada explícitamente en `docs/MEJORAS_FUTURAS.md:9852`.

### H-04 — MEDIO — El filtro inicial confunde raíz inválida o inaccesible con ausencia

**Anclas:** `scripts/abrir_caso.py:114`, `scripts/abrir_caso.py:115`.

**Propiedad rota:** solo una ausencia constatada puede representarse por un árbol vacío sin incidencias. El booleano `is_dir()` no distingue todos los motivos por los que no pudo reconocer un directorio.

**Entrada → salida:** raíz que es un fichero no vacío → `ArbolLocal({}, (), ())`. Raíz con nombre inválido en Windows → igual. Raíz existente con `PermissionError` inyectado en su consulta de metadatos → igual. También un componente de 256 caracteres devuelve vacío, sin motivo. Ninguna de estas situaciones es «hemos recorrido una carpeta vacía». El callback de `os.walk` no puede ayudar: se retorna antes de llamarlo.

**Verificación:** **EJECUTANDO**, `root_file`, `root_invalid_windows`, `root_stat_denied`, `long_invalid_root`. El error de metadatos es inyectado; no se modificaron ACL reales.

### H-05 — MEDIO — Los directorios enlazados quedan fuera sin declarar la exclusión

**Ancla:** `scripts/abrir_caso.py:135`.

**Propiedad rota:** inventario completo de lo no medido bajo la raíz. `os.walk` usa `followlinks=False` implícitamente y no se inspeccionan ni se declaran los directorios simbólicos que decide no recorrer.

**Entrada → salida:** raíz con `linked_dir → directorio/doc`, enlace a fichero y enlace roto. Se hashea el enlace a fichero, se declara el roto, pero no aparece `linked_dir`, ni su documento, ni un motivo de exclusión. No propongo activar `followlinks=True` a ciegas: introduciría otros problemas, incluidos ciclos; el defecto es afirmar cobertura sin declarar el subárbol excluido.

**Verificación:** **EJECUTANDO**, `probes.json:symlinks`, con enlaces reales permitidos en este Windows. La omisión de subdirectorios enlazados también era posible antes; contradice la nueva declaración absoluta de completitud.

### H-06 — MEDIO — Los archivos posteriores al listado pueden desaparecer del resultado entero

**Anclas:** `scripts/abrir_caso.py:135`, `scripts/abrir_caso.py:141`, `scripts/abrir_caso.py:177`.

**Propiedad rota:** «Nada falta en silencio» (`scripts/abrir_caso.py:104`) sin definir un límite temporal del inventario. No hay nueva enumeración general ni señal de estabilidad del directorio.

**Entrada → salida:** el directorio contiene `first`; durante su hash aparece `late.pdf`, que sigue presente al devolver. El resultado solo contiene `first` y ambos inventarios de incidencias están vacíos. `_reaparecido` solo actúa tras `FileNotFoundError` y no incorpora todos los archivos nuevos que pueda ver. Tampoco pretende identificar individualmente todos los candidatos de una ambigüedad: declara la clave original.

**Verificación:** **EJECUTANDO**, `probes.json:late`. No se exige una instantánea imposible de un árbol que cambia indefinidamente; se constata que la declaración de completitud actual excede lo que mide el recorrido único. No es una regresión exclusiva del diff.

### H-07 — MEDIO — Un fallo del recuento borra incidencias ya conocidas y devuelve «hecha»

**Anclas:** `scripts/abrir_caso.py:565`, `scripts/abrir_caso.py:573`.

**Propiedad rota:** transportar la declaración al pendiente de la etapa independientemente de un recuento auxiliar.

**Entrada → salida:** el intake devuelve `custodia_sin_verificar` con un fichero; el posterior `rglob` lanza `PermissionError`. La salida es `estado='hecha'`, detalle sobre la imposibilidad de contar y **`pendientes=()`**. Los datos ya venían en `res` pero el retorno anticipado evita leerlos. Los errores que `rglob` suprima no activan esta rama; aquí se comprobó específicamente una excepción que sí llega al manejador.

**Verificación:** **EJECUTANDO**, `probes.json:stage_count_fail`, con excepción inyectada en el recuento.

### H-08 — MEDIO — En el pull fallido la declaración llega al evento, pero no al resultado de excepción ni a V1

**Anclas:** `scripts/abrir_caso.py:339`, `scripts/abrir_caso.py:350`, `scripts/abrir_caso.py:367`, `scripts/abrir_caso.py:541`.

**Propiedad rota:** cadena completa de los tres destinos también por `except DriveIntakeError`. El `dataclasses.replace` únicamente existe en el camino de éxito.

**Entrada → salida:** pull rc=3 con un archivo parcial ilegible. El evento contiene correctamente `status='fallo'`, `count=0` y el fichero con motivo. Sin embargo `exc.result.custodia_sin_verificar` sigue vacío y `etapa_drive` devuelve un fallo genérico con `pendientes=()`, sin claves ni motivos de custodia. No afirmo que este camino anuncie éxito: se conserva el fallo del pull. Lo que se pierde es la declaración específica en dos destinos, pese a haberla calculado.

**Verificación:** **EJECUTANDO**, `probes.json:failed_pull`. A18 comprueba el evento, no el resultado de excepción ni su transporte a la etapa.

### H-09 — BAJO — El reconocimiento del renombrado produce falsos negativos con capitalización y doble extensión

**Ancla:** `scripts/abrir_caso.py:200`.

**Propiedad rota:** reconocimiento exacto de candidatos equivalentes en Windows. `Photo → photo.jpg` no satisface la igualdad sensible a mayúsculas de las cadenas `stem/name`. `x → x.tar.gz` tampoco: el stem es `x.tar`.

**Entrada → salida:** en ambas carreras el documento sigue presente y legible, pero no se hashea, no se registra renombrado y la clave vieja queda en `sin_verificar`. A diferencia de H-01, estos casos **sí declaran el hueco**; no son pérdida silenciosa ni atribución a otro documento. La extensión doble excede el patrón literal de «una extensión», por lo que es límite de cobertura, no prueba de que el montaje real la añada.

**Verificación:** **EJECUTANDO**, `probes.json:case/double`. `x.pdf → x.pdf.jpg`, `.x → .x.pdf` y `x. → x..jpg` sí satisfacen el criterio léxico bajo Python 3.14 (`probes_extra.json:stem`). La creación normal de `x.` en este Windows lo normalizó a `x`; no se presenta ese experimento como reproducción de un nombre terminal con punto persistente. Un directorio `x.pdf` es descartado correctamente por `q.is_file()` (`directory_candidate`).

### H-10 — MEDIO — La suite tolera que desaparezcan todas las incidencias salvo la primera

**Anclas:** `scripts/abrir_caso.py:179` (punto mutado); `tests/test_hash_tree_tolerante.py:151`, `:172`, `:223`, `:472` (oráculos con una única incidencia).

**Propiedad rota por el control:** completitud de `sin_verificar`. No se afirma que HEAD ya haga esta truncación: el hallazgo es que el arnés no la detecta.

**Entrada → salida del mutante:** dos archivos `a.pdf` y `b.pdf` arrojan `PermissionError`; M1 devuelve solo `a.pdf`. Los 23 tests nuevos y la suite completa conservan sus resultados originales. El testigo externo que exige las dos claves pasa sobre HEAD y falla sobre M1.

**Verificación:** **EJECUTANDO**, diffs, XML y testigo M1 en `evidence/`. La ausencia de un aserto sobre más de un hueco permite afirmar falsamente que el inventario completo viaja.

### H-11 — MEDIO — El aserto del pull fallido acepta que el motivo se borre entero

**Anclas:** `tests/test_hash_tree_tolerante.py:442`, `tests/test_hash_tree_tolerante.py:443`; `scripts/abrir_caso.py:339` (punto mutado).

**Propiedad rota por el control:** conservar el motivo original en el evento forense. El esperado de `motivo` se extrae del mismo valor actual que se compara; esa parte del aserto es tautológica.

**Entrada → salida del mutante:** el recorrido comunica `PermissionError(13, 'Permission denied')`; M2 escribe `motivo=""` en el evento del pull fallido. A18 y los otros 22 tests siguen verdes. La suite completa tampoco añade fallos ni errores. El testigo que compara contra el motivo de entrada pasa sobre HEAD y falla sobre M2.

**Verificación:** **EJECUTANDO**, diffs, XML y testigo M2 en `evidence/`. La implementación HEAD transmite hoy el motivo; el defecto confirmado está en el instrumento que debería detectar su pérdida.

### H-12 — BAJO — El aviso afirma que se hasheó incluso un reaparecido ilegible

**Anclas:** `scripts/abrir_caso.py:162`, `scripts/abrir_caso.py:170`, `scripts/abrir_caso.py:275`, `scripts/abrir_caso.py:277`.

**Propiedad rota:** exactitud de la declaración al operador. Se añade el par a `renombrados` antes de intentar leer el candidato; la pertenencia a esa lista no acredita un hash.

**Entrada → salida:** `hashes={}`, `renombrados=((.../x,.../x.pdf),)` y `sin_verificar=(.../x.pdf, PermissionError)`, combinación que produce legítimamente el caso A21. `_intake_generico` imprime «se hasheó bajo el nombre efectivo» y acto seguido declara que ese archivo no se pudo leer. El primer mensaje es falso. Por lectura, la misma afirmación también se emite para el renombrado excluido como protocolo efectivo.

**Verificación:** **EJECUTANDO + LEYENDO**, `probe_diagnostic.py` / `probe_diagnostic.json`, contra la copia `p/` y con planificador real. Es una inconsistencia de diagnóstico, distinta de la pérdida del evento de H-02.

## 4. Respuestas de cobertura y límites

### P1 — Inventario de todas las salidas sin hash identificadas

| Situación / ancla | Qué sucede | Evidencia |
|---|---|---|
| Raíz inexistente, `scripts/abrir_caso.py:114` | Todo vacío: caso permitido explícitamente | Tests y lectura |
| Raíz fichero, inválida, demasiado largo un componente, error al consultar metadatos, `:114` | Todo vacío sin motivo, H-04 | Sondas |
| Error de `scandir` de raíz o subdirectorio, `:124`, `:135` | Se declara el directorio, no cada descendiente desconocido | Tests A8/A22 y lectura |
| Directorio del listado pasa a fichero, `:135` | Al descender se declara `NotADirectoryError` bajo su clave | Sonda `dir_to_file` |
| Directorio simbólico descendiente, `:135` | No se sigue ni se declara; H-05 | Sonda real |
| Enlace a fichero, `:150` | Sigue destino y hashea; si está roto, declara `FileNotFoundError` | Sonda real |
| Archivo nuevo después de enumerar, `:141` | Sin hash ni incidencia general; H-06 | Sonda real |
| Protocolo por ubicación, `:147` | Exclusión intencionada, sin `sin_verificar` | Tests |
| `FileNotFoundError`, cero candidatos, `:153` | Se declara clave original y `repr(error)` | Tests / sondas |
| Varios candidatos, `:157`, `:203` | Se declara ambigüedad de la clave original; no se elige | Tests / sonda extra |
| Relectura del directorio falla, `:197` | Se declara clave original con motivo de relectura | A20 |
| Candidato con `stem` distinto, directorio, o cadena ya listada, `:196`, `:200` | No se adopta; si ninguno más encaja se declara el original | Tests / sondas; casing rompe exclusión en H-01 |
| Candidato efectivo es protocolo, `:166` | Se anota renombrado, se excluye sin hash por política | A11/A11b |
| Lectura efectiva falla con `OSError`, `:170` | Se declara clave efectiva; se conserva el renombrado | A21 |
| Lectura inicial falla con otro `OSError`, `:173` | Se declara clave original; incluye fichero convertido en directorio antes de abrir | A6 / sonda Windows inválido; cambio de tipo leído |
| Excepción fuera de `OSError` | Puede propagarse; no existe retorno parcial general | Lectura; no se afirma tolerancia a fallos de programación/interrupciones |

Un nombre `bad<name` inyectado como hijo listado produce `OSError(22)` y sí queda declarado. No se fabricó un archivo real con un nombre prohibido. No se extrapola MAX_PATH: se creó y hasheó correctamente una ruta real de **373 caracteres** en este entorno; el componente de 256 caracteres y la consulta fallida de raíz ilustran otro límite. Las ACL reales y otros montajes/runtimes quedan sin verificar. El error de metadatos que se intentó inyectar en un candidato no alteró la clasificación de `iterdir` en este runtime: el resultado siguió declarando dos candidatos ambiguos; no se usa como evidencia de un hueco adicional.

### P2 y P5 — Consumidores y cadena completa

La búsqueda de todos los `.py` encuentra **dos llamadas de producción** a `hash_tree_local`, ambas en `scripts/abrir_caso.py:333` y `:356`. No hay llamada en `streamlit_app.py` ni en `core/`. Ambas consumen `.hashes` correctamente; no encontré un consumidor Python de producción que trate `ArbolLocal` como dict. Los tests consumidores antiguos se adaptaron en `tests/test_abrir_caso_cli.py:20`, `:249` y `tests/test_intake_control_por_ubicacion.py:221`.

| Camino | Retorno / excepción | Evento | Pendiente V1 |
|---|---|---|---|
| Éxito normal, `scripts/abrir_caso.py:356` | Se adjunta la tupla completa en `:367` | Completa si hay `plan.con_sha`, H-02 | `:573` transporta cantidad y claves; el texto no conserva motivos |
| Pull fallido, `:333` | No se adjunta al `exc.result`, H-08 | `:334`–`:343` sí guarda claves y motivos aunque count=0 | Retorno genérico `:542`, H-08 |
| Error posterior al hasheo | No alcanza `:367`, H-03 | No alcanza el evento | `fallo` genérico |
| Recuento final falla | La custodia ya venía en `res` | Ya se intentó antes | Se descarta, H-07 |
| `dry_run=True`, `:267` | `_intake_drive_ev` todavía puede adjuntar datos al resultado | No escribe evento, deliberado; retorna antes de avisos | V1 usa `dry_run=False` |

`_intake_manual` construye su propio dict mediante `file_sha256` en `scripts/abrir_caso.py:429`, y llama `_intake_generico` en `:434`; no consume este árbol. No se le ha extendido la tolerancia. `brain.reconcile` recibe exactamente el mismo tipo de dict que antes (`scripts/abrir_caso.py:285`); una clave renombrada estable funciona y una nueva carrera en cualquier nivel vuelve a fallar antes de reconciliar, H-03.

Los caminos Streamlit (`streamlit_app.py:511` y `:2579`) llaman directamente a `pull_drive_ev`; anuncian archivos descargados en `:525` y `:2591`. No hashean ni leen el nuevo campo. No hay una declaración producida y descartada allí: **no se produce custodia por este helper**. Esta cobertura ausente es anterior al diff; no se atribuye falsamente al cambio de tipo. El remedio manual documentado en `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:273` menciona los dos helpers pero no documenta el nuevo desempaquetado ni la transmisión de incidencias: es una guía incompleta, no un tercer llamador Python ejecutable encontrado.

### P6 — Las tres decisiones

1. **Guard AST:** la restricción literal actual sí existe. `tests/test_abrir_caso_exit_bajo_mutex.py:94` reúne definiciones del módulo, `:104` solo sigue llamadas cuyo nombre coincide con ellas y `:173` exige que `hash_tree_local` esté entre las alcanzadas. Moverla sin adaptar el guard hace fallar ese aserto. **No es cierto que toda mudanza obligue a debilitar la propiedad:** se puede ampliar el análisis a la función del módulo destino y exigir que la alcance e inspeccione, con control positivo de una terminación inyectada allí. Eso fortalece o conserva la cobertura; sería un cambio del guard, no una excepción a la propiedad. Un wrapper local por sí solo conservaría el nombre pero dejaría sin inspeccionar el cuerpo trasladado, por lo que no lo considero una solución equivalente. **Verificado leyendo**; no se implementó una mudanza ni se acredita cobertura de un guard alternativo.
2. **`Reconciliacion`:** no ha cambiado el dict que recibe. Su contrato es comparar contra un plan (`core/abrir_caso.py:273`), no censar el remoto ni certificar completitud. En el camino local plan y verificación derivan de los mismos hashes (`scripts/abrir_caso.py:263`, `:285`); la sonda vacía devuelve `ok=True` aunque existe un hueco. Ese resultado es coherente con su contrato estrecho, pero no prueba «todo el destino verificado». La ausencia del campo no exige por sí sola modificar la clase: la arquitectura de transporte separado puede ser válida **si la incidencia no se pierde**. H-02, H-04 y H-07 muestran por qué la justificación «ningún llamador lo leería» no acredita hoy esa condición. No se atribuye a `reconcile` una comparación remota que nunca hace.
3. **Campo en `DriveIntakeResult`:** la trampa está **expresamente documentada en el propio campo**, `core/intake_drive.py:118`–`:123`: vacío desde el pull significa no verificado, no resultado limpio. El docstring de retorno de `pull_drive_ev` (`:179`) es genérico y no lo reitera. El valor por sí solo sigue siendo ambiguo, y el tipo no impide una lectura incorrecta; pero no encontré consumidor actual que lo interprete como certificado después del pull a pelo. No invento esa regresión. Sí existe la pérdida concreta del resultado parcial en H-08. **Lectura** del DTO y consumidores; el pull remoto no se ejecutó.

### Inventario de lo NO cubierto

- Montaje real de Google Drive for Desktop, cambios espontáneos del proveedor, rclone real, cuentas y CRM: **SIN VERIFICAR**.
- Revisión de procedencia/commits y genealogía: imposible con estos archives; no acreditada.
- ACL reales, archivos especiales/dispositivos, junctions/reparse points distintos de los enlaces probados, ciclos de enlaces, otros Python y otros sistemas operativos: **SIN VERIFICAR**. El hash de un archivo que cambie sus bytes mientras se lee tampoco se validó como instantánea.
- No se audita toda la cadena de ingestión manual, correo, WhatsApp, sala de máquina o MCP; se buscó su relación con el cambio. No se ejecutó la UI Streamlit.
- El resto de la suite constituye cobertura de los tests existentes; un verde no demuestra ausencia de las omisiones reproducidas ni de casos no instrumentados.
- La afirmación histórica de «14 mutantes muertos» no se acredita sin sus definiciones, ejecuciones y artefactos. Se solicitó la lista; su comparación exacta con los controles propios queda **SIN VERIFICAR** si no se aporta.

NO-SHIP
<!-- informe-literal:fin:wq7z -->

## 2. Evidencia verificada por mí al adjudicar

Cada hallazgo se contrastó **contra la fuente** —el árbol real del worktree—, no contra el
informe ni contra el diff. Los doce se confirmaron; ninguno se refutó. Lo que sigue es la
evidencia de esa comprobación, con ruta y línea del árbol **posterior al remedio** salvo
donde se indica el commit revisado.

| Hallazgo | Comprobado en | Cómo lo verifiqué | Veredicto |
|---|---|---|---|
| H-01 `ALTO` | `scripts/abrir_caso.py` (`listadas` y `_reaparecido`) | Test rojo `test_r1_h01_…` sobre el árbol revisado: con `x` y `X.PDF` listados, el renombrado a `x.pdf` se adoptaba y el hash de `OTRO` acababa bajo dos claves. **CONFIRMADO** | confirmado |
| H-02 `ALTO` | `scripts/abrir_caso.py::_intake_generico` | Leí la condición `if plan.con_sha:` y escribí `test_r1_h02_…`: con `hashes={}` y una incidencia, `append_event` no se llamaba. **Y mi propio A13 lo tapaba**, porque su plan falso tenía `con_sha` no vacío | confirmado |
| H-03 `ALTO` | `scripts/abrir_caso.py::_inventario_desde_hashes` | `stat()` sobre la clave dos líneas después del hash. `MEJORAS #214:9852` ya nombraba esta función entre los cuatro recorridos-y-abre. Yo lo había dejado fuera «declarado»; el revisor tiene razón en que eso deja la **misma cadena** a medias | confirmado |
| H-04 `MEDIO` | `scripts/abrir_caso.py`, primera línea de `hash_tree_local` | `is_dir()` colapsa tres cosas. Es la frontera de esta pieza aplicada a la propia pieza | confirmado |
| H-05 `MEDIO` | `scripts/abrir_caso.py`, bucle de `os.walk` | Enlace de directorio real en `tmp_path`: el subárbol salía del inventario sin declararse | confirmado |
| H-06 `MEDIO` | docstring de `hash_tree_local` | El hecho es cierto y la propiedad «capturar lo que aparezca después» no es construible: un recorrido mide un instante. Lo remediable era mi **afirmación** de completitud, y eso se corrigió | confirmado (remedio de prosa) |
| H-07 `MEDIO` | `scripts/abrir_caso.py::etapa_drive` | El `except OSError` del recuento retornaba antes de construir los pendientes | confirmado |
| H-08 `MEDIO` | `scripts/abrir_caso.py::_intake_drive_ev` y `etapa_drive` | El `dataclasses.replace` solo existía en el camino de éxito | confirmado |
| H-09 `BAJO` | `_reaparecido` | `Photo` → `photo.jpg` y `x` → `x.tar.gz` no se reconocían. Mismo remedio que H-01 más el cambio de `stem` a prefijo | confirmado |
| H-10 `MEDIO` | el ARNÉS, no el código | Reproduje su mutante `tuple(sin_verificar)[:1]`: sobrevivía a los 23 tests porque todos los oráculos tenían **una** incidencia. Hoy es `M15` y muere | confirmado |
| H-11 `MEDIO` | el ARNÉS, `tests/test_hash_tree_tolerante.py` (A18) | Mi aserto sacaba el motivo esperado de la propia salida. Su mutante `motivo=""` pasaba. Hoy es `M16` y muere | confirmado |
| H-12 `BAJO` | `_intake_generico`, aviso de renombrado | El aviso afirmaba un hash que la línea siguiente desmentía | confirmado |

**Dos divergencias de remedio, razonadas.**

1. **H-06** no se remedia con código sino con prosa: no existe una instantánea de un árbol
   que cambia mientras se recorre. Lo que sí existe es no afirmar que se tiene. El docstring
   dice ahora qué mide —lo enumerado— y que de lo enumerado nada se pierde callando.
2. **P6.1** — el revisor rebate mi afirmación de que mudar `hash_tree_local` a `core/`
   «obligaría a debilitar el guard»: propone ampliar el guard AST al módulo destino, con su
   control positivo, lo que conservaría la cobertura. **Tiene razón y la prosa era
   demasiado absoluta**; la corregí. No mudo la función: eso es rehacer un guard, trabajo
   propio y fuera del alcance de esta pieza.

**Un defecto que encontré yo al remediar H-03, y que la R1 no vio porque no existía aún.**
Al desacoplar el inventario de los hashes, la clave que el `stat` no pudo medir seguía
llegando a `reconcile` dentro de `hashes`: salía como `extra`, `ok` pasaba a `False` y la
apertura **abortaba entera**. Un hueco declarado no es un sobrante; confundirlos convertía el
remedio en una vía nueva de tumbar la etapa. Fijado en
`test_r1_h03c_un_hueco_del_stat_NO_aborta_la_apertura_como_si_sobrara`. Acota además el §3.3
del handoff: «`extras` es siempre vacío porque `reconcile` cuadra consigo mismo» deja de ser
cierto en cuanto inventario y hashes pueden diferir.

**Lo que sigue SIN VERIFICAR, y no se da por cubierto:** el montaje real de Google Drive for
Desktop renombrando bajo los pies. Ni el revisor ni yo lo reprodujimos —requiere `G:` y una
apertura real—; lo que hay son carreras deterministas equivalentes en sus límites de I/O. Y
los 373 rojos que el revisor midió en su entorno son de plataforma: los reprodujo sobre BASE
con los **mismos 400 identificadores**, y aquí la suite da **0 fallos** con las dos semillas.
