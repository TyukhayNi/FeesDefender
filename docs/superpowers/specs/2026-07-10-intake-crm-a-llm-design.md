---
estado: revisar
dueño: Nikolai Tyukhay
fecha: 2026-07-10
tipo: brainstorming + runbook
---

> **⚠️ EN REVISIÓN — APROBACIÓN REVERTIDA 2026-07-10.** La aprobación previa (motor A2,
> ejes E2+E3+E4) se **retira**: se adoptó sin el proceso de brainstorming de superpowers
> y sobre cifras de ROI **no medidas**. Las decisiones de §6 vuelven a estar **abiertas**.
> Se re-brainstormea con método (sesión de Code con el plugin `superpowers` cargado) antes
> de adoptar nada. Puntos a estresar: (A) ROI sin medir → medir 1 caso real primero;
> (B) arbitraje €20/€60 sin recurso confirmado; (C) MD derivado vs original para un go/no-go
> jurídico; (D) caso de ejemplo VUELTA poco representativo; (E) opción mínima E2-solo no
> estresada; (F) sesgo de anclaje al converger.

# Bajada CRM → salas → registros → LLM

> **Documento de diseño (brainstorming) + runbook operativo.** Cubre el ciclo
> completo de un documento guardado en el **gestor documental (Gdocu) del CRM
> Sudespacho**: bajada (intake) a `05_CRM`, procesado en la **sala de máquina**
> (OCR/MD) y la **sala de lectura** (clasificación + índices), incorporación a los
> **registros del caso** y preparación para su lectura por un **LLM**.
>
> Las piezas ya existen por separado; lo que falta es **encadenarlas para la fuente
> CRM** y **cerrar dos decisiones de diseño** (§4 y §5). Este documento NO cambia
> `core/` ni las CLIs: documenta el estado, fija el runbook con lo existente y abre
> el brainstorming.

## 0. Propósito y alcance

- **En alcance:** documentar el flujo end-to-end para la fuente CRM; abrir el
  brainstorming del *motor de procesado* (§4) y de la *estrategia de consumo LLM por
  niveles* (§5). Consumidor LLM del alcance: la skill `viabilidad-prerelleno`.
- **Fuera de alcance:** construir el pipeline programático `core/viabilidad/*` de
  `docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md` (Haiku+Sonnet); refactor del motor
  documental (`docs/PLAN_MOTOR_DOCUMENTAL.md`, aparcado).

## 1. Estado verificado (código leído 2026-07-10)

| Etapa | Estado | Piezas (con `fichero:línea`) |
|---|---|---|
| Bajada Gdocu → `05_CRM` | **Hecha** (no cerrada en `PLAN.md`) | `core/sync_sudespacho.py`: `list_gdocu_docs_rest` (`:626`), `get_presigned_download_url` (`:744`, usa `GET /api/documents/{id}/downloadUri`), `pull_expediente_v2(..., physical_complete=…)` (`:1341`, contador `documents_overlap` + evento `cross_source_overlap`). `core/judicial_intake.py`: `intake_demanda_contestacion(..., full=…)` (`:73`) → `--full` = `only_doc_ids=None, physical_complete=True`. Auth REST solo `x-api-key` (sin PHPSESSID). |
| Sala de máquina | **Entregada 2026-07-09** | Skill `organizar-sala-maquina`; `core/sala_maquina.py` (dir `01_Procesado/02_Sala de máquina`, `:177`); CLI `scripts/sala_maquina.py {plan,apply}`. OCR OCRmyPDF (`core/anon/ocr.py`, `spa+cat+rus`, **sin tope de páginas**) → `{01_OCR,03_MD,raw_text}`; red de calidad `01_Procesado/_revisar/_cobertura.md` (`ocr_quality ∈ {ok,low,empty}`); idempotente por sha256; evento `procesado_sala_maquina`. |
| Sala de lectura | **Entregada** (core `sala_lectura.py` DEPRECADO 2026-06-18) | Skill `organizar-sala-lectura`; taxonomía `TAXONOMIA_EV`; salida plana + `INDICE.md`/`CRONOLOGIA.md`/`_MANIFIESTO.md`/`indice_documental.yaml` (SSOT documental, `core/catalogo_documental.py`). |
| LLM | **Existente (parcial)** | Skill `viabilidad-prerelleno` (lee `00_Input/`, hoja **AVISOS LLM**); anon `core/anon/api.py` → `06_Anonimizado/` (drop-zone `08_Para frontier/`); clientes `core/llm.py` (Ollama local), `core/llm_cloud.py`, `core/llm_local.py`. |

**Incoherencia detectada.** `scripts/sync_sudespacho.py intake-judicial --run-pipeline`
(`:284`) encadena el pipeline **VIEJO** `pipeline.run(...)` (extractor Docling ≤30 pp
→ `01_Procesado/raw_text/` + `06_Anonimizado/`), **no** las salas. El mismo documento
de `05_CRM` puede leerse con dos motores distintos (Docling ≤30 pp vs OCRmyPDF
ilimitado). Es el nudo del §4.

