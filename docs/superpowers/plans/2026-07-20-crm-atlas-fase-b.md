# Atlas del CRM sudespacho — Fase B + hardening Fase A · Plan v2

> **v2 — reescrito tras auditoría adversarial del plan (4 revisores, 2026-07-20).** Traza de correcciones en §APÉNDICE. Ejecución **EN LÍNEA** (el ejecutor sostiene contexto entre tareas), con checkpoints por grupo.

**Goal:** Completar el atlas del CRM: endurecer la Fase A commiteada y añadir la Fase B (esquema por elemento) con barrera anti-PII estanca, produciendo un mapa exhaustivo, determinista y seguro con una corrida `discover`.

**Architecture:** Lógica + cliente HTTP bespoke en `core/crm_atlas.py`; CLI Typer en `scripts/crm_atlas.py`. Fase A = OpenAPI público. Fase B = `x-api-key` (en `os.environ`) contra `/api/elements` + `view/config/{el}/fields|relations` + `view/enums/{el}/{prop}`. Solo lectura de esquema.

**Tech Stack:** Python 3.14 (venv), `httpx`, `typer`, `pytest`, `core/anon` (solo regex de EMAIL).

**Spec:** `docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md` (v2).

## Global Constraints

- **Solo esquema, nunca datos.** Prohibido `element_registries`/`element_register` para leer registros. El probe 4b (que provoca 500) es la única llamada "no-GET-limpia".
- **Sin escritura** (no POST/PUT/PATCH/DELETE).
- **Gate PII (decidido):** enums solo de `type=="Select"`; **denylist** `ListaUsuarios`/`ListaBancos`/`ListaGrupos`/`ListaElemento`/`ListaElementoSelect`/`Tags` (barrera primaria). `scan_atlas_for_pii` = **regex de EMAIL** (reusar `core/anon.anonimizar` L727) que **bloquea** el write + **cuarentena heurística**: todo valor de enum `Select` que parezca nombre de persona (2-4 tokens Title-Case, sin dígitos/códigos) NO se vuelca — va a `field_types_no_enumerados` para revisión. **NO usar `detectar_nombres_protegidos`** (semántica invertida: detecta operadores que NO deben anonimizarse). El cliente **nunca** logea headers/body; `warnings[]` solo `status`+`endpoint`.
- **Secretos por entorno:** `SUDESPACHO_API_KEY` de `os.environ`; nunca en árbol ni logs.
- **Encoding:** SIEMPRE `encoding="utf-8"`, `newline="\n"`, `ensure_ascii=False`; lectura del atlas previo (resume) con `encoding="utf-8"` explícito.
- **Determinismo:** `json.dumps(..., sort_keys=True, ensure_ascii=False, indent=2)` + ordenación explícita de TODA lista antes de serializar; el test canónico compara **`.md` y digest** (lo commiteado) bajo permutación de orden de llegada.
- **Entorno Windows + PowerShell:** conteo de tests por `--junit-xml` a ruta del scratchpad (NO `%TEMP%`: en la herramienta Bash usar `"$TMPDIR/j.xml"` o ruta absoluta; en PowerShell `$env:TEMP\j.xml`). Comandos desde la raíz del repo.
- **Tests de CLI:** parchear **`scripts.crm_atlas.fetch_oas3`** y **`scripts.crm_atlas.atlas_client`** (el binding importado en el módulo CLI, no `core.crm_atlas.*`); `monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)` como cinturón; nunca red real.
- **Auth header operativo:** `x-api-key` (el spec declara `Authorization` pero da 401).
- **Git:** rama + PR; pytest local antes de mergear. **Un PR por grupo** (§14).

---

## Grupo 0 — Andamiaje transversal (mata los bugs de "símbolo indefinido entre tasks")

Todo en `core/crm_atlas.py`. Front-loaded para que el resto compile.

### Task 0.1: Imports de módulo + excepciones

**Files:** Modify `core/crm_atlas.py` (cabecera); Test `tests/test_crm_atlas.py`

