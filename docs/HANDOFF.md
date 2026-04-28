# Handoff — FeesDefender

> Documento de traspaso entre sesiones / perfiles de Claude. Pegar el contenido
> íntegro al inicio de una nueva conversación para que el siguiente asistente
> tenga el contexto completo sin tener que reconstruirlo.

---

## 1. Identidad del proyecto

**Nombre:** FeesDefender — Sistema integral de defensa de honorarios.
**Nombres anteriores:** "Motor de Honorarios" → "FeesGuard" → "FeesDefender".
**Tipo:** sistema legal-tech, fase MVP, uso local.
**Objetivo de negocio:** automatizar el análisis, preparación y defensa
de reclamaciones de honorarios de intermediación inmobiliaria en España,
desde la apertura del expediente extrajudicial hasta la ejecución forzosa.
Diseñado para escalar a producto interno y, posteriormente, SaaS para
inmobiliarias (cliente principal hoy: Engel & Völkers — EV MMC SPAIN, S.L.U.).

**Usuario único actual:** Nikolai Tyukhay, abogado en España (Lic. Derecho
por la Federación Rusa). Especializado en resolución de conflictos y derecho
inmobiliario. Cartera principalmente civil; clientes de alto poder
adquisitivo de Rusia y ex-URSS, además de E&V.

**Carpeta raíz del proyecto:** `G:\Unidades compartidas\DESPACHO - PRODUCCION\Sudespacho.net\Base datos expedientes`

---

## 2. Arquitectura (no romper)

Tres capas estrictamente separadas. La interfaz **no contiene lógica de
negocio**. Los `.md` son la **fuente de verdad**. No hay base de datos.

```
┌────────────────────────────────────────────┐
│ UI: Streamlit / CLI Typer                  │  orquesta llamadas al core
├────────────────────────────────────────────┤
│ Core (Python, módulos en core/)            │
│   case_manager · sync · sync_sudespacho    │
│   inventory · extractor · md_generator     │
│   scorer · viability · demanda_generator   │
│   linker · llm · pipeline · utils · config │
├────────────────────────────────────────────┤
│ Datos: data/CASOS/{case_id}/  (.md)        │  fuente de verdad
└────────────────────────────────────────────┘
```

**LLM:** local con Ollama (modelo por defecto `llama3`, `temperature=0.2`).
Sin IA en la nube por confidencialidad.

**Confidencialidad estricta:** todo dato sensible vive solo en `data/CASOS/`,
que está en `.gitignore`. La carpeta `90_NOTAS_PERSONALES/` de cada caso es
zona del abogado y **ningún módulo del core la lee ni la escribe**.

---

## 3. Estructura de un caso

```
data/CASOS/{case_id}/
├── 00_INPUT/                    documentos originales por fuente
│   ├── _caso.md                 índice del caso (escrito por case_manager)
│   ├── _inventory.json          inventario con metadatos + fuente por archivo
│   ├── sudespacho_{id}/         ← pull desde el CRM, UNA SUBCARPETA POR EXPEDIENTE
│   │   ├── .pulled              marcador JSON: {doc_ids, last_sync, by_carpeta}
│   │   ├── civil/               subcarpeta del CRM (refleja carpetas del gestor)
│   │   └── demanda/             otra subcarpeta del CRM
│   ├── drive/                   ← rclone (sync.py)
│   │   ├── .synced              marcador idempotencia
│   │   └── *
│   ├── email/                   ← (futuro) Roundcube/Gmail
│   ├── whatsapp/                ← (futuro) export
│   └── manual/                  ← drag-and-drop del abogado
├── 01_PROCESADO/                texto extraído + .md por documento
├── 02_ANALISIS/                 hechos_atomicos · prueba_indexada · contradicciones · scoring · documentos_top
├── 03_DECISION/                 viabilidad
├── 04_OUTPUT_PREDEMANDA/        requerimiento_previo · demanda
├── 05_PROCEDIMIENTO/            escritos posteriores y resoluciones
├── 06_AI_COWORK/                _pipeline_log + _sync_log.md + notas con LLM
└── 90_NOTAS_PERSONALES/         zona del abogado, intocable
```

**Convención multi-expediente.** Un caso puede tener varios expedientes en el
CRM (p.ej. extrajudicial + judicial). Cada expediente tiene su propia subcarpeta
`sudespacho_{id}/` en `00_INPUT/`. El análisis es unificado a nivel de caso.
La lista de expedientes vinculados vive en el frontmatter de `_caso.md` bajo
`sudespacho_expedientes: [{id, element, input_dir}]`. Se registra mediante
`case_manager.register_expediente(case_id, exp_id, element)` (idempotente).

