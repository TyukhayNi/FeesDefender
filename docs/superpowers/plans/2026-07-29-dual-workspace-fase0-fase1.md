# Dual workspace — Fase 0 (banco de pruebas del frontal) + Fase 1 (núcleo de workspace) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que exista **una sola respuesta** a «¿dónde se trabaja este caso y qué
está permitido?», y que esa respuesta sea la que use el primer consumidor real
(`scripts/sala_maquina`). Al terminar: ningún camino del código crea un
directorio bajo `CASOS_ROOT` para una identidad que el catálogo no conoce; con
`--case-dir`, los bytes y el evento de custodia caen en el **mismo** árbol; y el
ciclo checkout/checkin queda por primera vez bajo test de orquestación.

**Architecture:** Tres piezas puras nuevas en `core/casos/` —modelo
(`workspace_model.py`), registro privado (`workspace_registry.py`) y resolver
(`workspace_resolver.py`)— más un `CaseCatalog` que envuelve al `case_locator`
actual. Los motores **no se tocan**: siguen recibiendo `Path`. `core.intake_log`
pasa a escribir en el log del workspace ya resuelto (es la costura que impide el
split brain). El frontal `scripts/repository_cli.py` gana un puerto inyectable
para rclone, sin cambio de comportamiento, para que la Fase 2 pueda tocar el lock
con red debajo.

**Tech Stack:** Python 3.11+, `typer` (CLI de sala de máquina), `argparse`
(`repository_cli`), `pytest` (+ `pytest-randomly`: la suite corre en orden
aleatorio), stdlib (`dataclasses`, `json`, `os.replace`, `tempfile`, `secrets`).
Sin dependencias nuevas.

## Global Constraints

- **Fuente única del diseño:** `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md` **rev. 2**. No reabrir sus decisiones cerradas (§3, §20). El informe de la revisión adversarial que las justifica es `…-adversarial-review.md`.
- **Alcance: Fase 0 + Fase 1 y nada más.** No se materializa `_caso.md` ni el log en local (Fase 2), no se toca `decidir_escritura` (Fase 2), no se toca `expedientes-xl` ni las skills de checkout (Fase 2/5), no se migra Streamlit (Fase 4). Si una tarea empieza a necesitar eso, **para y pregunta**.
- **`MEJORAS #96` NO se arregla aquí**, y por eso aquí **no** se materializa ningún `_caso.md` local: el orden importa (spec §6.3).
- **Ni un cambio de comportamiento en la Fase 0.** El puerto de rclone es refactor puro: mismos comandos, mismo orden, mismos códigos de salida. Los tests de caracterización se escriben **antes** y deben pasar igual antes y después.
- **Los bugs conocidos se documentan, no se arreglan.** Los tests que reproducen A-1, A-2 y B0-2 nacen `xfail(strict=True)` con el número de hallazgo en el motivo. La Fase 2 los pone en verde borrando el `xfail`. Un `xfail` que empieza a pasar rompe la suite: es la alarma de que alguien lo arregló sin actualizar el plan.
- **Fail closed.** Ante ambigüedad, el resolver lanza. Nunca devuelve un workspace «probable».
- **Cero PII en tests y en mensajes.** Casos sintéticos tipo `BaRS9 - Prueba - (W-TEST99) - Vuelta`; los errores citan W-code y código de error, nunca nombres ni rutas de terceros (spec §16).
- **Encoding:** UTF-8 sin BOM explícito (`encoding="utf-8"`) en toda lectura/escritura.
- **Comandos desde la raíz del worktree, con el intérprete del venv EXPLÍCITO** (`.\.venv\Scripts\python.exe -m pytest ...`). El `python` global de esta máquina **recoge** los tests y luego falla con `ModuleNotFoundError: dotenv` — medido en R7, siete errores de setup. Y `--basetemp` va **corto** y bajo `$env:TEMP`: con un basetemp bajo un worktree de ruta larga, `test_resumen_cuenta_por_estado` falla por presupuesto de ruta (MAX_PATH) y el fallo **no es del test** (memoria `feedback-pytest-junit-xml-y-dead-ends`).
- **Suite completa verde antes del PR.** El CI del PR solo corre `leak-scan`; pytest es responsabilidad local (memoria `feedback-ci-pr-solo-leak-scan`). Conteo por `--junit-xml`, no por el resumen de la tubería (`feedback-pytest-junit-xml-y-dead-ends`). **La sintaxis es de PowerShell, no de `cmd.exe`:** `--junit-xml="$env:TEMP\fd_junit.xml"`. `%TEMP%` no se expande en el shell normativo de este repo y llega literal al argumento (medido en R7).

---

## File Structure

| Fichero | Responsabilidad | Cambio |
|---|---|---|
| `scripts/repository_cli.py` | Frontal del checkout/checkin | **Modificar (F0):** `run_rclone` pasa por un puerto inyectable; `cmd_*` lo reciben |
| `tests/_dobles/fake_rclone.py` | Doble de Drive con semántica real | **Crear (F0)** |
| `tests/test_repository_cli_orquestacion.py` | Caracterización de `cmd_checkout`/`cmd_checkin` + reproducción de A-1/A-2/B0-2 | **Crear (F0)** |
| `core/casos/workspace_model.py` | `CaseRef`, `WorkspaceMode`, `Capability`, `CaseWorkspace`, `WorkspaceError` | **Crear (F1)** |
| `core/casos/workspace_registry.py` | Registro privado atómico de esta máquina | **Crear (F1)** |
| `core/casos/case_catalog.py` | Catálogo canónico: localizar + `AMBIGUOUS_CASE` | **Crear (F1)** |
| `core/casos/workspace_resolver.py` | Resolución por identidad y por `--case-dir` | **Crear (F1)** |
| `core/casos/case_locator.py` | Localizador legacy | **Modificar (F1):** `path_for(..., strict=)`, `resolve_ref` detecta duplicados |
| `core/config.py` | SSOT de configuración | **Modificar (F1):** `caso_path(..., strict=)`, raíz del registro privado |
| `core/intake_log.py` | Log forense de custodia | **Modificar (F1):** `append_event` recibe workspace/log resuelto; `log_path(case_id)` deprecado; eventos nuevos |
| `scripts/sala_maquina.py` | Primer consumidor real | **Modificar (F1):** `--case-dir` + resolución por workspace; `plan` declarado escritor |
| `tests/test_workspace_model.py`, `…_registry.py`, `…_catalog.py`, `…_resolver.py` | Unitarios de las piezas nuevas | **Crear (F1)** |
| `tests/test_workspace_matriz_contractual.py` | Matriz del §14.1, reutilizable | **Crear (F1)** |
| `tests/test_intake_log.py` | Sanity del set de eventos y de la ruta | **Modificar (F1)** |
| `tests/test_case_locator.py`, `tests/test_sala_maquina_*.py` | Regresión | **Modificar (F1)** según haga falta |
| `PLAN.md`, `docs/MEJORAS_FUTURAS.md`, `docs/ARQUITECTURA.md`, `docs/ARQUITECTURA_RELACIONES.md` | Gobernanza y acoplamiento | **Modificar (Task 11)** |

---

# FASE 0 — banco de pruebas del frontal

> ⚠️ **SUPERSEDIDA (2026-07-29).** Las Tareas 1-3 de abajo eran un boceto. El plan
> ejecutable de la Fase 0 vive en
> **`docs/superpowers/plans/2026-07-29-dual-workspace-fase0-banco-pruebas.md`**:
> 6 tareas, con las interfaces cerradas (`Entorno` inyecta las **cuatro** fuentes
> de no-determinismo, no solo rclone), la semántica del doble especificada y los
> siete `xfail(strict=True)` enumerados uno a uno.
>
> **No ejecutar las Tareas 1-3 de este fichero.** Se conservan como registro de
> cómo se tajó la fase; el hogar del estado sigue siendo `PLAN.md`. **La Fase 1
> (Tareas 4-11) de este plan sigue vigente** y es lo que se ejecuta después.

Sin esto, las Fases 1-3 no son demostrables: la orquestación del checkout/checkin
no tiene un solo test hoy (`tests/test_repository_cli.py` cubre 27 helpers puros
y ningún `cmd_*`).

### Task 1 (supersedida): Puerto inyectable de rclone (refactor puro, cero cambio de comportamiento)

`run_rclone` (`scripts/repository_cli.py:352`) es el único punto de I/O y se
invoca directamente desde `cmd_checkout`, `cmd_checkin`, `_integrar_bandeja`,
`_upload_evidencia`, `_append_evento_drive`, `_pull_caso_md` y `_push_caso_md`.
Mientras sea una función de módulo llamada por nombre, no hay forma de observar
el **orden** de las operaciones, que es exactamente lo que hay que fijar.

**Files:**
- Modify: `scripts/repository_cli.py` (`run_rclone` y sus 7 llamadores)
- Test: `tests/test_repository_cli.py` (añadir al final)

**Interfaces:**
- Produces: `class RcloneRunner` con `run(cmd: list[str]) -> subprocess.CompletedProcess`; instancia por defecto `DEFAULT_RUNNER`.
- `run_rclone(cmd, *, runner: RcloneRunner | None = None)` conserva firma posicional y comportamiento; delega en `runner or DEFAULT_RUNNER`.
- `cmd_checkout(args)` / `cmd_checkin(args)` aceptan `runner` por keyword opcional y lo propagan a **todos** los helpers de I/O que invocan.

- [ ] **Step 1: Write the failing tests**

En `tests/test_repository_cli.py`:

```python
# --- Puerto inyectable de rclone (Fase 0, spec §12) --------------------------

def test_run_rclone_usa_el_runner_inyectado(cli):
    llamadas = []

    class Espia:
        def run(self, cmd):
            llamadas.append(cmd)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

    cli.run_rclone(["rclone", "version"], runner=Espia())
    assert llamadas == [["rclone", "version"]]


def test_cmd_checkout_no_toca_el_runner_por_defecto_si_le_inyectan_uno(cli):
    # Ningún subprocess real: si el runner inyectado no se propaga, esto
    # intentaría ejecutar rclone y el test fallaría por FileNotFoundError o
    # por tardar. La aserción es que TODAS las llamadas pasaron por el espía.
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_repository_cli.py -k "runner" -v
```

Expected: FAILED con `TypeError: run_rclone() got an unexpected keyword argument 'runner'`.

- [ ] **Step 3: Write the implementation**

