# Integración sudespacho.net — Referencia centralizada

> Conocimiento empírico acumulado sobre la API de sudespacho.net.  
> Todo lo aquí documentado ha sido verificado contra el tenant `tnm.sudespacho.net`  
> (commons-pro). Última actualización: 2026-07-12 (§14: enums por API, gramática `filterGroup`, 3ª
> variante `tipo_operaciones_iva`).

---

## 0. Protocolo obligatorio para nuevas integraciones

**Antes de implementar cualquier conexión entre FeesDefender y el CRM, seguir siempre estos dos pasos:**

### 0.1 Leer la spec OAS3

```
https://api-crm-commons-pro.sudespacho.biz/api/docs
```

Referencia oficial de todos los endpoints REST disponibles. Confirmar:
- Si el endpoint `POST /api/element_register/{element}` existe para el slug objetivo.
- Qué esquema de auth usa (Bearer JWT vs x-api-key).
- Qué respuesta devuelve (HTTP 201 + `{"id": N}` o diferente).

⚠️ La spec OAS3 es genérica — los `properties` del body son **ejemplos ilustrativos**, no el schema específico del elemento. Para los nombres exactos de propiedades, usar el paso 0.2.

### 0.2 Capturar un HAR del elemento en el CRM

1. Abrir el CRM en Chrome con sesión activa.
2. DevTools → Network → activar grabación.
3. Crear un registro de prueba del elemento objetivo (colaborador, cliente, etc.) desde la UI del CRM.
4. Filtrar las requests por `api-crm-commons-pro.sudespacho.biz`.
5. Exportar como HAR (`Export HAR...`) y adjuntarlo al chat.

El HAR revela:
- La URL exacta del POST de creación.
- El body JSON con los **nombres reales de las propiedades** (ej. `nif_cif` no `nif`, `telefono1` no `telefono`).
- El esquema de auth real (Bearer JWT en cookie o header).
- Las vistas auxiliares: `GET /api/view/quick_creation/{element}` y `GET /api/view/complete/{element}` que listan todas las propiedades del elemento.

**Después de la prueba:** borrar el registro de prueba del CRM manualmente.

**Ejemplo documentado:** integración de `colaboradores` (2026-05-06, HAR `judicial_648.har`).  
Resultado: `POST /api/element_register/colaboradores` → HTTP 201, Bearer JWT, sin PHPSESSID.  
Properties: `nombre`, `email`, `movil`, `nif_cif`, `telefono1`, `notas`, etc.

---

## 1. Arquitectura de la plataforma

> **Spec OAS3 auditado 2026-05-06:** `https://api-crm-commons-pro.sudespacho.biz/api/docs.json`
> 466 paths. Los hallazgos de esa auditoría están integrados en este documento y en
> `docs/ARQUITECTURA_CRM_SUDESPACHO.md`.

sudespacho.net expone **dos superficies de integración** con comportamientos distintos:

| Superficie | Host | Auth | Uso en FeesDefender |
|---|---|---|---|
| **API REST nueva** | `api-crm-commons-pro.sudespacho.biz` | `x-api-key: <API_KEY>` o `Authorization: Bearer <JWT>` según el endpoint | Healthcheck, metadatos, documentos, **crear expedientes** (desde 2026-05-06) |
| **Frontal heredado** | `tnm.sudespacho.net` | Cookies `PHPSESSID` + `@token` + `@refreshToken` + CSRF token | Vincular relaciones (saveselect), buscar colaboradores, crear colaboradores |

**Desde 2026-05-06**, la creación de expedientes extrajudiciales y judiciales **es completamente operativa vía API REST** (`POST /api/element_register/{element}` con `Authorization: Bearer <JWT>`) sin necesidad de PHPSESSID ni CSRF. FeesDefender implementa estrategia REST-first con fallback al frontal heredado.

**Desde 2026-05-04**, el listado y descarga de documentos (Gestor Documental / Gdocu) también es operativo vía API REST. El frontal heredado solo sigue siendo necesario para operaciones de vinculación (`saveselect`): vincular EV MMC, colaborador, cliente a un expediente.

**⚠️ Cambio auth 2026-05-04:** El servidor requiere tres cookies simultáneas para el frontal heredado: `PHPSESSID` (sesión PHP), `@token` (JWT, TTL ~1h) y `@refreshToken`. Sin las tres, el servidor devuelve la landing page (`E-plan - sudespacho.net`) con HTTP 200.

---

## 2. Autenticación

### 2.1 API REST nueva

```
Header: x-api-key: <SUDESPACHO_API_KEY>
```

**⚠️ El header `Authorization` está reservado al flujo JWT de sesión web del CRM.**  
Usar `Authorization` con la API key devuelve 401 aunque la key sea válida. Confirmado empíricamente el 2026-04-25.

Obtener la API key: `tnm.sudespacho.net → Ajustes → API → Generar clave`.

### 2.2 Frontal heredado

```
Cookie: PHPSESSID=<valor>
Header: X-CSRF-Token: <token de 32 hex chars> (en el body del POST, campo csrf_token)
```

**Obtener PHPSESSID:** Chrome DevTools → Application → Cookies → `tnm.sudespacho.net` → valor de `PHPSESSID`.

**Obtener CSRF token:** aparece en el HTML de cualquier página del CRM como:
```javascript
var csrf_token = '...32 caracteres hex...';
```
El cliente `sync_sudespacho_legacy.py` lo extrae automáticamente del HTML tras login.

**⚠️ La cookie caduca por inactividad.** Si `check_legacy` devuelve "Sesión expirada", renovar manualmente y actualizar `.env`.

### 2.3 Variables de entorno (.env)

```env
# API REST
SUDESPACHO_BASE_URL=https://api-crm-commons-pro.sudespacho.biz
SUDESPACHO_API_KEY=<tu_api_key>
SUDESPACHO_AUTH_HEADER=x-api-key
SUDESPACHO_AUTH_SCHEME=
SUDESPACHO_ELEMENT=expedientes_judiciales
SUDESPACHO_TIMEOUT_S=120

# Frontal heredado — las tres cookies son obligatorias desde 2026-05-04
SUDESPACHO_LEGACY_HOST=tnm.sudespacho.net
SUDESPACHO_LEGACY_PHPSESSID=<valor_copiado_de_devtools>
SUDESPACHO_LEGACY_JWT=<valor_de_@token_copiado_de_devtools>
SUDESPACHO_LEGACY_REFRESH_TOKEN=<valor_de_@refreshToken_copiado_de_devtools>
SUDESPACHO_LEGACY_TIMEOUT_S=120
```

**Cómo obtener las tres cookies** (Chrome DevTools → Application → Cookies → `tnm.sudespacho.net`):
- `PHPSESSID` → variable `SUDESPACHO_LEGACY_PHPSESSID`
- `@token` → variable `SUDESPACHO_LEGACY_JWT`
- `@refreshToken` → variable `SUDESPACHO_LEGACY_REFRESH_TOKEN`

O desde la consola del CRM (abrir DevTools → Console, con sesión activa):
```javascript
document.cookie.split(';').map(c=>c.trim()).filter(c=>c.startsWith('PHPSESSID')||c.startsWith('@'))
```

⚠️ `@token` expira en ~1h. `PHPSESSID` expira por inactividad (~24 min). Renovar ambos cuando `check_legacy` falle.

---

## 3. Endpoints confirmados

### 3.1 API REST nueva (`api-crm-commons-pro.sudespacho.biz`)

| Método | Endpoint | Descripción | Estado |
|---|---|---|---|
| GET | `/api/documents?itemsPerPage=1` | Healthcheck efectivo con API key | ✅ Confirmado |
| GET | `/api/online/current` | Healthcheck nativo (solo sesión web, no API key) | ⚠️ 404 con API key |
| GET | `/api/element_register/{element}/{id}?properties[]=…` | Metadatos del expediente | ⚠️ Bug 500 en backend (properties es required según OAS3, pero el servidor falla al procesar arrays PHP) |
| GET | `/api/documents/{id}` | Metadatos de un documento (id_carpeta, categoria, etc.) | ✅ Confirmado |
| GET | `/api/documents` | Listado con filterGroup | ✅ Confirmado |
| GET | `/api/folders/gdocu/{parent}?related_element=…&related_member=…` | Carpetas Gdocu del expediente | ✅ Confirmado |
| GET | `/api/documents/{folder_id}/zip/files` | Zip de carpeta Gdocu | ✅ Confirmado |
| GET | `/api/documents/{id}/downloadUri` | URL de descarga de un documento | ✅ Confirmado |
| GET | `/api/documents/presigned_urls/s3/download/{documentId}` | URL S3 prefirmada (vía OAS3) | ✅ Confirmado |
| GET | `/api/element_registries/{element}?filterGroup[...]=associated&value={id}&property=left.{element}.id` | Listado de cualquier tipo de elemento filtrado por expediente asociado **SIN PHPSESSID** | ✅ Confirmado 2026-05-04 |
| GET | `/api/element_registries/summary/{element}?filterGroup[...]=...` | Agregado/resumen de un tipo de elemento | ✅ Confirmado 2026-05-04 |
| GET | `/api/files/presigned_download_url/{doc_id}?relatedElement={element}&relatedId={exp_id}&direction=left` | URL S3 prefirmada para descarga **SIN PHPSESSID** | ✅ Confirmado 2026-05-04 |
| GET | `/api/related_registers?id={register_id}` | Relaciones entre registros (extrajudicial↔judicial) | ✅ Confirmado |
| GET | `/api/related_register/{element}/{id}` | Relaciones de un elemento (singular, vía OAS3) | ✅ Documentado OAS3 |
| POST | `/api/element_register/extrajudiciales` | Crear expediente **extrajudicial** — `Authorization: Bearer <JWT>`, JSON plano, HTTP 201 → `{"id": N}` | ✅ Confirmado 2026-05-06 |
| POST | `/api/element_register/expedientes_judiciales` | Crear expediente **judicial** — `Authorization: Bearer <JWT>`, JSON plano, HTTP 201 → `{"id": N}` | ✅ Confirmado 2026-05-06 |
| POST | `/api/expedient/convert/{id}?type=CONVERT` | Convertir extrajudicial → judicial — auth: `x-api-key` | 🔬 Pendiente validar en tenant tnm |
| POST | `/api/relation_element/{element}/{id}` | **Crear relación REST** — body: `["left.X.N","right.Y.M"]` — reemplaza `saveselect` | 🔬 Pendiente validar en tenant tnm |
| POST | `/api/tags/{element}?field=tags` | **Crear tag REST** — body: `{"label":"...", "colour":"#xxx"}` — reemplaza legacy | 🔬 Pendiente validar |
| PUT | `/api/relation_element/{element}/{id}` | Actualizar relación existente — body: `{"primary":1,"relation":"left.X.N"}` | 🔬 Pendiente validar |
| POST | `/api/related_registers` | ❌ 405 — solo acepta GET (ver DEAD_ENDS.md) | ✗ Dead end |

