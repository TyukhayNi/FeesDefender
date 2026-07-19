---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-19
revision: v2 (tras panel de revisión adversarial + verificación del flujo de correo y del código)
topic: Intake procuradores F3 — escritura en el CRM (relate + adjuntar)
relacionado:
  - docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md (§7, §15 F3)
  - docs/INTEGRACION_SUDESPACHO.md (§10.10 — SSOT del contrato del plugin)
  - docs/DEAD_ENDS.md (Módulo de correo nest-mail/Roundcube)
---

# Diseño — F3: escritura en el CRM (relate correo↔expediente + adjuntar)

> Fase F3 del intake de correos de procuradores. F1 (matcher) y F2 (bandeja) ya están
> MERGEADAS; hoy todo corre en dry-run. Esta fase añade la escritura real.
>
> **v2** incorpora: (a) el panel de 3 revisiones adversariales (HAR / auth-sesión /
> alcance-reuso); (b) la verificación en código de lo que ya existe; (c) el flujo de
> correo real, confirmado con cabeceras: `procesal@tyukhay.legal` **reenvía** (auto-forward
> de Gmail) a las 4 cuentas individuales de los abogados, y Roundcube es un **cliente IMAP
> sobre esas mismas cuentas de Gmail**. El `Message-ID` se **conserva** en el reenvío
> (verificado carácter a carácter) → es una llave estable robot↔Roundcube.

## 1. Objetivo y alcance

Dado un correo ya emparejado con su expediente y confirmado en la bandeja (F2),
**relacionarlo con el expediente en el CRM** y **subir sus adjuntos reales al gestor
documental** con nombre legible y carpeta correcta, de forma idempotente y con
verificación y traza del resultado.

**Entra (Track 2 — este spec):** el cliente que ejecuta las escrituras contra el plugin
Roundcube con la **sesión inyectada**; la resolución `Message-ID → (uid, cuenta, carpeta)`;
las lecturas api-crm que el diálogo necesita (tipos de entidad, carpetas); y la **traza del
resultado del write**.

**NO entra:**
- **Obtención de la sesión Roundcube** (handshake frontal→Roundcube): Track 1 (spike de auth
  en curso). Este módulo define el contrato de sesión y lo consume.
- **Nombrado LLM** y **decisión de qué adjunto subir** (F4). F3 consume `{nombre_final, subir}`
  por adjunto; la lógica que los produce es F4.
- Grabaciones (F5) y control de calidad (F6).

## 2. Topología de correo y auth (fundamento del diseño)

1. El procurador escribe a **`procesal@tyukhay.legal`** (y, residual, `procesal@fglegal.es`).
2. `procesal@` **no se opera**: por filtros de Gmail hace **auto-forward** a las **4 cuentas
   individuales** (`nikolai.tyukhay@`, `paola.barreto@`, `sergio.pinol@`, `ana.velastegui@`,
   todas `@tyukhay.legal`). El reenvío **conserva el `Message-ID` original** (verificado).
3. **El robot del intake lee `procesal@`** (`BUZONES_DESPACHO` en `core/gmail_source.py`).
4. **Roundcube (el webmail de sudespacho) es un cliente IMAP/SMTP sobre las cuentas de Gmail
   de cada abogado** (`imap.gmail.com`/`smtp.gmail.com`). `procesal@` **NO está en Roundcube**.
5. **Consecuencia clave:** el correo que el robot ve en `procesal@` es **el mismo mensaje**
   (mismo `Message-ID`) que está, por reenvío, en la cuenta Gmail de cada abogado — y esa
   cuenta es la que Roundcube abre. Por tanto el relate se hace **en la cuenta de un abogado**
   (no en `procesal@`), localizando el correo por `Message-ID`.

**Tres dominios de auth distintos** (verificado en código + HAR):
- `api-crm-commons-pro.sudespacho.biz` — REST, **`x-api-key`** (lo usa `core/`: buscar
  expediente, carpetas). Confirmado en `SudespachoConfig` (`auth_header="x-api-key"`).
- `tnm.sudespacho.net` — frontal legacy, `PHPSESSID`+`@token` (no lo usa F3).
- `roundcube.sudespacho.net` — webmail, **sesión Roundcube** (cookies `roundcube_sessid`/
  `sessauth` + header `X-Roundcube-Request`, token estable por-sesión). Es el único auth que
  F3 no tiene resuelto (Track 1).

## 3. Hallazgos que fundamentan el diseño (HAR + UI + cabeceras + código)

