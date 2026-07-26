# Revisión adversarial — Diagnóstico de gobernanza documental (INDICE/PLAN/specs/plans)

> Fecha: 2026-07-26. Revisor: Claude Code (orquestador + 5 subagentes en paralelo, uno por hallazgo).
> Objeto: `docs/superpowers/handoffs/handoff-2026-07-26-gobernanza-indice-adversarial.md`.
> Estado: **pendiente de adjudicación por Nikolai**.
> Método: refutar primero. Ninguna afirmación sin ancla a `fichero:línea`, hash de commit o PR.

## Veredicto

**No implementar la remediación propuesta.** El diagnóstico de origen tiene una **tasa de acierto muy
baja**: de los 5 hallazgos, **4 quedan REFUTADOS** y 1 CONFIRMADO CON MATIZ con dos de sus tres anclas
falsas. Su causa raíz es metodológica: mide el repo contra un contrato de gobernanza que nunca se
escribió (que `INDICE.md` indexe cada spec/plan) y busca la trazabilidad en el artefacto equivocado
(el *stem* del fichero de plan, cuando la unidad real es **etiqueta `[XXX]` + nº de PR + enlace al
spec**).

El test propuesto no es un guard de completitud: es **una redefinición de qué es `INDICE.md`**, con
retrofit manual de ~98 filas, y colisionaría de inmediato con el vocabulario de `estado:` ya vigente.

Pero la revisión **no sale de vacío**. Al intentar refutar, aparecieron **seis defectos reales** que el
diagnóstico no vio, dos de ellos **P1 en código** (uno destructivo). El hueco de gobernanza real existe
y está en el **ledger `PLAN.md ## ✅ Cerrados`**, no en `INDICE.md`.

| | Hallazgo | Veredicto | Severidad |
|---|---|---|---|
| H1 | `INDICE.md` no indexa nada tras 19-07 | **REFUTADO** | P2 |
| H2 | `crm-atlas` ausente de PLAN/bitácora | **CONFIRMADO CON MATIZ** | P2 |
| H3 | 24 de 54 plans huérfanos | **REFUTADO** (88% falsos positivos) | P2 |
| H4 | Frontmatter inconsistente | **REFUTADO** como defecto | P2 |
| H5 | `MEJORAS_FUTURAS.md` sin cableado | **REFUTADO** (falso positivo conceptual) | P2 |

---

## Hallazgos del diagnóstico original

### H1 — `INDICE.md` no indexa nada posterior al 2026-07-19 → **REFUTADO** (P2)

`docs/INDICE.md` **nunca tuvo tabla de specs/plans fechados**. Sus tres únicas tablas son docs de raíz
de `docs/` ([INDICE.md:28](../../INDICE.md)), planes **legacy** `PLAN_*.md` ([:51](../../INDICE.md)) y
handoffs ([:71](../../INDICE.md)). El deber de indexado que la gobernanza le asigna alcanza solo a los
legacy: `GOBERNANZA_FUENTES_VERDAD.md:50` — *"los `docs/PLAN_*.md` legacy se quedan donde están,
etiquetados con `estado:` e indexados en `docs/INDICE.md`"*.

Cobertura histórica medida, que desmonta la narrativa de "dejó de mantenerse":

| Corpus | Total | En INDICE.md |
|---|---|---|
| specs fechados | 44 | **1** (y por nota de supersesión, [INDICE.md:57](../../INDICE.md)) |
| plans fechados | 40 | **0** |
| `PLAN_*.md` legacy | 14 | **14 (100%)** |
| handoffs | 15 | **15 (100%)** |
| fechados **anteriores** al 19-07 | 74 | **1** |

Nunca fue 84 y bajó a 0: **siempre fue ~1**. Y el fichero **sí se tocó después del 19-07**: `5c6ec9a`
(2026-07-20) le añadió la fila de `FLUJO_GIT.md` — exactamente lo que su contrato cubre.

Además, el diagnóstico se equivoca al decir que solo el plan de preclasificación está en `PLAN.md`:
**cuatro** de los ocho lo están, y los ocho salvo los dos de `crm-atlas` están trazados en
`docs/bitacora/2026.md`.

**Escenario concreto:** no lo hay. Nikolai abre sesión leyendo `STATUS.md` + `PLAN.md`, y `CLAUDE.md:205`
describe INDICE.md como *"Índice de `docs/` + ciclo de vida"* — literalmente índice de `docs/`. Añadirle
84 filas crearía un cuarto sitio donde restatar estado: el drift que `GOBERNANZA_FUENTES_VERDAD.md:142-144`
combate.

