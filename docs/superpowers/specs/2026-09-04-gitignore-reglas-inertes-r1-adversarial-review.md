---
tipo: revision-adversarial
objeto: "diff del destrackeo de .claude/settings.local.json y su guard de reglas inertes"
objeto_rev: "rama claude/settings-local-untrack, commit f7284d4"
commit: f7284d4
ronda: "1"
revisor: Codex
veredicto: LISTA-CON-CAMBIOS
marcador_nonce: qwzt
sha256_informe: f59966eb791476fbb7fb12ec43ab4a4b5a07124cc73a4bf084d1d710e69f38a9
adjudicado_en: docs/superpowers/specs/2026-09-04-gitignore-reglas-inertes-r1-adversarial-review.md §3
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1.** El §0 es el mandato literal, el §1 conserva la voz
> del revisor sin una coma cambiada, el §2 es la evidencia que verifiqué por mi cuenta y el
> §3 mi adjudicación.
>
> **Dónde vive la adjudicación, y por qué aquí.** La regla de `CLAUDE.md` es que la
> adjudicación va *embebida en el spec o el plan revisado*. **Este cambio no tiene ninguno
> de los dos**: nació de que Nikolai no podía crear una rama desde la UI. Crear un spec
> retrospectivo solo para tener dónde adjudicar sería papeleo —y este proyecto ya midió
> 9,4 líneas de `docs/` por línea de `core/`—, así que la adjudicación va en el §3 de esta
> misma acta, **declarado en el frontmatter** para que nadie la busque en otro sitio. No es
> la forma preferente y se dice, en vez de disimularlo. Precedente del mismo día:
> `2026-09-04-crm-lectura-relaciones-r1-adversarial-review.md`.
>
> **Una ronda y no dos, por radio de daño** (`CLAUDE.md` §«Cuántas rondas»): la pieza no
> decide quién puede escribir sobre qué copia y no puede destruir ni corromper datos de
> cliente. Toca un `.gitignore` y un fichero de tests; ninguna línea de `core/` ni de
> `scripts/`. **Y el techo se respeta: no hay R2.** La remediación de los cuatro hallazgos
> queda cubierta por su prueba de mutación —9 mutantes matados y 1 superviviente
> declarado— y **no por un revisor**, que es distinto y se declara así.

## 0. Mandato, literal

# Mandato de revisión adversarial — R1 sobre un DIFF

Eres el revisor adversarial. **Solo lectura sobre el objeto.** No escribas ni modifiques nada
bajo `../obj/`. Tu único artefacto de salida es `INFORME.md` en tu directorio de trabajo actual.

## 1. El objeto

Dos copias congeladas de un repositorio Python (Windows), archivadas con `git archive`, sin `.git`:

- `../obj/base/` — commit `cb5b6b8`, el estado ANTES del cambio.
- `../obj/head/` — commit `f7284d4`, el estado DESPUÉS. **Este es el que se revisa.**

Compara los dos árboles tú mismo (`diff -ru`, o fichero a fichero). Los ficheros tocados son
cuatro: `.claude/settings.local.json` (borrado del índice), `.claude/settings.local.json.example`
(nuevo), `.gitignore` (una excepción nueva) y `tests/test_gitignore_no_inerte.py` (nuevo guard).

**Al abrir y al cerrar, calcula y declara el `sha256` del objeto** así, y dilo en el informe:

