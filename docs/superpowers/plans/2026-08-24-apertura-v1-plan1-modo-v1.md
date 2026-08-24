# Apertura V1 — Plan 1: el modo `v1` y sus puertas negativas

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer que «ser una ejecución V1» sea un hecho comprobable del CLI —`--modo v1`— que rechaza, antes de cualquier efecto, todo lo que V1 no admite.

**Architecture:** Un flag de modo en el entrypoint existente `scripts/abrir_caso.py`, con vocabulario cerrado y validación como primera sentencia del cuerpo de `main`, antes de la autoderivación de identidad, de `ensure_case`, de todo intake y de toda lectura remota. En modo `v1`: `--crm` solo admite `skip` y `--fuente` solo admite `drive_ev`. El modo `libre` conserva el comportamiento actual byte a byte, así que V2, V3 y el uso ad hoc no se regresan.

**Tech Stack:** Python 3.14, Typer, pytest, `typer.testing.CliRunner`.

## Erratas del plan, detectadas al ejecutarlo (2026-08-24)

Tres defectos del texto de arriba. Se corrigieron **en la implementación**, no en la aserción, y
se anotan aquí porque los Planes 2-5 heredarían el patrón:

1. **El Task 2 traía un test vacuo.** `test_v1_rechaza_el_default_de_crm` contenía
   `assert default or True`, que no puede fallar nunca — el antipatrón que este repo tiene
   documentado (memoria `feedback-guard-sin-prueba-de-mutacion`). Sustituido por la aserción que
   sí muerde: `inspect.signature(cli.main).parameters["crm"].default.default == "api"`. Si alguien
   cambiara el default a `skip`, el test lo dice.
2. **El dato de identidad de los tests del Task 4 no existe.** `--tipo-caso honorarios` levanta
   `ValueError: Tipo de caso desconocido`. Los canónicos están en `config.TIPOS_CASO_ALL`; se usa
   `--tipo-caso BAD_DEBT --sufijo "Bad debt"` (memoria `feedback-case-sufijo-tipo-canonico`).
   Que el test del **aborto** pasara con el dato malo y solo cayera el de camino feliz es, de
   hecho, evidencia de la propiedad: v1 aborta antes de resolver identidad.
3. **La aritmética de tests iba desfasada en 1 desde el Task 3.** La parametrización de tres
   fuentes suma 3 casos, no 2: son **11** tras el Task 3 y **14** al final, no 10 y 13.

Y una comprobación que el plan no pedía y la doctrina del repo sí: el test del *orden* se validó
**por mutación** —desplazar la puerta por debajo de `ensure_case` lo pone rojo con
`no debía llegar a ejecutarse ningún efecto`—, restaurando después con `git checkout`. Sin esa
prueba, «valida antes de cualquier efecto» sería otra propiedad nombrada y no contratada, que es
justo la figura que el §23 de la spec detuvo tres veces.

## Por qué este plan es el primero, y por qué V1 no cabe en un plan

La spec rev. 8 fija V1 (§21), toma cuatro decisiones (§24) y enumera un write-set de 27 clases
(§25). Eso **no es un subsistema**: son cinco, y la propia spec declara que tres contratos todavía
no existen (§25.5: el orden durable por clase de operación, la monotonía de observación por fuente
y el snapshot inmutable por ronda «cuelgan de la primitiva de D2 y se escriben con el plan, no
aquí»). Un único plan TDD para todo V1 sería una fábrica de marcadores de posición, que es
exactamente lo que la skill de planes prohíbe y lo que el §23 castigó tres veces.

Troceo declarado, en orden de dependencia:

| Plan | Alcance | Depende de |
|---|---|---|
| **Plan 1 — este** | `--modo v1` y sus puertas negativas | **nada**: es validación de argumentos antes de todo efecto |
| Plan 2 | Primitiva de mutex de D2 (lockfile `O_EXCL`, namespace por W-code, lease) | Fase 1 (registro local) |
| Plan 3 | Write-set: llevar al guard y al mutex las 25 clases que hoy no pasan (§25.3) | Plan 2 |
| Plan 4 | Generación, monotonía por fuente y rondas atestadas (H3-03/H3-05/H3-06) | Plan 2; **su contrato aún no está escrito en la spec** |
| Plan 5 | Cableado del orden completo y E2E de V1 | Planes 1-4 |

**Precondición externa de los planes 2-5, no de este:** la **Fase 1 de la arquitectura dual**
(decisión D1, §24), que ya tiene su propio plan en
`docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md`. No se re-planifica aquí.

**Este plan no cablea nada.** No hace que V1 *corra*: hace que V1 sea *reconocible y acotable*, que
es la precondición de todo lo demás y lo que R5 declaró ausente (H5-01).

## Global Constraints

- Windows + PowerShell. Todo comando shell parte de `cd "C:\Users\tnm33\Dev\FeesDefender"`.
- Python del venv del repo: `.venv\Scripts\python.exe`. Nunca el Python del sistema: no tiene `python-dotenv` y `core/config.py:14` lo importa.
- Encoding SIEMPRE UTF-8 sin BOM.
- `pytest` con `--basetemp` en ruta **CORTA** bajo `C:\Users\tnm33\AppData\Local\Temp` (MAX_PATH produce fallos falsos).
- `main` está protegida: el trabajo va en rama + PR. Nunca `git add -A`: commits acotados a los ficheros del paso.
- Terminología de partes: **propietario / buscador**, nunca vendedor / comprador.
- Nombres de carpeta en tipo oración (`06_Anonimizado`, no `06_ANONIMIZADO`).
- La lógica vive en el core; la UI y los CLI solo orquestan. Este plan toca un CLI a propósito: lo que añade es validación de argumentos, no lógica de negocio.
- **No se crea `scripts.apertura_expediente`** (criterio 50 de la spec).
- El modo `libre` no cambia de comportamiento. Cualquier test existente que falle es una regresión, no un ajuste.

## File Structure

- `scripts/abrir_caso.py` — **modificar**. Añade la constante `_MODOS`, la opción `--modo` y la función pura `validar_modo(...)`, más su llamada como primera sentencia del cuerpo de `main`. Responsabilidad única del añadido: decidir si esta invocación es admisible en el modo pedido.
- `tests/test_abrir_caso_modo_v1.py` — **crear**. Fichero nuevo y enfocado, en vez de engordar `tests/test_abrir_caso_cli.py` (ya cubre hash, intake y alta): estos tests son de una sola responsabilidad y conviene poder correrlos solos.
- `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` — **modificar**. Documenta el modo. Sin esto el modo existe y nadie lo usa, que es el defecto de familia de este repo.

**Por qué `validar_modo` es una función pura y no código inline:** para poder probar la matriz de
combinaciones sin arrancar el CLI ni tocar disco, y para que el orden de validación —antes de todo
efecto— sea una propiedad demostrable con un test que compruebe que no se creó nada.

---

### Task 1: vocabulario cerrado del modo

**Files:**
- Modify: `scripts/abrir_caso.py` (constante nueva junto a `_FUENTES_CLI:64`; opción nueva en la firma de `main`, tras `--fuente`; validación al inicio del cuerpo, antes de `if fuente not in _FUENTES_CLI:386`)
- Test: `tests/test_abrir_caso_modo_v1.py`

**Interfaces:**
- Consumes: nada.
- Produces: `_MODOS: tuple[str, ...]`; `validar_modo(modo: str, *, crm: str, fuente: str) -> list[str]` — devuelve la lista de mensajes de error; vacía significa admisible. Los tasks 2 y 3 amplían **esta misma** función y no crean otras.

- [ ] **Step 1: Write the failing test**

Crear `tests/test_abrir_caso_modo_v1.py`:

```python
"""El modo de ejecución de `abrir_caso`: vocabulario cerrado y puertas de V1.

Spec: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md
§24 D3 — el discriminante de V1 y el dueño de la secuencia son el mismo objeto.
"""
from pathlib import Path

from typer.testing import CliRunner

from core.casos import case_locator
from scripts import abrir_caso as cli

runner = CliRunner()


def test_modos_vocabulario_cerrado():
    assert cli._MODOS == ("libre", "v1")


def test_modo_desconocido_es_error():
    errores = cli.validar_modo("V1", crm="skip", fuente="drive_ev")
    assert errores
    assert "modo desconocido" in errores[0].lower()


def test_modo_libre_no_impone_nada():
    assert cli.validar_modo("libre", crm="api", fuente="email") == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && .venv\Scripts\python.exe -m pytest tests/test_abrir_caso_modo_v1.py -q -p no:cacheprovider --basetemp=C:\Users\tnm33\AppData\Local\Temp\fdp1
```

Expected: FAIL con `AttributeError: module 'scripts.abrir_caso' has no attribute '_MODOS'`.

- [ ] **Step 3: Write minimal implementation**

En `scripts/abrir_caso.py`, junto a `_FUENTES_CLI` (línea 64):

```python
_MODOS = ("libre", "v1")
```

Y la función pura, antes de la definición de `main`:

```python
def validar_modo(modo: str, *, crm: str, fuente: str) -> list[str]:
    """Errores que impiden ejecutar en `modo`. Lista vacía = admisible.

    Pura a propósito: la matriz de combinaciones se prueba sin arrancar el CLI ni
    tocar disco, y el orden —validar ANTES de cualquier efecto— queda demostrable.
    """
    if modo not in _MODOS:
        return [f"Modo desconocido: {modo!r}. Válidos: {_MODOS}"]
    return []
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && .venv\Scripts\python.exe -m pytest tests/test_abrir_caso_modo_v1.py -q -p no:cacheprovider --basetemp=C:\Users\tnm33\AppData\Local\Temp\fdp1
```

Expected: PASS, 3 passed.

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && git add tests/test_abrir_caso_modo_v1.py scripts/abrir_caso.py && git commit -m "feat(abrir_caso): vocabulario cerrado del modo de ejecución"
```

---

### Task 2: en modo `v1`, `--crm` solo admite `skip`

**Files:**
- Modify: `scripts/abrir_caso.py` (cuerpo de `validar_modo`)
- Test: `tests/test_abrir_caso_modo_v1.py`

**Interfaces:**
- Consumes: `validar_modo(modo, *, crm, fuente)` del Task 1.
- Produces: la misma firma, con una regla más. No cambia el tipo de retorno.

**Contexto que el implementador necesita:** el default de `--crm` es `"api"`
(`scripts/abrir_caso.py:381`), y `api` alcanza `create_expediente` — un POST real. Por eso
**omitir** el flag en modo `v1` tiene que abortar: es literalmente lo que exigió el hallazgo
H5-01. No se cambia el default a `skip`: cambiarlo haría que la omisión pasara en silencio, que es
el defecto contrario.

- [ ] **Step 1: Write the failing test**

Añadir a `tests/test_abrir_caso_modo_v1.py`:

```python
def test_v1_rechaza_crm_api():
    errores = cli.validar_modo("v1", crm="api", fuente="drive_ev")
    assert len(errores) == 1
    assert "--crm skip" in errores[0]


def test_v1_admite_crm_skip():
    assert cli.validar_modo("v1", crm="skip", fuente="drive_ev") == []


def test_v1_rechaza_el_default_de_crm():
    """Omitir --crm deja `api` por default: en v1 eso ABORTA, no se corrige en silencio."""
    default = cli.main.__defaults__ is None  # la firma usa typer.Option, no defaults nativos
    assert default or True  # el default efectivo se comprueba en el test de CLI del Task 4
    assert cli.validar_modo("v1", crm="api", fuente="drive_ev") != []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && .venv\Scripts\python.exe -m pytest tests/test_abrir_caso_modo_v1.py -q -p no:cacheprovider --basetemp=C:\Users\tnm33\AppData\Local\Temp\fdp1
