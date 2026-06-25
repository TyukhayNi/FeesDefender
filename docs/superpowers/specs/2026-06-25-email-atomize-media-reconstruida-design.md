# Diseño — Layer B Fase 4: promoción `media-reconstruida` (correos enterrados sin estructura)

> Extensión de `core/email_atomize/`. Spec base: `2026-06-25-email-atomize-layerb-design.md`
> (Layer B Fase 2) y `2026-06-24-email-atomize-design.md` (motor). Caso piloto W-02VND1; el
> motor sigue siendo **genérico/agnóstico de caso**. Prime directive heredado: **cero
> misatribución** — un remitente solo se afirma desde un bloque de cabecera explícito y parseable.
> **Aprobado por Nikolai 2026-06-25** (opción A: atoms propios con nivel `media-reconstruida`;
> Gap 1 ahora, Gap 2 diferido).

---

## 0. Problema y decisión

Una auditoría read-only de los 366 atoms de W-02VND1 cruzada contra `corpus.jsonl`
(`scripts/audit_correos_no_separados.py`) encontró **36 correos incrustados que no tienen
fichero-atom propio**. La causa raíz no es un bug: el §4 de la spec de Layer B **a propósito**
topa a `media` (→ `_revision/cola.md`, no promovido) todo bloque de cita cuya profundidad NO
viene de estructura (anidamiento DOM / run de `>`), aunque traiga `De:`/`Enviado`/`Asunto:`
legibles. La inmensa mayoría de los 36 son de esa clase (`outlook_es`, `fwd_line` en texto plano
o cabeceras de reenvío sin blockquote): atribución de remitente fiable, pero límite de cuerpo
inferido por adyacencia.

**Decisión (opción A).** Se añade un peldaño de confianza **`media-reconstruida`** que **promueve
a atom capa B propio** estos bloques, con autoridad explícitamente menor que un `.eml` auténtico
(`alta`) y que una reconstrucción estructural (`alta-reconstruida`): banner "por verificar",
`en_revision: true`, y `De (reconstruido, por verificar)` en la lectura. Idempotente y regenerable
desde el motor (`python -m scripts.atomize_emails --ref W-02VND1`), no por curación manual.

**Alcance.** Gap 1 (bloques de cabecera de primer nivel sobre el `.eml` crudo) — cubre ~34/36,
incluido el ejemplo MSG-00021. **Gap 2 diferido** (correos enterrados DENTRO de un segmento ya
reconstruido, p.ej. el reenvío interior de MSG-00306): se documenta como pendiente (§10), no se
implementa aquí.

---

## 1. Regla de promoción: nuevo peldaño en `inline.clasificar()`

`clasificar(anc, fecha_portador_iso, *, estructural, ambigua, discrepancia=False, mojibake=False)`
gana una rama. Orden exacto (cualquier predicado fallido demota un nivel, **nunca redondea
hacia arriba**):

```
anc vacío (sin de/fecha/asunto)                      -> baja, "sin_cabecera"
mojibake                                             -> baja, "mojibake"
email_ok  = dirección sintácticamente válida en anc.de
fecha_ok  = anc.fecha_iso != "0000-00-00"
fecha posterior al portador                          -> media, "fecha_incoherente"   (NO promueve)
not email_ok and not fecha_ok                        -> baja, "sin_remitente_ni_fecha"

# --- zona de promoción: requiere remitente válido Y fecha coherente ---
email_ok and fecha_ok and not ambigua and not discrepancia:
    estructural        -> "alta-reconstruida", "ok"       (ya existente)
    not estructural    -> "media-reconstruida", "no_estructural"   # NUEVO: promueve

# --- resto: cabecera coja o límite no fiable -> queda en cola.md ---
en otro caso (falta email O falta fecha, o ambigua, o discrepancia)
                                                     -> "media", motivos
```

Claves del peldaño nuevo:
- **`media-reconstruida` exige `email_ok` Y `fecha_ok`.** Solo nombre sin `<dirección>`, o sin
  fecha → no promueve (se queda en `media`/`baja` → `cola.md`). Nunca se inventa remitente.
- **`ambigua` (`ambiguedad_profundidad`: varias cabeceras apiladas levantadas del cuerpo) y
  `discrepancia` (html↔plano) NO promueven** — ahí el límite de cuerpo es genuinamente
  inatribuible. Quedan en `media` → `cola.md`.
