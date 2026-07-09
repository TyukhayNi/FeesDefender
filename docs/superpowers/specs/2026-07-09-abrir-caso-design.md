---
estado: vigente
dueño: Nikolai (arquitectura) + Claude Code (implementación)
disparador: encargo de Nikolai — unificar alta + intake + alta CRM en una sola pasada
banco_de_pruebas: W-02Z2NR (Passeig Marítim / Castelldefels) y W-02VND1 (Tibidabo 8)
---

# SPEC — `abrir-caso`: alta + intake de expediente en una sola pasada

**Versión:** 1.0 (diseño cerrado; reconciliado con el código real de FeesDefender)
**Fecha:** 2026-07-09
**Naturaleza:** documento de DISEÑO. El siguiente paso es `writing-plans`, no construir.
**Origen:** reescribe el borrador `SPEC_ABRIR_CASO.md` v0.1 (aportado por Nikolai) anclándolo
al código existente y cerrando las cinco decisiones abiertas de su §15.

---

## 0. Problema que resuelve

Abrir un expediente FeesDefender hoy es una secuencia manual de piezas que ya existen
pero **no están unidas**:

1. Crear la estructura de carpetas + `_caso.md` → `core/case_manager.ensure_case()`.
2. Depositar los ficheros del Drive E&V en `00_Input/` con trazabilidad forense →
   `core/intake_drive.pull_drive_ev()` (local) o la skill `intake-expediente` (Cowork).
3. Dar de alta el expediente en el CRM sudespacho → `core/sudespacho_create.create_expediente()`.

Las tres funcionan por separado; ninguna herramienta las orquesta. `abrir-caso` las pega
en **una sola operación** disparada por `(W-code + fuente de ficheros)`, minimizando las
idas y vueltas y con las invariantes forenses cableadas de principio a fin.

Además ataca el cuello de botella medido de trabajar contra el Drive (ver
`PLAN.md` → «PRINCIPIO TRANSVERSAL — copia al Drive por lote»): en Cowork el coste no son
los bytes sino el **número de llamadas MCP** (~10-15 s cada una). `abrir-caso` colapsa las
operaciones por-fichero en primitivas de árbol (`extract_archive`, `copy_dir`, `hash_tree`).

---

## 1. Alcance

**Incluye:** resolución de identidad/nombre de caso (con política de colisión),
montaje de la estructura canónica, extracción/depósito clasificado en `00_Input/<fuente>/`,
verificación por SHA-256, escritura de `_intake_log.jsonl`, inicialización de `_caso.md`,
alta en el CRM sudespacho (con gate de confirmación) y volcado de IDs.

**No incluye:** organización de la sala de lectura (`organizar-sala-lectura`),
triaje/viabilidad, ni redacción de escritos. Tampoco procesa por fuente (MIME del `.eml`,
OCR del PDF): eso sigue en el pipeline local. `90_Notas personales/` es zona reservada del
abogado — ningún paso la lee ni la escribe.

**Fuente primaria (F1):** `drive_ev` (la carpeta `W-XXXXXX` del Drive E&V, o su zip en
`_ingest`). Las fuentes `manual`/`whatsapp`/`email` entran en F3.

---

## 2. Decisiones cerradas (brainstorming 2026-07-09)

| # | Decisión | Resolución |
|---|---|---|
| D1 | **Contexto de ejecución** | **Ambos frentes.** Cerebro puro en `core/` + un orquestador CLI local (rclone/G:) + una skill Cowork (conector `expedientes-xl`). Comparten el cerebro. |
| D2 | **Política de colisión de código** | **`ask`.** W-code duplicado ⇒ error (salvo `--force`). Código duplicado + W-code nuevo ⇒ **para y pregunta** qué código usar. No autonumera en silencio. |
| D3 | **Alta CRM en la pasada** | **API con gate de confirmación.** Prepara y muestra el payload; crea el expediente solo tras OK del usuario. El resto (carpetas+intake+log) corre sin gate. |
| D4 | **Verificación en el frente local** | **Hashear tras el pull.** `hash_tree` local después del `rclone`, registrando SHA-256 de cada fichero en el evento `pull_drive_ev`. Cumple la cadena de custodia (§11). |
| D5 | **Hogar del CLI** | **Módulo nuevo `scripts/abrir_caso.py` (Typer)**, estilo `init_caso.py`. No toca `repository_cli.py` (biblioteca, validado en vivo). `init_caso.py` se conserva como atajo trivial; deprecación diferida (con disparador). |

