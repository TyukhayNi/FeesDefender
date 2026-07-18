# Checklist de autoría de skills — despacho

> **Fuente única de la guía de autoría de skills del despacho.** Vive aquí, en
> `.claude/skills/_shared/`, junto a la plantilla (`_plantilla-skill/`) y los helpers canónicos.
> Las skills se editan en `.claude/skills/` (fuente única de desarrollo desde 2026-06-12).
> Esta guía se trajo desde el repo externo `despacho-skills` el 2026-07-18, al consolidarlo:
> ese repo quedó **deprecado** (sus carpetas de skills ya migraron a FeesDefender) y solo
> conservaba esta guía; ahora vive en la fuente única.

Destilado operativo de las dos guías de buenas prácticas:
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices (Anthropic)
- https://agentskills.io/skill-creation/best-practices

**Regla del despacho:** seguir esta checklist SIEMPRE que se cree, redacte o modifique una skill
(SKILL.md, flujo/proceso, plantillas, scripts). Es la fuente única; no hace falta volver a las URLs.

---

## 1. Frontmatter y triggering (lo más crítico)

- [ ] `name`: minúsculas, números y guiones; ≤ 64 chars; sin «anthropic»/«claude». Forma gerundio o nombre claro.
- [ ] `description`: **tercera persona** (no «Úsala»/«I can»/«You can» → «Se usa cuando…», «Procesa…»). ≤ 1024 chars.
- [ ] La `description` dice **qué hace Y cuándo usarla**, con términos/triggers concretos. Es lo que decide la activación frente a 100+ skills.
- [ ] Evitar descripciones vagas («ayuda con documentos»).
- [ ] **Sin etiquetas tipo XML `<...>` en la `description`** (p. ej. `<fuente>`, `<AAAA-MM-DD>_<NN>`): Cowork/claude.ai **rechaza la importación** («SKILL.md description cannot contain XML tags»). Escribe `AAAA-MM-DD_fuente_NN` o «por fuente/por lote», no ángulos. En el **cuerpo** del `SKILL.md` sí se pueden usar; solo la `description` está vetada. Lo verifica `scripts/validate_skills.py` (aviso) + `tests/test_skill_descriptions_no_xml.py`.

## 2. Concisión — el contexto es un bien común

- [ ] Añadir solo lo que el modelo **no sabría**: convenciones del proyecto, edge cases, qué API/herramienta usar. No explicar qué es un PDF/HTTP/.docx.
- [ ] Por cada párrafo: «¿lo haría mal el agente sin esto?». Si no, fuera.
- [ ] Cuerpo de `SKILL.md` **< 500 líneas / ~5.000 tokens**.

## 3. Progressive disclosure (organización en ficheros)

- [ ] `SKILL.md` = índice/overview que apunta a material detallado.
- [ ] **Referencias a un solo nivel** desde `SKILL.md` (no anidadas: SKILL→A→B). Todo lo enlazado cuelga directo de SKILL.md.
- [ ] Cada enlace dice **CUÁNDO cargarlo** («lee `references/api-errors.md` si la API devuelve != 200»), no un genérico «ver references/».
- [ ] Ficheros de referencia > 100 líneas: incluir índice (tabla de contenidos) al inicio.
- [ ] Organizar por dominio (`reference/finance.md`, `reference/sales.md`), no `doc1.md`/`doc2.md`.

## 4. Calibrar el control a la fragilidad

- [ ] Tareas con varios caminos válidos → **libertad alta** (instrucciones + el *porqué*).
- [ ] Operaciones frágiles / secuencia exacta → **prescriptivo** («ejecuta exactamente este comando; no añadas flags»).
- [ ] **Defaults, no menús**: un default claro + escape («para PDF escaneado, usa X»). No listar 4 librerías equivalentes.
- [ ] **Procedimientos, no respuestas puntuales**: enseñar a abordar la clase de problema, no resolver una instancia concreta.

## 5. Patrones de instrucción (usar los que apliquen)

- [ ] **Gotchas**: bloque de avisos no obvios (correcciones a errores que el agente cometería), en `SKILL.md` para que los lea antes de toparse con la situación. Añadir aquí cada corrección que haya que hacerle.
- [ ] **Plantillas de salida**: dar el formato como template concreto (mejor que describirlo en prosa).
- [ ] **Checklists** copiables para flujos multi-paso con dependencias/validaciones.
- [ ] **Validation loop**: hacer → validar (script o checklist) → corregir → repetir hasta pasar; solo entonces avanzar.
- [ ] **Plan-validate-execute** para operaciones por lote o destructivas: plan en formato estructurado → validar contra fuente de verdad → ejecutar.

## 6. Contenido

- [ ] **Sin información sensible al tiempo** («antes de agosto 2025…»). Usar sección «patrones antiguos» si hace falta histórico.
- [ ] **Terminología consistente** (un solo término por concepto).
- [ ] Ejemplos **concretos**, no abstractos.

## 7. Scripts (si la skill ejecuta código)

- [ ] **Solve, don't punt**: los scripts manejan errores, no delegan el fallo al agente.
- [ ] Sin *voodoo constants*: todo valor justificado/documentado.
- [ ] Dependencias listadas y verificadas como disponibles (no asumir instalado).
- [ ] Dejar claro si el script se **ejecuta** («Run `x.py`») o se **lee como referencia** («See `x.py` for the algorithm»).
- [ ] Validación/verificación para operaciones críticas.

## 8. Anti-patrones

- [ ] **Rutas con `/`**, nunca `\` (Windows-style rompe en Unix).
- [ ] No ofrecer demasiadas opciones (ver §4 defaults).
- [ ] Nombres de fichero descriptivos (`form_validation_rules.md`, no `doc2.md`).
- [ ] Tools MCP siempre con nombre cualificado `Servidor:tool`.

## 9. Evaluación e iteración

- [ ] **Partir de expertise real** (tarea real, artefactos del proyecto), no de genéricos del LLM.
- [ ] **Refine with real execution**: ejecutar la skill en tareas reales, leer las trazas (no solo el output), y realimentar: ¿qué disparó falsos positivos? ¿qué faltó? ¿qué se puede cortar?
- [ ] Idealmente ≥ 3 evaluaciones antes de dar por buena. (En este despacho puede diferirse si el volumen es bajo — dejarlo documentado, no como olvido.)
- [ ] Probar con los modelos que se vayan a usar (Haiku/Sonnet/Opus).

## 10. Antes de cerrar (pre-ship)

- [ ] `description` específica, tercera persona, qué+cuándo.
- [ ] Cuerpo < 500 líneas; detalle en ficheros aparte si hace falta.
- [ ] Referencias a un nivel y con «cuándo cargar».
- [ ] Sin info sensible al tiempo; terminología consistente; ejemplos concretos.
- [ ] Scripts: sin punts, sin voodoo constants, deps verificadas, rutas con `/`.
- [ ] Si aplica al despacho: regenerar artefactos y verificar invariantes (p. ej. `.docx` byte-idénticos), reinstalar copia activa y registrar en CHANGELOG.
