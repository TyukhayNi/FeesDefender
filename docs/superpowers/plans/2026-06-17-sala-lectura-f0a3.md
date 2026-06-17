# Sala de lectura Fases 0–3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Formalize the human layer of `01_Procesado`: document catalog (`indice_documental.yaml`), scaffolding for `Sala lectura/` + `MD/` + `_revisar/`, and reroute markdown generation to `01_Procesado/MD/`.

**Architecture:** New module `core/catalogo_documental.py` builds a YAML catalog from inventory data — the canonical document source of truth per case. `ensure_case` gains three new subdirectories under `01_Procesado`. `markdown_generator.build` changes its output path from `01_Procesado/{slug}.md` to `01_Procesado/MD/{slug}.md`.

**Tech Stack:** Python, PyYAML 6.x, pytest. No new dependencies.

**Non-collision constraint:** Do NOT modify `core/intake_manifest.py`, `core/intake_log.py`, `streamlit_app.py`, nor create `core/whatsapp_*.py` (parallel worktree boundary).

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `core/catalogo_documental.py` | Catalog YAML builder + loader |
| Modify | `core/case_manager.py:262-268` | Add `Sala lectura/`, `MD/`, `_revisar/` subdirs |
| Modify | `core/markdown_generator.py:25-26` | Change output from `01_Procesado/` to `01_Procesado/MD/` |
| Create | `tests/test_catalogo_documental.py` | Tests for catalog module |
| Modify | `tests/test_extractor_skip.py:72,80,82,90,94` | Adjust path expectations to `MD/` |
| Modify | `tests/test_pipeline.py` | (no change needed — mocks don't check paths) |

---

### Task 0: Verify Phase 0 already closed (doble extract_all)

**Files:** read-only verification

- [ ] **Step 1: Confirm the fix is in place**

Read `core/pipeline.py` — `extract_all` is called once (line 79), result stored in `extraction` (line 75), passed to `markdown_generator.build` (line 85). The existing test `test_extract_all_se_ejecuta_una_sola_vez` covers this regression.

- [ ] **Step 2: Run the regression test**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: PASS

**No code changes. Phase 0 was closed in session 32.**

---

### Task 1: Catalog module — `core/catalogo_documental.py`

**Files:**
- Create: `core/catalogo_documental.py`
- Create: `tests/test_catalogo_documental.py`

#### Step 1: Write the failing tests

- [ ] **1a: Test build produces YAML with correct schema**

```python
def test_build_catalog_genera_yaml_con_esquema_correcto(tmp_casos_root):
    from core import case_manager, inventory
    import importlib
    importlib.reload(case_manager)
    importlib.reload(inventory)
    from core import catalogo_documental
    importlib.reload(catalogo_documental)

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    doc = case_dir / "00_Input" / "01_Drive EV" / "contrato.pdf"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_bytes(b"%PDF-fake-content")
    inventory.scan("EV-2026-TEST")

    path = catalogo_documental.build_catalog("EV-2026-TEST")

    assert path.name == "indice_documental.yaml"
    assert path.exists()

    entries = catalogo_documental.load_catalog("EV-2026-TEST")
    assert len(entries) == 1
    e = entries[0]
    assert e.ruta_relativa == "01_Drive EV/contrato.pdf"
    assert e.nombre_original == "contrato.pdf"
    assert e.fuente == "drive_ev"
    assert e.estado == "original"
    assert e.hash  # non-empty sha256
    assert e.id_doc == e.hash[:12]
    assert e.fecha_indexado  # non-empty ISO timestamp
    # D9 fields present with null defaults
    assert e.parent_id is None
    assert e.orden_en_bundle is None
```

- [ ] **1b: Test multiple sources mapped correctly**

```python
def test_build_catalog_mapea_fuentes(tmp_casos_root):
    from core import case_manager, inventory
    import importlib
    importlib.reload(case_manager)
    importlib.reload(inventory)
    from core import catalogo_documental
    importlib.reload(catalogo_documental)

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    for sub, name in [
        ("01_Drive EV", "doc1.txt"),
        ("05_CRM/01_Demanda", "doc2.txt"),
        ("02_Whatsapp/00_Consultor propietario", "chat.txt"),
    ]:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"contenido {name}", encoding="utf-8")
    inventory.scan("EV-2026-TEST")

    catalogo_documental.build_catalog("EV-2026-TEST")
    entries = catalogo_documental.load_catalog("EV-2026-TEST")
    fuentes = {e.nombre_original: e.fuente for e in entries}

    assert fuentes["doc1.txt"] == "drive_ev"
    assert fuentes["doc2.txt"] == "crm"
    assert fuentes["chat.txt"] == "whatsapp"
```

- [ ] **1c: Test idempotency — second run preserves entries**

```python
def test_build_catalog_idempotente(tmp_casos_root):
    from core import case_manager, inventory
    import importlib
    importlib.reload(case_manager)
    importlib.reload(inventory)
    from core import catalogo_documental
    importlib.reload(catalogo_documental)

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    (case_dir / "00_Input" / "nota.txt").write_text("hola", encoding="utf-8")
    inventory.scan("EV-2026-TEST")

    catalogo_documental.build_catalog("EV-2026-TEST")
    entries1 = catalogo_documental.load_catalog("EV-2026-TEST")
    ts1 = entries1[0].fecha_indexado

    catalogo_documental.build_catalog("EV-2026-TEST")
    entries2 = catalogo_documental.load_catalog("EV-2026-TEST")

    assert len(entries2) == 1
    assert entries2[0].fecha_indexado == ts1  # preserved, not re-stamped
```

- [ ] **1d: Test load_catalog returns empty for non-existent catalog**

```python
def test_load_catalog_sin_archivo(tmp_casos_root):
    from core import case_manager
    import importlib
    importlib.reload(case_manager)
    from core import catalogo_documental
    importlib.reload(catalogo_documental)

    case_manager.ensure_case("EV-2026-TEST")
    entries = catalogo_documental.load_catalog("EV-2026-TEST")
    assert entries == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_catalogo_documental.py -v`
Expected: FAIL (module does not exist)

- [ ] **Step 3: Implement `core/catalogo_documental.py`**

```python
"""Catálogo documental canónico: indice_documental.yaml.

Fuente de verdad documental por caso. Alimenta INDICE.md / CRONOLOGIA.md
(renders de solo lectura, fases futuras). Cada documento de 00_Input/
tiene exactamente una entrada.
"""
from __future__ import annotations

import yaml
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import caso_path
from .inventory import load as load_inventory
from .utils import now_iso

CATALOG_FILENAME = "indice_documental.yaml"

_SOURCE_MAP = {
    "01_Drive EV": "drive_ev",
    "02_Whatsapp": "whatsapp",
    "03_Email": "email",
    "04_Manual": "manual",
    "05_CRM": "crm",
    "06_Entrevistas": "entrevistas",
}


@dataclass
class CatalogEntry:
    id_doc: str
    ruta_relativa: str
    nombre_original: str
    tipo_documental: str | None = None
    fecha_doc: str | None = None
    parte: str | None = None
    fuente: str = ""
    estado: str = "original"
    hash: str = ""
    fecha_indexado: str = ""
    parent_id: str | None = None
    orden_en_bundle: int | None = None


def _catalog_path(case_id: str) -> Path:
    return caso_path(case_id) / "01_Procesado" / CATALOG_FILENAME


def _map_source(inventory_source: str) -> str:
    return _SOURCE_MAP.get(inventory_source, inventory_source)


def load_catalog(case_id: str) -> list[CatalogEntry]:
    path = _catalog_path(case_id)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not data:
        return []
    return [CatalogEntry(**entry) for entry in data]


def build_catalog(case_id: str) -> Path:
    inv = load_inventory(case_id)
    path = _catalog_path(case_id)

    existing = load_catalog(case_id) if path.exists() else []
    existing_by_hash = {e.hash: e for e in existing if e.hash}

    now = now_iso()
    entries: list[CatalogEntry] = []

    for f in inv["files"]:
        sha = f.get("sha256", "")
        if sha and sha in existing_by_hash:
            entries.append(existing_by_hash[sha])
            continue

        rel = f["rel_path"]
        entries.append(CatalogEntry(
            id_doc=sha[:12] if sha else rel,
            ruta_relativa=rel,
            nombre_original=f["name"],
            fuente=_map_source(f.get("source", "manual")),
            hash=sha,
            fecha_indexado=now,
        ))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(
            [asdict(e) for e in entries],
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_catalogo_documental.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add core/catalogo_documental.py tests/test_catalogo_documental.py
git commit -m "feat(catalogo): módulo indice_documental.yaml con parent_id/orden_en_bundle (Fase 1)"
```

---

### Task 2: Scaffolding — `Sala lectura/`, `MD/`, `_revisar/`

**Files:**
- Modify: `core/case_manager.py` (~line 262)
- Modify: `tests/test_extractor_skip.py` (existing test uses `01_Procesado` paths)

- [ ] **Step 1: Write a failing test for the new subdirs**

Add to `tests/test_catalogo_documental.py` (co-located, same feature):

```python
def test_ensure_case_crea_subdirs_sala_lectura(tmp_casos_root):
    from core import case_manager
    import importlib
    importlib.reload(case_manager)

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    procesado = case_dir / "01_Procesado"

    assert (procesado / "Sala lectura").is_dir()
    assert (procesado / "MD").is_dir()
    assert (procesado / "_revisar").is_dir()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_catalogo_documental.py::test_ensure_case_crea_subdirs_sala_lectura -v`
Expected: FAIL — dirs don't exist

- [ ] **Step 3: Add subdirectory creation to `ensure_case`**

In `core/case_manager.py`, after the line `for sub in CASO_SUBDIRS:` block (~line 264), add:

```python
    # Subestructura de 01_Procesado (sala de lectura + MD + cuarentena)
    for sub01 in ("Sala lectura", "MD", "_revisar"):
        (case_dir / "01_Procesado" / sub01).mkdir(exist_ok=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_catalogo_documental.py::test_ensure_case_crea_subdirs_sala_lectura -v`
Expected: PASS

- [ ] **Step 5: Run full suite to check for regressions**

Run: `python -m pytest -q --tb=short --ignore=tests/test_sudespacho_relations.py`
Expected: all green (836 + new tests passed)

- [ ] **Step 6: Commit**

```bash
git add core/case_manager.py tests/test_catalogo_documental.py
git commit -m "feat(scaffold): Sala lectura + MD + _revisar en 01_Procesado (Fase 2)"
```

---

### Task 3: Reroute MD to `01_Procesado/MD/` (Fase 3)

**Files:**
- Modify: `core/markdown_generator.py:25-26`
- Modify: `tests/test_extractor_skip.py:72,80,82,90,94`

- [ ] **Step 1: Write a targeted failing test**

Add to `tests/test_catalogo_documental.py`:

```python
def test_markdown_build_escribe_en_md_subdir(tmp_casos_root):
    from core import case_manager, markdown_generator
    from core.extractor import ExtractionResult
    import importlib
    importlib.reload(case_manager)
    importlib.reload(markdown_generator)

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    raw = case_dir / "01_Procesado" / "raw_text"
    raw.mkdir(parents=True, exist_ok=True)
    txt = raw / "nota.txt"
    txt.write_text("texto extraido", encoding="utf-8")

    res = ExtractionResult(
        rel_path="nota.txt", output_path=txt, chars=14, method="raw", skipped=False,
    )
    paths = markdown_generator.build("EV-2026-TEST", [res])
    md = paths[0]

    # MD goes to 01_Procesado/MD/, NOT flat in 01_Procesado/
    assert md.parent.name == "MD"
    assert md.parent.parent.name == "01_Procesado"
    assert md.name == "nota.md"
    assert md.exists()
    # Old flat path should NOT exist
    assert not (case_dir / "01_Procesado" / "nota.md").exists()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_catalogo_documental.py::test_markdown_build_escribe_en_md_subdir -v`
Expected: FAIL — MD goes to wrong directory

- [ ] **Step 3: Change output directory in `markdown_generator.py`**

In `core/markdown_generator.py` line 25, change:

```python
# Before:
    out_dir = caso_path(case_id) / "01_Procesado"
# After:
    out_dir = caso_path(case_id) / "01_Procesado" / "MD"
```

- [ ] **Step 4: Run new test to verify it passes**

Run: `python -m pytest tests/test_catalogo_documental.py::test_markdown_build_escribe_en_md_subdir -v`
Expected: PASS

- [ ] **Step 5: Fix existing test path expectations in `test_extractor_skip.py`**

In `test_build_solo_regenera_lo_reextraido`, the test creates `raw_text/` and then checks that `.md` exists. The `.md` path comes from `paths[0]` which now goes to `MD/` — the test uses `paths[0]` directly, so it should still work. But check: the test accesses `md.stat().st_mtime_ns` on the returned path, which is correct regardless of directory.

Verify: `python -m pytest tests/test_extractor_skip.py -v`

If any path-hardcoded assertions break, adjust them to expect `MD/` subdirectory.

- [ ] **Step 6: Run full suite**

Run: `python -m pytest -q --tb=short --ignore=tests/test_sudespacho_relations.py`
Expected: all green

- [ ] **Step 7: Commit**

```bash
git add core/markdown_generator.py tests/test_catalogo_documental.py
git commit -m "feat(md-faucet): MD en claro a 01_Procesado/MD/ (Fase 3)"
```

---

### Task 4: Final verification + suite green

- [ ] **Step 1: Run full suite**

```
python -m pytest -q --tb=short --ignore=tests/test_sudespacho_relations.py
```

Expected: 836 + ~6 new = ~842 passed, 58 skipped

- [ ] **Step 2: Verify idempotency manually**

Confirm that `markdown_generator.build` with `skipped=True` still skips correctly with the new path, and that `ensure_case` creates the new dirs idempotently.

---

## Notes for PLAN.md update (at session close)

- Phase 0: already closed (s32). Verified.
- Phase 1: `core/catalogo_documental.py` with `parent_id`/`orden_en_bundle`. Catalog as independent artifact — **reconciliation with `_intake_hashes.json` deferred** per prompt.
- Phase 2: scaffolding `Sala lectura/` + `MD/` + `_revisar/` in `ensure_case`.
- Phase 3: MD faucet to `01_Procesado/MD/`.
