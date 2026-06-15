# Intake de chats de WhatsApp — Fase A — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingerir exports de WhatsApp (`.zip` con `_chat.txt` + media) al árbol del caso (`00_Input/02_Whatsapp/<rol>/<chat>/`) de forma trazable y con control humano desde la UI de Streamlit.

**Architecture:** Tres capas. Un **parser puro** (`core/whatsapp_export.py`) convierte el `_chat.txt` en mensajes (núcleo reutilizable por la futura Fase B email). Un **glue** (`core/whatsapp_intake.py`) analiza el zip, deposita su contenido verbatim + el zip original, registra en `IntakeManifest` (dedup por hash de zip) y emite el evento `upload_whatsapp`. La **UI** (`streamlit_app.py`) sube uno o varios zips, previsualiza por chat y confirma.

**Tech Stack:** Python 3, `dataclasses`, `re`, `zipfile`, `hashlib` (vía `compute_sha256_bytes`); `pytest`; Streamlit (solo orquestación). Sin LLM, sin red.

**Convenciones del repo a respetar:** encoding UTF-8 sin BOM; tests con fixture `tmp_casos_root` + `case_manager.ensure_case` + `importlib.reload(config)`; commits con `git add <rutas exactas>` (NUNCA `git add -A` — hay trabajo concurrente en el árbol); suite rápida `python -m pytest -q --tb=no`.

**Referencias de spec:** `docs/superpowers/specs/2026-06-15-intake-whatsapp-design.md`.

---

## File Structure

- **Create** `core/whatsapp_export.py` — parser puro: `WhatsAppMessage`, `parse_chat`, `referencias_adjuntos`, `filter_by_date_range`. Sin IO ni red.
- **Create** `core/whatsapp_intake.py` — glue: `ChatPreview`, `DepositResult`, `analyze`, `deposit_export`. Lee zip en memoria, deposita en disco, registra manifest + log.
- **Create** `tests/test_whatsapp_export.py` — tests del parser.
- **Create** `tests/test_whatsapp_intake.py` — tests del glue.
- **Modify** `streamlit_app.py` — expander «📲 Importar chat de WhatsApp» en el tab Casos (verificación manual, sin unit test, como el resto de la UI).

Reutiliza sin modificar: `core/config.py` (`WHATSAPP_SUBDIRS`, `caso_path`, `settings`), `core/intake_manifest.py` (`IntakeManifest`, `compute_sha256_bytes`), `core/intake_log.py` (`append_event`, evento `upload_whatsapp` ya existente).

---

## Task 1: Parser — formato Android básico

**Files:**
- Create: `core/whatsapp_export.py`
- Test: `tests/test_whatsapp_export.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests del parser puro de exports de WhatsApp (core.whatsapp_export)."""
from __future__ import annotations

from datetime import datetime

from core.whatsapp_export import WhatsAppMessage, parse_chat


class TestParseAndroidBasico:
    def test_mensaje_simple(self):
        texto = "8/1/24, 10:32 - Juan Pérez: Hola, ¿qué tal?"
        msgs = parse_chat(texto)
        assert len(msgs) == 1
        m = msgs[0]
        assert isinstance(m, WhatsAppMessage)
        assert m.autor == "Juan Pérez"
        assert m.texto == "Hola, ¿qué tal?"
        assert m.es_sistema is False
        assert m.adjunto_ref is None
        assert m.timestamp == datetime(2024, 1, 8, 10, 32)

    def test_varios_mensajes(self):
        texto = (
            "8/1/24, 10:32 - Juan: Hola\n"
            "8/1/24, 10:33 - Ana López: Buenas\n"
        )
        msgs = parse_chat(texto)
        assert [m.autor for m in msgs] == ["Juan", "Ana López"]
        assert [m.texto for m in msgs] == ["Hola", "Buenas"]

    def test_anio_cuatro_cifras_y_segundos(self):
        texto = "8/1/2024, 10:32:05 - Juan: Hola"
        msgs = parse_chat(texto)
        assert msgs[0].timestamp == datetime(2024, 1, 8, 10, 32, 5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_whatsapp_export.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'core.whatsapp_export'`).

- [ ] **Step 3: Write minimal implementation**