**Marcador `.pulled`.** JSON con `{doc_ids: [...], last_sync: ISO, by_carpeta: {...}}`.
Permite pull incremental: `set(crm_ids) - set(already_pulled_ids)` = nuevos.
Tres modos: skip (default, si `.pulled` existe no hace nada), incremental
(`--incremental`, solo descarga lo nuevo), force (`--force`, re-descarga todo).

**Convención `case_id`.** La referencia CRM ES el `case_id` y el nombre de la
carpeta. Formato: `{City}{OpType}{Team} - {Dirección} ({W-ID}) - {Tipo caso}`.
Ejemplo: `BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU`.
- `Ba` = Barcelona, `RR` = Residential Rentals, `3` = equipo 3
- `W-030LFT` = CRM ID de Engel & Völkers
- `Art 20 LAU` = tipología del caso
Los caracteres `(`, `)`, `-`, `,`, `º` son válidos en NTFS con comillas en PS.
Formato heredado (tests): `EV-2026-001` — sigue aceptado por `validate_case_id()`.

Cada `.md` lleva frontmatter YAML con trazabilidad obligatoria cuando el
contenido procede de un LLM: `case_id`, `tipo`, `fase`, `fecha`, `model`,
`prompt_id`, `prompt_hash`, `fuentes`.

---

## 4. Pipeline

`core.pipeline.run(case_id)` ejecuta secuencialmente, idempotente, nunca
toca `00_INPUT/` ni `90_NOTAS_PERSONALES/`:

1. `case_manager.ensure_case`
2. `sync.pull` (rclone) o `sync_sudespacho.pull_expediente` (API CRM)
3. `inventory.scan` → `00_INPUT/_inventory.json`
4. `extractor.extract_all` (Docling con fallbacks pypdf, python-docx)
5. `markdown_generator.build` → `01_PROCESADO/{slug}.md`
6. `scorer.score` (modo `hybrid` por defecto: heurística + LLM)
7. `viability.analyze` → 4 prompts en cadena
8. `demanda_generator.draft_demanda`
9. `linker.crosslink` (`[[wikilinks]]` para Obsidian)

Cualquier paso es ejecutable aislado.

---

## 5. Estado actual (a 2026-04-26)

**Implementado y testeado (25 tests OK):**

- Estructura completa de proyecto, `pyproject.toml`, `requirements.txt`,
  `.env.example`, `.gitignore`.
- Core completo: 14 módulos en `core/` (más `sync_sudespacho_legacy.py`).
- 7 prompts jurídicos en `prompts/`.
- UI Streamlit con 4 tabs (Casos / Nuevo / Pipeline / Visor).
- CLIs Typer: `init_caso`, `run_pipeline`, `sync_sudespacho` (con `sync_all`).
- Script de tarea programada: `scripts/scheduled_sync.py` (Windows Task Scheduler).
- 3 backends de ingesta de documentos.
- Tests pytest (25/25): `test_case_manager`, `test_inventory`, `test_utils`,
  `test_sync_sudespacho`, `test_sync_sudespacho_legacy`. Aislamiento por
  fixture `tmp_casos` que parchea tanto `core.config.CASOS_ROOT` como
  `core.case_manager.CASOS_ROOT` (capturan el valor en import time).

**Arquitectura multi-expediente (implementada 2026-04-26):**
- `case_manager.ExpedienteLink` y campo `sudespacho_expedientes` en `CaseMeta`.
- `case_manager.register_expediente(case_id, exp_id, element)` — idempotente.
- `sync_sudespacho.pull_expediente` descarga en `sudespacho_{id}/` y gestiona
  3 modos: skip / incremental / force mediante marcador `.pulled` (JSON).
- `scripts/scheduled_sync.py` — sync incremental diario de todos los casos;
  escribe log en `06_AI_COWORK/_sync_log.md`.
- `scripts/sync_sudespacho.py sync_all` — equivalente CLI al script programado.
- Flujo notificaciones judiciales: secretaria archiva en sudespacho →
  tarea programada detecta docs nuevos → pull incremental automático.

**Primer caso real creado y con documentos descargados (2026-04-26):**
- `BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU`
- Expediente 648 (`expedientes_judiciales`), 5 documentos descargados (5,35 MB)
  en `00_INPUT/sudespacho_648/civil/` (4 PDFs) y `demanda/` (1 RTF).
- **Pendiente:** eliminar carpeta residual `00_INPUT/sudespacho/` (pull anterior
  pre-arquitectura) y ejecutar pipeline end-to-end por primera vez.

