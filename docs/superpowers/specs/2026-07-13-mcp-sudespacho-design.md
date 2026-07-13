# Diseño — MCP `sudespacho` (CRM del despacho, lectura → escritura por fases)

_Brainstorming Claude Code · FeesDefender · 2026-07-13_
_Origen: `docs/superpowers/handoff-2026-07-13-mcp-sudespacho.md` (brainstorming
previo en Cowork, planificación). Precedente de patrón:
`docs/superpowers/specs/2026-07-08-google-despacho-mcp-design.md`._

## 0. Estado de las decisiones (cerradas en brainstorming)

| Decisión | Resuelto |
|---|---|
| Relación con `core/` | **Standalone** (sin `import core`), patrón de los 4 plugins actuales; anti-drift por **tests de paridad** contra `core` cuando F2 replique lógica de escritura |
| Entrega | **`.dxt` a Cowork por el puente de Claude Desktop** + instalable por cada compañero en su propio Desktop |
| Orden de fases | **F1 lectura → F2 escritura → F3+ (según disparador)** |
| Credenciales | **Modelo B: cuenta personal de cada usuario (Bearer JWT + refresh)**, NO la `x-api-key`. La key es **global/admin** (no ligada a usuario, permisos no modificables, ~100% acceso) → inútil para rol/atribución. El JWT personal SÍ respeta la matriz de rol (oculta contabilidad server-side) Y atribuye los eventos al usuario. Modelo A (key por usuario) **retirado**; Modelo C (central) **descartado** (pierde atribución) |
| `presigned_download_url` | **NO es bloqueo** — la descarga REST ya funciona vía `GET /api/documents/{id}/downloadUri` (RESUELTO 2026-06-10). Se expone en F1 con patrón DL-root (bytes nunca por el modelo) |
| Confidencialidad | **Lista blanca (deny-by-default)**: solo se exponen los elementos del catálogo permitido. **Todo el árbol financiero/contable EXCLUIDO** (Facturas, Contabilidad, Exportación Contable) |
| **Borrado** | **NUNCA, en ninguna fase.** Triple garantía: (1) el plugin no registra tool de borrado; (2) el cliente HTTP no implementa `DELETE`; (3) el rol del usuario tiene `Delete` OFF en todo. Regla dura §5 |
| Diseño de tools | **Genéricas** (`element` como parámetro), no una tool por entidad |
| Descubrimiento | **Introspección (`describe_element`) + playbook + catálogo**; lectura casi automática, escritura mantiene la disciplina HAR |
| Ubicación | `plugins/sudespacho_mcp/` |

**Nota de rumbo (principio transversal, `PLAN.md` 2026-07-13):** este MCP es la capa
**interfaz distribuible** sobre el **motor determinista** (`core/`). El motor sigue
siendo el hogar de lo forense/irreversible; el plugin lo *dispara* o consulta, no lo
reimplementa. Este es además el **primer producto rápido escalable a los compañeros**
(Ana, Sergio, Paola) porque la API REST del CRM ya es *nube* (no depende de `G:`).

## 1. Propósito y alcance

Dar acceso directo al CRM del despacho (sudespacho, tenant `tnm`) **desde el chat**
(Cowork/Claude Desktop/móvil), sin pasar por la app Streamlit ni por el PC de
desarrollo. Mono-tenant, sin multicuenta.

**F1 (esta entrega) = LECTURA pura.** Consultar expedientes, documentos, y el catálogo
de entidades del CRM (clientes, contrarios, abogados, procuradores, colaboradores,
organismos, contactos, juzgados, poderes, actuaciones, notas técnicas, tareas, agenda…),
más descarga de documentos. La escritura (alta de expediente, vinculación, tags) es
**F2**, con su propio spec/plan.

**Consolidación de superficies del CRM:** el MCP convive con `core/` (Streamlit/CLI
siguen operando el CRM en local). No se jubila nada. El objetivo del MCP es el alcance
*chat/nube/compañeros*, no sustituir el camino local.

## 2. Topología y estructura

Servidor **stdio local FastMCP**, calcado del molde de `plugins/google_despacho_mcp/`
y del `Gmail MCP Desktop`. Empaquetado `.dxt` + entrada en `claude_desktop_config.json`;
llega a Cowork/claude.ai por el **puente de Claude Desktop** (mismo requisito operativo
que Gmail/google-despacho: PC encendido + app de escritorio + puente — salvo en el
Modelo C, ver §3).

