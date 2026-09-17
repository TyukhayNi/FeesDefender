---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-17
---

# El proceso de bad debt de Engel & Völkers

> Cómo viaja una factura impagada de intermediación desde que Finanzas la mete en el fichero de
> morosidad hasta que se presenta la demanda: quién hace qué, con qué plazos, qué documento
> acredita cada paso y dónde vive cada cosa.
>
> **Levantado el 2026-09-17** leyendo los procedimientos escritos de E&V, las cinco tablas de bad
> debt, el CRM y los ficheros reales de un ciclo semanal. Lo medido se marca como medido; lo que
> solo está escrito, como escrito.

**Fuentes primarias**, todas en el Drive de E&V:

| Documento | Dónde |
|---|---|
| Manual procesos reclamación extrajudicial | `02. OPERACIONES / 01. MOROSIDAD / 00. PROCEDIMIENTOS BD` |
| Procedimiento OVC | ídem |
| Procedimiento_Clasificacion_Impago | ídem |
| Plantilla «OFERTA VINCULANTE - OBJETO.rtf» | ídem |
| Cartas emitidas, por semana y plaza | `JURIDICO / CONTINGENCIAS / MOROSIDAD / 02. CARTAS / CARTAS BD <año>` |
| Ficheros de deuda, uno por agrupación de Market Centers | ver §7 |

---

## 1. Quién hace qué

El reparto no está en el organigrama: sale de quién es propietario de cada fichero y de lo que
dice el manual.

| Función | Quién | Qué hace |
|---|---|---|
| Operativa de morosidad | E&V (coordinación de contingencias) | Prepara el **listado semanal por plaza** con las tres vías de notificación. **Pide a Finanzas** el requerimiento y la OVC. Prepara la documentación del expediente, comparte la carpeta con Jurídico y reclama lo que falta. |
| Finanzas | E&V | **Genera** los PDF —factura, requerimiento, OVC— y los **envía** por vía certificada. |
| Jurídico | nosotros | **Firma** la OVC, revisa viabilidad, prepara y presenta la demanda, reporta. |
| Alta en el CRM | Jurídico | Crea el expediente extrajudicial al entrar en revisión de viabilidad (§6). |
| Motivo del impago | Team Leader de ventas | Rellena `Reason for Non-Payment` (§3). |

**La consecuencia que más se olvida: el tramo `01`→`05` es enteramente interno de E&V.** La
operativa pide, Finanzas emite y envía. Jurídico no entra hasta `10. Revisar viabilidad`. Atribuir
a Jurídico los `PIDO BF A FINANZAS` de la columna `Seguimiento Jurídico` es un error de lectura:
**el nombre de la columna dice de qué trata, no quién teclea en ella.**

---

## 2. Los 14 estados

Lista cerrada. La columna se llama `Situacion` en los cinco ficheros de deuda.

| Estado | Cuándo se pone |
|---|---|
| `01. Enviar burofax` | Al actualizar Finanzas el fichero. Objetivo: **≤30 días desde la factura** |
| `02. No enviar burofax` | Cuando Finanzas indica que no procede. Se vuelve a pedir en la siguiente actualización |
| `03. Burofax enviado` | Al enviarse el requerimiento |
| `04. Enviar OVC` | **15 días** desde el envío del requerimiento |
| `05. Enviada OVC` | Enviada por las tres vías |
| `06. Próximo abono` | La factura **no es debida** y procede abonarla |
| `07. Pendiente info` | Jurídico no sabe aún si la factura se debe |
| `08. Próximo write off` | Deuda total **< 2.500 €** — reclamación judicial económicamente inviable |
| `09. Pendiente pago` | Finanzas u operativa informan de pago **en 7 días como mucho** |
| `10. Revisar viabilidad` | 15 días desde la OVC, si se cumplen los dos requisitos del §6 |
| `11. Preparar propuesta` | Siguiente a `10`. **Máximo 60 días desde la fecha de la factura** |
| `12. Preparar demanda` | *(sin definir en el manual)* |
| `13. Prejudicial` | **La factura se cobró o se abonó antes de poner la demanda** |
| `14. Judicial` | *(sin definir en el manual)* |

