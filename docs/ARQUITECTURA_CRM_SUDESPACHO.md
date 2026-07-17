# Arquitectura CRM sudespacho.net — Referencia FeesDefender

> Documento de conocimiento estructural sobre el CRM sudespacho.net, orientado a la
> integración con FeesDefender. Combina la documentación oficial de
> `developers.sudespacho.net` (capturada 2026-05-06), el spec OAS3 en
> `api-crm-commons-pro.sudespacho.biz/api/docs.json` (466 paths, capturado 2026-05-06)
> y el conocimiento empírico acumulado en `INTEGRACION_SUDESPACHO.md`.
>
> **Este documento responde a "¿qué es el CRM y cómo funciona?"**
> `INTEGRACION_SUDESPACHO.md` responde a "¿qué endpoints usamos y cómo?"

---

## 1. Modelo conceptual del CRM

sudespacho.net es un CRM legal SaaS multi-tenant construido sobre una arquitectura de
**registros tipados** (`element_register`). Todos los objetos del sistema — expedientes,
clientes, colaboradores, documentos, actuaciones — son instancias del mismo tipo
abstracto `ElementRegister`, diferenciadas por el campo `element` (slug del tipo).

### 1.1 Entidades principales (slugs de elemento)

| Slug | Nombre en UI | Serie | Uso en FeesDefender |
|---|---|---|---|
| `extrajudiciales` | Expediente extrajudicial | 42 | Expediente en fase de reclamación previa |
| `expedientes_judiciales` | Expediente judicial | 28 | Expediente en fase procesal |
| `clientes_propios` | Clientes propios | — | EV MMC SPAIN, S.L.U. (ID=2), parte actora |
| `clientes_contrarios` | Clientes contrarios | — | Parte demandada |
| `colaboradores` | Colaboradores | — | Agentes E&V (Marta Reynares y equipo) |
| `procuradores_propios` | Procuradores | — | Procurador asignado al judicial |
| `abogados_propios` | Abogados | — | Nikolai_Tyukhay |
| `gdocu` | Gestor Documental | — | Documentos adjuntos al expediente |
| `actuaciones` | Actuaciones | — | Tareas y eventos procesales |

> **Nota:** `extrajudiciales` y `expedientes_judiciales` son elementos distintos en el
> CRM, no dos estados del mismo expediente. La conversión crea un nuevo registro judicial
> vinculado al extrajudicial original mediante una relación.

### 1.2 Relaciones entre entidades

El CRM usa un modelo de **relaciones dirigidas** entre registros. Cada relación tiene:

- **Dirección**: `left` (el elemento padre apunta al hijo) o `right` (inverso).
- **Cardinalidad**: N:M por defecto (un expediente puede tener múltiples clientes y
  viceversa).
- **Sintaxis en API**: `"{elemento}:{id}:{dirección}"` — p. ej. `"expedientes_judiciales:648:left"`.

Relaciones confirmadas en el tenant `tnm`:

| Entidad A | Entidad B | Dirección desde A | Ejemplo real |
|---|---|---|---|
| `extrajudiciales` | `expedientes_judiciales` | `left` | Extrajudicial 591 → Judicial 648 |
| `extrajudiciales` | `clientes_propios` | `right` | Exp → EV MMC (ID=2) |
| `extrajudiciales` | `colaboradores` | `right` | Exp → Marta Reynares |
| `extrajudiciales` | `clientes_contrarios` | `right` | Exp → parte contraria (confirmado 2026-07-17; antes solo confirmado en judicial — mismo endpoint genérico `relation_element`, ver `INTEGRACION_SUDESPACHO.md` §10.6) |
| `expedientes_judiciales` | `clientes_propios` | `right` | Exp → EV MMC |
| `expedientes_judiciales` | `clientes_contrarios` | `right` | Exp → parte contraria |
| `expedientes_judiciales` | `procuradores_propios` | `right` | Exp → procurador |
| `expedientes_judiciales` | `colaboradores` | `right` | Exp → colaborador |
| `gdocu` | `expedientes_judiciales` | `left` | Documento → Exp judicial |
| `gdocu` | `extrajudiciales` | `left` | Documento → Exp extrajudicial |

