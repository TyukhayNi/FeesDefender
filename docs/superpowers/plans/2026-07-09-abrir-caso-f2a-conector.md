# `abrir-caso` F2a — Primitivas del conector `expedientes-xl` (`hash_tree` + `strip_top_level`)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development / executing-plans. Steps use `- [ ]`.

**Goal:** Añadir al conector `expedientes-xl` las dos primitivas que el frente Cowork de `abrir-caso` necesita (spec §7): `hash_tree` (hash recursivo server-side en 1 llamada) y el flag `strip_top_level` en `extract_archive` (quitar el wrapper del export).

**Architecture:** Lógica pura en `plugins/expedientes_xl/fsops.py` (sin deps de `mcp`/`core`) + wrapper de tool en `plugins/expedientes_xl/server.py`. Tests en `tests/test_expedientes_xl_fsops.py` (lógica) y `tests/test_expedientes_xl_server.py` (tools). SSOT del conector = `plugins/expedientes_xl/`; hay una copia empaquetada en `dist/plugin/feesdefender/expedientes_xl/` que se regenera al final.

**Tech Stack:** Python (`hashlib`, `pathlib`, `zipfile`, `tarfile`), `pytest`, FastMCP.

**Spec:** `docs/superpowers/specs/2026-07-09-abrir-caso-design.md` §7.

---

## File Structure
- **Modify** `plugins/expedientes_xl/fsops.py` — añadir `hash_tree()` y `_common_top_level()`; añadir parámetro `strip_top_level` a `extract_archive()`.
- **Modify** `plugins/expedientes_xl/server.py` — añadir tool `hash_tree`; añadir param `strip_top_level` al tool `extract_archive`.
- **Modify** `tests/test_expedientes_xl_fsops.py` — tests de `hash_tree` y `strip_top_level`.
- **Modify** `tests/test_expedientes_xl_server.py` — tests de las tools nuevas (seguir el patrón del fichero).
- **Regenerar** la copia `dist/plugin/feesdefender/expedientes_xl/` al final.

---

### Task 1: `hash_tree` (fsops + server + tests)

**Files:** Modify `plugins/expedientes_xl/fsops.py`, `plugins/expedientes_xl/server.py`, `tests/test_expedientes_xl_fsops.py`, `tests/test_expedientes_xl_server.py`.

- [ ] **Step 1: Write the failing test (fsops)**

Añadir a `tests/test_expedientes_xl_fsops.py`:

```python
def test_hash_tree_mapea_relpath_posix_a_sha(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_bytes(b"hola")
    (tmp_path / "sub" / "b.txt").write_bytes(b"mundo")
    out = fsops.hash_tree([tmp_path], str(tmp_path))
    assert out == {
        "a.txt": hashlib.sha256(b"hola").hexdigest(),
        "sub/b.txt": hashlib.sha256(b"mundo").hexdigest(),
    }


def test_hash_tree_salta_directorios_y_root_inexistente(tmp_path):
    vacio = tmp_path / "vacia"
    vacio.mkdir()
    assert fsops.hash_tree([tmp_path], str(vacio)) == {}


def test_hash_tree_rechaza_fuera_de_sandbox(tmp_path):
    with pytest.raises(fsops.OutsideSandbox):
        fsops.hash_tree([tmp_path], "C:\\Windows")
```

- [ ] **Step 2: Run → fail**

Run: `"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest tests/test_expedientes_xl_fsops.py -k hash_tree -v` (cwd = worktree)
Expected: FAIL `AttributeError: module 'plugins.expedientes_xl.fsops' has no attribute 'hash_tree'`.

- [ ] **Step 3: Implement in `fsops.py`** (añadir tras `sha256_file`)

