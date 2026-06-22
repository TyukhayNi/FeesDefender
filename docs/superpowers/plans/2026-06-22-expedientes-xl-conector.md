# Conector `expedientes-xl` (Plan 1/3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un servidor MCP stdio genérico (`expedientes-xl`) con operaciones de fichero server-side de cualquier tamaño/tipo (hashear, copiar, descomprimir, escribir binario, anexar texto, borrar), acotado a `allowedDirectories`, con saneado anti path-traversal y tope de tamaño.

**Architecture:** Lógica pura en `fsops.py` (sin dependencias de `mcp` ni de `core/`, 100% pytest-testable) + un wrapper fino `server.py` (FastMCP, lee los directorios permitidos de `argv`, expone cada función como tool). Sin `import core` → shippable sin FeesDefender (regla de 3 capas). El saneado replica el patrón de `core/intake_manual.extract_zip` (re-implementado autocontenido, NO importado).

**Tech Stack:** Python 3 (venv del repo), SDK oficial `mcp` (FastMCP), `pytest`. Plataforma Windows + PowerShell.

---

## Estructura de ficheros

- Create: `plugins/expedientes_xl/__init__.py` — paquete.
- Create: `plugins/expedientes_xl/fsops.py` — lógica pura + excepciones + saneado.
- Create: `plugins/expedientes_xl/server.py` — wrapper FastMCP (thin).
- Create: `plugins/expedientes_xl/requirements.txt` — `mcp`.
- Create: `plugins/expedientes_xl/README.md` — cómo registrar el server (Claude Code + `claude_desktop_config.json`).
- Test: `tests/test_expedientes_xl_fsops.py` — toda la lógica pura.

`fsops.py` no importa `mcp` ni `core`. `server.py` es el único que importa `mcp`. Los tests cubren `fsops.py` sin tocar el transporte MCP.

---

## Task 1: Scaffold del paquete + saneado de rutas (`resolve_within`)

**Files:**
- Create: `plugins/expedientes_xl/__init__.py`
- Create: `plugins/expedientes_xl/fsops.py`
- Test: `tests/test_expedientes_xl_fsops.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_expedientes_xl_fsops.py
from pathlib import Path

import pytest

from plugins.expedientes_xl import fsops


def test_resolve_within_acepta_ruta_dentro(tmp_path):
    allowed = [tmp_path]
    target = tmp_path / "sub" / "f.txt"
    assert fsops.resolve_within(allowed, str(target)) == target.resolve()


def test_resolve_within_rechaza_traversal(tmp_path):
    allowed = [tmp_path]
    fuera = tmp_path / ".." / "escape.txt"
    with pytest.raises(fsops.OutsideSandbox):
        fsops.resolve_within(allowed, str(fuera))


def test_resolve_within_rechaza_absoluta_fuera(tmp_path):
    allowed = [tmp_path]
    with pytest.raises(fsops.OutsideSandbox):
        fsops.resolve_within(allowed, "C:\\Windows\\system32\\x")
```

- [ ] **Step 2: Ejecutar el test para verque falla**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py -v`
Expected: FAIL — `ModuleNotFoundError: plugins.expedientes_xl` / `AttributeError: resolve_within`.

- [ ] **Step 3: Implementación mínima**

```python
# plugins/expedientes_xl/__init__.py
# (vacío — marca el paquete)
```

```python
# plugins/expedientes_xl/fsops.py
"""Operaciones de fichero genéricas, acotadas a allowedDirectories.

Sin dependencias de `mcp` ni de `core/`: lógica pura, testeable con pytest.
El saneado anti path-traversal replica el patrón de
`core/intake_manual.extract_zip` (re-implementado autocontenido).
"""
from __future__ import annotations

from pathlib import Path


class OutsideSandbox(Exception):
    """La ruta resuelta cae fuera de todos los allowedDirectories."""


class TooLarge(Exception):
    """El contenido supera el tope de tamaño permitido."""