### 1.3 Sistema de tags

Los tags en sudespacho son **etiquetas coloreadas vinculadas a grupos de elementos**.
Existen dos grupos distintos: grupo 1 (extrajudicial) y grupo 2 (judicial), con IDs
de tags **completamente distintos**.

**Formato del token legacy:** `#{color_hex}___{tag_id}` (p. ej. `#528800___127`)
**Formato REST:** array de IDs numéricos (`["127", "130"]`)

Categorías semánticas en el tenant `tnm`:

| Color | Hex | Significado | Ejemplos |
|---|---|---|---|
| Verde | `#528800` | Tipo de asunto | BAD DEBT, NEGATIVA ARRAS, LAU 20 |
| Rojo | `#a32929` | Equipo comercial E&V | BaRR3, MaRS6, VaRS1 |
| Lila | `#5229a3` | Valoración de riesgo (defensiva) | RIESGO POSIBLE, RIESGO REMOTO |
| Azul | `#5b9bd1` | Ciudad + probabilidad éxito (actora) | MADRID, POSIBILIDAD EXITO=50% |

### 1.4 Gestor Documental (Gdocu)

Los documentos son registros del tipo `gdocu`, relacionados con expedientes via `left`.
Cada documento tiene:
- `id_carpeta` → categoría/sección del documento (p. ej. "CIVIL", "DEMANDA")
- `nombreoriginal` / `nombrefinal` → nombre del fichero
- `mime`, `tamano` → metadatos del fichero
- `doc` → URL prefirmada S3 (TTL ~5 min)
- `relatedRegisters` → array de relaciones del tipo `"elemento:id:dirección"`

El almacenamiento físico es **Amazon S3** (`api-crm-tmp.s3.eu-west-1.amazonaws.com`).
Las URLs prefirmadas expiran en **600 segundos** para REST, ~5 min para legacy.
También existe almacenamiento **Google Drive** (los archivos de Google Docs/Sheets
generados desde el CRM).

---

## 2. Superficies de integración

### 2.1 API REST oficial (preferida)

**Host:** `https://api-crm-commons-pro.sudespacho.biz`
**Auth:** `x-api-key: <API_KEY>` en header (para la mayoría de endpoints)
**Excepciones auth:**
- `POST /api/element_register/{element}` (crear expediente) usa `Authorization: Bearer <JWT>`
- `GET /api/online/current` solo acepta sesión web (devuelve 404 con API key)

**Formato respuesta:** JSON-LD con envoltura `hydra:member` / `hydra:totalItems` para
colecciones, o objeto plano para ítems individuales.

**Paginación estándar:** `?page=N&itemsPerPage=M` (default 30 items/página)

**Filtrado estándar (`filterGroup`):**
```
filterGroup[condition]=AND
filterGroup[filterGroups][0][filters][0][operator]=associated
filterGroup[filterGroups][0][filters][0][value]={id}
filterGroup[filterGroups][0][filters][0][property]=left.{elemento}.id
```
Operadores disponibles: `equal`, `not-equal`, `associated`, `not-associated`, `like`,
`not-like`, `greater-than-or-equal`, `less-than-or-equal`, `is-empty`, `is-not-empty`,
`in`, `not-in`, `between`.

### 2.2 Frontal heredado (legacy fallback)

**Host:** `https://tnm.sudespacho.net`
**Auth:** tres cookies simultáneas obligatorias desde 2026-05-04:
- `PHPSESSID` — sesión PHP (expira ~24 min por inactividad)
- `@token` — JWT (TTL ~1h); mismo valor que `SUDESPACHO_LEGACY_JWT`
- `@refreshToken` — long-lived, para renovar `@token`
**CSRF:** campo `csrf_token` repetido 3 veces en el body del POST (form-urlencoded)

El frontal heredado todavía es necesario para operaciones de vinculación (`saveselect`)
hasta que se confirme que `PUT /api/relation_element/` las reemplaza.

---

## 3. Catálogo completo de endpoints (oficial + empírico)

