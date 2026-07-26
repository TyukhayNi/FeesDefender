# Diseño — Bundle por hilo de correo en la sala de lectura (Slice 1)

> **Historial de este spec.** Nació el 2026-07-23 como "consumo de emails atomizados en la sala de
> lectura": la sala leería `01_Procesado/Emails/` (salida de `core/email_atomize`) en vez de releer
> el `.eml` crudo. Dos revisiones adversariales independientes —Codex
> ([`…-adversarial-review.md`](2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md)) y un
> workflow de 6 lentes con verificación por escépticos— convergieron en los mismos bloqueantes, y la
> adjudicación (Claude, 2026-07-26) concluyó que el spec **empaquetaba tres proyectos** y que su
> mecanismo central de idempotencia partía de una premisa falsa. **Re-tajado el 2026-07-26 con
> aprobación de Nikolai:** este documento queda reducido al **Slice 1**, que entrega el beneficio más
> visible sin ninguno de los bloqueantes. Los Slices 2 y 3 salen a backlog con disparador explícito
> (`MEJORAS #84`, `#85`). La tabla de adjudicación completa vive en la revisión hermana.

---

## 1. Objetivo y alcance

**Objetivo.** Que la correspondencia de un caso ocupe en la sala de lectura **una entrada por hilo**
en vez de una por mensaje. Hoy cada `.eml` se copia como documento propio y ocupa su propia línea de
índice: un caso con ~277 correos (magnitud real de W-02VND1) produce ~277 ficheros sueltos y ~277
líneas — la sala deja de ser legible, que es exactamente su propósito.

**Este spec NO hace** (y es deliberado, no un olvido):

- **No consume `01_Procesado/Emails/`.** Nada de `corpus.jsonl`, `MSG-id`, Capa B ni adjuntos
  deduplicados. → `MEJORAS #84` (Slice 2).
- **No cambia QUÉ fichero se copia.** Sigue copiándose el `.eml` con sus adjuntos MIME, como hoy. El
  criterio "email → MD legible, el `.eml` es custodia" que Nikolai cerró el 2026-07-19
  (`MEJORAS #75`) llega con el Slice 2, no aquí.
- **No toca `core/email_atomize` ni `core/anon`** (módulo congelado por `CLAUDE.md`).
- **No toca el OCR de adjuntos** ni el motor de extracción. → `MEJORAS #85` (Slice 3).
- **No introduce ningún motor de threading nuevo.** → `MEJORAS #86`.

Todo el cambio vive **dentro del paquete `.skill`** de `organizar-sala-lectura`. Cero instalación
nueva para el equipo: los scripts de la skill son **stdlib puro y self-contained** (corren en el
sandbox de Cowork sin `core/`, como declara el propio docstring de `scripts/preclasificar.py`), así
que Paola, Ana y Sergio solo reimportan el `.skill` como ya hacen.

## 2. Los tres cambios

### 2.1 Forma de copia: un bundle por grupo de hilo

Se **reutiliza `agrupar_por_hilo` tal cual** ([`preclasificar.py:133-155`](../../../.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:133)),
que ya agrupa los `.eml` por hilo y ya está endurecido contra el falso positivo de una cifra en el
asunto (ítem 11 del backlog de robustez). Lo único que cambia es **dónde aterriza cada fichero**:

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

## 3. Idempotencia: sin algoritmo nuevo

**El skip incremental no cambia.** Sigue siendo por `sha256` del `.eml` de origen, y cada `.eml`
conserva su fila propia en el `_MANIFIESTO.md`. Un mensaje nuevo del hilo es un `.eml` nuevo, con su
propio `sha256`, que aterriza como anexo dentro de la carpeta ya existente. No hace falta ledger, ni
conjuntos, ni columna nueva, ni huella agregada.

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
  Threading riguroso por `References`/`In-Reply-To` → `MEJORAS #86`.
- **Correspondencia suelta no gana nada:** un hilo de un único mensaje queda plano, como hoy.
- **La sala no aprovecha el trabajo de `email_atomize`.** Sigue releyendo el `.eml`. Ese era el
  objetivo original y queda íntegro en `MEJORAS #84`.

## 6. Plan de testing

1. Grupo de 3 `.eml` → una subcarpeta, principal = el más antiguo, 2 anexos con `parent_id` correcto
   y su fecha propia.
2. Grupo de 1 mensaje sin adjuntos → fichero plano, sin subcarpeta.
3. `construir_indice` sobre 1 principal + 3 anexos → **una** línea con `(+3 anexos)`;
   `construir_cronologia` sobre lo mismo → **cuatro** líneas.
4. Re-corrida sin cambios → 0 escrituras (skip por `sha256` intacto).
5. Re-corrida con un `.eml` nuevo del mismo hilo → 1 anexo nuevo en la carpeta existente, principal
   intacto (`sha256` idéntico), índice con `(+4 anexos)`.
6. Re-corrida con un `.eml` nuevo **anterior** al principal → entra como anexo, la carpeta **no** se
   renombra, `CRONOLOGIA.md` lo ordena primero.
7. `verificar_sala.py` verde sobre una sala con bundles de hilo: sin `parent_id` huérfano, sin
   colisión de `nombre_canonico`.
8. **Regresión:** tests de `preclasificar` e índices verdes; los bundles de WhatsApp y CRM existentes
   siguen pasando el verify y ahora aparecen colapsados en el índice.

## 7. Pasos operativos al cerrar

- Versión de la skill → **1.13** (frontmatter + `CHANGELOG.md`, guard verde).
- Re-empaquetar (`scripts/package_skill.py --out dist/skills <dir>`) y **re-importar el `.skill` en
  Cowork** — sin esto, Paola/Ana/Sergio siguen con la v1.12.
- `MEJORAS #75` queda **parcialmente promovido**: la parte de granularidad la cubre este spec; la de
  consumo de fuentes atomizadas sigue en backlog como `#84`.
