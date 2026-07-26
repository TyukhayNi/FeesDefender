# Revisión adversarial — Consumo de emails atomizados en la sala de lectura

> Fecha: 2026-07-23. Revisor: Codex. Estado: **✅ ADJUDICADA (Claude, 2026-07-26)** — ver la tabla
> final. Resultado: el spec se **re-tajó** en tres slices y quedó reducido al Slice 1; los hallazgos
> que atacaban el consumo del corpus y el OCR salieron de alcance con destino de backlog.
> Esta revisión no sustituye la spec: identifica condiciones que deben aceptarse,
> rechazarse con evidencia o incorporarse antes de escribir el plan de implementación.

> **Segunda revisión, independiente (2026-07-26).** Un workflow de 6 lentes (contrato de datos ·
> idempotencia · integración con la skill · motor OCR · doctrinas del repo · completitud) produjo 55
> hallazgos brutos → 35 únicos. La verificación adversarial (3 escépticos por hallazgo, con lectura de
> fuente completa) solo alcanzó a **7 de 35** antes de que la organización topara su límite mensual de
> gasto; **los 7 sobrevivieron con 3 de 3 escépticos confirmando**, y los 28 restantes quedaron
> **sin verificar** (no refutados — la distinción importa: sus verificadores murieron por el límite,
> no por desmontar el hallazgo). Los 7 verificados coinciden en lo sustancial con P0.1, P0.2, P1.1 y
> P1.4 de esta revisión, más dos aportaciones propias recogidas abajo (F-A, F-B).

## Veredicto

**No implementar todavía.** La dirección —consumir el trabajo ya atomizado y presentar un
bundle por hilo— es adecuada, pero el diseño contiene tres bloqueantes P0 y varios contratos
que no coinciden con el código actual.

## Hallazgos

### P0.1 — No existe un contrato de cobertura por lote o `.eml`

La spec promete fallback por lote y distinguir hilos cubiertos de no cubiertos (§1, §5 y §6),
pero hay un único `corpus.jsonl` por caso y sus filas no exponen `eml_origen` ni una marca de
cobertura reconciliable con el inventario actual de `00_Input` (`core/email_atomize/corpus.py:21-46`).

**Escenario:** se atomiza el caso, entra después un lote nuevo y se organiza la sala sin
reatomizar. El corpus existe, pero está obsoleto; el consumidor no puede demostrar qué `.eml`
falta ni si pertenece a un hilo conocido.

**Cambio exigido:** persistir y reconciliar al menos `ruta_eml/sha256 -> MSG-id`; la mera
existencia de `corpus.jsonl` nunca equivale a cobertura completa.

### P0.2 — Capa B carece de hilo y colapsaría conversaciones distintas

La motivación promete aprovechar la autoría reconstruida de Capa B, pero
`core/email_atomize/inline.py:1023-1031` construye esos mensajes sin `hilo` ni `in_reply_to`;
ambos quedan vacíos por defecto (`model.py:37-44`). Al agrupar el corpus por `hilo`, todos los
mensajes B del expediente pueden terminar en un único bucket `""`.

**Cambio exigido:** definir que Capa B hereda el hilo del portador `reconstruido_de` y probar
que ningún mensaje consumible cae en un bucket global vacío.

### P0.3 — El incremento por anexos contradice la granularidad de una fila por hilo

Según §7, si llega una respuesta nueva se mantiene inmutable el documento principal y el nuevo
mensaje se añade como anexo. El principal deja de representar el hilo actual. Además,
`indices_desde_manifiesto.py:43-75` emite una línea por cada fila del manifiesto: los mensajes
nuevos aparecerían como filas adicionales, contradiciendo “N hilos producen N filas”.

La spec tampoco fija dónde se acumula el conjunto registrado de `MSG-id`: si no se actualiza,
el mismo mensaje se vuelve a añadir; si se modifica la fila previa, debe declararse que los
metadatos son mutables aunque los documentos copiados sean append-only.

**Cambio exigido:** elegir entre (a) regenerar atómicamente una vista derivada versionada del
hilo o (b) conservar principal+deltas, pero agrupar índice y cronología por bundle y definir un
estado acumulativo inequívoco.

### P1.1 — `MSG-id` no está congelado por contenido

`core/email_atomize/ids.py:37-45` asigna números secuenciales preservados por `_registro.json`;
no deriva el ID del contenido. Además, el dedup distingue mensajes sin `Message-ID` por SHA
(`dedup.py:25-26`), pero `msg_id_for()` recibe después la clave vacía: dos mensajes distintos
sin `Message-ID` pueden compartir `MSG-id`.

**Cambio exigido:** para ausencia de `Message-ID`, acuñar la identidad con `sha256:<raw>` y
probar dos mensajes distintos sin esa cabecera, incluida una reconstrucción desde registro nuevo.