### 3.1 ElementRegistries — listado y agregados de cualquier elemento

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| GET | `/api/element_registries/{element}` | x-api-key | Listado filtrable de registros |
| GET | `/api/element_registries/summary/{element}` | x-api-key | Agregado/resumen numérico |
| GET | `/api/element_registries/gdocu` | x-api-key | ⭐ Listado docs de expediente (filtro `associated`) |

`element_registries` es la vía principal de lectura en REST. Devuelve `hydra:member`
con un array de `{id, values: [{property: {name}, value}]}`.

### 3.2 Expedientes — crear, leer, convertir

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| POST | `/api/element_register/extrajudiciales` | Bearer JWT | ⭐ Crear extrajudicial — JSON, HTTP 201 → `{id}` |
| POST | `/api/element_register/expedientes_judiciales` | Bearer JWT | ⭐ Crear judicial — JSON, HTTP 201 → `{id}` |
| GET | `/api/element_register/{element}/{id}` | x-api-key | ⚠️ Bug 500 — no usar hasta corrección |
| POST | `/api/expedient/convert/{id}?type=CONVERT` | **x-api-key** | Convertir extrajudicial → judicial |
| POST | `/api/expedient/convert/{id}?type=DUPLICATE` | **x-api-key** | Duplicar expediente |
| POST | `/extrajudiciales/saveadd/elemento/extrajudiciales` | PHPSESSID+JWT | Legacy fallback crear extrajudicial |
| POST | `/judiciales/saveadd/elemento/expedientes_judiciales` | PHPSESSID+JWT | Legacy fallback crear judicial |

> **⚠️ Auth diferenciada en crear vs convertir:** `POST /api/element_register/` usa JWT
> (`Authorization: Bearer`), mientras que `POST /api/expedient/convert/` usa `x-api-key`.
> Son el mismo token distinto header — no confundir.

### 3.3 Documentos (Gdocu) — listado y descarga

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| GET | `/api/element_registries/gdocu` + filterGroup | x-api-key | ⭐ Listado docs de expediente SIN PHPSESSID |
| GET | `/api/files/presigned_download_url/{doc_id}?relatedElement=...&relatedId=...&direction=left` | x-api-key | ⭐ URL S3 prefirmada (TTL 600s) |
| GET | `/api/documents` | x-api-key | Listado general de documentos con filtros |
| GET | `/api/documents/{id}` | x-api-key | Metadatos de un documento (shape no estándar: `values[]`) |
| GET | `/api/documents/{id}/zip/files` | x-api-key | ZIP de una carpeta Gdocu |
| GET | `/api/documents/presigned_urls/{service}/download/{documentId}` | x-api-key | URL prefirmada — service: `s3`, `aws`, `gdrive` |
| GET | `/api/documents/{id}/downloadUri` | x-api-key | URL de descarga directa |
| GET | `/api/folders/gdocu/{parent}?related_element=...&related_member=...` | x-api-key | Carpetas Gdocu del expediente |
| POST | `/gdocu/list/elemento/gdocu/elemento_relacionado/{element}/miembro_relacionado/{id}/...` | PHPSESSID | Legacy: listado HTML doc IDs |
| POST | `/gestordocumental/predownloadfile/...` | PHPSESSID | Legacy: resolver método de descarga |
| POST | `/gestordocumental/descargaficheros3/id_docu/{id}/...` | PHPSESSID | Legacy: URL S3 prefirmada |

### 3.4 Relaciones entre registros

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| GET | `/api/related_registers?id={register_id}` | x-api-key | ⭐ Relaciones de un registro (plural, empírico) |
| GET | `/api/related_register/{element}/{id}` | x-api-key | Relaciones de un elemento (singular, oficial) |
| POST | `/api/relation_element/{element}/{id}` | Bearer JWT | **⭐ Crear relación REST** (confirmado 2026-05-06 — 201, idempotente, sin PHPSESSID) |
| PUT | `/api/relation_element/{element}/{id}` | Bearer JWT | Actualizar relación existente (primary, relation) |
| POST | `/api/related_registers` | — | ❌ Dead end — devuelve 405 |
| POST | `/{elemento}/saveselect/elemento/{elem}/elemento_relacionado/{elem2}/miembro_relacionado/{id}/...` | PHPSESSID | Legacy: vincular entidad |
| POST | `/views/saveselectrelacion/elemento/juzgados/elemento_relacion/autos/...` | PHPSESSID | Legacy especial: vincular juzgado (usa `saveselectrelacion`) |

