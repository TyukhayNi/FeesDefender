---
tipo: plan
estado: vigente
creado: 2026-09-26
objeto: que ningún guard ni verja lea un fallo de git como «no hay nada»
spec: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md
---

# Git que falla en voz alta

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que un guard, la verja de cierre o el escaneo de CI que enumeran con `git` **paren o lo declaren** cuando `git` falla, en vez de leer la salida vacía como «no hay nada que objetar» y dar verde sin haber mirado.

**Architecture:** tres sitios con tres remedios del mismo principio —«no pude medir» no es «medí y salió cero»—. En los tests, un helper único (`tests/_git.py`) que ejecuta `git` y hace `pytest.fail` con su stderr si el código de salida no es uno de los que el comando usa como respuesta. En `session_close`, una **sonda** previa: si `git` no responde en el árbol, se dice, los avisos que dependen de él salen como «no comprobado» y la verja corre los tests lentos por si acaso. En CI, `pipefail` en el paso de `leak-scan`.

**Tech Stack:** Python 3.14, `pytest`, GitHub Actions (bash). Sin dependencias nuevas.

## Global Constraints

- Nunca se borra ni se debilita un test para poner verde; los guards migrados conservan sus aserciones.
- Un negativo contra un literal se vacía: los «no contiene» se escriben contra constantes del módulo.
- Aceptar el cambio son dos semillas (777 y 31337), con la suite entera.
- Tocar un guard **no se exime nunca** de revisión (`CLAUDE.md`).

---

## 1. El hallazgo y su frontera

**Lo vio la R1 de Codex de los estados medidos** (2026-09-26, sección SIN VERIFICAR de su informe): `_md_trackeados()` de `tests/test_docs_gobernanza.py` hace `git ls-files` sin mirar el código de salida. En la copia `git archive` sin `.git` sobre la que trabajan los revisores, `git` falla, la lista sale vacía y los guards que la recorren **pasan en verde sin haber mirado nada**. Confirmado en la fuente.

**La frontera no es ese helper: es «un fallo de git se lee como un resultado vacío».** Recorridas las 26 llamadas a `git` del repo (`tests/`, `scripts/`, `core/`), estas son las que la cruzan:

| Sitio | Qué hace hoy si `git` falla |
|---|---|
| `tests/test_docs_gobernanza.py::_md_trackeados` (`git ls-files *.md`) | los guards G2, G7, G8… pasan sin mirar nada |
| `tests/test_docs_gobernanza.py::test_sin_refs_a_docs_plan_legacy` (`git grep`) | pasa: lee el fallo como «sin coincidencias» |
| `tests/test_guard_no_basetemp_versionado.py::_trackeados` (`git ls-files`) | pasa sin mirar nada |
| `tests/test_gitignore_no_inerte.py::_regla` (`check-ignore -v`) | lee «sin regla» |
| **`.github/workflows/leak-scan.yml`** (`git ls-files -z \| xargs -0 -r …`, sin `pipefail`) | **el escaneo de PII de CI sale verde sin escanear**: el código de la tubería es el de `xargs` |
| `scripts/session_close.py::_git_lines` → `_anon_tocado` y los avisos | la verja **se salta los tests lentos** y los avisos dicen «nada que avisar» |
| `tests/_mutantes_*.py` (cinco arneses, `git status --porcelain`) | el arnés cree que el árbol quedó limpio |

**Lo que ya estaba bien, comprobado:** ~~`scripts/precommit_leak_guard.py::_git` (declara el principal «no determinado»)~~, `core/codicert.py`, `core/email_atomize/entregas.py` («desconocido»), ~~`_ls_files` y el lote de `check-ignore` de `test_gitignore_no_inerte.py`~~, el `_git` de `test_precommit_leak_guard.py` (exige 0) y `test_plugin_desplegado.py` (sus llamadores exigen `is not None` y lista no vacía). **Fuera, declarado:** ~~`scripts/check_skills.py`, en modo aviso y, dentro de `session_close`, cubierto por la sonda~~.

