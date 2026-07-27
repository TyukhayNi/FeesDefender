# Diseño — Bundle por hilo de correo en la sala de lectura (Slice 1)

> **Historial de este spec.** Nació el 2026-07-23 como "consumo de emails atomizados en la sala de
> lectura": la sala leería `01_Procesado/Emails/` (salida de `core/email_atomize`) en vez de releer
> el `.eml` crudo. Dos revisiones adversariales independientes —Codex
> ([`…-adversarial-review.md`](2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md)) y un
> workflow de 6 lentes con verificación por escépticos— convergieron en los mismos bloqueantes, y la
> adjudicación (Claude, 2026-07-27) concluyó que el spec **empaquetaba tres proyectos** y que su
> mecanismo central de idempotencia partía de una premisa falsa. **Re-tajado el 2026-07-27 con
> aprobación de Nikolai:** este documento queda reducido al **Slice 1**, que entrega el beneficio más
> visible sin ninguno de los bloqueantes. Los Slices 2 y 3 salen a backlog con disparador explícito
> (`MEJORAS #86`, `#87`). La tabla de adjudicación completa vive en la revisión hermana.

---

## 1. Objetivo y alcance

**Objetivo.** Que la correspondencia de un caso ocupe en la sala de lectura **una entrada por hilo**
en vez de una por mensaje. Hoy cada `.eml` se copia como documento propio y ocupa su propia línea de
índice: un caso con ~277 correos (magnitud real de W-02VND1) produce ~277 ficheros sueltos y ~277
líneas — la sala deja de ser legible, que es exactamente su propósito.

**Este spec NO hace** (y es deliberado, no un olvido):

- **No consume `01_Procesado/Emails/`.** Nada de `corpus.jsonl`, `MSG-id`, Capa B ni adjuntos
  deduplicados. → `MEJORAS #86` (Slice 2).
- **No cambia QUÉ fichero se copia.** Sigue copiándose el `.eml` con sus adjuntos MIME, como hoy. El
  criterio "email → MD legible, el `.eml` es custodia" que Nikolai cerró el 2026-07-19
  (`MEJORAS #75`) llega con el Slice 2, no aquí.
- **No toca `core/email_atomize` ni `core/anon`** (módulo congelado por `CLAUDE.md`).
- **No toca el OCR de adjuntos** ni el motor de extracción. → `MEJORAS #87` (Slice 3).
- **No introduce ningún motor de threading nuevo.** → `MEJORAS #88`.

Todo el cambio vive **dentro del paquete `.skill`** de `organizar-sala-lectura`. Cero instalación
nueva para el equipo: los scripts de la skill son **stdlib puro y self-contained** (corren en el
sandbox de Cowork sin `core/`, como declara el propio docstring de `scripts/preclasificar.py`), así
que Paola, Ana y Sergio solo reimportan el `.skill` como ya hacen.

## 2. Los tres cambios

### 2.1 Forma de copia: un bundle por grupo de hilo

**Corrección de premisa (2026-07-27, antes de escribir el plan).** La primera versión de este spec
decía "se reutiliza `agrupar_por_hilo` tal cual". **Es falso y no habría entregado el beneficio:** esa
función no agrupa hilos, agrupa **colisiones de nombre del mismo día y mismo asunto**. `email_export`
nombra cada mensaje `AAAA-MM-DD_descripcion.eml` con **su propia fecha**
([`email_export.py:119-129`](../../../core/email_export.py:119)) y `_ruta_unica` solo añade `_2`/`_3`
cuando el nombre completo choca; el propio test vigente se llama
`test_agrupar_por_hilo_junta_variantes_del_mismo_dia_y_asunto`. Un hilo que cruza días produce stems
distintos y **no se agrupaba**: 277 correos habrían colapsado a ~240, no a ~40.

