# PLAN — Motor documental unificado (split/OCR/MD) y empaquetado como conector

> **Estado:** diseño / memoria de diagnóstico. No implementado. Backlog: `MEJORAS #48`
> (promovido a `PLAN.md`). Norte: **empaquetar el motor OCR→split→MD como conector/plugin**
> reutilizable por el despacho. Este documento consolida el diagnóstico; el refactor y el
> empaquetado son trabajo posterior.

## 0. Por qué existe este documento

Se trazó, leyendo el código real, cómo está cableado el flujo **split / OCR / MD** de
FeesDefender. Aparecieron varias incoherencias arquitectónicas y varias funcionalidades
que faltan. Nikolai quiere **empaquetar el motor como un conector** para que lo usen los
compañeros. Un motor fragmentado y que falla en silencio no se puede empaquetar bien: por
eso sanear las incoherencias + construir una **fachada única** + un **registro de cobertura**
*es* el trabajo de preparación del plugin.

Entradas de backlog relacionadas que este plan consolida: `MEJORAS #21` (re-OCR por
degradación), `#24` (conversor multi-formato a MD), `#39` (robustez OCR Docling/RapidOCR),
`#42` (OCR server-side en `expedientes-xl`), `#43` (intake sin rama de OCR), `#41` (plugin
de skills).

---

## A. Cómo está cableado hoy

Orquestador: [`core/pipeline.py::run()`](../core/pipeline.py:43)

```
ensure_case → sync → inventory → extractor.extract_all → markdown_generator.build
            → scorer → viability → [demanda] → [anon] → linker
```

Ruta de un PDF en [`extractor._extract_one`](../core/extractor.py:234) (líneas 237-253):

1. **pypdf primero.** Si la capa de texto basta (`_texto_suficiente`: ≥100 chars y ≥40
   char/pág, [extractor.py:125-137](../core/extractor.py:125)) → pypdf, **sin OCR**.
2. Si es escaneado y **≤30 páginas** (`MAX_OCR_PAGINAS`, [extractor.py:44](../core/extractor.py:44))
   → **Docling** (OCR interno).
3. Si es escaneado y **>30 páginas** → `sin_texto` (se salta).

Luego [`markdown_generator.build`](../core/markdown_generator.py) envuelve cada
`raw_text/{slug}.txt` en `MD/{slug}.md` con frontmatter.

Tablas: Docling con `do_table_structure = False` ([extractor.py:81](../core/extractor.py:81))
por memoria — se conserva el texto, se pierde la rejilla.

---

## B. Incoherencias (5)

1. **Tres motores de OCR desacoplados** para el mismo trabajo, con idiomas distintos:
   | Motor | Módulo | Quién lo llama | Idiomas |
   |---|---|---|---|
   | Docling interno | [`extractor._try_docling`](../core/extractor.py:87) | el pipeline (≤30pp) | por defecto |
   | RapidOCR por página | [`core/ocr_per_page.py`](../core/ocr_per_page.py) | **solo** script manual [`scripts/ocr_textless_pdfs.py`](../scripts/ocr_textless_pdfs.py) | por defecto |
   | OCRmyPDF | [`core/anon/ocr.py`](../core/anon/ocr.py) | anonimización ([`api._ocr_y_extraer`](../core/anon/api.py:254)), re-OCR del ORIGINAL de cero | `spa+cat+rus` |

   → el mismo PDF lee distinto según el camino; doble OCR pipeline+anon.

2. **Hueco de >30pp.** El pipeline salta escaneados largos → `.md` vacío → invisibles a
   `scorer`/`viability`/`anon`. Rescate manual con **otro** motor (`ocr_textless_pdfs.py`).
   El paso `extractor.extract_all` termina en ✅ igualmente: nada avisa.

3. **Banda muerta de umbrales.** `extractor._texto_suficiente` = ≥100 chars;
   `ocr_textless_pdfs.UMBRAL_TEXTO` = 50 ([ocr_textless_pdfs.py:31](../scripts/ocr_textless_pdfs.py:31)).
   Un escaneado >30pp con 50–99 chars residuales **no lo OCR-iza nadie**: el extractor no
   (>30pp) y el script de rescate tampoco (≥50 → "ya tiene texto").