#### Detalle: crear expediente extrajudicial vía REST (confirmado 2026-05-06)

```
POST https://api-crm-commons-pro.sudespacho.biz/api/element_register/extrajudiciales
Authorization: Bearer <SUDESPACHO_LEGACY_JWT>   ← mismo @token del frontal PHP
Content-Type: application/json

{
  "Referencia_Cliente":   "MaRS6 - Gran Vía 1 - (W-001TEST) - Negativa arras",
  "Fecha_alta":           "2026-05-06",
  "Tipo_Asunto":          "Civil",
  "Tipo_Procedimiento":   "reclamacion extrajudicial",
  "cuantia":              10000,
  "costas":               0,
  "intereses":            0,
  "total":                10000.0,
  "Profesional":          "Nikolai_Tyukhay",
  "Notas":                "",
  "tnm_posicionprocesal": "01",
  "tnm_siniestro":        "0",
  "serie_expediente":     "2026",
  "Numero_Expediente":    "0",
  "tags":                 ["130", "127", "286"]
}
→ HTTP 201, {"id": 599, "message": "Created!"}
```

**Notas importantes:**
- El `Authorization: Bearer` usa `SUDESPACHO_LEGACY_JWT` (= cookie `@token`) — **no** la `SUDESPACHO_API_KEY`.
- Los nombres de propiedad son **CamelCase** para extrajudiciales (p.ej. `Referencia_Cliente`, `Fecha_alta`).
- Las tags se envían como **array de IDs numéricos** (`["130", "127"]`), **no** como tokens completos (`"#528800___127"`). Usar `_tags_to_rest()` para la conversión.
- El body vacío `{}` devuelve 404. Un body con propiedades inválidas devuelve 500 con la lista completa de propiedades válidas (útil para discovery).
- `Numero_Expediente: "0"` → el servidor asigna el número definitivo.

#### Detalle: crear expediente judicial vía REST (confirmado 2026-05-06)

```
POST https://api-crm-commons-pro.sudespacho.biz/api/element_register/expedientes_judiciales
Authorization: Bearer <SUDESPACHO_LEGACY_JWT>
Content-Type: application/json

{
  "referencia_cliente":    "MaRS6 - Gran Vía 1 - (W-001TEST) - Negativa arras",
  "fecha_alta":            "2026-05-06",
  "tipo_asunto":           "Civil",
  "tipo_procedimiento":    "procedimiento juicio verbal",
  "cuantia":               10000,
  "costas":                0,
  "intereses":             0,
  "total":                 10000.0,
  "profesional_asignado":  "Nikolai_Tyukhay",
  "notas":                 "",
  "posicion_procesal":     "01",
  "NIG":                   "",
  "referencia_procurador": "",
  "referencia_propia":     "",
  "serie_expediente":      "2026",
  "num_expediente":        "0",
  "tags":                  ["130", "127", "286"]
}
→ HTTP 201, {"id": 700, "message": "Created!"}
```

**Diferencia respecto a extrajudicial:** judicial usa nombres **en minúscula** (`referencia_cliente`, `fecha_alta`) mientras extrajudicial usa **CamelCase** (`Referencia_Cliente`, `Fecha_alta`). Ambos confirmados contra la lista de propiedades devuelta por el servidor ante body inválido (HTTP 500).

**⚠️ `num_expediente` — comportamiento diferente al extrajudicial (confirmado 2026-05-07, fix v2 2026-05-07):**  
El endpoint judicial **NO auto-asigna** `num_expediente` — el campo es de tipo `Autoincremental` pero la asignación la gestiona el cliente (el SPA lo envía explícitamente). A diferencia del extrajudicial (`Numero_Expediente: "0"` → auto-asignado por el servidor).

Fix en `sudespacho_create.py`: `_get_next_num_expediente_judicial(year)` consulta `GET /api/element_registries/expedientes_judiciales` con filtro `serie_expediente=year`, extrae el **máximo** `num_expediente` de los items devueltos y envía `max+1` en el payload. Usar max en lugar de count evita saltar números si hay expedientes con `num_expediente` vacío.

**Bugs de implementación descubiertos el 2026-05-07 via diagnóstico live con apiCrm del SPA:**
- `properties[]` es **requerido** — sin al menos un `properties[N]=campo`, el servidor devuelve HTTP 500 con "properties is required".
- El operador correcto es `"equal"` (no `"eq"` → HTTP 404 con lista de operadores válidos: `equal, not-equal, not-associated, associated, like, not-like, greater-than-or-equal, less-than-or-equal, is-empty, is-not-empty, in, not-in, between`).
- La respuesta de `element_registries/expedientes_judiciales` usa `{"totalItems": N, "items": [...]}` (NO `hydra:totalItems`/`hydra:member` — formato diferente al de `gdocu`).

#### Bug conocido: `element_register` devuelve 500

`GET /api/element_register/expedientes_judiciales/{id}?properties[]=id` → HTTP 500 "Array to string conversion" (el servidor no procesa `properties` como array PHP). **✅ WORKAROUND ENCONTRADO 2026-07-13:** usar la forma **coma** `?properties=id,serie_expediente,...` (string separado por comas, sin `[]`) → **HTTP 200** con el registro (verificado en exp. 672). Ya NO hace falta el frontal heredado para el detalle. *(Descubierto en la sesión de verificación del MCP `sudespacho`; ver `docs/superpowers/specs/2026-07-13-mcp-sudespacho-design.md` §13.)*

#### Detalle: `/api/element_registries/{element}` — listado filtrado por expediente (confirmado 2026-05-04)

```
GET https://api-crm-commons-pro.sudespacho.biz/api/element_registries/gdocu
    ?page=1
    &itemsPerPage=25
    &properties[2]=nombrefinal
    &properties[4]=mime
    &properties[9]=tamano
    &properties[11]=id_carpeta
    &properties[12]=origen
    &properties[13]=origen_id
    &filterGroup[condition]=AND
    &filterGroup[filterGroups][0][filters][0][operator]=associated
    &filterGroup[filterGroups][0][filters][0][value]={expediente_id}
    &filterGroup[filterGroups][0][filters][0][property]=left.expedientes_judiciales.id
    &filterGroup[filterGroups][0][condition]=AND
    &return_totals=true
Header: x-api-key: <API_KEY>
→ HTTP 200, JSON {"hydra:member": [...], "hydra:totalItems": N}
```

El campo `id` del registro devuelto es el `doc_id` que se usa en `presigned_download_url`.

Para listar actuaciones: sustituir `gdocu` por `actuaciones` y ajustar `properties[]`.

#### Detalle: `/api/files/presigned_download_url/{doc_id}` — URL S3 prefirmada (confirmado 2026-05-04)

```
GET https://api-crm-commons-pro.sudespacho.biz/api/files/presigned_download_url/{doc_id}
    ?relatedElement=expedientes_judiciales
    &relatedId={expediente_id}
    &direction=left
Header: x-api-key: <API_KEY>
→ HTTP 200, devuelve URL S3 prefirmada
```

La URL S3 apunta a `api-crm-tmp.s3.eu-west-1.amazonaws.com/{uuid}/{filename}` con TTL de **600 segundos** (`X-Amz-Expires=600`). Resolver y descargar en la misma operación.

Este endpoint es el mismo que usa el CRM para el visor PDF y para el botón "Descargar" del menú `...` de cada documento.

### 3.2 Frontal heredado (`tnm.sudespacho.net`)

| Método | Endpoint | Descripción | Estado |
|---|---|---|---|
| POST | `/gdocu/list/elemento/gdocu/elemento_relacionado/{element}/miembro_relacionado/{id}/direccion_relacionado/der` | Listado de documentos (devuelve HTML) | ✅ Confirmado |
| POST | `/gestordocumental/predownloadfile/elemento_relacionado/{element}/miembro_relacionado/{id}/direccion_relacionado/der` | Resolución método descarga (s3/cloud/s3old) | ✅ Confirmado |
| GET | `/autocompletar/buscar/elemento/{element}?term={q}&` | Búsqueda autocomplete por cualquier elemento CRM | ✅ Confirmado 2026-04-29 |
| POST | `/clientespropios/saveselect/elemento/clientes_propios/elemento_relacionado/extrajudiciales/miembro_relacionado/{exp_id}/direccion_relacionado/der` | Vincular cliente a expediente extrajudicial | ✅ Confirmado 2026-04-29 |
| POST | `/views/saveselect/elemento/colaboradores/elemento_relacionado/extrajudiciales/miembro_relacionado/{exp_id}/direccion_relacionado/der` | Vincular colaborador a expediente extrajudicial | ✅ Confirmado 2026-04-29 |
| POST | `/views/saveadd/elemento/colaboradores` | Crear nuevo colaborador | ✅ Confirmado 2026-04-29 |
| POST | `/gestordocumental/descargaficheros3/id_docu/{doc_id}/elemento_relacionado/{element}/miembro_relacionado/{id}/direccion_relacionado/der` | URL S3 prefirmada del documento | ✅ Confirmado |
| POST | `/extrajudiciales/saveadd/elemento/extrajudiciales` | Crear expediente extrajudicial (legacy fallback) | ✅ Confirmado 2026-04-28 |
| POST | `/judiciales/saveadd/elemento/expedientes_judiciales` | Crear expediente judicial (legacy fallback) | ✅ Confirmado 2026-05-04 |

