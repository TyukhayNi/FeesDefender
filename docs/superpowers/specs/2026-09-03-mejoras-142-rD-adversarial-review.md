---
tipo: revision-adversarial
objeto: "diff de MEJORAS #142: nadie termina el proceso bajo el mutex"
objeto_rev: "rama claude/mejoras-142-exit-bajo-mutex, commit 6f249cb"
commit: 6f249cb
ronda: "D"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: p3xq
sha256_informe: 512dbb264603ad3916236509ec827e4b9ed1c34f3c769798055201f9169dc2c8
adjudicado_en: docs/superpowers/plans/2026-09-03-mejoras-142-exit-bajo-mutex.md §3
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revision adversarial R-D.** El §1 conserva la voz del revisor sin una coma
> cambiada; la **adjudicacion** vive en el **§3 del plan**.
>
> **Una ronda y no dos**, por radio de dano: la pieza no decide quien puede escribir ni
> cambia ninguna escritura; cambia cuando termina el proceso, y mueve validacion a antes
> del lock — menos tiempo bajo exclusion, no mas.
>
> Veredicto `NO-SHIP`: **5 hallazgos** — 1 ALTO, 2 MEDIOS, 2 BAJOS. Adjudicados: **5
> confirmados, 0 refutados**.
>
> **La correccion funcional central la reprodujo y funciona.** Lo que tumbo fue **el
> guard**: solo reconocia `typer.Exit`, asi que un `sys.exit` o un `raise typer.Abort()`
> bajo el mutex lo dejaban VERDE —medido con dos mutaciones en memoria—, y su lista de
> funciones vigiladas estaba **escrita a mano**: 13 nombres frente a las **17** que el
> bloque alcanza de verdad, con tres nombres muertos tolerados como `skip`.
>
> **Prueba de no mutacion:** el objeto (`DIFF.patch`) conservo el `sha256`
> `c28e6dda07d8a56551075bc8d490ef3b53d7bdc4785c5eb725d6edd792ddb708` al abrir y al cerrar.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:p3xq -->

NO-SHIP

Hay 1 hallazgo ALTO, 2 MEDIOS y 2 BAJOS. La corrección funcional central sí está reproducida: mantiene los cuatro errores, protege `dry-run` y hace visible la nota de pérdida. Pesa más que el guard prometido acepte `sys.exit`, `os._exit`/Abort y funciones transitivas omitidas, incluso con tres nombres muertos, porque deja verde exactamente la regresión que pretende impedir. Antes de mergear debe cerrarse la detección, hacer exacta la superficie transitiva y añadir pruebas dinámicas del aviso y de la pérdida en `dry-run`; la precedencia de errores debe adjudicarse expresamente.

---

## 1. Objeto y evidencia

Revisión adversarial, solo lectura, de `../head/` (commit declarado `6f249cb`) contra
`../base/` (`origin/main`). Trabajé sobre copias en el directorio temporal del sistema;
los hashes de `scripts/abrir_caso.py` y del guard en la copia coinciden al terminar con
los originales de `../head/`.

- SHA-256 de `./DIFF.patch` al abrir:
  `c28e6dda07d8a56551075bc8d490ef3b53d7bdc4785c5eb725d6edd792ddb708`.
- SHA-256 de `./DIFF.patch` al cerrar:
  `c28e6dda07d8a56551075bc8d490ef3b53d7bdc4785c5eb725d6edd792ddb708`.
- Un censo SHA-256 de ambos árboles confirmó exactamente dos diferencias:
  `scripts/abrir_caso.py` cambiado y
  `tests/test_abrir_caso_exit_bajo_mutex.py` añadido.
- Leí completos el patch, las dos versiones de `scripts/abrir_caso.py`, el guard nuevo y
  `core/casos/case_mutex.py`. También inspeccioné los productores alcanzables bajo el
  mutex y busqué `typer.Exit`, `click Exit/Abort`, `SystemExit`, `sys.exit` y `os._exit`
  en las dependencias transitivas relevantes.

Ejecuciones con
`C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`
(Python 3.14.4, pytest 9.1.1):

- Batería dirigida de 19 módulos de apertura/mutex: `head`, 325/325 pruebas pasaron;
  la batería equivalente de `base`, 309/309. Los 16 casos adicionales son los del guard
  nuevo.
- Cuatro pruebas de autoderivación (`codigo/team/sufijo`, precedencia de flags explícitos,
  sufijo sin API y `case-id` con `team-id` derivado): 4/4 en `base` y 4/4 en `head`.