4. **Cabecera vs código en `extractor.py`.** El docstring ([extractor.py:3-6](../core/extractor.py:3))
   dice "*.pdf → Docling; fallback → pypdf*" (Docling primario); el código v2 hace lo
   **contrario** (pypdf primero, Docling solo escaneados). El comentario `EXTRACTOR_VERSION`
   sí lo explica, pero la cabecera quedó sin actualizar.

5. **`separar.py` desenganchado + etiqueta engañosa.** [`separar.py`](../core/anon/separar.py)
   no está en ningún pipeline (`anonimizar_caso` "No separa PDFs", [api.py:27](../core/anon/api.py:27));
   solo CLI + tests. Y el comentario "OCR vía Docling" ([pipeline.py:70](../core/pipeline.py:70))
   miente para los PDFs con texto, que van por pypdf sin OCR.

---

## C. Trato de imágenes (tres tratos incompatibles)

- **Pipeline principal:** [`extractor`](../core/extractor.py:234) **no tiene rama de imagen**
  → `ExtractionError` → se salta (ni `.txt` ni `.md`).
- **Adjuntos de correo:** [`adjuntos_contenido/router.py:27-32`](../core/adjuntos_contenido/router.py:27):
  <50KB "decorativa" omitida; ≥50KB → **cola de visión** (LLM, **no** OCR).
- **Anonimización:** ignora imágenes ([api.py:30](../core/anon/api.py:30)); depende de
  [`core/anon/imagen_a_pdf.convertir`](../core/anon/imagen_a_pdf.py), que es **solo CLI manual**.
- **Agujero HEIC:** `inventory._RELEVANT_EXTS` ([inventory.py:42](../core/inventory.py:42))
  **NO** incluye `.heic/.heif/.webp/.gif/.bmp`; `local_organizer`/`sala_lectura` **SÍ**. Las
  fotos de iPhone se caen desde el inventario.
- **Conflicto de fondo:** **OCR** (foto-de-documento) vs **visión** (foto-de-escena) sin
  política única; hoy lo decide el módulo que la tocó, no el contenido.

---

## D. Faltas del workflow (para el análisis jurídico)

1. **Registro de cobertura por documento** *(la clave)* — hoy todo falla en silencio;
   `_pipeline_log.md` registra pasos, no documentos. Sin esto, las demás fallan sin avisar.
2. **Control de calidad del OCR** — densidad de chars, ratio de gibberish, idioma detectado.
3. **Clasificar QUÉ es cada documento** (encargo/factura/arras/PBC…) enganchando
   [`judicial_classifier`](../core/judicial_classifier.py) + la taxonomía de la sala de lectura.
4. **Reensamblar documentos multi-parte** — fotos página-a-página;
   [`conjunto_detector`](../core/conjunto_detector.py) solo cubre cabecera+prueba.
5. **PDFs protegidos/cifrados/firmados** — rc=15/16 conocidos en `anon/ocr.py`, no tratados en el flujo principal.
6. **Tablas** — hoy descartadas a propósito; factura/liquidación de honorarios son tablas (base, %, importe).
7. **Detección de idioma** por documento (catalán/ruso).
8. **Punto de revisión humano** antes del análisis (como el visto bueno de `organizar-sala-lectura`).
9. **Transcripción de audio/vídeo** — notas de voz WhatsApp, entrevistas; hoy fuera del espinazo.

---

## E. Empaquetado del motor como plugin (norte) — prerrequisitos

10. **Fachada única** del motor: un solo punto de entrada
    `procesar_expediente(entrada, salida, opciones) → informe` que orqueste OCR→split→MD
    (hoy repartido entre `pipeline`/`extractor`/`ocr_per_page`/`anon.ocr`/`separar` + scripts).
    **Prerrequisito nº 1.**
