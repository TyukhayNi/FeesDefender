# DISEÑO FINAL — Layer B it.3: promoción del INTERIOR REENVIADO + parse c′ (Gap 2)

> Extensión de `core/email_atomize/inline.py`. Specs base: `2026-06-25-email-atomize-layerb-design.md`,
> `2026-06-25-email-atomize-media-reconstruida-design.md` y `2026-06-25-email-atomize-bodyscan-remitente-design.md`
> (it.2; su §6 difiere **explícitamente** c′ y Gap 2 — esta spec los cierra dentro de un alcance acotado).
> Caso piloto W-02VND1; motor genérico. **Prime directive heredado: cero misatribución.**
> Diseño sintetizado por workflow adversarial (3 diseños independientes × 3 jueces; todos REWORK ≈6.7) +
> verificación sobre datos reales. Esta spec incorpora los *grafts* que cerraron los fallos fatales hallados.

---

## 0. Contexto y decisión de base

### 0.1 Qué queda sin recuperar hoy (verificado sobre W-02VND1 y el código)

El motor (it.2) atribuye **la primera atribución de la ventana** de un segmento y **NO re-segmenta lo que
reconstruye**. Cuando el cuerpo de un segmento ya reconstruido contiene **un correo REENVIADO** con su propia
cabecera, ese interior:

1. Queda **sin atom propio** (vive enterrado dentro del `.md` del exterior).
2. Su cabecera suele ser **forma c′** (el valor del `De:` es un **nombre** o está **vacío/bare** y el `<addr>`
   del remitente va **envuelto** en líneas siguientes), que el parser actual no liga (→ `de=""`).

**Medición real (read-only, cruzada contra el corpus del motor, no contra la auditoría tolerante):** el filón
recuperable son **~5-7 correos c′ genuinos**, casi todos de **PersonaUno / PersonaDos** — la autoría
enterrada es el payoff del levantamiento del velo —, más el **testigo MSG-00305** (Eva→Consulado de [PAIS_EXTRANJERO],
7-jul, *Re: offer letter TIBIDABO 8*, con la **Contraoferta**). La cifra exacta de atoms net-new **solo se sabe
tras construir** (dedup por `cuerpo_sha` del motor; las claves `(de,fecha)`/`(de,asunto)` infra- y sobre-cuentan
por colisión de hilo).

### 0.2 Forma real de las cabeceras interiores (verificado, literal de los `.eml`)

Patrón universal tras un **marcador de reenvío explícito**:

```
---------- Forwarded message ---------          (o "----\xa0Mensaje reenviado\xa0---------")
De:                                              ← etiqueta bare
PersonaUno                                  ← NOMBRE en línea propia
<                                                ← '<' en línea propia
per01a@example.invalid                                  ← <addr> en línea propia (envuelto)
>                                                ← '>' en línea propia
Date: / Fecha: ...                               ← PRIMERA etiqueta tras el valor del De:
Subject: / Asunto: ...
To: / Para: Eva <eva.pratpadros@…>, …            ← destinatarios (CON sus <addr>)
Cc: …
<cuerpo del interior: "Muy Sras mías:", "Buenas tardes,", "Estimada PersonaSiete", …>
```

**Hallazgo rector que de-riesga la misatribución:** el `<addr>` del **remitente** está SIEMPRE en las líneas
**inmediatamente posteriores al `De:` y ANTES de la primera etiqueta `Date:/Fecha:`**. Los `<addr>` de
**destinatario** (`To:/Para:/Cc:`) viven **después** de `Date:/Subject:`. Por tanto, una **franja acotada
`De:`→primera-etiqueta** aísla al remitente y deja fuera a los destinatarios **por construcción**.

### 0.3 Decisión de alcance (Nikolai) y síntesis de los 3 diseños

- **Alcance:** FOCO en **promoción del interior reenviado + parse c′**, **acotado por marcador de reenvío
  EXPLÍCITO**. La **recursión profunda** en cadenas Apple `El…escribió:` apiladas queda **FUERA** (§6). Solo
  **UN** nivel de desanidado por marcador.