> **Corregido por la R1 (§4); lo tachado se deja para que se vea qué se creyó.** El leak-guard solo
> declaraba el principal no determinado con la lista **vacía**, y con una parcial callaba (H-01);
> `_ls_files` y el lote de `check-ignore` miraban el código pero no el stderr con que git dice que
> no leyó algo (H-04); y `check_skills` solo quedaba cubierto por la sonda en el fallo total
> (H-05). Faltaban además dos sitios: el `ls-files` del guard de comentarios de `.gitignore` (H-02)
> y el precheck de `scripts/migrate_repo_local.ps1` (H-03). Y el paso de CI tenía una segunda forma
> de dar verde sin escanear —la lista vacía con código 0—, que la R1 midió y ejecutar el paso
> confirmó (H-06).

**Dos trampas de diseño, medidas antes de escribir:**
- **Algunos comandos usan el código de salida como respuesta.** `git grep` devuelve 1 sin coincidencias y `git check-ignore`, 1 si no está ignorado: «falla si no es 0» a ciegas rompería esos guards. El helper recibe los códigos válidos de cada comando.
- **En `session_close`, un fallo por rama es legítimo.** `_git_count` cuenta cero cuando el remoto de una rama ya no existe (`rev-list` da 128): si cada llamada lanzara, una sola rama así tumbaría el aviso de todas. Por eso allí el remedio es la sonda de «¿responde git aquí?», no hacer lanzar a cada llamada. *(Corregido por la R1, H-05: la sonda cubre el fallo total y nada más. Ahora cada consulta lanza, y el upstream desaparecido —que es lo que daba el 128 por rama— se reconoce por lo que git dice de él, `[gone]`, sin tumbar a las demás. §4.)*

## 2. Tasks

### Task 1: `tests/_git.py` y los guards que lo usan
- [x] Tests primero (`tests/test_guard_git_falla_en_voz_alta.py`): el helper para con el stderr si el código no es válido, admite los códigos que se le dan, para si `git` no existe; `_md_trackeados`, las referencias heredadas, `_trackeados` y `_regla` paran con un `git` que falla, y devuelven algo con el `git` real (control positivo).
- [x] Implementar el helper y migrar `test_docs_gobernanza.py` (dos sitios) y `test_guard_no_basetemp_versionado.py`; `_regla` valida su código como ya hacen sus hermanas del mismo fichero.

### Task 2: `session_close`, la sonda
- [x] Tests primero: con la sonda en fallo, el modo de la verja es COMPLETO y dice por qué; los avisos que dependen de `git` salen como «no comprobado»; con `git` sano, nada cambia.
- [x] Implementar `_git_responde()`, el modo de la verja y el envoltorio de los avisos.

### Task 3: CI, `pipefail`
- [x] Test primero: el paso de `leak-scan` corre con `set -o pipefail` antes de la tubería.
- [x] Implementarlo.

### Task 4: los arneses
- [x] Que el `git status --porcelain` de los arneses pare si git falla: `check=True` en tres, validación a mano en `_mutantes_propiedades_utils.py`, y `_mutantes_particion_124.py` ya validaba (herramientas, no tests: sin test propio). *(Decía «`check=True` en los cinco»; lo precisó la R1.)*

### Task 5: verificación y revisión
- [x] Suite con las dos semillas; mutantes de cada remedio.
- [x] R1 de Codex sobre el diff: una ronda; **`gpt-6-astra` · `medium`**, fila «gobernanza que pueda hacer que la cobertura parezca presente estando ausente: un guard». **NO-SHIP, seis hallazgos, los seis confirmados.** Adjudicación embebida en el §4; acta hermana `…-git-que-falla-en-voz-alta-r1-adversarial-review.md`.

