# Diseño — Atlas del CRM sudespacho (descubrimiento exhaustivo, re-ejecutable)

_Brainstorming Claude Code · FeesDefender · 2026-07-20_
_Origen: petición de Nikolai — "no quiero cada vez ir descubriendo los endpoints del CRM;
con los datos que ya tienes, descubre TODOS los endpoints, relaciones y campos existentes".
Precedentes de conocimiento: `docs/INTEGRACION_SUDESPACHO.md`, `docs/ARQUITECTURA_CRM_SUDESPACHO.md`,
`../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md`._

## 0. Estado de las decisiones (cerradas en brainstorming)

| Decisión | Resuelto |
|---|---|
| **Alcance** | **Atlas completo en vivo** (no "solo consolidar docs" ni "volcado OAS3 crudo"): inventario de endpoints + esquema por elemento (campos, relaciones, enums) |
| **Cobertura de elementos** | **TODOS los del tenant** que devuelva `/api/elements` (incluidos contabilidad/RRHH/tickets). Seguro porque **solo se lee esquema**, nunca datos de registros |
| **Ubicación del artefacto** | **Compartido con El Contable**: se genera en FeesDefender (`docs/crm_atlas/`) y se sincroniza copia a `../ElContable/docs/crm_atlas/`; ambos docs a mano lo enlazan |
| **Partición por credenciales** | **Fase A pública (cero credenciales)** = inventario de endpoints desde `/api/docs.json`; **Fase B autenticada (`x-api-key`)** = esquema por elemento. El atlas es útil solo con Fase A |
| **Naturaleza del artefacto** | **Generado por script, re-ejecutable.** No se mantiene a mano. `git diff` entre corridas = deriva del tenant |
| **Barandilla dura** | **Solo esquema.** Nunca se leen registros reales (`element_registries` con datos queda fuera). Cero PII, cero datos financieros → el `atlas.json`/`.md` pasan `leak-scan` y son commiteables |
| **Escritura** | **NUNCA.** El cliente HTTP del harness no implementa POST/PUT/PATCH/DELETE. La única llamada "no-GET-limpia" es el probe de propiedad inválida, que es un GET que provoca un 500 inocuo |
| **Ubicación del código** | `core/crm_atlas.py` (lógica pura, regla 3 capas) + `scripts/crm_atlas.py` (CLI Typer) |
| **Estratificación con docs existentes** | Atlas = capa de **verdad cruda generada**; `INTEGRACION`/`ARQUITECTURA`/referencia común = **doctrina a mano** que lo cita. No compiten, no se duplican |

## 0.bis Estado empírico (validado en vivo 2026-07-20)

Fase A **construida, testeada y corrida** (PR en rama; `core/crm_atlas.py` + `scripts/crm_atlas.py`
+ `tests/test_crm_atlas.py`). Los mecanismos de Fase B **validados en vivo** con la `x-api-key`.

| Hecho | Valor confirmado |
|---|---|
| Credencial | `SUDESPACHO_API_KEY` es un **secreto de Windows** (variable de entorno de usuario); Python la hereda por `os.environ` al arrancar. `core/config.py` hace `load_dotenv(override=False)` → el env del SO gana. **Ya presente en la sesión** (122 chars) sin `.env` en el worktree |
| Base URL | No es secreto: constante pública `https://api-crm-commons-pro.sudespacho.biz` (la pone el harness) |
| Endpoints (Fase A) | **548 operaciones** · **486 paths** declarados (424 con operación + **62 huérfanos** solo-`parameters`, capturados) · **125 módulos** (tags). El tenant creció desde 466 (2026-05-06) |
| Catálogo de elementos | `GET /api/elements` → 200 · **89 elementos** · slug en `item["id"]["value"]`, nombre en `item["label"]` |
| Campos | `view/config/{el}/fields` → 200 con `type` por campo (verificado: `extrajudiciales`, 34 campos). Probe inválido → 500 con nombres (fallback), también verificado |
| Relaciones | `view/config/{el}/relations` → 200 `{parent,children}` (verificado: `extrajudiciales`) |
| Enums | `view/enums/{el}/{prop}` → 200 `{enums:[{id,label}]}` (verificado) |
| Legacy `@token`/PHPSESSID | **No presentes** y **no necesarios** para el atlas (solo escritura/frontal PHP) |

**Conclusión:** la Fase B es ejecutable ya, sin más input — la key vive en el entorno de la sesión
y todos los endpoints de descubrimiento responden con `x-api-key`.

## 1. Propósito y alcance