### P1.2 — El `hilo` actual no identifica siempre la conversación lógica

`headers.py:63-72` toma la primera referencia y, si falta, solo el `In-Reply-To` inmediato.
Una cadena A <- B <- C donde C perdió `References` queda partida: A/B usan hilo A y C usa hilo B.

**Cambio exigido:** acotar formalmente qué significa “hilo”, definir reconciliación o aceptar y
documentar la partición conservadora; añadir el caso a tests.

### P1.3 — No está resuelta la relación muchos-a-muchos de adjuntos

Un adjunto deduplicado por SHA puede pertenecer a varios hilos. El skip global por SHA de la sala
haría que solo apareciera en el primero; copiarlo en ambos exige distinguir duplicado legítimo por
pertenencia de duplicado evitable. §7 tampoco dice qué ocurre cuando un mensaje incremental trae
un adjunto nuevo.

**Cambio exigido:** estado por bundle con conjuntos separados `msg_ids` y `attachment_shas`, más
una política explícita para adjuntos compartidos y para deltas con nuevos binarios.

### P1.4 — `ocr_pdf` no sustituye directamente al extractor de texto

`core/anon/ocr.py:30-42` exige una ruta de salida y devuelve un PDF buscable, no texto. El router
actual devuelve una `Extraccion` textual. Faltan el PDF temporal, la extracción posterior con
`pypdf`, limpieza, fallos, PDF nativo/ya OCRizado y actualización coherente de
`metodo_extraccion`/`ocr_aplicado`.

**Cambio exigido:** especificar un adaptador completo y probar PDF escaneado, nativo, ya OCRizado,
cifrado/corrupto y limpieza de temporales.

### P1.5 — La ruta documentada de contenido de adjunto no existe

La spec usa `adjuntos/<sha>.contenido.md`; el código genera
`<fecha>_<slug>_<ATT-id>.contenido.md` (`core/adjuntos_contenido/pipeline.py:27-29`).

**Cambio exigido:** resolver por el sidecar/índice SHA; no construir una ruta nominal inexistente.

## Condiciones mínimas para aprobar la spec

1. Contrato de cobertura reconciliable entre `00_Input` y corpus.
2. Herencia de hilo para Capa B y tratamiento explícito de hilo vacío/partido.
3. Semántica incremental compatible con una fila visible por bundle.
4. Identidad estable para mensajes sin `Message-ID`.
5. Estado de adjuntos por bundle, incluidos adjuntos compartidos y deltas.
6. Adaptador completo `ocr_pdf -> texto` y resolución real de sidecars.
7. Tests de corpus desactualizado, reducción del conjunto, hilo nuevo, hilo vacío, adjunto
   compartido/nuevo y re-recorrida tras un delta.

## Adjudicación (Claude, 2026-07-26)

**Decisión de fondo.** El veredicto "no implementar todavía" se acepta. La adjudicación individual
mostró que los hallazgos no eran defectos de detalle de un spec por lo demás sano: se concentraban en
**dos piezas separables** (el consumo del corpus atomizado y la unificación del motor OCR) y en **un
mecanismo propio roto** (el §7, ledger de `MSG-id` con principal inmutable y deltas). Por eso el
remedio no fue parchear ocho puntos, sino **re-tajar el spec en tres slices** (aprobado por Nikolai el
2026-07-26) y reducirlo al que no arrastra ningún bloqueante:

- **Slice 1 — bundle por hilo en la sala** (este spec, re-escrito). No consume el corpus, no usa
  `MSG-id`, no toca `email_atomize` ni el OCR. Idempotencia = el `sha256` por `.eml` que ya existe.
- **Slice 2 — consumo de las fuentes atomizadas** → `MEJORAS #84`, con P0.1, P0.2, P1.1 y P1.3 como
  **requisitos de entrada** del futuro spec.
- **Slice 3 — motor de extracción/OCR unificado para adjuntos** → `MEJORAS #85`, con P1.4 y P1.5 como
  requisitos de entrada.

**Dos correcciones a la revisión, verificadas contra fuente** (Claude es el juez; ni Codex ni el
workflow tienen la última palabra sobre corrección):

- **P0.1 se rebaja de bloqueante a omisión del spec.** La cobertura **sí** es demostrable:
  `_registro.json` persiste `eml_procesados`, la lista de `.eml` ya atomizados
  (`core/email_atomize/ids.py:77-79,91`, alimentada desde `pipeline.py:110` con
  `marcar_procesado(col.eml_origen)`). Lo que falla es que el spec no la citaba y asumía "existe
  `corpus.jsonl` ⇒ todo cubierto". El caveat de la revisión sí se sostiene y se hereda al Slice 2: la
  llave es el **nombre** del fichero, y `corpus.jsonl` no emite `eml_origen` (verificado,
  `core/email_atomize/corpus.py:21-46`), así que mapear un `.eml` cubierto a *su* hilo sigue sin llave
  fuerte.
