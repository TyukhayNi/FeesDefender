---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-09-15-reclamacion-extrajudicial-envio-unico-design.md
objeto_rev: "1"
commit: 4520373
ronda: "1"
revisor: Codex
veredicto: REQUIERE-REVISION
marcador_nonce: k9v2
sha256_informe: 3fc79e7e432a3be672d09c9e813d65ad2f243ea5ba3585174949ffb003cbe9e6
adjudicado_en: docs/superpowers/specs/2026-09-15-reclamacion-extrajudicial-envio-unico-design.md §8
---

# Acta — R1 adversarial sobre el diseño del envío único de la reclamación extrajudicial

Objeto: el **spec** `2026-09-15-reclamacion-extrajudicial-envio-unico-design.md` en el commit
`4520373`. El objeto se archivó con `git archive` en `C:/t/rev-envio-unico-1455/objeto` (1.356
ficheros); el revisor trabajó sobre esa copia, sin `.git` y sin tocar el repositorio real.

Al objeto se le añadió un fichero que no está en el repo: `_ARTICULOS_LO_1_2025_BOE.txt`, con la
transcripción literal de los artículos 5, 6, 7, 9, 10, 14 y 17 de la Ley Orgánica 1/2025,
extraída del XML oficial del BOE (`BOE-A-2025-76`). Sin él la revisión habría sido de coherencia
interna: el revisor no tiene red, y el mandato le ordenaba declarar **SIN VERIFICAR** todo
razonamiento que dependiera de una norma ausente de ese fichero. Lo hizo en cinco sitios.

| | |
|---|---|
| Revisor | Codex CLI `0.153.4`, binario `7ac07f4ce733f89a`, `model_reasoning_effort=high` |
| Objeto | `C:/t/rev-envio-unico-1455/objeto` — 1.356 ficheros |
| `sha256` del spec, al abrir y al cerrar | idénticos, declarados por el revisor |
| `sha256` del informe | `3fc79e7e432a3be672d09c9e813d65ad2f243ea5ba3585174949ffb003cbe9e6` — **fichero crudo y bloque canonicalizado coinciden**, y coinciden con el que el propio revisor devolvió en su último mensaje |
| Veredicto | **REQUIERE-REVISION** |
| Hallazgos | 12 (7 `alto`, 4 `medio`, 1 `bajo`) — **12 confirmados, 0 refutados**, con un extremo de H-09 refutado contra la fuente |

**Lo que la ronda encontró y ninguna lectura mía habría encontrado:** que el art. 17.4 dice **«un
mes»** y no «treinta días naturales». Las plantillas del CRM llevan treinta días naturales desde
siempre y yo lo copié sin mirar el precepto. Treinta días naturales se quedan **cortos** en los
meses de 31, así que la oferta habría decaído antes del mínimo legal y la contraria tendría un
argumento contra el requisito de procedibilidad. Es un error de derecho, no de redacción, y ya
estaba en un documento del expediente `W-02SRFU` listo para firmar.

**Y una cosa que conviene decir del mandato, porque explica el rendimiento:** de los doce
hallazgos, siete nacen del fichero de artículos. El mandato anterior de la casa habría mandado a
Codex a leer un spec sin la ley delante; habría devuelto coherencia interna y habría declarado
SIN VERIFICAR todo lo jurídico, que es justo donde estaba el error.

## 1. Informe recibido de Codex, sin modificar

Bloque literal entre marcadores. El `sha256` del bloque canonicalizado —UTF-8, `LF`, un único
salto final— es el `sha256_informe` del frontmatter, y el guard **G8** lo recomputa.

<!-- informe-literal:inicio:k9v2 -->
Higiene inicial: se encontró `_stdout.log`, además de `MANDATO.md` y `objeto/`; no se leyó su contenido.

# Informe adversarial R1 — diseño de reclamación extrajudicial en un solo envío

## Objeto, fuentes y cobertura