Decisiones del borrador v0.1 ya resueltas por el código existente (su §15):
- **§15.1 (reexponer `register_expediente`):** innecesario. El alta real es
  `sudespacho_create.create_expediente[_judicial]()`, ya operativa por REST. (Ojo: el nombre
  `register_expediente` **ya está cogido** por un escritor de metadata local — ver §3.)
- **§15.2 (mapeo tipo_asunto/procedimiento):** existe `tag_defaults_for_tipo_caso[_judicial]`
  + los `_build_rest_payload_*`. Se reutiliza; huecos se rellenan sobre casos reales.
- **§15.3 (esqueleto plantilla física vs declarativo):** declarativo. `CASO_SUBDIRS` +
  `INPUT_SUBDIRS` + `WHATSAPP_SUBDIRS` + `EMAIL_SUBDIRS` ya existen y `ensure_case()` los
  monta idempotente. **No** hace falta carpeta-plantilla física.
- **§15.5 (reutilizar vs sustituir skills):** orquestar, no reescribir. Las tres piezas ya
  existen sueltas.

---

## 3. Arquitectura — 3 capas

Separación clave para testear y para no reimplementar lógica (patrón «biblioteca de casos»:
cerebro puro + orquestadores finos + músculo de I/O).

| Capa | Responsabilidad | Determinista | Toca bytes |
|---|---|---|---|
| `core/abrir_caso.py` | naming, política de colisión, `plan_intake`, `reconcile`, `crm_payload` | Sí (puro, testeable) | No |
| `core/*` existentes | alta (`ensure_case`), intake (`pull_drive_ev`), CRM (`create_expediente`), log (`append_event`) | — | Sí (rclone/FS) |
| Conector `expedientes-xl` | primitivas de bytes server-side (Cowork) | — | Sí |
| Orquestadores | pegan las piezas, gestionan gates y CRM | No | vía core/conector |

### 3.1 `core/abrir_caso.py` — CEREBRO PURO (cero I/O)

- `resolver_identidad(args, listado_ciudad, cfg) -> Identidad`
  - `case_id = "{codigo} - {direccion} ({w_code}) - {sufijo}"` — formato **canónico**
    que valida `core.utils.validate_case_id` (la dirección va pegada al paréntesis de la
    referencia, **sin** guion previo; p. ej. `BaRS1 - Tibidabo 8 (W-02VND1) - Vuelta`).
  - Busca en el listado de `CASOS/<ciudad>/` prefijos `{codigo}` y `{w_code}`.
  - **Colisión (D2):** `w_code` duplicado ⇒ error (mismo caso ya existe) salvo `--force`.
    `codigo` duplicado + `w_code` nuevo ⇒ marca `requiere_confirmacion` (política `ask`);
    el orquestador para y pregunta.
  - Salida: `case_id`, `case_path`, `codigo`, colisiones detectadas, `posicion` (derivada de
    `tipo_caso` vía `config.posicion_de_tipo`).
- `plan_intake(inventario, log_existente, fuente) -> PlanIntake`
  - `inventario` = lista `{relpath, sha256|None, size}` (del árbol extraído en Cowork, o del
    `hash_tree` post-pull en local). Para cada fichero: `fuente → 00_Input/<sub>`, `evento`
    (`pull_drive_ev`|`upload_manual`|`upload_whatsapp`|`upload_email`|`upload_entrevista`),
    ruta destino canónica.
  - Dedup: sha256 vs `_intake_log.jsonl` existente (`is_duplicate`); marca 0-byte.
  - Salida: **plan** = lista `{src, dst, evento, dup, zero, sha256}`. Sin tocar bytes.
    En `--dry-run` la ejecución termina aquí.
- `reconcile(plan, hashes_destino) -> Reconciliacion`
  - cada fichero esperado existe y su sha coincide; `count` coincide; sin extras inesperados.
  - mismatch ⇒ el orquestador **aborta** (no escribe log), reporta diffs.
