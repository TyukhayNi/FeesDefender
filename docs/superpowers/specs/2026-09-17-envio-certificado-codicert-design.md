---
tipo: spec
estado: vigente
creado: 2026-09-17
objeto: envío certificado de burofax y OVC por la API de Codicert (Servicios de MailCertificado S.L.)
rev: "4"
---

# El requerimiento sale solo: burofax, correo y SMS por la API de Codicert

Encargo de Nikolai del **2026-09-17**: los burofaxes y las OVC ya preparados —el PDF sale del
CRM— tienen que salir por **codicert.io** por los **tres canales a la vez**: burofax postal,
correo electrónico y SMS, **a todos los requeridos**. Dos requeridos son dos correos y dos SMS
si constan; y **un burofax por domicilio distinto**. Al terminar, hay que **descargar los
certificados** y producir la versión **aportable** como prueba.

> **Rev. 4 (2026-09-17).** Segunda tanda de medición sobre la UI del sandbox: se cierran los
> huecos **1**, **4** y **8**. El 8 destapa un defecto que habría reventado en producción —**siete
> provincias del CRM no existen con ese nombre en Codicert**, y una es Valencia—; el 1 dice que
> **el texto del SMS no es configurable**, así que el literal de `CONVENCIONES` §5 no cabe donde
> se creía.
>
> **Rev. 3 (2026-09-17).** Se cierran por medición los huecos **5** y **7**, a petición de
> Nikolai. El 5 trae una consecuencia que refuerza el hallazgo J-06: el prestador **es cualificado**
> y el art. 326.4 LEC juega, luego romper la firma cuesta más de lo que la rev. 2 suponía. El 7
> **retira un discriminante que la rev. 2 daba por bueno** —el pie por sección, que la plantilla
> viva no tiene— y lo sustituye por uno medido.
>
> **Rev. 2 (2026-09-17).** Reescrito tras la R1 adversarial: **34 hallazgos**, 12 altos, sobre
> tres lentes. Veredicto agregado **REQUIERE-REVISION**. Cambian de raíz el **§3** (la gramática
> del identificador, que antes no existía y hacía que la OVC no saliera nunca), el **§5** (los
> plazos corren por requerido, no por expedición) y el **§6** (el documento se parte en dos PDF).
> Adjudicación en el **§11**; acta literal en
> [`…-r1-adversarial-review.md`](2026-09-17-envio-certificado-codicert-r1-adversarial-review.md).

## 1. El contrato de la API, medido

Documentación en `https://ws.codicert.tk/` (Redoc sobre `rest.json`, OpenAPI 3.0, versión
4.2.1 del prestador). **Las dos bases existen y responden**, verificado por resultado —un
`POST /usuarios/acceso` con credenciales falsas devuelve en ambas el mismo
`400 {"estado":"KO","mensaje":"No se pudo iniciar la sesión…"}`, y una ruta inventada da 404:

| Entorno | Base API | Portal |
|---|---|---|
| Sandbox | `https://ws.codicert.tk/v2` | `https://usuarios.codicert.tk` |
| Producción | `https://ws.codicert.io/v2` | `https://usuarios.codicert.io` |

**Autenticación.** `POST /usuarios/acceso` con `{usuario, clave}` —las mismas del portal—
devuelve una ficha con el token **y su `fecha_vencimiento`**, que el cliente conserva: un token
caducado a mitad de expedición es un fallo evitable.

### 1.1 Los tres canales son DOS endpoints, y esto es lo que más cambia el diseño

| Canal del despacho | Endpoint | Límite duro |
|---|---|---|
| Burofax postal | `POST /envios/burofax` | `destinatarios` array de **exactamente 1**; adjuntos **solo PDF**; `pais` solo `"España"` |
| Correo certificado | `POST /envios/entrega-electronica-certificada` con `tipo_entrega: "correo"` | adjuntos 1..10 |
| SMS certificado | **el mismo endpoint**, con `tipo_entrega: "sms"` | ídem |

Los dos endpoints exigen la cabecera **`x-json-ficheros: 1`** cuando el cuerpo es JSON con
ficheros en base64, que es siempre en nuestro caso. La declaran diez endpoints del contrato y
olvidarla es el error fácil de este formato.

El «SMS» del proceso de la casa **no es** `POST /envios/sms-certificado`. Ese producto existe y
es texto pelado —`cuerpo` más un móvil, sin adjunto—, y no sirve para remitir un documento. Lo
que se usa es la **entrega electrónica certificada notificada por SMS**, que entrega el
documento. De ahí el literal de `CONVENCIONES_DESPACHO.md` §5, *«Consulte el documento
adjunto»*: hay documento que consultar porque el canal lo lleva.

Consecuencia operativa que gobierna todo el motor: **el burofax admite un destinatario por
llamada**. Dos domicilios son dos llamadas, siempre.

**Dónde está de verdad el patrón del móvil** (rev. 2, H-02 de la lente de API). `^[67]\d{8}$`
aparece en exactamente dos sitios del contrato: `DestinatarioPostal.telefono` —el **teléfono de
incidencia del burofax**— y `SolicitudSms`, el producto que no usamos. En
`DestinatarioVerificable`, que es el destinatario de la entrega electrónica certificada, **no hay
patrón ninguno**. La rev. 1 lo atribuyó al canal equivocado y su regla habría detenido planes
correctos: el destinatario SMS real del §2, `34645508869`, lleva prefijo internacional y no casa
ese patrón. Regla que queda: se normaliza el móvil y se valida su forma, pero **el patrón estricto
se aplica solo donde el contrato lo exige**, y el prefijo `34` se acepta.

### 1.2 El resto de la superficie que se usa

```
GET  /envios                               listado paginado (100 máx. por página)
GET  /envios/{IdEnvio}/estados             histórico de estados certificados
GET  /certificados/comunicacion/{IdEnvio}  el certificado, en PDF
GET  /certificados/eml/{IdEnvio}           el EML de la comunicación
GET  /envios/{IdEnvio}/adjuntos/{Adjunto}  el adjunto tal como se envió
GET  /usuarios/credito                     crédito del usuario
```

