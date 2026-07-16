# MCP "Drive como disco" V1 — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidar `expedientes-xl` como único servidor MCP de filesystem sobre las dos
Drives montadas (`G:` rw, `H:` ro), con zonas por tier, oráculo de hidratación y guardas
Stream-aware, según el spec rev 3.

**Architecture:** Extender el plugin standalone `plugins/expedientes_xl/` (Python puro +
FastMCP) con módulos nuevos de lógica pura (`tiers.py`, `oracle.py`, `guards.py`,
`readops.py`, `winio.py`, `audit.py`) y recablear `server.py`. El servidor estándar
`expedientes` se jubila al final (secuencia §8 del spec). El checkin autoritativo sigue
por rclone: este plan NO toca core/ ni las skills.

**Tech Stack:** Python 3 (stdlib + `mcp.server.fastmcp`, ya en requirements), pytest,
SQLite (stdlib), PowerShell/COM solo para `resolve_shortcut`.

**Spec:** `docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-design.md` (rev 3).

## Global Constraints

- Windows + PowerShell; encoding SIEMPRE UTF-8 sin BOM.
- Docstrings y mensajes en castellano; estilo del plugin existente (`fsops.py`: lógica
  pura, sin dependencias de `mcp` ni de `core/`).
- El plugin es STANDALONE: no puede importar `core/` en runtime. La sincronía con
  `core.config.MERGE_EXCLUSIONS` se garantiza por TEST (que sí corre en el repo).
- Sin dependencias nuevas en `plugins/expedientes_xl/requirements.txt`.
- Nombres de tool EXISTENTES se conservan: `hash_path`, `hash_tree`, `copy_path`,
  `copy_dir`, `extract_archive`, `write_file_base64`, `append_text`. `delete_path` se
  RETIRA.
- Variables de entorno del plugin con prefijo `XL_`: `XL_AUDIT_PATH`, `XL_ORACLE_TTL`
  (def. 5), `XL_HYDRATION_MAX_FILE_MB` (def. 10), `XL_TREE_MAX_MB` (def. 150),
  `XL_TREE_MAX_COLD` (def. 50), `XL_ORACLE_STRICT` (def. 0), `XL_READ_MAX_BYTES`
  (def. 5000000).
- Tests en `tests/test_expedientes_xl_*.py`; suite completa verde antes de cada commit.
- Commits acotados (nunca `add -A`); rama de construcción nueva desde `main` (tras
  mergear el PR docs-only del spec): `claude/mcp-drive-disco-f1`.
- Tier 0 = segmento `90_Notas personales`/`90_NOTAS_PERSONALES` (ni lectura).
  Tier 1 = segmento `00_Input` (carve-out de protocolo) y backups (sin carve-out).
  `H:` entera solo-lectura.

---

### Task 0 (Fase 0, NO bloqueante): Spike conflict-copy de `os.replace` en GDFD

**Files:**
- Create: `scratch no versionado` (script desechable, NO commitear)

Objetivo: fijar la redacción final de §6.1 (¿`os.replace` sobre `G:` genera
conflict-copies en la nube con edición concurrente?). No bloquea ninguna tarea.

- [ ] **Step 1: Script desechable** (ejecutar a mano, fuera del repo):

```python
# spike_replace.py — ejecutar con python spike_replace.py
import os, tempfile, time
from pathlib import Path
d = Path(r"G:\Mi unidad\_spike_replace_DELETEME"); d.mkdir(exist_ok=True)
f = d / "doc.txt"; f.write_text("v1", encoding="utf-8")
print("1) Abre", f, "en drive.google.com y déjalo visible. Enter para seguir.")
input()
fd, tmp = tempfile.mkstemp(dir=d, prefix="doc.", suffix=".tmp")
os.write(fd, b"v2-replace"); os.close(fd)
os.replace(tmp, f)
print("2) replace hecho. Observa en la web: ¿nueva versión limpia o 'copia en conflicto'?")
print("3) Repite editando el doc en la web ANTES del replace. Borra la carpeta a mano al acabar.")
```

- [ ] **Step 2: Registrar el resultado** en el spec (§6.1, sustituir la marca [F0] por
  el comportamiento observado) y en `STATUS.md` de la sesión que lo corra.

---

### Task 1: `tiers.py` — clasificación de zonas

**Files:**
- Create: `plugins/expedientes_xl/tiers.py`
- Test: `tests/test_expedientes_xl_tiers.py`

**Interfaces:**
- Produces: `Tier` (IntEnum: `PROHIBIDA=0, FORENSE=1, WORKSPACE=2`),
  `Zonas` (dataclass frozen: `rw_roots: tuple[Path,...]`, `ro_roots: tuple[Path,...]`,
  `backup_dirs: tuple[str,...]`, `backup_shared: tuple[str,...]`),
  `classify(zonas, path: Path) -> Tier`, `es_backup(zonas, path: Path) -> bool`,
  `TierViolation(Exception)`, constantes `PROTOCOL_EDIT`, `PROTOCOL_APPEND`.

- [ ] **Step 1: Test que falla**

```python
# tests/test_expedientes_xl_tiers.py
from pathlib import Path
import pytest
from plugins.expedientes_xl.tiers import (
    Tier, Zonas, classify, es_backup, PROTOCOL_EDIT, PROTOCOL_APPEND,
)

Z = Zonas(rw_roots=(Path("G:/"),), ro_roots=(Path("H:/"),))

@pytest.mark.parametrize("ruta,tier", [
    (r"G:\CASOS\BaX\90_Notas personales\nota.md", Tier.PROHIBIDA),
    (r"G:\CASOS\BaX\90_NOTAS_PERSONALES\nota.md", Tier.PROHIBIDA),
    (r"G:\CASOS\BaX\00_Input\03_Email\m.eml", Tier.FORENSE),
    (r"G:\CASOS\BaX\00_Input\90_Notas personales\x", Tier.PROHIBIDA),  # Tier 0 gana
    (r"G:\Otros ordenadores\PC\doc.txt", Tier.FORENSE),
    (r"G:\Unidades compartidas\BACKUP\z.zip", Tier.FORENSE),
    (r"H:\Unidades compartidas\BACKUP MADRID\z", Tier.FORENSE),
    (r"G:\CASOS\BaX\01_Procesado\doc.md", Tier.WORKSPACE),
    (r"H:\Mi unidad\doc.pdf", Tier.WORKSPACE),
])
def test_classify(ruta, tier):
    assert classify(Z, Path(ruta)) is tier

def test_es_backup_distingue_de_00input():
    assert es_backup(Z, Path(r"G:\Otros ordenadores\PC\a")) is True
    assert es_backup(Z, Path(r"G:\CASOS\BaX\00_Input\a")) is False

def test_carveout_espeja_merge_exclusions():
    from core.config import MERGE_EXCLUSIONS  # el test SÍ puede importar core
    core_files = {e for e in MERGE_EXCLUSIONS if "/" not in e}
    assert set(PROTOCOL_EDIT) | set(PROTOCOL_APPEND) == core_files
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_expedientes_xl_tiers.py -q`
Expected: FAIL `ModuleNotFoundError: plugins.expedientes_xl.tiers`

- [ ] **Step 3: Implementación mínima**

```python
# plugins/expedientes_xl/tiers.py
"""Zonas (tiers) sobre rutas del montaje GDFD — lógica pura.

Tier 0 (PROHIBIDA): `90_Notas personales` — ni lectura (regla dura de CLAUDE.md).
Tier 1 (FORENSE): `00_Input` (carve-out de protocolo) y backups (sin carve-out).
Tier 2 (WORKSPACE): el resto. Los carve-outs espejan core.config.MERGE_EXCLUSIONS
(sincronía garantizada por test; el plugin no importa core en runtime).
Spec: docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-design.md §2.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path


class Tier(IntEnum):
    PROHIBIDA = 0
    FORENSE = 1
    WORKSPACE = 2


class TierViolation(Exception):
    """Operación rechazada por la política de zonas."""


_NOTAS = {"90_notas personales", "90_notas_personales"}
_INPUT = "00_input"

# Carve-out de protocolo bajo 00_Input (espeja core.config.MERGE_EXCLUSIONS)
PROTOCOL_EDIT: tuple[str, ...] = ("_caso.md", "MANIFEST_CHECKOUT.json")
PROTOCOL_APPEND: tuple[str, ...] = ("_intake_log.jsonl", "AUDITLOG_MERGE_*.jsonl")


@dataclass(frozen=True)
class Zonas:
    rw_roots: tuple[Path, ...]
    ro_roots: tuple[Path, ...] = ()
    backup_dirs: tuple[str, ...] = ("Otros ordenadores",)
    backup_shared: tuple[str, ...] = ("BACKUP", "BACKUP MADRID", "TWBCN-Backup2")


def es_backup(zonas: Zonas, path: Path) -> bool:
    parts = list(path.parts)
    lower = [p.lower() for p in parts]
    if any(b.lower() in lower for b in zonas.backup_dirs):
        return True
    for i, p in enumerate(lower):
        if p == "unidades compartidas" and i + 1 < len(parts):
            if parts[i + 1].upper() in {b.upper() for b in zonas.backup_shared}:
                return True
    return False


def classify(zonas: Zonas, path: Path) -> Tier:
    segs = [p.lower() for p in path.parts]
    if any(s in _NOTAS for s in segs):
        return Tier.PROHIBIDA
    if _INPUT in segs or es_backup(zonas, path):
        return Tier.FORENSE
    return Tier.WORKSPACE
```

- [ ] **Step 4: Verificar que pasa**

Run: `python -m pytest tests/test_expedientes_xl_tiers.py -q`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/tiers.py tests/test_expedientes_xl_tiers.py
git commit -m "feat(xl): tiers.py - clasificacion de zonas 0/1/2 con test de sincronia MERGE_EXCLUSIONS"
```

---

### Task 2: `tiers.py` — `check_read` / `check_write` con carve-out

**Files:**
- Modify: `plugins/expedientes_xl/tiers.py`
- Test: `tests/test_expedientes_xl_tiers.py` (añadir)

**Interfaces:**
- Consumes: `classify`, `es_backup`, `PROTOCOL_*` (Task 1).
- Produces: `check_read(zonas, path) -> None` (lanza `TierViolation` si Tier 0),
  `check_write(zonas, path, *, exists: bool, append: bool = False) -> None`
  (lanza `TierViolation` con motivo legible). Reglas exactas:
  1. `path` bajo un `ro_root` → rechazo («H: es solo-lectura en V1»).
  2. Tier 0 → rechazo.
  3. backup → rechazo (sin carve-out).
  4. Tier 1 (`00_Input`): `exists=False` → permitido (crear-nuevo);
     `exists=True` → permitido solo si nombre ∈ `PROTOCOL_EDIT`
     o (`append=True` y nombre casa con `PROTOCOL_APPEND`, usar `fnmatch`);
     resto → rechazo.
  5. Tier 2 → permitido.

- [ ] **Step 1: Test que falla**

```python
# añadir a tests/test_expedientes_xl_tiers.py
from plugins.expedientes_xl.tiers import TierViolation, check_read, check_write

def test_check_read_bloquea_tier0():
    with pytest.raises(TierViolation):
        check_read(Z, Path(r"G:\CASOS\BaX\90_Notas personales\n.md"))
    check_read(Z, Path(r"G:\CASOS\BaX\00_Input\d.pdf"))  # Tier 1 se lee

def test_check_write_ro_root():
    with pytest.raises(TierViolation, match="solo-lectura"):
        check_write(Z, Path(r"H:\Mi unidad\x.txt"), exists=False)

