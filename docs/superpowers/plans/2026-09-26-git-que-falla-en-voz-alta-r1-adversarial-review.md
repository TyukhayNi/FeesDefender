---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-26-git-que-falla-en-voz-alta.md
objeto_rev: "1"
commit: e7b408d
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: 34jx
sha256_informe: 5de221d61b23318cf93e5b718e3532c5a7dfc94f3ca1bfbcff4ba2f930e60ff0
adjudicado_en: docs/superpowers/plans/2026-09-26-git-que-falla-en-voz-alta.md §4
---

# Acta — R1 adversarial sobre «git que falla en voz alta»

Objeto: la pieza entera, `a703025` → `e7b408d` —el helper `tests/_git.py`, los tres guards
migrados, la sonda de `session_close`, el `pipefail` del paso de CI, los cuatro arneses y el plan—.

**Primera ronda sobre esta pieza, la única que le da la tabla de `CLAUDE.md`**: toca guards, que no
se eximen nunca, y no decide quién escribe sobre qué copia ni destruye datos. Modelo de la fila
«gobernanza que pueda hacer que la cobertura parezca presente estando ausente: un guard»,
`gpt-6-astra`·`medium`, por una frontera silenciosa y nombrada: un guard, la verja de cierre o el
escaneo de CI que dan verde sin haber mirado.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.4` (binario `13995fba801849b0`), sondeado `VIVO` con el mismo modelo a las 14:36, antes de montar el objeto |
| Modelo y esfuerzo | `gpt-6-astra` · `medium` — **releídos** de la cabecera del `_stdout.log` (sesión `01a0ddb8-c2f6-7b01-9b8c-a07297b6211e`) |
| Velocidad | `service_tier="default"` — **afirmada** desde el lanzador conservado (`C:\t\git-voz-alta-r1-1436-lanzador\_lanzar.ps1`) |
| Objeto | dos copias `git archive` (`base/` 1.424 ficheros, `head/` 1.427), dentro del workdir, sin `.git`; cotejadas contra los commits por `sha256` en LF |
| Duración | de 14:37:48 a 14:54:28; terminó con `exit=0` y ninguna línea de muerte en el log (vigía armado antes de lanzar) |
| `sha256` del informe | `5de221d61b23318cf93e5b718e3532c5a7dfc94f3ca1bfbcff4ba2f930e60ff0` |
| Veredicto | **NO-SHIP** |

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:34jx -->
Higiene de apertura: solo estaban `MANDATO.md`, `base/`, `head/` y `_stdout.log`; no había elementos ajenos.

# R1 — Git que falla en voz alta

Objeto: `base/` (`a703025acecfb08f3a489f2c298e4318db9c4d9c`) → `head/` (`e7b408d0af6eb795f898666a3a79f667b167d0c9`), según el anclaje del mandato. Las copias no contienen metadatos con los que autenticar esos commits. Revisión local, sin red, sobre el contenido entregado. Fecha de cierre comprobada en el sistema: 2026-09-26.

**La corrección cierra el caso original sin `.git`, pero no toda la propiedad.** Quedan una resolución parcial y silenciosa de la blocklist, un enumerador de guards sin validar, errores de lectura con códigos aparentemente válidos y consultas que fallan después de una sonda satisfactoria. La adjudicación de estos hallazgos corresponde al autor contra la fuente.

## Evidencia y reproducción común

Se generaron hashes SHA-256 de los bytes de **todos** los ficheros de ambos árboles antes y después: 1.424 en `base/`, 1.427 en `head/`. `hashes-apertura.json` y `hashes-cierre.json` **coinciden íntegramente**. SHA-256 de ambos manifiestos: `4138bbaea7a7124fbfdcbd6dcf827f70282b321f45f5c3e571bd8b48990d8f79`. No se normalizaron sus archivos antes de hashearlos; esto acredita conservación de los bytes recibidos, incluidos CRLF.

El diff real contiene los once ficheros de código/configuración indicados y el plan nuevo. `copia/` es una copia de `head/` inicializada y commiteada localmente; `copia-base/` y `copia-archive/` conservan el escenario sin `.git`. Las reproducciones crean laboratorios adicionales aquí. No se modificaron `base/` ni `head/`, ni se instaló nada en el venv. El intento de modificar un `.git` de un worktree **sintético** fue denegado; la reproducción de H-01 usa finalmente una inyección explícita del fallo de consulta, sin modificarlo. No se accedió al repositorio real para examinar su contenido.

Todas las órdenes siguientes se ejecutan desde este directorio, con esta preparación:

```powershell
$py = 'C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
$env:TEMP = Join-Path $PWD '_tmp'
$env:TMP = $env:TEMP
$env:LOCALAPPDATA = Join-Path $PWD '_perfil'
```

Los scripts `reproducir*.py`/`reproducir-migracion.ps1` quedan entregados junto con sus logs. Usan únicamente datos sintéticos. Git observado: `2.53.0.windows.2`.

| Ejecución | Resultado comprobado | Evidencia |
|---|---|---|
| Los seis módulos del §3 del mandato, copia con git, semilla 777 | 122 passed, 2 failed | `tests-777.log` |
| Los mismos, semilla 31337 | 122 passed, 2 failed | `tests-31337.log` |
| Gobernanza + basetemp de base, sin `.git`, semilla 777 | 48 passed | `tests-base-archive.log` |
| Gobernanza + basetemp de head, sin `.git`, semilla 777 | 45 passed, 3 failed por git | `tests-head-archive.log` |
| Mutante que descarta coincidencias; cuatro módulos de guards, semilla 777 | 77 passed; el mutante sobrevive | `repro-mutante-refs.log` |

Los dos fallos repetidos son `TestLaVerja.test_el_mensaje_sugiere_un_interprete_QUE_EXISTE` y `TestLaRutaQueSugiere.test_en_este_repo_encuentra_uno_que_existe`, en `test_session_close_no_pude_medir.py:137,161`. Presuponen un `.venv` descubrible dentro del checkout/principal; ejecutar con un intérprete externo no crea esa ruta en una copia archive inicializada. El fichero no cambia entre base y head. **No los atribuyo al diff ni los oculto como verdes**; tampoco fabriqué un ejecutable vacío para satisfacerlos. Los 18 casos nuevos pasan en ambas semillas.

## 1. ¿Está completo el inventario?

**No.** Se recorrieron `tests/`, `scripts/`, `core/`, `.github/` y `.pre-commit-config.yaml`, tanto invocaciones directas como llamadores de wrappers. Los índices de búsqueda están en `inventario-git.txt`, `inventario-llamadores.txt`, `inventario-ficheros-git.txt` e `inventario-subprocess.txt`. `rg` no estaba disponible; se utilizó `Select-String`.

### H-01 — El leak-guard calla cuando solo consigue una blocklist parcial

- **Severidad:** alta. **Coste del remedio:** acotado.
- **Dónde:** `head/scripts/precommit_leak_guard.py:123-128,205-218,390-401`; clasificación incorrecta en el plan, §1, párrafo «Lo que ya estaba bien».
- **Defecto:** `_resolver_principal` devuelve el motivo del fallo de git, pero `main()` solo lo comunica si la unión de términos está **vacía**. Si el worktree tiene cualquier término local, un fallo de `git worktree list` deja sin leer el principal, se escanea con una lista parcial y desaparece el aviso. No se exige que falle cerrado: falta incluso la declaración que promete el plan.
- **Reproducción:** `& $py reproducir.py leak`. Crea un repo y un worktree reales dentro del scratchpad, con `CANARIO_PRINCIPAL` en la lista del principal, `CANARIO_LOCAL` en la del worktree y un fichero que contiene el primero. Con git sano, `main` devuelve **1** y bloquea. Inyectando exclusivamente rc=128 en `git worktree list`, conserva `['CANARIO_LOCAL']`, registra internamente `git worktree list falló` y devuelve **0, stdout vacío, stderr vacío**. Los demás comandos git siguen ejecutándose realmente. Evidencia: `repro-leak.log`.
- **Afirmación contradicha:** plan §1: «Lo que ya estaba bien, comprobado: `scripts/precommit_leak_guard.py::_git` (declara el principal “no determinado”)». El docstring del guard, líneas 29-30, añade que el principal queda «no determinado» **«y se dice»**. Guardar el motivo en un objeto no lo comunica al usuario del hook.
- **Remedio:** distinguir explícitamente resolución completa, principal no aplicable y resolución fallida; declarar siempre esta última aunque haya términos locales. Si se elige bloquear, documentarlo como cambio de política. Añadir el test de lista local no vacía + fallo de consulta + término exclusivo del principal. Es un defecto preexistente que el inventario da erróneamente por cerrado; por eso pertenece al mandato de esta ronda.

### H-02 — Otro `ls-files` del mismo módulo sigue haciendo pasar un guard vacío

- **Severidad:** media. **Coste del remedio:** acotado.
- **Dónde:** `head/tests/test_gitignore_no_inerte.py:391-395,455-478`.
- **Defecto:** `_gitignores_trackeados()` usa el wrapper crudo `_git`, consume stdout sin validar `returncode` y alimenta el guard de comentarios al final de las reglas. Ante rc=128 devuelve `[]`; el bucle no examina ningún `.gitignore` y el test pasa. No está en el inventario ni declarado fuera.
- **Reproducción:** `& $py reproducir.py omitido`. Con un `.gitignore` sintético que contiene `build/ # comentario invalido`, el guard sale rojo con índice sano. Corrompiendo únicamente el índice del laboratorio, el mismo `ls-files` devuelve **128** y el guard pasa **verde**. Se repone el índice al terminar. Evidencia: `repro-omitido.log`.
- **Afirmación contradicha:** objetivo del plan: «que un guard […] que enumeran con `git` paren o lo declaren cuando `git` falla». La afirmación de haber recorrido las 26 llamadas no cubre este llamador del wrapper.
- **Remedio:** reutilizar una enumeración validada, conservando la separación NUL, y probar el guard final con el fallo de git y con una regla ofensora real. Revisar también los llamadores crudos de `_git` del módulo: `ignora()` en la línea 359 convierte cualquier rc distinto de 0 en falso. En ese test los controles de rutas que sí deben estar ignoradas impiden un verde ante fallo total, pero no distinguen un fallo selectivo en una consulta negativa.

