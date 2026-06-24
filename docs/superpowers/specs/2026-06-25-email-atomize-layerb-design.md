# Diseño detallado — Layer B (atomización inline) · Fase 2

> Diseño de Fase 2 de `core/email_atomize/`. **Sintetizado por un workflow adversarial**
> (4 diseños independientes × 3 jueces adversariales + síntesis; ganador: *header-anchor* base
> 25.7/40 + grafts de *forensic-conservative* 27.0 y *html-dom*). El workflow cazó 3 fallos
> que rompían la arquitectura (doble autoridad sobre el bloque del autor; guarda de intercalada
> ciega al HTML dominante; upgrade de fidelidad contra el path de IDs congelado) y los resolvió.
> **Aprobado por Nikolai 2026-06-25.** Decisión: `per01b@example.invalid` = **candidato,
> tope `media`** (no se auto-promociona a alta hasta confirmarlo en `identidades.yaml` de Fase 3);
> `ignacio@despacho-ab.example` = parte relacionada (su despacho), persona DISTINTA.
> Medición real previa: 138/277 ficheros con marcador inline; 120 HTML; 124 multi-marcador;
> ~21 bloques inline con autoría de PersonaUno. Spec base: `2026-06-24-email-atomize-design.md`.

---
Key facts I confirmed against the code that shape the design:
- `iter_body_text(raw)` → `(texto, es_html)`; HTML retains markup (decoded charset/QP only). No `es_html=` kwarg exists — designs that asserted it were wrong.
- `MensajeColapsado` has NO `fecha`/`msg_id` — the carrier date/id only exist after `_construir_mensaje`. Layer B must receive `RegistroMensaje` objects, not iterate `colapsados` for date.
- `ids.msg_id_for` does `entry["sha256"] = sha` unconditionally on hit; `_norm_mid` only strips `<>`, so `fp:` keys survive but the sha-overwrite is a hazard for fp keys (no real .eml sha).
- `bodies.extraer_cuerpo` returns the TRIMMED author body; the quoted tail is discarded — Layer B must re-derive from the raw, and the author-block cut point must be shared, not duplicated.
- `dedup.colapsar` merge keys on `len(raw)` ("more bytes wins") — synthesized stub bytes are NOT a valid fidelity signal.
- `pipeline` processes all Layer A before anything else; render emits flags only when True (frontmatter non-churn holds).

Now the synthesized design.

---

# Layer B — Inline Authorship Reconstruction (`core/email_atomize/inline.py`)

> Phase 2 design for `core/email_atomize/`. Caso piloto W-02VND1; engine is **generic/case-agnostic**. Hand-off target: `superpowers:writing-plans`. Prime directive: **zero misattribution** — a sender is asserted only when an explicit, parseable header block names it; everything weaker routes to `_revision/`.

## 0. Base approach + grafts (justification)

Base = **`header-anchor`** (the highest-scoring family: 28/28/26 across panels; no fatal flaws on two of three judges). Its core principle — *promotion requires a parseable header block; structural depth (DOM nesting / `>` run-length) supplies boundaries, markers only supply labels* — is the forensically correct division of labor and the only one that survived adversarial review without a misattribution hole.

Grafted fixes:
- From **`forensic-conservative`**: the explicit `clasificar(cab, fecha_portador)` ladder, the watched-identity double-control sub-queue, and the **date-coherence anti-fabrication guard** (a quoted segment must predate its carrier).
- From **`html-dom`**: the structural-truth insight that blockquote nesting beats regex for the dominant 120/138 HTML files, and the **token-conservation invariant** (author + segments ≈ whole body) as a `.extract()` safety net.
- Cross-cutting fixes for flaws every design shared: a **single shared author-block segmenter** feeding both `bodies._limpia_cita` and Layer B (kills the "two authorities on the author block" fatal flaw); a **fidelity-upgrade bridge that does NOT rely on whole-body fingerprint equality** (kills the circular/whole-body-hash fatal flaws); and the **fingerprint date is day-granular, not hour/minute** (kills the tz-jitter renumber risk).

---

## 1. Module / file plan

