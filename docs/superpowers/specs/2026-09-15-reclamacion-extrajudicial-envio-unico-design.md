---
tipo: spec
estado: vigente
creado: 2026-09-15
objeto: plantillas de reclamación extrajudicial del CRM sudespacho (carpeta 375) + documento refundido requerimiento/OVC
rev: "2"
---

# La reclamación extrajudicial en un solo envío

Encargo de Nikolai del **2026-09-15**: el proceso extrajudicial de vueltas y negativas consta hoy
de **dos** envíos certificados —primero el requerimiento, quince días después la oferta vinculante
confidencial— y quiere **uno**, con **menos formularios**, que **engloben los dos pasos** y en los
que **no haya que picar tantos datos**.

Este spec fija el diseño. El prototipo ya existe y se construyó primero, a propósito: el
requerimiento refundido de `W-02SRFU`, en castellano e inglés, en su `04_Output predemanda`. Lo
que sigue generaliza ese documento, no lo anticipa.

> **Rev. 2 (2026-09-15).** Reescrito tras la R1 adversarial: 12 hallazgos, 12 confirmados y un
> extremo refutado. La corrección de fondo es la del **§3.1** —el art. 17.4 dice «un mes», no
> «treinta días naturales»— y las secciones **§3.3**, **§3.4** y **§9** son nuevas. Adjudicación
> en el §8; acta literal en
> [`…-r1-adversarial-review.md`](2026-09-15-reclamacion-extrajudicial-envio-unico-r1-adversarial-review.md).

## 1. La auditoría, medida

Volcado del catálogo `templates/rtf` del CRM el 2026-09-15: **392 plantillas**. La carpeta **375**
es la de reclamaciones E&V, con **29 formularios**:

| Familia | N | Detalle |
|---|---|---|
| Burofaxes ofensivos (E&V reclama) | **10** | vuelta ×2, negativa ×5, exclusiva, reserva ×2 |
| Burofaxes defensivos (E&V reclamado) | 4 | devolución honorarios ×2, LAU 20, responsabilidad profesional |
| Burofaxes de consultores | 3 | apropiación indebida, secreto empresarial, cese de infracción |
| Burofaxes genéricos | 4 | genérico ×2, impago rentas, hoja de reclamación |
| **Ofertas vinculantes confidenciales** | **2** | ordinaria (310) y «secreto empresa» (321) |
| Acuerdos transaccionales | 4 | negativa, pago cantidad, reserva, exconsultor |
| Anexos | 2 | cuestionario de viabilidad, alegaciones de consumo |

**Las tres muestras, que no son la misma y en la rev. 1 se confundían** (H-09). Se renderizaron
**22** plantillas contra el expediente 652: las 21 del cuadro de defectos más el cuestionario de
viabilidad (171), que no es una carta y por eso queda fuera de ese cuadro. El cuadro cuenta
**21**; el grep del pie catalán se hizo sobre los **22 ficheros RTF** crudos, porque la conversión
a texto plano descarta cabecera y pie y allí es donde vive esa cita. Los identificadores de cada
muestra están en el **§9**.

| Defecto | Denominador | Afectadas |
|---|---|---|
| Huecos `[XX]` (ciudad, fechas, precio, porcentaje, importe) | 21 plantillas analizadas | **20** |
| Doblete singular/plural (`Ud./s.`, `subscribó/ieron`, `le/s`) | 21 plantillas analizadas | **8** — hasta 31 ocurrencias en una sola |
| Tres IBAN (BCN/VAL/MAD) que hay que podar a uno | 21 plantillas analizadas | **9** |
| Pie que cita `121-11.c) CCCat`, derecho catalán | 22 ficheros RTF crudos | **14** |

Del CRM se autorrellenan **dos** campos: `Referencia_Cliente` y `cuantia`. Los demás huecos no se
pueden autorrellenar **porque los campos no existen**. Los del elemento `extrajudiciales` son:
`costas, cuantia, Fecha_alta, fecha_alta_hist, historico, intereses, Notas, numero_anterior,
Numero_Expediente, online, Profesional, Referencia_Cliente, referencia_historico,
Referencia_Propia, saldo_*, serie_expediente, Tipo_Asunto, Tipo_Procedimiento, total,
total_pendiente, profesional_asignado, tags, tnm_posicionprocesal, tnm_siniestro,
dias_sin_actuaciones`. No hay ciudad del Market Center, ni IBAN, ni fecha de encargo, ni precio,
ni porcentaje.