- Matriz CLI aislada de los cuatro abortos de ejecución: manual normal sin origen,
  manual `--dry-run` sin origen, WhatsApp sin fichero y reconciliación fallida. En los
  cuatro, `base` y `head` dieron el mismo texto y código 1; la excepción observada en el
  entrypoint fue `SystemExit` en ambos.
- Sonda de pérdida del mutex: con `AbortarApertura` en vuelo, `head` imprimió
  `[AVISO] [mutex] ...`; con `--dry-run` y pérdida a la salida, `base` terminó 0 y `head`
  terminó 1 con `MUTEX_PERDIDO`. En ambos hubo 0 llamadas CRM y 0 eventos de intake.
- Suite completa de `head`: 3.901 casos recogidos; 3.811 pasaron, 77 se omitieron,
  10 quedaron `xfail` y 3 fallaron. Los tres fallos son ajenos al diff y se reprodujeron
  exactamente en `base`: un wrapper que depende de `ping` con `PATH` envenenado y dos
  pruebas que exigen un `.venv` ausente en la copia. Una primera corrida con el cwd en el
  padre produjo además falsos fallos de guards que abren rutas relativas; se descartó y
  se repitió desde la raíz de la copia con `--basetemp=..\th2`.
- Ruff sobre los dos ficheros de `head`: 7 diagnósticos. Seis corresponden a deuda ya
  presente en el CLI o a diagnósticos que también existen en `base`; el `F401` del guard
  nuevo sí es introducido por este diff (HD-05).
- Arneses adversariales en memoria, sin escribir en el objeto: el guard quedó verde con
  un `SystemExit` en una función alcanzable no listada, con `sys.exit` y `typer.Abort` en
  una función sí listada, y con tres entradas obsoletas en su lista manual. Las salidas
  exactas se detallan en HD-01 y HD-02.

Queda **SIN VERIFICAR** el orden aleatorio: no está instalado `pytest-randomly`. También
quedaron sin ejecutar 70 pruebas marcadas lentas, cinco pruebas de Ollama y dos guards
dependientes de fixtures locales ausentes (PII/blocklist). No se ejercieron Drive, Gmail
ni CRM reales; las comparaciones de CLI se aislaron con dobles para no producir efectos
externos.

## 2. Hallazgos

### HD-01 — ALTO — El detector no reconoce varias terminaciones del proceso que dice vigilar

**Qué es y dónde.** `_exits` solo selecciona nodos `ast.Raise` cuyo `ast.dump()` contiene
la subcadena `"Exit"` (`tests/test_abrir_caso_exit_bajo_mutex.py:48-50`). Por construcción
no ve `sys.exit(...)`, `os._exit(...)`, `typer.Abort()` ni `click.Abort()`; tampoco resuelve
aliases. Esto contradice la propiedad anunciada en el propio guard
(`tests/test_abrir_caso_exit_bajo_mutex.py:17-19`). `_alta_crm` se ejecuta bajo el mutex
(`scripts/abrir_caso.py:1040-1041`) y figura expresamente entre las funciones vigiladas.

**Por qué importa y qué lo dispara.** Basta introducir `sys.exit(77)` o
`raise typer.Abort()` en `_alta_crm` para volver a terminar el proceso bajo exclusión sin
poner rojo el guard. `sys.exit` reproduce la nota invisible sobre `SystemExit`; un Abort
es formateado por Click/Typer sin traceback; `os._exit` es peor, porque ni siquiera ejecuta
el `finally` que libera y diagnostica.

**Cómo se comprobó.** Alimenté al guard, en memoria, dos versiones mutadas del mismo
fuente: una con `__import__("sys").exit(77)` y otra con `raise typer.Abort()` dentro de
`_alta_crm`. En ambos casos el arnés informó:
`FALSE_GREEN passed=16 skipped=0 failed=0`.

**Qué haría falta.** Detectar explícitamente tanto `ast.Call` como `ast.Raise`, con los
símbolos de terminación prohibidos (`sys.exit`, `os._exit`, `SystemExit`, Exit y Abort de
Typer/Click), y resolver imports/aliases al menos dentro del módulo. Añadir mutantes de
cada forma prohibida como prueba negativa del propio guard.

### HD-02 — MEDIO — La frontera transitiva está incompleta y tolera tres nombres muertos

