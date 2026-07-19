# Fase 2 de contenido de adjuntos (`core/adjuntos_contenido`) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extraer el contenido (texto fiel + cola de resumen/visión) de cada adjunto único de `01_Procesado/Emails/adjuntos/` a un `<base>.contenido.md`, reutilizando el motor `core.extractor`.

**Architecture:** Módulo delgado `core/adjuntos_contenido/` encadenable tras `email_atomize`. Descubre adjuntos por sus sidecars, enruta por tipo (texto fiel vía `core.extractor._extract_one`; imágenes → cola de visión; no soportados → omitido), renderiza `.contenido.md` con caché incremental por sha256, y deja una capa LLM (resumen/visión) desacoplada que por defecto no llama a nada de pago.

**Tech Stack:** Python 3, pytest, `core.extractor` (pypdf/Docling/pandas/python-docx), `striprtf` (RTF), stdlib (ICS), dataclasses.

---

## Desviaciones respecto al spec aprobado

1. **Sin flag `ocr`.** `core.extractor._extract_one` ya hace OCR inline (Docling para PDF escaneado ≤30 pp, con guarda anti-OOM). El spec proponía `ocr=True` opt-in, pero exponerlo exigiría modificar la lógica OCR existente — prohibido por el no-objetivo del spec. Se confía en el motor: PDFs escaneados se OCR-izan inline y se marcan `confianza: por-verificar` (método `docling`); los que el motor no puede (>30 pp o Docling ausente) caen a `sin_texto` y cuentan en el report. El flag conservado es `forzar` (ignora caché).
2. **`.xlsm`** se añade al conjunto soportado del extractor (el spec listaba `.xls/.xlsx`; el caso real tiene un `.xlsm`).

## Estructura de ficheros

**Crear:**
- `core/adjuntos_contenido/__init__.py` — API pública (`procesar_caso`, `aplicar_resumenes`, `Resumidor`, `ResumidorNoop`, `ContenidoReport`).
- `core/adjuntos_contenido/model.py` — dataclasses `AdjuntoDescubierto`, `Extraccion`, `ContenidoReport`.
- `core/adjuntos_contenido/descubrir.py` — escaneo de `adjuntos/`, parseo de sidecars, emparejado con binarios.
- `core/adjuntos_contenido/router.py` — dispatch por tipo (reutiliza `_extract_one`; imágenes/omitidos).
- `core/adjuntos_contenido/render.py` — `render_contenido`, `parsear_contenido`, `reemplazar_resumen`, `set_frontmatter`.
- `core/adjuntos_contenido/estado.py` — caché incremental por sha256.
- `core/adjuntos_contenido/pipeline.py` — `procesar_caso` / `procesar_dir` + poda.
- `core/adjuntos_contenido/resumen.py` — capa LLM (`Resumidor`, `ResumidorNoop`, `aplicar_resumenes`).
- `core/adjuntos_contenido/__main__.py` — CLI.

**Modificar:**
- `core/extractor.py` — añadir `_try_rtf`, `_try_ics`, branch `.rtf`/`.ics`, y `.xlsm` al conjunto pandas. **No** bumpear `EXTRACTOR_VERSION` (solo añade tipos antes no soportados; no cambia resultados de los ya soportados). **No** tocar la rama PDF/OCR.
- `requirements.txt` — añadir `striprtf`.

**Tests (crear):**
- `tests/test_extractor_rtf_ics_xlsm.py`
- `tests/test_adjuntos_contenido_descubrir.py`
- `tests/test_adjuntos_contenido_router.py`
- `tests/test_adjuntos_contenido_render.py`
- `tests/test_adjuntos_contenido_estado.py`
- `tests/test_adjuntos_contenido_resumen.py`
- `tests/test_adjuntos_contenido_pipeline.py`

---

## Task 1: Dependencia `striprtf`

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Añadir la dependencia**

Añadir al final de `requirements.txt` (en su propia línea):

```
striprtf
```

- [ ] **Step 2: Instalar en el venv**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pip install striprtf`
Expected: `Successfully installed striprtf-...`

- [ ] **Step 3: Verificar import**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -c "from striprtf.striprtf import rtf_to_text; print(rtf_to_text(r'{\rtf1\ansi Hola mundo\par}'))"`
Expected: imprime `Hola mundo`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "build: añadir striprtf para extracción de RTF (burofax) en fase 2 de adjuntos"
```

---

## Task 2: Extractor RTF en `core/extractor.py`

**Files:**
- Modify: `core/extractor.py`
- Test: `tests/test_extractor_rtf_ics_xlsm.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_extractor_rtf_ics_xlsm.py`:

```python
from pathlib import Path

from core.extractor import _extract_one


def test_extract_rtf(tmp_path: Path):
    p = tmp_path / "burofax.rtf"
    p.write_text(r"{\rtf1\ansi\deff0 Hola \b mundo\b0 burofax\par}", encoding="ascii")
    texto, metodo = _extract_one(p)
    assert metodo == "rtf"
    assert "Hola" in texto and "mundo" in texto and "burofax" in texto
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_extractor_rtf_ics_xlsm.py::test_extract_rtf -v`
Expected: FAIL con `ExtractionError: No hay extractor disponible para burofax.rtf (.rtf)`

- [ ] **Step 3: Implementar `_try_rtf` y su branch**

En `core/extractor.py`, añadir la función junto a los demás backends (p. ej. tras `_try_email`, antes de `# --- Orquestador ---`):

```python
def _try_rtf(path: Path) -> str | None:
    try:
        from striprtf.striprtf import rtf_to_text  # type: ignore
    except Exception:
        return None
    try:
        raw = path.read_bytes().decode("latin-1", errors="replace")
        return rtf_to_text(raw)
    except Exception:
        return None
```

Y en `_extract_one`, justo antes del `raise ExtractionError(...)` final, añadir:

```python
    if ext == ".rtf":
        if (text := _try_rtf(path)) is not None:
            return text, "rtf"
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_extractor_rtf_ics_xlsm.py::test_extract_rtf -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/extractor.py tests/test_extractor_rtf_ics_xlsm.py
git commit -m "feat(extractor): soporte RTF (striprtf) para burofax"
```

---

## Task 3: Extractor ICS en `core/extractor.py`

