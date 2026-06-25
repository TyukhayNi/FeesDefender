# Stress-test — F5.D1: Contrato del adaptador de fuente y frontera adaptador↔núcleo

> **Para:** revisor adversarial (Perplexity).
> **Formato:** handoff anonimizado. No hay datos reales de cliente; actores y cifras son genéricos.
> **Qué pido:** romper la decisión candidata con casos límite, contrastarla con los marcos de referencia citados, y señalar dónde la frontera entre capas se filtra, se duplica o no escala. Busco fallos, no confirmación.

---

## 1. Contexto mínimo del sistema

Diseño una **cronología unificada de prueba**: fusiona en una sola línea de tiempo todas las fuentes de prueba de un expediente litigioso (correo, mensajería instantánea, registros de CRM, entrevistas grabadas/transcritas, documentos, asientos registrales). Es trabajo jurídico-forense: separa **lo que consta en la prueba** de **lo que se infiere**. La herramienta debe ser **replicable a cualquier expediente** del despacho.

Piezas ya cerradas y **congeladas** (se respetan como invariantes, no se discuten):

- **Modelo B:** el átomo de la línea es un **acto datado anclado a un registro de fuente** (un mensaje enviado, una oferta firmada, un asiento publicado), nunca un hecho del mundo inferido. La interpretación vive en una **capa derivada** aparte (hechos probados, con grafo de apoyos y semáforo 🟢🟡🔴).
- **Ficha del acto (esquema común ya definido):** id estable opaco; `procedencia` (fuente · localizador interno · clave natural de contenido · referencia de hash de intake); `cuando` (fecha en EDTF/ISO 8601-2, `fecha_fin`, `orden_relativo`); `tipo`; `quien` (actor resuelto + papel en el acto); `que_dice` (puntero al literal, no se copia, + paráfrasis); `alcance_probatorio`; `anclaje` (A–E); `modo_recuperacion`; `estado_registro`.
- **Identidad (capa propia ya diseñada):** un registro de entidades por expediente (`identidades.yaml`) resuelve que un mismo actor aparece como email, teléfono, nombre de contacto y NIF en fuentes distintas. La identidad es **transversal** (el teléfono de una tarjeta de contacto es el puente entre la mensajería y el resto) y **reutilizable** entre expedientes; los roles y calificaciones son específicos del caso.
- **IDs:** dos regímenes — congelados por contenido (actos y artefactos: id derivado de la huella/clave natural; re-ejecutar no renumera) y asignados-persistidos (actores, enlaces, hechos derivados). Libro `huella→id` persistente. El id del acto en la cronología (`EVT-…`) es distinto del id que use el atomizador de una fuente (p. ej. `MSG-…` del correo): se enlazan por pinpoint.
- **Correlación entre fuentes (fase previa cerrada):** dentro de una fuente se **deduplica** (copias idénticas colapsan); entre fuentes **no se fusiona, se correlaciona** (pruebas independientes que se enlazan). El enrutamiento (auto/cola/no-propuesto), el cómputo del semáforo y el tratamiento de contradicciones ya están diseñados y son del **núcleo**.
- **Tiempo (fase previa cerrada):** orden parcial; cada acto se proyecta a `[suelo, techo]`; relaciones derivadas antes/después/contiene/contenido_en/indeterminado; todo esto es del **núcleo**.
- **El motor de correo está CONGELADO.** Ya atomiza los correos del expediente: emite un fichero por mensaje (con metadatos en cabecera), un índice de máquina (un registro por mensaje) y un libro persistente de IDs. No se modifica.
- **Existe una capa inferior, "organizar sala de lectura", a NIVEL FICHERO** (clasifica y nombra los ficheros del expediente). La cronología vive **por encima** (nivel acto), no la duplica.
- **Existe un intake con custodia:** al entrar cada fichero al expediente se registra su hash (huella) y un log. Esa custodia ya existe; la cronología la **referencia**, no la rehace.
- **Restricción de entorno:** el build corre en local (acceso directo a los ficheros del expediente); el prototipado en nube **no monta** el almacenamiento del expediente.

---

## 2. El problema de F5.D1

Cada fuente llega en un formato radicalmente distinto y con identificadores distintos. Hay que decidir **la arquitectura de ingesta**: cómo cada fuente cruda se convierte en actos del esquema común, **sin duplicar** el motor de correo ni la capa de sala de lectura, de modo que **añadir una fuente nueva sea barato** y que el criterio jurídico sensible esté concentrado, no disperso. El núcleo de la decisión es **dónde poner la frontera** entre lo específico de cada fuente y lo común.

---

## 3. DECISIÓN CANDIDATA a romper

**Tres capas estrictas, con una frontera tajante:**