```

Expected: FAIL con `assert len([]) == 1` en `test_v1_rechaza_crm_api`.

- [ ] **Step 3: Write minimal implementation**

Sustituir el cuerpo de `validar_modo` en `scripts/abrir_caso.py`:

```python
def validar_modo(modo: str, *, crm: str, fuente: str) -> list[str]:
    """Errores que impiden ejecutar en `modo`. Lista vacía = admisible.

    Pura a propósito: la matriz de combinaciones se prueba sin arrancar el CLI ni
    tocar disco, y el orden —validar ANTES de cualquier efecto— queda demostrable.
    """
    if modo not in _MODOS:
        return [f"Modo desconocido: {modo!r}. Válidos: {_MODOS}"]
    if modo == "libre":
        return []
    errores: list[str] = []
    if crm != "skip":
        errores.append(
            f"--modo v1 no escribe en el CRM: exige --crm skip (recibido: {crm!r}). "
            "El default es `api` y alcanza un POST de alta, así que omitir el flag "
            "también aborta."
        )
    return errores
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && .venv\Scripts\python.exe -m pytest tests/test_abrir_caso_modo_v1.py -q -p no:cacheprovider --basetemp=C:\Users\tnm33\AppData\Local\Temp\fdp1
```

Expected: PASS, 6 passed.

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && git add tests/test_abrir_caso_modo_v1.py scripts/abrir_caso.py && git commit -m "feat(abrir_caso): en modo v1 el CRM solo admite skip"
```

---

### Task 3: en modo `v1`, `--fuente` solo admite `drive_ev`

**Files:**
- Modify: `scripts/abrir_caso.py` (cuerpo de `validar_modo`)
- Test: `tests/test_abrir_caso_modo_v1.py`

**Interfaces:**
- Consumes: `validar_modo(modo, *, crm, fuente)` de los Tasks 1-2.
- Produces: la misma firma, con la segunda regla. Los errores se **acumulan**: pedir `--crm api` y `--fuente email` a la vez devuelve dos mensajes, no uno.

**Contexto:** `_FUENTES_CLI = ("drive_ev", "manual", "whatsapp", "email")`
(`scripts/abrir_caso.py:64`). `--fuente email` llama a `_intake_email` (`:194`), que ejecuta
`email_export.export_label`: **Gmail real**. V1 no descubre ni exporta correo (§21.2), así que
`email`, `manual` y `whatsapp` quedan fuera. La atomización local que V1 **sí** incluye actúa sobre
correo ya depositado, y la ejecuta la sala de máquina, no este selector.

- [ ] **Step 1: Write the failing test**

Añadir a `tests/test_abrir_caso_modo_v1.py`:

```python
import pytest


@pytest.mark.parametrize("fuente", ["email", "manual", "whatsapp"])
def test_v1_rechaza_fuentes_ajenas(fuente):
    errores = cli.validar_modo("v1", crm="skip", fuente=fuente)
    assert len(errores) == 1
    assert fuente in errores[0]


def test_v1_admite_drive_ev():
    assert cli.validar_modo("v1", crm="skip", fuente="drive_ev") == []


def test_v1_acumula_los_errores():
    errores = cli.validar_modo("v1", crm="api", fuente="email")
    assert len(errores) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && .venv\Scripts\python.exe -m pytest tests/test_abrir_caso_modo_v1.py -q -p no:cacheprovider --basetemp=C:\Users\tnm33\AppData\Local\Temp\fdp1
```

Expected: FAIL con `assert len([]) == 1` en los tres casos parametrizados.

- [ ] **Step 3: Write minimal implementation**

En `scripts/abrir_caso.py`, añadir la constante junto a `_MODOS` y la regla en `validar_modo`:

```python
_FUENTES_V1 = ("drive_ev",)
```