Separación lógica-pura / wrapper (patrón `plugins/expedientes_xl/` y
`email_export_mcp/build_server`):

```
plugins/sudespacho_mcp/
    __init__.py
    sudespacho_client.py   # cliente REST puro (x-api-key); httpx inyectable para tests
    catalog.py             # catálogo de elementos permitidos (lista blanca) + slugs vetados
    discovery.py           # introspección: describe_element() → borrador de ficha
    server.py              # registro de tools FastMCP; resuelve credencial y delega
    sudespacho_cli.py      # alta/prueba de la clave del usuario (interactivo, local)
    run_server.bat         # wrapper de arranque (patrón expedientes_mcp/google_despacho)
    dxt-build/manifest.json
    README.md
    requirements.txt
```

**Principio de aislamiento:** `sudespacho_client.py` no conoce `mcp` ni el transporte;
recibe un cliente httpx (o base_url+key) ya construido → testeable con fake sin API viva.
`server.py` es wrapper fino: resuelve la credencial, aplica la **lista blanca** (§5) y
delega. **Sin `import core`** (standalone); las convenciones compartidas con `core`
(regex de W-code, schema de eventos si F2 los emite, ids del tenant) se anclan por
**tests de paridad** (patrón §14.6 de google-despacho), no por copia a fe.

Credenciales y config **fuera del repo** (env / `~/.sudespacho-despacho/`, gitignored),
override por `SUDESPACHO_DESPACHO_HOME`. Tests en `tests/`.

## 3. Autenticación / credenciales (Modelo B — cuenta personal de cada usuario)

**Superficie REST:** `https://api-crm-commons-pro.sudespacho.biz`. La API acepta dos
credenciales: **`x-api-key`** (estática) y **`Bearer JWT`** (token de sesión de un usuario).

**Hallazgo que fija el modelo (2026-07-13):** la **`x-api-key` de sudespacho es GLOBAL** —
**no** ligada a un usuario ni a sus credenciales, con **permisos no modificables y amplios
(~100% de cualquier acción contra el CRM)**. Por tanto:
- **La `x-api-key` NO sirve para el plugin de compañeros:** repartirla les daría acceso total
  (contabilidad incluida) y **sin atribución** (credencial anónima). Contradice los dos
  requisitos (confidencialidad por rol + traza por usuario).
- La `x-api-key` se **reserva al contexto admin de Nikolai** (Streamlit/CLI de `core`), nunca
  al MCP distribuido.

**Modelo B — el MCP se conecta con la CUENTA PERSONAL de cada usuario (Bearer JWT):**
- Cada compañero se autentica con **su propio login del CRM** → el MCP obtiene su
  **`Bearer JWT` + refresh token** y opera la API REST con ese JWT.
- **Rol respetado (confidencialidad):** a diferencia de la key, un **usuario personal SÍ
  tiene matriz de permisos modificable** (`REFERENCIA_SUDESPACHO_API_PERMISOS.md` §3, ~198
  elementos, `settings/users/{id}?tab=permissions`). Apagando el `Read` de los elementos
  financieros en el rol "abogado", **el CRM se los niega server-side**. La lista blanca del
  plugin (§5) es **segunda barrera** (defensa en profundidad).
- **Atribución (traza):** las acciones viajan con el JWT del usuario → el CRM registra
  `created_by`/`modified_by` **bajo esa persona**. Nikolai puede seguir quién hizo qué. (Es
  la razón por la que El Contable eligió credenciales por-usuario: "atribución limpia".)
- **Contraseñas:** el usuario introduce **su propia** contraseña en el login del plugin
  (como en cualquier app); el plugin guarda **solo los tokens** (`~/.sudespacho-despacho/`,
  gitignored), **nunca la contraseña**, nunca el token en el repo ni en el chat
  (`docs/SEGURIDAD_DATOS.md`). *(El asistente Claude no introduce contraseñas de terceros.)*
- **Refresco:** el JWT caduca; se renueva con el refresh token. `core.sync_sudespacho_legacy`
  ya implementa este baile (`try_auto_refresh_jwt` / `_try_refresh_jwt_post`); standalone se
  **porta** esa lógica (trabajo acotado). Precisar si el REST con Bearer JWT necesita además
  PHPSESSID o basta el JWT+refresh (gate).

**Modelo C — DESCARTADO** (no solo despriorizado): motor central con la key global. Perdería
la **atribución por usuario** (todo bajo una credencial anónima) y expondría acceso total.
Incompatible con los requisitos.

