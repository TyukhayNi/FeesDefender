---
estado: ejecutable
dueño: Nikolai Tyukhay
fecha: 2026-08-25
revision: 2
---

# Apertura V1 — Plan 2: la primitiva de mutex interproceso (rev. 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el mutex interproceso por caso que la decisión **D2** del §24 especifica, para que dos procesos de esta máquina no puedan operar a la vez sobre el mismo expediente.

**Architecture:** Dos capas sobre el **registro local** de la Fase 1. Una capa de exclusión (`filelock`, bloqueo nativo del sistema) sostenida solo durante una sección crítica de milisegundos, y sobre ella un **fichero de estado** `<W-CODE>.lock` con propietario, nonce y *lease*. La primera da la atomicidad; el segundo sobrevive al proceso y permite decidir el abandono por **caducidad del lease**, nunca por PID. El gestor de contexto **renueva el lease mientras el cuerpo corre**.

**Tech Stack:** Python 3.14, `filelock`, `pytest`. **Sin `psutil`** — ver §0.2.

> **Esta es la rev. 2.** La rev. 1 recibió **`NO EJECUTABLE`** en la revisión R10: **11 hallazgos, 11 confirmados** (4 críticos). La adjudicación está en el §0; el acta literal, en `docs/superpowers/specs/2026-08-25-apertura-v1-plan2-r10-adversarial-review.md`.
>
> **Lo que más importa de esa ronda:** el test que la rev. 1 presentaba como su prueba rigurosa —dos procesos reales— **pasaba en verde con la exclusión entera eliminada**, y el revisor lo ejecutó para demostrarlo. Una ronda sobre el plan cuesta una tarde; ese test habría costado la confianza en el mecanismo.

---

## 0. Adjudicación de la revisión adversarial R10 (Codex, 2026-08-25) — NO-EJECUTABLE, remediado

- **Objeto revisado:** la rev. 1 de este plan, en el commit `13542e0`.
- **Ronda:** R10, la primera que recibe este plan; corrida **antes de ejecutarlo**.
- **Revisor:** Codex por CLI sobre copia externa `git archive` sin `.git`; adjudica Claude Code contra la fuente.
- **Informe recibido:** `docs/superpowers/specs/2026-08-25-apertura-v1-plan2-r10-adversarial-review.md`, `sha256` `f896aaf988682d43cd6bdc15db2b7ef379ad1fd35b3b38f4806d4a16b3d989ab`, recomputado al archivarlo y **coincide**.
- **Hallazgos:** 11 — 4 CRÍTICOS, 2 ALTOS, 3 MEDIOS, 2 BAJOS. **11 confirmados, 0 refutados.**
- **Remediado en:** esta rev. 2, tarea por tarea.

### 0.1. Las once, una por una

| # | Sev. | Hallazgo | Veredicto | Remedio en la rev. 2 |
|---|---|---|---|---|
| H10-01 | CRÍTICO | La prueba de dos procesos **queda verde sin ninguna exclusión** | **CONFIRMADO** (el revisor lo ejecutó) | Task 8: dos hijos soltados desde una **barrera común**; mutante `nullcontext` obligatorio |
| H10-02 | CRÍTICO | Un `ahora` naïve o futuro **roba un lease vivo** | **CONFIRMADO** | `_instante()` exige offset explícito; renovación **monótona** |
| H10-03 | CRÍTICO | `lease_seconds` 0/negativo/truncado permite dos titulares | **CONFIRMADO** | `_lease_valido()`: `int` estricto positivo; `bool` y `float` rechazados |
| H10-04 | CRÍTICO | `tomado()` puede **perder el lock y seguir** | **CONFIRMADO** | Renovación **obligatoria** en hilo (decisión de Nikolai, 2026-08-25) |
| H10-05 | ALTO | El fail-closed no tiene prueba ni valida esquema | **CONFIRMADO** | Task 4: ocho estados inválidos y dos mutantes |
| H10-06 | ALTO | La primitiva **no es `O_EXCL`**, es bloqueo nativo | **CONFIRMADO** | §0.2: se declara lo que se obtiene y se fija la versión |
| H10-07 | MEDIO | `psutil.boot_time()` no es un `boot_id` estable | **CONFIRMADO** | Se retira `psutil`: identidad por **UUID de proceso** |
| H10-08 | MEDIO | El W-code **escapa de la raíz**; la constraint de herencia es falsa | **CONFIRMADO** | `_w_code_valido()` + contención comprobada; constraint reescrita |
| H10-09 | MEDIO | Se atribuye el criterio 41 sin probar sus efectos | **CONFIRMADO** | Se reclama **solo** el contrato unitario de D2 |
| H10-10 | BAJO | «Dependencias ya usadas» es **falso** | **CONFIRMADO** | Task 1 renombrada; el test parsea con `packaging` |
| H10-11 | BAJO | El argumento contra los hilos es falso | **CONFIRMADO** | Retirado; se conserva el motivo normativo |

### 0.2. Dos decisiones que la ronda obligó a tomar, no a redactar

**La primitiva NO es `O_CREAT|O_EXCL` (H10-06).** D2 dice «lockfile con creación atómica (`O_CREAT|O_EXCL`), vía `filelock`», y las dos mitades no describen lo mismo: en Windows `filelock` abre con `O_CREAT|O_TRUNC` y bloquea con `msvcrt.locking`, o sea **bloqueo nativo**, no adjudicación por creación exclusiva. Se adopta el bloqueo nativo y **se dice**, en vez de adjudicar la decisión por el nombre de la librería. El motivo es sustantivo: un lock nativo **se suelta solo cuando el proceso muere**, mientras que un fichero creado con `O_EXCL` sobrevive al cadáver y exige limpieza — y el guard cubre solo la sección crítica, así que su abandono no puede depender de nadie. `filelock` se fija a **`>=3.29,<4`**: la rev. 1 pedía `>=3.12` y citaba comportamiento medido en 3.29.0.

**El propietario es DIAGNÓSTICO; la titularidad la decide el nonce (H10-07).** Al mirar por qué el `boot_id` tenía que ser estable, aparece que no gobierna nada: `renovar` y `liberar` comparan **nonce**. El bloque de propietario existe para que un humano sepa quién tiene el caso. Con eso, la identidad puede ser un **UUID generado una vez por proceso** — estable durante su vida, distinto para cualquier otro y **sin reloj**. Se retira `psutil`, cuya única razón era `boot_time()`, que su propio docstring declara sensible a ajustes de hora y NTP.

### 0.3. Lo que sigue SIN VERIFICAR, y se declara

- **Nada de este plan se ha ejecutado.** Las once remediaciones son cambios de *plan*; su suficiencia se mide ejecutándolo, y con una ronda sobre el diff.
- **El revisor no pudo correr los tests del plan** (no existen) ni instalar dependencias. Sus comprobaciones ejecutables las hizo sobre **arneses efímeros equivalentes**, no sobre este código.
- **El comportamiento de `filelock`** bajo la versión que resuelva `>=3.29,<4` en otra máquina. Medido aquí en 3.29.0/Windows.

