---
tipo: revision-adversarial
objeto: "diff 3ca97ee..0f8a373 — «leak-guard: la blocklist se resuelve también desde el checkout principal, y su ausencia se declara» (MEJORAS #161, PLAN fila #20)"
objeto_rev: "1"
commit: "0f8a373"
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: p9vx
sha256_informe: b03bfd488971380488d6c1ea0b97df8ef65fc66d49155862984bd60381d754b3
adjudicado_en: docs/superpowers/plans/2026-09-05-mejoras-161-blocklist-desde-la-raiz-comun.md §4
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1 sobre el DIFF.** El §1 conserva la voz del revisor sin una
> coma cambiada; el §2 es la evidencia que verifiqué por mi cuenta al adjudicar.
>
> **La adjudicación NO está aquí:** va embebida en
> `docs/superpowers/plans/2026-09-05-mejoras-161-blocklist-desde-la-raiz-comun.md` §4, que es el
> documento que la decisión modificó. Esta acta es el archivo de la voz del revisor, no un segundo
> hogar de la decisión.
>
> **Una ronda, por radio de daño** (`CLAUDE.md` §«Cuántas rondas»): la pieza es una guarda de
> lectura, no decide quién escribe sobre qué copia ni puede destruir datos de cliente. **El diff
> REMEDIADO (`e635e83`) no se ha vuelto a revisar**, y se dice; lo que sí se hizo, y consta en el
> §2, es reproducir los contraejemplos concretos del revisor contra el código remediado.
>
> **Objeto:** dos copias externas de `3ca97ee` (base) y `0f8a373` (head), montadas con
> `git archive` fuera del repo, más el parche entre ambas. El revisor declaró que no acredita la
> genealogía —sus copias no tienen `.git`— y verificó contenido y hashes, que es lo correcto.
> Codex CLI `0.153.0-alpha.5`, modelo `gpt-6-astra`, ~123.000 tokens, 17:33–17:40. El veredicto
> vino en la última línea del informe, del set cerrado del guard G9, pedido así desde el mandato.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:p9vx -->

Higiene: CONFORME. Al abrir, `.` contenía exclusivamente `MANDATO.md` (última modificación: 2026-09-05 17:32:53, hora local); no había otros ficheros que excluir de lectura.

# R1 — DIFF de MEJORAS #161

## 1. Custodia y alcance

Revisión de contenido de los archivos externos `../base/` y `../head/`, identificados por el mandato como `3ca97ee` y `0f8a373`. Ninguno contiene `.git`: **no acredito genealogía ni correspondencia criptográfica con esos commits**. El contraste completo de archivos encontró exactamente tres modificaciones, sin altas ni bajas: los tres ficheros enumerados en el mandato. Se leyó el parche, pero las conclusiones se contrastaron con `head/`.

SHA-256 **al abrir**, antes de leer el código:

| Fichero de `head/` | SHA-256 |
|---|---|
| `scripts/precommit_leak_guard.py` | `9f8b241c5b71c3432fe15a4e5e5f8d4eeede2b8a92723968ca95d5da45473c2c` |
| `tests/test_precommit_leak_guard.py` | `4e93f3d948761a9c62134555ea0801a92035b5dbe62c2f387e32bed4a91a4869` |

Toda ejecución del objeto se hizo en `./objeto/`, copia completa de `head/`, o en laboratorios sintéticos dentro de este workdir. Las mutaciones se limitaron a esa copia y se restauraron. No se escribió en `base/` ni en `head/`. La autorización específica del mandato para ejecutar en una copia y usar temporales relativos prevalece sobre las instrucciones generales del repositorio acerca del directorio de ejecución. No hubo delegación.

## 2. Resumen en tres líneas

El worktree convencional recupera la unión y ambos mutantes mueren, pero P1 falla con metadatos Git separados y submódulos.
P2 no llega al usuario del hook normal: pre-commit oculta el aviso cuando devuelve 0; además, dos cargas pueden producir un verde silencioso sin escaneo por valor.
Hay ocho hallazgos reproducidos: dos ALTO, tres MEDIO y tres BAJO; los dos últimos son contradicciones documentales preexistentes, no regresiones del diff.

## 3. Hallazgos

