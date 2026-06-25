# Stress-test — F6.D1: El entregable humano unificado (vista multi-fuente)

> **Para:** revisor adversarial (Perplexity).
> **Formato:** handoff anonimizado. No hay datos reales de cliente; actores y nombres son genéricos.
> **Qué pido:** romper la decisión candidata con casos límite, contrastarla con los marcos citados, y señalar dónde la vista engaña, pierde fidelidad probatoria o mezcla capas. Busco fallos, no confirmación.

---

## 1. Contexto mínimo del sistema

Diseño una **cronología unificada de prueba**: fusiona en una sola línea de tiempo todas las fuentes de prueba de un expediente litigioso (correo, mensajería, registros de CRM, entrevistas grabadas/transcritas, documentos, asientos registrales). Trabajo jurídico-forense: separa lo que consta en la prueba de lo que se infiere. El entregable se usa para argumentar y, llegado el caso, para aportar a un juzgado.

Piezas ya cerradas y **congeladas** (se respetan como invariantes, no se discuten):

- **Modelo B (dos capas):** el átomo es un **acto datado anclado a un registro de fuente** (capa **canónica**), nunca un hecho inferido. La interpretación (hechos probados, relato, nexo causal) vive en una **capa derivada** aparte, con un semáforo de soporte 🟢🟡🔴, la clasificación de la carga de la prueba (art. 217 LEC) y las presunciones (art. 386 LEC). Las dos capas no se mezclan.
- **Almacén delgado:** el almacén de eventos NO copia el texto literal (verbatim); lo **apunta** a la fuente (la verdad de contenido vive en la fuente: correo, export de chat, transcripción, ficha de CRM, PDF). Cada acto tiene un puntero al literal + una paráfrasis marcada como tal.
- **Identidad resuelta:** un mismo actor aparece como email, teléfono, nombre de contacto y NIF en fuentes distintas; ya se resuelve a una identidad única.
- **Correlación, no fusión:** dentro de una fuente se deduplica; entre fuentes **no se fusiona, se correlaciona** (pruebas independientes que se enlazan). Un hecho corroborado por N **fuentes independientes** vale más; la circulación de un mismo documento por varios canales prueba algo distinto (difusión), no refuerza el contenido.
- **Vistas = informes regenerables:** todo lo legible (cronologías, dossiers) se **regenera** desde el almacén, lleva cabecera "generado, no editar", y NO es fuente de verdad. La única pieza **curada a mano** por el abogado es el documento de hechos probados (en adelante "documento de hechos").
- **Antecedente (motor de correo, congelado):** ya existe una vista de lectura humana **solo para correo** —un Markdown cronológico, limpio (fecha·hora — asunto, De/Para/CC, adjuntos, cuerpo limpio), con una referencia discreta al pie para citar, y nota de reenvío en lenguaje llano—. Esta vista se quiere **generalizar** a todas las fuentes.

---

## 2. El problema de F6.D1

La vista de correo era homogénea (todo eran correos con De/Para/asunto/cuerpo). Ahora hay que leer en **una sola cronología** actos de fuentes que **no comparten estructura**: un mensaje de chat, una actividad de CRM, un fragmento de entrevista con timecode, un asiento registral, una firma de documento. Hay que decidir el **formato de la vista unificada** sin (a) romper Modelo B (no colar inferencia en la línea de actos), (b) perder fidelidad probatoria (anclaje verificable), ni (c) confundir al lector mezclando "lo que consta" con "lo que se infiere".

---

## 3. DECISIÓN CANDIDATA a romper

**(1) Una vista cronológica única, una entrada por acto, regenerable.** Generaliza la vista de correo. Cada entrada:
- **Esqueleto común (agnóstico de fuente):** fecha (renderizada en humano: exacta / "~marzo 2024" / "≤ firma" / "orden indeterminado" como haz simultáneo) · tipo (categoría·subtipo) · fuente · actores resueltos con su papel · referencia discreta al pie para citar.
- **Bloque específico de fuente (mínimo, donde ayuda a leer):** correo → De/Para/CC/asunto; chat → emisor/chat; entrevista → hablante + timecode; CRM → tipo de actividad; registral → referencia oficial.
- **Cuerpo:** la vista **dereferencia el literal de la fuente al generar** (el almacén sigue delgado; la verdad de contenido vive en la fuente). Muestra el literal anclado (cuerpo limpio del correo, texto del chat, fragmento de transcripción, texto de la actividad), nunca paráfrasis inventada.

