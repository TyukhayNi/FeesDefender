---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-19
topic: Intake procuradores F3 — escritura en el CRM (relate + adjuntar)
relacionado:
  - docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md (§7, §15 F3)
  - docs/INTEGRACION_SUDESPACHO.md (§10.10 — SSOT del contrato del plugin)
  - docs/DEAD_ENDS.md (Módulo de correo nest-mail/Roundcube)
---

# Diseño — F3: escritura en el CRM (relate correo↔expediente + adjuntar)

> Fase F3 del intake de correos de procuradores. Diseño validado contra el HAR de
> un relate+adjuntar manual (`judicial_648.har`, 2026-07-19) **y** contra 4 capturas
> de pantalla del flujo UI. F1 (matcher) y F2 (bandeja) ya están MERGEADAS; esta fase
> añade la escritura real, que hoy corre en dry-run.

## 1. Objetivo y alcance

Dado un correo ya emparejado con su expediente y confirmado en la bandeja (F2),
**relacionarlo con el expediente en el CRM** y **subir sus adjuntos al gestor
documental** con nombre legible y en la carpeta correcta, de forma idempotente y
con verificación posterior.

**Entra en este spec (Track 2):** el cliente que ejecuta las escrituras contra el
plugin Roundcube, más las lecturas api-crm que el diálogo necesita (tipos de entidad,
carpetas), con la **sesión Roundcube inyectada** como dependencia.

**NO entra:**
- **Obtención de la sesión Roundcube** (el handshake frontal→Roundcube). Es Track 1,
  spike de auth en curso; este módulo define el *contrato* de sesión y lo consume.
- La bandeja / confirmación humana (F2, ya hecha) y la terna de traza §18.9 (ya en F2).
- El **nombrado LLM** de adjuntos (F4). Este spec consume un nombre ya decidido y un
  flag "subir sí/no" por adjunto; la lógica que los produce es F4.
- Grabaciones (F5) y control de calidad (F6).

## 2. Hallazgos que fundamentan el diseño (HAR + UI)

1. **El write es un plugin propio de Roundcube**, no `MailRoundcube` (api-crm) ni
   `PUT /api/mail/{id}` (nest-mail) ni AppSync. Contrato completo (acciones + params)
   en `INTEGRACION_SUDESPACHO.md §10.10` (SSOT). Transporte: `POST
   roundcube.sudespacho.net/?_task=mail&_action=plugin.sudespacho_asignaa_*`,
   form-urlencoded, cabeceras `X-Requested-With` + `X-Roundcube-Request`.
2. **La llave del correo es el Message-ID RFC** (`<…@…>`), aceptado tal cual →
   puente directo Gmail↔CRM (el robot ya tiene el Message-ID desde Gmail).
3. **Dos diálogos secuenciales con dependencia de datos:**
   - Diálogo 1 "Asignación de email": elegir tipo de entidad → buscar/seleccionar el
     expediente → **Confirmar** = relate (`set_registros_seleccionados`).
   - La **respuesta del relate devuelve** `mailId` (id del correo registrado en el CRM)
     **y los `attId` de sus adjuntos**.
   - Diálogo 2 "Relacionar adjuntos": marcar casillas + renombrar + elegir carpeta →
     **Guardar** = adjuntar (`set_adjuntos_relacionar_crm`), que **consume** `mailId`/`attId`.
   → El adjuntar NO es posible sin relacionar antes; el orquestador debe encadenar.
4. **Renombrar y marcar casilla NO tienen endpoint** — son estado local del formulario;
   viajan solo en el submit del adjuntar (`datosAdjuntos[nombre_adjunto]` /
   `[seleccionado_adjunto]`). La extensión va bloqueada (solo se edita el nombre).
5. **No todo adjunto se sube:** en la captura, un `.png` de código de barras quedó
   desmarcado y solo el PDF se subió. F4 decide qué subir (logos/firmas fuera).
6. **Separación por auth:** solo 4 llamadas usan la sesión Roundcube (get_relaciones,
   relacionar, adjuntar, get_mails_asignados). La búsqueda de tipo/expediente y las
   carpetas son **api-crm REST con x-api-key** (auth que el robot ya tiene) → **no
   dependen del handshake**.

## 3. Arquitectura (componentes por responsabilidad y auth)

### 3.1 `core/procurador_relate.py` — cliente del plugin Roundcube (sesión inyectada)

Responsabilidad única: ejecutar las 4 acciones del plugin con una sesión dada.

```
get_relaciones(session, message_id) -> RelacionesPrevias
relacionar(session, message_id, id_elemento, *, uid, element, grupos, usuarios) -> RelateResult
    # RelateResult expone: ok, mail_id, adjuntos=[{att_id, nombre_original}], error
adjuntar(session, id_elemento, adjuntos_a_subir, folder_id, *, mail_id, message_id, uid, element) -> AdjuntarResult
    # adjuntos_a_subir = [{att_id, nombre_final}]  (nombre_final lo decide F4)
get_mails_asignados(session, uid, message_id) -> list           # verificación
archivar_en_crm(session, plan) -> ArchivoResult                 # orquestador fino
```

- **Contrato de sesión (dependencia):** objeto tipo `httpx.Client` con
  `base_url=https://roundcube.sudespacho.net`, cookies de sesión Roundcube y header
  `X-Roundcube-Request`. El módulo lo recibe; no lo fabrica. En tests, un fake que
  registra `(action, params)` y devuelve JSON canned.
