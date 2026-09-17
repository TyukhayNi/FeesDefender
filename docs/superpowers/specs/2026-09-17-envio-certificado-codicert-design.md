---
tipo: spec
estado: vigente
creado: 2026-09-17
objeto: envío certificado de burofax y OVC por la API de Codicert (Servicios de MailCertificado S.L.)
rev: "1"
---

# El requerimiento sale solo: burofax, correo y SMS por la API de Codicert

Encargo de Nikolai del **2026-09-17**: los burofaxes y las OVC ya preparados —el PDF sale del
CRM— tienen que salir por **codicert.io** por los **tres canales a la vez**: burofax postal,
correo electrónico y SMS, **a todos los requeridos**. Dos requeridos son dos correos y dos SMS
si constan; y **un burofax por domicilio distinto**. Al terminar, hay que **descargar los
certificados** y producir la versión **recortada** que se aporta como prueba.

Este spec fija el diseño. No hay prototipo: lo que hay es el contrato de la API leído, el
proceso real medido en producción y la anatomía de un certificado abierto en disco. Todo lo que
sigue con cifra está medido el 2026-09-17 salvo que se diga otra cosa.

## 1. El contrato de la API, medido

Documentación en `https://ws.codicert.tk/` (Redoc sobre `rest.json`, OpenAPI 3.0, versión
4.2.1 del prestador). **Las dos bases existen y responden**, verificado por resultado —un
`POST /usuarios/acceso` con credenciales falsas devuelve en ambas el mismo
`400 {"estado":"KO","mensaje":"No se pudo iniciar la sesión…"}`, no un 404:

| Entorno | Base API | Portal |
|---|---|---|
| Sandbox | `https://ws.codicert.tk/v2` | `https://usuarios.codicert.tk` |
| Producción | `https://ws.codicert.io/v2` | `https://usuarios.codicert.io` |

**Autenticación.** `POST /usuarios/acceso` con `{usuario, clave}` —las mismas del portal—
devuelve un hash de 32 hex que viaja después como `Authorization: Bearer <hash>`. No hay
API-key estática: el token se pide por sesión.

### 1.1 Los tres canales son DOS endpoints, y esto es lo que más cambia el diseño

| Canal del despacho | Endpoint | Límite duro |
|---|---|---|
| Burofax postal | `POST /envios/burofax` | `destinatarios` es un array de **exactamente 1**; adjuntos **solo PDF**; solo España |
| Correo certificado | `POST /envios/entrega-electronica-certificada` con `tipo_entrega: "correo"` | adjuntos 1..10, varios tipos |
| SMS certificado | **el mismo endpoint**, con `tipo_entrega: "sms"` | ídem; el móvil ha de casar `^[67]\d{8}$` |

El «SMS» del proceso de la casa **no es** `POST /envios/sms-certificado`. Ese producto existe y
es texto pelado —`cuerpo` más un móvil, sin adjunto—, y no sirve para remitir un documento. Lo
que se usa es la **entrega electrónica certificada notificada por SMS**, que entrega el
documento. De ahí el literal de `CONVENCIONES_DESPACHO.md` §5, *«Consulte el documento
adjunto»*: hay documento que consultar porque el canal lo lleva.

Consecuencia operativa que gobierna todo el motor: **el burofax admite un destinatario por
llamada**. Dos domicilios son dos llamadas, siempre, sin excepción en el contrato.

### 1.2 El resto de la superficie que se usa

```
GET  /envios                               listado paginado (100 máx. por página)
GET  /envios/{IdEnvio}/estados             histórico de estados certificados
GET  /certificados/comunicacion/{IdEnvio}  el certificado, en PDF
GET  /certificados/eml/{IdEnvio}           el EML de la comunicación
GET  /envios/{IdEnvio}/adjuntos/{Adjunto}  el adjunto tal como se envió
GET  /usuarios/credito                     crédito del usuario
```

`id_personalizado` admite **20 caracteres** y **se puede repetir a propósito** en varios envíos
—lo dice su descripción—. Un W-code son 8: cabe de sobra.

### 1.3 Los estados que importan

La plataforma distingue 43 códigos. Para el despacho solo cuentan seis, y la frontera entre los
tres primeros es la que decide plazos:

| Código | Título | Qué significa para nosotros |
|---|---|---|
| 5 | Procesado | **No es entrega.** Es lo que devuelve el certificado emitido al enviar |
| 27 | Entregado en el servidor | El correo llegó al servidor del destino, nadie lo ha abierto |
| 17 | Entregado | Entrega acreditada |
| 20 | Leído · Documentación accedida | Acceso al contenido. Es lo que pide el art. 17.2 |
| 28 | Rechazado | Entrega fallida por rechazo |
| 42 / 40 | Fallido / Caducado | Sin entrega |

Ya está escrito en la memoria del despacho y se repite aquí porque el motor tiene que
codificarlo: **«Procesado» no es «Entregado»**, y una comunicación cuyo certificado dice
Procesado no acredita recepción.

### 1.4 El coste, que no es simétrico

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
consecuencia económica que el plan de expedición debe poner delante antes de gastar.

## 2. El proceso real, medido en producción

Cuenta maestra `engelvoelkers` en `usuarios.codicert.io`, **25 subusuarios**. Envíos del
subusuario `barcelona.bd` del 10-09-2026, referencia `BCN-OS-008684 - OVC`:

| Hora | Tipo | Destinatario | Estado |
|---|---|---|---|
| 13:05:34 | Burofax | TUV SUD IBERIA, S.A. | Entregado |
| 13:02:57 | Entrega Electrónica Certificada | 34645508869 | Recordatorio lectura entregado |
| 13:01:27 | Entrega Electrónica Certificada | JoseMaria.Arnau@tuvsud.com | Leído |

Tres envíos, tres canales, **un mismo `id_personalizado`**. Ese campo es el hilo que cose la
expedición, y ya se usa así sin que nadie lo hubiera escrito. El motor no inventa una
convención: adopta la que está en producción.

El detalle del burofax confirma además el mapeo de la ficha postal: `nombre` es la razón social
(«TUV SUD IBERIA, S.A.»), `a_atencion` la persona («Sr. Jose María Arnau»), y debajo dirección,
población, provincia, CP y un teléfono de contacto.

### 2.1 El emisor sale del expediente, no se teclea

Decisión de Nikolai del 2026-09-17: **los envíos salen del usuario `.bd` del Market Center**
que reclama, que es lo que ya se hace —el certificado del W-04A6LI salió de `valencia.bd` y el
OVC de TUV SUD de `barcelona.bd`—.

El mapeo es determinista y no necesita tabla nueva: las **siete ciudades canónicas** de
`core/ciudades.py` tienen cada una su usuario en Codicert.

| Ciudad (`core.ciudades.CIUDADES`) | Usuario Codicert |
|---|---|
| Barcelona | `barcelona.bd` |
| Bilbao | `bilbao.bd` |
| Madrid | `madrid.bd` |
| San Sebastián | `sansebastian.bd` |
| Santander | `santander.bd` |
| Sevilla | `sevilla.bd` |
| Valencia | `valencia.bd` |

`ciudades.ciudad_de_equipo()` deriva la ciudad del código de equipo del expediente (`BaRS7` →
Barcelona), así que el emisor se resuelve solo desde el expediente.

## 3. Arquitectura

Tres capas, como el resto del proyecto: CLI → core → CRM/Codicert. Tres módulos nuevos, uno por
responsabilidad, más el comando.

### 3.1 `core/codicert.py` — transporte

Cliente de la API. **No sabe qué es un expediente.** Recibe datos ya resueltos y devuelve lo
que dice el servidor.

```
token(usuario, clave, *, entorno) -> str          # cachea en memoria, no en disco
enviar_burofax(token, destinatario, pdf, *, asunto, cuerpo, id_personalizado) -> IdEnvio
enviar_eec(token, destinatarios, pdf, *, tipo_entrega, asunto, cuerpo, id_personalizado) -> IdEnvio
estados(token, id_envio) -> list[Estado]
certificado(token, id_envio) -> bytes
listar_envios(token, **filtros) -> Iterator[EnvioSimple]
credito(token) -> Decimal
```

