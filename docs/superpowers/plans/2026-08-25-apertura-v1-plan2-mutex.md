---
estado: ejecutable
dueño: Nikolai Tyukhay
fecha: 2026-08-25
---

# Apertura V1 — Plan 2: la primitiva de mutex interproceso

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el mutex interproceso por caso que la decisión **D2** del §24 especifica, para que dos procesos de esta máquina no puedan operar a la vez sobre el mismo expediente.

**Architecture:** Dos capas sobre el **registro local** de la Fase 1. Una capa de exclusión (`filelock` con creación atómica) que solo se sostiene durante una sección crítica muy corta, y sobre ella un **fichero de estado** `<w_code>.lock` con propietario, nonce y *lease*. La primera da la atomicidad; el segundo sobrevive a un proceso muerto y permite decidir el abandono por **caducidad del lease**, nunca por antigüedad de PID.

**Tech Stack:** Python 3.14, `filelock`, `psutil` (solo para el instante de arranque del sistema), `pytest`.

## Por qué no se reutiliza el lock de checkout

Está medido y no hay que volver a medirlo: **Drive no es un mutex**. `test_defecto_doble_titular` demuestra que un write-then-verify sobre un fichero remoto compartido no da exclusión —A relee su propio nonce porque su push pisó el de B— y `test_defecto_rollback_cancela_un_lock_ajeno`, que se libera sin comprobar titularidad. Los dos siguen vivos en `xfail`. **Ámbito de este mutex: una máquina.** La coordinación entre máquinas sigue siendo el lock de checkout, con sus seis defectos declarados.

## Dónde vive, y por qué ese sitio ya estaba reservado

En la raíz del registro privado (`workspace_registry.raiz_por_defecto()`). No es una elección nueva: el Task 5 de la Fase 1 ya lo previó y **dejó sitio a propósito** — `WorkspaceRegistry.cargar()` recorre `*.json` con este comentario en el fuente:

> `*.json` a propósito: los lockfiles de D2 (`<w_code>.lock`) viven en esta misma raíz y no son entradas ni candidatos a cuarentena.

El namespace es el **W-code**, no la ruta del caso, porque el mutex tiene que existir **antes de que la carpeta exista** (la apertura de un caso nuevo lo toma antes de crear nada).

## Global Constraints

- **Windows + PowerShell.** Rutas con `pathlib`; nada de `fcntl`.
- **Encoding UTF-8 sin BOM** en todo fichero escrito.
- **`main` protegida:** rama + PR. Tests acompañan todo cambio en `core/`.
- **La suite corre con `pytest-randomly`:** dos semillas antes de declarar verde.
- **El registro no puede vivir bajo `CASOS_ROOT` ni bajo el repo** — lo comprueba `WorkspaceRegistry.__init__` y el mutex hereda esa raíz, así que hereda la garantía.
- **Reloj inyectado.** Ninguna función de este módulo llama a `datetime.now()` por dentro: el `ahora` es parámetro, como en todo `core/casos/`.
- **Fuera de alcance:** el write-set de las 27 clases del §25 (eso es el **Plan 3**). Aquí se construye la primitiva y **nadie la llama todavía**.

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `core/casos/case_mutex.py` (nuevo) | La primitiva entera: identidad de proceso, estado en disco, `adquirir`/`renovar`/`liberar` |
| `core/casos/workspace_model.py` (modificar) | Dos errores nuevos del §10: `CaseBusy`, `MutexNotMine` |
| `requirements.txt` (modificar) | Declarar `filelock` y `psutil`, hoy usados sin declarar |
| `tests/test_case_mutex.py` (nuevo) | Contrato de la primitiva |
| `tests/test_case_mutex_concurrencia.py` (nuevo) | Dos procesos **de verdad**, solapados |

---

### Task 1: Declarar las dependencias que ya se usan sin declarar

**Files:**
- Modify: `requirements.txt`
- Test: `tests/test_case_mutex.py`

