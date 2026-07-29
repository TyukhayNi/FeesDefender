# Dual workspace — Fase 0: banco de pruebas del frontal — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Estado: rev. 2** (2026-07-29), tras revisión adversarial de Codex con veredicto
**NO EJECUTABLE EN SU FORMA ACTUAL** (3 B0 + 5 A + 1 M). Todos aceptados salvo dos
sub-puntos refutados con el binario (§«Contrato de rclone»). La rev. 1 nunca se
mergeó: se corrige antes de entrar a `main`.

**Goal:** Poner el ciclo `checkout`/`checkin` bajo test de **orquestación** sin
cambiar su comportamiento. Al terminar: el orden exacto de las operaciones contra
Drive es observable, los siete defectos que la revisión adversarial encontró en el
frontal están **reproducidos en código** (no descritos en prosa), y la Fase 2 puede
tocar el lock con red debajo.

**Architecture:** Un único punto de inyección, `Entorno`, que agrupa las cinco
fuentes de no-determinismo del frontal. `ENTORNO_REAL` reproduce exactamente lo de
hoy. Frente a él, un doble en memoria (`FakeDrive` + `FakeRclone`) que **miente
como Drive** y cuyo contrato está fijado a **rclone v1.73.5 (Windows amd64)** con
fixtures grabadas de salidas reales, no fabricadas. Y una **barrera de seguridad**
que hace imposible que un error de propagación toque el Drive real.

**Tech Stack:** Python 3.11+, `argparse` (el frontal), `pytest` (+
`pytest-randomly`: orden aleatorio), stdlib. Sin dependencias nuevas. **Sin red y
sin `rclone` instalado.**

## Lo que ya está hecho (y cambia el punto de partida)

El **PR #156** (`5f4c81a`, mergeado antes de este plan) arregló dos rutas de
destrucción de datos —un pull fallido del `_caso.md` degradaba el fichero canónico
a un stub sin `id_go`; un pull fallido del log lo reemplazaba por una línea— y de
paso dejó en el repo:

- `tests/test_repository_cli_guard_pull.py`: **8 tests que SÍ ejercitan
  `cmd_checkout` y `cmd_checkin`**, con un doble mínimo de rclone por `monkeypatch`
  de `run_rclone`. Son los primeros tests de orquestación del repo.
- Un `FakeRclone` embrionario que este plan **promueve y extiende**, no reinventa.
- `ProtocoloIOError`, `_remoto_existe`, `_pull_caso_md → (fm, cuerpo) | None` y
  `_push_caso_md(..., *, cuerpo)`: firmas ya estables, con las que el `Entorno`
  tiene que convivir.

Consecuencia para el orden de tareas: el refactor de la Task 1B ya **no** se hace a
ciegas (hay 8 tests que cazan una regresión de comportamiento en los `cmd_*`), pero
sigue sin haber caracterización del camino verde ni de los fallos, así que el tajo
1A/1B se mantiene.

## Global Constraints

- **Fuente única del diseño:** `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md` (rev. 2), §12 «Fase 0» y §14. Informe que la justifica: `2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md`.
- **Este plan SUSTITUYE las Tareas 1-3** de `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md`, marcadas allí como supersedidas. La Fase 1 sigue viviendo allí.
- **Cero cambio de comportamiento.** Con `ENTORNO_REAL` el frontal ejecuta los mismos comandos, en el mismo orden, con los mismos códigos de salida. Los 27 tests de helpers puros **y los 8 del guard** deben pasar sin tocarlos.
- **Ningún bug se arregla aquí.** Los defectos se reproducen en `xfail(strict=True, raises=AssertionError)` citando su identificador. Un `xfail` que empieza a pasar rompe la suite. **Si al escribir un test descubres que el defecto no existe, para y repórtalo**: puede ser un falso positivo de la revisión de la SPEC, y eso obliga a retirarlo de su §20.
- **Sin esperas reales.** El `Entorno` inyecta `esperar`; en tests es un no-op que cuenta llamadas.
- **Sin no-determinismo en los asertos.** Timestamp, hostname, nonce, usuario y directorio de trabajo salen del `Entorno`.
- **Datos SIEMPRE sintéticos** (`BaRS9 - Prueba - (W-TEST99) - Vuelta`), cero PII. Las fixtures de rclone son **sintéticas en los valores y fieles en la forma**: las capturas reales llevan nombres de ficheros de expedientes y **no entran al repo** (`docs/SEGURIDAD_DATOS.md`).
- **Rutas Windows.** El doble normaliza a POSIX en su índice, igual que `parse_inventario_lsjson`.
- **Encoding:** UTF-8 sin BOM. El doble guarda **bytes**, no `str`: media parte de `B0-2` es un byte que no decodifica.
- **Comandos desde la raíz del worktree.** El worktree no tiene `.venv` propio: usar `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`.
- **Suite completa verde antes del PR.** El CI solo corre `leak-scan`. Conteo por `--junit-xml`.

