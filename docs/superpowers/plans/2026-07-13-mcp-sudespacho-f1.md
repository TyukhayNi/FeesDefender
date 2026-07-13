# MCP `sudespacho` — F1 (lectura) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un MCP standalone que da LECTURA del CRM sudespacho desde el chat, autenticado con la cuenta personal de cada usuario (Bearer JWT + refresh), con lista blanca que oculta la contabilidad y sin ninguna capacidad de borrado.

**Architecture:** Plugin stdio FastMCP en `plugins/sudespacho_mcp/`, **sin `import core`** (autocontenido, patrón de los otros 4 plugins). Lógica pura (cliente REST con `httpx` inyectable) separada del wrapper de tools (`server.py`). Auth Modelo B: login una vez (usuario/contraseña → tokens), refresco silencioso rodante (`POST /api/token/refresh`). Lectura por la API genérica de elementos (`GET /api/element_registries/{element}`). Entrega `.dxt` + puente de Claude Desktop.

**Tech Stack:** Python 3.12+, `mcp` (FastMCP), `httpx`, `pytest`. Spec: `docs/superpowers/specs/2026-07-13-mcp-sudespacho-design.md`.

**Convenciones del repo (críticas):**
- Windows + PowerShell; UTF-8 sin BOM.
- Tests en `tests/` (raíz del repo), no dentro del plugin. `python -m pytest -q`.
- Commits: rama + PR (main protegida). `pre-commit` corre gitleaks + leak-guard.
- Secretos (tokens/contraseña) nunca en repo ni chat; tokens en `~/.sudespacho-despacho/` (env `SUDESPACHO_DESPACHO_HOME`).
- **Regla dura NO-BORRADO:** el cliente no implementa `DELETE`; el server no registra tool de borrado; test que lo asegura.

**Contratos ya verificados (no re-descubrir):**
- Listado: `GET https://api-crm-commons-pro.sudespacho.biz/api/element_registries/{element}?page=1&itemsPerPage=10&properties[0]=..&return_totals=false` → 200, respuesta `{totalItems, currentPage, itemsPerPage, items:[{id, isPrimary, values:[{property:{name}, value, label?}]}]}` (NO hydra). Verificado en vivo 2026-07-13.
- Refresco (rodante, no requiere JWT vigente): `POST /api/token/refresh` body `{"refresh_token": rt}` → `{"token": jwt, "refresh_token": rt2}` (gesdinet/Lexik). Fuente: `core/sync_sudespacho_legacy.py:232` (`_try_refresh_jwt_post`).
- JWT: en cliente vive en `localStorage['token']`, claims `iat, exp(60min), roles, username`. Auth REST = `Authorization: Bearer <jwt>`, SIN PHPSESSID.
- Descarga documento: `GET /api/documents/{id}/downloadUri` → campo `presignedDownloadUrl`. Fuente: `core/sync_sudespacho.py:744`.

**Gates — estado tras verificación en vivo 2026-07-13 (detalle en spec §13):**
- ✅ **Login RESUELTO:** no hay endpoint usuario/contraseña (404) → alta por `refresh_token` pegado (Task 14).
- ✅ **Bug 500 RESUELTO:** forma **coma** `?properties=a,b,c` → 200 (array `properties[]` → 500). Sin legacy.
- ✅ **Slugs RESUELTOS** (Task 6): `abogados_propios`/`abogados_contrarios` (no `abogados`), `extrajudiciales` (no `expedientes_extrajudiciales`), `juzgados` válido. Y `properties[]` obligatorio en el listado.
- ⏳ **Rol oculta contabilidad** (slug + campo `actuaciones.total` + descarga de doc factura): PENDIENTE, necesita usuario de rol abogado.
- ⏳ **Escritura con JWT personal (F2):** ¿`POST /api/element_register` atribuye `created_by`? PENDIENTE.
- ⏳ **Tope de licencia (4 concurrentes):** Nikolai consulta con sudespacho.
- ⏳ **Vida del `refresh_token`** (opaco): medir (¿rodante/absoluto?).

> **⚠️ CORRECCIONES DE LA REVISIÓN ADVERSARIAL (2026-07-13) — OBLIGATORIAS.** Este plan se
> escribió antes del red-team; aplica estas correcciones al ejecutar (detalladas en cada task):
> 1. **Token store atómico** (temp + `os.replace`) y **carga tolerante** (`JSONDecodeError`→None) — Task 3.
> 2. **`auth._extract` tolerante**: exigir solo `jwt`; `refresh_token` opcional (como `core`) — Task 4.
> 3. **Sesión con lock de fichero + re-lectura de disco antes de `NeedsLogin`** (carrera del refresh rodante entre Claude Code y el puente) — Task 5.
> 4. **Refresco REACTIVO a 401** en el cliente (no solo proactivo por reloj): 401→refrescar→reintentar una vez; distinguir 401 de 5xx/red (transitorio) — Task 4/7.
> 5. **Filtro de propiedades (confidencialidad por campo)**: vetar `properties` económicas (`total`, `base_imponible`, `precio_unidad`, `iva*`, `irpf*`, `importe*`, `cobro*`, `pago*`) y relaciones a slug vetado (`*.conceptos_*`, `right.facturas.*`, `sum(...)` sobre esas) — Task 6/7.
> 6. **`describe_element` SOLO ESQUEMA** (sin registros de muestra) — Task 10.
> 7. **Documentos:** registrar `download_document` (a DL-root) como tool; **NO** exponer `get_document_download_url`; añadir `gdocu` a la lista blanca; validar elemento-origen del doc — Task 9/12, Task 6.
> 8. **Descarga con `timeout` + `follow_redirects=True`** (como `core._download_url_raw`) — Task 9.
> 9. **Detalle (bug 500): coma VERIFICADA en vivo (200)** — usar `?properties=a,b,c` (coma), NO `properties[]` (500). **Sin fallback legacy.** Alta por `refresh_token` pegado (no hay login usuario/pass, verificado) — Task 8/14.
> 10. **Paginación:** `list_elements`/`por_expediente` deben iterar páginas (o exponer `page`/`itemsPerPage` y un helper), no una sola página — Task 7/8.
> 11. **Tests del server sin acoplarse a internals de FastMCP:** extraer la lógica de guard a funciones puras testeables (`ensure_allowed`, filtro de propiedades) y testear ESAS; un único smoke-test tolerante para el registro de tools. Pinnear rango de `mcp` — Task 11/12.
> 12. **Slugs VERIFICADOS en vivo (2026-07-13, Task 6):** `abogados_propios`/`abogados_contrarios` (no `abogados`→404), `extrajudiciales` (no `expedientes_extrajudiciales`→404), `juzgados` válido (200). `properties[]` obligatorio en el listado (default `["id"]`).
> 13. **Redacción de secretos en logs** + permisos restrictivos de `tokens.json` — Task 3/15.