**API sudespacho.net — confirmado (2026-04-25):**

Tras decodificación empírica completa, el sistema usa **dos backends en
paralelo**:

1. **API REST nueva** (`api-crm-commons-pro.sudespacho.biz`), auth
   `x-api-key`. La doc oficial declara `Authorization`, pero ese header
   está reservado al flujo JWT de sesión web y rechaza tokens de API
   key con 401 *Invalid JWT Token*. El header correcto es `x-api-key`
   con valor literal de la clave (sin `Bearer`).

2. **Frontal heredado** (`<tenant>.sudespacho.net`, p.ej.
   `tnm.sudespacho.net`), auth cookie `PHPSESSID` + token CSRF
   extraído del HTML.

**Por qué los dos:**

La API REST **no expone** "listar documentos de un expediente":
   - `relatedRegisters` aparece en el schema de salida de Documents pero
     no es propiedad filtrable.
   - `/api/folders/gdocu/0?related_element=…` devuelve `[]` para los
     expedientes del tenant.
   - `/api/documents` solo permite filtrar por: `asunto, carpeta,
     categoria, condiciones, descripcion, doc, enlaceiberley, esonline,
     estado, fechaenvio, fechaexpiracion, fechamodificacion,
     fechapublicacion, id_carpeta, mime, nombrefinal, nombreoriginal,
     online, origen, origen_id, origen_rutas, subcategoria, tamano,
     tipo, tags, id, grupo_contable_id, id_creador, id_ultimo_modificador,
     fecha_creacion, fecha_ultima_modificacion`. Ninguno enlaza con el
     expediente: probamos `origen` + `origen_id` con id 649 y devuelve 0.
   - `/api/element_register/expedientes_judiciales/{id}` está
     bug-eado: responde 500 *Array to string conversion* para cualquier
     combinación de `properties[]`. Bug del backend (`GetRegister.php`
     línea 48), no de cliente.

El frontal heredado **sí** tiene listado y descarga:
   - `POST /gdocu/list/elemento/gdocu/elemento_relacionado/{element}/
     miembro_relacionado/{id}/direccion_relacionado/der` →
     HTML con `id="fila_gdocu_<doc_id>"` (regex extrae IDs).
   - `POST /gestordocumental/descargaficheros3/id_docu/{doc_id}/
     elemento_relacionado/{element}/miembro_relacionado/{id}/
     direccion_relacionado/der` con `csrf_token` →
     `{resultado, url:<S3 presigned 5 min>}`.
   - GET de la URL S3 → binario, filename en `Content-Disposition`.

**Implementación:**

- `core/sync_sudespacho.py` — cliente API REST (healthcheck,
  metadatos cuando se arregle el backend).
- `core/sync_sudespacho_legacy.py` — cliente legacy (listado +
  descarga). Es el camino activo de ingestión.
- `pull_expediente` (en `sync_sudespacho.py`) usa el cliente legacy
  para listar IDs y descargar cada documento. Idempotente vía
  marcador `.sudespacho_pulled`.

**Pendiente / abierto:**

- La cookie `PHPSESSID` caduca con la sesión: el usuario debe
  refrescarla en `.env` periódicamente. **Mejora deseable**: implementar
  flujo de login automático con usuario/contraseña al frontal heredado
  para no depender de copia manual de cookie.
- Pendiente reportar a sudespacho.net el bug 500 en `GetRegister.php`
  para `expedientes_judiciales`. Cuando lo arreglen, podremos leer
  metadatos del expediente vía API REST nueva.
- Anonimización: descartada explícitamente del MVP. Si se reactiva, su sitio
  natural es un módulo `core/anonymizer.py` entre `extractor` y
  `markdown_generator`, con mapa cifrado fuera del vault.
- Refuerzo del núcleo jurídico: hechos probatorios, nexo causal, viabilidad
  afinada, mejora iterativa de prompts. Es el siguiente objetivo declarado.
- Extensión a otros tipos de litigio civil. La arquitectura lo permite
  (sustituyendo `prompts/` y `KEYWORD_WEIGHTS` por dominio).

---

## 6. Decisiones tomadas y por qué

- **3 capas estrictamente separadas.** Permite reutilizar el core como
  librería y prepara el salto a SaaS multi-tenant (basta montar
  `CASOS_ROOT` por cliente). No mover lógica a la UI nunca.
- **`.md` como fuente de verdad, sin BD.** Inspeccionable, diff-able,
  navegable en Obsidian, portátil. La BD es un coste futuro, no actual.
- **Frontmatter YAML con `prompt_hash` y `model`.** Reproducibilidad y
  auditoría de outputs LLM. Sin esto, debugar un análisis defectuoso es
  imposible.
