# MCP `google-despacho` — F1 (lectura cross-cuenta) · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar la Fase 1 del MCP `google-despacho`: un servidor stdio local FastMCP que da a Cowork/Claude Code **lectura de Drive sobre las dos cuentas** (`@tyukhay.legal` + `@engelvoelkers.com`) a la vez, incluidas todas las unidades compartidas, sin reautenticar al cambiar de cuenta.

**Architecture:** Tres capas calcadas del molde `~/Dev/Gmail MCP Desktop/` y del patrón `plugins/expedientes_xl/`: `google_auth.py` (único que toca OAuth/tokens, multicuenta), `drive_ops.py` (lógica **pura** de Drive; recibe un `service` ya construido; cero dependencia de `mcp`), y `server.py` (wrapper fino FastMCP; cada tool resuelve `account → service` y delega). Tests con `service` **fake inyectado** vía `build_server(service_factory=...)`, sin API viva.

**Tech Stack:** Python 3.14 (venv del repo), `mcp` (FastMCP), `google-api-python-client`, `google-auth`, `google-auth-oauthlib`. Drive API v3. pytest.

---

## Contexto y decisiones que arrastra este plan (no re-litigar)

Del spec `docs/superpowers/specs/2026-07-08-google-despacho-mcp-design.md` y su cierre R2:

- **OAuth (R2, cerrada 2026-07-09):** un solo cliente OAuth, proyecto Cloud de Gmail (`Gmail MCP Despacho`), **External + En producción**, **sin split**, **sin marcar Internal**. Un `credentials.json` único para ambas cuentas. La app en Producción **no** sufre el caduca-7-días. → En F1 hay **un solo** `credentials.json`; el "mapeo por-cuenta" del spec quedó **moot** (mismo proyecto) y **no** se implementa (YAGNI).
- **Scope de F1 (decidido 2026-07-09):** **`drive.readonly`** (mínimo privilegio). Doble restricción calcada de Gmail: scope de solo lectura **+** solo se registran tools de lectura. F2 ampliará a `drive` completo (edición consciente de `google_auth.SCOPES` + una reautorización). Esto **refina** la §3 del spec (que fijaba `drive` completo desde el inicio); la §3 se actualiza al cerrar F1.
- **Entrega:** stdio local + `.dxt` + puente de Claude Desktop (ya verificado con Gmail). El empaquetado `.dxt` es de F-final; F1 se valida vía `claude_desktop_config.json` + Claude Code.
- **`download_file_content` (R3):** escribe a disco local acotado por DL-root (`GOOGLE_DESPACHO_DL_ROOT`), **nunca** base64 al modelo. Solo `read_file_content` devuelve texto.
- **Aislamiento por `account`:** ninguna tool cruza cuentas de forma implícita. Todas las unidades compartidas: `corpora`, `includeItemsFromAllDrives=true`, `supportsAllDrives=true`.
- **Config fuera del repo:** `~/.google-despacho/` (override `GOOGLE_DESPACHO_HOME`), con `credentials.json` y `tokens/<email>.json`.

## Estructura de ficheros (F1)

```
plugins/google_despacho_mcp/
    __init__.py            # marca de paquete (vacío)
    google_auth.py         # OAuth multicuenta; SCOPES=drive.readonly; tokens ~/.google-despacho/tokens/<email>.json
    drive_ops.py           # operaciones PURAS de Drive; `service` inyectado; sin mcp/sin core
    server.py              # FastMCP; build_server(service_factory=...); tools de LECTURA con `account`
    google_cli.py          # add/list/remove cuentas por navegador (OAuth interactivo)
    run_server.bat         # wrapper de arranque (python del repo → server.py, stderr al log)
    requirements.txt
    README.md

tests/
    google_despacho_fakes.py          # doble de `service` googleapiclient (NO test_ → no coleccionado)
    test_google_despacho_auth.py      # helpers puros de google_auth (rutas, listado de cuentas)
    test_google_despacho_drive_ops.py # cada función de drive_ops con FakeService
    test_google_despacho_server.py    # tools vía build_server con service_factory inyectado + _resolve_dest
```

`calendar_ops.py` y las tools de Calendar son **F4**, fuera de este plan.

---

## Task 1: Scaffold del paquete + `google_auth.py` (OAuth multicuenta, solo lectura)

**Files:**
- Create: `plugins/google_despacho_mcp/__init__.py`
- Create: `plugins/google_despacho_mcp/google_auth.py`
- Create: `plugins/google_despacho_mcp/requirements.txt`
- Test: `tests/test_google_despacho_auth.py`

- [ ] **Step 1: Crear la marca de paquete y requirements**

`plugins/google_despacho_mcp/__init__.py` (vacío):

```python
```

`plugins/google_despacho_mcp/requirements.txt`:

```
mcp>=1.0
google-api-python-client>=2.0
google-auth>=2.0
google-auth-oauthlib>=1.0
```

- [ ] **Step 2: Escribir el test que falla (helpers puros de auth)**

`tests/test_google_despacho_auth.py`:

```python
"""Tests de los helpers puros de google_auth (rutas y listado de cuentas).

El flujo OAuth interactivo (add_account) NO se testea aquí: requiere navegador.
Se aísla el HOME con la variable GOOGLE_DESPACHO_HOME apuntando a un tmp_path.
"""
from __future__ import annotations

import importlib

import pytest

from plugins.google_despacho_mcp import google_auth


@pytest.fixture
def auth_home(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_DESPACHO_HOME", str(tmp_path))
    # recargar para que config_home relea la variable si hubiera cache de módulo
    importlib.reload(google_auth)
    return tmp_path


def test_config_home_crea_estructura(auth_home):
    base = google_auth.config_home()
    assert base == auth_home
    assert (auth_home / "tokens").is_dir()


def test_scope_es_solo_lectura(auth_home):
    assert google_auth.SCOPES == [
        "https://www.googleapis.com/auth/drive.readonly"
    ]


def test_list_account_emails_vacio_y_ordenado(auth_home):
    assert google_auth.list_account_emails() == []
    (auth_home / "tokens" / "b@tyukhay.legal.json").write_text("{}")
    (auth_home / "tokens" / "a@engelvoelkers.com.json").write_text("{}")
    assert google_auth.list_account_emails() == [
        "a@engelvoelkers.com",
        "b@tyukhay.legal",
    ]


def test_load_credentials_sin_token_da_error(auth_home):
    with pytest.raises(FileNotFoundError):
        google_auth.load_credentials("nadie@tyukhay.legal")
```

