# Layout de `00_Input` por lotes de entrega — plan de implementación (MEJORAS #54)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar la spec rev 2 (`docs/superpowers/specs/2026-07-17-layout-00-input-lotes-design.md`,
PR #49, `32fa663` en `main`): los canales de ENTREGA (`whatsapp`, `email`, `manual`, `entrevista`)
depositan cada intake en un lote append-only `00_Input/<AAAA-MM-DD>_<fuente>_<NN>/` con
`_manifiesto.yaml`; los canales ESPEJO (`01_Drive EV`, `05_CRM`) no se tocan; dedup cross-lote
vía M9 + Message-ID (el duplicado SE COPIA y se anota); migración bajo demanda con remapeo.

**Architecture:** Módulo core nuevo `core/intake_lotes.py` (naming + reserva atómica + manifiesto +
`clasificar_tipo_contenido` + `fuente_de`); M9 (`core/intake_manifest.py`) extendido con `message_id`
y el helper `duplicado_de_para`; los 5 escritores de entrega migran a lote; los lectores adoptan el
descubrimiento mínimo; script de migración bajo demanda con cerebro puro (`core/migrar_layout.py`).
Patrón del repo: cerebro puro + orquestadores finos; TDD por tarea.

**Tech Stack:** Python 3 (venv `.venv/`), pytest, PyYAML, Typer (CLI), Windows/PowerShell.

## Global Constraints

*(La spec es la ÚNICA fuente de verdad del diseño. Las 4 decisiones de Nikolai de su §2 no se
reabren: espejos fuera; M9 índice único; duplicados se copian; migración remapea.)*

- **Espejos intactos:** `core/intake_drive.py`, `core/sync_sudespacho.py` (pull v2),
  `core/judicial_intake.py`, `intake_manual.save_file_crm_branch`, `core/local_organizer.py`
  NO cambian su mecanismo `.pulled`/`reconcile` ni su cajón (`01_Drive EV`, `05_CRM`).