---

## Contrato de rclone — v1.73.5, Windows amd64

Medido sobre la versión instalada. **Es el contrato del doble**: si algún día se
actualiza rclone, se re-mide y se actualizan las fixtures.

**`lsjson` — el backend Drive y el local NO son iguales:**

| | Drive | Local |
|---|---|---|
| Claves por entrada | `Path, Name, Size, MimeType, ModTime, IsDir, ID, Hashes` | las mismas **menos `ID`** |
| Algoritmos en `Hashes` | `md5, sha1, sha256` (3) | 13 (`blake3`, `crc32`, `md5`, `quickxor`, `xxh3`…) |
| `ModTime` | `"2026-05-29T07:41:12.000Z"` (ms + `Z`) | `"…T14:33:51.1997234+02:00"` (7 decimales + offset) |
| `Path` | barra normal, acentos UTF-8 literales | idéntico |

- Claves de hash **en minúscula en ambos backends**: `.get("md5")` de `parse_inventario_lsjson` es correcto. **Refutada** la premisa `Hashes.MD5` del informe (venía de documentación desactualizada).
- Directorios: `IsDir: true` y **sin** `Hashes`. De 59 ficheros reales, **0 sin md5**.
- **No hay backslashes en `Path` ni en el backend local**, así que la fixture «salida Windows con backslashes» que pedía el informe **no existe**: nada que capturar.

**Filtros:**

- `--files-from` + `--exclude` → **`CRITICAL`, exit 1, nada transferido**: *«the usage of --files-from overrides all other filters, it should be used alone or with --files-from-raw»*. El comentario del código (`build_copy_cmd`) acierta; **refutada** la lectura de que los filtros «se ignoran». El doble debe **abortar**, no ignorar.
- `--files-from` con una entrada **inexistente** → **exit 0, en silencio**.

**`check`:**

- `--one-way` cuenta lo que difiere y lo que falta en destino, e **ignora los extras del destino** (2 diferencias frente a 3 sin el flag). Es justo lo que el checkin necesita: los `PRESERVE_DRIVE` solo existen en Drive.
- Mismo tamaño y **contenido distinto** → `md5 differ`, exit 1. Es decir: **`verificacion_limpia` es por hash**, aunque `build_check_cmd` no pase `--checksum`.
- `cmd_checkin` solo lee el `returncode`: el doble **no necesita emular el texto** de las NOTICE.

**Otros:**

- `--backup-dir` recibe la versión **del destino** que se sobrescribe, con la jerarquía preservada.
- `--fast-list` no cambia la forma ni el conjunto de `Path`: es cuota y velocidad. El doble no lo modela.
- `copyto` de un origen inexistente → **exit 3**, y no crea el destino. `lsjson` de una ruta inexistente → **exit 3** con `stdout` = `"["` (JSON inválido, que `validar_inventario_texto` ya rechaza).

**Google-native: no se puede capturar.** Barrido de **3007 ficheros hasta
profundidad 6** en la unidad canónica: **cero** entradas `application/vnd.google-apps*`.
La rama `hash is None` → `ACCION_PRESERVE_DRIVE` de `plan_merge`, documentada como
caso de primera clase, **nunca ha sido ejercitada por datos reales**. Su fixture es
**sintética y se declara como tal**; no se muta el Drive para averiguar su forma
exacta. No hace falta: el contrato del parser
(`(item.get("Hashes") or {}).get("md5") or None`) trata igual las tres variantes
—sin clave `Hashes`, `Hashes: {}`, y `Hashes` sin `md5`—, así que el test emite las
tres y asierta `hash is None` en todas. Anotado en `docs/MEJORAS_FUTURAS.md` #104.