- **Scoring híbrido por defecto.** Heurística de keywords del dominio
  honorarios como prefiltro + LLM solo sobre los relevantes. Cambiable a
  `heuristic` o `llm` puros desde `.env`.
- **rclone + API sudespacho como backends paralelos**, no excluyentes. Cada
  uno tiene su nicho.
- **No anonimización en MVP**. El sistema es local, el LLM es local: la
  anonimización añadiría complejidad sin beneficio actual.
- **Numeración de párrafos en escritos** y formato de la Sala 1ª TS por
  defecto en los prompts forenses (`demanda`, `requerimiento`).
- **Idempotencia del pipeline.** Re-ejecutar nunca toca `00_INPUT/` ni
  `90_NOTAS_PERSONALES/`. Sí regenera `02_ANALISIS/` y siguientes.

---

## 7. Convenciones que el siguiente Claude debe respetar

**Idioma.** Conversación en español. Documentos legales en español por defecto.
Comunicaciones a clientes ruso-parlantes en ruso salvo indicación.

**Tono.** Conversacional: neutro y directo, sin relleno, sin introducciones.
Documentos legales: formal, riguroso, criterios formales Sala 1ª TS (Times
New Roman 12, márgenes 2,5 cm, interlineado 1,5, párrafos numerados, citas
10 pt cursiva con sangría 1 cm, máx. 25 pp).

**Resolución de conflictos.** Antes de plantear vía judicial, priorizar
**siempre** mediación / negociación / conciliación. Vía judicial solo si
los MASC no son viables o han fracasado.

**Nivel del usuario.** Formación jurídica avanzada. No explicar conceptos
básicos. No incluir advertencias genéricas tipo "consulte a un abogado".

**Jurisprudencia.** Repositorios: CENDOJ y Lefebvre El Derecho. Adaptar citas
y búsquedas a esas fuentes.

**Comunicaciones a E&V.** Registro especialmente cuidado, corporativo, marca
premium.

**Posición procesal.** Mayoritariamente actor. Al analizar viabilidad,
enfocar desde la perspectiva que se indique.

**Respuestas en chat.** Sin bullets ni headers innecesarios. Sin emojis salvo
que se pidan. Sin postambles del tipo "espero que te haya sido útil". Si se
crea un archivo, dar el `computer://` link y un resumen de 1-2 líneas.

---

## 8. Cómo arrancar localmente

```powershell
# Siempre cambiar de directorio primero en PowerShell:
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Sudespacho.net\Base datos expedientes"

python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # editar SUDESPACHO_LEGACY_PHPSESSID, SUDESPACHO_API_KEY

# UI
streamlit run streamlit_app.py

# CLI — crear caso con referencia CRM como case_id
python -m scripts.init_caso "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU" `
    --cliente "EV MMC SPAIN, S.L.U." --contraparte "MARTÍNEZ GARCÍA, LAURA"

# Validar credenciales
python -m scripts.sync_sudespacho check          # API REST (x-api-key)
python -m scripts.sync_sudespacho check_legacy   # cookie PHP (PHPSESSID)

# Pull inicial (modo skip — no descarga si ya existe .pulled)
python -m scripts.sync_sudespacho pull `
    --case "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU" `
    --expediente 648

# Pull incremental (solo docs nuevos)
python -m scripts.sync_sudespacho pull `
    --case "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU" `
    --expediente 648 --incremental

# Sync de todos los casos (tarea programada)
python -m scripts.scheduled_sync --run-pipeline

# Pipeline completo sobre un caso
python -m scripts.run_pipeline "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"