Producir un **artefacto generado, exhaustivo y re-ejecutable** que sea la foto completa de la
superficie del CRM sudespacho en el tenant `tnm`, de modo que **nunca haya que descubrir un
endpoint, un campo o un enum a mano caso por caso**. El descubrimiento a trozos (HAR por
elemento, probe suelto) se sustituye por una corrida que baja todo de una vez y lo persiste.

**En alcance:**
- Inventario completo de endpoints REST (los ~466 paths del OpenAPI).
- Catálogo de todos los tipos de elemento del tenant.
- Por cada elemento: **campos** (nombres y, si disponible, tipo/label), **relaciones** válidas
  (con dirección) y **enums** de sus campos select.
- Render humano navegable + fuente legible por máquina.
- Re-ejecutable con detección de deriva por `git diff`.

**Fuera de alcance (YAGNI):** ver §12. En particular: NO se leen datos de registros, NO se
escribe nada en el CRM, NO se construye un cliente de uso general (eso ya es `core/` y el MCP
`sudespacho`), NO se mapea la matriz de permisos por DOM (queda como extensión futura, §12).

## 2. Fuentes de descubrimiento

Cinco fuentes, todas de **lectura**; ninguna crea registros de prueba.

> **✅ Validación en vivo 2026-07-20** (con la `x-api-key` del entorno; ver §0.bis): los 5
> mecanismos devuelven 200/500 como se espera. Las formas de payload de abajo son las **reales**,
> ya confirmadas — no supuestas.

| # | Fuente | Método | Da | Auth | Fase |
|---|---|---|---|---|---|
| 1 | `GET /api/docs.json` | GET | Los **486** endpoints: método, path, params, auth, schema req/resp, tags | **Pública** | A |
| 2 | Portal `developers.sudespacho.net/docs/api-crm/{slug}` | GET | Nombre humano + URL de doc por operación (enriquecimiento **opcional**) | Pública | A |
| 3 | `GET /api/elements` | GET | Catálogo del tenant: **89 elementos**, cada uno `{"label","id":{"value":slug}}` (slug en `id.value`) | `x-api-key` | B |
| 4a | `GET /api/view/config/{element}/fields` (**primaria**) | GET | `{"items":[{id,name,label,type,active,deleted}]}` — campos **con tipo** (`Moneda`,`Date`,`Enum`…) | `x-api-key` | B |
| 4b | Probe de propiedad inválida (§0.3 de `INTEGRACION`) | GET → 500 | Lista de **nombres** de campo (fallback si 4a falla) | `x-api-key` | B |
| 5a | `GET /api/view/config/{element}/relations` | GET | `{"parent":[...],"children":[...]}` — slugs relacionados por dirección | `x-api-key` | B |
| 5b | `GET /api/view/enums/{element}/{propiedad}` | GET | `{"enums":[{id,label}]}` de un campo select | `x-api-key` | B |

**Notas de fuente:**
- **1 es pública** (verificado 2026-07-20 con WebFetch **y** con httpx local, sin credenciales).
  Es el mayor de-riesgo: el inventario de endpoints no depende de tener `.env`.
- **4a primaria sobre 4b**: `view/config/{el}/fields` da nombre + **tipo** + label + active/deleted
  (verificado sobre `extrajudiciales`: 34 campos con tipo). El probe (4b) solo da nombres y queda
  como fallback si 4a falla para algún elemento.
- **5b (enums)**: los campos select se identifican por el `type` que devuelve **4a** (p. ej. `Enum`),
  y solo sobre esos se llama `view/enums` — así se evita sondear todos los campos. Verificado
  2026-07-20 (`facturas_recibidas/tipo_operaciones_iva` → `{enums:[{id,label}]}`).
- **2 es opcional**: el portal es casi con seguridad un Docusaurus generado desde el mismo
  OpenAPI (slug `get-activities-collection` es el patrón openapi→docusaurus), así que aporta
  poco sobre el spec. Se limita a **enlazar** cada path a su página; no se scrapea contenido.

## 3. Arquitectura

Regla 3 capas: lógica en `core/`, la CLI solo orquesta.

