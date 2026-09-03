---
tipo: plan
objeto: "Apertura V1 — Plan 5: el cableado de la secuencia y el E2E"
estado_remediacion: pendiente
creado: 2026-09-03
---

# Apertura V1 — Plan 5: el cableado de la secuencia y el E2E (rev. 1)

> ## ⛔ ESTADO: rev. 1 `NO-EJECUTABLE`. NO se construye con este diseño.
>
> **R-A (diseño) devolvió `NO-EJECUTABLE`: 12 hallazgos, 12 confirmados, 0 refutados**, 4
> críticos y uno más elevado a crítico por el adjudicador. Acta:
> `docs/superpowers/specs/2026-09-03-apertura-v1-plan5-rA-adversarial-review.md`. Adjudicación
> completa en el §5.
>
> **Lo que sobrevive:** el diagnóstico del §1 —nadie encadena, `preparado_con_pendientes` no
> existe, el `element` del CRM tiene default judicial— lo reprodujo el revisor entero. La
> decisión de invertir el orden es de Nikolai y sigue en pie.
>
> **Lo que cae:** dos de las cuatro deudas del §0 no eran deudas aceptables sino **contradicciones
> literales de la spec**, y las tres etapas se saltaban costuras que ya existían. Pendiente:
> **rev. 2**, con los puntos enumerados en el §5.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** que `python -m scripts.abrir_caso --modo v1 …` ejecute la secuencia completa de V1
—identidad → esqueleto → pull de Drive E&V → pull del CRM → atomización del correo depositado →
sala de máquina— bajo un solo mutex, y termine declarando su estado; hoy `--modo v1` es solo una
puerta que valida y no encadena nada.

**Architecture:** un **secuenciador puro** en `core/apertura_v1.py` que conoce el orden, el punto
de parada, la máquina de estados y el informe, y recibe las etapas como invocables. Los
**adaptadores** viven en `scripts/abrir_caso.py`, porque atan valores que solo el CLI ha resuelto
(`folder_id`, `team_id`, `case_dir`, `ident`) y son los que imprimen. El secuenciador corre
**dentro** del bloque `mutex_sesion.sostenido(...)` que ya existe en `main`.

**Tech Stack:** Python 3, Typer, pytest (con `pytest-randomly`), `dataclasses`.

---

## Global Constraints

- **Windows + PowerShell.** Todo comando shell se lanza desde la raíz del worktree.
- **Encoding UTF-8 sin BOM** en todo fichero que se escriba.
- **En proceso, nunca por subproceso.** `mutex_sesion._SESIONES` es estado de módulo, o sea del
  proceso (`core/casos/mutex_sesion.py:57-60`): un hijo chocaría contra el lease de su propio
  padre y devolvería `CaseBusy`.
- **No se toca `core/casos/case_mutex.py`.** Cuatro rondas y 17 mutantes; editarlo es reabrirlas.
- **El reloj se pasa explícito** (`now_iso_utc`, no `now_iso`): `case_mutex` rechaza a propósito un
  instante sin offset, y el reloj mayoritario del repo es naïve.
- **`--modo libre` no cambia de comportamiento.** Hay 103 referencias a `scripts.abrir_caso` en el
  repo; cualquier regresión del modo por defecto es un fallo del plan.
- **Cada mutación de contrato lleva su mutante.** Si un contrato enumera N fronteras, hacen falta
  N mutantes, uno por frontera. Un solo mutante rojo prueba que el test no está vacío; no prueba
  el contrato.
- **Dos semillas antes de cerrar:** `-p randomly --randomly-seed=777` y `=31337`.

---

## §0. El diseño, y lo que se aplaza con nombre y consecuencia

Diseño aprobado por Nikolai el **2026-09-03**, tras la consulta que midió el estado real: la
decisión fue **cablear primero y aplazar 3B/3C**, contra el orden que la spec proponía
(3A-bis → 3B → 3C → 4 → 5).

**El razonamiento que la sostiene:** hay un mutex con cuatro rondas de revisión y diecisiete
mutantes que **no protege nada**, y una costura de escritura con **un** llamador de producción.
Añadir una tercera pieza sin encadenar antes de que un E2E mida qué duele es repetir el modo de
fallo que este repo ya tiene documentado.

**Las cuatro deudas que se declaran, aprobadas expresamente:**

| # | Deuda | Consecuencia exacta | Por qué se acepta |
|---|---|---|---|
| 1 | **3B aplazado** | Los derivados de la sala de máquina se siguen escribiendo fuera de la costura. `TECHO_CENSO` sigue en **83** (`tests/test_escritura_censo.py:75`) y el trinquete impide que suba | El censo es un tope que solo baja; la deuda queda contada, no oculta |
| 2 | **3C aplazado** | **La poda sigue borrando** con `p.unlink()` (`core/email_atomize/pipeline.py:220,267`; `core/adjuntos_contenido/pipeline.py:109`), contra lo que D4 ordenó (archivar) | Lo que borra son **derivados regenerables**; `00_Input` queda intacto. Medido y puesto delante de Nikolai al aprobar |
| 3 | **Bloque 3 de la spec aplazado** (espejo versionado de Drive, monotonía de observación H3-05, snapshot por ronda H3-06) | El pull se cablea con la semántica que tiene hoy | El marcador `.pulled` (`core/intake_drive.py:206`) impide re-descargar: no sobrescribe crudo |
| 4 | **3A-bis aplazado** | Si el guard desvía el pull a la bandeja, el sello de los ids de Drive no se estampa en la ficha canónica: queda aplazado **con aviso en pantalla** | Es D5, ya autorizada por Nikolai el 2026-08-26 |

**Presupuesto de revisión: DOS rondas.** La secuencia sostiene el mutex durante toda su duración,
y eso decide quién puede escribir sobre esa copia mientras corre: entra en la categoría de dos del
presupuesto de `CLAUDE.md`. **R-A sobre este plan, antes de escribir una línea de código; R-B sobre
el diff.** Techo duro: no hay tercera sin autorización expresa de Nikolai.

**Validación real: W-02Q38C**, el piloto ya abierto (decisión de Nikolai el 2026-09-03). Es el caso
que disparó el ítem y sigue declarado abierto porque su `_caso.md` no se sincroniza por el camino
común; correr la secuencia sobre él lo cierra **por el cableado y no por parche manual**.

**Lo que este plan NO construye, dicho para que nadie lo dé por hecho:** el alta CRM (V2),
`crm_ficha` (V2), el descubrimiento de correo en Gmail (V3), la sala de **lectura** (V3), la
viabilidad (V3). Y no construye el protocolo durable `operations`/`estado.json` del bloque 2 de la
spec: **la reanudación se apoya en la idempotencia que cada etapa ya tiene**, que es lo que el
criterio 14 llama punto fijo.

---

## §1. Lo que ya está construido, medido antes de planificar

| Pieza | Estado verificado |
|---|---|
| `--modo v1` y sus cinco puertas negativas | `scripts/abrir_caso.py:422-489` (`validar_modo`), llamada en `:532` **antes de todo efecto** |
| Mutex por caso, reentrante en proceso | `core/casos/mutex_sesion.py:120` (`sostenido`), ya sostenido en `main` (`scripts/abrir_caso.py:646`) y en `sala_maquina` (`scripts/sala_maquina.py:506`) |
| Pull de Drive E&V | `core.intake_drive.pull_drive_ev` → `DriveIntakeResult` con `skipped: bool` (`core/intake_drive.py:112-122`) |
| Pull del CRM | `core.sync_sudespacho.pull_expediente_v2(case_id, expediente_id, *, element=…)` → `PullResultV2` (`core/sync_sudespacho.py:1352`) |
| Atomización del correo | dentro de `apply`, en `_atomizar_correo` (`scripts/sala_maquina.py:578`); su status va al evento `atomizado_email` |
| Sala de máquina | `scripts/sala_maquina.py:779` (`apply`), con estado idempotente por sha |
| Registro del expediente CRM | `ExpedienteLink{id, element, input_dir}` en `CaseMeta.sudespacho_expedientes` (`core/case_manager.py:59-63,87`) |

**Y los tres huecos que este plan llena:**

1. **Nadie encadena.** `scripts/abrir_caso.py` no importa `sala_maquina` ni llama al pull del CRM;
   `_despachar_intake` (`:316`) atiende **una sola `--fuente` por invocación**.
2. **`preparado_con_pendientes` no existe en el código.** `git grep preparado_con_pendientes --
   core scripts tests` devuelve **cero**: vive solo en la prosa de la spec.
3. **El `element` del pull CRM tiene default judicial.** `core/sync_sudespacho.py:1356` declara
   `element: str = "expedientes_judiciales"`, y ése es exactamente el defecto que el criterio 38
   persigue en su dirección peligrosa: lo que puede colarse es una apertura **extrajudicial por la
   vía judicial**.

---

## §2. File Structure

| Fichero | Responsabilidad | Acción |
|---|---|---|
| `core/apertura_v1.py` | **Secuenciador puro.** Vocabulario de estados, pendientes, resultado de etapa, orden, punto de parada, máquina de estados. Cero I/O, cero Typer, cero red | **Crear** (~140 líneas) |
| `scripts/abrir_caso.py` | Adaptadores de las cinco etapas + el flag `--hasta` + el informe + el código de salida | **Modificar** (`:646-679`, y añadir ~120 líneas de adaptadores) |
| `scripts/sala_maquina.py` | `_atomizar_correo` y `apply` devuelven el status de la atomización | **Modificar** (`:578-640`, `:779-918`) |
| `core/intake_log.py` | Un tipo de evento nuevo en el set cerrado `INTAKE_EVENTS` | **Modificar** (`:41`) |
| `tests/test_apertura_v1_secuenciador.py` | El secuenciador con etapas falsas | **Crear** |
| `tests/test_apertura_v1_etapas.py` | Los cinco adaptadores | **Crear** |
| `tests/test_apertura_v1_cableado.py` | `main --modo v1` de punta a punta con dobles | **Crear** |
| `tests/test_apertura_v1_e2e.py` | E2E con fixtures sin PII (marcado `slow`) | **Crear** |
| `tests/_mutantes_plan5.py` | Arnés de mutación: un mutante por frontera contratada | **Crear** |

**Por qué el secuenciador va en `core/` y los adaptadores en `scripts/`:** la regla de tres capas
del proyecto dice que la lógica vive en el core y la UI solo orquesta. El **orden** y la **máquina
de estados** son lógica y se prueban sin disco ni red; **atar `folder_id` a una llamada concreta e
imprimir el resultado** es orquestación.

