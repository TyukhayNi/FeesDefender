# Derivación documental de los 14 hitos (DATOS OPERACIÓN)

> Motor de scoring de la hoja `INFORMACION`. Cada hito se deriva de respuestas concretas del cuestionario que, en el pre-relleno, se obtienen **del documento**. El `TOTAL` es métrica auxiliar, **no veredicto**. Cómo tratar la ausencia de documento (`pendiente` vs `0`) depende del tipo de hito — ver regla de oro 4 de `SKILL.md` y la nota al pie de la tabla.

## Reglas de oro del scoring
- **Conservador**: una firma `no_cotejado` puntúa **0**, nunca 1.
- **`N/A` no suma ni resta**: la fórmula `=SUM(F25:G38)` ignora celdas de texto.
- **Sin documento → `pendiente`** (vacío) para los hitos que dependen de un hecho no necesariamente documentado. Para los **hitos de existencia documental** (marcados `[E]` en la tabla) la ausencia total de referencia al documento en `00_Input` **es** la respuesta → `0`, no pendiente. Detalle y lista completa en la regla de oro 4 de `SKILL.md`.
- Las observaciones por hito **ya no van en INFORMACION**: el rastro `[doc: fichero] "cita" (confianza)` vive en `PREGUNTAS` (col. CITA/FUENTE) y las banderas en `AVISOS LLM`.

## Orden y celdas (hoja INFORMACION)
14 hitos en `B25:B38`, score en `F` (merge `F:G`), fecha en `H`. TOTAL en `F39 = SUM(F25:G38)`.

| # | Celda | Hito | Score | Regla de derivación (pre-relleno documental) | Fecha desde |
|---|-------|------|-------|-----------------------------------------------|-------------|
| 1 | F25 | **CUANTÍA** | 1/2/3 | Categórico sobre TOTAL DEUDA: `≤10.000€`→1; `10.001–20.000€`→2; `>20.000€`→3. | — |
| 2 | F26 | **ENCARGO** `[E]` | 0/1 | =1 **solo si TODO**: firmado (`cap_08`) + original (`cap_13`) + completo páginas/cláusulas (`cap_08b`) + firman todos los clientes (`cap_08c`) + cotejo firmas vs DNI = sí (`cap_08d`). Si `cap_08d=no_cotejado` → **0**. Sin encargo en el expediente → **0**. | doc. encargo |
| 3 | F27 | **IDENTIFICACIÓN PROPIETARIO** `[E]` | 0/1 | =1 si copia de DNI de **todos** los propietarios (`cap_17`). Sin copia en el expediente → **0**. | — |
| 4 | F28 | **TITULARIDAD** `[E]` | 0/1 | =1 si existe nota simple de captación (`cap_18a`). Aviso si titulares ≠ firmantes del encargo (`cap_18c=no`). Sin nota simple en el expediente → **0**. | nota simple (`cap_18b`) |
| 5 | F29 | **HOJA DE VISITA** `[E]` | 0/1/N/A | N/A si no aplica (`vis_00=no`); 1 si hoja firmada (`vis_05`) **y** original/copia (`vis_06∈{original,copia}`); si no (incl. sin documento y `vis_00` sin resolver), 0. | doc. hoja de visita |
| 6 | F30 | **OFERTA** `[E]` | 0/1 | =1 si original firmado de la oferta (`ofb_05`). Sin oferta en el expediente → **0**. | doc. oferta |
| 7 | F31 | **IDENTIFICACIÓN BUSCADOR** `[E]` | 0/1 | =1 si copia de DNI de **todos** los buscadores (`vis_09`). Aviso si firmas oferta vs DNI no coinciden / pendientes de cotejo (`vis_10`). Sin copia en el expediente → **0**. | — |
| 8 | F32 | **ARRAS / ARRENDAMIENTO** `[E]` | 0/1/N/A | 1 si `firmadas` (`arr_00`); 0 si `intentadas_no_firmadas`; N/A si `no_aplica` (p. ej. el proceso se truncó antes de esta fase). | `arr_00` fecha |
| 9 | F33 | **RECON. HON. — ARRAS** `[E]` | 0/1/N/A | 1 si reconocimiento de honorarios firmado en arras (`arr_13`); 0 no; N/A si `ARRAS/ARRENDAMIENTO` es N/A. | `arr_13` fecha |
| 10 | F34 | **ESCRITURA** `[E]` | 0/1/N/A | 1 si se otorgó (`esc_01=sí`); 0 si `esc_01=no` **o** no consta ninguna escritura en el expediente; N/A no aplica. Aviso si `esc_01=sí` y `esc_02=no` (sin nota simple posterior) → "confirmar otorgamiento con nota simple actualizada". | `esc_01` fecha |
| 11 | F35 | **RECON. HON. — ESCRITURA** `[E]` | 0/1/N/A | 1 si reconocimiento firmado en escritura (`esc_03`); 0 no; N/A si `ESCRITURA` es N/A o no hubo escritura. | `esc_03` fecha |
| 12 | F36 | **RECLAMACIÓN JURÍDICO** | 0/1 | =1 si se envió burofax jurídico (`rec_02`) — interrumpe prescripción. Este hito **no** es de existencia documental: el burofax pudo enviarse por un canal aún no volcado al expediente, así que sin evidencia clara queda `pendiente` y se avisa (severidad alta si hay indicios de riesgo de prescripción), no `0` automático. | `rec_02` fecha |
| 13 | F37 | **RESPUESTA A LA RECLAMACIÓN** | 0/1/N/A | 1 si hubo respuesta (`rec_03=sí`); 0 no; N/A si `en_plazo` o si `RECLAMACIÓN JURÍDICO` es `pendiente`. | `rec_03` fecha |
| 14 | F38 | **OFERTA VINCULANTE CONFIDENCIAL** | 0/1/N/A | 1 si hubo oferta de transacción del deudor (`rec_04`); 0 no; N/A no aplica. | `rec_04` fecha |

