---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-19
revision: v5 (2026-09-07 — medido con escrituras: el adjuntar duplica, y la verificación va por el lado del expediente)
topic: Intake procuradores F3 — escritura en el CRM (relate + adjuntar)
relacionado:
  - docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md (§7, §15 F3)
  - docs/INTEGRACION_SUDESPACHO.md (§10.10 — SSOT del contrato)
  - docs/DEAD_ENDS.md (Módulo de correo nest-mail/Roundcube)
  - docs/superpowers/specs/2026-07-19-intake-miniapp-entrega-design.md (entrega; su §5 queda afectada)
  - 2026-07-19-f3-relate-crm-r1-adversarial-review.md (acta de la R1; adjudicada en §12)
---

# Diseño — F3: escritura en el CRM (relate correo↔expediente + adjuntar)

> Fase F3 del intake de correos de procuradores. F1 (matcher) y F2 (bandeja) están
> MERGEADAS y corren en dry-run. Esta fase añade la escritura real.

## 0. Cómo llegó este documento a la rev. 5, en tres correcciones y una lección de método

**Rev. 1 y 2 (julio):** un HAR mostró que el «Asignar a elemento» del webmail lo ejecuta un
plugin de Roundcube, y de ahí se concluyó que **la API REST no permitía escribir**.
`MailRoundcube` llegó a marcarse «candidato descartado» en `DEAD_ENDS` **sin haberlo llamado
nunca**, estando declarado en `/api/docs.json` —público, y ya versionado en el atlas de este
repo— todo el tiempo. Un HAR prueba *qué hace la interfaz*, no *qué permite la API*.

**Rev. 3 (2026-09-07, mañana):** medido que los cinco endpoints REST existen, autentican con
la `x-api-key` de siempre y **escriben**, con `cookies`/`dataHash` vacíos. Conclusión escrita
entonces: el webview sobra. **También era falsa, y por el mismo vicio**: se midió sobre los
correos que el CRM ya tenía indexados y se generalizó al resto.

**Rev. 4 (2026-09-07, tarde) — lo que de verdad pasa, medido en campo:** la vía REST **solo
opera sobre correos que el CRM ya tiene en su tabla `mail`**, y un correo entra en esa tabla
**cuando se le hace el primer relate desde el webmail**. Sobre un correo nuevo, el relate REST
devuelve `200` y **no escribe nada**. El resultado no es «REST sí» ni «REST no», sino un
reparto (§1).

**Rev. 5 (2026-09-07, noche) — lo que dijeron las ESCRITURAS.** Las tres incógnitas que el §8
declaraba sin probar se midieron contra los expedientes de prueba 636 y 683: el relate REST
escribe y verifica sobre un correo indexado; **el adjuntar DUPLICA** si se le repite el POST; y
re-postear el relate sí devuelve el manifiesto de un correo ya relacionado. Y apareció lo que
ninguna ronda había mirado: **`findRelations` da una vista POR COPIA** mientras la relación que
escribe es **global**, así que el contrato de verificación del §4 daba **falso negativo sobre una
escritura buena**. La rev. 5 lo corrige (§4.1) y **revierte la adjudicación de H-05** (§12).

La lección que queda, y que ya está en `DEAD_ENDS`: **medir sobre una población y concluir
sobre otra** es el mismo error las tres veces, cambiando la población.

**Y una cuarta, sobre el instrumento en vez de la población.** El hallazgo del §4.1 salió de que
la primera medición de esa sesión —escrita contra un atributo que no existe,
`Relaciones.relacionados`, cuando el campo es `pares`— **solo podía devolver «cero relaciones»**, y
su salida se publicó como refutación del §2.8. Un instrumento que no puede dar el otro valor no
mide nada. La regla que faltaba, y que ahora está escrita: **si una medición propia refuta algo
que ya se midió en campo, el sospechoso por defecto es el instrumento**, y no se publica sin un
control positivo que le haya visto dar el otro valor.

## 1. El reparto (lo que este diseño construye)