- [ ] **Step 3: Ejecutar el test y verlo fallar**

Run: `python -m pytest tests/test_google_despacho_auth.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'plugins.google_despacho_mcp.google_auth'` (o AttributeError).

- [ ] **Step 4: Implementar `google_auth.py`**

`plugins/google_despacho_mcp/google_auth.py`:

```python
"""Autenticación OAuth y gestión de cuentas para el MCP google-despacho.

SCOPE F1: drive.readonly. SOLO LECTURA. El alcance se fija aquí y NO se
parametriza, para que ampliarlo (F2: escritura) exija una edición consciente
de este fichero.

Config (por defecto ~/.google-despacho, override GOOGLE_DESPACHO_HOME):
    $GOOGLE_DESPACHO_HOME/
        credentials.json              <- secreto OAuth de cliente (App de escritorio); lo aportas tú
        tokens/
            cuenta@dominio.com.json   <- token por cuenta (autogenerado)

Un solo credentials.json para ambas cuentas (R2: un único proyecto Cloud).
"""
from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Alcance deliberadamente restringido a SOLO LECTURA (F1). F2 lo amplía a
# "https://www.googleapis.com/auth/drive" con edición consciente + reautorización.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def config_home() -> Path:
    home = os.environ.get("GOOGLE_DESPACHO_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".google-despacho"
    base.mkdir(parents=True, exist_ok=True)
    (base / "tokens").mkdir(parents=True, exist_ok=True)
    return base


def credentials_path() -> Path:
    return config_home() / "credentials.json"


def tokens_dir() -> Path:
    return config_home() / "tokens"


def _token_path(email: str) -> Path:
    return tokens_dir() / f"{email}.json"


def list_account_emails() -> list[str]:
    return sorted(p.stem for p in tokens_dir().glob("*.json"))


def load_credentials(email: str) -> Credentials:
    path = _token_path(email)
    if not path.exists():
        raise FileNotFoundError(
            f"La cuenta '{email}' no está autenticada. "
            f"Ejecuta: python plugins/google_despacho_mcp/google_cli.py add"
        )
    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json())
    if not creds or not creds.valid:
        raise RuntimeError(
            f"Las credenciales de '{email}' no son válidas. Reautentica: "
            f"python plugins/google_despacho_mcp/google_cli.py add"
        )
    return creds


def build_service(email: str):
    """Construye el cliente de la API de Drive v3 para una cuenta."""
    creds = load_credentials(email)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# --- Operaciones interactivas (uso desde el CLI, NUNCA desde el servidor MCP) ---

def add_account() -> str:
    """Lanza el flujo OAuth en el navegador y guarda el token de una cuenta.

    Devuelve la dirección de correo autenticada (resuelta vía about.get).
    """
    creds_file = credentials_path()
    if not creds_file.exists():
        raise FileNotFoundError(
            f"No existe {creds_file}. Descarga el secreto OAuth de cliente "
            f"(tipo 'App de escritorio') desde Google Cloud Console y guárdalo ahí."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")

    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    about = service.about().get(fields="user(emailAddress)").execute()
    email = about["user"]["emailAddress"]

    _token_path(email).write_text(creds.to_json())
    return email


def remove_account(email: str) -> bool:
    """Elimina el token local. No revoca en Google (hazlo en la cuenta)."""
    path = _token_path(email)
    if path.exists():
        path.unlink()
        return True
    return False
```

- [ ] **Step 5: Ejecutar el test y verlo pasar**

Run: `python -m pytest tests/test_google_despacho_auth.py -q`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add plugins/google_despacho_mcp/__init__.py plugins/google_despacho_mcp/google_auth.py plugins/google_despacho_mcp/requirements.txt tests/test_google_despacho_auth.py
git commit -m "feat(google-despacho): F1 google_auth multicuenta (scope drive.readonly)"
```

---

## Task 2: Doble de test del `service` (FakeService)

**Files:**
- Create: `tests/google_despacho_fakes.py`

- [ ] **Step 1: Escribir el doble (sin prefijo test_ → pytest no lo colecciona)**

`tests/google_despacho_fakes.py`:

```python
"""Doble de test del `service` de googleapiclient (Drive v3).

Imita la interfaz fluida: service.<coleccion>().<metodo>(**kw).execute().
Para media, .execute() devuelve bytes (comportamiento real de get_media/
export_media en googleapiclient). Registra las llamadas para aserciones.
"""
from __future__ import annotations


class _FakeRequest:
    def __init__(self, result):
        self._result = result

    def execute(self):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class _FakeCollection:
    """Resultados enlatados por método.

    `responses`: método -> resultado único, o método -> lista de resultados
    consumidos FIFO (para paginación). Si un método no tiene respuesta, devuelve {}.
    """
    def __init__(self, responses):
        self._responses = {
            k: (list(v) if isinstance(v, list) else v)
            for k, v in (responses or {}).items()
        }
        self.calls = []

    def __getattr__(self, method):
        def _call(**kwargs):
            self.calls.append((method, kwargs))
            resp = self._responses.get(method)
            if isinstance(resp, list):
                result = resp.pop(0) if resp else {}
            else:
                result = {} if resp is None else resp
            return _FakeRequest(result)
        return _call


class FakeService:
    def __init__(self, *, files=None, drives=None, about=None, permissions=None):
        self._c = {
            "files": _FakeCollection(files),
            "drives": _FakeCollection(drives),
            "about": _FakeCollection(about),
            "permissions": _FakeCollection(permissions),
        }

    def files(self):
        return self._c["files"]

    def drives(self):
        return self._c["drives"]

    def about(self):
        return self._c["about"]

    def permissions(self):
        return self._c["permissions"]

    def recorded(self, collection: str):
        """Lista de (metodo, kwargs) llamados sobre una colección."""
        return self._c[collection].calls