**Cambio exigido:** ninguno por H1.

---

### H2 — `crm-atlas` ausente de `PLAN.md` y bitácora → **CONFIRMADO CON MATIZ** (P2)

El hecho central es **cierto y verificado por mí de forma independiente**: 0 ocurrencias de `atlas`
(case-insensitive) en `PLAN.md`, `STATUS.md`, `docs/bitacora/2026.md` e `INDICE.md`. No es artefacto de
cobertura temporal: el ledger tiene entradas del 21-07 y 23-07, posteriores al merge del atlas
(2026-07-20T14:26:57Z).

Ancla que el diagnóstico no vio, y que es la más elocuente — `docs/bitacora/2026.md:24`:

> *"Higiene de worktrees: … la de esta sesión (`sudespacho-crm-endpoints-13f5ab`) se poda en este cierre."*

Ese es el `headRefName` del PR #104. **La rama del atlas aparece en la bitácora una sola vez: como
escombro a podar.** El entregable nunca se narró; solo su basura.

Pero **dos de las tres anclas de H2 son falsas**:

1. `87ff113` **no** está citado en `docs/CRM_SUDESPACHO_ATLAS.md`, sino en
   `specs/2026-07-20-crm-atlas-descubrimiento-design.md:27` y `:274`.
2. **Fase B no está pendiente: está construida y mergeada.** `gh pr view 104` → MERGED, mergeCommit
   `b2d624c`, título *"Fase A + Fase B"*. `git show --stat b2d624c` incluye `core/crm_atlas.py` (860
   líneas) y `tests/test_crm_atlas.py` (694). La inferencia implícita de H2 está invertida.

Sobre `87ff113` (instrucción 3 del encargo): **existe** (`87ff11309f1e…`, 2026-07-20 14:05:45) pero
**NO está en `main`** — `git merge-base --is-ancestor 87ff113 main` es falso y `git branch --contains`
no devuelve nada. Es un commit **colgante pre-squash**. El trabajo entró como `b2d624c`.

**Escenario concreto:** `PLAN.md:347` mantiene vivo `[SIGUIENTE-MCP-SUDESPACHO]`, el consumidor natural
del atlas, y su `PLAN.md:358` remite a `INTEGRACION_SUDESPACHO.md` sin saber que el atlas existe. Quien
abra esa sesión redescubrirá endpoints a mano — lo que `CLAUDE.md:212` prohíbe expresamente — repitiendo
~6.400 líneas ya pagadas. Y si llega al atlas, leerá que Fase B está pendiente y **la reconstruirá**.

**Cambio exigido:**
1. `PLAN.md ## ✅ Cerrados`: fila `[CRM-ATLAS]` — Fase A+B+Grupo 3.2, PR #104 (`b2d624c`), con enlace al spec.
2. `PLAN.md:358`: añadir `docs/CRM_SUDESPACHO_ATLAS.md` como consulta previa del F1 del MCP sudespacho.
3. `specs/2026-07-20-crm-atlas-descubrimiento-design.md:27,274`: sustituir `87ff113` por `b2d624c`, o anotar que es pre-squash.
4. **No** retroinsertar un cierre en la bitácora: es log cronológico, no ledger.

---

### H3 — 24 de 54 plans huérfanos → **REFUTADO** (P2). Tasa de falsos positivos: **88%**

El caso de calibración que el propio handoff señaló **es en efecto un falso positivo**, y he verificado
el ancla yo mismo. Los cuatro `apertura-b1-b5*` están trazados, pero no donde el grep miró — no en la
entrada `[abrir-caso]` sino en el ledger, [PLAN.md:1538](../../../PLAN.md):

> `✅ **[SIGUIENTE-APERTURA-EXPEDIENTE]** Builds de apertura B1-B5 (…) — PR #69/#71/#72/#74 · [spec](…2026-07-18-apertura-expediente-b1-b5-design.md)`

El ledger traza por **etiqueta + PRs + spec**. El stem del *plan* no aparece nunca porque el diseño de
gobernanza no lo usa. Establecido eso, el mismo escepticismo derriba el resto:

- **De los 25 stems listados** (el hallazgo dice "24" pero lista 25): **22 REFUTADOS**, **3
  CONFIRMADO-BENIGNO**, **0 CONFIRMADO-GRAVE**.
