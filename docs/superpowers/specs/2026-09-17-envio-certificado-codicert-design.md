---
tipo: spec
estado: vigente
creado: 2026-09-17
objeto: envío certificado de burofax y OVC por la API de Codicert (Servicios de MailCertificado S.L.)
rev: "17"
---

# El requerimiento sale solo: burofax, correo y SMS por la API de Codicert

Encargo de Nikolai del **2026-09-17**: los burofaxes y las OVC ya preparados —el PDF sale del
CRM— tienen que salir por **codicert.io** por los **tres canales a la vez**: burofax postal,
correo electrónico y SMS, **a todos los requeridos**. Dos requeridos son dos correos y dos SMS
si constan; y **un burofax por domicilio distinto**. Al terminar, hay que **descargar los
certificados** y producir la versión **aportable** como prueba.

> **Rev. 17 (2026-09-26).** Los estados, **medidos sobre todos los envíos reales**: los 117 de
> `madrid.bd` (del 2026-06-03 al 2026-09-23) y los 2 del sandbox, leídos en solo lectura (plan
> [`2026-09-26-codicert-estados-medidos.md`](../plans/2026-09-26-codicert-estados-medidos.md),
> M-17 a M-22). El SMS **no tiene estados propios** —ni 29, ni 30, ni 39 en 22 SMS— y el **22**
> dejaba un envío sin cerrar para siempre: **Nikolai decidió** que cierra sin entrega cuando ningún
> aviso llegó (§1.3, §6.3). El SMS Certificado **sí registró un acceso**, y la razón para no usarlo
> cambia (§1.1). Y lo que no se cosecha tiene **cuatro motivos**, no uno (§7.1).
>
> **Rev. 16 (2026-09-25).** Los **plazos del servicio**, leídos en la Declaración de Prácticas del
> prestador (v2.5): la entrega electrónica queda a disposición **30 días naturales desde el envío**
> y, vencidos sin lectura, pasa a **40 «Caducado»** (§1.3). Y una decisión de Nikolai: el **17 y el
> 21 acreditan la recepción, no la lectura**, aunque el prestador solo llame «entregada» a la leída
> (§6.2). El motor ya clasificaba así; no cambia.
>
> **Rev. 15 (2026-09-25).** La R3 de Codex sobre F3 (§12.4): el aportable **lo compone el
> motor** —el OCR solo devuelve líneas— y la relectura lo **recompone** y exige los mismos bytes;
> cada página tiene que dibujar su imagen y parecerse más a la suya que a cualquier otra del
> íntegro; el título de las condiciones no admite minúsculas detrás, y una mención antes de él
> para (§7.4).
>
> **Rev. 14 (2026-09-25).** La R2 de Codex sobre F3 (§12.4): el aportable pasa a ser la **imagen**
> de las páginas que se conservan, con una capa de texto de OCR (§7.4).
>
> **Rev. 13 (2026-09-25).** Actualizada al construir **F3**, con diez mediciones sobre tres
> certificados reales y los adjuntos de dos envíos (plan
> [`2026-09-25-codicert-f3.md`](../plans/2026-09-25-codicert-f3.md), M-1 a M-10; lectura de
> producción autorizada por Nikolai en la sesión, 0,00 € gastados). **Dos premisas del §7 no se
> sostenían en lo construido:** el motor **no compone** las condiciones —las trae el operador—, así
> que su texto se lee de los adjuntos que salieron, verificados contra la huella del acta (§7.3); y
> el requerimiento **sí lleva importes** —la deuda reclamada—, así que el aviso de «sin cifras»
> habría saltado en todo envío real y se rehace sobre las frases propias de las condiciones (§7.4).
> Además, la reproducción real es el refundido **más la factura**, y el burofax se recorta con los
> adjuntos del correo de la misma expedición, porque su fichero fundido es la concatenación exacta
> de estos (§7.3).
>
> **Rev. 12 (2026-09-21).** Actualizada al construir **F2**, con diez mediciones de producción
> en solo lectura (0,00 € gastados). Tres cambian el diseño: el **§1.3** gana **seis códigos de
> estado vivos** que no clasificaba —y la regla de que lo no clasificado se declara, nunca se
> presume benigno—; el **§7.2** documenta **dónde** nombra el certificado a su emisor y por qué la
> verificación del art. 17.2 tiene que acotarse a su bloque (la razón social aparece nueve veces
> en el documento y una en el sitio bueno), más que el PDF **se cachea** en vez de re-emitirse; y
> el **§9** cierra la vía de acreditación del mapeo ciudad→usuario, que el certificado sí lleva.
> Se añaden tres certificados a la tabla de anatomía del §7.2, y uno de ellos tumba el «seis
> páginas de acta» del burofax.
>
> **Rev. 11 (2026-09-17).** Lectura contra **producción** con `madrid.bd`. Se cierra el hueco **3**
> —la portada del burofax **no entra en la reproducción**, medido por diferencia exacta— y con él
> los ocho. La gramática del identificador del §3 **se alinea con la que ya está en uso**
> (`W-04AKM2 - OVC`) en vez de inventar otra.
>
> **Rev. 10 (2026-09-17).** Se cierra del todo el hueco **1** con el literal del SMS, y un
> certificado real de OVC confirma dos cosas sobre envíos reales de E&V: el acta electrónica
> **lista los ficheros uno a uno con su huella** —partir A y B quedaría reflejado— y el
> discriminante
> `CONFIDENCIAL - CONDICIONES` **se ve funcionar** sobre un documento que salió de verdad.
>
> **Rev. 9 (2026-09-17).** Primera expedición real en sandbox (1,06 € de los 20 €). Los dos
> canales **no tratan igual los adjuntos**: el burofax los fusiona, pero **la entrega electrónica
> los lista uno a uno con su nombre y su `sha256`**, así que el valor probatorio de la división A/B
> existe por la vía electrónica. Y el orden de la reproducción **sí es el de subida**, lo que
> corrige una inferencia que la rev. 6 presentó como medición.
>
> **Rev. 8 (2026-09-17).** Primer contacto real con la API del sandbox, ya con credenciales.
> **Deshace una alarma falsa mía**: la provincia es obligatoria pero **no se valida contra lista**,
> así que no hay 422 a mitad de expedición. A cambio destapa que el servidor **exige `asunto`,
> `cuerpo` y `adjuntos`** en el burofax contra lo que dice el contrato —luego la portada **no es
> opcional**— y que el `422` viene desglosado campo por campo, que es la herramienta de
> verificación barata del motor.
>
> **Rev. 7 (2026-09-17).** Nikolai pregunta qué pasa cuando el envío lleva además la factura y el
> documento de la negativa —que es lo normal—, y destapa que **la parada dura de la rev. 6 estaba
> mal enunciada**: por el lado de la página suelta habría bloqueado el caso normal, porque esos
> adjuntos son escaneos sin texto. Se reenuncia por el lado de B. El §7 deja de hablar de «dos
> PDF» y dice lo que de verdad exige: que las condiciones económicas viajen solas en su adjunto.
>
> **Rev. 6 (2026-09-17).** Nikolai aporta un certificado de **burofax** real y tumba el fundamento
> del §7: **Codicert fusiona los adjuntos en un solo PDF**, con nombre UUID y una sola huella, así
> que el acta no documenta A y B por separado y el nombre neutro no sirve de nada. El orden de la
> reproducción **tampoco es el de envío**. El §7.3 se rehace sobre el único instrumento que
> sobrevive —casar el texto de B— con dos paradas duras. Se cierra el hueco **2** y se añade el
> estado **19**.
>
> **Rev. 5 (2026-09-17).** Corrección de Nikolai sobre la UI: **hay dos vías para el SMS**, y la
> rev. 4 describió mal la segunda —el SMS Certificado sí tiene `cuerpo` propio y admite un
> adjunto—. Se mantiene la entrega electrónica certificada, ahora por la razón correcta: es la que
> acredita el acceso al contenido del art. 10.2. Se cierra el hueco **6** y se anotan tres
> discrepancias medidas entre la UI y el contrato de la API.
>
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

**Autenticación, ejercida contra el sandbox el 2026-09-17.** `POST /usuarios/acceso` con
`{usuario, clave}` —las mismas del portal— devuelve `{estado:"OK", datos:{ficha, fecha_vencimiento}}`.
La **ficha tiene 64 caracteres**, no los 32 del ejemplo de la documentación, y **vence a las 24
horas**. El cliente conserva el vencimiento: un token caducado a mitad de expedición es un fallo
evitable.

### 1.1 Los tres canales son DOS endpoints, y esto es lo que más cambia el diseño

| Canal | Endpoint | Límite duro |
|---|---|---|
| Burofax postal | `POST /envios/burofax` | `destinatarios` array de **exactamente 1**; adjuntos **solo PDF**; `pais` solo `"España"` |
| Correo certificado | `POST /envios/entrega-electronica-certificada` con `tipo_entrega: "correo"` | adjuntos 1..10 |
| SMS certificado | **el mismo endpoint**, con `tipo_entrega: "sms"` | ídem |

