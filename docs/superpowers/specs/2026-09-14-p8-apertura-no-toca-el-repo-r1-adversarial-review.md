---
tipo: revision-adversarial
objeto: scripts/session_close.py
objeto_rev: "1"
commit: 7a78385
ronda: "1"
revisor: Codex
veredicto: LISTA-CON-CAMBIOS
marcador_nonce: p8r1
sha256_informe: ce3c4bb551a14d7f32f49ad74b8b628924f49fc02779721c48deb96b25260ccb
adjudicado_en: docs/superpowers/specs/2026-09-14-p8-apertura-no-toca-el-repo-design.md §13
---

# Acta — R1 adversarial sobre el diff de P8 (la apertura no toca el repo)

Objeto: el **diff** `aba9656..7a78385`. Se archivaron las dos copias con `git archive` en
`C:/Users/tnm33/Dev/_revisiones/2026-09-14-p8-r1/{base,head}`; el revisor trabajó sobre ellas,
sin `.git` y sin tocar el repositorio real.

| | |
|---|---|
| Revisor | Codex CLI `0.153.4`, binario `7ac07f4ce733f89a`, modelo `gpt-6-astra`, `model_reasoning_effort=high` |
| Objeto | `…/2026-09-14-p8-r1/{base,head}` — 1343 y 1347 ficheros |
| `sha256` de los dos ficheros pedidos, al abrir y al cerrar | **idénticos**; el revisor los recalculó tras sus mutaciones y contrastó además las copias ejecutables |
| `sha256` del informe | `ce3c4bb551a14d7f32f49ad74b8b628924f49fc02779721c48deb96b25260ccb` — **recomputado por mí sobre el fichero crudo, y coincide con el que el revisor devolvió en su último mensaje** |
| Veredicto | **LISTA-CON-CAMBIOS** |
| Hallazgos | 6 (0 `ALTO`, 4 `MEDIO`, 2 `BAJO`) — **6 confirmados, 0 refutados** |
| Ejecución del revisor | **118 tests corridos** con el Python del sistema, más mutantes dirigidos (M1-M4) y sondas de reproducción |

**Los seis hallazgos son DOS fronteras, y esa es la lectura que importa.**

**Frontera 1 (H-01, H-02, H-03): el lector convertía «no pude interpretar esto» en «no hay nada
que declarar».** Tres vías —sintaxis que no entiende y aplana, enumeración que falla y devuelve
cero, bytes que no decodifica y sustituye—. Es **la misma lección que la pieza A de la fila #27
ya había comprado** (`rglob` suprime los errores de recorrido; por eso allí se usó
`os.walk(onerror=…)`) y que **este mismo spec cita en su §6** mientras el lector hacía lo
contrario en tres sitios. Un hecho escrito que su propio autor no aplicó.

**Frontera 2 (H-04, H-05): la prueba prometía más de lo que ejercitaba.** El comentario del guard
prometía comprobar los estados «en los dos sentidos» y el aserto solo hacía uno; el test titulado
«no rompe el cierre» no tocaba `main()` ni miraba la salida. El revisor lo demostró con mutantes:
M1 (desconectar la llamada) y M2 (silenciar el diagnóstico) dejaban **72 tests verdes**.

**H-06 se confirma con matiz.** No había contradicción lógica —el ordinal es del **cierre de
sesión**, no del expediente, y ése sigue numerándose—, pero sí una ambigüedad que introducía este
diff: quien abriera tres expedientes leería `[APER-30]` tres veces y numeraría tres cierres.

**Lo que el revisor intentó refutar y no pudo, y conviene registrar:** el mutante M4 —hacer que el
lector devuelva siempre vacío— produjo **13 fallos**, así que el control positivo no era
decorativo. Y declaró SIN VERIFICAR, correctamente, la suite completa, las dos semillas de
aceptación, las ACL nativas de Windows y una apertura real.

<!-- mandato-literal:inicio:p8r1 -->