| Paso | Quién lo hace | Cómo |
|---|---|---|
| **Primer relate** de un correo entrante | **el webmail, con sesión viva** | `fetch` al plugin **desde el origen `roundcube.sudespacho.net`** |
| Completar adjuntos, renombrar, carpeta | FeesDefender | REST `x-api-key` |
| Anti-duplicado, verificación, traza | FeesDefender | REST `x-api-key` |

**Lo que la rev. 4 sí simplifica frente a la rev. 2:** el `fetch` **no** hay que inyectarlo en
un iframe cross-origin ni regenerar el `dataHash`. Basta abrir `roundcube.sudespacho.net` en
su propio origen con la sesión del navegador viva: ahí `rcmail.env` es accesible y trae todo
lo que el composite necesita. **Verificado en vivo el 2026-09-07** (§2.9). El token de sesión
no tiene que salir del navegador: la petición se construye y se lanza dentro de la página.

**Entra:** el cliente REST de las cinco operaciones; el anti-duplicado; la verificación por
relectura; la traza del resultado. **NO entra:** nombrado LLM y decisión de qué subir (F4),
grabaciones (F5), control de calidad (F6).

## 2. El contrato, medido

Host `api-crm-commons-pro.sudespacho.biz`, header **`x-api-key`**, JSON. Detalle literal en
`INTEGRACION_SUDESPACHO.md §10.10`.

| Operación | Petición | Respuesta |
|---|---|---|
| Leer relaciones | `GET /api/mail/findRelations/{base64(Message-ID)}?account={n}` | `{elemento: {relacionados: {id: {…}}}}` |
| Anti-duplicado en lote | `POST /api/mail/findAssigned` · `{messageIds:[…], account}` | array de los ya asignados |
| ¿Trae adjuntos? | `POST /api/mail/attachments` · `{messageIds:"<str>", account}` | `{hasAttachments: bool}` |
| **RELATE** | `POST /api/mail/relate/selected` · `{messageIds, relatedMembers, relatedElement, cookies, dataHash}` | `acumulaDatos.mailadjunto[mail_id] = [{id, nombre_archivo, enlace}]` |
| **ADJUNTAR** | `POST /api/mail/relate/attachments` · `{datosRelacionados, datosAdjuntos, folderId, messageIds}` | `{status:"success"}` — **siempre**, ver §4 |

1. **`cookies`/`dataHash` se exigen presentes y funcionan vacíos** — pero **solo sobre correos
   ya indexados** (§2.8). Es comportamiento observado, no contrato prometido.
2. **`relatedElement` va SIN el sufijo `->izq`** en REST. Con él → 500. *(El plugin sí lo
   lleva: son dos superficies distintas.)*
3. **El relate devuelve `mail_id` y los `att_id`** en `acumulaDatos.mailadjunto`, en JSON. El
   encadenado relate→adjuntar se conserva, y **volver a llamarlo es la única vía conocida de
   recuperar los `att_id`** de un correo ya relacionado: es idempotente en la relación.
4. **`uid` del elemento `mail` ES el Message-ID RFC** (39/40 en muestra; el filtro discrimina
   1 sobre 462.414). El `mail_id` se recupera releyendo, sin re-relacionar.
5. **`account` = el campo `cuenta` del elemento `mail`**, y determina el buzón donde se busca.
   Cuenta `0` (noreply) → 400. Cardinalidad medida: **0 de 12 Message-ID tienen más de un
   registro** — el CRM indexa una copia, no una por buzón. Aun así el cliente exige unicidad y
   manda a revisión si hubiera varias.
6. **El Message-ID vale con y sin `<>`.** Encaja con lo que `gmail_source` guarda pelado.
7. **`hasAttachments` cuenta también los inline** (un correo dio `true` con `mailadjunto`
   vacío). Da `false` cuando toca, comprobado: no es inerte, es que **son dos preguntas
   distintas**. Para decidir qué subir vale el `mailadjunto` del relate.

### 2.8 La frontera: solo lo indexado — **el hecho que gobierna el diseño**

Prueba discriminante del 2026-09-07, con dos correos reales:

| Correo | ¿Registro en `mail`? | `hasAttachments` | relate REST |
|---|---|---|---|
| ya relacionado antes | sí | `true` | escribe ✅ |
| entrante nuevo, sin relacionar | **no** | `false` | **200 y no escribe** ❌ |

Y la transición, medida sobre el mismo Message-ID: **antes** del relate del webmail,
`resolver_cuenta → None` y `hasAttachments → False`; **después**, `→ 15` y `→ True`.

Dos hipótesis se descartaron por el camino y conviene dejarlas escritas para que nadie las
repita: no era el **auto-envío** (un correo entrante puro tampoco entra), ni un **retardo de
indexación** (no entra por esperar). Entra **al relacionarlo desde el webmail**.

**CONFIRMADO por censo el 2026-09-07 (rev. 5), y con nombre y apellidos.** Sobre 32 correos de
`procesal@` de cuatro días: **23 indexados, los 23 con relación** a su `expedientes_judiciales`;
**0 indexados sin relación**; 0 errores de lectura; 9 sin fila `mail` (comprobado `filas=0`, no
multicuenta). Y `id_creador` lo cierra: **las 23 filas de la cuenta 20 las creó el usuario 23 =
ANA VELASTEGUI**, y su `fecha_creacion` sigue una jornada de trabajo —filas del 09-07 entre 08:36
y 16:43 para correos **enviados el 09-04**—, no la llegada del correo. O sea: **indexado ⟺ una
persona lo relacionó**, y los 9 que faltan son su cola pendiente (uno de ellos en la carpeta de
SPAM, que probablemente no vio).

⚠️ **Y una advertencia para quien vuelva a medir esto.** En esa misma sesión se «refutó» este §2.8
con un script cuya línea de conteo leía un atributo inexistente (`Relaciones.relacionados`, cuando
el campo es `pares`) y por tanto **solo podía imprimir «cero relaciones»**. De esos ceros salieron
además dos conclusiones falsas —un «retardo de indexado de 5-7 h» y una «minoría misteriosa»—, y
las dos se disolvieron al medir bien. **Ninguna refutación de este párrafo vale sin un control
positivo** que haya visto al instrumento devolver el otro valor.

### 2.9 Lo que el webmail expone, en su propio origen (verificado 2026-09-07)

Abriendo `https://roundcube.sudespacho.net/` con la sesión viva del navegador, `rcmail.env` es
accesible y trae:

- `sudespacho_id_cuenta` — **el mismo id que el campo `cuenta` del elemento `mail`**
  (medido: 15 = `nikolai.tyukhay@tyukhay.legal`). Cierra la incógnita de la rev. 2.
- `sudespacho_message_ids` — mapa **`{uid IMAP: Message-ID}`** de los mensajes listados: de
  ahí sale el `uid` del composite sin búsqueda IMAP propia.
- `mailbox` (p. ej. `INBOX`) y `request_token` (CSRF).

Composite del plugin: `<MsgID>,,,{uid}|||RC,,,{id_cuenta},,,{carpeta}`, **doblemente
URL-encodeado** (solo ese campo). Relate ejecutado así en vivo → 200 con su `mailadjunto`.

### 2.10 `expedientes_judiciales` — medido (2026-09-07)

Punta a punta contra el **judicial de prueba 683** (`330/2026`, ref «PRUEBA - BORRAR»), con el
orquestador y relate real (`ya_estaba=False`):

- **`relatedElement: "expedientes_judiciales"` se acepta.** `expedientes_judiciales->izq` y el
  alias `judiciales` dan **500** — la misma regla que en extrajudicial: el slug canónico, pelado.
- El censo del gestor documental con `left.expedientes_judiciales.id` **discrimina**.
- Las **carpetas son las mismas** del tenant: `312 = DOCUMENTOS` sirve igual.
- Relación creada, documento subido con su nombre final a la carpeta pedida, **y el
  extrajudicial 636 intacto**: sin contaminación cruzada.

**Y un hallazgo que no se buscaba: las relaciones son multi-elemento, y la idempotencia tiene
que ser por PAR.** El correo ya constaba en `extrajudiciales:636` y aun así se relacionó con
`expedientes_judiciales:683`; ambas conviven. Si el pre-chequeo mirase «¿tiene alguna
relación?» en vez de «¿tiene **esta**?», habría contestado «ya estaba» y no habría archivado
nada — y un correo puede pertenecer a dos asuntos a la vez. Fijado con test y mutante.