def resolve_within(allowed_dirs: list[Path], target: str | Path) -> Path:
    """Resuelve `target` y exige que quede dentro de algún allowedDir.

    Rechaza explícitamente componentes "..", nulos, y rutas cuyo destino
    resuelto (símbolos y symlinks ya colapsados) no esté bajo un allowedDir.
    """
    raw = Path(target)
    if any(part in ("..", "") or "\x00" in part for part in raw.parts):
        raise OutsideSandbox(f"Ruta con componente no permitido: {target!r}")
    resolved = raw.resolve()
    for base in allowed_dirs:
        base_resolved = Path(base).resolve()
        try:
            resolved.relative_to(base_resolved)
            return resolved
        except ValueError:
            continue
    raise OutsideSandbox(f"Ruta fuera del sandbox: {target!r}")
```

- [ ] **Step 4: Ejecutar el test para ver que pasa**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/expedientes_xl/__init__.py plugins/expedientes_xl/fsops.py tests/test_expedientes_xl_fsops.py
git commit -m "feat(expedientes-xl): saneado resolve_within + scaffold del paquete"
```

---

## Task 2: `sha256_file` (hash server-side)

**Files:**
- Modify: `plugins/expedientes_xl/fsops.py`
- Test: `tests/test_expedientes_xl_fsops.py`

- [ ] **Step 1: Escribir el test que falla**

```python
import hashlib

def test_sha256_file_coincide_con_hashlib(tmp_path):
    f = tmp_path / "x.bin"
    data = b"contenido binario \x00\x01\x02" * 1000
    f.write_bytes(data)
    esperado = hashlib.sha256(data).hexdigest()
    assert fsops.sha256_file([tmp_path], str(f)) == esperado


def test_sha256_file_rechaza_fuera_de_sandbox(tmp_path):
    with pytest.raises(fsops.OutsideSandbox):
        fsops.sha256_file([tmp_path], "C:\\Windows\\notepad.exe")
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py::test_sha256_file_coincide_con_hashlib -v`
Expected: FAIL — `AttributeError: sha256_file`.

- [ ] **Step 3: Implementación mínima**

```python
# añadir a fsops.py
import hashlib

_CHUNK = 1024 * 1024  # 1 MiB


def sha256_file(allowed_dirs: list[Path], path: str | Path) -> str:
    """SHA-256 del fichero, calculado server-side. Devuelve solo el digest."""
    target = resolve_within(allowed_dirs, path)
    h = hashlib.sha256()
    with open(target, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()
```

- [ ] **Step 4: Ejecutar el test para ver que pasa**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py -k sha256 -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/expedientes_xl/fsops.py tests/test_expedientes_xl_fsops.py
git commit -m "feat(expedientes-xl): sha256_file server-side"
```

---

## Task 3: `copy_file` y `copy_tree`

**Files:**
- Modify: `plugins/expedientes_xl/fsops.py`
- Test: `tests/test_expedientes_xl_fsops.py`

- [ ] **Step 1: Escribir el test que falla**

```python
def test_copy_file_copia_no_destructivo(tmp_path):
    src = tmp_path / "orig.bin"
    src.write_bytes(b"\x00\x01datos")
    dst = tmp_path / "dest" / "copia.bin"
    out = fsops.copy_file([tmp_path], str(src), str(dst))
    assert out == dst.resolve()
    assert dst.read_bytes() == b"\x00\x01datos"
    assert src.exists()  # no destructivo


def test_copy_file_rechaza_destino_fuera(tmp_path):
    src = tmp_path / "orig.bin"
    src.write_bytes(b"x")
    with pytest.raises(fsops.OutsideSandbox):
        fsops.copy_file([tmp_path], str(src), str(tmp_path / ".." / "fuera.bin"))


def test_copy_tree_recursivo(tmp_path):
    src = tmp_path / "arbol"
    (src / "a").mkdir(parents=True)
    (src / "a" / "f.txt").write_text("hola", encoding="utf-8")
    dst = tmp_path / "copia_arbol"
    out = fsops.copy_tree([tmp_path], str(src), str(dst))
    assert out == dst.resolve()
    assert (dst / "a" / "f.txt").read_text(encoding="utf-8") == "hola"
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py -k "copy_file or copy_tree" -v`
Expected: FAIL — `AttributeError: copy_file`.

- [ ] **Step 3: Implementación mínima**

```python
# añadir a fsops.py
import shutil


def copy_file(allowed_dirs: list[Path], src: str | Path, dst: str | Path) -> Path:
    """Copia un fichero (no destructivo). src y dst dentro del sandbox."""
    src_p = resolve_within(allowed_dirs, src)
    dst_p = resolve_within(allowed_dirs, dst)
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_p, dst_p)
    return dst_p