Hay dos campos con prefijo **`tnm_`**. Eso acredita que existen campos propios; **no** acredita
por sí solo que se puedan crear otros, ni con qué permisos ni por qué vía. Es una inferencia y se
rotula como tal (H-09).

### 1.1 Lo que corrige la intuición de partida

Medido sobre los diez burofaxes ofensivos: **48 grupos de párrafo distintos**, y solo **4**
compartidos por cinco o más plantillas (la línea `REF:`, la apertura, el cierre y el recitativo
del acuerdo de mediación). **No son diez copias de un formulario: son diez teorías del devengo.**
Fundirlas en un formulario único sería una pérdida. El criterio de agrupación está en el §9.

La duplicación real está en dos sitios, y ninguno es el bloque de hechos:

1. **El motor MASC**, clonado palabra por palabra en las dos OVC salvo el singular/plural y la
   palabra del concepto reclamado («Honorarios» → «Indemnización»).
2. **El recitativo** —quién es la Agencia, qué se firmó, cuánto se debe— que la OVC repite entero
   después de que el requerimiento ya lo haya dicho, quince días antes.

## 2. El hallazgo legal que condiciona el diseño

Verificado contra el texto consolidado del BOE ([BOE-A-2025-76](https://www.boe.es/buscar/act.php?id=BOE-A-2025-76)),
Título II de la Ley Orgánica 1/2025:

- **Art. 5.1**: el requisito de procedibilidad se cumple, entre otras vías, «si se formula una
  oferta vinculante confidencial». **Nada exige un requerimiento previo separado**: la
  refundición no tropieza aquí.
- **Art. 17.3**: «La oferta vinculante tendrá carácter confidencial **en todo caso**, siéndole de
  aplicación lo dispuesto en el artículo 9.»
- **Art. 9.2**: las partes «no podrán declarar o aportar documentación derivada del proceso de
  negociación **o relacionada con el mismo**». **Art. 9.3**: la autoridad judicial «la inadmitirá
  y dispondrá que no se incorpore al expediente», **además de la responsabilidad que dicha
  infracción genere**.
- **Art. 9.1**: la confidencialidad rige «salvo la información relativa a si las partes acudieron
  o no al intento de negociación previa **y al objeto de la controversia**».
- **Art. 17.4**: al demandar «basta acreditar la remisión … a cuyo documento procesal se ha de
  acompañar el justificante de haberla enviado **y de que la misma ha sido recibida** por la parte
  requerida, sin que pueda hacerse mención a su contenido». **La rev. 1 truncaba este artículo en
  «basta acreditar la remisión» y con ello se comía el requisito de recepción** (H-05).

**Consecuencia.** El requerimiento lleva en su pie una declaración que dice que la comunicación
«cumple los requisitos del requerimiento previo fehaciente y justificado a los efectos de la
imposición de la condena en costas (artículo 395.1.2 LEC) y de la reclamación extrajudicial a los
efectos de la interrupción de la prescripción (artículo 1973 CC)». Si el requerimiento se funde
con la OVC en un texto indistinguible, ese texto pasa a ser documentación relacionada con la
negociación y **puede ser inadmitido**. Los dos sobres de hoy no son lastre burocrático: existen
porque uno tiene que poder aportarse y el otro no.

### 2.1 Qué se pierde si la inadmisión prospera, y con qué se sustituye

La rev. 1 listaba dos efectos. Son más, y conviene separar **perder una prueba** de **perder un
efecto jurídico** (H-03):

| Efecto que descansa en el bloque A | Qué pasa si A se inadmite | Fuente alternativa |
|---|---|---|
| Costas por requerimiento previo fehaciente (art. 395.1.2 LEC) | Se pierde el soporte documental | Ninguna equivalente. Es la pérdida más cara |
| Constitución en mora y su fecha (art. 1100 CC) | Se pierde la prueba de la interpelación | Cualquier otra intimación anterior que conste |
| Interrupción de la prescripción (art. 1973 CC) | Se pierde ese soporte | **El art. 7.1 da fundamento propio**: la solicitud de MASC interrumpe desde el intento de comunicación. No se pierde el efecto, se pierde una vía |
| Prueba de qué se reclamó y cuándo | Se pierde el uso de A para acreditarlo | Contratos, facturas y reconocimientos, que son independientes del crédito |
| Acreditación del intento para la procedibilidad | **No se pierde** | Arts. 9.1, 10 y 17.4, con sus justificantes |

**Un matiz que se adjudica en contra del revisor** y consta en el §8: para el art. 7.4, acreditar
que la contraria **no acudió** sí está exceptuado por la primera rama del art. 9.1 («si las partes
acudieron o no al intento de negociación previa»). Lo que no se puede aportar es el **contenido**
de lo que dijeron. La vía estrecha del art. 9.2.b —impugnación de la tasación de costas, «a esos
únicos fines»— es adicional, no la única.

**SIN VERIFICAR**, y se declara: el tenor y la aplicación de los arts. 1100, 1101, 1107 y 1973 CC,
del art. 395.1.2 LEC y del art. 283.3 LEC no se han contrastado contra su fuente en esta ronda.
Solo se verificó la remisión que el art. 9.2 hace al 283.3 LEC.

### 2.2 La decisión, y quién la tomó

Se le plantearon a Nikolai tres formas el 2026-09-15: (a) un envío con dos documentos separados,
(b) un documento único que fuese solo la OVC, (c) **un documento único mixto asumiendo el riesgo**.

**Eligió (c), con el riesgo asumido y escrito.** Este spec lo recoge sin suavizarlo: cabe que la
contraria pida la inadmisión del documento entero ex arts. 9.3 LO 1/2025 y 283.3 LEC, y si
prospera se pierde el requerimiento como documento aportable. El art. 9.3 contempla además
**responsabilidad** por la infracción, cuya clase no se ha verificado.

## 3. El diseño: una pieza, cuatro bloques, dos regímenes

| Bloque | Contenido | Régimen pretendido | Sección de Word |
|---|---|---|---|
| **A · Requerimiento** | Hechos, devengo, cuantía, plazo de pago, cuenta | se pretende aportable | 1 |
| **B · Deslinde** | Declara qué es cada parte y a cuál alcanza la confidencialidad | se pretende aportable | 1 |
| **C · Oferta vinculante confidencial** | Motor MASC: arts. 6.2, 6.3, 14.1, 7.4, 17.4 | confidencial | 2 |
| **D · Condiciones económicas** | Importe, calendario, cuenta, aceptación, vencimiento anticipado | confidencial | 2 |

**El bloque B es un argumento, no una garantía**, y la rev. 1 lo presentaba como resultado (H-01).
Se apoya en el art. 9.1, cuya excepción cubre «la información relativa … al objeto de la
controversia»; de ahí **no se sigue** que toda la exposición de hechos, el devengo, el
requerimiento, su plazo y la cuenta queden fuera de la confidencialidad. Y **una declaración
unilateral no fija el régimen frente al tribunal**: la dispensa del art. 9.2.a exige que *todas*
las partes se dispensen recíprocamente, expresa y por escrito. Por eso la columna dice «se
pretende aportable» y no «aportable».

Lo que B sí hace, y por eso se mantiene: deja por escrito y con fecha la intención del remitente,
sitúa el requerimiento antes de la negociación y da al tribunal el material para separar los dos
regímenes si decide separarlos. Es la mejor posición disponible si se impugna.

**Tres decisiones de forma**, verificadas en el prototipo:

1. **El orden importa.** El requerimiento va primero, de modo que la negociación deriva de él y
   no al revés.
2. **Dos secciones de Word, no una.** La sección 2 lleva pie propio que marca cada página como
   documento confidencial con su cita legal, y conserva el membrete. La marca viaja con la
   página, no con una declaración enterrada en el cuerpo.
3. **Las condiciones económicas, en página propia.** Facilita el corte, pero **no lo resuelve**:
   ver §3.4.

### 3.1 Los dos relojes

El bloque A fija **cinco días naturales** para el pago íntegro: eso constituye en mora (art. 1100
CC) y dispara el art. 395.1.2 LEC.

El bloque C corre **UN MES, contado de fecha a fecha**. **Esto es una corrección de la rev. 1, y
del CRM** (H-04): el art. 17.4 dice «en el plazo de **un mes** o en cualquier otro plazo mayor
establecido por la parte requirente». Las plantillas del CRM dicen «treinta días naturales», y
treinta días naturales se quedan **cortos** en los meses de 31: la oferta decaería antes del
mínimo legal y la contraria tendría un argumento contra el requisito de procedibilidad.

**Y el art. 10.4 no fija un suelo universal de treinta días**, como decía la rev. 1. Sus cuatro
apartados regulan cosas distintas: a) y b) treinta días naturales para supuestos de falta de
contacto o de respuesta; c) tres meses desde la primera reunión, prorrogables de mutuo acuerdo;
d) terminación escrita en cualquier momento. El art. 17.4 añade el **rechazo** como alternativa.
No todas las terminaciones esperan treinta días.

