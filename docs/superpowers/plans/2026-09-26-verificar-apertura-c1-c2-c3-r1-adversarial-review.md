---
tipo: revision-adversarial
objeto: diff cc98244..778920b de la fila #45 (MEJORAS #306, #307, #287; core/verificar_apertura.py, su adaptador y sus tests), contra el plan docs/superpowers/plans/2026-09-26-verificar-apertura-c1-c2-c3.md
objeto_rev: "1"
commit: 778920b
ronda: "1"
revisor: Codex
modelo: gpt-6-sol
esfuerzo: high
velocidad: default
veredicto: NO-SHIP
marcador_nonce: t8wm
sha256_informe: 553e6583394f79dea1041e8464b75b595a04d28509e0fc0f6d98daa15d0a7945
adjudicado_en: docs/superpowers/plans/2026-09-26-verificar-apertura-c1-c2-c3.md §7
---

# Acta — R1 adversarial sobre el DIFF de la fila #45 (`verificar_apertura` C1, C2 y C3)

Objeto: el diff `cc98244..778920b`, que cierra los tres falsos rojos de `verificar_apertura`
(`MEJORAS #306`, `#307`, `#287`) según el plan de la pieza. **Una ronda**: toca `core/` —que nunca
queda exento— pero es un verificador de solo lectura, sin datos de cliente ni cobertura de revisión.
Fila ordinaria de la política: `gpt-6-sol` · `high` · `default`, y **tercera fila del ledger de
calibración de la #38**. En el mandato la pieza figura como «fila #44»: el #406 tomó ese número
mientras se subía el PR, y pasó a la #45 sin cambiar el objeto.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.4` (binario `13995fba801849b0`), `gpt-6-sol` · `high` — **releídos** del `turn_context` del rollout y de la cabecera del `_stdout.log`; velocidad `default` **afirmada** desde el lanzador conservado |
| Objeto | `base/` (`cc98244`), `head/` (`778920b`) y `c1f63aa/`, copias `git archive` fuera del repo, más `diff.patch` y `commits.txt` |
| `sha256` del objeto | **idéntico al abrir y al cerrar**: 4.305 ficheros, comparados por él y por mí contra una reextracción de los tres commits desde git |
| `sha256` del informe | `553e6583394f79dea1041e8464b75b595a04d28509e0fc0f6d98daa15d0a7945` |
| Tiempos | lanzado a las 16:33:42; `INFORME.md` a las 16:49:32; `exec` salió a las 16:49:46 con `exit=0` |
| Veredicto | `NO-SHIP` — 6 hallazgos: 1 `alta`, 3 `media`, 2 `baja` |

## 0. Mandato, literal

# Mandato — R1 adversarial sobre el diff de la fila #44: `verificar_apertura` C1, C2 y C3 (FeesDefender)

## 0. Higiene y reglas

- Tu directorio de trabajo debe contener solo: `MANDATO.md`, `base/`, `head/`, `c1f63aa/`,
  `diff.patch` y `commits.txt`. Si hay cualquier otro fichero, **no lo leas** y decláralo en la
  primera línea del informe.
- `base/` es el commit `cc98244` (main), `head/` es `778920b` (la rama del cambio, con `main`
  fusionado) y `c1f63aa/` es un commit intermedio de la misma rama (ver pregunta 6); los tres,
  extraídos con `git archive`, sin `.git`. Son de **solo lectura**: si necesitas ejecutar o modificar
  algo, copia a una carpeta tuya dentro de tu directorio de trabajo. Calcula el SHA-256 de todos los
  ficheros de `base/`, `head/` y `c1f63aa/` al abrir y al cerrar, y di si coinciden.
- Python con las dependencias del repo:
  `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe` (tiene pytest; **no** tiene
  pytest-randomly, así que no hacen falta semillas). Usa `--basetemp` con una ruta **relativa**
  dentro de tu directorio de trabajo.
- No accedas a red, al CRM, a Drive, a Google ni al repositorio real.

## 1. Objeto

El diff `cc98244..778920b` (`diff.patch`, `commits.txt`; el commit de fusión de `main` queda fuera
de `commits.txt` y no aporta cambios propios). Cierra tres falsos rojos de
`core/verificar_apertura.py`, el verificador de solo lectura del «OK» de una apertura de expediente:

- **C1** (`MEJORAS #306`): el censo remoto contra `00_Input/01_Drive EV` daba los nativos de Google
  como faltantes y sobrantes a la vez.