```
core/crm_atlas.py            # lógica pura, funciones testeables offline
    fetch_oas3(client)                 -> dict            # baja /api/docs.json
    parse_oas3(spec) -> list[Endpoint]                    # normaliza los 466 paths
    fetch_elements(client) -> list[str]                   # /api/elements → slugs (item["id"]["value"])
    discover_element(client, slug) -> ElementSchema       # orquesta 4a/4b + 5a + 5b por elemento
        parse_fields_config(payload) -> list[Field]        # 4a primaria: {"items":[{name,type,label,...}]}
        parse_invalid_property_probe(detail_500) -> list[str]   # 4b fallback: "...properties are: a,b,c"
        parse_relations_config(payload) -> list[Relation]  # 5a: {"parent":[...],"children":[...]}
        parse_enums(payload) -> list[EnumValue]            # 5b: {"enums":[{id,label}]}
        select_enum_fields(fields) -> list[str]            # campos cuyo type es Enum → a 5b
    build_atlas(endpoints, elements, meta) -> Atlas       # dataclass → dict serializable
    render_markdown(atlas) -> str                         # atlas.json → CRM_SUDESPACHO_ATLAS.md

scripts/crm_atlas.py         # CLI Typer, calcada de scripts/sync_sudespacho.py
    discover  --phase {a|b|all}  --also-elcontable  --out-dir  --resume
```

**Cliente HTTP:** se reutiliza el `httpx` de `core/sync_sudespacho.py`. Para la **Fase A** se
instancia un cliente **sin API key y con base URL por defecto** al host público conocido
(`https://api-crm-commons-pro.sudespacho.biz`, constante del módulo, sobreescribible por
`--base-url` o `SUDESPACHO_BASE_URL`) → la Fase A corre con **cero `.env`**. Como `from_env` hoy
exige `SUDESPACHO_BASE_URL` + `SUDESPACHO_API_KEY`, se añade un builder mínimo
(`config_for_atlas(require_key=False)`) que no rompe el contrato actual de `SudespachoConfig`.
Para la **Fase B** se usa `x-api-key`; si un endpoint concreto exigiera Bearer JWT, el cliente
reintenta con `SUDESPACHO_LEGACY_JWT`.

**Degradación por elemento:** `discover_element` captura la excepción de cada sub-llamada y
la registra en `warnings[]` del atlas en vez de abortar la corrida. Un elemento con relaciones
"no disponibles" sale con `relations: []` + warning, y la corrida sigue.

## 4. Modelo de datos del atlas (`atlas.json`)

```jsonc
{
  "meta": {
    "tenant": "tnm",
    "generated_at": "2026-07-20T09:00:00Z",   // se estampa fuera del harness (ver §7)
    "generator": "scripts.crm_atlas",
    "generator_version": 1,
    "phase_a_complete": true,
    "phase_b_complete": false,
    "sources": {
      "oas3": {"url": ".../api/docs.json", "openapi": "3.0.0", "info_version": "0.0.1"},
      "elements_catalog": {"url": ".../api/elements"},
      "dev_portal": {"base": "https://developers.sudespacho.net/docs/api-crm/", "linked": true}
    }
  },
  "endpoints": [
    {
      "path": "/api/element_registries/{element}",
      "method": "GET",
      "operation_id": "…",
      "summary": "…",
      "tags": ["ElementRegistries"],
      "auth": "apiKey",                        // del securityScheme del spec
      "parameters": [{"name": "…", "in": "query", "required": true, "type": "string", "description": "…"}],
      "request_schema_ref": "#/components/…",  // o null
      "response_codes": ["200", "500"],
      "dev_doc_url": "https://developers.sudespacho.net/docs/api-crm/get-…"  // opcional
    }
  ],
  "elements": [
    {
      "slug": "extrajudiciales",
      "name_ui": "Expediente extrajudicial",   // si derivable, si no null
      "fields": [
        {"name": "Referencia_Cliente", "type": "string", "label": "Referencia cliente", "source": "view/complete"}
      ],
      "relations": [
        {"element": "clientes_propios", "direction": "right", "source": "view/config"}
      ],
      "enums": {
        "tipo_operaciones_iva": [{"id": "E1", "label": "…"}]
      },
      "probes": {"fields": "view/complete", "relations": "ok", "enums": "ok"}
    }
  ],
  "warnings": ["element 'X': view/config/relations → 404 (relations vacías)"]
}
```

`Endpoint`, `Field`, `Relation`, `EnumValue`, `ElementSchema`, `Atlas` son `@dataclass` en
`core/crm_atlas.py`; `build_atlas` produce el dict serializable y `render_markdown` el `.md`.

## 5. Fases de ejecución

- **Fase A — Atlas de endpoints (pública, cero credenciales).**
  `discover --phase a`. Baja `/api/docs.json`, normaliza los ~466 paths, opcionalmente enlaza
  cada path a su página del portal. Escribe `endpoints[]` + `meta.phase_a_complete=true`.
  **Ejecutable ya en este worktree sin `.env`.**
