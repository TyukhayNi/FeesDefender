# Dual workspace — Fase 0: banco de pruebas del frontal — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Poner el ciclo `checkout`/`checkin` bajo test de **orquestación** —hoy no
tiene ninguno— sin cambiar una coma de su comportamiento. Al terminar: el orden
exacto de las operaciones contra Drive es observable en un test, los siete
defectos que la revisión adversarial encontró en el frontal están **reproducidos
en código** (no descritos en prosa), y la Fase 2 puede tocar el lock con red
debajo.

**Architecture:** Un único punto de inyección, `Entorno`, que agrupa las cuatro
fuentes de no-determinismo del frontal: el runner de rclone, el reloj, el
hostname y el directorio temporal de trabajo. `ENTORNO_REAL` reproduce
exactamente lo de hoy. Frente a él, un doble en memoria (`FakeDrive` +
`FakeRclone`) que **miente como Drive**: sirve lecturas obsoletas, tiene ficheros
Google-native sin MD5, y puede hacer fallar una operación concreta. Los tests se
parten en dos bloques: caracterización (verde, red de seguridad) y reproducción
de defectos (`xfail(strict=True)`, que es la lista de trabajo de la Fase 2).

**Tech Stack:** Python 3.11+, `argparse` (el frontal), `pytest` (+
`pytest-randomly`: la suite corre en orden aleatorio), stdlib
(`dataclasses`, `json`, `hashlib`, `pathlib`). Sin dependencias nuevas. **Sin red
y sin `rclone` instalado**: la suite no toca `G:` ni el binario.

## Global Constraints

- **Fuente única del diseño:** `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md` (rev. 2), §12 «Fase 0» y §14. No se reabren sus decisiones. El informe que las justifica: `2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md`.
- **Este plan SUSTITUYE las Tareas 1-3** de `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md`, que quedan marcadas como supersedidas (Task 6). La Fase 1 sigue viviendo allí.
- **Cero cambio de comportamiento.** Es la restricción dura de toda la fase. Con `ENTORNO_REAL` (el default) el frontal ejecuta los mismos comandos, en el mismo orden, con los mismos códigos de salida. Los 27 tests de `tests/test_repository_cli.py` deben pasar **sin tocarlos**.
- **Ningún bug se arregla aquí.** Los defectos se reproducen en `xfail(strict=True)` citando su identificador (`A-1`, `A-2`, `B0-2`). Un `xfail` que empieza a pasar **rompe la suite**: es la alarma de que alguien lo arregló sin actualizar el plan. Si al escribir un test descubres que el defecto **no** existe, **para y repórtalo**: puede ser un falso positivo de la revisión, y eso cambia la Fase 2.
- **Sin esperas reales.** `_SYNC_LAG_S` son 4 segundos por checkout. El `Entorno` inyecta `esperar`, y en tests es un no-op que solo cuenta llamadas. Un test que duerma de verdad es un test mal escrito.
- **Sin no-determinismo en los asertos.** Timestamp, hostname y directorio temporal salen del `Entorno`. Ningún test compara contra `now_iso_utc()` real ni contra `socket.gethostname()`.
- **Datos SIEMPRE sintéticos** (`BaRS9 - Prueba - (W-TEST99) - Vuelta`), cero PII, cero rutas de terceros. Es la norma del fichero de tests existente y de `docs/SEGURIDAD_DATOS.md`.
- **Rutas Windows.** El frontal compone rutas remotas con `/` y locales con `Path`. El doble normaliza a POSIX en su índice, igual que `parse_inventario_lsjson`. Un test que dependa del separador nativo es un test frágil.
- **Encoding:** UTF-8 sin BOM (`encoding="utf-8"`) en todo. El doble guarda **bytes**, no `str`: la mitad de `B0-2` es precisamente un byte que no decodifica.
- **Comandos desde la raíz del worktree**, con el venv del repo. El worktree no tiene `.venv` propio: usar `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`.
- **Suite completa verde antes del PR.** El CI del PR solo corre `leak-scan`; pytest es responsabilidad local. Conteo por `--junit-xml`, no por el resumen de la tubería.