- **`archivar_en_crm(session, plan)`** encadena: `get_relaciones` (anti-duplicado §4)
  → si no existe, `relacionar` → parsea `mail_id`+`att_id` de su respuesta → `adjuntar`
  con los adjuntos marcados y sus nombres → `get_mails_asignados` (verificación).
  `plan` = el ítem confirmado en la bandeja (F2): `{message_id, uid, element, id_elemento,
  folder_id, permisos:{grupos, usuarios}, adjuntos:[{att_id, nombre_final, subir}]}`. El
  orquestador resuelve `att_id`/`mail_id` reales desde la respuesta del relate, así que en
  `plan` los adjuntos se identifican por su correspondencia con los que devuelve el relate
  (por orden/nombre_original), no por un `att_id` conocido de antemano.
- Cada función construye el body **exactamente** como §10.10 y parsea el JSON Roundcube
  (`{action, exec, callbacks, unlock, env}`). Nunca lanza excepción que tumbe el runner:
  devuelve un result tipado con `ok=False` + motivo.

### 3.2 Capa api-crm (x-api-key, sin handshake)

- **Tipos de entidad relacionables:** `GET /api/view/relation/mail` → `relationsViews`.
  En la práctica es una lista fija (`expedientes_judiciales`, `extrajudiciales`,
  `clientes_*`, …); para el intake de procuradores el objetivo es casi siempre
  `expedientes_judiciales`. Se puede resolver con una constante y validar contra la
  llamada, sin hacerla en caliente.
- **Buscar/leer el expediente:** **reusar `core/procurador_search.py`** (F2) —
  `search_expedientes` (listado/filtro) y `fetch_expediente_datos` (por id). El `id`
  de la fila seleccionada es el `id_elemento` del relate.
- **Carpetas del gestor documental:** `list_gdocu_folders(id_elemento, parent, *, element)`
  → `GET /api/folders/gdocu/{parent}?related_element={element}&related_member={id}`.
  Items `{id, parent, label, color}`, jerárquico por `parent`. **Nota:** el plan §14
  anotaba que `list_gdocu_folders` devolvía vacío; el HAR lo explica — **faltaba
  `related_member`**. Verificar si ya existe un método en `SudespachoClient` y
  corregirlo/añadirlo con estos params.

## 4. Flujo end-to-end (un correo confirmado)

1. `get_relaciones(session, message_id)` — ¿ya relacionado con este expediente?
   Sí → saltar relate (idempotente), seguir a adjuntar si faltan documentos.
2. (api-crm, ya resuelto por F2) `id_elemento` del expediente confirmado.
3. `relacionar(...)` → `mail_id` + lista de adjuntos `{att_id, nombre_original}`.
4. F4 (fuera de este spec) decide, por adjunto: subir sí/no + `nombre_final`.
5. (api-crm) `list_gdocu_folders(...)` para resolver `folder_id` destino.
6. `adjuntar(id_elemento, [{att_id, nombre_final}], folder_id, mail_id=…, …)`.
7. `get_mails_asignados(...)` — verificar que el correo consta asignado.
8. (F2) registrar en la terna de traza + marcar el correo procesado.

## 5. Idempotencia y errores

- **Anti-duplicado (§4 del plan):** `get_relaciones` antes de escribir; el mismo correo
  en varios buzones se trata una sola vez (dedup ya en F2/`procurador_runner`).
- Respuesta no-JSON o `callbacks` de error → `ok=False` con motivo; el runner enruta el
  ítem a revisión, no se pierde.
- Fallo tras relacionar pero antes de adjuntar → el correo queda relacionado (estado
  válido) y el adjuntar se puede reintentar (idempotente sobre `mail_id`).

## 6. Incógnitas parametrizadas (se fijan con una corrida real)

No bloquean el código; se aíslan como parámetros/constantes con default del HAR y se
confirman al ejecutar contra un expediente de prueba:

1. `messageIdsEncontrados = <MsgID>,,,{n}` — el sufijo `,,,{n}` (en el HAR `,,,3`);
   `n` parece un contador/uid. Parametrizar y verificar.
2. `_unlock=loading{ts}` — id de lock del UI; presumiblemente el server no lo valida.
3. `elementoSeleccionado = {element}->izq` — confirmar si `->izq` es fijo o varía por
   tipo de elemento / posición de la relación.
4. `groups/usersAccessRegister[identifiers][]` — permisos de visibilidad (en el HAR `2`
   = EV MMC). Confirmar cómo se derivan (fijo por tenant vs por expediente).

## 7. Testing (TDD)

- Sesión Roundcube **fake** que captura `(action, params)` y devuelve respuestas canned
  tomadas de la forma del HAR (sin PII).
- Casos: relate OK (extrae `mail_id`/`att_id` de la respuesta) · adjuntar OK (params
  exactos, nombre y carpeta correctos) · ya-relacionado → no-op · adjunto desmarcado no
  viaja · respuesta de error → `ok=False`.
- `list_gdocu_folders`: mock httpx (mismo patrón que `procurador_search`), asertar
  `related_element`+`related_member` en la query.
- El módulo se prueba **sin red y sin sesión real**; la validación end-to-end contra el
  CRM llega cuando Track 1 entregue la sesión (expediente de prueba + limpieza posterior).

## 8. Dependencias y orden

- **Bloqueante para producción, NO para construir:** Track 1 (handshake de auth) decide
  si el cliente se dispara solo (A') o el humano remata con 1 clic (C). El cliente de
  §3.1 es necesario en A' y reutilizable; se construye ya con sesión inyectada.
- F4 (nombrado LLM) consume la salida del relate; se puede construir en paralelo o
  después. Este spec define la frontera (`{att_id, nombre_final, subir}`).

## 9. Higiene

Los HAR y capturas usados contienen PII real (correo de prueba, expedientes, terceros):
no se commitean (gitignored) y se borran tras el análisis. Los relates/adjuntos de
prueba en el CRM se limpian (hecho por Nikolai el 2026-07-19).