**Files:**
- Modify: `core/extractor.py`
- Test: `tests/test_extractor_rtf_ics_xlsm.py`

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_extractor_rtf_ics_xlsm.py`:

```python
def test_extract_ics(tmp_path: Path):
    p = tmp_path / "invite.ics"
    p.write_text(
        "BEGIN:VCALENDAR\r\n"
        "BEGIN:VEVENT\r\n"
        "SUMMARY:Reunión [inmueble]\r\n"
        "DTSTART:20260604T100000Z\r\n"
        "LOCATION:Barcelona\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n",
        encoding="utf-8",
    )
    texto, metodo = _extract_one(p)
    assert metodo == "ics"
    assert "Reunión [inmueble]" in texto
    assert "DTSTART" in texto and "20260604T100000Z" in texto
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_extractor_rtf_ics_xlsm.py::test_extract_ics -v`
Expected: FAIL con `ExtractionError: ... (.ics)`

- [ ] **Step 3: Implementar `_try_ics` y su branch**

En `core/extractor.py`, añadir junto a los backends:

```python
def _try_ics(path: Path) -> str | None:
    """Resumen estructurado de un .ics (stdlib, sin dependencias).

    Desdobla líneas continuadas (RFC 5545: empiezan con espacio/tab) y vuelca
    los campos relevantes de cada VEVENT.
    """
    try:
        raw = _read_text_file(path)
    except Exception:
        return None
    unfolded = raw.replace("\r\n", "\n").replace("\n ", "").replace("\n\t", "")
    campos = ("SUMMARY", "DTSTART", "DTEND", "LOCATION", "ORGANIZER", "ATTENDEE", "DESCRIPTION")
    lineas: list[str] = []
    for linea in unfolded.split("\n"):
        if ":" not in linea:
            continue
        nombre = linea.split(":", 1)[0].split(";", 1)[0].strip().upper()
        if nombre in campos:
            valor = linea.split(":", 1)[1].strip()
            lineas.append(f"{nombre}: {valor}")
    return "\n".join(lineas) if lineas else None
```

Y en `_extract_one`, antes del `raise` final (tras el branch `.rtf`):

```python
    if ext == ".ics":
        if (text := _try_ics(path)) is not None:
            return text, "ics"
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_extractor_rtf_ics_xlsm.py::test_extract_ics -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/extractor.py tests/test_extractor_rtf_ics_xlsm.py
git commit -m "feat(extractor): soporte ICS (stdlib) para invitaciones de calendario"
```

---

## Task 4: Soporte `.xlsm` en el branch pandas

**Files:**
- Modify: `core/extractor.py:231`
- Test: `tests/test_extractor_rtf_ics_xlsm.py`

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_extractor_rtf_ics_xlsm.py`:

```python
def test_extract_xlsm(tmp_path: Path):
    from openpyxl import Workbook

    p = tmp_path / "datos.xlsm"
    wb = Workbook()
    ws = wb.active
    ws["A1"] = "hola"
    ws["B1"] = "mundo"
    wb.save(p)  # openpyxl escribe estructura xlsx; la extensión no afecta a la lectura
    texto, metodo = _extract_one(p)
    assert metodo == "pandas"
    assert "hola" in texto and "mundo" in texto
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_extractor_rtf_ics_xlsm.py::test_extract_xlsm -v`
Expected: FAIL con `ExtractionError: ... (.xlsm)`

- [ ] **Step 3: Añadir `.xlsm` al conjunto pandas**

En `core/extractor.py`, en `_extract_one`, cambiar la línea:

```python
    if ext in {".csv", ".xlsx", ".xls"}:
```

por:

```python
    if ext in {".csv", ".xlsx", ".xls", ".xlsm"}:
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_extractor_rtf_ics_xlsm.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add core/extractor.py tests/test_extractor_rtf_ics_xlsm.py
git commit -m "feat(extractor): soportar .xlsm en la rama pandas"
```

---

## Task 5: Modelo de datos

**Files:**
- Create: `core/adjuntos_contenido/__init__.py`
- Create: `core/adjuntos_contenido/model.py`
- Test: `tests/test_adjuntos_contenido_render.py` (placeholder de import; se amplía en Task 8)

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_adjuntos_contenido_render.py`:

```python
from pathlib import Path

from core.adjuntos_contenido.model import AdjuntoDescubierto, Extraccion, ContenidoReport


def test_modelos_basicos():
    adj = AdjuntoDescubierto(
        att_id="ATT-00001", sha256="abc", tipo="application/pdf",
        nombre_original="x.pdf", mensajes=["MSG-00001"], base="2024-01-01_x_ATT-00001",
        ruta_binario=Path("x.pdf"), ruta_sidecar=Path("x.md"),
    )
    assert adj.att_id == "ATT-00001"
    ext = Extraccion(texto="hola", metodo="rtf", ok=True, confianza="alta")
    assert ext.vision_estado == "n/a" and ext.motivo == ""
    rep = ContenidoReport()
    assert rep.extraidos == 0 and rep.errores == []
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_render.py::test_modelos_basicos -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.adjuntos_contenido'`

- [ ] **Step 3: Crear el paquete y el modelo**

Crear `core/adjuntos_contenido/__init__.py` vacío (se llenará en Task 12):

```python
"""Fase 2 de contenido de adjuntos: extracción de texto fiel + cola de resumen/visión."""
```

Crear `core/adjuntos_contenido/model.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AdjuntoDescubierto:
    att_id: str
    sha256: str
    tipo: str
    nombre_original: str
    mensajes: list[str]
    base: str
    ruta_binario: Path
    ruta_sidecar: Path


@dataclass
class Extraccion:
    texto: str
    metodo: str
    ok: bool
    confianza: str
    vision_estado: str = "n/a"
    motivo: str = ""


@dataclass
class ContenidoReport:
    extraidos: int = 0
    omitidos: int = 0
    sin_texto: int = 0
    saltados: int = 0
    podados: int = 0
    pendientes_resumen: int = 0
    pendientes_vision: int = 0
    errores: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_render.py::test_modelos_basicos -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/adjuntos_contenido/__init__.py core/adjuntos_contenido/model.py tests/test_adjuntos_contenido_render.py
git commit -m "feat(adjuntos-contenido): paquete + modelo de datos"
```