**`13. Prejudicial` no significa «en fase prejudicial».** Significa cobrada o abonada antes de
demandar. Está verificado contra el dato: las filas en `13` traen `Pdte = 0` y `Cobrada / Abonada`
relleno. Un expediente con la demanda redactada y sin presentar es `12`, no `13`.

---

## 3. El motivo del impago

Lista cerrada, obligatoria, la rellena el TL de ventas en la columna `Reason for Non-Payment`:
`AGENCY_DISPUTE` · `REFUSES_TO_SIGN` · `NO_FUNDS` · `NO_RESPONSE` · `PENDING_SIGNATURE`.

Ante la duda, `NO_RESPONSE`, documentando el último intento de contacto.

---

## 4. El binomio: requerimiento + OVC

No son dos pasos del mismo trámite. Son **dos cartas de naturaleza distinta**.

| | Requerimiento | OVC |
|---|---|---|
| Firma | «Dpto. Jurídico EV MMC SPAIN, SLU» — sin abogado nominado | **el abogado**, en nombre de la Agencia |
| Membrete | operativo del Market Center | societario |
| **Unidad** | **por DEUDOR** — agrega todas sus facturas | **por FACTURA / W-code** |
| Plazo que concede | **7 días** naturales | **30 días** naturales |
| Qué es | reclamación comercial de pago | **MASC del art. 17 LO 1/2025** — requisito de procedibilidad |
| Anexo | IBAN al pie | página aparte de condiciones: dos plazos del 50 % |

**La asimetría es lo que hay que entender.** Un requerimiento puede cubrir cuatro facturas de un
mismo deudor en una sola carta; la OVC se emite una por W-code. De ahí que en las tablas varias
filas compartan `Fecha Burofax` y difieran en `Fecha OVC`. Y de ahí la comprobación obligatoria
antes de demandar: **existe la OVC de *este* W-code, no solo el requerimiento que lo agrupaba**.

**Vías de envío** (procedimiento OVC): correo certificado, SMS certificado y burofax, **a todos
los deudores** que consten. Medido sobre 19 operaciones el 2026-09-17: el burofax de la OVC vuelve
`FALLIDO` en 9 y `ENTREGADO CON ALBARÁN` en 3. La vía que mejor acredita recepción es el **SMS
certificado**; la más usada, el correo.

---

## 5. El reloj del art. 7.3 LO 1/2025

La OVC es el MASC, y abre una ventana para demandar:

> *las partes deberán formular la demanda dentro del plazo de un año a contar […] desde la fecha
> de recepción de la solicitud de negociación […] para que pueda entenderse cumplido el requisito
> de procedibilidad* — art. 7.3 LO 1/2025

Tres consecuencias operativas:

1. **El año corre desde la recepción, no desde el envío.** La fecha exacta sale del certificado,
   no de la columna `Fecha OVC`. Tomar la fecha de envío es el lado seguro.
2. **Cada W-code tiene su propio reloj**, porque cada uno tiene su propia OVC.
3. **No confundirlo con los 30 días de la oferta.** Que la OVC «caduque» a los 30 días es que
   decae la oferta (art. 17.4), no que se pierda la procedibilidad.

**Lo que acredita el requisito no es la carta: es el acuse.** Al preparar la demanda hay que poder
aportar la OVC **y** su certificado de envío con resultado.

---

## 6. La fase de viabilidad — y los dos relojes que no coinciden

### 6.1 Cuándo entra

Se pasa a `10. Revisar viabilidad` a los 15 días de la OVC **si se cumplen dos requisitos
simultáneos**:

1. **Importe > 2.500 €**, sumando la deuda de todos los deudores solidarios. Por debajo,
   `08. Próximo write off`.
2. Que la operación proyectada **se haya consumado** (arrendamiento firmado, escritura otorgada,
   traspaso firmado), lo que en el fichero se ve por `Payment Rate` = «Segunda parte», «Directa» o
   «Alquiler».