- [ ] **Step 1:** Añadir a los imports de módulo: `import json`, `import os`, `import time`, `import random`, `import concurrent.futures`. (Ya están `re`, `dataclasses`, `typing`, `httpx`.)
- [ ] **Step 2:** Definir la jerarquía de excepciones **antes** de todo:
```python
class CrmAtlasError(RuntimeError):
    pass

class CrmAtlasAuthError(CrmAtlasError):
    pass
```
- [ ] **Step 3: Test**
```python
def test_exception_hierarchy():
    from core.crm_atlas import CrmAtlasError, CrmAtlasAuthError
    assert issubclass(CrmAtlasAuthError, CrmAtlasError)
    import core.crm_atlas as m
    assert all(hasattr(m, n) for n in ("json","os","time","random"))
```
- [ ] **Step 4:** Run `python -m pytest tests/test_crm_atlas.py::test_exception_hierarchy -v` → PASS.
- [ ] **Step 5: Commit** `feat(crm-atlas): andamiaje — imports + jerarquia CrmAtlasError/CrmAtlasAuthError`

### Task 0.2: Migrar `meta` a esquema anidado + `generator_version=2`

**Files:** Modify `core/crm_atlas.py` (`build_atlas_phase_a`); Test `tests/test_crm_atlas.py`

**Interfaces (Produces):** `meta.phase_a = {"complete": True}`, `meta.phase_b = {"ran": False, "complete": False}`, `meta.generator_version = 2`, `meta.auth_note` (x-api-key). Se retiran los bools planos `phase_a_complete`/`phase_b_complete`.

- [ ] **Step 1: Test (falla)**
```python
def test_meta_nested_schema(spec):
    from core.crm_atlas import build_atlas_phase_a
    m = build_atlas_phase_a(spec, tenant="tnm")["meta"]
    assert m["generator_version"] == 2
    assert m["phase_a"] == {"complete": True}
    assert m["phase_b"]["complete"] is False and m["phase_b"]["ran"] is False
    assert "x-api-key" in m["auth_note"]
    assert "phase_a_complete" not in m and "phase_b_complete" not in m
```
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** En `build_atlas_phase_a`: `generator_version=2`; sustituir los bools por `"phase_a":{"complete":True}`, `"phase_b":{"ran":False,"complete":False}`; añadir `"auth_note": ("El spec declara header 'Authorization' (apiKey) pero devuelve 401; el header operativo es 'x-api-key' (INTEGRACION §2.1).")`.
- [ ] **Step 4:** PASS.
- [ ] **Step 5: Commit** `refactor(crm-atlas): meta anidado (phase_a/phase_b) + generator_version 2 + auth_note`

### Task 0.3: `render_markdown` defensivo (tolera atlas de Fase A y de Fase B)

**Files:** Modify `core/crm_atlas.py` (`render_markdown`); Test `tests/test_crm_atlas.py`

**Interfaces (Produces):** `render_markdown(atlas)` no lanza `KeyError` ante `meta`/`summary` parciales; lee `meta["phase_b"]["complete"]`; renderiza `elements` si existen.

- [ ] **Step 1: Test (falla) — atlas mínimo de Fase B no debe petar**
```python
def test_render_markdown_tolerates_minimal_phase_b():
    from core.crm_atlas import render_markdown
    md = render_markdown({"meta":{"tenant":"tnm","phase_b":{"complete":False}},
                          "summary":{"by_tag":{}}, "endpoints":[], "elements":[]})
    assert "# Atlas del CRM" in md   # no KeyError
```
- [ ] **Step 2:** FAIL (`KeyError: 'sources'`).
- [ ] **Step 3:** Reescribir accesos con `.get(...)`: `meta.get("sources",{}).get("oas3",{})`, `summ.get("total_operations","?")`, `summ.get("by_method",{})`, etc. El header de fase lee `meta.get("phase_b",{}).get("complete")` → "✅"/"⏳ pendiente". Actualizar el test existente `test_render_markdown_has_tables_and_index` si dependía de `phase_b_complete`.
- [ ] **Step 4:** PASS + módulo completo verde.
- [ ] **Step 5: Commit** `refactor(crm-atlas): render_markdown defensivo (Fase A y B)`

---

## Grupo 1 — Hardening de la Fase A

