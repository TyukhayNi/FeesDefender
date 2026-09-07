---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-19
revision: v3 (2026-09-07 — la vía REST del módulo `MailRoundcube`, medida de punta a punta; el plugin pasa a plan B)
topic: Intake procuradores F3 — escritura en el CRM (relate + adjuntar)
relacionado:
  - docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md (§7, §15 F3)
  - docs/INTEGRACION_SUDESPACHO.md (§10.10 — SSOT del contrato)
  - docs/DEAD_ENDS.md (Módulo de correo nest-mail/Roundcube)
  - docs/superpowers/specs/2026-07-19-intake-miniapp-entrega-design.md (entrega; su §5 queda afectada)
---

# Diseño — F3: escritura en el CRM (relate correo↔expediente + adjuntar)

> Fase F3 del intake de correos de procuradores. F1 (matcher) y F2 (bandeja) están
> MERGEADAS y corren en dry-run. Esta fase añade la escritura real.
>
> **El nombre del fichero conserva «plugin-roundcube» por los enlaces entrantes; desde la
> rev. 3 el plugin ya no es la vía principal.** Lo es la API REST de `api-crm-commons`.

## 0. Qué cambió en la rev. 3, y por qué importa

Las rev. 1 y 2 daban por establecido que **la escritura solo era posible desde dentro de la
sesión del webmail**: un plugin propio de Roundcube, invocado por `fetch` desde el iframe,
con la sesión que el CRM monta por SSO. De ahí salía todo lo demás — el transporte por
webview, la miniapp con navegador embebido, el HTML que había que parsear con guardarraíl,
y la lista de incógnitas de la §8.

**Eso era cierto de la interfaz y falso del sistema.** El 2026-09-07 se midió que
`api-crm-commons` expone las mismas cuatro operaciones como REST, autenticadas con la
`x-api-key` que FeesDefender ya usa, y que **la cadena entera funciona con `cookies` y
`dataHash` vacíos**.

**El error de método, para no repetirlo:** el HAR del 2026-07-19 probó *qué hace la UI*, y de
ahí se concluyó *qué permite la API*. `MailRoundcube` llegó a marcarse «candidato descartado»
en `DEAD_ENDS` sin haberlo llamado nunca. El contrato declarado —`/api/docs.json`, público,
la Fase A del atlas que este mismo repo genera— lo nombraba desde el principio. Es
literalmente la trampa que `CLAUDE.md` §14.6 avisa: **leer el contrato declarado antes de
sondear en vivo**, y no confundir «no lo vi» con «no está».

El disparador de la revisión fue lateral: El Contable había archivado en su spec F10 la
sospecha de que `POST /api/mail/relate/attachments` «olía a la dirección contraria, a correo
entrante». Tenía razón y nadie la había seguido.

## 1. Objetivo y alcance

Dado un correo ya emparejado con su expediente y confirmado en la bandeja (F2),
**relacionarlo con el expediente en el CRM** y **subir sus adjuntos al gestor documental**
con nombre legible y carpeta correcta, de forma idempotente, verificada y trazada.

**Entra:** el cliente REST de las cinco operaciones de correo; el anti-duplicado; la
verificación por relectura; y la traza del resultado del write.

**NO entra:**
- **Nombrado LLM** y **decisión de qué adjunto subir** (F4). F3 consume `{nombre_final, subir}`
  por adjunto.
- Grabaciones (F5) y control de calidad (F6).
- **El webview.** Deja de ser necesario para el camino principal (§7 lo conserva como plan B).

## 2. El contrato, medido

Host `api-crm-commons-pro.sudespacho.biz`, header **`x-api-key`**, JSON. Todo lo de esta
sección se midió en vivo el **2026-09-07**; el detalle literal es el SSOT de
`INTEGRACION_SUDESPACHO.md §10.10`.