---

## 4. Modelo de datos

### 4.1 Elementos (tipos de registro)

| Slug | Descripción |
|---|---|
| `expedientes_judiciales` | Expediente judicial (serie 28) |
| `expedientes_extrajudiciales` | Expediente extrajudicial (serie 42) |
| `clientes_propios` | Clientes parte actora |
| `clientes_contrarios` | Clientes parte contraria |
| `procuradores_propios` | Procuradores |
| `abogados_propios` | Abogados |
| `colaboradores` | Colaboradores externos |

### 4.2 Campos de documentos (`DOC_FIELDS` en `sync_sudespacho.py`)

| Campo API | Alias interno | Descripción |
|---|---|---|
| `id` | `id` | ID numérico del documento |
| `nombreoriginal` | `filename` | Nombre original del fichero |
| `nombrefinal` | `filename_final` | Nombre final tras procesado |
| `mime` | `mime` | MIME type |
| `tamano` | `size` | Tamaño en bytes |
| `fechamodificacion` | `modified_at` | Fecha de modificación |
| `fechapublicacion` | `created_at` | Fecha de publicación/creación |
| `categoria` | `category` | Categoría del documento |
| `doc` | `url` | URL prefirmada S3 |
| `id_carpeta` | `id_folder` | ID de la carpeta Gdocu |
| `relatedRegisters` | `related` | Relaciones del documento |
| `tipo` | `type` | Tipo de documento |
| `asunto` | `subject` | Asunto/título |

### 4.3 Propiedades de expediente (`EXPEDIENTE_DEFAULT_PROPERTIES`)

```python
("id", "referencia", "asunto", "estado",
 "cliente", "contraparte",
 "fecha_apertura", "fecha_cierre",
 "importe_reclamado")
```

### 4.4 Relaciones entre expedientes

```
GET /api/related_registers?id={register_id}
```

Devuelve `hydra:Collection` de `RelatedRegisterView`:
- `element`: tipo de entidad relacionada
- `registries`: dict `{id_registro: {...}}` de registros vinculados

**Caso real verificado:**
- Extrajudicial `591` (serie 42, Civil) → Judicial `648` (serie 28, creado 2026-04-13)

### 4.5 Shape de metadatos de documento (API nueva)

La respuesta de `GET /api/documents/{id}` usa un shape **no estándar**:

```json
{
  "id": "40020",
  "isPrimary": false,
  "values": [
    {"property": {"name": "id_carpeta"}, "value": "306", "label": "CIVIL"},
    {"property": {"name": "nombreoriginal"}, "value": "CEDULA DE EMPLAZAMIENTO..."},
    ...
  ]
}
```

El cliente lo aplana a un dict simple para uso interno. Ver `get_document_metadata()` en `sync_sudespacho.py`.

---

## 5. Flujo de descarga de documentos

### 5.1 Flujo REST nuevo — **preferido** (sin PHPSESSID, confirmado 2026-05-04)

```
GET /api/element_registries/gdocu
    ?filterGroup[filterGroups][0][filters][0][operator]=associated
    &filterGroup[filterGroups][0][filters][0][value]={expediente_id}
    &filterGroup[filterGroups][0][filters][0][property]=left.expedientes_judiciales.id
    &properties[2]=nombrefinal&properties[4]=mime&properties[9]=tamano&...
    &return_totals=true
    → JSON {"hydra:member": [{id: 40054, values: [...]}, ...]}
    → extraer doc_id (campo "id") y nombrefinal de cada registro

Para cada doc_id:
    GET /api/files/presigned_download_url/{doc_id}
        ?relatedElement=expedientes_judiciales&relatedId={expediente_id}&direction=left
        → URL S3 prefirmada (TTL 600s)

    GET <S3_URL> (sin auth, presigned)
        → bytes → guardar en disco
```

Este flujo no requiere PHPSESSID. Solo necesita `x-api-key`.  
**Pendiente de implementar en `core/sync_sudespacho.py`** como reemplazo de los métodos legacy.

### 5.2 Flujo legacy — válido pero requiere PHPSESSID + @token

```
sync_sudespacho_legacy.list_doc_ids(expediente_id, element)
    → POST /gdocu/list/... → HTML
    → regex id="fila_gdocu_<doc_id>" → [doc_id, ...]

Para cada doc_id:
    sync_sudespacho.get_document_metadata(doc_id)   [opcional, para carpeta destino]
        → GET /api/documents/{doc_id}
        → id_carpeta_label → slug de carpeta

    sync_sudespacho_legacy.download_document(doc_id, expediente_id, tmp_path)
        → POST /gestordocumental/predownloadfile/... → {resultado, metodo: 's3'|...}
        → POST /gestordocumental/descargaficheros3/... → {resultado, url: '<S3_URL>'}
        → GET <S3_URL> (sin auth, presigned, TTL ~5 min) → bytes
        → Content-Disposition → filename_in_disposition
        → write to tmp_path → rename a {slug}.{ext}
```

---

## 6. Operaciones pendientes de confirmar

### 6.1 Crear expediente extrajudicial — ✅ CONFIRMADO (2026-04-28)

**Endpoint:** `POST https://tnm.sudespacho.net/extrajudiciales/saveadd/elemento/extrajudiciales`  
**Auth:** PHPSESSID (cookie) + `csrf_token` en el body (3 repeticiones, observado en captura)  
**Content-Type:** `application/x-www-form-urlencoded; charset=UTF-8`  
**Surface:** frontal heredado (NO la API REST nueva)

**Campos del formulario confirmados** (campo_XXXX__extrajudiciales):

| ID campo | Valor en test | Significado |
|---|---|---|
| `campo_1740` | `TEST-CAPTURA-FEESDEFENDER` | **referencia_cliente** — identificador cruzado entre sudespacho/Drive/FeesDefender. Formato: `"MaRS2 - Puerto Rico 2, 5º 2 - (W-0470GM) - Negativa arras"`. Coincide con el `case_id`. |
| `campo_1731` | `28-04-2026` | **fecha_apertura** (DD-MM-YYYY) |
| `campo_1730` | `2000` | **importe_reclamado** (entero sin separadores) |
| `campo_1750` | `2.000,00` | importe_reclamado (display ES "N.NNN,NN") |
| `campo_1729` | `0,00` | **costas** (0,00 por defecto; se actualiza al cierre) |
| `campo_1734` | `0,00` | **cuantía** (0,00 por defecto; todos los importes forman la Cuantía) |
| `campo_1748` | `Civil` | materia (select) |
| `campo_1749` | `reclamacion extrajudicial` | subtipo (select) |
| `campo_1747` | `2026` | año (para numeración) |
| `campo_1737` | `49` | **nº expediente extrajudicial** — auto-asignado por el servidor; el valor enviado es el siguiente libre en ese momento. Enviar `0` es seguro. |
| `campo_2487` | `Nikolai_Tyukhay` | responsable (username CRM) |
| `campo_2488[]` | `#528800___214`, `#a32929___135`, `__void__` | tags (formato `#{color}___{id}`, termina en `__void__`) |
| `campo_1735` | `<p>...</p>` | descripción HTML |
| `campo_2586` | `02` | **posición procesal** — `01`=Actor, `02`=Demandado, `03`=Querellante, `04`=Querellado, `05`=Denunciante, `06`=Denunciado, `07`=Resp. Civil Directo, `08`=Resp. Civil Subsidiario. Confirmado 2026-04-28. Ver constantes `POSICION_*` en `sudespacho_create.py`. |
| `campo_2587` | `0` | pendiente identificar (valor fijo) |

**Implementación:** `core/sudespacho_create.py` — función `create_expediente()`.

**Grupos y usuarios** (`permisos_grupos[]` / `permisos_usuarios[]`):

| ID | Tipo | Nombre |
|---|---|---|
| 2 | Grupo | OFICINA_1 |
| 7 | Grupo | DIRECCION+CONTABILIDAD |
| 2 | Usuario | Nikolai_Tyukhay |
| 17 | Usuario | Paola_Barreto |

Formato: claves repetidas en el form-data, una por ID. Mismo mecanismo para cualquier otro elemento del CRM.

**Shape de respuesta** (confirmado con saveedit el 2026-04-28):
```json
{
  "resultado": true,
  "dato": "600",
  "wfcontroller": "extrajudiciales",
  "updated": true,
  "info": "Guardar registro"
}
```
El ID del expediente está en el campo `"dato"`. Para saveadd (creación) el campo contendrá el ID nuevo asignado.

### 6.2 Convertir extrajudicial → judicial

Endpoint documentado: `POST /api/expedient/convert/{id}`  
Pendiente: confirmar payload y respuesta con una conversión real.

---

## 7. Módulos FeesDefender que usan esta integración

| Módulo | Superficie | Función |
|---|---|---|
| `core/sync_sudespacho.py` | API REST nueva | Healthcheck, metadatos docs, descarga zip, listado filterGroup. **Desde 2026-05-04:** `list_gdocu_docs_rest()` + `download_document_rest()` — listado y descarga sin PHPSESSID. `pull_expediente()` usa REST como vía principal; fallback automático a legacy si REST no disponible. |
| `core/sync_sudespacho_legacy.py` | Frontal heredado | **Fallback** listado doc IDs + descarga individual. Requiere PHPSESSID + @token + @refreshToken. Sigue siendo la única superficie para operaciones de escritura (crear expedientes, vincular relaciones, buscar colaboradores). |
| `core/sudespacho_relations.py` | Frontal heredado | Buscar / crear / vincular colaboradores. Toda la lógica de relaciones (extrajudicial + judicial). Requiere PHPSESSID. Sin alternativa REST conocida. |
| `core/sudespacho_create.py` | Frontal heredado | Crear expediente extrajudicial y judicial. Requiere PHPSESSID + CSRF. |
| `scripts/sync_sudespacho.py` | CLI Typer | `check`, `check_legacy`, `pull` |
| `scripts/scheduled_sync.py` | CLI Typer | Pull incremental diario de todos los casos |