### New files
- **`core/email_atomize/inline.py`** — pure module. No I/O. Public API:
  - `segmentar(raw: bytes) -> Segmentacion` — author block + ordered ancestor segments (HTML-first, plain fallback).
  - `parsear_anclaje(texto_anclaje: str, estilo: str) -> Anclaje | None` — sender/date/subject from a header block.
  - `clasificar(anc: Anclaje | None, fecha_portador_iso: str, *, depth_ambigua: bool, estructural: bool) -> tuple[str, str]` — `(confianza, motivo)`.
  - `fingerprint_b(anc: Anclaje | None, cuerpo_norm: str) -> str` — `"fp:" + sha256(...)[:24]`.
  - `fingerprint_a(m: RegistroMensaje) -> str` — same algorithm over a Layer-A message (for the bridge).
  - `normaliza_cuerpo(texto: str) -> str` — the ONE canonical normalizer (used by both fingerprints).
  - `reconstruir(m_a: RegistroMensaje, raw: bytes) -> ReconResult` — orchestrates segmentation→attribution→confidence→fingerprint for one carrier; returns updated author flags + list of candidate Layer-B segments (NOT yet id-assigned).
- **`core/email_atomize/_segmenter.py`** (or a section inside `inline.py`) — the shared `cortar_autor(base_text: str) -> (autor: str, resto: str | None, intercalada: bool)` used by BOTH `bodies._limpia_cita` and Layer B. **`bodies` is refactored to call this**, guaranteeing one cut point.

### Changed files (all additive; Layer A output byte-identical)
- **`bodies.py`**: `extraer_cuerpo` gains `conservar_resto: bool = False` (default = current behavior, byte-identical). When `True`, returns the chosen base text **untrimmed** plus the author/resto split from the shared segmenter. `_limpia_cita` is reimplemented to delegate to `_segmenter.cortar_autor`. **Regression test asserts the 277 `.md` bodies are byte-identical before/after.**
- **`model.py`**: add to `RegistroMensaje` (all defaulted → existing construction untouched, frontmatter emits only when set):
  - `fingerprint: str = ""`
  - `reconstruido_desde_cita: bool = False`
  - `fecha_inferida: bool = False`
  - `ambiguedad_profundidad: bool = False`
  - `en_revision: bool = False`
  - `reconstruido_de: str = ""` (parent MSG-id)
  - new dataclass `SegmentoEnterrado(portador_msg_id, estilo, profundidad, de, fecha_iso, confianza, motivo, extracto, fingerprint)` — the review-queue row.
- **`ids.py`**: add a parallel **fp index** + alias map, both additive in `_registro.json` (load tolerates absence → frozen 277 untouched):
  - `self.mensajes_fp: dict[str, dict]` (`fp -> {"id", "cuerpo_sha"}`).
  - `self.alias: dict[str, str]` (`rfc_message_id -> fp`).
  - `msg_id_for_fp(fp: str, *, cuerpo_sha: str) -> str` — freezes id by fp; **does NOT touch `mensajes`/sha256 of Layer-A entries** (separate dict; the sha-overwrite hazard is avoided because fp ids carry `cuerpo_sha`, not an .eml sha).
  - `resolver_alias(rfc_message_id: str) -> str | None`, `registrar_alias(rfc_message_id, fp)`.
  - `save()` persists `mensajes_fp` + `alias`; `version` bumped 1→2 with a defaulting loader.
- **`dedup.py`**: **`colapsar` is NOT modified** (the 277 idempotency core stays frozen). The fidelity-upgrade lives entirely in the new pipeline pass, not in `colapsar`'s `len(raw)` merge (which is invalid for synthetic stubs — we never synthesize stub bytes; see §5).
- **`pipeline.py`**: after the Layer-A loop builds `mensajes` (all capa A, all id-assigned), run a **Layer-B pass** (§7). Then write `_revision/`.
- **`render.py`**: 
  - `render_md`: emit the new flags when set; for capa B add a body banner `> RECONSTRUIDO DESDE CITA — remitente verificado por cabecera inline` (alta) / `> AUTORÍA POR RECONSTRUIR — sin verificar` (media/baja). **Provenance must be visible at point of citation, not only in the queue** (fixes the judge weakness that a lawyer could cite a `.md` in isolation).
  - `render_correos_lectura`: capa-B `de` line is rendered distinctly — `**De (reconstruido):** …` — never with the same visual authority as an authenticated Layer-A `De:`. Add the plain-language forward note "Mensaje recuperado de una cita; remitente verificado por cabecera (MSG-id)".
  - new `render_revision(mensajes_b, punteros) -> dict[str, str]` producing `cola.md`, `casi_duplicados.md`, `del_burgo.md` (+ `.jsonl` mirrors for idempotent re-alerting).
