# `abrir-caso` F1 — Implementation Plan (cerebro puro + CLI local, fuente `drive_ev`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el cerebro puro `core/abrir_caso.py` y el CLI local `scripts/abrir_caso.py` que abren un expediente E&V (alta + intake `drive_ev` + alta CRM con gate) en una sola pasada.

**Architecture:** Cerebro PURO en `core/abrir_caso.py` (naming, colisión, plan de intake, reconciliación por hash, payload CRM — cero I/O, 100% testeable) + orquestador fino Typer en `scripts/abrir_caso.py` que pega `case_manager.ensure_case` + `intake_drive.pull_drive_ev` + hash local + `sudespacho_create.create_expediente` (gate de confirmación) + `intake_log.append_event`. Patrón «biblioteca de casos».

**Tech Stack:** Python 3, `dataclasses`, `hashlib`, `pathlib`, `typer` (CLI), `pytest` (+ `typer.testing.CliRunner`). Reutiliza `core.config`, `core.case_manager`, `core.intake_drive`, `core.intake_log`, `core.sudespacho_create`, `core.utils`, `core.casos.case_locator`.

**Spec:** `docs/superpowers/specs/2026-07-09-abrir-caso-design.md` (F1 = §11).

---

## File Structure

- **Create `core/abrir_caso.py`** — cerebro puro. Dataclasses `Identidad`, `ItemIntake`, `PlanIntake`, `Reconciliacion`; funciones `componer_case_id`, `resolver_identidad`, `plan_intake`, `reconcile`, `crm_payload`. Sin I/O de disco/red (los imports pesados —`sudespacho_create`— son locales dentro de `crm_payload`).
- **Create `scripts/abrir_caso.py`** — orquestador Typer. Helper `hash_tree_local`; comando `main` que ejecuta el pipeline §5 del spec. Único módulo con I/O.
- **Create `tests/test_abrir_caso.py`** — tests unitarios del cerebro (puros, sin FS).
- **Create `tests/test_abrir_caso_cli.py`** — test de integración del CLI (Drive temporal + `pull_drive_ev`/`create_expediente` mockeados).

**Contratos de tipos (consistentes en todo el plan):**

```python
@dataclass(frozen=True)
class Identidad:
    codigo: str            # prefijo, p.ej. "BaRS11"
    direccion: str
    w_code: str            # "W-02Z2NR" (con prefijo W-)
    sufijo: str
    case_id: str           # "<codigo> - <direccion> (<w_code>) - <sufijo>"
    posicion: str          # config.POSICION_ACTORA|DEFENSIVA|OTROS
    w_code_duplicado: bool
    codigo_duplicado: bool
    requiere_confirmacion: bool   # codigo dup + w_code nuevo, política `ask`
    colisiones: tuple[str, ...]   # nombres de casos existentes que colisionan

@dataclass(frozen=True)
class ItemIntake:
    relpath: str    # posix, relativo a la raíz del origen
    dst: str        # posix, relativo a 00_Input/ (p.ej. "01_Drive EV/sub/x.pdf")
    evento: str     # "pull_drive_ev" | "upload_manual" | ...
    sha256: str | None
    size: int
    dup: bool
    zero: bool

@dataclass(frozen=True)
class PlanIntake:
    items: tuple[ItemIntake, ...]
    fuente: str
    @property
    def depositables(self) -> tuple[ItemIntake, ...]: ...   # not dup and not zero
    @property
    def con_sha(self) -> list[dict]: ...                    # [{"path": dst, "sha256": ...}]
    @property
    def categorias(self) -> tuple[str, ...]: ...            # top-level dirs de dst

@dataclass(frozen=True)
class Reconciliacion:
    ok: bool
    faltantes: tuple[str, ...]
    mismatches: tuple[str, ...]
    extras: tuple[str, ...]
```

**Mapas de fuente (constantes de módulo en `core/abrir_caso.py`):**

```python
FUENTE_A_SUBDIR = {
    "drive_ev": "01_Drive EV", "manual": "04_Manual",
    "whatsapp": "02_Whatsapp", "email": "03_Email", "entrevista": "06_Entrevistas",
}
FUENTE_A_EVENTO = {
    "drive_ev": "pull_drive_ev", "manual": "upload_manual",
    "whatsapp": "upload_whatsapp", "email": "upload_email", "entrevista": "upload_entrevista",
}
```
F1 ejercita solo `drive_ev`; el resto entra en F3 (los mapas se definen ya porque son constantes triviales).

---

### Task 1: `componer_case_id` + esqueleto de `core/abrir_caso.py`

