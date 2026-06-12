# Checklist post-juicio — `[REF]`

Formulario de revisión que se dispara **7 días después de `fecha_juicio`** (ver
`scripts/schedule_post_juicio.js`). Recoge la observación del letrado tras el acto,
sin entrar en el resultado de la sentencia. Es el insumo principal de las fases 2-5
del plan de evolución: sin esta observación post-sala, el corpus golden y el
LLM-as-judge calibrarían sobre vacío.

Las respuestas se guardan como `logs/<ref>_post.jsonl` mediante
`log_uso.logTo("<ref>_post.jsonl", { ... })`.

---

## Campos

1. **Entregables que realmente se usaron en sala** (no solo en preparación).
   ¿Qué documentos se cogieron y consultaron durante el acto?

   > _Respuesta:_

2. **Pregunta no prevista que salió.**
   ¿Qué pregunta (propia o del adversario) surgió y no estaba en el banco?

   > _Respuesta:_

3. **Respuesta de retirada del adversario que falló.**
   De las anticipadas en la caja de anticipación, ¿cuál no funcionó como se esperaba?

   > _Respuesta:_

4. **Bloque que se quedó largo o corto.**
   ¿Qué parte del material sobró o faltó respecto a lo que pidió la dinámica de sala?

   > _Respuesta:_

5. **Valoración del acto (sin entrar en sentencia).**
   ¿Cómo describiría cómo se desarrolló el acto del juicio?

   > _Respuesta:_

---

## Esquema del registro (`logs/<ref>_post.jsonl`)

Una sola línea JSON. `ts` y `skill` los inyecta `log_uso` automáticamente.

```json
{
  "ref": "W-XXXXX",
  "fase": "post",
  "fecha_juicio": "AAAA-MM-DD",
  "entregables_usados": ["…"],
  "pregunta_no_prevista": "…",
  "retirada_fallida": "…",
  "bloque_largo_o_corto": "…",
  "valoracion_acto": "…"
}
```
