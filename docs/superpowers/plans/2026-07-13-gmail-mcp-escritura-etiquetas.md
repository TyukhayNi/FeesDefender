# Gmail MCP — escritura de etiquetas + migración a `plugins/` · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrar el MCP de Gmail (`~/Dev/Gmail MCP Desktop/`) al repo (`plugins/gmail_mcp/`) y ampliarlo de solo-lectura a lectura + etiquetado (crear / aplicar / quitar etiquetas de usuario), multicuenta, con guardarraíles fail-closed.

**Architecture:** Gemelo de `plugins/google_despacho_mcp/` (F1→F2). `gmail_auth.py` fija el scope OAuth (`gmail.modify`) y gestiona tokens por cuenta en `~/.gmail-mcp/` (config-home INALTERADO). `server.py` expone las tools vía `build_server(service_factory=…, account_lister=…)` — inyección de dependencias que permite testear con un `service` falso sin tocar Gmail. Los guardarraíles viven en helpers puros a nivel de módulo (espíritu del `allow_external` de google-despacho): solo etiquetas de usuario, `account` obligatorio en escritura, sin borrado/envío/archivar.

**Tech Stack:** Python 3.10+, `mcp` (FastMCP), `google-api-python-client`, `google-auth`, `google-auth-oauthlib`; pytest con service inyectado.

**Spec:** `docs/superpowers/specs/2026-07-13-gmail-mcp-escritura-etiquetas-design.md` (commit `3df616f`).

**Rama / worktree:** `feat/gmail-mcp-escritura` en `C:\Users\tnm33\Dev\FeesDefender\.claude\worktrees\gmail-mcp-write`. Todos los comandos `python`/`pytest` se ejecutan desde la RAÍZ del worktree. En la Bash tool, usar barras normales en rutas.

---

## Estructura de ficheros

**Crear:**
- `plugins/gmail_mcp/__init__.py` — marca el paquete (vacío).
- `plugins/gmail_mcp/gmail_auth.py` — scope `gmail.modify`, tokens, OAuth (add/list/remove).
- `plugins/gmail_mcp/server.py` — FastMCP vía `build_server(...)`: tools de lectura (migradas) + etiquetado (nuevas) + guardarraíles.
- `plugins/gmail_mcp/gmail_cli.py` — alta/listado/baja de cuentas (flujo OAuth en navegador).
- `plugins/gmail_mcp/run_server.bat` — arranque robusto para Claude Desktop (stderr al log).
- `plugins/gmail_mcp/requirements.txt` — dependencias del conector.
- `plugins/gmail_mcp/README.md` — doc del conector (lectura + etiquetado).
- `plugins/gmail_mcp/dxt-build/manifest.json` — manifest del `.dxt` (VERSIONADO).
- `plugins/gmail_mcp/dxt-build/.gitignore` — ignora el `.dxt` y las copias `.py` regeneradas.
- `tests/gmail_mcp_fakes.py` — doble de test del `service` de Gmail (interfaz `users().<coll>().<metodo>().execute()`).
- `tests/test_gmail_mcp_auth.py` — scope + config-home.
- `tests/test_gmail_mcp_server.py` — tools con service inyectado.

**Nota sobre la "migración":** `~/Dev/Gmail MCP Desktop/` queda FUERA del repo y no se toca en este plan. El corte de cableado (repuntar `claude_desktop_config.json` al nuevo path + reimportar `.dxt`) es un paso OPERATIVO post-merge que ejecuta Nikolai (§8 del spec). El código nuevo se escribe directamente adaptado del original.

---

## Task 1: Paquete + `gmail_auth.py` (scope `gmail.modify`)

**Files:**
- Create: `plugins/gmail_mcp/__init__.py`
- Create: `plugins/gmail_mcp/gmail_auth.py`
- Test: `tests/test_gmail_mcp_auth.py`

- [ ] **Step 1: Crear el marcador de paquete**

Crear `plugins/gmail_mcp/__init__.py` VACÍO (0 bytes), igual que `plugins/google_despacho_mcp/__init__.py`.

- [ ] **Step 2: Escribir el test que falla**

Crear `tests/test_gmail_mcp_auth.py`:

```python
"""Auth del MCP gmail: scope fijado a gmail.modify y config-home configurable."""
from __future__ import annotations

from pathlib import Path

from plugins.gmail_mcp import gmail_auth


def test_scope_es_gmail_modify():
    # Único scope, deliberadamente fijado (no readonly, no mail.google.com).
    assert gmail_auth.SCOPES == ["https://www.googleapis.com/auth/gmail.modify"]


def test_config_home_respeta_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GMAIL_MCP_HOME", str(tmp_path / "cfg"))
    home = gmail_auth.config_home()
    assert home == Path(tmp_path / "cfg")
    assert (home / "tokens").is_dir()


def test_config_home_por_defecto(monkeypatch):
    monkeypatch.delenv("GMAIL_MCP_HOME", raising=False)
    assert gmail_auth.config_home() == Path.home() / ".gmail-mcp"
```

- [ ] **Step 3: Ejecutar el test para verificar que falla**

Run: `python -m pytest tests/test_gmail_mcp_auth.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'plugins.gmail_mcp.gmail_auth'`.

- [ ] **Step 4: Escribir `gmail_auth.py`**

Crear `plugins/gmail_mcp/gmail_auth.py`:

```python
"""Autenticación OAuth y gestión de cuentas para el MCP gmail-multiaccount.

SCOPE ÚNICO: gmail.modify (lectura + etiquetado). `gmail.modify` subsume
`gmail.readonly` → las tools de lectura siguen funcionando; y NO permite borrado
permanente ni IMAP/SMTP total (eso exige mail.google.com), por lo que el borrado
queda descartado a nivel de scope, no solo de tools. El alcance se fija aquí y NO
se parametriza: ampliarlo exige una edición consciente de este fichero +
reautorización de cada cuenta.

Config (por defecto ~/.gmail-mcp, override GMAIL_MCP_HOME):
    $GMAIL_MCP_HOME/
        credentials.json          <- secreto OAuth de cliente (App de escritorio); lo aportas tú
        tokens/
            cuenta@dominio.com.json   <- token por cuenta (autogenerado)
"""
from __future__ import annotations

import os
from pathlib import Path

# Los paquetes de Google se importan de forma perezosa dentro de las funciones
# (patrón de google_despacho_mcp/google_auth.py) para que el módulo sea importable
# sin ellos (tests bajo .venv).

# Alcance: gmail.modify. Se fija aquí y NO se parametriza.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def config_home() -> Path:
    """Directorio raíz de configuración."""
    home = os.environ.get("GMAIL_MCP_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".gmail-mcp"
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
    """Devuelve las direcciones de las cuentas con token guardado."""
    return sorted(p.stem for p in tokens_dir().glob("*.json"))


def load_credentials(email: str):
    """Carga (y refresca si procede) las credenciales de una cuenta autenticada."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    path = _token_path(email)
    if not path.exists():
        raise FileNotFoundError(
            f"La cuenta '{email}' no está autenticada. "
            f"Ejecuta: python -m plugins.gmail_mcp.gmail_cli add"
        )
    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json())
    if not creds or not creds.valid:
        raise RuntimeError(
            f"Las credenciales de '{email}' no son válidas. Reautentica: "
            f"python -m plugins.gmail_mcp.gmail_cli add"
        )
    return creds


def build_service(email: str):
    """Construye el cliente de la API de Gmail v1 para una cuenta."""
    from googleapiclient.discovery import build

    creds = load_credentials(email)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# --- Operaciones interactivas (uso desde el CLI, NUNCA desde el servidor MCP) ---

def add_account() -> str:
    """Lanza el flujo OAuth en el navegador y guarda el token de una cuenta.

    Devuelve la dirección de correo autenticada (resuelta vía getProfile).
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds_file = credentials_path()
    if not creds_file.exists():
        raise FileNotFoundError(
            f"No existe {creds_file}. Descarga el secreto OAuth de cliente "
            f"(tipo 'App de escritorio') desde Google Cloud Console y guárdalo ahí."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    profile = service.users().getProfile(userId="me").execute()
    email = profile["emailAddress"]

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

- [ ] **Step 5: Ejecutar el test para verificar que pasa**

Run: `python -m pytest tests/test_gmail_mcp_auth.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/tnm33/Dev/FeesDefender/.claude/worktrees/gmail-mcp-write"
git add plugins/gmail_mcp/__init__.py plugins/gmail_mcp/gmail_auth.py tests/test_gmail_mcp_auth.py
git commit -m "feat(gmail-mcp): paquete plugins/gmail_mcp + gmail_auth con scope gmail.modify"
```

---

## Task 2: Test fake + `server.py` (migración a `build_server` con DI)

Migra las tools de LECTURA al nuevo servidor con inyección de `service_factory`/`account_lister` (patrón google-despacho) y renombra la identidad del server. La `list_labels` se migra AÚN en su forma antigua (lista de nombres); la Task 3 la cambia a `{id,name}`.

**Files:**
- Create: `tests/gmail_mcp_fakes.py`
- Create: `plugins/gmail_mcp/server.py`
- Test: `tests/test_gmail_mcp_server.py`

- [ ] **Step 1: Escribir el doble de test (fake)**

Crear `tests/gmail_mcp_fakes.py`:

```python
"""Doble de test del `service` de googleapiclient (Gmail v1).

Imita la interfaz fluida anidada de Gmail:
    service.users().messages().<metodo>(**kw).execute()
    service.users().threads().<metodo>(**kw).execute()
    service.users().labels().<metodo>(**kw).execute()
Registra las llamadas para aserciones.
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

    `responses`: método -> resultado único, o método -> lista consumida FIFO.
    Si un método no tiene respuesta, devuelve {}.
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


class _FakeUsers:
    def __init__(self, messages, threads, labels):
        self._messages = _FakeCollection(messages)
        self._threads = _FakeCollection(threads)
        self._labels = _FakeCollection(labels)

    def messages(self):
        return self._messages

    def threads(self):
        return self._threads

    def labels(self):
        return self._labels


class FakeGmailService:
    def __init__(self, *, messages=None, threads=None, labels=None):
        self._users = _FakeUsers(messages, threads, labels)

    def users(self):
        return self._users

    def recorded(self, collection: str):
        """Lista de (metodo, kwargs) llamados sobre 'messages'|'threads'|'labels'."""
        return {
            "messages": self._users._messages,
            "threads": self._users._threads,
            "labels": self._users._labels,
        }[collection].calls
```

- [ ] **Step 2: Escribir el test de regresión que falla**

Crear `tests/test_gmail_mcp_server.py`:

```python
"""Tests del server MCP gmail-multiaccount vía build_server con service_factory
inyectado (sin API viva ni tokens). Comprueba enrutado account→service,
tools de lectura migradas y guardarraíles de etiquetado."""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gmail_mcp_fakes import FakeGmailService  # noqa: E402

from plugins.gmail_mcp import server as srv  # noqa: E402


def _tool(mcp, name):
    return mcp._tool_manager._tools[name].fn


# ------------------------------- lectura / DI -------------------------------

def test_build_server_es_fastmcp_y_se_renombra():
    mcp = srv.build_server(
        service_factory=lambda e: FakeGmailService(),
        account_lister=lambda: ["a@tyukhay.legal"],
    )
    assert mcp is not None
    assert mcp.name == "gmail-multiaccount"


def test_list_accounts_usa_lister():
    mcp = srv.build_server(
        service_factory=lambda e: FakeGmailService(),
        account_lister=lambda: ["a@tyukhay.legal", "b@engelvoelkers.com"],
    )
    assert _tool(mcp, "list_accounts")() == ["a@tyukhay.legal", "b@engelvoelkers.com"]


def test_search_messages_taggea_cada_cuenta():
    msg = {
        "id": "m1", "threadId": "t1",
        "payload": {"headers": [{"name": "Subject", "value": "Reserva"}]},
        "snippet": "hola", "labelIds": [],
    }
    shared = FakeGmailService(messages={"list": {"messages": [{"id": "m1"}]},
                                        "get": msg})
    mcp = srv.build_server(
        service_factory=lambda e: shared,
        account_lister=lambda: ["a@tyukhay.legal", "b@engelvoelkers.com"],
    )
    out = _tool(mcp, "search_messages")(query="reserva")
    assert sorted(r["account"] for r in out) == ["a@tyukhay.legal", "b@engelvoelkers.com"]
    assert all(r["subject"] == "Reserva" for r in out)


def test_resolve_accounts_sin_cuentas_da_error():
    with pytest.raises(RuntimeError):
        srv._resolve_accounts(None, lambda: [])
```

- [ ] **Step 3: Ejecutar el test para verificar que falla**

Run: `python -m pytest tests/test_gmail_mcp_server.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'plugins.gmail_mcp.server'`.

- [ ] **Step 4: Escribir `server.py`**

Crear `plugins/gmail_mcp/server.py`:

```python
#!/usr/bin/env python3
"""Servidor MCP `gmail-multiaccount` — LECTURA + ETIQUETADO de Gmail multicuenta.