- Objeto: `objeto/docs/superpowers/specs/2026-09-15-reclamacion-extrajudicial-envio-unico-design.md`, 222 líneas. En adelante, **S**.
- Commit declarado por el mandato: `4520373c343be0cfff00b8de9d834b188ecb2f68`. No existe `objeto/.git`: **procedencia y genealogía SIN VERIFICAR**. Se revisa el contenido suministrado.
- Fuente jurídica exclusiva: `objeto/_ARTICULOS_LO_1_2025_BOE.txt`. En adelante, **L**. Las conclusiones jurídicas se limitan a sus arts. 5, 6, 7, 9, 10, 14 y 17. No se consultó la red ni jurisprudencia.
- Contraste del proyecto: `AGENTS.md`, `CLAUDE.md`, `docs/CONVENCIONES_DESPACHO.md`; consultas dirigidas al atlas y documentación del CRM, `PLAN.md` y bitácora. Estos documentos acreditan lo que el repo declara, no hechos jurídicos externos.
- Se interpreta el mandato como auditoría de solidez del argumento propio. Se mantiene la decisión del letrado de usar **un documento mixto y un envío**; no se propone sustituirla por dos documentos.
- Método: lectura y cotejo de apartados, seguimiento de escenarios de recepción/respuesta/aceptación y recuento por PowerShell de la tabla. No se ejecutó código de producción ni tests: no hay diff de código y solo está autorizada la escritura de este informe. No se renderizó el prototipo, ausente de la copia examinada. Se aplicaron `using-superpowers` y `verification-before-completion`.

### Prueba de no-mutación del spec

Calculados con `Get-FileHash -Algorithm SHA256`, antes de leer el contenido y al cerrar la revisión de las fuentes:

| Momento | SHA-256 |
|---|---|
| Apertura | `e98c027ca334e8db9780995345c4ed6d01db67dbd4b2237a0944b138e0c93032` |
| Cierre | `e98c027ca334e8db9780995345c4ed6d01db67dbd4b2237a0944b138e0c93032` |

Los hashes coinciden. Solo se ha escrito `INFORME.md`, fuera de `objeto/`. Esta comprobación acredita la igualdad de los bytes del spec en ambos momentos; no acredita un commit ni equivale a un hash de todo el repositorio.

## P1 — El deslinde

### H-01 — El art. 9.1 no permite identificar todo el bloque A con su excepción

**severidad: alto · coste: acotado**

**Anclaje:** S §2.1, líneas 104-106; §3, líneas 112-120 y 125-129. L art. 9.1-3, líneas 43-51; art. 17.3-4, líneas 84-85.

**Dictamen:** la excepción permite identificar el objeto de la controversia y la existencia del intento; no habilita, por esa sola identificación, la aportación íntegra de su contenido probatorio. Para identificar el objeto pueden ser necesarios partes, relación, pretensión, importe y un contexto factual mínimo. De ello no se sigue que toda exposición de hechos y devengo, el requerimiento de pago, su plazo y la cuenta queden fuera de la confidencialidad. El salto está en «que es exactamente lo que el bloque A contiene» (S 118-119).

La regla literal es más amplia que el relato del spec: el art. 9.1 comprende la «documentación utilizada» en la negociación; el art. 9.2 comprende documentación derivada **o relacionada**. El art. 17.3 hace confidencial la oferta «en todo caso». Poner primero A, cambiar de sección de Word o declararlo aportable no crea una excepción legal.

**Una declaración unilateral no fija ese régimen frente a la otra parte ni al tribunal.** La dispensa prevista en el art. 9.2.a exige que **todas las partes**, expresa y por escrito, se dispensen recíprocamente. El bloque B no cumple esa condición. Tampoco la marca de confidencialidad de C puede hacer público A por exclusión.

El §2.1 sí reconoce el riesgo de inadmisión total. El defecto consiste en que el §3 vuelve a presentar «Aportable» y un deslinde «operativo» como resultados, apoyados en una equivalencia que el texto legal no sostiene. No concluyo que cualquier juez deba necesariamente excluir todo A: la extensión concreta de la excepción y la separabilidad del documento requieren interpretación. Con la fuente disponible no puede certificarse su supervivencia a la impugnación.

**Remedio:** describir B como manifestación de intención y apoyo argumental de eficacia incierta; distinguir identificación del objeto de uso probatorio del requerimiento y condicionar las etiquetas «Aportable». Conservar la arquitectura elegida y expresar que el riesgo subsiste incluso con orden y pies correctos. Es una corrección de la justificación y del riesgo, no un cambio de formato.

### H-02 — Quitar solo D deja dentro de la aportación el bloque C, expresamente confidencial

**severidad: alto · coste: estructural**

**Anclaje:** S §3, líneas 114-115 y 130-132; §6, líneas 204-205. `docs/CONVENCIONES_DESPACHO.md` §7, líneas 187-202. L art. 17.4, línea 85; art. 9.3, línea 51.

