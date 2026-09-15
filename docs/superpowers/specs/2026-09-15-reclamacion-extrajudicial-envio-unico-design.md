---
tipo: spec
estado: vigente
creado: 2026-09-15
objeto: plantillas de reclamación extrajudicial del CRM sudespacho (carpeta 375) + documento refundido requerimiento/OVC
rev: "1"
---

# La reclamación extrajudicial en un solo envío

Encargo de Nikolai del **2026-09-15**: el proceso extrajudicial de vueltas y negativas consta hoy
de **dos envíos certificados** —primero el requerimiento, quince días después la oferta vinculante
confidencial— y quiere **uno**, con **menos formularios**, que **engloben los dos pasos** y en los
que **no haya que picar tantos datos**.

Este spec fija el diseño. El prototipo ya existe y se construyó primero, a propósito: el
requerimiento refundido de `W-02SRFU`, en castellano e inglés, en su `04_Output predemanda`. Lo
que sigue generaliza ese documento, no lo anticipa.

## 1. La auditoría, medida

Volcado del catálogo `templates/rtf` del CRM el 2026-09-15: **392 plantillas**. La carpeta **375**
es la de reclamaciones E&V, con **29 formularios**:

| Familia | N | Detalle |
|---|---|---|
| Burofaxes ofensivos (E&V reclama) | **10** | vuelta ×2, negativa ×5, exclusiva, reserva ×2 |
| Burofaxes defensivos (E&V reclamado) | 4 | devolución honorarios ×2, LAU 20, responsabilidad profesional |
| Burofaxes de consultores | 3 | apropiación indebida, secreto empresarial, cese de infracción |
| Burofaxes genéricos | 4 | genérico ×2, impago rentas, hoja de reclamación |
| **Ofertas vinculantes confidenciales** | **2** | ordinaria y «secreto empresa» |
| Acuerdos transaccionales | 4 | negativa, pago cantidad, reserva, exconsultor |
| Anexos | 2 | cuestionario de viabilidad, alegaciones de consumo |

Lo que hay que rellenar a mano, contado sobre las 21 plantillas renderizadas contra un expediente
real:

| Defecto | Plantillas afectadas |
|---|---|
| Huecos `[XX]` (ciudad, fechas, precio, porcentaje, importe) | **20 de 21** |
| Doblete singular/plural (`Ud./s.`, `subscribó/ieron`, `le/s`) | **8** — hasta 31 ocurrencias en una sola |
| Tres IBAN (BCN/VAL/MAD) que hay que podar a uno | **9** |
| Pie que cita `121-11.c) CCCat`, derecho catalán, se envíe donde se envíe | **14 de 22 ficheros RTF** |

Del CRM se autorrellenan **dos** campos: `Referencia_Cliente` y `cuantia`. Los demás huecos no se
pueden autorrellenar **porque los campos no existen**. Los del elemento `extrajudiciales` son:
`costas, cuantia, Fecha_alta, fecha_alta_hist, historico, intereses, Notas, numero_anterior,
Numero_Expediente, online, Profesional, Referencia_Cliente, referencia_historico,
Referencia_Propia, saldo_*, serie_expediente, Tipo_Asunto, Tipo_Procedimiento, total,
total_pendiente, profesional_asignado, tags, tnm_posicionprocesal, tnm_siniestro,
dias_sin_actuaciones`. No hay ciudad del Market Center, ni IBAN, ni fecha de encargo, ni precio,
ni porcentaje. Sí hay dos campos con prefijo **`tnm_`**, que prueban que el CRM admite campos
propios.

### 1.1 Lo que corrige la intuición de partida

Medido sobre los diez burofaxes ofensivos: **48 grupos de párrafo distintos**, y solo **4**
compartidos por cinco o más plantillas (la línea `REF:`, la apertura, el cierre y el recitativo
del acuerdo de mediación). **No son diez copias de un formulario: son diez teorías del devengo.**
Fundirlas en un formulario único sería una pérdida.

La duplicación real está en dos sitios, y ninguno es el bloque de hechos:

1. **El motor MASC**, clonado palabra por palabra en las dos OVC salvo el singular/plural y la
   palabra del concepto reclamado («Honorarios» → «Indemnización»).
