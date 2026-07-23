# Revisión adversarial — Consumo de emails atomizados en la sala de lectura

> Fecha: 2026-07-23. Revisor: Codex. Estado: **pendiente de adjudicación**.
> Esta revisión no sustituye la spec: identifica condiciones que deben aceptarse,
> rechazarse con evidencia o incorporarse antes de escribir el plan de implementación.

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

## Adjudicación

Antes del plan, completar esta tabla y modificar la spec en consonancia:

| Hallazgo | Decisión | Evidencia / cambio incorporado |
| --- | --- | --- |
| P0.1 | pendiente | |
| P0.2 | pendiente | |
| P0.3 | pendiente | |
| P1.1 | pendiente | |
| P1.2 | pendiente | |
| P1.3 | pendiente | |
| P1.4 | pendiente | |
| P1.5 | pendiente | |