> **Trampa de medición, para quien regenere las fixtures:** en PowerShell,
> `$LASTEXITCODE` tras un `Select-Object -First N` puede quedar en `0` por
> terminación temprana del pipe. La primera medición de este contrato dijo que
> `copyto` de un origen inexistente devolvía 0; sin tubería devuelve 3. Medir
> asignando a variable y leyendo `$LASTEXITCODE` acto seguido.

---

## File Structure

| Fichero | Responsabilidad | Cambio |
|---|---|---|
| `tests/_barrera.py` | Barrera de seguridad: nada de rclone/Drive real | **Crear (Task 0)** |
| `tests/conftest.py` | Fixtures globales | **Modificar (Task 0):** la barrera es `autouse` |
| `scripts/repository_cli.py` | Frontal | **Modificar (1A/1B):** `Entorno` + `ENTORNO_REAL`; propagación a los `cmd_*` y helpers |
| `tests/_dobles/__init__.py`, `tests/_dobles/fake_drive.py` | `FakeDrive` + `FakeRclone` + `entorno_de_prueba` | **Crear (Task 2):** promueve el doble embrionario del PR #156 |
| `tests/_fixtures/rclone_v1735/*.json` | Salidas grabadas (sintéticas en valores, fieles en forma) | **Crear (Task 2)** |
| `tests/test_fake_drive.py` | El doble también se prueba, contra las fixtures | **Crear (Task 2)** |
| `tests/test_repository_cli_guard_pull.py` | Los 8 tests del guard | **Modificar (Task 2):** consumen el doble común en vez del embrionario |
| `tests/test_repository_cli_checkout.py` | Caracterización de `cmd_checkout` | **Crear (Task 3)** |
| `tests/test_repository_cli_checkin.py` | Caracterización de `cmd_checkin` | **Crear (Task 4)** |
| `tests/test_repository_cli_fallos.py` | Matriz de fallos por call-site | **Crear (Task 5)** |
| `tests/test_repository_cli_defectos.py` | Los 7 `xfail(strict=True)` | **Crear (Task 6)** |
| `tests/test_repository_cli.py` | Helpers puros | **Modificar (1A):** 2 tests de neutralidad del `Entorno` |
| `PLAN.md`, `scripts/repository_cli.py` (docstring) | Gobernanza | **Modificar (Task 7)** |

---

### Task 0: Barrera de seguridad — que un error de propagación no pueda tocar el Drive real

**Va primero.** Los defaults del frontal son el remote y el `team_drive` reales
(`RCLONE_REMOTE_TL`, `TEAM_DRIVE_TL` en `core/config.py`), un solo helper al que no
se propague el `Entorno` cae en `subprocess.run` de verdad, y `tmp_casos_root`
**no es `autouse`** (verificado: `tests/conftest.py:44` es un `@pytest.fixture`
pelado, pese a que el docstring del módulo dice «aísla el CASOS_ROOT en cada
test»). Es decir: precisamente el bug que la Task 1B podría introducir podría
intentar operar sobre expedientes reales.

**Files:**
- Create: `tests/_barrera.py`
- Modify: `tests/conftest.py`

**Interfaces:**
- Fixture `autouse=True, scope="function"` que:
  1. sustituye `subprocess.run` **en el namespace de `scripts.repository_cli`** por una función que lanza `AssertionError("subprocess real prohibido en tests")`;
  2. sustituye `shutil.which`/`settings.rclone_binary` por un binario inexistente, para que un `_rclone_bin()` colado no encuentre nada;
  3. exporta un helper `remote_sintetico()` → `"r,team_drive=T:"`, y un `assert_remote_sintetico(cmds)` que falla si algún comando menciona `gdrive_tl` o el `team_drive` real.