> **🔬 Oportunidad prioritaria:** `PUT /api/relation_element/{element}/{id}` con body
> `{"relation": "left.expedientes_judiciales.648"}` podría reemplazar todos los
> `saveselect` del frontal legacy, eliminando la dependencia de PHPSESSID para vínculos.
> **Pendiente validar** con un caso real en el tenant `tnm`.

### 3.5 Tags — crear y gestionar

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| POST | `/api/tags/{element}?field={fieldName}` | x-api-key | **🔬 Crear tag REST** (pendiente validar) |
| POST | `/tagsinput/saveadd/elemento/tags_input/elemento_relacionado/tags/miembro_relacionado/{grupo_id}/...` | PHPSESSID | Legacy: crear tag (confirmado 2026-04-30) |

Body del endpoint REST: `{"label": "NOMBRE TAG", "colour": "#5b9bd1"}`
El `field` en el query param es el nombre del campo de tags del elemento (p. ej. `tags`).

> **🔬 Oportunidad:** Si funciona, reemplaza la creación legacy de tags (actualmente
> único método confirmado). Confirmar con `POST /api/tags/extrajudiciales?field=tags`.

### 3.6 Clientes — búsqueda, creación, conversión

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| GET | `/autocompletar/buscar/elemento/{element}?term={q}&` | PHPSESSID | ⭐ Búsqueda fulltext (legacy) |
| POST | `/api/client/convert/{id}?type=CONVERT` | x-api-key | Convertir prospecto → cliente |
| POST | `/api/client/convert/{id}?type=DUPLICATE` | x-api-key | Duplicar cliente |
| POST | `/views/saveadd/elemento/colaboradores` | PHPSESSID | Legacy: crear colaborador |

### 3.7 Expedient (conversión extrajudicial → judicial)

```
POST /api/expedient/convert/{id}?type=CONVERT
Authorization: x-api-key: <API_KEY>        ← OJO: x-api-key, NO Bearer JWT
Body: {}    (body vacío)
→ HTTP 201, {"id": "N_nuevo_judicial"}
```

Este endpoint crea un nuevo expediente judicial vinculado al extrajudicial `{id}`.
**Aún no validado** en el tenant `tnm` — la conversión podría requerir campos adicionales.

### 3.8 Elementos disponibles (catálogo)

`GET /api/elements` devuelve el catálogo de tipos de elemento disponibles en el tenant:

```json
[{
  "clientes": {"flags": 0, "iteratorClass": "..."},
  "proveedores": {...},
  "ticket": {...},
  "bancos": {...},
  "personal": {...}
}]
```

Útil para discovery — devuelve los slugs activos en el tenant.

### 3.9 Correo (microservicio `nest-mail`) — envío + historial de mail

El envío de email desde el expediente (Historial → Mail) usa el microservicio
`nest-mail-commons-pro.sudespacho.biz` + `api-crm-commons`. Flujo: crear borrador
(`POST nest-mail/api/mail/`) → enviar (`PUT …/api/mail/{id}` con `draft:false`) → registrar como
elemento CRM (`PUT api-crm-commons/api/element_register/mail/{id}`) → relacionar con el expediente
(`POST api-crm-commons/api/relation_element/extrajudiciales/{exp}`) → el email queda en el historial
del expediente (visible al equipo sin ir en copia). **Endpoints y payload completos:
`INTEGRACION_SUDESPACHO.md §10.9`.** ⚠️ Estas XHR del SPA se autentican por **cookie de sesión web**
(no `x-api-key`); `GET /api/accounts/{id}` expone credenciales SMTP/IMAP en claro (higiene: HAR nunca
al repo).

---

## 4. Mapa de autenticación por operación