---

## Por qué no se reutiliza el lock de checkout

Está medido: **Drive no es un mutex**. `test_defecto_doble_titular` demuestra que un write-then-verify sobre un fichero remoto compartido no da exclusión, y `test_defecto_rollback_cancela_un_lock_ajeno`, que se libera sin comprobar titularidad. Los dos siguen vivos en `xfail` (verificado: 6 `xfailed` en ese fichero). **Ámbito de este mutex: una máquina.**

## Dónde vive

En la raíz del registro privado (`workspace_registry.raiz_por_defecto()`). El Task 5 de la Fase 1 dejó sitio a propósito: `WorkspaceRegistry.cargar()` recorre `*.json` (verificado en `workspace_registry.py:183-192`), así que un `.lock` no se confunde con una entrada. El namespace es el **W-code**, no la ruta, porque el mutex tiene que existir **antes de que la carpeta exista**.

## Global Constraints

- **Windows + PowerShell.** Rutas con `pathlib`; nada de `fcntl`.
- **Encoding UTF-8 sin BOM.**
- **`main` protegida:** rama + PR. Tests acompañan todo cambio en `core/`.
- **Dos semillas** antes de declarar la suite verde (`pytest-randomly`).
- **La raíz del mutex se valida en el propio módulo.** La rev. 1 decía que «hereda» la barrera de `WorkspaceRegistry` y **era falso**: el mutex llama a `raiz_por_defecto()` sin construir un registro (H10-08).
- **Reloj inyectado y validado.** El `ahora` es parámetro y **debe llevar offset explícito**. En producción lo suministra **`core.utils.now_iso_utc()`**, y esto es una decisión, no un detalle: el reloj mayoritario del repo es `now_iso()`, que devuelve **naïve** (`2026-08-25T20:11:46`, medido) y **`_instante()` lo rechazará**. La rev. 1 nombraba `now_iso()` sin comprobarlo — habría reventado en el primer llamador real. Son 65 usos de `now_iso` frente a 6 de `now_iso_utc` en `core/` y `scripts/`, así que quien cablee la primitiva (Plan 3) tiene que **pasar el reloj con offset explícitamente**, no heredar el de su módulo. Unificar los dos relojes del repo es un problema aparte y no entra aquí.
- **Alcance:** se reclama el **contrato unitario de D2**. El **criterio 41** exige además staging disjunto, unión conservada en cuatro artefactos y titularidad cruzada: eso es el **Plan 3** (H10-09).
- **Fuera de alcance:** el write-set de las 27 clases del §25.

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `core/casos/case_mutex.py` (nuevo) | La primitiva: validación, identidad, estado, `adquirir`/`renovar`/`liberar`/`tomado` |
| `core/casos/workspace_model.py` (modificar) | Tres errores del §10: `CaseBusy`, `MutexNotMine`, `MutexIlegible` |
| `requirements.txt` (modificar) | Introducir `filelock>=3.29,<4` |
| `tests/test_case_mutex.py` (nuevo) | Contrato unitario |
| `tests/test_case_mutex_estados_invalidos.py` (nuevo) | El fail-closed, con sus mutantes |
| `tests/test_case_mutex_concurrencia.py` (nuevo) | La carrera **de verdad**, con barrera |

---

### Task 1: Introducir `filelock` como dependencia NUEVA

> **Renombrada (H10-10).** La rev. 1 la titulaba «declarar las que ya se usan» y afirmaba que `filelock` y `psutil` estaban usados sin declarar. **Es falso**: el revisor buscó imports de ambos en todo el árbol y encontró **cero**. Estaban instalados en un venv y nada los importaba. Son dependencias **nuevas**, y `psutil` ya no entra (§0.2).

**Files:**
- Modify: `requirements.txt`
- Test: `tests/test_case_mutex.py`