## 3. Arquitectura

### 3.1 `core/procurador_relate.py` — cliente REST

```
buscar_relaciones(message_id, account)          -> Relaciones
filtrar_ya_asignados(message_ids, account)      -> set[str]
tiene_adjuntos(message_id, account)             -> bool
resolver_cuenta(message_id)                     -> str | None
relacionar(message_id, element, miembros, account) -> RelateResult
adjuntar(element, miembro, mail_id, seleccion, folder_id, message_id) -> AdjuntarResult
archivar(message_id, element, miembro, adjuntos, folder_id, account)  -> ArchivoResult
```

Transporte: un cliente con la interfaz de `httpx.Client`; en producción el de
`SudespachoClient`, que ya lleva la `x-api-key`. Los tests inyectan un fake con la **forma real
medida**. Nada de webview en este módulo: lo que necesita sesión vive fuera.

### 3.2 Resolución de la cuenta

Por **lectura** del elemento `mail` filtrando por `uid = <Message-ID>`; su campo `cuenta` es el
`account`. **Devuelve `None` si hay cero o más de una coincidencia**, y entonces el correo va a
revisión: no se adivina.

**Un `None` aquí significa las más de las veces «el CRM no conoce este correo todavía»**
(§2.8), no «error». Es la señal de que le falta el paso del webmail.

### 3.3 Carpeta del gestor documental

`/api/folders/gdocu/{parent}` **con `parent=1`** sí lista las carpetas del tenant (medido:
`1 General`, `306 CIVIL`, `311 PENAL`, `312 DOCUMENTOS`, `63 Documentacion RGPD LOPD`). Con
`parent=0` devuelve `[]`, que es de donde salió el «dead end de carpetas» del plan §8.
Respaldo: `CARPETA_ID_TO_PATH`/`CRM_TREE` en `core/config.py`. Por defecto **1 (General)**.

## 4. La regla que gobierna esta pieza: verificar por resultado

**`relate/attachments` devuelve `{"status":"success"}` con los tres parámetros vacíos**, y
**`relate/selected` devuelve 200 con un miembro inexistente** y sin escribir. Los dos son
instrumentos que no pueden dar el otro valor. De ahí, y no de una preferencia de estilo:

- El adjuntar se verifica **por censo del gestor documental** antes/después, por nombre.
- El relate se verifica **releyendo `findRelations`**.
- Ningún `ok` del módulo se deriva de un código de estado. Y `verificado` es campo aparte de
  `ok`: un write con 200 cuya relectura no confirma tiene que poder distinguirse en la traza.
- Si el censo **no se puede leer**, el resultado es **indeterminado**, ni éxito ni fallo: un
  fallo invitaría a reintentar y reintentar podría duplicar (§8.2).

Esto no es teórico: en la primera prueba de campo el relate devolvió 200 sin escribir y la
guarda lo cazó.

### 4.1 La relectura va por el lado del EXPEDIENTE, no del correo (medido, rev. 5)

`GET /api/mail/findRelations/{base64}?account={n}` devuelve las relaciones de **esa COPIA** del
correo, no las del correo. Y un mismo Message-ID vive como **N filas `mail`, una por cuenta**:
medido el 2026-09-07 sobre tres correos, **tres copias cada uno** en las cuentas 11, 13 y 15, con
el `expedientes_judiciales` colgando de **una sola** de las tres. Es `procesal@` como lista de
distribución: una cuenta de correo del CRM por persona, una fila por cuenta, y quien archiva lo
hace sobre su propia copia.

La relación que el relate escribe, en cambio, es **global**. Medido sobre el 683: relacionar la
copia de la cuenta 15 la hace visible desde el expediente, y relacionar después la copia de la
cuenta **2** con el **mismo** miembro **no añade nada** — el CRM devolvió el **mismo `mail_id`
(439232)** desde las dos cuentas y el expediente se quedó en dos correos. De ahí dos conclusiones
de signo opuesto:

- **NO hay riesgo de duplicar la relación.** El CRM la clava a la identidad del correo, no a la
  copia. La idempotencia por par `(elemento, id)` no necesita además cruzar las copias.
- **SÍ hay falso negativo.** La relectura desde la cuenta 2 seguía devolviendo `pares=[]`, así que
  `relacionar()` respondió `ok=False` con el motivo *«el CRM respondió 200 pero la relectura no lo
  verifica; ¿existe el miembro?»* — y el miembro existía, y la relación estaba escrita. Un
  reintento guiado por ese diagnóstico **no converge nunca**, y el motivo señala a la causa
  equivocada.

**Corolario de diseño, que esta revisión cambia:** el relate se verifica leyendo el
**expediente** —`GET /api/related_register/{elemento}/{id}` → bloque `mail`, que es la vista
global— y no el correo por cuenta. Esa ruta **ya estaba cableada en el repo**
(`core.sudespacho_relations.get_relaciones`, `INTEGRACION_SUDESPACHO §15.5`, lo consume
`scripts/crm_ficha.py`): F3 se construyó con la lectura por correo sin que nadie comparase las
dos superficies.

## 5. Flujo end-to-end

1. **Anti-duplicado en lote**: `filtrar_ya_asignados([...], account)`.
2. Resolver `account` (§3.2). Si `None` → **revisión**: al correo le falta el paso del webmail.
3. `buscar_relaciones` — ¿ya relacionado **con este expediente**?
4. `relacionar(...)` → `mail_id` + adjuntos. Verificar por relectura.
5. **Si ya estaba relacionado, NO se da por archivado** (§8 / R1-H-01): se re-pide el
   manifiesto —el relate es idempotente— y se sigue al adjuntar, que decide por censo qué
   falta de verdad. *Este caso ocurrió en la primera prueba de campo: el correo constaba
   relacionado y el documento no estaba subido.*
   **MEDIDO el 2026-09-07 (rev. 5):** el mecanismo funciona. `_post_relate` sobre un correo ya
   relacionado devolvió `mail_id=464006` y el manifiesto `[('183918', 'PREUBA - ADJUNBTAR -
   BORRAR.docx')]`. Ojo al nivel: **`relacionar()` NO sirve para esto** —corta en seco con
   `ya_estaba=True` y manifiesto vacío—, y por eso `archivar()` llama a `_post_relate`
   directamente. Quien llame al nivel de arriba esperando el manifiesto se lleva una lista vacía
   y puede leerlo como «no hay adjuntos».
6. F4 (fuera) decide `subir` y `nombre_final`.
7. Resolver `folder_id`.
8. `adjuntar(...)` solo con lo seleccionado y lo que no esté ya presente.
9. Verificar por censo (§4).
10. Grabar la traza (§6) y marcar procesado (F2).

## 6. Traza del resultado

`record_decision` (F2) graba propuesta-robot vs acción-humana vs quién/cuándo. F3 **extiende**
ese modelo con `{ok, verificado, mail_id, folder_id, adjuntos_subidos, error}` y el estado
`archivado_en_crm`. Lo exige el requisito duro §18.9 del plan y lo consume F6.

**El destino es un par, no un número.** `RobotProposal` y `HumanAction` llevan desde la rev. 4
el campo `element`, y `destino_efectivo(proposal, action)` devuelve `(elemento_canónico, id)` o
`None`. Un id sin elemento es ambiguo —el extrajudicial 636 y un judicial 636 son expedientes
de clientes distintos— y **un elemento ausente no se completa con un default**: va a revisión.
Los ítems confirmados en dry-run, anteriores al campo, caen ahí a propósito.

## 7. El webmail, que sigue en el camino crítico

No es plan B: es el **paso 0** de todo correo entrante nuevo (§1, §2.8). Lo que cambia respecto
de la rev. 2 es su forma, que es mucho más simple de lo que se temía:

- **No hace falta iframe.** `roundcube.sudespacho.net` en su propio origen, con la sesión del
  navegador, expone `rcmail.env` entero.
