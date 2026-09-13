---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-13-fila29-clave-de-cruce.md
objeto_rev: "1"
commit: 78afc7a
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: kx9w
sha256_informe: 32dff5969934321eead733b09bfe9e59712b833a4b1ad59c98753a39f356d172
adjudicado_en: docs/superpowers/plans/2026-09-13-fila29-clave-de-cruce.md §5
---

# Acta — R1 adversarial sobre el diff de la fila #29 (`MEJORAS #251` y `#252`)

Objeto: el **diff** `f97ee61..78afc7a`. Se archivaron las dos copias `git archive` y el
`DIFF.patch`; el revisor trabajó sobre ellas, sin `.git` y sin tocar el repositorio real.

| | |
|---|---|
| Revisor | Codex CLI `0.153.4`, binario `7ac07f4ce733f89a`, `model_reasoning_effort=high` |
| Objeto | `C:/t/obj-fila29-125133/{base,head}` + `DIFF.patch` (705 líneas) |
| `sha256` del diff, al abrir y al cerrar | `ee42d05769a84f3083fa4f8dc11d9470a3bb89de190c5b372e80437a2166b0ea` (idéntico; comprobado por las dos partes) |
| `sha256` del informe | `32dff5969934321eead733b09bfe9e59712b833a4b1ad59c98753a39f356d172` — **fichero crudo y bloque canonicalizado coinciden**, así que la cadena se verifica contra la salida del revisor |
| Veredicto | **NO-SHIP** |
| Hallazgos | 8 (2 `ALTO`, 4 `MEDIO`, 2 `BAJO`) — **8 confirmados, 0 refutados** |

**Una ronda que cambió el diseño, no solo el código.** Los dos `ALTO` dicen que el remedio
de la primera versión —una tabla plana que deshacía el `--local-encoding` de rclone— era
**inseguro**: cambiaba falsos descuadres, que gritan, por **falsos cruces, que callan**. En
una red de custodia ese intercambio es el prohibido. La tabla se retiró entera.

**El revisor declaró su propia higiene**, y se archiva: encontró un `_stdout.log` en su
workdir, lo enumeró y declaró no haberlo leído. También declaró que unos primeros intentos
de pytest murieron por permisos y que **sus logs no acreditan cobertura** — no los presentó
como evidencia.

**Y encontró dos mutaciones propias que SOBREVIVÍAN** a los 11 mutantes del autor (H-07).
Las dos están ahora en el arnés, como `M17` y `M18`.

## 0. Mandato, literal

<!-- mandato-literal:inicio:kx9w -->
# Mandato — Revisión adversarial R1 sobre un DIFF (FeesDefender, fila #29 / `MEJORAS #251` y `#252`)

## 0. Quién eres y qué se te pide

Eres el **revisor adversarial** de un cambio que otro agente (Claude) acaba de escribir y
que todavía **no está mergeado**. Auditalo con hostilidad técnica y devuelve hallazgos
**anclados a línea**. No eres el juez: quien adjudica cada hallazgo contra la fuente es
Claude. Tu valor está en ver lo que el autor no puede ver porque lo escribió él.

**Solo lectura sobre el objeto.** No modifiques `base/` ni `head/`. Si necesitas ejecutar,
**copia a tu workdir** y ejecuta la copia — incluidos los subagentes que uses, si usas
alguno. Al terminar te pediré el `sha256` del diff otra vez.

## 0-bis. Por qué este mandato está redactado como auditoría de completitud

El cambio es una **red de verificación de custodia**. Te pido que dictamines si su
cobertura es completa y exacta, y que construyas **controles positivos** (casos que la red
DEBE detectar) para comprobar que el instrumento mide lo que dice medir. Si alguna petición
te sonara a otra cosa, interprétala como auditoría de completitud y dilo.

## 1. El objeto, congelado

| | |
|---|---|
| Base (`main`, commit `f97ee61`) | `C:/t/obj-fila29-125133/base/` |
| Head (el cambio, commit `78afc7a`) | `C:/t/obj-fila29-125133/head/` |
| Diff unificado (705 líneas) | `C:/t/obj-fila29-125133/DIFF.patch` |
| `sha256` del diff **al abrir** | `ee42d05769a84f3083fa4f8dc11d9470a3bb89de190c5b372e80437a2166b0ea` |

Copias de `git archive`, **sin `.git`**: no puedes usar `git log`/`blame` ni acreditar
genealogía. Verifica **contenido y hash**, no procedencia. Recomputa el `sha256` del
`DIFF.patch` antes de nada y di si coincide.

## 2. Qué hace el cambio (tesis del autor, que tienes que poner a prueba)

`core/verificar_apertura.py` tiene dos comprobaciones que cruzan el censo remoto de Google
Drive contra los ficheros en disco: **C1** (censo: qué falta y qué sobra) y **C2** (el
`sha256` local contra el `sha256Checksum` que declara Drive). Cruzaban **por la ruta
cruda**, y el autor midió que eso produce dos fallos:

- Drive publica `Á` **descompuesta** (NFD) y el disco la tiene **precompuesta** (NFC): C1
  decía «1 falta y 1 sobra» con las dos rutas imprimiéndose idénticas, y **C2 dejaba de
  verificar el fichero** diciendo «no tiene hash en Drive con el que contrastar».
- `rclone` escribe en disco `␠NIE.jpg` (U+2420) los nombres que empiezan por espacio.

El remedio es `clave_de_cruce` (NFC + deshacer el encoding de rclone), más la detección de
**colisiones de clave**, más un diagnóstico que **prueba** el relleno de `MEJORAS #225`
rehasheando sin la cola de ceros, más que `abrir_caso` corra la verificación al terminar V1.

## 3. Las ocho preguntas que tienes que contestar

Para cada una: **ancla a `fichero:línea` del `head/`** y di si lo verificaste
**ejecutando** o **leyendo**. Un hallazgo que no puedas anclar no lo incluyas.