`GET /envios` **no filtra por `id_personalizado`** —probados cinco parámetros de búsqueda, los
cinco devuelven el total sin filtrar— pero **sí acepta `fecha_inicio`, `fecha_fin`, `tipo` y
`estado`**, y cada elemento del listado **devuelve su `id_personalizado`**. Esos dos hechos
juntos son los que hacen viable el §3.5: se acota por fecha y se filtra en casa.

`id_personalizado` **se puede repetir a propósito** entre envíos —lo dice su descripción— y admite
**20 caracteres en cuatro de los cinco productos**. `SolicitudBurofax` lo redefine inline **sin
declarar `maxLength`**, así que el límite del burofax es desconocido: el motor se ciñe a 20 para
todos, que es el suelo seguro.

### 1.3 Los estados: son 37, y el que faltaba es el que cierra

La plataforma documenta **37** códigos (la rev. 1 dijo 43; recontados sobre la documentación
renderizada). Para el despacho cuentan estos, y la frontera entre los tres primeros decide plazos:

| Código | Título | Qué significa para nosotros |
|---|---|---|
| 5 | Procesado | **No es entrega.** Es lo que devuelve el certificado emitido al enviar |
| 27 | Entregado en el servidor | Llegó al servidor del destino; nadie lo ha abierto |
| 17 | Entregado | Entrega acreditada |
| 20 | Leído · Documentación accedida | Acceso al contenido — art. 10.2 |
| **21** | **Recordatorio lectura entregado** | **Entrega acreditada del recordatorio, sin acceso al contenido** |
| 28 | Rechazado | Entrega fallida por rechazo. **Tiene valor afirmativo**, ver §5 |
| 42 / 40 | Fallido / Caducado | Sin entrega |

El **21** faltaba en la rev. 1 y es exactamente donde quedaron **dos de los tres envíos de
producción** que el §2 pone de ejemplo. Sin clasificarlo, una expedición real no cerraría nunca.

Y se repite aquí porque el motor tiene que codificarlo: **«Procesado» no es «Entregado»**.

### 1.4 El coste, que no es simétrico, y el presupuesto de bytes

Tarifa «80» vigente, leída del portal de producción el 2026-09-17:

| Concepto | Precio |
|---|---|
| Envío postal Península (burofax) | **16,9716 €** |
| Entrega electrónica certificada | 0,3867 € |
| — notificación por correo | + 0,4064 € |
| — notificación por SMS | + 0,0834 € |
| Megabyte adicional | 0,0288 € |

Un burofax cuesta **unas veinte veces** el correo certificado y **treinta y seis veces** el SMS.
La regla «un burofax por domicilio distinto» tiene, además del fundamento jurídico, una
consecuencia económica que el plan debe poner delante antes de gastar.

**Los bytes se pagan, y el límite lo dice la UI, no el contrato** (rev. 4, hueco 4 cerrado el
2026-09-17). Los dos endpoints aceptan los ficheros **en base64 dentro del JSON**, lo que añade un
tercio al tamaño en tránsito. El formulario declara: **máximo 6 ficheros, 60 MB en total, y el
precio del producto incluye 1 MB**; por encima, cargo adicional a 0,0288 €/MB. Con dos adjuntos de
un requerimiento normal se está muy por debajo, así que el coste por bytes es ruido — pero el plan
los estima igual, porque el margen del §5.2 tiene que cuadrar.

⚠️ **La UI dice 6 ficheros y el contrato de la API dice `1..10`.** Discrepan, y no se ha medido
cuál manda. El motor se ciñe a **6**, que es el suelo seguro, y el diseño con dos adjuntos cabe de
sobra. El burofax añade dos avisos propios: los PDF deben ir en **DIN A4** o no se asegura la
impresión, y **se eliminan las firmas electrónicas** y marcas de autor del adjunto — irrelevante
para nuestros PDF, que no van firmados, pero conviene que conste antes de que a alguien se le
ocurra adjuntar uno que sí lo esté.

## 2. El proceso real, medido en producción

Cuenta maestra `engelvoelkers` en `usuarios.codicert.io`, **25 subusuarios enumerados** el
2026-09-17 en `/masterusuarios`. Envíos del subusuario `barcelona.bd` del 10-09-2026, referencia
`BCN-OS-008684 - OVC`:

| Hora | Tipo | Destinatario | Estado |
|---|---|---|---|
| 13:05:34 | Burofax | TUV SUD IBERIA, S.A. | Entregado |
| 13:02:57 | Entrega Electrónica Certificada | 34645508869 | Recordatorio lectura entregado |
| 13:01:27 | Entrega Electrónica Certificada | JoseMaria.Arnau@tuvsud.com | Leído |

Tres envíos, tres canales, **un mismo `id_personalizado`**. Ese campo es el hilo que cose la
expedición, y ya se usa así sin que nadie lo hubiera escrito.

**Y la convención de producción lleva el tipo de comunicación dentro**, cosa que la rev. 1 leyó
mal: `BCN-OS-008684 - OVC` es la referencia de la operación **más** el discriminante. La
producción ya había resuelto lo que la rev. 1 dejaba abierto. El §3 lo recoge.

El detalle del burofax confirma el mapeo de la ficha postal: `nombre` es la razón social
(«TUV SUD IBERIA, S.A.»), `a_atencion` la persona («Sr. Jose María Arnau»), y debajo dirección,
población, provincia, CP y el teléfono de incidencia.

### 2.1 El emisor sale del expediente, no se teclea

Decisión de Nikolai del 2026-09-17: **los envíos salen del usuario `.bd` del Market Center**
que reclama, que es lo que ya se hace —el certificado del W-04A6LI salió de `valencia.bd` y el
OVC de TUV SUD de `barcelona.bd`—.

El mapeo es determinista: las **siete ciudades canónicas** de `core/ciudades.py` tienen cada una
su usuario, y **las siete se enumeraron** en el portal el 2026-09-17; no es inferencia. El slug de
la variable de entorno se fija aquí para que nadie lo invente (el caso de San Sebastián, con
espacio y tilde, no admite traducción automática):