### 4.1 Clarificación del spec oficial OAS3 (2026-05-06)

**El spec OAS3 declara un ÚNICO esquema de auth:**
```yaml
securitySchemes:
  apiKey:
    type: apiKey
    name: Authorization    # ← header HTTP
    in: header
```
La seguridad global del spec es `[{"apiKey": []}]`. Esto significa que la spec
describe únicamente el header `Authorization`, que se usa tanto para el JWT de sesión
web como (según el spec) para la API key. **`x-api-key` no aparece en ningún lugar
del spec OAS3** — es un header paralelo no documentado que también funciona.

**Modelo auth real (tres tokens distintos):**

| Token | Header HTTP | Valor | Origen |
|---|---|---|---|
| API key | `x-api-key` | `$SUDESPACHO_API_KEY` | Panel CRM → Ajustes → API |
| JWT sesión | `Authorization: Bearer <token>` | `$SUDESPACHO_LEGACY_JWT` (= cookie `@token`) | Login web SPA |
| JWT sesión (alternativo) | `Authorization: <token>` | Mismo JWT sin `Bearer` | Según spec OAS3 |

**Tabla de auth por operación (confirmado empíricamente):**

| Operación | Auth necesaria | PHPSESSID | JWT (Bearer) | x-api-key |
|---|---|---|---|---|
| Listar documentos de expediente | REST | ❌ | ❌ | ✅ |
| Descargar documento (URL S3) | REST | ❌ | ❌ | ✅ |
| Crear expediente extrajudicial/judicial | REST | ❌ | ✅ | ❌ |
| Convertir extrajudicial → judicial | REST | ❌ | ❌ | ✅ (pendiente) |
| Listar expedientes (metadatos) | REST | ❌ | ❌ | ✅ |
| Crear relación vía `relation_element` | REST | ❌ | ✅ | ❌ |
| Crear tag vía `POST /api/tags/` | REST | ❌ | ❌ | ✅ (pendiente) |
| Buscar colaborador (autocomplete) | Legacy | ✅ | ✅ | ❌ |
| Crear colaborador | Legacy | ✅ | ✅ | ❌ |
| Vincular entidades (`saveselect`) | Legacy (fallback) | ✅ | ✅ | ❌ |

**Conclusión:** El objetivo es usar **solo x-api-key** para todas las operaciones
excepto la creación de expedientes (que requiere JWT). La dependencia de PHPSESSID
es el único obstáculo restante para operación 100% REST.

---

## 5. Arquitectura REST: patrón filterGroup

El patrón de filtrado `filterGroup` es la clave para todas las consultas avanzadas.
Estructura anidable con condiciones AND/OR:

```python
# Ejemplo: docs de un expediente judicial
params = {
    "page": 1,
    "itemsPerPage": 25,
    "properties[2]": "nombrefinal",
    "properties[4]": "mime",
    "properties[9]": "tamano",
    "filterGroup[condition]": "AND",
    "filterGroup[filterGroups][0][filters][0][operator]": "associated",
    "filterGroup[filterGroups][0][filters][0][value]": str(expediente_id),
    "filterGroup[filterGroups][0][filters][0][property]": "left.expedientes_judiciales.id",
    "filterGroup[filterGroups][0][condition]": "AND",
    "return_totals": "true",
}
```

El operador `associated` es el que permite filtrar por relación (equivale a un JOIN).
La propiedad `left.{elemento}.id` especifica la dirección de la relación.

---

## 6. Módulos de sudespacho.net documentados oficialmente

El portal `developers.sudespacho.net` documenta ~100 módulos. Los relevantes para
un despacho jurídico con integración FeesDefender:

| Módulo | URL docs | Relevancia |
|---|---|---|
| ElementRegistries | `/docs/api-crm/get-summation-...` | ⭐⭐⭐ Core de todas las lecturas |
| Expedient | `/docs/api-crm/convert-judicial-expedient-item` | ⭐⭐⭐ Conversión ext→jud |
| Documents / Gdocu | `/docs/api-crm/get-list-documents-collection` | ⭐⭐⭐ Descarga de docs |
| PresignedUrl | `/docs/api-crm/get-one-down-presigned-url-item` | ⭐⭐⭐ URL S3 |
| RelatedRegister | `/docs/api-crm/get-related-register-related-register-collection` | ⭐⭐ Vínculos entre exps |
| RelationsElements | `/docs/api-crm/put-relation-element-relations-elements-collection` | ⭐⭐ Crear vínculos REST |
| Tag | `/docs/api-crm/post-tags-tag-collection` | ⭐⭐ Crear tags REST |
| Client | `/docs/api-crm/convert-client-client-collection` | ⭐ Conversión prospects |
| Make | `/docs/api-crm/get-integration-make-integration-dto-collection` | ⭐ Automatización futura |
| Activities | `/docs/api-crm/get-activities-collection` | — Solo lectura, 204 response |

---

## 7. Oportunidades de mejora REST (pendientes de validar)

Estas tres operaciones actualmente requieren PHPSESSID (legacy). La documentación
oficial sugiere alternativas REST que, si funcionan, eliminarían completamente la
dependencia de PHPSESSID:

### 7.1 [ALTA] ✅ Vincular entidades via `relation_element` — CONFIRMADO 2026-05-06

**El endpoint funciona en el tenant `tnm`.** Validado contra los expedientes 591
(extrajudicial) y 648 (judicial). Implementado en `core/sudespacho_relations.py`
como REST-first con fallback legacy.

**POST — crear relación nueva (CONFIRMADO):**
```
POST /api/relation_element/{element}/{id}
Authorization: Bearer <JWT>          ← NO x-api-key; mismo token que create_expediente
Content-Type: application/json

["left.expedientes_judiciales.10", "right.clientes_propios.2"]
```
El body es un **array JSON de strings de relación**. Sintaxis: `"{dirección}.{slug}.{id}"`.
Se pueden enviar múltiples relaciones en una sola llamada. Respuesta: `201 "Created!"`.

**Comportamiento verificado:**
- ✅ Idempotente: relaciones ya existentes devuelven 201 sin crear duplicados
- ✅ Múltiples relaciones en un solo POST: 201 OK
- ⚠️ `exp_id` inexistente → 201 sin error (sin validación de FK server-side)
- ⚠️ Direction inválida → 500 PHP exception (no 400)
- ❌ Array vacío → 404 "It is necessary to include properties"

**Equivalencia confirmada con saveselect legacy:**

| Operación | Endpoint REST (CONFIRMADO) |
|---|---|
| Vincular EV MMC (ID=2) a extrajudicial 600 | `POST /api/relation_element/extrajudiciales/600` body `["right.clientes_propios.2"]` |
| Vincular colaborador (ID=50) a extrajudicial 600 | `POST /api/relation_element/extrajudiciales/600` body `["right.colaboradores.50"]` |
| Vincular EV MMC a judicial 648 | `POST /api/relation_element/expedientes_judiciales/648` body `["right.clientes_propios.2"]` |
| Vincular contrario a judicial 648 | `POST /api/relation_element/expedientes_judiciales/648` body `["right.clientes_contrarios.{id}"]` |
| Vincular procurador a judicial 648 | `POST /api/relation_element/expedientes_judiciales/648` body `["right.procuradores_propios.{id}"]` |

**PUT — actualizar relación existente:**
```
PUT /api/relation_element/{element}/{id}
Authorization: Bearer <JWT>
{"primary": 1, "relation": "left.facturas.2"}
```

**Estado:** Implementado en `sudespacho_relations.py` — `_link_rest()` + `_link_rest_or_legacy()`.
Todos los `link_*()` públicos son ahora REST-first con fallback a saveselect legacy.

### 7.2 [MEDIA] Crear tags via `POST /api/tags/{element}`

```
POST /api/tags/extrajudiciales?field=tags
x-api-key: <API_KEY>
Content-Type: application/json

{"label": "TEST TAG REST", "colour": "#528800"}
```

Si funciona, reemplaza `POST /tagsinput/saveadd/...` del frontal legacy.
Nota: actualmente solo se necesita crear tags cuando un equipo nuevo de E&V
abre oficina. No es una operación frecuente.