- Los tres benignos: `dedup-guard-robusto`, `adjuntos-contenido-fase2`, `crm-atlas-fase-b`. Los tres
  tienen el código en `main` con tests; lo que falta es la fila de ledger.
- La ironía de `2026-07-18-gobernanza-planificacion` **no se materializa**: es de los mejor trazados
  (`bitacora:42`, PRs #75-#78, y su ruta está incluso hardcodeada en
  [test_docs_gobernanza.py:40](../../../tests/test_docs_gobernanza.py)).

Cuatro defectos de método, en orden de gravedad:

1. **Mide el artefacto equivocado** — stem de plan, cuando la unidad es etiqueta + PR.
2. **Universo demasiado estrecho** — solo `PLAN.md` + `INDICE.md`. Las citas literales viven sobre todo
   en `docs/bitacora/2026.md`, y también en `MEJORAS_FUTURAS.md`, `DEAD_ENDS.md`, handoffs, `tests/` y
   docstrings de `core/`. Bien medido: **42 de 54** planes tienen cita literal en algún sitio del repo.
3. **`INDICE.md` es un control inaplicable** para plans fechados (error de categoría). Los legacy son
   14, no 9.
4. **Aritmética incoherente** — 54−19=35, 35−9=26, se afirma 24, la lista tiene 25.

**Escenario concreto** (estrecho, y solo en `dedup-guard-robusto`): Nikolai vuelve a chocar con un
expediente duplicado en el CRM. Nada en PLAN/bitácora/MEJORAS dice que eso ya se atacó en junio con una
decisión de diseño concreta — anclar identidad en el **W-code**, no en la etiqueta. La sesión rediseña
desde cero y añade un tercer camino de matching junto a `normalize_referencia` / `wcode_match` /
`_match_in_results` en `core/sudespacho_relations.py`, justo donde un fallo crea un expediente duplicado.
**No hay pérdida de trabajo ni de prueba en ningún caso**: todo el código está en `main` con tests.

**Cambio exigido:** retirar H3 tal como está redactado. Queda el residuo del §"Defectos reales" (D1, D2).

---

### H4 — Frontmatter inconsistente → **REFUTADO como defecto** (P2)

El hecho material es cierto; la premisa implícita —que rompe algo— es falsa. **No existe ningún
consumidor programático del frontmatter de `docs/superpowers/`**:

- [test_docs_gobernanza.py:13](../../../tests/test_docs_gobernanza.py) — `(ROOT / "docs").glob("*.md")`.
  Glob **no recursivo**: los 44 specs, 54 plans y 15 handoffs están fuera de su alcance por diseño.
- `scripts/session_close.py` — cero ocurrencias de `handoff|estado:|consumido_por|superpowers`.
- `.pre-commit-config.yaml` y `.github/workflows/leak-scan.yml` — no miran frontmatter.
- Todo el `yaml.safe_load` del repo opera sobre artefactos de **expediente**, nunca sobre `docs/`.

Censo real (corrige a H4, que afirma que los plans "no tienen frontmatter en absoluto"):

| Carpeta | Total | YAML | Prosa negrita | Ninguno |
|---|---|---|---|---|
| `specs/` | 44 | 14 | 11 | 19 |
| `plans/` | 54 | **14** | 2 | 38 |
| `handoffs/` | 15 | 15 | 0 | 0 |
| `specs/cronologia-handoffs/` | 8 | 0 | 0 | **8** |

Y esos 14 de `plans/` **son exactamente los 14 `PLAN_*.md` legacy**, ni uno más. El YAML existe justo
donde una norma lo exigió. No hay deriva desde un estándar: hay dos poblaciones con reglas distintas.

**Conclusión:** exigir YAML a los 44 specs y 40 plans fechados **no corrige un incumplimiento — inventa
una regla nueva**. Los specs más recientes siguen el patrón sin YAML, o sea que ese *es* el estándar de
facto vigente.

**Escenario concreto:** el único daño real es el **inverso**, y lo dispara "arreglar" H4 — ver D3 abajo.

**Cambio exigido:** ninguno. A lo sumo, acotar por escrito el alcance de la frase ambigua
`INDICE.md:23` ("frontmatter de cada doc") a las tres poblaciones que el índice cubre. Una frase, no
una migración. Regla correcta: **el frontmatter se introduce el día que se construya el consumidor, no
antes.**

---