def copy_tree(allowed_dirs: list[Path], src: str | Path, dst: str | Path) -> Path:
    """Copia recursiva de un árbol de directorios dentro del sandbox."""
    src_p = resolve_within(allowed_dirs, src)
    dst_p = resolve_within(allowed_dirs, dst)
    shutil.copytree(src_p, dst_p, dirs_exist_ok=True)
    return dst_p
```

- [ ] **Step 4: Ejecutar el test para ver que pasa**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py -k "copy_file or copy_tree" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/expedientes_xl/fsops.py tests/test_expedientes_xl_fsops.py
git commit -m "feat(expedientes-xl): copy_file + copy_tree"
```

---

## Task 4: `extract_archive` (zip/tar con saneado por miembro)

**Files:**
- Modify: `plugins/expedientes_xl/fsops.py`
- Test: `tests/test_expedientes_xl_fsops.py`

- [ ] **Step 1: Escribir el test que falla**

```python
import io
import zipfile


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_extract_archive_extrae_estructura(tmp_path):
    archive = tmp_path / "e.zip"
    archive.write_bytes(_zip_bytes({"a/f.txt": b"uno", "g.txt": b"dos"}))
    dest = tmp_path / "out"
    out = fsops.extract_archive([tmp_path], str(archive), str(dest))
    assert (dest / "a" / "f.txt").read_bytes() == b"uno"
    assert (dest / "g.txt").read_bytes() == b"dos"
    assert sorted(p.name for p in out) == ["f.txt", "g.txt"]


def test_extract_archive_descarta_miembro_traversal(tmp_path):
    archive = tmp_path / "mal.zip"
    archive.write_bytes(_zip_bytes({"../escape.txt": b"malo", "ok.txt": b"bien"}))
    dest = tmp_path / "out"
    out = fsops.extract_archive([tmp_path], str(archive), str(dest))
    assert (tmp_path / "escape.txt").exists() is False  # no escapó
    assert (dest / "ok.txt").read_bytes() == b"bien"
    assert [p.name for p in out] == ["ok.txt"]
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py -k extract_archive -v`
Expected: FAIL — `AttributeError: extract_archive`.

- [ ] **Step 3: Implementación mínima**

```python
# añadir a fsops.py
import tarfile
import zipfile


def _safe_member_dest(dest_dir: Path, member_name: str) -> Path | None:
    """Devuelve el destino saneado de un miembro, o None si debe descartarse.

    Descarta toda entrada con "..", componente absoluto o nulo; doble check
    de que el destino resuelto queda dentro de dest_dir (patrón extract_zip).
    """
    member_path = Path(member_name)
    if any(
        part in ("..", "") or "\x00" in part or Path(part).is_absolute()
        for part in member_path.parts
    ):
        return None
    dest = dest_dir / member_path
    try:
        dest.resolve().relative_to(dest_dir.resolve())
    except ValueError:
        return None
    return dest


def extract_archive(
    allowed_dirs: list[Path], archive: str | Path, dest_dir: str | Path
) -> list[Path]:
    """Descomprime .zip o .tar(.gz/.bz2) en dest_dir, ambos dentro del sandbox.

    Saneado anti path-traversal por miembro: las entradas peligrosas se
    descartan (no se intenta rescatarlas). Devuelve los ficheros extraídos.
    """
    archive_p = resolve_within(allowed_dirs, archive)
    dest_p = resolve_within(allowed_dirs, dest_dir)
    dest_p.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []

    if zipfile.is_zipfile(archive_p):
        with zipfile.ZipFile(archive_p) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                dest = _safe_member_dest(dest_p, member.filename)
                if dest is None:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(member))
                extracted.append(dest)
    elif tarfile.is_tarfile(archive_p):
        with tarfile.open(archive_p) as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                dest = _safe_member_dest(dest_p, member.name)
                if dest is None:
                    continue
                src = tf.extractfile(member)
                if src is None:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read())
                extracted.append(dest)
    else:
        raise ValueError(f"No es un archivo zip ni tar: {archive!r}")

    return sorted(extracted)
```