- La barrera **no** se salta con `monkeypatch` del propio test: si un test necesita ejecutar de verdad, lo declara con un marcador explícito `@pytest.mark.rclone_real` que hoy nadie usa y que la suite salta por defecto.
- **La prohibición de `monkeypatch` de las Global Constraints aplica al mecanismo de producción, no a esta barrera:** aquí el `monkeypatch` es el instrumento correcto.

- [ ] **Step 1: Write the failing test** — un test que llame a `subprocess.run` desde el namespace del frontal debe fallar con la barrera puesta; y un test que construya un comando con el remote real debe fallar en `assert_remote_sintetico`.
- [ ] **Step 2: Run to verify it fails** (sin barrera, el subprocess se intentaría).
- [ ] **Step 3: Implement** la barrera y hacerla `autouse` desde `conftest.py`.
- [ ] **Step 4: Verify** que los 8 tests del guard y los 27 de helpers puros siguen verdes con la barrera puesta:

```bash
python -m pytest tests/test_repository_cli.py tests/test_repository_cli_guard_pull.py -q
```

---

### Task 1A: `Entorno` y la costura de `run_rclone` — sin tocar los `cmd_*`

Cinco fuentes de no-determinismo, no una:

| Fuente | Dónde | Por qué bloquea el test |
|---|---|---|
| `run_rclone` | 14 llamadas en 7 helpers | ejecuta el binario |
| `now_iso_utc()` | `cmd_checkout`, `cmd_checkin`, **y `_append_evento_drive`** | entra en el lock y en nombres de artefacto |
| `socket.gethostname()` | `cmd_checkout` | entra en el lock |
| `_tmp_dir()` | `mkdtemp` | los artefactos caen donde el test no mira |
| `time.sleep(_SYNC_LAG_S)` | `cmd_checkout` | 4 s por invocación |

Y tres dependencias más que el informe señaló y hay que cerrar en el contrato:
`_nonce()` (usa `secrets`), `_usuario_por_defecto()` (usa `get_actor()` → entorno del
SO) y `_rclone_bin()` (usa `settings.rclone_binary`), más los **dos `ts_compacto()`
sin argumento** de `_append_evento_drive`.

**Files:**
- Modify: `scripts/repository_cli.py` (solo `run_rclone`, `_tmp_dir` y la definición del `Entorno`)
- Test: `tests/test_repository_cli.py` (añadir al final)

**Interfaces:**

```python
@dataclass(frozen=True)
class Entorno:
    ejecutar: Callable[[list[str]], subprocess.CompletedProcess]
    ahora: Callable[[], str]            # ISO-8601 UTC con Z
    hostname: Callable[[], str]
    work_dir: Callable[[], Path]
    esperar: Callable[[float], None]
    nonce: Callable[[], str]
    usuario: Callable[[], str]
    binario: Callable[[], str]

ENTORNO_REAL = Entorno(
    ejecutar=_ejecutar_rclone_real,   # el cuerpo actual de run_rclone, intacto
    ahora=now_iso_utc, hostname=socket.gethostname,
    work_dir=lambda: Path(tempfile.mkdtemp(prefix="fd_biblio_")),
    esperar=time.sleep, nonce=_nonce,
    usuario=_usuario_por_defecto, binario=_rclone_bin,
)
```

- `run_rclone(cmd, *, entorno: Entorno = ENTORNO_REAL)` conserva firma posicional y comportamiento.
- **En esta tarea NO se toca ningún `cmd_*` ni helper de I/O.** Solo existe el tipo, la instancia real y el keyword de `run_rclone`.
- `_SYNC_LAG_S` sigue siendo constante del módulo: se inyecta **quién** espera, no cuánto.

- [ ] **Step 1: Write the failing tests** — `run_rclone(entorno=...)` usa el `ejecutar` inyectado; y un test de neutralidad que compruebe que las ocho piezas de `ENTORNO_REAL` son las de hoy (`hostname() == socket.gethostname()`, `esperar is time.sleep`, `work_dir()` con prefijo `fd_biblio_`, `ahora()` acaba en `Z`…).
- [ ] **Step 2: Run tests to verify they fail** (`AttributeError: … has no attribute 'ENTORNO_REAL'`).
- [ ] **Step 3: Write the implementation** — extraer el cuerpo de `run_rclone` a `_ejecutar_rclone_real` **sin tocar una línea** (mismos flags, `encoding="utf-8"`, `errors="replace"`).
- [ ] **Step 4: Verify neutralidad**