def test_check_write_00input_crear_nuevo_ok():
    check_write(Z, Path(r"G:\CASOS\BaX\00_Input\04_Manual\nuevo.pdf"), exists=False)

def test_check_write_00input_sobrescribir_rechazado():
    with pytest.raises(TierViolation):
        check_write(Z, Path(r"G:\CASOS\BaX\00_Input\04_Manual\viejo.pdf"), exists=True)

def test_check_write_carveout_protocolo():
    check_write(Z, Path(r"G:\CASOS\BaX\00_Input\_caso.md"), exists=True)          # edit
    check_write(Z, Path(r"G:\CASOS\BaX\00_Input\_intake_log.jsonl"), exists=True, append=True)
    check_write(Z, Path(r"G:\CASOS\BaX\00_Input\AUDITLOG_MERGE_x.jsonl"), exists=True, append=True)
    with pytest.raises(TierViolation):  # el log NO es editable, solo append
        check_write(Z, Path(r"G:\CASOS\BaX\00_Input\_intake_log.jsonl"), exists=True)

def test_check_write_backup_sin_carveout():
    with pytest.raises(TierViolation):
        check_write(Z, Path(r"G:\Otros ordenadores\PC\_caso.md"), exists=True)
    with pytest.raises(TierViolation):  # ni crear-nuevo en backup
        check_write(Z, Path(r"G:\Unidades compartidas\BACKUP\n.txt"), exists=False)
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_expedientes_xl_tiers.py -q` → FAIL (ImportError `check_read`)

- [ ] **Step 3: Implementación**

```python
# añadir a plugins/expedientes_xl/tiers.py
from fnmatch import fnmatch


def check_read(zonas: Zonas, path: Path) -> None:
    if classify(zonas, path) is Tier.PROHIBIDA:
        raise TierViolation(f"Zona prohibida (90_Notas personales): {path}")


def check_write(zonas: Zonas, path: Path, *, exists: bool, append: bool = False) -> None:
    for ro in zonas.ro_roots:
        try:
            path.resolve().relative_to(Path(ro).resolve())
            raise TierViolation(f"Unidad solo-lectura en V1: {path}")
        except ValueError:
            continue
    tier = classify(zonas, path)
    if tier is Tier.PROHIBIDA:
        raise TierViolation(f"Zona prohibida (90_Notas personales): {path}")
    if tier is Tier.WORKSPACE:
        return
    # Tier 1
    if es_backup(zonas, path):
        raise TierViolation(f"Backup: solo-lectura, sin excepciones: {path}")
    if not exists:
        return  # crear-nuevo bajo 00_Input: permitido (intake)
    nombre = path.name
    if nombre in PROTOCOL_EDIT:
        return
    if append and any(fnmatch(nombre, pat) for pat in PROTOCOL_APPEND):
        return
    raise TierViolation(
        f"00_Input es forense-inmutable: no se sobrescribe lo depositado: {path}"
    )
```

- [ ] **Step 4: Verificar que pasa** → `python -m pytest tests/test_expedientes_xl_tiers.py -q` PASS

- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/tiers.py tests/test_expedientes_xl_tiers.py
git commit -m "feat(xl): check_read/check_write con carve-out de protocolo y H: solo-lectura"
```

---

### Task 3: `winio.py` — escritura atómica, backoff y rutas largas

**Files:**
- Create: `plugins/expedientes_xl/winio.py`
- Test: `tests/test_expedientes_xl_winio.py`