- **Base elegida:** *minimal-hook* (Diseño 1) — emite **UN `Segmento` sintético** adicional para el interior y
  lo añade a `res.candidatos`; el pipeline `_pase_layer_b` lo deduplica por `fingerprint` y le acuña id **sin
  un solo cambio**. No toca el segmentador, `Segmento`, `clasificar` (firma), ni el pipeline.
- **Grafts integrados (cierran los fallos fatales del panel):**
  - **[G-CAPTURA]** Capturar `texto_exterior_original = seg.texto` **al inicio** del bucle `for seg` (antes de
    `_RE_INLINE_MID`/`_cuerpo_sin_cabecera` de la línea ~828-830). El desanidado lee SIEMPRE esa copia pre-poda.
  - **[G-FRANJA-ACOTADA]** El lookahead c′ liga el `<addr>` **solo** a la franja `De:`→primera-etiqueta-genérica,
    con **tope obligatorio** (si no aparece una etiqueta que cierre la franja dentro de la ventana → rechazo) y
    **unicidad** (exactamente 1 `<addr>` en la franja). Cierra robo de `Para/Cc` y robo por etiqueta intermedia
    no reconocida (`Reply-To:`/`Responder a:`/`Destinatario:`).
  - **[G-DELEGACION]** Rechazo si la franja contiene una fórmula de delegación (`en nombre de` / `on behalf of`
    / `via `) entre el nombre y el `<addr>` (cierra el único ataque (v) que sobrevivió en el panel).
  - **[G-PODA-c′]** **Poda dedicada** de la cabecera interior (NO reutilizar `_cuerpo_sin_cabecera`, que falla en
    c′ porque `_cabecera_head` exige `De:\S`). Garantiza `cuerpo_sha` estable entre los N portadores redundantes.
  - **[G-NO-DUPLICAR-EXTERIOR]** No emitir el interior si `(anc_i.de, anc_i.fecha_iso) == (seg.de, seg.fecha_iso)`
    del exterior (mismo mensaje). Usa **identidad de mensaje (de+fecha)**, **NO** `de`-inequality (que mataría el
    testigo: Eva reenvía su propio correo → exterior=Eva 23-jul, interior=Eva 7-jul, **misma de, distinta fecha**).
  - **[G-APILAMIENTO]** (heredado it.2) en la ventana del interior: `n_apple + n_de > 1 → None`. Garantiza UN
    nivel; manda a cola los casos apilados (p.ej. "Reconocimiento de cliente" con 2 `De:` en ventana).
  - **[G-AMBIGUA-INTERIOR]** `ambigua = _n_cabeceras(cuerpo_interior) > 1` al clasificar el interior (defensa en
    profundidad barata, hereda G6 sobre el propio cuerpo del interior).

---

## 1. Algoritmo

### 1.1 Constantes nuevas en `inline.py`

```python
# Marcador de reenvío EXPLÍCITO, line-anchored, tolerante a guiones/nbsp de cierre y forma bare.
# (El _RE_FWD_INTRO de it.2 FALLA con "---------- Forwarded message ---------" por los guiones de cierre.)
_RE_FWD_MARK = re.compile(
    r"(?im)^[\s\-]*(?:inicio del mensaje reenviado|begin forwarded message|forwarded message"
    r"|mensaje reenviado|mensaje original|original message)[\s\-:]*$")

# Etiqueta GENÉRICA (incluye Reply-To/Responder a/Destinatario/…): cierra la franja del remitente.
# Acotada a 1-30 chars de "palabra" + ':' para no tragar el cuerpo; NO casa el bare "De:" del propio inicio
# porque la franja arranca en de_idx+1.
_RE_GEN_LABEL = re.compile(r"(?im)^\s*[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 ._-]{0,30}:")

# Fórmula de delegación: el <addr> NO es del autor nombrado.
_RE_DELEGACION = re.compile(r"(?i)\b(?:en nombre de|on behalf of|via|p\.?\s*p\.?|por orden de)\b")
```

`_MAX_LINEAS_SCAN = 16` (heredado) gobierna la ventana del interior tras el marcador.