No se contradicen porque hacen cosas distintas, pero un lector de buena fe puede leerlos como
contradictorios. **El bloque B lo cierra por escrito**: el transcurso de los cinco días no
consume, interrumpe ni altera el mes.

### 3.2 Qué ocurre si aceptan tarde

Escenario que la rev. 1 dejaba abierto (H-08): no pagan al quinto día y aceptan el fraccionamiento
después, dentro del plazo de la oferta. El art. 17.1 obliga al oferente a cumplir lo que ofreció,
así que no basta con decir que la oferta sigue viva.

**El documento lo resuelve en dos sitios.** El bloque B declara que la aceptación dentro de plazo
—aunque sea posterior al quinto día— hace que la obligación asumida sea la del calendario y
sustituya a la exigencia de pago íntegro, sin intereses ni costas mientras el calendario se
cumpla; y que si la oferta decae, revive la exigencia íntegra. La condición 5 del bloque D lo
repite con el detalle del calendario: si la aceptación llega pasada la fecha del primer plazo,
ambos pagos se desplazan al mes natural siguiente al de la aceptación, conservando los mismos
días.

### 3.3 Lo que hay que acreditar, y no basta llamar «certificado» al envío

Nuevo en la rev. 2 (H-05, H-07). La ley exige hechos probados, no un nombre comercial:

| Hecho | Precepto | Cómo se acredita |
|---|---|---|
| Identidad del oferente | art. 17.2 | El certificado nombra al remitente |
| **Recepción efectiva** por la otra parte | arts. 17.2 y 17.4 | Acuse de recepción, no solo de envío |
| Fecha de esa recepción | art. 17.2 | Sello del certificado |
| Contenido, y **acceso al contenido íntegro** | arts. 17.2 y 10.2 | `sha256` de cada adjunto en el certificado, y conservación del original |
| Identidad y recepción **de la aceptación** | art. 17.2 | La condición 4 del bloque D lo exige al destinatario |
| Idoneidad del destino o del canal | art. 7.1 | Domicilio personal o lugar de trabajo que conste, o el canal electrónico ya usado entre las partes |

**El reloj del art. 7.1 es propio y no coincide con el de la oferta.** Interrumpe la prescripción
y suspende la caducidad desde la fecha en que conste el **intento** de comunicación, no desde la
recepción; y se reinicia si en treinta días naturales no hay reunión ni respuesta escrita. Es una
vía distinta del art. 1973 CC que el requerimiento invoca, y conviene no fundirlas.

**Estado de entrega fallida:** si no se acredita recepción, la vía de la OVC **no se da por
cumplida** automáticamente. Se conserva el intento, que sirve para el art. 7.1, y se reintenta por
otro canal idóneo.

### 3.4 El paquete para el juzgado