**Lo que sí funciona, y es más barato que leer cabeceras RFC:** `_slug_descripcion` **ya elimina los
prefijos `Re:`/`RV:`/`Fwd:`** antes de construir el nombre
([`email_export.py:90-103`](../../../core/email_export.py:90)), así que **todos los mensajes de un hilo
comparten la misma `descripcion`** y solo difieren en el prefijo de fecha. Por tanto la clave de hilo
pasa a ser **la descripción, ignorando la fecha** — sigue siendo solo nombres de fichero, cero
lecturas de contenido, idéntico en los tres modos de acceso. `MEJORAS #88` (threading por cabeceras
RFC) se conserva como el refinamiento fino, no como prerrequisito.

`agrupar_por_hilo` **cambia de clave** (descripción en vez de stem con fecha), conservando por
construcción la protección del ítem 11 del backlog: un `_N` final solo se recorta si la descripción
sin ese sufijo existe de verdad en el conjunto, así que `oferta_vivienda_1_990_000` no se fusiona con
un `oferta_vivienda_1_990` inexistente. Con la clave nueva, lo que cambia además es **dónde aterriza
cada fichero**:

- **Grupo con ≥2 mensajes** → subcarpeta fechada `AAAA-MM-DD_descripcion/`; **principal** = el `.eml`
  más antiguo; **anexos** = los demás mensajes y los adjuntos MIME de todos ellos.
- **Grupo de 1 mensaje sin adjuntos** → **plano, sin subcarpeta** (evita cientos de carpetas con un
  solo fichero dentro).
- **Grupo de 1 mensaje con adjuntos** → bundle, exactamente como hoy.

Se respetan sin cambios las convenciones vigentes de documento compuesto: el `AAAA-MM-DD` de cada
anexo es **su propia fecha** (misma regla que los anexos de WhatsApp), y el `parent_id` de un anexo
es **el nombre pelado de la carpeta del bundle**.

### 2.2 `INDICE.md` colapsa bundles; `CRONOLOGIA.md` no cambia

Hoy `construir_indice` y `construir_cronologia` recorren **todas** las filas del manifiesto y emiten
una línea por cada una, sin mirar `parent_id`
([`indices_desde_manifiesto.py:43-75`](../../../.claude/skills/organizar-sala-lectura/scripts/indices_desde_manifiesto.py:43)).
Es decir: agrupar en carpetas, por sí solo, **no reduciría el índice**. Por eso el Slice 1 incluye:

- **`INDICE.md`:** una línea por documento **principal** (filas sin `parent_id`), con sufijo
  `(+N anexos)`. Es la vista "qué documentos tenemos, por categoría" — un hilo es un documento.
- **`CRONOLOGIA.md`:** **sin cambios**, sigue listando todas las filas. Es una línea de tiempo, y un
  anexo con fecha propia es un evento datado; la regla de "fecha propia del anexo" existe
  precisamente para eso. Colapsarlo ahí destruiría información temporal.

Efecto colateral **buscado**: los bundles ya existentes de WhatsApp y CRM también dejan de inflar el
índice. La información no se pierde — los anexos siguen en `_MANIFIESTO.md`, en `CRONOLOGIA.md` y en
disco.

### 2.3 El nombre del bundle se fija en la primera corrida y no se renombra

`descripcion` = slug del asunto del mensaje más antiguo del grupo (≤50 caracteres, minúsculas,
guiones bajos, revisada **sin PII** — regla vigente de la skill). Si en una re-corrida llega un
mensaje **anterior** al principal, entra como **anexo con su fecha propia** y la carpeta **no se
renombra**: renombrar pisaría documentos ya copiados y rompería la doctrina "solo añade, nunca
borra ni sobrescribe". `CRONOLOGIA.md`, que no colapsa, lo sitúa en su posición temporal correcta.

## 3. Idempotencia

