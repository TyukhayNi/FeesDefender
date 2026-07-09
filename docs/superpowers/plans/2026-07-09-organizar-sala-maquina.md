# organizar-sala-maquina — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la skill `organizar-sala-maquina`: un orquestador lean que convierte el crudo de `00_Input/` en la Sala de máquina (`01_Procesado/02_Sala de máquina/{01_OCR, 03_MD, raw_text}`) con OCR persistido (OCRmyPDF), MD legible, red de seguridad de calidad y `_cobertura.md`, sin usar el `pipeline.run()` viciado.

**Architecture:** Cerebro puro en `core/sala_maquina.py` (routing, `plan`, `ocr_quality`, `render_cobertura`, guard) + orquestador de I/O `ejecutar()` que reutiliza `anon.ocr.ocr_pdf` (OCRmyPDF, sin tope de páginas) y los helpers deterministas SANOS de `extractor` (`_try_pypdf`, `_texto_suficiente`, nativos) — NUNCA `pipeline.run` ni la rama Docling/30 pp. CLI Typer `scripts/sala_maquina.py` (plan/dry-run/apply, Preview→Apply). Skill `.claude/skills/organizar-sala-maquina/` que dispara y sugiere `organizar-sala-lectura`.

**Tech Stack:** Python 3, pytest, OCRmyPDF 17.4.1 + Tesseract 5.4 (`spa/cat/rus`) + Ghostscript 10 (ya instalados), pypdf, Typer. Windows/PowerShell + venv en `C:\Users\tnm33\Dev\FeesDefender\.venv`.

**Spec:** `docs/superpowers/specs/2026-07-09-organizar-sala-maquina-design.md`.

**Worktree:** `C:\Users\tnm33\Dev\fd-sala-maquina` (rama `feat/organizar-sala-maquina`). Todo comando corre con el venv del repo principal: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe`.

---

## File Structure

- **Create** `core/sala_maquina.py` — cerebro puro (dataclasses `DocPlan`/`DocCobertura`, `clasificar_ruta`, `ocr_quality`, `_ratio_gibberish`, `plan`, `render_cobertura`, `destino_seguro`) + orquestador `ejecutar()` (I/O acotado a OCR/extracción) + helpers de listado `inventariar()`.
- **Modify** `core/intake_log.py:42` — añadir el evento `procesado_sala_maquina` a `INTAKE_EVENTS`.
- **Create** `scripts/sala_maquina.py` — CLI Typer (`plan`/`apply`, `--dry-run`, `--vision`, `--force`).
- **Create** `.claude/skills/organizar-sala-maquina/SKILL.md` + `CHANGELOG.md` (+ helpers `_shared` sincronizados).
- **Create tests** `tests/test_sala_maquina.py` (unit puro) y `tests/test_sala_maquina_ejecutar.py` (integración).

**Convenciones ancladas al código (no reinventar):**
- `core/utils.py`: `output_slug(rel_path, sha256)` → `slug__sha8`; `file_sha256(path)`; `text_sha256(text)`; `write_md(path, meta, body)`; `now_iso()`.
- `core/anon/ocr.py`: `ocr_pdf(entrada, salida, *, idiomas="spa+cat+rus", ...)` → devuelve `salida` si OCR-izó, `entrada` si ya tenía texto; `ocr_disponible()`. (Bug #11 YA resuelto.)
- `core/extractor.py`: `_try_pypdf(path)`, `_pdf_num_paginas(path)`, `_texto_suficiente(text, n_pags)`, `_try_email`, `_try_rtf`, `_try_ics`, `_try_pandas_table`, `_try_docx`, `_read_text_file`. **NO** usar `_extract_one` (embebe Docling/30 pp).
- `core/config.py`: `caso_path(case_id)` → raíz del caso.
- `core/intake_log.py`: `append_event(case_id, event, *, details)`.

---

## FASE F1 — Walking skeleton (cerebro puro + PDF de punta a punta + CLI)

### Task 1: Scaffold del cerebro + routing por extensión

**Files:**
- Create: `core/sala_maquina.py`
- Test: `tests/test_sala_maquina.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sala_maquina.py
from core import sala_maquina as sm