### 1.2 Lookahead c′ — `_addr_remitente_cprime(lines, de_idx) -> tuple[str, str]`

Liga el `<addr>` del remitente a la franja `De:`→primera-etiqueta. Devuelve `("", "")` ante cualquier duda.

1. `tope = de_idx + 1; while tope < len(lines) and not _RE_GEN_LABEL.match(lines[tope]): tope += 1`.
2. **[G-FRANJA tope obligatorio]** `if tope == len(lines): return "", ""` (sin etiqueta que cierre la franja
   → la franja se tragaría el cuerpo → rechazo; el `<addr>` real va seguido de `Date:/Fecha:`).
3. `franja = "\n".join(lines[de_idx:tope])` (la línea `De:` + nombre + `<` + addr + `>`).
4. **[G-DELEGACION]** `if _RE_DELEGACION.search(franja): return "", ""`.
5. `addrs = _RE_ADDR.findall(franja)`; **[G-UNICIDAD]** `if len(addrs) != 1: return "", ""`
   (0 = solo nombre → cola; >1 = ambiguo → cola). `_RE_ADDR` ya des-envuelve `<\n addr \n>`.
6. `de = addrs[0].lower()`. `de_nombre` = el texto de la franja ANTES del `<` (une las líneas de nombre,
   strip de comillas y de la etiqueta `De:`), reutilizando la lógica de `_addr_o_nombre`/`_parse_apple`.
7. `return de, de_nombre`.

### 1.3 Poda dedicada de la cabecera interior — `_cuerpo_interior(lines, de_idx) -> str`

`_cuerpo_sin_cabecera` NO sirve (su `_cabecera_head` exige `_RE_DEFROM_LINE = De:\s*\S`, que c′ bare no cumple),
y un fallo de poda parte el `cuerpo_sha` entre los 14 portadores redundantes (→ N atoms en vez de 1). Poda
explícita, tolerante a valores envueltos, **con set de etiquetas CONOCIDAS** (`_RE_ANYLABEL`, no genérico — para
no tragar saludos como "Muy Sras mías:" que terminan en `:`):

1. Desde `de_idx`, consumir el bloque de cabecera contiguo: una línea pertenece a la cabecera si
   (a) matchea `_RE_ANYLABEL` (etiqueta conocida), o (b) es un **fragmento de valor envuelto**: stripped ∈ {`<`,
   `>`}, o matchea `^<?\s*[^@\s]+@[^@\s]+\s*>?,?$` (email bare/bracketed, posible coma de lista), o **termina en
   `<`** (línea de destinatario partida: `To: Eva <`), o es una **línea de nombre** (≤6 palabras, sin
   puntuación de frase) **seguida en ≤2 líneas** por un patrón `<`+email.
2. La cabecera termina en la primera línea que **no** cumpla (a) ni (b) = inicio del cuerpo prosa.
3. `return "\n".join(lines[fin_cabecera:]).strip()`.

La poda opera sobre la misma ventana en todos los portadores → el wrap físico distinto colapsa bajo
`normaliza_cuerpo` (que ya colapsa whitespace) → **`cuerpo_sha` estable** → dedup correcta.

### 1.4 Extracción del interior — `_interior_reenviado(texto: str) -> tuple[Anclaje, str] | None`

Función pura. Devuelve `(Anclaje_del_interior, cuerpo_del_interior)` o `None`.

1. **[G-MARK]** `m = _RE_FWD_MARK.search(texto)`; si `None → None`. **Marcador explícito obligatorio**: sin él
   NO se desanida (cierra el riesgo de re-segmentar prosa citada).
2. **Ventana acotada:** desde la línea **siguiente** al marcador, saltar blancos; `vent = lines[i : i+_MAX_LINEAS_SCAN]`.
   Solo se escanea la ventana (no el cuerpo entero) — impide cazar un reenvío más profundo.
3. **[G-APILAMIENTO]** `if len(_RE_APPLE_FIN_M.findall(cab)) + len(_RE_DE_LABEL_ANY.findall(cab)) > 1: return None`
   (cab = `"\n".join(vent)`). Varias atribuciones en ventana → ambiguo → cola (garantiza 1 nivel, no recursión).