---

## File Structure

| Fichero | Responsabilidad | Cambio |
|---|---|---|
| `scripts/repository_cli.py` | Frontal del checkout/checkin | **Modificar:** `Entorno` + `ENTORNO_REAL`; los 7 helpers de I/O y los 2 `cmd_*` lo reciben. Docstring §Nota de alcance reescrito |
| `tests/_dobles/__init__.py` | Paquete de dobles reutilizables | **Crear** |
| `tests/_dobles/fake_drive.py` | `FakeDrive` + `FakeRclone` + `entorno_de_prueba()` | **Crear** |
| `tests/test_fake_drive.py` | El doble también se prueba | **Crear** |
| `tests/test_repository_cli_checkout.py` | Caracterización de `cmd_checkout` | **Crear** |
| `tests/test_repository_cli_checkin.py` | Caracterización de `cmd_checkin` | **Crear** |
| `tests/test_repository_cli_defectos.py` | Los 7 `xfail(strict=True)` de A-1 / A-2 / B0-2 | **Crear** |
| `tests/test_repository_cli.py` | Helpers puros (existente) | **Modificar:** solo añadir los 2 tests de neutralidad del `Entorno` |
| `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md` | Plan combinado | **Modificar:** Tareas 1-3 supersedidas por este plan |
| `PLAN.md` | Cola y estado | **Modificar** (Task 6) |

Tres ficheros de test y no uno: `checkout` y `checkin` son sujetos distintos y
cambian por motivos distintos; los defectos van aparte porque su ciclo de vida es
otro (mueren al arreglarse, en la Fase 2).

---

### Task 1: `Entorno` — un solo punto de inyección para las cuatro fuentes de no-determinismo

`run_rclone` (`scripts/repository_cli.py:352`) es el único punto de I/O, pero no
es el único obstáculo para testear la orquestación. Hay cuatro:

| Fuente | Dónde | Por qué bloquea el test |
|---|---|---|
| `run_rclone` | `:352`, 7 llamadores | ejecuta el binario real |
| `now_iso_utc()` | `cmd_checkout:416`, `cmd_checkin:502`, `_append_evento_drive:758` | el timestamp entra en nombres de artefacto y en el lock |
| `socket.gethostname()` | `cmd_checkout:418` | el hostname entra en el lock |
| `_tmp_dir()` | `:677`, `mkdtemp` | los artefactos (`DELTA_PREVIO.md`, logs) caen en un directorio que el test no conoce |
| `time.sleep(_SYNC_LAG_S)` | `cmd_checkout:446` | 4 s por invocación |

Inyectarlas de una en una son cinco keywords que hay que propagar por siete
helpers. Un objeto las agrupa y deja la firma estable para la Fase 2.

**Files:**
- Modify: `scripts/repository_cli.py` (`run_rclone`, `_tmp_dir`, `cmd_checkout`, `cmd_checkin`, `_integrar_bandeja`, `_upload_evidencia`, `_append_evento_drive`, `_pull_caso_md`, `_push_caso_md`)
- Test: `tests/test_repository_cli.py` (añadir al final)

**Interfaces:**

```python
@dataclass(frozen=True)
class Entorno:
    """Fuentes de no-determinismo del frontal, inyectables en test."""
    ejecutar: Callable[[list[str]], subprocess.CompletedProcess]
    ahora: Callable[[], str]                 # ISO-8601 UTC con Z
    hostname: Callable[[], str]
    work_dir: Callable[[], Path]
    esperar: Callable[[float], None]

ENTORNO_REAL = Entorno(
    ejecutar=_ejecutar_rclone_real,   # el cuerpo actual de run_rclone
    ahora=now_iso_utc,
    hostname=socket.gethostname,
    work_dir=lambda: Path(tempfile.mkdtemp(prefix="fd_biblio_")),
    esperar=time.sleep,
)
```