11. **Desacople de rutas/entorno:** no asumir `caso_path`/`00_Input/`/`G:`/`.env`; recibir
    rutas explícitas de entrada/salida.
12. **Preflight de capacidades:** el conector reporta (y falla claro si faltan) ocrmypdf /
    tesseract `spa+cat+rus` / torch — como los prerequisitos documentados de `email-export`.
13. **Salida estructurada (JSON):** el registro de cobertura (D.1) devuelto **como dato**, no
    solo efectos en carpetas → lo que lo hace tool MCP consultable.
14. **Aislamiento por subproceso** por documento (patrón ya usado en `ocr_textless_pdfs.py`)
    para que un OOM no tumbe el servidor MCP.
15. **Versión del motor + modelos pinneados** (`EXTRACTOR_VERSION` ya existe; fijar además
    versiones de modelos para salida reproducible entre compañeros).
16. **Sin fuga de datos de casos en el paquete** + **preservar la lógica de `core/anon`**
    (regla de oro: no tocar regex/thresholds) al vendorizarla.

---

## F. Workflow objetivo (para fase posterior)

```
0. Inventario + clasificación por tipo (set de extensiones UNIFICADO, incl. HEIC→PDF)
   ├─ docx/eml/txt/csv         → (ya texto) ───────────────┐
   ├─ imagen foto-de-documento → imagen_a_pdf → OCR         │
   ├─ imagen foto-de-escena    → cola de visión             │
   └─ pdf ─────────────────────► 1. OCR (un motor, spa+cat+rus, salida = PDF BUSCABLE)
                                    │        └─ persiste → 01_Procesado/OCR/{id}.pdf
                                    → 2. split/merge (separar + conjunto_detector)
                                    │        └─ persiste → 01_Procesado/Documentos/{id}.pdf (+ índice)
                                    → 3. MD (lectura plana, sin OCR) ◄┘
                                             └─ persiste → 01_Procesado/MD/{id}.md
   → scorer → viability → [anon reutiliza el PDF buscable] → linker
   (registro de cobertura en indice_documental.yaml + control de calidad, transversales)
```
Cada etapa **persiste su producto** como artefacto de primera clase (ver §G); nada es
efímero y todo es regenerable sin re-tocar `00_Input/`.

Principios rectores:
- **El OCR produce un PDF buscable**, no un `.txt` suelto → el texto viaja en el artefacto y
  nadie lo recalcula (adiós al doble OCR y al "cada camino lee distinto").
- **OCR obligatorio en su etapa**, no un rescate manual → cierra el hueco de >30pp.
- **Los no-PDF** (docx, email, txt) saltan OCR y split y van directos a MD.

Motor OCR único candidato: **OCRmyPDF** — el único de los tres que produce PDF buscable, ya
maneja `spa+cat+rus` y, al ir página-a-página con Tesseract, es más estable en memoria (la
idea del subproceso aislado se absorbe aquí y el tope de 30pp desaparece). RapidOCR/Docling
quedarían como reserva para PDFs que Tesseract lea mal.

---

## G. Persistencia de artefactos por etapa

Principio rector: **cada etapa guarda su producto como artefacto de primera clase,
derivado y regenerable**, bajo `01_Procesado/` (nunca `00_Input/`; toda la ruta
`data/CASOS/*` está gitignored, así que ningún artefacto con PII sale del disco).

### G.1 Layout por etapa
```
01_Procesado/
  OCR/          ← PDFs buscables            [NUEVO — hoy el OCR es efímero]
  Documentos/   ← split/merge: 1 PDF por documento lógico + índice de segmentación  [NUEVO]
  raw_text/     ← texto extraído            (ya existe; [extractor.py:342](../core/extractor.py:342))
  MD/           ← .md por documento         (ya existe; [markdown_generator.py:25](../core/markdown_generator.py:25))
  indice_documental.yaml  ← registro de cobertura (ya existe; se amplía)
```
`ensure_case` crea hoy eager `01_Procesado/{Sala lectura, MD, _revisar}`
([case_manager.py:267](../core/case_manager.py:267)); `raw_text/` la crea el extractor
bajo demanda. `OCR/` y `Documentos/` seguirían ese mismo patrón (creación bajo demanda
por la etapa que las escribe). Elegido **layout por etapa** (no por documento): encaja con
"el producto de cada proceso", reutiliza `MD/`/`raw_text/` y resuelve limpio el 1→N del split.

