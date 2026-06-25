# Stress-test — F4.D1: Los tres tiempos del evento probatorio

> **Para:** revisor adversarial (Perplexity).
> **Formato:** handoff anonimizado. No hay datos reales de cliente; los actores y cifras son genéricos.
> **Qué pido:** romper la decisión candidata con casos límite, contrastarla con los marcos de referencia citados, y señalar dónde introduce error, ambigüedad o pérdida de información. No busco confirmación; busco fallos.

---

## 1. Contexto mínimo del sistema

Estoy diseñando una **cronología unificada de prueba**: una herramienta que fusiona en una sola línea de tiempo todas las fuentes de prueba de un expediente litigioso (correo electrónico, mensajería instantánea, registros de CRM, entrevistas grabadas y transcritas, documentos, asientos registrales públicos). Es trabajo jurídico-forense: separa con rigor **lo que consta en la prueba** de **lo que se infiere de ella**.

Piezas ya cerradas y **congeladas** (no se discuten aquí; solo se respetan como invariantes):

- **Modelo B (disciplina rectora):** el átomo de la línea de tiempo es un **acto datado anclado a un registro de fuente** ("este mensaje se envió", "esta oferta se firmó", "este asiento se publicó"), **nunca un hecho del mundo inferido** ("la venta se consumó"). Lo segundo vive en una **capa derivada** aparte (hechos probados, con su grafo de apoyos y un semáforo 🟢🟡🔴).
- **Granularidad:** un mensaje = un evento; una **entrevista = un** evento (categoría "esto se declaró"); un documento por sí solo = **cero** eventos (es prueba que se engancha a un acto, no un acto).
- **Declaraciones:** una declaración (entrevista, testimonio) narra hechos pasados. El acto canónico es **la declaración misma**; el hecho pasado narrado, si carece de registro propio, o bien queda como **enlace de testimonio**, o bien se modela como **evento reconstruido de baja confianza** marcado `modo_recuperacion = reconstruida`, enlazado al acto declarativo por una relación `reconstruye`.
- **Ficha del acto (campos temporales ya fijados):**
  - `cuando.fecha` en **EDTF / ISO 8601-2** (admite fecha precisa, aproximada `~`, incierta `?`, intervalos, dígitos sin especificar `XX`).
  - `cuando.fecha_fin` opcional (actos durativos).
  - `cuando.orden_relativo` — secuencia dentro de la fuente cuando no hay fecha absoluta.
  - `fecha_documento` (opcional) — fecha del soporte, distinta de la fecha del acto.
  - `modo_recuperacion` — directa / reconstruida-desde-cita / reenviada.
  - `procedencia` — fuente, localizador interno, clave natural, referencia de hash de intake.
- **Regla de no inflar fichas:** decisiones anteriores rechazaron por sobreingeniería un campo `tipo_tiempo` y, en general, multiplicar casillas. Las soluciones se prefieren como **reglas/invariantes sobre metadatos existentes**, no como campos nuevos.

---

## 2. El problema de F4.D1

Las fuentes traen el tiempo de forma heterogénea y, sobre todo, **mezclan tres tiempos distintos** que no deben confundirse:

- **Tiempo del HECHO** — cuándo ocurrió el acto (se firmó la oferta el día X).
- **Tiempo de ENUNCIACIÓN** — cuándo alguien lo declaró/afirmó (en la entrevista del día Y se dijo "la oferta se firmó en marzo").
- **Tiempo de REGISTRO** — cuándo la fuente capturó el dato (el CRM registró la actividad el día Z; el PDF que prueba el acto está fechado el día W; la extracción forense se hizo el día V).

Ejemplos del banco de pruebas (genéricos): un correo enviado (hecho = enunciación, coinciden); una entrevista grabada de preparación donde un participante narra hechos de hace dos años ("en torno a la primavera me dijo que…"); un documento fechado hoy que prueba un acto de hace cuatro años; un asiento de registro público cuya fecha de publicación ≠ fecha del hecho que refleja; un log de actividad de CRM con su propio timestamp de sistema.

El contenedor (EDTF, `fecha_fin`, `orden_relativo`, `fecha_documento`, `modo_recuperacion`) ya existe. **Lo que falta es la semántica:** ¿qué tiempo se coloca en la línea de tiempo única, y dónde viven los otros dos?

---

## 3. DECISIÓN CANDIDATA a romper

**Un solo tiempo ancla la línea: el tiempo del HECHO del acto** (lo que guarda `cuando.fecha` en EDTF). Tres reglas de deslinde:

1. **Acto no declarativo** (correo enviado, oferta firmada, pago, inscripción): el tiempo del hecho **coincide** con el de enunciación —el acto es su propia ocurrencia—. Una sola fecha. No se añade nada.

