# Apertura B1–B5 · PR-1 (quick wins: B4 + B3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir el evento forense `archivado` al log de intake (B4) y un normalizador de teléfono a 9 dígitos aplicado en los DTOs del CRM (B3).

**Architecture:** Cambios puros y acotados. B4 amplía un `frozenset` cerrado. B3 añade un helper puro en `core/utils.py` y lo cablea en el `__post_init__` de los dos DTOs de `core/sudespacho_relations.py`, de modo que toda construcción de DTO (REST + legacy + CLI + skill + tests) queda normalizada en un único punto. Sin I/O nuevo.

**Tech Stack:** Python 3, `dataclasses`, `re`, `pytest`. Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-18-apertura-expediente-b1-b5-design.md` (§5).

## Global Constraints

- **Plataforma:** Windows. Encoding **UTF-8 sin BOM** en todo fichero editado.
- **Worktree:** editar SOLO en este worktree (`…\worktrees\feesdefender-input-layout-spec-2b1e28`). **Nunca** `cd`/ruta absoluta a la raíz compartida (`Dev\FeesDefender`) para editar — otra sesión puede sobrescribir sin conflicto de git.
- **Ejecutar pytest** con el intérprete del repo principal contra el código del worktree, desde la raíz del worktree:
  `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest <ruta>::<test> -v`
  (el worktree no hereda `.venv`; el intérprete principal importa el `core` del worktree porque el cwd va en `sys.path`). Para conteos globales usar `--junit-xml` (la línea de resumen no se captura por tubería en este Windows).
- **`main` protegida:** rama + PR, check `leak-scan` verde. **Nunca** push directo ni `--no-verify`.
- **No tocar** `core/anon/` (congelado). **PII por W-code** en docs/commits/ramas.
- **Rama:** trabajar en la rama actual `claude/apertura-expediente-b1-b5-785145` (ya lleva la spec). PR-1 se abre desde ella. Los PR-2..PR-4 saldrán de ramas nuevas off `main` tras cada merge.
- TDD estricto, DRY, YAGNI, commits frecuentes.

---

### Task 1: B4 — evento `archivado` en `INTAKE_EVENTS`

**Files:**
- Modify: `core/intake_log.py` (frozenset `INTAKE_EVENTS`, `:42-70`; docstring `:9`)
- Test: `tests/test_intake_log.py` (`:332-334` conteo; `test_intake_events_contiene_los_canonicos` set `expected`; nuevo test de comportamiento)

**Interfaces:**
- Consumes: nada.
- Produces: `INTAKE_EVENTS` pasa a contener `"archivado"` (26 eventos). `append_event(case_id, "archivado", details=…)` deja de lanzar `ValueError`.

- [ ] **Step 1: Actualizar los tests existentes de conteo y catálogo (fallarán primero)**

En `tests/test_intake_log.py`, cambiar el conteo (`:334`) de `25` a `26`:

```python
def test_intake_events_es_frozenset_con_24_eventos(il):
    assert isinstance(il.INTAKE_EVENTS, frozenset)
    assert len(il.INTAKE_EVENTS) == 26
```

Y añadir `"archivado"` al set `expected` de `test_intake_events_contiene_los_canonicos` (justo tras `"migracion_layout_intake",`):

```python
        "migracion_layout_intake",
        "archivado",
    }
```

- [ ] **Step 2: Añadir el test de comportamiento (nuevo)**

Al final de la sección "INTAKE_EVENTS — sanity" de `tests/test_intake_log.py`:

```python
def test_append_event_acepta_archivado(il, cm):
    cm.ensure_case("LOG-ARCH")
    il.set_actor("Nikolai Tyukhay")
    il.append_event("LOG-ARCH", "archivado", details={"motivo": "PRESCRIPCION"})

    events = il.read_events("LOG-ARCH")
    assert len(events) == 1
    assert events[0]["event"] == "archivado"
    assert events[0]["details"] == {"motivo": "PRESCRIPCION"}
```

- [ ] **Step 3: Ejecutar los tests para verificar que fallan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_intake_log.py::test_intake_events_es_frozenset_con_24_eventos tests/test_intake_log.py::test_intake_events_contiene_los_canonicos tests/test_intake_log.py::test_append_event_acepta_archivado -v`
Expected: FAIL — conteo `25 != 26`; `archivado` no en el set real; `append_event` lanza `ValueError: Evento desconocido: 'archivado'`.

- [ ] **Step 4: Implementar — añadir `archivado` al `frozenset`**

En `core/intake_log.py`, dentro de `INTAKE_EVENTS`, tras la entrada `"migracion_layout_intake"` (`:68-69`):

```python
    "migracion_layout_intake",  # migración bajo demanda a lotes (#54): details =
                                 # {"lotes": [nombres], "remapeados": {registro: n}}
    "archivado",                # archivo del expediente inviable (RUNBOOK §10; MEJORAS #70.a):
                                 # details = {"motivo": MAYUSCULAS_GUION_BAJO, "fecha": ISO}
})
```

