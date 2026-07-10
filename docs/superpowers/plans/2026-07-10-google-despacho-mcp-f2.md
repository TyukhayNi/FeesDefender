# google-despacho MCP — F2 (escritura CRUD + permisos + navegación) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir a `google-despacho` la escritura de Drive (CRUD de ficheros y carpetas, permisos con guardarraíl de compartición externa) y la navegación por carpetas, manteniendo el principio "bytes masivos nunca por el modelo" y la separación lógica-pura/wrapper de la F1.

**Architecture:** Toda la lógica va en `drive_ops.py` como funciones puras que reciben un `service` de googleapiclient ya construido (testeable con `FakeService` inyectado). `server.py` registra una tool FastMCP por operación, resuelve `account`→`service` y confina rutas locales (DL-root para descarga, nuevo UPLOAD-root para subida). El scope OAuth sube de `drive.readonly` a `drive` completo (edición consciente de `google_auth.SCOPES` + reautorización manual de las 2 cuentas). El intake de una sola orden (`import_drive_folder`) NO entra: es F3.

**Tech Stack:** Python 3, `mcp.server.fastmcp.FastMCP`, `googleapiclient` (Drive v3), `pytest`. Molde: la F1 ya mergeada en `plugins/google_despacho_mcp/`.

**Spec:** `docs/superpowers/specs/2026-07-08-google-despacho-mcp-design.md` §13.

**Convenciones del repo que aplican:**
- Comando de test: `python -m pytest -q --tb=no <ruta>` desde `C:\Users\tnm33\Dev\FeesDefender`.
- `main` protegida: trabajo en rama `feat/google-despacho-mcp-f2` + PR con check `leak-scan`.
- UTF-8 sin BOM. Commits desde PowerShell/Bash del repo.
- Todo cambio en código → test en `tests/`.

**Ficheros que se tocan:**
- Modificar: `plugins/google_despacho_mcp/google_auth.py` (scope).
- Modificar: `plugins/google_despacho_mcp/drive_ops.py` (funciones puras nuevas).
- Modificar: `plugins/google_despacho_mcp/server.py` (tools nuevas + `_resolve_upload`).
- Modificar: `plugins/google_despacho_mcp/google_cli.py` (mensaje de scope).
- Modificar: `plugins/google_despacho_mcp/README.md` (tools F2).
- Crear/ampliar tests: `tests/test_google_despacho_drive_ops_write.py` (nuevo, lógica de escritura), `tests/test_google_despacho_server.py` (ampliar: UPLOAD-root, guardarraíl, exclusividad text/local_path), `tests/test_google_despacho_auth.py` (ampliar: scope).

**Nota sobre el `FakeService`** (`tests/google_despacho_fakes.py`): su `__getattr__` ya acepta cualquier método (`create`, `update`, `copy`, `delete`, `create` de `permissions`, …) devolviendo la respuesta enlatada por método y registrando `(método, kwargs)`. NO hay que tocarlo. Para subidas, `drive_ops` construye un `MediaInMemoryUpload`/`MediaFileUpload` real (import perezoso) y lo pasa como `media_body`; el fake solo lo registra.

---

## Task 1: Subir el scope OAuth a `drive` completo

**Files:**
- Modify: `plugins/google_despacho_mcp/google_auth.py:26`
- Modify: `plugins/google_despacho_mcp/google_cli.py:21`
- Test: `tests/test_google_despacho_auth.py`

- [ ] **Step 1: Escribir el test que fija el scope F2**

Añadir a `tests/test_google_despacho_auth.py`:

```python
def test_scope_es_drive_completo_f2():
    from plugins.google_despacho_mcp import google_auth
    assert google_auth.SCOPES == ["https://www.googleapis.com/auth/drive"]
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_auth.py::test_scope_es_drive_completo_f2 -q`
Expected: FAIL (`SCOPES` sigue en `drive.readonly`).

- [ ] **Step 3: Cambiar el scope**

En `plugins/google_despacho_mcp/google_auth.py`, reemplazar el bloque del scope:

```python
# Alcance F2: Drive completo (lectura + escritura + permisos). `drive` subsume
# `drive.readonly`, así que las tools de lectura de F1 siguen funcionando. Se fija
# aquí y NO se parametriza: ampliarlo exige edición consciente + reautorización de
# cada cuenta. `drive.file` NO sirve (solo ficheros creados por la app; F2 toca
# expedientes existentes).
SCOPES = ["https://www.googleapis.com/auth/drive"]
```

Y actualizar el docstring del módulo (líneas 3-5) para que diga "SCOPE F2: drive (lectura+escritura)" en vez de "drive.readonly. SOLO LECTURA".

- [ ] **Step 4: Actualizar el mensaje del CLI**

En `plugins/google_despacho_mcp/google_cli.py`, `cmd_add`, cambiar el texto:

```python
    print("Se abrirá el navegador para autenticar la cuenta "
          "(Drive: lectura + ESCRITURA)...")
```

- [ ] **Step 5: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_auth.py -q`
Expected: PASS (todos).

- [ ] **Step 6: Commit**

```bash
git add plugins/google_despacho_mcp/google_auth.py plugins/google_despacho_mcp/google_cli.py tests/test_google_despacho_auth.py
git commit -m "feat(google-despacho): F2 sube scope OAuth a drive completo"
```

- [ ] **Step 7 (MANUAL, fuera del código): reautorizar las 2 cuentas**

Tras mergear, ejecutar UNA vez por cuenta (abre navegador; el token viejo de `drive.readonly` no basta para escribir):

```
python plugins/google_despacho_mcp/google_cli.py add   # cuenta TL
python plugins/google_despacho_mcp/google_cli.py add   # cuenta EV
```

Anotar en el PR que este paso es requisito operativo antes de usar las tools de escritura.

---

## Task 2: UPLOAD-root — confinamiento de rutas de subida en el server

**Files:**
- Modify: `plugins/google_despacho_mcp/server.py` (añadir `_resolve_upload` junto a `_resolve_dest`)
- Test: `tests/test_google_despacho_server.py`

El server ya tiene `_resolve_dest` (DL-root, para descargas). La subida necesita el simétrico: `_resolve_upload`, confinado por `GOOGLE_DESPACHO_UPLOAD_ROOT`, con el mismo saneado `realpath` anti-symlink, y además exige que el fichero exista.

- [ ] **Step 1: Escribir los tests de `_resolve_upload`**

Añadir a `tests/test_google_despacho_server.py` (mirar imports existentes; el módulo ya importa `server`):

```python
def test_resolve_upload_dentro_de_root(tmp_path, monkeypatch):
    from plugins.google_despacho_mcp import server
    root = tmp_path / "up"
    root.mkdir()
    f = root / "doc.pdf"
    f.write_bytes(b"x")
    monkeypatch.setenv("GOOGLE_DESPACHO_UPLOAD_ROOT", str(root))
    out = server._resolve_upload(str(f))
    assert out == os.path.realpath(str(f))


def test_resolve_upload_fuera_de_root_rechaza(tmp_path, monkeypatch):
    from plugins.google_despacho_mcp import server
    root = tmp_path / "up"
    root.mkdir()
    fuera = tmp_path / "otro.pdf"
    fuera.write_bytes(b"x")
    monkeypatch.setenv("GOOGLE_DESPACHO_UPLOAD_ROOT", str(root))
    with pytest.raises(ValueError):
        server._resolve_upload(str(fuera))


def test_resolve_upload_fichero_inexistente_rechaza(tmp_path, monkeypatch):
    from plugins.google_despacho_mcp import server
    monkeypatch.delenv("GOOGLE_DESPACHO_UPLOAD_ROOT", raising=False)
    with pytest.raises(FileNotFoundError):
        server._resolve_upload(str(tmp_path / "no_existe.pdf"))
```

Asegurar que el fichero de test tiene al principio `import os` y `import pytest` (ya suele estar; añadir `import os` si falta).

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_server.py -k resolve_upload -q`
Expected: FAIL (`_resolve_upload` no existe).

- [ ] **Step 3: Implementar `_resolve_upload`**

