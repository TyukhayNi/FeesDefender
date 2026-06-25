# Handoffs de stress-test — Cronología Unificada de Prueba

Material de **provenance de diseño** del spec
[`../2026-06-25-cronologia-unificada-design.md`](../2026-06-25-cronologia-unificada-design.md) (v7, DISEÑO COMPLETO).

**Qué son.** Cada fichero es el *handoff* que se entregó a un **revisor adversarial**
(Perplexity) para intentar **romper** una decisión candidata con casos límite y marcos de
referencia. Es decir: son los **PROMPTS de la revisión adversarial**, no las decisiones.
Las decisiones **sintetizadas** (lo que hay que construir) viven en el spec, no aquí:

| Handoff (presente) | Decisión | Sección del spec |
|---|---|---|
| `handoff_F3D4_stresstest_claude.md` | Fórmula del 🟢🟡🔴 (estatus de soporte) — **incluye pseudocódigo `calcular_estatus_soporte` + tabla estructura→estatus** | §7.4 |
| `handoff_F3D5_stresstest_claude.md` | Contradicción inter-fuente — **incluye mini-pseudocódigo `procesar_contradiccion`** | §7.5 |
| `handoff_F4D1_stresstest_claude.md` | Los tres tiempos del evento | §8.1 |
| `handoff_F4D2_stresstest_claude.md` | Orden parcial y comparación de intervalos | §8.2 |
| `handoff_F5D1_stresstest_claude.md` | Contrato del adaptador y frontera de 3 capas | §9.1 |
| `handoff_F5D2_stresstest_claude.md` | Encaje con capas de fichero, staging, orden de construcción | §9.2 |
| `handoff_F6D1_stresstest_claude.md` | Entregable humano unificado (vista multi-fuente) | §10.1 |

**Conjunto COMPLETO (2026-06-25):** los 7 handoffs que el spec cita están en el repo. Los de
**F3.D4 y F3.D5** son los únicos que traen **pseudocódigo operativo** (`calcular_estatus_soporte`,
`procesar_contradiccion`) además del stress-test — material directamente build-ready para el
cómputo del semáforo y de la contradicción.

## Naturaleza

Documentos de diseño/auditoría, **no construcción**. Anonimizados (sin datos reales de
cliente). Registrados el 2026-06-25 para conservar la cadena de diseño junto al spec.