---

## Task 6: Descubrimiento de adjuntos

**Files:**
- Create: `core/adjuntos_contenido/descubrir.py`
- Test: `tests/test_adjuntos_contenido_descubrir.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_adjuntos_contenido_descubrir.py`:

```python
from pathlib import Path

from core.adjuntos_contenido.descubrir import descubrir

SIDECAR = (
    "# GENERADO por core.email_atomize — NO editar.\n\n"
    "- att_id: ATT-00053\n"
    "- nombre_original: Contrato honorarios profesionales.pdf\n"
    "- tipo: application/pdf\n"
    "- sha256: 12ece1abc\n"
    "- primera_aparicion: 2024-10-05\n"
    "- mensajes: MSG-00050, MSG-00133\n"
    "- etiquetas: []\n\n"
    "## Descripción\n\n(pendiente; OCR en fase 2)\n"
)


def test_descubre_y_empareja(tmp_path: Path):
    adj_dir = tmp_path / "adjuntos"
    adj_dir.mkdir()
    base = "2024-10-05_Contrato_honorarios_profesionales_ATT-00053"
    (adj_dir / f"{base}.md").write_text(SIDECAR, encoding="utf-8")
    (adj_dir / f"{base}.pdf").write_bytes(b"%PDF-1.4 fake")
    # un .contenido.md ajeno NO debe tomarse como sidecar
    (adj_dir / f"{base}.contenido.md").write_text("ruido", encoding="utf-8")

    res = descubrir(adj_dir)

    assert len(res) == 1
    a = res[0]
    assert a.att_id == "ATT-00053"
    assert a.sha256 == "12ece1abc"
    assert a.tipo == "application/pdf"
    assert a.nombre_original == "Contrato honorarios profesionales.pdf"
    assert a.mensajes == ["MSG-00050", "MSG-00133"]
    assert a.base == base
    assert a.ruta_binario == adj_dir / f"{base}.pdf"


def test_sidecar_ficha_md_para_original_md(tmp_path: Path):
    adj_dir = tmp_path / "adjuntos"
    adj_dir.mkdir()
    base = "2024-01-01_nota_ATT-00099"
    sidecar = SIDECAR.replace(
        "Contrato honorarios profesionales.pdf", "nota.md"
    ).replace("ATT-00053", "ATT-00099")
    (adj_dir / f"{base}.ficha.md").write_text(sidecar, encoding="utf-8")
    (adj_dir / f"{base}.md").write_bytes(b"# nota original")

    res = descubrir(adj_dir)

    assert len(res) == 1
    assert res[0].base == base
    assert res[0].ruta_binario == adj_dir / f"{base}.md"
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_descubrir.py -v`
Expected: FAIL con `ModuleNotFoundError: ... descubrir`

- [ ] **Step 3: Implementar `descubrir.py`**

Crear `core/adjuntos_contenido/descubrir.py`:

```python
from __future__ import annotations

from pathlib import Path

from .model import AdjuntoDescubierto

_HEADER = "# GENERADO por core.email_atomize"


def descubrir(adjuntos_dir: Path) -> list[AdjuntoDescubierto]:
    """Empareja cada sidecar de email_atomize con su binario en `adjuntos/`."""
    out: list[AdjuntoDescubierto] = []
    for sidecar in sorted(adjuntos_dir.glob("*.md")):
        if sidecar.name.endswith(".contenido.md"):
            continue
        try:
            texto = sidecar.read_text(encoding="utf-8")
        except Exception:
            continue
        if not texto.lstrip().startswith(_HEADER):
            continue
        meta = _parse_sidecar(texto)
        if not meta.get("att_id") or not meta.get("sha256"):
            continue
        base, binario = _binario_para(sidecar, meta.get("nombre_original", ""))
        out.append(AdjuntoDescubierto(
            att_id=meta["att_id"],
            sha256=meta["sha256"],
            tipo=meta.get("tipo", ""),
            nombre_original=meta.get("nombre_original", ""),
            mensajes=meta.get("mensajes", []),
            base=base,
            ruta_binario=binario,
            ruta_sidecar=sidecar,
        ))
    return out


def _parse_sidecar(texto: str) -> dict:
    meta: dict = {}
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea.startswith("- ") or ": " not in linea:
            continue
        clave, valor = linea[2:].split(": ", 1)
        clave, valor = clave.strip(), valor.strip()
        if clave == "mensajes":
            meta[clave] = [m.strip() for m in valor.split(",") if m.strip()]
        else:
            meta[clave] = valor
    return meta


def _binario_para(sidecar: Path, nombre_original: str) -> tuple[str, Path]:
    nombre = sidecar.name
    if nombre.endswith(".ficha.md"):
        base = nombre[: -len(".ficha.md")]
    else:
        base = nombre[: -len(".md")]
    ext = Path(nombre_original).suffix
    return base, sidecar.with_name(f"{base}{ext}")
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_descubrir.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add core/adjuntos_contenido/descubrir.py tests/test_adjuntos_contenido_descubrir.py
git commit -m "feat(adjuntos-contenido): descubrimiento y emparejado sidecar↔binario"
```

---

## Task 7: Router de extracción por tipo

**Files:**
- Create: `core/adjuntos_contenido/router.py`
- Test: `tests/test_adjuntos_contenido_router.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_adjuntos_contenido_router.py`:

```python
from pathlib import Path

from core.adjuntos_contenido.router import extraer, IMG_DECORATIVA_MAX


def test_imagen_pequena_es_decorativa(tmp_path: Path):
    p = tmp_path / "icon.png"
    p.write_bytes(b"x" * 1024)  # < 50KB
    ext = extraer(p, "image/png")
    assert ext.metodo == "omitido"
    assert ext.ok is True
    assert "decorativa" in ext.motivo


def test_imagen_grande_va_a_vision(tmp_path: Path):
    p = tmp_path / "foto.jpg"
    p.write_bytes(b"x" * (IMG_DECORATIVA_MAX + 1))
    ext = extraer(p, "image/jpeg")
    assert ext.metodo == "vision"
    assert ext.vision_estado == "pendiente"


def test_emz_y_zip_omitidos(tmp_path: Path):
    for nombre, mime in [("a.emz", "application/octet-stream"), ("c.zip", "application/zip")]:
        p = tmp_path / nombre
        p.write_bytes(b"x" * (60 * 1024))
        ext = extraer(p, mime)
        assert ext.metodo == "omitido"
        assert ext.ok is True


def test_no_soportado_es_omitido_sin_excepcion(tmp_path: Path):
    p = tmp_path / "raro.xyz"
    p.write_bytes(b"contenido")
    ext = extraer(p, "application/octet-stream")
    assert ext.metodo == "omitido"
    assert "sin extractor" in ext.motivo


def test_rtf_extrae_texto_alta_confianza(tmp_path: Path):
    p = tmp_path / "burofax.rtf"
    p.write_text(r"{\rtf1\ansi Hola burofax\par}", encoding="ascii")
    ext = extraer(p, "application/rtf")
    assert ext.metodo == "rtf"
    assert ext.confianza == "alta"
    assert "Hola" in ext.texto


def test_docling_se_marca_por_verificar(tmp_path: Path, monkeypatch):
    p = tmp_path / "escaneado.pdf"
    p.write_bytes(b"%PDF-1.4 fake")
    monkeypatch.setattr("core.adjuntos_contenido.router._extract_one",
                        lambda ruta: ("texto OCR", "docling"))
    ext = extraer(p, "application/pdf")
    assert ext.metodo == "docling"
    assert ext.confianza == "por-verificar"


def test_sin_texto_marca_no_ok(tmp_path: Path, monkeypatch):
    p = tmp_path / "escaneado.pdf"
    p.write_bytes(b"%PDF-1.4 fake")
    monkeypatch.setattr("core.adjuntos_contenido.router._extract_one",
                        lambda ruta: ("", "sin_texto"))
    ext = extraer(p, "application/pdf")
    assert ext.metodo == "sin_texto"
    assert ext.ok is False
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_router.py -v`
Expected: FAIL con `ModuleNotFoundError: ... router`

- [ ] **Step 3: Implementar `router.py`**

Crear `core/adjuntos_contenido/router.py`:

```python
from __future__ import annotations

from pathlib import Path

from core.extractor import ExtractionError, _extract_one

from .model import Extraccion

# Imagen por debajo de este tamaño = probable firma/icono/emoji → omitida.
IMG_DECORATIVA_MAX = 50 * 1024
_EXT_IMAGEN = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
_EXT_OMITIDO = {".emz", ".zip"}


def extraer(ruta: Path, mime: str) -> Extraccion:
    """Enruta un adjunto a extracción de texto, cola de visión u omitido.

    Nunca lanza: un tipo no soportado se marca `omitido`."""
    ext = ruta.suffix.lower()

    if mime.startswith("image/") or ext in _EXT_IMAGEN:
        if ruta.stat().st_size < IMG_DECORATIVA_MAX:
            return Extraccion(texto="", metodo="omitido", ok=True, confianza="omitido",
                              motivo="imagen decorativa (<50KB)")
        return Extraccion(texto="", metodo="vision", ok=True, confianza="por-verificar",
                          vision_estado="pendiente")

    if ext in _EXT_OMITIDO:
        return Extraccion(texto="", metodo="omitido", ok=True, confianza="omitido",
                          motivo=f"tipo no procesado ({ext})")

    try:
        texto, metodo = _extract_one(ruta)
    except ExtractionError:
        return Extraccion(texto="", metodo="omitido", ok=True, confianza="omitido",
                          motivo=f"sin extractor ({ext})")

    if metodo == "sin_texto" or not texto.strip():
        return Extraccion(texto="", metodo="sin_texto", ok=False, confianza="omitido",
                          motivo="PDF escaneado sin texto / OCR no disponible")

    confianza = "por-verificar" if metodo == "docling" else "alta"
    return Extraccion(texto=texto, metodo=metodo, ok=True, confianza=confianza)
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_router.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add core/adjuntos_contenido/router.py tests/test_adjuntos_contenido_router.py
git commit -m "feat(adjuntos-contenido): router de extracción por tipo (texto/visión/omitido)"
```

---

## Task 8: Render del `.contenido.md`

**Files:**
- Create: `core/adjuntos_contenido/render.py`
- Test: `tests/test_adjuntos_contenido_render.py` (ampliar)

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_adjuntos_contenido_render.py`:

```python
from core.adjuntos_contenido import render


def _md_ejemplo() -> str:
    return render.render_contenido(
        att_id="ATT-00053", nombre_original="Contrato.pdf", tipo="application/pdf",
        sha256="abc123", metodo="pypdf", caracteres=42, confianza="alta",
        resumen_estado="pendiente", vision_estado="n/a",
        mensajes=["MSG-00050", "MSG-00133"], resumen=None, texto="Texto fiel del contrato.",
    )


def test_render_estructura_y_frontmatter():
    md = _md_ejemplo()
    assert md.startswith("---\n")
    assert "att_id: ATT-00053" in md
    assert "metodo_extraccion: pypdf" in md
    assert "ocr_aplicado: false" in md
    assert "resumen_estado: pendiente" in md
    assert "mensajes: [MSG-00050, MSG-00133]" in md
    assert "## Resumen\n\n_(pendiente; capa LLM en sesión)_" in md
    assert "## Texto\n\nTexto fiel del contrato." in md


def test_render_docling_marca_ocr_y_por_verificar():
    md = render.render_contenido(
        att_id="ATT-1", nombre_original="x.pdf", tipo="application/pdf", sha256="s",
        metodo="docling", caracteres=10, confianza="por-verificar",
        resumen_estado="pendiente", vision_estado="n/a", mensajes=["MSG-1"],
        resumen=None, texto="ocr",
    )
    assert "ocr_aplicado: true" in md
    assert "confianza: por-verificar" in md


