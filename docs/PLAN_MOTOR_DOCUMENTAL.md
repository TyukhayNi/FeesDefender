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
                                    │        ├─ persiste → 02_Sala de máquina/01_OCR/{ruta espejo}/{slug__sha8}.pdf
                                    │        └─ si ocr_quality low/empty → reocr automático (ver §G.7)
                                    → 2. split/merge (separar + conjunto_detector)
                                    │        └─ persiste → 02_Sala de máquina/02_Documentos/…/{slug__sha8}.pdf (+ índice)
                                    → 3. MD (lectura plana, sin OCR) ◄┘
                                             └─ persiste → 02_Sala de máquina/03_MD/…/{slug__sha8}.md (ESPEJO)
   → scorer → viability → [anon reutiliza el PDF buscable] → linker
   (registro ÚNICO de caso index.yaml + control de calidad, transversales — ver §H)
   01_Sala de lectura = vista DERIVADA del registro (INDICE/CRONOLOGIA/.xlsx), para el humano
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

### G.1 Layout: Sala de lectura (humano) vs Sala de máquina (pipeline) — DECIDIDO
```
01_Procesado/
  01_Sala de lectura/   ← HUMANO. Vista DERIVADA del registro (§H): INDICE.md, CRONOLOGIA.md, .xlsx
  02_Sala de máquina/   ← MÁQUINA (pipeline). En claro CON PII, gitignored. Productos numerados:
     01_OCR/            PDFs buscables            [NUEVO — hoy el OCR es efímero]
     02_Documentos/     split/merge: 1 PDF lógico por documento + índice de segmentación  [NUEVO]
     03_MD/             espejos markdown — ESPEJAN la jerarquía de 00_Input/  (hoy MD/ es plano)
        (raw_text = sub-artefacto de la etapa MD, no etapa de primera clase)
  _revisar/             worklist de residuo (se mantiene)
```
- **Tres audiencias, no dos:** humano → `01_Sala de lectura` (en claro, ordenado); pipeline/máquina
  interna → `02_Sala de máquina` (en claro, **con PII**, gitignored); **LLM externo → `06_Anonimizado`**
  (tapado). La "Sala de máquina" es el taller determinista del pipeline, NO lo que lee el LLM externo:
  el muro claro(`01`)/tapado(`06`) del proyecto se mantiene intacto.
- `ensure_case` hoy crea eager `01_Procesado/{Sala lectura, MD, _revisar}`
  ([case_manager.py:267](../core/case_manager.py:267)). La migración renombra `Sala lectura` →
  `01_Sala de lectura` y crea `02_Sala de máquina/` (fase F0). Cada subcarpeta de producto se crea
  bajo demanda por la etapa que la escribe, como hoy hace el extractor con `raw_text/`.
- Naming "tipo oración" respetado; numeración `01_`/`02_` como el resto del árbol del caso.

### G.1bis Espejos (mirror) — los productos replican la jerarquía de origen
Hoy `MD/` es **plano** ([markdown_generator.py:25](../core/markdown_generator.py:25)); el espejar
quedó pendiente (`docs/PLAN_SALA_LECTURA_01_PROCESADO.md:164-168`). Decisión: cada producto vive en la
**misma ruta relativa que su fuente en `00_Input/`**, dentro de su carpeta de etapa. Beneficios:
navegación en paralelo al origen y **resuelve de raíz el bug #47** (los cuatro `_chat.txt` que se
pisaban dejan de colisionar al colgar de rutas distintas). Cuidado con el límite de 260 chars de ruta
en Windows → nombre de fichero por `{slug}__{sha8}` (corto). Frontmatter del espejo, estilo Vassal:
`id (doc-NNN), sha, source, type, date, pages, extraction_method` + **`mirror_stale`** (idempotencia:
marca el espejo como desactualizado si cambió el origen).

### G.2 Victoria barata (primer paso de código — fase F3)
Persistir el PDF del OCR. Hoy [`api._ocr_y_extraer`](../core/anon/api.py:254) escribe el PDF
buscable en `tempfile.mkdtemp` y lo borra con `shutil.rmtree` (`api.py:270,283-284`).
[`anon/ocr.py::ocr_pdf`](../core/anon/ocr.py:30) **ya acepta ruta de salida explícita** y crea
su carpeta → basta apuntarla a `01_Procesado/OCR/{id}.pdf` en vez del tempdir. Efecto: el PDF
buscable queda guardado, la anonimización y el resto lo **reutilizan**, y se acaba el doble OCR.
Máximo retorno por el menor cambio.

