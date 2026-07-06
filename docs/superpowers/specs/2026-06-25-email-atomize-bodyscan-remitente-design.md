# DISEÑO FINAL — Layer B: atribución de remitente desde el CUERPO de una cita (body-scan de remitente, iteración 2)

> Extensión de `core/email_atomize/inline.py`. Specs base: `docs/superpowers/specs/2026-06-25-email-atomize-layerb-design.md` (§3, §4, §11.6 — el body-scan es **el vector de mayor riesgo de misatribución del corpus**) y `2026-06-25-email-atomize-media-reconstruida-design.md` (peldaño `media-reconstruida`). Caso piloto W-02VND1; motor genérico. **Prime directive heredado: cero misatribución.** Recupera **hasta 28 segmentos** con `<addr>` literal en el cuerpo (11 forma a + 10 forma b + ≤7 forma c; cota superior — las (c') con nombre+`<addr>` envuelto quedan en cola, §6); los **48 sin `<addr>` siguen en cola** por construcción.

---

## 0. Contexto y decisión de base

### 0.1 Por qué hoy quedan en `de=""` (verificado contra el código)

Las 3 formas comparten causa: **la atribución vive DENTRO del cuerpo del segmento citado** (`seg.texto`), no en el anclaje que precede al contenedor (`seg.anclaje_texto`). En la rama HTML, `seg.anclaje_texto` es el `_pending_parts` previo al `<blockquote>` (un `gmail_attr` o prosa "Te reenvío"); la atribución Apple ("El … escribió:") y los bloques `De:/Fecha:` del reenvío Apple son la **primera línea del propio `<blockquote>`**, que cae en `seg.texto`. `parsear_anclaje(seg.anclaje_texto, …)` (línea 715) devuelve `None`, y el único puente actual del cuerpo, `_cabecera_head` (línea 312), exige un bloque `De:`/`From:` **contiguo al inicio** con `\S` tras los dos puntos (vía `_RE_DEFROM_LINE`, línea 279) — que (a)/(b) no son (atribuciones Apple) y (c) no cumple (valores envueltos en la línea siguiente: `De:\nper03@example.invalid`).

### 0.2 Hallazgo rector: el gap es de ROUTING, no de extracción

Verificado ejecutando los regex reales sobre las 3 formas:

- **`_RE_ADDR` (línea 121) ya des-envuelve la forma (b)**: `<\s*([^<>\s]+@[^<>\s]+)\s*>` tolera `\n` alrededor → `<\neva.pratpadros@…\n>` → `eva.pratpadros@…`. No hay que reparar la envoltura del `<addr>`.
- **`_RE_LABEL` (líneas 117-120) ya des-envuelve la forma (c)**: `:\s*(.*)$` con `\s` que incluye `\n` consume el salto y captura el valor de la línea siguiente. `_parse_label("De:\nper03@example.invalid\nFecha:\n27 de mayo de 2024\n…")` → `de="per03@example.invalid"`, `fecha_iso="2024-05-27"`.
- **`_parse_apple` (línea 213) ya parsea (a)** literalmente.
- **`_parse_label` indexa por etiqueta con `setdefault` (línea 198)**: `de = labels.get("de") or labels.get("from")`; el `<addr>` de `Para:/To:/Cc:` cae en claves distintas y **nunca** se usa como `de`. Esto neutraliza de raíz el robo del destinatario y el caso de orden invertido (`Para:` antes de `De:`).

**Conclusión: los parsers existentes ya extraen bien. La iteración solo decide CUÁNDO escanear, ACOTA el inicio del cuerpo y añade las guardas que los parsers no tienen.**

### 0.3 Decisión de base y grafts (síntesis de los 3 diseños y veredictos)

**Base elegida: Diseño 1 (minimal-hook)** — gana en cobertura, idempotencia y blast radius (toca solo `inline.py` + 2 ficheros de test; no toca el segmentador, `Segmento`, ni el invariante de conservación de tokens). Se descarta el **Diseño 2 (segmenter-level)** por su fallo fatal verificado: mover la atribución de `seg.texto` a `seg.anclaje_texto` en el segmentador rompe el invariante de conservación de tokens (líneas 574-575) y perturba `_cuerpo_sin_cabecera`/los fp ya congelados — mayor superficie sin cobertura adicional. Además su `_reparar_envoltura` es innecesaria (0.2).

Sobre la base D1 se graftan, para cerrar los fallos fatales señalados:

- **[Graft D3-G4]** Guarda de **>1 `<addr>` en la unidad de atribución Apple** → cola. Cierra ADVERSARIAL 2 (verificado en código: línea 219 coge el primer `<addr>` sin guarda).
- **[Graft D3-confianza]** **Topar SIEMPRE a `media-reconstruida` cuando el anclaje se levanta del cuerpo** (nunca `alta-reconstruida`). Cierra el hueco de D1: un blockquote estructural cuya primera línea sea una cita más profunda promovería a ALTA con el remitente equivocado. La frontera DOM autentica el LÍMITE del cuerpo, no el REMITENTE levantado de su interior.
- **[Fix al bug de conteo Apple de D1]** Contar atribuciones Apple apiladas con líneas que **terminan en `escribió:/wrote:/va escriure:` bajo `re.M`** (no `len(_RE_APPLE.findall)+…`, que da 2 para UNA forma (a) bien formada — falso negativo masivo, verificado).
- **[Fix al fallo latente del veredicto 1]** La guarda de apilamiento **cuenta sobre la vista des-envuelta del cabezal** (`_RE_DE_LABEL_ANY` ve los `De:` envueltos que `_n_cabeceras` no ve), blindado con un test de dos bloques (c) envueltos apilados.

Se **descarta el G9-mojibake de D3** como guarda dura de descarte: rechazaría correos E&V reales recuperables cuyo HTML→texto introdujo marcas de charset (pérdida de cobertura, advertida por veredicto 2). La defensa correcta ya existe: si el `<addr>` extraído está corrupto, `_email_valido` (línea 603) lo demota; un mojibake en prosa del cabezal no afecta a un `<addr>` limpio.

---

## 1. Algoritmo del body-scan

### 1.1 Enganche — un único punto, 5 líneas

En `reconstruir()` (líneas 715-722), un **tercer escalón de fallback** DESPUÉS de `_cabecera_head` y SOLO si seguimos sin remitente atribuible:

```python
anc = parsear_anclaje(seg.anclaje_texto or "", seg.estilo)
levantada_del_cuerpo = False
if anc is None:
    head = _cabecera_head(seg.texto)
    anc = _parse_label(head) if head else None
    levantada_del_cuerpo = anc is not None
# NUEVO — body-scan acotado: solo si seguimos sin REMITENTE atribuible.
if (anc is None or not anc.de) and seg.texto:
    anc_body = _atribucion_en_cuerpo(seg.texto)
    if anc_body is not None:
        anc = anc_body
        levantada_del_cuerpo = True   # gobierna confianza (§3) y ambigüedad (§2)
```

**Trigger por disyunción `anc is None OR not anc.de`** [base D1, validado por veredicto 2]: cubre tanto el anclaje vacío como el anclaje estructural que parseó SOLO fecha (`de=""`, `anc is not None`) — recall hole que un trigger `anc is None` solo se saltaría. Nunca pisa una atribución que ya dio `de` (G-prioridad: el anchor estructural legítimo gana).

`levantada_del_cuerpo=True` es load-bearing por partida doble: (i) alimenta la guarda de ambigüedad de profundidad heredada (línea 727); (ii) es la señal que topa la confianza a media-reconstruida (§3).

### 1.2 Función pura `_atribucion_en_cuerpo(texto: str) -> Anclaje | None`

Constantes nuevas en `inline.py`:

```python
_RE_FWD_INTRO = re.compile(
    r"(?im)^\s*(?:inicio del mensaje reenviado|begin forwarded message"
    r"|---+\s*(?:mensaje reenviado|forwarded message|mensaje original|original message))\s*:?\s*$")
_RE_DE_LABEL_ANY = re.compile(r"(?im)^\s*(?:de|from)(?:\s+el)?\s*:")  # ve 'De:' AUNQUE el valor vaya envuelto
_RE_APPLE_FIN_M  = re.compile(r"(?im)(?:escrib(?:i[oó])|wrote|va\s+escriure)\s*:\s*$")  # conteo correcto (re.M)
_MAX_LINEAS_SCAN = 16  # ventana del INICIO; (c) con cabecera completa envuelta cabe (ver §6 calibración)
```

Pasos:

1. **Pre-filtro G1 (sin `<addr>` → jamás).** `if not _RE_ADDR.search(texto): return None`. Aborta los 48 antes de toda inferencia.

2. **Acotar al INICIO.** `lines = texto.splitlines()`; saltar líneas en blanco; saltar **una sola** línea-intro de reenvío si matchea `_RE_FWD_INTRO`, y los blancos que la sigan. Si tras consumir esa única intro siguen apareciendo más marcadores antes del bloque → no contiguo → más adelante caerá por unicidad. `cabeza = "\n".join(lines[i : i + _MAX_LINEAS_SCAN])`. **Solo se escanea esta ventana**, nunca el cuerpo entero — impide cazar la atribución de un mensaje citado más profundo que aparezca más abajo en el mismo `seg.texto`. Trade-off deliberado: preferimos un falso negativo (más cola) a un falso positivo (misatribución de nivel).

3. **Guarda de unicidad / anti-apilamiento (G3) — PRIMERO, sobre la vista des-envuelta** [fix fallo latente]:
   ```python
   n_apple = len(_RE_APPLE_FIN_M.findall(cabeza))       # 1 para UNA forma (a); ≥2 = apiladas
   n_de    = len(_RE_DE_LABEL_ANY.findall(cabeza))      # ve 'De:' envueltos (c) que _n_cabeceras NO ve
   if (n_apple + n_de) > 1:
       return None                                       # varias atribuciones apiladas → AMBIGUO → cola
   ```
   `_RE_DE_LABEL_ANY` cuenta sobre la `cabeza` literal: como NO exige `\S` tras `:`, ve tanto `De: x` como `De:\nx` — cierra el punto ciego de `_n_cabeceras`/`_cabecera_head`. La coordinación "des-envolver/contar antes de parsear" es aquí trivial porque la cabeza es texto crudo y el conteo es por línea-etiqueta, no por valor; el test §5.5 lo blinda explícitamente.

4. **Distinguir forma y parsear** (orden importa; replica `parsear_anclaje` sobre la cabeza acotada):
   - **(a)/(b) — Apple:** `anc = _parse_apple(cabeza)`. `_parse_apple` ya exige estructura (`_RE_APPLE` "El/On…" o línea acabada en `escribió:/wrote:`). 
     **Guarda G4 [graft D3] — >1 `<addr>` en la línea de atribución:** localizar la línea de atribución (la que matchea `_RE_APPLE`/`_RE_ATTR_FIN`); si `len(_RE_ADDR.findall(linea_atribucion)) > 1` → `return None`. Cierra ADVERSARIAL 2 (remitente + destinatario en la misma línea Apple).
   - **(c) — bloque De:/Fecha:/Asunto::** si `_parse_apple` da `None`, `anc = _parse_label(cabeza)`. La des-envoltura la hace `_RE_LABEL`; el remitente sale solo de la clave `de`/`from` (G5, §2).
   - `anc = _parse_apple(cabeza) [con G4] or _parse_label(cabeza)`.

5. **Exigir remitente real (G5/G1).** Si `anc is None` o `not anc.de` → `None`. El body-scan **nunca** devuelve un Anclaje sin `de`: reserva el escalón a "hay `<addr>` literal ligado al remitente", manteniendo la promesa de los 48.

6. Devolver el `Anclaje`. La elección del `<addr>` correcto está garantizada por: (i) ventana acotada al primer mensaje; (ii) G4 (una sola dirección en la unidad Apple); (iii) `_parse_label` lee el `<addr>` SOLO de la clave `de`/`from`, jamás de `para`/`to`/`cc`.

---

## 2. Guardas anti-misatribución

Todas dentro de `_atribucion_en_cuerpo` salvo las heredadas; cualquiera que dispare → `_atribucion_en_cuerpo` devuelve `None` → el segmento sigue con `de=""` → `clasificar(None,…)` → `baja, sin_cabecera` → puntero a `_revision/cola.md` (comportamiento actual, sin cambio).

| # | Guarda | Forma | Manda a cola cuando | Estado |
|---|---|---|---|---|
| **G1** | Sin `<addr>` literal | todas | `_RE_ADDR.findall(texto)` vacío → **los 48** | innegociable (prime directive 1; restricción 7) |
| **G2** | No contigua / ventana | a/b/c | la atribución no está en la ventana del inicio (tras blancos + ≤1 intro de reenvío); cita anidada profunda | acotación §1.2-2 |
| **G3** | Apilamiento (>1 atribución) | a/b/c | `n_apple + n_de > 1` sobre la vista des-envuelta (`_RE_APPLE_FIN_M` con `re.M` + `_RE_DE_LABEL_ANY` que ve envueltos) | **fix bug conteo D1 + fix fallo latente veredicto 1** |
| **G4** | >1 `<addr>` en la línea Apple | a/b | la línea de atribución tiene 2 `<addr>` (remitente+destinatario) | **graft D3 — cierra ADVERSARIAL 2** |
| **G5** | `de` vacío / destinatario | c | `De:`/`From:` sin `<addr>` propio (solo nombre, o el `<addr>` solo en `Para:/Cc:`) → `anc.de==""` | estructural vía `_parse_label` (línea 199) |
| **G6** | Ambigüedad de profundidad (heredada) | a/b/c | `_n_cabeceras(seg.texto) > 1 and (levantada_del_cuerpo or not estructural)` (línea 727) — 2ª red sobre G3 para bloques no-envueltos en TODO el cuerpo | heredada, intacta |
| **G7** | Fecha posterior al portador (heredada) | todas | `clasificar` (líneas 628-630) → `media, fecha_incoherente`; nunca alta | heredada, intacta |
| **G8** | Identidad candidata (heredada) | todas | `anc.de ∈ identidades.candidatas` (línea 730) → tope `media` + `del_burgo.md` | heredada, intacta |

**Por qué no G9-mojibake:** descartado (0.3). Un `<addr>` limpio en un cabezal con mojibake en prosa es recuperable y seguro; un `<addr>` corrupto ya lo demota `_email_valido` → `clasificar` da `media`/`baja`. Añadir G9 cuesta cobertura E&V real sin ganar seguridad.

**Doble red sobre el punto ciego de `_n_cabeceras`:** G3 (`_RE_DE_LABEL_ANY`) caza envueltos en la VENTANA; G6 (`_n_cabeceras`) caza no-envueltos en TODO el cuerpo. Riesgo residual: dos atribuciones envueltas separadas por >16 líneas → la ventana solo ve la primera; G6 es ciego a envueltos → se atribuye al PRIMER mensaje. Esto es correcto (primer mensaje de un reenvío encadenado) y coherente con que el body-scan atribuye SIEMPRE al primer mensaje de la ventana (los enterrados son Gap 2, §6).

---

## 3. Confianza e integración con los peldaños

**No se crea peldaño nuevo. No se toca la firma de `clasificar`.** El `Anclaje` del body-scan entra al `clasificar(anc, m_a.fecha_iso, estructural=…, ambigua=…)` existente (línea 728). Pero se aplica una **guarda dura de honestidad** [graft D3], porque una atribución levantada del cuerpo tiene las dos propiedades de un `media-reconstruida` —remitente fiable (de un `<addr>` literal) + **límite de cuerpo por adyacencia, no autenticado por estructura DOM**— y por tanto NO debe poder subir a `alta-reconstruida` aunque el segmento sea estructural:

```python
conf, motivo = clasificar(anc, m_a.fecha_iso, estructural=seg.estructural, ambigua=ambigua)
# Atribución levantada del cuerpo: el límite de cuerpo no está autenticado por estructura.
# Nunca alta-reconstruida; tope media-reconstruida (cierra el hueco blockquote-DOM-con-cita-interior).
if levantada_del_cuerpo and conf == "alta-reconstruida":
    conf, motivo = "media-reconstruida", "atribucion_cuerpo"
```

Esto **subsume y refuerza** el fallback `_cabecera_head` preexistente (que también levanta del cuerpo y hoy puede subir a alta): a partir de esta iteración, **todo lo levantado del cuerpo topa a media-reconstruida**, coherente y más seguro. El `motivo="atribucion_cuerpo"` da trazabilidad del origen en `corpus.jsonl`/frontmatter.

Resultado por caso:
- **Anclaje estructural legítimo (gmail_attr/html_quote con `de`)** → intacto, `alta-reconstruida` posible (no se levantó del cuerpo).
- **Body-scan recuperado** → `media-reconstruida` (`atribucion_cuerpo`), `en_revision=True`, banner "AUTORÍA POR VERIFICAR", → `res.candidatos` → atom B propio en `reconstruidos.md` para cotejo.
- **Ambigua / sin fecha / email inválido / fecha incoherente** → `media`/`baja` → cola.
- **Tope inferior respetado:** si `clasificar` devuelve algo < media-reconstruida (p.ej. `media, fecha_incoherente`), se respeta; la guarda solo degrada alta→media-reconstruida, nunca redondea hacia arriba.

Routing y capping de identidad **sin cambios**: línea 730 (candidata→media), líneas 750-751 (`en_revision` para vigiladas + media/baja/media-reconstruida), 752-758 (candidatos vs punteros). `PersonaUno` candidato sigue capado y forzado a `del_burgo.md`. `render.py`/`corpus.py` ya rotulan `media-reconstruida` — **cero churn**.

---

## 4. Idempotencia y Capa A byte-idéntica

- **Capa A byte-idéntica.** `_atribucion_en_cuerpo` vive SOLO en `reconstruir()` (rama Layer B). No toca `_construir_mensaje`, `bodies.extraer_cuerpo`, `_segmenter.cortar_autor`, ni el render de Capa A. Los 277 `.md` quedan byte-idénticos (regresión obligatoria, test existente en `test_email_atomize_regresion*.py`).
- **`seg.texto` no se reescribe.** A diferencia de D2, el body-scan no mueve texto entre `anclaje_texto` y `texto` ni perturba el invariante de conservación de tokens. `seg.texto = _cuerpo_sin_cabecera(seg.texto)` (línea 739) se ejecuta igual; para (a)/(b)/(c) `_cabecera_head(seg.texto)` es `None` → devuelve el texto íntegro, así que la atribución queda DENTRO del cuerpo del atom. Es lo correcto para forensic-conservative: el lector ve literalmente la cabecera de la que se extrajo el remitente.
- **Fingerprint determinista.** `fingerprint_b(anc, normaliza_cuerpo(seg.texto))` (línea 748): `de`/`fecha_iso`/`asunto` salen de regex deterministas sobre el mismo `seg.texto`; `normaliza_cuerpo` colapsa whitespace, así que el wrap físico del `<addr>` no altera el hash. El conteo/parseo de la cabeza opera sobre una vista local, NO entra al fingerprint. Re-ejecutar asigna el mismo `fp` → `msg_id_for_fp` congela el id → **cero renumeración**. `sorted(candidatos, key=fingerprint)` (pipeline línea 184) es estable bajo `pytest-randomly`.
- **Dedup/upgrade.** `idx.resolver(seg)` (línea 678) sigue puenteando a un `.eml` limpio de Capa A por `rfc_message_id` o `cuerpo_sha` — sin cambios. Riesgo residual conocido: como la atribución queda dentro del cuerpo (no se poda), el `cuerpo_sha` puede no casar con el `.eml` limpio → upgrade fallido → `casi_duplicados.md`. **Miss, no misatribución.** Atacable en iteración posterior extendiendo `_cabecera_head`/`_cuerpo_sin_cabecera` para reconocer atribuciones Apple, con su propia regresión de Capa A — fuera de alcance aquí.

---

## 5. Plan de tests

**Puros — `tests/test_email_atomize_inline.py`** (fixtures con el texto literal de las 3 formas; patrón §14 de la casa). Sobre `_atribucion_en_cuerpo` directamente:

1. **(a) Apple en línea:** `"El 27 may 2024, a las 10:49, PersonaCinco <persona.cinco@engelvoelkers.com> escribió:\ncuerpo…"` → `de="persona.cinco@…"`, `fecha_iso="2024-05-27"`.
2. **(b) `<addr>` envuelto:** `"El 4 oct 2024, a las 11:48, PersonaCuatro, Eva <\npersona.cuatro@engelvoelkers.com\n> escribió:\ncuerpo…"` → `de="eva.pratpadros@…"`, `fecha_iso="2024-10-04"`.
3. **(c) bloque envuelto con intro:** `"Inicio del mensaje reenviado:\n\nDe:\nper03@example.invalid\nFecha:\n27 de mayo de 2024, 10:38:07 CEST\nPara: \"PersonaCinco, Isabel\" <persona.cinco@engelvoelkers.com>\nAsunto: x"` → `de="per03@example.invalid"` (**NO** el del `Para:`), `fecha_iso="2024-05-27"`.
4. **G5 robo de destinatario:** (c) cuyo `De:` no lleva `<addr>` (solo nombre) pero `Para:` sí → `None`.
5. **G3 apilamiento envuelto (blinda el fallo latente del veredicto 1):** cabeza con **dos** bloques `De:\nvalor` envueltos apilados → `None`. Verifica que el conteo (`_RE_DE_LABEL_ANY`) ve los envueltos.
6. **G3 conteo Apple correcto (blinda el bug de D1):** UNA sola forma (a) bien formada → NO se descarta (sí recupera); DOS atribuciones Apple apiladas → `None`.
7. **G4 dos `<addr>` en la línea Apple (ADVERSARIAL 2):** `"El … , Isabel <a@x> escribió:"` con un segundo `<dest@y>` en la misma línea → `None`.
8. **G2 ventana:** atribución válida más allá de la línea 16 (precedida de prosa larga) → `None`.
9. **G1 los 48:** bloque con `De:` solo-nombre, sin `<addr>` en ninguna etiqueta → `None`.
10. **Sin estructura:** email suelto en prosa sin "El…/escribió:" ni `De:` → `None`.

Integración en `reconstruir` (sección T9):

11. **Enganche (a) en blockquote HTML, anclaje previo es prosa** → candidato `media-reconstruida` (`atribucion_cuerpo`) con `de` correcto (hoy daría `de=""`/cola). **Verifica el graft de confianza: NO sube a alta pese a ser estructural.**
12. **Trigger por disyunción:** anclaje estructural con SOLO fecha (`de=""`, `anc is not None`) y `<addr>` en el cuerpo → body-scan dispara, recupera `de`. (Recall hole que un trigger `anc is None` se saltaría.)
13. **Prioridad anchor:** gmail_attr con `de` válido + atribución en cuerpo → gana el gmail_attr, body-scan no se invoca.
14. **G3 a nivel `reconstruir`:** dos cabeceras `De:` envueltas apiladas en el cuerpo → no promueve (punteros).

**Glue — `tests/test_email_atomize_pipeline_b.py`:**

15. Pipeline completo, portador forma (a) → atom B `media-reconstruida` con `de` correcto; `corpus.jsonl` lo refleja con `motivo="atribucion_cuerpo"`; aparece en `_revision/reconstruidos.md`.
16. **Dedup contra `.eml` limpio:** si la cita coincide con un `.eml` de Capa A → upgrade vía `idx.resolver`, no se acuña duplicado.
17. **Idempotencia:** dos corridas → 0 renumerados, fp estables, **277 Capa A `.md` byte-idénticos** (extiende el test de regresión existente).
18. **Regresión del peldaño alto:** estructural + cabecera completa en `anclaje_texto` (no levantada del cuerpo) sigue `alta-reconstruida` — el graft solo topa lo levantado del cuerpo.

**Caso real W-02VND1 (verificación adversarial post-build, NO en CI):** re-ejecutar `python -m scripts.atomize_emails --ref W-02VND1` y auditar manualmente los tres MSG citados — **MSG-00023** (forma a, Apple `<addr>` en línea), **MSG-00035** (forma b, `<addr>` envuelto), **MSG-00305** (forma c, bloque De: envuelto tras "Inicio del mensaje reenviado:"). Confirmar, con tolerancia cero a misatribución: (i) cada uno promueve con el `de` que aparece LITERALMENTE en el `.eml` fuente; (ii) ninguno coge el `<addr>` del `Para:`; (iii) los 48 sin `<addr>` siguen en `cola.md`; (iv) el conteo de `de=""` baja de 76 a ≤48; (v) cuadrar contra `scripts/audit_correos_no_separados.py` (nada desaparece en silencio). **Calibrar `_MAX_LINEAS_SCAN`** contra los 7 casos reales de forma (c): si alguno con cabecera completa (`De/Fecha/Para/Cc/Cco/Asunto` envueltos) se trunca, subir el límite; **nunca a "cuerpo entero"**.

---

## 6. Alcance — qué queda fuera

- **Los 48 segmentos sin `<addr>` literal.** Quedan en cola por G1; recuperarlos exigiría inferir remitente sin dirección literal → viola el prime directive. Fuera de alcance, definitivo.
- **Gap 2 — atribuciones enterradas más profundas que la primera de la ventana** (cita anidada dentro de lo ya citado, o segunda atribución envuelta separada por >16 líneas). El body-scan atribuye SIEMPRE al primer mensaje de la ventana; los enterrados no se re-segmentan. Coherente con §10 de la spec `media-reconstruida`. Diferido.
- **Sub-forma (c') `De:` ↵ Nombre ↵ `<addr>` envuelto** (verificado: `_parse_label` captura el NOMBRE como valor del `De:` y el `<addr>`, dos líneas más abajo, no se alcanza → `de=""` → G5 → cola). Es un **miss seguro** (no misatribución), coherente con la filosofía forensic-conservative. Por eso los **28 son cota superior**: la recuperación real es el subconjunto de los 7 de forma (c) que llevan el `<addr>` DESNUDO en la línea siguiente al `De:` (no precedido de un nombre). Recuperar (c') exige un lookahead "si el valor del `De:` es un nombre sin `@`, buscar el `<addr>` en las líneas siguientes hasta la próxima etiqueta" — diferido a una iteración posterior con su propia guarda (¿de quién es ese `<addr>`?).
- **MSG-00305 interior / recall de cita anidada.** Doblemente fuera: su cabecera es (c') Y está anidada dentro de una reconstrucción (Gap 2). Spec separado posterior (junto con recall MSG-00018 + OCR, ya marcado como diferido en memoria del proyecto).
- **Fidelity-upgrade reforzado.** Que el `cuerpo_sha` del atom recuperado case con el `.eml` limpio (hoy falla porque la atribución queda en el cuerpo). Requiere tocar `_cabecera_head`/`_cuerpo_sin_cabecera` con su propia regresión de Capa A. Iteración posterior.
- **G9-mojibake como descarte duro.** Descartado por coste de cobertura (0.3, §2); la validación de `<addr>` ya cubre el riesgo real.

---

**Ficheros a tocar:** SOLO `core/email_atomize/inline.py` (función pura nueva `_atribucion_en_cuerpo` + 4 constantes + ~6 líneas de enganche en `reconstruir` + ~3 líneas del graft de confianza) y los dos ficheros de test (`tests/test_email_atomize_inline.py`, `tests/test_email_atomize_pipeline_b.py`). **Cero cambios** en `model.py`, `clasificar` (firma), `pipeline.py`, `render.py`, `corpus.py`, `dedup.py`, `ids.py`, el segmentador, `Segmento`, o la Capa A.