**La alternativa que NO se toma, y por qué:** extraer el cuerpo de `apply` (140 líneas de
orquestación en la capa de UI, dentro de un fichero de 1.000) a `core/`. Corregiría una violación
real de la regla, pero remueve el test de la etapa que la secuencia necesita estable: dos riesgos
en un diff. Queda anotado como pieza propia; el secuenciador no cambia si algún día se hace,
porque solo conoce la forma del adaptador.

---

## §3. Las catorce fronteras que este plan contrata

Una por mutante. Si el arnés de mutación no las mata todas, el plan no está cumplido.

| # | Frontera | Mutante que la mata |
|---|---|---|
| F1 | Un `fallo` de etapa **detiene** la secuencia: las posteriores no corren | quitar el `break` tras `fallo` |
| F2 | El estado final es `bloqueado` si hubo `fallo` | devolver `preparado_con_pendientes` con `fallo` presente |
| F3 | **V1 nunca es `completo`**: el pendiente permanente de fuentes V3 siempre está en la lista | quitar `PENDIENTE_FUENTES_V3` de la lista inicial |
| F4 | `--hasta <etapa>` para **después** de esa etapa, no antes | parar antes |
| F5 | `--hasta` con nombre desconocido es error, no «no parar nunca» | ignorar el nombre desconocido |
| F6 | El pull de Drive con `.pulled` presente reporta `saltada`, no `hecha` | mapear `skipped=True` a `hecha` |
| F7 | El `element` del pull CRM sale del `ExpedienteLink`, **nunca** del default | omitir el kwarg `element=` |
| F8 | Un `ExpedienteLink` **sin** `element` es `fallo`, no una adivinanza | rellenar con `"expedientes_judiciales"` |
| F9 | Un caso **sin** `ExpedienteLink` es `saltada` con pendiente, no `fallo` | mapearlo a `fallo` |
| F10 | Atomización `parcial` → etapa `hecha` **con pendiente** | mapearla a `hecha` sin pendiente |
| F11 | Atomización `fallo` → etapa `fallo` | mapearla a `hecha` |
| F12 | Atomización no ejecutada (`None`, sin correo) **no** deja pendiente | mapear `None` a pendiente |
| F13 | El evento final se emite con el estado real, y su nombre está en `INTAKE_EVENTS` | emitir un nombre fuera del set |
| F14 | Estado `bloqueado` → código de salida distinto de 0 | salir 0 siempre |

---

## Task 1: El vocabulario de estados y la regla que impide mentir

**Files:**
- Create: `core/apertura_v1.py`
- Test: `tests/test_apertura_v1_secuenciador.py`

**Interfaces:**
- Consumes: nada.
- Produces: `EstadoV1` (`PREPARADO_CON_PENDIENTES`, `BLOQUEADO`, `COMPLETO`), `Pendiente`,
  `PENDIENTE_FUENTES_V3`, `estado_de(pendientes: Sequence[Pendiente], *, hubo_fallo: bool) -> str`.

**Contexto que el implementador necesita:** el §21.3 de la spec ordena que V1 **nunca** termine
`completo`, porque Gmail y LeadHub son fuentes de V3 que V1 no consulta; el criterio 13 lo refuerza.
La tentación es escribir `return PREPARADO_CON_PENDIENTES` a pelo, y eso es una constante que
miente: no se puede auditar. Aquí el estado se **deriva** de la lista de pendientes, y V1 arranca
con un pendiente permanente en ella. Así la propiedad «V1 nunca es completo» es una consecuencia de
los datos y no una promesa del autor.

- [ ] **Step 1: Write the failing test**

```python
"""El secuenciador de V1: estados, orden y punto de parada.

Spec: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md
§21.3 (V1 nunca es `completo`), §21.4 criterio 13, §24 D4 (las tres salidas).
Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md
"""
import pytest

from core import apertura_v1 as av1


def test_vocabulario_de_estados_cerrado():
    assert av1.EstadoV1.COMPLETO == "completo"
    assert av1.EstadoV1.PREPARADO_CON_PENDIENTES == "preparado_con_pendientes"
    assert av1.EstadoV1.BLOQUEADO == "bloqueado"


def test_un_fallo_bloquea_aunque_no_haya_pendientes():
    assert av1.estado_de([], hubo_fallo=True) == av1.EstadoV1.BLOQUEADO


def test_sin_pendientes_y_sin_fallo_seria_completo():
    """La regla pura admite `completo`. Lo que lo impide en V1 es el pendiente
    permanente del test siguiente, no un `return` cableado aquí."""
    assert av1.estado_de([], hubo_fallo=False) == av1.EstadoV1.COMPLETO


def test_con_pendientes_es_preparado_con_pendientes():
    p = av1.Pendiente(codigo="x", detalle="lo que sea")
    assert av1.estado_de([p], hubo_fallo=False) == av1.EstadoV1.PREPARADO_CON_PENDIENTES


def test_f3_el_pendiente_de_fuentes_v3_es_permanente_y_por_eso_v1_nunca_es_completo():
    """F3. Si esta lista se vaciara, V1 podría declararse `completo` mintiendo:
    Gmail y LeadHub son de V3 y V1 no las consulta (spec §21.3)."""
    assert av1.PENDIENTE_FUENTES_V3.codigo == "fuentes_v3_sin_consultar"
    assert av1.estado_de([av1.PENDIENTE_FUENTES_V3],
                         hubo_fallo=False) == av1.EstadoV1.PREPARADO_CON_PENDIENTES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_secuenciador.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.apertura_v1'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Secuenciador de la primera vertical de apertura (V1) — Plan 5.

**Qué hace y qué no.** Conoce el ORDEN de las etapas de V1, el punto de parada, la
maquina de estados del §24 D4 y la forma del informe. No sabe qué es Drive, ni el CRM,
ni el OCR: recibe las etapas como invocables. Por eso se prueba entero sin disco, sin
red y sin OCR, que es la razón de que viva en `core/` y no en el entrypoint.

**La regla que impide mentir.** El §21.3 ordena que V1 nunca termine `completo`. Eso NO
se implementa devolviendo la constante: se implementa arrancando la lista de pendientes
con `PENDIENTE_FUENTES_V3` dentro. Así el estado es una consecuencia de los datos, y un
test puede comprobar la propiedad en vez de creerse el docstring.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Sequence


class EstadoV1:
    """Los tres estados del §13. Clase-espacio-de-nombres, no enum: el valor viaja a
    un evento JSONL y a la pantalla, y ahi es una cadena."""

    COMPLETO = "completo"
    PREPARADO_CON_PENDIENTES = "preparado_con_pendientes"
    BLOQUEADO = "bloqueado"


@dataclasses.dataclass(frozen=True)
class Pendiente:
    """Algo que V1 no pudo cerrar y que hay que decir en voz alta."""

    codigo: str
    detalle: str


#: Permanente en toda ejecucion V1: Gmail y LeadHub son fuentes de V3 (spec §21.3).
PENDIENTE_FUENTES_V3 = Pendiente(
    codigo="fuentes_v3_sin_consultar",
    detalle="V1 no descubre correo en Gmail ni consulta LeadHub: ambas son de V3. "
            "Si el material de este caso sigue sin depositar, no esta aqui.",
)


def estado_de(pendientes: Sequence[Pendiente], *, hubo_fallo: bool) -> str:
    """Regla pura del §24 D4. `completo` es alcanzable aqui a proposito: quien lo
    impide en V1 es el pendiente permanente, no esta funcion."""
    if hubo_fallo:
        return EstadoV1.BLOQUEADO
    if pendientes:
        return EstadoV1.PREPARADO_CON_PENDIENTES
    return EstadoV1.COMPLETO
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_apertura_v1_secuenciador.py -q`
Expected: PASS, 5 passed

- [ ] **Step 5: Commit**

```bash
git add core/apertura_v1.py tests/test_apertura_v1_secuenciador.py
git commit -m "feat(v1): el vocabulario de estados de la apertura, con el pendiente permanente"
```

---

## Task 2: El secuenciador — orden, parada en fallo y punto de parada

**Files:**
- Modify: `core/apertura_v1.py`
- Test: `tests/test_apertura_v1_secuenciador.py`

**Interfaces:**
- Consumes: `EstadoV1`, `Pendiente`, `PENDIENTE_FUENTES_V3`, `estado_de` de la Task 1.
- Produces:
  - `EtapaResultado(nombre: str, estado: str, detalle: str, pendientes: tuple[Pendiente, ...])`
    con `estado` en `("hecha", "saltada", "fallo")`.
  - `Etapa(nombre: str, correr: Callable[[], EtapaResultado])`.
  - `ResultadoV1(estado: str, etapas: tuple[EtapaResultado, ...], pendientes: tuple[Pendiente, ...], parada: str | None)`.
  - `EtapaDesconocida(ValueError)`.
  - `secuenciar(etapas: Sequence[Etapa], *, hasta: str | None = None) -> ResultadoV1`.

**Contexto:** `hasta` para **después** de ejecutar la etapa nombrada, no antes. Esa es la lectura
que hace útil el flag: `--hasta drive` significa «tráeme el Drive y para ahí», no «no hagas nada».
Un nombre desconocido es un error, porque el fallo silencioso —seguir hasta el final ignorando la
parada pedida— es exactamente la clase de guarda inerte que este proyecto ya se ha cazado tres
veces en un día.

- [ ] **Step 1: Write the failing test**