**Qué es y dónde.** `INVOCADAS_BAJO_MUTEX` tiene 13 nombres escritos a mano
(`tests/test_abrir_caso_exit_bajo_mutex.py:31-36`), pero el grafo real local alcanza 17.
Faltan `hash_tree_local`, `_inventario_local`, `_inventario_desde_hashes` y
`traducir_pull_crm`, alcanzadas respectivamente desde `_intake_drive_ev`,
`_intake_manual`, `_intake_generico` y `etapa_crm`. La lista sí incluye otras funciones
de profundidad tres, por lo que no es una decisión de limitarse a un salto. Además, una
función inexistente se convierte en `pytest.skip` (`tests/test_abrir_caso_exit_bajo_mutex.py:70-73`)
y el supuesto anti-vacío solo exige 10 vivas de 13
(`tests/test_abrir_caso_exit_bajo_mutex.py:80-88`).

**Por qué importa y qué lo dispara.** Un `raise SystemExit(...)` añadido en cualquiera de
las cuatro funciones omitidas queda fuera de toda inspección. Por separado, hasta tres
renombres/eliminaciones de funciones listadas convierten sus casos en skips mientras el
umbral sigue verde: el guard puede perder un 23 % de su superficie sin fallar.

**Cómo se comprobó.** El cierre transitivo AST desde el cuerpo real del `with` devolvió
las cuatro funciones omitidas. Una mutación en memoria con `raise SystemExit(77)` dentro
de `_inventario_local` produjo `FALSE_GREEN passed=16 skipped=0 failed=0`. Sustituir las
tres primeras entradas por nombres inexistentes produjo
`FALSE_GREEN passed=13 skipped=3 failed=0`.

**Qué haría falta.** Derivar el cierre de llamadas locales desde el `with` en vez de
mantener una lista divergente; para llamadas externas, declarar y comprobar una frontera
explícita. Un nombre obsoleto debe fallar, nunca hacer `skip`, y el control debe exigir
igualdad exacta con la superficie esperada, no `>= 10`.

### HD-03 — MEDIO — La conducta que rescata las notas no tiene una prueba de comportamiento

**Qué es y dónde.** El único test de `AbortarApertura` verifica el campo `codigo` y que no
sea `SystemExit` (`tests/test_abrir_caso_exit_bajo_mutex.py:91-97`). Ningún test nuevo
ejecuta `main` con una nota en `__notes__`, ni exige el `[AVISO]` de
`scripts/abrir_caso.py:1046-1053`. Tampoco fuerza una pérdida al salir de un `--dry-run`
para demostrar el salto de `scripts/abrir_caso.py:1028-1041` a
`scripts/abrir_caso.py:1075-1076`.

**Por qué importa y qué lo dispara.** El handler de notas es la mitad operacional del
arreglo: sin él, `AbortarApertura` seguiría llevando la pérdida como nota que el operador
no ve. El guard estructural seguiría verde si se borrara la impresión, si se leyera el
atributo equivocado o si se degradara el `dry-run` otra vez a éxito tras perder el mutex.

**Cómo se comprobó.** Una búsqueda de toda la batería de apertura/mutex no encontró una
aserción sobre `__notes__` para este entrypoint. La sonda dinámica construida para la
revisión sí prueba que el código actual funciona: obtuvo código 1 y el canario `[AVISO]`
para el aborto, y código 1 sin CRM ni intake para la pérdida en `dry-run`. Esa evidencia
demuestra la implementación de hoy, no una regresión defendida por el diff.

**Qué haría falta.** Incorporar esas dos sondas como tests: contexto falso que añada una
nota a `AbortarApertura`, y contexto falso que lance `MutexPerdido` al salir limpiamente
del `dry-run`; exigir texto, código y ausencia de CRM/evento.

### HD-04 — BAJO — Cambia la precedencia observable de errores en modo `libre`

**Qué es y dónde.** `head` llama a `_validar_flags` antes de resolver identidad
(`scripts/abrir_caso.py:842-849`); `base` resolvía primero la identidad y validaba la
fuente al entrar en `_despachar_intake` (`base/scripts/abrir_caso.py:822-892` y
`base/scripts/abrir_caso.py:327-330`).

**Por qué importa y qué lo dispara.** Toda invocación inválida a la vez en identidad y en
flags de fuente cambia el primer —y único— diagnóstico. Ejecutado literalmente con
`--fuente manual`, `base` terminó 1 diciendo que faltaban los seis flags de identidad;
`head` terminó 1 diciendo únicamente que faltaba `--src`. No cambia el código, pero sí el
contrato de salida que el mandato pidió comprobar y el dato que recibe el operador.