### Task 1.1: Determinismo (`sort_keys`) + `generated_at` UTC/no-stamp por defecto

**Files:** Modify `scripts/crm_atlas.py`; Test `tests/test_crm_atlas.py`

- [ ] **Step 1: Test** — `test_atlas_json_is_byte_stable` (dos builds mismos datos → `json.dumps(sort_keys=True)` idéntico).
- [ ] **Step 2:** PASS (build ya determinista con `generated_at=None`).
- [ ] **Step 3:** CLI: escribir con `json.dumps(atlas, ensure_ascii=False, indent=2, sort_keys=True)`; default `stamp_time: bool = typer.Option(False, ...)`; cuando se selle usar `now_iso_utc()` (ya existe en `core/utils.py:76`); **cambiar el import** de `scripts/crm_atlas.py` a `from core.utils import now_iso_utc`.
- [ ] **Step 4: Test CLI** (monkeypatch **`scripts.crm_atlas.fetch_oas3`**, `_MINI_SPEC` de módulo — ver Task 1.6) → `atlas.json.meta.generated_at is None`.
- [ ] **Step 5:** Módulo verde. **Commit** `fix(crm-atlas): determinismo sort_keys + generated_at no-stamp/UTC`

### Task 1.2: `_request_schema` — merge-patch, multipart, allOf/oneOf

**Files:** Modify `core/crm_atlas.py:143-164`; Test `tests/test_crm_atlas.py`

- [ ] **Step 1: Tests (fallan)** — merge-patch (`$ref`→basename), multipart (`type:object`→"object"), **allOf** (`{"allOf":[{"$ref":".../Base"},...]}`→"Base").
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Ampliar la tupla de content-types a `("application/json","application/ld+json","application/merge-patch+json","multipart/form-data")`; antes del `$ref` directo, manejar `allOf/oneOf/anyOf` (tomar el primer `$ref`). Preservar la rama array/tipo existente.
- [ ] **Step 4:** PASS (incl. `test_request_schema_ref_basename`). **Commit** `fix(crm-atlas): _request_schema cubre merge-patch/multipart/allOf`

### Task 1.3: `operation_id_to_dev_slug` — colapsar no-alfanuméricos + trailing slash

**Files:** Modify `core/crm_atlas.py:77-89`, `parse_oas3`; Test `tests/test_crm_atlas.py`

- [ ] **Step 1: Test** — `getAccounting - ConfigurationItem`→`get-accounting-configuration-item`; `createPublic Holidays (Multiple)Collection`→`create-public-holidays-multiple-collection`.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Tras construir el slug: `s = re.sub(r"[^0-9a-zA-Z]+","-", s.lower()).strip("-")` (usa el `re` ya importado). En `parse_oas3`, `dev_doc_url = f"{DEV_PORTAL_BASE}/{slug}/"` (trailing `/`).
- [ ] **Step 4:** **Actualizar `test_parse_endpoint_fields`** (`tests/test_crm_atlas.py:136`): esperar `.endswith("/get-absences-absences-collection/")` (con barra). Verificar con el **módulo completo**: `python -m pytest tests/test_crm_atlas.py -q --junit-xml=...`.
- [ ] **Step 5:** PASS. **Commit** `fix(crm-atlas): slug del portal colapsa no-alfanum + trailing slash`

### Task 1.4: `Endpoint.deprecated` + `Param.enum/default` (defaults al final)

**Files:** Modify `core/crm_atlas.py` (`Param`,`Endpoint`,`_parse_param`,`parse_oas3`); Test

- [ ] **Step 1: Test** — `deprecated` True; `Param.enum==["a","b"]`, `Param.default=="a"`.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Añadir a `Param`: `enum: list | None = None`, `default: Any = None` (**al final, con default**, para no romper el orden de dataclass). A `Endpoint`: `deprecated: bool = False` (al final). Poblar en `_parse_param` (`schema.get("enum")`, `schema.get("default")`) y `parse_oas3` (`bool(op.get("deprecated",False))`). Verificar que el fallback `Param(name="",...)` de la línea ~115 sigue válido (los nuevos campos tienen default).
- [ ] **Step 4:** PASS. **Commit** `feat(crm-atlas): capturar deprecated + enum/default de parametros`

