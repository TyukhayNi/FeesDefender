# EVOLUCION.md — Plan de evolución asistida en cinco fases

Documento estándar de toda skill del despacho. Define las cinco fases del plan de evolución y el criterio objetivo para activar cada una. Acompaña al `SKILL.md` y se entrega siempre con la skill, aunque solo la Fase 1 esté implementada al inicio.

Aplica a la skill `preparacion-juicio-oral` y, por extensión, a todas las skills nuevas del despacho.

---

## Estado actual de la skill `preparacion-juicio-oral`

| Fase | Estado | Notas |
|------|--------|-------|
| 0 — Skill funcional | Implementada | Genera CONCLUSIONES y PREGUNTAS por testigo. Validador docx pasa. |
| 1 — Auto-instrumentación | **Implementada (2026-05-30)** | Construida en Claude Code. `log_uso.js` + 4 generadores instrumentados + checklists pre/post + `schedule_post_juicio.js` + `logs/README.md`. |
| 2 — Corpus de golden cases | Plan | Activar tras 5+ ejecuciones reales. |
| 3 — Eval automatizado | Plan | Activar tras Fase 2. |
| 4 — LLM-as-judge | Plan | Activar tras Fase 3. |
| 5 — Subagente editor | Plan | Activar tras Fase 4 y 20+ ejecuciones. |

---

## ⏭️ Cómo y cuándo avanzar de fase (recordatorio)

No hace falta recordar el proceso de memoria: esto lo resume. Regla de oro del
despacho: **Fase 1 siempre; Fases 2-5 solo cuando los datos lo pidan.** Con poco
volumen (1-2 juicios al año) la mejora manual rinde más que el bucle automatizado.

**Qué hace cada fase, en una línea:**

- **Fase 1 — Auto-instrumentación:** registra el uso y recoge tu feedback pre/post juicio. (El termómetro.)
- **Fase 2 — Golden cases:** congela 4-6 casos reales aprobados como referencia.
- **Fase 3 — Eval automatizado:** detecta regresiones *formales* al cambiar la skill.
- **Fase 4 — LLM-as-judge:** detecta regresiones de *calidad* sustantiva.
- **Fase 5 — Subagente editor:** lee logs + tus observaciones y te **propone parches** a la skill para que apruebes o rechaces. (La automejora propiamente dicha.)

**¿Dónde estoy ahora?** Cuenta las ejecuciones reales registradas:

- Ejecuciones totales = nº de líneas en `logs/uso.jsonl`.
- Juicios con feedback post-sala = nº de archivos `logs/*_post.jsonl`.
- En PowerShell: `(Get-Content logs\uso.jsonl).Count` y `(Get-ChildItem logs\*_post.jsonl).Count`.

**Disparadores (no avanzar hasta cumplirlos):**

| Para pasar a… | Necesitas… |
|---|---|
| **Fase 2** (golden cases) | **5+ ejecuciones reales** con su `<ref>_post.jsonl` rellenado |
| Fase 3 (eval) | Corpus de 4+ goldens estable ≥ 1 mes sin cambios |
| Fase 4 (LLM-judge) | Eval verde en 3 corridas consecutivas |
| Fase 5 (subagente editor) | LLM-judge estable 2 meses + 20+ ejecuciones |

**Cuándo y cómo dar el paso:** cuando creas que toca, abre Claude Code y di, literalmente,
«**avanza la skill `<nombre>` a la Fase X del plan de evolución**». Claude leerá este
documento y los `logs/`, comprobará el criterio objetivo y construirá la fase. **No
improvises las fases a mano** — su alcance está descrito abajo. Si el criterio aún no
se cumple, Claude te lo dirá y no avanzará.

---

## Fase 1 — Auto-instrumentación (implementada 2026-05-30)

**Objetivo**: registrar cada ejecución de la skill y recoger feedback estructurado pre/post juicio. Sin esto, las fases siguientes no son viables.

**Componentes a construir**

1. `scripts/log_uso.js` — módulo helper que cada generador invoca al finalizar. Escribe una línea estructurada en `logs/uso.jsonl`:

```jsonl
{"ts":"2026-05-30T08:00:00Z","skill":"preparacion-juicio-oral","ref":"W-EJEMPLO","accion":"gen_conclusiones","archivos":["CONCLUSIONES_W-EJEMPLO.docx"],"hechos_no_ctrv":6,"hechos_ctrv":1,"testigos":5}
```

Instrumentar `gen_conclusiones.js`, `gen_interrogatorio.js`, `gen_cuadro_hechos.js`, `gen_orden_vista.js` para que llamen a `log_uso.log(...)` antes de salir.

2. `templates/checklist_pre_juicio.md` — formulario breve que el agente le pide al letrado rellenar al iniciar la preparación:

- Objetivo táctico del juicio.
- Frentes argumentales prioritarios (1-3).
- Riesgos identificados de partida.
- Testigos clave y rol procesal.

Las respuestas se guardan como `logs/<ref>_pre.jsonl`.

3. `templates/checklist_post_juicio.md` — formulario de revisión post-juicio. Se dispara 7 días después de `fecha_juicio` mediante `schedule`:

- ¿Cuáles entregables se usaron en sala (no en preparación)?
- ¿Qué pregunta del banco salió y no estaba prevista?
- ¿Qué respuesta de retirada del adversario falló?
- ¿Qué bloque se quedó largo o corto?
- ¿Cómo describiría el resultado del acto (sin entrar en sentencia)?