```
cd ../obj/head && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Es la prueba de no-mutación que sustituye a `git status` (no hay `.git`). Sin `.git` no puedes
acreditar la genealogía de la copia: verifica contenido y hash, no que sea el commit que digo.

## 2. Qué problema resolvía el cambio, según su autor

`.claude/settings.local.json` estaba **trackeado** pese a figurar en el `.gitignore`.
`.gitignore` no aplica a lo que ya está en el índice, así que esa línea era una **regla inerte**:
escrita, visible y sin morder. Claude Code le añadía entradas de permisos, git veía el cambio, y
cambiar de rama fallaba con «haz commit o stash». El remedio fue `git rm --cached` (deja el
fichero en disco), una plantilla `.example`, y un **guard** que cierra la clase: ningún fichero
trackeado puede estar ignorado por el `.gitignore`.

Al correr el guard por primera vez dio cinco positivos. El autor los adjudicó así:
`.env.example` era un **falso positivo del propio guard** (la decisión se tomaba desde
`check-ignore -v`, que reporta también las negaciones, y el fichero salía acusado por su propio
rescate `!.env.example`); los cuatro `.claude/skills/*/logs/README.md` eran **verdaderos
positivos**, ignorados de verdad por la regla `logs/`, y su trackeo es deliberado, así que se
declaró la excepción en el `.gitignore` con tres líneas.

**No tomes nada de este párrafo como verdad.** Es la tesis del revisado. Verifícala o túmbala.

## 3. Lo que tienes que atacar, en orden de daño

1. **¿La excepción del `.gitignore` hace lo que dice?** Las tres líneas son
   `!.claude/skills/*/logs/`, `.claude/skills/*/logs/*`, `!.claude/skills/*/logs/README.md`.
   ¿Deja de ignorar algo que SÍ debía seguir ignorado — un `.jsonl` de telemetría con datos
   reales, un `logs/` de otro sitio del repo, un `README.md` en un `logs/` que no sea de skills?
   ¿Hay rutas de skill que el glob `*` no alcanza (subdirectorios más profundos)? Móntate un repo
   de laboratorio y **mídelo**, no lo razones.
2. **¿El guard puede quedarse verde sin mirar nada?** Busca cada vía: una excepción que se trague,
   una lista vacía que pase por «no hay nada», un `subprocess` cuyo fallo no se detecte, un
   `assert` cuya condición sea siempre cierta, una sonda que dejó de existir. El autor dice haber
   cerrado tres de esas vías; comprueba si quedan más.
3. **¿Los tests prueban el contrato que dicen probar, o lo esquivan?** En particular
   `test_el_guard_grita_si_git_no_puede_responder` usa `Path(REPO.anchor)` (la raíz del disco)
   como «no es un repo git». ¿Es fiable en cualquier máquina? ¿Y el fixture `repo_lab`, que hace
   `git init` sin configurar usuario — puede fallar o, peor, pasar por motivos equivocados?
4. **¿El guard produce falsos positivos que harán que alguien lo desactive?** Un guard que acusa
   reglas sanas se acaba borrando. Piensa en ficheros trackeados a propósito que el `.gitignore`
   cubra por vías que el guard no distinga.
5. **¿El mensaje de fallo del guard lleva a un remedio que funciona?** Afirma que un `!ruta` a
   secas no basta cuando el padre está excluido por un patrón de directorio. Verifícalo.
6. **La plantilla `.example` y el borrado del original.** ¿Se pierde algo que hiciera falta? ¿El
   `.example` queda a su vez atrapado por alguna regla?
7. **Cualquier cosa que se te ocurra y que dañe.** No te limites a mi lista.

## 4. Puedes EJECUTAR, y se te pide que lo hagas

Hay un Python de sistema con `pytest`:
`C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`

- **Copia** lo que necesites a tu workdir; **no mutes `../obj/`**.
- Usa `--basetemp` **relativo dentro de tu workdir** (tu sandbox no puede crear en `C:\t\...`).
- **No tienes `pytest-randomly`**: el orden aleatorio con dos semillas queda **SIN VERIFICAR**
  por tu parte, y lo cubre el autor. Dilo así, no lo omitas.
- Puede faltarte alguna dependencia del repo (`filelock`, `httpx`, `dotenv`). Lo que no puedas
  importar, declaralo SIN VERIFICAR — no lo atribuyas al objeto ni lo des por refutado.

## 5. Forma del informe (`INFORME.md`)

Por cada hallazgo: **identificador** (`H1`, `H2`…), **severidad** (`CRÍTICO` / `ALTO` / `MEDIO` /
`BAJO`), **ruta y línea**, **qué está mal**, **cómo lo comprobaste** (comando y salida, o «solo
lectura»), y **el escenario concreto de fallo**: entradas o estado → resultado equivocado. Un
hallazgo sin escenario de fallo no vale.

Marca explícitamente lo que **no** pudiste verificar y por qué.

**Y cierra el informe con una línea de veredicto, con la palabra exacta y sola**, elegida de este
set cerrado y de ninguna otra parte:

```
VEREDICTO: SHIP
VEREDICTO: LISTA-CON-CAMBIOS
VEREDICTO: REQUIERE-REVISION
VEREDICTO: NO-SHIP
VEREDICTO: NO-EJECUTABLE
```

No hay premio por encontrar cosas ni por no encontrarlas. Si el diff está bien, dilo y explica qué
atacaste sin éxito — eso también es información. Si está mal, sé concreto.

## 6. Higiene del directorio de trabajo

Tu directorio de trabajo debe contener **solo este `MANDATO.md`** al empezar. Si encuentras
cualquier otro fichero preexistente —en particular un `INFORME.md`— **no lo leas, no lo uses y
dilo en la primera línea de tu informe**: seria residuo de otra ronda sobre otro objeto, y
contaminarlo invalidaria esta.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:qwzt -->
ADVERTENCIA DE HIGIENE: al inicio existía, además de `MANDATO.md`, el fichero preexistente `_stdout.log`; no lo leí ni lo usé, y lo trato como residuo potencial de otra ronda.

# Revisión adversarial R1 — `base` cb5b6b8 frente a `head` f7284d4

## Integridad y alcance

- Hash de apertura del objeto, calculado con el comando literal del mandato: `e74c1aaad3bab090df5dbb962a2ca3e0ff32ad2cf4f424182ecabb504d9a16fe *-`.
- Hash de cierre del objeto, calculado otra vez con el mismo comando: `e74c1aaad3bab090df5dbb962a2ca3e0ff32ad2cf4f424182ecabb504d9a16fe *-`.
- Los hashes coinciden. No se escribió bajo `../obj/`; las ejecuciones se hicieron sobre copias desechables en el workdir, ya retiradas.
- `git diff --no-index -- ../obj/base ../obj/head` confirmó los cuatro cambios declarados: borrado de `.claude/settings.local.json`, alta de `.claude/settings.local.json.example`, tres reglas nuevas en `.gitignore` y alta de `tests/test_gitignore_no_inerte.py`.
- Al no haber `.git` en las copias congeladas, queda **SIN VERIFICAR** que los árboles procedan realmente de los commits nominales; se verificaron contenido y hash, no genealogía.

## Hallazgos

### H1 — MEDIO — `tests/test_gitignore_no_inerte.py:61-63`, `tests/test_gitignore_no_inerte.py:88-104`

**Qué está mal.** `_ignorados()` usa `git check-ignore` sin aislar las fuentes de exclusión. Git no consulta solo el `.gitignore` versionado: también aplica `.git/info/exclude` y `core.excludesFile`. El guard y su mensaje presentan cualquier coincidencia como una regla del `.gitignore` del proyecto y recomiendan tocar el repositorio. Eso hace el resultado dependiente de cada máquina y produce falsos positivos sobre ficheros correctamente trackeados.

**Cómo lo comprobé.** En repositorios de laboratorio con `README.md` trackeado y un `.gitignore` sin regla para Markdown:

```text
python probe_gitignore.py
[CORE_EXCLUDESFILE]
README.md: IGNORADO; regla="C:\t\gi1\inf\probe_repos\global.ignore":1:*.md | README.md; rc=0
[INFO_EXCLUDE]
README.md: IGNORADO; regla=.git/info/exclude:1:*.md | README.md; rc=0
```

Después configuré en la copia de `head` un `core.excludesFile` con `*.md` y ejecuté:

```text
python -m pytest tests/test_gitignore_no_inerte.py::test_ninguna_regla_de_gitignore_es_inerte ...
FAILED ...
.claude/commands/cierre.md <- C:/t/gi1/inf/probe_repos/global.ignore:1:*.md
... (cientos de Markdown trackeados)
```

**Escenario concreto.** Un desarrollador tiene `*.md` en su fichero global, o `docs/` en `.git/info/exclude`, para ocultar artefactos locales. Estado: el repositorio no contiene ninguna regla nueva inerte y sus Markdown/documentación están trackeados deliberadamente. Resultado equivocado: el test acusa masivamente esos ficheros, propone excepciones versionadas para una preferencia local y deja la suite roja solo en esa máquina. Es el tipo de ruido que incentiva desactivar el guard.

### H2 — MEDIO — `tests/test_gitignore_no_inerte.py:145-151`

**Qué está mal.** El fixture `repo_lab` descarta los `returncode` tanto de `git init` como de `git add -f`. Si `git init` falla y el `tmp_path` está debajo de otro repositorio, el `git add -f` siguiente puede operar sobre el índice del repositorio padre. Peor: los cinco tests del archivo pueden quedar verdes usando ese padre, así que el laboratorio no acredita que haya creado el repo aislado que dice crear.

**Cómo lo comprobé.** En una copia desechable de `head`, sustituí solo la llamada del fixture por `git init --opcion-inexistente .`, mantuve un repositorio padre y usé un basetemp relativo no ignorado:

```text
python -m pytest tests/test_gitignore_no_inerte.py -q -p no:cacheprovider --basetemp=adv_bt
..... [100%]