Antes solo lectura (scope gmail.readonly). Ahora añade ETIQUETADO: crear una
etiqueta de usuario, y aplicar/quitar una etiqueta a un mensaje o hilo. El scope
OAuth es `gmail.modify` (subsume readonly; NO permite borrado permanente).

Guardarraíles (fail-closed): solo etiquetas de USUARIO (rechaza etiquetas de
sistema: INBOX/SENT/DRAFT/TRASH/SPAM/IMPORTANT/STARRED/UNREAD/CHAT y CATEGORY_*);
`account` obligatorio en toda escritura (sin fan-out); sin borrado (de mensajes o
etiquetas), sin envío/borradores, sin archivar, sin marcar leído/no leído.

Selección de cuenta: las tools de LECTURA aceptan `account` (email) y pueden
omitirlo para consultar TODAS las cuentas (cada resultado se etiqueta con su
cuenta). Las tools de ESCRITURA exigen `account` explícito.

get_attachment escribe a disco (confinable con GMAIL_DL_ROOT): es una lectura en
Gmail cubierta por el scope; el destino puede acotarse a una raíz.
"""
from __future__ import annotations

import base64
import os
import sys
from email.utils import parsedate_to_datetime
from typing import Callable, Optional

from mcp.server.fastmcp import FastMCP

# Import dual-modo: como paquete (tests) o standalone (Claude Desktop).
try:
    from . import gmail_auth
except ImportError:  # ejecución directa: python server.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gmail_auth  # type: ignore  # noqa: E402


# ----------------------------- utilidades internas -----------------------------

_HEADERS_OF_INTEREST = ("From", "To", "Cc", "Subject", "Date")


def _decode_b64url(data: str) -> str:
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", "replace")
    except Exception:
        return ""


def _extract_body(payload: dict) -> str:
    """Extrae el cuerpo en texto, recorriendo las partes y priorizando text/plain."""
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})

    if mime == "text/plain" and body.get("data"):
        return _decode_b64url(body["data"])

    parts = payload.get("parts", [])
    if parts:
        for part in parts:
            text = _extract_body(part)
            if text and part.get("mimeType", "").startswith("text/plain"):
                return text
        for part in parts:
            if part.get("mimeType", "").startswith("text/"):
                text = _extract_body(part)
                if text:
                    return text
        for part in parts:
            text = _extract_body(part)
            if text:
                return text

    if mime.startswith("text/") and body.get("data"):
        return _decode_b64url(body["data"])
    return ""


def _headers_dict(payload: dict) -> dict:
    out = {}
    for h in payload.get("headers", []):
        name = h.get("name", "")
        if name in _HEADERS_OF_INTEREST:
            out[name] = h.get("value", "")
    return out


def _format_message(msg: dict, include_body: bool = True) -> dict:
    payload = msg.get("payload", {})
    headers = _headers_dict(payload)
    result = {
        "id": msg.get("id"),
        "thread_id": msg.get("threadId"),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "cc": headers.get("Cc", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "snippet": msg.get("snippet", ""),
        "labels": msg.get("labelIds", []),
    }
    if include_body:
        result["body"] = _extract_body(payload)
    return result


def _resolve_accounts(account: Optional[str], lister: Callable[[], list[str]]) -> list[str]:
    if account:
        return [account]
    accounts = lister()
    if not accounts:
        raise RuntimeError(
            "No hay cuentas conectadas. Añade alguna con: "
            "python -m plugins.gmail_mcp.gmail_cli add"
        )
    return accounts


def _iter_attachment_parts(payload: dict):
    """Recorre el árbol MIME y produce cada 'part' que sea un adjunto real."""
    stack = [payload]
    while stack:
        part = stack.pop()
        for child in part.get("parts", []) or []:
            stack.append(child)
        body = part.get("body", {}) or {}
        if (part.get("filename") or body.get("attachmentId")) and (
            body.get("attachmentId") or body.get("data")
        ):
            yield part


def _resolve_dest(dest_path: str) -> str:
    """Resuelve y valida la ruta de destino de descarga. Si GMAIL_DL_ROOT está
    definida, el destino debe quedar dentro de esa raíz (realpath contra
    symlink-escape)."""
    dest = os.path.realpath(os.path.expanduser(dest_path))
    root = os.environ.get("GMAIL_DL_ROOT")
    if root:
        root_abs = os.path.realpath(os.path.expanduser(root))
        try:
            inside = os.path.commonpath([root_abs, dest]) == root_abs
        except ValueError:
            inside = False  # unidades distintas en Windows
        if not inside:
            raise ValueError(f"Destino fuera de GMAIL_DL_ROOT ({root_abs}): {dest}")
    return dest


def build_server(
    *,
    service_factory: Callable[[str], object] | None = None,
    account_lister: Callable[[], list[str]] | None = None,
) -> FastMCP:
    """Construye el servidor. `service_factory`/`account_lister` son puntos de
    inyección para tests; en producción se toman de gmail_auth."""
    if service_factory is None:
        service_factory = gmail_auth.build_service
    if account_lister is None:
        account_lister = gmail_auth.list_account_emails

    mcp = FastMCP("gmail-multiaccount")

    # ------------------------------- lectura -------------------------------

    @mcp.tool()
    def list_accounts() -> list[str]:
        """Lista las direcciones de Gmail conectadas a este servidor."""
        return account_lister()

    @mcp.tool()
    def search_messages(query: str, account: Optional[str] = None,
                        max_results: int = 20) -> list[dict]:
        """Busca mensajes con la sintaxis de búsqueda de Gmail. Omite `account`
        para buscar en TODAS las cuentas (cada resultado se etiqueta con la suya).
        Devuelve metadatos y snippet (sin cuerpo); usa read_message para el íntegro."""
        results: list[dict] = []
        for acc in _resolve_accounts(account, account_lister):
            service = service_factory(acc)
            resp = (service.users().messages()
                    .list(userId="me", q=query, maxResults=max_results).execute())
            for ref in resp.get("messages", []):
                full = (service.users().messages()
                        .get(userId="me", id=ref["id"], format="metadata",
                             metadataHeaders=list(_HEADERS_OF_INTEREST)).execute())
                item = _format_message(full, include_body=False)
                item["account"] = acc
                results.append(item)
        return results

    @mcp.tool()
    def read_message(message_id: str, account: str) -> dict:
        """Lee un mensaje completo, incluido el cuerpo en texto."""
        service = service_factory(account)
        full = (service.users().messages()
                .get(userId="me", id=message_id, format="full").execute())
        item = _format_message(full, include_body=True)
        item["account"] = account
        return item

    @mcp.tool()
    def read_thread(thread_id: str, account: str) -> dict:
        """Lee un hilo completo con todos sus mensajes ordenados por fecha."""
        service = service_factory(account)
        thread = (service.users().threads()
                  .get(userId="me", id=thread_id, format="full").execute())
        messages = [_format_message(m, include_body=True)
                    for m in thread.get("messages", [])]

        def _sort_key(m: dict):
            try:
                return parsedate_to_datetime(m["date"])
            except Exception:
                return None

        messages.sort(key=lambda m: (_sort_key(m) is None, _sort_key(m)))
        return {"thread_id": thread_id, "account": account, "messages": messages}

    @mcp.tool()
    def list_labels(account: Optional[str] = None) -> dict:
        """Lista las etiquetas de una cuenta, o de todas si se omite `account`."""
        out: dict[str, list[str]] = {}
        for acc in _resolve_accounts(account, account_lister):
            service = service_factory(acc)
            resp = service.users().labels().list(userId="me").execute()
            out[acc] = sorted(l.get("name", "") for l in resp.get("labels", []))
        return out

    @mcp.tool()
    def list_attachments(message_id: str, account: str) -> list[dict]:
        """Lista los adjuntos de un mensaje (sin descargarlos). Por adjunto:
        filename, mime_type, size (bytes) y attachment_id."""
        service = service_factory(account)
        full = (service.users().messages()
                .get(userId="me", id=message_id, format="full").execute())
        out: list[dict] = []
        for part in _iter_attachment_parts(full.get("payload", {})):
            body = part.get("body", {}) or {}
            out.append({
                "filename": part.get("filename", ""),
                "mime_type": part.get("mimeType", ""),
                "size": body.get("size", 0),
                "attachment_id": body.get("attachmentId", ""),
            })
        return out

    @mcp.tool()
    def get_attachment(message_id: str, attachment_id: str, account: str,
                       dest_path: str, max_bytes: int = 50_000_000) -> dict:
        """Descarga un adjunto a disco (base64url -> fichero). dest_path confinable
        con GMAIL_DL_ROOT. Devuelve ruta absoluta y tamaño en bytes."""
        dest = _resolve_dest(dest_path)
        service = service_factory(account)
        att = (service.users().messages().attachments()
               .get(userId="me", messageId=message_id, id=attachment_id).execute())
        size = att.get("size", 0)
        if max_bytes and size and size > max_bytes:
            raise ValueError(
                f"Adjunto de {size} bytes supera max_bytes ({max_bytes}). "
                f"Sube el límite explícitamente si de verdad lo quieres.")
        raw = base64.urlsafe_b64decode(att.get("data", "").encode("utf-8"))
        if max_bytes and len(raw) > max_bytes:
            raise ValueError(f"Adjunto de {len(raw)} bytes supera max_bytes ({max_bytes}).")
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(raw)
        return {"path": dest, "bytes": len(raw), "account": account}

    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Ejecutar el test para verificar que pasa**

Run: `python -m pytest tests/test_gmail_mcp_server.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add tests/gmail_mcp_fakes.py plugins/gmail_mcp/server.py tests/test_gmail_mcp_server.py
git commit -m "feat(gmail-mcp): server con build_server (DI) + tools de lectura migradas + rename a gmail-multiaccount"
```

---

## Task 3: `list_labels` devuelve `{id, name}`

Aplicar etiquetas necesita el id, no solo el nombre. Se extiende `list_labels` para devolver, por cuenta, una lista de `{id, name}`.

**Files:**
- Modify: `plugins/gmail_mcp/server.py` (tool `list_labels`)
- Test: `tests/test_gmail_mcp_server.py`

- [ ] **Step 1: Añadir el test que falla**

Añadir al final de `tests/test_gmail_mcp_server.py`:

```python
# ------------------------------- list_labels -------------------------------

def test_list_labels_devuelve_id_y_nombre_ordenado():
    labels = {"list": {"labels": [
        {"id": "Label_9", "name": "W-02XOR7", "type": "user"},
        {"id": "INBOX", "name": "INBOX", "type": "system"},
        {"id": "Label_1", "name": "Arras", "type": "user"},
    ]}}
    svc = FakeGmailService(labels=labels)
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "list_labels")(account="a@tyukhay.legal")
    assert out == {"a@tyukhay.legal": [
        {"id": "Label_1", "name": "Arras"},
        {"id": "INBOX", "name": "INBOX"},
        {"id": "Label_9", "name": "W-02XOR7"},
    ]}
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `python -m pytest tests/test_gmail_mcp_server.py::test_list_labels_devuelve_id_y_nombre_ordenado -v`
Expected: FAIL (devuelve lista de strings, no de dicts).

- [ ] **Step 3: Reescribir la tool `list_labels`**

En `plugins/gmail_mcp/server.py`, reemplazar la función `list_labels` completa por:

```python
    @mcp.tool()
    def list_labels(account: Optional[str] = None) -> dict:
        """Lista las etiquetas de una cuenta (o de todas si se omite `account`).
        Devuelve, por cuenta, una lista de {id, name} ordenada por nombre. El id es
        necesario para apply_label/remove_label."""
        out: dict[str, list[dict]] = {}
        for acc in _resolve_accounts(account, account_lister):
            service = service_factory(acc)
            resp = service.users().labels().list(userId="me").execute()
            out[acc] = sorted(
                ({"id": l.get("id"), "name": l.get("name", "")}
                 for l in resp.get("labels", [])),
                key=lambda d: d["name"],
            )
        return out
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `python -m pytest tests/test_gmail_mcp_server.py -v`
Expected: PASS (todos, incluido el nuevo).

- [ ] **Step 5: Commit**

```bash
git add plugins/gmail_mcp/server.py tests/test_gmail_mcp_server.py
git commit -m "feat(gmail-mcp): list_labels devuelve {id,name} (id necesario para etiquetar)"
```

---

## Task 4: Guardarraíles + `create_label`

Introduce los helpers de guardarraíl (blocklist de sistema, resolución de etiqueta de usuario) y la tool `create_label` (idempotente).

**Files:**
- Modify: `plugins/gmail_mcp/server.py` (helpers a nivel de módulo + tool `create_label`)
- Test: `tests/test_gmail_mcp_server.py`

- [ ] **Step 1: Añadir los tests que fallan**

Añadir al final de `tests/test_gmail_mcp_server.py`:

```python
# ------------------------------- guardarraíles -------------------------------

_USER_LABELS = {"list": {"labels": [
    {"id": "Label_1", "name": "W-02XOR7", "type": "user"},
    {"id": "INBOX", "name": "INBOX", "type": "system"},
    {"id": "CATEGORY_PROMOTIONS", "name": "CATEGORY_PROMOTIONS", "type": "system"},
]}}


def test_resolve_user_label_por_id():
    svc = FakeGmailService(labels=_USER_LABELS)
    match = srv._resolve_user_label(svc, "Label_1")
    assert match["id"] == "Label_1" and match["name"] == "W-02XOR7"


def test_resolve_user_label_por_nombre():
    svc = FakeGmailService(labels=_USER_LABELS)
    match = srv._resolve_user_label(svc, "W-02XOR7")
    assert match["id"] == "Label_1"


def test_resolve_user_label_inexistente_error():
    svc = FakeGmailService(labels=_USER_LABELS)
    with pytest.raises(ValueError):
        srv._resolve_user_label(svc, "NoExiste")


def test_resolve_user_label_sistema_rechazado_por_type():
    svc = FakeGmailService(labels=_USER_LABELS)
    with pytest.raises(ValueError):
        srv._resolve_user_label(svc, "INBOX")


def test_resolve_user_label_category_rechazado():
    svc = FakeGmailService(labels=_USER_LABELS)
    with pytest.raises(ValueError):
        srv._resolve_user_label(svc, "CATEGORY_PROMOTIONS")


# ------------------------------- create_label -------------------------------

def test_create_label_idempotente_si_existe():
    svc = FakeGmailService(labels={"list": {"labels": [
        {"id": "Label_1", "name": "W-02XOR7", "type": "user"}]}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "create_label")(account="a@tyukhay.legal", name="W-02XOR7")
    assert out["id"] == "Label_1" and out["created"] is False
    # No debe haber llamado a labels().create
    assert not any(m == "create" for m, _ in svc.recorded("labels"))


def test_create_label_crea_si_no_existe():
    svc = FakeGmailService(labels={
        "list": {"labels": []},
        "create": {"id": "Label_new", "name": "W-99", "type": "user"}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "create_label")(account="a@tyukhay.legal", name="W-99")
    assert out["id"] == "Label_new" and out["created"] is True
    assert any(m == "create" for m, _ in svc.recorded("labels"))


def test_create_label_rechaza_nombre_de_sistema():
    svc = FakeGmailService(labels={"list": {"labels": []}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    tool = _tool(mcp, "create_label")
    for bad in ["INBOX", "inbox", "CATEGORY_X", "TRASH"]:
        with pytest.raises(ValueError):
            tool(account="a@tyukhay.legal", name=bad)


def test_create_label_account_obligatorio():
    svc = FakeGmailService(labels={"list": {"labels": []}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    fn = _tool(mcp, "create_label")
    assert inspect.signature(fn).parameters["account"].default is inspect._empty
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `python -m pytest tests/test_gmail_mcp_server.py -k "resolve_user_label or create_label" -v`
Expected: FAIL con `AttributeError: module ... has no attribute '_resolve_user_label'` y `KeyError: 'create_label'`.

- [ ] **Step 3: Añadir los helpers a nivel de módulo**

En `plugins/gmail_mcp/server.py`, insertar ANTES de `def build_server(` (tras `_resolve_dest`):

```python
# --------------------------- guardarraíles de etiqueta ---------------------------

# Etiquetas de sistema: nunca se crean/aplican/quitan. La fuente de verdad es el
# campo `type == "system"` de la API; esta blocklist es una red defensiva por si
# una etiqueta no aparece en el listado.
SYSTEM_LABELS = frozenset({
    "INBOX", "SENT", "DRAFT", "TRASH", "SPAM",
    "IMPORTANT", "STARRED", "UNREAD", "CHAT",
})


def _is_system_label_ref(ref: str) -> bool:
    """True si `ref` (id o nombre) es una etiqueta de sistema por convención."""
    r = (ref or "").strip().upper()
    return r in SYSTEM_LABELS or r.startswith("CATEGORY_")


def _list_labels_raw(service) -> list[dict]:
    resp = service.users().labels().list(userId="me").execute()
    return resp.get("labels", [])


def _resolve_user_label(service, label: str) -> dict:
    """Resuelve `label` (id o nombre) a un dict de etiqueta de USUARIO. Fail-closed:
    ValueError si está vacío, si no existe, o si es de sistema (por type o por
    convención de id/nombre)."""
    target = (label or "").strip()
    if not target:
        raise ValueError("label vacío.")
    labels = _list_labels_raw(service)
    by_id = [l for l in labels if l.get("id") == target]
    by_name = [l for l in labels if l.get("name") == target]
    match = by_id[0] if by_id else (by_name[0] if by_name else None)
    if match is None:
        raise ValueError(
            f"Etiqueta no encontrada: {label!r}. Las etiquetas de usuario se crean "
            f"explícitamente con create_label; no se crean al aplicar.")
    if (match.get("type") or "").strip().lower() == "system" \
            or _is_system_label_ref(match.get("id", "")) \
            or _is_system_label_ref(match.get("name", "")):
        raise ValueError(
            f"Etiqueta de sistema no permitida: {match.get('id')} "
            f"({match.get('name')}). Solo etiquetas de usuario.")
    return match


def _guard_create_name(name: str) -> str:
    n = (name or "").strip()
    if not n:
        raise ValueError("name vacío.")
    if _is_system_label_ref(n):
        raise ValueError(f"Nombre reservado de etiqueta de sistema: {name!r}.")
    return n
```

- [ ] **Step 4: Añadir la tool `create_label`**

En `plugins/gmail_mcp/server.py`, insertar dentro de `build_server`, justo ANTES de `    return mcp`:

```python
    # ------------------------------- etiquetado -------------------------------

    @mcp.tool()
    def create_label(account: str, name: str) -> dict:
        """Crea la etiqueta de USUARIO `name` en `account`. IDEMPOTENTE: si ya
        existe, devuelve su id sin recrearla. Rechaza nombres de etiqueta de
        sistema. Devuelve {account, id, name, created}."""
        clean = _guard_create_name(name)
        service = service_factory(account)
        for l in _list_labels_raw(service):
            if l.get("name") == clean:
                return {"account": account, "id": l.get("id"),
                        "name": l.get("name"), "created": False}
        created = service.users().labels().create(
            userId="me", body={"name": clean}).execute()
        return {"account": account, "id": created.get("id"),
                "name": created.get("name", clean), "created": True}
```

- [ ] **Step 5: Ejecutar para verificar que pasa**

Run: `python -m pytest tests/test_gmail_mcp_server.py -v`
Expected: PASS (todos).

- [ ] **Step 6: Commit**

```bash
git add plugins/gmail_mcp/server.py tests/test_gmail_mcp_server.py
git commit -m "feat(gmail-mcp): guardarraíles de etiqueta de usuario (fail-closed) + create_label idempotente"
```

---

## Task 5: `apply_label`

**Files:**
- Modify: `plugins/gmail_mcp/server.py` (helper `_modify_target` + tool `apply_label`)
- Test: `tests/test_gmail_mcp_server.py`

- [ ] **Step 1: Añadir los tests que fallan**

Añadir al final de `tests/test_gmail_mcp_server.py`:

```python
# ------------------------------- apply_label -------------------------------

def _label_svc(**extra):
    """FakeGmailService con etiquetas de usuario + respuestas de modify."""
    labels = {"list": {"labels": [
        {"id": "Label_1", "name": "W-02XOR7", "type": "user"},
        {"id": "INBOX", "name": "INBOX", "type": "system"},
    ]}}
    return FakeGmailService(labels=labels, **extra)


def test_apply_label_a_mensaje_por_id():
    svc = _label_svc(messages={"modify": {"id": "m1", "labelIds": ["Label_1"]}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="Label_1",
                                    target_id="m1", target_type="message")
    assert out["label_id"] == "Label_1" and out["action"] == "apply"
    assert out["target_type"] == "message"
    method, kwargs = svc.recorded("messages")[-1]
    assert method == "modify"
    assert kwargs["body"] == {"addLabelIds": ["Label_1"]}
    assert kwargs["id"] == "m1"


def test_apply_label_por_nombre_resuelve_id():
    svc = _label_svc(messages={"modify": {"id": "m1", "labelIds": ["Label_1"]}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="W-02XOR7",
                                    target_id="m1", target_type="message")
    assert out["label_id"] == "Label_1"


def test_apply_label_a_hilo():
    svc = _label_svc(threads={"modify": {"id": "t1", "labelIds": ["Label_1"]}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="Label_1",
                                    target_id="t1", target_type="thread")
    method, kwargs = svc.recorded("threads")[-1]
    assert method == "modify" and kwargs["body"] == {"addLabelIds": ["Label_1"]}
    assert out["target_type"] == "thread"


def test_apply_label_nombre_inexistente_error():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="NoExiste",
                                  target_id="m1", target_type="message")


def test_apply_label_sistema_rechazado():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="INBOX",
                                  target_id="m1", target_type="message")


def test_apply_label_target_type_invalido_error():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="Label_1",
                                  target_id="x", target_type="foo")


def test_apply_label_account_obligatorio():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    fn = _tool(mcp, "apply_label")
    assert inspect.signature(fn).parameters["account"].default is inspect._empty
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `python -m pytest tests/test_gmail_mcp_server.py -k apply_label -v`
Expected: FAIL con `KeyError: 'apply_label'`.

- [ ] **Step 3: Añadir el helper `_modify_target`**

En `plugins/gmail_mcp/server.py`, insertar a nivel de módulo, tras `_guard_create_name`:

```python
def _modify_target(service, *, target_id: str, target_type: str,
                   add: Optional[list[str]] = None,
                   remove: Optional[list[str]] = None) -> dict:
    """Aplica addLabelIds/removeLabelIds a un mensaje o hilo. target_type inválido
    → ValueError (fail-closed)."""
    body: dict = {}
    if add:
        body["addLabelIds"] = add
    if remove:
        body["removeLabelIds"] = remove
    tt = (target_type or "").strip().lower()
    if tt == "message":
        return (service.users().messages()
                .modify(userId="me", id=target_id, body=body).execute())
    if tt == "thread":
        return (service.users().threads()
                .modify(userId="me", id=target_id, body=body).execute())
    raise ValueError(f"target_type debe ser 'message' o 'thread', no {target_type!r}.")
```

- [ ] **Step 4: Añadir la tool `apply_label`**

En `plugins/gmail_mcp/server.py`, insertar dentro de `build_server`, justo ANTES de `    return mcp`:

```python
    @mcp.tool()
    def apply_label(account: str, label: str, target_id: str,
                    target_type: str = "message") -> dict:
        """Aplica la etiqueta de USUARIO `label` (id o nombre EXISTENTE) al mensaje
        o hilo `target_id`. `target_type`: 'message' | 'thread'. El correo permanece
        en Inbox (no se archiva). `label` inexistente → error (crear es explícito con
        create_label). Devuelve {account, label_id, label_name, target_id,
        target_type, action, label_ids}."""
        service = service_factory(account)
        match = _resolve_user_label(service, label)
        resp = _modify_target(service, target_id=target_id, target_type=target_type,
                              add=[match["id"]])
        return {"account": account, "label_id": match["id"],
                "label_name": match.get("name"), "target_id": target_id,
                "target_type": target_type.strip().lower(), "action": "apply",
                "label_ids": resp.get("labelIds", [])}
```

- [ ] **Step 5: Ejecutar para verificar que pasa**

Run: `python -m pytest tests/test_gmail_mcp_server.py -v`
Expected: PASS (todos).

- [ ] **Step 6: Commit**

```bash
git add plugins/gmail_mcp/server.py tests/test_gmail_mcp_server.py
git commit -m "feat(gmail-mcp): apply_label (mensaje/hilo, resuelve id o nombre, permanece en Inbox)"
```

---

## Task 6: `remove_label`

**Files:**
- Modify: `plugins/gmail_mcp/server.py` (tool `remove_label`)
- Test: `tests/test_gmail_mcp_server.py`

- [ ] **Step 1: Añadir los tests que fallan**

Añadir al final de `tests/test_gmail_mcp_server.py`:

```python
# ------------------------------- remove_label -------------------------------

def test_remove_label_de_mensaje():
    svc = _label_svc(messages={"modify": {"id": "m1", "labelIds": []}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "remove_label")(account="a@tyukhay.legal", label="Label_1",
                                     target_id="m1", target_type="message")
    assert out["action"] == "remove" and out["label_id"] == "Label_1"
    method, kwargs = svc.recorded("messages")[-1]
    assert method == "modify" and kwargs["body"] == {"removeLabelIds": ["Label_1"]}


def test_remove_label_de_hilo():
    svc = _label_svc(threads={"modify": {"id": "t1", "labelIds": []}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "remove_label")(account="a@tyukhay.legal", label="W-02XOR7",
                                     target_id="t1", target_type="thread")
    method, kwargs = svc.recorded("threads")[-1]
    assert method == "modify" and kwargs["body"] == {"removeLabelIds": ["Label_1"]}


def test_remove_label_sistema_rechazado():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "remove_label")(account="a@tyukhay.legal", label="INBOX",
                                   target_id="m1", target_type="message")


def test_remove_label_account_obligatorio():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    fn = _tool(mcp, "remove_label")
    assert inspect.signature(fn).parameters["account"].default is inspect._empty
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `python -m pytest tests/test_gmail_mcp_server.py -k remove_label -v`
Expected: FAIL con `KeyError: 'remove_label'`.

- [ ] **Step 3: Añadir la tool `remove_label`**

En `plugins/gmail_mcp/server.py`, insertar dentro de `build_server`, justo ANTES de `    return mcp`:

```python
    @mcp.tool()
    def remove_label(account: str, label: str, target_id: str,
                     target_type: str = "message") -> dict:
        """Quita la etiqueta de USUARIO `label` (id o nombre EXISTENTE) del mensaje o
        hilo `target_id`. `target_type`: 'message' | 'thread'. Rechaza etiquetas de
        sistema. Devuelve {account, label_id, label_name, target_id, target_type,
        action, label_ids}."""
        service = service_factory(account)
        match = _resolve_user_label(service, label)
        resp = _modify_target(service, target_id=target_id, target_type=target_type,
                              remove=[match["id"]])
        return {"account": account, "label_id": match["id"],
                "label_name": match.get("name"), "target_id": target_id,
                "target_type": target_type.strip().lower(), "action": "remove",
                "label_ids": resp.get("labelIds", [])}
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `python -m pytest tests/test_gmail_mcp_server.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add plugins/gmail_mcp/server.py tests/test_gmail_mcp_server.py
git commit -m "feat(gmail-mcp): remove_label (mensaje/hilo, guardarraíl de sistema)"
```

---

## Task 7: CLI, arranque, requirements, README y `dxt-build`

Completa el paquete con las piezas operativas. No hay tests unitarios nuevos (son artefactos de arranque/empaquetado); la verificación es una comprobación de arranque manual en la Task 8.

**Files:**
- Create: `plugins/gmail_mcp/gmail_cli.py`
- Create: `plugins/gmail_mcp/run_server.bat`
- Create: `plugins/gmail_mcp/requirements.txt`
- Create: `plugins/gmail_mcp/README.md`
- Create: `plugins/gmail_mcp/dxt-build/manifest.json`
- Create: `plugins/gmail_mcp/dxt-build/.gitignore`

- [ ] **Step 1: Crear `gmail_cli.py`**

```python
#!/usr/bin/env python3
"""Gestión de cuentas de gmail-multiaccount desde la terminal.