### 7.3 [MEDIA] Convertir extrajudicial → judicial via `expedient/convert`

```
POST /api/expedient/convert/{id}?type=CONVERT
x-api-key: <API_KEY>
Body: {}
```

Si funciona, proporciona la ruta canónica para la conversión. Actualmente se crea
el judicial directamente (no se convierte el extrajudicial).

### 7.4 [BAJA] Búsqueda de colaboradores via `element_registries`

```
GET /api/element_registries/colaboradores
    ?filterGroup[filters][0][property]=campo_1080   (email)
    &filterGroup[filters][0][operator]=equal
    &filterGroup[filters][0][value]=marta@engelvoelkers.com
    &properties[]=campo_1080&properties[]=campo_1086
```

Si funciona, reemplaza el autocomplete legacy para búsqueda de colaboradores.

---

## 8. Make / Zapier — automatización externa

El CRM tiene integración nativa con Make (ex Integromat) a través de la API key.
`GET /api/make` devuelve las API keys configuradas para Make.

**Caso de uso futuro:** trigger en Make cuando se crea un expediente en sudespacho
→ notificación a Slack/Teams → inicia pipeline FeesDefender automáticamente.
No priorizado ahora; la integración directa Python es más fiable y controlable.

---

## 9. Discrepancias conocidas entre API oficial y uso empírico

| Situación | API oficial | Empírico (confirmado) | Explicación |
|---|---|---|---|
| Auth crear expediente | No documentada (inferida como x-api-key) | `Authorization: Bearer <JWT>` | El endpoint usa el JWT de sesión web, no la API key |
| Related registers | `GET /api/related_register/{element}/{id}` (singular) | `GET /api/related_registers?id={id}` (plural, query param) | Dos versiones del mismo endpoint; la plural-querystring es la que usamos |
| PresignedUrl path | `/api/documents/presigned_urls/s3/download/{id}` | `/api/files/presigned_download_url/{id}?relatedElement=...` | Dos endpoints distintos — ambos funcionales |
| Auth x-api-key vs Authorization | Docs dicen `Authorization: x-api-key` para `apiKey` scheme | `x-api-key` en header (NO en Authorization) | Bug/confusión en la documentación; `x-api-key` es el header correcto |

---

## 10. Checklist de validación REST (sesiones futuras)

Para llegar a operación 100% REST sin PHPSESSID:

- [x] **Validar `relation_element`** ✅ 2026-05-06 — `POST /api/relation_element/{element}/{id}`
      con `Authorization: Bearer <JWT>` + body array de strings. HTTP 201 confirmado.
      Implementado en `sudespacho_relations.py` como REST-first.
- [ ] **Validar `POST /api/tags/`** — crear un tag de prueba en el grupo extrajudicial.
- [ ] **Validar `expedient/convert`** — convertir un extrajudicial de prueba a judicial.
- [ ] **Explorar `element_registries/colaboradores`** para búsqueda de colaboradores
      sin PHPSESSID.
- [ ] **Explorar creación de colaboradores** — buscar si existe `POST /api/element_register/colaboradores`.

---

---

## 11. Hallazgos del spec OAS3 (2026-05-06)

> Fuente: `GET https://api-crm-commons-pro.sudespacho.biz/api/docs.json`
> 466 paths documentados. Capturado y analizado 2026-05-06.

### 11.1 Autenticación — clarificación definitiva

El spec OAS3 solo declara **un esquema** de auth: `apiKey` en el header `Authorization`.
**`x-api-key` no aparece en ningún lugar del spec.** Es un mecanismo paralelo no
documentado que funciona empíricamente. Implicaciones:

- El spec asume que tanto la API key como el JWT van en el header `Authorization`.
- La distinción `x-api-key` vs `Authorization: Bearer` que usamos es real y funcional
  pero no está en el spec oficial.
- Para crear expedientes (`POST /api/element_register/`), el spec indica `Authorization`
  genérico — que en práctica acepta el JWT (`Bearer <token>`).

### 11.2 `POST /api/relation_element/{element}/{id}` — CREATE relación

