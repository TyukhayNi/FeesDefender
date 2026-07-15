# Split de bundles multi-documento en la Sala de máquina — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Partir cada PDF-bundle multi-documento de `00_Input/` en sus N documentos lógicos (corte por hoja en blanco, marcadores como clasificador/fallback) ANTES de generar los MD, en vez de un único MD gigante.

**Architecture:** Cerebro nuevo aislado `core/split_documental.py` (detección de blanco por ráster+chars, segmentación pura, clasificación reusando `separar.detectar_tipo`, manifiesto editable, materialización reusando `separar.separar_pdf`). `core/anon/separar.py` se toca **solo** con un parámetro opcional aditivo `tipos_extra` (default `None` ⇒ comportamiento byte-idéntico; regla de oro respetada). La integración en la Sala de máquina (`core/sala_maquina.py`, `scripts/sala_maquina.py`) se secuencia **después** de que Cluster A mergee (mismos ficheros).

**Tech Stack:** Python 3, pytest, pypdf (cortar/leer), pypdfium2 + Pillow (ráster de tinta), fpdf2/reportlab (fixtures de test), Typer (CLI).

**Spec:** `docs/superpowers/specs/2026-07-14-split-sala-maquina-design.md`

---

## Notas de secuenciación (LEER ANTES DE EMPEZAR)

- **Fase F1 (Tareas 1–11) NO toca ficheros de Cluster A** (`core/sala_maquina.py`, `scripts/sala_maquina.py`). Se puede construir ya, en paralelo a Cluster A.
- **Fase F2 (Tareas 12–15) SÍ toca esos ficheros** → **NO empezar hasta que Cluster A haya mergeado a `main`**; rebasar la rama antes de la Tarea 12. El código de F2 se escribe contra la forma ACTUAL de `ejecutar`/`apply`; al rebasar, reconciliar el punto de inserción (marcado en cada tarea).
- Rama propia + PR (nunca push directo a `main`). Instalar hooks: `pre-commit install && pre-commit install --hook-type pre-push`.
- Entorno: Windows/PowerShell; empezar comandos con `cd "C:\Users\tnm33\Dev\FeesDefender"; .\.venv\Scripts\Activate.ps1`. Tests: `python -m pytest`.

### Validación contra `main` (recon 2026-07-15) — parche aplicado