- **No hace falta regenerar el `dataHash`** ni tocar credenciales IMAP. Sigue descartado
  reproducir la sesión headless (`DEAD_ENDS`).
- **El token no tiene que salir del navegador**: la petición se construye y se lanza dentro de
  la página.
- **Alternativa a medir:** pasar `cookies`+`dataHash` capturados al endpoint REST
  `relate/selected`. Es lo que el esquema pide, y explicaría por qué los pide. **No probado.**

**El spec de entrega queda afectado** y hay que revisarlo (H-11): la miniapp sigue necesitando
un navegador, pero solo para este paso.

## 8. Lo que NO está probado, dicho por delante

1. ~~Que `cookies`/`dataHash` **vacíos** sigan valiendo sobre correos indexados~~ — **MEDIDO
   el 2026-09-07 (rev. 5)**: escriben, y la relectura lo confirma (`ok=True verificado=True` al
   relacionar contra el judicial de prueba 683). Se retira de esta lista.
2. ~~**La idempotencia del adjuntar**~~ — **MEDIDA el 2026-09-07 (rev. 5): el CRM DUPLICA.** El
   mismo `att_id`, el mismo nombre final y el mismo `mail_id`, posteados dos veces a
   `relate/attachments`, dejan **dos documentos** en el gestor documental: censo del 636 3 → 4 →
   5, con el nombre repetido. Los dos POST contestaron `{"status":"success","errors":[]}`.
   **Consecuencia de diseño:** la guarda por censo de `adjuntar`
   (`pendientes = [… if n not in antes]`) es **PORTANTE**, no cinturón de seguridad — quitarla
   duplica un documento en el expediente de un cliente. Y su punto débil queda declarado:
   **filtra por NOMBRE FINAL**, así que dos nombres distintos para el mismo adjunto la esquivan y
   el documento entra dos veces. Con la idempotencia del CRM ya medida, la vía limpia para cerrar
   ese hueco es filtrar además por `att_id` ya subido, no solo por nombre.
3. ~~`expedientes_judiciales` sin medir~~ — **MEDIDO el 2026-09-07** (§2.10). Se retira de esta
   lista.
4. **Pasar `cookies`+`dataHash` reales al endpoint REST** (§7): no probado.
5. **Escritura incierta** (timeout tras escribir): no hay protocolo de reconciliación. R1-H-03.
6. **Dos escritores a la vez**: no hay exclusión ni clave de idempotencia remota. R1-H-04.
7. **Contenido binario del adjunto**: se verificó nombre y carpeta, no los bytes.
8. **Por qué el corpus tiene dos regímenes.** Los correos históricos son de **copia múltiple**
   (ctas 11/13/15) **y traen relación de ficha** (`procuradores_propios`, en las tres copias, que
   es lo que hace `autoassign`); los de esta semana son de **copia única** en la cuenta 20 y **sin**
   relación de ficha. Las dos cosas cambiaron a la vez. **La causa no está medida** y no se supone:
   importa porque F3 tiene que ser correcto sobre el corpus que existe, no solo sobre el de esta
   semana.
9. **Hay filas `mail` cuyo `uid` NO es un Message-ID.** Medido: `uid=1908692`, con `cuenta`
   vacía. Todo el direccionamiento de F3 asume `uid = Message-ID` («39/40 en muestra»); ese 1/40
   tiene ahora una forma concreta, y `resolver_cuenta()` no puede encontrarlo nunca.

**Ya no está aquí, porque se midió:** la visibilidad (§8.4 de la rev. 3). El CRM **deriva los
permisos solo** — grupo «Oficina del Despacho Principal» (id 2) y usuario = **el titular del
buzón desde el que se archiva** (cuenta 20 → `ana.velastegui`, cuenta 15 → `Nikolai_Tyukhay`).
Es una propiedad del diseño, no un detalle: **el correo hereda la visibilidad del buzón**, así
que la cuenta desde la que se archiva decide quién lo ve. Falta fijar el criterio de aceptación
(R1-H-10).