### G.3 Identidad de documento — DUAL (decidido)
Hoy fragmentada en 4-5 esquemas: `output_slug` = `slug__sha8` ([utils.py:32](../core/utils.py:32)) en
extractor/MD; `id_doc = sha[:12]` en el catálogo ([catalogo_documental.py:109](../core/catalogo_documental.py:109));
`slugify(stem)` + sha8 distinto en anon ([api.py:239-242](../core/anon/api.py:239)); el nombre del split
por tipo procesal; y el nombre canónico legible `AAAA-MM-DD_descripción`. Decisión: **id dual**.
- **`sha8`** (interno, estable, atado al contenido): dedup automática, resuelve #47. Nombre de fichero
  de artefacto = `slug__sha8` (reutiliza `output_slug`), regenerable y dedup-safe.
- **`doc-NNN`** (legible, estilo Vassal): asa humana en el registro y en referencias.
- El registro (§H) **mapea `doc-NNN ↔ sha8 ↔ rutas`**; el nombre canónico legible se reserva a la
  vista de la Sala de lectura, no a los ficheros del pipeline.

### G.4 Registro de cobertura → registro ÚNICO de caso (ver §H)
El registro de cobertura deja de ser de fase y se eleva a **ámbito CASO** (decisión), consolidando los
registros que hoy solapan. Diseño completo en **§H**. Sigue siendo la respuesta a §E.13 (consultable) y
§D.1 (nada se cae en silencio).

### G.5 Estado / idempotencia por etapa
Consolidar el estado en el propio ledger (o un `_stage_state.json`) con SHA de origen + versión de
motor, siguiendo el patrón de `_extract_state.json`
([extractor.py:39,299-303](../core/extractor.py:299)): re-ejecutar salta lo no cambiado y jamás
re-toca `00_Input/`.

### G.6 Split 1→N y merge N→1
Un bundle produce N documentos; un merge junta N ficheros en 1. Los PDFs lógicos resultantes van a
`02_Sala de máquina/02_Documentos/`; la relación con el bundle se expresa con `parent_id`/`role_in_bundle`
del registro (no con subcarpetas). El índice de segmentación de [`separar.py`](../core/anon/separar.py)
(`indice.json`) se integra en el registro.

### G.7 reocr condicional por calidad — DECIDIDO (funde el hueco de >30pp)
En vez del rescate manual actual (`scripts/ocr_textless_pdfs.py`, invocado a mano), el OCR escribe en el
registro `ocr_quality` (`ok | low | empty`) + `ocr_quality_reason`; si es `low`/`empty`, se dispara un
**reocr automático**. El motor por página con subproceso aislado que ya existe
([`core/ocr_per_page.py`](../core/ocr_per_page.py)) pasa a ser esa etapa `reocr`, disparada por **calidad**,
no por un comando manual (patrón tomado de Vassal, §I). Marca `ocr_reattempted` en el registro. Esto
**funde en un solo mecanismo**: el hueco de >30pp (§B.2), la banda muerta de umbrales 100 vs 50 (§B.3,
ahora un único campo `ocr_quality`) y el control de calidad del OCR (§D.2).

---

## H. Registro único de caso (estilo Vassal `index.yaml`)

Hoy el único registro de ámbito-caso es `00_Input/_caso.md` (solo metadatos); los demás son de fase
(`_inventory.json`, `indice_documental.yaml`, `_MANIFIESTO.md`, `_intake_log.jsonl`) y **solapan** en el
dedup por hash (el propio repo lo reconoce sin resolver). Decisión: **un registro único de caso**,
tomando el modelo de Vassal.

- **Elevar+extender `indice_documental.yaml`** ([`core/catalogo_documental.py`](../core/catalogo_documental.py),
  `CatalogEntry`) a **ámbito CASO** (raíz del caso, p. ej. `<caso>/_indice_documental.yaml`), consolidando
  los registros que hoy solapan.