Errores tipados —`CodicertAuthError`, `CodicertDatosInvalidosError` (el 422), `CodicertError`—
porque el 422 trae el detalle de qué falta y hay que poder enseñarlo sin que se confunda con
una caída.

### 3.2 `core/expedicion_certificada.py` — la lógica del despacho

Aquí vive todo lo que es criterio de la casa:

```
planificar(expediente_id) -> Plan
ejecutar(plan, *, confirmado) -> Expedicion
refrescar(referencia) -> Expedicion
cosechar(referencia) -> list[CertificadoCosechado]
```

`Plan` es una estructura inspeccionable, no un efecto: lleva el emisor resuelto, la lista de
envíos previstos con su canal y su destinatario, el documento elegido con su `sha256`, el coste
estimado desglosado, y **las ausencias declaradas**.

### 3.3 `core/certificado_aportable.py` — anatomía y recorte

```
anatomia(pdf) -> Anatomia          # qué páginas son acta y cuáles reproducción
recortar(pdf, paginas_retiradas) -> tuple[bytes, Manifiesto]
```

### 3.4 `scripts/codicert.py` — el comando

`plan` · `enviar` · `estado` · `cosechar`. Cuatro verbos, cada uno con su salida legible.

### 3.5 Dónde vive la verdad

**La fuente de verdad son los envíos en Codicert**, consultados por `id_personalizado`. El
índice local es caché y se puede borrar sin perder nada.

La alternativa —un JSON de estado por expediente— se descarta a propósito: crearía una segunda
fuente de verdad sobre hechos que son de la plataforma, y mentiría en cuanto alguien enviase
algo desde el portal en vez de desde el motor. Es el Drift que `GOBERNANZA_FUENTES_VERDAD.md`
lleva cinco casos documentando.

El precio de esta decisión, y se paga a conciencia: **`GET /envios` no filtra por
`id_personalizado`** —probados cinco parámetros de búsqueda, los cinco devuelven el total sin
filtrar—, así que localizar una expedición exige traer páginas y filtrar en casa. Con 100
elementos por página y el volumen real del despacho, es barato; si algún día no lo fuese, el
remedio es el índice local, que ya existe como caché.

## 4. Quién recibe qué: las reglas del despacho

Entrada: el expediente. Del CRM salen las partes contrarias por su relación con el expediente,
y `clientes_contrarios` ya tiene todos los campos necesarios —`nombre`, `1apellido`,
`2apellido`, `direccion`, `poblacion`, `provincia`, `cp`, `email`, `movil`, `nif_cif`—.

1. **Correo y SMS: uno por cada requerido**, con su propio envío. Nunca se agrupan dos
   requeridos en un mismo envío electrónico, aunque el endpoint lo permita: cada uno necesita
   su propio acuse.
2. **Burofax: uno por domicilio distinto.** Dos requeridos con el mismo domicilio comparten
   sobre; con domicilios distintos son dos envíos.
3. **Cuando dos requeridos comparten sobre**, ambos nombres van en el campo `nombre` del
   destinatario postal, separados por « Y », y `a_atencion` queda para la persona de contacto
   si la hay. El certificado acredita entonces la entrega **en ese domicilio**, no la recepción
   personal de cada uno; queda dicho aquí para que nadie lo lea de más al aportarlo.
4. **Lo que falta se declara, no se inventa.** Un requerido sin móvil sale en el plan como «sin
   canal SMS» y así queda en el registro. No hay canal por defecto ni sustitución silenciosa.
   Un requerido **sin ningún canal** detiene el plan: no se envía una expedición coja sin que
   alguien lo decida.
5. **El móvil se valida contra el patrón del contrato** (`^[67]\d{8}$`) antes de gastar. Un
   fijo en el campo `movil` del CRM se rechaza en el plan, no en el 422.

### 4.1 La puerta humana

`plan` no envía. Escribe el plan, lo enseña con el coste desglosado y termina. `enviar` exige
el plan y una confirmación explícita.

No es ceremonia: un burofax cuesta 16,97 €, y lo que sale por el otro lado es una comunicación
jurídica irreversible a un tercero. Ninguna automatización de la casa debe poder gastarlos sin
que alguien haya leído a quién.

### 4.2 Idempotencia

