# Sala de lectura F4–F6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la sala de lectura de `01_Procesado` — clasificador/fechador híbrido (F6), copiador + bundles (F4) e índices (F5) — con el catálogo `indice_documental.yaml` como única fuente de verdad.

**Architecture:** Módulo nuevo `core/sala_lectura.py` centrado en el catálogo, que reutiliza helpers probados de `core/local_organizer.py` sin resucitar Ollama. El residuo ambiguo del clasificador se vuelca a una worklist markdown (`01_Procesado/_revisar/_clasificar.md`) que Claude rellena en sesión leyendo los `MD/` en claro. Disparo por CLI `scripts/sala_lectura.py` + botón Streamlit.

**Tech Stack:** Python 3.11, pytest, pyyaml, typer, python-docx (ya en deps). Windows + PowerShell. Spec: `docs/superpowers/specs/2026-06-17-sala-lectura-f4f6-design.md`.

---

## File Structure

- **Modify** `core/catalogo_documental.py` — extender `CatalogEntry` con campos F6/F4; `load_catalog` tolerante a claves desconocidas; `save_catalog(case_id, entries)`.
- **Create** `core/sala_lectura.py` — `clasificar_caso`, `aplicar_clasificacion`, `render_indices`, `poblar_sala_lectura` + helpers privados.
- **Create** `scripts/sala_lectura.py` — CLI typer (subcomandos `clasificar`/`aplicar`/`render`/`poblar`/`organizar`).
- **Modify** `streamlit_app.py` — botón "📚 Organizar sala de lectura" en el tab Casos.
- **Create** `tests/test_sala_lectura.py` — tests de todas las fases.

Convenciones del repo (respetar):
- Tests usan la fixture `tmp_casos_root` y recargan módulos con `importlib.reload` tras cambiar `CASOS_ROOT` (ver `tests/test_catalogo_documental.py`).
- UTF-8 sin BOM siempre. Helpers en `core/utils.py`: `file_sha256`, `text_sha256`, `slugify`, `now_iso`, `read_md`, `write_md`.
- Comando de test rápido: `python -m pytest -q --tb=short tests/test_sala_lectura.py`.
- Commits acotados a los ficheros de cada tarea (working tree compartido — nunca `git add -A`).

**Helper de recarga para todos los tests de este plan** (cópialo al principio de `tests/test_sala_lectura.py`):

```python
"""Tests de la sala de lectura (F4–F6)."""
from __future__ import annotations

import importlib
from pathlib import Path


def _reload():
    from core import case_manager, catalogo_documental, inventory, sala_lectura
    importlib.reload(case_manager)
    importlib.reload(inventory)
    importlib.reload(catalogo_documental)
    importlib.reload(sala_lectura)
    return case_manager, inventory, catalogo_documental, sala_lectura


def _caso_con_docs(case_manager, inventory, catalogo, docs):
    """Crea un caso con `docs` = [(subcarpeta, nombre, contenido_bytes_o_str)] y
    devuelve (case_id, case_dir) con inventario y catálogo ya construidos."""
    case_id = "EV-2026-TEST"
    case_dir = case_manager.ensure_case(case_id)
    for sub, name, content in docs:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
    inventory.scan(case_id)
    catalogo.build_catalog(case_id)
    return case_id, case_dir
```

---

## ETAPA 1 — Catálogo extendido + clasificador determinista + worklist

### Task 1: Extender `CatalogEntry` y hacer `load_catalog` tolerante

**Files:**
- Modify: `core/catalogo_documental.py`
- Test: `tests/test_sala_lectura.py`

- [ ] **Step 1: Write the failing test**

```python
def test_catalog_entry_campos_nuevos_por_defecto(tmp_casos_root):
    cm, inv, cat, _ = _reload()
    case_id, _ = _caso_con_docs(cm, inv, cat, [("01_Drive EV", "x.txt", "hola")])
    e = cat.load_catalog(case_id)[0]
    assert e.descripcion is None
    assert e.fecha_fuente is None
    assert e.confianza is None
    assert e.nombre_canonico is None
    assert e.ruta_sala_lectura is None


def test_load_catalog_tolera_claves_desconocidas(tmp_casos_root):
    cm, inv, cat, _ = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [("01_Drive EV", "x.txt", "hola")])
    # Simula un catálogo de una versión futura con un campo extra.
    import yaml
    path = case_dir / "01_Procesado" / "indice_documental.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data[0]["campo_de_otra_version"] = "ignorar"
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    entries = cat.load_catalog(case_id)  # no debe lanzar
    assert len(entries) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_catalog_entry_campos_nuevos_por_defecto tests/test_sala_lectura.py::test_load_catalog_tolera_claves_desconocidas`
Expected: FAIL (`TypeError: __init__() got an unexpected keyword argument` y/o atributos inexistentes).

- [ ] **Step 3: Extender el dataclass y la carga**

En `core/catalogo_documental.py`, añadir campos al `CatalogEntry` (tras `orden_en_bundle`):

```python
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
    # F6/F4 (sala de lectura)
    descripcion: str | None = None
    fecha_fuente: str | None = None          # contenido | crm_mtime | exif | mtime | desconocida
    confianza: float | None = None
    nombre_canonico: str | None = None
    ruta_sala_lectura: str | None = None
```

Reescribir `load_catalog` para filtrar claves desconocidas:

```python
import dataclasses


def _entry_fields() -> set[str]:
    return {f.name for f in dataclasses.fields(CatalogEntry)}


def load_catalog(case_id: str) -> list[CatalogEntry]:
    path = _catalog_path(case_id)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not data:
        return []
    known = _entry_fields()
    return [CatalogEntry(**{k: v for k, v in entry.items() if k in known}) for entry in data]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_catalog_entry_campos_nuevos_por_defecto tests/test_sala_lectura.py::test_load_catalog_tolera_claves_desconocidas`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/catalogo_documental.py tests/test_sala_lectura.py