2. **Acto declarativo/narrativo** (entrevista, "como te dije ayer"): el acto que entra en la línea es **la enunciación**, datada en su tiempo de enunciación. El **hecho pasado narrado** NO es ese acto: es enlace de testimonio, o bien —si es fuente única— un **evento reconstruido** propio, con su tiempo del hecho difuso (EDTF aproximado) y `modo_recuperacion = reconstruida`, unido por enlace `reconstruye`. El tiempo de enunciación queda en el acto declarativo padre; el tiempo del hecho, en el evento reconstruido hijo.

3. **Tiempo de REGISTRO** (timestamp de log, fecha de extracción, fecha del soporte documental): **nunca es una posición en la línea de tiempo**. Es metadato de procedencia/custodia. Vive en `procedencia` + `fecha_documento`; se usa solo para autenticidad y para detectar la divergencia `fecha_documento ≠ fecha_hecho`. No se le abre casilla temporal propia.

**Consecuencia sobre campos:** no se triplica la fecha en cada acto. Se introduce **un único campo nuevo condicional, `tiempo_enunciacion`, presente solo cuando diverge del tiempo del hecho** (es decir, en eventos reconstruidos). En el caso normal, un solo campo de fecha.

---

## 4. Invariantes que la solución NO puede violar

- (I1) El átomo sigue siendo un acto anclado (Modelo B); no se cuela inferencia en la capa canónica por la puerta del tiempo.
- (I2) No inflar la ficha: cualquier campo nuevo debe justificarse contra "regla sobre metadato existente".
- (I3) Coherencia con el modelo de declaración ya cerrado (declaración = acto; hecho narrado = enlace o evento reconstruido).
- (I4) Trazabilidad/verificabilidad por un tercero (cada fecha debe anclarse a su fuente con pinpoint).
- (I5) El tiempo de registro no debe poder "contaminar" la ordenación material de los hechos.

---

## 5. Marcos de referencia que pido contrastar explícitamente

Quiero que evalúes la candidata **contra** estos marcos y me digas en cuáles encaja, en cuáles choca y qué me estoy perdiendo:

1. **Bases de datos temporales — bitemporalidad/tritemporalidad.** *Valid time* (cuándo el hecho es cierto en el mundo) vs *transaction time* (cuándo el sistema lo registró) vs, en literatura tri-temporal, *decision time* (cuándo se decidió/afirmó). Mi triple "hecho / registro / enunciación" parece un mapeo casi exacto. **Pregunta dura:** ¿colapsar enunciación a "solo cuando diverge" sacrifica algo que un modelo tritemporal completo conservaría? ¿Hay consultas (auditoría, reconstrucción de "qué se sabía cuándo") que se vuelven imposibles?

2. **EDTF / ISO 8601-2.** ¿Cubre realmente todos los patrones de fecha difusa de declaración oral ("a principios de…", "el verano siguiente a X", "antes de la firma")? ¿Dónde se queda corto y obliga a `orden_relativo`?

3. **Allen's interval algebra / OWL-Time / CIDOC-CRM (time-spans, before/after, fuzzy boundaries).** Para ordenar eventos difusos junto a precisos hace falta un operador de comparación. ¿La candidata, al anclar todo al "tiempo del hecho", deja bien definida la relación de orden entre un intervalo difuso y un instante preciso, o crea ambigüedades (solapamientos, indeterminación)?

4. **W3C PROV-O.** `prov:generatedAtTime` / `prov:atTime` vs la distinción actividad/entidad. ¿Mi "tiempo de registro como procedencia, no como posición" es consistente con cómo PROV trata el tiempo de generación de una entidad frente al tiempo de una actividad?

5. **Derecho probatorio y procesal (España).** (a) **Prescripción / *dies a quo*** (cómputo del plazo, p. ej. arts. 1969 y 1964 CC): necesita **suelo y techo** de fecha (lo más temprano y lo más tardío posible) sobre fechas inciertas — ¿la candidata da base para derivarlos del EDTF? (b) **Prueba testifical y de declaración**: el valor del "tiempo de enunciación" (cuándo se dijo) frente al "tiempo del hecho" narrado — relevancia de la contemporaneidad y de la distancia temporal entre hecho y declaración. (c) **Prueba por presunciones (art. 386 LEC) y secuencias indiciarias**: requieren un orden temporal robusto entre indicios; ¿qué pasa cuando dos indicios solo tienen fecha difusa y su orden relativo es justamente lo que importa?

6. **Forense audiovisual — timecode SMPTE.** Las entrevistas traen timecode relativo al inicio de la grabación (HH:MM:SS:FF), no reloj de pared. El sistema debe anclarlo a la fecha de la llamada para citar un fragmento. ¿Es correcto tratar el timecode como **localizador interno (pinpoint) dentro de un único acto-entrevista**, sin convertirlo en fechas-hora absolutas por fragmento? ¿O hay un riesgo probatorio en no absolutizar?