- **C2** (`MEJORAS #307`): el reconocimiento del relleno con ceros de `MEJORAS #225` no confirmaba
  nunca un fichero que ya acababa en ceros, como todo ZIP.
- **C3** (`MEJORAS #287`): la cobertura de la sala de máquina contra el catálogo de la sala de
  lectura no podía salir verde con un PDF partido, y se rediseña: de cardinalidad a identidad.

El plan con lo medido, el diseño, los tests y lo que declara no cubierto está en
`head/docs/superpowers/plans/2026-09-26-verificar-apertura-c1-c2-c3.md`; las entradas del backlog,
en `head/docs/MEJORAS_FUTURAS.md` (#287, #306, #307 y la nueva #316). Revisa el código contra ese
plan. El §4 del plan da cifras medidas sobre 23 expedientes reales a los que no tienes acceso:
decláralas SIN VERIFICAR, salvo lo que puedas razonar desde el código.

## 2. Qué te pido, numerado

1. **C2: ¿sigue siendo prueba?** `_es_el_relleno_de_225` (en `head/core/verificar_apertura.py`)
   confirma ahora en cualquier frontera dentro de la cola de ceros cuyo prefijo hashee al sha256
   declarado. Intenta construir un fichero local que **no** sea «el original seguido de ceros hasta
   el siguiente múltiplo de 512» y que la función confirme. Comprueba también que se conservan las
   garantías previas: una sola lectura con el tamaño comprobado al cerrar, cola de menos de 512,
   tamaño múltiplo de 512, y el coste acotado.
2. **El test `n9` reescrito.** `test_n9_…` exigía antes que un original que ya acababa en ceros,
   rellenado, saliera **sin** confirmar, y ahora exige que se confirme (su docstring y el plan §3 lo
   declaran). Dictamina si eso es debilitar la suite o corregir un aserto que fijaba un falso
   negativo, y si la propiedad que protegía —no poner una etiqueta falsa— queda sostenida por otros
   tests, en particular en su mismo escenario.
3. **C1: el nombre con que el pull deja un nativo en disco.** `ruta_local_esperada` y el `mime_type`
   nuevo de `FicheroRemoto` (en `head/core/verificar_apertura_fuentes.py`). ¿Describen lo que hace
   rclone con los formatos de exportación por defecto? ¿Puede un fichero **no** nativo cruzarse como
   si fuera la exportación de un nativo, o un nativo que no llegó salir como presente? Revisa las
   colisiones nativo/subido en C1 y en C2, y si C2 cambia de comportamiento en algo más que la clave.
4. **C3: falsos verdes.** ¿Puede un documento que la sala de máquina procesó faltar del catálogo y
   C3 decir `ok`? Ataca el cruce por sha256 de origen (`parent_sha256` o `sha256`), la
   normalización de rutas (`_clave_de_ruta_de_origen`: prefijo `00_Input/`, barras invertidas,
   NFC), las dos exclusiones (el registro de protocolo por ubicación de `core/intake_control.py` y
   el `_export_original.zip` con un `_chat.txt` en su carpeta), las filas sin `rel_path`, las
   entradas del catálogo sin ruta o sin hash, las filas `duplicado`, y la comparación de los dos
   catálogos como multiconjuntos. Y la dirección inversa: ¿puede una entrada del catálogo sin fuente
   pasar?
5. **C3: la cobertura sana.** La acreditación estructural de un hijo de bundle
   (`slug.startswith(padre + "__")`), junto a la presencia del padre en la cobertura. ¿Es demasiado
   permisiva, o demasiado estricta con coberturas reales? Con el cruce por identidad, ¿sigue
   sirviendo para algo esa comprobación, o solo conserva los mensajes de los tests antiguos?
6. **El cambio de fixtures (`c1f63aa`).** El plan dice que es neutro: con los fixtures nuevos y la
   C3 anterior, el fichero de tests entero sigue verde. `c1f63aa/` es ese commit —C1 y C2 ya
   cambiados, C3 todavía la anterior—. Compruébalo corriendo sus tests, y dictamina si algún test
   de C3 cambió de significado con los datos nuevos aunque su aserto no cambiara.
7. **Los tests nuevos** (`test_306_*`, `test_307_*`, `test_287_*`, `n9b`, y el de
   `head/tests/test_intake_drive.py` sobre los formatos de exportación). ¿Prueba cada uno lo que su
   nombre dice? ¿Alguno pasaría con una implementación equivocada? Si puedes, introduce en una copia
   tuya variantes defectuosas concretas y di qué test las detecta y cuál no.
8. **Contratos que no deben cambiar.** Los estados y su significado (`ok` · `pendiente` · `fallo`),
   el registro de las nueve comprobaciones, la guarda que exige a cada una un caso en `fallo`, las
   claves de evidencia que consumen el CLI y su `--json`, y que el módulo siga sin escribir ni
   importar escritores. ¿Rompe el diff algo de eso?
9. **El §5 del plan** («lo que no cubre»). ¿Alguno de esos límites es en realidad un defecto que
   merece remedio ahora?

## 3. Formato del informe

Escribe `INFORME.md` en tu directorio de trabajo, en castellano. Por cada hallazgo: identificador
(H-01, H-02…), **severidad** (alta · media · baja) y **coste del remedio** (trivial · acotado ·
estructural), dónde (fichero:línea en `head/`), la evidencia reproducible y el remedio que propones.
Añade una sección «Lo que intenté refutar y no pude» y otra «SIN VERIFICAR».

No encontrar defectos es un resultado legítimo: si es tu conclusión, dilo, con la evidencia de lo
que probaste. Termina el informe con una línea que contenga solo el veredicto, uno de: SHIP,
LISTA-CON-CAMBIOS, REQUIERE-REVISION, NO-SHIP.

Como último mensaje, da la ruta de `INFORME.md` y su SHA-256 calculado sobre el contenido en UTF-8,
con saltos LF y un único salto final.

## 1. Informe recibido, sin modificar (Codex, 2026-09-26)

<!-- informe-literal:inicio:t8wm -->
Fichero ajeno a la lista permitida al abrir el directorio: `_stdout.log`; no lo he leído.

# R1 adversarial — fila #44, `cc98244..778920b`

**Alcance.** He leído únicamente `MANDATO.md`, `diff.patch`, `commits.txt` y los tres árboles autorizados; las ejecuciones y mutaciones están en `scratch/`, fuera de esos árboles. No he consultado red, CRM, Drive, Google ni el repositorio real. SHA-256 de todos los ficheros al abrir y cerrar: 4.305 rutas (base 1.436, head 1.437, c1f63aa 1.432), **0 diferencias**. El plan aporta mediciones de expedientes a las que no tuve acceso: se separan abajo.

## Hallazgos

### H-01 — Alta; remedio acotado — C3 puede acreditar dos fuentes con una sola entrada contradictoria

**Dónde:** `head/core/verificar_apertura.py:291-323` (en especial 307-310 y 319-323).

**Evidencia reproducible:** `python scratch/probes.py`, caso `cruce_hash_ajeno`: cobertura `A.pdf` con SHA-A y `B.pdf` con SHA-B; catálogo con **una** entrada `(ruta_relativa=A.pdf, hash=SHA-B)`. Resultado actual: `ok`, `por_ruta=1`, `por_sha=1`, `n_sin_catalogar=0`, `n_catalogo_sin_fuente=0`. `B.pdf` no tiene entrada propia: el hash que se le atribuye contradice la ruta de la única entrada. El caso aún menor `ruta_correcta_hash_falso` también devuelve `ok` con un hash distinto para la misma ruta. La causa son los dos conjuntos globales, `rutas_cat` y `hashes_cat`: cada mitad de una entrada puede acreditar una fuente distinta. Las filas `duplicado` y las piezas de bundle atraviesan la misma lógica.

**Remedio:** contrastar pares de identidad por entrada. Si una ruta del catálogo identifica una fuente de la cobertura y ambos lados tienen SHA, exigir que coincidan; una entrada contradictoria debe ser `fallo` y su hash no debe acreditar otra fuente. Conservar el cruce por hash para copias y rutas históricas que no coinciden, comprobando que la entrada usada es internamente coherente. Añadir los dos contraejemplos como tests. Este falso verde afecta el objetivo principal de C3 y bloquea el envío.

### H-02 — Media; remedio estructural — C1 puede llamar «exportado» a un fichero ajeno

**Dónde:** `head/core/verificar_apertura.py:812-821,862-910`.

**Evidencia reproducible:** `python scratch/probes.py`, caso `nativo_sustituido`: remoto con solo el nativo `x` (`application/vnd.google-apps.document`) y disco con un `x.docx` de bytes arbitrarios, sin exportación del nativo. C1 devuelve `ok` y declara «1 nativos de Google, cruzados con su exportación». No hay colisión remota que pueda avisar: esta requiere **dos** objetos remotos con la misma ruta esperada. C2 devuelve `pendiente`, porque el nativo no publica `sha256Checksum`; por tanto el informe completo no acredita todos los hashes, pero C1 sí da un falso verde de presencia/procedencia. La tabla de extensiones transforma nombres; no prueba que el fichero local proceda de ese objeto.

**Remedio:** para acreditar procedencia haría falta un manifiesto verificable del pull, o un contraste independiente de la exportación; mientras no exista, el detalle y la evidencia de C1 deben decir «nombre compatible con la exportación», no «exportación acreditada». Hacer explícita esa limitación en la salida, especialmente si se usa el `ok` de C1 aisladamente. `ruta_local_esperada` acierta la regla nominal: el pull no fija otros formatos y `rclone help backend drive` de la versión local 1.73.5 declara `docx,xlsx,pptx,svg` por defecto. La exportación real y la configuración efectiva no se han probado.

### H-03 — Media; remedio acotado — Dos catálogos discrepantes en campos documentales se declaran iguales

**Dónde:** `head/core/verificar_apertura.py:240-256,387-391`.

**Evidencia reproducible:** `python scratch/probes.py`, caso `catalogos_metadatos_distintos`: las dos ubicaciones contienen una entrada con igual `(ruta_relativa, hash)` pero distinto `id_doc` y `estado` (`original` frente a `retirado`). C3 devuelve `ok`. `Counter` sí conserva multiplicidades y descubre diferente ruta/hash aun con igual número de entradas (`test_287_dos_catalogos...`), pero `_identidad_de_entrada` desecha el resto de cada entrada. El plan dice que han de tener «las mismas entradas»; este caso no las tiene.

**Remedio:** definir qué campos del catálogo deben concordar entre las dos ubicaciones y comparar sus entradas completas canonicalizadas, o restringir expresamente el contrato a identidad de ruta/hash y mostrar que el resto puede divergir. `id_doc` y `estado` merecen cotejo porque afectan al uso de la sala.

### H-04 — Media; remedio acotado — C3 acepta entradas sin una de sus dos claves de custodia

**Dónde:** `head/core/verificar_apertura.py:287-323,387-391`.

**Evidencia reproducible:** `python scratch/probes.py`: `sin_ruta` (solo `hash`) da `ok` por SHA; `sin_hash` (solo `ruta_relativa`) da `ok` por ruta; `sin_ambos` sí da `fallo`. En la dirección inversa, `ruta_fantasma_hash_real` da `ok`: una entrada cuya ruta no figura en cobertura se acredita por el hash de otra ruta. Eso puede ser legítimo para un catálogo histórico o una copia, pero C3 no demuestra que el lugar anunciado exista. El productor `head/.claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py:65-72` escribe ambos campos. El fallback por SHA para una **ruta antigua distinta** es necesario, pero una entrada sin ruta no permite localizar lo que el catálogo presenta; una sin hash no acredita identidad de contenido. Ningún test nuevo distingue estos casos de una entrada bien formada.

**Remedio:** validar la forma mínima del catálogo antes del cruce: exigir ruta y hash cuando el productor los promete; si se admiten catálogos históricos sin uno de ellos, declararlo `pendiente` o documentar y probar explícitamente la excepción, sin llamarlo cotejo íntegro. No eliminar el fallback por SHA para rutas presentes que no coinciden.

### H-05 — Baja; remedio acotado — La guarda estructural de hijos acredita cualquier sufijo

**Dónde:** `head/core/verificar_apertura.py:259-278`.

**Evidencia reproducible:** `python scratch/probes.py`, caso `padre_slug_basura`: una única fila con `parent_slug="bundle"`, `slug="bundle__basura"`, ruta y hash cruzados con el catálogo devuelve `ok` y `hijos_de_bundle=1`, aunque no tiene la forma `<padre>__<doc_id>_<TIPO>` que genera `head/core/split_documental.py:517-525`. `test_287_un_hijo_cuyo_slug_NO_deriva...` solo prueba un slug sin prefijo. No encontré una cobertura sana del productor que la guarda nueva rechace: ese productor sí antepone `padre + "__"`. El cruce por identidad sigue comprobando la fuente, de modo que la guarda sirve para detectar metadatos de split corruptos; hoy lo hace de forma incompleta. Una fila de padre presente puede acreditar un hijo de slug arbitrario, como antes.

**Remedio:** validar los campos estructurales del split cuando estén disponibles (por ejemplo `doc_id` y tipo frente al slug), o describir la guarda modestamente como prueba de prefijo, no de hijo válido. Evitar una expresión regular más rígida que el propio productor o que los formatos históricos.

### H-06 — Baja; remedio trivial — Un mutante de la exclusión de WhatsApp sobrevive a los tests nuevos

**Dónde:** `head/tests/test_verificar_apertura.py:2498-2526`; código protegido en `head/core/verificar_apertura.py:301-315`.

**Evidencia reproducible:** en una copia cambié únicamente la condición «`_chat.txt` en **la misma** carpeta» por «hay algún `_chat.txt` en la cobertura». Los **14** tests `test_287_*` siguieron verdes. En `scratch/probes.py`, `zip_chat_otra_carpeta` (chat catalogado en `lote1`, zip no catalogado en `lote2`) da `fallo` con el código correcto y `ok` con ese mutante. El control «sin chat al lado» de la suite no pone otro chat en el expediente. La implementación actual sí respeta la carpeta.

**Remedio:** añadir un test con chat en otra carpeta y zip sin catalogar; exigir `fallo` y la ruta del zip en `sin_catalogar`.

## Lo que intenté refutar y no pude

- **C2 y `n9`.** No encontré un fichero distinto de «prefijo con el SHA remoto + entre 1 y 511 ceros hasta el siguiente múltiplo de 512» que `_es_el_relleno_de_225` confirme. El bucle solo prueba fronteras con sufijo de ceros; el prefijo se compara por SHA-256. En `scratch/probes.py` confirmé 43 originales de longitudes y colas distintas y rechacé 43 alteraciones del contenido. La propia función consulta el tamaño, lee una vez en bloques de hasta 1 MiB, comprueba los bytes esperados y un byte extra antes de cerrar, y finaliza a lo sumo 511 hashes de estado sobre la cola de 511 bytes. Exige tamaño múltiplo de 512. Esto no convierte la lectura en una instantánea atómica frente a sustituciones simultáneas de igual tamaño; esa limitación ya existía. C2, fuera de esta función, hace además su lectura inicial de `_sha256` antes de llamar al reconocedor en las discrepancias.
- El cambio de `n9` corrige un aserto que fijaba un falso negativo, pues su fichero **sí** es el original seguido del relleno. No rebaja la exigencia de hash ni convierte la discrepancia en `ok`: `n9` espera `fallo` con explicación. `n9b` altera el contenido en el mismo escenario y exige ausencia de confirmación; `n8`, `n10`, `n11`, `r1_h05b` y los `test_307_*` cubren alteraciones, forma y límite. El test del ZIP construye un ZIP real; los de cola larga y bytes añadidos ejercitan sus nombres.
- **C1 y C2.** El adaptador conserva `mimeType`, las cuatro extensiones corresponden a los formatos por defecto observables localmente, un no nativo no recibe extensión y un nativo sin formato sigue faltando. La colisión de nativo `x` con subido `x.docx` da `fallo` en C1; con hash remoto del subido, también en C2. C2 cambia la clave de cruce, no la regla de veredicto ni el reconocimiento de ceros. Con dos checksums remotos **idénticos**, C2 puede dar `ok` sin marcar colisión (caso `colision_dos_hashes_iguales`), pero C1 sigue en `fallo`, y no hay checksum distinto que elegir.
- **C3.** La normalización de `00_Input/`, `\\` y NFC cruza el caso previsto. Una fila sin `rel_path` da `fallo`. El registro de protocolo se aplica por ubicación: el homónimo fuera de sitio sigue exigido. Un `_export_original.zip` sin chat en su carpeta se exige. Una entrada sin ruta **y** sin hash no pasa; una entrada de ruta/hash completamente ajenos tampoco. Las copias `duplicado` se cuentan como procedencias por `rel_path` y pueden cruzar por hash; si tampoco se cataloga su titular, quedan sin catalogar. Los dos catálogos se comparan con `Counter`, por lo que sus multiplicidades y sus pares ruta/hash distintos sí se detectan. Muté `parent_sha256` por `sha256` en una copia: `test_287_una_pieza_de_bundle_se_cruza_por_el_sha256_del_PDF_de_ORIGEN` falló como debía.
- **Fixtures de `c1f63aa`.** El AST completo de `c3_cobertura_vs_catalogo` tiene el mismo SHA-256 en `base/` y `c1f63aa/` (`c07bf23e…511`): allí C3 aún es la anterior. Desde una copia, `pytest scratch/c1_run/tests/test_verificar_apertura.py --basetemp scratch/pytest_c1_root -p no:cacheprovider -q` recogió 167 tests: 166 pasaron y 1 quedó omitido por `--runslow`. Los fixtures nuevos **sí cambian el significado futuro** de los tests de C3 que esperan `ok`: ahora las rutas de catálogo y cobertura son las mismas; con C3 anterior, `scratch/probe_c1_fixture.py` demuestra que dos rutas de catálogo totalmente distintas también dan `ok` si solo cuadra el número. Los asertos no cambiaron y el commit es neutro para C3 antigua, pero prepara casos de identidad para C3 nueva.
- **Contratos externos.** El AST de `Resultado`, `Informe`, `ESTADOS`, `ESTADOS_MEDIDOS`, `COMPROBACIONES` e `IMPLEMENTADAS` es idéntico entre `base/` y `head/`: se conservan los nueve IDs, orden y significados de `ok`/`pendiente`/`fallo`. La guarda que ejecuta un caso en `fallo` por cada comprobación pasó en las pruebas. C1 y C2 conservan sus claves de evidencia y C3 conserva las anteriores y añade detalle; el test de `--json` pasó. No hay llamadas de escritura de ficheros nuevas ni importación de escritores; el nuevo `core.intake_control` solo importa `re` y clasifica rutas.

## Pruebas y límites del plan

- La copia de `head/` pasó `pytest scratch/head_run/tests/test_verificar_apertura.py scratch/head_run/tests/test_intake_drive.py --basetemp scratch/pytest_head_root -p no:cacheprovider -q`: **262 recogidos, 261 pasados, 1 omitido** (`--runslow`). El test nuevo de `intake_drive` solo verifica que el comando no fija opciones de exportación; por sí solo no prueba el formato efectivo de rclone ni su configuración. No repetí la suite completa de 6.800 casos declarada en el plan.
- Los límites del §5 sobre presentaciones/dibujos sin caso medido, `size` remoto de C2, decisión de ubicación #221 y filas `duplicado` sin titular catalogado no exigen un remedio independiente ahora: las incertidumbres están declaradas y las condiciones relevantes quedan en `fallo` o sin confirmar. La falta de procedencia acreditada para nativos y la aceptación de metadatos incompletos de catálogo sí merecen los remedios H-02/H-04. El backlog #316 sobre documentos no catalogados es un problema de la skill productora, no una razón para omitirlos en C3.

## SIN VERIFICAR

- Todas las cifras y nombres de los **23 expedientes reales** del §4, incluida la distribución 5 `ok`/14 `fallo`/4 catálogos discordantes, las 36 fuentes de W-030A13, la afirmación de que el 100 % de los hijos reales deriva del slug padre y los ocho nativos de W-02Y2J6. Solo he razonado la lógica sobre datos sintéticos y el código.
- La ejecución de C1/C2 `--con-red`, una descarga/exportación real de rclone, y la configuración efectiva del remote. La ayuda local de rclone 1.73.5 acredita sus **valores por defecto**, no el resultado de una transferencia.
- El comportamiento de la suite completa y de los tests marcados `--runslow`; no se ejecutaron por alcance y por la prohibición de acceso a sistemas reales.

NO-SHIP

<!-- informe-literal:fin:t8wm -->

## 2. Evidencia verificada por mí al adjudicar

- **Digest.** Recomputado sobre el `INFORME.md` entregado (UTF-8, LF, un único salto final):
  `553e6583394f79dea1041e8464b75b595a04d28509e0fc0f6d98daa15d0a7945`, **el mismo que declara el revisor en su último mensaje** (`_ultimo_mensaje.txt`). El
  fichero venía ya en LF con un solo salto: el digest del crudo y el del canónico coinciden, y la
  cadena se verifica contra la salida del revisor, no solo contra sí misma.
- **La ronda terminó, y así se supo.** Vigía armado antes de lanzar, con las dos salidas —fin y
  muerte—, ejecutado con `powershell -File` porque el `Monitor` corre en bash. Señal de fin: el
  `_exit.txt` del lanzador (`exit=0`) y el `-o` (16:49:46); el vigía dijo `TERMINO` a las 16:50:07.
  Ninguna de las cuatro muertes conocidas en el log. Los `ERROR tests/…` que aparecen en él son de la
  suite que el revisor corrió en su copia, no del proceso.
- **Modelo y esfuerzo, releídos:** `gpt-6-sol` · `high` en el `turn_context` de
  `rollout-2026-09-26T16-33-42-01a0de22-de15-7530-9853-441a3abd7553.jsonl` (`originator:
  codex_exec`, CLI `0.155.0-alpha.16.4`) y en la cabecera del `_stdout.log`. Binario elegido por
  tener `codex-code-mode-host.exe` al lado y **sondado antes** con los tres flags
  (`C:\t\sonda-sol-va-1632`): `VIVO`, sin aviso de tier. La velocidad `default` se **afirma** desde
  el lanzador conservado (`C:\t\va-c123-r1-1632-lanzador\_lanzar.ps1`); no se puede releer.
- **El objeto no se tocó, y lo mido yo, no solo él.** Reextraje `cc98244`, `778920b` y `c1f63aa`
  desde git a un directorio aparte y comparé fichero a fichero con las copias del revisor: **4.305
  ficheros, cero diferencias** (1.436 + 1.437 + 1.432, las mismas cuentas que da él).
- **La línea de higiene del informe:** el `_stdout.log` que dice haber encontrado al abrir es la
  redirección de su propia salida que hace el lanzador, no un fichero ajeno. Hizo bien en no leerlo.
- **Tokens y cupo, para la calibración** (releídos del rollout): 6.213.607 tokens totales, de los
  que 6.053.248 son entrada en caché; **entrada nueva + salida = 160.359**, la medida de las filas 1 y
  2 del ledger, y la cifra que imprime el log. El contador semanal de la cuenta marcaba **78 %** en el
  primer y en el último evento (14:33:53 → 14:49:45 UTC), **con otra ronda de otra sesión corriendo
  a la vez** los primeros minutos (`C:\Users\tnm33\Dev\_revisiones_codex\2026-09-26-facturables-r2`,
  `gpt-6-sol`·`medium`, de 14:32:38 a 14:37:15 UTC): el Δ es de la cuenta, no de esta ronda.
- **Los seis hallazgos, reproducidos contra el código y no contra el informe** (un script mío monta
  cada contraejemplo y llama a la comprobación real):
  - **H-01.** Cobertura `A.pdf` (sha A) y `B.pdf` (sha B); catálogo con una entrada `(A.pdf, sha B)`:
    `ok`, 1 por ruta y 1 por sha256. Con `(A.pdf, sha X)`: `ok` por ruta. Causa: `rutas_cat` y
    `hashes_cat`, dos conjuntos globales.
  - **H-02.** Nativo `x` en el remoto y un `x.docx` cualquiera en disco: C1 `ok` «cruzados con su
    exportación»; C2 `pendiente`, sin hash que contrastar.
  - **H-03.** Dos catálogos con el mismo par ruta/sha256 y distintos `id_doc` y `estado`: `ok`.
  - **H-04.** Entrada solo con `hash`: `ok` por sha256; solo con `ruta_relativa`: `ok` por ruta; ruta
    fuera de la cobertura con el hash de una fuente: `ok`. Ninguno lo decía.
  - **H-05.** Una fila `bundle__basura` con `parent_slug: bundle`: `ok`, un hijo de bundle.
  - **H-06.** El código correcto da `fallo` con el chat en otra carpeta; ningún test ponía otro chat
    en el expediente, así que el mutante «cualquier chat» sobrevivía.
- **Y lo que medí en los 23 expedientes reales antes de remediar,** para que el remedio no fabricara
  rojos: **cero** entradas cuya ruta sea la de una fuente con otro sha256; todos los hashes son
  sha256 de 64 hex; las 668 piezas con `doc_id` llevan el slug `<padre>__<doc_id>_`; y 150 entradas
  (147 de W-02JSVZ, 3 de W-02X1WJ) casan solo por sha256 con una ruta que la cobertura no tiene.
- **Adjudicación:** `docs/superpowers/plans/2026-09-26-verificar-apertura-c1-c2-c3.md` §7.