- `run_rclone(cmd, *, entorno: Entorno = ENTORNO_REAL)` conserva la firma posicional y el comportamiento.
- `cmd_checkout(args, *, entorno=ENTORNO_REAL)` y `cmd_checkin(args, *, entorno=ENTORNO_REAL)`; el `entorno` se propaga **por parámetro explícito** a todos los helpers de I/O que invocan.
- **Prohibido** resolverlo por variable global mutable o por `monkeypatch` como mecanismo de producción: el objetivo es una costura, no un truco de test.
- `_SYNC_LAG_S` se mantiene como constante del módulo; lo que se inyecta es **quién espera**, no cuánto.

- [ ] **Step 1: Write the failing tests**

Añadir al final de `tests/test_repository_cli.py`:

```python
# --- Entorno inyectable (Fase 0, spec §12) -----------------------------------

def test_run_rclone_usa_el_entorno_inyectado(cli):
    vistos: list[list[str]] = []

    def _ejecutar(cmd):
        vistos.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    entorno = dataclasses.replace(cli.ENTORNO_REAL, ejecutar=_ejecutar)
    res = cli.run_rclone(["rclone", "version"], entorno=entorno)

    assert vistos == [["rclone", "version"]]
    assert res.returncode == 0


def test_entorno_real_conserva_los_valores_de_hoy(cli):
    # Neutralidad: el default no cambia nada. Si alguien sustituye una de estas
    # cuatro piezas por otra, este test lo caza.
    e = cli.ENTORNO_REAL
    assert e.ahora is not None and e.ahora().endswith("Z")
    assert e.hostname() == socket.gethostname()
    assert e.esperar is time.sleep
    d = e.work_dir()
    assert d.is_dir() and d.name.startswith("fd_biblio_")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_repository_cli.py -k "entorno" -v
```

Expected: 2 FAILED con `AttributeError: module 'scripts.repository_cli' has no attribute 'ENTORNO_REAL'`.

- [ ] **Step 3: Write the implementation**

Extraer el cuerpo actual de `run_rclone` a `_ejecutar_rclone_real` **sin tocar una línea** (mismos flags, mismo `encoding="utf-8"`, mismo `errors="replace"`), definir `Entorno`/`ENTORNO_REAL`, y propagar el keyword. Sustituir en `cmd_checkout`/`cmd_checkin` las cuatro llamadas directas (`now_iso_utc()`, `socket.gethostname()`, `_tmp_dir()`, `time.sleep(...)`) por las del `entorno`.

- [ ] **Step 4: Verify the refactor is behaviour-neutral**

```bash
python -m pytest tests/test_repository_cli.py tests/test_repository_checkout.py -q
```

Expected: los 27 tests previos verdes **sin haberlos tocado**, más los 2 nuevos. Si alguno de los 27 cambia, el refactor no es neutral: revísalo, no lo adaptes.

---

### Task 2: `FakeDrive` — un doble que miente como Drive

Un `Mock` que devuelve `returncode=0` no vale: los tres defectos del frontal
salen de la consistencia eventual, de los Google-native sin MD5 y de las
operaciones que fallan a mitad. El doble tiene que poder mentir igual.

**Files:**
- Create: `tests/_dobles/__init__.py`, `tests/_dobles/fake_drive.py`
- Test: `tests/test_fake_drive.py`

**Interfaces:**

```python
class FakeDrive:
    """Árbol remoto en memoria: {relpath_posix: bytes}, más los sin-MD5."""
    def escribir(self, rel: str, data: bytes, *, google_native: bool = False) -> None
    def leer(self, rel: str) -> bytes | None
    def borrar(self, rel: str) -> None
    def existe(self, rel: str) -> bool
    def rutas(self) -> list[str]
    def md5(self, rel: str) -> str | None      # None si google_native
    def snapshot(self) -> dict[str, str]       # {rel: md5|"<native>"} para death tests

class FakeRclone:
    def __init__(self, drive: FakeDrive, *,
                 lecturas_obsoletas: dict[str, list[bytes]] | None = None,
                 fallar: dict[str, list[int]] | None = None) -> None
    registro: list[list[str]]     # TODOS los comandos, en orden
    def __call__(self, cmd: list[str]) -> subprocess.CompletedProcess
```