Reconocimiento paralelo del código real de `main` (con Cluster A ya mergeado, PR #42 en `24e69db`) tras escribirse este plan. **Prerrequisito de F2 satisfecho.** Confirmado correcto: detección de tinta con PIL puro (sin numpy), anclas F1 (`detectar_tipo` L247/bucle L287; `detectar_segmentos` L337/llamada L376), y los helpers asumidos (`slugify`, `file_sha256`, `separar_pdf`/`generar_indice`, `PDFVacioError`). **Correcciones incorporadas al plan:**

- **D2 →** Task 11 Step 3b: añadir `split_documental` sube `INTAKE_EVENTS` a 24 y rompe `test_intake_log.py` (conteo + set) → actualizado en el mismo paso.
- **D3/D4 →** Task 12 Step 4: reescrito para cambiar `_ocr_y_extraer`→`list[DocCobertura]` y delegar en `_split_o_md`, **sin inlinear `ocr_pdf`** (así conserva el rescate por visión de Cluster A, `sala_maquina.py:357-370`); anclas F2 re-referenciadas (rama digital L414-422, `_ocr_y_extraer` L347-386, no 344-347).
- **D1 + estado →** Task 13B (NUEVA): `fusionar_cobertura` re-clavada a `(rel_path, slug)` (los N segmentos comparten `rel_path` y colapsaban a 1) + estado idempotente agrupado por `parent_sha256` (bundle) con regla "todos ok/low".
- **D5 →** Task 10: `_slug_seg` usa `_norm_tipo` (TIPO en MAYÚSCULAS), no `slugify` (que lo pasaría a minúsculas). Añadir `import re`.
- **D7 (deferido) →** `reforzar` por bundle entero: correcto pero subóptimo; follow-on documentado.

---

## File Structure

| Fichero | Rol | Fase |
|---|---|---|
| `tests/_pdf_fixtures.py` (crear) | helper compartido para construir PDFs de prueba (texto + páginas en blanco) | F1 |
| `core/anon/separar.py` (modificar) | param aditivo `tipos_extra` en `detectar_tipo` + `detectar_segmentos` | F1 |
| `core/split_documental.py` (crear) | cerebro del split: detección blanco, segmentación, clasificación, manifiesto, materialización | F1 |
| `core/intake_log.py` (modificar) | nuevo evento `split_documental` en `INTAKE_EVENTS` | F1 |
| `tests/test_split_documental.py` (crear) | unit + integración del cerebro | F1 |
| `tests/test_anon_separar.py` (modificar) | regresión byte-idéntica de `tipos_extra=None` + inyección | F1 |
| `core/sala_maquina.py` (modificar) | `_ocr_y_extraer`→lista + split entre OCR y MD; `DocCobertura` +campos; `fusionar_cobertura` re-clavada a `(rel_path, slug)` | **F2 (tras Cluster A)** |
| `scripts/sala_maquina.py` (modificar) | sub-gate del manifiesto en `plan`/`apply`; estado idempotente por `parent_sha256` | **F2 (tras Cluster A)** |
| `tests/test_split_sala_maquina_e2e.py` (crear) | E2E bundle→N MD + manifiesto respetado | F2 |

---

# FASE F1 — Cerebro aislado (independiente de Cluster A)

## Task 1: Helper de fixtures PDF (texto + páginas en blanco)

**Files:**
- Create: `tests/_pdf_fixtures.py`
- Test: `tests/test_split_documental.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_split_documental.py`:

```python
"""Tests del cerebro del split (core/split_documental)."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests._pdf_fixtures import build_pdf


def test_build_pdf_pagina_en_blanco_sin_texto(tmp_path: Path):
    # 3 páginas: texto, BLANCA ([]), texto
    pdf = build_pdf(tmp_path / "b.pdf", [["CEDULA DE EMPLAZAMIENTO", "Juzgado"], [], ["FACTURA", "Total 100"]])
    from pypdf import PdfReader
    with PdfReader(str(pdf)) as r:
        assert len(r.pages) == 3
        assert len((r.pages[1].extract_text() or "").strip()) < 10  # la blanca ~0 chars
        assert "CEDULA" in (r.pages[0].extract_text() or "").upper()
```

- [ ] **Step 2: Ejecutar el test para verlo fallar**

Run: `python -m pytest tests/test_split_documental.py::test_build_pdf_pagina_en_blanco_sin_texto -v`
Expected: FAIL con `ModuleNotFoundError: tests._pdf_fixtures`.

- [ ] **Step 3: Implementar el helper**

Crear `tests/_pdf_fixtures.py`:

```python
"""Helpers para construir PDFs de prueba con capa de texto real (sin fixtures binarios).

Reutiliza el patrón de ``tests/test_anon_separar._build_pdf`` (fpdf2). Una sublista
vacía ``[]`` produce una página SIN texto (delimitador en blanco para el detector).
"""
from __future__ import annotations

from pathlib import Path


def build_pdf(path: Path, pages: list[list[str]]) -> Path:
    """Construye un PDF: una página por sublista; cada string es una línea.

    ``[]`` ⇒ página en blanco (add_page sin celdas). Devuelve la ruta.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    for lineas in pages:
        pdf.add_page()
        pdf.set_font("helvetica", size=14)
        y = 20
        for ln in lineas:
            pdf.set_xy(15, y)
            pdf.cell(0, 8, ln)
            y += 12
    pdf.output(str(path))
    return path
```

- [ ] **Step 4: Ejecutar el test para verlo pasar**

Run: `python -m pytest tests/test_split_documental.py::test_build_pdf_pagina_en_blanco_sin_texto -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/_pdf_fixtures.py tests/test_split_documental.py
git commit -m "test(split): helper de fixtures PDF con páginas en blanco"
```

---

## Task 2: `separar.detectar_tipo` — parámetro aditivo `tipos_extra`

**Files:**
- Modify: `core/anon/separar.py:247-301` (`detectar_tipo`)
- Test: `tests/test_anon_separar.py`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_anon_separar.py`:

```python
def test_detectar_tipo_tipos_extra_none_identico():
    # Con tipos_extra=None debe dar EXACTAMENTE lo mismo que sin el argumento.
    lineas = ["CÉDULA DE EMPLAZAMIENTO", "Juzgado de Instancia"]
    assert detectar_tipo(lineas) == detectar_tipo(lineas, tipos_extra=None)


def test_detectar_tipo_inyecta_marcador_ev():
    extra = [{"tipo": "DOC_PBC", "prioridad": 7,
              "marcadores": ["PREVENCION DE BLANQUEO", "PREVENCIÓN DE BLANQUEO"],
              "exige_inicio": True}]
    lineas = ["PREVENCIÓN DE BLANQUEO DE CAPITALES"]
    tipo, prio, _ = detectar_tipo(lineas, tipos_extra=extra)
    assert tipo == "DOC_PBC"
    # Sin inyección, ese marcador no existe → no lo clasifica como PBC
    assert detectar_tipo(lineas)[0] != "DOC_PBC"
```

- [ ] **Step 2: Ejecutar para verlos fallar**

Run: `python -m pytest tests/test_anon_separar.py -k tipos_extra -v`
Expected: FAIL con `TypeError: detectar_tipo() got an unexpected keyword argument 'tipos_extra'`.

- [ ] **Step 3: Modificar `detectar_tipo`**

En `core/anon/separar.py`, cambiar la firma y el bucle de tipos. Firma actual:

```python
def detectar_tipo(lineas):
```

Cambiar a:

```python
def detectar_tipo(lineas, tipos_extra=None):
```

Y donde itera `for defn in TIPOS_DOCUMENTO:` (línea ~287), cambiar a:

```python
    for defn in TIPOS_DOCUMENTO + (tipos_extra or []):
```

(No se toca ninguna entrada de `TIPOS_DOCUMENTO`, ni regex, ni thresholds: solo se concatena una lista opcional cuyo default `None` reproduce el bucle actual.)

- [ ] **Step 4: Ejecutar para verlos pasar + regresión**

Run: `python -m pytest tests/test_anon_separar.py -k "tipos_extra or detectar_tipo" -v`
Expected: PASS (incluidos los tests previos de `detectar_tipo`).

- [ ] **Step 5: Commit**

```bash
git add core/anon/separar.py tests/test_anon_separar.py
git commit -m "feat(separar): tipos_extra opcional aditivo en detectar_tipo (regla de oro intacta)"
```

---

## Task 3: `separar.detectar_segmentos` — propagar `tipos_extra`

**Files:**
- Modify: `core/anon/separar.py:337-489` (`detectar_segmentos`)
- Test: `tests/test_anon_separar.py`

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_anon_separar.py`:

```python
def test_detectar_segmentos_acepta_tipos_extra(tmp_path):
    from tests._pdf_fixtures import build_pdf
    pdf = build_pdf(tmp_path / "x.pdf", [["ACTIVACION DEL ENCARGO", "cuerpo"]])
    extra = [{"tipo": "DOC_ACTIVACION", "prioridad": 7,
              "marcadores": ["ACTIVACION DEL ENCARGO", "ACTIVACIÓN DEL ENCARGO"],
              "exige_inicio": True}]
    segs = detectar_segmentos(pdf, _LOG_MUDO, tipos_extra=extra)
    assert any(s["tipo"] == "DOC_ACTIVACION" for s in segs)
```

- [ ] **Step 2: Ejecutar para verlo fallar**

Run: `python -m pytest tests/test_anon_separar.py::test_detectar_segmentos_acepta_tipos_extra -v`
Expected: FAIL con `TypeError: detectar_segmentos() got an unexpected keyword argument 'tipos_extra'`.

- [ ] **Step 3: Modificar `detectar_segmentos`**

Firma actual:

```python
def detectar_segmentos(ruta_pdf, log, *, on_page: "Callable[[int, int], None] | None" = None):
```

Cambiar a:

```python
def detectar_segmentos(ruta_pdf, log, *, on_page: "Callable[[int, int], None] | None" = None, tipos_extra=None):
```

Y la línea `tipo, prio, num_doc = detectar_tipo(lineas)` (dentro del bucle de la primera pasada, ~línea 376) cambiar a:

```python
            tipo, prio, num_doc = detectar_tipo(lineas, tipos_extra=tipos_extra)
```

- [ ] **Step 4: Ejecutar para verlo pasar**

Run: `python -m pytest tests/test_anon_separar.py::test_detectar_segmentos_acepta_tipos_extra -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/anon/separar.py tests/test_anon_separar.py
git commit -m "feat(separar): propagar tipos_extra en detectar_segmentos"
```

---

## Task 4: Modelos + `segmentar_por_blancos` (pura)

**Files:**
- Create: `core/split_documental.py`
- Test: `tests/test_split_documental.py`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_split_documental.py`:

```python
from core.split_documental import Segmento, DocLogico, segmentar_por_blancos


def test_segmentar_colapsa_blancos_y_bordes():
    # 8 págs, blancas en {3, 6, 7}. Blancos iniciales/finales/consecutivos no crean vacíos.
    assert segmentar_por_blancos(8, {3, 6, 7}) == [(1, 2), (4, 5), (8, 8)]


def test_segmentar_sin_blancos_un_solo_rango():
    assert segmentar_por_blancos(5, set()) == [(1, 5)]


def test_segmentar_todo_blanco_vacio():
    assert segmentar_por_blancos(3, {1, 2, 3}) == []
```

- [ ] **Step 2: Ejecutar para verlos fallar**

Run: `python -m pytest tests/test_split_documental.py -k segmentar -v`
Expected: FAIL con `ModuleNotFoundError: core.split_documental`.

- [ ] **Step 3: Crear `core/split_documental.py` con modelos + función pura**

```python
"""Cerebro del split de bundles multi-documento en la Sala de máquina.

Corte primario por HOJA EN BLANCO (chars≈0 ∧ baja tinta); marcadores como
clasificador (separar.detectar_tipo) y fallback (separar.detectar_segmentos).
NO edita core/anon/: reutiliza separar.py como librería. Ver
docs/superpowers/specs/2026-07-14-split-sala-maquina-design.md.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from core.anon import separar
from core.anon.exceptions import PDFVacioError
from core.utils import file_sha256

_LOG = logging.getLogger("split_documental")
if not _LOG.handlers:
    _LOG.addHandler(logging.NullHandler())

# Umbrales del detector de blanco (calibrar contra el bundle real en F0, Task 8b).
UMBRAL_CHARS_BLANCO = 10       # < → candidata a blanco (cribado barato por chars OCR)
UMBRAL_TINTA_BLANCO = 0.008    # fracción de píxeles con tinta; < → blanco confirmado
_RENDER_SCALE = 2              # pypdfium2 → ~144 dpi
_UMBRAL_OSCURO = 200           # nivel de gris (0-255) por debajo del cual el píxel es "tinta"


@dataclass
class Segmento:
    seg: int
    pagina_inicio: int
    pagina_fin: int
    tipo: str
    role: str = "documento"


@dataclass
class DocLogico:
    slug: str
    seg_sha256: str
    destino: str          # passthrough | split | merge
    tipo: str
    parent_slug: str
    parent_sha256: str
    role_in_bundle: str
    paginas: str | None
    fuentes: list[str] = field(default_factory=list)


def segmentar_por_blancos(total_pag: int, blancos: set[int]) -> list[tuple[int, int]]:
    """Puro: rangos (inicio, fin) 1-based inclusive EXCLUYENDO las páginas en blanco.

    Colapsa blancos consecutivos, iniciales y finales; nunca emite rangos vacíos.
    """
    rangos: list[tuple[int, int]] = []
    inicio: int | None = None
    for p in range(1, total_pag + 1):
        if p in blancos:
            if inicio is not None:
                rangos.append((inicio, p - 1))
                inicio = None
        else:
            if inicio is None:
                inicio = p
    if inicio is not None:
        rangos.append((inicio, total_pag))
    return rangos
```

- [ ] **Step 4: Ejecutar para verlos pasar**

Run: `python -m pytest tests/test_split_documental.py -k segmentar -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add core/split_documental.py tests/test_split_documental.py
git commit -m "feat(split): modelos + segmentar_por_blancos (pura)"
```

---

## Task 5: `_primeras_lineas` + `clasificar`

**Files:**
- Modify: `core/split_documental.py`
- Test: `tests/test_split_documental.py`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_split_documental.py`:

```python
from core.split_documental import _primeras_lineas, clasificar


def test_primeras_lineas_filtra_cortas_y_limita():
    txt = "CEDULA DE EMPLAZAMIENTO\nab\nJuzgado de Instancia\nlinea3\nlinea4\nlinea5\nlinea6"
    out = _primeras_lineas(txt, n=3)
    assert out == ["CEDULA DE EMPLAZAMIENTO", "Juzgado de Instancia", "linea3"]  # 'ab' (<3) fuera


def test_clasificar_usa_marcador_judicial():
    textos = ["CÉDULA DE EMPLAZAMIENTO\nJuzgado", "otra pagina"]
    assert clasificar(textos, 1, 1) == "CEDULA_EMPLAZAMIENTO"


def test_clasificar_sin_marcador_devuelve_documento():
    textos = ["texto anodino sin marcadores reconocibles"]
    assert clasificar(textos, 1, 1) == "DOCUMENTO"
```

- [ ] **Step 2: Ejecutar para verlos fallar**

Run: `python -m pytest tests/test_split_documental.py -k "primeras_lineas or clasificar" -v`
Expected: FAIL con `ImportError` / `AttributeError`.

- [ ] **Step 3: Implementar en `core/split_documental.py`**

Añadir (tras `segmentar_por_blancos`):

```python
def _primeras_lineas(texto_pagina: str, n: int = 5) -> list[str]:
    """Primeras N líneas útiles (>=3 chars) del texto de una página (para clasificar)."""
    out: list[str] = []
    for raw in (texto_pagina or "").splitlines():
        ln = raw.strip()
        if len(ln) >= 3:
            out.append(ln)
        if len(out) >= n:
            break
    return out


def clasificar(textos: list[str], inicio: int, fin: int, *, tipos_extra=None) -> str:
    """Etiqueta un segmento por los marcadores de su primera página (separar.detectar_tipo).

    Reutiliza los marcadores judiciales de separar.py + los E&V inyectados. Sin
    marcador reconocible → 'DOCUMENTO'.
    """
    if tipos_extra is None:
        tipos_extra = TIPOS_EXTRA_EV
    lineas = _primeras_lineas(textos[inicio - 1]) if 0 <= inicio - 1 < len(textos) else []
    tipo, _prio, _num = separar.detectar_tipo(lineas, tipos_extra=tipos_extra)
    return tipo or "DOCUMENTO"
```

> `TIPOS_EXTRA_EV` se define en la Task 6; para que estos tests corran ya, añade **provisionalmente** `TIPOS_EXTRA_EV: list[dict] = []` cerca de las constantes. La Task 6 lo rellena.

- [ ] **Step 4: Ejecutar para verlos pasar**

Run: `python -m pytest tests/test_split_documental.py -k "primeras_lineas or clasificar" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/split_documental.py tests/test_split_documental.py
git commit -m "feat(split): _primeras_lineas + clasificar (reusa separar.detectar_tipo)"
```

---

## Task 6: `TIPOS_EXTRA_EV` (marcadores E&V inyectados)

**Files:**
- Modify: `core/split_documental.py`
- Test: `tests/test_split_documental.py`

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_split_documental.py`:

```python
import pytest as _pytest
from core.split_documental import TIPOS_EXTRA_EV


@_pytest.mark.parametrize("linea,esperado", [
    ("PREVENCIÓN DE BLANQUEO DE CAPITALES", "DOC_PBC"),
    ("CONTRATO DE ARRAS PENITENCIALES", "DOC_ARRAS"),
    ("DOCUMENTO DE RESERVA", "DOC_RESERVA"),
])
def test_marcadores_ev_clasifican(linea, esperado):
    assert clasificar([linea], 1, 1) == esperado


def test_tipos_extra_ev_no_vacio():
    assert len(TIPOS_EXTRA_EV) >= 3
```

- [ ] **Step 2: Ejecutar para verlo fallar**

Run: `python -m pytest tests/test_split_documental.py -k "marcadores_ev or tipos_extra_ev" -v`
Expected: FAIL (clasifica como `DOCUMENTO`, no `DOC_PBC`).

- [ ] **Step 3: Rellenar `TIPOS_EXTRA_EV`**

Reemplazar el `TIPOS_EXTRA_EV: list[dict] = []` provisional por:

```python
# Marcadores E&V inyectados (hueco del congelado: separar.TIPOS_DOCUMENTO está
# tuneado a lo judicial). Se pasan como tipos_extra; NO viven en core/anon.
TIPOS_EXTRA_EV: list[dict] = [
    {"tipo": "DOC_PBC", "prioridad": 7, "exige_inicio": True,
     "marcadores": ["PREVENCION DE BLANQUEO", "PREVENCIÓN DE BLANQUEO",
                    "SUJETO OBLIGADO", "IDENTIFICACION DEL TITULAR REAL",
                    "IDENTIFICACIÓN DEL TITULAR REAL"]},
    {"tipo": "DOC_ARRAS", "prioridad": 7, "exige_inicio": True,
     "marcadores": ["CONTRATO DE ARRAS", "ARRAS PENITENCIALES", "SEÑAL Y ARRAS"]},
    {"tipo": "DOC_RESERVA", "prioridad": 7, "exige_inicio": True,
     "marcadores": ["DOCUMENTO DE RESERVA", "HOJA DE RESERVA", "CONTRATO DE RESERVA"]},
    {"tipo": "DOC_ACTIVACION", "prioridad": 7, "exige_inicio": True,
     "marcadores": ["ACTIVACION DEL ENCARGO", "ACTIVACIÓN DEL ENCARGO", "HOJA DE ACTIVACION",
                    "HOJA DE ACTIVACIÓN"]},
    {"tipo": "DOC_OFERTA", "prioridad": 6, "exige_inicio": True,
     "marcadores": ["OFERTA DE COMPRA", "HOJA DE OFERTA", "PROPUESTA DE COMPRA"]},
    {"tipo": "DOC_RECLAMACION", "prioridad": 6, "exige_inicio": True,
     "marcadores": ["RECLAMACION DE CANTIDAD", "RECLAMACIÓN DE CANTIDAD",
                    "REQUERIMIENTO DE PAGO", "BUROFAX"]},
]
```

- [ ] **Step 4: Ejecutar para verlo pasar**

Run: `python -m pytest tests/test_split_documental.py -k "marcadores_ev or tipos_extra_ev" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/split_documental.py tests/test_split_documental.py
git commit -m "feat(split): TIPOS_EXTRA_EV (arras/PBC/reserva/activación/oferta/reclamación)"
```

---

## Task 7: Detección de blanco por ráster (`cobertura_tinta`, `paginas_en_blanco`)

**Files:**
- Modify: `core/split_documental.py`
- Test: `tests/test_split_documental.py`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_split_documental.py`:

```python
from core.split_documental import cobertura_tinta, paginas_en_blanco, _texto_por_pagina


def test_cobertura_tinta_blanca_vs_texto(tmp_path):
    pdf = build_pdf(tmp_path / "t.pdf", [["MUCHO TEXTO EN ESTA PAGINA " * 5], []])
    tinta_texto = cobertura_tinta(pdf, 1)
    tinta_blanca = cobertura_tinta(pdf, 2)
    assert tinta_blanca < tinta_texto
    assert tinta_blanca < 0.008  # la blanca por debajo del umbral


def test_paginas_en_blanco_detecta_la_delimitadora(tmp_path):
    pdf = build_pdf(tmp_path / "b.pdf", [["CEDULA DE EMPLAZAMIENTO"], [], ["FACTURA"]])
    textos = _texto_por_pagina(pdf)
    assert paginas_en_blanco(pdf, textos) == {2}
```

- [ ] **Step 2: Ejecutar para verlos fallar**

Run: `python -m pytest tests/test_split_documental.py -k "cobertura_tinta or paginas_en_blanco" -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementar en `core/split_documental.py`**

```python
def _texto_por_pagina(pdf_path: Path) -> list[str]:
    """Texto de cada página vía pypdf (cribado barato; el buscable ya tiene capa)."""
    from pypdf import PdfReader
    with PdfReader(str(pdf_path)) as reader:
        return [(p.extract_text() or "") for p in reader.pages]


def cobertura_tinta(pdf_path: Path, num_pag: int, *, scale: int = _RENDER_SCALE) -> float:
    """Fracción de píxeles con tinta (grises < _UMBRAL_OSCURO) de la página `num_pag` (1-based).

    Una hoja en blanco (aunque escaneada, con mota/franjas) queda muy por debajo del
    umbral; una foto/plano escaneado con 0 chars OCR tiene tinta alta → NO es blanco.
    """
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        pil = doc[num_pag - 1].render(scale=scale).to_pil().convert("L")
    finally:
        doc.close()
    hist = pil.histogram()               # 256 buckets para modo 'L'
    oscuros = sum(hist[:_UMBRAL_OSCURO])
    total = pil.width * pil.height
    return oscuros / total if total else 0.0


def paginas_en_blanco(pdf_path: Path, textos: list[str], *,
                      umbral_chars: int = UMBRAL_CHARS_BLANCO,
                      umbral_tinta: float = UMBRAL_TINTA_BLANCO) -> set[int]:
    """Páginas delimitadoras (1-based): pocos chars OCR Y baja cobertura de tinta.

    Cribado barato por chars primero; solo las candidatas se rasterizan (coste
    acotado a las páginas vacías-de-texto, no a las 200).
    """
    blancos: set[int] = set()
    for i, txt in enumerate(textos, 1):
        if len((txt or "").strip()) >= umbral_chars:
            continue  # tiene texto → no es separador
        if cobertura_tinta(pdf_path, i) < umbral_tinta:
            blancos.add(i)
    return blancos
```

- [ ] **Step 4: Ejecutar para verlos pasar**

Run: `python -m pytest tests/test_split_documental.py -k "cobertura_tinta or paginas_en_blanco" -v`
Expected: PASS.

> **Nota de calibración (F0):** `UMBRAL_TINTA_BLANCO`/`UMBRAL_CHARS_BLANCO` se ajustan contra el bundle escaneado REAL (dato gitignored) ejecutando `paginas_en_blanco` sobre él y comparando con la verdad-terreno. Los valores iniciales pasan los fixtures sintéticos; anota el valor final en un comentario del módulo si difiere.

- [ ] **Step 5: Commit**

```bash
git add core/split_documental.py tests/test_split_documental.py
git commit -m "feat(split): detección de blanco por chars+tinta (ráster pypdfium2)"
```

---

## Task 8: `detectar` (orquesta blanco → fallback → passthrough)

**Files:**
- Modify: `core/split_documental.py`
- Test: `tests/test_split_documental.py`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_split_documental.py`:

```python
from core.split_documental import detectar


def test_detectar_por_blancos(tmp_path):
    pdf = build_pdf(tmp_path / "j.pdf", [
        ["CEDULA DE EMPLAZAMIENTO"], [],
        ["A U T O", "AUTO Nº 12"], [],
        ["FACTURA", "Invoice"],
    ])
    segmentos, blancos = detectar(pdf)
    assert blancos == {2, 4}
    assert [(s.pagina_inicio, s.pagina_fin) for s in segmentos] == [(1, 1), (3, 3), (5, 5)]
    assert segmentos[0].tipo == "CEDULA_EMPLAZAMIENTO"
    assert segmentos[2].tipo == "DOC_FACTURA"


def test_detectar_sin_blancos_fallback_marcadores(tmp_path):
    # Sin páginas en blanco; dos documentos con marcador → fallback separar los separa.
    pdf = build_pdf(tmp_path / "n.pdf", [
        ["CÉDULA DE EMPLAZAMIENTO", "cuerpo"],
        ["FACTURA", "Total 100"],
    ])
    segmentos, blancos = detectar(pdf)
    assert blancos == set()
    assert len(segmentos) >= 2


def test_detectar_documento_unico_passthrough(tmp_path):
    pdf = build_pdf(tmp_path / "u.pdf", [["FACTURA", "una sola factura", "Total 50"]])
    segmentos, blancos = detectar(pdf)
    assert len(segmentos) == 1
    assert segmentos[0].pagina_inicio == 1 and segmentos[0].pagina_fin == 1
```

- [ ] **Step 2: Ejecutar para verlos fallar**

Run: `python -m pytest tests/test_split_documental.py -k detectar -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementar `detectar`**

```python
def detectar(pdf_path: Path, *, tipos_extra=None, log: logging.Logger | None = None
             ) -> tuple[list[Segmento], set[int]]:
    """Detecta los documentos lógicos de un PDF ya buscable.

    Primario: hoja en blanco. Fallback (sin blancos): marcadores (separar). Si
    ni una ni otro dan >1 → passthrough (un solo segmento con todo el PDF).
    Devuelve (segmentos, paginas_en_blanco).
    """
    log = log or _LOG
    if tipos_extra is None:
        tipos_extra = TIPOS_EXTRA_EV
    pdf_path = Path(pdf_path)

    textos = _texto_por_pagina(pdf_path)
    total = len(textos)
    if total == 0:
        raise PDFVacioError(f"PDF sin páginas: {pdf_path.name}")

    blancos = paginas_en_blanco(pdf_path, textos)
    rangos = segmentar_por_blancos(total, blancos)

    if len(rangos) > 1:
        segmentos = [
            Segmento(seg=i, pagina_inicio=ini, pagina_fin=fin,
                     tipo=clasificar(textos, ini, fin, tipos_extra=tipos_extra))
            for i, (ini, fin) in enumerate(rangos, 1)
        ]
        return segmentos, blancos

    # Sin blancos útiles → fallback por marcadores
    segs_sep = separar.detectar_segmentos(pdf_path, log, tipos_extra=tipos_extra)
    if len(segs_sep) > 1:
        segmentos = [
            Segmento(seg=i, pagina_inicio=s["pagina_inicio"], pagina_fin=s["pagina_fin"],
                     tipo=s["tipo"])
            for i, s in enumerate(segs_sep, 1)
        ]
        return segmentos, blancos

    # Passthrough
    tipo = clasificar(textos, 1, total, tipos_extra=tipos_extra)
    return [Segmento(seg=1, pagina_inicio=1, pagina_fin=total, tipo=tipo)], blancos
```

- [ ] **Step 4: Ejecutar para verlos pasar**

Run: `python -m pytest tests/test_split_documental.py -k detectar -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add core/split_documental.py tests/test_split_documental.py
git commit -m "feat(split): detectar (blanco→fallback marcadores→passthrough)"
```

---

## Task 9: Manifiesto — construir / escribir / leer / validar

**Files:**
- Modify: `core/split_documental.py`
- Test: `tests/test_split_documental.py`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_split_documental.py`:

```python
from core.split_documental import (
    construir_manifiesto, escribir_manifiesto, leer_manifiesto, validar_manifiesto,
)


def test_construir_y_roundtrip_manifiesto(tmp_path):
    segs = [Segmento(1, 1, 4, "CEDULA_EMPLAZAMIENTO"), Segmento(2, 6, 12, "AUTO")]
    man = construir_manifiesto("01_Drive EV/bundle.pdf", "a1b2c3d4" * 8, segs, {5})
    assert man["segmentos"][0]["pp"] == "1-4"
    assert man["delimitadores"] == [5]
    escribir_manifiesto(tmp_path, man)
    assert (tmp_path / "_segmentacion.json").exists()
    assert (tmp_path / "_segmentacion.md").exists()
    assert leer_manifiesto(tmp_path)["segmentos"][1]["tipo"] == "AUTO"


def test_validar_rechaza_rango_invalido():
    man = {"segmentos": [{"seg": 1, "pp": "1-4", "tipo": "X", "role": "documento"},
                         {"seg": 2, "pp": "3-9", "tipo": "Y", "role": "documento"}]}
    with pytest.raises(ValueError, match="solap"):
        validar_manifiesto(man, total_pag=20)


def test_validar_rechaza_fuera_de_rango():
    man = {"segmentos": [{"seg": 1, "pp": "1-40", "tipo": "X", "role": "documento"}]}
    with pytest.raises(ValueError, match="fuera de rango"):
        validar_manifiesto(man, total_pag=20)
```

- [ ] **Step 2: Ejecutar para verlos fallar**

Run: `python -m pytest tests/test_split_documental.py -k manifiesto -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementar en `core/split_documental.py`**

Añadir `import json` arriba, y:

```python
_MANIFIESTO_JSON = "_segmentacion.json"
_MANIFIESTO_MD = "_segmentacion.md"


def _pp(inicio: int, fin: int) -> str:
    return f"{inicio}-{fin}"


def _pp_a_rango(pp: str) -> tuple[int, int]:
    a, b = pp.split("-", 1)
    return int(a), int(b)


def construir_manifiesto(bundle_rel_path: str, bundle_sha256: str,
                         segmentos: list[Segmento], blancos: set[int]) -> dict:
    return {
        "fuente": bundle_rel_path,
        "bundle_sha256": bundle_sha256,
        "segmentos": [{"seg": s.seg, "pp": _pp(s.pagina_inicio, s.pagina_fin),
                       "tipo": s.tipo, "role": s.role} for s in segmentos],
        "delimitadores": sorted(blancos),
    }


def escribir_manifiesto(carpeta_bundle: Path, manifiesto: dict) -> None:
    carpeta_bundle = Path(carpeta_bundle)
    carpeta_bundle.mkdir(parents=True, exist_ok=True)
    (carpeta_bundle / _MANIFIESTO_JSON).write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    lineas = [
        "<!-- GENERADO — editable: ajusta pp/tipo/role y re-ejecuta apply -->",
        f"# Segmentación propuesta — {manifiesto['fuente']}",
        "",
        "| seg | páginas | tipo | role |",
        "|---|---|---|---|",
    ]
    for e in manifiesto["segmentos"]:
        lineas.append(f"| {e['seg']} | {e['pp']} | {e['tipo']} | {e['role']} |")
    lineas += ["", f"Delimitadores (hojas en blanco descartadas): {manifiesto['delimitadores']}", ""]
    (carpeta_bundle / _MANIFIESTO_MD).write_text("\n".join(lineas) + "\n", encoding="utf-8")


def leer_manifiesto(carpeta_bundle: Path) -> dict:
    return json.loads((Path(carpeta_bundle) / _MANIFIESTO_JSON).read_text(encoding="utf-8"))


def manifiesto_existe(carpeta_bundle: Path) -> bool:
    return (Path(carpeta_bundle) / _MANIFIESTO_JSON).exists()


def validar_manifiesto(manifiesto: dict, total_pag: int) -> None:
    """Falla claro si algún rango está fuera de [1, total_pag] o solapa/está desordenado."""
    ultimo_fin = 0
    for e in sorted(manifiesto["segmentos"], key=lambda x: _pp_a_rango(x["pp"])[0]):
        ini, fin = _pp_a_rango(e["pp"])
        if ini < 1 or fin > total_pag or fin < ini:
            raise ValueError(f"Segmento {e['seg']} fuera de rango: {e['pp']} (total {total_pag})")
        if ini <= ultimo_fin:
            raise ValueError(f"Segmento {e['seg']} solapa con el anterior: {e['pp']}")
        ultimo_fin = fin
```

- [ ] **Step 4: Ejecutar para verlos pasar**

Run: `python -m pytest tests/test_split_documental.py -k manifiesto -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add core/split_documental.py tests/test_split_documental.py
git commit -m "feat(split): manifiesto editable (construir/escribir/leer/validar)"
```

---

## Task 10: `materializar` (split → PDFs + DocLogico)

**Files:**
- Modify: `core/split_documental.py`
- Test: `tests/test_split_documental.py`

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_split_documental.py`:

```python
from core.split_documental import materializar


def test_materializar_corta_y_devuelve_doclogicos(tmp_path):
    pdf = build_pdf(tmp_path / "j.pdf", [
        ["CEDULA DE EMPLAZAMIENTO"], [], ["A U T O", "AUTO Nº 12"], [], ["FACTURA"],
    ])
    from core.split_documental import detectar
    segs, blancos = detectar(pdf)
    man = construir_manifiesto("01_Drive EV/j.pdf", "d" * 64, segs, blancos)
    carpeta = tmp_path / "02_Documentos" / "bundle-slug"
    docs = materializar(pdf, man, carpeta, parent_slug="bundle-slug",
                        parent_sha256="d" * 64, bundle_rel_path="01_Drive EV/j.pdf")
    assert len(docs) == 3
    # Un PDF por segmento con nombre = seg_slug + índice de segmentación
    pdfs = sorted(carpeta.glob("*.pdf"))
    assert len(pdfs) == 3
    assert (carpeta / "indice.json").exists()
    d0 = docs[0]
    assert d0.destino == "split"
    assert d0.parent_slug == "bundle-slug"
    assert d0.role_in_bundle == "documento"
    assert d0.paginas == "1-1"
    assert len(d0.seg_sha256) == 64
    assert d0.slug.endswith(d0.seg_sha256[:8])
    assert d0.fuentes == ["01_Drive EV/j.pdf"]
```

- [ ] **Step 2: Ejecutar para verlo fallar**

Run: `python -m pytest tests/test_split_documental.py::test_materializar_corta_y_devuelve_doclogicos -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementar `materializar`**

```python
def _norm_tipo(tipo: str) -> str:
    """TIPO en MAYÚSCULAS y path-safe. NO usa slugify (lleva lowercase=True y
    machacaría el case): decisión D5 de la validación 2026-07-15. Colapsa cualquier
    char no [A-Z0-9] a '_'; vacío → 'DOCUMENTO'."""
    return re.sub(r"[^A-Z0-9]+", "_", (tipo or "").upper()).strip("_") or "DOCUMENTO"


def _slug_seg(parent_slug: str, seg: int, tipo: str, seg_sha256: str) -> str:
    # parent_slug ya viene de output_slug (path-safe). TIPO por _norm_tipo (mayúsculas),
    # NO slugify: slugify lo pasaría a minúsculas (D5).
    return f"{parent_slug}__seg{seg:02d}_{_norm_tipo(tipo)}__{seg_sha256[:8]}"


def materializar(pdf_path: Path, manifiesto: dict, carpeta_bundle: Path, *,
                 parent_slug: str, parent_sha256: str, bundle_rel_path: str,
                 log: logging.Logger | None = None) -> list[DocLogico]:
    """Corta el bundle según el manifiesto → PDFs en carpeta_bundle + DocLogico por segmento.

    Reutiliza separar.separar_pdf (cortador atómico Windows-safe) y separar.generar_indice.
    Renombra cada PDF a {seg_slug}.pdf (identidad estable por contenido).
    """
    log = log or _LOG
    pdf_path = Path(pdf_path)
    carpeta_bundle = Path(carpeta_bundle)
    carpeta_bundle.mkdir(parents=True, exist_ok=True)

    segs_sep = []
    for e in manifiesto["segmentos"]:
        ini, fin = _pp_a_rango(e["pp"])
        segs_sep.append({"tipo": e["tipo"], "num_doc": e["seg"],
                         "pagina_inicio": ini, "pagina_fin": fin, "lineas_inicio": []})

    resultados = separar.separar_pdf(pdf_path, segs_sep, carpeta_bundle, log)
    separar.generar_indice(resultados, pdf_path, carpeta_bundle, log)

    docs: list[DocLogico] = []
    for e, r in zip(manifiesto["segmentos"], resultados):
        emitido = carpeta_bundle / r["archivo"]
        seg_sha = file_sha256(emitido)
        slug = _slug_seg(parent_slug, e["seg"], e["tipo"], seg_sha)
        destino_pdf = carpeta_bundle / f"{slug}.pdf"
        emitido.replace(destino_pdf)   # renombrar a identidad estable por contenido
        docs.append(DocLogico(
            slug=slug, seg_sha256=seg_sha, destino="split", tipo=e["tipo"],
            parent_slug=parent_slug, parent_sha256=parent_sha256,
            role_in_bundle=e.get("role", "documento"), paginas=r["paginas"],
            fuentes=[bundle_rel_path],
        ))
    return docs
```

> **Verificado (recon 2026-07-15):** `core.utils.slugify` existe (`core/utils.py:27`) pero fuerza minúsculas (`lowercase=True`); por eso `_slug_seg` usa `_norm_tipo` (mayúsculas) para el TIPO, NO `slugify`. Añade `import re` al principio de `core/split_documental.py` (junto a `import json` de la Task 9). `file_sha256` y `separar.separar_pdf`/`generar_indice`/`PDFVacioError` verificados presentes con la firma asumida.

- [ ] **Step 4: Ejecutar para verlo pasar**

Run: `python -m pytest tests/test_split_documental.py::test_materializar_corta_y_devuelve_doclogicos -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/split_documental.py tests/test_split_documental.py
git commit -m "feat(split): materializar (corta con separar_pdf + DocLogico + indice)"
```

---

## Task 11: Evento de log `split_documental`

**Files:**
- Modify: `core/intake_log.py:42-67` (`INTAKE_EVENTS`)
- Test: `tests/test_intake_log.py` (o el test existente de eventos)

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_split_documental.py` (auto-contenido, no depende de config global):

```python
def test_split_documental_es_evento_valido():
    from core.intake_log import INTAKE_EVENTS
    assert "split_documental" in INTAKE_EVENTS
```

- [ ] **Step 2: Ejecutar para verlo fallar**

Run: `python -m pytest tests/test_split_documental.py::test_split_documental_es_evento_valido -v`
Expected: FAIL (`assert 'split_documental' in INTAKE_EVENTS`).

- [ ] **Step 3: Añadir el evento**

En `core/intake_log.py`, dentro del `frozenset` `INTAKE_EVENTS`, tras la línea `"procesado_sala_maquina", ...`:

```python
    "split_documental",        # split 1→N de un bundle en 02_Documentos/ (documentos lógicos)
```

- [ ] **Step 3b: Actualizar los tests de conteo/set de `INTAKE_EVENTS`**

Añadir el evento **rompe dos asserts existentes** de `tests/test_intake_log.py` (recon 2026-07-15): el conteo `len(INTAKE_EVENTS) == 23` (~L332-334) y el set exacto de `test_intake_events_contiene_los_canonicos` (~L349). Sube el conteo a **24** y añade `"split_documental"` al set esperado:

```python
# tests/test_intake_log.py — test de conteo:
assert len(intake_log.INTAKE_EVENTS) == 24   # era 23; +split_documental
# y en test_intake_events_contiene_los_canonicos, añadir al set esperado:
    "split_documental",
```

NO tocar `traza.UPLOAD_EVENTS` (el split NO lo emite Cowork): el test de paridad `test_intake_traza.py::test_paridad_eventos_subconjunto_de_core` (UPLOAD_EVENTS ⊆ INTAKE_EVENTS) sigue verde porque solo añadimos a INTAKE_EVENTS.

- [ ] **Step 4: Ejecutar para verlo pasar**

Run: `python -m pytest tests/test_split_documental.py::test_split_documental_es_evento_valido -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/intake_log.py tests/test_split_documental.py
git commit -m "feat(intake_log): evento split_documental"
```

---

## Checkpoint F1

- [ ] Suite del cerebro verde: `python -m pytest tests/test_split_documental.py tests/test_anon_separar.py -v`
- [ ] Regresión global (marcadores del anonimizador intactos): `python -m pytest -q`
- [ ] Abrir PR de F1 (cerebro + separar param). **F1 es entregable por sí solo** (cerebro testeado, sin integración).

---

# FASE F2 — Integración en la Sala de máquina (⚠️ SOLO tras Cluster A mergeado)

> **Antes de la Tarea 12:** confirmar que Cluster A (cobertura acumulativa + `--vision` + reforzar) está en `main`; rebasar esta rama sobre `main`. Los puntos de inserción abajo se describen contra la forma ACTUAL de `core/sala_maquina.ejecutar` / `scripts/sala_maquina.apply`; **reconciliar con la versión mergeada** (los nombres de helpers de Cluster A pueden variar; el punto lógico —tras obtener el PDF buscable y ANTES de `_escribir_md`— no cambia).

## Task 12: Enganchar el split en `sala_maquina.ejecutar` (entre OCR y MD)

**Files:**
- Modify: `core/sala_maquina.py` (rama `d.ruta == "pdf"` de `ejecutar` + `DocCobertura`)
- Test: `tests/test_split_sala_maquina_e2e.py` (crear)

**Contexto del punto de inserción (código actual):** en `ejecutar`, un PDF con capa de texto suficiente hace `_escribir_md(...)` y `continue` (`core/sala_maquina.py:344-347`); un escaneado va a `_ocr_y_extraer` que internamente hace OCR→`_try_pypdf`→`_escribir_md`. El split se inserta **sobre el PDF buscable** (el original digital, o el `01_OCR/{slug}.pdf` que produjo `_ocr_y_extraer`), **antes** de escribir el MD del bundle. Cuando hay ≥2 segmentos, en vez de un MD del bundle se generan N MD (uno por documento lógico) y N filas de cobertura.

- [ ] **Step 1: Extender `DocCobertura` con los campos de documento lógico**

En `core/sala_maquina.py`, añadir a la dataclass `DocCobertura` (tras `sha256: str = ""`):

```python
    parent_slug: str = ""       # slug del bundle si es un segmento (split); vacío si suelto
    parent_sha256: str = ""     # sha del fichero FÍSICO de origen; clave del estado idempotente
    role: str = "documento"     # role_in_bundle
    paginas: str = ""           # rango en el bundle ("1-4"); vacío si no aplica
    tipo: str = ""              # tipo clasificado del documento lógico

# `sha256` sigue siendo la custodia de ESTA fila (= seg_sha256 en un segmento, = sha del
# fichero en un passthrough); `parent_sha256` es el sha del FÍSICO (bundle) y es la clave
# por la que el estado idempotente marca "procesado" (ver Task 13B). Ambos con default
# para que un _cobertura.json antiguo se lea sin romper (cobertura_desde_dicts tolerante).
```

- [ ] **Step 2: Escribir el test E2E que falla**

Crear `tests/test_split_sala_maquina_e2e.py`:

```python
"""E2E: un bundle digital multi-doc produce N MD (documentos lógicos), no 1 gigante."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests._pdf_fixtures import build_pdf

pytestmark = pytest.mark.slow


def _bundle_digital(dirpath: Path) -> Path:
    # PDF CON capa de texto (digital): _try_pypdf lo lee sin OCR. 3 docs + 2 blancos.
    return build_pdf(dirpath / "00_Input" / "01_Drive EV" / "bundle.pdf", [
        ["CEDULA DE EMPLAZAMIENTO", "Juzgado"], [],
        ["A U T O", "AUTO Nº 12"], [],
        ["FACTURA", "Total 100"],
    ])


def test_bundle_digital_se_parte_en_n_md(tmp_path, monkeypatch):
    import core.config as config
    case_dir = tmp_path / "W-TEST01"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    _bundle_digital(case_dir)
    monkeypatch.setattr(config, "caso_path", lambda cid: case_dir)

    from core import sala_maquina as sm
    docs = sm.plan(sm.inventariar(case_dir), set())
    cob = sm.ejecutar(case_dir, docs, case_id="W-TEST01")

    # 3 documentos lógicos, no 1 bundle
    seg_rows = [c for c in cob if c.parent_slug]
    assert len(seg_rows) == 3
    md_dir = case_dir / "01_Procesado" / "02_Sala de máquina" / "03_MD"
    assert len(list(md_dir.glob("*.md"))) == 3
    docs_dir = case_dir / "01_Procesado" / "02_Sala de máquina" / "02_Documentos"
    assert len(list(docs_dir.rglob("*.pdf"))) == 3
```

- [ ] **Step 3: Ejecutar para verlo fallar**

Run: `python -m pytest tests/test_split_sala_maquina_e2e.py -v --runslow`
Expected: FAIL (hoy `ejecutar` genera 1 MD del bundle; `parent_slug` no se puebla).

- [ ] **Step 4: Insertar el split en `ejecutar`**

En `core/sala_maquina.py`, crear un helper y llamarlo desde la rama PDF. Añadir imports arriba:

```python
from core import split_documental as split
from core.intake_log import append_event
```

Añadir el helper (junto a `_ocr_y_extraer`):

```python
def _split_o_md(case_dir: Path, sm_dir: Path, case_id: str, d: DocPlan,
                buscable: Path, metodo_base: str, ocr: bool, vision: bool) -> list[DocCobertura]:
    """Sobre el PDF buscable: si tiene ≥2 segmentos, corta y genera MD por documento lógico;
    si no, MD único (passthrough, comportamiento actual). Devuelve filas de cobertura.
    """
    segmentos, blancos = split.detectar(buscable)
    if len(segmentos) <= 1:
        # passthrough: MD único como hoy
        texto = _try_pypdf(buscable) or ""
        estado, nota = ocr_quality(texto, _pdf_num_paginas(buscable))
        texto, estado, nota = _aplicar_vision(buscable, texto, estado, nota, vision)
        _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, metodo_base, ocr, estado)
        return [DocCobertura(d.slug, d.rel_path, metodo_base, estado, len(texto), ocr, nota, d.sha256,
                             parent_sha256=d.sha256, tipo=segmentos[0].tipo)]

    # split: manifiesto → materializar → MD por segmento
    carpeta_bundle = destino_seguro(sm_dir / "02_Documentos" / d.slug, case_dir)
    manifiesto = (split.leer_manifiesto(carpeta_bundle)
                  if split.manifiesto_existe(carpeta_bundle)
                  else split.construir_manifiesto(d.rel_path, d.sha256, segmentos, blancos))
    split.validar_manifiesto(manifiesto, _pdf_num_paginas(buscable) or 0)
    if not split.manifiesto_existe(carpeta_bundle):
        split.escribir_manifiesto(carpeta_bundle, manifiesto)
    doclogicos = split.materializar(buscable, manifiesto, carpeta_bundle,
                                    parent_slug=d.slug, parent_sha256=d.sha256,
                                    bundle_rel_path=d.rel_path)
    filas: list[DocCobertura] = []
    for dl in doclogicos:
        seg_pdf = carpeta_bundle / f"{dl.slug}.pdf"
        texto = _try_pypdf(seg_pdf) or ""
        estado, nota = ocr_quality(texto, _pdf_num_paginas(seg_pdf))
        texto, estado, nota = _aplicar_vision(seg_pdf, texto, estado, nota, vision)
        _escribir_md(case_dir, case_id, dl.slug, d.rel_path, texto, metodo_base, ocr, estado)
        filas.append(DocCobertura(dl.slug, d.rel_path, metodo_base, estado, len(texto), ocr, nota,
                                  dl.seg_sha256, parent_slug=dl.parent_slug, parent_sha256=d.sha256,
                                  role=dl.role_in_bundle, paginas=dl.paginas, tipo=dl.tipo))
    append_event(case_id, "split_documental", details={
        "bundle": d.rel_path, "bundle_sha256": d.sha256, "n_segmentos": len(doclogicos),
        "segmentos": [{"slug": dl.slug, "seg_sha256": dl.seg_sha256, "tipo": dl.tipo,
                       "paginas": dl.paginas} for dl in doclogicos],
        "delimitadores": manifiesto["delimitadores"],
    })
    return filas