### H-03 — El precheck PowerShell anuncia árbol limpio tras rc=128

- **Severidad:** baja. **Coste del remedio:** acotado.
- **Dónde:** `head/scripts/migrate_repo_local.ps1:40-47` (también consultas no validadas en 84-92 y 110).
- **Defecto:** decide por `$status` y no por `$LASTEXITCODE`. `$ErrorActionPreference = 'Stop'` no basta para convertir este código nativo en una excepción. El stderr se ve, pero el script continúa y lo contradice con `[OK] Git status limpio`.
- **Reproducción:** `pwsh -NoProfile -File ./reproducir-migracion.ps1`, y lo mismo con `powershell`. El script extrae y ejecuta **solo** el precheck de la copia, en `copia-archive/`; no ejecuta migración, instalación ni red. Confirmado tanto en PowerShell 7.6.6 como en Windows PowerShell 5.1: fatal de git, `[OK] Git status limpio`, código git 128. Logs `repro-migracion-pwsh.log` y `repro-migracion-ps51.log`.
- **Afirmación contradicha:** objetivo del plan, citado en H-02; la cabecera de este script también promete «Cada paso valida el estado previo antes de actuar».
- **Remedio:** capturar y comprobar inmediatamente el código nativo antes de interpretar stdout; para `remote get-url`, separar «no hay origin» de fallos generales. Añadirlo al inventario o declarar expresamente fuera este script histórico. Severidad limitada: la suite posterior es otra barrera y no he demostrado que la migración completa llegue a ejecutarse tras este fallo.