---

## Task 1: Capturar el contrato de LOGIN inicial (discovery, en vivo)

`core` no implementa login usuario/contraseña (solo refresco). El endpoint de login es lo único del contrato de auth sin confirmar. Setup gesdinet/Lexik → casi seguro `POST /api/login_check`.

> ✅ **RESUELTO en la sesión de verificación (2026-07-13) — esta task queda como documentación.**
> NO hay endpoint estándar de login usuario/contraseña (`/api/login_check`, `/api/token`,
> `/api/auth/login`, `/api/login`… todos **404**). **Decisión:** el alta es por **`refresh_token`
> pegado** (Task 14); el plugin arranca el JWT con `POST /api/token/refresh` (verificado). El plugin
> **no maneja contraseña**. Automatizar el login de cero (frontal + posible CSRF) queda fuera de
> alcance salvo disparador.

**Files:**
- Create: `plugins/sudespacho_mcp/AUTH_CONTRACT.md` (contrato de auth verificado; NO tokens)

- [ ] **Step 1: Escribir el contrato de auth (verificado)**

En `AUTH_CONTRACT.md`, documentar:
- **Alta:** pegar `refresh_token` (de localStorage del CRM del usuario) → `POST /api/token/refresh`.
- **Refresco:** `POST /api/token/refresh`, body `{"refresh_token": rt}` → `{"token": jwt, "refresh_token": rt2}` (rodante; funciona sin JWT vigente).
- **JWT:** 60 min, claims `iat, exp, roles, username`. Auth REST = `Authorization: Bearer <jwt>`, sin PHPSESSID.
- **NO** existe login usuario/contraseña por API (candidatos probados → 404).
- **NO** pegar tokens en `AUTH_CONTRACT.md` ni en el chat.

- [ ] **Step 2: Commit**

```bash
git add plugins/sudespacho_mcp/AUTH_CONTRACT.md
git commit -m "docs(sudespacho-mcp): contrato de auth verificado (alta por refresh_token; login usuario/pass no existe)"
```

---

## Task 2: Scaffold del paquete

**Files:**
- Create: `plugins/sudespacho_mcp/__init__.py`
- Create: `plugins/sudespacho_mcp/config.py`
- Create: `plugins/sudespacho_mcp/requirements.txt`
- Test: `tests/sudespacho_mcp/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_config.py
import os
from plugins.sudespacho_mcp import config

def test_home_default(monkeypatch, tmp_path):
    monkeypatch.delenv("SUDESPACHO_DESPACHO_HOME", raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config.home_dir() == tmp_path / ".sudespacho-despacho"

def test_home_override(monkeypatch, tmp_path):
    monkeypatch.setenv("SUDESPACHO_DESPACHO_HOME", str(tmp_path / "x"))
    assert config.home_dir() == tmp_path / "x"

def test_base_url_default(monkeypatch):
    monkeypatch.delenv("SUDESPACHO_BASE_URL", raising=False)
    assert config.base_url() == "https://api-crm-commons-pro.sudespacho.biz"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_config.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# plugins/sudespacho_mcp/__init__.py
# (vacío)
```

```python
# plugins/sudespacho_mcp/config.py
from __future__ import annotations
import os
from pathlib import Path

DEFAULT_BASE_URL = "https://api-crm-commons-pro.sudespacho.biz"

def home_dir() -> Path:
    override = os.getenv("SUDESPACHO_DESPACHO_HOME")
    if override:
        return Path(override)
    root = os.getenv("USERPROFILE") or os.getenv("HOME") or "."
    return Path(root) / ".sudespacho-despacho"

def base_url() -> str:
    return (os.getenv("SUDESPACHO_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

def tokens_path() -> Path:
    return home_dir() / "tokens.json"
```

```
# plugins/sudespacho_mcp/requirements.txt
mcp>=1.0
httpx>=0.27
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_config.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/__init__.py plugins/sudespacho_mcp/config.py plugins/sudespacho_mcp/requirements.txt tests/sudespacho_mcp/test_config.py
git commit -m "feat(sudespacho-mcp): scaffold del paquete + config (home/base_url)"
```

---

## Task 3: Almacén de tokens (persistencia local)

**Files:**
- Create: `plugins/sudespacho_mcp/token_store.py`
- Test: `tests/sudespacho_mcp/test_token_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_token_store.py
from plugins.sudespacho_mcp.token_store import TokenStore

def test_save_and_load_roundtrip(tmp_path):
    store = TokenStore(tmp_path / "tokens.json")
    store.save(jwt="J1", refresh="R1")
    assert store.load() == {"jwt": "J1", "refresh": "R1"}

def test_load_missing_returns_none(tmp_path):
    assert TokenStore(tmp_path / "nope.json").load() is None

def test_save_creates_parent_dir(tmp_path):
    store = TokenStore(tmp_path / "sub" / "tokens.json")
    store.save(jwt="J", refresh="R")
    assert (tmp_path / "sub" / "tokens.json").exists()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_token_store.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# plugins/sudespacho_mcp/token_store.py
from __future__ import annotations
import json
from pathlib import Path

class TokenStore:
    """Persiste JWT + refresh en disco local (UTF-8). Solo tokens, nunca contraseña."""
    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def load(self) -> dict | None:
        # Carga tolerante: fichero ausente/corrupto/truncado → None (degrada a NeedsLogin limpio,
        # no crash). Cubre la carrera de escritura entre procesos (Claude Code + puente Desktop).
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def save(self, *, jwt: str, refresh: str) -> None:
        # Escritura ATÓMICA: temp + os.replace (atómico en Windows) para no dejar el fichero
        # truncado si dos procesos escriben a la vez o hay un kill a mitad.
        import os, tempfile
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps({"jwt": jwt, "refresh": refresh}, ensure_ascii=False)
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp, self._path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        try:  # permisos restrictivos (best-effort; en Windows aplica icacls aparte si hace falta)
            os.chmod(self._path, 0o600)
        except OSError:
            pass
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_token_store.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/token_store.py tests/sudespacho_mcp/test_token_store.py
git commit -m "feat(sudespacho-mcp): almacen de tokens local"
```