| Operación | Petición | Respuesta |
|---|---|---|
| Leer relaciones | `GET /api/mail/findRelations/{base64(Message-ID)}?account={n}` | `{elemento: {nombre, relacionados: {id: {id, url, texto, elemento, miembro}}}}` |
| Anti-duplicado en lote | `POST /api/mail/findAssigned` · `{messageIds: [<id>, …]}` | array con **los que ya están asignados** |
| ¿Trae adjuntos? | `POST /api/mail/attachments` · `{messageIds: "<id>", account}` | `{status, hasAttachments: bool, errors}` |
| **RELATE** | `POST /api/mail/relate/selected` · `{messageIds, relatedMembers, relatedElement, cookies, dataHash}` | `acumulaDatos.mailadjunto[mail_id] = [{id, nombre_archivo, enlace}]` |
| **ADJUNTAR** | `POST /api/mail/relate/attachments` · `{datosRelacionados, datosAdjuntos, folderId, messageIds}` | `{status: "success", errors: []}` — **siempre** (§4) |

Siete hechos que el diseño necesita y que la rev. 2 tenía mal o no tenía:

1. **`cookies` y `dataHash` se exigen presentes y funcionan vacíos.** El relate respondió 200
   y escribió con `""` en ambos. Son el resto de la firma del plugin, no una dependencia real
   de esta ruta. *(Lo que esto NO prueba: que sigan siendo opcionales mañana. §8.)*
2. **`relatedElement` va SIN el sufijo `->izq`** del plugin. Con él → 500 en
   `RelationsViewsService::getRawData()`.
3. **El relate devuelve el `mail_id` y los `att_id`** en `acumulaDatos.mailadjunto`, igual que
   el plugin: el encadenado relate→adjuntar se conserva, y la respuesta es **JSON**, no el
   HTML que la rev. 2 mandaba parsear.
4. **`uid` del elemento `mail` ES el Message-ID RFC.** Medido aquí (39/40 de una muestra) y
   antes por El Contable. El filtro `uid = <Message-ID>` discrimina 1 sobre un censo de
   462.414. **Consecuencia:** el `mail_id` se recupera releyendo, lo que **deroga el «límite
   conocido» de la rev. 2** (que daba por imposible recuperarlo sin re-relacionar).
5. **`account` es el campo `cuenta` del elemento `mail`**, y no es decorativo: **determina el
   buzón donde se busca**. El mismo Message-ID con la cuenta correcta devolvió relaciones y
   con otra devolvió vacío. Correlación cuenta→dirección medida por El Contable sobre 100
   correos (`REFERENCIA_SUDESPACHO_API_PERMISOS.md`); **cuenta `0` no es válida** para
   `findRelations` (400).
6. **El Message-ID vale con y sin `<>`.** Encaja con lo que ya guarda `gmail_source`, que lo
   pela con `.strip("<>")`. Sin conversión.
7. **`hasAttachments` cuenta también los inline** (logo de firma): un correo dio `true` y su
   `mailadjunto` vino vacío. No es un fallo del endpoint —da `false` cuando toca, comprobado—
   sino que **son dos preguntas distintas**: `hasAttachments` = «¿hay algo adjunto?»;
   `mailadjunto` del relate = «¿qué adjuntos son archivables?». Para decidir qué subir, la
   buena es la segunda.

**Prueba de punta a punta** (expediente de prueba extrajudicial 636, 2026-09-07):
censo previo del gestor documental = 0 documentos → relate → `findRelations` devuelve
`extrajudiciales:636` → adjuntar 1 de 3 adjuntos → censo posterior = 1 documento, con el
nombre pedido, en la carpeta 1. La selección se respetó: los otros dos no subieron.

## 3. Arquitectura

### 3.1 `core/procurador_relate.py` — cliente REST del módulo de correo

```
buscar_relaciones(message_id, account)        -> Relaciones          # findRelations
filtrar_ya_asignados(message_ids)             -> set[str]            # findAssigned (lote)
tiene_adjuntos(message_id, account)           -> bool                # attachments
relacionar(message_id, element, miembros)     -> RelateResult        # relate/selected
adjuntar(element, miembro, mail_id, adjuntos, folder_id, message_id) -> AdjuntarResult
archivar(plan)                                -> ArchivoResult       # orquestador §5
```

- **Transporte:** `SudespachoClient` (`core/sync_sudespacho.py`), que ya lleva la `x-api-key`.
  Nada de webview, nada de cookies de Roundcube, nada de credenciales IMAP.
- **Puro y testeable:** cada función construye su petición sin red; los tests inyectan un
  transporte fake con respuestas tomadas de la **forma real medida** (incluida la ruta
  anidada `acumulaDatos.mailadjunto[mail_id]`). El riesgo a evitar sigue siendo el mismo que
  en la rev. 2: fabricar el fixture desde la descripción y no desde lo observado.