### Task 1.5: `render_digest` + gitignore `atlas.json`

**Files:** Modify `core/crm_atlas.py` (`render_digest`), `scripts/crm_atlas.py`, `.gitignore`; Test

- [ ] **Step 1: Test** — `render_digest(atlas)` contiene `f"- {tag}: {n}"` por módulo (assert real, NO tautología); sobre atlas con `elements`, una línea por elemento con `len(fields)` y hash.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Implementar `render_digest` (usa `json.dumps`+`hashlib` — `json` ya importado en Task 0.1). CLI escribe `docs/crm_atlas/atlas.digest.md`.
- [ ] **Step 4:** `.gitignore` += `docs/crm_atlas/atlas.json`; `git rm --cached docs/crm_atlas/atlas.json`.
- [ ] **Step 5:** Regenerar `discover --phase a`; `git status` → `atlas.json` no trackeado; `.md`/digest sí.
- [ ] **Step 6:** PASS. **Commit** `feat(crm-atlas): digest de deriva; atlas.json fuera de git`

### Task 1.6: Fixture `_MINI_SPEC` de módulo (habilita tests de CLI)

**Files:** Modify `tests/test_crm_atlas.py`

- [ ] **Step 1:** Extraer el dict del fixture `spec` a una constante de módulo `_MINI_SPEC = {...}` y reescribir el fixture `def spec(): return copy.deepcopy(_MINI_SPEC)`. Así los `lambda` de CLI pueden devolver `_MINI_SPEC`.
- [ ] **Step 2:** Módulo verde. **Commit** `test(crm-atlas): _MINI_SPEC de modulo para tests de CLI`

---

## Grupo 2 — Fase B

### Task 2.1: `get_with_retry` (capa de reintento) — ANTES de discover_element

**Files:** Modify `core/crm_atlas.py`; Test

**Interfaces (Produces):** `get_with_retry(client, path, *, attempts=5) -> httpx.Response` (exponencial `min(1·2^n,30)s`, jitter `_jitter`, respeta `Retry-After`, reintenta solo 429/5xx). El probe 4b **NO** la usa.

- [ ] **Step 1: Tests** — (a) 503,503,200 → 3 llamadas, `sleep` y `_jitter` monkeypatcheados; (b) 4xx no-429 → NO reintenta; (c) agota → lanza.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Implementar (`time`/`random` de Task 0.1). `_jitter(d)=d*(1+random.uniform(-0.2,0.2))`.
- [ ] **Step 4:** PASS. **Commit** `feat(crm-atlas): get_with_retry (backoff + Retry-After)`

### Task 2.2: `atlas_client` + `auth_healthcheck`

**Files:** Modify `core/crm_atlas.py`; Test

- [ ] **Step 1: Tests** — healthcheck lanza `CrmAtlasAuthError` en 401; no lanza en 200. (`atlas_client` lee `os.environ`; test de que sin key lanza `CrmAtlasAuthError`, con `monkeypatch.delenv`.)
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** `atlas_client(base_url=PUBLIC_BASE_URL)` → `httpx.Client` con `{"x-api-key":key,"Accept":"application/json"}`; sin key → `CrmAtlasAuthError`. `auth_healthcheck(client)` → `GET /api/elements`; 401/403 → `CrmAtlasAuthError`; else `raise_for_status`.
- [ ] **Step 4:** PASS. **Commit** `feat(crm-atlas): atlas_client + auth_healthcheck fail-fast`

### Task 2.3: `fetch_elements` (Accept json + hydra unwrap + guarda)

**Files:** Modify `core/crm_atlas.py`; Test

- [ ] **Step 1: Test** — lista Y hydra (`hydra:member`); miembro sin `id.value` ignorado; salida ordenada+dedup (`["absences","devices"]`).
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Implementar (desenvuelve `data.get("hydra:member", data.get("items", data))`; extrae `it["id"]["value"]`; `CrmAtlasError` si forma inesperada). Usa `get_with_retry`.
- [ ] **Step 4:** PASS. **Commit** `feat(crm-atlas): fetch_elements (hydra/list + guarda)`