def test_clasificar_ruta_por_extension():
    assert sm.clasificar_ruta(".pdf") == "pdf"
    assert sm.clasificar_ruta(".PDF") == "pdf"
    assert sm.clasificar_ruta(".jpg") == "imagen"
    assert sm.clasificar_ruta(".heic") == "imagen"
    assert sm.clasificar_ruta(".eml") == "nativo"
    assert sm.clasificar_ruta(".txt") == "nativo"
    assert sm.clasificar_ruta(".docx") == "nativo"
    assert sm.clasificar_ruta(".mp4") == "sin_soporte"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py::test_clasificar_ruta_por_extension -v`
Expected: FAIL (`ModuleNotFoundError` o `AttributeError: clasificar_ruta`).

- [ ] **Step 3: Write minimal implementation**

```python
# core/sala_maquina.py
"""Cerebro + orquestador de la Sala de máquina (skill organizar-sala-maquina).

Convierte el crudo de 00_Input/ en 01_Procesado/02_Sala de máquina/:
  01_OCR/     PDFs buscables (OCRmyPDF)   03_MD/  markdown legible   raw_text/  intermedio

NO usa pipeline.run() ni la rama Docling/30pp de extractor. OCR aguas arriba con
OCRmyPDF (sin tope de páginas); reutiliza solo los helpers deterministas sanos del
extractor. Ver docs/superpowers/specs/2026-07-09-organizar-sala-maquina-design.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_EXTS_IMAGEN = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic", ".heif", ".webp", ".bmp", ".gif"}
_EXTS_NATIVO = {".eml", ".txt", ".md", ".rtf", ".ics", ".csv", ".xlsx", ".xls", ".docx", ".html", ".htm"}


def clasificar_ruta(ext: str) -> str:
    """Enruta por extensión: 'pdf' | 'imagen' | 'nativo' | 'sin_soporte'."""
    e = ext.lower()
    if e == ".pdf":
        return "pdf"
    if e in _EXTS_IMAGEN:
        return "imagen"
    if e in _EXTS_NATIVO:
        return "nativo"
    return "sin_soporte"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py::test_clasificar_ruta_por_extension -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/tnm33/Dev/fd-sala-maquina"
git add core/sala_maquina.py tests/test_sala_maquina.py
git commit -m "feat(sala-maquina): routing por extension (cerebro puro)"
```

---

### Task 2: Red de seguridad de calidad — `ocr_quality`

**Files:**
- Modify: `core/sala_maquina.py`
- Test: `tests/test_sala_maquina.py`

- [ ] **Step 1: Write the failing test**

```python
def test_ocr_quality_texto_limpio_es_ok():
    texto = ("El arrendatario reclama la devolución de los honorarios de "
             "intermediación conforme al artículo veinte de la Ley de "
             "Arrendamientos Urbanos. " * 5)
    estado, motivo = sm.ocr_quality(texto, n_pags=1)
    assert estado == "ok"
    assert motivo == ""


def test_ocr_quality_vacio_es_empty():
    estado, _ = sm.ocr_quality("   ", n_pags=3)
    assert estado == "empty"


def test_ocr_quality_gibberish_es_low():
    # Muchos chars, pero tokens sin vocales / no léxicos (OCR ruidoso).
    basura = "xkq zzt brrr wgh nkk xcv " * 40
    estado, motivo = sm.ocr_quality(basura, n_pags=1)
    assert estado == "low"
    assert "gibberish" in motivo


def test_ocr_quality_baja_densidad_es_low():
    # Texto legible pero muy poco para 10 páginas (escaneado semivacío).
    estado, _ = sm.ocr_quality("Firmado en Barcelona. Conforme.", n_pags=10)
    assert estado == "low"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py -k ocr_quality -v`
Expected: FAIL (`AttributeError: ocr_quality`).

- [ ] **Step 3: Write minimal implementation**

```python
import re

_MIN_CHARS = 40                 # < esto para el documento entero = empty
_MIN_DENSIDAD = 40              # char/pág mínima (alineado con extractor._texto_suficiente)
_MAX_GIBBERISH = 0.40           # > 40% de tokens sin vocal = OCR ruidoso
_TOKEN_RE = re.compile(r"[^\W\d_]{2,}", re.UNICODE)   # tokens alfabéticos (incl. tildes/cirílico)
_VOCALES = set("aeiouáéíóúàèìòùüïAEIOUÁÉÍÓÚÀÈÌÒÙÜÏаэеёиоуыюяАЭЕЁИОУЫЮЯ")


def _ratio_gibberish(text: str) -> float:
    """Fracción de tokens alfabéticos (≥2 letras) que NO tienen ninguna vocal.

    Un OCR ruidoso produce tiras consonánticas ('xkq', 'brrr'); las palabras
    reales en spa/cat/rus casi siempre llevan vocal. 0.0 si no hay tokens.
    """
    tokens = _TOKEN_RE.findall(text)
    if not tokens:
        return 1.0
    sin_vocal = sum(1 for t in tokens if not (set(t) & _VOCALES))
    return sin_vocal / len(tokens)


def ocr_quality(text: str, n_pags: int | None) -> tuple[str, str]:
    """Estado de calidad del texto extraído: ('ok'|'low'|'empty', motivo).

    Tres señales (spec §5.2): densidad char/pág, ratio de gibberish, léxico.
    No aborta: solo clasifica para la worklist de revisión humana.
    """
    t = (text or "").strip()
    if len(t) < _MIN_CHARS:
        return "empty", "sin texto o residual"
    gib = _ratio_gibberish(t)
    if gib > _MAX_GIBBERISH:
        return "low", f"gibberish {gib:.0%} (OCR ruidoso o idioma no soportado)"
    if n_pags and n_pags > 0 and (len(t) / n_pags) < _MIN_DENSIDAD:
        return "low", f"densidad baja ({len(t) // max(n_pags,1)} char/pág)"
    return "ok", ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py -k ocr_quality -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py tests/test_sala_maquina.py
git commit -m "feat(sala-maquina): red de calidad ocr_quality (densidad+gibberish+lexico)"
```

---

### Task 3: Modelos de datos + `plan()` (puro, con skip incremental)

**Files:**
- Modify: `core/sala_maquina.py`
- Test: `tests/test_sala_maquina.py`

- [ ] **Step 1: Write the failing test**

```python
def test_plan_enruta_y_marca_skip():
    inventario = [
        {"rel_path": "01_Drive EV/encargo.pdf", "sha256": "aaaa1111", "ext": ".pdf"},
        {"rel_path": "03_Email/hilo.eml", "sha256": "bbbb2222", "ext": ".eml"},
        {"rel_path": "01_Drive EV/foto.heic", "sha256": "cccc3333", "ext": ".heic"},
        {"rel_path": "01_Drive EV/video.mp4", "sha256": "dddd4444", "ext": ".mp4"},
    ]
    plan = sm.plan(inventario, estado_previo={"bbbb2222"})
    by_sha = {d.sha256: d for d in plan}
    assert by_sha["aaaa1111"].ruta == "pdf"
    assert by_sha["aaaa1111"].slug == "encargo__aaaa1111"
    assert by_sha["bbbb2222"].skip is True          # ya procesado
    assert by_sha["cccc3333"].ruta == "imagen"
    assert by_sha["dddd4444"].ruta == "sin_soporte"
    assert by_sha["aaaa1111"].skip is False


def test_plan_excluye_90_notas_personales():
    inventario = [
        {"rel_path": "90_Notas personales/borrador.pdf", "sha256": "e1", "ext": ".pdf"},
        {"rel_path": "01_Drive EV/ok.pdf", "sha256": "e2", "ext": ".pdf"},
    ]
    plan = sm.plan(inventario, estado_previo=set())
    assert [d.sha256 for d in plan] == ["e2"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py -k plan -v`
Expected: FAIL (`AttributeError: plan` / `DocPlan`).

- [ ] **Step 3: Write minimal implementation**

```python
from core.utils import output_slug

_EXCLUIR_PREFIJOS = ("90_Notas personales/", "90_Notas personales\\")


@dataclass
class DocPlan:
    rel_path: str
    sha256: str
    ext: str
    ruta: str            # pdf | imagen | nativo | sin_soporte
    slug: str            # output_slug (slug__sha8)
    skip: bool = False


@dataclass
class DocCobertura:
    slug: str
    rel_path: str
    metodo: str          # pypdf | ocr | nativo | sin_soporte
    estado: str          # ok | low | empty | sin_texto | sin_soporte
    chars: int = 0
    ocr: bool = False
    nota: str = ""


def plan(inventario: list[dict], estado_previo: set[str]) -> list[DocPlan]:
    """Puro: enruta cada fichero y marca skip si su sha ya fue procesado.

    Excluye 90_Notas personales/ (zona del abogado, invariante del proyecto).
    """
    out: list[DocPlan] = []
    for f in inventario:
        rel = f["rel_path"]
        if rel.startswith(_EXCLUIR_PREFIJOS):
            continue
        sha = f["sha256"]
        out.append(DocPlan(
            rel_path=rel,
            sha256=sha,
            ext=f["ext"],
            ruta=clasificar_ruta(f["ext"]),
            slug=output_slug(rel, sha),
            skip=sha in estado_previo,
        ))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py -k plan -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py tests/test_sala_maquina.py
git commit -m "feat(sala-maquina): plan() puro con skip incremental y exclusion de notas"
```

---

### Task 4: `render_cobertura()` (puro)

**Files:**
- Modify: `core/sala_maquina.py`
- Test: `tests/test_sala_maquina.py`

- [ ] **Step 1: Write the failing test**

```python
def test_render_cobertura_marca_generado_y_ordena_dudosos_primero():
    cob = [
        sm.DocCobertura(slug="a__1", rel_path="x/a.pdf", metodo="pypdf", estado="ok", chars=1200),
        sm.DocCobertura(slug="b__2", rel_path="x/b.pdf", metodo="ocr", estado="empty",
                        chars=0, ocr=True, nota="sin texto o residual"),
    ]
    md = sm.render_cobertura(cob)
    assert md.startswith("<!-- GENERADO — NO EDITAR A MANO -->")
    # los dudosos (no-ok) van primero para que salten a la vista
    assert md.index("b__2") < md.index("a__1")
    assert "empty" in md and "sin texto" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py -k render_cobertura -v`
Expected: FAIL (`AttributeError: render_cobertura`).

- [ ] **Step 3: Write minimal implementation**

```python
def render_cobertura(cobertura: list[DocCobertura]) -> str:
    """Puro: Markdown de _cobertura.md. Dudosos (estado != ok) primero."""
    orden = {"empty": 0, "sin_texto": 0, "sin_soporte": 1, "low": 2, "ok": 3}
    filas = sorted(cobertura, key=lambda d: (orden.get(d.estado, 0), d.slug))
    lineas = [
        "<!-- GENERADO — NO EDITAR A MANO -->",
        "# Cobertura de la Sala de máquina",
        "",
        "| documento | origen | método | estado | chars | ocr | nota |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in filas:
        lineas.append(
            f"| {d.slug} | {d.rel_path} | {d.metodo} | {d.estado} | "
            f"{d.chars} | {'sí' if d.ocr else '—'} | {d.nota} |"
        )
    dudosos = [d for d in filas if d.estado != "ok"]
    lineas += ["", f"**{len(dudosos)} de {len(filas)} documentos requieren tu revisión.**", ""]
    return "\n".join(lineas) + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py -k render_cobertura -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py tests/test_sala_maquina.py
git commit -m "feat(sala-maquina): render_cobertura() puro (worklist de revision)"
```

---

### Task 5: Guard `destino_seguro()` — invariante `00_Input` intocable

**Files:**
- Modify: `core/sala_maquina.py`
- Test: `tests/test_sala_maquina.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import pytest


def test_destino_seguro_rechaza_00_input_y_notas():
    case = Path("C:/casos/EV-2026-001")
    with pytest.raises(ValueError):
        sm.destino_seguro(case / "00_Input" / "x.md", case)
    with pytest.raises(ValueError):
        sm.destino_seguro(case / "90_Notas personales" / "x.md", case)


def test_destino_seguro_admite_sala_maquina():
    case = Path("C:/casos/EV-2026-001")
    dst = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / "x.md"
    assert sm.destino_seguro(dst, case) == dst
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py -k destino_seguro -v`
Expected: FAIL (`AttributeError: destino_seguro`).

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path

_ZONAS_VETADAS = ("00_Input", "90_Notas personales")


def destino_seguro(dst: Path, case_dir: Path) -> Path:
    """Devuelve dst si es un destino de escritura permitido; si no, ValueError.

    Invariante del proyecto (M5): jamás escribir en 00_Input/ ni en
    90_Notas personales/. Se comprueba por los componentes de la ruta relativa.
    """
    dst = Path(dst)
    try:
        partes = dst.relative_to(case_dir).parts
    except ValueError:
        raise ValueError(f"Destino fuera del caso: {dst}")
    if partes and partes[0] in _ZONAS_VETADAS:
        raise ValueError(f"Destino en zona vetada {partes[0]!r}: {dst}")
    return dst
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py -k destino_seguro -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py tests/test_sala_maquina.py
git commit -m "feat(sala-maquina): guard destino_seguro (00_Input/90_Notas intocables)"
```

---

### Task 6: Registrar el evento de log `procesado_sala_maquina`

**Files:**
- Modify: `core/intake_log.py:42`
- Test: `tests/test_sala_maquina.py`

- [ ] **Step 1: Write the failing test**

```python
from core import intake_log


def test_evento_procesado_sala_maquina_registrado():
    assert "procesado_sala_maquina" in intake_log.INTAKE_EVENTS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py -k procesado_sala_maquina -v`
Expected: FAIL (assert: no está en el frozenset).

- [ ] **Step 3: Write minimal implementation**

En `core/intake_log.py`, dentro del `frozenset` `INTAKE_EVENTS` (tras `"conjunto_detectado", ...`), añadir la línea:

```python
    "procesado_sala_maquina",  # OCR+MD escritos en 01_Procesado/02_Sala de máquina/
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina.py -k procesado_sala_maquina -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/intake_log.py tests/test_sala_maquina.py
git commit -m "feat(sala-maquina): evento de log procesado_sala_maquina"
```

---

### Task 7: `ejecutar()` — orquestador de I/O (rutas PDF: pypdf + OCR)

**Files:**
- Modify: `core/sala_maquina.py`
- Test: `tests/test_sala_maquina_ejecutar.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sala_maquina_ejecutar.py
from pathlib import Path
from core import sala_maquina as sm


def _pdf_con_texto(path: Path):
    """Escribe un PDF mínimo con capa de texto usng reportlab si está; si no, pypdf."""
    from reportlab.pdfgen import canvas          # dep de test (ya en el entorno docling)
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, "Encargo de mediación firmado por el propietario. "
                          "Honorarios de intermediación del cinco por ciento.")
    c.showPage()
    c.save()


def test_ejecutar_pdf_digital_escribe_md_sin_ocr(tmp_path, monkeypatch):
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "encargo.pdf"
    _pdf_con_texto(src)
    sha = sm_file_sha(src)
    # ocr_pdf NO debe llamarse para un PDF digital
    def _boom(*a, **k):
        raise AssertionError("no debe OCR-izar un PDF con capa de texto")
    monkeypatch.setattr(sm, "ocr_pdf", _boom)

    plan = [sm.DocPlan(rel_path="01_Drive EV/encargo.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"encargo__{sha[:8]}")]
    cob = sm.ejecutar(case, plan, case_id="EV-2026-001")

    md = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / f"encargo__{sha[:8]}.md"
    assert md.exists()
    assert "Honorarios" in md.read_text(encoding="utf-8")
    assert cob[0].metodo == "pypdf" and cob[0].estado == "ok" and cob[0].ocr is False


def sm_file_sha(p: Path) -> str:
    from core.utils import file_sha256
    return file_sha256(p)


def test_ejecutar_pdf_escaneado_llama_ocr_y_persiste(tmp_path, monkeypatch):
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "escaneado.pdf"
    src.write_bytes(b"%PDF-1.4\n% escaneado sin capa de texto\n")
    sha = sm_file_sha(src)

    ocr_dir = case / "01_Procesado" / "02_Sala de máquina" / "01_OCR"

    def _fake_ocr(entrada, salida, **k):
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        Path(salida).write_bytes(b"%PDF buscable con texto")
        return Path(salida)

    # pypdf del original = poco texto (escaneado); del PDF buscable = texto útil.
    def _fake_pypdf(path):
        return "Contrato de arras penitenciales entre las partes. " * 4 \
            if "01_OCR" in str(path) else ""

    monkeypatch.setattr(sm, "ocr_pdf", _fake_ocr)
    monkeypatch.setattr(sm, "_try_pypdf", _fake_pypdf)
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)

    plan = [sm.DocPlan(rel_path="01_Drive EV/escaneado.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"escaneado__{sha[:8]}")]
    cob = sm.ejecutar(case, plan, case_id="EV-2026-001")

    assert (ocr_dir / f"escaneado__{sha[:8]}.pdf").exists()   # PDF buscable persistido
    md = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / f"escaneado__{sha[:8]}.md"
    assert "arras" in md.read_text(encoding="utf-8")
    assert cob[0].metodo == "ocr" and cob[0].ocr is True and cob[0].estado == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina_ejecutar.py -v`
Expected: FAIL (`AttributeError: ejecutar`).

- [ ] **Step 3: Write minimal implementation**

```python
# en core/sala_maquina.py — importar los helpers SANOS del extractor y el OCR
from core.extractor import _try_pypdf, _pdf_num_paginas, _texto_suficiente
from core.anon.ocr import ocr_pdf
from core.utils import now_iso, text_sha256, write_md


def _sala_maquina_dir(case_dir: Path) -> Path:
    return case_dir / "01_Procesado" / "02_Sala de máquina"


def _escribir_md(case_dir, case_id, slug, rel_path, texto, metodo, ocr, estado):
    sm_dir = _sala_maquina_dir(case_dir)
    md_path = destino_seguro(sm_dir / "03_MD" / f"{slug}.md", case_dir)
    raw_path = destino_seguro(sm_dir / "raw_text" / f"{slug}.txt", case_dir)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(texto, encoding="utf-8")
    meta = {
        "case_id": case_id, "tipo": "documento_procesado", "fase": "01_Procesado",
        "fecha": now_iso(), "source_path": rel_path, "extractor": metodo,
        "chars": len(texto), "ocr": ocr, "ocr_quality": estado,
        "text_sha256": text_sha256(texto),
    }
    write_md(md_path, meta, texto)


def ejecutar(case_dir: Path, plan: list[DocPlan], *, case_id: str,
             vision: bool = False) -> list[DocCobertura]:
    """Recorre el plan escribiendo 01_OCR/, raw_text/, 03_MD/. Devuelve cobertura.

    Rutas PDF (F1): pypdf si hay capa de texto suficiente; si no, OCRmyPDF →
    PDF buscable persistido en 01_OCR/ → texto del PDF buscable → MD.
    imagen/nativo se implementan en F2 (aquí producen 'sin_soporte' provisional).
    """
    case_dir = Path(case_dir)
    sm_dir = _sala_maquina_dir(case_dir)
    cobertura: list[DocCobertura] = []

    for d in plan:
        if d.skip:
            continue
        src = case_dir / "00_Input" / d.rel_path
        if d.ruta == "pdf":
            texto = _try_pypdf(src) or ""
            npags = _pdf_num_paginas(src)
            if texto and _texto_suficiente(texto, npags):
                estado, nota = ocr_quality(texto, npags)
                _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, "pypdf", False, estado)
                cobertura.append(DocCobertura(d.slug, d.rel_path, "pypdf", estado, len(texto), False, nota))
                continue
            # escaneado → OCRmyPDF (sin tope de páginas)
            ocr_out = destino_seguro(sm_dir / "01_OCR" / f"{d.slug}.pdf", case_dir)
            try:
                buscable = ocr_pdf(src, ocr_out)
            except Exception as e:  # OCRError incl. cifrado/corrupto/firmado
                cobertura.append(DocCobertura(d.slug, d.rel_path, "ocr", "empty", 0, True, f"OCR falló: {e}"))
                continue
            texto = _try_pypdf(buscable) or ""
            estado, nota = ocr_quality(texto, _pdf_num_paginas(buscable))
            _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, "ocr", True, estado)
            cobertura.append(DocCobertura(d.slug, d.rel_path, "ocr", estado, len(texto), True, nota))
        else:
            # imagen/nativo/sin_soporte → F2
            cobertura.append(DocCobertura(d.slug, d.rel_path, "sin_soporte", "sin_soporte", 0, False, "ruta F2"))
    return cobertura
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina_ejecutar.py -v`
Expected: PASS (2 tests). Si `reportlab` no está, instalar en el venv: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pip install reportlab`.

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py tests/test_sala_maquina_ejecutar.py
git commit -m "feat(sala-maquina): ejecutar() rutas PDF (pypdf + OCRmyPDF persistido)"
```

---

### Task 8: CLI `scripts/sala_maquina.py` (Typer, Preview→Apply)

**Files:**
- Create: `scripts/sala_maquina.py`
- Test: `tests/test_sala_maquina_ejecutar.py`

- [ ] **Step 1: Write the failing test**

```python
def test_inventariar_lista_00_input_con_sha(tmp_path):
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    (case / "00_Input" / "01_Drive EV" / "a.pdf").write_bytes(b"%PDF-1.4 x")
    (case / "00_Input" / "_intake_log.jsonl").write_text("{}", encoding="utf-8")  # control: ignorar
    inv = sm.inventariar(case)
    assert len(inv) == 1
    assert inv[0]["rel_path"] == "01_Drive EV/a.pdf"
    assert len(inv[0]["sha256"]) == 64 and inv[0]["ext"] == ".pdf"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina_ejecutar.py -k inventariar -v`
Expected: FAIL (`AttributeError: inventariar`).

- [ ] **Step 3: Write minimal implementation**

En `core/sala_maquina.py`:

```python
from core.utils import file_sha256

_IGNORAR = {"_intake_log.jsonl", "_inventory.json", ".pulled", ".synced"}


def inventariar(case_dir: Path) -> list[dict]:
    """Lista 00_Input/ (recursivo) con sha256 y ext. Ignora ficheros de control.

    NO excluye 90_Notas personales aquí (lo hace plan(), único punto de verdad),
    pero sí los ficheros de control del intake.
    """
    root = Path(case_dir) / "00_Input"
    out: list[dict] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name in _IGNORAR:
            continue
        out.append({
            "rel_path": p.relative_to(root).as_posix(),
            "sha256": file_sha256(p),
            "ext": p.suffix.lower(),
        })
    return out
```

Y crear `scripts/sala_maquina.py`:

```python
"""CLI de la Sala de máquina: OCR+MD de un expediente (skill organizar-sala-maquina).