| Ciudad (`core.ciudades.CIUDADES`) | Usuario Codicert | Prefijo de variable |
|---|---|---|
| Barcelona | `barcelona.bd` | `CODICERT_BARCELONA_` |
| Bilbao | `bilbao.bd` | `CODICERT_BILBAO_` |
| Madrid | `madrid.bd` | `CODICERT_MADRID_` |
| San Sebastián | `sansebastian.bd` | `CODICERT_SANSEBASTIAN_` |
| Santander | `santander.bd` | `CODICERT_SANTANDER_` |
| Sevilla | `sevilla.bd` | `CODICERT_SEVILLA_` |
| Valencia | `valencia.bd` | `CODICERT_VALENCIA_` |

`ciudades.ciudad_de_equipo()` deriva la ciudad del código de equipo (`BaRS7` → Barcelona) y
devuelve `str | None`. **Cuando devuelve `None`** —código desconocido, expediente sin clasificar—
el plan **no se emite**: se para y se dice qué falta. Lo mismo si la plaza resuelta no tiene
credencial cargada.

## 3. La gramática del identificador

Sección nueva en la rev. 2, y es el hallazgo más grave de la ronda. El `id_personalizado` sostiene
cuatro funciones —identidad de la expedición, clave de la fuente de verdad, clave de la
idempotencia y unidad de agregación del estado— y la rev. 1 **no decía cómo se compone**. Con el
W-code solo, el modo de fallo es silencioso y positivo:

> Día 0, el requerimiento expide seis envíos con `id_personalizado = W-04A6LI`. Día 15, sin
> respuesta, se lanza la OVC. La comprobación de idempotencia encuentra los seis, da cada par
> (canal, destinatario) por hecho y **declara la expedición completa sin que haya salido un byte**.
> El motor informa de éxito.

**La frontera no es «requerimiento contra OVC».** Es *qué distingue dos expediciones del mismo
expediente*: también un segundo requerimiento a un domicilio nuevo, o un reenvío por otro canal
tras una entrega fallida. Por eso el discriminante no es un booleano, es una secuencia:

```
<W-code>-<TIPO><n>
W-04A6LI-REQ1      requerimiento, primera expedición
W-04A6LI-OVC1      oferta vinculante, primera expedición
W-04A6LI-REQ2      segunda expedición del requerimiento (domicilio nuevo, reenvío)
```

Caben: 20 − 8 (W-code) − 1 (guion) = **11 caracteres**, de sobra. `TIPO` es un enum cerrado y `n`
lo calcula el motor contando las expediciones previas del mismo tipo.

**El tipo de comunicación es un parámetro obligatorio de `planificar`**, no un dato derivable del
expediente: el mismo expediente da varias comunicaciones y ninguna propiedad suya dice cuál toca.

## 4. Arquitectura

Tres capas, como el resto del proyecto: CLI → core → CRM/Codicert.

### 4.1 Los módulos

- **`core/codicert.py`** — transporte puro: token con su vencimiento, los dos endpoints de envío,
  estados, certificado, listado, crédito. No sabe qué es un expediente.
- **`core/expedicion_certificada.py`** — la lógica del despacho: planificar, ejecutar, refrescar,
  cosechar.
- **`core/certificado_aportable.py`** — anatomía del certificado, recorte y manifiesto.
- **`core/sudespacho_documentos.py`** — **la subida al gestor documental**, con el contrato del
  §17.1 de `INTEGRACION_SUDESPACHO.md` dentro. Va en la familia `sudespacho_*` aunque este spec sea
  su primer consumidor: no es su dueño, y un cuarto cliente `x-api-key` naciendo dentro del módulo
  de expediciones es exactamente cómo se multiplican los clientes huérfanos.
- **`scripts/codicert.py`** — `plan` · `enviar` · `estado` · `cosechar`.

La lectura de las partes contrarias **no se escribe de nuevo**: `core/sudespacho_relations.py`
ya tiene `get_relaciones(element, exp_id)`, que es exactamente eso.

### 4.2 El puerto de inyección, que es lo que hace probable el diseño

Las cuatro funciones del despacho reciben un **`EntornoExpedicion`** por keyword, con default
real, en la línea del `Entorno` de `scripts/repository_cli.py`:

```
planificar(expediente_id, tipo, *, entorno=...) -> Plan
ejecutar(plan, confirmacion, *, entorno=...)    -> Expedicion
refrescar(referencia, *, entorno=...)           -> Expedicion
cosechar(referencia, *, entorno=...)            -> list[CertificadoCosechado]
```

El `EntornoExpedicion` lleva el cliente de Codicert, el cliente del CRM, el resolutor de
credenciales, el reloj y **la raíz de escritura**. Sin él no hay dónde enchufar un doble, la única
salida es `monkeypatch` sobre bindings de módulo —que es lo que `tests/_barrera.py` existe para
evitar— y, sobre todo, `cosechar` escribiría en el árbol real, que la regla sin escotilla de
`CLAUDE.md` §Tests prohíbe.

`Plan` es una estructura inspeccionable, no un efecto: emisor resuelto **y validado**, entorno,
lista de envíos con canal y destinatario, el documento elegido con su `sha256`, **el asunto y el
cuerpo de cada canal**, coste estimado desglosado, **crédito disponible y margen**, y las
ausencias declaradas.

### 4.3 Dónde vive la verdad, y el rastro que la plataforma no puede darnos

**La fuente de verdad son los envíos en Codicert**, consultados acotando por fecha y filtrando por
`id_personalizado` en casa. La alternativa —un JSON de estado por expediente— se descarta: crearía
una segunda fuente de verdad sobre hechos de la plataforma y mentiría en cuanto alguien enviase
desde el portal.

Pero hay un hecho que **es nuestro y la plataforma no puede contarnos**: que nosotros llamamos.
Antes de cada POST se escribe `(id_personalizado, canal, destinatario, timestamp, en_vuelo)` y se
cierra con el `IdEnvio` al recibir la respuesta. No es una segunda verdad sobre la plataforma; es
el rastro de nuestra intención, y sin él un timeout deja un burofax pagado y sin `IdEnvio`
recuperable, porque el listado no filtra por el único campo que lo identificaría.