> ⚠️ **El manual se contradice en el requisito 2.** Tras enunciarlo, añade que *«en las compraventas
> revisamos la viabilidad si se trata de las facturas de "Primera parte", es decir cuando solo se
> ha firmado las arras y no se ha otorgado la escritura»* — que es lo contrario. **Sin resolver a
> 2026-09-17.** Afecta justo a los expedientes de «Se firmaron Arras», que son los que más se
> atascan.

### 6.2 Qué cuenta como «revisada» — dos definiciones en vigor

| | Manual de E&V | KPI interno de Jurídico |
|---|---|---|
| **Plazo** | 60 días desde **la fecha de la factura** | 90 días desde el **vencimiento de la última factura de la operación** |
| **Cierre válido** | pasar a `11` (viable) o `06` (no viable) | igual: situación `11` o `06` |
| **Además exige** | preparar la documentación y compartir la carpeta | expediente extrajudicial creado en el CRM **con el tiempo imputado como facturable** |
| **Si es inviable** | reclamar el documento esencial al TL; a la semana, escalar a Finanzas recomendando el abono | correo a la administración del cliente, con copia al TL y a Jurídico, recomendando el abono **y motivándolo** |

**Ni el plazo ni el ancla coinciden.** Sesenta días desde la emisión y noventa desde el vencimiento
de la última factura son relojes distintos, y en operaciones con 1.ª y 2.ª parte pueden separarse
meses. Mientras no se unifiquen, **el que obliga hacia el cliente es el del manual**; el otro mide
el desempeño interno.

> ⚠️ **Errata del KPI:** cita el estado objetivo como «10. Preparar propuesta». En el fichero,
> `10` es *Revisar viabilidad* y `11` es *Preparar propuesta*. El estado que quiere decir es el
> **11**. Medido literalmente, el criterio no se cumple nunca.

### 6.3 La salida que el manual ya prevé para lo bloqueado

> *Si en una semana el documento necesario para la reclamación judicial no es aportado, reenvía la
> cadena de los mensajes al Dto. de Finanzas […] recomendando **el abono de la factura** por no ser
> viable la reclamación judicial*

Una semana. No es una recomendación blanda: es el camino escrito para que un expediente sin
documentación no se quede indefinidamente en `10`.

---

## 7. Dónde vive cada cosa

**Ficheros de deuda** — cinco, uno por agrupación de Market Centers (BCN MC1, BCN MC2, MAD,
«SEV/SAN/SSE/BIL», VLC). En cada uno:

- pestaña `BD DD.MM.AAAA` — la operativa de la semana, que se congela en copia cada semana;
- pestaña `JURIDICO` — donde anota Jurídico, acumulativa desde 2018, **nunca se purga**;
- `Listado Mails` y `BP List` — destinatarios y contactos.

`Pdte` vale 1 si sigue viva y 0 si se pagó, se abonó o se dio de baja: **es el filtro que separa lo
vivo de lo cerrado.**

**El layout de columnas NO es igual en los cinco.** Localizar siempre por nombre de cabecera, nunca
por posición: en Madrid no existe `Fecha IVA`, en Valencia no existe `Fecha envío factura abono`, y
en el de Sevilla la cabecera está partida entre las filas 1 y 3, con los datos a partir de la 4.

**Cartas emitidas** — `CARTAS BD <año> / <N.mes> / Del DD.MM.AA al DD.MM.AA / <plaza> /
{REQUERIMIENTOS, OVC}`, más un `CARTAS - TEMPLATE.xlsx` por plaza y semana con el listado que la
operativa pasa a Finanzas: datos de la factura y las tres vías (`MAIL`, `ADRESS`, `MVL`).

**Certificados de envío** — no viven en `CARTAS`, sino en la carpeta de la operación, bajo
`07. RECLAMACIONES` o `_DEMANDA`, con la nomenclatura `D XX - {OVC|REQUERIMIENTO} - {BF|MAIL|SMS} -
{RESULTADO}.pdf`.

---

## 8. El soporte documental de la demanda