Uso:
  python -m scripts.sala_maquina plan  "<case_id>"            # solo propuesta
  python -m scripts.sala_maquina apply "<case_id>" [--vision] [--force]
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from core import sala_maquina as sm
from core.config import caso_path
from core.intake_log import append_event

app = typer.Typer(add_completion=False)

_STATE = "_sala_maquina_state.json"


def _estado_previo(case_dir: Path) -> set[str]:
    f = sm._sala_maquina_dir(case_dir) / _STATE
    if not f.exists():
        return set()
    return set(json.loads(f.read_text(encoding="utf-8")).get("procesados", []))


def _guardar_estado(case_dir: Path, shas: set[str]) -> None:
    d = sm._sala_maquina_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / _STATE).write_text(json.dumps({"procesados": sorted(shas)}, ensure_ascii=False, indent=2),
                            encoding="utf-8")


def _construir_plan(case_dir: Path, force: bool):
    previo = set() if force else _estado_previo(case_dir)
    return sm.plan(sm.inventariar(case_dir), previo)


@app.command()
def plan(case_id: str):
    """Muestra la propuesta (Preview) sin escribir nada."""
    case_dir = caso_path(case_id)
    p = _construir_plan(case_dir, force=False)
    nuevos = [d for d in p if not d.skip]
    typer.echo(f"Caso: {case_id}")
    for ruta in ("pdf", "imagen", "nativo", "sin_soporte"):
        n = sum(1 for d in nuevos if d.ruta == ruta)
        if n:
            typer.echo(f"  {ruta}: {n}")
    typer.echo(f"  (saltados por sha ya procesado: {sum(1 for d in p if d.skip)})")