**El denominador es el Market Center, no el despacho** (rev. 2). Quien pagina `GET /envios` no ve
los envíos del despacho: ve los de `barcelona.bd`, la cuenta compartida por la que sale todo el bad
debt de la plaza. Ese volumen **está sin medir**, y por eso la consulta se acota siempre por
`fecha_inicio`/`fecha_fin`. Conviene además que conste: esa credencial da al motor **lectura de
todo el tráfico certificado de la plaza**, incluidas comunicaciones ajenas al despacho.

## 5. Quién recibe qué: las reglas del despacho

Entrada: el expediente y el **tipo de comunicación**. Del CRM salen las partes contrarias por
`get_relaciones`, y `clientes_contrarios` tiene los campos necesarios —`nombre`, `1apellido`,
`2apellido`, `direccion`, `poblacion`, `provincia`, `cp`, `email`, `movil`, `nif_cif`—.

1. **Correo y SMS: uno por cada requerido**, con su propio envío. Nunca se agrupan dos requeridos
   en un mismo envío electrónico, aunque el endpoint lo permita: cada uno necesita su acuse.
2. **Burofax: uno por domicilio distinto.** Dos requeridos con el mismo domicilio comparten sobre;
   con domicilios distintos son dos envíos.
3. **Cuando dos requeridos comparten sobre**, ambos nombres van en `nombre`, separados por « Y »,
   y `a_atencion` queda para la persona de contacto. **El certificado acredita entonces la entrega
   en ese domicilio, no la recepción personal de cada uno**, y ese aviso va **en el plan y en el
   manifiesto del certificado**, no solo aquí. Decisión de Nikolai del 2026-09-17, mantenida tras
   la R1: ver §11, H-03 de la lente jurídica.
4. **Lo que falta se declara, no se inventa.** Un requerido sin móvil sale como «sin canal SMS».
   Un requerido **sin ningún canal** detiene el plan.
5. **La ficha se valida entera antes de gastar, no en el 422.** El móvil se normaliza —el prefijo
   va en campo aparte, que es por qué el destinatario real de producción es `34645508869`— y
   `pais` solo admite `"España"`, así que un domicilio extranjero para el burofax se detiene en el
   plan.

   **Y la provincia hay que traducirla** (rev. 4, hueco 8 cerrado el 2026-09-17). Las dos listas
   tienen 52 valores, **45 coinciden y 7 no**: el CRM escribe en castellano lo que Codicert escribe
   en la lengua cooficial. Sin esta tabla, un requerido de la Comunidad Valenciana o del País Vasco
   produce el 422 **a mitad de expedición**, con las electrónicas mandadas y el burofax no.

   | CRM | Codicert |
   |---|---|
   | Alicante | `Alacant` |
   | **Valencia** | **`València`** |
   | Castellón | `Castelló` |
   | Álava | `Araba` |
   | Guipúzcoa | `Gipuzkoa` |
   | Vizcaya | `Bizkaia` |
   | Baleares (Illes) | `Islas Baleares` |

   Valencia es una de las siete plazas, así que esto no es un caso de laboratorio. El contrato de
   la API declara `provincia` como texto libre y es la **UI** la que ofrece la lista cerrada: que
   el servidor rechace un valor fuera de ella está por medir, pero el motor envía lo que la lista
   ofrece, que es el suelo seguro.
6. **El asunto y el cuerpo son literal cerrado**, compuestos por el motor a partir de una plantilla
   de la casa, y **van en el `Plan`** para que el humano los lea antes de gastar. Pueden nombrar el
   objeto de la controversia y la remisión de una oferta vinculante —el art. 9.1 exceptúa
   expresamente «el objeto de la controversia» y el art. 17.4 exige la manifestación de la
   remisión—, pero **no pueden contener términos de la oferta**: ni importe, ni calendario, ni
   quita, ni plazo. El acta del certificado los reproduce y **el acta no se recorta**.
7. **El SMS no lleva texto propio, y eso obliga a revisar el literal de la casa** (rev. 4, hueco 1
   cerrado el 2026-09-17). Medido por tres vías que coinciden: el formulario de entrega electrónica
   certificada **no tiene campo** para el texto del SMS —solo asunto, cuerpo, adjuntos y
   destinatarios—; el contrato de la API tampoco lo expone; y entre los tipos de comunicación
   **personalizables** solo están *Logo*, *Página de lectura*, *Correo de notificación* y *Correo
   de confirmación de firma*: **el SMS no está**. Lo único que se controla es el **nombre del
   remitente** (`de`, 60 caracteres), que es lo que el destinatario lee.

   Consecuencia práctica: el literal de `CONVENCIONES_DESPACHO.md` §5 —«EV MMC SPAIN, S.L.U. le
   remite Oferta Vinculante Confidencial (OVC) y propuesta de negociación extrajudicial. Consulte
   el documento adjunto»— **no se puede poner en el SMS**. Donde sí cabe es en el **correo de
   notificación**, que es personalizable, y en el asunto y el cuerpo. Queda por confirmar el texto
   exacto que compone la plataforma, que se leerá en el primer envío de sandbox.

### 5.1 La puerta humana

`plan` no envía: escribe el plan, lo enseña y termina. `enviar` **replanifica y compara**: si el
plan recalculado difiere del aprobado —destinatarios, domicilios, documento, coste— no manda,
enseña el diff y pide un plan nuevo. El plan va sellado con su propio `sha256` y el del documento.

Y la confirmación **no es un booleano**: `ejecutar` recibe un objeto de confirmación que solo el
CLI sabe construir a partir del plan leído, con el digest dentro. Un `bool` no distingue «un humano
leyó» de «alguien puso `True`», y el §4.1 de la rev. 1 dejaba la puerta a un keyword.

No es ceremonia: un burofax cuesta 16,97 €, y lo que sale por el otro lado es una comunicación
jurídica irreversible.

### 5.2 Idempotencia: el vacío de un listado no autoriza a gastar

`INTEGRACION_SUDESPACHO.md` §17.4 lo tiene medido en este mismo repositorio: una guarda
anti-duplicado que consultaba el listado dijo «aún no está» sobre algo que ya estaba, **y lo subió
dos veces**. Aquí la consecuencia son 16,97 € y dos certificados del mismo requerimiento.

