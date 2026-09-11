---
tipo: revision-adversarial
objeto: diff 044798b..0c3f19c — las cinco comprobaciones de red de verificar_apertura
objeto_rev: "1"
commit: 0c3f19c
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: p2rd
sha256_informe: f09e654b15231cfca9b742dd92b8bd84f66e38af5327917918bb9c61e061f56d
adjudicado_en: docs/superpowers/plans/2026-09-11-apertura-menos-decisiones.md §8
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# Acta de revisión adversarial R1 — las cinco comprobaciones de red

- **Objeto revisado:** diff `044798b..0c3f19c` — `core/verificar_apertura.py`, `core/verificar_apertura_fuentes.py` (nuevo) y sus tests
- **Ronda:** R1 (única por presupuesto: el comando es de solo lectura y no puede destruir nada)
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` sin `.git`, solo lectura
- **Informe recibido:** 2026-09-11, `C:/t/rev-p2red-113637/wd/INFORME.md`, 42777 bytes
- **Hallazgos:** 14 — 8 ALTOS, 5 MEDIOS, 1 BAJO; **14 confirmados, 0 refutados**
- **Remediado en:** `docs/superpowers/plans/2026-09-11-apertura-menos-decisiones.md` §8

**Por qué existe esta acta.** Yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**.

**Qué se le pidió.** La misma pregunta del centro que la ronda anterior —«¿puede este verificador
decir *ok* de un expediente roto?»— y construir expedientes rotos de formas que el autor no
hubiera previsto. Cuatro de los ocho ALTOS producen literalmente **9 ok / 0 fallos**.

**Se le prohibió expresamente consultar los servicios reales** (Drive y el CRM): no hay
credenciales en su entorno y no debía buscarlas. Todo lo que midió lo midió con dobles suyos.

**Custodia.** Dos árboles `git archive` sin `.git`, directorio de ronda con nombre irrepetible
comprobado vacío. Los `sha256` de los tres ficheros coinciden al abrir y al cerrar, y el revisor
repite el `diff -ru` al cierre para acreditar que el alcance no cambió. El digest se computó tras
el `exit 0` del proceso.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:p2rd -->
# Revisión adversarial R1 — cinco comprobaciones de red de `verificar_apertura`

La respuesta a la pregunta central es **sí**: el verificador puede devolver un informe entero con **9 `ok`, 0 `pendiente` y 0 `fallo` sobre un expediente roto**. Lo he reproducido con duplicados remotos, ausencia de partes en el CRM, una cuantía `NaN` y dos censos sucesivos incoherentes. También admite metadatos corruptos como una apertura pendiente; el CLI termina con código 0. Son mediciones sobre copias y fuentes sintéticas, no afirmaciones sobre expedientes reales. La adjudicación corresponde al autor contra la fuente.

## Higiene, alcance y método

Al enumerar el workdir antes de crear andamiaje aparecieron `MANDATO.md` y **`_stdout.log`**. Incumple la condición de «solo MANDATO.md». **No abrí ni leí `_stdout.log`**. No había `INFORME.md`. Las lecturas posteriores se limitaron al mandato, las instrucciones aplicables, las copias congeladas y el andamiaje creado durante esta revisión.

Se ejecutó `C:/Program Files/Git/usr/bin/diff.exe -ru ../base ../head`. El resultado contiene **exactamente** los cuatro ficheros declarados: modificaciones de `core/verificar_apertura.py`, `tests/test_verificar_apertura.py` y el plan; y el nuevo `core/verificar_apertura_fuentes.py`. No aparecen otros cambios. No hay `.git` en las copias. Se leyó también el código llamado por el adaptador y por el CLI; no se decidió únicamente sobre el diff.

Se copiaron los árboles a `wd/copia` y `wd/basecopy`. Todos los tests, sondas, temporales y mutaciones se ejecutaron dentro del workdir. Se usó el Python indicado, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider` y `--basetemp=../tmp/<corrida>` desde la copia, creando previamente `wd/tmp`. `TEMP`, `TMP` y las ubicaciones del perfil del proceso apuntaron al andamiaje. Se desactivó la carga de `.env` y se vació la clave del CRM para las suites. Las sondas del adaptador sustituyen el proveedor del token y `httpx.get` por dobles; no buscan credenciales.