### Task 6: la remediación de la R1 (§4)
- [x] Tests primero, vistos en rojo por su razón: la lista parcial del leak-guard; el stderr con un código que es respuesta, con el doble y, en Windows, con un fichero bloqueado y git de verdad; los llamadores crudos del `.gitignore`; cada consumidor de `session_close` con la sonda verde y la consulta rota; el CHANGELOG que `check_skills` no pudo mirar; el ofensor sintético del guard de referencias; y el paso de CI ejecutado.
- [x] Remedios: `precommit_leak_guard` (lista PARCIAL), `tests/_git.py` (stderr y `-z`), `test_gitignore_no_inerte.py` (`_consulta`), `session_close` (`ConsultaGitFallida` y sus consumidores), `check_skills`, el paso de CI (la lista en un fichero, y no vacía) y `migrate_repo_local.ps1`.
- [x] Suite con las dos semillas, y el arnés de mutantes con los dos del revisor.

## 3. Ejecución (2026-09-26)

- **Commits:** `4b6f06d` (el helper y los guards de tests), `52849da` (`session_close`), `b3af097` (CI) y
  `2c50c37` (los arneses), cada uno con sus tests vistos en rojo antes de implementar.
- **El escenario del hallazgo, reproducido y cerrado.** En una copia `git archive` sin `.git`, los
  guards de gobernanza y de basetemp de **`main` dan 48 verdes sin haber mirado nada**; los de esta
  rama, en la misma copia, **fallan en voz alta los tres que dependen de git** —el de referencias
  heredadas, el G2 de citas y el de basetemps— con el stderr de git, y los otros 45 siguen verdes
  porque recorren el sistema de ficheros.
- **El paso de CI, simulado en bash con un `git` que falla:** sin `pipefail` sale con **0**; con él,
  con **128**.
- **Suite:** 6.501 casos, 0 fallos, 96 omitidos, idéntica con las semillas 777 y 31337. **+18 sobre
  los 6.483 de `main`, y cuadran al test**: los 18 de `tests/test_guard_git_falla_en_voz_alta.py`.
- **Mutantes: 12 de 12 muertos**, cada uno por el test que declaraba (el arnés, en el scratchpad de
  la sesión).

**La remediación de la R1 (§4), el mismo día:**

- **Commit:** `08c42df`, con cada test visto en rojo por su razón antes de su remedio —el del
  leak-guard, con el stderr vacío que describía el revisor; el de `trackeados`, con la ruta
  entrecomillada en octal; el de `ROOT` parcheado, mirando el repo real—.
- **Las cinco reproducciones del propio revisor** (`reproducir.py`, copiado cambiando solo de dónde
  importa) corridas contra el árbol remediado: **ninguna da ya verde ni calla**. La lista parcial se
  declara; `grep` y `check-ignore` con el fichero bloqueado paran; el guard de comentarios para con
  el índice roto; y `session_close` corre los lentos, nombra la rama que no pudo contar y declara no
  comprobada la trazabilidad con el objeto corrupto.
- **La verja real** (`python -m scripts.session_close`) sobre el árbol remediado, antes de los
  últimos retoques —el fallo «mudo» y la raíz leída al llamar, que solo tocan tests—: verde con las
  dos semillas, y su aviso de publicación nombra ya en una línea las diez ramas con el upstream
  desaparecido en vez de contarlas como cero.
- **Suite:** 6.753 casos, 0 fallos, 96 omitidos, idéntica con las semillas 777 y 31337, sobre el
  árbol con `main` (`ca250a4`) ya mezclado. **+58 sobre los 6.695 que colecciona `main`, y cuadran
  al test**: los 53 de `tests/test_guard_git_falla_en_voz_alta.py` (eran 18) y los 5 nuevos de
  `tests/test_precommit_leak_guard.py`; ningún otro fichero cambia su recuento.
- **Mutantes: 46 de 46 muertos**: los 11 vivos de la primera tanda con las anclas al día —el 12,
  «CI sin pipefail», ya no aplica: no hay tubería—, los 33 del remedio y los dos del revisor, el de
  las referencias que devuelven `[]` (27) y el del `pipefail` desactivado, reformulado como la
  vuelta a la tubería (44).

## 4. Adjudicación de la revisión adversarial (Codex, 2026-09-26) — NO-SHIP, remediado