El corte que el diseño llama «limpio» solo omite la página de condiciones económicas. Queda C, que la propia tabla llama «Oferta vinculante confidencial» y clasifica como confidencial. En el prototipo descrito, las páginas 4 y 5 llevan ese pie: retirar la página económica no elimina por sí solo la otra página confidencial.

La convención citada existe, pero el art. 17.4 no dice «sin contenido económico»: dice **«sin que pueda hacerse mención a su contenido»**. Invocar una práctica interna no acredita su adecuación al precepto. Si la operación prevista es otra, el spec no la define y deja al operador una instrucción que puede revelar C. Es un problema independiente de que se admita o no el deslinde de A.

**Remedio:** definir el paquete destinado al juzgado por información permitida, con justificantes de envío y recepción y la manifestación procesal exigida, sin reproducir C/D. Tratar la eventual aportación de A como una decisión jurídica separada y sujeta a H-01. Conservar íntegro el único documento enviado y su certificación bajo custodia. El remedio es **estructural** porque cambia el contrato de selección y preparación de la documentación judicial, no porque obligue a cambiar el envío único.

## P2 — Inventario de pérdidas

### H-03 — El inventario omite la mora y mezcla pérdida de prueba con pérdida del efecto jurídico

**severidad: alto · coste: acotado**

**Anclaje:** S §2, líneas 91-106; §3, línea 112; §3.1, líneas 136-143; §3.2, líneas 147-151. L art. 7.1 y 7.4, líneas 26-29 y 39; art. 9.2.b y 9.3, líneas 47 y 51; art. 17.4, línea 85.

**El inventario no está completo.** Además de las costas y la prescripción citadas en §2, el propio diseño depende del requerimiento para:

| Uso o efecto | Qué falta describir si A se inadmite |
|---|---|
| Constitución en mora atribuida al art. 1100 CC (S 136-137) | Se pierde este soporte para probar la interpelación y su fecha/plazo. La corrección de esa atribución y sus posibles consecuencias sobre intereses quedan **SIN VERIFICAR**, porque el art. 1100 y las normas sobre intereses no están en L. |
| Prueba de qué se reclamó y cuándo (S 112: hechos, devengo, cuantía, plazo, cuenta) | Se pierde el uso de A para acreditar la comunicación de esos extremos. No equivale a perder contratos, facturas u otras pruebas independientes del crédito; ni una narración unilateral prueba por sí sola la verdad del devengo. |
| Justificación de la conducta negociadora y eventual efecto en costas, multas o sanciones (S 147-151; art. 7.4) | No se puede dar por disponible todo el contenido del envío para defender la colaboración de la Agencia. El art. 7.4 no crea una excepción general a la confidencialidad; el art. 9.2.b abre un uso específico en la impugnación de la tasación y exoneración/moderación, a esos únicos fines. |
| Acreditación del objeto y del intento para la demanda (S 77-89 y 130-132) | Si se pretendía descansar en A y en el documento recortado, hay una dependencia probatoria que debe resolverse. La inadmisión de A **no supone automáticamente** perder la procedibilidad: subsisten las vías de los arts. 9.1, 10 y 17.4 si se conservan sus justificantes. |

Además, el art. 9.3 contempla **responsabilidad por la infracción**, no solo inadmisión. Su clase y alcance no pueden concretarse con L, pero su existencia como riesgo sí debe constar.

En sentido inverso, perder A como documento aportable no acredita por sí mismo que no hubiera interrupción: el art. 7.1 prevé un fundamento interruptivo propio para la solicitud de MASC, y también suspensión de caducidad. Debe distinguirse ese efecto de la vía del art. 1973 CC invocada por el spec.

**Remedio:** añadir una matriz efecto/prueba/fuente alternativa/riesgo residual. Marcar como **SIN VERIFICAR** el contenido y aplicación de los arts. 395.1.2 LEC, 1973 CC y 1100 CC. Del art. 283.3 LEC solo se verifica la remisión que hace el art. 9; su tenor autónomo tampoco se ha suministrado. No sustituir esas lagunas por la afirmación de que los cinco días «disparan» por sí solos efectos legales.

## P3 — Recorrido procesal

### H-04 — «Treinta días» no reproduce el plazo del art. 17.4 ni es un suelo general de terminación

**severidad: alto · coste: acotado**

**Anclaje:** S §3.1, líneas 137-143. L art. 17.4, línea 85; art. 10.4, líneas 65-69.

