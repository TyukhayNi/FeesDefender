---
tipo: plan
objeto: "Apertura V1 — Plan 5: el cableado de la secuencia y el E2E"
estado_remediacion: remediado
creado: 2026-09-03
---

# Apertura V1 — Plan 5: el cableado de la secuencia y el E2E (rev. 2)

> ## ⚠ ESTADO: rev. 2 ejecutada; **TRES rondas adjudicadas** (R-A plan, R-B sustituto, R-C
> Codex). Remediada en parte; **cuatro bloques abiertos** y NO se mergea sin decisión de
> Nikolai sobre HC-04 y HC-06 (ver §7).
>
> **R-A (diseño) devolvió `NO-EJECUTABLE` sobre la rev. 1: 12 hallazgos, 11 confirmados y 1
> parcialmente refutado**, 4 críticos y uno más elevado a crítico por el adjudicador. Acta:
> `docs/superpowers/specs/2026-09-03-apertura-v1-plan5-rA-adversarial-review.md`; adjudicación
> completa en el §5, que **se conserva** — es el registro de qué se decidió y por qué.
>
> **Los dos cambios de fondo de esta rev. 2, decididos con Nikolai el 2026-09-03:**
>
> 1. **La etapa de Drive consulta en cada ronda** (`force=True`), en vez de apoyar el punto fijo
>    en el marcador `.pulled`. La tabla de riesgos de la spec llama a eso, literal, «falso punto
>    fijo». `rclone` transfiere solo lo que difiere, así que el coste es una consulta real, no una
>    re-descarga.
> 2. **Entra el `estado.json` por ronda** que la spec exige «desde la primera entrega» (Task 8b).
>    Sin él, «reanudar tras un corte» era una afirmación mía, no una propiedad.
>
> **Y las tres etapas dejan de rodear costuras que ya existían:** Drive pasa por
> `_intake_drive_ev` (hashes, reconciliación, registro de parciales), el CRM se lee **por
> resultado y no por ausencia de excepción**, y la salida ocurre **fuera** del bloque de mutex.

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
- **`--modo libre` no cambia de comportamiento.** `git grep -o "scripts\.abrir_caso" | wc -l`
  da **53 apariciones en 19 ficheros** (medido el 2026-09-03); cualquier regresión del modo por
  defecto es un fallo del plan. *(La spec §24 D3 dice «103 referencias» y esa cifra **no es
  reproducible**: la rev. 1 la copió sin medirla. La decisión que sostiene no cambia, pero la
  cifra hay que corregirla donde vive — anotado como fleco para la spec.)*
- **Verificar por resultado, nunca por status.** Regla de `CLAUDE.md` para el CRM. Ninguna etapa
  puede concluir «hecha» por el hecho de que una llamada no lanzara excepción.
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

**Las deudas que quedan, después de que R-A tumbara dos de las cuatro de la rev. 1:**

| # | Deuda | Consecuencia exacta | Por qué se acepta |
|---|---|---|---|
| 1 | **3B aplazado** | Los derivados de la sala de máquina se siguen escribiendo fuera de la costura. `TECHO_CENSO` sigue en **83** (`tests/test_escritura_censo.py:75`) y el trinquete impide que suba — el evento nuevo de la Task 7 pasa por la costura justamente para no subirlo | El censo es un tope que solo baja; la deuda queda contada, no oculta |
| 2 | **3C aplazado** | La poda sigue borrando en vez de archivar, contra D4. **R-A lo señaló y la adjudicación lo acotó:** el `unlink` de `mensajes/` está **gateado en foto completa** (`core/email_atomize/pipeline.py:204-220`), así que solo sobreviven las podas de `vistas/*.md` y `*.contenido.md` | Lo perdible son derivados regenerables desde `corpus.jsonl` y desde el crudo, **nunca material de cliente**. Radio pequeño y medido, no supuesto |
| 3 | **Espejo versionado de Drive aplazado** (historial content-addressed, generaciones, tombstones) | Si Drive **reemplaza** un fichero, se pierde la versión procesada anterior | Lo que la rev. 1 aplazaba de este bloque y **ya no se aplaza** es lo importante: la consulta remota por ronda (Task 3) y el `estado.json` (Task 8b). Lo que queda es el historial de versiones, cuyo disparador —E&V sustituyendo un fichero en sitio— no se ha observado |
| 4 | **3A-bis aplazado** | Si el guard desvía el pull a la bandeja, el sello de los ids de Drive no se estampa en la ficha canónica: queda aplazado **con aviso en pantalla** | Es D5, ya autorizada por Nikolai el 2026-08-26 |

**Y las dos que la rev. 1 declaraba y R-A demostró que no eran deudas sino contradicciones
literales de la spec** (§11, tabla de riesgos): «`.pulled` evita volver a Drive → **falso punto
fijo** → consulta remota real en cada ronda; caché o skip no cuentan como "sin novedad"» y
«reanudación sin generación común → fase verde sobre inputs obsoletos → `estado.json` atómico
**obligatorio desde la primera entrega**». Las dos entran en esta rev. 2 y dejan de ser deuda.

**Presupuesto de revisión: DOS rondas.** La secuencia sostiene el mutex durante toda su duración,
y eso decide quién puede escribir sobre esa copia mientras corre: entra en la categoría de dos del
presupuesto de `CLAUDE.md`. **R-A sobre este plan, antes de escribir una línea de código; R-B sobre
el diff.** Techo duro: no hay tercera sin autorización expresa de Nikolai.

**Validación real: W-02Q38C**, el piloto ya abierto (decisión de Nikolai el 2026-09-03). Es el caso
que disparó el ítem y sigue declarado abierto porque su `_caso.md` no se sincroniza por el camino
común; correr la secuencia sobre él lo cierra **por el cableado y no por parche manual**.

**Lo que este plan NO construye, dicho para que nadie lo dé por hecho:** el alta CRM (V2),
`crm_ficha` (V2), el descubrimiento de correo en Gmail (V3), la sala de **lectura** (V3), la
viabilidad (V3), y el historial content-addressed de Drive con sus tombstones. **Sí** construye el
`estado.json` por ronda, porque la spec lo hace obligatorio desde la primera entrega y sin él la
reanudación es una afirmación y no una propiedad.

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

## §3. Las veintiocho fronteras que este plan contrata

Una por mutante. Si el arnés de mutación no las mata todas, el plan no está cumplido.

| # | Frontera | Mutante que la mata |
|---|---|---|
| F1 | Un `fallo` de etapa **detiene** la secuencia: las posteriores no corren | quitar el `break` tras `fallo` |
| F2 | El estado final es `bloqueado` si hubo `fallo` | devolver `preparado_con_pendientes` con `fallo` presente |
| F3 | **V1 nunca es `completo`**: el pendiente permanente de fuentes V3 siempre está en la lista | quitar `PENDIENTE_FUENTES_V3` de la lista inicial |
| F4 | `--hasta <etapa>` para **después** de esa etapa, no antes | parar antes |
| F5 | `--hasta` con nombre desconocido es error, no «no parar nunca» | ignorar el nombre desconocido |
| F6 | En V1 la etapa de Drive **exige** que la consulta remota se haya hecho: un `skipped=True` es `fallo`, no `saltada` | mapear `skipped=True` a `saltada` |
| F7 | El `element` del pull CRM sale del `ExpedienteLink`, **nunca** del default | omitir el kwarg `element=` |
| F8 | Un `ExpedienteLink` **sin** `element` es `fallo`, no una adivinanza | rellenar con `"expedientes_judiciales"` |
| F9 | Un caso **sin** `ExpedienteLink` es `saltada` con pendiente, no `fallo` | mapearlo a `fallo` |
| F10 | Atomización `parcial` → etapa `hecha` **con pendiente** | mapearla a `hecha` sin pendiente |
| F11 | Atomización `fallo` → etapa `fallo` | mapearla a `hecha` |
| F12 | Atomización no ejecutada (`None`, sin correo) **no** deja pendiente | añadirle un pendiente |
| F13 | El evento final se emite con el estado real, y su nombre está en `INTAKE_EVENTS` | emitir un nombre fuera del set |
| F14 | Estado `bloqueado` → código de salida distinto de 0 | salir 0 siempre |
| **F15** | La etapa de Drive pasa por `_intake_drive_ev`, que hashea, reconcilia y registra parciales — **no** por `pull_drive_ev` a pelo | llamar directamente a `pull_drive_ev` |
| **F16** | En V1 el pull se pide con `force=True`: **consulta remota real en cada ronda** | pasar `force=False` |
| **F17** | `PullResultV2.errors` no vacío → `fallo`, aunque no se lanzara excepción | ignorar `errors` |
| **F18** | `blocked_legacy_v1` → `fallo` | ignorar el flag |
| **F19** | `documents_failed > 0` → `hecha` **con pendiente**, no `hecha` a secas | ignorar el contador |
| **F20** | Gestor documental **vacío confirmado** (0 docs, 0 errores) → `saltada`, distinguible del error | mapearlo a `fallo` |
| **F21** | El `element` pertenece al vocabulario cerrado `{"extrajudiciales", "expedientes_judiciales"}` | aceptar cualquier cadena |
| **F22** | En V1 un `element` judicial **aborta**: la rama judicial sigue bloqueada (criterio 38, cruce inverso) | aceptar el judicial |
| **F23** | El vocabulario de `--hasta` se valida en `validar_modo`, **antes de todo efecto** | validarlo solo dentro de `secuenciar` |
| **F24** | Una parada pedida **enumera como pendientes** las etapas que no corrieron | no enumerarlas |
| **F25** | La salida del proceso ocurre **fuera** del bloque de mutex | lanzar `typer.Exit` dentro del `with` |
| **F26** | `CaseBusy` y `MutexPerdido` en la frontera → estado `bloqueado` y salida no cero | dejarlos propagar como traza |
| **F27** | `estado.json` se escribe **atómicamente** y con id de ronda | escribir en sitio, sin `os.replace` |
| **F28** | Una ronda anterior **sin cerrar** se detecta y se dice en el informe | ignorar el estado previo |

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

## Task 3: El adaptador del pull de Drive E&V, por la custodia y consultando cada ronda

**Files:**
- Modify: `scripts/abrir_caso.py:136-175` (`_intake_drive_ev`) y adaptador nuevo
- Test: `tests/test_apertura_v1_etapas.py`

**Interfaces:**
- Consumes: `core.apertura_v1.EtapaResultado`, `core.intake_drive.DriveIntakeResult`.
- Produces: `_intake_drive_ev(..., *, force: bool = False) -> DriveIntakeResult` (antes devolvía
  `None`) y `etapa_drive(ident, case_dir, *, folder_id, team_id, intake=None) -> EtapaResultado`.

**Contexto — los dos hallazgos que esta task remedia, y por qué eran críticos.**

**HA-02.** La rev. 1 llamaba a `pull_drive_ev` directamente. Eso **rodea** `_intake_drive_ev`
(`scripts/abrir_caso.py:136-175`), que hace tres cosas que no son opcionales: `hash_tree_local`
sobre el **destino efectivo** —la corrección de R14/H14-02—, `_intake_generico` (reconciliación,
manifiesto y evento), y ante un `DriveIntakeError` el registro de los bytes **parciales** con
`status: fallo` antes de relanzar —la corrección de R15/H15-06—. Escribir un adaptador por encima
de una costura es la manera silenciosa de derogarla. Así que el adaptador **usa** esa función; lo
único que cambia en ella es que devuelva su resultado en vez de tirarlo.

