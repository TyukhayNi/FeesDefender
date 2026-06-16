# `logs/` — telemetría y feedback de la skill (Fase 1)

Recoge la auto-instrumentación de la **Fase 1** de `EVOLUCION.md`, insumo de las
fases 2-5. Sin estos datos, esas fases calibrarían sobre vacío.

**Dónde se escribe.** La telemetría usa el helper canónico del despacho
`scripts/registrar_uso.py`, que escribe en el **store central**
`data/_skill_logs/oposicion-alegacion-nulidad/` (no en esta carpeta `logs/`). Lo
único que viaja con el `.skill` es este `README.md`.

**Privacidad / versionado:** los `.jsonl` contienen referencias de asuntos reales
y **no se versionan ni se empaquetan en el `.skill`** (`data/_skill_logs/` está
git-ignorado). Los `ts` son ISO 8601 en UTC y los inyecta `registrar_uso.py`.

## `uso.jsonl` — registro de ejecuciones

Una línea JSON por escrito preparado, escrita por `registrar_uso.py` al cerrar el
flujo (paso 6 del `SKILL.md`). Esquema unificado del despacho:

| Campo       | Tipo   | Descripción                                                     |
|-------------|--------|-----------------------------------------------------------------|
| `ts`        | string | Timestamp ISO 8601 UTC (automático).                            |
| `skill`     | string | `"oposicion-alegacion-nulidad"` (automático).                   |
| `version`   | string | `version:` del frontmatter del `SKILL.md` (automático).         |
| `ref`       | string | Referencia interna del asunto (W-XXXXX), o `null`.              |
| `accion`    | string | Acción registrada, p. ej. `"oposicion_408"`.                    |
| `archivos`  | array  | Nombres de los `.docx` producidos.                              |
| `metricas`  | object | Métricas del escrito (ver abajo).                               |

Las métricas específicas de esta skill van **dentro de `metricas`**:

| Clave en `metricas` | Tipo     | Descripción                                          |
|---------------------|----------|------------------------------------------------------|
| `via_a`             | nº       | Motivos **vía A** — nulidad absoluta / pleno derecho.|
| `via_b`             | nº       | Motivos **vía B** — vicio del consentimiento.        |
| `via_c`             | nº       | Motivos **vía C** — control de incorporación.        |
| `via_d`             | nº       | Motivos **vía D** — control de contenido / abusividad.|
| `fondo`             | nº       | Motivos recolocados como fondo (fuera del 408.2).    |
| `n_ordinales`       | nº       | Nº de ordinales finalmente incluidos.                |
| `ordinales`         | string[] | Lista de ordinales incluidos.                        |
| `modulo_mediacion`  | bool     | Si se activó el módulo de mediación inmobiliaria.    |

## `<ref>_post.jsonl` — feedback tras la resolución

Respuestas del letrado a `templates/checklist_post_resolucion.md`, una vez
notificada la resolución del trámite. Es el insumo de mayor valor: dice qué
funcionó en sala, no solo qué se redactó.