# Tests
pytest -q
```

---

## 9. Gotchas / cosas no obvias

- **Mount sync delay.** El shell del agente (Linux) ve una caché de los archivos
  montados en Windows. Los archivos escritos por el file tool pueden tardar en
  aparecer en bash. Verificar estado real siempre con `Read`, no con `ls`.
  Para correr pytest, copiar el árbol a `outputs/` del agente y ejecutar allí.
- **Comandos PowerShell.** Incluir SIEMPRE `cd` al directorio del proyecto al
  inicio del bloque. Ejemplo:
  ```
  cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Sudespacho.net\Base datos expedientes"
  python -m scripts.sync_sudespacho check
  ```
- **PHPSESSID caduca.** La cookie de sesión PHP del frontal `tnm.sudespacho.net`
  expira por inactividad. Cuando `check_legacy` falla con "Sesión expirada" o
  "redirección a login", hay que: abrir Chrome → tnm.sudespacho.net → F12 →
  Application → Cookies → copiar `PHPSESSID` → pegarlo en `.env` →
  `SUDESPACHO_LEGACY_PHPSESSID=<nuevo valor>`. Mejora futura: login automático
  con usuario/contraseña en `sync_sudespacho_legacy.py`.
- **Carpeta residual `sudespacho/`.** El primer pull (pre-arquitectura) descargó
  en `00_INPUT/sudespacho/`. Tras implementar multi-expediente, los docs se
  descargan en `sudespacho_{id}/`. La carpeta antigua tiene duplicados — limpiarla
  con `Remove-Item -Recurse -Force "...\00_INPUT\sudespacho"` antes del pipeline.
- **`ensure_case` no preserva expedientes al re-crear.** Si se llama con un
  caso ya existente, no reescribe el índice (detecta `is_new = False`). Usar
  `register_expediente` para añadir expedientes a casos existentes.
- **Allowlist Cowork.** `developers.sudespacho.net` y
  `api-crm-commons-pro.sudespacho.biz` están autorizados (Settings →
  Capabilities → Network access). El segundo sirve el OpenAPI live en
  `/api/docs.json`.
- **Los prompts no inventan jurisprudencia.** Prohibido en `viabilidad.md` y
  `demanda.md`. Solo citas de STS presentes en el contexto.
- **`90_NOTAS_PERSONALES/` es zona protegida.** Ningún módulo la lee ni escribe.
- **Numeración H-001, H-002... para hechos atómicos.** Referencia canónica que
  enlaza `hechos_atomicos.md`, `prueba_indexada.md` y `demanda.md`.

---

## 10. Próximas tareas razonables

Si la siguiente sesión tiene que retomar el desarrollo, las prioridades por
orden son:

1. **Limpiar carpeta residual y lanzar pipeline end-to-end.** Eliminar
   `00_INPUT/sudespacho/` del caso `BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU`
   y ejecutar `python -m scripts.run_pipeline "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"`.
   Es la primera ejecución real del pipeline completo.
2. **Configurar Windows Task Scheduler** para `scheduled_sync.py` con
   ejecución diaria (p.ej. 08:00). Verificar que el pull incremental detecta
   correctamente los nuevos documentos judiciales.
3. **Reforzar `prompts/viabilidad.md`** con criterio jurisprudencial más
   denso sobre nexo causal en mediación inmobiliaria. Iterar contra el caso
   real del despacho.
4. **Tests adicionales:** `test_linker.py` (idempotencia wikilinks),
   `test_scorer.py` (heurística sin LLM), `test_pipeline.py` (mock Ollama).
5. **Añadir `prompts/escrito_conclusiones.md`** y otros escritos de fase
   de juicio.
6. **Login automático PHPSESSID.** Implementar flujo usuario/contraseña en
   `sync_sudespacho_legacy.py` para no depender de copia manual de cookie.

---

## 11. Inventario rápido de archivos

```
README.md · pyproject.toml · requirements.txt · .env.example · .gitignore
streamlit_app.py
core/  __init__ · config · utils · llm · case_manager · sync
       sync_sudespacho · sync_sudespacho_legacy
       inventory · extractor · markdown_generator · scorer · viability
       demanda_generator · linker · pipeline
prompts/  scoring · viabilidad · hechos_atomicos · prueba_indexada
          contradicciones · demanda · requerimiento
          intake_consulta.yaml                (63 preguntas Engel para wizard)
data/CASOS/
  _PLANTILLA/                               (8 subcarpetas canónicas)
  BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU/   ← primer caso real
    00_INPUT/
      _caso.md                              expediente 648 registrado
      sudespacho_648/civil/                 4 PDFs descargados
      sudespacho_648/demanda/               1 RTF descargado
      sudespacho_648/.pulled                marcador incremental
      sudespacho/                           ← RESIDUO: eliminar antes del pipeline
scripts/  init_caso · run_pipeline · sync_sudespacho · scheduled_sync
tests/  conftest · test_case_manager · test_inventory · test_utils
        test_sync_sudespacho · test_sync_sudespacho_legacy
docs/   ARQUITECTURA · DESARROLLO · INGESTA_SUDESPACHO · HANDOFF (este)
        Protocolo_Preguntas_Viabilidad_EV.txt   (63 preguntas guion entrevista)
        MANUAL_GESTION_INTERNA_DESPACHO.txt     (manual interno V.2020-1)
        MANUAL_DESPACHO.md                      (índice navegable del manual)
        CONVENCIONES_DESPACHO.md                (operativas accionables)
        PLANTILLA_INFORME_VIABILIDAD.xlsx       (output canónico del intake — Engel)
```