**Files:**
- Create: `core/abrir_caso.py`
- Test: `tests/test_abrir_caso.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_abrir_caso.py
from core import abrir_caso
from core.utils import validate_case_id


def test_componer_case_id_formato_canonico():
    cid = abrir_caso.componer_case_id(
        codigo="BaRS11",
        direccion="Passeig Marítim, 30 - Castelldefels (08860)",
        w_code="W-02Z2NR",
        sufijo="Vuelta",
    )
    assert cid == "BaRS11 - Passeig Marítim, 30 - Castelldefels (08860) (W-02Z2NR) - Vuelta"
    # debe pasar la validación canónica del despacho
    assert validate_case_id(cid) == cid
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_abrir_caso.py::test_componer_case_id_formato_canonico -v`
Expected: FAIL con `AttributeError: module 'core.abrir_caso' has no attribute ...` (o ModuleNotFoundError).

- [ ] **Step 3: Write minimal implementation**

```python
# core/abrir_caso.py
"""Cerebro puro de `abrir-caso` (alta + intake + CRM en una pasada).

Cero I/O de disco o red: naming, política de colisión, plan de intake,
reconciliación por hash y construcción del payload CRM. Los orquestadores
(CLI local, skill Cowork) le dan los datos ya leídos y ejecutan los efectos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core import config

FUENTE_A_SUBDIR = {
    "drive_ev": "01_Drive EV", "manual": "04_Manual",
    "whatsapp": "02_Whatsapp", "email": "03_Email", "entrevista": "06_Entrevistas",
}
FUENTE_A_EVENTO = {
    "drive_ev": "pull_drive_ev", "manual": "upload_manual",
    "whatsapp": "upload_whatsapp", "email": "upload_email", "entrevista": "upload_entrevista",
}

_W_CODE_EN_NOMBRE = re.compile(r"\((W-[A-Z0-9]+)\)")


def componer_case_id(*, codigo: str, direccion: str, w_code: str, sufijo: str) -> str:
    """Compone el case_id canónico: '<codigo> - <direccion> (<w_code>) - <sufijo>'.

    Formato validado por core.utils.validate_case_id (regex _CASE_ID_NEW):
    la dirección va pegada al paréntesis de la referencia, sin guion previo.
    """
    return f"{codigo} - {direccion} ({w_code}) - {sufijo}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_abrir_caso.py::test_componer_case_id_formato_canonico -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/abrir_caso.py tests/test_abrir_caso.py
git commit -m "feat(abrir-caso): componer_case_id canónico + esqueleto del cerebro"
```

---

### Task 2: `resolver_identidad` — colisión (`ask`)

**Files:**
- Modify: `core/abrir_caso.py`
- Test: `tests/test_abrir_caso.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_abrir_caso.py (añadir)
import pytest


def _ident(**kw):
    base = dict(codigo="BaRS11", direccion="Tibidabo 8", w_code="W-NUEVO1",
                sufijo="Vuelta", tipo_caso="VUELTA")
    base.update(kw)
    return base


def test_resolver_identidad_sin_colision():
    ident = abrir_caso.resolver_identidad(
        **_ident(), nombres_existentes=["BaRS1 - Otra (W-VIEJO1) - Vuelta"], force=False,
    )
    assert ident.case_id == "BaRS11 - Tibidabo 8 (W-NUEVO1) - Vuelta"
    assert ident.posicion == config.POSICION_ACTORA
    assert not ident.requiere_confirmacion
    assert not ident.w_code_duplicado


def test_resolver_identidad_wcode_duplicado_es_error():
    with pytest.raises(abrir_caso.ColisionCaso):
        abrir_caso.resolver_identidad(
            **_ident(w_code="W-02VND1"),
            nombres_existentes=["BaRS1 - Tibidabo 8 (W-02VND1) - Vuelta"],
            force=False,
        )


def test_resolver_identidad_wcode_duplicado_force_no_lanza():
    ident = abrir_caso.resolver_identidad(
        **_ident(w_code="W-02VND1"),
        nombres_existentes=["BaRS1 - Tibidabo 8 (W-02VND1) - Vuelta"],
        force=True,
    )
    assert ident.w_code_duplicado is True


def test_resolver_identidad_codigo_duplicado_requiere_confirmacion():
    ident = abrir_caso.resolver_identidad(
        **_ident(codigo="BaRS1"),
        nombres_existentes=["BaRS1 - Otra (W-VIEJO1) - Vuelta"],
        force=False,
    )
    assert ident.codigo_duplicado is True
    assert ident.requiere_confirmacion is True
    assert "BaRS1 - Otra (W-VIEJO1) - Vuelta" in ident.colisiones
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_abrir_caso.py -k resolver_identidad -v`
Expected: FAIL con `AttributeError: ... 'resolver_identidad'` / `'ColisionCaso'`.