2. **El recitativo** —quién es la Agencia, qué se firmó, cuánto se debe— que la OVC repite entero
   después de que el requerimiento ya lo haya dicho, quince días antes.

Y esa duplicación tiene un coste medido: el pie con la norma catalana vive en **14 ficheros**
porque hay 14 copias del invariante que lo contiene.

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
  y dispondrá que no se incorpore al expediente».
- **Art. 9.1**, y es la puerta que queda abierta: la confidencialidad rige «salvo la información
  relativa a si las partes acudieron o no al intento de negociación previa **y al objeto de la
  controversia**».
- **Art. 17.4**: al demandar basta acreditar la remisión «sin que pueda hacerse mención a su
  contenido».

**Consecuencia.** El requerimiento lleva en su pie una declaración que dice que la comunicación
«cumple los requisitos del requerimiento previo fehaciente y justificado a los efectos de la
imposición de la condena en costas (artículo 395.1.2 LEC) y de la reclamación extrajudicial a los
efectos de la interrupción de la prescripción (artículo 1973 CC)». Si el requerimiento se funde
con la OVC en un texto indistinguible, ese texto pasa a ser documentación relacionada con la
negociación y **deja de poder aportarse**. Los dos sobres de hoy no son lastre burocrático:
existen porque uno tiene que poder aportarse y el otro no.

### 2.1 La decisión, y quién la tomó

Se le plantearon a Nikolai tres formas el 2026-09-15: (a) un envío con dos documentos separados,
(b) un documento único que fuese solo la OVC, (c) **un documento único mixto asumiendo el riesgo**.

**Eligió (c), con el riesgo asumido y escrito.** Este spec lo recoge sin suavizarlo: cabe que la
contraria pida la inadmisión del documento entero ex arts. 9.3 LO 1/2025 y 283.3 LEC, y si
prospera se pierde el requerimiento como documento aportable.

## 3. El diseño: una pieza, cuatro bloques, dos regímenes

| Bloque | Contenido | Régimen | Sección |
|---|---|---|---|
| **A · Requerimiento** | Hechos, devengo, cuantía, plazo de pago, cuenta | Aportable | 1 |
| **B · Deslinde** | Declara qué es cada parte y a cuál alcanza la confidencialidad | Aportable | 1 |
| **C · Oferta vinculante confidencial** | Motor MASC: arts. 6.2, 6.3, 14.1, 7.4, 17.4 | Confidencial | 2 |
| **D · Condiciones económicas** | Importe, calendario, cuenta, aceptación, vencimiento anticipado | Confidencial | 2 |

**El bloque B es la mitigación**, y descansa en el art. 9.1: lo que se exceptúa de la
confidencialidad es *el objeto de la controversia*, que es exactamente lo que el bloque A
contiene. El deslinde lo dice expresamente, en el propio documento, antes de que nadie tenga que
discutirlo.

**Tres decisiones de forma que hacen el deslinde operativo**, y las tres se verificaron en el
prototipo:

1. **El orden importa.** El requerimiento va primero, de modo que la negociación deriva de él y
   no al revés.
2. **Dos secciones de Word, no una.** La sección 2 lleva pie propio que marca cada página como
   documento confidencial con su cita legal, y conserva el membrete. Así la marca viaja con la
   página, no con una declaración enterrada en el cuerpo.
3. **Las condiciones económicas, en página propia.** Es la página que hoy se omite al certificar
   para el juzgado (`CONVENCIONES_DESPACHO.md` §7, «D 15/D 16/D 17 - CERTIFICADOS OVCs sin la
   página del contenido económico»); con esta estructura la omisión es un corte limpio por página.

### 3.1 Los dos relojes

El bloque A fija **cinco días naturales** para el pago íntegro: eso constituye en mora (art. 1100
CC) y dispara el art. 395.1.2 LEC. El bloque C corre **treinta días naturales**, que es suelo
legal y no se puede acortar — el art. 17.4 dice «un mes o en cualquier otro plazo mayor» y el art.
10.4 fija en treinta días la terminación sin acuerdo.