@app.command()
def apply(case_id: str, vision: bool = False, force: bool = False):
    """Ejecuta OCR+MD y escribe la Sala de máquina + cobertura + log."""
    case_dir = caso_path(case_id)
    p = _construir_plan(case_dir, force=force)
    cob = sm.ejecutar(case_dir, p, case_id=case_id, vision=vision)

    sm_dir = sm._sala_maquina_dir(case_dir)
    revisar = case_dir / "01_Procesado" / "_revisar"
    revisar.mkdir(parents=True, exist_ok=True)
    (revisar / "_cobertura.md").write_text(sm.render_cobertura(cob), encoding="utf-8")

    procesados = _estado_previo(case_dir) | {d.sha256 for d in p if not d.skip}
    _guardar_estado(case_dir, procesados)
    append_event(case_id, "procesado_sala_maquina", details={
        "count": len(cob),
        "files": [{"path": c.rel_path, "slug": c.slug, "metodo": c.metodo, "estado": c.estado} for c in cob],
    })
    dudosos = [c for c in cob if c.estado != "ok"]
    typer.echo(f"Sala de máquina actualizada: {len(cob)} documentos, {len(dudosos)} a revisar.")
    typer.echo("Siguiente paso sugerido: organizar-sala-lectura sobre este caso.")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sala_maquina_ejecutar.py -k inventariar -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py scripts/sala_maquina.py tests/test_sala_maquina_ejecutar.py