```

**Reconciliado con el `main` post-Cluster A (recon 2026-07-15).** Anclas REALES (Cluster A desplazó ~70 líneas respecto de cuando se escribió el plan): la rama pdf-digital de `ejecutar` está en **`core/sala_maquina.py:414-422`** (`_escribir_md` L420, `continue` L422), NO en 344-347; `_ocr_y_extraer` está en **L347-386** e incluye ahora el **rescate por visión si el OCR falla** (L357-370) y el manejo `PriorOcrFound` (L375). **NO inlinees `ocr_pdf` en `ejecutar`** (perderías ese rescate). En su lugar:

**(a)** Cambia `_ocr_y_extraer` para que DEVUELVA `list[DocCobertura]` y termine delegando en `_split_o_md` sobre el `buscable` que ya produjo. Conserva íntegro el camino de rescate (que ahora devuelve una lista de un elemento):

```python
def _ocr_y_extraer(case_dir, sm_dir, case_id, d, entrada, vision) -> list[DocCobertura]:
    ocr_out = destino_seguro(sm_dir / "01_OCR" / f"{d.slug}.pdf", case_dir)
    try:
        buscable = ocr_pdf(entrada, ocr_out)
    except Exception as e:                    # OCRError: cifrado/corrupto/firmado
        nota = f"OCR falló: {e}"
        if not vision:
            return [DocCobertura(d.slug, d.rel_path, "ocr", "empty", 0, True, nota, d.sha256,
                                 parent_sha256=d.sha256)]
        # rescate por visión (Cluster A): pypdfium2 puede rasterizar lo que OCRmyPDF rechazó
        texto, estado, nota = _reforzar_con_vision(entrada, "", "empty", nota)
        if texto.strip():
            _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, "vision", False, estado)
        return [DocCobertura(d.slug, d.rel_path, "vision", estado, len(texto), False, nota, d.sha256,
                             parent_sha256=d.sha256)]
    persistido = Path(buscable) == ocr_out and ocr_out.exists()
    metodo, ocr = ("ocr", True) if persistido else ("pypdf", False)
    return _split_o_md(case_dir, sm_dir, case_id, d, Path(buscable), metodo, ocr, vision)