### H5 — `MEJORAS_FUTURAS.md` sin cableado → **REFUTADO** (falso positivo conceptual, P2)

La regla, literal — `CLAUDE.md:50-55`:

> *"**Regla de promoción backlog → cola**: una entrada de `docs/MEJORAS_FUTURAS.md` se promueve a
> `PLAN.md` cuando tiene **disparador concreto**: … o decisión explícita de Nikolai."*

Es **estrictamente unidireccional y condicional**. Su antecedente es *"una entrada de
MEJORAS_FUTURAS.md"*. No hay ninguna cláusula que exija que todo trabajo **nazca** en el backlog. H5
reclama un flujo PLAN→MEJORAS que la norma nunca estableció.

Además, su premisa fáctica también falla:

- El flujo inverso está vivo y es reciente: `MEJORAS_FUTURAS.md:2994` (#81, PR #117), `:3022` (#82, PR
  #120), `:3045` (#83, PR #123), `:3073` (#84, PR #125).
- Los specs de sala-lectura de julio **sí citan el backlog**:
  `specs/2026-07-23-emails-atomizados-sala-lectura-design.md:10` declara base `MEJORAS #75/#76`.
- `crm-atlas` sí declara *"petición de Nikolai"* (`…crm-atlas-descubrimiento-design.md:6`) — pero
  *"decisión explícita de Nikolai"* es literalmente uno de los tres disparadores admitidos.

Dirección MEJORAS→PLAN: **cuadra al 100%** (las 6 entradas `[PROMOVIDO → PLAN.md]` tienen su entrada en
PLAN.md). Dirección PLAN→MEJORAS: 3 contramarcas ausentes (#26 en `:855`, #58 en `:2405`, #74 en `:2751`).

**Cambio exigido:** ninguno por H5. Cerrarlo como falso positivo conceptual. Exigir que `crm-atlas`
naciera en el backlog obligaría a escribir una entrada ficticia y marcarla promovida en el mismo commit
— justo lo que `CLAUDE.md:54-55` prohíbe.

---

## Defectos reales encontrados al refutar (lo que el diagnóstico no vio)

### D1 — P1 · El atlas ordena el comando que lo mutila *(destructivo)*

`docs/CRM_SUDESPACHO_ATLAS.md:4`, hardcodeado en [core/crm_atlas.py:371](../../../core/crm_atlas.py):

> *"Regenerar: `python -m scripts.crm_atlas discover --phase a`."*

Pero en `scripts/crm_atlas.py` la escritura es **incondicional**, fuera del `if phase in {"b","all"}`
— el propio comentario lo llama *"Escritura (único camino, tras el gate)"*:

```python
_write_text(atlas_json, …)
_write_text(atlas_md, render_markdown(atlas))
_write_text(digest_md, render_digest(atlas))
```

Con `--phase a`, `build_atlas_phase_a` reinicia `meta["phase_b"]` y no produce clave `elements`.
**Ejecutar el comando impreso en el propio documento borra las ~2.300 líneas de Fase B** (el fichero
tiene 3.696 líneas; `## Esquema por elemento — 87/89 resueltos` empieza en la 1394) y los hashes del
digest. Silenciosamente, sin aviso, e irrecuperable sin `SUDESPACHO_API_KEY` y una corrida en vivo.

`CLAUDE.md:212` sí dice lo correcto (`--phase all`). **El documento que se declara SSOT es el que está mal.**

**Cambio exigido:** `core/crm_atlas.py:371` debe emitir `--phase all`; y el CLI debería rehusar
sobrescribir un `.md` que contiene Fase B con un atlas que no la tiene, salvo `--force`.

### D2 — P1 · La SSOT del CRM se autocontradice, y el bug está en el generador

- `docs/CRM_SUDESPACHO_ATLAS.md:14` → `| Fase B (esquema por elemento) | ⏳ pendiente |`
- `docs/CRM_SUDESPACHO_ATLAS.md:1394` → `## Esquema por elemento — 87/89 resueltos` + ~2.300 líneas de datos.

Ambas las escribió `b2d624c`. Causa raíz verificada en [core/crm_atlas.py:366](../../../core/crm_atlas.py):

```python
phase_b_complete = meta.get("phase_b", {}).get("complete", False)
…
lines.append(f"| Fase B … | {'✅' if phase_b_complete else '⏳ pendiente'} |")
```

El meta lleva **dos** claves — `ran` y `complete` (= *0 degradados*) — y el render **ignora `ran`**,
presentando una métrica de completitud como si fuera estado de ejecución. Con 2 elementos degradados
(`conceptos_honorario`, `tareas`), la fila miente. Ningún test lo cubre.

**Cambio exigido:** distinguir los tres estados: `✅ 87/89` / `⚠️ 87/89 (2 degradados)` / `⏳ no ejecutada`.

### D3 — P1 latente · Vocabularios de `estado:` colisionantes (trampa de la remediación)

[test_docs_gobernanza.py:7](../../../tests/test_docs_gobernanza.py) define
`_ESTADOS = {"vigente","historico","aparcado","revisar"}`. Pero `GOBERNANZA_FUENTES_VERDAD.md:174`
impone a los handoffs `estado: activo | consumido | historico`. **`activo` y `consumido` no están en el
set.**

Hoy es invisible porque el glob no es recursivo. **En el momento en que alguien amplíe el glob a
`docs/**/*.md` —que es el movimiento natural de la remediación propuesta— el test falla al instante por
7 de 15 handoffs**, no por los specs. Cualquier plan de endurecimiento debe reconciliar el vocabulario
*antes* de tocar el glob.

### D4 — P2 · `MEJORAS #48` está duplicado *(verificado por mí)*

- [MEJORAS_FUTURAS.md:1700](../../MEJORAS_FUTURAS.md) — `## 48. Motor documental unificado … [PROMOVIDO → PLAN.md]`
- [MEJORAS_FUTURAS.md:1779](../../MEJORAS_FUTURAS.md) — `## 48. Endurecimiento del robot CENDOJ (cendoj-descarga)` + hijos `48.A`–`48.D`

Conteo propio: **85 encabezados `## NN.` para 84 números; es la única colisión del fichero.** Rompe la
llave del protocolo: `CLAUDE.md:220` y `PLAN.md:393,403` resuelven "`MEJORAS #48`" al motor documental.
La referencia `MEJORAS #NN` que la regla de promoción exige deja de ser unívoca justo en ese número.

**Escenario:** una sesión va a cerrar el motor documental, hace `Ctrl+F "## 48"` en un fichero de 3.105
líneas y marca `[COMPLETADO]` en la entrada de CENDOJ.

### D5 — P2 · Puntero roto que ninguna herramienta detecta *(verificado por mí)*

[PLAN.md:449](../../../PLAN.md) cita `…-email-atomize-layerb-{design,fase2}.md`. El
`…-layerb-design.md` existe en `specs/`; **no existe ningún `plans/*layerb*`** — el plan se llama
`2026-06-25-email-atomize-fase2.md`.

> **Resuelto 2026-07-26 (PR2 de la remediación):** `PLAN.md` desdobla ya la cita en el spec y el
> plan reales, y el guard **G2** cubre el hueco. La cita de arriba se deja en forma elíptica
> (`…-`) a propósito: es *prueba* de un puntero roto, no un puntero vivo, y G2 descarta las
> elipsis por patrón — que es como el repo distingue el ejemplo de la referencia.

El guard `test_sin_refs_a_docs_plan_legacy` solo comprueba que no se cite la **ubicación vieja**
`docs/PLAN_*.md`; **nunca verifica que la ruta citada exista**.

### D6 — P2 · `CRM_SUDESPACHO_ATLAS.md` fuera de INDICE.md, y exento del guard

Es un doc de raíz de `docs/` —el corpus que INDICE.md **sí** promete cubrir— y `CLAUDE.md:210` lo declara
*"SSOT de la superficie"*. No está en la tabla. Peor: empieza por `# Atlas…` sin `---`, y
[test_docs_gobernanza.py:15](../../../tests/test_docs_gobernanza.py) (`if txt.startswith("---")`) lo
**exime silenciosamente** del guard. Un doc de raíz sin frontmatter no falla el test: desaparece del
control. Ese es un agujero del guard, no del doc.

*(Colateral menor: los 7 handoffs de `specs/cronologia-handoffs/` no tienen frontmatter alguno; su
estado vive **solo** en la vista derivada `INDICE.md:90`, que es exactamente el Drift que
`GOBERNANZA_FUENTES_VERDAD.md:178` declara querer impedir.)*

---

## Veredicto sobre la remediación propuesta

### El test `test_specs_plans_handoffs_citados_en_indice`: **no implementar, ni con fecha de corte**

Seis razones, en orden de peso:

1. **Asserta un contrato inexistente.** INDICE.md nunca indexó specs/plans fechados: 1 de 84
   históricamente. El test no detecta una degradación; **impone una política nueva** disfrazada de guard.
2. **Retrofit desproporcionado y de bajo valor.** ~98 filas manuales, más el juicio caso por caso del
   `estado:` de 30 specs históricos: precisamente el recurso escaso (criterio de Nikolai) que la
   gobernanza quiere ahorrar.
3. **Contradice el principio rector.** `GOBERNANZA_FUENTES_VERDAD.md:142-144` pide *"un campo de
   frontmatter y un índice de una tabla; nada de sitio de documentación"*. Una tabla de 112 entradas que
   restata estado ya presente en PLAN/bitácora/git **crea el cuarto hogar** que la doctrina combate.
4. **La variante con fecha de corte no arregla nada.** Sigue afirmando el contrato equivocado, solo que
   hacia el futuro; y como no hay consumidor, es trabajo que no compra nada.
5. **Precedente de erosión.** El guard existente ya acumula **dos excepciones hardcodeadas en 48 líneas**
   ([test_docs_gobernanza.py:40](../../../tests/test_docs_gobernanza.py) y [:46](../../../tests/test_docs_gobernanza.py)).
   Un test sobre 112 ficheros heterogéneos acumulará excepciones hasta que alguien lo silencie.
6. **Colisiona con D3.** El movimiento natural de ampliar el glob rompe 7 handoffs al instante.

**Apunte transversal**: el test propuesto habría dado **verde** ante los seis defectos reales (D1-D6).
Un guard que no habría cazado ninguno de los problemas que sí existen es la definición de guard mal
dirigido.

### El aviso `_avisar_specs_sin_plan_activo()`: **es la parte buena, pero hay que rediseñarlo**

La idea encaja con el patrón vigente (`_avisar_plan_desfasado` / `_avisar_higiene_planificacion`: no
bloqueante, solo lectura local, sin red) y apunta al hueco **real** — el ledger, no el índice. Ahora
bien, tal como está esbozado (buscar mención en `PLAN.md` y bitácora) **reproduciría el 88% de falsos
positivos de H3**, porque busca el stem del plan y no mira el corpus completo.

Rediseño mínimo para que sirva: disparar sobre **specs/plans creados en los últimos N días según
`git log --diff-filter=A`**, y darlo por trazado si aparece **cualquiera** de estas señales en
`PLAN.md`, `docs/bitacora/`, `MEJORAS_FUTURAS.md`, `DEAD_ENDS.md` o `handoffs/`: el stem, la etiqueta
`[XXX]` del bloque, o el nº de PR del commit que lo introdujo.

### Contrapropuesta: tres guards baratos que sí habrían cazado defectos reales

En la línea de `GOBERNANZA_FUENTES_VERDAD.md:126-136` (*"automatizar solo los 3-4 invariantes que más
duelen"*):

| # | Guard | Coste | Habría cazado |
|---|---|---|---|
| **G1** | Unicidad de los `## NN.` en `MEJORAS_FUTURAS.md` | ~5 líneas | **D4** (`#48`) |
| **G2** | Toda ruta `docs/superpowers/{specs,plans}/*.md` citada en un `.md` trackeado debe existir en disco | ~15 líneas | **D5** (`layerb`) |
| **G3** | Todo doc de raíz de `docs/` debe **tener** frontmatter con `estado:` (no solo "si lo tiene, que sea válido") | ~3 líneas | **D6** (atlas exento) |

G3 exige antes decidir el `estado:` de los docs de raíz que hoy no lo llevan — trabajo acotado y
verificable, no un retrofit de 98 ficheros. Reconciliar el vocabulario (D3) es **prerrequisito** de
cualquier ampliación futura del glob.

### Lo que de verdad falta: el ledger, no el índice

El único fallo de gobernanza con daño demostrado es **`crm-atlas`: trabajo mergeado a `main` (PR #104)
sin fila en `PLAN.md ## ✅ Cerrados` ni entrada en la bitácora** — incumpliendo la regla de *hogar único
del estado* de `CLAUDE.md:62-71`. Se arregla con **cuatro líneas de ledger** (crm-atlas + los tres
benignos de H3: `dedup-guard-robusto`, `adjuntos-contenido-fase2`, `crm-atlas-fase-b`), no con un test
de 112 ficheros.

---

## Fiabilidad de esta propia revisión

Verificado **por mí directamente** (no delegado): estado de `87ff113` y `b2d624c`; las 0 ocurrencias de
`atlas` en los cuatro ficheros; el duplicado `#48` y el conteo 85/84; el ledger `PLAN.md:1538`; el
puntero roto `PLAN.md:449`; la estructura de `INDICE.md`; el alcance y el vocabulario de
`test_docs_gobernanza.py`; y ambas mitades de D1/D2 en `core/crm_atlas.py` y `scripts/crm_atlas.py`.

Procede **solo de subagente** (no re-verificado línea a línea): el censo de frontmatter de H4, la tabla
de 25 filas de H3 y las 3 contramarcas ausentes de H5.

**Caveat:** el subagente de H2 reportó recuentos de líneas erróneos (`PLAN.md` 1340, bitácora 156;
reales **1549** y **286**). No afecta a sus conclusiones de `grep`, que confirmé aparte, pero conviene
no citar sus cifras de tamaño.

## Adjudicación

> Segunda ronda (2026-07-26, 4 subagentes en paralelo) con mandato de **disputar las
> conclusiones de esta misma revisión**. Corrigió seis afirmaciones propias — anotadas en
> §Autocorrecciones. Recomendación por fila; la decisión sigue siendo de Nikolai.

| Ítem | Veredicto | Recomendación | Acción | Esfuerzo | PR |
| --- | --- | --- | --- | --- | --- |
| H1 | REFUTADO | aceptar | ninguna, cerrar | 0 | — |
| H2 | CONFIRMADO CON MATIZ (P2, **no sube a P1**) | aceptar | fila `[CRM-ATLAS]` en el ledger + puntero en `PLAN.md:358` + `87ff113`→`b2d624c` | 20 min | PR2 |
| H3 | REFUTADO (88% FP) | aceptar | retirar. **5 stems pendientes ya verificados: los 5 TRAZADOS** (ver §Cierre de H3) — 0 filas obligatorias | 0 | — |
| H4 | REFUTADO | aceptar | acotar la frase de `INDICE.md:23` a las 3 poblaciones | 5 min | PR2 |
| H5 | REFUTADO | aceptar **con reserva** | ninguna; **corregir el dato: la contramarca `#58` es falsa** (`MEJORAS_FUTURAS.md:2405` ya lleva `[COMPLETADO → PR #42]`) | 0 | — |
| D1 | **P2 alto** (recuperable con `git restore`), no P1 | arreglar | `--phase all` en **los dos** renders (md **y digest**) + guarda dura anti-clobber en el CLI | 30 min | PR1 |
| D2 | P1 | arreglar | tres estados leyendo `ran` + `complete` + contadores | 15 min | PR1 |
| D3 | P1 latente | **modificar** | **no** unificar `_ESTADOS`: vocabularios por población. Hoy solo señalizar la trampa en `test_docs_gobernanza.py:7` | 5 min | PR2 |
| D4 | P2 | hacer | renumerar **CENDOJ → `#85`** (6 refs externas, todas internas al fichero; mover el motor rompería 3 anclas del protocolo) | 20 min | PR2 |
| D5 | P2 | hacer | desdoblar la cita de `PLAN.md:449` en spec + plan reales | 2 min | PR2 |
| D6 | P2 | **modificar** | alta en INDICE sí; el frontmatter **no se puede añadir a mano** (fichero generado) → emitirlo en `render_markdown` | 10+20 min | PR2 + PR1 |
| G1 | — | hacer | unicidad de `## NN.` en MEJORAS (verde solo tras D4) | 10 min | PR2 |
| G2 | — | **modificar** | tal como se redactó **no caza D5**: añadir stems desnudos, expandir llaves `{a,b}`, descartar elipsis y placeholders | 40 min | PR2 |
| G3 | — | **descartar y sustituir** | no es barato (12 de 20 docs fallan). Sustituir por «todo `docs/*.md` citado en `INDICE.md`» — caza D6 igual y nace verde con **una** fila | 10 min | PR2 |
| Test INDICE | — | **no implementar** | confirmado | — | — |
| Test «citado en algún sitio» | — | **no como test**, pero limpiar | solo **6 de 99** fallarían (4 huérfanos reales). No bloqueante porque `session_close` corre pytest como verja y rompería el estado legítimo «spec hoy, decisión mañana» | 20 min | PR2 |
| Aviso `session_close` | — | implementar **con corrección crítica** | **excluir `handoffs/` del corpus de trazas** y eliminar la señal `[XXX]`; N=10 días | 45 líneas | PR3 |

### Cierre de H3 — los 5 stems que quedaban sin anclar

Verificados (2026-07-26). **Los 5 TRAZADOS; ninguna fila de ledger es obligatoria.**

| Plan | Ancla | Señal |
|---|---|---|
| `2026-06-15-intake-whatsapp-fase-a` | `PLAN.md:1546` + `bitacora/2026.md:193` | etiqueta `[INTAKE-WHATSAPP-FASE-A]` en el ledger + prosa de cierre |
| `2026-06-17-sala-lectura-f0a3` | `PLAN.md:711-715` | casillas `[x]` (hash `f253a84`) dentro de `[SIGUIENTE-CATALOGO-DOCUMENTAL]`, ítem **abierto** — correcto que no esté en `## ✅ Cerrados` |
| `2026-06-22-expedientes-xl-conector` | `bitacora/2026.md:175` + `PLAN.md:144,1544` | prosa nominal del cierre 22-06 (plan 1/3) |
| `2026-06-22-intake-skill-trazabilidad` | `bitacora/2026.md:175` | prosa nominal (plan 2/3) |
| `2026-06-22-empaquetado-plugin-feesdefender` | `bitacora/2026.md:175` + `ARQUITECTURA_RELACIONES.md:19,52-65` | prosa nominal (plan 3/3) + pieza viva del SSOT de build |

Esto **eleva la tasa de falsos positivos de H3 por encima del 88%** y confirma el diagnóstico
de método: la señal real vive como etiqueta, como casilla `[x]` dentro de un ítem abierto, o
como prosa nominal de bitácora — nunca como stem del plan.

Único hueco de **forma** (no de trazabilidad): el trío del plugin nunca recibió etiqueta ni
fila de ledger. Opcional, 1 fila consolidada `[PLUGIN-FEESDEFENDER]` con los tres planes.

**Gotcha general que conviene retener:** los hashes de junio citados en la bitácora
(`fa96e8c`, `c7d1f2a`, `fc71a75`, `f253a84`) **ya no resuelven en `main`** — el trabajo es
anterior a la reescritura de historial (`a40b27f`) y a la protección de rama (2026-07-07).
Que un hash de esa época no resuelva no dice nada sobre si el trabajo se hizo. Es el mismo
error de categoría que el del squash con `87ff113`, por otra causa.

### Autocorrecciones de la segunda ronda

Seis afirmaciones de este informe que la segunda ronda corrigió, todas contra el repo:

1. **D1 no es «irrecuperable».** `CRM_SUDESPACHO_ATLAS.md` y `atlas.digest.md` están **trackeados**; `git restore` los devuelve al 100%. Lo único irrecuperable es `atlas.json`, que está gitignored y **hoy no existe**. Severidad real: P2 alto.
2. **D1 tiene un segundo vector que no vi:** `render_digest` imprime `discover` **sin fase**, y el default del CLI es `--phase a` — mismo destrozo por otra puerta.
3. **G2, tal como lo redacté, no habría cazado D5.** La cita de `PLAN.md:449` es un *stem desnudo*, sin directorio; mi guard solo miraba rutas completas. La afirmación de la tabla de contrapropuesta era falsa.
4. **G3 no es barato:** 12 de 20 docs de raíz lo incumplirían — el mismo retrofit que este informe rechaza, un orden de magnitud menor. Y uno de los 12 es generado.
5. **El aviso rediseñado, tal como lo especifiqué, dispara 0 avisos: se autoanula.** Al incluir `handoffs/` en el corpus, el stem de crm-atlas aparece *solo* dentro del handoff que denunció el hueco — el aviso daría por trazado el defecto por haber sido denunciado. Corregido: `GOBERNANZA_FUENTES_VERDAD.md:164-166` dice que el handoff **no es fuente de verdad**. Excluyéndolo, dispara 3 a N=10 días, con 2 verdaderos positivos.
6. **Mi razón nº2 contra el test (~98 filas de retrofit) no sobrevive a la variante reformulada:** exigir la cita en *cualquier* sitio del corpus solo falla en 6 de 99. El descarte se sostiene, pero por otro motivo (la verja de pytest en `session_close`), no por el coste.

Además: el radio de D3 es **11 ficheros, no 7** (7 `consumido`, 1 `histórico` con tilde, 2 `aprobado`, 1 placeholder); `activo` no lo usa ningún handoff.