```python
def _etapa(nombre, estado="hecha", pendientes=(), registro=None):
    def correr():
        if registro is not None:
            registro.append(nombre)
        return av1.EtapaResultado(nombre=nombre, estado=estado,
                                  detalle=f"{nombre}: {estado}",
                                  pendientes=tuple(pendientes))
    return av1.Etapa(nombre=nombre, correr=correr)


def test_las_etapas_corren_en_orden():
    visto = []
    r = av1.secuenciar([_etapa("a", registro=visto), _etapa("b", registro=visto),
                        _etapa("c", registro=visto)])
    assert visto == ["a", "b", "c"]
    assert [e.nombre for e in r.etapas] == ["a", "b", "c"]


def test_f1_un_fallo_detiene_la_secuencia():
    """F1. La etapa posterior NO corre: si corriera, escribiria sobre un caso cuyo
    paso anterior fracaso."""
    visto = []
    r = av1.secuenciar([_etapa("a", registro=visto),
                        _etapa("b", estado="fallo", registro=visto),
                        _etapa("c", registro=visto)])
    assert visto == ["a", "b"]
    assert [e.nombre for e in r.etapas] == ["a", "b"]


def test_f2_un_fallo_deja_el_resultado_bloqueado():
    r = av1.secuenciar([_etapa("a", estado="fallo")])
    assert r.estado == av1.EstadoV1.BLOQUEADO


def test_f3_una_corrida_impecable_sigue_siendo_preparado_con_pendientes():
    """F3 en el secuenciador: aunque las tres etapas salgan `hecha` y sin pendientes
    propios, el permanente esta en la lista."""
    r = av1.secuenciar([_etapa("a"), _etapa("b"), _etapa("c")])
    assert r.estado == av1.EstadoV1.PREPARADO_CON_PENDIENTES
    assert av1.PENDIENTE_FUENTES_V3 in r.pendientes


def test_los_pendientes_de_las_etapas_se_acumulan():
    p = av1.Pendiente(codigo="crm_sin_expediente", detalle="no hay expediente")
    r = av1.secuenciar([_etapa("a", pendientes=[p]), _etapa("b")])
    assert p in r.pendientes


def test_f4_hasta_para_DESPUES_de_la_etapa_nombrada():
    """F4. `--hasta drive` significa «tráeme el Drive y para ahí»."""
    visto = []
    r = av1.secuenciar([_etapa("a", registro=visto), _etapa("b", registro=visto),
                        _etapa("c", registro=visto)], hasta="b")
    assert visto == ["a", "b"]
    assert r.parada == "b"


def test_f5_un_hasta_desconocido_es_error_y_no_corre_nada():
    """F5. Tragarse el nombre y correr entero es la guarda inerte: el operador pidio
    parar y la secuencia hizo lo contrario sin decirlo."""
    visto = []
    with pytest.raises(av1.EtapaDesconocida):
        av1.secuenciar([_etapa("a", registro=visto)], hasta="drve")
    assert visto == []


def test_sin_hasta_la_parada_es_none():
    r = av1.secuenciar([_etapa("a")])
    assert r.parada is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_secuenciador.py -q`
Expected: FAIL con `AttributeError: module 'core.apertura_v1' has no attribute 'EtapaResultado'`

- [ ] **Step 3: Write minimal implementation**

Añadir a `core/apertura_v1.py`, tras `estado_de`:

```python
from collections.abc import Callable

#: Vocabulario cerrado del resultado de una etapa. `saltada` NO es `hecha`: significa
#: que la etapa decidio, con razon declarada, que no habia nada que hacer.
ESTADOS_ETAPA = ("hecha", "saltada", "fallo")


class EtapaDesconocida(ValueError):
    """`hasta` nombra una etapa que no esta en la secuencia."""


@dataclasses.dataclass(frozen=True)
class EtapaResultado:
    nombre: str
    estado: str
    detalle: str
    pendientes: tuple[Pendiente, ...] = ()

    def __post_init__(self):
        if self.estado not in ESTADOS_ETAPA:
            raise ValueError(
                f"estado de etapa fuera del vocabulario: {self.estado!r}; "
                f"validos: {ESTADOS_ETAPA}")


@dataclasses.dataclass(frozen=True)
class Etapa:
    nombre: str
    correr: Callable[[], EtapaResultado]


@dataclasses.dataclass(frozen=True)
class ResultadoV1:
    estado: str
    etapas: tuple[EtapaResultado, ...]
    pendientes: tuple[Pendiente, ...]
    parada: str | None


def secuenciar(etapas: Sequence[Etapa], *, hasta: str | None = None) -> ResultadoV1:
    """Corre las etapas en orden. Para tras `hasta`, y para en el primer `fallo`.

    `hasta` se valida ANTES de correr nada: un nombre mal escrito no puede convertirse
    en «no pares», porque entonces el operador pidio parar y la secuencia siguio.
    """
    nombres = [e.nombre for e in etapas]
    if hasta is not None and hasta not in nombres:
        raise EtapaDesconocida(
            f"--hasta {hasta!r} no es una etapa de V1; validas: {nombres}")

    hechas: list[EtapaResultado] = []
    pendientes: list[Pendiente] = [PENDIENTE_FUENTES_V3]
    hubo_fallo = False
    parada: str | None = None

    for etapa in etapas:
        res = etapa.correr()
        hechas.append(res)
        pendientes.extend(res.pendientes)
        if res.estado == "fallo":
            hubo_fallo = True
            break
        if hasta is not None and etapa.nombre == hasta:
            parada = etapa.nombre
            break

    return ResultadoV1(
        estado=estado_de(pendientes, hubo_fallo=hubo_fallo),
        etapas=tuple(hechas),
        pendientes=tuple(pendientes),
        parada=parada,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_apertura_v1_secuenciador.py -q`
Expected: PASS, 13 passed

- [ ] **Step 5: Commit**

```bash
git add core/apertura_v1.py tests/test_apertura_v1_secuenciador.py
git commit -m "feat(v1): el secuenciador — orden, parada en fallo y punto de parada"
```

---

## Task 3: El adaptador del pull de Drive E&V

**Files:**
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_apertura_v1_etapas.py`

**Interfaces:**
- Consumes: `core.apertura_v1.EtapaResultado`, `core.intake_drive.DriveIntakeResult`.
- Produces: `etapa_drive(ident, case_dir, *, folder_id, team_id, pull=None) -> EtapaResultado`.
  `pull` es el punto de inyección para los tests; por defecto, `_intake_drive_ev`.

**Contexto:** `pull_drive_ev` devuelve `DriveIntakeResult` con `skipped: bool` — `True` cuando el
marcador `.pulled` ya existía y no se forzó (`core/intake_drive.py:206,228`). Eso **no es** «hecha»:
es «ya estaba, no toqué nada», y distinguirlo es lo que hace legible el informe de una segunda
corrida. `errors` no vacío o `rclone_returncode != 0` es `fallo`.

- [ ] **Step 1: Write the failing test**

```python
"""Los adaptadores de las etapas de V1: traducen una llamada real a `EtapaResultado`.

Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md §3 (F6-F12).
"""
from pathlib import Path

import pytest

from core import apertura_v1 as av1
from core.intake_drive import DriveIntakeResult
from scripts import abrir_caso as cli


def _drive_result(**kw):
    base = dict(case_id="C", team_id="T", folder_id="F", target_dir=Path("."),
                files_after=3, skipped=False, rclone_returncode=0, errors=[])
    base.update(kw)
    return DriveIntakeResult(**base)


def test_drive_ok_es_hecha():
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T",
                        pull=lambda: _drive_result())
    assert r.estado == "hecha"
    assert r.pendientes == ()


def test_f6_drive_con_pulled_previo_es_SALTADA_no_hecha():
    """F6. `.pulled` presente = no se re-descargo. Decir «hecha» borraria la
    diferencia entre una primera corrida y una repeticion, que es justo lo que el
    informe de una reanudacion tiene que enseñar."""
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T",
                        pull=lambda: _drive_result(skipped=True))
    assert r.estado == "saltada"


def test_drive_con_errores_es_fallo():
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T",
                        pull=lambda: _drive_result(errors=["rclone: exit 3"]))
    assert r.estado == "fallo"
    assert "exit 3" in r.detalle


def test_drive_con_returncode_no_cero_es_fallo():
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T",
                        pull=lambda: _drive_result(rclone_returncode=3))
    assert r.estado == "fallo"