### Task 2.4: `parse_fields_config` (4a) — con `source`

**Files:** Modify `core/crm_atlas.py` (`Field`, parser); Test

- [ ] **Step 1: Test** — entrada **desordenada** `[tipo, cuantia]` → salida ordenada por name `["cuantia","tipo"]`; `deleted=True` excluido; `type` conservado; `source="view/config/fields"`.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** `Field(name,type,label,active,source)`; `parse_fields_config` excluye `deleted`, **ordena por name**.
- [ ] **Step 4:** PASS. **Commit** `feat(crm-atlas): parse_fields_config (con source, ordenado)`

### Task 2.5: `parse_invalid_property_probe` (4b, guardado)

**Files:** Modify `core/crm_atlas.py`; Test

- [ ] **Step 1: Test** — 500+patrón→`["a","b","c"]`; 500 sin patrón→**`None`**; **200→`None`** (anti-lectura de registros). (Se fija `None`, coherente con "null=falló"; se reconcilia spec §2 a `None` — ver Task 3.2 doc.)
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Implementar (exige `status==500` + regex `properties are:`); recibe el `Response` (llamado con `client.get`, NO `get_with_retry`).
- [ ] **Step 4:** PASS. **Commit** `feat(crm-atlas): probe 4b guardado (500+patron, anti-200)`

### Task 2.6: `parse_relations_config` (5a)

**Files:** Modify `core/crm_atlas.py`; Test

- [ ] **Step 1: Test** — entrada desordenada → `{"parent":sorted,"children":sorted}`; claves ausentes toleradas.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS. **Commit** `feat(crm-atlas): parse_relations_config`

### Task 2.7: `select_enum_fields` (allowlist) + `parse_enums` (5b)

**Files:** Modify `core/crm_atlas.py`; Test

**Interfaces:** `SELECT_TYPE="Select"`; `ENUM_DENYLIST={"ListaUsuarios","ListaBancos","ListaGrupos","ListaElemento","ListaElementoSelect","Tags"}`.

- [ ] **Step 1: Tests** — `select_enum_fields` con `[Select, ListaUsuarios, ListaBancos, Tags]` → `["<solo el Select>"]`; `parse_enums` entrada `[R2,R1]` → ordenado `[{R1},{R2}]`, solo `{id,label}`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar (allowlist `f.type==SELECT_TYPE`). **Step 4:** PASS. **Commit** `feat(crm-atlas): select_enum_fields (allowlist Select) + parse_enums`

### Task 2.8: `discover_element` (orquestación + degradación + cableado a get_with_retry)

**Files:** Modify `core/crm_atlas.py`; Test

**Interfaces (Produces):** dict `{slug, fields, relations, enums, field_types_no_enumerados, probes}`. `relations=None` si falló; `probes[k]∈{"view/config/fields","500-probe","ok","failed"}`; **`probes["enums"]="ok"` aunque no haya campos Select** (evita bucle de resume); `field_types_no_enumerados` = **todo campo con `type != "Select"`** (por tipo, sin valores). 4a/5a/5b vía `get_with_retry`; 4b vía `client.get`.

- [ ] **Step 1: Tests** — (a) feliz: `enums` solo del Select, `field_types_no_enumerados` con el `ListaUsuarios`, orden correcto, `probes` todo "ok"; (b) relations 500 → `relations=None`, `probes["relations"]="failed"`; (c) elemento sin campos Select → `probes["enums"]=="ok"`; (d) las sub-llamadas no-probe pasan por `get_with_retry` (monkeypatch de `get_with_retry` a un contador).
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS. **Commit** `feat(crm-atlas): discover_element (degradacion, get_with_retry, probes)`

### Task 2.9: `scan_atlas_for_pii` — email + cuarentena heurística

**Files:** Modify `core/crm_atlas.py`; Test

