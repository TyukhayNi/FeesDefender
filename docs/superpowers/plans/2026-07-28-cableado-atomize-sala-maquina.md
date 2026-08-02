# Cableado de la atomización de correo en la sala de máquina — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que `python -m scripts.sala_maquina apply` atomice el correo del caso **antes** del OCR, deje el resultado declarado en el log de custodia (`atomizado_email` con `status`) y vuelva ruidosa la discrepancia de enumeración de `MEJORAS #98`.

**Architecture:** Un helper nuevo `_atomizar_correo(case_id, case_dir)` en `scripts/sala_maquina.py` (capa de orquestación) llama a `core.email_atomize.pipeline.atomize_dir` con las rutas derivadas del `case_dir` **ya resuelto**, entre `_resolver_caso` y `_construir_plan`. El predicado de conteo (`contar_eml`) y los derivadores de ruta desde `case_dir` viven en el **core** (regla de 3 capas), para que `plan` y `apply` compartan una sola verdad. El motor `core/email_atomize/` **no se toca**.

**Tech Stack:** Python 3.11+, `typer` (CLI), `pytest` (+ `pytest-randomly`, la suite corre en orden aleatorio), stdlib `email` para los `.eml` sintéticos de los tests.

## Global Constraints

- **Fuente única del diseño:** `docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-design.md` (rev. 2). **No reabrir sus decisiones**, en particular el punto de disparo (`scripts/sala_maquina.py::apply`), que sobrevivió a dos revisiones adversariales.
- **Alcance: cableado, no motor.** Ni una línea de `core/email_atomize/*` cambia de comportamiento. Se **añaden** funciones a `core/email_atomize/pipeline.py`; no se modifica ninguna existente salvo por delegación byte-equivalente (`emails_src_dirs`, `emails_out_dir`).
- **Enumeración: `glob`, nunca `rglob`, para decidir.** El pre-scan cuenta lo que el motor **verá** (`glob("*.eml")` por carpeta fuente). `rglob` se usa **solo** para el segundo conteo del aviso. Alinear el criterio hacia abajo es lo que mantiene honesto el no-op y el evento (spec §4.1).
- **Fallo blando para el OCR, duro para el registro:** una excepción del motor **no** aborta el OCR, pero **sí** emite evento con `status: "fallo"` y banner visible (spec §4.4).
- **No se promete frescura.** El consumidor debe leer el `status`. El motor no poda `adjuntos/` ni publica atómicamente (`MEJORAS #99`).
- **Encoding:** todo fichero se lee/escribe en UTF-8 sin BOM explícito (`encoding="utf-8"`), patrón ya vigente en el módulo.
- **Comandos desde la raíz del worktree**, con el venv del repo: `python -m pytest ...`.
- **Suite completa verde antes del PR.** El CI del PR solo corre `leak-scan`; pytest es responsabilidad local.

---

## File Structure

| Fichero | Responsabilidad | Cambio |
|---|---|---|
| `core/email_atomize/pipeline.py` | Motor + derivadores de ruta del caso | **Modificar (aditivo):** `contar_eml`, `emails_src_dirs_de_caso`, `emails_out_dir_de_caso`; `emails_src_dirs`/`emails_out_dir` delegan |
| `core/intake_log.py` | Set cerrado de eventos forenses | **Modificar:** alta de `"atomizado_email"` (26 → 27 eventos) |
| `scripts/sala_maquina.py` | Orquestación del CLI de la sala de máquina | **Modificar:** `_atomizar_correo` + llamada en `apply` + línea/aviso en `plan` |
| `tests/test_email_atomize_pipeline.py` | Tests del motor y sus derivadores | **Modificar:** tests de las 3 funciones nuevas |
| `tests/test_intake_log.py` | Sanity del set de eventos | **Modificar:** `26` → `27` **y el set `expected` completo** (`:337-379`) |
| `tests/test_sala_maquina_cableado_atomize.py` | Contrato del cableado (spec §6): 12 tests con doble + 3 contra el motor real | **Crear** |
| `.claude/skills/organizar-sala-maquina/SKILL.md` | Contrato operativo de la skill | **Modificar:** el `apply` atomiza; qué NO promete |
| `PLAN.md`, `docs/MEJORAS_FUTURAS.md`, `docs/ARQUITECTURA.md` | Gobernanza y acoplamiento | **Modificar** (Task 7) |

Los dos grupos de tests del §6 viven en **un solo fichero** (mismo sujeto, cambian juntos), separados por un comentario de sección.

---

### Task 1: Primitivas del core — conteo y rutas derivadas del `case_dir`

Hoy `emails_src_dirs(case_id)` y `emails_out_dir(case_id)` **re-resuelven** el caso (`path_for(resolve_ref(...))`). El CLI ya trae el `case_dir` resuelto por `_resolver_caso`, y resolver tres veces (conteo, fuentes, salida) es superficie gratuita (spec §4.6). Se extrae la parte pura y `contar_eml` se añade aquí, no en el CLI, para que `plan` y `apply` no deriven.

**Files:**
- Modify: `core/email_atomize/pipeline.py:281-299` (bloque `emails_src_dirs` / `emails_out_dir`; `atomize_case` en `:302-303` **no se toca**)
- Test: `tests/test_email_atomize_pipeline.py` (añadir al final)

**Interfaces:**
- Consumes: `core.intake_lotes.PATRON_LOTE` (ya importado en el módulo), `core.casos.case_locator.{path_for,resolve_ref}`.
- Produces:
  - `emails_src_dirs_de_caso(case_dir: Path | str) -> list[Path]`
  - `emails_out_dir_de_caso(case_dir: Path | str) -> Path`
  - `contar_eml(fuentes: Iterable[Path | str]) -> tuple[int, int]` → `(n_top, n_rec)`
  - `emails_src_dirs(case_id: str) -> list[Path]` y `emails_out_dir(case_id: str) -> Path` conservan firma y comportamiento.

- [ ] **Step 1: Write the failing tests**

Añadir al final de `tests/test_email_atomize_pipeline.py`:

```python
# --- Derivadores de ruta y conteo (cableado, spec §4.1/§4.6) ------------------

def test_contar_eml_distingue_nivel_superior_de_recursivo(tmp_path):
    src = tmp_path / "2026-07-28_email_01"
    (src / "mensaje_con_adjunto").mkdir(parents=True)
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (src / "b.eml").write_bytes(_msg("<b@x>", "Dos"))
    # El layout que deja `--extraer-adjuntos`: el .eml baja a una subcarpeta y el
    # motor (glob, no rglob) no lo verá — MEJORAS #98.
    (src / "mensaje_con_adjunto" / "c.eml").write_bytes(_msg("<c@x>", "Tres"))

    assert P.contar_eml([src]) == (2, 3)


def test_contar_eml_suma_fuentes_y_tolera_inexistentes(tmp_path):
    lote = tmp_path / "2026-07-28_email_01"
    legacy = tmp_path / "03_Email"
    lote.mkdir()
    legacy.mkdir()
    (lote / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (legacy / "b.eml").write_bytes(_msg("<b@x>", "Dos"))

    assert P.contar_eml([lote, legacy, tmp_path / "no_existe"]) == (2, 2)
    assert P.contar_eml([]) == (0, 0)


def test_emails_src_dirs_de_caso_no_resuelve_el_caso(tmp_path, monkeypatch):
    from core.casos import case_locator

    def _prohibido(*a, **k):
        raise AssertionError("re-localización del caso: debe partir del case_dir dado")

    monkeypatch.setattr(case_locator, "path_for", _prohibido)
    monkeypatch.setattr(case_locator, "resolve_ref", _prohibido)

    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
    (case_dir / "00_Input" / "2026-07-28_email_01").mkdir(parents=True)
    (case_dir / "00_Input" / "2026-07-20_whatsapp_01").mkdir()   # otra fuente: se ignora
    (case_dir / "00_Input" / "03_Email").mkdir()                 # cajón legacy: se incluye

    fuentes = P.emails_src_dirs_de_caso(case_dir)
    assert [f.name for f in fuentes] == ["2026-07-28_email_01", "03_Email"]
    assert P.emails_out_dir_de_caso(case_dir) == case_dir / "01_Procesado" / "Emails"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_email_atomize_pipeline.py -k "contar_eml or de_caso" -v
```