- [ ] **Step 3: Write minimal implementation**

```python
# core/abrir_caso.py (añadir)


class ColisionCaso(Exception):
    """El W-code ya existe en la ciudad (mismo caso) y no se forzó --force."""


@dataclass(frozen=True)
class Identidad:
    codigo: str
    direccion: str
    w_code: str
    sufijo: str
    case_id: str
    posicion: str
    w_code_duplicado: bool
    codigo_duplicado: bool
    requiere_confirmacion: bool
    colisiones: tuple[str, ...]


def _codigo_de(nombre: str) -> str:
    return nombre.split(" - ", 1)[0].strip()


def _w_code_de(nombre: str) -> str | None:
    m = _W_CODE_EN_NOMBRE.search(nombre)
    return m.group(1) if m else None


def resolver_identidad(
    *,
    codigo: str,
    direccion: str,
    w_code: str,
    sufijo: str,
    tipo_caso: str,
    nombres_existentes: list[str],
    force: bool,
) -> Identidad:
    """Compone el case_id y evalúa la política de colisión (D2 `ask`).

    - w_code duplicado en la ciudad ⇒ ColisionCaso (salvo force).
    - codigo duplicado + w_code nuevo ⇒ requiere_confirmacion=True (el
      orquestador para y pregunta).
    """
    posicion = config.posicion_de_tipo(tipo_caso)  # ValueError si tipo desconocido
    case_id = componer_case_id(codigo=codigo, direccion=direccion, w_code=w_code, sufijo=sufijo)

    colisiones_w = [n for n in nombres_existentes if _w_code_de(n) == w_code]
    colisiones_cod = [n for n in nombres_existentes if _codigo_de(n) == codigo]

    w_dup = bool(colisiones_w)
    cod_dup = bool(colisiones_cod)

    if w_dup and not force:
        raise ColisionCaso(
            f"El W-code {w_code} ya existe en la ciudad: {colisiones_w}. "
            f"Usa --force para forzar."
        )

    requiere_confirmacion = cod_dup and not w_dup

    return Identidad(
        codigo=codigo, direccion=direccion, w_code=w_code, sufijo=sufijo,
        case_id=case_id, posicion=posicion,
        w_code_duplicado=w_dup, codigo_duplicado=cod_dup,
        requiere_confirmacion=requiere_confirmacion,
        colisiones=tuple(dict.fromkeys(colisiones_w + colisiones_cod)),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_abrir_caso.py -k resolver_identidad -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add core/abrir_caso.py tests/test_abrir_caso.py
git commit -m "feat(abrir-caso): resolver_identidad con política de colisión ask/force"
```

---

### Task 3: `plan_intake` — mapeo fuente, dedup, 0-byte

**Files:**
- Modify: `core/abrir_caso.py`
- Test: `tests/test_abrir_caso.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_abrir_caso.py (añadir)


def _inv(relpath, sha, size):
    return {"relpath": relpath, "sha256": sha, "size": size}


def test_plan_intake_mapea_drive_ev_y_marca_dup_y_cero():
    inventario = [
        _inv("ACTIVACION/hoja.pdf", "aaa", 100),
        _inv("OFERTAS/oferta.pdf", "bbb", 200),   # duplicado (ya en log)
        _inv("vacio.txt", "e3b0c4", 0),           # 0-byte
    ]
    # log con un evento previo cuyo fichero tenía sha "bbb"
    log_existente = [
        {"event": "pull_drive_ev", "details": {"files": [{"path": "01_Drive EV/x", "sha256": "bbb"}]}},
    ]
    plan = abrir_caso.plan_intake(inventario, log_existente, "drive_ev")

    assert plan.fuente == "drive_ev"
    by_rel = {i.relpath: i for i in plan.items}
    assert by_rel["ACTIVACION/hoja.pdf"].dst == "01_Drive EV/ACTIVACION/hoja.pdf"
    assert by_rel["ACTIVACION/hoja.pdf"].evento == "pull_drive_ev"
    assert by_rel["OFERTAS/oferta.pdf"].dup is True
    assert by_rel["vacio.txt"].zero is True

    # depositables = ni dup ni 0-byte
    assert {i.relpath for i in plan.depositables} == {"ACTIVACION/hoja.pdf"}
    assert plan.con_sha == [{"path": "01_Drive EV/ACTIVACION/hoja.pdf", "sha256": "aaa"}]
    assert plan.categorias == ("01_Drive EV",)


def test_plan_intake_fuente_desconocida():
    with pytest.raises(ValueError):
        abrir_caso.plan_intake([], [], "inexistente")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_abrir_caso.py -k plan_intake -v`
Expected: FAIL con `AttributeError: ... 'plan_intake'`.