---

## 8. Gotchas / cosas no obvias

1. **`x-api-key` no está en el spec OAS3**: El spec oficial OAS3 solo declara el header
   `Authorization` como mecanismo de auth (`apiKey` scheme). `x-api-key` es un header
   paralelo no documentado que funciona empíricamente. En la práctica: usar `x-api-key`
   para operaciones de lectura y admin, `Authorization: Bearer <JWT>` para crear expedientes.

2. **PHPSESSID caduca**: Por inactividad del servidor PHP (~24 min), no por tiempo fijo.
   Si `check_legacy` falla, renovar desde DevTools → Application → Cookies.

3. **`element_register` GET bug 500 — causa confirmada + WORKAROUND**: El spec OAS3 marca
   `properties[]` como **required**. El servidor falla (`Array to string conversion`) al procesar
   el parámetro en forma **array** (`properties[]=`). **Workaround (2026-07-13):** enviar
   `properties=a,b,c` en forma **coma** (string) → HTTP 200. Además, el **listado**
   `element_registries` también exige `properties` (omitirlo → 500).

4. ~~**Listado de documentos no está en la API nueva**~~ **CORREGIDO 2026-05-04**: El listado
   de documentos de un expediente SÍ está disponible vía API REST nueva usando
   `GET /api/element_registries/gdocu` con filtro `associated`. PHPSESSID no necesario.

5. **URL S3 prefirmada expira en ~600s (REST) / ~5 min (legacy)**: Resolver y descargar
   en la misma operación. No cachear la URL.

6. **PowerShell Invoke-WebRequest vs Invoke-RestMethod**: El primero devuelve bytes decimales
   uno por línea. Usar siempre `Invoke-RestMethod` o guardar con `Out-File`.

7. **Mount sync Linux↔Windows**: Archivos escritos por el agente pueden no aparecer
   inmediatamente en el mount Linux de bash. Verificar existencia con `Read` tool (ruta Windows).

8. **`relation_element` POST — body es array de strings**: A diferencia del PUT (body objeto),
   el POST para crear relaciones usa un array JSON:
   `["left.expedientes_judiciales.648", "right.clientes_propios.2"]`
   Cada string tiene el formato `"{dirección}.{elemento}.{id}"`.

9. **`element_register` POST acepta `relatedElement`+`relatedId`**: Se puede crear un registro
   y vincularlo en un solo call, sin necesidad de `saveselect` posterior.

---

## 9. Caso real de referencia

```
Expediente extrajudicial: 591  (serie 42, Civil)
  ↓ relacionado con
Expediente judicial:      648  (serie 28, creado 2026-04-13)
  Cliente: EV MMC SPAIN, S.L.U.
  Case ID local: "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
  Docs descargados: 5 archivos, 5,35 MB
  Carpetas Gdocu: civil/, demanda/
```

---

## 10. Operaciones de relación (confirmadas 2026-04-29)

### 10.1 Constantes del tenant tnm

| Entidad | ID | Notas |
|---|---|---|
| EV MMC SPAIN, S.L.U. | `2` (clientes_propios) | ID 73 = DUPLICADO — nunca usar. Default para honorarios. |
| ENGEL & VÖLKERS SPAIN, S.L.U. | `27` (clientes_propios) | Sociedad matriz. Disponible en el selector "Otros casos" (UI Streamlit, tab Nuevo caso). Confirmado 2026-05-11. |

> **Mapping en código**: `core.config.CLIENTES_PROPIOS_EV` —
> `"EV_MMC_SPAIN" → "2"`, `"ENGEL_VOLKERS_SPAIN" → "27"`. Default para
> honorarios: `CLIENTE_PROPIO_DEFAULT = "EV_MMC_SPAIN"`. Las funciones
> `link_ev_mmc()` y `link_ev_mmc_judicial()` aceptan keyword
> `cliente_propio_id=` para sobreescribir el default — la UI lo cablea
> automáticamente cuando el `tipo_caso` es `OTROS` y el usuario elige
> ENGEL & VÖLKERS SPAIN en el selector "Cliente propio E&V".

> **Tag CRM "OTROS"** (categoría comodín añadida 2026-05-11): cubre casos
> de E&V no relacionados con defensa o reclamación de honorarios. Sin
> tag verde de asunto ni tag de valoración por defecto — `tag_defaults_for_tipo_caso("OTROS")`
> devuelve `[]`. Solo viajan al CRM el tag rojo de equipo, el azul de
> ciudad y el sentinel `__void__`. Si en el futuro se quiere filtrar por
> "OTROS" en el frontal, dar de alta el tag manualmente en sudespacho.net
> (Ajustes → Tags) y añadirlo a `_TIPO_A_TAG_VERDE` / `_TIPO_A_TAG_VERDE_J`.

### 10.2 Autocomplete de búsqueda

```
GET /autocompletar/buscar/elemento/{element}?term={query}&
Auth: PHPSESSID (cookie)
Response: [{"id": 1, "label": "...", "value": "{id}", "data": []}]
```

Elementos confirmados: `extrajudiciales`, `colaboradores`, `clientes_propios`.
La búsqueda es fulltext sobre los campos visibles del listado.
`value` contiene el ID numérico del registro.

### 10.3 Vincular cliente a expediente extrajudicial

```
POST /clientespropios/saveselect/elemento/clientes_propios
     /elemento_relacionado/extrajudiciales
     /miembro_relacionado/{exp_id}
     /direccion_relacionado/der
Content-Type: application/x-www-form-urlencoded
Body: seleccionado[]={client_id}
      &numeroresultados_listado=5
      &documentos_adjuntos_seleccionados=
      &csrf_token={token}
      &cc-num=HubspotCollectedFormsWorkaround
Response: JSON {"resultado": true, "acumulaDatos": {"clientes_propios": ["{client_id}"]}}
```

⚠️ El endpoint es **saveselect** (no `select`) y **sin** `/elemento_relacion/` al final.
El navegador abre un popup con `/addselect/...`; al pulsar "Guardar" el popup llama
`saveselect()` en el padre, que hace el POST a este endpoint.

### 10.4 Vincular colaborador a expediente extrajudicial

```
POST /views/saveselect/elemento/colaboradores
     /elemento_relacionado/extrajudiciales
     /miembro_relacionado/{exp_id}
     /direccion_relacionado/der
Body: seleccionado[]={colab_id}
      &numeroresultados_listado=5
      &documentos_adjuntos_seleccionados=
      &csrf_token={token}
      &cc-num=HubspotCollectedFormsWorkaround
Response: JSON {"resultado": true, "acumulaDatos": {"colaboradores": ["{colab_id}"]}}
```

### 10.5 Crear colaborador

```
POST /views/saveadd/elemento/colaboradores
Body: (form-urlencoded, campos campo_XXXX__colaboradores)
Response: {"resultado": true, "dato": "{colab_id}", "wfcontroller": "colaboradores"}
```

Mapping de campos de colaborador (confirmado 2026-04-29, miembro 776):

| Campo | Significado | Notas |
|---|---|---|
| campo_1086__colaboradores | Nombre completo | Obligatorio |
| campo_1080__colaboradores | Email | Clave de deduplicación |
| campo_1084__colaboradores | Nacionalidad | select; "1" = Sin Asignar |
| campo_1085__colaboradores | NIF/CIF | |
| campo_1083__colaboradores | Móvil | |
| campo_1090__colaboradores | Teléfono 1 | |
| campo_1091__colaboradores | Teléfono 2 | |
| campo_1081__colaboradores | Fax | |
| campo_1092__colaboradores | Teléfono 3 | |
| campo_1094__colaboradores | Web | |
| campo_1079__colaboradores | Dirección | |
| campo_1089__colaboradores | Provincia | select |
| campo_1088__colaboradores | Población | |
| campo_1078__colaboradores | CP | |
| campo_1087__colaboradores | Notas | textarea, HTML |

---

## 12. Expediente judicial — Crear y vincular (confirmado 2026-04-30)

### 12.1 Crear expediente judicial

**Endpoint:** `POST https://tnm.sudespacho.net/expedientesjudiciales/saveadd/elemento/expedientes_judiciales`  
**Auth:** PHPSESSID (cookie) + `csrf_token` en el body (3 repeticiones)  
**Content-Type:** `application/x-www-form-urlencoded; charset=UTF-8`

**Campos del formulario** (campo_XXXX__expedientes_judiciales):

| ID campo | Significado | Notas |
|---|---|---|
| `campo_851` | fecha_alta | DD-MM-YYYY |
| `campo_864` | num_expediente | Enviar "0" (auto-asignado) |
| `campo_875` | serie_expediente | YYYY (select) |
| `campo_860` | NIG | Número de Identificación del Juicio |
| `campo_855` | historico | hidden; "No" por defecto |
| `campo_852` | fecha_alta_hist | Vacío normalmente |
| `campo_868` | referencia_historico | Vacío normalmente |
| `campo_876` | tipo_asunto | select: Civil, Penal, Administrativo, Laboral, Familia |
| `campo_867` | **referencia_cliente** | Identificador cruzado FeesDefender (case_id) |
| `campo_869` | referencia_procurador | |
| `campo_847` | siniestro | hidden; "No" por defecto |
| `campo_878` | tipo_procedimiento | select: "procedimiento juicio verbal", "procedimiento juicio ordinario", etc. |
| `campo_870` | referencia_propia | Referencia interna del despacho |
| `campo_862` | numero_anterior | |
| `campo_2485` | posicion_procesal | select: "01"=Actor, "02"=Demandado, etc. |
| `campo_866` | abogado_principal | select de usernames (ej. "Nikolai_Tyukhay") |
| `campo_849` | cuantia | Número entero |
| `campo_848` | costas | Número entero |
| `campo_856` | intereses | Número entero |
| `campo_879` | total | Formato ES "N.NNN,NN" |
| `campo_2486[]` | tags | Tokens `#{color}___{id}` del grupo judicial; termina en `__void__` |
| `campo_861` | notas | HTML (sin TinyMCE conflicto en POST directo) |

