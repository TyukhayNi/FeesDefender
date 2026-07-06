---
estado: historico
dueño: Nikolai Tyukhay
---

# PLAN — Sala de lectura y organización de `01_Procesado`

> **Origen:** HANDOFF de sesión de planificación Cowork, 2026-06-12 (aprobado por
> Nikolai). Plan fino autocontenido para hilo nuevo. Implementación: Claude Code.
> **Frontera:** todo el código lo implementa Claude Code. Cowork ha hecho el
> diseño, los prototipos (`INDICE.md` / `CRONOLOGIA.md`) y el handoff.
> **Sección §0 (al final): notas de Claude Code** con el estado real del repo y
> los acoplamientos detectados — leer antes de arrancar.

---

## 1. Objetivo

Montar en `01_Procesado` una capa orientada al humano:

- una **sala de lectura** donde el abogado consulte el caso completo (documentos,
  conversaciones, entrevistas, procesal) **en claro y en orden**;
- una **capa de texto** (`MD/`) para búsqueda a texto completo.

Aprovechar la API de **Scaleway** (Generative APIs, LLM soberano UE) para
clasificar y **fechar** documentos sin exponer datos personales fuera de la UE.

## 2. Decisiones cerradas

1. **`procesal@` NO se conecta como fuente de documentos.** Los documentos ya
   entran por el CRM (sudespacho) → `00_Input/05_CRM`. Conectar Gmail duplicaría
   el ciclo subida/descarga del CRM.
2. **Scaleway, doble rol:**
   - (a) Clasificador/extractor de **tipo** y **fecha** de documento para
     organizar el intake.
   - (b) Sobre `procesal@`, solo como **señal** (plazos, señalamientos,
     vinculación al expediente → El Contable/alertas), nunca re-ingiriendo
     adjuntos.
   - Motor **híbrido**: reglas deterministas primero; LLM solo para el residuo
     ambiguo.
3. **Capas** (sobre la estructura existente del expediente):
   `00_Input` (crudo, inmutable, fuente de verdad) → `01_Procesado` (capa humana)
   → `06_Anonimizado` (MD tapado para LLM) → `07_AI cowork` (taller del LLM).
   Todo aguas abajo de `00_Input` es **regenerable**.

## 3. Estructura de `01_Procesado`

```
01_Procesado/
├── Sala lectura/        lo que el abogado LEE
│   ├── INDICE.md · CRONOLOGIA.md      (portada: por fuente / narrativa)
│   ├── Drive E&V/   CRM/              PDF originales OCR'd, en bundles
│   └── WhatsApp/   Entrevistas/       MD nativos (aquí el .md ES el documento)
├── MD/                  rendiciones en claro de los binarios (PDF→texto),
│                        espeja la estructura de Sala lectura, solo para búsqueda
├── _manifiesto.jsonl    trazabilidad: original → nombre canónico, SHA-256, fuente, fecha
└── _revisar/            cuarentena de lo no clasificado con confianza (repaso humano)
```

## 4. Reglas de organización

- **Subcarpetas por fuente:** Drive E&V, CRM, WhatsApp, Entrevistas.
- **Nombre de fichero:** `<AAAA-MM-DD>_<tipo>_<descripción breve>.<ext>`, en tipo
  oración.
- **Documentos compuestos** (escrito + adjuntos; chat + multimedia) → **bundle**:
  subcarpeta con el principal (conserva su **nombre descriptivo**) y los anexos en
  **subcarpeta**: `adjuntos/` para escritos, `media/` para chats. Decisión a cargo
  del *detector de conjunto* previsto en la reorg de `05_CRM`.
- **Copia, no mueve:** `00_Input` queda intacto.
- **Dedup por SHA-256:** mismo documento en dos fuentes → una sola entrada (mismo
  hash que ya usa el anonimizador).
- **Índices:** un documento = una entrada (PDF + MD no duplican línea); el enlace
  va al **original**, con "ver texto" opcional al MD. Generados automáticamente
  desde `indice_documental.yaml`; **solo lectura**.

## 5. Routing de los outputs del pipeline

De una sola extracción (OCR → texto → anonimización):