⚠️ **MATIZADO el 2026-09-07: esta frase habla de UNA de las dos superficies, y leída sola
engaña.** Explicado por Nikolai: en **Roundcube** la visibilidad va por el buzón —un correo que
llegó a la cuenta de Ana no lo ven los otros tres, nadie entra al webmail de otro—; pero **a
través del expediente** lo ve **todo el equipo con acceso a ese expediente** en cuanto el correo
está relacionado. Las dos cosas son ciertas a la vez. Corolario que no estaba escrito:
**relacionar es el acto que hace el correo visible al equipo**, no solo el que lo archiva. Detalle
en `2026-09-07-f3-cableado-bandeja-y-verificacion-design.md` §5.1.

## 9. Testing

Transporte fake, sin red. Casos cubiertos: relate OK · `relatedElement` sin `->izq` ·
`findAssigned` con `account` y en array · Message-ID con y sin `<>` · base64 en la ruta ·
cuenta ambigua → revisión · ya-relacionado con documentos pendientes → **los completa** ·
documento ya presente → no re-sube · censo ilegible antes o después → indeterminado ·
**`success` sin cambio en el censo → `ok=False`** · join ambiguo → revisión.

**Arnés de mutación:** cada aserto que sostiene el diseño se comprueba matando a su mutante
(un test verde recién escrito no prueba nada hasta que se le ve ponerse rojo). El arnés juzga
por **código de salida**, no por una subcadena de la salida — un arnés que da el mismo
resultado para todos los mutantes está roto, y el primero lo estaba.

## 10. Dependencias y orden

- **F4** consume la salida del relate. El join F4↔relate se hace por `nombre_archivo` con
  guardarraíl: nombre que no casa o homónimos → **revisión, nunca adivinar**. El orden **no**
  se acepta como sustituto de identidad (la rev. 3 lo permitía; R1-H-08).
- **Alcance:** judicial-first pendiente de §8.3. `clientes` fuera.

## 11. Higiene

Los HAR no se commitean. Este spec usa placeholders salvo los expedientes de prueba **636**
(extrajudicial) y **683** (judicial), que son del propio despacho. **Residuos deliberados, no
borrados** (en el CRM no se borra sin autorización expresa de Nikolai):

- **636** — de la mañana del 2026-09-07: cinco correos relacionados y los `gdocu` `42865`,
  `42870` y `42871`. De la tarde (rev. 5, prueba de idempotencia del §8.2): **dos copias** de
  `ZZ BORRAR test idempotencia adjuntar 2026-09-07.docx`, que son justamente el resultado que se
  quería medir. Censo del 636 al cerrar: 5 documentos.
- **683** — la relación con un correo de marketing ajeno a cualquier caso (`mail_id` 439232,
  asunto «INMATIC, empieza tu periodo de Prueba»), elegido a propósito por no contener dato de
  cliente. Censo al cerrar: 1 documento, 2 correos relacionados.

El slug del extrajudicial es **`extrajudiciales`**; `expedientes_extrajudiciales` devuelve censo
ilegible (`None`), que con la guarda del §4 se traduce en «indeterminado» y no en un falso cero.

**Decisión de Nikolai (2026-09-07): los residuos SE QUEDAN.** El 636 y el 683 siguen siendo banco
de pruebas y habrá más escrituras; los borrará él **al terminar**, de una vez. Así que **nadie los
limpia por iniciativa propia** —ni por celo de higiene ni al pasar por aquí—, y el censo de esos
dos expedientes **no es un indicador de nada** mientras esta línea siga en pie: cualquier medición
que los use tiene que tomar su propia foto previa, como hizo la rev. 5.

## 12. Adjudicación de la revisión adversarial R1 (Codex, 2026-09-07) — NO-SHIP, parcial