Respuestas en `logs/<ref>_post.jsonl`.

4. Tarea programada con la skill `schedule` que dispare la conversación de revisión post-juicio.

5. Documentación del esquema en `logs/README.md`.

**Criterio de activación de la Fase 2**: 5+ ejecuciones reales registradas con su correspondiente checklist post-juicio rellenado.

---

## Fase 2 — Corpus de golden cases (plan)

**Objetivo**: tener 4-6 casos reales completos como referencia para detectar regresiones.

**Componentes**

- `golden/<caso_id>/caso.json` con la entrada real.
- `golden/<caso_id>/expected/` con los `.docx` aprobados manualmente por el letrado.
- `golden/<caso_id>/notas.md` con el contexto del caso y por qué se eligió como golden.

Variedad mínima: 1 corretaje inmobiliario, 1 arrendaticio, 1 responsabilidad contractual, 1 con modo `partes` (juez no fijó controversia), 1 con testigo problemático.

**Criterio de activación de la Fase 3**: corpus de 4+ goldens estable durante al menos 1 mes sin cambios.

---

## Fase 3 — Eval automatizado (plan)

**Objetivo**: detectar regresiones formales en cada cambio de la skill.

**Componentes**

- `eval/run_eval.js` que regenera todos los goldens y compara `.docx` salida vs `expected`.
- Comparación a nivel de XML (después de unpack) para detectar diferencias estructurales (anchos de columna, sombreados, número de párrafos, validador).
- Reporte en `eval/reports/<fecha>.md` con diff resumido.

Integrar con `skill-creator` si su módulo de eval lo permite directamente; si no, script autónomo.

**Criterio de activación de la Fase 4**: eval estable y verde en al menos 3 corridas consecutivas tras cambios de la skill.

---

## Fase 4 — LLM-as-judge (plan)

**Objetivo**: detectar regresiones de calidad sustantiva (no solo formal).

**Componentes**

- Rúbrica explícita en `eval/rubrica.md` con cinco ejes:
  1. Claridad estructural del documento.
  2. Anclaje documental en cada hecho.
  3. Anticipación a repreguntas en interrogatorios.
  4. Fidelidad a las decisiones metodológicas codificadas en `SKILL.md`.
  5. Calidad del español jurídico.
- `eval/llm_judge.js` que invoca a un modelo secundario (sugerido: Haiku) para puntuar 0-5 cada eje sobre cada golden contra el output actual.
- Umbral de aceptación configurable por eje. Cualquier puntuación que baje > 1 punto respecto al golden se marca como regresión.

**Criterio de activación de la Fase 5**: el ciclo eval + LLM-judge funciona automáticamente en cada cambio durante 2 meses sin falsos positivos relevantes.

---

## Fase 5 — Subagente editor (plan)

**Objetivo**: cerrar el loop de mejora con propuestas concretas de parches.

**Componentes**

- Subagente con rol "editor de skills" definido en `subagents/skill_editor.md` (o mecanismo equivalente que ofrezca Claude Code en ese momento).
- El subagente lee:
  - `logs/uso.jsonl` (uso real acumulado).
  - `logs/*_post.jsonl` (observaciones del letrado tras juicios).
  - `eval/reports/*.md` (regresiones detectadas).
  - `golden/*/notas.md` (por qué cada golden es golden).
- Produce propuestas de parche en formato diff sobre archivos concretos de la skill.
- El letrado revisa, aprueba o rechaza. Lo aprobado se aplica y se reempaqueta el `.skill`.

**Criterio de retirada**: si tras 6 meses el subagente produce más ruido que valor, se desactiva.

---

## Cómo empezar (cuando estés en Claude Code)

1. Clona o inicia el repo `despacho-skills/`.
2. Importa el `.skill` actual (descomprime en `despacho-skills/preparacion-juicio-oral/`).
3. Copia este `EVOLUCION.md` como `despacho-skills/preparacion-juicio-oral/EVOLUCION.md`.
4. Aborda **solo la Fase 1**. Implementación sugerida:
   - Crear `scripts/log_uso.js` (module helper).
   - Modificar los cuatro `gen_*.js` para llamar a `log_uso.log({...})` antes de salir.
   - Crear las dos plantillas de checklist.
   - Crear `scripts/schedule_post_juicio.js` que use la skill `schedule` para disparar el formulario 7 días después.
   - Actualizar `SKILL.md` con la sección «Telemetría y feedback» que documente los logs.
   - Reempaquetar `.skill` y reinstalar.
5. Marcar Fase 1 como «implementada» en la tabla de estado al inicio de este documento.
6. No tocar Fases 2-5 hasta cumplir los criterios de activación.

---

## Recordatorio de filosofía

Las Fases 2-5 son inversión, no requisito. Si el uso real de la skill es bajo (1-2 juicios al año), la mejora manual sigue siendo más eficiente que el loop automatizado. Solo si el volumen lo justifica conviene avanzar fase a fase.

Implementar Fases 2-5 sin haber acumulado datos reales con la Fase 1 es construir maquinaria sobre vacío: el corpus golden sería sintético, el eval mediría contra cosas inventadas, el LLM-as-judge calibraría contra opiniones no validadas en sala, y el subagente editor propondría parches especulativos.

La regla operativa: **Fase 1 siempre, Fases 2-5 solo cuando los datos lo pidan**.