**Descubrimiento más importante del spec.** Además del PUT (actualizar), existe POST
para **crear** relaciones nuevas:

```json
// Body: array JSON de strings de relación
["left.expedientes_judiciales.10", "right.gdocu.9"]
```

Sintaxis de cada string: `"{dirección}.{slug_elemento}.{id}"`
Dirección `left` = la entidad referenciada es "padre", `right` = es "hijo".

Respuesta 201 si se crea correctamente. Esto **reemplaza en su totalidad** el mecanismo
`saveselect` del frontal legacy si funciona en el tenant `tnm`.

### 11.3 `GET /api/element_register/{element}/{id}` — properties es REQUIRED

El spec marca `properties` como **required** en el GET de un registro individual.
Esto clarifica el bug 500: el bug NO es que `properties[]` sea inválido, sino que
el servidor requiere el parámetro pero tiene un bug al procesar arrays en PHP
(`Array to string conversion`). El bug está en el backend, no en nuestro uso.

El GET también acepta params opcionales `relatedElement` y `relatedId` — para filtrar
el registro dentro del contexto de una relación específica.

### 11.4 `POST /api/element_register/{element}` — creación con relación

El body del POST incluye `relatedElement` y `relatedId` como campos opcionales:
```json
{
  "nombre": "Manolo",
  "email": "manolo@api.es",
  "relatedElement": "contactos_met",
  "relatedId": "23232"
}
```
Esto permite **crear un registro y vincularlo en un solo call**. Útil para crear
colaboradores directamente con relación al expediente, sin `saveselect` posterior.

### 11.5 Endpoints masivos (`/api/element_register/mass/`)

Existen tres variantes de operaciones masivas:

| Endpoint | Uso |
|---|---|
| `POST /api/element_register/mass/{element}` | Operación masiva genérica |
| `GET /api/element_register/mass/{element}/{ids}` | Operación masiva sobre IDs |
| `POST /api/element_register/bulk-deletion/{element}` | Borrado masivo |

Relevante para sincronización batch de expedientes en el futuro.

### 11.6 Integración Google Drive y Microsoft OneDrive

El CRM tiene integración nativa con ambas plataformas:
- `/api/drive/connect`, `/api/drive/uploadFiles`, `/api/drive/files/{id}/download`
- `/api/entra/connect`, `/api/entra/uploadFiles`, `/api/entra/files/{id}/download`

Estos endpoints permiten subir/descargar documentos directamente desde el CRM hacia
Google Drive o OneDrive. No relevante para FeesDefender ahora (usamos rclone), pero
documentado para el futuro.

### 11.7 Contadores de serie (`/api/general_counters/`)

Endpoints para gestionar la numeración automática de expedientes:
- `GET /api/general_counters/{element}/{seriesId}` — obtener el contador actual
- Permite conocer el siguiente número disponible antes de crear un expediente.

### 11.8 Configuración de vistas y relaciones

`GET /api/view/config/{element}/relations` — devuelve la configuración de relaciones
de un elemento, incluyendo qué elementos puede relacionar y en qué dirección.
Útil para discovery: saber qué relaciones son válidas sin ensayo/error.

### 11.9 Endpoints adicionales relevantes

| Endpoint | Descripción |
|---|---|
| `/api/list/{element}/{field}` | Listado de valores de un campo select/combo |
| `/api/elements/count_related` | Contar registros relacionados |
| `/api/element_registries` | Colección de element_registries sin filtro |
| `/api/registers` | Alias de registros |
| `/api/merge-tags/{element}` | Merge tags entre registros |
| `/api/online/clients` | Clientes conectados en línea |
| `/api/autonumber`, `/api/autonumber/{element}` | Autonumeración |
| `/api/predefined/{element}` | Plantillas predefinidas por elemento |

---

*Fuente: `developers.sudespacho.net` + `api-crm-commons-pro.sudespacho.biz/api/docs.json`
(466 paths, OAS3, capturado 2026-05-06) + conocimiento empírico en `INTEGRACION_SUDESPACHO.md`.
Última actualización: 2026-05-06.*