```

- [ ] **Step 2: Verificación rápida de import (no hay test propio; lo usan Tasks 3-6)**

Run: `python -c "import sys; sys.path.insert(0,'tests'); from google_despacho_fakes import FakeService; s=FakeService(files={'list':{'files':[]}}); print(s.files().list(q='x').execute()); print(s.recorded('files'))"`
Expected: imprime `{'files': []}` y `[('list', {'q': 'x'})]`.

- [ ] **Step 3: Commit**

```bash
git add tests/google_despacho_fakes.py
git commit -m "test(google-despacho): doble FakeService para drive_ops/server"
```

---

## Task 3: `drive_ops` — listados y búsqueda (`list_shared_drives`, `search_files`, `list_recent_files`, `about_get`)

**Files:**
- Create: `plugins/google_despacho_mcp/drive_ops.py`
- Test: `tests/test_google_despacho_drive_ops.py`

- [ ] **Step 1: Escribir los tests que fallan**

`tests/test_google_despacho_drive_ops.py`:

```python
"""Tests de drive_ops con FakeService inyectado (sin API viva)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # para google_despacho_fakes
from google_despacho_fakes import FakeService  # noqa: E402

from plugins.google_despacho_mcp import drive_ops  # noqa: E402


def test_list_shared_drives_pagina():
    svc = FakeService(drives={"list": [
        {"drives": [{"id": "d1", "name": "EXPEDIENTES"}], "nextPageToken": "T"},
        {"drives": [{"id": "d2", "name": "OTRA"}]},
    ]})
    out = drive_ops.list_shared_drives(svc)
    assert [d["id"] for d in out] == ["d1", "d2"]
    # segunda llamada llevó el pageToken
    assert svc.recorded("drives")[1][1].get("pageToken") == "T"


def test_search_files_pone_flags_alldrives():
    svc = FakeService(files={"list": {"files": [{"id": "f1", "name": "a.pdf"}]}})
    out = drive_ops.search_files(svc, "name contains 'a'")
    assert out == [{"id": "f1", "name": "a.pdf"}]
    _, kw = svc.recorded("files")[0]
    assert kw["includeItemsFromAllDrives"] is True
    assert kw["supportsAllDrives"] is True
    assert kw["corpora"] == "allDrives"
    assert kw["q"] == "name contains 'a'"
    assert "driveId" not in kw


def test_search_files_por_drive_id_usa_corpora_drive():
    svc = FakeService(files={"list": {"files": []}})
    drive_ops.search_files(svc, "x", drive_id="D123")
    _, kw = svc.recorded("files")[0]
    assert kw["corpora"] == "drive"
    assert kw["driveId"] == "D123"


def test_search_files_respeta_max_results_y_pagina():
    svc = FakeService(files={"list": [
        {"files": [{"id": "1"}, {"id": "2"}], "nextPageToken": "T"},
        {"files": [{"id": "3"}]},
    ]})
    out = drive_ops.search_files(svc, "x", page_size=2, max_results=3)
    assert [f["id"] for f in out] == ["1", "2", "3"]


def test_list_recent_files_ordena_por_modified():
    svc = FakeService(files={"list": {"files": [{"id": "f1"}]}})
    out = drive_ops.list_recent_files(svc, page_size=5)
    assert out == [{"id": "f1"}]
    _, kw = svc.recorded("files")[0]
    assert kw["orderBy"] == "modifiedTime desc"
    assert kw["q"] == "trashed = false"


def test_about_get():
    svc = FakeService(about={"get": {"user": {"emailAddress": "n@tyukhay.legal"}}})
    out = drive_ops.about_get(svc)
    assert out["user"]["emailAddress"] == "n@tyukhay.legal"
```

- [ ] **Step 2: Ejecutar y verlo fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops.py -q`
Expected: FAIL — `ModuleNotFoundError` / `AttributeError` (drive_ops aún no existe).

- [ ] **Step 3: Implementar la primera mitad de `drive_ops.py`**

`plugins/google_despacho_mcp/drive_ops.py`:

```python
"""Operaciones PURAS de Google Drive v3.

Sin dependencia de `mcp` ni de `core/`: cada función recibe un `service` ya
construido (googleapiclient) e implementa una operación de lectura. Testeable
con un `service` fake inyectado. Todas las lecturas abarcan unidades
compartidas (corpora=allDrives, includeItemsFromAllDrives, supportsAllDrives).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

FILE_FIELDS = (
    "id, name, mimeType, size, modifiedTime, createdTime, parents, driveId, "
    "webViewLink, sha256Checksum, trashed, owners(emailAddress)"
)
PERM_FIELDS = (
    "permissions(id, type, role, emailAddress, domain, displayName, deleted)"
)