def test_drive_que_revienta_es_fallo_y_no_propaga():
    def explota():
        raise RuntimeError("token caducado")
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T", pull=explota)
    assert r.estado == "fallo"
    assert "token caducado" in r.detalle
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_etapas.py -q`
Expected: FAIL con `AttributeError: module 'scripts.abrir_caso' has no attribute 'etapa_drive'`

- [ ] **Step 3: Write minimal implementation**

Añadir a `scripts/abrir_caso.py` (tras `_despachar_intake`), y añadir el import
`from core import apertura_v1 as av1` al bloque de imports de `core`:

```python
def etapa_drive(ident, case_dir: Path, *, folder_id, team_id, pull=None):
    """Etapa 1 de V1: materializar la carpeta de Drive E&V.

    `skipped` NO es `hecha`: el marcador `.pulled` significa «ya estaba y no toque
    nada» (`core/intake_drive.py:206`), y esa diferencia es lo unico que distingue en
    el informe una primera corrida de una reanudacion.
    """
    def _pull():
        return intake_drive.pull_drive_ev(ident.case_id, folder_id, team_id)

    try:
        res = (pull or _pull)()
    except Exception as exc:  # noqa: BLE001 — el estado de V1 es el producto, no la traza
        return av1.EtapaResultado(nombre="drive", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")
    if res.errors or res.rclone_returncode != 0:
        return av1.EtapaResultado(
            nombre="drive", estado="fallo",
            detalle=f"rclone rc={res.rclone_returncode}; errores={res.errors}")
    if res.skipped:
        return av1.EtapaResultado(
            nombre="drive", estado="saltada",
            detalle=f"`.pulled` ya presente: {res.files_after} ficheros en destino")
    return av1.EtapaResultado(
        nombre="drive", estado="hecha",
        detalle=f"{res.files_after} ficheros en {res.target_dir}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_apertura_v1_etapas.py -q`
Expected: PASS, 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_apertura_v1_etapas.py
git commit -m "feat(v1): adaptador del pull de Drive E&V, con `.pulled` como `saltada`"
```

---

## Task 4: El adaptador del pull del CRM, con el `element` explícito

**Files:**
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_apertura_v1_etapas.py`

**Interfaces:**
- Consumes: `core.apertura_v1.EtapaResultado`, `core.casos.case_locator.read_case_meta`,
  `core.sync_sudespacho.pull_expediente_v2`.
- Produces: `etapa_crm(ident, case_dir, *, leer_meta=None, pull=None) -> EtapaResultado`.

**Contexto, y es el punto más delicado del plan.** `pull_expediente_v2` declara
`element: str = "expedientes_judiciales"` (`core/sync_sudespacho.py:1356`). El criterio 38 de la
spec exige que la vía sea explícita **en las dos direcciones**, y advierte de que la peligrosa es
la que un test ingenuo no cubre: *una apertura extrajudicial colándose por la rama judicial*, que
es justo lo que produce ese default. Por eso:

- el `element` sale del `ExpedienteLink` registrado en `_caso.md`
  (`CaseMeta.sudespacho_expedientes`, `core/case_manager.py:87`), **y de ningún otro sitio**;
- un link **con `id` y sin `element`** es `fallo`, no una adivinanza;
- un caso **sin link ninguno** es `saltada` con pendiente, porque el alta CRM es V2 y un caso nuevo
  legítimamente no tiene expediente que consultar. Abortar ahí dejaría la secuencia inútil justo
  para los casos nuevos, que son su terreno.

- [ ] **Step 1: Write the failing test**

```python
class _IdentFalsa:
    def __init__(self, case_id="C"):
        self.case_id = case_id
        self.w_code = "W-000000"


def test_f7_el_element_sale_del_link_y_nunca_del_default():
    """F7. El default de `pull_expediente_v2` es JUDICIAL: un caso extrajudicial que
    lo herede se pulla de la rama equivocada sin decir nada (criterio 38)."""
    visto = {}

    def pull(case_id, expediente_id, *, element):
        visto.update(case_id=case_id, expediente_id=expediente_id, element=element)
        return object()

    meta = {"sudespacho_expedientes": [
        {"id": "648", "element": "extrajudiciales", "input_dir": "sudespacho_648"}]}
    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: meta, pull=pull)
    assert r.estado == "hecha"
    assert visto["element"] == "extrajudiciales"
    assert visto["expediente_id"] == "648"


def test_f8_un_link_sin_element_es_fallo_y_no_se_adivina():
    """F8. Rellenar el hueco con el default es exactamente el defecto del criterio 38."""
    meta = {"sudespacho_expedientes": [{"id": "648", "input_dir": "sudespacho_648"}]}
    llamado = []
    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: meta,
                      pull=lambda *a, **k: llamado.append(1))
    assert r.estado == "fallo"
    assert "element" in r.detalle
    assert llamado == [], "no se puede pullar sin saber la rama"


def test_f9_un_caso_sin_expediente_registrado_es_saltada_con_pendiente():
    """F9. El alta CRM es V2: un caso nuevo no tiene expediente. Abortar aqui dejaria
    la secuencia inutil justo para los casos nuevos."""
    r = cli.etapa_crm(_IdentFalsa(), Path("."),
                      leer_meta=lambda _d: {"sudespacho_expedientes": []},
                      pull=lambda *a, **k: pytest.fail("no debe pullar"))
    assert r.estado == "saltada"
    assert [p.codigo for p in r.pendientes] == ["crm_sin_expediente"]


def test_crm_que_revienta_es_fallo():
    meta = {"sudespacho_expedientes": [
        {"id": "648", "element": "extrajudiciales", "input_dir": "d"}]}

    def explota(*a, **k):
        raise RuntimeError("PHPSESSID caducada")

    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: meta, pull=explota)
    assert r.estado == "fallo"
    assert "PHPSESSID" in r.detalle


def test_varios_links_se_pullan_todos():
    vistos = []

    def pull(case_id, expediente_id, *, element):
        vistos.append((expediente_id, element))
        return object()

    meta = {"sudespacho_expedientes": [
        {"id": "648", "element": "extrajudiciales", "input_dir": "a"},
        {"id": "649", "element": "expedientes_judiciales", "input_dir": "b"}]}
    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: meta, pull=pull)
    assert r.estado == "hecha"
    assert vistos == [("648", "extrajudiciales"), ("649", "expedientes_judiciales")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_etapas.py -q`
Expected: FAIL con `AttributeError: module 'scripts.abrir_caso' has no attribute 'etapa_crm'`

- [ ] **Step 3: Write minimal implementation**

Añadir a `scripts/abrir_caso.py`:

```python
def etapa_crm(ident, case_dir: Path, *, leer_meta=None, pull=None):
    """Etapa 2 de V1: pull del expediente CRM ya registrado.

    **El `element` sale del `ExpedienteLink` y de ningun otro sitio.**
    `sync_sudespacho.pull_expediente_v2` lo declara con default
    `"expedientes_judiciales"` (`core/sync_sudespacho.py:1356`), y el criterio 38 de la
    spec avisa de que el cruce peligroso es el inverso al obvio: una apertura
    EXTRAJUDICIAL colandose por la rama judicial. Heredar ese default es producirlo.
    """
    from core import sync_sudespacho

    _leer = leer_meta or case_locator.read_case_meta
    _pull = pull or sync_sudespacho.pull_expediente_v2

    try:
        meta = _leer(case_dir)
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="crm", estado="fallo",
                                  detalle=f"no se pudo leer _caso.md: {exc}")

    links = list(meta.get("sudespacho_expedientes") or [])
    if not links:
        return av1.EtapaResultado(
            nombre="crm", estado="saltada",
            detalle="sin expediente CRM registrado en _caso.md",
            pendientes=(av1.Pendiente(
                codigo="crm_sin_expediente",
                detalle="El caso no tiene expediente CRM vinculado, asi que no hay nada "
                        "que pullar. El alta CRM es de V2."),))

    sin_element = [l for l in links if not l.get("element")]
    if sin_element:
        return av1.EtapaResultado(
            nombre="crm", estado="fallo",
            detalle=f"expediente(s) sin `element` en _caso.md: "
                    f"{[l.get('id') for l in sin_element]}. No se adivina: el default "
                    f"del pull es judicial y el criterio 38 prohibe heredarlo.")

    hechos = []
    for link in links:
        try:
            _pull(ident.case_id, str(link["id"]), element=link["element"])
        except Exception as exc:  # noqa: BLE001
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"pull de {link['id']} ({link['element']}) fallo: "
                        f"{type(exc).__name__}: {exc}")
        hechos.append(f"{link['id']}/{link['element']}")
    return av1.EtapaResultado(nombre="crm", estado="hecha",
                              detalle="pullados: " + ", ".join(hechos))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_apertura_v1_etapas.py -q`
Expected: PASS, 10 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_apertura_v1_etapas.py
git commit -m "feat(v1): adaptador del pull CRM con el element explicito (criterio 38)"
```

---

## Task 5: `apply` devuelve el status de la atomización

**Files:**
- Modify: `scripts/sala_maquina.py:578-640` (`_atomizar_correo`), `:779-918` (`apply`)
- Test: `tests/test_sala_maquina_cableado_atomize.py`

**Interfaces:**
- Produces: `_atomizar_correo(case_id, case_dir) -> str | None` con `"ok" | "parcial" | "fallo" |
  None`; `apply(...) -> str | None` que devuelve ese mismo valor.

**Contexto:** hoy `_atomizar_correo` devuelve `None` y el status solo viaja dentro del evento
`atomizado_email`. Su propio docstring dice que «el consumidor DEBE leer el `status` del evento».
Leer el evento **también** funcionaría, pero tiene una trampa medible: si esta corrida no ejecutó la
atomización (el no-op estricto de `:596`, sin correo y sin árbol previo), el último evento del log
es de una corrida **anterior**, y el secuenciador reportaría un status ajeno como propio. Devolverlo
elimina la clase entera de ese error. `None` = no se ejecutó, que no es lo mismo que `ok`.

Typer ignora el valor de retorno de un comando, así que el CLI no cambia de comportamiento.

- [ ] **Step 1: Write the failing test**

Añadir a `tests/test_sala_maquina_cableado_atomize.py`:

```python
def test_atomizar_correo_devuelve_el_status(tmp_path, monkeypatch):
    """El status va al valor de retorno, no solo al evento: si esta corrida no atomiza,
    el ultimo evento del log es de OTRA corrida y leerlo miente."""
    from scripts import sala_maquina as sm_cli

    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)

    class _Report:
        publicado = True
        errores = ["un fallo blando"]
        eml_leidos = 2
        poda_omitida = False
        mensajes = 2
        adjuntos_unicos = 0
        reconstruidos_b = 0
        citas_a_revision = 0
        upgrades = 0
        notas = []
        fallos_lectura = []

        def resumen(self):
            return "2 mensajes"

    monkeypatch.setattr(sm_cli.atomize, "contar_eml", lambda _f: 2)
    monkeypatch.setattr(sm_cli.atomize, "atomize_dir",
                        lambda *a, **k: _Report())
    assert sm_cli._atomizar_correo("C", case_dir) == "parcial"


def test_atomizar_correo_devuelve_none_cuando_no_se_ejecuta(tmp_path, monkeypatch):
    """El no-op estricto (`:596`): sin correo y sin arbol previo no se llama al motor.
    `None` NO es `ok`, y el secuenciador tiene que poder distinguirlo."""
    from scripts import sala_maquina as sm_cli

    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)
    monkeypatch.setattr(sm_cli.atomize, "contar_eml", lambda _f: 0)
    monkeypatch.setattr(sm_cli.atomize, "atomize_dir",
                        lambda *a, **k: pytest.fail("no debe llamarse"))
    assert sm_cli._atomizar_correo("C", case_dir) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sala_maquina_cableado_atomize.py -q -k devuelve`
Expected: FAIL — `assert None == 'parcial'`

- [ ] **Step 3: Write minimal implementation**

En `scripts/sala_maquina.py`:

1. Cambiar la firma y el docstring de `_atomizar_correo`:

```python
def _atomizar_correo(case_id: str, case_dir: Path) -> str | None:
    """Atomiza el correo del caso ANTES del OCR (cableado, spec 2026-07-27 §4).

    Devuelve el status de ESTA corrida — `"ok" | "parcial" | "fallo"` — o `None` si no
    se ejecuto (no-op estricto). Lo devuelve ademas de emitirlo en el evento porque el
    consumidor que lee el ultimo `atomizado_email` del log no puede saber si es suyo:
    en una corrida que no atomiza, el ultimo evento es de la corrida anterior.
    """
```

2. En el no-op estricto, `return None` en vez de `return`:

```python
    if n == 0 and not out.exists():
        return None
```

3. Al final de la función, después de emitir el evento, devolver el status:

```python
    return details.get("status")
```

4. En `apply`, capturar y devolver el valor. La llamada actual a `_atomizar_correo` pasa a:

```python
        status_atomizacion = _atomizar_correo(case_id, case_dir)
```

y la última línea del cuerpo de `apply`, tras el `typer.echo` del siguiente paso sugerido:

```python
        # Typer ignora el retorno de un comando, asi que el CLI no cambia. Quien lo lee
        # es el secuenciador de V1, que llama a esta funcion directamente (el idiom de
        # los tests de este repo) y necesita el status para la maquina de estados de D4.
        return status_atomizacion
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sala_maquina_cableado_atomize.py -q`
Expected: PASS, todos los tests del fichero (los previos incluidos, sin regresión)

- [ ] **Step 5: Commit**

```bash
git add scripts/sala_maquina.py tests/test_sala_maquina_cableado_atomize.py
git commit -m "feat(v1): apply devuelve el status de la atomizacion de SU corrida"
```

---

## Task 6: El adaptador de la sala de máquina

**Files:**
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_apertura_v1_etapas.py`