- **Fuera de alcance** (spec §10): reenganche fino de `email_atomize`/`sala_maquina`/motor de sala
  de lectura (#55/#56); escritor `entrevista` (#53); limpieza de cajones vacíos post-migración;
  barrido retroactivo; cambios de esquema en `_intake_log.jsonl`.
- Vocabulario de fuente de lote (spec §4): `whatsapp | email | manual | entrevista` — canónico
  **singular** `entrevista`. Nombre de lote: `<AAAA-MM-DD>_<fuente>_<NN>` (`NN` 2 dígitos, sube).
- Vocabulario `tipo_contenido` (spec §5, eje TIPO, no procedencia):
  `pdf | imagen | video | audio | docx | txt | eml | whatsapp | otros` (`whatsapp` solo `_chat.txt`).
- Dedup (spec §6): fuente única M9. Duplicado detectado → **se copia igualmente** +
  `duplicado_de: <lote>/<relpath>`. Tamaño 0 nunca marca duplicado. Mismo sha intra-lote: se copia
  y se anota. Espejos: su dedup sigue siendo su sync.
- `00_Input` append-only; el guard §6 (`dir_intake`/`guard_escritura`/bandeja `_pendiente_checkin`)
  no cambia de semántica; `_intake_log.jsonl` sin cambios de esquema.
- `core/anon/` no se toca. `data/CASOS/` gitignored; tests SOLO con datos sintéticos (sin PII).
- Entorno: Windows + PowerShell; UTF-8 sin BOM. Conteo de pytest SIEMPRE vía `--junit-xml`
  (la línea de resumen no se captura por tuberías en este Windows — `docs/DEAD_ENDS.md`).
- Git: rama nueva desde `main` (p. ej. `claude/input-lotes-f1`), commits acotados por tarea
  (nunca `add -A`), PR a `main` con check `leak-scan`. Instalar hooks en el worktree:
  `pre-commit install && pre-commit install --hook-type pre-push`.
- Comando de test por tarea (desde la raíz del repo):
  `python -m pytest <fichero>::<test> -q --tb=short --junit-xml=.pytest-task.xml`
  y verificar `failures="0" errors="0"` en el XML. `.pytest-task.xml` no se commitea.

## Estructura de ficheros (mapa del cambio)

| Fichero | Acción | Responsabilidad |
|---|---|---|
| `core/config.py` | Modificar | `FUENTES_LOTE`, `ESPEJO_SUBDIRS`, `INTAKE_CONTROL_FILES` (lista única) |
| `core/intake_lotes.py` | **Crear** | Naming/reserva de lote, manifiesto, `clasificar_tipo_contenido`, `fuente_de` |
| `core/intake_manifest.py` | Modificar | M9: `message_id`, `lookup_message_id`, `message_ids`, `duplicado_de_para` |
| `core/whatsapp_intake.py` | Modificar | Escritor whatsapp → lote |
| `core/intake_manual.py` | Modificar | Escritor manual → lote (`abrir_lote_manual`, `save_file`/`extract_zip` con `lote`) |
| `core/email_export.py` | Modificar | Estado de canal a raíz de `00_Input`, dedup por M9/Message-ID, lote por corrida, índices cross-lote |
| `core/abrir_caso.py` + `scripts/abrir_caso.py` | Modificar | Vías manual/email por lote; fin de `FUENTE_A_SUBDIR` |
| `core/case_manager.py` | Modificar | `ensure_case` eager→lazy en cajones de entrega |
| `core/inventory.py`, `core/catalogo_documental.py` | Modificar | Adoptan `fuente_de`; `entrevista` singular |
| `core/whatsapp_atomize/pipeline.py`, `core/email_atomize/pipeline.py` | Modificar | Descubrimiento en lotes + cajón legacy |
| `core/migrar_layout.py` | **Crear** | Cerebro puro de la migración (plan + remapeos) |
| `scripts/migrar_layout_intake.py` | **Crear** | CLI de migración bajo demanda |
| `streamlit_app.py` | Modificar | Un lote manual por clic de «Guardar documentos» |
| `.claude/skills/…` (6 skills) | Modificar | Textos al modelo de lote + re-empaquetado |
| `tests/test_intake_lotes.py`, `tests/test_migrar_layout.py` | **Crear** | Suites nuevas |

---

### Task 1: Config — vocabulario de lote + lista única de ficheros de control

**Files:**
- Modify: `core/config.py` (tras `EMAIL_SUBDIRS`, ~línea 410)
- Modify: `core/inventory.py:47`, `core/intake_manual.py:37`, `core/intake_drive.py:64`
- Test: `tests/test_intake_lotes.py` (crear)

**Interfaces:**
- Produces: `config.FUENTES_LOTE: tuple[str, ...]` = `("whatsapp", "email", "manual", "entrevista")`;
  `config.ESPEJO_SUBDIRS: tuple[str, ...]` = `("01_Drive EV", "05_CRM")`;
  `config.INTAKE_CONTROL_FILES: frozenset[str]` = `{".pulled", ".synced", "_inventory.json",
  "_exported_ids.json", "_resolved_links.json"}`.
- `intake_drive.CONTROL_FILES` (API pública existente) pasa a ser alias de
  `config.INTAKE_CONTROL_FILES`; ídem `inventory._CONTROL_FILES` e `intake_manual._CONTROL_FILES`.

- [ ] **Step 1: Test que falla**

```python
# tests/test_intake_lotes.py
"""Layout de 00_Input por lotes (MEJORAS #54, spec 2026-07-17 rev 2)."""
from __future__ import annotations


def test_fuentes_lote_sin_espejos():
    from core import config
    assert config.FUENTES_LOTE == ("whatsapp", "email", "manual", "entrevista")
    assert "drive_ev" not in config.FUENTES_LOTE and "crm" not in config.FUENTES_LOTE
    assert config.ESPEJO_SUBDIRS == ("01_Drive EV", "05_CRM")


def test_lista_unica_de_ficheros_de_control():
    from core import config, intake_drive, intake_manual, inventory
    assert intake_drive.CONTROL_FILES == config.INTAKE_CONTROL_FILES
    assert inventory._CONTROL_FILES == config.INTAKE_CONTROL_FILES
    assert intake_manual._CONTROL_FILES == config.INTAKE_CONTROL_FILES
    # Los índices del canal email también son control (spec §5).
    assert {"_exported_ids.json", "_resolved_links.json", ".pulled", ".synced",
            "_inventory.json"} <= set(config.INTAKE_CONTROL_FILES)
```

- [ ] **Step 2: Run** `python -m pytest tests/test_intake_lotes.py -q --tb=short --junit-xml=.pytest-task.xml`
  — Expected: FAIL (`AttributeError: FUENTES_LOTE`).

- [ ] **Step 3: Implementación mínima**

En `core/config.py`, tras `EMAIL_SUBDIRS`:

```python
# --- Lotes de entrega en 00_Input (MEJORAS #54, spec 2026-07-17 rev 2) -------

# Fuentes que forman LOTE de entrega (00_Input/<AAAA-MM-DD>_<fuente>_<NN>/).
# 'drive_ev' y 'crm' NO están: son canales ESPEJO (cajón fijo + sync incremental).
# 'entrevista' se reserva aunque hoy no tiene escritor (#53).
FUENTES_LOTE: tuple[str, ...] = ("whatsapp", "email", "manual", "entrevista")

# Cajones espejo: no forman lotes, su sync no se toca.
ESPEJO_SUBDIRS: tuple[str, ...] = ("01_Drive EV", "05_CRM")

# Ficheros de control del intake: NUNCA son documento ni entran en manifiestos
# de lote. Lista ÚNICA (antes: copias en inventory/intake_manual/intake_drive).
INTAKE_CONTROL_FILES: frozenset[str] = frozenset({
    ".pulled", ".synced", "_inventory.json",
    "_exported_ids.json", "_resolved_links.json",
})
```

Recableado (conservando los nombres públicos):

```python
# core/intake_drive.py:64  (mantener _PULL_MARKER = ".pulled" como constante propia)
CONTROL_FILES: frozenset[str] = INTAKE_CONTROL_FILES        # import desde .config

# core/inventory.py:47
_CONTROL_FILES = INTAKE_CONTROL_FILES                       # import desde .config

# core/intake_manual.py:37
_CONTROL_FILES = INTAKE_CONTROL_FILES                       # import desde .config
```

- [ ] **Step 4: Run** el mismo comando — Expected: PASS. Correr también
  `python -m pytest tests/test_intake_drive.py tests/test_inventory.py tests/test_intake_manual.py tests/test_abrir_caso.py -q --tb=short --junit-xml=.pytest-task.xml`
  (consumidores de `CONTROL_FILES`, p. ej. `scripts/abrir_caso.py::hash_tree_local`) — Expected: verde.
  Si algún test asertaba el contenido EXACTO de la lista vieja, actualizarlo a la nueva.

- [ ] **Step 5: Commit** `git add core/config.py core/inventory.py core/intake_manual.py core/intake_drive.py tests/test_intake_lotes.py && git commit -m "feat(intake): vocabulario FUENTES_LOTE + lista unica INTAKE_CONTROL_FILES (MEJORAS #54 T1)"`

---

### Task 2: `core/intake_lotes.py` — patrón de nombre + reserva atómica de lote

**Files:**
- Create: `core/intake_lotes.py`
- Test: `tests/test_intake_lotes.py`

**Interfaces:**
- Consumes: `config.FUENTES_LOTE`, `config.PENDIENTE_CHECKIN_SUBDIR`, `config.caso_path`,
  `case_manager.dir_intake(case_id, rel_base, origen)` (existente, `core/case_manager.py:719`).
- Produces:
  - `PATRON_LOTE: re.Pattern` — casa `^(\d{4}-\d{2}-\d{2})_(whatsapp|email|manual|entrevista)_(\d{2,})$`;
    grupo 2 = fuente.
  - `MANIFIESTO_LOTE = "_manifiesto.yaml"`.
  - `reservar_lote(case_id: str, fuente: str, origen: str, *, hoy: datetime.date | None = None) -> Path`
    — crea y devuelve el directorio del lote (bajo `00_Input/` o desviado a la bandeja por el guard).
    `ValueError` si `fuente not in FUENTES_LOTE`.

- [ ] **Step 1: Tests que fallan** (añadir a `tests/test_intake_lotes.py`)

```python
import importlib
from datetime import date

import pytest

from core import case_manager, config

HOY = date(2026, 7, 17)


@pytest.fixture(autouse=True)
def _reload(tmp_casos_root):
    importlib.reload(config)
    importlib.reload(case_manager)


def _caso(case_id="EV-2026-100"):
    case_manager.ensure_case(case_id, titulo="Lotes")
    return case_id


def test_reservar_lote_formato_y_creacion(tmp_casos_root):
    from core import intake_lotes
    case_id = _caso()
    lote = intake_lotes.reservar_lote(case_id, "whatsapp", "whatsapp", hoy=HOY)
    assert lote.name == "2026-07-17_whatsapp_01"
    assert lote.parent == config.caso_path(case_id) / "00_Input"
    assert lote.is_dir()
    assert intake_lotes.PATRON_LOTE.match(lote.name).group(2) == "whatsapp"


def test_reservar_lote_colision_mismo_dia_sube_nn(tmp_casos_root):
    from core import intake_lotes
    case_id = _caso()
    l1 = intake_lotes.reservar_lote(case_id, "manual", "manual", hoy=HOY)
    l2 = intake_lotes.reservar_lote(case_id, "manual", "manual", hoy=HOY)
    assert (l1.name, l2.name) == ("2026-07-17_manual_01", "2026-07-17_manual_02")


def test_reservar_lote_rechaza_espejos(tmp_casos_root):
    from core import intake_lotes
    case_id = _caso()
    for fuente in ("drive_ev", "crm"):
        with pytest.raises(ValueError):
            intake_lotes.reservar_lote(case_id, fuente, fuente, hoy=HOY)


def test_contador_cuenta_lotes_de_la_bandeja(tmp_casos_root):
    # Un intake sobre caso prestado deja su lote en _pendiente_checkin/<origen>/00_Input/;
    # si el contador no lo viera, el checkin fusionaría dos lotes homónimos (spec §4).
    from core import intake_lotes
    case_id = _caso()
    bandeja = (config.caso_path(case_id) / config.PENDIENTE_CHECKIN_SUBDIR
               / "manual" / "00_Input" / "2026-07-17_manual_01")
    bandeja.mkdir(parents=True)
    lote = intake_lotes.reservar_lote(case_id, "manual", "manual", hoy=HOY)
    assert lote.name == "2026-07-17_manual_02"


def test_reserva_atomica_por_mkdir(tmp_casos_root, monkeypatch):
    # Carrera: otro proceso creó el dir entre el escaneo y el mkdir → se prueba NN+1.
    from core import intake_lotes
    case_id = _caso()
    (config.caso_path(case_id) / "00_Input" / "2026-07-17_manual_01").mkdir()
    monkeypatch.setattr(intake_lotes, "_lotes_existentes", lambda case_dir: set())
    lote = intake_lotes.reservar_lote(case_id, "manual", "manual", hoy=HOY)
    assert lote.name == "2026-07-17_manual_02"
```

- [ ] **Step 2: Run** `python -m pytest tests/test_intake_lotes.py -q --tb=short --junit-xml=.pytest-task.xml`
  — Expected: FAIL (`ModuleNotFoundError: core.intake_lotes`).

- [ ] **Step 3: Implementación**

```python
# core/intake_lotes.py
"""Lotes de entrega en ``00_Input`` (MEJORAS #54, spec 2026-07-17 rev 2).

Canales de ENTREGA (``whatsapp``, ``email``, ``manual``, ``entrevista``): cada
intake es su propia subcarpeta ``00_Input/<AAAA-MM-DD>_<fuente>_<NN>/`` con un
``_manifiesto.yaml`` (albarán forense de la entrega — NO fuente de dedup, eso
es M9). Canales ESPEJO (``01_Drive EV``, ``05_CRM``): cajón fijo, aquí no se
tocan.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from . import config
from .config import caso_path

MANIFIESTO_LOTE = "_manifiesto.yaml"

PATRON_LOTE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})_(whatsapp|email|manual|entrevista)_(\d{2,})$"
)


def _lotes_existentes(case_dir: Path) -> set[str]:
    """Nombres de lote presentes en 00_Input/ Y en la bandeja _pendiente_checkin.

    El contador mira también la bandeja (spec §4): un intake sobre caso
    prestado se desvía ahí con su nombre de lote.
    """
    raices = [case_dir / "00_Input"]
    bandeja = case_dir / config.PENDIENTE_CHECKIN_SUBDIR
    if bandeja.is_dir():
        raices += [d / "00_Input" for d in bandeja.iterdir() if d.is_dir()]
    nombres: set[str] = set()
    for raiz in raices:
        if not raiz.is_dir():
            continue
        nombres |= {p.name for p in raiz.iterdir()
                    if p.is_dir() and PATRON_LOTE.match(p.name)}
    return nombres


def reservar_lote(case_id: str, fuente: str, origen: str,
                  *, hoy: date | None = None) -> Path:
    """Reserva (mkdir atómico) y devuelve el directorio del siguiente lote.

    Aplica el guard §6 vía ``dir_intake``: caso prestado/conflicto → el lote
    nace en la bandeja. La reserva es atómica: si el mkdir colisiona (dos
    sesiones concurrentes sobre un caso *disponible*), se prueba ``NN+1``.
    """
    if fuente not in config.FUENTES_LOTE:
        raise ValueError(
            f"Fuente de lote inválida: {fuente!r}. Válidas: {config.FUENTES_LOTE}. "
            "Los espejos (drive_ev, crm) no forman lotes."
        )
    from .case_manager import dir_intake  # import local: evita ciclo config↔case_manager

    fecha = (hoy or date.today()).isoformat()
    ocupados = _lotes_existentes(caso_path(case_id))
    nn = 1
    while True:
        nombre = f"{fecha}_{fuente}_{nn:02d}"
        if nombre in ocupados:
            nn += 1
            continue
        destino = dir_intake(case_id, f"00_Input/{nombre}", origen)
        try:
            destino.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            nn += 1
            continue
        return destino
```

- [ ] **Step 4: Run** el mismo comando — Expected: PASS.

- [ ] **Step 5: Commit** `git add core/intake_lotes.py tests/test_intake_lotes.py && git commit -m "feat(intake): reserva atomica de lote AAAA-MM-DD_fuente_NN con contador sobre bandeja (T2)"`

---

### Task 3: `intake_lotes` — `clasificar_tipo_contenido` + manifiesto de lote

**Files:**
- Modify: `core/intake_lotes.py`
- Test: `tests/test_intake_lotes.py`

**Interfaces:**
- Produces:
  - `clasificar_tipo_contenido(nombre: str) -> str` — por extensión; vocabulario del eje TIPO
    (Global Constraints); `_chat.txt` → `whatsapp`; desconocido → `otros`.
  - `@dataclass ItemManifiesto(relpath: str, sha256: str, size: int, tipo_contenido: str,
    message_id: str | None = None, duplicado_de: str | None = None)` — `relpath` POSIX relativo
    a la raíz DEL LOTE.
  - `escribir_manifiesto(lote_dir: Path, *, fuente: str, fecha_intake: str, origen: str,
    items: list[ItemManifiesto], fecha_intake_estimada: bool = False) -> Path` — escribe
    `_manifiesto.yaml` (UTF-8; claves None omitidas; items ordenados por relpath).
  - `anexar_items(lote_dir: Path, items: list[ItemManifiesto], *, origen: str) -> Path` —
    crea el manifiesto si falta (fuente+fecha derivadas de `PATRON_LOTE` sobre el nombre del dir)
    y fusiona por `relpath` (el nuevo gana). Para escritores incrementales (manual).
  - `leer_manifiesto(lote_dir: Path) -> dict | None`.
  - `items_desde_disco(lote_dir: Path, *, message_id_de: dict[str, str] | None = None,
    duplicados: dict[str, str] | None = None) -> list[ItemManifiesto]` — inventaría el lote
    excluyendo `config.INTAKE_CONTROL_FILES` y `_manifiesto.yaml` (los dicts opcionales van
    indexados por relpath). `_export_original.zip` SÍ entra (contenido forense, spec §5).

- [ ] **Step 1: Tests que fallan**

```python
def test_clasificar_tipo_contenido():
    from core.intake_lotes import clasificar_tipo_contenido as tc
    assert tc("_chat.txt") == "whatsapp"          # solo _chat.txt es 'whatsapp'
    assert tc("notas.txt") == "txt"
    assert tc("escrito.PDF") == "pdf"
    assert tc("IMG-001.jpg") == "imagen"
    assert tc("video.mp4") == "video"
    assert tc("nota_voz.opus") == "audio"         # _AUDIO_EXTS ya existía (whatsapp_intake:21)
    assert tc("correo.eml") == "eml"
    assert tc("contrato.docx") == "docx"
    assert tc("raro.xyz") == "otros"


def test_manifiesto_round_trip_y_exclusiones(tmp_path):
    from core import intake_lotes as il
    lote = tmp_path / "2026-07-17_manual_01"
    lote.mkdir()
    (lote / "doc.pdf").write_bytes(b"pdf")
    (lote / "_export_original.zip").write_bytes(b"zip")   # SÍ entra (spec §5)
    (lote / "_exported_ids.json").write_text("{}", encoding="utf-8")  # control: NO entra
    (lote / ".pulled").write_text("", encoding="utf-8")               # control: NO entra
    items = il.items_desde_disco(lote)
    assert {i.relpath for i in items} == {"doc.pdf", "_export_original.zip"}

    il.escribir_manifiesto(lote, fuente="manual", fecha_intake="2026-07-17",
                           origen="test", items=items)
    data = il.leer_manifiesto(lote)
    assert data["fuente"] == "manual" and data["origen"] == "test"
    assert {i["relpath"] for i in data["items"]} == {"doc.pdf", "_export_original.zip"}
    # None se omite: sin message_id/duplicado_de no aparecen las claves.
    assert all("duplicado_de" not in i and "message_id" not in i for i in data["items"])
    # El propio manifiesto no se auto-inventaría.
    assert "_manifiesto.yaml" not in {i.relpath for i in il.items_desde_disco(lote)}


def test_manifiesto_message_id_y_duplicado(tmp_path):
    from core import intake_lotes as il
    lote = tmp_path / "2026-07-17_email_01"
    lote.mkdir()
    (lote / "2026-07-01_asunto.eml").write_bytes(b"raw")
    items = il.items_desde_disco(
        lote,
        message_id_de={"2026-07-01_asunto.eml": "<x@y>"},
        duplicados={"2026-07-01_asunto.eml": "2026-06-10_manual_01/copia.eml"},
    )
    il.escribir_manifiesto(lote, fuente="email", fecha_intake="2026-07-17",
                           origen="email_export", items=items)
    item = il.leer_manifiesto(lote)["items"][0]
    assert item["message_id"] == "<x@y>"
    assert item["duplicado_de"] == "2026-06-10_manual_01/copia.eml"
    assert item["tipo_contenido"] == "eml"


def test_anexar_items_fusiona_por_relpath(tmp_path):
    from core import intake_lotes as il
    lote = tmp_path / "2026-07-17_manual_01"
    lote.mkdir()
    a = il.ItemManifiesto("a.pdf", "sha-a", 3, "pdf")
    il.anexar_items(lote, [a], origen="ui_manual")
    a2 = il.ItemManifiesto("a.pdf", "sha-a2", 4, "pdf")
    b = il.ItemManifiesto("b.txt", "sha-b", 1, "txt")
    il.anexar_items(lote, [a2, b], origen="ui_manual")
    data = il.leer_manifiesto(lote)
    assert data["fuente"] == "manual" and data["fecha_intake"] == "2026-07-17"
    por_rel = {i["relpath"]: i for i in data["items"]}
    assert set(por_rel) == {"a.pdf", "b.txt"}
    assert por_rel["a.pdf"]["sha256"] == "sha-a2"   # el nuevo gana
```

- [ ] **Step 2: Run** — Expected: FAIL (`ImportError: clasificar_tipo_contenido`).

- [ ] **Step 3: Implementación** (añadir a `core/intake_lotes.py`)

```python
import yaml
from dataclasses import asdict, dataclass

from .intake_manifest import compute_sha256

_TIPOS_POR_EXT = {
    ".pdf": "pdf",
    ".jpg": "imagen", ".jpeg": "imagen", ".png": "imagen", ".tiff": "imagen",
    ".tif": "imagen", ".heic": "imagen", ".webp": "imagen", ".gif": "imagen",
    ".mp4": "video", ".mov": "video", ".avi": "video", ".webm": "video", ".3gp": "video",
    ".opus": "audio", ".ogg": "audio", ".m4a": "audio", ".aac": "audio",
    ".mp3": "audio", ".wav": "audio",
    ".docx": "docx", ".doc": "docx", ".odt": "docx", ".rtf": "docx",
    ".txt": "txt", ".md": "txt",
    ".eml": "eml", ".msg": "eml",
}


def clasificar_tipo_contenido(nombre: str) -> str:
    """Eje TIPO (spec §5) — por extensión. Vocabulario propio, NO el de procedencia."""
    n = Path(nombre).name
    if n == "_chat.txt":
        return "whatsapp"
    return _TIPOS_POR_EXT.get(Path(n).suffix.lower(), "otros")


@dataclass
class ItemManifiesto:
    """Una fila del albarán del lote. ``relpath`` es POSIX relativo al lote."""
    relpath: str
    sha256: str
    size: int
    tipo_contenido: str
    message_id: str | None = None      # solo ítems .eml (spec §5)
    duplicado_de: str | None = None    # anotación; el fichero SE COPIA igual (§6)


def _item_a_dict(item: ItemManifiesto) -> dict:
    return {k: v for k, v in asdict(item).items() if v is not None}


def escribir_manifiesto(lote_dir: Path, *, fuente: str, fecha_intake: str,
                        origen: str, items: list[ItemManifiesto],
                        fecha_intake_estimada: bool = False) -> Path:
    data: dict = {"fuente": fuente, "fecha_intake": fecha_intake, "origen": origen}
    if fecha_intake_estimada:
        data["fecha_intake_estimada"] = True
    data["items"] = [_item_a_dict(i) for i in sorted(items, key=lambda i: i.relpath)]
    path = Path(lote_dir) / MANIFIESTO_LOTE
    path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return path


def leer_manifiesto(lote_dir: Path) -> dict | None:
    path = Path(lote_dir) / MANIFIESTO_LOTE
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def anexar_items(lote_dir: Path, items: list[ItemManifiesto], *, origen: str) -> Path:
    """Fusiona ítems en el manifiesto (crea si falta; el nuevo gana por relpath)."""
    lote_dir = Path(lote_dir)
    data = leer_manifiesto(lote_dir)
    if data is None:
        m = PATRON_LOTE.match(lote_dir.name)
        if m is None:
            raise ValueError(f"No es un directorio de lote: {lote_dir.name!r}")
        data = {"fuente": m.group(2), "fecha_intake": m.group(1),
                "origen": origen, "items": []}
    por_rel = {i.get("relpath"): i for i in data.get("items", [])}
    for item in items:
        por_rel[item.relpath] = _item_a_dict(item)
    data["items"] = [por_rel[k] for k in sorted(por_rel)]
    path = Path(lote_dir) / MANIFIESTO_LOTE
    path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return path


def items_desde_disco(lote_dir: Path, *,
                      message_id_de: dict[str, str] | None = None,
                      duplicados: dict[str, str] | None = None) -> list[ItemManifiesto]:
    """Inventaría el lote para el albarán, excluyendo control y el propio manifiesto."""
    lote_dir = Path(lote_dir)
    message_id_de = message_id_de or {}
    duplicados = duplicados or {}
    items: list[ItemManifiesto] = []
    for p in sorted(lote_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.name in config.INTAKE_CONTROL_FILES or p.name == MANIFIESTO_LOTE:
            continue
        rel = p.relative_to(lote_dir).as_posix()
        items.append(ItemManifiesto(
            relpath=rel, sha256=compute_sha256(p), size=p.stat().st_size,
            tipo_contenido=clasificar_tipo_contenido(p.name),
            message_id=message_id_de.get(rel), duplicado_de=duplicados.get(rel),
        ))
    return items
```

- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `git add core/intake_lotes.py tests/test_intake_lotes.py && git commit -m "feat(intake): _manifiesto.yaml por lote + clasificar_tipo_contenido (T3)"`

---

### Task 4: M9 — `message_id` opcional + `duplicado_de_para`

**Files:**
- Modify: `core/intake_manifest.py` (clase `IntakeManifest`)
- Test: `tests/test_intake_manifest.py` (añadir al final; si el fichero no existe, crearlo)

**Interfaces:**
- Produces (métodos de `IntakeManifest`):
  - `register(sha256, relative_path, *, source, message_id: str | None = None, **alias_details)`
    — mismo contrato de retorno `(action, primary_rel)`; si `message_id` viene y el entry no lo
    tiene, se persiste como `entry["message_id"]`.
  - `lookup_message_id(message_id: str) -> tuple[str, dict] | None` — `(sha, entry)` del primer
    entry (orden de inserción) con ese `message_id`.
  - `message_ids() -> set[str]` — todos los `message_id` registrados.
  - `duplicado_de_para(sha256: str, size: int, message_id: str | None = None) -> str | None`
    — valor para `duplicado_de` (§6): `primary_path` si el sha ya existe; si no y hay
    `message_id` registrado con OTRO sha, el `primary_path` de ese entry; `None` si `size == 0`
    (spec §6: tamaño 0 nunca marca) o si no hay duplicado.
- Compatibilidad: entries sin `message_id` (esquema actual) cargan y operan igual.

- [ ] **Step 1: Tests que fallan** (clase nueva al final de `tests/test_intake_manifest.py`)

```python
class TestMessageIdM9:
    def test_register_persiste_message_id(self, tmp_casos_root):
        from core import case_manager
        from core.intake_manifest import IntakeManifest
        case_manager.ensure_case("EV-M9-001", titulo="m9")
        with IntakeManifest("EV-M9-001") as m:
            m.register("sha-1", "2026-07-17_email_01/a.eml",
                       source="email", message_id="<uno@x>")
        with IntakeManifest("EV-M9-001") as m:   # round-trip por disco
            assert m.lookup("sha-1")["message_id"] == "<uno@x>"
            assert m.message_ids() == {"<uno@x>"}
            sha, entry = m.lookup_message_id("<uno@x>")
            assert sha == "sha-1"
            assert entry["primary_path"] == "2026-07-17_email_01/a.eml"

    def test_duplicado_de_para_sha_y_message_id(self, tmp_casos_root):
        from core import case_manager
        from core.intake_manifest import IntakeManifest
        case_manager.ensure_case("EV-M9-002", titulo="m9")
        with IntakeManifest("EV-M9-002") as m:
            m.register("sha-1", "2026-07-17_email_01/a.eml",
                       source="email", message_id="<uno@x>")
            # sha idéntico → duplicado por sha
            assert m.duplicado_de_para("sha-1", 10) == "2026-07-17_email_01/a.eml"
            # mismo correo, bytes distintos (sha nuevo) → duplicado por Message-ID (§6)
            assert m.duplicado_de_para("sha-2", 10, message_id="<uno@x>") \
                == "2026-07-17_email_01/a.eml"
            # sha y mid desconocidos → no es duplicado
            assert m.duplicado_de_para("sha-3", 10, message_id="<otro@x>") is None

    def test_tamano_cero_nunca_marca_duplicado(self, tmp_casos_root):
        from core import case_manager
        from core.intake_manifest import IntakeManifest
        case_manager.ensure_case("EV-M9-003", titulo="m9")
        with IntakeManifest("EV-M9-003") as m:
            m.register("sha-vacio", "2026-07-17_manual_01/vacio.txt", source="manual")
            assert m.duplicado_de_para("sha-vacio", 0) is None
```

- [ ] **Step 2: Run** `python -m pytest tests/test_intake_manifest.py -q --tb=short --junit-xml=.pytest-task.xml`
  — Expected: FAIL (`TypeError: register() got an unexpected keyword argument 'message_id'`).

- [ ] **Step 3: Implementación** (en `core/intake_manifest.py`)

En `register` (firma `core/intake_manifest.py:245`): añadir parámetro keyword
`message_id: str | None = None` y, en las dos ramas:

```python
        # rama "entry is None" (hash nuevo):
        if entry is None:
            nuevo: dict[str, Any] = {"primary_path": rel, "aliases": []}
            if message_id:
                nuevo["message_id"] = message_id
            self.data[sha256] = nuevo
            self._dirty = True
            return ("write", rel)
        # tras resolver alias/skip, antes del return final:
        if message_id and not entry.get("message_id"):
            entry["message_id"] = message_id
            self._dirty = True
```

Métodos nuevos (junto a `lookup`, `core/intake_manifest.py:315`):

```python
    def lookup_message_id(self, message_id: str) -> tuple[str, dict[str, Any]] | None:
        """Primer entry (orden de inserción) cuyo ``message_id`` coincide, o None."""
        if not message_id:
            return None
        for sha, entry in self.data.items():
            if entry.get("message_id") == message_id:
                return (sha, entry)
        return None

    def message_ids(self) -> set[str]:
        """Todos los Message-ID registrados (dedup tri-canal de correos, spec §6)."""
        return {e["message_id"] for e in self.data.values() if e.get("message_id")}

    def duplicado_de_para(self, sha256: str, size: int,
                          message_id: str | None = None) -> str | None:
        """Valor para ``duplicado_de`` del manifiesto de lote (spec §6), o None.

        El caller COPIA el fichero igualmente: esto solo anota. Tamaño 0 nunca
        marca (su sha constante relacionaría cosas sin relación).
        """
        if size == 0:
            return None
        entry = self.data.get(sha256)
        if entry is not None:
            return entry.get("primary_path") or None
        if message_id:
            hit = self.lookup_message_id(message_id)
            if hit is not None:
                return hit[1].get("primary_path") or None
        return None
```

- [ ] **Step 4: Run** el fichero + `python -m pytest tests/test_whatsapp_intake.py tests/test_email_export.py -q --tb=no --junit-xml=.pytest-task.xml` (consumidores de `register`) — Expected: verde.
- [ ] **Step 5: Commit** `git add core/intake_manifest.py tests/test_intake_manifest.py && git commit -m "feat(m9): message_id opcional + lookup + duplicado_de_para (T4)"`

---

### Task 5: Escritor WhatsApp → lote

**Files:**
- Modify: `core/whatsapp_intake.py` (función `deposit_export`, líneas 103-205)
- Modify: `tests/test_guard_intake_wiring.py:49-73` (asserts de ruta)
- Test: `tests/test_whatsapp_intake.py` (actualizar rutas + tests nuevos)

**Interfaces:**
- Consumes: `intake_lotes.reservar_lote`, `intake_lotes.escribir_manifiesto`,
  `intake_lotes.ItemManifiesto`, `intake_lotes.clasificar_tipo_contenido`,
  `IntakeManifest.duplicado_de_para` (T2/T3/T4).
- Produces: `deposit_export(case_id, rol_subdir, content, *, zip_name, date_range=None)`
  — misma firma y mismo `DepositResult`; `chat_dir` pasa a ser
  `00_Input/<lote>/<rol>/<chat>/`. **Contrato nuevo del skip:** con `skipped_dedup=True`,
  `chat_dir` apunta a la carpeta del depósito PREVIO (derivada del `primary_path` del zip en M9),
  no a una ruta hipotética nueva. Las subcarpetas de rol se conservan DENTRO del lote (verbatim §4).
- Reglas: (a) idempotencia de canal se mantiene — zip byte-idéntico ya ingerido → `skipped_dedup`,
  sin abrir lote nuevo; (b) por ítem, el duplicado cross-lote SE COPIA + `duplicado_de` (§6);
  (c) el lote lleva `_manifiesto.yaml` con `_export_original.zip` incluido.

- [ ] **Step 1: Tests que fallan** (añadir a `tests/test_whatsapp_intake.py`; reutilizar los
  helpers `_make_zip`/fixtures del propio fichero)

```python
def test_deposit_crea_lote_con_manifiesto(tmp_casos_root):
    from core import intake_lotes, whatsapp_intake
    case_id = "EV-WA-LOTE"
    case_manager.ensure_case(case_id, titulo="wa")
    content = _make_zip({"_chat.txt": _CHAT, "IMG-001.jpg": b"img"})
    res = whatsapp_intake.deposit_export(case_id, "03_Otros", content, zip_name="chat.zip")
    # chat_dir = <lote>/<rol>/<chat> — el lote conserva la subcarpeta de rol (verbatim §4)
    lote_dir = res.chat_dir.parent.parent
    assert intake_lotes.PATRON_LOTE.match(lote_dir.name).group(2) == "whatsapp"
    assert res.chat_dir.parent.name == "03_Otros"
    man = intake_lotes.leer_manifiesto(lote_dir)
    assert man["fuente"] == "whatsapp"
    rels = {i["relpath"] for i in man["items"]}
    assert "03_Otros/chat/_chat.txt" in rels
    assert "03_Otros/chat/_export_original.zip" in rels   # sí entra (spec §5)


def test_duplicado_cross_lote_se_copia_y_anota(tmp_casos_root):
    from core import intake_lotes, whatsapp_intake
    from core.intake_manifest import IntakeManifest, compute_sha256_bytes
    case_id = "EV-WA-DUP"
    case_manager.ensure_case(case_id, titulo="wa")
    # La misma imagen ya entró por un lote manual anterior (registrada en M9).
    with IntakeManifest(case_id) as m:
        m.register(compute_sha256_bytes(b"img"),
                   "2026-06-10_manual_01/IMG-001.jpg", source="manual")
    content = _make_zip({"_chat.txt": _CHAT, "IMG-001.jpg": b"img"})
    res = whatsapp_intake.deposit_export(case_id, "03_Otros", content, zip_name="chat.zip")
    assert not res.skipped_dedup
    assert (res.chat_dir / "IMG-001.jpg").exists()        # SE COPIA igualmente (§6)
    man = intake_lotes.leer_manifiesto(res.chat_dir.parent.parent)
    item = next(i for i in man["items"] if i["relpath"].endswith("IMG-001.jpg"))
    assert item["duplicado_de"] == "2026-06-10_manual_01/IMG-001.jpg"


def test_zip_identico_sigue_dedup_de_canal_sin_lote_nuevo(tmp_casos_root):
    from core import config, whatsapp_intake
    case_id = "EV-WA-IDEM"
    case_manager.ensure_case(case_id, titulo="wa")
    content = _make_zip({"_chat.txt": _CHAT})
    r1 = whatsapp_intake.deposit_export(case_id, "03_Otros", content, zip_name="chat.zip")
    r2 = whatsapp_intake.deposit_export(case_id, "03_Otros", content, zip_name="chat.zip")
    assert r2.skipped_dedup and r2.chat_dir == r1.chat_dir
    input_dir = config.caso_path(case_id) / "00_Input"
    lotes = [d for d in input_dir.iterdir() if d.name.endswith("_whatsapp_01")
             or "_whatsapp_" in d.name]
    assert len(lotes) == 1                                # no se abrió un segundo lote
```

- [ ] **Step 2: Run** `python -m pytest tests/test_whatsapp_intake.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: FAIL (rutas `02_Whatsapp`).

- [ ] **Step 3: Implementación** — reescribir el cuerpo de `deposit_export` desde la línea 130
  (`preview = analyze(...)`) hasta el `intake_log.append_event`:

```python
    preview = analyze(content, zip_name=zip_name)
    zip_sha = compute_sha256_bytes(content)
    members = _read_members(content)
    chat_txt_name, texto = _find_chat_txt(members)

    from . import intake_lotes

    files_written: list[Path] = []
    with IntakeManifest(case_id) as manifest:
        previo = manifest.lookup(zip_sha)
        if previo is not None:
            # Idempotencia de CANAL (no dedup cross-lote §6): el mismo export
            # byte-idéntico ya entró; no se abre lote nuevo.
            prev_dir = (caso_path(case_id) / "00_Input"
                        / Path(previo["primary_path"]).parent)
            return DepositResult(chat_dir=prev_dir, preview=preview,
                                 skipped_dedup=True)

        lote_dir = intake_lotes.reservar_lote(case_id, "whatsapp", "whatsapp")
        lote = lote_dir.name
        chat_dir = lote_dir / rol_subdir / preview.chat_name
        chat_dir.mkdir(parents=True, exist_ok=True)
        rel_base = f"{lote}/{rol_subdir}/{preview.chat_name}"
        items: list[intake_lotes.ItemManifiesto] = []

        def _escribe(name: str, data: bytes, **extra) -> None:
            sha = compute_sha256_bytes(data)
            # duplicado_de ANTES de register (register crearía el entry propio)
            dup = manifest.duplicado_de_para(sha, len(data))
            dest = chat_dir / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)          # el duplicado SE COPIA igual (§6)
            files_written.append(dest)
            manifest.register(sha, f"{rel_base}/{name}", source="whatsapp",
                              chat=preview.chat_name, **extra)
            items.append(intake_lotes.ItemManifiesto(
                relpath=f"{rol_subdir}/{preview.chat_name}/{name}",
                sha256=sha, size=len(data),
                tipo_contenido=intake_lotes.clasificar_tipo_contenido(name),
                duplicado_de=dup))

        for name, data in members.items():
            _escribe(name, data)
        _escribe(_ORIGINAL_ZIP_NAME, content, es_zip_origen=True)

        if date_range is not None:
            desde, hasta = date_range
            recortados = filter_by_date_range(parse_chat(texto), desde, hasta)
            lineas = [f"[{m.timestamp}] {m.autor or '(sistema)'}: {m.texto}"
                      for m in recortados]
            _escribe("_chat_recortado.txt",
                     "\n".join(lineas).encode("utf-8"))

        intake_lotes.escribir_manifiesto(
            lote_dir, fuente="whatsapp", fecha_intake=lote[:10],
            origen="whatsapp_intake", items=items)