Nuevo en la rev. 2 (H-02). La práctica de la casa —`CONVENCIONES_DESPACHO.md` §7, «D 15/D 16/D 17
CERTIFICADOS OVCs sin la página del contenido económico»— **omite solo la página económica**, y
eso no basta: el bloque C es la oferta, y el art. 17.4 dice «sin que pueda hacerse mención a su
contenido», no «sin la página económica».

El paquete se define por **información permitida**, no por páginas quitadas:

- **Sí entra:** el justificante de envío y el de recepción; la manifestación expresa en la demanda
  de que se remitió una oferta vinculante; la identificación del objeto de la controversia; la
  fecha.
- **No entra:** el texto de los bloques C y D, ni cita ni paráfrasis de su contenido.
- **Decisión separada:** aportar el bloque A es una decisión jurídica caso a caso, sujeta al
  riesgo del §3, y no un automatismo del paquete.
- **Custodia:** el documento enviado se conserva **íntegro** con su certificado. Lo que se recorta
  es lo que se aporta, nunca lo que se archiva.

### 3.5 Del envío a la demanda: los eventos que hay que registrar

Nuevo en la rev. 2 (H-06). No hay un contador, hay cinco causas de cierre y un plazo final:

| Evento | Precepto | Qué abre |
|---|---|---|
| Sin contacto ni respuesta escrita en 30 días naturales desde la recepción | art. 10.4.a | Terminación sin acuerdo |
| Propuesta concreta sin respuesta en 30 días desde su recepción | art. 10.4.b | Terminación sin acuerdo |
| Tres meses desde la primera reunión sin acuerdo | art. 10.4.c | Terminación, salvo continuación pactada |
| Escrito de cualquiera dando por terminadas las negociaciones | art. 10.4.d | Terminación inmediata |
| Rechazo, o falta de aceptación expresa en el plazo de la oferta | art. 17.4 | Decaimiento de la OVC |

**Y el plazo que la rev. 1 no tenía: un año (art. 7.3).** La demanda ha de formularse dentro del
año contado desde la **recepción de la solicitud** si quedó sin respuesta, o desde la
**terminación sin acuerdo**. Pasado ese año el requisito de procedibilidad deja de entenderse
cumplido: archivar el certificado no lo conserva indefinidamente. Si hubo medidas cautelares
durante la negociación, el plazo es de **veinte días** desde la terminación, no el año.

Una respuesta que no acepta **no es silencio** y tampoco prorroga la oferta. Hay que registrar
cuál es la causa de cierre y su fecha acreditada, porque de ella cuelga el año.

## 4. De doce formularios a uno más diez bloques

El invariante —membrete, destinatario, `REF:`, apertura, requerimiento de pago, cuenta, deslinde,
motor MASC, condiciones, pie— **se escribe una vez**. Lo variable es el **bloque de hechos**, uno
por supuesto:

| # | Supuesto | Plantilla actual | ¿Lleva el pie catalán? |
|---|---|---|---|
| 1 | Vuelta, honorarios | 188 | sí |
| 2 | Vuelta, reserva de acciones | 244 | sí |
| 3 | Negativa de compra (deudor = comprador) | 254 | sí |
| 4 | Negativa a firmar arras con oferta aceptada | 200 | sí |
| 5 | Negativa a firmar compraventa tras arras | 281 | sí |
| 6 | Negativa a aceptar oferta full price, pagar honorarios | 304 | sí |
| 7 | Negativa a aceptar oferta full price, firmar contrato | 190 | sí |
| 8 | Incumplimiento de exclusiva | 214 | sí |
| 9 | Reclamación de reserva, compraventas | 216 | sí |
| 10 | Reclamación de reserva, arrendamientos | 196 | sí |

**El pie catalán: diez dentro del alcance, cuatro fuera.** La rev. 1 prometía corregirlo «una vez,
y no catorce», y el alcance son doce formularios, no catorce (H-10). Medido: de los **14** ficheros
RTF que citan `121-11.c) CCCat`, **los 10 de la tabla** entran en la sustitución; los otros cuatro
—**195** y **243** (devolución de honorarios), **213** (LAU 20) y **286** (genérico)— pertenecen a
familias que este spec no toca y **conservan el defecto**. Se declara en vez de disimularlo: son
cuatro burofaxes que seguirán invocando derecho catalán fuera de Cataluña hasta que alguien los
aborde.