**Resto del inventario.** `limpieza_post_audit.run` valida el código por defecto; `core/email_atomize/entregas._git_commit` devuelve «desconocido». `core/codicert` y `_sondeo_crm._checkout_principal` tienen fallbacks de resolución de credenciales/configuración, no un verde de un guard; el segundo ni siquiera figuraba en la lista del plan. Los tests del plugin exigen contenidos/listas en sus comprobaciones relevantes y declaran `skip` si no pueden resolver el commit canónico. No se ejecutaron contra instalaciones personales. `.pre-commit-config.yaml` no contiene otra enumeración con git; mantiene `verbose: true`. Los casos de `session_close` y los arneses se detallan en §3 y §5. `check_skills` está declarado fuera, pero la afirmación de que queda cubierto por la sonda solo vale para fallo total, no para fallo de `status/show`.

**Observaciones aparte, con otras herramientas (preexistentes; no se suman como defectos del diff):**

- `scripts/health_check.py:104-118` cuenta cero errores y muestra tres marcas positivas aunque todos los comandos de versión devuelvan rc=42. Reproducción: `& $py reproducir.py health`; `repro-health.log`. Falta comprobar el código antes de `_ok`; stderr con un mensaje de error acaba impreso como resultado positivo.
- Los `_corre` de `_mutantes_accion_6a.py:173-180`, `_mutantes_mejoras_136.py:148-155` y `_mutantes_renovacion_mutex.py:97-104` buscan líneas `FAILED` sin validar el código de pytest. Reproducción con rc=4 y stderr de uso: `& $py reproducir.py pytest-arneses`; los tres devuelven `set()` y el llamador lo interpreta como baseline verde. No acredita por sí solo una campaña entera falsamente verde, porque los mutantes esperados pueden declararse supervivientes después. Conviene separar corrida inválida de conjunto vacío, como ya hacen los arneses más robustos. Evidencia: `repro-pytest-arneses.log`.