Los dos endpoints exigen la cabecera **`x-json-ficheros: 1`** cuando el cuerpo es JSON con
ficheros en base64, que es siempre en nuestro caso. La declaran diez endpoints del contrato y
olvidarla es el error fácil de este formato.

**Hay DOS vías para mandar un SMS, y la rev. 4 describió mal la segunda** (corregido en rev. 5 tras
la observación de Nikolai, medido en la UI de producción el 2026-09-17):

| Vía | Texto del SMS | Adjunto | Qué acredita |
|---|---|---|---|
| **EEC con `tipo_entrega: "sms"`** | **Lo compone la plataforma.** No hay campo | 6 ficheros | Entrega **y acceso al contenido** (estado 20) |
| **SMS Certificado** (`/envios/sms-certificado`) | **`cuerpo`, obligatorio y nuestro** | **1 fichero** | ~~Entrega del SMS (estados 29/30)~~ **Medido (rev. 17): entrega y acceso, `17 → 20`**, en el único de producción |

Lo que la rev. 4 dijo —«el SMS no lleva texto propio»— es cierto de la primera vía y **falso de la
segunda**: el formulario de SMS Certificado tiene un `Cuerpo` obligatorio con contador de
caracteres GSM y aviso de no usar tildes, que es inequívocamente el texto que llega al móvil. Y
tampoco es «texto pelado»: admite **un adjunto**.

**Se sigue eligiendo la EEC por SMS, pero ahora por la razón correcta.** No es que la otra no
tenga texto: es que el art. 10.2 exige acreditar que la otra parte **«ha podido acceder a su
contenido íntegro»**, y eso es lo que da el estado 20 de la entrega electrónica certificada. El
SMS Certificado acredita que el SMS se entregó, no que se accediera al documento. Es además lo que
E&V ya hace: los tres envíos de producción del §2 son entregas electrónicas certificadas.

El precio de esa elección, dicho: **el literal de `CONVENCIONES_DESPACHO.md` §5 no se puede poner
en el SMS por esta vía.** Lo que el destinatario lee lo compone la plataforma con el nombre del
remitente. Si se quisiera controlar ese texto palabra por palabra, habría que usar SMS Certificado
y renunciar al acuse de acceso — que es peor negocio.

**Corrección de la rev. 17, medida: el SMS Certificado también registra el acceso.** El único de
producción (`006bkxe0q63`, tipo `s` en el listado) hizo `17 → 20 «Documentación accedida»`, y
ninguno de los 22 SMS medidos pasó por el 29 ni por el 30 (§1.3). Es una sola muestra, pero basta
para que la razón de arriba —«acredita que el SMS se entregó, no que se accediera»— no se sostenga
tal cual. **La elección de la entrega electrónica sigue en pie por otra razón**, que no depende de
ese matiz: el SMS Certificado admite **un** fichero, y el requerimiento sale con las condiciones
económicas **en adjunto aparte** (§7), que es lo que hace posible el aportable. El motor no manda
SMS Certificado; si aparece uno con la referencia de una expedición —se puede mandar desde el
portal—, **no se cosecha y sus fechas no cuentan** para el requerido (§7.1).

Consecuencia operativa que gobierna todo el motor: **el burofax admite un destinatario por
llamada**. Dos domicilios son dos llamadas, siempre.

**Y el servidor exige más de lo que el contrato declara** (rev. 8, sondeado contra el sandbox sin
gastar un céntimo: crédito 20 € antes y después). Un `POST /envios/burofax` incompleto devuelve un
`422` **desglosado campo por campo**, y ese desglose dice que son **obligatorios**:

```
asunto    : El campo asunto es obligatorio
cuerpo    : El campo cuerpo es obligatorio
adjuntos  : El campo adjuntos es obligatorio
```

El OpenAPI los declara opcionales y a `adjuntos` le pone `minItems: 0`. **No es cierto.**
Consecuencia directa: **la portada del burofax no es opcional** —asunto y cuerpo la componen— así
que la salida que el spec daba al hueco 3 («si estorba, se omite») **no existe**.

**El `422` desglosado es además la herramienta de verificación barata del motor**: permite
comprobar la forma de un payload sin enviar nada ni gastar. Las sondas se diseñan para que no
puedan salir —`pais` fuera de su enum es el pestillo seguro— y se cierran comprobando el crédito
antes y después.

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
GET  /envios/{IdEnvio}/adjuntos/{Adjunto}  el adjunto tal como se envió (nombre en base64url)
GET  /usuarios/credito                     crédito del usuario
```

`GET /envios` **no filtra por `id_personalizado`** —probados cinco parámetros de búsqueda, los
cinco devuelven el total sin filtrar— pero **sí acepta `fecha_inicio`, `fecha_fin`, `tipo` y
`estado`**, ejercidos contra el sandbox, y cada elemento **devuelve su `id_personalizado`**. Esos
dos hechos juntos son los que hacen viable el §4.3: se acota por fecha y se filtra en casa.

**`GET /envios/{id}/adjuntos/{nombre}` funciona y es la verificación por resultado del envío**
(rev. 11): devuelve el fichero **tal como salió**, con el nombre en base64url sin relleno. Comparar
su `sha256` con el del bloque que el motor compuso es la única forma de acreditar que se envió lo
que se quería enviar, y no una versión anterior. Es la misma disciplina que el §7.1 aplica a la
subida al CRM.

Dos correcciones al contrato, medidas: la envoltura real es
`{estado, datos, pagina, longitud, total, totalPaginas}` —el OpenAPI escribe `total_paginas`— y
**`longitud` acepta [10..100], no [1..100]**: con 1, 2 o 5 devuelve `400`.

`id_personalizado` **se puede repetir a propósito** entre envíos —lo dice su descripción— y admite
**20 caracteres en cuatro de los cinco productos**. `SolicitudBurofax` lo redefine inline **sin
declarar `maxLength`**, así que el límite del burofax es desconocido: el motor se ciñe a 20 para
todos, que es el suelo seguro.

### 1.3 Los estados: son 37, y el que faltaba es el que cierra

La plataforma documenta **37** códigos (la rev. 1 dijo 43; recontados sobre la documentación
renderizada). Para este motor cuentan estos, y la frontera entre los tres primeros decide plazos:

| Código | Título | Qué significa para nosotros |
|---|---|---|
| 5 | Procesado | **No es entrega.** Es lo que devuelve el certificado emitido al enviar |
| 27 | Entregado en el servidor | Llegó al servidor del destino; nadie lo ha abierto |
| 17 | Entregado | Entrega acreditada |
| 20 | Leído · Documentación accedida | Acceso al contenido — art. 10.2 |
| **21** | **Recordatorio lectura entregado** | **Entrega acreditada del recordatorio, sin acceso al contenido** |
| **19** | **Entregado con albarán** | **Terminal del burofax.** Entrega con copia del albarán firmado por el receptor |
| 28 | Rechazado | Entrega fallida por rechazo. **Tiene valor afirmativo**, ver §5 |
| 42 / 40 | Fallido / Caducado | Sin entrega |

El **21** faltaba en la rev. 1 y es exactamente donde quedaron **dos de los tres envíos de
producción** que el §2 pone de ejemplo. El **19** faltaba hasta la rev. 6 y es el estado en que
termina un burofax entregado en mano. Sin clasificarlos, una expedición real no cerraría nunca.

Y se repite aquí porque el motor tiene que codificarlo: **«Procesado» no es «Entregado»**.

**Y faltaban SEIS más, todos vivos** (rev. 12, medidos el 2026-09-21 leyendo el histórico de 22
envíos de `madrid.bd` de tres semanas). Ninguno es terminal, pero un motor que clasificara solo
los nueve de arriba dejaría envíos reales sin clasificar:

| Código | Título | Dónde aparece |
|---|---|---|
| 3 | Enviado a imprenta para su impresión | burofax, primer estado |
| 8 | Pendiente de recogida | burofax |
| 11 | En tránsito a la ciudad de destino | burofax |
| 12 | En reparto | burofax |
| 14 | Recordatorio lectura **enviado** | entrega electrónica — el 21 es el *entregado* |
| **31** | **Incidencia** | burofax. Dos veces, con detalles distintos: «No es posible realizar la entrega, esta se está gestionando» y «Dirección de entrega no encontrada» |

**La regla que el motor codifica, y que importa más que la tabla:** un código que **no** esté
clasificado no cae en «en curso» por defecto. Se declara **desconocido** y el frontal lo nombra.

**Los plazos del servicio, según el prestador** (rev. 16, leídos el 2026-09-25 en la Declaración
de Prácticas de Codicert, **v2.5 del 23/01/2026**,
`https://www.codicert.io/wp-content/uploads/2026/01/dpc_23_01_2026.pdf`). La API no los dice:
solo devuelve, en la entrega electrónica y el correo certificado, un `fecha_expiracion` de salida
—que **no es este plazo**: es el envío más cinco años (rev. 17, abajo)—, y el único plazo
configurable (`expiracion`, de 3 a 30 días) es de los contratos y el SEPA.