**Lo que este spec NO propone:** tocar los burofaxes defensivos, los de consultores ni los
acuerdos transaccionales. Son otra familia, con otro radio, y no los pidió el encargo.

## 5. Dónde vive, y por qué en dos tiempos

**Fase 1 — en el CRM, ahora.** Diez plantillas nuevas «REQUERIMIENTO + OVC» que sustituyan a **las
diez ofensivas y a la OVC ordinaria (310)**. Reduce 11 → 10 y **sigue duplicando el invariante
diez veces**, pero el envío único funciona desde el día siguiente y Ana y Olga lo generan desde la
ficha sin pasar por el letrado. Coste: escritura en el CRM, sin código.

**La OVC 321 («secreto empresa») se queda** (H-11). Su bloque de hechos es un contrato de
representante de comercio y la vulneración del secreto empresarial: sirve a la familia de
consultores, que este spec excluye expresamente. Retirarla la dejaría sin reemplazo. La rev. 1
decía «sustituyan a las doce actuales» y contaba las dos OVC; eran once.

**Fase 2 — generación local.** Una skill que ensambla el documento desde el expediente y una
biblioteca de bloques de hechos, tomando el membrete del RTF del CRM. **Aquí, y solo aquí**, 11 →
**1 + 10** y los `[XX]` se autorrellenan, porque el expediente **sí** tiene ciudad, fechas, precio,
porcentaje e importes, cada uno con su fuente. La ruta de edición que conserva el membrete está
medida: `soffice --headless --convert-to docx` sobre el RTF y `python-docx` sobre el primer run de
cada párrafo, borrando antes los `w:hyperlink`.

La ganancia de mantenimiento —tocar el invariante una vez— **es de la fase 2**, no de la fase 1.

**La vía descartada, y por qué se documenta:** crear campos `tnm_` en el CRM para ciudad, IBAN,
fecha de encargo, precio y porcentaje. Parece posible —`tnm_posicionprocesal` y `tnm_siniestro`
existen— pero eso acredita la existencia, no el mecanismo ni los permisos. Y traslada al CRM datos
que ya están en el expediente con mejor anclaje, obligando a teclearlos dos veces. Se reconsidera
solo si la fase 2 no se construye.

## 6. Lo que el prototipo ya acredita

El documento de `W-02SRFU` (castellano e inglés, cinco páginas cada uno) se construyó y se
verificó por resultado, no por el `OK` del script:

- Membrete E&V presente en **las cinco páginas** de ambas versiones (una imagen embebida por
  página en el PDF).
- Páginas 1-3 con el pie de requerimiento fehaciente; páginas 4-5 con el pie de confidencialidad.
  Comprobado extrayendo el texto de cada página del PDF.
- Las tres líneas `REF:` comparten prefijo, que es lo que después cita el certificado de envío.
- Cero rayas (—) en cuerpo y pies tras el pase de estilo.

**Un defecto que el render destapó y la revisión de código no habría visto:** el bloque de
deslinde cayó en la sección confidencial, heredando el pie que él mismo decía no llevar. La causa
era un `append` al `<w:body>` que deja el párrafo **detrás** del `sectPr`, y con ello dentro de la
sección siguiente. Se corrigió insertando antes del `sectPr`, **y se volvió a verificar**: el
listado por página de arriba es posterior al arreglo.

## 7. Cobertura de revisión

**Se ejecutó una R1 sobre el diseño, por decisión de cobertura y no por deducción de la tabla.**
La rev. 1 presentaba esa ronda como consecuencia de la tabla de `CLAUDE.md`, y no lo es (H-12): la
fila de una ronda dice «sobre el **diff**», y la única fila que prescribe una ronda de **diseño**
es la de dos, cuya condición —decidir quién escribe sobre qué copia, o poder destruir datos de
cliente— esta pieza no cumple. Por el diff, que es documental, la tabla daría **cero**.