# Revisión adversarial — P8: una sesión de apertura no toca el repo (R1, sobre el DIFF)

Eres el revisor adversarial de un cambio de un repositorio legal-tech en Python (Windows).
Trabajas **en solo lectura sobre copias congeladas**: no hay `.git`, y no debes modificar nada
bajo `../head` ni `../base`. Tu directorio de trabajo es el actual (`workdir`), y es el único
sitio donde puedes escribir, además de `/tmp`.

## El objeto

- `../base/` — el árbol ANTES del cambio (commit `aba9656`).
- `../head/` — el árbol DESPUÉS del cambio (commit `7a78385`).

**El objeto de la revisión es la diferencia entre los dos**, en estos ocho ficheros:

```
CLAUDE.md                                                    |  21 +
PLAN.md                                                      |   4 +-
docs/RUNBOOK_APERTURA_EXPEDIENTE.md                          |  39 +
docs/superpowers/plans/2026-09-14-p8-apertura-no-toca-el-repo.md    | 736 +
docs/superpowers/specs/2026-09-14-p8-apertura-no-toca-el-repo-design.md | 230 +
scripts/session_close.py                                     | 121 +
tests/test_guard_formato_apertura.py                         |  47 +
tests/test_session_close_aperturas.py                        | 165 +
```

Puedes obtener el diff con `diff -ru ../base ../head` (o por fichero). El spec del cambio está
en `../head/docs/superpowers/specs/2026-09-14-p8-apertura-no-toca-el-repo-design.md`: léelo, es
donde están las decisiones y sus porqués, y **es también objeto de crítica**, no solo contexto.

## Qué hace el cambio, en dos frases

Una sesión que abre un expediente no debe tocar el repositorio: anota los defectos que encuentre
en un fichero de trabajo fuera del repo (`%LOCALAPPDATA%\FeesDefender\aperturas\<fecha>_<W-code>.md`)
y los ficha al cerrar. Como nada obligaba a ese «al cerrar», `scripts/session_close.py` ahora
**avisa** de los ficheros que siguen en `estado: pendiente` — aviso, nunca verja.

## Puedes ejecutar, y conviene que lo hagas

El Python del sistema —`C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`—
tiene `pytest`, `yaml`, `dotenv`, `typer`, `httpx` y `filelock`. Desde una copia de `../head` en
tu propio workdir puedes correr la suite o tests sueltos. Dos avisos prácticos:

- Usa un `--basetemp` corto (p. ej. `C:/t/p8`): MAX_PATH tumba tests que están bien.
- **No mutes `../head`**: copia a tu workdir lo que necesites ejecutar.

Si no puedes ejecutar algo, dilo como **SIN VERIFICAR**. No es un demérito: es información.

## Qué quiero de ti

Lee el diff con criterio propio y dime qué encuentras. Interesan especialmente:

1. **El lector** (`_leer_aperturas`, `_frontmatter_apertura`, `raiz_aperturas_por_defecto` en
   `scripts/session_close.py`): ¿hay entradas que clasifique mal? ¿Algún fichero que deba salir
   por `ilegibles` y se cuele como pendiente, o al revés? ¿Rutas, encoding, symlinks, permisos,
   ficheros enormes, nombres raros en Windows?
2. **La dirección de los fallos.** El diseño dice que ante la duda el aviso debe hablar (un
   fichero no interpretable nunca debe pasar por «fichado»). ¿Se cumple en todos los caminos?
3. **El guard** `tests/test_guard_formato_apertura.py`: extrae un bloque del RUNBOOK y se lo pasa
   al lector. ¿Es un guard que de verdad muerde, o puede quedar verde con el contrato roto? ¿Su
   extracción del bloque es frágil ante ediciones razonables del documento?
4. **Los tests**: ¿prueban lo que dicen probar? ¿Hay asertos que pasarían con una implementación
   trivial o rota? ¿Falta algún caso cuyo fallo nadie vería?