Regla adoptada: **un censo negativo no prueba ausencia**. Si la ausencia no se puede sostener
sobre algo inmediato —el registro de intención del §4.3, que es nuestro y no tiene latencia— el
flujo **se detiene y declara SIN VERIFICAR**, nunca manda. Un `en_vuelo` sin `IdEnvio` para y pide
humano; jamás reintenta solo.

Lo mismo para `cosechar`, que la rev. 1 dejó sin guarda: se comprueba por `origen_id` —clave del
contenido, inmediata— y no por el listado del gestor, cuya latencia es justo la que produjo el
duplicado medido.

**El crédito se contrasta antes de empezar.** `planificar` llama a `credito` y el plan imprime
coste estimado, crédito disponible y margen. Con margen negativo el plan nace **no ejecutable**:
media expedición por saldo insuficiente deja a un requerido requerido y al otro no, y con él dos
fechas distintas para la misma comunicación.

## 6. Del envío a la prueba

### 6.1 Los plazos corren POR REQUERIDO

Corrección de fondo de la rev. 2 (H-08 de la lente jurídica, confirmado contra el literal). Hay
**tres** niveles y la ley usa el de en medio:

| Nivel | Para qué sirve |
|---|---|
| Envío | Operativo: seguir cada canal |
| **Requerido** | **El que manda.** La fecha más temprana acreditada entre sus canales |
| Expedición | Comodidad de informe. **Sin efecto jurídico** |

El art. 10.4.a cuenta desde la recepción «**por la otra parte**», el art. 7.3 desde la recepción
«por la parte a la que se haya dirigido la misma» y el mes del art. 17.4 corre frente a cada
requerido. Dos requeridos que reciben en fechas distintas tienen **dos relojes**, y agregarlos en
uno puede llevar a demandar a quien aún tiene su mes vivo y su procedibilidad sin cumplir.

Simétricamente: **un canal fallido no resta si otro del mismo requerido acreditó recepción.** Al
requerido le basta cualquier canal.

### 6.2 Qué acredita cada cosa, con su precepto

| Hecho | Precepto | Cómo se acredita |
|---|---|---|
| Identidad del oferente | art. 17.2 | El certificado nombra al remitente — y `cosechar` **lo verifica** contra el emisor esperado |
| Recepción efectiva y su fecha | art. 17.2 | Estado 17, 20 o 21 con su fecha |
| **Acceso al contenido íntegro** | **art. 10.2** | Estado 20. La rev. 1 lo atribuía al 17.2: el literal del 10.2 es «y que ha podido acceder a su contenido íntegro» |
| Recepción **de la aceptación** | art. 17.2 | El precepto exige constancia «tanto de la oferta **como de la aceptación**». Es un evento de entrada que el motor debe poder registrar |
| Idoneidad del canal | art. 7.1 | **Domicilio o lugar de trabajo que conste**, o el medio electrónico **empleado por las partes en sus relaciones previas** |
| Definición del objeto | art. 7.1 | La solicitud ha de definir «adecuadamente el objeto de la negociación» |

**La idoneidad del canal se registra, no se presume** (rev. 2). Un email sacado del CRM que nunca
se usó entre las partes no es, por sí solo, el «medio de comunicación electrónico empleado por las
partes en sus relaciones previas» del art. 7.1. El plan marca cada canal electrónico como
**acreditado** o **no acreditado** a esos efectos, y esa marca viaja al registro. No bloquea el
envío: impide dar por interrumpida la prescripción por una vía que no la interrumpe.

### 6.3 Las causas de cierre, y las que tienen valor afirmativo

El art. 10.4 da cuatro causas de terminación sin acuerdo y el 17.4 el decaimiento de la oferta al
mes. A ellas se añade lo que la rev. 1 trató solo como pérdida:

**El rechazo y el silencio tienen valor afirmativo.** El estado 28 no es un fracaso del envío: es
un hecho acreditado con consecuencias propias —art. 7.4 y art. 395.1 LEC en la redacción dada por
el art. 22.28 de la LO 1/2025—. El motor lo registra como evento con fecha, no como error.

**El año del art. 7.3 tiene dos *dies a quo*** unidos por «respectivamente»: desde la recepción si
la solicitud quedó sin respuesta, desde la terminación sin acuerdo si hubo negociación. El motor no
puede computarlo sin saber cuál se dio, así que **registra la causa de cierre** y, si no la conoce,
lo dice en vez de calcular. Con medidas cautelares el plazo son **veinte días**, no el año.

## 7. El documento se parte en DOS PDF

Decisión de Nikolai del 2026-09-17, tomada durante la R1 y mejor que el diseño de la rev. 1.

El envío lleva **dos adjuntos**:

| | Contenido | Aportable |
|---|---|---|
| **A** | Requerimiento + la parte general de la OVC (el motor MASC: la invitación a negociar) | **Sí** |
| **B** | Condiciones económicas de la oferta — los dos pagos | **No** |

**Por qué esta línea y no otra.** Satisface los dos preceptos a la vez, que es lo que ninguna de
las alternativas hacía. El art. 10.2 exige acreditar el **intento de negociación** —«la solicitud o
invitación para negociar»—, así que el aportable tiene que contener la invitación; y el art. 17.4
prohíbe mencionar el contenido **de la oferta**, que son sus términos económicos, no la invitación.
Cortar antes (dejando fuera la parte general) blinda el 17.4 y sacrifica el 10.2; cortar después
—la práctica de `CONVENCIONES` §7— hace lo contrario.

**Por qué es robusto.** El recorte deja de ser una heurística sobre el texto y pasa a ser
estructural: el certificado reproduce **cada adjunto** y el acta lista **nombre y `sha256` de cada
uno**, así que la frontera la fijamos nosotros al componer el envío. Y es gratis: mismo número de
envíos, mismo precio.

**Por qué mejora la prueba.** El acta es irrecortable y se conserva entera, de modo que el
aportable **sigue diciendo que se remitió un segundo documento, con su nombre, su huella y su
fecha, sin su contenido**. Eso es literalmente lo que pide el art. 17.4: «el justificante de
haberla enviado y de que la misma ha sido recibida por la parte requerida, sin que pueda hacerse
mención a su contenido».

Dos condiciones para no estropearlo: **B se nombra de forma neutra** (`ANEXO II.pdf`), porque el
nombre viaja en el acta que no se recorta; y el íntegro se custodia con los dos adjuntos y sus
huellas.

