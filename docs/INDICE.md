---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-05
---

# Índice de `docs/` — FeesDefender

> Índice único de la documentación del repo con su **ciclo de vida**, para
> distinguir de un vistazo lo vivo de lo muerto (Fase 3 de
> `GOBERNANZA_FUENTES_VERDAD.md`, recomendación nº3). No sustituye a
> `ARQUITECTURA_RELACIONES.md` (mapa SSOT) ni a `PLAN.md` (cola de trabajo).

## Convenciones

- **Dónde nacen los documentos de diseño:** los specs y planes nuevos van en
  `docs/superpowers/{specs,plans}/` (flujo brainstorming→spec→plan→ejecución, con
  nombre fechado). Los `docs/superpowers/plans/PLAN_*.md` (reubicados desde
  `docs/` el 2026-07-18) son **legacy**: no se crean más con ese nombre; los
  vivos se mantienen donde están hasta que cierren.
- **Estado archivado:** la bitácora histórica de `STATUS.md` se rota a
  `docs/bitacora/AAAA.md`.
- **Campo `estado`** en el frontmatter — **solo de las tres poblaciones que este
  índice cubre**: los docs de raíz de `docs/`, los `PLAN_*.md` legacy y los
  handoffs. Los specs y planes fechados de `docs/superpowers/{specs,plans}/` **no
  están sujetos a esta regla** (ni los indexa este fichero): su estado vive en
  `PLAN.md` — etiqueta, casilla y ledger `## ✅ Cerrados`. El frontmatter se
  introduce el día que se construya un consumidor, no antes. Valores: `vigente`
  (en uso o trabajo pendiente), `historico` (implementado o superado; se conserva
  como registro), `aparcado` (decisión explícita de pausa) o `revisar` (sin señal
  clara — Nikolai confirma). Los handoffs usan **otro vocabulario**
  (`activo | consumido | historico`, `GOBERNANZA_FUENTES_VERDAD §5`). El `estado`
  de los `PLAN_*.md` es un primer pase automatizado.

## Referencia y gobernanza (vigentes)