- [ ] **Step 3: Write minimal implementation**

```python
# core/abrir_caso.py (añadir)


@dataclass(frozen=True)
class ItemIntake:
    relpath: str
    dst: str
    evento: str
    sha256: str | None
    size: int
    dup: bool
    zero: bool


@dataclass(frozen=True)
class PlanIntake:
    items: tuple[ItemIntake, ...]
    fuente: str

    @property
    def depositables(self) -> tuple[ItemIntake, ...]:
        return tuple(i for i in self.items if not i.dup and not i.zero)

    @property
    def con_sha(self) -> list[dict]:
        return [{"path": i.dst, "sha256": i.sha256} for i in self.depositables]

    @property
    def categorias(self) -> tuple[str, ...]:
        vistos: list[str] = []
        for i in self.depositables:
            top = i.dst.split("/", 2)[1] if "/" in i.dst else i.dst
            # top-level DENTRO de la subcarpeta de fuente (p.ej. 01_Drive EV/ACTIVACION)
        # categorías = primeras dos componentes de dst (subdir de fuente + categoría)
        out: list[str] = []
        for i in self.depositables:
            partes = i.dst.split("/")
            base = partes[0]
            if base not in out:
                out.append(base)
        return tuple(out)


def _shas_en_log(log_existente: list[dict]) -> set[str]:
    shas: set[str] = set()
    for ev in log_existente:
        for f in (ev.get("details") or {}).get("files") or []:
            s = f.get("sha256")
            if s:
                shas.add(s)
    return shas


def plan_intake(inventario: list[dict], log_existente: list[dict], fuente: str) -> PlanIntake:
    """Construye el plan de depósito (puro). Sin tocar bytes.

    inventario: [{"relpath": posix, "sha256": str|None, "size": int}, ...].
    """
    if fuente not in FUENTE_A_SUBDIR:
        raise ValueError(f"Fuente desconocida: {fuente!r}. Válidas: {sorted(FUENTE_A_SUBDIR)}")
    subdir = FUENTE_A_SUBDIR[fuente]
    evento = FUENTE_A_EVENTO[fuente]
    shas_previos = _shas_en_log(log_existente)

    items: list[ItemIntake] = []
    for entry in inventario:
        rel = entry["relpath"]
        sha = entry.get("sha256")
        size = int(entry.get("size", 0))
        items.append(ItemIntake(
            relpath=rel,
            dst=f"{subdir}/{rel}",
            evento=evento,
            sha256=sha,
            size=size,
            dup=bool(sha) and sha in shas_previos,
            zero=size == 0,
        ))
    return PlanIntake(items=tuple(items), fuente=fuente)
```

> Nota: la propiedad `categorias` devuelve la subcarpeta de primer nivel de `dst`
> (p.ej. `"01_Drive EV"`); el orquestador Cowork la usa para copiar por lote. En el
> frente local no se usa (el pull ya depositó). Limpiar el bucle muerto del borrador
> anterior si quedó (dejar solo la segunda mitad).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_abrir_caso.py -k plan_intake -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add core/abrir_caso.py tests/test_abrir_caso.py
git commit -m "feat(abrir-caso): plan_intake (mapeo fuente, dedup por sha, 0-byte)"
```

---

### Task 4: `reconcile` — verificación por hash

**Files:**
- Modify: `core/abrir_caso.py`
- Test: `tests/test_abrir_caso.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_abrir_caso.py (añadir)


def _plan_una(dst="01_Drive EV/ACTIVACION/hoja.pdf", sha="aaa"):
    item = abrir_caso.ItemIntake(relpath="ACTIVACION/hoja.pdf", dst=dst, evento="pull_drive_ev",
                                 sha256=sha, size=100, dup=False, zero=False)
    return abrir_caso.PlanIntake(items=(item,), fuente="drive_ev")


def test_reconcile_ok():
    plan = _plan_una()
    rec = abrir_caso.reconcile(plan, {"01_Drive EV/ACTIVACION/hoja.pdf": "aaa"})
    assert rec.ok is True
    assert rec.faltantes == () and rec.mismatches == () and rec.extras == ()


def test_reconcile_mismatch_y_faltante_y_extra():
    plan = _plan_una()
    rec = abrir_caso.reconcile(plan, {"01_Drive EV/ACTIVACION/hoja.pdf": "ZZZ",
                                      "01_Drive EV/extra.pdf": "qqq"})
    assert rec.ok is False
    assert "01_Drive EV/ACTIVACION/hoja.pdf" in rec.mismatches
    assert "01_Drive EV/extra.pdf" in rec.extras

    rec2 = abrir_caso.reconcile(plan, {})
    assert rec2.ok is False
    assert "01_Drive EV/ACTIVACION/hoja.pdf" in rec2.faltantes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_abrir_caso.py -k reconcile -v`
Expected: FAIL con `AttributeError: ... 'reconcile'`.

- [ ] **Step 3: Write minimal implementation**

```python
# core/abrir_caso.py (añadir)