```bash
python -m pytest tests/test_repository_cli.py tests/test_repository_checkout.py tests/test_repository_cli_guard_pull.py -q
```

Los 35 previos verdes **sin haberlos tocado**. Si alguno cambia, el refactor no es neutral: revísalo, no lo adaptes.

---

### Task 2: `FakeDrive` — promover el doble del PR #156 y fijarlo al contrato

**Files:**
- Create: `tests/_dobles/__init__.py`, `tests/_dobles/fake_drive.py`, `tests/_fixtures/rclone_v1735/`, `tests/test_fake_drive.py`
- Modify: `tests/test_repository_cli_guard_pull.py` (consumir el doble común)

**Interfaces:**

```python
class FakeDrive:
    def escribir(self, rel: str, data: bytes, *, google_native: bool = False) -> None
    def leer(self, rel: str) -> bytes | None
    def borrar(self, rel: str) -> None
    def rutas(self) -> list[str]
    def md5(self, rel: str) -> str | None      # None si google_native
    def snapshot(self) -> dict[str, str]       # {rel: md5|"<native>"} para death tests
    def bytes_snapshot(self) -> dict[str, bytes]   # para evidencia y protocolo

class FakeRclone:
    def __init__(self, drive, *, fallos=None, hook=None) -> None
    registro: list[list[str]]
    def __call__(self, cmd) -> subprocess.CompletedProcess
```

Semántica obligatoria, toda derivada del contrato medido:

- **`fallos`**: `{"moveto": [1], "copyto:00_Input/_caso.md": [2]}` — falla la enésima ocurrencia de ese subcomando (opcionalmente acotada a una ruta). Cada entrada scriptea `returncode`, `stdout` y `stderr`, para poder modelar el inventario truncado.
- **`hook`**: `Callable[[int, list[str], FakeDrive], None]` invocado **antes** de aplicar la operación N. Es la pieza que permite **interleaving determinista sin hilos** (Task 6) y mutar el Drive a mitad de un flujo. Sustituye a las «lecturas obsoletas» de la rev. 1 (ver Task 6).
- `--files-from` **junto a** `--exclude`/`--include`/`--filter` → `returncode=1` con el mensaje real. Nunca ignorarlos.
- `--files-from` con entradas inexistentes → se omiten, `returncode=0`.
- `check --one-way` → compara **md5**; cuenta diferencias y faltantes en destino; **ignora extras**; `returncode=1` si hay alguna.
- `--backup-dir` → mueve ahí la versión **del destino** que se sobrescribe, con jerarquía.
- `--log-file` → **crea el fichero**. Sin esto `_upload_evidencia` hace `if p.exists()` y se salta la subida en silencio: un test de CP9 pasaría por el motivo equivocado.
- `copyto` de origen ausente → `returncode=3`; `lsjson` de ruta ausente → `returncode=3` y `stdout="["`.
- Remoto se distingue de local por la cadena de conexión (`remote,team_drive=…:`), como hace `remote_arg`; se reconocen también las formas con `root_folder_id`.
- Comando o flag **no soportado** → `AssertionError`, no éxito permisivo. Un doble que dice «sí» a todo no prueba nada.

**Fixtures grabadas** en `tests/_fixtures/rclone_v1735/`, cada una con una cabecera
que diga de dónde salió y si es real-sanitizada o sintética:

| Fixture | Origen |
|---|---|
| `lsjson_drive.json` | captura real del backend Drive, **nombres y hashes sustituidos** |
| `lsjson_local.json` | captura real del backend local (13 hashes, sin `ID`, otro `ModTime`) |
| `lsjson_native.json` | **SINTÉTICA** — no existe ninguna en el Drive canónico (0 en 3007) |
| `lsjson_vacio.json`, `lsjson_truncado.txt` | inventario vacío y `"["` de una ruta ausente |
| `files_from_con_filtros.txt` | el `stderr` real del `CRITICAL` |