### 7.1 Cosecha

Cuando una expedición finaliza, `cosechar` baja el certificado de cada envío, **verifica que el
remitente sea el emisor esperado**, y lo sube al expediente con el nombre canónico
`<ASUNTO> - <REF>-<codigo>.pdf` por la vía del §17.1. La subida se verifica por resultado: se baja
lo subido y se compara el `sha256`.

### 7.2 La anatomía del certificado, medida

Sobre el certificado `006casm113n` (gdocu 42990 del W-04A6LI, 6 páginas):

- **Va firmado digitalmente.** `AcroForm` con `SigFlags: 3`, `/ByteRange`, `adbe.pkcs7` y
  `DocMDP`. **Recortar páginas rompe la firma.** Por eso el recorte nace como **documento derivado
  con trazabilidad**, nunca como «el certificado».
- **Y la presunción que se pierde al romperla es real** (rev. 3, hueco 5 cerrado el 2026-09-17).
  `SERVICIOS DE MAILCERTIFICADO SL`, CIF `B85804532`, **figura en la lista de confianza española**
  —`https://tsl.digital.gob.es/TSL.xml`, alcanzada desde la LOTL europea
  `https://ec.europa.eu/tools/lotl/eu-lotl.xml`, no desde la web del prestador— con **tres
  servicios de tipo `http://uri.etsi.org/TrstSvc/Svctype/EDS/Q`** —entrega electrónica certificada
  **cualificada**—, los tres en estado `granted`, el vigente desde el 2026-07-01. Luego el **art.
  326.4 LEC** juega: presunción de que el documento reúne la característica cuestionada y **carga
  de la comprobación a quien impugne**, con sus costas y la multa por temeridad. Romper la firma
  cuesta eso, y hay que decidirlo sabiéndolo.
- **El burofax acredita por otra vía, y eso no lo debilita.** Ninguno de los tres servicios
  cualificados cubre el envío postal —los tres son de entrega **electrónica**—, pero el art. 326.4
  LEC es una regla sobre **documento electrónico** amparado por un servicio de confianza eIDAS, no
  la fuente del valor del burofax. **El burofax es medio fehaciente y certifica el contenido y el
  resultado de la entrega**, que es justamente para lo que se usa. Decir que «se queda sin la
  presunción» sería confundir un régimen probatorio distinto con una desventaja.
  Lo que **no he verificado** y sigue como hueco: por qué vía concreta se le reconoce esa
  fehaciencia cuando el envío lo cursa Codicert —si actúa como operador postal o deposita en un
  tercero—, dato que solo importa si alguien llega a impugnar el certificado postal.
- **Acta y reproducción se distinguen por el texto.** Las páginas del acta llevan en cabecera
  *«Este certificado contiene un sello temporal y se encuentra firmado digitalmente con un
  certificado reconocido»*; las de la reproducción no. En ese certificado: 1-4 acta, 5-6
  reproducción.

### 7.3 Los tres marcos de referencia, y el discriminante doble

Se recorta **la reproducción dentro del certificado**, no el documento. Hay tres numeraciones
distintas y el motor debe nombrar siempre cuál usa: página del documento, página de la reproducción
y página del certificado —desplazada por las páginas de acta y, en el burofax, quizá por la
portada—.

**El documento vivo, medido** (rev. 3, hueco 7 cerrado el 2026-09-17). La plantilla **281**
renderizada por la API sobre un expediente real y convertida a PDF da **tres páginas**:

| Página | Bloque | Cómo se reconoce |
|---|---|---|
| 1 | Requerimiento | Encabezado `OFERTA VINCULANTE CONFIDENCIAL Y PROPUESTA DE NEGOCIACIÓN DIRECTA`; lleva el `100 %` de honorarios y los tres IBAN |
| 2 | OVC, motor MASC | Diez menciones de «oferta vinculante»; el «UN MES» del art. 17.4 |
| 3 | Condiciones económicas | Abre con el literal **`CONFIDENCIAL - CONDICIONES`**; calendario de `DIEZ (10)` y `TREINTA (30)` días |

**La línea A/B del §7 cae en una frontera de página que ya existe**: A = páginas 1-2, B = página 3.
Y se comprobó por el lado que importa: **en A no hay términos económicos**. No hay un solo importe
en euros en todo el documento —las condiciones no llevan cifra, que es deuda conocida de la
plantilla—, el `100 %` de la página 1 es el porcentaje de honorarios reclamado y pertenece al
requerimiento, y el «UN MES» de la página 2 es el plazo legal del art. 17.4, no un término
negociado.

**Un discriminante que la rev. 2 dio por bueno y NO existe.** La rev. 2 proponía localizar B «por
el pie», apoyándose en que el refundido lleva pie propio en su sección confidencial. Eso es cierto
del **prototipo de `W-02SRFU`** —cinco páginas, pies distintos en 1-3 y 4-5— y **falso de la
plantilla 281 viva**: sus tres páginas llevan **el mismo** pie de requerimiento fehaciente. Medido.
Un control que el documento real no soporta no es un control.

El motor localiza B por **dos instrumentos independientes que deben coincidir**:

1. **Por estructura**: el motor compuso A y B, conoce el número de páginas de cada uno y su orden;
   la reproducción empieza donde acaba el acta, por el discriminante del §7.2.
2. **Por el literal de apertura de B**: `CONFIDENCIAL - CONDICIONES`, que es texto exacto del
   documento y no una heurística. Como B lo compone el motor, su primera línea se conoce siempre,
   también si la plantilla cambia.

**Si los dos no coinciden, el motor para.** Un solo instrumento que no puede dar el otro valor no
acredita nada; dos que deben coincidir sí.

### 7.4 Qué produce, y el aviso que sí tiene discriminante

Tres artefactos, los tres archivados:

1. El **certificado íntegro**, con su firma intacta. Es lo que se custodia.
2. El **aportable**, como fichero nuevo con nombre distinguible.
3. Un **manifiesto**: código de envío, `sha256` del íntegro, huellas de A y B tal como las lista el
   acta, páginas conservadas y retiradas, el emisor verificado, y el aviso del §5 regla 3 cuando el
   sobre fue conjunto.