```python
    if fuente not in _FUENTES_V1:
        errores.append(
            f"--modo v1 solo admite --fuente {_FUENTES_V1[0]} (recibido: {fuente!r}). "
            "V1 no descubre ni exporta correo: `email` ejecuta email_export.export_label, "
            "que llama a Gmail. La atomización local de V1 actúa sobre correo YA depositado "
            "y la ejecuta la sala de máquina."
        )
```

(insertado tras el bloque de `crm`, antes del `return errores`)

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && .venv\Scripts\python.exe -m pytest tests/test_abrir_caso_modo_v1.py -q -p no:cacheprovider --basetemp=C:\Users\tnm33\AppData\Local\Temp\fdp1
```

Expected: PASS, 10 passed.

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && git add tests/test_abrir_caso_modo_v1.py scripts/abrir_caso.py && git commit -m "feat(abrir_caso): en modo v1 la única fuente es drive_ev"
```

---

### Task 4: la validación ocurre ANTES de cualquier efecto

**Files:**
- Modify: `scripts/abrir_caso.py` (firma de `main`: opción `--modo`; cuerpo de `main`: llamada a `validar_modo` como primera sentencia, antes de `if fuente not in _FUENTES_CLI` de la línea 386)
- Test: `tests/test_abrir_caso_modo_v1.py`

**Interfaces:**
- Consumes: `validar_modo` de los Tasks 1-3.
- Produces: la opción de CLI `--modo` con default `"libre"`. Los planes 2-5 asumen este flag como el discriminante de V1.

**Por qué este test es el que importa:** los Tasks 1-3 prueban la *decisión*. Este prueba el
*orden*, que es lo que H5-01 exigía —«abortar antes de cualquier efecto»— y lo que ninguna prueba
de camino feliz demuestra. La aserción fuerte no es el código de salida: es que **no se creó la
carpeta del caso**.

- [ ] **Step 1: Write the failing test**

Añadir a `tests/test_abrir_caso_modo_v1.py`:

```python
@pytest.fixture
def casos_root(tmp_path, monkeypatch):
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    return root


def test_v1_aborta_antes_de_crear_el_esqueleto(casos_root, monkeypatch):
    """Sin --crm skip, v1 aborta y NO deja rastro en disco."""
    def explota(*a, **k):
        raise AssertionError("no debía llegar a ejecutarse ningún efecto")

    monkeypatch.setattr(cli.case_manager, "ensure_case", explota)
    monkeypatch.setattr(cli, "_despachar_intake", explota)
    monkeypatch.setattr(cli, "_alta_crm", explota)

    res = runner.invoke(cli.app, [
        "--modo", "v1",
        "--w-code", "W-TEST01", "--ciudad", "Barcelona",
        "--tipo-caso", "honorarios", "--codigo-caso", "BaTEST",
        "--sufijo", "honorarios", "--direccion", "Calle Falsa 1",
        "--folder-id", "FID", "--team-id", "TID",
    ])

    assert res.exit_code == 1
    assert "--crm skip" in res.output
    assert list(casos_root.iterdir()) == []


def test_v1_con_los_flags_correctos_pasa_la_puerta(casos_root, monkeypatch):
    """La puerta no bloquea una invocación V1 válida: llega al intake."""
    llamadas = []
    monkeypatch.setattr(cli.case_manager, "ensure_case",
                        lambda *a, **k: llamadas.append("ensure_case"))
    monkeypatch.setattr(cli, "_despachar_intake",
                        lambda *a, **k: llamadas.append("intake"))
    monkeypatch.setattr(cli, "_alta_crm", lambda *a, **k: llamadas.append("crm"))

    res = runner.invoke(cli.app, [
        "--modo", "v1", "--crm", "skip",
        "--w-code", "W-TEST01", "--ciudad", "Barcelona",
        "--tipo-caso", "honorarios", "--codigo-caso", "BaTEST",
        "--sufijo", "honorarios", "--direccion", "Calle Falsa 1",
        "--folder-id", "FID", "--team-id", "TID",
    ])

    assert res.exit_code == 0, res.output
    assert "ensure_case" in llamadas and "intake" in llamadas


def test_modo_libre_conserva_el_comportamiento(casos_root, monkeypatch):
    """Sin --modo, nada cambia: `email` y el default de crm siguen admitidos."""
    monkeypatch.setattr(cli.case_manager, "ensure_case", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_despachar_intake", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_alta_crm", lambda *a, **k: None)

    res = runner.invoke(cli.app, [
        "--fuente", "email", "--cuenta", "x@y.z", "--label", "L",
        "--w-code", "W-TEST01", "--ciudad", "Barcelona",
        "--tipo-caso", "honorarios", "--codigo-caso", "BaTEST",
        "--sufijo", "honorarios", "--direccion", "Calle Falsa 1",
    ])

    assert "Modo desconocido" not in res.output
    assert "--modo v1" not in res.output
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && .venv\Scripts\python.exe -m pytest tests/test_abrir_caso_modo_v1.py -q -p no:cacheprovider --basetemp=C:\Users\tnm33\AppData\Local\Temp\fdp1
```