**Interfaces:**
- Produces: `atomic_write_bytes(dst: Path, data: bytes) -> int`,
  `atomic_write_text(dst: Path, text: str) -> int`,
  `retry_sharing(fn: Callable[[], T]) -> T` (3 intentos 0,5/1/2 s ante winerror 32;
  al agotar relanza), `long_path(p: Path) -> str` (prefijo `\\?\` en rutas absolutas
  de unidad), `SharingViolation(Exception)`.

- [ ] **Step 1: Test que falla**

```python
# tests/test_expedientes_xl_winio.py
from pathlib import Path
import pytest
from plugins.expedientes_xl.winio import (
    atomic_write_bytes, atomic_write_text, long_path, retry_sharing,
)

def test_atomic_write_crea_y_reemplaza(tmp_path):
    f = tmp_path / "doc.txt"
    assert atomic_write_text(f, "v1") == 2
    assert atomic_write_text(f, "v2-nuevo") == len("v2-nuevo")
    assert f.read_text(encoding="utf-8") == "v2-nuevo"
    # sin temporales huérfanos
    assert [p.name for p in tmp_path.iterdir()] == ["doc.txt"]

def test_atomic_write_no_deja_parcial_si_falla(tmp_path, monkeypatch):
    f = tmp_path / "doc.txt"
    atomic_write_text(f, "estable")
    import plugins.expedientes_xl.winio as w
    monkeypatch.setattr(w.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(OSError):
        atomic_write_text(f, "nuevo")
    assert f.read_text(encoding="utf-8") == "estable"          # destino intacto
    assert [p.name for p in tmp_path.iterdir()] == ["doc.txt"]  # tmp limpiado

def test_long_path_prefija():
    assert long_path(Path(r"G:\Mi unidad\a.txt")).startswith("\\\\?\\")
    ya = "\\\\?\\G:\\a"
    assert long_path(Path(ya)) == ya

def test_retry_sharing_reintenta(monkeypatch):
    import plugins.expedientes_xl.winio as w
    monkeypatch.setattr(w.time, "sleep", lambda s: None)
    intentos = {"n": 0}
    def fn():
        intentos["n"] += 1
        if intentos["n"] < 3:
            e = PermissionError("locked"); e.winerror = 32; raise e
        return "ok"
    assert retry_sharing(fn) == "ok"
    assert intentos["n"] == 3
```

- [ ] **Step 2: Verificar que falla** → FAIL ModuleNotFoundError

- [ ] **Step 3: Implementación**

```python
# plugins/expedientes_xl/winio.py
"""E/S robusta en Windows/GDFD: escritura atómica (tmp+nonce MISMO directorio +
os.replace — nunca %TEMP%: cross-device rename falla con EXDEV), reintentos ante
ERROR_SHARING_VIOLATION (~$ de Office) y prefijo \\?\ para MAX_PATH."""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")

_BACKOFF = (0.5, 1.0, 2.0)


class SharingViolation(Exception):
    """Fichero bloqueado por otro proceso (probablemente editado por un humano)."""


def long_path(p: Path) -> str:
    s = str(p)
    if s.startswith("\\\\?\\"):
        return s
    return "\\\\?\\" + s


def retry_sharing(fn: Callable[[], T]) -> T:
    ultimo: PermissionError | None = None
    for espera in _BACKOFF:
        try:
            return fn()
        except PermissionError as e:
            if getattr(e, "winerror", None) != 32:
                raise
            ultimo = e
            time.sleep(espera)
    raise SharingViolation(
        "Bloqueado tras 3 reintentos: probablemente lo está editando un humano"
    ) from ultimo


def atomic_write_bytes(dst: Path, data: bytes) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=dst.name + ".", suffix=".tmp", dir=str(dst.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        retry_sharing(lambda: os.replace(tmp, dst))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return len(data)


def atomic_write_text(dst: Path, text: str) -> int:
    return atomic_write_bytes(dst, text.encode("utf-8"))
```

- [ ] **Step 4: Verificar que pasa** → PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/winio.py tests/test_expedientes_xl_winio.py
git commit -m "feat(xl): winio - atomic write (tmp+nonce mismo dir), backoff sharing-violation, \\?\\ long path"
```

---

### Task 4: `audit.py` — auditoría JSONL fuera del volumen

**Files:**
- Create: `plugins/expedientes_xl/audit.py`
- Test: `tests/test_expedientes_xl_audit.py`

**Interfaces:**
- Produces: `log_op(op: str, ruta: str, resultado: str, motivo: str = "", **extra) -> None`
  (best-effort: NUNCA lanza; ruta del log = env `XL_AUDIT_PATH` o
  `%LOCALAPPDATA%\FeesDefender\xl_audit.jsonl`; una línea JSON por evento con
  `ts` ISO-8601 UTC, `op`, `ruta`, `resultado`, `motivo`, extras).

- [ ] **Step 1: Test que falla**

```python
# tests/test_expedientes_xl_audit.py
import json
from plugins.expedientes_xl import audit

def test_log_op_escribe_jsonl(tmp_path, monkeypatch):
    log = tmp_path / "sub" / "audit.jsonl"
    monkeypatch.setenv("XL_AUDIT_PATH", str(log))
    audit.log_op("write_text", r"G:\x.txt", "ok", hash_post="abc")
    audit.log_op("copy_dir", r"G:\y", "tier_violation", motivo="backup")
    lineas = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas) == 2
    ev = json.loads(lineas[0])
    assert ev["op"] == "write_text" and ev["hash_post"] == "abc" and "ts" in ev

def test_log_op_nunca_lanza(monkeypatch):
    monkeypatch.setenv("XL_AUDIT_PATH", r"Z:\no\existe\audit.jsonl")
    audit.log_op("x", "y", "z")  # no debe lanzar
```

- [ ] **Step 2: Verificar que falla** → FAIL
- [ ] **Step 3: Implementación**

```python
# plugins/expedientes_xl/audit.py
"""Auditoría de operaciones mutantes: JSONL append-only FUERA del volumen Drive
(patrón _intake_log.jsonl). Best-effort: no rompe la operación si el log falla."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _ruta_log() -> Path:
    env = os.environ.get("XL_AUDIT_PATH")
    if env:
        return Path(env)
    base = os.environ.get("LOCALAPPDATA", str(Path.home()))
    return Path(base) / "FeesDefender" / "xl_audit.jsonl"


def log_op(op: str, ruta: str, resultado: str, motivo: str = "", **extra) -> None:
    ev = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
          "op": op, "ruta": ruta, "resultado": resultado, "motivo": motivo, **extra}
    try:
        dst = _ruta_log()
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except OSError as e:  # pragma: no cover - best effort
        print(f"[xl-audit] no se pudo escribir el log: {e}", file=sys.stderr)
```

- [ ] **Step 4: Verificar que pasa** → PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/audit.py tests/test_expedientes_xl_audit.py
git commit -m "feat(xl): audit - JSONL append-only fuera del volumen, best-effort"
```

---

### Task 5: `oracle.py` — snapshot con TTL vía SQLite backup API

**Files:**
- Create: `plugins/expedientes_xl/oracle.py`
- Test: `tests/test_expedientes_xl_oracle.py`

**Interfaces:**
- Produces: `class Oracle` con
  `__init__(self, dbs: dict[str, Path], cache_dirs: dict[str, Path], ttl: float = 5.0)`
  — `dbs` mapea prefijo de raíz (str, p. ej. `"G:\\"`) → ruta de `metadata_sqlite_db`;
  `cache_dirs` idem → carpeta `content_cache`;
  `_snapshot(self, root: str) -> sqlite3.Connection | None` (copia con TTL;
  `None` = oráculo caído → los callers tratan como UNKNOWN);
  `refresh_count` (int, para tests del TTL).
- Detalle crítico (spec §4.1): el snapshot usa `src.backup(dst)` desde una conexión
  `mode=ro` — nunca copia de ficheros ni `immutable=1`. **Caché TTL obligatoria**:
  un `backup()` por ráfaga, no por operación.

- [ ] **Step 1: Test que falla** (fixture: mini-BD con el esquema real verificado)

```python
# tests/test_expedientes_xl_oracle.py
import sqlite3
from pathlib import Path
import pytest
from plugins.expedientes_xl.oracle import Oracle

SCHEMA = """
CREATE TABLE items (stable_id INTEGER PRIMARY KEY, id TEXT, trashed INT DEFAULT 0,
  is_folder INT DEFAULT 0, is_tombstone INT DEFAULT 0, file_size INT DEFAULT 0,
  local_title TEXT, team_drive_stable_id INT);
CREATE TABLE item_properties (item_stable_id INT, key TEXT, value);
CREATE TABLE stable_parents (item_stable_id INT, parent_stable_id INT, local_title_hash TEXT);
CREATE TABLE shortcut_details (shortcut_stable_id INT, target_stable_id INT, target_mime_type TEXT);
"""

@pytest.fixture
def mini_db(tmp_path):
    db = tmp_path / "metadata_sqlite_db"
    con = sqlite3.connect(db)
    con.executescript(SCHEMA)
    # Árbol: TD (10) / Caso (20) / 00_Input (30) / hot.pdf (40), cold.pdf (50)
    filas = [(10, "td1", 1, "EXPEDIENTES - TYUKHAY LEGAL", None),
             (20, "c1", 1, "Caso X", 10), (30, "i1", 1, "00_Input", 10),
             (40, "h1", 0, "hot.pdf", 10), (50, "c2", 0, "cold.pdf", 10)]
    for sid, cid, isf, title, td in filas:
        con.execute("INSERT INTO items(stable_id,id,is_folder,local_title,team_drive_stable_id) VALUES (?,?,?,?,?)",
                    (sid, cid, isf, title, td))
    for hijo, padre in [(20, 10), (30, 20), (40, 30), (50, 30)]:
        con.execute("INSERT INTO stable_parents VALUES (?,?,'')", (hijo, padre))
    con.execute("INSERT INTO item_properties VALUES (40,'content-entry',X'0801')")
    con.commit(); con.close()
    cache = tmp_path / "content_cache"; cache.mkdir()
    return db, cache

def test_snapshot_ttl_no_repite_backup(mini_db, monkeypatch):
    db, cache = mini_db
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)
    con1 = o._snapshot("G:\\")
    con2 = o._snapshot("G:\\")
    assert con1 is con2 and o.refresh_count == 1
    assert con1.execute("SELECT count(*) FROM items").fetchone()[0] == 5

def test_snapshot_caido_devuelve_none(tmp_path):
    o = Oracle({"G:\\": tmp_path / "no_existe"}, {"G:\\": tmp_path}, ttl=5)
    assert o._snapshot("G:\\") is None
```

- [ ] **Step 2: Verificar que falla** → FAIL
- [ ] **Step 3: Implementación**

```python
# plugins/expedientes_xl/oracle.py
"""Oráculo de hidratación HOT/COLD sobre la BD interna de GDFD.

OPCIONAL y fail-closed: si la BD no está o el esquema cambió, todo es UNKNOWN
(los guards lo tratan como COLD). Snapshot vía SQLite online backup API con
caché TTL (~5 s): un backup() por ráfaga, no por operación (anti-thrashing).
Spec §4.1. La BD es privada de Google: NUNCA depender de ella para corrección.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
from pathlib import Path


class Oracle:
    def __init__(self, dbs: dict[str, Path], cache_dirs: dict[str, Path],
                 ttl: float | None = None) -> None:
        self._dbs = {k: Path(v) for k, v in dbs.items()}
        self._cache_dirs = {k: Path(v) for k, v in cache_dirs.items()}
        self._ttl = ttl if ttl is not None else float(os.environ.get("XL_ORACLE_TTL", "5"))
        self._snap: dict[str, tuple[float, sqlite3.Connection | None]] = {}
        self._cache_names: dict[str, tuple[float, frozenset[str]]] = {}
        self.refresh_count = 0

    def _snapshot(self, root: str) -> sqlite3.Connection | None:
        ahora = time.monotonic()
        cacheado = self._snap.get(root)
        if cacheado and ahora - cacheado[0] < self._ttl:
            return cacheado[1]
        con: sqlite3.Connection | None = None
        try:
            src = sqlite3.connect(f"file:{self._dbs[root]}?mode=ro", uri=True, timeout=8)
            fd, tmp = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            dst = sqlite3.connect(tmp)
            src.backup(dst)
            src.close()
            con = dst
            self.refresh_count += 1
        except (sqlite3.Error, OSError, KeyError):
            con = None  # oráculo caído -> UNKNOWN (fail-closed en guards)
        if cacheado and cacheado[1] is not None and cacheado[1] is not con:
            try:
                cacheado[1].close()
            except sqlite3.Error:
                pass
        self._snap[root] = (ahora, con)
        return con
```

- [ ] **Step 4: Verificar que pasa** → PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/oracle.py tests/test_expedientes_xl_oracle.py
git commit -m "feat(xl): oracle - snapshot de metadata_sqlite_db via backup API con cache TTL"
```

---

### Task 6: `oracle.py` — `status(path)` por ascendencia + cruce con caché

**Files:**
- Modify: `plugins/expedientes_xl/oracle.py`
- Test: `tests/test_expedientes_xl_oracle.py` (añadir)

**Interfaces:**
- Consumes: `_snapshot` (Task 5).
- Produces: `status(self, path: Path) -> str` — `"HOT" | "COLD" | "UNKNOWN"`.
  Algoritmo: (1) elegir BD por prefijo de raíz; (2) candidatos =
  `items WHERE local_title = <leaf>`; (3) subir por `stable_parents` casando cada
  `local_title` con los segmentos del path (ignorando los niveles virtuales
  `Unidades compartidas` / `Mi unidad` / la letra); exactamente 1 candidato casa →
  resuelto, 0 o >1 → `UNKNOWN` (fail-closed); (4) resuelto sin `content-entry` →
  `COLD`; con `content-entry`: si `XL_ORACLE_STRICT=1`, cruzar los varints del blob
  con el set de nombres de `content_cache` (sin match → `COLD`); por defecto
  (lenient) → `HOT`.

- [ ] **Step 1: Test que falla**

```python
# añadir a tests/test_expedientes_xl_oracle.py
def test_status_hot_cold_unknown(mini_db):
    db, cache = mini_db
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)
    base = r"G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\Caso X\00_Input"
    assert o.status(Path(base + r"\hot.pdf")) == "HOT"
    assert o.status(Path(base + r"\cold.pdf")) == "COLD"
    assert o.status(Path(base + r"\no_existe.pdf")) == "UNKNOWN"
    assert o.status(Path(r"Z:\fuera\x.pdf")) == "UNKNOWN"   # raíz sin BD

def test_status_oraculo_caido_unknown(tmp_path):
    o = Oracle({"G:\\": tmp_path / "no"}, {"G:\\": tmp_path}, ttl=5)
    assert o.status(Path(r"G:\Mi unidad\a.pdf")) == "UNKNOWN"

def test_status_ambiguo_unknown(mini_db):
    db, cache = mini_db
    con = __import__("sqlite3").connect(db)
    # duplicar el leaf con OTRA ascendencia que también casa parcialmente
    con.execute("INSERT INTO items(stable_id,id,is_folder,local_title) VALUES (60,'d',0,'hot.pdf')")
    con.execute("INSERT INTO stable_parents VALUES (60,30,'')")
    con.commit(); con.close()
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)
    base = r"G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\Caso X\00_Input"
    assert o.status(Path(base + r"\hot.pdf")) == "UNKNOWN"  # 2 candidatos -> fail-closed
```

- [ ] **Step 2: Verificar que falla** → FAIL (AttributeError `status`)
- [ ] **Step 3: Implementación**

```python
# añadir a plugins/expedientes_xl/oracle.py
_VIRTUALES = {"unidades compartidas", "mi unidad", "otros ordenadores"}


def _varints(blob: bytes) -> set[int]:
    out: set[int] = set()
    val = shift = 0
    for b in blob:
        val |= (b & 0x7F) << shift
        if b & 0x80:
            shift += 7
        else:
            if val > 1000:
                out.add(val)
            val = shift = 0
    return out


class Oracle(Oracle):  # nota para el ejecutor: fusionar en la clase, no subclasear
    pass
```

(Métodos a añadir DENTRO de la clase `Oracle`:)

```python
    def _root_de(self, path: Path) -> str | None:
        s = str(path)
        for root in self._dbs:
            if s.upper().startswith(root.upper()):
                return root
        return None

    def _resolver(self, con: sqlite3.Connection, path: Path) -> int | None:
        """stable_id del path por ascendencia de títulos; None = no resoluble."""
        segs = [p for p in path.parts[1:] if p.lower() not in _VIRTUALES]
        if not segs:
            return None
        leaf = segs[-1]
        ancestros = [s.lower() for s in segs[:-1]]
        candidatos = [r[0] for r in con.execute(
            "SELECT stable_id FROM items WHERE local_title = ? AND is_tombstone = 0 AND trashed = 0",
            (leaf,))]
        resueltos = []
        for sid in candidatos:
            cadena: list[str] = []
            actual = sid
            for _ in range(64):  # tope de profundidad
                fila = con.execute(
                    "SELECT p.parent_stable_id, i.local_title FROM stable_parents p "
                    "JOIN items i ON i.stable_id = p.parent_stable_id "
                    "WHERE p.item_stable_id = ?", (actual,)).fetchone()
                if fila is None:
                    break
                actual = fila[0]
                cadena.append((fila[1] or "").lower())
            # la cadena (leaf->raíz) debe contener los ancestros del path como sufijo
            if cadena[: len(ancestros)] == list(reversed(ancestros)):
                resueltos.append(sid)
        return resueltos[0] if len(resueltos) == 1 else None

    def _nombres_cache(self, root: str) -> frozenset[str]:
        ahora = time.monotonic()
        c = self._cache_names.get(root)
        if c and ahora - c[0] < self._ttl:
            return c[1]
        nombres: set[str] = set()
        base = self._cache_dirs.get(root)
        if base and base.is_dir():
            for r, _dirs, files in os.walk(base):
                nombres.update(files)
        fz = frozenset(nombres)
        self._cache_names[root] = (ahora, fz)
        return fz

    def status(self, path: Path) -> str:
        root = self._root_de(path)
        if root is None:
            return "UNKNOWN"
        con = self._snapshot(root)
        if con is None:
            return "UNKNOWN"
        try:
            sid = self._resolver(con, path)
            if sid is None:
                return "UNKNOWN"
            fila = con.execute(
                "SELECT value FROM item_properties WHERE item_stable_id = ? AND key = 'content-entry'",
                (sid,)).fetchone()
            if fila is None:
                return "COLD"
            if os.environ.get("XL_ORACLE_STRICT") == "1":
                ids = _varints(bytes(fila[0]))
                nombres = self._nombres_cache(root)
                if not any(str(i) in nombres for i in ids):
                    return "COLD"
            return "HOT"
        except sqlite3.Error:
            return "UNKNOWN"
```

- [ ] **Step 4: Verificar que pasa** → PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/oracle.py tests/test_expedientes_xl_oracle.py
git commit -m "feat(xl): oracle.status - resolucion por ascendencia fail-closed + cruce opcional con content_cache"
```

---

### Task 7: `oracle.py` — `subtree_cold_stats` y descubrimiento de cuentas

**Files:**
- Modify: `plugins/expedientes_xl/oracle.py`
- Test: `tests/test_expedientes_xl_oracle.py` (añadir)

**Interfaces:**
- Produces: `subtree_cold_stats(self, path: Path) -> tuple[int, int] | None`
  (`(n_cold, n_total)` de FICHEROS bajo la carpeta; `None` = no resoluble/caído) y
  función de módulo `descubrir_cuentas(drivefs_dir: Path, roots: dict[str, Path]) ->
  tuple[dict[str, Path], dict[str, Path]]` que devuelve `(dbs, cache_dirs)` casando
  ≥2 nombres de las unidades compartidas de cada letra (`os.listdir` de
  `<letra>\Unidades compartidas`) contra `items.local_title` de cada
  `metadata_sqlite_db` bajo `drivefs_dir` (subdirectorios numéricos). Cuenta sin
  match → se omite (el oráculo de esa letra queda caído → UNKNOWN).

- [ ] **Step 1: Test que falla**

```python
# añadir a tests/test_expedientes_xl_oracle.py
from plugins.expedientes_xl.oracle import descubrir_cuentas

def test_subtree_cold_stats(mini_db):
    db, cache = mini_db
    o = Oracle({"G:\\": db}, {"G:\\": cache}, ttl=999)
    base = r"G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\Caso X\00_Input"
    assert o.subtree_cold_stats(Path(base)) == (1, 2)   # cold.pdf de 2 ficheros
    assert o.subtree_cold_stats(Path(r"G:\no\existe")) is None

def test_descubrir_cuentas(mini_db, tmp_path, monkeypatch):
    db, cache = mini_db
    acct = tmp_path / "DriveFS" / "12345"
    acct.mkdir(parents=True)
    (acct / "content_cache").mkdir()
    import shutil
    shutil.copy2(db, acct / "metadata_sqlite_db")
    g = tmp_path / "G"; (g / "Unidades compartidas" / "EXPEDIENTES - TYUKHAY LEGAL").mkdir(parents=True)
    (g / "Unidades compartidas" / "Caso X").mkdir()   # 2º marcador
    dbs, caches = descubrir_cuentas(tmp_path / "DriveFS", {"G:\\": g})
    assert dbs == {"G:\\": acct / "metadata_sqlite_db"}
    assert caches == {"G:\\": acct / "content_cache"}
```

- [ ] **Step 2: Verificar que falla** → FAIL
- [ ] **Step 3: Implementación** (añadir a `oracle.py`)

```python
    def subtree_cold_stats(self, path: Path) -> tuple[int, int] | None:
        root = self._root_de(path)
        if root is None:
            return None
        con = self._snapshot(root)
        if con is None:
            return None
        try:
            sid = self._resolver(con, path)
            if sid is None:
                return None
            pendientes, ficheros = [sid], []
            while pendientes:
                actual = pendientes.pop()
                for hijo, es_dir in con.execute(
                    "SELECT p.item_stable_id, i.is_folder FROM stable_parents p "
                    "JOIN items i ON i.stable_id = p.item_stable_id "
                    "WHERE p.parent_stable_id = ? AND i.is_tombstone = 0 AND i.trashed = 0",
                        (actual,)):
                    (pendientes if es_dir else ficheros).append(hijo)
            if not ficheros:
                return (0, 0)
            marca = ",".join("?" * len(ficheros))
            hot = con.execute(
                f"SELECT count(DISTINCT item_stable_id) FROM item_properties "
                f"WHERE key='content-entry' AND item_stable_id IN ({marca})",
                ficheros).fetchone()[0]
            return (len(ficheros) - hot, len(ficheros))
        except sqlite3.Error:
            return None


def descubrir_cuentas(drivefs_dir: Path, roots: dict[str, Path]
                      ) -> tuple[dict[str, Path], dict[str, Path]]:
    """Mapea letra->BD casando nombres de unidades compartidas contra local_title."""
    dbs: dict[str, Path] = {}
    caches: dict[str, Path] = {}
    cuentas = [d for d in drivefs_dir.iterdir()
               if d.is_dir() and d.name.isdigit() and (d / "metadata_sqlite_db").exists()]
    for root, base in roots.items():
        uc = Path(base) / "Unidades compartidas"
        marcadores = [p.name for p in uc.iterdir() if p.is_dir()][:10] if uc.is_dir() else []
        if len(marcadores) < 2:
            continue
        for cuenta in cuentas:
            try:
                con = sqlite3.connect(f"file:{cuenta / 'metadata_sqlite_db'}?mode=ro",
                                      uri=True, timeout=8)
                hits = sum(
                    1 for m in marcadores
                    if con.execute("SELECT 1 FROM items WHERE local_title=? LIMIT 1",
                                   (m,)).fetchone())
                con.close()
            except sqlite3.Error:
                continue
            if hits >= 2:
                dbs[root] = cuenta / "metadata_sqlite_db"
                caches[root] = cuenta / "content_cache"
                break
    return dbs, caches
```

- [ ] **Step 4: Verificar que pasa** → PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/oracle.py tests/test_expedientes_xl_oracle.py
git commit -m "feat(xl): oracle - subtree_cold_stats + descubrimiento cuenta<->letra por marcadores"
```

---

### Task 8: `guards.py` — guarda de hidratación fail-closed + bloqueo `.g*`

**Files:**
- Create: `plugins/expedientes_xl/guards.py`
- Test: `tests/test_expedientes_xl_guards.py`

**Interfaces:**
- Consumes: `Oracle.status`, `Oracle.subtree_cold_stats` (Tasks 6-7).
- Produces: `FileNotHydrated(Exception)` con atributo `.omitidos: list[str]`;
  `GDocBloqueado(Exception)`; `check_gdoc(path) -> None`;
  `guard_file(oracle, path) -> None` (aborta si tamaño lógico > `XL_HYDRATION_MAX_FILE_MB`
  y status ∈ {COLD, UNKNOWN}); `guard_tree(oracle, root) -> None` (aborta si
  `subtree_cold_stats` supera `XL_TREE_MAX_COLD` **o** el tamaño lógico del árbol
  supera `XL_TREE_MAX_MB`; stats `None` (oráculo caído) + árbol > umbral → aborta
  fail-closed). El mensaje SIEMPRE lista lo omitido (sin silencios).

- [ ] **Step 1: Test que falla**

```python
# tests/test_expedientes_xl_guards.py
from pathlib import Path
import pytest
from plugins.expedientes_xl.guards import (
    FileNotHydrated, GDocBloqueado, check_gdoc, guard_file, guard_tree,
)

class FakeOracle:
    def __init__(self, status="HOT", stats=(0, 10)):
        self._status, self._stats = status, stats
    def status(self, path): return self._status
    def subtree_cold_stats(self, path): return self._stats

def test_check_gdoc_bloquea():
    for ext in (".gdoc", ".gsheet", ".gslides"):
        with pytest.raises(GDocBloqueado, match="google-despacho"):
            check_gdoc(Path(f"G:/x{ext}"))
    check_gdoc(Path("G:/x.pdf"))  # no lanza

def test_guard_file_cold_grande_aborta(tmp_path, monkeypatch):
    monkeypatch.setenv("XL_HYDRATION_MAX_FILE_MB", "0")  # todo es "grande"
    f = tmp_path / "grande.bin"; f.write_bytes(b"x" * 10)
    with pytest.raises(FileNotHydrated) as ei:
        guard_file(FakeOracle("COLD"), f)
    assert str(f) in ei.value.omitidos
    with pytest.raises(FileNotHydrated):
        guard_file(FakeOracle("UNKNOWN"), f)   # fail-closed
    guard_file(FakeOracle("HOT"), f)            # HOT pasa

def test_guard_file_cold_pequeno_pasa(tmp_path, monkeypatch):
    monkeypatch.setenv("XL_HYDRATION_MAX_FILE_MB", "10")
    f = tmp_path / "peq.bin"; f.write_bytes(b"x")
    guard_file(FakeOracle("COLD"), f)  # pequeño: se permite (descarga corta)

def test_guard_tree_por_conteo(tmp_path, monkeypatch):
    monkeypatch.setenv("XL_TREE_MAX_COLD", "5")
    with pytest.raises(FileNotHydrated, match="51"):
        guard_tree(FakeOracle(stats=(51, 100)), tmp_path)
    guard_tree(FakeOracle(stats=(2, 100)), tmp_path)

def test_guard_tree_oraculo_caido_failclosed(tmp_path, monkeypatch):
    monkeypatch.setenv("XL_TREE_MAX_MB", "0")   # árbol siempre "grande"
    (tmp_path / "a.bin").write_bytes(b"x" * 10)
    with pytest.raises(FileNotHydrated):
        guard_tree(FakeOracle(stats=None), tmp_path)
```

- [ ] **Step 2: Verificar que falla** → FAIL
- [ ] **Step 3: Implementación**

```python
# plugins/expedientes_xl/guards.py
"""Guardas Stream-aware (spec §6.2, §6.4): fail-closed ante COLD/UNKNOWN grande,
bloqueo de extensiones nativas de Google (lectura FS = ERROR_INVALID_FUNCTION)."""
from __future__ import annotations

import os
from pathlib import Path

_GDOC_EXTS = {".gdoc", ".gsheet", ".gslides", ".gdraw", ".gform", ".gtable", ".gmap"}


class GDocBloqueado(Exception):
    """Documento nativo de Google: ilegible por FS; exportar vía google-despacho."""


class FileNotHydrated(Exception):
    def __init__(self, mensaje: str, omitidos: list[str]):
        super().__init__(mensaje)
        self.omitidos = omitidos


def _mb(nombre: str, defecto: str) -> float:
    return float(os.environ.get(nombre, defecto))


def check_gdoc(path: Path) -> None:
    if path.suffix.lower() in _GDOC_EXTS:
        raise GDocBloqueado(
            f"{path.name}: documento nativo de Google — el montaje no puede leerlo; "
            "usa google-despacho (export_to_drive / read_file_content)")


def guard_file(oracle, path: Path) -> None:
    umbral = _mb("XL_HYDRATION_MAX_FILE_MB", "10") * 1024 * 1024
    try:
        tam = path.stat().st_size
    except OSError:
        return  # inexistente: lo dirá la operación
    if tam <= umbral:
        return
    estado = oracle.status(path)
    if estado != "HOT":
        raise FileNotHydrated(
            f"ERROR_FILE_NOT_HYDRATED: {path} ({tam} B, estado={estado}). "
            "Fija la carpeta 'Disponible sin conexión' en Drive o autoriza la descarga.",
            omitidos=[str(path)])


def guard_tree(oracle, root: Path) -> None:
    max_cold = int(_mb("XL_TREE_MAX_COLD", "50"))
    max_bytes = _mb("XL_TREE_MAX_MB", "150") * 1024 * 1024
    stats = oracle.subtree_cold_stats(root)
    if stats is not None:
        n_cold, n_total = stats
        if n_cold > max_cold:
            raise FileNotHydrated(
                f"ERROR_TREE_NOT_HYDRATED: {root}: {n_cold} ficheros COLD de {n_total} "
                f"(umbral {max_cold}). Hidrata el árbol antes (pin offline).",
                omitidos=[str(root)])
        return
    # oráculo caído: fail-closed si el árbol es grande (tamaño LÓGICO, stat no hidrata)
    total = 0
    for r, _d, files in os.walk(root):
        for f in files:
            try:
                total += os.stat(os.path.join(r, f)).st_size
            except OSError:
                continue
        if total > max_bytes:
            raise FileNotHydrated(
                f"ERROR_TREE_UNKNOWN: {root}: oráculo no disponible y árbol > "
                f"{max_bytes/1e6:.0f} MB — abortado fail-closed.",
                omitidos=[str(root)])
```

- [ ] **Step 4: Verificar que pasa** → PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/guards.py tests/test_expedientes_xl_guards.py
git commit -m "feat(xl): guards - hidratacion fail-closed (fichero+arbol) y bloqueo .g*"
```

---

### Task 9: `readops.py` — lectura y metadatos

**Files:**
- Create: `plugins/expedientes_xl/readops.py`
- Test: `tests/test_expedientes_xl_readops.py`

**Interfaces:**
- Consumes: `resolve_within` (fsops), `check_read`/`classify` (tiers),
  `check_gdoc`/`guard_file` (guards), `long_path` (winio).
- Produces:
  `read_text(allowed, zonas, oracle, path, head: int | None = None, tail: int | None = None) -> str`
  (UTF-8 `errors="replace"`; cap `XL_READ_MAX_BYTES`; `head`/`tail` en líneas);
  `read_multiple(allowed, zonas, oracle, paths: list[str]) -> dict[str, str]`
  (valor = contenido o `"ERROR: <motivo>"` por fichero — un fallo no tumba el lote);
  `get_metadata(allowed, zonas, oracle, path) -> dict` (name, size, mtime ISO, is_dir,
  tier, hydration);
  `list_dir(allowed, zonas, path, sizes: bool = False, max_entries: int = 500) -> list[dict]`
  (hijos directos; los Tier 0 se OMITEN y se cuentan en la clave `"_podados"` del
  último elemento si hubo poda).

- [ ] **Step 1: Test que falla**

```python
# tests/test_expedientes_xl_readops.py
from pathlib import Path
import pytest
from plugins.expedientes_xl.readops import read_text, read_multiple, get_metadata, list_dir
from plugins.expedientes_xl.tiers import Zonas, TierViolation
from plugins.expedientes_xl.guards import GDocBloqueado

class FakeOracle:
    def status(self, p): return "HOT"
    def subtree_cold_stats(self, p): return (0, 0)

@pytest.fixture
def sandbox(tmp_path):
    caso = tmp_path / "CASOS" / "Caso1"
    (caso / "00_Input").mkdir(parents=True)
    (caso / "90_Notas personales").mkdir()
    (caso / "00_Input" / "doc.txt").write_text("l1\nl2\nl3\nl4\n", encoding="utf-8")
    (caso / "90_Notas personales" / "secreto.txt").write_text("privado", encoding="utf-8")
    (caso / "hoja.gsheet").write_text("{}", encoding="utf-8")
    zonas = Zonas(rw_roots=(tmp_path,))
    return tmp_path, zonas, caso

def test_read_text_y_head_tail(sandbox):
    root, zonas, caso = sandbox
    f = str(caso / "00_Input" / "doc.txt")
    assert read_text([root], zonas, FakeOracle(), f) == "l1\nl2\nl3\nl4\n"
    assert read_text([root], zonas, FakeOracle(), f, head=2) == "l1\nl2\n"
    assert read_text([root], zonas, FakeOracle(), f, tail=1) == "l4\n"

def test_read_text_bloquea_tier0_y_gdoc(sandbox):
    root, zonas, caso = sandbox
    with pytest.raises(TierViolation):
        read_text([root], zonas, FakeOracle(), str(caso / "90_Notas personales" / "secreto.txt"))
    with pytest.raises(GDocBloqueado):
        read_text([root], zonas, FakeOracle(), str(caso / "hoja.gsheet"))

def test_read_multiple_aisla_errores(sandbox):
    root, zonas, caso = sandbox
    res = read_multiple([root], zonas, FakeOracle(),
                        [str(caso / "00_Input" / "doc.txt"), str(caso / "no_existe.txt")])
    assert res[str(caso / "00_Input" / "doc.txt")].startswith("l1")
    assert res[str(caso / "no_existe.txt")].startswith("ERROR:")

def test_get_metadata(sandbox):
    root, zonas, caso = sandbox
    m = get_metadata([root], zonas, FakeOracle(), str(caso / "00_Input" / "doc.txt"))
    assert m["name"] == "doc.txt" and m["tier"] == 1 and m["hydration"] == "HOT"
    assert m["size"] == 12 and m["is_dir"] is False

def test_list_dir_poda_tier0(sandbox):
    root, zonas, caso = sandbox
    entradas = list_dir([root], zonas, str(caso))
    nombres = [e["name"] for e in entradas if "name" in e]
    assert "00_Input" in nombres and "hoja.gsheet" in nombres
    assert "90_Notas personales" not in nombres
    assert entradas[-1].get("_podados") == 1
```

- [ ] **Step 2: Verificar que falla** → FAIL
- [ ] **Step 3: Implementación**

```python
# plugins/expedientes_xl/readops.py
"""Operaciones de lectura/navegación con tiers y guardas Stream-aware."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from . import fsops
from .guards import check_gdoc, guard_file
from .tiers import Tier, Zonas, check_read, classify

_READ_MAX = int(os.environ.get("XL_READ_MAX_BYTES", "5000000"))


def _abrir(allowed, zonas, oracle, path: str) -> Path:
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    check_gdoc(p)
    guard_file(oracle, p)
    return p


def read_text(allowed, zonas, oracle, path: str,
              head: int | None = None, tail: int | None = None) -> str:
    p = _abrir(allowed, zonas, oracle, path)
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
        texto = fh.read(_READ_MAX)
    if head is not None:
        return "".join(texto.splitlines(keepends=True)[:head])
    if tail is not None:
        return "".join(texto.splitlines(keepends=True)[-tail:])
    return texto


def read_multiple(allowed, zonas, oracle, paths: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in paths:
        try:
            out[path] = read_text(allowed, zonas, oracle, path)
        except Exception as e:  # aislar: un fallo no tumba el lote
            out[path] = f"ERROR: {e}"
    return out


def get_metadata(allowed, zonas, oracle, path: str) -> dict:
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    st = p.stat()
    return {
        "name": p.name,
        "size": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
        "is_dir": p.is_dir(),
        "tier": int(classify(zonas, p)),
        "hydration": oracle.status(p) if not p.is_dir() else None,
    }


def list_dir(allowed, zonas, path: str, sizes: bool = False,
             max_entries: int = 500) -> list[dict]:
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    out: list[dict] = []
    podados = 0
    for hijo in sorted(p.iterdir()):
        if classify(zonas, hijo) is Tier.PROHIBIDA:
            podados += 1
            continue
        if len(out) >= max_entries:
            out.append({"_truncado": True})
            break
        e: dict = {"name": hijo.name, "is_dir": hijo.is_dir()}
        if sizes and not hijo.is_dir():
            try:
                e["size"] = hijo.stat().st_size
            except OSError:
                e["size"] = None
        out.append(e)
    if podados:
        out.append({"_podados": podados})
    return out
```

- [ ] **Step 4: Verificar que pasa** → PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/readops.py tests/test_expedientes_xl_readops.py
git commit -m "feat(xl): readops - read_text(head/tail), read_multiple, get_metadata, list_dir con poda Tier 0"
```

---

### Task 10: `readops.py` — `iter_tree` con poda + `tree` + `search_name`

**Files:**
- Modify: `plugins/expedientes_xl/readops.py`
- Test: `tests/test_expedientes_xl_readops.py` (añadir)

**Interfaces:**
- Produces: `iter_tree(zonas, root: Path, on_prune=None)` (generador de `Path` de
  ficheros, `os.walk` topdown podando directorios Tier 0; `on_prune(path)` callback);
  `tree(allowed, zonas, path, max_depth: int = 8, max_entries: int = 2000) -> dict`
  (`{"entries": [rel_paths...], "podados": n, "truncado": bool}`);
  `search_name(allowed, zonas, path, patron: str, max_results: int = 200) -> list[str]`
  (fnmatch case-insensitive sobre el nombre, con poda).

- [ ] **Step 1: Test que falla**

```python
# añadir a tests/test_expedientes_xl_readops.py
from plugins.expedientes_xl.readops import iter_tree, tree, search_name

def test_iter_tree_poda_tier0(sandbox):
    root, zonas, caso = sandbox
    podas = []
    vistos = [p.name for p in iter_tree(zonas, caso, on_prune=podas.append)]
    assert "doc.txt" in vistos and "secreto.txt" not in vistos
    assert len(podas) == 1 and podas[0].name == "90_Notas personales"

def test_tree_estructura(sandbox):
    root, zonas, caso = sandbox
    t = tree([root], zonas, str(caso))
    assert any(e.endswith("doc.txt") for e in t["entries"])
    assert t["podados"] == 1 and t["truncado"] is False

def test_search_name(sandbox):
    root, zonas, caso = sandbox
    hits = search_name([root], zonas, str(caso), "*.txt")
    assert any(h.endswith("doc.txt") for h in hits)
    assert not any("secreto" in h for h in hits)   # Tier 0 podado
```

- [ ] **Step 2: Verificar que falla** → FAIL
- [ ] **Step 3: Implementación** (añadir a `readops.py`)

```python
from fnmatch import fnmatch


def iter_tree(zonas: Zonas, root: Path, on_prune=None):
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        base = Path(dirpath)
        vivos = []
        for d in dirnames:
            if classify(zonas, base / d) is Tier.PROHIBIDA:
                if on_prune:
                    on_prune(base / d)
            else:
                vivos.append(d)
        dirnames[:] = vivos
        for f in filenames:
            yield base / f


def tree(allowed, zonas, path: str, max_depth: int = 8, max_entries: int = 2000) -> dict:
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    entries: list[str] = []
    podados = 0
    truncado = False

    def _poda(_ruta):
        nonlocal podados
        podados += 1

    for f in iter_tree(zonas, p, on_prune=_poda):
        rel = f.relative_to(p)
        if len(rel.parts) > max_depth:
            continue
        if len(entries) >= max_entries:
            truncado = True
            break
        entries.append(rel.as_posix())
    return {"entries": entries, "podados": podados, "truncado": truncado}


def search_name(allowed, zonas, path: str, patron: str, max_results: int = 200) -> list[str]:
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    hits: list[str] = []
    for f in iter_tree(zonas, p):
        if fnmatch(f.name.lower(), patron.lower()):
            hits.append(str(f))
            if len(hits) >= max_results:
                break
    return hits
```

- [ ] **Step 4: Verificar que pasa** → PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/readops.py tests/test_expedientes_xl_readops.py
git commit -m "feat(xl): iter_tree con poda Tier 0 + tree + search_name (clausula de travesia)"
```

---

### Task 11: `readops.py` — `search_content`

**Files:**
- Modify: `plugins/expedientes_xl/readops.py`
- Test: `tests/test_expedientes_xl_readops.py` (añadir)

**Interfaces:**
- Produces: `search_content(allowed, zonas, oracle, path, consulta: str,
  regex: bool = False, max_results: int = 200) -> dict`
  → `{"matches": [{"path": str, "line": int, "text": str}], "omitidos_cold": [str],
  "podados": int}`. Salta binarios (byte nulo en los primeros 8 KB) y ficheros `.g*`;
  los COLD/UNKNOWN por encima del umbral de fichero se OMITEN y se listan (sin
  silencios); los HOT se leen con `errors="replace"`.

- [ ] **Step 1: Test que falla**

```python
# añadir a tests/test_expedientes_xl_readops.py
from plugins.expedientes_xl.readops import search_content

class ColdOracle(FakeOracle):
    def __init__(self, cold_names): self.cold = cold_names
    def status(self, p): return "COLD" if p.name in self.cold else "HOT"

def test_search_content_basico(sandbox):
    root, zonas, caso = sandbox
    res = search_content([root], zonas, FakeOracle(), str(caso), "l3")
    assert res["matches"][0]["line"] == 3 and res["matches"][0]["text"] == "l3"
    assert res["podados"] == 1                       # 90_Notas fuera
    assert not any("secreto" in m["path"] for m in res["matches"])

def test_search_content_omite_cold_grande(sandbox, monkeypatch):
    root, zonas, caso = sandbox
    monkeypatch.setenv("XL_HYDRATION_MAX_FILE_MB", "0")   # todo grande
    res = search_content([root], zonas, ColdOracle({"doc.txt"}), str(caso), "l3")
    assert res["matches"] == []
    assert any(o.endswith("doc.txt") for o in res["omitidos_cold"])

def test_search_content_salta_binarios(sandbox):
    root, zonas, caso = sandbox
    (caso / "bin.dat").write_bytes(b"l3\x00binario")
    res = search_content([root], zonas, FakeOracle(), str(caso), "l3")
    assert not any(m["path"].endswith("bin.dat") for m in res["matches"])
```

- [ ] **Step 2: Verificar que falla** → FAIL
- [ ] **Step 3: Implementación** (añadir a `readops.py`)

```python
import re as _re

from .guards import FileNotHydrated, GDocBloqueado


def search_content(allowed, zonas, oracle, path: str, consulta: str,
                   regex: bool = False, max_results: int = 200) -> dict:
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    patron = _re.compile(consulta) if regex else None
    matches: list[dict] = []
    omitidos: list[str] = []
    podados = 0

    def _poda(_r):
        nonlocal podados
        podados += 1

    for f in iter_tree(zonas, p, on_prune=_poda):
        if len(matches) >= max_results:
            break
        try:
            check_gdoc(f)
            guard_file(oracle, f)
        except GDocBloqueado:
            continue
        except FileNotHydrated:
            omitidos.append(str(f))
            continue
        try:
            with open(f, "rb") as fh:
                if b"\x00" in fh.read(8192):
                    continue
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                for n, linea in enumerate(fh, 1):
                    hit = patron.search(linea) if patron else (consulta in linea)
                    if hit:
                        matches.append({"path": str(f), "line": n,
                                        "text": linea.rstrip("\n")[:300]})
                        if len(matches) >= max_results:
                            break
        except OSError:
            continue
    return {"matches": matches, "omitidos_cold": omitidos, "podados": podados}
```

- [ ] **Step 4: Verificar que pasa** → PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/readops.py tests/test_expedientes_xl_readops.py
git commit -m "feat(xl): search_content - grep con poda Tier 0, salto de binarios y omision COLD listada"
```

---

### Task 12: `fsops.py` — escrituras atómicas y `copy_tree` v2 con travesía

**Files:**
- Modify: `plugins/expedientes_xl/fsops.py`
- Test: `tests/test_expedientes_xl_fsops.py` (añadir; ADAPTAR tests existentes de `copy_tree`)

**Interfaces:**
- Consumes: `atomic_write_text`/`atomic_write_bytes`/`retry_sharing` (winio),
  `Zonas`/`check_write`/`classify`/`Tier` (tiers), `iter_tree` (readops),
  `guard_tree` (guards).
- Produces:
  `write_text_file(allowed, zonas, path, text) -> Path` (atómico; `check_write` con
  `exists` real);
  `edit_text_file(allowed, zonas, path, old: str, new: str) -> Path` (el fichero debe
  existir; `old` debe aparecer EXACTAMENTE una vez, si no `ValueError`; escritura
  atómica);
  `copy_file_v2(allowed, zonas, src, dst) -> Path` (origen `check_read`+existencia;
  destino `check_write`; si `dst` existe → copia a tmp + `os.replace`);
  `copy_tree_v2(allowed, zonas, oracle, src, dst) -> list[Path]` — **dos pasadas**:
  (1) PRE-SCAN: `guard_tree(src)`; recorrer `iter_tree(src)` calculando cada destino
  y validando `check_write(dst_f, exists=dst_f.exists())` — CUALQUIER violación →
  aborto SIN copiar nada; (2) COPIA: por fichero, `copy_file_v2`. Devuelve la lista
  copiada. Los Tier 0 del origen se podan (no viajan). El `copy_tree` antiguo
  (`shutil.copytree(dirs_exist_ok=True)`) SE ELIMINA.
- Cambios a tests existentes: los tests de `copy_tree` en
  `tests/test_expedientes_xl_fsops.py` pasan a llamar `copy_tree_v2` con
  `Zonas(rw_roots=(tmp_path,))` y `FakeOracle`; el comportamiento "sobrescribir árbol
  existente en silencio" DEJA de estar soportado (test nuevo asegura el aborto).

- [ ] **Step 1: Tests que fallan**

```python
# añadir a tests/test_expedientes_xl_fsops.py
from pathlib import Path
import pytest
from plugins.expedientes_xl import fsops
from plugins.expedientes_xl.tiers import Zonas, TierViolation

class FakeOracle:
    def status(self, p): return "HOT"
    def subtree_cold_stats(self, p): return (0, 1)

def _zonas(tmp_path): return Zonas(rw_roots=(tmp_path,))

def test_write_text_file_atomico(tmp_path):
    z = _zonas(tmp_path)
    f = tmp_path / "01_Procesado" / "nota.md"
    fsops.write_text_file([tmp_path], z, str(f), "hola")
    assert f.read_text(encoding="utf-8") == "hola"

def test_write_text_file_respeta_00input(tmp_path):
    z = _zonas(tmp_path)
    f = tmp_path / "00_Input" / "depositado.txt"
    fsops.write_text_file([tmp_path], z, str(f), "v1")       # crear-nuevo: ok
    with pytest.raises(TierViolation):
        fsops.write_text_file([tmp_path], z, str(f), "v2")   # sobrescribir: no

def test_edit_text_file_unica_aparicion(tmp_path):
    z = _zonas(tmp_path)
    f = tmp_path / "doc.md"; f.write_text("a b a", encoding="utf-8")
    with pytest.raises(ValueError):
        fsops.edit_text_file([tmp_path], z, str(f), "a", "z")   # 2 apariciones
    fsops.edit_text_file([tmp_path], z, str(f), "b", "z")
    assert f.read_text(encoding="utf-8") == "a z a"

def test_copy_tree_v2_poda_y_aborta(tmp_path):
    z = _zonas(tmp_path)
    src = tmp_path / "src"; (src / "90_Notas personales").mkdir(parents=True)
    (src / "doc.txt").write_text("x", encoding="utf-8")
    (src / "90_Notas personales" / "s.txt").write_text("p", encoding="utf-8")
    dst = tmp_path / "dst"
    copiados = fsops.copy_tree_v2([tmp_path], z, FakeOracle(), str(src), str(dst))
    assert (dst / "doc.txt").exists()
    assert not (dst / "90_Notas personales").exists()          # podado
    # destino que cae en 00_Input existente -> aborto TOTAL sin copiar nada
    dst2 = tmp_path / "00_Input"
    (dst2).mkdir(); (dst2 / "doc.txt").write_text("orig", encoding="utf-8")
    with pytest.raises(TierViolation):
        fsops.copy_tree_v2([tmp_path], z, FakeOracle(), str(src), str(dst2))
    assert (dst2 / "doc.txt").read_text(encoding="utf-8") == "orig"  # intacto
```

- [ ] **Step 2: Verificar que falla** → FAIL
- [ ] **Step 3: Implementación** (en `fsops.py`; imports arriba del fichero:
  `from .tiers import Zonas, check_read as _check_read, check_write as _check_write`
  `from .winio import atomic_write_text, retry_sharing`
  `from .readops import iter_tree` — import LOCAL dentro de las funciones si hay
  ciclo readops↔fsops; readops importa fsops, así que aquí importar dentro de la
  función):

```python
def write_text_file(allowed_dirs, zonas, path, text):
    """Escribe texto ATÓMICO (tmp+nonce mismo dir) respetando zonas."""
    from .tiers import check_write
    from .winio import atomic_write_text
    dst = resolve_within(allowed_dirs, path)
    check_write(zonas, dst, exists=dst.exists())
    atomic_write_text(dst, text)
    return dst


def edit_text_file(allowed_dirs, zonas, path, old, new):
    """Reemplaza `old` (exactamente 1 aparición) por `new`, atómico."""
    from .tiers import check_write
    from .winio import atomic_write_text
    dst = resolve_within(allowed_dirs, path)
    if not dst.is_file():
        raise FileNotFoundError(f"No existe: {path}")
    check_write(zonas, dst, exists=True)
    texto = dst.read_text(encoding="utf-8")
    n = texto.count(old)
    if n != 1:
        raise ValueError(f"'{old[:60]}' aparece {n} veces (se exige exactamente 1)")
    atomic_write_text(dst, texto.replace(old, new, 1))
    return dst


def copy_file_v2(allowed_dirs, zonas, src, dst):
    """Copia con destino atómico (si existe: tmp+replace) y zonas en ambos extremos."""
    import tempfile
    from .tiers import check_read, check_write
    from .winio import retry_sharing
    src_p = resolve_within(allowed_dirs, src)
    dst_p = resolve_within(allowed_dirs, dst)
    check_read(zonas, src_p)
    check_write(zonas, dst_p, exists=dst_p.exists())
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=dst_p.name + ".", suffix=".tmp", dir=str(dst_p.parent))
    os.close(fd)
    try:
        shutil.copyfile(src_p, tmp)
        retry_sharing(lambda: os.replace(tmp, dst_p))
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return dst_p


def copy_tree_v2(allowed_dirs, zonas, oracle, src, dst):
    """Copia recursiva con travesía por nodo: poda Tier 0, valida CADA destino
    ANTES de copiar nada (dos pasadas), guarda de árbol frío."""
    from .guards import guard_tree
    from .readops import iter_tree
    from .tiers import check_write
    src_p = resolve_within(allowed_dirs, src)
    dst_p = resolve_within(allowed_dirs, dst)
    guard_tree(oracle, src_p)
    plan: list[tuple[Path, Path]] = []
    for f in iter_tree(zonas, src_p):
        destino = dst_p / f.relative_to(src_p)
        check_write(zonas, destino, exists=destino.exists())  # aborta ANTES de copiar
        plan.append((f, destino))
    copiados: list[Path] = []
    for origen, destino in plan:
        copiados.append(copy_file_v2(allowed_dirs, zonas, str(origen), str(destino)))
    return sorted(copiados)
```

Y **eliminar** la antigua `copy_tree` (y adaptar sus tests existentes a
`copy_tree_v2`, manteniendo los casos de sandbox/anti-traversal que ya prueban
`resolve_within`).

- [ ] **Step 4: Verificar que pasa** → `python -m pytest tests/test_expedientes_xl_fsops.py -q` PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/fsops.py tests/test_expedientes_xl_fsops.py
git commit -m "feat(xl): write/edit atomicos + copy_tree_v2 con travesia por nodo (pre-scan, poda, aborto)"
```

---

### Task 13: `readops.py` — `resolve_shortcut` con re-validación

**Files:**
- Modify: `plugins/expedientes_xl/readops.py`
- Test: `tests/test_expedientes_xl_readops.py` (añadir)

**Interfaces:**
- Produces: `resolve_shortcut(allowed, zonas, path) -> dict`
  (`{"target": str | None, "dentro_sandbox": bool, "tier": int | None}`).
  Resolución vía PowerShell COM (subprocess, sin dependencias); el TARGET se
  re-valida: si `resolve_within` falla o Tier 0 → `dentro_sandbox=False`,
  `target=None` en Tier 0 (no filtrar la ruta prohibida al modelo) y se registra
  en auditoría el intento.
- El parser COM se INYECTA (`_resolver_lnk` como parámetro con default) para
  testear sin COM.

- [ ] **Step 1: Test que falla**

```python
# añadir a tests/test_expedientes_xl_readops.py
from plugins.expedientes_xl.readops import resolve_shortcut

def test_resolve_shortcut_revalida(sandbox):
    root, zonas, caso = sandbox
    lnk = caso / "atajo.lnk"; lnk.write_bytes(b"fake")
    ok = resolve_shortcut([root], zonas, str(lnk),
                          _resolver_lnk=lambda p: str(caso / "00_Input" / "doc.txt"))
    assert ok["dentro_sandbox"] is True and ok["tier"] == 1

    fuera = resolve_shortcut([root], zonas, str(lnk),
                             _resolver_lnk=lambda p: r"C:\Windows\System32\cmd.exe")
    assert fuera["dentro_sandbox"] is False and fuera["target"] is None

    tier0 = resolve_shortcut([root], zonas, str(lnk),
                             _resolver_lnk=lambda p: str(caso / "90_Notas personales" / "s.txt"))
    assert tier0["dentro_sandbox"] is False and tier0["target"] is None
```

- [ ] **Step 2: Verificar que falla** → FAIL
- [ ] **Step 3: Implementación** (añadir a `readops.py`)

```python
import subprocess

from . import audit
from .fsops import OutsideSandbox


def _resolver_lnk_com(path: str) -> str:
    ps = ("(New-Object -ComObject WScript.Shell)"
          f".CreateShortcut('{path}').TargetPath")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, encoding="utf-8", errors="replace",
                       timeout=15)
    return (r.stdout or "").strip()


def resolve_shortcut(allowed, zonas, path: str, _resolver_lnk=_resolver_lnk_com) -> dict:
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    target = _resolver_lnk(str(p))
    if not target:
        return {"target": None, "dentro_sandbox": False, "tier": None}
    try:
        t = fsops.resolve_within(allowed, target)
    except OutsideSandbox:
        audit.log_op("resolve_shortcut", str(p), "escape_bloqueado", motivo=target[:120])
        return {"target": None, "dentro_sandbox": False, "tier": None}
    tier = classify(zonas, t)
    if tier is Tier.PROHIBIDA:
        audit.log_op("resolve_shortcut", str(p), "tier0_bloqueado")
        return {"target": None, "dentro_sandbox": False, "tier": None}
    return {"target": str(t), "dentro_sandbox": True, "tier": int(tier)}
```

- [ ] **Step 4: Verificar que pasa** → PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/readops.py tests/test_expedientes_xl_readops.py
git commit -m "feat(xl): resolve_shortcut con re-validacion de destino (anti-escape, Tier 0 opaco)"
```

---

### Task 14: `server.py` — Zonas/roots, retirar `delete_path`, guardas en tools existentes

**Files:**
- Modify: `plugins/expedientes_xl/server.py`
- Test: `tests/test_expedientes_xl_server.py` (adaptar + añadir)

**Interfaces:**
- Produces: `build_server(zonas: Zonas, oracle, max_b64_bytes=..., max_extract_bytes=...)
  -> FastMCP` (firma NUEVA; `allowed_dirs` = `zonas.rw_roots + zonas.ro_roots`).
  `_parse_argv` acepta `--rw <dir>` (repetible), `--ro <dir>` (repetible),
  `--max-b64-bytes N`; posicionales legacy = `--rw`. `main()` construye el `Oracle`
  con `descubrir_cuentas(%LOCALAPPDATA%/Google/DriveFS, roots)`.
- Cambios en tools EXISTENTES:
  - `delete_path`: **eliminar** el tool (y sus tests).
  - `write_file_base64`: + `check_write(exists=...)` + auditoría.
  - `append_text`: + `check_write(exists=..., append=True)` + auditoría.
  - `copy_path` → delega en `copy_file_v2`; `copy_dir` → `copy_tree_v2` (+ auditoría).
  - `extract_archive`: + `check_write(exists=False)` por MIEMBRO destino (antes de
    volcar; miembro que caiga en Tier 0/1-existente → se OMITE y se lista) + auditoría.
  - `hash_path`: + `check_read` + `guard_file`; `hash_tree`: + `check_read` +
    `guard_tree` + poda Tier 0 (usar `iter_tree` en vez de `rglob`).
- Semáforo global: `threading.BoundedSemaphore(int(os.environ.get("XL_IO_CAP", "2")))`
  envolviendo las operaciones pesadas (`copy_dir`, `hash_tree`, `extract_archive`).
- **Timeout-que-responde** (spec §3.2): las operaciones pesadas corren en un
  `ThreadPoolExecutor(max_workers=XL_IO_CAP)` de módulo con hilos daemon; el tool hace
  `future.result(timeout=float(os.environ.get("XL_OP_TIMEOUT", "120")))` y ante
  `TimeoutError` devuelve error legible («operación sigue en curso en segundo plano;
  reintenta o hidrata primero») — el canal MCP nunca queda colgado. La cancelación
  que aborta la E/S es V2 (solo si se observa acumulación de hilos).

- [ ] **Step 1: Tests que fallan** (adaptar los existentes a la firma nueva y añadir)

```python
# tests/test_expedientes_xl_server.py — patrón de adaptación:
# ANTES: srv = build_server([tmp_path])
# AHORA:
from plugins.expedientes_xl.tiers import Zonas

class FakeOracle:
    def status(self, p): return "HOT"
    def subtree_cold_stats(self, p): return (0, 1)

def _srv(tmp_path):
    return build_server(Zonas(rw_roots=(tmp_path,)), FakeOracle())

# nuevos:
def test_delete_path_retirado(tmp_path):
    srv = _srv(tmp_path)
    nombres = [t.name for t in __import__("asyncio").run(srv.list_tools())]
    assert "delete_path" not in nombres

def test_write_base64_respeta_zonas(tmp_path):
    import asyncio, base64, pytest
    srv = _srv(tmp_path)
    destino = str(tmp_path / "00_Input" / "n.bin")
    b64 = base64.b64encode(b"bytes").decode()
    asyncio.run(srv.call_tool("write_file_base64", {"path": destino, "content_b64": b64}))
    assert (tmp_path / "00_Input" / "n.bin").read_bytes() == b"bytes"   # crear-nuevo ok
    with pytest.raises(Exception, match="forense-inmutable"):           # sobrescribir no
        asyncio.run(srv.call_tool("write_file_base64", {"path": destino, "content_b64": b64}))
```

(El ejecutor adapta los tests existentes de `delete_path` eliminándolos, y los de
`copy_dir` al nuevo comportamiento con poda/aborto.)

- [ ] **Step 2: Verificar que falla** → FAIL
- [ ] **Step 3: Implementación** — recablear `build_server` (estructura):

```python
def build_server(zonas: Zonas, oracle, max_b64_bytes: int = DEFAULT_MAX_B64,
                 max_extract_bytes: int = fsops.DEFAULT_MAX_EXTRACT_BYTES) -> FastMCP:
    mcp = FastMCP("expedientes-xl")
    allowed = list(zonas.rw_roots) + list(zonas.ro_roots)
    io_cap = threading.BoundedSemaphore(int(os.environ.get("XL_IO_CAP", "2")))

    @mcp.tool()
    def hash_path(path: str) -> str:
        """SHA-256 (hex) de un fichero, calculado server-side."""
        p = fsops.resolve_within(allowed, path)
        tiers.check_read(zonas, p)
        guards.guard_file(oracle, p)
        return fsops.sha256_file(allowed, path)

    @mcp.tool()
    def hash_tree(root: str) -> dict[str, str]:
        """SHA-256 recursivo (poda 90_Notas; aborta árbol frío grande)."""
        with io_cap:
            p = fsops.resolve_within(allowed, root)
            tiers.check_read(zonas, p)
            guards.guard_tree(oracle, p)
            out = {}
            for f in readops.iter_tree(zonas, p):
                out[f.relative_to(p).as_posix()] = fsops.sha256_file(allowed, str(f))
            return out

    @mcp.tool()
    def write_file_base64(path: str, content_b64: str) -> int:
        """Escribe un binario desde base64 (respeta zonas; tope configurado)."""
        p = fsops.resolve_within(allowed, path)
        tiers.check_write(zonas, p, exists=p.exists())
        n = fsops.write_base64(allowed, path, content_b64, max_b64_bytes)
        audit.log_op("write_file_base64", str(p), "ok", bytes=n)
        return n

    # ... resto de tools existentes con el mismo patrón (check + guardas + audit);
    # copy_path -> fsops.copy_file_v2; copy_dir -> fsops.copy_tree_v2 (con io_cap);
    # append_text -> check_write(append=True); extract_archive -> filtro por miembro.
    # delete_path: NO registrar.
    return mcp
```

`_parse_argv` nuevo:

```python
def _parse_argv(argv: list[str]) -> tuple[Zonas, int]:
    rw: list[Path] = []
    ro: list[Path] = []
    max_b64 = DEFAULT_MAX_B64
    it = iter(argv)
    for a in it:
        if a == "--rw":
            rw.append(Path(next(it)))
        elif a == "--ro":
            ro.append(Path(next(it)))
        elif a == "--max-b64-bytes":
            max_b64 = int(next(it))
        else:
            rw.append(Path(a))  # legacy posicional
    if not rw and not ro:
        raise SystemExit("Uso: server.py [--rw DIR]... [--ro DIR]... [--max-b64-bytes N]")
    return Zonas(rw_roots=tuple(rw), ro_roots=tuple(ro)), max_b64
```

- [ ] **Step 4: Suite verde** → `python -m pytest tests/test_expedientes_xl_server.py tests/test_expedientes_xl_fsops.py -q` PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/server.py tests/test_expedientes_xl_server.py
git commit -m "feat(xl): server con Zonas rw/ro, delete_path retirado, guardas+audit en tools existentes, semaforo E/S"
```

---

### Task 15: `server.py` — cablear las tools nuevas

**Files:**
- Modify: `plugins/expedientes_xl/server.py`
- Test: `tests/test_expedientes_xl_server.py` (añadir)

**Interfaces:**
- Produces (nombres de tool MCP, spec §5): `read_text(path, head=None, tail=None)`,
  `read_multiple(paths)`, `list_dir(path, sizes=False)`, `tree(path, max_depth=8)`,
  `get_metadata(path)`, `search_name(path, patron)`, `search_content(path, consulta,
  regex=False)`, `create_dir(path)`, `write_text(path, text)`, `edit_text(path, old,
  new)`, `resolve_shortcut(path)`, `hydration_status(path)`.
  Todos delegan en `readops`/`fsops` (Tasks 9-13); `search_content` y `tree` bajo el
  semáforo; mutaciones auditan. `create_dir` = `mkdir(parents=True, exist_ok=True)`
  tras `check_write(exists=False)`. `hydration_status` devuelve
  `{"status": oracle.status(p)}` tras `check_read`.

- [ ] **Step 1: Test que falla**

```python
# añadir a tests/test_expedientes_xl_server.py
import asyncio, json

def test_tools_nuevas_registradas(tmp_path):
    srv = _srv(tmp_path)
    nombres = {t.name for t in asyncio.run(srv.list_tools())}
    esperadas = {"read_text", "read_multiple", "list_dir", "tree", "get_metadata",
                 "search_name", "search_content", "create_dir", "write_text",
                 "edit_text", "resolve_shortcut", "hydration_status"}
    assert esperadas <= nombres

def test_read_text_via_tool(tmp_path):
    (tmp_path / "d.txt").write_text("hola\n", encoding="utf-8")
    srv = _srv(tmp_path)
    res = asyncio.run(srv.call_tool("read_text", {"path": str(tmp_path / "d.txt")}))
    assert "hola" in str(res)
```

- [ ] **Step 2: Verificar que falla** → FAIL
- [ ] **Step 3: Implementación** — registrar los 12 tools con el patrón de Task 14
  (cada uno delega en su función de `readops`/`fsops`; docstrings castellano de una
  línea; `write_text`/`edit_text`/`create_dir` auditan con `audit.log_op`).

- [ ] **Step 4: Suite verde completa** → `python -m pytest -q --tb=no` PASS
- [ ] **Step 5: Commit**

```powershell
git add plugins/expedientes_xl/server.py tests/test_expedientes_xl_server.py
git commit -m "feat(xl): 12 tools nuevas de lectura/navegacion/busqueda/escritura cableadas"
```

---

### Task 16: Test de integración end-to-end

**Files:**
- Test: `tests/test_expedientes_xl_integracion.py` (nuevo)

Sandbox temporal que simula la estructura real (G/H falsos) y verifica el CONJUNTO:

- [ ] **Step 1: Escribir el test completo**

```python
# tests/test_expedientes_xl_integracion.py
"""E2E del servidor consolidado sobre un arbol de caso simulado."""
import asyncio
from pathlib import Path
import pytest
from plugins.expedientes_xl.server import build_server
from plugins.expedientes_xl.tiers import Zonas

class Orac:
    def __init__(self): self.cold = set()
    def status(self, p): return "COLD" if p.name in self.cold else "HOT"
    def subtree_cold_stats(self, p): return (len(self.cold), 10)

@pytest.fixture
def mundo(tmp_path):
    g = tmp_path / "G"; h = tmp_path / "H"
    caso = g / "Unidades compartidas" / "EXPEDIENTES" / "CASOS" / "Caso1"
    (caso / "00_Input" / "03_Email").mkdir(parents=True)
    (caso / "90_Notas personales").mkdir()
    (caso / "01_Procesado").mkdir()
    # mismo nombre que un fichero ya depositado: fuerza el aborto del punto 6
    (caso / "01_Procesado" / "m.eml").write_text("copia", encoding="utf-8")
    (caso / "00_Input" / "_caso.md").write_text("---\nestado: x\n---\n", encoding="utf-8")
    (caso / "00_Input" / "03_Email" / "m.eml").write_text("mail", encoding="utf-8")
    (caso / "90_Notas personales" / "priv.md").write_text("secreto", encoding="utf-8")
    (h / "Mi unidad").mkdir(parents=True)
    (h / "Mi unidad" / "doc.txt").write_text("ev", encoding="utf-8")
    zonas = Zonas(rw_roots=(g,), ro_roots=(h,))
    return build_server(zonas, Orac()), g, h, caso

def _call(srv, tool, **args):
    return asyncio.run(srv.call_tool(tool, args))

def test_e2e(mundo):
    srv, g, h, caso = mundo
    # 1. leer H: (ro) OK; escribir H: NO
    assert "ev" in str(_call(srv, "read_text", path=str(h / "Mi unidad" / "doc.txt")))
    with pytest.raises(Exception, match="solo-lectura"):
        _call(srv, "write_text", path=str(h / "Mi unidad" / "x.txt"), text="no")
    # 2. tree del caso NO expone 90_Notas
    t = str(_call(srv, "tree", path=str(caso)))
    assert "priv.md" not in t and "m.eml" in t
    # 3. search_content no lee Tier 0
    s = str(_call(srv, "search_content", path=str(caso), consulta="secreto"))
    assert "priv.md" not in s
    # 4. intake: crear-nuevo bajo 00_Input ok; sobrescribir no
    nuevo = caso / "00_Input" / "04_Manual" / "n.pdf"
    _call(srv, "write_text", path=str(nuevo), text="pdfsimulado")
    with pytest.raises(Exception, match="forense-inmutable"):
        _call(srv, "write_text", path=str(nuevo), text="v2")
    # 5. carve-out: editar _caso.md ok
    _call(srv, "edit_text", path=str(caso / "00_Input" / "_caso.md"),
          old="estado: x", new="estado: prestado")
    # 6. copy_dir cuyo destino PISA un fichero ya depositado en 00_Input -> aborto
    #    total ANTES de copiar nada (01_Procesado contiene m.eml, que ya existe en
    #    00_Input/03_Email). Crear-nuevo bajo 00_Input sí es legal; pisar, no.
    with pytest.raises(Exception, match="forense-inmutable"):
        _call(srv, "copy_dir", src=str(caso / "01_Procesado"),
              dst=str(caso / "00_Input" / "03_Email"))
    assert (caso / "00_Input" / "03_Email" / "m.eml").read_text(encoding="utf-8") == "mail"
```

- [ ] **Step 2: Ejecutar** → `python -m pytest tests/test_expedientes_xl_integracion.py -q`
  (ajustar los `match=` a los mensajes reales si difieren). Expected: PASS
- [ ] **Step 3: Suite completa** → `python -m pytest -q --tb=no` PASS
- [ ] **Step 4: Commit**

```powershell
git add tests/test_expedientes_xl_integracion.py
git commit -m "test(xl): integracion e2e - tiers, poda, carve-out, H: ro, copy_dir aborta"
```

---

### Task 17: Arranque poll-until-mount + configs

**Files:**
- Create: `plugins/expedientes_xl/run_server.bat`
- Modify: `plugin-src/.mcp.json`, `plugins/expedientes_mcp/config_ejemplo.json` (añadir
  bloque de ejemplo del consolidado, sin tocar el de `expedientes` aún)

- [ ] **Step 1: Escribir `run_server.bat`** (patrón EXACTO de
  `plugins/expedientes_mcp/run_server.bat` — respetar sus REGLAS DE ORO: jamás stdout,
  jamás `timeout`/`start`/`call`, python en primer plano en la última línea):

```bat
@echo off
REM expedientes-xl consolidado - espera el montaje de G: y H: antes de arrancar.
REM Reglas de oro: ver plugins/expedientes_mcp/run_server.bat (mismo patron).
setlocal
set "PROBE_G=G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS"
set "PROBE_H=H:\Unidades compartidas"
set "SRV=%~dp0server.py"
set "LOG=%APPDATA%\Claude\logs\mcp-server-expedientes-xl-wrapper.log"
if not exist "%APPDATA%\Claude\logs" mkdir "%APPDATA%\Claude\logs" 2>NUL
set /a TRIES=0
set /a MAXTRIES=25
:waitloop
if exist "%PROBE_G%\" if exist "%PROBE_H%\" goto ready
set /a TRIES+=1
if %TRIES% GEQ %MAXTRIES% (
  echo [xl-wrapper] TIMEOUT: G:/H: no montaron tras ~50s>>"%LOG%"
  echo [xl-wrapper] TIMEOUT: G:/H: no montaron - abre Google Drive y reinicia 1>&2
  exit /b 1
)
ping -n 3 127.0.0.1 >NUL
goto waitloop
:ready
echo [xl-wrapper] montadas; arrancando server consolidado>>"%LOG%"
python "%SRV%" --rw "G:\" --ro "H:\" 2>>"%LOG%"
```

- [ ] **Step 2: Actualizar `plugin-src/.mcp.json`** — entrada `expedientes-xl`:

```json
"expedientes-xl": {
  "command": "cmd",
  "args": ["/c", "${CLAUDE_PLUGIN_ROOT}/expedientes_xl/run_server.bat"]
}
```

- [ ] **Step 3: Probar el arranque a mano**

Run (PowerShell): `cmd /c plugins\expedientes_xl\run_server.bat` (con G:/H: montadas)
Expected: el proceso queda vivo esperando stdin (Ctrl+C para salir); el log del
wrapper registra "montadas".

- [ ] **Step 4: Commit**

```powershell
git add plugins/expedientes_xl/run_server.bat plugin-src/.mcp.json plugins/expedientes_mcp/config_ejemplo.json
git commit -m "feat(xl): wrapper poll-until-mount para G:+H: y cableado del plugin"
```

---

### Task 18: Documentación, empaquetado y checklist de despliegue

**Files:**
- Modify: `plugins/expedientes_xl/README.md`, `docs/MEJORAS_FUTURAS.md`
- Create: `docs/DESPLIEGUE_MCP_DRIVE_DISCO.md`

- [ ] **Step 1: README del plugin** — actualizar: superficie completa de tools
  (existentes + 12 nuevas), tabla de tiers, variables `XL_*`, límites conocidos
  (H: 100 % COLD → primera lectura descarga; conflict-copies de nube = límite GDFD).

- [ ] **Step 2: `docs/DESPLIEGUE_MCP_DRIVE_DISCO.md`** — la secuencia §8 del spec como
  checklist ejecutable:

```markdown
# Despliegue del servidor consolidado (spec §8 — orden OBLIGATORIO)
1. [ ] Mergear el PR de código; `python -m pytest -q --tb=no` verde en main.
2. [ ] Claude Code: verificar que plugin-src/.mcp.json apunta al run_server.bat
       y que las tools nuevas responden (read_text sobre un fichero de G:).
3. [ ] Claude Desktop (Cowork): con la app CERRADA (¡reescribe su config al cerrar!),
       actualizar el bloque expedientes-xl en claude_desktop_config.json al wrapper.
4. [ ] Validar en Cowork: read_text/list_dir/search_content sobre G: y H:.
5. [ ] Re-empaquetar skills afectadas y re-importar en Cowork.
6. [ ] Migrar organizar-sala-lectura a los nombres del consolidado
       (write_file→write_text, read_media_file→YA NO — binarios no van al modelo).
7. [ ] SOLO ENTONCES retirar la entrada `expedientes` de claude_desktop_config.json.
8. [ ] Sesión de humo: intake de un fichero de prueba + tree de un caso + grep.
NUNCA dejar la skill migrada con el server viejo activo (o viceversa).
```

- [ ] **Step 3: `docs/MEJORAS_FUTURAS.md`** — añadir entrada V2 con lo diferido
  (move/rename/batch_rename pelado/create_zip/du/verify_manifest/escritura-H:/gate
  compartido/cancelación-real/confirm_sync-como-skill) con referencia al spec y la
  regla de promoción.

- [ ] **Step 4: Suite completa + commit**

```powershell
python -m pytest -q --tb=no
git add plugins/expedientes_xl/README.md docs/DESPLIEGUE_MCP_DRIVE_DISCO.md docs/MEJORAS_FUTURAS.md
git commit -m "docs(xl): README consolidado + checklist de despliegue + V2 en MEJORAS_FUTURAS"
```

- [ ] **Step 5: PR**

```powershell
git push -u origin claude/mcp-drive-disco-f1
gh pr create --title "MCP Drive-como-disco V1: servidor consolidado expedientes-xl" --body "Implementa el spec rev 3 (...). Suite completa verde. leak-scan pass."
```

---

## Notas para el ejecutor

1. **Orden**: Tasks 1→18 son secuenciales salvo: Task 0 (spike) en cualquier momento;
   Tasks 3-4 pueden ir en paralelo con 5-7.
2. **Import cíclico** `fsops`↔`readops`: `readops` importa `fsops` a nivel de módulo;
   `fsops` importa `readops`/`tiers`/`winio`/`guards` DENTRO de las funciones nuevas.
3. **pytest-randomly** está activo: ningún test puede depender del orden; los fixtures
   no comparten estado global (cuidado con `os.environ` — usar `monkeypatch.setenv`).
4. **No tocar** `core/`, las skills, ni el server `expedientes` viejo: la migración de
   la skill es del checklist de despliegue (Task 18), manual y posterior.
5. Si un mensaje de error de `match=` difiere en los tests de integración, ajustar el
   test al mensaje real — el CONTRATO es la excepción, no la prosa exacta.
6. **MAX_PATH**: donde una operación abra rutas potencialmente largas
   (`sha256_file`, copias, `open` de readops), pasar `winio.long_path(p)` a `open()`/
   `shutil` cuando `len(str(p)) >= 248`. No hace falta en `Path.iterdir/os.walk`
   (aceptan el resultado ya resuelto).
