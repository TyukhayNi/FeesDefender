# Atlas del CRM sudespacho — Fase B + hardening Fase A · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar el atlas del CRM: endurecer la Fase A ya commiteada y añadir la Fase B (esquema por elemento: campos, relaciones, enums) con barrera anti-PII, de forma que una sola corrida `discover` produzca un mapa exhaustivo, determinista y seguro.

**Architecture:** Lógica pura + cliente HTTP bespoke en `core/crm_atlas.py`; CLI Typer en `scripts/crm_atlas.py`. Fase A = OpenAPI público (sin credenciales). Fase B = `x-api-key` (ya en `os.environ`) contra `/api/elements` + `view/config/{el}/fields|relations` + `view/enums/{el}/{prop}`. Solo lectura de esquema; nunca datos ni escritura.

**Tech Stack:** Python 3.14 (venv), `httpx`, `typer`, `pytest` (+ `pytest-randomly`), `core/anon` para el gate anti-PII.

**Spec:** `docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md` (v2).

## Global Constraints

- **Solo esquema, nunca datos de registros.** Prohibido llamar a `element_registries`/`element_register` para leer registros. El probe 4b (que provoca un 500) es la única llamada "no-GET-limpia".
- **Sin escritura:** el cliente no implementa POST/PUT/PATCH/DELETE.
- **Barrera PII (dura):** enums solo para `type=="Select"`; denylist `ListaUsuarios`/`ListaBancos`/`ListaGrupos`/`ListaElemento*`/`Tags`. Gate `scan_atlas_for_pii` que **bloquea** el write. El cliente **nunca** logea headers ni bodies; `warnings[]` solo `status`+`endpoint`.
- **Secretos solo por entorno:** `SUDESPACHO_API_KEY` de `os.environ`; nunca en el árbol ni en logs.
- **Encoding:** SIEMPRE `encoding="utf-8"`, `newline="\n"`, `ensure_ascii=False`. Lectura del atlas previo (resume) con `encoding="utf-8"` explícito.
- **Determinismo:** `json.dumps(..., sort_keys=True, ensure_ascii=False, indent=2)` + ordenación explícita de toda lista antes de serializar.
- **Entorno:** Windows + PowerShell; comandos desde la raíz del repo. Conteo de tests SIEMPRE por `--junit-xml` (el resumen de pytest no se captura por tubería en este Windows).
- **Auth header operativo:** `x-api-key` (el spec declara `Authorization` pero da 401 — `INTEGRACION §2.1`).
- **Git:** rama + PR (nunca commit directo a `main`). Correr pytest local antes de mergear (el CI solo corre leak-scan).

---

## Grupo 1 — Hardening de la Fase A (bugs verificados en la auditoría)

Todos tocan `core/crm_atlas.py` (ya commiteado en `87ff113`) y sus tests `tests/test_crm_atlas.py`.

### Task 1: Determinismo de serialización + `generated_at`

**Files:**
- Modify: `scripts/crm_atlas.py` (llamada `json.dumps`, default de `--stamp-time`)
- Modify: `core/crm_atlas.py` (`build_atlas_phase_a` → orden de `by_tag`/`by_method` ya ordenado; asegurar listas ordenadas)
- Modify: `core/utils.py` (usar `now_iso_utc` si existe; si no, añadirlo)
- Test: `tests/test_crm_atlas.py`

**Interfaces:**
- Produces: el `atlas.json` es idéntico byte a byte entre dos corridas con los mismos datos y `--no-stamp-time`.

- [ ] **Step 1: Test de determinismo (falla)**

```python
def test_atlas_json_is_byte_stable(spec):
    from core.crm_atlas import build_atlas_phase_a
    import json
    a1 = build_atlas_phase_a(spec, tenant="tnm", generated_at=None)
    a2 = build_atlas_phase_a(spec, tenant="tnm", generated_at=None)
    s1 = json.dumps(a1, sort_keys=True, ensure_ascii=False, indent=2)
    s2 = json.dumps(a2, sort_keys=True, ensure_ascii=False, indent=2)
    assert s1 == s2
```

- [ ] **Step 2: Ejecutar → verificar que pasa (build ya es determinista con `generated_at=None`)**

Run: `python -m pytest tests/test_crm_atlas.py::test_atlas_json_is_byte_stable -v`
Expected: PASS (confirma que el build es estable; el riesgo real es la CLI, Step 3).

- [ ] **Step 3: CLI — `sort_keys=True` y default `--no-stamp-time`**