```

(El rescate por visión y `PriorOcrFound` quedan idénticos a Cluster A; solo cambia el contrato de retorno a lista y la delegación final en `_split_o_md`. La nota del passthrough `pypdf` "OCRmyPDF no regeneró…" la absorbe `_split_o_md`.)

**(b)** En `ejecutar`, la rama pdf-digital (L414-422) llama a `_split_o_md` sobre `src`; las ramas escaneado (L424) e imagen (L437) usan `.extend(...)` porque `_ocr_y_extraer` ya devuelve lista:

```python
            if d.ruta == "pdf":
                texto = _try_pypdf(src) or ""
                npags = _pdf_num_paginas(src)
                if texto and _texto_suficiente(texto, npags):
                    cobertura.extend(_split_o_md(case_dir, sm_dir, case_id, d, src, "pypdf", False, vision))
                    continue
                cobertura.extend(_ocr_y_extraer(case_dir, sm_dir, case_id, d, src, vision))
            elif d.ruta == "imagen":
                # ... conversión a PDF intermedio igual que hoy, pero:
                cobertura.extend(_ocr_y_extraer(case_dir, sm_dir, case_id, d, intermedio, vision))
```

> **Regla dura de reconciliación al rebasar:** si Cluster A hubiera tocado más el interior de `_ocr_y_extraer`, mantén su lógica y aplica SOLO el cambio de contrato (retorno `list[DocCobertura]` + delegación en `_split_o_md`). El split va sobre el `buscable`, **después** del rescate por visión de OCR y **antes** del MD. Cambiar `append`→`extend` en las ramas escaneado/imagen es obligatorio (si no, `TypeError`/lista anidada).

- [ ] **Step 5: Ejecutar para verlo pasar**

Run: `python -m pytest tests/test_split_sala_maquina_e2e.py -v --runslow`
Expected: PASS (3 MD, 3 PDF en 02_Documentos, 3 filas con parent_slug).

- [ ] **Step 6: Commit**

```bash
git add core/sala_maquina.py tests/test_split_sala_maquina_e2e.py
git commit -m "feat(sala_maquina): split del bundle entre OCR y MD (N MD por documento lógico)"
```

---

## Task 13: Cobertura por documento lógico + `plan` reporta manifiestos

**Files:**
- Modify: `core/sala_maquina.py` (`render_cobertura`)
- Modify: `scripts/sala_maquina.py` (`plan`, `apply`)
- Test: `tests/test_split_documental.py` (render) + reuso E2E

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_split_documental.py`:

```python
def test_render_cobertura_incluye_columnas_de_segmento():
    from core.sala_maquina import DocCobertura, render_cobertura
    filas = [DocCobertura("bundle__seg01_cedula__ab", "01_Drive EV/b.pdf", "pypdf", "ok",
                          120, False, "", "ab" * 32, parent_slug="bundle", role="documento",
                          paginas="1-4", tipo="CEDULA_EMPLAZAMIENTO")]
    out = render_cobertura(filas)
    assert "parent" in out.lower()
    assert "1-4" in out
    assert "CEDULA_EMPLAZAMIENTO" in out
```

- [ ] **Step 2: Ejecutar para verlo fallar**

Run: `python -m pytest tests/test_split_documental.py::test_render_cobertura_incluye_columnas_de_segmento -v`
Expected: FAIL (las columnas nuevas no están en la tabla).

- [ ] **Step 3: Ampliar `render_cobertura`**

En `core/sala_maquina.py`, en `render_cobertura`, cambiar la cabecera y la fila para incluir `parent`/`páginas`/`tipo`:

```python
        "| documento | origen | tipo | páginas | parent | método | estado | chars | ocr | nota |",
        "|---|---|---|---|---|---|---|---|---|---|",
```

y la fila:

```python
        lineas.append(
            f"| {_celda(d.slug)} | {_celda(d.rel_path)} | {_celda(d.tipo)} | {_celda(d.paginas)} | "
            f"{_celda(d.parent_slug)} | {d.metodo} | {d.estado} | {d.chars} | "
            f"{'sí' if d.ocr else '—'} | {_celda(d.nota)} |"
        )
```