1. **El write es un plugin de Roundcube** (`POST roundcube.sudespacho.net/?_task=mail&_action=
   plugin.sudespacho_asignaa_*`, form-urlencoded, `X-Requested-With`+`X-Roundcube-Request`).
   NO es `MailRoundcube` (api-crm) ni `PUT /api/mail/{id}` (nest-mail) ni AppSync. SSOT del
   contrato: `INTEGRACION_SUDESPACHO.md §10.10`.
2. **Dos diálogos con dependencia de datos** (confirmado HAR):
   - Diálogo 1 "Asignación de email": elegir entidad → buscar/seleccionar expediente →
     **Confirmar** = relate (`set_registros_seleccionados`).
   - **La respuesta del relate DEVUELVE** `mail_id` (id del correo en el CRM) y la lista de
     adjuntos con sus `att_id` — en `env.sudespacho_comprueba_adjuntos_email.acumulaDatos.
     mailadjunto[mail_id] = [{id, nombre_archivo, enlace}]`. **No preexisten** (no salen de
     `get_relaciones` ni de las GET api-crm). → El adjuntar CONSUME lo que el relate produce;
     encadenar es obligatorio.
   - Diálogo 2 "Relacionar adjuntos": marcar casillas + renombrar + carpeta → **Guardar** =
     adjuntar (`set_adjuntos_relacionar_crm`).
3. **La llave del write es un composite Roundcube**, no el `Message-ID` pelado:
   `messageIdsEncontrados = <MsgID>,,,{uid}|||RC,,,{id_cuenta},,,{carpeta}`, **doblemente
   URL-encodeado** (solo este campo; `get_relaciones` usa el `Message-ID` simple). El `{uid}`
   es el UID IMAP del mensaje en esa cuenta; `{id_cuenta}` es el id interno de la cuenta en
   Roundcube; `{carpeta}` es la carpeta IMAP (INBOX **o** una etiqueta como "00. PROCESAL").
4. **`Message-ID` estable** (verificado): se conserva del procurador a `procesal@` y a la
   cuenta del abogado. Es la llave de emparejamiento robot↔Roundcube y la entrada para
   resolver `(uid, cuenta, carpeta)` por búsqueda IMAP.
5. **Renombrar y marcar casilla NO tienen endpoint**: viajan en el submit del adjuntar
   (`datosAdjuntos[nombre_adjunto]` / `[seleccionado_adjunto]`). Extensión bloqueada.
6. **No todo adjunto se sube**: el correo trae inline (logo, `Content-Disposition: inline` +
   `Content-ID`) y adjuntos reales (`Content-Disposition: attachment`). F4 decide; el criterio
   inline-vs-attachment es determinista por cabecera, no "a ojo".
7. **Solo 4 llamadas usan la sesión Roundcube** (get_relaciones, relacionar, adjuntar,
   get_mails_asignados). Buscar entidad/expediente y carpetas son api-crm `x-api-key`.

## 4. Arquitectura (componentes por responsabilidad y auth)

### 4.1 `core/procurador_relate.py` — cliente del plugin Roundcube (sesión inyectada)

```
get_relaciones(session, message_id) -> RelacionesPrevias   # HTML → parse; solo Message-ID
relacionar(session, message_ids_encontrados, id_elemento, *, element, grupos, usuarios)
    -> RelateResult   # ok, mail_id, adjuntos=[{att_id, nombre_archivo}], error
adjuntar(session, id_elemento, adjuntos_a_subir, folder_id, *, mail_id, message_ids_encontrados, element)
    -> AdjuntarResult   # adjuntos_a_subir = [{att_id, nombre_final}]
get_mails_asignados(session, uid, message_id) -> list       # verificación (débil, ver §6)
archivar_en_crm(session, plan) -> ArchivoResult             # orquestador; ver §5
```

- **Contrato de sesión (dependencia):** objeto tipo `httpx.Client` con
  `base_url=https://roundcube.sudespacho.net`, cookies de sesión Roundcube y header
  `X-Roundcube-Request`. Lo recibe; no lo fabrica. Tests: fake que captura `(action, params)`
  y devuelve JSON canned **tomado de la forma real del HAR** (incluida la ruta anidada
  `acumulaDatos.mailadjunto[mail_id]`).
- **Encoding:** el módulo pre-encodea `messageIdsEncontrados` una vez y deja que el
  form-encoder lo encodee otra (doble encoding) — **solo** en ese campo.

### 4.2 Resolución `Message-ID → (uid, cuenta, carpeta)`