git commit -m "feat(sala-lectura): extiende CatalogEntry (F6/F4) y load tolerante"
```

---

### Task 2: `save_catalog` (persistir entries mutadas)

**Files:**
- Modify: `core/catalogo_documental.py`
- Test: `tests/test_sala_lectura.py`

- [ ] **Step 1: Write the failing test**

```python
def test_save_catalog_roundtrip(tmp_casos_root):
    cm, inv, cat, _ = _reload()
    case_id, _ = _caso_con_docs(cm, inv, cat, [("01_Drive EV", "x.txt", "hola")])
    entries = cat.load_catalog(case_id)
    entries[0].tipo_documental = "05. FACTURACIÓN - FINANZAS"
    entries[0].confianza = 0.9
    cat.save_catalog(case_id, entries)
    reloaded = cat.load_catalog(case_id)
    assert reloaded[0].tipo_documental == "05. FACTURACIÓN - FINANZAS"
    assert reloaded[0].confianza == 0.9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_save_catalog_roundtrip`
Expected: FAIL (`AttributeError: module ... has no attribute 'save_catalog'`).

- [ ] **Step 3: Implementar `save_catalog`** (refactor: `build_catalog` reusa el writer)

En `core/catalogo_documental.py`:

```python
def save_catalog(case_id: str, entries: list[CatalogEntry]) -> Path:
    path = _catalog_path(case_id)
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

Y en `build_catalog`, sustituir el bloque final de escritura (`path.parent.mkdir(...)` + `path.write_text(...)` + `return path`) por:

```python
    return save_catalog(case_id, entries)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_save_catalog_roundtrip tests/test_catalogo_documental.py`
Expected: PASS (incluye los tests existentes del catálogo — no deben romperse).

- [ ] **Step 5: Commit**

```bash
git add core/catalogo_documental.py tests/test_sala_lectura.py
git commit -m "feat(sala-lectura): save_catalog para persistir entries enriquecidas"
```

---

### Task 3: Reglas deterministas — categoría por keyword e imagen

**Files:**
- Create: `core/sala_lectura.py`
- Test: `tests/test_sala_lectura.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest


@pytest.mark.parametrize("nombre, esperado", [
    ("Factura honorarios 2025.pdf", "05. FACTURACIÓN - FINANZAS"),
    ("Burofax requerimiento de pago.pdf", "07. RECLAMACIONES"),
    ("Hoja de encargo en exclusiva.pdf", "01. ACTIVACIÓN"),
    ("Oferta del comprador.pdf", "03. OFERTAS"),
    ("Contrato de arras penitenciales.pdf", "04. ARRAS - ARRENDAMIENTOS"),
    ("Nota simple registral.pdf", "06. PBC"),
    ("Documento sin pistas.pdf", None),
])
def test_clasificar_por_keyword(nombre, esperado):
    from core import sala_lectura
    importlib.reload(sala_lectura)
    assert sala_lectura._categoria_por_nombre(nombre) == esperado


def test_categoria_imagen():
    from core import sala_lectura
    importlib.reload(sala_lectura)
    assert sala_lectura._es_imagen(".jpg") is True
    assert sala_lectura._es_imagen(".pdf") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_sala_lectura.py -k "por_keyword or categoria_imagen"`
Expected: FAIL (`ModuleNotFoundError: No module named 'core.sala_lectura'`).

- [ ] **Step 3: Crear `core/sala_lectura.py` con las reglas**

```python
"""Sala de lectura de 01_Procesado (F4–F6).

Clasificador/fechador híbrido + copiador organizado + render de índices.
El catálogo `indice_documental.yaml` es la única fuente de verdad. El residuo
ambiguo del clasificador se vuelca a `01_Procesado/_revisar/_clasificar.md`
(worklist) que Claude rellena en sesión leyendo los `MD/` en claro.

Excepción RGPD temporal autorizada por Nikolai (spec
2026-06-17-sala-lectura-f4f6-design.md §2).
"""
from __future__ import annotations

import re
from pathlib import Path

from core.config import TAXONOMIA_EV, UMBRAL_CONFIANZA_AUTOMOVE, caso_path
from core.local_organizer import _exif_o_mtime, _sanitize

# Categoría → tokens del nombre de fichero (orden de prioridad de la tupla).
# Las primeras que casen ganan; el orden de TAXONOMIA fija desempates.
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("07. RECLAMACIONES", ("burofax", "requerimiento", "reclamacion", "reclamación", "ovc", "incumplimiento")),
    ("05. FACTURACIÓN - FINANZAS", ("factura", "honorarios", "abono", "minuta", "justificante de pago")),
    ("06. PBC", ("dni", "nie", "pasaporte", "nota simple", "titularidad", "pbc", "blanqueo")),
    ("04. ARRAS - ARRENDAMIENTOS", ("arras", "reserva", "señal", "arrendamiento", "alquiler")),
    ("03. OFERTAS", ("oferta", "contraoferta")),
    ("01. ACTIVACIÓN", ("encargo", "captacion", "captación", "exclusiva", "expose", "exposé", "hoja de visita")),
]

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".bmp", ".tiff", ".tif"}


def _es_imagen(ext: str) -> bool:
    return ext.lower() in _IMG_EXTS


def _categoria_por_nombre(nombre: str) -> str | None:
    low = nombre.lower()
    for categoria, tokens in _KEYWORDS:
        if any(t in low for t in tokens):
            return categoria
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_sala_lectura.py -k "por_keyword or categoria_imagen"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/sala_lectura.py tests/test_sala_lectura.py
git commit -m "feat(sala-lectura): reglas deterministas de categoria por nombre/imagen"
```

---

### Task 4: Fecha determinista (patrón en nombre → mtime)

**Files:**
- Modify: `core/sala_lectura.py`
- Test: `tests/test_sala_lectura.py`

- [ ] **Step 1: Write the failing test**

```python
def test_fecha_desde_nombre_iso():
    from core import sala_lectura
    importlib.reload(sala_lectura)
    assert sala_lectura._fecha_desde_nombre("2025-07-12 oferta.pdf") == ("2025-07-12", "contenido")
    assert sala_lectura._fecha_desde_nombre("oferta 12-07-2025.pdf") == ("2025-07-12", "contenido")
    assert sala_lectura._fecha_desde_nombre("sin fecha.pdf") == (None, None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_fecha_desde_nombre_iso`
Expected: FAIL (`AttributeError: ... '_fecha_desde_nombre'`).

- [ ] **Step 3: Implementar `_fecha_desde_nombre`**

Añadir a `core/sala_lectura.py`:

```python
_FECHA_ISO_RE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_FECHA_DMY_RE = re.compile(r"(?<!\d)(\d{2})[-/.](\d{2})[-/.](\d{4})(?!\d)")


def _fecha_desde_nombre(nombre: str) -> tuple[str | None, str | None]:
    m = _FECHA_ISO_RE.search(nombre)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "contenido"
    m = _FECHA_DMY_RE.search(nombre)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}", "contenido"
    return None, None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_fecha_desde_nombre_iso`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/sala_lectura.py tests/test_sala_lectura.py
git commit -m "feat(sala-lectura): deteccion de fecha por patron en el nombre"
```

---

### Task 5: `clasificar_caso` — enriquece catálogo + escribe worklist del residuo

**Files:**
- Modify: `core/sala_lectura.py`
- Test: `tests/test_sala_lectura.py`

- [ ] **Step 1: Write the failing test**

```python
def test_clasificar_caso_deterministas_y_residuo(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1"),
        ("01_Drive EV", "Documento ambiguo.pdf", b"%PDF-2"),
        ("01_Drive EV", "foto fachada.jpg", b"\xff\xd8\xff\xe0jpg"),
    ])
    resumen = sl.clasificar_caso(case_id)

    entries = {e.nombre_original: e for e in cat.load_catalog(case_id)}
    assert entries["Factura honorarios.pdf"].tipo_documental == "05. FACTURACIÓN - FINANZAS"
    assert entries["foto fachada.jpg"].tipo_documental == "00. FOTOS"
    # El ambiguo NO se clasifica con confianza → queda en residuo.
    assert entries["Documento ambiguo.pdf"].tipo_documental is None

    worklist = case_dir / "01_Procesado" / "_revisar" / "_clasificar.md"
    assert worklist.exists()
    contenido = worklist.read_text(encoding="utf-8")
    assert "Documento ambiguo.pdf" in contenido
    assert "Factura honorarios.pdf" not in contenido  # ya resuelto, no entra al worklist
    assert resumen["n_residuo"] == 1
    assert resumen["n_deterministas"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_clasificar_caso_deterministas_y_residuo`
Expected: FAIL (`AttributeError: ... 'clasificar_caso'`).

- [ ] **Step 3: Implementar `clasificar_caso` + worklist + constantes**

Añadir a `core/sala_lectura.py`:

```python
from core import catalogo_documental

CATEGORIA_FOTOS = "00. FOTOS"
WORKLIST_NAME = "_clasificar.md"
_CONF_DETERMINISTA = 0.9
_CONF_IMAGEN = 1.0

_WL_COLS = ["Hash", "Origen", "Fuente", "Tipo", "Fecha", "Parte", "Descripcion"]


def _revisar_dir(case_id: str) -> Path:
    return caso_path(case_id) / "01_Procesado" / "_revisar"


def _input_path(case_id: str, ruta_relativa: str) -> Path:
    return caso_path(case_id) / "00_Input" / ruta_relativa


def _fecha_de(case_id, entry) -> tuple[str | None, str]:
    fecha, fuente = _fecha_desde_nombre(entry.nombre_original)
    if fecha:
        return fecha, fuente
    src = _input_path(case_id, entry.ruta_relativa)
    if _es_imagen(Path(entry.nombre_original).suffix) and src.exists():
        f, fnt = _exif_o_mtime(src)
        return f, ("exif" if fnt == "exif" else "mtime")
    if src.exists():
        from datetime import datetime
        return datetime.fromtimestamp(src.stat().st_mtime).date().isoformat(), "mtime"
    return None, "desconocida"


def _celda(s) -> str:
    return str(s if s is not None else "").replace("|", "/").replace("\n", " ").strip()


def _write_worklist(case_id: str, residuo: list) -> Path:
    out = _revisar_dir(case_id)
    out.mkdir(parents=True, exist_ok=True)
    path = out / WORKLIST_NAME
    lineas = [
        f"# Worklist de clasificación — {case_id}",
        "",
        "> Rellena **Tipo**, **Fecha** (YYYY-MM-DD), **Parte** "
        "(propietario/buscador/tercero) y **Descripcion** (≤60 car., sin PII) "
        "leyendo `01_Procesado/MD/<slug>.md`. No toques la columna **Hash**.",
        "> Tipos válidos: " + " · ".join(TAXONOMIA_EV),
        "",
        "| " + " | ".join(_WL_COLS) + " |",
        "|" + "|".join(["---"] * len(_WL_COLS)) + "|",
    ]
    for e in residuo:
        fecha, _ = _fecha_de(case_id, e)
        fila = [e.hash, _celda(e.nombre_original), _celda(e.fuente),
                "", fecha or "", "", ""]
        lineas.append("| " + " | ".join(fila) + " |")
    lineas.append("")
    path.write_text("\n".join(lineas), encoding="utf-8")
    return path


def clasificar_caso(case_id: str) -> dict:
    entries = catalogo_documental.load_catalog(case_id)
    residuo = []
    n_det = 0
    for e in entries:
        if e.tipo_documental and (e.confianza or 0) >= UMBRAL_CONFIANZA_AUTOMOVE:
            continue  # ya resuelto en una corrida previa
        ext = Path(e.nombre_original).suffix
        if _es_imagen(ext):
            fecha, fuente = _fecha_de(case_id, e)
            e.tipo_documental = CATEGORIA_FOTOS
            e.fecha_doc, e.fecha_fuente = fecha, fuente
            e.confianza = _CONF_IMAGEN
            e.descripcion = e.descripcion or "Fotografía"
            n_det += 1
            continue
        categoria = _categoria_por_nombre(e.nombre_original)
        if categoria:
            fecha, fuente = _fecha_de(case_id, e)
            e.tipo_documental = categoria
            e.fecha_doc, e.fecha_fuente = fecha, fuente
            e.confianza = _CONF_DETERMINISTA
            n_det += 1
            continue
        residuo.append(e)

    catalogo_documental.save_catalog(case_id, entries)
    _write_worklist(case_id, residuo)
    return {"case_id": case_id, "n_total": len(entries),
            "n_deterministas": n_det, "n_residuo": len(residuo)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_clasificar_caso_deterministas_y_residuo`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/sala_lectura.py tests/test_sala_lectura.py
git commit -m "feat(sala-lectura): clasificar_caso (reglas + worklist del residuo)"
```

---

### Task 6: `aplicar_clasificacion` — vuelca la worklist rellena al catálogo

**Files:**
- Modify: `core/sala_lectura.py`
- Test: `tests/test_sala_lectura.py`

- [ ] **Step 1: Write the failing test**

```python
def test_aplicar_clasificacion_vuelca_worklist(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Documento ambiguo.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    h = cat.load_catalog(case_id)[0].hash

    # Claude/humano rellena la worklist.
    worklist = case_dir / "01_Procesado" / "_revisar" / "_clasificar.md"
    filas = [
        "# Worklist", "",
        "| Hash | Origen | Fuente | Tipo | Fecha | Parte | Descripcion |",
        "|---|---|---|---|---|---|---|",
        f"| {h} | Documento ambiguo.pdf | drive_ev | 01. ACTIVACIÓN | 2025-03-01 | propietario | Acuerdo marco |",
        "",
    ]
    worklist.write_text("\n".join(filas), encoding="utf-8")

    res = sl.aplicar_clasificacion(case_id)
    e = cat.load_catalog(case_id)[0]
    assert e.tipo_documental == "01. ACTIVACIÓN"
    assert e.fecha_doc == "2025-03-01"
    assert e.parte == "propietario"
    assert e.descripcion == "Acuerdo marco"
    assert e.confianza == 1.0
    assert res["n_aplicadas"] == 1


def test_aplicar_ignora_filas_sin_tipo_o_tipo_invalido(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    h = cat.load_catalog(case_id)[0].hash
    worklist = case_dir / "01_Procesado" / "_revisar" / "_clasificar.md"
    filas = [
        "| Hash | Origen | Fuente | Tipo | Fecha | Parte | Descripcion |",
        "|---|---|---|---|---|---|---|",
        f"| {h} | ambiguo.pdf | drive_ev | TIPO INVENTADO | 2025-03-01 |  |  |",
    ]
    worklist.write_text("\n".join(filas), encoding="utf-8")
    res = sl.aplicar_clasificacion(case_id)
    assert cat.load_catalog(case_id)[0].tipo_documental is None
    assert res["n_aplicadas"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_sala_lectura.py -k aplicar`
Expected: FAIL (`AttributeError: ... 'aplicar_clasificacion'`).

- [ ] **Step 3: Implementar el parseo y el volcado**

Añadir a `core/sala_lectura.py`:

```python
def _parse_worklist(text: str) -> list[dict]:
    filas = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        celdas = [c.strip() for c in line.strip("|").split("|")]
        if len(celdas) != len(_WL_COLS):
            continue
        if celdas[0] == "Hash" or set(celdas[0]) <= {"-"}:
            continue
        filas.append(dict(zip(_WL_COLS, celdas)))
    return filas


def aplicar_clasificacion(case_id: str) -> dict:
    path = _revisar_dir(case_id) / WORKLIST_NAME
    if not path.exists():
        return {"case_id": case_id, "n_aplicadas": 0}
    filas = {f["Hash"]: f for f in _parse_worklist(path.read_text(encoding="utf-8"))}
    entries = catalogo_documental.load_catalog(case_id)
    aplicadas = 0
    for e in entries:
        fila = filas.get(e.hash)
        if not fila:
            continue
        tipo = fila["Tipo"].strip()
        if tipo not in TAXONOMIA_EV:
            continue  # sin tipo válido → sigue pendiente
        e.tipo_documental = tipo
        e.fecha_doc = fila["Fecha"].strip() or e.fecha_doc
        e.fecha_fuente = e.fecha_fuente or "contenido"
        e.parte = fila["Parte"].strip() or None
        e.descripcion = fila["Descripcion"].strip() or None
        e.confianza = 1.0
        aplicadas += 1
    catalogo_documental.save_catalog(case_id, entries)
    return {"case_id": case_id, "n_aplicadas": aplicadas}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_sala_lectura.py -k aplicar`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/sala_lectura.py tests/test_sala_lectura.py
git commit -m "feat(sala-lectura): aplicar_clasificacion vuelca la worklist al catalogo"
```

---

## ETAPA 2 — Render de índices (F5)

### Task 7: `render_indices` — INDICE.md (por fuente→tipo) + CRONOLOGIA.md (por fecha)

**Files:**
- Modify: `core/sala_lectura.py`
- Test: `tests/test_sala_lectura.py`

- [ ] **Step 1: Write the failing test**

```python
def test_render_indices(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura.pdf", b"%PDF-1"),
        ("05_CRM/01_Demanda", "Burofax.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)  # ambas casan por keyword
    paths = sl.render_indices(case_id)

    indice = case_dir / "01_Procesado" / "Sala lectura" / "INDICE.md"
    crono = case_dir / "01_Procesado" / "Sala lectura" / "CRONOLOGIA.md"
    assert indice in paths and crono in paths
    txt_i = indice.read_text(encoding="utf-8")
    assert "no editar a mano" in txt_i.lower()
    assert "drive_ev" in txt_i.lower() or "drive e&v" in txt_i.lower()
    assert "Factura.pdf" in txt_i
    txt_c = crono.read_text(encoding="utf-8")
    assert "Burofax.pdf" in txt_c
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_render_indices`
Expected: FAIL (`AttributeError: ... 'render_indices'`).

- [ ] **Step 3: Implementar el render**

Añadir a `core/sala_lectura.py`:

```python
from core.utils import now_iso, slugify

_SALA = "Sala lectura"
FUENTE_LABEL = {
    "drive_ev": "Drive E&V", "crm": "CRM", "whatsapp": "WhatsApp",
    "entrevistas": "Entrevistas", "email": "Email", "manual": "Manual",
}
_CABECERA_RO = "<!-- GENERADO AUTOMÁTICAMENTE — NO EDITAR A MANO. " \
               "Se regenera desde indice_documental.yaml. -->"


def _sala_dir(case_id: str) -> Path:
    return caso_path(case_id) / "01_Procesado" / _SALA


def _link_original(e) -> str:
    # Enlace relativo desde Sala lectura/ al original en 00_Input/.
    return f"../../00_Input/{e.ruta_relativa}"


def _link_md(e) -> str | None:
    if Path(e.nombre_original).suffix.lower() == ".md":
        return None
    return f"../MD/{slugify(Path(e.ruta_relativa).stem)}.md"


def render_indices(case_id: str) -> list[Path]:
    entries = catalogo_documental.load_catalog(case_id)
    out = _sala_dir(case_id)
    out.mkdir(parents=True, exist_ok=True)

    # --- INDICE.md: por fuente → tipo ---
    por_fuente: dict[str, list] = {}
    for e in entries:
        por_fuente.setdefault(e.fuente, []).append(e)
    li = [_CABECERA_RO, "", f"# Índice del expediente — {case_id}", "",
          f"Generado: {now_iso()}.", ""]
    for fuente in sorted(por_fuente):
        li.append(f"## {FUENTE_LABEL.get(fuente, fuente)}")
        li.append("")
        por_tipo: dict[str, list] = {}
        for e in por_fuente[fuente]:
            por_tipo.setdefault(e.tipo_documental or "Sin clasificar", []).append(e)
        for tipo in sorted(por_tipo):
            li.append(f"### {tipo}")
            for e in sorted(por_tipo[tipo], key=lambda x: (x.fecha_doc or "", x.nombre_original)):
                md = _link_md(e)
                ver_texto = f" · [ver texto]({md})" if md else ""
                fecha = e.fecha_doc or "s/f"
                li.append(f"- {fecha} — [{e.nombre_original}]({_link_original(e)}){ver_texto}")
            li.append("")
    indice = out / "INDICE.md"
    indice.write_text("\n".join(li), encoding="utf-8")

    # --- CRONOLOGIA.md: por fecha ascendente, sin fecha al final ---
    lc = [_CABECERA_RO, "", f"# Cronología — {case_id}", "",
          f"Generado: {now_iso()}.", "",
          "| Fecha | Fuente | Tipo | Documento |", "|---|---|---|---|"]
    def _key(e):
        return (e.fecha_doc is None, e.fecha_doc or "", e.nombre_original)
    for e in sorted(entries, key=_key):
        lc.append(f"| {e.fecha_doc or 's/f'} | {FUENTE_LABEL.get(e.fuente, e.fuente)} "
                  f"| {e.tipo_documental or 'Sin clasificar'} "
                  f"| [{e.nombre_original}]({_link_original(e)}) |")
    lc.append("")
    crono = out / "CRONOLOGIA.md"
    crono.write_text("\n".join(lc), encoding="utf-8")
    return [indice, crono]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_render_indices`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/sala_lectura.py tests/test_sala_lectura.py
git commit -m "feat(sala-lectura): render INDICE.md y CRONOLOGIA.md desde el catalogo"
```

---

## ETAPA 3 — Copiador plano idempotente (F4 sin bundles)

### Task 8: `_nombre_canonico` — `<AAAA-MM-DD>_<tipo>_<descripción>.<ext>`

**Files:**
- Modify: `core/sala_lectura.py`
- Test: `tests/test_sala_lectura.py`

- [ ] **Step 1: Write the failing test**

```python
def test_nombre_canonico():
    from core import sala_lectura as sl
    importlib.reload(sl)
    from core.catalogo_documental import CatalogEntry
    e = CatalogEntry(
        id_doc="abc", ruta_relativa="01_Drive EV/x.pdf", nombre_original="x.pdf",
        tipo_documental="01. ACTIVACIÓN", fecha_doc="2025-07-12",
        descripcion="Hoja de captación firmada", hash="abc123",
    )
    assert sl._nombre_canonico(e) == "2025-07-12_activacion_hoja-de-captacion-firmada.pdf"

    e2 = CatalogEntry(id_doc="d", ruta_relativa="a/y.pdf", nombre_original="y.pdf", hash="d")
    # Sin tipo/fecha/desc → cae a fallback con fecha desconocida y stem original.
    assert sl._nombre_canonico(e2).endswith("_y.pdf")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_nombre_canonico`
Expected: FAIL (`AttributeError: ... '_nombre_canonico'`).

- [ ] **Step 3: Implementar `_nombre_canonico` + mapa de slugs de tipo**

Añadir a `core/sala_lectura.py`:

```python
_TIPO_SLUG = {
    "00. FOTOS": "foto",
    "01. ACTIVACIÓN": "activacion",
    "03. OFERTAS": "oferta",
    "04. ARRAS - ARRENDAMIENTOS": "arras",
    "05. FACTURACIÓN - FINANZAS": "factura",
    "06. PBC": "pbc",
    "07. RECLAMACIONES": "reclamacion",
    "08. PENDIENTE DE CLASIFICAR": "pendiente",
}


def _nombre_canonico(entry) -> str:
    ext = Path(entry.nombre_original).suffix.lower()
    fecha = entry.fecha_doc or "0000-00-00"
    tipo = _TIPO_SLUG.get(entry.tipo_documental or "", "doc")
    desc_src = entry.descripcion or Path(entry.nombre_original).stem
    desc = slugify(_sanitize(desc_src), max_length=50)
    return f"{fecha}_{tipo}_{desc}{ext}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_sala_lectura.py::test_nombre_canonico`
Expected: PASS

> Nota: si `slugify` no separa con guiones igual que el assert, ajusta el assert
> al output real de `slugify` (revisa `core/utils.py::slugify`). El contrato es:
> minúsculas, sin acentos, separado por `-`. Verifica el formato exacto y fija el
> test a ese formato; no cambies `slugify`.

- [ ] **Step 5: Commit**

```bash
git add core/sala_lectura.py tests/test_sala_lectura.py
git commit -m "feat(sala-lectura): nombre canonico fecha_tipo_descripcion"
```

---

### Task 9: `poblar_sala_lectura` (plano) — copia idempotente + dedup + renombrado

**Files:**
- Modify: `core/sala_lectura.py`
- Test: `tests/test_sala_lectura.py`

- [ ] **Step 1: Write the failing test**

```python
def test_poblar_sala_lectura_copia_idempotente(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-FACTURA"),
    ])
    sl.clasificar_caso(case_id)
    r1 = sl.poblar_sala_lectura(case_id)

    sala = case_dir / "01_Procesado" / "Sala lectura" / "Drive E&V"
    copias = list(sala.glob("*.pdf"))
    assert len(copias) == 1
    assert copias[0].read_bytes() == b"%PDF-FACTURA"
    # 00_Input intacto
    assert (case_dir / "00_Input" / "01_Drive EV" / "Factura honorarios.pdf").exists()
    # ruta_sala_lectura persistida en el catálogo
    assert cat.load_catalog(case_id)[0].ruta_sala_lectura is not None

    # 2ª corrida: idempotente (SKIP, sin duplicar)
    r2 = sl.poblar_sala_lectura(case_id)
    assert len(list(sala.glob("*.pdf"))) == 1
    assert r2["acciones"].get("SKIP_UNCHANGED", 0) >= 1


def test_poblar_dedup_por_hash(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    # Mismo contenido en dos fuentes → mismo hash → una sola copia.
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura.pdf", b"%PDF-IGUAL"),
        ("05_CRM/01_Demanda", "Factura copia.pdf", b"%PDF-IGUAL"),
    ])
    sl.clasificar_caso(case_id)
    sl.poblar_sala_lectura(case_id)
    todas = list((case_dir / "01_Procesado" / "Sala lectura").rglob("*.pdf"))
    assert len(todas) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_sala_lectura.py -k poblar`
Expected: FAIL (`AttributeError: ... 'poblar_sala_lectura'`).

- [ ] **Step 3: Implementar `poblar_sala_lectura` (plano)**

Añadir a `core/sala_lectura.py`:

```python
import shutil


def poblar_sala_lectura(case_id: str) -> dict:
    entries = catalogo_documental.load_catalog(case_id)
    base = _sala_dir(case_id)
    acciones: dict[str, int] = {}
    vistos_hash: set[str] = set()

    for e in entries:
        if e.hash and e.hash in vistos_hash:
            acciones["SKIP_DEDUP"] = acciones.get("SKIP_DEDUP", 0) + 1
            continue
        src = _input_path(case_id, e.ruta_relativa)
        if not src.exists():
            acciones["MISSING_SRC"] = acciones.get("MISSING_SRC", 0) + 1
            continue
        fuente_dir = FUENTE_LABEL.get(e.fuente, e.fuente)
        dst_rel = f"{_SALA}/{fuente_dir}/{_nombre_canonico(e)}"
        dst = caso_path(case_id) / "01_Procesado" / dst_rel

        prev = e.ruta_sala_lectura
        if prev == dst_rel and dst.exists():
            acciones["SKIP_UNCHANGED"] = acciones.get("SKIP_UNCHANGED", 0) + 1
        else:
            if prev and prev != dst_rel:
                old = caso_path(case_id) / "01_Procesado" / prev
                if old.exists():
                    old.unlink()
                acciones["MOVED"] = acciones.get("MOVED", 0) + 1
            else:
                acciones["COPY"] = acciones.get("COPY", 0) + 1
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            e.ruta_sala_lectura = dst_rel
        if e.hash:
            vistos_hash.add(e.hash)

    catalogo_documental.save_catalog(case_id, entries)
    return {"case_id": case_id, "acciones": acciones}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_sala_lectura.py -k poblar`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/sala_lectura.py tests/test_sala_lectura.py
git commit -m "feat(sala-lectura): poblar_sala_lectura plano (copia idempotente + dedup)"
```

---

## ETAPA 4 — Bundles (F4) con degradación

### Task 10: bundles CRM (cabecera + `adjuntos/`) con degradación a copia plana

**Files:**
- Modify: `core/sala_lectura.py`
- Test: `tests/test_sala_lectura.py`

**Contexto:** `core/conjunto_detector.detect_bundles(docs)` toma `list[GdocuDocInfo]`
y devuelve `list[BundleProposal]` (atributos `header_doc_id`, `member_doc_ids`,
`evidence_doc_ids`, `confidence`). Los `doc_id` del CRM **no** son el hash del
catálogo. La unión catálogo↔CRM se hace por **nombre de fichero** (`filename` ==
`nombre_original`). El parámetro `crm_docs` es opcional: si no se pasa, no hay
bundles (degradación a copia plana, ya implementada en Task 9).

- [ ] **Step 1: Write the failing test**

```python
def test_poblar_con_bundles_crm(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    from core.sync_sudespacho import GdocuDocInfo
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("05_CRM/01_Demanda", "ORDINARIO VUELTA VENDEDOR.pdf", b"%PDF-CAB"),
        ("05_CRM/01_Demanda", "D 01 - encargo.pdf", b"%PDF-D1"),
        ("05_CRM/01_Demanda", "D 02 - oferta.pdf", b"%PDF-D2"),
    ])
    sl.clasificar_caso(case_id)
    ts = "2025-01-01T10:00:00+01:00"
    crm_docs = [
        GdocuDocInfo("1", "ORDINARIO VUELTA VENDEDOR.pdf", "307", "Demanda",
                     "application/pdf", 1, {}, ts),
        GdocuDocInfo("2", "D 01 - encargo.pdf", "307", "Demanda",
                     "application/pdf", 1, {}, ts),
        GdocuDocInfo("3", "D 02 - oferta.pdf", "307", "Demanda",
                     "application/pdf", 1, {}, ts),
    ]
    sl.poblar_sala_lectura(case_id, crm_docs=crm_docs)

    crm_dir = case_dir / "01_Procesado" / "Sala lectura" / "CRM"
    bundles = [p for p in crm_dir.iterdir() if p.is_dir()]
    assert len(bundles) == 1
    adjuntos = bundles[0] / "adjuntos"
    assert adjuntos.is_dir()
    assert len(list(adjuntos.glob("*.pdf"))) == 2  # las 2 pruebas D NN
    # parent_id persistido en el catálogo
    entries = {e.nombre_original: e for e in cat.load_catalog(case_id)}
    assert entries["D 01 - encargo.pdf"].parent_id is not None


def test_poblar_sin_crm_docs_degrada_a_plano(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("05_CRM/01_Demanda", "D 01 - encargo.pdf", b"%PDF-D1"),
    ])
    sl.clasificar_caso(case_id)
    sl.poblar_sala_lectura(case_id)  # sin crm_docs
    crm_dir = case_dir / "01_Procesado" / "Sala lectura" / "CRM"
    assert any(crm_dir.glob("*.pdf"))  # copia plana, sin subcarpeta de bundle
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_sala_lectura.py -k bundles`
Expected: FAIL (`poblar_sala_lectura() got an unexpected keyword argument 'crm_docs'`).

- [ ] **Step 3: Añadir bundles a `poblar_sala_lectura`**

Refactorizar la firma y añadir el cálculo de bundles **antes** del bucle de copia.
Reemplazar la definición de `poblar_sala_lectura` por:

```python
def _bundle_map(case_id: str, entries: list, crm_docs) -> dict:
    """Devuelve {hash: (bundle_slug, rol)} para los miembros de bundles CRM de
    alta confianza. rol ∈ {'cabecera', 'adjunto'}. Une CRM↔catálogo por filename.
    """
    if not crm_docs:
        return {}
    from core.conjunto_detector import detect_bundles
    by_filename = {e.nombre_original: e for e in entries}
    id_to_filename = {d.doc_id: d.filename for d in crm_docs}
    out: dict = {}
    for prop in detect_bundles(crm_docs):
        if prop.confidence != "alta":
            continue
        header_id = prop.header_doc_id
        header_e = by_filename.get(id_to_filename.get(header_id, "")) if header_id else None
        slug_src = header_e.nombre_original if header_e else f"bundle-{prop.timestamp}"
        bundle_slug = slugify(_sanitize(Path(slug_src).stem), max_length=50)
        for doc_id in prop.member_doc_ids:
            e = by_filename.get(id_to_filename.get(doc_id, ""))
            if not e:
                continue
            rol = "cabecera" if doc_id == header_id else "adjunto"
            out[e.hash] = (bundle_slug, rol, header_e.hash if header_e else None)
    return out


def poblar_sala_lectura(case_id: str, *, crm_docs=None) -> dict:
    entries = catalogo_documental.load_catalog(case_id)
    bundles = _bundle_map(case_id, entries, crm_docs)
    acciones: dict[str, int] = {}
    vistos_hash: set[str] = set()
    orden_bundle: dict[str, int] = {}

    for e in entries:
        if e.hash and e.hash in vistos_hash:
            acciones["SKIP_DEDUP"] = acciones.get("SKIP_DEDUP", 0) + 1
            continue
        src = _input_path(case_id, e.ruta_relativa)
        if not src.exists():
            acciones["MISSING_SRC"] = acciones.get("MISSING_SRC", 0) + 1
            continue
        fuente_dir = FUENTE_LABEL.get(e.fuente, e.fuente)
        nombre = _nombre_canonico(e)

        b = bundles.get(e.hash)
        if b:
            bundle_slug, rol, header_hash = b
            if rol == "cabecera":
                dst_rel = f"{_SALA}/{fuente_dir}/{bundle_slug}/{nombre}"
                e.parent_id = None
            else:
                dst_rel = f"{_SALA}/{fuente_dir}/{bundle_slug}/adjuntos/{nombre}"
                e.parent_id = header_hash
                orden_bundle[bundle_slug] = orden_bundle.get(bundle_slug, 0) + 1
                e.orden_en_bundle = orden_bundle[bundle_slug]
        else:
            dst_rel = f"{_SALA}/{fuente_dir}/{nombre}"

        dst = caso_path(case_id) / "01_Procesado" / dst_rel
        prev = e.ruta_sala_lectura
        if prev == dst_rel and dst.exists():
            acciones["SKIP_UNCHANGED"] = acciones.get("SKIP_UNCHANGED", 0) + 1
        else:
            if prev and prev != dst_rel:
                old = caso_path(case_id) / "01_Procesado" / prev
                if old.exists():
                    old.unlink()
                acciones["MOVED"] = acciones.get("MOVED", 0) + 1
            else:
                acciones["COPY"] = acciones.get("COPY", 0) + 1
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            e.ruta_sala_lectura = dst_rel
        if e.hash:
            vistos_hash.add(e.hash)

    catalogo_documental.save_catalog(case_id, entries)
    return {"case_id": case_id, "acciones": acciones, "n_bundles": len({v[0] for v in bundles.values()})}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_sala_lectura.py -k "bundles or poblar"`
Expected: PASS (los tests planos de Task 9 siguen verdes — sin `crm_docs`).

- [ ] **Step 5: Commit**

```bash
git add core/sala_lectura.py tests/test_sala_lectura.py
git commit -m "feat(sala-lectura): bundles CRM (cabecera+adjuntos) con degradacion a plano"
```

---

## ETAPA 5 — Disparo (CLI + Streamlit)

### Task 11: CLI `scripts/sala_lectura.py`

**Files:**
- Create: `scripts/sala_lectura.py`
- Test: `tests/test_sala_lectura.py`

**Contexto:** los scripts del repo usan `typer`. Revisa `scripts/detectar_conjuntos.py`
o `scripts/sync_sudespacho.py` para el patrón exacto (app `typer.Typer()`,
`if __name__ == "__main__"`). El orquestador `organizar` encadena
`clasificar → render → poblar` y **se detiene tras `clasificar` si hay residuo**.

- [ ] **Step 1: Write the failing test**

```python
def test_cli_organizar_se_detiene_con_residuo(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-2"),
    ])
    from core import sala_lectura
    importlib.reload(sala_lectura)
    res = sala_lectura.organizar(case_id)
    assert res["detenido_por_residuo"] is True
    assert res["n_residuo"] == 1
    # No debe haber poblado (se detuvo).
    assert not (case_dir / "01_Procesado" / "Sala lectura" / "Drive E&V").exists()


def test_organizar_completo_sin_residuo(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1"),
    ])
    from core import sala_lectura
    importlib.reload(sala_lectura)
    res = sala_lectura.organizar(case_id)
    assert res["detenido_por_residuo"] is False
    assert (case_dir / "01_Procesado" / "Sala lectura" / "INDICE.md").exists()
    assert any((case_dir / "01_Procesado" / "Sala lectura" / "Drive E&V").glob("*.pdf"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_sala_lectura.py -k organizar`
Expected: FAIL (`AttributeError: ... 'organizar'`).

- [ ] **Step 3: Implementar `organizar` (core) + CLI**

Añadir a `core/sala_lectura.py`:

```python
def organizar(case_id: str, *, crm_docs=None) -> dict:
    """Orquestador: clasificar → (si hay residuo, parar) → render → poblar."""
    clasif = clasificar_caso(case_id)
    if clasif["n_residuo"] > 0:
        return {"case_id": case_id, "detenido_por_residuo": True,
                "n_residuo": clasif["n_residuo"],
                "worklist": str(_revisar_dir(case_id) / WORKLIST_NAME)}
    render_indices(case_id)
    pob = poblar_sala_lectura(case_id, crm_docs=crm_docs)
    return {"case_id": case_id, "detenido_por_residuo": False,
            "n_residuo": 0, "acciones": pob["acciones"]}
```

Crear `scripts/sala_lectura.py`:

```python
"""CLI de la sala de lectura (F4–F6). Disparo: clasificar/aplicar/render/poblar/organizar."""
from __future__ import annotations

import typer

from core import sala_lectura

app = typer.Typer(help="Organiza la sala de lectura de 01_Procesado.")


@app.command()
def clasificar(case: str = typer.Option(..., "--case")):
    r = sala_lectura.clasificar_caso(case)
    typer.echo(f"Deterministas: {r['n_deterministas']} · Residuo: {r['n_residuo']}")
    if r["n_residuo"]:
        typer.echo(f"Rellena la worklist y corre 'aplicar': "
                   f"01_Procesado/_revisar/{sala_lectura.WORKLIST_NAME}")


@app.command()
def aplicar(case: str = typer.Option(..., "--case")):
    r = sala_lectura.aplicar_clasificacion(case)
    typer.echo(f"Aplicadas: {r['n_aplicadas']}")


@app.command()
def render(case: str = typer.Option(..., "--case")):
    paths = sala_lectura.render_indices(case)
    typer.echo("Generado: " + ", ".join(p.name for p in paths))


@app.command()
def poblar(case: str = typer.Option(..., "--case")):
    r = sala_lectura.poblar_sala_lectura(case)
    typer.echo(f"Acciones: {r['acciones']}")


@app.command()
def organizar(case: str = typer.Option(..., "--case")):
    r = sala_lectura.organizar(case)
    if r["detenido_por_residuo"]:
        typer.echo(f"⏸  Detenido: {r['n_residuo']} doc(s) en revisión. "
                   f"Rellena la worklist y vuelve a correr 'organizar'.")
    else:
        typer.echo(f"✓ Sala de lectura organizada. Acciones: {r['acciones']}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_sala_lectura.py -k organizar`
Expected: PASS

Smoke CLI (manual, opcional): `python -m scripts.sala_lectura --help`

- [ ] **Step 5: Commit**

```bash
git add core/sala_lectura.py scripts/sala_lectura.py tests/test_sala_lectura.py
git commit -m "feat(sala-lectura): orquestador organizar + CLI typer"
```

---

### Task 12: Botón Streamlit "📚 Organizar sala de lectura"

**Files:**
- Modify: `streamlit_app.py`

**Contexto:** localiza el tab Casos y el patrón de botones existentes (p. ej. el
botón "⚖️ Intake judicial automático" o el expander "📂 Subir al árbol CRM").
Reusa el mismo estilo de `st.button` + `st.session_state` + mensajes. **No** hay
test automático de Streamlit en el repo; se valida con smoke manual.

- [ ] **Step 1: Añadir el botón junto a los demás del caso seleccionado**

```python
        if st.button("📚 Organizar sala de lectura", key=f"sala_{case_id}"):
            from core import sala_lectura
            with st.spinner("Clasificando y organizando…"):
                res = sala_lectura.organizar(case_id)
            if res["detenido_por_residuo"]:
                st.warning(
                    f"⏸ Quedan {res['n_residuo']} documento(s) sin clasificar en "
                    f"`01_Procesado/_revisar/_clasificar.md`. Pídele a Claude que "
                    f"los resuelva en una sesión y vuelve a pulsar el botón."
                )
            else:
                st.success(f"✓ Sala de lectura organizada: {res['acciones']}")
```

- [ ] **Step 2: Smoke manual**

Run: `python -m streamlit run streamlit_app.py`
Verifica: en el tab Casos, con un caso que tenga documentos en `00_Input`, el
botón aparece, lanza la organización y muestra el aviso/éxito correcto.

- [ ] **Step 3: Commit**

```bash
git add streamlit_app.py
git commit -m "feat(sala-lectura): boton Streamlit Organizar sala de lectura"
```

---

## Cierre

- [ ] **Suite completa verde**

Run: `python -m pytest -q --tb=short`
Expected: todos los tests previos verdes + los nuevos de `test_sala_lectura.py`.
Los 5 fallos preexistentes de `test_sudespacho_relations.py` (ajenos, import
circular) se ignoran si ya estaban rojos antes de empezar — confírmalo con
`git stash` + corrida limpia si hay duda.

- [ ] **Actualizar `PLAN.md`** — marcar `[x]` las fases (4) copiador+bundles,
  (5) render de índices y (6) clasificador híbrido en
  `[SIGUIENTE-SALA-LECTURA-01]`, con los hashes de commit. Nota: la fase 6 se
  cerró por la excepción RGPD (Claude-en-sesión), no por Scaleway.

- [ ] **Cierre de sesión** — `python -m scripts.session_close` (o `/cierre`).

---

## Self-review (cubierto)

- **Cobertura del spec:** §3 arquitectura → Tasks 3–10 (módulo `core/sala_lectura.py`
  reusando `local_organizer`). §4 modelo de datos → Tasks 1–2. §5 API → Tasks 5–10
  (las 4 funciones + `organizar`). §6 reglas deterministas → Tasks 3–5. §7 bundles
  → Task 10 (con degradación). §8 disparo → Tasks 11–12. §9 idempotencia/aceptación
  → Tasks 9, 10 (SKIP/MOVE/dedup, `00_Input` intacto). §10 etapas → estructura del plan.
- **Excepción RGPD §2:** documentada en el docstring de `core/sala_lectura.py`
  (Task 3) y en el aviso del botón (Task 12).
- **Sin placeholders:** todos los pasos llevan código y comando concretos.
- **Consistencia de tipos:** `CatalogEntry` (Task 1) usado igual en todas; nombres
  de función (`clasificar_caso`/`aplicar_clasificacion`/`render_indices`/
  `poblar_sala_lectura`/`organizar`) idénticos en core, CLI y Streamlit.
- **Pendiente de verificar en ejecución:** formato exacto de `slugify` (Task 8,
  nota) y el patrón typer/Streamlit del repo (Tasks 11–12) — ajustar al observar
  el código real, sin cambiar helpers compartidos.