git commit -m "feat(sala-maquina): CLI Typer plan/apply + inventariar + estado idempotente"
```

---

### Task 9: Walking skeleton E2E sobre un documento real (verificación)

**Files:** ninguno (verificación manual con un PDF real).

- [ ] **Step 1: Confirmar prerequisitos OCR**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -c "from core.anon.ocr import ocr_disponible; print(ocr_disponible())"`
Expected: `True`.

- [ ] **Step 2: Preparar un caso de prueba con UN PDF escaneado real**

Copiar un PDF escaneado corto a `<caso>/00_Input/04_Manual/`. Usar un caso desechable en disco local (no `G:` para el skeleton).

- [ ] **Step 3: Preview**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m scripts.sala_maquina plan "<case_id>"`
Expected: cuenta 1 en `pdf`.

- [ ] **Step 4: Apply y verificar los tres artefactos**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m scripts.sala_maquina apply "<case_id>"`
Expected: existen `01_Procesado/02_Sala de máquina/01_OCR/*.pdf` (buscable), `03_MD/*.md` (con texto real), `raw_text/*.txt`, y `01_Procesado/_revisar/_cobertura.md`. `00_Input/` intacto. Evento en `_intake_log.jsonl`.

- [ ] **Step 5: Verificar idempotencia**