```python
def hash_tree(allowed_dirs: list[Path], root: str | Path) -> dict[str, str]:
    """SHA-256 recursivo server-side de todos los ficheros bajo `root`.

    Devuelve {relpath_posix: sha256hex}, relpath relativo a `root`. Determinista
    (el dict se construye en orden ordenado). Salta directorios y **symlinks**
    (defensa: un symlink podría apuntar fuera del sandbox). Si `root` no existe
    o no es directorio, devuelve {}.
    """
    root_p = resolve_within(allowed_dirs, root)
    out: dict[str, str] = {}
    if not root_p.is_dir():
        return out
    for p in sorted(root_p.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(_CHUNK), b""):
                h.update(chunk)
        out[p.relative_to(root_p).as_posix()] = h.hexdigest()
    return out
```

- [ ] **Step 4: Run → pass** (same command). Expected: PASS.

- [ ] **Step 5: Add the server tool** in `server.py` (dentro de `build_server`, tras `hash_path`):

```python
    @mcp.tool()
    def hash_tree(root: str) -> dict[str, str]:
        """SHA-256 (hex) recursivo de un árbol. {relpath_posix: sha256}."""
        return fsops.hash_tree(allowed_dirs, root)
```

- [ ] **Step 6: Server test.** Read `tests/test_expedientes_xl_server.py` and follow its existing pattern (how it builds the server and invokes a tool) to add a test that `hash_tree` returns the expected dict for a small tree. Run: `... -m pytest tests/test_expedientes_xl_server.py -k hash_tree -v` → PASS.

- [ ] **Step 7: Commit**

```bash
git add plugins/expedientes_xl/fsops.py plugins/expedientes_xl/server.py tests/test_expedientes_xl_fsops.py tests/test_expedientes_xl_server.py
git commit -m "feat(expedientes-xl): hash_tree — SHA-256 recursivo server-side"
```

---

### Task 2: `strip_top_level` en `extract_archive` (fsops + server + tests)

**Files:** Modify `plugins/expedientes_xl/fsops.py`, `plugins/expedientes_xl/server.py`, `tests/test_expedientes_xl_fsops.py`, `tests/test_expedientes_xl_server.py`.

- [ ] **Step 1: Write the failing tests (fsops)**

Añadir a `tests/test_expedientes_xl_fsops.py` (usa `zipfile` ya importado):

```python
def _make_zip(path, names_to_bytes):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in names_to_bytes.items():
            zf.writestr(name, data)


def test_extract_strip_top_level_quita_wrapper(tmp_path):
    z = tmp_path / "export.zip"
    _make_zip(z, {"Wrapper/ACTIVACION/hoja.pdf": b"A", "Wrapper/oferta.pdf": b"B"})
    dest = tmp_path / "out"
    extracted = fsops.extract_archive([tmp_path], str(z), str(dest), strip_top_level=True)
    rels = sorted(p.relative_to(dest.resolve()).as_posix() for p in extracted)
    assert rels == ["ACTIVACION/hoja.pdf", "oferta.pdf"]


def test_extract_sin_strip_conserva_wrapper(tmp_path):
    z = tmp_path / "export.zip"
    _make_zip(z, {"Wrapper/ACTIVACION/hoja.pdf": b"A"})
    dest = tmp_path / "out"
    extracted = fsops.extract_archive([tmp_path], str(z), str(dest))
    rels = [p.relative_to(dest.resolve()).as_posix() for p in extracted]
    assert rels == ["Wrapper/ACTIVACION/hoja.pdf"]


def test_extract_strip_no_actua_con_multiples_raices(tmp_path):
    z = tmp_path / "export.zip"
    _make_zip(z, {"A/x.pdf": b"1", "B/y.pdf": b"2"})
    dest = tmp_path / "out"
    extracted = fsops.extract_archive([tmp_path], str(z), str(dest), strip_top_level=True)
    rels = sorted(p.relative_to(dest.resolve()).as_posix() for p in extracted)
    assert rels == ["A/x.pdf", "B/y.pdf"]  # sin único wrapper → no se toca


def test_extract_strip_no_actua_con_fichero_en_raiz(tmp_path):
    z = tmp_path / "export.zip"
    _make_zip(z, {"suelto.pdf": b"1", "Wrapper/x.pdf": b"2"})
    dest = tmp_path / "out"
    extracted = fsops.extract_archive([tmp_path], str(z), str(dest), strip_top_level=True)
    rels = sorted(p.relative_to(dest.resolve()).as_posix() for p in extracted)
    assert rels == ["Wrapper/x.pdf", "suelto.pdf"]  # hay fichero en raíz → no hay wrapper único
```