Introducir `RcloneRunner`, `DEFAULT_RUNNER` y el keyword `runner` en `run_rclone`; propagarlo por parámetro explícito en los 7 llamadores y en `cmd_checkout`/`cmd_checkin`. **No** usar variable global mutable ni monkeypatching como mecanismo de producción.

- [ ] **Step 4: Verify the refactor is behaviour-neutral**

```bash
python -m pytest tests/test_repository_cli.py tests/test_repository_checkout.py -q
```

Expected: los 27 tests previos siguen verdes sin tocarlos.

---

### Task 2 (supersedida): Doble de Drive con la semántica que muerde

Un `Mock` que devuelve `returncode=0` no sirve: los bugs de esta SPEC salen de la
consistencia eventual, de los ficheros Google-native y de los `moveto` que
fallan. El doble tiene que poder mentir igual que Drive.

**Files:**
- Create: `tests/_dobles/fake_rclone.py` (+ `tests/_dobles/__init__.py`)
- Test: `tests/test_fake_rclone.py` (el doble también se prueba)

**Interfaces:**
- `class FakeDrive`: árbol en memoria `{relpath: (bytes, md5|None)}`.
- `class FakeRcloneRunner(drive: FakeDrive, *, sync_lag_reads: int = 0, fallar: dict[str, int] | None = None)`:
  - interpreta `copyto`, `copy`, `moveto`, `lsjson`, `check`, `rmdirs`;
  - `registro: list[list[str]]` conserva el **orden** de todos los comandos (es lo que fijan los tests de orden);
  - `sync_lag_reads`: las N primeras lecturas de un fichero recién escrito devuelven la versión **anterior** (modela el sync lag que hace posible A-1);
  - `md5 is None` para los Google-native;
  - `fallar={"moveto": 1}` hace fallar la enésima operación de ese tipo.
- Helper `escribir_caso_md(drive, fm: dict, cuerpo: str = "# Caso\n")` para sembrar el lock.

- [ ] **Step 1: Write the failing tests** — el doble debe cumplir: `copyto` + `lsjson` coherentes; `sync_lag_reads=1` devuelve lo viejo una vez y lo nuevo después; `md5=None` sobrevive al `lsjson`; `fallar` devuelve `returncode != 0` exactamente en la ocurrencia indicada; `registro` preserva el orden.
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Write the implementation**
- [ ] **Step 4: Verify**

```bash
python -m pytest tests/test_fake_rclone.py -q
```

---

### Task 3 (supersedida): Caracterización de `cmd_checkout` / `cmd_checkin` + reproducción de los bugs

Dos bloques en un solo fichero, separados por comentario de sección: lo que hoy
funciona (red de seguridad) y lo que hoy está roto (`xfail(strict=True)` con el
número de hallazgo).

**Files:**
- Create: `tests/test_repository_cli_orquestacion.py`

**Interfaces:** consume `FakeRcloneRunner` y `cmd_checkout`/`cmd_checkin` con `runner=`.

**Bloque A — comportamiento vigente que no debe romperse:**

- `cmd_checkout` sobre un caso `prestado` aborta con `2` y **no ejecuta ningún `copy`** (el `registro` no contiene `copy`).
- `--dry-run` no escribe el lock ni copia.
- Si el nonce releído no es el propio, aborta con `2` sin copiar.
- Si `rclone copy` falla, revierte el lock a `disponible` y devuelve `1`.
- Orden observado hoy en el camino feliz: lock → `copy` → `MANIFEST_CHECKOUT.json` → evento `case_checkout`.
- `cmd_checkin` con ruta local inexistente devuelve `2`.
- Con conflictos: escribe estado `conflicto` y **no** libera el lock.
- Con borrados y sin `--yes`: devuelve `3` y no toca nada.
- Si la copia falla: no propaga borrados y devuelve `1`.

**Bloque B — bugs reproducidos, `xfail(strict=True)`:**

- `A-1 · doble titular`: dos `cmd_checkout` cuyas lecturas de CP0 ocurren antes de que ninguno escriba (`sync_lag_reads=1`) → hoy **ambos** devuelven `0`; se exige exactamente uno.
- `A-1 · rollback ajeno`: el rollback tras un `copy` fallido limpia el lock sin comprobar que el nonce vigente sigue siendo el propio.
- `A-2 · orden del checkin`: en el camino verde con bandeja no vacía, el `registro` muestra `check` **antes** de los `moveto` de la bandeja y el evento `case_checkin` **antes** de ellos; se exige integrar → verificar → evento → liberar.
- `A-2 · bandeja fallida libera el lock`: con `fallar={"moveto": 1}` sobre la bandeja, hoy el lock se libera igual.
- `A-2 · checkin reentrante duplica evento`: dos `cmd_checkin` seguidos dejan dos `case_checkin` en el log.
- `B0-2 · el log canónico se reescribe`: un log sembrado con una línea final sin `\n` y con un byte no UTF-8 sale normalizado y con `U+FFFD` tras un solo evento.
- `B0-2 · el baseline no cubre el log`: el `MANIFEST_CHECKOUT.json` generado **no** contiene entrada para `00_Input/_intake_log.jsonl`.

- [ ] **Step 1: Write the tests** (bloque A en verde, bloque B en `xfail`)
- [ ] **Step 2: Run and confirm the split**

```bash
python -m pytest tests/test_repository_cli_orquestacion.py -q -rxX
```

Expected: bloque A PASSED; bloque B **xfailed** (ninguno `xpassed` — con `strict=True` un `xpass` es fallo).

- [ ] **Step 3: No hay implementación en esta tarea.** Si algo del bloque A falla, es un bug vivo que no conocíamos: **para y repórtalo** antes de continuar.

**Criterio de salida de la Fase 0:** la matriz del §14.1 es ejecutable para el ciclo checkout/checkin y las brechas 8-15 del §11 tienen un test que las reproduce o las documenta.

---

# FASE 1 — núcleo de workspace

### Task 4: Modelo puro — `CaseRef`, modos, capacidades y errores

Es la pieza que todas las demás consumen y no tiene dependencias: primero.

**Files:**
- Create: `core/casos/workspace_model.py`
- Test: `tests/test_workspace_model.py`

**Interfaces:**
- `@dataclass(frozen=True) CaseRef`: `case_id: str | None`, `w_code: str | None`, `canonical_ref: str | None`. Al menos uno de `case_id`/`w_code` no vacío, o `ValueError`. `normalizar()` de clase para el W-code (mayúsculas, `strip`).
- `class WorkspaceMode(StrEnum)`: `DRIVE_ACTIVE`, `LOCAL_CHECKOUT`, `LOCAL_SCRATCH`, `BLOCKED_FOREIGN_CHECKOUT`, `BLOCKED_CONFLICT`.
- `class Capability(StrEnum)`: las 8 del §5.4.
- `CAPACIDADES_POR_MODO: dict[WorkspaceMode, frozenset[Capability]]` — la tabla del §5.4 como dato, no como `if`.
- `@dataclass(frozen=True) CaseWorkspace`: `case_ref`, `mode`, `working_root: Path | None`, `canonical_ref`, `checkout_user`, `checkout_maquina`, `checkout_nonce`, `checkout_timestamp`, `capabilities: frozenset[Capability]`, `validado_en: str`, `procedencia: str`. Métodos: `permite(cap) -> bool`; `exigir(cap) -> None` (lanza `CapabilityDenied`); `es_mutable -> bool`.
- `class WorkspaceError(Exception)` con `codigo: str` + subclases por cada código del §10 (`CaseLocked`, `LocalWorkspaceMissing`, `LockMismatch`, `LockNotMine`, `CaseConflict`, `AmbiguousCase`, `RuntimeCannotAccessWorkspace`, `CapabilityDenied`, `CanonicalMutationDeferred`, `CheckoutCancelledElsewhere`, `WorkspaceUnderCatalogRoot`, `AuditBaselineMissing`).
- `str(error)` **nunca** incluye rutas locales (§16): el mensaje se construye con W-code, código, titular y fecha.

- [x] **Step 1: Write the failing tests** — `CaseRef` sin identidad lanza; `working_root is None` con modo mutable es incoherente y lanza; `exigir` lanza `CapabilityDenied` con `codigo == "CAPABILITY_DENIED"`; un `CaseWorkspace` es inmutable (`dataclasses.FrozenInstanceError`).

  **La tabla se prueba por IGUALDAD COMPLETA, no por negativos sueltos** (R7/H7-10). Los tres negativos que este Step tenía —`BLOCKED_*` sin `WRITE_CASE` ni `INGEST`, `LOCAL_CHECKOUT` sin `MUTATE_CANONICAL`— los pasa también una tabla **casi vacía**, que es el modo de fallo caro: difiere el descubrimiento a una fase posterior. Por tanto: `CAPACIDADES_POR_MODO[modo] == esperado[modo]` parametrizado por los cinco modos, con las **ocho** capacidades del §5.4 nombradas en positivo donde corresponda (`read_case`, `write_case`, `ingest`, `generate_derivatives`, `mutate_canonical`, `checkout`, `checkin`, `promote`).

  **Mutación obligatoria:** ocho mutantes, uno por capacidad, cada uno quitándola o intercambiándola en un modo. Los ocho deben morir. Una tabla es un dato, y un dato solo queda contratado por la igualdad que lo fija (memoria `feedback-mutacion-vale-por-su-mutante`).

  **Los doce errores del §10, y sus mensajes** (R7/H7-12). El canario «no contiene el separador de unidad de Windows» solo detecta `:\`: dejaba pasar `C:/...`, `\\servidor\...`, `/home/...` y cualquier ruta relativa. Se parametrizan **las doce subclases** contra un juego de canarios —Windows con las dos barras, UNC, POSIX, relativa— más nombre, email y dirección (§16), exigiendo ausencia de todos. Y se prueban las otras dos reglas del §10, que no estaban en ningún Step: el mensaje **declara que no hubo efecto** cuando el camino es de bloqueo, y **nunca sugiere reintentar contra Drive**. Se comprueba el `codigo` exacto de cada una de las doce, no solo el de `CapabilityDenied`.
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Write the implementation**
- [x] **Step 4: Verify**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_workspace_model.py -q
```

**✅ CONSTRUIDO** en `d6cee04` (modelo + tests) y `de14b20` (el hueco que encontró un mutante
superviviente: un `w_code` en blanco se normalizaba a cadena vacía en vez de a `None`, así que
pasaba por identidad válida).