5. **El aviso** (`_avisar_aperturas_sin_fichar`) y su cableado en `main()`: ¿puede romper el
   cierre por alguna vía? ¿Puede callar cuando debería hablar?
6. **Coherencia entre la prosa y el código**: el spec, el RUNBOOK y `CLAUDE.md` describen un
   contrato. ¿El código hace lo que dicen? ¿Se contradicen entre sí?

También quiero tu juicio sobre el **diseño**, no solo sobre la implementación: si una decisión
del spec te parece equivocada, dilo, aunque esté implementada sin defectos.

## Formato de cada hallazgo

Escribe un fichero `INFORME.md` en tu directorio de trabajo. Para cada hallazgo:

- **Id** (`H-01`, …) y **título** de una línea.
- **Dónde**: fichero y línea del árbol `../head`.
- **Qué pasa**: el defecto, con el camino concreto que lo produce.
- **Cómo lo verificaste**: comando ejecutado y su salida, o `SIN VERIFICAR` y por qué.
- **Severidad**: `ALTO` · `MEDIO` · `BAJO`.
- **Coste del remedio**: `trivial` (una línea) · `acotado` (una función o un test) ·
  `estructural` (cambia el diseño o toca varias piezas).

Los dos ejes son independientes y los necesito **los dos**: sin el segundo, un defecto menor con
remedio estructural llega indistinguible de uno grave que se arregla en una línea, y quien
adjudica se queda sin el dato que decide.

Cierra con un **veredicto** global: `SHIP`, `LISTA-CON-CAMBIOS` o `NO-SHIP`, y una línea de por qué.

## Dos cosas sobre el encargo

- **Volver sin hallazgos es un resultado válido.** Si el cambio te parece correcto, dilo y ya
  está; no busques defectos para justificar la ronda. Prefiero un informe corto y cierto que uno
  largo y especulativo.
- **No apliques cambios.** Tu salida es el informe. Quien adjudica contrasta cada hallazgo contra
  el código y decide; tú no tienes la última palabra sobre corrección, y eso no te resta: un
  hallazgo bien argumentado vale aunque se refute.

## Evidencia de no-mutación

Al empezar y al terminar, calcula y reporta el `sha256` de estos dos ficheros de `../head`:

```
../head/scripts/session_close.py
../head/tests/test_guard_formato_apertura.py
```

Ponlos al principio y al final del `INFORME.md`.


<!-- mandato-literal:fin:p8r1 -->

<!-- informe-literal:inicio:p8r1 -->

# Revisión adversarial P8 — R1 sobre el diff

Objeto: `aba9656` → `7a78385`, árboles congelados `../base` y `../head`. Revisión ejecutada el 2026-09-14. Todas las ubicaciones de los hallazgos corresponden a `../head`.

## Evidencia inicial de no mutación

SHA-256 calculados antes de explorar el objeto:

| Fichero de `../head` | SHA-256 inicial |
|---|---|
| `scripts/session_close.py` | `7712a9ac36c4d9f94b82ff8b83383ff7b998cbbb295033c5a93b43c344bea386` |
| `tests/test_guard_formato_apertura.py` | `c9e29bdf91f3c283fbc3da1f2cae0cbeea66c36fb3fcec2254c9c169414eed82` |

## Alcance y ejecución

Contrasté los ocho ficheros cambiados, el spec completo, el plan y el código circundante. La comparación de contenido entre árboles confirmó que esos son los ocho ficheros distintos. No apliqué correcciones. Las ejecuciones y mutaciones se hicieron en `workdir/h`, copia de `head`, con datos sintéticos y escrituras dentro de `workdir`. Las mutaciones se restauraron al terminar cada prueba.