**Interfaces:**
- Produces: nada de código. Cierra un hueco de reproducibilidad: `filelock` (3.29.0) y `psutil` (7.2.2) están instalados en el venv de esta máquina y **no aparecen en `requirements.txt`**, así que un clon limpio no los tendría y el módulo del Task 2 no importaría.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_case_mutex.py
"""Contrato de la primitiva de mutex por caso (decisión D2 del §24)."""
from __future__ import annotations

import io
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_las_dependencias_del_mutex_estan_declaradas():
    """Una dependencia de producción que solo existe en mi venv no existe.

    `filelock` y `psutil` estaban instalados y sin declarar cuando se escribió este
    plan: en un clon limpio el módulo del mutex no importaría, y el fallo aparecería
    en la máquina de otro, no en la mía.
    """
    texto = io.open(RAIZ / "requirements.txt", encoding="utf-8").read()
    for paquete in ("filelock", "psutil"):
        assert paquete in texto, (
            f"{paquete} se usa en core/casos/case_mutex.py y no está en "
            f"requirements.txt")
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: FAIL — `AssertionError: filelock se usa en core/casos/case_mutex.py y no está en requirements.txt`

- [ ] **Step 3: Declararlas**

Añadir a `requirements.txt`, antes del bloque `# Tests`:

```
filelock>=3.12           # mutex interproceso por caso (core/casos/case_mutex.py, D2 del
                         # §24 de la spec de apertura). Creación atómica O_CREAT|O_EXCL:
                         # la exclusión no se hace a mano.
psutil>=5.9              # SOLO para psutil.boot_time(): el `boot_id` que distingue un PID
                         # reutilizado tras un reinicio de un PID vivo (H3-02).
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/test_case_mutex.py
git commit -m "deps: declarar filelock y psutil, que ya se usaban sin declarar"
```

---

### Task 2: Identidad del proceso — y por qué el PID no basta

**Files:**
- Create: `core/casos/case_mutex.py`
- Test: `tests/test_case_mutex.py`

**Interfaces:**
- Produces: `identidad_proceso() -> ProcesoID`, un `dataclass(frozen=True)` con `host: str`, `pid: int`, `boot_id: str`. `ProcesoID.es_el_mismo(otro: dict) -> bool` compara los tres.

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_case_mutex.py
def test_la_identidad_lleva_boot_id_ademas_de_pid():
    """El PID solo no identifica: el sistema los reutiliza.

    H3-02 nombra exactamente esa trampa. Tras un reinicio, otro proceso puede tener el
    mismo PID que el dueño muerto del lock, y un mutex que decidiera «es mío» por PID
    dejaría entrar a un impostor. El `boot_id` —aquí, el instante de arranque del
    sistema— hace que dos vidas distintas de la máquina no se confundan.
    """
    from core.casos.case_mutex import identidad_proceso
    yo = identidad_proceso()
    assert yo.pid > 0
    assert yo.host
    assert yo.boot_id, "sin boot_id, un PID reutilizado se haría pasar por el dueño"


def test_la_identidad_no_se_reconoce_a_si_misma_con_otro_boot_id():
    from core.casos.case_mutex import identidad_proceso
    yo = identidad_proceso()
    mismo = {"host": yo.host, "pid": yo.pid, "boot_id": yo.boot_id}
    otro_arranque = {"host": yo.host, "pid": yo.pid, "boot_id": "otro-arranque"}
    assert yo.es_el_mismo(mismo) is True
    assert yo.es_el_mismo(otro_arranque) is False, (
        "mismo host y mismo PID en OTRO arranque no es el mismo proceso")
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.casos.case_mutex'`

- [ ] **Step 3: Implementación mínima**