- **Objeto revisado:** la pieza entera, `a703025` → `e7b408d` —el helper, los guards migrados, la sonda de `session_close`, el paso de CI, los arneses y este plan—, 12 ficheros
- **Ronda:** 1, sobre el diff — la única que la tabla de `CLAUDE.md` da a esta pieza (toca guards, que no se eximen nunca; no decide quién escribe ni destruye datos)
- **Revisor:** Codex CLI `0.155.0-alpha.16.4`, `gpt-6-astra`·`medium` releídos del log; `service_tier="default"` afirmado desde el lanzador conservado
- **Informe recibido:** `2026-09-26-git-que-falla-en-voz-alta-r1-adversarial-review.md`, `sha256` del bloque literal `5de221d61b23318cf93e5b718e3532c5a7dfc94f3ca1bfbcff4ba2f930e60ff0`
- **Hallazgos:** 6 — 1 `alta`, 3 `media`, 2 `baja` —, más uno propio (A-01). **Los seis confirmados contra la fuente, ninguno refutado**
- **Remediado en:** `08c42df` (los seis y el propio, con sus tests) y el commit de documentación que trae esta adjudicación

**Por qué `gpt-6-astra`·`medium`, dicho como la política pide.** Es la fila «gobernanza que pueda
hacer que la cobertura parezca presente estando ausente: un guard». La frontera, nombrada: un guard,
la verja de cierre o el escaneo de CI que dan verde **sin haber mirado**. Y el informe es la prueba
de que la fila era la buena: cinco de los seis hallazgos son exactamente eso, fuera de los sitios
que yo había inventariado.

**La pregunta que ordena la adjudicación —«¿de qué frontera es esto un ejemplo?»— tiene aquí una
sola respuesta**, y el informe la encuentra por cuatro caras que mi inventario no veía: yo busqué
«un código de salida que no se mira» y la frontera es **«una respuesta incompleta que se lee como
completa»**. Esa respuesta puede venir con un código que falla (lo que cerraba la pieza), con un
código que es respuesta y un stderr que dice que no leyó algo (H-04), con una sonda que responde
mientras las consultas no (H-05), con una lista parcial que no está vacía (H-01) o con una lista
vacía que sale con 0 (H-06, CI). Remediarlas una a una sin nombrar la frontera habría sido repetir
las cuatro rondas del mutex.