**Gate de verificación:**
1. **Mecanismo de auth — ✅ VERIFICADO EN VIVO (2026-07-13, usuario admin de Nikolai):**
   - `GET /api/element_registries/clientes_propios?page&itemsPerPage&properties[i]&return_totals=false`
     → **200**. Patrón `element_registries` genérico confirmado (forma `properties[i]` array).
   - JWT en `localStorage['token']` con claims `iat, exp, roles, username, authorization` →
     **user-bound (`username` = atribución) y role-bearing (`roles`)**.
   - **Vida del JWT = 60 min** + `localStorage['refresh_token']` → refresco horario.
   - **Sin cookie PHPSESSID**; API cross-origin → auth **solo por `Bearer JWT`** (no PHPSESSID
     para el REST). El frontal legacy NO es necesario para autenticar.
   - (El JWT es secreto: verificado sin volcarlo al chat ni al repo.)
2. **Atribución en escritura — PENDIENTE (F2):** crear un `TEST - BORRAR` y confirmar
   `created_by` = ese usuario; Nikolai lo borra (el plugin nunca borra).
3. **Rol que oculta la contabilidad — PENDIENTE:** necesita un **usuario de rol abogado**
   (Nikolai es admin y lo ve todo); su JWT debe recibir **403/lista vacía** en un elemento
   financiero. Endpoints de login/refresh: capturarlos (o reusar `core.sync_sudespacho_legacy`).

**🚩 RIESGO — tope de licencia (4 concurrentes):** el contrato limita a **4 usuarios
concurrentes** (verificado 2026-07-13: entrar obligó a expulsar al 4º, el usuario de soporte
de sudespacho). Si cada sesión JWT del MCP **consume una licencia**, entonces Nikolai + 3
compañeros = 4 → sin margen. **Bloqueante potencial del escalado a todos los compañeros a la
vez.** A confirmar: (a) ¿una sesión JWT del MCP cuenta como licencia concurrente?; (b) ¿un
mismo usuario en web + MCP cuenta una o dos?; (c) mitigaciones — reusar el token de la sesión
web existente en vez de abrir otra, ampliar licencias, o limitar concurrencia. Enlaza con el
fleco de El Contable ("límite 4; confirmar si un usuario API consume licencia").

**Prerrequisito de despliegue:** cada compañero debe tener **cuenta propia en el CRM** con
rol abogado (sin `Read` en la contabilidad). Si no la tiene, crearla/configurar su matriz es
parte del alta. *(Pendiente de Nikolai: ¿Ana/Sergio/Paola ya tienen usuario CRM?)*

**Frontal legacy PHP** (`tnm.sudespacho.net`, PHPSESSID): solo si una lectura de F1 la REST
no la cubre (p. ej. detalle completo de expediente por el bug 500, §4/§6). Nota: el login
personal y su JWT/refresh son de la misma familia que este frontal — el gate aclara qué
piezas hacen falta para el REST.

## 4. Tools por fase

Todas las de lectura pasan por la **lista blanca** (§5): un `element` fuera del catálogo
permitido se rechaza con error claro, aunque la clave pudiera verlo.

### F1 — Lectura (esta entrega)

**Consulta genérica de elementos** (sobre `GET /api/element_registries/{element}`,
confirmado sin PHPSESSID 2026-05-04; respuesta `{totalItems, items}`, NO formato hydra):

| Tool | Endpoint / nota |
|---|---|
| `list_element_types()` | Devuelve el catálogo de slugs **permitidos** (la lista blanca), para que el modelo elija sin inventar |
| `list_elements(element, filtros?, page?)` | `GET /api/element_registries/{element}` — listado paginado |
| `search_elements(element, term)` | `GET /autocompletar/buscar/elemento/{element}?term=` — búsqueda autocomplete |
| `get_element_summary(element, filtros?)` | `GET /api/element_registries/summary/{element}` — agregado |
| `list_elements_por_expediente(element, exp_id, direccion='left')` | filtro `filterGroup[...]=associated&value={id}&property=left.{element}.id` — cualquier entidad asociada a un expediente |

**Expedientes y documentos** (envuelven lo ya confirmado en `core`):

