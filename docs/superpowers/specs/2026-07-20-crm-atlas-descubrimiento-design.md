# Diseño — Atlas del CRM sudespacho (descubrimiento exhaustivo, re-ejecutable)

_Brainstorming Claude Code · FeesDefender · 2026-07-20_
_**v2 — reescrita tras auditoría adversarial (4 revisores en paralelo, 2026-07-20).** Los
hallazgos y su resolución están en §15._
_Origen: petición de Nikolai — "no quiero cada vez ir descubriendo los endpoints del CRM;
con los datos que ya tienes, descubre TODOS los endpoints, relaciones y campos existentes".
Precedentes: `docs/INTEGRACION_SUDESPACHO.md`, `docs/ARQUITECTURA_CRM_SUDESPACHO.md`,
`../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md`._

## 0. Estado de las decisiones (cerradas)

| Decisión | Resuelto |
|---|---|
| **Alcance** | Atlas completo en vivo: inventario de endpoints (Fase A) + esquema por elemento (Fase B) |
| **Cobertura de elementos** | **TODOS los 89** del tenant (`/api/elements`), incluidos contabilidad/RRHH. Solo esquema |
| **Barrera PII (nueva, BLOCKER de la auditoría)** | Los **valores** de enum solo se vuelcan para campos `type=="Select"` (taxonomías estáticas). Los tipos dinámicos respaldados por tabla — `ListaUsuarios`, `ListaBancos`, `ListaGrupos`, `ListaElemento*`, `Tags` — se registran **por tipo, nunca por valor** (verificado: `ListaUsuarios` devuelve nombre+**email** del personal). Además, **gate anti-PII en el generador antes de escribir** (detector email/persona reusando `core/anon`) que **bloquea** — NO se confía en `leak-scan` (salta `docs/` y no lista al personal propio) |
| **Artefacto en git** | Se commitean **`CRM_SUDESPACHO_ATLAS.md`** (referencia navegable) + **`atlas.digest.md`** (superficie de deriva legible). **`atlas.json` se gitignora** y se regenera bajo demanda (>1 MB con 89 elementos; su diff no se revisa) |
| **El Contable** | **Sin `--also-elcontable`.** Artefacto canónico solo en FeesDefender + **puntero** desde la referencia común. No se copia el fichero cross-repo |
| **Partición por credenciales** | Fase A pública (cero `.env`) = endpoints; Fase B autenticada (`x-api-key`) = esquema por elemento |
| **Escritura** | NUNCA. El cliente del harness no implementa POST/PUT/PATCH/DELETE. Único efecto server-side: el 500 inocuo del probe 4b |
| **Ubicación del código** | `core/crm_atlas.py` (lógica pura) + `scripts/crm_atlas.py` (CLI). Auth resuelta **localmente** en `core/crm_atlas.py`; **NO** se retrofitea `SudespachoConfig` |
| **Estratificación SSOT** | Atlas = verdad cruda generada; los docs a mano lo **citan** Y se **vacían** las tablas de endpoints que ahora dupliquen (§9) |

## 0.bis Estado empírico (validado en vivo 2026-07-20)

Fase A **construida, testeada (11 tests) y corrida** (commit `87ff113`). Mecanismos de Fase B y
riesgos de PII **validados en vivo** con la `x-api-key` del entorno (solo esquema):