**Lo que R7 le cambió después de estar construido.** El task se levantó **antes** de que R7
adjudicara, así que sus dos hallazgos se comprobaron contra el código ya escrito, no contra el plan:

- **H7-10 (tabla de capacidades) — ya cubierto.** `test_la_matriz_de_capacidades_es_la_del_spec`
  compara el diccionario **entero** contra una transcripción a mano, así que un mutante que quite o
  intercambie cualquiera de las ocho capacidades en cualquiera de los cinco modos muere ahí. La
  igualdad completa que el hallazgo pedía ya estaba; no hicieron falta ocho mutantes sueltos, porque
  la igualdad los mata a todos.
- **H7-12 (mensajes de error) — hueco real, y doble.** El canario era **uno solo** —una ruta de
  Windows— y sus dos asertos (`[A-Za-z]:[\/]` y la contrabarra) cazaban **3 de 8** casos: Windows
  con las dos barras y UNC. Se le escapaban POSIX puro, la ruta relativa y las tres de PII del §16;
  y como solo **inyectaba** una ruta Windows, esos cinco no se ejercitaban en ningún caso. Ampliado
  a **ocho canarios × doce clases**, con fragmentos parciales además de la copia literal, y la
  segunda regla del §10 —no empujar a reintentar contra Drive— extendida de **una** clase a las
  doce. Verificado por mutación: filtrar `detalle` tal cual mata los cinco canarios que antes
  pasaban, por las doce clases.

**Y una frontera que se respeta a propósito:** *no* se prueba que el mensaje no lleve un nombre. El
§10.3 manda construirlo con «W-code, código, titular y fecha», o sea que el `titular` va dentro por
diseño. Un canario de «ningún nombre» contradiría la fuente en vez de protegerla, así que el vector
que se vigila es `detalle`.

---

### Task 5: Registro privado de workspaces (atómico, fuera del repo y de Drive)

**Files:**
- Create: `core/casos/workspace_registry.py`
- Modify: `core/config.py` (raíz por defecto del registro)
- Test: `tests/test_workspace_registry.py`

**Interfaces:**
- Raíz: `settings.workspace_registry_dir`, por defecto `%LOCALAPPDATA%\FeesDefender\workspaces` y override por `FEESDEFENDER_WORKSPACE_REGISTRY`. **Nunca** bajo el repo ni bajo `CASOS_ROOT` (comprobado en el arranque; si coincide, lanza).
- `@dataclass(frozen=True) WorkspaceEntry`: `case_id`, `w_code`, `canonical_ref`, `local_path: Path`, `nonce`, `maquina`, `tipo: Literal["checkout","scratch"]`, `ultima_validacion: str`, `schema: int`.
- `class WorkspaceRegistry`: `cargar()`, `buscar(ref: CaseRef) -> list[WorkspaceEntry]`, `alta(entry)`, `baja(ref)`, `revalidar(ref, *, local_path)`.
- **Forma del registro: UN FICHERO POR ENTRADA, nombrado por W-code** — `<w_code>.json` bajo la raíz del registro. **Esto se decide aquí y no después** (R7/H7-04). Un JSON agregado —la lectura natural de `cargar()` en singular— tiene dos problemas que un `os.replace` no resuelve: (1) *lost updates*, dos procesos cargan el mismo estado y el último reemplazo borra el alta del primero; y (2) el mutex de **D2** (§24 de la spec de apertura) es un lockfile `O_CREAT|O_EXCL` con **namespace por W-code** que vive en este registro, y locks por W-code **no se excluyen entre sí** sobre un fichero agregado. Cambiar la forma después arrastra cuarentena, migración y tests. Un fichero por W-code hace que la atomicidad por entrada baste y que los lockfiles de D2 convivan sin colisión.
- Escritura atómica: fichero temporal en el mismo directorio + `os.replace`. Nunca escritura in-place.
- **Un registro corrupto NO se convierte en «registro vacío»: FALLA CERRADO** (R7/H7-02). Los bytes se preservan renombrando a `*.corrupto.<ts>` (el `ts` lo pasa el llamante: nada de reloj implícito en la lógica pura), pero `cargar()` **lanza** `RegistryUnreadable`, no devuelve `[]`. Devolver vacío borra la diferencia entre «no había workspace local» y «no puedo saber qué había», y esa segunda es precisamente la que el resolver necesita para **no** autorizar `DRIVE_ACTIVE` sobre un caso que quizá está prestado. La cuarentena salva los bytes; la decisión de autorización ya habría fallado abierta. Contraría el «Fail closed» del §3 de la spec dual y la constraint global de este plan.
- `schema` distinto del soportado → error explícito, no adivinar.