4. **Parsear cabecera del interior:**
   - **Apple** (`_RE_APPLE.search(cab)` o línea `…escribió:`): `anc = _parse_apple(<unidad>)` (con G4 unicidad
     heredada). [cubre interiores Apple tras marcador, si los hubiera.]
   - **Bloque De:/Fecha:** `anc = _parse_label(cab)` (ya da fecha/asunto correctos). Si `anc.de == ""` (c′):
     localizar `de_idx` (1ª línea `_RE_DE_LABEL_ANY` de `vent`); `de, de_nombre = _addr_remitente_cprime(vent, de_idx)`;
     si `de`, fijar `anc.de = de`, `anc.de_nombre = de_nombre`.
5. **[G5]** Si `anc is None or not anc.de → None` (NUNCA se afirma remitente sin `<addr>` literal ligado).
6. `cuerpo = _cuerpo_interior(vent, de_idx)` (o, en rama Apple, podar la unidad de atribución).
   Si `not cuerpo.strip() → None` (no hay cuerpo separable).
7. `return anc, cuerpo`.

### 1.5 Enganche en `reconstruir()`

```python
for seg in seg_total.ancestros:
    texto_exterior_original = seg.texto          # [G-CAPTURA] ANTES de cualquier poda
    ...  # (it.2 intacto: parsear_anclaje / _cabecera_head / _atribucion_en_cuerpo, clasificar, tope, poda,
         #  fingerprint, en_revision, append a res.candidatos|res.punteros del EXTERIOR — sin cambios)
    # --- NUEVO it.3: desanidar UN interior reenviado del cuerpo del exterior ---
    inter = _interior_reenviado(texto_exterior_original)
    if inter is not None:
        anc_i, cuerpo_i = inter
        # [G-NO-DUPLICAR-EXTERIOR] el interior no es el MISMO mensaje que el exterior (de+fecha)
        if not (anc_i.de == seg.de and anc_i.fecha_iso == seg.fecha_iso):
            ambigua_i = _n_cabeceras(cuerpo_i) > 1                       # [G-AMBIGUA-INTERIOR]
            conf_i, mot_i = clasificar(anc_i, m_a.fecha_iso, estructural=False, ambigua=ambigua_i)
            if conf_i == "media-reconstruida":
                mot_i = "interior_reenviado"
            if conf_i == "alta-reconstruida":      # imposible con estructural=False; defensivo
                conf_i, mot_i = "media-reconstruida", "interior_reenviado"
            # identidad candidata: hereda el cap a media + ruta del_burgo (sin cambios de routing)
            if anc_i.de in identidades.candidatas and conf_i == "media-reconstruida":
                conf_i, mot_i = "media", "identidad_candidata"
            seg_i = Segmento(
                texto=cuerpo_i, estilo="interior_reenviado", estructural=False,
                profundidad=seg.profundidad + 1, de=anc_i.de, de_nombre=anc_i.de_nombre,
                fecha_iso=anc_i.fecha_iso, asunto=anc_i.asunto, confianza=conf_i, motivo=mot_i,
                portador_msg_id=m_a.msg_id)
            mm_i = _RE_INLINE_MID.search(cuerpo_i)
            seg_i.rfc_message_id = mm_i.group(1).strip() if mm_i else ""
            cuerpo_norm_i = normaliza_cuerpo(cuerpo_i)
            seg_i.cuerpo_sha = cuerpo_sha_de(cuerpo_norm_i)
            seg_i.fingerprint = fingerprint_b(anc_i, cuerpo_norm_i)
            seg_i.en_revision = True               # SIEMPRE en revisión (interior por verificar)
            if conf_i in ("alta-reconstruida", "media-reconstruida"):
                res.candidatos.append(seg_i)
            else:
                res.punteros.append(SegmentoEnterrado(
                    portador_msg_id=m_a.msg_id, estilo="interior_reenviado",
                    profundidad=seg.profundidad + 1, de=seg_i.de, fecha_iso=seg_i.fecha_iso,
                    confianza=conf_i, motivo=mot_i, extracto=(cuerpo_i or "")[:200],
                    fingerprint=seg_i.fingerprint))
```