- **§4.5.5 — 30 días naturales desde el envío.** Es lo que la comunicación queda a disposición del
  destinatario; el remitente puede cambiarlo, nunca por debajo de 72 horas, y por nuestra API no
  se puede en la entrega electrónica. **Vencido sin lectura, el estado es el 40, «Caducado».**
- **§4.5.10 — la correspondencia con la norma ETSI EN 319 522-1**, que es la que da sentido a cada
  código: 27 = D.1 (el aviso llegó al servidor), **17 = D.3 (el aviso llegó al buzón)**, **20 =
  E.1 (entrega del contenido: leído)**, 22 = D.4 (recordatorio fallido), 28 = C.4 (rechazo), 40 =
  C.5 (vence el plazo sin aceptación ni rechazo) y 42 = C.2 (fallido). Cinco de los doce códigos
  de esa tabla —el 0 «solicitado», el 2 «cancelado», el 16 «identificación errónea», el 22 y el 34
  «aceptado»— el motor no los clasificaba: si aparecían, salían como **desconocidos**, que es lo
  que la regla de arriba quiere. **Desde la rev. 17 el 22 sí se clasifica** (abajo); los otros
  cuatro, no.
- **§4.5.7 — las evidencias se conservan al menos 15 años** desde el envío (las condiciones
  generales dicen cinco para el resto de documentos).
- **El burofax no está en esa Declaración**, que es la del servicio electrónico: sus plazos no
  salen de aquí.

Con eso, F2 ya encaja: una entrega electrónica solo se cosecha en 20 o cerrada (28, 40, 42), así
que la que nadie lee se cosecha al caducar, a los 30 días.

**Los estados, medidos sobre todos los envíos** (rev. 17, 2026-09-26; plan de los estados medidos,
M-17 a M-22). Barrido en solo lectura de los 117 envíos de `madrid.bd` —72 entregas electrónicas por
correo, 20 por SMS, 24 burofax y 1 SMS Certificado— y de los 2 del sandbox:

- **El SMS no tiene estados propios.** Ninguno de los 22 SMS pasa por el 29, el 30 ni el 39: recorren
  los del correo. Esos tres siguen **sin clasificar**, a propósito: si aparecen, se declaran.
- **El 22 dejaba el envío sin cerrar.** Un SMS que no llegó nunca hizo `3 → 14 → 22` y ahí se quedó,
  83 días sin el 40, que la plataforma no pone a lo que no entregó. **Decisión de Nikolai
  (2026-09-26): el 22 cierra sin entrega si ningún aviso llegó**; si llegó el primero, el requerido
  aún puede leer y lo cierra el 40. Lo que aprobó nombraba el 17, el 20 y el 21; **el plan lo
  concreta (D-1)** añadiendo el 19 y **el 27** —éste, porque el aviso está en su servidor, igual que
  con el 17— y contándolos en cualquier punto del histórico, porque el acuse puede llegar tarde
  (§6.3). El motor lo clasifica en familia propia, `AVISO_FALLIDO`, porque no siempre cierra.
- **El 40 llega a los 30 días exactos del envío, al segundo**: 24 de 24 en el correo y 6 de 6 en el
  SMS. La Declaración, confirmada con datos.
- **`fecha_expiracion` no es ese plazo**: en los 119 envíos, de los tres tipos, es el envío **más
  cinco años**. Es la custodia.
- **Un burofax entregado puede quedarse sin su 19**: `006bgjupt2a`, 88 días en 17. En los otros
  siete, el 19 tardó de 1,3 a 29,1 días. El motor no lo cierra: lo declara **estancado** (§7.1).
- En el correo, **45 de 72** pasan por el 27 y no por el 17; si no se leen, su recepción es el primer
  21, un día después del envío. Es la regla del §6.2, que no cambia.
Si mañana la plataforma añade un cierre nuevo, con el default benigno la expedición no terminaría
nunca y nadie se enteraría.

**El histórico dice cosas que el listado calla, y la diferencia son días de plazo.** `GET /envios`
devuelve **un solo estado**, el último; `GET /envios/{id}/estados`, el histórico entero. En el
burofax `006catfpdv6` el listado dice `19 · Entregado con albarán` del **17-09** y el histórico
trae un `17 · Entregado` del **14-09**. La fecha que cuenta para el art. 17.2 y para el mes del
art. 17.4 es **la más temprana acreditada**: leer el listado se equivocaría en tres días en un
cómputo de procedibilidad. Por eso `refrescar` lee el histórico de cada envío, uno a uno.

Y el último evento tampoco es el más fuerte: en `006catetonk` el histórico va `21` (11-09), `21`
(12-09) y **`20`** (12-09). Cronología y jerarquía jurídica son ejes distintos.

**El `detalle` del 20 identifica al lector**, lo que matiza el hallazgo API-01 de la R1 («campos
de verificación vacíos: Leído no identifica a nadie»): dice *«El destinatario ‹email› leyó la
comunicación desde la ip ‹ip›»*. Por esa vía sí identifica.

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

**Y el MB incluido depende de la tarifa, no del producto.** El mismo formulario de entrega
electrónica certificada declara **1 MB incluido en el sandbox y 6 MB en producción**. Con nuestros
dos adjuntos no habrá cargo en producción; el plan lo estima igual porque el margen del §5.2 debe
cuadrar, pero la cifra sale de la tarifa del usuario, no de una constante.

**Se cobra un envío por destinatario** —lo dice la propia UI—, así que agrupar destinatarios en un
envío no ahorra nada. Eso quita el único argumento que podría haber a favor de agrupar, y deja la
regla del §5 apoyada solo en lo que importa: cada requerido necesita su propio acuse.

⚠️ **La UI y el contrato de la API discrepan en tres sitios**, y ninguno se ha medido contra el
servidor. El motor se ciñe siempre al **suelo seguro**:

| | Contrato | UI | Motor |
|---|---|---|---|
| Adjuntos de la EEC | `1..10` | 6 ficheros | **6** |
| Adjuntos del SMS Certificado | no declara | 1 fichero | **1** |
| Destinatarios del SMS Certificado | `maxItems: 1` | hasta 30 | **1** | El burofax añade dos avisos propios: los PDF deben ir en **DIN A4** o no se asegura la
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

**La convención ya existe en producción y el motor la adopta**, en vez de inventar otra (rev. 11,
leído por API en `madrid.bd`): los envíos vivos llevan `W-02W9BO - OVC` y `W-04AKM2 - OVC`, es
decir **`<W-code> - <TIPO>`**. Lo único que falta es el ordinal, y solo desde la segunda expedición
del mismo tipo:

```
W-04AKM2 - REQ     requerimiento
W-04AKM2 - OVC     oferta vinculante
W-04AKM2 - REQ 2   segunda expedición del requerimiento (domicilio nuevo, reenvío)
```

Caben: `W-04AKM2 - REQ 2` son 16 de los 20 disponibles. `TIPO` es un enum cerrado y el ordinal lo
calcula el motor contando las expediciones previas del mismo tipo.

Que la convención esté ya en uso tiene además una consecuencia práctica: **el equipo lee esos
identificadores en el portal**, así que el motor no puede escribir algo que a Ana o a Olga les
resulte ajeno.

**El tipo de comunicación es un parámetro obligatorio de `planificar`**, no un dato derivable del
expediente: el mismo expediente da varias comunicaciones y ninguna propiedad suya dice cuál toca.

## 4. Arquitectura

Tres capas, como el resto del proyecto: CLI → core → CRM/Codicert.

### 4.1 Los módulos

- **`core/codicert.py`** — transporte puro: token con su vencimiento, los dos endpoints de envío,
  estados, certificado, listado, crédito. No sabe qué es un expediente.
- **`core/expedicion_certificada.py`** — el criterio del jurídico: planificar, ejecutar,
  refrescar, cosechar.
- **`core/certificado_aportable.py`** — anatomía del certificado, recorte y manifiesto.
- **`core/sudespacho_documentos.py`** — **la subida al gestor documental**, con el contrato del
  §17.1 de `INTEGRACION_SUDESPACHO.md` dentro. Va en la familia `sudespacho_*` aunque este spec sea
  su primer consumidor: no es su dueño, y un cuarto cliente `x-api-key` naciendo dentro del módulo
  de expediciones es exactamente cómo se multiplican los clientes huérfanos.
- **`scripts/codicert.py`** — `plan` · `enviar` · `estado` · `cosechar`.

La lectura de las partes contrarias **no se escribe de nuevo**: `core/sudespacho_relations.py`
ya tiene `get_relaciones(element, exp_id)`, que es exactamente eso.

### 4.2 El puerto de inyección, que es lo que hace probable el diseño

Las cuatro funciones del jurídico reciben un **`EntornoExpedicion`** por keyword, con default
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