| Documento | Qué es |
|---|---|
| `ARQUITECTURA.md` | Capas, mapa de dependencias, flujo del pipeline. |
| `ARQUITECTURA_RELACIONES.md` | Mapa SSOT (código/plugin/skills) — *quién depende de quién*. |
| `ARQUITECTURA_CRM_SUDESPACHO.md` | Arquitectura de la integración con el CRM. |
| `GOBERNANZA_FUENTES_VERDAD.md` | Gobernanza de fuentes de verdad (esta iniciativa). |
| `FLUJO_GIT.md` | Flujo de trabajo git + protocolo de cierre (SSOT); manual llano del modelo git. |
| `SEGURIDAD_DATOS.md` | Prevención de fugas de PII y secretos — doctrina, controles y runbook. |
| `INTEGRACION_SUDESPACHO.md` | API sudespacho (§14 fusiona la referencia común externa). |
| `CRM_SUDESPACHO_ATLAS.md` | **SSOT de la superficie del CRM** — inventario generado y re-ejecutable (endpoints Fase A + campos/relaciones/enums por elemento, Fase B). Consultar ANTES de descubrir un endpoint a mano. **Generado**: regenerar con `python -m scripts.crm_atlas discover --phase all` (nunca `--phase a`: no trae Fase B). |
| `INGESTA_SUDESPACHO.md` | Flujo de ingesta desde el CRM. |
| `RUNBOOK_APERTURA_EXPEDIENTE.md` | Runbook operativo de apertura E2E de expediente (alta→intake→sala→viabilidad→CRM→archivo→cierre); gotchas embebidos. |
| `CONVENCIONES_DESPACHO.md` | Convenciones del despacho. |
| `DEAD_ENDS.md` | Callejones sin salida — consultar antes de reintentar. |
| `DESARROLLO.md` | Guía de desarrollo. |
| `DESPLIEGUE_MCP_DRIVE_DISCO.md` | Checklist ejecutable de despliegue del MCP "Drive como disco" V1 (spec §8); código V1 construido y mergeado (PR #52), despliegue manual pendiente. |
| `DEVTOOLS_CAPTURA_CREATE.md` | Captura DevTools para el alta en el CRM. |
| `INSTALACION_ANONIMIZADOR.md` | Instalación del anonimizador (`core/anon`). |
| `MANUAL_DESPACHO.md` | Manual operativo del despacho. |
| `MEJORAS_FUTURAS.md` | Backlog técnico (todo el repo). |
| `MEJORA_CONTINUA_SKILLS.md` | Ciclo de mejora de las skills. |

## Planes de diseño legacy (`docs/superpowers/plans/PLAN_*.md`)

| Documento | Estado | Qué es |
|---|---|---|
| `docs/superpowers/plans/PLAN_DESPLIEGUE_EV.md` | vigente | Despliegue del Streamlit en VPS + apertura a E&V (futuro). |
| `docs/superpowers/plans/PLAN_INTAKE_CRM_COMPLETO.md` | vigente | Intake CRM completo a `05_CRM` (`[SIGUIENTE-INTAKE-CRM-COMPLETO]`); su Paso 2 (procesado) queda supersedido por el diseño de 2026-07-10 (abajo). |
| `superpowers/specs/2026-07-10-intake-crm-a-llm-design.md` | revisar | Bajada CRM → salas → registros → LLM + ejes de eficiencia + ROI (`[SIGUIENTE-INTAKE-CRM-A-LLM]`); aprobación revertida 2026-07-10, en re-brainstorming (decisiones abiertas). |
| `docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md` | vigente | Intake procuradores→CRM; F1/F2 hechas, F3 pendiente. |
| `docs/superpowers/plans/PLAN_PRERELLENO_LLM_VIABILIDAD.md` | historico | Diseño original (motor `core/viabilidad.py` + API Haiku/Sonnet) nunca se construyó; superado en el flujo recomendado por la skill `viabilidad-prerelleno` (lee `00_Input/` crudo). `core/scorer.py`/`core/viability.py` SÍ se usan (vía `core/pipeline.py`, cableado en Streamlit). **Archivado 2026-07-19 (ratificado por Nikolai; triaje).** |
| `docs/superpowers/plans/PLAN_SaRS1_anon_pipeline.md` | vigente | Pipeline SaRS1 multi-hilo; H6 aún abierto. |
| `docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md` | aparcado | Motor OCR→split→MD como conector (⏸️ 2026-07-04; `MEJORAS #48`). |
| `docs/superpowers/plans/PLAN_BITACORA_CASOS.md` | aparcado | Bitácora razonada por caso (planificada s24, 2026-05-21); nunca implementada y fuera de la cola viva — recuperar si se decide. |
| `docs/superpowers/plans/PLAN_SUBDIVISION_CIUDADES.md` | historico | Implementado (`core/ciudades` + `case_locator`; migración 2026-05-21). |
| `docs/superpowers/plans/PLAN_SALA_LECTURA_01_PROCESADO.md` | historico | Superado por la sala única (`[SIGUIENTE-SALA-UNICA-PLANA]` + skill). |
| `docs/superpowers/plans/PLAN_email_aplanado_anidados.md` | historico | Implementado ✅ (Parte 1 — emails `.eml` anidados). |
| `docs/superpowers/plans/PLAN_email_enlaces_drive.md` | historico | Implementado ✅ (Parte 2 — enlaces Drive, `911bf39`). |
| `docs/superpowers/plans/PLAN_registro_outputs_skills.md` | historico | Registro de outputs de skills en el expediente (v1); superado por `PLAN_skills_registro_y_mejora_v3.md`. |
| `docs/superpowers/plans/PLAN_registro_outputs_skills_v2.md` | historico | Idem v2 (añade clientes particulares); superado por v3. |
| `docs/superpowers/plans/PLAN_skills_registro_y_mejora_v3.md` | historico | Registro de outputs + mejora continua (v3 consolidado). Implementado ✅ (`.claude/skills/_shared/{registrar_outputs,registrar_uso}.py`, `scripts/{sync_skill_helpers,package_skill}.py` + copias en skills). |

## Handoffs

> Andamios efímeros de traspaso. **Regla:** `GOBERNANZA_FUENTES_VERDAD §5` (ubicación única
> `docs/superpowers/handoffs/`; `estado:` en el frontmatter = hogar único). Esta tabla es **vista derivada**.

| Documento (en `docs/superpowers/handoffs/`) | Estado | Qué es |
|---|---|---|
| `handoff-2026-07-30-fase0-task4-checkin.md` | consumido | Task 4 de la Fase 0 dual: caracterización de `cmd_checkin` (`tests/test_repository_cli_checkin.py`, PR-A). |
| `handoff-2026-07-19-triaje-plan.md` | consumido | Triaje de la cola de planificación (informe aplicado). |
| `handoff-2026-07-17-apertura-W-{02T3XO,02TH0W,046G2R}-mejoras-proceso.md` | historico | 3 aperturas E2E; consolidados en `RUNBOOK_APERTURA_EXPEDIENTE.md`. |
| `handoff-2026-07-16-rightsizing-mcp-drive-v1.md` | consumido | Right-sizing V1 del MCP Drive-disco (spec `2026-07-16-…` + build PR #52). |
| `handoff-2026-07-13-mcp-sudespacho.md` | consumido | Brainstorming MCP sudespacho (spec `2026-07-13-…`). |
| `handoff-2026-07-03-escritos-judiciales-v1-1.md` | consumido | Actualización de formato v1.0→v1.1 de la skill `escritos-judiciales`. |
| `handoff-2026-06-25-email-atomize-fase3.md` | consumido | Fase 3 de `core/email_atomize`. |
| `handoff-2026-06-18-unificar-salas-lectura.md` | consumido | Unificación de salas de lectura (skill v1.3+ / spec `2026-06-18-…`). |
| `handoff-2026-06-18-buzon-intake.md` | historico | Buzón de intake universal; nunca construido (`core/intake_buzon.py` inexistente), superado por el intake vigente. |
| `handoff-2026-06-12-control-calidad-archivo-check2.md` | historico | Control de calidad del archivo (check 2); absorbido por el diseño de intake-procuradores (F3 / PR #81). |
| `handoff-2026-06-12-sala-lectura-01-procesado.md` | historico | Sala de lectura + `01_Procesado`; deriva a `core/sala_lectura.py` (F4–F6), luego deprecado por la skill v1.3+. |
| `handoff-2026-06-05-prerelleno-viabilidad-experiencia.md` | historico | Conocimiento cristalizado que originó la skill `viabilidad-prerelleno`. |
| `prompt_handoff_expedientes_seguros.md` | historico | Absorción del Anonimizador (`core/anon`). |
| `../specs/cronologia-handoffs/handoff_F*.md` (7) | consumido | Stress-tests de la Cronología v7 (excepción de ubicación: agrupados con su spec). |