- **Campos por documento** (unión de los actuales + Vassal `index.yaml`):
  `id (doc-NNN), sha, file, mirror, type, title, date, parties, summary, source, seal, signature,
  completeness (full|partial|fragment), quality, pages, ocr_quality, ocr_quality_reason, ocr_reattempted,
  mirror_stale, filing_status, filing_folder, tags, bundle_id, parent_id, role_in_bundle (head|attachment)`.
  Los campos de OCR-calidad y `mirror_stale` habilitan §G.7 y la idempotencia; `bundle_id/parent_id/role_in_bundle`
  cubren el 1→N del split (§G.6).
- **Las vistas humanas se DERIVAN del registro**, no se mantienen a mano: `01_Sala de lectura/INDICE.md`,
  `CRONOLOGIA.md` y un **`.xlsx`** (reutilizar la skill `xlsx`), igual que Vassal genera su `.xlsx` desde
  `index.yaml` (`catalog` → `scripts/generate_table.py`).

## I. Aprendizajes de Vassal Litigator

Referencia: `https://github.com/strigov/vassal-litigator` — plugin de Claude Cowork para litigio (14 skills,
espejos MD, registro único `index.yaml`, `reocr` condicional). Es la dirección de FeesDefender.

**Qué se adopta:**
| Idea de Vassal | Aplicación en FeesDefender |
|---|---|
| `mirrors/` con frontmatter | Espejos MD en `03_MD/` que espejan la jerarquía de origen (§G.1bis) |
| `index.yaml` único de caso | Registro único de caso (§H) |
| `mirror_stale` | Idempotencia del espejo (§G.1bis/§H) |
| `reocr` disparado por `ocr_quality` | Etapa reocr automática (§G.7) |
| Preview→Apply + `history.md` | Confirmación humana antes de aplicar + auditoría de acciones a nivel de caso |
| Vista `.xlsx` derivada del índice | Sala de lectura derivada del registro (§H) |

**Qué NO se copia literal:**
- El `.vassal/` **oculto** que agrupa todo lo de máquina: FeesDefender ya usa carpetas numeradas
  top-level (`00_Input`…`07_AI cowork`) y una "Sala de máquina" **visible** numerada (decisión de Nikolai,
  mejor para audiencia mixta). Se adopta el *principio* (zona de máquina clara + registro único), no la estructura.
- Vassal **no anonimiza**; FeesDefender mantiene `06_Anonimizado` como capa tapada para el LLM externo.

---

## J. Botón "Reorganizar caso" (migración de casos antiguos a la estructura nueva)

Los casos antiguos tienen otra estructura (MD plano, `Sala lectura` sin numerar, sin `02_Sala de máquina`
ni registro único). Se necesita un botón repetible para llevarlos al layout nuevo, seguro y por flota.

- **Idea rectora:** la Sala de máquina es **regenerable desde `00_Input/`** → migrar ≈ (a) renombrar
  `Sala lectura` → `01_Sala de lectura`, (b) crear `02_Sala de máquina/`, (c) re-ejecutar el pipeline en
  el layout nuevo (regenera `01_OCR/02_Documentos/03_MD` como espejos) + reconstruir el registro único
  (§H). **Nunca** se tocan `00_Input/` ni `90_Notas personales/`.
- **Reutilizar el patrón existente** (no inventar): `plan`/`apply` con artefacto revisable + **journal
  reversible + backups `.bak`** de [`scripts/migrate_05crm_buckets.py`](../scripts/migrate_05crm_buckets.py)
  (re-llavea `_intake_hashes.json` y `_extract_state.json` para preservar dedup y cache OCR); gate humano
  con confirmación literal como [`scripts/migrate_to_city_structure.py`](../scripts/migrate_to_city_structure.py);
  verificador post tipo [`scripts/verify_city_layout.py`](../scripts/verify_city_layout.py).
- **Pieza nueva — sello `layout_version` (decisión):** añadir `layout_version: N` a `00_Input/_caso.md`
  (análogo de `EXTRACTOR_VERSION`, [extractor.py:37](../core/extractor.py:37)). Hoy **no existe** un sello
  de versión de layout por caso — el estado se infiere del filesystem, frágil para una flota. Con el sello,
  el botón lee la versión, sabe qué pasos aplicar, migra hacia delante y re-sella; y habilita un modo
  **"reorganizar todos"** que recorre la flota y reporta casos atrasados.