- [ ] **Step 1: Write the failing tests** — el doble se valida **contra el parser real** `parse_inventario_lsjson` **y contra las fixtures**, no contra JSON construido a su medida. Como mínimo: las tres variantes de native → `hash is None`; `--files-from` + `--exclude` → rc 1; `check` por md5 con extras en destino ignorados; `--backup-dir` recibe la versión del destino; `--log-file` crea el fichero; `hook` se invoca antes de la operación N; comando no soportado → `AssertionError`.
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Write the implementation**
- [ ] **Step 4: Migrar los 8 tests del guard** a `entorno_de_prueba` + `FakeRclone` comunes, **sin cambiar un solo aserto de comportamiento**. Ese es el criterio de que el doble común es al menos tan capaz como el embrionario.

```bash
python -m pytest tests/test_fake_drive.py tests/test_repository_cli_guard_pull.py -q
```

---

### Task 3: Caracterización de `cmd_checkout`

**Files:** Create `tests/test_repository_cli_checkout.py`.
**Interfaces:** helper local `args_checkout(**kw) -> argparse.Namespace`. **Y un smoke test por `build_parser().parse_args([...])`**, para que el entrypoint público no quede fuera (los helpers de `Namespace` lo eluden).

- [ ] `caso_prestado_aborta_con_2_y_sin_copiar` — **death snapshot** del árbol completo (Drive y local) antes/después, no solo «no hay `copy`».
- [ ] `caso_en_conflicto_aborta_con_2`
- [ ] `dry_run_no_escribe_lock_ni_copia` — Drive byte-idéntico.
- [ ] `nonce_ajeno_tras_el_sync_lag_aborta_sin_copiar` — con `hook`, no con lecturas obsoletas.
- [ ] `camino_feliz_orden_de_operaciones` — posiciones **relativas** en el `registro`: push del lock → relectura → `copy` → `MANIFEST` → pull del log → push del log.
- [ ] `camino_feliz_escribe_lock_completo` — `checkout_maquina == "PC-TEST"` y `checkout_timestamp` del `Entorno`, no del reloj real.
- [ ] `camino_feliz_no_baja_el_protocolo` — sin `_caso.md`, sin `_intake_log.jsonl`, sin `90_Notas personales/` en local.
- [ ] `camino_feliz_conserva_cuerpo_y_metadatos_del_caso_md` — ya cubierto por el guard; aquí se re-asierta desde el doble común.
- [ ] `manifest_contiene_el_inventario_y_se_sube`
- [ ] `fallo_de_copy_revierte_el_lock_y_devuelve_1`
- [ ] `evento_case_checkout_con_los_campos_del_contrato` — hoy incluye `ruta_local`; **la SPEC §6.1 la retira en la Fase 2**, y este test es el que habrá que actualizar entonces. Dejarlo dicho en el propio test.
- [ ] `esperar_se_llama_una_vez_con_el_sync_lag` — sin dormir.

**Si alguno falla, es un bug vivo que no conocíamos: para y repórtalo.**

---

### Task 4: Caracterización de `cmd_checkin`

**Files:** Create `tests/test_repository_cli_checkin.py`. Helpers `args_checkin` + `montar_checkin` + smoke test por `build_parser`.

- [ ] `ruta_local_inexistente_devuelve_2` — y cero comandos.
- [ ] `inventario_de_drive_invalido_devuelve_1` — con la fixture `lsjson_truncado.txt`.
- [ ] `dry_run_escribe_delta_y_no_toca_nada` — el `DELTA_PREVIO.md` en el `work_dir` **inyectado**.
- [ ] `borrados_sin_yes_devuelve_3`
- [ ] `plan_solo_copy_local_sube_y_verifica_con_la_misma_lista`
- [ ] `preserve_drive_no_se_sube`
- [ ] `conflicto_escribe_estado_conflicto_y_no_libera`
- [ ] `veto_de_grupo_no_libera_el_lock` (N6c)
- [ ] `fallo_de_copy_no_propaga_borrados` — cero `moveto`.
- [ ] `camino_verde_libera_el_lock_con_traza` — `ultimo_checkin_timestamp` y `ultimo_checkin_auditlog`.
- [ ] `bandeja_se_integra_y_se_vacia`
- [ ] `bandeja_con_colision_va_a_reingesta` — anotando que `MEJORAS #101` dice que nadie lo reconcilia después.
- [ ] `caracterizacion_temporal_A2_orden_actual_del_camino_verde` — **etiquetado como andamio**: fija el orden que hoy tiene (`check` → evento → bandeja → liberación) y que la Fase 2 va a cambiar. Su docstring debe decir: *«la Fase 2 elimina o actualiza este test en el mismo commit que retira el `xfail` de A-2»*. Es el único aserto que congela un defecto; los demás fijan efectos estables.