**P1 — ¿`clave_de_cruce` es correcta y completa?** (`head/core/verificar_apertura.py`).
¿La tabla `_DESHACER_ENCODING_RCLONE` corresponde de verdad al `--local-encoding` que el
pull pasa a rclone? Búscalo en `head/core/intake_drive.py` y compara. ¿Falta algún
carácter? ¿Sobra alguno que rclone NO codifique, de modo que el cruce una dos ficheros
distintos? El autor excluyó `／` (U+FF0F) a propósito: dictamina si esa exclusión deja un
hueco peor que el que evita. **Y el orden**: normaliza NFC y *después* traduce — ¿puede
ese orden producir un resultado distinto del inverso en algún carácter?

**P2 — ¿El cruce canónico puede FUNDIR dos ficheros distintos?** Es el riesgo simétrico
del que el cambio arregla. Si dos ficheros del remoto o dos del disco colapsan a la misma
clave, ¿se detecta **siempre**? El autor solo comprueba colisiones **del remoto**
(`vistas`): ¿qué pasa con dos ficheros **locales** que colapsan? Construye el caso y
ejecútalo.

**P3 — ¿`_es_el_relleno_de_225` prueba lo que dice probar?** Afirma que si el re-hash sin
la cola de ceros cuadra con el de Drive, está **demostrado** que es el original con relleno
detrás. Dictamina si esa afirmación es exacta. ¿Hay entradas para las que dé un falso
positivo? ¿Y su manejo del streaming —`seek`, el tope `_MAX_COLA_RELLENO`, el bucle de
lectura— es correcto para un fichero grande, para uno de exactamente 512 bytes, para uno
que sea todo ceros? **Construye los casos límite y ejecútalos.**

**P4 — ¿C2 sigue midiendo lo que medía?** El cambio toca el bucle de contraste. ¿Algún
camino que antes contaba como `contrastado`, `ilegible` o `sin_hash_remoto` cambió de
categoría sin querer? Compara `base/` y `head/` línea a línea en esa función.

**P5 — El encadenado en `abrir_caso` (`MEJORAS #252`).** ¿`_informar_v1_y_verificar` puede
romper la apertura, cambiar su código de salida, escribir algo, o correr bajo el mutex?
Localiza el punto de llamada en `head/scripts/abrir_caso.py` y dictamina. ¿El `except
Exception` es demasiado ancho —se traga un `KeyboardInterrupt`, un `SystemExit`, un
`typer.Exit`—? ¿Qué pasa si `DeLaRed()` revienta en el constructor?

**P6 — ¿Los tests prueban lo que dicen?** Los 14 nuevos están en
`head/tests/test_verificar_apertura.py` (busca `test_n1`…`test_n11`) y
`head/tests/test_apertura_v1_etapas.py` (`test_e1`…`test_e3`). Para cada uno: **¿pasaría
también con el código de `base/`?** ¿Hay asertos **tautológicos** —que saquen su
expectativa de la propia salida, o que comprueben que una clave existe en un dict en vez de
su contenido—? El autor dice haber corregido uno de ese tipo; busca si quedan más.

**P7 — El arnés de mutación.** `head/tests/_mutantes_mejoras_251.py` declara **11 mutantes,
11 muertos**. **Ejecútalo** (copia el árbol a tu workdir primero) y di si es cierto.
Después elige **dos mutaciones tuyas**, distintas de esas once, que rompan una propiedad
que el cambio afirma, y di si la suite las detecta. Si sobreviven, es un hallazgo.

**P8 — La suite, con las dos semillas.** Copia `head/` a tu workdir y corre:

```
C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest -q --tb=short -p randomly --randomly-seed=777 --basetemp=bt777
```