**Cómo se comprobó.** Ejecuté ambos módulos como CLI reales con esa entrada; las salidas
anteriores fueron distintas y los códigos iguales a 1. Las entradas válidas y los cuatro
abortos de ejecución no cambiaron.

**Qué haría falta.** O aceptar y documentar expresamente la nueva precedencia fail-fast,
con un test de salida, o mantener la validación fuera del mutex pero después de resolver
la identidad si la compatibilidad del diagnóstico es requisito.

### HD-05 — BAJO — El fichero nuevo introduce un `F401`

**Qué es y dónde.** `textwrap` se importa y no se usa
(`tests/test_abrir_caso_exit_bajo_mutex.py:23`).

**Por qué importa y cómo se comprobó.** `python -m ruff check scripts/abrir_caso.py
tests/test_abrir_caso_exit_bajo_mutex.py` devuelve 1 y señala ese `F401`. Los otros seis
diagnósticos de `head` son deuda preexistente o equivalentes presentes en `base`; este es
el diagnóstico nuevo atribuible al diff.

**Qué haría falta.** Eliminar el import.

## 3. Lo que NO es un hallazgo

- No queda hoy una terminación explícita conocida bajo el mutex en el cierre transitivo
  inspeccionado. `scripts.sala_maquina.apply` contiene `typer.Exit`, pero
  `etapa_sala_maquina` lo captura dentro del `try` y lo traduce a resultado
  (`scripts/abrir_caso.py:526-537`). Las dependencias relevantes restantes no contienen
  los patrones de terminación buscados. HD-01/HD-02 son falsos verdes demostrados del
  guard, no la afirmación de que hoy exista ya uno de esos exits en producción.
- Los cuatro `AbortarApertura` conservan en el CLI el texto y código 1 de `base`. Con una
  pérdida simultánea, el handler nuevo sí hace visible la nota con `[AVISO]`.
- `--dry-run` no alcanza alta CRM ni log de intake. Si el cuerpo termina limpio sale 0;
  si se pierde el mutex al abandonar el bloque, sale 1 por `MutexPerdido`. No encontré un
  camino que deje `salida_dry_run=True` y ejecute `_alta_crm`.
- Adelantar `_validar_flags` no rompe la autoderivación válida. Para `drive_ev`, la función
  no rechaza `folder_id`/`team_id` y no recibe `codigo_caso` ni `sufijo`; las cuatro rutas
  de autoderivación pasaron en ambos árboles.
- `CaseBusy` en el camino actual nace al adquirir, antes de que exista un error del cuerpo
  al que anotar una pérdida. `MutexPerdido` en una salida limpia ya es el error primario y
  tiene handler visible. Las excepciones inesperadas no traducidas a Exit conservan su
  traceback; no encontré otro camino actual que pierda una nota distinta.
- Los tres fallos de la suite completa no se imputan al diff: están fuera de los dos
  ficheros cambiados y se reproducen en `base` bajo la misma copia sin `.venv` y el mismo
  entorno restringido.
<!-- informe-literal:fin:p3xq -->

## 2. Evidencia verificada por el adjudicador

- **HD-01 y HD-02 CONFIRMADOS ejecutando el cierre derivado:** devuelve exactamente **17**
  funciones, la misma cifra que el revisor midio por su cuenta. Y `hash_tree_local` esta
  definida en el propio modulo (`scripts/abrir_caso.py:73`), asi que la asercion que la
  nombra pasa por la razon correcta y no por un import — lo comprobe porque me olia a que
  podia estar pasando en falso.
- **El guard reescrito MUERDE las cuatro formas**, probado con mutacion en memoria:
  `typer.Exit`, `typer.Abort`, `sys.exit` y `raise SystemExit`. Antes solo la primera, y yo
  me habia quedado tranquilo con dos mutantes **de la misma forma**.
- **HD-04 CONFIRMADO, y remediado hacia la opcion mejor de las dos que el informe daba:**
  la validacion se mueve a despues de resolver identidad y sigue fuera del lock, con lo que
  se conserva el diagnostico que ve el operador. Sacar la validacion del mutex no
  autorizaba a reordenar lo que el operador lee.
- **HD-05 cerrado sin deuda nueva:** `ruff` baja de **8** diagnosticos en `base` a **6** en
  `head`, porque los `from exc` anadidos retiran dos `B904`.

**Medicion tras remediar: 3.896 tests, 0 fallos con dos semillas (777 y 31337).**