**Interfaces:**
- Consumes: `scripts.sala_maquina.apply` (Task 5).
- Produces: `etapa_sala_maquina(ident, *, correr=None) -> EtapaResultado`.

**Contexto:** aquí se aplica la máquina de estados del §24 D4, que separa el comportamiento del
motor del resultado de V1: el OCR **sigue** aunque la atomización falle —eso no se regresa— pero el
resultado de V1 sí lo refleja. `ok` y `None` → `hecha` sin pendiente; `parcial` → `hecha` **con**
pendiente; `fallo` → `fallo`. Y `typer.Exit` con código distinto de 0 es un `fallo` del OCR, no una
excepción que deba propagarse fuera de la secuencia.

Este es el único punto donde `scripts/abrir_caso.py` importa otro script. El import va **dentro de
la función**, no en el módulo: `scripts/sala_maquina.py` arrastra el motor de OCR y el atomizador,
y pagarlo en cada `--help` del modo `libre` sería una regresión de arranque para los 103 llamadores.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize("status,estado,hay_pendiente", [
    ("ok", "hecha", False),
    (None, "hecha", False),      # F12: no se ejecuto != quedo pendiente
    ("parcial", "hecha", True),  # F10
])
def test_f10_f12_el_status_de_atomizacion_gobierna_el_pendiente(status, estado,
                                                                hay_pendiente):
    r = cli.etapa_sala_maquina(_IdentFalsa(), correr=lambda: status)
    assert r.estado == estado
    assert bool(r.pendientes) is hay_pendiente


def test_f11_atomizacion_en_fallo_bloquea_la_etapa():
    """F11. D4: `fallo` de atomizacion deja V1 `bloqueado`."""
    r = cli.etapa_sala_maquina(_IdentFalsa(), correr=lambda: "fallo")
    assert r.estado == "fallo"


def test_un_typer_exit_no_cero_del_ocr_es_fallo():
    import typer

    def revienta():
        raise typer.Exit(code=2)

    r = cli.etapa_sala_maquina(_IdentFalsa(), correr=revienta)
    assert r.estado == "fallo"
    assert "2" in r.detalle


def test_un_typer_exit_cero_no_es_fallo():
    import typer

    def sale_limpio():
        raise typer.Exit(code=0)

    r = cli.etapa_sala_maquina(_IdentFalsa(), correr=sale_limpio)
    assert r.estado == "hecha"


