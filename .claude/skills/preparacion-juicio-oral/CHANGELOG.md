# CHANGELOG — `preparacion-juicio-oral`

## 2026-06-16 — Telemetría unificada (v1.0.1)

- `scripts/log_uso.js` deja de ser una implementación JS propia y pasa a ser un **shim** que conserva la API `log`/`logTo` pero delega en el helper canónico `scripts/registrar_uso.py` (fuente única del esquema y del store central `data/_skill_logs/`). Se elimina la doble telemetría JS/Python; las métricas del evento viajan dentro de `metricas`. Sin cambios en los generadores ni en `schedule_post_juicio.js` (sigue usando `log_uso.LOGS_DIR`). `logs/README.md` y `SKILL.md` actualizados. *Evidencia*: handoff de homogeneización de skills (PLAN.md, Ola 1).

## Fase 1 — Auto-instrumentación (2026-05-30)

Implementación de la **Fase 1** del plan de evolución asistida (`EVOLUCION.md`).
Trabajo realizado en Claude Code (no en Cowork), conforme a la regla del despacho.

### Resumen

Solo se **añade** instrumentación y documentación. **No se ha tocado** ninguna de las
12 decisiones metodológicas de `SKILL.md` ni el formato visual de los outputs
(Arial 12, sombreados, citas literales de AP). Verificado: los `.docx` generados tras
la instrumentación son **byte-idénticos** a los del baseline (mismo `word/document.xml`).

### Añadido

- **`scripts/log_uso.js`** — módulo helper de telemetría. `log(entry)` escribe en
  `logs/uso.jsonl`; `logTo(file, entry)` para `logs/<ref>_pre.jsonl` y
  `logs/<ref>_post.jsonl`. Inyecta `ts` (ISO 8601 UTC) y `skill` automáticamente,
  crea `logs/` si no existe y es *best-effort* (si el log falla, avisa por stderr
  pero nunca rompe la generación del `.docx`).
- **Instrumentación de los 4 generadores** (`gen_conclusiones`, `gen_interrogatorio`,
  `gen_cuadro_hechos`, `gen_orden_vista`): cada uno llama a `log_uso.log({...})` tras
  escribir su(s) `.docx`, registrando `ref`, `accion`, `archivos` y métricas
  (hechos no controvertidos/controvertidos, conclusiones, petitum, testigo, rol,
  bloques, preguntas, anticipación, etc.). En `gen_interrogatorio` el log es único y
  se emite tras `Promise.all` de las dos escrituras (letrado + testigo).
- **`templates/checklist_pre_juicio.md`** — 4 campos (objetivo táctico, frentes
  prioritarios, riesgos, testigos clave con rol) → `logs/<ref>_pre.jsonl`.
- **`templates/checklist_post_juicio.md`** — 5 campos (entregables usados en sala,
  pregunta no prevista, retirada fallida, bloque largo/corto, valoración del acto
  sin entrar en sentencia) → `logs/<ref>_post.jsonl`.
- **`scripts/schedule_post_juicio.js`** — calcula `fecha_juicio + 7 días` (offset
  Europe/Madrid con regla DST), emite el descriptor de tarea (`taskId`, `fireAt`,
  `description`, `prompt`) en el formato de la skill `schedule`, lo deja en
  `logs/<ref>_schedule.json` e imprime la instrucción para activarlo manualmente.
- **`logs/README.md`** — esquema documentado de `uso.jsonl`, `<ref>_pre.jsonl`,
  `<ref>_post.jsonl` y `<ref>_schedule.json`.
- **Sección «Telemetría y feedback»** en `SKILL.md` (al final, sin alterar las 12 reglas).

### Modificado

- **`EVOLUCION.md`**: tabla de estado → Fase 1 «Implementada (2026-05-30)»; encabezado
  de la sección Fase 1 actualizado.
- Requires añadidos en `gen_cuadro_hechos.js`, `gen_orden_vista.js` y
  `gen_conclusiones.js` (`path` y/o `log_uso`). Sin cambios en la lógica de formato.

### Bugs latentes

Ninguno. La verificación de baseline pasó limpia: parser XML estricto OK; los anchos
de columna suman exactamente 8787 DXA en todas las tablas (no se rompen); la caja de
anticipación conserva borde (`pBdr`) y sombreado (`F8F8F8`). No fue necesaria ninguna
reparación ni modificación de `format_constants.js`.

### Tooling de repo (no se empaqueta en el `.skill`)

- **`tools/validate_docx.js`** — validador OPC/OOXML ligero usado para la verificación
  de baseline y los tests de regresión. Comprueba que el `.docx` es un OPC legible, que
  contiene las partes obligatorias y que cada parte XML está bien formada.

### Tests de regresión (verdes)

- Los 4 generadores producen `.docx` válidos tras la instrumentación.
- `caso_EJEMPLO.json` → `word/document.xml` **idéntico** al baseline (hash SHA-256).
- `logs/uso.jsonl` se crea con líneas JSON válidas (5/5) y métricas correctas.
- El `.skill` reempaquetado extrae, `npm install`, ejecuta y registra telemetría
  correctamente (prueba de reinstalación).

### No incluido (fuera de alcance)

Fases 2-5 (corpus golden, eval, LLM-as-judge, subagente editor): pendientes, sujetas a
sus criterios de activación. Los datos reales de `logs/` y `test_cases/` no se versionan
ni se empaquetan en el `.skill`.

---

## Baseline (importado del hilo Cowork)

Estado Fase 0: skill funcional que genera CONCLUSIONES y PREGUNTAS por testigo, con
outputs opcionales CUADRO_HECHOS y ORDEN_VISTA. Validador docx pasa.