git ls-files -- adv_bt
adv_bt/test_la_decision_muerde_sobre_0/.env.example
adv_bt/test_la_decision_muerde_sobre_0/limpio.txt
adv_bt/test_la_decision_muerde_sobre_0/secreto.txt
adv_bt/test_la_decision_respeta_la_ne0/.env.example
adv_bt/test_la_decision_respeta_la_ne0/limpio.txt
adv_bt/test_la_decision_respeta_la_ne0/secreto.txt
```

**Escenario concreto.** `git init` falla por permisos, configuración/template rota o indisponibilidad puntual; pytest ha creado su basetemp dentro de un checkout Git escribible. Resultado equivocado: 5/5 verde, pero las sondas se añaden con `-f` al índice real del checkout padre. El guard creado para detectar contaminación del índice puede contaminarlo él mismo y no avisar. Deben comprobarse ambas llamadas y acreditarse que `git rev-parse --show-toplevel` coincide con `tmp_path` antes de añadir.

La ausencia de `user.name`/`user.email` no es el problema: ejecuté el archivo con `GIT_CONFIG_NOSYSTEM=1` y `GIT_CONFIG_GLOBAL=NUL`, y dio `5 passed`; `init` y `add` no necesitan identidad mientras no haya commit.

### H3 — BAJO — `tests/test_gitignore_no_inerte.py:189`

**Qué está mal.** `Path(REPO.anchor)` no significa necesariamente «fuera de todo repositorio Git»; solo significa raíz de la unidad. El test depende de que esa raíz no contenga `.git`.

**Cómo lo comprobé.** En esta máquina `C:\` no es repositorio y el test pasa. En el laboratorio, el mismo `git check-ignore` ejecutado desde una ruta que sí pertenece a un repositorio devolvió un código semántico 0/1, no 128. La selección de la ruta, por inspección, no prueba la precondición que el test asume.

**Escenario concreto.** Un runner/contenedor inicializa `/` como repositorio, o una máquina Windows tiene `C:\.git`. Entrada: `_ignorados([".env"], repo=Path(REPO.anchor))`. Resultado equivocado: no se lanza `RuntimeError` y el test falla aunque el control de códigos de error funcione. Es un falso rojo de portabilidad, no una vía para que el guard de producción quede verde.

### H4 — BAJO — `.gitignore:63-65`

**Qué está mal.** El `*` de `.claude/skills/*/logs/` cubre exactamente un componente de skill; no cruza `/`. La explicación habla genéricamente de los `logs/README.md` «de las skills», pero una skill anidada/namespaced queda fuera.

**Cómo lo comprobé.** Laboratorio con las reglas exactas del diff:

```text
.claude/skills/alpha/logs/README.md: NO_IGNORADO; regla=!.claude/skills/*/logs/README.md; rc=1
.claude/skills/grupo/alpha/logs/README.md: IGNORADO; regla=logs/; rc=0
```

**Escenario concreto.** Se añade una skill en `.claude/skills/grupo/alpha/` y se trackea su `logs/README.md` como esquema documental. Resultado: la excepción no la alcanza y el guard falla por la regla global `logs/`, aunque el caso es conceptualmente el mismo que los cuatro README rescatados. Hoy no existe un `logs/README.md` trackeado a esa profundidad, por lo que es una limitación futura, no una rotura presente.

## Ataques sin hallazgo

- **Alcance de las tres reglas.** Medido con Git 2.53.0.windows.2: el README directo de una skill queda no ignorado; `telemetry.jsonl`, un JSONL en subdirectorio y un README anidado bajo `logs/subdir/` siguen ignorados. `otro/logs/README.md` y `otro/logs/telemetry.jsonl` siguen ignorados. No encontré ampliación hacia otros `logs/` ni exposición de telemetría real.
- **Necesidad de las tres líneas.** Con solo `!…/README.md`, el README sigue ignorado porque el padre continúa excluido. Con solo el rescate del directorio, tanto README como `telemetry.jsonl` quedan expuestos. Con las tres líneas, solo el README directo queda rescatado. El texto del remedio es correcto para ese layout.
- **Tesis de los cuatro positivos.** En un índice reconstruido desde cada archivo, los cuatro `.claude/skills/*/logs/README.md` dieron `check-ignore --no-index rc=0` en `base` (regla `logs/`) y `rc=1` en `head`. La tesis queda confirmada para esos cuatro ficheros.
- **Vacuidad del guard.** El test principal exige una lista de trackeados no vacía; `_ls_files` y `_ignorados` verifican sus códigos de retorno. El mutante sin `--no-index` produjo exactamente un fallo en `test_la_decision_muerde...`; el mutante que tragaba el `returncode` de `check-ignore` produjo exactamente un fallo en `test_el_guard_grita...`; volver a decidir desde `-v` produjo cuatro fallos. No hallé otra salida vacía aceptada como éxito en la ruta del guard. H2 sí deja defectuoso el laboratorio, no la decisión principal.
- **Plantilla y borrado.** `base` trackea `.claude/settings.local.json`; `head` trackea solo `.claude/settings.local.json.example`. El fichero real sigue dando `check-ignore rc=0` y la plantilla `rc=1`. Ambos JSON parsean; la plantilla conserva `$schema`, `env` y `permissions`, y el original no contenía permisos ni secretos operativos, solo comentarios. Desde un `git archive` queda **SIN VERIFICAR** que `git rm --cached` preservara físicamente el fichero local del autor; solo se acredita su ausencia del árbol de `head`.
- **Ejecución focal.** Con Python 3.14 y configuración Git global/sistema anulada: `python -m pytest tests/test_gitignore_no_inerte.py -q -p no:cacheprovider --basetemp=../bt_final_target` → `5 passed`.
- **Suite completa.** Con `cwd` en la copia y basetemp hermano: llegó al 100 %, pero no quedó verde por tres tests de descubrimiento de intérpretes (`test_mcp_wrappers` y `test_session_close_no_pude_medir`). Los mismos tres fallaron en `base`; no se atribuyen al diff. Los tests lentos, Ollama y el fixture PII se omitieron según sus marcadores/condiciones, así que esas coberturas quedan **SIN VERIFICAR**. Ninguna dependencia de importación (`filelock`, `httpx`, `dotenv`) bloqueó la colección ni el archivo revisado.
- **Orden aleatorio.** Las dos corridas con semillas quedan expresamente **SIN VERIFICAR** porque no está instalado `pytest-randomly`, conforme al mandato.

Los dos hallazgos MEDIO requieren cambios acotados en el guard/tests; la política central del diff (destrackear la configuración local, conservar plantilla y rescatar solo los README directos sin exponer telemetría) sí quedó medida y funciona.

VEREDICTO: LISTA-CON-CAMBIOS
<!-- informe-literal:fin:qwzt -->

## 2. Evidencia verificada al adjudicar

Comprobado por mí, sobre el repositorio real y sobre repos de laboratorio, no sobre el
informe:

| Qué | Cómo | Resultado |
|---|---|---|
| El `.gitignore` versionado tiene **más precedencia** que `.git/info/exclude` | repo de laboratorio con ambas fuentes emparejando la misma ruta, y luego con `!ruta` en `info/exclude` | `-v` atribuye a `.gitignore:1:ambas.txt` en los dos casos → **una regla inerte del repo no puede quedar enmascarada** por una exclusión local; el filtro del remedio no abre falsos negativos |
| La anulación de `core.excludesFile` funciona | `-c core.excludesFile=<f>` frente a `… -c core.excludesFile=` | `IGNORADO` → `versionable`; el último `-c` gana |
| La fuente que declara `-v` se parsea bien con rutas de Windows | 4 sondas: `.gitignore`, `sub/.gitignore`, fichero global absoluto, `.git/info/exclude` | fuentes `'.gitignore'`, `'sub/.gitignore'` (versionadas) frente a `''` y `'.git/info/exclude'` (no) |
| `**` no se va de alcance | laboratorio con las tres reglas reales y 7 sondas | rescata `skills/alpha/logs/README.md` **y** `skills/grupo/alpha/logs/README.md`; siguen ignoradas `uso.jsonl` a las dos profundidades, `logs/sub/README.md`, `otro/logs/README.md` y `logs/app.log` |
| La telemetría real sigue ignorada | `git check-ignore --no-index -q` sobre las 4 carpetas `logs/` de skills del repo | los 4 `README.md` versionables; `uso.jsonl` y `W-XXXXXX_post.jsonl` **ignorados** |
| Las 4 carpetas `logs/` de skills están a un solo nivel | `find .claude/skills -type d -name logs` | 4 rutas, todas de profundidad 1 → H4 es limitación futura, no rotura presente |
| `GIT_CEILING_DIRECTORIES` deja a git sin repositorio | `rev-parse --show-toplevel` y `check-ignore` en un tmp con y sin ceiling | `rc=128` en los dos casos, y con ceiling **no depende de los ancestros** |
| El guard muerde | arnés de mutación, 10 mutantes, uno por frontera | **9 matados** por el test previsto; **1 superviviente declarado** (M6, ver §3); worktree limpio y guard verde al restaurar |
| La suite no se resiente | suite completa, dos semillas (`777` y `31337`), contada por JUnit XML | **3.945 tests, 0 fallos, 0 errores, 87 skips** en ambas. Delta +3 sobre la corrida previa (3.942) = los tres tests nuevos |

**Dos «SIN VERIFICAR» del revisor que sí pude cubrir:**

- *«Desde un `git archive` queda SIN VERIFICAR que `git rm --cached` preservara físicamente
  el fichero local del autor»*. Verificado: `.claude/settings.local.json` sigue en disco en
  la raíz del repo (832 bytes), con sus permisos locales.
- *«La suite completa no quedó verde por tres tests de descubrimiento de intérpretes
  (`test_mcp_wrappers` y `test_session_close_no_pude_medir`)»*. **No reproducen aquí**: 23,
  47 y 14 tests de esos módulos, todos verdes en las dos semillas. Es su entorno —Python de
  sistema, otro juego de intérpretes presentes—, no el diff. Él ya lo había acotado
  correctamente al medirlos rojos también en `base`.

**Lo que queda SIN VERIFICAR, y se declara:** la genealogía de las copias (sin `.git` no se
acredita que los árboles procedan de los commits nominales; se verificó contenido y hash);
los tests marcados lentos y los de Ollama, omitidos por sus marcadores; y **la remediación
de los cuatro hallazgos, que ningún revisor ha mirado** — solo su prueba de mutación.

## 3. Adjudicación de la revisión adversarial (Codex, 2026-09-04) — LISTA-CON-CAMBIOS, remediado

- **Objeto revisado:** `rama claude/settings-local-untrack` rev. 1, commit `f7284d4`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-09-04-gitignore-reglas-inertes-r1-adversarial-review.md` §1
- **Hallazgos:** 4 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** PR pendiente de número (commits `edb1ba7` y siguiente)

| # | Severidad | Veredicto | Dónde se remedia |
|---|---|---|---|
| H1 — `check-ignore` aplica también `info/exclude` y `core.excludesFile` | MEDIO | **confirmado** | `edb1ba7`: dos capas en `_ignorados` + test `test_una_exclusion_LOCAL_no_es_una_regla_inerte_del_repo` |
| H2 — `repo_lab` se come el `returncode` de `init` y de `add -f` | MEDIO | **confirmado** | `edb1ba7`: aislamiento acreditado por `samefile` **antes** de tocar ningún índice |
| H3 — `Path(REPO.anchor)` no significa «fuera de todo repositorio» | BAJO | **confirmado** | `edb1ba7`: `GIT_CEILING_DIRECTORIES` + precondición comprobada |
| H4 — el `*` de la excepción no cruza `/` | BAJO | **confirmado** | `edb1ba7`: `**` en las tres líneas + test `test_la_excepcion_alcanza_una_skill_anidada` |

**Las divergencias, razonadas:**

**H1 — remedié la frontera, no el ejemplo, y eso cambió el remedio.** El informe describe
`core.excludesFile` y `.git/info/exclude`. Pero de lo que son ejemplo es de otra cosa: **el
guard tiene que responder por las reglas que el repositorio REPARTE, no por las que esta
máquina aplica.** Enunciada así, la lista de fuentes a excluir deja de ser un catálogo que
alguien tendrá que ampliar —hoy dos, mañana la que git añada— y pasa a ser un predicado: la
fuente de la regla tiene que ser un `.gitignore` **trackeado**. Eso cubre además un caso que
el informe no menciona: un `.gitignore` local sin commitear. Es el corolario de `CLAUDE.md`
(«¿de qué frontera es esto un ejemplo?») aplicado antes de escribir el parche, y no después
de cuatro rondas.

**H1, y el hallazgo que produjo mi propia prueba de mutación:** al remediar puse *dos*
capas, y el mutante M6 —quitar la anulación de `core.excludesFile`— **sobrevivió**: la suite
sigue verde, porque el filtro por fuente ya descarta la regla global. O sea que la primera
capa **no sostiene la corrección**. La conservo, porque evita gastar un `-v` por cada
fichero que solo ignora una regla local (en una máquina con `*.md` global serían cientos de
subprocesos), pero **dejé de atribuirle la garantía**: el comentario del guard ahora dice
que es rendimiento y no garantía. Describir como activa una línea que no muerde es
exactamente la patología que este guard persigue, y la habría enviado dentro del propio
guard.

**H2 es el hallazgo caro y el revisor lo demostró ejecutando.** No es un `assert` que falte:
es que con el `init` roto **los cinco tests quedaban verdes** y las sondas se añadían con
`-f` al índice del repositorio padre. El guard escrito para detectar contaminación del
índice contaminaba uno de verdad, y callado. Ningún unitario lo ve; hay que romper el `init`
para verlo. Confirmado con la comparación que cierra el argumento: con el mismo `init` roto
y **sin** la comprobación, él obtuvo `5 passed`; con ella, el mutante M8 aborta en *setup*
con `ERROR` en los tres tests del laboratorio. Descarté además su hipótesis alternativa
—`user.name`/`user.email` ausentes— porque él mismo la midió irrelevante: `init` y `add` no
necesitan identidad mientras no haya commit.

**H4 lo remedié pese a que él mismo lo acota como limitación futura.** No existe hoy ningún
`logs/README.md` a esa profundidad —lo verifiqué: las cuatro carpetas están a un nivel—, así
que no rompe nada. Pero el coste de pasar `*` a `**` es una tecla y la propiedad correcta es
«el `logs/README.md` de una skill», no «de una skill que esté exactamente a un nivel».
Cerrar el ejemplo y no la propiedad es el modo de fallo que este proyecto lleva medido
cuatro veces.

**Y un defecto que introduje AL remediar,** cazado por el propio test que estaba escribiendo:
el filtro que lee las tres líneas de la excepción desde el `.gitignore` se tragaba la línea
de **comentario** que también menciona «skills» y «logs», y contaba cuatro. Es el quinto
caso registrado de introducir un defecto en la remediación.

**Sobre el mandato, para la próxima:** pedir el veredicto del set cerrado **desde el
mandato** funcionó — el informe lo trajo en su última línea y no hubo que hacer una segunda
llamada. La cláusula de higiene del directorio de trabajo también: el revisor declaró en su
primera línea el `_stdout.log` que encontró y dijo no haberlo leído. Esa cláusula nació de
un incidente de esta misma sesión: el primer directorio que elegí, `/c/t/rev1/`, **ya lo
estaba usando una sesión concurrente**, con su propio `INFORME.md` de otra ronda sobre otro
objeto dentro. Mi corrida lo iba a sobrescribir. Paré, lo salvé por copia con hash
verificado, y relancé en un directorio nuevo. **La lección operativa: el directorio de una
ronda tiene que llevar un nombre que no pueda colisionar**, porque el fallo silencioso
—archivar el informe de otro revisor como la voz del propio, con un digest internamente
coherente y falso— destruye justo la garantía que el acta existe para dar.