**HA-03.** La tabla de riesgos de la spec dice, literal: «`.pulled` evita volver a Drive → **falso
punto fijo** → consulta remota real en cada ronda; caché o skip no cuentan como "sin novedad"».
La rev. 1 apoyaba su punto fijo exactamente en ese skip. En V1 el pull va con **`force=True`**:
`rclone` transfiere solo lo que difiere, así que se paga una consulta remota, no una re-descarga.
Y entonces `skipped=True` deja de ser un estado normal: si aparece, la consulta **no** se hizo y
eso es un `fallo`, no un `saltada`.

- [ ] **Step 1: Write the failing test**

```python
"""Los adaptadores de las etapas de V1: traducen una llamada real a `EtapaResultado`.

Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md §3.
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


def test_f15_la_etapa_pasa_por_la_custodia_y_no_por_el_pull_a_pelo():
    """F15. `_intake_drive_ev` hashea el destino efectivo, reconcilia y registra los bytes
    parciales de un pull fallido. Llamar a `pull_drive_ev` directamente deroga las tres."""
    visto = {}

    def intake(ident, case_dir, folder_id, team_id, *, dry_run, force):
        visto.update(folder_id=folder_id, team_id=team_id, force=force)
        return _drive_result()

    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T", intake=intake)
    assert r.estado == "hecha"
    assert visto["folder_id"] == "F"


def test_f16_en_v1_el_pull_consulta_en_cada_ronda():
    """F16. La spec llama al skip por `.pulled` «falso punto fijo»."""
    visto = {}

    def intake(ident, case_dir, folder_id, team_id, *, dry_run, force):
        visto["force"] = force
        return _drive_result()

    cli.etapa_drive(None, Path("."), folder_id="F", team_id="T", intake=intake)
    assert visto["force"] is True


def test_f6_un_skipped_en_v1_es_fallo_porque_la_consulta_no_se_hizo():
    """F6, reformulada por HA-03. Con `force=True`, `skipped` no puede ser True; si lo es,
    alguien devolvió el marcador al camino y la ronda no consultó Drive."""
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T",
                        intake=lambda *a, **k: _drive_result(skipped=True))
    assert r.estado == "fallo"
    assert "consulta remota" in r.detalle


def test_drive_con_errores_es_fallo():
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T",
                        intake=lambda *a, **k: _drive_result(errors=["rclone: exit 3"]))
    assert r.estado == "fallo"
    assert "exit 3" in r.detalle


def test_drive_que_revienta_es_fallo_y_no_propaga():
    def explota(*a, **k):
        raise RuntimeError("token caducado")
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T", intake=explota)
    assert r.estado == "fallo"
    assert "token caducado" in r.detalle
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_etapas.py -q`
Expected: FAIL con `AttributeError: module 'scripts.abrir_caso' has no attribute 'etapa_drive'`

- [ ] **Step 3: Write minimal implementation**

Primero, que `_intake_drive_ev` devuelva su resultado y acepte `force`. En
`scripts/abrir_caso.py:136`, la firma y las dos últimas líneas:

```python
def _intake_drive_ev(ident, case_dir: Path, folder_id, team_id, *,
                     dry_run: bool, force: bool = False) -> intake_drive.DriveIntakeResult:
```

```python
    try:
        res = intake_drive.pull_drive_ev(ident.case_id, folder_id, team_id, force=force)
```

y al final del cuerpo, tras `_intake_generico(...)`:

```python
    return res
```

Después, el adaptador (añadir `from core import apertura_v1 as av1` a los imports de `core`):

```python
def etapa_drive(ident, case_dir: Path, *, folder_id, team_id, intake=None):
    """Etapa 1 de V1: materializar la carpeta de Drive E&V, con custodia.

    **Pasa por `_intake_drive_ev` y no por `pull_drive_ev`**: la custodia —hashes sobre el
    destino efectivo, reconciliacion, y registro de los bytes parciales de un pull fallido—
    vive ahi, y es el resultado de R14/H14-02 y R15/H15-06. Un adaptador que la rodea la
    deroga en silencio.

    **`force=True` siempre.** La spec llama al skip por `.pulled` «falso punto fijo»: en V1
    la consulta remota se hace en cada ronda, y `rclone` transfiere solo lo que difiere.
    """
    _intake = intake or _intake_drive_ev
    try:
        res = _intake(ident, case_dir, folder_id, team_id, dry_run=False, force=True)
    except Exception as exc:  # noqa: BLE001 — el estado de V1 es el producto, no la traza
        return av1.EtapaResultado(nombre="drive", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")
    if res.errors or res.rclone_returncode != 0:
        return av1.EtapaResultado(
            nombre="drive", estado="fallo",
            detalle=f"rclone rc={res.rclone_returncode}; errores={res.errors}")
    if res.skipped:
        # Con `force=True` esto no deberia poder pasar. Si pasa, el marcador `.pulled`
        # volvio al camino y la ronda NO consulto Drive: decirlo `saltada` seria firmar
        # el falso punto fijo que la spec prohibe.
        return av1.EtapaResultado(
            nombre="drive", estado="fallo",
            detalle="la consulta remota no se hizo: el pull devolvio `skipped` pese a "
                    "pedirse con force=True")
    return av1.EtapaResultado(
        nombre="drive", estado="hecha",
        detalle=f"{res.files_after} ficheros en {res.target_dir}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_apertura_v1_etapas.py tests/test_abrir_caso_cli.py -q`
Expected: PASS. `test_abrir_caso_cli.py` entra porque `_intake_drive_ev` cambió de firma: el
`force` lleva default para no regresar a sus llamadores del modo `libre`.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_apertura_v1_etapas.py
git commit -m "feat(v1): etapa de Drive por la custodia y con consulta remota en cada ronda"
```

---

## Task 4: El adaptador del pull del CRM — por resultado, y con la rama cerrada

**Files:**
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_apertura_v1_etapas.py`

**Interfaces:**
- Produces: `ELEMENTS_CRM: frozenset[str]`, `traducir_pull_crm(res) -> tuple[str, str, tuple]`,
  y `etapa_crm(ident, case_dir, *, leer_meta=None, pull=None) -> EtapaResultado`.

**Contexto — dos hallazgos, y el primero incumple una regla escrita en `CLAUDE.md`.**

**HA-04 (CRÍTICO).** La rev. 1 marcaba `hecha` toda llamada que no lanzara. Pero
`pull_expediente_v2` **comunica por retorno**: `blocked_legacy_v1`, `documents_failed`, `errors`
(`core/sync_sudespacho.py:1306-1318`). El revisor lo ejecutó con `errors=['list_gdocu_docs_rest:
500']` y obtuvo `crm_estado_con_errors= hecha`; después de eso, la sala de máquina corría sobre un
CRM ausente y V1 salía 0. Y `CLAUDE.md` §14.6 tiene la regla escrita: **«verificar por resultado,
nunca por status»**. Por eso la traducción es una función aparte y con su tabla: para que se pueda
mutar rama por rama.

**HA-05 (ALTO).** El criterio 38 pide los **dos** cruces y no solo el default. La rev. 1 exigía que
`element` fuese no vacío y luego confiaba en él: admitía un literal desconocido y un link judicial
en un caso extrajudicial. En V1 se cierra entero: vocabulario cerrado, y **la rama judicial aborta**
—sigue bloqueada hasta que exista adaptador judicial verificado, que es lo que la spec dice—.
`_ELEMENT_EXTRAJUDICIAL` ya existe en este mismo fichero (`scripts/abrir_caso.py:46`) y el alta lo
usa, así que la regla no inventa vocabulario: lo reutiliza.

- [ ] **Step 1: Write the failing test**

```python
class _IdentFalsa:
    def __init__(self, case_id="C"):
        self.case_id = case_id
        self.w_code = "W-000000"


def _meta(element="extrajudiciales", **extra):
    link = {"id": "648", "input_dir": "sudespacho_648"}
    if element is not None:
        link["element"] = element
    link.update(extra)
    return {"sudespacho_expedientes": [link]}


class _Res:
    def __init__(self, **kw):
        self.blocked_legacy_v1 = kw.get("blocked_legacy_v1", False)
        self.documents_total_crm = kw.get("documents_total_crm", 5)
        self.documents_written = kw.get("documents_written", 5)
        self.documents_failed = kw.get("documents_failed", 0)
        self.errors = kw.get("errors", [])


def test_f7_el_element_sale_del_link_y_nunca_del_default():
    """F7. El default de `pull_expediente_v2` es JUDICIAL (`core/sync_sudespacho.py:1356`)."""
    visto = {}

    def pull(case_id, expediente_id, *, element):
        visto.update(expediente_id=expediente_id, element=element)
        return _Res()

    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: _meta(), pull=pull)
    assert r.estado == "hecha"
    assert visto == {"expediente_id": "648", "element": "extrajudiciales"}


def test_f8_un_link_sin_element_es_fallo_y_no_se_adivina():
    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: _meta(element=None),
                      pull=lambda *a, **k: pytest.fail("no debe pullar sin rama"))
    assert r.estado == "fallo"
    assert "element" in r.detalle


def test_f21_un_element_fuera_del_vocabulario_es_fallo():
    """F21. Aceptar cualquier cadena deja pasar un typo hasta la API."""
    r = cli.etapa_crm(_IdentFalsa(), Path("."),
                      leer_meta=lambda _d: _meta(element="extrajudicial"),
                      pull=lambda *a, **k: pytest.fail("no debe pullar"))
    assert r.estado == "fallo"
    assert "extrajudicial" in r.detalle


def test_f22_un_element_judicial_aborta_en_v1():
    """F22. El cruce INVERSO del criterio 38, que es el peligroso: la rama judicial sigue
    bloqueada hasta que exista adaptador verificado."""
    r = cli.etapa_crm(_IdentFalsa(), Path("."),
                      leer_meta=lambda _d: _meta(element="expedientes_judiciales"),
                      pull=lambda *a, **k: pytest.fail("no debe pullar la rama judicial"))
    assert r.estado == "fallo"
    assert "judicial" in r.detalle


def test_f9_un_caso_sin_expediente_registrado_es_saltada_con_pendiente():
    r = cli.etapa_crm(_IdentFalsa(), Path("."),
                      leer_meta=lambda _d: {"sudespacho_expedientes": []},
                      pull=lambda *a, **k: pytest.fail("no debe pullar"))
    assert r.estado == "saltada"
    assert [p.codigo for p in r.pendientes] == ["crm_sin_expediente"]


@pytest.mark.parametrize("kw,estado,codigo", [
    ({"errors": ["list_gdocu_docs_rest: 500"]}, "fallo", None),          # F17
    ({"blocked_legacy_v1": True}, "fallo", None),                        # F18
    ({"documents_failed": 2}, "hecha", "crm_documentos_fallidos"),       # F19
    ({"documents_total_crm": 0, "documents_written": 0}, "saltada", "crm_gestor_vacio"),  # F20
    ({}, "hecha", None),
])
def test_f17_f20_el_resultado_del_pull_gobierna_la_etapa(kw, estado, codigo):
    """HA-04. `pull_expediente_v2` NO lanza: lo dice todo por retorno. Leer solo la
    ausencia de excepcion es incumplir «verificar por resultado, nunca por status»."""
    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: _meta(),
                      pull=lambda *a, **k: _Res(**kw))
    assert r.estado == estado
    assert [p.codigo for p in r.pendientes] == ([codigo] if codigo else [])


def test_crm_que_revienta_es_fallo():
    def explota(*a, **k):
        raise RuntimeError("PHPSESSID caducada")
    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: _meta(), pull=explota)
    assert r.estado == "fallo"
    assert "PHPSESSID" in r.detalle
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_etapas.py -q`
Expected: FAIL con `AttributeError: module 'scripts.abrir_caso' has no attribute 'etapa_crm'`