def test_parsear_y_reemplazar_resumen_preserva_texto():
    md = _md_ejemplo()
    md2 = render.reemplazar_resumen(md, "Reconocimiento de deuda de honorarios.")
    md2 = render.set_frontmatter(md2, "resumen_estado", "hecho")
    assert "Reconocimiento de deuda de honorarios." in md2
    assert "resumen_estado: hecho" in md2
    # el texto fiel se preserva intacto
    assert "## Texto\n\nTexto fiel del contrato." in md2
    fm, resumen_body, texto_body = render.parsear_contenido(md2)
    assert fm["att_id"] == "ATT-00053"
    assert resumen_body == "Reconocimiento de deuda de honorarios."
    assert texto_body == "Texto fiel del contrato."
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_render.py -v`
Expected: FAIL (los tests de modelo pasan; los de render fallan con `ImportError`/`AttributeError`)

- [ ] **Step 3: Implementar `render.py`**

Crear `core/adjuntos_contenido/render.py`:

```python
from __future__ import annotations

import re

_GEN = ("# GENERADO por core.adjuntos_contenido — texto fiel determinista; "
        "el RESUMEN puede ser de IA (marcado).")
_RESUMEN_PENDIENTE = "_(pendiente; capa LLM en sesión)_"
_TEXTO_VACIO = "_(sin texto extraído)_"


def render_contenido(*, att_id: str, nombre_original: str, tipo: str, sha256: str,
                     metodo: str, caracteres: int, confianza: str, resumen_estado: str,
                     vision_estado: str, mensajes: list[str], resumen: str | None,
                     texto: str) -> str:
    ocr = "true" if metodo == "docling" else "false"
    resumen_body = resumen.strip() if (resumen and resumen.strip()) else _RESUMEN_PENDIENTE
    texto_body = texto if texto.strip() else _TEXTO_VACIO
    return (
        "---\n"
        f"{_GEN}\n"
        f"att_id: {att_id}\n"
        f"nombre_original: {nombre_original}\n"
        f"tipo: {tipo}\n"
        f"sha256: {sha256}\n"
        f"metodo_extraccion: {metodo}\n"
        f"ocr_aplicado: {ocr}\n"
        f"caracteres: {caracteres}\n"
        f"confianza: {confianza}\n"
        f"resumen_estado: {resumen_estado}\n"
        f"vision_estado: {vision_estado}\n"
        f"mensajes: [{', '.join(mensajes)}]\n"
        "---\n\n"
        "## Resumen\n\n"
        f"{resumen_body}\n\n"
        "## Texto\n\n"
        f"{texto_body}\n"
    )


def reemplazar_resumen(md: str, nuevo_resumen: str) -> str:
    """Sustituye el cuerpo de `## Resumen` preservando el resto byte a byte."""
    patron = re.compile(r"(## Resumen\n\n).*?(\n\n## Texto)", re.DOTALL)
    return patron.sub(lambda m: m.group(1) + nuevo_resumen.strip() + m.group(2), md, count=1)


def set_frontmatter(md: str, clave: str, valor: str) -> str:
    patron = re.compile(rf"(?m)^({re.escape(clave)}: ).*$")
    return patron.sub(rf"\g<1>{valor}", md, count=1)


def parsear_contenido(md: str) -> tuple[dict, str, str]:
    """Devuelve (frontmatter, cuerpo_resumen, cuerpo_texto)."""
    partes = md.split("---\n", 2)
    fm_block = partes[1] if len(partes) >= 3 else ""
    cuerpo = partes[2] if len(partes) >= 3 else md
    fm: dict = {}
    for linea in fm_block.splitlines():
        if linea.startswith("#") or ": " not in linea:
            continue
        clave, valor = linea.split(": ", 1)
        fm[clave.strip()] = valor.strip()
    resumen_body, texto_body = "", ""
    if "## Texto" in cuerpo:
        antes, despues = cuerpo.split("## Texto", 1)
        texto_body = despues.strip()
    else:
        antes = cuerpo
    if "## Resumen" in antes:
        resumen_body = antes.split("## Resumen", 1)[1].strip()
    return fm, resumen_body, texto_body
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_render.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add core/adjuntos_contenido/render.py tests/test_adjuntos_contenido_render.py
git commit -m "feat(adjuntos-contenido): render del .contenido.md + parseo/edición de resumen"
```

---

## Task 9: Caché de estado incremental

**Files:**
- Create: `core/adjuntos_contenido/estado.py`
- Test: `tests/test_adjuntos_contenido_estado.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_adjuntos_contenido_estado.py`:

```python
from pathlib import Path

from core.adjuntos_contenido import estado


def test_guardar_y_cargar_roundtrip(tmp_path: Path):
    files = {"sha1": {"metodo": "pypdf", "chars": 10, "ok": True,
                      "resumen_estado": "pendiente", "vision_estado": "n/a", "base": "b1"}}
    estado.guardar_estado(tmp_path, files)
    assert estado.cargar_estado(tmp_path) == files


def test_version_distinta_invalida_cache(tmp_path: Path):
    estado.guardar_estado(tmp_path, {"sha1": {"ok": True}})
    p = tmp_path / estado._ESTADO
    p.write_text(p.read_text(encoding="utf-8").replace(
        f'"contenido_version": {estado.CONTENIDO_VERSION}', '"contenido_version": 999'),
        encoding="utf-8")
    assert estado.cargar_estado(tmp_path) == {}


def test_sin_fichero_devuelve_vacio(tmp_path: Path):
    assert estado.cargar_estado(tmp_path) == {}
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_estado.py -v`
Expected: FAIL con `ModuleNotFoundError: ... estado`

- [ ] **Step 3: Implementar `estado.py`**

Crear `core/adjuntos_contenido/estado.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

# Súbela cuando cambie la lógica de extracción/render para invalidar el caché.
CONTENIDO_VERSION = 1
_ESTADO = "_contenido_estado.json"


def cargar_estado(adjuntos_dir: Path) -> dict:
    p = adjuntos_dir / _ESTADO
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if data.get("contenido_version") != CONTENIDO_VERSION:
        return {}
    return data.get("files", {})


def guardar_estado(adjuntos_dir: Path, files: dict) -> None:
    payload = {"contenido_version": CONTENIDO_VERSION, "files": files}
    (adjuntos_dir / _ESTADO).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_estado.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add core/adjuntos_contenido/estado.py tests/test_adjuntos_contenido_estado.py
git commit -m "feat(adjuntos-contenido): caché de estado incremental por sha256"
```

---

## Task 10: Orquestador `pipeline.py`

**Files:**
- Create: `core/adjuntos_contenido/pipeline.py`
- Test: `tests/test_adjuntos_contenido_pipeline.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_adjuntos_contenido_pipeline.py`:

```python
from pathlib import Path