- `crm_payload(identidad, args) -> NuevoExpedienteExtrajudicial | NuevoExpedienteJudicial`
  - construye el DTO de `sudespacho_create` con `referencia_cliente = case_id`, posición,
    cliente propio (`CLIENTES_PROPIOS_EV`, default `EV_MMC_SPAIN`), `tags` vía
    `tag_defaults_for_tipo_caso[_judicial]`, cuantía/serie si constan.
- Constructores de detalle de evento (dicts puros) para `intake_log.append_event`.

**El cerebro no importa rclone, ni el conector, ni la red.** Todo lo verifican tests unitarios.

### 3.2 Orquestador LOCAL — `scripts/abrir_caso.py` (Typer)

Flujo (§5), sobre `CASOS_ROOT` (montaje `G:` / disco):
`ensure_case()` → `pull_drive_ev()` (rclone `gdrive_ev`) → **`hash_tree` local** (D4) →
`reconcile` → `append_event` con sha256 → `_caso.md` init → **gate CRM** →
`create_expediente()` → `patch _caso.md`. Reutiliza el guard §6 de intake vía `dir_intake`.

### 3.3 Orquestador COWORK — skill `abrir-caso`

Mismo flujo, músculo distinto: conector `expedientes-xl`
(`extract_archive` con `strip_top_level` → `copy_dir` por categoría → `hash_tree` →
`append_text`), bytes siempre server-side. Comparte el cerebro `core/abrir_caso.py`
(importado en el PC vía el puente de Claude Desktop, igual que hoy corre el pipeline local).

---

## 4. Contrato de invocación (CLI local)

```
python -m scripts.abrir_caso \
  --w-code       W-02Z2NR                 (obligatorio)
  --ciudad       Barcelona                 (obligatorio; deriva CASOS/<ciudad>/)
  --tipo-caso    VUELTA                    (enum TIPOS_CASO_ALL; obligatorio)
  --direccion    "Passeig Marítim, 30 - Castelldefels (08860)"
  --sufijo       "Vuelta"                  (describe el asunto; parte del nombre de carpeta)
  --codigo-caso  BaRS11                    (opcional; si falta y no hay colisión, se propone)
  --fuente       drive_ev                  (default drive_ev; F1 solo soporta drive_ev)
  --zip          <ruta en _ingest>         (opcional; solo frente Cowork/offline)
  --folder-id    <id carpeta Drive EV>     (frente local: pasa a pull_drive_ev)
  --team-id      <shared drive EV>         (frente local)
  --cliente      EV_MMC_SPAIN              (clave de CLIENTES_PROPIOS_EV; default)
  --posicion     (auto)                    (default: posicion_de_tipo(tipo_caso))
  --contraparte  / --cuantia               (opcionales)
  --crm          api|skip                  (default api → gate de confirmación; skip = TODO)
  --force                                  (fuerza pese a W-code duplicado)
  --dry-run                                (solo plan, no escribe)
```

**Defaults del despacho** (no preguntar): `posicion` ← `posicion_de_tipo(tipo_caso)`;
`cliente` ← `EV_MMC_SPAIN`; `crm` ← `api` (con gate).

---

## 5. Pipeline

### 5.1 Resolver identidad y nombre de caso
`resolver_identidad`. Colisión según D2 (`ask`). Salida: `case_id`, `case_path`, `codigo`,
`posicion`.

### 5.2 Montar esqueleto — `ensure_case()`
Una llamada idempotente. Monta `CASO_SUBDIRS` + subestructura de `01_Procesado` +
`INPUT_SUBDIRS` + `WHATSAPP_SUBDIRS` + `EMAIL_SUBDIRS` + base lazy de `00_Input/05_CRM/` +
plantillas de viabilidad en `02_Analisis/`. Escribe `_caso.md` con `tipo_caso`, `ciudad`,
`direccion`, `cliente`, `posicion`. **No** toca CRM ni Drive.

### 5.3 Obtener el inventario de origen
- **Local:** `pull_drive_ev(case_id, folder_id, team_id)` (rclone). Idempotente por `.pulled`.
  Luego `hash_tree(00_Input/01_Drive EV)` local → inventario con sha256 (D4).