**El aviso** deja de ser una promesa genérica y pasa a tener discriminante: comprueba que el
**bloque A** no contenga cifras ni términos de la oferta —importe, calendario, quita, plazo de
aceptación— y que **el asunto y el cuerpo** tampoco, porque el acta los reproduce y el acta no se
recorta. Si salta, nombra qué encontró y dónde.

## 8. Credenciales y entornos

Las claves viven **solo en `.env`** —gitignored— o en el entorno, nunca en el árbol ni en el chat.
Prefijos, en la tabla del §2.1; el `.env.example` los documenta los dieciséis.

```
CODICERT_ENTORNO=sandbox|produccion
CODICERT_SANDBOX_USUARIO / CODICERT_SANDBOX_CLAVE
CODICERT_<CIUDAD>_USUARIO / CODICERT_<CIUDAD>_CLAVE
```

**La precedencia es: la orden manda sobre el entorno.** Producción exige que la orden lo diga
**aunque** `CODICERT_ENTORNO=produccion` esté puesto en el `.env`. Una variable olvidada no puede
ser lo único que separa una prueba de un gasto irreversible. El plan imprime el entorno y el
usuario emisor literal en su cabecera.

**El `.env` se lee de la raíz real del repositorio**, resuelta con `git rev-parse`, no de
`Path(__file__).parent.parent`: medido el 2026-09-17, en un worktree ese camino no encuentra el
`.env` de la raíz y el motor trabajaría a ciegas.

E&V pidió expresamente el 2026-09-07 que las pruebas de integración vayan contra el entorno de
pruebas, «así no se cobrará nada».

## 9. Fases y testabilidad

| Fase | Qué entrega | Utilizable sola |
|---|---|---|
| **F1** | `core/codicert.py` + `planificar` + `ejecutar` + `plan`/`enviar` | Sí: sustituye el picado manual |
| **F2** | `refrescar` + `cosechar` + `core/sudespacho_documentos.py` + `estado`/`cosechar` | Sí: cierra la prueba del envío |
| **F3** | `core/certificado_aportable.py` + el aportable y su manifiesto | Sí: produce lo que va al juzgado |

**Lo que se prueba con doble y lo que no.** Con el puerto del §4.2, la lógica del despacho se
prueba entera contra dobles. Lo que **no se puede probar sin enviar de verdad** se nombra aquí para
que nadie crea que la suite lo cubre: la anatomía del certificado de burofax, la portada del
burofax y el texto de la notificación SMS. Y la guarda de idempotencia viene **con su control
positivo** —un envío sembrado que la ponga en «ya existe»— y con un mutante que la mate; el
discriminante del §3 es lo que hace que ese mutante pueda existir.

**El mapeo ciudad→usuario no es verificable en sandbox**, donde hay una sola credencial: todas las
plazas colapsan en el mismo usuario. Se acredita la primera vez en producción, leyendo el remitente
del certificado emitido.

## 10. Huecos declarados

1. ~~**Si el texto de la notificación SMS es configurable.**~~ **CERRADO el 2026-09-17** (§5 regla
   7): **no lo es**, por tres vías que coinciden. Lo que se controla es el nombre del remitente, y
   el literal de la casa hay que llevarlo al correo de notificación. Queda por leer el texto exacto
   que compone la plataforma.
2. **La anatomía del certificado de un burofax**, frente a las 4 páginas de acta medidas en el de
   una entrega electrónica certificada. El discriminante del §7.2 no depende del número, pero no
   está comprobado que la cabecera sea idéntica en el certificado postal. Buscado el 2026-09-17 en
   el gestor documental de diez expedientes: **no hay ninguno archivado**, solo certificados de
   entrega electrónica. Se cierra con uno del portal de producción.
3. **Si la portada del burofax se imprime como página adicional**, y por tanto desplaza la
   numeración de la reproducción. La portada **es opcional en el contrato**: si estorba, se omite.
4. ~~**El límite de tamaño de los adjuntos.**~~ **CERRADO el 2026-09-17** (§1.4): 6 ficheros, 60 MB
   en total, 1 MB incluido en el precio. **Queda un resto**: la UI dice 6 ficheros y el contrato
   `1..10`, y no se ha medido cuál manda.
5. ~~**Si Codicert figura en la lista de confianza como prestador cualificado.**~~ **CERRADO el
   2026-09-17** (§7.2): sí figura, con tres servicios `EDS/Q` `granted`. El art. 326.4 LEC juega
   para los certificados electrónicos. **Queda un resto abierto**: ninguno de esos tres servicios
   cubre el **envío postal**. El burofax es fehaciente por su propia vía —certifica contenido y
   entrega—; lo que no está verificado es por qué cauce concreto se le reconoce cuando lo cursa
   Codicert.
6. **El volumen de envíos de la cuenta de un Market Center**, del que depende que paginar sea
   barato.
7. ~~**El mapeo página→bloque del documento refundido vivo.**~~ **CERRADO el 2026-09-17** (§7.3):
   la plantilla 281 renderizada da tres páginas —requerimiento, OVC, condiciones—, la línea A/B
   cae en una frontera de página que ya existe, y el discriminante es el literal
   `CONFIDENCIAL - CONDICIONES`. De paso se retiró el discriminante «por el pie» que la rev. 2 daba
   por bueno y que el documento vivo no soporta.
8. ~~**Los 52 valores de `provincia` del CRM** cruzados con lo que el burofax acepta.~~ **CERRADO
   el 2026-09-17** (§5 regla 5): 45 coinciden, **7 no**, y hacen falta traducirse. Afecta a la
   Comunidad Valenciana entera y al País Vasco.

**Balance tras la tanda del 2026-09-17:** de los ocho, **cinco cerrados** (1, 4, 5, 7, 8) y tres
abiertos (2, 3, 6), más dos restos menores —el cauce de la fehaciencia postal y la discrepancia
`6` contra `1..10` en el número de adjuntos—.

Los tres abiertos **no se cierran en sandbox**: el 2 y el 3 necesitan un certificado de burofax
real, y el 6 una lectura del portal de producción. Ninguno bloquea F1.

## 11. Adjudicación de la revisión adversarial (Claude Code en sesión independiente, 2026-09-17) — REQUIERE-REVISION, parcial

