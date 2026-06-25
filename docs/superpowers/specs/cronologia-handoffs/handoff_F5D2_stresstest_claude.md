# Stress-test — F5.D2: Encaje con las capas de fichero, staging y orden de construcción

> **Para:** revisor adversarial (Perplexity).
> **Formato:** handoff anonimizado. No hay datos reales de cliente; actores y nombres son genéricos.
> **Qué pido:** romper la decisión candidata con casos límite, contrastarla con los marcos citados, y señalar dónde el encaje con las capas inferiores se duplica, se contamina o rompe la custodia. Busco fallos, no confirmación.

---

## 1. Contexto mínimo del sistema

Diseño una **cronología unificada de prueba**: fusiona en una sola línea de tiempo todas las fuentes de prueba de un expediente litigioso (correo, mensajería, registros de CRM, entrevistas grabadas/transcritas, documentos, asientos registrales). Trabajo jurídico-forense: separa lo que consta en la prueba de lo que se infiere.

Capas de fichero **ya existentes** en cada expediente (no se discuten; se respetan):

- **Intake / `00_Input`** — los ficheros crudos tal como entraron, **inmutables**. Al ingresar cada fichero se registra su **hash de contenido** y un **log de eventos** (custodia: quién subió qué y cuándo). Esta custodia ya existe; la cronología la **referencia**, no la rehace. Hay una subcarpeta `90_Notas personales` que es **zona reservada del abogado**: ningún módulo automático la lee ni la escribe.
- **"Organizar sala de lectura"** — una capa a **nivel fichero** que lee `00_Input`, clasifica cada fichero por categorías, lo **renombra canónicamente** y lo **copia** a `01_Procesado/Sala lectura` (estructura plana), generando índices para lectura humana (un índice documental con clasificación y fecha extraída, una cronología a nivel fichero, un manifiesto). Es una **reorganización derivada y regenerable** del crudo, pensada para que un humano lea el expediente.
- **Motor de atomización de correo (CONGELADO)** — ya procesó los correos: emite su salida (un fichero por mensaje con metadatos, un índice de máquina, un libro de IDs) en `01_Procesado/Emails/`, anclando su propia custodia al crudo. No se toca.

Decisiones de fases previas (cerradas, se respetan como invariantes):

- **Arquitectura de ingesta (decisión inmediatamente anterior, F5.D1):** tres capas — **atomizador** (bytes→átomos con clave natural estable, específico de fuente) · **adaptador** (átomo→ficha de acto en esquema común, normaliza fecha, rellena procedencia con hash de intake, emite tokens de actor crudos sin resolver) · **núcleo agnóstico** (asigna el id del acto, resuelve identidad, deduplica, correlaciona, ordena en el tiempo, enlaza, genera vistas). Entre adaptador y núcleo hay una **capa de staging** (actos normalizados sin resolver). El atomizador/adaptador no decide identidad ni correlación.
- **Modelo B:** el átomo es un acto anclado a un registro de fuente, nunca un hecho inferido.
- **Custodia:** el almacén de eventos es **work-product**, no prueba; la prueba son las fuentes apuntadas. El pinpoint debe ser **verificable por un tercero**.
- **Idempotencia:** libro `huella→id` congelado; re-ejecutar no renumera; las decisiones humanas (correlación curada) son **sticky** y no se pisan al re-ejecutar.
- **Ubicación prevista de la cronología:** `01_Procesado/Cronologia/`, en paralelo a `01_Procesado/Emails/`.
- **Entorno:** el build corre en local (acceso directo a los ficheros del expediente); el prototipado en nube no monta el almacenamiento del expediente.

---

## 2. El problema de F5.D2

Quedan tres piezas de encaje:
1. **¿De dónde lee el atomizador** — del crudo `00_Input`, o de las copias renombradas de la sala de lectura? ¿Consume los índices de la sala de lectura o los ignora? (Riesgo: duplicar la sala de lectura, o anclar la custodia a una copia derivada en vez del crudo.)
2. **Dónde y en qué formato viven el staging y el almacén enriquecido.**
3. **Orden de construcción incremental** sin recalcular ni pisar lo ya curado.

---

## 3. DECISIÓN CANDIDATA a romper