- **Fase B — Esquema por elemento (autenticada, `x-api-key`).**
  `discover --phase b` (o `all`). Requiere `SUDESPACHO_API_KEY` (y `@token` si algún endpoint
  pide Bearer). Recorre `/api/elements` y, por elemento, descubre campos/relaciones/enums con
  degradación. Escribe `elements[]` + `meta.phase_b_complete=true`.
- El atlas es **incremental**: correr solo A deja un atlas válido (endpoints) con
  `phase_b_complete=false`; correr B después lo completa sin re-hacer A si se usa `--resume`.

## 6. Barandillas duras (higiene de datos y seguridad)

1. **Solo esquema, nunca datos.** El harness **no** llama a `element_registries`/`element_register`
   para leer registros. Solo nombres de campo, config de relación y valores de enum. Esto hace
   seguro mapear incluso `contabilidad`/`personal`/`facturas`: se ven los **nombres** de campo,
   no importes ni PII.
2. **Sin escritura.** El cliente del harness no implementa verbos de mutación. Único efecto
   server-side: el 500 inocuo del probe de propiedad inválida.
3. **Secretos solo por entorno.** `SUDESPACHO_API_KEY`/`@token` vienen de `.env`/`$env:`; nunca
   se escriben al `atlas.json`/`.md` ni al log.
4. **Artefacto commiteable.** `atlas.json`/`.md` contienen solo esquema → pasan `leak-scan`.
   Salvaguarda: un test de higiene comprueba que el atlas no contiene patrones de secreto ni
   claves conocidas antes de permitir el commit.
5. **Deriva detectable.** Re-ejecutar + `git diff` sobre `atlas.json` = qué cambió en el tenant
   (elementos, campos o enums nuevos/retirados) desde la última corrida.

## 7. Robustez operativa

- **Volumen:** ~130–200 elementos × (1 fields + 1 relations + N enums) ≈ 1.000–1.500 GETs.
  Runtime de minutos, no instantáneo.
- **Concurrencia limitada** (p. ej. 8 en vuelo) + **backoff con reintentos** ante 429/5xx
  transitorios. El portal no documenta rate limits, pero se es cortés por diseño.
- **Resumable:** `--resume` relee el `atlas.json` previo y salta los elementos ya resueltos
  (útil si `@token` caduca a mitad de corrida — se renueva y se retoma).
- **Determinismo para diff limpio:** endpoints y elementos se **ordenan** (por path+método /
  por slug) y los campos/enums también, para que el `git diff` refleje cambios reales y no
  reordenamientos. `generated_at` se estampa **fuera** del harness (el orquestador CLI lo
  inyecta) para no ensuciar el diff en corridas sin cambios sustantivos — opción
  `--stamp-time/--no-stamp-time`.

## 8. Artefactos y ubicación

- **Canónico (FeesDefender):**
  - `docs/crm_atlas/atlas.json` — fuente legible por máquina.
  - `docs/CRM_SUDESPACHO_ATLAS.md` — render humano generado.
- **Copia compartida (El Contable):** `--also-elcontable` copia ambos a
  `../ElContable/docs/crm_atlas/` cuando el repo hermano está presente al lado. **El commit
  en El Contable es un PR aparte** en ese repo (branch protection propia); el harness solo
  escribe los ficheros, no commitea cross-repo.
- **Cross-links (sin duplicar contenido):**
  - `docs/INTEGRACION_SUDESPACHO.md` §0 → puntero al atlas como inventario exhaustivo.
  - `docs/ARQUITECTURA_CRM_SUDESPACHO.md` §3/§11 → puntero al atlas.
  - `../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md` §2 → puntero al atlas.
  - `CLAUDE.md` (Referencias rápidas) → entrada del atlas.

## 9. Estratificación con la documentación existente (SSOT)

Regla "un hecho, un hogar" (`docs/GOBERNANZA_FUENTES_VERDAD.md`):

- **Atlas (generado):** hogar de la **verdad cruda mecánica** — *qué existe*: todo endpoint,
  todo campo, toda relación, todo enum. Se regenera; no se edita a mano.
- **`INTEGRACION_SUDESPACHO.md` (a mano):** *qué usamos y cómo* — payloads confirmados,
  gotchas, workarounds, casos reales. **Cita** al atlas, no lo copia.
- **`ARQUITECTURA_CRM_SUDESPACHO.md` (a mano):** modelo conceptual — *qué es el CRM*.
- **Referencia común El Contable (a mano, curada por Cowork):** doctrina agnóstica —
  auth, permisos, presets por rol, enums fiscales con su *por qué*.

El atlas **no sustituye** a ninguno; les quita la carga de ser exhaustivos y les deja el "por qué".

## 10. Tests (TDD)

Los parsers son funciones puras → 100% testeables offline con fixtures; el HTTP se mockea.