El flujo OAuth necesita navegador → el alta se hace aquí, nunca desde el server.

    python -m plugins.gmail_mcp.gmail_cli add            # autentica una cuenta (abre navegador)
    python -m plugins.gmail_mcp.gmail_cli list           # lista cuentas conectadas
    python -m plugins.gmail_mcp.gmail_cli remove EMAIL    # elimina el token local
"""
from __future__ import annotations

import os
import sys

# Import dual-modo: como módulo del paquete o como script suelto.
try:
    from . import gmail_auth
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gmail_auth  # type: ignore  # noqa: E402


def cmd_add() -> None:
    print("Se abrirá el navegador para autenticar la cuenta "
          "(Gmail: lectura + ETIQUETADO)...")
    email = gmail_auth.add_account()
    print(f"OK · cuenta conectada: {email}")
    print(f"Token guardado en: {gmail_auth.tokens_dir() / (email + '.json')}")


def cmd_list() -> None:
    accounts = gmail_auth.list_account_emails()
    if not accounts:
        print("(sin cuentas conectadas)")
        return
    print("Cuentas conectadas:")
    for a in accounts:
        print(f"  - {a}")


def cmd_remove(email: str) -> None:
    if gmail_auth.remove_account(email):
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
            print("Uso: python -m plugins.gmail_mcp.gmail_cli remove EMAIL")
            sys.exit(1)
        cmd_remove(args[1])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Crear `run_server.bat`**

Mismo patrón que `plugins/google_despacho_mcp/run_server.bat` (stdout para el pipe JSON-RPC, stderr al log). Contenido:

```bat
@echo off
REM Wrapper de arranque del MCP gmail-multiaccount para Claude Desktop.
REM stdout (fd1) queda para el pipe JSON-RPC de MCP; stderr al log.
REM Si el interprete no esta en esta ruta, editar la linea de abajo.
C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe "%~dp0server.py" 2>>"%APPDATA%\Claude\gmail-multiaccount-mcp.log"
```

- [ ] **Step 3: Crear `requirements.txt`**

```
mcp>=1.2.0
google-api-python-client>=2.100.0
google-auth>=2.23.0
google-auth-oauthlib>=1.1.0
```

- [ ] **Step 4: Crear `README.md`**

```markdown
# MCP `gmail-multiaccount` — lectura + etiquetado

Servidor MCP local (stdio) que mantiene varias cuentas de Gmail del despacho
autenticadas simultáneamente. Permite **buscar y leer** correo y **etiquetar**
(crear una etiqueta de usuario y aplicarla/quitarla a un mensaje o hilo) desde
Claude Code y Cowork.

Gemelo de `plugins/google_despacho_mcp/` (mismo patrón: `build_server` con
inyección de `service`, CLI de cuentas, `run_server.bat`, `dxt-build/`).

## Alcance (scope OAuth)

`https://www.googleapis.com/auth/gmail.modify` — subsume `gmail.readonly` y NO
permite borrado permanente ni IMAP/SMTP total. Fijado en `gmail_auth.SCOPES`;
ampliarlo exige editar ese fichero y reautorizar cada cuenta.

## Herramientas

| Herramienta | Función |
|---|---|
| `list_accounts` | Lista las cuentas conectadas |
| `search_messages` | Busca con sintaxis Gmail; en una cuenta o en todas |
| `read_message` | Lee un mensaje completo (cuerpo en texto) |
| `read_thread` | Lee un hilo completo ordenado por fecha |
| `list_labels` | Lista etiquetas `{id, name}` de una o todas las cuentas |
| `list_attachments` | Lista adjuntos de un mensaje |
| `get_attachment` | Descarga un adjunto a disco (confinable con `GMAIL_DL_ROOT`) |
| `create_label` | Crea (idempotente) una etiqueta de usuario |
| `apply_label` | Aplica una etiqueta de usuario a un mensaje/hilo |
| `remove_label` | Quita una etiqueta de usuario de un mensaje/hilo |

## Guardarraíles

- **Solo etiquetas de usuario.** Se rechazan las de sistema (INBOX, SENT, DRAFT,
  TRASH, SPAM, IMPORTANT, STARRED, UNREAD, CHAT y `CATEGORY_*`) por el campo
  `type` de la API + blocklist defensiva. Fail-closed ante etiqueta desconocida.
- **`account` obligatorio en toda escritura** (sin fan-out: nunca se modifican las
  cuentas a la vez).
- **Sin borrado** (mensajes ni etiquetas), **sin envío/borradores**, **sin
  archivar**, **sin marcar leído/no leído**. Esas tools no existen.

## Cuentas y tokens

Config-home en `~/.gmail-mcp/` (override `GMAIL_MCP_HOME`): `credentials.json`
(secreto OAuth de cliente, App de escritorio) + `tokens/<cuenta>.json` por cuenta.

```
python -m plugins.gmail_mcp.gmail_cli add       # alta (abre navegador)
python -m plugins.gmail_mcp.gmail_cli list      # cuentas conectadas
python -m plugins.gmail_mcp.gmail_cli remove EMAIL
```

Con scope `gmail.modify`, una cuenta con token `readonly` viejo dará
`invalid_scope` hasta reautorizar. Verifica que la app OAuth esté en
**Producción** antes de reautorizar (en *Testing* el refresh token caduca a 7
días).

## Requisitos

Python 3.10+ y las dependencias de `requirements.txt`.
```

- [ ] **Step 5: Crear `dxt-build/manifest.json`**

```json
{
  "manifest_version": "0.3",
  "name": "gmail-multiaccount",
  "display_name": "Gmail despacho — multicuenta (lectura + escritura)",
  "version": "2.0.0",
  "description": "Lectura + etiquetado de las cuentas de Gmail del despacho (buscar/leer correos e hilos; crear etiqueta de usuario y aplicarla/quitarla a mensaje o hilo). Sin borrado, envío ni archivado. Scope gmail.modify.",
  "author": {
    "name": "Tyukhay Legal"
  },
  "server": {
    "type": "python",
    "entry_point": "server.py",
    "mcp_config": {
      "command": "C:\\Users\\tnm33\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe",
      "args": ["C:\\Users\\tnm33\\Dev\\FeesDefender\\plugins\\gmail_mcp\\server.py"],
      "env": {
        "GMAIL_MCP_HOME": "C:\\Users\\tnm33\\.gmail-mcp"
      }
    }
  }
}
```

- [ ] **Step 6: Crear `dxt-build/.gitignore`**

```
# Artefactos de build del .dxt. La fuente canónica es manifest.json (versionado)
# + los módulos reales en ../ (server.py, gmail_auth.py). El .dxt y las copias .py
# se regeneran al empaquetar; no se versionan.
*.dxt
server.py
gmail_auth.py
```

- [ ] **Step 7: Commit**

```bash
git add plugins/gmail_mcp/gmail_cli.py plugins/gmail_mcp/run_server.bat \
        plugins/gmail_mcp/requirements.txt plugins/gmail_mcp/README.md \
        plugins/gmail_mcp/dxt-build/manifest.json plugins/gmail_mcp/dxt-build/.gitignore
git commit -m "feat(gmail-mcp): CLI de cuentas, run_server.bat, requirements, README y dxt-build (manifest)"
```

---

## Task 8: Verificación integral + cierre de rama

**Files:** ninguno nuevo (verificación + PR).

- [ ] **Step 1: Arranque del server (humo, sin API viva)**

Verifica que `server.py` se importa y construye el FastMCP sin tokens (DI por defecto no se toca):

Run:
```bash
python -c "from plugins.gmail_mcp import server; m = server.build_server(service_factory=lambda e: None, account_lister=lambda: []); print(sorted(m._tool_manager._tools))"
```
Expected: imprime la lista con las 10 tools:
`['apply_label', 'create_label', 'get_attachment', 'list_accounts', 'list_attachments', 'list_labels', 'read_message', 'read_thread', 'remove_label', 'search_messages']`

- [ ] **Step 2: Suite completa verde**

Run: `python -m pytest -q --tb=short`
Expected: PASS, sin regresiones. Anota el total (debe ser el nº previo + los tests nuevos de Gmail). Si algún número baja, investígalo antes de seguir.

- [ ] **Step 3: leak-scan local (pre-commit sobre todo el árbol)**

Run: `pre-commit run --all-files`
Expected: PASS (gitleaks + check-added-large-files + `precommit_leak_guard`). Si `pre-commit` no está instalado en el worktree, instalarlo primero:
```bash
pre-commit install && pre-commit install --hook-type pre-push
```

- [ ] **Step 4: Push de la rama y PR**

```bash
git push -u origin feat/gmail-mcp-escritura
gh pr create --fill --base main --title "feat(gmail-mcp): escritura de etiquetas + migración a plugins/gmail_mcp"
```
Verifica que el check `leak-scan` (CI) queda en verde en el PR antes de mergear.

- [ ] **Step 5: Merge (tras verde)**

```bash
gh pr merge --squash --delete-branch
```

- [ ] **Step 6: Recordatorio de pasos OPERATIVOS post-merge (los ejecuta Nikolai)**

No son código; anotarlos en el cierre de sesión:
1. Verificar que la app OAuth de Gmail está en **Producción** (si no, el refresh token caduca a 7 días — `reference-gmail-mcp-token-expiry`).
2. **Reautorizar las 5 cuentas**: `python -m plugins.gmail_mcp.gmail_cli add` (flujo OAuth en navegador, login + "Permitir" lo hace Nikolai). Con `gmail.modify`, las cuentas con token readonly viejo darán `invalid_scope` hasta reautorizar.
3. Reempaquetar el **`.dxt`** desde `dxt-build/` y reimportar en Cowork (Ajustes → Extensiones).
4. Actualizar `claude_desktop_config.json` al nuevo path (`plugins/gmail_mcp/`) con **Claude Desktop CERRADO** (reescribe el config al cerrar — `reference-claude-desktop-config-clobber`). No dejar a la vez la entrada cruda del config y el `.dxt` con el mismo nombre (colisión del puente): quedarse con una sola vía.

---

## Notas de implementación

- **DRY:** el fake (`tests/gmail_mcp_fakes.py`) reutiliza el patrón de `tests/google_despacho_fakes.py` adaptado a la interfaz anidada de Gmail (`users().<coll>()`).
- **YAGNI:** fuera de alcance (no implementar): archivar/mover-de-bandeja, borrar, enviar/borradores, marcar leído-no-leído, scope por-cuenta, filtros/reglas de Gmail, jerarquías de etiquetas (spec §9).
- **Fail-closed:** el guardarraíl de etiqueta de usuario se apoya en el campo `type` de la API como fuente de verdad, con una blocklist defensiva de ids/nombres de sistema por si una etiqueta no aparece en el listado.
- **Config-home inalterado:** `~/.gmail-mcp/` no se mueve; la ruta del código (`plugins/gmail_mcp/`) y la de los tokens son independientes.
- **API privada de `mcp`:** los tests acceden a `mcp._tool_manager._tools[...].fn` (igual que los de google-despacho, `mcp` 1.28.0); puede requerir ajuste al subir de versión de `mcp`.