- **`corpus.py`**: `_fila` already emits `capa`/`confianza`; add `fingerprint`, `reconstruido_desde_cita`, `en_revision` so machine consumers can filter.

---

## 2. Segmentation algorithm

A carrier body → `Segmentacion(autor: str, ancestros: list[Segmento], respuesta_intercalada: bool)`. `Segmento = (texto, anclaje_texto: str|None, profundidad: int, estilo: str, estructural: bool)`. `estructural=True` means depth came from DOM nesting or `>` run-length (trustworthy); `False` means depth was inferred from adjacency only.

### 2.0 Intercalada guard (runs FIRST, both formats)
If author text appears **after/between** quoted content, do **not** segment: keep the whole body as the author block, set `respuesta_intercalada=True`, attribute nothing.
- **Plain**: existing `bodies` logic (author line after first `>`).
- **HTML** (fixes the dominant-format intercalada hole): after locating quote containers, if any non-whitespace author text node exists **after the start of the first container**, treat as intercalada. HTML threads with author text outside the leading block default to `respuesta_intercalada` rather than being segmented.

### 2.1 HTML path (preferred; 120/138 files)
Parse the raw `text/html` part (from `iter_body_text` where `es_html=True` — retains markup) with a **stdlib `html.parser.HTMLParser` subclass maintaining a tag stack** (no bs4/lxml dependency — consistent with `bodies._html_a_texto`). Quote-container selectors, deepest-first:

| Client | Selector |
|---|---|
| Apple/generic | `<blockquote ...>` (esp. `type="cite"`) |
| Gmail | `<div class~="gmail_quote">`, `<blockquote class~="gmail_quote">`; attribution in `<div class~="gmail_attr">` |
| Outlook desktop | `<div id="divRplyFwdMsg">`, `<div id="x_divRplyFwdMsg">`, `<div class~="OutlookMessageHeader">`/`x_OutlookMessageHeader`; `<hr>` immediately followed by a `From:`/`De:` block |

- **Depth = blockquote/container nesting count** (`estructural=True`). Handles the depth 1–5 cases (max 5, 2 files) natively. **Hard recursion cap = 8.**
- **Author block** = text nodes outside any container (via `_html_a_texto`).
- **Anclaje_texto** = the text node / header div **immediately preceding** the container (the `gmail_attr` line, the Outlook `OutlookMessageHeader` table, or the `From:` block after `<hr>`).
- Each segment's inner text → `_html_a_texto` (same formatting as Layer A).
- **Header-to-level binding validation** (fixes the html-dom "marker bound to wrong level" weakness): a preceding header binds to a container only if it sits at the container's parent depth and within 6 lines/nodes. If the nearest header is ambiguous (two flush-left Outlook headers adjacent), set `estructural` boundary but mark `ambiguedad_profundidad=True` → caps confidence at media.
- **Malformed HTML / unbalanced tags / mojibake-flagged (3 files)** → fall back to the plain path on the `text/plain` part.

### 2.2 Plain path (fallback: ~18 files w/o usable HTML)
Collect **all** marker offsets across styles, sort by document position, each opens a segment ending at the next marker/EOF (handles the 124 multi-marker files; no single-style assumption). Concrete regexes (extend `bodies._RE_CITA_HDR`, shared constant `inline.MARCADORES`):