- **Cowork:** `extract_archive(zip, dest=_ingest/_extract_<w_code>, strip_top_level=True)`;
  el inventario sale de listar el árbol extraído + `hash_tree` de origen.

### 5.4 Planificar depósito — `plan_intake` (puro)
Mapeo fuente→subcarpeta, dedup por sha vs log, 0-byte, evento. Salida = plan.
En `--dry-run` termina aquí y reporta el plan.

### 5.5 Depositar
- **Local:** ya depositado por el `rclone copy` de 5.3 (pull = copia).
- **Cowork:** `copy_dir(extract/<cat>, case/00_Input/01_Drive EV/<cat>)` por categoría de
  primer nivel; saltar duplicados/0-byte según plan.

### 5.6 Verificación por hash — `reconcile`
`hash_tree(case/00_Input/01_Drive EV) -> {relpath: sha256}` (ya obtenido en 5.3 local).
`reconcile(plan, hashes)`: existe+coincide, count, sin extras. Mismatch ⇒ **abortar sin log**.

### 5.7 Escribir `_intake_log.jsonl`
`append_event(case_id, event, details={count, files:[{path, sha256}]})` — el `path` es
relativo a `00_Input/`, posix. Eventos válidos ya en `INTAKE_EVENTS`.

### 5.8 Inicializar/actualizar `_caso.md`
Ya escrito por `ensure_case` (5.2). Reentrante: si existe, no recrea.

### 5.9 Alta CRM — **gate de confirmación (D3)**
Si `--crm api`: `crm_payload(...)` → **mostrar** el payload → esperar OK →
`create_expediente[_judicial]()` (REST `x-api-key`), que devuelve **solo el `id`** (string).
Volcar ese `id` a `_caso.md` vía `register_expediente(case_id, id, element)` (el escritor de
metadata local; `element` = `extrajudiciales`|`expedientes_judiciales` según la rama del
payload). `num`/`serie` no vienen en la respuesta de alta: si se quieren en `_caso.md`, un
`pull_crm` posterior los trae (fuera de F1). `--crm skip` ⇒ `referencia_crm` pendiente + TODO.

### 5.10 Limpieza y reporte
Cowork: `delete_path(_ingest/_extract_<w_code>)` (el zip crudo en `_ingest` **intacto**).
Reporte: depositados por fuente/categoría, hashes OK, duplicados/0-byte, ID de CRM,
colisiones avisadas.

---

## 6. Contratos de datos (anclados al código real)

### 6.1 `_caso.md` — clase `CaseMeta` (`core/case_manager.py:62`)
`abrir-caso` rellena: `case_id`, `titulo`, `tipo_caso`, `ciudad`, `direccion`, `cliente`,
`contraparte?`, `cuantia?`, `posicion` (derivada), y tras el CRM `referencia_crm` +
`sudespacho_expedientes[]` (`ExpedienteLink` = `{id, element, input_dir}`). El lock de
biblioteca (`estado_repositorio="disponible"`, etc.) nace por defecto — un caso nuevo no
está prestado.

### 6.2 Evento de intake — `intake_log.append_event` (`core/intake_log.py:134`)
Formato: `{"ts", "actor", "event", "case_id", "details"}`. `details` = `{count, files:[{path,
sha256}]}`. Novedad: en el frente **local** el evento `pull_drive_ev` ahora incluye `sha256`
por fichero (hoy no los tiene — D4).

### 6.3 CRM — `sudespacho_create` (`core/sudespacho_create.py`)
`create_expediente(NuevoExpedienteExtrajudicial)` / `create_expediente_judicial(...)`.
Endpoints `POST /api/element_register/{extrajudiciales|expedientes_judiciales}` (base
`api-crm-commons-pro.sudespacho.biz`, header `x-api-key`). Respuesta 201 `{id}`.

---

## 7. Nueva primitiva del conector (F2)

Añadir a `plugins/expedientes_xl/` (`fsops.py` + `server.py` + tests):

1. **`hash_tree(root) -> {relpath: sha256}`** — hash recursivo server-side en 1 llamada.
   Colapsa N `hash_path` en 1. (`hash_path` de-a-uno ya existe.)