| Tool | Endpoint / nota |
|---|---|
| `list_expedientes(referencia? \| texto?)` | búsqueda por referencia/texto (patrón `element_registries` + filtro `like`, operador **`equal`** no `eq`) |
| `get_expediente(exp_id, element)` | metadatos; el singular REST `element_register/{id}?properties[]=` da **500** con la forma **array**. **Hipótesis a probar (dato de El Contable):** la forma **coma** `?properties=a,b,c` esquiva el bug → si funciona, no hace falta el frontal legacy para el detalle |
| `list_documentos(exp_id, element)` | `GET /api/element_registries/gdocu?relatedElement=&relatedId=&direction=left` |
| `get_document_download_url(doc_id, exp_id, element)` | `GET /api/documents/{id}/downloadUri` → `presignedDownloadUrl` (§7) |
| `download_document(doc_id, exp_id, element, dest?)` | descarga a **DL-root** local + `sha256`; **nunca** bytes/base64 por el modelo (§7) |

**Introspección / descubrimiento** (§6):

| Tool | Nota |
|---|---|
| `describe_element(element)` | pregunta al CRM las propiedades reales del elemento (`/api/view/complete/{element}` + claves de una muestra de `element_registries`) → **borrador de ficha de catálogo** (slug + propiedades + muestra) para revisar y pegar |

### F2 — Escritura (spec/plan aparte)
`create_expediente` (extra/judicial), `create_colaborador`, `link_*` (vincular partes),
`create_tag`. Aquí es donde vive la lógica cara (autoincremento `max()+1` de
`num_expediente`, tokens de tag, form-data). Standalone → se **replica con tests de
paridad** contra `core`, y **cada endpoint de escritura mantiene la disciplina HAR**
(los nombres de propiedad importan; un error da 500).

### F3+ — Según disparador
Agenda/calendario del CRM en **escritura** (crear citas/tareas); frontal legacy si algo
lo exige; lote. **Regla de promoción del proyecto:** solo por disparador concreto.

## 5. Seguridad y confidencialidad

**Lista blanca (deny-by-default) — control principal del plugin.** El lector es genérico
(acepta cualquier slug), así que la protección **no** puede ser una lista negra (se olvida
un slug y filtra). El plugin **solo expone los elementos del catálogo permitido**
(`catalog.py`); cualquier otro `element` se rechaza con error claro, **aunque la clave
pudiera verlo**. La pertenencia al catálogo es dato revisado a mano, no descubierto en
automático (la introspección propone, un humano aprueba antes de añadir a la lista blanca).

**Árbol financiero/contable — EXCLUIDO explícitamente** (documentado en `catalog.py` como
`_VETADOS = "confidencial — nunca exponer"`, para que nadie lo añada por reflejo):
- **Facturas:** facturas, facturas proforma, remesas, facturas recibidas, cobros clientes,
  pagos proveedores, catálogo conceptos honorario, conceptos honorario, conceptos gasto,
  conceptos suplido, conceptos provisión, libros oficiales.
- **Contabilidad:** nóminas, amortizaciones.
- **Exportación Contable:** cuentas contables.
- **Slugs confirmados (de El Contable)** a vetar explícitamente: `conceptos_honorario`,
  `conceptos_gasto`, `conceptos_suplido`, `conceptos_provision`, `conceptos_varios`,
  `conceptos_recibidas*`, `catalogo_conceptos_*`, `facturas`, `facturas_proforma` (+ el
  endpoint `POST /api/invoices`). El resto (remesas, facturas recibidas, cobros clientes,
  pagos proveedores, libros oficiales, nóminas, amortizaciones, cuentas contables) se
  confirman por slug conforme se capturen; **el deny-by-default los cubre igual** mientras
  tanto — doble negativa (vetados por slug Y fuera de la lista blanca).

**El CRM como portero fuerte (Modelo A).** La lista blanca protege *a través de las tools*.
No impide que quien tenga la clave en la mano llame a la API directamente. Por eso la
confidencialidad real se apoya en que **cada compañero use su clave de rol acotado**, que
el CRM niega server-side. Dos barreras: rol del CRM (fuerte) + lista blanca (defensa en
profundidad). **Nunca** repartir la clave de administrador con el plugin.

**Borrado — NUNCA, regla dura (en ninguna fase, ni F1 ni F2+).** Triple garantía en capas:
1. **Tools:** el plugin no registra ninguna tool de borrado; sin `delete_*`, sin flag
   `permanent`. No hay superficie de borrado que el modelo pueda invocar.
2. **Cliente HTTP:** `sudespacho_client.py` no implementa el verbo `DELETE` (calcado del
   transporte de El Contable, que deliberadamente omite el borrado).