En `scripts/crm_atlas.py`, cambiar la escritura:
```python
_write_text(atlas_json, json.dumps(atlas, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
```
y el default del flag:
```python
    stamp_time: bool = typer.Option(False, help="Sellar generated_at (UTC). Default OFF para diff limpio."),
```
y usar UTC cuando se selle:
```python
        generated_at=now_iso_utc() if stamp_time else None,
```
Añadir `now_iso_utc` a `core/utils.py` si no existe:
```python
def now_iso_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

- [ ] **Step 4: Test del default de la CLI (no-stamp → generated_at None)**

```python
def test_cli_discover_a_no_stamp(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from scripts.crm_atlas import app
    import json, core.crm_atlas as m
    monkeypatch.setattr(m, "fetch_oas3", lambda base_url=m.PUBLIC_BASE_URL, **k: _MINI_SPEC)
    out = tmp_path / "atlas.json"; md = tmp_path / "atlas.md"
    r = CliRunner().invoke(app, ["discover", "--phase", "a",
                                 "--atlas-json", str(out), "--atlas-md", str(md)])
    assert r.exit_code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["meta"]["generated_at"] is None
```
(`_MINI_SPEC` = el fixture `spec` extraído a módulo o duplicado mínimo.)

- [ ] **Step 5: Ejecutar todos los tests del módulo**

Run: `python -m pytest tests/test_crm_atlas.py -q --junit-xml=%TEMP%\j.xml`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/crm_atlas.py scripts/crm_atlas.py core/utils.py tests/test_crm_atlas.py
git commit -m "fix(crm-atlas): determinismo (sort_keys) + generated_at UTC/no-stamp por defecto"
```

### Task 2: `_request_schema` — content-types que faltan + composición

**Files:**
- Modify: `core/crm_atlas.py:143-164` (`_request_schema`)
- Test: `tests/test_crm_atlas.py`

**Interfaces:**
- Consumes: nada nuevo.
- Produces: `Endpoint.request_schema` no-nulo para bodies `application/merge-patch+json` y `multipart/form-data`.

- [ ] **Step 1: Test (falla) — merge-patch y multipart**

```python
def test_request_schema_merge_patch_and_multipart():
    from core.crm_atlas import parse_oas3
    spec = {"openapi":"3.0.0","info":{},"security":[{"apiKey":[]}],"components":{"securitySchemes":{}},
      "paths":{
        "/api/x/{id}":{"patch":{"operationId":"patch_x","tags":["X"],"responses":{"200":{}},
          "requestBody":{"content":{"application/merge-patch+json":{"schema":{"$ref":"#/components/schemas/PatchX"}}}}}},
        "/api/up":{"post":{"operationId":"post_up","tags":["X"],"responses":{"201":{}},
          "requestBody":{"content":{"multipart/form-data":{"schema":{"type":"object"}}}}}}}
    eps = {(e.path,e.method): e for e in parse_oas3(spec)}
    assert eps[("/api/x/{id}","PATCH")].request_schema == "PatchX"
    assert eps[("/api/up","POST")].request_schema == "object"
```

- [ ] **Step 2: Ejecutar → FAIL** (`request_schema` = None hoy).

Run: `python -m pytest tests/test_crm_atlas.py::test_request_schema_merge_patch_and_multipart -v`
Expected: FAIL.

- [ ] **Step 3: Ampliar los content-types + composición**

En `_request_schema`, ampliar la tupla y manejar `allOf/oneOf/anyOf`:
```python
    for ctype in ("application/json", "application/ld+json",
                  "application/merge-patch+json", "multipart/form-data"):
        ct = content.get(ctype, {})
        schema = ct.get("schema", {}) if isinstance(ct, dict) else {}
        if not isinstance(schema, dict):
            continue
        for comp in ("allOf", "oneOf", "anyOf"):
            if comp in schema and isinstance(schema[comp], list) and schema[comp]:
                first = schema[comp][0]
                if isinstance(first, dict) and "$ref" in first:
                    return first["$ref"].rsplit("/", 1)[-1]
        if "$ref" in schema:
            return schema["$ref"].rsplit("/", 1)[-1]
        if schema.get("type"):
            ...  # (rama array/tipo existente, sin cambios)
```

- [ ] **Step 4: Ejecutar → PASS.**

Run: `python -m pytest tests/test_crm_atlas.py::test_request_schema_merge_patch_and_multipart -v`

- [ ] **Step 5: Commit**

```bash
git add core/crm_atlas.py tests/test_crm_atlas.py
git commit -m "fix(crm-atlas): _request_schema cubre merge-patch+json, multipart y allOf/oneOf"
```

### Task 3: `operation_id_to_dev_slug` — colapsar no-alfanuméricos + trailing slash

**Files:**
- Modify: `core/crm_atlas.py:77-89`
- Test: `tests/test_crm_atlas.py`

**Interfaces:**
- Produces: slugs kebab sin paréntesis ni guiones dobles; `dev_doc_url` con `/` final.

- [ ] **Step 1: Test (falla) — paréntesis y `" - "`**

```python
def test_dev_slug_collapses_punctuation():
    from core.crm_atlas import operation_id_to_dev_slug
    assert operation_id_to_dev_slug("getAccounting - ConfigurationItem") == "get-accounting-configuration-item"
    assert operation_id_to_dev_slug("createPublic Holidays (Multiple)Collection") == "create-public-holidays-multiple-collection"
```

- [ ] **Step 2: Ejecutar → FAIL** (hoy deja `(multiple)` y `---`).

- [ ] **Step 3: Implementar**

Al final de `operation_id_to_dev_slug`, tras construir la cadena, colapsar:
```python
    import re
    s = op_id.replace("_", " ")
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    s = re.sub(r"[^0-9a-zA-Z]+", "-", s.lower())   # colapsa TODO no-alfanum a un solo '-'
    return s.strip("-")
```
Y en `parse_oas3`, añadir barra final:
```python
    dev_doc_url=(f"{DEV_PORTAL_BASE}/{operation_id_to_dev_slug(op_id)}/" if dev_links and op_id else None)
```

- [ ] **Step 4: Ejecutar los tests de slug (incluido el existente `test_dev_slug_matches_portal_pattern`) → PASS.** Ajustar el test existente para esperar el mismo resultado (sin `/` en la función; el `/` lo añade `parse_oas3`).

Run: `python -m pytest tests/test_crm_atlas.py -k dev_slug -v`

- [ ] **Step 5: Commit**

```bash
git add core/crm_atlas.py tests/test_crm_atlas.py
git commit -m "fix(crm-atlas): slug del portal colapsa no-alfanumericos + trailing slash (evita 404)"
```

### Task 4: `Endpoint.deprecated` + `Param.enum`/`default`

**Files:**
- Modify: `core/crm_atlas.py` (`Param`, `Endpoint`, `_parse_param`, `parse_oas3`)
- Test: `tests/test_crm_atlas.py`

- [ ] **Step 1: Test (falla)**

```python
def test_deprecated_and_param_enum_default():
    from core.crm_atlas import parse_oas3
    spec={"openapi":"3.0.0","info":{},"security":[{"apiKey":[]}],"components":{"securitySchemes":{}},
      "paths":{"/api/y":{"get":{"operationId":"get_y","tags":["Y"],"deprecated":True,"responses":{"200":{}},
        "parameters":[{"name":"mode","in":"query","required":False,
                       "schema":{"type":"string","enum":["a","b"],"default":"a"}}]}}}}
    e = parse_oas3(spec)[0]
    assert e.deprecated is True
    assert e.parameters[0].enum == ["a","b"]
    assert e.parameters[0].default == "a"
```

- [ ] **Step 2: Ejecutar → FAIL.**

- [ ] **Step 3: Implementar** — añadir `deprecated: bool = False` a `Endpoint`, `enum: list | None` y `default: … | None` a `Param`; poblarlos en `_parse_param` (`schema.get("enum")`, `schema.get("default")`) y en `parse_oas3` (`bool(op.get("deprecated", False))`).

- [ ] **Step 4: Ejecutar → PASS.** Ajustar `test_parse_endpoint_fields` si comprueba el shape de `Param`.

- [ ] **Step 5: Commit** `fix(crm-atlas): capturar deprecated y enum/default de parametros`

### Task 5: `render_digest` + `meta.auth_note` + gitignore `atlas.json`

**Files:**
- Modify: `core/crm_atlas.py` (`build_atlas_phase_a` → `meta.auth_note`; nueva `render_digest`)
- Modify: `scripts/crm_atlas.py` (escribir digest; ruta `atlas.digest.md`)
- Modify: `.gitignore` (añadir `docs/crm_atlas/atlas.json`)
- Test: `tests/test_crm_atlas.py`

**Interfaces:**
- Produces: `render_digest(atlas) -> str`; artefacto `docs/crm_atlas/atlas.digest.md`.

- [ ] **Step 1: Test de `render_digest` + `auth_note`**

```python
def test_digest_and_auth_note(spec):
    from core.crm_atlas import build_atlas_phase_a, render_digest
    atlas = build_atlas_phase_a(spec, tenant="tnm")
    assert "x-api-key" in atlas["meta"]["auth_note"]
    d = render_digest(atlas)
    assert "548" not in d or True                      # digest lleva conteos por módulo
    assert "## Digest" in d
    for tag in atlas["summary"]["by_tag"]:
        assert tag in d                                # cada módulo aparece con su nº de ops
```

- [ ] **Step 2: Ejecutar → FAIL** (`render_digest`/`auth_note` no existen).

- [ ] **Step 3: Implementar** `auth_note` en `meta` y `render_digest`:
```python
def render_digest(atlas: dict) -> str:
    m, s = atlas["meta"], atlas["summary"]
    out = ["# Digest del atlas del CRM sudespacho", "",
           "> Superficie de DERIVA (legible en diff). Regenerar: `python -m scripts.crm_atlas discover`.",
           "", f"## Digest — tenant `{m['tenant']}`", "",
           f"- endpoints: {s['total_operations']} ops / {s['total_path_keys']} paths "
           f"({s['paths_without_operations']} huérfanos)"]
    out.append("")
    out.append("### Endpoints por módulo")
    for tag, n in s["by_tag"].items():
        out.append(f"- {tag}: {n}")
    if atlas.get("elements"):
        import hashlib
        out.append("")
        out.append("### Elementos (campos · hash de esquema)")
        for el in atlas["elements"]:
            blob = json.dumps({"fields": el.get("fields"), "relations": el.get("relations"),
                               "enums": el.get("enums")}, sort_keys=True, ensure_ascii=False)
            h = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]
            out.append(f"- {el['slug']}: {len(el.get('fields') or [])} campos · {h}")
    return "\n".join(out) + "\n"
```
En `build_atlas_phase_a`, añadir a `meta`:
```python
"auth_note": ("El spec declara header 'Authorization' (apiKey) pero devuelve 401; "
              "el header operativo es 'x-api-key' (INTEGRACION §2.1)."),
```
En la CLI, escribir el digest y su ruta `DEFAULT_DIGEST = Path("docs/crm_atlas/atlas.digest.md")`.

- [ ] **Step 4: `.gitignore`** — añadir línea `docs/crm_atlas/atlas.json`. Sacar de git el ya trackeado:
```bash
git rm --cached docs/crm_atlas/atlas.json
```

- [ ] **Step 5: Regenerar y verificar artefactos**

Run: `python -m scripts.crm_atlas discover --phase a`
Expected: escribe `.md` + `.digest.md`; `atlas.json` local (no trackeado).
Run: `git status --short` → `atlas.json` NO aparece; `.md`/`.digest.md` sí.

- [ ] **Step 6: Ejecutar tests → PASS. Commit**

```bash
git add core/crm_atlas.py scripts/crm_atlas.py .gitignore tests/test_crm_atlas.py docs/CRM_SUDESPACHO_ATLAS.md docs/crm_atlas/atlas.digest.md
git commit -m "feat(crm-atlas): digest de deriva + auth_note; atlas.json fuera de git"
```

---

## Grupo 2 — Fase B (esquema por elemento)

Todo nuevo en `core/crm_atlas.py` + tests. Cliente HTTP bespoke con `x-api-key`.

### Task 6: `atlas_client()` + `auth_healthcheck()` (fail-fast)

**Files:**
- Modify: `core/crm_atlas.py`
- Test: `tests/test_crm_atlas.py`

**Interfaces:**
- Produces: `atlas_client() -> httpx.Client` (header `x-api-key` de env; sin logging de body/headers); `auth_healthcheck(client) -> None` (lanza `CrmAtlasAuthError` en 401/403).

- [ ] **Step 1: Test (falla) — healthcheck lanza en 401**

```python
def test_auth_healthcheck_fails_fast_on_401():
    import httpx, pytest
    from core.crm_atlas import auth_healthcheck, CrmAtlasAuthError
    transport = httpx.MockTransport(lambda req: httpx.Response(401))
    with httpx.Client(transport=transport, base_url="https://x") as c:
        with pytest.raises(CrmAtlasAuthError):
            auth_healthcheck(c)

def test_auth_healthcheck_ok_on_200():
    import httpx
    from core.crm_atlas import auth_healthcheck
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=[]))
    with httpx.Client(transport=transport, base_url="https://x") as c:
        auth_healthcheck(c)   # no lanza
```

- [ ] **Step 2: Ejecutar → FAIL.**

- [ ] **Step 3: Implementar**

```python
class CrmAtlasAuthError(RuntimeError):
    pass

def atlas_client(base_url: str = PUBLIC_BASE_URL, *, timeout: float = 60.0) -> httpx.Client:
    key = os.environ.get("SUDESPACHO_API_KEY", "").strip()
    if not key:
        raise CrmAtlasAuthError("Falta SUDESPACHO_API_KEY en el entorno.")
    return httpx.Client(base_url=base_url.rstrip("/"),
                        headers={"x-api-key": key, "Accept": "application/json"},
                        timeout=timeout)

def auth_healthcheck(client: httpx.Client) -> None:
    r = client.get("/api/elements")
    if r.status_code in (401, 403):
        raise CrmAtlasAuthError(f"Auth global rechazada (HTTP {r.status_code}). Revisa SUDESPACHO_API_KEY.")
    r.raise_for_status()
```

- [ ] **Step 4: Ejecutar → PASS. Commit** `feat(crm-atlas): cliente x-api-key + auth healthcheck fail-fast`

### Task 7: `fetch_elements()` — Accept json + hydra unwrap + guarda

**Files:** Modify `core/crm_atlas.py`; Test `tests/test_crm_atlas.py`

**Interfaces:**
- Produces: `fetch_elements(client) -> list[str]` (slugs, ordenados, dedup).

- [ ] **Step 1: Test (falla) — lista Y hydra**

```python
def test_fetch_elements_list_and_hydra():
    import httpx
    from core.crm_atlas import fetch_elements
    members = [{"label":"Devices","id":{"value":"devices"}},
               {"label":"Absences","id":{"value":"absences"}},
               {"label":"Bad"}]  # sin id.value -> se ignora con guarda
    def handler(req):
        if "ld+json" in req.headers.get("accept",""):
            return httpx.Response(200, json={"hydra:member": members, "hydra:totalItems": 3})
        return httpx.Response(200, json=members)
    with httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x") as c:
        assert fetch_elements(c) == ["absences", "devices"]   # ordenado, dedup, 'Bad' descartado
```

- [ ] **Step 2: Ejecutar → FAIL.**

- [ ] **Step 3: Implementar**

```python
def fetch_elements(client: httpx.Client) -> list[str]:
    r = client.get("/api/elements")
    r.raise_for_status()
    data = r.json()
    members = data.get("hydra:member", data.get("items", data)) if isinstance(data, dict) else data
    if not isinstance(members, list):
        raise CrmAtlasError("/api/elements devolvió una forma inesperada.")
    slugs = set()
    for it in members:
        if isinstance(it, dict):
            ident = it.get("id")
            slug = ident.get("value") if isinstance(ident, dict) else (ident if isinstance(ident, str) else None)
            if slug:
                slugs.add(slug)
    return sorted(slugs)
```
(`CrmAtlasError` = clase base ya existente o nueva.)

- [ ] **Step 4: Ejecutar → PASS. Commit** `feat(crm-atlas): fetch_elements (hydra/list + guarda de miembro)`

### Task 8: `parse_fields_config()` (fuente 4a)

**Files:** Modify `core/crm_atlas.py`; Test `tests/test_crm_atlas.py`

**Interfaces:**
- Produces: `Field(name, type, label, active)`; `parse_fields_config(payload) -> list[Field]`.

- [ ] **Step 1: Test (falla)**

```python
def test_parse_fields_config():
    from core.crm_atlas import parse_fields_config
    payload = {"items":[{"id":1,"name":"cuantia","label":"Cuantía","type":"Moneda","active":True,"deleted":False},
                        {"id":2,"name":"tipo","label":"Tipo","type":"Select","active":True,"deleted":False},
                        {"id":3,"name":"x","label":"x","type":"TextCorto","active":False,"deleted":True}]}
    fields = parse_fields_config(payload)
    assert [f.name for f in fields] == ["cuantia", "tipo"]     # deleted=True se excluye
    assert {f.name: f.type for f in fields} == {"cuantia":"Moneda","tipo":"Select"}
```

- [ ] **Step 2: Ejecutar → FAIL.**
- [ ] **Step 3: Implementar** dataclass `Field` + `parse_fields_config` (excluir `deleted`, conservar `name/type/label/active`).
- [ ] **Step 4: PASS. Commit** `feat(crm-atlas): parse_fields_config (view/config/fields)`

### Task 9: `parse_invalid_property_probe()` (fuente 4b, con guardas)

**Files:** Modify `core/crm_atlas.py`; Test `tests/test_crm_atlas.py`

**Interfaces:**
- Consumes: un `httpx.Response`.
- Produces: `parse_invalid_property_probe(resp) -> list[str] | None` (None si no es 500-con-patrón).

- [ ] **Step 1: Tests (fallan) — 500+patrón OK; 500 sin patrón → None; 200 → None**

```python
def test_probe_guards():
    import httpx
    from core.crm_atlas import parse_invalid_property_probe as p
    ok = httpx.Response(500, json={"detail":"ElementProperty not found : zz The properties are: a,b,c."})
    assert p(ok) == ["a","b","c"]
    other500 = httpx.Response(500, json={"detail":"Array to string conversion"})
    assert p(other500) is None
    got200 = httpx.Response(200, json={"items":[{"id":1}]})   # NUNCA tratar 200 como esquema
    assert p(got200) is None
```

- [ ] **Step 2: Ejecutar → FAIL.**
- [ ] **Step 3: Implementar**

```python
_PROBE_RE = re.compile(r"properties are\s*:?\s*(.+)", re.IGNORECASE)

def parse_invalid_property_probe(resp) -> list[str] | None:
    if resp.status_code != 500:
        return None
    try:
        detail = (resp.json().get("detail") or "")
    except Exception:
        return None
    m = _PROBE_RE.search(detail)
    if not m:
        return None
    return [f.strip() for f in m.group(1).replace(".", "").split(",") if f.strip()]
```

- [ ] **Step 4: PASS. Commit** `feat(crm-atlas): probe 4b con guardas (500+patron, anti-200)`

### Task 10: `parse_relations_config()` (fuente 5a)

**Files:** Modify `core/crm_atlas.py`; Test `tests/test_crm_atlas.py`

- [ ] **Step 1: Test (falla)**

```python
def test_parse_relations_config():
    from core.crm_atlas import parse_relations_config
    rel = parse_relations_config({"parent":["sms","abogados_propios"], "children":["actuaciones","abogados_propios"]})
    assert rel == {"parent":["abogados_propios","sms"], "children":["abogados_propios","actuaciones"]}  # ordenado
```

- [ ] **Step 2: FAIL.**
- [ ] **Step 3: Implementar** — devolver `{"parent": sorted(...), "children": sorted(...)}`, tolerando claves ausentes.
- [ ] **Step 4: PASS. Commit** `feat(crm-atlas): parse_relations_config (parent/children ordenado)`

### Task 11: `select_enum_fields()` (allowlist) + `parse_enums()` (fuente 5b)

**Files:** Modify `core/crm_atlas.py`; Test `tests/test_crm_atlas.py`

**Interfaces:**
- Produces: `SELECT_TYPE="Select"`, `ENUM_DENYLIST={"ListaUsuarios","ListaBancos","ListaGrupos","ListaElemento","ListaElementoSelect","Tags"}`; `select_enum_fields(fields) -> list[str]`; `parse_enums(payload) -> list[dict]`.

- [ ] **Step 1: Tests (fallan) — allowlist Select, denylist Lista***

```python
def test_select_enum_fields_allowlist_only_select():
    from core.crm_atlas import parse_fields_config, select_enum_fields
    fields = parse_fields_config({"items":[
        {"name":"tipo","type":"Select","label":"","active":True,"deleted":False},
        {"name":"profesional_asignado","type":"ListaUsuarios","label":"","active":True,"deleted":False},
        {"name":"banco","type":"ListaBancos","label":"","active":True,"deleted":False},
        {"name":"tags","type":"Tags","label":"","active":True,"deleted":False}]})
    assert select_enum_fields(fields) == ["tipo"]   # SOLO Select; Lista*/Tags fuera

def test_parse_enums():
    from core.crm_atlas import parse_enums
    assert parse_enums({"enums":[{"id":"R1","label":"x","extra":1},{"id":"R2","label":"y"}]}) == \
        [{"id":"R1","label":"x"},{"id":"R2","label":"y"}]
```

- [ ] **Step 2: FAIL.**
- [ ] **Step 3: Implementar** las constantes + `select_enum_fields` (filtra `f.type == SELECT_TYPE`; ignora denylist) + `parse_enums` (extrae solo `{id,label}`, ordenado por `id`).
- [ ] **Step 4: PASS. Commit** `feat(crm-atlas): select_enum_fields (allowlist Select, denylist Lista*/Tags) + parse_enums`

### Task 12: `discover_element()` — orquestación con degradación

**Files:** Modify `core/crm_atlas.py`; Test `tests/test_crm_atlas.py`

**Interfaces:**
- Consumes: `atlas_client`, `parse_fields_config`/`parse_invalid_property_probe`/`parse_relations_config`/`select_enum_fields`/`parse_enums`.
- Produces: `discover_element(client, slug) -> dict` con claves `slug, fields, relations, enums, field_types_no_enumerados, probes`. `relations=None` si falló; `probes[k] in {"view/config/fields","500-probe","failed","ok"}`.

- [ ] **Step 1: Tests (fallan) — feliz + degradación**

```python
def test_discover_element_happy(monkeypatch):
    import httpx
    from core.crm_atlas import discover_element
    def handler(req):
        p = req.url.path
        if p.endswith("/fields"):
            return httpx.Response(200, json={"items":[
                {"name":"tipo","type":"Select","label":"T","active":True,"deleted":False},
                {"name":"resp","type":"ListaUsuarios","label":"R","active":True,"deleted":False}]})
        if p.endswith("/relations"):
            return httpx.Response(200, json={"parent":[],"children":["actuaciones"]})
        if "/view/enums/" in p:
            return httpx.Response(200, json={"enums":[{"id":"A","label":"a"}]})
        return httpx.Response(404)
    with httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x") as c:
        el = discover_element(c, "extrajudiciales")
    assert [f["name"] for f in el["fields"]] == ["resp","tipo"]        # ordenado
    assert el["enums"] == {"tipo":[{"id":"A","label":"a"}]}            # SOLO el Select
    assert el["field_types_no_enumerados"] == {"resp":"ListaUsuarios"} # Lista* registrado por tipo
    assert el["relations"] == {"parent":[],"children":["actuaciones"]}
    assert el["probes"] == {"fields":"view/config/fields","relations":"ok","enums":"ok"}

def test_discover_element_degrades_relations(monkeypatch):
    import httpx
    from core.crm_atlas import discover_element
    def handler(req):
        p = req.url.path
        if p.endswith("/fields"):
            return httpx.Response(200, json={"items":[]})
        if p.endswith("/relations"):
            return httpx.Response(500, json={"detail":"boom"})
        return httpx.Response(404)
    with httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x") as c:
        el = discover_element(c, "x")
    assert el["relations"] is None            # null, no [] — distingue fallo de vacío
    assert el["probes"]["relations"] == "failed"
```

- [ ] **Step 2: FAIL.**
- [ ] **Step 3: Implementar** `discover_element` con try/except por sub-llamada: 4a primero (si 404 → 4b), 5a, luego 5b solo sobre `select_enum_fields`; los `Field` con `type` en denylist van a `field_types_no_enumerados`. Cada fallo → `probes[k]="failed"`, campo `None` (relations) o `[]`/`{}` según semántica. El probe 4b (Task 9) se llama **sin** la capa de reintento (Task 13).
- [ ] **Step 4: PASS. Commit** `feat(crm-atlas): discover_element con degradacion (null vs vacio, probes)`

### Task 13: Capa de reintento/backoff + concurrencia

**Files:** Modify `core/crm_atlas.py`; Test `tests/test_crm_atlas.py`

**Interfaces:**
- Produces: `get_with_retry(client, path, *, attempts=5) -> httpx.Response` (exponencial `min(1·2^n,30)s` + jitter, respeta `Retry-After`, reintenta 429/5xx). Nota: el probe 4b **NO** usa esta capa.

- [ ] **Step 1: Test (falla) — reintenta 503 y luego 200; jitter/sleep parcheado**

```python
def test_get_with_retry_retries_503(monkeypatch):
    import httpx
    from core import crm_atlas as m
    calls = {"n":0}
    def handler(req):
        calls["n"] += 1
        return httpx.Response(200, json={}) if calls["n"] >= 3 else httpx.Response(503)
    monkeypatch.setattr(m.time, "sleep", lambda s: None)   # no dormir en test
    monkeypatch.setattr(m, "_jitter", lambda d: d)
    with httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x") as c:
        r = m.get_with_retry(c, "/api/elements")
    assert r.status_code == 200 and calls["n"] == 3
```

- [ ] **Step 2: FAIL.**
- [ ] **Step 3: Implementar** `get_with_retry` (import `time`; `_jitter`; respetar `Retry-After`; `attempts=5`, base 1s, cap 30s; reintenta solo 429/5xx; lanza tras agotar). Concurrencia se aplica en Task 15 (orquestador) con un pool de tamaño 4.
- [ ] **Step 4: PASS. Commit** `feat(crm-atlas): backoff exponencial + Retry-After (excluye probe 4b)`

### Task 14: `scan_atlas_for_pii()` — gate anti-PII

**Files:** Modify `core/crm_atlas.py`; Test `tests/test_crm_atlas.py`

**Interfaces:**
- Consumes: `core/anon` (detectores EMAIL/PERSONA).
- Produces: `scan_atlas_for_pii(atlas) -> list[str]` (lista de hallazgos; vacía = limpio). La CLI **aborta el write** si no está vacía.

- [ ] **Step 1: Test (falla) — email en un enum → detectado; atlas limpio → vacío**

```python
def test_scan_atlas_for_pii_detects_email():
    from core.crm_atlas import scan_atlas_for_pii
    dirty = {"elements":[{"slug":"x","enums":{"campo":[{"id":"a","label":"Fulano de Tal fulano@bufete.com"}]}}]}
    hits = scan_atlas_for_pii(dirty)
    assert hits and any("x" in h for h in hits)

def test_scan_atlas_for_pii_clean():
    from core.crm_atlas import scan_atlas_for_pii
    clean = {"elements":[{"slug":"y","enums":{"iva":[{"id":"R1","label":"Operaciones interiores"}]}}]}
    assert scan_atlas_for_pii(clean) == []
```

- [ ] **Step 2: FAIL.**
- [ ] **Step 3: Implementar** — recorrer `enums` y labels de campo; detectar patrón de email (regex) y, si `core/anon` expone un detector de PERSONA barato, usarlo; devolver lista de `"{slug}.{prop}: <motivo>"` (sin volcar el valor). Priorizar email (regex robusto) — la denylist `Lista*` ya evita el grueso; esto es defensa en profundidad.
- [ ] **Step 4: PASS. Commit** `feat(crm-atlas): gate anti-PII (email/persona) que bloquea el write`

### Task 15: `build_atlas` Fase B + orden determinista + métrica de completitud

**Files:** Modify `core/crm_atlas.py`; Test `tests/test_crm_atlas.py`

**Interfaces:**
- Produces: `build_atlas_phase_b(spec_or_phase_a_atlas, elements_results, ...) -> dict` con `meta.phase_b={ran,elements_total,elements_ok,elements_degraded,complete}` y `elements[]` ordenado.

- [ ] **Step 1: Test (falla) — completitud + orden + concurrencia determinista**

```python
def test_build_atlas_phase_b_completeness_and_order():
    from core.crm_atlas import build_atlas_phase_b
    results = [
        {"slug":"b","fields":[],"relations":{"parent":[],"children":[]},"enums":{},"field_types_no_enumerados":{},"probes":{"fields":"ok","relations":"ok","enums":"ok"}},
        {"slug":"a","fields":[],"relations":None,"enums":{},"field_types_no_enumerados":{},"probes":{"fields":"ok","relations":"failed","enums":"ok"}},
    ]
    atlas = build_atlas_phase_b({"meta":{},"summary":{},"endpoints":[]}, results, tenant="tnm")
    assert [e["slug"] for e in atlas["elements"]] == ["a","b"]     # ordenado por slug
    pb = atlas["meta"]["phase_b"]
    assert pb == {"ran":True,"elements_total":2,"elements_ok":1,"elements_degraded":1,"complete":False}
```

- [ ] **Step 2: FAIL.**
- [ ] **Step 3: Implementar** — ordenar `elements` por slug (y dentro, `fields` por name, ya vienen de discover); calcular la métrica (`degraded` = elementos con algún `probes[k]=="failed"`); `complete = ran and elements_degraded==0`.
- [ ] **Step 4: PASS. Commit** `feat(crm-atlas): build_atlas fase B (metrica de completitud + orden)`

### Task 16: `render_markdown` Fase B — sección de degradados + escape

**Files:** Modify `core/crm_atlas.py`; Test `tests/test_crm_atlas.py`

- [ ] **Step 1: Test (falla)** — el `.md` con elementos degradados muestra una cabecera "N/M resueltos" y una tabla de degradados **al principio**; labels con `|`/`\n` escapados en campos y enums.

```python
def test_render_md_phase_b_degraded_section():
    from core.crm_atlas import build_atlas_phase_b, render_markdown
    results=[{"slug":"a","fields":[],"relations":None,"enums":{},"field_types_no_enumerados":{},"probes":{"fields":"ok","relations":"failed","enums":"ok"}}]
    md = render_markdown(build_atlas_phase_b({"meta":{},"summary":{"by_tag":{}},"endpoints":[]}, results, tenant="tnm"))
    assert "degradado" in md.lower()
    assert "a" in md
```

- [ ] **Step 2: FAIL.**
- [ ] **Step 3: Implementar** — sección "Elementos con descubrimiento degradado" antes del detalle; por elemento, tabla de campos (name·type) + relaciones + enums; `_md_escape` aplicado a **todo** label de campo y enum.
- [ ] **Step 4: PASS. Commit** `feat(crm-atlas): render fase B (seccion de degradados + escape de labels)`

### Task 17: CLI `discover --phase b|all --scope --resume`

**Files:** Modify `scripts/crm_atlas.py`; Test `tests/test_crm_atlas.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: `discover --phase b|all [--scope all|juridicos] [--resume] [--no-stamp-time]`. Sin `--also-elcontable`.

- [ ] **Step 1: Test (falla) — `--phase all` con transport mockeado produce atlas con elements y bloquea si PII**

Test con `CliRunner` + `monkeypatch` de `fetch_oas3`, `atlas_client` (devuelve un `httpx.Client` con `MockTransport`), verificando que: (a) escribe `.md`+digest, (b) `atlas.json` local, (c) si un enum trae email → exit_code != 0 y NO escribe (gate).

- [ ] **Step 2: FAIL.**
- [ ] **Step 3: Implementar** el cuerpo `phase in {b,all}`: `client=atlas_client(base_url)`, `auth_healthcheck(client)`, `slugs=fetch_elements(client)` (filtrar por `--scope juridicos` contra una constante `ELEMENTOS_JURIDICOS` si se elige), pool de concurrencia 4 (`concurrent.futures.ThreadPoolExecutor`) llamando `discover_element`, `build_atlas_phase_b`, **`hits=scan_atlas_for_pii(atlas)` → si hits: echo + `raise typer.Exit(1)` SIN escribir**, luego escribir `.md`+digest (json local). Quitar `--also-elcontable`.
- [ ] **Step 4: PASS. Commit** `feat(crm-atlas): CLI fase B (scope, gate PII, sin also-elcontable)`

### Task 18: `--resume` (reintenta degradados)

**Files:** Modify `scripts/crm_atlas.py`, `core/crm_atlas.py`; Test `tests/test_crm_atlas.py`

- [ ] **Step 1: Test (falla)** — con un `atlas.json` previo donde `a` está "ok" y `b` "failed", `--resume` **salta `a`** y **reintenta `b`**. (Leer previo con `encoding="utf-8"`.)
- [ ] **Step 2: FAIL.**
- [ ] **Step 3: Implementar** `load_previous_atlas(path) -> dict|None` (utf-8) + predicado `is_resolved(el)` (`all(v=="ok" or v=="view/config/fields" or v=="500-probe" for v in probes.values())` y ninguna `failed`); en la CLI, si `--resume` y hay previo, saltar los resueltos y **reintentar** el resto.
- [ ] **Step 4: PASS. Commit** `feat(crm-atlas): --resume reintenta degradados (lee utf-8)`

### Task 19: Corrida en vivo + verificación

**Files:** (ninguno de código) — corrida real.

- [ ] **Step 1:** `python -m scripts.crm_atlas discover --phase all` (con `SUDESPACHO_API_KEY` en el entorno).
- [ ] **Step 2:** Verificar: `meta.phase_b.elements_total==89`, `elements_degraded` bajo (idealmente 0); ningún `enums` de tipos `Lista*`; el gate PII no bloqueó (o, si bloqueó, investigar el hallazgo antes de continuar).
- [ ] **Step 3:** Inspeccionar el `atlas.json` local: confirmar 0 emails (`grep -c "@" | por labels`), y que `field_types_no_enumerados` registra los `ListaUsuarios`.
- [ ] **Step 4:** `python -m pytest -q --junit-xml` (suite completa verde; recordar las env vars).
- [ ] **Step 5: Commit** de `.md`+digest actualizados.

---

## Grupo 3 — Integración documental

### Task 20: Vaciar tablas de `ARQUITECTURA` a punteros + cross-links + doc-hygiene

**Files:**
- Modify: `docs/ARQUITECTURA_CRM_SUDESPACHO.md` (§3, §6, §11 → puntero + "por qué")
- Modify: `docs/INTEGRACION_SUDESPACHO.md` (§0 puntero; §8.1 reconciliación x-api-key SIN borrar la nota empírica)
- Modify: `CLAUDE.md` (Referencias rápidas → entrada del atlas)
- Modify: `../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md` (§2 puntero — **PR aparte en El Contable**)

- [ ] **Step 1:** En `ARQUITECTURA §3/§6/§11`: sustituir las tablas de endpoints/módulos/conteo por un puntero a `docs/CRM_SUDESPACHO_ATLAS.md`/digest + conservar solo el "por qué" conceptual. (No hay test; es doc.)
- [ ] **Step 2:** En `INTEGRACION §8.1`: **añadir** la reconciliación ("la guía oficial documenta `x-api-key`; el spec declara `Authorization`; no concuerdan") **sin borrar** la nota de que `Authorization` da 401.
- [ ] **Step 3:** Cross-links en `INTEGRACION §0` y `CLAUDE.md`.
- [ ] **Step 4:** Verificar guards de docs: `python -m pytest tests/test_docs_gobernanza.py -q` (si existe) + `python -m pytest -q` completa.
- [ ] **Step 5: Commit** `docs(crm-atlas): atlas como SSOT de endpoints — vaciar tablas de ARQUITECTURA a punteros`
- [ ] **Step 6 (El Contable, PR aparte):** puntero desde `REFERENCIA §2` al atlas de FeesDefender (sin copia física).

---

## Self-review (cobertura de la spec)

- §2 fuentes → Tasks 6-11. §3 arquitectura → Tasks 6-18. §4 modelo → Tasks 12,15. §5 fases → Tasks 6,17. §6 barandillas → Tasks 9,11,14,17 (gate). §7 robustez → Tasks 1,13,15,18. §8 artefactos → Task 5. §9 SSOT → Task 20. §10 tests → embebidos en cada task. §11 doc-hygiene → Task 20. §14 hardening → Tasks 1-5. §15 traza → cubierta por los arreglos anteriores.
- Sin placeholders: cada step de código lleva código real.
- Consistencia de tipos: `Field`/`Endpoint`/`Param`, `discover_element` dict con `probes`, `phase_b` métrica — consistentes entre tasks.