`[E]` = **hito de existencia documental** (regla de oro 4 de `SKILL.md`): sin referencia alguna a ese documento en `00_Input` → `0`, no `pendiente`, porque la pregunta ES si el documento existe. Los cuatro hitos sin `[E]` (`CUANTÍA`, `RECLAMACIÓN JURÍDICO`, `RESPUESTA A LA RECLAMACIÓN`, `OFERTA VINCULANTE CONFIDENCIAL`) dependen de un hecho o de un cálculo que puede no estar documentado aunque haya ocurrido — ahí sigue rigiendo `pendiente` por defecto.

> **Cambio respecto a la metodología antigua**: el hito `RECLAMACIÓN FINANZAS` (antiguo `rec_01`) **se eliminó del modelo aprobado** ("no reclaman"). No existe en la plantilla ni en el cuestionario. Son **14 hitos**, no 15.

## Importes y fórmulas (mantener las fórmulas Excel)
- `PRECIO` (`H13`) — del encargo / oferta / escritura (operación efectiva).
- `% HONORARIOS` (`E14`) — **default 5** si no consta otro en el encargo.
- `TOTAL HONORARIOS` (`H14`) = `=H13/100*E14*1.21` (compraventa, IVA 21%). En **arrendamiento**, ajustar a la fórmula del encargo (típicamente una mensualidad o % sobre renta anual).
- `PAGOS PARCIALES` (`H15`) — default 0.
- `TOTAL DEUDA` (`H16`) = `=H14-H15`.
- `PROPUESTA PAGO` (`H17`) — si consta.
- `DIFERENCIA` (`H18`) = `=H16-H17`.

## Actividades (valores numéricos)
`EXPOSES - PROPIEDAD` (F42), `VISITAS - PROPIEDAD` (F43), `EXPOSES - COMPRADOR` (F44), `VISITAS - COMPRADOR` (F45). Décimas/centenas para exposés, unidades para visitas.