## 2. Los códigos válidos

Los conjuntos elegidos admiten las respuestas normales correctas. **El problema es que el código no siempre basta para acreditar que la consulta fue completa.**

| Llamada migrada | Códigos aceptados | Dictamen |
|---|---|---|
| `_md_trackeados`: `ls-files *.md` | 0 | Correcto para fallo comunicado por código; no vi un negativo legítimo que necesite otro rc. |
| Basetemp: `ls-files` | 0 | Correcto. |
| Referencias heredadas: `grep -l -E` | 0, 1 | Necesarios para match/no match, pero insuficientes: H-04. |
| `_regla`: `check-ignore --no-index -v` | 0, 1 | Necesarios; `-v` puede informar también una negación. El módulo ya separa atribución de decisión. Insuficientes ante errores de lectura: H-04. |
| Tres arneses: `status --porcelain`, `check=True` | 0 | Correcto: árbol sucio cambia stdout, no requiere rc distinto de 0. |
| `_mutantes_propiedades_utils._preflight` | 0 | Correcto: devuelve motivo ante otro rc. |
| Sonda: `rev-parse --git-dir` | 0 | Correcto para esa consulta, no acredita otras: H-05. |

### H-04 — `grep` y `check-ignore` pueden fallar al leer y aun devolver 0/1

- **Severidad:** media. **Coste del remedio:** acotado.
- **Dónde:** `head/tests/_git.py:20-32`; `head/tests/test_docs_gobernanza.py:41-49`; `head/tests/test_gitignore_no_inerte.py:88-100,140-150`.
- **Defecto:** stderr solo se examina cuando el código es inválido. Git puede emitir errores de acceso, omitir el fichero y conservar un código de respuesta normal. No es un error inventado por un doble: se reprodujo con Git real y un handle exclusivo de Windows.
- **Reproducción:** `& $py reproducir.py grep` y `& $py reproducir.py ignore`.
  - Un fichero versionado con `docs/PLAN_PROHIBIDO.md` hace fallar el guard. Bloquear su lectura produce rc=1, stdout vacío y `error: failed to stat … Permission denied`; el mismo guard queda **verde**. Añadiendo un match en el fichero exento `test_docs_gobernanza.py`, git devuelve **0** con el mismo error; también queda verde. Por tanto, vigilar solo stderr cuando rc=1 tampoco bastaría.
  - Un `.gitignore` versionado que ignora un fichero forzadamente trackeado produce un ofensor con lectura sana. Con el `.gitignore` bloqueado, `check-ignore` devuelve **1**, stdout vacío y `warning: unable to access '.gitignore': Permission denied`; `_regla` devuelve `''` y `_ignorados` devuelve `[]`.
- **Afirmación contradicha:** docstring de `tests/_git.py`: «si el comando falla, el guard PARA — nunca lee el vacío como respuesta»; objetivo del plan. Admitir 1 es correcto, equiparar todos los 1 con una lectura completa no lo es.
- **Remedio:** conservar los códigos normales y validar también los diagnósticos de lectura. Para estos guards puede fallarse conservadoramente ante stderr no vacío, o clasificarse de forma explícita qué advertencias inocuas se admiten; nunca ignorar `failed to stat`/`unable to access`. Aplicarlo tanto al helper como a las dos consultas de ignore. Añadir controles con el mismo fichero ofensor antes y durante el fallo de lectura. Logs: `repro-grep.log`, `repro-ignore.log`.