Intérprete: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`, Python 3.14.4. En los comandos siguientes, `$py` designa ese ejecutable. Se fijó `PYTHONDONTWRITEBYTECODE=1`; pytest usó `-p no:cacheprovider`, temporales fuera de `h` y una raíz de aperturas sintética.

Comprobación final desde `workdir/h`:

```powershell
& $py -m pytest tests/test_session_close_aperturas.py tests/test_guard_formato_apertura.py tests/test_session_close_aviso.py tests/test_session_close_verja.py tests/test_docs_gobernanza.py -p no:cacheprovider --basetemp=../tf --tb=short -o addopts= -q
```

Salida: **`118 passed in 10.93s`**. Registro: `pytest-final.txt`. No equivale a haber ejecutado la suite completa ni sus dos semillas de aceptación.

## H-01 — El parser permite que un estado secundario o ambiguo silencie el pendiente

- **Dónde:** `scripts/session_close.py:469-476`; contrato en `docs/superpowers/specs/2026-09-14-p8-apertura-no-toca-el-repo-design.md:132-151`.
- **Qué pasa:** el parser elimina la sangría de las claves, sobrescribe duplicados e ignora las líneas sin `:`. Este fichero declara un pendiente en el nivel principal, pero el lector devuelve `([], [])` y el aviso no imprime nada:

  ```yaml
  ---
  caso: W-TEST
  fecha: 2026-09-14
  estado: pendiente
  detalle:
    estado: fichado
  ---
  ```

  El mismo silencio ocurre con dos claves raíz `estado`, primero `pendiente` y después `fichado`. Un frontmatter con `estado: fichado` y una línea suelta `error sin dos puntos` también se acepta, aunque el YAML está roto. Si el formato admitido es exclusivamente plano, estos documentos deben ser ilegibles; aplanarlos o escoger el último estado incumple igualmente ese contrato. El test de «frontmatter roto» solo prueba que falta el delimitador de cierre, no errores dentro de un bloque cerrado.
- **Cómo lo verifiqué:** desde `workdir`, `& $py reproduce.py`, registro `reproduce.txt`:

  ```text
  nested => ([], []) stdout= ''
  duplicate => ([], []) stdout= ''
  broken_yaml => ([], []) stdout= ''
  yaml nested => {'caso': 'W-TEST', 'fecha': datetime.date(2026, 9, 14), 'estado': 'pendiente', 'detalle': {'estado': 'fichado'}}
  yaml broken_yaml => ScannerError
  ```

  PyYAML se utilizó como contraste en la sonda, sin cambiar el lector.
- **Severidad:** MEDIO.
- **Coste del remedio:** acotado. Validar en `_frontmatter_apertura` la gramática plana admitida y rechazar duplicados, anidamientos y líneas no interpretables, con pruebas que exijan `ilegibles` y aviso. No hace falta introducir un escritor ni soportar todo YAML para cerrar este fallo.

## H-02 — Un recorrido fallido se confunde con una carpeta vacía

- **Dónde:** `scripts/session_close.py:490-492`.
- **Qué pasa:** `Path.glob` suprime el error de enumeración en el intérprete utilizado. Si `os.scandir` falla por permisos, el bucle recibe cero entradas y `_avisar_aperturas_sin_fichar` guarda silencio. El `try/except` exterior no lo rescata porque no recibe ninguna excepción. Además, una raíz existente que sea un fichero regular se trata exactamente igual que una carpeta ausente. El contrato solo justifica silencio para ausencia o falta de asuntos, no para incapacidad de comprobarlos.
- **Cómo lo verifiqué:** `& $py reproduce.py`, registro `reproduce.txt`. En una carpeta real que contiene el pendiente de control, inyecté `PermissionError` en `os.scandir`, manteniendo el `glob` de producción. También pasé un fichero regular real como raíz:

  ```text
  scandir_denied => ([], []) stdout= ''
  root_file => ([], []) stdout= ''
  ```

  El caso de permisos es una inyección del fallo de la API, no una prueba de ACL reales de Windows; estas últimas quedan SIN VERIFICAR.
- **Severidad:** MEDIO.
- **Coste del remedio:** acotado. Usar una enumeración que propague sus errores y distinguir explícitamente ausencia de raíz de raíz inválida o inaccesible. El aviso existente puede declarar el fallo global; no debe inventar nombres de ficheros que no consiguió enumerar.

## H-03 — La sustitución de bytes inválidos permite dar por interpretable una nota corrupta

- **Dónde:** `scripts/session_close.py:495-497`, validación posterior en `508-511`.
- **Qué pasa:** `errors="replace"` oculta los errores UTF-8. Un byte inválido dentro de `caso` se convierte en U+FFFD y el campo sigue siendo no vacío. Con `estado: fichado`, la nota corrupta desaparece de ambas listas; con `pendiente`, se presentaría como un pendiente legible. No hay diagnóstico de la pérdida de información. Esto es independiente de la gramática del frontmatter: el lector pierde la señal antes de parsearlo.
- **Cómo lo verifiqué:** `& $py reproduce.py`, registro `reproduce.txt`. La sonda escribe bytes reales con `caso: W-\xff`, fecha válida y `estado: fichado`:

  ```text
  invalid_utf8 => ([], []) stdout= ''
  ```

- **Severidad:** MEDIO.
- **Coste del remedio:** acotado. Decodificar estrictamente y registrar el `UnicodeDecodeError` como ilegible por fichero, conservando la continuación del recorrido. Cambiar solo `errors` sin ampliar el manejo de excepciones perdería esa continuidad.

## H-04 — El guard comprueba los estados en una sola dirección

- **Dónde:** `tests/test_guard_formato_apertura.py:41-47`; promesa del guard en el spec, `166-168`.
- **Qué pasa:** itera sobre los estados del código y busca sus palabras en todo el RUNBOOK. No comprueba que todos los estados prometidos por el RUNBOOK sean aceptados. Añadir `archivado` a la lista normativa de estados deja el guard verde, pese a que el lector lo devuelve como desconocido. El comentario de las líneas 42-44 promete cubrir precisamente ambos sentidos. Buscar en el documento entero también permite que una mención ajena al contrato satisfaga el aserto.
- **Cómo lo verifiqué:** `& $py mutations.py`, mutante M3, registro `M3_estado_documentado_no_aceptado.txt`. La única mutación añade el estado `archivado` a la enumeración de estados en `RUNBOOK:124`; no cambia el lector:

  ```text
  M3_estado_documentado_no_aceptado exit= 0 72 passed in 5.16s
  ```

  Los 72 incluyen ambos tests del guard y las pruebas del lector que rechazan `archivado`.
- **Severidad:** BAJO.
- **Coste del remedio:** acotado. Extraer el conjunto de estados de su sección normativa y compararlo por igualdad con el código, con un control negativo de un estado añadido solo al documento.

## H-05 — La suite no protege el cableado del aviso ni su diagnóstico de excepciones

- **Dónde:** `tests/test_session_close_aperturas.py:155-166`; llamada de producción en `scripts/session_close.py:880-884`; requisito de prueba en el spec, `190`.
- **Qué pasa:** el test titulado «no rompe el cierre» llama directamente al aviso, no a `main()`, y no usa `capsys` para exigir que se anuncie el fallo. Por ello pasan dos roturas distintas: eliminar la llamada desde `main()` y conservar el aviso inaccesible, o tragar en silencio la excepción del lector. Las pruebas positivas de la función aislada no cubren esas propiedades. El código actual sí contiene ambos caminos correctamente; el hallazgo es contra su protección de regresiones.
- **Cómo lo verifiqué:** `& $py mutations.py`. Registros `M1_main_desconectado.txt` y `M2_error_silenciado.txt`:

  ```text
  M1_main_desconectado exit= 0 72 passed in 5.11s
  M2_error_silenciado exit= 0 72 passed in 5.29s
  ```

  M1 sustituye exclusivamente la llamada de la línea 882 por `pass`; M2 sustituye exclusivamente el diagnóstico de la línea 533 por `pass`. Cada mutación se ejecuta por separado y se restaura.
- **Severidad:** MEDIO.
- **Coste del remedio:** acotado. Añadir una prueba de `main()` con dependencias, suite y avisos ajenos doblados, raíz sintética y asertos de llamada/salida. Exigir además diagnóstico cuando el lector lanza, no solo ausencia de excepción.

## H-06 — La nueva regla de cierre contradice una instrucción operativa que sigue vigente

- **Dónde:** `CLAUDE.md:382-385`, frente a `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:1210-1212` (`[APER-30]`).
- **Qué pasa:** el diff ordena un único bloque «aperturas del día» y dice que el cierre se cita por fecha, sin ordinal. Pero el §11 del runbook al que remite la apertura sigue ordenando buscar el último `(Nº cierre` en `STATUS.md` antes de numerar. El paso específico de cierre conserva la conducta que la nueva regla pretende retirar. La orden antigua ya existía; el problema introducido por este diff es mantenerla activa al establecer la nueva regla incompatible.
- **Cómo lo verifiqué:** lectura de ambos fragmentos con líneas numeradas y `Get-Content ../head/docs/RUNBOOK_APERTURA_EXPEDIENTE.md | Select-Object -Skip 1209 -First 3`. Salida relevante: `Numeración del "cierre" en STATUS.md`, `grep del último (Nº cierre`, `ANTES de numerar`. El texto nuevo de `CLAUDE:382-385` dice «no en un cierre numerado por caso» y «por fecha y no por ordinal». Los 118 tests finales, incluidos los de gobernanza, pasan con ambos textos presentes.
- **Severidad:** BAJO.
- **Coste del remedio:** acotado. Actualizar el paso de cierre del RUNBOOK para que remita al bloque diario vigente y retire la numeración anterior.

## Cobertura de los seis puntos del encargo

| Punto | Resultado |
|---|---|
| 1. Lector, rutas y entradas | H-01 a H-03. Probados también `.MD`, nombres Unicode, enlace simbólico roto y cuerpo grande. |
| 2. Dirección de fallos | No se cumple en los tres caminos de silencio reproducidos. Los estados desconocidos simples sí generan aviso. |
| 3. Guard | H-04. El ejemplo literal actual se extrae y pasa por el lector. La extracción depende de vallas de backticks; detalle abajo. |
| 4. Tests | H-05 y los mutantes. Los controles positivos existentes sí detectan un lector completamente inerte. |
| 5. Aviso y `main()` | Cableado actual probado mediante dobles; excepciones contenidas. El aviso no se alcanza si falla la suite, igual que los otros avisos posteriores. |
| 6. Prosa y diseño | H-06 y la incompatibilidad entre «YAML roto → ilegible» y el parser tolerante de H-01. Juicio de diseño abajo. |

## Lo que intenté refutar y NO pude

- **El control positivo no es decorativo.** M4 hace que el lector devuelva siempre vacío: `13 failed, 59 passed in 4.66s`. Registro `M4_lector_siempre_vacio.txt`. No afirmo que todos los tests sean débiles.
- **El aviso actual no rompe `main()` por una excepción ordinaria del lector o del propio aviso.** `reproduce.py` ejecutó `main()` con dobles para evitar suite, subprocessos y acceso al perfil. Con un pendiente alcanzó su impresión; al inyectar `RuntimeError` en el lector devolvió `None` y anunció `no se pudieron leer las aperturas: boom`; al inyectarla en el aviso anunció `no se pudo comprobar las aperturas sin fichar: boom aviso`. No es una ejecución completa del CLI de cierre.
- **Nombres y enlaces en Windows:** `.MD` y `á_🧪.md` se clasificaron como pendientes. Un enlace simbólico roto real salió por `ilegibles` sin perder los dos pendientes anteriores. Registro `edge_probes.txt`.
- **Ausencia, extensiones y errores individuales:** los tests existentes verifican raíz ausente, ausencia de recursión, ignorar `.txt`, campos obligatorios ausentes y continuación tras un directorio llamado `.md`; pasaron.
- **Encoding y formato conservador:** un BOM UTF-8, un estado entre comillas o con comentario producen `ilegibles`, no silencio. Son falsos rechazos potenciales de variantes de edición; el BOM está fuera de la convención UTF-8 sin BOM del plan. No los equiparo a los falsos silencios de H-01/H-03.

## Juicio sobre el diseño y límites de la medición

La separación entre apertura y reparación, la raíz persistente fuera del worktree, `descartado`, la ausencia de caducidad automática y el carácter informativo del aviso son proporcionales al problema descrito. La limitación a una persona y un PC está expresamente aceptada; no propongo rediseñarla. Tampoco trataría `fichas: []` como un bug del lector: el spec excluye deliberadamente su auditoría automática. Eso deja la verdad del estado bajo responsabilidad de quien lo escribe.

La decisión que sí debe corregirse es aceptar como válido lo que el parser no entiende. Prescindir de YAML puede ser razonable si se define y valida un formato plano; no justifica ignorar sintaxis y resolver ambigüedades escogiendo el último valor. El guard de un ejemplo tampoco sustituye esa validación. La motivación de evitar una caída por falta de `yaml` es débil en este punto: `main()` ya exige esa dependencia en su preflight. La conversión de una fecha tampoco obliga a un parser tolerante. No se necesita imponer YAML como remedio, pero sí un contrato de lectura cerrado.

Hay límites adicionales medidos que no considero bloqueantes para estas notas pequeñas:

- Un cuerpo de 16 MiB, aunque el frontmatter ocupa unas líneas, consumió aproximadamente **48,1 MiB** de pico trazado y **0,055 s**. Se lee y divide todo el fichero. SIN VERIFICAR agotamiento real de memoria, ficheros de varios GiB o lecturas bloqueadas; no afirmo que el `try/except` limite tiempo o memoria.
- Cambiar solo las vallas del ejemplo de backticks a `~~~` hace que el guard extraiga el siguiente bloque de comandos del RUNBOOK y falle por `sin frontmatter`. Es fragilidad editorial con fallo visible, no aceptación silenciosa de un contrato roto. `edge_probes.py` conserva la sonda.
- La raíz configurable admite valores relativos y el RUNBOOK escribe la ruta fija de `%LOCALAPPDATA%`. La operativa probada es la ruta por defecto; compartir un override entre escritor manual y cierres de varios worktrees requiere una convención adicional. No he probado sesiones reales con overrides divergentes.
- «No toca el repo» necesita leerse como prohibición de reparaciones durante la apertura, con el fichado documental al cierre que el propio encargo acepta; el proceso todavía escribe backlog y bitácora. No lo he tratado como mandato de impedir toda escritura física mediante código.
- SIN VERIFICAR: suite completa, semillas de aceptación 777/31337, ACL nativas de denegación y una apertura/cierre real del despacho. La ejecución se delimitó a los 118 tests relacionados y sondas sintéticas; no se accedió a expedientes ni servicios externos. No se certifica cobertura porcentual del diff ni aceptación global del repositorio.

## Veredicto

**LISTA-CON-CAMBIOS** — El alcance y el aviso son adecuados, pero antes de integrar deben cerrarse los falsos silencios del lector y la cobertura que actualmente permite desconectar el disparador sin un test rojo.

## Evidencia final de no mutación

Recalculados tras las pruebas y las mutaciones de la copia. Coinciden exactamente con los iniciales:

| Fichero de `../head` | SHA-256 final |
|---|---|
| `scripts/session_close.py` | `7712a9ac36c4d9f94b82ff8b83383ff7b998cbbb295033c5a93b43c344bea386` |
| `tests/test_guard_formato_apertura.py` | `c9e29bdf91f3c283fbc3da1f2cae0cbeea66c36fb3fcec2254c9c169414eed82` |

Registros de custodia: `hashes-inicio.json` y `hashes-final.json`. Las dos copias ejecutables correspondientes en `workdir/h` también se contrastaron con `head` tras restaurar las mutaciones: idénticas.


<!-- informe-literal:fin:p8r1 -->
