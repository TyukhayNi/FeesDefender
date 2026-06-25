# Diseño — Fix de parseo "Enviado el:" en email_atomize (cabeceras Outlook ES)

> Fix de bug acotado en `core/email_atomize/inline.py`. Causa raíz hallada por depuración
> sistemática (Phase 1 completa) sobre datos reales de W-02VND1. Spec base: Layer B
> (`2026-06-25-email-atomize-layerb-design.md`) y F4 media-reconstruida
> (`2026-06-25-email-atomize-media-reconstruida-design.md`). Prime directive heredado: **cero
> misatribución**.

## 0. Causa raíz (verificada sobre datos reales)

Tras la corrida en vivo de F4 sobre W-02VND1, **6 segmentos `fwd_line` con remitente válido
extraído** (`per01c@example.invalid`, `per01a@example.invalid`, `per03@example.invalid` — correspondencia de PersonaUno)
quedaron en `cola.md` con motivo `sin_fecha,no_estructural`, sin promover a `media-reconstruida`.

Reproducción (Phase 1):
- Las 3 expresiones de etiqueta de `inline.py` —`_RE_LABEL` (parseo), `_RE_2ND_LABEL` (detección
  de marca) y `_RE_ANYLABEL` (acumulación de anclaje)— casan `enviado` seguido **inmediatamente**
  de `\s*:`. Pero el Outlook español emite la etiqueta de fecha como **"Enviado el:"** (el ` el`
  intermedio). `_RE_LABEL.match("Enviado el: …")` → **False**.
- Efecto **en cascada** (peor que solo la fecha): en `_pasada_segmentos`, tras la línea `De:` el
  bucle de anclaje acumula líneas mientras `_RE_ANYLABEL` casa. La línea `"Enviado el:"` **no
  casa** → el bucle para → **Enviado/Para/Asunto quedan fuera del anclaje**. El anclaje real de
  los 6 bloques es solo `"-----Mensaje original----- / De: <remitente>"`. Resultado:
  `parsear_anclaje` extrae remitente pero **ni fecha ni asunto** → `fecha_iso="0000-00-00"` →
  `clasificar` devuelve `media`/`sin_fecha` → no promueve.
- Confirmado: `parsear_anclaje("…\nEnviado el: viernes, 4 de octubre de 2024 11:40\n…")` → fecha
  `0000-00-00`; con `"Enviado:"` (sin ` el`) → `2024-10-04`. El test `test_anclaje_outlook_bilingue`
  usaba `"Enviado:"`, enmascarando el caso real. Las 6 etiquetas reales: `"Enviado el: <día>, N de
  <mes> de <año> HH:MM"`.

## 1. Fix

Insertar un sufijo opcional **no capturador** `(?:\s+el)?` entre el grupo de alternancia de
etiquetas y el `\s*:`, en las tres expresiones de `inline.py`. Al ir FUERA del grupo 1, el grupo
capturado sigue siendo la etiqueta desnuda (`"Enviado"`), de modo que `_parse_label` indexa
`labels["enviado"]` correctamente (no `"enviado el"`).

```python
# _RE_LABEL  (parseo de etiquetas → grupos: 1=etiqueta, 2=valor; (?:\s+el)? NO añade grupo)
r"(?im)^\s*(de|from|enviado|enviat|sent|fecha|date|para|to|asunto|subject|cc|cco|bcc)(?:\s+el)?\s*:\s*(.*)$"
# _RE_2ND_LABEL  (detección de 2ª etiqueta para marca outlook_es)
r"(?i)^\s*(enviado|enviat|sent|fecha|date|para|to|asunto|subject|cc|cco|bcc)(?:\s+el)?\s*:"
# _RE_ANYLABEL  (acumulación de anclaje)
r"(?i)^\s*(de|from|enviado|enviat|sent|fecha|date|para|to|asunto|subject|cc|cco|bcc)(?:\s+el)?\s*:"
```

- Se añade también `enviat` (Catalán; corpus bilingüe) al set de etiquetas de fecha — cubre
  `"Enviat el:"`. El resto de etiquetas Catalanes de Outlook (`Data:`, `Per a:`, `Assumpte:`)
  quedan **fuera de alcance** (gap aparte; los 6 confirmados son ES).
- **Seguridad / por qué es aditivo:** `(?:\s+el)?` es opcional → toda línea que casaba antes
  sigue casando idéntica (los tests con `"Enviado:"`/`"Sent:"`/`"Date:"` no cambian). Solo AÑADE
  match para líneas `"<etiqueta> el:"`. Que el sufijo aplique a cualquier etiqueta (no solo
  `enviado`) es teóricamente más permisivo, pero `" el:"` solo aparece tras `Enviado`/`Enviat` en
  la práctica → inocuo. Grupo 1 intacto → claves de `labels` intactas. NO toca la lógica de
  promoción ni los guardarraíles de ambigüedad/fecha-incoherente.

## 2. Plan de tests (TDD)

**Puros (`tests/test_email_atomize_inline.py`):**
1. `parsear_anclaje` sobre bloque `outlook_es` con `"Enviado el: lunes, 3 de febrero de 2020
   18:42"` → `de` correcto **y `fecha_iso == "2020-02-03"`** (hoy falla: `0000-00-00`).
2. `parsear_anclaje` con `"Enviat el: 3 de febrer de 2020"` (Catalán) → fecha parseada.
3. Regresión: `"Enviado:"` (sin ` el`) sigue parseando la fecha (no romper el caso existente).
4. **Anclaje completo (cascada)**: `segmentar_texto` de un cuerpo `fwd_line`/`outlook_es` con
   bloque `De:/Enviado el:/Para:/Asunto:` → el `anclaje_texto` del segmento **incluye** las líneas
   Enviado/Para/Asunto (hoy se truncan tras `De:`), y `parsear_anclaje` del segmento da de+fecha+asunto.

**Glue (`tests/test_email_atomize_pipeline_b.py`):** portador de texto plano cuyo bloque citado usa
`"Enviado el: …"` con remitente válido `<addr>` no estructural → tras atomizar, **1 atom
`media-reconstruida`** (hoy: 0; iría a `cola.md` por `sin_fecha`).

**Regresión dura:** suite completa del motor verde; Capa A byte-idéntica (el cambio solo afecta el
parseo de citas, no el render de Capa A).

## 3. Verificación sobre datos reales (post-fix)

Re-correr `atomize_case('W-02VND1')` (autorizado esta sesión; escribe en `G:`, idempotente). Esperado:
- Los **6 bloques `fwd_line` de PersonaUno** (`per01c@example.invalid`, `per01a@example.invalid`, `per03@example.invalid`)
  pasan de `cola.md/sin_fecha` a **atoms `media-reconstruida`** propios (con fecha y asunto), o se
  resuelven por dedup a una copia limpia si existe.
- Capa A byte-idéntica (verificar SHA-256 contra manifiesto previo).
- `reconstruidos.md` los lista. Auditar cada uno: su `De:`/`Enviado el:` aparece literal en el `.eml`.
- Idempotencia: 2ª corrida → 0 cambios.

## 4. Fuera de alcance

- Los **76 segmentos `sin_cabecera`** (gmail_quote/apple sin remitente extraíble) — gap distinto
  (extracción de remitente en HTML), no lo aborda este fix.
- Etiquetas Catalanas de Outlook completas (`Data:`/`Per a:`/`Assumpte:`).
- Gap 2 (enterrados dentro de reconstrucciones).