```

Notas de implementación: (1) el import de `dir_intake` de la línea 135 ya no hace falta —
`reservar_lote` aplica el guard; (2) `_chat_recortado.txt` pasa por `_escribe` (bytes UTF-8) para
entrar en custodia y manifiesto; (3) añadir `"lote": lote` a los `details` del evento
`upload_whatsapp` (campo ADITIVO en details — no es cambio de esquema del log).

En `tests/test_guard_intake_wiring.py`:

```python
# test_whatsapp_disponible_escribe_normal — sustituir el assert de cajón:
    assert "_pendiente_checkin" not in res.chat_dir.as_posix()
    from core.intake_lotes import PATRON_LOTE
    assert PATRON_LOTE.match(res.chat_dir.parent.parent.name).group(2) == "whatsapp"

# test_whatsapp_prestado_desvia_a_bandeja — el árbol vivo ahora se comprueba así:
    vivo = caso_path(case_id) / "00_Input"
    assert not any(vivo.rglob("_chat.txt"))
```

- [ ] **Step 4: Run** `python -m pytest tests/test_whatsapp_intake.py tests/test_guard_intake_wiring.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: PASS (actualizar cualquier otro assert de `02_Whatsapp` que falle en `test_whatsapp_intake.py`).
- [ ] **Step 5: Commit** `git add core/whatsapp_intake.py tests/test_whatsapp_intake.py tests/test_guard_intake_wiring.py && git commit -m "feat(whatsapp): deposito por lote con manifiesto y duplicado_de (T5)"`

---

### Task 6: Escritor manual → lote (`intake_manual` + Streamlit)

**Files:**
- Modify: `core/intake_manual.py` (`save_file` :53, `extract_zip` :101, `list_files` :232;
  `save_file_crm_branch` NO se toca — espejo)
- Modify: `streamlit_app.py:588-616` (bloque «Guardar documentos»)
- Test: `tests/test_intake_manual.py`

**Interfaces:**
- Produces:
  - `abrir_lote_manual(case_id: str, *, origen: str = "manual") -> Path` — envoltura de
    `reservar_lote(case_id, "manual", origen)`.
  - `save_file(case_id, filename, content, *, lote: Path | None = None) -> Path` — sin `lote`,
    abre uno propio (una entrega de un fichero); con `lote`, deposita en él (la UI agrupa un clic
    en UN lote). Registra en M9 + anexa al manifiesto (`anexar_items`). Sobrescribir el mismo
    nombre DENTRO del mismo lote sigue permitido (reintento idempotente).
  - `extract_zip(case_id, content, *, lote: Path | None = None) -> list[Path]` — ídem, extrae en
    el lote y registra cada fichero.
  - `list_files(case_id) -> list[Path]` — nivel raíz de cada lote `manual` + legacy `04_Manual`.
- El guard §6 lo aplica `reservar_lote`; `save_file` deja de llamar a `guard_escritura`
  directamente (el lote YA es la ruta efectiva).

- [ ] **Step 1: Tests que fallan** (añadir a `tests/test_intake_manual.py`)