## 3. La sonda de `session_close`

Preguntar una vez es útil para el fallo total, pero **no sustituye el estado de cada consulta**. No hace falta derribar todos los avisos por una rama desaparecida; sí hace falta conservar que esa rama o comprobación no se pudo medir.

### H-05 — Una sonda verde permite decisiones y avisos basados en consultas fallidas

- **Severidad:** media. **Coste del remedio:** estructural, porque afecta al contrato de resultados de `_git_lines` y a sus consumidores.
- **Dónde:** `head/scripts/session_close.py:55-70,88-105,108-124,133-150,153-190,412-426,476-479,905-918`; `head/scripts/check_skills.py:67-89` para el aviso envuelto.
- **Reproducción:** `& $py reproducir.py sonda`.
  - Repo sintético con cambio staged en `core/anon/motor.py` y último commit ajeno a anon: sonda `None`, modo `(True, 'core/anon/ tocado')`. Se corrompe el índice: `status` falla con 128, **la sonda sigue devolviendo `None`** y el modo pasa a `(False, '')`. Es exactamente la decisión de omitir los lentos sin haber medido ese cambio.
  - Corrompiendo un objeto de commit, `rev-parse --git-dir` sigue funcionando y `log` falla con 128; el aviso imprime **«Sin specs/plans nuevos»**, sin «no comprobado».
  - Un repo con commits y sin `origin/main` produce **«sin commits sin publicar. Nada que llevar al archivo»** porque `rev-list` falla y se convierte en cero. Este último caso es un límite deliberado del diseño, pero ilustra por qué «no tumbar todas las ramas» no exige afirmar cero.
- **Afirmación contradicha:** objetivo del plan y la explicación de `_git_responde`: «`_git_lines` devuelve `[]` ante cualquier fallo, y para una consulta suelta es lo correcto». No lo es para `status`, `show`, `log` o enumeración de ramas. Una consulta fallida también puede generar una falsa rama fantasma en el aviso de PLAN.
- **Remedio:** conservar el error de la consulta y su diagnóstico. En selección de lentos, desconocido debe dar COMPLETO; en cada aviso, desconocido debe quedar declarado. Si una rama no tiene referencia remota, continuar con las demás y declarar esa rama no comprobada; no presentar el error genérico 128 como cantidad cero. La sonda puede mantenerse como preflight, sin utilizarla como certificado para todo el cierre.
- **Límite de la reproducción:** el índice persistentemente corrupto hará fallar otros guards de la suite, por lo que **no afirmo que esa ejecución completa de `main` termine verde**. Lo comprobado es la selección errónea de modo y los avisos falsos. Una consulta transitoria o un fallo de `log` no necesita romper los `ls-files` de la suite. Evidencia: `repro-sonda.log`.

**Lo correcto del orden actual:** si faltan dependencias, `main()` sale con código 2 antes de consultar git o ejecutar pytest, diciendo que no ha medido. No rompe la propiedad: no da verde ni finge haber corrido los lentos. Con fallo total de git y dependencias presentes, seleccionar `--runslow` es conservador y correcto. Si pytest falla, se sale con 1 antes de los avisos, pero el fallo de git ya se imprimió en 911-913; tampoco hay silencio. El test integral nuevo puentea pytest para alcanzar y comprobar los cinco avisos, por lo que no debe confundirse con una ejecución íntegra de la suite sin git.

## 4. CI

**Sí: para el fallo no cero del productor de esta tubería, `pipefail` basta.** Se ejecutó el bloque `run` extraído del workflow de la copia bajo Git Bash con `-e`, con dobles controlados del productor y del escáner. `reproducir-ci.py` y `repro-ci.log` conservan el experimento.

| Caso | Código del paso | ¿Se invoca el escáner? |
|---|---:|---|
| git devuelve 128, sin `pipefail` | 0 | No |
| git devuelve 128, bloque de head | 128 | No |
| git devuelve 0 y lista vacía | 0 | No |
| git real, índice ausente en laboratorio con fichero preparado | 0 | No |
| Lista no vacía, `python` ausente | 127 | No; `xargs` declara el error |
| Lista no vacía, escáner devuelve 1 | 123 | Sí |
| Lista no vacía, escáner devuelve 0 | 0 | Sí |

