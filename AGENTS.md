# FeesDefender — Instrucciones del proyecto (Codex)

> **Este fichero es un PUNTERO, no una copia.** Codex lo carga automáticamente al abrir el
> repo; la fuente única de las instrucciones del proyecto es **`CLAUDE.md`** (raíz del repo).

## Lee `CLAUDE.md` — completo — antes de trabajar

Todo lo que necesitas está ahí y **aplica igual seas Codex, Claude Code o Cowork**: qué es este
proyecto, el idioma de las respuestas, la revisión adversarial obligatoria, las reglas
que nunca se rompen (arquitectura de 3 capas, `data/CASOS/` fuera de git, `main` protegida →
rama + PR, `core/anon/` congelado, higiene de datos y secretos), el entorno de ejecución en
Windows/PowerShell, los gotchas críticos, el flujo de trabajo con `STATUS.md` y `PLAN.md`, los
tests, y las convenciones de escritos del despacho.

**No dupliques su contenido aquí.** Este fichero existió como copia de `CLAUDE.md` con
«Claude» sustituido por «Codex», y esa sustitución mecánica fabricó rutas que no existen:
mandaba editar las skills en `.Codex/skills/`, un directorio inexistente (`.codex/` solo
contiene `config.toml`). Mantener dos copias del 93 % del mismo texto garantiza que divergan, y
una instrucción divergente es peor que ninguna.

## Lo único específico de Codex

- **Fichero de entrada:** Codex lee `AGENTS.md`; Claude Code y Cowork leen `CLAUDE.md`. De ahí
  que exista este puntero.
- **Config local:** `.codex/config.toml` (versionado) fija `PYTHONIOENCODING`/`PYTHONUTF8`,
  porque en Windows la salida de `subprocess` se decodifica con cp1252 y trunca las tildes — el
  mismo gotcha de encoding que documenta `CLAUDE.md`.
- **Skills:** se editan **siempre** en `.claude/skills/` (fuente única de desarrollo, con
  helpers en `.claude/skills/_shared/`). El árbol `.agents/skills/` es un espejo local **no
  versionado** que ya ha divergido de la fuente; no lo edites ni te fíes de él. Ver `MEJORAS #97`.
- **Codex es el revisor adversarial del proyecto** (desde 2026-08-01; sustituye a Gemini/`agy`, que
  se retiró por cupo agotado — ver `docs/DEAD_ENDS.md`). Cuando te llamen para eso: trabajas en
  **solo lectura**, no escribes en el repo, y dejas los hallazgos en un fichero **fuera** de él
  (`%TEMP%\...`). Contrasta cada hallazgo **contra el código real**, no solo contra el diff: un
  hallazgo que solo se sostiene mirando el diff suele ser un falso positivo. **Claude adjudica** y
  registra el resultado en el spec o el plan; tu informe se recibe sin modificar. Detalle del
  contrato en `CLAUDE.md` §«Revisión adversarial».