**(1) Encaje con fichero — anclaje al crudo; la sala de lectura como PISTA, nunca como fuente.**
- El atomizador ancla **custodia y pinpoint siempre al crudo de `00_Input` + su hash de intake** (fuente inmutable), nunca a las copias renombradas de la sala de lectura (derivadas, regenerables).
- Excepción coherente: para "correo", la fuente autoritativa es la salida del **motor congelado**, que ya ancló su custodia al crudo.
- El atomizador **puede consumir el índice documental de la sala de lectura como PISTA** (clasificación, fecha ya extraída, agrupación de documentos compuestos) para arrancar más fino, pero **el literal y la custodia apuntan al crudo**, jamás a la copia.
- Deslinde de niveles: **sala de lectura = nivel fichero** (qué ficheros hay, para lectura humana); **cronología = nivel acto** (qué ocurrió, anclado al crudo). Sus dos "cronologías" (la de fichero y la de actos) **coexisten** sin pisarse — distinta granularidad y propósito.
- Invariante heredado: **ningún atomizador toca `90_Notas personales`.**

**(2) Staging y almacén — bajo `01_Procesado/Cronologia/`.**
- **Staging** (salida del adaptador, actos normalizados sin resolver): `01_Procesado/Cronologia/_staging/<fuente>.jsonl`, regenerable, un acto por línea, cabecera "generado, no editar".
- El **núcleo** enriquece desde el staging y produce: almacén canónico de eventos + índice de máquina (`eventos.jsonl`) + libro persistente (`_registro_cronologia.json`: sticky, mapa `huella→id`) en la raíz de `Cronologia/`. Las vistas (cronología de actos, dossiers) cuelgan de ahí, regenerables.
- Mismo patrón que el motor de correo (índice de máquina regenerable + libro persistente).

**(3) Orden de construcción — incremental, dirigido por la prueba.**
- Correo (congelado, listo) + **mensajería primero** (es la espina temporal del caso), con **índice de artefactos por hash desde el día 1** (para casar el documento que viaja por varios canales).
- Luego CRM, entrevistas y documental/registral.
- Cada fuente nueva **regenera su staging y añade candidatos a la cola** sin recalcular ni pisar las decisiones humanas ya curadas (gobernanza sticky).

---

## 4. Invariantes que la solución NO puede violar

- (I1) Custodia anclada al crudo inmutable; el pinpoint debe ser verificable por un tercero; no anclar a copias derivadas.
- (I2) No duplicar la sala de lectura (capa de fichero) ni el motor de correo (congelado).
- (I3) `90_Notas personales` nunca se lee ni se escribe.
- (I4) Idempotencia: re-ejecutar no renumera ni pisa decisiones humanas sticky.
- (I5) Las salidas regenerables (staging, índices, vistas) se distinguen claramente de las piezas persistentes (libro de IDs, decisiones humanas) y del crudo.

---

## 5. Marcos de referencia que pido contrastar explícitamente

1. **Cadena de custodia y prueba electrónica forense** (ISO/IEC 27037 — identificación, recogida, adquisición, preservación; principios de integridad y verificabilidad por tercero). ¿Anclar el pinpoint al crudo + hash de intake, y consumir la sala de lectura solo como pista, es correcto desde la custodia? ¿Hay riesgo de que "consumir la clasificación de una capa derivada" contamine la cadena, aunque el literal apunte al crudo?
2. **Data lakehouse / arquitectura por zonas (raw / staging / curated)** y **medallion (bronze/silver/gold)**. ¿Mi reparto crudo→staging→almacén enriquecido→vistas encaja en estas zonas? ¿El staging por fuente (`_staging/<fuente>.jsonl`) es el sitio correcto, o debería ser una zona única multi-fuente?
3. **Idempotencia y reprocesado en pipelines incrementales** (full refresh vs incremental; *late-arriving data*; *backfill*). Cuando una fuente nueva entra tarde y aporta actos **anteriores** a los ya cargados, ¿el orden de construcción incremental aguanta sin reordenar mal ni romper enlaces curados?
4. **Separación derivado/autoritativo y "single source of truth".** La sala de lectura y la cronología derivan ambas del mismo crudo. ¿Coexistir dos "cronologías" (fichero vs acto) crea ambigüedad sobre cuál es la buena, o el deslinde por nivel es suficiente?
5. **Reproducibilidad y datos de origen inmutables** (immutable raw zone). ¿La política "el crudo nunca se toca, todo lo demás se regenera" es completa, o falta tratar el caso del crudo que cambia (un fichero re-subido, una versión corregida)?