| # | Hallazgo | Sev. · coste | Adjudicación y remedio |
|---|---|---|---|
| **H-01** | El leak-guard calla cuando solo consigue una blocklist **parcial** | alta · acotado | **Confirmado** en la fuente: `main` solo imprimía el aviso con la unión de términos **vacía**; con un solo término en el worktree y `git worktree list` fallando, escaneaba con la mitad y devolvía 0 con stdout y stderr vacíos. Mi §1 lo daba por bien («declara el principal no determinado»), y era falso: lo guardaba en un objeto y no se lo decía a nadie. Remedio, **sin cambiar la política** (sigue sin fallar cerrado, como dice su docstring): `_resolver_principal` clasifica cada salida —resuelto, este árbol ya es el principal y bare están **determinados**; todo lo demás, no—, `Blocklist.principal_determinado` lo lleva (por defecto `False`: una lista construida sin decirlo no se da por completa) y `main` declara la lista **PARCIAL** con cuántos términos escaneó y por qué no hubo principal. Tests con el fallo inyectado solo en `worktree list` y el resto de git real: el término del principal bloquea con git sano, con el fallo se declara parcial, el principal propio no avisa, y la clasificación de las siete salidas. Mutantes 13-19. |
| **H-02** | Otro `ls-files` del mismo módulo seguía haciendo pasar un guard vacío | media · acotado | **Confirmado**: `_gitignores_trackeados` usaba el `_git` crudo sin mirar el código, y el guard de comentarios recorría `[]` en verde con el índice roto; `ignora()` leía cualquier código distinto de 0 como «no ignorada». Remedio: la enumeración pasa por `tests/_git.py` (conservando la separación NUL, ver A-01); las consultas del módulo, por una `_consulta` validada —código **y** stderr, H-04—, también las dos crudas de dos tests (`init` y la asimetría de `--no-index`), que habrían pasado sin medir. `ignora` sube a `_ignora` y el guard de comentarios a `_reglas_muertas(repo)`, para probarlos contra un ofensor real de laboratorio. Mutantes 06 y 23-26. |
| **H-03** | El precheck PowerShell anunciaba árbol limpio tras un rc=128 | baja · acotado | **Confirmado** en PowerShell 7.6 y 5.1: decidía por la salida y no por `$LASTEXITCODE`. Remedio en los tres sitios que el informe señala: `status` y `rev-parse` paran con su código; `remote get-url` distingue el 2 («no hay `origin`», que es una respuesta) de cualquier otro. **Sin test en la suite, dicho:** es un script histórico sin arnés de PowerShell, y hoy ni siquiera llega a ese paso —su ruta de Drive ya no existe—. Verificado ejecutando sus tres bloques, extraídos, en un directorio sin repo (los tres paran con `[ERR]`, salida 1) y en un repo sin remoto (sigue, con el 2), en las dos versiones. |
| **H-04** | `grep` y `check-ignore` pueden fallar al leer y aun así devolver 0/1 | media · acotado | **Confirmado con git de verdad**, no solo con el log del revisor: un test mío bloquea en exclusiva el fichero ofensor y, antes del remedio, el guard de referencias devolvía `[]`; con el `.gitignore` bloqueado, la decisión dejaba de ver un fichero trackeado e ignorado. Remedio conservador, como el revisor ofrece: **un stderr no vacío también para**, en el helper y en las consultas del módulo del `.gitignore`. Medido antes de decidirlo: las catorce consultas de los guards y de `session_close` no escriben nada por stderr en el árbol sano, así que la regla no hace ruido hoy; si un día git avisa de algo inocuo, el rojo lleva su texto y se clasifica entonces, con la evidencia delante. Tests con el doble (códigos 0 y 1) y los dos de Windows con el bloqueo; y, para que la regla del stderr no tape la del código, un fallo «mudo» —128 sin stderr— en cada consulta validada. Mutantes 20 y 22, y los 03-05, 23 y 30, que solo mata el mudo. |
| **H-05** | Una sonda verde permite decisiones y avisos sobre consultas fallidas | media · estructural | **Confirmado**, y la trampa 2 de mi §1 era el error de fondo: el remedio de la sonda era correcto para el fallo total y yo lo presenté como si cubriera cada consulta. Remedio: `_git_lines` **lanza** `ConsultaGitFallida` (código, stderr o git que no se ejecuta), y cada consumidor declara su «no lo sé»: la verja corre los lentos si no se sabe si `core/anon/` está tocado; `_si_git_responde` declara no comprobado el aviso cuya consulta falla por el camino; `_git_count` devuelve `None`, no 0. **Y la trampa 2 se resuelve sin tumbar el aviso de todas las ramas**: el upstream desaparecido —diez de las veintiuna ramas de hoy, todas las que hacían fallar `rev-list`— es un estado que git **dice** (`[gone]`), así que se nombra en una línea y no se cuenta; cualquier otro fallo por rama sale como «rama NO comprobada», y «sin commits sin publicar» solo se dice si no hay ninguna. `check_skills`, cuyo `run()` tenía el mismo `[]`, declara el CHANGELOG no comprobado y lo cuenta como aviso. Tests de cada consumidor y uno de punta a punta con la sonda verde y todo lo demás roto. Mutantes 30-42. |
| **H-06** | Sobrevivían pérdidas completas de detección y un `pipefail` desactivado | baja · acotado | **Confirmado**, con los dos mutantes del revisor: el control positivo del guard de referencias solo pedía `isinstance(list)`, y el test de CI buscaba `set -o pipefail` en el texto. Remedio: un ofensor sintético pasa por `_refs_a_docs_plan_legacy(repo)` y por el filtro de excepciones extraído (`_ofensores_plan_legacy`); y el test de CI **ejecuta** el bloque `run:` tal cual lo lee GitHub —sustituye al que buscaba el texto, que ya no tendría qué buscar: sin tubería no hay `pipefail`, y la propiedad que probaba, «un listado que falla no da verde», la prueban ahora cinco casos en vez de una regex—, con `bash -e`, un `git` falso y un `python` espía, en cinco casos y uno más con git de verdad sin índice. Al ejecutarlo apareció lo que el revisor midió y dejó como límite distinto: **una lista vacía con código 0 también daba verde**, y un índice ausente la produce con git real. Por eso el paso cambia: la lista va a un fichero y se exige que no esté vacía antes de escanear; sin tubería, `pipefail` sobra y se retira. Mutantes 27-29 y 43-45; el del revisor sobre `pipefail` es el 44, reformulado. |
| **A-01** (propio) | `trackeados()` —mi helper— entrecomillaba las rutas con tildes | baja · trivial | Lo vi al remediar H-02, que pedía conservar la separación NUL: sin `-z`, git escapa en octal las rutas con bytes no ASCII (`core.quotePath`) y la ruta devuelta no existe. Hoy no hay ninguna en el repo (medido: cero), así que no había verde falso; con la primera, lo habría. Remedio: `-z`. Test con `año.md` en un laboratorio sin la configuración de la máquina; mutante 21. |

