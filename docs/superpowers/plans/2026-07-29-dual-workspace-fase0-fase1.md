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
- **Comandos desde la raíz del worktree**, con el venv del repo: `python -m pytest ...`.
- **Suite completa verde antes del PR.** El CI del PR solo corre `leak-scan`; pytest es responsabilidad local (memoria `feedback-ci-pr-solo-leak-scan`). Conteo por `--junit-xml`, no por el resumen de la tubería (`feedback-pytest-junit-xml-y-dead-ends`).

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

- [ ] **Step 1: Write the failing tests** — `CaseRef` sin identidad lanza; un modo `BLOCKED_*` **no** concede `WRITE_CASE` ni `INGEST`; `LOCAL_CHECKOUT` no concede `MUTATE_CANONICAL`; `working_root is None` con modo mutable es incoherente y lanza; `exigir` lanza `CapabilityDenied` con `codigo == "CAPABILITY_DENIED"`; un `CaseWorkspace` es inmutable (`dataclasses.FrozenInstanceError`); ningún `str(error)` contiene el separador de unidad de Windows.
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Write the implementation**
- [ ] **Step 4: Verify**

```bash
python -m pytest tests/test_workspace_model.py -q
```

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
- Escritura atómica: fichero temporal en el mismo directorio + `os.replace`. Nunca escritura in-place.
- Un registro corrupto **no se borra**: se renombra a `*.corrupto.<ts>` y se devuelve vacío con aviso; el `ts` lo pasa el llamante (nada de `Date.now()` implícito en la lógica pura).
- `schema` distinto del soportado → error explícito, no adivinar.

- [ ] **Step 1: Write the failing tests** — dos entradas para el mismo `w_code` se devuelven **ambas** (la desambiguación es del resolver, no del registro); `alta` sobre una ruta que ya está registrada para otro caso lanza; `os.replace` deja el fichero íntegro si el proceso muere entre escritura y rename (simulado escribiendo el temporal y no renombrando); JSON corrupto → cuarentena + vacío; ruta del registro bajo `CASOS_ROOT` → lanza; el fichero **no** contiene secretos ni contenido de documentos.
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Write the implementation**
- [ ] **Step 4: Verify**

```bash
python -m pytest tests/test_workspace_registry.py -q
```

---

### Task 6: `CaseCatalog` + modo estricto del localizador (cierra A-5 y A-8)

Aquí se mata el fallback silencioso. Es el cambio con más superficie de
regresión de la Fase 1: `path_for` y `caso_path` los llaman 80 ficheros.

**Files:**
- Create: `core/casos/case_catalog.py`
- Modify: `core/casos/case_locator.py` (`path_for`, `resolve_ref`), `core/config.py` (`caso_path`)
- Test: `tests/test_workspace_catalog.py`, `tests/test_case_locator.py` (añadir)

**Interfaces:**
- `path_for(case_id: str, *, strict: bool = False) -> Path`: con `strict=True` lanza `LocalWorkspaceMissing` en vez de devolver la ruta flat inexistente. **Default `False` en esta fase** (compatibilidad); el default se invierte en la Fase 4, cuando ya no queden llamadores legacy.
- `caso_path(case_id, *, strict: bool = False)` propaga el keyword.
- `resolve_ref(ref)` conserva firma, **pero** si dos casos del catálogo comparten `meta.id_go` lanza `AmbiguousCase` en lugar de devolver el primero por orden de escaneo.
- `class CaseCatalog`: `localizar(ref: CaseRef) -> Path` (estricto siempre), `estado_compartido(ref) -> dict` (lee el `_caso.md` del canon vía `read_case_meta`), `es_proyeccion_local(case_dir) -> bool` (marca `meta.proyeccion_local`), `bajo_catalogo(path) -> bool` (para `WorkspaceUnderCatalogRoot`).
- Un `case_dir` marcado como proyección local **se excluye** de `list_cases()`.

- [ ] **Step 1: Write the failing tests** — `path_for(strict=True)` de un caso ausente lanza y **no crea nada** (comprobar el árbol antes/después); dos casos con el mismo `id_go` → `AmbiguousCase`; una carpeta con `meta.proyeccion_local: true` no aparece en `list_cases()` ni gana la resolución por W-code; `bajo_catalogo` reconoce un subdirectorio de `CASOS_ROOT` y rechaza uno de fuera; `path_for(strict=False)` sigue comportándose exactamente como hoy (regresión).
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Write the implementation**
- [ ] **Step 4: Verify** — aquí es donde puede romperse algo ajeno:

```bash
python -m pytest tests/test_case_locator.py tests/test_workspace_catalog.py -q
python -m pytest -q --tb=short
```

Expected: suite completa verde. Si un test ajeno falla, **no** es del entorno: es un consumidor de `path_for` que dependía del fallback (memoria `feedback-test-roto-culpar-al-entorno`). Diagnostícalo y repórtalo.

---

### Task 7: `CaseWorkspaceResolver` — la matriz del §7 en una sola pieza

**Files:**
- Create: `core/casos/workspace_resolver.py`
- Test: `tests/test_workspace_resolver.py`

**Interfaces:**
- `class CaseWorkspaceResolver(catalog: CaseCatalog, registry: WorkspaceRegistry, *, usuario: str, maquina: str, ahora: str)` — el reloj y la identidad **se inyectan**: la pieza es pura y determinista.
- `resolver_por_identidad(ref: CaseRef, *, drive_accesible: bool) -> CaseWorkspace` — implementa §7.2 paso por paso.
- `resolver_por_ruta(path: Path, *, drive_accesible: bool) -> CaseWorkspace` — implementa §7.1.
- Ambos **lanzan** `WorkspaceError` en los caminos de bloqueo; no devuelven un modo `BLOCKED_*` como valor de retorno normal salvo cuando el llamante pide diagnóstico explícito (`diagnostico=True`).
- `mutate_canonical=False` en el camino offline (§7.1.5 / §7.2.9).

- [ ] **Step 1: Write the failing tests** — una fila por escenario del §14.1, más: `prestado` por otra máquina → `CaseLocked` con titular y fecha en el mensaje y **sin** ruta local; `prestado` propio con nonce distinto → `LockMismatch`; `prestado` propio sin entrada de registro → `LocalWorkspaceMissing` (no se adopta solo, §15); `conflicto` → `CaseConflict` en cualquier modo; Drive inaccesible con **un** checkout verificado → `LOCAL_CHECKOUT` sin `MUTATE_CANONICAL`; Drive inaccesible con dos candidatos → `AmbiguousCase`; scratch cuyo W-code colisiona con un caso publicado → `AmbiguousCase` que exige `--case-dir`; `--case-dir` a una ruta bajo `CASOS_ROOT` → `WorkspaceUnderCatalogRoot`; `--case-dir` donde identidad, manifest y registro se contradicen → aborta.
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Write the implementation**
- [ ] **Step 4: Verify**

```bash
python -m pytest tests/test_workspace_resolver.py -q
```

---

### Task 8: `core.intake_log` escribe donde están los bytes (cierra B0-1)

La tarea más importante del plan. Sin ella, `--case-dir` es una máquina de
split brain.

**Files:**
- Modify: `core/intake_log.py`
- Test: `tests/test_intake_log.py`

**Interfaces:**
- `append_event(destino, event, *, details=None, actor=None, ts=None, case_id=None) -> Path`, donde `destino` es un `CaseWorkspace` **o** un `Path` al árbol del caso ya resuelto. El `case_id` del registro sale del workspace; el keyword existe solo para el camino `Path`.
- `log_path(case_id)` queda **deprecado**: emite `DeprecationWarning` y exige `strict=False` explícito; se retira en la Fase 4. `log_path_de(case_dir: Path) -> Path` es la vía nueva.
- **`append_event` deja de crear la raíz del caso.** Si `00_Input/` no existe bajo el destino, lanza `LocalWorkspaceMissing`: crear un expediente es trabajo de la apertura, no de la auditoría. Solo crea el fichero de log.
- Altas en `INTAKE_EVENTS` (27 → 32): `scratch_creado`, `scratch_promovido`, `checkout_adoptado`, `conflicto_resuelto`, `checkout_cancelado_unilateral`. `pendiente_checkin` **se conserva** (lectura histórica) con comentario de que su emisión se retira en la Fase 2.

- [ ] **Step 1: Write the failing tests**

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
    ...