- [ ] **Step 3: Write minimal implementation**

```python
#: Vocabulario cerrado de ramas del CRM. `_ELEMENT_EXTRAJUDICIAL` ya existe arriba (`:46`)
#: y lo usa el alta: aqui se reutiliza, no se inventa.
_ELEMENT_JUDICIAL = "expedientes_judiciales"
ELEMENTS_CRM = frozenset({_ELEMENT_EXTRAJUDICIAL, _ELEMENT_JUDICIAL})


def traducir_pull_crm(res) -> tuple[str, str, tuple]:
    """`PullResultV2` -> (estado, detalle, pendientes). Tabla completa, una rama por linea.

    Existe como funcion aparte para que cada rama se pueda mutar por separado: el defecto
    que remedia (HA-04) era leer la AUSENCIA DE EXCEPCION como exito, y `pull_expediente_v2`
    no lanza casi nunca — lo dice todo por retorno.
    """
    if getattr(res, "blocked_legacy_v1", False):
        return "fallo", "el expediente esta bloqueado por el legado v1", ()
    errores = list(getattr(res, "errors", []) or [])
    if errores:
        return "fallo", f"el pull devolvio errores: {errores}", ()
    fallidos = int(getattr(res, "documents_failed", 0) or 0)
    if fallidos:
        return ("hecha", f"pull con {fallidos} documento(s) fallido(s)",
                (av1.Pendiente(
                    codigo="crm_documentos_fallidos",
                    detalle=f"{fallidos} documento(s) del gestor documental no se "
                            f"descargaron: `00_Input/05_CRM` esta incompleto."),))
    if int(getattr(res, "documents_total_crm", 0) or 0) == 0:
        # Vacio CONFIRMADO, que no es lo mismo que un error: el CRM contesto y no hay nada.
        return ("saltada", "el gestor documental del expediente esta vacio",
                (av1.Pendiente(
                    codigo="crm_gestor_vacio",
                    detalle="El expediente existe en el CRM y su gestor documental no "
                            "tiene documentos. No es un fallo; es que no hay nada."),))
    return "hecha", f"{getattr(res, 'documents_written', 0)} documento(s) escritos", ()


def etapa_crm(ident, case_dir: Path, *, leer_meta=None, pull=None):
    """Etapa 2 de V1: pull del expediente CRM ya registrado.

    **El `element` sale del `ExpedienteLink`, pertenece al vocabulario cerrado, y la rama
    judicial aborta.** El criterio 38 pide los dos cruces: el obvio —que un caso judicial no
    entre por la via extrajudicial— y el que produce el default de
    `core/sync_sudespacho.py:1356`, que es el inverso.
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

    for link in links:
        el = link.get("element")
        if not el:
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"el expediente {link.get('id')!r} no declara `element` en "
                        f"_caso.md. No se adivina: el default del pull es judicial.")
        if el not in ELEMENTS_CRM:
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"`element` fuera del vocabulario: {el!r}; validos: "
                        f"{sorted(ELEMENTS_CRM)}")
        if el == _ELEMENT_JUDICIAL:
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"el expediente {link.get('id')!r} es de la rama judicial, que "
                        f"sigue bloqueada: V1 no tiene adaptador judicial verificado.")

    hechos, pendientes = [], []
    for link in links:
        try:
            res = _pull(ident.case_id, str(link["id"]), element=link["element"])
        except Exception as exc:  # noqa: BLE001
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"pull de {link['id']} fallo: {type(exc).__name__}: {exc}")
        estado, detalle, pend = traducir_pull_crm(res)
        if estado == "fallo":
            return av1.EtapaResultado(nombre="crm", estado="fallo",
                                      detalle=f"{link['id']}: {detalle}")
        hechos.append(f"{link['id']} ({detalle})")
        pendientes.extend(pend)

    # `saltada` solo si TODOS lo fueron: un expediente vacio junto a otro con documentos
    # es una etapa hecha.
    estado = "saltada" if all("vacio" in h for h in hechos) else "hecha"
    return av1.EtapaResultado(nombre="crm", estado=estado,
                              detalle="; ".join(hechos), pendientes=tuple(pendientes))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_apertura_v1_etapas.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_apertura_v1_etapas.py
git commit -m "feat(v1): etapa CRM por resultado, vocabulario cerrado y rama judicial bloqueada"
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

1. En `core/intake_log.py`, dentro del `frozenset`. **Y el docstring de cabecera dice «27
   tipos» cuando `len(INTAKE_EVENTS)` es **33** (medido el 2026-09-03, HA-12): se corrige a
   **34**, que es lo que queda tras añadir este. Cambiarlo a «28» habría propagado el error.**

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

- [ ] **Step 5: Subir el techo del censo, con la explicación que su propia regla exige**

`registrar_cierre_v1` añade un tercer `append_event` a `scripts/abrir_caso.py`, y el detector del
censo cuenta `append_event` como primitiva (`tests/test_escritura_censo.py:36-38`). El censo pasa
de **83 a 84** y los dos trinquetes se ponen rojos — R-A lo midió (HA-11).

**Subirlo está permitido y hay precedente exacto**, escrito en ese mismo fichero: la regla dice «o
es una escritura nueva sin costura —y entonces falta migrarla— o la lista de productores creció y
hay que decirlo, **no absorberlo**», y el 82→83 anterior fue por un `append_event` de protocolo de
la remediación de R15/H15-06. Éste es de la misma clase: una línea del log forense.

**Lo que NO se hace, y conviene decirlo porque era tentador:** mover `registrar_cierre_v1` a
`core/apertura_v1.py`, que no está en la lista de productores. El censo bajaría a 83 sin que la
escritura desapareciera. Eso es absorber la deuda, que es justo lo que la regla prohíbe.

En `tests/test_escritura_censo.py`, cambiar `TECHO_CENSO = 83` a `84` y añadir al comentario:

```python
#: **83 -> 84 el 2026-09-03.** El cableado de V1 (Plan 5) añade `apertura_v1_terminada` en
#: `scripts/abrir_caso.py`: el estado de la secuencia tiene que quedar en el log forense, o
#: la única constancia de una apertura es la pantalla. Misma clase que el +1 anterior —
#: escritura de **protocolo**, fila #13— y misma condición de bajada: se migra con la #13.
```

- [ ] **Step 6: Commit**

```bash
git add core/intake_log.py scripts/abrir_caso.py tests/test_apertura_v1_cableado.py tests/test_escritura_censo.py
git commit -m "feat(v1): evento apertura_v1_terminada; el censo sube a 84 con su declaracion"
```

---

## Task 8: El cableado en `main` — la salida fuera del mutex y la parada honesta

**Files:**
- Modify: `core/apertura_v1.py` (las etapas no ejecutadas), `scripts/abrir_caso.py:646-679` y la
  firma de `main`
- Test: `tests/test_apertura_v1_cableado.py`

**Interfaces:**
- Produces: `secuencia_v1(...) -> ResultadoV1`, `codigo_de_salida(estado) -> int`,
  `ResultadoV1.no_ejecutadas: tuple[str, ...]`, y el flag `--hasta` validado en `validar_modo`.

**Contexto — tres hallazgos de R-A, y el tercero se reproduce en tres líneas.**

**HA-07 (CRÍTICO).** La rev. 1 lanzaba `typer.Exit(code=…)` **dentro** del `with
mutex_sesion.sostenido(...)`. `case_mutex.tomado` (`core/casos/case_mutex.py:615-659`) distingue
dos caminos: sin excepción en vuelo, una pérdida del lease **lanza** `MutexPerdido`; con excepción
en vuelo, solo la **anota**. Mi `Exit(0)` era esa excepción, así que el proceso salía 0 con la
exclusión perdida y el aviso enterrado en una nota. El revisor lo ejecutó: `TIPO=Exit EXIT_CODE=0`.
Rompe la propiedad que R12/H12-04 construyó: «una pérdida no se evapora». **Remedio: salir del
`with` normalmente y hacer el `Exit` después.**

**HA-06 (ALTO).** `--hasta drve` pasaba la puerta temprana y solo fallaba dentro de `secuenciar`,
después de identidad, mutex y `ensure_case` — en un caso nuevo, con el esqueleto ya creado. El
vocabulario se valida en `validar_modo`, que corre **antes de todo efecto**, que es la propiedad
que D3 hace central.

**HA-06, segunda mitad.** Con `--hasta drive` la rev. 1 emitía `apertura_v1_terminada` y salía 0,
sin que CRM y sala figuraran en ningún sitio: un evento que dice «terminada» sobre una corrida que
no lo hizo. Remedio: las etapas no ejecutadas **entran como pendientes**, así que el estado sigue
derivándose de los datos y el evento no puede mentir.

- [ ] **Step 1: Write the failing test**

```python
def _fake(nombre, visto):
    return av1.Etapa(nombre=nombre,
                     correr=lambda: (visto.append(nombre) or
                                     av1.EtapaResultado(nombre=nombre, estado="hecha",
                                                        detalle="ok")))


def test_una_corrida_completa_toca_TODAS_las_fases_de_v1():
    """El criterio que el bloque 4 del §21.5 pide literalmente."""
    visto = []
    r = cli.secuencia_v1(None, None, folder_id="F", team_id="T",
                         etapas=[_fake(n, visto) for n in
                                 ("drive", "crm", "sala_maquina")])
    assert visto == ["drive", "crm", "sala_maquina"]
    assert r.no_ejecutadas == ()


def test_f24_una_parada_pedida_enumera_las_etapas_que_no_corrieron():
    """F24. Un evento que dice «terminada» sobre una corrida parada a mitad, sin decir que
    faltan dos fases, es un registro falso."""
    visto = []
    r = cli.secuencia_v1(None, None, folder_id="F", team_id="T", hasta="drive",
                         etapas=[_fake(n, visto) for n in
                                 ("drive", "crm", "sala_maquina")])
    assert visto == ["drive"]
    assert r.no_ejecutadas == ("crm", "sala_maquina")
    assert "crm" in " ".join(p.detalle for p in r.pendientes)