Una lista vacía con rc=0 **no queda protegida**: `xargs -r` salta incluso la comprobación de existencia del intérprete. Para exigir escaneo positivo, hace falta validar una lista no vacía y consumir esa misma lista, o exigir un recuento del escáner. El `checkout` normal de este repo suministra un índice poblado; no he demostrado que el workflow intacto lo vacíe por sí mismo. Es un límite distinto del fallo no cero que este cambio pretende corregir, no otro fallo probado de `pipefail`.

El workflow solo contiene este job, utiliza `ubuntu-latest`, no declara otro shell ni `continue-on-error` y el pipeline es el último comando. La semántica esperada del runner Linux con shell no especificado es `bash -e`; el `set -o pipefail` explícito aporta lo que faltaba. Si solo hubiese `sh` sin soporte de `pipefail`, ese `set` fallaría, no produciría verde. No se ejecutó GitHub Actions ni se comprobó el runner remoto: esto es análisis del YAML y reproducción local del shell, no una certificación del servicio.

Sin `PII_BLOCKLIST`, el bloque sale explícitamente con 1 antes del escaneo. Un valor no vacío pero sin términos utilizables puede llegar al guard, que declara blocklist vacía y continúa con rutas/formas: limitación ya declarada del guard, distinta de enumerar cero ficheros. El job tampoco acredita por sí solo que branch protection exija este check; su propia cabecera lo advierte.

La debilidad del test que protege `pipefail` se incluye en H-06.

## 5. Los arneses

**Los cuatro cambios son correctos para el fallo no cero de `git status`.** Se ejercitó el preflight sobre la copia sin `.git`, sin permitir que llegara a la primera mutación:

- `_mutantes_accion_6a.py:189`, `_mutantes_mejoras_136.py:164`, `_mutantes_renovacion_mutex.py:113`: `CalledProcessError`, rc=128. Paran antes del baseline y de modificar ficheros.
- `_mutantes_propiedades_utils.py:352-355`: devuelve un motivo con rc y stderr; `main`, en 409-412, lo imprime y devuelve 2 antes de medir o mutar.
- El quinto arnés que consulta git, `_mutantes_particion_124.py:132-136`, **ya estaba protegido**: imprime «NO SE PUDO CONSULTAR GIT» y devuelve 2.

Reproducción: `& $py reproducir.py arneses`; `repro-arneses.log`. Los `checkout` de restauración de los tres primeros ya llevan `check=True`. Un ejecutable git ausente también impide continuar por excepción. Los restantes seis `_mutantes_*.py` no consultan git: no encontré otro preflight git con esta propiedad.

La Task 4 del plan dice «`check=True` […] de los cinco arneses». Es una descripción imprecisa: tres incorporan `check=True`, uno añade validación manual y el quinto ya validaba antes. La propiedad queda cubierta en los cinco; no convierto esa imprecisión documental en un defecto funcional. Las observaciones sobre fallos de **pytest** están separadas en §1 y no refutan esta corrección de git.

## 6. ¿Los tests prueban lo que dicen?

Los 18 tests nuevos sí detectan el caso rc=128 uniforme, el ejecutable ausente en el helper, parte de los códigos normales, la sonda negativa, la selección de lentos, los envoltorios de avisos y la presencia textual de `pipefail`. **Eso no prueba toda la propiedad**, como muestran H-01, H-02, H-04 y H-05.

### H-06 — Sobreviven pérdidas completas de detección y un `pipefail` desactivado

- **Severidad:** baja. **Coste del remedio:** acotado. Es un hueco de protección frente a regresiones; el mutante no está en head.
- **Dónde:** `head/tests/test_guard_git_falla_en_voz_alta.py:63-73,82-87,161-174`; función extraída en `head/tests/test_docs_gobernanza.py:41-49`.
- **Reproducciones ejecutadas:**
  1. `& $py reproducir-mutante-refs.py` cambia, solo en `copia/`, el retorno de `_refs_a_docs_plan_legacy` por `[]`, **manteniendo la llamada a git y la validación del código**. Los cuatro módulos de guards, incluidos todos los casos nuevos, producen **77 passed, rc=0**. El script restaura los bytes originales en `finally`; `git diff --exit-code` confirmó la reposición. Los tests de fallo siguen rojos donde deben porque aún se ejecuta git; el supuesto control positivo solo exige `isinstance(..., list)`.
  2. `& $py reproducir-ci.py` inserta `set +o pipefail` después de `set -o pipefail` en un YAML de laboratorio. Invoca el **test del autor**, que pasa; ejecuta el bloque alterado, que devuelve **0** con git=128 y cero invocaciones del escáner. La regex verifica que el texto aparece, no que gobierne la tubería.
