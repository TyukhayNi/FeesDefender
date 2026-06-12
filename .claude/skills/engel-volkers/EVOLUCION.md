# EVOLUCION.md — plan de evolución asistida de `engel-volkers`

Documento estándar de toda skill del despacho (ver el `README.md` del repo
`despacho-skills`). Define las cinco fases del plan de mejora y el criterio objetivo
para activar cada una. Acompaña al `SKILL.md` y se entrega siempre con la skill.

`engel-volkers` es una **skill de contexto de cliente** (aporta identidad societaria,
Market Centers, tipologías y reglas de trato; no genera escritos ni `.docx`). El modelo
de 5 fases se aplica igual, pero la instrumentación mide *invocación y acierto del
contexto*, no generación de documentos.

---

## Estado actual de la skill `engel-volkers`

| Fase | Estado | Notas |
|------|--------|-------|
| 0 — Skill funcional | Implementada | Contexto de cliente E&V: identidad/sociedades, Market Centers, tipologías CRM, redacción/trato, reglas operativas. |
| 0b — Validación pre-lanzamiento (skill-creator) | **Hecha (2026-05-30)** | Cobertura 100 % vs 17,5 % sin skill; triggering 20/20 (precisión y recall 100 %). Artefactos en `engel-volkers-workspace/`. |
| 1 — Auto-instrumentación | **Implementada (2026-05-30)** | Adaptada a skill de contexto: el asistente registra cada uso (`logs/uso.jsonl`) y recoge feedback de cierre (`logs/<ref>_post.jsonl`). Ver `SKILL.md` §8, `logs/README.md`, `templates/checklist_post.md`. |
| 2 — Corpus de golden cases | Plan | 4-6 asuntos E&V reales como referencia de contexto correcto. Activar tras 5+ usos reales con feedback. |
| 3 — Eval automatizado | Plan | Reutilizar el método fiel de triggering (`engel-volkers-workspace/full_trigger_eval.py`) y la cobertura. Formalizar tras Fase 2. |
| 4 — LLM-as-judge | Plan | Calidad del contexto aportado (exactitud societaria, tipologías, trato). |
| 5 — Subagente editor | Plan | Propone parches al `SKILL.md` a partir de logs y feedback. |

---

## ⏭️ Cómo y cuándo avanzar de fase (recordatorio)

No hace falta recordar el proceso de memoria: esto lo resume. Regla de oro del
despacho: **Fase 1 siempre; Fases 2-5 solo cuando los datos lo pidan.**

**Qué hace cada fase, en una línea:**

- **Fase 1 — Auto-instrumentación:** registra cada uso real y recoge tu feedback. (El termómetro.)
- **Fase 2 — Golden cases:** congela 4-6 asuntos reales aprobados como referencia.
- **Fase 3 — Eval automatizado:** detecta regresiones *formales* al cambiar la skill.
- **Fase 4 — LLM-as-judge:** detecta regresiones de *calidad* sustantiva.
- **Fase 5 — Subagente editor:** lee logs + tus observaciones y te **propone parches** a la skill. (La automejora propiamente dicha.)

**Disparadores (no avanzar hasta cumplirlos):**

| Para pasar a… | Necesitas… |
|---|---|
| **Fase 2** (golden cases) | **5+ usos reales registrados** con feedback del letrado |
| Fase 3 (eval) | Corpus de 4+ goldens estable ≥ 1 mes sin cambios |
| Fase 4 (LLM-judge) | Eval verde en 3 corridas consecutivas |
| Fase 5 (subagente editor) | LLM-judge estable 2 meses + 20+ usos |

**Cuándo y cómo dar el paso:** cuando creas que toca, abre Claude Code y di, literalmente,
«**avanza la skill `engel-volkers` a la Fase X del plan de evolución**». Claude leerá este
documento y los datos disponibles, comprobará el criterio objetivo y construirá la fase.
**No improvises las fases a mano.** Si el criterio aún no se cumple, Claude te lo dirá y
no avanzará.

> Nota: el orden natural es implementar **Fase 1** (auto-instrumentación de invocaciones)
> en cuanto la skill entre en uso real, antes de formalizar el eval de la Fase 3.

---

## Fase 1 — Auto-instrumentación (implementada 2026-05-30, adaptada a skill de contexto)

**Objetivo:** registrar cada uso del contexto E&V y recoger feedback al cerrar el asunto. Sin esto, las fases siguientes no son viables.

**Diferencia con las skills generadoras** (p. ej. `preparacion-juicio-oral`): `engel-volkers` no produce `.docx` ni ejecuta scripts, así que **no hay generadores que instrumentar**. El registro lo escribe el **asistente** siguiendo la orden de `SKILL.md` §8, sin depender de Node.

**Componentes implementados:**
1. Sección «Telemetría y feedback (Fase 1)» en `SKILL.md` (§8) — orden de registro de uso + cuándo ofrecer el feedback de cierre.
2. `logs/README.md` — esquema de `uso.jsonl` y `<ref>_post.jsonl`.
3. `templates/checklist_post.md` — feedback de cierre (una sola pregunta).

**Omitido a propósito** (vs. la skill generadora): checklist **pre** (no hay objetivo táctico que capturar), `schedule` post-juicio (no hay fecha de juicio; el feedback es en el momento del cierre), generadores instrumentados y validador `.docx` (no aplican).

**Criterio de activación de la Fase 2:** 5+ usos reales en `logs/uso.jsonl` con su `<ref>_post.jsonl` rellenado.