- **Sin doble URL-encoding.** Era una particularidad del form-urlencoded del plugin. Aquí es
  JSON.

### 3.2 Resolución de la cuenta (`account`)

El robot lee de `procesal@`, que **no está en Roundcube**; el correo vive, por el
auto-forward, en las cuentas de los abogados, que es donde el CRM lo indexa. Hay que saber
con qué `account` preguntar.

**Se resuelve por lectura, no por configuración:** `GET /api/element_registries/mail`
filtrado por `uid = <Message-ID>` devuelve el registro con su campo `cuenta`. Una llamada, y
además confirma que el CRM ya conoce el correo. Si no aparece en ninguna cuenta, el correo no
está indexado y **no se archiva por esta vía** → a revisión, nunca a adivinar iterando.

### 3.3 Carpeta del gestor documental

Sin cambios respecto de la rev. 2: `SudespachoClient.list_gdocu_folders` + el mapa estático
`CARPETA_ID_TO_PATH`/`CRM_TREE` de `core/config.py` como respaldo, porque la API no expone las
carpetas vacías. Por defecto **1 (General)**, que es lo que la prueba usó.

## 4. La regla que gobierna esta pieza: verificar por resultado

**`POST /api/mail/relate/attachments` devuelve `{"status": "success", "errors": []}` con los
tres parámetros vacíos.** Es un instrumento que no puede dar el otro valor: su `success` no
distingue «subí el documento» de «no hice nada». Comprobado a propósito antes de fiarse de él.

De ahí, y no de una preferencia de estilo, salen tres obligaciones del cliente:

- **El adjuntar se verifica releyendo el gestor documental** del expediente
  (`element_registries/gdocu` con `operator=associated`, `property=left.{element}.id`), y se
  compara el censo antes/después. Sin eso, `adjuntar()` **no puede devolver `ok=True`**.
- **El relate se verifica releyendo `findRelations`**, no por el 200.
- Ningún `ok` del módulo se deriva de un código de estado. Es la regla dura de
  `INTEGRACION_SUDESPACHO.md §14.6`, y aquí hay un caso concreto que la exige.

## 5. Flujo end-to-end

1. **Anti-duplicado en lote:** `filtrar_ya_asignados([…])` con los Message-ID del lote. Una
   llamada para todos. Los que vuelven, ya están archivados → se muestran ✅, no se re-archivan.
2. Resolver `account` por lectura del elemento `mail` (§3.2).
3. `buscar_relaciones(...)` — ¿ya relacionado **con este expediente**? Idempotencia fina: puede
   estar relacionado con otro y aun así faltar el nuestro.
4. `relacionar(...)` → `mail_id` + `[{att_id, nombre_archivo}]`. **Persistir los ids en cuanto
   responde**, para poder reanudar el adjuntar sin re-relacionar. *(Ya no es imprescindible
   —§2.4 permite recuperarlos releyendo— pero ahorra una llamada y una carrera.)*
5. Verificar el relate por relectura (§4).
6. F4 (fuera) decide por adjunto `subir` sí/no y `nombre_final`.
7. Resolver `folder_id`.
8. `adjuntar(...)` **solo con los seleccionados**.
9. Verificar el adjuntar por censo del gestor documental (§4).
10. Grabar la traza del resultado (§6) y marcar el correo procesado (F2).

## 6. Traza del resultado

Sin cambios de fondo respecto de la rev. 2: `record_decision` (F2) graba propuesta-robot vs
acción-humana vs quién/cuándo, y F3 **extiende** ese modelo con el outcome del write
`{ok, mail_id, folder_id, adjuntos_subidos, verificado, error}` y el estado `archivado_en_crm`.
Lo exige el requisito duro §18.9 del plan y lo consume F6. Se diseña dentro del modelo de
datos de la cola, no se atornilla después.

Novedad de la rev. 3: **`verificado` es un campo propio**, distinto de `ok`. Un write cuyo
status fue 200 pero cuya relectura no confirmó nada es un caso real (§4) y tiene que poder
distinguirse en la traza.

## 7. El plugin y el webview, como plan B

No se tiran: se degradan a respaldo documentado.