---

## 6. Casos límite diseñados para romper la candidata

- **C1 — La pista de la sala de lectura es errónea.** El índice documental clasificó mal un fichero o le asignó una fecha equivocada. Si el atomizador "arranca más fino" con esa pista, hereda el error. ¿La pista contamina el acto, aunque el literal apunte al crudo? ¿Qué prevalece y cómo se detecta la discrepancia?

- **C2 — Documento compuesto.** La sala de lectura agrupó en una subcarpeta fechada un documento de varias piezas (p. ej. un burofax + su acuse + su certificado). ¿El atomizador documental crea uno o varios actos? ¿Usa la agrupación de la sala de lectura (pista) o la ignora y va al crudo? Si la sala de lectura agrupó mal, ¿se propaga?

- **C3 — El crudo cambia.** Un fichero de `00_Input` se re-sube corregido (misma cosa, distinto hash), o se añade una versión mejor de un export. La política dice "crudo inmutable", pero la realidad lo contradice. ¿El libro `huella→id` lo trata como artefacto nuevo, como upgrade, o rompe? ¿Y las citas ya emitidas?

- **C4 — Llegada tardía que reordena.** Se construye correo + mensajería; meses después entra el CRM con actividades **anteriores** a todo lo cargado, que se intercalan en mitad de la línea. ¿El orden incremental las coloca bien sin recomputar el semáforo de hechos ya curados? ¿Reabre enlaces sticky?

- **C5 — La sala de lectura aún no se ha corrido.** Un expediente donde el intake existe pero nadie organizó la sala de lectura todavía. ¿La cronología puede construirse solo desde `00_Input` crudo sin la pista? ¿La pista es opcional de verdad, o hay dependencia oculta?

- **C6 — Solapamiento de la cronología de fichero y la de actos.** El usuario ve dos ficheros llamados parecido (`CRONOLOGIA.md` de la sala de lectura a nivel fichero y la cronología de actos). ¿Riesgo real de que cite el equivocado en un escrito? ¿El deslinde por nivel basta o hay que renombrar/separar?

- **C7 — Mismo crudo, dos fuentes lo reclaman.** Un PDF está tanto en `00_Input/03_Email` (adjunto exportado) como copiado por la sala de lectura a `01_Procesado/Sala lectura`. ¿El atomizador documental lo toma como fuente "documental" y además aparece como adjunto del correo? ¿Doble acto/artefacto, o el índice por hash lo unifica?

- **C8 — Staging por fuente vs orden global.** El staging está partido por fuente (`_staging/correo.jsonl`, `_staging/whatsapp.jsonl`). El orden temporal es global. ¿Partir el staging por fuente complica la correlación inter-fuente y el ordenado global, o es indiferente porque el núcleo los une igualmente?

- **C9 — `90_Notas personales` contiene prueba.** El abogado, por error, dejó en `90_Notas personales` un documento que es prueba real. La regla dice "no se lee". ¿Se pierde prueba? ¿La regla debe tener una válvula (avisar "hay algo aquí, muévelo") sin leer el contenido?

---

## 7. Preguntas concretas al revisor

1. ¿Anclar la custodia al crudo y usar la sala de lectura **solo como pista** es forense-correcto, o consumir su clasificación ya contamina la cadena? ¿Regla mínima para blindar esto?
2. ¿El staging debe ser **por fuente** o **zona única multi-fuente**? ¿Cuál sirve mejor a la correlación y al ordenado global?
3. ¿La política "crudo inmutable, lo demás regenerable" necesita una regla explícita para el **crudo que cambia/re-sube** (C3), o se delega al libro `huella→id`?
4. ¿El orden incremental aguanta **datos de llegada tardía** que se intercalan (C4) sin romper idempotencia ni pisar decisiones humanas?
5. ¿La dependencia de la sala de lectura es realmente **opcional** (C5), o estoy creando un acoplamiento oculto?
6. ¿`90_Notas personales` necesita una **válvula de aviso sin lectura** (C9), o la prohibición absoluta es lo correcto?
7. ¿Algún marco/patrón que no he citado y que debería gobernar esto?

Sé escueto y quirúrgico: qué **rompe**, con qué caso, y qué cambio mínimo lo arregla. Evita validar por validar y evita arquitectura pesada si una regla basta.