def test_f23_el_vocabulario_de_hasta_se_valida_antes_de_todo_efecto():
    """F23. En la rev. 1 un typo pasaba la puerta y reventaba DESPUES de crear el esqueleto."""
    errores = cli.validar_modo("v1", crm="skip", fuente="drive_ev", folder_id="F",
                               hasta="drve")
    assert errores and "drve" in errores[0]
    assert cli.validar_modo("v1", crm="skip", fuente="drive_ev", folder_id="F",
                            hasta="drive") == []


def test_hasta_no_existe_en_modo_libre():
    errores = cli.validar_modo("libre", crm="api", fuente="manual", hasta="drive")
    assert errores and "--hasta" in errores[0]


def test_f14_un_resultado_bloqueado_sale_con_codigo_no_cero():
    assert cli.codigo_de_salida(av1.EstadoV1.BLOQUEADO) != 0
    assert cli.codigo_de_salida(av1.EstadoV1.PREPARADO_CON_PENDIENTES) == 0
    assert cli.codigo_de_salida(av1.EstadoV1.COMPLETO) == 0


def test_f25_la_salida_ocurre_fuera_del_bloque_de_mutex():
    """F25. Con una excepcion en vuelo, `case_mutex.tomado` solo ANOTA la perdida del lease
    en vez de lanzarla (`core/casos/case_mutex.py:640-659`). Lanzar `Exit` dentro del `with`
    convierte una perdida de exclusion en una salida 0 con una nota."""
    import ast
    import inspect

    fuente = inspect.getsource(cli.main)
    arbol = ast.parse(fuente.lstrip())
    withs = [n for n in ast.walk(arbol) if isinstance(n, ast.With)]
    assert withs, "el cuerpo de main ya no tiene el bloque de mutex"
    dentro = [n for w in withs for n in ast.walk(w)
              if isinstance(n, ast.Raise) and "Exit" in ast.dump(n)]
    assert dentro == [], (
        "hay un `raise typer.Exit` DENTRO del bloque de mutex: la perdida del lease "
        "quedaria como nota sobre una salida limpia")


def test_f26_case_busy_se_traduce_a_bloqueado_y_no_a_una_traza():
    from core.casos.workspace_model import CaseBusy

    def revienta(*a, **k):
        raise CaseBusy(w_code="W-000000", detalle="otro proceso lo tiene")

    estado, detalle = cli.traducir_fallo_de_mutex(revienta)
    assert estado == av1.EstadoV1.BLOQUEADO
    assert "otro proceso" in detalle
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_cableado.py -q`
Expected: FAIL con `AttributeError: module 'scripts.abrir_caso' has no attribute 'secuencia_v1'`

- [ ] **Step 3: Write minimal implementation**

1. En `core/apertura_v1.py`, `ResultadoV1` gana un campo y `secuenciar` lo llena:

```python
@dataclasses.dataclass(frozen=True)
class ResultadoV1:
    estado: str
    etapas: tuple[EtapaResultado, ...]
    pendientes: tuple[Pendiente, ...]
    parada: str | None
    no_ejecutadas: tuple[str, ...] = ()
```

Al final de `secuenciar`, antes de construir el resultado:

```python
    corridas = {r.nombre for r in hechas}
    no_ejecutadas = tuple(e.nombre for e in etapas if e.nombre not in corridas)
    # Una fase que no corrio es un pendiente, no un silencio: si no entrara aqui, una
    # parada pedida produciria un `preparado_con_pendientes` indistinguible de una
    # corrida completa, y el evento diria «terminada» sobre media secuencia.
    pendientes.extend(
        Pendiente(codigo=f"etapa_no_ejecutada:{n}",
                  detalle=f"La etapa {n!r} no se ejecuto en esta ronda.")
        for n in no_ejecutadas)
```

2. En `scripts/abrir_caso.py`, `validar_modo` acepta `hasta` y valida su vocabulario:

```python
#: Nombres de las etapas de V1, en orden. Es el vocabulario de `--hasta`.
ETAPAS_V1 = ("drive", "crm", "sala_maquina")
```

En la rama `libre`, antes del `return []`:

```python
    if modo == "libre":
        if hasta is not None:
            return ["--hasta solo existe en --modo v1: en `libre` no hay secuencia "
                    "que parar, y aceptarlo en silencio fingiria haberla parado."]
        return []
```

y entre las comprobaciones de `v1`:

```python
    # H A-06: el vocabulario se valida AQUI y no dentro de `secuenciar`, porque
    # `secuenciar` corre despues de la identidad, del mutex y de `ensure_case`: un typo
    # abortaba con el esqueleto ya creado.
    if hasta is not None and hasta not in ETAPAS_V1:
        errores.append(
            f"--hasta {hasta!r} no es una etapa de V1; validas: {list(ETAPAS_V1)}")
```

3. Las funciones del cableado:

```python
def codigo_de_salida(estado: str) -> int:
    """`bloqueado` sale distinto de 0: un script que invoque la secuencia tiene que poder
    distinguir «termino con pendientes» de «no termino»."""
    return 1 if estado == av1.EstadoV1.BLOQUEADO else 0


def traducir_fallo_de_mutex(fn):
    """Corre `fn` y traduce un fallo de exclusion a (estado, detalle).

    `CaseBusy` y `MutexPerdido` no son trazas que mostrar: son uno de los tres estados del
    §13. Dejarlos propagar deja la corrida sin estado y al operador con un stacktrace.
    """
    from core.casos.workspace_model import CaseBusy, MutexPerdido
    try:
        return None, fn()
    except (CaseBusy, MutexPerdido) as exc:
        return av1.EstadoV1.BLOQUEADO, str(exc)


def secuencia_v1(ident, case_dir, *, folder_id, team_id, hasta=None, etapas=None):
    """El orden completo de V1 (spec §24 D3): Drive -> CRM -> sala de maquina.

    La atomizacion del correo depositado va DENTRO de la tercera, que es donde el cableado
    de 2026-07-27 la puso; por eso el gotcha del runbook —atomizar y pull antes del OCR— se
    cumple por construccion y no por memoria del operador.
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
    for n in resultado.no_ejecutadas:
        typer.echo(f"  [ no corre] {n}")
    if resultado.parada:
        typer.echo(f"  (parada pedida tras la etapa {resultado.parada!r})")
    for p in resultado.pendientes:
        typer.echo(f"  PENDIENTE {p.codigo}: {p.detalle}")
```

4. En `main`: el bloque bajo mutex **calcula**, y la salida ocurre **después** del `with`.

```python
    resultado_v1 = None
    estado_mutex = None
    with mutex_sesion.sostenido(...):        # el `with` existente, sin cambios
        case_manager.ensure_case(...)        # sin cambios
        case_dir = case_locator.localizar(ident.case_id)

        if modo == "v1":
            resultado_v1 = secuencia_v1(ident, case_dir, folder_id=folder_id,
                                        team_id=team_id, hasta=hasta)
            registrar_cierre_v1(case_dir, ident, resultado_v1)
        else:
            _despachar_intake(
                fuente, ident, case_dir,
                folder_id=folder_id, team_id=team_id, src=src, rol=rol,
                cuenta=cuenta, label=label, dry_run=dry_run,
                extraer_adjuntos=extraer_adjuntos,
            )
            if dry_run:
                typer.echo(
                    f"[dry-run] esqueleto en {case_dir}; se omiten log de intake y alta CRM")
                raise typer.Exit(code=0)
            _alta_crm(ident, cuantia=cuantia, crm_mode=crm, yes=yes)

    # FUERA del `with` (HA-07). Si el lease se perdio, el cierre del bloque ya lanzo
    # `MutexPerdido` en vez de anotarlo sobre nuestra excepcion: la perdida no se evapora.
    if resultado_v1 is not None:
        _informar_v1(resultado_v1)
        raise typer.Exit(code=codigo_de_salida(resultado_v1.estado))

    typer.echo(f"OK Caso abierto: {ident.case_id}")
```

**Nota sobre el `dry-run` del modo `libre`:** su `typer.Exit(0)` sigue dentro del `with`, como
estaba. No se toca en este plan —regresarlo sería alcance ajeno— pero **tiene el mismo defecto que
HA-07** y queda anotado en el §4 como fleco medido.

5. Envolver la adquisición para F26: el `with` se abre dentro de `traducir_fallo_de_mutex` o, más
simple, se captura en la frontera:

```python
    try:
        with mutex_sesion.sostenido(...):
            ...
    except (CaseBusy, MutexPerdido) as exc:
        typer.echo(f"=== Apertura V1: {av1.EstadoV1.BLOQUEADO} ===", err=True)
        typer.echo(f"  exclusion: {exc}", err=True)
        raise typer.Exit(code=codigo_de_salida(av1.EstadoV1.BLOQUEADO))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_apertura_v1_cableado.py tests/test_abrir_caso_modo_v1.py tests/test_abrir_caso_cli.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/apertura_v1.py scripts/abrir_caso.py tests/test_apertura_v1_cableado.py
git commit -m "feat(v1): cableado con la salida fuera del mutex y la parada enumerada"
```

---

## Task 8b: El `estado.json` por ronda

**Files:**
- Create: `core/apertura_v1_estado.py`
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_apertura_v1_estado.py`

**Interfaces:**
- Produces: `RondaV1(ronda_id: str, iniciada: str, terminada: str | None, estado: str | None,
  etapas: dict[str, str])`, `leer(case_dir) -> RondaV1 | None`,
  `abrir(case_dir, *, ronda_id, ahora) -> RondaV1`, `cerrar(case_dir, ronda, *, estado, etapas,
  ahora) -> None`.

**Contexto:** la tabla de riesgos de la spec dice «reanudación sin generación común → fase verde
sobre inputs obsoletos → `estado.json` atómico **obligatorio desde la primera entrega**». La rev. 1
lo aplazaba y sostenía la reanudación en «la idempotencia que cada etapa ya tiene»; R-A (HA-01)
señaló que eso contradice una línea expresa, y Nikolai decidió el 2026-09-03 incorporarlo.

**Lo que hace y lo que no.** Registra qué ronda corrió, cuándo empezó, qué etapas cerró y en qué
estado terminó, con escritura **atómica** (`os.replace`, el patrón de
`core/casos/workspace_registry.py`). **No** es el `operations` completo del bloque 2 de la spec: no
hay reconciliación de dos escritores ni generaciones de artefacto. Lo que compra es la propiedad
que la rev. 1 afirmaba sin construir: **una ronda que murió a mitad se detecta y se dice**, en vez
de que la siguiente corrida la dé por buena.

- [ ] **Step 1: Write the failing test**

```python
"""El `estado.json` por ronda de V1 (spec §11: obligatorio desde la primera entrega)."""
import json

import pytest

from core import apertura_v1_estado as est


def test_sin_fichero_no_hay_ronda(tmp_path):
    assert est.leer(tmp_path) is None


def test_f27_la_escritura_es_atomica_y_lleva_id_de_ronda(tmp_path, monkeypatch):
    """F27. Escribir en sitio deja un JSON truncado si el proceso muere a mitad, y un
    estado ilegible es peor que ninguno: la siguiente ronda no sabe que hubo una."""
    reemplazos = []
    real = est.os.replace
    monkeypatch.setattr(est.os, "replace",
                        lambda a, b: (reemplazos.append((a, b)), real(a, b))[1])
    r = est.abrir(tmp_path, ronda_id="r1", ahora="2026-09-03T10:00:00+00:00")
    assert r.ronda_id == "r1"
    assert reemplazos, "la escritura no paso por os.replace"
    assert json.loads((tmp_path / "00_Input" / "_apertura_v1.json")
                      .read_text(encoding="utf-8"))["ronda_id"] == "r1"


def test_f28_una_ronda_sin_cerrar_se_detecta(tmp_path):
    """F28. Es la propiedad entera: si la ronda anterior no se cerro, la siguiente NO puede
    tratar su salida como buena."""
    est.abrir(tmp_path, ronda_id="r1", ahora="2026-09-03T10:00:00+00:00")
    previa = est.leer(tmp_path)
    assert previa.terminada is None
    assert previa.sin_cerrar() is True


def test_una_ronda_cerrada_no_esta_sin_cerrar(tmp_path):
    r = est.abrir(tmp_path, ronda_id="r1", ahora="2026-09-03T10:00:00+00:00")
    est.cerrar(tmp_path, r, estado="preparado_con_pendientes",
               etapas={"drive": "hecha"}, ahora="2026-09-03T10:05:00+00:00")
    leida = est.leer(tmp_path)
    assert leida.sin_cerrar() is False
    assert leida.estado == "preparado_con_pendientes"
    assert leida.etapas == {"drive": "hecha"}


def test_un_estado_ilegible_se_trata_como_ausente(tmp_path):
    (tmp_path / "00_Input").mkdir(parents=True)
    (tmp_path / "00_Input" / "_apertura_v1.json").write_text("{roto", encoding="utf-8")
    assert est.leer(tmp_path) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_estado.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.apertura_v1_estado'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Estado durable por ronda de la apertura V1 — Plan 5, Task 8b.

La spec lo hace obligatorio «desde la primera entrega» (§11, tabla de riesgos: «reanudacion
sin generacion comun → fase verde sobre inputs obsoletos»). Sin esto, «reanudar tras un
corte» es una afirmacion del autor y no una propiedad del sistema.

**Lo que NO es:** el `operations` completo del bloque 2. No reconcilia dos escritores ni
versiona artefactos. Lo que da es que una ronda muerta a mitad se DETECTE.
"""
from __future__ import annotations

