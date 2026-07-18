---
estado: vigente
dueño: Nikolai (arquitectura) + Claude Code (implementación)
disparador: encargo de Nikolai — "organizar la sala de máquinas desde Cowork"; retomar la vía lean [SIGUIENTE-SKILL-EXPEDIENTE-A-MD]
banco_de_pruebas: W-02VND1 (Tibidabo 8) — golden fixture ya usado por email_atomize
---

# SPEC — `organizar-sala-maquina`: OCR + MD del expediente (construye la Sala de máquina)

**Versión:** 1.0 (diseño cerrado; anclado al código real de FeesDefender)
**Fecha:** 2026-07-09
**Naturaleza:** documento de DISEÑO. El siguiente paso es `writing-plans`, no construir.
**Origen:** materializa la vía lean del apéndice de `docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md`
(`[SIGUIENTE-SKILL-EXPEDIENTE-A-MD]` en `PLAN.md`, diseño cerrado 2026-07-04), renombrada a
`organizar-sala-maquina` y reconciliada con el ecosistema de `abrir-caso`
(`docs/superpowers/specs/2026-07-09-abrir-caso-design.md`, otra sesión).

---

## 0. Problema que resuelve

El pipeline de procesado documental está **a medias**: el `extractor` saca texto crudo a
`01_Procesado/raw_text/{slug}.txt` y `markdown_generator` lo envuelve en `01_Procesado/MD/`,
pero:

1. **El OCR es efímero.** `core/anon/api._ocr_y_extraer` genera el PDF buscable en un
   `tempfile.mkdtemp` y lo **borra** (`shutil.rmtree`). Cada camino re-OCR-iza → doble trabajo
   y "cada camino lee distinto".
2. **Hueco de escaneados >30 pp.** `extractor` capa el OCR de Docling a `MAX_OCR_PAGINAS = 30`
   (anti-OOM de RapidOCR); por encima marca `sin_texto` → `.md` vacío, invisible a
   `scorer`/`viability`. Rescate manual con otro motor. **Nadie avisa** (fallo silencioso).
3. **No hay una "sala de máquina" en disco.** Los productos de máquina viven planos y
   dispersos; no hay una carpeta que el abogado (ni Cowork) reconozca como el taller del
   pipeline.

`organizar-sala-maquina` cierra este medio-desarrollo con una **skill lean**: orquesta los
motores que YA existen para producir, de forma persistente e idempotente, los dos artefactos
de máquina de primera clase (**PDF buscable** + **MD legible**) bajo una **Sala de máquina**
numerada, sin arrastrar el aparato pesado del motor completo (registro único, split,
reorganización de flota), que sigue aparcado.

---

## 1. Alcance

**Incluye:** enrutar cada fichero de `00_Input/` por tipo; producir el **PDF buscable** con
OCRmyPDF para escaneados/imágenes y persistirlo; extraer texto (nativo o del PDF buscable) a
**MD** con frontmatter trazable; escribir un **registro de cobertura** (`_cobertura.md`) que
marca el estado de cada documento (sin fallo silencioso); idempotencia por `sha256`;
Preview→Apply; y **sugerir** `organizar-sala-lectura` como siguiente paso.

**No incluye:**
- **Organización de la sala de lectura** — la ejecuta `organizar-sala-lectura` (se sugiere, no
  se encadena; ver §12).
- **Split/merge** de documentos compuestos (`02_Documentos/`), **registro único** `index.yaml`,
  id `doc-NNN`, **reocr-torch automático**, **anonimización** (`06_`), **botón de reorganizar
  flota** y **renombrado** `Sala lectura`→`01_Sala de lectura`: todo eso es el **motor completo**
  (`docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md`, aparcado). Ver §11 y §15.
- **Alta de caso / intake / CRM** — eso es `abrir-caso` (un eslabón antes).
- `90_Notas personales/` es zona reservada del abogado: ningún paso la lee ni la escribe.

**Fuente:** todo `00_Input/` excepto `90_Notas personales/`. **Entorno:** ejecución **local**
(Claude Code / CLI en el PC con OCRmyPDF); Cowork = director/revisor (§11).

---

## 2. Decisiones cerradas (brainstorming 2026-07-09)