> ⚠️ **Corrección (2026-07-27, tras la revisión final de la rama).** Este apartado afirmaba
> "sin algoritmo nuevo: basta el `sha256` por `.eml`". **Era falso para bundles.** El skip por
> `sha256` sí basta para decidir *si* un fichero se copia, pero el **nombre de la carpeta** y el
> **nombre de cada anexo** son estado DERIVADO del grupo, y el grupo cambia entre corridas. De esa
> confusión salieron tres fallos reales que la revisión encontró en el código ya escrito: un mensaje
> podía desaparecer sin error (exclusión del principal por valor con basenames repetidos), un mensaje
> nuevo podía llevarse el `_anexo_1` de otro ya copiado y sobrescribirlo (índice posicional), y un
> mensaje nuevo podía recibir la ruta del principal ya copiado (`carpeta_existente` sin candidato).
> El remedio adoptado **no es un contrato de re-corrida más complejo, sino suprimir el estado
> derivado**: los nombres pasan a ser función pura del fichero de origen (decisión de Nikolai,
> 2026-07-27). Lo que sigue describe el diseño ya corregido.

**El skip incremental no cambia:** sigue siendo por `sha256` del `.eml` de origen, y cada `.eml`
conserva su fila propia en el `_MANIFIESTO.md`. No hace falta ledger, ni conjuntos, ni columna nueva.

**Lo que sí hizo falta: que ningún nombre dependa del grupo.**

- El nombre de un **anexo-mensaje** es `<fecha_propia>_<descripcion>_<discriminante>.eml`, donde el
  discriminante deriva **solo de su propio nombre de origen** (hash corto). Añadir un mensaje no
  renumera ni pisa nada. El `orden` sigue siendo posicional, pero es metadato del manifiesto, no un
  nombre de fichero.
- El **nombre de la carpeta** se fija en la primera corrida y se pasa como `carpeta_existente`; si
  ningún mensaje del grupo casa con su fecha, el principal ya está copiado y **nadie** recibe el rol
  de principal: todas las filas son anexos.
- Si el hilo ya se materializó **plano**, `plano_existente=True` impide abrir carpeta: los mensajes
  nuevos entran como documentos planos propios, en vez de crear un bundle sin principal dentro.
- Los **basenames de origen deben ser únicos**: si se repiten, la función aborta con `ValueError`.
  Dos lotes distintos pueden traer el mismo basename con `sha256` distinto, porque `_ruta_unica` solo
  desambigua dentro de su propio lote; silenciarlo perdería un mensaje.

## 3-bis. Lo que el §7 original proponía y quedó retirado

Esto retira **por completo** el §7 del diseño anterior (ledger de `MSG-id` + principal inmutable +
deltas). Era la pieza que las dos revisiones desmontaron, por tres vías confirmadas de forma
independiente: el `MSG-id` no está congelado por contenido sino por `Message-ID` con contenido
mutable, el conjunto de mensajes de un hilo puede **encoger** entre corridas, y el índice emitía una
línea por fila. El re-tajo no la parchea: la hace innecesaria.

## 4. Convivencia con salas ya montadas

**No hay migración.** Los `.eml` ya copiados constan por su `sha256` y se saltan; solo los documentos
**nuevos** adoptan la forma de bundle. El resultado es una sala mixta (documentos antiguos planos +
bundles nuevos), sin duplicados y sin borrar nada. Es el comportamiento esperado, no un defecto, y se
documenta como tal en la skill. Re-montar una sala entera con la forma nueva sigue siendo la
operación manual que ya prevé la skill (vaciar `Sala lectura/` a mano y re-correr; el crudo está
intacto).

## 5. Limitaciones aceptadas (documentadas, no arregladas)

- **El agrupado es por nombre de fichero, no por cabeceras RFC.** Un hilo cuyo asunto cambió a mitad
  de conversación no se agrupa. Es la limitación que el propio `agrupar_por_hilo` ya advierte en su
  docstring ("proxy barato, no sustituto de un threading riguroso si algún día hace falta").
  Threading riguroso por `References`/`In-Reply-To` → `MEJORAS #88`.
- **Dos conversaciones distintas con el mismo asunto comparten bundle** (p. ej. dos "consulta" de
  años diferentes). **Decisión de Nikolai 2026-07-27: sin guarda** — se descartó partir por salto
  temporal para no introducir un umbral arbitrario. El daño está acotado: los documentos conservan su
  fecha correcta en el `_MANIFIESTO.md` y en `CRONOLOGIA.md`, el crudo de `00_Input` está intacto y la
  sala es una vista derivada, no prueba; la molestia es de legibilidad. `MEJORAS #88` es el arreglo
  cuando moleste de verdad.