GOOGLE_NATIVE_PREFIX = "application/vnd.google-apps."
_EXPORT_TEXT = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}
_EXPORT_PDF = {
    "application/vnd.google-apps.document": "application/pdf",
    "application/vnd.google-apps.spreadsheet": "application/pdf",
    "application/vnd.google-apps.presentation": "application/pdf",
    "application/vnd.google-apps.drawing": "application/pdf",
}
_EXPORT_OFFICE = {
    "application/vnd.google-apps.document":
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.google-apps.spreadsheet":
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.google-apps.presentation":
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
_TEXTUAL_MIMES = {"application/json", "application/xml", "application/rtf", "text/csv"}


def list_shared_drives(service, *, page_size: int = 100) -> list[dict]:
    drives: list[dict] = []
    page_token = None
    while True:
        params = {"pageSize": min(page_size, 100),
                  "fields": "nextPageToken, drives(id, name)"}
        if page_token:
            params["pageToken"] = page_token
        resp = service.drives().list(**params).execute()
        drives.extend(resp.get("drives", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return drives


def search_files(service, query: str, *, page_size: int = 50,
                 drive_id: str | None = None, order_by: str | None = None,
                 max_results: int | None = None) -> list[dict]:
    files: list[dict] = []
    page_token = None
    while True:
        params = {
            "q": query,
            "pageSize": min(page_size, 1000),
            "fields": f"nextPageToken, files({FILE_FIELDS})",
            "includeItemsFromAllDrives": True,
            "supportsAllDrives": True,
            "spaces": "drive",
        }
        if drive_id:
            params["corpora"] = "drive"
            params["driveId"] = drive_id
        else:
            params["corpora"] = "allDrives"
        if order_by:
            params["orderBy"] = order_by
        if page_token:
            params["pageToken"] = page_token
        resp = service.files().list(**params).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token or (max_results and len(files) >= max_results):
            break
    return files[:max_results] if max_results else files


def list_recent_files(service, *, page_size: int = 20) -> list[dict]:
    resp = service.files().list(
        pageSize=min(page_size, 1000),
        orderBy="modifiedTime desc",
        q="trashed = false",
        fields=f"files({FILE_FIELDS})",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        corpora="allDrives",
        spaces="drive",
    ).execute()
    return resp.get("files", [])


def about_get(service, *,
              fields: str = "user(displayName, emailAddress), storageQuota") -> dict:
    return service.about().get(fields=fields).execute()
```

- [ ] **Step 4: Ejecutar y verlo pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py tests/test_google_despacho_drive_ops.py
git commit -m "feat(google-despacho): F1 drive_ops listados/búsqueda (allDrives)"
```

---

## Task 4: `drive_ops` — metadatos y permisos (`get_file_metadata`, `get_file_permissions`)

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py` (añadir 2 funciones)
- Test: `tests/test_google_despacho_drive_ops.py` (añadir tests)

- [ ] **Step 1: Añadir tests que fallan**

Añadir al final de `tests/test_google_despacho_drive_ops.py`:

```python
def test_get_file_metadata_pide_supports_alldrives():
    svc = FakeService(files={"get": {"id": "f1", "name": "x.pdf", "mimeType": "application/pdf"}})
    out = drive_ops.get_file_metadata(svc, "f1")
    assert out["id"] == "f1"
    _, kw = svc.recorded("files")[0]
    assert kw["fileId"] == "f1"
    assert kw["supportsAllDrives"] is True
    assert "sha256Checksum" in kw["fields"]


def test_get_file_permissions_pagina():
    svc = FakeService(permissions={"list": [
        {"permissions": [{"id": "p1", "type": "user", "role": "writer"}], "nextPageToken": "T"},
        {"permissions": [{"id": "p2", "type": "anyone", "role": "reader"}]},
    ]})
    out = drive_ops.get_file_permissions(svc, "f1")
    assert [p["id"] for p in out] == ["p1", "p2"]
    _, kw0 = svc.recorded("permissions")[0]
    assert kw0["fileId"] == "f1"
    assert kw0["supportsAllDrives"] is True
```

- [ ] **Step 2: Ejecutar y verlo fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops.py -q`
Expected: FAIL — `AttributeError: module 'drive_ops' has no attribute 'get_file_metadata'`.

- [ ] **Step 3: Añadir las funciones a `drive_ops.py`** (tras `about_get`)

```python
def get_file_metadata(service, file_id: str, *, fields: str | None = None) -> dict:
    return service.files().get(
        fileId=file_id,
        fields=fields or FILE_FIELDS,
        supportsAllDrives=True,
    ).execute()


def get_file_permissions(service, file_id: str) -> list[dict]:
    perms: list[dict] = []
    page_token = None
    while True:
        params = {
            "fileId": file_id,
            "supportsAllDrives": True,
            "pageSize": 100,
            "fields": f"nextPageToken, {PERM_FIELDS}",
        }
        if page_token:
            params["pageToken"] = page_token
        resp = service.permissions().list(**params).execute()
        perms.extend(resp.get("permissions", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return perms
```

- [ ] **Step 4: Ejecutar y verlo pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py tests/test_google_despacho_drive_ops.py
git commit -m "feat(google-despacho): F1 drive_ops metadatos + permisos"
```

---

## Task 5: `drive_ops` — contenido (`read_file_content`, `download_file_content`)

**Files:**
- Modify: `plugins/google_despacho_mcp/drive_ops.py` (añadir 2 funciones)
- Test: `tests/test_google_despacho_drive_ops.py` (añadir tests)

- [ ] **Step 1: Añadir tests que fallan**

Añadir al final de `tests/test_google_despacho_drive_ops.py`:

```python
def test_read_file_content_doc_nativo_exporta_texto():
    svc = FakeService(files={
        "get": {"id": "g1", "name": "Nota", "mimeType": "application/vnd.google-apps.document"},
        "export_media": b"hola mundo",
    })
    out = drive_ops.read_file_content(svc, "g1")
    assert out["text"] == "hola mundo"
    assert out["mime_type"] == "application/vnd.google-apps.document"
    _, kw = svc.recorded("files")[-1]
    assert kw["mimeType"] == "text/plain"


def test_read_file_content_texto_plano():
    svc = FakeService(files={
        "get": {"id": "t1", "name": "a.txt", "mimeType": "text/plain", "size": "5"},
        "get_media": b"plano",
    })
    out = drive_ops.read_file_content(svc, "t1")
    assert out["text"] == "plano"


def test_read_file_content_binario_rechaza():
    svc = FakeService(files={
        "get": {"id": "b1", "name": "x.pdf", "mimeType": "application/pdf", "size": "10"},
    })
    with pytest.raises(ValueError):
        drive_ops.read_file_content(svc, "b1")


def test_download_file_content_binario_escribe_y_hashea(tmp_path):
    import hashlib as _h
    data = b"binario-de-prueba"
    svc = FakeService(files={
        "get": {"id": "b1", "name": "x.bin", "mimeType": "application/octet-stream", "size": str(len(data))},
        "get_media": data,
    })
    dest = tmp_path / "sub" / "x.bin"
    out = drive_ops.download_file_content(svc, "b1", str(dest))
    assert dest.read_bytes() == data
    assert out["bytes"] == len(data)
    assert out["sha256"] == _h.sha256(data).hexdigest()


def test_download_file_content_doc_nativo_default_pdf(tmp_path):
    svc = FakeService(files={
        "get": {"id": "g1", "name": "Doc", "mimeType": "application/vnd.google-apps.document"},
        "export_media": b"%PDF-1.4 fake",
    })
    dest = tmp_path / "doc.pdf"
    drive_ops.download_file_content(svc, "g1", str(dest))
    _, kw = svc.recorded("files")[-1]
    assert kw["mimeType"] == "application/pdf"
    assert dest.read_bytes() == b"%PDF-1.4 fake"


def test_download_file_content_keep_editable_office(tmp_path):
    svc = FakeService(files={
        "get": {"id": "g1", "name": "Doc", "mimeType": "application/vnd.google-apps.document"},
        "export_media": b"docx-bytes",
    })
    dest = tmp_path / "doc.docx"
    drive_ops.download_file_content(svc, "g1", str(dest), keep_editable=True)
    _, kw = svc.recorded("files")[-1]
    assert kw["mimeType"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_download_file_content_supera_max_bytes(tmp_path):
    data = b"x" * 100
    svc = FakeService(files={
        "get": {"id": "b1", "name": "x.bin", "mimeType": "application/octet-stream", "size": "100"},
        "get_media": data,
    })
    with pytest.raises(ValueError):
        drive_ops.download_file_content(svc, "b1", str(tmp_path / "x.bin"), max_bytes=10)
```

- [ ] **Step 2: Ejecutar y verlo fallar**

Run: `python -m pytest tests/test_google_despacho_drive_ops.py -q`
Expected: FAIL — `AttributeError: ... 'read_file_content'`.

- [ ] **Step 3: Añadir las funciones a `drive_ops.py`** (tras `get_file_permissions`)

```python
def read_file_content(service, file_id: str, *, max_bytes: int = 5_000_000) -> dict:
    """Devuelve el TEXTO de un fichero: Doc nativo exportado a texto, o fichero
    de texto plano. Los binarios se rechazan (usa download_file_content)."""
    meta = get_file_metadata(service, file_id, fields="id, name, mimeType, size")
    mime = meta.get("mimeType", "")
    name = meta.get("name", "")
    if mime.startswith(GOOGLE_NATIVE_PREFIX):
        export_mime = _EXPORT_TEXT.get(mime)
        if not export_mime:
            raise ValueError(
                f"El Doc nativo {mime!r} no es exportable a texto; "
                f"usa download_file_content."
            )
        data = service.files().export_media(fileId=file_id, mimeType=export_mime).execute()
    else:
        if not (mime.startswith("text/") or mime in _TEXTUAL_MIMES):
            raise ValueError(
                f"El fichero {mime!r} no es de texto; usa download_file_content."
            )
        size = int(meta.get("size") or 0)
        if max_bytes and size > max_bytes:
            raise ValueError(f"{size} bytes supera max_bytes ({max_bytes}).")
        data = service.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
    if isinstance(data, (bytes, bytearray)):
        if max_bytes and len(data) > max_bytes:
            raise ValueError(f"{len(data)} bytes supera max_bytes ({max_bytes}).")
        text = bytes(data).decode("utf-8", "replace")
    else:
        text = str(data)
    return {"id": file_id, "name": name, "mime_type": mime, "text": text}


def download_file_content(service, file_id: str, dest_path: str, *,
                          max_bytes: int = 100_000_000,
                          keep_editable: bool = False) -> dict:
    """Descarga a `dest_path` (ruta absoluta ya saneada por el server). Doc
    nativo → export (default PDF; keep_editable → Office). Devuelve path,
    bytes y sha256 del artefacto realmente guardado."""
    meta = get_file_metadata(
        service, file_id, fields="id, name, mimeType, size, sha256Checksum"
    )
    mime = meta.get("mimeType", "")
    if mime.startswith(GOOGLE_NATIVE_PREFIX):
        table = _EXPORT_OFFICE if keep_editable else _EXPORT_PDF
        export_mime = table.get(mime)
        if not export_mime:
            raise ValueError(f"El Doc nativo {mime!r} no tiene export soportado.")
        data = service.files().export_media(fileId=file_id, mimeType=export_mime).execute()
    else:
        size = int(meta.get("size") or 0)
        if max_bytes and size > max_bytes:
            raise ValueError(f"{size} bytes supera max_bytes ({max_bytes}).")
        data = service.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("La API no devolvió bytes al descargar.")
    if max_bytes and len(data) > max_bytes:
        raise ValueError(f"{len(data)} bytes supera max_bytes ({max_bytes}).")
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {
        "path": str(dest),
        "bytes": len(data),
        "mime_type": mime,
        "sha256": hashlib.sha256(bytes(data)).hexdigest(),
    }
```

- [ ] **Step 4: Ejecutar y verlo pasar**

Run: `python -m pytest tests/test_google_despacho_drive_ops.py -q`
Expected: PASS (15 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/google_despacho_mcp/drive_ops.py tests/test_google_despacho_drive_ops.py
git commit -m "feat(google-despacho): F1 drive_ops read/download (export Docs + hash)"
```

---

## Task 6: `server.py` — FastMCP, `build_server`, tools de lectura, DL-root

**Files:**
- Create: `plugins/google_despacho_mcp/server.py`
- Test: `tests/test_google_despacho_server.py`

- [ ] **Step 1: Escribir los tests que fallan**

`tests/test_google_despacho_server.py`:

```python
"""Tests del server MCP google-despacho vía build_server con service_factory
inyectado (sin API viva ni tokens). Comprueba enrutado account→service,
delegación a drive_ops y saneado del DL-root."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_despacho_fakes import FakeService  # noqa: E402

from plugins.google_despacho_mcp import server as srv  # noqa: E402


def _factory(mapping):
    """Devuelve un service_factory(email)->FakeService a partir de un dict."""
    def factory(email):
        if email not in mapping:
            raise FileNotFoundError(email)
        return mapping[email]
    return factory


def _tool(mcp, name):
    """Extrae la función Python subyacente de una tool registrada en FastMCP."""
    # FastMCP guarda las tools en un gestor interno; usamos la API pública.
    return mcp


def test_build_server_devuelve_fastmcp():
    mcp = srv.build_server(
        service_factory=lambda e: FakeService(),
        account_lister=lambda: ["a@tyukhay.legal"],
    )
    assert mcp is not None
    assert mcp.name == "google-despacho"


def test_resolve_dest_confina_a_dl_root(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_DESPACHO_DL_ROOT", str(tmp_path))
    ok = srv._resolve_dest(str(tmp_path / "sub" / "a.bin"))
    assert Path(ok).is_absolute()
    with pytest.raises(ValueError):
        srv._resolve_dest(str(tmp_path.parent / "fuera.bin"))


def test_resolve_accounts_todas_si_omitido():
    lister = lambda: ["a@tyukhay.legal", "b@engelvoelkers.com"]
    assert srv._resolve_accounts(None, lister) == [
        "a@tyukhay.legal", "b@engelvoelkers.com"
    ]
    assert srv._resolve_accounts("a@tyukhay.legal", lister) == ["a@tyukhay.legal"]


def test_resolve_accounts_sin_cuentas_da_error():
    with pytest.raises(RuntimeError):
        srv._resolve_accounts(None, lambda: [])
```

Nota: FastMCP no expone trivialmente las funciones registradas para invocarlas
como Python plano; por eso los tests de comportamiento de las tools se hacen
sobre las **funciones puras helper** del server (`_resolve_dest`,
`_resolve_accounts`) y sobre `drive_ops` (Task 3-5). La cobertura extremo-a-extremo
de las tools es el check de integración manual (Task 9). Esto sigue el patrón de
`tests/test_email_export_mcp_server.py` (que testea la lógica, no el transporte MCP).

- [ ] **Step 2: Ejecutar y verlo fallar**

Run: `python -m pytest tests/test_google_despacho_server.py -q`
Expected: FAIL — `ModuleNotFoundError: ... server`.

- [ ] **Step 3: Implementar `server.py`**

`plugins/google_despacho_mcp/server.py`:

```python
#!/usr/bin/env python3
"""Servidor MCP `google-despacho` — F1: LECTURA de Drive multicuenta.

Doble restricción (calcada de Gmail-despacho): scope OAuth drive.readonly +
solo se registran tools de LECTURA. Ninguna operación de escritura/borrado/
permisos existe en F1.

Selección de cuenta: las tools aceptan `account` (email). En búsquedas/listados
se puede omitir para consultar TODAS las cuentas conectadas (cada resultado se
etiqueta con su cuenta). Las tools por-fichero exigen `account` explícito.

download_file_content escribe a disco (confinable con GOOGLE_DESPACHO_DL_ROOT);
nunca devuelve bytes por el modelo.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Optional

from mcp.server.fastmcp import FastMCP

# Import dual-modo: como paquete (tests) o standalone (Claude Desktop).
try:
    from . import drive_ops, google_auth
except ImportError:  # ejecución directa: python server.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import drive_ops  # type: ignore  # noqa: E402
    import google_auth  # type: ignore  # noqa: E402


def _resolve_accounts(account: Optional[str], lister: Callable[[], list[str]]) -> list[str]:
    if account:
        return [account]
    accounts = lister()
    if not accounts:
        raise RuntimeError(
            "No hay cuentas conectadas. Añade alguna con: "
            "python plugins/google_despacho_mcp/google_cli.py add"
        )
    return accounts


def _resolve_dest(dest_path: str) -> str:
    """Resuelve y valida la ruta de descarga; si GOOGLE_DESPACHO_DL_ROOT está
    definida, el destino debe quedar dentro de esa raíz."""
    dest = os.path.abspath(os.path.expanduser(dest_path))
    root = os.environ.get("GOOGLE_DESPACHO_DL_ROOT")
    if root:
        root_abs = os.path.abspath(os.path.expanduser(root))
        if os.path.commonpath([root_abs, dest]) != root_abs:
            raise ValueError(f"Destino fuera de GOOGLE_DESPACHO_DL_ROOT ({root_abs}): {dest}")
    return dest


def build_server(
    *,
    service_factory: Callable[[str], object] | None = None,
    account_lister: Callable[[], list[str]] | None = None,
) -> FastMCP:
    """Construye el servidor. `service_factory`/`account_lister` son puntos de
    inyección para tests; en producción se toman de google_auth."""
    if service_factory is None:
        service_factory = google_auth.build_service
    if account_lister is None:
        account_lister = google_auth.list_account_emails

    mcp = FastMCP("google-despacho")

    @mcp.tool()
    def list_accounts() -> list[str]:
        """Lista las cuentas de Google conectadas a este servidor."""
        return account_lister()

    @mcp.tool()
    def list_shared_drives(account: Optional[str] = None) -> dict:
        """Lista las unidades compartidas accesibles por cada cuenta."""
        out: dict[str, list[dict]] = {}
        for acc in _resolve_accounts(account, account_lister):
            out[acc] = drive_ops.list_shared_drives(service_factory(acc))
        return out

    @mcp.tool()
    def search_files(
        query: str,
        account: Optional[str] = None,
        drive_id: Optional[str] = None,
        max_results: int = 50,
    ) -> list[dict]:
        """Busca ficheros con la sintaxis de query de Drive v3 (abarca unidades
        compartidas). `query` p.ej. "name contains 'arras' and trashed = false".
        Omite `account` para buscar en TODAS las cuentas. `drive_id` acota a una
        unidad compartida concreta."""
        results: list[dict] = []
        for acc in _resolve_accounts(account, account_lister):
            found = drive_ops.search_files(
                service_factory(acc), query, drive_id=drive_id, max_results=max_results
            )
            for f in found:
                f["account"] = acc
            results.extend(found)
        return results

    @mcp.tool()
    def list_recent_files(account: Optional[str] = None, max_results: int = 20) -> list[dict]:
        """Ficheros modificados recientemente (por cuenta)."""
        results: list[dict] = []
        for acc in _resolve_accounts(account, account_lister):
            found = drive_ops.list_recent_files(service_factory(acc), page_size=max_results)
            for f in found:
                f["account"] = acc
            results.extend(found)
        return results

    @mcp.tool()
    def get_file_metadata(file_id: str, account: str) -> dict:
        """Metadatos de un fichero (incluye sha256Checksum si es binario)."""
        return drive_ops.get_file_metadata(service_factory(account), file_id)

    @mcp.tool()
    def get_file_permissions(file_id: str, account: str) -> list[dict]:
        """Lista los permisos (ACL) de un fichero: type/role/emailAddress/domain."""
        return drive_ops.get_file_permissions(service_factory(account), file_id)

    @mcp.tool()
    def read_file_content(file_id: str, account: str, max_bytes: int = 5_000_000) -> dict:
        """Devuelve el TEXTO de un Doc nativo (exportado) o de un fichero de
        texto. Los binarios se rechazan: usa download_file_content."""
        return drive_ops.read_file_content(service_factory(account), file_id, max_bytes=max_bytes)

    @mcp.tool()
    def download_file_content(
        file_id: str,
        account: str,
        dest_path: str,
        max_bytes: int = 100_000_000,
        keep_editable: bool = False,
    ) -> dict:
        """Descarga un fichero a disco local (Doc nativo → PDF por defecto;
        keep_editable → Office). Confinable con GOOGLE_DESPACHO_DL_ROOT. Nunca
        devuelve los bytes por el modelo; devuelve ruta, tamaño y sha256."""
        dest = _resolve_dest(dest_path)
        return drive_ops.download_file_content(
            service_factory(account), file_id, dest,
            max_bytes=max_bytes, keep_editable=keep_editable,
        )

    @mcp.tool()
    def about_get(account: str) -> dict:
        """Info de la cuenta y cuota de almacenamiento (about.get)."""
        return drive_ops.about_get(service_factory(account))

    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Ejecutar y verlo pasar**

Run: `python -m pytest tests/test_google_despacho_server.py -q`
Expected: PASS (4 tests). Si `mcp.name` no fuese el atributo correcto en la versión instalada, ajustar la aserción de `test_build_server_devuelve_fastmcp` a `assert mcp is not None` y comprobar el nombre con el atributo que exponga esa versión (`python -c "from mcp.server.fastmcp import FastMCP; print([a for a in dir(FastMCP('x')) if 'name' in a.lower()])"`).

- [ ] **Step 5: Suite completa (no romper nada)**

Run: `python -m pytest -q --tb=short`
Expected: PASS — el total previo (1556) + los nuevos tests de google-despacho.

- [ ] **Step 6: Commit**

```bash
git add plugins/google_despacho_mcp/server.py tests/test_google_despacho_server.py
git commit -m "feat(google-despacho): F1 server FastMCP con tools de lectura + DL-root"
```

---

## Task 7: `google_cli.py` — alta/baja de cuentas por navegador

**Files:**
- Create: `plugins/google_despacho_mcp/google_cli.py`

(Sin tests unitarios: el flujo OAuth exige navegador; se valida en Task 9. Los
helpers puros que usa ya están cubiertos en Task 1.)

- [ ] **Step 1: Implementar el CLI**

`plugins/google_despacho_mcp/google_cli.py`:

```python
#!/usr/bin/env python3
"""Gestión de cuentas de google-despacho desde la terminal.

El flujo OAuth necesita navegador → el alta se hace aquí, nunca desde el server.

    python plugins/google_despacho_mcp/google_cli.py add            # autentica una cuenta (abre navegador)
    python plugins/google_despacho_mcp/google_cli.py list           # lista cuentas conectadas
    python plugins/google_despacho_mcp/google_cli.py remove EMAIL    # elimina el token local
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import google_auth  # noqa: E402


def cmd_add() -> None:
    print("Se abrirá el navegador para autenticar la cuenta (SOLO LECTURA de Drive)...")
    email = google_auth.add_account()
    print(f"OK · cuenta conectada: {email}")
    print(f"Token guardado en: {google_auth.tokens_dir() / (email + '.json')}")


def cmd_list() -> None:
    accounts = google_auth.list_account_emails()
    if not accounts:
        print("(sin cuentas conectadas)")
        return
    print("Cuentas conectadas:")
    for a in accounts:
        print(f"  - {a}")


def cmd_remove(email: str) -> None:
    if google_auth.remove_account(email):
        print(f"Token eliminado: {email}")
        print("Revoca también en https://myaccount.google.com/permissions "
              "si quieres invalidarlo en Google.")
    else:
        print(f"No existe token para: {email}")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    cmd = args[0]
    if cmd == "add":
        cmd_add()
    elif cmd == "list":
        cmd_list()
    elif cmd == "remove":
        if len(args) < 2:
            print("Uso: python google_cli.py remove EMAIL")
            sys.exit(1)
        cmd_remove(args[1])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verificar que arranca (muestra la ayuda)**

Run: `python plugins/google_despacho_mcp/google_cli.py`
Expected: imprime el docstring de uso y sale con código 1.

- [ ] **Step 3: Commit**

```bash
git add plugins/google_despacho_mcp/google_cli.py
git commit -m "feat(google-despacho): F1 CLI de alta/baja de cuentas (OAuth navegador)"
```

---

## Task 8: Arranque, dependencias y README

**Files:**
- Create: `plugins/google_despacho_mcp/run_server.bat`
- Create: `plugins/google_despacho_mcp/README.md`

- [ ] **Step 1: Wrapper de arranque** (calcado de `plugins/email_export_mcp/run_server.bat`; usa el Python del sistema, no el venv, porque Claude Desktop lo lanza fuera del repo — ajustar la ruta de Python si difiere en la máquina)

`plugins/google_despacho_mcp/run_server.bat`:

```bat
@echo off
REM Wrapper de arranque del MCP google-despacho para Claude Desktop.
REM stdout (fd1) queda para el pipe JSON-RPC de MCP; stderr al log.
REM Si el interprete no esta en esta ruta, editar la linea de abajo.
C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe "%~dp0server.py" 2>>"%APPDATA%\Claude\google-despacho-mcp.log"
```

- [ ] **Step 2: README con setup**

`plugins/google_despacho_mcp/README.md`:

````markdown
# MCP `google-despacho` — F1 (lectura de Drive multicuenta)

Servidor stdio local (FastMCP) que da lectura de Google Drive sobre varias
cuentas a la vez (`@tyukhay.legal` + `@engelvoelkers.com`), incluidas todas las
unidades compartidas, sin reautenticar al cambiar de cuenta.

**F1 es SOLO LECTURA**: scope `drive.readonly` + solo tools de lectura. La
escritura llega en F2.

## Prerrequisitos (una vez)

1. En Google Cloud Console (proyecto `Gmail MCP Despacho`, el mismo de Gmail):
   habilitar **Google Drive API**. La pantalla de consentimiento ya está
   `En producción` (R2) → no hay caduca-7-días.
2. Descargar el secreto OAuth de cliente (tipo **App de escritorio**) →
   guardarlo como `~/.google-despacho/credentials.json`
   (o `$GOOGLE_DESPACHO_HOME/credentials.json`). Puede ser el mismo cliente que Gmail.
3. Instalar dependencias en el intérprete que usará el server:
   `python -m pip install -r plugins/google_despacho_mcp/requirements.txt`

## Conectar las cuentas

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python plugins\google_despacho_mcp\google_cli.py add   # repetir para cada cuenta
python plugins\google_despacho_mcp\google_cli.py list
```

Al autorizar aparecerá el aviso **"Google no ha verificado esta app"** (app sin
verificar, scope restringido) → *Configuración avanzada → Ir a … (no seguro)*.
Es esperado; tope de 100 usuarios, sobra para 2.

## Registrar en Claude Desktop

En `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-despacho": {
      "command": "C:\\Users\\tnm33\\Dev\\FeesDefender\\plugins\\google_despacho_mcp\\run_server.bat"
    }
  }
}
```

Reiniciar Claude Desktop. El puente expone el conector a Cowork/claude.ai
(igual que Gmail). Requisito operativo: PC encendido + app de escritorio + puente.

## Ejecutar desde Claude Code

Añadir a la config MCP de Claude Code el mismo comando, o lanzar
`python plugins/google_despacho_mcp/server.py` como server stdio.

## Variables de entorno

- `GOOGLE_DESPACHO_HOME` — raíz de config (default `~/.google-despacho`).
- `GOOGLE_DESPACHO_DL_ROOT` — si se define, confina los destinos de
  `download_file_content` a esa carpeta.

## Tools (F1)

`list_accounts`, `list_shared_drives`, `search_files`, `list_recent_files`,
`get_file_metadata`, `get_file_permissions`, `read_file_content`,
`download_file_content`, `about_get`. Todas aceptan `account`; las de búsqueda/
listado lo omiten para consultar todas las cuentas.
````

- [ ] **Step 3: Commit**

```bash
git add plugins/google_despacho_mcp/run_server.bat plugins/google_despacho_mcp/README.md
git commit -m "docs(google-despacho): F1 wrapper de arranque + README de setup"
```

---

## Task 9: Check de integración manual + cableado (no automatizable)

Estos pasos exigen navegador, tokens reales y Drive vivo; **no** son tests
pytest. Ejecutar en la máquina de Nikolai. Anotar el resultado en el commit de cierre.

- [ ] **Step 1: Instalar dependencias y conectar las dos cuentas**

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m pip install -r plugins\google_despacho_mcp\requirements.txt
python plugins\google_despacho_mcp\google_cli.py add    # @tyukhay.legal
python plugins\google_despacho_mcp\google_cli.py add    # @engelvoelkers.com
python plugins\google_despacho_mcp\google_cli.py list
```
Expected: `list` muestra las dos cuentas.

- [ ] **Step 2: Humo local del server sobre Drive real** (script de un solo uso)

```powershell
python -c "import sys; sys.path.insert(0,'plugins/google_despacho_mcp'); import google_auth, drive_ops; svc=google_auth.build_service('nikolai.tyukhay@tyukhay.legal'); print('unidades:', [d['name'] for d in drive_ops.list_shared_drives(svc)]); print('recientes:', [f['name'] for f in drive_ops.list_recent_files(svc, page_size=5)])"
```
Expected: imprime la unidad «EXPEDIENTES - TYUKHAY LEGAL» entre las unidades compartidas, y 5 ficheros recientes. Repetir con la cuenta `@engelvoelkers.com` (verá su My Drive + lo compartido con ella).

- [ ] **Step 3: Cablear en Claude Desktop y verificar por el puente**

Añadir la entrada `google-despacho` a `claude_desktop_config.json` (ver README),
reiniciar Claude Desktop, y en una sesión de Cowork/claude.ai invocar
`list_accounts` → debe devolver las dos cuentas. Comprobar el log
`%APPDATA%\Claude\google-despacho-mcp.log` si no aparece.

- [ ] **Step 4: Prueba end-to-end de lectura contra un fichero desechable**

En Cowork: `search_files(query="name contains '<algo conocido>'")` sin `account`
→ resultados de ambas cuentas etiquetados. `read_file_content` de un Google Doc
de prueba → texto. `download_file_content` de un binario pequeño a una carpeta
bajo `GOOGLE_DESPACHO_DL_ROOT` → devuelve path + sha256, y el fichero aparece en disco.

- [ ] **Step 5: Cerrar F1**

- Actualizar el spec §3 (nota: F1 usó `drive.readonly`; F2 amplía a `drive`).
- Marcar F1 hecha en `PLAN.md` (entrada `[SIGUIENTE-GOOGLE-MCP]`) con el hash del PR.
- Registrar el hito en `STATUS.md`.
- Abrir PR de la rama `feat/google-despacho-mcp` a `main` (debe pasar `leak-scan`).

---

## Self-Review

**1. Cobertura del spec (F1):**
- Tools F1 del §4 (`list_accounts`, `list_shared_drives`, `search_files`, `list_recent_files`, `get_file_metadata`, `get_file_permissions`, `read_file_content`, `download_file_content`, `about.get`) → todas registradas en Task 6. ✔
- Unidades compartidas (`corpora=allDrives`, `includeItemsFromAllDrives`, `supportsAllDrives`) → Task 3/4, testeado. ✔
- Aislamiento por `account` (§5) → `_resolve_accounts`, cada tool resuelve service por cuenta; ningún cruce implícito. ✔
- Bytes nunca por el modelo / DL-root (R3, §5) → `download_file_content` escribe a disco, `_resolve_dest` confina; solo `read_file_content` devuelve texto. ✔
- Export de Docs nativos (§6): default PDF, `keep_editable`→Office, hash del artefacto guardado → Task 5, testeado. ✔
- OAuth un solo cliente + scope fijado en `google_auth` (R2 + decisión de scope) → Task 1. ✔ (F1 = `drive.readonly`, refina §3; documentado.)
- DI para tests con `service` fake (§8) → `build_server(service_factory=...)` + FakeService. ✔
- Estructura de ficheros (§2) → Task 1-8 crean todo salvo `calendar_ops.py` (F4, fuera de alcance). ✔

**2. Placeholders:** revisado — no hay "TBD"/"implementar luego"/"manejar errores apropiadamente". Task 9 es manual **por naturaleza** (OAuth + Drive vivo) y lleva comandos concretos, no placeholders.

**3. Consistencia de tipos/nombres:** `service_factory(email)->service`, `account_lister()->list[str]`, `drive_ops.*` con firma `(service, ...)`; nombres de tool == nombres del spec §4 (`about_get` es el `about.get` del spec, renombrado a identificador Python válido — anotado). `FILE_FIELDS`/`PERM_FIELDS`/`_EXPORT_*` definidos una vez en `drive_ops` y reutilizados. Sin discrepancias.

**Nota de reconciliación con el spec:** la §3 del spec (scope `drive` completo, "External+Testing") queda **superada** por R2 (§11, que prevalece) y por la decisión de scope de F1 (`drive.readonly`). Task 9 Step 5 incluye actualizar la §3 al cerrar F1.

---

## Execution Handoff

**Plan completo y guardado en `docs/superpowers/plans/2026-07-09-google-despacho-mcp-f1.md`. Dos opciones de ejecución:**

**1. Subagent-Driven (recomendada)** — despacho un subagente fresco por tarea, reviso entre tareas, iteración rápida.

**2. Inline Execution** — ejecuto las tareas en esta sesión con executing-plans, por lotes con checkpoints de revisión.

**¿Qué enfoque?**