**Por qué no hay doble emisión con it.2:** `_atribucion_en_cuerpo` NO reconoce los marcadores nuevos
(`_RE_FWD_INTRO` falla con los guiones de cierre) y sus parsers fallan en la ventana liderada por el marcador
(c′ → `de=""`; Apple necesita `^El/On`). Verificado: en todos los casos reales it.2 devolvió `None` para estos
interiores. Aun así, **[G-NO-DUPLICAR-EXTERIOR]** cubre el caso teórico (y los 6 `fwd_line` PersonaUno de F4.1:
exterior=PersonaUno fecha=X, interior=PersonaUno fecha=X → suprimido).

---

## 2. Guardas anti-misatribución

| # | Guarda | Manda a cola / suprime cuando | Cierra |
|---|---|---|---|
| **G-MARK** | sin marcador de reenvío explícito en el cuerpo | no hay `_RE_FWD_MARK` | re-segmentar prosa; falso interior |
| **G-FRANJA** | franja `De:`→1ª-etiqueta sin tope | no aparece `_RE_GEN_LABEL` dentro de la ventana | la franja se traga el cuerpo |
| **G-UNICIDAD** | `len(_RE_ADDR.findall(franja)) != 1` | 0 (solo nombre) o >1 (ambiguo) `<addr>` en la franja | robo de Para/Cc; remitente+algo |
| **G-DELEGACION** | `en nombre de`/`on behalf of`/`via` en la franja | el `<addr>` no es del autor nombrado | ataque (v): relay/delegación |
| **G-APILAMIENTO** | `n_apple + n_de > 1` en la ventana | ≥2 atribuciones apiladas (p.ej. Reconocimiento ×2) | recursión / nivel equivocado |
| **G-NO-DUP-EXT** | `(anc_i.de, anc_i.fecha_iso) == (seg.de, seg.fecha_iso)` | el interior ES el mismo mensaje que el exterior | doble emisión (it.2 / fwd_line F4.1) |
| **G-AMBIGUA-INT** | `_n_cabeceras(cuerpo_i) > 1` → `ambigua` en `clasificar` | otra cabecera apilada dentro del cuerpo del interior | nivel equivocado (2ª red) |
| **G5** (heredada) | `anc.de` vacío | el body-scan nunca devuelve sin `de` | invención de remitente |
| **G-CONF** (heredada it.2) | interior NUNCA `alta-reconstruida` | `estructural=False` + tope dura | autenticar límite no-DOM como alta |
| **G-FECHA/G-IDENTIDAD** (heredadas) | fecha posterior al portador → media; candidata → media + del_burgo.md | `clasificar` | fecha imposible; identidad no confirmada |

**Por qué la franja es segura sobre datos reales:** el `<addr>` del remitente está SIEMPRE entre `De:` y la 1ª
etiqueta (`Date:/Fecha:`); los destinatarios van DESPUÉS de `Date:/Subject:` → fuera de la franja. Una etiqueta
intermedia adversaria (`Reply-To:`) cierra la franja antes del addr → `addrs=0` → rechazo.

---

## 3. Confianza e integración con los peldaños

El interior entra al `clasificar(anc_i, m_a.fecha_iso, estructural=False, ambigua=…)` existente y recibe
**`media-reconstruida`** con `motivo="interior_reenviado"` (banner «AUTORÍA POR VERIFICAR», `en_revision=True`
**SIEMPRE**). Justificación: (i) remitente fiable (de un `<addr>` literal ligado al `De:` por la franja acotada);
(ii) el **límite de su cuerpo** es por adyacencia tras un marcador, **no autenticado por estructura DOM** ni por
el `.eml`; (iii) es un mensaje reconstruido a **dos saltos**. Si `clasificar` devuelve algo menor (fecha
incoherente / candidata) se respeta. PersonaUno (`per01a@example.invalid`, identidad confirmada en Fase 2) →
`media-reconstruida`, `en_revision` (vigilada) → aparece en `del_burgo.md`. PersonaUno `outlook`/candidata → cap
a `media` + `del_burgo.md` (routing sin cambios). `render.py`/`corpus.py` ya rotulan `media-reconstruida` → cero
churn de código.