En `plugins/google_despacho_mcp/server.py`, justo después de `_resolve_dest` (línea ~60):

```python
def _resolve_upload(local_path: str) -> str:
    """Resuelve y valida la ruta de ORIGEN de una subida. Si
    GOOGLE_DESPACHO_UPLOAD_ROOT está definida, el origen debe quedar dentro de esa
    raíz (realpath contra symlink-escape). El fichero debe existir."""
    src = os.path.realpath(os.path.expanduser(local_path))
    if not os.path.isfile(src):
        raise FileNotFoundError(f"No existe el fichero a subir: {src}")
    root = os.environ.get("GOOGLE_DESPACHO_UPLOAD_ROOT")
    if root:
        root_abs = os.path.realpath(os.path.expanduser(root))
        try:
            inside = os.path.commonpath([root_abs, src]) == root_abs
        except ValueError:
            inside = False  # unidades distintas en Windows
        if not inside:
            raise ValueError(f"Origen fuera de GOOGLE_DESPACHO_UPLOAD_ROOT ({root_abs}): {src}")
    return src
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_server.py -k resolve_upload -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/google_despacho_mcp/server.py tests/test_google_despacho_server.py
git commit -m "feat(google-despacho): F2 _resolve_upload (UPLOAD-root)"
```

---