@dataclass(frozen=True)
class Reconciliacion:
    ok: bool
    faltantes: tuple[str, ...]
    mismatches: tuple[str, ...]
    extras: tuple[str, ...]


def reconcile(plan: PlanIntake, hashes_destino: dict[str, str]) -> Reconciliacion:
    """Verifica el depósito contra el plan (puro).

    hashes_destino: {relpath_desde_00_Input: sha256} de lo realmente en disco.
    Compara solo los depositables del plan.
    """
    esperados = {i.dst: i.sha256 for i in plan.depositables}
    faltantes = tuple(sorted(d for d in esperados if d not in hashes_destino))
    mismatches = tuple(sorted(
        d for d, s in esperados.items()
        if d in hashes_destino and s is not None and hashes_destino[d] != s
    ))
    extras = tuple(sorted(d for d in hashes_destino if d not in esperados))
    ok = not (faltantes or mismatches or extras)
    return Reconciliacion(ok=ok, faltantes=faltantes, mismatches=mismatches, extras=extras)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_abrir_caso.py -k reconcile -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add core/abrir_caso.py tests/test_abrir_caso.py
git commit -m "feat(abrir-caso): reconcile (faltantes/mismatch/extras por hash)"
```

---

### Task 5: `crm_payload` — DTO extrajudicial

**Files:**
- Modify: `core/abrir_caso.py`
- Test: `tests/test_abrir_caso.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_abrir_caso.py (añadir)


def test_crm_payload_extrajudicial_actora():
    ident = abrir_caso.resolver_identidad(
        **_ident(codigo="BaRS11", w_code="W-02Z2NR"),
        nombres_existentes=[], force=False,
    )
    dto = abrir_caso.crm_payload(ident, tipo_caso="VUELTA", cuantia=15000.0)
    from core import sudespacho_create as sc
    assert isinstance(dto, sc.NuevoExpedienteExtrajudicial)
    assert dto.referencia_cliente == ident.case_id
    assert dto.cuantia == 15000.0
    assert dto.posicion == sc.POSICION_ACTOR           # actora → ACTOR
    # tags base del tipo de caso presentes
    assert dto.tags == sc.tag_defaults_for_tipo_caso("VUELTA")


def test_crm_payload_defensiva_mapea_demandado():
    ident = abrir_caso.resolver_identidad(
        **_ident(codigo="BaRS11", w_code="W-02Z2NR", tipo_caso="LAU_20"),
        nombres_existentes=[], force=False,
    )
    dto = abrir_caso.crm_payload(ident, tipo_caso="LAU_20", cuantia=0.0)
    from core import sudespacho_create as sc
    assert dto.posicion == sc.POSICION_DEMANDADO
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_abrir_caso.py -k crm_payload -v`
Expected: FAIL con `AttributeError: ... 'crm_payload'`.

- [ ] **Step 3: Write minimal implementation**

```python
# core/abrir_caso.py (añadir)


def crm_payload(identidad: Identidad, *, tipo_caso: str, cuantia: float = 0.0):
    """Construye el DTO NuevoExpedienteExtrajudicial para sudespacho.

    Import local de sudespacho_create para no arrastrar sus deps de red al
    importar el cerebro.
    """
    from core import sudespacho_create as sc

    posicion_crm = {
        config.POSICION_ACTORA: sc.POSICION_ACTOR,
        config.POSICION_DEFENSIVA: sc.POSICION_DEMANDADO,
        config.POSICION_OTROS: sc.POSICION_ACTOR,
    }[identidad.posicion]

    return sc.NuevoExpedienteExtrajudicial(
        referencia_cliente=identidad.case_id,
        cuantia=cuantia,
        tags=sc.tag_defaults_for_tipo_caso(tipo_caso),
        posicion=posicion_crm,
    )
```

> Nota: los tags de equipo (rojo) y ciudad (azul) los añade el orquestador/despacho
> según el Market Center; F1 usa solo los tags base del tipo de caso
> (`tag_defaults_for_tipo_caso`). El expediente judicial y sus tags quedan para fuera de F1.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_abrir_caso.py -k crm_payload -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add core/abrir_caso.py tests/test_abrir_caso.py
git commit -m "feat(abrir-caso): crm_payload (DTO extrajudicial + mapeo de posición)"
```

---

### Task 6: `hash_tree_local` — hash recursivo en disco (orquestador)