**Interfaces:** produce nada de código.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_case_mutex.py
"""Contrato unitario de la primitiva de mutex por caso (decisión D2 del §24)."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
AHORA = "2026-08-25T12:00:00Z"
W = "W-MUTEX1"


@pytest.fixture
def raiz(tmp_path):
    return tmp_path / "locks"


def _requisitos() -> dict[str, str]:
    """`{nombre: especificador}` parseado de verdad, no por subcadena.

    `"filelock" in texto` pasaría con el nombre dentro de un comentario o como
    subcadena de otro paquete (R10/H10-10). `packaging` es la única lectura que
    acredita que un clon instalaría algo.
    """
    from packaging.requirements import Requirement
    reqs = {}
    for linea in io.open(RAIZ / "requirements.txt", encoding="utf-8"):
        linea = linea.split("#", 1)[0].strip()
        if not linea:
            continue
        r = Requirement(linea)
        reqs[r.name.lower().replace("_", "-")] = str(r.specifier)
    return reqs


def test_filelock_esta_declarado_con_version_fijada():
    reqs = _requisitos()
    assert "filelock" in reqs, (
        "core/casos/case_mutex.py importa filelock y requirements.txt no lo declara")
    assert ">=3.29" in reqs["filelock"], (
        "la versión se fija: el backend Windows se midió en 3.29.0 y `>=3.12` no lo "
        "reproduce (R10/H10-06)")


def test_psutil_NO_se_declara():
    """Se retiró con el `boot_id` (§0.2). Un requisito sin importador es ruido."""
    assert "psutil" not in _requisitos()
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: FAIL — `AssertionError: core/casos/case_mutex.py importa filelock y requirements.txt no lo declara`

- [ ] **Step 3: Declararla**

En `requirements.txt`, antes del bloque `# Tests`:

```
filelock>=3.29,<4        # mutex interproceso por caso (core/casos/case_mutex.py, D2 del
                         # §24). En Windows es bloqueo NATIVO (msvcrt.locking), no
                         # O_CREAT|O_EXCL: ver §0.2 del plan. Versión fijada porque ese
                         # backend es lo que se midió.
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/test_case_mutex.py
git commit -m "deps: filelock fijado a >=3.29,<4 para el mutex de D2"
```

---

### Task 2: Validar las entradas antes de tocar disco

> Cierra **tres críticos** (H10-02, H10-03, H10-08). Van juntas porque son la misma clase de defecto —una API que acepta y **persiste** valores que rompen la exclusión— y porque ninguna escribe: son puras y se prueban solas.

**Files:**
- Create: `core/casos/case_mutex.py`
- Test: `tests/test_case_mutex.py`

**Interfaces:**
- Produces:
  - `_instante(ts: str) -> float` — lanza `ValueError` sin offset explícito.
  - `_lease_valido(v) -> int` — lanza si no es `int` estricto positivo.
  - `_w_code_valido(w) -> str` — canónico; lanza si no casa `^W-[A-Z0-9]{3,20}$`.
  - `identidad_proceso() -> ProcesoID` con `host`, `pid`, `proceso_uid`.

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_case_mutex.py
class TestElRelojNoSeAceptaACiegas:
    """R10/H10-02: un timestamp sin zona se lee en hora LOCAL.

    Medido: `2026-08-25T12:00:00` y `...Z` difieren en **7.200 s**. Con el lease por
    defecto, el segundo proceso da por vencido el lock del primero al instante.
    """

    def test_un_timestamp_SIN_offset_se_rechaza(self):
        from core.casos.case_mutex import _instante
        with pytest.raises(ValueError, match="offset"):
            _instante("2026-08-25T12:00:00")

    @pytest.mark.parametrize("ts", ["2026-08-25T12:00:00Z",
                                    "2026-08-25T14:00:00+02:00"])
    def test_con_offset_son_el_MISMO_instante(self, ts):
        from core.casos.case_mutex import _instante
        assert _instante(ts) == _instante("2026-08-25T12:00:00Z")

    def test_una_cadena_que_no_es_fecha_se_rechaza(self):
        from core.casos.case_mutex import _instante
        with pytest.raises(ValueError):
            _instante("ahora mismo")


class TestElLeaseNoAceptaValoresQueLoRompen:
    """R10/H10-03: `int(0.5)` es 0 y `-1` vence al instante."""

    @pytest.mark.parametrize("malo", [0, -1, 0.5, True, False, "60", None])
    def test_valores_que_permitirian_dos_titulares(self, malo):
        from core.casos.case_mutex import _lease_valido
        with pytest.raises((TypeError, ValueError)):
            _lease_valido(malo)

    def test_un_entero_positivo_pasa(self):
        from core.casos.case_mutex import _lease_valido
        assert _lease_valido(300) == 300


class TestElWCodeNoPuedeEscaparDeLaRaiz:
    """R10/H10-08: `..\\escape` resolvía FUERA del registro. El revisor lo ejecutó."""

    @pytest.mark.parametrize("malo", ["", "   ", "..", r"..\escape", "C:/tmp/escape",
                                      "W-A/B", "W-A B", "CON", "W-", "sin-prefijo"])
    def test_un_w_code_que_no_lo_es_se_rechaza(self, malo):
        from core.casos.case_mutex import _w_code_valido
        with pytest.raises(ValueError):
            _w_code_valido(malo)

    def test_se_canoniza_a_mayusculas(self):
        from core.casos.case_mutex import _w_code_valido
        assert _w_code_valido(" w-test01 ") == "W-TEST01"


class TestIdentidadDeProceso:
    """El propietario es DIAGNÓSTICO: la titularidad la decide el nonce (§0.2)."""

    def test_es_estable_dentro_del_proceso(self):
        from core.casos.case_mutex import identidad_proceso
        assert identidad_proceso() == identidad_proceso()

    def test_NO_depende_del_reloj(self):
        """R10/H10-07: `psutil.boot_time()` cambia con NTP y con la hibernación."""
        import inspect
        from core.casos import case_mutex
        fuente = inspect.getsource(case_mutex.identidad_proceso)
        assert "boot_time" not in fuente and "psutil" not in fuente

    def test_distingue_un_PID_reutilizado(self):
        from core.casos.case_mutex import identidad_proceso
        yo = identidad_proceso()
        impostor = {"host": yo.host, "pid": yo.pid, "proceso_uid": "otro"}
        assert yo.es_el_mismo(impostor) is False
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.casos.case_mutex'`

- [ ] **Step 3: Implementación mínima**

```python
# core/casos/case_mutex.py
"""Mutex interproceso por caso — decisión D2 del §24 de la spec de apertura.

Contesta una sola pregunta: **¿puede este proceso operar ahora sobre este expediente?**
Ámbito **una máquina**: entre máquinas sigue el lock de checkout del Drive.

**La primitiva es bloqueo NATIVO, no `O_CREAT|O_EXCL`** (§0.2 del plan): en Windows
`filelock` abre con `O_CREAT|O_TRUNC` y bloquea con `msvcrt.locking`. Se elige a
propósito: un lock nativo se suelta solo cuando el proceso muere, y un fichero creado
con `O_EXCL` sobrevive al cadáver.
"""
from __future__ import annotations

import dataclasses
import os
import re
import socket
import uuid
from datetime import datetime

_RE_W_CODE = re.compile(r"^W-[A-Z0-9]{3,20}$")

#: UUID de ESTE proceso, generado al importar: estable durante su vida y distinto para
#: cualquier otro. Sustituye al `boot_id` derivado del reloj (R10/H10-07).
_PROCESO_UID = uuid.uuid4().hex


def _instante(ts: str) -> float:
    """Epoch de un ISO-8601 **con offset explícito**. Sin offset, lanza.

    `datetime.timestamp()` interpreta un datetime naïve en hora **local**: medido,
    `2026-08-25T12:00:00` y `...Z` difieren en 7.200 s, y con eso el segundo proceso da
    por vencido el lease del primero al instante (R10/H10-02).
    """
    momento = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    if momento.tzinfo is None or momento.utcoffset() is None:
        raise ValueError(
            f"el instante {ts!r} no lleva offset de zona: sin él se leería en hora "
            f"local y el lease se calcularía mal")
    return momento.timestamp()


def _lease_valido(valor) -> int:
    """`int` estricto y positivo. `bool` y `float` se rechazan (R10/H10-03)."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise TypeError(f"lease_seconds debe ser int, no {type(valor).__name__}")
    if valor <= 0:
        raise ValueError(f"lease_seconds debe ser positivo, no {valor}")
    return valor


def _w_code_valido(w_code: str) -> str:
    """Canónico en mayúsculas. Nada que pueda escapar de la raíz (R10/H10-08)."""
    canon = str(w_code or "").strip().upper()
    if not _RE_W_CODE.match(canon):
        raise ValueError(
            f"{w_code!r} no es un W-code: se espera W- seguido de 3-20 alfanuméricos. "
            f"Un valor libre acabaría componiendo una ruta fuera del registro")
    return canon


@dataclasses.dataclass(frozen=True)
class ProcesoID:
    """Quién soy. **Diagnóstico**: la titularidad la decide el nonce (§0.2)."""

    host: str
    pid: int
    proceso_uid: str

    def a_json(self) -> dict:
        return {"host": self.host, "pid": self.pid, "proceso_uid": self.proceso_uid}

    def es_el_mismo(self, otro: dict | None) -> bool:
        if not isinstance(otro, dict):
            return False
        return (otro.get("host") == self.host and otro.get("pid") == self.pid
                and otro.get("proceso_uid") == self.proceso_uid)


def identidad_proceso() -> ProcesoID:
    return ProcesoID(host=socket.gethostname(), pid=os.getpid(),
                     proceso_uid=_PROCESO_UID)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: PASS (20 tests)

- [ ] **Step 5: Commit**

```bash
git add core/casos/case_mutex.py tests/test_case_mutex.py
git commit -m "mutex D2: validar reloj, lease y W-code antes de tocar disco"
```

---

### Task 3: Los tres errores del §10

**Files:**
- Modify: `core/casos/workspace_model.py`
- Test: `tests/test_workspace_model.py`