El art. 17.4 dice **un mes**, o un plazo mayor fijado por el requirente. No dice treinta días naturales. Un mes no es una unidad de duración fija de treinta días; el diseño no acredita que su plazo sea siempre igual o superior al legal. La regla general de cómputo por meses no está en L y queda **SIN VERIFICAR**; precisamente por ello no procede sustituir la unidad legal por otra.

Tampoco el art. 10.4 establece un suelo universal de treinta días: a) y b) regulan supuestos de falta de reunión/contacto o respuesta, c) contempla tres meses desde la primera reunión con posible continuación acordada, y d) permite terminación escrita. El propio art. 17.4 contempla **rechazo** como alternativa a la falta de aceptación en plazo. No todas las terminaciones deben esperar treinta días.

**Remedio:** conservar «un mes desde la recepción» para el plazo ordinario de aceptación, o fijar un plazo mayor inequívoco; retirar la atribución de un suelo general al art. 10.4. Distinguir plazo de la oferta y causa/fecha de terminación, y verificar el cómputo concreto antes de automatizarlo. No basta corregir un literal si se mantiene la falsa equiparación con todas las terminaciones.

### H-05 — Falta el contrato de evidencia de recepción, acceso íntegro y aceptación

**severidad: alto · coste: estructural**

**Anclaje:** S §2, líneas 88-89; §3, líneas 114-115 y 130-132; §6, línea 206. L art. 10.1-2, líneas 56-57; art. 17.1-2 y 17.4, líneas 82-85; art. 5.1, línea 3.

«Basta acreditar la remisión» es una abreviación materialmente incompleta: el art. 17.4 exige manifestación expresa y justificante de envío **y de recepción**. El art. 17.2 exige identidad del oferente, recepción efectiva, fecha y contenido, tanto para remitir la oferta como para remitir la aceptación. El art. 10.2, en defecto del documento bilateral que describe, exige probar recepción, fecha y posibilidad de acceso al **contenido íntegro**.

Un envío denominado «certificado» y un prefijo REF común no especifican que se prueben todos esos hechos ni qué versión íntegra recibió el destinatario. Tampoco hay procedimiento para acreditar la aceptación expresa y su recepción por el oferente. No se demuestra que el prototipo incumpla estos requisitos: **el diseño no los convierte en condiciones comprobables**.

Escenario de fallo: existe justificante de emisión o de un intento de entrega, pero no recepción efectiva acreditada. El operador aplica la frase abreviada del §2 y da por satisfecho el art. 17.4. Otro escenario: se acredita la entrega de una notificación, pero no el acceso al adjunto íntegro. La regla del intento de comunicación del art. 7.1 no permite suplir sin más las condiciones probatorias del art. 17.

**Remedio:** definir los recibos y eventos exigidos para oferta y aceptación, identidad de las partes, fechas y vínculo inequívoco con el contenido íntegro conservado; comprobar identidad del objeto negociado y litigioso. Especificar la evidencia pública utilizable sin revelar ese contenido (H-02). Definir también el estado de entrega fallida, sin declarar cumplida automáticamente la vía OVC. Es **estructural** porque crea el contrato entre envío, custodia y preparación de demanda.

### H-06 — No se diseña la salida de la negociación ni el vencimiento de la procedibilidad

**severidad: alto · coste: acotado**

**Anclaje:** S §3.1-3.2, líneas 134-151, y §5, líneas 180-190. L art. 10.4, líneas 65-69; art. 7.3, líneas 36-38; art. 17.4, línea 85.

El spec solo contempla dos relojes del documento y el compromiso de contestar. No establece cómo registrar y distinguir:

- Falta de reunión/contacto o respuesta a la solicitud inicial: art. 10.4.a.
- Propuesta concreta durante negociación iniciada y ausencia de acuerdo/respuesta: art. 10.4.b.
- Tres meses desde la primera reunión, con posible continuación de mutuo acuerdo: art. 10.4.c.
- Terminación escrita con constancia del intento de comunicación: art. 10.4.d.
- Rechazo de la OVC o ausencia de aceptación expresa dentro de su plazo: art. 17.4.

Una respuesta que no acepta no equivale sin más a silencio; tampoco prorroga automáticamente la OVC. Debe identificarse qué vía continúa y cuál termina, sin fundir los arts. 10.4 y 17.4 en un solo contador.