```python
# core/casos/case_mutex.py
"""Mutex interproceso por caso — la decisión D2 del §24 de la spec de apertura.

Contesta una sola pregunta: **¿puede este proceso operar ahora sobre este expediente?**
Su ámbito es **una máquina**, declarado: la coordinación entre máquinas sigue siendo el
lock de checkout del Drive.
"""
from __future__ import annotations

import dataclasses
import os
import socket


@dataclasses.dataclass(frozen=True)
class ProcesoID:
    """Quién soy, de forma que un PID reutilizado no pueda hacerse pasar por mí."""

    host: str
    pid: int
    boot_id: str

    def a_json(self) -> dict:
        return {"host": self.host, "pid": self.pid, "boot_id": self.boot_id}

    def es_el_mismo(self, otro: dict | None) -> bool:
        if not isinstance(otro, dict):
            return False
        return (otro.get("host") == self.host
                and otro.get("pid") == self.pid
                and otro.get("boot_id") == self.boot_id)


def identidad_proceso() -> ProcesoID:
    """`(host, pid, boot_id)`. El `boot_id` es el instante de arranque del sistema.

    **Por qué el PID no basta**, que es lo que H3-02 imputa a cualquier mutex que lo
    use solo: el sistema reutiliza PIDs. Tras un reinicio, otro proceso puede tener el
    del dueño muerto, y decidir la titularidad por PID dejaría entrar a un impostor.
    """
    import psutil

    return ProcesoID(host=socket.gethostname(), pid=os.getpid(),
                     boot_id=str(int(psutil.boot_time())))
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add core/casos/case_mutex.py tests/test_case_mutex.py
git commit -m "mutex D2: identidad de proceso con boot_id, que es lo que el PID no da"
```

---

### Task 3: Los dos errores del §10

**Files:**
- Modify: `core/casos/workspace_model.py`
- Test: `tests/test_workspace_model.py`

**Interfaces:**
- Produces: `CaseBusy` (código `CASE_BUSY`) y `MutexNotMine` (código `MUTEX_NOT_MINE`), subclases de `WorkspaceError`, ambas en `errores_conocidos()`.

> **Nota normativa:** el §10 dice «**Como mínimo** estos códigos», así que añadir dos no reabre la tabla. Es el mismo precedente que el Task 5 de la Fase 1, que la llevó de 12 a 15.

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_workspace_model.py
def test_los_errores_del_mutex_estan_en_la_tabla():
    """Un error fuera de `errores_conocidos()` queda fuera de los canarios del §16.

    Es el hueco que R7/H7-12 castigó: los tres errores del registro se declararon en
    `workspace_model` justamente para no quedarse fuera de esa lista.
    """
    from core.casos.workspace_model import (CaseBusy, MutexNotMine,
                                            errores_conocidos)
    codigos = {c.codigo for c in errores_conocidos()}
    assert "CASE_BUSY" in codigos
    assert "MUTEX_NOT_MINE" in codigos
    assert CaseBusy in errores_conocidos()
    assert MutexNotMine in errores_conocidos()


def test_el_mensaje_de_case_busy_no_lleva_rutas():
    """§16: ni rutas locales ni PII. El mensaje identifica por W-code."""
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
    """Otro proceso de ESTA máquina tiene el mutex del caso, y su lease sigue vivo."""

    codigo = "CASE_BUSY"
    descripcion = "otro proceso de esta maquina esta operando sobre el caso"


class MutexNotMine(WorkspaceError):
    """Se intentó liberar o renovar un mutex cuyo nonce es de otro.

    Separado de `CaseBusy` a propósito: `CASE_BUSY` es «espera»; esto es «te
    equivocas de dueño», y confundirlos es el defecto A-1 del frontal —el rollback
    que cancela un lock ajeno— trasladado a esta capa.
    """

    codigo = "MUTEX_NOT_MINE"
    descripcion = "el mutex del caso pertenece a otro titular"