```python
RE_FWD   = re.compile(r"^\s*-{2,}\s*(forwarded message|mensaje reenviado|reenviado|"
                      r"begin forwarded message|original message|mensaje original)\s*-*\s*$",
                      re.I | re.M)                                          # fwd_line (42)
RE_OUTLOOK = re.compile(r"^\s*(?:de|from)\s*:\s*(?P<de>.+)$"               # outlook_es (54)
                        r"(?:\n.*){0,3}?\n\s*(?:enviado|sent|fecha|date|para|to|asunto|subject)\s*:",
                        re.I | re.M)        # De/From must be followed within 4 lines by 2nd label
RE_APPLE_ES = re.compile(r"^\s*el\s+(?P<x>.+?)\s+escrib(?:i[oó]|ió)\s*:\s*$", re.I | re.M)  # 19
RE_APPLE_EN = re.compile(r"^\s*on\s+(?P<x>.+?)\s+wrote\s*:\s*$", re.I | re.M)               # 4
# quote_gt (72): a RUN of consecutive lines whose lstrip startswith '>'; depth = leading '>' count
```
- **Depth**: `>` run-length is authoritative when present (`estructural=True`); for Outlook/Apple/fwd blocks without `>`, depth from adjacency (`estructural=False` → caps at media). Coalesce `>`-runs across single blank lines (fixes the depth-5 mis-slice).
- The **stray-`De:` guard** (`RE_OUTLOOK` requires a 2nd label within 4 lines) prevents prose `"De: acuerdo"` from spawning a phantom.

### 2.3 HTML/plain coherence
If both parts exist and segment **counts differ materially**, use HTML for boundaries + plain for readable body text per segment; on material divergence set `motivo="discrepancia_html_plano"` → media + review (never guess).

### 2.4 Token-conservation invariant (safety net)
After segmentation, assert `tokens(autor) + Σ tokens(ancestros)` is within ±5% of `tokens(whole flattened body)`. On failure (DOM `.extract` dropped/duplicated text) → **abandon segmentation for this carrier**: author block reverts to the Layer-A body, the whole file goes to `cola.md` with `motivo="conservacion_tokens"`. No partial/risky attribution.

---

## 3. Sender / date reconstruction (incl. the headerless ~77)

`parsear_anclaje(texto, estilo)` extracts `(de, de_nombre, fecha_iso, fecha_dt, asunto)` **only from the segment's own header block**, never from inference, never from a name mentioned in body prose.

- **outlook_es / fwd_line block**: bilingual label map `{de,from→from; enviado,sent,fecha,date→date; para,to→to; asunto,subject→subject}`. Synthesize an RFC header string and feed it to `email.message_from_string` + `headers._fecha`/`parseaddr`/`getaddresses` — **reuse `headers.py` normalization, don't reimplement** (Europe/Madrid tz, address split). `parseaddr` splits `de_nombre`/`de`; a bare display-name → `de=""`, `de_nombre` set.
- **apple_es / apple_en / gmail_attr**: `"El <fecha>, a las <hora>, <Nombre> <addr> escribió:"` — regex pulls trailing `<addr>`, the display name, and the leading date fragment.
- **Spanish/Catalan long-form dates** (`"lunes, 3 de febrero de 2020 18:42"`, `"12 de marçde 2021"`): a dedicated **ES+CA month/day map** (locale-independent — Windows locale unreliable) → build aware datetime in Europe/Madrid; `parsedate_to_datetime` tried first. **Add Catalan** (`gener…desembre`, `va escriure`) — the corpus is bilingual (judge gap). On parse failure: `fecha_iso="0000-00-00"`, `fecha_inferida=True`.