- **Correspondencia suelta no gana nada:** un hilo de un único mensaje queda plano, como hoy.
- **La sala no aprovecha el trabajo de `email_atomize`.** Sigue releyendo el `.eml`. Ese era el
  objetivo original y queda íntegro en `MEJORAS #86`.

## 6. Plan de testing

Sobre las **dos funciones deterministas** que soportan el diseño (`agrupar_por_hilo` con la clave
nueva y `layout_bundle_hilo`, ambas en `scripts/preclasificar.py`) y sobre `construir_indice`:

1. **Clave nueva:** el mismo asunto en fechas distintas cae en un solo grupo.
2. **Regresión del ítem 11:** `oferta_vivienda_1_990_000` sigue sin fusionarse con un
   `oferta_vivienda_1_990` inexistente.
3. Grupo de 3 `.eml` → una subcarpeta, principal = el más antiguo, 2 anexos con `parent_id` = nombre
   pelado de la carpeta y **su fecha propia**.
4. Grupo de 1 mensaje **sin** adjuntos → plano, sin subcarpeta. Grupo de 1 **con** adjuntos → bundle.
5. Un `0000-00-00` (fecha no parseable) **no** se convierte en principal: las fechas ciertas van
   primero (misma convención que el índice).
6. **Idempotencia del nombre (§2.3):** con `carpeta_existente` dado, añadir al grupo un mensaje
   **anterior** al principal **no** renombra la carpeta; el mensaje entra como anexo con su fecha.
6-bis. **Estabilidad del nombre del anexo entre corridas** (el fallo que la revisión final
   encontró): un mensaje que llegue en la 2ª corrida y ordene ANTES que otro ya copiado no puede
   cambiar el nombre de aquel; y ninguna fila del grupo puede repetir `nombre_canonico`.
6-ter. **`carpeta_existente` sin candidato de esa fecha** → todas las filas son anexos, ninguna
   recibe `{carpeta}/{carpeta}.eml` (la ruta del principal ya copiado).
6-quater. **`plano_existente=True`** → no se abre carpeta y ninguna fila lleva `/`.
6-quinquies. **Basenames repetidos en el grupo** → `ValueError`, no pérdida silenciosa.
7. `construir_indice` sobre 1 principal + 3 anexos → **una** línea con `(+3 anexos)`;
   `construir_cronologia` sobre lo mismo → **cuatro** líneas (sin cambios).
8. **Ningún anexo desaparece en silencio:** un anexo con `parent_id` huérfano (sin principal que lo
   reclame) sigue emitiendo su propia línea en `INDICE.md` — misma doctrina del ítem 12 del backlog.
9. **Regresión:** suite completa verde, incluidos los tests vigentes de `agrupar_por_hilo`
   (actualizados a la clave sin fecha) y los bundles de WhatsApp/CRM, que ahora aparecen colapsados.

**Fuera de test unitario, por honestidad:** las invariantes de re-corrida (skip por `sha256`, "solo
añade") no las implementa código de la skill sino el procedimiento del `SKILL.md` sobre el
`_MANIFIESTO.md`; no se simulan con un test. Lo testeable de esa promesa es la **determinismo de
`layout_bundle_hilo`**, que cubre el test 6.

## 7. Pasos operativos al cerrar

- Versión de la skill → **1.13** (frontmatter + `CHANGELOG.md`, guard verde).
- Re-empaquetar (`scripts/package_skill.py --out dist/skills <dir>`) y **re-importar el `.skill` en
  Cowork** — sin esto, Paola/Ana/Sergio siguen con la v1.12.
- `MEJORAS #75` queda **parcialmente promovido**: la parte de granularidad la cubre este spec; la de
  consumo de fuentes atomizadas sigue en backlog como `#86`.