---

## 4. Idempotencia y Capa A byte-idéntica

- **Capa A byte-idéntica.** El desanidado vive SOLO en `reconstruir()` (rama Layer B) y lee una **copia local**
  (`texto_exterior_original`); no toca `_construir_mensaje`, `bodies`, ni el render de Capa A. Los 277 `.md`
  quedan byte-idénticos (test de regresión existente). El **atom exterior** (p.ej. MSG-00305 23-jul) **no se
  toca**: el interior es un atom **ADICIONAL**.
- **Fingerprint estable + dedup.** `fingerprint_b(anc_i, normaliza_cuerpo(cuerpo_i))` con `de/fecha/asunto`
  deterministas y `cuerpo_i` podado de forma **consistente** entre portadores → mismo `fp` → `_pase_layer_b`
  emite **UN** atom B con **N procedencias** (los 14 portadores de "Referencia: BaRS1" → 1 atom). Upgrade vía
  `idx.resolver` si el interior coincide con un `.eml` limpio de Capa A → 0 net-new (cuenta `report.upgrades`).
- **Sin renumerar.** `reg.msg_id_for_fp(fp)` congela el id; re-ejecutar = mismos fp.
- **Rebaseline DELIBERADO de golden de Capa B.** Aparecen atoms B net-new → `corpus.jsonl`,
  `CORREOS_LECTURA.md`, `_revision/reconstruidos.md` y los golden de `render_b`/`pipeline_b` ganan filas. Esto
  **NO** es un cambio de Capa A. Documentar el delta (N atoms + sus fp) al actualizar fixtures.

---

## 5. Plan de tests (TDD)

**Puros — `tests/test_email_atomize_inline.py`** (fixtures con el texto literal real):

1. **c′ forma (1) PersonaUno (`[PAIS_EXTRANJERO] docs`):** marcador + `De:`↵`PersonaUno`↵`<`↵`per01a@example.invalid`↵`>`↵`Date:`… →
   `_interior_reenviado` → `de="per01a@example.invalid"`, `de_nombre="PersonaUno"`, `fecha=2025-07-23`,
   `asunto="[PAIS_EXTRANJERO] docs"`; `cuerpo` SIN la cabecera.
2. **c′ testigo Eva 7-jul (MSG-00305):** ancla exterior Eva 23-jul; interior `De:`↵`PersonaCuatro, Eva`↵`<`↵`eva…`↵`>`↵
   `Fecha: El lun, 7 jul 2025`↵`Asunto: Re: offer letter TIBIDABO 8`↵`Para: …contacto@org-qa.example…` →
   `de="eva.pratpadros@…"`, `fecha=2025-07-07`, asunto correcto; el `<addr>` de [PAIS_EXTRANJERO] (Para/Cc) **NO** se coge.
3. **G-UNICIDAD robo de destinatario:** `De:`↵`Nombre` (sin `<addr>`) + `Para: <x@y>` → `None` (de="").
4. **G-FRANJA etiqueta intermedia:** `De:`↵`Nombre`↵`Reply-To: <relay@x>`↵`<`↵`addr@real`↵`>` →
   la franja se cierra en `Reply-To:` antes del addr → `addrs=0` → `None`.
5. **G-DELEGACION:** `De:`↵`Secretaría en nombre de PersonaDos`↵`<`↵`secretaria@x`↵`>` → `None`.
6. **G-APILAMIENTO:** ventana con 2 bloques `De:` (caso "Reconocimiento de cliente" real: Ignacio PersonaCinco +
   PersonaTres) → `None` (cola).
7. **G-MARK:** cuerpo con cabecera c′ pero **sin** marcador de reenvío → `None`.
8. **G-MARK marcador con guiones/nbsp:** `_RE_FWD_MARK` casa `"---------- Forwarded message ---------"` y
   `"----\xa0Mensaje reenviado\xa0---------"` (que `_RE_FWD_INTRO` NO casa).