def test_una_excepcion_del_ocr_es_fallo():
    def explota():
        raise RuntimeError("ocrmypdf no esta instalado")

    r = cli.etapa_sala_maquina(_IdentFalsa(), correr=explota)
    assert r.estado == "fallo"
    assert "ocrmypdf" in r.detalle
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_etapas.py -q`
Expected: FAIL con `AttributeError: module 'scripts.abrir_caso' has no attribute 'etapa_sala_maquina'`

- [ ] **Step 3: Write minimal implementation**

```python
def etapa_sala_maquina(ident, *, correr=None):
    """Etapa 3 de V1: atomizacion del correo depositado + OCR y espejos MD.

    La maquina de estados es la del §24 D4: el motor NO cambia —el OCR sigue aunque la
    atomizacion falle— y lo que cambia es el resultado de V1, que si lo refleja.

    El import va dentro: `scripts/sala_maquina` arrastra el motor de OCR y el
    atomizador, y pagarlo en cada arranque del modo `libre` seria una regresion para
    los 103 llamadores del entrypoint.
    """
    def _correr():
        from scripts import sala_maquina
        return sala_maquina.apply(case_id=ident.case_id)

    try:
        status = (correr or _correr)()
    except typer.Exit as exc:
        codigo = getattr(exc, "exit_code", 0) or 0
        if codigo:
            return av1.EtapaResultado(
                nombre="sala_maquina", estado="fallo",
                detalle=f"la sala de maquina salio con codigo {codigo}")
        status = None
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="sala_maquina", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")

    if status == "fallo":
        return av1.EtapaResultado(
            nombre="sala_maquina", estado="fallo",
            detalle="la atomizacion del correo fallo (§24 D4: bloquea el cierre de V1)")
    if status == "parcial":
        return av1.EtapaResultado(
            nombre="sala_maquina", estado="hecha",
            detalle="OCR hecho; atomizacion PARCIAL",
            pendientes=(av1.Pendiente(
                codigo="atomizacion_parcial",
                detalle="La atomizacion publico con errores o con poda omitida: "
                        "`01_Procesado/Emails` no esta completo. Ver el evento "
                        "`atomizado_email` en `_intake_log.jsonl`."),))
    return av1.EtapaResultado(
        nombre="sala_maquina", estado="hecha",
        detalle=("OCR hecho; sin correo que atomizar" if status is None
                 else "OCR hecho; atomizacion ok"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_apertura_v1_etapas.py -q`
Expected: PASS, 17 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_apertura_v1_etapas.py
git commit -m "feat(v1): adaptador de la sala de maquina con la maquina de estados de D4"
```

---

## Task 7: El evento que deja constancia del estado

**Files:**
- Modify: `core/intake_log.py:41` (`INTAKE_EVENTS`)
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_apertura_v1_cableado.py`

**Interfaces:**
- Produces: el evento `"apertura_v1_terminada"` en `INTAKE_EVENTS`, y
  `registrar_cierre_v1(case_dir, ident, resultado) -> None`.

**Contexto:** `INTAKE_EVENTS` es un **frozenset cerrado** (`core/intake_log.py:38-41`) y emitir un
nombre que no esté dentro es un evento imposible — el defecto exacto que R14 encontró en una versión
anterior de esta familia de trabajo. El `details` lleva `estado`, la lista de `pendientes` y el
resumen por etapa, que es lo que convierte «terminó» en algo auditable seis meses después.

- [ ] **Step 1: Write the failing test**

```python
"""El cableado de la secuencia detras de `--modo v1`.

Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md §3 (F13-F14).
"""
import json

from core import apertura_v1 as av1
from core import intake_log
from scripts import abrir_caso as cli


def test_f13_el_evento_de_cierre_esta_en_el_set_cerrado():
    """F13. `INTAKE_EVENTS` es cerrado: un nombre fuera del set es un evento imposible
    de emitir, y el fallo no aparece hasta que alguien intenta emitirlo."""
    assert "apertura_v1_terminada" in intake_log.INTAKE_EVENTS


def test_el_evento_de_cierre_lleva_el_estado_y_los_pendientes(tmp_path):
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)

    resultado = av1.ResultadoV1(
        estado=av1.EstadoV1.PREPARADO_CON_PENDIENTES,
        etapas=(av1.EtapaResultado(nombre="drive", estado="hecha", detalle="3 ficheros"),),
        pendientes=(av1.PENDIENTE_FUENTES_V3,),
        parada=None,
    )

    class _Ident:
        case_id = "C"
        w_code = "W-000000"

    cli.registrar_cierre_v1(case_dir, _Ident(), resultado)

    log = case_dir / "00_Input" / "_intake_log.jsonl"
    lineas = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l]
    ev = [l for l in lineas if l["event"] == "apertura_v1_terminada"][-1]
    assert ev["details"]["estado"] == "preparado_con_pendientes"
    assert ev["details"]["pendientes"] == ["fuentes_v3_sin_consultar"]
    assert ev["details"]["etapas"] == [{"nombre": "drive", "estado": "hecha"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_cableado.py -q`
Expected: FAIL — `assert 'apertura_v1_terminada' in frozenset({...})`

- [ ] **Step 3: Write minimal implementation**

1. En `core/intake_log.py`, dentro del `frozenset` (y actualizando el «27 tipos» del docstring de
   cabecera a 28):

```python
    "apertura_v1_terminada",  # cierre de la secuencia de V1 con su estado y pendientes
```

2. En `scripts/abrir_caso.py`:

```python
def registrar_cierre_v1(case_dir: Path, ident, resultado) -> None:
    """Deja el estado de V1 en el log forense del caso.

    Es el unico rastro durable de la corrida: la pantalla se pierde, el `.jsonl` no.
    """
    intake_log.append_event(
        case_dir, "apertura_v1_terminada", case_id=ident.case_id,
        details={
            "estado": resultado.estado,
            "parada": resultado.parada,
            "pendientes": [p.codigo for p in resultado.pendientes],
            "etapas": [{"nombre": e.nombre, "estado": e.estado}
                       for e in resultado.etapas],
        },
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_apertura_v1_cableado.py -q`
Expected: PASS, 2 passed

- [ ] **Step 5: Commit**

```bash
git add core/intake_log.py scripts/abrir_caso.py tests/test_apertura_v1_cableado.py
git commit -m "feat(v1): evento apertura_v1_terminada con estado, pendientes y etapas"
```

---

## Task 8: El cableado en `main`, el flag `--hasta` y el código de salida

**Files:**
- Modify: `scripts/abrir_caso.py:646-679` (el bloque bajo mutex) y la firma de `main`
- Test: `tests/test_apertura_v1_cableado.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: `secuencia_v1(ident, case_dir, *, folder_id, team_id, hasta=None, etapas=None) -> ResultadoV1`
  y el flag `--hasta` en `main`.

**Contexto, y es lo que hace que este plan exista:** el bloque `with mutex_sesion.sostenido(...)`
de `:646` ya cubre esqueleto + intake + alta CRM. La secuencia se inserta **dentro** de ese bloque,
después de `_despachar_intake`. Un solo mutex para toda la corrida, y las adquisiciones anidadas de
`sala_maquina` se unen a la sesión existente en vez de chocar, que es exactamente lo que
`mutex_sesion` construyó.

El orden es el de D3: **Drive → CRM → sala de máquina** (la atomización va dentro de la tercera).
La etapa de Drive la ejecuta `_despachar_intake`, que ya corre antes; el adaptador `etapa_drive` la
envuelve para que la secuencia tenga un resultado que informar, así que en `--modo v1` el despacho
por fuente **se sustituye** por la secuencia y no se duplica.

- [ ] **Step 1: Write the failing test**

```python
def test_una_corrida_completa_toca_TODAS_las_fases_de_v1():
    """El criterio que el bloque 4 del §21.5 pide literalmente: «un test que afirme que
    una corrida completa toca todas las fases de V1»."""
    visto = []

    def _fake(nombre):
        return av1.Etapa(nombre=nombre,
                         correr=lambda: (visto.append(nombre) or
                                         av1.EtapaResultado(nombre=nombre,
                                                            estado="hecha",
                                                            detalle="ok")))

    r = cli.secuencia_v1(None, None, folder_id="F", team_id="T",
                         etapas=[_fake("drive"), _fake("crm"), _fake("sala_maquina")])
    assert visto == ["drive", "crm", "sala_maquina"]
    assert r.estado == av1.EstadoV1.PREPARADO_CON_PENDIENTES


def test_f4_hasta_drive_no_toca_el_crm_ni_la_sala():
    visto = []

    def _fake(nombre):
        return av1.Etapa(nombre=nombre,
                         correr=lambda: (visto.append(nombre) or
                                         av1.EtapaResultado(nombre=nombre,
                                                            estado="hecha",
                                                            detalle="ok")))

    cli.secuencia_v1(None, None, folder_id="F", team_id="T", hasta="drive",
                     etapas=[_fake("drive"), _fake("crm"), _fake("sala_maquina")])
    assert visto == ["drive"]


def test_f14_un_resultado_bloqueado_sale_con_codigo_no_cero():
    """F14. Salir 0 con la secuencia bloqueada es lo que hace que un script que la
    invoque siga adelante como si nada."""
    assert cli.codigo_de_salida(av1.EstadoV1.BLOQUEADO) != 0
    assert cli.codigo_de_salida(av1.EstadoV1.PREPARADO_CON_PENDIENTES) == 0
    assert cli.codigo_de_salida(av1.EstadoV1.COMPLETO) == 0


def test_el_modo_libre_no_ejecuta_la_secuencia(monkeypatch):
    """Sin regresion para los 103 llamadores: `libre` sigue despachando por fuente."""
    llamado = []
    monkeypatch.setattr(cli, "secuencia_v1",
                        lambda *a, **k: llamado.append(1))
    assert cli.validar_modo("libre", crm="api", fuente="manual") == []
    assert llamado == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_cableado.py -q`
Expected: FAIL con `AttributeError: module 'scripts.abrir_caso' has no attribute 'secuencia_v1'`

- [ ] **Step 3: Write minimal implementation**

1. Las dos funciones nuevas en `scripts/abrir_caso.py`:

```python
def codigo_de_salida(estado: str) -> int:
    """`bloqueado` sale distinto de 0: un script que invoque la secuencia tiene que
    poder distinguir «termino con pendientes» de «no termino»."""
    return 1 if estado == av1.EstadoV1.BLOQUEADO else 0


def secuencia_v1(ident, case_dir, *, folder_id, team_id, hasta=None, etapas=None):
    """El orden completo de V1 (spec §24 D3): Drive -> CRM -> sala de maquina.

    La atomizacion del correo depositado va DENTRO de la tercera, que es donde el
    cableado de 2026-07-27 la puso; por eso el gotcha del runbook —atomizar y pull
    antes del OCR— se cumple por construccion y no por memoria del operador.

    `etapas` es el punto de inyeccion de los tests. En produccion se construyen aqui.
    """
    if etapas is None:
        etapas = [
            av1.Etapa("drive", lambda: etapa_drive(
                ident, case_dir, folder_id=folder_id, team_id=team_id)),
            av1.Etapa("crm", lambda: etapa_crm(ident, case_dir)),
            av1.Etapa("sala_maquina", lambda: etapa_sala_maquina(ident)),
        ]
    return av1.secuenciar(etapas, hasta=hasta)


def _informar_v1(resultado) -> None:
    """El informe en pantalla. Lo durable es el evento; esto es para el operador."""
    typer.echo("")
    typer.echo(f"=== Apertura V1: {resultado.estado} ===")
    for e in resultado.etapas:
        typer.echo(f"  [{e.estado:>7}] {e.nombre}: {e.detalle}")
    if resultado.parada:
        typer.echo(f"  (parada pedida tras la etapa {resultado.parada!r})")
    for p in resultado.pendientes:
        typer.echo(f"  PENDIENTE {p.codigo}: {p.detalle}")
```

2. El flag en la firma de `main`, junto a `--modo`:

```python
    hasta: str | None = typer.Option(
        None, "--hasta",
        help="v1: para DESPUES de esta etapa (drive|crm|sala_maquina). Reanudar es "
             "volver a lanzar la misma orden: lo hecho se salta solo."),
```

3. En `validar_modo`, rechazar `--hasta` en modo `libre` (parámetro nuevo `hasta=None`):

```python
    # `--hasta` solo tiene dueño de secuencia en v1. En `libre` no hay secuencia que
    # parar, y aceptarlo en silencio seria decir que se hizo caso a una peticion que
    # nadie leyo.
```

En la rama `if modo == "libre":` la comprobación va **antes** del `return []`:

```python
    if modo == "libre":
        if hasta is not None:
            return ["--hasta solo existe en --modo v1: en `libre` no hay secuencia "
                    "que parar, y aceptarlo en silencio fingiria haberla parado."]
        return []
```

4. Dentro del bloque `with mutex_sesion.sostenido(...)`, sustituir la llamada a
   `_despachar_intake` por una bifurcación por modo:

```python
        if modo == "v1":
            resultado = secuencia_v1(ident, case_dir, folder_id=folder_id,
                                     team_id=team_id, hasta=hasta)
            registrar_cierre_v1(case_dir, ident, resultado)
            _informar_v1(resultado)
            raise typer.Exit(code=codigo_de_salida(resultado.estado))

        # 5.3-5.7 intake por fuente (modo `libre`)
        _despachar_intake(
            fuente, ident, case_dir,
            folder_id=folder_id, team_id=team_id, src=src, rol=rol,
            cuenta=cuenta, label=label, dry_run=dry_run,
            extraer_adjuntos=extraer_adjuntos,
        )
```

5. Pasar `hasta=hasta` en la llamada a `validar_modo` de `:532`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_apertura_v1_cableado.py tests/test_abrir_caso_modo_v1.py tests/test_abrir_caso_cli.py -q`
Expected: PASS, sin regresión en los dos ficheros previos

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_apertura_v1_cableado.py
git commit -m "feat(v1): cablear la secuencia bajo el mutex, con --hasta y codigo de salida"
```

---

## Task 9: El arnés de mutación — catorce mutantes, uno por frontera

**Files:**
- Create: `tests/_mutantes_plan5.py`

**Interfaces:**
- Produces: `python -m tests._mutantes_plan5` con salida `MUERTO`/`VIVO` por mutante y código de
  salida distinto de 0 si alguno sobrevive.

**Contexto, y es la lección que los Planes 2-5 heredan:** una prueba de mutación vale lo que vale
su elección de mutante. El §3 enumera catorce fronteras, así que hacen falta catorce mutantes, uno
por frontera. Un mutante que mata **más** tests de los previstos está **mal apuntado**, no bien
elegido: si el mutante F6 mata tests de F7, no está probando F6.

**Y antes de mutar, commitea:** `git checkout` restaura desde el **índice**, así que mutar sobre
trabajo sin commitear y restaurar después lo pierde.

- [ ] **Step 1: Write the harness**

```python
"""Arnes de mutacion del Plan 5: catorce mutantes, uno por frontera del §3.

Uso: python -m tests._mutantes_plan5

Cada entrada muta UNA linea de produccion y declara que tests DEBEN ponerse rojos. Un
mutante que mata mas tests de los declarados esta MAL APUNTADO: no prueba su frontera,
prueba otra cosa. Un mutante que sobrevive significa que la frontera no esta contratada.

Restaura con `git checkout -- <fichero>`, que lee del INDICE: commitea antes de correr.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# (id, fichero, texto_original, texto_mutado, test_que_debe_morir)
MUTANTES = [
    ("F1", "core/apertura_v1.py",
     "            hubo_fallo = True\n            break",
     "            hubo_fallo = True",
     "tests/test_apertura_v1_secuenciador.py::test_f1_un_fallo_detiene_la_secuencia"),
    ("F2", "core/apertura_v1.py",
     "    if hubo_fallo:\n        return EstadoV1.BLOQUEADO",
     "    if False:\n        return EstadoV1.BLOQUEADO",
     "tests/test_apertura_v1_secuenciador.py::test_f2_un_fallo_deja_el_resultado_bloqueado"),
    ("F3", "core/apertura_v1.py",
     "    pendientes: list[Pendiente] = [PENDIENTE_FUENTES_V3]",
     "    pendientes: list[Pendiente] = []",
     "tests/test_apertura_v1_secuenciador.py::"
     "test_f3_una_corrida_impecable_sigue_siendo_preparado_con_pendientes"),
    ("F4", "core/apertura_v1.py",
     "        if hasta is not None and etapa.nombre == hasta:\n"
     "            parada = etapa.nombre\n            break",
     "        if hasta is not None and etapa.nombre == hasta:\n"
     "            parada = etapa.nombre",
     "tests/test_apertura_v1_secuenciador.py::test_f4_hasta_para_DESPUES_de_la_etapa_nombrada"),
    ("F5", "core/apertura_v1.py",
     "    if hasta is not None and hasta not in nombres:\n        raise EtapaDesconocida(",
     "    if False:\n        raise EtapaDesconocida(",
     "tests/test_apertura_v1_secuenciador.py::test_f5_un_hasta_desconocido_es_error_y_no_corre_nada"),
    ("F6", "scripts/abrir_caso.py",
     '    if res.skipped:\n        return av1.EtapaResultado(\n'
     '            nombre="drive", estado="saltada",',
     '    if res.skipped:\n        return av1.EtapaResultado(\n'
     '            nombre="drive", estado="hecha",',
     "tests/test_apertura_v1_etapas.py::test_f6_drive_con_pulled_previo_es_SALTADA_no_hecha"),
    ("F7", "scripts/abrir_caso.py",
     '            _pull(ident.case_id, str(link["id"]), element=link["element"])',
     '            _pull(ident.case_id, str(link["id"]), element="expedientes_judiciales")',
     "tests/test_apertura_v1_etapas.py::test_f7_el_element_sale_del_link_y_nunca_del_default"),
    ("F8", "scripts/abrir_caso.py",
     '    sin_element = [l for l in links if not l.get("element")]',
     '    sin_element = []',
     "tests/test_apertura_v1_etapas.py::test_f8_un_link_sin_element_es_fallo_y_no_se_adivina"),
    ("F9", "scripts/abrir_caso.py",
     '            nombre="crm", estado="saltada",\n'
     '            detalle="sin expediente CRM registrado en _caso.md",',
     '            nombre="crm", estado="fallo",\n'
     '            detalle="sin expediente CRM registrado en _caso.md",',
     "tests/test_apertura_v1_etapas.py::"
     "test_f9_un_caso_sin_expediente_registrado_es_saltada_con_pendiente"),
    ("F10", "scripts/abrir_caso.py",
     '    if status == "parcial":',
     '    if False:',
     "tests/test_apertura_v1_etapas.py::"
     "test_f10_f12_el_status_de_atomizacion_gobierna_el_pendiente[parcial-hecha-True]"),
    ("F11", "scripts/abrir_caso.py",
     '    if status == "fallo":',
     '    if False:',
     "tests/test_apertura_v1_etapas.py::test_f11_atomizacion_en_fallo_bloquea_la_etapa"),
    ("F12", "scripts/abrir_caso.py",
     '        detalle=("OCR hecho; sin correo que atomizar" if status is None',
     '        detalle=("OCR hecho; atomizacion ok" if status is None',
     "tests/test_apertura_v1_etapas.py::"
     "test_f10_f12_el_status_de_atomizacion_gobierna_el_pendiente[None-hecha-False]"),
    ("F13", "core/intake_log.py",
     '    "apertura_v1_terminada",',
     "",
     "tests/test_apertura_v1_cableado.py::test_f13_el_evento_de_cierre_esta_en_el_set_cerrado"),
    ("F14", "scripts/abrir_caso.py",
     "    return 1 if estado == av1.EstadoV1.BLOQUEADO else 0",
     "    return 0",
     "tests/test_apertura_v1_cableado.py::test_f14_un_resultado_bloqueado_sale_con_codigo_no_cero"),
]


def _correr(nodeid: str) -> bool:
    """True si el test PASA."""
    r = subprocess.run(
        [sys.executable, "-m", "pytest", nodeid, "-q", "--no-header", "-p", "no:randomly"],
        cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace")
    return r.returncode == 0


def main() -> int:
    vivos = []
    for ident, rel, viejo, nuevo, nodeid in MUTANTES:
        f = RAIZ / rel
        original = f.read_text(encoding="utf-8")
        if viejo not in original:
            print(f"{ident}: ARNES ROTO — el texto a mutar no esta en {rel}")
            vivos.append(ident)
            continue
        f.write_text(original.replace(viejo, nuevo, 1), encoding="utf-8")
        try:
            paso = _correr(nodeid)
        finally:
            f.write_text(original, encoding="utf-8")
        if paso:
            print(f"{ident}: VIVO — {nodeid} sigue verde con la mutacion aplicada")
            vivos.append(ident)
        else:
            print(f"{ident}: MUERTO")
    if vivos:
        print(f"\n{len(vivos)} mutante(s) VIVO(s): {vivos}")
        return 1
    print(f"\n{len(MUTANTES)}/{len(MUTANTES)} mutantes muertos, cada uno por su frontera.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Commit before mutating**

```bash
git add tests/_mutantes_plan5.py && git commit -m "test(v1): arnes de mutacion, catorce fronteras"
```

- [ ] **Step 3: Run the harness**

Run: `python -m tests._mutantes_plan5`
Expected: `14/14 mutantes muertos, cada uno por su frontera.` y código de salida 0.

- [ ] **Step 4: Si algún mutante sobrevive**

No es un fallo del arnés: es una frontera **sin contratar**. Añade el test que la cubra y vuelve a
correr. Y si un mutante mata más tests de los declarados, **reapúntalo**: está probando otra cosa.

- [ ] **Step 5: Commit**

```bash
git add -u && git commit -m "test(v1): 14/14 mutantes muertos"
```

---

## Task 10: E2E de la secuencia con fixtures sin PII

**Files:**
- Create: `tests/test_apertura_v1_e2e.py`

**Interfaces:**
- Consumes: todo lo anterior.

**Contexto:** el bloque 5 del §21.5 pide «E2E de V1 con fixtures sin PII». El OCR real no entra
aquí: es lento y no es lo que este plan construye. Lo que el E2E demuestra es que **la secuencia
recorre las tres etapas sobre un árbol de caso real en disco, deja el evento y es punto fijo**.
`pytest-randomly` está activo en este repo, así que el test no puede depender del orden.

- [ ] **Step 1: Write the failing test**

```python
"""E2E de la secuencia de V1 sobre un arbol de caso real en disco, sin PII y sin OCR.

Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md, Task 10.
Criterio 14 del §14 de la spec: punto fijo — correrla dos veces no cambia nada.
"""
import json

import pytest

from core import apertura_v1 as av1
from scripts import abrir_caso as cli


@pytest.fixture()
def caso(tmp_path):
    d = tmp_path / "BaXX1 - Prueba (W-000000) - NEGATIVA_OFERTA"
    (d / "00_Input").mkdir(parents=True)
    (d / "00_Input" / "_caso.md").write_text(
        "---\ncase_id: BaXX1 - Prueba (W-000000) - NEGATIVA_OFERTA\n"
        "id_go: W-000000\ntipo_caso: NEGATIVA_OFERTA\nciudad: Barcelona\n"
        "sudespacho_expedientes:\n"
        "  - id: '648'\n    element: extrajudiciales\n    input_dir: sudespacho_648\n---\n",
        encoding="utf-8")
    return d


class _Ident:
    case_id = "BaXX1 - Prueba (W-000000) - NEGATIVA_OFERTA"
    w_code = "W-000000"


def test_e2e_la_secuencia_recorre_las_tres_etapas_y_deja_el_evento(caso, monkeypatch):
    from core.intake_drive import DriveIntakeResult

    monkeypatch.setattr(cli.intake_drive, "pull_drive_ev",
                        lambda *a, **k: DriveIntakeResult(
                            case_id="C", team_id="T", folder_id="F",
                            target_dir=caso / "00_Input" / "01_Drive EV",
                            files_after=2, skipped=False))
    from core import sync_sudespacho
    monkeypatch.setattr(sync_sudespacho, "pull_expediente_v2",
                        lambda *a, **k: object())
    monkeypatch.setattr(cli, "etapa_sala_maquina",
                        lambda ident, **k: av1.EtapaResultado(
                            nombre="sala_maquina", estado="hecha", detalle="OCR simulado"))

    r = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")

    assert [e.nombre for e in r.etapas] == ["drive", "crm", "sala_maquina"]
    assert r.estado == av1.EstadoV1.PREPARADO_CON_PENDIENTES

    cli.registrar_cierre_v1(caso, _Ident(), r)
    log = caso / "00_Input" / "_intake_log.jsonl"
    ev = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l][-1]
    assert ev["event"] == "apertura_v1_terminada"
    assert ev["details"]["estado"] == "preparado_con_pendientes"


def test_e2e_es_punto_fijo_la_segunda_corrida_no_cambia_el_estado(caso, monkeypatch):
    """Criterio 14. La segunda corrida reporta `saltada` en Drive —el `.pulled` ya
    esta— y el ESTADO no cambia. Eso es lo que hace que reanudar sea volver a lanzar
    la misma orden."""
    from core.intake_drive import DriveIntakeResult

    corridas = {"n": 0}

    def _pull(*a, **k):
        corridas["n"] += 1
        return DriveIntakeResult(
            case_id="C", team_id="T", folder_id="F",
            target_dir=caso / "00_Input" / "01_Drive EV",
            files_after=2, skipped=corridas["n"] > 1)

    monkeypatch.setattr(cli.intake_drive, "pull_drive_ev", _pull)
    from core import sync_sudespacho
    monkeypatch.setattr(sync_sudespacho, "pull_expediente_v2", lambda *a, **k: object())
    monkeypatch.setattr(cli, "etapa_sala_maquina",
                        lambda ident, **k: av1.EtapaResultado(
                            nombre="sala_maquina", estado="hecha", detalle="OCR simulado"))

    primera = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")
    segunda = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")

    assert primera.estado == segunda.estado
    assert primera.etapas[0].estado == "hecha"
    assert segunda.etapas[0].estado == "saltada"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_e2e.py -q`
Expected: FAIL mientras falte cualquier pieza de las Tasks 1-8.

- [ ] **Step 3: No implementation needed**

Si las Tasks 1-8 están hechas, este test debe pasar sin código nuevo. Si no pasa, el defecto está en
ellas y se corrige ahí, no aquí.

- [ ] **Step 4: Run the whole suite with two seeds**

```bash
python -m pytest -q --tb=short -p randomly --randomly-seed=777 --junit-xml=.pytest-777.xml
```

```bash
python -m pytest -q --tb=short -p randomly --randomly-seed=31337 --junit-xml=.pytest-31337.xml
```

Expected: 0 fallos con ambas. **El conteo se lee del `--junit-xml`, no del resumen por tubería.**
Una variación del conteo respecto al último cierre que no esté explicada es bandera roja.

- [ ] **Step 5: Commit**

```bash
git add tests/test_apertura_v1_e2e.py && git commit -m "test(v1): E2E de la secuencia, con punto fijo"
```

---

## Task 11: La corrida real sobre W-02Q38C

**Files:**
- Modify: `PLAN.md` (fila #15), `docs/bitacora/2026.md`

**Contexto:** el bloque 5 del §21.5 pide, además del E2E, «una apertura real controlada con
`--crm skip`». Nikolai eligió W-02Q38C el 2026-09-03. Esta task **no es un test**: es un
procedimiento con verificación, y su producto es la evidencia.

- [ ] **Step 1: Antes de tocar nada, fotografiar el estado**

```bash
python -m scripts.sync_sudespacho check-legacy
```

Si falla, renovar `PHPSESSID` antes de seguir (`/renovar-php`). Anotar el sha256 del árbol del caso
antes de la corrida, para poder decir después qué cambió.

- [ ] **Step 2: Correr en seco hasta la primera etapa**

```bash
python -m scripts.abrir_caso --modo v1 --crm skip --fuente drive_ev --case-id "<case_id de W-02Q38C>" --folder-id "<folder id>" --hasta drive
```

Expected: la etapa `drive` reporta `saltada` (el caso ya está abierto, `.pulled` presente) y la
secuencia para. **Verificar por resultado, no por status:** listar el destino y comprobar que el
número de ficheros no cambió.

- [ ] **Step 3: La corrida completa**

```bash
python -m scripts.abrir_caso --modo v1 --crm skip --fuente drive_ev --case-id "<case_id de W-02Q38C>" --folder-id "<folder id>"
```

Expected: las tres etapas en el informe, estado `preparado_con_pendientes`, y el evento
`apertura_v1_terminada` en `00_Input/_intake_log.jsonl`.

- [ ] **Step 4: Verificar el punto fijo sobre el caso real**

Repetir el comando del Step 3. Expected: mismo estado, `drive` en `saltada`, y la sala de máquina
sin documentos nuevos (su estado por sha los salta).

- [ ] **Step 5: Cerrar el registro**

Marcar en `PLAN.md` fila #15 el Plan 5 como ejecutado con el hash del PR, retirar de la sección
`[SIGUIENTE-APERTURA-INTEGRAL]` el punto (5) y el (6) —W-02Q38C se cierra por este wiring—, y dejar
en la bitácora el bloque de cierre con el conteo de la suite medido, no recordado.

```bash
git add PLAN.md docs/bitacora/2026.md && git commit -m "docs(v1): Plan 5 ejecutado; W-02Q38C cerrado por el cableado"
```

---

## §4. Self-review de este plan

**Cobertura del alcance aprobado.** Las cinco etapas de V1 (identidad, esqueleto, Drive, CRM,
atomización + sala de máquina) están cubiertas: identidad y esqueleto ya los hace `main` antes del
bloque bajo mutex y no se tocan; las tres restantes son las Tasks 3, 4 y 6. El flag `--hasta` es la
Task 8. Las tres salidas de D4, la Task 1 y la 6. El evento durable, la Task 7. El E2E, la 10. La
corrida real sobre W-02Q38C, la 11.

**Lo que este plan deja SIN cubrir, con nombre:**

- **`--hasta` no admite parar dentro de la sala de máquina** (entre la atomización y el OCR). La
  atomización vive dentro de `apply` y separarla es trabajo de otra pieza. Declarado, no oculto.
- **Los cuatro defectos vivos que rodean este camino no se arreglan aquí:** `MEJORAS #137`, `#138`,
  `#139` y `#141`. Ninguno bloquea la secuencia; `#141` (`buscar()` no valida el `case_id`) es el
  que más cerca pasa, porque la secuencia resuelve el caso por `--case-id`.
- **Las cuatro deudas del §0.** Siguen exactamente como se aprobaron.

**Consistencia de tipos.** `EtapaResultado` se construye en las Tasks 3, 4 y 6 siempre con los
mismos nombres de campo (`nombre`, `estado`, `detalle`, `pendientes`); `Pendiente` siempre con
(`codigo`, `detalle`); `secuenciar` recibe `Sequence[Etapa]` y devuelve `ResultadoV1` en las Tasks
2, 8 y 10. `apply` devuelve `str | None` en la Task 5 y lo consume la 6.

**Sin marcadores de posición.** No hay «TBD», «pendiente de detallar» ni pasos sin código.

---

## 5. Adjudicación de la revisión adversarial (Codex, 2026-09-03) — NO-EJECUTABLE, pendiente

- **Objeto revisado:** diseño del Plan 5 — el cableado de la secuencia de V1 y el E2E (rev. 1), commit `a95326e`
- **Ronda:** A
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-03-apertura-v1-plan5-rA-adversarial-review.md`
- **Hallazgos:** 12 recibidos — 12 confirmados, 0 refutados (4 CRÍTICOS + 1 elevado por el adjudicador, 5 ALTOS, 1 MEDIO, 1 BAJO)
- **Remediado en:** pendiente — la rev. 2 de este plan

**La ronda EJECUTÓ, y ahí está su valor.** Los cuatro críticos no se deducen leyendo: salieron de
correr los adaptadores propuestos con dobles, de aplicar las piezas al trinquete del censo, de
pasar la fixture del E2E por el lector real de metadatos y de reproducir una pérdida de mutex bajo
un `typer.Exit(0)`. Un revisor que solo hubiera leído habría devuelto tres o cuatro medios.

**El hallazgo de fondo, y es sobre la premisa, no sobre el detalle.** Dos de las cuatro deudas que
el §0 declaraba «aceptadas» no son deudas: son **contradicciones literales de la tabla de riesgos
de la spec**, que ya había nombrado los dos mecanismos con su mitigación obligatoria. La spec dice,
palabra por palabra, «`.pulled` evita volver a Drive → Falso punto fijo → Consulta remota real en
cada ronda; caché o skip no cuentan como "sin novedad"» y «Reanudación sin generación común → Fase
verde sobre inputs obsoletos → `estado.json` atómico obligatorio desde la primera entrega». Yo
construí sobre esos dos mecanismos el argumento de que la reanudación «no cuesta diseño nuevo», y
**se lo presenté a Nikolai como razón para preferir la ejecución desatendida**. La premisa era
falsa y la decisión se tomó sobre ella.

**Por qué no lo vi, que es lo que hay que llevarse.** Leí el §21 y el §24 de la spec —el alcance y
las decisiones— y no leí su **tabla de riesgos**, que es donde vivía la respuesta a la pregunta que
me estaba haciendo. Busqué el dato en el sitio donde se declara la intención, no en el sitio donde
se declara lo que puede salir mal. Es la misma clase que ya tengo medida cuatro veces: **el dato de
alcance se busca en el registro del nivel de su alcance**, y «qué mecanismo es un falso punto fijo»
es un riesgo, no un criterio.

**Y tres de los críticos son la misma forma:** mis tres adaptadores **rodeaban** costuras que ya
existían y que rondas anteriores habían construido a propósito. `etapa_drive` se saltaba la custodia
que R14/H14-02 y R15/H15-06 pusieron en `_intake_drive_ev`; `etapa_crm` marcaba `hecha` leyendo la
ausencia de excepción en vez del resultado, contra una regla que `CLAUDE.md` tiene escrita
—«verificar por resultado, nunca por status»—; y `etapa_sala_maquina` salía con `typer.Exit(0)`
**dentro** del bloque de mutex, convirtiendo en una nota la pérdida ruidosa que R12/H12-04 había
construido. Escribir un adaptador nuevo por encima de una costura vieja es la manera silenciosa de
derogarla.

### Adjudicación hallazgo por hallazgo

| Id | Sev. | Veredicto | Contrastado contra |
|---|---|---|---|
| HA-01 | CRÍTICO | **CONFIRMADO** | spec §11: `estado.json` atómico «obligatorio desde la primera entrega» |
| HA-02 | CRÍTICO | **CONFIRMADO** | `scripts/abrir_caso.py:136-175`: hashes, `_intake_generico` y registro de parciales, los tres rodeados |
| HA-03 | ALTO → **CRÍTICO** | **CONFIRMADO y elevado** | spec §11: «`.pulled` … Falso punto fijo … caché o skip no cuentan» |
| HA-04 | CRÍTICO | **CONFIRMADO** | `core/sync_sudespacho.py:1306-1318` + `CLAUDE.md` §14.6 |
| HA-05 | ALTO | **CONFIRMADO** | el criterio 38 pide los dos cruces y preflight de referencia; F7/F8 solo cierran la herencia del default |
| HA-06 | ALTO | **CONFIRMADO** | `--hasta` se valida dentro de `secuenciar`, después de identidad, mutex y `ensure_case` |
| HA-07 | CRÍTICO | **CONFIRMADO** | `core/casos/case_mutex.py:615-659`: con excepción en vuelo, la pérdida solo se anota |
| HA-08 | ALTO | **CONFIRMADO**, escenario corregido | no es «borra derivados»: es que una corrida **parcial** poda contra un `esperados` incompleto |
| HA-09 | ALTO | **CONFIRMADO** | F12 muta solo el texto de `detalle` y su test no lo afirma: sobrevive. Y `_correr` no puede medir su propia regla |
| HA-10 | ALTO | **CONFIRMADO** | `core/casos/case_locator.py:222`: `read_case_meta` devuelve `fm.get("meta")`; la fixture daba `{}` |
| HA-11 | MEDIO | **CONFIRMADO** | el evento nuevo sube el censo a 84/83, y el test vigente de V1 dobla una costura que el plan retira |
| HA-12 | BAJO | **CONFIRMADO** | `len(INTAKE_EVENTS)` = 33; `git grep -o` da 53 en 19 ficheros, no 103 |

**Sobre HA-12, una precisión que no exculpa.** La cifra «103 referencias» **no es mía: es del §24
D3 de la spec**, donde sostiene la decisión de usar un modo en vez de un subcomando. La copié a las
restricciones globales sin medirla. La decisión no cambia —53 referencias siguen siendo demasiadas
para romper la forma del CLI—, pero **la spec lleva una cifra no reproducible en un sitio portante**
y eso hay que corregirlo donde vive.

**Lo que R-A dejó SIN VERIFICAR, y por tanto sin cubrir:** la corrida real sobre W-02Q38C, el acceso
a Drive y a Sudespacho, la suite completa con las dos semillas —el intérprete del revisor no tiene
`pytest-randomly`— y el aislamiento dinámico de los trece mutantes distintos de F12. Nada de eso
está refutado: está sin mirar, y así se declara.

### Lo que tiene que traer la rev. 2

**Nueve defectos son mecánicos y se arreglan sin tocar el alcance:** HA-02 (adaptar
`_intake_drive_ev`, no rodearlo), HA-04 (tabla completa de traducción de `PullResultV2`, con el
vacío confirmado distinguido del error), HA-05 (los dos cruces del criterio 38 con pruebas
separadas y vocabulario cerrado), HA-06 (validar `--hasta` en la puerta previa a todo efecto, y no
emitir terminación en una parada pedida), HA-07 (salir **fuera** del bloque de mutex, y capturar
`CaseBusy`/`MutexPerdido` en la frontera), HA-09 (mutante F12 que introduzca de verdad el pendiente,
y arnés que compare el conjunto exacto de rojos), HA-10 (fixture con el esquema real y espías),
HA-11 (el evento nuevo por la costura, sin subir el censo; y migrar el test vigente), HA-12
(corregir 33→34 y retirar o medir la cifra de referencias).

**Dos no son mecánicos y cambian el plan:**

- **HA-03 tiene arreglo barato y hay que tomarlo:** la etapa de Drive **consulta en cada ronda** en
  vez de apoyarse en `.pulled`. `rclone` transfiere solo lo que difiere, así que el coste es una
  consulta remota real, no una re-descarga. Eso cumple la mitigación que la spec exige sin
  construir el espejo versionado entero.
- **HA-01 obliga a elegir, y la elección es de Nikolai porque es alcance y coste:** o el plan
  incorpora un `estado.json` mínimo por ronda —que es lo que la spec llama obligatorio desde la
  primera entrega— o deja de llamarse V1 y de prometer que cierra W-02Q38C. Lo que no cabe es
  seguir prometiendo V1 sin ello.

**No se pide una tercera ronda sobre la rev. 1.** El techo duro la prohíbe sin autorización expresa,
y además no haría falta: lo que falta no es más ataque sobre este documento, es un documento
distinto.