Falta por completo el **año del art. 7.3**: si la solicitud inicial queda sin respuesta, se cuenta desde su **recepción**, no desde añadir un mes de espera; si finaliza un proceso negociador sin acuerdo, desde su terminación. El mero archivo del certificado no conserva indefinidamente la procedibilidad. Si hay medidas cautelares, el mismo apartado añade reglas de veinte días que no pueden sustituirse por el año ordinario.

**Remedio:** incorporar una sección operativa de eventos, causa de cierre, fecha acreditada y alertas para demanda; incluir la rama condicional de cautelares. Verificarla con escenarios de silencio, respuesta sin aceptación, rechazo, continuidad y terminación escrita. No requiere otro envío inicial ni un motor nuevo: puede ser un registro manual definido en el diseño.

### H-07 — Falta el reloj propio de prescripción y caducidad del art. 7.1

**severidad: alto · coste: acotado**

**Anclaje:** S §2, líneas 91-97; §3.1, líneas 136-143. L art. 7.1, líneas 26-29.

El art. 7.1 exige solicitud que defina adecuadamente el objeto y fija efectos desde el **intento de comunicación** en el domicilio personal o laboral conocido, o mediante el canal electrónico empleado previamente por las partes. No basta elegir cualquier dirección electrónica y denominar el envío «certificado».

El precepto distingue **interrupción de prescripción** y **suspensión de caducidad**, y después reinicio y reanudación. Si no hay recepción, el supuesto de falta de reunión/respuesta puede computarse desde el intento; para la propuesta concreta sin respuesta, el texto atiende a su recepción. La duración de esos efectos debe seguir sus reglas, no presumirse idéntica al plazo de aceptación o al año de procedibilidad.

**Remedio:** añadir a la cronología la idoneidad del destino/canal, la fecha de intento, la de recepción o su ausencia, la respuesta y el evento de reinicio/reanudación. Distinguir los arts. 7.1, 7.3 y 17.4. Mantener como **SIN VERIFICAR** la duración material de la prescripción/caducidad del crédito y la relación completa con el art. 1973 CC, no incluidos en L.

## P4 — Los dos relojes

### H-08 — B preserva la vigencia de la oferta, pero no define qué ocurre al aceptarla después del quinto día

**severidad: medio · coste: acotado**

**Anclaje:** S §3, líneas 112-115; §3.1, líneas 136-143. L art. 17.1, línea 82; art. 17.4, línea 85.

**No hay una contradicción lógica inevitable** entre exigir el total en cinco días y ofrecer, durante un plazo mayor, un fraccionamiento del mismo principal. Una exigencia de cumplimiento y una alternativa negociada pueden coexistir. B sí cierra algo concreto: el quinto día no extingue la posibilidad de aceptación.

Pero no cierra el escenario decisivo: el destinatario no paga el quinto día y acepta expresamente el fraccionamiento después, dentro del plazo de la oferta. El art. 17.1 obliga al oferente a cumplir la obligación asumida. El diseño no dice qué sucede con el requerimiento de pago íntegro, la mora que atribuye al quinto día, sus posibles accesorios, ni cómo se calculan las cuotas si la aceptación llega al final del plazo. Si se mantienen simultáneamente exigibles todo el importe y el calendario aceptado, la contraria puede señalar una incompatibilidad real.

Tampoco el quinto día habilita por sí solo a demandar por la vía de esta OVC: debe atenderse a su rechazo o falta de aceptación en el plazo del art. 17.4. La frase «no altera los treinta» resuelve la vigencia, no todos esos efectos.

**Remedio:** definir en B/D qué obligación se asume al aceptar, desde qué evento se fija el calendario y qué tratamiento tienen principal y eventuales accesorios respecto de A. Someter las afirmaciones de mora a verificación del CC. Comprobar aceptación dentro de los primeros cinco días, después de ellos y al final del plazo. No se propone cambiar la decisión económica ni imponer una quita.

## P5 — Coherencia interna y mediciones

**Recuento ejecutado:** se extrajeron los valores de la segunda columna de S 27-33 y se sumaron: **10 + 4 + 3 + 4 + 2 + 4 + 2 = 29**, en **siete familias**. El detalle ofensivo también cuadra: 2 vueltas + 5 negativas + 1 exclusiva + 2 reservas = 10. No hay hallazgo aritmético en esa tabla.

### H-09 — Las mediciones no tienen un corpus identificable y el denominador cambia sin explicación

**severidad: medio · coste: acotado**