```

Y añadirlos a la tupla que devuelve `errores_conocidos()`.

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_workspace_model.py -q -p no:randomly`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/casos/workspace_model.py tests/test_workspace_model.py
git commit -m "mutex D2: CASE_BUSY y MUTEX_NOT_MINE en la tabla del 10"
```

---

### Task 4: Adquirir — exclusión y contenido

**Files:**
- Modify: `core/casos/case_mutex.py`
- Test: `tests/test_case_mutex.py`

**Interfaces:**
- Consumes: `identidad_proceso()` (Task 2), `CaseBusy` (Task 3), `workspace_registry.raiz_por_defecto()`.
- Produces:
  - `ruta_del_lock(w_code: str, *, raiz: Path | None = None) -> Path` → `<raiz>/<W-CODE>.lock`.
  - `adquirir(w_code: str, *, ahora: str, raiz: Path | None = None, lease_seconds: int = 300) -> str` → devuelve el **nonce** del titular. Lanza `CaseBusy` si otro lo tiene con lease vivo.
  - `leer_estado(w_code, *, raiz=None) -> dict | None`.

> **La forma, en dos capas, y por qué.** `filelock` sobre `<W-CODE>.lock.guard` da la **exclusión atómica** durante una sección crítica de milisegundos: leer el estado, decidir, escribirlo. El estado vive aparte, en `<W-CODE>.lock`, porque tiene que **sobrevivir al proceso**: si el dueño muere, el `filelock` se suelta solo y no quedaría rastro de quién lo tenía ni de si su lease caducó. Una sola capa no puede hacer las dos cosas.

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_case_mutex.py
import pytest

AHORA = "2026-08-25T12:00:00Z"
W = "W-MUTEX1"


@pytest.fixture
def raiz(tmp_path):
    return tmp_path / "locks"


def test_adquirir_escribe_el_estado_con_todo_lo_que_D2_exige(raiz):
    from core.casos.case_mutex import adquirir, identidad_proceso, leer_estado
    nonce = adquirir(W, ahora=AHORA, raiz=raiz)
    estado = leer_estado(W, raiz=raiz)
    yo = identidad_proceso()
    assert estado["nonce"] == nonce and nonce
    assert estado["acquired_at"] == AHORA
    assert estado["renewed_at"] == AHORA
    assert estado["lease_seconds"] == 300
    assert yo.es_el_mismo(estado["propietario"])


def test_un_segundo_adquirir_con_lease_vivo_lanza_CASE_BUSY(raiz):
    from core.casos.case_mutex import adquirir
    from core.casos.workspace_model import CaseBusy
    adquirir(W, ahora=AHORA, raiz=raiz)
    with pytest.raises(CaseBusy):
        adquirir(W, ahora="2026-08-25T12:00:30Z", raiz=raiz)


def test_el_namespace_es_el_W_CODE_y_no_la_ruta_del_caso(raiz):
    """El mutex tiene que existir ANTES de que exista la carpeta del caso."""
    from core.casos.case_mutex import adquirir, ruta_del_lock
    adquirir(W, ahora=AHORA, raiz=raiz)
    assert ruta_del_lock(W, raiz=raiz).name == f"{W}.lock"
    assert ruta_del_lock(W, raiz=raiz).is_file()


def test_dos_W_codes_distintos_no_se_excluyen(raiz):
    from core.casos.case_mutex import adquirir
    adquirir("W-AAA111", ahora=AHORA, raiz=raiz)
    adquirir("W-BBB222", ahora=AHORA, raiz=raiz)      # no lanza


def test_el_registro_NO_confunde_el_lock_con_una_entrada(raiz):
    """El Task 5 de la Fase 1 dejó sitio a propósito: `cargar()` glob-ea `*.json`."""
    from core.casos.case_mutex import adquirir
    from core.casos.workspace_registry import WorkspaceRegistry
    adquirir(W, ahora=AHORA, raiz=raiz)
    assert WorkspaceRegistry(raiz, ahora=AHORA).cargar() == []
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: FAIL — `ImportError: cannot import name 'adquirir'`

- [ ] **Step 3: Implementación mínima**

```python
# añadir a core/casos/case_mutex.py
import json
from pathlib import Path

from .workspace_model import CaseBusy

#: Cuánto vale una adquisición sin renovar. Cinco minutos: más que cualquier sección
#: crítica de V1 y menos que la paciencia de un operador ante un caso que se quedó
#: tomado por un proceso muerto.
LEASE_POR_DEFECTO = 300

#: Espera máxima por la sección crítica. NO es la espera por el caso: es la espera por
#: el fichero de estado, que se tiene milisegundos.
ESPERA_SECCION_CRITICA = 10