**(2) Corroboración multi-fuente visible, en lenguaje llano.** Si un acto está corroborado por actos de otras fuentes, la entrada muestra una referencia cruzada discreta ("consta también en el chat de… del [fecha]"), para que se vea la convergencia de varias fuentes, **sin** exponer la maquinaria de enlaces.

**(3) Dos vistas enlazadas, no fundidas.** La cronología de **actos** (qué ocurrió, capa canónica, para relato e inmediatez probatoria) y el documento de **hechos probados** (qué quedó probado: semáforo + carga de la prueba + presunciones, capa derivada, curado a mano). No se mezclan; la línea de actos alimenta la de hechos por citas. El entregable humano es **ambas, navegables**.

**(4) Dossiers temáticos = la misma vista filtrada por tesis** (p. ej. "titularidad real", "control de hecho", "nexo causal"), tirando de **todas** las fuentes, bajo demanda. El dossier enseña la convergencia multi-fuente de esa tesis.

Todo regenerable, cabecera "no editar"; el documento de hechos es la única pieza curada a mano.

---

## 4. Invariantes que la solución NO puede violar

- (I1) Modelo B: la cronología de actos no muestra inferencias como si fueran hechos constatados; lo inferido vive en la vista de hechos, etiquetado.
- (I2) Anclaje verificable: cada entrada debe permitir a un tercero ir a la fuente y comprobar el literal (pinpoint).
- (I3) Almacén delgado: la vista dereferencia el literal al generar; no se persiste verbatim en el almacén.
- (I4) Correlación ≠ fusión: la convergencia multi-fuente se muestra como corroboración entre actos independientes, nunca como un único acto fundido; circulación ≠ contenido.
- (I5) Regenerable vs curado: la cronología y los dossiers se regeneran; solo el documento de hechos es propiedad humana.

---

## 5. Marcos de referencia que pido contrastar explícitamente

1. **Diseño de pruebas documentales para tribunal / "demonstrative evidence" y narrativa probatoria** (cómo se presenta un timeline a un juez sin que la presentación "argumente" de contrabando). ¿Mi separación cronología-de-actos vs documento-de-hechos es suficiente para no contaminar, o el propio orden/selección de la cronología ya persuade y debe advertirse?
2. **Edición diplomática vs edición de lectura (digital scholarly editing, TEI).** Mostrar el literal "limpio" (cuerpo sin colas citadas, transcripción legible) frente al original íntegro: ¿qué garantías de fidelidad debe dar una vista de lectura para ser citable en juicio? ¿Cuándo "limpiar" para leer cruza a "alterar"?
3. **Principio de mejor evidencia / integridad documental (p. ej. doctrina de "best evidence", y en España la prueba documental y su impugnación).** La vista muestra un literal dereferenciado y "limpiado"; ¿debe coexistir siempre con un acceso al original íntegro y su hash? ¿La vista es "prueba" o solo "índice de lectura"?
4. **Multi-fuente y corroboración (Wigmore / Schum, estructuras de inferencia probatoria).** Mostrar "consta también en…" — ¿ayuda o induce a leer como refuerzo lo que a veces es mera **circulación** del mismo documento (que no corrobora el contenido)? ¿Cómo se distingue visualmente corroboración de contenido vs difusión?
5. **Accesibilidad/usabilidad de timelines densos** (cientos de actos, multi-fuente, fechas difusas). ¿El formato de "una entrada por acto en Markdown lineal" escala, o necesita agrupación/secciones para no volverse ilegible?

---

## 6. Casos límite diseñados para romper la candidata