---

### Task 5: Matriz de fallos por call-site

Lo que el informe llamó, con razón, la frontera cuyo retorno decide pérdida,
auditoría o liberación. **Los cinco puntos de lectura del protocolo ya los cubre el
PR #156**; esta tarea cubre el resto.

**Files:** Create `tests/test_repository_cli_fallos.py`.

Tabla que el test implementa, una fila por caso — *call site → fallo inyectado →
`rc` → snapshot Drive/local → estado del lock*:

| Call site | Fallo | Qué se exige |
|---|---|---|
| `_leer_manifest` | fichero ausente | degrada a merge de 2 vías; hoy **en silencio** → que quede declarado en el DELTA |
| `_leer_manifest` | JSON corrupto | idem, y no revienta |
| `lsjson` de CP1 | truncado | `InventarioInvalido` → `rc=1`, cero mutación |
| `lsjson` de `_integrar_bandeja` | truncado | devuelve `(0,0)` y **no** libera creyendo la bandeja vacía |
| `check` | `rc=1` | amarillo, lock conservado |
| semáforo | copia fallida | **el «rojo» de orquestación es inalcanzable**: `cmd_checkin` retorna antes de `clasificar_semaforo`. Fijarlo como hecho y no como intención |
| subida del `MANIFEST` | falla | hoy el retorno se **ignora**: declararlo |
| `_upload_evidencia` | falla | idem |
| artefactos del protocolo | — | **todos** dentro del `work_dir` inyectado; nada en el árbol del caso |
| CP11 | `estado_repositorio` ausente | `MEJORAS #93-B`: hoy lanza `TransicionInvalida` **después** de mover bytes, registrar el evento e integrar la bandeja. **No se arregla aquí**; se caracteriza en su propio test para que la Fase 2 lo tenga medido |

---

### Task 6: Los siete defectos, reproducidos

**Files:** Create `tests/test_repository_cli_defectos.py`, con la cabecera que
explique el ciclo de vida de los `xfail` y enlace al informe.

**Reglas, todas derivadas del informe:**

- `@pytest.mark.xfail(strict=True, raises=AssertionError, reason="A-1 · …")`. Sin `raises=`, cualquier excepción de fixture o montaje cuenta como éxito y el «7 xfailed» no demuestra nada.
- Las precondiciones del montaje deben lanzar **otra** excepción (`RuntimeError`), de modo que el único `AssertionError` posible sea el aserto normativo final.
- **Nada de lecturas obsoletas.** El informe tiene razón: encolar una lectura antigua *asumía la conclusión*, y la evidencia del repo va en contra (`MEJORAS #94` documenta que el **montaje** miente mientras rclone/API devuelve el contenido real). El interleaving se produce con el `hook` del doble: ambos CP0 terminan antes del primer push, que es un escenario trivialmente real (dos procesos arrancados con segundos de diferencia) y no necesita ninguna propiedad discutible del backend.