**Anclaje:** S §1, líneas 22-70; §3, líneas 122-123; §3.2, líneas 147-151; §5, líneas 187-190; §6, líneas 199-212.

Se anuncian 21 plantillas renderizadas y la misma tabla pasa a **14 de 22 ficheros RTF**. Eso puede ser correcto si una plantilla genera dos ficheros o hay muestras diferentes, pero no se explica el puente 29 → 21 → 22. Tampoco se identifican los miembros de cada muestra ni la definición y normalización de los «48 grupos de párrafo».

La búsqueda por extensiones en `objeto/` no localizó RTF; los nombres de los PDF/DOCX presentes no corresponden al prototipo descrito. No hay resultados o artefactos enlazados que permitan repetir la medición del membrete, los REF o las rayas. El §6 **sí explica parcialmente cómo** se comprobó: imágenes del PDF y extracción de texto por página. No sería correcto afirmar que no da método alguno. Falta el producto y su identificación, y no queda explícito si el defecto de B narrado al final fue corregido y vuelto a verificar.

El dato de 392 plantillas encuentra respaldo documental en `docs/INTEGRACION_SUDESPACHO.md:1091-1099`, y el esquema citado encuentra respaldo en `docs/CRM_SUDESPACHO_ATLAS.md:2675-2712`; ninguno sustituye el volcado y la corrida concreta. `PLAN.md:51` repite las cifras. La bitácora del 2026-09-14, en su entrada BaRS10 (`docs/bitacora/2026.md:236-276`), trata de verificación de citas; no acredita allí las dos respuestas desatendidas que S 150 le atribuye. Ese incidente queda **SIN VERIFICAR**, no refutado.

Finalmente, dos campos `tnm_` existentes acreditan su existencia, no por sí solos los permisos, mecanismo ni éxito de crear otros en el CRM (S 192-194). Es una inferencia que debe rotularse como tal.

**Remedio:** añadir un registro de evidencia con IDs de muestra, criterio de conteo, explicación 21/22, localización y digest de artefactos fuera del repo cuando contengan datos reales, y método/resultado por comprobación. Corregir el enlace del incidente y distinguir «observado», «inferido» y «pendiente». No introducir expedientes reales en el repositorio para resolver la laguna.

### H-10 — Se atribuye al alcance de doce plantillas la eliminación de catorce copias del pie

**severidad: medio · coste: acotado**

**Anclaje:** S §1, líneas 43 y 69-70; §4, líneas 172-176; §5, líneas 180-187.

El §4 promete corregir el pie «una vez, y no catorce», pero su universo de sustitución es de doce formularios. No hay mapa que sitúe las catorce copias afectadas dentro o fuera de ese universo. Si los catorce ficheros corresponden a formularios distintos, al menos dos quedan fuera; si hay varias salidas por plantilla, falta decirlo. Además, la fase 1 reconoce que seguirá duplicando el invariante diez veces: la reducción del mantenimiento solo puede atribuirse a la fase 2 y a sus consumidores.

No hay contradicción aritmética entre «1 + 10» y «10 nuevas»: son fases expresamente distintas. El defecto es prometer el saneamiento de las catorce copias sin delimitar cuáles quedan cubiertas.

**Remedio:** mapear los catorce ficheros a plantilla/familia/fase, y restringir la promesa de corrección única al invariante realmente centralizado. Declarar las copias residuales sin ampliar el encargo a otras familias por iniciativa del revisor.

### H-11 — La sustitución de ambas OVC deja sin correspondencia la de secreto empresarial

**severidad: medio · coste: estructural**

**Anclaje:** S §1, líneas 29-31 y 64-65; §4, líneas 159-176; §5, líneas 180-183.

Las dos OVC son la ordinaria y «secreto empresa». El diseño propone retirar/sustituir **las dos** junto con los diez burofaxes ofensivos, pero sus diez bloques no contienen secreto empresarial y excluye expresamente los burofaxes de consultores. El hecho de que el motor difiera solo en «Honorarios»/«Indemnización» permite compartir texto; no demuestra que los usuarios de ambas ofertas queden cubiertos por los diez supuestos nuevos.

Si «sustituyan» significa retirar del catálogo, la OVC de secreto empresarial pierde su reemplazo. Si significa sustituirlas solo en este flujo, debe decirlo y corregir el significado del recuento. El uso efectivo por otras familias no se ha medido: el hallazgo es la ausencia de correspondencia en el propio inventario, no una retirada ya ejecutada.