- [ ] **Step 2: Run → fail**

Run: `... -m pytest tests/test_expedientes_xl_fsops.py -k strip -v`
Expected: FAIL `TypeError: extract_archive() got an unexpected keyword argument 'strip_top_level'`.

- [ ] **Step 3: Implement in `fsops.py`**

Añadir el helper (antes de `extract_archive`):

```python
def _common_top_level(names: list[str]) -> str | None:
    """Único directorio de primer nivel común a TODOS los nombres, o None.

    Devuelve None si algún miembro está en la raíz del archivo (sin carpeta) o
    si hay más de un directorio de primer nivel: en esos casos no hay un wrapper
    inequívoco que quitar.
    """
    tops: set[str] = set()
    for n in names:
        parts = Path(n).parts
        if len(parts) < 2:
            return None
        tops.add(parts[0])
    return tops.pop() if len(tops) == 1 else None
```

Modificar la firma y el cuerpo de `extract_archive` para (a) aceptar `strip_top_level: bool = False`, (b) recopilar los nombres de miembros-fichero antes de extraer, (c) calcular el prefijo a quitar, (d) al construir el destino de cada miembro, quitar el primer componente si procede. Reescribir así:

```python
def extract_archive(
    allowed_dirs: list[Path],
    archive: str | Path,
    dest_dir: str | Path,
    max_total_bytes: int = DEFAULT_MAX_EXTRACT_BYTES,
    strip_top_level: bool = False,
) -> list[Path]:
    """Descomprime .zip o .tar(.gz/.bz2) en dest_dir, ambos dentro del sandbox.

    Saneado anti path-traversal por miembro; presupuesto global `max_total_bytes`
    (anti zip-bomb). Si `strip_top_level` y el archivo tiene un ÚNICO directorio de
    primer nivel que envuelve a todos los ficheros, se quita ese wrapper de las
    rutas extraídas. Devuelve los ficheros extraídos (ordenados).
    """
    archive_p = resolve_within(allowed_dirs, archive)
    dest_p = resolve_within(allowed_dirs, dest_dir)
    dest_p.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    budget = [max_total_bytes]

    def _dest_name(name: str, prefix: str | None) -> str | None:
        if prefix is None:
            return name
        rel = Path(name).parts[1:]  # quitar el wrapper
        return str(Path(*rel)) if rel else None

    if zipfile.is_zipfile(archive_p):
        with zipfile.ZipFile(archive_p) as zf:
            file_members = [m for m in zf.infolist() if not m.is_dir()]
            prefix = _common_top_level([m.filename for m in file_members]) if strip_top_level else None
            for member in file_members:
                name = _dest_name(member.filename, prefix)
                if name is None:
                    continue
                dest = _safe_member_dest(dest_p, name)
                if dest is None:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src:
                    _stream_member(src, dest, budget)
                extracted.append(dest)
    elif tarfile.is_tarfile(archive_p):
        with tarfile.open(archive_p) as tf:
            file_members = [m for m in tf.getmembers() if m.isfile()]
            prefix = _common_top_level([m.name for m in file_members]) if strip_top_level else None
            for member in file_members:
                name = _dest_name(member.name, prefix)
                if name is None:
                    continue
                dest = _safe_member_dest(dest_p, name)
                if dest is None:
                    continue
                src = tf.extractfile(member)
                if src is None:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                _stream_member(src, dest, budget)
                extracted.append(dest)
    else:
        raise ValueError(f"No es un archivo zip ni tar: {archive!r}")

    return sorted(extracted)
```