---

## 6. Casos límite diseñados para romper la candidata

Atácala con estos (y con otros que se te ocurran):

- **C1 — Declaración performativa.** Una declaración que **es** el hecho jurídico relevante (un reconocimiento de deuda hecho en la propia entrevista; una renuncia verbal). Aquí enunciación = hecho, pero el contenido también es un hecho del mundo con efectos. ¿La regla 2 (enunciación en el padre, hecho narrado en el hijo) lo trata bien, o lo parte indebidamente?

- **C2 — Hecho narrado que SÍ tiene registro propio en otra fuente.** En la entrevista se narra "la oferta se firmó en primavera"; existe además el PDF de la oferta firmada con fecha exacta. ¿El evento reconstruido difuso debe **fusionarse**, **correlacionarse** o **desaparecer** ante el acto preciso? (Recordatorio: entre fuentes no se fusiona, se correlaciona; dentro de fuente se deduplica.) ¿La candidata genera un evento reconstruido fantasma que duplica el acto real?

- **C3 — Documento fechado DESPUÉS del hecho que prueba.** Un certificado emitido hoy que acredita un acto de hace cuatro años. `fecha_documento` ≫ `fecha_hecho`. ¿La candidata coloca el acto en la línea en el lugar correcto (hace cuatro años) sin que la fecha del soporte lo arrastre? ¿Y si el documento es la **única** prueba de la fecha del hecho y esa fecha es a su vez difusa?

- **C4 — Registro de sistema con timestamp preciso pero hecho impreciso.** Un log de CRM dice "actividad registrada el [timestamp exacto]" pero describe una gestión "de la semana pasada". El registro es preciso; el hecho, difuso. ¿Tratar el timestamp del log solo como registro/procedencia pierde información ordenadora útil? ¿Cuándo el timestamp del registro **sí** debería poder anclar el orden (porque es lo más fiable que hay)?

- **C5 — Mensaje reenviado / cita.** Un correo reenviado hoy contiene un mensaje original de hace un año. `modo_recuperacion = reenviada`. ¿Cuál es el "tiempo del hecho" del mensaje original y cuál el del acto de reenvío? ¿Son dos eventos (el original y el reenvío) con tiempos distintos, y la candidata lo soporta?

- **C6 — Fecha del dispositivo manipulable.** Timestamps de mensajería que dependen del reloj del emisor (manipulable). ¿La candidata distingue "fecha afirmada por el dispositivo" de "fecha verificable"? ¿Debería el eje de fiabilidad de fuente intervenir en el tiempo, o eso rompe la separación de capas?

- **C7 — Acto durativo con extremos de distinta precisión.** Una negociación que empieza en fecha precisa y termina en fecha difusa (o al revés). `fecha` + `fecha_fin`: ¿qué pasa cuando uno de los dos extremos es incierto y el otro no, de cara a la ordenación y a la prescripción?

- **C8 — Dos eventos difusos cuyo orden es el hecho controvertido.** El núcleo del litigio es **si A ocurrió antes que B**, y ambos solo tienen fecha aproximada. `orden_relativo` solo funciona **dentro** de una fuente; A y B vienen de fuentes distintas. ¿La candidata deja sin resolver (correctamente, marcándolo como indeterminado) o fuerza un orden espurio?

- **C9 — Husos horarios y normalización.** Correo en un huso, mensajería en otro, entrevista en hora local, registro en UTC. ¿La candidata dice algo sobre normalización de zona horaria, o lo deja como agujero?

---

## 7. Preguntas concretas al revisor

1. ¿La reducción "un ancla (tiempo del hecho) + enunciación solo cuando diverge + registro como procedencia" es **sólida** o pierde algo que la tri-temporalidad clásica conservaría? Da el caso concreto donde se rompe.
2. ¿El campo condicional `tiempo_enunciacion` es la mínima adición correcta, o (a) sobra porque ya está implícito en el par acto-declarativo/evento-reconstruido, o (b) falta más (un eje temporal explícito y obligatorio)?
3. Para **ordenar** difuso junto a preciso en una sola línea: ¿qué operador/semántica recomiendas (Allen, intervalos con suelo/techo, orden parcial explícito con "indeterminado")? ¿Debe la línea de tiempo admitir **orden parcial** en vez de total?
4. Para **prescripción**: ¿basta derivar suelo/techo del EDTF, o hace falta un campo explícito de "fecha más temprana / más tardía posible"?
5. ¿Algún marco que no he citado y que debería gobernar esto?

Sé escueto y quirúrgico: dime qué **rompe**, con qué caso, y qué cambio mínimo lo arregla. Evita validar por validar y evita proponer arquitectura pesada si una regla basta.