Expected: FAIL — Typer rechaza `--modo` con `No such option: --modo`, así que `exit_code == 2`.

- [ ] **Step 3: Write minimal implementation**

En la firma de `main`, tras la opción `--fuente` (línea 370):

```python
    modo: str = typer.Option(
        "libre", "--modo",
        help="libre|v1. `v1` es el discriminante de la primera vertical (spec §24 D3): "
             "exige --crm skip y --fuente drive_ev, y valida antes de cualquier efecto."),
```

Y como **primera sentencia** del cuerpo de `main`, antes de `if fuente not in _FUENTES_CLI:`:

```python
    # Puerta del modo (spec §24 D3): se valida ANTES de la identidad, de ensure_case,
    # de todo intake y de toda lectura remota. El orden es la propiedad, no el mensaje.
    errores_modo = validar_modo(modo, crm=crm, fuente=fuente)
    if errores_modo:
        for e in errores_modo:
            typer.echo(f"[ERROR] {e}", err=True)
        raise typer.Exit(code=1)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && .venv\Scripts\python.exe -m pytest tests/test_abrir_caso_modo_v1.py -q -p no:cacheprovider --basetemp=C:\Users\tnm33\AppData\Local\Temp\fdp1
```

Expected: PASS, 13 passed.

Y la suite de no regresión del entrypoint:

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && .venv\Scripts\python.exe -m pytest tests/test_abrir_caso.py tests/test_abrir_caso_cli.py -q -p no:cacheprovider --basetemp=C:\Users\tnm33\AppData\Local\Temp\fdp1
```

Expected: PASS sin fallos. Un fallo aquí es una **regresión del modo `libre`**, no un ajuste: revertir y revisar.

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && git add tests/test_abrir_caso_modo_v1.py scripts/abrir_caso.py && git commit -m "feat(abrir_caso): --modo v1 valida antes de cualquier efecto"
```

---

### Task 5: documentar el modo donde se usa

**Files:**
- Modify: `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` (sección de apertura con `abrir_caso`)
- Test: `tests/test_docs_gobernanza.py` (no se modifica; se corre)

**Interfaces:**
- Consumes: el flag `--modo` del Task 4.
- Produces: nada de código.

**Por qué es un task y no una nota:** el defecto de familia de este repo es construir piezas que
nadie encadena, y su versión documental es un flag que existe y nadie usa. El runbook es el SSOT
operativo de la apertura.