- **Objeto revisado:** `docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md` rev. 1, commit `d895d1d`
- **Ronda:** 1, sobre el diseño
- **Revisor:** Claude Code (sesión independiente) — Codex sin cupo hasta el 2026-09-19
- **Informe recibido:** `2026-09-17-envio-certificado-codicert-r1-adversarial-review.md`, `sha256` del bloque literal `59d499ffd7fddb209d2979893c96da537aad4cef008c4820fe20a8737d31b2f5`
- **Hallazgos:** 34 — 12 `alta`, 14 `media`, 8 `baja`. **33 confirmados, 1 refutado en un extremo**
- **Remediado en:** esta rev. 2

**La independencia de esta ronda es más débil y así consta en el acta.** Autor y revisor son el
mismo modelo, con los mismos puntos ciegos. Se compensó con tres lentes en paralelo, sin contexto
de autoría y con mandato de reproducir toda medición; pero no equivale a una revisión ajena, y
escribirlo de otro modo sería maquillar el registro.

**Los doce hallazgos altos, y qué hice con cada uno:**

| # | Lente | Hallazgo | Adjudicación | Dónde |
|---|---|---|---|---|
| A-01 | arquitectura | El `id_personalizado` no tenía gramática: con el W-code solo, la OVC no sale nunca | **Confirmado.** El modo de fallo es silencioso y positivo | §3, nuevo |
| A-02 | arquitectura | «Consultar antes de mandar» es un censo negativo, con precedente medido en el repo | **Confirmado** contra `INTEGRACION_SUDESPACHO.md` §17.4 | §4.3 y §5.2 |
| A-03 | arquitectura | Sin costura no hay dobles, y la guarda de idempotencia no puede dar el otro valor | **Confirmado** | §4.2 y §9 |
| A-04 | arquitectura | El modelo de páginas contradice la única medición del repo | **Confirmado.** Medido: 5 páginas, 4-5 confidencialidad | §7.3 |
| J-01 | jurídica | El año del art. 7.3 tiene dos *dies a quo* | **Confirmado** contra el literal del BOE | §6.3 |
| J-02 | jurídica | El art. 7.1 exige canal idóneo y definición del objeto | **Confirmado** contra el literal | §6.2 |
| J-03 | jurídica | El burofax conjunto no acredita recepción de cada requerido | **Confirmado en derecho.** Nikolai mantiene la regla; el aviso sube al plan y al manifiesto | §5 regla 3 |
| J-04 | jurídica | Precepto mal atribuido y un estado medido fuera de la tabla | **Confirmado** por partida doble | §1.3 y §6.2 |
| J-05 | jurídica | El acta reproduce asunto y cuerpo, y el aviso era ciego ahí | **Confirmado** | §5 regla 6 y §7.4 |
| J-06 | jurídica | Romper la firma cuesta la presunción del art. 326.4 LEC | **Confirmado** contra el literal. El remedio que proponía —un justificante sin reproducción— **no existe**: Nikolai confirma que el certificado incluye siempre el PDF | §7.2, hueco 5 |
| API-01 | API | `campos_verificacion` vacío: «Leído» no identifica a nadie | **Confirmado** | §6.2 |
| API-02 | API | El patrón del móvil, atribuido al canal que no lo tiene | **Confirmado**, y verificado por mí en el OpenAPI | §1.1 |

**Los veintidós medios y bajos** se remediaron todos salvo donde el remedio es una medición: la
cabecera `x-json-ficheros` (§1.1), el recuento de 37 estados (§1.3), el presupuesto de bytes
(§1.4), el `id_personalizado` del burofax sin `maxLength` (§1.2), el vencimiento del token (§1),
los filtros de `GET /envios` (§1.2), la verificación del remitente y el `None` de
`ciudad_de_equipo` (§2.1 y §7.1), el hogar de la subida y la idempotencia de `cosechar` (§4.1 y
§5.2), el plan rancio y el booleano de confirmación (§5.1), el crédito (§5.2), el denominador de
la paginación (§4.3), el asunto y el cuerpo (§5 regla 6), los tres niveles de plazo (§6.1), el
rechazo con valor afirmativo (§6.3), los slugs de ciudad y la precedencia de entorno (§8), y la
validación completa de la ficha postal (§5 regla 5).

**El extremo refutado.** La lente de arquitectura sostiene en su H-05 que las siete ciudades con
usuario `.bd` son «inferencia sobre 25 subusuarios que nadie enumeró». **Se enumeraron** el
2026-09-17 en `/masterusuarios`, y las siete existen. El revisor no tenía acceso al portal. Su
hallazgo acierta en lo principal —el spec no decía que estuviera medido— y eso sí se ha corregido.

**Un hallazgo sobre mí, no sobre el diseño, y es el que más conviene retener.** La lente de
arquitectura señala en su H-12 que la rev. 1 presentaba las dos rondas como **lectura** de la tabla
de `CLAUDE.md`, cuando la tabla da **una**: esta pieza no decide quién escribe sobre qué copia ni
destruye datos de cliente. **Confirmado.** Dos rondas siguen siendo lo que quiero —gasta dinero y
manda comunicaciones irreversibles a terceros— pero eso es **ampliar la cobertura por decisión**,
no deducirla. Es exactamente el movimiento que el revisor del spec hermano marcó dos días antes y
que su autor adjudicó como confirmado; lo repetí sin darme cuenta. Si la tabla se puede leer para
arriba cuando conviene, se puede leer para abajo cuando conviene.

## 12. Revisión adversarial

**Dos rondas: la primera está hecha (§11) y la segunda irá sobre el diff.** Son dos **por decisión
expresa**, no por lectura de la tabla de `CLAUDE.md`, que a esta pieza le asigna una: no decide
quién escribe sobre qué copia ni destruye datos de cliente. Se amplía porque **gasta dinero y manda
comunicaciones jurídicas irreversibles a terceros, con efectos de prescripción**, y porque un
defecto aquí no se arregla con un `git revert`.

La R2 la ejecutará **Codex** si tiene cupo a partir del 2026-09-19; si no, Claude Code en sesión
independiente con el mismo registro sin maquillar.