> Reconciliación con Cluster A: si Cluster A cambió el formato de la tabla (cobertura acumulativa), añade estas columnas a SU tabla, no dupliques.

- [ ] **Step 4: Ejecutar para verlo pasar**

Run: `python -m pytest tests/test_split_documental.py::test_render_cobertura_incluye_columnas_de_segmento -v`
Expected: PASS.

- [ ] **Step 5: Reportar manifiestos en `plan` (CLI)**

En `scripts/sala_maquina.py`, en el comando `plan`, tras listar los contadores, añadir un pre-cómputo de segmentación por PDF nuevo para avisar de bundles multi-segmento (sin escribir nada aún salvo el manifiesto propuesto, que es el gate editable):

```python
    # Pre-detección de bundles (Preview del split): informa y deja el manifiesto editable.
    from core import split_documental as split
    from core.sala_maquina import _sala_maquina_dir, destino_seguro
    sm_dir = _sala_maquina_dir(case_dir)
    for d in nuevos:
        if d.ruta != "pdf":
            continue
        src = case_dir / "00_Input" / d.rel_path
        try:
            segmentos, blancos = split.detectar(src)
        except Exception:
            continue
        if len(segmentos) > 1:
            carpeta = destino_seguro(sm_dir / "02_Documentos" / d.slug, case_dir)
            if not split.manifiesto_existe(carpeta):
                split.escribir_manifiesto(carpeta, split.construir_manifiesto(
                    d.rel_path, d.sha256, segmentos, blancos))
            typer.echo(f"  bundle {d.rel_path}: {len(segmentos)} documentos → revisa "
                       f"{carpeta / '_segmentacion.md'} y ajusta antes de apply")
```