---

## Task 4: Auth — login y refresco (httpx inyectable)

**Files:**
- Create: `plugins/sudespacho_mcp/auth.py`
- Test: `tests/sudespacho_mcp/test_auth.py`

Contrato: login `POST /api/login_check` body `{username, password}` → `{token, refresh_token}` (confirmar campos exactos en `AUTH_CONTRACT.md` de la Task 1 y ajustar `_LOGIN_PATH`/claves si difieren). Refresco `POST /api/token/refresh` body `{refresh_token}` → `{token, refresh_token}` (rodante).

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_auth.py
import httpx
from plugins.sudespacho_mcp.auth import login, refresh

def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api-crm-commons-pro.sudespacho.biz")

def test_login_returns_tokens():
    def handler(req):
        assert req.url.path == "/api/login_check"
        assert b"password" in req.content
        return httpx.Response(200, json={"token": "JWT1", "refresh_token": "RT1"})
    with _client(handler) as c:
        assert login(c, "user@x", "secret") == {"jwt": "JWT1", "refresh": "RT1"}

def test_refresh_returns_new_tokens():
    def handler(req):
        assert req.url.path == "/api/token/refresh"
        return httpx.Response(200, json={"token": "JWT2", "refresh_token": "RT2"})
    with _client(handler) as c:
        assert refresh(c, "RT1") == {"jwt": "JWT2", "refresh": "RT2"}

def test_refresh_failure_raises():
    def handler(req):
        return httpx.Response(401, json={"message": "expired"})
    with _client(handler) as c:
        import pytest
        with pytest.raises(Exception):
            refresh(c, "RT_bad")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_auth.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# plugins/sudespacho_mcp/auth.py
from __future__ import annotations
import httpx

_LOGIN_PATH = "/api/login_check"      # confirmar en AUTH_CONTRACT.md (Task 1)
_REFRESH_PATH = "/api/token/refresh"  # gesdinet/Lexik, rodante

class AuthError(RuntimeError):
    """Auth fallida de forma TERMINAL (401/credencial muerta) → NeedsLogin."""

class TransientAuthError(AuthError):
    """Fallo transitorio (5xx/timeout/red) → reintentar, NO forzar re-login."""

def _extract(data: dict, *, prev_refresh: str | None = None) -> dict:
    # TOLERANTE (como core._try_refresh_jwt_post): exigir solo el JWT; si no viene
    # refresh_token nuevo, conservar el anterior (el CRM puede no rotarlo en cada refresh).
    jwt = data.get("token") or data.get("@token") or data.get("access_token")
    if not jwt:
        raise AuthError("respuesta de auth sin token")
    rt = data.get("refresh_token") or data.get("@refreshToken") or prev_refresh
    if not rt:
        raise AuthError("respuesta de auth sin refresh_token y sin refresh previo")
    return {"jwt": jwt, "refresh": rt}

def login(client: httpx.Client, username: str, password: str) -> dict:
    try:
        r = client.post(_LOGIN_PATH, json={"username": username, "password": password})
    except httpx.HTTPError as e:
        raise TransientAuthError(f"login red/timeout: {e}") from e
    if r.status_code in (401, 403):
        raise AuthError(f"login rechazado HTTP {r.status_code}")
    if r.status_code >= 400:
        raise TransientAuthError(f"login HTTP {r.status_code}")
    return _extract(r.json())

def refresh(client: httpx.Client, refresh_token: str) -> dict:
    try:
        r = client.post(_REFRESH_PATH, json={"refresh_token": refresh_token})
    except httpx.HTTPError as e:
        raise TransientAuthError(f"refresh red/timeout: {e}") from e
    if r.status_code in (401, 403):
        raise AuthError(f"refresh_token caducado (HTTP {r.status_code}) → re-login")
    if r.status_code >= 400:
        raise TransientAuthError(f"refresh HTTP {r.status_code} (transitorio)")
    return _extract(r.json(), prev_refresh=refresh_token)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_auth.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/auth.py tests/sudespacho_mcp/test_auth.py
git commit -m "feat(sudespacho-mcp): auth login + refresh rodante (httpx inyectable)"
```

---

## Task 5: Proveedor de sesión (JWT vigente con refresco silencioso)

**Files:**
- Create: `plugins/sudespacho_mcp/session.py`
- Test: `tests/sudespacho_mcp/test_session.py`

Decodifica el `exp` del JWT; si faltan <60s o ya expiró, refresca (rodante) y persiste el nuevo par. Si el refresh falla → `NeedsLogin`.

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_session.py
import base64, json, time, httpx, pytest
from plugins.sudespacho_mcp.session import Session, NeedsLogin
from plugins.sudespacho_mcp.token_store import TokenStore

def _jwt(exp: int) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"h.{payload}.s"

def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x")

def test_valid_jwt_used_without_refresh(tmp_path):
    store = TokenStore(tmp_path / "t.json")
    store.save(jwt=_jwt(int(time.time()) + 3600), refresh="RT")
    def handler(req):
        raise AssertionError("no debe refrescar si el JWT es válido")
    sess = Session(store, _client(handler))
    assert sess.bearer().startswith("h.")

def test_expired_jwt_triggers_refresh_and_persists(tmp_path):
    store = TokenStore(tmp_path / "t.json")
    store.save(jwt=_jwt(int(time.time()) - 10), refresh="RT1")
    def handler(req):
        return httpx.Response(200, json={"token": _jwt(int(time.time()) + 3600), "refresh_token": "RT2"})
    sess = Session(store, _client(handler))
    _ = sess.bearer()
    assert store.load()["refresh"] == "RT2"  # rodante persistido

def test_refresh_failure_raises_needslogin(tmp_path):
    store = TokenStore(tmp_path / "t.json")
    store.save(jwt=_jwt(int(time.time()) - 10), refresh="RTbad")
    def handler(req):
        return httpx.Response(401, json={})
    with pytest.raises(NeedsLogin):
        Session(store, _client(handler)).bearer()

def test_no_tokens_raises_needslogin(tmp_path):
    with pytest.raises(NeedsLogin):
        Session(TokenStore(tmp_path / "none.json"), _client(lambda r: httpx.Response(200))).bearer()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_session.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# plugins/sudespacho_mcp/session.py
from __future__ import annotations
import base64, json, time, httpx
from .token_store import TokenStore
from . import auth

class NeedsLogin(RuntimeError):
    pass

def _jwt_exp(jwt: str) -> int | None:
    try:
        part = jwt.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part)).get("exp")
    except Exception:
        return None

class Session:
    """Da un Bearer JWT vigente; refresca (rodante) y persiste al caducar."""
    def __init__(self, store: TokenStore, client: httpx.Client, *, skew: int = 60) -> None:
        self._store = store
        self._client = client
        self._skew = skew

    def bearer(self) -> str:
        data = self._store.load()
        if not data:
            raise NeedsLogin("no hay tokens: ejecuta el login del plugin")
        exp = _jwt_exp(data["jwt"])
        if exp is None or exp - time.time() < self._skew:
            try:
                new = auth.refresh(self._client, data["refresh"])
            except auth.AuthError as e:
                raise NeedsLogin(str(e)) from e
            self._store.save(jwt=new["jwt"], refresh=new["refresh"])
            return new["jwt"]
        return data["jwt"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_session.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/session.py tests/sudespacho_mcp/test_session.py
git commit -m "feat(sudespacho-mcp): sesion con refresco silencioso rodante + NeedsLogin"
```

