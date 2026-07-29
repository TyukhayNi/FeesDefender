# Dual workspace — Fase 0: banco de pruebas del frontal — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Estado: rev. 4 — EJECUTABLE. Sin más rondas adversariales.** (2026-07-29).

La rev. 3 recibió **REQUIERE REVISIÓN** de la **tercera** pasada adversarial de Codex
(3 B0 + 2 A), de-escalando desde el **NO EJECUTABLE** que habían recibido las rev. 1 y
2. Adjudicado todo contra el fuente y contra el binario: **cinco hallazgos confirmados,
uno refutado, uno declarado sin verificar**. Ninguno toca arquitectura, orden de fases
ni el reparto en dos PRs: son correcciones locales de contrato, incorporadas aquí.

**Por qué esta ronda no fue un bucle, y por qué es la última.** El bloqueante de PR-A
lo **creó la propia rev. 3**: al sustituir el helper opt-in de la barrera por un proxy
de `subprocess` (corrección correcta de R2-B0-2), no vio que sus propias Tasks 3-4
**mandan doblar `run_rclone`**, que es la única superficie que el proxy tiene. Es una
interacción nueva entre dos de sus correcciones, no un defecto heredado. Y a la vez, el
rendimiento marginal ha caído de forma medible: las rondas 1 y 2 rindieron **dos PRs de
producción** (#156, #160); esta rinde **cero hallazgos de código** y cinco correcciones
de redacción. Una cuarta pasada mediría el plan contra sí mismo. **Se construye.**

**Goal:** Poner el ciclo `checkout`/`checkin` bajo test de **orquestación** sin
cambiar su comportamiento, para que la Fase 2 pueda tocar el lock con red debajo.

**Architecture:** Una barrera de test que hace imposible alcanzar rclone o el Drive
reales; un punto único de inyección (`Entorno`) para las ocho fuentes de
no-determinismo del frontal; y un doble en memoria fijado a **rclone v1.73.5
(Windows amd64)** con fixtures grabadas y un **hook de mutación por operación** que
produce interleaving determinista sin hilos.

---

## Lo que ya está hecho, y por qué cambia el plan

Dos PRs se adelantaron a esta fase porque arreglaban pérdida de datos viva, no deuda
de diseño. **Los dos salieron de adjudicar revisiones de este plan**, no de revisar
código:

| PR | Qué cerró |
|---|---|
| **#156** (`5f4c81a`) | La **lectura** del protocolo: `_pull_caso_md` devolvía `{}` igual si el `_caso.md` faltaba que si rclone falló, y `estado_de_fm({})` vale `disponible` → el checkout creía el caso libre y degradaba el `_caso.md` canónico a un stub sin `id_go`. Y `_append_evento_drive` reemplazaba todo el `_intake_log.jsonl` por una línea cuando el pull fallaba |
| **#160** (`fec3444`) | La **escritura**: seis retornos de `copyto` ignorados. El peor imprimía «✓ VERDE … lock liberado» y devolvía 0 con el caso aún `prestado`. Incluyó el 8º defecto que Codex destapó: `_integrar_bandeja` devolvía `(0,0)` con un `lsjson` ilegible y el checkin liberaba el lock creyendo la bandeja vacía |

Consecuencias para este plan, verificadas contra `main` en `fec3444`:

- Existen ya **16 tests de orquestación** de `cmd_checkout`/`cmd_checkin`
  (`tests/test_repository_cli_guard_pull.py`) y un `FakeRclone` embrionario con fallos
  de pull, de push por destino+ocurrencia y por subcomando+ocurrencia. Este plan lo
  **promueve**, no lo reinventa.
- El frontal tiene firmas nuevas con las que el `Entorno` debe convivir:
  `ProtocoloIOError`, `_remoto_existe`, `_pull_caso_md → (fm, cuerpo) | None`,
  `_push_caso_md(..., *, cuerpo)`, `_upload_evidencia → list[str]`,
  `_integrar_bandeja` que **lanza**, y el código de salida **4**.
- **Los defectos a reproducir siguen siendo SIETE, no ocho.** Se encontraron ocho en
  el frontal; el octavo (listado ilegible de la bandeja) lo cerró #160, así que pasa
  de `xfail` a caracterización verde. **El recuento vive en el §12 de la SPEC** (su
  criterio de salida 2), ya corregido allí; el §20 es la adjudicación de la revisión
  adversarial *de la SPEC* y no contiene ningún recuento de defectos del frontal. La
  rev. 3 apuntaba al §20 en cuatro sitios: corregido.
- **La matriz de fallos se ha encogido.** Recuento sobre `fec3444`: de las 15 llamadas
  a `run_rclone`, solo **dos** no examinan el retorno — el `lsjson` de CP1 (que juzga
  por **contenido** vía `validar_inventario_texto`, no por retorno) y el `rmdirs` de
  la bandeja. Todo lo demás está comprobado.

**Recuentos correctos, que la rev. 2 tenía mal** (los corrigió Codex y los he
verificado): **15 call-sites de `run_rclone` en 8 rutinas** (16 apariciones menos la
del `def`), y **cuatro** `ts_compacto()` sin argumento —dos en `_append_evento_drive`
y dos que añadió #156 en `_pull_caso_md` y `_push_caso_md`—, no dos.

---

## Global Constraints

- **Fuente única del diseño:** `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md` (rev. 2), §12 «Fase 0» y §14.
- **Este plan SUSTITUYE las Tareas 1-3** de `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md`, allí marcadas como supersedidas. Su Fase 1 sigue vigente.
- **Cero cambio de comportamiento.** Con `ENTORNO_REAL` el frontal ejecuta los mismos comandos, en el mismo orden, con los mismos códigos de salida. Los 27 tests de helpers puros **y los 16 de orquestación** deben pasar sin tocar sus asertos.
- **Ningún bug se arregla aquí.** Se reproducen en `xfail(strict=True, raises=AssertionError)`. **Si un `xfail` no falla, para y repórtalo**: sería un falso positivo de la revisión de la SPEC. Se retira de la Task 6 y se corrige el recuento del **§12** de la SPEC (criterio de salida 2), que es donde vive.
- **Sin esperas reales, sin no-determinismo en los asertos.** Todo sale del `Entorno`.
- **Datos sintéticos**, cero PII. Las capturas reales de rclone llevan nombres de expedientes y **no entran al repo**: las fixtures son sintéticas en los valores y fieles en la forma (`docs/SEGURIDAD_DATOS.md`).
- **Dos PRs, no uno** (ver «Reparto en PRs»). Un solo PR con barrera, doble, refactor de 15 call-sites, ~40 tests y siete `xfail` es demasiado para revisar.
- **Comandos desde la raíz del worktree**, con el venv de la raíz (`C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`); el worktree no tiene `.venv`.
- **Suite completa verde antes de cada PR.** El CI solo corre `leak-scan`. Conteo por `--junit-xml`.
- **Nunca leer `$LASTEXITCODE` detrás de un `Select-Object -First`** al regenerar fixtures: la terminación temprana del pipe lo deja en 0 (ya falseó una medición de este contrato).
- **Nunca asertar sobre una subcadena que el nombre del test pueda inyectar en la salida capturada.** `tmp_path` contiene el nombre del test y el frontal imprime rutas: en #160, un aserto sobre `"evidencia"` pasó en verde sin que el mensaje existiera. Los asertos sobre mensajes usan **frases con espacios**.

---

## Contrato de rclone — v1.73.5, Windows amd64

Medido sobre la versión instalada **tres veces, con comandos distintos** (yo en la rev.
2, el revisor en la 3ª pasada, y otra vez en la adjudicación de esa pasada). Si rclone se
actualiza, se re-mide y se regeneran las fixtures.

**Excepción declarada: la columna «Drive» de `lsjson` es de fuente única** —la medición
de la rev. 2— porque medirla exige el Drive real, que está fuera de alcance. Ni la 3ª
pasada ni su adjudicación la re-verificaron. No está refutada; está **sin re-medir**, y
así se etiqueta.

**`lsjson` — Drive y local NO son iguales:**

| | Drive | Local |
|---|---|---|
| Claves | `Path, Name, Size, MimeType, ModTime, IsDir, ID, Hashes` | las mismas **menos `ID`** |
| Algoritmos | `md5, sha1, sha256` | 13 |
| `ModTime` | `"2026-05-29T07:41:12.000Z"` | `"…T14:33:51.1997234+02:00"` |

- Claves de hash **en minúscula en los dos backends** (`.get("md5")` es correcto). La tesis `Hashes.MD5` quedó **refutada** en las dos pasadas.
- Directorios: `IsDir: true`, sin `Hashes`. De 59 ficheros reales, 0 sin md5.
- **No hay backslashes en `Path`** en ningún backend: la fixture «Windows con backslashes» no existe.

**Filtros y transferencia:**

- `--files-from` + `--exclude`/`--include`/`--filter` → **`CRITICAL`, exit 1, nada transferido**. **Refutada** la tesis de que los ignora.
- `--files-from` con entrada inexistente → **exit 0**, se omite en silencio.
- `--backup-dir` recibe la versión **del destino** sobrescrita, con jerarquía.
- `--fast-list` no cambia la forma ni el conjunto de `Path`.

**Códigos de salida, y no son uniformes:**

| Operación | Código |
|---|---|
| `copyto` de origen ausente | **3**, sin crear el destino |
| `lsjson` de ruta ausente | **3**, `stdout` = `"["` (JSON inválido) |
| **`moveto` de origen ausente** | **1** — distinto del 3 de `copyto`; un doble que los unifique miente |
| **`rmdirs` sobre árbol no vacío** | **0**, y no borra nada |
| `check` con cualquier diferencia | 1 |

**`check`:** `--one-way` cuenta lo que difiere y lo que falta en destino e **ignora
los extras del destino** (2 diferencias frente a 3 sin el flag). Mismo tamaño y
contenido distinto → `md5 differ`: **compara por hash aunque no se pase
`--checksum`**, luego `verificacion_limpia` es de fiar. `cmd_checkin` solo lee el
`returncode`, así que el doble no emula el texto de las NOTICE.

**`--log-file` crea el fichero SOLO si el comando llega a inicializar.** Medido: con
la combinación ilegal `--files-from` + `--exclude`, rclone aborta en la validación
global con `rc=1` y **no crea el log**. La rev. 2 lo afirmaba sin condición; el orden
correcto en el doble es **validar flags primero**.

**Y el par que cierra la regla, medido en la adjudicación de la 3ª pasada:** un fallo
**operativo** sí deja el log. `copy` de un origen inexistente con `--log-level INFO
--log-file` → **rc 3 y log de 1408 bytes**. Luego la frontera no es «fallo / éxito» sino
**«validación de flags / ejecución»**: lo primero no crea log, lo segundo sí, falle o no.
Un doble que ate la creación del log al éxito de la operación miente.

**Google-native: no se puede capturar.** 3007 ficheros hasta profundidad 6 en la
unidad canónica, **cero** entradas `application/vnd.google-apps*` (`MEJORAS #104`). Su
fixture es **sintética y se declara como tal**; no se muta el Drive para averiguar la
forma. No hace falta: el contrato del parser
(`(item.get("Hashes") or {}).get("md5") or None`) trata igual las tres variantes —sin
clave `Hashes`, `Hashes: {}`, `Hashes` sin `md5`—, así que el test emite las tres y
asierta `hash is None`. La forma real que emitiría Drive queda **declaradamente sin
verificar**.

---

## Reparto en PRs

| PR | Tareas | Criterio para pasar al siguiente |
|---|---|---|
| **PR-A — red de seguridad** | 0, 1A, 2, 3, 4 | La barrera es comprobable **también con `run_rclone` doblado** (validador compartido, Task 0), el doble consume fixtures grabadas, y los dos `cmd_*` están caracterizados **con el frontal sin tocar** (inyección por `monkeypatch` de test) |
| **PR-B — costura y defectos** | 1B, 5, 6, 7 | El `Entorno` está enhebrado, la caracterización sigue verde **sin cambiar asertos**, y los siete defectos están reproducidos |

**Dónde cae lo que corrigió la rev. 4:** a **PR-A**, la barrera (B0-1) y el contrato de
los `fallos*`/`resultados` de la Task 2 (parte de B0-3) más la promesa de neutralidad
(A-1). A **PR-B**, el protocolo del hook (B0-2), la Tabla A (resto de B0-3) y el montaje
del `xfail` del baseline (A-2).

**Hallazgos de la 3ª pasada que se RECHAZAN, y por qué:**

- **`from subprocess import run` como bloqueante.** Hoy no existe en `repository_cli`
  (`:63-81`). Es un riesgo hipotético de estilo futuro, no un escape actual. Se acepta el
  guard estático porque es gratis; **no** cuenta como parte del B0.
- **«los `subprocess` legítimos de otros módulos no se rompen»** no es un hallazgo: es
  evidencia **a favor** de que el alcance «toda la suite» es seguro. Se recoge como tal.
- **El sub-punto de los defaults de `ENTORNO_REAL`** (que un default se captura al
  definir la función, y sustituir `ENTORNO_REAL` después no lo cambia): **correcto como
  hecho de Python, inaplicable como defecto** — ningún punto de este plan propone
  rebindear `ENTORNO_REAL`; la inyección es siempre por `entorno=`. Queda dicho en la
  Task 1B para que nadie lo intente.
- **El recorte del plan.** Se rechaza en lo sustantivo. La historia de este documento es
  que **las dos rondas anteriores fallaron por tareas infra-escritas** —la rev. 2 prometió
  la Task 1B cinco veces sin escribirla—, y el contrato de rclone tiene que estar **en el
  plan**, que es lo que se lee *antes* de que las fixtures existan. Se acepta solo el
  `README.md` de procedencia junto a las fixtures (Task 2).

---

## File Structure

| Fichero | Responsabilidad | Cambio |
|---|---|---|
| `tests/_barrera.py` | Barrera: nada de rclone/Drive/`CASOS_ROOT` reales | **Crear (Task 0)** |
| `tests/conftest.py` | Fixtures globales | **Modificar (Task 0):** barrera `autouse` de sesión + función |
| `tests/_dobles/__init__.py`, `tests/_dobles/fake_drive.py` | `FakeDrive`, `FakeRclone`, `entorno_de_prueba` | **Crear (Task 2)** — promueve el doble de #156/#160 |
| `tests/_fixtures/rclone_v1735/*` | Salidas grabadas, con cabecera de procedencia | **Crear (Task 2)** |
| `tests/test_fake_drive.py` | El doble se prueba contra las fixtures | **Crear (Task 2)** |
| `tests/test_repository_cli_guard_pull.py` | Los 16 tests de orquestación existentes | **Modificar (Task 2):** consumen el doble común |
| `tests/test_repository_cli_checkout.py`, `…_checkin.py` | Caracterización | **Crear (Tasks 3-4)** |
| `scripts/repository_cli.py` | Frontal | **Modificar (1A):** `Entorno` + `ENTORNO_REAL` y keyword en `run_rclone`. **Modificar (1B):** propagación a los 15 call-sites |
| `tests/test_repository_cli_fallos.py` | Caracterización de fallos | **Crear (Task 5)** |
| `tests/test_repository_cli_defectos.py` | Los 7 `xfail` | **Crear (Task 6)** |
| `tests/test_repository_cli.py` | Helpers puros | **Modificar (1A):** 2 tests de neutralidad |
| `PLAN.md`, SPEC §11/§12/§14, docstring del frontal | Gobernanza | **Modificar (Task 7)** |

---

# PR-A — red de seguridad

### Task 0: Barrera — implementable, automática y comprobable

La rev. 2 la especificó de forma **no implementable**, y el revisor lo demostró punto
por punto. Los cinco defectos y su corrección:

| Defecto de la rev. 2 | Por qué no funciona | Corrección |
|---|---|---|
| «sustituye `subprocess.run` en el namespace de `scripts.repository_cli`» | `repository_cli` hace `import subprocess`: `repository_cli.subprocess` **es** el módulo global. Parchear su `run` afecta a toda la suite | Sustituir el **binding del módulo**: `monkeypatch.setattr(repository_cli, "subprocess", _ProxySubprocess())`, un objeto que delega todo salvo `run`/`Popen`, que lanzan |
| «sustituye `settings.rclone_binary`» | `Settings` es `@dataclass(frozen=True)`: mutarlo lanza `FrozenInstanceError` | Fijar `RCLONE_BINARY`/`CASOS_ROOT` por **variable de entorno antes de importar** y sustituir el binding cacheado `repository_cli.settings` — **implementable, verificado**: `settings` se importa por nombre (`:79`) y `_rclone_bin` lo lee de ahí (`:185`) |
| «parchear `shutil.which`» | `shutil` **no se importa** en `repository_cli` | Se retira: no cierra nada |
| `@pytest.mark.rclone_real` como escotilla | No está registrado ni se salta (el `conftest` solo implementa `slow`). Y **nadie lo necesita** | **Se retira.** Esta fase prohíbe rclone real sin excepciones |
| `assert_remote_sintetico(cmds)` como helper opt-in | Si el autor olvida llamarlo, no hay barrera | El proxy **rechaza en el momento** cualquier comando cuyo remote no case `^r,team_drive=T:` o cuya ruta local caiga fuera de la raíz permitida. **Corregido de nuevo abajo:** el proxy solo no basta, porque doblar `run_rclone` lo deja sin superficie |

Y **tres defectos más que encontró la 3ª pasada, los tres confirmados** (su B0-1). Son
el motivo de que PR-A no fuera ejecutable en la rev. 3:

| Defecto de la rev. 3 | Por qué no funciona | Corrección |
|---|---|---|
| «`autouse` de **sesión** para cubrir colección» | Pytest **importa los módulos de test durante la colección**, y las fixtures de sesión se montan después, en el setup del primer test. Una fixture no puede proteger un efecto de import. Y no es teórico: `core.config` se importa a nivel de módulo en 4 ficheros de test (p. ej. `tests/test_case_manager.py:7`), así que «fijar `CASOS_ROOT` antes de importar» **no puede hacerse desde una fixture** | La fijación de `CASOS_ROOT`/`RCLONE_BINARY` y el veto de import van al **cuerpo de `tests/conftest.py`** (que se importa antes de los módulos de test) o a `pytest_configure`. La fixture de sesión **se retira**: no aporta nada que la de función no dé, y su justificación era falsa |
| «el proxy rechaza cualquier comando con remote real o ruta fuera de `tmp_path`» | **`run_rclone` es la ÚNICA superficie de `subprocess` del módulo**: `subprocess.` aparece dos veces en `repository_cli.py` (la anotación de `:391` y la llamada de `:399`), ambas dentro de ella. Doblar `run_rclone` deja el proxy con **superficie cero** — y las Tasks 3-4 **mandan doblarla**. La barrera validaría exactamente cero comandos en los tests que más I/O hacen | **Un único validador de operandos**, `assert_operandos_sinteticos(cmd, *, raiz_local)`, invocado **tanto por el proxy como por `FakeRclone.__call__`**. El doble recibe `raiz_local` en el constructor y **rechaza todo operando local externo**, además del remote no sintético |
| «rutas locales bajo `tmp_path`», dando por hecho que `CASOS_ROOT` las gobierna | **No las gobierna.** `cmd_checkout` hace `local = Path(args.local)` (`:454`), `local.mkdir(parents=True, exist_ok=True)` (`:517`) y escribe el manifest (`:545-548`) sobre lo que venga en `args.local`, sin pasar por `CASOS_ROOT`. Y el doble escribe `Path(destino)` tal cual (`guard_pull.py:138-141, 168-172`) | La `raiz_local` permitida es un dato **explícito** del montaje, no una consecuencia de `CASOS_ROOT`. El validador la exige |

**Endurecimiento aceptado, que no era un defecto:** hoy no existe `from subprocess
import run` en `repository_cli` (verificado en sus imports, `:63-81`), pero ese estilo
eludiría el proxy en el futuro. Se añade un **guard estático** que falle si aparece.
No es parte del bloqueante; es gratis.

Además: la barrera es `autouse` de **función** (aislamiento por test) más la fijación de
entorno en el cuerpo del `conftest` (arriba), y **prohíbe `importlib.reload` de
`scripts.repository_cli`** durante los tests de esta fase, porque restauraría sus
bindings reales. **Recargar `core.config` sí está permitido** —lo hacen ya
`tmp_casos_root` y `tests/test_case_manager.py`, y no restaura ningún binding de
`repository_cli`—: el veto es solo sobre este último.
`tests/conftest.py::tmp_casos_root` —que **no es `autouse`**, pese a lo que dice el
docstring del módulo (`tests/conftest.py:42`)— sigue existiendo para quien lo pida; la
barrera cubre el hueco de quien no.

**Lo que el proxy sí cierra, y por eso el alcance «toda la suite» se mantiene:**
sustituir únicamente `repository_cli.subprocess` **no rompe** los usos legítimos de
`subprocess` de otros módulos (p. ej. `tests/test_docs_gobernanza.py`), porque no toca
el módulo global. Verificado en la 3ª pasada.

**Alcance, decidido y escrito:** la barrera aplica a **toda la suite**. Un
`subprocess.run` real desde `scripts/repository_cli.py` no es legítimo en ningún test
del repo, y limitarla a esta fase dejaría el agujero abierto para el siguiente test
que se escriba.

- [ ] **Step 1: Write the failing tests** — un `run_rclone` sin doble falla con `AssertionError` de la barrera; un comando con el remote real falla; una ruta local fuera de la `raiz_local` falla **por el proxy**; **la misma ruta falla igual con `run_rclone` doblado, por el validador dentro de `FakeRclone`** (es el test que la rev. 3 no tenía y que demuestra el escape); un `importlib.reload(repository_cli)` falla; un `importlib.reload(core.config)` **pasa**; el guard estático falla ante un `from subprocess import run` inyectado.
- [ ] **Step 2: Run to verify they fail**
- [ ] **Step 3: Implement** el proxy, el validador compartido, la fijación de entorno en el cuerpo del `conftest` y la fixture `autouse` de función. **El validador se escribe aquí y la Task 2 lo consume**: si se escribiera dos veces, las dos copias divergirían.
- [ ] **Step 4: Verify** que los 27 + 16 siguen verdes **y que la suite completa no se rompe** — es el riesgo real de esta tarea:

```bash
python -m pytest -q --tb=short
```

---

### Task 1A: `Entorno` — el tipo y la instancia real, sin tocar los `cmd_*`

Ocho fuentes de no-determinismo, no cuatro ni cinco:

| Fuente | Dónde |
|---|---|
| `run_rclone` | **15 call-sites en 8 rutinas** |
| `now_iso_utc()` | `cmd_checkout`, `cmd_checkin`, `_append_evento_drive` |
| `socket.gethostname()` | `cmd_checkout` |
| `_tmp_dir()` | `mkdtemp` |
| `time.sleep(_SYNC_LAG_S)` | `cmd_checkout` |
| `_nonce()` | `secrets` |
| `_usuario_por_defecto()` | `get_actor()` → entorno del SO |
| `_rclone_bin()` | `settings.rclone_binary` |

Y **cuatro** `ts_compacto()` sin argumento, que consumen el reloj de forma encubierta:
dos en `_append_evento_drive` y dos en `_pull_caso_md`/`_push_caso_md`.

**Interfaces:** `@dataclass(frozen=True) Entorno` con `ejecutar`, `ahora`, `hostname`,
`work_dir`, `esperar`, `nonce`, `usuario`, `binario`; `ENTORNO_REAL` reproduciendo
exactamente lo de hoy; `run_rclone(cmd, *, entorno=ENTORNO_REAL)`. **En esta tarea no
se toca ningún `cmd_*` ni helper de I/O.**

- [ ] **Step 1: Write the failing tests** — `run_rclone` usa el `ejecutar` inyectado; y neutralidad de las ocho piezas de `ENTORNO_REAL`. El test de neutralidad **no deja un temporal real en disco** (hallazgo del revisor): comprueba la fábrica sin invocarla, o la invoca y limpia.
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Write the implementation** — extraer el cuerpo de `run_rclone` a `_ejecutar_rclone_real` sin tocar una línea.
- [ ] **Step 4: Verify** 27 + 16 + 2 verdes, sin tocar los previos.

---

### Task 2: `FakeDrive` — promover el doble y romper su circularidad

**Interfaces:** `FakeDrive` (`escribir/leer/borrar/rutas/md5/snapshot/bytes_snapshot`)
y `FakeRclone(drive, *, raiz_local, fallos, fallos_push, fallos_sub, resultados, hook)`,
con `registro` de todos los comandos en orden y **`cmds` como alias contractual de
`registro`** (ver Step 4). `raiz_local` es obligatoria: el doble invoca el validador de
la Task 0 en cada `__call__` y **rechaza todo operando local fuera de esa raíz**, porque
doblar `run_rclone` desactiva el proxy (Task 0, B0-1 de la 3ª pasada).

**Los tres `fallos*` se heredan de #160, pero NO «tal cual»** — la 3ª pasada demostró
que su semántica de fallo es insuficiente y además contradice el contrato de rclone de
este mismo plan (su B0-3, confirmado):

- `_sub_falla` devuelve hoy `rc=3` con `stdout="["` para **cualquier** subcomando
  (`guard_pull.py:126-129`). Eso hace **imposible** la fila obligatoria de la Tabla A
  «`rc != 0` con `stdout` parseable», y **unifica `moveto` (rc real 1) con `copyto`
  (rc real 3)** — precisamente lo que el contrato de arriba llama mentira. Medido de
  nuevo en la adjudicación: `moveto` de origen ausente → **1**, `copyto` → **3**.
- El `hook` **no puede suplirlo**: su firma devuelve `None`, así que muta el `FakeDrive`
  pero no sustituye el resultado de la operación.

**Cuarto canal, nuevo: `resultados`** —
`{(subcomando, ocurrencia_1based): (returncode, stdout, stderr)}`. Devuelve ese
resultado **guionizado**, **sin mutar el `FakeDrive`** salvo que el escenario lo pida
por separado. Es el único mecanismo con el que la Tabla A es ejecutable, y sustituye a
la promesa de conservar los `fallos*` intactos. Los tres `fallos*` siguen existiendo
para los 16 tests migrados; `resultados` gana precedencia cuando ambos casan.

**La circularidad que hay que matar** (A-1 de la 2ª pasada): el doble actual llama a
`rc.esta_excluido(rel)`, o sea **importa las reglas de producción para decidir la
transferencia**. Si alguien quitara `_exclusiones_rclone()` del comando, el doble
seguiría excluyendo y el test pasaría. Contrato nuevo:

- el `copy` del doble decide **solo por los flags presentes en `cmd`**;
- **sin flags, transfiere también protocolo y notas**;
- el doble **no importa `core.repository_checkout` ni `core.config`**;
- hay un test «con flags / sin flags» que lo demuestra.

**Orden de procesamiento del doble**, en este orden y no otro:

1. validar operandos sintéticos (remote y `raiz_local`) → `AssertionError`;
2. validar combinaciones ilegales de flags (`--files-from` con filtros → `rc=1`, sin
   crear log ni transferir nada);
3. crear el `--log-file` si el comando es válido. **Medido: un fallo *operativo* SÍ deja
   el log** (`copy` de origen ausente → rc 3 **con log de 1408 B**); solo el fallo de
   *validación de flags* no lo crea. Por eso este paso va antes del 4 y después del 2;
4. aplicar `resultados`, luego `fallos*`;
5. ejecutar la operación;
6. **disparar el `hook`** si toca (protocolo abajo).

**Códigos de salida por operación**, del contrato: `copyto` ausente → 3; `lsjson`
ausente → 3 con `stdout="["`; `moveto` ausente → **1**; `rmdirs` no vacío → **0** sin
borrar; `check` con diferencias → 1. Un comando o flag **no soportado** →
`AssertionError`, nunca éxito permisivo.

**El `hook`, con protocolo cerrado de verdad.** La rev. 2 lo dejó ambiguo (su A-2) y la
rev. 3 fijó el contador y el one-shot **pero no cuándo dispara, ni cómo se apunta a la
operación `n`, ni de dónde sale el actor** — los tres huecos los cazó la 3ª pasada (su
B0-2, confirmado), y sin ellos los dos `xfail` de A-1 no son construibles. Contrato
completo:

- **Armado explícito: `armar(n_objetivo, callback)`.** No hay disparo implícito en la
  primera operación. Sin `n_objetivo` el `xfail` del *rollback ajeno* es imposible:
  necesita disparar tras la **tercera** operación relevante de A (la relectura de
  verificación del nonce), y un hook que se desarma «al invocarse» se habría consumido
  en la primera.
- **Instante de disparo, y es la mitad del hallazgo:** el callback corre **después de
  los efectos y del resultado** de la operación objetivo y **antes de devolver al
  caller**. El orden importa y decide si el defecto se reproduce:
  - si disparase **antes** de materializar el CP0 de A, B completaría su checkout y
    escribiría `prestado`, y **A leería ese estado y abortaría correctamente**: no hay
    doble titular, el test pasaría y el `xfail(strict=True)` rompería la suite;
  - disparando **después**, A conserva su lectura de `disponible`, B completa el flujo
    y A sigue con su push ciego. Ese es el interleaving que se busca.
- **contador global por instancia**, incrementado **antes** de invocar el callback, y
  **las operaciones que fallan también cuentan** —incluidas las guionizadas por
  `resultados` y las abortadas en la validación de flags—, para que `n_objetivo` sea
  estable frente a un escenario que introduzca un fallo.
- **one-shot**: se desarma al dispararse y solo se rearma con otro `armar(...)` — sin
  eso, un actor concurrente que reentre recursaría.
- **Actor: ejecutores etiquetados.** La firma `Callable[[int, list[str], FakeDrive],
  None]` no lleva actor, y `FakeRclone.__call__(self, cmd)` tampoco
  (`guard_pull.py:123`): con una instancia compartida entre A y B **nada distingue
  `(A, copyto)` de `(B, copyto)`**. Se resuelve con un **wrapper por actor**,
  `EjecutorActor(fake, "A")`, que comparte el `FakeDrive` y el contador global pero
  etiqueta cada llamada. Cada `Entorno` recibe su ejecutor; el `FakeRclone` no adivina
  quién le habla.
- las operaciones que el propio hook provoque **se numeran en la misma secuencia** y
  quedan en el `registro`, con su actor;
- `FakeRclone` expone `traza_actores: list[tuple[str, str]]` (actor, subcomando) para
  poder asertar la **secuencia causal**, no solo el estado final.

**Fixtures grabadas** en `tests/_fixtures/rclone_v1735/`, cada una con cabecera que
declare **comando, versión de rclone, backend, fecha y qué campos se sustituyeron**:
`lsjson_drive.json` (real sanitizada), `lsjson_local.json` (real),
`lsjson_native.json` (**sintética**, con las tres variantes de md5 ausente),
`lsjson_vacio.json`, `lsjson_truncado.txt`, `files_from_con_filtros.txt` (el `stderr`
real del `CRITICAL`). Más un **`README.md` en ese directorio** con la procedencia
completa: los comandos exactos con los que se midió cada contrato, la versión del
binario y qué campos se sanearon — así regenerarlas no obliga a arqueología del plan
(único recorte que se acepta de la 3ª pasada).

- [ ] **Step 1: Write the failing tests** — validado **contra el parser real** y contra las fixtures. Mínimo: «con flags / sin flags»; las tres variantes native → `hash is None`; `--files-from`+filtros → rc 1 **y sin log**; **`copy` con fallo operativo → rc≠0 CON log** (el par del anterior: distingue validación de operación); `check` por md5 ignorando extras; **`moveto` ausente → 1 y `copyto` ausente → 3, en el mismo test, para que un doble que los unifique no pase**; `rmdirs` no vacío → 0; `resultados` devuelve `rc≠0` con `stdout` parseable **sin mutar el Drive**; operando local fuera de `raiz_local` → `AssertionError`; `armar(n_objetivo)` dispara en la operación `n` y no antes, one-shot, con las fallidas contando; `traza_actores` distingue A de B con ejecutores etiquetados; comando no soportado → `AssertionError`.
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Write the implementation**
- [ ] **Step 4: Migrar los 16 tests existentes** al doble común. **El diff se limita a imports y montaje: asertos, snapshots y trazas quedan idénticos.** No se promete «cuerpos idénticos» —la 3ª pasada demostró que era insostenible (su A-1, confirmado)—: los tests actuales asertan sobre **`fake.cmds`** (`guard_pull.py:309`, `:431`, y el helper de `:251`) y **llaman helpers directamente** (`cli._push_caso_md` en `:317`, `cli._append_evento_drive` en `:334`, `:346`, `:504`), así que un renombrado a `registro` o el paso de `entorno=` tocaría cuerpos. Dos decisiones para que la promesa sea cierta y el stop condition no salte por nada:
  - **`cmds` se conserva como alias contractual de `registro`**, no como resto histórico. Está documentado en el docstring del doble;
  - las llamadas directas a helpers pueden cambiar mecánicamente para pasar `entorno=` (en la Task 1B). **Eso no es una regresión y no dispara el «para y repórtalo»**; lo que lo dispara es cambiar un **aserto**.
  Antes de borrar el doble embrionario, comprobar **paridad** en los tres ejes que pueden cambiar de significado: el `registro` de comandos, las precondiciones de cada escenario y el snapshot final del Drive. Si el doble común es más permisivo en algún punto, la migración es una regresión silenciosa (A-4 de la 2ª pasada).

---

### Tasks 3 y 4: Caracterización de `cmd_checkout` y `cmd_checkin`

Se escriben **antes** de 1B, con el frontal **sin tocar**: la inyección es por
`monkeypatch` de `run_rclone`, `_tmp_dir`, `_SYNC_LAG_S`, `_nonce` y
`_usuario_por_defecto`, exactamente como hacen hoy los 16 tests de #156/#160.

**Files:** `tests/test_repository_cli_checkout.py`, `tests/test_repository_cli_checkin.py`.
Helpers locales de `Namespace` **más un smoke test por comando construido con
`build_parser().parse_args([...])`**, para que el entrypoint público no quede fuera.

**Checkout:** caso prestado aborta con 2 (**con death snapshot del Drive y del
local**, no solo «no hay `copy`»); conflicto aborta con 2; `--dry-run` no escribe;
nonce ajeno tras el sync lag aborta sin copiar; orden relativo del camino feliz; lock
completo con `checkout_maquina`/`timestamp` **del `Entorno`**; el protocolo no baja a
local; el `MANIFEST` se genera y se sube; `copy` fallido revierte y devuelve 1; el
evento lleva los campos del contrato —**incluido `ruta_local`, que la SPEC §6.1 retira
en la Fase 2: este test es el que habrá que actualizar entonces, y lo dice en su
docstring**—; `esperar` se llama una vez con `_SYNC_LAG_S`, sin dormir.

**Checkin:** ruta local inexistente → 2 con cero comandos; inventario inválido → 1;
`--dry-run` escribe el DELTA en el `work_dir` inyectado y no toca nada; borrados sin
`--yes` → 3; el `copy` y el `check` usan la **misma** lista `--files-from`;
`PRESERVE_DRIVE` no se sube; conflicto escribe estado y no libera; veto de grupo no
libera; `copy` fallido no propaga borrados; camino verde libera con
`ultimo_checkin_*`; la bandeja se integra y se vacía; colisión → `_reingesta_*`
(anotando que `MEJORAS #101` dice que nadie lo reconcilia); **y el listado ilegible de
la bandeja no libera el lock** (era el 8º defecto; #160 lo arregló, así que aquí es
caracterización verde).

**El orden actual del camino verde se fija DENTRO del test del camino verde**, como un
tramo de su traza marcado `# contrato temporal (A-2)`, no como test independiente —la
rev. 2 lo tenía suelto y el revisor propuso integrarlo, con razón: así hay un solo
sitio que actualizar cuando la Fase 2 cambie el orden.

**Si algo de esto falla, es un bug vivo que no conocíamos: para y repórtalo.**

---

# PR-B — costura y defectos

### Task 1B: enhebrar el `Entorno` por los 15 call-sites

La rev. 2 **prometió esta tarea cinco veces y no la escribió** —incluida la frase «la
Task 1B es el punto de mayor riesgo del plan»—, y el revisor lo cazó. Va aquí,
**después** de la caracterización, que es la única red que la protege.

**Files:** `scripts/repository_cli.py`.

**Los 15 call-sites, por rutina:** `cmd_checkout` (2), `cmd_checkin` (4),
`_integrar_bandeja` (3), `_append_evento_drive` (2), `_pull_caso_md` (1),
`_push_caso_md` (1), `_upload_evidencia` (1), `_remoto_existe` (1).

**Y las otras siete fuentes:** `now_iso_utc()` en
`cmd_checkout`/`cmd_checkin`/`_append_evento_drive`; los **cuatro** `ts_compacto()`
sin argumento; `socket.gethostname()`; `_tmp_dir()`; `time.sleep`; `_nonce()`;
`_usuario_por_defecto()`; `_rclone_bin()`.

**Firma:** `cmd_checkout(args, *, entorno=ENTORNO_REAL)` y ídem `cmd_checkin`,
propagando por **parámetro explícito** a los siete helpers de I/O. Prohibido
resolverlo por global mutable.

**Qué cambia en los tests, dicho sin eufemismos:** el **montaje** de los tests de las
Tasks 3-4 y de los 16 migrados pasa de `monkeypatch` de módulo a `entorno=` inyectado, y
las llamadas directas a helpers ganan `entorno=`. **Asertos, snapshots y trazas quedan
idénticos** — eso, y no «cuerpos idénticos», que la 3ª pasada refutó: hay tests que
invocan los helpers a pelo (`guard_pull.py:317, 334, 346, 504`) y su línea de llamada
cambia necesariamente.

**Lo que NO hace falta hacer:** rebindear `ENTORNO_REAL`. La inyección es **siempre** por
`entorno=`. La 3ª pasada observó, con razón, que un default de función se captura al
definirla y que sustituir `ENTORNO_REAL` después no lo cambia — es cierto, y por eso el
plan no lo propone en ningún punto. Queda dicho para que nadie lo intente.

- [ ] **Step 1** — propagar `entorno` a los 7 helpers y a los 2 `cmd_*`, sin tocar lógica.
- [ ] **Step 2** — migrar el montaje de los tests de Tasks 3-4 y de los 16 previos.
- [ ] **Step 3: Verify** — la caracterización pasa **con los mismos asertos** y la suite completa está verde. Cualquier **aserto** que haya que cambiar es señal de que el refactor no fue neutral: **para y repórtalo**. Cambiar una **línea de llamada o de montaje** no lo es.

---

### Task 5: Fallos — dos tablas, no una

La rev. 2 mezclaba caracterización con expectativas normativas, y eso hacía la tabla
inasertable (B0-3 de la 2ª pasada). Se parte:

**Tabla A — caracterización del comportamiento ACTUAL** (verde, sin cambiar nada):

| Call site | Fallo inyectado | Qué se fija |
|---|---|---|
| `_leer_manifest` | fichero ausente | devuelve `{}` → merge de **2 vías** en silencio; se fija el `rc`, el plan resultante y el estado del lock |
| `_leer_manifest` | JSON corrupto | idem, y no revienta |
| `lsjson` de CP1 | `stdout` truncado | `InventarioInvalido` → `rc=1`, cero mutación |
| `lsjson` de CP1 | **`rc != 0` con `stdout` parseable** — **requiere `resultados`, no `fallos_sub`** (Task 2) | **pasa**: `validar_inventario_texto` juzga por contenido, no por retorno. Es uno de los dos únicos retornos que siguen sin examinar |
| `rmdirs` de la bandeja | `rc != 0` vía `resultados` | se ignora: **retorno descartado, comando emitido en el `registro` y lock liberado igual**. Es el otro |
| `check` | `rc=1` | amarillo, lock conservado |
| `moveto` de un borrado | `rc=1` | `borrado_fallo` → amarillo, lock conservado |
| artefactos del protocolo | — | **todos** dentro del `work_dir` inyectado; nada en el árbol del caso |
| CP11 | `estado_repositorio` ausente | `MEJORAS #93-B`: `TransicionInvalida` **después** de mover bytes, registrar evento e integrar bandeja. Se caracteriza tal cual; **no se arregla aquí** |

**Tabla B — expectativas normativas que hoy NO se cumplen** → van a la Task 6 como
`xfail`, no aquí. La rev. 2 colaba dos en esta tabla: que un baseline ausente «quede
declarado en el DELTA» (exigiría cambiar `render_delta`, que hoy solo recibe el plan,
y por tanto **no es caracterización**) y que un listado ilegible de la bandeja no
libere el lock (ya arreglado en #160 → Tabla A).

**Dos precisiones de la 3ª pasada, ambas confirmadas:**

- la fila del `lsjson` de CP1 **no es inyectable con los `fallos*` heredados**: hoy todo
  fallo de subcomando sale como `rc=3, stdout="["`, que es JSON inválido. De ahí el canal
  `resultados` de la Task 2. La fila **no se retira**: la combinación «retorno no cero
  con salida utilizable» es el patrón que `CLAUDE.md` documenta para este Drive (`exit 1`
  por dangling shortcuts) y `build_lsjson_cmd` pasa `--drive-skip-shortcuts` justo para
  esquivarla, lo que mitiga los atajos y no los demás errores no fatales. Que Drive emita
  *exactamente* esa forma queda **sin verificar**; que producción ignore el retorno es un
  hecho del código (`:598-603`), y es lo que la fila fija;
- **`FakeDrive` no modela directorios**: es un `dict` ruta→bytes. Por eso el aserto del
  `rmdirs` **no afirma «quedan directorios vacíos»** —sería inasertable— sino lo que sí
  se puede comprobar: retorno descartado, comando emitido, lock liberado. Modelar
  directorios sería trabajo de la Fase 2, y no hace falta aquí.

**Hecho, no intención, sobre el semáforo:** el «rojo» de orquestación es
**inalcanzable** — `cmd_checkin` retorna en el `if copia_fallo` **antes** de llamar a
`clasificar_semaforo`. Se fija como hecho; la rama roja del helper puro ya está
cubierta por sus propios tests.

---

### Task 6: Los SIETE defectos, reproducidos

Siete, no ocho: el octavo lo cerró #160. Cada uno con
`@pytest.mark.xfail(strict=True, raises=AssertionError, reason="…")`, y **las
precondiciones del montaje lanzan `RuntimeError`**, de modo que el único
`AssertionError` posible sea el aserto normativo final.

- [ ] **`A-1 · doble titular`** — con el `hook`: tras el CP0 de A y antes de su push, el hook ejecuta el **flujo completo** de B (`cmd_checkout` es monolítico: no se puede pausar a B tras su CP0). Se asierta la **secuencia causal** en `traza_actores`, no solo que ambos acaben en 0.
- [ ] **`A-1 · rollback ajeno`** — el hook instala el lock de B **después** de que A verifique el suyo y antes de que falle el `copy`. Se exige que A no toque un lock ajeno (`LOCK_NOT_MINE`). El test debe demostrar que B **leyó `disponible` antes**, o solo prueba un estado, no la causa.
- [ ] **`A-2 · orden del checkin`** — se exige integrar bandeja → verificar → evento → liberar.
- [ ] **`A-2 · fallo de moveto en la bandeja libera el lock`** — con `resultados={("moveto", n): (1, "", "…")}`, **no** con `fallos_sub`: el rc real de un `moveto` fallido es **1**, y el canal heredado lo aplanaría a 3. Producción solo mira `!= 0`, así que el `xfail` saldría igual, pero un doble que miente sobre el código de salida contamina la Fase 2. Hoy solo se imprime `⚠` y se libera. (El listado ilegible ya no: #160.)
- [ ] **`A-2 · checkin reentrante duplica el evento`** — dos checkins en verde. **Capturar explícitamente la `TransicionInvalida` de CP11** (`MEJORAS #93-B`) para poder contar los eventos; sin eso el `xfail` se satisface con ese traceback.
- [ ] **`B0-2 · el log canónico se reescribe y se corrompe`** — sembrar `b'{"event":"a"}\n\n{"event":"\xff"}'` sin salto final; se exige que los bytes preexistentes sobrevivan **idénticos**.
- [ ] **`B0-2 · falta el baseline del log`** — **emplazamiento cerrado y durable**: el hash y el número de líneas del log viven como **campos del `MANIFEST_CHECKOUT.json`** (`log_hash`, `log_lineas`), que ya se escribe en el local **y se sube al Drive**. La rev. 2 lo ponía en el `work_dir` temporal, que no se comunica al checkin y desaparece con el proceso: cerraba el aserto y no el defecto.
  **Montaje, que la rev. 3 dejaba abierto** (A-2 de la 3ª pasada, confirmado): la Fase 0 **no puede hacer que checkout emita esos campos** —sería cambio de comportamiento, prohibido— así que el test **no puede** exigir primero que los genere y después que el checkin los use: se quedaría en `xfail` por el primer aserto, sin demostrar recuperación ni uso. Por tanto:
  - el manifest **se siembra** ya con `log_hash`/`log_lineas` como **precondición verificada que lanza `RuntimeError`** si no queda escrita;
  - **un único aserto normativo final**, sobre que el checkin los **recupera y los usa** para detectar divergencia del log;
  - y a la Tabla A de la Task 5 se añade la **caracterización verde** de los dos hechos que hoy lo hacen inocuo: el manifest que escribe checkout **no lleva esos campos** (`:545-548`), y `_leer_manifest` **solo devuelve `data["inventario"]`** (`:1010-1020`), así que campos extra y manifests legacy pasan sin romper nada. Medido en la adjudicación.
  - **Fuera de alcance aquí:** la política ante un manifest legacy **sin** baseline —bloquear o admitir compatibilidad explícita— se decide en la Fase 2, no se cuela en un `xfail`.

```bash
python -m pytest tests/test_repository_cli_defectos.py -q -rxX
```

Expected: **7 xfailed, 0 xpassed**.

---

### Task 7: Gobernanza

- [ ] `PLAN.md`: `[x]` a la Fase 0 con los hashes de PR-A y PR-B.
- [x] **SPEC §11 brecha 14 y §12 criterio de salida: hechos corregidos ya**, con la rev. 3 de este plan — no se esperan al build, porque afirmaban en `main` cosas falsas: que la orquestación no tenía ningún test (hay 16) y que los defectos a reproducir eran siete sin explicar que se encontraron ocho y uno se cerró.
- [ ] **SPEC §14.2:** repasar si queda alguna afirmación sobre ausencia de tests de orquestación.
- [ ] Docstring del frontal: la «Nota de alcance» ya menciona los guards; actualizarla al banco completo y decir qué sigue **sin** cubrir (rclone real, Drive real, cuota de API).
- [ ] Suite completa + guards de docs.

**Criterio de salida de la Fase 0:**

1. la **brecha 14** queda cerrada: doble contractual + caracterización de los dos `cmd_*`;
2. los **siete** defectos reproducidos en `xfail(strict=True, raises=AssertionError)`;
3. la Tabla A de la Task 5 cubre los dos retornos que siguen sin examinar y los caminos de fallo que deciden pérdida, auditoría o liberación;
4. el arnés de la matriz del §14.1 queda **preparado para la Fase 1**, no ejecutado aquí (sus filas de scratch, registro ausente y capacidades son de la Fase 1);
5. ningún test puede alcanzar rclone real, el Drive real ni `CASOS_ROOT`.

---

## Riesgos y trampas conocidas

- **La Task 0 es el punto de mayor riesgo del PR-A**, no 1B: el proxy de `subprocess` aplica a **toda la suite** y puede romper tests ajenos. Se verifica con la suite completa antes de seguir.
- **La trampa concreta de la Task 0, que ya cayó una vez:** es fácil escribir una barrera que **parezca** cerrada y no valide nada, porque el propio plan manda doblar `run_rclone` y esa es la única superficie del proxy. El test que lo demuestra —operando local ilegítimo **con el doble puesto**— no es opcional: es el que distingue una barrera de un adorno.
- **La Task 1B sigue siendo el punto de mayor riesgo del PR-B** (toca el camino que mueve los bytes), pero ya con 27 + 16 + ~25 tests debajo.
- **`pytest-randomly`**: `FakeDrive` se construye por test, nunca a nivel de módulo.
- **`ts_compacto()` tiene resolución de minuto**: dos pulls en el mismo minuto comparten nombre de temporal. Hoy es inocuo; un test que dependa de nombres únicos intra-minuto es frágil.
- **`_md5` usa MD5 a propósito** (paridad con la Drive API): el doble usa el mismo algoritmo.
- **No confundir «reproducir» con «arreglar»**. Y si un `xfail` no falla, se documenta y se corrige el recuento del **§12** de la SPEC.

## Fuera de alcance de la Fase 0

- Arreglar cualquiera de los siete defectos, incluido `MEJORAS #93-B`.
- Tocar `core/repository_checkout.py`.
- Cualquier pieza del `CaseWorkspace` (Fase 1).
- Dobles de CRM y Gmail (Fase 3).
- `MEJORAS #96`, `#101`, `#102`, `#104`.
- Verificar contra `G:` o rclone real.