| Hecho | Valor confirmado |
|---|---|
| Credencial | `SUDESPACHO_API_KEY` es **secreto de Windows** (env var de usuario), heredado por `os.environ` al arrancar. `core/config.py` hace `load_dotenv(override=False)` → el SO gana. Presente en la sesión (122 chars) sin `.env` |
| Base URL | Constante pública `https://api-crm-commons-pro.sudespacho.biz` |
| Endpoints (Fase A) | **548 operaciones** · **486 paths** (424 con operación + 62 huérfanos solo-`parameters`) · **125 módulos** (tags). El tenant creció desde 466 (2026-05-06) |
| Catálogo | `GET /api/elements` → **89 elementos**. ⚠️ Forma dependiente de `Accept`: `application/json` → lista plana; `ld+json`/`*/*` → Hydra `{hydra:member}`. Miembro: `{"label", "id":{"value":slug}}` |
| Campos | `view/config/{el}/fields` → `{items:[{name,type,label,active,deleted}]}`. Vocabulario de `type` real: `{Moneda,Date,CheckBox,EditorHtmlSimple,TextCorto,Autoincremental,ListaUsuarios,Select,Tags,NumEntero,ListaBancos,DateTime}`. **NO existe `Enum`** — los select son `type=="Select"` |
| Relaciones | `view/config/{el}/relations` → `{parent:[...],children:[...]}`. Captura **dirección**, no cardinalidad. Un slug puede estar en ambos → tratar como **grafo**, no árbol |
| Enums | `view/enums/{el}/{prop}` → `{enums:[{id,label,...}]}`. **`Select`** = taxonomía inocua (fiscal/geográfica). **`ListaUsuarios`** = nombre+email del personal (PII). **`ListaBancos`** = config bancaria interna |
| De-riesgos | IBANs (`CuentaBancaria`) y listas de clientes/proveedores (`ListaElemento`) dan **500** en `view/enums` → NO se filtran por esta vía |
| Legacy `@token`/PHPSESSID | No presentes y **no necesarios** (solo escritura/frontal PHP) |

## 1. Propósito y alcance

Producir un **artefacto generado, exhaustivo y re-ejecutable** = la foto completa de la superficie
del CRM sudespacho en el tenant `tnm`, para **no descubrir a mano** endpoints, campos o enums. El
descubrimiento a trozos (HAR/probe suelto) se sustituye por una corrida que baja todo y lo persiste.

**En alcance:** inventario de endpoints (486 paths / 548 ops); catálogo de los 89 elementos; por
elemento sus **campos** (nombre+tipo), **relaciones** (parent/children) y **enums de campos
`Select`**; render humano + digest de deriva.

**Precisión sobre "campos":** los campos del atlas son los del **modelo de datos del elemento**
(`view/config/fields`), NO los del contrato REST de un body POST/PATCH. El atlas guarda el **nombre
del `$ref`** del requestBody, no expande `components/schemas` (YAGNI; §12).

**Fuera de alcance:** ver §12. Nunca datos de registros; nunca escritura; no cliente de uso general.

## 2. Fuentes de descubrimiento

Cinco fuentes, todas de **lectura**; ninguna crea registros. Formas de payload **verificadas en vivo**.

| # | Fuente | Da | Auth | Fase |
|---|---|---|---|---|
| 1 | `GET /api/docs.json` | 486 endpoints (método, path, params, auth, schema req/resp, tags) | **Pública** | A |
| 2 | Portal `developers.sudespacho.net/docs/api-crm/{slug}` | URL de doc por operación (enlace **opcional**) | Pública | A |
| 3 | `GET /api/elements` (`Accept: application/json`) | 89 slugs (`item["id"]["value"]`); fallback: desenvolver `hydra:member` | `x-api-key` | B |
| 4a | `GET /api/view/config/{el}/fields` (**primaria**) | `{items:[{name,type,label,active,deleted}]}` — campos **con tipo** | `x-api-key` | B |
| 4b | Probe de propiedad inválida (§0.3 `INTEGRACION`) | GET → **500** con `detail` "…properties are: a,b,c" (fallback si 4a 404) | `x-api-key` | B |
| 5a | `GET /api/view/config/{el}/relations` | `{parent:[...],children:[...]}` | `x-api-key` | B |
| 5b | `GET /api/view/enums/{el}/{prop}` | `{enums:[{id,label}]}` — **solo campos `type=="Select"`** | `x-api-key` | B |

**Notas de fuente:**
- **1 es pública** (verificado con WebFetch y httpx local sin credenciales) → el inventario de
  endpoints no depende de `.env`.