def _raiz(raiz: Path | None) -> Path:
    if raiz is not None:
        return Path(raiz)
    from .workspace_registry import raiz_por_defecto
    return raiz_por_defecto()


def ruta_del_lock(w_code: str, *, raiz: Path | None = None) -> Path:
    return _raiz(raiz) / f"{(w_code or '').strip().upper()}.lock"


def _guard(w_code: str, raiz: Path | None):
    from filelock import FileLock
    p = ruta_del_lock(w_code, raiz=raiz)
    p.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(p) + ".guard", timeout=ESPERA_SECCION_CRITICA)


def leer_estado(w_code: str, *, raiz: Path | None = None) -> dict | None:
    p = ruta_del_lock(w_code, raiz=raiz)
    if not p.is_file():
        return None
    try:
        crudo = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    return crudo if isinstance(crudo, dict) else None


def _escribir_estado(w_code: str, estado: dict, *, raiz: Path | None) -> None:
    p = ruta_del_lock(w_code, raiz=raiz)
    tmp = p.with_name(f".{p.name}.tmp")
    tmp.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    os.replace(tmp, p)


def adquirir(w_code: str, *, ahora: str, raiz: Path | None = None,
             lease_seconds: int = LEASE_POR_DEFECTO) -> str:
    """Toma el mutex del caso y devuelve el nonce del titular."""
    import secrets

    yo = identidad_proceso()
    with _guard(w_code, raiz):
        estado = leer_estado(w_code, raiz=raiz)
        if estado is not None and not _caducado(estado, ahora):
            raise CaseBusy(w_code=w_code,
                           maquina=(estado.get("propietario") or {}).get("host"),
                           fecha=estado.get("renewed_at"),
                           detalle="el lease del titular sigue vivo")
        nonce = secrets.token_hex(8)
        _escribir_estado(w_code, {
            "schema": 1, "propietario": yo.a_json(), "nonce": nonce,
            "acquired_at": ahora, "renewed_at": ahora,
            "lease_seconds": int(lease_seconds),
        }, raiz=raiz)
        return nonce
```

`_caducado` se implementa en el Task 5; para que este Task pase, defínelo provisionalmente como `def _caducado(estado, ahora): return False` y sustitúyelo allí.

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add core/casos/case_mutex.py tests/test_case_mutex.py
git commit -m "mutex D2: adquirir con namespace por W-code y estado en el registro"
```

---

### Task 5: El lease — abandono por caducidad, nunca por PID

**Files:**
- Modify: `core/casos/case_mutex.py`
- Test: `tests/test_case_mutex.py`

**Interfaces:**
- Produces: `_caducado(estado: dict, ahora: str) -> bool` y `renovar(w_code, *, nonce, ahora, raiz=None) -> None` (lanza `MutexNotMine` si el nonce no es el del titular).

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_case_mutex.py
def test_un_lease_caducado_se_puede_tomar(raiz):
    from core.casos.case_mutex import adquirir
    adquirir(W, ahora="2026-08-25T12:00:00Z", raiz=raiz, lease_seconds=60)
    nuevo = adquirir(W, ahora="2026-08-25T12:01:01Z", raiz=raiz)   # 61 s después
    assert nuevo, "un lease caducado deja el caso libre"


def test_renovar_ALARGA_el_lease_y_lo_defiende(raiz):
    from core.casos.case_mutex import adquirir, renovar
    from core.casos.workspace_model import CaseBusy
    nonce = adquirir(W, ahora="2026-08-25T12:00:00Z", raiz=raiz, lease_seconds=60)
    renovar(W, nonce=nonce, ahora="2026-08-25T12:00:50Z", raiz=raiz)
    with pytest.raises(CaseBusy):
        adquirir(W, ahora="2026-08-25T12:01:01Z", raiz=raiz)


def test_el_abandono_NO_se_decide_por_el_PID(raiz):
    """El corazón de H3-02, y la razón de que el lease exista.

    El estado dice que el dueño es un PID que **no existe** en esta máquina. Un mutex
    que mirara «¿vive ese PID?» lo daría por abandonado. Este mira el lease: sigue
    vivo, así que sigue tomado. Lo contrario es la trampa del PID reutilizado.
    """
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