- **Objeto revisado:** `docs/superpowers/specs/2026-07-19-f3-relate-crm-plugin-roundcube-design.md` rev. 3, commit `01d9060`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-07-19-f3-relate-crm-r1-adversarial-review.md`
- **Hallazgos:** 10 confirmados · 1 rebajado · 0 refutados · 0 escalados · 0 sin verificar *(H-05 revertido de «refutado» a «confirmado» el 2026-09-07 con medición; ver más abajo)*
- **Remediado en:** rev. 4 y rev. 5 de este documento

Ronda sobre el **diseño**, antes de construir. El revisor corrió sin red sobre una copia
congelada; el `sha256` del objeto coincide al abrir y al cerrar. Adjudicado contra la fuente:
tres hallazgos se midieron en vivo, cosa que él no podía hacer.

| Hallazgo | Sev. | Veredicto | Dónde se remedia |
|---|---|---|---|
| H-01 · «asignado» ≠ «archivado completo» | CRÍTICO | **confirmado** | §5.5 y el código: `ya_estaba` re-pide el manifiesto y completa. **Ocurrió en la primera prueba de campo** |
| H-02 · el censo no identifica la escritura | CRÍTICO | **confirmado** | §4: censo por nombre, y censo ilegible ⇒ indeterminado |
| H-03 · sin protocolo para escritura incierta | ALTO | confirmado | declarado en §8.5; no se cierra en esta fase |
| H-04 · comprobar antes no excluye dos escritores | ALTO | confirmado | declarado en §8.6 |
| H-05 · multicuenta del mismo Message-ID | ALTO | **CONFIRMADO** — *revertido el 2026-09-07* | §4.1: tres copias medidas (ctas 11/13/15). No duplica la relación; **rompe la verificación** |
| H-06 · el destino no era inequívoco | CRÍTICO | **confirmado** | §6 y el código: `element` en la terna + `destino_efectivo` |
| H-07 · la traza colapsa adjuntos homónimos | ALTO | confirmado | declarado; F3 no adivina (`_emparejar` → revisión) |
| H-08 · el join por orden | ALTO | confirmado | §10: solo identidad, nunca orden |
| H-09 · generalizaciones presentadas como medidas | MEDIO | **confirmado, y con razón de más** | §0 y §2.8: la rev. 3 generalizaba de lo indexado a todo |
| H-10 · la visibilidad sin criterio | ALTO | rebajado | medido: el CRM deriva los permisos (§8) |
| H-11 · documentos hermanos sin reconciliar | MEDIO | confirmado | §7 y el plan; el spec de entrega queda pendiente |

**H-09 merece una nota, porque el revisor acertó más de lo que él mismo podía saber.** Dijo que
la rev. 3 saltaba de la observación a la propiedad del sistema «repitiendo en menor escala el
salto criticado en §0». No tenía red para probarlo. Cuatro horas después, la prueba de campo
demostró que **el salto era exactamente ese**: `cookies`/`dataHash` vacíos valían sobre lo
indexado y se escribió como si valieran siempre.

**H-05 se REVIRTIÓ, y el motivo importa más que el hallazgo.** La rev. 4 lo cerró como
«refutado en su premisa» con la nota *«medido 0/12»*. El 2026-09-07 se midió otra vez y salió
**3 de 3**: tres Message-ID con tres filas `mail` cada uno, en las cuentas 11, 13 y 15. Los 12
de la primera medición eran todos de copia única —correos de esta semana, cuenta 20—, así que la
muestra **no podía** mostrar el fenómeno: es el mismo error de método que el §0 denuncia dos
párrafos más arriba, cometido dentro de la propia adjudicación que lo denunciaba.

Lo que sí cambia respecto de lo que el revisor temía: la consecuencia. Él apuntaba al riesgo de
**elegir el buzón a ciegas**; el guardarraíl de unicidad del §3.2 cubre eso y se mantiene. El
daño real, que ninguno de los dos vio, es que **la verificación por relectura queda acotada a una
copia** mientras la escritura es global (§4.1). O sea: el hallazgo era correcto, mi refutación era
falsa, y la razón por la que era importante no era la que él dio ni la que yo negué.

**Divergencia declarada:** se acepta el veredicto —el diseño rev. 3 no era apto para
construirse tal cual—. No se acepta el encuadre de que la vía REST quede en entredicho; el
propio informe lo dice: «no hay base para refutar REST por esos defectos». Lo que estaba mal
era el contrato de seguridad alrededor de la escritura, y el alcance que se le atribuyó.