```python
class TestSaveFileEnLote:
    def test_save_file_sin_lote_abre_lote_propio(self, caso_man, tmp_casos_root):
        from core import intake_lotes, intake_manual
        dest = intake_manual.save_file(caso_man, "demanda.pdf", b"pdf")
        lote = dest.parent
        assert intake_lotes.PATRON_LOTE.match(lote.name).group(2) == "manual"
        man = intake_lotes.leer_manifiesto(lote)
        assert man["items"][0]["relpath"] == "demanda.pdf"

    def test_dos_save_file_al_mismo_lote(self, caso_man, tmp_casos_root):
        from core import intake_lotes, intake_manual
        lote = intake_manual.abrir_lote_manual(caso_man)
        d1 = intake_manual.save_file(caso_man, "a.pdf", b"a", lote=lote)
        d2 = intake_manual.save_file(caso_man, "b.pdf", b"b", lote=lote)
        assert d1.parent == d2.parent == lote
        rels = {i["relpath"] for i in intake_lotes.leer_manifiesto(lote)["items"]}
        assert rels == {"a.pdf", "b.pdf"}

    def test_duplicado_se_copia_y_anota(self, caso_man, tmp_casos_root):
        from core import intake_lotes, intake_manual
        intake_manual.save_file(caso_man, "a.pdf", b"mismo")
        d2 = intake_manual.save_file(caso_man, "copia.pdf", b"mismo")
        assert d2.exists()                                 # se copia igual (§6)
        man = intake_lotes.leer_manifiesto(d2.parent)
        item = next(i for i in man["items"] if i["relpath"] == "copia.pdf")
        assert "duplicado_de" in item

    def test_extract_zip_en_lote(self, caso_man, tmp_casos_root):
        from core import intake_lotes, intake_manual
        paths = intake_manual.extract_zip(caso_man, _make_zip({"x/a.pdf": b"a"}))
        lote = paths[0].parent.parent                       # <lote>/x/a.pdf
        assert intake_lotes.PATRON_LOTE.match(lote.name)
        assert intake_lotes.leer_manifiesto(lote)["items"][0]["relpath"] == "x/a.pdf"

    def test_list_files_ve_lotes_y_legacy(self, caso_man, tmp_casos_root):
        from core import config, intake_manual
        intake_manual.save_file(caso_man, "nuevo.pdf", b"n")
        legacy = config.caso_path(caso_man) / "00_Input" / "04_Manual"
        legacy.mkdir(parents=True, exist_ok=True)
        (legacy / "viejo.pdf").write_bytes(b"v")
        nombres = {p.name for p in intake_manual.list_files(caso_man)}
        assert {"nuevo.pdf", "viejo.pdf"} <= nombres
```

- [ ] **Step 2: Run** `python -m pytest tests/test_intake_manual.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: FAIL.

- [ ] **Step 3: Implementación**

```python
# core/intake_manual.py — sustituir el cuerpo de save_file y añadir helpers
from .intake_manifest import IntakeManifest, compute_sha256_bytes


def abrir_lote_manual(case_id: str, *, origen: str = "manual") -> Path:
    """Reserva un lote 'manual' (una entrega). La UI agrupa un clic en UN lote."""
    from .intake_lotes import reservar_lote
    return reservar_lote(case_id, "manual", origen)


def _registrar_en_lote(case_id: str, lote: Path, rel: str, content: bytes,
                       *, origen: str) -> None:
    from . import intake_lotes
    sha = compute_sha256_bytes(content)
    with IntakeManifest(case_id) as manifest:
        dup = manifest.duplicado_de_para(sha, len(content))
        manifest.register(sha, f"{Path(lote).name}/{rel}", source="manual")
    intake_lotes.anexar_items(lote, [intake_lotes.ItemManifiesto(
        relpath=rel, sha256=sha, size=len(content),
        tipo_contenido=intake_lotes.clasificar_tipo_contenido(rel),
        duplicado_de=dup)], origen=origen)


def save_file(case_id: str, filename: str, content: bytes,
              *, lote: Path | None = None) -> Path:
    # (conservar las validaciones actuales de filename y de existencia del caso)
    ...
    if lote is None:
        lote = abrir_lote_manual(case_id)
    dest = Path(lote) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    _registrar_en_lote(case_id, Path(lote), filename, content, origen="ui_manual")
    return dest


def extract_zip(case_id: str, content: bytes,
                *, lote: Path | None = None) -> list[Path]:
    # (conservar la validación de existencia del caso)
    ...
    if lote is None:
        lote = abrir_lote_manual(case_id)
    extraidos = sorted(safe_zip_extract(content, Path(lote)))
    for p in extraidos:
        rel = p.relative_to(lote).as_posix()
        _registrar_en_lote(case_id, Path(lote), rel, p.read_bytes(),
                           origen="ui_manual")
    return extraidos


def list_files(case_id: str) -> list[Path]:
    """Nivel raíz de cada lote 'manual' + legacy 04_Manual (casos no migrados)."""
    from .intake_lotes import MANIFIESTO_LOTE, PATRON_LOTE
    input_dir = caso_path(case_id) / "00_Input"
    if not input_dir.exists():
        return []
    bases = [d for d in input_dir.iterdir() if d.is_dir()
             and (m := PATRON_LOTE.match(d.name)) and m.group(2) == "manual"]
    legacy = input_dir / _MANUAL_SUBDIR
    if legacy.is_dir():
        bases.append(legacy)
    out = [p for d in bases for p in d.iterdir()
           if p.is_file() and p.name not in _CONTROL_FILES
           and p.name != MANIFIESTO_LOTE]
    return sorted(out)
```

Quitar de `save_file` el bloque `guard_escritura` (líneas 85-97 actuales): el guard ya lo aplicó
`reservar_lote`. `_manual_dir` se conserva (lo usa `list_files` para el legacy).

En `streamlit_app.py` (bloque del botón `casos_dem_btn`, línea 588): abrir UN lote por clic y
pasarlo a ambas llamadas:

```python
            if st.button("⬆️ Guardar documentos", ...):
                _lote_dem = intake_manual.abrir_lote_manual(_caso_dem)
                _saved_dem = 0
                _errors_dem: list[str] = []
                for _uf in _uploaded_dem:
                    try:
                        _raw = _uf.read()
                        if _uf.name.lower().endswith(".zip"):
                            _extracted = intake_manual.extract_zip(
                                _caso_dem, _raw, lote=_lote_dem)
                            ...
                        else:
                            intake_manual.save_file(
                                _caso_dem, _uf.name, _raw, lote=_lote_dem)
                            ...
```

(y en el mensaje de éxito, sustituir el literal `04_Manual/` por `_lote_dem.name`).

- [ ] **Step 4: Run** `python -m pytest tests/test_intake_manual.py tests/test_guard_intake_wiring.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: PASS salvo `TestEnsureCaseCrea04Manual` (se invierte en T10; si bloquea aquí, dejarlo para T10 sin tocar `ensure_case`). Actualizar los asserts `04_Manual` restantes del fichero.
- [ ] **Step 5: Commit** `git add core/intake_manual.py streamlit_app.py tests/test_intake_manual.py && git commit -m "feat(manual): save_file/extract_zip por lote + un lote por clic en la UI (T6)"`

---

### Task 7: Email (1/2) — estado de canal a la raíz + dedup Message-ID vía M9

**Files:**
- Modify: `core/email_export.py` (`export_label` :~948-1040, `_emit_traza` :1141,
  `ExportReport`)
- Test: `tests/test_email_export.py`

**Interfaces:**
- Consumes: `IntakeManifest.message_ids()`, `.lookup_message_id()`, `register(message_id=)` (T4).
- Produces:
  - `_dir_estado_canal(dest: Path, case_id: str | None) -> Path` — con `case_id`, la raíz de
    `00_Input/` del caso (los índices `_exported_ids.json`/`_resolved_links.json` pasan a ser
    ficheros de protocolo de la raíz, spec §8); sin `case_id`, `dest` (compat uso suelto).
  - Lectura con fallback legacy: si el índice no está en la raíz pero sí en `03_Email/`, se
    fusiona (y se guarda ya en la raíz).
  - `vistos` (dedup Message-ID) deja de escanear el destino: con `case_id` se siembra de
    `M9.message_ids() ∪ existing_message_ids(<00_Input>/03_Email)` (legacy sin migrar).
  - **Cambio de contrato (§6/§9.3):** un mensaje nuevo (gmail_id no exportado) cuyo Message-ID ya
    consta → **SE ESCRIBE** y se acumula en `report.duplicados_map: dict[str, str]`
    (`relpath → primary_path` de M9) para el manifiesto de T8; contador nuevo
    `ExportReport.duplicados: int = 0`. La idempotencia de canal (no re-descargar) sigue siendo
    el índice de `gmail_id`.
  - `_emit_traza` pasa `message_id=mid` al `manifest.register(...)` de cada `.eml`.
  - `existing_message_ids` se CONSERVA (siembra del legacy + uso suelto sin caso).

- [ ] **Step 1: Tests que fallan** (añadir a `tests/test_email_export.py`; usar la
  infraestructura `_FakeService` existente del fichero y su patrón de e2e con `case_id`)

```python
def test_indices_de_canal_viven_en_la_raiz_de_00_input(tmp_casos_root):
    # export con case_id → _exported_ids.json en 00_Input/, NO dentro del destino
    case_id = _caso_para_export()             # helper existente del fichero (o ensure_case)
    dest = ee.email_dest_dir(case_id)
    report = ee.export_label("acc@x", "Etiqueta", dest, case_id=case_id,
                             service=_FakeService([_EML_UNO]))
    input_dir = config.caso_path(case_id) / "00_Input"
    assert (input_dir / "_exported_ids.json").is_file()
    assert not (dest / "_exported_ids.json").exists()


def test_fallback_legacy_del_indice_en_03_email(tmp_casos_root):
    # Caso no migrado: el índice viejo en 03_Email/ se respeta (no re-descarga)
    case_id = _caso_para_export()
    legacy = config.caso_path(case_id) / "00_Input" / "03_Email"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "_exported_ids.json").write_text(
        json.dumps({"acc@x": ["gid-1"]}), encoding="utf-8")
    dest = ee.email_dest_dir(case_id)
    report = ee.export_label("acc@x", "Etiqueta", dest, case_id=case_id,
                             service=_FakeService([("gid-1", _EML_UNO)]))
    assert report.written == 0 and report.skipped == 1


def test_mismo_message_id_bytes_distintos_se_escribe_y_anota(tmp_casos_root):
    # §9.3: mismo correo con bytes distintos y mismo Message-ID → se copia + duplicado_de
    case_id = _caso_para_export()
    with IntakeManifest(case_id) as m:
        m.register("sha-previo", "2026-07-01_email_01/previo.eml",
                   source="email", message_id="<uno@x>")
    dest = ee.email_dest_dir(case_id)
    report = ee.export_label("acc@x", "Etiqueta", dest, case_id=case_id,
                             service=_FakeService([_EML_UNO_VARIANTE]))  # mid <uno@x>
    assert report.written == 1 and report.duplicados == 1
    assert list(report.duplicados_map.values()) == ["2026-07-01_email_01/previo.eml"]
    assert any(dest.rglob("*.eml"))                        # el fichero ESTÁ en disco


def test_emit_traza_registra_message_id_en_m9(tmp_casos_root):
    case_id = _caso_para_export()
    dest = ee.email_dest_dir(case_id)
    ee.export_label("acc@x", "Etiqueta", dest, case_id=case_id,
                    service=_FakeService([_EML_UNO]))
    with IntakeManifest(case_id) as m:
        assert "<uno@x>" in m.message_ids()
```

(Definir en el propio test los raws sintéticos `_EML_UNO`/`_EML_UNO_VARIANTE` con
`Message-ID: <uno@x>` y cuerpos distintos, al estilo de los raws ya usados en el fichero.)

- [ ] **Step 2: Run** `python -m pytest tests/test_email_export.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: FAIL.

- [ ] **Step 3: Implementación** (en `core/email_export.py`)

```python
def _dir_estado_canal(dest: Path, case_id: str | None) -> Path:
    """Hogar de _exported_ids.json/_resolved_links.json.

    Con caso: la raíz de 00_Input (fichero de protocolo, spec §8 — así el índice
    sobrevive al paso a lotes y un re-export no re-baja la etiqueta entera).
    Sin caso (uso suelto): el propio dest, como hasta ahora.
    """
    if not case_id:
        return dest
    from .casos.case_locator import path_for, resolve_ref
    return path_for(resolve_ref(case_id)) / "00_Input"
```

En `export_label` (líneas ~968-979):

```python
    estado_dir = _dir_estado_canal(dest, case_id)
    index = _load_export_index(estado_dir)
    legacy_cajon = estado_dir / "03_Email"
    if case_id and legacy_cajon.is_dir():
        for acc, gids in _load_export_index(legacy_cajon).items():
            index[acc] = sorted(set(index.get(acc, [])) | set(gids))
    ya_gids: set[str] = set() if force else set(index.get(account, []))
    ...
    if candidates:
        if case_id:
            with IntakeManifest(case_id) as _m:
                vistos = _m.message_ids()
            vistos |= existing_message_ids(legacy_cajon)
        else:
            vistos = existing_message_ids(dest)
        link_index = _load_resolved_links(estado_dir)
        if case_id and not link_index:
            link_index = _load_resolved_links(legacy_cajon)
```

Bucle principal (líneas 1007-1016) — el duplicado por Message-ID se escribe y anota, ya no hace
`continue`:

```python
        for gid, raw_bytes in _iter_raws(...):
            mid = message_id_of(raw_bytes)
            duplicado_de = None
            if mid and mid in vistos:
                report.duplicados += 1
                if case_id:
                    with IntakeManifest(case_id) as _m:
                        hit = _m.lookup_message_id(mid)
                    duplicado_de = hit[1].get("primary_path") if hit else None
            elif mid:
                vistos.add(mid)
            try:
                eml_path = _escribe_mensaje(dest, raw_bytes, extract_attachments, report)
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"{gid}: {exc}")
                continue
            rel = str(eml_path.relative_to(dest)).replace("\\", "/")
            if duplicado_de:
                report.duplicados_map[rel] = duplicado_de
            report.files.append(rel)
            report.written += 1
            nuevos_gids.append(gid)
            _flatten_safe(gid, raw_bytes)
            _links_safe(gid, raw_bytes, mid)

        index[account] = sorted(ya_gids | set(nuevos_gids))
        _save_export_index(estado_dir, index)
        _save_resolved_links(estado_dir, link_index)
```

`ExportReport`: añadir campos `duplicados: int = 0` y
`duplicados_map: dict[str, str] = field(default_factory=dict)`.

`_emit_traza` (:1196, donde calcula el sha y registra): para los `.eml`, calcular `mid` (ya
dispone del mapeo Message-ID→sha→ruta para el evento) y pasarlo:
`manifest.register(sha, rel, source="email", message_id=mid, ...)` (los no-eml siguen sin
`message_id`). El aplanado de anidados y el rescate de enlaces (Parte 1/Parte 2) conservan su
dedup interno intra-corrida — su reclasificación fina es #55, fuera de alcance.

- [ ] **Step 4: Run** `python -m pytest tests/test_email_export.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: PASS. Los tests existentes que asertaban `skipped` por Message-ID (no por gmail_id) se actualizan al contrato nuevo (`duplicados`/escritura).
- [ ] **Step 5: Commit** `git add core/email_export.py tests/test_email_export.py && git commit -m "feat(email): indices de canal en raiz de 00_Input + dedup Message-ID via M9, copia+anota (T7)"`

---

### Task 8: Email (2/2) — lote por corrida + manifiesto + índices cross-lote

**Files:**
- Modify: `core/email_export.py` (`email_dest_dir` :1301, `export_label` cierre :1030-1040,
  `write_indices` :1276)