9. **Poda c′ consistente:** dos variantes de wrap del MISMO interior → `normaliza_cuerpo(cuerpo_i)` idéntico.
10. **de_nombre c′(1):** `De:` bare + nombre en línea siguiente → `de_nombre` recupera "PersonaUno".

**Integración en `reconstruir` (sección T-it3):**

11. **Testigo MSG-00305 end-to-end:** portador real → exterior Eva 23-jul intacto **+ interior** Eva 7-jul
    `media-reconstruida`/`interior_reenviado`, `en_revision=True`, `de`/`fecha`/`asunto` del interior. (Hoy: ausente.)
12. **PersonaUno c′ → del_burgo.md:** interior `per01a@example.invalid` → candidato `media-reconstruida`, vigilado.
13. **[G-NO-DUP-EXT] no doble:** segmento cuyo exterior YA es el interior (de+fecha iguales) → NO se emite 2º atom.
14. **[Regresión F4.1] los 6 `fwd_line` PersonaUno** ya promovidos → mismo nº de atoms, fp idénticos, 0 atoms
    `interior_reenviado` duplicados.
15. **Prioridad:** exterior estructural con `de` válido (anchor) sigue intacto; el interior es ADICIONAL.

**Glue — `tests/test_email_atomize_pipeline_b.py`:**

16. **Dedup multi-portador:** el MISMO interior c′ citado en ≥2 portadores con wrap distinto → **1** atom B con
    procedencia `len ≥ 2` (no N atoms).
17. **Upgrade c′:** interior cuyo `(de,fecha,cuerpo)` ya existe como `.eml` limpio de Capa A → `idx.resolver`
    casa por `cuerpo_sha` → upgrade, 0 net-new.
18. **Idempotencia:** dos corridas → 0 renumerados, fp estables, **277 Capa A `.md` byte-idénticos**.
19. **Regresión byte-identidad del portador:** un portador con marcador pero interior NO promovible (sin `<addr>`
    en franja / multi-addr) → su `.md` de Capa A byte-idéntico a la corrida pre-feature.

**Caso real W-02VND1 (verificación adversarial post-build, NO en CI):** re-ejecutar `atomize_case('W-02VND1')`
(con autorización) y auditar a mano que **MSG-00305 7-jul Eva** emerge como atom B `media-reconstruida` net-new
con cuerpo limpio, y que PersonaUno `[PAIS_EXTRANJERO] docs`/`Estudio acciones penales`/`FYI` + Ignacio `Referencia` emergen
con el `<addr>` que aparece **LITERAL** en su `.eml` fuente; **ninguno** sale con `de` de un destinatario; los
277 Capa A byte-idénticos; idempotente; cobertura medida por la cifra del **motor**.

---

## 6. Alcance — qué queda fuera

- **Interiores en forma Apple (`El…/On … escribió:`) tras el marcador.** `_interior_reenviado` SOLO desanida
  interiores con bloque `De:`/`Fecha:`/`Asunto:` (incl. c′); un interior cuya cabecera es una atribución Apple
  va a **cola**. Decisión de la verificación adversarial: la rama Apple no podaba bien su propia cabecera cuando
  el `<addr>` iba envuelto (contaminaba el `cuerpo_sha`), y **no ocurre en el corpus real** (los marcadores van
  seguidos de bloques `De:`). Retirar la rama elimina el hueco con coste de cobertura nulo.
- **Recursión profunda / cadenas Apple apiladas / 2º nivel de reenvío.** Solo UN nivel por marcador explícito;
  lo apilado va a cola por G-APILAMIENTO (verificado: "Reconocimiento de cliente"). El contenido sigue legible
  dentro del atom exterior. **NO reintroducir** una franja que cruce etiquetas desconocidas sin G-FRANJA/G-UNICIDAD.
- **Interiores sin `<addr>` literal ligable al `De:`** (solo nombre, o `<addr>` solo en Para/Cc). Cola por
  G-UNICIDAD/G5 — recuperarlos violaría el prime directive. Definitivo.