**Remedio:** delimitar los consumidores de cada OVC y conservar disponible la de secreto empresarial para el ámbito excluido, o documentar su sustituto si ya existe. Recalcular el inventario resultante sin crear un undécimo supuesto por iniciativa propia. Es **estructural**: cambia la frontera de sustitución y compatibilidad del catálogo que otros usuarios consumen.

## P6 — Dimensionado de la revisión

### H-12 — La tabla no prescribe literalmente una ronda de diseño para esta pieza documental

**severidad: bajo · coste: acotado**

**Anclaje:** S §7, líneas 216-222. `CLAUDE.md:70-87`, especialmente filas 77-79 y regla de cierre 85-87.

La tabla dice:

- Dos rondas para decisiones sobre quién escribe en qué copia o destrucción/corrupción de datos de cliente: diseño y diff.
- Cero para un cambio que no modifica líneas que corran en producción, con las excepciones expresas de `core/`, guards y contrato de revisión.
- Una para lo demás, **sobre el diff**.

El spec es documental según el objeto del mandato; no se demuestra que entre en la primera fila. **No hay fundamento en esa tabla para exigir dos rondas por la importancia jurídica del texto.**

La regla de cierre permite cuestionar una exención que necesita defensa; invocarla como prudencia resulta defendible. Pero §7 no muestra una duda concreta sobre el diff o una excepción de la tabla: argumenta por la importancia futura del documento, justamente cuando `CLAUDE.md:81-84` manda decidir la exención por el diff. Tampoco la fila de una ronda dice «sobre el diseño». Por tanto, «una de diseño» no es una deducción literal de la tabla: es una decisión adicional de cobertura. Esta tensión no permite imputar mala fe al autor ni inventar una obligación de dos.

**Remedio:** registrar que esta R1 de diseño se ejecuta por mandato expreso, y separar esa decisión de lo que la tabla impondría al cambio documental. No presentar la tabla como garantía del presupuesto de revisión de una implementación futura cuyo diff aún no existe. No hace falta modificar el contrato ni pedir otra ronda para corregir esa atribución.

## Lo que intenté refutar y NO pude

1. **La posibilidad de un único envío.** Busqué en los arts. 5, 14 y 17 la exigencia de un requerimiento separado y anterior. No aparece en el texto suministrado. El art. 5.1 admite la OVC y el art. 17 no exige dos sobres. No se refuta la decisión de negocio; se refuta la suficiencia de algunas justificaciones.
2. **Que el riesgo estuviera oculto por completo.** Contrasté la seguridad del §3 con §2.1: las líneas 104-106 sí reconocen expresamente la posible inadmisión de todo el documento y la decisión del letrado. H-01 no sostiene lo contrario.
3. **La suma de familias y la cardinalidad de los diez supuestos.** Extraje y sumé los valores: siete familias, 29; el detalle ofensivo y la lista del §4 dan diez. Sin discrepancia.
4. **Una incompatibilidad inevitable de los dos plazos.** Seguí el escenario en que, tras el día cinco, se acepta el fraccionamiento aún vigente. El art. 17.1 permite identificar una obligación asumida al aceptar; no impone que antes desaparezca toda reclamación de pago. La coexistencia es defendible. H-08 afecta a sus consecuencias no definidas, no a la mera coexistencia.
5. **La falsedad de la cita a las convenciones.** Leí `CONVENCIONES_DESPACHO.md:187-202`: sí contiene el checklist con exclusión de la página económica. La cita es fiel. H-02 cuestiona la suficiencia de esa práctica frente a la ley y al nuevo diseño.
6. **Una confusión numérica entre las dos fases.** §5 distingue expresamente diez plantillas con duplicación en fase 1 y biblioteca 1 + 10 en fase 2. No lo convierto en hallazgo. Subsisten los problemas de alcance de H-10/H-11.
7. **Que la generación administrativa demostrara falta de asistencia letrada.** Contrasté S 114 y 182 con el art. 6.2 (L 21). Generar desde una ficha «sin pasar por el letrado» no demuestra por sí solo ausencia de asistencia en la formulación/aceptación; el motor cita el artículo. No declaro una infracción probada. La asistencia efectiva y sus excepciones deben comprobarse en la ejecución, que esta revisión no cubre.
8. **La necesidad de dos rondas según la tabla.** Apliqué sus disparadores a este objeto documental: no se acredita ninguno de los de dos rondas. Los hallazgos jurídicos de esta R1 no modifican retroactivamente la tabla.

