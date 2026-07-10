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
  nombre fechado). Los `docs/PLAN_*.md` sueltos son **legacy**: no se crean más
  ahí; los vivos se mantienen donde están hasta que cierren.
- **Estado archivado:** la bitácora histórica de `STATUS.md` se rota a
  `docs/bitacora/AAAA.md`.
- **Campo `estado`** en el frontmatter de cada doc: `vigente` (en uso o trabajo
  pendiente), `historico` (implementado o superado; se conserva como registro),
  `aparcado` (decisión explícita de pausa) o `revisar` (sin señal clara — Nikolai
  confirma). El `estado` de los `PLAN_*.md` es un primer pase automatizado.

## Referencia y gobernanza (vigentes)

| Documento | Qué es |
|---|---|
| `ARQUITECTURA.md` | Capas, mapa de dependencias, flujo del pipeline. |
| `ARQUITECTURA_RELACIONES.md` | Mapa SSOT (código/plugin/skills) — *quién depende de quién*. |
| `ARQUITECTURA_CRM_SUDESPACHO.md` | Arquitectura de la integración con el CRM. |
| `GOBERNANZA_FUENTES_VERDAD.md` | Gobernanza de fuentes de verdad (esta iniciativa). |
| `SEGURIDAD_DATOS.md` | Prevención de fugas de PII y secretos — doctrina, controles y runbook. |
| `INTEGRACION_SUDESPACHO.md` | API sudespacho (§14 fusiona la referencia común externa). |
| `INGESTA_SUDESPACHO.md` | Flujo de ingesta desde el CRM. |
| `CONVENCIONES_DESPACHO.md` | Convenciones del despacho. |
| `DEAD_ENDS.md` | Callejones sin salida — consultar antes de reintentar. |
| `DESARROLLO.md` | Guía de desarrollo. |
| `DEVTOOLS_CAPTURA_CREATE.md` | Captura DevTools para el alta en el CRM. |
| `INSTALACION_ANONIMIZADOR.md` | Instalación del anonimizador (`core/anon`). |
| `MANUAL_DESPACHO.md` | Manual operativo del despacho. |
| `MEJORAS_FUTURAS.md` | Backlog técnico (todo el repo). |
| `MEJORA_CONTINUA_SKILLS.md` | Ciclo de mejora de las skills. |

## Planes de diseño legacy (`docs/PLAN_*.md`)

| Documento | Estado | Qué es |
|---|---|---|
| `PLAN_DESPLIEGUE_EV.md` | vigente | Despliegue del Streamlit en VPS + apertura a E&V (futuro). |
| `PLAN_INTAKE_CRM_COMPLETO.md` | vigente | Intake CRM completo a `05_CRM` (`[SIGUIENTE-INTAKE-CRM-COMPLETO]`); su Paso 2 (procesado) queda supersedido por el diseño de 2026-07-10 (abajo). |
| `superpowers/specs/2026-07-10-intake-crm-a-llm-design.md` | aprobada | Bajada CRM → salas → registros → LLM + ejes de eficiencia + ROI (`[SIGUIENTE-INTAKE-CRM-A-LLM]`); aprobada 2026-07-10: motor A2, ejes E2+E3+E4. |
| `PLAN_INTAKE_PROCURADORES_EMAIL.md` | vigente | Intake procuradores→CRM; F1/F2 hechas, F3 pendiente. |
| `PLAN_PRERELLENO_LLM_VIABILIDAD.md` | vigente | Pre-relleno LLM del informe de viabilidad. |
| `PLAN_SaRS1_anon_pipeline.md` | vigente | Pipeline SaRS1 multi-hilo; H6 aún abierto. |
| `PLAN_MOTOR_DOCUMENTAL.md` | aparcado | Motor OCR→split→MD como conector (⏸️ 2026-07-04; `MEJORAS #48`). |
| `PLAN_BITACORA_CASOS.md` | aparcado | Bitácora razonada por caso (planificada s24, 2026-05-21); nunca implementada y fuera de la cola viva — recuperar si se decide. |
| `PLAN_SUBDIVISION_CIUDADES.md` | historico | Implementado (`core/ciudades` + `case_locator`; migración 2026-05-21). |
| `PLAN_SALA_LECTURA_01_PROCESADO.md` | historico | Superado por la sala única (`[SIGUIENTE-SALA-UNICA-PLANA]` + skill). |
| `PLAN_email_aplanado_anidados.md` | historico | Implementado ✅ (Parte 1 — emails `.eml` anidados). |
| `PLAN_email_enlaces_drive.md` | historico | Implementado ✅ (Parte 2 — enlaces Drive, `911bf39`). |

## Handoffs

| Documento | Estado | Qué es |
|---|---|---|
| `prompt_handoff_expedientes_seguros.md` | historico | Handoff de absorción del Anonimizador (ya integrado en `core/anon`). |