**El denominador es el Market Center, no el jurídico** (rev. 2). Quien pagina `GET /envios` no ve
los envíos del jurídico: ve los de `barcelona.bd`, la cuenta compartida por la que sale todo el
bad debt de la plaza. Ese volumen **está sin medir**, y por eso la consulta se acota siempre por
`fecha_inicio`/`fecha_fin`. Conviene además que conste: esa credencial da al motor **lectura de
todo el tráfico certificado de la plaza**, incluidas comunicaciones ajenas al jurídico.

## 5. Quién recibe qué: las reglas del jurídico

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

   **Y la provincia conviene traducirla, aunque no reviente** (rev. 4, corregido en rev. 8). Las
   dos listas tienen 52 valores, **45 coinciden y 7 no**: el CRM escribe en castellano lo que
   Codicert escribe en la lengua cooficial.

   ⚠️ **La rev. 4 dio aquí una alarma falsa y hay que deshacerla.** Escribí que sin la tabla «un
   requerido de la Comunidad Valenciana produce el 422 a mitad de expedición». **Medido contra el
   servidor: no.** `provincia` es obligatoria —con el campo vacío sí salta el error, que es el
   control que acredita que el validador lo mira— pero **no se comprueba contra ninguna lista**:
   `ZZZZZ_NO_EXISTE` pasa sin queja, y el `cp` tampoco se valida (`XXXXX` pasa). La lista cerrada
   vive en la **UI**, no en la API.

   Lo que queda, que es real pero menor: **la provincia se imprime en el sobre**. «Valencia» es
   correcto en castellano y perfectamente repartible, así que el riesgo es de coherencia, no de
   entrega. Se traduce por higiene —mandar lo que la plataforma usa— y **no es un bloqueante**.

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
7. **Por la vía elegida, el texto del SMS lo compone la plataforma** (rev. 5). No hay campo en el
   formulario de entrega electrónica certificada, no lo expone el contrato, y entre los tipos de
   comunicación **personalizables** solo están *Logo*, *Página de lectura*, *Correo de
   notificación* y *Correo de confirmación de firma*. Lo que se controla es el **nombre del
   remitente** (`de`, 60 caracteres), que es lo que el destinatario lee junto al enlace.

   La otra vía —**SMS Certificado**— sí tiene `cuerpo` propio, pero no acredita el acceso al
   contenido que pide el art. 10.2 (§1.1). Se descarta por eso, no por falta de texto.

   Consecuencia práctica que hay que corregir fuera de este spec: el literal de
   `CONVENCIONES_DESPACHO.md` §5 —«EV MMC SPAIN, S.L.U. le remite Oferta Vinculante Confidencial
   (OVC)…»— describe un SMS que **por esta vía no se puede componer**. Donde sí cabe es en el
   **correo de notificación**, que es personalizable, y en el asunto y el cuerpo de la
   comunicación.

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

**El 17 y el 21 son recepción, no lectura — decidido por Nikolai el 2026-09-25 (rev. 16).** La
Declaración de Prácticas del prestador (v2.5, §4.5.5) solo llama **entregada** a la comunicación
leída (20), y su tabla hace del 17 el aviso entregado en el buzón (ETSI D.3, §1.3). Se le planteó
si eso obligaba a dejar de contar el 17 y el 21 como recepción, y decidió que no: **la recepción la
acreditan el 17, el 20 y el 21; el acceso al contenido del art. 10.2, solo el 20.** Es la
clasificación que el motor ya tenía (`RECEPCION` y `ACCESO` en `core/expedicion_certificada.py`),
y no cambia.

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

**El 22, cuando ningún aviso llegó, también cierra** (rev. 17, decisión de Nikolai del
2026-09-26, con los indicios que concreta el plan en su D-1). Es el recordatorio fallido (ETSI D.4):
si en todo el histórico no hay ningún indicio de que un aviso llegara —17, 19, 20, 21 o 27; antes o
después del 22, porque el acuse puede llegar tarde—, el envío queda **cerrado sin entrega** en la
fecha del 22 y su certificado se cosecha como
prueba del intento. **Riesgo aceptado, dicho:** si después llegara un indicio, la cosecha siguiente
saltaría el certificado ya archivado (`ya_estaba`) y el hecho posterior no entraría solo en el
expediente. Medido: 83 días sin cambios tras el 22.

**El año del art. 7.3 tiene dos *dies a quo*** unidos por «respectivamente»: desde la recepción si
la solicitud quedó sin respuesta, desde la terminación sin acuerdo si hubo negociación. El motor no
puede computarlo sin saber cuál se dio, así que **registra la causa de cierre** y, si no la conoce,
lo dice en vez de calcular. Con medidas cautelares el plazo son **veinte días**, no el año.

## 7. Las condiciones económicas van en su propio adjunto

Decisión de Nikolai del 2026-09-17, tomada durante la R1 y mejor que el diseño de la rev. 1.

El envío **no lleva dos adjuntos: lleva los que haga falta**, y lo que el diseño exige es que las
condiciones económicas viajen **solas en el suyo** (rev. 7, tras la pregunta de Nikolai sobre los
envíos reales, que adjuntan también la factura y el documento de la negativa):

| | Contenido | Aportable |
|---|---|---|
| **A** | Requerimiento + la parte general de la OVC (el motor MASC: la invitación a negociar) | **Sí** |
| **B** | Condiciones económicas de la oferta — los dos pagos | **No** |
| **C…** | Factura, oferta aceptada, arras, y cuanta prueba acompañe | **Sí** |

**Los documentos probatorios entran en el aportable.** La factura y el documento que acredita la
negativa —oferta a precio aceptada, arras— **no son contenido de la oferta vinculante**: son los
hechos del caso. El art. 17.4 veda mencionar el contenido de la **oferta**, no la documentación de
la controversia, cuyo objeto el art. 9.1 exceptúa expresamente de la confidencialidad. Solo sale B.

**Caben.** El burofax admite **10 ficheros PDF y 200 páginas en total**; la entrega electrónica
certificada, 6 ficheros y 60 MB. El cuello es el burofax por número de ficheros y el electrónico
por tamaño, que con escaneos de factura y oferta es el que hay que vigilar: en producción van 6 MB
incluidos y el resto se cobra a 0,0288 €/MB.

**Por qué esta línea y no otra.** Satisface los dos preceptos a la vez, que es lo que ninguna de
las alternativas hacía. El art. 10.2 exige acreditar el **intento de negociación** —«la solicitud o
invitación para negociar»—, así que el aportable tiene que contener la invitación; y el art. 17.4
prohíbe mencionar el contenido **de la oferta**, que son sus términos económicos, no la invitación.
Cortar antes (dejando fuera la parte general) blinda el 17.4 y sacrifica el 10.2; cortar después
—la práctica de `CONVENCIONES` §7— hace lo contrario.

**Los dos canales se comportan DISTINTO con los adjuntos, y eso decide qué prueba da cada uno**
(rev. 9, medido con una expedición real en sandbox el 2026-09-17):

| | Burofax | Entrega electrónica certificada |
|---|---|---|
| Adjuntos en el acta | **Fusionados en uno**, con nombre UUID y **una sola huella** | **Uno por uno, con su nombre real y su `sha256`** |
| Orden de la reproducción | sin medir | **el de subida** |
| Portada añadida | sí (asunto y cuerpo son obligatorios) | **ninguna** |

En el burofax `006ar9bel3n` se subieron **tres** ficheros y el acta lista **uno solo**,
`9dc535a2-…-6a1d86d90dfd.pdf`. En la expedición de prueba, el acta de la entrega electrónica lista
`SONDA_PRIMERO.pdf` y `SONDA_SEGUNDO.pdf` **con sus dos huellas**, y coinciden con las calculadas
en local antes de enviar.

**Y se confirma sobre un envío real de E&V**, no solo sobre la sonda: el certificado de la
OVC `006catetonk` lista **dos** ficheros con sus dos huellas, y su reproducción respeta ese orden
—tres páginas del primero, una del segundo—. Que en ese envío el requerimiento, la OVC y las
condiciones fueran **un solo fichero** es decisión de quien lo compuso, no imposición de la
plataforma: **partirlo en A y B habría quedado reflejado en el acta**, con una huella por bloque.
Es exactamente lo que el §7 propone, y este certificado lo acredita.

**Qué significa para la división A/B.** El beneficio probatorio que la rev. 5 le atribuía —que el
aportable siga acreditando el envío de un segundo documento, con su huella, sin su contenido—
**existe en los canales electrónicos y se pierde en el postal**. Como el requerimiento sale por los
tres a la vez, basta con que **uno** lo acredite: el certificado de la entrega electrónica nombra B
y da su huella aunque el del burofax no. La línea A/B se mantiene, y ahora con su fundamento
medido en vez de supuesto.

**Y el nombre neutro de B sigue importando**, justo por eso: en los electrónicos **sí llega al
acta**, así que `ANEXO II.pdf` evita que el propio listado de ficheros anuncie que hay unas
condiciones económicas.