## Síntesis para adjudicación

El diseño conserva una decisión legítimamente asumida, pero presenta como operativa una frontera de confidencialidad que la declaración unilateral no garantiza, propone un corte judicial que puede dejar C visible y confunde un mes con treinta días. Faltan además las condiciones de acreditación y los eventos que permiten pasar del envío a la demanda sin perder el control de los plazos. Estas son razones para revisar el diseño antes de usarlo como patrón general, manteniendo el documento mixto elegido. Los doce hallazgos y sus remedios quedan sometidos a adjudicación contra la fuente; las carencias de prueba externa no se presentan como falsedades demostradas.

## Veredicto

REQUIERE-REVISION
<!-- informe-literal:fin:k9v2 -->

## 2. Evidencia verificada al adjudicar

Cada hallazgo se contrastó **contra la fuente**, no contra el informe. Lo que se abrió para
comprobarlo:

| Hallazgo | Fuente abierta | Resultado |
|---|---|---|
| H-01 | Art. 9.1 y 9.2.a del fichero del BOE | La excepción cubre «la información relativa … al objeto de la controversia», no el contenido probatorio; la dispensa del 9.2.a exige a **todas** las partes por escrito. **Confirmado** |
| H-02 | Art. 17.4 + `docs/CONVENCIONES_DESPACHO.md` §7 | El precepto dice «sin que pueda hacerse mención a su contenido»; la convención omite solo la página económica. **Confirmado** |
| H-03 | Arts. 7.1, 7.4, 9.1, 9.2.b | Inventario incompleto: faltaba la mora. **Confirmado**, con un matiz adjudicado en contra del revisor (§8) |
| H-04 | Art. 17.4 y art. 10.4 | «un mes o cualquier otro plazo mayor»; el 10.4 no fija suelo universal de treinta días. **Confirmado** |
| H-05 | Arts. 17.2, 17.4 y 10.2 | El 17.4 exige justificante de envío **y de recepción**; el 10.2, acceso al contenido íntegro. Mi §2 truncó el artículo. **Confirmado** |
| H-06 | Arts. 10.4 y 7.3 | El año del art. 7.3 no estaba en el diseño. **Confirmado** |
| H-07 | Art. 7.1 | Interrupción desde el **intento** de comunicación, con reglas de reinicio propias. **Confirmado** |
| H-08 | Arts. 17.1 y 17.4 | La aceptación tardía no estaba resuelta. **Confirmado** |
| H-09 | `docs/bitacora/2026.md`, medición propia | El puente 21/22 es real. El hecho de BaRS10 **sí consta**, en `docs/bitacora/2026.md:2402-2403`: ese extremo se **refuta** (§8) |
| H-10 | Medición de las 22 plantillas renderizadas | De los 14 ficheros con el pie catalán, **10** están en el alcance y **4** quedan fuera. **Confirmado** |
| H-11 | Catálogo de la carpeta 375, plantillas 310 y 321 | La 321 es de secreto empresarial y su familia está excluida. **Confirmado** |
| H-12 | Tabla de rondas de `CLAUDE.md` | La fila de una ronda dice «sobre el diff»; «una de diseño» es decisión adicional, no deducción. **Confirmado** |

## 3. Lo que el revisor no pudo hacer, y se declara

- **No tiene red.** Todo lo jurídico se verificó contra el fichero de artículos suministrado, no
  contra el BOE en vivo. La transcripción se hizo desde el XML oficial y su método está en el §1
  del spec; quien quiera repetirla, `https://www.boe.es/diario_boe/xml.php?id=BOE-A-2025-76`.
- **Cinco razonamientos quedaron SIN VERIFICAR** por depender de normas ausentes del fichero:
  arts. 1100, 1101, 1107 y 1973 del Código Civil, art. 395.1.2 LEC y el tenor autónomo del art.
  283.3 LEC. El revisor los marcó como tales en vez de darlos por buenos, que es lo correcto.
- **No pudo reproducir las mediciones del CRM.** El volcado del catálogo y el render de las 22
  plantillas se hicieron contra la API en vivo y sus artefactos viven fuera del repo. El §9 del
  spec deja su registro de evidencia.
- **Sin `.git`**, no puede acreditar que la copia sea el commit que se le dijo: verifica contenido
  y hash, no genealogía.