- [ ] **Step 4: Ejecutar el test para ver que pasa**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py -k extract_archive -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/expedientes_xl/fsops.py tests/test_expedientes_xl_fsops.py
git commit -m "feat(expedientes-xl): extract_archive zip/tar con saneado por miembro"
```

---

## Task 5: `write_base64` (binario con tope de tamaño)

**Files:**
- Modify: `plugins/expedientes_xl/fsops.py`
- Test: `tests/test_expedientes_xl_fsops.py`

- [ ] **Step 1: Escribir el test que falla**

```python
import base64


def test_write_base64_escribe_binario(tmp_path):
    data = b"\x89PNG\r\n\x1a\n binario"
    b64 = base64.b64encode(data).decode("ascii")
    dst = tmp_path / "img.png"
    n = fsops.write_base64([tmp_path], str(dst), b64, max_bytes=1000)
    assert n == len(data)
    assert dst.read_bytes() == data


def test_write_base64_rechaza_sobre_tope(tmp_path):
    data = b"x" * 200
    b64 = base64.b64encode(data).decode("ascii")
    with pytest.raises(fsops.TooLarge):
        fsops.write_base64([tmp_path], str(tmp_path / "big.bin"), b64, max_bytes=100)
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py -k write_base64 -v`
Expected: FAIL — `AttributeError: write_base64`.

- [ ] **Step 3: Implementación mínima**

```python
# añadir a fsops.py
import base64