## Task 3: `create_file` (texto) y `upload_file` (ruta local)

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py`
- Modify: `plugins/google_despacho_mcp/server.py`
- Test: `tests/test_google_despacho_drive_ops_write.py` (crear)

Ambas crean un fichero nuevo y devuelven `{id, name, mime_type, sha256, web_view_link}`. `sha256` se calcula sobre los bytes que SUBIMOS (forense: hasheamos lo que enviamos, no lo que Drive reporte después). `create_file` es para texto corto del modelo; `upload_file` para bytes desde disco.

- [ ] **Step 1: Escribir el test (fichero nuevo)**

Crear `tests/test_google_despacho_drive_ops_write.py`:

```python
"""Tests de las operaciones de ESCRITURA de drive_ops con FakeService inyectado."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # para google_despacho_fakes
from google_despacho_fakes import FakeService  # noqa: E402

from plugins.google_despacho_mcp import drive_ops  # noqa: E402


def test_create_file_texto_devuelve_id_y_hash():
    svc = FakeService(files={"create": {
        "id": "n1", "name": "log.jsonl", "mimeType": "text/plain",
        "webViewLink": "https://drive/n1",
    }})
    out = drive_ops.create_file(svc, name="log.jsonl", parent_id="P1", text="hola\n")
    assert out["id"] == "n1"
    assert out["web_view_link"] == "https://drive/n1"
    assert out["sha256"] == hashlib.sha256("hola\n".encode("utf-8")).hexdigest()
    _, kw = svc.recorded("files")[0]
    assert kw["body"]["name"] == "log.jsonl"
    assert kw["body"]["parents"] == ["P1"]
    assert kw["supportsAllDrives"] is True
    assert "webViewLink" in kw["fields"]


def test_create_file_texto_supera_tope():
    svc = FakeService(files={"create": {"id": "n1"}})
    with pytest.raises(ValueError):
        drive_ops.create_file(svc, name="x", parent_id="P1", text="x" * 20,
                              max_text_bytes=10)


def test_upload_file_hashea_los_bytes_del_disco(tmp_path):
    data = b"%PDF-1.4 binario"
    src = tmp_path / "doc.pdf"
    src.write_bytes(data)
    svc = FakeService(files={"create": {
        "id": "u1", "name": "doc.pdf", "mimeType": "application/pdf",
        "webViewLink": "https://drive/u1",
    }})
    out = drive_ops.upload_file(svc, local_path=str(src), parent_id="P1")
    assert out["id"] == "u1"
    assert out["sha256"] == hashlib.sha256(data).hexdigest()
    _, kw = svc.recorded("files")[0]
    assert kw["body"]["name"] == "doc.pdf"          # nombre por defecto = basename
    assert kw["body"]["parents"] == ["P1"]
    assert "media_body" in kw
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -q`
Expected: FAIL (`create_file`/`upload_file` no existen).

- [ ] **Step 3: Implementar en `drive_ops.py`**

Añadir al final de `plugins/google_despacho_mcp/drive_ops.py` (y añadir arriba, junto a los otros, la constante de campos de creación):

```python
import mimetypes  # arriba del fichero, junto a los imports existentes

CREATE_FIELDS = "id, name, mimeType, webViewLink, parents"


def _media_from_bytes(data: bytes, mime_type: str):
    """MediaInMemoryUpload real (import perezoso, como el resto de Google)."""
    from googleapiclient.http import MediaInMemoryUpload
    return MediaInMemoryUpload(data, mimetype=mime_type, resumable=False)


def _media_from_path(local_path: str, mime_type: str):
    from googleapiclient.http import MediaFileUpload
    return MediaFileUpload(local_path, mimetype=mime_type, resumable=True)


def create_file(service, *, name: str, parent_id: str, text: str,
                mime_type: str = "text/plain",
                max_text_bytes: int = 1_000_000) -> dict:
    """Crea un fichero de TEXTO (contenido generado por el modelo). Tope pequeño
    (`max_text_bytes`) para forzar que los bytes de verdad vayan por upload_file."""
    data = text.encode("utf-8")
    if max_text_bytes and len(data) > max_text_bytes:
        raise ValueError(f"{len(data)} bytes supera max_text_bytes ({max_text_bytes}); "
                         f"usa upload_file para ficheros grandes.")
    body = {"name": name, "parents": [parent_id]}
    created = service.files().create(
        body=body, media_body=_media_from_bytes(data, mime_type),
        fields=CREATE_FIELDS, supportsAllDrives=True,
    ).execute()
    return {
        "id": created.get("id"), "name": created.get("name"),
        "mime_type": created.get("mimeType"),
        "web_view_link": created.get("webViewLink"),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def upload_file(service, *, local_path: str, parent_id: str,
                name: str | None = None, mime_type: str | None = None) -> dict:
    """Sube un fichero desde disco local (la ruta ya la saneó el server con
    UPLOAD-root). sha256 sobre los bytes del disco."""
    p = Path(local_path)
    fname = name or p.name
    mtype = mime_type or (mimetypes.guess_type(fname)[0] or "application/octet-stream")
    data = p.read_bytes()
    body = {"name": fname, "parents": [parent_id]}
    created = service.files().create(
        body=body, media_body=_media_from_path(str(p), mtype),
        fields=CREATE_FIELDS, supportsAllDrives=True,
    ).execute()
    return {
        "id": created.get("id"), "name": created.get("name"),
        "mime_type": created.get("mimeType"),
        "web_view_link": created.get("webViewLink"),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -q`
Expected: PASS.

- [ ] **Step 5: Registrar las tools en `server.py`**

Dentro de `build_server`, antes de `return mcp`, añadir:

```python
    @mcp.tool()
    def create_file(name: str, parent_id: str, text: str, account: str,
                    mime_type: str = "text/plain") -> dict:
        """Crea un fichero de TEXTO (contenido del modelo: logs, notas, .md) en la
        carpeta `parent_id`. Para ficheros binarios/grandes usa upload_file.
        Devuelve id, nombre, sha256 y web_view_link."""
        return drive_ops.create_file(
            service_factory(account), name=name, parent_id=parent_id,
            text=text, mime_type=mime_type)

    @mcp.tool()
    def upload_file(local_path: str, parent_id: str, account: str,
                    name: Optional[str] = None) -> dict:
        """Sube un fichero desde una ruta LOCAL (confinada por
        GOOGLE_DESPACHO_UPLOAD_ROOT) a la carpeta `parent_id`. Los bytes NO pasan
        por el modelo. Devuelve id, nombre, sha256 y web_view_link."""
        src = _resolve_upload(local_path)
        return drive_ops.upload_file(
            service_factory(account), local_path=src, parent_id=parent_id, name=name)
```

- [ ] **Step 6: Test de server (exclusividad de raíz de subida)**

Añadir a `tests/test_google_despacho_server.py` un test que verifique que `upload_file` pasa por `_resolve_upload` (rechaza fuera de root). Mirar cómo se construye el server en los tests existentes (`build_server(service_factory=…, account_lister=…)`); patrón:

```python
def test_tool_upload_file_confina_root(tmp_path, monkeypatch):
    from plugins.google_despacho_mcp import server
    from google_despacho_fakes import FakeService
    monkeypatch.setenv("GOOGLE_DESPACHO_UPLOAD_ROOT", str(tmp_path / "up"))
    (tmp_path / "up").mkdir()
    fuera = tmp_path / "fuera.pdf"
    fuera.write_bytes(b"x")
    svc = FakeService(files={"create": {"id": "u1"}})
    mcp = server.build_server(service_factory=lambda acc: svc,
                              account_lister=lambda: ["a@b.com"])
    tool = mcp._tool_manager._tools["upload_file"].fn  # patrón de F1 (mcp 1.28.0)
    with pytest.raises(ValueError):
        tool(local_path=str(fuera), parent_id="P1", account="a@b.com")
```

Nota: acceder a la tool por `mcp._tool_manager._tools["<name>"].fn` es el patrón ya usado en `test_google_despacho_server.py::test_search_files_taggea_cada_cuenta_sin_contaminar` (API privada de `mcp`; ajustar si sube de versión).

- [ ] **Step 7: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_server.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py plugins/google_despacho_mcp/server.py tests/test_google_despacho_drive_ops_write.py tests/test_google_despacho_server.py
git commit -m "feat(google-despacho): F2 create_file + upload_file (sha256 + webViewLink)"
```

---

## Task 4: `create_folder` y `ensure_folder_path` (idempotente)

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py`
- Modify: `plugins/google_despacho_mcp/server.py`
- Test: `tests/test_google_despacho_drive_ops_write.py`

`create_folder` crea una carpeta sin más. `ensure_folder_path` recorre segmentos (`"01_Procesado/Sala lectura"`) creando solo los que falten (busca por nombre+parent+mimeType carpeta+no-trashed), y devuelve el `folder_id` final. Idempotente: si todo existe, no crea nada.

- [ ] **Step 1: Escribir los tests**

Añadir a `tests/test_google_despacho_drive_ops_write.py`:

```python
FOLDER_MIME = "application/vnd.google-apps.folder"


def test_create_folder():
    svc = FakeService(files={"create": {"id": "c1", "name": "06_Entrevistas",
                                        "mimeType": FOLDER_MIME}})
    out = drive_ops.create_folder(svc, name="06_Entrevistas", parent_id="P1")
    assert out["id"] == "c1"
    _, kw = svc.recorded("files")[0]
    assert kw["body"]["mimeType"] == FOLDER_MIME
    assert kw["body"]["parents"] == ["P1"]


def test_ensure_folder_path_crea_solo_lo_que_falta():
    # "A/B": A ya existe (list la encuentra), B no (list vacío -> create)
    svc = FakeService(files={
        "list": [
            {"files": [{"id": "A1", "name": "A", "mimeType": FOLDER_MIME}]},  # busca A
            {"files": []},                                                    # busca B bajo A1
        ],
        "create": {"id": "B1", "name": "B", "mimeType": FOLDER_MIME},
    })
    out = drive_ops.ensure_folder_path(svc, path="A/B", parent_id="ROOT")
    assert out["id"] == "B1"
    # solo se creó B (una llamada a create)
    creates = [c for c in svc.recorded("files") if c[0] == "create"]
    assert len(creates) == 1
    assert creates[0][1]["body"]["parents"] == ["A1"]


def test_ensure_folder_path_todo_existe_no_crea():
    svc = FakeService(files={
        "list": [
            {"files": [{"id": "A1", "name": "A", "mimeType": FOLDER_MIME}]},
            {"files": [{"id": "B1", "name": "B", "mimeType": FOLDER_MIME}]},
        ],
    })
    out = drive_ops.ensure_folder_path(svc, path="A/B", parent_id="ROOT")
    assert out["id"] == "B1"
    creates = [c for c in svc.recorded("files") if c[0] == "create"]
    assert creates == []
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k folder -q`
Expected: FAIL.

- [ ] **Step 3: Implementar en `drive_ops.py`**

```python
FOLDER_MIME = "application/vnd.google-apps.folder"


def create_folder(service, *, name: str, parent_id: str) -> dict:
    body = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
    created = service.files().create(
        body=body, fields="id, name, mimeType, parents, webViewLink",
        supportsAllDrives=True,
    ).execute()
    return {"id": created.get("id"), "name": created.get("name"),
            "web_view_link": created.get("webViewLink")}


def _find_child_folder(service, name: str, parent_id: str) -> dict | None:
    safe = name.replace("\\", "\\\\").replace("'", "\\'")
    q = (f"name = '{safe}' and '{parent_id}' in parents "
         f"and mimeType = '{FOLDER_MIME}' and trashed = false")
    resp = service.files().list(
        q=q, fields="files(id, name, mimeType)",
        includeItemsFromAllDrives=True, supportsAllDrives=True,
        corpora="allDrives", spaces="drive", pageSize=2,
    ).execute()
    found = resp.get("files", [])
    return found[0] if found else None


def ensure_folder_path(service, *, path: str, parent_id: str) -> dict:
    """Crea los segmentos de `path` que no existan bajo `parent_id` y devuelve el
    id de la carpeta final. Idempotente. Los segmentos vacíos se ignoran."""
    current = parent_id
    last = {"id": parent_id, "name": None, "web_view_link": None}
    for segment in [s for s in path.replace("\\", "/").split("/") if s]:
        existing = _find_child_folder(service, segment, current)
        if existing:
            last = {"id": existing["id"], "name": existing.get("name"),
                    "web_view_link": None}
        else:
            last = create_folder(service, name=segment, parent_id=current)
        current = last["id"]
    return last
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k folder -q`
Expected: PASS.

- [ ] **Step 5: Registrar tools en `server.py`**

```python
    @mcp.tool()
    def create_folder(name: str, parent_id: str, account: str) -> dict:
        """Crea una carpeta bajo `parent_id`. Para estructura anidada idempotente
        usa ensure_folder_path."""
        return drive_ops.create_folder(service_factory(account), name=name, parent_id=parent_id)

    @mcp.tool()
    def ensure_folder_path(path: str, parent_id: str, account: str) -> dict:
        """Crea los segmentos de `path` (p. ej. '01_Procesado/Sala lectura') que no
        existan bajo `parent_id` y devuelve el id de la carpeta final. IDEMPOTENTE:
        no duplica carpetas existentes (Drive permite duplicados; esto lo evita)."""
        return drive_ops.ensure_folder_path(service_factory(account), path=path, parent_id=parent_id)
```

- [ ] **Step 6: Ejecutar suite del módulo**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py tests/test_google_despacho_server.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py plugins/google_despacho_mcp/server.py tests/test_google_despacho_drive_ops_write.py
git commit -m "feat(google-despacho): F2 create_folder + ensure_folder_path idempotente"
```

---

## Task 5: `update_file_content` y `update_file_metadata`

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py`
- Modify: `plugins/google_despacho_mcp/server.py`
- Test: `tests/test_google_despacho_drive_ops_write.py`, `tests/test_google_despacho_server.py`

`update_file_content` reemplaza el contenido in-place (mismo `file_id`) desde `text=` o `local_path=` (exactamente uno; la exclusividad se valida en el server). `update_file_metadata` renombra.

- [ ] **Step 1: Escribir los tests de drive_ops**

```python
def test_update_file_content_texto():
    svc = FakeService(files={"update": {"id": "f1", "name": "log.jsonl",
                                        "mimeType": "text/plain"}})
    out = drive_ops.update_file_content(svc, "f1", text="nuevo\n")
    assert out["id"] == "f1"
    assert out["sha256"] == __import__("hashlib").sha256(b"nuevo\n").hexdigest()
    _, kw = svc.recorded("files")[0]
    assert kw["fileId"] == "f1"
    assert "media_body" in kw
    assert kw["supportsAllDrives"] is True


def test_update_file_content_desde_ruta(tmp_path):
    src = tmp_path / "x.pdf"
    src.write_bytes(b"PDF")
    svc = FakeService(files={"update": {"id": "f2", "name": "x.pdf"}})
    out = drive_ops.update_file_content(svc, "f2", local_path=str(src))
    assert out["sha256"] == __import__("hashlib").sha256(b"PDF").hexdigest()


def test_update_file_content_exige_exactamente_uno():
    svc = FakeService(files={"update": {}})
    with pytest.raises(ValueError):
        drive_ops.update_file_content(svc, "f1")  # ni text ni local_path
    with pytest.raises(ValueError):
        drive_ops.update_file_content(svc, "f1", text="a", local_path="/x")


def test_update_file_metadata_renombra():
    svc = FakeService(files={"update": {"id": "f1", "name": "nuevo.pdf"}})
    out = drive_ops.update_file_metadata(svc, "f1", name="nuevo.pdf")
    assert out["name"] == "nuevo.pdf"
    _, kw = svc.recorded("files")[0]
    assert kw["body"] == {"name": "nuevo.pdf"}
    assert kw["fileId"] == "f1"
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k update -q`
Expected: FAIL.

- [ ] **Step 3: Implementar en `drive_ops.py`**

```python
def update_file_content(service, file_id: str, *, text: str | None = None,
                        local_path: str | None = None,
                        mime_type: str | None = None,
                        max_text_bytes: int = 1_000_000) -> dict:
    """Reemplaza el contenido de un fichero existente (mismo file_id). Exactamente
    uno de `text` / `local_path`. sha256 sobre los bytes enviados."""
    if (text is None) == (local_path is None):
        raise ValueError("Pasa exactamente uno de text o local_path.")
    if text is not None:
        data = text.encode("utf-8")
        if max_text_bytes and len(data) > max_text_bytes:
            raise ValueError(f"{len(data)} bytes supera max_text_bytes ({max_text_bytes}).")
        media = _media_from_bytes(data, mime_type or "text/plain")
    else:
        data = Path(local_path).read_bytes()
        mtype = mime_type or (mimetypes.guess_type(local_path)[0] or "application/octet-stream")
        media = _media_from_path(local_path, mtype)
    updated = service.files().update(
        fileId=file_id, media_body=media,
        fields="id, name, mimeType, webViewLink", supportsAllDrives=True,
    ).execute()
    return {"id": updated.get("id"), "name": updated.get("name"),
            "mime_type": updated.get("mimeType"),
            "web_view_link": updated.get("webViewLink"),
            "sha256": hashlib.sha256(data).hexdigest()}


def update_file_metadata(service, file_id: str, *, name: str) -> dict:
    """Renombra un fichero (u otros metadatos editables en el futuro)."""
    updated = service.files().update(
        fileId=file_id, body={"name": name},
        fields="id, name, webViewLink", supportsAllDrives=True,
    ).execute()
    return {"id": updated.get("id"), "name": updated.get("name"),
            "web_view_link": updated.get("webViewLink")}
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k update -q`
Expected: PASS.

- [ ] **Step 5: Registrar tools en `server.py`**

```python
    @mcp.tool()
    def update_file_content(file_id: str, account: str,
                            text: Optional[str] = None,
                            local_path: Optional[str] = None) -> dict:
        """Reemplaza el contenido de un fichero (mismo id). Pasa `text` (contenido
        del modelo) O `local_path` (ruta local confinada por UPLOAD-root), no ambos.
        Devuelve id, nombre, sha256 y web_view_link."""
        src = _resolve_upload(local_path) if local_path else None
        return drive_ops.update_file_content(
            service_factory(account), file_id, text=text, local_path=src)

    @mcp.tool()
    def update_file_metadata(file_id: str, name: str, account: str) -> dict:
        """Renombra un fichero. Devuelve id, nombre y web_view_link."""
        return drive_ops.update_file_metadata(service_factory(account), file_id, name=name)
```

- [ ] **Step 6: Ejecutar suite del módulo**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py tests/test_google_despacho_server.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py plugins/google_despacho_mcp/server.py tests/test_google_despacho_drive_ops_write.py
git commit -m "feat(google-despacho): F2 update_file_content + update_file_metadata"
```

---

## Task 6: `move_file` y `copy_file`

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py`
- Modify: `plugins/google_despacho_mcp/server.py`
- Test: `tests/test_google_despacho_drive_ops_write.py`

`move_file` cambia de carpeta con `addParents`/`removeParents` (necesita leer los parents actuales primero). `copy_file` usa `files.copy` (interno de Drive), con `new_name` opcional.

- [ ] **Step 1: Escribir los tests**

```python
def test_move_file_calcula_remove_parents():
    svc = FakeService(files={
        "get": {"id": "f1", "parents": ["OLD"]},
        "update": {"id": "f1", "name": "x", "parents": ["NEW"]},
    })
    out = drive_ops.move_file(svc, "f1", dst_folder_id="NEW")
    assert out["id"] == "f1"
    upd = [c for c in svc.recorded("files") if c[0] == "update"][0][1]
    assert upd["addParents"] == "NEW"
    assert upd["removeParents"] == "OLD"
    assert upd["fileId"] == "f1"


def test_copy_file_con_nuevo_nombre():
    svc = FakeService(files={"copy": {"id": "c1", "name": "copia.pdf",
                                      "webViewLink": "https://drive/c1"}})
    out = drive_ops.copy_file(svc, "f1", dst_folder_id="DST", new_name="copia.pdf")
    assert out["id"] == "c1"
    _, kw = svc.recorded("files")[0]
    assert kw["fileId"] == "f1"
    assert kw["body"]["parents"] == ["DST"]
    assert kw["body"]["name"] == "copia.pdf"
    assert kw["supportsAllDrives"] is True


def test_copy_file_sin_nombre_no_pone_name():
    svc = FakeService(files={"copy": {"id": "c1"}})
    drive_ops.copy_file(svc, "f1", dst_folder_id="DST")
    _, kw = svc.recorded("files")[0]
    assert "name" not in kw["body"]
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k "move or copy" -q`
Expected: FAIL.

- [ ] **Step 3: Implementar en `drive_ops.py`**

```python
def move_file(service, file_id: str, *, dst_folder_id: str) -> dict:
    meta = service.files().get(
        fileId=file_id, fields="id, parents", supportsAllDrives=True,
    ).execute()
    prev_parents = ",".join(meta.get("parents", []))
    updated = service.files().update(
        fileId=file_id, addParents=dst_folder_id, removeParents=prev_parents,
        fields="id, name, parents, webViewLink", supportsAllDrives=True,
    ).execute()
    return {"id": updated.get("id"), "name": updated.get("name"),
            "parents": updated.get("parents"),
            "web_view_link": updated.get("webViewLink")}


def copy_file(service, file_id: str, *, dst_folder_id: str,
              new_name: str | None = None) -> dict:
    body: dict = {"parents": [dst_folder_id]}
    if new_name:
        body["name"] = new_name
    copied = service.files().copy(
        fileId=file_id, body=body,
        fields="id, name, mimeType, webViewLink", supportsAllDrives=True,
    ).execute()
    return {"id": copied.get("id"), "name": copied.get("name"),
            "mime_type": copied.get("mimeType"),
            "web_view_link": copied.get("webViewLink")}
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k "move or copy" -q`
Expected: PASS.

- [ ] **Step 5: Registrar tools en `server.py`**

```python
    @mcp.tool()
    def move_file(file_id: str, dst_folder_id: str, account: str) -> dict:
        """Mueve un fichero a otra carpeta (addParents/removeParents)."""
        return drive_ops.move_file(service_factory(account), file_id, dst_folder_id=dst_folder_id)

    @mcp.tool()
    def copy_file(file_id: str, dst_folder_id: str, account: str,
                  new_name: Optional[str] = None) -> dict:
        """Copia un fichero a otra carpeta (files.copy interno de Drive), con
        renombrado opcional."""
        return drive_ops.copy_file(service_factory(account), file_id,
                                   dst_folder_id=dst_folder_id, new_name=new_name)
```

- [ ] **Step 6: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py plugins/google_despacho_mcp/server.py tests/test_google_despacho_drive_ops_write.py
git commit -m "feat(google-despacho): F2 move_file + copy_file"
```

---

## Task 7: `delete_file` (papelera/permanente) y `restore_file`

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py`
- Modify: `plugins/google_despacho_mcp/server.py`
- Test: `tests/test_google_despacho_drive_ops_write.py`

Borrado por defecto = a papelera (`trashed=true` vía update). `permanent=true` = `files.delete` (irreversible). `restore_file` = `trashed=false`.

- [ ] **Step 1: Escribir los tests**

```python
def test_delete_file_a_papelera_por_defecto():
    svc = FakeService(files={"update": {"id": "f1", "trashed": True}})
    out = drive_ops.delete_file(svc, "f1")
    assert out["trashed"] is True
    _, kw = svc.recorded("files")[0]
    assert kw["body"] == {"trashed": True}
    # no se llamó a delete
    assert all(c[0] != "delete" for c in svc.recorded("files"))


def test_delete_file_permanente_llama_delete():
    svc = FakeService(files={"delete": {}})
    out = drive_ops.delete_file(svc, "f1", permanent=True)
    assert out["permanently_deleted"] is True
    _, kw = svc.recorded("files")[0]
    assert kw["fileId"] == "f1"
    assert kw["supportsAllDrives"] is True


def test_restore_file_desmarca_trashed():
    svc = FakeService(files={"update": {"id": "f1", "trashed": False}})
    out = drive_ops.restore_file(svc, "f1")
    assert out["trashed"] is False
    _, kw = svc.recorded("files")[0]
    assert kw["body"] == {"trashed": False}
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k "delete or restore" -q`
Expected: FAIL.

- [ ] **Step 3: Implementar en `drive_ops.py`**

```python
def delete_file(service, file_id: str, *, permanent: bool = False) -> dict:
    """Por defecto envía a la papelera (reversible con restore_file). Con
    permanent=True borra IRREVERSIBLEMENTE (files.delete)."""
    if permanent:
        service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        return {"id": file_id, "permanently_deleted": True}
    updated = service.files().update(
        fileId=file_id, body={"trashed": True},
        fields="id, trashed", supportsAllDrives=True,
    ).execute()
    return {"id": updated.get("id"), "trashed": updated.get("trashed")}


def restore_file(service, file_id: str) -> dict:
    """Saca un fichero de la papelera (trashed=false)."""
    updated = service.files().update(
        fileId=file_id, body={"trashed": False},
        fields="id, trashed", supportsAllDrives=True,
    ).execute()
    return {"id": updated.get("id"), "trashed": updated.get("trashed")}
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k "delete or restore" -q`
Expected: PASS.

- [ ] **Step 5: Registrar tools en `server.py`**

```python
    @mcp.tool()
    def delete_file(file_id: str, account: str, permanent: bool = False) -> dict:
        """Envía un fichero a la PAPELERA (por defecto, reversible con restore_file).
        permanent=True lo borra IRREVERSIBLEMENTE."""
        return drive_ops.delete_file(service_factory(account), file_id, permanent=permanent)

    @mcp.tool()
    def restore_file(file_id: str, account: str) -> dict:
        """Saca un fichero de la papelera."""
        return drive_ops.restore_file(service_factory(account), file_id)
```

- [ ] **Step 6: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py plugins/google_despacho_mcp/server.py tests/test_google_despacho_drive_ops_write.py
git commit -m "feat(google-despacho): F2 delete_file (papelera/permanente) + restore_file"
```

---

## Task 8: `append_text` (append forense a log/nota)

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py`
- Modify: `plugins/google_despacho_mcp/server.py`
- Test: `tests/test_google_despacho_drive_ops_write.py`

Drive no tiene append: leer contenido actual (get_media), concatenar, reescribir vía `update_file_content`. Solo para ficheros de texto.

- [ ] **Step 1: Escribir el test**

```python
def test_append_text_concatena_y_reescribe():
    svc = FakeService(files={
        "get": {"id": "f1", "name": "log.jsonl", "mimeType": "text/plain", "size": "6"},
        "get_media": b"linea1\n",
        "update": {"id": "f1", "name": "log.jsonl", "mimeType": "text/plain"},
    })
    out = drive_ops.append_text(svc, "f1", "linea2\n")
    assert out["id"] == "f1"
    # el update recibió el contenido concatenado
    upd = [c for c in svc.recorded("files") if c[0] == "update"][0][1]
    assert "media_body" in upd


def test_append_text_rechaza_binario():
    svc = FakeService(files={
        "get": {"id": "b1", "name": "x.pdf", "mimeType": "application/pdf", "size": "10"},
    })
    with pytest.raises(ValueError):
        drive_ops.append_text(svc, "b1", "no")
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k append -q`
Expected: FAIL.

- [ ] **Step 3: Implementar en `drive_ops.py`**

```python
def append_text(service, file_id: str, text: str, *,
                max_bytes: int = 5_000_000) -> dict:
    """Append a un fichero de TEXTO existente (read-modify-write server-side).
    Rechaza binarios y Docs nativos. Devuelve id, nombre y sha256 del resultado."""
    meta = get_file_metadata(service, file_id, fields="id, name, mimeType, size")
    mime = meta.get("mimeType", "")
    if mime.startswith(GOOGLE_NATIVE_PREFIX):
        raise ValueError(f"append_text no aplica a Docs nativos ({mime!r}).")
    if not (mime.startswith("text/") or mime in _TEXTUAL_MIMES):
        raise ValueError(f"append_text solo para texto; {mime!r} no lo es.")
    size = int(meta.get("size") or 0)
    if max_bytes and size > max_bytes:
        raise ValueError(f"{size} bytes supera max_bytes ({max_bytes}).")
    current = service.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
    current_bytes = bytes(current) if isinstance(current, (bytes, bytearray)) else str(current).encode("utf-8")
    new_bytes = current_bytes + text.encode("utf-8")
    if max_bytes and len(new_bytes) > max_bytes:
        raise ValueError(f"{len(new_bytes)} bytes supera max_bytes ({max_bytes}).")
    updated = service.files().update(
        fileId=file_id, media_body=_media_from_bytes(new_bytes, mime or "text/plain"),
        fields="id, name, mimeType", supportsAllDrives=True,
    ).execute()
    return {"id": updated.get("id"), "name": updated.get("name"),
            "sha256": hashlib.sha256(new_bytes).hexdigest()}
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k append -q`
Expected: PASS.

- [ ] **Step 5: Registrar tool en `server.py`**

```python
    @mcp.tool()
    def append_text(file_id: str, text: str, account: str) -> dict:
        """Añade texto al final de un fichero de TEXTO existente (p. ej.
        _intake_log.jsonl). Read-modify-write server-side. Devuelve id, nombre y
        sha256 del resultado."""
        return drive_ops.append_text(service_factory(account), file_id, text)
```

- [ ] **Step 6: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py plugins/google_despacho_mcp/server.py tests/test_google_despacho_drive_ops_write.py
git commit -m "feat(google-despacho): F2 append_text (log forense server-side)"
```

---

## Task 9: `export_to_drive` (export a PDF/Office guardado de vuelta en Drive)

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py`
- Modify: `plugins/google_despacho_mcp/server.py`
- Test: `tests/test_google_despacho_drive_ops_write.py`

Exporta un Doc nativo (o `.docx`/`.xlsx` subido) a PDF (default) u Office, y sube el resultado a Drive server-side (bytes no pasan por el modelo). Devuelve el fichero nuevo con sha256. `format` ∈ {`pdf`, `office`}. Para Docs nativos usa `export_media`; para binarios ya-Office no hay conversión a PDF vía Drive API → se documenta como no soportado (usar el pipeline local). El default de carpeta destino es la del origen.

- [ ] **Step 1: Escribir el test**

```python
def test_export_to_drive_doc_nativo_a_pdf():
    svc = FakeService(files={
        "get": {"id": "g1", "name": "Escrito", "mimeType":
                "application/vnd.google-apps.document", "parents": ["CASO"]},
        "export_media": b"%PDF-1.4 real",
        "create": {"id": "p1", "name": "Escrito.pdf", "mimeType": "application/pdf",
                   "webViewLink": "https://drive/p1"},
    })
    out = drive_ops.export_to_drive(svc, "g1")
    assert out["id"] == "p1"
    assert out["sha256"] == __import__("hashlib").sha256(b"%PDF-1.4 real").hexdigest()
    # exportó a PDF y subió con nombre + .pdf a la carpeta del origen
    exp = [c for c in svc.recorded("files") if c[0] == "export_media"][0][1]
    assert exp["mimeType"] == "application/pdf"
    crt = [c for c in svc.recorded("files") if c[0] == "create"][0][1]
    assert crt["body"]["name"] == "Escrito.pdf"
    assert crt["body"]["parents"] == ["CASO"]


def test_export_to_drive_dst_folder_explicito():
    svc = FakeService(files={
        "get": {"id": "g1", "name": "Doc", "mimeType":
                "application/vnd.google-apps.document", "parents": ["ORIG"]},
        "export_media": b"pdf",
        "create": {"id": "p1", "name": "Doc.pdf"},
    })
    drive_ops.export_to_drive(svc, "g1", dst_folder_id="OTRA")
    crt = [c for c in svc.recorded("files") if c[0] == "create"][0][1]
    assert crt["body"]["parents"] == ["OTRA"]


def test_export_to_drive_no_nativo_rechaza():
    svc = FakeService(files={
        "get": {"id": "b1", "name": "x.docx", "mimeType":
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "parents": ["C"]},
    })
    with pytest.raises(ValueError):
        drive_ops.export_to_drive(svc, "b1")
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k export_to_drive -q`
Expected: FAIL.

- [ ] **Step 3: Implementar en `drive_ops.py`**

```python
_EXPORT_EXT = {"application/pdf": ".pdf",
               "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
               "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx"}


def export_to_drive(service, file_id: str, *, format: str = "pdf",
                    dst_folder_id: str | None = None,
                    new_name: str | None = None) -> dict:
    """Exporta un Doc NATIVO a PDF (default) u Office y sube el resultado a Drive
    (server-side; sin bytes por el modelo). Destino por defecto = carpeta del
    origen. Los ficheros ya-binarios (docx subido, etc.) no se convierten aquí."""
    meta = get_file_metadata(service, file_id,
                             fields="id, name, mimeType, parents")
    mime = meta.get("mimeType", "")
    if not mime.startswith(GOOGLE_NATIVE_PREFIX):
        raise ValueError(
            f"export_to_drive solo exporta Docs nativos; {mime!r} ya es binario. "
            f"Usa copy_file o el pipeline local para convertir.")
    table = _EXPORT_PDF if format == "pdf" else _EXPORT_OFFICE
    export_mime = table.get(mime)
    if not export_mime:
        raise ValueError(f"El Doc {mime!r} no tiene export soportado a {format!r}.")
    data = service.files().export_media(fileId=file_id, mimeType=export_mime).execute()
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("La API no devolvió bytes al exportar.")
    data = bytes(data)
    base = new_name or meta.get("name", "export")
    ext = _EXPORT_EXT.get(export_mime, "")
    fname = base if base.lower().endswith(ext) else base + ext
    parents = [dst_folder_id] if dst_folder_id else meta.get("parents", [])
    created = service.files().create(
        body={"name": fname, "parents": parents},
        media_body=_media_from_bytes(data, export_mime),
        fields=CREATE_FIELDS, supportsAllDrives=True,
    ).execute()
    return {"id": created.get("id"), "name": created.get("name"),
            "mime_type": export_mime,
            "web_view_link": created.get("webViewLink"),
            "sha256": hashlib.sha256(data).hexdigest()}
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k export_to_drive -q`
Expected: PASS.

- [ ] **Step 5: Registrar tool en `server.py`**

```python
    @mcp.tool()
    def export_to_drive(file_id: str, account: str, format: str = "pdf",
                        dst_folder_id: Optional[str] = None,
                        new_name: Optional[str] = None) -> dict:
        """Exporta un Doc nativo a PDF (default) u Office ('office') y GUARDA el
        resultado en Drive (server-side; sin bytes por el modelo). Destino por
        defecto = la carpeta del origen. Devuelve id, nombre, sha256 y web_view_link."""
        return drive_ops.export_to_drive(
            service_factory(account), file_id, format=format,
            dst_folder_id=dst_folder_id, new_name=new_name)
```

- [ ] **Step 6: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py plugins/google_despacho_mcp/server.py tests/test_google_despacho_drive_ops_write.py
git commit -m "feat(google-despacho): F2 export_to_drive (PDF/Office -> Drive)"
```

---

## Task 10: `create_shortcut`

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py`
- Modify: `plugins/google_despacho_mcp/server.py`
- Test: `tests/test_google_despacho_drive_ops_write.py`

Un acceso directo es un fichero con `mimeType = application/vnd.google-apps.shortcut` y `shortcutDetails.targetId`. Enlaza un doc en otra carpeta sin duplicar bytes.

- [ ] **Step 1: Escribir el test**

```python
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"


def test_create_shortcut():
    svc = FakeService(files={"create": {
        "id": "s1", "name": "Escrito (acceso directo)", "mimeType": SHORTCUT_MIME,
        "shortcutDetails": {"targetId": "T1"}, "webViewLink": "https://drive/s1"}})
    out = drive_ops.create_shortcut(svc, target_id="T1", dst_folder_id="DST",
                                    name="Escrito (acceso directo)")
    assert out["id"] == "s1"
    assert out["target_id"] == "T1"
    _, kw = svc.recorded("files")[0]
    assert kw["body"]["mimeType"] == SHORTCUT_MIME
    assert kw["body"]["shortcutDetails"]["targetId"] == "T1"
    assert kw["body"]["parents"] == ["DST"]
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k shortcut -q`
Expected: FAIL.

- [ ] **Step 3: Implementar en `drive_ops.py`**

```python
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"


def create_shortcut(service, *, target_id: str, dst_folder_id: str,
                    name: str | None = None) -> dict:
    """Crea un acceso directo a `target_id` dentro de `dst_folder_id` (sin duplicar
    bytes). Si no se da `name`, Drive usa el del destino."""
    body = {"mimeType": SHORTCUT_MIME, "parents": [dst_folder_id],
            "shortcutDetails": {"targetId": target_id}}
    if name:
        body["name"] = name
    created = service.files().create(
        body=body, fields="id, name, mimeType, shortcutDetails, webViewLink",
        supportsAllDrives=True,
    ).execute()
    return {"id": created.get("id"), "name": created.get("name"),
            "target_id": (created.get("shortcutDetails") or {}).get("targetId"),
            "web_view_link": created.get("webViewLink")}
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k shortcut -q`
Expected: PASS.

- [ ] **Step 5: Registrar tool en `server.py`**

```python
    @mcp.tool()
    def create_shortcut(target_id: str, dst_folder_id: str, account: str,
                        name: Optional[str] = None) -> dict:
        """Crea un acceso directo a `target_id` en `dst_folder_id`: enlaza un doc en
        varias carpetas sin duplicar bytes (fuente única)."""
        return drive_ops.create_shortcut(
            service_factory(account), target_id=target_id,
            dst_folder_id=dst_folder_id, name=name)
```

- [ ] **Step 6: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py plugins/google_despacho_mcp/server.py tests/test_google_despacho_drive_ops_write.py
git commit -m "feat(google-despacho): F2 create_shortcut"
```

---

## Task 11: Permisos con guardarraíl de compartición externa (SEGURIDAD)

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py`
- Modify: `plugins/google_despacho_mcp/server.py`
- Test: `tests/test_google_despacho_drive_ops_write.py`, `tests/test_google_despacho_server.py`

Pieza crítica. El GUARDARRAÍL vive en el server (es política, no operación de Drive) y `drive_ops` ejecuta el permiso ya validado. Reglas:
- Dominios internos: `tyukhay.legal`, `engelvoelkers.com`.
- Se BLOQUEA (salvo `allow_external=true`): `type=anyone` y `type=user`/`type=domain` cuyo dominio no sea interno.
- `role=owner` NUNCA (ni con el flag): se rechaza siempre.
- `sendNotificationEmail=false` por defecto.

- [ ] **Step 1: Escribir el test del guardarraíl (server) y de la operación (drive_ops)**

Añadir a `tests/test_google_despacho_drive_ops_write.py` (operación pura):

```python
def test_create_permission_pasa_body_y_flags():
    svc = FakeService(permissions={"create": {"id": "p1", "type": "user",
                                              "role": "reader"}})
    out = drive_ops.create_permission(
        svc, "f1", perm_type="user", role="reader",
        email_address="colega@tyukhay.legal", send_notification_email=False)
    assert out["id"] == "p1"
    _, kw = svc.recorded("permissions")[0]
    assert kw["fileId"] == "f1"
    assert kw["body"]["type"] == "user"
    assert kw["body"]["role"] == "reader"
    assert kw["body"]["emailAddress"] == "colega@tyukhay.legal"
    assert kw["sendNotificationEmail"] is False
    assert kw["supportsAllDrives"] is True


def test_delete_permission():
    svc = FakeService(permissions={"delete": {}})
    out = drive_ops.delete_permission(svc, "f1", "p1")
    assert out["deleted"] is True
    _, kw = svc.recorded("permissions")[0]
    assert kw["fileId"] == "f1"
    assert kw["permissionId"] == "p1"
```

Añadir a `tests/test_google_despacho_server.py` (política del guardarraíl — usa el helper de invocación de tools del fichero):

```python
def _perm_tool(name="create_permission"):
    from plugins.google_despacho_mcp import server
    from google_despacho_fakes import FakeService
    svc = FakeService(permissions={"create": {"id": "p1"}, "delete": {}})
    mcp = server.build_server(service_factory=lambda acc: svc,
                              account_lister=lambda: ["a@b.com"])
    return mcp._tool_manager._tools[name].fn  # patrón de F1 (mcp 1.28.0)


def test_guardarrail_bloquea_anyone_sin_flag():
    tool = _perm_tool()
    with pytest.raises(ValueError):
        tool(file_id="f1", perm_type="anyone", role="reader", account="a@b.com")


def test_guardarrail_bloquea_dominio_externo_sin_flag():
    tool = _perm_tool()
    with pytest.raises(ValueError):
        tool(file_id="f1", perm_type="user", role="reader",
             email_address="x@gmail.com", account="a@b.com")


def test_guardarrail_permite_interno_sin_flag():
    tool = _perm_tool()
    out = tool(file_id="f1", perm_type="user", role="reader",
               email_address="x@engelvoelkers.com", account="a@b.com")
    assert out["id"] == "p1"


def test_guardarrail_permite_externo_con_flag():
    tool = _perm_tool()
    out = tool(file_id="f1", perm_type="anyone", role="reader",
               allow_external=True, account="a@b.com")
    assert out["id"] == "p1"


def test_guardarrail_owner_siempre_rechazado():
    tool = _perm_tool()
    with pytest.raises(ValueError):
        tool(file_id="f1", perm_type="user", role="owner",
             email_address="x@tyukhay.legal", allow_external=True, account="a@b.com")
```

Acceder a la tool por `mcp._tool_manager._tools["<name>"].fn` es el patrón ya usado en `test_google_despacho_server.py` de la F1 (API privada de `mcp`).

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k permission tests/test_google_despacho_server.py -k guardarrail -q`
Expected: FAIL.

- [ ] **Step 3: Implementar las operaciones en `drive_ops.py`**

```python
def create_permission(service, file_id: str, *, perm_type: str, role: str,
                      email_address: str | None = None, domain: str | None = None,
                      send_notification_email: bool = False) -> dict:
    body: dict = {"type": perm_type, "role": role}
    if email_address:
        body["emailAddress"] = email_address
    if domain:
        body["domain"] = domain
    created = service.permissions().create(
        fileId=file_id, body=body,
        sendNotificationEmail=send_notification_email,
        fields="id, type, role, emailAddress, domain", supportsAllDrives=True,
    ).execute()
    return created


def update_permission(service, file_id: str, permission_id: str, *, role: str) -> dict:
    updated = service.permissions().update(
        fileId=file_id, permissionId=permission_id, body={"role": role},
        fields="id, type, role, emailAddress, domain", supportsAllDrives=True,
    ).execute()
    return updated


def delete_permission(service, file_id: str, permission_id: str) -> dict:
    service.permissions().delete(
        fileId=file_id, permissionId=permission_id, supportsAllDrives=True,
    ).execute()
    return {"file_id": file_id, "permission_id": permission_id, "deleted": True}
```

- [ ] **Step 4: Implementar el guardarraíl y las tools en `server.py`**

Añadir arriba (junto a los helpers de módulo, tras `_resolve_upload`):

```python
INTERNAL_DOMAINS = {"tyukhay.legal", "engelvoelkers.com"}


def _guard_external_share(*, perm_type: str, role: str,
                          email_address: Optional[str], domain: Optional[str],
                          allow_external: bool) -> None:
    """Guardarraíl §5. Lanza ValueError si la compartición es externa sin
    allow_external, o si pide role=owner (siempre prohibido)."""
    if role == "owner":
        raise ValueError("role=owner nunca se concede automáticamente por el MCP.")
    external = False
    if perm_type == "anyone":
        external = True
    elif perm_type in ("user", "group"):
        dom = (email_address or "").rsplit("@", 1)[-1].lower()
        external = dom not in INTERNAL_DOMAINS
    elif perm_type == "domain":
        external = (domain or "").lower() not in INTERNAL_DOMAINS
    if external and not allow_external:
        raise ValueError(
            "Compartición EXTERNA bloqueada (type/dominio ajeno a "
            f"{sorted(INTERNAL_DOMAINS)}). Repite con allow_external=true si es a "
            "conciencia.")
```

Y las tools dentro de `build_server`:

```python
    @mcp.tool()
    def create_permission(file_id: str, perm_type: str, role: str, account: str,
                          email_address: Optional[str] = None,
                          domain: Optional[str] = None,
                          allow_external: bool = False,
                          send_notification_email: bool = False) -> dict:
        """Concede un permiso (ACL). perm_type: user|group|domain|anyone;
        role: reader|commenter|writer (owner PROHIBIDO). Compartir con externos
        (anyone o dominio ajeno a tyukhay.legal/engelvoelkers.com) exige
        allow_external=true. No envía email de aviso salvo send_notification_email."""
        _guard_external_share(perm_type=perm_type, role=role,
                              email_address=email_address, domain=domain,
                              allow_external=allow_external)
        return drive_ops.create_permission(
            service_factory(account), file_id, perm_type=perm_type, role=role,
            email_address=email_address, domain=domain,
            send_notification_email=send_notification_email)

    @mcp.tool()
    def update_permission(file_id: str, permission_id: str, role: str,
                          account: str) -> dict:
        """Cambia el rol de un permiso existente (owner PROHIBIDO)."""
        if role == "owner":
            raise ValueError("role=owner nunca se concede automáticamente por el MCP.")
        return drive_ops.update_permission(
            service_factory(account), file_id, permission_id, role=role)

    @mcp.tool()
    def delete_permission(file_id: str, permission_id: str, account: str) -> dict:
        """Revoca un permiso (ACL) de un fichero."""
        return drive_ops.delete_permission(service_factory(account), file_id, permission_id)
```

- [ ] **Step 5: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k permission tests/test_google_despacho_server.py -k guardarrail -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py plugins/google_despacho_mcp/server.py tests/test_google_despacho_drive_ops_write.py tests/test_google_despacho_server.py
git commit -m "feat(google-despacho): F2 permisos + guardarrail de comparticion externa"
```

---

## Task 12: Navegación — `list_folder`, `list_trash`, `get_folder_path`

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py`
- Modify: `plugins/google_despacho_mcp/server.py`
- Test: `tests/test_google_despacho_drive_ops_write.py`

`list_folder` = hijos directos (reusa la query `'ID' in parents`). `list_trash` = ficheros en papelera. `get_folder_path` = sube por `parents` hasta la raíz y devuelve la lista de nombres (miga de pan).

- [ ] **Step 1: Escribir los tests**

```python
def test_list_folder_hijos_directos():
    svc = FakeService(files={"list": {"files": [
        {"id": "a", "name": "00_Input", "mimeType": FOLDER_MIME},
        {"id": "b", "name": "doc.pdf", "mimeType": "application/pdf"}]}})
    out = drive_ops.list_folder(svc, "P1")
    assert [f["id"] for f in out] == ["a", "b"]
    _, kw = svc.recorded("files")[0]
    assert "'P1' in parents" in kw["q"]
    assert "trashed = false" in kw["q"]


def test_list_trash():
    svc = FakeService(files={"list": {"files": [{"id": "t1", "name": "viejo"}]}})
    out = drive_ops.list_trash(svc)
    assert out[0]["id"] == "t1"
    _, kw = svc.recorded("files")[0]
    assert kw["q"] == "trashed = true"


def test_get_folder_path_sube_hasta_raiz():
    # C -> B -> A -> (sin parents)
    svc = FakeService(files={"get": [
        {"id": "C", "name": "Sala lectura", "parents": ["B"]},
        {"id": "B", "name": "01_Procesado", "parents": ["A"]},
        {"id": "A", "name": "W-02352", "parents": []},
    ]})
    out = drive_ops.get_folder_path(svc, "C")
    assert out["names"] == ["W-02352", "01_Procesado", "Sala lectura"]
    assert out["path"] == "W-02352/01_Procesado/Sala lectura"
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k "list_folder or list_trash or folder_path" -q`
Expected: FAIL.

- [ ] **Step 3: Implementar en `drive_ops.py`**

```python
def list_folder(service, folder_id: str, *, page_size: int = 200) -> list[dict]:
    """Hijos directos de una carpeta (name/id/mimeType/...). No recursivo."""
    q = f"'{folder_id}' in parents and trashed = false"
    return search_files(service, q, page_size=page_size)


def list_trash(service, *, page_size: int = 100) -> list[dict]:
    """Ficheros en la papelera (para recuperar con restore_file)."""
    return search_files(service, "trashed = true", page_size=page_size)


def get_folder_path(service, folder_id: str, *, max_depth: int = 50) -> dict:
    """Miga de pan: sube por `parents` hasta la raíz. Devuelve names (raíz→hoja)
    y path unido por '/'. Si hay varios parents, sigue el primero."""
    names: list[str] = []
    current = folder_id
    for _ in range(max_depth):
        meta = service.files().get(
            fileId=current, fields="id, name, parents", supportsAllDrives=True,
        ).execute()
        names.append(meta.get("name", ""))
        parents = meta.get("parents") or []
        if not parents:
            break
        current = parents[0]
    names.reverse()
    return {"names": names, "path": "/".join(names)}
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops_write.py -k "list_folder or list_trash or folder_path" -q`
Expected: PASS.

- [ ] **Step 5: Registrar tools en `server.py`**

```python
    @mcp.tool()
    def list_folder(folder_id: str, account: str, max_results: int = 200) -> list[dict]:
        """Lista los hijos DIRECTOS de una carpeta (navegación tipo explorador, sin
        escribir queries). No recursivo."""
        return drive_ops.list_folder(service_factory(account), folder_id, page_size=max_results)

    @mcp.tool()
    def list_trash(account: str, max_results: int = 100) -> list[dict]:
        """Lista los ficheros en la papelera de la cuenta (recuperables con
        restore_file)."""
        return drive_ops.list_trash(service_factory(account), page_size=max_results)

    @mcp.tool()
    def get_folder_path(folder_id: str, account: str) -> dict:
        """Miga de pan / ruta completa de una carpeta (raíz→hoja)."""
        return drive_ops.get_folder_path(service_factory(account), folder_id)
```

- [ ] **Step 6: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py plugins/google_despacho_mcp/server.py tests/test_google_despacho_drive_ops_write.py
git commit -m "feat(google-despacho): F2 navegacion (list_folder, list_trash, get_folder_path)"
```

---

## Task 13: Docstring del server, README y verificación final

**Files:**
- Modify: `plugins/google_despacho_mcp/server.py` (docstring de cabecera)
- Modify: `plugins/google_despacho_mcp/README.md`
- Test: toda la suite

- [ ] **Step 1: Actualizar el docstring de cabecera de `server.py`**

Reemplazar el docstring (líneas ~2-14) para reflejar que ya NO es solo lectura: describir que F2 añade escritura CRUD, permisos con guardarraíl `allow_external`, y navegación; y documentar las dos variables de entorno de confinamiento: `GOOGLE_DESPACHO_DL_ROOT` (descargas) y `GOOGLE_DESPACHO_UPLOAD_ROOT` (subidas).

- [ ] **Step 2: Actualizar `README.md`**

Añadir a la lista de tools las de F2 agrupadas (escritura, permisos, navegación), la nota de scope `drive` completo + reautorización, y la variable `GOOGLE_DESPACHO_UPLOAD_ROOT`. Seguir el estilo de la sección de tools de F1 ya presente.

- [ ] **Step 3: Ejecutar la suite completa del módulo**

Run: `python -m pytest tests/test_google_despacho_auth.py tests/test_google_despacho_drive_ops.py tests/test_google_despacho_drive_ops_write.py tests/test_google_despacho_server.py -q`
Expected: PASS (todos).

- [ ] **Step 4: Ejecutar la suite COMPLETA del repo (regresión)**

Run: `python -m pytest -q --tb=no`
Expected: verde salvo los fallos pre-existentes ya documentados en STATUS.md (`test_sudespacho_relations`). Anotar el conteo.

- [ ] **Step 5: Commit**

```bash
git add plugins/google_despacho_mcp/server.py plugins/google_despacho_mcp/README.md
git commit -m "docs(google-despacho): F2 docstring server + README (escritura/permisos/navegacion)"
```

- [ ] **Step 6: Verificación de integración manual (antes de dar F2 por viva)**

Requiere reautorización (Task 1, Step 7). Contra una carpeta DESECHABLE de Drive:
1. `ensure_folder_path("_pruebas_f2/sub", parent_id=<root TL>)` dos veces → misma id, sin duplicar.
2. `create_file(text=…)` una nota; `append_text` una línea; `read_file_content` → verifica contenido.
3. `upload_file` un fichero local pequeño (dentro de UPLOAD-root) → verifica sha256.
4. `copy_file` + `move_file` + `update_file_metadata` (renombrar) → verifica en la UI de Drive.
5. `create_permission` interno OK; `anyone` sin flag → error; con `allow_external=true` → OK; luego `delete_permission`.
6. `export_to_drive` de un Google Doc → PDF en la carpeta.
7. `delete_file` (papelera) → `list_trash` lo ve → `restore_file` → `delete_file(permanent=true)`.
8. Confirmar que las 9 tools de lectura de F1 siguen funcionando con el scope nuevo.

- [ ] **Step 7: PR**

```bash
git push -u origin feat/google-despacho-mcp-f2
gh pr create --fill --base main
```
Verificar que el check `leak-scan` pasa. En el cuerpo del PR, recordar el paso manual de reautorización de las 2 cuentas.

---

## Notas de cierre

- **Actualizar `PLAN.md`**: marcar F2 y anotar el hash del PR (regla del proyecto: hogar del estado de ciclo de vida).
- **Actualizar el spec** §13.8 / §12 con "F2 HECHA" tras el merge.
- **NO** tocar `import_drive_folder`, lote ni Calendar: son F3/F4.
- La memoria persistente (`project-google-despacho-mcp.md`) la actualiza Claude en el chat al cerrar.