Se pidió igualmente, y el motivo es el que acabó justificándola: el texto que este spec fija se
reproduce en toda reclamación extrajudicial futura, y su punto contestable era jurídico. La ronda
devolvió un error de derecho que ninguna lectura del diff habría encontrado.

**Lo que esto no autoriza:** presentar la tabla como garantía del presupuesto de revisión de la
implementación futura. Cuando exista su diff, se dimensiona entonces.

## 8. Adjudicación de la revisión adversarial del diseño (Codex, 2026-09-15) — REQUIERE-REVISION, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-09-15-reclamacion-extrajudicial-envio-unico-design.md` rev. 1, commit `4520373`
- **Ronda:** R1, sobre el diseño
- **Revisor:** Codex CLI `0.153.4`, binario `7ac07f4ce733f89a`, `model_reasoning_effort=high`
- **Informe recibido:** `2026-09-15-reclamacion-extrajudicial-envio-unico-r1-adversarial-review.md`, `sha256` `3fc79e7e432a3be672d09c9e813d65ad2f243ea5ba3585174949ffb003cbe9e6`
- **Hallazgos:** 12 (7 `alto`, 4 `medio`, 1 `bajo`) — 12 confirmados, 0 refutados, 1 extremo de H-09 refutado
- **Remediado en:** esta rev. 2 del spec, y en los documentos de `W-02SRFU` para H-04, H-05 y H-08

**El hallazgo que paga la ronda entera es H-04**, y es un error de derecho mío: el art. 17.4 dice
«un mes» y yo escribí «treinta días naturales», copiando la plantilla del CRM sin abrir el
precepto. Treinta días naturales son menos que un mes en los meses de 31, así que la oferta habría
decaído antes del mínimo legal. Estaba ya en un documento del expediente listo para firmar.

| # | Hallazgo | Sev. / coste | Adjudicación | Dónde se remedia |
|---|---|---|---|---|
| H-01 | El art. 9.1 no permite identificar todo el bloque A con su excepción | alto / acotado | **Confirmado.** El art. 9.1 exceptúa «la información relativa … al objeto de la controversia», no su contenido probatorio; y el art. 9.2.a exige dispensa de **todas** las partes por escrito. Presentar «Aportable» como resultado era sobreafirmar | §3, tabla y dos párrafos nuevos |
| H-02 | Quitar solo D deja dentro C, expresamente confidencial | alto / estructural | **Confirmado.** El art. 17.4 dice «sin que pueda hacerse mención a su contenido», no «sin la página económica» | §3.4, nuevo |
| H-03 | El inventario omite la mora y mezcla pérdida de prueba con pérdida de efecto | alto / acotado | **Confirmado**, con un matiz **adjudicado en contra**: para el art. 7.4, acreditar que la contraria no acudió sí está exceptuado por la primera rama del art. 9.1; lo vedado es el contenido. El art. 9.2.b es una vía adicional, no la única | §2.1, matriz nueva |
| H-04 | «Treinta días» no reproduce el plazo del art. 17.4 | alto / acotado | **Confirmado.** Error de derecho | §3.1, y **los documentos de W-02SRFU regenerados** |
| H-05 | Falta el contrato de evidencia de recepción, acceso íntegro y aceptación | alto / estructural | **Confirmado.** Mi §2 truncaba el art. 17.4 y se comía el requisito de recepción | §2, §3.3 nueva, y la condición 4 del bloque D |
| H-06 | No se diseña la salida de la negociación ni el vencimiento de la procedibilidad | alto / acotado | **Confirmado.** Faltaba entero el año del art. 7.3, y la rama de veinte días con cautelares | §3.5, nueva |
| H-07 | Falta el reloj propio de prescripción y caducidad del art. 7.1 | alto / acotado | **Confirmado.** El art. 7.1 corre desde el **intento** de comunicación y tiene reglas de reinicio propias | §3.3 |
| H-08 | B no define qué ocurre al aceptar después del quinto día | medio / acotado | **Confirmado** | §3.2 nueva, y **los documentos regenerados** (bloque B y condición 5) |
| H-09 | Las mediciones no tienen corpus identificable; el denominador cambia | medio / acotado | **Confirmado** en el puente 21/22 y en la falta de registro. **Refutado en un extremo**: el incidente de `BaRS10` que el revisor declaró SIN VERIFICAR **sí consta**, en `docs/bitacora/2026.md:2402-2403`; miró la entrada equivocada del mismo día. Lo que faltaba era mi ancla, y ahora está | §1 y §9, nuevo |
| H-10 | Se atribuye a doce plantillas la eliminación de catorce copias del pie | medio / acotado | **Confirmado.** Medido: **10** de los 14 entran en el alcance; **195, 243, 213 y 286** quedan fuera y conservan el defecto | §4, con las cuatro nombradas |
| H-11 | La sustitución de ambas OVC deja sin correspondencia la de secreto empresarial | medio / estructural | **Confirmado.** La 321 sirve a la familia de consultores, que el spec excluye | §5: la 321 se queda; el recuento pasa de 12 a 11 |
| H-12 | La tabla no prescribe literalmente una ronda de diseño | bajo / acotado | **Confirmado.** Vestí de deducción lo que era una decisión de cobertura. La fila de una ronda dice «sobre el diff»; por el diff, esta pieza daría cero | §7, reescrito |

