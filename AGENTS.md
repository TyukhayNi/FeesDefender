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
  se retiró por cupo agotado — ver `docs/DEAD_ENDS.md`). Contrata así:

  - **Solo lectura, y qué significa.** El repo, los ficheros ignorados por git, `data/CASOS/` y los
    sistemas externos (CRM, Drive) son **entradas de solo lectura durante toda la revisión**. Sí
    puedes **ejecutar código y tests** cuando todas sus escrituras van fuera del repo y no hay
    efectos externos: `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, `--basetemp` fuera del
    árbol. `git status --porcelain --untracked-files=all` antes y después es evidencia adicional,
    **no sustituto** de la prohibición.
  - **Contrasta contra el código real**, no solo contra el diff: un hallazgo que solo se sostiene
    mirando el diff suele ser un falso positivo.
  - **La ruta del informe la fija el encargo**, fuera del repo, derivada de la identidad de la
    revisión. **No sobrescribas informes anteriores:** sus digests son la cadena de custodia.
  - **Devuelve `ruta` y `sha256` canónico** —UTF-8, `LF`, un único salto final— **antes de que se
    adjudique**, por un canal separado del fichero. Sin esa declaración tuya, la prueba de origen se
    reduce a que el autor calcule y escriba los dos lados.
  - **El mandato te llega numerado y ordenado por daño**, con el objeto anclado a un **commit**.
    Contéstalo **punto por punto en una sección propia**, y numera tus hallazgos `H-NN` con
    severidad. Es lo que más subió la calidad medible de las seis rondas del 2026-08-01: sin el
    anclaje no se te puede pedir «reproduce mi medición».
  - **Tú no adjudicas, y conviene saber por qué.** Un hallazgo puede ser correcto y su remedio
    pasarse de rosca: en la primera ronda de aquella serie, un hallazgo acertado exigía suprimir dos
    criterios de aceptación, y uno era el objetivo del encargo. Distinguirlo solo lo puede hacer
    quien tiene la intención del encargo en la mano.
  - **Tu informe se archiva literal**, con su digest, en un acta hermana del objeto revisado. La
    adjudicación va aparte, embebida en el spec o el plan. Contrato completo en
    `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` y resumen en
    `CLAUDE.md` §«Revisión adversarial».

- **Revisor sustituto cuando Codex no puede correr** (regla del 2026-08-01, con Codex sin cupo hasta
  el 2026-08-08). No repetir el error de `agy`: lo caro no fue la lentitud, fue que el paso figurase
  cubierto sin que nadie mirara.

  - **Cuándo.** Solo por **indisponibilidad real** del revisor —sin cupo, caído—, nunca por
    comodidad ni por prisa. Si no hay sustituto, la cobertura se declara ausente y se sigue; **un
    revisor que no corre no refuta**.
  - **Quién.** Una sesión **limpia** de Claude Code: chat nuevo, **sin el contexto de autoría** y sin
    la adjudicación del autor. Se le da el objeto anclado a un commit y el mandato, nada más. El
    resto del contrato de arriba se aplica igual: ruta fijada, `ruta + sha256` de vuelta, informe
    archivado literal.
  - **Qué pierde, y cómo se compensa.** Mismo modelo, **puntos ciegos compartidos**, y sin la tensión
    de interés que hizo que Codex argumentara contra la ampliación de sus propios permisos. Se
    compensa con **subagentes en paralelo, una lente por hallazgo**, y con un mandato que prohíba dar
    nada por bueno sin abrir el fichero y le exija **reproducir las mediciones** en vez de creerlas.
  - **Cómo se registra, sin maquillaje.** `revisor: Claude Code (sesión independiente)` en el acta —
    **nunca «Codex»**— y la adjudicación declara en prosa que la independencia es **más débil**
    porque autor y revisor son el mismo modelo. Si eso no se escribe, el registro miente y el
    mecanismo pierde su único sentido.
  - **Lo que el sustituto NO cubre.** Revisar **el propio contrato de revisión** o cualquier objeto
    donde el sesgo compartido sea precisamente el riesgo: eso espera a Codex. Precedente medido: la
    revisión de Claude sobre el spec del dual workspace —objeto escrito por **Codex**— dio 19
    hallazgos, y la de gobernanza con cinco subagentes refutó 4 de 5. Claude como revisor funciona
    **cuando el autor es otro**.