**The ~77 headerless files** (markers present, no parseable From): `parsear_anclaje` returns `None` or `de==""`. These are **never** given a sender. Two outcomes:
- The segment glues to its nearest **anchored** parent (kept as that ancestor's body, `motivo="sin_cabecera"`), OR
- if the whole body is quote-only with zero anchors anywhere (the 13 `quote_only_candidates`) → ONE `confianza="baja"`, `reconstruido_desde_cita=True`, `de=""` message → `cola.md`.

---

## 4. Confidence rules (exact) + routing

Evaluated per segment. Layer-A messages keep `confianza="alta"` untouched. Layer-B never uses the bare string `"alta"` (reserved for authenticated MIME); the top reconstructed level is **`"alta-reconstruida"`**.

```
ALTA-RECONSTRUIDA (promotes to a capa=B .md; NOT in cola.md, but watched ids → del_burgo.md):
    anc.de is a syntactically valid email
    AND anc.fecha parses (fecha_iso != 0000-00-00)
    AND anc.fecha_iso <= fecha_portador_iso            # date-coherence guard
    AND estructural is True                            # depth from DOM/'>' not adjacency
    AND not ambiguedad_profundidad
    AND not discrepancia_html_plano
MEDIA (NOT promoted; SegmentoEnterrado pointer + cola.md):
    header present but exactly one of {valid email, parseable date} missing
    OR estructural is False  OR ambiguedad_profundidad  OR discrepancia_html_plano
    OR name/address mismatch (display-name token neither contains nor is contained in addr local-part)
BAJA (NOT promoted; pointer + cola.md, de=""):
    marker present but no parseable header (the ~77)
    OR quote_only candidate (the 13)
    OR mojibake on the segment body
    OR token-conservation failure (whole carrier)
```

Hard misattribution guards (override upward):
- **Date posterior to carrier** → never alta; `motivo="fecha_incoherente"` → media + review.
- **Anchor collision**: a parsed quoted-From landing on the depth-0 author block → reject the segment, author reverts to full Layer-A body, log to `casi_duplicados.md`.
- **Any single failing predicate demotes one full level — never rounds up.**

Routes to `_revision/`: all media + all baja; **plus every alta-reconstruida whose `de` matches a watched identity** (double control, doesn't block promotion); plus all `ambiguedad_profundidad` / `fecha_incoherente` / `discrepancia_html_plano` / `conservacion_tokens`.

---

## 5. Fingerprint (stable identity for MID-less inline messages)

ONE canonical normalizer `normaliza_cuerpo` used by **both** `fingerprint_b` (over a quoted segment) and `fingerprint_a` (over a Layer-A message) — extracted to a single function so the two code paths cannot diverge (fixes the "two normalizers" fatal flaw):

```python
def normaliza_cuerpo(texto: str) -> str:
    t = strip_quote_marks(texto)        # remove leading '>'+ per line
    t = strip_signature(t)              # cut at first of: /^-- ?$/, "Enviado desde mi", "Sent from my",
                                        #                  "Obtener Outlook", "Get Outlook"
    t = collapse_ws(t)                  # \s+ -> ' '
    t = unicodedata.normalize("NFKC", t).casefold()
    t = nfkd_ascii_fold(t)              # accent-strip (same as _slug_descripcion)
    return t.strip()
```

```python
def fingerprint_b(anc, cuerpo_norm) -> str:
    remitente = (anc.de or "").strip().lower() if anc else ""          # address ONLY, never name
    fecha_dia = anc.fecha_iso if (anc and anc.fecha_iso != "0000-00-00") else ""  # DAY granularity
    asunto    = _slug_descripcion(anc.asunto if anc else "")           # reuse: strips Re/RV/Fwd, accents
    cuerpo_sha = sha256(cuerpo_norm).hexdigest()
    material  = "\x1f".join([remitente, fecha_dia, asunto, cuerpo_sha])
    return "fp:" + sha256(material).hexdigest()[:24]
```

Design decisions that fix the panel's fatal/major fingerprint flaws:
- **Date is DAY-granular, not hour/minute.** Quoted inline dates are usually tz-naive Spanish strings; the MIME copy is tz-aware. Day granularity absorbs the ±1–2h tz/DST offset that would otherwise split identity across runs (the renumber risk three judges flagged). Residual same-day collisions are caught by `cuerpo_sha` + `casi_duplicados.md`.
- **Minimum-body floor**: if `len(cuerpo_norm) < 24` chars, the fingerprint is computed but is **never allowed to drive collapse/upgrade** — such short boilerplate (`"ok"`, `"de acuerdo"`) only ever produces a distinct id and, on any near-match, routes to `casi_duplicados.md` for human confirmation (fixes the false-collapse fatal flaw). No silent merge of short messages.
- Pure function of content; reproducible across runs (sha256 + fixed separator, no time/path/order). Tested by hashing the same fixture twice.

---

## 6. Fidelity-upgrade (keep MSG-id, improve body/confidence)

The bridge does **NOT** depend on whole-body fingerprint equality between a trimmed Layer-A body and an isolated inline fragment (that was the circular fatal flaw). Instead:

**Bridge key = the inline block's OWN `Message-ID:` line when present** (full Outlook/Gmail forward dumps carry it), recorded as `alias[rfc_message_id] = fp`. This is the reliable, common case for forwarded `.eml` (W-02VND1: 266/266 embedded already exist as clean `.eml`).

Secondary bridge (when the inline block has no `Message-ID:`): a **decoupled `cuerpo_sha`-only match** — `fingerprint_a` and `fingerprint_b` are compared **on `cuerpo_sha` alone** (not the full fp), since sender/date/subject framing differs between a quote and the clean copy but the normalized body text is the same when not truncated. A `cuerpo_sha` match (with the ≥24-char floor) maps fp→Message-ID. Truncated quotes won't match → they fall to `casi_duplicados.md`, not silently merged.

Flow (in the pipeline Layer-B pass, AFTER all Layer-A ids are frozen):
1. For each Layer-A message, compute `fingerprint_a` + its `cuerpo_sha`; index `cuerpo_sha → MSG-id` and `rfc_message_id → MSG-id`.
2. For each reconstructed alta-reconstruida segment:
   - If its inline `Message-ID:` (or `cuerpo_sha`) resolves to an existing Layer-A MSG-id → **the segment is a lower-fidelity duplicate of a clean copy**: do NOT mint a new message; append a `procedencia` entry `{"citado_en": carrier_msg_id, "profundidad": d}` to the Layer-A message. The clean copy wins (capa A, alta). No duplicate, no renumber.
   - Else → `reg.msg_id_for_fp(fp, cuerpo_sha=...)`, build the capa-B `RegistroMensaje`.
3. **Cross-run upgrade**: if run-1 minted a fp-keyed capa-B id and run-2 the clean `.eml` arrives, step 2 resolves the alias/`cuerpo_sha` to the **existing fp id is NOT re-minted**; the Layer-A message records `registrar_alias(rfc_message_id, fp)` and the corpus shows the capa-B id was superseded (logged in `casi_duplicados.md` as an upgrade event). The fp id persists in `_registro.json`, so any prior citation stays valid.

**Ordering guarantee**: Layer A is fully built and id-frozen before the Layer-B pass — so a clean copy present anywhere registers before its inline twin folds in (fixes the ordering-inversion fatal flaw in `header-anchor`/`text-seg`).

**Deterministic id assignment**: before any `msg_id_for_fp` call, sort candidate segments by `(fp)` so re-runs assign new numbers in a stable order regardless of `pytest-randomly`/dict ordering (fixes the renumber-on-reorder risk).

---

## 7. Pipeline integration (concrete)

```python
# in atomize_dir, AFTER the Layer-A loop builds `mensajes` (all capa A, ids frozen) and BEFORE writes:
import core.email_atomize.inline as INL

# 1. index Layer A for the bridge
idx = INL.indice_layer_a(mensajes)          # {cuerpo_sha: msg_id}, {rfc_mid: msg_id}, set(fp_a)

# 2. reconstruct per carrier
candidatos: list[Segmento] = []
punteros:   list[SegmentoEnterrado] = []
for m_a, col in zip(mensajes, colapsados):  # carriers only (depth 0); align by msg
    res = INL.reconstruir(m_a, col.raw)
    # author flags back onto the Layer-A message (respuesta_intercalada etc.)
    m_a.respuesta_intercalada |= res.intercalada
    candidatos.extend(res.ancestros_alta)   # alta-reconstruida candidates
    punteros.extend(res.punteros)           # media/baja -> queue + frontmatter pointer on m_a

# 3. resolve duplicates / mint fp ids (deterministic order)
mensajes_b: list[RegistroMensaje] = []
for seg in sorted(candidatos, key=lambda s: s.fingerprint):
    destino = idx.resolver(seg)             # existing Layer-A MSG-id via mid-alias or cuerpo_sha
    if destino:
        idx.msg(destino).procedencia.append({"citado_en": seg.portador_msg_id, "profundidad": seg.depth})
        continue
    seg_msg_id = reg.msg_id_for_fp(seg.fingerprint, cuerpo_sha=seg.cuerpo_sha)
    mensajes_b.append(INL.construir_b(seg, seg_msg_id, reg))

mensajes.extend(mensajes_b)

# 4. write outputs (existing) + review queue
(out / "_revision").mkdir(exist_ok=True)
for nombre, contenido in R.render_revision(mensajes_b, punteros).items():
    (out / "_revision" / nombre).write_text(contenido, encoding="utf-8")
```

Idempotency: Layer-A `colapsar` untouched → 277 ids frozen. Layer B only ADDS fp-keyed ids + queue files (regenerated each run, `.jsonl` mirror de-alerts). `00_Input` never touched.

---

## 8. Frontmatter additions (consistent with `model.py`/`render.py`)

Emitted only when set (so the 277 stay byte-identical):
```yaml
capa: B
confianza: alta-reconstruida        # | media | baja
fingerprint: "fp:ab12…"
reconstruido_desde_cita: true
reconstruido_de: MSG-00042          # parent carrier
fecha_inferida: true                # if date didn't parse
ambiguedad_profundidad: true
en_revision: true                   # media/baja or watched-id alta
procedencia:
  - {citado_en: "MSG-00042", profundidad: 1}
respuesta_intercalada: true         # on the CARRIER (Layer A) when interleaved
```
Body banner (capa B) rendered in the `.md` body AND distinct `De (reconstruido)` in `CORREOS_LECTURA.md` — provenance visible at the point of citation.

---

## 9. PersonaUno recovery (engine stays generic)

Layer B is **case-agnostic**: it parses literal inline From addresses and never coalesces identities. The 21 inline-authored blocks surface because they each carry a **parseable inline From** (19× `per01a@example.invalid`, 2× `per01c@example.invalid`) → they land **alta-reconstruida** with a real address, independent of the weak ~77 headerless majority.

A single **config-driven watched-list** (`identidades.yaml`, Phase 3; absent in Phase 2 ⇒ no-op, but the hook exists now as a constant `IDENTIDADES_VIGILADAS: set[str]`) force-routes any segment whose `de` ∈ watched to `_revision/del_burgo.md` for probative review even when alta-reconstruida. For Phase 3 `identidades.yaml`:
- PersonaUno = `{per01a@example.invalid, per01c@example.invalid}`; **`per01b@example.invalid` = candidate** (name-proximity only → capped at media until confirmed).
- `ignacio@despacho-ab.example` (20× inline From) = **related party (his firm), a DISTINCT person** — never folded into PersonaUno despite the domain surname.
- Identity unification (collapsing `per01c@example.invalid` ↔ `per01a@example.invalid`) is **Phase 3, not Layer B**.

---

## 10. Test plan (synthetic fixtures, mapped to measured patterns)

Pure-layer tests (`tests/test_email_atomize_inline.py`) + glue (`tests/test_email_atomize_pipeline_b.py`), per the §14 house pattern (crafted raw `.eml` fixtures).

**Correctness / recovery:**
1. `html_quote` single Gmail blockquote + `gmail_attr` From → 1 alta-reconstruida, correct `de`/`fecha`. (120 files)
2. Nested blockquote depth 5 → 5-link ancestor chain, correct depths. (2 files)
3. `outlook_es` `De:/Enviado:/Para:/Asunto:` block (plain + HTML `OutlookMessageHeader`) → alta. (54)
4. `apple_es` `El … escribió:` + `apple_en` `On … wrote:` inline addr. (19+4)
5. `fwd_line` `---- Forwarded ----` + following From block. (42)
6. Multi-marker file mixing Outlook+Gmail+Apple in one body → correct N segments, document order. (124)
7. Spanish long-form date + **Catalan** date/`va escriure` → parses to correct ISO.

**Non-misattribution (the prime directive):**
8. Headerless marker (markers, no From) → **no sender ever**, `de=""`, → `cola.md`. (77)
9. Quote-only body, no anchor → ONE baja `reconstruido_desde_cita`, `de=""`. (13)
10. Stray prose `"De: acuerdo"` near `"asunto"` → **NOT** segmented (2nd-label guard).
11. Outlook display-name-only (no `<addr>`) → media, `de=""`, never promoted to an address.
12. `per01b@example.invalid` near a name → capped at media (name/addr proximity).
13. `ignacio@despacho-ab.example` inline → attributed to Ignacio, **NOT** PersonaUno.
14. Date posterior to carrier → `fecha_incoherente` → media + review, never alta.
15. **HTML interleaved reply** (author text between blockquotes) → `respuesta_intercalada`, no fragment attribution. (dominant-format intercalada hole)
16. Anchor collision (quoted From on author block) → segment rejected, author = full Layer-A body.
17. Token-conservation failure (synthetic over-`.extract`) → whole carrier to queue, no partial attribution.

**Identity / idempotency / upgrade:**
18. `fingerprint_b` reproducible: same fixture twice → identical fp.
19. Day-granular date: same message quoted (tz-naive) vs MIME (tz-aware, ±2h) → **same fp day component**, bridges.
20. Re-run over existing `_registro.json` → **all 277 Layer-A MSG-ids unchanged**; Layer-B fp ids stable.
21. Fidelity-upgrade: inline twin in run-1, clean `.eml` in run-2 → same logical message, **no duplicate, no renumber**, alias recorded.
22. Short-body floor: two distinct `"ok"` replies same sender/day/subject → **NOT** auto-collapsed → `casi_duplicados.md`.
23. **Regression**: 277 Layer-A `.md` bodies byte-identical before/after the `bodies` refactor (`conservar_resto` default path).

---

## 11. Residual risks + adversarial verification on real data (post-build)

**Residual risks:**
- ES/CA long-date parser coverage is the alta↔media gate; an unhandled format silently demotes (safe: more review, zero misattribution) but shrinks the PersonaUno alta yield.
- `html.parser` (no real DOM) can mis-count nesting on malformed Outlook/Office365 HTML; mitigated by header-to-level binding validation + token-conservation + plain fallback, but mis-nesting that *passes* both checks would mis-state who-quoted-whom (structure, not sender).
- `cuerpo_sha`-only bridge misses truncated quotes (Gmail/Outlook elide trailing content) → upgrade miss → near-dup, surfaced in `casi_duplicados.md` for a human (acceptable: miss, not misattribution).
- Watched-list is literal-address; a new PersonaUno address not in `identidades.yaml` won't hit `del_burgo.md` (but still hits `cola.md` if media/baja, or is a normal alta `.md`).

**Adversarially verify on the 277 after building:**
1. **Manual audit of EVERY alta-reconstruida** (expect ≈21 PersonaUno + others): confirm the asserted `de`/`fecha` literally appears in the source `.eml` header block. Zero tolerance for a fabricated sender.
2. **Measure the real ~61/~77 split**: count how many marker files actually promoted vs queued; confirm the 21 PersonaUno blocks all promoted (alta) and none landed silently in `baja`.
3. **Date-parse failure rate** on `outlook_es`/`apple_es` real dates → tune the ES/CA map until alta yield stabilizes without forcing any wrong date.
4. **Re-run twice, diff `_registro.json`**: assert 0 renumbers, 0 duplicate fp ids, identical 277 Layer-A `.md`.
5. **Cross-check `casi_duplicados.md`** against known forwarded `.eml`: confirm fidelity-upgrade fired where the clean copy exists (W-02VND1: should be most PersonaUno quotes, since 266/266 embedded exist as clean `.eml`).
6. **Probe interleaved HTML threads** specifically for any segmented (not `respuesta_intercalada`) output — the single highest-risk misattribution vector in this corpus.