## 2. Runbook end-to-end (local — Windows/PowerShell)

> Todo el flujo es **local**: requiere `.env` con credenciales Sudespacho y OCRmyPDF
> instalado. Las salas tienen **gate humano** (Preview→Apply), así que no es un
> pipeline totalmente desatendido. Prefijar comandos con
> `cd "C:\Users\tnm33\Dev\FeesDefender"` y `.\.venv\Scripts\Activate.ps1`.

### 2.0 Tareas de intake por fuente

Un expediente se nutre de **seis fuentes**, cada una con su cajón en `00_Input/`, su punto
de entrada y su evento forense en `_intake_log.jsonl`. El CRM (paso 1 del runbook) es una de
ellas; el resto se listan aquí para el cuadro completo.

| Fuente | Destino `00_Input/` | Punto de entrada | Evento | Estado |
|---|---|---|---|---|
| Drive E&V | `01_Drive EV/` (carpeta `W-XXXXXX`) | `core/intake_drive.pull_drive_ev` (`:162`) / command `/pull-rclone` (rclone) | `pull_drive_ev` | ✅ |
| CRM sudespacho | `05_CRM/<rama>/` | `intake_demanda_contestacion(full=…)` / `intake-judicial --full` | `pull_crm`, `intake_judicial`, `cross_source_overlap` | ✅ |
| WhatsApp | `02_Whatsapp/<consultor>/` | `core/whatsapp_intake` (zip) / UI Streamlit | `upload_whatsapp` | ✅ |
| Email | `03_Email/<consultor>/` | `core/email_export` / skill `exportar-correos-etiqueta` | `upload_email` | ✅ |
| Manual | `04_Manual/` | `core/intake_manual` / expander Streamlit | `upload_manual` | ✅ |
| Entrevistas | `06_Entrevistas/<fecha>_<rol>/` | (transcripción Meet) | `upload_entrevista` | ⏳ `[SIGUIENTE-INTAKE-ENTREVISTAS]` |

**Orquestadores genéricos** (dirigen el alta + depósito sin tocar bytes por el modelo): skill
`intake-expediente` (conector MCP `expedientes-xl`, hash/copia/extracción server-side) y
`abrir-caso` (alta del caso + estructura). **Invariantes comunes a todas las fuentes:** SHA-256
por fichero, dedup por hash (`IntakeManifest`), guard de escritura (`dir_intake` — si el caso
está prestado, desvía a `_pendiente_checkin/`), y nunca se toca `90_Notas personales/`. Aguas
abajo, **las salas leen TODO `00_Input/`** (todas las fuentes juntas), no solo el CRM.

### 2.1 Secuencia end-to-end