`enviar` **consulta antes de mandar**: si ya existen envíos con ese `id_personalizado` en la
plataforma, enseña cuáles y no los repite. Un fallo a mitad de expedición —tres canales por dos
requeridos son cinco o seis llamadas— se reanuda completando lo que falta, nunca repitiendo lo
hecho. Repetir un burofax cuesta diecisiete euros y ensucia la prueba con dos certificados del
mismo requerimiento.

## 5. Del envío a la prueba: qué se registra

`estado` no se limita a imprimir el estado actual. Traduce el histórico a los hechos que el
§3.3 del spec del envío único exige acreditar, y **distingue el estado del envío del estado de
la expedición**: una expedición está entregada cuando lo están todos sus destinatarios, no
cuando lo está el primero.

Se registra, por envío: código de envío, canal, destinatario, fecha de cada estado con su
código, y la fecha de la **primera** que acredita recepción. De ella cuelgan los plazos del art.
10.4 y el año del art. 7.3, así que no puede quedar en «entregado, más o menos».

**Entrega fallida.** Si un canal no acredita recepción, el motor lo dice y no compensa con los
otros. Conserva el intento —que sirve al art. 7.1— y deja la decisión de reintentar por otro
canal idóneo a quien lleva el caso.

## 6. Los certificados: cosecha y recorte

### 6.1 Cosecha

Cuando una expedición finaliza, `cosechar` baja el certificado de cada envío
(`GET /certificados/comunicacion/{IdEnvio}`) y lo sube al gestor documental del expediente con
el nombre canónico de la casa, `<ASUNTO> - <REF>-<codigo>.pdf`, por la vía ya medida:
presigned URL de S3, `PUT` de los bytes, `POST /api/documents` con `origen_id` y
`relatedRegisters`. La subida **se verifica por resultado**: se baja lo subido por su
`downloadUri` y se compara el `sha256`.

### 6.2 La anatomía del certificado, medida

Abierto en disco el certificado `006casm113n` (gdocu 42990 del W-04A6LI, 6 páginas):

- **Va firmado digitalmente.** `AcroForm` con `SigFlags: 3`, un `/ByteRange`, `adbe.pkcs7` y
  `DocMDP`. **Recortar páginas rompe la firma**: el PDF resultante no valida y el visor lo
  marcará como alterado. Esto vale para cualquier criterio de recorte, así que no es argumento
  a favor de ninguno; es la razón de que el recorte tenga que nacer como **documento derivado
  con trazabilidad**, y nunca presentarse como «el certificado».
- **Acta y reproducción se distinguen por el texto, no por contar páginas.** Las páginas del
  acta llevan en cabecera *«Este certificado contiene un sello temporal y se encuentra firmado
  digitalmente con un certificado reconocido»*; las de la reproducción del adjunto no la
  llevan. En ese certificado: páginas 1-4 acta, 5-6 reproducción.

El motor usa ese discriminante. No cuenta páginas fijas: las mide.

### 6.3 El recorte, y la tensión que se declara

**Decisión de Nikolai del 2026-09-17: recorte por páginas, como hasta ahora** — el criterio de
`CONVENCIONES_DESPACHO.md` §7 («D 15 / D 16 / D 17 CERTIFICADOS OVCs sin la página del
contenido económico»), por continuidad con lo ya aportado en procedimientos vivos.

Queda dicho, porque callarlo sería maquillar el registro: el §3.4 de
[`2026-09-15-reclamacion-extrajudicial-envio-unico-design.md`](2026-09-15-reclamacion-extrajudicial-envio-unico-design.md)
—hallazgo H-02, adjudicado como confirmado— sostiene lo contrario. Su criterio es de
**información permitida** y no de páginas quitadas, porque el art. 17.4 LO 1/2025 dice «sin que
pueda hacerse mención a su contenido» y el recorte por páginas deja visible el cuerpo de la
OVC. Con el documento refundido, que es requerimiento (p. 1), OVC (p. 2) y condiciones
económicas (p. 3), retirar solo la tercera deja la oferta entera en la segunda.

El diseño respeta la decisión y añade el único remedio compatible con ella: **el motor avisa**
cuando, tras el recorte, la reproducción conserva texto de la OVC. Avisar no es vetar. La
decisión de aportar sigue siendo del letrado, caso a caso, con el aviso delante.