### G.2 Victoria barata (primer paso de código — fase F3)
Persistir el PDF del OCR. Hoy [`api._ocr_y_extraer`](../core/anon/api.py:254) escribe el PDF
buscable en `tempfile.mkdtemp` y lo borra con `shutil.rmtree` (`api.py:270,283-284`).
[`anon/ocr.py::ocr_pdf`](../core/anon/ocr.py:30) **ya acepta ruta de salida explícita** y crea
su carpeta → basta apuntarla a `01_Procesado/OCR/{id}.pdf` en vez del tempdir. Efecto: el PDF
buscable queda guardado, la anonimización y el resto lo **reutilizan**, y se acaba el doble OCR.
Máximo retorno por el menor cambio.

### G.3 Identidad única de documento
Hoy fragmentada: `output_slug` = `slug__sha8` ([utils.py:32](../core/utils.py:32)) en
extractor/MD; `id_doc = sha[:12]` en el catálogo ([catalogo_documental.py:109](../core/catalogo_documental.py:109));
`slugify(stem)` + sha8 distinto en anon ([api.py:239-242](../core/anon/api.py:239)). Unificar en
**un solo id** para que `OCR/{id}.pdf`, `Documentos/{id}.pdf`, `raw_text/{id}.txt` y `MD/{id}.md`
compartan raíz y un documento se pueda seguir entre etapas por el nombre.

### G.4 Registro de cobertura = ampliar `indice_documental.yaml`
[`core/catalogo_documental.py`](../core/catalogo_documental.py) (dataclass `CatalogEntry`) ya tiene
entrada por documento, dedup por SHA y `parent_id`/`orden_en_bundle`. Ampliarla con, por etapa:
`{etapa, motor, ruta_artefacto, chars, confianza, avisos}`. Así los artefactos guardados se vuelven
**consultables** (§E.13) y nada se cae en silencio (§D.1). Una sola fuente de verdad, no artefactos
sueltos por carpetas.

### G.5 Estado / idempotencia por etapa
Consolidar el estado en el propio ledger (o un `_stage_state.json`) con SHA de origen + versión de
motor, siguiendo el patrón de `_extract_state.json`
([extractor.py:39,299-303](../core/extractor.py:299)): re-ejecutar salta lo no cambiado y jamás
re-toca `00_Input/`.

### G.6 Split 1→N y merge N→1
Un bundle produce N documentos; un merge junta N ficheros en 1. Los PDFs lógicos resultantes van a
`Documentos/`; la relación con el bundle se expresa con `parent_id`/`orden_en_bundle` del catálogo
(no con subcarpetas). El índice de segmentación de [`separar.py`](../core/anon/separar.py) (`indice.json`)
se integra en el ledger.

---

## Orden de ejecución sugerido (trabajo futuro)

1. **Saneamiento barato y no disruptivo:** alinear umbrales (B.3), corregir docstring/etiqueta
   (B.4, B.5), unificar el set de extensiones de imagen + HEIC (C).
2. **Registro de cobertura (D.1)** — el cimiento de observabilidad; habilita todo lo demás.
3. **Fachada única (E.10)** + desacople de rutas (E.11) + salida estructurada (E.13).
4. **Motor OCR único** (OCRmyPDF, produce PDF buscable) y **reordenar** split→MD sobre él.
5. **Conector MCP** + empaquetado en el plugin (E.12/14/15/16).
6. Faltas restantes (D.2–D.9) según disparador real.

## Fuera de alcance de este documento

- El refactor real del código (fachada, motor único, reordenación).
- La construcción del conector MCP y su empaquetado.
- El cierre de las faltas D.1–D.9.