from core.adjuntos_contenido.pipeline import procesar_dir

HEADER = "# GENERADO por core.email_atomize — NO editar.\n\n"


def _sidecar(att_id: str, nombre: str, tipo: str, sha: str) -> str:
    return (
        HEADER
        + f"- att_id: {att_id}\n- nombre_original: {nombre}\n- tipo: {tipo}\n"
        + f"- sha256: {sha}\n- primera_aparicion: 2024-01-01\n"
        + "- mensajes: MSG-00001\n- etiquetas: []\n\n## Descripción\n\n(pendiente; OCR en fase 2)\n"
    )


def _crea_adjunto(adj_dir: Path, base: str, ext: str, sidecar: str, data: bytes):
    (adj_dir / f"{base}.md").write_text(sidecar, encoding="utf-8")
    (adj_dir / f"{base}{ext}").write_bytes(data)


def test_pipeline_familias(tmp_path: Path):
    adj = tmp_path / "adjuntos"
    adj.mkdir()
    # RTF (texto)
    _crea_adjunto(adj, "2024-01-01_burofax_ATT-00001", ".rtf",
                  _sidecar("ATT-00001", "burofax.rtf", "application/rtf", "sha-rtf"),
                  br"{\rtf1\ansi Hola burofax\par}")
    # imagen pequeña (omitida)
    _crea_adjunto(adj, "2024-01-01_icon_ATT-00002", ".png",
                  _sidecar("ATT-00002", "icon.png", "image/png", "sha-png"),
                  b"x" * 1024)
    # imagen grande (visión pendiente)
    _crea_adjunto(adj, "2024-01-01_foto_ATT-00003", ".jpg",
                  _sidecar("ATT-00003", "foto.jpg", "image/jpeg", "sha-jpg"),
                  b"x" * (60 * 1024))
    # emz (omitido)
    _crea_adjunto(adj, "2024-01-01_blob_ATT-00004", ".emz",
                  _sidecar("ATT-00004", "blob.emz", "application/octet-stream", "sha-emz"),
                  b"x" * (60 * 1024))

    rep = procesar_dir(adj)

    assert rep.extraidos == 1            # rtf
    assert rep.omitidos == 2             # png pequeño + emz
    assert rep.pendientes_vision == 1    # jpg grande
    assert rep.pendientes_resumen == 2   # rtf (texto) + jpg (visión)
    # se generaron los .contenido.md
    assert (adj / "2024-01-01_burofax_ATT-00001.contenido.md").exists()
    rtf_md = (adj / "2024-01-01_burofax_ATT-00001.contenido.md").read_text(encoding="utf-8")
    assert "Hola burofax" in rtf_md
    assert "metodo_extraccion: rtf" in rtf_md
    # el binario y el sidecar NO se tocan
    assert (adj / "2024-01-01_burofax_ATT-00001.rtf").read_bytes() == br"{\rtf1\ansi Hola burofax\par}"
    assert "NO editar" in (adj / "2024-01-01_burofax_ATT-00001.md").read_text(encoding="utf-8")


def test_pipeline_idempotente_y_skip(tmp_path: Path):
    adj = tmp_path / "adjuntos"
    adj.mkdir()
    _crea_adjunto(adj, "2024-01-01_burofax_ATT-00001", ".rtf",
                  _sidecar("ATT-00001", "burofax.rtf", "application/rtf", "sha-rtf"),
                  br"{\rtf1\ansi Hola burofax\par}")
    rep1 = procesar_dir(adj)
    md1 = (adj / "2024-01-01_burofax_ATT-00001.contenido.md").read_text(encoding="utf-8")
    rep2 = procesar_dir(adj)
    md2 = (adj / "2024-01-01_burofax_ATT-00001.contenido.md").read_text(encoding="utf-8")
    assert rep1.extraidos == 1
    assert rep2.saltados == 1 and rep2.extraidos == 0
    assert md1 == md2  # byte-idéntico


def test_pipeline_poda_huerfanos(tmp_path: Path):
    adj = tmp_path / "adjuntos"
    adj.mkdir()
    _crea_adjunto(adj, "2024-01-01_burofax_ATT-00001", ".rtf",
                  _sidecar("ATT-00001", "burofax.rtf", "application/rtf", "sha-rtf"),
                  br"{\rtf1\ansi Hola burofax\par}")
    huerfano = adj / "2020-01-01_viejo_ATT-99999.contenido.md"
    huerfano.write_text("contenido viejo sin sidecar", encoding="utf-8")

    rep = procesar_dir(adj)

    assert rep.podados == 1
    assert not huerfano.exists()
    assert (adj / "2024-01-01_burofax_ATT-00001.contenido.md").exists()
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_pipeline.py -v`
Expected: FAIL con `ModuleNotFoundError: ... pipeline`

- [ ] **Step 3: Implementar `pipeline.py`**

Crear `core/adjuntos_contenido/pipeline.py`:

```python
from __future__ import annotations

from pathlib import Path

from . import render, router
from .descubrir import descubrir
from .estado import cargar_estado, guardar_estado
from .model import ContenidoReport


def procesar_caso(case_id: str, *, forzar: bool = False) -> ContenidoReport:
    from core.email_atomize.pipeline import emails_out_dir
    return procesar_dir(emails_out_dir(case_id) / "adjuntos", forzar=forzar)