import dataclasses
import json
import os
import tempfile
from pathlib import Path

_FICHERO = "_apertura_v1.json"


@dataclasses.dataclass(frozen=True)
class RondaV1:
    ronda_id: str
    iniciada: str
    terminada: str | None = None
    estado: str | None = None
    etapas: dict[str, str] = dataclasses.field(default_factory=dict)

    def sin_cerrar(self) -> bool:
        return self.terminada is None


def _ruta(case_dir: Path) -> Path:
    return Path(case_dir) / "00_Input" / _FICHERO


def leer(case_dir: Path) -> RondaV1 | None:
    """`None` si no hay, o si el fichero esta roto: un estado ilegible se trata como
    ausente, que es el lado seguro — lo contrario seria decidir sobre datos inventados."""
    f = _ruta(case_dir)
    if not f.is_file():
        return None
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(d, dict) or "ronda_id" not in d or "iniciada" not in d:
        return None
    return RondaV1(ronda_id=str(d["ronda_id"]), iniciada=str(d["iniciada"]),
                   terminada=d.get("terminada"), estado=d.get("estado"),
                   etapas=dict(d.get("etapas") or {}))


def _escribir(case_dir: Path, ronda: RondaV1) -> None:
    """Atomica: temporal en el MISMO directorio + `os.replace`. Escribir en sitio deja un
    JSON truncado si el proceso muere, y entonces la ronda siguiente no sabe que hubo una.
    """
    f = _ruta(case_dir)
    f.parent.mkdir(parents=True, exist_ok=True)
    cuerpo = json.dumps(dataclasses.asdict(ronda), ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=str(f.parent), prefix=".apertura_v1.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(cuerpo)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, f)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def abrir(case_dir: Path, *, ronda_id: str, ahora: str) -> RondaV1:
    r = RondaV1(ronda_id=ronda_id, iniciada=ahora)
    _escribir(case_dir, r)
    return r


def cerrar(case_dir: Path, ronda: RondaV1, *, estado: str,
           etapas: dict[str, str], ahora: str) -> None:
    _escribir(case_dir, dataclasses.replace(
        ronda, terminada=ahora, estado=estado, etapas=dict(etapas)))
```

- [ ] **Step 4: Cablearlo en `main`**

Dentro del bloque de mutex, en la rama `v1`, rodeando la secuencia:

```python
        if modo == "v1":
            previa = estado_v1.leer(case_dir)
            if previa is not None and previa.sin_cerrar():
                typer.echo(
                    f"[AVISO] la ronda {previa.ronda_id!r} (iniciada {previa.iniciada}) "
                    f"no llego a cerrarse: esta corrida no da por buena su salida.",
                    err=True)
            ronda = estado_v1.abrir(case_dir, ronda_id=now_iso_utc(),
                                    ahora=now_iso_utc())
            resultado_v1 = secuencia_v1(ident, case_dir, folder_id=folder_id,
                                        team_id=team_id, hasta=hasta)
            estado_v1.cerrar(case_dir, ronda, estado=resultado_v1.estado,
                             etapas={e.nombre: e.estado for e in resultado_v1.etapas},
                             ahora=now_iso_utc())
            registrar_cierre_v1(case_dir, ident, resultado_v1)
```

Run: `python -m pytest tests/test_apertura_v1_estado.py tests/test_apertura_v1_cableado.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/apertura_v1_estado.py scripts/abrir_caso.py tests/test_apertura_v1_estado.py
git commit -m "feat(v1): estado.json atomico por ronda, y el aviso de la ronda sin cerrar"
```

---

## Task 9: El arnés de mutación — veintiocho mutantes, y que sepa medir su propia regla

**Files:**
- Create: `tests/_mutantes_plan5.py`

**Interfaces:**
- Produces: `python -m tests._mutantes_plan5`, con salida por mutante y código no cero si alguno
  sobrevive **o mata de más**.

**Contexto — HA-09, y son dos defectos, no uno.**

**El arnés no podía medir su propia regla.** La rev. 1 ejecutaba solo el `nodeid` declarado y leía
un booleano, así que por construcción **no observaba qué otros tests mataba el mutante**. La regla
que el propio plan enuncia —«un mutante que mata de más está mal apuntado»— era inverificable. Se
corrige ejecutando el **conjunto contractual completo** por mutante y comparando el conjunto exacto
de rojos con el declarado.

**Y F12 sobrevivía.** Su mutante cambiaba solo el texto de `detalle`, y su test afirma `estado` y
la presencia de pendientes, no el texto. El revisor lo corrió aislado: `EXIT=0`, VIVO. **La
lección, que es la misma que ya tengo escrita:** si la mitad útil de un contrato es texto para un
humano, no está verificada hasta que alguien afirme sobre ese texto. Se corrige apuntando el
mutante a la propiedad —añadir el pendiente que F12 dice que no hay— y no a la prosa.

**F8 también estaba mal apuntado:** retiraba la guarda y el test moría por `KeyError`, no por el
contrato. Se apunta a la adivinanza que el contrato prohíbe.

- [ ] **Step 1: Write the harness**

```python
"""Arnes de mutacion del Plan 5: veintiocho mutantes, uno por frontera del §3.

Uso: python -m tests._mutantes_plan5

Cada entrada muta UNA linea de produccion y declara el conjunto EXACTO de nodeids que debe
ponerse rojo. Se ejecuta el conjunto contractual completo y se comparan los conjuntos: un
mutante que mata de menos no prueba su frontera; uno que mata de mas esta mal apuntado y
prueba otra cosa. La rev. 1 leia un booleano de un solo nodeid y por eso no podia medir su
propia regla (HA-09).

Restaura con `git checkout -- <fichero>`, que lee del INDICE: commitea antes de correr.
"""
from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: El conjunto contractual: se ejecuta ENTERO por mutante.
SUITE = ("tests/test_apertura_v1_secuenciador.py",
         "tests/test_apertura_v1_etapas.py",
         "tests/test_apertura_v1_cableado.py",
         "tests/test_apertura_v1_estado.py")

# (id, fichero, texto_original, texto_mutado, {nodeids que DEBEN morir})
MUTANTES = [
    ("F1", "core/apertura_v1.py",
     "            hubo_fallo = True\n            break",
     "            hubo_fallo = True",
     {"tests/test_apertura_v1_secuenciador.py::test_f1_un_fallo_detiene_la_secuencia"}),
    # … F2-F5 como en la rev. 1, con su nodeid unico convertido en conjunto …
    ("F6", "scripts/abrir_caso.py",
     '            detalle="la consulta remota no se hizo: el pull devolvio `skipped` pese a "',
     '            detalle="`.pulled` ya presente, no se re-descargo: "',
     {"tests/test_apertura_v1_etapas.py::"
      "test_f6_un_skipped_en_v1_es_fallo_porque_la_consulta_no_se_hizo"}),
    ("F8", "scripts/abrir_caso.py",
     '        if not el:',
     '        el = el or _ELEMENT_JUDICIAL\n        if False:',
     {"tests/test_apertura_v1_etapas.py::test_f8_un_link_sin_element_es_fallo_y_no_se_adivina",
      "tests/test_apertura_v1_etapas.py::test_f22_un_element_judicial_aborta_en_v1"}),
    ("F12", "scripts/abrir_caso.py",
     '        detalle=("OCR hecho; sin correo que atomizar" if status is None\n'
     '                 else "OCR hecho; atomizacion ok"))',
     '        detalle=("OCR hecho; sin correo que atomizar" if status is None\n'
     '                 else "OCR hecho; atomizacion ok"),\n'
     '        pendientes=(av1.Pendiente(codigo="x", detalle="x"),))',
     {"tests/test_apertura_v1_etapas.py::"
      "test_f10_f12_el_status_de_atomizacion_gobierna_el_pendiente[None-hecha-False]",
      "tests/test_apertura_v1_etapas.py::"
      "test_f10_f12_el_status_de_atomizacion_gobierna_el_pendiente[ok-hecha-False]"}),
    ("F16", "scripts/abrir_caso.py",
     "        res = _intake(ident, case_dir, folder_id, team_id, dry_run=False, force=True)",
     "        res = _intake(ident, case_dir, folder_id, team_id, dry_run=False, force=False)",
     {"tests/test_apertura_v1_etapas.py::test_f16_en_v1_el_pull_consulta_en_cada_ronda"}),
    ("F17", "scripts/abrir_caso.py",
     "    if errores:\n        return \"fallo\", f\"el pull devolvio errores: {errores}\", ()",
     "    if False:\n        return \"fallo\", f\"el pull devolvio errores: {errores}\", ()",
     {"tests/test_apertura_v1_etapas.py::"
      "test_f17_f20_el_resultado_del_pull_gobierna_la_etapa[kw0-fallo-None]"}),
    # … F18-F28 con la misma forma: una linea mutada, un conjunto declarado …
]
```

**El resto de entradas sigue exactamente esa forma.** Se escriben las veintiocho: el §3 enumera
veintiocho fronteras y la regla del plan es una por frontera. Las de la rev. 1 que no cambian (F1-F5,
F7, F9-F11, F13, F14) conservan su texto mutado y solo convierten su `nodeid` en un conjunto de un
elemento.

```python
def _rojos(suite) -> set[str]:
    """Conjunto de nodeids en rojo tras correr la suite entera.

    Por JUnit XML y no por el resumen: el resumen no sobrevive a una tuberia, y este repo
    ya tiene esa leccion escrita.
    """
    xml = RAIZ / ".mutantes.xml"
    subprocess.run(
        [sys.executable, "-m", "pytest", *suite, "-q", "--no-header",
         "-p", "no:randomly", "-p", "no:cacheprovider", f"--junit-xml={xml}"],
        cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace")
    if not xml.exists():
        raise RuntimeError("pytest no genero el XML: el arnes no puede medir nada")
    arbol = ET.parse(xml)
    rojos = set()
    for tc in arbol.iter("testcase"):
        if tc.find("failure") is not None or tc.find("error") is not None:
            archivo = (tc.get("file") or "").replace("\\", "/")
            rojos.add(f"{archivo}::{tc.get('name')}")
    xml.unlink()
    return rojos


def main() -> int:
    base = _rojos(SUITE)
    if base:
        print(f"ARNES INUTIL: la suite ya tiene {len(base)} rojo(s) sin mutar: {sorted(base)}")
        return 1

    malos = []
    for ident, rel, viejo, nuevo, esperados in MUTANTES:
        f = RAIZ / rel
        original = f.read_text(encoding="utf-8")
        if viejo not in original:
            print(f"{ident}: ARNES ROTO — el texto a mutar no esta en {rel}")
            malos.append(ident)
            continue
        f.write_text(original.replace(viejo, nuevo, 1), encoding="utf-8")
        try:
            rojos = _rojos(SUITE)
        finally:
            f.write_text(original, encoding="utf-8")
        if rojos == esperados:
            print(f"{ident}: MUERTO por su frontera ({len(rojos)} rojo)")
            continue
        if not rojos:
            print(f"{ident}: VIVO — nada se puso rojo")
        elif esperados - rojos:
            print(f"{ident}: MATA DE MENOS — no murio {sorted(esperados - rojos)}")
        else:
            print(f"{ident}: MAL APUNTADO — mata de mas: {sorted(rojos - esperados)}")
        malos.append(ident)

    if malos:
        print(f"\n{len(malos)} mutante(s) con problema: {malos}")
        return 1
    print(f"\n{len(MUTANTES)}/{len(MUTANTES)} mutantes muertos, cada uno SOLO por su frontera.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Commit before mutating**

`git checkout` restaura desde el **índice**: mutar sobre trabajo sin commitear y restaurar después
lo pierde.

```bash
git add tests/_mutantes_plan5.py && git commit -m "test(v1): arnes de mutacion, 28 fronteras, conjunto exacto"
```

- [ ] **Step 3: Run the harness**

Run: `python -m tests._mutantes_plan5`
Expected: `28/28 mutantes muertos, cada uno SOLO por su frontera.` y código de salida 0.

- [ ] **Step 4: Si algo no cuadra, leer QUÉ dice**

`VIVO` = la frontera no está contratada: falta el test. `MATA DE MENOS` = el test declarado no la
cubre. `MAL APUNTADO` = el mutante prueba otra cosa; reapúntalo, **no** amplíes el conjunto
esperado para que cuadre. Esa última tentación es la que convierte el arnés en decoración.

- [ ] **Step 5: Commit**

```bash
git add -u && git commit -m "test(v1): 28/28 mutantes muertos por su propia frontera"
```

---

## Task 10: E2E de la secuencia — con el esquema real y con espías

**Files:**
- Create: `tests/test_apertura_v1_e2e.py`

**Contexto — HA-10, y el defecto es del tipo que no se nota porque sale verde.** La fixture de la
rev. 1 escribía `sudespacho_expedientes` en el nivel superior del frontmatter. `read_case_meta`
devuelve `fm.get("meta")` (`core/casos/case_locator.py:222-223`), así que devolvía `{}`, la etapa
CRM tomaba la rama `saltada` y **el E2E pasaba sin ejercitar el CRM**. El revisor lo ejecutó y
obtuvo `{}`. Dos remedios, y el segundo es el que impide que vuelva: el esquema real, y **espías
que afirmen que cada doble se llamó** — porque un test que no comprueba que llamó, no distingue
«funcionó» de «no se ejecutó».

Y se dobla solo el **límite remoto y el OCR**, no las etapas: doblar `etapa_sala_maquina` entera
salta el adaptador, que es una de las piezas bajo prueba.

- [ ] **Step 1: Write the failing test**

```python
"""E2E de la secuencia de V1 sobre un arbol de caso real en disco, sin PII y sin OCR.

Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md, Task 10.
Criterio 14 del §14 de la spec: punto fijo.
"""
import json

import pytest

from core import apertura_v1 as av1
from core.intake_drive import DriveIntakeResult
from scripts import abrir_caso as cli

CASE_ID = "BaXX1 - Prueba (W-000000) - NEGATIVA_OFERTA"


@pytest.fixture()
def caso(tmp_path):
    """Esquema REAL: `read_case_meta` devuelve `fm["meta"]`, no el frontmatter entero."""
    d = tmp_path / CASE_ID
    (d / "00_Input").mkdir(parents=True)
    (d / "00_Input" / "_caso.md").write_text(
        "---\n"
        "meta:\n"
        f"  case_id: {CASE_ID}\n"
        "  id_go: W-000000\n"
        "  tipo_caso: NEGATIVA_OFERTA\n"
        "  ciudad: Barcelona\n"
        "  sudespacho_expedientes:\n"
        "    - id: '648'\n"
        "      element: extrajudiciales\n"
        "      input_dir: sudespacho_648\n"
        "---\n",
        encoding="utf-8")
    return d


def test_la_fixture_es_legible_por_el_lector_real(caso):
    """El guardarrail de HA-10: si esto falla, el resto del E2E prueba la rama `saltada`
    y pasa en verde sin tocar el CRM."""
    from core.casos import case_locator
    meta = case_locator.read_case_meta(caso)
    assert meta.get("sudespacho_expedientes"), "el lector real no ve el expediente"


class _Ident:
    case_id = CASE_ID
    w_code = "W-000000"


class _ResCRM:
    blocked_legacy_v1 = False
    documents_total_crm = 3
    documents_written = 3
    documents_failed = 0
    errors: list[str] = []


@pytest.fixture()
def dobles(caso, monkeypatch):
    """Se doblan SOLO los limites: rclone, la API del CRM y el OCR."""
    llamadas = {"drive": 0, "crm": 0, "ocr": 0}

    def _intake(ident, case_dir, folder_id, team_id, *, dry_run, force):
        llamadas["drive"] += 1
        assert force is True, "V1 tiene que consultar Drive en cada ronda"
        return DriveIntakeResult(case_id="C", team_id="T", folder_id="F",
                                 target_dir=caso / "00_Input" / "01_Drive EV",
                                 files_after=2, skipped=False)

    def _pull(case_id, expediente_id, *, element):
        llamadas["crm"] += 1
        assert element == "extrajudiciales"
        return _ResCRM()

    def _apply(case_id=None, **kw):
        llamadas["ocr"] += 1
        return "ok"

    from core import sync_sudespacho
    from scripts import sala_maquina
    monkeypatch.setattr(cli, "_intake_drive_ev", _intake)
    monkeypatch.setattr(sync_sudespacho, "pull_expediente_v2", _pull)
    monkeypatch.setattr(sala_maquina, "apply", _apply)
    return llamadas


def test_e2e_la_secuencia_recorre_las_tres_etapas_y_las_LLAMA(caso, dobles):
    """El espia es la mitad que faltaba: sin el, «hecha» y «no se ejecuto» se ven igual."""
    r = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")

    assert [e.nombre for e in r.etapas] == ["drive", "crm", "sala_maquina"]
    assert [e.estado for e in r.etapas] == ["hecha", "hecha", "hecha"]
    assert dobles == {"drive": 1, "crm": 1, "ocr": 1}
    assert r.estado == av1.EstadoV1.PREPARADO_CON_PENDIENTES
    assert r.no_ejecutadas == ()


def test_e2e_el_evento_de_cierre_queda_en_el_log(caso, dobles):
    r = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")
    cli.registrar_cierre_v1(caso, _Ident(), r)
    log = caso / "00_Input" / "_intake_log.jsonl"
    ev = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l][-1]
    assert ev["event"] == "apertura_v1_terminada"
    assert ev["details"]["estado"] == "preparado_con_pendientes"
    assert ev["details"]["etapas"] == [
        {"nombre": "drive", "estado": "hecha"},
        {"nombre": "crm", "estado": "hecha"},
        {"nombre": "sala_maquina", "estado": "hecha"}]


def test_e2e_es_punto_fijo_MATERIAL_y_no_solo_de_estado(caso, dobles):
    """Criterio 14. La rev. 1 comparaba el string de estado, que no dice nada: dos corridas
    pueden coincidir en el token y diferir en el arbol. Se compara el arbol."""
    def foto():
        return sorted((p.relative_to(caso).as_posix(), p.stat().st_size)
                      for p in caso.rglob("*") if p.is_file()
                      and p.name != "_intake_log.jsonl")

    primera = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")
    tras_1 = foto()
    segunda = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")
    tras_2 = foto()

    assert primera.estado == segunda.estado
    assert tras_1 == tras_2, "la segunda corrida cambio el arbol: no es punto fijo"
    # Y las tres etapas se CONSULTARON las dos veces: el punto fijo de V1 no es «no mirar»,
    # es «mirar y no cambiar nada» (HA-03).
    assert dobles == {"drive": 2, "crm": 2, "ocr": 2}


def test_e2e_un_fallo_del_crm_bloquea_y_la_sala_no_corre(caso, dobles, monkeypatch):
    from core import sync_sudespacho

    class _Roto(_ResCRM):
        errors = ["list_gdocu_docs_rest: 500"]

    monkeypatch.setattr(sync_sudespacho, "pull_expediente_v2",
                        lambda *a, **k: _Roto())
    r = cli.secuencia_v1(_Ident(), caso, folder_id="F", team_id="T")
    assert r.estado == av1.EstadoV1.BLOQUEADO
    assert dobles["ocr"] == 0, "la sala de maquina corrio sobre un CRM incompleto"
    assert r.no_ejecutadas == ("sala_maquina",)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apertura_v1_e2e.py -q`
Expected: FAIL mientras falte cualquier pieza de las Tasks 1-8b.

- [ ] **Step 3: No implementation needed**

Si las Tasks 1-8b están hechas, este test pasa sin código nuevo. Si no pasa, el defecto está en
ellas y se corrige ahí.

- [ ] **Step 4: Run the whole suite with two seeds**

```bash
python -m pytest -q --tb=short -p randomly --randomly-seed=777 --junit-xml=.pytest-777.xml
```

```bash
python -m pytest -q --tb=short -p randomly --randomly-seed=31337 --junit-xml=.pytest-31337.xml
```

Expected: 0 fallos con ambas. **El conteo se lee del `--junit-xml`, no del resumen por tubería.**
Una variación respecto al último cierre que no esté explicada es bandera roja.

- [ ] **Step 5: Commit**

```bash
git add tests/test_apertura_v1_e2e.py && git commit -m "test(v1): E2E con esquema real, espias y punto fijo material"
```

---

## Task 10b: Migrar el test vigente que dobla la costura retirada

**Files:**
- Modify: `tests/test_abrir_caso_modo_v1.py:107-128`

**Contexto — HA-11, segunda mitad, y es el peor riesgo operativo del plan.** El test vigente de una
invocación V1 válida dobla `_despachar_intake`. La Task 8 sustituye esa costura por `secuencia_v1`
en modo `v1`, así que **el doble queda inerte y el test llega al Drive real**. El revisor lo
reprodujo: la invocación intentó el pull de verdad. Un test que sale a la red es peor que un test
que falla.

- [ ] **Step 1: Ver qué dobla hoy**

Run: `python -m pytest tests/test_abrir_caso_modo_v1.py -q`
Expected: PASS (línea base antes de tocar nada).

- [ ] **Step 2: Cambiar el doble a la costura nueva**

Donde el test hace `monkeypatch.setattr(cli, "_despachar_intake", …)` para el caso `v1`, se dobla
en su lugar la secuencia, y **se afirma que se llamó** — que es lo que impide que el doble vuelva a
quedarse inerte sin avisar:

```python
    llamada = {}

    def _falsa(ident, case_dir, *, folder_id, team_id, hasta=None, etapas=None):
        llamada["si"] = True
        return av1.ResultadoV1(
            estado=av1.EstadoV1.PREPARADO_CON_PENDIENTES,
            etapas=(av1.EtapaResultado(nombre="drive", estado="hecha", detalle="doble"),),
            pendientes=(av1.PENDIENTE_FUENTES_V3,), parada=None, no_ejecutadas=())

    monkeypatch.setattr(cli, "secuencia_v1", _falsa)
    # …invocación…
    assert llamada.get("si"), "el doble quedo inerte: la invocacion no paso por secuencia_v1"
```

- [ ] **Step 3: Comprobar que NO sale a la red**

Doblar además `cli._intake_drive_ev` con un `pytest.fail` explícito: si la migración se hace mal,
el test lo dice en vez de tardar treinta segundos y tocar Drive.

```python
    monkeypatch.setattr(cli, "_intake_drive_ev",
                        lambda *a, **k: pytest.fail("el test salio a Drive"))
```

- [ ] **Step 4: Run**

Run: `python -m pytest tests/test_abrir_caso_modo_v1.py -q`
Expected: PASS, sin actividad de red.

- [ ] **Step 5: Commit**

```bash
git add tests/test_abrir_caso_modo_v1.py
git commit -m "test(v1): migrar el doble del test vigente a la costura nueva"
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

## §4. Self-review de esta rev. 2

**Cobertura de los doce hallazgos de R-A.** HA-01 → Task 8b. HA-02 → Task 3 (por
`_intake_drive_ev`). HA-03 → Task 3 (`force=True`) y F16. HA-04 → Task 4 (`traducir_pull_crm`, con
F17-F20). HA-05 → Task 4 (F21, F22). HA-06 → Task 8 (F23, F24). HA-07 → Task 8 (F25, F26). HA-08 →
adjudicado como parcialmente refutado; lo que sobrevive queda como deuda 2 del §0. HA-09 → Task 9.
HA-10 → Task 10. HA-11 → Task 7 (Step 5, el techo a 84) y Task 10b. HA-12 → Task 7 (33→34) y las
restricciones globales.

**Lo que esta rev. 2 deja SIN cubrir, con nombre:**

- **El historial content-addressed de Drive con generaciones y tombstones.** Si E&V **sustituye** un
  fichero en sitio, se pierde la versión procesada anterior. Es la deuda 3 del §0.
- **`--hasta` no admite parar dentro de la sala de máquina**, entre la atomización y el OCR: la
  atomización vive dentro de `apply` y separarla es otra pieza.
- **El `typer.Exit(0)` del `dry-run` del modo `libre` sigue dentro del bloque de mutex** y tiene el
  mismo defecto que HA-07. No se toca porque regresarlo es alcance ajeno a este plan, pero **queda
  medido y dicho**: es una entrada para `MEJORAS_FUTURAS.md`, no un descuido.
- **Los cuatro defectos vivos del entorno:** `MEJORAS #137`, `#138`, `#139` y `#141`. El más cercano
  sigue siendo `#141` (`buscar()` no valida el `case_id`), porque la secuencia resuelve por
  `--case-id`.
- **La cifra «103 referencias» de la spec §24 D3 es irreproducible** (son 53 en 19 ficheros). La
  decisión que sostiene no cambia; corregirla donde vive es un fleco para la spec.

**Consistencia de tipos.** `EtapaResultado` se construye en las Tasks 3, 4 y 6 con los mismos campos
(`nombre`, `estado`, `detalle`, `pendientes`); `Pendiente` siempre `(codigo, detalle)`; `secuenciar`
devuelve `ResultadoV1`, que en la Task 8 gana `no_ejecutadas` y lo consumen las Tasks 8, 10 y 10b;
`apply` devuelve `str | None` en la Task 5 y lo consume la 6; `traducir_pull_crm` devuelve
`(estado, detalle, pendientes)` y solo la Task 4 lo usa.

**Sin marcadores de posición.** La única elisión deliberada está en la lista de mutantes de la Task
9, donde se escriben las entradas nuevas y las corregidas y se dice explícitamente que las diez
inalteradas conservan su texto de la rev. 1 convirtiendo su `nodeid` en un conjunto de un elemento.
No es un «TBD»: es no reimprimir código que no cambia.

---

## 5. Adjudicación de la revisión adversarial (Codex, 2026-09-03) — NO-EJECUTABLE, remediado

- **Objeto revisado:** diseño del Plan 5 — el cableado de la secuencia de V1 y el E2E (rev. 1), commit `a95326e`
- **Ronda:** A
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-03-apertura-v1-plan5-rA-adversarial-review.md`
- **Hallazgos:** 12 recibidos — 11 confirmados, 1 parcialmente refutado (4 CRÍTICOS + 1 elevado por el adjudicador, 5 ALTOS, 1 MEDIO, 1 BAJO)
- **Remediado en:** la rev. 2 de este plan (§0, §3 y las Tasks 3, 4, 7, 8, 8b, 9, 10 y 10b)

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
| HA-08 | ALTO | **PARCIALMENTE REFUTADO** | la poda de `mensajes/` está **gateada** en foto completa (`core/email_atomize/pipeline.py:204-220`); sobrevive solo en `vistas/` y `*.contenido.md` |
| HA-09 | ALTO | **CONFIRMADO** | F12 muta solo el texto de `detalle` y su test no lo afirma: sobrevive. Y `_correr` no puede medir su propia regla |
| HA-10 | ALTO | **CONFIRMADO** | `core/casos/case_locator.py:222`: `read_case_meta` devuelve `fm.get("meta")`; la fixture daba `{}` |
| HA-11 | MEDIO | **CONFIRMADO** | el evento nuevo sube el censo a 84/83, y el test vigente de V1 dobla una costura que el plan retira |
| HA-12 | BAJO | **CONFIRMADO** | `len(INTAKE_EVENTS)` = 33; `git grep -o` da 53 en 19 ficheros, no 103 |

**Sobre HA-08, y esta corrección es contra mí, no contra el revisor.** Lo confirmé, y encima le
añadí un escenario de fallo más grave que el suyo —«una corrida parcial poda contra un `esperados`
incompleto»— **sin comprobar la guarda**. La guarda existe: el `unlink` de `mensajes/` vive dentro
del `else` de `if report.errores:` (`core/email_atomize/pipeline.py:204-220`), y el comentario del
motor lo dice con todas las letras: «La poda solo retira huérfanos cuando la foto está completa».
Con errores de lectura, `poda_omitida = True` y no se poda nada. Mi escenario era **imposible** en
la vía que más importa.

Lo que **sí** sobrevive del hallazgo, y es estrecho: las otras dos podas —`vistas/*.md`
(`:262-267`) y `*.contenido.md` (`core/adjuntos_contenido/pipeline.py:107-109`)— **no** llevan esa
guarda, y un fallo de render de vista **deliberadamente no entra en `report.errores`** (el
comentario de `:192-195` explica por qué: apagaría la poda del árbol entero). Así que un render
parcial de vistas puede retirar una vista buena de una corrida anterior. Lo que se pierde es una
vista o un `.contenido.md`: derivados regenerables desde `corpus.jsonl` y desde el crudo, **nunca
material de cliente**. La contradicción con D4 —podar en vez de archivar— sigue en pie como deuda
real de radio pequeño; el riesgo de pérdida que le atribuí, no.

**Y la lección, que es del mismo día y de la misma mano:** acepté un hallazgo y lo agravé sin ir a
la fuente. Un revisor que no comprueba la guarda no refuta; un **adjudicador** que no la comprueba
tampoco confirma. Adjudicar contra la fuente no es solo para tumbar hallazgos: también para no
inflarlos.

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


---

## 6. Adjudicación de la revisión adversarial (Claude Code sesión independiente, 2026-09-03) — NO-SHIP, parcial

- **Objeto revisado:** diff del Plan 5 — el cableado de la secuencia de V1, commit `5cdf7da`
- **Ronda:** B
- **Revisor:** Claude Code (sesión independiente)
- **Informe recibido:** `docs/superpowers/specs/2026-09-03-apertura-v1-plan5-rB-adversarial-review.md`
- **Hallazgos:** 73 recibidos — 10 CRÍTICOS, 10 ALTOS, 2 MEDIO-ALTOS, ~29 MEDIOS, ~22 BAJOS; 1 parcialmente refutado
- **Remediado en:** los commits de esta rama posteriores a `5cdf7da`

**La independencia es MÁS DÉBIL de lo contratado, y va primero.** Codex agotó su cupo a mitad de
la ronda —vuelve el 2026-09-07— y se aplicó el revisor sustituto de `AGENTS.md`: seis lentes de
**Claude Code**, o sea el mismo modelo que escribió el código. La compensación que el contrato
exige se aplicó entera (seis lentes en paralelo, copia congelada, sin mi adjudicación de R-A ni su
acta, obligación de abrir el fichero y de ejecutar), y aun así **este diff no debería mergearse sin
que Codex lo haya visto**.

### Lo que la ronda demostró, y no es un defecto sino un método

**El «28/28 mutantes muertos» con que cerré la pieza era una autoatestación cerrada.** Tres lentes
lo desmontaron con mutantes propios: **17 de 21 vivos** en una, **11 de 12** en otra, y una tercera
midió que **cuatro de mis 28 muertes caían sobre fronteras inexistentes en producción**. El
conjunto de ficheros de mi arnés **excluía justo el cableado**, así que medía el interior de las
piezas y no lo que las une. Un número que yo genero con mi arnés, sobre mi lista de fronteras, en
mi suite, **no es evidencia independiente**: es mi hipótesis escrita en cifras.

### Las cuatro fronteras cerradas (no los ejemplos)

| Frontera | Lo que estaba mal | Lo que se cerró |
|---|---|---|
| **A. El productor decide, no el tipo** | Leí los *campos* de `PullResultV2` y no su *productor*: `errors` se rellena también cuando el gestor está **vacío**, y `documents_failed` se incrementa en el mismo bloque que su `errors.append`. Las dos ramas eran inalcanzables y un expediente sin documentos **abortaba la apertura** | `sync_sudespacho.es_gestor_vacio()` vive **con el productor** y el adaptador pregunta; tres ramas, las tres alcanzables; y un test que corre el **productor real** y le pregunta al predicado. Cambio de criterio propio: unos documentos que no bajan dejan el espejo incompleto y eso **bloquea**, no se anota |
| **B. Un fichero de control se declara en TODOS los registros** | Existe un registro canónico (`config.INTAKE_CONTROL_FILES`, «Lista ÚNICA») y lo declaré en **ninguno** de los cuatro sitios que clasifican `00_Input` | Declarado en los cuatro; `sala_maquina._IGNORAR` pasa a **derivar** del canónico en vez de duplicarlo (esa duplicación era el hueco); y un **guard que itera sobre lo que el módulo declara**, así que el próximo fichero de control obliga a declararlo |
| **C. Escribir sin exclusión es la violación que el mutex impide** | El registro durable se escribía **dentro** del bloque, y una pérdida de lease solo se anota: disco y `.jsonl` afirmaban un éxito que la pantalla desmentía | El registro sale del bloque, y **si se perdió la exclusión no se escribe nada**: la ronda queda abierta y la corrida siguiente la ve `sin_cerrar()`. Eso convierte ese aviso en el mecanismo y no en un adorno. Y `CaseBusy` deja de colapsarse con `MutexPerdido` |
| **D. Una costura tiene dos extremos** | Todos mis tests inyectaban el colaborador, así que contrataban solo el lado del llamador. Se podía hacer que `apply` dejara de devolver el status, que la custodia dejara de reenviar `force`, o que `main` pasara `hasta=None`, **sin un solo rojo** | `tests/test_apertura_v1_costuras.py`: diez tests que recorren el camino **por defecto** y afirman el efecto donde el valor se consume, incluidos el código de salida del **proceso**, la emisión del evento y el cierre de la ronda. El arnés incorpora los ficheros del cableado |

**Y dos cosas que no eran fronteras sino errores planos:** `traducir_fallo_de_mutex` tenía tres
tests y **cero llamadores** (retirada; su prueba se reescribió conduciendo `main`, donde además
distingue las dos causas de fallo de exclusión), y el help de `--hasta` prometía una reanudación
que la puerta impide (corregido: se reanuda por `--case-id`).

**Medición tras remediar: 3.880 tests, 0 fallos con dos semillas (777 y 31337); 31/31 mutantes
muertos, cada uno solo por su frontera**, con el arnés ya cubriendo el cableado y sin las dos
muertes vacuas (F19/F20 retirados: sus fronteras dejaron de existir).

### Lo que NO se remedió, declarado uno por uno

No se declara refutado nada de esto: está **abierto**.

1. **`MEJORAS #142` sube de prioridad y su descripción era engañosa.** El `Exit` dentro del bloque
   de mutex vive **casi solo en el modo `libre`** —el que usa el equipo— con **9 salidas**; la rama
   `v1` que remedié apenas podía manifestarlo porque sus etapas capturan `Exception`. Remedié donde
   el defecto no podía darse.
2. **La atomicidad se contrata con un espía de llamada** (L4-01, L6-13): el test comprueba que se
   pasó por `os.replace`, no que ningún estado parcial sea observable. Una escritura en sitio con un
   `os.replace(f, f)` de adorno pasaría.
3. **`os.replace` puede lanzar `PermissionError` en Windows** si otro proceso tiene el destino
   abierto, y nadie lo captura (L4-02); en `cerrar` invierte la semántica.
4. **Un JSON truncado se lee como «primera ronda»** (L4-04): el modo de fallo que el fichero existe
   para detectar es el que no detecta.
5. **`abrir` sobrescribe la evidencia de una ronda anterior sin cerrar** (L1-07, L4-03).
6. **El guard AST de F25 vigila `ast.Raise`**, así que enrutar la salida por un helper lo elude
   (L1-04). Limitación declarada, no cerrada.
7. **Flecos del arnés:** F15 muere 5 de 6 veces por un error de montaje de su fixture y no por su
   frontera (L1-13); F27 espía `os.replace` y sobrevive a quitar el `dir=` de `mkstemp` (L1-12).
8. **`_informar_v1` no tiene frontera** y el campo `parada` del evento puede mentir (L1-15); el
   `details` del evento es subconjunto estricto de lo que se imprime (L5-06).
9. **`fsync` cubre el fichero y no el directorio** (L4-08); el temporal es más largo que el destino,
   con una ventana de `MAX_PATH` (L4-12, SIN VERIFICAR).
10. **Task 11 —la corrida real sobre W-02Q38C— sigue sin ejecutarse.**

**Una tercera ronda sobre esta pieza necesita autorización expresa de Nikolai** (techo duro del
presupuesto). Mi lectura: lo que queda abierto no es del mismo orden que lo remediado —ninguno de
los diez bloquea una apertura ni pierde datos de cliente—, pero son **diez**, y el punto 1 es una
decisión de alcance que tomamos sobre una descripción mía que resultó engañosa. Eso último no lo
arregla una ronda: lo decide él.


---

## 7. Adjudicación de la revisión adversarial (Codex, 2026-09-03) — NO-SHIP, parcial

- **Objeto revisado:** diff **remediado** del Plan 5, commit `80edd24`
- **Ronda:** C
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-03-apertura-v1-plan5-rC-adversarial-review.md`
- **Hallazgos:** 7 recibidos — 7 confirmados, 0 refutados (2 CRÍTICOS, 2 ALTOS, 3 MEDIOS)
- **Remediado en:** los commits posteriores a `80edd24` (HC-01, HC-02 y HC-03); HC-04 a HC-07 abiertos

**Tercera ronda, autorizada expresamente por Nikolai** («codex tiene cupo, relánzalo»). El techo
duro la prohíbe sin esa autorización y aquí consta. **La independencia queda restablecida:** el
revisor es Codex, no el sustituto de R-B. Se sondeó la vía con un `exec` de una línea **antes** de
montar el objeto — lección de esta misma sesión, donde Codex murió a mitad de R-B tras quemar
~153.000 tokens sin dejar informe.

### El hallazgo que justifica la ronda: HC-02, y es un defecto que introduje al remediar

Remediando R-B saqué la publicación del registro durable **fuera** del bloque de mutex, para no
afirmar un éxito que la pérdida del lease desmiente. Con eso abrí una ventana **sin exclusión
ninguna**. Codex lo mutó y lo ejecutó: la intercalación `R1 abre → R1 libera → R2 abre → R1 cierra`
deja el fichero con `ronda_id=R1` y **borra la evidencia de que R2 sigue en curso**; una tercera
corrida ve una ronda cerrada y no avisa. Ese mutante **sobrevivió a los 105 tests contractuales**.

**Y lo que lo hace instructivo, no solo grave:** cuatro líneas encima de esa escritura yo había
escrito el comentario «escribir sin mutex es la violacion que el mutex existe para impedir». Enuncié
la propiedad correcta en prosa y escribí lo contrario en código, en el acto mismo de remediar. Es
[[feedback-nombrar-la-propiedad-no-es-contrato]] cometido dentro de una remediación.

### La frontera, que cierra tres hallazgos con un cambio

**`revalidar → publicar → liberar → salir`, indivisible.**

- La publicación vuelve **dentro** del bloque, como **último acto** (HC-02).
- Precedida de `sesion.revalidar()`: `mutex_sesion.sostenido()` **cede la sesión** y `main` usaba
  `with` sin `as`, así que una pérdida a mitad de una etapa larga pasaba inadvertida hasta la salida,
  con dos escritores sobre el mismo expediente (HC-01).
- El **evento forense va primero** y el `estado.json` después: el `.jsonl` es append-only y
  autoritativo, el JSON es el marcador derivado. Al revés, un append fallido dejaba el estado
  diciendo «terminada» sin rastro alguno (HC-03).
- Fuera del bloque queda **solo informar y salir**, con lo que la propiedad de HA-07 se conserva —y
  ahora sin ninguna escritura a ese lado, que es lo que antes la contradecía.

**Dos cosas que aparecieron al arreglar.** La costura de escritura ya **defendía en profundidad**
(lanza `EscrituraSinMutex` en modo `v1` sin mutex sostenido, y salta antes que la revalidación
nueva); el test se ancló a la propiedad y no al mensaje de una de las dos guardas. Y hubo que
**acotar el guard F25** a `typer.Exit` en vez de cualquier `raise`: su propiedad es «no terminar el
proceso aquí dentro», y un `raise MutexPerdido` deliberado es lo contrario del defecto —prohibirlo
bloqueaba el arreglo correcto—. Queda justificado en el propio test para que no se lea como una
relajación de conveniencia.

**Medición tras remediar: 3.883 tests, 0 fallos con dos semillas; 31/31 mutantes muertos, cada uno
solo por su frontera.**

### Los cuatro que quedan ABIERTOS, confirmados y sin remediar

| Id | Sev. | Qué es | Por qué no se cierra hoy |
|---|---|---|---|
| **HC-04** | ALTO | La **contaminación cruzada** que detecta la atomización va a `report.notas`, y el status solo mira `publicado` y `errores`: con notas y cero errores devuelve `ok`, el OCR sigue y V1 declara la etapa hecha sin pendiente | Es el que más pesa de los cuatro: documentos de otros casos colados van por su **tercera aparición** en este repo. Tocar el vocabulario de status del motor es alcance propio |
| **HC-05** | MEDIO | «El productor clasifica» solo lo pregunta mi adaptador. Otros **cuatro** consumidores de `PullResultV2` reinterpretan el mismo sum type implícito, y `sync_all` llega a imprimir «Sync completado» con errores dentro | El arreglo correcto es del módulo del CRM, compartido con El Contable / El Auditor: pieza propia con su presupuesto |
| **HC-06** | MEDIO | **Cambié el §3 de este plan sin adjudicarlo**: F19 pasó de «hecha con pendiente» a `fallo`. Y el «31/31» es cierto sobre *mi lista*, no sobre *el §3* — faltan F19, F20 y F26 | Es corrección **documental** y de gobernanza, no de código, y su frase da en el clavo: que bloquear sea más prudente no autoriza al diff a cambiar su propia fuente |
| **HC-07** | MEDIO | El «punto fijo material» del E2E es **vacuo**: los tres dobles no escriben nada, así que la foto compara un árbol de un fichero y excluye el único que cambia | Arreglarlo pide dobles que escriban de verdad, o un E2E con OCR real bajo `--runslow` |

**No se pide una cuarta ronda.** Lo que queda son cuatro bloques confirmados, tres de ellos con
alcance fuera de esta pieza, y ninguno bloquea una apertura ni pierde datos de cliente. Lo que sí
hace falta es **decidir HC-04 y HC-06**: el primero porque toca prueba documental, el segundo porque
es una fuente que yo modifiqué sin permiso de nadie.