- [ ] **Step 4: Run → pass** (`-k strip` and the whole fsops file). Expected: PASS, and the pre-existing `extract_archive` tests still pass (no behaviour change when `strip_top_level=False`).

- [ ] **Step 5: Server tool param.** In `server.py`, change the `extract_archive` tool to accept and forward the flag:

```python
    @mcp.tool()
    def extract_archive(archive_path: str, dest_dir: str, strip_top_level: bool = False) -> list[str]:
        """Descomprime zip/tar en dest_dir. `strip_top_level` quita el wrapper único. Devuelve los ficheros."""
        return [str(p) for p in fsops.extract_archive(
            allowed_dirs, archive_path, dest_dir, max_extract_bytes, strip_top_level=strip_top_level)]
```

- [ ] **Step 6: Server test.** Following the file's pattern, add a test that the `extract_archive` tool with `strip_top_level=True` drops the wrapper. Run `... -m pytest tests/test_expedientes_xl_server.py -v` → PASS.

- [ ] **Step 7: Commit**

```bash
git add plugins/expedientes_xl/fsops.py plugins/expedientes_xl/server.py tests/test_expedientes_xl_fsops.py tests/test_expedientes_xl_server.py
git commit -m "feat(expedientes-xl): strip_top_level en extract_archive (quita el wrapper del export)"
```

---

### Task 3: Regenerar la copia empaquetada + suite verde

**Files:** posible `dist/plugin/feesdefender/expedientes_xl/*` (regenerado, no editado a mano).

- [ ] **Step 1: Localizar el empaquetador.** Buscar el script que produce `dist/plugin/feesdefender/`:
  `grep -ril "expedientes_xl\|dist/plugin" scripts/` y revisar `scripts/package_plugin.py` si existe.

- [ ] **Step 2: Regenerar.** Si hay script de empaquetado, ejecutarlo con el venv para que `dist/plugin/feesdefender/expedientes_xl/{fsops,server}.py` reflejen la SSOT. Si NO hay script y la copia es un espejo manual trackeado, copiar `fsops.py` y `server.py` de `plugins/expedientes_xl/` a `dist/plugin/feesdefender/expedientes_xl/`. Si `dist/` está en `.gitignore` (no trackeado), NO hacer nada (se regenera en su momento) y anotarlo en el reporte.

- [ ] **Step 3: Suite completa**

Run: `"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest tests/test_expedientes_xl_fsops.py tests/test_expedientes_xl_server.py -v` → todos verde.
Run: `"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q --tb=short` → verde (mismos pre-existentes conocidos, cero regresiones nuevas).

- [ ] **Step 4: Commit (si la regeneración cambió `dist/`)**

```bash
git add -A
git commit -m "chore(expedientes-xl): regenerar copia empaquetada con hash_tree/strip_top_level"
```

---

## Self-Review
- **Cobertura spec §7:** `hash_tree` (Task 1) ✓; `strip_top_level` (Task 2) ✓. `copy_dir` ya existía (no se toca).
- **Placeholders:** ninguno; todo el código está escrito. El único paso condicional (Task 3) es por desconocer si `dist/` se trackea — resuelto con instrucción explícita de las 3 ramas posibles.
- **No-regresión:** `strip_top_level` es opcional con default `False` → `extract_archive` mantiene su conducta actual; los tests pre-existentes deben seguir verdes (verificar en Task 2 Step 4).
- **Seguridad:** `hash_tree` salta symlinks (no sigue fuera del sandbox) y resuelve `root` dentro del sandbox; `_dest_name` sigue pasando por `_safe_member_dest` (el saneado anti-traversal se conserva tras quitar el wrapper).
- **Fuera de F2a (correcto):** la skill Cowork `abrir-caso` es F2b (siguiente plan).