Subcomandos que interpreta (los seis que el frontal usa) y su semántica:

| Comando | Semántica del doble |
|---|---|
| `copyto A B` | Un fichero. Si `A` es remoto → escribe el local; si `B` es remoto → escribe el drive. `returncode=1` si el origen no existe |
| `copy A B [--files-from f]` | Árbol. Respeta `--files-from`; **si no lo hay, aplica las exclusiones `--exclude` del propio comando** (es lo que hace que el checkout no baje `_caso.md`, y omitirlo falsearía la Fase 2) |
| `lsjson D -R --hash` | `stdout` con el JSON que espera `parse_inventario_lsjson`: `Path`, `Size`, `IsDir`, `Hashes.md5` (ausente en los native) |
| `check L D --one-way [--files-from]` | Compara por md5. `returncode=1` si falta o difiere alguno |
| `moveto A B` | Copia y borra el origen. Remoto→remoto (backup-dir, bandeja) |
| `rmdirs D` | No-op que devuelve 0 |

Detalles que **no** son opcionales:

- **`--log-file`**: si el comando lo trae, el doble **crea el fichero** con una línea. Sin esto, `_upload_evidencia` (`:727-733`) hace `if p.exists()` y se salta la subida en silencio: un test de CP9 pasaría por el motivo equivocado.
- **`lecturas_obsoletas`**: cola por ruta remota; cada lectura de esa ruta consume un elemento y devuelve **ese** contenido en lugar del real. Es el modelo del sync lag, y es lo que hace reproducible `A-1` sin hilos ni `sleep`.
- **`fallar`**: `{"moveto": [1]}` hace fallar la **primera** operación `moveto` (índice 1-based por tipo de subcomando) con `returncode=1`. Permite el «la bandeja falla y el lock se libera igual».
- **Distinguir remoto de local por la cadena de conexión** (`remote,team_drive=...:`), como hace `remote_arg` (`:149-164`). No por heurística de letra de unidad.
- **Helper de siembra:** `sembrar_caso(drive, *, estado="disponible", **lock)` escribe `00_Input/_caso.md` con el frontmatter del lock usando `core.utils.write_md`, para no duplicar el formato del frontmatter en los tests.
- **Helper de entorno:** `entorno_de_prueba(drive, *, ahora="2026-07-29T10:00:00Z", host="PC-TEST", work_dir=..., **kw) -> tuple[Entorno, FakeRclone]`.

- [ ] **Step 1: Write the failing tests**

En `tests/test_fake_drive.py`, como mínimo:

```python
def test_copyto_ida_y_vuelta(tmp_path):
    drive = FakeDrive()
    (tmp_path / "x.txt").write_bytes(b"hola")
    fake = FakeRclone(drive)
    fake(["rclone", "copyto", str(tmp_path / "x.txt"), "r,team_drive=T:00_Input/x.txt"])
    assert drive.leer("00_Input/x.txt") == b"hola"
    fake(["rclone", "copyto", "r,team_drive=T:00_Input/x.txt", str(tmp_path / "y.txt")])
    assert (tmp_path / "y.txt").read_bytes() == b"hola"


def test_lsjson_omite_native_del_hash_y_lo_declara(tmp_path):
    drive = FakeDrive()
    drive.escribir("doc.pdf", b"a")
    drive.escribir("hoja", b"", google_native=True)
    out = FakeRclone(drive)(["rclone", "lsjson", "r,team_drive=T:", "-R", "--hash"]).stdout
    inv = parse_inventario_lsjson(out)          # el parser REAL, no una copia
    assert inv["doc.pdf"]["hash"] is not None
    assert inv["hoja"]["hash"] is None


def test_lecturas_obsoletas_sirven_lo_viejo_una_vez(tmp_path):
    drive = FakeDrive()
    drive.escribir("00_Input/_caso.md", b"NUEVO")
    fake = FakeRclone(drive, lecturas_obsoletas={"00_Input/_caso.md": [b"VIEJO"]})
    fake(["rclone", "copyto", "r,team_drive=T:00_Input/_caso.md", str(tmp_path / "a")])
    assert (tmp_path / "a").read_bytes() == b"VIEJO"
    fake(["rclone", "copyto", "r,team_drive=T:00_Input/_caso.md", str(tmp_path / "b")])
    assert (tmp_path / "b").read_bytes() == b"NUEVO"


def test_copy_respeta_las_exclusiones_del_comando(tmp_path):
    # Sin esto el checkout del doble bajaría _caso.md y la Fase 2 se diseñaría
    # sobre una mentira.
    ...

def test_fallar_afecta_solo_a_la_ocurrencia_indicada(tmp_path): ...
def test_registro_preserva_el_orden(tmp_path): ...
def test_check_devuelve_1_si_difiere_un_md5(tmp_path): ...
def test_log_file_se_crea(tmp_path): ...
```

- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Write the implementation**
- [ ] **Step 4: Verify**

```bash
python -m pytest tests/test_fake_drive.py -q
```

El doble se valida **contra el parser real** (`parse_inventario_lsjson`), no contra una reimplementación: si el formato del `lsjson` del doble se desviase, este test lo caza antes de que envenene los demás.

---

### Task 3: Caracterización de `cmd_checkout`

Red de seguridad: fija lo que hoy hace bien, para que la Fase 2 pueda cambiar el
orden sin romperlo por accidente.

**Files:**
- Create: `tests/test_repository_cli_checkout.py`

**Interfaces:** helper local `args_checkout(**kw) -> argparse.Namespace` que construye el `Namespace` con los campos del parser (`case_id`, `local`, `remote_path`, `folder_id`, `remote`, `team_drive`, `user`, `dry_run`, `notas`), para no acoplar cada test a `build_parser`.

Tests (todos con `FakeDrive` sembrado y `entorno_de_prueba`):

- [ ] `caso_prestado_aborta_con_2_y_sin_copiar` — sembrado `estado: prestado`; `rc == 2` y **ningún** comando `copy` en el `registro`.
- [ ] `caso_en_conflicto_aborta_con_2` — el frontal solo comprueba `!= "disponible"`; fijarlo evita que un refactor de la Fase 2 lo relaje sin querer.
- [ ] `dry_run_no_escribe_lock_ni_copia` — `rc == 0`, el `_caso.md` del drive **byte-idéntico**, `registro` sin `copy` ni `copyto` de escritura.
- [ ] `nonce_ajeno_tras_el_sync_lag_aborta_sin_copiar` — `lecturas_obsoletas` hace que la relectura devuelva un `_caso.md` con otro nonce → `rc == 2`, cero `copy`.
- [ ] `camino_feliz_orden_de_operaciones` — el `registro` muestra, en este orden: `copyto` del `_caso.md` (push del lock) → `copyto` del `_caso.md` (relectura) → `copy` (Drive→local) → `copyto` del `MANIFEST_CHECKOUT.json` → `copyto` del log (pull) → `copyto` del log (push). Se asertan **posiciones relativas**, no la lista literal: así el test no se rompe por un comando de diagnóstico añadido.
- [ ] `camino_feliz_escribe_lock_completo` — el `_caso.md` del drive queda con `estado_repositorio: prestado`, `checkout_user`, `checkout_maquina == "PC-TEST"`, `checkout_nonce` no vacío y `checkout_timestamp == "2026-07-29T10:00:00Z"` (del `Entorno`, no del reloj real).
- [ ] `camino_feliz_no_baja_el_protocolo` — la copia local **no** tiene `00_Input/_caso.md` ni `00_Input/_intake_log.jsonl` ni `90_Notas personales/` (las exclusiones de `MERGE_EXCLUSIONS`, vía el `copy` del doble).
- [ ] `manifest_contiene_el_inventario_y_se_sube` — el `MANIFEST_CHECKOUT.json` local existe, su `inventario` cuadra con los ficheros bajados, y hay un `copyto` de ese fichero al drive.
- [ ] `fallo_de_copy_revierte_el_lock_y_devuelve_1` — `fallar={"copy": [1]}`; `rc == 1` y el drive vuelve a `estado_repositorio: disponible`.
- [ ] `evento_case_checkout_registrado_con_los_campos_del_contrato` — la última línea del log del drive es un `case_checkout` cuyo `details` trae `user`, `checkout_nonce`, `checkout_maquina`, `n_ficheros`, `manifest_hash` **y `ruta_local`** (hoy sí; la spec §6.1 la retira en la Fase 2, y este test es el que habrá que actualizar entonces — con esa nota en el propio test).
- [ ] `esperar_se_llama_una_vez_con_el_sync_lag` — sin dormir: el `Entorno` cuenta la llamada y comprueba el argumento `_SYNC_LAG_S`.