| # | Decisión | Resolución |
|---|---|---|
| D1 | **Enfoque** | **Skill lean, local.** Orquesta motores existentes; Cowork dirige, no ejecuta OCR (no tiene los binarios). |
| D2 | **Layout** | Escribe en **`01_Procesado/02_Sala de máquina/{01_OCR, 03_MD, raw_text}`**. Crea la carpeta; **no** renombra `Sala lectura` (ver D6). |
| D3 | **Motor OCR** | **OCRmyPDF** (fijado) — página a página, sin tope de 30 pp, `spa+cat+rus`. **Claude visión = refuerzo OPCIONAL** (off por defecto) para páginas duras. |
| D4 | **Handoff a sala de lectura** | **Sugerir (puntero atómico)**, no encadenar. Alinea con el modelo del ecosistema de `abrir-caso`. |
| D5 | **Red de seguridad de calidad** | `ocr_quality` = **densidad char/pág + ratio de gibberish + check de idioma `spa/cat/rus`** (no solo conteo de chars: caza la basura legible que un umbral de longitud deja pasar). `_revisar/_cobertura.md` = **worklist de revisión humana** (lista `low`/`empty`/`gibberish` con motivo). **Sin fallo silencioso.** El reocr automático + audit completo es del motor (§D.2/§G.7), diferido. |
| D5b | **NO se usa `pipeline.run()`** | La skill **no** invoca el orquestador actual **ni la rama OCR (Docling, tope 30 pp) del extractor** — la pieza diagnosticada como no-óptima (§B del motor). Reutiliza solo los **helpers deterministas sanos** del extractor + OCRmyPDF aguas arriba (ver §5.1). |
| D6 | **Renombrado `Sala lectura`→`01_Sala de lectura`** | **Fuera de alcance.** Los casos existentes ya tienen `Sala lectura/` con contenido en el Drive; renombrar solo en código deja las dos carpetas (drift). Exige la migración de flota (`reorganizar_caso`+`layout_version`) = **motor F0**. |
| D7 | **raw_text** | Se **conserva** como sub-artefacto **sin numerar** dentro de `02_Sala de máquina/` (ancla de idempotencia + debug), no como producto de cabecera. |
| D8 | **Integración en el ecosistema** | Cliente futuro del patrón **grafo único** (`MEJORAS #50`, otra sesión). Ahora solo la **descripción disambiguada** del frontmatter; **no** se hand-escribe sección de ecosistema. |
| D9 | **Nombre** | `organizar-sala-maquina` (dir ASCII, como `organizar-sala-lectura`); "sala de máquina" en la descripción. Jubila el nombre `expediente-a-md`. |

---

## 3. Arquitectura — 3 capas (patrón del repo)

Mismo reparto que `abrir-caso` y `email_export`: cerebro con la lógica de decisión + un
orquestador que llama al músculo de I/O + la skill que dispara.

| Capa | Responsabilidad | Determinista | Toca bytes |
|---|---|---|---|
| `core/sala_maquina.py` | `plan(inventario)` (enrutado por tipo, dedup por sha, skip incremental), modelo de `Cobertura`, render de `_cobertura.md` | Sí (puro, testeable) | No |
| `core/*` existentes | OCR (`anon.ocr.ocr_pdf`), extracción (`extractor`), MD (`markdown_generator`), catálogo (`catalogo_documental`), log (`intake_log`) | — | Sí |
| `scripts/sala_maquina.py` (Typer) | orquesta `plan`→OCR→extracción→MD→cobertura; gates Preview→Apply, `--dry-run`, `--vision` | No | vía core |
| `.claude/skills/organizar-sala-maquina/` | dispara, presenta la propuesta, sugiere el siguiente paso | No | vía CLI |

### 3.1 `core/sala_maquina.py` — CEREBRO (I/O acotado a la etapa OCR/extracción)
- `plan(inventario, estado_previo) -> Plan` **(puro)** — por cada fichero decide **ruta**
  (§5) y **destino** canónico (`output_slug` = `slug__sha8`), marca `skip` si el `sha256` ya
  consta procesado (patrón `_extract_state.json`). Sin tocar bytes. En `--dry-run` termina aquí.