- [ ] **Step 5: Corregir el docstring stale del conteo**

En `core/intake_log.py:9`, sustituir:

```python
- M10-Q1: 17 tipos de evento permitidos (constante ``INTAKE_EVENTS``).
```

por:

```python
- M10-Q1: 26 tipos de evento permitidos (constante ``INTAKE_EVENTS``).
```

- [ ] **Step 6: Ejecutar los tests para verificar que pasan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_intake_log.py -v`
Expected: PASS (toda la suite del módulo verde).

- [ ] **Step 7: Commit**

```bash
git add core/intake_log.py tests/test_intake_log.py
git commit -m "feat(intake-log): evento 'archivado' en INTAKE_EVENTS (B4, MEJORAS #70.a)"
```

---

### Task 2: B3 — helper puro `normalize_es_phone`

**Files:**
- Modify: `core/utils.py` (añadir función; usa `re` ya importado en `:6`)
- Test: `tests/test_utils.py`

**Interfaces:**
- Consumes: nada.
- Produces: `normalize_es_phone(raw: str) -> str` en `core.utils`. Quita separadores y prefijo español (`+34`/`0034`/`34`+len 11); no valida longitud; no toca extranjeros; idempotente.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_utils.py` (con `import pytest` — verificar que ya está; si no, añadirlo):

```python
from core.utils import normalize_es_phone


@pytest.mark.parametrize("raw,esperado", [
    ("+34 600 123 456", "600123456"),
    ("600123456", "600123456"),
    ("0034600123456", "600123456"),
    ("+34600123456", "600123456"),
    ("934 567 890", "934567890"),
    ("34600123456", "600123456"),
    ("(+34) 600-123-456", "600123456"),
    ("", ""),
])
def test_normalize_es_phone(raw, esperado):
    assert normalize_es_phone(raw) == esperado


def test_normalize_es_phone_idempotente():
    for raw in ["+34 600 123 456", "600123456", "0034600123456"]:
        una = normalize_es_phone(raw)
        assert normalize_es_phone(una) == una


def test_normalize_es_phone_extranjero_no_se_mutila():
    # No es +34: no se convierte en un ES de 9 dígitos erróneo.
    assert normalize_es_phone("+33 6 12 34 56 78") == "+33612345678"
```

- [ ] **Step 2: Ejecutar para verificar que fallan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_utils.py -k normalize_es_phone -v`
Expected: FAIL con `ImportError: cannot import name 'normalize_es_phone'`.

- [ ] **Step 3: Implementar el helper**

Añadir a `core/utils.py` (p. ej. tras `text_sha256`, `:25`):

```python
_TEL_SEPARADORES = re.compile(r"[\s.\-/()]+")


def normalize_es_phone(raw: str) -> str:
    """Normaliza un teléfono español a 9 dígitos para el CRM sudespacho.

    El CRM rechaza `+34`, `0034` y espacios (`HTTP 400 movil is incorrect`);
    hay que enviar solo los 9 dígitos. Conservador: quita separadores y el
    prefijo de país español, pero NO valida longitud (eso lo hace el CRM) ni
    toca números extranjeros (`+33…` se dejan intactos salvo separadores).

    Idempotente: ``normalize_es_phone(normalize_es_phone(x)) == normalize_es_phone(x)``.
    """
    if not raw:
        return raw
    s = _TEL_SEPARADORES.sub("", raw)
    if s.startswith("+34"):
        s = s[3:]
    elif s.startswith("0034"):
        s = s[4:]
    elif s.startswith("34") and len(s) == 11:
        s = s[2:]
    return s
```

- [ ] **Step 4: Ejecutar para verificar que pasan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_utils.py -k normalize_es_phone -v`
Expected: PASS (10 casos param + idempotencia + extranjero).

- [ ] **Step 5: Commit**

```bash
git add core/utils.py tests/test_utils.py
git commit -m "feat(utils): normalize_es_phone a 9 digitos (B3)"
```

---

### Task 3: B3 — cablear la normalización en los DTOs

**Files:**
- Modify: `core/sudespacho_relations.py` (import de `normalize_es_phone`; `__post_init__` en `NuevoColaborador` `:188-204` y `NuevoClienteContrario` `:207-223`)
- Test: `tests/test_sudespacho_relations.py`

**Interfaces:**
- Consumes: `core.utils.normalize_es_phone` (Task 2).
- Produces: al construir `NuevoColaborador`/`NuevoClienteContrario`, `movil` (y `telefono` en el colaborador) quedan normalizados. Sin cambios de firma ni de campos.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_sudespacho_relations.py` (los imports de `NuevoColaborador`/`NuevoClienteContrario` ya existen, `:12-13`):

```python
def test_nuevo_colaborador_normaliza_telefonos():
    c = NuevoColaborador(nombre="X", movil="+34 600 123 456", telefono="934 567 890")
    assert c.movil == "600123456"
    assert c.telefono == "934567890"