Verificar:

```bash
python -m pytest tests/test_repository_cli_checkout.py -q
```

**Si alguno falla, es un bug vivo que no conocíamos: para y repórtalo** antes de seguir.

---

### Task 4: Caracterización de `cmd_checkin`

**Files:**
- Create: `tests/test_repository_cli_checkin.py`

**Interfaces:** helper `args_checkin(**kw)` (campos del parser: los de checkout menos `notas`, más `wcode` e `yes`) + helper `sembrar_checkout(drive, tmp_path)` que deja un par local/remoto ya «prestado» con su `MANIFEST_CHECKOUT.json`, para no repetir el montaje en once tests.

- [ ] `ruta_local_inexistente_devuelve_2` — y cero comandos en el `registro`.
- [ ] `inventario_de_drive_invalido_devuelve_1` — `lsjson` con `stdout` vacío → `InventarioInvalido` capturado → `rc == 1` sin tocar nada.
- [ ] `dry_run_escribe_delta_y_no_toca_nada` — `DELTA_PREVIO.md` existe en el `work_dir` **inyectado** (por eso se inyecta), y el drive queda byte-idéntico.
- [ ] `borrados_sin_yes_devuelve_3` — un fichero borrado en local, presente e intacto en drive → `rc == 3`, drive intacto.
- [ ] `plan_solo_copy_local_sube_y_verifica_por_files_from` — el `copy` lleva `--files-from` y el `check` **el mismo** fichero de lista.
- [ ] `preserve_drive_no_se_sube` — un fichero que solo cambió en Drive no aparece en el `--files-from`.
- [ ] `conflicto_escribe_estado_conflicto_y_no_libera` — semáforo amarillo, `estado_repositorio == "conflicto"`, y **ningún** `copyto` posterior que lo devuelva a `disponible`.
- [ ] `veto_de_grupo_no_libera_el_lock` — el caso N6c: sin conflictos, con vetados → amarillo, lock intacto.
- [ ] `fallo_de_copy_no_propaga_borrados` — `fallar={"copy": [1]}` con un borrado confirmado → `rc == 1` y **cero** `moveto`.
- [ ] `camino_verde_orden_de_operaciones` — orden observado hoy: `copy` → `moveto` de borrados/renombrados → `check` → `copyto` de evidencia → `copyto` del log (evento `case_checkin`) → `moveto` de la bandeja → `copyto` del `_caso.md` (liberación). **Este test documenta el orden que la Fase 2 va a cambiar**; el `xfail` de la Task 5 es su contraparte normativa. Dejarlo escrito aquí es lo que hace visible el cambio en el diff de la Fase 2.
- [ ] `camino_verde_libera_el_lock_con_traza` — `estado_repositorio == "disponible"`, `ultimo_checkin_timestamp` y `ultimo_checkin_auditlog` escritos.
- [ ] `bandeja_se_integra_y_se_vacia` — un fichero en `_pendiente_checkin/email/…` acaba en su ruta y hay un `rmdirs`.
- [ ] `bandeja_con_colision_va_a_reingesta` — el destino existe → `_reingesta_<base>` (y anotar en el test que `MEJORAS #101` dice que nadie lo reconcilia después).