**Interfaces:** produce `CaseBusy` (`CASE_BUSY`), `MutexNotMine` (`MUTEX_NOT_MINE`), `MutexIlegible` (`MUTEX_ILEGIBLE`), las tres en `errores_conocidos()`.

> **Nota normativa, verificada:** el «como mínimo» que permite añadir códigos está en la spec **dual** (`2026-07-29-feesdefender-dual-case-workspace-design.md:719-746`), no en la de apertura. La rev. 1 lo citaba sin decir dónde.

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_workspace_model.py
def test_los_errores_del_mutex_estan_en_la_tabla():
    from core.casos.workspace_model import (CaseBusy, MutexIlegible, MutexNotMine,
                                            errores_conocidos)
    codigos = {c.codigo for c in errores_conocidos()}
    assert {"CASE_BUSY", "MUTEX_NOT_MINE", "MUTEX_ILEGIBLE"} <= codigos
    for clase in (CaseBusy, MutexNotMine, MutexIlegible):
        assert clase in errores_conocidos()


def test_el_mensaje_del_mutex_no_lleva_rutas_ni_PII():
    from core.casos.workspace_model import CaseBusy
    exc = CaseBusy(w_code="W-TEST01", maquina="ESTA",
                   detalle=r"C:\Users\alguien\CASOS\BaRS1 - Calle Falsa 1 - (W-TEST01)")
    texto = str(exc)
    assert "W-TEST01" in texto
    assert "Calle Falsa" not in texto and "C:\\" not in texto
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_workspace_model.py -q -p no:randomly -k mutex`
Expected: FAIL — `ImportError: cannot import name 'CaseBusy'`

- [ ] **Step 3: Implementación mínima**

En `core/casos/workspace_model.py`, junto a los tres errores del registro:

```python
class CaseBusy(WorkspaceError):
    """Otro proceso de ESTA máquina tiene el mutex, y su lease sigue vivo."""

    codigo = "CASE_BUSY"
    descripcion = "otro proceso de esta maquina esta operando sobre el caso"


class MutexNotMine(WorkspaceError):
    """Se intentó renovar o liberar un mutex cuyo nonce es de otro.

    Separado de `CaseBusy` a propósito: aquel es «espera»; este es «te equivocas de
    dueño». Confundirlos es el defecto A-1 del frontal —el rollback que cancela un lock
    ajeno— trasladado a esta capa.
    """

    codigo = "MUTEX_NOT_MINE"
    descripcion = "el mutex del caso pertenece a otro titular"


class MutexIlegible(WorkspaceError):
    """El lock existe y no se puede leer o no cumple su esquema. **NO es «no hay lock».**

    Falla cerrado por la misma razón que `RegistryUnreadable` (R7/H7-02), y aquí el
    precio de confundirlos es mayor: leerlo como «libre» dejaría entrar a un segundo
    proceso, que es lo único que este módulo existe para impedir.
    """

    codigo = "MUTEX_ILEGIBLE"
    descripcion = "el mutex del caso existe y no se puede interpretar"
```

Y añadirlas a la tupla de `errores_conocidos()`.

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_workspace_model.py -q -p no:randomly`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/casos/workspace_model.py tests/test_workspace_model.py
git commit -m "mutex D2: CASE_BUSY, MUTEX_NOT_MINE y MUTEX_ILEGIBLE en la tabla del 10"
```

---

### Task 4: El estado en disco, y el fail-closed **con prueba**

> **R10/H10-05:** la rev. 1 arreglaba el fail-open y **no lo probaba**, así que un mutante que lo revirtiera pasaba entera su suite.

**Files:**
- Modify: `core/casos/case_mutex.py`
- Create: `tests/test_case_mutex_estados_invalidos.py`

**Interfaces:**
- Produces: `raiz_de_locks(raiz=None) -> Path` (valida ubicación), `ruta_del_lock(w_code, *, raiz=None) -> Path` (contención comprobada), `leer_estado(w_code, *, raiz=None) -> dict | None` (`None` **solo** si no hay fichero).

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_case_mutex_estados_invalidos.py
"""El mutex falla CERRADO: «no puedo leerlo» nunca es «está libre» (R10/H10-05)."""
from __future__ import annotations

import pytest

W = "W-MUTEX1"
AHORA = "2026-08-25T12:00:00Z"

_OK = (b'"propietario":{"host":"h","pid":1,"proceso_uid":"u"},'
       b'"acquired_at":"2026-08-25T12:00:00Z","renewed_at":"2026-08-25T12:00:00Z"')

ESTADOS_INVALIDOS = {
    "bytes_no_utf8": b"\xff\xfe\x00",
    "json_truncado": b'{"nonce": "abc"',
    "una_lista": b"[]",
    "objeto_vacio": b"{}",
    "propietario_no_objeto": b'{"schema":1,"propietario":"yo","nonce":"a",'
                             b'"acquired_at":"2026-08-25T12:00:00Z",'
                             b'"renewed_at":"2026-08-25T12:00:00Z","lease_seconds":60}',
    "nonce_vacio": b'{"schema":1,' + _OK + b',"nonce":"","lease_seconds":60}',
    "timestamp_sin_zona": b'{"schema":1,"propietario":{"host":"h","pid":1,'
                          b'"proceso_uid":"u"},"nonce":"a",'
                          b'"acquired_at":"2026-08-25T12:00:00",'
                          b'"renewed_at":"2026-08-25T12:00:00","lease_seconds":60}',
    "lease_no_positivo": b'{"schema":1,' + _OK + b',"nonce":"a","lease_seconds":-1}',
}


@pytest.fixture
def raiz(tmp_path):
    return tmp_path / "locks"


def _sembrar(raiz, datos: bytes):
    from core.casos.case_mutex import ruta_del_lock
    p = ruta_del_lock(W, raiz=raiz)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(datos)
    return p


@pytest.mark.parametrize("nombre", sorted(ESTADOS_INVALIDOS))
def test_un_estado_invalido_lanza_MUTEX_ILEGIBLE(raiz, nombre):
    from core.casos.case_mutex import leer_estado
    from core.casos.workspace_model import MutexIlegible
    _sembrar(raiz, ESTADOS_INVALIDOS[nombre])
    with pytest.raises(MutexIlegible):
        leer_estado(W, raiz=raiz)


@pytest.mark.parametrize("nombre", sorted(ESTADOS_INVALIDOS))
def test_un_estado_invalido_NO_deja_adquirir(raiz, nombre):
    """Lo que de verdad importa: un lock roto no abre el caso."""
    from core.casos.case_mutex import adquirir
    from core.casos.workspace_model import MutexIlegible
    _sembrar(raiz, ESTADOS_INVALIDOS[nombre])
    with pytest.raises(MutexIlegible):
        adquirir(W, ahora=AHORA, raiz=raiz)


@pytest.mark.parametrize("nombre", sorted(ESTADOS_INVALIDOS))
def test_los_bytes_del_estado_roto_se_CONSERVAN(raiz, nombre):
    """Un lock ilegible es evidencia: se diagnostica, no se pisa."""
    from core.casos.case_mutex import adquirir
    from core.casos.workspace_model import MutexIlegible
    original = ESTADOS_INVALIDOS[nombre]
    p = _sembrar(raiz, original)
    with pytest.raises(MutexIlegible):
        adquirir(W, ahora=AHORA, raiz=raiz)
    assert p.read_bytes() == original


def test_sin_fichero_SI_es_None(raiz):
    """Control negativo: sin él, «lanza siempre» pasaría todo lo de arriba."""
    from core.casos.case_mutex import leer_estado
    assert leer_estado(W, raiz=raiz) is None
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex_estados_invalidos.py -q -p no:randomly`
Expected: FAIL — `ImportError: cannot import name 'ruta_del_lock'`