- Si un día la API REST **empezara a exigir de verdad `cookies`/`dataHash`** (§8.1), el
  camino conocido es capturarlos de un webview donde el CRM haya hecho su SSO y **pasárselos
  al mismo endpoint REST** — que es bastante más simple que el `fetch` dentro del iframe
  cross-origin de la rev. 2, porque las peticiones se siguen construyendo en Python.
- El contrato del plugin (`plugin.sudespacho_asignaa_*`, form-urlencoded, doble encoding del
  composite, `X-Roundcube-Request`) queda archivado en `INTEGRACION_SUDESPACHO.md §10.10` con
  su HAR de origen. Sigue siendo lo que hace la interfaz.
- **La miniapp con navegador embebido deja de ser necesaria para archivar.** El spec de
  entrega (`…-intake-miniapp-entrega-design.md` §5) queda afectado y hay que revisarlo: sin
  webview, la bandeja puede correr como la app Streamlit que ya existe. **No se resuelve aquí**
  — es su documento.

## 8. Lo que NO está probado, dicho por delante

1. **Que `cookies`/`dataHash` vacíos sigan valiendo.** Están declarados como obligatorios en
   el 400 que el servidor devuelve al omitirlos; hoy se aceptan vacíos. Es un comportamiento
   observado, no un contrato prometido. **Mitigación:** un test de integración —marcado
   `slow`, no en la suite normal— que lo compruebe contra el expediente de prueba, y un error
   clasificado aparte si un día cambia.
2. **La idempotencia del adjuntar.** No se ha probado a re-postear el mismo adjunto. Hasta que
   se pruebe, el cliente **no reintenta el adjuntar solo**: comprueba primero el censo.
3. **`extrajudiciales` está probado; `expedientes_judiciales`, no.** La prueba fue sobre el
   636, que es extrajudicial. El plan es judicial-first, así que **esto hay que medirlo antes
   de habilitarlo** — no se asume por simetría.
4. **Permisos de visibilidad.** El plugin llevaba `groups/usersAccessRegister`; la vía REST no
   los pide. Queda por ver con qué visibilidad nace la relación y si eso importa.
5. **Qué pasa con un `relatedMembers` inexistente.** Devuelve 200 y no escribe (comprobado con
   un id inventado: censo idéntico antes y después). O sea: **el 200 tampoco prueba que el
   miembro exista** → una más para la §4.

## 9. Testing

- Transporte **fake** que captura `(path, body)` y devuelve respuestas canned con la forma
  real medida. Nada de red en la suite.
- Casos: relate OK (extrae `mail_id`/`att_id`) · `relatedElement` sin `->izq` · adjuntar solo
  los seleccionados · **adjuntar cuyo `success` no se corresponde con el censo → `ok=False`**
  · ya-relacionado → no-op · anti-duplicado en lote · Message-ID con y sin `<>` · cuenta
  ausente → revisión, no adivinar.
- **El caso que no puede faltar** (§4): un fake que devuelve `success` y un censo que no
  cambia. Si el módulo lo da por bueno, el test tiene que ponerse rojo.
- Lo que los tests **no** cubren, y se valida en vivo: la vigencia de §8.1, la idempotencia
  del adjuntar y el caso judicial.

## 10. Dependencias y orden

- **Ya no hay bloqueo de auth.** El Track 1 (handshake del webmail) desaparece del camino
  crítico.
- **F4** consume la salida del relate. Frontera sin cambios: F4 entrega
  `{att_id?, nombre_final, subir}`; el join F4↔relate se hace por `nombre_archivo`/orden con
  guardarraíl (verificar conteo, exigir unicidad o coincidencia de orden; si es ambiguo →
  revisión, nunca adivinar).
- **Alcance:** judicial-first, pendiente de §8.3. `clientes` fuera (F2 lo retiró; YAGNI).

## 11. Higiene

Los HAR y cabeceras del análisis original contienen PII real: no se commitean y se borran. Este
spec usa placeholders. **Del sondeo del 2026-09-07 quedan residuos deliberados en el
expediente de prueba 636** —tres correos relacionados y el documento `gdocu 42865`
(`SONDA FEESDEFENDER 2026-09-07 - borrable.pdf`)— que **no se han borrado**: en el CRM no se
borra nada sin autorización expresa de Nikolai.