- **P0.2 no obliga a modificar el atomizador congelado.** El enlace Capa B→hilo es derivable **en el
  consumidor**: `construir_b` fija `procedencia=[{"citado_en": <portador>}]` y `corpus.py` lo emite,
  de modo que un mensaje B puede heredar el hilo de su portador sin tocar `email_atomize`. El defecto
  (todos los B con `hilo=""`, `model.py:43`) es real y triple-verificado; solo cambia dónde se arregla.

| Hallazgo | Decisión | Evidencia / cambio incorporado |
| --- | --- | --- |
| P0.1 | **rebajado + fuera de alcance** | `_registro.json.eml_procesados` da la cobertura (`ids.py:77-91`, `pipeline.py:110`); no era capacidad ausente sino omisión. El Slice 1 no consume el corpus → no aplica. Requisito de entrada de `MEJORAS #84`, con el caveat "llave por nombre, sin `eml_origen` en `corpus.jsonl`". |
| P0.2 | **aceptado + fuera de alcance** | Real y verificado 3/3 (Capa B con `hilo=""`, `model.py:43`). Arreglable en el consumidor vía `procedencia[].citado_en`, sin tocar módulo congelado. El Slice 1 no lee el corpus → no aplica. Requisito de entrada de `MEJORAS #84`. |
| P0.3 | **aceptado y resuelto en el Slice 1** | Confirmado en código: `construir_indice` recorre todas las filas sin filtrar `parent_id` (`indices_desde_manifiesto.py:43-66`), así que agrupar en carpetas no habría reducido el índice. Doble remedio: (a) el §7 (principal inmutable + deltas) **se retira entero**, el skip vuelve a ser el `sha256` por `.eml`; (b) `INDICE.md` colapsa bundles a una línea `(+N anexos)` y `CRONOLOGIA.md` se deja intacta. |
| P1.1 | **aceptado + fuera de alcance** | La premisa "`MSG-id` congelado por contenido" era falsa (`ids.py:37-46`: congelado por `Message-ID`, contenido mutable por upgrade de fidelidad). El Slice 1 ya no usa `MSG-id` para nada. Requisito de entrada de `MEJORAS #84`. |
| P1.2 | **aceptado como limitación documentada** | El Slice 1 conserva a propósito la heurística de nombre de `agrupar_por_hilo` (`preclasificar.py:133-155`), cuyo docstring ya advierte que no sustituye un threading riguroso. Consecuencia declarada en §5 del spec: un hilo con cambio de asunto no se agrupa. Threading RFC → `MEJORAS #86`. |
| P1.3 | **aceptado + fuera de alcance** | El Slice 1 sigue extrayendo los adjuntos del MIME de cada `.eml` (status quo); no reutiliza el dedup global por sha256 de `email_atomize`, que es donde nace el problema muchos-a-muchos. Requisito de entrada de `MEJORAS #84`. |
| P1.4 | **aceptado + fuera de alcance** | Confirmado también por el workflow (crítico, 3/3): `ocr_pdf` es PDF→PDF, no extractor de texto, y Docling es además el extractor primario de otros tipos, así que retirarlo dejaría formatos sin cobertura. Sale entero a `MEJORAS #85`. |
| P1.5 | **aceptado + fuera de alcance** | La ruta `adjuntos/<sha>.contenido.md` del spec no existía; el nombre real lo compone `core/adjuntos_contenido/pipeline.py:27-29`. Sale a `MEJORAS #85`. |
| **F-A** (workflow) | **aceptado y resuelto en el Slice 1** | No había regla de convivencia para salas ya montadas. Resuelto sin migración: el skip por `sha256` salta lo ya copiado y solo lo nuevo se bundlea → sala mixta, sin duplicados ni borrados (§4 del spec). |
| **F-B** (workflow) | **aceptado y resuelto en el Slice 1** | Huecos de definición: hilo de un solo mensaje, `descripcion` canónica y fecha del bundle. Resueltos en §2.1/§2.3: grupo de 1 sin adjuntos → plano; `descripcion` = slug del asunto del más antiguo, ≤50 car., sin PII; nombre fijado en la 1ª corrida y nunca renombrado. |

**Hallazgos sin verificar que quedan vivos para el Slice 2/3.** De los 28 que no llegaron a
verificación, los que apuntan al consumo del corpus o al OCR se heredan como material de entrada de
`MEJORAS #84`/`#85` (caché de `adjuntos_contenido` a versionar, mapeo de confianza del router,
adjuntos decorativos, `corpus.jsonl` con línea meta inicial, ejecutabilidad del script en Modo 3,
`senales_gate` marcando adjuntos reutilizados como "binario opaco sin espejo MD"). **No están
adjudicados** y no deben tratarse como aprobados ni como descartados.