**Y hay una vía mejor que el spec no contemplaba:** el propio certificado dice que las partes
pueden **solicitar acta notarial** de la comunicación durante los cinco años de custodia, y el
portal tiene el botón. Un acta notarial del estado y contenido es prueba más fuerte que un
certificado recortado con la firma rota. Queda anotado como alternativa a valorar por caso, no
como parte del motor.

### 7.1 Cosecha

Cuando una expedición finaliza, `cosechar` baja el certificado de cada envío, **verifica que el
remitente sea el emisor esperado**, y lo sube al expediente con el nombre canónico
`<ASUNTO> - <REF>-<codigo>.pdf` por la vía del §17.1. La subida se verifica por resultado: se baja
lo subido y se compara el `sha256`.

**Lo que no se cosecha, con su motivo** (rev. 17). No hay uno, hay cuatro, y el frontal —`estado`,
`cosechar` y el aportable de F3— dice el de cada envío en vez de «el hecho aún puede mejorar», que
de tres de los 117 envíos reales era falso:

- **canal sin clasificar** — no se sabe en qué culmina; no se cosecha nunca, ni con un cierre, y
  **sus fechas no cuentan** en el reloj del requerido;
- **código sin clasificar** — se arregla en el código, no esperando;
- **estancado** — en curso pero **más de 40 días sin moverse** (el silencio más largo medido antes de
  un cambio es de 29,1 días);
- **en curso** — el hecho aún puede mejorar.

El estancado es un **aviso**, no una clasificación: no hace cosechable nada, y señala la salida que
ya existe, `cosechar --incluir-pendientes`, que baja el certificado con su estado en el nombre sin
ocupar el sitio del definitivo. **Límite declarado:** el aportable se prepara solo sobre el
definitivo, así que un estancado no tiene aportable (`MEJORAS_FUTURAS.md`, con su disparador).
El motivo se mide contra la **hora de la lectura**, que la expedición lleva siempre.

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
- **Acta y reproducción se distinguen por el texto, y el discriminante vale para los DOS tipos**
  (rev. 6, hueco 2 cerrado). Las páginas del acta llevan en cabecera *«Este certificado contiene un
  sello temporal y se encuentra firmado digitalmente con un certificado reconocido»*; las de la
  reproducción no. Medido en los dos:

  | Certificado | Total | Acta | Reproducción |
  |---|---|---|---|
  | Entrega electrónica `006casm113n` | 6 | 1-4 | 5-6 |
  | **Burofax `006ar9bel3n`** | **10** | **1-6** | **7-10** |
  | Entrega electrónica `006catetonk` | 8 | 1-4 | 5-8 |
  | Burofax `006catfpdv6` | 10 | 1-6 | 7-10 |
  | **Burofax `006cdgfj5no`** | **9** | **1-5** | **6-9** |

  Las tres últimas, medidas el 2026-09-21, y la última añade un dato que F3 necesita: **el acta
  del burofax no mide siempre seis páginas**. Crece con el histórico de incidencias, así que no
  hay número fijo que valga y el discriminante del sello temporal no es una comodidad.

  El acta del burofax trae dos secciones que la electrónica no: el **histórico de estados** con sus
  incidencias —«destinatario ausente en el primer intento»— y una **copia del albarán de entrega
  firmado**, con su propia advertencia: se exhibe «únicamente a título informativo… y no como
  prueba legal de la entrega», y el original se pide compulsado notarialmente. Conviene saberlo
  antes de aportarlo como si fuera el acuse.

- **El certificado se emite a fecha de descarga, no de envío.** El del burofax del 23-04-2026 dice
  «Madrid, a 17 de septiembre de 2026». Es la confirmación estructural de la regla que ya estaba
  escrita: un certificado bajado el día del envío dirá «Procesado», y hay que **volver a bajarlo**
  cuando el histórico haya avanzado.

  ⚠️ **Matizado el 2026-09-21: no se emite en cada descarga, se emite UNA VEZ y se cachea.** Los
  tres certificados bajados ese día siguen diciendo «Madrid, a **17** de septiembre», que es
  cuando alguien los bajó por primera vez, y **dos descargas seguidas devuelven los mismos bytes
  y el mismo `sha256`**. Lo que **no** está medido es si se regenera cuando el estado avanza. La
  consecuencia de diseño para F2: el `sha256` del certificado **no** sirve como clave de
  idempotencia —identificaría «este envío en este estado», no «este envío»—, así que la clave es
  el `IdEnvio`.

- **Cómo nombra el certificado a su emisor — y por qué importa dónde se lee** (2026-09-21, y es
  lo que hace verificable el art. 17.2). Lo nombra **dos veces**, y son dos hechos distintos:

  | Dónde | Qué da |
  |---|---|
  | `1. Datos del emisor.` → `Nombre y apellidos/Razón social:` + `CIF:` | la **persona jurídica** (`EV MMC SPAIN, S.L.U.`), idéntica en las siete plazas |
  | bloque `CERTIFICADO` → «…del usuario dado de alta en la web www.codicert.io con nombre de usuario **madrid.bd**.» | la **cuenta emisora**, que es la plaza |

  ⚠️ **`EV MMC SPAIN` aparece NUEVE veces en el documento entero y UNA sola en la página 1.** Las
  otras ocho están en la reproducción de nuestro propio requerimiento, que nombra a E&V sin
  parar. **Una búsqueda global de la razón social daría «emisor correcto» sobre el certificado de
  otro remitente que nos mencione**, que es exactamente el documento que un tercero podría
  aportar: el control sería inerte. La verificación se hace **solo dentro del bloque acotado**
  entre `1. Datos del emisor.` y `2. Datos del receptor.`. Implementado así en
  `core/certificado_lectura.py`, con su control negativo.

  Detalle fino que ya costó un falso resultado: el literal termina en `madrid.bd.`, con el punto
  de la frase pegado al login.

### 7.3 Cómo se localiza B dentro de la reproducción

Se recorta **la reproducción dentro del certificado**, no el documento. Hay tres numeraciones y el
motor debe nombrar siempre cuál usa: página del documento, página de la reproducción y página del
certificado.

**El documento vivo, medido** (hueco 7, 2026-09-17). La plantilla **281** renderizada por la API
sobre un expediente real y convertida a PDF da **tres páginas**:

| Página | Bloque | Cómo se reconoce |
|---|---|---|
| 1 | Requerimiento | Encabezado `OFERTA VINCULANTE CONFIDENCIAL Y PROPUESTA DE NEGOCIACIÓN DIRECTA`; el `100 %` de honorarios y los tres IBAN |
| 2 | OVC, motor MASC | Diez menciones de «oferta vinculante»; el «UN MES» del art. 17.4 |
| 3 | Condiciones económicas | Abre con el literal **`CONFIDENCIAL - CONDICIONES`**; calendario de `DIEZ (10)` y `TREINTA (30)` días |

La línea A/B cae en una frontera de página que ya existe: **A = páginas 1-2, B = página 3**. Y en A
**no hay términos económicos**: ni un importe en euros en todo el documento, el `100 %` pertenece
al requerimiento y el «UN MES» es el plazo legal del art. 17.4.

**Dos instrumentos que la medición del certificado de burofax ha descartado**, y conviene que
consten para que nadie los reinvente:

1. ~~Por el pie de sección.~~ La rev. 2 lo daba por bueno; la plantilla viva lleva **el mismo** pie
   en sus tres páginas. Los dos pies distintos son del prototipo de `W-02SRFU`, otro documento.
2. **Por el orden y el conteo de adjuntos: sirve, pero no basta solo.** La rev. 6 lo declaró
   «falso, medido» apoyándose en que el requerimiento de `006ar9bel3n` aparece el último; **eso era
   una inferencia, no una medición** —nadie sabe en qué orden se subieron aquellos tres ficheros—.
   Lo medido, en la expedición de prueba: **la reproducción sigue el orden de subida** (páginas 5-6
   el primer adjunto, 7 el segundo). Vale como control cruzado del instrumento de abajo, no como
   instrumento único: del burofax no está medido.

**El instrumento que sí funciona: casar el texto.** Para cada página de la reproducción se extrae
el texto y se casa, normalizado, contra las páginas de B. Es independiente del orden, del número de
adjuntos y de que Codicert los fusione.