**Interfaces (Produces):** `scan_atlas_for_pii(atlas) -> list[str]` (hits `"{slug}.{prop}: <motivo>"`, sin volcar el valor). Escanea `enums` **y** `warnings`. Motivos: EMAIL (regex de `core/anon`) → hit; valor `Select` que parece nombre-persona (`_parece_persona`) → hit + el llamador lo mueve a cuarentena. La CLI **bloquea el write** si hay hits de email; los de "parece persona" disparan la cuarentena (mover ese enum a `field_types_no_enumerados`) y se re-escanea.

- [ ] **Step 1: Tests** — (a) label con email → hit; (b) label `"María González Ruiz"` (nombre SIN email) → hit por heurística; (c) `"Operaciones interiores"` / `"R1"` → limpio; (d) email en `warnings` → hit.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Implementar: reusar el patrón EMAIL de `core.anon.anonimizar.PATRONES_REGEX_COMPILADOS`; `_parece_persona(s)` = 2-4 tokens, todos Title-Case, sin dígitos ni caracteres de código, no en una allowlist de palabras de taxonomía. Recorrer `elements[*].enums` y `warnings`.
- [ ] **Step 4:** PASS. **Commit** `feat(crm-atlas): gate anti-PII (email regex + cuarentena heuristica de persona)`

### Task 2.10: `build_atlas_phase_b` — meta/summary completos + orden + circuit-breaker

**Files:** Modify `core/crm_atlas.py`; Test

**Interfaces (Produces):** `build_atlas_phase_b(phase_a_atlas: dict, elements_results: list[dict], *, tenant) -> dict` (primer arg = atlas de Fase A, del que **hereda `meta.sources`/`summary`/`endpoints`**). `meta.phase_b={ran,elements_total,elements_ok,elements_degraded,complete}`, `complete = ran and elements_degraded==0`. `elements` ordenado por slug.

- [ ] **Step 1: Tests** — (a) métrica + orden por slug (entrada desordenada); (b) **determinismo bajo permutación** sobre `render_markdown`+`render_digest` (no solo el json); (c) circuit-breaker: si `elements_degraded > total//2` → `meta.phase_b["circuit_broken"]=True` (la CLI aborta el write, Task 3.1).
- [ ] **Step 2:** FAIL. **Step 3:** Implementar (hereda meta/summary de Fase A; ordena `elements`, y dentro `fields`/`relations`/`enums` ya vienen ordenados de discover; ordena `warnings`). **Step 4:** PASS. **Commit** `feat(crm-atlas): build_atlas_phase_b (completitud + orden + circuit-breaker)`

### Task 2.11: `render_markdown` Fase B — sección de degradados

**Files:** Modify `core/crm_atlas.py`; Test

- [ ] **Step 1: Test** — slug distintivo `extrajudiciales_zzz` degradado → aparece cabecera "N/M resueltos" y el slug **después** de la cabecera de degradados (`md.index("degradado") < md.index(slug)`); `_md_escape` en labels de campo/enum.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar (sección "Elementos con descubrimiento degradado" al principio; tablas por elemento). **Step 4:** PASS. **Commit** `feat(crm-atlas): render fase B (degradados + escape)`

### Task 2.12: Leak-guard carve-out para `docs/crm_atlas/**`

**Files:** Modify `scripts/precommit_leak_guard.py:158`; Test (si hay suite del guard) o verificación manual

- [ ] **Step 1:** En `escanear_formas`, cambiar el skip para que `docs/crm_atlas/**` **no** quede exento (el resto de `docs/` sigue exento). Así el AVISO de email-forma cubre el `.md`/digest commiteados.
- [ ] **Step 2:** Verificar: crear un `.md` de prueba con un email bajo `docs/crm_atlas/` → el guard lo marca; bajo otro `docs/` → sigue exento.
- [ ] **Step 3: Commit** `fix(leak-guard): docs/crm_atlas/** no exento (cubre el atlas commiteado)`

### Task 2.13: CLI 17a — `discover --phase b|all` (cableado A+B + concurrencia)

**Files:** Modify `scripts/crm_atlas.py`; Test