Una barrera mediante `sys.addaudithook` impidió conexiones y resolución de nombres y registró aperturas para escritura. **No se consultó Google Drive ni el CRM.** La barrera inicial fue excesiva para algunos tests generales: bloqueó también sockets locales de infraestructura y rechazó rutas internas de dos tests con prefijo Windows `\\?\`. Esos rojos se declaran como interferencia del andamiaje, no como defectos del diff. No afectaron a las suites del fichero revisado, que terminaron verdes.

Las anclas siguientes son de **`head`**, salvo donde se indica `base`. Las sondas son reproducibles con `run_tests.py` y `harness/test_review_probes.py`; sus entradas y salidas completas quedaron en `tmp/probes.json`. Este informe contiene la evidencia necesaria para entender los hallazgos; esos ficheros son andamiaje, no entregables adicionales.

## Hashes de apertura

| Fichero de `head` | SHA-256 |
|---|---|
| `core/verificar_apertura.py` | `7e9de223de931c7f2f0f9b31bd680bd5d67bdab2030cf7026b1749a2b22f456b` |
| `core/verificar_apertura_fuentes.py` | `d83110ae8483afca014f697a2107396e6001813167d1ae28f743833bb5986dae` |
| `tests/test_verificar_apertura.py` | `2d3ae5a60248466a54677d09e887193206f23d613d3a5923b8850790b7448873` |

## Hallazgos

### H-01 — ALTO — El censo elimina duplicados remotos y el hash depende del orden

**Ancla:** `core/verificar_apertura.py:511` y `:556`.

**Entrada → salida medida:** local `a.pdf = b'x'`; remoto `[FicheroRemoto('a.pdf', '0'*64), FicheroRemoto('a.pdf', sha256(b'x'))]`. C1 devuelve `ok`, evidencia `remoto=1, local=1`; C2 devuelve `ok`. Preparadas correctamente las otras siete comprobaciones, `completo_duplicado_remoto` devuelve **9 ok / 0 pendientes / 0 fallos**. Invertir el orden remoto conserva C1 `ok`, pero convierte C2 en `fallo`.

**Por qué es incorrecto:** el conjunto de rutas destruye la multiplicidad y el diccionario conserva solo el último checksum. Hay dos objetos remotos y solo uno local; además, uno de los checksums discrepa. La representación del puerto no conserva el id de Drive para distinguir objetos homónimos. No es el caso que cubre `test_c1_FALLA_con_duplicados_que_el_remoto_no_tiene`: ese test introduce dos **nombres locales diferentes**.

### H-02 — ALTO — C2 cuenta hashes disponibles como si fueran hashes contrastados; dos consultas dejan escapar el faltante

**Ancla:** `core/verificar_apertura.py:556`, `:558`, `:569`, `:584`; llamadas independientes en `:505` y `:550`.

**Entrada → salida medida:** local vacío, remoto `a.pdf` con checksum → C1 `fallo`, pero C2 **`ok`: «los 1 ficheros coinciden con el hash de Drive»**, con `locales=0`, `con_hash_remoto=1`, **`sin_hash_remoto=-1`**. No se ha abierto ningún documento. Con local `a.pdf` y checksum solo para remoto `b.pdf`, C2 también da `ok`: la igualdad de cardinalidades sustituye a la comparación efectiva.

**Fuga entre comprobaciones, medida:** primera llamada del puerto: `[a.pdf]`; segunda: `[a.pdf,b.pdf]`, ambos con checksum; local contiene solo `a.pdf`. C1 valida la primera foto, C2 declara contrastados ambos hashes de la segunda. `completo_dos_fotos` obtiene **9 ok / 0 pendientes / 0 fallos**; el puerto registra **dos** llamadas de censo. Con una foto estable, C1 sí detecta el faltante: no atribuyo a la pareja un escape estático que no tiene.

**Por qué es incorrecto:** `len(con_hash)` no es el número de ficheros leídos y comparados. La prosa promete evitar fotos distintas y la orquestación hace justamente dos consultas completas, sin compartir resultado ni cachearlo. C6, C7 y C9 también consultan separadamente el mismo expediente.

### H-03 — ALTO — Metadatos ilegibles o mal formados se convierten en ausencia legítima

**Ancla:** `core/verificar_apertura.py:450`, `:458`, `:730`; ramas de pendiente en `:503`, `:548`, `:605`, `:642`, `:675`.

**Entradas → salidas medidas:** `_caso.md` con `---\nmeta: [\n---`, raíz YAML lista, falta del delimitador inicial o un **directorio** llamado `_caso.md` → las cinco de red salen `pendiente`. `sudespacho_expedientes` como mapa, `[{'element':'extrajudiciales'}]`, `[{'id':''}]` o `['texto',None,4]` → C6/C7/C9 `pendiente`. Una lista con un expediente válido seguido de `None` produce los tres `ok`.

**Efecto en la interfaz:** sobre el YAML corrupto y sin artefactos locales posteriores, el CLI real —doblado únicamente el localizador— termina **exit 0**, con «9 de 9 comprobaciones ejecutadas — 0 ok, 9 pendiente(s), 0 fallo(s)».

**Por qué es incorrecto:** `_frontmatter` devuelve `{}` ante errores de lectura, parseo y tipo; `_expediente_registrado` filtra entradas inválidas y no distingue lista corrupta de lista ausente. Se repite la frontera que la R1 anterior había cerrado en `_leer_lista_de_mapas`: **no poder leer o tener datos corruptos no acredita que el alta no se haya hecho**. La ausencia limpia sí puede ser pendiente; estos escenarios contienen corrupción explícita.

### H-04 — ALTO — La estructura de entrada no se valida y una enumeración denegada puede aprobar

**Ancla:** `core/verificar_apertura.py:475`, especialmente `:477` y `:480`; contraste con `_dir_estructural` en `:133`.

**Entradas → salidas medidas:** un fichero de texto ocupando `00_Input/01_Drive EV` → C1/C2 `pendiente` («el pull no ha corrido»). Un fichero ocupando `00_Input` → las cinco de red `pendiente`. Una `PermissionError` inyectada en `os.scandir` de la raíz de Drive, con remoto vacío → C1 **`ok`**, C2 `pendiente`; en Python 3.14 el `rglob` utilizado suprime el error de enumeración.

**Por qué es incorrecto:** ni una colisión de tipo ni la imposibilidad de recorrer el árbol equivalen a que el productor no haya corrido o a que existan cero ficheros. El caso de permisos se midió con un doble a nivel de sistema de ficheros, no cambiando las ACL reales.

### H-05 — ALTO — Un enlace que sale del expediente se valida como copia local

**Ancla:** `core/verificar_apertura.py:480`, `:481`, `:483`, `:563`, `:724`.

**Entrada → salida medida:** `00_Input/01_Drive EV/a.pdf` es un enlace simbólico a `tmp_path/outside.pdf`, **fuera del caso sintético**, con bytes `b'x'`; remoto `a.pdf` declara ese hash. C1 y C2 devuelven **`ok`**. El enlace se pudo crear y ejecutar en este Windows. Al romper su destino y usar remoto vacío, C1 sigue en `ok` y C2 en `pendiente`.

**Por qué es incorrecto:** `is_file()` y la apertura siguen el enlace, mientras `relative_to` se aplica al nombre léxico. No se acredita una copia contenida en el expediente ni se informa del enlace roto. Todos los destinos de esta sonda estaban dentro del workdir; no se leyó ningún fichero ajeno.

### H-06 — MEDIO — La exclusión de protocolo oculta documentos reales y es asimétrica

**Ancla:** `core/verificar_apertura.py:472`, `:481`, `:511`; productor en `core/intake_drive.py:856`.

**Entradas → salidas medidas:** local `a.pdf` más `.ajeno.pdf`, remoto solo `a.pdf` → C1/C2 `ok`; lo mismo con `sub/.pulled` conteniendo un documento ajeno. Local y remoto contienen únicamente `.documento.pdf`, con hash correcto → C1 **`fallo` por faltante**, aunque existe en ambos; C2 `ok` por H-02.

**Por qué es incorrecto:** se excluye cualquier basename que empiece por punto y los cuatro nombres de protocolo a cualquier profundidad, pero no se aplica esa exclusión al remoto. El propio productor dice en `intake_drive.py:859` que el único protocolo de **esa raíz** es `.pulled`, y que otros nombres de control pueden ser documentos de E&V. El test verde solo prueba el `.pulled` que el helper deposita siempre en la raíz; no justifica una exclusión universal.

### H-07 — ALTO — «Tiene alguna relación» no acredita partes ni identidad de la ficha

**Ancla:** `core/verificar_apertura.py:618`, `:619`, `:625`; `core/verificar_apertura_fuentes.py:208`.

**Entrada → salida medida:** `ExpedienteCRM(encontrado=True, cuantia='100', relaciones={'actuaciones':[{'id':'9'}]})`, **sin ninguna parte**, → C6 `ok` y C7 `ok`. Con los artefactos locales válidos, `completo_sin_partes` obtiene **9 ok / 0 pendientes / 0 fallos**. Una referencia `OTRO CASO (W-OTRO01)` con las mismas relaciones y cuantía tampoco altera los verdes.

**Por qué es incorrecto:** C6 cuenta indistintamente todos los bloques; una actuación puede satisfacer tanto «parte vinculada» como «actuación asociada». La referencia se reduce a un booleano de evidencia y ni siquiera su ausencia es condición de fallo. Tampoco se contrasta quiénes son los vinculados contra los esperados. Releer una relación cualquiera no cierra el defecto motivador de «id de otro deudor». El adaptador, además, toma `items[0]` sin comprobar su id contra el solicitado. No afirmo que el servidor ignore hoy el filtro: señalo que la identidad queda confiada a él, no verificada.

### H-08 — ALTO — El primer expediente oculta todos los demás

**Ancla:** `core/verificar_apertura.py:458`, `:466`, `:603`, `:640`, `:673`.

**Entrada → salida medida:** `_caso.md` registra `644/extrajudiciales` válido y `999/expedientes_judiciales` inexistente. Un doble que responde según el id produce C6/C7/C9 **`ok`**. Registro de llamadas: **tres veces `('644','extrajudiciales')`, ninguna a `999`**.

**Por qué es incorrecto:** la función decide por posición, sin criterio de vigencia ni advertencia sobre los expedientes omitidos. Para informar sobre toda la apertura debe comprobar los registrados o declarar expresamente el alcance pendiente. Si se desea comprobar únicamente el vigente, falta una política de selección sustentada en datos; el orden de la lista no acredita vigencia.

### H-09 — ALTO — Conversión numérica permisiva: `NaN` da coincidencia y valores inválidos dan pendiente

**Ancla:** `core/verificar_apertura.py:688`, `:691`, `:701`, `:711`.

**Entradas → salidas medidas:** local `100`, CRM `'NaN'` → C9 **`ok`**; `completo_nan` obtiene **9 ok / 0 pendientes / 0 fallos**. Local `'1e309'`, CRM `'2e309'` → ambos se convierten a infinito, la resta es NaN y C9 `ok`. `'roto'` contra `'mal'`, o `'1.234,56'` contra sí mismo, → ambos se convierten a `None` y C9 **`pendiente`: «ni _caso.md ni el CRM declaran cuantía»**, pese a `local_declarada=True` y `crm_declarada=True`.

**Por qué es incorrecto:** una comparación con NaN no satisface `> 0.005`; cae en la rama de coincidencia. Y se confunde ausencia con error de conversión. Los separadores de miles españoles e ingleses se convierten en dos puntos y fallan. La matriz posterior incluye números negativos y notación científica: los negativos iguales y exponentes finitos iguales sí acreditan igualdad; este diff no establece que una cuantía deba ser positiva, por lo que no los califico como falso positivo solo por su signo o formato.

### H-10 — MEDIO — El adaptador degrada una consulta fallida de relaciones a «no hay vínculos»

**Ancla:** `core/verificar_apertura_fuentes.py:210`, `:213`, `:218`; contrato del lector llamado en `core/sudespacho_relations.py:1862`.

**Entrada → salida medida:** respuesta válida de ficha por HTTP sintético y `get_relaciones` lanzando `SudespachoRelationsError('ERROR SINTETICO')` → `DeLaRed.expediente_crm` devuelve **`ExpedienteCRM(encontrado=True, relaciones={})`**, no `None`. C6 informa «no tiene NINGUNA parte», C7 «no tiene ninguna actuación», C9 puede seguir `ok` con la cuantía leída.

**Por qué es incorrecto:** se pierde la distinción contractual entre consulta imposible y lista vacía. C6/C7 terminan en fallo, por lo que **este escenario no es un falso verde global**, pero atribuyen al expediente una ausencia que no se pudo observar. El lector subyacente lanza precisamente para preservar esa distinción. Los dobles del puerto no recorren esta traducción.

### H-11 — MEDIO — Los tests de cableado dejan pasar integraciones rotas

**Ancla:** `tests/test_verificar_apertura.py:803`, `:809`, `:812`, `:996`, `:1063`.

**Mutaciones → salidas medidas:** (a) invertir `team_id/folder_id` y `exp_id/element` al llamar al puerto; (b) convertir en keyword-only esos argumentos de `DeLaRed`, conservando sus nombres; (c) sustituir `get_relaciones(elem, exp_id)` por `get_relaciones('actuaciones', exp_id)`. **Cada mutante por separado deja 31 passed, 1 skipped** en el conjunto seleccionado de tests nuevos/modificados.

**Por qué es incorrecta la cobertura que se les atribuye:** el doble responde igual a cualquier identificador, el test «POR_EL_LADO_DEL_EXPEDIENTE» no invoca el adaptador y la comparación `list(inspect.signature(...).parameters)` verifica nombres y orden, pero no `Parameter.kind`, defaults, tipos de retorno ni comportamiento. Con (b), la llamada posicional real lanza `TypeError`, aunque el test de contrato pase. La lógica de estados sí tiene controles positivos: sus mutantes dirigidos mueren. Lo que no está acreditado es el cableado y la traducción real.

### H-12 — BAJO — La afirmación «no se han debilitado» pierde una propiedad concreta

**Ancla:** `base/tests/test_verificar_apertura.py:89` frente a `head/tests/test_verificar_apertura.py:89`, `:104` y `:399`.

**Mutación → salida medida:** borrar en `Resultado.__post_init__` el `detalle` de cualquier `SIN_IMPLEMENTAR`. En `head`, los 31 tests seleccionados siguen verdes, incluidos el hueco sintético y su aviso en el CLI. Ejecutado el cuerpo del test antiguo sobre el núcleo de `base` cargado en memoria: control verde y mutante **muerto por AssertionError**.

**Por qué es una pérdida real:** se conservaron el conteo y el aviso, pero desaparecieron los asertos de que el hueco tenga un motivo no vacío y contenga «no construida». El texto sintético del doble aporta la explicación; la propiedad dejó de estar exigida al resultado. No invalida la separación de tests ni justifica recuperar el reparto obsoleto de cinco sin implementar.

### H-13 — MEDIO — El CLI anunciado no permite usar las cinco comprobaciones remotas

**Ancla:** `scripts/verificar_apertura.py:69` (llamada `va.verificar(base)`), `core/verificar_apertura.py:781`; plan §5, líneas 112–119.

**Escenario:** expediente con IDs de Drive y CRM correctos, cualquier disponibilidad real de ambos servicios → el CLI llama siempre sin fuentes, por lo que usa `SinRed` y las cinco terminan en fallo. La sonda del núcleo con IDs y `SinRed` mide esos cinco fallos. El CLI no tiene un argumento ni otra ruta que inyecte `DeLaRed`.

**Por qué es incompleto:** la API Python sí permite llamar `verificar(caso, DeLaRed())`; el problema no es su default cerrado. La prosa presenta la pieza como un **comando construido** que hace las nueve verificaciones, pero las cinco nuevas solo son utilizables por un llamador Python distinto del comando. No propongo abrir la red por defecto; falta un modo explícito de usar el adaptador desde la entrada anunciada.

### H-14 — MEDIO — Un censo declarado incompleto puede convertirse en un censo vacío válido

**Ancla:** `core/verificar_apertura_fuentes.py:141`, `:153`, `:161`, `:166`.

**Entrada → salida medida:** HTTP sintético 200 con `{'files': [], 'incompleteSearch': True}` → `DeLaRed.censo_drive` devuelve `[]`; local vacío → C1 `ok`, C2 `pendiente`. También un objeto `{}` se interpreta como `[]`, mientras `{'files': None}` termina en `None` y ambas comprobaciones fallan.

**Por qué es incorrecto:** no se preserva información de completitud, y la máscara `fields` ni siquiera pide ese indicador. La sonda acredita la reacción a una respuesta que declara estar incompleta; **no acredita que Drive haya emitido esa respuesta en producción**, ni evalúa la frecuencia de ese escenario. La ausencia de `files` por sí sola puede depender del contrato del servicio; no la trato como prueba independiente de corrupción real.

## A. Dictamen de las diez afirmaciones

| # | Dictamen y evidencia |
|---|---|
| 1 | **Confirmada en el núcleo.** Imports en `verificar_apertura.py:48–56`; el protocolo solo se importa bajo `TYPE_CHECKING`. El default importa `SinRed` en `:782`; las importaciones y llamadas HTTP del adaptador están dentro de sus métodos. El núcleo recibe el puerto y no ejecuta HTTP directamente. |
| 2 | **Parcial.** `SinRed` es el default (`:781–784`) y no produce `ok` en las cinco. Pero **no siempre produce fallo**: antes de consultar hay ramas de pendiente por falta de carpeta/IDs; H-03/H-04 muestran que también absorben corrupción. Con IDs y árbol válido se midieron cinco fallos. |
| 3 | **Confirmada en las cinco receptoras de `None`; incumplida en la traducción de algunos errores del adaptador.** Ramas `:506`, `:551`, `:609`, `:645`, `:681`; cinco controles dirigidos muertos. `[]` es un dato: local vacío + remoto vacío → C1 ok y C2 pendiente. H-10 muestra el error que nunca llega como `None`. `actuaciones=None` se normaliza a `[]` (`fuentes.py:76`) y C7 falla; no da ok. |
| 4 | **Cierta, insuficiente.** Se comparan `float`, no textos (`:688`, `:715`); `73140`/`'73140.00'` pasa y el mutante textual muere. H-09 delimita los errores de conversión, finitud y precisión. |
| 5 | **Cierta para el `.pulled` de raíz; excesiva e inconsistente en general.** `_PROTOCOLO` y `startswith('.')` en `:472–481`; H-06. |
| 6 | **Parcial.** Hay ramas de discrepancia, ausencia de hash y coincidencia (`:572–591`), y el caso mixto sin hash sale pendiente. Pero H-02 demuestra que puede llamar «coincidentes» a hashes nunca comparados. |
| 7 | **Confirmada en el código.** `fuentes.py:211` llama a `get_relaciones(elem, exp_id)`; el lector construye `related_register` en `sudespacho_relations.py:1876`; `ExpedienteCRM.actuaciones` lee ese bloque. La relación real del CRM está SIN VERIFICAR. El test de nombre enfático no acredita por sí solo esa ruta, H-11. |
| 8 | **Confirmada.** Marca `_necesita_fuentes` en `:147–150` y despacho por marca en `:800–812`. Las pruebas existentes de C5 siguen verdes con su argumento keyword-only; ya no se cuentan parámetros. La existencia histórica del bug previo al diff no puede medirse a partir de estas dos copias. |
| 9 | **Existe, pero no compara firmas completas.** `tests:1063–1069` compara listas de nombres. El mutante con un parámetro adicional muere; el de keyword-only sobrevive. |
| 10 | **Parcialmente falsa.** El nuevo reparto y la exclusión de huecos del cómputo se conservan con tests eficaces; el CLI conserva su aviso con un hueco sintético. La exigencia del motivo no vacío desaparece, medida en H-12. |

## B. Matriz de bordes solicitados

`H(x)` designa SHA-256 de los bytes `x`. Los estados son de la comprobación indicada, no un supuesto estado agregado.

| Entrada concreta | Resultado medido | Interpretación |
|---|---|---|
| Dos remotos `a.pdf` con hashes distintos; el último coincide | C1 ok / C2 ok | Falso verde, H-01. |
| Remoto `sub\\a.pdf`, local `sub/a.pdf`, mismos bytes | C1 fallo / C2 ok | C1 compara cadenas sin adaptar separadores; C2 no comparó esos bytes y aun así aprueba, H-02. |
| Remoto `A.PDF`, local `a.pdf` | C1 fallo / C2 ok | Comparación sensible a mayúsculas del censo aunque el entorno Windows admita el mismo acceso; no hay política de equivalencia. El ok de C2 es injustificado. |
| Remoto `café.pdf` NFD, local `café.pdf` NFC | C1 fallo / C2 ok | No se normalizan rutas. No presupongo que esos dos nombres deban unificarse sin política del productor; C2 vuelve a contar sin comparar. |
| Remoto `../fuera.pdf`, local `a.pdf` | C1 fallo / C2 ok | La ruta remota no se abre; no hay traversal remoto medido. El fallo de C1 evita el verde global estable. El traversal local por symlink es H-05. |
| Fichero en vez de carpeta de Drive | C1 pendiente / C2 pendiente | Colisión omitida, H-04. |
| Symlink de `a.pdf` a bytes fuera del caso | C1 ok / C2 ok | No acredita copia contenida, H-05. |
| `.documento.pdf` en ambos extremos | C1 fallo / C2 ok | Exclusión unilateral, H-06. |
| `.ajeno.pdf` o `sub/.pulled` solo en local | C1 ok / C2 ok | Documento sobrante ocultado, H-06. |
| Local cero bytes y remoto `H(b'')` | C1 ok / C2 ok | **Correcto como comparación de integridad**: los bytes coinciden. No acredita que un PDF vacío sea utilizable; no hay validación semántica del documento. |
| Local cero bytes y remoto `H(b'x')` | C2 fallo | Detectado correctamente. |
| Hash remoto correcto en MAYÚSCULAS | C2 ok | Correcto: compara hashes sin distinguir caja. |
| Remoto con hash, ausente en local | C1 fallo / C2 ok, contador sin hash = −1 | H-02; C1 lo detecta con una foto estable. |
| Remoto sin hash, ausente en local | C1 fallo / C2 pendiente | C1 lo detecta; C2 no prueba presencia. |
| Relaciones `{'clientes': [], 'actuaciones': []}` | C6 fallo / C7 fallo | Correcto: no basta que existan las claves. |
| `{'clientes':[{'id':'1'}], 'actuaciones': None}` | C6 ok / C7 fallo | No aprueba la actuación; se pierde la diferencia de forma/ausencia al normalizar a lista vacía. |
| `{'actuaciones':'no consultado'}` en el puerto | C6 ok / C7 ok | Falta validación de forma del puerto: se cuentan caracteres. **Fuera del tipo anotado**; no afirmo que el lector real, que es más estricto, produzca esta forma. |
| Dos expedientes registrados; segundo inexistente | C6/C7/C9 ok; solo se consulta el primero | H-08. |
| Entradas sin id, id vacío o no mapas | C6/C7/C9 pendiente; inválida tras válida → ok | H-03. |

### Cuantía: conversión y significado

| Local / CRM | Conversión | C9 medido | Juicio |
|---|---|---|---|
| `73140` / `'73140.00'` | 73140 / 73140 | ok (suite) | Correcto. |
| `'1.234,56'` / `'1.234,56'` | None / None | pendiente | No es ausencia: ambas declaran cuantía. |
| `'1.234,56'` / `'1234.56'` | None / 1234.56 | fallo | Igual importe bajo formato español; conversión no soportada y diagnóstico de ausencia falso. |
| `'1,234.56'` / `'1,234.56'` | None / None | pendiente | Mismo defecto con formato inglés. |
| `'1,234.56'` / `'1234.56'` | None / 1234.56 | fallo | Igual importe bajo formato inglés; no soportado. |
| `None` / `'0'`, y `0` / `None` | None / 0, y 0 / None | fallo / fallo | Correcto: ausencia no equivale a cero. |
| `-100` / `'-100'` | −100 / −100 | ok | Igualdad correcta; validez de una cuantía negativa no es una regla declarada aquí. |
| `'1e3'` / `'1000'` | 1000 / 1000 | ok | Notación científica finita correctamente comparada. |
| `100` / `'NaN'` | 100 / NaN | ok | Falso verde, H-09. |
| `'1e309'` / `'2e309'` | inf / inf | ok | Overflow aceptado como coincidencia. |
| `'roto'` / `'mal'` | None / None | pendiente | Datos inválidos se presentan como ausentes. |
| `'1,234'` / `'1.234'` | 1.234 / 1.234 | ok | Ambiguo: interpreta coma decimal, no miles. No puede aceptar simultáneamente ambas convenciones sin una política. |
| `'10000000000000000.00'` / `'10000000000000000.01'` | 1e16 / 1e16 | ok | Pierde el céntimo con float; borde extremo, no afirmación de importes reales del despacho. |

## C. Dobles y adaptador

El puerto fijo sí ejerce las ramas de decisión del núcleo, pero **no verifica sus argumentos**. El adaptador real añade autenticación, HTTP, parseo de dos envoltorios de respuesta, normalización del elemento, paginación y recorrido de carpetas. Nada de ello se ejercita en los controles con `_FuentesDobles`. No equivale a una traducción trivial acreditada por las firmas.

**Control independiente de Drive:** con HTTP doblado bajo `DeLaRed`, se recorrieron raíz `F` con páginas inicial/P2, subcarpeta `S` con inicial/S2 y nieta `N` con una página. Secuencia medida: `(F,None) → (F,P2) → (S,None) → (S,S2) → (N,None)`. Se devolvieron `a.pdf`, `b.pdf`, `sub/c.pdf` y `sub/nivel/d.pdf`, conservando hashes. **La paginación ordinaria y el recorrido de subcarpetas funcionan.** Aunque `pagina_token` se declara fuera del bucle exterior, al terminar cada carpeta queda vacío antes de pasar a la siguiente; no hay fuga del token entre carpetas en esa ejecución. Esto no prueba completitud del servicio real, shortcuts, ciclos o nombres patológicos.

**Control independiente de CRM:** con HTTP sintético y el lector `get_relaciones` real, se aceptaron tanto `items` como `hydra:member`, se pidió `cuantia`, se extrajo su valor textual y se visitó `related_register/extrajudiciales/644`. Se reprodujo asimismo la pérdida del error de relaciones de H-10. No hubo llamada real al CRM.

El test de integración marcado se omitió en las suites. Se ejecutó **su cuerpo original** aparte con HTTP sintético: control verde y mutante `DeLaRed.expediente_crm → None` rojo por el aserto «el adaptador no devolvió la forma del puerto». Esto verifica que ese cuerpo detecta ese defecto, **no elimina el SIN VERIFICAR de la integración real**.

## D. Ejecución y control positivo

Python **3.14.4**, pytest **9.0.3**, pytest-randomly **5.0.0** y xdist **3.8.0**. Semillas de la regla del proyecto: **777 y 31337**.

| Corrida / árbol | Semilla | `--runslow` | Resultado literal | Exit de pytest |
|---|---|---|---|---|
| `base-focused` / basecopy | 777 | no | 63 passed in 31.20s | 0 |
| `focused777` / copia | 777 | no | 92 passed, 1 skipped in 17.57s | 0 |
| `focused777slow` / copia | 777 | sí | 92 passed, 1 skipped in 29.35s | 0 |
| `focused31337slow` / copia | 31337 | sí | 92 passed, 1 skipped in 23.73s | 0 |
| `full777` / copia, suite general, -n 4 | 777 | no | 52 failed, 5119 passed, 86 skipped, 10 xfailed, 20 warnings, 4 errors in 430.60s (0:07:10) | 1 |
| `full31337slow` / copia, suite general, -n 4 | 31337 | sí | 53 failed, 5190 passed, 14 skipped, 10 xfailed, 27 warnings, 4 errors in 533.68s (0:08:53) | 1 |

Comandos efectivos, ejecutados desde la copia mediante `run_tests.py`, con el entorno aislado descrito arriba:

```text
python -m pytest -p no:cacheprovider tests/test_verificar_apertura.py --randomly-seed=777 --basetemp=../tmp/focused777 --tb=short
python -m pytest -p no:cacheprovider tests/test_verificar_apertura.py --randomly-seed=777 --runslow --basetemp=../tmp/focused777slow --tb=short
python -m pytest -p no:cacheprovider tests/test_verificar_apertura.py --randomly-seed=31337 --runslow --basetemp=../tmp/focused31337slow --tb=short
python -m pytest -p no:cacheprovider --randomly-seed=777 --basetemp=../tmp/full777 --tb=short -n 4
python -m pytest -p no:cacheprovider --randomly-seed=31337 --runslow --basetemp=../tmp/full31337slow --tb=short -n 4
```

Aquí `python` representa `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`. El wrapper imprime el retorno del subproceso (`EXIT 0/1`); su propio retorno de shell no es el retorno de pytest. Se usaron **cuatro workers** en las suites generales para limitar recursos, y ejecución en serie para el fichero aislado.

**La integración omitida es siempre** `test_integracion_el_adaptador_real_habla_con_el_CRM`, con motivo `sin SUDESPACHO_API_KEY: la integración con el CRM queda SIN VERIFICAR`. Activar `--runslow` no aporta credenciales ni revoca ese skip.

La diferencia de inventario del fichero es 63 casos en base frente a 93 en head (92 ejecutados + 1 omitido). Se ejecutaron asimismo las sondas ampliadas del núcleo/adaptador (**1 passed**), el control del cuerpo de integración (**1 passed**) y el control del antiguo aserto del motivo (**1 passed**, que contiene control verde y mutante esperado rojo). Las sondas externas a `tests/` emitieron una advertencia `PytestUnknownMarkWarning` al importar el test marcado `slow`; no se cuenta como integración ejecutada.

**Desglose de los rojos de las suites generales:**

| Módulo | Fallos 777 | Fallos 31337 + slow | Evidencia / límite |
|---|---:|---:|---|
| `test_anon_integration.py` | 0 | 1 | Presidio devuelve error por `AUDIT: network disabled`; solo se ejecuta con `--runslow`. |
| `test_case_mutex_concurrencia.py` | 1 | 1 | Mismo falso rechazo del prefijo extendido en un proceso hijo; no es evidencia de fallo del mutex. |
| `test_crm_ficha_cli.py` | 1 | 1 | `DID NOT RAISE FugaDeRedEnTest` en su control positivo; no adjudicado como regresión de este diff. |
| `test_email_export_mcp_server.py` | 6 | 6 | Sockets locales de infraestructura bloqueados por la barrera del revisor. |
| `test_expedientes_xl_integracion.py` | 1 | 1 | Socket local bloqueado; integración local no acreditada. |
| `test_expedientes_xl_server.py` | 36 | 36 | Sockets locales de infraestructura bloqueados por la barrera del revisor. |
| `test_expedientes_xl_winio.py` | 1 | 1 | La barrera del revisor interpreta incorrectamente el prefijo de ruta extendida `\\?\` como exterior. |
| `test_gitignore_no_inerte.py` | 3 | 3 | Requiere Git; las copias congeladas no tienen `.git`. |
| `test_session_close_no_pude_medir.py` | 2 | 2 | Espera un venv del repo; la copia usa el intérprete externo indicado por el mandato. |
| `test_sync_sudespacho.py` | 1 | 1 | Intento de resolución de nombre bloqueado por la barrera de red. |

Además hay **4 errores de colección en cada corrida**: el mismo módulo `test_llm_local.py` en los cuatro workers, al intentar consultar Ollama durante la colección. No son cuatro defectos independientes. No se escondieron estos resultados ni se cambiaron tests para obtener verde. El conjunto aislado del diff y sus controles sí tiene ejecución completa salvo la integración expresamente omitida.

### Mutantes dirigidos

El plugin de andamiaje `harness/review_mutants.py` recompila únicamente los módulos copiados en memoria antes del test y los restaura después. **Los tests del autor no se editaron.** Primero se ejecutó el mismo conjunto sin mutación: 31 passed, 1 skipped, 61 deselected. Después se aplicó una mutación específica por caso: **31 failed por aserto, 1 skipped, 61 deselected**, sin errores de setup o colección. No se cuentan excepciones de importación como mutantes muertos.

Se incluyen todos los casos nuevos ejecutables, los cinco parámetros nuevos del control transversal y los dos controles modificados que contextualizan el cambio. La integración omitida se cubre solo al nivel de cuerpo y HTTP sintético descrito arriba.

| Mutante | Test / parámetro (prefijo `test_`) | Cambio dirigido | Resultado |
|---|---|---|---|
| M-01 | `c1_FALLA_con_duplicados_que_el_remoto_no_tiene` | `c1_censo_remoto`: `en_local - en_remoto` → `set()` | MUERTO (aserto) |
| M-02 | `c1_FALLA_si_falta_un_fichero_del_remoto` | `c1_censo_remoto`: `en_remoto - en_local` → `set()` | MUERTO (aserto) |
| M-03 | `c1_ignora_los_ficheros_de_protocolo` | `_locales_de_drive_ev`: `p.name in _PROTOCOLO or p.name.startswith(".")` → `False` | MUERTO (aserto) |
| M-04 | `c1_ok_cuando_el_censo_cuadra` | `c1_censo_remoto`: `, OK,` → `, FALLO,` | MUERTO (aserto) |
| M-05 | `c2_FALLA_si_el_hash_local_no_es_el_que_Drive_declara` | `c2_hash_contra_drive`: `real.lower() != esperado.lower()` → `False` | MUERTO (aserto) |
| M-06 | `c2_lo_que_Drive_no_hashea_queda_SIN_comprobar_y_se_dice` | `c2_hash_contra_drive`: `, PENDIENTE,` → `, OK,` | MUERTO (aserto) |
| M-07 | `c2_ok_cuando_coinciden` | `c2_hash_contra_drive`: `, OK,` → `, FALLO,` | MUERTO (aserto) |
| M-08 | `c6_FALLA_si_el_CRM_no_encuentra_lo_que_caso_md_registra` | `c6_ficha_y_relaciones_crm`: `if not exp.encontrado:` → `if False:` | MUERTO (aserto) |
| M-09 | `c6_FALLA_si_el_expediente_no_tiene_ninguna_parte` | `c6_ficha_y_relaciones_crm`: `if not partes:` → `if False:` | MUERTO (aserto) |
| M-10 | `c6_ok_con_partes_vinculadas` | `c6_ficha_y_relaciones_crm`: `, OK,` → `, FALLO,` | MUERTO (aserto) |
| M-11 | `c7_FALLA_sin_actuacion_asociada` | `c7_actuacion_asociada`: `if n == 0:` → `if False:` | MUERTO (aserto) |
| M-12 | `c7_lee_las_actuaciones_POR_EL_LADO_DEL_EXPEDIENTE` | `c7_actuacion_asociada`: `n = len(exp.actuaciones)` → `n = 0` | MUERTO (aserto) |
| M-13 | `c9_FALLA_con_cuantias_distintas` | `c9_cuantia_coherente`: `if abs(n_local - n_crm) > 0.005:` → `if False:` | MUERTO (aserto) |
| M-14 | `c9_FALLA_si_el_CRM_tiene_cuantia_y_caso_md_no` | `c9_cuantia_coherente`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-15 | `c9_compara_NUMEROS_y_no_textos` | `c9_cuantia_coherente`: `if abs(n_local - n_crm) > 0.005:` → `if str(local) != str(exp.cuantia):` | MUERTO (aserto) |
| M-16 | `c9_pendiente_si_ninguno_declara_cuantia` | `c9_cuantia_coherente`: `, PENDIENTE,` → `, OK,` | MUERTO (aserto) |
| M-17 | `cada_comprobacion_implementada_PUEDE_decir_fallo[censo_remoto]` | `c1_censo_remoto`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-18 | `cada_comprobacion_implementada_PUEDE_decir_fallo[crm_actuacion]` | `c7_actuacion_asociada`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-19 | `cada_comprobacion_implementada_PUEDE_decir_fallo[crm_ficha]` | `c6_ficha_y_relaciones_crm`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-20 | `cada_comprobacion_implementada_PUEDE_decir_fallo[cuantia_coherente]` | `c9_cuantia_coherente`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-21 | `cada_comprobacion_implementada_PUEDE_decir_fallo[hash_drive]` | `c2_hash_contra_drive`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-22 | `cli_dice_SIEMPRE_lo_que_no_ha_comprobado` | `GLOBAL`: `if r.estado in ESTADOS_MEDIDOS` → `if r.estado in ESTADOS` | MUERTO (aserto) |
| M-23 | `el_adaptador_real_cumple_el_puerto` | Añadir parámetro `extra=None` solo a `DeLaRed.censo_drive` | MUERTO (aserto) |
| M-24 | `el_puerto_cerrado_es_el_default` | `c1_censo_remoto`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-25 | `las_nueve_estan_implementadas` | `c1_censo_remoto`: `PENDIENTE` → `SIN_IMPLEMENTAR` | MUERTO (aserto) |
| M-26 | `no_poder_consultar_es_FALLO_y_nunca_ok[censo_remoto]` | `c1_censo_remoto`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-27 | `no_poder_consultar_es_FALLO_y_nunca_ok[crm_actuacion]` | `c7_actuacion_asociada`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-28 | `no_poder_consultar_es_FALLO_y_nunca_ok[crm_ficha]` | `c6_ficha_y_relaciones_crm`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-29 | `no_poder_consultar_es_FALLO_y_nunca_ok[cuantia_coherente]` | `c9_cuantia_coherente`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-30 | `no_poder_consultar_es_FALLO_y_nunca_ok[hash_drive]` | `c2_hash_contra_drive`: `, FALLO,` → `, OK,` | MUERTO (aserto) |
| M-31 | `un_hueco_NO_contaria_como_comprobado` | `GLOBAL`: `if r.estado in ESTADOS_MEDIDOS` → `if r.estado in ESTADOS` | MUERTO (aserto) |
| M-32 | `integracion_el_adaptador_real_habla_con_el_CRM` | `DeLaRed.expediente_crm → None` | OMITIDO en suite; MUERTO al ejecutar su cuerpo con HTTP sintético, control previamente verde |

**Mutantes supervivientes, ejecutados por separado:** `swapped_ids`, `keyword_only`, `wrong_related_side` y `empty_detail`: **cada uno 31 passed, 1 skipped, 61 deselected**. Sus fronteras son H-11 y H-12. Un test puede matar una mutación del estado y dejar pasar una mutación de integración; matar el primer mutante no prueba todas las promesas de su nombre.

### Escrituras y salidas a red de los tests

En las corridas del fichero revisado no se registraron intentos de socket. Las escrituras de fixtures van a `tmp_path`; **openpyxl sí abre temporales `tmp/openpyxl.*` fuera del `tmp_path` individual**, dentro del temporal del proceso. Se midieron **14 aperturas de esos temporales por corrida de referencia del fichero**. La cabecera del test ya reconoce esa excepción. Las escrituras del plugin de mutación y de las sondas a los logs del workdir son del revisor, no del producto ni de los tests nuevos.

El test de integración nuevo intentaría consultar el CRM si tuviese credenciales y `--runslow`; aquí se saltó. **La suite general sí contiene intentos de red**, bloqueados antes de resolver/conectar: `test_llm_local.py` consulta disponibilidad de Ollama durante colección; pruebas de servidores MCP usan sockets locales; y tests de `test_crm_dedup_partes.py` y `test_sudespacho_relations.py::test_ensure_contrario_vinculado_existente` intentaron resolver el host del CRM. Son ficheros ajenos al diff. Se registró también una resolución de `x:443` en `test_sync_sudespacho.py`. Ninguno de esos intentos atravesó la barrera. No se presentan esos tests generales como aislados por sus propios dobles.

## E. La prosa frente al código

Las tres afirmaciones sobre el CRM real del plan §5, líneas 197–204 —nombre de la propiedad, parentesco de actuaciones y envoltorio de respuesta— quedan **SIN VERIFICAR contra el servicio**. El código sí hace lo siguiente, medido con respuestas sintéticas:

- Pide la propiedad literal `cuantia` (`fuentes.py:186`) y C9 la convierte a número; no valida todos sus valores, H-09.
- Lee `actuaciones` desde las relaciones del expediente (`fuentes.py:76`, `:211`), no desde un listado general de actuaciones.
- Acepta `items` y `hydra:member` (`fuentes.py:205`); se ejercieron ambos envoltorios.

Hay discordancias verificables sin CRM: el plan `:193` promete cinco fallos por defecto sin explicar las ramas previas de pendiente; `:207–208` promete una sola foto de censo/hash pero se midieron dos; la tabla `:130` todavía menciona `rclone lsf`, aunque el adaptador usa HTTP. La presentación del comando como construido omite H-13. El docstring del núcleo `:28–32` todavía dice que cinco comprobaciones no se han construido. La marca explícita del puerto sí coincide con lo construido. El test de integración se salta sin clave como dice el plan; no puede servir como confirmación de esta revisión.

## Inventario de lo NO cubierto

- Identidad documental entre cobertura y catálogo: C3 comprueba cardinalidad, como declara el código; no que sean los mismos documentos.
- Corrección material de los documentos, contenido del PDF, validez jurídica de la cuantía y suficiencia del trabajo descrito por una actuación. Hash idéntico de dos ficheros vacíos no acredita contenido útil.
- Validación completa de identidades y roles de todas las partes; política de expediente vigente; significado y completitud de cada bloque de relaciones. Los escenarios medidos muestran huecos, no una especificación sustitutiva.
- Exhaustividad de nombres y rutas: se probaron caja, NFC/NFD, separadores, salto `..`, colisiones, enlaces y permiso de enumeración doblado. No se agotaron junctions, ADS, rutas UNC, todos los caracteres reservados, nombres transformados por rclone/Drive Desktop ni carreras del sistema de ficheros.
- ACL reales, permisos remotos, accesos revocados a subcarpetas, Google Docs exportados, shortcuts, ciclos y reintentos/timeouts a escala real. La paginación se midió con cinco respuestas sintéticas, no con una carpeta real de más de 1.000 ficheros.
- Suite general verde: las corridas completas tienen fallos/errores de entorno y de la barrera descritos. No se han adjudicado como regresiones del diff ni resuelto cambiando código o tests del autor.
- No se calculó cobertura de líneas/ramas ni un porcentaje exhaustivo de mutation testing. La lista de mutantes es finita y dirigida; los supervivientes están declarados.
- No se volvió a auditar integralmente las cuatro comprobaciones locales de la entrega anterior. Sus tests sí se ejecutaron y las sondas completas las usaron para comprobar los nueve verdes.

## Lo que NO pude verificar

**SIN VERIFICAR:** Google Drive y el CRM reales; credenciales, permisos, datos de cualquier expediente real; las tres mediciones históricas del plan; que el contrato actual de los servicios coincida con las respuestas sintéticas; frecuencia en producción de censos parciales/duplicados; compatibilidad completa del flujo real de descarga y sus transformaciones de nombres; que los fallos generales pendientes desaparezcan en el entorno habitual del autor. No se consultaron los servicios ni se buscaron credenciales para cerrar estos huecos.

**Sí ejecutado:** suite del diff con las dos semillas y `--runslow`, suites generales con ambas semillas, control base, sondas del núcleo y del adaptador, controles positivos y mutantes supervivientes. El veredicto se apoya en los falsos verdes medidos, no en lo que queda sin verificar ni en los fallos introducidos por el aislamiento de la revisión.

## Hashes de cierre

| Fichero de `head` | SHA-256 al cierre | Coincide con apertura |
|---|---|---|
| `core/verificar_apertura.py` | `7e9de223de931c7f2f0f9b31bd680bd5d67bdab2030cf7026b1749a2b22f456b` | Sí |
| `core/verificar_apertura_fuentes.py` | `d83110ae8483afca014f697a2107396e6001813167d1ae28f743833bb5986dae` | Sí |
| `tests/test_verificar_apertura.py` | `2d3ae5a60248466a54677d09e887193206f23d613d3a5923b8850790b7448873` | Sí |

Recomputados al cierre: **los tres hashes son idénticos**. El `diff -ru` de cierre vuelve a mostrar exactamente los cuatro ficheros declarados (retorno 1, el normal cuando existen diferencias). No se escribió en `base` ni en `head`.

VEREDICTO: NO-SHIP
<!-- informe-literal:fin:p2rd -->

## 2. Evidencia verificada por mí, contra la fuente

La adjudicación razonada, hallazgo a hallazgo, vive en el §8 del plan hermano, que es el documento
que la decisión modificó. Aquí va la voz literal del revisor y nada más.