- **Cablear `--force`:** hoy `run_pipeline`/`pipeline.run` **no** tienen `--force` (solo
  [`extractor.extract_all(force=)`](../core/extractor.py:329), sin cablear). Hace falta para forzar la
  regeneración en el layout nuevo.
- **Dónde vive:** CLI `scripts/reorganizar_caso.py` (`plan`/`apply`, por caso y `--todos`) + botón Streamlit;
  ejecución local. Fase **F0**.

## K. Botón "Reformar plugin/skills" + mantenimiento continuo

Al cambiar el código que afecta a los procesos (nombres de carpeta, taxonomía, rutas), las skills y
conectores del plugin deben reconstruirse. Se necesita un botón que lo haga y avise de lo que queda desalineado.

- **Orquestador `scripts/rebuild_plugin.py` (un clic):** encadena la cadena que **ya existe** →
  [`sync_skill_helpers`](../scripts/sync_skill_helpers.py) → [`sync_taxonomia_skills`](../scripts/sync_taxonomia_skills.py)
  → [`validate_skills`](../scripts/validate_skills.py) → [`check_skills`](../scripts/check_skills.py) (drift)
  → [`package_skill --all`](../scripts/package_skill.py) + [`package_plugin`](../scripts/package_plugin.py)
  → imprime "qué cambió / qué re-importar en el servidor".
- **Frontera honesta (decisión), dos capas:**
  - *Mecánica* (automatizable a un clic): helpers `_shared`, taxonomía (`TAXONOMIA_EV`), constantes de
    carpetas (`CASO_SUBDIRS`), repackage, frescura del `.skill`.
  - *Semántica* (detectar+señalar, **no** reescribir): la prosa de las skills que menciona rutas/procesos
    (p. ej. `02_Sala de máquina`, `index.yaml`). El botón **lista** las skills afectadas por el cambio de
    proceso → handoff a Claude Code para editar el `SKILL.md` (mismo modelo de handoff que
    [`motor_mejora.py`](../scripts/motor_mejora.py) / `docs/MEJORA_CONTINUA_SKILLS.md`).
- **Drift no-silencioso (decisión):** enganchar `check_skills --strict` a un **hook** (skill
  `session-start-hook`, o pre-commit) para que el sistema avise solo al tocar código que afecta procesos,
  en vez de depender de correrlo a mano al cerrar sesión (hoy todo es "modo AVISO").
- **Disparador concreto:** el propio refactor de este documento (renombrar a `01_Sala de lectura`, crear
  `02_Sala de máquina`, registro `index.yaml`) **romperá la prosa** de varias de las ~18 skills que citan
  rutas viejas → el botón K es lo que permite aterrizar el refactor limpio por toda la biblioteca. Fase **F4**
  (+ mantenimiento continuo).

---

## Orden de ejecución sugerido (trabajo futuro)

1. **Saneamiento barato y layout (F0):** renombrar `Sala lectura` → `01_Sala de lectura`, crear
   `02_Sala de máquina/`, migrar W-02VND1; alinear umbrales (B.3), corregir docstring/etiqueta (B.4, B.5),
   unificar el set de extensiones de imagen + HEIC (C).
2. **Registro único de caso (F1)** — §H, con id dual (§G.3); cimiento de observabilidad + vistas derivadas.
3. **Fachada única (F2)** (E.10) + desacople de rutas (E.11) + salida estructurada (E.13).
4. **Motor OCR único + reocr por calidad + espejos (F3)** — OCRmyPDF (PDF buscable), reocr §G.7,
   persistir en `02_Sala de máquina/{01_OCR,02_Documentos,03_MD}`, reordenar split→MD.
5. **Conector MCP + empaquetado en el plugin (F4)** (E.12/14/15/16).
6. **Faltas restantes (F5)** (D.2–D.9) según disparador real.

## Fuera de alcance de este documento

- El refactor real del código (fachada, motor único, reordenación).
- La construcción del conector MCP y su empaquetado.
- El cierre de las faltas D.1–D.9.