- La honestidad del nivel: en lo no estructural el **remitente** es fiable (sale de un `De:`
  literal), pero el **límite del cuerpo** viene de adyacencia → por eso "por verificar", nunca
  `alta`.
- Identidad candidata (`identidades.candidatas`, p.ej. `per01b@example.invalid`) sigue capada:
  si saliera `media-reconstruida` y `anc.de ∈ candidatas`, se mantiene promovida pero `en_revision`
  y forzada a `del_burgo.md` (no cambia su tope, ya es media).

## 2. Routing en `inline.reconstruir()`

- Promoción: `if conf in ("alta-reconstruida", "media-reconstruida"): res.candidatos.append(seg)`
  (antes solo `alta-reconstruida`); el resto sigue a `res.punteros` (cola).
- `en_revision`: `watched or conf in ("media", "baja", "media-reconstruida")` — los
  `media-reconstruida` **siempre** entran en revisión (hay que cotejarlos).
- `construir_b` ya copia `confianza=seg.confianza` → el atom capa B nace con `media-reconstruida`.

## 3. Dedup, fidelity-upgrade e idempotencia (núcleo de los 277 intacto)

Sin cambios en `dedup.colapsar` ni en el índice de Capa A. El pipeline ya:
1. Congela los ids de capa A antes de la pasada Layer B.
2. Para cada candidato (ahora incluye `media-reconstruida`), `idx.resolver(seg)` intenta
   puentear contra un `.eml` limpio (por `Message-ID` o `cuerpo_sha`). **Si existe, no se crea
   duplicado**: se añade `procedencia` al atom auténtico (p.ej. el reenvío exterior de MSG-00306
   resuelve a MSG-00018 y no se duplica). El auténtico (capa A, `alta`) gana.
3. Si no existe → `msg_id_for_fp(fp, cuerpo_sha=...)`, orden determinista por `fingerprint`
   (re-ejecutable sin renumerar).

Casi-duplicados día-granular → `casi_duplicados.md`, nunca fusión silenciosa. Los 277 `.md` de
capa A quedan **byte-idénticos** (regresión obligatoria).

## 4. Render y procedencia (`render.py`)

El banner de cuerpo y la línea `De` se eligen por `confianza`:

| confianza | banner cuerpo (.md) | línea en CORREOS_LECTURA |
|---|---|---|
| `alta-reconstruida` | `> RECONSTRUIDO DESDE CITA — remitente verificado por cabecera inline` | `**De (reconstruido):**` |
| `media-reconstruida` | `> AUTORÍA POR VERIFICAR — reconstruida de una cita; remitente por cabecera, sin autenticar` | `**De (reconstruido, por verificar):**` |

Frontmatter (campos ya en `model.py`, emitidos solo si set → 277 no churn):
`capa: B`, `confianza: media-reconstruida`, `reconstruido_desde_cita: true`,
`reconstruido_de: MSG-xxxxx`, `en_revision: true`, `fingerprint`, `procedencia`.

`corpus.py` ya emite `capa`/`confianza`/`fingerprint`/`reconstruido_desde_cita`/`en_revision`
→ sin cambios; los consumidores máquina pueden filtrar `confianza == "media-reconstruida"`.

## 5. Nuevo `_revision/reconstruidos.md` (checklist de verificación)

`render_revision` gana un cuarto fichero: tabla de los atoms `media-reconstruida` promovidos
(`MSG-id | remitente | fecha | asunto | reconstruido_de (portador) | extracto`) + su espejo
`reconstruidos.jsonl` para re-alertado idempotente. Es la lista de trabajo para cotejar cada
uno contra su `.eml` fuente. (`cola.md` deja de contener estos — ahora son atoms; pasan a esta
lista.)

## 6. Identidades vigiladas

Sin cambios de mecánica: `PersonaUno = {per01a@example.invalid, per01c@example.invalid}`,
`per01b@example.invalid` = candidata (tope media), `ignacio@despacho-ab.example` =
parte relacionada DISTINTA. Todo `media-reconstruida` con `de ∈ vigiladas/candidatas` se fuerza a
`del_burgo.md` además de promover.

## 7. Ficheros tocados (todo aditivo; salida capa A byte-idéntica)

- **`core/email_atomize/inline.py`**: rama `media-reconstruida` en `clasificar()`; promoción en
  `reconstruir()`; `en_revision` incluye `media-reconstruida`.