- [x] **Step 1: Write the failing tests** — dos entradas para el mismo `w_code` se devuelven **ambas** (la desambiguación es del resolver, no del registro); `alta` sobre una ruta que ya está registrada para otro caso lanza; ruta del registro bajo `CASOS_ROOT` → lanza; el fichero **no** contiene secretos ni contenido de documentos; `schema` no soportado → lanza; `revalidar` usa el `ts` **inyectado** y no un reloj propio.

  **La atomicidad se prueba ATRAVESANDO LA API** (R7/H7-03). La versión anterior de este Step decía «simulado escribiendo el temporal y no renombrando», que **no llama a `alta()`**: ese test pasa aunque producción escriba el JSON destino in-place y jamás use `os.replace`. Prueba correcta: sembrar bytes válidos, parchear `os.replace` **en el módulo de producción** para que lance, invocar `alta()`, y exigir tres cosas — que la excepción salió, que el destino conserva **exactamente** los bytes anteriores, y que el temporal quedó en el mismo directorio. **Mutante obligatorio:** sustituir `os.replace(tmp, dst)` por `dst.write_text(...)` debe dejar el test ROJO.

  **Fallo cerrado del registro corrupto:** un registro truncado que contenga el comienzo de una entrada local hace que `cargar()` lance `RegistryUnreadable`; el fichero original sigue en `*.corrupto.<ts>` con sus bytes intactos; y `resolver_por_identidad` sobre un canon `disponible` devuelve **error estructurado y cero efectos**, nunca `DRIVE_ACTIVE` (esa segunda mitad se prueba en el Task 7, con este error ya disponible).

  **Concurrencia:** dos procesos, barrera después de `cargar()`, `alta()` simultánea de W-codes **distintos**; al terminar deben existir **ambas** entradas. Y un test de layout que demuestre que un lockfile de D2 en la raíz del registro no se lee como entrada ni se manda a cuarentena.
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Write the implementation**
- [x] **Step 4: Verify**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_workspace_registry.py -q
```

**✅ CONSTRUIDO.** 22 tests, y **once mutantes que mueren cada uno POR SU FRONTERA** —no
«alguno falla»: el arnés comprueba que el test asesino sea el que le toca. Se hizo así
porque los 22 pasaron a la primera, y un test que nunca se vio fallar por su propia razón
no prueba nada; es la lección de H7-07 aplicada al propio trabajo. Las once fronteras:
atomicidad, temporal en el mismo directorio, fallo cerrado, cuarentena que preserva bytes,
`ts` inyectado en el nombre de la cuarentena, layout por W-code, `*.json` (el lockfile de
D2 no es una entrada), devolver **ambas** entradas, reloj inyectado en `revalidar`, guarda
de raíz, y ruta duplicada.

**Tres errores nuevos, y el §10 pasa de 12 a 15 códigos.** `REGISTRY_UNREADABLE` lo fuerza
H7-02; `SCHEMA_NO_SOPORTADO` y `RUTA_YA_REGISTRADA` los pide este contrato. Van al
**modelo** y no al registro: el resolver los muestra, así que les aplican las reglas de
mensaje del §10 y los ocho canarios del §16 — definirlos aquí los habría dejado fuera de
`errores_conocidos()`, que es el hueco que R7 castigó en H7-12. La tabla del §10 admitía
las filas sin reabrir nada, porque dice «Como mínimo».

**Desviación declarada del plan: `core/config.py` NO se toca.** Este task decía «Modify:
`core/config.py` (raíz por defecto del registro)», y la raíz acabó en
`workspace_registry.raiz_por_defecto()`. El motivo es concreto: `Settings` es un
`@dataclass(frozen=True)` cuyos campos se evalúan **en el import**, así que un
`workspace_registry_dir` ahí queda congelado y solo se puede redirigir con
`importlib.reload(core.config)` —que la barrera permite pero desaconseja, y que arrastra
el gotcha de `reload` + `isinstance`—. `raiz_por_defecto()` lee el entorno de forma
perezosa. Y la clase **no** se cae a ese default: recibe la raíz inyectada, porque la
barrera de test cubre rclone y `subprocess` pero no las escrituras a `%LOCALAPPDATA%`, y
sin default no hay dónde caerse.

---

### Task 6: `CaseCatalog` + modo estricto del localizador (cierra A-5 y A-8)

Aquí se mata el fallback silencioso. Es el cambio con más superficie de
regresión de la Fase 1.

**El inventario, medido por AST y no por `grep`** (R7/H7-14). La versión anterior decía «los
llaman 80 ficheros», y ese 80 sale de contar ficheros que **mencionan** la subcadena —imports,
comentarios, docstrings y 25 ficheros de test incluidos—, no llamadas. Contando nodos
`ast.Call`:

| Símbolo | Llamadas | Ficheros |
|---|---|---|
| `path_for` | 39 | 13 |
| `caso_path` | 112 | 44 |
| **unión, todo el repo** | **151** | **55** (43 producción + 12 tests) |
| unión, solo producción | 95 | **43** |

La superficie real de migración es de **43 ficheros de producción**. El Step 1 exige emitir ese
inventario con un script AST versionado (fichero, línea, símbolo, producción/test), porque es a
la vez la lista de trabajo y el insumo del guard de `legacy_unresolved`.

**Files:**
- Create: `core/casos/case_catalog.py`
- Modify: `core/casos/case_locator.py` (`path_for`, `resolve_ref`), `core/config.py` (`caso_path`)
- Test: `tests/test_workspace_catalog.py`, `tests/test_case_locator.py` (añadir)

**Interfaces:**
**El booleano `strict` era la forma equivocada, y por eso el plan se contradecía a sí mismo**
(R7/H7-01, el CRÍTICO). Su *Goal* y su criterio de salida (2) exigen que ningún camino cree un
directorio bajo `CASOS_ROOT` para una identidad que el catálogo no conoce; su sección final
declaraba no invertir el default «hasta la Fase 4». Las dos cosas no caben, y la spec zanja el
empate: la Fase 1 es donde «`caso_path` deja de devolver rutas inexistentes y ningún escritor
hace `mkdir` de la raíz» (§Fase 1 de la spec dual, y D1 en los mismos términos).

El plan quedó atrapado eligiendo entre romper el alta e invertir el default porque **un flag de
dos valores tenía que servir a tres intenciones distintas**. Se separan:

| Intención | API | Ausencia del caso | Quién la usa |
|---|---|---|---|
| **Localizar** lo que debe existir | `localizar(case_id) -> Path` | **lanza** `LocalWorkspaceMissing` | todo lector y todo escritor de un caso ya abierto |
| **Preguntar** si existe | `buscar(case_id) -> Path \| None` | devuelve `None` | los detectores de ausencia con rama elegante |
| **Nombrar** destino de un alta | `destino_de_alta(case_id) -> Path` | es su caso normal | **solo** `case_manager.ensure_case` |

- `path_for(case_id: str, *, strict: bool = True) -> Path`: **default `True` ya en esta fase**, como manda la spec. `strict=False` sobrevive únicamente como escotilla legacy explícita, inventariada y con guard que impide que crezca.
- `caso_path(case_id, *, strict: bool = True)` propaga el keyword.
- `destino_de_alta` **no pasa por el localizador estricto**: nombra una ruta que por definición todavía no existe. Es la única puerta por la que se crea, y es explícita en el nombre.

**Los 27 detectores de ausencia, medidos** (aportación del adjudicador, que el revisor no vio). Hay una tercera clase de llamador que ni crea ni lee un caso existente: usa la ruta del fallback **para saber si el caso existe** —`caso_path(x) / "_caso.md"` y luego `if not .exists(): <rama elegante>`—. Son **27 sitios en 17 ficheros**. Con `strict=True` no reciben `False`: reciben una excepción, y su rama elegante desaparece. Medido en vivo sobre `scripts/abrir_caso.py`: hoy un `--case-id` inexistente da `[ERROR] Caso no encontrado para --case-id 'W-NOEXISTE'` con salida 1; con `strict=True` aplicado sin más, da un `FileNotFoundError` sin capturar y **sin una sola línea de salida**. Esos 27 migran a `buscar()`, no a `localizar()`. Sin esta tercera API, invertir el default degrada la interfaz de dos entrypoints (`abrir_caso`, `crm_ficha`) de un error legible a una traza.
- `resolve_ref(ref)` conserva firma, **pero** si dos casos del catálogo comparten `meta.id_go` lanza `AmbiguousCase` en lugar de devolver el primero por orden de escaneo.
- `class CaseCatalog`: `localizar(ref: CaseRef) -> Path` (estricto siempre), `estado_compartido(ref) -> dict` (lee el `_caso.md` del canon vía `read_case_meta`), `es_proyeccion_local(case_dir) -> bool` (marca `meta.proyeccion_local`), `bajo_catalogo(path) -> bool` (para `WorkspaceUnderCatalogRoot`).
- Un `case_dir` marcado como proyección local **se excluye** de `list_cases()`.

- [ ] **Step 1: Write the failing tests** — `localizar()` de un caso ausente lanza `LocalWorkspaceMissing` y **no crea nada** (hash del árbol antes/después, idéntico); `buscar()` del mismo caso devuelve `None` y tampoco crea nada; `destino_de_alta()` devuelve la ruta y **tampoco** crea nada (nombrar no es crear); dos casos con el mismo `id_go` → `AmbiguousCase`; una carpeta con `meta.proyeccion_local: true` no aparece en `list_cases()` ni gana la resolución por W-code; `bajo_catalogo` reconoce un subdirectorio de `CASOS_ROOT` y rechaza uno de fuera; `path_for(strict=False)` sigue comportándose exactamente como hoy (la escotilla legacy).

  **La propagación del keyword se prueba, no se supone** (R7/H7-01): un test llama `config.caso_path(ausente)` **sin argumentos** y exige `LocalWorkspaceMissing` — si `caso_path` se olvida de propagar, ese test es el único que lo caza.

  **Barrido parametrizado de escritores, sobre el inventario AST del Step 0:** para cada escritor de producción, invocarlo con un W-code inexistente y exigir `LocalWorkspaceMissing` **más** hash de `CASOS_ROOT` idéntico antes y después. Es el test que convierte el criterio de salida (2) en algo que muere si alguien lo rompe, en vez de una frase. Incluye a `catalogo_documental.save_catalog`, que hoy hace `mkdir(parents=True)` sobre la ruta resuelta.

  **`ensure_case` sigue creando, por la puerta explícita:** un test exige que el alta de un caso nuevo funciona igual que hoy, y que lo hace vía `destino_de_alta` — mutar `ensure_case` para que llame a `localizar()` debe dejarlo ROJO.
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Write the implementation**
- [x] **Step 4: Verify** — aquí es donde puede romperse algo ajeno:

```bash
python -m pytest tests/test_case_locator.py tests/test_workspace_catalog.py -q
python -m pytest -q --tb=short
```

Expected: suite completa verde. Si un test ajeno falla, **no** es del entorno: es un consumidor de `path_for` que dependía del fallback (memoria `feedback-test-roto-culpar-al-entorno`). Diagnostícalo y repórtalo.

---

**Estado del Task 6 — ✅ COMPLETO.**

Se separa así porque el task mezclaba dos piezas con riesgos muy distintos, y solo una
tocaba los 43 ficheros de producción.

**✅ Construido y verificado (PR #231 + commits posteriores):**

- Las **tres intenciones** — `localizar()` lanza, `buscar()` devuelve `None`,
  `destino_de_alta()` admite la ausencia. 7 mutantes, cada uno muerto por su frontera.
- El **alta por la puerta explícita** (`ensure_case` → `destino_de_alta`).
- **Los 33 detectores migrados**, en cuatro clases que hubo que leer una a una: 19
  detectores de verdad, 6 que ya lanzaban (pasan a `localizar` y ganan el error del §10),
  5 constructores que no se tocan, y 3 con *seam* que usan el patrón `try/except` sobre el
  binding del módulo.
- **El default invertido**, que es el criterio de salida (2) de la Fase 1. Radio medido
  **dos veces**: 377 rotos antes de migrar, **18** después.
- **El guard permanente** (`tests/test_guard_localizador.py`), que **no depende de números
  de línea** —la lista de trabajo indexada por línea caducó a mitad de la propia
  migración— y lleva su prueba de mutación. Censo de `strict=False` en producción: **CERO**.
- Seis fugas del **§16** cerradas por el camino, ninguna buscada.

**✅ Y el `CaseCatalog`, que cierra el A-8:**

- `core/casos/case_catalog.py` con las cuatro preguntas del §5.1 — y ninguna más: no
  decide sobre qué copia se trabaja (Task 7) ni conoce las copias locales (el registro).
- **El A-8 cerrado por las dos puertas.** Medido antes de escribir nada: con dos
  carpetas declarando `id_go: W-DUPLI`, `resolve_ref` devolvía «Calle A» **sin aviso**,
  elegida por orden de escaneo — renombrar una carpeta cambiaba la respuesta. Ahora
  lanza `AmbiguousCase`, y se cierra **también** `case_locator.resolve_ref`, que era la
  que elegía en silencio. Cerrar solo la puerta nueva habría dejado viva la dañina.
- **La marca de proyección va en la misma pieza**, y no es un extra: el §6.3 prevé que
  la copia local lleve su `_caso.md` con el **mismo** W-code, así que sin la marca el
  propio diseño fabricaría la ambigüedad que la regla detecta. El filtro va en los
  **tres** caminos de `list_cases()` — una proyección puede vivir bajo una ciudad.
- `estado_compartido` **reutiliza** `config.ESTADO_REPO_*` y los lectores puros de
  `repository_checkout`. Dos vocabularios para el mismo hecho es como nacen las
  divergencias.
- `bajo_catalogo` compara por **componentes de ruta**, no por prefijo de cadena:
  `CASOS_x` no está bajo `CASOS`, y confundirlos daría por bueno un destino de checkout
  fuera de la biblioteca.

17 tests y 8 mutantes, cada uno muerto por su frontera. **El Task 7 deja de estar
bloqueado:** ya tiene el `estado_compartido` y el `bajo_catalogo` que consume.

---

### Task 7: `CaseWorkspaceResolver` — la matriz del §7 en una sola pieza

**Files:**
- Create: `core/casos/workspace_resolver.py`
- Test: `tests/test_workspace_resolver.py`

**Interfaces:**
- `class CaseWorkspaceResolver(catalog: CaseCatalog, registry: WorkspaceRegistry, *, usuario: str, maquina: str, ahora: str)` — el reloj y la identidad **se inyectan**: la pieza es pura y determinista.
- **Y eso se contrata, no se enuncia** (R7/H7-11). Un constructor puede aceptar los tres argumentos y luego ignorarlos llamando a `datetime.now()`, `getpass.getuser()` o `socket.gethostname()` por dentro; el Step 1 anterior comprobaba resultados de escenarios, que pasan igual. Prueba: parchear los tres **globales** para que **lancen**, resolver, y exigir que no salte nada; luego resolver dos veces con entradas idénticas y exigir igualdad completa del `CaseWorkspace`; luego variar **solo** una inyección y exigir que cambien únicamente los campos que dependen de ella.
- `resolver_por_identidad(ref: CaseRef, *, drive_accesible: bool) -> CaseWorkspace` — implementa §7.2 paso por paso.
- `resolver_por_ruta(path: Path, *, drive_accesible: bool) -> CaseWorkspace` — implementa §7.1.
- Ambos **lanzan** `WorkspaceError` en los caminos de bloqueo; no devuelven un modo `BLOCKED_*` como valor de retorno normal salvo cuando el llamante pide diagnóstico explícito. Ese `diagnostico: bool = False` **va en las dos firmas de arriba**, que no lo declaraban: la excepción se mencionaba en prosa y no existía en la interfaz (R7/H7-11).
- `mutate_canonical=False` en el camino offline (§7.1.5 / §7.2.9).

- [x] **Step 1: Write the failing tests** — una fila por escenario del §14.1, más: `prestado` por otra máquina → `CaseLocked` con titular y fecha en el mensaje y **sin** ruta local; `prestado` propio con nonce distinto → `LockMismatch`; `prestado` propio sin entrada de registro → `LocalWorkspaceMissing` (no se adopta solo, §15); `conflicto` → `CaseConflict` en cualquier modo; Drive inaccesible con **un** checkout verificado → `LOCAL_CHECKOUT` sin `MUTATE_CANONICAL`; Drive inaccesible con dos candidatos → `AmbiguousCase`; scratch cuyo W-code colisiona con un caso publicado → `AmbiguousCase` que exige `--case-dir`; `--case-dir` a una ruta bajo `CASOS_ROOT` → `WorkspaceUnderCatalogRoot`; `--case-dir` donde identidad, manifest y registro se contradicen → aborta.
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Write the implementation**
- [x] **Step 4: Verify**

```bash
python -m pytest tests/test_workspace_resolver.py -q
```

---

**Estado del Task 7 — ✅ COMPLETO.** `core/casos/workspace_resolver.py`, 23 tests, y
**18 mutantes que mueren cada uno por su propia frontera**.

**La prueba de mutación encontró un defecto real, no tests flojos.** De las 18 fronteras,
**cinco no estaban contratadas**, y una de ellas era un mecanismo que no hacía nada:

- **La resta de capacidad para el offline era inerte.** Quitaba `MUTATE_CANONICAL` de
  `local_checkout`, y ese modo **nunca la tuvo** — solo la tiene `drive_active`. El test
  lo confirmaba pasando con el mecanismo desactivado. Lo que un modo local puede hacer
  contra el canon es **`checkin`** (cerrar el ciclo) o **`promote`**, así que tal como
  estaba **un checkout offline seguía anunciando `CHECKIN`**: el sistema habría dejado
  intentar publicar sin Drive, justo lo que el §7.1.5 prohíbe. Se retira ahora
  `CAPACIDADES_DE_CANON` = {`mutate_canonical`, `checkin`, `promote`}.
- **Dos tests pasaban por el camino equivocado.** El de «offline con dos candidatos» no
  creaba el caso en el catálogo, así que la ambigüedad la levantaba **otra** guarda
  (`_solo_local`) y la del camino offline no se ejercitaba nunca. El de «ruta que no
  existe» usaba una ruta sin registrar, así que la rechazaba la guarda del **registro**,
  no la de existencia. Mismo patrón: **el test pasaba, pero por una razón distinta de la
  que decía comprobar** — y con el verde idéntico, sin mutación no se ve.

**Dos decisiones de diseño:**

- **Restar una capacidad no es inyectarlas.** El modelo prohíbe inyectar —un llamador
  podría fabricarse un `blocked_*` con permiso de escritura— pero restar solo puede
  hacerlo **menos** poderoso. La asimetría es lo que permite expresar el offline sin
  abrir el agujero, y hay test que la fija sobre los cinco modos.
- **Bloquear lanzando, no devolviendo.** Un motor que va a escribir no debe recibir un
  valor que *parezca* un workspace y no lo sea. La excepción es `diagnostico=True`, para
  quien va a **pintar** el estado en vez de operar.

**Un test mío que estaba mal, y se conserva el razonamiento:** escribí que el conflicto
debía bloquear «en cualquier modo». Falso — el §7.2 lee el estado compartido en el paso
(3) **solo si Drive está accesible**. El hueco lo cierra el §7.1 por el otro lado: el
checkin revalida el nonce contra Drive, así que el conflicto aflora al publicar. Está
explicado en el propio test en vez de borrado.

---

### Task 8: `core.intake_log` escribe donde están los bytes (cierra B0-1)

La tarea más importante del plan. Sin ella, `--case-dir` es una máquina de
split brain.

**Files:**
- Modify: `core/intake_log.py`
- Test: `tests/test_intake_log.py`

**Interfaces:**
- `append_event(destino, event, *, details=None, actor=None, ts=None, case_id=None) -> Path`, donde `destino` es un `CaseWorkspace` **o** un `Path` al árbol del caso ya resuelto. El `case_id` del registro sale del workspace; el keyword existe solo para el camino `Path`.
- **`log_path(case_id)` SE RETIRA en esta fase**, no se deprecia hasta la Fase 4 (R7/H7-01). La spec lo dice sin matices al definir la Fase 1: «`core.intake_log` migrado en esta fase (B0-1): `append_event` recibe el workspace o el log ya resuelto; `log_path(case_id)` **se retira**». Dejarlo vivo con `DeprecationWarning` conserva exactamente la vía que parte la custodia en dos, que es el defecto que este task existe para cerrar. `log_path_de(case_dir: Path) -> Path` es la única vía.
- **`append_event` deja de crear la raíz del caso.** Si `00_Input/` no existe bajo el destino, lanza `LocalWorkspaceMissing`: crear un expediente es trabajo de la apertura, no de la auditoría. Solo crea el fichero de log.
- Altas en `INTAKE_EVENTS` (**28 → 33**): `scratch_creado`, `scratch_promovido`, `checkout_adoptado`, `conflicto_resuelto`, `checkout_cancelado_unilateral`. `pendiente_checkin` **se conserva** (lectura histórica) con comentario de que su emisión se retira en la Fase 2.
- **La aritmética estaba rancia y era peligrosa** (R7/H7-06). El plan decía «27 → 32», pero el repo tiene **28** eventos desde que `contenido_adjuntos` entró el 2026-08-04, **después** de escribirse este plan. Verificado: `len(INTAKE_EVENTS) == 28`. Sumar los cinco da **33**. Un `assert len(...) == 32` habría forzado al implementador a **borrar en silencio un evento histórico** para cuadrar el número — y en un log forense retirar vocabulario rompe la lectura de lo ya escrito. El aserto es doble: `len(INTAKE_EVENTS) == 33` **y** comparación de conjuntos —los 28 actuales son subconjunto estricto y la diferencia es exactamente los cinco nuevos—, que es lo que impide cuadrar la cifra por resta.

- [x] **Step 1: Write the failing tests**

```python
def test_append_event_no_crea_la_raiz_del_caso(tmp_path):
    # El bug B0-1: hoy mkdir(parents=True) fabrica el expediente entero.
    destino = tmp_path / "caso_que_no_existe"
    with pytest.raises(LocalWorkspaceMissing):
        append_event(destino, "upload_manual", details={}, case_id="W-TEST99")
    assert not destino.exists()