Las ubicaciones siguientes son líneas de `head/`. Los scripts y logs citados están junto a este informe; usan únicamente valores sintéticos. Los scripts de preparación crean directorios nuevos: para repetirlos completos, usar otro workdir limpio con la misma estructura, sin borrar los laboratorios custodiados.

### H-01 — ALTO — El aviso de ausencia queda oculto en pre-commit y pre-push

**Ubicación:** `scripts/precommit_leak_guard.py:311`, impresión en 313 y retorno satisfactorio en 325–326; integración en `.pre-commit-config.yaml:31` y siguientes, sin `verbose: true`.

**Reproducción:** `python review_checks.py precommit`. Crea un repo temporal con el guard copiado y la sección `repo: local` exacta de la configuración; excluye los hooks remotos ajenos a la prueba. Sin blocklist, ejecuta `python -m pre_commit run leak-guard --files nota.md --hook-stage pre-commit`, y lo repite para `pre-push`, con y sin `-v`.

**Esperado:** el usuario vea que la comprobación por valor no se ejecutó, conservando el código 0 previsto por el diseño.

**Observado:** en ambos stages, sin `-v`, código 0 y únicamente `leak-guard (...)...Passed`; STDERR vacío. Con `-v`, aparece el aviso completo. Evidencia: `precommit.log`. Pre-commit instalado: 4.6.1. Se leyó su `pre_commit/commands/run.py`: `_run_single_hook` solo imprime la salida bajo `verbose or hook.verbose or retcode or files_modified`. También lo declara la [documentación oficial de verbose](https://pre-commit.com/#hooks-verbose).

El test con `capsys` acredita la impresión directa, pero no esta frontera de integración. No se propone cambiar la decisión explícita de no fallar cerrado: la visibilidad del aviso se puede corregir independientemente.

### H-02 — ALTO — El padre de los metadatos Git no identifica siempre el checkout principal

**Ubicación:** `scripts/precommit_leak_guard.py:103`; afirmación incorrecta del docstring en 79–80.

**Reproducción:** `python review_checks.py matrix`, casos `gitfile-separate`, `separate-wt`, `submodule` y `submodule-wt`. El script ejecuta `git init --separate-git-dir <lab>/storage/metadata` en `<lab>/separate`, guarda `Termino Separate` en la blocklist de ese checkout y crea un worktree. Guarda también `Lista Ajena` en `<lab>/storage/data/_config/pii_blocklist.txt`. En el worktree, `nota.md` contiene `Termino Separate`.

**Esperado:** recuperar `Termino Separate` del checkout principal y bloquear; no incorporar una lista de la carpeta contenedora de metadatos como si fuera otro checkout.

**Observado:** `--git-common-dir` devuelve `.../storage/metadata`; `_raiz_comun` devuelve `.../storage`. El worktree carga únicamente `Lista Ajena`; `main` devuelve 0 y STDERR vacío. En un submódulo real, Git devuelve `.../super/.git/modules/modulo`; el código toma `.../super/.git/modules`. Un worktree del submódulo pierde así su lista principal. Evidencia: `matrix.log`.

En un bare, Git devuelve `.` y el código incorpora su carpeta padre, que tampoco es un checkout. La [documentación de rev-parse](https://git-scm.com/docs/git-rev-parse#Documentation/git-rev-parse.txt---git-common-dir) describe un directorio de metadatos; no garantiza que su padre sea el árbol de trabajo. El fallo no afecta al layout convencional `principal/.git`, que sí se reprodujo correctamente.

### H-03 — MEDIO — Dos cargas independientes permiten omitir el escaneo sin emitir el aviso

**Ubicación:** `scripts/precommit_leak_guard.py:311` y 315; segunda carga en `escanear`, línea 281.

**Reproducción:** `python final_checks.py`, caso `first-load-success-second-timeout`. Repo y worktree reales; solo el principal contiene `Termino Observable`, que aparece en la nota del worktree. La primera llamada a `subprocess.run` ejecuta Git real y obtiene la raíz. Se inyecta `subprocess.TimeoutExpired(..., 10)` exclusivamente en la segunda llamada; no se sustituye `cargar_blocklist`, `escanear` ni `main`.

**Esperado:** escanear con la lista ya obtenida, o declarar la imposibilidad de ejecutar esa comprobación.

**Observado:** la primera carga evita el aviso; la segunda devuelve lista vacía porque `_raiz_comun` absorbe la excepción. `main` devuelve 0, STDERR vacío y se registran dos consultas. Evidencia: `final_checks.log`. Es una prueba determinista de fallo transitorio inyectado, no una afirmación de haber observado un timeout natural de Git.

El aviso y la comprobación necesitan describir la misma carga. Volver a resolver Git para construir las rutas del aviso añade una tercera observación independiente cuando la lista está vacía.

### H-04 — BAJO — El remedio afirma que el principal carece de lista cuando no pudo consultarlo

**Ubicación:** `scripts/precommit_leak_guard.py:171`–172, en relación con 96–99.

**Reproducción:** `python extra_checks.py`, caso `invalid-env-empty-false-remedy`: worktree sin términos locales y principal con blocklist válida; `GIT_DIR` apunta a un directorio inexistente. Git real devuelve 128. También `python final_checks.py`, caso `all-terms-short-main-file-exists`, mantiene un fichero existente en el principal con `Ana` y `Li`.

**Esperado:** distinguir falta de términos utilizables, fallo de resolución y ausencia de ficheros; no afirmar una causa que no se comprobó.

**Observado:** el aviso asegura que «el checkout principal tampoco la tiene». En la primera reproducción sí la tiene, pero no fue localizado; en la segunda existe, pero todos sus términos fueron descartados por `_TERM_MIN`. Evidencias: `extra.log` y `final_checks.log`. El encabezado «blocklist VACÍA» es correcto para la lista resultante; la explicación causal no lo es.

### H-05 — MEDIO — Los tests nuevos heredan firma y configuración global de Git

**Ubicación:** `tests/test_precommit_leak_guard.py:106`–124, especialmente el commit de la fixture en 124.

**Reproducción:** ejecución sin aislar Git, registrada en `suite_retry.log`: los cinco tests que usan `repo_con_worktree` dan error al crear el commit. Reejecutar ese `git commit -q -m init` mostró `fatal: failed to write commit object`, por firma global activada sin clave privada utilizable. `python run_suites.py` incluye una segunda reproducción independiente con `GIT_CONFIG_COUNT`, `commit.gpgsign=true` y un programa de firma sintético inexistente: `suite_signing.log`, un error en setup.

**Esperado:** fabricar el repo sintético sin depender de claves de firma, hooks o configuración global del usuario.

**Observado:** configurar `user.name` y `user.email` no neutraliza la firma heredada. Con `GIT_CONFIG_GLOBAL` apuntando a un fichero vacío y `GIT_CONFIG_NOSYSTEM=1`, los mismos tests pasan. La prueba de usuario no configurado quedó cubierta por esa ejecución aislada: las identidades locales de la fixture sí bastan para ese aspecto.

### H-06 — MEDIO — Los tests «fuera de Git» no aíslan la búsqueda ascendente de repositorios

**Ubicación:** `tests/test_precommit_leak_guard.py:145`–149 y 172–178; afecta también al test anterior de línea 82.

**Reproducción:** `python extra_checks.py` ejecuta el módulo completo con `--basetemp="../lab/wt ñ con espacios/pytest_nested"`, dentro de un worktree real con lista en su principal. No modifica los tests. Git global y de sistema están aislados.

**Esperado:** las pruebas que requieren ausencia de repositorio/lista construyan realmente ese estado y mantengan su resultado independientemente de la ubicación del temporal.

**Observado:** 3 fallos y 14 aprobados: `test_sin_blocklist_solo_rutas`, `test_fuera_de_git_solo_la_raiz_dada` y `test_sin_blocklist_en_ninguna_raiz_main_lo_declara`. La carpeta `suelto` pertenece al repositorio ancestro; el guard descubre su principal y su lista. Evidencia: `suite_nested.log`. La conducta de producción es coherente con la búsqueda Git; lo defectuoso es la precondición de las pruebas. Es relevante para temporales relativos dentro del árbol, como los usados en este mandato; no implica que falle el temporal predeterminado situado fuera de todo repo.

### H-07 — BAJO — El docstring promete bloqueo de NIF societario que el código excluye

**Ubicación:** `scripts/precommit_leak_guard.py:237`.

**Reproducción:** `python review_checks.py matrix`, caso `nif-docstring`: `nota.md` contiene `Empresa B65824054`; `escanear_formas(['nota.md'], repo)` devuelve `([], [])`. El test existente `test_nif_empresa_no_bloquea` pasa.

**Esperado:** documentación concordante con los tipos que efectivamente bloquean: DNI, NIE e IBAN; excluir expresamente el NIF/CIF societario de la promesa genérica.

**Observado:** el docstring enumera `DNI/NIE/NIF/IBAN`, mientras `_patrones_forma` excluye el NIF/CIF de empresa deliberadamente. **Preexistente en base**, comprobado por igualdad AST de la función. No es motivo independiente para frenar este diff; se registra porque el mandato exige señalar protección afirmada sin implementación.

### H-08 — BAJO — El mensaje recomienda una exención que no funciona para bloqueos por valor

**Ubicación:** `scripts/precommit_leak_guard.py:332`; escaneo por valor en 280–304.

**Reproducción:** `python review_checks.py matrix`, caso `allow-value-existing`: blocklist sintética `Termino Sintetico`; nota `Termino Sintetico # leak-guard:allow`; invocar `main`.

**Esperado:** limitar el remedio de la anotación a bloqueos por forma, o describir correctamente cómo se trata una coincidencia sintética por valor.

**Observado:** devuelve 1 por coincidencia de valor y vuelve a recomendar añadir la anotación ya presente. `escanear` no aplica `_ALLOW`; solo lo hace `escanear_formas`. Evidencia: `matrix.log`. **Preexistente en base**, no regresión del diff; se registra como contradicción del mensaje, sin pedir que se debilite la comprobación por valor.

## 4. Contraste de las propiedades

### P1 — REFUTADA en el alcance solicitado

Confirmada para checkout principal y worktrees convencionales: unión real, sin sustituir la lista principal por la local, sin duplicar la raíz principal. Confirmada con espacios, `ñ`, `core.fscache` activado/desactivado y junctions sencillas. Refutada como identificación general del checkout principal por H-02. El entorno Git también puede redirigirla a otro repositorio: se ejecutaron `GIT_DIR` y `GIT_COMMON_DIR` apuntando a otro `.git`, y se incorporaron sus términos. No se presenta esto como fallo de Git: es la consecuencia de heredar ese contexto sin validar qué checkout se pretende consultar.

Sin ejecutable Git, fuera de repositorio y con retorno 128 no rompe: se reproducen el retorno `None` y la carga local. Esa tolerancia no acredita haber consultado la raíz principal.

### P2 — REFUTADA como declaración efectiva del hook

La impresión directa sí está confirmada en el caso estable con ficheros que escanear: con las cuatro rutas ausentes se obtiene código 0 y aviso que enumera las cuatro; con lista utilizable no aparece el aviso. Vacío, comentarios y términos cortos también lo disparan. No se cuestiona el retorno 0 decidido expresamente por el diseño.

H-01 refuta que esa declaración alcance al usuario por el hook configurado. H-03 refuta además que el aviso refleje siempre la lista que realmente usó `escanear`. H-04 limita la veracidad del remedio.

`main(['guard'])` devuelve 0 sin aviso, reproducido. Para este hook es coherente: sin archivos, pre-commit no lo ejecuta (`always_run` no está activado); se obtuvo `(no files to check)Skipped`. La promesa literal del docstring necesita esa precondición, pero no cuento esta salida como defecto operativo adicional.

## 5. Cobertura de las siete fronteras del mandato

### 1. Resolución Git

Matriz real en `matrix.log` y `extra.log`; las rutas se abrevian respecto del laboratorio:

| Situación | Salida real de `--git-common-dir` | Resultado del código |
|---|---|---|
| Principal | `.git` | `None`; una sola raíz |
| Worktree convencional | ruta absoluta `principal/.git` | principal correcto |
| Subdirectorio del principal | `../.git` | recupera principal |
| Subdirectorio del worktree | ruta absoluta `principal/.git` | recupera principal, pero no la raíz local del worktree |
| Bare | `.` | incorpora carpeta padre incorrectamente |
| Gitfile por `--separate-git-dir` | ruta absoluta `storage/metadata` | incorpora `storage`; H-02 |
| Submódulo real | ruta absoluta `super/.git/modules/modulo` | incorpora `.git/modules`; H-02 |
| Worktree del submódulo | la misma ruta del submódulo | omite lista de su checkout principal |
| Fuera de Git | vacío; retorno 128 | solo raíz proporcionada |
| `GIT_DIR` / `GIT_COMMON_DIR` ajenos | `.git` indicado por entorno | incorpora checkout ajeno |
| Espacios y `ñ` | rutas preservadas | correcto en layout convencional |
| `core.fscache=true/false` | sin cambio en la salida | mismo resultado correcto |
| Junction al principal | `.git` | sin duplicación tras `resolve()` |
| Junction al worktree | principal absoluto | unión correcta |

Cuando se entrega a `cargar_blocklist` un subdirectorio del worktree, se omite la lista situada en la raíz local de ese worktree: se midió `Only Local` presente al pasar la raíz y ausente al pasar `subdir`. No lo elevo a hallazgo independiente: los consumidores revisados pasan su raíz mediante `__file__`, no un cwd arbitrario. Cambiar el cwd del proceso no cambia `REPO_DEFECTO`.

### 2. Unión

Se ejecutaron lista local vacía, solo comentarios, términos locales y principales repetidos, y `replacements.txt` local combinado con blocklist principal. No se encontró enmascaramiento: se acumula en un mismo `set`. Un término largo local no suprime uno corto principal. Se ordenan por longitud descendente; los empates carecen de desempate explícito, lo que puede alterar el orden de mensajes, no el conjunto comprobado. El parser de replacements sigue teniendo la misma lógica previa; no se reinterpretan aquí líneas arbitrarias como comentarios válidos.

### 3. Aviso, lectura y errores

Además de H-01/H-03/H-04, se probaron:

- UTF-16 y cp1252: se obtienen términos corruptos pero no vacíos; el contenido UTF-8 con el nombre sintético no coincide y no hay aviso de vacío. Es comportamiento heredado de `errors='replace'`, no una garantía nueva ni un fallo cerrado. P2 comprueba vacío, no validez del encoding.
- Denegación de lectura: se abrió una blocklist sintética con `CreateFileW` sin compartir acceso; la lectura real lanzó `PermissionError`, sin aviso de vacío. También se inyectó una denegación controlada. No hay verde silencioso: la excepción interrumpe la ejecución. No se confunde esto con `cargar_blocklist` devolviendo `[]`.
- Git ausente: prueba real con PATH sin Git y prueba inyectada; no rompe. Con términos locales queda sin aviso, aunque no haya podido consultar el principal.
- Timeout: se inyectó `TimeoutExpired`; se captura. Con lista local ausente se hacen tres consultas y se avisa; con lista local presente, dos y no se avisa. La desaparición de cobertura tras la primera carga es H-03.

### 4. CI

Se abrió y comparó `.github/workflows/leak-scan.yml`: no cambia. **El workflow actual ya falla con `exit 1` si el secret está vacío**, pese a comentarios que lo llaman opcional. No se atribuye ese comportamiento al diff.

Se ejecutó en Git Bash el mismo tramo de escritura con `printf` y `git ls-files -z | xargs -0 -r python scripts/precommit_leak_guard.py`, con guard copiado y secret sintético. Resultados en `extra.log`: contenido limpio, 0; coincidencia, 123 de `xargs` porque el guard devuelve 1; secret ausente, 1 antes del escaneo. El texto de la anotación de error de Actions se sustituyó por un mensaje local; no se ejecutó GitHub Actions.

La lista escrita en el propio checkout se sigue leyendo. La novedad es consultar Git dos veces por invocación con lista, tres sin lista. `timeout=10` limita cada consulta, no todo `main`: si todas consumieran ese plazo habría aproximadamente 20/30 segundos de espera más el resto del trabajo, por invocación de `xargs`. Es un cálculo del flujo confirmado por conteo de llamadas, **no latencia natural medida**. Se comprobaron fallos reales por entorno Git inválido y falta del ejecutable. No se encontró un fallo nuevo de la ruta CI convencional con secret válido.

### 5. `tests/test_no_pii_en_tests.py`

Su código ejecutable no cambia. En el archivo sin Git y sin lista: skip. Reutilizando la función real con `REPO` apuntando a un worktree sintético: pasa con lista principal y corpus limpio; detecta una coincidencia en `tests/`; vuelve a hacer skip cuando la lista principal se vacía. El skip sigue siendo alcanzable.

También se creó `tests/ignored_fixture.txt`, ignorado por Git, con un término sintético de la lista principal. `git check-ignore` lo confirmó ignorado, pero `_ficheros_versionables()` lo enumeró y el test falló. Su `rglob` ya examinaba archivos ignorados; ahora esa condición puede aflorar en worktrees que antes omitían el test. Un árbol versionado limpio no garantiza por sí solo este test verde. No se afirma que eso sea una regresión accidental: el contrato visible del test dice revisar los ficheros de `tests/` y `core/`, y no ofrece exención por Git ni por anotación para valores. No se utilizó ninguna lista real del despacho.

### 6. Tests nuevos y mutantes

Prueban Git real para el layout convencional, unión y llamada a `main`, y matan los dos mutantes exigidos. No prueban integración con pre-commit, gitdir separado, submódulo, bare, fallos de consulta ni la segunda carga. La prueba de rutas llama directamente al constructor del aviso mientras la lista existe; la prueba de ausencia usa una carpeta supuestamente fuera de Git. La sonda adicional de cuatro rutas realmente ausentes cubrió esa combinación.

`init -b` requiere una versión de Git que soporte esa opción. Se ejecutó Git 2.53.0.windows.2; no se ejecutaron versiones antiguas. El soporte de selección del nombre inicial está documentado en las [notas de Git 2.28](https://raw.githubusercontent.com/git/git/v2.28.0/Documentation/RelNotes/2.28.0.txt). Con identidad global ausente funcionan; firma heredada falla (H-05). Con `core.autocrlf=true` y temporal con espacios y `ñ`: **17 aprobados**. La ubicación del temporal sí importa (H-06). `pytest-randomly` no está instalado: semillas y hermeticidad frente al orden de la suite completa, **SIN VERIFICAR**.

### 7. Regresiones en funciones no cambiadas

Comparación AST de base/head: `_email_inerte`, `_es_binario`, `_limpiar_regex_lhs`, `_norm`, `_patrones_forma`, `escanear` y `escanear_formas` idénticas. Las reglas `RUTAS_VETADAS` no cambian. Los tests ejecutados cubren rutas HAR/descubrimiento, límites de palabra, binarios, DNI/NIE/IBAN, NIF societario excluido, emails y exenciones por forma.

En la ejecución real se cargó `core.anon.anonimizar`; se verificó identidad de los regex con los canónicos. Se forzó ausencia de ese módulo para ejercer el fallback y comprobar detección de DNI. No se observó regresión en esas comprobaciones. Esto no elimina sus límites preexistentes, incluidos H-07/H-08.

## 6. Ejecuciones y resultados

Entorno medido: Windows, Python **3.14.4**, pytest **9.1.1**, Git **2.53.0.windows.2**, pre-commit **4.6.1**. `rg` no estaba disponible; se usaron búsquedas de PowerShell/Python. Python invocado por ruta completa: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`.

Preparación: `Copy-Item -LiteralPath ../head -Destination ./objeto -Recurse`. Los comandos pytest se ejecutaron dentro de `objeto/` y siempre con `--basetemp` relativo dentro de este workdir. Para la ejecución aislada, solo en el entorno del proceso: `GIT_CONFIG_GLOBAL=<workdir>/empty.gitconfig`, `GIT_CONFIG_NOSYSTEM=1`, sin selectores `GIT_DIR/GIT_COMMON_DIR/GIT_WORK_TREE/GIT_INDEX_FILE`; sin cambios en configuración global del usuario.

Comando sustantivo de suite, administrado por `run_suites.py`:

```text
python -m pytest -o addopts= -q -p no:randomly -p no:cacheprovider --basetemp=./tmp_<corrida> tests/test_precommit_leak_guard.py tests/test_leak_guard_formas.py tests/test_no_pii_en_tests.py
```

| Ejecución | Resultado | Evidencia |
|---|---|---|
| Primer intento usando `workdir` de la herramienta apuntado a `objeto/` | 31 errores de setup: `WinError 5` al crear temporal; no ejerció tests | `suite_original.log` |
| Reintento desde el workdir autorizado con `Set-Location ./objeto` | 25 aprobados, 1 skip, 5 errores de fixture por firma heredada | `suite_retry.log` |
| Suite con configuración Git aislada | 30 aprobados, 1 skip; exit 0 | `suite_clean.log` |
| Mutante `_raiz_comun` siempre `None` | 4 fallos, 26 aprobados, 1 skip; exit 1 | `mutant_none.log` |
| Mutante `main` sin bloque de aviso | 1 fallo, 29 aprobados, 1 skip; exit 1 | `mutant_silent.log` |
| Código restaurado, suite repetida | 30 aprobados, 1 skip; exit 0 | `suite_restored.log` |
| Firma heredada sintética | 1 error de setup | `suite_signing.log` |
| Temporal dentro de worktree con lista | 3 fallos, 14 aprobados | `suite_nested.log` |
| CRLF + ruta con espacios/ñ | 17 aprobados | `suite_crlf.log` |

Los cuatro tests que matan el primer mutante son resolución de worktree, unión, término conocido bloqueado por `main` y cuatro rutas del aviso. El segundo muere en `test_sin_blocklist_en_ninguna_raiz_main_lo_declara`. **Ninguno sobrevive**. La restauración de la copia devolvió el SHA-256 de producción al valor de apertura.

Sondas adicionales ejecutadas: `python review_checks.py matrix`, `python review_checks.py precommit`, `python extra_checks.py`, `python final_checks.py`; todas terminaron con código 0 del arnés. Sus logs conservan resultados internos, incluidas las excepciones o salidas no cero esperadas. `run_suites.py` restaura producción con `finally`; su exit 0 no sustituye los códigos individuales de pytest registrados arriba.

## 7. Sin verificar y límites

- Genealogía y autenticidad de los commits: archivos exportados sin `.git`; solo contenido y hashes acreditados.
- No se ejecutó la suite completa del proyecto. Se ejecutaron los tres módulos indicados y las sondas descritas. No hay cobertura de `pytest-randomly` ni orden aleatorio global.
- Git antiguo, Ubuntu/Python 3.11 reales, runner de GitHub, descarga de hooks remotos y secretos reales: no ejecutados. El CI se reprodujo parcialmente en Git Bash con datos sintéticos.
- No se provocó un timeout natural de diez segundos de Git. La rama de excepción y el fallo entre cargas se ejercieron mediante inyección explícita. No hay medición de latencia del CI, red o disco remoto.
- Se probaron junctions simples y `core.fscache` al consultar repos existentes; no concurrencia de checkout, ciclos de junctions, UNC, rutas extremadamente largas ni todas las variantes de Unicode.
- La denegación de lectura fue real por exclusión de compartición de Windows, más una inyección de `PermissionError`; no se modificaron ACL ni se cubrieron todas las políticas de permisos.
- No se revisó la blocklist privada ni se puede asegurar qué worktrees reales del despacho pasarían `test_no_pii_en_tests`. Las coincidencias y listas utilizadas fueron sintéticas.
- H-07 y H-08 están en base: son deuda documental comprobada, no evidencia de regresión nueva. El dictamen se apoya en los fallos nuevos H-01 a H-06 y queda sujeto a adjudicación de Claude contra la fuente.

## 8. Custodia al cerrar

SHA-256 **al cerrar**, vuelto a calcular sobre los dos originales externos; ambos coinciden con la apertura:

| Fichero de `head/` | SHA-256 |
|---|---|
| `scripts/precommit_leak_guard.py` | `9f8b241c5b71c3432fe15a4e5e5f8d4eeede2b8a92723968ca95d5da45473c2c` |
| `tests/test_precommit_leak_guard.py` | `4e93f3d948761a9c62134555ea0801a92035b5dbe62c2f387e32bed4a91a4869` |

NO-SHIP

<!-- informe-literal:fin:p9vx -->

## 2. Evidencia verificada por mí al adjudicar

Cada hallazgo se contrastó **contra la fuente** (el código en `head/` y, cuando tocaba, el código de
la herramienta ajena), no contra el diff ni contra la seguridad con que venía redactado. Los ocho
se **confirman**. Detalle y remedio por hallazgo en el §4 del plan; aquí solo lo que yo reproduje.

- **H-01.** Leí `pre_commit/commands/run.py` del venv (4.6.2), línea 217:
  `if verbose or hook.verbose or retcode or files_modified:` — la salida de un hook que devuelve 0
  solo se muestra si el hook es `verbose`. Reproducido en un repo temporal con el guard copiado y
  el hook con `verbose: true`: `pre-commit run leak-guard --files nota.md` **sin `-v`** imprime el
  aviso completo. Sin `verbose` no lo imprime, como el revisor midió.
- **H-02.** Reproducido en el scratchpad: `git init --separate-git-dir storage/metadata separate`
  + worktree; desde el worktree `--git-common-dir` = `…/storage/metadata`, cuyo padre `storage`
  no es un checkout. Y algo que el revisor no dijo y que cambia el remedio: en ese layout
  **`git worktree list --porcelain` también reporta los metadatos como «worktree»**, así que
  ningún comando de git identifica el principal desde el worktree enlazado. Por eso el remedio
  no es «otro comando» sino **verificar por resultado** (árbol de trabajo + mismo common-dir) y
  declarar «no determinado» cuando no pasa. Mutante «aceptar el candidato sin verificar»: muere.
  Mutante «volver al padre del common-dir»: mueren 4 tests.
- **H-03.** En `head/`, `main` llamaba a `cargar_blocklist` y luego `escanear` la volvía a
  llamar: dos resoluciones independientes (líneas 311 y 281 de `head/`). Remedio verificado con
  un test que cuenta las llamadas a `resolver_blocklist` durante `main`: **una**. Mutante «main
  resuelve dos veces»: muere.
- **H-04.** El texto del aviso en `head/` (líneas 171-172) afirmaba «el checkout principal tampoco
  la tiene». Remedio: estado observado por ruta y motivo de la resolución. Mutantes «estado fijo»
  sobre cada uno de los dos ficheros: mueren. **Nota propia:** la primera corrida del mutante lo
  dio por superviviente porque el `sed` no había mutado nada (sangría); se comprobó contando las
  líneas mutadas antes de creer el resultado.
- **H-05.** Confirmado en esta máquina: `git config --global` tiene `commit.gpgsign=true`,
  `gpg.format=ssh` e `init.templatedir` con plantilla de hooks. La fixture heredaba los tres. Con
  la firma inyectada por `GIT_CONFIG_COUNT` (la reproducción sintética del revisor) los 23 tests
  del módulo **pasan** tras el remedio; antes de cerrar también el canal de entorno fallaban 2.
- **H-06.** Reproducido: `--basetemp` dentro de este worktree (cuyo principal sí tiene la lista)
  → antes 3 fallos; tras el remedio (`GIT_CEILING_DIRECTORIES` en la fixture) **23 pasan**.
- **H-07 y H-08.** Preexistentes en `base`, confirmados leyendo `_patrones_forma` (excluye NIF)
  y `escanear` (no aplica `_ALLOW`). Corregidos docstring y mensaje.

**Observaciones del revisor que NO se remediaron, con su razón:** (a) `test_no_pii_en_tests.py`
escanea también ficheros gitignored bajo `tests/` y `core/` — es el contrato visible del test
(«ningún fichero de esas carpetas») y preexiste; se anota. (b) Pasar un **subdirectorio** del
worktree a `cargar_blocklist` omite la lista de la raíz local — los consumidores pasan la raíz
por `__file__`; se anota. (c) El CI **ya** fallaba con secret vacío pese a llamarlo opcional —
preexistente, fuera de este diff.

**Cobertura de la remediación: sin revisión adversarial.** Una ronda por radio de daño; los
contraejemplos del revisor se reprodujeron contra el código remediado y hay nueve mutantes,
pero **nadie ajeno ha atacado el árbol tal como queda**.