Verificar:

```bash
python -m pytest tests/test_repository_cli_checkin.py -q
```

---

### Task 5: Los siete defectos, reproducidos

**Files:**
- Create: `tests/test_repository_cli_defectos.py`

Cabecera del fichero, obligatoria:

```python
"""Defectos del frontal reproducidos en código (Fase 0 de la arquitectura dual).

Cada test describe el comportamiento CORRECTO y está marcado `xfail(strict=True)`
porque hoy no se cumple. La Fase 2 los pone en verde borrando el marcador; un
`xpass` rompe la suite a propósito: significa que alguien arregló el defecto sin
actualizar el plan.

Origen: docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md
"""
```

- [ ] **`A-1 · doble titular`.** Dos `cmd_checkout` secuenciales sobre el mismo caso; el segundo recibe una lectura obsoleta de `_caso.md` en su CP0 (que es el modelo del sync lag: pulló antes de que el primero escribiera). Hoy **ambos devuelven 0** y ambos tienen copia local escribible. Se exige exactamente un `rc == 0`.
- [ ] **`A-1 · rollback ajeno`.** A adquiere el lock; su `copy` falla (`fallar={"copy": [1]}`); entre medias el drive ya tiene el lock de B (sembrado). Hoy A ejecuta `aplicar_lock_cancelado` sobre el frontmatter que **pulló al principio** y lo pushea, borrando el lock de B. Se exige que A no toque un lock que no es suyo (`LOCK_NOT_MINE`, spec §10).
- [ ] **`A-2 · orden del checkin`.** Camino verde con bandeja no vacía. Hoy el `registro` tiene `check` **antes** de los `moveto` de la bandeja, y el `copyto` del evento `case_checkin` también antes. Se exige: integrar bandeja → `check` → evento → liberar.
- [ ] **`A-2 · bandeja fallida libera el lock`.** `fallar={"moveto": [1]}` sobre la bandeja. Hoy solo se imprime `⚠` y el lock se libera igual. Se exige `estado_repositorio == "prestado"` al terminar.
- [ ] **`A-2 · checkin reentrante duplica el evento`.** Dos `cmd_checkin` seguidos en verde. Hoy el log del drive tiene **dos** `case_checkin`. Se exige uno (clave de idempotencia, spec §8.5).
- [ ] **`B0-2 · el log canónico se reescribe y se corrompe`.** Sembrar el log con `b'{"event":"a"}\n\n{"event":"\xff"}'` (línea en blanco, byte no UTF-8, sin salto final) y llamar a `_append_evento_drive`. Hoy el resultado pierde la línea en blanco, sustituye el byte por `U+FFFD` y normaliza el final. Se exige que los bytes de las líneas preexistentes sobrevivan **idénticos**.
- [ ] **`B0-2 · el baseline no cubre el log`.** Tras un `cmd_checkout` en verde, el `MANIFEST_CHECKOUT.json` **no** tiene entrada para `00_Input/_intake_log.jsonl` (lo excluye `inventario_local` vía `MERGE_EXCLUSIONS`). Se exige que exista un baseline del log —en el manifest o en artefacto propio— porque sin él el §6.3 no es implementable.

Verificar:

```bash
python -m pytest tests/test_repository_cli_defectos.py -q -rxX
```

Expected: **7 xfailed, 0 xpassed**. Un `xpassed` con `strict=True` sale como fallo: investígalo, no lo silencies.

- [ ] **Step final:** suite completa.