- Modify: `scripts/export_label_emails.py:63`
- Modify: `tests/test_guard_intake_wiring.py:80-95`
- Test: `tests/test_email_export.py`

**Interfaces:**
- Produces:
  - `email_dest_dir(case_id) -> Path` — **reserva un lote email nuevo** por llamada
    (`intake_lotes.reservar_lote(resolve_ref(case_id), "email", "email")`); guard §6 incluido.
  - `export_label(...)`: si `case_id` y `dest` es un lote (`PATRON_LOTE.match(dest.name)`):
    al cerrar, (a) si el lote quedó SIN contenido (corrida sin novedad) → se elimina el
    directorio (no quedan lotes vacíos); (b) si hay contenido → `_manifiesto.yaml` con
    `message_id` por `.eml` y `duplicado_de` desde `report.duplicados_map`;
    (c) `INDICE.md`/`CRONOLOGIA.md` se regeneran **cross-lote** en `01_Procesado/Emails/`.
    Sin `case_id` (uso suelto): comportamiento actual (`write_indices(dest)` en el destino).
  - `write_indices_caso(case_id) -> None` — recorre los lotes `email` de `00_Input/` + el cajón
    legacy `03_Email/` y escribe los índices en `01_Procesado/Emails/` con rutas
    `<lote|03_Email>/<rel>`.
  - `write_indices(dest_dir)` se conserva (uso suelto y tests puros).

- [ ] **Step 1: Tests que fallan**

```python
def test_email_dest_dir_reserva_lote(tmp_casos_root):
    from core.intake_lotes import PATRON_LOTE
    case_id = _caso_para_export()
    d = ee.email_dest_dir(case_id)
    assert PATRON_LOTE.match(d.name).group(2) == "email"
    assert d.parent.name == "00_Input" and d.is_dir()


def test_export_escribe_manifiesto_con_message_id(tmp_casos_root):
    from core import intake_lotes
    case_id = _caso_para_export()
    dest = ee.email_dest_dir(case_id)
    ee.export_label("acc@x", "Etiqueta", dest, case_id=case_id,
                    service=_FakeService([_EML_UNO]))
    man = intake_lotes.leer_manifiesto(dest)
    assert man["fuente"] == "email"
    eml = next(i for i in man["items"] if i["relpath"].endswith(".eml"))
    assert eml["message_id"] == "<uno@x>" and eml["tipo_contenido"] == "eml"


def test_reexport_sin_novedad_no_deja_lote_vacio_y_cronologia_completa(tmp_casos_root):
    # §9.5: el re-export no re-descarga (índice de canal) y la cronología cross-lote sale completa
    case_id = _caso_para_export()
    d1 = ee.email_dest_dir(case_id)
    ee.export_label("acc@x", "Etiqueta", d1, case_id=case_id,
                    service=_FakeService([_EML_UNO]))
    d2 = ee.email_dest_dir(case_id)
    r2 = ee.export_label("acc@x", "Etiqueta", d2, case_id=case_id,
                         service=_FakeService([_EML_UNO]))
    assert r2.written == 0
    assert not d2.exists()                                  # lote vacío eliminado
    crono = (config.caso_path(case_id) / "01_Procesado" / "Emails"
             / "CRONOLOGIA.md").read_text(encoding="utf-8")
    assert d1.name in crono                                 # ruta con prefijo de lote


def test_cronologia_cross_lote_incluye_legacy(tmp_casos_root):
    case_id = _caso_para_export()
    legacy = config.caso_path(case_id) / "00_Input" / "03_Email"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "2026-01-01_viejo.eml").write_bytes(_EML_VIEJO)
    ee.write_indices_caso(case_id)
    indice = (config.caso_path(case_id) / "01_Procesado" / "Emails"
              / "INDICE.md").read_text(encoding="utf-8")
    assert "03_Email/2026-01-01_viejo.eml" in indice
```

- [ ] **Step 2: Run** — Expected: FAIL (`email_dest_dir` devuelve `00_Input/03_Email`).

- [ ] **Step 3: Implementación**

```python
def email_dest_dir(case_id: str) -> Path:
    """Destino de escritura del export: un LOTE email nuevo por corrida (spec §8).

    Reserva 00_Input/<AAAA-MM-DD>_email_<NN>/ (guard §6 incluido: caso prestado →
    el lote nace en la bandeja). export_label elimina el lote si la corrida no
    escribe nada.
    """
    from .casos.case_locator import resolve_ref
    from .intake_lotes import reservar_lote
    return reservar_lote(resolve_ref(case_id), "email", "email")
```

Cierre de `export_label` (sustituir la línea 1034 `write_indices(dest)`):

```python
    from . import intake_lotes

    es_lote = bool(case_id) and intake_lotes.PATRON_LOTE.match(dest.name) is not None
    if es_lote:
        contenido = [p for p in dest.rglob("*") if p.is_file()
                     and p.name not in config.INTAKE_CONTROL_FILES
                     and p.name != intake_lotes.MANIFIESTO_LOTE]
        if not contenido:
            _rmtree_vacio(dest)          # corrida sin novedad: no queda lote vacío
        else:
            mids: dict[str, str] = {}
            for eml in dest.rglob("*.eml"):
                mid = message_id_of(eml.read_bytes())
                if mid:
                    mids[str(eml.relative_to(dest)).replace("\\", "/")] = mid
            items = intake_lotes.items_desde_disco(
                dest, message_id_de=mids, duplicados=report.duplicados_map)
            intake_lotes.escribir_manifiesto(
                dest, fuente="email", fecha_intake=dest.name[:10],
                origen="email_export", items=items)
        write_indices_caso(case_id)
    else:
        write_indices(dest)
```

(`_rmtree_vacio(dest)`: borra subdirectorios vacíos y el dir con `Path.rmdir()`; sin ficheros por
definición del if. OJO: `email_export.py` NO importa `config` hoy — añadir `from . import config`
al bloque de imports, línea 45.)

Refactor de índices — extraer el render de `write_indices` y añadir la vista de caso:

```python
def _escribe_indices_en(out_dir: Path, entradas: list[_Entrada]) -> None:
    # (cuerpo actual de write_indices desde `cab = (...)` hasta el final,
    #  escribiendo en out_dir en vez de dest)


def write_indices(dest_dir: Path | str) -> None:
    """Regenera INDICE.md/CRONOLOGIA.md desde los .eml de dest_dir (uso suelto)."""
    dest = Path(dest_dir)
    _escribe_indices_en(dest, _recolecta_entradas(dest))


def write_indices_caso(case_id: str) -> None:
    """Índices CROSS-LOTE del caso en 01_Procesado/Emails/ (spec §8).

    Recorre los lotes email de 00_Input/ + el cajón legacy 03_Email; las rutas
    llevan el prefijo del lote/cajón. Son artefactos derivados, no crudo.
    """
    import dataclasses

    from . import intake_lotes
    from .casos.case_locator import path_for, resolve_ref

    case_dir = path_for(resolve_ref(case_id))
    input_dir = case_dir / "00_Input"
    bases: list[Path] = []
    if input_dir.is_dir():
        bases = [d for d in input_dir.iterdir() if d.is_dir()
                 and (m := intake_lotes.PATRON_LOTE.match(d.name))
                 and m.group(2) == "email"]
    legacy = input_dir / "03_Email"
    if legacy.is_dir():
        bases.append(legacy)
    entradas: list[_Entrada] = []
    for base in bases:
        entradas += [dataclasses.replace(e, ruta=f"{base.name}/{e.ruta}")
                     for e in _recolecta_entradas(base)]
    entradas.sort(key=lambda e: (e.fecha, e.ruta))
    out = case_dir / "01_Procesado" / "Emails"
    out.mkdir(parents=True, exist_ok=True)
    _escribe_indices_en(out, entradas)
```

`scripts/export_label_emails.py:63`: sustituir
`dest = path_for(case_id) / "00_Input" / "03_Email"` por
`dest = email_dest_dir(case_id)` (importar de `core.email_export`; el docstring del script
se actualiza al modelo de lote).

`tests/test_guard_intake_wiring.py:80-95`:

```python
def test_email_dest_dir_disponible_normal(tmp_casos_root):
    from core import email_export
    from core.intake_lotes import PATRON_LOTE
    case_manager.ensure_case("EV-2026-001", titulo="x")
    d = email_export.email_dest_dir("EV-2026-001")
    assert PATRON_LOTE.match(d.name).group(2) == "email"
    assert "_pendiente_checkin" not in d.as_posix()


def test_email_dest_dir_prestado_desvia(tmp_casos_root):
    from core import email_export, intake_log
    from core.intake_lotes import PATRON_LOTE
    case_id = _caso_prestado()
    d = email_export.email_dest_dir(case_id)
    assert "_pendiente_checkin/email/00_Input/" in d.as_posix()
    assert PATRON_LOTE.match(d.name)
    assert any(e["event"] == "pendiente_checkin" for e in intake_log.read_events(case_id))
```

- [ ] **Step 4: Run** `python -m pytest tests/test_email_export.py tests/test_guard_intake_wiring.py tests/test_email_export_mcp_server.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: PASS (los e2e existentes que asertaban `00_Input/03_Email` se actualizan al lote; el MCP server usa mocks de `email_dest_dir` → sin cambios).
- [ ] **Step 5: Commit** `git add core/email_export.py scripts/export_label_emails.py tests/test_email_export.py tests/test_guard_intake_wiring.py && git commit -m "feat(email): lote por corrida + manifiesto + indices cross-lote en 01_Procesado/Emails (T8)"`

---

### Task 9: `abrir_caso` — cerebro y CLI por lote

**Files:**
- Modify: `core/abrir_caso.py` (`FUENTE_A_SUBDIR` :14, `plan_intake` :152)
- Modify: `scripts/abrir_caso.py` (`_depositar_manual` :126, `_intake_manual` :148,
  `_intake_email` :188, `_intake_generico`/`_intake_drive_ev` :72-101)
- Test: `tests/test_abrir_caso.py`

**Interfaces:**
- Consumes: `intake_manual.abrir_lote_manual`/`save_file(lote=)`/`extract_zip(lote=)` (T6),
  `email_export.email_dest_dir` (T8), `config.FUENTES_LOTE` (T1).
- Produces (cerebro puro, sin I/O):
  - `FUENTE_A_SUBDIR` **eliminado**; nuevo `FUENTES: tuple[str, ...] = ("drive_ev",) +
    config.FUENTES_LOTE` y `SUBDIR_DRIVE_EV = "01_Drive EV"`.
  - `plan_intake(inventario, log_existente, fuente, *, lote: str | None = None) -> PlanIntake`
    — `drive_ev` (espejo): `dst = f"01_Drive EV/{rel}"` como hoy; fuentes de lote: `lote`
    obligatorio (`ValueError` si falta), `dst = f"{lote}/{rel}"`. La cadena de custodia toma la
    fuente de `plan.fuente`, no del primer segmento (spec §8).
  - `FUENTE_A_EVENTO` sin cambios.
- CLI: la vía manual abre UN lote y deposita por `intake_manual` (deja de copiar por
  `shutil` fuera de `dir_intake`); la vía email usa `email_dest_dir` (lote, T8); `drive_ev`
  intacta. Los dry-run no reservan lote (mensaje "se depositaría en un lote nuevo
  `<fecha>_<fuente>_NN`").

- [ ] **Step 1: Tests que fallan** (en `tests/test_abrir_caso.py`; actualizar además el assert
  de la línea 93 `plan.categorias == ("01_Drive EV",)` que sigue válido para drive_ev)

```python
def test_plan_intake_fuente_de_lote_exige_lote():
    import pytest
    from core import abrir_caso as brain
    with pytest.raises(ValueError):
        brain.plan_intake([], [], "manual")           # sin lote → error


def test_plan_intake_lote_compone_dst():
    from core import abrir_caso as brain
    inv = [{"relpath": "a.pdf", "sha256": "s1", "size": 3}]
    plan = brain.plan_intake(inv, [], "manual", lote="2026-07-17_manual_01")
    assert plan.items[0].dst == "2026-07-17_manual_01/a.pdf"
    assert plan.categorias == ("2026-07-17_manual_01",)


def test_plan_intake_drive_ev_sigue_en_cajon_espejo():
    from core import abrir_caso as brain
    inv = [{"relpath": "w/doc.pdf", "sha256": "s1", "size": 3}]
    plan = brain.plan_intake(inv, [], "drive_ev")
    assert plan.items[0].dst == "01_Drive EV/w/doc.pdf"


def test_fuente_a_subdir_eliminado():
    from core import abrir_caso as brain
    assert not hasattr(brain, "FUENTE_A_SUBDIR")
    assert brain.FUENTES == ("drive_ev", "whatsapp", "email", "manual", "entrevista")
```

- [ ] **Step 2: Run** `python -m pytest tests/test_abrir_caso.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: FAIL.

- [ ] **Step 3: Implementación**

`core/abrir_caso.py`:

```python
# sustituir FUENTE_A_SUBDIR (líneas 14-17) por:
SUBDIR_DRIVE_EV = "01_Drive EV"          # espejo: cajón fijo (spec §2)
FUENTES = ("drive_ev",) + config.FUENTES_LOTE
# FUENTE_A_EVENTO se queda igual.


def plan_intake(inventario: list[dict], log_existente: list[dict], fuente: str,
                *, lote: str | None = None) -> PlanIntake:
    """Plan de depósito (puro). Fuentes de entrega componen dst bajo su LOTE."""
    if fuente not in FUENTES:
        raise ValueError(f"Fuente desconocida: {fuente!r}. Válidas: {sorted(FUENTES)}")
    if fuente == "drive_ev":
        base = SUBDIR_DRIVE_EV
    else:
        if not lote:
            raise ValueError(f"La fuente de entrega {fuente!r} requiere lote=")
        base = lote
    evento = FUENTE_A_EVENTO[fuente]
    # ... (resto igual, con dst=f"{base}/{rel}")
```

`scripts/abrir_caso.py`:

```python
def _intake_generico(case_dir, case_id, fuente, hashes, *, base, dry_run):
    # nuevo parámetro `base` (lote o "01_Drive EV") en lugar de FUENTE_A_SUBDIR
    inventario = _inventario_desde_hashes(case_dir, base, hashes)
    plan = brain.plan_intake(inventario, intake_log.read_events(case_id), fuente,
                             lote=None if fuente == "drive_ev" else base)
    # ... resto igual


def _intake_drive_ev(ident, case_dir, folder_id, team_id, *, dry_run):
    intake_drive.pull_drive_ev(ident.case_id, folder_id, team_id)
    subdir = brain.SUBDIR_DRIVE_EV
    hashes = hash_tree_local(case_dir / "00_Input" / subdir, prefijo=subdir)
    _intake_generico(case_dir, ident.case_id, "drive_ev", hashes,
                     base=subdir, dry_run=dry_run)


def _depositar_manual(case_id: str, src: Path, lote: Path) -> list[str]:
    """Deposita el origen en el LOTE vía intake_manual (guard+M9+manifiesto)."""
    if zipfile.is_zipfile(src):
        paths = intake_manual.extract_zip(case_id, src.read_bytes(), lote=lote)
        return [p.relative_to(lote).as_posix() for p in paths]
    if src.is_dir():
        depositados: list[str] = []
        for p in sorted(src.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(src).as_posix()
            # subcarpetas: escribir vía bytes en el lote conservando estructura
            dest = lote / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            intake_manual.save_file_en_lote(case_id, lote, rel, p.read_bytes())
            depositados.append(rel)
        return depositados
    raise FileNotFoundError(f"--src no es carpeta ni .zip: {src}")


def _intake_manual(ident, case_dir, src_str, *, dry_run):
    src = Path(src_str)
    if dry_run:
        # (igual que hoy, pero el eco dice "en un lote nuevo <fecha>_manual_NN")
        ...
        return
    lote = intake_manual.abrir_lote_manual(ident.case_id, origen="abrir_caso_cli")
    try:
        rels = _depositar_manual(ident.case_id, src, lote)
    except FileNotFoundError as exc:
        ...
    hashes = {f"{lote.name}/{rel}": file_sha256(lote / rel) for rel in rels}
    _intake_generico(case_dir, ident.case_id, "manual", hashes,
                     base=lote.name, dry_run=False)


def _intake_email(ident, case_dir, cuenta, label, *, dry_run):
    if dry_run:
        typer.echo(f"[dry-run] email: se exportaría la etiqueta {label!r} de {cuenta} "
                   "a un lote nuevo 00_Input/<fecha>_email_NN (sin ejecutar)")
        return
    dest = email_export.email_dest_dir(ident.case_id)     # reserva el lote (T8)
    email_export.export_label(cuenta, label, dest, case_id=ident.case_id)
    typer.echo(f"Email: etiqueta {label!r} exportada a {dest}")
```

Nota: `save_file(case_id, filename, ...)` rechaza rutas con separadores; para conservar
subcarpetas del origen manual, añadir en T9 a `core/intake_manual.py` el helper fino
`save_file_en_lote(case_id, lote, rel, content) -> Path` (escribe `lote/rel` +
`_registrar_en_lote(...)`; MISMA validación anti path-traversal que `safe_zip_extract`:
rechaza `..` y rutas absolutas).

- [ ] **Step 4: Run** `python -m pytest tests/test_abrir_caso.py tests/test_intake_manual.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: PASS.
- [ ] **Step 5: Commit** `git add core/abrir_caso.py core/intake_manual.py scripts/abrir_caso.py tests/test_abrir_caso.py tests/test_intake_manual.py && git commit -m "feat(abrir-caso): vias manual/email por lote via dir_intake; fin de FUENTE_A_SUBDIR (T9)"`

---

### Task 10: `ensure_case` — eager→lazy en cajones de entrega

**Files:**
- Modify: `core/case_manager.py:274-280`
- Modify: `tests/test_intake_manual.py:232-237` (`TestEnsureCaseCrea04Manual` se INVIERTE, spec §9.6)
- Test: `tests/test_case_manager.py` (o el fichero donde viven los tests de `ensure_case`)

**Interfaces:**
- `ensure_case` deja de crear al alta: los 4 cajones de entrega, sus roles
  (`WHATSAPP_SUBDIRS`/`EMAIL_SUBDIRS`) y `01_Drive EV` (lazy: `intake_drive.pull_drive_ev` ya
  hace `mkdir(parents=True)`, `intake_drive.py:197`). La base `05_CRM` se mantiene eager
  (D7, `_ensure_crm_tree_dirs`, :283). `00_Input/` al alta queda **sin cajones de entrega**,
  no vacío (conserva `_caso.md` y protocolo).
- `config.INPUT_SUBDIRS` se CONSERVA (vocabulario legacy para `fuente_de` y la migración).

- [ ] **Step 1: Tests**

```python
# Invertir TestEnsureCaseCrea04Manual (tests/test_intake_manual.py:232):
class TestEnsureCaseNoCreaCajonesDeEntrega:
    def test_ensure_case_no_crea_cajones_de_entrega(self, tmp_casos_root):
        importlib.reload(case_manager)
        case_manager.ensure_case("NUEVO-MAN", titulo="Nuevo manual")
        input_dir = tmp_casos_root / "NUEVO-MAN" / "00_Input"
        for cajon in ("01_Drive EV", "02_Whatsapp", "03_Email",
                      "04_Manual", "06_Entrevistas"):
            assert not (input_dir / cajon).exists(), f"{cajon} debe ser lazy"
        # La base 05_CRM sigue eager (D7) y el protocolo de la raíz existe.
        assert (input_dir / "05_CRM").is_dir()
        assert (input_dir / "_caso.md").is_file()
```

- [ ] **Step 2: Run** `python -m pytest tests/test_intake_manual.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: FAIL (los cajones se crean).

- [ ] **Step 3: Implementación** — en `core/case_manager.py`, eliminar las líneas 274-280:

```python
    # (ELIMINADO — spec §8 «Scaffolding de ensure_case»: los cajones de entrega y
    # sus roles ya no se crean al alta; los lotes nacen con cada intake y
    # 01_Drive EV lo crea el pull. La base 05_CRM sigue eager (D7), justo abajo.)
```

(borrar los tres bucles `for intake_sub in INPUT_SUBDIRS`, `for sub3 in WHATSAPP_SUBDIRS`,
`for sub3 in EMAIL_SUBDIRS`; conservar `_ensure_crm_tree_dirs(case_dir)`).

- [ ] **Step 4: Run** `python -m pytest -q --tb=no --junit-xml=.pytest-task.xml` (SUITE COMPLETA —
  este cambio tiene radio amplio). Expected: verde; `test_smoke_paso7` (base `05_CRM`) NO cambia
  (spec §9.6). Cualquier test que dependa de un cajón eager se arregla creando el dir en el
  propio test (fixture) o migrando su assert al modelo lazy.
- [ ] **Step 5: Commit** `git add core/case_manager.py tests/ && git commit -m "feat(alta): ensure_case deja de crear cajones de entrega (lazy); 05_CRM eager intacto (T10)"`

---

### Task 11: Contrato `fuente_de` + adopción en los 3 lectores de metadatos

**Files:**
- Modify: `core/intake_lotes.py` (función `fuente_de`)
- Modify: `core/inventory.py:50-58` (`_source_of`)
- Modify: `core/catalogo_documental.py:22-29,58` (`_SOURCE_MAP` singular + `_map_source`)
- Modify: `.claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py:15-30`
- Test: `tests/test_intake_lotes.py`, `tests/test_inventory.py`, y el test anti-drift de la skill
  (junto al existente de `CAMPOS_EMITIDOS`)

**Interfaces:**
- Produces: `intake_lotes.fuente_de(rel_path: str) -> str` — orden de resolución (spec §8):
  1. primer segmento espejo → `01_Drive EV`→`drive_ev`, `05_CRM`→`crm`;
  2. patrón de lote → la fuente del nombre (el nombre manda);
  3. cajón legacy → mapa canónico (con `06_Entrevistas`→`entrevista` SINGULAR);
  4. fichero en raíz → `manual`.
  Primer segmento desconocido → `manual` (unifica el fallback; hoy divergían las 3 copias).
- `inventory.FileEntry.source` pasa a valores CANÓNICOS (`drive_ev`, no `01_Drive EV`) —
  cambio de contrato; `catalogo_documental._map_source` queda como tolerancia legacy
  (mapea nombres de cajón viejos persistidos y es identidad para los canónicos).
- El helper de la skill es SELF-CONTAINED (corre en Cowork sin `core/`): duplica la lógica con
  regex propia; el test anti-drift compara su salida contra `core.intake_lotes.fuente_de`.

- [ ] **Step 1: Tests que fallan**

```python
# tests/test_intake_lotes.py
def test_fuente_de_contrato_completo():
    from core.intake_lotes import fuente_de
    assert fuente_de("01_Drive EV/w/doc.pdf") == "drive_ev"          # espejo
    assert fuente_de("05_CRM/Civil/demanda.pdf") == "crm"            # espejo
    assert fuente_de("2026-07-17_whatsapp_01/00_Consultor propietario/c/_chat.txt") == "whatsapp"
    assert fuente_de("2026-07-17_email_02/a.eml") == "email"         # lote
    assert fuente_de("02_Whatsapp/rol/chat/_chat.txt") == "whatsapp" # cajón legacy
    assert fuente_de("06_Entrevistas/x.mp4") == "entrevista"         # SINGULAR (spec §4)
    assert fuente_de("suelto_en_raiz.pdf") == "manual"               # raíz
    assert fuente_de("CarpetaRara/x.pdf") == "manual"                # fallback unificado
    assert fuente_de("2026-07-17_manual_01\\a.pdf") == "manual"      # tolera backslash


# tests del helper de la skill (fichero de los tests anti-drift existentes):
def test_fuente_skill_sin_drift_con_core():
    import importlib.util
    from pathlib import Path
    from core.intake_lotes import fuente_de
    ruta = Path(".claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py")
    spec = importlib.util.spec_from_file_location("mac", ruta)
    mac = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mac)
    casos = ["01_Drive EV/a.pdf", "05_CRM/b.pdf", "2026-07-17_email_01/c.eml",
             "2026-07-17_whatsapp_02/rol/chat/_chat.txt", "02_Whatsapp/r/c/_chat.txt",
             "06_Entrevistas/g.mp4", "raiz.pdf", "Rara/x.pdf"]
    for c in casos:
        assert mac._fuente(c) == fuente_de(c), c
```

- [ ] **Step 2: Run** — Expected: FAIL.

- [ ] **Step 3: Implementación**

```python
# core/intake_lotes.py
ESPEJOS = {"01_Drive EV": "drive_ev", "05_CRM": "crm"}
CAJONES_LEGACY = {
    "01_Drive EV": "drive_ev", "02_Whatsapp": "whatsapp", "03_Email": "email",
    "04_Manual": "manual", "05_CRM": "crm", "06_Entrevistas": "entrevista",
}


def fuente_de(rel_path: str) -> str:
    """Fuente canónica de un rel_path bajo 00_Input/ (spec §8, contrato único).

    Sustituye a inventory._source_of, catalogo_documental._map_source y al
    _fuente del helper de organizar-sala-lectura.
    """
    partes = rel_path.replace("\\", "/").lstrip("/").split("/")
    if len(partes) < 2:
        return "manual"                       # fichero en la raíz
    top = partes[0]
    if top in ESPEJOS:
        return ESPEJOS[top]
    m = PATRON_LOTE.match(top)
    if m:
        return m.group(2)                     # el nombre del lote manda
    return CAJONES_LEGACY.get(top, "manual")
```

```python
# core/inventory.py — _source_of delega:
def _source_of(rel_parts: tuple[str, ...]) -> str:
    from .intake_lotes import fuente_de
    return fuente_de("/".join(rel_parts))
```

```python
# core/catalogo_documental.py — singular + identidad para canónicos:
_SOURCE_MAP = {
    "01_Drive EV": "drive_ev", "02_Whatsapp": "whatsapp", "03_Email": "email",
    "04_Manual": "manual", "05_CRM": "crm", "06_Entrevistas": "entrevista",
}
# _map_source(:58) queda igual (get con passthrough): con inventory ya canónico
# es identidad; el mapa solo tolera inventarios viejos persistidos.
```

```python
# .claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py
import re
_PATRON_LOTE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(whatsapp|email|manual|entrevista)_(\d{2,})$")
_SOURCE_MAP = {
    "01_Drive EV": "drive_ev", "02_Whatsapp": "whatsapp", "03_Email": "email",
    "04_Manual": "manual", "05_CRM": "crm", "06_Entrevistas": "entrevista",
}


def _fuente(ruta_rel: str) -> str:
    partes = ruta_rel.replace("\\", "/").lstrip("/").split("/")
    if len(partes) < 2:
        return "manual"
    top = partes[0]
    m = _PATRON_LOTE.match(top)
    if m:
        return m.group(2)
    return _SOURCE_MAP.get(top, "manual")
```

- [ ] **Step 4: Run** `python -m pytest tests/test_intake_lotes.py tests/test_inventory.py tests/test_catalogo_documental.py -q --tb=short --junit-xml=.pytest-task.xml` + el fichero del test anti-drift — Expected: PASS (actualizar los asserts de `source`/`fuente` que esperaban valores de cajón o el plural `entrevistas`).
- [ ] **Step 5: Commit** `git add core/intake_lotes.py core/inventory.py core/catalogo_documental.py .claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py tests/ && git commit -m "feat(lectura): contrato unico fuente_de + entrevista singular; adopcion en inventory/catalogo/skill (T11)"`

---

### Task 12: Lectores — descubrimiento mínimo en lotes (`whatsapp_atomize`, `email_atomize`)

**Files:**
- Modify: `core/whatsapp_atomize/pipeline.py:22-31` (`descubrir_chats`)
- Modify: `core/email_atomize/pipeline.py:61-83,265-276` (`atomize_dir` multi-src,
  `emails_src_dirs`, `atomize_case`)
- Test: `tests/test_whatsapp_atomize*.py`, `tests/test_email_atomize*.py` (los ficheros de esas
  suites en `tests/`)