> ⚠️ **Rev. 13: de dónde sale el texto de B.** Este párrafo decía «el motor compone B, luego
> conoce su texto exactamente», y **en lo construido no es así**: F1 recibe los PDF por `--doc` y
> dejó escrito que partir la plantilla es trabajo del operador (M-9 del plan de F3). F3 lee B de
> **los adjuntos que salieron**, bajados de Codicert con `GET /envios/{id}/adjuntos/{nombre}` y
> verificados contra la huella que lista el acta —3 de 3 coinciden (M-5)—, lo que además es más
> fiable que lo que el operador diga que mandó. Salen de la **entrega electrónica**, la única cuyo
> acta lista los adjuntos uno a uno; y valen para el **burofax** de la misma expedición, porque su
> fichero fundido es la concatenación exacta de esos adjuntos, página a página y en el mismo orden
> (M-4). Una expedición **solo de burofax** no trae de dónde sacarlos, y F3 para y lo dice.
>
> **Lo medido, que fija el instrumento** (M-3): quitada la cabecera que Codicert pone a cada página
> de la reproducción («Código de envío: … Página: N de M»), original y copia coinciden al **100 %**
> en las ocho parejas medidas; la misma plantilla en otra expedición, **0,877-0,939**; páginas
> distintas, **0,39** como mucho. El umbral está en **0,98**. B son las páginas desde la que lleva
> el rótulo **como línea entera** hasta el final de su documento: la palabra «condiciones» sale
> también en el requerimiento y en la factura (M-7), y si el rótulo no cae al final se retira de
> más, nunca de menos, y se avisa de la página arrastrada.
>
> **Y la reproducción real no es el documento de tres páginas de la tabla de arriba**: es el
> refundido **más la factura**, cuatro páginas (M-1). La factura es prueba y se queda.

**Y el literal `CONFIDENCIAL - CONDICIONES` se ha visto funcionar sobre un documento real** (rev.
10): en la OVC `006catetonk`, enviada por correo a un requerido de verdad, aparece en la página 7
del certificado —tercera de la reproducción—, exactamente donde el mapa de arriba lo sitúa. El
discriminante deja de ser una lectura de la plantilla y pasa a estar acreditado sobre un envío que
salió.

**La parada, y hay que calibrarla bien** (rev. 7). La regla es **una sola** y se enuncia por el
lado de B, no por el de la página suelta:

> **Si las páginas de B no se localizan TODAS, el motor para y no produce aportable.**

Enunciarla al revés —«si alguna página de la reproducción no tiene texto extraíble, para»— es lo
que escribió la rev. 6, y **habría bloqueado el caso normal**: los envíos reales adjuntan la
factura y el documento de la negativa, que suelen ser escaneos sin capa de texto. Está medido que
ocurre: las páginas 7 y 8 de `006ar9bel3n` traen 45 caracteres —solo el pie— porque ese adjunto era
una imagen. Con aquella redacción, el motor no habría producido un aportable jamás.

La regla buena es segura por construcción: **si B está localizado entero, lo que quede fuera no es
B**, y se conserva aunque sea ilegible para la máquina. El riesgo de dejar dentro algo confidencial
solo existe cuando B **no** se ha localizado del todo, y ese es exactamente el caso en que se para.
Nuestro B nace de un RTF y lleva texto siempre; si un día no se localizara, es que algo cambió y
hace falta un humano.

> **Rev. 13: la parada, construida, son tres** (`core/certificado_aportable.recortar`), las tres
> antes de entregar nada: (1) una página de B que no se localiza en la reproducción, o que no
> tiene texto con que localizarla, para; (2) una página que se conserva y lleva el rótulo para,
> **también si es del acta**, que no se recorta —es la red de la primera por un instrumento
> independiente—; y (3) el PDF producido **se relee** y tiene que ser exactamente las páginas
> conservadas, sin copia de B ni rótulo. Y una cuarta regla, de las que no se escriben solas: **si
> ningún documento enviado lleva el rótulo, F3 no certifica que el íntegro sea aportable** —o no
> había condiciones, o las había con otro rótulo—: para y lo decide una persona.
>
> **Rev. 14 (R2): el rótulo ABRE las condiciones como título, y la tercera parada relee el
> FICHERO.** Una cita del título en la prosa del requerimiento lo retiraba entero (R2/H-03):
> ahora solo abre las condiciones el rótulo que abre una línea —aunque la extracción lo parta—, y
> una mención en una página que se conserva **para**, diciendo que es una mención. Y la relectura
> ya no mira el texto de las páginas: mira el fichero entero contra una **lista blanca** (§7.4).

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

> ⚠️ **Rev. 13: el discriminante de «cifras» no sirve, y se cambia por el texto de B.** Los tres
> requerimientos reales llevan la **deuda reclamada en euros** («…adeudando… la cantidad de X €»),
> y la factura, base, IVA y total (M-2): un aviso por cifras habría saltado en todo envío. Lo que
> distingue una fuga es el **propio texto de las condiciones**: se buscan sus frases de **8
> palabras** —tras el rótulo y antes de la despedida— en todo lo que se conserva, **acta incluida**,
> que es donde van el asunto y el cuerpo. Medido: cero coincidencias en los tres certificados; con
> 5 o 6 palabras saltan en falso el IBAN de la factura y «de la Oferta Vinculante Confidencial»
> (M-6), y los sintéticos de la suite reproducen esas dos fuentes para que el umbral no se pueda
> bajar sin que un test lo vea. Sigue siendo **aviso, no parada**.
>
> **Los ficheros**, junto al íntegro en `04_Output predemanda/Certificados`:
> `<íntegro> - APORTABLE.pdf` y `<íntegro> - MANIFIESTO.json`. El aportable **no lleva la firma**
> del prestador —recortar la rompe— **ni su sello visible**: el widget de firma de la página 1 se
> quita, porque pintaría «Digitally signed by…» sobre un documento que ya no está firmado (M-8,
> comprobado a ojo sobre el aportable real). Lo que sí conserva es la numeración de Codicert en el
> pie («Página 1 de 8» en un aportable de 7): el salto se ve, y el aportable no aparenta estar
> completo. El recorte es **determinista**, y por eso volver a lanzarlo compara por contenido y ni
> duplica ni pisa. F3 **no sube** el aportable al CRM: el íntegro, que es la prueba, ya lo subió F2.
>
> ⚠️ **Rev. 14 (R2/H-01): el aportable es la IMAGEN de las páginas que se conservan, con una capa
> de texto leída por OCR.** Copiar su estructura arrastraba lo que compartían con las retiradas: el
> formulario de las condiciones (R1) y, podado ese, patrones, fuentes, máscaras y metadatos que
> ninguna página conservada dibujaba (R2, siete vías). Cada remedio cerraba una vía; la imagen
> cierra la frontera: **lo que no se dibuja no está**. Cada página conservada se dibuja **sin
> anotaciones** a 200 ppp —las huellas del acta se leen a ojo— y va como una imagen JPEG; encima,
> una capa de texto **invisible** de OCR (OCRmyPDF + Tesseract, `spa`), que solo ve esos píxeles,
> para que el aportable se pueda buscar y lo lea una LLM (lo pidió Nikolai el 2026-09-25). **Sin
> OCR no hay aportable.** El texto fiel sigue siendo el del íntegro, y el manifiesto (versión 2) y
> el frontal lo dicen. La relectura exige un **perfil**: cada página, su imagen —byte a byte la del
> raster, que el OCR no toca— y como mucho una capa de texto invisible; nada suelto en el fichero; y
> que el OCR no lea el rótulo ni una página que se parezca más a una retirada que a la suya.
> **Idempotencia:** la imagen es determinista y el OCR no, así que volver a lanzar **relee** el
> aportable escrito contra la imagen de hoy, sin pasar el OCR otra vez; un manifiesto sin su
> aportable **para**, porque un aportable repuesto no casaría con él. Y lo que el CRM dijo del
> destinatario va en su propia clave del manifiesto, fuera de su identidad (R2/H-04).
>
> ⚠️ **Rev. 15 (R3): el fichero lo COMPONE el motor, y la relectura lo recompone.** Sustituye tres
> cosas de la rev. 14: OCRmyPDF, el perfil de la relectura y la parada del manifiesto huérfano. La
> R3 enseñó que un fichero escrito por otro tiene más sitios de los que un perfil enumera
> —revisiones anteriores, objetos de otra generación, datos colgados de una fuente, una segunda
> capa que nadie invoca— y que una página puede guardar su imagen sin dibujarla. Ahora el OCR
> (**Tesseract directo**, `spa`) solo devuelve **líneas** —texto y caja— de la imagen de cada
> página, y el aportable se escribe aquí en una **forma fija**: por página, su imagen a página
> completa y un renglón de texto invisible por línea leída, en Helvetica y WinAnsi; sin
> metadatos, revisiones ni objetos sin uso. **La relectura lee los renglones, recompone el fichero
> con la imagen del recorte y exige los mismos bytes**; después exige que ninguna página lleve el
> rótulo, que cada página **dibuje** su imagen tal cual —se dibuja el fichero con PDFium— y que
> esa imagen se parezca más a la página que tocaba que a **cualquier** otra del íntegro, y que
> cada página con texto traiga el suyo (un parecido de 0,30 como poco). **No acredita que cada
> palabra salga de los píxeles**: eso descansa en que el OCR solo los recibe a ellos. Un **aviso
> nuevo** dice cuándo la imagen de una página muestra frases de las condiciones que su texto no
> lleva —un escaneo—. El **título** de las condiciones exige, además, que no le siga nada en
> minúscula en su línea, y una mención antes del título **para** (R3/H-05). El fichero es
> determinista —el mismo OCR sobre la misma imagen da las mismas líneas—, así que un manifiesto
> huérfano **se repone** si el aportable sale con su huella, y si no, para. Manifiesto, versión 3.

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
| **F3** | `core/certificado_aportable.py` + el aportable y su manifiesto + `aportable` | Sí: produce lo que va al juzgado |