- `parse_oas3`: fixture recortado del spec real → assert nº de endpoints, params, auth por op.
- `parse_invalid_property_probe`: fixture del `detail` del 500 (`"...properties are: a,b,c"`)
  → assert lista de nombres.
- `parse_complete_view` / `parse_relations_config` / `parse_enums`: fixtures de payload real.
- `build_atlas` + `render_markdown`: assert shape del JSON y del MD (tablas, orden determinista).
- **Higiene:** test que verifica que un atlas de muestra no contiene patrones de secreto.
- **Degradación:** test de `discover_element` con una sub-llamada que lanza → warning, no aborta.
- Las llamadas en vivo (fetch_*) llevan un test fino con `httpx` mockeado (transport de prueba).

## 11. Correcciones de doc-hygiene derivadas

La guía oficial de autenticación (`developers.sudespacho.net/docs/first-steps/authentication/`,
revisada 2026-07-20) documenta **`x-api-key`** como el header de la API key. Esto **refuta** el
marco de nuestros docs de que "`x-api-key` no está documentado / es un header paralelo empírico"
(`INTEGRACION` §8.1, `ARQUITECTURA` §4.1/§11.1). Al aterrizar el atlas se corrige esa redacción:
`x-api-key` es oficial; lo que confunde es que el **spec OAS3** declara `Authorization: apiKey`
en su `securityScheme` (la guía en prosa y el spec no concuerdan). Cambio menor, doc-only.

## 12. Fuera de alcance (YAGNI)

- **Datos de registros:** jamás. El atlas es esquema.
- **Escritura / cliente de uso general:** ya existen (`core/`, MCP `sudespacho`).
- **Matriz de permisos por elemento (DOM):** la referencia común (§3) la describe vía
  `data-testid` en el front (~198 elementos). Es descubrimiento por **navegador**, no REST →
  extensión futura opcional (`discover --with-permissions` sobre webview), no en esta entrega.
- **Enriquecimiento profundo del portal:** solo se enlaza la URL de operación; no se scrapea
  el cuerpo narrativo.
- **Publicación como skill/plugin "sudespacho-integration"** (idea de la referencia común §8.6):
  posible futuro si el patrón se estabiliza; no ahora.

## 13. Riesgos y verificación en primera corrida

Los riesgos originales (¿existe `view/config/relations`? ¿shape de `/api/elements`? ¿credenciales?)
**quedaron resueltos por la validación en vivo del 2026-07-20** (ver §0.bis). Riesgos residuales:

- **`view/config/{el}/fields` puede no existir para algún elemento** (verificado en `extrajudiciales`,
  no en los 89) → fallback al probe (4b); si ambos fallan, `warnings` + `fields: []`, sin abortar.
- **Enums**: el valor exacto del `type` que marca "select" (¿`Enum`? ¿otro?) se fija en la 1ª corrida
  inspeccionando los tipos reales de los 89 elementos; `select_enum_fields` se calibra con eso.
- **Volumen**: 89 elementos × (1 fields + 1 relations + N enums) ≈ pocos cientos de GETs. Concurrencia
  limitada + backoff (§7).
- **Higiene**: aunque el atlas es solo esquema, los **labels de enum** o **nombres de campo** de
  elementos como `usuarios`/`personal` podrían nombrar personas del despacho (ya documentadas). No es
  PII de tercero, pero el test de higiene (§10) corre igual sobre el atlas final antes del commit.
- Anotar cualquier endpoint que falle en `INTEGRACION`/`DEAD_ENDS` (regla: no marcar dead end sin
  confirmación de Nikolai).

## 14. Plan de entrega por fases

1. **Fase A (pública):** ✅ **HECHA** (commit `87ff113` en rama) — `core.crm_atlas` (fetch/parse OAS3
   + build + render) + `scripts.crm_atlas discover --phase a` + 11 tests offline. Corrida sin
   credenciales → `atlas.json`/`.md` con 548 operaciones / 486 paths / 125 módulos.
2. **Fase B (autenticada):** catálogo de elementos (89) + `discover_element` (4a `fields` primaria /
   4b probe fallback / 5a relations / 5b enums) + `select_enum_fields` + degradación + resume + tests.
   Corrida en vivo con `x-api-key` (ya en el entorno) → completa `elements[]`. **Sin bloqueos** (§0.bis).
3. **Integración doc:** cross-links en los 3 docs + `CLAUDE.md`; corrección de doc-hygiene §11;
   `--also-elcontable` + PR en El Contable.

Cada fase = su propio PR (regla de flujo git: rama + PR, `main` protegida).