### 6.4 Qué produce el recorte

Tres cosas, y las tres se archivan:

1. El **certificado íntegro**, con su firma intacta, en el expediente. Es lo que se custodia.
2. El **aportable recortado**, como fichero nuevo y nombre distinguible.
3. Un **manifiesto** junto al aportable: código de envío, `sha256` del íntegro, páginas
   conservadas, páginas retiradas y el aviso del §6.3 si saltó. Sin él, el recorte es un PDF
   sin genealogía; con él, cualquiera puede cotejarlo contra el original.

## 7. Credenciales y entornos

Las claves viven **solo en `.env`** —gitignored— o en variables de entorno, nunca en el árbol
ni en el chat. Nomenclatura:

```
CODICERT_ENTORNO=sandbox|produccion
CODICERT_SANDBOX_USUARIO / CODICERT_SANDBOX_CLAVE
CODICERT_BARCELONA_USUARIO / CODICERT_BARCELONA_CLAVE
…una pareja por ciudad de las siete…
```

El motor **arranca en sandbox por defecto**. Producción exige que la orden lo diga, y el plan
imprime el entorno en su cabecera. E&V pidió expresamente por correo el 2026-09-07 que las
pruebas de integración se hagan contra el entorno de pruebas, «así no se cobrará nada y se
pueden hacer varias pruebas sin afectar la información ni el coste».

Las plazas que no tengan credenciales cargadas no impiden que el motor funcione para las
demás: se añaden al `.env` cuando lleguen, sin tocar código.

## 8. Fases

| Fase | Qué entrega | Utilizable sola |
|---|---|---|
| **F1** | `core/codicert.py` + `planificar` + `ejecutar` + `plan`/`enviar` | Sí: sustituye el picado manual del envío |
| **F2** | `refrescar` + `cosechar` + subida al gestor documental + `estado`/`cosechar` | Sí: cierra la prueba del envío |
| **F3** | `core/certificado_aportable.py` + el aportable y su manifiesto | Sí: produce lo que va al juzgado |

## 9. Huecos declarados

Lo que no sé, dicho como lo que es, para que nadie lo lea como resuelto:

1. **Si el texto del SMS es configurable.** El esquema de la entrega electrónica certificada no
   expone campo para el cuerpo del SMS de notificación —`cuerpo` es el de la comunicación, que
   se lee tras el enlace—. El literal de la casa (`CONVENCIONES_DESPACHO.md` §5) tiene que
   caber en algún sitio, o no cabe. **Se mide en sandbox antes de escribir esa línea.**
2. **Cuántas páginas de acta trae el certificado de un burofax.** He medido el de una entrega
   electrónica certificada (4 de acta sobre 6). El discriminante textual del §6.2 no depende del
   número, pero no está comprobado que la cabecera sea idéntica en el certificado postal.
3. **Si la portada del burofax (`asunto` y `cuerpo`) se imprime como página adicional** y, por
   tanto, altera el recuento de páginas del documento reproducido en el certificado.
4. **Qué devuelve `GET /envios` cuando el mismo `id_personalizado` tiene seis envíos** — que
   los devuelva todos es la hipótesis, no una medición.

Los cuatro se cierran con una expedición completa en sandbox, que es el primer hito de F1.

## 10. Revisión adversarial

**Dos rondas**: una sobre este diseño y otra sobre el diff. El radio de daño no es el tamaño
del código: la pieza **manda comunicaciones jurídicas irreversibles a terceros, con coste y con
efectos de prescripción**. Un defecto aquí no se arregla con un `git revert`.

**La ejecuta Claude Code en sesión independiente**, no Codex: Codex está sin cupo hasta el
2026-09-19 (indisponibilidad real, comunicada por Nikolai el 2026-09-17). Se registrará en el
acta como `revisor: Claude Code (sesión independiente)` —nunca como «Codex»— y la adjudicación
declarará en prosa que **la independencia es más débil**, porque autor y revisor son el mismo
modelo y comparten puntos ciegos. Condiciones completas en `AGENTS.md` §«Revisor sustituto».