- `ejecutar(plan, opciones) -> Cobertura` — recorre el plan llamando a los motores; escribe
  `01_OCR/`, `03_MD/`, `raw_text/`. Aislamiento por subproceso por documento (patrón
  `ocr_textless_pdfs.py`) para que un OOM no tumbe la corrida.
- `render_cobertura(cobertura) -> str` **(puro)** — Markdown de `_cobertura.md`.

**El cerebro no importa la red ni el conector.** Los tests unitarios cubren `plan` y
`render_cobertura`; la integración cubre `ejecutar` sobre PDFs reales/mock.

---

## 4. Layout en disco

```
01_Procesado/
├── Sala lectura/            ← existente; NO se toca (renombrado = motor F0, D6)
├── MD/  ·  raw_text/        ← legacy de pipeline.run; coexisten (deuda → motor unifica, §15)
├── 02_Sala de máquina/      ← NUEVO — lo crea y posee esta skill
│   ├── 01_OCR/              producto: PDFs BUSCABLES  {slug__sha8}.pdf   (custodia)
│   ├── 03_MD/               producto: markdown legible {slug__sha8}.md
│   └── raw_text/            intermedio SIN numerar (idempotencia + debug, D7)
└── _revisar/
    └── _cobertura.md        registro de cobertura (sin fallo silencioso, D5)
```
El hueco `02_Documentos/` (split) se **reserva** en la numeración pero **no se crea**: es del
motor. `03_MD/` va numerado como en el layout objetivo del motor (§G.1) para que la skill sea
un **anticipo compatible**, no scaffolding que haya que migrar.

---

## 5. Enrutado por tipo y motor

| Entrada | Camino | Persiste en `01_OCR/` | Persiste MD |
|---|---|---|---|
| PDF con capa de texto (`_texto_suficiente`: ≥100 chars y ≥40 char/pág) | `pypdf` (sin OCR) | No (ya buscable) | Sí |
| PDF escaneado / imagen / `.heic` | `imagen_a_pdf`(si imagen) → **OCRmyPDF** → PDF buscable → extraer texto | **Sí** | Sí |
| `.eml` / WhatsApp `_chat.txt` / `.docx` / `.txt` / `.csv` / `.xlsx` | texto nativo (`extractor`) | No | Sí |

- **Motor OCR: OCRmyPDF** vía `core/anon/ocr.py::ocr_pdf` (ya acepta ruta de salida explícita y
  crea la carpeta) apuntado a `02_Sala de máquina/01_OCR/{slug__sha8}.pdf` — la **victoria
  barata** (§G.2 del motor): el PDF buscable queda guardado y todo lo reutiliza (fin del doble
  OCR). ⚠️ **Prerrequisito de código:** verificar/reparar la firma de `ocr_pdf` hacia
  `ocrmypdf.ocr` (bug latente `MEJORAS #11`) antes del E2E.
- **>30 pp:** OCRmyPDF va **página a página** → **no hay tope de 30 pp** ni OOM. La skill
  **cierra el hueco** de escaneados largos que hoy salen vacíos (§B.2 del motor).
- **Visión (opcional, `--vision`, off por defecto):** para páginas con `ocr_quality` pobre
  (manuscrito/tablas), refuerza el MD con Claude visión (Sonnet 5/Opus 4.8) renderizando la
  página con `pypdfium2`. **No** genera PDF buscable (eso solo OCRmyPDF). Gateado por la regla
  PII relajada temporalmente (§10).

### 5.1 Qué se reutiliza y qué NO (por qué no el `pipeline.run()` actual)

El flujo actual (`core/pipeline.py::run`) enruta los PDF escaneados por **Docling con tope de
`MAX_OCR_PAGINAS = 30`** (`extractor._extract_one`, líneas 246-247) — la pieza diagnosticada
como **no-óptima** (§B del motor: OOM/segfault de RapidOCR, hueco >30 pp → `.md` vacío, fallo
silencioso). `organizar-sala-maquina` **no lo usa**:

- **NO invoca** `pipeline.run()` ni `extractor._extract_one` (que embebe la rama Docling/30 pp).
- **SÍ reutiliza los helpers deterministas SANOS** de `extractor`: `_try_pypdf` +
  `_texto_suficiente` (enrutado del PDF digital), `_try_email`/`_try_rtf`/`_try_ics`/
  `_try_pandas_table`/`_try_docx`/`_read_text_file` (nativos), y `markdown_generator.build`
  (envoltura MD con frontmatter).
- El **OCR va aguas arriba con OCRmyPDF** (`anon.ocr.ocr_pdf`, página a página, sin tope) →
  produce el **PDF buscable** en `01_OCR/` → el texto se extrae de ese PDF ya buscable con
  `_try_pypdf`. **Docling queda completamente fuera del camino.**

Así se cierra el hueco de >30 pp y se elimina el doble OCR sin heredar la orquestación viciada.
La unificación definitiva (una sola fachada `procesar_expediente()`) es del motor (F1), fuera
de alcance.

### 5.2 Red de seguridad de calidad (`ocr_quality`)

Por cada documento OCR-izado se computa un `ocr_quality ∈ {ok, low, empty}` con **tres señales**
(no solo conteo de chars, que deja pasar la basura legible):

1. **Densidad** char/pág (reutiliza el umbral de `_texto_suficiente`).
2. **Ratio de gibberish** — fracción de tokens sin vocal / secuencias no-léxicas; alto ⇒ OCR
   ruidoso aunque haya muchos chars.
3. **Idioma** — el texto es mayoritariamente palabras reales en `spa/cat/rus` (heurística
   ligera, sin modelo pesado); si no casa ⇒ sospecha de gibberish/idioma no soportado.

`low`/`empty`/gibberish **no abortan**: se persisten igual, se marcan en `_cobertura.md` como
**worklist de revisión humana** (con motivo), y el reporte final dice "N documentos requieren tu
revisión / candidatos a `--vision`". Es **marca-y-expón para el humano**, no garantía automática:
el **reocr automático por calidad** (motor §G.7) y el **audit completo** (motor §D.2) quedan
diferidos.

---

## 6. Pipeline

1. **Inventario.** Listar `00_Input/` (todas las fuentes salvo `90_Notas personales/`),
   calcular `sha256` de cada fichero.
2. **`plan`** (puro): enrutar + destino canónico + skip incremental por `sha256`. `--dry-run`
   reporta el plan y termina.
3. **(GATE Preview→Apply)** presentar la propuesta (contadores por ruta, nuevos vs saltados,
   escaneados >30 pp que antes se caían) y **esperar OK**.
4. **`ejecutar`** (tras OK): por documento, según ruta (§5), escribir `01_OCR/` (si aplica),
   `raw_text/` y `03_MD/`. Aislamiento por subproceso.
5. **Cobertura:** escribir `_revisar/_cobertura.md` (D5) + evento en `_intake_log.jsonl`
   (`append_event`, hash forense).
6. **Reporte + handoff:** nº por ruta, escaneados rescatados, documentos `empty`/`low` a
   revisar; **sugerir** `organizar-sala-lectura` sobre este caso (puntero, no ejecutar).

---

## 7. Contratos de datos