- [ ] **Step 3: Implementación mínima**

```python
# añadir a core/casos/case_mutex.py
import json
from pathlib import Path

_CAMPOS = ("schema", "propietario", "nonce", "acquired_at", "renewed_at",
           "lease_seconds")


def raiz_de_locks(raiz: Path | None = None) -> Path:
    """La raíz, VALIDADA aquí. La rev. 1 decía que heredaba la garantía y no lo hacía."""
    from .. import config
    from .workspace_model import WorkspaceUnderCatalogRoot

    if raiz is None:
        from .workspace_registry import raiz_por_defecto
        raiz = raiz_por_defecto()
    raiz = Path(raiz).resolve()
    for prohibida, motivo in ((Path(config.settings.casos_root), "CASOS_ROOT"),
                              (Path(config.settings.project_root), "el repo")):
        try:
            prohibida = prohibida.resolve()
        except OSError:                                  # pragma: no cover - defensivo
            continue
        if raiz == prohibida or prohibida in raiz.parents:
            raise WorkspaceUnderCatalogRoot(
                detalle=f"el mutex no puede vivir bajo {motivo}")
    return raiz


def ruta_del_lock(w_code: str, *, raiz: Path | None = None) -> Path:
    base = raiz_de_locks(raiz)
    candidata = (base / f"{_w_code_valido(w_code)}.lock").resolve()
    if candidata.parent != base:
        raise ValueError("la ruta del lock escapa de la raíz del registro")
    return candidata


def _validar_estado(crudo, w_code: str) -> dict:
    from .workspace_model import MutexIlegible

    def malo(por_que: str):
        return MutexIlegible(w_code=w_code, detalle=por_que)

    if not isinstance(crudo, dict):
        raise malo("el lock no contiene un objeto")
    faltan = [c for c in _CAMPOS if c not in crudo]
    if faltan:
        raise malo(f"al lock le faltan campos: {faltan}")
    if not isinstance(crudo["propietario"], dict):
        raise malo("el propietario no es un objeto")
    if not isinstance(crudo["nonce"], str) or not crudo["nonce"]:
        raise malo("el nonce está vacío o no es texto")
    try:
        _lease_valido(crudo["lease_seconds"])
        _instante(crudo["acquired_at"])
        _instante(crudo["renewed_at"])
    except (TypeError, ValueError) as exc:
        raise malo(f"campo temporal o de lease inválido: {exc}") from exc
    return crudo


def leer_estado(w_code: str, *, raiz: Path | None = None) -> dict | None:
    """El estado, o `None` **si y solo si no hay lock**.

    Un fichero ilegible o que no cumple el esquema lanza `MutexIlegible`. Si devolviera
    `None`, `adquirir` daría el caso por libre y **dos procesos entrarían**.
    """
    from .workspace_model import MutexIlegible

    p = ruta_del_lock(w_code, raiz=raiz)
    if not p.is_file():
        return None
    try:
        crudo = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise MutexIlegible(
            w_code=w_code,
            detalle=f"el lock existe y no se puede leer: {type(exc).__name__}") from exc
    return _validar_estado(crudo, w_code)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_case_mutex_estados_invalidos.py -q -p no:randomly`
Expected: PASS (25 tests)

- [ ] **Step 5: Los dos mutantes obligatorios**

Uno por uno; **cada uno tiene que morir**. Revertir con `git checkout`, nunca a mano.

1. En `leer_estado`, sustituir el `raise MutexIlegible(...)` del `except` por `return None`
   → `test_un_estado_invalido_NO_deja_adquirir[bytes_no_utf8]` **rojo**.
2. En `_validar_estado`, sustituir el cuerpo por `return crudo`
   → `objeto_vacio`, `nonce_vacio`, `lease_no_positivo` y `timestamp_sin_zona` **rojos**.

Si alguno **no** muere, ese test no contrata nada: párate y arréglalo.

- [ ] **Step 6: Commit**

```bash
git add core/casos/case_mutex.py tests/test_case_mutex_estados_invalidos.py
git commit -m "mutex D2: esquema validado y fail-closed con sus mutantes"
```

---

### Task 5: Adquirir, el lease y la renovación monótona

**Files:**
- Modify: `core/casos/case_mutex.py`
- Test: `tests/test_case_mutex.py`

**Interfaces:** produce `adquirir(w_code, *, ahora, raiz=None, lease_seconds=LEASE_POR_DEFECTO) -> str`, `renovar(w_code, *, nonce, ahora, raiz=None) -> None`, `_caducado(estado, ahora) -> bool`.

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_case_mutex.py
class TestAdquirir:

    def test_escribe_el_estado_que_D2_exige(self, raiz):
        from core.casos.case_mutex import adquirir, identidad_proceso, leer_estado
        nonce = adquirir(W, ahora=AHORA, raiz=raiz)
        estado = leer_estado(W, raiz=raiz)
        assert estado["nonce"] == nonce and nonce
        assert estado["acquired_at"] == estado["renewed_at"] == AHORA
        assert estado["lease_seconds"] == 300
        assert identidad_proceso().es_el_mismo(estado["propietario"])

    def test_un_segundo_adquirir_con_lease_vivo_lanza_CASE_BUSY(self, raiz):
        from core.casos.case_mutex import adquirir
        from core.casos.workspace_model import CaseBusy
        adquirir(W, ahora=AHORA, raiz=raiz)
        with pytest.raises(CaseBusy):
            adquirir(W, ahora="2026-08-25T12:00:30Z", raiz=raiz)

    def test_dos_W_codes_distintos_no_se_excluyen(self, raiz):
        from core.casos.case_mutex import adquirir
        adquirir("W-AAA111", ahora=AHORA, raiz=raiz)
        adquirir("W-BBB222", ahora=AHORA, raiz=raiz)

    def test_el_registro_no_confunde_el_lock_con_una_entrada(self, raiz):
        from core.casos.case_mutex import adquirir
        from core.casos.workspace_registry import WorkspaceRegistry
        adquirir(W, ahora=AHORA, raiz=raiz)
        assert WorkspaceRegistry(raiz, ahora=AHORA).cargar() == []

    def test_un_ahora_SIN_offset_no_llega_a_escribir(self, raiz):
        from core.casos.case_mutex import adquirir, ruta_del_lock
        with pytest.raises(ValueError):
            adquirir(W, ahora="2026-08-25T12:00:00", raiz=raiz)
        assert not ruta_del_lock(W, raiz=raiz).exists()