- **Duplicado cross-path (over-count, NO misatribución).** Si el MISMO correo aparece en un portador `fwd_line`
  de **texto plano** (cuyo cuerpo Layer-B conserva la cabecera embebida `-----mensaje original----- De:…`, vía
  preexistente) Y en otro portador `html_quote` (de donde it.3 lo desanida con cuerpo **limpio**), los dos
  `cuerpo_sha` difieren → dos atoms del mismo correo (verificado: PersonaUno `CAPEX_for_His_Excellency`). Ambos
  van `media-reconstruida` + `en_revision` y atribuidos correctamente; **es redundancia, no misatribución**.
  Deduplicarlos exige una poda cross-path o dedup laxa en `_pase_layer_b` (toca el pipeline) → fuera de alcance.
  Coherente con near-dups preexistentes (it.2) del mismo origen (p.ej. aangerri "RV: Plànols" ×2, sin relación
  con it.3). Pendiente: MEJORAS.
- **Delegación del EXTERIOR.** `_RE_DELEGACION` se aplica al `De:` del **interior** (ambas ramas inline + c′);
  la misma fórmula en la atribución de un **exterior/anchor** (`_parse_apple`/`_parse_label` del path Layer B
  preexistente) NO se filtra — es comportamiento preexistente, fuera de alcance de it.3. Pendiente: MEJORAS.
- **`_RE_GEN_LABEL` (recall-loss seguro).** Una línea de continuación del nombre con `:` ("Director: …") cierra
  la franja antes del `<addr>` → `de=""` → cola. Conservador (prefiere cola a misatribución). No corregido.
- **Fidelity-upgrade reforzado** más allá de `idx.resolver` por `cuerpo_sha`. Iteración posterior.

---

## 7. Verificación adversarial final — resultado

Workflow de 2 revisores + 5 vectores de ataque ejecutando inputs contra el motor real:

- **Revisión de spec:** SHIP (todas las guardas del §2 verificadas; Capa A intacta; alcance respetado).
- **Ataques que SOSTUVIERON la atribución (0 misatribución):** nivel-equivocado (×11), Capa A/idempotencia (×8),
  marcador-abuso (×22).
- **Ataque que ROMPIÓ la atribución → CORREGIDO:** `delegacion-relay`. Dos defectos: (i) `_RE_DELEGACION` solo
  se aplicaba en el path c′, NO en el path inline (`De: X en nombre de Y <relay>` con `<addr>` en la línea `De:`
  pasaba por `_parse_label`/`_addr_o_nombre` sin guarda → afirmaba el relay); (ii) faltaban `p.p.`/`p.o.`/`vía`
  (tilde). **Fix:** guarda de delegación **unificada** sobre la franja `De:`→1ª-etiqueta en `_interior_reenviado`
  (cubre ambas ramas) + `_RE_DELEGACION` ampliada. Cerrado end-to-end (0 atoms relay en `reconstruir`).
- **Fidelidad (ALTO) → CORREGIDO:** la heurística de "línea de nombre" en `_cuerpo_interior` se comía un saludo
  corto si el cuerpo mencionaba un email cerca → ahora exige que la línea siguiente sea `<` o un `<addr>` real.
- **Auditoría read-only sobre W-02VND1 (sin escribir en G:):** 12 interiores distintos, **todos con `<addr>`
  LITERAL en su `.eml` fuente, 0 inventados** (PersonaUno ×5, Ignacio ×2, Eva→[PAIS_EXTRANJERO] 7-jul testigo, PersonaTres,
  Nikolai ×2, Marta). Suite +26 tests, 179 `email_atomize` verdes.

---

**Ficheros a tocar:** SOLO `core/email_atomize/inline.py` (3 constantes + `_addr_remitente_cprime`,
`_cuerpo_interior`, `_interior_reenviado` + ~25 líneas de enganche en `reconstruir` con `texto_exterior_original`)
y los 2 ficheros de test. **Cero cambios** en `model.py`, `clasificar` (firma), `pipeline.py`, `render.py`,
`corpus.py`, `dedup.py`, `ids.py`, el segmentador, `Segmento` (se reutilizan sus campos), o la Capa A.
Golden de Capa B se rebaselinan deliberadamente (atoms B net-new), documentando el delta.