```python
"""Parser puro de exports de WhatsApp («Exportar chat»).

Capa SIN red ni IO: convierte el texto de un ``_chat.txt`` en una lista de
``WhatsAppMessage``. Es el núcleo reutilizable por la Fase A (subida UI) y la
futura Fase B (adaptador email). Tolera los formatos iOS (corchetes) y Android
(guion), años de 2/4 cifras y horas 12/24h.

Ver ``docs/superpowers/specs/2026-06-15-intake-whatsapp-design.md`` §4.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class WhatsAppMessage:
    """Un mensaje del chat ya parseado."""
    timestamp: datetime | None   # None si la línea no parsea fecha
    autor: str | None            # None en mensajes de sistema
    texto: str                   # cuerpo (multilínea ya unido)
    adjunto_ref: str | None      # nombre de fichero referenciado, si lo hay
    es_sistema: bool             # cifrado E2E, altas/bajas de grupo, etc.


# Cabecera Android:  d/m/yy, HH:MM[ :SS][ am/pm] - resto
_RE_ANDROID = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s+"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]\.?\s*m\.?)?)\s+-\s+(.*)$",
    re.IGNORECASE,
)


def _parse_header(line: str) -> tuple[str, str, str] | None:
    """Si la línea abre un mensaje, devuelve (fecha, hora, resto). Si no, None."""
    m = _RE_ANDROID.match(line)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return None


def _parse_dt(date_str: str, time_str: str) -> datetime | None:
    """Combina fecha (día primero) + hora en un datetime. None si no parsea."""
    fecha = None
    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            fecha = datetime.strptime(date_str, fmt).date()
            break
        except ValueError:
            continue
    if fecha is None:
        return None
    t = re.sub(r"\s+", "", time_str.strip().lower().replace(".", ""))
    hora = None
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M:%S%p", "%I:%M%p"):
        try:
            hora = datetime.strptime(t, fmt).time()
            break
        except ValueError:
            continue
    if hora is None:
        return None
    return datetime.combine(fecha, hora)


def _split_author(rest: str) -> tuple[str | None, str]:
    """Separa 'Nombre: texto' por el primer ': '. Sin ': ' → mensaje de sistema."""
    idx = rest.find(": ")
    if idx == -1:
        return None, rest
    return rest[:idx], rest[idx + 2:]


def parse_chat(texto: str) -> list[WhatsAppMessage]:
    """Parsea el contenido de un ``_chat.txt`` → lista de mensajes."""
    msgs: list[WhatsAppMessage] = []
    cur: WhatsAppMessage | None = None
    for line in texto.splitlines():
        header = _parse_header(line)
        if header is None:
            if cur is not None:
                cur.texto = cur.texto + "\n" + line
            continue
        date_str, time_str, rest = header
        autor, texto_msg = _split_author(rest)
        cur = WhatsAppMessage(
            timestamp=_parse_dt(date_str, time_str),
            autor=autor,
            texto=texto_msg,
            adjunto_ref=None,
            es_sistema=autor is None,
        )
        msgs.append(cur)
    return msgs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_whatsapp_export.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_export.py tests/test_whatsapp_export.py
git commit -m "feat(whatsapp): parser de export — formato Android básico"
```

---

## Task 2: Parser — formato iOS, multilínea y mensajes de sistema

**Files:**
- Modify: `core/whatsapp_export.py`
- Test: `tests/test_whatsapp_export.py`

- [ ] **Step 1: Write the failing test** (añadir al final de `tests/test_whatsapp_export.py`)

```python
class TestParseIosMultilineaSistema:
    def test_formato_ios_corchetes(self):
        texto = "[8/1/24 10:32:05] Juan Pérez: Hola desde iPhone"
        msgs = parse_chat(texto)
        assert len(msgs) == 1
        assert msgs[0].autor == "Juan Pérez"
        assert msgs[0].texto == "Hola desde iPhone"
        assert msgs[0].timestamp == datetime(2024, 1, 8, 10, 32, 5)

    def test_ios_con_marca_lrm_invisible(self):
        # iOS antepone U+200E (LRM) a algunas líneas.
        texto = "‎[8/1/24 10:32:05] Juan: Hola"
        msgs = parse_chat(texto)
        assert len(msgs) == 1
        assert msgs[0].autor == "Juan"

    def test_mensaje_multilinea(self):
        texto = (
            "8/1/24, 10:32 - Juan: Primera línea\n"
            "segunda línea del mismo mensaje\n"
            "tercera línea\n"
            "8/1/24, 10:33 - Ana: Otro mensaje"
        )
        msgs = parse_chat(texto)
        assert len(msgs) == 2
        assert msgs[0].texto == "Primera línea\nsegunda línea del mismo mensaje\ntercera línea"
        assert msgs[1].texto == "Otro mensaje"

    def test_mensaje_de_sistema(self):
        texto = (
            "8/1/24, 9:00 - Los mensajes y las llamadas están cifrados de "
            "extremo a extremo."
        )
        msgs = parse_chat(texto)
        assert len(msgs) == 1
        assert msgs[0].autor is None
        assert msgs[0].es_sistema is True

    def test_hora_12h_pm(self):
        texto = "8/1/24, 1:05 p. m. - Juan: Tarde"
        msgs = parse_chat(texto)
        assert msgs[0].timestamp == datetime(2024, 1, 8, 13, 5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_whatsapp_export.py::TestParseIosMultilineaSistema -v`
Expected: FAIL (`test_formato_ios_corchetes` y `test_ios_con_marca_lrm_invisible` fallan: el header iOS no se reconoce). El multilínea, sistema y 12h ya pasan con Task 1, pero iOS no.

- [ ] **Step 3: Write minimal implementation** (añadir el regex iOS y usarlo en `_parse_header`)

En `core/whatsapp_export.py`, tras `_RE_ANDROID`, añadir:

```python
# Cabecera iOS:  [d/m/yy[,] HH:MM[:SS][ am/pm]] resto  (puede ir precedida de U+200E)
_RE_IOS = re.compile(
    r"^‎?\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]\.?\s*m\.?)?)\]\s*(.*)$",
    re.IGNORECASE,
)
```