No se contradicen porque hacen cosas distintas, pero un lector de buena fe puede leerlos como
contradictorios. **El bloque B lo cierra por escrito**: el transcurso de los cinco días no
consume, interrumpe ni altera los treinta.

### 3.2 Una cláusula que inocula contra un error ya medido

El bloque C incluye el compromiso de la Agencia de **responder por escrito** a cuanta comunicación
reciba dentro del plazo. No es cortesía: en `BaRS10` el argumento de costas del art. 7.4 que
nuestro propio requerimiento había puesto por escrito **se volvió en contra** al probarse que la
contraria respondió dos veces y no se le contestó (bitácora del 2026-09-14). La cláusula convierte
esa asimetría en un compromiso verificable.

## 4. De doce formularios a uno más diez bloques

El invariante —membrete, destinatario, `REF:`, apertura, requerimiento de pago, cuenta, deslinde,
motor MASC, condiciones, pie— **se escribe una vez**. Lo variable es el **bloque de hechos**, uno
por supuesto:

| # | Supuesto | Plantilla actual |
|---|---|---|
| 1 | Vuelta, honorarios | 188 |
| 2 | Vuelta, reserva de acciones | 244 |
| 3 | Negativa de compra (deudor = comprador) | 254 |
| 4 | Negativa a firmar arras con oferta aceptada | 200 |
| 5 | Negativa a firmar compraventa tras arras | 281 |
| 6 | Negativa a aceptar oferta full price, pagar honorarios | 304 |
| 7 | Negativa a aceptar oferta full price, firmar contrato | 190 |
| 8 | Incumplimiento de exclusiva | 214 |
| 9 | Reclamación de reserva, compraventas | 216 |
| 10 | Reclamación de reserva, arrendamientos | 196 |

Doce formularios (los diez más las dos OVC) pasan a **un esqueleto y diez bloques**. El pie con la
norma catalana se corrige **una vez**, y no catorce.

**Lo que este spec NO propone:** tocar los burofaxes defensivos, los de consultores ni los
acuerdos transaccionales. Son otra familia, con otro radio, y no los pidió el encargo.

## 5. Dónde vive, y por qué en dos tiempos

**Fase 1 — en el CRM, ahora.** Diez plantillas nuevas «REQUERIMIENTO + OVC» que sustituyan a las
doce actuales. Reduce 12 → 10 y **sigue duplicando el invariante diez veces**, pero el envío único
funciona desde el día siguiente y Ana y Olga lo generan desde la ficha sin pasar por el letrado.
Coste: escritura en el CRM, sin código.

**Fase 2 — generación local.** Una skill que ensambla el documento desde el expediente y una
biblioteca de bloques de hechos, tomando el membrete del RTF del CRM. Aquí es donde 12 → **1 + 10**
y donde los `[XX]` se autorrellenan, porque el expediente **sí** tiene ciudad, fechas, precio,
porcentaje e importes, cada uno con su fuente. La ruta de edición que conserva el membrete está
medida: `soffice --headless --convert-to docx` sobre el RTF y `python-docx` sobre el primer run de
cada párrafo, borrando antes los `w:hyperlink`.

**La vía descartada, y por qué se documenta:** crear campos `tnm_` en el CRM para ciudad, IBAN,
fecha de encargo, precio y porcentaje. Es posible —`tnm_posicionprocesal` y `tnm_siniestro` lo
prueban— pero traslada al CRM datos que ya están en el expediente con mejor anclaje, y obliga a
teclearlos dos veces. Se reconsidera solo si la fase 2 no se construye.

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
sección siguiente. Solo se ve mirando la página.

## 7. Cobertura de revisión

**Una ronda sobre el diseño.** El diff es de documentación y no cambia una línea de producción,
pero la regla de cierre de `CLAUDE.md` dice que si hay que argumentar por qué algo es trivial no
lo es, y aquí hubo que argumentarlo: el texto que este spec fija se reproducirá en toda
reclamación extrajudicial futura, y su punto contestable —si el documento mixto sobrevive a una
impugnación ex art. 9.3— es exactamente lo que un revisor adversarial debe atacar.

No son dos: la pieza no decide quién escribe sobre qué copia ni puede destruir datos de cliente.