- [ ] **Step 1: Tests (CLI, transport mockeado)** — `--phase all`: `fetch_oas3`→A, `atlas_client`(MockTransport)→B; escribe `.md`+digest, `atlas.json` local; `meta.phase_b.elements_total` correcto. **Auth 401 → exit≠0 y NO existe atlas** (`not out.exists()`). **Quitar `--scope juridicos`** (elegimos los 89); quitar `--also-elcontable`, `ELCONTABLE_ATLAS_DIR`, `import shutil` y el docstring que lo cita.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Cuerpo `b|all`: `spec=fetch_oas3()` + `a=build_atlas_phase_a(spec,...)`; `client=atlas_client()`; `auth_healthcheck(client)`; `slugs=fetch_elements(client)`; `ThreadPoolExecutor(max_workers=4)` sobre `discover_element`; `atlas=build_atlas_phase_b(a, results, tenant=...)`. (Gate + escritura en Task 2.14.)
- [ ] **Step 4:** PASS. **Commit** `feat(crm-atlas): CLI fase B — cableado A+B + concurrencia (sin scope/elcontable)`

### Task 2.14: CLI 17b — gate PII bloquea el write (+ circuit-breaker)

**Files:** Modify `scripts/crm_atlas.py`; Test

- [ ] **Step 1: Tests** — (a) un enum con email → `scan_atlas_for_pii` da hits → **exit≠0, NADA escrito** (ni json local); (b) hits "parece persona" → ese enum se **cuarentena** (a `field_types_no_enumerados`), se re-escanea, y si queda limpio → escribe; (c) `circuit_broken` → exit≠0, nada escrito.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Tras `build_atlas_phase_b`: aplicar cuarentena de los hits heurísticos → re-`scan_atlas_for_pii`; si quedan hits de email o `circuit_broken` → `typer.echo` + `raise typer.Exit(1)` **antes de cualquier `_write_text`**. Solo si limpio, escribir `.md`+digest+json(local). **Único camino de escritura** (lo comparte `--resume`).
- [ ] **Step 4:** PASS. **Commit** `feat(crm-atlas): gate PII bloquea el write + cuarentena + circuit-breaker`

### Task 2.15: `--resume` (reintenta degradados, lee utf-8, pasa por el gate)

**Files:** Modify `scripts/crm_atlas.py`, `core/crm_atlas.py`; Test

- [ ] **Step 1: Tests** — (a) previo con `a`=ok, `b`=failed → `--resume` salta `a`, reintenta `b`; (b) **resume + enum sucio → bloquea** (mismo gate); (c) lectura del previo con `encoding="utf-8"` (round-trip con label `"Año/Categoría|X\nY"`).
- [ ] **Step 2:** FAIL. **Step 3:** `load_previous_atlas(path)` (utf-8) + `is_resolved(el)` (ninguna `probes.value=="failed"`); resume reusa el camino de escritura con gate de Task 2.14. **Step 4:** PASS. **Commit** `feat(crm-atlas): --resume (reintenta degradados, utf-8, con gate)`

---

## Grupo 3 — Corrida en vivo + integración documental

### Task 3.1: Corrida en vivo (checkpoint MANUAL — requiere key en el entorno)

- [ ] **Step 1:** `python -m scripts.crm_atlas discover --phase all` (con `SUDESPACHO_API_KEY` en el entorno).
- [ ] **Step 2:** Verificar: `meta.phase_b.elements_total==89`; `elements_degraded` bajo; ningún `enums` de tipos `Lista*`; el gate no bloqueó (o, si bloqueó, **investigar el hallazgo** antes de seguir — es señal de PII real).
- [ ] **Step 3:** Inspección de higiene del `atlas.json` local (con Python, contando patrones de email en labels, SIN imprimirlos) → 0 emails; `field_types_no_enumerados` registra los `ListaUsuarios`.
- [ ] **Step 4:** `python -m pytest -q --junit-xml=...` (suite completa verde; recordar env vars de sudespacho para los tests que las piden — nota del task_289b4b7b).
- [ ] **Step 5: Commit** de `.md`+digest actualizados.

### Task 3.2: Integración documental + reconciliación doc-hygiene

**Files:** Modify `docs/ARQUITECTURA_CRM_SUDESPACHO.md` (§3/§6/§11 → puntero; **§4.1/§11.1** reconciliación x-api-key), `docs/INTEGRACION_SUDESPACHO.md` (§0 puntero; §8.1 reconciliación **sin borrar** la nota empírica), `CLAUDE.md` (Referencias rápidas), spec §2 (nota 4b: `[]`→`None`).