El robot leyó el correo en `procesal@`, pero el relate se hace en la cuenta de un abogado.
Hay que resolver el UID IMAP + carpeta del correo en esa cuenta a partir del `Message-ID`
estable. Vía: **búsqueda IMAP en `imap.gmail.com`** de la cuenta del abogado (el robot ya
tiene OAuth a esas cuentas vía `gmail_source`), o una acción de búsqueda del propio Roundcube
(a capturar). El `id_cuenta` interno de Roundcube es **por abogado** (hay que conocerlo por
cuenta). **Este componente es explícito, no un parámetro con default.**

### 4.3 Capa api-crm (x-api-key, sin handshake)

- **Tipos de entidad:** `GET /api/view/relation/mail` → `relationsViews`. En la práctica,
  constante (para procuradores el objetivo es `expedientes_judiciales`); no hace falta en caliente.
- **Buscar/leer expediente:** **reusar `core/procurador_search.py`** (F2). El `id_elemento`
  del camino feliz ya viene de `RobotProposal.expediente_id` (no hay que re-buscar).
- **Carpetas:** **`SudespachoClient.list_gdocu_folders` YA EXISTE** (`sync_sudespacho.py`) y
  ya envía `related_element` + `related_member` con `x-api-key`. **Corrección v1→v2:** el vacío
  histórico NO era por "faltar related_member". El default es `parent=0`; el HAR usó **`parent=1`**
  (raíz "General"). Acción: investigar empíricamente (probar `parent=1` + `related_member` +
  `x-api-key`); si una carpeta destino **vacía** no aparece (dead-end de carpetas vacías, plan
  §8), resolver el `folder_id` por el mapa estático `CARPETA_ID_TO_PATH`/`CRM_TREE`
  (`core/config.py`). `FolderInfo = {folder_id, name, raw}`.

## 5. Flujo end-to-end (un correo confirmado)

1. `get_relaciones(session, message_id)` (Message-ID simple) — ¿ya relacionado con este
   expediente? La respuesta es **HTML** (no estructurada): parsear con guardarraíl. Si ya
   está → no re-relacionar (idempotente), pero ver §6 para el adjuntar.
2. (api-crm, F2) `id_elemento` del expediente confirmado.
3. Resolver `(uid, id_cuenta, carpeta)` del correo en la cuenta del abogado (§4.2) y construir
   `messageIdsEncontrados`.
4. `relacionar(...)` → `mail_id` + adjuntos `[{att_id, nombre_archivo}]`. **Persistir estos
   ids inmediatamente** (§6).
5. F4 (fuera) decide por adjunto: `subir` sí/no (inline→no por defecto) + `nombre_final`.
6. (api-crm) `list_gdocu_folders(...)` (o `CARPETA_ID_TO_PATH`) → `folder_id`.
7. `adjuntar(id_elemento, [{att_id, nombre_final}], folder_id, mail_id=…, message_ids_encontrados=…)`.
8. `get_mails_asignados(...)` — verificación débil (ver §6); preferir re-`get_relaciones`.
9. **Grabar la traza del resultado** (§7) y marcar el correo procesado (F2).

## 6. Idempotencia, reanudación y errores

- **Los ids del adjuntar (`mail_id`, `att_id`) SOLO existen tras el relate.** `get_relaciones`
  no los devuelve. → El orquestador **persiste `mail_id` + lista de `att_id` + `messageIdsEncontrados`
  en cuanto responde el relate**, para poder (a) adjuntar aunque el proceso se reinicie, y
  (b) reintentar el adjuntar sin re-relacionar.
- **Reanudación "ya relacionado":** si `get_relaciones` indica que el correo ya está
  relacionado pero **no hay ids persistidos**, NO se puede adjuntar por esta vía (no hay forma
  documentada de recuperar `mail_id`/`att_id` sin re-relacionar). Caso a enrutar a revisión
  manual (o capturar una acción de lectura que los recupere). Documentar como límite conocido.
- **El adjuntar NO está probado idempotente** → re-postear puede **duplicar documentos**.
  Antes de re-subir, comprobar los adjuntos ya presentes (vía `element_registries/gdocu` por
  nombre) **o** confirmar empíricamente el dedupe server-side con un expediente de prueba.
- **Errores de sesión:** clasificar "sesión/CSRF caducada" como error propio → re-handshake
  (Track 1), distinto de "revisión". El resto → `ok=False` + motivo, sin excepción que tumbe
  el runner.

## 7. Traza del resultado del write (F3, no F2)

`record_decision` (F2) graba propuesta-robot vs acción-humana vs quién/cuándo, pero **no el
resultado del write**. F3 **extiende la traza/estado** con el outcome: `{ok, mail_id, folder_id,
adjuntos_subidos, error}` y un estado nuevo `archivado_en_crm`. Lo exige el requisito duro
§18.9 del plan y lo consume F6 (verificar "el correo consta asignado"). Diseñar dentro del
modelo de datos de la cola, no atornillar después.