**Lo que el revisor NO pudo refutar, y lo dice:** que el envío único sea posible. Buscó en los
arts. 5, 14 y 17 la exigencia de un requerimiento separado y anterior, y no aparece. La decisión
de negocio queda intacta; lo que la ronda refuta es la suficiencia de algunas justificaciones.

**Cobertura declarada:** sin segunda ronda. La remediación de esta R1 **no ha pasado revisión**, y
se dice. El techo de dos de `CLAUDE.md` no se ha tocado.

## 9. Registro de evidencia

Las mediciones del §1 se hicieron contra el CRM en vivo el 2026-09-15 y sus artefactos viven
**fuera del repo**, en el scratchpad de la sesión, porque contienen datos de un expediente real.
Esto es lo que hace falta para repetirlas (H-09):

| Medición | Cómo se obtuvo | Muestra |
|---|---|---|
| 392 plantillas | `GET /api/templates/rtf/extrajudiciales` con `properties[]` y paginación, `Accept: application/json` **exacto** | catálogo completo |
| 29 en la carpeta 375 | filtrado por `id_carpeta == "375"` sobre el catálogo | — |
| Render de 22 plantillas | `GET /api/templates/rtf/{id}/extrajudiciales/652` | **171, 179, 188, 190, 194, 195, 196, 198, 200, 210, 213, 214, 216, 230, 243, 244, 254, 281, 286, 304, 310, 321** |
| Cuadro de defectos (21) | sobre el texto de `soffice --convert-to txt` | las 22 menos **171**, que es un cuestionario y no una carta |
| Pie catalán (14 de 22) | `grep` sobre el **RTF crudo**, no sobre el texto: la conversión descarta cabecera y pie | **188, 190, 195, 196, 200, 213, 214, 216, 243, 244, 254, 281, 286, 304** |
| 48 grupos de párrafo | agrupación por `difflib.SequenceMatcher ≥ 0,92` sobre párrafos de más de 60 caracteres, en los 10 ofensivos | 188, 190, 196, 200, 214, 216, 244, 254, 281, 304 |
| Campos de `extrajudiciales` | truco del `properties[0]=__nope__`, que devuelve `500` con la lista entera | — |

**Respaldo documental de lo que sí está en el repo:** el recuento de plantillas y el esquema, en
`docs/INTEGRACION_SUDESPACHO.md` y `docs/CRM_SUDESPACHO_ATLAS.md`. Ninguno sustituye al volcado.

**El incidente que justifica la cláusula de respuesta del §3.2 del documento** —la contraria
respondió dos veces con acuses de lectura y no se le contestó, invirtiendo el argumento de costas
del art. 7.4 que nuestro propio requerimiento había puesto por escrito— está en
`docs/bitacora/2026.md:2402-2403`.

**Distinción que se mantiene en todo el spec:** *observado* (se midió y el §9 dice cómo),
*inferido* (se deduce de algo observado, como los campos `tnm_`) y *sin verificar* (no se
contrastó, y se nombra).