1. **Bajar el expediente completo del Gdocu → `05_CRM`:**
   ```powershell
   python -m scripts.sync_sudespacho intake-judicial `
       --case "<case_id>" --expediente <id_judicial> --full --no-run-pipeline
   ```
   `--full` deja `05_CRM` **físicamente completo**. La salida JSON reporta
   `documents_total_crm / documents_written / documents_skipped_dedup /
   documents_overlap` y etiqueta demanda/contestación (los roles ambiguos avisan, no
   bloquean). Evita `--run-pipeline` aquí (motor viejo; ver §4).

2. **Sala de máquina (OCR + espejos MD):**
   ```powershell
   python -m scripts.sala_maquina plan  "<case_id>"    # Preview (no escribe)
   python -m scripts.sala_maquina apply "<case_id>"    # [--vision] [--force]
   ```
   Procesa **todo** `00_Input/` (incluye `05_CRM`), incremental por sha256. Deja
   `01_Procesado/02_Sala de máquina/{01_OCR,03_MD}` y `_revisar/_cobertura.md`
   (revisar los `low`/`empty`; `--vision` refuerza los dudosos).

3. **Sala de lectura (clasificación E&V + índices):** invocar la skill
   `organizar-sala-lectura` sobre el caso (gate único de propuesta) → registros
   (`indice_documental.yaml`, `INDICE.md`, `CRONOLOGIA.md`, `_MANIFIESTO.md`).

4. **LLM:** invocar `viabilidad-prerelleno` (lee `00_Input/` incl. `05_CRM`; vuelca
   banderas a AVISOS LLM). Para LLM **externo/cloud**, anonimizar antes
   (`06_Anonimizado/` → `08_Para frontier/`). Ver §5 para la estrategia por niveles.

**Trazabilidad (`00_Input/_intake_log.jsonl`):** paso 1 → `pull_crm` /
`intake_judicial` / `cross_source_overlap`; paso 2 → `procesado_sala_maquina`. SHA-256
por fichero en cada evento.

## 3. Incorporación a los registros del caso

Cómo un documento del CRM queda **trazado e indexado**:

1. Aterriza en `05_CRM/<rama>/` — ruta resuelta por `crm_branch_path`
   (`core/case_manager.py:926`); buckets planos (`01_Demanda`, `02_Contestacion`, …,
   `99_Otros`, `99_Sin categoria/<exp>`). Tope conocido: mapping estático
   `CARPETA_ID_TO_PATH` (`core/config.py:559`); `id_carpeta` no mapeado →
   `99_Sin categoria/` + evento `category_unknown` (el árbol Gdocu no es reconstruible
   por API — dead end §13.3 de `INTEGRACION_SUDESPACHO.md`).
2. Tagging demanda/contestación por heurística de filename
   (`core/judicial_classifier.py`) — etiquetado, no filtro (con `--full` todo se baja).
3. `inventory.scan` → `_inventory.json`; `build_catalog` → `indice_documental.yaml`
   (SSOT documental, id = sha[:12]); la sala de lectura renderiza índices legibles.
4. Estado del pull en `00_Input/_caso.md` (`sudespacho_expedientes[]`, schema D8).

## 4. Brainstorming A — reconciliación del motor

**Problema.** Dos motores para el mismo material: (a) pipeline viejo
`core/pipeline.py::run` (extractor Docling, tope 30 pp, `raw_text/` + anon), encadenado
hoy por `intake-judicial --run-pipeline`; (b) salas nuevas (OCRmyPDF sin tope, red de
calidad, registros). Riesgo vivo: **doble extracción divergente** del mismo doc de
`05_CRM`, y **desgobierno de la anonimización** (las salas **no** anonimizan; el "muro
PII" está *relajado* desde 2026-07-04, deuda consciente).

**Opciones:**

- **A1 — Salas-only.** Deprecar el `--run-pipeline` viejo; tras el pull, correr las
  dos salas. *Pro:* motor único moderno, sin tope de páginas, red de calidad, un solo
  texto por doc. *Contra:* pierde el auto-encadenado de anon; las salas tienen gate
  humano (no desatendido); hay que reubicar dónde vive la anonimización.
- **A2 — Híbrido (recomendación de arranque).** Salas para OCR/MD/registros; pipeline
  viejo **solo** para el paso de anon (`06_Anonimizado/`) hasta migrar la anon a
  consumir los MD/OCR de la sala. *Pro:* elimina la doble extracción de texto
  conservando la anon existente; migración incremental. *Contra:* dos motores
  conviven un tiempo; hay que garantizar que la anon parte del OCR de la sala, no de
  un re-OCR Docling.
- **A3 — Solo documentar el canónico.** No tocar código; declarar salas = canónico,
  pipeline = legacy, y planificar la migración. *Pro:* coste cero ahora. *Contra:* la
  incoherencia y el riesgo de doble extracción siguen vivos.

**Enlaces:** `[SIGUIENTE-MOTOR-DOCUMENTAL]` (aparcado, unificación grande),
`[SIGUIENTE-SALA-UNICA-PLANA]`, `docs/PLAN_INTAKE_CRM_COMPLETO.md` (su "Paso 2" quedó
desfasado). **A decidir con Nikolai.**

## 5. Brainstorming B — consumo LLM por niveles (economía de tokens)

> **Estado de esta sección (2026-07-10):** el catálogo de ejes de abajo se **baraja como
> prioritario, pero NO está adoptado**. Queda como decisión abierta (§6). Se conserva la
> explicación del flujo y la estimación de tiempo para poder decidir con datos.

### 5.0 Estado del flujo de viabilidad hoy: los dos mundos

El pre-relleno del informe de viabilidad convive en dos mundos que casi no se tocan;
entender esto es la base para decidir los ejes.

- **Mundo 1 — flujo vivo: skill `viabilidad-prerelleno` (Claude-en-sesión).** El "LLM"
  es Claude leyendo, no un programa. Lee **todo `00_Input/`** (crudo, **no anonimizado**;
  nunca `06_Entrevistas` en 1.ª pasada ni `90_Notas personales`), sin recuperación ni
  scoring en código. Rellena la hoja `PREGUNTAS` (**88 preguntas** = 58 documentales / 30
  testificales), deriva los **14 hitos** y vuelca banderas a `AVISOS LLM`; genera un XLSX
  paralelo con `scripts/render_informe.py` (nunca sobrescribe el humano). Anclaje
  `[doc: fichero] "cita" + confianza`; regla de oro **nunca inventar** → sin documento,
  `pendiente`. RGPD: en claro bajo la excepción §2 (sin API externa).
  (`SKILL.md:24,42,66`.)
- **Mundo 2 — motor de código latente: `pipeline → scorer → viability`.** Existe en
  `core/` pero **la skill NO lo invoca**. `core/scorer.py` puntúa por keywords ponderadas
  (`honorarios`=5.0, `intermediación`=4.0…) → `documentos_top.md` (top-K);
  `core/viability.py` concatena esos top-K **hasta 18.000 chars** (`_MAX_CONTEXT_CHARS`),
  llama a Ollama local (llama3) y escribe `03_Decision/viabilidad.md` (+ `hechos_atomicos`,
  `contradicciones`, `prueba_indexada`). Lee el **MD viejo** `01_Procesado/MD/`
  (`markdown_generator`), **no** el de la sala de máquina.
- **La paradoja:** la palanca de ahorro (scoring + top-K + presupuesto de contexto) **ya
  está inventada**, pero vive en el motor que nadie usa y sobre el MD equivocado; el flujo
  real lee todo el crudo sin filtrar.

### 5.1 Jerarquía de fuentes por niveles (idea de Nikolai)

Que el LLM lea primero el **texto ligero** y solo escale a fuentes más caras si hace falta:

- **Nivel 1 — fuente principal:** espejos MD
  `01_Procesado/02_Sala de máquina/03_MD/{slug__sha8}.md`. Texto plano barato; frontmatter
  con `ocr_quality`, `text_sha256`, `source_path`.
- **Nivel 2 — soporte:** OCR PDF `.../01_OCR/{slug__sha8}.pdf` (tablas, layout, columnas).
- **Nivel 3 — soporte:** crudo `00_Input/...` (imágenes, firmas, inspección visual).

**Señal de escalado (ya existe):** `ocr_quality` del frontmatter + `_revisar/_cobertura.md`
→ `ok` usa N1; `low`/`empty` sube a N2 y, si insuficiente, N3. Idea a validar: que
`indice_documental.yaml` liste por doc su `ocr_quality` + punteros a los tres niveles.

**RGPD:** los tres niveles están **en claro** → válido para LLM **local** / Claude-en-sesión
(§2). Para **cloud/frontier** la jerarquía se replica sobre `06_Anonimizado/`.

### 5.2 Catálogo de ejes (candidatos) y matriz

| # | Eje | Tokens | Velocidad | Robustez (anclaje) | Coste | Reusa |
|---|---|---|---|---|---|---|
| **E1** | Leer MD (sala de máquina) en vez de crudo | ↑↑ | ↑ | ↔ (MD derivado; gate `ocr_quality`) | Bajo | `03_MD/` + frontmatter |
| **E2** | Jerarquía niveles MD→OCR→crudo, escalado por `ocr_quality`/`_cobertura.md` | ↑↑ | ↑ | ↑ (escala a fuente fiel donde el MD flojea) | Bajo | E1 + `01_OCR/` |
| **E3** | Recuperación selectiva por catálogo (`tipo_documental`/`fecha`/`parte`/categoría E&V) | ↑↑ | ↑↑ | ↔ (riesgo de omisión → barrido de residuo) | Medio (requiere sala de lectura) | `indice_documental.yaml` |
| **E4** | Ficha de hechos en **una pasada** → JSON anclado (cita+fuente); responder 88 preguntas / 14 hitos desde el JSON | ↑↑ | ↑ | ↑ (si preserva cita verbatim) | Medio | dirección `hechos_atomicos` |
| **E5** | RAG local con embeddings (Ollama `/api/embeddings` + store + chunking) | ↑↑↑ | ↑ | ↔/↓ (chunks pierden contexto) | **Alto** (todo nuevo) | patrón `llm_local.py`, coseno de `_few_shot` |
| **E6** | Caching programático (`keep_alive`, caché por `text_sha256`) | ↑ | ↑ | — | Bajo | solo pipeline programático |
| **E7** | Incremental por sha256 (no reprocesar sin cambios) | ↑ | ↑ | — | Bajo | sala de máquina ya idempotente |

**Invariante de anclaje (gobierna el objetivo de robustez):** el MD sostiene la cita a
nivel de **fichero** (verbatim + `source_path`), pero **no** el pinpoint a página/cláusula
que exige `verificacion-anclada-fuente` (Regla 4) — el ancla de página vive solo en el PDF
OCR (`01_OCR/`). Por eso toda extracción debe **preservar la cita verbatim**: es el puente
para re-anclar al PDF OCR. Resumir/parafrasear para ahorrar tokens **rompe** el anclaje.

**Recomendación (no adoptada):** trío **E2 + E3 + E4** — cubre los tres objetivos
reutilizando lo existente y preservando el anclaje verbatim. **E5 (RAG) diferido** (coste
alto, riesgo de anclaje; E3 ya da recuperación dirigida barata para 88 preguntas). E6/E7
solo si se construye el camino programático `core/viabilidad/*` (hoy fuera de alcance).
**Dependencia de orden:** E1/E2 exigen sala de máquina antes; E3 exige sala de lectura
antes → atan con la decisión de motor (§4).

### 5.3 Estimación de tiempo (incluido el pipeline) y robustez

Cuello de botella real: (1) que el corpus **quepa en contexto** (1 pasada, desatendido) o
lo **desborde** (troceo + compactación + supervisión); (2) **OCR en sesión** de escaneados.
Supuestos: página escaneada ≈ 1.500–2.500 tok; página MD ≈ 400–500 tok (~3× más ligera,
sin OCR en sesión); ~40 % de docs escaneados; E3 lee ~20–35 % de los docs; E4 lee una vez →
JSON → 88 preguntas. **Incluye el pipeline** (OCR sala de máquina + clasificación sala de
lectura) en la columna de ejes; el crudo no requiere pipeline. Se separa el **wall-clock**
del **tiempo de abogado** (atendido), que es el que de verdad cuesta.

| Caso | Crudo (todo atendido) | Ejes (pipeline+lectura) wall-clock | Ejes: tiempo **de abogado** |
|---|---|---|---|
| Pequeño ~40 docs / 200 pp | ~15–30 min | ~15–26 min (OCR ~3–6 + clasif ~8–12 + lectura ~4–8) | ~8–12 min |
| Medio ~150 docs / 800 pp | ~45–90 min (babysitting, desborda) | ~30–55 min (OCR ~10–20 + clasif ~12–20 + lectura ~8–15) | **~10–20 min** |
| Grande ~600 docs / 3.000 pp | horas / inviable de una vez | ~1.5–2.8 h (casi todo desatendido) | ~30–50 min |

**Lectura honesta:** incluido el pipeline, en **wall-clock** los ejes ~empatan en casos
pequeños, ganan ~1.5× en medios y son la **única vía viable** en grandes. La ganancia clara
es el **tiempo de abogado** (de ~45–90 min babysitteando a ~10–20 min en el caso medio) y que
el pipeline **se amortiza** aguas abajo (88 preguntas, 2.ª pasada de entrevista, escritos):
el crudo repaga la lectura cara muchas veces; los ejes la pagan una.

**Robustez de decisiones (%).** Rúbrica = media de *completitud* (no perder docs por desbordar
contexto ni por escaneados ilegibles), *fidelidad/anclaje* (fuente no distorsionada + cita
verbatim + pinpoint recuperable) y *consistencia* (idempotente, reproducible, trazado).

| Caso | Crudo | Ejes | Δ |
|---|---|---|---|
| Pequeño, texto mayoritario | ~78 % | ~85 % | +7 pp |
| Medio, mixto | ~68 % | ~87 % | +19 pp |
| Grande, muy escaneado | ~55 % | ~86 % | +31 pp |

**Matiz clave para el objetivo 3 ("fuentes no distorsionadas"):** el crudo *es* la fuente más
fiel, pero en el flujo real el modelo **igual OCR-iza por visión** los escaneados (distorsión
peor y sin registro) y, al desbordar el contexto, **resume** (omisión grande). La distorsión
del crudo es **incontrolada e invisible**; la de los ejes es **controlada** (`ocr_quality`
marca lo dudoso, escala al OCR/crudo fiel donde el MD flojea, preserva la cita verbatim
re-anclable a la página del PDF OCR, y es reproducible). Por eso los ejes suben en robustez
pese a leer un derivado, y la ventaja **crece con el tamaño y el % de escaneado**.

> Son órdenes de magnitud con supuestos explícitos, no benchmarks; medir en W-02VND1 (668
> docs) calibraría tiempo y robustez.

## 6. Decisiones abiertas / siguientes pasos

> Aprobación revertida 2026-07-10 (ver banner). Las decisiones vuelven a estar **abiertas**;
> las recomendaciones se conservan como punto de partida del re-brainstorming, no como acuerdo.

1. **Motor (§4):** A1 / A2 / A3. *Recomendación de arranque (no adoptada): A2.*
2. **Ejes de consumo LLM (§5):** trío **E2+E3+E4** *recomendado, NO adoptado*; E5 diferido.
   Reabrir: ¿E2 solo basta (opción mínima)? ¿`viabilidad-prerelleno` cambia su fuente a MD (N1)
   o modo opt-in? ¿manifiesto de niveles en `indice_documental.yaml`?
3. **Validación previa a decidir (nueva, prioritaria):** medir UN caso real (intake +
   `sala_maquina apply` + lectura) para sustituir el ROI estimado por cifras reales, y confirmar
   el supuesto de recurso €20/h y la delegabilidad de la clasificación (puntos A y B del banner).
4. **Higiene de cola:** cerrar formalmente `[SIGUIENTE-INTAKE-CRM-COMPLETO]` en `PLAN.md`
   (su Paso 1 está hecho en código) y enlazar este documento.
5. **Siguiente artefacto:** re-brainstorming con el plugin `superpowers` cargado → spec revisada;
   solo entonces promover a plan de implementación en `docs/superpowers/plans/`.

## Referencias

- CRM: `core/sync_sudespacho.py`, `core/judicial_intake.py`,
  `scripts/sync_sudespacho.py:201`, `docs/INTEGRACION_SUDESPACHO.md`,
  `docs/PLAN_INTAKE_CRM_COMPLETO.md`.
- Salas: `core/sala_maquina.py`, `scripts/sala_maquina.py`,
  `.claude/skills/organizar-sala-{maquina,lectura}/SKILL.md`.
- Registros: `core/catalogo_documental.py`, `core/inventory.py`, `core/intake_log.py`,
  `core/case_manager.py`.
- LLM/anon: `.claude/skills/viabilidad-prerelleno/`, `core/anon/api.py`,
  `core/llm.py`, `core/llm_cloud.py`, `docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md`.
- Motor (contexto): `docs/PLAN_MOTOR_DOCUMENTAL.md` (aparcado).

## 7. Anexo — Simulación: `viabilidad-prerelleno` sobre el Drive de Engel

> **Caso ficticio ilustrativo.** Ref, importes y contenidos inventados; sin PII; roles por
> función (propietario / buscador). Sirve para ver el flujo de punta a punta cuando la
> documental viene del Drive de E&V, y para contrastar crudo vs ejes en un caso concreto.

**Caso:** `BaRS7 - <calle> (W-0AB123) - Negativa escritura`, tipo **`NEGATIVA_ESCRITURA`**
(el buscador se niega a escriturar tras firmar arras). Precio de la operación **900.000 €**;
honorarios 5 % + IVA ⇒ TOTAL DEUDA ≈ **54.450 €**. Sociedad cliente: EV MMC SPAIN (ID 2),
posición actora. Supera el umbral de 2.500 € y la frontera de 15.000 € ⇒ ordinario.

**Carpeta bajada** `00_Input/01_Drive EV/W-0AB123/` (nombres tras la sala de lectura, por
categoría E&V):

```
01. ACTIVACIÓN/  2024-03-12_nota_encargo_exclusiva.pdf · 2024-03-12_dni_propietario.pdf ·
                 2024-03-14_nota_simple_registral.pdf
03. OFERTAS/     2024-05-02_hoja_visita_firmada.pdf · 2024-05-20_oferta_compra_firmada.pdf ·
                 2024-05-20_dni_buscador.pdf
04. ARRAS/       2024-06-10_contrato_arras_penitenciales.pdf ·
                 2024-06-10_reconocimiento_honorarios_arras.pdf
05. FACTURACIÓN/ 2024-06-11_factura_honorarios.pdf
07. RECLAMACIONES/ 2024-09-15_burofax_requerimiento.pdf
00. FOTOS/       2024-03-11_foto_inmueble_01.jpg … (×12)
```

**Paso a paso:**

1. **Intake (Drive E&V):** `/pull-rclone "BaRS7 - <calle> (W-0AB123) - Negativa escritura"`
   → rclone copia a `00_Input/01_Drive EV/W-0AB123/`; marcador `.pulled`; evento
   `pull_drive_ev` (SHA-256 por fichero) en `_intake_log.jsonl`.
2. **Sala de máquina** (`sala_maquina apply`): OCR + espejos MD en
   `01_Procesado/02_Sala de máquina/03_MD/`; `_cobertura.md` marca las 12 fotos como `empty`
   (sin texto) y los PDFs firmados como `ok`; evento `procesado_sala_maquina`.
3. **Sala de lectura** (`organizar-sala-lectura`): clasifica por categoría E&V, nombra
   canónicamente y escribe `indice_documental.yaml` (con `tipo_documental`, `parte`, `fecha`).
4. **`viabilidad-prerelleno`** (Claude-en-sesión). Con los ejes: lee el **MD (N1, E2)**;
   por hito consulta solo las categorías relevantes vía el catálogo (**E3** — p. ej. el hito
   ENCARGO mira `01. ACTIVACIÓN`); **una pasada → JSON (E4)**. Detecta `NEGATIVA_ESCRITURA`,
   rellena `PREGUNTAS` anclando `[doc: fichero] "cita" (confianza)` y deriva los 14 hitos.
5. **Salida:** `python scripts/render_informe.py datos_W-0AB123.json --salida "…/02_Analisis/Informe viabilidad LLM - W-0AB123.xlsx"`
   → XLSX de 4 hojas; **VIABILIDAD en blanco** (la decide el abogado).

**Hitos derivados (hoja INFORMACION):**

| # | Hito | Score | Por qué (ancla) |
|---|---|---|---|
| 1 | CUANTÍA | **3** | TOTAL DEUDA ≈ 54.450 € (>20.000 €) |
| 2 | ENCARGO | **0** | firmado (`cap_08`) y original (`cap_13`), pero **firma sin cotejar vs DNI** (`cap_08d=no_cotejado`) → regla conservadora = 0 |
| 3 | IDENT. PROPIETARIO | 1 | DNI propietario (`cap_17`) |
| 4 | TITULARIDAD | 1 | nota simple de captación (`cap_18a`) |
| 5 | HOJA DE VISITA | 1 | hoja firmada, original (`vis_05`/`vis_06`) |
| 6 | OFERTA | 1 | original firmado (`ofb_05`) |
| 7 | IDENT. BUSCADOR | 1 | DNI buscador (`vis_09`) |
| 8 | ARRAS | 1 | arras firmadas (`arr_00=firmadas`) |
| 9 | RECON. HON. — ARRAS | 1 | reconocimiento firmado en arras (`arr_13`) |
| 10 | ESCRITURA | **0** | no se otorgó (`esc_01=no`) — es el supuesto del caso |
| 11 | RECON. HON. — ESCRITURA | N/A | no hubo escritura |
| 12 | RECLAMACIÓN JURÍDICO | 1 | burofax enviado (`rec_02`) → interrumpe prescripción |
| 13 | RESPUESTA A LA RECLAMACIÓN | pendiente | no consta respuesta documentada (aún en plazo) |
| 14 | OFERTA VINCULANTE CONFIDENCIAL | pendiente | no consta oferta de transacción del deudor |

`TOTAL = 11` (métrica auxiliar, no veredicto; `N/A`/pendiente no suman).

**Fragmento del JSON de datos** (estilo `SKILL.md`):

```json
{
  "case_id": "W-0AB123", "tipo_caso": "NEGATIVA_ESCRITURA",
  "importes": {"precio": 900000, "pct_honorarios": 5, "pagos_parciales": 0},
  "hitos": {"CUANTIA": {"score": 3}, "ENCARGO": {"score": 0}, "ESCRITURA": {"score": 0},
            "RECLAMACION_JURIDICO": {"score": 1, "fecha": "15/09/2024"}},
  "preguntas": {
    "cap_08":  {"respuesta": "Sí", "cita": "[doc: 2024-03-12_nota_encargo_exclusiva] \"firmado por DocuSign\"", "confianza": "alta", "pendiente": "no"},
    "cap_08d": {"respuesta": "No cotejado", "cita": "[doc: 2024-03-12_dni_propietario] \"copia sin cotejo de firma\"", "confianza": "media", "pendiente": "no"},
    "esc_01":  {"respuesta": "No", "cita": "[doc: 2024-09-15_burofax_requerimiento] \"pese a las arras, la parte compradora no acudió a la notaría\"", "confianza": "alta", "pendiente": "no"}
  },
  "avisos": [
    {"tipo": "Prueba débil", "aviso": "Firma del encargo sin cotejar con DNI (cap_08d) → ENCARGO puntúa 0.",
     "impacto": "Hito ENCARGO", "severidad": "media", "accion": "Recabar DNI para cotejar.", "sube": "no", "estado": "abierto"},
    {"tipo": "Documento faltante", "aviso": "Original de las arras no localizado (solo copia).",
     "impacto": "Hito ARRAS", "severidad": "baja", "accion": "Solicitar original al consultor.", "sube": "no", "estado": "abierto"}
  ]
}
```

**Contraste crudo vs ejes (este caso).** Sobre **crudo**, Claude leería los ~19 binarios
enteros —incluidas las 12 fotos como imágenes (tokens altos e inútiles para el fondo)— sin
filtrar. Con **ejes**, lee el **MD** de las 3–4 categorías que cada hito necesita
(`ACTIVACIÓN/OFERTAS/ARRAS/RECLAMACIONES`) y salta las fotos (`empty` en `_cobertura.md`).
Ganancia y robustez, en la tabla de §5.3. **RGPD:** todo en claro bajo la excepción §2
(Claude-en-sesión, sin API externa); para un LLM cloud habría que anonimizar antes.

## 8. ROI — cómo enfocar los estudios de viabilidad

> Objetivo de esta sección: decidir **dónde y cómo** invertir el estudio de viabilidad para
> maximizar el retorno, con el tiempo de abogado como recurso escaso.

### 8.1 La idea, sin jerga

No importa tanto *cuánto* se tarda, sino **quién pone cada minuto**. Hay dos clases de trabajo:

- **Mecánico** (juntar documentos = intake, OCR, ordenar/clasificar): sin criterio jurídico
  → lo hace la **máquina** o alguien de **€20/h**.
- **De criterio** (decidir si el caso se aguanta): solo el letrado → **€60/h**.

El **intake** (juntar todo en `00_Input/`) es mecánico y **se paga igual** leas crudo o por
ejes (es coste común). El **crudo** obliga a que el letrado (€60/h) haga casi todo, porque un
montón desordenado **no se puede delegar**. Los **ejes** parten el trabajo en fases limpias →
lo mecánico baja a €20/h o a la máquina, y el letrado **solo decide**.

### 8.2 Efecto de meter el intake en el ROI

Mirando **solo la lectura**, los ejes iban ~6× más rápidos. Al sumar el intake (mismos
minutos en ambos caminos), la ventaja de **velocidad** se diluye a ~1,8×. Por eso el argumento
correcto **no es la velocidad — es el coste y quién paga cada minuto**: los ejes habilitan
pagar €20/h (o €0) por el ~75 % del tiempo que es mecánico y reservar €60/h para la decisión.

### 8.3 Caso real — W-02VND1 (VUELTA, Barcelona)

Recuentos **reales** (medidos): 668 documentos; 531 con MD `ok`; 90 fotos vacías; 277 correos
`.eml` + 162 adjuntos; la sala de lectura en Cowork tardó ~53 min (conector Drive per-fichero).
Minutos y euros **estimados** (senior €60/h = €1/min; mecánico €20/h = €0,33/min):

| Tarea | Crudo (senior todo) | Ejes (senior todo) | Ejes bien montado |
|---|---|---|---|
| Intake (juntar 668 docs) | €75 | €75 | €25 (@€20) |
| OCR sala de máquina (desatendido) | — | €0 | €0 |
| Clasificación / sala de lectura (gate) | — | €45 | €15 (@€20) |
| Leer y **decidir** | €240 (≈4 h, desborda) | €30 | €30 (@€60) |
| **Total** | **≈ €315** | **≈ €150** (−52 %) | **≈ €70** (−78 %) |

Robustez del caso: crudo ~55 % (desborda → resume → omite; 90 fotos sin ver) vs ejes ~86 %.
En un caso grande, el crudo no es solo caro: es **poco fiable**.

**Matiz VUELTA:** se gana por **testimonio** (nexo causal), no por papeles → el trabajo
documental tiene techo. Su misión es **anclar los hitos y marcar los huecos** para el guion de
entrevista; el letrado debe parar ahí, no exprimir el documento 669.

### 8.4 Palancas de ROI (de mayor a menor impacto)

1. **Embudo de gasto (antes que nada):** no estudiar a fondo lo que no lo merece.
   (a) **Filtro de tipo** — solo `INFORME_VIABILIDAD_TIPOS` (las `NEGATIVA_*`, `VUELTA`,
   `INCUMPLIMIENTO_EXCLUSIVA`, `RESPONSABILIDAD_PROFESIONAL`); `BAD_DEBT`/`LAU_20`/`DEVOLUCION_*`
   → sin estudio, vía de cantidad, todo a €20/h. (b) **Filtro de cuantía** — <2.500 € no se
   litiga; escala la profundidad con el importe. (c) **Triaje barato primero**
   (`triaje-viabilidad`, semáforo) → solo los verde/ámbar escalan al prerelleno completo.
2. **Arbitraje de tarifas (lo que más rinde, y solo los ejes lo habilitan):** el ~75 % del
   tiempo (intake + clasificación) es mecánico → €20/h o máquina; el letrado €60/h **solo**
   en la decisión. En crudo pagas €60/h por trabajo de becario.
3. **Automatizar el intake** (coste común): terminar de automatizar WhatsApp/manual para bajar
   los ~30–75 min atendidos; cada minuto ahorrado cuenta **en los dos** caminos.
4. **Enfocar los hitos load-bearing** (ENCARGO, nexo causal, cuantía, prescripción) y **mandar
   los huecos a la entrevista**; no leer más allá de lo que mueve el semáforo (techo testifical).

### 8.5 Conclusiones

- El ahorro grande **no es de tokens ni de segundos**: es **tiempo de abogado** (~4× en el caso
  medio) y **robustez** (~68 % → ~87 %; y hasta ~55 % → ~86 % en casos grandes como W-02VND1).
- **El embudo va antes que los ejes:** decide *si* hay estudio; los ejes optimizan el coste
  *dentro* del estudio.
- **Orden de adopción de los ejes:** E2 (leer MD con gate, barato) → E3 (recuperación por
  catálogo, el que más enfoca) → E4 (ficha de hechos una pasada, anclaje + reutilización).
  E5 (RAG) diferido.
- **Regla de oro:** que la hora de €60 solo toque la decisión; todo lo demás, máquina o €20/h.
- **Calibrar con W-02VND1:** cronometrar una corrida local (intake + `sala_maquina apply` +
  lectura) convierte estos rangos en cifras exactas del despacho.

> Cifras de euros y minutos: **estimaciones** con supuestos explícitos (30–75 min de intake,
> tarifas €20/€60), no benchmarks. Los recuentos de W-02VND1 sí son reales.