def test_renovar_con_un_nonce_ajeno_lanza_MUTEX_NOT_MINE(raiz):
    from core.casos.case_mutex import adquirir, renovar
    from core.casos.workspace_model import MutexNotMine
    adquirir(W, ahora=AHORA, raiz=raiz)
    with pytest.raises(MutexNotMine):
        renovar(W, nonce="nonce-de-otro", ahora=AHORA, raiz=raiz)
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: FAIL — `test_un_lease_caducado_se_puede_tomar` lanza `CaseBusy` (porque `_caducado` devuelve `False` fijo) e `ImportError` para `renovar`.

- [ ] **Step 3: Implementación mínima**

```python
# en core/casos/case_mutex.py — sustituye el _caducado provisional
def _a_epoch(ts: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()


def _caducado(estado: dict, ahora: str) -> bool:
    """¿Venció el lease? **Nunca se mira el PID.**

    Comprobar si el PID vive parece más listo y es la trampa que H3-02 nombra: el
    sistema reutiliza PIDs, así que un PID vivo puede ser de otro programa y un PID
    muerto puede pertenecer a un dueño legítimo que solo está tardando. El lease no
    tiene ese problema porque lo renueva quien de verdad sigue trabajando.
    """
    try:
        vencimiento = _a_epoch(estado["renewed_at"]) + float(estado["lease_seconds"])
        return _a_epoch(ahora) > vencimiento
    except (KeyError, TypeError, ValueError):
        # Estado ilegible: se trata como NO caducado. Falla cerrado — dar por libre un
        # lock que no se entiende es la manera de que dos procesos entren a la vez.
        return False


def renovar(w_code: str, *, nonce: str, ahora: str, raiz: Path | None = None) -> None:
    """Alarga el lease. Exige demostrar titularidad releyendo el nonce."""
    from .workspace_model import MutexNotMine

    with _guard(w_code, raiz):
        estado = leer_estado(w_code, raiz=raiz)
        if estado is None or estado.get("nonce") != nonce:
            raise MutexNotMine(w_code=w_code,
                               detalle="el nonce no coincide con el del titular")
        estado["renewed_at"] = ahora
        _escribir_estado(w_code, estado, raiz=raiz)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add core/casos/case_mutex.py tests/test_case_mutex.py
git commit -m "mutex D2: lease con renovacion; el abandono nunca se decide por PID"
```

---

### Task 6: Liberar con prueba de titularidad, y el gestor de contexto

**Files:**
- Modify: `core/casos/case_mutex.py`
- Test: `tests/test_case_mutex.py`

**Interfaces:**
- Produces:
  - `liberar(w_code, *, nonce, raiz=None) -> None` — lanza `MutexNotMine` si el nonce no es el del titular; **idempotente** si ya no hay estado.
  - `tomado(w_code, *, ahora, raiz=None, lease_seconds=LEASE_POR_DEFECTO)` — gestor de contexto que adquiere y libera, y libera **también si el cuerpo lanza**.

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_case_mutex.py
def test_liberar_con_nonce_ajeno_NO_suelta_el_mutex(raiz):
    """Es el defecto A-1 del frontal —el rollback que cancela un lock ajeno—
    trasladado a esta capa, y aquí no se repite."""
    from core.casos.case_mutex import adquirir, leer_estado, liberar
    from core.casos.workspace_model import MutexNotMine
    nonce = adquirir(W, ahora=AHORA, raiz=raiz)
    with pytest.raises(MutexNotMine):
        liberar(W, nonce="nonce-de-otro", raiz=raiz)
    assert leer_estado(W, raiz=raiz)["nonce"] == nonce, "el mutex se soltó de todas formas"


def test_liberar_dos_veces_no_es_un_error(raiz):
    from core.casos.case_mutex import adquirir, liberar
    nonce = adquirir(W, ahora=AHORA, raiz=raiz)
    liberar(W, nonce=nonce, raiz=raiz)
    liberar(W, nonce=nonce, raiz=raiz)          # idempotente: no lanza