**Files:**
- Create: `scripts/abrir_caso.py`
- Test: `tests/test_abrir_caso_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_abrir_caso_cli.py
import hashlib
from pathlib import Path

from scripts import abrir_caso as cli


def test_hash_tree_local(tmp_path: Path):
    root = tmp_path / "01_Drive EV"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_bytes(b"hola")
    (root / "sub" / "b.txt").write_bytes(b"mundo")

    hashes = cli.hash_tree_local(root, prefijo="01_Drive EV")

    assert hashes["01_Drive EV/a.txt"] == hashlib.sha256(b"hola").hexdigest()
    assert hashes["01_Drive EV/sub/b.txt"] == hashlib.sha256(b"mundo").hexdigest()
    assert len(hashes) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_abrir_caso_cli.py::test_hash_tree_local -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'scripts.abrir_caso'` (o AttributeError).

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/abrir_caso.py
"""CLI local: abrir un expediente E&V (alta + intake drive_ev + CRM) en una pasada.

Orquestador fino sobre el cerebro puro core.abrir_caso. Único módulo con I/O.

Uso:
  python -m scripts.abrir_caso --w-code W-02Z2NR --ciudad Barcelona \\
      --tipo-caso VUELTA --codigo-caso BaRS11 --sufijo "Vuelta" \\
      --direccion "Passeig Marítim, 30 - Castelldefels (08860)" \\
      --folder-id <id> --team-id <shared-drive>
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def hash_tree_local(root: Path, *, prefijo: str) -> dict[str, str]:
    """SHA-256 recursivo de todos los ficheros bajo root.

    Devuelve {"<prefijo>/<relpath posix>": sha256hex}. Si root no existe, {}.
    """
    if not root.is_dir():
        return {}
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        rel = p.relative_to(root).as_posix()
        out[f"{prefijo}/{rel}"] = h.hexdigest()
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_abrir_caso_cli.py::test_hash_tree_local -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_cli.py
git commit -m "feat(abrir-caso): hash_tree_local (hash recursivo en disco)"
```

---

### Task 7: CLI orquestador `main` — pipeline completo con gate CRM

**Files:**
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_abrir_caso_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_abrir_caso_cli.py (añadir)
import pytest
from typer.testing import CliRunner

from core import case_manager, intake_log
from core.casos import case_locator


@pytest.fixture
def drive_temporal(tmp_path, monkeypatch):
    """Apunta CASOS_ROOT al tmp y mockea el pull rclone y el alta CRM."""
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)

    # Mock del pull: deposita 2 ficheros en 00_Input/01_Drive EV y devuelve un stub
    def fake_pull(case_id, folder_id, team_id, *, force=False):
        dest = case_locator.path_for(case_id) / "00_Input" / "01_Drive EV" / "ACTIVACION"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "hoja.pdf").write_bytes(b"contenido-1")
        (dest.parent / "oferta.pdf").write_bytes(b"contenido-2")
        return type("R", (), {"count": 2})()

    monkeypatch.setattr("core.intake_drive.pull_drive_ev", fake_pull)
    monkeypatch.setattr("core.sudespacho_create.create_expediente", lambda dto, **kw: "9999")
    return root


def _args(**over):
    base = [
        "--w-code", "W-02Z2NR", "--ciudad", "Barcelona", "--tipo-caso", "VUELTA",
        "--codigo-caso", "BaRS11", "--sufijo", "Vuelta",
        "--direccion", "Passeig Marítim 30",
        "--folder-id", "FID", "--team-id", "TID", "--yes",
    ]
    for k, v in over.items():
        base += [f"--{k}", v]
    return base


def test_cli_pasada_completa_crea_intake_log_y_crm(drive_temporal):
    result = CliRunner().invoke(cli.app, _args())
    assert result.exit_code == 0, result.output

    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    case_dir = case_locator.path_for(case_id)
    assert (case_dir / "00_Input" / "01_Drive EV" / "ACTIVACION" / "hoja.pdf").is_file()

    # evento pull_drive_ev con sha256 por fichero (D4)
    eventos = intake_log.read_events(case_id)
    pulls = [e for e in eventos if e["event"] == "pull_drive_ev"]
    assert pulls and pulls[-1]["details"]["files"]
    assert all(f["sha256"] for f in pulls[-1]["details"]["files"])

    # CRM registrado en _caso.md
    import yaml
    fm = yaml.safe_load((case_dir / "00_Input" / "_caso.md").read_text(encoding="utf-8").split("---")[1])
    ids = [e["id"] for e in fm["meta"]["sudespacho_expedientes"]]
    assert "9999" in ids


def test_cli_idempotente_no_dobla_intake_ni_crm(drive_temporal, monkeypatch):
    llamadas = {"crm": 0}
    def contando(dto, **kw):
        llamadas["crm"] += 1
        return "9999"
    monkeypatch.setattr("core.sudespacho_create.create_expediente", contando)

    CliRunner().invoke(cli.app, _args())
    CliRunner().invoke(cli.app, _args())

    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    fm_txt = (case_locator.path_for(case_id) / "00_Input" / "_caso.md").read_text(encoding="utf-8")
    import yaml
    fm = yaml.safe_load(fm_txt.split("---")[1])
    # una sola entrada CRM pese a dos corridas (register_expediente es idempotente)
    assert len(fm["meta"]["sudespacho_expedientes"]) == 1


def test_cli_dry_run_no_escribe_crm(drive_temporal, monkeypatch):
    llamadas = {"crm": 0}
    monkeypatch.setattr("core.sudespacho_create.create_expediente",
                        lambda dto, **kw: llamadas.__setitem__("crm", llamadas["crm"] + 1) or "9999")
    result = CliRunner().invoke(cli.app, _args(**{"dry-run": ""}) if False else _args() + ["--dry-run"])
    assert result.exit_code == 0
    assert llamadas["crm"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_abrir_caso_cli.py -k "pasada or idempotente or dry_run" -v`
Expected: FAIL (el comando `app`/`main` aún no existe).

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/abrir_caso.py (añadir imports arriba y el comando)
import typer

from core import abrir_caso as brain
from core import case_manager, intake_drive, intake_log, sudespacho_create
from core.casos import case_locator

app = typer.Typer(add_completion=False, help="Abrir un expediente E&V en una pasada")

_ELEMENT_EXTRAJUDICIAL = "extrajudiciales"


@app.command()
def main(
    w_code: str = typer.Option(..., "--w-code"),
    ciudad: str = typer.Option(..., "--ciudad"),
    tipo_caso: str = typer.Option(..., "--tipo-caso"),
    codigo_caso: str = typer.Option(..., "--codigo-caso"),
    sufijo: str = typer.Option(..., "--sufijo"),
    direccion: str = typer.Option(..., "--direccion"),
    folder_id: str = typer.Option(None, "--folder-id"),
    team_id: str = typer.Option(None, "--team-id"),
    cuantia: float = typer.Option(0.0, "--cuantia"),
    crm: str = typer.Option("api", "--crm", help="api|skip"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes", help="auto-confirma el gate CRM"),
) -> None:
    # 5.1 identidad + colisión
    nombres = [p.name for p in case_locator.list_cases(ciudad)]
    try:
        ident = brain.resolver_identidad(
            codigo=codigo_caso, direccion=direccion, w_code=w_code, sufijo=sufijo,
            tipo_caso=tipo_caso, nombres_existentes=nombres, force=force,
        )
    except brain.ColisionCaso as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1)
    if ident.requiere_confirmacion and not force:
        typer.echo(f"⚠️ El código {ident.codigo} ya existe: {ident.colisiones}")
        if not (yes or typer.confirm("¿Crear igualmente con este código?")):
            raise typer.Exit(code=1)

    # 5.2 esqueleto
    case_manager.ensure_case(
        ident.case_id, titulo=ident.case_id, referencia_crm=ident.case_id,
        tipo_caso=tipo_caso, ciudad=ciudad, direccion=direccion,
    )
    case_dir = case_locator.path_for(ident.case_id)

    # 5.3 pull + hash local (D4)
    intake_drive.pull_drive_ev(ident.case_id, folder_id, team_id)
    subdir = brain.FUENTE_A_SUBDIR["drive_ev"]
    hashes = hash_tree_local(case_dir / "00_Input" / subdir, prefijo=subdir)

    # 5.4 plan
    inventario = [
        {"relpath": k[len(subdir) + 1:], "sha256": v,
         "size": (case_dir / "00_Input" / k).stat().st_size}
        for k, v in hashes.items()
    ]
    plan = brain.plan_intake(inventario, intake_log.read_events(ident.case_id), "drive_ev")
    if dry_run:
        typer.echo(f"[dry-run] {len(plan.depositables)} depositables, "
                   f"{len(plan.items) - len(plan.depositables)} omitidos")
        raise typer.Exit(code=0)

    # 5.6 reconcile
    rec = brain.reconcile(plan, hashes)
    if not rec.ok:
        typer.echo(f"❌ Reconciliación falló: faltan={rec.faltantes} "
                   f"mismatch={rec.mismatches} extra={rec.extras}")
        raise typer.Exit(code=1)

    # 5.7 log forense con sha256
    if plan.con_sha:
        intake_log.append_event(ident.case_id, "pull_drive_ev",
                                details={"count": len(plan.con_sha), "files": plan.con_sha})

    # 5.9 alta CRM con gate
    if crm == "api":
        payload = brain.crm_payload(ident, tipo_caso=tipo_caso, cuantia=cuantia)
        typer.echo(f"CRM → alta extrajudicial ref={payload.referencia_cliente} "
                   f"posicion={payload.posicion} tags={payload.tags} cuantia={payload.cuantia}")
        if yes or typer.confirm("¿Dar de alta en el CRM?"):
            exp_id = sudespacho_create.create_expediente(payload)
            case_manager.register_expediente(ident.case_id, exp_id, _ELEMENT_EXTRAJUDICIAL)
            typer.echo(f"✓ CRM id={exp_id}")
    else:
        typer.echo("CRM omitido (--crm skip): referencia pendiente + TODO")

    typer.echo(f"✓ Caso abierto: {ident.case_id}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_abrir_caso_cli.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_cli.py
git commit -m "feat(abrir-caso): CLI local — pipeline alta+intake+CRM con gate y dry-run"
```

---

### Task 8: Suite verde completa + regresión de `pull_drive_ev`

**Files:**
- Test: (verificación; sin cambios de producción salvo que aparezca una regresión)

- [ ] **Step 1: Correr el módulo nuevo aislado**

Run: `python -m pytest tests/test_abrir_caso.py tests/test_abrir_caso_cli.py -v`
Expected: PASS (todos los tests de Tasks 1-7).

- [ ] **Step 2: Correr los tests de las piezas reutilizadas (no romper nada)**

Run: `python -m pytest tests/test_case_manager.py tests/test_intake_log.py tests/test_intake_drive.py -q`
Expected: PASS (sin regresiones; `pull_drive_ev` intacto — F1 no modifica su firma, solo lo consume).

- [ ] **Step 3: Suite completa**

Run: `python -m pytest -q --tb=short`
Expected: verde (número base + los tests nuevos; cualquier fallo pre-existente conocido se documenta en STATUS.md, no se introduce ninguno nuevo).

- [ ] **Step 4: Commit (si hubo algún ajuste de regresión)**

```bash
git add -A
git commit -m "test(abrir-caso): suite verde F1 + verificación de no-regresión"
```

---

## Self-Review

**1. Spec coverage (F1 = §11 del spec):**
- §5.1 resolver_identidad + colisión `ask` → Task 2 ✓
- §5.2 ensure_case → Task 7 (orquestador) ✓
- §5.3 pull_drive_ev + hash local (D4) → Tasks 6, 7 ✓
- §5.4 plan_intake → Task 3 ✓
- §5.6 reconcile → Tasks 4, 7 ✓
- §5.7 append_event con sha256 → Task 7 ✓
- §5.8 _caso.md idempotente → Task 7 (ensure_case) + test idempotencia ✓
- §5.9 gate CRM + create_expediente + register_expediente → Task 5, 7 ✓
- §13 Tests (unit puros + integración + idempotencia + dry-run) → Tasks 1-8 ✓
- **Fuera de F1 (correcto que NO estén):** conector `hash_tree`/`strip_top_level` (F2), skill Cowork (F2), fuentes manual/whatsapp/email (F3), expediente judicial, tags equipo/ciudad, guard §6 sobre caso prestado (un caso recién creado nace `disponible`; el test de guard §6 del spec §13 se cubre en F2/F3 cuando aplique a un caso prestado real).

**2. Placeholder scan:** sin TBD/TODO. Todo paso con código muestra el código. La `nota` de `categorias` en Task 3 avisa de limpiar un bucle muerto — el código final que dejo es el correcto (segunda mitad); el implementador debe borrar el primer `for` exploratorio si lo copió.

**3. Type consistency:** `Identidad`, `ItemIntake`, `PlanIntake`, `Reconciliacion` y sus campos son idénticos en definición (Tasks 2-4) y uso (Tasks 5, 7). `resolver_identidad(**kwargs, nombres_existentes, force)`, `plan_intake(inventario, log_existente, fuente)`, `reconcile(plan, hashes_destino)`, `crm_payload(ident, *, tipo_caso, cuantia)`, `hash_tree_local(root, *, prefijo)` — firmas consistentes en tests y orquestador. `_ELEMENT_EXTRAJUDICIAL = "extrajudiciales"` coincide con el `element` esperado por `register_expediente` (metadata local).

**Riesgo residual a validar en ejecución:** (a) el mock `fake_pull` del test deposita en la ruta que `hash_tree_local` luego lee — verificado en el flujo; (b) `create_expediente` real espera `SUDESPACHO_API_KEY` en entorno — por eso el test lo mockea; la corrida en vivo contra el CRM es manual y fuera de la suite (como el resto de integraciones CRM del repo).