Re-ejecutar `apply`: Expected: 0 nuevos (todo saltado por sha). Confirmar que ningún artefacto cambió de timestamp salvo `_cobertura.md`.

- [ ] **Step 6: Suite completa verde**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_sala_maquina.py tests/test_sala_maquina_ejecutar.py`
Expected: todo PASS. Commit si hubo ajustes.

---

## FASE F2 — Amplitud y robustez

> Mismo patrón TDD que F1 (test que falla → impl mínima → verde → commit). Cada punto es una tarea.

### Task 10: Ruta `nativo` en `ejecutar()`
- Reutilizar los `_try_*` del extractor por extensión: `.eml`→`_try_email`; `.rtf`→`_try_rtf`; `.ics`→`_try_ics`; `.csv/.xlsx/.xls`→`_try_pandas_table`; `.docx`→`_try_docx`; `.txt/.md/.html/.htm`→`_read_text_file`. Escribir MD (método `nativo`, `ocr=False`), sin tocar `01_OCR/`. `ocr_quality` con `n_pags=None`. Test: un `.eml` y un `.txt` producen MD con su texto; `metodo == "nativo"`.

### Task 11: Ruta `imagen`/`.heic` en `ejecutar()`
- `imagen` → convertir a PDF con `core/anon/imagen_a_pdf.convertir(...)` (verificar firma real del módulo antes de codificar), guardar el PDF intermedio y pasarlo por el mismo camino OCR que un escaneado → `01_OCR/`. `.heic` requiere `pillow-heif` (verificar en el venv; si falta, `pip install pillow-heif` y marcar en cobertura `sin_soporte` con nota si no se puede convertir). Test con una imagen PNG pequeña (mock de OCR).

### Task 12: `--vision` (refuerzo opcional, mockeado)
- Para documentos con `estado in {low, empty}` y `vision=True`: renderizar páginas con `pypdfium2` y reforzar el MD con transcripción. La llamada al modelo va tras una función `_transcribir_vision(imgs) -> str` **inyectable** (para mockear en test; sin llamadas reales). Off por defecto. Test: con `--vision` y `_transcribir_vision` mockeado, un doc `empty` mejora a `ok`/`low` y el MD incorpora la transcripción.

### Task 13: Test de guard `00_Input` en `ejecutar()` (integración)
- Verificar que `ejecutar` nunca crea ficheros bajo `00_Input/` ni `90_Notas personales/` (snapshot del árbol de `00_Input` antes/después: sin cambios). Un doc en `90_Notas personales/` que llegara al plan se excluye (ya cubierto en Task 3, aquí se verifica end-to-end).

### Task 14: Corrida real sobre W-02VND1 + métrica "de N a 0"
- Ejecutar `plan`/`apply` sobre el golden fixture W-02VND1 (autorización de Nikolai para tocar `G:`; seguir la regla hidratar→procesar→devolver si aplica). Medir documentos que hoy salen ciegos (`empty`/`low`) vs antes. Registrar el resultado en `STATUS.md` al cerrar. **No** es un test automático.

---

## FASE F3 — Skill + empaquetado

### Task 15: `SKILL.md` desde `_plantilla-skill`
- Copiar `.claude/skills/_shared/_plantilla-skill/` → `.claude/skills/organizar-sala-maquina/`. Frontmatter: `name: organizar-sala-maquina`, `metadata.rol: output`, `naturaleza: atomica`, `version: "1.0"`, `requires: []` (verificación en espíritu vía `_cobertura.md`; NO `pase-de-estilo`). **Descripción disambiguada** (obligatoria para el triggering): qué hace (OCR+MD → Sala de máquina) y qué NO (no organiza la sala de lectura — la SUGIERE; no valora viabilidad; no anonimiza; no da de alta/intake — eso es abrir-caso). Cuerpo: modos de acceso, procedimiento (dispara `scripts.sala_maquina plan`→gate→`apply`), Preview→Apply, gotchas (local-only, OCRmyPDF requerido), y **handoff: sugiere `organizar-sala-lectura`** al terminar. **NO** escribir sección de ecosistema a mano (patrón #50, otra sesión).

### Task 16: Helpers `_shared` + CHANGELOG + validación
- Si la skill usa `registrar_uso`/`registrar_outputs`, sincronizar con `scripts/sync_skill_helpers.py` y verificar `tests/test_skill_helpers_sync.py` verde. Crear `CHANGELOG.md` (v1.0). Correr `scripts/validate_skills.py` y `scripts/check_skills.py` → sin errores.

### Task 17: Empaquetado `.skill`
- `scripts/package_skill.py organizar-sala-maquina` → genera el `.skill`. (Instalación en el servidor Cowork = paso manual de Nikolai; documentar en el reporte.)

### Task 18: Wiring de `PLAN.md` (al abrir el PR)
- Cerrar `[SIGUIENTE-SKILL-EXPEDIENTE-A-MD]`: renombrar la entrada a `organizar-sala-maquina`, marcar `✅` con el hash del PR, puntero al spec. Hacerlo **en el commit del PR** para minimizar solape con la rama `feat/abrir-caso` que también toca `PLAN.md`.

---

## Self-Review (hecho)

- **Cobertura del spec:** §5.1 (no pipeline.run) → Task 7 (`ejecutar` usa `_try_pypdf`+`ocr_pdf`, nunca `_extract_one`). §5.2 (calidad) → Task 2 + Task 4. §4 layout → Task 7 (`_sala_maquina_dir`). §6 pipeline → Tasks 7-8. §7 contratos (evento, frontmatter) → Task 6 + Task 7 (`_escribir_md`). §8 idempotencia → Task 8 (`_sala_maquina_state.json`) + Task 9 step 5. §9 errores → Task 7 (try/except OCRError → `empty`). §10 guard → Task 5 + Task 13. §12 handoff → Task 8 (mensaje) + Task 15. Rutas imagen/nativo/vision → Tasks 10-12.
- **Placeholders:** ninguno en F1 (código completo). F2/F3 a granularidad de tarea con código para lo no-obvio; el ejecutor expande siguiendo el patrón de F1. Dos verificaciones señaladas explícitamente (firma de `imagen_a_pdf.convertir`, `pillow-heif` en venv) — son *comprobaciones*, no huecos de diseño.
- **Consistencia de tipos:** `DocPlan`/`DocCobertura` (Task 3) usados igual en `ejecutar` (Task 7) y `render_cobertura` (Task 4); `ocr_quality` firma `(text, n_pags)->(estado,motivo)` idéntica en Task 2 y su uso en Task 7; `_sala_maquina_dir` y `destino_seguro` compartidos.