- **MD (`03_MD/{slug__sha8}.md`):** reutiliza el frontmatter de `markdown_generator`
  (`case_id`, `tipo`, `fase`, `source_path`, `extractor`/método, `chars`, `tokens_estim`,
  `text_sha256`) + `ocr_quality` (`ok`/`low`/`empty`) cuando el camino fue OCR. Nombre
  `slug__sha8` (resuelve la colisión de stem #47).
- **`_cobertura.md`:** cabecera `<!-- GENERADO — NO EDITAR A MANO -->`; una fila por documento:
  `nombre_canonico | ruta_original | método | estado (ok/low/empty/sin_texto) | chars | ocr | notas`.
- **`_intake_log.jsonl`:** evento `procesado_sala_maquina` (nuevo en `INTAKE_EVENTS`),
  `details = {count, files:[{path, sha256, metodo, estado}]}`.
- **Catálogo:** opcional — alimentar `catalogo_documental` como hoy; el **registro único**
  `index.yaml` es del motor (§H), fuera de alcance.

---

## 8. Idempotencia y reejecución

- **Skip por `sha256`** (patrón `_extract_state.json` + flag `skipped`): re-correr solo procesa
  lo nuevo; `raw_text/` persistido es el ancla (D7) → regenera MD sin re-OCR.
- **`00_Input/` intocable** — invariante forzado por guard/test (M5): la corrida falla si algo
  intenta escribir en `00_Input/` o `90_Notas personales/`.
- **Nunca borra** productos previos de la sala de máquina; solo añade/actualiza.
- `--force` para regenerar (sube `EXTRACTOR_VERSION`/versión de motor invalida el cache).
- `--dry-run` para plan sin efectos.

---

## 9. Manejo de errores (sin fallo silencioso)

| Fallo | Comportamiento |
|---|---|
| OCRmyPDF error (cifrado/protegido, rc 15/16) | documento `empty` + motivo en `_cobertura.md`; sigue con el resto |
| Escaneado sin texto tras OCR | `empty` + nota; candidato a `--vision` |
| Texto pobre (`ocr_quality=low`) | se persiste + se marca en cobertura para revisión humana |
| `.heic`/imagen sin rama | `imagen_a_pdf` → OCR; si falla, `sin_texto` reportado (nunca se cae del inventario en silencio) |
| Documento ya procesado (sha) | `skip`, reportado |
| OOM en un documento | subproceso aislado muere; se marca `empty` y la corrida continúa |

---

## 10. Seguridad e invariantes

- Ejecución **local**; los bytes no pasan por el chat.
- **`00_Input/` y `90_Notas personales/` intocables** (guard/test, M5).
- **SHA-256** de cada producto en el log (cadena de custodia).
- **Regla PII relajada temporalmente** (decisión §L del motor, 2026-07-04): el MD en claro y el
  refuerzo de visión cloud son **deuda consciente**, con gate de reinstauración del muro `06`.
  La skill respeta el objetivo final `01`-claro/`06`-tapado; la anonimización es el último
  eslabón, fuera de esta skill.
- Docs/commits referencian por `W-XXXXX` (regla `docs/SEGURIDAD_DATOS.md`).

---

## 11. Cowork (director fino)

La skill corre **local** (necesita OCRmyPDF/Tesseract). Cowork, por el puente MCP
`expedientes`, **lee** `02_Sala de máquina/` + `_cobertura.md` para **revisar/aprobar**; no
ejecuta OCR. No se construye companion de Cowork ahora: su empaquetado como conector (con
preflight/doctor) es la **fase F4** del motor (aparcada). Se documenta el flujo en el
`SKILL.md`.

---

## 12. Relación con el ecosistema (mínimo; patrón #50 diferido)

Lugar en el flujo (confirmado con `abrir-caso` §12):
```
abrir-caso ──► organizar-sala-maquina ──► organizar-sala-lectura ──► viabilidad-prerelleno
 (crea+intake+CRM)  (OCR/MD — ESTA skill)   (vista humana)            (informe)
```
- **Predecesor:** `abrir-caso` (caso nuevo) o `intake-expediente` (ficheros añadidos a un caso
  existente). Lee `00_Input/` sin importar quién lo pobló.
- **Handoff (D4):** al terminar **sugiere** `organizar-sala-lectura` (puntero atómico), como
  `abrir-caso` sugiere a esta skill. No encadena.
- **Solape:** ninguno con `organizar-sala-lectura` — aquella organiza la **sala de lectura**
  (vista humana, clasificación E&V, copia con nombre canónico) leyendo `00_Input`; esta produce
  la **sala de máquina** (OCR/MD). Fronteras disjuntas.

**Gobernanza (regla de Nikolai):** la "sección de ecosistema" de las skills **no se escribe a
mano** (drift bidireccional). El diseño robusto — grafo único + generador + guardarraíl — vive
en `MEJORAS #50` como trabajo de otra sesión. Esta skill será un **cliente** de ese patrón:
por ahora declara su lugar solo vía la **descripción disambiguada** del frontmatter; el bloque
embebido `<!-- ECOSISTEMA:... -->` se añadirá cuando #50 aterrice. **No** se edita
`ARQUITECTURA_RELACIONES.md §3c` a mano desde esta skill.

---

## 13. Fases (build incremental, tests por fase)

- **F1 — cerebro + CLI local (walking skeleton).** `core/sala_maquina.py` (`plan`,
  `render_cobertura` puros; `ejecutar`) + `scripts/sala_maquina.py` (Typer, Preview→Apply,
  `--dry-run`). Reparar/verificar `ocr_pdf` (#11). Un documento real de punta a punta
  (PDF escaneado → PDF buscable en `01_OCR` → MD → cobertura). **Retorno inmediato.**
- **F2 — cobertura completa + rutas.** Todas las rutas de §5 (`.heic`, imagen, >30 pp,
  nativos); `_cobertura.md`; evento de log; skip incremental; guard `00_Input`. Corrida real
  sobre W-02VND1 (medir "de N documentos ciegos a 0").
- **F3 — skill + handoff.** `SKILL.md` (`organizar-sala-maquina`) desde `_plantilla-skill`
  (hereda estilo/verificación); descripción disambiguada; sugerencia de `organizar-sala-lectura`;
  sync helpers `_shared`; CHANGELOG; empaquetado `.skill`. `--vision` opcional detrás de flag.

---

## 14. Tests

- **Unit (core, puro):** `plan` (enrutado por extensión, dedup por sha, skip incremental,
  destino `slug__sha8`); `render_cobertura` (estados, orden estable); guard de `00_Input`
  (falla si un destino cae bajo `00_Input`/`90_Notas personales`); **`ocr_quality`** sobre
  fixtures — texto limpio `spa/cat/rus` ⇒ `ok`; gibberish denso (pasa el umbral de chars pero
  sin vocales/no-léxico) ⇒ `low`; vacío/residual ⇒ `empty`; idioma no soportado ⇒ marcado.
- **Integración:** PDF escaneado real/mock → PDF buscable persistido + MD + cobertura;
  PDF digital → pypdf sin OCR; `.heic`/imagen → OCR; nativo → texto; >30 pp no se cae;
  reejecución idempotente (skip por sha); `--force` regenera; OOM aislado marca `empty` sin
  tumbar la corrida.
- **Transcripción/visión mockeada** (sin llamadas reales) para el camino `--vision`.
- **Regresión:** no romper `extractor`/`markdown_generator`/`anon.ocr.ocr_pdf` para sus callers
  actuales.

---

## 15. Decisiones diferidas / deuda consciente (no bloquean F1)

1. **Coexistencia legacy `MD/` + `raw_text/` (de `pipeline.run`) vs `02_Sala de máquina/`.** Dos
   ubicaciones de MD hasta que la **fachada `procesar_expediente()`** del motor (F1) unifique.
   Mientras: para un caso procesado por esta skill, la fuente es la sala de máquina; el `MD/`
   legacy queda obsoleto (no se borra).
2. **Renombrado `Sala lectura`→`01_Sala de lectura`** — motor F0 (D6).
3. **Espejo de jerarquía en `03_MD/`** (replicar rutas de `00_Input`, §G.1bis) — el motor lo
   hace; aquí `slug__sha8` ya evita la colisión #47, así que no bloquea.
4. **`rapidocr` como reocr-torch automático** — motor §G.7; aquí OCRmyPDF basta.
5. **Empaquetado como conector (Cowork ejecutor)** — motor F4.
6. **Registro único `index.yaml` / id `doc-NNN` / split** — motor F1/G.6.
7. **Aislamiento por documento: `try/except` en proceso, NO subproceso OS.** El §3.1/§9/§14
   describen "aislamiento por subproceso por documento (patrón `ocr_textless_pdfs.py`)". La
   implementación real de `ejecutar()` aísla cada documento con un `try/except` **en el mismo
   proceso**: protege de excepciones Python (OCRError, lock `~$` de Office, PDF que revienta
   pypdf), que es el grueso de los fallos reales, pero **no** de un segfault/OOM nativo (p. ej.
   `pypdfium2` en `--vision` sobre un PDF corrupto tumbaría el intérprete). Riesgo bajo tras
   abandonar RapidOCR/Docling (los motores que segfaulteaban); OCRmyPDF corre en su propio
   proceso vía su CLI. El **aislamiento por subproceso OS** (relanzar cada documento en un
   worker y cosechar el que muera) se **difiere al motor completo**, donde el volumen y los
   motores pesados lo justifican.