Expected: 3 FAILED con `AttributeError: module 'core.email_atomize.pipeline' has no attribute 'contar_eml'` (y `emails_src_dirs_de_caso`).

- [ ] **Step 3: Write the implementation**

En `core/email_atomize/pipeline.py`, **reemplazar** el bloque actual `emails_src_dirs` / `emails_out_dir` (líneas 281-299) por:

```python
def emails_src_dirs_de_caso(case_dir: Path | str) -> list[Path]:
    """Fuentes de .eml de un caso YA localizado: lotes ``email`` de ``00_Input/`` +
    cajón legacy ``03_Email``.

    Parte del ``case_dir`` y no vuelve a resolver el caso: el llamante (CLI de la sala
    de máquina) ya lo resolvió una vez y resolver tres veces es superficie gratuita.
    """
    input_dir = Path(case_dir) / "00_Input"
    bases: list[Path] = []
    if input_dir.is_dir():
        bases = sorted(
            (d for d in input_dir.iterdir() if d.is_dir()
             and (m := PATRON_LOTE.match(d.name)) and m.group(2) == "email"),
            key=lambda d: d.name)
    legacy = input_dir / "03_Email"
    if legacy.is_dir():
        bases.append(legacy)
    return bases


def emails_out_dir_de_caso(case_dir: Path | str) -> Path:
    """Salida de la atomización de un caso YA localizado."""
    return Path(case_dir) / "01_Procesado" / "Emails"


def contar_eml(fuentes: Iterable[Path | str]) -> tuple[int, int]:
    """``(n_top, n_rec)``: los .eml que el motor VERÁ y los que realmente HAY.

    ``n_top`` usa el MISMO enumerador que el motor (``glob("*.eml")``, no recursivo —
    ``extract.iter_avistamientos``), así que es el conteo autoritativo para decidir
    no-op y para el evento. ``n_rec`` (``rglob``) solo sirve para delatar la
    discrepancia de `MEJORAS #98`: con ``--extraer-adjuntos``, el .eml de un mensaje
    con adjuntos baja a una subcarpeta y desaparece del atomizador sin error.
    ``n_rec >= n_top`` siempre. La ceguera a ``.EML`` en mayúsculas es la misma que la
    del motor, a propósito: los dos conteos han de medir lo mismo.
    """
    n_top = n_rec = 0
    for f in fuentes:
        base = Path(f)
        if not base.is_dir():
            continue
        n_top += sum(1 for _ in base.glob("*.eml"))
        n_rec += sum(1 for _ in base.rglob("*.eml"))
    return n_top, n_rec


def emails_src_dirs(case_id: str) -> list[Path]:
    """Fuentes de .eml del caso: lotes email de 00_Input/ + cajón legacy 03_Email."""
    from core.casos.case_locator import path_for, resolve_ref
    return emails_src_dirs_de_caso(path_for(resolve_ref(case_id)))


def emails_out_dir(case_id: str) -> Path:
    from core.casos.case_locator import path_for, resolve_ref
    return emails_out_dir_de_caso(path_for(resolve_ref(case_id)))
```

Y añadir `Iterable` al import de tipos en la cabecera del módulo (línea 10, junto a `from pathlib import Path`):

```python
from collections.abc import Iterable
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_email_atomize_pipeline.py tests/test_atomize_emails_cli.py -q
```

Expected: todos PASSED (los tests existentes de `emails_src_dirs`/`atomize_case` siguen verdes: la delegación es byte-equivalente).

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/pipeline.py tests/test_email_atomize_pipeline.py
git commit -m "feat(email_atomize): contar_eml + derivadores de ruta desde case_dir"
```

---

### Task 2: Alta del evento forense `atomizado_email`

`INTAKE_EVENTS` es un set cerrado: `append_event` lanza `ValueError` con un evento no declarado. Sin esta alta, el cableado revienta en la primera corrida real.

**Files:**
- Modify: `core/intake_log.py:9` (docstring M10-Q1) y `core/intake_log.py:66-72` (el set)
- Modify: `tests/test_intake_log.py:332-334` (sanity de longitud) **y `:337-379` (el set `expected` completo)**

> **DOS tests, no uno.** `test_intake_events_contiene_los_canonicos` compara
> `il.INTAKE_EVENTS == expected` con un literal que termina en `"archivado"`: tocar solo
> el de longitud deja la suite roja por el elemento de más. (Hallazgo de la revisión
> adversarial, verificado leyendo el fichero.)

**Interfaces:**
- Consumes: nada.
- Produces: `"atomizado_email"` como miembro válido de `core.intake_log.INTAKE_EVENTS`; `len(INTAKE_EVENTS) == 27`.

- [ ] **Step 1: Write the failing test**

En `tests/test_intake_log.py`, sustituir el cuerpo del test de sanity (línea 332):

```python
def test_intake_events_es_frozenset_con_24_eventos(il):
    assert isinstance(il.INTAKE_EVENTS, frozenset)
    assert len(il.INTAKE_EVENTS) == 27
    assert "atomizado_email" in il.INTAKE_EVENTS
```

(El nombre de la función dice «24»: deriva preexistente, no se toca aquí — renombrarla mezclaría ruido en el diff.)

Y en `test_intake_events_contiene_los_canonicos`, añadir la entrada al final del literal `expected` (tras `"archivado",`) y una frase al docstring:

```python
        "archivado",
        "atomizado_email",
    }
    assert il.INTAKE_EVENTS == expected
```

```
    ``atomizado_email`` con el cableado de la atomización de correo en la sala de
    máquina (2026-07-28).
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_intake_log.py -k "events_es_frozenset or contiene_los_canonicos" -v
```

Expected: 2 FAILED — `assert 26 == 27` y el `==` del set (falta `atomizado_email` en producción).

- [ ] **Step 3: Write the implementation**

En `core/intake_log.py`, añadir al final del set `INTAKE_EVENTS` (tras la entrada `"archivado"`, dentro de las llaves):

```python
    "atomizado_email",          # atomización de correo encadenada por la sala de máquina
                                 # (spec 2026-07-27 §4.5): details = {"status": ok|parcial|fallo,
                                 # "eml_nivel_superior": n, "eml_totales": n, + contadores del
                                 # AtomizeReport si el motor terminó}. NO lleva "files".
```

Y en el docstring del módulo, línea 9: `- M10-Q1: 26 tipos de evento permitidos` → `- M10-Q1: 27 tipos de evento permitidos`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_intake_log.py -q
```

Expected: todos PASSED.

- [ ] **Step 5: Commit**

```bash
git add core/intake_log.py tests/test_intake_log.py
git commit -m "feat(intake_log): alta del evento atomizado_email (26->27)"
```

---

### Task 3: `_atomizar_correo` — orden, no-op y reconciliación

El corazón del cableado. Cubre los tests 1, 2, 3 y 8 del §6. El evento y los `status` llegan en la Task 4 (aquí el helper aún no registra nada), para que un revisor pueda rechazar el contrato del evento sin rechazar el orden.

**Files:**
- Modify: `scripts/sala_maquina.py` (imports, helper nuevo tras `_resolver_caso`, llamada en `apply`)
- Test: `tests/test_sala_maquina_cableado_atomize.py` (crear)

**Interfaces:**
- Consumes: `core.email_atomize.pipeline.{emails_src_dirs_de_caso, emails_out_dir_de_caso, contar_eml, atomize_dir}` (Task 1); `cli._resolver_caso(case_id) -> (case_id, case_dir)`.
- Produces: `scripts.sala_maquina._atomizar_correo(case_id: str, case_dir: Path) -> None`; el módulo expone el pipeline como `cli.atomize` (los tests parchean `cli.atomize.atomize_dir`).

- [ ] **Step 1: Write the failing tests**

Crear `tests/test_sala_maquina_cableado_atomize.py`:

```python
"""Cableado de la atomización de correo en la sala de máquina (spec §6).