def test_el_gestor_de_contexto_libera_aunque_el_cuerpo_reviente(raiz):
    from core.casos.case_mutex import adquirir, leer_estado, tomado
    with pytest.raises(RuntimeError):
        with tomado(W, ahora=AHORA, raiz=raiz):
            raise RuntimeError("boom")
    assert leer_estado(W, raiz=raiz) is None, (
        "una excepción dentro de la sección crítica dejó el caso tomado para siempre")
    adquirir(W, ahora=AHORA, raiz=raiz)         # y por tanto se puede volver a tomar
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: FAIL — `ImportError: cannot import name 'liberar'`

- [ ] **Step 3: Implementación mínima**

```python
# añadir a core/casos/case_mutex.py
import contextlib


def liberar(w_code: str, *, nonce: str, raiz: Path | None = None) -> None:
    """Suelta el mutex. Exige demostrar titularidad; idempotente si ya no está."""
    from .workspace_model import MutexNotMine

    with _guard(w_code, raiz):
        estado = leer_estado(w_code, raiz=raiz)
        if estado is None:
            return                                   # ya liberado: no es un error
        if estado.get("nonce") != nonce:
            raise MutexNotMine(w_code=w_code,
                               detalle="el nonce no coincide con el del titular")
        ruta_del_lock(w_code, raiz=raiz).unlink(missing_ok=True)


@contextlib.contextmanager
def tomado(w_code: str, *, ahora: str, raiz: Path | None = None,
           lease_seconds: int = LEASE_POR_DEFECTO):
    """Adquiere y libera. Libera **también si el cuerpo lanza**.

    Sin el `finally`, una excepción en la sección crítica dejaría el caso tomado hasta
    que venciera el lease — que es exactamente el fallo que hace a la gente borrar
    lockfiles a mano y perderle el respeto al mecanismo.
    """
    nonce = adquirir(w_code, ahora=ahora, raiz=raiz, lease_seconds=lease_seconds)
    try:
        yield nonce
    finally:
        liberar(w_code, nonce=nonce, raiz=raiz)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest tests/test_case_mutex.py -q -p no:randomly`
Expected: PASS (15 tests)

- [ ] **Step 5: Commit**

```bash
git add core/casos/case_mutex.py tests/test_case_mutex.py
git commit -m "mutex D2: liberar exige titularidad y el gestor libera ante excepcion"
```

---

### Task 7: Dos procesos solapados DE VERDAD

**Files:**
- Create: `tests/test_case_mutex_concurrencia.py`
- Test: se prueba a sí mismo

**Interfaces:**
- Consumes: todo lo anterior.