def test_nuevo_cliente_contrario_normaliza_movil():
    c = NuevoClienteContrario(nombre="X", movil="0034 611 222 333")
    assert c.movil == "611222333"
```

- [ ] **Step 2: Ejecutar para verificar que fallan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sudespacho_relations.py::test_nuevo_colaborador_normaliza_telefonos tests/test_sudespacho_relations.py::test_nuevo_cliente_contrario_normaliza_movil -v`
Expected: FAIL (`c.movil == "+34 600 123 456"`, sin normalizar).

- [ ] **Step 3: Importar el helper**

En `core/sudespacho_relations.py`, junto a los demás imports de `core` (buscar el bloque de `from .` / `from core.`), añadir:

```python
from .utils import normalize_es_phone
```

(Si el módulo importa como `from core.utils import …`, seguir ese estilo para consistencia.)

- [ ] **Step 4: Añadir `__post_init__` a `NuevoColaborador`**

En `core/sudespacho_relations.py`, tras los campos de `NuevoColaborador` (después de `usuarios: …`, `:204`):

```python
    def __post_init__(self) -> None:
        self.movil = normalize_es_phone(self.movil)
        self.telefono = normalize_es_phone(self.telefono)
```

- [ ] **Step 5: Añadir `__post_init__` a `NuevoClienteContrario`**

En `core/sudespacho_relations.py`, tras los campos de `NuevoClienteContrario` (después de `poblacion: str = ""`, `:222`):

```python
    def __post_init__(self) -> None:
        self.movil = normalize_es_phone(self.movil)
```

- [ ] **Step 6: Ejecutar para verificar que pasan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sudespacho_relations.py::test_nuevo_colaborador_normaliza_telefonos tests/test_sudespacho_relations.py::test_nuevo_cliente_contrario_normaliza_movil -v`
Expected: PASS.

- [ ] **Step 7: Regresión del módulo (DTOs no rompen el resto)**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sudespacho_relations.py -v`
Expected: PASS salvo los fallos **ambientales** conocidos que exigen `SUDESPACHO_*` (worktree sin `.env`; idénticos a `main`). Ningún fallo nuevo atribuible a los DTOs.

- [ ] **Step 8: Commit**

```bash
git add core/sudespacho_relations.py tests/test_sudespacho_relations.py
git commit -m "feat(crm): normaliza telefonos en los DTOs de relaciones (B3)"
```

---

### Task 4: Verificación de PR-1 + apertura de PR

**Files:** ninguno (verificación + git).

- [ ] **Step 1: Suite completa a JUnit XML (conteo fiable)**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --junit-xml=.pr1_report.xml`
Expected: 0 fallos nuevos respecto al baseline (~2037 passed; los 5 fallos de `test_sudespacho_relations` que exigen `SUDESPACHO_*` son ambientales del worktree, idénticos a `main`). Revisar el XML: los nuevos tests de Task 1-3 en `passed`.

- [ ] **Step 2: Limpiar el artefacto del reporte**

```bash
rm -f .pr1_report.xml
```

(No debe commitearse; verificar que no queda en `git status`.)

- [ ] **Step 3: Push de la rama y apertura del PR**

```bash
git push -u origin claude/apertura-expediente-b1-b5-785145
```

Abrir el PR con `gh` hacia `main` (título: `PR-1 apertura: quick wins B4 (evento archivado) + B3 (normalizacion telefono)`; cuerpo enlazando la spec §5 y este plan). Confirmar que el check `leak-scan` queda **verde** antes de pedir merge.

- [ ] **Step 4: Revisión adversarial antes de mergear**

Lanzar la revisión de código (skill `requesting-code-review` o workflow de revisión) sobre el diff de la rama. Resolver hallazgos confirmados antes del merge. No mergear con `leak-scan` en rojo ni con `--no-verify`.

---

## Self-Review (hecho al escribir el plan)

- **Cobertura de spec §5:** B4 (Task 1) ✓; B3 helper (Task 2) ✓; B3 en DTOs (Task 3) ✓. Nota de la spec "PR-3 hereda B3" — se cumple porque B3 vive en los DTOs.
- **Placeholders:** ninguno; todo el código y los comandos son literales.
- **Consistencia de tipos:** `normalize_es_phone(str) -> str` idéntica en Task 2 (definición) y Task 3 (consumo). Campos DTO (`movil`/`telefono`) coinciden con `core/sudespacho_relations.py:188-223` verificado.
- **Conteo de eventos:** verificado que el test real asevera `== 25` hoy (`tests/test_intake_log.py:334`) → pasa a `26`; el set `expected` de `test_intake_events_contiene_los_canonicos` también se amplía. Sin este ajuste, Task 1 rompe la suite.