```

Más: `log_path(case_id)` emite `DeprecationWarning`; el set de eventos pasa a 32 **y se actualiza el `expected` completo** del test existente; un evento desconocido sigue lanzando `ValueError`.

- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Write the implementation** — migrar además **todos** los llamadores internos de `append_event(case_id, …)` que ya disponen del `case_dir`. Los que no lo tengan se dejan en el camino legacy con comentario `# legacy_unresolved (Fase 4)`, nunca «arreglados» a medias.
- [ ] **Step 4: Verify**

```bash
python -m pytest tests/test_intake_log.py -q
python -m pytest -q --tb=short
```

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

- [ ] **Step 1: Write the failing tests** — death test de cero escritura: hash del árbol antes y después de invocar `plan` y `apply` sobre un caso prestado por otra máquina (idénticos, y `registro` del log sin líneas nuevas); `--case-dir` sobre un scratch procesa y escribe el evento **en el scratch**; `--case-dir` junto con identidad → error de uso; identidad de un caso disponible → se comporta como hoy (regresión de `test_sala_maquina_*`).
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Write the implementation**
- [ ] **Step 4: Verify**

```bash
python -m pytest tests/test_sala_maquina_workspace.py tests/test_sala_maquina_cableado_atomize.py -q
```

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
- `matriz_para(invocar: Callable[[CaseWorkspace | Path], int])`: arnés parametrizado que cualquier test de entrypoint puede consumir.
- `hash_arbol(root) -> dict[str, str]` y `assert_sin_efectos(antes, despues, *, log_antes, log_despues, llamadas_externas)`: comprueba los **cuatro planos** del §3.2-bis — árbol, canon (incluidas carpetas creadas), servicios externos (contador de llamadas del doble) y estado local (registro y sentinels).

- [ ] **Step 1: Write the tests** (arnés + aplicación a `sala_maquina`)
- [ ] **Step 2: Run**

```bash
python -m pytest tests/test_workspace_matriz_contractual.py -q
```

- [ ] **Step 3: Comprobar que el arnés falla cuando debe** — introducir a mano una escritura en un caso bloqueado, verificar que la matriz la caza, y revertir. Un arnés que no puede fallar no prueba nada.

**Criterio de salida de la Fase 1:** (1) la matriz pura demuestra una única resolución para Drive disponible, checkout propio, checkout ajeno, scratch, conflicto, ruta ausente y nonce divergente; (2) ninguna ruta del código crea un directorio bajo `CASOS_ROOT` para una identidad que el catálogo no conoce; (3) con `--case-dir`, el evento de auditoría cae en el mismo árbol que los bytes.

---

### Task 11: Gobernanza y acoplamiento

**Files:**
- Modify: `PLAN.md` (marcar Fase 0 y Fase 1 con `[x]` + hash del PR en el bloque `[SIGUIENTE-DUAL-WORKSPACE]`)
- Modify: `docs/ARQUITECTURA.md` (las tres piezas nuevas de `core/casos/` en el mapa de dependencias; `intake_log` ya no depende de `config.caso_path`)
- Modify: `docs/ARQUITECTURA_RELACIONES.md` (el resolver pasa a ser **SSOT de la copia operativa**; `case_locator` queda como catálogo)
- Modify: `docs/MEJORAS_FUTURAS.md` (cerrar lo que esta fase resuelva de `#93`, si algo; anotar lo que quede)

- [ ] **Step 1: Actualizar los cuatro documentos**
- [ ] **Step 2: Suite completa + leak-scan**

```bash
python -m pytest -q --junit-xml=%TEMP%\fd_junit.xml
```

- [ ] **Step 3: PR** — rama `claude/dual-case-workspace`, PR a `main` (protegida: nunca commit directo). El PR describe qué `xfail` quedan vivos y por qué (son la lista de trabajo de la Fase 2).

---

## Lo que este plan deliberadamente NO hace

- No materializa `_caso.md` ni `_intake_log.jsonl` en el checkout local (Fase 2, y **antes** hay que arreglar `MEJORAS #96`).
- No cambia `decidir_escritura` ni retira `_pendiente_checkin/` (Fase 2, conmutación atómica).
- No arregla A-1 ni A-2: los deja reproducidos en `xfail(strict=True)` (Fase 2).
- No toca `expedientes_xl/tiers.py` ni las skills de checkout/checkin (Fase 2 para la decisión, Fase 5 para el resto).
- No migra `email_export`, `catalogo_documental` ni Streamlit (Fases 3 y 4).
- No invierte el default de `strict` en `path_for`/`caso_path` (Fase 4, cuando no queden llamadores legacy).