```bash
python -m pytest -q --junit-xml=%TEMP%\fd_fase0.xml
```

**Criterio de salida de la Fase 0** (spec §12): la matriz del §14.1 es ejecutable para el ciclo checkout/checkin, y las brechas 8-15 del §11 tienen un test que las reproduce o las documenta.

---

### Task 6: Gobernanza — que no queden dos planes diciendo lo mismo

**Files:**
- Modify: `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md`
- Modify: `PLAN.md`
- Modify: `scripts/repository_cli.py` (docstring, §Nota de alcance)

- [ ] **Step 1:** en el plan combinado, marcar las Tareas 1-3 como **supersedidas por este plan** con un puntero, y dejar su encabezado de Fase 0 reducido a esa nota. La Fase 1 (Tareas 4-11) se queda ahí y se renumera **solo si hace falta**; si renumerar añade ruido al diff, se deja la numeración y se anota.
- [ ] **Step 2:** en `PLAN.md`, marcar `[x]` la **Fase 0** del bloque `[SIGUIENTE-DUAL-WORKSPACE]` con el hash del PR, y citar este plan.
- [ ] **Step 3:** reescribir la «Nota de alcance (MVP)» del docstring de `scripts/repository_cli.py:30-34`, que hoy afirma que la orquestación *«no se ha ejecutado en vivo»* y que *«las funciones PURAS están cubiertas por tests»*. Tras esta fase eso es falso por omisión: la orquestación está cubierta por dobles. Decirlo, y decir qué **no** cubre (rclone real, Drive real, cuota de API).
- [ ] **Step 4:** suite completa + guards de docs.

```bash
python -m pytest tests/test_docs_gobernanza.py tests/test_gobernanza_taxonomia.py -q
```

---

## Riesgos y trampas conocidas

- **El refactor de la Task 1 es el punto de mayor riesgo de todo el plan**, porque toca el camino que mueve los bytes de los expedientes. Mitigación: es puro (nada de lógica se mueve), los 27 tests existentes son el juez, y no se toca ningún `cmd_*` en la misma tarea que el doble.
- **`pytest-randomly`**: la suite corre en orden aleatorio. Ningún test puede depender del estado de otro; `FakeDrive` se construye por test, nunca a nivel de módulo.
- **Fixtures de `conftest.py`**: `tests/conftest.py` aísla `CASOS_ROOT` por test. Estos tests no lo necesitan (trabajan con `tmp_path` y el doble), pero **no deben** apoyarse en el `CASOS_ROOT` real ni en `G:`.
- **Recuento de eventos**: si algún test comprueba el tamaño de `INTAKE_EVENTS`, no se toca aquí — la Fase 0 no añade eventos.
- **`_md5` usa MD5 a propósito** (paridad con la Drive API). El doble debe usar el mismo algoritmo o los `check` no cuadrarán.
- **No confundir «reproducir» con «arreglar»**: la tentación al escribir el `xfail` de `A-1` es corregir `_push_caso_md` de paso. No. Ese cambio necesita su sub-SPEC (Fase 2) y su revisión adversarial.
- **Si un `xfail` no falla**, el hallazgo puede ser un falso positivo de la revisión. Es un resultado valioso: se documenta y se retira del §20 de la spec, no se fuerza el test para que falle.

## Fuera de alcance de la Fase 0

- Arreglar cualquiera de los siete defectos (Fase 2).
- Tocar `core/repository_checkout.py`: el cerebro es puro y ya está cubierto (30 KB de tests).
- Cualquier pieza del `CaseWorkspace` (Fase 1: `CaseRef`, registro, resolver, `intake_log`, `--case-dir`).
- Dobles de CRM y Gmail. Aquí solo Drive/rclone; los otros llegan cuando la vertical de correo entre en la Fase 3.
- `MEJORAS #96` (el guard sobre la copia prestada) y `#101`/`#102`, que son Fase 2 y backlog.
- Cualquier verificación contra `G:` o contra rclone real: la suite no los necesita ni los toca.
