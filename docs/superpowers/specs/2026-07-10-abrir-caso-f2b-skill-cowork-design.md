---
estado: aparcado
dueño: Nikolai (arquitectura) + Claude Code
disparador_original: abrir un caso E&V desde Cowork/móvil (frente Cowork de abrir-caso)
decision: APARCADO 2026-07-10 tras revisión adversarial (bajo ROI + huecos de viabilidad)
---

# abrir-caso F2b (skill Cowork) — APARCADO 2026-07-10

> **NO construir.** Decisión de Nikolai 2026-07-10 tras un red-team adversarial (5 lentes
> independientes sobre el borrador de diseño, verificando contra el código real). El borrador
> resultó a la vez **infactible en partes** y **sobredimensionado**. Este documento conserva el
> **porqué** y los **hallazgos técnicos reutilizables** para que un futuro intento no los
> redescubra. Reabrir solo con disparador real: alguien necesita **abrir un caso desde Cowork/móvil**
> (no solo depositar material — eso ya lo hace `intake-expediente`).

## Por qué se aparca

- **Valor incremental delgado.** El alta CRM **no puede correr desde Cowork** (sin credenciales
  `SUDESPACHO_*` ni red al CRM) → se difiere a la CLI local, que **ya hace todo** (`scripts/abrir_caso.py`,
  F1+F3: estructura + intake + CRM en una pasada). El único delta genuino de F2b sobre lo existente
  es «crear el caso desde el móvil»; el resto **duplica `intake-expediente`** (deposita material en
  `00_Input` con custodia), creando una segunda superficie de drift.
- **Huecos de viabilidad reales en Cowork** (ver hallazgos): sin listado (colisión), sin lectura de
  texto (dedup), y el handoff a la CLI local exige tocar `core/`.

## Hallazgos del red-team (reutilizables — verificados contra el código, 2026-07-10)

Fuente: workflow `spec-redteam-abrir-caso-f2b` (run `wf_1704d4e5-789`), 5 lentes, alta confianza.

1. **`_caso.md` es de DOS niveles, no plano** (lo escribe `core.case_manager._write_case_index`):
   top-level `{case_id, tipo: caso_index, fase, fecha, estado, ciudad, referencia_crm,
   sudespacho_expedientes, drive, meta}` **+** bloque anidado `meta:` = `asdict(CaseMeta)` (~28 campos,
   incl. `tipo_caso`, `direccion`, `cliente`, `estado_repositorio`, `checkout_*`).
   - El **lock de biblioteca** (`core.repository_checkout.estado_de_fm`/`leer_lock_de_fm`) lee
     `estado_repositorio` **SOLO de `fm['meta']`**. Escrito plano → lock **muerto** (default por accidente).
   - `sudespacho_expedientes` sí se lee **top-level** (`get_case_status`/`register_expediente`).
   - `ensure_case` **no reescribe** un `_caso.md` existente (solo cuando `is_new`); lee `fm['meta']`.
     Un `_caso.md` plano de Cowork haría que el `register_expediente` local reconstruya desde `meta`
     vacío y **pierda `cliente`/`titulo`/`referencia_crm`**.
   - `posicion` **NO es campo de `CaseMeta`** (se deriva en runtime con `posicion_de_tipo`, no se
     persiste). No escribirlo.
   - **Cualquier** helper/skill que escriba `_caso.md` debe emitir la estructura EXACTA de
     `_write_case_index` y validarse con un **test de round-trip conductual** (construir → asertar
     `estado_de_fm(...) == 'disponible'`, round-trip lock/pull-state, set de claves top-level ==),
     NO con comparación de nombres de clave.
2. **Cowork no puede LISTAR ni LEER texto con `expedientes-xl`** (sus tools: `hash_path`,
   `hash_tree`, `copy_path`, `copy_dir`, `extract_archive`, `write_file_base64`, `append_text`,
   `delete_path` — sin `list`/`read`). → la **detección de colisión** (listar `CASOS/<ciudad>/`) y la
   **dedup** vs `00_Input/_intake_log.jsonl` no son ejecutables ahí. El MCP `expedientes` es LOCAL;
   el Drive de solo-lectura de Cowork de la cuenta E&V **no ve** «EXPEDIENTES - TYUKHAY LEGAL».
   *(Vía posible si se reabre: `google-despacho` read está en Cowork vía `.dxt`, VE la unidad TL y
   tiene `search_files` → podría cubrir listado/colisión; pero es otra dependencia.)*
3. **El handoff a la CLI local está roto** como se planteó: (a) el caso ya existe → `ColisionCaso`
   sin `--force`; (b) con `--force` pero sin `--folder-id/--team-id`, `--fuente drive_ev` llama a
   `pull_drive_ev(None, None)` → crash de rclone; (c) aun con todo, **re-descarga** (Cowork no
   escribe `.pulled`; el sha-dedup solo suprime el evento de log, no la transferencia). **No existe
   modo solo-CRM/skip-intake** en la CLI → arreglarlo exige tocar `core/`.
4. **Mecanismo de sync mal asumido:** `traza.py` **no** está en `.claude/skills/_shared/` (vive a mano
   en `intake-expediente/scripts/`, e `intake-expediente` **no** está en `_TARGETS`); y
   `sync_skill_helpers.py` copia **todos** los `_shared/*.py` a **todos** los targets (sin selección
   por fichero/target) → meter un helper E&V en `_shared` lo esparce a las 7 skills legales.
5. **Contrato de entrada sin definir** + `parse_ev_folder_name` es core-only (no está en Cowork).

## Si se reabre (versión recomendada, delgada)

No una skill que duplique el intake. La forma correcta sería **una de estas dos**, decidida con
disparador real:
- **(A)** Añadir a `intake-expediente` una rama «crea el caso si no existe» — el único delta real —
  escribiendo un `_caso.md` **fiel a `_write_case_index`** (dos niveles) con test de round-trip.
- **(B)** Skill nueva pero **delgada**: solo alta (identidad + `_caso.md` fiel + TODO CRM), delegando
  el material a `intake-expediente`; nombrar `google-despacho` para el listado de colisión; y, para el
  cierre en local, **añadir a la CLI un modo `--skip-intake`/`--crm-only`** (levantar el veto de no
  tocar `core/`) o documentar honestamente la re-descarga.

Relación con el ecosistema y el resto de fases: ver
`docs/superpowers/specs/2026-07-09-abrir-caso-design.md` y `PLAN.md` `[abrir-caso]`.
