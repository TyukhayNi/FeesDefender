# `logs/` — telemetría y feedback de la skill (Fase 1)

Este directorio recoge la auto-instrumentación definida en la **Fase 1** de
`EVOLUCION.md`. Es el insumo de las fases 2-5 (corpus golden, eval, LLM-as-judge,
subagente editor). Sin estos datos, esas fases calibrarían sobre vacío.

**Privacidad / versionado:** los `.jsonl` y los `.json` de este directorio contienen
referencias internas de asuntos reales y **no se versionan ni se empaquetan en el
`.skill`** (ver `.gitignore`). Lo único que viaja con la skill es este `README.md`,
que documenta el esquema. Todos los timestamps `ts` son ISO 8601 en UTC y los inyecta
`scripts/log_uso.js` automáticamente, igual que el campo `skill`.

---

## `uso.jsonl` — registro de ejecuciones

Una línea JSON por cada generación de `.docx`. La escribe cada `gen_*.js` al
finalizar, vía `log_uso.log({...})`. Campos comunes:

| Campo     | Tipo     | Descripción                                            |
|-----------|----------|--------------------------------------------------------|
| `ts`      | string   | Timestamp ISO 8601 UTC (automático).                   |
| `skill`   | string   | `"preparacion-juicio-oral"` (automático).              |
| `ref`     | string   | Referencia interna del asunto (W-XXXXX), o `null`.     |
| `accion`  | string   | Generador que emitió la línea (ver abajo).             |
| `archivos`| string[] | Nombres de los `.docx` producidos en esa ejecución.    |

Campos específicos por `accion`:

- **`gen_conclusiones`**: `hechos_no_ctrv` (nº), `hechos_ctrv` (nº), `conclusiones` (nº), `petitum` (nº).
- **`gen_interrogatorio`**: `testigo` (nombre), `rol` (`directo`|`cruzado`|`neutro`|`problematico`), `version_testigo` (bool), `bloques` (nº), `preguntas` (nº), `anticipacion` (nº de ítems).
- **`gen_cuadro_hechos`**: `filas` (nº), `hechos_ctrv` (nº), `hechos_no_ctrv` (nº).
- **`gen_orden_vista`**: `testigos` (nº), `documentos_mano` (nº), `protestas` (nº), `riesgos` (nº), `recordatorios` (nº).
- **`schedule_post_juicio`**: `fecha_juicio`, `fire_at` (ISO con offset), `task_id`. La emite `scripts/schedule_post_juicio.js` al programar la revisión.

Ejemplo:

```jsonl
{"ts":"2026-05-30T08:00:00.000Z","skill":"preparacion-juicio-oral","ref":"W-EJEMPLO","accion":"gen_conclusiones","archivos":["CONCLUSIONES_EJEMPLO.docx"],"hechos_no_ctrv":6,"hechos_ctrv":1,"conclusiones":2,"petitum":3}
{"ts":"2026-05-30T08:00:01.000Z","skill":"preparacion-juicio-oral","ref":"W-EJEMPLO","accion":"gen_interrogatorio","archivos":["PREGUNTAS_Testigo_letrado.docx","PREGUNTAS_Testigo_testigo.docx"],"testigo":"Sr. Testigo","rol":"directo","version_testigo":true,"bloques":4,"preguntas":18,"anticipacion":2}
```

---

## `<ref>_pre.jsonl` — checklist pre-juicio

Una línea JSON con la intención estratégica de partida (formulario
`templates/checklist_pre_juicio.md`). La escribe el agente vía
`log_uso.logTo("<ref>_pre.jsonl", {...})` al iniciar la preparación.

| Campo                  | Tipo       | Descripción                                         |
|------------------------|------------|-----------------------------------------------------|
| `ts`, `skill`          | string     | Automáticos.                                        |
| `ref`                  | string     | Referencia del asunto.                              |
| `fase`                 | string     | `"pre"`.                                            |
| `objetivo_tactico`     | string     | Resultado concreto perseguido.                      |
| `frentes_prioritarios` | string[]   | 1-3 ejes argumentales por orden.                    |
| `riesgos`              | string[]   | Riesgos identificados de partida.                   |
| `testigos_clave`       | object[]   | `{ nombre, rol, motivo }` por testigo.              |

---

## `<ref>_post.jsonl` — checklist post-juicio

Una línea JSON con la observación tras el acto (formulario
`templates/checklist_post_juicio.md`), disparada ~7 días después de `fecha_juicio`
por `scripts/schedule_post_juicio.js`. La escribe el agente vía
`log_uso.logTo("<ref>_post.jsonl", {...})`.

| Campo                   | Tipo     | Descripción                                          |
|-------------------------|----------|------------------------------------------------------|
| `ts`, `skill`           | string   | Automáticos.                                         |
| `ref`                   | string   | Referencia del asunto.                               |
| `fase`                  | string   | `"post"`.                                            |
| `fecha_juicio`          | string   | Fecha del acto (AAAA-MM-DD).                         |
| `entregables_usados`    | string[] | Entregables realmente usados en sala.               |
| `pregunta_no_prevista`  | string   | Pregunta que salió y no estaba prevista.             |
| `retirada_fallida`      | string   | Respuesta de retirada del adversario que falló.      |
| `bloque_largo_o_corto`  | string   | Bloque que sobró o faltó.                            |
| `valoracion_acto`       | string   | Valoración del acto sin entrar en sentencia.         |

---

## `<ref>_schedule.json` — descriptor de tarea programada

No es un `.jsonl`: es un único objeto JSON con el descriptor de la revisión
post-juicio que produce `scripts/schedule_post_juicio.js`, listo para entregar a la
skill `schedule`. Campos: `taskId`, `fireAt` (ISO 8601 con offset Europe/Madrid),
`description`, `prompt` (autocontenido).

---

## Criterio de activación de la Fase 2

5+ ejecuciones reales registradas en `uso.jsonl` con su correspondiente
`<ref>_post.jsonl` rellenado.