2. **`extract_archive(..., strip_top_level: bool = False)`** — quita el wrapper del export
   (evita el nivel extra tipo `Passeig Marítim.../`).

**No** hace falta `copy_tree`: `copy_dir` ya copia árboles (recursivo, `dirs_exist_ok=True`).
El borrador v0.1 se equivocaba en este punto.

---

## 8. Idempotencia y reejecución

- **Lock write-then-verify** en `_caso.md` (mismo mecanismo con nonce que el checkout de
  biblioteca; reutiliza `case_manager`/`repository_checkout`).
- **Reentrante:** si `_caso.md` existe, no recrea estructura; el intake deduplica por sha
  contra el log; el CRM no re-da de alta si `sudespacho_expedientes` ya tiene entrada para
  ese `element` (evita expedientes fantasma por reejecución — refuerza el gate D3).
- `--dry-run` para plan sin efectos.

---

## 9. Manejo de errores

| Fallo | Comportamiento |
|---|---|
| Zip ausente/corrupto | abortar antes de tocar nada |
| Hash mismatch en §5.6 | abortar, **no** escribir log, reportar diffs |
| `w_code` duplicado | error salvo `--force` |
| `codigo` colisiona + w_code nuevo | parar y **preguntar** (D2 `ask`) |
| CRM caído / rechaza | completar Drive+intake, `referencia_crm` pendiente + TODO, salir 0 con warning |
| Duplicados / 0-byte | saltar y reportar, no abortar |
| Caso prestado (lock) | el guard §6 desvía el intake a `_pendiente_checkin/` (conducta existente) |

---

## 10. Seguridad y cadena de custodia (invariantes)

- Los bytes se procesan **server-side** (Cowork) o en disco local (CLI); **nunca** por el chat.
- **SHA-256 obligatorio de todo lo depositado** — incluido el frente local (D4). El log es la
  prueba de integridad.
- El crudo (`_ingest/<zip>`) **no se borra**; solo se limpia el temporal de extracción.
- Nombres de fichero **se preservan** en `00_Input` (el renombrado canónico es fase posterior
  de sala de lectura).
- Sin PII en las rutas del evento más allá del nombre de fichero existente. Docs/commits
  referencian por `W-XXXXX` (regla `docs/SEGURIDAD_DATOS.md`).
- `90_Notas personales/` intocable.

---

## 11. Fases (build incremental, tests por fase)

- **F1 — cerebro puro + CLI local, fuente `drive_ev`.** `core/abrir_caso.py`
  (`resolver_identidad`/`plan_intake`/`reconcile`/`crm_payload`) + `scripts/abrir_caso.py`
  (Typer) orquestando `ensure_case`+`pull_drive_ev`+hash local+gate CRM+`append_event`.
  Tests unitarios del cerebro + integración con Drive temporal (rclone mock / CRM mock).
  **Retorno inmediato — es el frente de trabajo de Nikolai.**
- **F2 — conector + skill Cowork.** `hash_tree` + `strip_top_level` en `expedientes-xl`
  (+tests); skill `abrir-caso` (Cowork) que reutiliza el cerebro. Empaquetado `.skill`.
- **F3 — resto de fuentes + deprecación.** Fuentes `manual`/`whatsapp`/`email` en
  `plan_intake`; evaluar plegar/deprecar `init_caso.py` (con disparador).

---

## 12. Relación con el ecosistema de skills

`abrir-caso` es el **eslabón que hoy falta al principio** del flujo del despacho: produce el
caso con `00_Input/` poblado y `_caso.md`, y todo lo demás lo **consume**.

```
abrir-caso ──► organizar-sala-máquina ──► organizar-sala-lectura ──► viabilidad-prerelleno
 (crea +        (OCR/MD, procesado         (vista humana)              (informe)
  intake +       máquina — NUEVA,
  CRM)           en construcción)
     └──► triaje-viabilidad (lee 00_Input directo, sin sala) ──► preparacion-litigio-civil
                 ──► escritos-judiciales ──► preparacion-audiencia-previa / -juicio-oral
```