> **Rev. 13 (2026-09-25), al construir F3.** El humo (`scripts/_codicert_humo_f3.py`) corrió
> contra **producción**, en solo lectura y fuera del expediente, sobre `W-04AKM2 - OVC`: aportable
> del correo `006catetonk` sin su página 7 y del burofax `006catfpdv6` sin su página 9 —las dos,
> la de condiciones, casada al 1,000 en las tres numeraciones—; `006catf83zx` declarado pendiente;
> factura conservada, rótulo ausente **de lo visible**, huellas de íntegro y aportable iguales a
> las del manifiesto, sello de firma presente en el íntegro y ausente en el aportable; crédito
> 836,9215 € antes y después. **El camino real queda ejercido para Madrid**; las otras seis plazas
> siguen sin credencial.
>
> ⚠️ **Y lo que ese humo NO vio, que es lo importante:** releía el texto de las páginas, no el
> fichero. La R1 (H-01) demostró que **los dos aportables llevaban dentro el formulario de la
> página de condiciones**, porque los certificados reales comparten un `/Resources` entre todas
> sus páginas (§12.4). Remediado y **re-verificado sin red sobre esos mismos certificados**:
> formularios con el rótulo 1 → 0, lo conservado idéntico píxel a píxel salvo el sello. Los dos
> PDF defectuosos solo existieron en el directorio temporal de la sesión.
>
> **Rev. 14:** la R2 enseñó siete vías más, y el aportable pasó a ser imagen con OCR (§7.4).
> **Re-verificado sin red sobre los mismos dos certificados:** ni un stream del íntegro sobrevive en
> el aportable, cada imagen es su página y el OCR lee lo conservado sin leer el rótulo. Y correrlo
> sobre los REALES encontró lo que el sintético no enseñaba: por encima de 1 MB OCRmyPDF linealiza
> —objetos que no cuelgan de nada, que la relectura para— y deja `sys.stderr` cambiado por un
> `StringIO` que se tragaba las trazas. Los dos, arreglados en el adaptador y con su test.
>
> **Rev. 15:** con el aportable compuesto por el motor, **re-verificado sin red sobre los mismos
> dos certificados**: ni un stream del íntegro dentro, lo que dibuja cada página es la suya, el OCR
> se parece a cada original y no lee el rótulo, y **un segundo OCR da el mismo fichero**. OCRmyPDF
> sale del camino del aportable, y con él los dos defectos de la rev. 14.

**Lo que se prueba con doble y lo que no.** Con el puerto del §4.2, el criterio del jurídico se
prueba entera contra dobles. Lo que **no se puede probar sin enviar de verdad** se nombra aquí para
que nadie crea que la suite lo cubre: la anatomía del certificado de burofax, la portada del
burofax y el texto de la notificación SMS. Y la guarda de idempotencia viene **con su control
positivo** —un envío sembrado que la ponga en «ya existe»— y con un mutante que la mate; el
discriminante del §3 es lo que hace que ese mutante pueda existir.

**El mapeo ciudad→usuario no es verificable en sandbox**, donde hay una sola credencial: todas las
plazas colapsan en el mismo usuario. Se acredita la primera vez en producción, leyendo el remitente
del certificado emitido.

> **Rev. 12 (2026-09-21), al construir F2.** El certificado **sí lleva la cuenta emisora**, en su
> bloque `CERTIFICADO` («con nombre de usuario `madrid.bd`»), así que la vía de acreditación
> existe y `cosechar` la ejerce en cada cosecha (§7.2). Queda acreditado para **Madrid**. Las
> otras seis siguen sin medir, y no por falta de instrumento: **de las siete plazas solo Madrid
> tiene credencial cargada** en la máquina — Barcelona, Bilbao, San Sebastián, Santander, Sevilla
> y Valencia no están ni en el registro de usuario ni en el `.env`.
>
> **Y el sandbox no deja entrar:** su `POST /usuarios/acceso` devuelve
> `400 "Error interno, contacte con el administrador"`, que no es «credenciales inválidas». El
> humo de F2 va por eso contra producción, y **solo en lectura**, con el crédito comprobado antes
> y después (medido: 861,0205 € en las dos, 0,0000 € gastados).

## 10. Huecos declarados

1. ~~**Si el texto de la notificación SMS es configurable.**~~ **CERRADO del todo el 2026-09-17**
   (§5 regla 7): **no lo es**. El SMS que llegó al móvil en la expedición de prueba dice
   *«… le ha enviado una comunicación. Acceda <url>»*, con el nombre del remitente delante y nada
   más. Es plantilla fija de la plataforma: lo único nuestro es ese nombre.
2. ~~**La anatomía del certificado de un burofax.**~~ **CERRADO el 2026-09-17** (§7.2) sobre
   `006ar9bel3n`, aportado por Nikolai: 10 páginas, **6 de acta y 4 de reproducción**, y **el
   discriminante del sello temporal funciona igual** que en el electrónico. De paso destapó que
   Codicert **fusiona los adjuntos** y que el orden de la reproducción no es el de envío (§7).
3. ~~**Si la portada del burofax se imprime como página adicional.**~~ **CERRADO el 2026-09-17**
   por diferencia exacta: se bajó el adjunto de `006ar9bel3n` con
   `GET /envios/{id}/adjuntos/{nombre}` y tiene **4 páginas**; la reproducción del certificado tiene
   **4**. **La portada no entra en la reproducción**, aunque el servidor exija `asunto` y `cuerpo`
   y esa portada se imprima en el sobre. La reproducción son los adjuntos y nada más.
4. ~~**El límite de tamaño de los adjuntos.**~~ **CERRADO el 2026-09-17** (§1.4): 6 ficheros, 60 MB
   en total, 1 MB incluido en el precio. **Queda un resto**: la UI dice 6 ficheros y el contrato
   `1..10`, y no se ha medido cuál manda.
5. ~~**Si Codicert figura en la lista de confianza como prestador cualificado.**~~ **CERRADO el
   2026-09-17** (§7.2): sí figura, con tres servicios `EDS/Q` `granted`. El art. 326.4 LEC juega
   para los certificados electrónicos. **Queda un resto abierto**: ninguno de esos tres servicios
   cubre el **envío postal**. El burofax es fehaciente por su propia vía —certifica contenido y
   entrega—; lo que no está verificado es por qué cauce concreto se le reconoce cuando lo cursa
   Codicert.
6. ~~**El volumen de envíos de la cuenta de un Market Center.**~~ **CERRADO el 2026-09-17**
   (§4.3): `barcelona.bd` acumula **1.954** envíos históricos y `madrid.bd` **953**. Son veinte
   páginas para el histórico completo de la plaza más activa, y una o dos acotando por fecha.
   Paginar es barato.
7. ~~**El mapeo página→bloque del documento refundido vivo.**~~ **CERRADO el 2026-09-17** (§7.3):
   la plantilla 281 renderizada da tres páginas —requerimiento, OVC, condiciones—, la línea A/B
   cae en una frontera de página que ya existe, y el discriminante es el literal
   `CONFIDENCIAL - CONDICIONES`. De paso se retiró el discriminante «por el pie» que la rev. 2 daba
   por bueno y que el documento vivo no soporta.
8. ~~**Los 52 valores de `provincia` del CRM** cruzados con lo que el burofax acepta.~~ **CERRADO
   el 2026-09-17** (§5 regla 5): 45 coinciden, **7 no**, y hacen falta traducirse. Afecta a la
   Comunidad Valenciana entera y al País Vasco.

**Balance tras la tanda del 2026-09-17:** de los ocho, **los ocho cerrados**, y solo quedan dos restos menores: el cauce por el que se reconoce la
fehaciencia del burofax y la discrepancia `6` contra `1..10` en el número de adjuntos, más dos restos menores —el cauce de la fehaciencia postal y la discrepancia
`6` contra `1..10` en el número de adjuntos—.

Ninguno de los dos restos condiciona el diseño ni bloquea F1.

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

### 12.1 Qué cubre la R1 y qué NO — cobertura declarada

**La R1 revisó la rev. 1, no esta.** Entre aquel objeto (`d895d1d`) y la rev. 11 hay **760 líneas
añadidas y 225 borradas**: el spec pasó de 374 a 909. El **§3 entero es nuevo** —y es el remedio
del hallazgo más grave de la ronda— y el **§7 está reescrito de raíz**. **Nada de eso lo ha mirado
un revisor.**

Se declara y no se remedia con otra ronda, por dos razones que conviene dejar escritas para que
nadie las confunda con desidia:

1. **La mayor parte de lo añadido es medición, no razonamiento.** Las revisiones 3 a 11 cierran
   huecos contra el servidor, contra certificados reales y contra la lista de confianza. Eso no se
   refuta leyéndolo: se refuta reproduciéndolo, y varias mediciones ya se reprodujeron al
   adjudicar.
2. **Lo que sí es razonamiento puro —el §3 y el §7.3— es exactamente lo que el diff encarnará.**
   La ronda del diff lo cubre leyendo el código que lo implementa, que es donde un defecto deja de
   ser una frase y pasa a gastar 16,97 € y mandar una comunicación irreversible.

Gastar aquí la segunda ronda obligaría a pedir una tercera para el diff, y «la anterior encontró
algo» es un argumento que **nunca se agota**: es el que llevó a encadenar R10→R11→R12→R13 en el
precedente que `CLAUDE.md` documenta. Se para donde la regla dice que se para.

**Dos rondas: la primera está hecha (§11) y la segunda irá sobre el diff.** Son dos **por decisión
expresa**, no por lectura de la tabla de `CLAUDE.md`, que a esta pieza le asigna una: no decide
quién escribe sobre qué copia ni destruye datos de cliente. Se amplía porque **gasta dinero y manda
comunicaciones jurídicas irreversibles a terceros, con efectos de prescripción**, y porque un
defecto aquí no se arregla con un `git revert`.

La R2 la ejecutará **Codex** si tiene cupo a partir del 2026-09-19; si no, Claude Code en sesión
independiente con el mismo registro sin maquillar.

### 12.3 La cobertura de F2 (2026-09-21)

**F2 tuvo UNA ronda, y es lectura de la tabla de `CLAUDE.md`, no decisión.** El fundamento
que amplió F1 a dos —gasta dinero y manda comunicaciones irreversibles a terceros— **no se
traslada**: `refrescar` solo lee y las dos escrituras de `cosechar` (un PDF en el expediente,
un documento en el CRM) son reversibles. Ampliar aquí «porque la pieza es importante» sería
leer la tabla para arriba cuando conviene, que es justo el movimiento que el §11 me anotó.

- **R1 de Codex sobre el diff** (commit `8dd3952`): **NO-SHIP**, 10 hallazgos — 3 `alta`,
  7 `media`—, **los diez confirmados contra la fuente y remediados**.
- Acta literal: [`2026-09-21-codicert-f2-r1-adversarial-review.md`](../plans/2026-09-21-codicert-f2-r1-adversarial-review.md).
  Adjudicación y remedio: §§11 y 12 de [`2026-09-21-codicert-f2.md`](../plans/2026-09-21-codicert-f2.md).
- **Sobre los diez remedios, la cobertura independiente es AUSENTE**, igual que en el §12.2:
  cada uno se escribió con su control visto en rojo antes y la suite va verde con las dos
  semillas, lo que prueba que cada remedio hace lo que dice — **no** que ninguno haya abierto
  algo que nadie fue a buscar.

### 12.2 La R2 se hizo; la R3 queda dispensada — y eso se declara, no se disimula

**La R2 la ejecutó Codex el 2026-09-21** sobre el diff (commit `52c2c0e`, 8.102 líneas): veredicto
**NO-SHIP**, 16 hallazgos —7 `alta`, 9 `media`— y **los dieciséis remediados** ese mismo día. La
adjudicación, hallazgo por hallazgo, está en el §13 del plan; el informe literal, en su acta
hermana. Esta ronda no leyó: **corrió**, con sondas ejecutables que reproducían cada defecto.

**No hay R3, por decisión expresa de Nikolai del 2026-09-21.** Es suya por construcción: el techo
duro de `CLAUDE.md` reserva la tercera ronda a su autorización, y aquí la denegó. Lo que sigue es
la consecuencia, escrita para que nadie la lea de más:

- **Los dieciséis remedios y la pasada de nomenclatura no los ha mirado ningún revisor
  independiente.** Sobre ellos la cobertura es **AUSENTE**. No están refutados: están **sin
  verificar**, que es distinto y menos tranquilizador.
- **Lo que sí los acredita, y no es lo mismo:** cada remedio se escribió con su control visto
  **en rojo antes** del arreglo, y la suite completa va verde con las dos semillas fijas. Eso
  prueba que cada remedio hace lo que dice hacer. **No** prueba que ninguno haya abierto algo que
  nadie fue a buscar — para eso hace falta un lector con interés contrario, y no lo hubo.
- **La pasada de nomenclatura toca `core/`**, que el contrato no exime nunca «por inocente que
  parezca el diff». No se declara exenta por trivial —esa lectura me correspondería a mí, que soy
  la parte revisada, y la regla de cierre dice que lo que hay que argumentar como trivial no lo
  es—: se declara **dispensada por quien tiene el techo duro**. La diferencia importa, porque una
  exención es un juicio sobre el diff y una dispensa es una decisión sobre el coste.

### 12.4 La cobertura de F3 (2026-09-25)

**Una ronda, sobre el diff**, que es la lectura de la tabla de `CLAUDE.md`: F3 no decide quién
escribe sobre qué copia ni destruye datos de cliente —crea dos ficheros nuevos junto al íntegro y
no pisa ninguno—. Con **`gpt-6-astra`·`medium`**, la fila de «escritura sobre datos de cliente…
idempotencia», y la frontera que lo justifica es **silenciosa**: un aportable con la página de
condiciones dentro *parece* correcto —nombre, manifiesto y páginas en su sitio— y su defecto solo
aparece cuando la otra parte lo lee en el juzgado.

- **R1 de Codex sobre el diff** (commit `a87e2d9`): **NO-SHIP**, 7 hallazgos —2 `alta`, 5
  `media`—, **los siete confirmados contra la fuente y remediados**, más dos observaciones
  laterales también remediadas. Acta literal:
  [`2026-09-25-codicert-f3-r1-adversarial-review.md`](../plans/2026-09-25-codicert-f3-r1-adversarial-review.md);
  adjudicación en el §12 del [plan de F3](../plans/2026-09-25-codicert-f3.md).
- **El alto que la justifica, medido en los certificados reales:** las páginas comparten un
  `/Resources` con el Form XObject de cada página de la reproducción, y copiar las conservadas
  metía en el aportable el formulario de las condiciones —invisible, recuperable—. El §7.4 se
  cumple ahora sobre el **fichero**, no sobre lo que se ve: recursos podados a lo que cada página
  dibuja, sin anotaciones, y una relectura del grafo entero que para si queda un solo objeto que
  solo usaban las páginas retiradas.
- **Sobre los nueve commits de la remediación la cobertura independiente era AUSENTE**: cada
  remedio con su test visto en rojo, 26 de 26 mutantes muertos por su test y la suite con las dos
  semillas, lo que prueba que cada remedio hace lo que dice, **no** que ninguno haya abierto algo
  que nadie fue a buscar. Una segunda ronda excede la tabla y la decide Nikolai.
- **R2 de Codex sobre esa remediación, autorizada expresamente por Nikolai el 2026-09-25**
  (`a87e2d9` → `3ae4cbe`, mismo modelo y por la misma frontera): **NO-SHIP**, 7 hallazgos —1
  `alta`, 5 `media`, 1 `baja`—, **los siete confirmados contra la fuente y remediados**. Acta
  literal: [`2026-09-25-codicert-f3-r2-adversarial-review.md`](../plans/2026-09-25-codicert-f3-r2-adversarial-review.md);
  adjudicación en el §13 del plan. **El alto cambió la pieza**, no el remedio: la poda cerraba
  vías de una en una, y el aportable pasó a ser la imagen de lo conservado con su capa de OCR
  (§7.4), con la relectura como lista blanca.
- **La remediación de la R2 NO ha pasado ronda: su cobertura independiente es AUSENTE**, y pesa
  más que la anterior porque la imagen, el perfil y el puerto de OCR son código nuevo. Una R3
  supera el techo de dos rondas: solo la autoriza Nikolai.
- **R3 de Codex sobre esa remediación, autorizada expresamente por Nikolai el 2026-09-25**
  (`3ae4cbe` → `6d950b1`, mismo modelo y por la misma frontera): **NO-SHIP**, 5 hallazgos —2
  `alta`, 3 `media`—, **los cinco confirmados contra la fuente y remediados**. Acta literal:
  [`2026-09-25-codicert-f3-r3-adversarial-review.md`](../plans/2026-09-25-codicert-f3-r3-adversarial-review.md);
  adjudicación en el §14 del plan. **Los cuatro primeros eran la propiedad de la R2 otra vez**:
  la relectura admitía un fichero que no había escrito el motor y trataba de enumerar lo que ese
  fichero podía llevar. Desde la rev. 15 el aportable **lo compone el motor** y la relectura lo
  **recompone** y exige los mismos bytes (§7.4).
- **La remediación de la R3 NO ha pasado ronda: su cobertura independiente es AUSENTE.** La
  composición y la recomposición vuelven a ser una pieza nueva. Una cuarta ronda solo la autoriza
  Nikolai.