**(1) ATOMIZADOR — específico de fuente.** Dueño de los bytes y de las rarezas del formato. Convierte el crudo en **átomos con ID estable congelado por contenido** (clave natural propia de la fuente). El motor de correo congelado **ES** el atomizador de la fuente "correo". Mensajería, CRM, entrevistas y documental necesitan cada uno el suyo (un export de chat crudo no tiene IDs estables → hay que dárselos). Vive por encima de la sala de lectura (nivel fichero), por debajo del esquema común.

**(2) ADAPTADOR/PROYECTOR — específico de fuente, pero delgado, con librería compartida.** Mapea cada átomo a una **ficha del acto** del esquema común: normaliza la fecha a EDTF, rellena `procedencia` (incluida la referencia de hash de intake), fija `alcance_probatorio`/`anclaje`/`modo_recuperacion`, apunta al literal (no lo copia) y emite el **token de actor crudo** (email, teléfono, nombre de contacto, NIF) **sin resolverlo**. Para "correo", el adaptador es un **lector de solo lectura** sobre la salida del motor congelado; no modifica el motor.

**(3) NÚCLEO AGNÓSTICO — todo lo demás, idéntico en toda fuente.** Asigna **EVT-id** (mapeando la clave natural del átomo → EVT-id congelado; el id de la fuente y el EVT-id se enlazan por pinpoint); **resuelve la identidad** contra el registro de entidades (porque es transversal); deduplica intra-fuente; correlaciona inter-fuente; proyecta el tiempo y ordena; construye enlaces y capa derivada; mantiene el libro persistente y genera las vistas.

**Invariante rector de la frontera:** el adaptador **nunca** asigna EVT-ids, **nunca** crea enlaces, **nunca** decide correlación, **nunca** resuelve identidad. Solo produce fichas de acto normalizadas con su clave natural y su token de actor crudo. Ventajas buscadas: añadir fuente = escribir atomizador + adaptador sin tocar el núcleo; el criterio sensible (sobre todo la identidad) está concentrado; re-ejecutar no renumera (el núcleo re-engancha por clave natural).

---

## 4. Invariantes que la solución NO puede violar

- (I1) Modelo B: el adaptador no infiere hechos; solo proyecta actos anclados.
- (I2) No duplicar el motor de correo (congelado) ni la sala de lectura (nivel fichero).
- (I3) Identidad resuelta en un único sitio (el núcleo), nunca en cada adaptador.
- (I4) Idempotencia: re-ejecutar un atomizador/adaptador no renumera ni rompe citas estables ya emitidas en escritos.
- (I5) Toda ficha trazable a su fuente con pinpoint verificable por un tercero; la custodia del intake se referencia, no se rehace.
- (I6) Coste marginal bajo de añadir una fuente: el núcleo no cambia al sumar fuentes.

---

## 5. Marcos de referencia que pido contrastar explícitamente

1. **Patrones de integración de datos — Ports & Adapters / Hexagonal Architecture, Anti-Corruption Layer (DDD).** Mi capa (2) es esencialmente un ACL por fuente. ¿La frontera está donde debe? ¿Hay lógica que estoy dejando en el adaptador y que pertenece al núcleo, o al revés?
2. **ETL / ELT y la disciplina Extract–Transform–Load.** ¿Mi reparto atomizador(extract)/adaptador(transform)/núcleo(load+enrich) es sano, o estoy metiendo "transform" pesado (resolución de identidad, dedup) en el sitio equivocado? ¿Conviene un **staging** intermedio explícito (actos normalizados sin resolver) antes del enriquecimiento?
3. **Schema-on-read vs schema-on-write / formato canónico de evento (event normalization, p. ej. patrones SIEM/observabilidad: "common event format").** ¿Proyectar al esquema común en el adaptador (schema-on-write) es correcto, o debería conservar el átomo nativo y proyectar tarde?
4. **Entity resolution / record linkage en pipelines.** La identidad se resuelve en el núcleo a partir de tokens crudos emitidos por el adaptador. ¿Es correcto que el adaptador NO resuelva nada, o hay normalización mínima de identificadores (e-mail lowercasing, E.164 para teléfonos) que sí debe hacer el adaptador para que el núcleo no reciba basura?
5. **Idempotencia y claves naturales vs claves sustitutas (surrogate keys), CDC (change data capture).** Mi id congelado por contenido (clave natural → EVT-id) frente a re-ejecuciones y a **upgrades** (un átomo de baja calidad que reaparece mejor). ¿El esquema aguanta cambios de la fuente sin renumerar ni perder enlaces?
6. **Procedencia / W3C PROV en pipelines de transformación.** ¿La cadena atomizador→adaptador→núcleo conserva la procedencia de forma auditable en cada salto (quién derivó qué de qué)?