Reemplazar `_parse_header` por:

```python
def _parse_header(line: str) -> tuple[str, str, str] | None:
    """Si la línea abre un mensaje, devuelve (fecha, hora, resto). Si no, None."""
    for rx in (_RE_IOS, _RE_ANDROID):
        m = rx.match(line)
        if m:
            return m.group(1), m.group(2), m.group(3)
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_whatsapp_export.py -v`
Expected: PASS (todos, Task 1 + Task 2).

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_export.py tests/test_whatsapp_export.py
git commit -m "feat(whatsapp): parser — formato iOS, multilínea, mensajes de sistema"
```

---

## Task 3: Parser — referencias a adjuntos y filtro por fechas

**Files:**
- Modify: `core/whatsapp_export.py`
- Test: `tests/test_whatsapp_export.py`

- [ ] **Step 1: Write the failing test** (añadir al final)

```python
from core.whatsapp_export import filter_by_date_range, referencias_adjuntos


class TestAdjuntosYFiltro:
    def test_adjunto_android(self):
        texto = "8/1/24, 10:32 - Juan: IMG-20240108-WA0001.jpg (archivo adjunto)"
        msgs = parse_chat(texto)
        assert msgs[0].adjunto_ref == "IMG-20240108-WA0001.jpg"

    def test_adjunto_ios(self):
        texto = "[8/1/24 10:32:05] Juan: ‎<adjunto: 00000042-PHOTO-2024.jpg>"
        msgs = parse_chat(texto)
        assert msgs[0].adjunto_ref == "00000042-PHOTO-2024.jpg"

    def test_adjunto_con_caption_multilinea(self):
        # El nombre se captura de la primera línea aunque haya caption debajo.
        texto = (
            "8/1/24, 10:32 - Juan: IMG-20240108-WA0001.jpg (archivo adjunto)\n"
            "Mira esta foto"
        )
        msgs = parse_chat(texto)
        assert msgs[0].adjunto_ref == "IMG-20240108-WA0001.jpg"
        assert msgs[0].texto.endswith("Mira esta foto")

    def test_referencias_adjuntos(self):
        texto = (
            "8/1/24, 10:32 - Juan: IMG-1.jpg (archivo adjunto)\n"
            "8/1/24, 10:33 - Juan: Hola\n"
            "8/1/24, 10:34 - Juan: DOC-2.pdf (archivo adjunto)"
        )
        assert referencias_adjuntos(parse_chat(texto)) == ["IMG-1.jpg", "DOC-2.pdf"]

    def test_filter_by_date_range(self):
        texto = (
            "8/1/24, 10:00 - Juan: A\n"
            "9/1/24, 10:00 - Juan: B\n"
            "10/1/24, 10:00 - Juan: C"
        )
        msgs = parse_chat(texto)
        out = filter_by_date_range(
            msgs, desde=datetime(2024, 1, 9), hasta=datetime(2024, 1, 9, 23, 59)
        )
        assert [m.texto for m in out] == ["B"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_whatsapp_export.py::TestAdjuntosYFiltro -v`
Expected: FAIL (`adjunto_ref` siempre None; `referencias_adjuntos`/`filter_by_date_range` no existen).

- [ ] **Step 3: Write minimal implementation**

En `core/whatsapp_export.py`, tras los regex de cabecera, añadir:

```python
# Referencias a adjunto dentro del cuerpo del mensaje.
_RE_ADJ_IOS = re.compile(r"^‎?<adjunto:\s*(.+?)>\s*$", re.IGNORECASE)
_RE_ADJ_ANDROID = re.compile(r"^(.+?)\s*\(archivo adjunto\)\s*$", re.IGNORECASE)


def _adjunto_ref(texto_linea: str) -> str | None:
    """Extrae el nombre del adjunto referenciado en una línea, si lo hay."""
    for rx in (_RE_ADJ_IOS, _RE_ADJ_ANDROID):
        m = rx.match(texto_linea)
        if m:
            return m.group(1).strip()
    return None
```

En `parse_chat`, al construir el mensaje, calcular `adjunto_ref` desde la PRIMERA línea (`texto_msg`), antes de unir continuaciones:

```python
        cur = WhatsAppMessage(
            timestamp=_parse_dt(date_str, time_str),
            autor=autor,
            texto=texto_msg,
            adjunto_ref=_adjunto_ref(texto_msg),
            es_sistema=autor is None,
        )
```

Al final del módulo, añadir las dos funciones públicas:

```python
def referencias_adjuntos(msgs: list[WhatsAppMessage]) -> list[str]:
    """Nombres de fichero referenciados como adjunto, en orden de aparición."""
    return [m.adjunto_ref for m in msgs if m.adjunto_ref]


def filter_by_date_range(
    msgs: list[WhatsAppMessage],
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> list[WhatsAppMessage]:
    """Devuelve los mensajes con timestamp dentro de [desde, hasta] (inclusive).

    Los mensajes sin timestamp se descartan (no se puede ubicarlos en el rango).
    """
    out: list[WhatsAppMessage] = []
    for m in msgs:
        if m.timestamp is None:
            continue
        if desde is not None and m.timestamp < desde:
            continue
        if hasta is not None and m.timestamp > hasta:
            continue
        out.append(m)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_whatsapp_export.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_export.py tests/test_whatsapp_export.py
git commit -m "feat(whatsapp): parser — adjuntos referenciados y filtro por fechas"
```

---

## Task 4: Glue — `analyze` (previsualización, sin escribir)

**Files:**
- Create: `core/whatsapp_intake.py`
- Test: `tests/test_whatsapp_intake.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests del glue de ingesta de WhatsApp (core.whatsapp_intake)."""
from __future__ import annotations

import importlib
import io
import zipfile

import pytest

from core import case_manager


def _make_zip(files: dict[str, bytes]) -> bytes:
    """ZIP en memoria {nombre: contenido}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


_CHAT_TXT = (
    "8/1/24, 10:32 - Juan: Hola\n"
    "8/1/24, 10:33 - Juan: IMG-1.jpg (archivo adjunto)\n"
    "8/1/24, 10:34 - Juan: nota.opus (archivo adjunto)\n"
    "9/1/24, 11:00 - Ana: DOC-2.pdf (archivo adjunto)\n"
).encode("utf-8")


@pytest.fixture(autouse=True)
def _reload_config(tmp_casos_root, monkeypatch):
    from core import config as cfg
    importlib.reload(cfg)
    importlib.reload(case_manager)


def test_analyze_cuenta_mensajes_adjuntos_y_faltantes():
    from core import whatsapp_intake
    importlib.reload(whatsapp_intake)

    # IMG-1.jpg presente; DOC-2.pdf y nota.opus referenciados pero NO incluidos.
    content = _make_zip({"_chat.txt": _CHAT_TXT, "IMG-1.jpg": b"\xff\xd8jpgdata"})
    prev = whatsapp_intake.analyze(content, zip_name="WhatsApp Chat - Juan.zip")

    assert prev.chat_name == "WhatsApp Chat - Juan"
    assert prev.n_mensajes == 4
    assert prev.adjuntos_presentes == ["IMG-1.jpg"]
    assert set(prev.adjuntos_faltantes) == {"DOC-2.pdf", "nota.opus"}
    assert prev.rango_fechas is not None
    assert prev.rango_fechas[0].day == 8 and prev.rango_fechas[1].day == 9


def test_analyze_cuenta_audios():
    from core import whatsapp_intake
    importlib.reload(whatsapp_intake)

    content = _make_zip({
        "_chat.txt": _CHAT_TXT,
        "IMG-1.jpg": b"x",
        "nota.opus": b"audio",
    })
    prev = whatsapp_intake.analyze(content, zip_name="chat.zip")
    assert prev.audios == ["nota.opus"]


def test_analyze_sin_chat_txt_falla():
    from core import whatsapp_intake
    importlib.reload(whatsapp_intake)

    content = _make_zip({"IMG-1.jpg": b"x"})
    with pytest.raises(ValueError, match="_chat.txt"):
        whatsapp_intake.analyze(content, zip_name="chat.zip")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_whatsapp_intake.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'core.whatsapp_intake'`).

- [ ] **Step 3: Write minimal implementation**

```python
"""Glue de ingesta de exports de WhatsApp → ``00_Input/02_Whatsapp/`` (Fase A).

Capa de pegamento entre la UI y el parser puro. NO depende de Streamlit (recibe
bytes + nombre). Deposita el contenido del export verbatim, conserva el zip
original como artefacto de procedencia, registra en ``IntakeManifest`` (dedup por
hash de zip) y emite el evento ``upload_whatsapp``.

Ver ``docs/superpowers/specs/2026-06-15-intake-whatsapp-design.md`` §5.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import WHATSAPP_SUBDIRS, caso_path, settings
from .whatsapp_export import parse_chat, referencias_adjuntos

# Subcarpeta de WhatsApp dentro de 00_Input/ (mismo patrón que _MANUAL_SUBDIR).
_WHATSAPP_SUBDIR = "02_Whatsapp"
# Extensiones consideradas audio (ignoradas por el pipeline; transcripción diferida).
_AUDIO_EXTS = frozenset({".opus", ".ogg", ".m4a", ".aac", ".mp3"})
# Nombre del zip original conservado dentro de la carpeta del chat.
_ORIGINAL_ZIP_NAME = "_export_original.zip"


@dataclass
class ChatPreview:
    """Resumen de un export para la previsualización en la UI (sin escribir)."""
    chat_name: str
    n_mensajes: int
    rango_fechas: tuple[datetime, datetime] | None
    adjuntos_referenciados: list[str]
    adjuntos_presentes: list[str]
    adjuntos_faltantes: list[str]
    audios: list[str]


def _sanitize_name(nombre: str) -> str:
    """Saneo del nombre del chat para usarlo como carpeta. Conserva acentos."""
    base = nombre
    if base.lower().endswith(".zip"):
        base = base[:-4]
    base = base.replace("\\", "_").replace("/", "_")
    for ch in ':*?"<>|':
        base = base.replace(ch, "_")
    base = base.replace("..", "_").strip().strip(".")
    return base or "chat"


def _read_members(content: bytes) -> dict[str, bytes]:
    """Lee un zip en memoria → {nombre_saneado: bytes}. Saneo anti path-traversal.

    Aplana cualquier subcarpeta (los exports de WhatsApp son planos); descarta
    entradas con ``..``, rutas absolutas o componentes vacíos.
    """
    members: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for info in zf.infolist():
            if info.filename.endswith("/"):
                continue
            parts = Path(info.filename).parts
            if any(p in ("..", "") or Path(p).is_absolute() for p in parts):
                continue
            members[Path(info.filename).name] = zf.read(info)
    return members


def _find_chat_txt(members: dict[str, bytes]) -> tuple[str, str]:
    """Localiza el ``.txt`` del chat y lo decodifica. Lanza ValueError si no hay."""
    if "_chat.txt" in members:
        name = "_chat.txt"
    else:
        txts = [n for n in members if n.lower().endswith(".txt")]
        if not txts:
            raise ValueError(
                "El export no contiene ningún _chat.txt (.txt) — "
                "no parece una exportación de WhatsApp."
            )
        name = sorted(txts)[0]
    return name, members[name].decode("utf-8", errors="replace")


def analyze(content: bytes, *, zip_name: str) -> ChatPreview:
    """Analiza un export (.zip) en memoria SIN escribir nada. Para la UI."""
    members = _read_members(content)
    chat_txt_name, texto = _find_chat_txt(members)

    msgs = parse_chat(texto)
    refs = referencias_adjuntos(msgs)

    # Ficheros media presentes = todo menos el .txt del chat.
    presentes = sorted(n for n in members if n != chat_txt_name)
    presentes_set = set(presentes)
    faltantes = [r for r in refs if r not in presentes_set]
    audios = [n for n in presentes if Path(n).suffix.lower() in _AUDIO_EXTS]

    timestamps = [m.timestamp for m in msgs if m.timestamp is not None]
    rango = (min(timestamps), max(timestamps)) if timestamps else None

    return ChatPreview(
        chat_name=_sanitize_name(zip_name),
        n_mensajes=len(msgs),
        rango_fechas=rango,
        adjuntos_referenciados=refs,
        adjuntos_presentes=presentes,
        adjuntos_faltantes=faltantes,
        audios=audios,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_whatsapp_intake.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_intake.py tests/test_whatsapp_intake.py
git commit -m "feat(whatsapp): glue analyze — previsualización + adjuntos faltantes"
```

---

## Task 5: Glue — `deposit_export` (depósito verbatim + manifest + log)

**Files:**
- Modify: `core/whatsapp_intake.py`
- Test: `tests/test_whatsapp_intake.py`

- [ ] **Step 1: Write the failing test** (añadir al final de `tests/test_whatsapp_intake.py`)

```python
class TestDepositExport:
    def _ensure_case(self):
        importlib.reload(case_manager)
        case_manager.ensure_case("WA-2026-001", titulo="Caso WhatsApp test")
        return "WA-2026-001"

    def test_deposita_verbatim_y_conserva_zip(self):
        from core import whatsapp_intake
        importlib.reload(whatsapp_intake)
        case_id = self._ensure_case()

        content = _make_zip({"_chat.txt": _CHAT_TXT, "IMG-1.jpg": b"jpgdata"})
        res = whatsapp_intake.deposit_export(
            case_id, "02_Grupo operacion", content, zip_name="Grupo Valldaura.zip"
        )

        assert res.skipped_dedup is False
        chat_dir = (
            caso_path(case_id) / "00_Input" / "02_Whatsapp"
            / "02_Grupo operacion" / "Grupo Valldaura"
        )
        assert res.chat_dir == chat_dir
        assert (chat_dir / "_chat.txt").read_bytes() == _CHAT_TXT
        assert (chat_dir / "IMG-1.jpg").read_bytes() == b"jpgdata"
        # El zip original se conserva.
        assert (chat_dir / "_export_original.zip").exists()

    def test_rol_invalido_falla(self):
        from core import whatsapp_intake
        importlib.reload(whatsapp_intake)
        case_id = self._ensure_case()
        content = _make_zip({"_chat.txt": _CHAT_TXT})
        with pytest.raises(ValueError, match="rol"):
            whatsapp_intake.deposit_export(
                case_id, "99_Inexistente", content, zip_name="x.zip"
            )

    def test_caso_inexistente_falla(self):
        from core import whatsapp_intake
        importlib.reload(whatsapp_intake)
        content = _make_zip({"_chat.txt": _CHAT_TXT})
        with pytest.raises(FileNotFoundError):
            whatsapp_intake.deposit_export(
                "NO-EXISTE", "03_Otros", content, zip_name="x.zip"
            )

    def test_registra_manifest_y_emite_evento(self):
        from core import whatsapp_intake, intake_log
        from core.intake_manifest import IntakeManifest, compute_sha256_bytes
        importlib.reload(whatsapp_intake)
        case_id = self._ensure_case()

        content = _make_zip({"_chat.txt": _CHAT_TXT, "IMG-1.jpg": b"jpgdata"})
        whatsapp_intake.deposit_export(
            case_id, "00_Consultor propietario", content, zip_name="Juan.zip"
        )

        with IntakeManifest(case_id) as m:
            # El hash del zip queda registrado (llave de dedup de importación).
            assert m.lookup(compute_sha256_bytes(content)) is not None
            # Y los ficheros internos también.
            assert m.lookup(compute_sha256_bytes(b"jpgdata")) is not None

        eventos = intake_log.read_events(case_id)
        assert any(e["event"] == "upload_whatsapp" for e in eventos)

    def test_rango_fechas_genera_recortado(self):
        from core import whatsapp_intake
        importlib.reload(whatsapp_intake)
        case_id = self._ensure_case()

        content = _make_zip({"_chat.txt": _CHAT_TXT})
        res = whatsapp_intake.deposit_export(
            case_id, "03_Otros", content, zip_name="c.zip",
            date_range=(datetime(2024, 1, 9), datetime(2024, 1, 9, 23, 59)),
        )
        recortado = res.chat_dir / "_chat_recortado.txt"
        assert recortado.exists()
        # El original íntegro sigue presente.
        assert (res.chat_dir / "_chat.txt").read_bytes() == _CHAT_TXT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_whatsapp_intake.py::TestDepositExport -v`
Expected: FAIL (`deposit_export` / `DepositResult` no existen).

- [ ] **Step 3: Write minimal implementation**

En `core/whatsapp_intake.py`, ampliar imports:

```python
from . import intake_log
from .intake_manifest import IntakeManifest, compute_sha256_bytes
from .whatsapp_export import filter_by_date_range, parse_chat, referencias_adjuntos
```

Añadir el dataclass de resultado tras `ChatPreview`:

```python
@dataclass
class DepositResult:
    """Resultado de depositar un export en el caso."""
    chat_dir: Path
    preview: ChatPreview
    files_written: list[Path] = field(default_factory=list)
    skipped_dedup: bool = False
```

Añadir la función al final del módulo:

```python
def deposit_export(
    case_id: str,
    rol_subdir: str,
    content: bytes,
    *,
    zip_name: str,
    date_range: tuple[datetime | None, datetime | None] | None = None,
) -> DepositResult:
    """Deposita un export de WhatsApp en ``00_Input/02_Whatsapp/<rol>/<chat>/``.

    Verbatim: escribe el ``_chat.txt`` + todos los media + el zip original. Dedup
    por hash de zip: si ese export ya se importó, no escribe nada y devuelve
    ``skipped_dedup=True``. Registra cada fichero en el manifest y emite el evento
    ``upload_whatsapp``. Si ``date_range`` se da, añade ``_chat_recortado.txt``.
    """
    if rol_subdir not in WHATSAPP_SUBDIRS:
        raise ValueError(
            f"rol_subdir inválido: {rol_subdir!r}. "
            f"Válidos: {WHATSAPP_SUBDIRS}"
        )
    case_dir = caso_path(case_id)
    if not case_dir.exists():
        raise FileNotFoundError(
            f"El caso '{case_id}' no existe en {settings.casos_root}. "
            "Llama a ensure_case() antes de deposit_export()."
        )

    preview = analyze(content, zip_name=zip_name)
    chat_dir = case_dir / "00_Input" / _WHATSAPP_SUBDIR / rol_subdir / preview.chat_name
    zip_sha = compute_sha256_bytes(content)
    members = _read_members(content)
    chat_txt_name, texto = _find_chat_txt(members)

    files_written: list[Path] = []
    with IntakeManifest(case_id) as manifest:
        # Dedup de importación: mismo export ya visto → no reescribir.
        if manifest.lookup(zip_sha) is not None:
            return DepositResult(
                chat_dir=chat_dir, preview=preview, skipped_dedup=True
            )

        chat_dir.mkdir(parents=True, exist_ok=True)

        # 1) Contenido verbatim (todos los ficheros del export).
        rel_base = f"{_WHATSAPP_SUBDIR}/{rol_subdir}/{preview.chat_name}"
        for name, data in members.items():
            dest = chat_dir / name
            dest.write_bytes(data)
            files_written.append(dest)
            manifest.register(
                compute_sha256_bytes(data),
                f"{rel_base}/{name}",
                source="whatsapp",
                chat=preview.chat_name,
            )

        # 2) Zip original como artefacto de procedencia + llave de dedup.
        zip_dest = chat_dir / _ORIGINAL_ZIP_NAME
        zip_dest.write_bytes(content)
        files_written.append(zip_dest)
        manifest.register(
            zip_sha, f"{rel_base}/{_ORIGINAL_ZIP_NAME}",
            source="whatsapp", chat=preview.chat_name, es_zip_origen=True,
        )

        # 3) Recorte opcional por fechas (aditivo, nunca sustituye al original).
        if date_range is not None:
            desde, hasta = date_range
            recortados = filter_by_date_range(parse_chat(texto), desde, hasta)
            lineas = [
                f"[{m.timestamp}] {m.autor or '(sistema)'}: {m.texto}"
                for m in recortados
            ]
            rec_dest = chat_dir / "_chat_recortado.txt"
            rec_dest.write_text("\n".join(lineas), encoding="utf-8")
            files_written.append(rec_dest)

    intake_log.append_event(
        case_id,
        "upload_whatsapp",
        details={
            "chat": preview.chat_name,
            "rol": rol_subdir,
            "n_mensajes": preview.n_mensajes,
            "adjuntos_presentes": len(preview.adjuntos_presentes),
            "adjuntos_faltantes": preview.adjuntos_faltantes,
            "audios": len(preview.audios),
            "zip_sha256": zip_sha,
        },
    )

    return DepositResult(
        chat_dir=chat_dir, preview=preview, files_written=files_written,
        skipped_dedup=False,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_whatsapp_intake.py -v`
Expected: PASS (todos: Task 4 + Task 5).

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_intake.py tests/test_whatsapp_intake.py
git commit -m "feat(whatsapp): deposit_export — depósito verbatim + zip + manifest + log"
```

---

## Task 6: Glue — dedup por hash de zip (re-importación)

**Files:**
- Test: `tests/test_whatsapp_intake.py` (solo test; el comportamiento ya está implementado en Task 5 — este test lo blinda contra regresiones)

- [ ] **Step 1: Write the failing test** (añadir al final, dentro de `TestDepositExport`)

```python
    def test_reimportar_mismo_zip_se_salta(self):
        from core import whatsapp_intake
        importlib.reload(whatsapp_intake)
        case_id = self._ensure_case()

        content = _make_zip({"_chat.txt": _CHAT_TXT, "IMG-1.jpg": b"jpgdata"})
        first = whatsapp_intake.deposit_export(
            case_id, "03_Otros", content, zip_name="dup.zip"
        )
        assert first.skipped_dedup is False

        second = whatsapp_intake.deposit_export(
            case_id, "03_Otros", content, zip_name="dup.zip"
        )
        assert second.skipped_dedup is True
        assert second.files_written == []
```

- [ ] **Step 2: Run test to verify it passes** (debe pasar ya, gracias a Task 5)

Run: `python -m pytest tests/test_whatsapp_intake.py::TestDepositExport::test_reimportar_mismo_zip_se_salta -v`
Expected: PASS. Si falla, revisar que `deposit_export` consulta `manifest.lookup(zip_sha)` **antes** de escribir.

- [ ] **Step 3: Commit**

```bash
git add tests/test_whatsapp_intake.py
git commit -m "test(whatsapp): blinda el dedup por hash de zip en re-importación"
```

---

## Task 7: UI Streamlit — expander de importación (verificación manual)

**Files:**
- Modify: `streamlit_app.py` (tras el expander «📄 Demanda / documentos judiciales», ~línea 617, antes de `st.divider()` que precede a «📂 Subir al árbol CRM»)

> Nota: la UI no tiene unit tests en este repo (patrón establecido). Se verifica manualmente. La lógica está toda en el core; aquí solo orquestación.

- [ ] **Step 1: Asegurar el import del módulo**

En la cabecera de `streamlit_app.py`, junto a `from core import intake_manual` (línea 28), añadir:

```python
from core import whatsapp_intake
```

- [ ] **Step 2: Añadir el expander**

Insertar este bloque dentro del mismo `with` del tab Casos donde viven los otros expanders (mismo nivel de indentación que `with st.expander("📄 Demanda / documentos judiciales"):`):

```python
        st.divider()
        with st.expander("📲 Importar chat de WhatsApp"):
            _caso_wa = st.selectbox(
                "Caso",
                cases,
                key="casos_wa_sel",
                help="Caso al que se asociarán los chats de WhatsApp.",
            )
            _uploaded_wa = st.file_uploader(
                "Subir export(s) de WhatsApp",
                accept_multiple_files=True,
                type=["zip"],
                key="casos_wa_uploader",
                help=(
                    "Usa «Exportar chat → incluir multimedia» en WhatsApp y sube "
                    "el/los .zip resultantes. Se guardan en `00_Input/02_Whatsapp/`."
                ),
            )

            _wa_roles = [
                "00_Consultor propietario",
                "01_Consultor buscador",
                "02_Grupo operacion",
                "03_Otros",
            ]

            for _i, _uf_wa in enumerate(_uploaded_wa or []):
                _raw_wa = _uf_wa.read()
                try:
                    _prev = whatsapp_intake.analyze(_raw_wa, zip_name=_uf_wa.name)
                except Exception as _exc_wa:
                    st.error(f"❌ **{_uf_wa.name}**: {_exc_wa}")
                    continue

                st.markdown(f"**{_prev.chat_name}**")
                _rango = (
                    f"{_prev.rango_fechas[0]:%d/%m/%Y} – {_prev.rango_fechas[1]:%d/%m/%Y}"
                    if _prev.rango_fechas else "—"
                )
                st.caption(
                    f"· {_prev.n_mensajes} mensajes · rango {_rango} · "
                    f"{len(_prev.adjuntos_presentes)} adjuntos · "
                    f"{len(_prev.audios)} audios (transcripción diferida)"
                )
                if _prev.adjuntos_faltantes:
                    st.warning(
                        f"⚠️ Faltan {len(_prev.adjuntos_faltantes)} adjuntos que "
                        f"WhatsApp no incluyó en el export "
                        f"(p. ej. {', '.join(_prev.adjuntos_faltantes[:3])}…). "
                        "Pide un re-export o los ficheros sueltos si son relevantes."
                    )
                _rol_wa = st.selectbox(
                    "Rol / subcarpeta",
                    _wa_roles,
                    key=f"casos_wa_rol_{_i}",
                )

                if st.button(
                    f"⬆️ Importar «{_prev.chat_name}»",
                    key=f"casos_wa_btn_{_i}",
                ):
                    try:
                        _res = whatsapp_intake.deposit_export(
                            _caso_wa, _rol_wa, _raw_wa, zip_name=_uf_wa.name
                        )
                        if _res.skipped_dedup:
                            st.info(
                                f"↩️ «{_prev.chat_name}» ya estaba importado "
                                "(mismo export). No se ha duplicado."
                            )
                        else:
                            st.success(
                                f"✅ «{_prev.chat_name}» importado en "
                                f"`02_Whatsapp/{_rol_wa}/` "
                                f"({len(_res.files_written)} ficheros)."
                            )
                    except Exception as _exc_dep:
                        st.error(f"❌ Error importando «{_prev.chat_name}»: {_exc_dep}")
                st.divider()
```

- [ ] **Step 3: Verificación manual**

Run: `python -m streamlit run streamlit_app.py`
Pasos: tab Casos → «📲 Importar chat de WhatsApp» → subir un `.zip` de export real → comprobar que la tarjeta muestra nº de mensajes, rango, adjuntos y aviso de faltantes; elegir rol; pulsar Importar → verificar en disco que `00_Input/02_Whatsapp/<rol>/<chat>/` contiene `_chat.txt`, los media, `_export_original.zip`; volver a importar el mismo zip → mensaje «ya estaba importado».

- [ ] **Step 4: Commit**

```bash
git add streamlit_app.py
git commit -m "feat(whatsapp): expander de importación de chats en el tab Casos"
```

---

## Task 8: Cierre — suite verde y actualización de planificación

**Files:**
- Modify: `PLAN.md`
- Modify: `docs/MEJORAS_FUTURAS.md` (si procede anotar Fase B / transcripción de audio como diferidos)

- [ ] **Step 1: Suite completa verde**

Run: `python -m pytest -q --tb=no`
Expected: PASS, sin regresiones (el número total debe subir respecto a 935 por los tests nuevos de Task 1-6; cualquier fallo nuevo se investiga antes de cerrar).

- [ ] **Step 2: Actualizar `PLAN.md`**

Añadir entrada nueva (o anexo al bloque de intake) registrando: Fase A de intake WhatsApp COMPLETA (parser `whatsapp_export` + glue `whatsapp_intake` + expander Streamlit), con los hashes de commit de Task 1-7; Fase B (email) y transcripción de audio quedan diferidas.

- [ ] **Step 3: Commit**

```bash
git add PLAN.md docs/MEJORAS_FUTURAS.md
git commit -m "docs(intake-whatsapp): Fase A completa — planificación al día"
```

---

## Self-Review (rellenada por el autor del plan)

**Spec coverage:**
- §3 arquitectura 3 capas → Tasks 1-3 (parser), 4-6 (glue), 7 (UI). ✓
- §3.1 reutiliza andamiaje (`WHATSAPP_SUBDIRS`, `source="whatsapp"`, `upload_whatsapp`, dedup) → Task 5 lo consume. ✓
- §4 parser (formatos iOS/Android, multilínea, sistema, adjuntos, rango) → Tasks 1-3. ✓
- §5.1 depósito verbatim + zip original → Task 5. ✓
- §5.2 detección de adjuntos faltantes → Task 4 (`analyze`) + Task 7 (aviso UI). ✓
- §5.3 dedup por hash de zip + registro por fichero + evento → Tasks 5-6. ✓
- §5.4 recorte opcional por fechas → Task 5 (`date_range`). ✓
- §5.5 audio diferido (contado, no transcrito) → Task 4 (conteo) + Task 7 (etiqueta). ✓
- §6 UI: multi-zip, un caso por lote, rol por chat, previsualización por chat → Task 7. ✓
- §8 tests → Tasks 1-6. §7 RGPD: sin LLM en ingesta → ningún task llama a LLM. ✓

**Placeholder scan:** sin TBD/TODO; todo step de código lleva código completo. ✓

**Type consistency:** `WhatsAppMessage(timestamp, autor, texto, adjunto_ref, es_sistema)` consistente entre Tasks 1-3 y el glue. `analyze(content, *, zip_name) -> ChatPreview` y `deposit_export(case_id, rol_subdir, content, *, zip_name, date_range) -> DepositResult` consistentes entre Tasks 4-7 y la UI. `DepositResult.skipped_dedup`/`.files_written`/`.chat_dir`/`.preview` y `ChatPreview.chat_name`/`.n_mensajes`/`.rango_fechas`/`.adjuntos_presentes`/`.adjuntos_faltantes`/`.audios` usados igual en tests y UI. ✓
