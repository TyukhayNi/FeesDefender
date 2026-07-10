---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-10
tipo: brainstorming + runbook
---

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

**Idea (Nikolai):** que el LLM lea primero el **texto ligero** y solo escale a fuentes
más caras cuando haga falta, para gastar menos tokens.

**Jerarquía propuesta:**

- **Nivel 1 — fuente principal:** espejos MD
  `01_Procesado/02_Sala de máquina/03_MD/{slug__sha8}.md`. Texto plano barato; el
  frontmatter ya trae `ocr_quality`, `text_sha256`, `source_path` (anclaje).
- **Nivel 2 — soporte:** OCR PDF `.../01_OCR/{slug__sha8}.pdf` (cuando el MD no basta:
  tablas, layout, columnas).
- **Nivel 3 — soporte:** crudo `00_Input/05_CRM/...` (imágenes, firmas, inspección
  visual, documento nativo).

**Señal de escalado (ya existe, no hay que inventarla):** el campo `ocr_quality` del
frontmatter y `_revisar/_cobertura.md`. Regla: `ok` → usar N1; `low`/`empty` → subir a
N2 y, si sigue insuficiente, a N3. **Idea de diseño a validar:** que
`indice_documental.yaml` liste por documento su `ocr_quality` + punteros a los tres
niveles → un **manifiesto único** que el LLM consulta para decidir qué abrir sin
tantear.

**Interacción RGPD (crítica):** los tres niveles están **en claro**. Válido para LLM
**local** (`core/llm.py`, Ollama). Para **cloud/frontier**, el nivel equivalente debe
ser el **anonimizado** (`06_Anonimizado/`) — la jerarquía se replica sobre el árbol
anon, no sobre el crudo.

**Efecto en `viabilidad-prerelleno`:** hoy lee el crudo de `00_Input/`. La propuesta la
haría leer el **MD (N1)** como fuente principal. *Implica:* (1) nueva **dependencia de
orden** — la sala de máquina debe haber corrido antes; (2) el anclaje `[doc: fichero]
"cita"` se apoya en `source_path` del frontmatter; (3) ahorro de tokens grande a
escala (p. ej. cientos de docs por caso). *A decidir:* ¿se cambia la fuente primaria de
la skill, o se ofrece como modo opt-in?

## 6. Decisiones abiertas / siguientes pasos

1. **Motor (§4):** elegir A1 / A2 / A3. *Recomendación de arranque: A2.*
2. **Consumo LLM (§5):** ¿`viabilidad-prerelleno` migra a leer N1 (MD) como fuente
   principal? ¿Se materializa el manifiesto de niveles en `indice_documental.yaml`?
3. **Higiene de cola:** cerrar formalmente `[SIGUIENTE-INTAKE-CRM-COMPLETO]` en
   `PLAN.md` (su Paso 1 está hecho en código) y enlazar este documento.
4. Cuando §4 y §5 estén cerrados, promover a un plan de implementación en
   `docs/superpowers/plans/` (flujo brainstorming→spec→plan).

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
