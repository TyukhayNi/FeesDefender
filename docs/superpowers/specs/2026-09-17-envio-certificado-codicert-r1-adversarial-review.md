---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md
objeto_rev: "1"
commit: d895d1d
ronda: "1"
revisor: Claude Code (sesión independiente)
veredicto: REQUIERE-REVISION
marcador_nonce: q7w3
sha256_informe: 819b5f5741201796107362ff45c29fb553b301e18f09fd562b69ad5cb80385f6
adjudicado_en: docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md §11
---

# Acta — R1 adversarial sobre el diseño del envío certificado por Codicert

Objeto: el **spec** `2026-09-17-envio-certificado-codicert-design.md` en el commit `d895d1d`,
rama `claude/codicert-burofax-ovcs-89e7aa`.

## La independencia de esta ronda es MÁS DÉBIL, y hay que decirlo

La ejecuta **Claude Code en sesión independiente**, no Codex. Codex estaba sin cupo hasta el
2026-09-19 — indisponibilidad real comunicada por Nikolai el 2026-09-17, que es la única causa
que `AGENTS.md` §«Revisor sustituto» admite.

Autor y revisor son **el mismo modelo**, así que comparten puntos ciegos y no hay la tensión de
interés que hace valiosa una revisión ajena. Lo que se dice aquí de los hallazgos no vale lo que
valdría viniendo de Codex, y el registro mentiría si no lo consignara. La compensación que manda
el contrato —**tres lentes en paralelo**, cada una con su mandato, sin contexto de autoría y con
la orden expresa de reproducir toda medición en vez de creerla— se aplicó, y las tres sesiones
arrancaron limpias, con el objeto anclado al commit y nada más.

El mandato prohibía además cualquier escritura en el repositorio y declaraba por escrito que
**volver sin hallazgos es un resultado legítimo**, para no convertir el veredicto en profecía.
Las tres sesiones confirmaron al terminar que el worktree quedó limpio y `HEAD` en `d895d1d`.

| Lente | Fichero original | Líneas | `sha256` del fichero |
|---|---|---|---|
| jurídica y probatoria | `C:\Users\tnm33\Dev\_revisiones\2026-09-17-codicert-r1-juridica.md` | 564 | `3529662fe57a3c04eb8d6cb881cc8bde37bcb6465139fcde8010230a15744ac9` |
| contrato de la API | `C:\Users\tnm33\Dev\_revisiones\2026-09-17-codicert-r1-api.md` | 402 | `94093e7425b5d446b47e0df239da6654da811530b028c3a9bf1c753caea11942` |
| arquitectura y modos de fallo | `C:\Users\tnm33\Dev\_revisiones\2026-09-17-codicert-r1-arquitectura.md` | 631 | `9b386b4a0af454135be4c49f8a64a53697a008dfd4dc561b31a1fd3bd8579917` |

| | |
|---|---|
| Revisor | Claude Code, tres subagentes en sesión limpia |
| Objeto | `docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md`, commit `d895d1d` |
| `sha256` del bloque literal | `819b5f5741201796107362ff45c29fb553b301e18f09fd562b69ad5cb80385f6` — el del bloque **redactado** el 2026-09-26 (nota de abajo), recomputado por el guard G8; el del original era `59d499ffd7fddb20…` |
| Veredicto agregado | **REQUIERE-REVISION** (el peor de los tres: jurídica y arquitectura lo dan; la de API da LISTA-CON-CAMBIOS) |
| Hallazgos | 34 — 12 `alta`, 14 `media`, 8 `baja` |

**Redacción del 2026-09-26, declarada.** Dentro del bloque literal se han sustituido **tres**
apariciones del número de móvil de un tercero —dos por `34XXXXXXXXX` y una por `XXXXXXXXX`—, por
la regla de higiene de datos de `CLAUDE.md` y a petición de Nikolai. Nada más cambia en la voz
del revisor, y se comprueba: `git diff 6d60187 --` sobre este fichero enseña esas tres
sustituciones, el digest nuevo y esta nota; y los tres informes originales siguen archivados
fuera del repo con los `sha256` de la tabla de arriba. El `sha256_informe` del frontmatter es el
del bloque **redactado**; el del original era `59d499ffd7fddb209d2979893c96da537aad4cef008c4820fe20a8737d31b2f5`.

**Lo que la ronda encontró y ninguna lectura mía habría encontrado**, en una frase por lente:

- **Arquitectura:** con el `id_personalizado` compuesto solo con el W-code, la OVC que se manda
  quince días después del requerimiento **encuentra los seis envíos del primero, se declara
  completa y no sale**. Fallo silencioso y positivo: el motor informa de éxito.
- **API:** el patrón `^[67]\d{8}$` que yo atribuí al canal electrónico está en el burofax y en
  el SMS certificado, y **el móvil real que yo mismo cité de producción no lo cumple**; mi regla
  habría detenido planes correctos.
- **Jurídica:** los plazos del art. 10.4.a, del 17.4 y del 7.3 corren **por requerido**, no por
  expedición, y mi §5 agregaba una sola fecha para todos.

## 1. Informe recibido de los tres revisores, sin modificar

Los tres informes van literales y concatenados, en el orden de la tabla, separados por una regla
horizontal y precedidos de un comentario HTML que nombra su lente y su fichero de origen. No se ha
tocado una palabra: el digest del frontmatter lo acredita.

<!-- informe-literal:inicio:q7w3 -->
<!-- lente: jurídica y probatoria — fichero original: 2026-09-17-codicert-r1-juridica.md -->

# R1 — lente jurídica — envío certificado Codicert
objeto: docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md
commit: d895d1d
revisor: Claude Code (sesión independiente)
fecha: 2026-09-17
veredicto: REQUIERE-REVISION

> **Nota sobre la independencia.** Soy el revisor sustituto del `AGENTS.md` §«Revisor
> sustituto»: sesión limpia, sin el contexto de autoría, pero **mismo modelo que el autor**.
> La independencia es más débil de lo que sería con Codex y comparto puntos ciegos con quien
> escribió el objeto. Esto no es una fórmula: significa que un «no encontré nada» mío vale
> menos que uno de Codex, y que los hallazgos que siguen están anclados a texto legal
> literal descargado del BOE en esta sesión precisamente para no apoyarme en mi memoria.