class TestElLease:

    def test_caducado_se_puede_tomar(self, raiz):
        from core.casos.case_mutex import adquirir
        adquirir(W, ahora="2026-08-25T12:00:00Z", raiz=raiz, lease_seconds=60)
        assert adquirir(W, ahora="2026-08-25T12:01:01Z", raiz=raiz)

    def test_renovar_lo_alarga_y_lo_defiende(self, raiz):
        from core.casos.case_mutex import adquirir, renovar
        from core.casos.workspace_model import CaseBusy
        nonce = adquirir(W, ahora="2026-08-25T12:00:00Z", raiz=raiz, lease_seconds=60)
        renovar(W, nonce=nonce, ahora="2026-08-25T12:00:50Z", raiz=raiz)
        with pytest.raises(CaseBusy):
            adquirir(W, ahora="2026-08-25T12:01:01Z", raiz=raiz)

    def test_el_abandono_NO_se_decide_por_el_PID(self, raiz):
        """El corazón de H3-02: el sistema reutiliza PIDs."""
        import json
        from core.casos.case_mutex import adquirir, ruta_del_lock
        from core.casos.workspace_model import CaseBusy
        adquirir(W, ahora="2026-08-25T12:00:00Z", raiz=raiz, lease_seconds=600)
        p = ruta_del_lock(W, raiz=raiz)
        estado = json.loads(p.read_text(encoding="utf-8"))
        estado["propietario"]["pid"] = 999999          # un PID que no existe
        p.write_text(json.dumps(estado), encoding="utf-8")
        with pytest.raises(CaseBusy):
            adquirir(W, ahora="2026-08-25T12:05:00Z", raiz=raiz)

    def test_renovar_hacia_ATRAS_se_rechaza(self, raiz):
        """R10/H10-02: sin monotonía, un `ahora` retrasado acorta el lease propio."""
        from core.casos.case_mutex import adquirir, renovar
        nonce = adquirir(W, ahora="2026-08-25T12:00:30Z", raiz=raiz)
        with pytest.raises(ValueError):
            renovar(W, nonce=nonce, ahora="2026-08-25T12:00:00Z", raiz=raiz)

    def test_renovar_con_nonce_ajeno_lanza_MUTEX_NOT_MINE(self, raiz):
        from core.casos.case_mutex import adquirir, renovar
        from core.casos.workspace_model import MutexNotMine
        adquirir(W, ahora=AHORA, raiz=raiz)
        with pytest.raises(MutexNotMine):
            renovar(W, nonce="nonce-de-otro", ahora=AHORA, raiz=raiz)
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: FAIL — `ImportError: cannot import name 'adquirir'`

- [ ] **Step 3: Implementación mínima**

```python
# añadir a core/casos/case_mutex.py
import secrets

LEASE_POR_DEFECTO = 300
ESPERA_SECCION_CRITICA = 10


def _guard(w_code: str, raiz: Path | None):
    """Bloqueo NATIVO durante la sección crítica. Ver §0.2 sobre por qué no `O_EXCL`."""
    from filelock import FileLock
    p = ruta_del_lock(w_code, raiz=raiz)
    p.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(p) + ".guard", timeout=ESPERA_SECCION_CRITICA)


def _escribir_estado(w_code: str, estado: dict, *, raiz: Path | None) -> None:
    p = ruta_del_lock(w_code, raiz=raiz)
    tmp = p.with_name(f".{p.name}.tmp")
    tmp.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    os.replace(tmp, p)


def _caducado(estado: dict, ahora: str) -> bool:
    """¿Venció el lease? **Nunca se mira el PID** — el sistema los reutiliza (H3-02).

    El estado ya pasó por `_validar_estado`, así que sus campos son interpretables: no
    hace falta un `except` que, de existir, tendría que fallar CERRADO.
    """
    return _instante(ahora) > _instante(estado["renewed_at"]) + estado["lease_seconds"]


def adquirir(w_code: str, *, ahora: str, raiz: Path | None = None,
             lease_seconds: int = LEASE_POR_DEFECTO) -> str:
    """Toma el mutex y devuelve el nonce. Valida ANTES de tocar disco."""
    from .workspace_model import CaseBusy

    w_code = _w_code_valido(w_code)
    lease = _lease_valido(lease_seconds)
    _instante(ahora)                       # valida el reloj antes de crear nada
    yo = identidad_proceso()
    with _guard(w_code, raiz):
        estado = leer_estado(w_code, raiz=raiz)
        if estado is not None and not _caducado(estado, ahora):
            raise CaseBusy(w_code=w_code,
                           maquina=(estado["propietario"] or {}).get("host"),
                           fecha=estado["renewed_at"],
                           detalle="el lease del titular sigue vivo")
        nonce = secrets.token_hex(8)
        _escribir_estado(w_code, {
            "schema": 1, "propietario": yo.a_json(), "nonce": nonce,
            "acquired_at": ahora, "renewed_at": ahora, "lease_seconds": lease,
        }, raiz=raiz)
        return nonce


def renovar(w_code: str, *, nonce: str, ahora: str, raiz: Path | None = None) -> None:
    """Alarga el lease. Exige titularidad y **monotonía**."""
    from .workspace_model import MutexNotMine

    w_code = _w_code_valido(w_code)
    momento = _instante(ahora)
    with _guard(w_code, raiz):
        estado = leer_estado(w_code, raiz=raiz)
        if estado is None or estado["nonce"] != nonce:
            raise MutexNotMine(w_code=w_code,
                               detalle="el nonce no coincide con el del titular")
        if momento < _instante(estado["renewed_at"]):
            raise ValueError(
                "una renovación no puede retroceder en el tiempo: acortaría el lease "
                "propio y dejaría entrar a otro")
        estado["renewed_at"] = ahora
        _escribir_estado(w_code, estado, raiz=raiz)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/casos/case_mutex.py tests/test_case_mutex.py
git commit -m "mutex D2: adquirir, lease y renovacion monotona"
```

---

### Task 6: Liberar con prueba de titularidad

**Files:**
- Modify: `core/casos/case_mutex.py`
- Test: `tests/test_case_mutex.py`

**Interfaces:** produce `liberar(w_code, *, nonce, raiz=None) -> None`.

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_case_mutex.py
class TestLiberar:

    def test_con_nonce_ajeno_NO_suelta_el_mutex(self, raiz):
        """El defecto A-1 del frontal —cancelar un lock ajeno— aquí no se repite."""
        from core.casos.case_mutex import adquirir, leer_estado, liberar
        from core.casos.workspace_model import MutexNotMine
        nonce = adquirir(W, ahora=AHORA, raiz=raiz)
        with pytest.raises(MutexNotMine):
            liberar(W, nonce="nonce-de-otro", raiz=raiz)
        assert leer_estado(W, raiz=raiz)["nonce"] == nonce

    def test_dos_veces_no_es_un_error(self, raiz):
        from core.casos.case_mutex import adquirir, liberar
        nonce = adquirir(W, ahora=AHORA, raiz=raiz)
        liberar(W, nonce=nonce, raiz=raiz)
        liberar(W, nonce=nonce, raiz=raiz)

    def test_tras_liberar_otro_puede_entrar(self, raiz):
        from core.casos.case_mutex import adquirir, liberar
        nonce = adquirir(W, ahora=AHORA, raiz=raiz)
        liberar(W, nonce=nonce, raiz=raiz)
        assert adquirir(W, ahora=AHORA, raiz=raiz)
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: FAIL — `ImportError: cannot import name 'liberar'`