def procesar_dir(adjuntos_dir: Path, *, forzar: bool = False) -> ContenidoReport:
    report = ContenidoReport()
    if not adjuntos_dir.exists():
        report.errores.append(f"no existe el directorio {adjuntos_dir}")
        return report

    descubiertos = descubrir(adjuntos_dir)
    prev = {} if forzar else cargar_estado(adjuntos_dir)
    nuevo: dict = {}
    esperados: set[str] = set()

    for adj in descubiertos:
        destino = adjuntos_dir / f"{adj.base}.contenido.md"
        esperados.add(destino.name)

        cached = prev.get(adj.sha256)
        if not forzar and cached and cached.get("ok") and destino.exists():
            nuevo[adj.sha256] = cached
            report.saltados += 1
            continue

        if not adj.ruta_binario.exists():
            report.errores.append(f"{adj.att_id}: binario no encontrado ({adj.ruta_binario.name})")
            continue

        try:
            ext = router.extraer(adj.ruta_binario, adj.tipo)
        except Exception as exc:  # noqa: BLE001 — un adjunto no aborta la corrida
            report.errores.append(f"{adj.att_id}: {exc}")
            continue

        hay_resumen = ext.ok and (bool(ext.texto.strip()) or ext.vision_estado == "pendiente")
        resumen_estado = "pendiente" if hay_resumen else "n/a"

        md = render.render_contenido(
            att_id=adj.att_id, nombre_original=adj.nombre_original, tipo=adj.tipo,
            sha256=adj.sha256, metodo=ext.metodo, caracteres=len(ext.texto),
            confianza=ext.confianza, resumen_estado=resumen_estado,
            vision_estado=ext.vision_estado, mensajes=adj.mensajes,
            resumen=None, texto=ext.texto)
        destino.write_text(md, encoding="utf-8")

        entry = {"metodo": ext.metodo, "chars": len(ext.texto), "ok": ext.ok,
                 "resumen_estado": resumen_estado, "vision_estado": ext.vision_estado,
                 "base": adj.base}
        nuevo[adj.sha256] = entry

        if ext.metodo == "omitido":
            report.omitidos += 1
        elif ext.metodo == "sin_texto" or not ext.ok:
            report.sin_texto += 1
        elif ext.metodo == "vision":
            pass  # imagen sin texto; se contabiliza en pendientes_vision al final
        else:
            report.extraidos += 1

        guardar_estado(adjuntos_dir, nuevo)  # incremental → reanudable

    # poda de huérfanos: solo *.contenido.md sin sidecar actual
    for p in adjuntos_dir.glob("*.contenido.md"):
        if p.name not in esperados:
            p.unlink()
            report.podados += 1

    report.pendientes_resumen = sum(
        1 for e in nuevo.values() if e.get("resumen_estado") == "pendiente")
    report.pendientes_vision = sum(
        1 for e in nuevo.values() if e.get("vision_estado") == "pendiente")
    guardar_estado(adjuntos_dir, nuevo)
    return report
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_pipeline.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add core/adjuntos_contenido/pipeline.py tests/test_adjuntos_contenido_pipeline.py
git commit -m "feat(adjuntos-contenido): orquestador procesar_dir/procesar_caso + poda idempotente"
```

---

## Task 11: Capa LLM desacoplada

**Files:**
- Create: `core/adjuntos_contenido/resumen.py`
- Test: `tests/test_adjuntos_contenido_resumen.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_adjuntos_contenido_resumen.py`:

```python
from pathlib import Path

from core.adjuntos_contenido.pipeline import procesar_dir
from core.adjuntos_contenido.resumen import ResumidorNoop, aplicar_resumenes_dir

HEADER = "# GENERADO por core.email_atomize — NO editar.\n\n"


def _sidecar(att_id, nombre, tipo, sha):
    return (HEADER + f"- att_id: {att_id}\n- nombre_original: {nombre}\n- tipo: {tipo}\n"
            + f"- sha256: {sha}\n- primera_aparicion: 2024-01-01\n"
            + "- mensajes: MSG-00001\n- etiquetas: []\n\n## Descripción\n\n(pendiente)\n")


def _setup_rtf(tmp_path: Path) -> Path:
    adj = tmp_path / "adjuntos"
    adj.mkdir()
    (adj / "2024-01-01_burofax_ATT-00001.md").write_text(
        _sidecar("ATT-00001", "burofax.rtf", "application/rtf", "sha-rtf"), encoding="utf-8")
    (adj / "2024-01-01_burofax_ATT-00001.rtf").write_text(
        r"{\rtf1\ansi Hola burofax\par}", encoding="ascii")
    procesar_dir(adj)
    return adj


class _FakeResumidor:
    def resumir(self, texto: str) -> str:
        return "Resumen falso del burofax."

    def describir_imagen(self, ruta: Path) -> str:
        return "Foto de un inmueble."


def test_noop_deja_pendiente(tmp_path: Path):
    adj = _setup_rtf(tmp_path)
    aplicados = aplicar_resumenes_dir(adj, ResumidorNoop())
    assert aplicados == 0
    md = (adj / "2024-01-01_burofax_ATT-00001.contenido.md").read_text(encoding="utf-8")
    assert "resumen_estado: pendiente" in md
    assert "_(pendiente; capa LLM en sesión)_" in md


def test_resumidor_rellena_sin_tocar_texto(tmp_path: Path):
    adj = _setup_rtf(tmp_path)
    aplicados = aplicar_resumenes_dir(adj, _FakeResumidor())
    assert aplicados == 1
    md = (adj / "2024-01-01_burofax_ATT-00001.contenido.md").read_text(encoding="utf-8")
    assert "Resumen falso del burofax." in md
    assert "resumen_estado: hecho" in md
    assert "## Texto\n\nHola burofax" in md  # texto fiel intacto
    # 2ª pasada: ya está hecho, no reaplica
    assert aplicar_resumenes_dir(adj, _FakeResumidor()) == 0
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_resumen.py -v`
Expected: FAIL con `ModuleNotFoundError: ... resumen`

- [ ] **Step 3: Implementar `resumen.py`**

Crear `core/adjuntos_contenido/resumen.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from . import render
from .estado import cargar_estado, guardar_estado


class Resumidor(Protocol):
    def resumir(self, texto: str) -> str: ...
    def describir_imagen(self, ruta: Path) -> str: ...


class ResumidorNoop:
    """Por defecto: no llama a ningún modelo; deja la cola en 'pendiente'."""

    def resumir(self, texto: str) -> str:
        return ""

    def describir_imagen(self, ruta: Path) -> str:
        return ""


def aplicar_resumenes(case_id: str, resumidor: Resumidor) -> int:
    from core.email_atomize.pipeline import emails_out_dir
    return aplicar_resumenes_dir(emails_out_dir(case_id) / "adjuntos", resumidor)