**Shape de respuesta:** idéntico al extrajudicial — `{"resultado": true, "dato": "{id}", ...}`

**Implementación:** `core/sudespacho_create.py` — `create_expediente_judicial()`.

### 12.2 Endpoints de relación judicial (confirmados 2026-04-30, miembro/648)

| Relación | Endpoint POST (saveselect) | Notas |
|---|---|---|
| Cliente propio (EV MMC) | `/clientespropios/saveselect/elemento/clientes_propios/elemento_relacionado/expedientes_judiciales/miembro_relacionado/{id}/direccion_relacionado/der` | Body: `seleccionado[]={id}&numeroresultados_listado=5&...` |
| Cliente contrario | `/clientescontrarios/saveselect/elemento/clientes_contrarios/elemento_relacionado/expedientes_judiciales/miembro_relacionado/{id}/direccion_relacionado/der` | |
| Procurador propio | `/views/saveselect/elemento/procuradores_propios/elemento_relacionado/expedientes_judiciales/miembro_relacionado/{id}/direccion_relacionado/der` | |
| Colaborador | `/views/saveselect/elemento/colaboradores/elemento_relacionado/expedientes_judiciales/miembro_relacionado/{id}/direccion_relacionado/der` | |
| Extrajudicial relacionado | `/extrajudiciales/saveselect/elemento/extrajudiciales/elemento_relacionado/expedientes_judiciales/miembro_relacionado/{id}/direccion_relacionado/der` | |
| Juzgado (especial) | `/views/saveselectrelacion/elemento/juzgados/elemento_relacion/autos/elemento_relacionado/expedientes_judiciales/miembro_relacionado/{id}/direccion_relacionado/der` | Usa `saveselectrelacion`, no `saveselect` |

**Implementación:** `core/sudespacho_relations.py` — `link_ev_mmc_judicial()`, `link_contrario_judicial()`, `link_procurador_judicial()`, `link_colaborador_judicial()`, `ensure_colaborador_vinculado_judicial()`.

### 12.3 Tags del grupo judicial (grupo 2) — distintos del grupo extrajudicial (grupo 1)

⚠️ **Los IDs de tags son completamente distintos entre grupos.** Usar siempre `J_TAG_*` para judiciales.

**78 tags activos capturados 2026-04-30.** Pendiente crear tags de ciudad (Madrid, Barcelona, etc.) que NO existen en el grupo judicial.

**Valoración (lila):**

| Tag | ID judicial | Equivalente extrajudicial |
|---|---|---|
| POSIBILIDAD EXITO = 50% | 259 | 286 |
| POSIBILIDAD EXITO <15% - >50% | 260 | — |
| POSIBILIDAD EXITO < 15% | 261 | — |
| RIESGO REMOTO <15% | 219 | 216 |
| RIESGO POSIBLE <15%-50% | 220 | 217 |
| RIESGO PROBABLE >50% | 221 | 218 |

**Asunto (verde):** BAD DEBT (12), DEVOLUCION RESERVA (24), DEVOLUCION HONORARIOS (55), INCUMPLIMIENTO EXCLUSIVA (62), VUELTA (1), LAU 20 (227), CONSULTORES (210), NEGATIVA ARRAS (180), NEGATIVA ESCRITURA (184), NEGATIVA OFERTA (197), RESPONSABILIDAD PROFESIONAL (19). NEGATIVA CONTRATO ARRENDAMIENTO es **azul** en judicial (ID 283).

**Equipos faltantes en grupo judicial** (existen en extrajudicial, NO en judicial):
BiRS1, BiRS2, SaRS1, SeRS6, SSRR1, SSRS1, VaRS5, BaCS10 (extraj→ID 139), MaRS11, MaRS12, MaRS13.

### 12.4 Crear tags en el grupo judicial

**Endpoint:** `POST /tagsinput/saveadd/elemento/tags_input/elemento_relacionado/tags/miembro_relacionado/2/direccion_relacionado/der`

**Campos:**

| Campo | Descripción |
|---|---|
| `campo_2424__tags_input` | Nombre del tag |
| `campo_2422__tags_input` | Color hex con # (ej. `#5b9bd1`) |
| `permisos_grupos[]` | [2] |
| `permisos_usuarios[]` | [2] |
| `csrf_token` | × 3 |

**Respuesta:** `{"resultado": true, "dato": "{id}", ...}` — el ID del nuevo tag está en `"dato"`.

**Implementación:** `core/sudespacho_relations.py` — `create_tag_judicial()`.

---

## 13. Árbol del gestor documental

> Conocimiento empírico necesario para el refactor intake v2 (`05_CRM/`).
> Fuente única de los mappings: `core/config.py` (`CARPETA_ID_TO_PATH`).
> Última actualización: 2026-05-08.

### 13.1 Por qué esta sección existe

El refactor v2 de `00_Input/` (ver memoria persistente `project_intake_estructura_v2.md`)
deposita cada documento descargado del CRM en la rama exacta del árbol del gestor
documental dentro de `05_CRM/<rama>/`. Para hacerlo, FeesDefender necesita saber a qué
rama (`Civil/1ª Instancia/Declarativo/Demanda`, `General`, `Penal/Apelacion`, etc.)
corresponde cada documento.

El endpoint REST devuelve un identificador de carpeta y un label, pero **no la
jerarquía completa**. Esta sección documenta: (a) qué llega y qué no, (b) el dead
end del endpoint que expondría el árbol, y (c) la estrategia híbrida adoptada en
v1 con sus mappings empíricos.

### 13.2 Lo que sí devuelve el CRM por documento

`GET /api/element_registries/gdocu?...` (ver detalle en sección 3.1) devuelve por
cada documento, dentro de `values[]`:

| Propiedad | Tipo | Ejemplo | Notas |
|---|---|---|---|
| `id_carpeta` | string (entero) | `"307"` | ID numérico de la carpeta del gestor documental |
| `id_carpeta_label` | string | `"DEMANDA"`, `""` | Solo el **nodo hoja**, no la jerarquía. Puede venir vacío. |

La jerarquía completa (`Civil > 1ª Instancia > Declarativo > Demanda`) **no llega**
en la respuesta del endpoint `gdocu`. Lo confirma el probe `scripts/probe_gdocu.py`
ejecutado contra el expediente 657 el 2026-05-08.

### 13.3 Dead end: `/api/folders/gdocu/{parent}` no expone el árbol

El endpoint `GET /api/folders/gdocu/{parent}?related_element=...&related_member=...`
está documentado como ✅ Confirmado en la tabla 3.1, pero la query exploratoria
con `parent=0` (raíz) devuelve `[]` para todos los expedientes del tenant tnm.

- Re-confirmado el 2026-05-08 con `scripts/probe_gdocu_tree.py` contra el
  expediente 657 (judicial con docs en `Civil > 1ª Instancia > Declarativo >
  Demanda` y `General`): 0 carpetas devueltas.
- Detalle completo en `docs/DEAD_ENDS.md` → sección «`/api/folders/gdocu/0?related_element=...`».

**Investigación pendiente (no bloquea el refactor):** capturar HAR del gestor
documental en Chrome o consultar `developers.sudespacho.net` para descubrir la
query correcta (probable parámetro adicional o `parent` distinto de `0`). Si
aparece, sustituir el mapping hardcodeado por auto-construcción dinámica.

### 13.4 Estrategia híbrida `crm_branch_path()` v1

Implementación en `core/case_manager.py` (helper) + `core/config.py` (constantes).
El helper recibe `(case_id, id_carpeta, id_carpeta_label)` y devuelve la `Path`
local relativa dentro de `05_CRM/`. Tres niveles de resolución, en este orden:

1. **Lookup directo en `CARPETA_ID_TO_PATH`** (mapping hardcodeado por ID numérico).
2. **Heurística por `id_carpeta_label`** si el ID no está en el mapping pero el
   label es inequívoco dentro del árbol local v2 (p. ej. label `"DEMANDA"` con
   ambigüedad entre `Civil/1ª Instancia/Declarativo/Demanda`,
   `Civil/1ª Instancia/Monitorio/Demanda`, `Civil/Preliminares/Demanda` y
   `Penal/1ª Instancia/Instruccion/Denuncia` — no se aplica si hay >1 candidato).
3. **Fallback `05_CRM/99_Sin categoria/<expediente_id>/<filename>`** cuando ni el
   ID ni el label resuelven a una rama única. Cada caída en fallback escribe un
   evento `category_unknown` en `_intake_log.jsonl` (M10) con `id_carpeta` +
   `id_carpeta_label` + `expediente_id` para descubrimiento progresivo.

El nombre `99_Sin categoria/` (no `_Sin categoria/`) es deliberado: el filtro de
`core/anon/api.py:330` excluye carpetas con prefijo `_`, y los huérfanos deben
seguir entrando en el pipeline de anonimización. El prefijo `99_` mantiene el
orden visual al final del árbol sin chocar con ese filtro.

**Normalización tolerante:** el helper acepta `id_carpeta` como string o int, y
`id_carpeta_label` con cualquier capitalización / con o sin acentos. Devuelve
siempre la forma canónica tipo oración con separador `/` (p. ej.
`Civil/1ª Instancia/Declarativo/Demanda`), que coincide 1:1 con el filesystem.

### 13.5 Mappings empíricos confirmados

Constante `CARPETA_ID_TO_PATH` en `core/config.py`. El `id_carpeta` es una
taxonomía **global del tenant** (no por-expediente): el mismo ID aparece en
expedientes distintos (307 se observó en 657 y en 444), por lo que un mapping
estático es válido y la etiqueta-hoja (DEMANDA, OPOSICION…) es ambigua entre
ramas — el ID es la única clave fiable.