- [ ] **Step 3: Implementación mínima**

```python
# añadir a core/casos/case_mutex.py
def liberar(w_code: str, *, nonce: str, raiz: Path | None = None) -> None:
    """Suelta el mutex. Exige titularidad; idempotente si ya no está."""
    from .workspace_model import MutexNotMine

    w_code = _w_code_valido(w_code)
    with _guard(w_code, raiz):
        estado = leer_estado(w_code, raiz=raiz)
        if estado is None:
            return
        if estado["nonce"] != nonce:
            raise MutexNotMine(w_code=w_code,
                               detalle="el nonce no coincide con el del titular")
        ruta_del_lock(w_code, raiz=raiz).unlink(missing_ok=True)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/casos/case_mutex.py tests/test_case_mutex.py
git commit -m "mutex D2: liberar exige demostrar titularidad"
```

---

### Task 7: `tomado()` — con renovación OBLIGATORIA

> **R10/H10-04, decisión de Nikolai (2026-08-25).** La rev. 1 adquiría una vez y no renovaba: si el lease vencía a mitad del cuerpo, otro entraba y el primero seguía escribiendo sin enterarse. Y descartaba el renovador con una frase sin medición —«cinco minutos, más que cualquier sección crítica»— cuando la feature existe precisamente por corridas de OCR de duración incierta. **Un lease que nadie renueva no es un lease: es una apuesta sobre cuánto tardo.**

**Files:**
- Modify: `core/casos/case_mutex.py`
- Test: `tests/test_case_mutex.py`

**Interfaces:** produce `tomado(w_code, *, ahora_fn, raiz=None, lease_seconds=LEASE_POR_DEFECTO)`. `ahora_fn` es un **callable**, no una cadena: el renovador necesita el instante de cada latido.

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_case_mutex.py
def _esperar_a_que_renueve(raiz, *, intentos: int = 100) -> None:
    """Espera activa acotada. Un `sleep` fijo haría el test lento o inestable."""
    import time
    from core.casos.case_mutex import leer_estado
    for _ in range(intentos):
        estado = leer_estado(W, raiz=raiz)
        if estado and estado["renewed_at"] != estado["acquired_at"]:
            return
        time.sleep(0.02)
    raise AssertionError("el renovador no latió en 2 s")


class TestElGestorRenueva:

    def test_libera_aunque_el_cuerpo_reviente(self, raiz):
        from core.casos.case_mutex import adquirir, leer_estado, tomado
        with pytest.raises(RuntimeError):
            with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz):
                raise RuntimeError("boom")
        assert leer_estado(W, raiz=raiz) is None
        assert adquirir(W, ahora=AHORA, raiz=raiz)

    def test_RENUEVA_mientras_el_cuerpo_corre(self, raiz):
        """El hallazgo crítico: sin esto, el lease vence y otro entra.

        Reloj falso que avanza un minuto por lectura, y lease de 1 s para que el latido
        caiga en fracciones de segundo reales.
        """
        import itertools
        from core.casos.case_mutex import adquirir, leer_estado, tomado
        from core.casos.workspace_model import CaseBusy

        contador = itertools.count()

        def reloj():
            return f"2026-08-25T12:{next(contador) % 60:02d}:00Z"

        with tomado(W, ahora_fn=reloj, raiz=raiz, lease_seconds=1):
            _esperar_a_que_renueve(raiz)
            estado = leer_estado(W, raiz=raiz)
            assert estado["renewed_at"] != estado["acquired_at"], (
                "el lease no se renovó ni una vez durante el cuerpo")
            with pytest.raises(CaseBusy):
                adquirir(W, ahora=estado["renewed_at"], raiz=raiz)

    def test_el_renovador_para_al_salir(self, raiz):
        """Un hilo que sobreviva al `with` renovaría un lock que ya es de otro."""
        import threading
        from core.casos.case_mutex import tomado
        antes = threading.active_count()
        with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=1):
            pass
        assert threading.active_count() == antes
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly -k Gestor`
Expected: FAIL — `ImportError: cannot import name 'tomado'`

- [ ] **Step 3: Implementación mínima**

```python
# añadir a core/casos/case_mutex.py
import contextlib
import threading

#: Fracción del lease tras la que se renueva. Un tercio deja margen para dos latidos
#: perdidos antes de que el lease venza de verdad.
_FRACCION_LATIDO = 3


@contextlib.contextmanager
def tomado(w_code: str, *, ahora_fn, raiz: Path | None = None,
           lease_seconds: int = LEASE_POR_DEFECTO):
    """Adquiere, **renueva mientras el cuerpo corre**, y libera pase lo que pase.

    `ahora_fn` es un callable porque el renovador necesita el instante de cada latido;
    una cadena fija haría que la renovación escribiera siempre el mismo `renewed_at`, o
    sea que no renovara nada.

    El hilo es `daemon` y se para en el `finally`: un renovador que sobreviviera al
    bloque estaría alargando un lock que quizá ya es de otro.
    """
    lease = _lease_valido(lease_seconds)
    nonce = adquirir(w_code, ahora=ahora_fn(), raiz=raiz, lease_seconds=lease)
    parar = threading.Event()

    def _latir():
        while not parar.wait(lease / _FRACCION_LATIDO):
            try:
                renovar(w_code, nonce=nonce, ahora=ahora_fn(), raiz=raiz)
            except Exception:                    # noqa: BLE001
                return          # perdimos la titularidad; el cuerpo se entera al salir

    hilo = threading.Thread(target=_latir, name=f"mutex-{w_code}", daemon=True)
    hilo.start()
    try:
        yield nonce
    finally:
        parar.set()
        hilo.join(timeout=5)
        liberar(w_code, nonce=nonce, raiz=raiz)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: PASS

- [ ] **Step 5: El mutante obligatorio**

Quitar `hilo.start()`. → `test_RENUEVA_mientras_el_cuerpo_corre` **rojo**; los otros dos **verdes**. Eso prueba que ese test contrata la renovación y no otra cosa. Revertir con `git checkout`.

- [ ] **Step 6: Commit**

```bash
git add core/casos/case_mutex.py tests/test_case_mutex.py
git commit -m "mutex D2: el gestor renueva el lease mientras el cuerpo corre"
```

---

### Task 8: La carrera DE VERDAD