> **Base normativa de esta ronda, descargada y leída literal en esta sesión:**
> LO 1/2025 (texto consolidado, [BOE-A-2025-76](https://www.boe.es/buscar/act.php?id=BOE-A-2025-76)),
> arts. 5, 6, 7, 9, 10, 14, 17 y art. 22.28 (modificación del art. 395 LEC);
> LEC (texto consolidado, BOE-A-2000-323), arts. 326, 395 y 427;
> CC (texto consolidado, BOE-A-1889-4763), art. 1973.
> Donde cito entre comillas, es literal de esos textos. Donde no he abierto la fuente, lo digo.

---

## Hallazgos

### H-01 — El año del art. 7.3 tiene DOS dies a quo y el motor solo puede ver uno

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** spec §5 («Del envío a la prueba: qué se registra»); LO 1/2025
art. 7.3 y art. 10.4, literal del BOE; art. 17.4; spec hermano §3.5.

**El defecto.** El §5 dice, sin condición: «Se registra, por envío: … la fecha de la **primera**
que acredita recepción. De ella cuelgan los plazos del art. 10.4 y el año del art. 7.3».

El art. 7.3 dice literalmente: «En el caso de que la solicitud inicial de negociación **no tenga
respuesta** o bien de que el proceso negociador **finalice sin acuerdo**, las partes deberán
formular la demanda dentro del plazo de un año a contar, **respectivamente**, desde la fecha de
recepción de la solicitud de negociación por la parte a la que se haya dirigido la misma o, en su
caso, **desde la fecha de terminación del proceso de negociación sin acuerdo**».

Son dos ramas y dos fechas. La recepción solo es el dies a quo en la rama del silencio. Si la
contraria responde —y el propio spec hermano documenta un caso real en que respondió dos veces
(`docs/bitacora/2026.md:2402-2403`)—, el año cuelga de la **terminación**, que se produce por
alguno de los cuatro supuestos del art. 10.4 o por el decaimiento del art. 17.4.

El motor solo ve estados de la plataforma de envío. No ve la respuesta, ni la propuesta concreta
del art. 10.4.b, ni la primera reunión del art. 10.4.c, ni el escrito de terminación del art.
10.4.d, ni la aceptación o el rechazo de la oferta. Consecuencia doble, y las dos son caras:

1. **Enseña una regla falsa.** Un operador que lea el §5 anclará el año en la recepción también
   cuando hubo negociación, y el art. 10.1 exige que la actividad negociadora «deberá ser recogida
   documentalmente». Sin registro de la terminación no hay ni fecha ni acreditación.
2. **El art. 17.2 pide constancia de la ACEPTACIÓN, y el motor no tiene dónde ponerla.** Literal:
   «La forma de remisión **tanto de la oferta como de la aceptación** ha de permitir dejar
   constancia de la identidad del oferente, de su recepción efectiva por la otra parte y de la
   fecha en la que se produce dicha recepción, así como de su contenido». El §5 diseña el registro
   de la salida y nada de la entrada.

**Remedio.** Reescribir el §5 para que diga que la fecha de recepción ancla (a) los treinta días
del art. 10.4.a, (b) el mes del art. 17.4 y (c) el año del art. 7.3 **solo en la rama del
silencio**; y añadir al registro un bloque de **eventos de cierre** —aceptación, rechazo,
respuesta que no acepta, propuesta concreta, primera reunión, escrito de terminación— con su fecha
acreditada y su causa, alimentado a mano, que es lo que ya prescribe el §3.5 del spec hermano. No
hace falta motor: hace falta que el spec diga que ese registro existe y que el año se computa
desde él. La rama de veinte días con medidas cautelares (art. 7.3 párrafo segundo) también falta.

---

### H-02 — «El intento sirve al art. 7.1» es condicional, y el diseño no registra la condición

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** spec §5 («Entrega fallida») y §4 (fuentes de `email` y `movil`);
LO 1/2025 art. 7.1 párrafo primero, literal del BOE; spec hermano §3.3, fila «Idoneidad del
destino o del canal».

**El defecto.** El §5 afirma, sin matiz: «Conserva el intento —que sirve al art. 7.1—».

El art. 7.1 no da ese efecto a cualquier intento. Literal: «La solicitud …, **en la que se defina
adecuadamente el objeto de la negociación**, interrumpirá la prescripción o suspenderá la
caducidad de acciones desde la fecha en la que conste el intento de comunicación de dicha
solicitud a la otra parte **en el domicilio personal o lugar de trabajo que le conste a la persona
solicitante, o bien a través del medio de comunicación electrónico empleado por las partes en sus
relaciones previas**».

Dos condiciones, y el diseño no cubre ninguna:

- **Idoneidad del destino.** El §4 toma `direccion`, `email` y `movil` de `clientes_contrarios`
  del CRM. Un correo que figure en un contrato **no es** por ello «el medio de comunicación
  electrónico empleado por las partes en sus relaciones previas», y un móvil no es ni domicilio ni
  lugar de trabajo. El canal SMS, en particular, difícilmente será nunca el medio «empleado por las
  partes en sus relaciones previas» en una mediación inmobiliaria. El diseño no registra ese dato
  ni lo pide.
- **Definición del objeto.** El motor envía el PDF que le den. Nada comprueba que la comunicación
  defina el objeto de la negociación, que es requisito expreso del mismo párrafo.

El resultado es la peor clase de error que puede cometer esta pieza: **una falsa seguridad sobre
la interrupción de la prescripción**. El motor dirá «intento conservado, sirve al art. 7.1» para un
SMS a un móvil sacado del CRM, y probablemente no sirva.

Y hay una consecuencia cruzada con H-03: el **burofax al domicilio** es justamente el canal cuyo
*intento* tiene valor propio bajo el art. 7.1, y es el que el §4.3 fusiona para ahorrar 16,97 €.

**Remedio.** Que el `Plan` lleve, por destinatario y canal, un campo **idoneidad** con tres
valores —`domicilio/lugar de trabajo que consta`, `canal electrónico usado entre las partes`,
`no acreditada`— con su fuente; que se rellene en la puerta humana del §4.1 y quede en el
registro. Y que el §5 diga: el intento sirve al art. 7.1 **si el destino es idóneo**; si no
consta, se declara como no acreditado, nunca como servido.

---

### H-03 — Un burofax con dos nombres no acredita la recepción de cada requerido, y la advertencia vive donde nadie la leerá

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** spec §4.2, §4.3, §1.1 (el `destinatarios` del burofax es «un array
de exactamente 1») y §1.4 (coste); LO 1/2025 arts. 17.2 y 17.4, literal; art. 10.2, literal.

**El defecto.** La regla del §4.2 es «Burofax: uno por domicilio distinto», y el §4.3 mete ambos
nombres en el campo `nombre` separados por « Y ». El propio spec reconoce el límite: «El
certificado acredita entonces la entrega **en ese domicilio**, no la recepción personal de cada
uno». Tres problemas encadenados:

1. **Lo que la ley pide es individual.** El art. 17.2 exige constancia «de su recepción efectiva
   **por la otra parte**» y el art. 17.4 el justificante «de que la misma **ha sido recibida por la
   parte requerida**». Frente a cada requerido, «la otra parte» es él. El art. 10.2 remata: el
   documento debe probar «que **la otra parte** ha recibido la solicitud …, en qué fecha, y que
   **ha podido acceder a su contenido íntegro**». Un acuse firmado por A en el domicilio común no
   acredita nada de eso respecto de B.
2. **La asimetría de coste está invertida.** El spec justifica la fusión con el precio del burofax
   (16,9716 €). Lo que se arriesga es el requisito de procedibilidad frente a un codeudor —cuya
   falta lleva a inadmisión de la demanda ex art. 5— además de la interrupción de la prescripción
   y de las costas. Ahorrar diecisiete euros contra eso no es una decisión económica: es una
   apuesta con premio de diecisiete euros.
3. **La advertencia no viaja.** El §4.3 dice «queda dicho **aquí** para que nadie lo lea de más al
   aportarlo». «Aquí» es el spec. El letrado que prepare la demanda ocho meses después leerá el
   certificado y el manifiesto, no este fichero. Compárese con el §6.3, donde una tensión análoga
   sí recibe un aviso **del motor**. Aquí la salvaguarda es prosa en un documento de diseño.

**Remedio.** En este orden: (a) invertir el defecto — **un burofax por requerido**, y la fusión
como *opción* que alguien marca en la puerta humana del §4.1; (b) si se conserva la fusión como
regla, que el `Plan` la señale con el aviso literal y que el **manifiesto del §6.4 lo arrastre**,
de modo que el aportable nunca se lea sin él; (c) que el registro del §5 marque, por requerido
fusionado, `recepción personal: no acreditada`.

---

### H-04 — El umbral que «decide plazos» no queda fijado: hay una atribución errónea de precepto y un estado medido que la tabla no contempla

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** spec §1.3 (tabla de seis códigos) y §2 (tabla de envíos reales de
`BCN-OS-008684 - OVC`); LO 1/2025 arts. 17.2, 17.4 y 10.2, literal; memoria del despacho
`reference-certificado-envio-codicert.md`, que lista los estados que la plataforma distingue.

**El defecto, en dos pruebas.**

**(a) La atribución del código 20 al art. 17.2 es incorrecta, y contradice la fila de al lado.**
El §1.3 dice que el código 20 «Leído · Documentación accedida» es «Acceso al contenido. **Es lo que
pide el art. 17.2**». No lo es. El art. 17.2 pide constancia «de la identidad del oferente, de su
**recepción efectiva** por la otra parte y de la fecha …, así como de su contenido». El acceso al
contenido es del **art. 10.2**, y además en forma potencial: «que **ha podido acceder** a su
contenido íntegro», no que accediera. El spec hermano tenía bien la distinción (§3.3, fila
«Contenido, y acceso al contenido íntegro | arts. 17.2 y 10.2»); este spec la pierde.

No es un matiz académico. La misma tabla dice que el código 17 «Entregado» es «Entrega
acreditada». Si además el 20 fuera «lo que pide el art. 17.2», el 17 no bastaría —y entonces
**ningún burofax postal cumpliría nunca el art. 17.2**, porque el papel no tiene estado de
lectura. La tabla se contradice y deja sin fijar exactamente lo que el propio §1.3 anuncia que
fija: «la frontera … es la que decide plazos».

**(b) El único SMS medido acabó en un estado que la tabla no tiene.** El §2, que es la evidencia de
producción del propio spec, registra el envío de las 13:02:57 al `34XXXXXXXXX` en
**«Recordatorio lectura entregado»**. Ese estado no está entre los seis del §1.3 — y sí está en la
memoria del despacho, que enumera «PROCESADO · ENTREGADO · LEÍDO · **RECORDATORIO DE LECTURA
ENTREGADO** · ENTREGADO EN EL SERVIDOR · RECHAZADO». De los 43 códigos, el spec mapea seis y no
dice qué hacer con los otros 37. Para el canal SMS, el único resultado observado en producción es
hoy **inclasificable** por el propio motor.

**Remedio.** Sustituir la tabla de seis por un mapa explícito **código → hecho jurídico**, por
canal, con cuatro columnas de destino: (i) acredita recepción a efectos de arts. 17.2 y 17.4;
(ii) acredita «ha podido acceder al contenido íntegro» a efectos del art. 10.2; (iii) acredita
solo **intento** a efectos del art. 7.1; (iv) no acredita nada. Con dos reglas de cierre: el
**defecto para todo código no mapeado es «no acredita»**, y el mapa se completa con la expedición
de sandbox que el §9 ya programa, que debe salir de allí con los 43 códigos clasificados o con la
lista de los que quedan sin clasificar.

---

### H-05 — El acta del certificado no se puede recortar, y lleva el `asunto` y el `cuerpo` que compone el propio motor; el aviso del §6.3 no la mira

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** spec §6.2 (anatomía: acta vs. reproducción), §6.3 (el aviso),
§3.1 (`enviar_burofax`/`enviar_eec` reciben `asunto` y `cuerpo`), §9 hueco 1 y hueco 3;
`docs/CONVENCIONES_DESPACHO.md` §5 (literal del SMS); LO 1/2025 arts. 17.3, 17.4, 9.1, 9.2 y 9.3,
literal.

**El defecto.** El recorte del §6.3 opera sobre **la reproducción del adjunto**. El acta se queda,
porque el acta *es* el justificante. Pero el acta no es neutra: reproduce el **asunto** y el
**cuerpo** de la comunicación, que son parámetros que el motor compone (`enviar_burofax(…, asunto,
cuerpo, …)`, §3.1). El aviso que el §6.3 añade como único remedio se define «cuando, tras el
recorte, **la reproducción** conserva texto de la OVC»: es ciego justamente en la parte que no se
puede quitar.

Lo que está en juego es el art. 17.4, «sin que pueda hacerse mención a su contenido», con el art.
9.3 detrás: la autoridad judicial «**la inadmitirá y dispondrá que no se incorpore al
expediente**, sin perjuicio, además, de **la responsabilidad** que dicha infracción genere».

Dos precisiones para no exagerar en la dirección contraria:

- **Nombrar la OVC no infringe nada.** El art. 9.1 exceptúa «la información relativa a si las
  partes acudieron o no al intento de negociación previa **y al objeto de la controversia**», y el
  art. 17.4 exige precisamente «manifestación expresa» de la remisión. El literal de
  `CONVENCIONES_DESPACHO.md` §5 —«… le remite Oferta Vinculante Confidencial (OVC) y propuesta de
  negociación extrajudicial. Consulte el documento adjunto»— está, a mi juicio, del lado permitido.
- Lo que sí infringe es que el asunto o el cuerpo digan **términos**: importe ofrecido, calendario,
  quita, plazo de aceptación. Y nada en el diseño lo impide: hoy el asunto y el cuerpo son texto
  libre que llega desde arriba.

Añado un dato a favor del diseño, porque conviene que conste: la memoria del despacho acredita que
el acta lleva el **sha256 de cada adjunto**. Eso hace que el aportable recortado pueda identificar
qué se envió **sin reproducirlo**, y es el mejor cumplimiento disponible del art. 17.4 junto al
art. 10.2. El §6.4 debería apoyarse en ese hecho explícitamente, porque es el argumento que
sostiene el recorte por páginas.

**Remedio.** Tres cosas, todas en el spec: (a) fijar el `asunto` y el `cuerpo` como **literal
cerrado** que solo nombre el objeto de la controversia y la remisión de una OVC, nunca sus
términos, y decir que la puerta humana del §4.1 los enseña antes de gastar; (b) extender el aviso
del §6.3 **al acta**, no solo a la reproducción; (c) escribir en el §6.4 que el sha256 del acta es
lo que sustituye a la reproducción, y que el manifiesto lo cita.

---

### H-06 — Romper la firma cuesta la presunción del art. 326.4 LEC, y la vía de rehabilitación choca con la confidencialidad

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** spec §6.2 (segundo párrafo: «Recortar páginas rompe la firma»),
§6.3 y §6.4; LEC arts. 326.1, 326.2, 326.3 y 326.4, y art. 427.1, literal del BOE; LO 1/2025 arts.
9.2, 9.3 y 17.4, literal.

**El defecto.** El §6.2 registra el hecho técnico —«el PDF resultante no valida y el visor lo
marcará como alterado»— y de él deriva únicamente que el recorte «tenga que nacer como documento
derivado con trazabilidad». **Falta la consecuencia procesal, que es la cara.**

El art. 326.4 LEC dice: «Si se hubiera utilizado algún **servicio de confianza cualificado** de los
previstos en el Reglamento [(UE) 910/2014], se presumirá que el documento reúne la característica
cuestionada y que el servicio de confianza se ha prestado correctamente si figuraba, en el momento
relevante …, en la lista de confianza … Si aun así se impugnare el documento electrónico, **la
carga de realizar la comprobación corresponderá a quien haya presentado la impugnación**. Si
dichas comprobaciones obtienen un resultado negativo, serán las costas, gastos y derechos que
origine la comprobación exclusivamente a cargo de quien hubiese formulado la impugnación. Si, a
juicio del tribunal, la impugnación hubiese sido temeraria, podrá imponerle, además, una multa de
300 a 1200 euros».

Es decir: el certificado **íntegro** llega al pleito con presunción a su favor, con la carga de
comprobación invertida y con costas y multa para quien lo impugne en vano. El certificado
**recortado** no puede acogerse a eso: su integridad está demostrablemente rota, y se cae al
régimen del art. 326.2 —«el que lo haya presentado podrá pedir el cotejo pericial … o proponer
cualquier otro medio de prueba»; y si no se deduce su autenticidad, «el tribunal lo valorará
conforme a las reglas de la sana crítica»—, perdiendo además la prueba plena del art. 326.1.

**Y aquí está la trampa que el spec no nombra.** El momento de la impugnación es la audiencia
previa: art. 427.1, «cada parte se pronunciará sobre los documentos aportados de contrario …
manifestando si los admite o impugna». Impugnado el recortado, la vía natural de rehabilitación es
exhibir el íntegro. **Pero el íntegro es exactamente el documento que el art. 17.4 prohíbe
mencionar y que el art. 9.2 prohíbe aportar.** El remedio y la prohibición son el mismo documento.

Por la misma razón, la frase del §6.4 —«con él [el manifiesto], cualquiera puede cotejarlo contra
el original»— no es cierta en el único foro donde importa: nadie puede cotejar contra un original
que no puede entrar en autos. El sha256 del manifiesto solo lo puede verificar quien ya tiene el
íntegro, es decir, nosotros y el requerido que lo recibió.

**Remedio.** (a) Escribir en el §6.2/§6.4 qué se pierde al recortar, con el art. 326.4 delante, de
modo que la decisión del letrado del §6.3 se tome sabiendo el precio; (b) **medir en el hito de
sandbox del §9 si la plataforma emite un justificante sin reproducción del adjunto** —el §1.2 ya
lista `GET /envios/{IdEnvio}/estados`, «histórico de estados **certificados**»—: si existe un
documento firmado que acredite remisión y recepción sin reproducir el contenido, disuelve a la vez
este hallazgo y el H-05, y conserva la firma intacta; (c) si no existe, decirlo en el §9 como
hueco cerrado en negativo, que es información valiosa.

---

### H-07 — La presunción del art. 326.4 depende de que el servicio fuera CUALIFICADO, y el diseño no lo acredita ni lo registra

**Severidad:** media
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:** LEC art. 326.3 y 326.4, literal; memoria del despacho
`reference-certificado-envio-codicert.md`; spec §1 y §6.1 (nada al respecto).

**El defecto.** El art. 326 traza una frontera dura: el apartado 3 gobierna los servicios de
confianza **no cualificados** y remite al 326.2 (prueba ordinaria); el apartado 4 concede la
presunción y la inversión de la carga **solo** «si se hubiera utilizado algún servicio de confianza
**cualificado**» y «si figuraba, **en el momento relevante** a los efectos de la discrepancia, en
la lista de confianza de prestadores y servicios cualificados».

La memoria de la casa describe al prestador como «prestador de servicios de confianza del
Reglamento (UE) 910/2014 y de la Ley 6/2020» — **sin la palabra «cualificado»**, que es la que
decide. El spec no menciona la cuestión en ningún punto. Nótese además que ser prestador
cualificado no cualifica todos los servicios del catálogo: la lista de confianza se publica por
**servicio**, y aquí hay tres productos distintos (burofax postal, entrega electrónica certificada
por correo y por SMS).

**Remedio.** Dos líneas de spec y un dato: comprobar contra la lista de confianza española
(sede del Ministerio) qué servicios de Servicios de MailCertificado S.L. / Codicert figuran como
cualificados y desde cuándo, y que la cosecha del §6.1 **registre con cada certificado** el
prestador, el servicio concreto y su condición en la fecha del envío. Es el dato que al año
siguiente nadie podrá reconstruir y del que depende el art. 326.4.

---

### H-08 — La unidad jurídica es la parte requerida; el spec razona en «envío» y «expedición»

**Severidad:** media
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** spec §5 («una expedición está entregada cuando lo están todos sus
destinatarios, no cuando lo está el primero») y §4.1-§4.2; LO 1/2025 arts. 17.4, 10.4.a y 7.3,
literal.

**El defecto.** Los plazos que importan corren **por requerido**, no por expedición: el mes del
art. 17.4 frente a cada requerido, los treinta días del art. 10.4.a desde «la fecha de recepción
… **por la otra parte**», y el año del art. 7.3 desde la recepción «por la parte a la que se haya
dirigido la misma». Dos requeridos que reciben en fechas distintas tienen dos relojes.

La regla de agregación del §5 produce **una** fecha por expedición. Si esa fecha se usa para
computar, el requerido que recibió más tarde puede verse demandado con su mes del art. 17.4 aún
vivo —la oferta no ha decaído frente a él— y con su requisito de procedibilidad sin cumplir. El
spec sí distingue «el estado del envío del estado de la expedición», pero no dice cuál de los dos
es el que manda a efectos de plazos, y el que nombra en la misma frase es la expedición.

Simétricamente, la frase «Si un canal no acredita recepción … no compensa con los otros» es
correcta como regla de honestidad del informe, pero puede leerse como regla jurídica, y como regla
jurídica sería falsa: al requerido A le basta **cualquier** canal que acredite recepción; que el
burofax volviera no borra el correo entregado.

**Remedio.** Introducir en el §5 un tercer nivel, que es el que la ley usa: **por requerido**, la
fecha más temprana acreditada entre sus canales. Decir que los plazos se computan ahí, que
«expedición entregada» es una comodidad operativa sin efecto jurídico, y que un canal fallido no
resta si otro del mismo requerido acreditó recepción.

---

### H-09 — El rechazo de entrega y el silencio tienen valor AFIRMATIVO, y el §5 solo los trata como pérdida

**Severidad:** media
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:** spec §1.3 (código 28 «Rechazado | Entrega fallida por rechazo») y
§5 («Entrega fallida»); LEC art. 395.1 párrafo segundo **en su redacción vigente dada por el art.
22.28 de la LO 1/2025**, literal; LO 1/2025 art. 7.4, literal.

**El defecto.** El §5 trata toda no-entrega como pérdida: «el motor lo dice y no compensa con los
otros … Conserva el intento —que sirve al art. 7.1—». Solo nombra el art. 7.1. Pero el art. 395.1
LEC, tras la reforma de la propia LO 1/2025, dice: «Se entenderá que existe mala fe a estos efectos
cuando, antes de presentada la demanda, se hubiese requerido al demandado para el cumplimiento de
la obligación de forma fehaciente y justificada, **o cuando hubiese rechazado el acuerdo ofrecido o
la participación en un medio adecuado de solución de controversias**». Y el art. 7.4 LO 1/2025
ordena a los tribunales «tener en consideración **la colaboración de las partes** respecto a la
solución consensuada y el eventual abuso del servicio público de Justicia al pronunciarse sobre
las costas o en su tasación, y asimismo para la imposición de multas o sanciones».

Un burofax **rehusado** (código 28) es, para esos dos preceptos, un activo, no una pérdida. El
motor que lo archive como «entrega fallida» y nada más está tirando prueba de costas.

Dos cautelas que el spec debe escribir a la vez, para no pasarse al otro extremo: el «rechazado»
de la plataforma es rechazo **de la entrega**, no rechazo **del acuerdo**; son hechos distintos y
no deben fundirse en el registro. Y el rechazo de la entrega no sustituye a la recepción a efectos
de los arts. 17.2 y 17.4.

**Remedio.** Añadir al §5 una línea: los estados 28 (rechazado) y 40/42 (caducado/fallido) se
registran además como **hecho de no colaboración**, con su fecha, por su valor en el art. 395.1
párrafo segundo LEC y en el art. 7.4 LO 1/2025; y separarlos explícitamente del rechazo sustantivo
de la oferta, que es un evento de H-01.

---

### H-10 — El §5 omite el mes del art. 17.4 y la identidad del oferente, que es la primera fila de la tabla que dice satisfacer

**Severidad:** media
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:** spec §5 (lista literal de lo que se registra) contra el §3.3 del
spec hermano, que el §5 cita como su contrato; LO 1/2025 arts. 17.2 y 17.4, literal.

**El defecto.** El §5 dice que «traduce el histórico a los hechos que el §3.3 del spec del envío
único exige acreditar». Cotejadas las dos listas, faltan dos cosas:

- **El mes del art. 17.4.** El §5 nombra «los plazos del art. 10.4 y el año del art. 7.3» y no el
  plazo de la propia oferta: «en el plazo de un mes o en cualquier otro plazo mayor establecido por
  la parte requirente». Es el que decide si la OVC decayó y, por tanto, **si ya se puede demandar**.
  Es también el plazo que la R1 del spec hermano corrigió (H-04, «un mes», no «treinta días»), y
  omitirlo aquí invita a que el error vuelva por la puerta de atrás.
- **La identidad del oferente.** Es la **primera** fila de la tabla del §3.3 hermano y la primera
  exigencia del art. 17.2. El §5 registra «código de envío, canal, destinatario» y no el emisor,
  aunque el §2.1 lo resuelva en el plan. Lo que va al expediente es el registro, no el plan.

**Remedio.** Añadir ambos a la lista del §5: emisor resuelto por envío, y el mes del art. 17.4
entre los plazos que cuelgan de la fecha de recepción, con su regla de cómputo «de fecha a fecha»
tal como la fijó el §3.1 hermano.

---

### H-11 — La asistencia letrada preceptiva del art. 6.2: la R1 hermana la difirió «a la ejecución», y esta ES la ejecución

**Severidad:** media
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:** LO 1/2025 art. 6.2 y 6.3, y art. 17.2, literal; spec §2.1 (el
emisor es el usuario `.bd` del Market Center); acta
`2026-09-15-reclamacion-extrajudicial-envio-unico-r1-adversarial-review.md`, apartado de lo que el
revisor **no** pudo confirmar, punto 7.

**El defecto.** El art. 6.2 dice: «**Únicamente será preceptiva la asistencia letrada** a las
partes **cuando se utilice como medio adecuado de solución de controversias la formulación de una
oferta vinculante**, excepto cuando la cuantía del asunto controvertido no supere los dos mil euros
o bien cuando una ley sectorial no exija la intervención de letrado o letrada». Es decir: en
nuestro caso típico —OVC por honorarios muy por encima de 2.000 €— la asistencia letrada **es
preceptiva**.

La R1 del spec hermano miró esto y se abstuvo con una frase que ahora es un encargo: «La asistencia
efectiva y sus excepciones deben comprobarse **en la ejecución**, que esta revisión no cubre».
Este spec es la ejecución, y no la cubre tampoco.

El diseño fija el emisor por Market Center (`barcelona.bd`, `valencia.bd`), de modo que quien
figura remitiendo es la cuenta de *bad debt* del cliente. El art. 17.2 exige constancia de «la
identidad del oferente». Nada en el diseño comprueba que el oferente que consta en el certificado
coincida con el que formula la oferta en el documento, ni deja rastro de la intervención letrada.

No afirmo infracción: no he leído los documentos que se envían, y es perfectamente posible que la
firma del letrado conste dentro del PDF. Afirmo que **el diseño no lo comprueba ni lo registra**, y
que la ronda anterior dejó dicho que aquí debía comprobarse.

**Remedio.** Que el `Plan` imprima, junto al emisor resuelto, el **oferente que declara el
documento** y se detenga si no coinciden; y que el registro del §5 deje constancia del letrado
interviniente cuando el envío sea una OVC de cuantía superior a 2.000 €.

---

### H-12 — El mapa de páginas del refundido que usa el §6.3 no es el medido

**Severidad:** baja
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:** spec §6.3 («el documento refundido, que es requerimiento (p. 1),
OVC (p. 2) y condiciones económicas (p. 3)») contra el §6 del spec hermano, que mide el prototipo
de `W-02SRFU`: «cinco páginas cada uno … Páginas 1-3 con el pie de requerimiento fehaciente;
páginas 4-5 con el pie de confidencialidad».

**El defecto.** El §6.3 apoya su descripción de la tensión en un documento de tres páginas que no
es el que existe. En el prototipo medido, los bloques C y D ocupan **dos** páginas, de modo que
retirar «la página del contenido económico» de `CONVENCIONES_DESPACHO.md` §7 puede dejar dentro no
ya la OVC entera, sino además parte de las condiciones. El error va en la dirección que **subestima**
el problema, que es la peor para un párrafo cuyo oficio es declarar un riesgo.

Hay además un remedio que este error tapa: el spec hermano decidió (§3, «tres decisiones de forma»,
punto 2) que la sección confidencial lleva **pie propio en cada página**. Eso es un discriminante
textual por página, exactamente igual de medible que el del §6.2 para separar acta de reproducción
— y convierte el aviso del §6.3 de heurística en comprobación.

**Remedio.** Corregir el mapa de páginas citando el §6 hermano, y redefinir el aviso: **ninguna
página que lleve el pie de confidencialidad puede sobrevivir en el aportable**. El manifiesto
declara cuántas llevaban ese pie y cuántas se retiraron; si los números no cuadran, el aviso salta.

---

## Lo que he comprobado y está bien

- **«Procesado» no es «Entregado» (§1.3).** Correcto, coherente con la memoria del despacho y con
  el propio certificado medido del W-04A6LI. Es la trampa más fácil de la plataforma y está bien
  puesta en el sitio donde gobierna el motor.
- **§6.2, la firma se rompe al recortar, y el spec se niega a usarlo como argumento de parte.**
  «Esto vale para cualquier criterio de recorte, así que no es argumento a favor de ninguno».
  Es exactamente la disciplina correcta; mi H-06 no discute el hecho, añade su precio procesal.
- **§6.3 describe con fidelidad la contradicción con el spec hermano.** He abierto el §3.4 de
  `2026-09-15-reclamacion-extrajudicial-envio-unico-design.md` y el H-02 del acta de su R1. El
  criterio que se le atribuye —«información permitida» y no «páginas quitadas»—, la cita del art.
  17.4 y la etiqueta «adjudicado como confirmado» son todos exactos. Declarar la contradicción en
  lugar de sortearla es lo que permite que esta ronda la discuta.
- **§6.4, los tres artefactos.** Conservar el íntegro con su firma, producir el aportable como
  fichero distinto y acompañarlo de manifiesto es la arquitectura correcta, y coincide con la
  «Custodia» del §3.4 hermano. Mi crítica es que el manifiesto promete un cotejo que el foro no
  permite, no que sobre.
- **§4.4, «lo que falta se declara, no se inventa», y la parada ante un requerido sin ningún
  canal.** Jurídicamente es la regla correcta: sin recepción no hay art. 17.4 ni art. 10.2, y una
  expedición coja no debe salir sin que alguien lo decida.
- **§4.1, la puerta humana.** Bien fundada, y más de lo que el spec alega: además del coste y de
  la irreversibilidad, el art. 9.3 contempla **responsabilidad** por la infracción de la
  confidencialidad. Esa es la razón más fuerte para que ninguna automatización pueda disparar sola.
- **§4.1, el móvil se valida antes de gastar** y §4.2, «nunca se agrupan dos requeridos en un
  mismo envío electrónico … cada uno necesita su propio acuse». Esta última es precisamente la
  regla correcta del art. 17.2 — y es la que el §4.3 abandona para el burofax (H-03).
- **§3.5, la fuente de verdad es la plataforma.** Correcto también en clave probatoria: el hecho
  jurídico lo produce el prestador, no nuestro índice.
- **No se reintroduce el error de los «treinta días».** El spec no repite en ningún punto el plazo
  que la R1 hermana corrigió a «un mes». Lo comprobé por búsqueda; solo lo omite (H-10).
- **§10 cumple el contrato del revisor sustituto.** Declara que la ronda la ejecuta Claude Code en
  sesión independiente, que se registrará como tal y nunca como «Codex», y que la independencia es
  más débil. También es correcto que esta pieza no es el contrato de revisión, que es lo único que
  el sustituto no puede revisar.

---

## Lo que NO he podido verificar

1. **Si Servicios de MailCertificado S.L. / Codicert figura como prestador CUALIFICADO, y para qué
   servicios, en la lista de confianza española.** Es la premisa del art. 326.4 LEC (H-07). Una
   búsqueda web devolvió una afirmación en ese sentido, pero procede de un resumen de fragmentos,
   no de la lista oficial, y **no la doy por buena**. Se cierra abriendo la sede del Ministerio y
   mirando el servicio concreto y su fecha de alta.
2. **La jurisprudencia sobre el art. 1973 CC.** El precepto, que sí he leído literal, dice solo que
   la prescripción se interrumpe «por reclamación extrajudicial del acreedor» y **no resuelve** si
   basta la remisión o hace falta que llegue al deudor. La doctrina jurisprudencial sobre la
   llegada a la esfera de conocimiento del deudor, y sobre la frustración imputable a este, **no la
   he contrastado contra ninguna sentencia en esta ronda**. Mis H-02 y H-03 no se apoyan en ella:
   se apoyan en los arts. 7.1, 10.2, 17.2 y 17.4 LO 1/2025, que sí he leído literal.
3. **La práctica judicial sobre notificación conjunta a dos destinatarios en un mismo domicilio.**
   No he encontrado —ni buscado en CENDOJ— resolución aplicable a requerimientos privados. El art.
   161 LEC regula la entrega a tercero en actos de comunicación **judiciales** y no gobierna un
   burofax entre particulares; no lo invoco por eso. H-03 se sostiene solo sobre el tenor de los
   arts. 17.2, 17.4 y 10.2.
4. **El contenido real del `asunto` y del `cuerpo`** que hoy se usan por cada canal, más allá del
   literal del SMS de `CONVENCIONES_DESPACHO.md` §5. H-05 describe un riesgo estructural, no una
   fuga observada.
5. **La anatomía del certificado de un burofax postal.** Es el hueco 2 que el propio §9 declara, y
   afecta a la fiabilidad del discriminante acta/reproducción del que depende todo el §6.
6. **Que los títulos de los códigos 17 / 20 / 27 / 28 / 40 / 42 sean los que la tabla del §1.3 les
   asigna.** Solo dispongo de la evidencia de producción del §2 y de la enumeración de la memoria
   del despacho, que no lleva códigos numéricos.
7. **El Reglamento (UE) 910/2014 en su literal.** No lo he abierto. Donde hablo de servicio de
   confianza cualificado lo hago a través del art. 326.4 LEC, que sí he leído literal y que es el
   precepto que produce el efecto procesal.

---

## Síntesis

Doce hallazgos: **6 altos, 5 medios, 1 bajo**. Ninguno impugna la decisión de negocio —tres
canales, un `id_personalizado` que los cose, puerta humana antes de gastar, íntegro custodiado y
aportable derivado con manifiesto—, que me parece sólida y, en la puerta humana, mejor fundada de
lo que el propio spec alega.

Lo que sí impugnan es la **doctrina jurídica que el motor va a codificar**. El patrón que los une
es uno solo y conviene nombrarlo como frontera y no como lista: **el spec razona en las unidades de
la plataforma —envío, expedición, estado— y la ley razona en otras: la parte requerida, el hecho
acreditado, el precepto que lo consume.** Donde el spec hermano había construido esa traducción
(su §3.3 y su §3.5), este spec la cita y no la arrastra entera; y las tres piezas que se caen en el
trasvase —la idoneidad del art. 7.1, las dos ramas del art. 7.3 y la distinción arts. 17.2/10.2—
son exactamente las tres que costaron hallazgos altos en aquella R1.

El veredicto es **REQUIERE-REVISION** y no NO-SHIP porque casi todo el remedio es **escribir la
doctrina que falta**, no rehacer la arquitectura: nueve de los doce hallazgos se cierran con texto
de spec y con la expedición de sandbox que el §9 ya tiene programada como primer hito de F1. El
único que puede resultar estructural es el H-06 si la plataforma no emite un justificante sin
reproducción, y eso se sabe con una llamada.

---

<!-- lente: contrato de la API — fichero original: 2026-09-17-codicert-r1-api.md -->

# R1 — lente contrato de API — envío certificado Codicert
objeto: docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md
commit: d895d1d
revisor: Claude Code (sesión independiente)
fecha: 2026-09-17
veredicto: LISTA-CON-CAMBIOS

## Método y material

Descargué yo el contrato en vivo, sin heredar la copia del scratchpad:

- `https://ws.codicert.tk/rest.json` → 88.298 bytes, `sha256
  74eb7155176491f78949723df76338a26675a2e2eef56d95e2f8a45877fe0000`. OpenAPI `3.0.0`,
  `info.version 4.2.1`. **Resultó byte a byte idéntica a la copia previa** del scratchpad
  (mismo sha256), así que esa copia no estaba manipulada.
- `https://ws.codicert.io/rest.json` → 88.289 bytes, `sha256
  25d9c01a9949c6fd2270a18a25a4deffacef0c36f1edd0fe74bef312ea2add42`. **Misma versión 4.2.1 y,
  normalizado el JSON, solo 3 diferencias**: el `servers[0].url`, el `contact.email` y la URL
  del logo. Dato útil para el §7: **sandbox y producción exponen la misma superficie**, así que
  medir en sandbox es medir el contrato de producción.
- Documentación renderizada (`https://ws.codicert.tk/`): Redoc sobre `/rest.json`. Confirma el
  §1 del spec.
- Las cuatro páginas de ejemplos citadas en el encargo.
- Sondas de red a los dos entornos con credenciales manifiestamente falsas, **con control
  negativo**. Ningún envío, ninguna autenticación real, ninguna escritura en el repo.

## Verificación de las afirmaciones del spec

| # | Afirmación del spec | Veredicto | Evidencia |
|---|---|---|---|
| 1 | `POST /envios/burofax` admite exactamente un destinatario | **CIERTA** | `components.schemas.SolicitudBurofax.allOf[0].properties.destinatarios`: `"minItems": 1, "maxItems": 1`, `items → DestinatarioPostal`; y el `requestBody` del path añade `"required": ["destinatarios"]`. No hay otra vía: `pais` es `enum ["España"]` y la descripción dice «Sólo se hacen envío de Burofaxes en España» |
| 2 | Correo y SMS son el mismo endpoint con `tipo_entrega: "correo"\|"sms"`; `/envios/sms-certificado` es texto sin adjunto | **CIERTA** (con matiz) | `SolicitudEntregaElectronicaCertificada.tipo_entrega`: `"enum": ["correo","sms"]`, descripción «Si se escoge el tipo de entrega SMS se ha de indicar el teléfono en cada destinatario». `SolicitudSmsCertificado = SolicitudSms + IdPersonalizado + Idioma`, y `SolicitudSms` solo tiene `destinatarios` (1 móvil) y `cuerpo`: **no existe `adjuntos`**. Matiz en H-10: existe además `POST /envios/correo-electronico-certificado` (tipo `ce`), producto distinto que el spec ni menciona ni descarta |
| 3 | `id_personalizado` admite 20 caracteres y puede repetirse entre envíos | **PARCIALMENTE FALSA** | Repetible: **cierta**, literal del contrato («esté ID se puede asignar a varios envíos si así lo deseas»). Los 20 caracteres: ciertos **solo para 4 de los 5 productos**. `SolicitudDeposito` (→ EEC), `SolicitudFax`, `SolicitudSmsCertificado` y `SolicitudContratoBase` referencian el trait `IdPersonalizado` (`maxLength: 20, minLength: 1, nullable: true`). **`SolicitudBurofax` NO lo referencia: redefine `id_personalizado` inline como `{"type":"string"}` sin `maxLength`, sin `minLength` y sin `nullable`.** El esquema no es homogéneo → H-07 |
| 4 | El móvil debe casar `^[67]\d{8}$`, y aplica al canal SMS de la entrega electrónica certificada | **FALSA** | Barrido exhaustivo de todos los `pattern` del documento: el patrón `^[67]\\d{8}$` aparece en **exactamente dos sitios** — `DestinatarioPostal.telefono` (el teléfono de contacto del **burofax**) y `SolicitudSms.destinatarios.items` (el producto **SMS certificado**, el que el spec dice NO usar). **No aparece en `DestinatarioVerificable`**, que es el `items` de `destinatarios` de `/envios/entrega-electronica-certificada`: ahí `telefono` es `{"type":"string"}` sin patrón y `required: []`. (`SolicitudFax` usa otro: `^[6789]\\d{8}$`.) → H-02 |
| 5 | Los siete códigos de estado y sus títulos (5, 27, 17, 20, 28, 42, 40) | **CIERTA** (los 7); el conteo «43 códigos» es **FALSO** | Literal de `paths./envios/{IdEnvio}/estados.get.description` (y del parámetro `estado` de `GET /envios`): `5 Procesado`, `27 Entregado en el servidor`, `17 Entregado`, `20 Leído \| Documentación accedida`, `28 Rechazado`, `42 Fallido`, `40 Caducado`. Los siete existen con ese título exacto. Pero la API documenta **37 códigos**, no 43: el máximo es 42 y faltan 7, 10, 13, 16, 38 y 41 → H-04 |
| 6 | Burofax solo PDF; entrega electrónica certificada 1..10 ficheros de más tipos | **CIERTA** | Burofax: `items → FicheroPdfCodificado`, cuyo `mime` es `"enum": ["application/pdf"]`; `minItems: 0` y **sin `maxItems`**. EEC (vía `SolicitudDeposito`): `items → FicheroCodificado`, `"minItems": 1, "maxItems": 10`, y la descripción enumera 7z, doc, docx, jpg, jpeg, ico, odp, ods, odt, ppt, pptx, pdf, png, rar, tar, tar.gz, txt, xls, xlsx, zip |
| 7 | Los seis endpoints del §1.2 existen con esos verbos y esas rutas | **CIERTA** | Los seis están en `paths`, con el verbo escrito: `GET /envios`, `GET /envios/{IdEnvio}/estados`, `GET /certificados/comunicacion/{IdEnvio}` (respuesta `application/pdf`), `GET /certificados/eml/{IdEnvio}` (`text/plain`), `GET /envios/{IdEnvio}/adjuntos/{Adjunto}`, `GET /usuarios/credito`. El «100 máx. por página» es correcto (`components.parameters.longitud.schema.maximum: 100`), **pero el `default` es 10** → H-10 |
| 8 | `ws.codicert.io/v2/usuarios/acceso` y `ws.codicert.tk/v2/usuarios/acceso` existen | **CIERTA**, reproducida con control negativo | `POST` con `{"usuario":"noexiste_revision_r1","clave":"credencial-falsa-12345"}`: **ambas** devuelven `400 {"estado":"KO","mensaje":"No se pudo iniciar la sesión, compruebe su usuario y contraseña","datos":[]}`. Control negativo que al spec le faltaba: `POST /v2/usuarios/acceso-que-no-existe` devuelve en ambas `404 {"mensaje":"No se ha encontrado la ruta indicada."}`. Luego el 400 **sí** discrimina ruta existente de inexistente |
| 9 | ¿Hay algo relevante en la API que el spec ignore? | **SÍ** — no es afirmación, es la pregunta abierta | Contestada en Hallazgos: H-01 (`campos_verificacion`), H-03 (`x-json-ficheros`), H-04 (estados), H-05 (tamaño y base64), H-06 (`fecha_vencimiento`), H-08 (portada opcional), H-10 (`remitente`, producto `ce`, filtros de `GET /envios`) |

**Fuera del encargo pero verificable y verificado:** el §2.1 dice que las siete ciudades
canónicas salen de `core/ciudades.py`. Cierto: `CIUDADES` es exactamente
`("Barcelona","Bilbao","Madrid","San Sebastián","Santander","Sevilla","Valencia")` y
`ciudad_de_equipo()` existe (línea 270).

## Hallazgos

### H-01 — El «Leído» que se invoca para el art. 17.2 no identifica a nadie: `campos_verificacion` va vacío por defecto y el diseño no lo decide

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** `components.schemas.SolicitudEntregaElectronicaCertificada`:
`campos_verificacion` es un array con `"default": []`, `"minItems": 0`, **no está en
`required`**, y su `enum` admite `nombre`, `numDoc`, `telefono`, `otroDato`, `otp`, `captcha`.
Su descripción: «Estos campos serán utilizados para identificar al/los destinatario/s para
acceder a la comunicación». El ejemplo publicado del proveedor
(`/ejemplos/entrega-electronica-certificada`) manda literalmente `"campos_verificacion":[]`.
`DestinatarioVerificable` ofrece los huecos correlativos: `nombre`, `num_doc`, `telefono`,
`otro_dato`. Y el §3.1 del spec:
`enviar_eec(token, destinatarios, pdf, *, tipo_entrega, asunto, cuerpo, id_personalizado)`.

**El defecto:** la firma propuesta **no tiene parámetro para `campos_verificacion`**, luego el
motor enviará siempre con el valor por defecto: `[]`. Con `[]`, quien tenga el enlace abre la
comunicación sin acreditar quién es. El §1.3 del spec dice del código 20 «Acceso al contenido.
**Es lo que pide el art. 17.2**», y el §5 cuelga de esa fecha los plazos del art. 10.4 y el año
del art. 7.3. Es decir: la pieza entera apoya su valor probatorio en un estado que, tal como
quedará configurada, acredita que **alguien** con el enlace accedió, no que accediera el
requerido. La API ofrece el remedio y el propio §4 dice que el CRM ya trae el dato
(`clientes_contrarios` incluye `nif_cif`): `campos_verificacion: ["numDoc"]` contra el NIF
convierte el acceso en acceso identificado.

No afirmo que la elección correcta sea verificar —hay una contrapartida real de fricción, y el
`otp` además **cuesta dinero por código** según la propia descripción—. Afirmo que es una
decisión con peso jurídico que el spec no toma ni declara como hueco, y que por omisión queda
tomada en el sentido más débil.

**Remedio:** añadir `campos_verificacion` a la firma de `enviar_eec` y al `Plan`, y escribir en
el §4 la regla de la casa con su fundamento (qué campo, contra qué dato del CRM, y qué se hace
cuando el requerido no tiene ese dato). Si la decisión es no verificar, decirlo ahí y decir con
qué alcance se lee entonces el código 20, en la misma frase en que hoy se invoca el art. 17.2.

### H-02 — El patrón `^[67]\d{8}$` está atribuido al canal que no lo tiene, y ausente del producto que sí lo tiene; y la propia medición del §2 no lo cumple

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** barrido de todos los `pattern` del documento (tres en total).
`^[67]\d{8}$` está en `DestinatarioPostal.telefono` y en `SolicitudSms.destinatarios.items`.
`DestinatarioVerificable.telefono` —el destinatario de la entrega electrónica certificada— es
`{"description":"Teléfono.", "type":"string", "example":"600000000"}`, **sin `pattern`**, y
`DestinatarioVerificable.required` es `[]`. Contra eso, §1.1 del spec: «SMS certificado | el
mismo endpoint, con `tipo_entrega: "sms"` | ídem; **el móvil ha de casar `^[67]\d{8}$`**»; y §4
regla 5: «El móvil se valida contra el patrón **del contrato**… Un fijo en el campo `movil` del
CRM **se rechaza en el plan, no en el 422**».

**El defecto:** tiene dos caras y las dos cuestan.

1. **Donde el spec pone la restricción, no está.** La premisa de la regla 5 —que si no valido
   en casa la API me devolvería un 422— no está en el contrato del endpoint que se va a usar.
   Nada garantiza que un fijo en `movil` produzca un 422: puede producir un envío aceptado,
   **cobrado**, y un SMS que no llega nunca. Eso no debilita la regla 5, la refuerza; pero su
   justificación escrita («el patrón del contrato», «no en el 422») es falsa, y una regla
   sostenida sobre una premisa falsa es una regla que alguien retirará el día que compruebe la
   premisa.

2. **Donde el spec no la pone, sí está — y en el producto de 16,97 €.**
   `DestinatarioPostal.telefono` es el teléfono de contacto de la ficha postal del burofax, y
   **sí** lleva el patrón. El §2 del spec describe esa ficha («y un teléfono de contacto») sin
   la restricción, y el §4 no valida nada postal. Si el teléfono que traiga el CRM para el
   requerido es un fijo (`93…`) o lleva prefijo, el **burofax** es el que se cae en validación.
   Ironía documental que conviene conocer: **el ejemplo oficial del proveedor incumple su propio
   esquema** — `/ejemplos/burofax` manda `"telefono":"999999999"`, que no casa `^[67]\d{8}$`.
   Luego no está probado que el servidor lo aplique; lo que sí está probado es que el contrato
   lo declara ahí y no en el otro sitio.

3. **La medición del propio spec contradice la regla.** El §2 registra el destinatario del
   envío SMS de producción como **`34XXXXXXXXX`** — once dígitos con prefijo de país. Eso **no
   casa** `^[67]\d{8}$`. Puede que el portal lo pinte con prefijo y la API recibiera
   `XXXXXXXXX`; no puedo dirimirlo sin credenciales. Pero tal como está escrito, el spec manda
   validar con un patrón que su propio dato medido no pasa, y el §4 regla 4 convierte eso en
   parada dura: «Un requerido sin ningún canal **detiene el plan**». Un requerido con solo
   móvil, anotado con prefijo, detendría la expedición.

**Remedio:** (a) corregir el §1.1 — el patrón no es del canal de la entrega electrónica
certificada; (b) reescribir la regla 5 con su verdadero fundamento: se valida en casa
**porque el contrato no valida**, y el riesgo no es un 422 sino un envío cobrado que no
entrega; (c) llevar la validación del patrón **también al destinatario postal**, donde el
contrato sí lo exige y donde fallar cuesta 16,97 €; (d) normalizar el móvil antes de comparar
(quitar `+34`/`34`, espacios y guiones) en vez de rechazar en crudo, y dejar dicho que la
normalización precede al patrón.

### H-03 — La cabecera `x-json-ficheros` no aparece en el spec, y la declaran los dos endpoints que se van a usar

**Severidad:** media
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:** `components.parameters.x-json-ficheros`: `{"name":
"x-json-ficheros", "in": "header", "description": "Incluye esta cabecera cuando el contenido de
la peticion es \`application/json\` y contiene ficheros codificados en base64.", "schema":
{"type":"integer","enum":[1]}}`. La declaran **diez** operaciones POST/PUT, entre ellas
`POST /envios/burofax` y `POST /envios/entrega-electronica-certificada`. El spec no la menciona
ni en el §1, que se presenta como «El contrato de la API, medido», ni en el §3.1.

**El defecto:** todos los envíos de esta pieza son `application/json` con un PDF en base64 —
exactamente el supuesto de la cabecera. Está **descrita como obligatoria en ese supuesto**
aunque el parámetro no lleve `"required": true`, lo cual me impide afirmar que el servidor la
exija: no puedo comprobarlo sin credenciales y el encargo prohíbe autenticarse. Lo que sí puedo
afirmar es que el documento que el §1 dice haber leído la declara y el §1 no la recoge. El modo
de fallo que preocupa no es el ruidoso (un 400 en el primer intento de sandbox, que se descubre
en cinco minutos) sino el silencioso: petición aceptada y adjunto ignorado. Un burofax cobrado
que sale con la portada y sin el requerimiento es el peor resultado posible de esta pieza.

**Remedio:** añadir la cabecera al §1.2 y a `core/codicert.py` como cabecera fija de todo POST
con adjuntos, y añadir al primer hito de sandbox (§9) la comprobación **por resultado** de que
el adjunto viajó: descargarlo con `GET /envios/{IdEnvio}/adjuntos/{Adjunto}` y comparar
`sha256` contra el PDF enviado.

### H-04 — La tabla de estados del §1.3 no clasifica el estado en el que el propio §2 deja el SMS de producción

**Severidad:** media
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** el listado completo de estados de la API (37 códigos) y el §2
del spec, que registra el envío SMS de producción del 10-09-2026 en estado **«Recordatorio
lectura entregado»** — que es el **código 21**, y no está en la tabla del §1.3. Tampoco están
`14 Recordatorio lectura enviado`, `22 Recordatorio lectura fallido`, `29 SMS enviado`,
`30 SMS entregado`, `39 SMS fallido` ni `19 Entregado con albarán` (el candidato natural al
acuse del burofax postal), ni los de tránsito `11`/`12` ni `9 Reexpedido` ni `18 Ok por error`.

**El defecto:** el §5 dice que «una expedición está entregada cuando lo están **todos** sus
destinatarios» y que se registra «la fecha de la **primera** que acredita recepción». Con un
clasificador que solo conoce {5, 27, 17, 20, 28, 42, 40}, el envío SMS que el propio spec exhibe
como caso real cae en el hueco: ni entregado, ni fallido, ni caducado. La expedición no cierra
nunca, y `cosechar` —que arranca «cuando una expedición finaliza»— no arranca. Es un defecto
que la propia medición del spec ya exhibe: el dato está en el §2 y la tabla del §1.3 no lo
cubre.

Dos puntos menores del mismo sitio: **«La plataforma distingue 43 códigos» es falso** — son 37
documentados (el máximo es 42, y 7, 10, 13, 16, 38 y 41 no existen); parece `max+1` en vez de un
conteo. Y el §1.3 anuncia «solo cuentan seis» y lista siete en seis filas.

**Remedio:** que el clasificador sea **total**, no una lista blanca: tres clases explícitas
—acredita recepción / no acredita todavía / cierra sin recepción— con **todos** los 37 códigos
asignados, y una clase «desconocido» que **avisa** en vez de callar, para que un código nuevo
del prestador se note. Decidir por escrito qué acredita recepción en el canal SMS (¿30? ¿21?
¿17?) y en el postal (¿17? ¿19?). Y corregir el 43 por 37.

### H-05 — Ningún presupuesto de bytes: la API no declara límite, no acepta multipart en estos dos endpoints, y la tarifa cobra por MB

**Severidad:** media
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** barrido del documento buscando límites de tamaño: **no hay
ninguno declarado** (ni `maxLength` sobre `datos`, ni nota de MB máximos). Los `content` de
`requestBody`: `POST /envios/burofax` y `POST /envios/entrega-electronica-certificada` aceptan
**solo `application/json`** — no `multipart/form-data`, que sí aceptan
`/envios/correo-electronico-certificado`, `/envios/sepa` y `/envios/sepa-online`. El
§1.4 del spec tarifa «Megabyte adicional 0,0288 €». El §9 declara cuatro huecos y ninguno es
este.

**El defecto:** el PDF de estos requerimientos sale del CRM y puede llevar OCR y anexos. Va
forzosamente inline en base64, lo que **infla ~33%** el cuerpo. Sobre eso: el prestador cobra
por MB, así que el coste del §1.4 no es fijo y el «coste estimado desglosado» que el `Plan`
promete enseñar antes de gastar **no se puede calcular** sin conocer el tamaño; y no hay límite
declarado, así que el techo real (del servidor web, no del contrato) es desconocido y se
descubrirá con un fallo. `PeticionMultipart` existe como esquema, pero no está ofrecido en estos
dos endpoints, así que la escapatoria para ficheros grandes no está disponible donde hace falta.

**Remedio:** que el `Plan` incluya el tamaño del PDF y el coste por MB en el desglose; fijar en
el §9 como hueco declarado «tamaño máximo de adjunto, no declarado por el contrato» y medirlo en
la corrida de sandbox del primer hito; y que `enviar_burofax`/`enviar_eec` avisen por encima de
un umbral propio antes de gastar.

### H-06 — La ficha de autenticación trae `fecha_vencimiento` y la firma del §3.1 la tira

**Severidad:** baja
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:** `components.schemas.FichaAutorizada` tiene `required: ["ficha",
"fecha_vencimiento"]`, siendo `fecha_vencimiento` «Fecha de vencimiento del token». Contra eso,
§3.1: `token(usuario, clave, *, entorno) -> str  # cachea en memoria, no en disco`.

**El defecto:** el contrato entrega la caducidad y la firma devuelve solo el `str`, luego el
cliente no puede renovar proactivamente: solo puede descubrir el vencimiento con un 401 a mitad
de expedición. Justo el modo de fallo que la casa ya tiene documentado con el PHPSESSID de
sudespacho (gotcha del `CLAUDE.md`). Es barato no repetirlo.

**Remedio:** devolver la ficha con su vencimiento (una tupla o un `dataclass` pequeño) y que la
caché en memoria renueve antes de expirar. El §7 del spec, que ya decide entorno y credenciales,
es el sitio de la frase.

### H-07 — El `id_personalizado` del burofax no lleva el `maxLength: 20` que el spec atribuye a todos

**Severidad:** baja
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:** el trait `IdPersonalizado` (`maxLength: 20, minLength: 1,
nullable: true`) lo referencian `SolicitudDeposito`, `SolicitudFax`, `SolicitudSmsCertificado` y
`SolicitudContratoBase`. **`SolicitudBurofax` no lo referencia**: declara `id_personalizado`
inline como `{"description": "...", "type": "string", "example": "IdPersonalizado"}`, sin
restricción de longitud. §1.2 del spec: «`id_personalizado` admite **20 caracteres**… Un W-code
son 8: cabe de sobra».

**El defecto:** ninguno operativo —8 caracteres caben en ambos—, pero la frase del §1.2 presenta
como propiedad del contrato algo que el contrato declara de forma heterogénea, y el §1 se vende
como «el contrato de la API, medido». Si mañana alguien alarga la referencia (p. ej. `W-04A6LI
-OVC-2`, 15 caracteres, o un sufijo por canal) creerá que tiene 20 garantizados en los tres
canales y solo los tiene en dos. Y, al revés: el trait exige `minLength: 1`, que el burofax
tampoco declara — una cadena vacía sería válida para el burofax y no para los otros dos,
rompiendo en silencio el hilo que el §2 dice que cose la expedición.

**Remedio:** una frase en el §1.2 —«el límite de 20 lo declara el trait común, que el burofax no
referencia: se asume 20 para los tres por prudencia»— y una validación única en el motor, antes
de repartir por canal, que garantice `1 <= len <= 20` para todos.

### H-08 — La portada del burofax es opcional en el contrato y la firma propuesta la impone, cerrando la salida que disolvería el hueco #3 del §9

**Severidad:** baja
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:** `SolicitudBurofax.asunto`: «Ese campo será añadido junto al
cuerpo como portada de la portada del Burofax»; `cuerpo`, lo simétrico. El `requestBody` del
path solo exige `destinatarios` — ni `asunto` ni `cuerpo` son obligatorios. Y el ejemplo oficial
`/ejemplos/burofax` manda literalmente `"asunto":null,"cuerpo":null`. Contra eso, §3.1:
`enviar_burofax(token, destinatario, pdf, *, asunto, cuerpo, id_personalizado)`. El §9 declara
como hueco 3: «Si la portada del burofax (`asunto` y `cuerpo`) se imprime como página adicional
y, por tanto, altera el recuento de páginas del documento reproducido en el certificado».

**El defecto:** el contrato ya contesta media pregunta —`asunto`+`cuerpo` **son** una portada,
lo dicen las dos descripciones— y ofrece la salida entera: mandarlos `null` y no tener portada.
La firma propuesta, con `asunto` y `cuerpo` como argumentos de palabra clave sin defecto, empuja
a llenarlos siempre, que es precisamente lo que activa el hueco 3 y lo que enturbia el recuento
de páginas del que depende el recorte del §6.3. Nota de contraste: en la entrega electrónica
certificada `asunto` y `cuerpo` **sí** son obligatorios (`required: ["destinatarios","asunto",
"cuerpo"]`), así que la firma común no puede tratar los dos canales igual.

**Remedio:** que `asunto` y `cuerpo` tengan defecto `None` en `enviar_burofax`, que el §9
recoja que el contrato ya los llama «portada», y que la corrida de sandbox mida el certificado
del burofax en las dos variantes —con portada y sin ella— ya que el hueco 2 del §9 obliga a
abrir ese certificado de todos modos.

### H-09 — Los ejemplos publicados que el spec cita como fuente ignoran el parámetro `?tipo=`: el «ejemplo de correo» devuelve un payload de SMS

**Severidad:** baja
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:** el servidor de documentación **ignora `?tipo=` por completo**.
`/ejemplos/entrega-electronica-certificada` devuelve el mismo cuerpo con `?tipo=entrega-correo`,
con `?tipo=entrega-sms` y con `?tipo=basura-inexistente` (mismo md5 en los tres), y ese cuerpo
es `"tipo_entrega":"sms"` con el asunto «Asunto de la entrega electrónica certificada **por
sms**». Los dos ficheros que descargué tienen idéntico `sha256`
(`12d60f21…ca14e1`). Lo mismo con el burofax: `?tipo=con-portada`, `?tipo=a-color` y
`?tipo=remitente-personalizado` devuelven todos el mismo md5 que el simple. Y
`/ejemplos/sms-certificado?tipo=id-personalizado` devuelve un payload **sin**
`id_personalizado`. Sin embargo `components.examples` del OpenAPI declara nueve ejemplos
distinguidos por ese parámetro (`BurofaxConPortada`, `BurofaxAColor`,
`BurofaxConRemitentePersonalizado`, `EntregaElectronicaCertificadaCorreoSimple`,
`SmsCertificadoConIdPersonalizado`…) que en realidad no existen.

**El defecto:** no es defecto del spec sino del proveedor, pero le afecta: el §1 dice apoyarse
en «el contrato de la API leído», y quien vaya a implementar abrirá esas URLs creyendo leer el
ejemplo de correo, el de portada o el de `id_personalizado`, y leerá otra cosa. **No hay ningún
ejemplo publicado de un payload `tipo_entrega: "correo"`, ni de `remitente` en el burofax, ni de
`id_personalizado`.** La afirmación 2 sigue siendo cierta porque el `enum` la sostiene, pero no
hay confirmación por ejemplo de ninguna de las tres.

**Remedio:** una nota en el §1 —los ejemplos del proveedor están rotos, `?tipo=` no se honra, el
esquema manda—, y que el primer hito de sandbox (§9) deje medido el payload real de
`tipo_entrega: "correo"`, que hoy no está documentado en ningún sitio.

### H-10 — Superficie leída a medias: el producto `ce`, el `remitente` que la entrega electrónica no admite, y los filtros de `GET /envios` que el §3.5 no usa

**Severidad:** baja
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:** tres cosas del mismo documento.

1. Existe `POST /envios/correo-electronico-certificado` (`TipoEnvio: "ce"`, «Correo Electrónico
   Certificado»), producto distinto de la entrega electrónica certificada (`"c"`). Admite
   `multipart/form-data` además de JSON y tiene `remitente` propio. El §1.1 del spec presenta
   los tres canales como «DOS endpoints» sin decir que existe un tercer producto de correo
   descartado, y el §1.4 imputa el precio «entrega electrónica certificada + notificación por
   correo» sin contrastarlo con la tarifa del `ce`.
2. `SolicitudEntregaElectronicaCertificada` **no tiene `remitente`** —lo tienen
   `SolicitudBurofax` y `SolicitudCorreoElectronicoCertificado`, no ella—. Esto **respalda** la
   decisión del §2.1 (enviar desde el usuario `.bd` del Market Center) con un argumento que el
   spec no usa y que es el más fuerte: en el canal electrónico **no hay forma de sobrescribir el
   remitente**, luego elegir el usuario no es una preferencia, es el único mecanismo.
3. `GET /envios` declara `fecha_inicio`, `fecha_fin`, `estado_fecha_inicio`, `estado_fecha_fin`,
   `tipo` y `estado` como filtros, y `longitud` tiene `default: 10` (máximo 100). El §3.5 dice
   que «localizar una expedición exige traer páginas y filtrar en casa» sin mencionar que esos
   filtros acotan el barrido, y el §4.2 hace de ese barrido la base de la idempotencia. Confirmo
   que **no existe filtro por `id_personalizado`** —el spec acierta— y, dato que cierra el
   diseño del §3.5: **`EnvioSimple` sí devuelve `id_personalizado`**, junto con `estado`, `tipo`,
   `asunto`, `fecha` e `id`, así que filtrar en casa es efectivamente posible.

**El defecto:** ninguno rompe el diseño; los tres son sitios donde el §1 afirma menos o peor de
lo que el contrato permite afirmar, y uno de ellos (el 2) deja sin su mejor argumento una
decisión que el spec presenta como preferencia.

**Remedio:** tres frases —una en §1.1 diciendo que `ce` existe y por qué se descarta (la
evidencia de producción del §2 lo justifica), una en §2.1 con el argumento del `remitente`
ausente, y una en §3.5/§4.2 diciendo que el barrido se acota por `tipo` + `fecha_inicio` y que
hay que pasar `longitud=100` explícitamente porque el defecto es 10.

## Lo que NO he podido verificar

Lo digo como ausencia de verificación, no como refutación ni como respaldo.

1. **Todo el §1.4 (la tarifa «80»).** Los precios se leen del portal de producción con sesión
   iniciada. No me autentico. **No verificado.** Lo único que puedo decir es que la existencia de
   un cargo «por megabyte» es coherente con que el contrato no declare límite de tamaño (H-05).
2. **Todo el §2 (el proceso real medido en producción).** Los 25 subusuarios, los tres envíos de
   `barcelona.bd` del 10-09-2026 con la referencia `BCN-OS-008684 - OVC`, que compartieran un
   mismo `id_personalizado`, y el mapeo de la ficha postal (`nombre` = razón social,
   `a_atencion` = persona). Requiere sesión. **No verificado.** El único punto donde ese
   material entra en tensión con el contrato está recogido en H-02.3.
3. **El §2.1: que existan los siete usuarios `<ciudad>.bd` en Codicert.** Requiere sesión. **No
   verificado.** Sí verifiqué la mitad del repo: `core.ciudades.CIUDADES` son exactamente esas
   siete y `ciudad_de_equipo()` existe.
4. **La medición del §3.5: «probados cinco parámetros de búsqueda, los cinco devuelven el total
   sin filtrar».** Requiere sesión. **No verificado.** Lo que sí verifiqué, y hace innecesaria la
   medición para la conclusión, es que la lista de parámetros de `GET /envios` no contiene
   ninguno de `id_personalizado`: la conclusión del spec es correcta aunque su prueba no la haya
   podido repetir.
5. **Todo el §6.2 (la anatomía del certificado `006casm113n`): `AcroForm`, `SigFlags: 3`,
   `ByteRange`, `adbe.pkcs7`, `DocMDP`, y el discriminante textual de cabecera con el reparto 4
   de acta + 2 de reproducción.** Busqué el PDF por nombre y por `W-04A6LI` bajo el repo y el
   escritorio: no está accesible desde este worktree (`data/CASOS/` no existe aquí). **No
   verificado.** Nada de lo que he leído lo contradice.
6. **Si el servidor aplica lo que el esquema declara.** En concreto: si exige `x-json-ficheros`
   (H-03), si impone `maxLength 20` al `id_personalizado` del burofax pese a no declararlo
   (H-07), si aplica `^[67]\d{8}$` a `DestinatarioPostal.telefono` pese a que su propio ejemplo
   lo incumple (H-02.2), qué tamaño máximo de adjunto acepta (H-05) y qué devuelve `GET /envios`
   cuando seis envíos comparten `id_personalizado` (hueco 4 del §9). Todo eso exige autenticarse
   y, en algún caso, enviar. El encargo lo prohíbe y no lo he hecho. **No verificado**, y todo
   ello cae dentro del primer hito de sandbox que el propio §9 ya prevé.
7. **Los huecos 1, 2 y 3 del §9** (texto del SMS configurable, páginas de acta del certificado
   postal, portada como página adicional). Confirmo que el hueco 1 está bien planteado: **no
   existe en `SolicitudEntregaElectronicaCertificada` ningún campo para el texto del SMS de
   notificación**, ni directo ni heredado de `SolicitudDeposito`. Los huecos 2 y 3 siguen
   abiertos; el 3 está medio contestado por el contrato (H-08).

## Lo que he comprobado y NO es un hallazgo

Para que conste que se miró y se descartó, no que no se miró.

- **Las incidencias.** Sospeché que `GET /envios/{IdEnvio}/incidencias` fuera el modo de fallo
  real del burofax postal y que el spec lo ignorase. **Es falso:** la propia descripción del
  endpoint dice «Sólo se muestran las incidencias asociados a los productos de "Contrato",
  "ContratoOnline" y "Sepa"», y las acciones de `SolicitudResolucionIncidencia` (`reenviarSms`,
  `modificar` teléfono del firmante…) son todas de firma. El spec hace bien en no mencionarlas.
- **`EnvioSimple` devuelve `id_personalizado`.** Era el punto donde el §3.5 podía caerse entero
  (si el listado no devolviera el campo, «filtrar en casa» sería imposible). Lo devuelve. El
  diseño se sostiene.
- **Sandbox y producción son el mismo contrato.** Diff normalizado de los dos `rest.json`: solo
  cambian el `servers[0].url`, el email de contacto y la URL del logo. La estrategia
  sandbox-primero del §7 mide lo que luego correrá en producción.
- **`enviar_burofax` con `destinatario` en singular** es la firma correcta: `maxItems: 1` la
  impone y el spec la respeta. **`asunto` y `cuerpo` obligatorios en `enviar_eec`** también es
  correcto: la entrega electrónica certificada los exige.

---

<!-- lente: arquitectura y modos de fallo — fichero original: 2026-09-17-codicert-r1-arquitectura.md -->

# R1 — lente arquitectura — envío certificado Codicert
objeto: docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md
commit: d895d1d
revisor: Claude Code (sesión independiente)
fecha: 2026-09-17
veredicto: REQUIERE-REVISION

> **Nota de método.** He abierto todos los ficheros que el spec cita y he verificado el contrato de
> la API contra el OpenAPI vivo (`GET https://ws.codicert.tk/rest.json`, lectura pura: no he
> autenticado, no he enviado nada, no he escrito en el repo ni en el worktree). No he ejecutado
> `pytest` a propósito: habría escrito `__pycache__`/`.pytest_cache` dentro del worktree.
>
> **Por qué REQUIERE-REVISION y no NO-SHIP:** la premisa del diseño aguanta. Los tres módulos, la
> separación de capas, la puerta humana y la decisión de dónde vive la verdad son correctos, y el
> §6.3 declara en contra de sí mismo en vez de enterrarlo. **Por qué no LISTA-CON-CAMBIOS:** H-01 y
> H-03 no son retoques de redacción, son dos decisiones de diseño que el spec no toma y de las que
> depende que la pieza haga o no haga su trabajo.

## Hallazgos

### H-01 — El `id_personalizado` es la clave de todo y el spec nunca dice cómo se compone; compuesto solo con el W-code, la OVC no sale nunca

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:**
- spec §1.2 («`id_personalizado` admite 20 caracteres y se puede repetir a propósito… Un W-code son 8: cabe de sobra»), §2 («Tres envíos, tres canales, **un mismo `id_personalizado`**. Ese campo es el hilo que cose la expedición»), §3.5, §4.2, §5
- `docs/CONVENCIONES_DESPACHO.md:136-139` — «**OVC** se envía 15 días después del requerimiento si no hay respuesta. 3 canales: SMS certificado, email certificado, burofax»
- OpenAPI de Codicert, campo `id_personalizado`: *maxLength 20*, descripción «Ten en cuenta que esté ID se puede asignar a varios envíos si así lo deseas»
- `docs/superpowers/specs/2026-09-15-reclamacion-extrajudicial-envio-unico-design.md:250-269` (§3.5, los relojes cuelgan de la fecha acreditada)

**El defecto:** el `id_personalizado` soporta cuatro funciones distintas —identidad de la expedición
(§2), clave de la fuente de verdad (§3.5), clave de la idempotencia (§4.2) y unidad de agregación del
estado (§5)— y **no hay una sola línea del spec que diga cómo se construye**. Lo único que se dice de
su composición es la aritmética del §1.2, que solo tiene sentido si la respuesta es «el W-code».

Y el W-code solo no discrimina la comunicación. `CONVENCIONES §5` fija dos comunicaciones distintas
sobre el mismo expediente separadas por quince días —requerimiento y OVC— y **las dos salen por los
mismos tres canales a los mismos requeridos**. Con el W-code como id, las dos expediciones son la
misma para el motor.

Además, el §2 dice que «el motor no inventa una convención: adopta la que está en producción», y la
convención que el propio §2 mide es `BCN-OS-008684 - OVC`: una referencia de operación de E&V **más
el tipo de comunicación**. No es un W-code y no va sin discriminante. La producción ya resolvió lo
que el spec deja abierto, y el spec lee de ella la parte contraria.

**Modo de fallo concreto:** expediente `W-04A6LI`. Día 0, `enviar` expide el requerimiento: 6 envíos
con `id_personalizado = W-04A6LI` (burofax ×1 + correo ×1 + SMS ×1, por dos requeridos). Día 15, sin
respuesta, se lanza `enviar` para la OVC. El §4.2 «consulta antes de mandar»: encuentra seis envíos
con ese `id_personalizado`, y como la regla es «se reanuda completando lo que falta, nunca repitiendo
lo hecho», para cada par (canal, destinatario) hay ya un envío hecho. **La OVC se declara completa
sin haber salido ni un byte.** El fallo es silencioso y positivo: el motor informa de éxito.

El daño no termina ahí. Aunque alguien fuerce el envío, el §5 agrega por `id_personalizado` y computa
«la primera fecha que acredita recepción» **mezclando los envíos del requerimiento con los de la
OVC**. De esa fecha cuelgan, por el propio §5, los plazos del art. 10.4 y el año del art. 7.3: la
colisión no solo bloquea el envío, corrompe el dato del que dependen los relojes de procedibilidad.

**Remedio:** decidir y escribir la gramática del `id_personalizado` en una sección propia, con el tipo
de comunicación dentro (`W-04A6LI-REQ`, `W-04A6LI-OVC`, `W-04A6LI-REQ2`…). Caben: 20 − 8 = 12
caracteres libres. Y declarar que el **tipo de comunicación es un parámetro obligatorio de
`planificar`**, no un dato derivable del expediente — porque no lo es: el mismo expediente da varias.
Corolario de frontera: la pregunta no es «requerimiento vs. OVC», es *«¿qué distingue dos expediciones
del mismo expediente?»* — también un segundo requerimiento a un domicilio nuevo, o un reenvío por otro
canal tras una entrega fallida del §5.

---

### H-02 — «Consultar antes de mandar» es un censo negativo sobre un listado, y el propio repo tiene medido que eso no autoriza a escribir

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:**
- spec §4.2 y §3.5
- `docs/INTEGRACION_SUDESPACHO.md:2799-2819` (§17.4, regla en tres partes) — «⚠️ **Un censo negativo NO prueba ausencia, así que no autoriza a escribir** […] y una guarda anti-duplicado que consultaba el **listado** dio “este poder aún no tiene su certificado” sobre uno que ya lo tenía, y **lo subió dos veces**»
- OpenAPI: `POST /envios/burofax` y `POST /envios/entrega-electronica-certificada` **no declaran ninguna clave de idempotencia**; la respuesta es `{"datos": {"id": "<IdEnvio>"}}` y nada más
- OpenAPI: `GET /envios` **no filtra por `id_personalizado`** (parámetros: `pagina`, `longitud`, `orden`, `ordenar_por`, `fecha_inicio`, `fecha_fin`, `estado_fecha_inicio`, `estado_fecha_fin`, `tipo`, `estado`, `id`). El `id` es el `IdEnvio`, no el personalizado.

**El defecto:** la única garantía de no gastar dos veces diecisiete euros es una lectura previa de un
listado paginado y eventualmente consistente. Es exactamente la forma de guarda que este repositorio
ya midió rompiéndose, y el spec no cita el §17.4 ni adopta su regla. La plataforma, además, **no
ofrece ninguna ayuda**: sin clave de idempotencia, el servidor acepta encantado el duplicado (su
propia documentación dice que el mismo `id_personalizado` puede ir en varios envíos), y la respuesta
del POST se reduce a un `id` que se pierde entero si la conexión cae.

**Modo de fallo concreto (tres, el primero es el barato de disparar):**

1. **Respuesta perdida.** `POST /envios/burofax` llega al servidor, el burofax se acepta y se cobra, y
   el cliente HTTP expira antes de recibir el `{"datos":{"id":…}}`. El motor no tiene el `IdEnvio` ni
   forma de deducirlo: el listado tarda, y la única clave por la que podría reencontrarlo —el
   `id_personalizado`— no es filtrable. Un reintento manual quince minutos después consulta, no lo ve,
   y manda el segundo. 33,94 € y **dos certificados del mismo requerimiento**, que es justo lo que el
   §4.2 dice querer evitar («ensucia la prueba»).
2. **Dos ejecuciones concurrentes.** Nikolai lanza `enviar` en su terminal y Paola desde la suya sobre
   el mismo expediente. Las dos consultan, las dos ven cero, las dos mandan. No hay mutex —el repo
   tiene uno por *entrypoint* para el árbol de casos, pero aquí el recurso compartido no es el
   filesystem, es la cuenta de Codicert— y el spec no lo menciona.
3. **Reanudación a mitad.** Los seis envíos se hacen en secuencia; si el cuarto falla, los tres
   primeros ya están. Reanudar exige que el listado ya los muestre. Si aún no los muestra, se repiten.

**Remedio:**
- Escribir en el spec la adopción explícita de la regla del §17.4: **el vacío de un listado no
  autoriza a gastar**; si no se puede sostener la ausencia sobre algo inmediato, el flujo **se detiene
  y declara SIN VERIFICAR** en vez de mandar.
- Convertir lo que el §3.5 llama «caché» en el **registro de intención previo a la llamada**: se
  escribe `(id_personalizado, canal, destinatario, timestamp, estado=en_vuelo)` **antes** del POST y
  se cierra con el `IdEnvio` después. No es una segunda fuente de verdad sobre hechos de la plataforma
  —la verdad sigue siendo suya—; es el rastro de que *nosotros* llamamos, que es un hecho nuestro y
  que la plataforma no puede contarnos. Sin él, el §3.5 es correcto y aun así irrecuperable ante un
  timeout.
- Acotar el reencuentro por `fecha_inicio`/`fecha_fin`, que sí existen y el spec no usa.
- Decir qué hace el motor cuando encuentra un `en_vuelo` sin `IdEnvio`: parar y pedir humano, nunca
  reintentar solo.

---

### H-03 — Las cuatro firmas del §3.2 no tienen costura: no se puede probar nada sin monkeypatch, y la guarda de idempotencia no puede dar el otro valor

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:**
- spec §3.1 y §3.2: `planificar(expediente_id) -> Plan`, `ejecutar(plan, *, confirmado)`,
  `refrescar(referencia)`, `cosechar(referencia)`
- `docs/ARQUITECTURA.md:65` — el puerto de inyección de `scripts/repository_cli.py` como **fuente
  única del no-determinismo del frontal**, con `tests/_dobles/fake_drive.py` y `tests/_barrera.py`
- `tests/_matriz_contractual.py:1-45` — los cuatro planos, y por qué la matriz vive una vez como datos
- `CLAUDE.md` §Tests — «Ningún test escribe en el árbol de producción, y esa regla no tiene escotilla»
- spec §9 (los cuatro huecos) y §8 (las fases)

**El defecto:** el §3.1 sí tiene costura —`token(usuario, clave, *, entorno)` recibe lo que necesita—
pero el §3.2, que es donde vive todo el criterio de la casa, recibe **solo un identificador**. Eso
obliga a que cada función resuelva por dentro: el cliente del CRM, las credenciales de la plaza, la
base de la API, el entorno y la ruta del expediente. No hay ningún punto por el que un test inyecte un
doble. El repo tiene ya el patrón resuelto (el `Entorno` de `repository_cli`, `fake_drive`) y el spec
no lo reutiliza ni lo nombra.

Las consecuencias son tres, y la tercera es la que hace que la suite pueda ponerse verde sobre un
camino roto:

1. **No hay dónde enchufar el doble**, así que la única salida es `monkeypatch` sobre bindings de
   módulo — que es lo que `tests/_barrera.py` existe para evitar.
2. **`cosechar(referencia)` y el §6.4 escriben en el expediente** (el aportable y su manifiesto van
   «junto al aportable»). Con la firma actual, la función resuelve la ruta sola: un test que la ejerza
   escribe en el árbol real, que es lo que la regla sin escotilla prohíbe. No se puede pasar un
   `tmp_path`.
3. **La guarda de idempotencia no puede dar el otro valor.** Con un doble, `listar_envios` devuelve lo
   que el test siembre; la guarda dirá «ya existen» o «no existen» según el fixture, y el test pasará
   en los dos casos sin acreditar nada. Y el caso que importa —dos comunicaciones distintas con el
   mismo `id_personalizado` (H-01)— **es indistinguible por construcción**: no hay dato en la respuesta
   que permita separarlas, así que ningún test puede escribirse que ponga la guarda en rojo por esa
   causa. Es literalmente un instrumento que no puede emitir el otro valor.

**Modo de fallo concreto:** F1 se implementa, la suite queda verde con dobles (`enviar` no repite,
`planificar` resuelve el emisor, el plan cuadra el coste). La primera corrida real contra producción
manda el burofax desde la plaza equivocada (H-05) o duplica el envío (H-02), y la suite sigue verde
porque el doble nunca pudo representar esa condición. Precedente del repo: el verde por suerte de
reparto que describe `CLAUDE.md` §Tests, y «el doble que tapa la condición».

**Remedio:**
- Añadir al spec una sección §·Testabilidad que fije el **puerto de inyección**, en la línea del
  `Entorno` de `repository_cli`: un objeto con el cliente Codicert, el cliente CRM, el resolutor de
  credenciales, el reloj y la raíz de escritura. Las cuatro funciones del §3.2 lo reciben por keyword
  con default real.
- Declarar qué se prueba con doble y qué **no se puede probar sin enviar de verdad**, con nombre:
  la anatomía del certificado de burofax (hueco #2), la portada (#3) y el texto del SMS (#1).
- Exigir que la guarda de idempotencia venga con su **control positivo** (un envío sembrado que la
  ponga en «ya existe») y con un **mutante** que la mate; si tras H-01 hay discriminante de tipo, ese
  mutante existe. Hoy no puede existir.
- Corregir el §9: los cuatro huecos **no** se cierran todos «con una expedición completa en sandbox».
  Dos de ellos (#2 y #3) son del **burofax postal**, y que el sandbox emita un certificado postal con
  la misma anatomía que producción es, a su vez, una hipótesis sin medir.

---

### H-04 — El modelo de páginas del §6.3 contradice la única medición del documento refundido, y el aviso que lo compensa no tiene discriminante

**Severidad:** alta
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:**
- spec §6.3 — «Con el documento refundido, que es requerimiento (p. 1), OVC (p. 2) y condiciones
  económicas (p. 3), retirar solo la tercera deja la oferta entera en la segunda»
- `…/2026-09-15-reclamacion-extrajudicial-envio-unico-design.md:330-336` (§6, lo que el prototipo
  acredita) — «El documento de `W-02SRFU` (castellano e inglés, **cinco páginas** cada uno) […]
  **Páginas 1-3** con el pie de requerimiento fehaciente; **páginas 4-5** con el pie de
  confidencialidad. Comprobado extrayendo el texto de cada página del PDF»
- ídem §3, tabla: bloques A+B → sección 1 de Word; bloques C+D → sección 2
- `docs/CONVENCIONES_DESPACHO.md:202` — «D 15/D 16/D 17 CERTIFICADOS OVCs (sin la página del contenido
  económico)»
- spec §6.2 — el certificado del W-04A6LI: 6 páginas, 1-4 acta, 5-6 reproducción

**El defecto:** el §6.3 es el único sitio del spec donde se dice qué se recorta, y su modelo de páginas
es incompatible con la única medición que existe en el repo. Medido: 5 páginas, confidencialidad en
4-5. Escrito en el §6.3: 3 páginas, económicas en la 3. Y hay un tercer marco de referencia que nadie
concilia: lo que se recorta no es el documento, es **la reproducción dentro del certificado**, cuya
numeración va desplazada por las páginas de acta (4 en el único certificado medido) y, para el
burofax, posiblemente también por la portada —que el propio §9 hueco #3 declara sin medir—.

El «único remedio compatible con la decisión» que el §6.3 añade —«el motor avisa cuando, tras el
recorte, la reproducción conserva texto de la OVC»— **no trae discriminante**. El §6.2 se toma el
trabajo de fijar uno para acta/reproducción (el literal del sello en cabecera) y dice bien «no cuenta
páginas fijas: las mide». Para el aviso no hay nada equivalente: ni literal, ni marca, ni pie. Y el
spec hermano fija en su §3.4 el criterio bueno —*información permitida*, no páginas quitadas—, que es
exactamente lo que un discriminante textual necesitaría codificar y que aquí no se codifica.

**Modo de fallo concreto:** se implementa F3 contra el §6.3 literal. Sobre el certificado del
refundido, el motor retira «la tercera página» de la reproducción: por la medición del prototipo esa
página **todavía es el requerimiento fehaciente**, y la OVC entera (4-5) queda dentro. El aportable
sale con el bloque C completo, que es precisamente lo que el art. 17.4 veda, y **sin** el bloque
económico que la convención sí quería fuera. Se aporta al juzgado un documento peor que el que la
práctica manual producía.

Y si el aviso se implementa con cualquier heurística laxa, **saltará en el 100 % de los recortes**
—porque, con este modelo de páginas, la OVC siempre queda dentro—, con lo que en dos semanas nadie
lo lee. Es la guarda que mide y solo susurra.

**Remedio:**
- Sustituir en el §6.3 el modelo de páginas por la **anatomía medida** del documento que se envía
  (secciones de Word y sus pies, que es lo que el prototipo sí acredita), o declarar explícitamente
  que el mapeo página→bloque **está sin medir** para el refundido y es hito de F3 antes de escribir
  código.
- Definir el discriminante del aviso con el mismo rigor que el del §6.2: qué literal, en qué sitio,
  medido sobre qué. Si no lo hay, decir que no lo hay — un aviso sin discriminante no es un remedio,
  es una promesa.
- Resolver los tres marcos de referencia (página del documento / página de la reproducción / página
  del certificado) nombrando cuál usa `recortar(pdf, paginas_retiradas)`; hoy el parámetro es
  ambiguo entre los tres.

---

### H-05 — El emisor por plaza nunca se verifica contra el certificado, y en sandbox el mapeo ciudad→usuario no se ejerce en absoluto

**Severidad:** media
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:**
- spec §2.1 (tabla de 7 ciudades → 7 usuarios `.bd`) y §7 (una pareja de credenciales por ciudad,
  más `CODICERT_SANDBOX_USUARIO/CLAVE`, **una sola**)
- `core/ciudades.py:270-295` — `ciudad_de_equipo` devuelve `str | None`
- `…/2026-09-15-…-design.md:214-216` (§3.3) — «Identidad del oferente | art. 17.2 | **El certificado
  nombra al remitente**»
- spec §6.1: la subida se verifica por `sha256`… del fichero, no del remitente

**El defecto:** el §7 crea siete credenciales de producción y **una** de sandbox. Eso significa que en
el único entorno donde se puede probar gratis, la resolución ciudad→usuario —la pieza determinista de
la que presume el §2.1— **no se ejerce**: todas las ciudades colapsan en el mismo usuario. El modo de
fallo «se usa la credencial de una plaza para un expediente de otra» es, por construcción, invisible
en sandbox y solo aparece en producción, donde cuesta 16,97 € y un certificado.

Y cuando aparece, nada lo detecta. El API acepta el envío sin protestar —la credencial es válida, el
destinatario también—, y el motor nunca vuelve a mirar quién firma. Su única verificación (§6.1) es
que los bytes del certificado subido coincidan con los bajados, que no dice nada del remitente. El
spec hermano, en la tabla que el §5 de este spec dice servir, pone la identidad del oferente como
**primera fila** de lo que hay que acreditar.

Segundo problema, menor pero del mismo sitio: el §2.1 afirma que las siete ciudades tienen su usuario
`.bd`, y lo único medido son dos (`barcelona.bd` y `valencia.bd`, §2 y §2.1). El resto se presenta
como determinismo y es inferencia sobre 25 subusuarios que nadie enumeró.

**Modo de fallo concreto:** expediente `SaRS1 - … (W-0XXXXX)`, Santander. `CODICERT_SANTANDER_*` no
está en el `.env` (el §7 admite que las plazas se añaden «cuando lleguen»). El motor, según el §7,
«funciona para las demás» — pero el spec no dice qué hace con esta. Dos ramas, las dos malas: si cae
a una credencial por defecto, el burofax sale nombrando a `barcelona.bd` como remitente y el
certificado acredita un oferente que no es el que reclama; si revienta, revienta **después** de que
el humano aprobara el plan y —si el fallo es al pedir el token de la segunda llamada— con parte de la
expedición ya gastada.

**Remedio:**
- Que `planificar` **resuelva y valide la credencial de la plaza antes de imprimir el plan**, y que el
  plan muestre el usuario emisor literal (`barcelona.bd`) junto al entorno. Sin credencial de esa
  plaza, el plan no se emite: se para y se dice cuál falta.
- Que `cosechar` **verifique el remitente del certificado** contra el emisor esperado, igual que
  verifica el `sha256`. Es la fila 1 del §3.3 del spec hermano y hoy no la cubre nadie.
- Decir qué hace el motor cuando `ciudad_de_equipo` devuelve `None` (código desconocido, expediente en
  `_Sin clasificar`, `codigo` vacío). Hoy: no dice nada.
- Declarar en el §9 que el mapeo ciudad→usuario **no es verificable en sandbox** y decir cómo se
  acredita la primera vez en producción.

---

### H-06 — La subida al gestor documental no tiene módulo asignado, y `cosechar` no tiene idempotencia: el repo ya pagó un certificado duplicado

**Severidad:** media
**Coste del remedio:** acotado

**Qué he leído para afirmarlo:**
- spec §3 (tres módulos nuevos: `core/codicert.py`, `core/expedicion_certificada.py`,
  `core/certificado_aportable.py`) y §6.1 (la subida, dentro de `cosechar`)
- `docs/INTEGRACION_SUDESPACHO.md:2714-2758` (§17.1, el flujo de tres pasos) y `:2812-2819` — «una
  guarda anti-duplicado que consultaba el **listado** […] **lo subió dos veces**. El duplicado se
  detectó por `sha256` idéntico de los dos binarios»
- `core/` completo: **no existe ninguna función de subida**. `grep -rn "presigned_upload\|api/documents"`
  sobre `core/` y `scripts/` solo devuelve el camino de **descarga** (`core/sync_sudespacho.py:745-845`)
- `core/sudespacho_relations.py:1985` — `get_relaciones(element, exp_id)` sí existe, y es lo que
  `planificar` necesita para el §4

**El defecto:** el §6.1 dice que la subida va «por la vía ya medida», y la vía medida es un
**documento** (`§17`), no código. En `core/` no hay implementación. El §3, que es donde el spec reparte
responsabilidades, no le da hogar: `core/codicert.py` «no sabe qué es un expediente», y la subida al
CRM no es asunto suyo; queda por descarte dentro de `core/expedicion_certificada.py`, que es donde vive
el criterio del despacho, no el transporte al CRM. El resultado previsible es un cuarto cliente
`x-api-key` naciendo dentro del módulo de expediciones, huérfano de `core/sudespacho_*`, y un quinto la
próxima vez que alguien tenga que subir algo.

Lo mismo por el otro lado: el §4 dice «del CRM salen las partes contrarias por su relación con el
expediente» y no nombra `sudespacho_relations.get_relaciones`, que es exactamente eso y ya está
escrito y probado.

Segunda mitad, independiente: **`cosechar` no tiene idempotencia**. El §4.2 la diseña solo para
`enviar`. Una segunda corrida de `cosechar` —porque el estado cambió, porque faltaba un envío, porque
se relanzó— vuelve a bajar y **vuelve a subir**. El §6.1 verifica por resultado *después* de subir,
que es lo correcto y no es una guarda anti-duplicado. Y el §17.4 documenta que el listado del gestor
tiene latencia, con la consecuencia medida en este mismo repo: un certificado subido dos veces.

**Modo de fallo concreto:** `cosechar W-04A6LI` se ejecuta el lunes y sube tres certificados. El
miércoles entra el estado 20 del tercer destinatario y se relanza `cosechar` para recogerlo. Los tres
anteriores se vuelven a bajar y a subir: el expediente queda con **seis** documentos, tres pares de
`sha256` idéntico, y la carpeta que después alimenta el `D 13/D 14/D 15` del §7 de
`CONVENCIONES_DESPACHO.md` deja de ser enumerable sin criterio humano.

**Remedio:**
- Asignar la subida a un módulo por nombre, y que sea de la familia `sudespacho_*` (p. ej.
  `core/sudespacho_documentos.py`), con el contrato del §17.1 dentro y `core/expedicion_certificada.py`
  llamándolo. Aunque este spec sea su primer consumidor, no es su dueño.
- Nombrar `get_relaciones` en el §4 como la vía de lectura de contrarios.
- Dar a `cosechar` su guarda, con la regla del §17.4: comprobar por `related_register` y por
  `origen_id` —que es una clave del contenido y por tanto inmediata—, no por el listado; y si no se
  puede sostener la ausencia, **parar y declarar SIN VERIFICAR**, no subir.

---

### H-07 — La puerta humana aprueba un plan que nadie vuelve a contrastar, y `confirmado` es un keyword

**Severidad:** media
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:**
- spec §4.1 («`plan` no envía. **Escribe** el plan, lo enseña con el coste desglosado y termina.
  `enviar` exige el plan y una confirmación explícita») y §3.2 (`ejecutar(plan, *, confirmado)`)

**El defecto:** la puerta está bien colocada —dos verbos, el gasto detrás del segundo— y bien
argumentada. Pero es **sorteable por dos vías distintas**, y ninguna es exótica:

1. **El plan puede estar rancio.** `plan` escribe un artefacto; `enviar` lo consume. Entre los dos no
   hay nada que ate el plan al estado del CRM en el momento de mandar: ni digest del plan, ni
   caducidad, ni re-planificación con comparación. Lo que el humano leyó y lo que sale pueden ser
   cosas distintas.
2. **`confirmado` es un parámetro.** La puerta vive en el CLI; en el core es un booleano que cualquier
   llamador suministra. `ejecutar(plan, confirmado=True)` desde un script, un reintento o un test es
   una expedición completa. El §4.1 dice «ninguna automatización de la casa debe poder gastarlos sin
   que alguien haya leído a quién», y el diseño lo deja a un keyword.

**Modo de fallo concreto:** se corre `plan` el viernes; el plan lista dos requeridos y estima 34,33 €.
El lunes Ana corrige en el CRM la dirección de uno de los requeridos (que estaba mal) y añade el
segundo domicilio que faltaba. Se corre `enviar` con el plan del viernes: el burofax sale a la
dirección vieja —16,97 € y un certificado que acredita entrega en un domicilio que ya se sabía
equivocado— y el tercer domicilio no recibe nada, sin que ningún mensaje lo diga.

**Remedio:**
- `enviar` **replanifica y compara**: si el plan recalculado difiere del aprobado (destinatarios,
  domicilios, documento, coste), no manda; enseña el diff y pide un plan nuevo. Es la misma forma de
  «verificar por resultado» que el repo aplica en todas partes.
- Sellar el plan con el `sha256` del documento y un `sha256` del propio plan, que `enviar` exige.
- Subir la puerta al tipo: en vez de `confirmado: bool`, que `ejecutar` reciba un objeto de
  confirmación que solo el CLI sepa construir a partir del plan leído (p. ej. con el digest dentro).
  Un booleano no puede distinguir «un humano leyó» de «alguien puso True».

---

### H-08 — El plan estima el coste y nunca lo contrasta con el crédito

**Severidad:** media
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:**
- spec §3.1 (`credito(token) -> Decimal` está en la superficie del cliente), §4.1 («lo enseña con el
  coste desglosado»), §4.2 (la reanudación), §1.4 (la tarifa)

**El defecto:** `credito` se declara en el §3.1 y no se usa en ninguna parte del diseño. El §4.1
calcula el coste estimado, lo imprime y no lo compara con nada. Es una pieza construida que nadie
encadena, y en este caso la que falta impide que la puerta humana decida con el dato que importa.

**Modo de fallo concreto:** expedición con dos domicilios y dos requeridos: 2 × 16,9716 + 4 × ~0,79 =
37,10 €. El saldo del subusuario es 20 €. El humano aprueba. Sale el primer burofax (16,97 €), salen
las electrónicas, y el segundo burofax falla por saldo. La expedición queda coja: **un requerido
requerido y el otro no**, con la fecha de recepción acreditada solo para el primero — y el §5 dice
que de esa fecha cuelgan los plazos. Se reanuda cuando E&V recargue, lo que puede ser días, y el
expediente acaba con dos fechas de requerimiento distintas para la misma comunicación.

**Remedio:** `planificar` llama a `credito` y el plan imprime «coste estimado / crédito disponible /
margen». Si el margen es negativo, el plan se emite **marcado como no ejecutable** y `enviar` se niega.
Dos líneas, y convierten un fallo a mitad en una parada antes de empezar.

---

### H-09 — La fuente de verdad se dimensiona con el denominador equivocado

**Severidad:** media
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:**
- spec §3.5 — «Con 100 elementos por página y **el volumen real del despacho**, es barato»
- spec §2 — «Cuenta maestra `engelvoelkers` […] **25 subusuarios**. Envíos del subusuario
  `barcelona.bd` del 10-09-2026, referencia `BCN-OS-008684 - OVC`»
- spec §2.1 — «los envíos salen del usuario `.bd` del Market Center **que reclama**»
- OpenAPI: `GET /envios` pagina sobre los envíos **del usuario autenticado**

**El defecto:** el spec decide bien dónde vive la verdad y paga el precio a conciencia, pero cifra ese
precio sobre el volumen equivocado. Los envíos que hay que paginar **no son los del despacho**: son los
de `barcelona.bd`, que es la cuenta compartida del Market Center y por la que sale todo el bad debt de
la plaza —incluido lo que el propio E&V manda desde el portal, como acredita el `BCN-OS-008684 - OVC`
del §2, que es una referencia de operación de E&V y no un expediente del despacho—. El denominador es
el Market Center, no el despacho, y nadie lo ha contado.

Hay un segundo efecto que el §7 no nombra: usar esa credencial da al motor **lectura de todo el tráfico
certificado de la plaza**, incluidas comunicaciones de asuntos que no son del despacho. Para un motor
que va a paginar el histórico entero como rutina, eso merece constar.

**Modo de fallo concreto:** `estado W-04A6LI` sobre `barcelona.bd`. Si la plaza lleva 4.000 envíos al
año, son 40 páginas por consulta, y el §5 dice que `estado` no es un verbo ocasional: es el que sigue
los plazos. Cada consulta de estado de cada expediente vivo pagina el histórico completo de la plaza.
El §3.5 dice «si algún día no lo fuese, el remedio es el índice local» — pero el índice local es caché
y el §3.5 dice que se puede borrar sin perder nada, así que el primer uso tras un borrado vuelve a
pagar el escaneo completo.

**Remedio:** acotar la consulta con `fecha_inicio`/`fecha_fin` (existen y el spec no los usa: la fecha
de la expedición la conoce el motor). Y corregir la frase del §3.5: el volumen es el de la plaza, y
está sin medir — o se mide antes de F1, o se dice que está sin medir.

---

### H-10 — El `asunto` y el `cuerpo` de cada envío no se especifican en ninguna parte

**Severidad:** media
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:**
- spec §3.1 — `enviar_burofax(…, *, asunto, cuerpo, id_personalizado)` y `enviar_eec(…, *, asunto,
  cuerpo, …)`: los dos parámetros existen y nadie dice de dónde salen
- spec §3.2 — el `Plan` lleva «el emisor resuelto, la lista de envíos previstos […] el documento
  elegido con su `sha256`, el coste estimado […] y las ausencias declaradas». No lleva el texto.
- `docs/CONVENCIONES_DESPACHO.md:136-139` — el literal del SMS de la casa
- OpenAPI: confirmado que **no existe campo para el texto de la notificación SMS**; solo `asunto`,
  `cuerpo` y `campos_verificacion`
- spec §1.1 — «De ahí el literal de `CONVENCIONES_DESPACHO.md` §5, *«Consulte el documento adjunto»*»

**El defecto:** el spec razona con cuidado sobre qué endpoint lleva el documento y por qué el literal
de la casa tiene sentido, y luego **no dice quién compone `asunto` ni `cuerpo`, ni de qué fuente, ni
si el humano los ve antes de aprobar**. Son el texto que el requerido lee antes de abrir nada, en una
comunicación jurídica con efectos de prescripción, y para el burofax son además lo que se imprime.
El §9 hueco #1 declara con honestidad que el texto del SMS puede no caber en ningún sitio — pero eso es
una pregunta sobre *el canal*, no sobre *de dónde sale el texto*, que sigue sin contestar para los tres
canales.

**Modo de fallo concreto:** quien implemente F1 tiene que inventarlos. Lo más probable es que salgan del
nombre del documento o de una constante del módulo. En cualquiera de los dos casos, el plan del §4.1 los
enseña o no los enseña —el §3.2 no los incluye en el `Plan`—, así que la puerta humana aprueba «a quién»
y «cuánto» sin haber leído **qué dice el envío**. Y si el `asunto` se compone del nombre del documento
refundido, puede acabar nombrando la OVC en el asunto de un correo: mención a su contenido, que es lo
que el art. 17.4 veda y el §6.3 se toma el trabajo de discutir para el aportable.

**Remedio:** fijar en el §4 la procedencia de `asunto` y `cuerpo` por canal, con el literal de
`CONVENCIONES §5` para el SMS, y **meterlos en el `Plan`** del §3.2 para que la puerta humana los lea.
Añadir la regla de que ni el asunto ni el cuerpo pueden nombrar la OVC.

---

### H-11 — Decisiones pequeñas sin tomar que quien implemente tendrá que inventar

**Severidad:** baja
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:**
- spec §7 (nomenclatura de credenciales, «…una pareja por ciudad de las siete…») contra
  `core/ciudades.py:25-33` — la ciudad canónica es **«San Sebastián»**, con espacio y tilde
- spec §7 (`CODICERT_ENTORNO=sandbox|produccion`) contra §7 («El motor arranca en sandbox por defecto.
  Producción exige que la orden lo diga»)
- spec §6.4 («Un **manifiesto** junto al aportable») y §3.5 («El índice local es caché»)
- spec §4.5 (solo se valida el móvil) contra `core/sudespacho_relations.py:1539-1553` — `provincia` es
  un Select con **52 valores literales** del CRM (`Baleares (Illes)`, `Guipúzcoa`, `A Coruña`…), y el
  burofax exige `provincia` y `pais` = «España»
- `docs/ARQUITECTURA.md:200` — `CaseWorkspaceResolver` es el SSOT de sobre qué copia se escribe, y la
  fila del mapa de dependencias dice «**Todo entrypoint que escriba en un expediente**»

**El defecto y sus modos, uno por línea:**

1. **La variable de entorno de San Sebastián.** Una variable de entorno no admite espacio ni tilde. El
   spec da la regla «una pareja por ciudad» y la ciudad canónica es `San Sebastián`. Quien implemente
   elegirá entre `CODICERT_SAN_SEBASTIAN_*` y `CODICERT_SANSEBASTIAN_*`; el `.env` tendrá la otra, y
   el fallo será «Santander funciona y San Sebastián no» sin que nadie entienda por qué. Ninguna de
   las 16 claves aparece en `.env.example`, que sí documenta todas las demás integraciones.
2. **Dos mecanismos para el entorno, sin precedencia.** `CODICERT_ENTORNO` en `.env` y «la orden lo
   dice». Si alguien pone `CODICERT_ENTORNO=produccion` para un envío real y lo deja puesto, «arranca
   en sandbox por defecto» deja de ser cierto para siempre y nadie se entera: el único indicador es la
   cabecera del plan, que es una lectura humana. Para una pieza que gasta e irreversibiliza, la
   frontera no debería depender de que alguien lea una línea.
3. **Dónde se escribe.** El §6.4 archiva tres cosas y no dice en qué carpeta de `CASO_SUBDIRS`; el §3.5
   habla de una caché local sin decir dónde vive. Y si el destino es el árbol del expediente, el
   entrypoint **escribe en un expediente** y le aplica la matriz del `CaseWorkspaceResolver`, que el
   spec no menciona: con el caso prestado a otra máquina, el motor escribiría sobre la copia que no
   toca.
4. **Validación parcial de la ficha postal.** El §4.5 valida el móvil «antes de gastar, no en el 422»,
   que es el criterio correcto — y luego no lo aplica a nada más. `provincia` viene del CRM como
   literal de un Select de 52 valores que nadie ha cruzado con lo que el burofax acepta, y `pais` solo
   admite «España». Un requerido con domicilio fuera de España o con una provincia que Codicert
   escriba distinto produce el 422 que el §4.5 dice querer evitar — y lo produce **a mitad de
   expedición**, con las electrónicas ya mandadas.

**Remedio:** fijar el slug de cada ciudad en el spec (tabla de tres columnas: ciudad canónica / usuario
Codicert / prefijo de variable); declarar la precedencia orden > entorno y que producción exige la
orden **aunque** el entorno lo diga; nombrar la carpeta destino y el paso por `CaseWorkspaceResolver`;
y extender la validación del §4.5 a todos los campos requeridos del destinatario postal.

---

### H-12 — Las dos rondas se presentan como lectura de la tabla, y la tabla da una

**Severidad:** baja
**Coste del remedio:** trivial

**Qué he leído para afirmarlo:**
- spec §10 — «**Dos rondas**: una sobre este diseño y otra sobre el diff. El radio de daño no es el
  tamaño del código…»
- `CLAUDE.md` §«Cuántas rondas»: dos rondas si la pieza «decide **quién puede escribir** sobre qué
  copia, o puede **destruir o corromper datos de cliente**»; «todo lo demás → **1** — sobre el diff»
- `…/2026-09-15-…-design.md:388` — H-12 del spec hermano, adjudicado **confirmado** dos días antes:
  «Vestí de deducción lo que era una decisión de cobertura. La fila de una ronda dice “sobre el diff”»

**El defecto:** esta pieza no decide quién escribe sobre qué copia ni destruye datos de cliente; por la
tabla le corresponde **una** ronda, sobre el diff. Que merezca dos es muy defendible —gasta dinero y
manda comunicaciones irreversibles a terceros— pero eso es **ampliar la cobertura por decisión**, no
leerlo de la tabla. El §10 lo redacta como si se dedujera, que es exactamente el movimiento que el
revisor del spec hermano marcó hace dos días y que su autor adjudicó como confirmado.

La dirección del error es la segura (más revisión, no menos), y por eso es baja. Pero el registro
importa: si la tabla se puede leer para arriba cuando conviene, se puede leer para abajo cuando conviene.

**Modo de fallo concreto:** el próximo spec cita el §10 de este como precedente de que «el radio de daño
económico da dos rondas», y la tabla acaba diciendo lo que cada autor necesite. El coste ya está medido
en `CLAUDE.md`: «redefiní el disparador» en el 55º cierre.

**Remedio:** reescribir el §10 como el §7 del spec hermano ya fue reescrito: la tabla da una; se pide
una segunda **por decisión de cobertura**, con el motivo delante y el nombre de quien la decide.

---

## Lo que he comprobado y está bien

**El contrato de la API está bien leído.** Verificado contra `https://ws.codicert.tk/rest.json` (GET,
sin auth, sin escritura):

- `POST /envios/burofax`: `destinatarios` con `minItems: 1, maxItems: 1` — el §1.1 es exacto, y la
  consecuencia que el spec saca de ahí («dos domicilios son dos llamadas, siempre») es correcta.
  `pais` solo admite «España», y `nombre`/`direccion`/`poblacion`/`provincia`/`cp` son obligatorios;
  `a_atencion` y `telefono`, opcionales — el mapeo de la ficha postal del §2 casa con el esquema.
- `POST /envios/entrega-electronica-certificada`: `tipo_entrega` ∈ {`correo`, `sms`} y `destinatarios`
  **sin** `maxItems`. Confirma que la regla 1 del §4 («nunca se agrupan dos requeridos») es criterio
  de la casa y no límite del contrato, que es como el spec la presenta.
- `id_personalizado`: `maxLength` 20 y la descripción dice literalmente que se puede asignar a varios
  envíos. El §1.2 es exacto.
- `GET /envios`: los parámetros son `pagina`, `longitud`, `orden`, `ordenar_por`, `fecha_inicio`,
  `fecha_fin`, `estado_fecha_inicio`, `estado_fecha_fin`, `tipo`, `estado`, `id`. **No filtra por
  `id_personalizado`**: la admisión del §3.5 es correcta y honesta, no una excusa.
- Y un dato que el §3.5 necesita y no dice: el item del listado (`EnvioSimple`) **sí trae
  `id_personalizado`**, junto a `asunto`, `estado`, `tipo`, `tipo_titulo`, `destinatarios`, `fecha`,
  `fecha_expiracion` e `id`. Eso es lo que hace viable «traer páginas y filtrar en casa». Sin ello la
  decisión del §3.5 no se sostendría. Conviene escribirlo.
- **No existe campo para el texto del SMS de notificación**: el hueco #1 del §9 está bien declarado y
  la sospecha del spec es correcta.

**El resto de anclajes que he abierto y confirmado:**

- `core/ciudades.py:25-33` — las siete ciudades canónicas son exactamente las del §2.1, con la
  ortografía que el spec usa. `ciudad_de_equipo` existe y hace lo que el §2.1 dice (`core/ciudades.py:270`).
- `core/sudespacho_relations.py:235-261` — `clientes_contrarios` trae **todos** los campos que el §4
  enumera (`nombre`, `apellido1`, `apellido2`, `direccion`, `poblacion`, `provincia`, `cp`, `email`,
  `movil`, `nif`), y además `telefono1`. El §4 no exagera. Y la lectura existe:
  `get_relaciones(element, exp_id)` en `:1985`.
- `docs/INTEGRACION_SUDESPACHO.md:2720-2758` — el flujo de subida del §6.1 reproduce fielmente el §17.1,
  incluida la regla que el spec repite bien: «la subida **se verifica por resultado**», bajando lo
  subido y comparando el `sha256`. Ni el 201 ni el ETag valen.
- `docs/bitacora/2026.md:2453` — el certificado `006casm113n` y el envío de W-04A6LI por Codicert están
  registrados; la anatomía del §6.2 se apoya en un artefacto real del despacho.
- `AGENTS.md:95-118` — el §10 cita bien el contrato del revisor sustituto: indisponibilidad real,
  sesión limpia, `revisor: Claude Code (sesión independiente)` nunca «Codex», y la declaración en prosa
  de que la independencia es más débil. El spec lo cumple por adelantado.
- `…/2026-09-15-…-design.md:378` — el §6.3 cita correctamente el H-02 del spec hermano como
  «adjudicado como confirmado», y **declara la tensión con la decisión de Nikolai en vez de
  disimularla**. Es el párrafo mejor escrito del documento: dice qué decidió el principal, por qué el
  diseño lo respeta, y qué queda mal a pesar de ello.
- La separación de capas del §3 respeta la arquitectura: `core/codicert.py` como transporte que «no
  sabe qué es un expediente», el criterio de la casa en `core/expedicion_certificada.py`, el CLI en
  `scripts/`, y `Plan` como estructura inspeccionable y no como efecto. Es la forma correcta.
- El §7 no rompe la política de secretos: `.env` gitignored, nada en el árbol ni en el chat, y
  `leak-scan` corre en CI (`.github/workflows/`). El patrón de leer credenciales del entorno en el
  punto de uso —y no por `core/config.Settings`— es además el que ya siguen `sudespacho_create`,
  `sudespacho_relations`, `sudespacho_actuaciones`, `crm_atlas` y `llm_cloud`; la frase del docstring
  de `core/config.py` («cualquier módulo del core debe importar `settings`») está desmentida por la
  práctica del propio repo y **no la cuento como incumplimiento**.
- El §5 distingue bien el estado del envío del estado de la expedición, y el §1.3 codifica la frontera
  «Procesado ≠ Entregado», que es el error que más caro sale en este terreno.

## Lo que NO he podido verificar

- **Nada de lo que el spec mide en producción.** No he autenticado contra Codicert ni he llamado a
  ningún endpoint que requiera token. Por tanto tomo como dichas, sin reproducir: la tarifa «80» del
  §1.4, los 25 subusuarios, los tres envíos del `BCN-OS-008684 - OVC` del §2, el mapeo de la ficha
  postal observado en el detalle del burofax, y el comportamiento idéntico de las dos bases ante
  credenciales falsas (§1).
- **La existencia de los siete usuarios `.bd`.** El spec mide dos (`barcelona.bd`, `valencia.bd`). Los
  otros cinco no los he podido comprobar por ninguna vía de lectura, y el spec tampoco los acredita
  (ver H-05).
- **La anatomía del certificado `006casm113n`** (§6.2: `AcroForm`, `SigFlags: 3`, `/ByteRange`,
  `adbe.pkcs7`, `DocMDP`, páginas 1-4 acta y 5-6 reproducción). El PDF no está en el repo —vive en un
  expediente, fuera de él— y no lo he abierto. Lo doy por dicho; el `sha256` que lo acreditaría no
  consta en el spec.
- **El texto de la cabecera discriminante del §6.2** («Este certificado contiene un sello temporal y se
  encuentra firmado digitalmente con un certificado reconocido»): no he podido comprobar que sea
  idéntico en el certificado de burofax, que es justo lo que el propio hueco #2 declara sin medir.
- **El comportamiento del sandbox.** No sé si emite certificado de burofax, ni si su anatomía coincide
  con la de producción. El §9 supone que sí (dice que los cuatro huecos se cierran ahí); yo no lo he
  podido confirmar y por eso lo convierto en parte de H-03.
- **La suite.** No la he ejecutado: el encargo es de solo lectura y `pytest` habría escrito
  `__pycache__` y `.pytest_cache` dentro del worktree. Mis afirmaciones sobre testabilidad son sobre
  las firmas del §3.2 y sobre los contratos de test del repo (`tests/_matriz_contractual.py`,
  `tests/_dobles/fake_drive.py`, `ARQUITECTURA.md:65`), no sobre una corrida.
- **El paginado real de `barcelona.bd`.** H-09 afirma que el denominador es el Market Center y no el
  despacho; eso se sigue de que la cuenta es compartida y de que la referencia medida en el §2 es de
  E&V. **Cuántos envíos hay, no lo sé**, y el spec tampoco: ese es precisamente el hallazgo.
<!-- informe-literal:fin:q7w3 -->

## 2. Evidencia verificada por mí contra la fuente

La adjudicación está en el **§11 del spec**, hallazgo por hallazgo. Aquí queda solo lo que
**verifiqué yo mismo abriendo la fuente**, que es lo que distingue confirmar de creer:

- **LO 1/2025** — descargada del BOE en vivo. Mi primer identificador, `BOE-A-2025-1`, era **una
  norma valenciana de simplificación administrativa**; el correcto es **`BOE-A-2025-76`**, hallado
  en el sumario del 3 de enero de 2025. Literales comprobados: art. 7.1 (interrupción desde el
  intento «en el domicilio personal o lugar de trabajo que le conste a la persona solicitante, o
  bien a través del medio de comunicación electrónico empleado por las partes en sus relaciones
  previas»), art. 7.3 (el año, con sus **dos** *dies a quo* unidos por «respectivamente»), art.
  10.2 («y que ha podido acceder a su contenido íntegro»), art. 10.4.a (treinta días naturales
  desde la recepción) y art. 17.2 y 17.4 (constancia «tanto de la oferta **como de la
  aceptación**»; «un mes»; «sin que pueda hacerse mención a su contenido»).
- **LEC art. 326** — `BOE-A-2000-323`, literal. El apartado 4 condiciona la presunción a que el
  servicio sea **cualificado** y figure «en la lista de confianza de prestadores y servicios
  cualificados», e invierte la carga de la comprobación al impugnante, con costas y multa por
  temeridad.
- **OpenAPI de Codicert** — `https://ws.codicert.tk/rest.json`, descargado de nuevo. Comprobado
  por mí: el patrón `^[67]\d{8}$` existe **solo** en `DestinatarioPostal.telefono` y en
  `SolicitudSms`, y **no** en `DestinatarioVerificable`; `SolicitudBurofax` redefine
  `id_personalizado` inline **sin `maxLength`**; `campos_verificacion` tiene `default: []`; la
  cabecera `x-json-ficheros` la declaran **diez** endpoints, los dos que uso entre ellos.
- **Códigos de estado** — recontados sobre la documentación renderizada: son **37**, no los 43 que
  escribí, y el **21, «Recordatorio lectura entregado»**, falta en mi tabla del §1.3 pese a ser el
  estado en el que quedaron dos de los tres envíos de producción que yo mismo puse de ejemplo.
- **Mapa de páginas del refundido** — `2026-09-15-reclamacion-extrajudicial-envio-unico-design.md`
  §6: el documento de `W-02SRFU` tiene **cinco** páginas, «1-3 con el pie de requerimiento
  fehaciente; páginas 4-5 con el pie de confidencialidad». Mi §6.3 decía tres. El pie propio de la
  sección confidencial es, además, un discriminante estructural mejor que cualquier heurística.

**Lo que NO pude verificar, declarado como tal y no como refutado:**

- Si **Codicert figura en la lista de confianza como prestador cualificado**. La firma de sus
  correos comerciales lo afirma, pero eso es autodeclaración: la fuente es la *trusted list*
  española y no la he consultado. De ello depende el art. 326.4 LEC, luego depende el precio real
  de romper la firma al recortar.
- La **anatomía del certificado de un burofax**. Lo medido es el de una entrega electrónica
  certificada (`006casm113n`, 6 páginas, 1-4 acta y 5-6 reproducción).
- Si el sandbox emite certificados con la **misma anatomía** que producción.
- El **volumen de envíos de la cuenta de un Market Center**, del que depende que paginar `GET
  /envios` sea barato.

**Un extremo refutado contra la fuente**, y conviene que conste porque va en mi favor: la lente de
arquitectura dice en su H-05 que las siete ciudades con usuario `.bd` son «inferencia sobre 25
subusuarios que nadie enumeró». Sí se enumeraron, el 2026-09-17, en `/masterusuarios` de la cuenta
maestra de producción: `barcelona.bd`, `bilbao.bd`, `madrid.bd`, `sansebastian.bd`, `santander.bd`,
`sevilla.bd` y `valencia.bd` **existen las siete**. El revisor no tenía acceso al portal y no podía
verlo. Lo que su hallazgo sí acierta —y por eso se confirma en lo principal— es que **el spec no
decía que estuviera medido**, y una afirmación sin su medición al lado es indistinguible de una
suposición.