def aplicar_resumenes_dir(adjuntos_dir: Path, resumidor: Resumidor) -> int:
    estado = cargar_estado(adjuntos_dir)
    aplicados = 0
    for _sha, entry in estado.items():
        pendiente_resumen = entry.get("resumen_estado") == "pendiente"
        pendiente_vision = entry.get("vision_estado") == "pendiente"
        if not pendiente_resumen and not pendiente_vision:
            continue
        destino = adjuntos_dir / f"{entry['base']}.contenido.md"
        if not destino.exists():
            continue
        md = destino.read_text(encoding="utf-8")
        fm, _resumen, texto_body = render.parsear_contenido(md)

        if pendiente_vision:
            binario = adjuntos_dir / f"{entry['base']}{Path(fm.get('nombre_original', '')).suffix}"
            nuevo = resumidor.describir_imagen(binario) if binario.exists() else ""
        else:
            nuevo = resumidor.resumir(texto_body)

        if not nuevo.strip():
            continue  # NO-OP o sin resultado: se mantiene pendiente

        md = render.reemplazar_resumen(md, nuevo)
        md = render.set_frontmatter(md, "resumen_estado", "hecho")
        entry["resumen_estado"] = "hecho"
        if pendiente_vision:
            md = render.set_frontmatter(md, "vision_estado", "hecho")
            entry["vision_estado"] = "hecho"
        destino.write_text(md, encoding="utf-8")
        aplicados += 1

    guardar_estado(adjuntos_dir, estado)
    return aplicados
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_resumen.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add core/adjuntos_contenido/resumen.py tests/test_adjuntos_contenido_resumen.py
git commit -m "feat(adjuntos-contenido): capa LLM desacoplada (Resumidor + aplicar_resumenes)"
```

---

## Task 12: API pública y CLI

**Files:**
- Modify: `core/adjuntos_contenido/__init__.py`
- Create: `core/adjuntos_contenido/__main__.py`
- Test: `tests/test_adjuntos_contenido_pipeline.py` (añadir test de API pública)

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_adjuntos_contenido_pipeline.py`:

```python
def test_api_publica_expone_simbolos():
    import core.adjuntos_contenido as ac
    assert hasattr(ac, "procesar_caso")
    assert hasattr(ac, "aplicar_resumenes")
    assert hasattr(ac, "Resumidor")
    assert hasattr(ac, "ResumidorNoop")
    assert hasattr(ac, "ContenidoReport")
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_pipeline.py::test_api_publica_expone_simbolos -v`
Expected: FAIL con `AssertionError` (símbolos no exportados)

- [ ] **Step 3: Implementar `__init__.py` y `__main__.py`**

Reescribir `core/adjuntos_contenido/__init__.py`:

```python
"""Fase 2 de contenido de adjuntos: extracción de texto fiel + cola de resumen/visión."""
from __future__ import annotations

from .model import AdjuntoDescubierto, ContenidoReport, Extraccion
from .pipeline import procesar_caso, procesar_dir
from .resumen import Resumidor, ResumidorNoop, aplicar_resumenes, aplicar_resumenes_dir

__all__ = [
    "AdjuntoDescubierto", "ContenidoReport", "Extraccion",
    "procesar_caso", "procesar_dir",
    "Resumidor", "ResumidorNoop", "aplicar_resumenes", "aplicar_resumenes_dir",
]
```

Crear `core/adjuntos_contenido/__main__.py`:

```python
"""CLI: python -m core.adjuntos_contenido <case_id> [--forzar]"""
from __future__ import annotations

import sys

from .pipeline import procesar_caso


def main(argv: list[str]) -> int:
    forzar = "--forzar" in argv
    casos = [a for a in argv if not a.startswith("--")]
    if not casos:
        print("uso: python -m core.adjuntos_contenido <case_id> [--forzar]")
        return 2
    rep = procesar_caso(casos[0], forzar=forzar)
    print(f"extraidos={rep.extraidos} omitidos={rep.omitidos} sin_texto={rep.sin_texto} "
          f"saltados={rep.saltados} podados={rep.podados} "
          f"pendientes_resumen={rep.pendientes_resumen} pendientes_vision={rep.pendientes_vision}")
    for e in rep.errores:
        print(f"  ERROR: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest tests/test_adjuntos_contenido_pipeline.py -v`
Expected: 4 passed

- [ ] **Step 5: Verificar el CLI (uso sin args)**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m core.adjuntos_contenido`
Expected: imprime `uso: python -m core.adjuntos_contenido <case_id> [--forzar]` y sale con código 2

- [ ] **Step 6: Commit**

```bash
git add core/adjuntos_contenido/__init__.py core/adjuntos_contenido/__main__.py tests/test_adjuntos_contenido_pipeline.py
git commit -m "feat(adjuntos-contenido): API pública + CLI"
```

---

## Task 13: Suite verde completa

**Files:** (ninguno nuevo)

- [ ] **Step 1: Correr la suite completa**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && python -m pytest -q --tb=short`
Expected: todos los tests previos siguen verdes + los nuevos. Si algún test de orden aleatorio (`pytest-randomly`) rompe por aislamiento, investigar reload/isinstance (ver memoria `project-test-suite-pytest-randomly`).

- [ ] **Step 2: Verificar que no se bumpeó `EXTRACTOR_VERSION`**

Run: `cd "C:/Users/tnm33/Dev/FeesDefender" && grep -n "EXTRACTOR_VERSION =" core/extractor.py`
Expected: sigue siendo `EXTRACTOR_VERSION = 2` (solo se añadieron extractores RTF/ICS y `.xlsm`; no se invalidó el caché del pipeline principal).

- [ ] **Step 3: Commit (si hubo ajustes)**

```bash
git add -A
git commit -m "test(adjuntos-contenido): suite verde completa fase 2"
```

---

## Validación final (fuera del plan TDD — corrida real, requiere autorización)

Tras la suite verde, correr sobre el caso real (escribe en G:\ Drive del despacho — **autorización explícita de Nikolai requerida**):

```bash
cd "C:/Users/tnm33/Dev/FeesDefender" && python -m core.adjuntos_contenido W-02VND1
```

Revisar una muestra de `01_Procesado/Emails/adjuntos/*.contenido.md` (un contrato `.docx`, un burofax `.rtf`, un PDF de texto, un PDF escaneado, una foto). La capa de resumen/visión (`aplicar_resumenes`) se ejecuta después, en sesión, sobre la cola `pendiente`.
