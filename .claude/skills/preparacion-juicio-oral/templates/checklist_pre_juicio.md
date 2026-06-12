# Checklist pre-juicio — `[REF]`

Formulario breve que el agente pide al letrado rellenar **al iniciar la preparación**,
antes de generar conclusiones e interrogatorios. Captura la intención estratégica de
partida para poder contrastarla después con lo ocurrido en sala (checklist post-juicio).

Las respuestas se guardan como `logs/<ref>_pre.jsonl` mediante
`log_uso.logTo("<ref>_pre.jsonl", { ... })`.

---

## Campos

1. **Objetivo táctico del juicio.**
   ¿Qué resultado concreto se persigue en el acto? (1-2 líneas.)

   > _Respuesta:_

2. **Frentes argumentales prioritarios (1-3).**
   Los ejes en los que se va a jugar el asunto, por orden de importancia.

   > 1.
   > 2.
   > 3.

3. **Riesgos identificados de partida.**
   Lo que puede salir mal: sesgo del juez, testigo frágil, documento impugnado, etc.

   > _Respuesta:_

4. **Testigos clave y rol procesal.**
   Quiénes son y con qué rol declaran (`directo` | `cruzado` | `neutro` | `problematico`).

   > - Nombre — rol — por qué es clave
   > - …

---

## Esquema del registro (`logs/<ref>_pre.jsonl`)

Una sola línea JSON. `ts` y `skill` los inyecta `log_uso` automáticamente.

```json
{
  "ref": "W-XXXXX",
  "fase": "pre",
  "objetivo_tactico": "…",
  "frentes_prioritarios": ["…", "…"],
  "riesgos": ["…"],
  "testigos_clave": [
    { "nombre": "…", "rol": "directo", "motivo": "…" }
  ]
}
```