- **Afirmación contradicha:** Task 1 del plan: los helpers «devuelven algo con el git real (control positivo)»; Task 3: «el paso de leak-scan corre con `set -o pipefail` antes de la tubería». Los controles actuales permiten perder esa conducta conservando su apariencia.
- **Remedio:** comprobar un ofensor sintético mediante el guard final de referencias, además de la excepción por git; probar el bloque de shell efectivo con productor fallido y consumidor espía, incluyendo el control sano. No basta exigir un número de matches contra el corpus actual, pues puede contener solo las excepciones permitidas.

**Sobre el 12/12 declarado:** el arnés no está entregado. El §2 del plan enumera tareas y propiedades, pero no especifica doce transformaciones reproducibles y sus tests asesinos. No puedo certificar ni refutar aquellas doce ejecuciones concretas. Mis dos mutantes son independientes: acreditan límites del conjunto de tests, no que el conteo histórico sea falso. Tampoco extrapolo el resultado de los 77 tests a toda la suite de 6.501.

## 7. Todo lo nuevo, en fresco

Se revisó el diff completo y el código consumidor. No se encontraron otros defectos introducidos fuera de los límites del helper/sonda y la cobertura ya descritos. La migración conserva las aserciones originales y los filtros de excepciones; el helper captura `OSError` y conserva stderr y rc en los fallos que sí detecta. La adición de `Callable` y los envoltorios no cambia el carácter no bloqueante de los avisos ni retrasa la salida por dependencias ausentes.

Los hallazgos del inventario son defectos **preexistentes no cubiertos o mal clasificados por esta pieza**, no regresiones atribuidas falsamente a sus líneas nuevas. No propongo que esta ronda implemente las observaciones ajenas a git; sí que se corrija la afirmación de cobertura y se remedien o delimiten explícitamente los huecos del contrato revisado.

## Lo que intenté refutar y NO pude

- El cierre del escenario original sin `.git`: reproduje los 48 verdes de base y los tres rojos pertinentes de head, con 45 verdes independientes de git.
- El uso de códigos normales 0/1: no encontré un código adicional de respuesta normal que deba admitirse en las llamadas migradas. El fallo está en diagnósticos que acompañan a códigos ya admitidos, no en exigir rc=0 a ciegas.
- La preservación de las aserciones de gobernanza y basetemp, y la separación entre decisión y atribución en el test de gitignore.
- La parada de los cinco preflights de arneses que consultan git ante rc=128.
- La propagación del fallo no cero del productor de CI, del intérprete ausente con entrada no vacía y del fallo del consumidor.
- El preflight de dependencias y el modo COMPLETO ante fallo total de git; los tests correspondientes pasan, salvo las dos precondiciones de ubicación del venv ya explicadas.
- La no mutación del objeto: hashes de los 2.851 ficheros coincidentes al cierre.

## SIN VERIFICAR

- La suite entera de 6.501 casos y sus 96 omisiones declaradas por el autor. Se ejecutaron los seis módulos ordenados con ambas semillas y los experimentos adicionales descritos; no se presenta esa cobertura parcial como suite entera.
- Las doce ejecuciones originales de mutación: falta su arnés y la lista exacta de transformaciones.
- GitHub Actions, acciones descargadas, configuración efectiva del runner, secretos y branch protection: excluidos por la prohibición de red. Bash local verifica la tubería, no esos servicios.
- La migración completa, campañas completas de los arneses y un `main()` real que ejecute todos los lentos: no se ejecutaron. Se aislaron las decisiones y los preflights sin instalaciones, red ni acceso a expedientes reales.
- Las instalaciones personales del plugin y las rutas de credenciales reales: no se inspeccionaron. Su revisión aquí es estática.
- El objeto no desbordó el esfuerzo de esta ronda. Las limitaciones anteriores son de material/entorno y alcance ejecutado, no cobertura presupuesta.