| `id_carpeta` | Rama canónica en `CRM_TREE` | Bucket (D5) | Origen del mapping |
|---|---|---|---|
| `"1"` | `General` | `99_Otros` | Raíz del gestor documental — escritos genéricos. Confirmado 2026-05-08. |
| `"307"` | `Civil/1ª Instancia/Declarativo/Demanda` | `01_Demanda` | Expediente 657. Doble verificación UI + REST (2026-05-08). |
| `"308"` | `Civil/1ª Instancia/Declarativo/Oposicion` | `02_Contestacion` | Expediente 649 (doc «OPOSICION DEMANDA CALLE ROSER»). ID contiguo a 307. Descubierto vía `category_unknown`; doble verificación UI + REST (2026-06-10). |
| `"380"` | `Civil/Preliminares/Demanda` | `05_Diligencias_Preliminares` | Expediente 444 (doc «D 17 - REQUERIMIENTO PAGO»). NO es 01_Demanda (exclusión Preliminares, D6). Descubierto vía `category_unknown`; verificado en UI (2026-06-10). |

**Nuevos IDs se descubren progresivamente:** cada `id_carpeta` no mapeado cae al
fallback y escribe un evento `category_unknown` en `_intake_log.jsonl`. La
sesión de revisión periódica del log permite añadir el ID al mapping una vez
identificada la rama por el usuario en la UI del CRM (regla de doble
verificación). El endpoint de árbol `/api/folders/gdocu/{parent}` NO devuelve la
jerarquía (dead end, §13.3) ni `/api/documents/{id}` trae `categoria`/parent
para una hoja ambigua, así que la rama de una hoja ambigua **solo** se cierra en
la UI.

### 13.6 Estructura del árbol local — buckets planos (reorg 2026-06-10, D5/D6)

Tras la reorg `[SIGUIENTE-REORG-05CRM]` (PLAN.md), `00_Input/05_CRM/` ya NO
replica el árbol profundo del CRM: es un conjunto de **buckets planos de un
nivel**, creados *lazy* (al escribir el primer documento — D7), no en eager.
El pipeline (extractor → markdown → anon) aplana a un output por documento con
slug stem-only, así que la estructura de `05_CRM/` es solo navegación humana
del input.

```
05_CRM/
├── 01_Demanda/                  ← Declarativo/Demanda (id 307)
├── 02_Contestacion/             ← Declarativo/Oposicion (id 308; un solo bucket aunque haya varios demandados, D5b)
├── 03_Monitorio_Demanda/        ← Monitorio/Demanda
├── 04_Monitorio_Oposicion/      ← Monitorio/Oposicion
├── 05_Diligencias_Preliminares/ ← Preliminares/* (id 380; su "demanda" NUNCA va a 01_Demanda, D6)
├── 99_Otros/                    ← resto plano (General, Documentos, RGPD/LOPD, Apelación, Ejecución, Penal…)
└── 99_Sin categoria/<exp>/      ← fallback cuando id_carpeta no resuelve
```

El routing rama-canónica → bucket vive en la función pura
`core/case_manager._bucket_for` (D6), aplicada dentro de `crm_branch_path` (id
mapping y label heuristic). El árbol canónico de referencia (qué rama existe)
sigue siendo `core/config.CRM_TREE`; `_bucket_for` lo aplana. Capitalización
tipo oración (D3). Mercantil, Concursal, Laboral y Contencioso-administrativo se
tratan procesalmente como Civil. JVB y ETJ no se usan (M8).

Migración de casos heredados (árbol profundo → buckets) **in situ**, sin
re-bajar ni re-OCR: `scripts/migrate_05crm_buckets.py` (D12-D13). El expediente
444 se migró el 2026-06-10 (96 docs; 0 colisiones).

### 13.7 Ámbito y limitaciones de v1

- Solo aplica a casos nuevos (D6). Casos antiguos con estructura v1
  (`sudespacho_<id>/`) están congelados — el detector
  `case_manager.is_legacy_intake_v1` bloquea el pull v2 con un mensaje claro en
  UI. Migración manual: borrar `sudespacho_*/` + `force-pull` v2.
- El mapping crece manualmente por descubrimiento. No hay sincronización
  automática contra el CRM.
- Si el endpoint `/api/folders/gdocu/{parent}` empezara a devolver el árbol con
  alguna query distinta, el migrar a auto-construcción es trivial:
  reescribir `core/case_manager.crm_branch_path` para consultar el árbol al
  inicio de cada pull (cacheado por expediente) y conservar
  `CARPETA_ID_TO_PATH` solo como fallback.

### 13.8 Segunda tanda de la reorg — D9/D10/D11 (2026-06-10)

- **D10 — fecha de modificación del CRM en el listado.** La query
  `list_gdocu_docs_rest` (`sync_sudespacho.py`) ahora pide también
  `properties[12] = "fechamodificacion"`; el DTO `GdocuDocInfo` gana el campo
  `modified_at` (ISO-8601 con offset, p. ej. `2026-06-08T16:21:33.000+02:00`).
  El nombre de propiedad y el formato se confirmaron **en vivo** contra el 444
  (`scripts/probe_gdocu_fecha.py`): el 500 del CRM ante un nombre inválido
  enumera las propiedades válidas (`asunto,carpeta,categoria,…,fechamodificacion,
  fechaenvio,fechaexpiracion,…`). El índice del slot `properties[N]` es solo
  posición de array — el CRM resuelve por el nombre, no por el número.