> **R10/H10-01, el hallazgo crítico.** La rev. 1 lanzaba al hijo **después** de que el padre terminara de adquirir: nunca había dos adquisiciones compitiendo, así que el test comprobaba «un estado ya escrito produce `CaseBusy`», no exclusión. El revisor lo corrió **con el guard eliminado** y salió verde. Aquí los dos contendientes se sueltan a la vez desde una **barrera común**, y el mutante es obligatorio.

**Files:**
- Create: `tests/test_case_mutex_concurrencia.py`

- [ ] **Step 1: Escribir el test**

```python
# tests/test_case_mutex_concurrencia.py
"""Dos procesos que compiten DE VERDAD por la misma adquisición.

La versión anterior dejaba que el padre terminara de adquirir antes de lanzar al hijo,
así que no había carrera: comprobaba que un lock ya escrito produce `CaseBusy`. Corrida
con la exclusión eliminada, pasaba en verde. Aquí los dos hijos se sueltan desde una
barrera común y compiten por la misma sección crítica.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
import time
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[1]
AHORA = "2026-08-25T12:00:00Z"
W = "W-CONC01"

HIJO = textwrap.dedent('''
    import sys, time
    sys.path.insert(0, {repo!r})
    from pathlib import Path
    from core.casos.case_mutex import adquirir
    from core.casos.workspace_model import CaseBusy

    Path({listo!r}).write_text("x", encoding="utf-8")     # «estoy cargado»
    salida = Path({salida!r})
    while not salida.exists():                             # barrera común
        time.sleep(0.005)
    try:
        adquirir({w!r}, ahora={ahora!r}, raiz={raiz!r}, lease_seconds=600)
        print("GANADOR")
    except CaseBusy:
        print("PERDEDOR")
''')


def _lanzar(tmp_path, raiz, n: int):
    guion = HIJO.format(repo=str(RAIZ_REPO), w=W, ahora=AHORA, raiz=str(raiz),
                        listo=str(tmp_path / f"listo_{n}"),
                        salida=str(tmp_path / "salida"))
    return subprocess.Popen([sys.executable, "-c", guion], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, encoding="utf-8", errors="replace")


def _esperar_en_la_barrera(tmp_path, cuantos: int) -> None:
    for _ in range(1000):
        if all((tmp_path / f"listo_{n}").exists() for n in range(1, cuantos + 1)):
            return
        time.sleep(0.01)
    raise AssertionError("los hijos no llegaron a la barrera")


def test_de_dos_procesos_que_COMPITEN_gana_exactamente_uno(tmp_path):
    raiz = tmp_path / "locks"
    hijos = [_lanzar(tmp_path, raiz, n) for n in (1, 2)]
    _esperar_en_la_barrera(tmp_path, 2)
    (tmp_path / "salida").write_text("ya", encoding="utf-8")

    salidas = []
    for h in hijos:
        out, err = h.communicate(timeout=60)
        assert h.returncode == 0, f"un hijo reventó:\\n{err[-800:]}"
        salidas.append(out.strip())

    assert sorted(salidas) == ["GANADOR", "PERDEDOR"], (
        f"dos procesos compitieron y el resultado fue {salidas}: dos GANADOR significa "
        f"que la exclusión no existe")


def test_un_proceso_solo_SI_entra(tmp_path):
    """Control negativo: sin él, «no dejar entrar nunca» pasaría el test de arriba."""
    raiz = tmp_path / "locks"
    hijo = _lanzar(tmp_path, raiz, 1)
    _esperar_en_la_barrera(tmp_path, 1)
    (tmp_path / "salida").write_text("ya", encoding="utf-8")
    out, err = hijo.communicate(timeout=60)
    assert hijo.returncode == 0, err[-800:]
    assert out.strip() == "GANADOR"
```

- [ ] **Step 2: Correr y verificar que pasa con el código real**

Run: `python -m pytest tests/test_case_mutex_concurrencia.py -q -p no:randomly`
Expected: PASS (2 tests)

- [ ] **Step 3: EL MUTANTE QUE LA REV. 1 NO TENÍA**

Sustituir `_guard` por:

```python
def _guard(w_code, raiz):
    import contextlib
    p = ruta_del_lock(w_code, raiz=raiz)
    p.parent.mkdir(parents=True, exist_ok=True)
    return contextlib.nullcontext()
```

Run: `python -m pytest tests/test_case_mutex_concurrencia.py -q -p no:randomly`
Expected: **`test_de_dos_procesos_que_COMPITEN_gana_exactamente_uno` ROJO** con `['GANADOR', 'GANADOR']`, y el control negativo **verde**.

**Si el mutante sobrevive, este test no prueba la exclusión y hay que arreglarlo antes de seguir** — que es exactamente lo que le pasó a la rev. 1. Puede hacer falta repetir la carrera (bucle de 20 iteraciones dentro del test) para que la ventana se abra: una carrera que solo falla a veces es una carrera igualmente.

Revertir con `git checkout -- core/casos/case_mutex.py`.

- [ ] **Step 4: Suite completa, dos semillas**

```bash
python -m pytest -q -p randomly --randomly-seed=777 --basetemp="$env:TEMP\fd_bt"
python -m pytest -q -p randomly --randomly-seed=31337 --basetemp="$env:TEMP\fd_bt2"
```
Expected: 0 fallos en las dos. Toda variación del conteo que no sean los tests nuevos se explica antes de seguir.

- [ ] **Step 5: Commit**

```bash
git add tests/test_case_mutex_concurrencia.py
git commit -m "mutex D2: la carrera de verdad, con barrera y mutante que la mata"
```

---

## Criterio de salida del Plan 2

1. `adquirir`/`renovar`/`liberar`/`tomado` existen, con namespace **W-code validado** en una raíz comprobada aquí, no heredada.
2. El abandono se decide **solo** por caducidad del lease; hay test con un PID inexistente.
3. Renovar y liberar exigen **titularidad**; renovar es además **monótona**.
4. `tomado()` **renueva mientras el cuerpo corre**, y su mutante muere.
5. Un estado ilegible o inválido **no abre el caso**: ocho formas, dos mutantes.
6. Hay una carrera con **dos procesos soltados a la vez**, y el mutante que quita la exclusión **la mata**.
7. `filelock` declarado con versión fijada; `psutil` no entra.
8. **Nadie llama todavía a la primitiva.** Cablearla es el Plan 3.

## Lo que este plan deliberadamente NO hace

- **No reclama el criterio 41** (H10-09), que exige además staging disjunto, unión conservada en cuatro artefactos y titularidad cruzada. Eso es el Plan 3.
- **No toca las 27 clases del write-set** (§25).
- **No coordina entre máquinas.** Entre máquinas sigue el lock de checkout, con sus seis defectos vivos en `xfail`.
- **No sustituye al `estado_repositorio`.** Aquel dice si el caso está prestado a otra máquina; este, si otro proceso **de esta** lo está tocando ahora.
- **No implementa fencing tokens.** Era la tercera opción de la decisión de H10-04 y se descartó porque obliga a que **todos** los escritores del write-set presenten el token, o sea que arrastra el Plan 3 dentro del Plan 2.