**Lo que el revisor dejó en pie, y conviene no perderlo:** el escenario original está cerrado —48
verdes sin mirar en `base/`, tres rojos pertinentes y 45 verdes independientes de git en `head/`—;
los códigos que se aceptan como respuesta son los correctos (el defecto estaba en lo que los
acompaña, no en exigir 0 a ciegas); los cinco preflights de arneses paran ante un 128; y la salida
de `main` por dependencias que faltan va antes de git y no rompe la propiedad.

**Las observaciones que no son hallazgos, adjudicadas una a una:**

- **`scripts/health_check.py` y los `_corre` de tres arneses** tienen la misma propiedad con otras
  herramientas: el primero da tres marcas positivas con todos los comandos fallando, y los segundos
  leen un pytest que no arrancó como línea base verde. **Ciertas, y fuera**: no son git ni guards de
  la suite. Fichadas en `MEJORAS #315` con la reproducción del revisor.
- **La Task 4 decía «`check=True` en los cinco arneses»** y eran tres con `check=True`, uno con
  validación manual y uno que ya validaba. Corregido en el §2.
- **Sus dos rojos de `test_session_close_no_pude_medir.py`** presuponen un `.venv` descubrible desde
  el checkout y el revisor corrió con un intérprete externo sobre una copia `git archive`: no son del
  diff, y en el repo pasan. Él mismo no los atribuyó.
- **Una del propio remedio, cazada antes de commitear.** Al inyectar `repo` con un valor por
  defecto, la raíz quedaba ligada al DEFINIR la función, y el `reproducir.py` del revisor —que
  redirige el guard parcheando `ROOT`— habría mirado el repo real sin decirlo. Lo destapó
  correrlo contra el remedio; se lee ahora al llamar. Test y mutantes 46-47.
- **El guard de referencias acusó a mi propio test**, que citaba de corrido un plan heredado de
  `docs/` para montar el laboratorio. Tenía razón: la cita se parte en dos, no se amplían las
  excepciones.
- **Y acusó después al acta de esta ronda**, y ahí la cita no se puede partir: es el informe
  literal del revisor, que nombra el plan heredado **sintético** de su laboratorio, y ese bloque lo
  sella G8. Excepción por nombre en `_ofensores_plan_legacy`, con el porqué escrito, como la que el
  guard ya tenía para la cita que coincide por casualidad con un plan de El Contable. Es la única
  excepción que esta pieza añade a un guard, y se dice.

**Cobertura de la remediación: AUSENTE.** Ningún revisor ha mirado el código de este remedio, y no
se da por revisado. La tabla de `CLAUDE.md` le da una ronda a esta pieza y ya la tuvo; una segunda
sobre la remediación solo la autoriza Nikolai. Lo que sí la respalda, sin sustituir a la ronda: los
tests en rojo antes de cada remedio, la suite con las dos semillas y el arnés de mutantes (§3).