> Nota: en `plan`, `split.detectar` corre sobre el PDF de `00_Input` solo si ya tiene capa de texto; para escaneados sin OCR aún, el manifiesto se computa en `apply` (tras OCR). Documentar esta asimetría en el `SKILL.md` (Task 15). El gate sigue vigente: `apply` respeta el manifiesto si existe (Task 12) y solo lo crea si falta.

- [ ] **Step 6: Commit**

```bash
git add core/sala_maquina.py scripts/sala_maquina.py tests/test_split_documental.py
git commit -m "feat(sala_maquina): cobertura por documento lógico + plan avisa de bundles"
```

---

## Task 13B: Re-clave de `fusionar_cobertura` + estado idempotente por bundle (documento lógico)

> **Defecto detectado en la validación (recon 2026-07-15), NO presente en el plan original.** La migración a documento lógico dejó la DEDUP de cobertura y el ESTADO idempotente clavados al fichero FÍSICO. Sin esta tarea: (1) `fusionar_cobertura` indexa por `rel_path` (`core/sala_maquina.py:176`) → los N segmentos de un bundle comparten `rel_path` → **colapsan a 1 fila, perdiendo N-1 en silencio** (verificado: con `previa=[]` y 3 segmentos devuelve 1). El E2E de la Task 12 NO lo detecta porque llama a `ejecutar` directo, sin pasar por `fusionar_cobertura` (que sí corre en el `apply` del CLI). (2) El estado se marca por `c.sha256`, que en un segmento es el `seg_sha256`, no el sha físico que `plan()` usa para el *skip* → el bundle **se re-parte en cada corrida** y podría marcarse "hecho" con un segmento fallido.

**Files:**
- Modify: `core/sala_maquina.py` (`fusionar_cobertura` + su docstring)
- Modify: `scripts/sala_maquina.py` (`apply` y `reforzar`: estado agrupado por bundle)
- Test: `tests/test_sala_maquina.py` (fusión) + `tests/test_split_sala_maquina_e2e.py` (idempotencia)

- [ ] **Step 1: Test que falla — la fusión conserva los N segmentos de un bundle**

Añadir a `tests/test_sala_maquina.py`:

```python
def test_fusionar_cobertura_conserva_n_segmentos_mismo_bundle():
    # 3 segmentos del MISMO bundle (mismo rel_path) con slug propio NO deben colapsar.
    from core.sala_maquina import DocCobertura, fusionar_cobertura
    segs = [DocCobertura(f"b__seg{i:02d}_X__{i:08x}", "01_Drive EV/b.pdf", "pypdf", "ok",
                         100, False, "", f"{i:064x}", parent_sha256="B" * 64, parent_slug="b")
            for i in (1, 2, 3)]
    out = fusionar_cobertura([], segs)
    assert len(out) == 3   # hoy colapsa a 1 (indexado solo por rel_path)
```

- [ ] **Step 2: Ejecutar para verlo fallar**

Run: `python -m pytest tests/test_sala_maquina.py -k conserva_n_segmentos -v`
Expected: FAIL (devuelve 1 fila).

- [ ] **Step 3: Re-clavar `fusionar_cobertura` a `(rel_path, slug)`**

En `core/sala_maquina.py`, cambiar el índice de `rel_path` a la clave compuesta `(rel_path, slug)`: el `slug` es único por documento lógico (segmento), y `rel_path` sigue distinguiendo dos ficheros físicos byte-idénticos con igual slug. Reemplazar el cuerpo de `fusionar_cobertura`:

```python
    por_clave = {(d.rel_path, d.slug): d for d in nueva}
    vistos: set[tuple[str, str]] = set()
    out: list[DocCobertura] = []
    for d in previa:
        clave = (d.rel_path, d.slug)
        out.append(por_clave.get(clave, d))
        vistos.add(clave)
    for d in nueva:
        clave = (d.rel_path, d.slug)
        if clave not in vistos:
            out.append(d)
            vistos.add(clave)
    return out
```

Actualizar la docstring: la clave de fusión pasa a `(rel_path, slug)`; explicar que (a) dos ficheros byte-idénticos con igual slug en carpetas distintas siguen siendo 2 filas (distinto `rel_path`), y (b) N segmentos de un bundle son N filas (mismo `rel_path`, distinto `slug`).

- [ ] **Step 4: Ejecutar — nuevo test pasa y el existente sigue verde**

Run: `python -m pytest tests/test_sala_maquina.py -k "conserva_n_segmentos or conserva_dos_rutas" -v`
Expected: PASS ambos. El existente `test_fusionar_cobertura_conserva_dos_rutas_mismo_slug` (misma slug, distinto `rel_path`) lo respeta la nueva clave.

- [ ] **Step 5: Estado idempotente por bundle (solo si TODOS los segmentos salen ok/low)**

En `scripts/sala_maquina.py`, `apply` marca hoy `exitosos = {c.sha256 for c in cob_delta if c.estado in ("ok","low")}` (L124). Con split, `c.sha256` de un segmento es el `seg_sha256`, no el sha físico que `plan()` usa para el *skip* → el bundle no se marcaría nunca (re-split en cada corrida), y un bundle con un segmento fallido no debe marcarse hecho. Agrupar por sha FÍSICO (`parent_sha256`, con fallback a `sha256` para filas no-split) y marcar hecho solo si TODOS sus documentos lógicos salieron `ok`/`low`:

```python
    from collections import defaultdict
    por_fisico: dict[str, list] = defaultdict(list)
    for c in cob_delta:
        por_fisico[c.parent_sha256 or c.sha256].append(c)
    exitosos = {sha for sha, filas in por_fisico.items()
                if all(f.estado in ("ok", "low") for f in filas)}
```