## 8. Incógnitas parametrizadas (a fijar en la validación temprana del plan)

1. Verificación exacta del `Message-ID` robot↔cuenta-abogado — **CERRADA v2** (idénticos,
   verificado carácter a carácter; el auto-forward de Gmail lo conserva).
2. Composite `messageIdsEncontrados`: forma `<MsgID>,,,{uid}|||RC,,,{id_cuenta},,,{carpeta}`,
   doble-encodeada. Confirmar `id_cuenta` por abogado y que `{carpeta}` refleje la etiqueta
   real (p. ej. "00. PROCESAL") vs INBOX.
3. `_unlock=loading{ts}`: id de lock del UI; presumiblemente no validado por el server.
4. `groups/usersAccessRegister[identifiers][]`: permisos de visibilidad (en el HAR ambos `=2`;
   grupo 2 = EV MMC). Confirmar origen (fijo por tenant vs por expediente) para grupo **y** usuario.
5. `folders/gdocu` con `x-api-key` + `parent=1`: pendiente de probar en vivo.
6. Recuperación de `mail_id`/`att_id` sin re-relacionar (§6): no documentada; capturar si se
   quiere reanudación completa.

## 9. Testing (TDD)

- Sesión Roundcube **fake** que captura `(action, params)` y devuelve respuestas canned con la
  **estructura real del HAR** (ruta anidada `acumulaDatos.mailadjunto[mail_id]`). Riesgo a evitar:
  construir el fixture desde la descripción y no desde el HAR → verde en test, roto en real.
- Casos: relate OK (extrae `mail_id`/`att_id`) · adjuntar OK (params exactos, nombre/carpeta) ·
  adjunto inline/desmarcado no viaja · ya-relacionado → no-op · reintento adjuntar sin re-relate ·
  respuesta de error → `ok=False` · doble-encoding del composite.
- `list_gdocu_folders`: mock inyectando cliente/transport fake (es método de `SudespachoClient`
  con `self._client.get`, **no** `httpx.get` a nivel módulo); asertar `related_element`+`related_member`+`parent`.
- **Lo que los tests NO cubren** (validación en vivo): auth/handshake real, resolución del `uid`,
  validez de `->izq` para no-judiciales, idempotencia real del adjuntar.

## 10. Dependencias y orden

- **Bloqueante para producción, NO para construir el cliente:** Track 1 (handshake). La vía A'
  (automatización) queda **reforzada por v2**: el correo está en Gmail (accesible por IMAP/OAuth)
  y el `Message-ID` es estable, así que resolver el `uid` y localizar el correo es factible; el
  POST al plugin sigue necesitando la sesión Roundcube. Fallback **C** (humano 1 clic) si el
  handshake no es replicable headless.
- **F4** (nombrado + decidir qué subir) consume la salida del relate. Frontera: F4 entrega
  `{att_id?, nombre_final, subir}`; el `att_id` real se conoce **post-relate**, así que el join
  F4↔relate se hace por `nombre_archivo`/orden con **guardarraíl** (verificar conteo, exigir
  unicidad de nombres o coincidencia de orden; si ambiguo → revisión, nunca adivinar).
- **element/permisos:** `RobotProposal` no persiste `element` ni `permisos`. Definir la
  transformación ReviewItem→`plan`: `element` se re-deriva (procuradores → `expedientes_judiciales`);
  `permisos` por default de tenant (grupo/usuario) hasta confirmar §8.4.

## 11. Decisiones abiertas

- **Cuenta de relate:** ¿en la cuenta del abogado que confirma en la bandeja, o una canónica
  (p. ej. la del abogado del expediente)? Afecta a `id_cuenta` y a dónde buscar el `uid`.
- **Alcance de elementos:** **judicial-first** (procuradores actúan en procedimientos).
  Extrajudicial = parámetro sin cablear los params no confirmados; `clientes` **fuera** (F2 lo
  retiró a propósito; YAGNI + gobernanza CLAUDE.md).
- Idempotencia del adjuntar (§6): confirmar vía prueba antes de habilitar reintentos automáticos.

## 12. Higiene

HAR y cabeceras usados en el análisis contienen PII real: **no se commitean** (gitignored) y se
borran tras el análisis. El spec usa placeholders (Message-ID, uid, ids, nombres). Relates/adjuntos
de prueba en el CRM se limpian (hecho por Nikolai el 2026-07-19).