- **C1 — El literal "limpio" altera el sentido.** Un correo con respuesta intercalada o un mensaje de chat que solo se entiende con el mensaje citado al que responde. Si la vista muestra el cuerpo "limpio" sin la cita, el literal queda ininteligible o cambia de sentido. ¿La vista de lectura debe conservar el contexto citado, y dónde está la línea entre "limpiar para leer" y "descontextualizar"?

- **C2 — Entrevista: el fragmento citado depende de lo anterior.** Un fragmento de transcripción ("eso fue así, sí") es ininteligible sin la pregunta previa. ¿La entrada del acto-entrevista muestra solo el fragmento puntual o la ventana de contexto? ¿Riesgo de tergiversación por recorte?

- **C3 — Corroboración aparente que es circulación.** El mismo PDF viaja por correo y por chat. La vista dice "consta también en el chat de…", y el lector (o el juez) lo lee como doble prueba del contenido, cuando solo prueba que el documento circuló. ¿La candidata induce este error? ¿Cómo se separa visualmente?

- **C4 — Acto con fecha indeterminada en mitad de fechas precisas.** Un acto "~marzo 2024" entre actos de fecha exacta. ¿Dónde se coloca en la cronología lineal? Si se le asigna una posición, se finge precisión; si se muestra como "haz", ¿cómo se lee sin romper la linealidad?

- **C5 — Densidad: cientos de actos.** El expediente real tiene cientos de mensajes + decenas de documentos + entrevistas. Una vista lineal única se vuelve ilegible. ¿El formato aguanta o necesita partición (por año, por tesis, por fuente) que a su vez puede romper la visión cronológica unificada?

- **C6 — Contradicción entre fuentes en la propia vista.** Dos actos dicen cosas incompatibles sobre el mismo punto (una versión del precio vs otra). La cronología de actos los muestra a ambos. ¿Cómo, sin que la vista "resuelva" cuál es verdad (prohibido) pero tampoco confunda al lector? ¿Marca el punto controvertido?

- **C7 — El lector cita la vista en vez del original.** En un escrito se cita "según la cronología, el [fecha] ocurrió X". Pero la cronología es work-product regenerable, no prueba. ¿La referencia al pie debe apuntar al **documento de la fuente** (lo aportable) y no a la vista? ¿Cómo se evita que se cite el índice como si fuera la prueba?

- **C8 — Dossier temático que sesga por omisión.** Un dossier "control de hecho" filtra solo lo favorable a esa tesis y omite actos neutros o contrarios. ¿El dossier, al filtrar, induce sesgo de confirmación? ¿Debe mostrar también lo que la contradice (coherente con la disciplina anti-sesgo del sistema)?

- **C9 — Acto sin literal legible (documental escaneado sin OCR, audio sin transcribir).** La vista quiere dereferenciar el literal pero no hay texto. ¿Qué muestra — "pendiente de transcripción", la descripción, nada? ¿Sin romper el anclaje?

---

## 7. Preguntas concretas al revisor

1. ¿La separación cronología-de-actos vs documento-de-hechos basta para no "argumentar de contrabando", o la mera selección/orden de la cronología ya persuade y exige una advertencia/encuadre?
2. ¿La vista de lectura con literal "limpio" es citable con garantías, o debe coexistir SIEMPRE con acceso al original íntegro + hash, y declararse "índice de lectura, no prueba"?
3. ¿Cómo distinguir **visualmente** corroboración de contenido (refuerza) vs circulación (no refuerza), para no inducir doble cómputo al lector/juez?
4. ¿El formato lineal único aguanta cientos de actos, o hay que partir — y qué partición no rompe la visión cronológica unificada?
5. ¿Los dossiers temáticos deben mostrar también lo neutro/contrario a la tesis para no sesgar (anti sesgo de confirmación), o se asume que el dossier es alegato de parte y se advierte?
6. ¿Algún marco/patrón que no he citado y que debería gobernar esto?

Sé escueto y quirúrgico: qué **rompe**, con qué caso, y qué cambio mínimo lo arregla. Evita validar por validar y evita arquitectura pesada si una regla basta.