def test_append_event_escribe_en_el_arbol_del_workspace_no_en_casos_root(tmp_path, monkeypatch):
    # Con --case-dir, el evento cae junto a los bytes. Si alguien reintroduce
    # caso_path aquí, este test lo caza.
    #
    # R7/H7-05: este cuerpo era literalmente `...`, que es una expresión Python
    # válida. El test PASABA sin llamar a append_event, sin sembrar CASOS_ROOT y
    # sin comprobar ningún fichero — verde en la frontera central del plan, en el
    # task que él mismo llama «la más importante».
    canon = tmp_path / "CASOS"                      # el sentinel que NO debe tocarse
    (canon / "BaRS9 - Prueba - (W-TEST99) - Vuelta" / "00_Input").mkdir(parents=True)
    monkeypatch.setattr(config.settings, "casos_root", canon)
    antes = hash_arbol(canon)

    scratch = tmp_path / "fuera" / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
    (scratch / "00_Input").mkdir(parents=True)

    destino = append_event(scratch, "upload_manual", details={}, case_id="W-TEST99")

    assert scratch in destino.parents          # el log cae junto a los BYTES
    assert destino.read_text(encoding="utf-8").strip()
    assert hash_arbol(canon) == antes          # y el canon queda INTACTO

# Mutante obligatorio: sustituir el destino por `caso_path(case_id)` deja este
# test ROJO por la última aserción. Si no muere, el test no contrata nada.
```

Más: `log_path(case_id)` **ya no existe** y su desaparición se prueba (`AttributeError` o `ImportError` al referenciarlo); el set de eventos pasa a **33** con el doble aserto de arriba **y se actualiza el `expected` completo** del test existente; un evento desconocido sigue lanzando `ValueError`.

- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Write the implementation** — migrar además **todos** los llamadores internos de `append_event(case_id, …)` que ya disponen del `case_dir`. Los que no lo tengan se dejan en el camino legacy con comentario `# legacy_unresolved (Fase 4)`, nunca «arreglados» a medias.
- [x] **Step 4: Verify**

```bash
python -m pytest tests/test_intake_log.py -q
python -m pytest -q --tb=short
```

---

**Estado del Task 8 — ✅ COMPLETO.** 24 tests y **7 mutantes que mueren cada uno por su
frontera**, incluido el que el plan declaraba **obligatorio** (sustituir el destino por
`caso_path(case_id)` deja rojo el test del corazón del task).

**Migrados 7 de 14 llamadores**, y la cifra está contada por AST, no estimada. Mi criterio
inicial —«tiene `case_dir` en la FIRMA»— era demasiado estrecho: dejaba fuera a `apply`,
`reforzar` y `_registrar_atomizado`, que lo resuelven en su primera línea. Los 7 restantes
quedan `legacy_unresolved` (Fase 4), y ya **no son peligrosos**: desde el paso 5 del Task 6
`caso_path` es estricto, así que el camino legacy no puede materializar un fantasma.

**Un test fijaba el defecto como comportamiento deseado.** `test_append_event_crea_subcarpeta_00_input_si_falta`
**exigía** que `append_event` creara `00_Input`, «útil en escenarios de migración». Esa
comodidad **es** la máquina de expedientes fantasma —el bug que ya ocurrió con W-02ZIIF—.
La suite estaba verde defendiendo el B0-1, y ninguna cobertura adicional lo habría
detectado: el problema no era falta de tests, era que apuntaban al lado contrario. Se
invirtió dejando escrito qué decía antes y por qué estaba mal.

**La migración estaba a medias sin que yo lo viera.** `append_event` podía escribir junto a
los bytes, pero `read_events` seguía exigiendo pasar por el catálogo — y con `--case-dir`
el catálogo **no conoce** esa copia, así que lo recién escrito era **ilegible**. Lo destapó
un test ajeno. Se añadió `read_events_de(case_dir)`, hermano de `log_path_de`.

**`read_events(case_id)` conserva su firma a propósito:** es un lector, nunca causó el
B0-1, y cambiarla tocaría 46 sitios de test sin cerrar ningún defecto.