**Handoff (no bloqueante).** Al terminar, `abrir-caso` **sugiere** como siguiente paso
`organizar-sala-máquina` sobre el caso recién creado (paso atómico + puntero, no encadenado
a la fuerza; igual que `expediente-a-md` sugiere `organizar-sala-lectura`, un eslabón antes).
⚠️ **Nombre provisional:** `organizar-sala-máquina` se está construyendo en otra sesión —
confirmar nombre e interfaz antes de cablear el handoff en F2.

**Solapes.**
- `intake-expediente` — `abrir-caso` **envuelve** su intake (depósito + log forense vía
  `expedientes-xl`) para el escenario "caso nuevo". `intake-expediente` **se queda** para su
  caso propio: añadir ficheros a un caso **ya existente**.
- `preparacion-litigio-civil` — **paralela**, para expedientes de **particulares** (no E&V,
  sin CRM); comparte el scaffolder declarativo (`scaffold_caso.py`), no el `_caso.md`.

**Infraestructura compartida.** Conector `expedientes-xl` · log `_intake_log.jsonl`
(`intake_log.append_event`) · `_plantilla-skill` (`requires` de estilo/verificación) ·
registro de la relación en `docs/ARQUITECTURA_RELACIONES.md`.

**Nota de gobernanza.** Esta sección es la primera instancia de un patrón que Nikolai quiere
en **todas** las skills del flujo; el diseño robusto (grafo único + generación + guardarraíl,
para evitar drift bidireccional) está en `docs/MEJORAS_FUTURAS.md` #50, como trabajo de otra
sesión.

---

## 13. Tests

- **Unit (core, puro):** naming/colisión (`ask`, `--force`, w_code dup); `plan_intake`
  (dedup, 0-byte, mapeo fuente→subcarpeta, evento correcto); `reconcile` (mismatch, count,
  extras); `crm_payload` (paridad con los DTOs de `sudespacho_create` + `tag_defaults`);
  derivación de posición/cliente.
- **Integración:** Drive temporal — `ensure_case`→pull(mock)→hash→reconcile→log; reejecución
  idempotente (dedup + no re-alta CRM); gate CRM con CRM mock (confirma/skip/caído).
- **Guard §6:** intake sobre caso prestado desvía a `_pendiente_checkin/`.
- **Regresión:** `pull_drive_ev` sigue funcionando para callers existentes tras añadir el
  hash post (no romper la firma / comportamiento actual salvo el evento enriquecido).

---

## 14. Pseudocódigo del orquestador local

```python
def abrir_caso(args):
    ident = core.abrir_caso.resolver_identidad(args, listar(f"CASOS/{args.ciudad}"), cfg)  # 5.1
    if ident.requiere_confirmacion and not args.force:
        codigo = preguntar_codigo(ident)          # D2 ask
    case = case_manager.ensure_case(ident.case_id, tipo_caso=args.tipo_caso, ...)          # 5.2
    res = intake_drive.pull_drive_ev(ident.case_id, args.folder_id, args.team_id)          # 5.3
    hashes = hash_tree_local(case / "00_Input/01_Drive EV")                                 # D4
    plan = core.abrir_caso.plan_intake(inventario(hashes), leer_log(case), "drive_ev")     # 5.4
    if args.dry_run: return plan
    core.abrir_caso.reconcile(plan, hashes)        # aborta si mismatch                     # 5.6
    intake_log.append_event(ident.case_id, "pull_drive_ev",
                            details={"count": len(plan.ok), "files": plan.con_sha})          # 5.7
    if args.crm == "api":                                                                   # 5.9
        payload = core.abrir_caso.crm_payload(ident, args)
        if confirmar(payload):                     # gate D3
            exp_id = sudespacho_create.create_expediente(payload)   # -> str (id)
            case_manager.register_expediente(ident.case_id, exp_id, element_de(payload))  # metadata local
    return core.abrir_caso.report(...)                                                       # 5.10
```

---

## 15. Decisiones diferidas (no bloquean F1)

1. Mapeo fino de `tipo_asunto`/`tipo_procedimiento` para tipos de caso poco frecuentes: se
   completa sobre casos reales (los defaults de `tag_defaults_for_tipo_caso` cubren el común).
2. Deprecación de `init_caso.py`: con disparador, en F3.
3. `abrir-caso` desde Streamlit (UI): fuera de alcance; el core y la CLI lo habilitan si se
   pide.