> **Por qué un `subprocess` y no dos hilos.** El mutex es **interproceso**. Dos hilos comparten el intérprete y `filelock` es reentrante dentro del mismo proceso: un test con hilos pasaría **aunque la exclusión no existiera**, que es la definición de un test que no prueba nada. La spec pide literalmente «prueba de dos procesos solapados» (criterio 41) y esto es lo que la cumple.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_case_mutex_concurrencia.py
"""Dos procesos DE VERDAD sobre el mismo W-code: exactamente uno entra.

Con hilos este test pasaría aunque no hubiera exclusión —`filelock` es reentrante
dentro del proceso—, así que se lanza un intérprete aparte. Es más lento y es el
único montaje que prueba lo que dice probar.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[1]
AHORA = "2026-08-25T12:00:00Z"
W = "W-CONC01"

GUION = textwrap.dedent('''
    import sys
    sys.path.insert(0, {repo!r})
    from core.casos.case_mutex import adquirir
    from core.casos.workspace_model import CaseBusy
    try:
        adquirir({w!r}, ahora={ahora!r}, raiz={raiz!r}, lease_seconds=600)
        print("GANADOR")
    except CaseBusy:
        print("PERDEDOR")
''')


def _correr_en_otro_proceso(raiz: Path) -> str:
    guion = GUION.format(repo=str(RAIZ_REPO), w=W, ahora=AHORA, raiz=str(raiz))
    res = subprocess.run([sys.executable, "-c", guion], capture_output=True,
                         encoding="utf-8", errors="replace", timeout=60)
    assert res.returncode == 0, f"el proceso hijo reventó:\\n{res.stderr[-800:]}"
    return res.stdout.strip()


def test_de_dos_procesos_solapados_entra_EXACTAMENTE_uno(tmp_path):
    from core.casos.case_mutex import adquirir
    raiz = tmp_path / "locks"

    # Este proceso toma el mutex y NO lo suelta.
    adquirir(W, ahora=AHORA, raiz=raiz, lease_seconds=600)

    # Otro proceso, de verdad, intenta lo mismo.
    assert _correr_en_otro_proceso(raiz) == "PERDEDOR", (
        "dos procesos entraron a la vez sobre el mismo expediente")


def test_si_el_primero_suelta_el_segundo_entra(tmp_path):
    from core.casos.case_mutex import adquirir, liberar
    raiz = tmp_path / "locks"
    nonce = adquirir(W, ahora=AHORA, raiz=raiz, lease_seconds=600)
    liberar(W, nonce=nonce, raiz=raiz)
    assert _correr_en_otro_proceso(raiz) == "GANADOR", (
        "el mutex no se soltó: sin este control, el test de arriba pasaría también "
        "con un mutex que no dejara entrar a nadie nunca")
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_case_mutex_concurrencia.py -q -p no:randomly`
Expected: FAIL antes de los Tasks 4-6; PASS una vez implementados. Si ya están, **mutar para comprobar que muerde**: en `adquirir`, sustituir `raise CaseBusy(...)` por `pass` y comprobar que `test_de_dos_procesos_solapados_entra_EXACTAMENTE_uno` se pone **rojo** y el otro **verde**. Restaurar con `git checkout -- core/casos/case_mutex.py`.

- [ ] **Step 3: (sin implementación nueva)**

Este Task no añade código de producción: prueba el que ya existe con el único montaje que lo prueba de verdad.

- [ ] **Step 4: Correr la suite completa, dos semillas**

```bash
python -m pytest -q -p randomly --randomly-seed=777 --basetemp="$env:TEMP\fd_bt"
python -m pytest -q -p randomly --randomly-seed=31337 --basetemp="$env:TEMP\fd_bt2"
```
Expected: 0 fallos en las dos. Cualquier variación del conteo que no sean los tests nuevos se explica antes de seguir.

- [ ] **Step 5: Commit**

```bash
git add tests/test_case_mutex_concurrencia.py
git commit -m "mutex D2: dos procesos solapados de verdad, no dos hilos"
```

---

## Criterio de salida del Plan 2

1. `adquirir`/`renovar`/`liberar`/`tomado` existen, con namespace por **W-code** en la raíz del registro de la Fase 1.
2. El abandono se decide **solo** por caducidad del lease; hay test que lo prueba con un PID inexistente.
3. Liberar y renovar exigen **demostrar titularidad**; un nonce ajeno no suelta el mutex.
4. Hay una prueba con **dos procesos reales** solapados, con su control negativo.
5. `filelock` y `psutil` están **declarados**.
6. **Nadie llama todavía a la primitiva.** Cablearla es el Plan 3, junto con el write-set del §25.

## Lo que este plan deliberadamente NO hace

- **No toca las 27 clases del write-set** (§25). Ese es el Plan 3, y mezclarlo aquí haría que la primitiva y su cableado entraran o salieran juntos.
- **No coordina entre máquinas.** Ámbito declarado: una. Entre máquinas sigue el lock de checkout, con sus **seis** defectos vivos en `xfail`.
- **No sustituye al `estado_repositorio`.** Son cosas distintas: aquel dice si el caso está prestado a otra máquina; este, si otro proceso **de esta** lo está tocando ahora.
- **No renueva el lease en segundo plano.** `renovar` existe y se llama explícitamente; un hilo renovador es complejidad que ninguna sección crítica de V1 necesita todavía.