Obligatorio en **arrendamientos**: encargo firmado · factura debida · nota informativa de la
sociedad deudora si el deudor es persona jurídica española · contrato de arrendamiento firmado ·
certificado de envío del requerimiento · certificados de envío de la OVC **sin las condiciones**.

Obligatorio en **ventas**: encargo de venta firmado · facturas pagadas y debidas · justificantes de
pago de las pagadas (prueban la conformidad del pagador con el servicio) · nota informativa si
procede · **nota simple que acredita la inscripción de la compraventa** · certificados de envío del
requerimiento y de la OVC.

Requisitos técnicos, que vienen de LexNET: **PDF**, nombre **en mayúsculas**, **sin símbolos
especiales** (comas, puntos, acentos), y patrón `D XX - NOMBRE DOCUMENTO`.

---

## 9. Cómo leer y medir esto

**Las tablas de deuda no se bajan con un conector.** Tres de los cinco ficheros superan el límite
de exportación de Google y un conector devuelve el libro entero por el modelo, sin poder elegir
pestaña — y la primera pestaña de estos ficheros es una copia semanal congelada, no `JURIDICO`.

La vía que funciona es el endpoint CSV por hoja, con el token OAuth que guarda en disco el MCP
`google-despacho`:

```
GET https://docs.google.com/spreadsheets/d/<id>/gviz/tq?tqx=out:csv&sheet=JURIDICO
Authorization: Bearer <token>
```

Medido el 2026-09-17: **1,72 MB de las cinco pestañas en 7,2 s**, a disco, sin pasar por el modelo.

**Para auditar qué cartas existen**, buscar en Drive por número de factura y **clasificar por la
carpeta** (`REQUERIMIENTOS` / `OVC`), nunca por el nombre del fichero. Para los certificados, buscar
por resultado (`LEIDO`, `CADUCADO`, `ENTREGADO`, `FALLIDO`, `ALBARAN`, `ACCEDIDA`) y casar el W-code
**contra la ruta**, no contra el nombre: los certificados se llaman `D XX - …` y no llevan W-code.

---

## 10. Gotchas medidos

- **Los nombres de fichero no siguen convención.** Conviven `CARTA <nº factura>.pdf`,
  `fra <nº factura>.pdf`, `<dirección> <nº factura>.pdf` y `<nº factura>.pdf` a secas — no se sabe
  qué es sin mirar en qué carpeta está.
- **Hay erratas de tecleo que rompen la trazabilidad por número de factura.** Medidas: un dígito de
  más en el número dentro del nombre; un dígito pegado al W-code; una carpeta `REQUERIMENTOS` sin
  la I; una referencia de expediente en el CRM con una letra de menos.
- **El orden del binomio se invierte a veces**: OVC anterior al requerimiento. Cuando pasa, el
  reloj del art. 7.3 arranca igual desde la OVC.
- **Puede haber dos OVC por la misma deuda.** Si las hay, la que cuenta es la que tiene
  certificados; una OVC sin acuse probablemente no llegó a salir.
- **Una carta generada no es una carta enviada.** Se ha medido el caso de un fichero de OVC
  existente desde junio con la operativa reclamándola a Finanzas en julio y agosto.
- **Verificar por resultado, nunca por presencia.** Un barrido que no encuentra algo puede estar
  ciego: antes de declarar un hueco, buscarlo por una segunda vía (dirección, deudor, W-code) y
  mirar dentro de la carpeta. Tres de cuatro huecos detectados el 2026-09-17 eran ceguera del
  instrumento, no ausencia.

---

## 11. Lo que queda abierto

1. La contradicción del requisito 2 de la fase de viabilidad (§6.1).
2. Los dos relojes de la revisión: 60 días desde emisión contra 90 desde vencimiento (§6.2).
3. La errata del estado objetivo del KPI: dice `10`, quiere decir `11` (§6.2).
4. `12. Preparar demanda` y `14. Judicial` no están definidos en el manual.
5. No hay estado para dos situaciones reales: **aplazamiento de pago acordado** a más de 7 días
   (el `09` es para 7) y **acuerdo transaccional firmado pendiente de cumplimiento**.