y lo mismo con `--randomly-seed=31337`. Ese Python tiene `pytest`, `yaml`, `dotenv`,
`typer`, `httpx`, `filelock`, `xdist`, `hypothesis`, `syrupy`, `pytest-randomly`, `PIL` y
`fitz`. Usa `--basetemp` **relativo y corto** dentro de tu workdir (MAX_PATH tumba tests
sanos, y tu sandbox no puede crear en `C:\t\`). Di el conteo exacto de cada semilla y
separa los rojos **de plataforma** reproduciéndolos sobre `base/`.

## 4. Formato del informe

Escribe **`INFORME.md`** en tu workdir (`C:/t/rev-fila29-125133/`):

1. **Integridad**: `sha256` del diff al abrir y al cerrar.
2. **Qué ejecutaste y qué solo leíste.** Lo que no pudiste ejecutar se declara **SIN
   VERIFICAR**, nunca «correcto».
3. **Hallazgos** `H-01`, `H-02`…, cada uno con severidad (`ALTO`/`MEDIO`/`BAJO`), ancla
   `fichero:línea`, qué propiedad rompe, **un caso concreto de entrada → salida
   incorrecta**, y si lo verificaste ejecutando o leyendo.
4. **Inventario de lo NO cubierto** por tu revisión.
5. **Última línea: el veredicto**, exactamente una de estas seis palabras:

```
SHIP
LISTA-CON-CAMBIOS
REQUIERE-REVISION
NO-SHIP
NO-EJECUTABLE
SIN-VEREDICTO
```

## 5. Higiene del workdir

Tu directorio debe contener **solo este `MANDATO.md`** cuando empieces. Si encuentras otro
fichero, **no lo leas**: decláralo en la primera línea del informe.

## 6. Lo que NO se te pide

No propongas refactorizaciones de estilo, no reescribas el cambio y no toques el
repositorio real (`C:/Users/tnm33/Dev/FeesDefender`). Y no ablandes un hallazgo por
cortesía: el autor prefiere un `NO-SHIP` correcto a un `SHIP` amable.
<!-- mandato-literal:fin:kx9w -->

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:kx9w -->
Higiene inicial: además de `MANDATO.md` existía `_stdout.log`; se detectó por su nombre y NO se leyó.

# Revisión adversarial R1 — fila #29, MEJORAS #251 y #252

## Integridad y alcance

Objeto recibido como dos archivos de árbol sin `.git`. No se acredita genealogía ni relación entre commits: se comprueba contenido.

- SHA-256 de `DIFF.patch` al abrir: `ee42d05769a84f3083fa4f8dc11d9470a3bb89de190c5b372e80437a2166b0ea`. **Coincide** con el mandato.
- Diff: **705 líneas**; 1.314 ficheros en base y 1.315 en head. Los cinco ficheros distintos son los dos módulos de producción, los dos módulos de tests y el arnés de mutación.
- SHA-256 al cerrar: `ee42d05769a84f3083fa4f8dc11d9470a3bb89de190c5b372e80437a2166b0ea`. **Coincide** con el de apertura. También se rehashearon todos los ficheros de base y head contra el inventario intermedio: sin cambios (`integrity_close.json`).
- No se escribió en `C:/t/obj-fila29-125133/base/`, `head/` ni en el repositorio real. Ejecuciones y mutaciones sobre copias dentro de `C:/t/rev-fila29-125133/`. Inventario de contenidos: `object_inventory.json`.

Interpreto el encargo como auditoría de completitud y exactitud del instrumento de custodia. Los controles son ficheros y respuestas remotas sintéticos. El veredicto es mi recomendación técnica; Claude adjudica contra la fuente.

## Qué ejecuté y qué leí

**Ejecutado:** las dos semillas pedidas; los 14 tests nuevos contra producción de head y de base; controles C1/C2 sobre nombres, colisiones y categorías; límites y streaming del relleno; excepciones del constructor; recorrido de renovación de token con subprocess y HTTP doblados; entrada real del CLI con secuencia y mutex sintéticos; arnés de 11 mutantes sobre copia limpia; dos mutaciones adicionales. Los resultados y límites de cada ejecución se detallan en P1–P8.

**Leído:** diff completo y código circundante de C1/C2, enumeración local, adaptador de fuentes, flags del pull, renovación de token y encadenado V1. Para rclone consulté su documentación y su implementación oficial pública; **no ejecuté un pull ni un binario real de rclone**. Las reglas de encoding se contrastaron por lectura y los resultados del verificador mediante ejecución.

Los intentos iniciales de pytest arrancados con la subcarpeta como `workdir` de la herramienta sufrieron `PermissionError` al crear sus temporales. Una sonda mínima aisló el problema: arrancar en el workdir autorizado y hacer `Set-Location` dentro del proceso permitió la escritura. Se interrumpieron esos intentos; sus logs `intento*_permisos.log` no acreditan cobertura. Tampoco se acredita el ensayo intermedio sobre `m/`, que quedó alterado tras la interrupción. El arnés válido usa una nueva copia `z/` y registra cada subprocess en `harness_cases.jsonl`. Ninguna interrupción afectó al objeto congelado.

## Hallazgos

### H-01 — ALTO — La traducción global acepta sustituciones de identidad que rclone no hace

**Ancla:** `head/core/verificar_apertura.py:567`, `:568`, `:596`, `:636` y `:754`.

**Propiedad rota:** C1 y C2 deben cruzar el mismo objeto, respetando el encoding efectivo. `LeftSpace`, `RightSpace`, `LeftPeriod` y `RightPeriod` dependen de la posición dentro de cada segmento. `str.translate` modifica cualquier posición y además se aplica también al nombre crudo del remoto.

**Entrada → salida incorrecta:** remoto único `a b.txt`, hash de `b'x'`; disco único `a␠b.txt`, contenido `b'x'`. C1 devuelve `ok`, faltan/sobran/colisiones vacíos; C2 devuelve `ok`, `contrastados=1`, `sin_hash_remoto=0`. El espacio interior no se codifica así: el nombre esperado en disco es `a b.txt`. Se acepta como presente un objeto con identidad distinta. Igual resultado para remoto `a.b.txt` y local `a．b.txt`.

**Verificación:** ejecutado, `controls_head.json`, casos `interior_space` e `interior_period`; base los denuncia. No hace falta una colisión interna: hay un nombre por lado, por lo que `vistas` no protege este caso. Las reglas posicionales constan en la [implementación oficial del encoder](https://github.com/rclone/rclone/blob/master/lib/encoder/encoder.go).

### H-02 — ALTO — La tabla no cubre el encoding que activa el pull

**Ancla:** `head/core/verificar_apertura.py:564`; contraste con `head/core/intake_drive.py:76` y `:78`.

**Propiedad rota:** la corrección se presenta como cierre del cruce rclone, pero deja documentos sin contraste bajo el mismo diagnóstico engañoso que motivó el cambio.

**Entrada → salida incorrecta:** remoto `a[1].txt` con hash de `b'x'`; local `a［1］.txt` con esos bytes. C1: `fallo`, «1 falta y 1 sobra». C2: `pendiente`, `contrastados=0`, `sin_hash_remoto=1`, aunque el remoto sí publicó hash. `SquareBracket` está activado y faltan `［`/`］`. También se reproduce con remoto `a\u0001b.txt` y local `a␁b.txt`: falta `Ctl`.

No basta con añadir caracteres a una tabla global: tampoco se interpreta el escape `‛` de rclone. Remoto `a？.txt`, local `a‛？.txt` → el mismo falso descuadre y hash sin contrastar. Faltan el tratamiento del NUL implícito, de los controles y del escape; `InvalidUtf8` tampoco tiene decodificador, aunque no se ha demostrado una entrada con bytes UTF-8 inválidos procedente de la API JSON de Drive. `Slash` es otra exclusión, discutida expresamente en P1.

**Verificación:** ejecutados los tres ejemplos (`brackets`, `control_char`, `quoted_fullwidth`); leído el flag y la [tabla oficial de encoding de rclone](https://rclone.org/overview/#encoding). No atribuyo al cambio la introducción de estos tres fallos: son huecos que persisten y contradicen su completitud declarada.

### H-03 — MEDIO — Normalizar antes de traducir rompe equivalencias canónicas válidas

**Ancla:** `head/core/verificar_apertura.py:596`.

**Propiedad rota:** el resultado de `clave_de_cruce` no queda necesariamente en NFC.

**Entrada → salida incorrecta:** remoto `<\u0338.txt` y local `＜\u0338.txt`, ambos con contenido `b'x'`. El remoto se normaliza a `≮.txt`; el local se normaliza primero, luego se traduce a `<\u0338.txt`, sin la composición posterior. C1 da «1 falta y 1 sobra» y C2 `pendiente`, cero contrastados. `>` seguido de U+0338 tiene el mismo problema con `≯`.

**Verificación:** ejecutado (`normalization_cross`). Barrido de los diez caracteres de la tabla contra 934 caracteres con clase combinante distinta de cero: dos diferencias de orden, `＜ + U+0338` y `＞ + U+0338`. No es un barrido exhaustivo de todas las cadenas Unicode.

### H-04 — MEDIO — C2 sobreescribe el hash ante colisiones y cambia lo que acredita

**Ancla:** `head/core/verificar_apertura.py:751`, `:754` y `:762`.

**Propiedad rota:** conservar la discrepancia del objeto contrastado y no atribuirle el checksum de otro.

**Entrada → salida incorrecta:** remoto `[('a.b.txt', sha('good')), ('a．b.txt', sha('bad'))]`; disco `a.b.txt = b'bad'`. Base denuncia el hash distinto. Head conserva el último hash del dict y C2 devuelve `ok`, `discrepan=[]`. El resultado depende del orden del censo.

Segundo caso: remoto `Á.txt` sin hash y `A\u0301.txt` con hash de `b'x'`; los dos nombres existen en disco con esos bytes. Base: uno contrastado y uno sin hash, `pendiente`. Head: dos contrastados, cero sin hash, `ok`. El segundo checksum se presta al objeto que carecía de él.

**Verificación:** ejecutado en ambas versiones, `remote_collision_last_hash` y `remote_collision_nohash`. **Límite de impacto:** C1 sí marca estas colisiones como fallo; no afirmo un informe global verde en estos dos casos. El defecto está en la conclusión y evidencia propias de C2.

### H-05 — MEDIO — El diagnóstico de relleno puede confirmar una combinación de dos versiones del fichero

**Ancla:** `head/core/verificar_apertura.py:696`, `:700`, `:701`, `:706` y `:716`.

**Propiedad rota:** la afirmación de «demostrado» exige que prefijo y cola pertenezcan a la misma versión. La función observa la cola y después vuelve al principio, sin validar estabilidad.

**Entrada → salida incorrecta:** tamaño declarado 512; primera lectura entrega `b'A' + 511 ceros`; antes del segundo `seek`, el contenido pasa a `b'B' + 511 b'X'`; hash remoto = SHA-256 de `b'B'`. La función devuelve `True`. Ni la primera versión ni la segunda son `B` con relleno de ceros. El control usa un stream que cambia de versión en el segundo `seek`, sin depender de acertar una carrera por tiempo.

**Verificación:** ejecutado, `padding.race_two_versions`. La protección frente a un `read()` vacío no detecta una modificación del mismo tamaño. C2 mantiene `fallo` por discrepancia; el falso positivo afecta a la etiqueta `relleno_225_confirmado`, no suprime el fallo.

También hay una discrepancia de contrato en el límite: el comentario `:670` promete una cola menor de 512, pero `512 bytes de x + 512 ceros` y `1.024 ceros` frente al hash de 512 ceros devuelven `True`. Sí acreditan un prefijo más ceros bajo lectura estable; no acreditan el límite declarado ni la causa histórica #225.

### H-06 — BAJO — «No escribe nada» no cubre la renovación indirecta de credenciales

**Ancla:** `head/scripts/abrir_caso.py:947`, `:958` y `:959`; recorrido por `head/core/verificar_apertura_fuentes.py:193` hasta `head/core/intake_drive.py:515`.

**Propiedad rota:** ausencia absoluta de escrituras atribuida al nuevo informe.

**Entrada → salida incorrecta:** caso con IDs de Drive y token caducado → `_verificar_expediente` desencadena `rclone config show gdrive_ev`, `rclone about gdrive_ev:`, y nueva lectura de configuración. El segundo comando renueva credenciales y puede reescribir la configuración de rclone; el propio productor lo documenta en `head/core/intake_drive.py:465`.

**Verificación:** recorrido ejecutado con subprocess y HTTP sintéticos, `token_refresh_commands`. La escritura real del archivo de credenciales **no se ejecutó**. No se ha encontrado una escritura nueva sobre el expediente desde este helper; la distinción entre expediente y configuración es material y limita la severidad.

### H-07 — MEDIO — Los tests no cierran la llamada desde main ni el streaming de más de un bloque

**Ancla:** `head/tests/test_apertura_v1_etapas.py:397`, `:403`; `head/tests/test_verificar_apertura.py:1708`, `:1720`; producción en `head/scripts/abrir_caso.py:1636` y `head/core/verificar_apertura.py:708`.

**Propiedad rota:** que las pruebas detecten la desconexión real de V1 y una regresión de streaming.

**Entrada → salida incorrecta del instrumento de prueba:** U1 sustituye únicamente la llamada de `main` por `_informar_v1(resultado_v1)`, dejando intacto el helper probado. Una invocación V1 completa sale 0 y hace **cero** llamadas al verificador; head hacía una, fuera del mutex. Los tests de los dos ficheros afectados siguen verdes: 166 pasados, 1 omitido.

U2 sustituye `while por_leer > 0` por `if por_leer > 0`: un fichero válido con original de 3.145.745 bytes y relleno hasta 3.146.240 pasa de `True` a `False` porque solo se rehashea el primer MiB. También sobrevive a los 167 tests afectados. Las corridas completas de ambos mutantes y la repetición de los tests inicialmente bloqueados no producen ningún resultado rojo adicional respecto de head; P7/P8 detallan los límites de esta comparación.

**Verificación:** ejecutados los controles de comportamiento (`cli_head.json`, `cli_mutant.json`, `own_mutant_positive.json`) y las suites descritas en P7. Estas mutaciones son distintas de M09 —que elimina la llamada *dentro del helper*— y de los otros diez mutantes del autor.

### H-08 — BAJO — La orden de detalle que imprime el CLI no se puede copiar con el case_id real

**Ancla:** `head/scripts/abrir_caso.py:971`, `:972` y `:1636`.

**Propiedad rota:** imprimir una orden utilizable con la identidad recibida.

**Entrada → salida incorrecta:** la entrada real de V1 resuelve `ident.case_id` a `BaTEST - Calle Falsa 1 (W-TEST01) - Bad debt`. Se imprime `python -m scripts.verificar_apertura --case-id BaTEST - Calle Falsa 1 (W-TEST01) - Bad debt --con-red`, sin comillas. Tokenizada como argumentos sin agrupar el identificador, Typer devuelve 2 por argumentos extra. En PowerShell los paréntesis añaden además sintaxis de shell; no ejecuté esa línea en el shell.

**Verificación:** identidad observada ejecutando el CLI sintético y rechazo ejecutado con `CliRunner`, `suggested_command.json`. E1 usa `W-TEST01`, sin espacios, y no alcanza esta impresión real.

## Respuestas a las ocho preguntas

### P1 — Clave y encoding

**No es completa ni exacta.** H-01, H-02 y H-03, con controles ejecutados. Se leyó `_LOCAL_ENCODING` (`head/core/intake_drive.py:76`) y se contrastó con la tabla (`head/core/verificar_apertura.py:564`). Todos los diez caracteres incluidos corresponden a alguna regla activa, pero `␠` y `．` se deshacen donde no procede, y se aplica la misma transformación al remoto crudo. Faltan corchetes, controles, NUL implícito y semántica de escape. El flag `InvalidUtf8` tampoco está implementado; su materialización desde Drive JSON queda SIN VERIFICAR.

**Barra:** la exclusión de `／` (`head/core/verificar_apertura.py:561`) deja el caso remoto `a/b.txt` frente a local `a／b.txt` sin contraste: ejecutado, C1 fallo y C2 pendiente. No juzgo que ese hueco sea peor que introducir un separador falso: añadir `／ → /` globalmente permitiría confundir un nombre con una jerarquía. El adaptador ya aplana nombres y jerarquía en `head/core/verificar_apertura_fuentes.py:174`; una solución completa necesita conservar segmentos/identidades. La exclusión conservadora es defendible; la cobertura no es completa.

**Orden:** sí cambia el resultado para `<`/`>` con U+0338; H-03. Normalización posterior y tratamiento correcto del encoding son problemas relacionados, pero resolver uno no resuelve el otro.

### P2 — Fusión y colisiones locales

**Ejecutado**, `local_collision`, `both_collision` y los casos de H-01/H-04. Anclas: `head/core/verificar_apertura.py:636`, `:637`, `:647`, `:650`, `:751`.

En Windows de esta ejecución **coexisten** dos ficheros reales `Á.txt` y `A\u0301.txt`. La afirmación de que «no caben los dos» (`:644`, `:659`) es falsa como afirmación general de Windows. Con un único remoto y esos dos locales, C1 falla por un sobrante, aunque `colisiones_de_clave=[]`; C2 contrasta ambos contra el mismo hash y puede dar `ok`.

No hay un falso verde de C1 causado solo por omitir la lista de colisiones locales: si la multiplicidad local de una clave es >1, o difiere de la remota y salta el Counter, o la remota también es >1 y salta `vistas`. Esto se sostiene para un censo completo enumerado sin error. No deben confundirse **detección de desbalance** y **diagnóstico explícito de colisión local**. El falso verde grave es el cruce de un nombre distinto por lado (H-01); la pérdida de exactitud de C2 consta en H-04.

### P3 — Relleno, límites y streaming

Anclas: `head/core/verificar_apertura.py:675`, `:697`, `:700`, `:703`, `:708`, `:716`. **Ejecutado** en `controls.py`:

| Entrada local | Original/hash de referencia | Resultado |
|---|---|---|
| Vacío | vacío | False |
| `x` + 511 ceros, 512 bytes | `x` | True |
| 512 `x`, sin cola de ceros | 511 `x` | False |
| 512 ceros | vacío | False |
| 1.024 ceros | 512 ceros | True |
| 512 `x` + 512 ceros | 512 `x` | True |
| `x` + 511 ceros | `x` + un cero legítimo | False |
| `x` + 7 ceros, no alineado | `x` | False |
| Original 3.145.745 bytes + 495 ceros | hash del original completo | True |
| Stream con lecturas parciales de hasta 7 bytes | original 700 `x` | True |
| Stream truncado respecto del stat | original 600 `x` | False |
| Cola de una versión y prefijo de otra | hash de `B` | **True incorrecto**, H-05 |

En un archivo **estable**, el hash coincidente del prefijo y una cola de ceros observada acreditan esa relación de bytes bajo el supuesto habitual de integridad de SHA-256. No acreditan quién añadió los ceros ni que la causa fuese #225. No construí colisiones criptográficas y no son necesarias para H-05.

El bucle acota lecturas de prefijo a 1 MiB y maneja lecturas cortas/EOF. La cola usa `read()` sin tamaño: en un fichero estable lee hasta 512 bytes, pero si crece tras el stat puede leer más; no existe un límite estricto de memoria bajo modificación concurrente. La función no quita necesariamente la cola **entera** si hay más de 512 ceros. Los falsos negativos con ceros legítimos son la política conservadora expresamente declarada.

### P4 — Categorías y contraste contra base

**Leído línea a línea:** base `core/verificar_apertura.py:616`–`:670` frente a head `core/verificar_apertura.py:731`–`:790`. Se mantienen las salidas tempranas, `except OSError`, posición de `contrastados += 1`, cómputo de `sin_contrastar` y prioridad de ilegibles/discrepancias/pendientes. La nueva etiqueta no retira ficheros de `discrepan`.

**Ejecutado** un caso mixto independiente en ambas versiones: cuatro locales, uno coincidente, uno discrepante, uno ilegible mediante `PermissionError` y uno sin checksum. Ambas dan 2 contrastados, 1 ilegible, 1 sin hash, 1 discrepante y estado fallo. Logs: `category_head.json` y `category_base.json`.

Sí cambian indebidamente categorías por el nuevo índice: un remoto sin checksum puede aparecer contrastado y una discrepancia puede desaparecer por colisión (H-04); los huecos de encoding siguen etiquetándose como falta de hash remoto (H-02). No he detectado una regresión aritmética independiente del cruce.

### P5 — Encadenado V1

**Leído y ejecutado con dobles en las fronteras.** Anclas: `head/scripts/abrir_caso.py:1520`, `:1571`, `:1572`, `:1632`, `:1636`, `:1637`, `:990` y `:993`.

La llamada nueva está después de salir del `with` del mutex y después del cierre durable. El control del CLI observa una llamada con `held=false`, salida 0 para estado completo. La línea `:1637` sigue calculando el código con el estado V1; un resultado negativo del informe no lo cambia. Las ramas que lanzan antes de alcanzar ese punto, y el modo libre, no ejecutan la nueva llamada.

| Excepción en `DeLaRed()` | Conducta ejecutada del wrapper |
|---|---|
| `RuntimeError('constructor boom')` | aviso explícito; retorna |
| `KeyboardInterrupt` | se propaga |
| `SystemExit(9)` | se propaga |
| `typer.Exit(7)` | aviso; se absorbe como `Exception` |

`except Exception` no se traga las dos excepciones que heredan directamente de `BaseException`; sí `typer.Exit`. Un constructor que revienta con una excepción ordinaria cae dentro del try del wrapper y deja el expediente SIN COMPROBAR. No ejecuté una apertura real ni una interrupción humana sobre un proceso real de apertura. Los fallos de impresión en `_informar_v1`, situado antes del try, o en el propio aviso también pueden propagarse: la promesa absoluta de que nunca cambia la salida es demasiado amplia, aunque la vía normal conserva el código. Escritura indirecta de credenciales: H-06; orden de detalle inutilizable: H-08.

### P6 — Los 14 tests, uno por uno

Se trasplantaron únicamente los dos ficheros de tests de head a la copia de base y se ejecutaron los 14 seleccionados; después se restauraron los tests originales de base. Producción de base permaneció intacta. **Head: 14 pasados. Base: 14 fallidos, 153 deseleccionados.** Evidencia `p6_head.log` y `p6_base.log`.

| Test y ancla en head | ¿Pasa con base? | Qué demuestra realmente |
|---|---|---|
| n1, `tests/test_verificar_apertura.py:1613` | No: aserto de estado | C1 acepta ese par NFC/NFD. |
| n2, `:1624` | No: contrastados 0 frente a 1 | C2 contrasta ese par. |
| n3, `:1638` | No: pendiente frente a fallo | Una discrepancia bajo ese par Unicode sigue visible. No fija su ruta exacta. |
| n4, `:1653` | No: estado fallo | Espacio inicial; no cubre posición interior, final o escapes. |
| n5, `:1667` | No: estado fallo | Un signo `?`; no prueba la clase completa del flag. |
| n6, `:1685` | No: KeyError de `colisiones_de_clave` | La lista no está vacía y el detalle dice colisión. No fija contenido/cardinalidad exactos ni colisiones locales. |
| n7, `:1708` | No: KeyError de `relleno_225_confirmado` | Caso positivo de relleno menor de un bloque. Lista esperada independiente y concreta. |
| n8, `:1731` | No: KeyError del nuevo campo | Alteración corta no alineada, sin relleno; no alcanza el rehash. |
| n9, `:1746` | No: KeyError del nuevo campo | Ceros finales legítimos, caso conservador. |
| n10, `:1763` | No: KeyError del nuevo campo | 512 bytes con cola pero hash incorrecto; sí alcanza la comparación final. |
| n11, `:1782` | No: KeyError del nuevo campo | Tamaño no múltiplo de 512 con prefijo correcto. |
| e1, `tests/test_apertura_v1_etapas.py:397` | No: AttributeError al instalar el doble | Invoca el helper directamente; no prueba su llamada desde main ni el helper real de verificación. |
| e2, `:408` | No: AttributeError al instalar el doble | `RuntimeError` ordinario no escapa del wrapper. Que no lance es un resultado comprobable, aunque no lleve `assert`. |
| e3, `:419` | No: AttributeError al instalar el doble | El mensaje de error se imprime con contenido concreto. |

**Tautologías:** no encontré expectativas extraídas de la propia salida en estos 14. n6 comprueba el contenido no vacío de la lista, ya no la mera presencia de la clave. Los accesos a campos de n7–n11 no son tautologías: comparan contra listas predeterminadas; su fallo con base por KeyError, sin embargo, no acredita por sí solo el comportamiento nuevo. Los `in str(discrepan)` de n7/n9 son asertos parciales de contenido, no igualdad exacta, pero tampoco son tautológicos. El hueco medido es de alcance, H-07.

### P7 — Mutación

**Sí: 11 mutantes, 11 muertos en la copia limpia.** `head/tests/_mutantes_mejoras_251.py:89`–`:124`. Se ejecutó su `main()` sin cambiar las definiciones ni los tests, con `PYTEST_ADDOPTS='--basetemp=bm -p no:cacheprovider'` para alojar sus temporales en la copia. El envoltorio `harness_run.py` registra las salidas de subprocess, además del resultado agregado del autor.

`harness_clean.log` y `harness_cases.jsonl`: 22 ejecuciones, alternando 11 controles con retorno 0 y 11 mutaciones con retorno 1; en cada mutación la salida identifica el test esperado como FAILED. No se contaron errores de colección como muertes. El arnés considera cualquier retorno no cero una muerte (`:118`), por lo que esta comprobación adicional es relevante. Los dos módulos se restauraron al mismo **texto**; el arnés normaliza los finales CRLF del archivo a LF al escribirlos en la copia. No restaura la identidad binaria de los archivos, pero no afecta al objeto congelado.

**Mutaciones propias:** U1 elimina la conexión desde `main` (`:1636`) y U2 limita el streaming a una única lectura (`:708`). Ambas sobreviven a los dos ficheros de tests afectados: **166 pasados, 1 omitido**, retorno 0, sin cambiar ningún test. Los controles positivos prueban que cada mutación sí rompe su propiedad: U1 hace cero llamadas al verificador; U2 devuelve False donde head devuelve True sobre un relleno válido de más de tres MiB. H-07.

También se ejecutó la **suite completa con semilla 777** para cada mutante: ambos dan **4.927 pasados, 373 fallidos, 91 omitidos, 6 xfail y 27 errores**, los mismos 400 nodeids rojos que head, con igual clasificación. Evidencia `u1_full.log`, `u2p_full.log` y `final_results.json`. Como ese montaje bloqueaba parte de las pruebas, se repitieron los 400 nodeids con temporales hermanos: ambos mutantes, head y base dan idénticos **391 pasados, 4 xfail y 5 fallidos**. No se detecta ninguna mutación en las pruebas ejercitables. Los cinco tests residuales dependientes de `.git`/venv siguen SIN VERIFICAR, no se cuentan como evidencia de supervivencia funcional ni como verdes.

### P8 — Suite y separación de plataforma

Se ejecutaron en `h/`, con el Python indicado en el mandato, `-m pytest -q --tb=short -p randomly --randomly-seed=777 --basetemp=bt777` y el equivalente con semilla 31337 y `bt31337`. Retorno **1** en ambas. `PYTHONIOENCODING=utf-8` y `PYTHONUTF8=1` preservaron la salida.

| Semilla | Pasados | Fallidos | Omitidos | Xfail | Errores de setup | Total |
|---|---:|---:|---:|---:|---:|---:|
| 777 | 4.927 | 373 | 91 | 6 | 27 | 5.424 |
| 31337 | 4.927 | 373 | 91 | 6 | 27 | 5.424 |

Conteos derivados de las líneas de progreso completas de pytest y contrastados con la colección independiente: **5.424 tests**. Se excluyeron del recuento las líneas `E` de los tracebacks. No hay errores de teardown adicionales. Los mismos **400 nodeids** dan rojo en ambas semillas.

Se reprodujeron los 400 sobre la copia de **base**: **373 fallidos y 27 errores de setup**, ninguno pasado, retorno 1. Evidencia `base_nodes.json`, `base_repro.log` y `base_repro.xml`. Por tanto, ninguno de estos 400 rojos demuestra una regresión introducida por el diff.

El origen dominante es **el montaje del arnés**, no el cruce canónico: temporales bajo `h/`/`b/` están dentro de lo que el código reconoce como proyecto; `head/core/casos/workspace_registry.py:157`–`:160` prohíbe poner ahí el registro, lanzando `WorkspaceUnderCatalogRoot`. El fallo es previo al código que muchos tests pretendían ejercer. Se conserva el conteo de los comandos pedidos; no se lo presenta como suite verde. Además hay dependencias del entorno ausentes, como `.git` y el venv esperado por tests específicos.

Para separar estos factores, se repitió la misma selección de 400 con `--basetemp=../rb` / `../rh` / `../ru1` / `../ru2p`: rutas cortas, relativas y dentro del workdir autorizado, pero hermanas del árbol copiado. No se modificó ni relajó ningún test. **Base, head, U1 y U2 dan los mismos 391 pasados, 4 xfail, 5 fallidos, cero errores**, con identidad de resultado por testcase. Evidencia: `external_{b,h,u1,u2p}.log`, sus XML y `final_results.json`. La selección es complementaria a las corridas completas; no se presenta como una nueva ejecución completa de 5.424 tests con esa disposición de temporales.

Los cinco fallos residuales se reproducen sobre base y pertenecen al entorno del objeto archivado:

- `head/tests/test_session_close_no_pude_medir.py:159` y `:122`: esperan descubrir un intérprete en el venv del repositorio, que no está en el archivo recibido. Tener disponible el Python indicado por el mandato no satisface ese supuesto del test.
- `head/tests/test_gitignore_no_inerte.py:153`, `:181` y `:202`: necesitan `git ls-files`/`git check-ignore`; retornan 128 porque las copias carecen de `.git`, como especificaba el mandato. No se creó un repositorio sintético para hacerlos pasar.

Los cuatro xfail son los ya declarados de `test_guard_copia_prestada.py::TestSobreLaCopiaLocalRegISTRADA`; los temporales interiores habían ocultado su resultado esperado con un error de registro anterior. No son xfail nuevos introducidos por esta revisión.

## Inventario de lo no cubierto

- SIN VERIFICAR: pull real de rclone, su versión/configuración instalada, montaje Drive Desktop, censo real de Google Drive y CRM real. Las conclusiones sobre nombres se basan en el flag congelado, fuente oficial y controles sintéticos.
- SIN VERIFICAR: archivos de cientos de MB o GB; el control de streaming cruza tres MiB y varios bloques, no mide rendimiento de expedientes completos.
- SIN VERIFICAR: toda intercalación concurrente posible. Se ejecutó una intercalación determinista concreta; no existe prueba de estabilidad del fichero ni snapshot remoto/local.
- SIN VERIFICAR: bytes UTF-8 inválidos entregados por Drive JSON; todas las cadenas Unicode, configuraciones alternativas de rclone, sistemas de archivos distintos del Windows utilizado y posibles colisiones criptográficas.
- La revisión no acredita genealogía git, procedencia de commits ni historial de casos reales. Los guards que dependan de git se deben interpretar teniendo en cuenta el archivo sin `.git`.
- Las pruebas omitidas/xfail y los fallos no resueltos de la suite no cuentan como cobertura aprobada; se cuantifican en P8. No se corrigió código ni se relajó ningún test.

NO-SHIP
<!-- informe-literal:fin:kx9w -->

## 2. Evidencia verificada por mí al adjudicar

Los ocho se contrastaron **contra la fuente**, no contra el informe. **Ocho confirmados,
cero refutados.** Y no son ocho defectos sueltos: tres de ellos son **reincidencias de
fronteras que yo mismo había cerrado horas antes**, en la pieza A de la fila #27.

| Hallazgo | Sev. | Qué comprobé | Veredicto |
|---|---|---|---|
| **H-01** | ALTO | `str.translate` es posicionalmente ciego y las reglas de rclone (`LeftSpace`, `RightPeriod`…) no lo son. Un remoto `a b.txt` y un local `a␠b.txt` —que rclone nunca escribiría— se cruzaban y C1/C2 daban `ok`. **Falso verde en una red de custodia** | confirmado |
| **H-02** | ALTO | Leí `_LOCAL_ENCODING` en `core/intake_drive.py`: activa `SquareBracket`, `Ctl` e `InvalidUtf8`, y rclone tiene un **escape** (`‛`). Mi tabla tenía diez caracteres y yo afirmé «cerrar la clase». Era falso: la cerré por ejemplos | confirmado |
| **H-03** | MEDIO | `<` + U+0338 compone a `≮` en el remoto, y el local `＜` + U+0338 se traducía **después** de normalizar sin recomponer. Desaparece al retirar la traducción | confirmado |
| **H-04** | MEDIO | `{clave: sha}` es un dict: **gana el último**, así que C2 contrastaba contra el hash de otro fichero y devolvía `ok` donde `base` daba `fallo`. **Regresión que introduje yo** | confirmado |
| **H-05** | MEDIO | La función leía la cola, hacía `seek(0)` y rehasheaba: **dos lecturas** de un fichero que puede cambiar. El revisor construyó la combinación de dos versiones. Y el límite: `512 x + 512 ceros` daba «confirmado» contra un comentario que prometía una cola menor de 512 | confirmado |
| **H-06** | BAJO | `DeLaRed` puede renovar el token y **reescribir la config de rclone**. No escribe en el expediente, pero mi «no escribe nada» era demasiado ancho | confirmado |
| **H-07** | MEDIO | Sus dos mutaciones sobreviven: quitar la llamada desde `main` (E1 prueba el helper, no la costura) y limitar el streaming a un bloque (ningún test tenía un fichero > 1 MiB) | confirmado |
| **H-08** | BAJO | `ident.case_id` **no es el W-code**: es `BaRS3 - Calle de Prueba 1 (W-TEST01) - Vuelta`. La orden impresa no se podía copiar. `Identidad` ya trae `w_code` | confirmado |

**Las tres reincidencias, que es lo que me llevo de esta ronda:**

1. **H-04 es «remediar el ejemplo, no la frontera»**, otra vez. Detecté las colisiones de
   clave en C1 y no las apliqué a C2, que es la misma frontera cuatro líneas más abajo.
2. **H-05 es la carrera de `MEJORAS #214`** —el fichero no es estable entre dos lecturas—
   **dentro del remedio que persigue esa misma carrera**.
3. **H-07/U1 es `A19` de la ronda anterior**: el test prueba el helper y no su cableado. Lo
   cacé hace unas horas en la pieza A y lo volví a cometer una pieza después.

**El cambio de diseño, y por qué no es «debilitar un test para poner verde».** Los tests
`n4` y `n5` contrataban que un nombre con el encoding de rclone **se cruzara**. Se retiran, y
su propiedad se sustituye por `r1_h01`/`r1_h02`/`r1_h02b`: ahora el descuadre **se declara y
se explica** en vez de cruzarse. No se relajó un aserto: se descubrió que el contrato
anterior era inseguro y se cambió el contrato, con su razón escrita. La diferencia está en
que el nuevo es **más** exigente, no menos — antes se aceptaban pares que rclone nunca
habría producido.

**Una guarda retirada por inerte, sin atribuirle garantía.** Al cerrar H-05 añadí un
`p.stat().st_size != tam` final; el arnés mostró que **no puede morder** (cualquier cambio de
tamaño lo cazan antes las dos lecturas, y uno que conserve el tamaño tampoco lo ve). Se
retiró. Y su hermana `len(cola) != tam - seguro` queda como **superviviente declarado** del
arnés: no supe construir su caso discriminante, así que se conserva porque hace el fallo
temprano y explícito, **no** porque esté demostrado que atrapa algo.

**Lo que sigue SIN VERIFICAR:** deshacer de verdad el encoding de rclone —haría falta
reimplementar su decodificador posicional con escape, y el mandato de esta pieza no era ese—,
por lo que un descuadre por `SquareBracket`, `Ctl` o `／` **sigue saliendo como descuadre**,
ahora explicado. Y los 400 rojos que el revisor midió en su entorno son de plataforma: los
reprodujo sobre `base` con los mismos nodeids, y aquí la suite da **0 fallos** con las dos
semillas.