Reemplaza la línea de `exitosos` en `apply` (L124) y aplica el MISMO patrón en `reforzar` (L180). El resto (`procesados = exitosos if force else _estado_previo(case_dir) | exitosos`) no cambia. (Para filas no-split —nativo, imagen, passthrough— `parent_sha256` vale `""` o `d.sha256`; el fallback `or c.sha256` las agrupa por su propio sha físico, idéntico al comportamiento actual.)

- [ ] **Step 6: Test E2E — el segmento lleva el sha físico del bundle y el skip lo respeta**

Añadir a `tests/test_split_sala_maquina_e2e.py`:

```python
def test_segmento_lleva_sha_fisico_y_skip_lo_respeta(tmp_path, monkeypatch):
    import core.config as config
    from core import sala_maquina as sm
    case_dir = tmp_path / "W-TEST03"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    _bundle_digital(case_dir)
    monkeypatch.setattr(config, "caso_path", lambda cid: case_dir)
    inv = sm.inventariar(case_dir)
    bundle_sha = inv[0]["sha256"]
    cob = sm.ejecutar(case_dir, sm.plan(inv, set()), case_id="W-TEST03")
    # cada segmento apunta al sha FÍSICO del bundle (clave del estado)
    assert [c.parent_sha256 for c in cob if c.parent_slug] == [bundle_sha] * 3
    # con ese sha en estado_previo, el bundle se salta ENTERO (no se re-parte)
    assert all(d.skip for d in sm.plan(inv, {bundle_sha}))
```

- [ ] **Step 7: Commit**

```bash
git add core/sala_maquina.py scripts/sala_maquina.py tests/test_sala_maquina.py tests/test_split_sala_maquina_e2e.py
git commit -m "fix(sala_maquina): cobertura y estado por documento lógico (no colapsar segmentos)"
```

> **Deferido consciente (D7 de la validación):** `reforzar` selecciona objetivos por `rel_path` (`scripts:157-158`), así que un solo segmento dudoso re-procesa el bundle entero. Es *correcto* (re-detecta y re-escribe), solo subóptimo. Refinarlo a granularidad de segmento queda como follow-on (nota en Task 15 → `docs/MEJORAS_FUTURAS.md`).

---

## Task 14: `--force` re-computa el manifiesto; sin `--force` respeta el editado

**Files:**
- Modify: `scripts/sala_maquina.py` (`apply` pasa `force` al camino de split) + `core/sala_maquina.py` (`_split_o_md` acepta `force`)
- Test: `tests/test_split_sala_maquina_e2e.py`

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_split_sala_maquina_e2e.py`:

```python
def test_manifiesto_editado_se_respeta(tmp_path, monkeypatch):
    import core.config as config
    from core import sala_maquina as sm, split_documental as split
    case_dir = tmp_path / "W-TEST02"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    _bundle_digital(case_dir)
    monkeypatch.setattr(config, "caso_path", lambda cid: case_dir)

    docs = sm.plan(sm.inventariar(case_dir), set())
    d = next(x for x in docs if x.ruta == "pdf")
    carpeta = case_dir / "01_Procesado" / "02_Sala de máquina" / "02_Documentos" / d.slug
    carpeta.mkdir(parents=True)
    # Manifiesto editado a mano: FUSIONA los 3 en 2 (letrado juntó cédula+auto).
    split.escribir_manifiesto(carpeta, {
        "fuente": d.rel_path, "bundle_sha256": d.sha256,
        "segmentos": [{"seg": 1, "pp": "1-3", "tipo": "EXPEDIENTE", "role": "documento"},
                      {"seg": 2, "pp": "5-5", "tipo": "DOC_FACTURA", "role": "documento"}],
        "delimitadores": [4]})
    cob = sm.ejecutar(case_dir, docs, case_id="W-TEST02")
    seg_rows = [c for c in cob if c.parent_slug]
    assert len(seg_rows) == 2   # respeta la fusión del letrado, no re-detecta 3
```

- [ ] **Step 2: Ejecutar para verlo fallar/pasar**

Run: `python -m pytest tests/test_split_sala_maquina_e2e.py::test_manifiesto_editado_se_respeta -v --runslow`
Expected: PASS si la Task 12 ya lee el manifiesto existente. Si FALLA (re-detecta 3), corregir `_split_o_md` para que priorice `leer_manifiesto` cuando `manifiesto_existe` (ya está así en Task 12 Step 4) — verificar que la validación no lo pisa.

- [ ] **Step 3: Cablear `force` en el camino de split (regenerar manifiesto)**

En `core/sala_maquina.py`, `ejecutar` ya recibe (de Cluster A) o recibe aquí el flag; propaga `force` a `_split_o_md` y, si `force`, ignora el manifiesto en disco:

```python
def _split_o_md(..., vision: bool, force: bool = False) -> list[DocCobertura]:
    ...
    usar_previo = split.manifiesto_existe(carpeta_bundle) and not force
    manifiesto = (split.leer_manifiesto(carpeta_bundle) if usar_previo
                  else split.construir_manifiesto(d.rel_path, d.sha256, segmentos, blancos))
    ...
    if not usar_previo:
        split.escribir_manifiesto(carpeta_bundle, manifiesto)
```

Y en la firma de `ejecutar`, aceptar y pasar `force` (si Cluster A no lo añadió ya): `ejecutar(case_dir, docs, *, case_id, vision=False, force=False)` → pasar `force` a `_split_o_md`. En `scripts/sala_maquina.apply`, pasar `force=force` a `sm.ejecutar`.

- [ ] **Step 4: Ejecutar la suite E2E completa**

Run: `python -m pytest tests/test_split_sala_maquina_e2e.py -v --runslow`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py scripts/sala_maquina.py tests/test_split_sala_maquina_e2e.py
git commit -m "feat(sala_maquina): --force regenera manifiesto; sin force respeta el editado"
```

---

## Task 15: Doc de la skill + nota en PLAN.md

**Files:**
- Modify: `.claude/skills/organizar-sala-maquina/SKILL.md` (documentar el split + el gate del manifiesto)
- Modify: `docs/MEJORAS_FUTURAS.md` (marcar merge N→1 y consumo sala-lectura como follow-on) + `PLAN.md`

- [ ] **Step 1: Documentar el split en `SKILL.md`**

Añadir una sección al `SKILL.md` de `organizar-sala-maquina` explicando: (a) los bundles multi-documento se parten por hoja en blanco antes del MD; (b) `plan` propone un `_segmentacion.md` editable por bundle; (c) el letrado ajusta (fusionar/mover límite/re-etiquetar) y `apply` corta; (d) los segmentos aterrizan en `02_Documentos/{bundle}/` y cada uno tiene su MD; (e) el consumo por `organizar-sala-lectura` (como documento compuesto) es follow-on. Copiar el árbol de §7.2 del spec.

- [ ] **Step 2: Actualizar backlog + plan**

En `docs/MEJORAS_FUTURAS.md` añadir dos entradas de follow-on (merge N→1 en apply + auto-detección `conjunto_detector`; consumo por `organizar-sala-lectura` de documentos lógicos). En `PLAN.md`, marcar el punto del split como en curso/hecho con referencia a este plan y al spec.

- [ ] **Step 3: Verificación final**

Run: `python -m pytest -q`
Expected: suite verde (nº ≥ el de partida; explicar cualquier diferencia en STATUS.md al cerrar).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/organizar-sala-maquina/SKILL.md docs/MEJORAS_FUTURAS.md PLAN.md
git commit -m "docs(split): documentar split en SKILL + follow-ons en backlog"
```

- [ ] **Step 5: Empaquetar la skill (si procede) + abrir PR de F2**

`python scripts/package_skill.py organizar-sala-maquina` (re-import en el servidor Cowork es manual). Abrir PR de F2; debe pasar `leak-scan`.

---

## Self-Review (cobertura del spec)

- **§3 modelo de doc lógico** → Tasks 4, 10 (DocLogico, destinos passthrough/split; merge diferido merge-ready por `fuentes`/`role`).
- **§4 detección (blanco primario, marcadores clasificador/fallback, tipos_extra fuera de core/anon)** → Tasks 2, 3, 5, 6, 7, 8.
- **§5 manifiesto editable** → Tasks 9, 13, 14.
- **§6 placement OCR→split→MD** → Task 12.
- **§7 layout (02_Documentos subcarpeta por bundle; passthrough fuera)** → Tasks 10, 12.
- **§8 contratos de datos (MD, cobertura por doc lógico, indice.json, evento log)** → Tasks 10, 11, 12, 13, **13B** (dedup por doc lógico).
- **§9 contrato de salida para sala de lectura** → Task 15 (documentado; consumo = follow-on).
- **§10 idempotencia / manifiesto respetado / guard 00_Input** → Tasks 12, **13B** (estado por bundle), 14 (`destino_seguro`).
- **§11 errores (aislamiento por bundle, validación de manifiesto, imagen-only no descartada)** → Tasks 9 (validar), 12 (try/except heredado de `ejecutar`), 8/detectar.
- **§12 composición con Cluster A** → gate de fase F2 + notas de reconciliación por tarea.
- **§14/§15 fases y tests** → estructura F1/F2 + tests por tarea.
- **Regla de oro core/anon** → Task 2/3 (param aditivo) + test de identidad `tipos_extra=None`.
- **Validación contra `main` (2026-07-15)** → correcciones D1–D5 + D7 incorporadas (ver "Validación contra `main`" arriba); F1 verificada construíble tal cual, F2 desbloqueada (Cluster A en `main`, `24e69db`).