- [ ] **`A-1 · doble titular`** — con `hook`: durante el flujo de A, tras su CP0 y antes de su push, se ejecuta el CP0 de B. Hoy ambos terminan con `rc=0` y copia local. Se exige exactamente un titular.
- [ ] **`A-1 · rollback ajeno`** — con `hook`: A verifica su nonce; **entonces** el hook instala el lock de B; luego falla el `copy`. Hoy A cancela con el frontmatter que tenía en memoria y borra el lock de B. Se exige `LOCK_NOT_MINE` (SPEC §10). *(Sin el hook este test no era construible: `fallos` solo altera retornos, y sembrar B antes hace que A aborte en CP0.)*
- [ ] **`A-2 · orden del checkin`** — se exige integrar bandeja → verificar → evento → liberar.
- [ ] **`A-2 · bandeja fallida libera el lock`** — `fallos={"moveto": [1]}`; se exige `estado_repositorio == "prestado"`.
- [ ] **`A-2 · checkin reentrante duplica el evento`** — dos checkins en verde. **Capturar explícitamente la `TransicionInvalida` de CP11** (`MEJORAS #93-B`) para poder llegar a contar los eventos; si no, el `xfail` se satisface con ese traceback sin comprobar la duplicidad.
- [ ] **`B0-2 · el log canónico se reescribe y se corrompe`** — sembrar `b'{"event":"a"}\n\n{"event":"\xff"}'` sin salto final; se exige que los bytes de las líneas preexistentes sobrevivan **idénticos**.
- [ ] **`B0-2 · el baseline no cubre el log`** — **representación cerrada**: se exige un artefacto `MANIFEST_LOG.json` en el `work_dir` del checkout con `{"hash": <md5 del log>, "lineas": <n>}`. Sin fijar el fichero y el contrato, el aserto era inasertable.

```bash
python -m pytest tests/test_repository_cli_defectos.py -q -rxX
```

Expected: **7 xfailed, 0 xpassed**.

---

### Task 7: Gobernanza

- [ ] `PLAN.md`: `[x]` a la Fase 0 con el hash del PR.
- [ ] Docstring de `scripts/repository_cli.py`: actualizar la «Nota de alcance», que el PR #156 ya dejó a medio camino (dice que hay tests de orquestación «del guard»; tras esta fase hay banco completo). Decir qué sigue **sin** cubrir: rclone real, Drive real, cuota de API.
- [ ] Suite completa + guards de docs.

**Criterio de salida de la Fase 0** (corregido; el de la rev. 1 sobreclamaba):

1. La **brecha 14** del §11 de la SPEC está cerrada: existe doble contractual y hay caracterización de `cmd_checkout`/`cmd_checkin`.
2. Los **siete defectos** del frontal están reproducidos en `xfail(strict=True, raises=AssertionError)`.
3. La **matriz de fallos** de la Task 5 cubre todos los retornos hoy ignorados.
4. El arnés de la matriz del §14.1 queda **preparado para consumirse en la Fase 1** — no ejecutado íntegramente aquí: sus filas de scratch, registro local ausente y resolución por capacidades son de la Fase 1, y las brechas 8-13 y 15 son de las Fases 1-3.
5. Ningún test puede tocar rclone real, el Drive real ni `CASOS_ROOT`.

---

## Riesgos y trampas conocidas

- **La Task 1B es el punto de mayor riesgo del plan** (toca el camino que mueve los bytes). Mitigación: va **después** de la caracterización, y el juez son los 35 tests previos más los de las Tasks 3-4.
- **`pytest-randomly`**: orden aleatorio. `FakeDrive` se construye por test, nunca a nivel de módulo.
- **`tmp_casos_root` no es `autouse`** — la barrera de la Task 0 es lo que cubre ese hueco.
- **`ts_compacto()` tiene resolución de minuto**: dos pulls en el mismo minuto reutilizan el nombre de fichero temporal. Hoy es inocuo, pero un test que dependa de nombres únicos dentro del mismo minuto es frágil.
- **`_md5` usa MD5 a propósito** (paridad con la Drive API): el doble usa el mismo algoritmo o los `check` no cuadran.
- **No confundir «reproducir» con «arreglar»**. Y si un `xfail` no falla, es un resultado valioso: se documenta y se retira del §20 de la SPEC.

## Fuera de alcance de la Fase 0

- Arreglar cualquiera de los siete defectos (Fase 2), incluido `MEJORAS #93-B`.
- Tocar `core/repository_checkout.py` (cerebro puro, ya cubierto).
- Cualquier pieza del `CaseWorkspace` (Fase 1).
- Dobles de CRM y Gmail (Fase 3).
- `MEJORAS #96`, `#101`, `#102`, `#104`.
- Verificar contra `G:` o rclone real.