**Interfaces:**
- Produces:
  - `descubrir_chats(case_dir) -> list[Path]` — carpetas con `_chat.txt` bajo el cajón legacy
    `00_Input/02_Whatsapp/` **y** bajo cada lote `whatsapp` de `00_Input/`. Orden estable por
    nombre. (Clasificación fina/colisiones de chat re-entregado = #55/#56, fuera de alcance.)
  - `email_atomize.pipeline.emails_src_dirs(case_id) -> list[Path]` — lotes `email` + legacy
    `03_Email` (los que existan).
  - `atomize_dir(src_dir: Path | str | Sequence[Path | str], out_dir, *, case_dir=None)` —
    acepta varias fuentes; los avistamientos se concatenan y `colapsar` (por Message-ID) hace el
    resto. `atomize_case` pasa `emails_src_dirs(case_id)`.
  - `core/sala_maquina.py` NO cambia (inventaría `00_Input/` recursivo, spec §8).

- [ ] **Step 1: Tests que fallan**

```python
# suite whatsapp_atomize
def test_descubrir_chats_ve_lotes_y_legacy(tmp_path):
    from core.whatsapp_atomize.pipeline import descubrir_chats
    legacy = tmp_path / "00_Input" / "02_Whatsapp" / "03_Otros" / "chat_viejo"
    legacy.mkdir(parents=True)
    (legacy / "_chat.txt").write_text("x", encoding="utf-8")
    lote = (tmp_path / "00_Input" / "2026-07-17_whatsapp_01"
            / "00_Consultor propietario" / "chat_nuevo")
    lote.mkdir(parents=True)
    (lote / "_chat.txt").write_text("y", encoding="utf-8")
    otros = tmp_path / "00_Input" / "2026-07-17_manual_01"   # lote NO whatsapp: fuera
    otros.mkdir(parents=True)
    (otros / "_chat.txt").write_text("z", encoding="utf-8")
    nombres = {p.name for p in descubrir_chats(tmp_path)}
    assert nombres == {"chat_viejo", "chat_nuevo"}


# suite email_atomize
def test_emails_src_dirs_lotes_y_legacy(tmp_casos_root):
    from core import case_manager
    from core.email_atomize.pipeline import emails_src_dirs
    case_manager.ensure_case("EV-EA-001", titulo="ea")
    base = tmp_casos_root / "EV-EA-001" / "00_Input"
    (base / "03_Email").mkdir(parents=True)
    (base / "2026-07-17_email_01").mkdir()
    (base / "2026-07-17_whatsapp_01").mkdir()               # no email: fuera
    dirs = {d.name for d in emails_src_dirs("EV-EA-001")}
    assert dirs == {"2026-07-17_email_01", "03_Email"}


def test_atomize_dir_acepta_varias_fuentes(tmp_path):
    from core.email_atomize.pipeline import atomize_dir
    d1, d2, out = tmp_path / "l1", tmp_path / "l2", tmp_path / "out"
    d1.mkdir(); d2.mkdir()
    (d1 / "a.eml").write_bytes(_EML_A)      # raws sintéticos con Message-ID distintos
    (d2 / "b.eml").write_bytes(_EML_B)
    report = atomize_dir([d1, d2], out, case_dir=tmp_path)
    assert len(list((out / "mensajes").glob("*.md"))) == 2
```

- [ ] **Step 2: Run** — Expected: FAIL.

- [ ] **Step 3: Implementación**

```python
# core/whatsapp_atomize/pipeline.py
from core.intake_lotes import PATRON_LOTE

def descubrir_chats(case_dir: Path) -> list[Path]:
    """Carpetas con _chat.txt: cajón legacy 02_Whatsapp + lotes whatsapp (spec §8)."""
    input_dir = case_dir / "00_Input"
    bases: list[Path] = []
    legacy = case_dir.joinpath(*_WHATSAPP_IN)
    if legacy.exists():
        bases.append(legacy)
    if input_dir.is_dir():
        bases += [d for d in input_dir.iterdir() if d.is_dir()
                  and (m := PATRON_LOTE.match(d.name)) and m.group(2) == "whatsapp"]
    dirs = {p.parent for base in bases for p in base.rglob("_chat.txt")}
    return sorted(dirs, key=lambda x: x.name)
```

```python
# core/email_atomize/pipeline.py
def emails_src_dirs(case_id: str) -> list[Path]:
    """Fuentes de .eml del caso: lotes email de 00_Input/ + cajón legacy 03_Email."""
    from core.casos.case_locator import path_for, resolve_ref
    from core.intake_lotes import PATRON_LOTE
    input_dir = path_for(resolve_ref(case_id)) / "00_Input"
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


def atomize_dir(src_dir, out_dir, *, case_dir=None) -> AtomizeReport:
    srcs = [Path(s) for s in src_dir] if isinstance(src_dir, (list, tuple)) \
        else [Path(src_dir)]
    # ... (resto igual; sustituir la línea 83)
    avistamientos = [a for s in srcs for a in E.iter_avistamientos(s)]


def atomize_case(case_id: str) -> AtomizeReport:
    return atomize_dir(emails_src_dirs(case_id), emails_out_dir(case_id))
```

(`emails_src_dir` singular :265 se elimina; si algún caller externo lo usa —`grep`—, se actualiza
en el mismo commit.)

- [ ] **Step 4: Run** las dos suites + `python -m pytest tests/test_sala_maquina.py -q --tb=no --junit-xml=.pytest-task.xml` (no debe cambiar) — Expected: PASS.
- [ ] **Step 5: Commit** `git add core/whatsapp_atomize/pipeline.py core/email_atomize/pipeline.py tests/ && git commit -m "feat(lectores): descubrimiento de chats/.eml en lotes + cajon legacy (T12)"`

---

### Task 13: Migración bajo demanda (1/2) — cerebro puro `core/migrar_layout.py`

**Files:**
- Create: `core/migrar_layout.py`
- Test: `tests/test_migrar_layout.py` (crear)

**Interfaces:**
- Produces (puro, sin tocar disco salvo lectura en `estimar_fecha`):
  - `CAJONES_ENTREGA = {"02_Whatsapp": "whatsapp", "03_Email": "email",
    "04_Manual": "manual", "06_Entrevistas": "entrevista"}` — SOLO entrega; espejos jamás (§7.1).
  - `estimar_fecha(cajon_dir: Path) -> str` — la MÁS ANTIGUA entre (a) fechas ISO en nombres de
    fichero (`AAAA-MM-DD_…`, nomenclatura del despacho) y (b) el mtime, sobre el contenido (§7.3).
  - `plan_migracion(input_dir: Path) -> list[MovimientoCajon]` con
    `@dataclass MovimientoCajon(cajon: str, fuente: str, lote: str, mapping: dict[str, str])`
    — `mapping` = rel viejo→nuevo (relativos a `00_Input/`, POSIX) de TODOS los ficheros del
    cajón (control incluido — también hay que moverlos o recolocarlos).
  - `remap_paths(data: dict, mapping: dict[str, str]) -> tuple[dict, int]` — reescribe
    `primary_path` y `aliases[].path` de un dict M9 (§7.4a); devuelve (data, n_remapeados).
  - `remap_cobertura(rows: list[dict], mapping: dict[str, str]) -> tuple[list[dict], int]` —
    reescribe `rel_path` de `_cobertura.json` (§7.4b; la fusión acumulativa casa por `rel_path`,
    `core/sala_maquina.py:157-185` — sin esto un caso procesado se re-OCRearía entero).
  - `remap_catalogo(entries: list[dict], mapping: dict[str, str]) -> tuple[list[dict], int]` —
    reescribe `ruta_relativa` de `indice_documental.yaml` (§7.4c). OJO: las rutas del catálogo
    llevan prefijo `00_Input/` o no según el caso — respetar el formato encontrado (probar ambos
    en el test con el formato real que emite `catalogo_documental`).

- [ ] **Step 1: Tests que fallan**

```python
# tests/test_migrar_layout.py
from pathlib import Path

from core import migrar_layout as ml


def _cajon(tmp_path, nombre, ficheros):
    d = tmp_path / "00_Input" / nombre
    for rel, contenido in ficheros.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contenido)
    return d


def test_estimar_fecha_prefiere_la_mas_antigua_de_nombres(tmp_path):
    d = _cajon(tmp_path, "04_Manual",
                {"2026-03-05_demanda.pdf": b"a", "2026-01-10_encargo.pdf": b"b"})
    assert ml.estimar_fecha(d) == "2026-01-10"


def test_plan_migracion_solo_cajones_de_entrega(tmp_path):
    _cajon(tmp_path, "04_Manual", {"a.pdf": b"a"})
    _cajon(tmp_path, "01_Drive EV", {"w/doc.pdf": b"d"})      # espejo: NO se toca
    _cajon(tmp_path, "05_CRM", {"General/x.pdf": b"x"})       # espejo: NO se toca
    _cajon(tmp_path, "02_Whatsapp", {})                       # vacío: sin lote
    plan = ml.plan_migracion(tmp_path / "00_Input")
    assert [m.cajon for m in plan] == ["04_Manual"]
    mov = plan[0]
    assert mov.fuente == "manual"
    assert mov.lote.endswith("_manual_01")
    assert mov.mapping == {"04_Manual/a.pdf": f"{mov.lote}/a.pdf"}


def test_remap_paths_m9():
    data = {"sha1": {"primary_path": "04_Manual/a.pdf",
                     "aliases": [{"path": "03_Email/x/a.pdf", "source": "email"}]}}
    mapping = {"04_Manual/a.pdf": "2026-01-10_manual_01/a.pdf",
               "03_Email/x/a.pdf": "2026-01-10_email_01/x/a.pdf"}
    out, n = ml.remap_paths(data, mapping)
    assert out["sha1"]["primary_path"] == "2026-01-10_manual_01/a.pdf"
    assert out["sha1"]["aliases"][0]["path"] == "2026-01-10_email_01/x/a.pdf"
    assert n == 2


def test_remap_cobertura_por_rel_path():
    rows = [{"rel_path": "04_Manual/a.pdf", "slug": "a_12345678", "estado": "ok"},
            {"rel_path": "01_Drive EV/w/doc.pdf", "slug": "doc_87654321", "estado": "ok"}]
    out, n = ml.remap_cobertura(rows, {"04_Manual/a.pdf": "2026-01-10_manual_01/a.pdf"})
    assert out[0]["rel_path"] == "2026-01-10_manual_01/a.pdf"
    assert out[1]["rel_path"] == "01_Drive EV/w/doc.pdf"      # espejo intacto
    assert n == 1
```

- [ ] **Step 2: Run** `python -m pytest tests/test_migrar_layout.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: FAIL (módulo no existe).

- [ ] **Step 3: Implementación**

```python
# core/migrar_layout.py
"""Cerebro puro de la migración bajo demanda a lotes (spec §7, MEJORAS #54).

Envuelve los cajones de ENTREGA con contenido en lotes sintéticos y calcula
el remapeo viejo→nuevo para los registros aguas abajo (M9, cobertura OCR,
catálogo). Los ESPEJOS (01_Drive EV, 05_CRM) no se tocan JAMÁS.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CAJONES_ENTREGA = {
    "02_Whatsapp": "whatsapp", "03_Email": "email",
    "04_Manual": "manual", "06_Entrevistas": "entrevista",
}
_FECHA_EN_NOMBRE = re.compile(r"^(\d{4}-\d{2}-\d{2})_")


@dataclass(frozen=True)
class MovimientoCajon:
    cajon: str
    fuente: str
    lote: str
    mapping: dict[str, str]     # rel viejo → rel nuevo (relativos a 00_Input/)


def estimar_fecha(cajon_dir: Path) -> str:
    """fecha_intake estimada (§7.3): mín(fechas ISO en nombres, mtimes)."""
    candidatas: list[str] = []
    for p in cajon_dir.rglob("*"):
        if not p.is_file():
            continue
        m = _FECHA_EN_NOMBRE.match(p.name)
        if m:
            candidatas.append(m.group(1))
        candidatas.append(
            datetime.fromtimestamp(p.stat().st_mtime).date().isoformat())
    return min(candidatas) if candidatas else datetime.now().date().isoformat()


def plan_migracion(input_dir: Path) -> list[MovimientoCajon]:
    """Un lote sintético <fecha>_<fuente>_01 por cajón de entrega CON contenido."""
    movimientos: list[MovimientoCajon] = []
    for cajon, fuente in CAJONES_ENTREGA.items():
        d = input_dir / cajon
        ficheros = [p for p in d.rglob("*") if p.is_file()] if d.is_dir() else []
        if not ficheros:
            continue
        lote = f"{estimar_fecha(d)}_{fuente}_01"
        mapping = {
            f"{cajon}/{p.relative_to(d).as_posix()}":
            f"{lote}/{p.relative_to(d).as_posix()}"
            for p in sorted(ficheros)
        }
        movimientos.append(MovimientoCajon(cajon, fuente, lote, mapping))
    return movimientos


def remap_paths(data: dict, mapping: dict[str, str]) -> tuple[dict, int]:
    """Reescribe primary_path/aliases[].path del M9 (§7.4a). Muta y devuelve."""
    n = 0
    for entry in data.values():
        p = entry.get("primary_path")
        if p in mapping:
            entry["primary_path"] = mapping[p]
            n += 1
        for alias in entry.get("aliases") or []:
            if isinstance(alias, dict) and alias.get("path") in mapping:
                alias["path"] = mapping[alias["path"]]
                n += 1
    return data, n


def remap_cobertura(rows: list[dict], mapping: dict[str, str]) -> tuple[list[dict], int]:
    """Reescribe rel_path de _cobertura.json (§7.4b)."""
    n = 0
    for row in rows:
        if row.get("rel_path") in mapping:
            row["rel_path"] = mapping[row["rel_path"]]
            n += 1
    return rows, n


def remap_catalogo(entries: list[dict], mapping: dict[str, str]) -> tuple[list[dict], int]:
    """Reescribe ruta_relativa del catálogo (§7.4c), con o sin prefijo 00_Input/."""
    n = 0
    for e in entries:
        ruta = e.get("ruta_relativa") or ""
        sin_prefijo = ruta[len("00_Input/"):] if ruta.startswith("00_Input/") else ruta
        if sin_prefijo in mapping:
            nuevo = mapping[sin_prefijo]
            e["ruta_relativa"] = f"00_Input/{nuevo}" if ruta.startswith("00_Input/") else nuevo
            n += 1
    return entries, n
```

- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `git add core/migrar_layout.py tests/test_migrar_layout.py && git commit -m "feat(migracion): cerebro puro plan_migracion + remapeos M9/cobertura/catalogo (T13)"`

---

### Task 14: Migración bajo demanda (2/2) — CLI `scripts/migrar_layout_intake.py`

**Files:**
- Create: `scripts/migrar_layout_intake.py`
- Test: `tests/test_migrar_layout.py`

**Interfaces:**
- Consumes: `core/migrar_layout.py` (T13), `intake_lotes.escribir_manifiesto`/`items_desde_disco`
  (T3), `case_manager.leer_estado_repositorio`, `intake_log.append_event`.
- Produces: `python -m scripts.migrar_layout_intake <case_id> [--dry-run]`:
  1. **Aborta** (exit 1, mensaje claro) si el caso está `prestado` o `conflicto` (§7.6).
  2. Ejecuta `plan_migracion`; por movimiento: mueve el CONTENIDO del cajón a la raíz del lote
     (`shutil.move` por hijo de primer nivel — conserva subcarpetas de rol); el cajón queda
     vacío y NO se borra (§7.2, §10).
  3. Los ficheros de control del canal email que estuvieran en `03_Email/`
     (`_exported_ids.json`, `_resolved_links.json`) se mueven a la raíz de `00_Input/`
     (su hogar desde T7), NO al lote.
  4. Escribe el manifiesto sintético del lote: `items_desde_disco(lote)` +
     `escribir_manifiesto(..., fecha_intake=<estimada>, origen="migracion_layout",
     fecha_intake_estimada=True)` (§7.3).
  5. Remapea con el `mapping` agregado: `00_Input/_intake_hashes.json` (leer JSON →
     `remap_paths` → escribir atómico), `01_Procesado/02_Sala de máquina/_cobertura.json`
     (`remap_cobertura`) y `01_Procesado/indice_documental.yaml` (`remap_catalogo`) — solo los
     que existan (§7.4).
  6. Protocolo de la raíz (`_caso.md`, `_intake_log.jsonl`, `_intake_hashes.json`) NO se mueve
     (§7.5). Emite `intake_log.append_event(case_id, "migracion_layout_intake",
     details={"lotes": [...], "remapeados": {...}})`. `INTAKE_EVENTS`
     (`core/intake_log.py:42`) es un frozenset CERRADO que valida con `ValueError` (:164):
     añadir el literal `"migracion_layout_intake"` a ese frozenset en el mismo commit, con su
     comentario de shape de `details` (evento nuevo, NO cambio de esquema del log — el esquema
     `{ts, actor, event, case_id, details}` no se toca).
  7. `--dry-run`: imprime el plan (cajón → lote, nº ficheros, remapeos) sin tocar nada.

- [ ] **Step 1: Test de integración que falla** (fixture spec §9.4: 4 cajones de entrega
  poblados + espejos poblados + registros aguas abajo)

```python
def test_migracion_integral_espejos_intactos_y_remapeo(tmp_casos_root):
    import json

    import yaml

    from core import case_manager, config
    from core.intake_lotes import PATRON_LOTE, leer_manifiesto
    from scripts.migrar_layout_intake import migrar

    case_id = "EV-MIG-001"
    case_manager.ensure_case(case_id, titulo="mig")
    base = config.caso_path(case_id) / "00_Input"
    # entrega (4 cajones) + espejos poblados
    for rel, b in {
        "02_Whatsapp/03_Otros/chat/_chat.txt": b"c",
        "03_Email/2026-02-01_asunto.eml": b"e",
        "03_Email/_exported_ids.json": b"{}",
        "04_Manual/2026-01-10_demanda.pdf": b"m",
        "06_Entrevistas/grabacion.mp4": b"g",
        "01_Drive EV/w/doc.pdf": b"d",
        "05_CRM/General/x.pdf": b"x",
    }.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    # registros aguas abajo
    (base / "_intake_hashes.json").write_text(json.dumps({
        "sha-m": {"primary_path": "04_Manual/2026-01-10_demanda.pdf", "aliases": []}}),
        encoding="utf-8")
    maq = config.caso_path(case_id) / "01_Procesado" / "02_Sala de máquina"
    maq.mkdir(parents=True)
    (maq / "_cobertura.json").write_text(json.dumps(
        [{"rel_path": "04_Manual/2026-01-10_demanda.pdf", "slug": "s", "estado": "ok"}]),
        encoding="utf-8")

    migrar(case_id, dry_run=False)

    # espejos y protocolo intactos
    assert (base / "01_Drive EV" / "w" / "doc.pdf").is_file()
    assert (base / "05_CRM" / "General" / "x.pdf").is_file()
    assert (base / "_caso.md").is_file()
    # los 4 cajones envueltos en lotes sintéticos con manifiesto estimado
    lotes = [d for d in base.iterdir() if d.is_dir() and PATRON_LOTE.match(d.name)]
    assert {PATRON_LOTE.match(d.name).group(2) for d in lotes} \
        == {"whatsapp", "email", "manual", "entrevista"}
    lote_manual = next(d for d in lotes if "_manual_" in d.name)
    assert lote_manual.name.startswith("2026-01-10")          # fecha del nombre de fichero
    assert leer_manifiesto(lote_manual)["fecha_intake_estimada"] is True
    # cajón vacío pero NO borrado; índice de canal movido a la raíz
    assert (base / "04_Manual").is_dir()
    assert not any((base / "04_Manual").iterdir())
    assert (base / "_exported_ids.json").is_file()
    # remapeo round-trip (§9.4): M9 y cobertura casan con el disco nuevo
    m9 = json.loads((base / "_intake_hashes.json").read_text(encoding="utf-8"))
    nuevo_rel = m9["sha-m"]["primary_path"]
    assert nuevo_rel.startswith("2026-01-10_manual_01/") and (base / nuevo_rel).is_file()
    cob = json.loads((maq / "_cobertura.json").read_text(encoding="utf-8"))
    assert cob[0]["rel_path"] == nuevo_rel


def test_migracion_aborta_con_caso_prestado(tmp_casos_root):
    import pytest

    from core import case_manager
    from scripts.migrar_layout_intake import CasoPrestadoError, migrar

    case_id = "EV-MIG-002"
    case_manager.ensure_case(case_id, titulo="mig")
    case_manager.escribir_lock(case_id, user="Nikolai Tyukhay",
                               timestamp="2026-07-17T09:00:00Z", nonce="n")
    with pytest.raises(CasoPrestadoError):
        migrar(case_id, dry_run=False)
```

- [ ] **Step 2: Run** — Expected: FAIL.

- [ ] **Step 3: Implementación**

```python
# scripts/migrar_layout_intake.py
"""Migración BAJO DEMANDA de un caso al layout de lotes (spec §7, MEJORAS #54).

Se dispara SOLO cuando el caso recibe un intake nuevo — nunca de oficio ni en
barrido. Envuelve los cajones de entrega en lotes sintéticos y remapea los
registros aguas abajo (M9, cobertura OCR, catálogo). Espejos y protocolo
intactos. Correr TRAS el checkin si el caso estaba prestado.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer
import yaml

from core import config, intake_log, intake_lotes, migrar_layout
from core.case_manager import leer_estado_repositorio
from core.config import caso_path

app = typer.Typer(add_completion=False)


class CasoPrestadoError(RuntimeError):
    """El caso está prestado/conflicto: migrar tras el checkin (§7.6)."""


def _json_atomico(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
                   encoding="utf-8")
    tmp.replace(path)


def migrar(case_id: str, *, dry_run: bool) -> list[migrar_layout.MovimientoCajon]:
    estado = leer_estado_repositorio(case_id)
    if estado in ("prestado", "conflicto"):
        raise CasoPrestadoError(
            f"El caso está '{estado}': la migración se corre tras el checkin "
            "(desviar medio árbol a la bandeja no tiene sentido, spec §7.6).")
    base = caso_path(case_id) / "00_Input"
    plan = migrar_layout.plan_migracion(base)
    if dry_run or not plan:
        return plan

    mapping_total: dict[str, str] = {}
    for mov in plan:
        cajon_dir, lote_dir = base / mov.cajon, base / mov.lote
        lote_dir.mkdir(parents=True, exist_ok=False)
        for hijo in sorted(cajon_dir.iterdir()):
            if (mov.cajon == "03_Email"
                    and hijo.name in config.INTAKE_CONTROL_FILES):
                # estado de canal → raíz de 00_Input (hogar desde #54), no al lote
                destino = base / hijo.name
                if not destino.exists():
                    shutil.move(str(hijo), str(destino))
                else:
                    hijo.unlink()          # ya consolidado en la raíz
                continue
            shutil.move(str(hijo), str(lote_dir / hijo.name))
        intake_lotes.escribir_manifiesto(
            lote_dir, fuente=mov.fuente, fecha_intake=mov.lote[:10],
            origen="migracion_layout",
            items=intake_lotes.items_desde_disco(lote_dir),
            fecha_intake_estimada=True)
        mapping_total.update(mov.mapping)

    remapeados: dict[str, int] = {}
    m9_path = base / "_intake_hashes.json"
    if m9_path.is_file():
        data = json.loads(m9_path.read_text(encoding="utf-8") or "{}")
        data, remapeados["m9"] = migrar_layout.remap_paths(data, mapping_total)
        _json_atomico(m9_path, data)
    cob_path = (caso_path(case_id) / "01_Procesado" / "02_Sala de máquina"
                / "_cobertura.json")
    if cob_path.is_file():
        rows = json.loads(cob_path.read_text(encoding="utf-8") or "[]")
        rows, remapeados["cobertura"] = migrar_layout.remap_cobertura(rows, mapping_total)
        _json_atomico(cob_path, rows)
    cat_path = caso_path(case_id) / "01_Procesado" / "indice_documental.yaml"
    if cat_path.is_file():
        entries = yaml.safe_load(cat_path.read_text(encoding="utf-8")) or []
        entries, remapeados["catalogo"] = migrar_layout.remap_catalogo(
            entries, mapping_total)
        cat_path.write_text(
            yaml.dump(entries, allow_unicode=True, default_flow_style=False,
                      sort_keys=False), encoding="utf-8")

    intake_log.append_event(case_id, "migracion_layout_intake", details={
        "lotes": [m.lote for m in plan], "remapeados": remapeados})
    return plan


@app.command()
def main(case_id: str, dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    try:
        plan = migrar(case_id, dry_run=dry_run)
    except CasoPrestadoError as exc:
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=1)
    if not plan:
        typer.echo("Nada que migrar: sin cajones de entrega con contenido.")
        return
    for mov in plan:
        typer.echo(f"{'[dry-run] ' if dry_run else ''}{mov.cajon} → {mov.lote} "
                   f"({len(mov.mapping)} ficheros)")


if __name__ == "__main__":
    app()
```

Y en `core/intake_log.py:42`, dentro del frozenset `INTAKE_EVENTS`:

```python
    "migracion_layout_intake",  # migración bajo demanda a lotes (#54): details =
                                # {"lotes": [nombres], "remapeados": {registro: n}}
```

- [ ] **Step 4: Run** `python -m pytest tests/test_migrar_layout.py -q --tb=short --junit-xml=.pytest-task.xml` — Expected: PASS.
- [ ] **Step 5: Commit** `git add scripts/migrar_layout_intake.py core/intake_log.py tests/test_migrar_layout.py && git commit -m "feat(migracion): scripts.migrar_layout_intake bajo demanda con remapeo y abort si prestado (T14)"`

---

### Task 15: Skills — textos al modelo de lote + re-empaquetado

**Files:**
- Modify: `.claude/skills/intake-expediente/SKILL.md` (líneas 43-44, 66-79: destino por fuente)
- Modify: `.claude/skills/organizar-sala-lectura/SKILL.md` (enumeración de cajones)
- Modify: `.claude/skills/triaje-viabilidad/SKILL.md`, `.claude/skills/viabilidad-prerelleno/SKILL.md`,
  `.claude/skills/preparacion-audiencia-previa/SKILL.md`,
  `.claude/skills/exportar-correos-etiqueta/SKILL.md` (referencias a `00_Input/03_Email` y cajones)
- Test: no hay pytest para prosa; el helper de `organizar-sala-lectura` ya quedó cubierto en T11.

- [ ] **Step 1: Actualizar los textos.** En cada `SKILL.md`, localizar (con `Grep` sobre
  `.claude/skills/`: patrón `0[1-6]_(Drive EV|Whatsapp|Email|Manual|CRM|Entrevistas)`) las
  enumeraciones del layout viejo y sustituirlas por el modelo dual, con esta redacción base
  (adaptada al contexto de cada skill):

  > `00_Input/` tiene dos formas de canal: **lotes de entrega**
  > `<AAAA-MM-DD>_<fuente>_<NN>/` (fuentes `whatsapp`, `email`, `manual`, `entrevista`; cada
  > lote lleva `_manifiesto.yaml` con `tipo_contenido` por ítem) y **cajones espejo** fijos
  > `01_Drive EV/` y `05_CRM/` (sync incremental). Los casos antiguos no migrados conservan los
  > cajones `02_Whatsapp/`, `03_Email/`, `04_Manual/`, `06_Entrevistas/`: leer AMBAS formas.
  > La fuente de un fichero se deriva de su primer segmento de ruta (espejo → lote → cajón
  > legacy → raíz=manual).

  En `intake-expediente` además: el depósito dirigido crea el lote
  (`create` del directorio `<AAAA-MM-DD>_<fuente>_<NN>` con NN siguiente al mayor existente
  ese día), deposita verbatim dentro y escribe `_manifiesto.yaml`; los espejos (`01_Drive EV`,
  `05_CRM`) NO reciben depósitos de esta skill salvo el flujo CRM ya documentado. En
  `exportar-correos-etiqueta`: el motor local escribe en un lote email nuevo por corrida y los
  índices viven en `01_Procesado/Emails/`.

- [ ] **Step 2: Verificación de coherencia.** `Grep '02_Whatsapp|03_Email|04_Manual|06_Entrevistas' .claude/skills/ --files-with-matches` — cada hit restante debe ser una mención deliberada del modo legacy (revisión manual).
- [ ] **Step 3: Re-empaquetar** (superficie que no se actualiza con el repo, spec §8):
  `python scripts/package_skill.py .claude/skills/intake-expediente` e ídem para
  `organizar-sala-lectura`, `triaje-viabilidad`, `viabilidad-prerelleno`,
  `preparacion-audiencia-previa`, `exportar-correos-etiqueta` (comprobar la firma real del
  script con `python scripts/package_skill.py --help` y usar la ruta de salida canónica
  `dist_skills/`). La RE-IMPORTACIÓN en Cowork es paso operativo de Nikolai (queda anotado en
  `PLAN.md`, sección `[SIGUIENTE-INPUT-LOTES]`).
- [ ] **Step 4: Run** `python -m pytest tests/ -q --tb=no -k "skill or helpers" --junit-xml=.pytest-task.xml` (tests de paridad/anti-drift de skills) — Expected: verde.
- [ ] **Step 5: Commit** `git add .claude/skills/ dist_skills/ && git commit -m "docs(skills): layout dual lote+espejo en 6 skills + reempaquetado (T15)"`

---

### Task 16: Cierre — suite completa, self-review contra la spec y PR

**Files:**
- Modify: `PLAN.md` (sección `[SIGUIENTE-INPUT-LOTES]`: marcar construcción hecha al mergear)
- Test: suite completa

- [ ] **Step 1: Suite completa** — `python -m pytest -q --tb=no --junit-xml=.pytest-full.xml` y
  leer el XML: `failures="0" errors="0"`. Cualquier desviación del conteo esperado se explica
  en el PR (regla de `CLAUDE.md`).
- [ ] **Step 2: Checklist spec §9** (verificación punto a punto, con el test que lo cubre):
  1. nombre/colisión/atomicidad/bandeja → `tests/test_intake_lotes.py` (T2);
  2. manifiesto round-trip/exclusiones/message_id → T3, T8;
  3. dedup M9: copia+anota, Message-ID, tamaño 0, espejos intactos → T4, T5, T6, T7;
  4. migración integral con espejos poblados + round-trip de cobertura + abort → T14;
  5. email incremental con lotes + cronología completa → T8;
  6. `TestEnsureCase…` invertido (T10), guard wiring actualizado (T5/T8), `test_smoke_paso7`
     intacto (T10).
- [ ] **Step 3: Higiene** — `git status` sin restos (`.pytest-task.xml`/`.pytest-full.xml` no
  commiteados); `pre-commit run --all-files` verde.
- [ ] **Step 4: PR** — usar la skill `superpowers:finishing-a-development-branch`: push de la
  rama, `gh pr create` a `main` (título:
  `Layout 00_Input por lotes — implementación (MEJORAS #54, spec rev 2)`), esperar `leak-scan`.
  NO mergear sin revisión de Nikolai.
- [ ] **Step 5: Tras el merge (sesión de cierre)** — `PLAN.md`: `[x]` construcción + hash del
  squash; `STATUS.md` vía `python -m scripts.session_close`. Paso operativo pendiente de
  Nikolai: re-importar las 6 skills en Cowork.

---

## Self-review (hecho al redactar; re-verificar al ejecutar)

- **Cobertura spec:** §4→T2; §5→T1/T3; §6→T4/T5/T6/T7; §7→T13/T14; §8 escritores→T5/T6/T7/T8/T9,
  espejos→sin tarea (constraint), `fuente_de`→T11, lectores→T12, `ensure_case`→T10, skills→T15;
  §9→T16 checklist; §10 respetado (sin tareas para #53/#55/#56).
- **Decisión consciente (anotar en el PR):** la idempotencia de canal se conserva (zip whatsapp
  byte-idéntico y `gmail_id` ya exportado NO re-entran — es el estado incremental del canal,
  spec §2/§8); la regla «el duplicado se copia» aplica a lo que SÍ se deposita (cross-lote y
  cross-canal), incluido el correo con mismo Message-ID y bytes distintos (§9.3).
- **Tipos consistentes entre tareas:** `ItemManifiesto`/`reservar_lote`/`PATRON_LOTE` (T2/T3)
  consumidos con esos nombres en T5-T9 y T12-T14; `duplicado_de_para(sha, size, message_id)`
  (T4) en T5/T6/T7; `write_indices_caso` (T8) solo en email.
- **Sin placeholders:** todo paso de código lleva el código; el único punto que depende de
  detalle no leído del repo (firma exacta de `package_skill.py`, T15) trae la instrucción de
  verificación (`--help`) y la ruta de salida canónica (`dist_skills/`).