---

## 6. Casos límite diseñados para romper la candidata

- **C1 — Una fuente cuyo "átomo" no es obvio.** Una ficha de CRM es un registro con muchos campos y un log de actividades dentro. ¿Es **un** acto o **N**? ¿Quién decide la granularidad — atomizador o adaptador? Si lo decide el atomizador, ¿no estoy metiendo criterio de fondo en la capa que dije que no decide nada?

- **C2 — El mismo documento llega por dos fuentes (correo adjunto y export de mensajería).** El artefacto es idéntico (misma huella) pero lo emiten dos atomizadores distintos. ¿Cómo se reconcilia la identidad del artefacto si cada adaptador lo proyecta por separado y el núcleo no debe fusionarlo entre fuentes? ¿La "identidad de artefacto por hash" cruza la frontera correctamente?

- **C3 — Token de actor ambiguo en origen.** Una tarjeta de contacto de mensajería titula a una persona pero lleva el teléfono y el email de **otra** (caso real: una ficha rotulada con un nombre pero operada por un apoderado distinto). El adaptador emite "el token tal cual": ¿qué token emite — el rótulo o el teléfono? Si emite el rótulo, el núcleo resuelve mal; si "corrige", está resolviendo identidad (prohibido en el adaptador). ¿Dónde se rompe?

- **C4 — La fuente congelada (motor de correo) no expone algo que el esquema común exige.** El adaptador-lector necesita un campo que el motor congelado no emite (p. ej. `alcance_probatorio`, o un nivel de formalización). ¿El adaptador lo **infiere** (rozando Modelo B), lo deja vacío, o esto obliga a reabrir el motor congelado pese a la prohibición?

- **C5 — Re-ejecución tras mejorar un atomizador.** Se mejora el atomizador de mensajería y ahora parte mejor los mensajes (antes fundía dos en uno). Las claves naturales cambian para algunos átomos. ¿Qué pasa con los EVT-ids ya citados en un escrito presentado? ¿El libro `huella→id` aguanta o se rompen citas?

- **C6 — Dos atomizadores asignan la misma clave natural por colisión.** Clave natural de correo = Message-ID; de mensajería = fecha+autor+hash. ¿Pueden colisionar entre fuentes y hacer que el núcleo funda dos actos de fuentes distintas (violando "entre fuentes no se fusiona")? ¿El espacio de claves naturales está bien aislado por fuente?

- **C7 — Documental sin atomizador propio.** Un PDF suelto (una nota simple, un certificado) que prueba un acto datado. ¿Quién lo convierte en acto — hay un "atomizador documental", o el documento solo se engancha como prueba a un acto creado por otra fuente? ¿Y si es la **única** fuente de ese acto?

- **C8 — Orden de construcción incremental.** Se construye correo + mensajería primero; CRM y entrevistas después. ¿El núcleo, ya poblado y con enlaces curados por el letrado, absorbe una fuente nueva sin recalcular/pisar decisiones humanas previas (las decisiones sticky de correlación)?

- **C9 — Conflicto de fecha entre la capa de custodia (intake) y el contenido.** El hash de intake tiene su propia fecha de entrada; el acto tiene su fecha del hecho. Ya está claro que la fecha de registro ≠ fecha del hecho, pero ¿el adaptador mezcla por error la fecha de intake como fecha del acto?

---

## 7. Preguntas concretas al revisor

1. ¿La frontera adaptador↔núcleo está en el sitio correcto, o hay **fugas** (granularidad, normalización de identificadores, identidad de artefacto) que obligan a mover la línea?
2. ¿Debe existir una **capa de staging explícita** (actos normalizados sin resolver, antes del enriquecimiento del núcleo), o es sobreingeniería?
3. ¿Qué **normalización mínima de identificadores** debe hacer el adaptador (sin resolver identidad) para no ensuciar el record linkage del núcleo?
4. ¿Cómo debe tratarse la **granularidad** (un acto vs N) — es decisión del atomizador, del adaptador, o config declarativa por fuente? ¿Dónde queda más limpia sin meter criterio de fondo en capas "tontas"?
5. El caso del **documental sin atomizador** (C7): ¿merece atomizador propio o es solo "prueba que se engancha"? Da la regla.
6. ¿La candidata sobrevive a la **re-ejecución con upgrade** (C5) sin romper citas estables? ¿Qué regla mínima lo garantiza?
7. ¿Algún marco/patrón que no he citado y que debería gobernar esto?

Sé escueto y quirúrgico: qué **rompe**, con qué caso, y qué cambio mínimo lo arregla. Evita validar por validar y evita arquitectura pesada si una regla basta.
