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
que Gmail/google-despacho: PC encendido + app de escritorio + puente).

**🔴 Requisito de distribución (corregido tras revisión adversarial):** para que un compañero
lo instale, el `.dxt` debe ser **autocontenido** — **no** puede depender del repo de FeesDefender
(Ana/Paola no lo tienen) ni de una ruta de Python personal de Nikolai. El `run_server.bat` NO debe
hardcodear `C:\Users\tnm33\...python.exe` ni lanzar `-m plugins.sudespacho_mcp` (eso exige el repo
+ cwd correcto). El plugin es **standalone de verdad** (paquete autosuficiente dentro del `.dxt`,
intérprete resuelto de forma portable). Si acabara dependiendo del repo, solo arrancaría en la
máquina de Nikolai y el objetivo "escalable a compañeros" se cae.

Separación lógica-pura / wrapper (patrón `plugins/expedientes_xl/` y
`email_export_mcp/build_server`):

```
sudespacho_mcp/            # paquete autosuficiente (se empaqueta entero en el .dxt)
    __init__.py
    sudespacho_client.py   # cliente REST puro; httpx + proveedor de sesión inyectables (tests)
    auth.py / session.py / token_store.py  # Modelo B: login, refresco rodante, persistencia
    catalog.py             # lista blanca de slugs + slugs vetados + filtro de propiedades (§5)
    discovery.py           # introspección: describe_element() SOLO ESQUEMA
    server.py              # registro de tools FastMCP; resuelve sesión, aplica lista blanca, delega
    sudespacho_cli.py      # alta de cuenta (login interactivo, local; guarda solo tokens)
    run_server.bat         # wrapper de arranque PORTABLE (sin ruta personal ni dependencia del repo)
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

### 3.1 Sesión y reconexión (UX de credenciales — objetivo: cero fricción)

- **Alta (una vez) — por `refresh_token`, NO por contraseña (verificado 2026-07-13):** no existe
  endpoint estándar de login usuario/contraseña en la API (todos 404), así que el compañero pega
  **su `refresh_token`** (de DevTools → localStorage de su sesión CRM) en `sudespacho_cli.py login`.
  El plugin arranca el JWT con `POST /api/token/refresh` y guarda ambos en `~/.sudespacho-despacho/`.
  **El plugin NUNCA maneja la contraseña**; el `refresh_token` es secreto y no va a chat ni repo.
  *(Automatizar el login de cero —frontal + posible CSRF— queda fuera de alcance salvo disparador.)*
- **Uso continuado:** JWT de 60 min; el plugin lo **refresca solo** con el refresh_token.
  **Sin re-login por uso** (p. ej. leer un expediente 2 h después: transparente).
- **Reinicio (PC / Claude Desktop apagado y encendido):** los tokens **persisten en disco**;
  al relanzar, el MCP refresca con el refresh_token guardado. **No re-login** mientras el
  refresh_token siga vivo. Cerrar Claude Desktop **≠** cerrar sesión en el CRM.
- **Re-login:** solo al caducar el refresh_token, o tras logout explícito / cambio de
  contraseña.
- **🔎 GATE (dato pendiente):** el **refresh_token es OPACO** (128 chars, no-JWT, verificado
  2026-07-13) → su caducidad y si es *rodante* la sabe solo el servidor. **Medir**
  (empíricamente o preguntando a sudespacho) la vida del refresh_token: determina cada cuánto
  re-loguea el usuario. Enlaza con la tensión de licencia: mantener la sesión caliente evita
  re-login pero puede consumir un slot de los 4; apagar el PC de noche libera el slot.

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
| `get_expediente(exp_id, element)` | metadatos. ✅ **VERIFICADO 2026-07-13:** la forma **coma** `element_register/{id}?properties=a,b,c` devuelve **200** (la forma **array** `properties[]=` da 500). Usar la coma. `INTEGRACION §8.3` ("no workaround") quedó desactualizado. |
| `list_documentos(exp_id, element)` | documentos de un expediente. Requiere que el slug de documentos (`gdocu`) esté en la lista blanca (§5); sin él, no hay forma de obtener un `doc_id` (corregido tras revisión adversarial) |
| `download_document(doc_id, exp_id, element, dest?)` | **tool principal de descarga**: resuelve `downloadUri` y **escribe a DL-root** local + `sha256`; devuelve ruta+hash+metadatos, **nunca** la URL S3 ni bytes/base64 por el modelo (§7). **Antes de descargar, valida que el elemento origen del documento NO está vetado** (un `doc_id` de factura no se sirve aunque se conozca su id) |
| `get_document_download_url` | **NO se expone** (entregaría una URL S3 prefirmada al modelo = capability token, contra el principio DL-root). Uso interno de `download_document` |

**Introspección / descubrimiento** (§6):

| Tool | Nota |
|---|---|
| `describe_element(element)` | **SOLO ESQUEMA** (nombres de propiedad + tipos, vía `/api/view/complete/{element}`). **NO devuelve registros de muestra** (evita volcar importes/PII al chat). Descubrir un elemento nuevo = su esquema, no sus datos. Un modo con muestra —si algún día hace falta— pasaría por la lista blanca y **nunca** por un slug vetado (corregido tras revisión adversarial) |

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

**🔴 La lista blanca por slug NO basta — fuga por campo/relación (corregido tras revisión
adversarial).** La referencia de permisos (`REFERENCIA_SUDESPACHO_API_PERMISOS.md` §3) avisa:
*"no hay toggle por-campo; leer importes (`total`, `duracion`, conceptos, facturas) parece
bastar con el `Read` del elemento"*. Y `properties[]` admite relaciones `left./right.<elem>.<campo>`
y agregados `sum(...)`. Como `actuaciones`/`expedientes` están permitidos y **llevan importes**,
un abogado podría leer honorarios vía `properties=["total","sum(right.conceptos_honorario.total)"]`
o vía `summary`, **sin tocar un slug vetado**. Por tanto el plugin añade un **filtro de propiedades**:
- **Veto de propiedades económicas** por nombre (`total`, `base_imponible`, `precio_unidad`,
  `importe*`, `iva*`, `irpf*`, `cobro*`, `pago*`, …) en `list_elements`/`summary`/`por_expediente`.
- **Veto de propiedades-relación a un slug vetado** (`*.conceptos_*`, `right.facturas.*`,
  `*.facturas_proforma.*`, y cualquier `sum(...)` sobre esas) — se rechazan aunque el elemento
  raíz esté permitido.
- El detalle/documentos validan también el **elemento origen** contra la lista blanca.

**El CRM como portero (barrera primaria — SIN verificar todavía).** La confidencialidad real se
apoya en que **cada compañero use su cuenta personal (Modelo B, §3)** y que **su rol niegue la
contabilidad server-side**. Pero eso está **PENDIENTE de verificar** (Nikolai es admin y lo ve
todo) y la referencia sugiere que a nivel de campo no hay bloqueo. Por eso:
- **Prerrequisito bloqueante de F1-producción:** probar con un usuario de rol abogado que recibe
  **403/vacío** tanto en un **slug financiero** (`facturas`) como en un **campo económico de un
  elemento permitido** (`actuaciones.properties[]=total`) y al **descargar un documento de factura**.
- Mientras no se verifique, el **filtro de propiedades del plugin** (arriba) es el control que
  NO depende de esa premisa. Defensa en profundidad: rol del CRM (por confirmar) + lista blanca de
  slugs + filtro de propiedades + veto de relaciones.
- **Nunca** repartir la `x-api-key` global con el plugin (ve todo, sin rol ni atribución).

**Borrado — NUNCA, regla dura (en ninguna fase, ni F1 ni F2+).** Triple garantía en capas:
1. **Tools:** el plugin no registra ninguna tool de borrado; sin `delete_*`, sin flag
   `permanent`. No hay superficie de borrado que el modelo pueda invocar.
2. **Cliente HTTP:** `sudespacho_client.py` no implementa el verbo `DELETE` (calcado del
   transporte de El Contable, que deliberadamente omite el borrado).
3. **Rol/credencial (defensa en profundidad):** el rol del usuario tiene `Delete` **OFF en
   todo** (principio §3.1 de la referencia común: "Nunca `Delete` para usuarios
   automáticos"). Aunque el código lo intentara, el CRM lo rechaza.

**Reformulación como NO-PÉRDIDA-DE-DATOS (para F2, tras revisión adversarial).** El borrado en
este CRM **no necesita el verbo DELETE**: un PUT/PATCH de `relation_element` que reenvíe el array
sin una relación existente **la elimina** (`REFERENCIA §2`: "excluir una relación = omitirla del
array"), y `register_expediente` está marcado **destructivo** (§10). En F1 (solo lectura) no hay
riesgo, pero **F2 debe nacer con política de update no-destructivo**: merge/append de relaciones
(nunca reemplazo ciego del array), lectura-antes-de-escribir que preserve lo existente, y prohibir
endpoints destructivos como `register_expediente`. La regla dura es **no pérdida de datos**, no
solo "no DELETE".

**Bytes nunca por el modelo:** `download_document` escribe a un **DL-root** acotado
(`SUDESPACHO_DL_ROOT`, saneado `realpath` contra symlink-escape, patrón `_resolve_dest`
de Gmail/google-despacho); solo se devuelven metadatos + ruta + `sha256`.

**Credenciales y secretos** en env / `~/.sudespacho-despacho/`; nunca en el árbol del repo ni en el
chat (regla dura del proyecto, `docs/SEGURIDAD_DATOS.md`). Además (tras revisión adversarial):
- **Redacción en logs:** el wrapper `.bat` enruta stderr a un log → **nunca** loguear headers
  `Authorization`/`Bearer` ni cuerpos de login/refresh; el cliente enmascara `token`/`refresh_token`
  en excepciones y trazas. Test que asegura que no se vuelca el header de autorización.
- **Permisos del fichero de tokens:** `tokens.json` guarda un refresh_token de larga vida (capability
  a la sesión CRM completa) → permisos restrictivos de fichero (ACL de solo-usuario); el riesgo
  residual (texto plano) se documenta en `SEGURIDAD_DATOS.md`.

## 6. Descubrimiento de endpoints (proceso reutilizable — "la guinda")

Objetivo: que añadir una entidad nueva sea **rápido y repetible**, no media hora de
DevTools por entidad.

**Tres piezas (entregables de F1):**
1. **`describe_element(element)`** (tool de introspección, **solo esquema**). El CRM se
   auto-describe: `GET /api/view/complete/{element}` (y `/quick_creation/{element}`) listan las
   propiedades. La tool emite un **borrador de ficha con nombres de propiedad + tipos, SIN
   registros de muestra** (evita volcar importes/PII). El endpoint `view/complete` es una
   aserción del spec **a verificar**; si no existe, se cae a listar los **nombres de propiedad**
   de una muestra (sin sus valores). Sirve al modelo para saber qué campos existen antes de
   consultar. *(La contradicción "para descubrir hay que saltarse la lista blanca" se resuelve
   así: el esquema no expone datos, luego describir un elemento aún-no-aprobado no filtra nada.)*
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
- `download_document` sigue el patrón R3 de google-despacho: resuelve la URL S3 (uso interno),
  descarga a una **ruta local acotada por DL-root** y devuelve `{path, sha256, mime, bytes}`.
  **Nunca** base64 ni la URL S3 al modelo (la URL prefirmada es un capability token; **no se
  expone** — corregido tras revisión adversarial). La descarga usa `timeout` + `follow_redirects`
  (como `core._download_url_raw`; sin ellos S3/CloudFront cuelga o falla en redirect).
- **Antes de resolver `downloadUri`, validar el elemento origen del documento** contra la lista
  blanca (un `doc_id` de una factura no se sirve aunque se conozca su id; los ids pueden ser
  enumerables). Gate en vivo: usuario abogado → 403 al descargar un documento de factura.

## 8. Tests

- `sudespacho_client.py`: **httpx fake inyectado** (patrón `build_server` de
  `email_export_mcp`); sin API viva en unitarios. Cubrir `{totalItems, items}` (no hydra),
  operador `equal`, paginación.
- **Lista blanca (§5):** un `element` vetado o fuera del catálogo → error, no llamada a la
  API. Test explícito de que **cada slug financiero/contable** está vetado.
- **Saneado del DL-root** (symlink-escape), como el de Gmail/google-despacho.
- **No-borrado (regla dura §5):** test que asegura que **ninguna** tool registrada tiene un
  nombre de borrado y que `sudespacho_client.py` **no** expone método `DELETE`.
- **`describe_element`:** devuelve **solo esquema** (nombres+tipos), **sin valores** de muestra.
- **Filtro de propiedades (§5):** rechaza `properties` económicas (`total`, `base_imponible`, …)
  y relaciones a slug vetado (`*.conceptos_*`, `sum(...total)`) aunque el elemento raíz sea permitido.
- **Paridad REAL con `core`** (anti-drift): tests que importan `core` **y** el plugin, mismo
  transporte fake, y comparan lo emitido/parseado para la lógica DUPLICADA y frágil: parseo
  `{totalItems,items,values[]}`, gramática `filterGroup` **`associated` de 2 niveles** (no 3),
  **paginación**, `downloadUri`. Además regex W-code / ids del tenant, y —en F2— schema de evento.
- **Verificación de rol (manual, gate §3):** usuario abogado → 403 en un **slug** financiero
  **Y** en un **campo** económico de un elemento permitido (`actuaciones.total`) **Y** al descargar
  un documento de factura.
- **Check de integración manual** contra el CRM (expediente real desechable): incluir
  `get_expediente` (¿coma vs 500?), `list_documentos`+`download_document`, además de la lectura.
- Regla del proyecto: todo cambio en código → tests en `tests/`.

## 9. Entregable / hecho cuando (F1)

- `.dxt` construido (manifest calcado del de google-despacho) e instalado en Claude Desktop;
  visible en Cowork por el puente; ejecutable también desde Claude Code.
- `list_element_types()` devuelve el catálogo permitido; los slugs financieros/contables
  **no** aparecen.
- Consulta de expedientes/documentos/entidades y **descarga a DL-root** operativas con la
  **cuenta personal del usuario (Modelo B)** — verificado el gate de rol (§3) a nivel slug Y campo.
- `describe_element` produce fichas de esquema (sin datos); playbook escrito en
  `docs/INTEGRACION_SUDESPACHO.md`.
- **Un solo consumidor por usuario** del `tokens.json` (o acceso serializado con lock): evita la
  carrera del refresh rodante entre Claude Code y el puente de Desktop (§3.1).
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

## 13. Revisión adversarial (2026-07-13) — correcciones aplicadas y gates en vivo

Cuatro revisores adversariales (seguridad · auth/sesión/licencia · arquitectura · producto).
El núcleo resistió (rechazo de la key global, deny-by-default por slug, no-borrado en F1,
DL-root, auth de lectura verificada). Correcciones ya incorporadas al spec/plan:

- **Confidencialidad por debajo del slug (§5):** filtro de **propiedades** económicas y de
  relaciones a slug vetado (la lista blanca por slug no basta; los importes viajan como campos
  de `actuaciones`/`expedientes`).
- **`describe_element` solo esquema (§4/§6):** sin registros de muestra (evita volcar importes/PII).
- **Documentos (§4/§7):** `download_document` es la tool (a DL-root); NO se expone la URL S3;
  validar el elemento origen del doc contra la lista blanca; `gdocu` en la lista blanca.
- **Bug 500 del detalle (§4/§7):** retirada la afirmación "la coma esquiva el 500"; es hipótesis
  a probar en vivo, con **fallback al frontal legacy**.
- **`.bat` distribuible (§2):** sin ruta de Python personal ni dependencia del repo; `.dxt`
  autocontenido (si no, no escala a compañeros).
- **No pérdida de datos (§5):** F2 con update no-destructivo (no basta "no DELETE").
- **Secretos en logs / permisos del token store (§5).**
- **Plan F1:** token store atómico + lock + carga tolerante; refresco reactivo a 401;
  `_extract` tolerante (rt opcional, como `core`); descarga con timeout+redirects; paginación;
  tests de paridad reales; slugs verificados antes de la lista blanca.

**Gates — estado tras la sesión de verificación en vivo (2026-07-13, usuario admin de Nikolai):**
1. ⏳ **Rol abogado oculta la contabilidad** a nivel **slug Y campo** (`actuaciones.total`) y en
   **descarga de documento de factura**. **PENDIENTE** — necesita un usuario de rol abogado real
   (Nikolai es admin y lo ve todo). Vector de fuga por campo confirmado (`actuaciones` lleva `total`).
2. ✅ **Login — RESUELTO (cambio de enfoque):** NO hay endpoint estándar de login usuario/contraseña
   (`/api/login_check`, `/api/token`, `/api/auth/login`, `/api/login`… todos **404**). **Decisión:**
   el alta es **"pegar el `refresh_token` una vez"** (de DevTools del usuario); el plugin arranca el
   JWT con `POST /api/token/refresh` (ya funciona solo con el refresh). **El plugin NO maneja la
   contraseña.** Captura del login real solo si algún día se quiere automatizar del todo (frontal +
   posible CSRF).
3. ✅ **Bug 500 del detalle — RESUELTO:** verificado en exp. 672: `?properties[]=id` (array) → **500**;
   `?properties=id[,otras]` (**coma**) → **200** con el registro. `get_expediente_detalle` usa la
   coma; **no hace falta el frontal legacy**. ⚠️ `INTEGRACION_SUDESPACHO.md §8.3` ("no hay workaround")
   queda **desactualizado** → actualizar.
4. ⏳ **Escritura con JWT personal (para F2):** `POST /api/element_register` ¿acepta JWT de rol
   abogado y atribuye `created_by`? **PENDIENTE** (`core` migró las escrituras a `x-api-key`).
5. ⏳ **Tope de 4 licencias:** ¿una sesión del MCP consume licencia? ¿web+MCP cuenta doble?
   **PENDIENTE** (Nikolai lo consulta con sudespacho).
6. ⏳ **Vida del `refresh_token`** (opaco): **PENDIENTE de medir**; ¿rodante o TTL absoluto?
7. ✅ **Slugs — RESUELTO:** válidos = `clientes_propios`, `clientes_contrarios`, **`abogados_propios`**,
   **`abogados_contrarios`** (¡`abogados` a secas → 404!), `procuradores_propios`, `procuradores_contrarios`,
   `colaboradores`, `organismos`, `contactos`, `poderes`, `expedientes_judiciales`, **`extrajudiciales`**
   (`expedientes_extrajudiciales` → 404), `actuaciones`, `notas_tecnicas`, `tareas`, `gdocu`, **`juzgados`**
   (200 — el 404 era del path de relación, no del listado). **Descubrimiento:** `properties[]` es
   **obligatorio también en el listado** `element_registries` (omitirlo → 500).