Dos grupos, como manda el contrato de tests: (1) con doble del motor, para el orden y
el contrato del evento; (2) contra el MOTOR REAL, porque la rev. 1 de la spec tenía 7
tests con doble que pasaban todos sobre un defecto real de enumeración.
"""
from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import pytest

import scripts.sala_maquina as cli
from core.email_atomize.pipeline import AtomizeReport


def _eml(mid: str, subj: str = "Oferta", attachments=None) -> bytes:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subj
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "propietario@example.invalid"
    m["To"] = "agencia@example.invalid"
    m.set_content("Cuerpo de prueba.")
    for fn, mime, data in attachments or []:
        maint, _, sub = mime.partition("/")
        m.add_attachment(data, maintype=maint, subtype=sub, filename=fn)
    return m.as_bytes()


@pytest.fixture
def caso(tmp_path, monkeypatch):
    """Caso en `tmp_path` con OCR y log neutralizados.

    Devuelve `(case_dir, eventos)`. El nombre de carpeta lleva W-code entre paréntesis
    para que el detector de contaminación cruzada no calle por `(SIN REFERENCIA)`.
    """
    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
    (case_dir / "00_Input" / "03_Email").mkdir(parents=True)
    eventos: list[tuple[str, dict]] = []
    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli, "append_event",
                        lambda cid, ev, *, details=None: eventos.append((ev, details or {})))
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
    return case_dir, eventos


def _evento(eventos, nombre="atomizado_email"):
    return [d for ev, d in eventos if ev == nombre]


# --- Grupo 1: con doble del motor --------------------------------------------

def test_atomiza_antes_de_construir_el_plan_de_ocr(caso, monkeypatch):
    # La Task 4 AMPLÍA este test para exigir que el evento y las notas existan también
    # antes del OCR: la secuencia de etapas por sí sola no lo mata.
    case_dir, _ = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    orden: list[str] = []

    def fake_atomize(*a, **k):
        orden.append("atomize")
        return AtomizeReport(mensajes=1)

    def fake_plan(cd, force):
        orden.append("plan")
        return []

    def fake_ejecutar(*a, **k):
        orden.append("ejecutar")
        return []

    monkeypatch.setattr(cli.atomize, "atomize_dir", fake_atomize)
    monkeypatch.setattr(cli, "_construir_plan", fake_plan)
    monkeypatch.setattr(cli.sm, "ejecutar", fake_ejecutar)

    cli.apply("W-TEST99")

    assert orden == ["atomize", "plan", "ejecutar"]


def test_noop_sin_eml_y_sin_arbol_previo(caso, monkeypatch):
    case_dir, eventos = caso
    llamadas: list[int] = []

    def fake_atomize(*a, **k):
        llamadas.append(1)
        return AtomizeReport()

    monkeypatch.setattr(cli.atomize, "atomize_dir", fake_atomize)

    cli.apply("W-TEST99")

    assert llamadas == []                                    # el motor no se invoca
    assert not (case_dir / "01_Procesado" / "Emails").exists()   # no se siembran carpetas
    assert _evento(eventos) == []                            # no se emite evento


def test_con_arbol_previo_y_cero_eml_si_se_atomiza(caso, monkeypatch):
    # La retirada de correos (remedio real de W-02VUDR contra la contaminación) debe
    # reflejarse: con árbol previo se llama al motor aunque no quede un solo .eml.
    case_dir, eventos = caso
    (case_dir / "01_Procesado" / "Emails" / "mensajes").mkdir(parents=True)
    llamadas: list[tuple] = []

    def fake_atomize(fuentes, out, *, case_dir=None):
        llamadas.append((list(fuentes), out, case_dir))
        return AtomizeReport()

    monkeypatch.setattr(cli.atomize, "atomize_dir", fake_atomize)

    cli.apply("W-TEST99")

    assert len(llamadas) == 1
    fuentes, out, cd = llamadas[0]
    # Las fuentes también se comprueban: pasar `[]` o una ruta equivocada dejaría este
    # test verde y la reconciliación sin efecto real.
    assert fuentes == [case_dir / "00_Input" / "03_Email"]
    assert out == case_dir / "01_Procesado" / "Emails"
    assert cd == case_dir            # case_dir explícito: no se infiere de out.parent.parent


def test_el_caso_se_resuelve_una_sola_vez(caso, monkeypatch):
    # Si el helper llamara a `atomize_case(case_id)` en vez de a `atomize_dir` con las
    # rutas derivadas, volvería a localizar el caso (spec §4.6).
    from core.casos import case_locator
    case_dir, _ = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: AtomizeReport(mensajes=1))

    def prohibido(*a, **k):
        raise AssertionError("re-localización del caso dentro del helper")

    # `resolve_ref` (que sí corre en `_resolver_caso`) NO llama a `path_for` (verificado
    # en `case_locator.list_cases`), así que cualquier llamada a `path_for` viene de un
    # `atomize_case(case_id)` indebido.
    monkeypatch.setattr(case_locator, "path_for", prohibido)
    # Y `resolve_ref` exactamente una vez: la vía barata de re-resolver también cuenta.
    real_resolve = case_locator.resolve_ref
    refs: list[str] = []

    def contar_resolve(ref):
        refs.append(ref)
        return real_resolve(ref)

    monkeypatch.setattr(case_locator, "resolve_ref", contar_resolve)

    cli.apply("W-TEST99")   # no debe lanzar

    assert refs == ["W-TEST99"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_sala_maquina_cableado_atomize.py -v
```

Expected: 4 FAILED — `AttributeError: module 'scripts.sala_maquina' has no attribute 'atomize'`.

- [ ] **Step 3: Write the implementation**

En `scripts/sala_maquina.py`, añadir el import tras `from core.casos import case_locator` (línea 15):

```python
from core.email_atomize import pipeline as atomize
```

Añadir el helper **inmediatamente después** de `_resolver_caso` (tras la línea 121):

```python
def _atomizar_correo(case_id: str, case_dir: Path) -> None:
    """Atomiza el correo del caso ANTES del OCR (cableado, spec 2026-07-27 §4).

    Garantiza por código el orden intake → atomización → sala de máquina, en vez de
    dejarlo en la memoria del operador, y hace correr el detector de contaminación
    cruzada en toda corrida. Recibe el `case_dir` YA resuelto y compone las rutas desde
    él: no vuelve a localizar el caso (§4.6).

    Lo que este paso NO promete: que `01_Procesado/Emails` quede fresco y consumible
    sin comprobar nada. El motor no poda `adjuntos/` ni publica de forma atómica
    (`MEJORAS #99`), así que el consumidor DEBE leer el `status` del evento
    `atomizado_email`.
    """
    fuentes = atomize.emails_src_dirs_de_caso(case_dir)
    out = atomize.emails_out_dir_de_caso(case_dir)
    n_top, n_rec = atomize.contar_eml(fuentes)

    # No-op estricto: sin correo Y sin árbol previo no se llama al motor, porque
    # `atomize_dir` hace mkdir de mensajes/ y adjuntos/ INCONDICIONALMENTE y sembraría
    # carpetas vacías en todo caso sin correo. Con árbol previo SÍ se llama aunque
    # n_top == 0: es la única vía en alcance para que la retirada de correos se refleje
    # (poda de `mensajes/`; `adjuntos/` NO se poda — `MEJORAS #99`).
    if n_top == 0 and not out.exists():
        return

    report = atomize.atomize_dir(fuentes, out, case_dir=case_dir)
    typer.echo(f"Correo atomizado: {report.resumen()}")
```

Y en `apply`, insertar la llamada entre el preflight de visión y el plan (tras la línea 169):

```python
    _atomizar_correo(case_id, case_dir)   # cableado: atomizar ANTES del OCR (spec §4)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_sala_maquina_cableado_atomize.py tests/test_sala_maquina_ejecutar.py -q
```

Expected: todos PASSED (los tests existentes de `apply` no tienen `.eml` en sus fixtures → no-op, sin cambio de comportamiento).

- [ ] **Step 5: Commit**

```bash
git add scripts/sala_maquina.py tests/test_sala_maquina_cableado_atomize.py
git commit -m "feat(sala_maquina): atomiza el correo antes del OCR (orden + no-op + reconciliacion)"
```

---

### Task 4: Evento forense con `status`, fallo blando y banner

Cubre los tests 4, 5 y 6 del §6. El fallo blando **sin evento** (rev. 1 de la spec) degradaría una avería hoy visible —el CLI manual escupe el traceback y el operador para— en una invisible, justo donde el motor puede renumerar IDs congelados.

**Files:**
- Modify: `scripts/sala_maquina.py` (`_atomizar_correo`, constante de banner)
- Modify: `tests/test_sala_maquina_cableado_atomize.py` (añadir al grupo 1)

**Interfaces:**
- Consumes: `AtomizeReport.{mensajes, adjuntos_unicos, reconstruidos_b, citas_a_revision, upgrades, notas, errores, resumen()}`; `cli.append_event`.
- Produces: evento `atomizado_email` con payload
  `{"status": "ok"|"parcial"|"fallo", "eml_nivel_superior": int, "eml_totales": int}`
  más, **solo si el motor terminó**, `{"mensajes", "adjuntos_unicos", "reconstruidos_b", "citas_a_revision", "upgrades", "notas", "errores"}`.

- [ ] **Step 1: Write the failing tests**

Añadir a `tests/test_sala_maquina_cableado_atomize.py`, en el grupo 1:

```python
def test_fallo_del_motor_no_aborta_el_ocr_y_emite_evento(caso, monkeypatch, capsys):
    case_dir, eventos = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    ejecutado: list[int] = []

    def boom(*a, **k):
        raise RuntimeError("motor roto")

    def fake_ejecutar(*a, **k):
        ejecutado.append(1)
        return []

    monkeypatch.setattr(cli.atomize, "atomize_dir", boom)
    monkeypatch.setattr(cli.sm, "ejecutar", fake_ejecutar)

    cli.apply("W-TEST99")

    assert ejecutado == [1]                      # el OCR corre igual (fallo blando)
    # Igualdad EXACTA: un payload de fallo sin los dos conteos de .eml también sería un
    # rastro mutilado, y con `assert status == "fallo"` pasaría igual.
    assert _evento(eventos)[0] == {
        "status": "fallo",
        "eml_nivel_superior": 1, "eml_totales": 1,
        "errores": ["RuntimeError: motor roto"],
    }
    err = capsys.readouterr().err
    assert "la atomización de correo FALLÓ" in err


def test_status_parcial_cuando_el_motor_termina_con_errores(caso, monkeypatch):
    case_dir, eventos = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: AtomizeReport(
        mensajes=2, errores=["<x@y>: cabecera ilegible"]))

    cli.apply("W-TEST99")

    # Igualdad exacta también aquí: el motor TERMINÓ, así que el payload debe llevar
    # todos los contadores del report — no solo `status` y `errores`.
    assert _evento(eventos)[0] == {
        "status": "parcial",
        "eml_nivel_superior": 1, "eml_totales": 1,
        "mensajes": 2, "adjuntos_unicos": 0, "reconstruidos_b": 0,
        "citas_a_revision": 0, "upgrades": 0,
        "notas": [], "errores": ["<x@y>: cabecera ilegible"],
    }


def test_payload_atado_a_los_campos_reales_del_report(caso, monkeypatch, capsys):
    # El doble devuelve un AtomizeReport REAL (no un SimpleNamespace): un campo mal
    # escrito en el payload rompe este test. Igualdad exacta del dict a propósito.
    case_dir, eventos = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    report = AtomizeReport(mensajes=413, adjuntos_unicos=162, reconstruidos_b=136,
                           citas_a_revision=43, upgrades=8,
                           notas=["W-code ajeno en 1 mensaje: W-00000"])
    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: report)

    cli.apply("W-TEST99")

    assert _evento(eventos)[0] == {
        "status": "ok",
        "eml_nivel_superior": 1, "eml_totales": 1,
        "mensajes": 413, "adjuntos_unicos": 162, "reconstruidos_b": 136,
        "citas_a_revision": 43, "upgrades": 8,
        "notas": ["W-code ajeno en 1 mensaje: W-00000"], "errores": [],
    }
    # objetivo 3 de la spec: la contaminación cruzada se ve ANTES del OCR
    assert "W-code ajeno" in capsys.readouterr().err


def test_un_fallo_de_log_no_aborta_el_ocr(caso, monkeypatch, capsys):
    case_dir, _ = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    ejecutado: list[int] = []

    def log_roto(cid, ev, *, details=None):
        # SOLO el evento de atomización. `apply` emite después `procesado_sala_maquina`
        # con un `append_event` SIN captura (`scripts/sala_maquina.py:195`): un doble que
        # lanzara para todo evento haría fallar este test por una vía ajena al cableado
        # (y así estaba mal escrito en la primera versión del plan).
        if ev == "atomizado_email":
            raise OSError("disco lleno")

    def fake_ejecutar(*a, **k):
        ejecutado.append(1)
        return []

    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: AtomizeReport(mensajes=1))
    monkeypatch.setattr(cli, "append_event", log_roto)
    monkeypatch.setattr(cli.sm, "ejecutar", fake_ejecutar)

    cli.apply("W-TEST99")   # no debe propagar OSError

    assert ejecutado == [1]
    assert "no se pudo registrar el evento atomizado_email" in capsys.readouterr().err
```

Y **añadir estas dos líneas al final** de `test_con_arbol_previo_y_cero_eml_si_se_atomiza`
(Task 3), que hasta ahora solo comprobaba la llamada — el evento no existía todavía:

```python
    assert _evento(eventos)[0]["status"] == "ok"          # reconciliación declarada
    assert _evento(eventos)[0]["eml_nivel_superior"] == 0
```

**Y ampliar el test de orden de la Task 3** — `test_atomiza_antes_de_construir_el_plan_de_ocr`
pasa a exigir que el rastro forense y el aviso de contaminación existan **antes** del OCR.
Sustituir su cuerpo completo por:

```python
def test_atomiza_antes_de_construir_el_plan_de_ocr(caso, monkeypatch):
    """Orden real, incluido el rastro: evento y notas ANTES de arrancar el OCR.

    La secuencia `atomize → plan → ejecutar` por sí sola NO basta: una implementación que
    guarde el report en memoria, corra el OCR (~1 h 40) y escriba el evento al final
    pasaría, dejando sin rastro una corrida que muere a mitad (spec §4.5) y sin ver la
    contaminación cruzada hasta después del OCR (objetivo 3 de la spec).
    """
    case_dir, _ = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    orden: list[str] = []
    real_echo = cli.typer.echo

    def fake_atomize(*a, **k):
        orden.append("atomize")
        return AtomizeReport(mensajes=1, notas=["W-code ajeno en 1 mensaje: W-00000"])

    def fake_plan(cd, force):
        orden.append("plan")
        return []

    def fake_ejecutar(*a, **k):
        orden.append("ejecutar")
        return []

    def fake_evento(cid, ev, *, details=None):
        orden.append(f"evento:{ev}")

    def fake_echo(msg="", **kw):
        if "NOTA:" in str(msg):
            orden.append("nota")
        real_echo(msg, **kw)

    monkeypatch.setattr(cli.atomize, "atomize_dir", fake_atomize)
    monkeypatch.setattr(cli, "_construir_plan", fake_plan)
    monkeypatch.setattr(cli.sm, "ejecutar", fake_ejecutar)
    monkeypatch.setattr(cli, "append_event", fake_evento)
    monkeypatch.setattr(cli.typer, "echo", fake_echo)

    cli.apply("W-TEST99")

    # Las etapas, en orden y sin duplicados.
    assert [x for x in orden if x in ("atomize", "plan", "ejecutar")] == \
        ["atomize", "plan", "ejecutar"]
    # Rastro y aviso ANTES del OCR. No se fija el orden entre nota y evento: los dos
    # cumplen la spec mientras precedan al plan.
    assert orden.index("evento:atomizado_email") < orden.index("plan")
    assert orden.index("nota") < orden.index("plan")
    # Y el evento del OCR después: nada se ha invertido por el camino.
    assert orden.index("evento:procesado_sala_maquina") > orden.index("ejecutar")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_sala_maquina_cableado_atomize.py -v
```

Expected: los 4 nuevos + el de reconciliación FAILED (`IndexError: list index out of range` al buscar el evento; y `RuntimeError: motor roto` propagado en el primero).

- [ ] **Step 3: Write the implementation**

En `scripts/sala_maquina.py`, añadir la constante del banner de fallo junto a `_STATE`/`_COBERTURA` (tras la línea 22):

```python
_SEP = "=" * 72

_BANNER_FALLO_ATOMIZE = (
    f"\n{_SEP}\n"
    "AVISO: la atomización de correo FALLÓ ({tipo}: {exc}).\n"
    "El OCR continúa (no depende de ella), pero `01_Procesado/Emails` puede haber\n"
    "quedado a medias con el registro de IDs sin salvar (MEJORAS #99): revísalo antes\n"
    f"de citar MSG-ids nuevos.\n{_SEP}"
)
```

Y **sustituir** las dos últimas líneas de `_atomizar_correo` (el `report = ...` + `typer.echo(...)` de la Task 3) por:

```python
    details: dict[str, object] = {"eml_nivel_superior": n_top, "eml_totales": n_rec}
    try:
        report = atomize.atomize_dir(fuentes, out, case_dir=case_dir)
    except Exception as exc:  # noqa: BLE001 — el OCR no depende de la atomización
        # Fallo BLANDO para el OCR (una corrida dura ~1h40 y no depende de esto) pero
        # DURO para el registro: sin evento, este cableado convertiría una avería hoy
        # ruidosa (traceback del CLI manual) en silenciosa. No se fabrican contadores:
        # si el motor no terminó, el payload no finge saber cuántos mensajes hay.
        details["status"] = "fallo"
        details["errores"] = [f"{type(exc).__name__}: {exc}"]
        typer.echo(_BANNER_FALLO_ATOMIZE.format(tipo=type(exc).__name__, exc=exc), err=True)
    else:
        details["status"] = "parcial" if report.errores else "ok"
        details.update({
            "mensajes": report.mensajes,
            "adjuntos_unicos": report.adjuntos_unicos,
            "reconstruidos_b": report.reconstruidos_b,
            "citas_a_revision": report.citas_a_revision,
            "upgrades": report.upgrades,
            "notas": list(report.notas),
            "errores": list(report.errores),
        })
        typer.echo(f"Correo atomizado ({details['status']}): {report.resumen()}")
        for nota in report.notas:
            # Contaminación cruzada por W-code y vistas rotas: a stderr, ANTES del OCR,
            # para que el operador pueda abortar y limpiar `00_Input`.
            typer.echo(f"NOTA: {nota}", err=True)

    # Se emite ANTES de arrancar el OCR: si la corrida larga muere, el rastro ya está
    # en disco. Un fallo de log tampoco aborta el OCR.
    try:
        append_event(case_id, "atomizado_email", details=details)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"AVISO: no se pudo registrar el evento atomizado_email: {exc}", err=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_sala_maquina_cableado_atomize.py -q
```

Expected: 8 PASSED.

- [ ] **Step 5: Commit**

```bash
git add scripts/sala_maquina.py tests/test_sala_maquina_cableado_atomize.py
git commit -m "feat(sala_maquina): evento atomizado_email con status + fallo blando con banner"
```

---

### Task 5: Aviso de correo invisible (`MEJORAS #98`) y `plan`/`reforzar` sin atomizar

Sin el aviso, este cableado **propagaría** la ceguera de `--extraer-adjuntos` con apariencia de éxito. Cubre el test 7 del §6 y la mitad con doble del test 9.

**Files:**
- Modify: `scripts/sala_maquina.py` (constante `_AVISO_EML_INVISIBLE`, uso en `_atomizar_correo`, línea informativa + aviso en `plan`)
- Modify: `tests/test_sala_maquina_cableado_atomize.py`

**Interfaces:**
- Consumes: `atomize.contar_eml`, `atomize.emails_src_dirs_de_caso` (Task 1).
- Produces: aviso por `stderr` en `apply` y `plan` cuando `n_rec > n_top`; línea `  correo: N .eml (se atomizarán en apply)` por `stdout` en `plan` cuando `n_top > 0`.

- [ ] **Step 1: Write the failing tests**

Añadir a `tests/test_sala_maquina_cableado_atomize.py`, en el grupo 1:

```python
def test_aviso_cuando_hay_eml_en_subcarpetas(caso, monkeypatch, capsys):
    case_dir, eventos = caso
    src = case_dir / "00_Input" / "03_Email"
    (src / "a.eml").write_bytes(_eml("<a@x>"))
    (src / "mensaje_con_adjunto").mkdir()
    (src / "mensaje_con_adjunto" / "b.eml").write_bytes(_eml("<b@x>"))
    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: AtomizeReport(mensajes=1))

    cli.apply("W-TEST99")

    err = capsys.readouterr().err
    assert "1 .eml viven en subcarpetas" in err
    assert "MEJORAS #98" in err
    d = _evento(eventos)[0]
    assert (d["eml_nivel_superior"], d["eml_totales"]) == (1, 2)


def test_sin_discrepancia_no_hay_aviso(caso, monkeypatch, capsys):
    # Prueba NEGATIVA: un aviso que salte siempre es tan inútil como no tenerlo, y el
    # test positivo de arriba pasaría igual.
    case_dir, _ = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: AtomizeReport(mensajes=1))

    cli.apply("W-TEST99")

    assert "viven en subcarpetas" not in capsys.readouterr().err


def test_plan_no_atomiza_pero_informa_y_avisa(caso, monkeypatch, capsys):
    case_dir, eventos = caso
    src = case_dir / "00_Input" / "03_Email"
    (src / "a.eml").write_bytes(_eml("<a@x>"))
    (src / "b.eml").write_bytes(_eml("<b@x>"))
    (src / "sub").mkdir()
    (src / "sub" / "c.eml").write_bytes(_eml("<c@x>"))

    def prohibido(*a, **k):
        raise AssertionError("`plan` es preview: no debe atomizar")

    monkeypatch.setattr(cli.atomize, "atomize_dir", prohibido)

    cli.plan("W-TEST99")

    cap = capsys.readouterr()
    assert "correo: 2 .eml (se atomizarán en apply)" in cap.out
    assert "1 .eml viven en subcarpetas" in cap.err
    assert _evento(eventos) == []
    # Prohibir `atomize_dir` no basta: `plan` tampoco debe escribir en el árbol por su
    # cuenta. Es preview.
    assert not (case_dir / "01_Procesado" / "Emails").exists()


def test_reforzar_no_atomiza(caso, monkeypatch, capsys):
    from core import sala_maquina as sm
    from core.utils import file_sha256
    case_dir, _ = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    drive = case_dir / "00_Input" / "01_Drive EV"
    drive.mkdir(parents=True)
    doc = drive / "escaneo.pdf"
    doc.write_bytes(b"%PDF-1.4 escaneo sin texto")
    sha = file_sha256(doc)
    cli._guardar_cobertura(case_dir, [sm.DocCobertura(
        slug=f"escaneo__{sha[:8]}", rel_path="01_Drive EV/escaneo.pdf", metodo="ocr",
        estado="low", chars=10, ocr=True, nota="OCR pobre", sha256=sha)])

    def prohibido(*a, **k):
        raise AssertionError("`reforzar` no debe atomizar")

    monkeypatch.setattr(cli.atomize, "atomize_dir", prohibido)
    monkeypatch.setattr(cli.sm, "vision_cableada", lambda: True)

    cli.reforzar("W-TEST99")

    assert "Reforzados" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_sala_maquina_cableado_atomize.py -k "aviso or plan_no_atomiza or reforzar" -v
```

Expected: los dos primeros FAILED (`assert "1 .eml viven en subcarpetas" in err` → cadena ausente; y en `plan`, falta la línea `correo:`). `test_reforzar_no_atomiza` debe PASAR ya (`reforzar` nunca llamó al motor) — es un test de regresión que fija la invariante.

- [ ] **Step 3: Write the implementation**

En `scripts/sala_maquina.py`, añadir junto a `_BANNER_FALLO_ATOMIZE`:

```python
_AVISO_EML_INVISIBLE = (
    f"\n{_SEP}\n"
    "AVISO: {n} .eml viven en subcarpetas y el atomizador NO los verá (MEJORAS #98).\n"
    "Causa típica: exportación con --extraer-adjuntos. Son justo los mensajes con\n"
    f"adjuntos. El conteo del evento lo deja registrado.\n{_SEP}"
)
```

En `_atomizar_correo`, insertar **justo después** de `n_top, n_rec = atomize.contar_eml(fuentes)`:

```python
    if n_rec > n_top:
        # No arregla la ceguera (es motor, MEJORAS #98): la vuelve ruidosa. Sin esto,
        # el cableado propagaría el agujero con apariencia de éxito.
        typer.echo(_AVISO_EML_INVISIBLE.format(n=n_rec - n_top), err=True)
```

En `plan`, insertar tras el bucle de rutas (tras la línea `typer.echo(f"  {ruta}: {n}")`, antes del bloque de pre-detección de bundles):

```python
    # Preview del cableado: `plan` NO atomiza (es preview), solo informa de lo que
    # `apply` atomizará, con el MISMO contador que usa `apply` (spec §4.7).
    n_top, n_rec = atomize.contar_eml(atomize.emails_src_dirs_de_caso(case_dir))
    if n_top:
        typer.echo(f"  correo: {n_top} .eml (se atomizarán en apply)")
    if n_rec > n_top:
        typer.echo(_AVISO_EML_INVISIBLE.format(n=n_rec - n_top), err=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_sala_maquina_cableado_atomize.py -q
```

Expected: 12 PASSED.

- [ ] **Step 5: Commit**

```bash
git add scripts/sala_maquina.py tests/test_sala_maquina_cableado_atomize.py
git commit -m "feat(sala_maquina): aviso de .eml invisibles (#98) + preview en plan"
```

---

### Task 6: Tests contra el motor REAL (enumeración, transición a cero, evento válido)

Los 7 tests con doble de la rev. 1 pasaban **todos** sobre un defecto real: un lote con `mensaje_con_adjunto/mensaje.eml` donde el pre-scan contaba 1 y el motor encontraba 0. Estos tres cierran esa clase de agujero.

**Files:**
- Modify: `tests/test_sala_maquina_cableado_atomize.py` (grupo 2, sin parchear `atomize_dir` ni `append_event`)

**Interfaces:**
- Consumes: todo lo construido en las Tasks 1-5; `core.intake_log.{caso_path, read_events}`.
- Produces: nada de producción (solo tests).

- [ ] **Step 1: Write the failing tests**

Añadir al final de `tests/test_sala_maquina_cableado_atomize.py`:

```python
# --- Grupo 2: contra el MOTOR REAL -------------------------------------------

def test_motor_real_solo_ve_el_nivel_superior(caso, monkeypatch, capsys):
    # El .eml de la subcarpeta NO se atomiza (glob, no rglob): el evento lo declara
    # con dos conteos distintos y el aviso lo grita. Si algún día el motor pasa a
    # enumerar recursivamente (MEJORAS #98), este test lo señalará.
    case_dir, eventos = caso
    src = case_dir / "00_Input" / "03_Email"
    (src / "a.eml").write_bytes(_eml("<a@x>", "Visible"))
    (src / "mensaje_con_adjunto").mkdir()
    (src / "mensaje_con_adjunto" / "b.eml").write_bytes(_eml("<b@x>", "Invisible"))

    cli.apply("W-TEST99")

    d = _evento(eventos)[0]
    assert d["status"] == "ok"
    assert (d["eml_nivel_superior"], d["eml_totales"]) == (1, 2)
    assert d["mensajes"] == 1                 # el motor solo atomizó el visible
    mds = list((case_dir / "01_Procesado" / "Emails" / "mensajes").glob("*.md"))
    assert len(mds) == 1
    assert "Invisible" not in mds[0].read_text(encoding="utf-8")
    assert "1 .eml viven en subcarpetas" in capsys.readouterr().err


def test_transicion_a_cero_fuentes_poda_mensajes_pero_no_adjuntos(caso, monkeypatch):
    # Retirar el correo (remedio real de W-02VUDR) debe reflejarse en `mensajes/`.
    # `adjuntos/` NO se poda: comportamiento CONOCIDO del motor (MEJORAS #99). El día
    # que se arregle, este test fallará y hay que actualizarlo — eso es lo que se
    # quiere: que la deuda no se olvide.
    case_dir, eventos = caso
    src = case_dir / "00_Input" / "03_Email"
    eml = src / "a.eml"
    eml.write_bytes(_eml("<a@x>", "Con adjunto",
                         attachments=[("contrato.pdf", "application/pdf", b"%PDF datos")]))

    cli.apply("W-TEST99")
    emails = case_dir / "01_Procesado" / "Emails"
    assert len(list((emails / "mensajes").glob("*.md"))) == 1
    adjuntos_antes = sorted(p.name for p in (emails / "adjuntos").glob("*.pdf"))
    assert adjuntos_antes                                  # el adjunto se materializó

    eml.unlink()
    cli.apply("W-TEST99")

    assert list((emails / "mensajes").glob("*.md")) == []  # podado
    assert sorted(p.name for p in (emails / "adjuntos").glob("*.pdf")) == adjuntos_antes
    d = _evento(eventos)[-1]
    assert d["status"] == "ok" and d["mensajes"] == 0


def test_evento_real_es_valido_y_serializable(tmp_path, monkeypatch):
    # Sin parchear `append_event`: verifica que `atomizado_email` está en INTAKE_EVENTS
    # (si no, ValueError) y que el payload es JSON-serializable de verdad.
    from core import intake_log
    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
    (case_dir / "00_Input" / "03_Email").mkdir(parents=True)
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(intake_log, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])

    cli.apply("W-TEST99")

    eventos = [e for e in intake_log.read_events("W-TEST99")
               if e["event"] == "atomizado_email"]
    assert len(eventos) == 1
    assert eventos[0]["details"]["status"] == "ok"
    assert eventos[0]["details"]["mensajes"] == 1
```

- [ ] **Step 2: Run tests to verify they pass (o fallan por una razón real)**

```bash
python -m pytest tests/test_sala_maquina_cableado_atomize.py -q
```

Expected: 15 PASSED. **Si alguno falla, es un hallazgo, no ruido de test:** el grupo 2 corre el motor de verdad y es exactamente la clase de test que la rev. 1 no tenía. Diagnostica antes de tocar los asserts (`superpowers:systematic-debugging`).

- [ ] **Step 3: Commit**

```bash
git add tests/test_sala_maquina_cableado_atomize.py
git commit -m "test(sala_maquina): frontera del cableado contra el motor real"
```

---

### Task 7: Documentación, suite completa y cierre

Sin esto, el `SKILL.md` sigue sin mencionar la atomización ni una vez, y el `PLAN.md` sigue presentando la casilla 2 como pendiente.

**Files:**
- Modify: `.claude/skills/organizar-sala-maquina/SKILL.md:118-131` (paso 3 del Procedimiento) y `:145` (Gotchas)
- Modify: `PLAN.md` (bloque `[SIGUIENTE-CABLEADO-CORREO]` + fila 11 de la cola)
- Modify: `docs/MEJORAS_FUTURAS.md` (`#55`, `#68.a`, `#98`)
- Modify: `docs/ARQUITECTURA.md:70,73` (consumidores de `core/email_atomize/`)

**Interfaces:**
- Consumes: el hash del commit/PR (se rellena al mergear).
- Produces: nada de código.

- [ ] **Step 1: `SKILL.md` — el `apply` atomiza**

En el paso 3 del Procedimiento, insertar como primer sub-bullet (antes de `**--vision**`):

```markdown
   - **Atomiza el correo primero.** Antes del OCR, `apply` corre el motor de
     atomización (`core/email_atomize`) sobre los lotes `email` de `00_Input/` y el
     cajón legacy `03_Email`, y deja el resultado en `01_Procesado/Emails/` + un evento
     `atomizado_email` en `_intake_log.jsonl` con `status` (`ok`/`parcial`/`fallo`).
     Ya no hace falta acordarse de lanzar `python -m scripts.atomize_emails` a mano.
     **Si el motor falla, el OCR sigue** (no depende de él) y el fallo sale como banner
     + evento: no lo ignores, revisa `01_Procesado/Emails` antes de citar `MSG-ids`.
     Si el caso no tiene correo y no tiene árbol previo, este paso no hace nada.
```

En Gotchas, añadir:

```markdown
- **La atomización no garantiza un árbol fresco.** El motor poda `mensajes/` pero **no**
  `adjuntos/` (`MEJORAS #99`), así que un adjunto de un correo retirado sobrevive y
  `adjuntos_contenido` lo seguirá recogiendo. Y con `--extraer-adjuntos` el `.eml` de un
  mensaje con adjuntos baja a una subcarpeta que el atomizador **no** enumera
  (`MEJORAS #98`): `apply` avisa con un banner cuando detecta esos `.eml`. El contenido
  (texto/OCR) de los adjuntos del correo sigue **fuera** de la sala de máquina, que lee
  solo `00_Input` (`MEJORAS #87`).
```

- [ ] **Step 2: `PLAN.md` — casillas y cola**

En el bloque `[SIGUIENTE-CABLEADO-CORREO]`, marcar la casilla 2 y dejar la 3 como está:

```markdown
- [x] Encadenar la atomización en ese punto, con tests que fijen el orden. ✅ **PR #NNN**
      (`<hash>`): `_atomizar_correo` en `scripts/sala_maquina.py::apply` antes de
      `_construir_plan`; `contar_eml` + derivadores desde `case_dir` en
      `core/email_atomize/pipeline.py`; evento `atomizado_email` (INTAKE_EVENTS 26→27)
      con `status` `ok`/`parcial`/`fallo`; fallo blando para el OCR y banner + evento
      para el registro; aviso de `.eml` invisibles (`MEJORAS #98`); `plan` informa y no
      atomiza; `reforzar` tampoco. +15 tests (3 contra el motor real).
```

En la fila 11 de la cola priorizada, cambiar `Estado` a `casillas 1-2 ✅ (PR #NNN); casilla 3 ⛔ #98` y `Gate` a `solo queda la casilla 3, bloqueada por MEJORAS #98`.

- [ ] **Step 3: `docs/MEJORAS_FUTURAS.md`**

En `#68.a`, tras el bullet de la corrección de `07b0377`, añadir:

```markdown
  - ✅ **RESUELTA la otra mitad (PR #NNN, `<hash>`):** `scripts/sala_maquina.py::apply`
    encadena la atomización antes del OCR y declara el resultado en el evento
    `atomizado_email`. Lo que **sigue** abierto de `#68.b` es el **contenido** de los
    adjuntos atomizados (`MEJORAS #87`), no el encadenado.
```

En `#98`, tras el párrafo «Mitigación ya en curso», sustituir «en curso» por el hecho:

```markdown
**Mitigación YA EN MAIN (no es el arreglo).** `apply` y `plan` emiten un banner cuando
el conteo recursivo de `.eml` supera al de nivel superior, y el evento `atomizado_email`
lleva los dos conteos (`eml_nivel_superior` / `eml_totales`) (PR #NNN). El agujero es
ruidoso; sigue abierto.
```

En `#55` (orden del pipeline documental), añadir al final del bloque de hechos verificados:

```markdown
**Actualización 2026-07-28 (PR #NNN).** El **orden** ya lo garantiza el código:
`scripts/sala_maquina.py::apply` atomiza antes del OCR. Lo que este ítem seguía
prometiendo y **sigue sin cumplirse** es lo otro: que los átomos ENTREN al OCR. La sala
de máquina continúa leyendo solo `00_Input`, así que el contenido de los adjuntos
atomizados sigue fuera (`MEJORAS #87`), y el consumo del árbol atomizado por la sala de
lectura es `MEJORAS #86`. La parte de este ítem que era «encadenar» está cerrada; la que
era «alimentar» no.
```

- [ ] **Step 4: `docs/ARQUITECTURA.md`**

En la fila de `core/email_atomize/` (línea 70), añadir a la columna de consumidores:
`scripts/sala_maquina.py::apply` (cableado 2026-07-28: lo llama antes del OCR y declara `status` en `atomizado_email`; spec/plan `…-cableado-atomize-sala-maquina*`).
En la fila de `contaminacion.py` (línea 73), añadir a los consumidores de `notas`:
`scripts/sala_maquina.py::_atomizar_correo` (las surfacea a stderr antes del OCR).

- [ ] **Step 5: Suite completa y leak-scan**

```bash
python -m pytest -q --tb=short --junit-xml=%TEMP%\fd_suite.xml
```

Expected: 0 failed, 0 errors. El resumen de pytest no se captura fiable por tuberías en Windows → el conteo autoritativo está en el JUnit XML. Y:

```bash
pre-commit run --all-files
```

Expected: `leak-scan` verde (es el único check que corre en el PR).

- [ ] **Step 6: Commit y PR**

```bash
git add -A .claude/skills/organizar-sala-maquina/SKILL.md PLAN.md docs/MEJORAS_FUTURAS.md docs/ARQUITECTURA.md
git commit -m "docs: cableado de la atomizacion de correo (SKILL, PLAN, MEJORAS #68/#98, ARQUITECTURA)"
git push -u origin HEAD
gh pr create --fill
```

`main` está protegida: nunca commit directo. Tras mergear, rellenar `#NNN`/`<hash>` en `PLAN.md` y `MEJORAS_FUTURAS.md` si el merge cambió el hash, y **podar rama + worktree** (`docs/FLUJO_GIT.md §4`).

---

## Revisión adversarial (obligatoria antes del PR)

Por `CLAUDE.md`, la revisión adversarial de código la ejecuta **Codex** en solo lectura y **Claude adjudica**. La salida va **fuera del repo** (el guard `test_citas_a_specs_y_plans_existen` rompe si un `.md` trackeado cita un fichero de `docs/superpowers/` que aún no existe); la adjudicación se registra luego en este plan, como se hizo con la revisión del plan.

> **Actualizado 2026-08-01.** Este bloque prescribía delegar a Gemini vía `agy`, con el comando literal de la CLI. Esa vía se retiró (cupo agotado de forma persistente: ver `docs/DEAD_ENDS.md`) — de hecho la revisión del plan de este mismo documento ya la hizo Codex por ese motivo, como registra abajo la §«Adjudicación de la revisión adversarial del PLAN». Cambia el ejecutor; **los cinco puntos de ataque de abajo siguen siendo los buenos**.

Encargo a Codex — revisar adversarialmente el diff de la rama contra `main` (cableado de la atomización de correo en `scripts/sala_maquina.py`), contrastando **cada hallazgo contra el código real, no solo contra el diff**, y volcando el resultado a un fichero fuera del repo (`%TEMP%\revision_cableado_correo.md`):

1. que el no-op **no siembre carpetas**;
2. que un fallo del motor **no aborte el OCR** pero **sí emita evento**;
3. que el payload del evento **no invente contadores**;
4. que `plan` **no escriba** en `01_Procesado/Emails`;
5. que **no se re-resuelva** el caso.

Al adjudicar: un hallazgo que solo mira el diff suele ser falso positivo, y la convergencia de dos revisores **no** exime de verificar contra la fuente. Claude es el juez.

---

## Desviaciones aprobadas durante la ejecución

**1. El `noop` con discrepancia SÍ emite evento** (decisión de Nikolai, 2026-07-28, durante la
revisión de la Task 5). La revisión de la tarea encontró que el banner de `#98` afirmaba «el conteo
del evento lo deja registrado» mientras el no-op salía **antes** de emitirlo — y ese camino es
justo el escenario típico del flag: si **todos** los `.eml` traen adjunto, todos bajan a subcarpeta,
`n_top == 0` y, sin árbol previo, la discrepancia se quedaba solo en un stderr efímero. Contradecía
el objetivo 4 de la spec («que la discrepancia deje de ser silenciosa») aunque respetase el §4.5
(«nunca evento en el `noop`»).

Regla final, que sustituye a la del §4.3 en esa fila: con `n_top == 0` y sin árbol previo **no se
llama al motor** (sigue intacto el motivo: `atomize_dir` hace `mkdir` incondicional y sembraría
carpetas vacías), pero **si `n_rec > n_top` se emite `atomizado_email` con `status: "noop"`** y solo
los dos conteos. Sin discrepancia, silencio total: ni evento ni salida. `"noop"` no es un status
nuevo — la tabla del §4.3 ya lo nombraba. La emisión guardada se extrajo a
`_registrar_atomizado(case_id, details)`, usada por los dos puntos de emisión.

**2. Redacción del banner.** La frase final pasa a «`apply` deja los dos conteos en el evento
`atomizado_email`»: el mismo banner lo imprime `plan`, que no emite ningún evento, así que la
promesa en primera persona era falsa en ese contexto.

**3. La guarda de no-op se amplía a «ve TODO o no reconcilia»** (hallado en la revisión de rama
completa, 2026-07-28, posterior al cierre de esta tarea). La regla del punto 1 de arriba solo
cubría `n_top == 0 and not out.exists()`: con árbol previo YA existente (`out.exists()`), la
condición vieja no se activaba y el helper caía al motor aunque hubiera discrepancia
(`n_rec > n_top`). El motor reconciliaría con visibilidad parcial o nula, y su poda de
idempotencia (`pipeline.py:122-125`) borraría `mensajes/*.md` cuyo `.eml` fuente es invisible,
además de vaciar `corpus.jsonl`, los índices, `_revision/` y `vistas/` — sin poder regenerarlos
mientras la ceguera de `MEJORAS #98` siga. Guarda final, evaluada ANTES que la del punto 1:
`if n_rec > n_top and out.exists(): status "noop" y no se llama al motor`. Motivo: el motor solo
puede reconciliar un árbol existente si VE TODO el correo; «cero visibles» no distingue entre «el
letrado retiró el correo» y «hay `.eml` invisibles». Coste aceptado: un caso con la discrepancia
viva **deja de atomizarse** (el árbol previo queda congelado, sin podar ni actualizar) hasta que
se aplane el lote — documentado también en `MEJORAS #98`.

---

## Adjudicación de la revisión adversarial del PLAN (Codex, 2026-07-28) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/plans/2026-07-28-cableado-atomize-sala-maquina.md`, rev. `no registrado`, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** no capturado — llegó por chat, antes del contrato de actas
- **Hallazgos:** 6 confirmados · 0 rebajados · 2 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** incorporado en este mismo plan antes de construir; build en PR #151

Los 6 son la tabla de «Aceptados y corregidos»; los 2 refutados, los dos de «Rechazados, con
motivo». **La prosa del párrafo siguiente dice «4 bloqueantes» y la tabla no publica severidades**,
así que qué cuatro de los seis lo eran queda **sin verificar**: el informe no se archivó y no hay
fuente que lo dirima.

`agy` no pudo correr (cupo de Gemini agotado), así que la revisión del plan la hizo Codex en solo
lectura. **Veredicto NO-SHIP con 4 bloqueantes; los 4 aceptados y ya incorporados arriba.**

**Aceptados y corregidos:**

| # | Hallazgo | Verificación | Dónde se arregló |
|---|---|---|---|
| 1 | El test de fallo de log **no podía pasar**: el doble lanzaba para cualquier evento y `apply` emite `procesado_sala_maquina` con un `append_event` sin captura | **CONFIRMADO** leyendo `scripts/sala_maquina.py:195-199` | Task 4: `log_roto` acotado a `ev == "atomizado_email"` |
| 2 | Task 2 dejaba rojo `test_intake_events_contiene_los_canonicos`, que compara el set **completo** | **CONFIRMADO** leyendo `tests/test_intake_log.py:337-379` (el literal termina en `"archivado"`) | Task 2: se actualizan **los dos** tests |
| 3 | El contrato no mataba una emisión forense **posterior** al OCR (spec §4.5 exige antes) | CONFIRMADO por lectura: el test de orden solo registraba `atomize/plan/ejecutar` | Task 4: el test de orden registra también `append_event` y las notas, y exige que precedan al plan |
| 4 | Los payloads `fallo` y `parcial` podían quedar incompletos y pasar igual | CONFIRMADO | Task 4: igualdad exacta de dict en los tres `status` |
| 5 | Faltaban pruebas negativas (aviso solo ante discrepancia; `plan` sin escribir en `Emails`; una sola resolución) y la aserción sobre `fuentes` | CONFIRMADO | Tasks 3 y 5 |
| 6 | Deriva descriptiva: la tabla decía «8 con doble», son 12 | CONFIRMADO | Tabla de File Structure |

**Rechazados, con motivo:**

- **«Pasa rota si se captura solo `RuntimeError`».** Matar un `except` demasiado estrecho exigiría
  dos tests con excepciones distintas. El código del plan dice `except Exception` con comentario
  explícito de por qué; nadie va a estrecharlo por accidente. YAGNI.
- **Notas de `vistas` a stderr (severidad baja).** Se mantiene imprimir todas las notas. `resumir`
  ya descarta el nombre de adjunto y solo emite W-code + MSG-ids
  (`core/email_atomize/contaminacion.py:62-81`); lo que puede llevar un nombre real es una nota de
  `vistas.yaml`, fichero que **escribe el propio letrado sobre su propio caso**; el CLI manual ya
  imprime exactamente esas notas hoy (`scripts/atomize_emails.py:35-39`); y `docs/SEGURIDAD_DATOS.md`
  §58-66 prescribe justamente referenciar casos por W-code. Añadir redacción inventaría una frontera
  que el repo no tiene y divergiría de un camino ya existente.

**Puntos que la revisión confirmó como correctos** (ya no son supuestos míos):

- **Omitir los contadores en `status: "fallo"` no rompe a nadie.** Los dos únicos consumidores
  productivos del log tratan `files` como opcional y no imponen schema a `details`
  (`core/abrir_caso.py:159-166`, `.claude/skills/intake-expediente/scripts/traza.py:50-69`).
- **Import al top sin ciclo**, y el parcheo `cli.atomize` funciona. Medido en este entorno, lo que
  Codex dejó como UNVERIFIED: importar el CLI cuesta **0,61 s** y el pipeline añade **+0,19 s**;
  `httpx` ya estaba cargado antes de este cambio. Irrelevante frente a una corrida de OCR de ~1 h 40.
- Las referencias de línea del plan corresponden al código real.