NO-SHIP
<!-- informe-literal:fin:34jx -->

## 2. Evidencia verificada por mí contra la fuente

**El informe es el del revisor, y está terminado.** `INFORME.md` se escribió a las 14:54:20 y el
lanzador registró la salida de `exec` a las 14:54:28: el fichero no podía seguir escribiéndose. Su
`sha256` canonicalizado y el que el revisor declaró en su mensaje final son **el mismo**
(`5de221d61b23318c…`); el fichero ya venía en LF con un solo salto final, así que la cadena se
verifica contra su salida y no solo contra sí misma.

**El objeto es el commit.** Cinco ficheros de `head/` —`tests/_git.py`, `scripts/session_close.py`,
el workflow de `leak-scan`, `tests/test_guard_git_falla_en_voz_alta.py` y
`tests/test_gitignore_no_inerte.py`— coinciden, quitando los CR de `git archive`, con
`git show e7b408d:<fichero>`; y tres de `base/` —`scripts/session_close.py`,
`tests/test_docs_gobernanza.py` y `scripts/precommit_leak_guard.py`—, con `a703025`. Las copias
son posteriores al saneado de PII del 2026-09-26: el revisor no ha tenido delante datos de
terceros.

**Sus reproducciones, contrastadas contra la fuente y no contra el informe.** Leí sus logs
(`repro-leak`, `repro-grep`, `repro-ignore`, `repro-omitido`, `repro-sonda`, `repro-ci`) y cada uno
dice lo que el informe afirma. Y fui más allá del log en tres:

- **H-04, con git de verdad en mis tests:** bloqueando en exclusiva el fichero ofensor, el guard de
  referencias devolvía `[]` antes del remedio (rojo por `DID NOT RAISE`); con el `.gitignore`
  bloqueado, la decisión perdía el fichero trackeado e ignorado.
- **H-06, al ejecutar el paso de CI:** además del `pipefail`, la **lista vacía con código 0** daba
  verde, también con git real sin índice —lo que el revisor midió y dejó como límite distinto—, y
  eso cambió el remedio del paso.
- **H-03, en PowerShell 7.6 y 5.1:** los tres bloques de consulta a git del script, extraídos y
  ejecutados en un directorio sin repo, paran con `[ERR]` tras el remedio; en un repo sin remoto,
  el 2 se lee como respuesta y el script sigue.

**Su `reproducir.py`, contra el árbol remediado.** Lo copié a mi scratchpad cambiando **una línea**
—de dónde importa— y corrí sus cinco casos de git: **ninguno da ya verde ni calla**. La lista
parcial se declara (con `1 término(s)` y el motivo); `grep` con el fichero bloqueado para, con código
1 y con 0; el `check-ignore` con el `.gitignore` bloqueado lanza; el guard de comentarios para con el
índice roto; y `session_close` corre los lentos con el índice roto, nombra `main` como «rama NO
comprobada» sin `origin/main` y declara no comprobada la trazabilidad con el objeto corrupto.
**Correrlo destapó además un defecto de mi propio remedio**, antes de commitear: la raíz por
defecto quedaba ligada al definir la función y su parche de `ROOT` habría mirado el repo real. Está
en el §4 del plan.

**Sus dos mutantes (H-06), en mi arnés.** El de las referencias que devuelven `[]` es el 27; el del
`pipefail` desactivado ya no se puede aplicar —no queda tubería—, y su equivalente es el 44, la
vuelta a la tubería sin `pipefail`. Los dos mueren, con los otros 44: **46 de 46**.

**Lo que declaró sin verificar**, contrastado donde se pudo: la suite entera con las dos semillas
la corrí yo (cifras en el §3 del plan); el arnés de los 12 mutantes del autor está ahora en el de
46, con sus anclas al día; GitHub Actions no se puede ejecutar aquí, y el test del paso lo emula
con `bash -e`, que es como GitHub corre un `run:` sin `shell:`.

**Cobertura de la remediación: AUSENTE.** Ningún revisor ha mirado el remedio. La tabla de
`CLAUDE.md` da una ronda a esta pieza y ya la tuvo; una segunda solo la autoriza Nikolai.