3. **Rol/credencial (defensa en profundidad):** el rol del usuario tiene `Delete` **OFF en
   todo** (principio §3.1 de la referencia común: "Nunca `Delete` para usuarios
   automáticos"). Aunque el código lo intentara, el CRM lo rechaza.

**Bytes nunca por el modelo:** `download_document` escribe a un **DL-root** acotado
(`SUDESPACHO_DL_ROOT`, saneado `realpath` contra symlink-escape, patrón `_resolve_dest`
de Gmail/google-despacho); solo se devuelven metadatos + ruta + `sha256`.

**Credenciales** en env / `~/.sudespacho-despacho/`; nunca en el árbol del repo ni en el
chat. (Regla dura del proyecto, `docs/SEGURIDAD_DATOS.md`.)

## 6. Descubrimiento de endpoints (proceso reutilizable — "la guinda")

Objetivo: que añadir una entidad nueva sea **rápido y repetible**, no media hora de
DevTools por entidad.

**Tres piezas (entregables de F1):**
1. **`describe_element(element)`** (tool de introspección). El CRM se auto-describe: hay
   endpoints que listan las propiedades de un elemento (`GET /api/view/complete/{element}`,
   `/api/view/quick_creation/{element}`), y las **claves** que devuelve `element_registries`
   ya son los nombres reales. La tool combina ambos y emite un **borrador de ficha**
   (slug + propiedades + 1-2 registros de muestra). Sirve también al modelo para saber qué
   campos existen antes de consultar.
2. **Playbook escrito** en `docs/INTEGRACION_SUDESPACHO.md` (§0, junto a la regla dura):
   *"Cómo añadir una entidad nueva"* — (a) `describe_element(slug)`; (b) revisar el borrador;
   (c) si es solo lectura, añadir la ficha al catálogo y marcar permitido/vetado; (d) si es
   escritura o hay rareza, **capturar HAR** para confirmar. Acumula las rarezas conforme
   aparecen (p. ej. `juzgados` propiedad no-relación).
3. **Catálogo** (`catalog.py`): slugs + propiedades + estado (`permitido`/`vetado`). Es la
   lista blanca de §5 y la fuente que consume `list_element_types()`.

**Límite (no rompe la regla dura del handoff):**
- **Lectura → casi automática** con `describe_element`. El HAR queda como verificación de
  rarezas.
- **Escritura (F2) → mantiene HAR obligatorio.** Ahí los nombres de propiedad importan
  (error → 500); la introspección ayuda pero no sustituye la captura.

## 7. Descarga de documentos

- Endpoint vivo: `GET /api/documents/{id}/downloadUri` → campo `presignedDownloadUrl`
  (RESUELTO 2026-06-10; los antiguos `/api/files/presigned_download_url/{id}` (400 IRI) y
  `/api/documents/presigned_urls/s3/download/{id}` (500) están rotos — no usar).
- `download_document` sigue el patrón R3 de google-despacho: resuelve la URL S3, descarga a
  una **ruta local acotada por DL-root** y devuelve `{path, sha256, mime, bytes}`. **Nunca**
  base64 al modelo. `get_document_download_url` devuelve solo la URL firmada (TTL corto) si
  se quiere pasar el enlace.

## 8. Tests

- `sudespacho_client.py`: **httpx fake inyectado** (patrón `build_server` de
  `email_export_mcp`); sin API viva en unitarios. Cubrir `{totalItems, items}` (no hydra),
  operador `equal`, paginación.
- **Lista blanca (§5):** un `element` vetado o fuera del catálogo → error, no llamada a la
  API. Test explícito de que **cada slug financiero/contable** está vetado.
- **Saneado del DL-root** (symlink-escape), como el de Gmail/google-despacho.
- **No-borrado (regla dura §5):** test que asegura que **ninguna** tool registrada tiene un
  nombre de borrado y que `sudespacho_client.py` **no** expone método `DELETE`.
- **`describe_element`:** contra un fake que devuelve `view/complete` + muestra → borrador
  correcto.
- **Paridad con `core`** (anti-drift, cuando aplique): regex de W-code, ids del tenant
  (`SUDESPACHO_ELEMENT`, EV MMC id), y —en F2— schema de evento forense.
- **Verificación de rol (manual, gate §3):** HAR con usuario abogado → 403 en contabilidad.
- **Check de integración manual** contra el CRM (un expediente real desechable) antes de
  dar F1 por viva.
- Regla del proyecto: todo cambio en código → tests en `tests/`.

## 9. Entregable / hecho cuando (F1)

- `.dxt` construido (manifest calcado del de google-despacho) e instalado en Claude Desktop;
  visible en Cowork por el puente; ejecutable también desde Claude Code.
- `list_element_types()` devuelve el catálogo permitido; los slugs financieros/contables
  **no** aparecen.
- Consulta de expedientes/documentos/entidades y **descarga a DL-root** operativas con la
  clave del usuario (Modelo A) — verificado el gate de rol (§3).
- `describe_element` produce fichas de catálogo; playbook escrito en
  `docs/INTEGRACION_SUDESPACHO.md`.
- Hito registrado en `STATUS.md` / `PLAN.md` + commit; entrada `[SIGUIENTE-MCP-SUDESPACHO]`
  en `PLAN.md`.

## 10. Referencias técnicas

- API de elementos (confirmados en `docs/INTEGRACION_SUDESPACHO.md`):
  `GET /api/element_registries/{element}` (listado), `/summary/{element}` (agregado),
  filtro `associated` por expediente, `/autocompletar/buscar/elemento/{element}`.
- Descarga: `GET /api/documents/{id}/downloadUri` → `presignedDownloadUrl`.
- Gotchas: singular `element_register/{id}?properties[]` → **500** ("Array to string
  conversion") → detalle completo por frontal legacy; `properties[]` required; operador
  **`equal`**; ids namespace-independientes judicial/extrajudicial; autoincremento
  `max()+1` (F2); `juzgados` propiedad no-relación.
- Auth REST `x-api-key`: `core/sudespacho_create.py::_get_api_key`,
  `core/sudespacho_relations.py` (`_rest_get_items`, `element_registries`).
- Molde del plugin: `plugins/google_despacho_mcp/` (`server.py`, `run_server.bat`,
  `dxt-build/manifest.json`), inyección para tests: `plugins/email_export_mcp/server.py`.
- Permisos y presets por rol: `../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md`
  (referencia común sudespacho, fusionada en `docs/INTEGRACION_SUDESPACHO.md` §14) — matriz
  §3 (elemento × Read/ReadGroup/Update/Delete/Create) y presets por rol §3.1. **El veto
  financiero real = apagar `Read` del rol abogado en esos elementos.**
- Modelo de datos financiero (conceptos/facturas/proforma, `/api/invoices`, idempotencia
  `facturado`, gramática `filterGroup`, enums, colisión `E1`):
  `../ElContable/docs/PLAN_DESCUBRIMIENTO_API_FacturacionEV.md`.
- **Host de calendario del CRM** (para la futura agenda): `api-calendar-commons-pro.sudespacho.biz`.
- Auth: dos mecanismos en el mismo host — **`x-api-key`** (global/admin, ~100% acceso, no
  ligada a usuario; la usa `core` para Nikolai) y **`Bearer JWT`** por login de usuario (lleva
  rol + identidad; la usa El Contable). **El MCP usa Bearer JWT (Modelo B, §3)**, NO la key.
  Baile de refresco de JWT ya en `core/sync_sudespacho_legacy.py` (`try_auto_refresh_jwt`).

## 11. Relación con el ecosistema

- **`core/` (motor determinista):** el MCP es interfaz, no lo reimplementa. Convive con
  Streamlit/CLI. Anti-drift por paridad, no por `import core`.
- **google-despacho (Calendar):** su F4 es **Google Calendar** — distinto del
  **calendario/agenda del propio CRM** (que es de *este* MCP). No confundir.
- **EXPEDIENTES-XL / expedientes:** fuera (bytes locales, `G:`). Este MCP habla con la nube
  del CRM.
- **Skills del despacho:** las de lectura del CRM podrán delegar en este MCP en el futuro
  (fuera de F1).

## 12. Próximo paso

1. **Gate de auth — testeable YA con el usuario de Nikolai (§3):** login en el CRM →
   observar en DevTools el `Bearer JWT` + refresh y el endpoint de login/refresh → una
   llamada REST con ese JWT → confirmar **atribución** del evento a Nikolai. Precisar si el
   REST necesita PHPSESSID o basta JWT+refresh. **No exfiltrar el JWT** (secreto). El test de
   **rol** (403 en contabilidad) necesita un usuario abogado, aparte.
2. Encadenar la skill **`writing-plans`** para desglosar **F1 (lectura)** en plan de
   implementación (con la auth Modelo B como primer bloque, apoyada en el baile de refresco
   ya existente en `core/sync_sudespacho_legacy.py`).