- **`core/email_atomize/render.py`**: banner + línea `De` por confianza; `render_revision` emite
  `reconstruidos.md`/`.jsonl`.
- **`core/email_atomize/pipeline.py`**: ninguna lógica nueva de promoción (fluye por `candidatos`);
  escribe el nuevo fichero de revisión.
- **`model.py` / `corpus.py` / `ids.py` / `dedup.py`**: **sin cambios** (campos y dedup ya
  soportan el caso).

## 8. Plan de tests

Puros (`tests/test_email_atomize_inline.py`):
1. `outlook_es` plano con `De:`+`Enviado:`+`Asunto:` y dirección válida, no estructural →
   `media-reconstruida`. (caso MSG-00021)
2. `fwd_line` `---- Forwarded ----` + bloque `From:`/`Date:` válido, no estructural →
   `media-reconstruida`. (casos PersonaUno/Tecnitasa)
3. Mismo bloque pero **solo nombre sin `<addr>`** → no promueve (`media`/`baja`).
4. Mismo bloque **sin fecha** → no promueve.
5. Fecha posterior al portador → `fecha_incoherente`, no promueve.
6. `ambiguedad_profundidad` (dos cabeceras apiladas levantadas del cuerpo) → no promueve.
7. Estructural + cabecera completa → sigue `alta-reconstruida` (no regresión del peldaño alto).

Glue (`tests/test_email_atomize_pipeline_b.py`):
8. Un `media-reconstruida` cuyo contenido ya existe como `.eml` limpio → **no duplica**, añade
   `procedencia` (dedup/fidelity-upgrade).
9. `reconstruidos.md`/`.jsonl` listan exactamente los promovidos.
10. Re-ejecución sobre `_registro.json` existente → 277 ids de capa A intactos; ids `fp` estables.
11. **Regresión**: los 277 `.md` de capa A byte-idénticos antes/después.

## 9. Verificación adversarial sobre datos reales (post-build)

Tras implementar, re-ejecutar `--ref W-02VND1` y:
1. **Auditar CADA `media-reconstruida`**: su `De:`/fecha aparece literalmente en el `.eml` fuente.
   Cero tolerancia a remitente fabricado.
2. **Cobertura**: los 36 del informe quedan (a) promovidos como `media-reconstruida`/`alta-reconstruida`,
   (b) resueltos por dedup contra `.eml` limpio, o (c) explícitamente diferidos a Gap 2 (los
   enterrados en reconstrucciones). Cuadrar la lista; cero desapariciones silenciosas.
3. **Idempotencia**: dos ejecuciones, diff de `_registro.json` → 0 renumerados, 0 fp duplicados,
   277 `.md` idénticos.
4. **PersonaUno / Ignacio**: revisar `del_burgo.md`; confirmar que PersonaDos nunca se
   pliega sobre PersonaUno.
5. Re-correr `scripts/audit_correos_no_separados.py`: el conteo de "sin atom" debe caer a los
   diferidos por Gap 2 (+ posibles casi-dups marcados), nada más.

## 10. Fuera de alcance — Gap 2 (diferido)

Correos enterrados DENTRO de un segmento ya reconstruido (anidamiento profundo; el motor no vuelve
a segmentar dentro de lo que reconstruye). Ejemplo: el reenvío interior Antoni 13-may 16:51 en
MSG-00306. **No se pierde prueba**: su reenvío exterior ya es MSG-00018 (auténtico) y el texto es
legible dentro de MSG-00306. El motor **no los detecta hoy** (no vuelve a segmentar dentro de lo
que reconstruye), así que NO se auto-listan en `_revision/`; el seguimiento provisional es
`scripts/audit_correos_no_separados.py`, que ya los identifica. Se atacarán en una spec posterior
con su propio diseño adversarial (es el vector de mayor riesgo de límite-de-cuerpo según la spec de
Layer B).

## 11. Riesgos residuales

- **Límite de cuerpo en lo no estructural**: la frontera viene de adyacencia; un reenvío con
  firma intercalada puede dejar texto de más/menos en el atom. Mitigación: banner "por verificar"
  + `reconstruidos.md` para cotejo humano; no se afirma `alta`.
- **Cobertura del parser de fechas ES/CA/EN** sigue siendo la puerta promover↔cola: un formato no
  soportado demota (seguro: más revisión, cero misatribución), pero baja el rendimiento.
- **Día-granular**: colisiones mismo-día se cazan por `cuerpo_sha` + `casi_duplicados.md`.