- [ ] **Step 1: Localizar el comando documentado**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && grep -n "scripts.abrir_caso" docs/RUNBOOK_APERTURA_EXPEDIENTE.md
```

Expected: una o más líneas con la invocación de apertura.

- [ ] **Step 2: Añadir el bloque del modo**

Junto al comando de apertura, añadir:

```markdown
> **Modo V1 (`--modo v1`).** La primera vertical se ejecuta con
> `--modo v1 --crm skip --fuente drive_ev`. El modo es el **discriminante**: estar en él ES ser
> una ejecución V1, y valida antes de cualquier efecto. Rechaza `--crm api` —el default, que
> alcanza un POST de alta— y rechaza `--fuente email|manual|whatsapp`, porque V1 no descubre ni
> exporta correo. Sin `--modo`, el comportamiento es el de siempre (`libre`), que es el que usan
> V2, V3 y el uso ad hoc. Contrato: spec de apertura integral §24 D3.
```

- [ ] **Step 3: Correr los guards de gobernanza**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && git add docs/RUNBOOK_APERTURA_EXPEDIENTE.md && .venv\Scripts\python.exe -m pytest tests/test_docs_gobernanza.py -q -p no:cacheprovider --basetemp=C:\Users\tnm33\AppData\Local\Temp\fdp1
```

Expected: PASS. Los guards leen `git ls-files`, así que **indexar antes de correr** no es opcional.

- [ ] **Step 4: Suite completa**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && .venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider --basetemp=C:\Users\tnm33\AppData\Local\Temp\fdp1
```

Expected: 0 fallos, 0 errores. El conteo debe subir en **13** respecto al cierre anterior; cualquier otra variación se explica, no se normaliza.

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender" && git add docs/RUNBOOK_APERTURA_EXPEDIENTE.md && git commit -m "docs(runbook): documentar --modo v1 en la apertura"
```

---

## Lo que este plan deliberadamente NO hace

- **No cablea la secuencia.** `--modo v1` no llama todavía al pull de Sudespacho, ni a la atomización, ni a la sala de máquina. Eso es el Plan 5 y necesita el mutex del Plan 2.
- **No resuelve el workspace.** La resolución por `CaseWorkspace` (D1) es precondición de los planes 2-5 y vive en el plan de la Fase 1. Este plan valida argumentos, no copias.
- **No toca el write-set.** Las 25 clases que hoy no pasan por el guard son el Plan 3.
- **No cambia el default de `--crm`.** Cambiarlo a `skip` haría que la omisión pasara en silencio, que es el defecto contrario al que H5-01 señala.
- **No promete lo que un modo no puede prometer.** Nada impide correr `--modo libre` sobre un caso de V1. V1 es un contrato de modo y el §24 D3 lo declara así; este plan no finge una frontera que no existe.

## Autorrevisión

**Cobertura de la spec.** De la parte de la spec que este plan reclama —§24 D3, y la mitad de
*enforcement* de H4-01 y H5-01— hay task para todo: vocabulario (1), puerta del CRM (2), puerta de
la fuente (3), orden de validación (4), difusión (5). Lo que la spec pide y **no** cubre este plan
está enumerado arriba con su plan destino. D1, D2 y D4 no tienen task aquí a propósito: no son de
este subsistema.

**Marcadores de posición.** Ninguno: cada paso lleva el código o el comando literal, con la salida
esperada. Los `file:line` son del árbol en `9a5f26a`.

**Consistencia de tipos.** `validar_modo(modo: str, *, crm: str, fuente: str) -> list[str]` es la
misma firma en los tasks 1, 2, 3 y 4; los tasks 2 y 3 amplían su cuerpo y no crean funciones
nuevas. `_MODOS` y `_FUENTES_V1` son tuplas de `str`, como `_FUENTES_CLI`, que es el patrón
establecido del fichero.

**Un riesgo declarado del Task 4.** Los tres tests de CLI dependen de que los nombres internos
`cli._despachar_intake` y `cli._alta_crm` sigan existiendo para el `monkeypatch`. Están definidos
hoy en `scripts/abrir_caso.py:248` y `:265`, y se llaman en `:487` y `:497`. Si un refactor los
renombra, estos tests fallan por el arnés y no por el comportamiento: en ese caso se ajusta el
parche, no la aserción.