- **4a primaria; 4b fallback endurecido.** 4b **exige `status==500` Y** que el `detail` matchee el
  patrón `properties are:`; si el patrón no aparece (el CRM tiene otros 500: "Array to string
  conversion", "Undefined array key properties" — `INTEGRACION §8.3`), devuelve `None` + warning, **no
  misparsea** (`None` = "falló/no aplica", coherente con `null`=sub-llamada falló del §4). Si la respuesta fuera `200` (elemento que valida laxo) **nunca** se trata como esquema
  (guarda anti-lectura-de-registros). 4b corre **fuera** de la capa de reintento-5xx (§7) para que su
  500 deliberado no dispare backoff.
- **`view/complete` NO se usa** (toma un id de **registro** → leería un registro; rompe la barandilla).
- **5b — enums solo de `Select`.** `select_enum_fields(fields)` = allowlist `type=="Select"`. Los
  tipos dinámicos (`ListaUsuarios`/`ListaBancos`/`ListaGrupos`/`ListaElemento*`/`Tags`) se registran
  por **tipo** (el campo existe y es tal tipo) pero **sus valores NUNCA** se piden a `view/enums`
  (§6). Cualquier `type` no visto antes → warning "tipo desconocido, revisar", no se asume select.
- **2 es opcional**: el portal es Docusaurus generado del mismo OpenAPI; solo se **enlaza**.

## 3. Arquitectura

Regla 3 capas: lógica en `core/`, la CLI orquesta. Auth resuelta localmente (sin tocar `SudespachoConfig`).

```
core/crm_atlas.py            # lógica pura + cliente HTTP bespoke
    # --- Fase A (hecha; con arreglos de auditoría, §14) ---
    fetch_oas3(base_url=PUBLIC, *, client, timeout) -> dict
    parse_oas3(spec, *, dev_links) -> list[Endpoint]      # + deprecated, param.enum/default
    operation_id_to_dev_slug(op_id) -> str                # kebab lodash: colapsa no-alfanum, trailing /
    find_orphan_paths(spec) -> list[dict]
    # --- Fase B (nueva) ---
    atlas_client() -> httpx.Client                        # x-api-key del entorno; NUNCA logea headers/body
    auth_healthcheck(client) -> None                      # GET /api/elements; 401/403 -> aborta (fail-fast)
    fetch_elements(client) -> list[str]                   # Accept json; desenvuelve hydra:member; guarda
    discover_element(client, slug) -> ElementSchema       # orquesta 4a/4b + 5a + 5b, con degradación
        parse_fields_config(payload) -> list[Field]        # 4a: {items:[{name,type,label,...}]}
        parse_invalid_property_probe(resp) -> list[str]|None # 4b: exige 500 + patrón; si no, None
        parse_relations_config(payload) -> Relations       # 5a: {parent,children}
        select_enum_fields(fields) -> list[str]            # allowlist type=="Select"; denylist Lista*/Tags
        parse_enums(payload) -> list[EnumValue]            # 5b
    scan_atlas_for_pii(atlas) -> list[str]                # gate: email/persona vía core.anon; no vacío -> BLOQUEA
    build_atlas(...) -> dict                              # orden determinista total
    render_markdown(atlas) -> str                         # .md navegable (escapa | y \n en TODO label)
    render_digest(atlas) -> str                           # ~100-200 líneas: por módulo nº ops; por elemento nº campos + hash

scripts/crm_atlas.py         # CLI Typer
    discover --phase {a|b|all} --scope {all|juridicos} --resume --no-stamp-time
             # (SIN --also-elcontable)
```

**Cliente HTTP:** Fase A usa `PUBLIC_BASE_URL` sin key. Fase B construye su **propio** `httpx.Client`
con header `x-api-key` (de `os.environ`), backoff y concurrencia (§7). **No** se reutiliza ni se
modifica `SudespachoConfig` (su invariante "hay api_key" no debe relajarse; `require_key=False` sería
un footgun para el cliente de pull existente).

## 4. Modelo de datos (`atlas.json`)

```jsonc
{
  "meta": {
    "tenant": "tnm", "generated_at": null,        // null salvo --stamp-time; si se sella, UTC 'Z'
    "generator": "scripts.crm_atlas", "generator_version": 2,
    "phase_a": {"complete": true},
    "phase_b": {"ran": true, "elements_total": 89, "elements_ok": 87, "elements_degraded": 2,
                "complete": false},                // complete == (ran && degraded==0)
    "auth_note": "El spec declara header 'Authorization' (apiKey), pero devuelve 401; el header operativo es 'x-api-key' (INTEGRACION §2.1).",
    "sources": { "oas3": {...}, "dev_portal": {...} }
  },
  "summary": { "total_operations": 548, "total_path_keys": 486, "total_paths": 424,
               "paths_without_operations": 62, "by_method": {...}, "by_tag": {...} },
  "endpoints": [ { "path","method","operation_id","summary","description","tags","auth",
                   "deprecated": false, "parameters":[{name,location,required,type,enum,default,description}],
                   "request_schema","response_codes","dev_doc_url" } ],
  "elements": [ {
    "slug": "extrajudiciales", "name_ui": "…",
    "fields": [ {"name":"Referencia_Cliente","type":"TextCorto","label":"…","source":"view/config/fields"} ],
    "relations": {"parent":[...],"children":[...]},   // null si la sub-llamada falló
    "enums": { "tipo_procedimiento": [{"id","label"}] },  // solo Select; Lista*/Tags NO
    "field_types_no_enumerados": {"profesional_asignado":"ListaUsuarios"},  // registrados por tipo, sin valores
    "probes": {"fields":"view/config/fields|500-probe|failed", "relations":"ok|failed", "enums":"ok|failed"}
  } ],
  "paths_without_operations": [ {"path","declared_keys","parameters"} ],
  "warnings": [ "element 'X': relations -> 404" ]   // solo status/endpoint, NUNCA payload
}
```

`null` = sub-llamada falló; `[]`/`{}` vacío = confirmado vacío (HTTP 200 sin contenido). Dataclasses
en `core/crm_atlas.py`.

## 5. Fases de ejecución

- **Fase A (pública):** ✅ hecha. `discover --phase a` → endpoints.
- **Fase B (autenticada):** `discover --phase b|all`. **Primero `auth_healthcheck`** (401/403 global
  → aborta, no degrada). Luego recorre los elementos (según `--scope`, default `all`=89), por elemento
  4a/4b + 5a + 5b con degradación por sub-llamada (a `probes`+`warnings`, `null` en el campo). Al
  final: `scan_atlas_for_pii` (BLOQUEA si encuentra), luego escribe. `phase_b.complete` solo si
  `elements_degraded==0`.

## 6. Barandillas duras (higiene y seguridad)

1. **Solo esquema, nunca datos.** No se llama a `element_registries`/`element_register` para leer
   registros. 4b tiene guarda anti-200 (§2).
2. **Anti-PII de enums (BLOCKER de auditoría, verificado):** `select_enum_fields` = **allowlist
   `type=="Select"`**; **denylist** `ListaUsuarios`/`ListaBancos`/`ListaGrupos`/`ListaElemento*`/`Tags`
   → se registra el tipo, **nunca** el valor. Test que **falla** si un `Lista*`/`Tags` llega a `enums{}`.
3. **Gate anti-PII en el generador, antes de escribir:** `scan_atlas_for_pii` corre email/persona
   (reusando `core/anon`) sobre el atlas final; si detecta algo, **aborta el write** (no se commitea).
   **No se confía en `leak-scan`**: `precommit_leak_guard.py:158` salta `docs/` y la blocklist no lista
   al personal propio → daría verde sobre PII. (Complementario: quitar la exención `docs/` para
   `docs/crm_atlas/**` en el leak-guard.)
4. **Sin escritura.** El cliente no implementa verbos de mutación.
5. **Secretos solo por entorno.** La `x-api-key` de `os.environ`; el cliente **nunca logea headers ni
   bodies**; `warnings[]` solo lleva `status`+`endpoint`, jamás el payload (un body de `ListaUsuarios`
   es PII). El `atlas.json`/`.md`/digest no contienen la key.
6. **Deriva detectable.** Re-ejecutar + `git diff` sobre el **digest** = qué cambió (elementos/campos/
   enums nuevos o retirados).

## 7. Robustez operativa

- **Volumen (medido):** 89 elementos, ~0,3 s/llamada, sin cabeceras de rate-limit. ≈ pocos cientos de
  GETs → **decenas de segundos**, no "minutos".
- **Concurrencia 4** (conservador; sin límite documentado, el ahorro de 8 vs 4 son segundos).
- **Backoff con números:** ante 429/5xx (fuera del probe 4b), reintento exponencial
  `delay=min(1s·2^n, 30s)`, `n_max=5`, jitter ±20%; **respetar `Retry-After`** si aparece.
- **Fail-fast de auth (§5):** healthcheck antes del bucle. Circuit-breaker: si >50% de elementos fallan
  seguidos, abortar (probable fallo global, no "elemento simple").
- **Determinismo (invariante duro):** `json.dumps(atlas, sort_keys=True, ensure_ascii=False,
  indent=2)` **y** ordenación explícita tras el gather: `elements` por slug, `fields` por name,
  `relations` parent/children por slug, `enums` props por name y valores por id, `warnings`
  alfabético, `endpoints` por (path,método). Test: construir dos veces con orden de llegada permutado
  → **idéntico byte a byte**.
- **`generated_at`:** default **`--no-stamp-time`** (null) para el artefacto commiteado; si se sella,
  **UTC 'Z'** (`now_iso_utc`, no `now_iso` local). Evita diff en cada corrida.
- **Resume:** "resuelto" = elemento con **todos** los `probes` en "ok"; `--resume` **reintenta los
  degradados** (no solo rellena ausentes). Lee el atlas previo con `encoding="utf-8"` explícito
  (Windows: sin ello, cp1252 → mojibake en labels con tildes/`ñ`).
- **Encoding:** escritura y lectura siempre `utf-8`, `newline="\n"`, `ensure_ascii=False`.
- **Enums grandes/paginados:** si `view/enums` trajera `hydra:totalItems`, comparar con lo recibido y
  avisar si hay truncado.

## 8. Artefactos y ubicación

- **`docs/CRM_SUDESPACHO_ATLAS.md`** — referencia navegable. ✅ commit.
- **`docs/crm_atlas/atlas.digest.md`** — digest de deriva (~100-200 líneas). ✅ commit.
- **`docs/crm_atlas/atlas.json`** — verdad-máquina cruda (>1 MB con Fase B). **gitignore**; se
  regenera con `discover`. No es dependencia de runtime.
- **El Contable:** **sin copia física**. Puntero (link) desde `REFERENCIA §2` al `.md`/digest de
  FeesDefender. Respeta la dirección de propagación de `REFERENCIA §8` (no empujar hacia dentro de El
  Contable). El generador es código y su hogar correcto es FeesDefender.
- **Cross-links:** `INTEGRACION §0`, `ARQUITECTURA` (§9), `REFERENCIA §2`, `CLAUDE.md`.

## 9. Estratificación SSOT

Regla "un hecho, un hogar" (`GOBERNANZA_FUENTES_VERDAD.md`). El atlas es el hogar de **"qué existe"**
(endpoints/campos/relaciones/enums). Por tanto, al aterrizarlo:
- **Vaciar** `ARQUITECTURA_CRM_SUDESPACHO.md` **§3** (tablas de endpoints), **§6** (tabla de módulos) y
  **§11** (conteo de paths) → reducir a **puntero al atlas** + el "por qué" conceptual. Si no, el atlas
  **suma** un hogar (ya hay drift 466 vs 486) en vez de **ser** uno.
- `INTEGRACION §3.1` conserva solo endpoints **confirmados con payload** (eso es "qué usamos y cómo",
  hogar legítimamente distinto) + puntero al atlas para el resto.

## 10. Tests (TDD)

Parsers puros con fixtures; HTTP mockeado (`httpx.MockTransport`). Además del camino feliz:
- `parse_oas3`: allOf/oneOf/anyOf en reqBody, `deprecated`, `parameters` por `$ref`, param `enum`/`default`.
- `_request_schema`: `application/json`, `application/ld+json`, **`application/merge-patch+json`**, **`multipart/form-data`**.
- `operation_id_to_dev_slug`: casos con paréntesis y con `" - "` (los que hoy dan 404).
- `fetch_elements`: forma **lista** Y forma **Hydra** (`hydra:member`); miembro malformado → guarda.
- `parse_fields_config` (no `parse_complete_view`).
- `parse_invalid_property_probe`: 500+patrón OK; 500 sin patrón → `None`+warning; **200 → nunca esquema**.
- `select_enum_fields`: `Select` sí; **`ListaUsuarios`/`ListaBancos`/`Tags` NO** (test que falla si se cuela).
- `scan_atlas_for_pii`: atlas con un email/nombre → **detecta y bloquea**.
- **Determinismo:** dos builds con orden de llegada permutado → JSON idéntico byte a byte.
- **Completitud:** auth 401 → aborta (no atlas "verde vacío"); N elementos degradados → `phase_b.complete==false` y salen en la sección de degradados del `.md`.
- **Resume:** salta los "ok", **reintenta** los degradados.
- **Encoding round-trip:** label `"Año/Categoría|X"` → escribir/releer → igualdad (encoding + escape de `|`/`\n`).

## 11. Correcciones de doc-hygiene (preservar, no sobrescribir)

La guía oficial (`developers.sudespacho.net/docs/first-steps/authentication/`) documenta `x-api-key`.
Al aterrizar: **añadir** una reconciliación en `INTEGRACION §8.1`/`ARQUITECTURA §4.1/§11.1` ("la guía en
prosa documenta `x-api-key`; el spec OAS3 declara `Authorization` y no concuerdan") **sin borrar** la
nota empírica de que `Authorization` devuelve 401 y `x-api-key` es el que funciona (conocimiento
load-bearing del cliente; regla del proyecto: no refutar sin confirmación de Nikolai).

## 12. Fuera de alcance (YAGNI)

- Datos de registros; escritura; cliente de uso general.
- Expandir `components/schemas` (los campos de un body POST/PATCH); el atlas guarda solo el nombre del `$ref`.
- Matriz de permisos por elemento (DOM, ~198): descubrimiento por navegador → extensión futura.
- Enriquecimiento profundo del portal (solo se enlaza).
- Publicar como skill/plugin `sudespacho-integration` (futuro si se estabiliza).

## 13. Riesgos y verificación

Los riesgos originales (¿existe `view/config/relations`? ¿shape de `/api/elements`? ¿credenciales?
¿es `Enum` o `Select`? ¿PII en enums?) **quedaron resueltos por la validación en vivo** (§0.bis, §15).
Residuales: (a) `view/config/fields` no verificado en los 89 (solo `extrajudiciales`/`facturas_recibidas`)
→ fallback 4b + warning; (b) un `type` nuevo no clasificado → warning, no se asume select; (c) enums
paginados → aviso de truncado; (d) aunque es solo esquema, el gate anti-PII (§6.3) corre igual antes de
escribir. Anotar cualquier endpoint que falle en `INTEGRACION`/`DEAD_ENDS` (no marcar dead end sin
confirmación de Nikolai).

## 14. Plan de entrega por fases

1. **Fase A** ✅ hecha (`87ff113`), **+ hardening** (bugs verificados en la auditoría):
   `json.dumps(sort_keys=True)`; `generated_at` default no-stamp / UTC; `_request_schema` acepta
   `merge-patch+json` + `multipart/form-data`; `operation_id_to_dev_slug` colapsa no-alfanuméricos +
   trailing `/`; `Endpoint.deprecated` + `Param.enum/default`; nota `auth_note` (`x-api-key`);
   `render_digest`. Regenerar y re-commitear el `.md`+digest; gitignorar el `.json`.
2. **Fase B:** `atlas_client` + `auth_healthcheck` + `fetch_elements` (hydra) + `discover_element`
   (4a/4b/5a/5b + `select_enum_fields` allowlist) + `scan_atlas_for_pii` + backoff/concurrencia +
   determinismo + resume + tests (§10). Corrida en vivo (`x-api-key` ya en el entorno) → `elements[]`.
3. **Integración doc:** vaciado de tablas de `ARQUITECTURA §3/§6/§11` a punteros (§9); cross-links;
   reconciliación doc-hygiene §11; puntero desde `REFERENCIA §2` (sin copia).

Cada fase/etapa = su propio PR (rama + PR, `main` protegida).

## 15. Traza de la auditoría adversarial (2026-07-20)

Cuatro revisores en paralelo (técnica, seguridad/PII, alcance/SSOT, robustez). Verificado por el
coordinador en vivo lo decisivo. Resolución:

| # | Hallazgo (severidad) | Resolución en esta v2 |
|---|---|---|
| PII-1 | **BLOCKER** `ListaUsuarios` enum vuelca nombre+email del personal | §0/§6.2: allowlist `Select`, denylist `Lista*`/`Tags` |
| PII-2 | **BLOCKER** "pasa leak-scan → seguro" es falso (salta `docs/`, no lista personal propio) | §6.3: gate anti-PII en el generador; quitar exención `docs/crm_atlas/**` |
| TEC-1 | **BLOCKER** el `type` select es `Select`, no `Enum` → cero enums en silencio | §0.bis/§2/§6.2: filtrar `Select` |
| TEC-2 | **BLOCKER** `/api/elements` es Hydra según `Accept` | §2/§3: `Accept: json` + desenvolver `hydra:member` |
| ROB-1 | **BLOCKER** atlas "verde pero vacío" (auth mala marcada completa) | §5/§7: fail-fast auth + métrica de completitud + `null` vs `[]` |
| TEC-M1 | `view/complete` toma id de registro (rompe barandilla) | §2: purgado; solo `view/config/fields` |
| TEC-M2 | probe 4b sin guardas (200→lee registros; otros 500→misparse) | §2: exige 500+patrón; guarda anti-200; fuera de retry |
| TEC-M3 | `_request_schema` ignora merge-patch/multipart (17 ops) | §14: añadir content-types |
| TEC-M4 | ~11 URLs de portal 404 (paréntesis, triple guión) | §14: colapsar no-alfanum + trailing `/` |
| TEC-M5 | atlas muestra header `Authorization` (401) | §4: `meta.auth_note` = `x-api-key` |
| ROB-B4/B8 | determinismo roto (`sort_keys`, orden por concurrencia, `generated_at` local) | §7/§14 |
| ROB-B5 | backoff/concurrencia hand-wave; cliente reutilizado no aporta | §7: números concretos, cliente propio |
| GOV-1 | **BLOCKER** commitear 2 artefactos enormes | §0/§8: `.md`+digest; `atlas.json` gitignore |
| GOV-2 | atlas = 2º hogar SSOT | §9: vaciar tablas de `ARQUITECTURA` |
| GOV-3 | `--also-elcontable` invierte propagación + propaga PII | §0/§8: eliminado; puntero |
| GOV-5 | `config_for_atlas` ensucia `SudespachoConfig` | §3: auth local, no retrofit |
| GOV-7 | §11 sobrescribía nota empírica `x-api-key` | §11: preservar + reconciliar |

**De-riesgos (no sobre-corregir):** IBANs y listas de clientes NO se filtran (500 en `view/enums`);
enums `Select` geográficos/fiscales son esquema legítimo y valioso; construcciones OAS3 exóticas
mayormente ausentes del spec real; paths huérfanos y `$ref` de params compartidos ya bien manejados.