**Tres fronteras no estaban contratadas** y lo dijo la mutación: el camino legacy tenía
**dos** guardas y el test no distinguía cuál actuaba; `log_path_de` se probaba sobre un
árbol que ya existía, así que un `mkdir` dentro habría sido no-op; y `read_events_de` se
probaba de rebote. De paso salió un hueco real en `_w_code_de`, que solo reconocía la
forma entre paréntesis: un **W-code suelto** —entrada legítima— no se identificaba en el
mensaje de error.

**Anotado y NO arreglado (ajeno a este task):** producción envuelve `append_event` en
`try/except Exception` y un fallo de escritura **solo imprime un aviso**. En un log
forense, perder un evento de custodia con un aviso por stderr es débil. Es preexistente.

---

### Task 8b: Adopción explícita de checkouts anteriores al registro (cierra el hueco de §15)

**Esta tarea no existía y el Task 9 la necesita** (R7/H7-09). El §15 de la spec ordena que «los
checkouts anteriores sin registro requieren `--case-dir` y una operación explícita de
adopción/verificación». El Task 7 prueba el lado negativo —checkout propio sin entrada de
registro → `LocalWorkspaceMissing`, «no se adopta solo»— y ningún task construía el lado
positivo: el único rastro en todo el plan era el **nombre** del evento `checkout_adoptado` en el
Task 8. Sin esta pieza, en cuanto el Task 9 sustituye `_resolver_caso`, un checkout legacy que
hoy se procesa queda **bloqueado sin vía normativa de desbloqueo**: se construye el error y no
la puerta.

**Files:**
- Create: `core/casos/workspace_adopcion.py`
- Modify: `scripts/repository_cli.py` (subcomando `adoptar`)
- Test: `tests/test_workspace_adopcion.py`

**Interfaces:**
- `verificar_adopcion(case_dir: Path, ref: CaseRef, *, usuario, maquina, ahora) -> Adopcion`:
  pieza **pura de decisión**, sin efectos. Comprueba las tres cosas que hacen adoptable un
  checkout: existe `MANIFEST_CHECKOUT.json` legible, la identidad del árbol concuerda con `ref`,
  y el lock del canon es **propio** (mismo usuario y máquina). Cualquier discrepancia devuelve
  `Adopcion(ok=False, motivo=...)`; no adivina.
- `adoptar(...)`: da de alta la `WorkspaceEntry` y emite `checkout_adoptado`. **Es el único
  escritor**, y solo corre si `verificar_adopcion` dio `ok`.
- `repository_cli adoptar --case-dir <ruta>`: la puerta humana. **Nunca** implícita: adoptar es
  una decisión del abogado sobre custodia, no un efecto colateral de correr un motor.