def write_base64(
    allowed_dirs: list[Path], path: str | Path, content_b64: str, max_bytes: int
) -> int:
    """Escribe un binario desde base64, con tope DURO de tamaño.

    Comprueba el tamaño ANTES de escribir; si supera max_bytes lanza TooLarge.
    Devuelve el número de bytes escritos.
    """
    data = base64.b64decode(content_b64, validate=True)
    if len(data) > max_bytes:
        raise TooLarge(f"{len(data)} bytes supera el tope {max_bytes}")
    dst = resolve_within(allowed_dirs, path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return len(data)
```

- [ ] **Step 4: Ejecutar el test para ver que pasa**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py -k write_base64 -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/expedientes_xl/fsops.py tests/test_expedientes_xl_fsops.py
git commit -m "feat(expedientes-xl): write_base64 con tope de tamaño"
```

---

## Task 6: `append_text` y `delete_path`

**Files:**
- Modify: `plugins/expedientes_xl/fsops.py`
- Test: `tests/test_expedientes_xl_fsops.py`

- [ ] **Step 1: Escribir el test que falla**

```python
def test_append_text_crea_y_anexa(tmp_path):
    dst = tmp_path / "log.jsonl"
    fsops.append_text([tmp_path], str(dst), '{"a":1}\n')
    fsops.append_text([tmp_path], str(dst), '{"b":2}\n')
    assert dst.read_text(encoding="utf-8") == '{"a":1}\n{"b":2}\n'


def test_append_text_rechaza_fuera(tmp_path):
    with pytest.raises(fsops.OutsideSandbox):
        fsops.append_text([tmp_path], str(tmp_path / ".." / "x.txt"), "y")


def test_delete_path_borra_dentro(tmp_path):
    f = tmp_path / "borrame.txt"
    f.write_text("x", encoding="utf-8")
    fsops.delete_path([tmp_path], str(f))
    assert f.exists() is False


def test_delete_path_rechaza_fuera(tmp_path):
    with pytest.raises(fsops.OutsideSandbox):
        fsops.delete_path([tmp_path], "C:\\Windows\\system32")
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py -k "append_text or delete_path" -v`
Expected: FAIL — `AttributeError: append_text`.

- [ ] **Step 3: Implementación mínima**

```python
# añadir a fsops.py
def append_text(allowed_dirs: list[Path], path: str | Path, text: str) -> Path:
    """Anexa texto UTF-8 a un fichero (lo crea si falta). Para .jsonl."""
    dst = resolve_within(allowed_dirs, path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "a", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return dst


def delete_path(allowed_dirs: list[Path], path: str | Path) -> None:
    """Borra un fichero o árbol dentro del sandbox."""
    target = resolve_within(allowed_dirs, path)
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink(missing_ok=True)
```

- [ ] **Step 4: Ejecutar el test para ver que pasa**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py -k "append_text or delete_path" -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/expedientes_xl/fsops.py tests/test_expedientes_xl_fsops.py
git commit -m "feat(expedientes-xl): append_text + delete_path"
```

---

## Task 7: Wrapper MCP (`server.py`) con FastMCP

**Files:**
- Create: `plugins/expedientes_xl/server.py`
- Create: `plugins/expedientes_xl/requirements.txt`
- Test: `tests/test_expedientes_xl_server.py`

- [ ] **Step 1: Crear `requirements.txt` e instalar `mcp`**

```text
# plugins/expedientes_xl/requirements.txt
mcp>=1.0
```

Run: `python -m pip install -r plugins/expedientes_xl/requirements.txt`
Expected: instala `mcp` en el venv del repo.

- [ ] **Step 2: Escribir el test que falla**

El test no levanta el transporte stdio; comprueba que `build_server` registra las 7 tools con el SDK (la lógica ya está cubierta por los tests de `fsops`).

```python
# tests/test_expedientes_xl_server.py
import pytest

from plugins.expedientes_xl import server as srv


@pytest.mark.asyncio
async def test_server_registra_todas_las_tools(tmp_path):
    mcp = srv.build_server([tmp_path], max_b64_bytes=1000)
    tools = await mcp.list_tools()
    nombres = {t.name for t in tools}
    assert nombres == {
        "hash_path",
        "copy_path",
        "copy_dir",
        "extract_archive",
        "write_file_base64",
        "append_text",
        "delete_path",
    }
```

- [ ] **Step 3: Ejecutar el test para ver que falla**

Run: `python -m pytest tests/test_expedientes_xl_server.py -v`
Expected: FAIL — `AttributeError: build_server` (o ImportError si falta `pytest-asyncio`; si falta, instalarlo: `python -m pip install pytest-asyncio` y añadirlo al requirements del plugin).

- [ ] **Step 4: Implementación mínima**

```python
# plugins/expedientes_xl/server.py
"""Servidor MCP stdio `expedientes-xl` (wrapper fino sobre fsops).

Uso: python server.py <allowed_dir> [<allowed_dir> ...] [--max-b64-bytes N]
Cada tool delega en fsops; toda ruta se valida contra allowed_dirs.
"""
from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

try:  # importado como paquete (pytest: plugins.expedientes_xl.server)
    from . import fsops
except ImportError:  # ejecutado como script suelto (python server.py): su dir está en sys.path[0]
    import fsops

DEFAULT_MAX_B64 = 8 * 1024 * 1024  # 8 MiB


def build_server(allowed_dirs: list[Path], max_b64_bytes: int = DEFAULT_MAX_B64) -> FastMCP:
    mcp = FastMCP("expedientes-xl")

    @mcp.tool()
    def hash_path(path: str) -> str:
        """SHA-256 (hex) de un fichero, calculado server-side."""
        return fsops.sha256_file(allowed_dirs, path)

    @mcp.tool()
    def copy_path(src: str, dst: str) -> str:
        """Copia un fichero (no destructivo). Devuelve la ruta destino."""
        return str(fsops.copy_file(allowed_dirs, src, dst))

    @mcp.tool()
    def copy_dir(src: str, dst: str) -> str:
        """Copia recursiva de un árbol. Devuelve la ruta destino."""
        return str(fsops.copy_tree(allowed_dirs, src, dst))

    @mcp.tool()
    def extract_archive(archive_path: str, dest_dir: str) -> list[str]:
        """Descomprime zip/tar en dest_dir. Devuelve los ficheros extraídos."""
        return [str(p) for p in fsops.extract_archive(allowed_dirs, archive_path, dest_dir)]

    @mcp.tool()
    def write_file_base64(path: str, content_b64: str) -> int:
        """Escribe un binario desde base64 (tope configurado). Bytes escritos."""
        return fsops.write_base64(allowed_dirs, path, content_b64, max_b64_bytes)

    @mcp.tool()
    def append_text(path: str, text: str) -> str:
        """Anexa texto UTF-8 a un fichero (lo crea si falta)."""
        return str(fsops.append_text(allowed_dirs, path, text))

    @mcp.tool()
    def delete_path(path: str) -> str:
        """Borra fichero o árbol dentro del sandbox."""
        fsops.delete_path(allowed_dirs, path)
        return path

    return mcp


def _parse_argv(argv: list[str]) -> tuple[list[Path], int]:
    dirs: list[Path] = []
    max_b64 = DEFAULT_MAX_B64
    it = iter(argv)
    for a in it:
        if a == "--max-b64-bytes":
            max_b64 = int(next(it))
        else:
            dirs.append(Path(a))
    if not dirs:
        raise SystemExit("Uso: server.py <allowed_dir> [...] [--max-b64-bytes N]")
    return dirs, max_b64


def main() -> None:
    dirs, max_b64 = _parse_argv(sys.argv[1:])
    build_server(dirs, max_b64).run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Ejecutar el test para ver que pasa**

Run: `python -m pytest tests/test_expedientes_xl_server.py -v`
Expected: PASS (1 test).

- [ ] **Step 6: Commit**

```bash
git add plugins/expedientes_xl/server.py plugins/expedientes_xl/requirements.txt tests/test_expedientes_xl_server.py
git commit -m "feat(expedientes-xl): server FastMCP con las 7 tools"
```

---

## Task 8: Verificación end-to-end + README de registro

**Files:**
- Create: `plugins/expedientes_xl/README.md`

- [ ] **Step 1: Registrar el server en Claude Code (verificación manual real)**

Run:
```powershell
claude mcp add expedientes-xl -- python "C:\Users\tnm33\Dev\FeesDefender\plugins\expedientes_xl\server.py" "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL"
claude mcp list
```
Expected: `expedientes-xl … √ Connected`.

- [ ] **Step 2: Smoke test de una operación real (tras reiniciar la sesión)**

En una sesión nueva de Claude Code, pedir: copiar un fichero pequeño de prueba a `_ingest/` y volver a copiarlo dentro del Drive con `copy_path`; comprobar que aparece. Confirmar que `hash_path` devuelve un digest de 64 chars.
Expected: la operación ocurre server-side, sin error, en segundos.

- [ ] **Step 3: Escribir el README de registro**

```markdown
# expedientes-xl

Servidor MCP stdio genérico de operaciones de fichero acotadas a un sandbox de
directorios. Sin lógica de FeesDefender.

## Requisitos
- Python 3 + `pip install -r requirements.txt` (instala `mcp`).
- El directorio permitido montado en disco (p. ej. el Drive del despacho).

## Registro

### Claude Code
```
claude mcp add expedientes-xl -- python <ruta>/expedientes_xl/server.py "<allowed_dir>"
```

### Cowork (Claude Desktop, vía claude_desktop_config.json)
```json
{
  "mcpServers": {
    "expedientes-xl": {
      "command": "python",
      "args": ["<ruta>/expedientes_xl/server.py", "<allowed_dir>"]
    }
  }
}
```

Opcional: `--max-b64-bytes N` para el tope de `write_file_base64` (def. 8 MiB).

## Tools
`hash_path` · `copy_path` · `copy_dir` · `extract_archive` · `write_file_base64` ·
`append_text` · `delete_path`. Toda ruta se valida contra los allowedDirectories.
```

- [ ] **Step 4: Suite completa verde**

Run: `python -m pytest tests/test_expedientes_xl_fsops.py tests/test_expedientes_xl_server.py -v`
Expected: PASS (todos). Luego `python -m pytest -q --tb=no` para confirmar que no se rompió nada del repo.

- [ ] **Step 5: Commit**

```bash
git add plugins/expedientes_xl/README.md
git commit -m "docs(expedientes-xl): README de registro + verificación e2e"
```

---

## Notas de cierre

- **No se toca `core/`** en este plan. El conector es autocontenido.
- **Siguiente plan (2/3):** skill de intake + trazabilidad (consume `hash_path`/`extract_archive`/`append_text`; espeja el esquema de `core/intake_manifest.py`+`intake_log.py` con gate anti-drift).
- **Plan (3/3):** empaquetado del plugin FeesDefender (manifest, `.mcp.json` con `${CLAUDE_PLUGIN_ROOT}`, marketplace en repo privado, entrada `claude_desktop_config.json` para Cowork).
- **Limpieza:** al terminar, quitar el server de prueba si se quiere (`claude mcp remove expedientes-xl`) o dejarlo como el connector de trabajo.
