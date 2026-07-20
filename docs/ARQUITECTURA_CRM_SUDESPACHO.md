# Arquitectura CRM sudespacho.net — Referencia FeesDefender

> Documento de conocimiento estructural sobre el CRM sudespacho.net, orientado a la
> integración con FeesDefender. Combina la documentación oficial de
> `developers.sudespacho.net`, el spec OAS3 en
> `api-crm-commons-pro.sudespacho.biz/api/docs.json` y el conocimiento empírico acumulado en
> `INTEGRACION_SUDESPACHO.md`.
>
> **Este documento responde a "¿qué es el CRM y cómo funciona?"** (modelo conceptual).
> El **inventario de la superficie** (endpoints + esquema por elemento, generado y re-ejecutable)
> es el atlas `docs/CRM_SUDESPACHO_ATLAS.md`; **"¿qué endpoints usamos y cómo?"**, `INTEGRACION_SUDESPACHO.md`.

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

## 3. Catálogo de endpoints → atlas generado (SSOT)

> **Vaciado 2026-07-20 (Grupo 3.2 del atlas).** El catálogo exhaustivo de endpoints ya no se
> mantiene a mano aquí: se generaba deriva (esta sección llegó a decir ~466 paths; el tenant
> tiene 486). Regla "un hecho, un hogar" (`docs/GOBERNANZA_FUENTES_VERDAD.md`).

El inventario completo y **re-ejecutable** de la superficie REST vive en el atlas
**`docs/CRM_SUDESPACHO_ATLAS.md`** — el **SSOT de "qué existe"**: **548 operaciones · 486 paths ·
125 módulos** (Fase A, del OpenAPI público `/api/docs.json`), más, por cada uno de los 89 elementos
del tenant, sus **campos, relaciones y enums** de tipo `Select` (Fase B). Regenerar y ver la deriva:

```
python -m scripts.crm_atlas discover --phase all
```

**Dónde vive cada cosa:**

- **Qué endpoints / campos / relaciones / enums existen** → el atlas (arriba).
- **Cuáles usamos y con qué payload / auth / dead-ends / bugs** → `INTEGRACION_SUDESPACHO.md`
  (§3.1 endpoints confirmados con payload; §5 descarga de documentos; §8 gotchas —bug 500 de
  `element_register`, `x-api-key` vs `Authorization`, dead-end `POST /api/related_registers` 405—;
  §10 / §12 / §15 operaciones de relación, judicial y actuaciones; §10.9 / §10.10 correo
  `nest-mail` + relate Roundcube).
- **Qué es el CRM y cómo funciona (modelo conceptual)** → el resto de este documento (§1, §2, §4…).

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
del spec OAS3** — es un header paralelo que también funciona.

> **Reconciliación (2026-07-20).** La **guía oficial en prosa**
> (`developers.sudespacho.net/docs/first-steps/authentication/`) **sí documenta `x-api-key`**
> como el header de la API key; el **spec OAS3** (`/api/docs.json`) no — declara `Authorization`.
> Las dos fuentes oficiales **no concuerdan**. Empíricamente manda la guía: enviar la API key por
> `Authorization` devuelve **401**, y el header operativo es **`x-api-key`** (conocimiento
> load-bearing del cliente; no refutar sin confirmación de Nikolai). El atlas lo fija en
> `meta.auth_note` (`docs/CRM_SUDESPACHO_ATLAS.md`).

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

## 6. Módulos de sudespacho.net → índice del atlas

> **Vaciado 2026-07-20 (Grupo 3.2).** La tabla a mano listaba ~10 de los ~100 módulos.

El índice completo por módulo (tag) — **125 módulos** con su número de operaciones y enlace a la
sección correspondiente — es el **"Índice por módulo (tag)"** del atlas
`docs/CRM_SUDESPACHO_ATLAS.md`. Cada operación enlaza además a su doc del portal
`developers.sudespacho.net` cuando existe (campo `dev_doc_url`).

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

## 11. Hallazgos del spec OAS3

> Fuente: `GET https://api-crm-commons-pro.sudespacho.biz/api/docs.json`. El **conteo vivo** de
> paths/operaciones y el desglose por módulo **ya no se fija a mano aquí** (llegó a decir 466;
> el tenant tiene 486) → lo da el atlas `docs/CRM_SUDESPACHO_ATLAS.md`, regenerable. Se conserva
> abajo solo la **clarificación de autenticación** (§11.1), conocimiento load-bearing.

### 11.1 Autenticación — clarificación definitiva

El spec OAS3 solo declara **un esquema** de auth: `apiKey` en el header `Authorization`.
**`x-api-key` no aparece en ningún lugar del spec.** Es un mecanismo paralelo no
documentado que funciona empíricamente. Implicaciones:

- El spec asume que tanto la API key como el JWT van en el header `Authorization`.
- La distinción `x-api-key` vs `Authorization: Bearer` que usamos es real y funcional
  pero no está en el spec oficial.
- **La guía oficial en prosa sí documenta `x-api-key`** (`developers.sudespacho.net/docs/first-steps/authentication/`);
  las dos fuentes oficiales no concuerdan. **Empíricamente manda la guía:** la API key por
  `Authorization` devuelve **401**; el header operativo es `x-api-key` (no refutar sin confirmación
  de Nikolai). El atlas lo registra en `meta.auth_note`.
- Para crear expedientes (`POST /api/element_register/`), el spec indica `Authorization`
  genérico — que en práctica acepta el JWT (`Bearer <token>`).

### 11.2 Resto de hallazgos del spec → atlas

> **Vaciado 2026-07-20 (Grupo 3.2).** Los antiguos §11.2–§11.9 enumeraban a mano endpoints
> concretos del spec (crear relación REST, bug 500 de `element_register`, operaciones masivas,
> integración Drive/OneDrive, contadores de serie, `view/config/relations`, `list`/`autonumber`…).
> Eso es "qué existe" → hoy vive, exhaustivo y regenerable, en el atlas `docs/CRM_SUDESPACHO_ATLAS.md`.
> Lo que **usamos** con payload confirmado (relación REST, bug 500 + workaround coma, etc.) está en
> `INTEGRACION_SUDESPACHO.md` §3.1 / §8 / §10 / §11.

---

*Documento conceptual ("¿qué es el CRM y cómo funciona?"). La superficie REST exhaustiva y
re-ejecutable (endpoints + esquema por elemento) es el atlas `docs/CRM_SUDESPACHO_ATLAS.md`; el
"qué usamos y cómo", `INTEGRACION_SUDESPACHO.md`. Base OAS3: `api-crm-commons-pro.sudespacho.biz/api/docs.json`.
Vaciado de tablas de endpoints → atlas: 2026-07-20 (Grupo 3.2).*