| Output | Destino |
|---|---|
| PDF con capa de texto (OCR'd) | `01_Procesado/Sala lectura/<fuente>/` (original legible) |
| MD en claro (paso intermedio) | `01_Procesado/MD/` (**derivación NUEVA a implementar**) |
| MD anonimizado (paso final) | `06_Anonimizado/` (sin cambios) |

El MD anonimizado **nunca** entra en `MD/`. `MD/` (claro, en 01) y `06_Anonimizado`
(tapado) son gemelos de la misma extracción.

## 6. Fronteras y RGPD

- `01_Procesado` es **en claro** → acceso restringido al despacho (fuera del rol
  `ev_team_leader`).
- El LLM **solo lee de `06`**, nunca de `01`.
- `90_Notas personales` queda reservada y fuera de la automatización.
- Persistir texto claro en `MD/` es acto relevante a efectos RGPD → confinado a 01.

## 7. Alcance de la primera fase

Empezar por **ficheros en `01_Procesado`** (formato ya prototipado: `INDICE.md` +
`CRONOLOGIA.md`). Streamlit y artifact de Cowork quedan **diferidos**.

## 8. Tareas de implementación (Claude Code)

1. Crear subcarpetas `Sala lectura/` y `MD/` dentro de `01_Procesado` (scaffolding
   del caso). Mantener `_manifiesto.jsonl` y `_revisar/`.
2. **Grifo de MD en claro:** que el pipeline persista el paso intermedio (texto en
   claro) a `01_Procesado/MD/`, espejando la ruta de `Sala lectura/`, antes de
   anonimizar a `06`.
3. **Copiador organizado:** poblar `Sala lectura/<fuente>/` desde `00_Input`
   (CRM ← `05_CRM`; Drive E&V; WhatsApp; Entrevistas), aplicando taxonomía +
   patrón de nombre. Copia, no mueve.
4. **Detector de conjunto / bundles** (reaprovechar el de la reorg `05_CRM`):
   atómico → fichero; compuesto → carpeta con principal + `adjuntos/`|`media/`.
5. **Dedup por SHA-256** y registro en `_manifiesto.jsonl` (original → canónico,
   SHA, fuente, fecha).
6. **Generador de índices** `INDICE.md` (por fuente) y `CRONOLOGIA.md` (narrativa,
   ascendente) desde `indice_documental.yaml`; un documento = una entrada; enlaces
   relativos al original.
7. **Clasificador/fechador** (Scaleway, híbrido): tipo + fecha por documento;
   *fallback* de fecha = fecha de entrada en CRM/Drive; sin confianza → `_revisar/`.

### Criterios de aceptación

- `00_Input` no se modifica en ninguna ejecución.
- Re-ejecución **idempotente**: no duplica ficheros ni re-renombra lo ya canónico.
- Ningún camino de IA accede a `01_Procesado`.
- Cada documento en `Sala lectura/` tiene su entrada en los índices y su rendición
  en `MD/` (si es binario), o es MD nativo.

## 9. Pendientes de decisión (no bloquean el arranque)

1. **Cerrar la taxonomía documental** (lista cerrada de tipos + patrón de nombre)
   en `indice_documental.yaml`. — Lo redacta Cowork.
2. **DPA / encargo de tratamiento con Scaleway** antes de enviarle documental de
   E&V.
3. **Correspondencia suelta** (email que nunca llega a ser documento del CRM):
   ¿nota normalizada en el expediente o fuera de la sala de lectura?

## 10. Referencias del repo

- `core/config.py` → `CASO_SUBDIRS`, subcarpetas de intake.
- `core/anon/api.py`, `core/anon/mapa_caso.py` → pipeline y mapa (SHA-256,
  idempotencia, `06`→`07`).
- Plan reorg `05_CRM` (detector de conjunto + bundles por metadato) →
  reaprovechar para los bundles de `01_Procesado`.

---

## §0 — Notas de Claude Code (estado real del repo, 2026-06-12)

> Lectura del código antes de arrancar. El diseño del handoff es coherente; estos
> son los **acoplamientos y desajustes con el repo actual** que fijan la secuencia.
> Nada de esto contradice el handoff: lo aterriza.

### A. Estado actual del código (verificado)

- **Subdirs del caso** (`core/config.py:278-288`): `01_Procesado` existe como
  carpeta de nivel 1 pero **sin** subestructura `Sala lectura/` ni `MD/`. El
  scaffolding `ensure_case` (`core/case_manager.py:207-359`) **no crea** `Sala
  lectura/`, `MD/`, `_manifiesto.jsonl` ni `_revisar/` → Tarea 1 es construcción
  desde cero.
- **Pipeline hoy** deposita en `01_Procesado` así:
  - OCR → `01_Procesado/raw_text/{slug}.txt` (`core/extractor.py:216-230`, skip
    incremental por SHA-256 ya implementado).
  - MD en claro → `01_Procesado/{slug}.md` **plano** (`core/markdown_generator.py:22-58`),
    con frontmatter (`source_path`, `extractor`, `chars`, `sha256_text`).
  - MD anonimizado → `06_Anonimizado/{slug}.md` + `_mapa_caso.json`
    (`core/anon/api.py`, `core/anon/mapa_caso.py`).
  → **Tarea 2 (grifo MD) NO es código nuevo: es re-enrutar** dónde escribe
  `markdown_generator.build`. Hoy ya escribe el MD en claro en `01_Procesado/`
  (plano); el handoff pide moverlo a `01_Procesado/MD/` **espejando** la ruta de
  `Sala lectura/`. El gemelo claro/tapado ya existe de facto (`01` plano vs `06`);
  lo que falta es la estructura espejo.
- **Dedup SHA-256** ya existe: `intake_manifest.py` (`IntakeManifest.register`,
  artefacto `00_Input/_intake_hashes.json`) + `compute_sha256` (chunks 64 KiB).
- **Detector de conjunto** ya existe: `core/conjunto_detector.py` — **solo emite
  propuestas** (`conjunto_detectado`/`pendiente_revision`); la persistencia de
  `parent_id` está **DIFERIDA a `[SIGUIENTE-CATALOGO-DOCUMENTAL]`**.
- **LLM cloud** ya existe: `core/llm_cloud.py::chat_json(messages, json_schema=…)`,
  Scaleway/Mistral Small 3.2, `temperature=0.0`, function-calling JSON. Mismo
  conector que el intake de procuradores.

### B. Acoplamiento crítico #1 — la sala de lectura **es** `[SIGUIENTE-CATALOGO-DOCUMENTAL]`

El handoff (§4 y Tarea 6) genera `INDICE.md`/`CRONOLOGIA.md` **desde
`indice_documental.yaml`**. Ese catálogo **no existe**: Nikolai decidió
explícitamente **no construirlo a medias** (ver `PLAN.md`, notas Cowork 2026-06-07
`[SIGUIENTE-CATALOGO-DOCUMENTAL]`; y `conjunto_detector.py` diferió ahí la
persistencia `parent_id`). Consecuencia:

> **Construir la sala de lectura obliga a construir el catálogo `indice_documental.yaml`.**
> Son la misma pieza vista por dos lados: el YAML es la fuente de verdad; `INDICE.md`
> / `CRONOLOGIA.md` / la sala de lectura son render de solo lectura sobre él. El
> esquema mínimo por entrada ya está cerrado en `PLAN.md` (`id_doc`, `ruta_relativa`,
> `nombre_original`, `tipo_documental`, `fecha_doc`, `parte`, `fuente`, `estado`,
> `hash`, `fecha_indexado`) — **falta `parent_id`/`orden_en_bundle`** que pide el
> detector de conjunto (D9 / MEJORAS #29) y los bundles del handoff (Tarea 4).

**Implicación de secuencia:** el catálogo es el cimiento, no una tarea más. Orden
natural: catálogo YAML (esquema + escritor desde pipeline/manifest) → render de
índices → copiador organizado → bundles → clasificador.

### C. Acoplamiento #2 — `_manifiesto.jsonl` (handoff §3) vs `_intake_hashes.json` (repo)

El handoff pide un `_manifiesto.jsonl` nuevo en `01_Procesado` (original →
canónico, SHA, fuente, fecha). El repo ya tiene `00_Input/_intake_hashes.json`
(`IntakeManifest`) con SHA → `primary_path` + aliases por fuente. **Solapan en el
dedup por hash.** Decisión a tomar (ver Decisiones abiertas, abajo): ¿el catálogo
`indice_documental.yaml` absorbe la trazabilidad y `_manifiesto.jsonl` desaparece,
o se mantienen tres artefactos (hashes de input, manifiesto de 01, catálogo)?
Inclinación de Claude Code: **una sola fuente de verdad documental** — el catálogo
YAML — alimentado por el dedup que ya existe; evitar un tercer artefacto.

### D. Acoplamiento #3 — RGPD y el clasificador Scaleway (Tarea 7)

Regla §6: "el LLM solo lee de `06`, nunca de `01`". Pero el clasificador/fechador
(Tarea 7) necesita **tipo y fecha del documento en claro** → leería de `00_Input`/
`01` (con PII). Esto es la **misma excepción RGPD acotada** que ya se aprobó para
el intake de procuradores (`PLAN.md` `[SIGUIENTE-INTAKE-PROCURADORES-EMAIL]`: LLM
cloud UE Scaleway, excepción que **no deroga la regla general**). Hay que:
1. Declararlo explícitamente como excepción acotada (igual que procuradores).
2. Maximizar reglas deterministas (motor híbrido) para minimizar lo que sale:
   muchos tipos/fechas salen del `filename`, de `id_carpeta_label` del CRM y de
   `modified_at` (ya traído al DTO en la 2ª tanda de `[SIGUIENTE-REORG-05CRM]`,
   D10) **sin LLM**.
3. **Bloqueante para Tarea 7:** el DPA con Scaleway (§9.2). **No bloquea** las
   Tareas 1-6, que son deterministas.

### E. Otros enganches menores

- **Idempotencia / `[IDEA-SKIP-INCREMENTAL-EXTRACCION]`** (`PLAN.md`): hoy
  `extract_all` se llama **dos veces** por corrida (bug de eficiencia, `pipeline.py`).
  El criterio de aceptación "re-ejecución idempotente" del handoff se apoya en
  cerrar antes (o a la vez) ese punto #1. Bajo riesgo, alto valor; conviene
  arreglarlo en la misma tanda que el grifo de MD (Tarea 2 toca el mismo flujo).
- **Bundles físicos vs `parent_id`** (handoff Tarea 4 vs D9/D11 de
  `[SIGUIENTE-REORG-05CRM]`): la reorg `05_CRM` decidió **no** crear subcarpeta
  física de bundle (`parent_id` en el catálogo). El handoff §4 sí pide subcarpeta
  física (`adjuntos/`|`media/`) **en la sala de lectura**. No es contradicción:
  `05_CRM` (input, plano) ≠ `Sala lectura` (vista humana). En la sala de lectura
  el bundle físico sí tiene sentido; el detector aporta el agrupamiento, el
  copiador lo materializa. Reaprovechar `conjunto_detector` como **proveedor de
  propuestas**, no reescribirlo.
- **Render de solo lectura:** reutilizar el patrón YAML→XLSX de las plantillas de
  viabilidad (`data/_plantillas/`, renderer ya existente) para el YAML→MD de
  índices. Cabecera "no editar a mano" como en `_INDICE.md` del organizador local.

### F. Secuencia propuesta por Claude Code

Fase única de arranque (lo demás — Streamlit, artifact Cowork — diferido por §7):

0. **(Prerrequisito de eficiencia)** Cerrar `[IDEA-SKIP-INCREMENTAL-EXTRACCION]`
   punto #1 (doble `extract_all`). Riesgo cero, gana 50% OCR, y deja el flujo del
   pipeline limpio antes de re-enrutar el MD.
1. **Catálogo `indice_documental.yaml`** (= `[SIGUIENTE-CATALOGO-DOCUMENTAL]`):
   esquema cerrado + `parent_id`/`orden_en_bundle`; escritor alimentado por el
   dedup existente (`IntakeManifest`); excluir `90_Notas personales`. Resuelve el
   Acoplamiento #2.
2. **Scaffolding** (`ensure_case`): `Sala lectura/`, `MD/`, `_revisar/` (lazy
   donde proceda). Decidir `_manifiesto.jsonl` según Acoplamiento #2.
3. **Grifo de MD en claro** (Tarea 2): re-enrutar `markdown_generator.build` a
   `01_Procesado/MD/` espejando `Sala lectura/`.
4. **Copiador organizado** (Tarea 3) + **bundles** (Tarea 4, consumiendo
   `conjunto_detector`): poblar `Sala lectura/<fuente>/` desde `00_Input`. Copia,
   no mueve.
5. **Render de índices** (Tarea 6): `INDICE.md` + `CRONOLOGIA.md` desde el catálogo,
   solo lectura.
6. **Clasificador/fechador híbrido** (Tarea 7): reglas deterministas primero
   (filename, `id_carpeta_label`, `modified_at`); LLM Scaleway solo para el residuo
   → `_revisar/` sin confianza. **Tras** DPA (§9.2).

Cada fase con sus tests (`tests/`), criterio de aceptación verificado, suite verde.

### G. Decisiones abiertas que conviene cerrar con Nikolai antes de la Fase 1

1. **Catálogo único vs `_manifiesto.jsonl` aparte** (Acoplamiento #2). Inclinación:
   catálogo único.
2. **¿La sala de lectura promueve formalmente `[SIGUIENTE-CATALOGO-DOCUMENTAL]`** de
   backlog a cola? (regla de promoción `CLAUDE.md`: disparador = caso real /
   decisión de Nikolai). De facto el handoff ya lo dispara.
3. **Taxonomía documental** (§9.1) — la redacta Cowork; bloquea la afinación del
   clasificador (Tarea 7) y el patrón de nombre, **no** el scaffolding ni el catálogo.
4. **DPA Scaleway** (§9.2) — bloquea solo la Tarea 7.
5. **Correspondencia suelta** (§9.3).