---

## Task 6: Catálogo / lista blanca (deny-by-default; contabilidad vetada)

**Files:**
- Create: `plugins/sudespacho_mcp/catalog.py`
- Test: `tests/sudespacho_mcp/test_catalog.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_catalog.py
import pytest
from plugins.sudespacho_mcp import catalog

FINANCIEROS = [
    "facturas", "facturas_proforma", "remesas", "facturas_recibidas",
    "cobros_clientes", "pagos_proveedores", "catalogo_conceptos_honorario",
    "conceptos_honorario", "conceptos_gasto", "conceptos_suplido",
    "conceptos_provision", "libros_oficiales", "nominas", "amortizaciones",
    "cuentas_contables",
]

def test_permitidos_incluye_lectura_legal():
    assert "clientes_propios" in catalog.ALLOWED
    assert "expedientes_judiciales" in catalog.ALLOWED

@pytest.mark.parametrize("slug", FINANCIEROS)
def test_financiero_no_permitido(slug):
    assert not catalog.is_allowed(slug)
    assert slug in catalog.VETADOS

def test_desconocido_denegado_por_defecto():
    assert not catalog.is_allowed("elemento_inventado_xyz")

def test_ensure_allowed_lanza_para_vetado():
    with pytest.raises(catalog.NotAllowed):
        catalog.ensure_allowed("nominas")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_catalog.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# plugins/sudespacho_mcp/catalog.py
from __future__ import annotations
import re

# Lista blanca de elementos de LECTURA permitidos (deny-by-default).
# ✅ Todos VERIFICADOS en vivo como `element_registries` válidos (200) el 2026-07-13.
# Correcciones de la verificación: `abogados` (a secas) NO existe (404) → `abogados_propios`/
# `abogados_contrarios`; `expedientes_extrajudiciales` NO existe (404) → `extrajudiciales`;
# `juzgados` SÍ es válido (200) — el 404 era del path de relación, no del listado.
ALLOWED: frozenset[str] = frozenset({
    "clientes_propios", "clientes_contrarios",
    "abogados_propios", "abogados_contrarios",
    "procuradores_propios", "procuradores_contrarios",
    "colaboradores", "organismos", "contactos", "poderes", "juzgados",
    "expedientes_judiciales", "extrajudiciales", "actuaciones",
    "notas_tecnicas", "tareas",
    "gdocu",  # documentos: necesario para obtener doc_id en list_documentos/download
})

# Vetados explícitos (confidencial — NUNCA exponer). Doble negativa con ALLOWED.
VETADOS: frozenset[str] = frozenset({
    "facturas", "facturas_proforma", "remesas", "facturas_recibidas",
    "cobros_clientes", "pagos_proveedores", "catalogo_conceptos_honorario",
    "conceptos_honorario", "conceptos_gasto", "conceptos_suplido",
    "conceptos_provision", "conceptos_varios", "libros_oficiales",
    "nominas", "amortizaciones", "cuentas_contables",
})

# Fragmentos de slug financiero para vetar relaciones left./right.<slug>.<campo>.
_VETADO_FRAG = ("factura", "conceptos_", "conceptos_recibidas", "cobros", "pagos_proveedores",
                "nomina", "amortizacion", "cuentas_contables", "remesa", "libros_oficiales")
# Nombres de propiedad económicos vetados (confidencialidad por CAMPO, no solo por slug).
_VETADO_PROP = re.compile(
    r"(^|[._])(total|base_imponible|precio_unidad|importe|iva|irpf|cobro|pago|descuento)",
    re.IGNORECASE,
)

class NotAllowed(PermissionError):
    pass

def is_allowed(slug: str) -> bool:
    return slug in ALLOWED and slug not in VETADOS

def ensure_allowed(slug: str) -> None:
    if not is_allowed(slug):
        raise NotAllowed(f"elemento '{slug}' no permitido por el plugin (lista blanca / vetado)")

def is_property_allowed(prop: str) -> bool:
    p = prop.lower()
    if p.startswith("sum(") or p.startswith("count("):  # agregados sobre campos económicos
        inner = p[p.index("(") + 1 : p.rfind(")")]
        return is_property_allowed(inner)
    if any(frag in p for frag in _VETADO_FRAG):  # relación a slug vetado (left./right.<slug>.*)
        return False
    if _VETADO_PROP.search(p):                    # campo económico directo
        return False
    return True

def ensure_properties_allowed(props: list[str]) -> None:
    bad = [p for p in (props or []) if not is_property_allowed(p)]
    if bad:
        raise NotAllowed(f"propiedades económicas/vetadas no permitidas: {bad}")
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_catalog.py -v`
Expected: PASS (18 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/catalog.py tests/sudespacho_mcp/test_catalog.py
git commit -m "feat(sudespacho-mcp): lista blanca deny-by-default + contabilidad vetada"
```

---

## Task 7: Cliente REST de lectura (element_registries) — SIN borrado

**Files:**
- Create: `plugins/sudespacho_mcp/client.py`
- Test: `tests/sudespacho_mcp/test_client_read.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_client_read.py
import httpx
from plugins.sudespacho_mcp.client import SudespachoClient

class _FakeSession:
    def bearer(self): return "JWT"

def _client(handler):
    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x")
    return SudespachoClient(http, _FakeSession())

def test_list_elements_sends_bearer_and_parses_items():
    def handler(req):
        assert req.headers["authorization"] == "Bearer JWT"
        assert req.url.path == "/api/element_registries/clientes_propios"
        assert req.url.params["page"] == "1"
        return httpx.Response(200, json={
            "totalItems": 1, "currentPage": 1, "itemsPerPage": 10,
            "items": [{"id": 5, "values": [{"property": {"name": "nombre"}, "value": "ACME"}]}],
        })
    res = _client(handler).list_elements("clientes_propios", properties=["nombre"], page=1)
    assert res["totalItems"] == 1
    assert res["items"][0]["id"] == 5

def test_client_has_no_delete_method():
    # Regla dura: el cliente NO expone borrado.
    assert not any("delete" in n.lower() for n in dir(SudespachoClient))
    assert not any("borrar" in n.lower() for n in dir(SudespachoClient))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_client_read.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# plugins/sudespacho_mcp/client.py
from __future__ import annotations
import httpx

class SudespachoClient:
    """Cliente REST de LECTURA. Inyecta httpx + un proveedor de sesión (.bearer()).
    NO implementa ningún verbo de borrado (regla dura §5 del spec)."""
    def __init__(self, http: httpx.Client, session) -> None:
        self._http = http
        self._session = session

    def _get(self, path: str, params: list[tuple[str, str]] | dict | None = None):
        r = self._http.get(path, params=params,
                            headers={"Authorization": f"Bearer {self._session.bearer()}",
                                     "Accept": "application/json"})
        r.raise_for_status()
        return r.json()

    def list_elements(self, element: str, *, properties: list[str] | None = None,
                      page: int = 1, items_per_page: int = 10,
                      filter_group: list[tuple[str, str]] | None = None) -> dict:
        # `properties[]` es OBLIGATORIO en element_registries: omitirlo → HTTP 500
        # (verificado en vivo 2026-07-13). Default seguro: ["id"].
        props = properties or ["id"]
        params: list[tuple[str, str]] = [("page", str(page)),
                                         ("itemsPerPage", str(items_per_page)),
                                         ("return_totals", "false")]
        for i, p in enumerate(props):
            params.append((f"properties[{i}]", p))
        params.extend(filter_group or [])
        return self._get(f"/api/element_registries/{element}", params)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_client_read.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/client.py tests/sudespacho_mcp/test_client_read.py
git commit -m "feat(sudespacho-mcp): cliente REST list_elements + guard no-borrado"
```

---

## Task 8: Cliente — summary, autocomplete, por-expediente, detalle

**Files:**
- Modify: `plugins/sudespacho_mcp/client.py`
- Test: `tests/sudespacho_mcp/test_client_read2.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_client_read2.py
import httpx
from plugins.sudespacho_mcp.client import SudespachoClient

class _S:
    def bearer(self): return "JWT"

def _c(handler):
    return SudespachoClient(httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x"), _S())

def test_summary():
    def h(req):
        assert req.url.path == "/api/element_registries/summary/actuaciones"
        return httpx.Response(200, json={"items": []})
    assert _c(h).summary("actuaciones") == {"items": []}

def test_search_autocomplete():
    def h(req):
        assert req.url.path == "/autocompletar/buscar/elemento/colaboradores"
        assert req.url.params["term"] == "gar"
        return httpx.Response(200, json=[{"id": 1, "label": "García"}])
    assert _c(h).search("colaboradores", "gar")[0]["id"] == 1

def test_por_expediente_usa_filtro_associated():
    captured = {}
    def h(req):
        captured["q"] = str(req.url)
        return httpx.Response(200, json={"items": []})
    _c(h).por_expediente("actuaciones", 671)
    assert "associated" in captured["q"] and "671" in captured["q"]

def test_get_detalle_usa_properties_coma():
    # Hipótesis del workaround del bug 500: forma coma en el SINGULAR.
    def h(req):
        assert req.url.path == "/api/element_register/expedientes_judiciales/671"
        assert req.url.params["properties"] == "id,Numero_Expediente"
        return httpx.Response(200, json={"id": 671})
    assert _c(h).get_detalle("expedientes_judiciales", 671, ["id", "Numero_Expediente"])["id"] == 671
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_client_read2.py -v`
Expected: FAIL (métodos no existen).

- [ ] **Step 3: Write minimal implementation (añadir a `client.py`)**

```python
    def summary(self, element: str, *, filter_group=None) -> dict:
        return self._get(f"/api/element_registries/summary/{element}", filter_group or None)

    def search(self, element: str, term: str) -> list:
        return self._get(f"/autocompletar/buscar/elemento/{element}", {"term": term})

    def por_expediente(self, element: str, exp_id: int, *, direccion: str = "left",
                       properties: list[str] | None = None) -> dict:
        params: list[tuple[str, str]] = [
            ("filterGroup[condition]", "AND"),
            ("filterGroup[filterGroups][0][filters][0][operator]", "associated"),
            ("filterGroup[filterGroups][0][filters][0][property]", f"{direccion}.{element}.id"),
            ("filterGroup[filterGroups][0][filters][0][value]", str(exp_id)),
        ]
        for i, p in enumerate(properties or []):
            params.append((f"properties[{i}]", p))
        return self._get(f"/api/element_registries/{element}", params)

    def get_detalle(self, element: str, id_: int, properties: list[str]) -> dict:
        # Workaround bug 500: forma COMA (no properties[]). Hipótesis de El Contable.
        return self._get(f"/api/element_register/{element}/{id_}",
                         {"properties": ",".join(properties)})
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_client_read2.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/client.py tests/sudespacho_mcp/test_client_read2.py
git commit -m "feat(sudespacho-mcp): summary/search/por-expediente/detalle (coma workaround)"
```

---

## Task 9: Documentos — URL de descarga y descarga a DL-root

**Files:**
- Modify: `plugins/sudespacho_mcp/client.py`
- Create: `plugins/sudespacho_mcp/download.py`
- Test: `tests/sudespacho_mcp/test_download.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_download.py
import hashlib, httpx, pytest
from plugins.sudespacho_mcp.client import SudespachoClient
from plugins.sudespacho_mcp.download import resolve_dest, DownloadRootError

class _S:
    def bearer(self): return "JWT"

def _c(handler):
    return SudespachoClient(httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x"), _S())

def test_download_uri_extrae_presigned():
    def h(req):
        assert req.url.path == "/api/documents/42/downloadUri"
        return httpx.Response(200, json={"presignedDownloadUrl": "https://s3/x?sig=1"})
    assert _c(h).document_download_url(42) == "https://s3/x?sig=1"

def test_resolve_dest_dentro_del_root(tmp_path):
    root = tmp_path / "dl"
    dest = resolve_dest(root, "sub/f.pdf")
    assert str(dest).startswith(str(root.resolve()))

def test_resolve_dest_symlink_escape_bloqueado(tmp_path):
    root = tmp_path / "dl"
    with pytest.raises(DownloadRootError):
        resolve_dest(root, "../../escape.pdf")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_download.py -v`
Expected: FAIL (módulos/métodos no existen).

- [ ] **Step 3: Write minimal implementation**

En `client.py` añadir:

```python
    def document_download_url(self, doc_id: int) -> str:
        data = self._get(f"/api/documents/{doc_id}/downloadUri")
        url = data.get("presignedDownloadUrl") or data.get("presignedUrl")
        if not url:
            raise RuntimeError(f"downloadUri doc {doc_id}: sin presignedDownloadUrl")
        return url
```

```python
# plugins/sudespacho_mcp/download.py
from __future__ import annotations
import hashlib, os, httpx
from pathlib import Path

class DownloadRootError(PermissionError):
    pass

def resolve_dest(root: Path, rel: str) -> Path:
    root = Path(root).resolve()
    dest = (root / rel).resolve()
    if os.path.commonpath([str(root), str(dest)]) != str(root):
        raise DownloadRootError(f"ruta fuera del DL-root: {rel}")
    return dest

def download_to(url: str, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    # timeout + follow_redirects como core._download_url_raw: S3/CloudFront puede redirigir,
    # y sin timeout una descarga lenta cuelga indefinidamente.
    with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as r:  # URL S3 prefirmada
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes():
                h.update(chunk)
                f.write(chunk)
    return {"path": str(dest), "sha256": h.hexdigest(), "bytes": dest.stat().st_size}
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_download.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/client.py plugins/sudespacho_mcp/download.py tests/sudespacho_mcp/test_download.py
git commit -m "feat(sudespacho-mcp): downloadUri + descarga a DL-root con sha256 (sin bytes por el modelo)"
```

---

## Task 10: Introspección `describe_element`

**Files:**
- Create: `plugins/sudespacho_mcp/discovery.py`
- Test: `tests/sudespacho_mcp/test_discovery.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_discovery.py
import httpx
from plugins.sudespacho_mcp.client import SudespachoClient
from plugins.sudespacho_mcp.discovery import describe_element

class _S:
    def bearer(self): return "JWT"

def _c(handler):
    return SudespachoClient(httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x"), _S())

def test_describe_element_junta_view_y_muestra():
    def h(req):
        if req.url.path == "/api/view/complete/organismos":
            return httpx.Response(200, json={"properties": [{"name": "nombre"}, {"name": "cif"}]})
        if req.url.path == "/api/element_registries/organismos":
            return httpx.Response(200, json={"items": [{"values": [{"property": {"name": "nombre"}, "value": "X"}]}]})
        return httpx.Response(404)
    ficha = describe_element(_c(h), "organismos")
    assert "nombre" in ficha["propiedades"]
    assert ficha["slug"] == "organismos"
    # SOLO esquema: no expone valores de registros (nada de "X" de la muestra).
    assert "muestra_n" not in ficha
    import json as _j
    assert "X" not in _j.dumps(ficha)  # el valor del registro NO aparece
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_discovery.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# plugins/sudespacho_mcp/discovery.py
from __future__ import annotations

def describe_element(client, element: str) -> dict:
    """Borrador de ficha de catálogo para revisión humana. SOLO ESQUEMA: nombres de propiedad
    (y tipos si el CRM los da), NUNCA valores de registros (evita volcar importes/PII al chat)."""
    props: dict[str, str] = {}
    try:
        view = client._get(f"/api/view/complete/{element}")
        for p in view.get("properties", []):
            if p.get("name"):
                props[p["name"]] = p.get("type", "")
    except Exception:
        pass
    if not props:
        # Fallback: SOLO los NOMBRES de propiedad de una muestra; se descartan los valores.
        muestra = client.list_elements(element, page=1, items_per_page=1)
        for it in muestra.get("items", []):
            for v in it.get("values", []):
                name = (v.get("property") or {}).get("name")
                if name:
                    props.setdefault(name, "")
    return {"slug": element, "propiedades": sorted(props.keys()), "tipos": props}
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_discovery.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/discovery.py tests/sudespacho_mcp/test_discovery.py
git commit -m "feat(sudespacho-mcp): describe_element (introspeccion → borrador de ficha)"
```

---

## Task 11: Server FastMCP — tools de lectura + lista blanca + sin tool de borrado

**Files:**
- Create: `plugins/sudespacho_mcp/server.py`
- Test: `tests/sudespacho_mcp/test_server.py`

`build_server()` inyecta cliente + sesión para testear sin API viva (patrón `email_export_mcp`). Cada tool de elemento pasa por `catalog.ensure_allowed`.

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_server.py
import pytest
from plugins.sudespacho_mcp.server import build_server
from plugins.sudespacho_mcp import catalog

class _FakeClient:
    def list_elements(self, element, **kw): return {"element": element, "items": []}
    def list_element_types(self): return sorted(catalog.ALLOWED)

def _tools(server):
    return {t.name for t in server._tool_manager.list_tools()}

def test_no_hay_tool_de_borrado():
    names = _tools(build_server(client=_FakeClient()))
    assert not any("delete" in n or "borrar" in n or "remove" in n for n in names)

def test_list_elements_rechaza_vetado():
    server = build_server(client=_FakeClient())
    fn = server._tool_manager.get_tool("list_elements").fn
    with pytest.raises(catalog.NotAllowed):
        fn(element="nominas")

def test_list_elements_permite_legal():
    server = build_server(client=_FakeClient())
    fn = server._tool_manager.get_tool("list_elements").fn
    assert fn(element="clientes_propios")["element"] == "clientes_propios"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_server.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# plugins/sudespacho_mcp/server.py
from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from . import catalog

def build_server(*, client) -> FastMCP:
    mcp = FastMCP("sudespacho")

    @mcp.tool()
    def list_element_types() -> list[str]:
        """Lista los tipos de elemento CRM permitidos (lista blanca)."""
        return client.list_element_types()

    @mcp.tool()
    def list_elements(element: str, page: int = 1, items_per_page: int = 10) -> dict:
        """Lista registros de un tipo de elemento permitido del CRM."""
        catalog.ensure_allowed(element)
        return client.list_elements(element, page=page, items_per_page=items_per_page)

    # NOTA: no se registra NINGUNA tool de borrado (regla dura §5).
    return mcp
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_server.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/server.py tests/sudespacho_mcp/test_server.py
git commit -m "feat(sudespacho-mcp): server FastMCP con lista blanca y sin tool de borrado"
```

---

## Task 12: Tools restantes en el server (search/summary/por-expediente/detalle/documentos/describe)

**Files:**
- Modify: `plugins/sudespacho_mcp/server.py`
- Test: `tests/sudespacho_mcp/test_server_tools.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_server_tools.py
import pytest
from plugins.sudespacho_mcp.server import build_server
from plugins.sudespacho_mcp import catalog

class _FakeClient:
    def search(self, element, term): return [{"element": element, "term": term}]
    def summary(self, element, **kw): return {"element": element}
    def por_expediente(self, element, exp_id, **kw): return {"element": element, "exp": exp_id}
    def get_detalle(self, element, id_, properties): return {"id": id_}
    def document_download_url(self, doc_id): return "https://s3/x"
    def describe(self, element): return {"slug": element}

def _fn(server, name):
    return server._tool_manager.get_tool(name).fn

def test_search_respeta_lista_blanca():
    fn = _fn(build_server(client=_FakeClient()), "search_elements")
    with pytest.raises(catalog.NotAllowed):
        fn(element="facturas", term="x")
    assert fn(element="colaboradores", term="x")[0]["term"] == "x"

def test_describe_element_respeta_lista_blanca():
    fn = _fn(build_server(client=_FakeClient()), "describe_element")
    with pytest.raises(catalog.NotAllowed):
        fn(element="cuentas_contables")
    assert fn(element="organismos")["slug"] == "organismos"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_server_tools.py -v`
Expected: FAIL (tools no existen).

- [ ] **Step 3: Write minimal implementation (añadir tools a `build_server`)**

```python
    @mcp.tool()
    def search_elements(element: str, term: str) -> list:
        """Autocomplete de un tipo de elemento permitido."""
        catalog.ensure_allowed(element)
        return client.search(element, term)

    @mcp.tool()
    def get_element_summary(element: str) -> dict:
        """Agregado/resumen de un tipo de elemento permitido."""
        catalog.ensure_allowed(element)
        return client.summary(element)

    @mcp.tool()
    def list_elements_por_expediente(element: str, exp_id: int) -> dict:
        """Elementos de un tipo permitido asociados a un expediente."""
        catalog.ensure_allowed(element)
        return client.por_expediente(element, exp_id)

    @mcp.tool()
    def get_expediente_detalle(element: str, id: int, properties: list[str]) -> dict:
        """Detalle de un registro (forma coma; workaround del bug 500)."""
        catalog.ensure_allowed(element)
        return client.get_detalle(element, id, properties)

    @mcp.tool()
    def get_document_download_url(doc_id: int) -> str:
        """URL S3 prefirmada para descargar un documento del CRM."""
        return client.document_download_url(doc_id)

    @mcp.tool()
    def describe_element(element: str) -> dict:
        """Borrador de ficha (propiedades reales) de un elemento permitido."""
        catalog.ensure_allowed(element)
        return client.describe(element)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_server_tools.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/server.py tests/sudespacho_mcp/test_server_tools.py
git commit -m "feat(sudespacho-mcp): tools de lectura restantes (todas con lista blanca)"
```

---

## Task 13: Adaptador de cliente para el server (`list_element_types` + `describe`) y cableado de arranque

**Files:**
- Modify: `plugins/sudespacho_mcp/client.py` (añadir `list_element_types`, `describe`)
- Modify: `plugins/sudespacho_mcp/server.py` (fábrica real `create_server()`)
- Create: `plugins/sudespacho_mcp/__main__.py`
- Test: `tests/sudespacho_mcp/test_client_adapter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_client_adapter.py
import httpx
from plugins.sudespacho_mcp.client import SudespachoClient
from plugins.sudespacho_mcp import catalog

class _S:
    def bearer(self): return "JWT"

def test_list_element_types_es_la_lista_blanca():
    c = SudespachoClient(httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})), base_url="https://x"), _S())
    assert set(c.list_element_types()) == set(catalog.ALLOWED)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_client_adapter.py -v`
Expected: FAIL (método no existe).

- [ ] **Step 3: Write minimal implementation**

En `client.py`:

```python
    def list_element_types(self) -> list[str]:
        from . import catalog
        return sorted(catalog.ALLOWED)

    def describe(self, element: str) -> dict:
        from .discovery import describe_element
        return describe_element(self, element)
```

En `server.py` añadir la fábrica real:

```python
def create_server():
    import httpx
    from .config import base_url, tokens_path
    from .token_store import TokenStore
    from .session import Session
    from .client import SudespachoClient
    http = httpx.Client(base_url=base_url(), timeout=30.0)
    session = Session(TokenStore(tokens_path()), http)
    return build_server(client=SudespachoClient(http, session))
```

```python
# plugins/sudespacho_mcp/__main__.py
from .server import create_server
if __name__ == "__main__":
    create_server().run()
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_client_adapter.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/client.py plugins/sudespacho_mcp/server.py plugins/sudespacho_mcp/__main__.py tests/sudespacho_mcp/test_client_adapter.py
git commit -m "feat(sudespacho-mcp): adaptador de cliente + fabrica de server + entrypoint"
```

---

## Task 14: CLI de login (alta de cuenta, una vez)

**Files:**
- Create: `plugins/sudespacho_mcp/sudespacho_cli.py`
- Test: `tests/sudespacho_mcp/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sudespacho_mcp/test_cli.py
import httpx
from plugins.sudespacho_mcp import sudespacho_cli
from plugins.sudespacho_mcp.token_store import TokenStore

def test_do_connect_bootstrapea_desde_refresh_token(tmp_path):
    # Alta = pegar el refresh_token; el plugin arranca el JWT con POST /api/token/refresh.
    def handler(req):
        assert req.url.path == "/api/token/refresh"
        return httpx.Response(200, json={"token": "J", "refresh_token": "R2"})
    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x")
    store = TokenStore(tmp_path / "t.json")
    sudespacho_cli.do_connect(http, store, "RT_pegado")
    assert store.load() == {"jwt": "J", "refresh": "R2"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sudespacho_mcp/test_cli.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# plugins/sudespacho_mcp/sudespacho_cli.py
from __future__ import annotations
import getpass, sys, httpx
from .auth import refresh
from .token_store import TokenStore
from .config import base_url, tokens_path

def do_connect(http: httpx.Client, store: TokenStore, refresh_token: str) -> None:
    # Alta por refresh_token (no hay endpoint de login usuario/contraseña — verificado 2026-07-13).
    # POST /api/token/refresh arranca el JWT y (si es rodante) devuelve un refresh nuevo.
    tokens = refresh(http, refresh_token)
    store.save(jwt=tokens["jwt"], refresh=tokens["refresh"])

def main() -> int:
    print("Conectar cuenta sudespacho.")
    print("En el CRM web (ya logueado): DevTools → Application → Local Storage →")
    print("copia el valor de 'refresh_token' y pégalo aquí. NO se pide tu contraseña.")
    rt = getpass.getpass("refresh_token: ").strip()  # oculto; no se registra
    with httpx.Client(base_url=base_url(), timeout=30.0) as http:
        do_connect(http, TokenStore(tokens_path()), rt)
    print(f"OK. Tokens guardados en {tokens_path()}. La sesión se refrescará sola.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sudespacho_mcp/test_cli.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/sudespacho_cli.py tests/sudespacho_mcp/test_cli.py
git commit -m "feat(sudespacho-mcp): CLI de login (guarda solo tokens, nunca la contraseña)"
```

---

## Task 15: Empaquetado — `run_server.bat`, `.dxt`, README

**Files:**
- Create: `plugins/sudespacho_mcp/run_server.bat`
- Create: `plugins/sudespacho_mcp/dxt-build/manifest.json`
- Create: `plugins/sudespacho_mcp/README.md`

- [ ] **Step 1: `run_server.bat` (patrón google_despacho, stderr al log)**

```bat
@echo off
REM Wrapper de arranque del MCP sudespacho para Claude Desktop.
REM stdout (fd1) queda para el pipe JSON-RPC de MCP; stderr al log.
C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe -m plugins.sudespacho_mcp 2>>"%APPDATA%\Claude\sudespacho-mcp.log"
```

- [ ] **Step 2: `dxt-build/manifest.json` (calcado del de google_despacho)**

```json
{
  "dxt_version": "0.1",
  "name": "sudespacho",
  "version": "0.1.0",
  "description": "CRM sudespacho (lectura) — cuenta personal del usuario",
  "server": {
    "type": "python",
    "entry_point": "plugins/sudespacho_mcp/__main__.py",
    "mcp_config": {
      "command": "run_server.bat"
    }
  }
}
```

- [ ] **Step 3: `README.md`**

Documentar: propósito (lectura CRM), Modelo B (login una vez con `python -m plugins.sudespacho_mcp.sudespacho_cli`), variables de entorno (`SUDESPACHO_BASE_URL`, `SUDESPACHO_DESPACHO_HOME`, `SUDESPACHO_DL_ROOT`), lista blanca (contabilidad vetada), no-borrado, y los gates de despliegue (rol abogado, licencia, vida del refresh). Enlazar el spec.

- [ ] **Step 4: Verificar arranque import-safe**

Run: `python -c "import plugins.sudespacho_mcp.server as s; s.create_server()"`
Expected: sin error de import (aunque no haya tokens; el fallo de sesión es en tiempo de llamada, no de arranque).

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/run_server.bat plugins/sudespacho_mcp/dxt-build/manifest.json plugins/sudespacho_mcp/README.md
git commit -m "feat(sudespacho-mcp): empaquetado .dxt + run_server.bat + README"
```

---

## Task 16: Suite verde + gitignore de tokens + nota de gates

**Files:**
- Modify: `.gitignore` (si hace falta), `plugins/sudespacho_mcp/README.md`

- [ ] **Step 1: Asegurar que los tokens nunca se commitean**

Confirmar que `~/.sudespacho-despacho/` está fuera del repo (lo está: es el HOME del usuario). Añadir a `.gitignore` una regla defensiva por si alguien pusiera `SUDESPACHO_DESPACHO_HOME` dentro del repo:

```
# tokens del MCP sudespacho (nunca al repo)
**/.sudespacho-despacho/
**/tokens.json
```

- [ ] **Step 2: Suite completa**

Run: `python -m pytest -q`
Expected: toda la suite verde (incluidos los ~30 tests nuevos del plugin). Si algún módulo del plugin no colecciona por falta de `mcp`, usar `importorskip("mcp")` en `test_server*.py` (patrón del repo).

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore(sudespacho-mcp): gitignore defensivo de tokens"
```

- [ ] **Step 4: Gates de DESPLIEGUE (documentar, no bloquean el build)**

En el `README.md`, sección "Antes de dar F1 por viva en producción":
1. **Rol abogado:** con un usuario de rol abogado, confirmar 403/vacío en un elemento financiero (la lista blanca es 2ª barrera; el CRM debe ser la 1ª).
2. **Licencia (4 concurrentes):** confirmar con sudespacho si la sesión del MCP consume licencia (Nikolai, en curso).
3. **Vida del `refresh_token`** (opaco): medir; mitigado por el refresco rodante.
4. **Check de integración manual:** login real + `list_elements("clientes_propios")` + `describe_element` + descarga de un documento a DL-root, contra el CRM real.

- [ ] **Step 5: Commit**

```bash
git add plugins/sudespacho_mcp/README.md
git commit -m "docs(sudespacho-mcp): gates de despliegue en README"
```

---

## Cierre

- Actualizar `PLAN.md` `[SIGUIENTE-MCP-SUDESPACHO]`: F1 marcada según avance + hash del PR.
- Abrir PR (rama actual), pasar `leak-scan`, mergear con `--squash --delete-branch`.
- Instalar el `.dxt` en Claude Desktop y cablear; ejecutar el check de integración manual (Task 16.4).