- [x] **Step 1: Write the failing tests** — un checkout legacy válido (manifest + identidad +
  lock propio) **sin** `WorkspaceEntry`: `verificar_adopcion` da `ok`, `adoptar` registra, y a
  continuación `sala_maquina --case-dir` **resuelve** donde antes lanzaba; lock de **otra**
  máquina → `ok=False` y cero escrituras; manifest ausente o ilegible → `ok=False`; identidad
  del árbol que no concuerda con `ref` → `ok=False`; `verificar_adopcion` no escribe **nada** en
  ninguno de los cuatro planos (se comprueba con el arnés del Task 10); adoptar dos veces es
  idempotente y no duplica el evento.
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Write the implementation**
- [x] **Step 4: Verify**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_workspace_adopcion.py -q
```

---


**Estado del Task 8b — ✅ COMPLETO.** 26 tests y **12 mutantes que mueren cada uno por su
frontera**.

**Una desviación de la letra del plan, y es de fondo.** El Step 1 pedía comprobar que «la
identidad del árbol concuerda con `ref`». **El árbol local no tiene identidad**: medido
antes de escribir nada, `MERGE_EXCLUSIONS` excluye `_caso.md` del checkout, y el nonce del
préstamo se escribe **solo en el `_caso.md` del Drive** (`aplicar_lock_prestado(fm_drive, …)`).

Eso no es un obstáculo para la pieza: **es su razón de ser.** El §15 exige adopción
explícita porque la máquina **no puede probar** que esa carpeta sea la copia que el lock
vigente designa. Lo que sí comprueba: que es un checkout (manifest legible), que el lock
del canon es **mío** —la que de verdad autoriza— y que el W-code del nombre casa.

Por eso `verificar_adopcion` devuelve `sin_verificar` y el subcomando lo **imprime antes
del resultado**. Si no lo hiciera, estaría pidiendo una decisión de custodia sin dar los
datos para tomarla, y la firma sería un trámite en vez de una decisión. Hay test que lo
exige, y un mutante que lo mata.

**Tres fronteras no estaban contratadas**, y las tres por el mismo motivo: **dos guardas y
el test sin distinguir cuál actuaba**. Falta-de-manifest se confundía con manifest-ilegible;
un `{roto` lo para el `json.loads`, así que la comprobación de **forma** no se ejercitaba
(el caso realista es un JSON válido de otra versión del formato); y `disponible` con
titular a `None` lo paraba la guarda de propiedad, no la del estado.

`adoptar` es el **único escritor**, no re-decide, y es idempotente. El evento
`checkout_adoptado` cae en el **local** — B0-1 aplicado también aquí.

---

### Task 9: `scripts/sala_maquina` resuelve por workspace y acepta `--case-dir` (cierra A-7 y parte de A-3)

Primer consumidor real. Es también lo que hace **utilizable** el modo
`local_scratch`, que hoy no tiene ninguna vía (el Cluster B del diseño de scratch
nunca se construyó).

**Files:**
- Modify: `scripts/sala_maquina.py` (`_resolver_caso`, `plan`, `apply`, `reforzar`)
- Test: `tests/test_sala_maquina_workspace.py` (crear)

**Interfaces:**
- Los tres subcomandos aceptan `--case-dir PATH` mutuamente excluyente con el argumento posicional de identidad.
- `_resolver_caso` desaparece; en su lugar `_resolver_workspace(case_id: str | None, case_dir: Path | None) -> CaseWorkspace`, que delega en el resolver y **exige la capacidad**: `plan` y `apply`/`reforzar` piden `WRITE_CASE` y `GENERATE_DERIVATIVES`.
- `plan` **declara que escribe** (docstring y ayuda del CLI): deja el `_segmentacion.md` de los bundles. Deja de anunciarse como preview inocuo.
- `append_event` recibe el workspace, no el `case_id`.
- Sobre un caso `prestado` por otro, los tres subcomandos **abortan con código 2 y cero bytes**: ni `_atomizar_correo`, ni `_segmentacion.md`, ni estado, ni cobertura, ni evento.

- [x] **Step 1: Write the failing tests** — death test de cero escritura sobre **los tres** subcomandos, `plan`, `apply` **y `reforzar`** (R7/H7-13: la interfaz promete que «los tres abortan con código 2 y cero bytes» y este Step solo probaba dos; `reforzar` escribe cobertura, estado y evento, así que puede omitir el guard y dejar la suite verde). Se muta el preflight de `reforzar` **en solitario** y debe morir. Hash del árbol antes y después de invocar cada uno sobre un caso prestado por otra máquina (idénticos, y `registro` del log sin líneas nuevas); `--case-dir` sobre un scratch procesa y escribe el evento **en el scratch**; `--case-dir` junto con identidad → error de uso; identidad de un caso disponible → se comporta como hoy (regresión de `test_sala_maquina_*`).
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Write the implementation**
- [x] **Step 4: Verify**

```bash
python -m pytest tests/test_sala_maquina_workspace.py tests/test_sala_maquina_cableado_atomize.py -q
```

---


**Estado del Task 9 — ✅ COMPLETO.** 22 tests y **8 mutantes por su frontera**, incluido el
que el plan exigía: mutar el preflight de **`reforzar` en solitario** (R7/H7-13). Muere por
su propio test, así que los tres subcomandos están contratados y no solo dos.

**Lo que cambia de verdad.** Antes, sobre un caso **prestado a otra máquina**, el motor
arrancaba igual: atomizaba el correo, dejaba `_segmentacion.md`, actualizaba estado y
cobertura y emitía el evento — todo sobre una copia que otro tenía en curso. Ahora los tres
abortan con **código 2 y cero bytes**, verificado por hash del árbol antes y después.

**El problema no era técnico sino de SITIO.** `sala_maquina` tiene **~28 puntos** donde los
tests parchean `cli.caso_path` para montar casos fuera de `CASOS_ROOT`. Poner la resolución
en el lugar equivocado habría tumbado media suite, y no por un defecto: por elegir mal.

La forma que lo resuelve es **preguntar primero al catálogo**. Si el canon no conoce el
caso, **no hay lock que respetar** y se conserva el binding del módulo
(`legacy_unresolved`, §7.3); si lo conoce, manda el resolver y puede bloquear. No es un
atajo de compatibilidad: el bloqueo solo puede existir donde hay algo que bloquear. Los
190 tests de sala de máquina siguen verdes — ninguno de los 28 cayó.

**`--case-dir` cierra A-7:** `local_scratch` tiene por fin vía de trabajo. Hasta hoy
dependía de sobrescribir `CASOS_ROOT` por entorno, porque el Cluster B del diseño de
scratch nunca se construyó.

**`plan` dejaba de decir la verdad.** Su docstring decía «Preview; no escribe nada salvo el
manifiesto de segmentación». Escribe. Un comando llamado `plan` que deja ficheros en el
expediente es de las cosas que se declaran en la ayuda, no se descubren. Hay test.

**Dos errores propios, cazados por la suite en segundos:** `from core.actor import
get_actor` (ese módulo no existe; vive en `core.intake_log`), y los sentinelas de Typer —al
invocar las funciones **directamente**, como hacen los tests de este repo, los defaults
llegan como `OptionInfo` y no como `None`, así que la exclusión mutua se disparaba siempre.

**Y una frontera sin contratar, la quinta del mismo patrón:** el test de exclusión mutua
pasaba `--case-dir X` con `X` inexistente, así que el rechazo lo producía la guarda de
**existencia** —que también sale con 2— y el test pasaba aunque la exclusión desapareciera.
Ahora el `--case-dir` que se pasa **funcionaría por sí solo**.

---

### Task 10: Matriz contractual reutilizable + death test de los cuatro planos

La matriz del §14.1 no puede reescribirse en cada componente: se parametriza una
vez y la consumen los entrypoints migrados (ahora `sala_maquina`; en la Fase 3,
la vertical de correo).

**Files:**
- Create: `tests/test_workspace_matriz_contractual.py`
- Test: se prueba a sí mismo (el arnés + su aplicación a `sala_maquina`)

**Interfaces:**
- `ESCENARIOS`: las 9 filas del §14.1 como datos (`id`, sembrado, resultado esperado).
- **«Servicio externo falla» necesita un mecanismo, no una fila** (R7/H7-08). La firma
  `matriz_para(invocar)` solo entrega workspace o ruta: se puede cumplir `len(ESCENARIOS) == 9`
  y **no inducir jamás** el fallo externo. La fila se acompaña de: un doble que falla **después**
  de un efecto observable, el instante de fallo como dato del escenario, un contador de llamadas,
  y una **segunda invocación** con aserto de idempotencia — o cero publicación, o una única
  publicación estable, más el conteo exacto de llamadas. Sin la segunda invocación no se prueba
  «reintento seguro o aborto idempotente», que es lo que el §14.1 exige.
- `matriz_para(invocar: Callable[[CaseWorkspace | Path], int])`: arnés parametrizado que cualquier test de entrypoint puede consumir.
- `hash_arbol(root) -> dict[str, str]` y `assert_sin_efectos(antes, despues, *, log_antes, log_despues, llamadas_externas)`: comprueba los **cuatro planos** del §3.2-bis — árbol, canon (incluidas carpetas creadas), servicios externos (contador de llamadas del doble) y estado local (registro y sentinels).

- [x] **Step 1: Write the tests** (arnés + aplicación a `sala_maquina`)
- [x] **Step 2: Run**

```bash
python -m pytest tests/test_workspace_matriz_contractual.py -q
```

- [x] **Step 3: Comprobar que el arnés falla cuando debe — CUATRO mutantes, uno por plano** (R7/H7-07). La interfaz promete los cuatro planos del §3.2-bis y este Step mandaba «introducir a mano **una** escritura en un caso bloqueado»: un solo mutante, que prueba el detector de ficheros y deja `llamadas_externas`, registro y sentinels sin participar en ninguna aserción. Es el modo de fallo que R6 encontró ayer en el Plan 1 y que ya tengo medido: **si el contrato enumera N fronteras, hacen falta N mutantes** (memoria `feedback-mutacion-vale-por-su-mutante`). Los cuatro, independientes, y los cuatro ROJOS obligatorios:
  1. **árbol** — crear o modificar un fichero bajo el árbol del caso;
  2. **canon** — crear un directorio o fichero bajo `CASOS_ROOT`, que es el plano que las carpetas fantasma usan;
  3. **servicios externos** — ejecutar una llamada del doble sin que el contador la vea;
  4. **estado local** — modificar el registro, una caché o un sentinel.

  El Step solo se cierra si **cada** mutante falla **por su plano**, no si «alguno» falla: un mutante que muere por la aserción de otro plano no prueba el suyo. Revertir con `git checkout` tras cada uno, nunca reescribiendo el texto a mano.

**Criterio de salida de la Fase 1:** (1) la matriz pura demuestra una única resolución para Drive disponible, checkout propio, checkout ajeno, scratch, conflicto, ruta ausente y nonce divergente; (2) ninguna ruta del código crea un directorio bajo `CASOS_ROOT` para una identidad que el catálogo no conoce; (3) con `--case-dir`, el evento de auditoría cae en el mismo árbol que los bytes.

---

### Task 11: Gobernanza y acoplamiento

**Files:**
- Modify: `PLAN.md` (marcar Fase 0 y Fase 1 con `[x]` + hash del PR en el bloque `[SIGUIENTE-DUAL-WORKSPACE]`)
- Modify: `docs/ARQUITECTURA.md` (las tres piezas nuevas de `core/casos/` en el mapa de dependencias; `intake_log` ya no depende de `config.caso_path`)
- Modify: `docs/ARQUITECTURA_RELACIONES.md` (el resolver pasa a ser **SSOT de la copia operativa**; `case_locator` queda como catálogo)
- Modify: `docs/MEJORAS_FUTURAS.md` (cerrar lo que esta fase resuelva de `#93`, si algo; anotar lo que quede)

- [x] **Step 1: Actualizar los cuatro documentos**
- [x] **Step 2: Suite completa + leak-scan**

```bash
.\.venv\Scripts\python.exe -m pytest -q --junit-xml="$env:TEMP\fd_junit.xml" --basetemp="$env:TEMP\fd_bt"
```

- [x] **Step 3: PR** — rama `claude/fase1-tasks-10-11-ec3d35`, PR a `main` (protegida: nunca commit directo). El PR describe qué `xfail` quedan vivos y por qué (son la lista de trabajo de la Fase 2).

---

## Lo que este plan deliberadamente NO hace

- No materializa `_caso.md` ni `_intake_log.jsonl` en el checkout local (Fase 2, y **antes** hay que arreglar `MEJORAS #96`).
- No cambia `decidir_escritura` ni retira `_pendiente_checkin/` (Fase 2, conmutación atómica).
- No arregla A-1 ni A-2: los deja reproducidos en `xfail(strict=True)` (Fase 2).
- No toca `expedientes_xl/tiers.py` ni las skills de checkout/checkin (Fase 2 para la decisión, Fase 5 para el resto).
- No migra `email_export` ni Streamlit (Fases 3 y 4). **`catalogo_documental` sí entra**: su `save_catalog` hace `mkdir(parents=True)` sobre la ruta resuelta, así que dejarlo fuera hacía inalcanzable el criterio de salida (2) de esta misma fase (R7/H7-01).
- **Retirada:** «no invierte el default de `strict`» estaba aquí y contradecía el *Goal* y el criterio de salida (2) de este mismo plan. La Fase 1 **sí** invierte el default; lo que se aplaza a la Fase 4 es retirar la escotilla `strict=False` y los `# legacy_unresolved` que queden inventariados (R7/H7-01).

---

## 12. Adjudicación de la revisión adversarial del plan de la Fase 1 (Codex, 2026-08-24) — NO-SHIP, remediado

- **Objeto revisado:** este plan, sus **Tasks 4 a 11** (los 1-3 estaban supersedidos y quedaron fuera de alcance), en el commit `3f092f8`.
- **Ronda:** R7, y es la **primera** revisión adversarial que este plan recibe. La fila #3 de `PLAN.md` lo decía expresamente; las tres pasadas adjudicadas que allí se mencionan fueron sobre la **spec**, no sobre el plan. Se corrió **antes de ejecutarlo**, no después.
- **Revisor:** Codex, por CLI, sobre una copia externa `git archive` sin `.git` ni red —solo lectura por construcción—, trabajando sobre su propia copia en `scratch_objeto/`. Adjudica Claude Code contra la fuente.
- **Informe recibido:** `docs/superpowers/specs/2026-08-24-dual-workspace-fase1-r7-adversarial-review.md`, §1 literal, `sha256` `53ba2b4d0370d1564a336cde7021b942c902807d78f39e053b8d0ed8ab45fbec` — recomputado al archivarlo y **coincide**. El árbol se recomputó de forma independiente al recibir el informe: 1.057 ficheros, `12616082…b503055`, idéntico en apertura y cierre.
- **Hallazgos:** 15 — 1 CRÍTICO, 7 ALTOS, 7 MEDIOS. **15 confirmados, 0 refutados**, más una aportación del adjudicador que el revisor no vio.
- **Remediado en:** el commit que acompaña a esta adjudicación, que reescribe los Tasks 4-11 y añade el Task 8b.

*El «12» sigue a los once tasks: es la sección posterior al plan, no una duodécima tarea.*

### Por qué esta ronda valió la pena, dicho sin adornos

Iba a ejecutar los ocho tasks. Si lo hubiera hecho, habría construido una Fase 1 que **no cumple su
propio criterio de salida**, y me habría enterado al llegar a la Fase 4 — con ocho tasks de código
encima. El §23 de la spec de apertura detuvo el bucle de revisar un diseño por sexta vez, y esa
lección sigue siendo buena; lo que no era lo mismo es aplicarla a un plan que nunca había sido
revisado **ninguna** vez.

**Tres de los quince son el mismo modo de fallo que ya tengo medido**, y eso es lo que más me
interesa del resultado: el test central del Task 8 era literalmente `...`; el death test de «cuatro
planos» mutaba uno; el canario de rutas solo detectaba `:\`. Es *nombrar la propiedad y llamarlo
contrato*, otra vez, en un plan escrito el 2026-07-29 — anterior a las rondas que me enseñaron a
buscarlo. Un plan viejo no es solo un plan viejo: es un plan escrito por alguien que aún no sabía
esto.

### Las quince, una por una

| # | Sev. | Hallazgo | Veredicto | Remedio |
|---|---|---|---|---|
| H7-01 | CRÍTICO | La Fase 1 conserva el fallback que su criterio de salida exige eliminar | **CONFIRMADO** | Tres APIs en vez de un booleano; default `strict=True`; `catalogo_documental` entra; `log_path` se retira |
| H7-02 | ALTO | Registro corrupto → «vacío» abre una vía fail-open | **CONFIRMADO** | `cargar()` lanza `RegistryUnreadable`; la cuarentena salva los bytes, no la decisión |
| H7-03 | ALTO | La prueba de atomicidad no ejecuta la operación atómica | **CONFIRMADO** | Se atraviesa `alta()` con `os.replace` parcheado; mutante `write_text` obligatorio |
| H7-04 | MEDIO | Forma concurrente no decidida, incompatible con el namespace de D2 | **CONFIRMADO** | Se decide **aquí**: un fichero por W-code; test de concurrencia y de layout |
| H7-05 | ALTO | El test que impedía el split brain es `...` y pasa | **CONFIRMADO** | Cuerpo real escrito, con sentinel del canon y mutante `caso_path` |
| H7-06 | ALTO | 28 + 5 no son 32 | **CONFIRMADO** | 33, con doble aserto de longitud **y** conjuntos |
| H7-07 | ALTO | El death test de «cuatro planos» muta uno | **CONFIRMADO** | Cuatro mutantes independientes, cada uno rojo **por su plano** |
| H7-08 | ALTO | «Servicio externo falla» es una fila sin mecanismo | **CONFIRMADO** | Doble, instante de fallo, contador y segunda invocación con idempotencia |
| H7-09 | ALTO | Se migra `sala_maquina` antes de construir la adopción que §15 exige | **CONFIRMADO** | **Task 8b nueva**: `verificar_adopcion` puro + `adoptar` + subcomando |
| H7-10 | MEDIO | La tabla de ocho capacidades puede estar incompleta y pasar | **CONFIRMADO** | Igualdad completa por modo + ocho mutantes |
| H7-11 | MEDIO | Pureza y reloj inyectado nombrados, no contratados | **CONFIRMADO** | Globales parcheados para lanzar + determinismo + `diagnostico` a la firma |
| H7-12 | MEDIO | El canario de rutas solo ve `:\` | **CONFIRMADO** | Doce subclases × canarios Windows/UNC/POSIX/relativa + PII + las dos reglas del §10 |
| H7-13 | MEDIO | El cero-escritura excluye `reforzar` | **CONFIRMADO** | Los tres subcomandos, con mutación en solitario del preflight de `reforzar` |
| H7-14 | MEDIO | «80 ficheros» no mide llamadores | **CONFIRMADO** | Inventario AST: 151 llamadas / 55 ficheros (43 de producción) |
| H7-15 | MEDIO | Los comandos no son autoejecutables en el entorno declarado | **CONFIRMADO** | Intérprete del venv explícito, `$env:TEMP`, `--basetemp` corto |

### Lo que aporta el adjudicador y el revisor no vio

**Hay una TERCERA clase de llamador, y es la que explica por qué el plan se acobardó.** El H7-01
señala la contradicción pero razona con dos clases: quien crea (necesita el fallback) y quien lee un
caso existente (a quien el fallback miente). Falta la que hace inviable la inversión ingenua: el que
usa la ruta del fallback **para saber si el caso existe**. Son **27 sitios en 17 ficheros**, medidos.
Con `strict=True` no reciben `False`, reciben una excepción.

Medido en vivo, no deducido: hoy `abrir_caso --case-id W-NOEXISTE` responde
`[ERROR] Caso no encontrado para --case-id 'W-NOEXISTE'` con salida 1; con `strict=True` aplicado sin
más, responde un `FileNotFoundError` sin capturar y **sin una sola línea de salida**. Lo mismo en
`crm_ficha`. Por eso el remedio no es invertir el flag, sino la tercera API `buscar() -> Path | None`:
sin ella, cumplir el criterio de salida (2) se paga degradando dos entrypoints de un error legible a
una traza.

**Y el plan se contradecía a sí mismo, no solo con la spec.** El revisor comparó plan contra spec y
D1. La contradicción es interna: el *Goal* y el criterio de salida (2) exigen que ningún camino cree
un directorio bajo `CASOS_ROOT` para una identidad desconocida, y la sección final declaraba no
invertir el default «hasta la Fase 4». Un documento que se desmiente en dos páginas no necesita una
fuente externa para estar mal.

### Lo que sigue SIN VERIFICAR, y se declara

- **El comportamiento dinámico de los Tasks 4-11**: su código no existe. Los quince hallazgos atacan
  la **suficiencia del plan y de los tests que propone**, no una implementación observada. Esto se
  cierra ejecutando, y con una ronda sobre el diff — que es donde R6 demostró morder de verdad.
- **El empeoramiento de las siete `xfail` de la Fase 0**: siguen vivas (7 `xfailed`, 0 `xpassed`,
  corrida protegida) y ningún Task 4-11 toca `scripts/repository_cli.py`. No se verificó que ninguna
  empeore; se verificó que ninguna se toca. No es lo mismo y no se declara como si lo fuera.
- **El coste real de migrar los 43 ficheros de producción**: el inventario AST está medido, la
  clasificación por intención es una heurística con un cubo ambiguo reconocido. El Step 0 del Task 6
  la convierte en inventario versionado; hasta entonces, los 27 detectores son un suelo, no un total.

---

## 13. Lo que el Task 10 cambió del propio Task 10 (2026-08-25)

*Adjudicación de las desviaciones al ejecutar. No sustituye a una revisión adversarial: el
diff de los Tasks 10-11 pasa la suya (R8) antes de mergearse, y su acta hermana se archiva
aparte.*

Las tres desviaciones son **del mismo tipo que R7 encontró siete veces**: una interfaz que
nombra una propiedad que su propia firma no puede expresar. Que aparezcan aquí, en la parte
del plan que R7 acababa de reescribir, dice algo del método: **la firma solo se puede
falsar escribiendo el consumidor.** R7 atacó la suficiencia de los tests propuestos y no
podía ver esto, porque para verlo hay que intentar instanciar la firma.

### 13.1. `invocar` recibe `CaseRef | Path`, no `CaseWorkspace | Path`

**Medido, no deducido.** Tres de las nueve filas se resuelven con excepciones que
`CaseWorkspaceResolver` lanza **incondicionalmente**, sin la rama de `diagnostico` que
`_bloqueo` reserva a `CaseLocked` y `CaseConflict`:

| Fila | Sitio | Excepción |
|---|---|---|
| Registro local ausente | `resolver_por_identidad`, §15 | `LocalWorkspaceMissing` |
| Nonce divergente | `resolver_por_identidad` | `LockMismatch` |
| Runtime sin acceso | `_offline`, §7.2.9-10 | `RuntimeCannotAccessWorkspace` |

No existe ningún `CaseWorkspace` que represente esos tres estados, así que con la firma
original **eran indatables**. `CaseRef` es además lo que un entrypoint necesita de verdad —la
identidad, para volver a resolver él mismo—: un adaptador que se creyera el workspace que le
pasa el arnés no probaría nada, porque la autorización la habría hecho el arnés.

### 13.2. `assert_sin_efectos` conserva su firma y gana el plano 4

La firma del plan —`(antes, despues, *, log_antes, log_despues, llamadas_externas)`— se
mantiene **literal**. Lo que cambia es el tipo de `antes`/`despues`: no son hashes de un
árbol sino instantáneas `Planos` de los tres planos de estado (árbol, canon, estado local).
Como hashes de árbol, la función prometía cuatro planos y **solo podía comprobar dos**: el
registro privado y los sentinels no tenían por dónde entrar.

**Y el plano 2 se define como el canon EXCLUYENDO la copia de trabajo.** Esto no estaba en el
plan y es lo que hace posible su Step 3: con «todo `CASOS_ROOT`», en `drive_active` el árbol
del caso vive *dentro* del canon, así que un mutante del plano 1 mataría también al 2 y el
Step se cerraría con un mutante que no prueba lo suyo. Definido como «el canon alrededor de
la copia», dice exactamente el criterio de salida (2). Por eso los cuatro mutantes corren
sobre la fila **«nonce divergente»**: es la única de las nueve donde los cuatro planos viven
en tres raíces distintas y son separables.

### 13.3. El plano 3 exige contador **o** motivo por escrito

`sala_maquina` no hace ninguna llamada mutante a CRM, Gmail ni Drive: su motor es OCR local.
Así que `assert llamadas_externas == 0` se cumple **por vacío**. Dejarlo así habría hecho que
el plano 3 pasara en silencio en este consumidor y en todos los siguientes — la versión de
test de dar por refutado lo que nadie miró. `matriz_para` exige ahora `contador_externo` o
`sin_superficie_externa=<motivo>`, y el detector del plano 3 se prueba donde sí se puede:
contra su mutante.

### 13.4. Dos defectos que el Task 10 destapó por mirar al ENTRYPOINT

**(a) `drive_accesible=True` literal.** `_resolver_workspace` lo pasaba fijo en sus dos vías,
así que la rama offline del §7.2.9-10 —diseñada, con tests unitarios en el resolver— era
**código muerto en producción**, y la fila 8 solo era inducible mintiéndole al resolver.
Cerrado con `_drive_accesible()`, que lee `FEESDEFENDER_OFFLINE=1`.

**Y la segunda condición que le añadí duró exactamente una corrida completa.** Escribí también
«…o la raíz del catálogo no está montada», con `Path(settings.casos_root).is_dir()`. Suena más
listo y es peor por dos motivos que la suite midió: **diverge de la fuente de verdad** que usa
el catálogo (`case_locator._root`), y tres tests que parchean `_root` sin tocar el entorno
pasaron a abortar con `RUNTIME_CANNOT_ACCESS_WORKSPACE` un caso disponible; y **da falso
negativo en producción**, porque `data/CASOS` no existe en un clon limpio ni en un worktree, así
que toda invocación se habría ido al modo offline en silencio. Meter una segunda fuente de
verdad sobre dónde está el canon era el defecto, no el detalle.

**(b) 223 tests en 17 módulos dejaban `core.config` secuestrado.** El 65º cierre arregló la
fixture `tmp_casos_root` y dio la clase por cerrada; una sonda de teardown sobre la suite
entera midió que **tapar un pozo de diecisiete** no es tapar la fuga. Cerrado con un guard
`autouse` en `conftest` (`restaurar_config_si_secuestrada`), que repone **también**
`CASOS_ROOT` porque el orden de desmontaje no era el que supuse — lo desmintió el primer test
al que se aplicó.

### 13.5. El riesgo que el 65º anotó y no arregló, ya contratado

Los ~28 tests que parchean `cli.caso_path` quedaban **por debajo** del estado ambiental del
catálogo, y eso funcionaba por convención de nombres, no por contrato. Ahora hay test en las
**dos** direcciones —el canon manda cuando conoce el caso; el binding del módulo manda cuando
no— con un mutante que invierte la precedencia y muere. La dirección que importa es la
primera: sin ella, cualquier código que reconfigure `caso_path` es una vía de escritura sobre
un expediente prestado.

### 13.6. Lo que sigue SIN VERIFICAR, y se declara

- **El plano 3 sobre una superficie externa real.** Ningún entrypoint migrado tiene una, así
  que el detector está probado contra su mutante pero **no** contra un servicio de verdad. Se
  cierra en la Fase 3, con la vertical de correo.
- **El arnés sobre un segundo consumidor.** Su valor es ser reutilizable y hoy lo usa uno.
  Que la firma valga para la UI o para un plugin es una promesa, no una medición.
- **Las siete `xfail` del frontal.** Siguen vivas (7 `xfailed`, 0 `xpassed`, corrida
  protegida) y ningún Task 10-11 toca `scripts/repository_cli.py`. Se verificó que no se
  tocan; no que ninguna empeore. No es lo mismo.