- [ ] **Step 1:** Vaciar tablas de `ARQUITECTURA §3/§6/§11` a puntero + "por qué"; reconciliar x-api-key en `§4.1/§11.1` **e** `INTEGRACION §8.1` (añadir, no borrar). Alinear spec §2 (probe 4b devuelve `None`).
- [ ] **Step 2:** Cross-links en `INTEGRACION §0` y `CLAUDE.md`.
- [ ] **Step 3:** `python -m pytest -q` (guards de docs verdes — `test_docs_gobernanza` si existe).
- [ ] **Step 4: Commit** `docs(crm-atlas): atlas como SSOT de endpoints + reconciliacion x-api-key`

### Task 3.3: El Contable (MANUAL, fuera del worktree — DIFERIDO)

- [ ] Puntero desde `REFERENCIA §2` al atlas de FeesDefender. **No ejecutable desde el worktree** (`../ElContable` no resuelve; el repo real está en `C:\Users\tnm33\Dev\ElContable`). Se hace en un PR aparte en ese repo, por ruta absoluta, tras mergear esta rama. Sin copia física del artefacto.

---

## Self-review (cobertura de la spec v2)

- §2 fuentes→2.3-2.8. §3 arq→G0+G2. §4 modelo→0.2,2.8,2.10. §5 fases→2.13. §6 barandillas→2.7,2.9,2.12,2.14. §7 robustez→1.1,2.1,2.10(circuit-breaker),2.15. §8 artefactos→1.5. §9 SSOT→3.2. §10 tests→embebidos + los 4 E2E (auth-401 en 2.13, gate-bloquea en 2.14, determinismo-permutado en 2.10, encoding en 2.15). §11 doc-hygiene→3.2. §12 YAGNI→respetado (sin --scope, sin expandir schemas). §13 riesgos→cubiertos. §14 hardening→G1. §15→APÉNDICE.
- Sin placeholders; símbolos definidos antes de usarse (G0 front-load); tests de CLI parchean el módulo CLI; comandos de shell corregidos.

## APÉNDICE — Traza de la auditoría del plan (v1→v2)

BLOCKERS: render_markdown Fase B (→0.3); `import json`/os/time (→0.1); `CrmAtlasError` (→0.1); `get_with_retry` sin cablear + orden (→2.1 antes de 2.8, cableado en 2.8); gate PII solo-email → cuarentena heurística (→2.9, decisión de Nikolai); tests E2E de los 4 blockers (→2.10/2.13/2.14/2.15).
MAJORS: monkeypatch al módulo CLI (→Global Constraints + 1.1/2.13); `_MINI_SPEC` (→1.6); `--junit %TEMP%` (→Global Constraints); `ELEMENTOS_JURIDICOS`/`--scope juridicos` eliminado (→2.13); Task 3 rompe `test_parse_endpoint_fields` (→1.3 Step 4); `--phase all` A+B (→2.13); meta plano→anidado + gen_version 2 (→0.2); leak-guard carve-out (→2.12); circuit-breaker (→2.10); El Contable diferido (→3.3); detector persona invertido → NO usar (→Global Constraints + 2.9).
MINORS: dataclass defaults al final (→1.4); `probes["enums"]="ok"` sin Select (→2.8); `Field.source` (→2.4); `field_types_no_enumerados`=todo≠Select (→2.8); tautologías `assert...or True`/`"a" in md` (→1.5/2.11); allOf test (→1.2); order tests con entrada desordenada (→2.4/2.7); reconciliación x-api-key en ARQUITECTURA §4.1/§11.1 (→3.2); cleanup `--also-elcontable`/`shutil`/docstring (→2.13).
DE-RIESGOS confirmados (no sobre-corregir): refs de línea de Fase A correctas; slug preserva casos; `_request_schema` conserva rama array; `atlas.json` trackeado (git rm --cached correcto); literales de `probes` consistentes; allowlist `Select` protege aunque `ENUM_DENYLIST` no sea wildcard.