- **D9 — detector de conjunto** (`core/conjunto_detector.py`). Clúster por
  `modified_at` idéntico (subida en lote) ∩ patrón de prueba `\bD\s*\d+…-`
  (numeración de la actora; el demandado NO numera así — confirmado en el 444).
  Cabecera = el doc del lote **sin** patrón de prueba (*odd-one-out*); en el 444
  es `ORDINARIO - VUELTA VENDEDOR - VALLDAURA.doc` (NO se llama "DEMANDA", así
  que el keyword procesal es solo desempate secundario). Bucket = el de la
  cabecera (`resolve_bucket`) o consenso unánime de los miembros. Baja confianza
  → `pendiente_revision`, sin adivinar. **Solo emite propuestas** (eventos
  `conjunto_detectado` / `pendiente_revision`); la persistencia de la relación
  cabecera↔anexo (`parent_id`) se difiere a `[SIGUIENTE-CATALOGO-DOCUMENTAL]`
  (`indice_documental.yaml` aún no existe — MEJORAS #29). Ejecutable on-demand:
  `scripts/detectar_conjuntos.py --expediente <id>` (dry-run; `--log --case`
  para emitir eventos). NO toca el CRM remoto ni mueve ficheros.
- **D11 — override local `doc_id → bucket`.** El letrado fuerza el bucket de un
  doc mal archivado editando el campo `bucket_override` (mapa `doc_id: bucket`)
  del frontmatter de `00_Input/_caso.md`. `crm_branch_path` lo consulta **antes**
  que la carpeta del CRM (nuevo `kind == "override"`), sin tocar el CRM remoto.
  Solo se honran buckets válidos. El pull (`pull_expediente_v2`) lee el mapa una
  vez por corrida y lo pasa por documento.

---

## 11. Historial de descubrimientos

| Fecha | Descubrimiento |
|---|---|
| 2026-04-25 | Confirmado que `Authorization` rechaza API key; `x-api-key` es el header correcto |
| 2026-04-25 | Bug 500 en `element_register` para cualquier `properties[]` |
| 2026-04-25 | `/api/online/current` devuelve 404 con API key (solo sesión web) |
| 2026-04-26 | Flujo legacy completo decodificado y verificado (list + predownload + S3) |
| 2026-04-26 | Arquitectura multi-expediente implementada: `sudespacho_{id}/` + marcador `.pulled` JSON |
| 2026-04-26 | Pull real expediente 648: 5 docs, 5,35 MB, carpetas civil/ y demanda/ |
| 2026-04-28 | Endpoint `related_registers` documentado y verificado (extrajudicial 591 → judicial 648) |
| 2026-04-28 | Endpoint CREATE extrajudicial confirmado: `POST /extrajudiciales/saveadd/elemento/extrajudiciales` vía frontal legacy, form-urlencoded, campos campo_XXXX |
| 2026-04-28 | Lista completa de 80 tags capturada desde selectize del formulario de alta extrajudicial |
| 2026-04-28 | Corrección: POSIBILIDAD EXITO=50% es azul (#5b9bd1___286), no lila |
| 2026-04-29 | Endpoints de relación confirmados: autocomplete, link cliente, link colaborador, create colaborador |
| 2026-04-29 | EV MMC SPAIN ID=2 confirmado (ID 73 = duplicado — nunca usar) |
| 2026-04-29 | Mapping completo de campos de colaborador (campo_1086..1087) obtenido de miembro 776 |
| 2026-04-28 | Corrección: NEGATIVA CONTRATO ARRENDAMIENTO es rojo (#a32929___155), no verde |
| 2026-04-28 | Confirmados IDs pendientes: CONSULTORES (194), DEVOLUCION HONORARIOS (126), todos los rojos (49 tags) |
| 2026-04-28 | FRANQUICIA: tag no creado aún en el CRM |
| 2026-04-30 | Todos los campo_XXXX del formulario judicial capturados por fetch HTML (sin TinyMCE) |
| 2026-04-30 | 78 tags del grupo judicial (miembro/2) capturados — IDs distintos del grupo extrajudicial |
| 2026-04-30 | Endpoints de relación judicial confirmados desde expediente 648 |
| 2026-04-30 | Endpoint creación de tags judiciales confirmado: POST /tagsinput/saveadd/.../miembro_relacionado/2/... |
| 2026-04-30 | TinyMCE bloquea `computer` y `javascript_tool` en páginas de formulario. Workaround: fetch HTML desde página lista (sin TinyMCE) |
| 2026-05-04 | **Cambio auth frontal heredado**: servidor requiere tres cookies simultáneas `PHPSESSID` + `@token` (JWT, TTL ~1h) + `@refreshToken`. Sin ellas sirve landing page con HTTP 200. Implementado en `SudespachoLegacyConfig.from_env()`. |
| 2026-05-04 | **SPA login NO crea PHPSESSID**: el login en `/tnm` (SPA Vue) solo genera tokens JWT en `localStorage`. La sesión PHP del frontal heredado requiere mecanismo distinto (no automatizable). |
| 2026-05-04 | **`/api/element_registries/gdocu` elimina dependencia de PHPSESSID para docs**: listado de documentos de un expediente ahora completamente operativo vía REST con solo `x-api-key`. Filtro: `associated` + `property=left.expedientes_judiciales.id`. |
| 2026-05-04 | **`/api/files/presigned_download_url/{doc_id}`**: descarga de documento vía REST sin PHPSESSID. TTL URL S3: 600s. Mismo endpoint que usa el CRM para visor y botón "Descargar". |
| 2026-05-04 | Gotcha #4 corregido: `element_registries/gdocu` SÍ lista documentos vía REST. La limitación anterior (`/api/documents?relatedRegisters`) era de ese endpoint concreto. |
| 2026-05-06 | **Auditoría OAS3** (`/api/docs.json`, 466 paths): `POST /api/relation_element/{element}/{id}` con body array de strings reemplaza `saveselect` (pendiente validar). `x-api-key` no está en el spec oficial — solo `Authorization`. Bug 500 en `element_register` GET confirmado: `properties` es required pero el servidor falla con arrays PHP. `element_register` POST acepta `relatedElement`+`relatedId` para crear y vincular en un call. |
| 2026-05-07 | **Fix `num_expediente` judicial v2**: diagnóstico live vía `apiCrm` del SPA reveló 3 bugs en `_get_next_num_expediente_judicial`: (1) `properties[]` requerido (sin él → 500), (2) operador debe ser `equal` no `eq` (→ 404), (3) respuesta usa `items`/`totalItems` (no `hydra:member`/`hydra:totalItems`). Fix aplicado: estrategia max(num_expediente)+1 en lugar de count+1. |

---

## 11. Sistema de etiquetas (tags) en sudespacho

> Fuente: Manual Gestión Interna Despacho, sección "¿Qué ETIQUETAS/TAGS y NOTAS ponemos?"  
> Implementación: `core/sudespacho_create.py` — constantes `TAG_*` y función `tag_defaults_for_tipo_caso()`.

### 11.1 Formato del token

```
#{color_hex}___{tag_id}
```

Ejemplos: `#528800___214`, `#a32929___135`. El **último elemento** de cualquier lista de tags debe ser siempre `__void__` (el builder lo añade automáticamente).

### 11.2 Orden canónico

Por expediente nuevo (Manual):

1. **Equipo / Rojo** — identifica el equipo comercial responsable
2. **Asunto / Verde** — tipo de reclamación
3. **Valoración / Lila** — riesgo (defensiva) o probabilidad de éxito (actora)

El tag **azul** (ciudad) no figura como obligatorio en el Manual. Se añade cuando está disponible.

### 11.3 Tags por categoría

#### Verde `#528800` — Tipo de asunto (11 de FeesDefender, 18 total en CRM)

| Constante Python | Tag CRM | ID | Estado |
|---|---|---|---|
| `TAG_VERDE_BAD_DEBT` | BAD DEBT | 110 | ✅ |
| `TAG_VERDE_NEGATIVA_OFERTA` | NEGATIVA OFERTA | 129 | ✅ |
| `TAG_VERDE_NEGATIVA_ARRAS` | NEGATIVA ARRAS | 127 | ✅ |
| `TAG_VERDE_NEGATIVA_ESCRITURA` | NEGATIVA ESCRITURA | 161 | ✅ |
| `TAG_VERDE_VUELTA` | VUELTA | 95 | ✅ |
| `TAG_VERDE_INCUMPLIMIENTO_EXCLUSIVA` | INCUMPLIMIENTO EXCLUSIVA | 170 | ✅ |
| `TAG_VERDE_RESPONSABILIDAD_PROF` | RESPONSABILIDAD PROFESIONAL | 123 | ✅ |
| `TAG_VERDE_DEVOLUCION_RESERVA` | DEVOLUCIÓN RESERVA | 125 | ✅ |
| `TAG_VERDE_LAU_20` | LAU 20 | 214 | ✅ |
| `TAG_VERDE_DEVOLUCION_HONORARIOS` | DEVOLUCION HONORARIOS | 126 | ✅ |
| `TAG_VERDE_CONSULTORES` | CONSULTORES | 194 | ✅ |
| _(ninguno)_ | NEGATIVA CONTRATO ARRENDAMIENTO | — | ⚠️ Es tag **rojo** (#a32929___155), ver abajo |
| _(ninguno)_ | FRANQUICIA | — | ❌ No creado en CRM (2026-04-28) |

#### Lila `#5229a3` — Valoración de riesgo (SOLO defensiva, 3 tags)

| Constante Python | Tag CRM | ID | Cuándo asignar |
|---|---|---|---|
| `TAG_LILA_RIESGO_POSIBLE` | RIESGO POSIBLE 15-50% | 217 | **DEFAULT** — todos los demás casos |
| `TAG_LILA_RIESGO_REMOTO` | RIESGO REMOTO <15% | 216 | Acuerdo extrajudicial OR >2 años sin actividad |
| `TAG_LILA_RIESGO_PROBABLE` | RIESGO PROBABLE >50% | 218 | Recomendaríamos reclamar si fuéramos el actor |

⚠️ **No hay tags lila para casos actores.** La valoración de éxito actora usa color **azul**.

#### Azul `#5b9bd1` — Ciudad + probabilidad de éxito actora (10 tags)

| Constante Python | Tag CRM | ID | Cuándo usar |
|---|---|---|---|
| `TAG_AZUL_MADRID` | MADRID | 258 | Plaza Madrid |
| `TAG_AZUL_VALENCIA` | VALENCIA | 257 | Plaza Valencia |
| `TAG_AZUL_POSIBILIDAD_50` | POSIBILIDAD EXITO=50% | 286 | **DEFAULT actora** — todos los asuntos nuevos |

⚠️ Bilbao, Sevilla, Santander y San Sebastián **no tienen tag azul de ciudad** en el CRM. Solo sus equipos tienen tags rojos (BiRS*, SeRS*, SaRS*). Los tags de probabilidad <15%→50% y <15% tampoco existen aún.

#### Rojo `#a32929` — Equipos comerciales + tipo especial (49 tags)

Nomenclatura: `{ciudad(2)}{tipo_op(2)}{nº}` — Ba=Barcelona, Ma=Madrid, Bi=Bilbao, Sa=Santander, Se=Sevilla, Va=Valencia · RR=Residential Rentals, RS=Residential Sales, CR=Commercial Rentals, CS=Commercial Sales.

Lista completa confirmada 2026-04-28:

| Ciudad | Tags |
|---|---|
| Barcelona Residential Rentals | BaRR1 (135), BaRR3 (113), BaRR4 (175) |
| Barcelona Residential Sales | BaRS1-12 (156,140,128,163,112/122,97,134,138,137,131,94,162) |
| Barcelona Commercial Rentals | BaCR1 (172), BaCR10 (287) |
| Barcelona Commercial Sales | BaCS1 (136), BaCS10 (139) |
| Bilbao Residential Sales | BiRS1 (273), BiRS2 (268) |
| Madrid Residential Rentals | MaRR1 (119), MaRR2 (118), MaRR3 (225) |
| Madrid Residential Sales | MaRS1-10,13,14 (96,117,115,116,133,130,141,236,120,106,190,189) |
| Santander Residential Sales | SaRS1 (276) |
| Sevilla Residential Sales | SeRS1 (230), SeRS6 (285) |
| Valencia Commercial Rentals | VaCR1 (132) |
| Valencia Residential Rentals | VaRR1 (104) |
| Valencia Residential Sales | VaRS1-5 (99,102,103,114,271) |
| Valencia PD (pendiente confirmar tipo) | VaPD1 (178) |
| **Tipo especial** | `TAG_ROJO_NEGATIVA_CONTRATO_ARR` = **#a32929___155** |

El tag `NEGATIVA CONTRATO ARRENDAMIENTO` (#a32929___155) está categorizado como rojo en el CRM, posiblemente porque lo usa el equipo de alquileres como identificador propio. `tag_defaults_for_tipo_caso("NEGATIVA_CONTRATO_ARRENDAMIENTO")` lo incluye correctamente.

### 11.4 Función `tag_defaults_for_tipo_caso(tipo_caso)`

```python
from core.sudespacho_create import tag_defaults_for_tipo_caso, TAG_ROJO_BaRR1

# Asunto actora: BAD DEBT, equipo BaRR1, Madrid
tags = [TAG_ROJO_BaRR1, TAG_AZUL_MADRID] + tag_defaults_for_tipo_caso("BAD_DEBT")
# → ["#a32929___135", "#5b9bd1___258", "#528800___110", "#5229a3___286"]

# Asunto defensiva: LAU 20 (sin equipo ni ciudad)
tags = tag_defaults_for_tipo_caso("LAU_20")
# → ["#528800___214", "#5229a3___217"]
```

El `TAG_SENTINEL` (`__void__`) se añade automáticamente en `build_form_data()`, no es necesario incluirlo en la lista.

### 11.5 Notas estándar por tipo de caso

El Manual define plantillas de texto para el campo `descripcion_html` del expediente. Las constantes `NOTA_*` en `sudespacho_create.py` contienen el texto base; los campos entre `(...)` y `[...]` se sustituyen con los datos del caso concreto.

### 11.6 Nota sobre discrepancia en default lila para defensiva

El Manual establece `RIESGO_POSIBLE` como el default para todos los asuntos defensiva, con `RIESGO_REMOTO` reservado para situaciones específicas (acuerdo o inactividad prolongada). En sesión de trabajo anterior se indicó verbalmente que el default sería `RIESGO_REMOTO`. **La función `tag_defaults_for_tipo_caso()` sigue el Manual escrito** (`RIESGO_POSIBLE`). Consultar con el despacho si la instrucción verbal prevalece.

---

## 14. Referencia común sudespacho — permisos, enums y patrón genérico de elementos

> **Fuente única de verdad (agnóstica de proyecto):**
> [`../../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md`](../../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md)
> — la redacta Cowork y la comparten El Contable, El Auditor y FeesDefender. Esta sección **fusiona** sus
> §1 (Auth), §2 (API de elementos), §3 (Permisos) y §5 (Enums/trampas) en este documento **sin duplicar**
> lo ya cubierto arriba: para auth y endpoints se cross-referencian las secciones existentes; **permisos y
> enums son contenido nuevo**. Verificado en navegador 2026-06-01/02 (F0), 2026-06-08 (facturación) y
> 2026-07-12 (descubrimiento de enums por API + corrección gramática `filterGroup` + 3ª variante de
> `tipo_operaciones_iva`).

### 14.1 Auth y hosts — *delta* sobre §2

Ya documentado arriba: `x-api-key` vs `Authorization: Bearer <JWT>` (§2.1), PHPSESSID + `@token` +
`@refreshToken` del frontal heredado (§2.2–§2.3), y "escrituras Bearer JWT sin PHPSESSID" (§1). **Añade
la referencia común:**

- **Host de calendario/eventos:** `api-calendar-commons-pro.sudespacho.biz` (distinto del host REST
  `api-crm-commons-pro.sudespacho.biz`).
- En la SPA `https://tnm.sudespacho.net/...` el token JWT vive en `localStorage['token']`.
- Preflight `OPTIONS` antes de cada llamada CORS (normal).

### 14.2 API REST de elementos (genérica) — *formaliza* §3

sudespacho expone casi todo como "elementos" con un patrón uniforme. FeesDefender ya usa partes de esto
(listado `element_registries` con `filterGroup` §3.1/§5.1, bug 500 del singular `element_register` §8.3,
`relation_element` POST como array §8.8). La referencia común lo **consolida**:

| Operación | Endpoint |
|---|---|
| Listar | `GET /api/element_registries/{element}?page&itemsPerPage&sort[..]&properties[..]&filterGroup[..]` |
| Totales | `GET /api/element_registries/summary/{element}?properties[..]&filterGroup[..]` |
| Detalle | `GET /api/element_register/{element}/{id}?properties=a,b,c` (¡singular `element_register`! — ⚠️ bug 500 conocido, ver §8.3) |
| Relacionar | `POST /api/relation_element/{element}/{id}` con body `["left|right.<element>.<id>", ...]` |

- **`properties[]`** hay que pedirlas explícitamente; sin ellas muchas devuelven **500**. Soportan
  relaciones `left.<element>.<campo>` / `right.<element>.<campo>` y agregados `sum(campo)`.
- **`filterGroup` (gramática anidada):**
  `filterGroup[condition]=AND|OR` → `filterGroups[i][condition]` →
  `filterGroups[i][filterGroups][j][filters][k]` con `[operator] [property] [value]`
  (valores `in`/`between` usan `[value][0]`, `[value][1]`). Operadores: `in`, `not-in`, `equal`,
  `between`, `is-empty`, `is-not-empty`, `associated`.
  - **⚠️ Corrección verificada 2026-07-12 (`associated`): la forma que acepta el API tiene 2 niveles,
    no 3.** El front real usa `filterGroup[filterGroups][0][filters][0][...]` (los `filters` cuelgan
    directamente del primer `filterGroups`, sin el `filterGroups[j]` intermedio de la gramática
    genérica de arriba). Con la forma de 3 niveles el API responde «Filter group condition is
    required». **El cliente REST de este repo ya construye la forma correcta de 2 niveles** en todas
    sus consultas (`core/sync_sudespacho.py` `associated`, `core/sudespacho_relations.py`,
    `core/procurador_search.py`, `core/sudespacho_create.py`), y los ejemplos de §3.1/§5.1 también son
    2 niveles — **no hay bug latente en el código actual**. La trampa solo mordería a código nuevo que
    copie literalmente la gramática de 3 niveles.
- **Forma de respuesta (listado):**
  `{ totalItems, currentPage, itemsPerPage, items:[ { id, isPrimary, values:[ {property:{name}, value, label?} ] } ] }`.
- **Relación many-to-many:** desde A, el relacionado es `right.<B>` (o `left.<B>`); se filtra con
  `operator=associated, property=right.<B>.id, value=<id>`. El CRM puede auto-añadir relaciones
  implícitas (p. ej. extrajudicial+cliente); **excluir una = omitirla del array**.

### 14.3 Permisos de usuario — **(nuevo en FeesDefender)**

- **Pantalla:** `https://tnm.sudespacho.net/tnm/settings/users/{id}?tab=permissions`.
- **Modelo:** matriz **elemento × {Ver propio, Ver grupo, Actualizar, Borrar, Crear}**. Cada toggle es un
  `input.el-switch__input` con `data-testid="{elemento}-{Read|ReadGroup|Update|Delete|Create}"` y
  `aria-checked`. ~198 elementos. (`Read`=Ver propio, `ReadGroup`=Ver grupo, `Update`=Actualizar,
  `Delete`=Borrar, `Create`=Crear.)
- **Auditar la matriz (read-only, JS en consola):** recorrer `input.el-switch__input`, leer el
  `data-testid` del ancestro y `aria-checked` → volcar el estado completo o solo lo activado.
- **Datos económicos / personales:** **no** hay toggle por-campo en esta matriz. Leer importes
  (`total`, `duracion`, conceptos, facturas) parece bastar con el `Read` del elemento *(pendiente: test
  definitivo con el token del usuario API)*. "Sin Datos Personales" (F0) se refiere a confidencialidad de
  contactos, no a estas cifras.
- **Tarifa por usuario:** *Configuración personal → "Precio tarifa hora"* (+ "Coste diario bruto").
  Nombre de propiedad API *(pendiente)*.

**Presets de mínimo privilegio por rol** (un usuario API por función, distinto del humano):

| Elemento | El Contable (facturación) | El Auditor | bot.contable (gastos, F0) |
|---|---|---|---|
| `actuaciones` | Read | Read | Read + Create (actuación+evento) |
| `conceptos_honorario` | Read + **Create** | Read | — |
| `conceptos_gasto` / `conceptos_suplido` | — | Read | Read + Create/Update |
| `facturas_proforma` | Read + **Create** | Read | — |
| `facturas` | Read · **Create OFF** 🔒 | Read | — |
| `clientes_propios` · `extrajudiciales` · `expedientes_judiciales` | Read | Read | Read |
| `catalogo_conceptos_honorario` | Read | Read | — |
| `usuarios` | Read (para tarifa) | Read | — |
| documentos / carpetas | — | Read | Read + subir |
| **Borrar (Delete)** | **OFF en todo** | **OFF en todo** | **OFF en todo** |

- **`facturas-Create` siempre OFF** salvo para quien emita facturas reales (hoy: nadie automático):
  cerrojo anti-emisión; aunque el código mandara `invoice_type:"factura"`, el permiso lo impide.
- **El Auditor = solo lectura, sin ningún `Create/Update/Delete`.** La credencial read-only **es** la
  garantía de "detecta y reporta, no corrige".
- **Nunca `Delete`** para usuarios automáticos: los borrados los hace una persona.
- **Licencias (límite 4):** confirmar si un usuario API consume licencia *(pendiente; aparentemente no)*.

### 14.4 Enums y trampas — **(nuevo en FeesDefender)**

- **Descubrir enums por API (verificado 2026-07-12):** `GET /api/view/enums/{elemento}/{propiedad}` →
  `{enums:[{id,label}]}`. Ejemplo: `/api/view/enums/facturas_recibidas/tipo_operaciones_iva`. Evita
  hardcodear listas de valores: se pueden validar/refrescar contra el CRM en tiempo de ejecución. (Uso
  potencial en el cliente REST anotado en `docs/MEJORAS_FUTURAS.md` #52 — sin disparador todavía.)
- `conceptos_honorario_motivo_exencion`: `NULL`="No exenta IVA", `E1..E6`=exenciones
  (art. 20/21/22/24/25/otra). Honorario abogacía → vacío/NULL.
- Otros enums: `conceptos_iva_propio`, `conceptos_irpf_propio`, `facturas_serie_factura`,
  `facturas_estado_cobro`.
- **⚠️ Colisión `tipo_operaciones_iva` — hay TRES listas distintas bajo el mismo nombre de campo:**
  1. `invoices.tipo_operaciones_iva` (facturas **emitidas**): `E*` — p. ej. `E1`="Operaciones
     interiores **SUJETAS** a IVA".
  2. `conceptos_honorario_motivo_exencion`: `E*` — pero `E1`="**EXENTA** art. 20". **Mismo código `E1`,
     sentido OPUESTO al de emitidas. No confundir.**
  3. `facturas_recibidas.tipo_operaciones_iva` (facturas **recibidas**, verificado 2026-07-12): lista
     PROPIA `tipo_operaciones_iva_recibidas` con códigos `R*` (deducibilidad): `R1`=interiores IVA
     deducible · `R1BI`=ídem bienes de inversión · `R2`=compensaciones agrarias · `R3`=adq.
     intracomunitaria de bienes · `R4`=inversión del sujeto pasivo · `R6`=importaciones · `R7`=IVA no
     deducible · `R8`=adq. intracomunitaria de servicios. (Contenido específico de El Contable; aquí
     como aviso de la trampa. Detalle en §4d de la referencia canónica.)
- **Formatos:** `duracion` en **segundos**; importes string con punto decimal; fechas `YYYY-MM-DD`
  (algunas datetime `YYYY-MM-DD HH:MM:SS`).
