# EVOLUCION.md — Plan de evolución asistida en cinco fases

Documento estándar de toda skill del despacho. Define las cinco fases del plan de
evolución y el criterio objetivo para activar cada una. Acompaña al `SKILL.md` y
se entrega siempre con la skill, aunque solo la Fase 1 esté implementada al inicio.

Aplica a la skill `oposicion-alegacion-nulidad`.

---

## Estado actual de la skill

| Fase | Estado | Notas |
|------|--------|-------|
| 0 — Skill funcional | Implementada | Orquesta el flujo 408.2: clasificación de motivos, repertorio de apartados, reglas de decisión, módulo de mediación, checklist de cierre. |
| 1 — Auto-instrumentación | **Implementada (2026-06-16)** | Helper canónico `scripts/registrar_uso.py` (store central `data/_skill_logs/`) + `logs/README.md` + `templates/checklist_post_resolucion.md` + paso 6 de cierre en `SKILL.md`. |
| 2 — Corpus de golden cases | Plan | Activar tras 5+ ejecuciones reales con su checklist post-resolución. |
| 3 — Eval automatizado | Plan | Activar tras Fase 2. |
| 4 — LLM-as-judge | Plan | Activar tras Fase 3. |
| 5 — Subagente editor | Plan | Activar tras Fase 4 y volumen suficiente. |

---

## Cómo y cuándo avanzar de fase

Regla de oro del despacho: **Fase 1 siempre; Fases 2-5 solo cuando los datos lo
pidan.** Con poco volumen, la mejora manual rinde más que el bucle automatizado.

**Qué hace cada fase, en una línea:**

- **Fase 1 — Auto-instrumentación**: registra cada escrito preparado y recoge tu feedback tras la resolución. (El termómetro.)
- **Fase 2 — Golden cases**: congela 4-6 escritos reales aprobados como referencia.
- **Fase 3 — Eval automatizado**: detecta regresiones *formales* al cambiar la skill.
- **Fase 4 — LLM-as-judge**: detecta regresiones de *calidad* sustantiva.
- **Fase 5 — Subagente editor**: lee logs + tus observaciones y te **propone parches** a la skill para que apruebes o rechaces. (La automejora propiamente dicha.)

**Cómo avanzar**: cuando creas que toca, en Claude Code di «**avanza la skill
`oposicion-alegacion-nulidad` a la Fase X del plan de evolución**». Claude leerá
este documento y los `logs/`, comprobará el criterio objetivo y construirá la
fase. No improvises las fases a mano.

**Disparadores (no avanzar hasta cumplirlos):**

| Para pasar a… | Necesitas… |
|---|---|
| **Fase 2** (golden cases) | **5+ ejecuciones reales** con su `<ref>_post.jsonl` rellenado |
| Fase 3 (eval) | Corpus de 4+ goldens estable ≥ 1 mes sin cambios |
| Fase 4 (LLM-judge) | Eval verde en 3 corridas consecutivas |
| Fase 5 (subagente editor) | LLM-judge estable + volumen suficiente |

---

## Fase 1 — Auto-instrumentación (implementada 2026-06-16)

**Objetivo**: registrar cada escrito preparado y recoger feedback estructurado
tras la resolución del trámite. Sin esto, las fases siguientes no son viables.

**Componentes**

1. `scripts/registrar_uso.py` (helper canónico del despacho) — escribe una línea
   en el store central `data/_skill_logs/oposicion-alegacion-nulidad/uso.jsonl` al
   cerrar el flujo (paso 6 del `SKILL.md`): referencia, acción, archivos y, dentro
   de `metricas`, nº de motivos por las cuatro vías (A nulidad absoluta · B vicio
   del consentimiento · C incorporación · D contenido/abusividad), motivos
   recolocados a fondo, ordinales incluidos y módulo de mediación.
2. `templates/checklist_post_resolucion.md` — formulario que el letrado rellena al
   notificarse la resolución; respuestas en `logs/<ref>_post.jsonl`.
3. `logs/README.md` — esquema de los logs.
4. (Opcional) tarea programada con la skill `schedule` que dispare la revisión
   post-resolución pasado un plazo desde la previsible resolución del trámite.

**Criterio de activación de la Fase 2**: 5+ ejecuciones reales registradas con su
checklist post-resolución rellenado.

---

## Fase 2 — Corpus de golden cases (plan)

**Objetivo**: 4-6 escritos reales completos como referencia para detectar regresiones.
Variedad mínima: 1 mediación inmobiliaria, 1 con vicio del consentimiento dominante,
1 con control de incorporación (legibilidad), 1 con abusividad/transparencia, 1 con
cuestión previa de cauce que prosperó. Cada golden con su entrada real, el `.docx`
aprobado por el letrado y una nota de por qué se eligió.

**Criterio de activación de la Fase 3**: corpus de 4+ goldens estable ≥ 1 mes.

---

## Fase 3 — Eval automatizado (plan)

**Objetivo**: detectar regresiones formales en cada cambio (estructura de ordinales,
formato Sala 1.ª, presencia de SUPLICO/OTROSÍES, integridad de notas al pie). Integrar
con `skill-creator` si su módulo de eval lo permite; si no, script autónomo.

**Criterio de activación de la Fase 4**: eval verde en 3 corridas consecutivas.

---

## Fase 4 — LLM-as-judge (plan)

**Objetivo**: detectar regresiones de calidad sustantiva. Rúbrica con ejes:
(1) correcta clasificación de motivos por vía de ineficacia; (2) recalificación
nulidad/anulabilidad; (3) anclaje y verificación de cada cita; (4) fidelidad a las
reglas de decisión del `SKILL.md`; (5) calidad del español jurídico y formato Sala 1.ª.

**Criterio de activación de la Fase 5**: ciclo eval + LLM-judge estable 2 meses.

---

## Fase 5 — Subagente editor (plan)

**Objetivo**: cerrar el loop de mejora con propuestas de parche. El subagente lee
`logs/uso.jsonl`, `logs/*_post.jsonl`, los reportes de eval y las notas de los
goldens, y produce parches en diff sobre archivos concretos de la skill. El letrado
aprueba o rechaza; lo aprobado se aplica y se reempaqueta el `.skill`.

**Criterio de retirada**: si tras 6 meses produce más ruido que valor, se desactiva.

---

## Recordatorio de filosofía

Las Fases 2-5 son inversión, no requisito. Si el uso real es bajo, la mejora manual
sigue siendo más eficiente que el loop automatizado. Implementar Fases 2-5 sin datos
reales de la Fase 1 es construir maquinaria sobre vacío. Regla operativa: **Fase 1
siempre, Fases 2-5 solo cuando los datos lo pidan**.
