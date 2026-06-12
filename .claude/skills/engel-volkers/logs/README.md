# `logs/` — telemetría y feedback de la skill (Fase 1)

Auto-instrumentación definida en la **Fase 1** de `EVOLUCION.md`. Es el insumo de las fases 2-5. Sin estos datos, esas fases calibrarían sobre vacío.

`engel-volkers` es una **skill de contexto** (no genera documentos), así que el registro lo escribe el **propio asistente** al usar la skill en un asunto real, no un script generador. El esquema es deliberadamente ligero.

**Privacidad / versionado:** estos `.jsonl` contienen referencias internas de asuntos reales (W-XXXXXX, sociedad, tipología) y **no se versionan ni se empaquetan**. La carpeta `engel-volkers/` entera está en `.gitignore` del repo. Todos los `ts` son ISO 8601 en UTC.

---

## `uso.jsonl` — registro de uso

Una línea JSON por cada vez que se aplica el contexto de cliente E&V en un asunto real.

| Campo              | Tipo   | Descripción                                                                 |
|--------------------|--------|-----------------------------------------------------------------------------|
| `ts`               | string | Timestamp ISO 8601 UTC.                                                      |
| `skill`            | string | `"engel-volkers"`.                                                           |
| `ref`              | string | Referencia interna del asunto (`W-XXXXXX`), o `null`.                        |
| `sociedad`         | string | `EV_MMC_SPAIN` o `ENGEL_VOLKERS_SPAIN`.                                      |
| `tipologia`        | string | Clave del §3 de la SKILL.md (`BAD_DEBT`, `NEGATIVA_OFERTA`, … `LAU_20`, `OTROS`). |
| `posicion`         | string | `actora` o `defensiva`.                                                      |
| `skill_encadenada` | string | Genérica usada (`escritos-judiciales` / `preparacion-litigio-civil` / `preparacion-juicio-oral`) o `null`. |

Ejemplo:

```jsonl
{"ts":"2026-05-30T08:00:00Z","skill":"engel-volkers","ref":"W-XXXXXX","sociedad":"EV_MMC_SPAIN","tipologia":"BAD_DEBT","posicion":"actora","skill_encadenada":"escritos-judiciales"}
```

---

## `<ref>_post.jsonl` — feedback al cerrar el trabajo

Una línea JSON con la valoración del letrado (formulario `templates/checklist_post.md`), ofrecida al cerrar el trabajo del asunto. Opcional: si el letrado declina, no se escribe.

| Campo                | Tipo     | Descripción                                                        |
|----------------------|----------|-------------------------------------------------------------------|
| `ts`, `skill`        | string   | Automáticos.                                                      |
| `ref`                | string   | Referencia del asunto.                                            |
| `fase`               | string   | `"post"`.                                                         |
| `contexto_correcto`  | bool     | ¿El contexto de cliente fue correcto?                            |
| `faltó`              | string   | Qué faltó o estuvo incompleto (sociedad, tipología, Market Center…); vacío si nada. |
| `activó_cuando_debía`| bool     | ¿La skill se activó cuando tocaba (o se activó cuando no debía)?  |
| `nota`               | string   | Observación libre (opcional).                                     |

Ejemplo:

```jsonl
{"ts":"2026-06-02T17:00:00Z","skill":"engel-volkers","ref":"W-XXXXXX","fase":"post","contexto_correcto":true,"faltó":"","activó_cuando_debía":true,"nota":"Bien; el reparto de sociedad fue inmediato."}
```

---

## Criterio de activación de la Fase 2 (Golden cases)

**5+ usos reales** registrados en `uso.jsonl` con su correspondiente `<ref>_post.jsonl` rellenado. Comprobación en PowerShell:

```powershell
(Get-Content logs\uso.jsonl).Count        # usos totales
(Get-ChildItem logs\*_post.jsonl).Count    # asuntos con feedback
```
