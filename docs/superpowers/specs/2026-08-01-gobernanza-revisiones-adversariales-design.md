# Gobernanza de las revisiones adversariales — hogar, formato y censo

> **Estado:** rev. 1 (2026-08-01), pendiente de revisión adversarial de Codex.
> **Objeto:** cómo se documenta y se audita el intercambio Claude Code ↔ Codex en las
> revisiones de specs, planes y diffs.
> **Origen:** pregunta de Nikolai (2026-08-01) sobre si el «diálogo interno» necesita
> documentarse, cómo se estructura y cómo puede auditarse.

## 1. Qué se documenta hoy, medido

No hay diálogo: hay un intercambio de dos turnos con bus humano. Claude escribe el objeto →
se encarga la revisión → Codex ataca en solo lectura y entrega un informe → Nikolai lo trae →
Claude adjudica contra la fuente. Lo que se parece a diálogo son las **rondas** (la Fase 0 del
dual workspace tuvo tres pasadas sobre el mismo plan).

Eso produce **cuatro artefactos discretos** —mandato, informe, adjudicación, cobertura— y hoy
solo uno tiene hogar fijo.

**Censo del 2026-08-01** (grep de encabezados sobre `docs/superpowers/`):

| Hogar | Nº | Ejemplo |
|---|---|---|
| Acta hermana `…-adversarial-review.md` | 4 | `2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md` |
| Sección embebida en el spec | 5 | §9 de `2026-07-29-sandwich-firma-falso-positivo-design.md` |
| Sección embebida en el plan | 3 | §Adjudicación… de `2026-07-28-cableado-atomize-sala-maquina.md` |
| Handoff `handoff-…-codex-*.md` | 3 | los tres de la vista procesal |
| **Ningún encabezado: solo la bitácora** | **≥3** | las tres pasadas de Codex sobre el plan de la Fase 0 |

Las tres últimas son el hallazgo que ordena este diseño: **una adjudicación con recuento
exacto —«5 confirmados, 1 refutado, 1 declarado sin verificar», veredicto REQUIERE REVISIÓN—
que ningún censo de specs ni de planes encuentra**, porque vive en la prosa del 50º cierre de
`docs/bitacora/2026.md`. El total real no es 12: es «al menos 15, y no sabemos cuántas más».

### 1.1 Por qué está disperso

- `CLAUDE.md` §«Revisión adversarial» dice que la adjudicación «se registra en el spec **o** el
  plan». Ese «o» es la dispersión, escrita como norma.
- `GOBERNANZA_FUENTES_VERDAD.md` §5 añade una partición **ortogonal**: informe recibido de fuera
  → handoff; acta producida dentro → junto al spec. Pero un evento de revisión es las dos cosas,
  así que se parte en dos ficheros. El caso vista procesal se documenta a sí mismo: el handoff
  anunciaba que la adjudicación se anotaría en él, y tres días después lleva un párrafo de cierre
  corrigiéndose — acabó en §10 del spec.

### 1.2 Por qué el frontmatter no es la vía

Solo **14 de 53** specs y **14 de 62** planes llevan frontmatter. Exigirlo son 87 ficheros de
migración para un problema que no lo necesita. **Descartado.**

## 2. Qué se corrige y qué no

**En alcance:** el hogar de cada uno de los cuatro artefactos; un formato de adjudicación
parseable; el archivo del informe recibido; un censo auditable; guards que lo sostengan.

**Fuera de alcance, explícitamente:**

- Exigir que todo spec o plan tenga revisión. El guard no juzga si algo debió revisarse.
- Automatizar el puente Codex ↔ Claude Code. Sigue siendo manual y mediado por Nikolai.
- Transcribir el intercambio. No hay transcripción que capturar.
- Frontmatter en specs y planes.
- Cambiar quién adjudica. Claude sigue siendo el juez (`CLAUDE.md`), y este diseño existe
  precisamente para que ese juicio sea contrastable.

## 3. Modelo: cuatro artefactos, cuatro hogares

| Artefacto | Hogar | Obligatorio |
|---|---|---|
| **Mandato** (qué se pidió atacar) | El propio spec/plan, §«Revisión adversarial» previa | No: reconstruible |
| **Informe recibido**, literal y sin modificar | Acta hermana `…-adversarial-review.md` | **Sí, siempre que haya informe** |
| **Adjudicación** (veredicto + hallazgo → decisión → remedio) | Sección embebida en el spec/plan | **Sí** |
| **Cobertura** (ejecutada / no ejecutada) | Fila del registro + línea en el spec/plan | **Sí** |

La decisión de fondo: **la adjudicación se queda embebida** donde el lector ya está, porque es
el patrón dominante y el más reciente (8 de 12 encabezados, todos los de la última semana de
julio), y **el acta cambia de papel**: deja de ser «adjudicación larga» y pasa a ser el archivo
de lo recibido de fuera. Con eso la tensión de §5 se disuelve sin tocar la regla: el informe
recibido tiene hogar, y no es el mismo que la decisión.

## 4. Vocabularios cerrados

Hoy un solo campo mezcla dos cosas, y ya importó: en cableado-atomize **Codex dijo REWORK y
Claude no aceptó ese veredicto global**. Se separan tres ejes.

**`cobertura`** — `ejecutada` · `no-ejecutada`.
Sin cobertura no hay veredicto. Es la doctrina de `docs/DEAD_ENDS.md` («un revisor que no corre
no refuta: deja sin verificar») convertida en campo obligatorio.

**`veredicto`** — lo que dijo el revisor, con las palabras que ya se usan en el repo:

| Valor | Significado |
|---|---|
| `SHIP` | Sin bloqueantes. |
| `LISTA-CON-CAMBIOS` | Se acepta aplicando cambios acotados. |
| `REQUIERE-REVISION` | El objeto necesita reescritura antes de avanzar. |
| `NO-SHIP` | Bloqueante. |
| `NO-EJECUTABLE` | El objeto no se puede ejecutar ni verificar tal como está. |
| `SIN-VEREDICTO` | El revisor no se pronunció globalmente. |

**`estado_remediacion`** — cómo quedó tras adjudicar: `remediado` · `parcial` · `sin-cambios` ·
`pendiente`. `sin-cambios` cubre tanto «todo refutado» como «aceptado sin necesidad de tocar
nada»; el desglose va al recuento, no aquí.

**Recuento de hallazgos** — `confirmados · rebajados · refutados · escalados · sin-verificar`.
`sin-verificar` no es decorativo: es la categoría que la doctrina exige y que la 3ª pasada de la
Fase 0 ya usó.

> **Tercera población de vocabularios.** Estos tres ejes NO comparten set con `_ESTADOS_DOCS`
> (docs de raíz) ni con `_ESTADOS_HANDOFF` (handoffs). La cabecera de
> `tests/test_docs_gobernanza.py` documenta por qué unificarlos rompe 11 ficheros al instante
> (trampa D3). Por eso el campo se llama **`estado_remediacion`** y no `estado`: colisión
> imposible por construcción, no por disciplina.

## 5. Encabezado canónico y ficha

Se formaliza la línea que ya se escribe sola. Numeración **permisiva**: existe un `10-bis.` y
hay encabezados sin número.

```
## [N.] Adjudicación de la revisión adversarial (<revisor>, <AAAA-MM-DD>) — <VEREDICTO>, <estado_remediacion>
```

Inmediatamente debajo, cinco líneas que hoy están en prosa dispersa o ausentes:

```markdown
- **Objeto revisado:** `<ruta>` rev. N, commit `abc1234`
- **Revisor:** Codex (solo lectura) | Claude (no independiente: autor del objeto)
- **Informe recibido:** `<acta>.md` | sin informe (revisión propia) | no archivado (anterior a esta regla)
- **Hallazgos:** N confirmados · N rebajados · N refutados · N escalados · N sin verificar
- **Remediado en:** PR #NNN (`hash`) | rev. N de este documento | pendiente
```

Cuando el objeto no es un documento sino un diff, «Objeto revisado» admite `rama <nombre>` o
`PR #NNN` en lugar de ruta y revisión. Es el caso de la revisión de rama completa de
`2026-07-29-sandwich-firma-falso-positivo.md`.

`commit: no registrado` es un valor legítimo al migrar lo ya escrito. **No se inventa lo que no
consta**: un commit reconstruido a ojo es peor que su ausencia declarada.

## 6. El acta hermana

**Ubicación y nombre:** junto a su objeto —`docs/superpowers/specs/` o
`docs/superpowers/plans/`— como `AAAA-MM-DD-<tema>-adversarial-review.md`. Si el objeto es un
diff sin plan, junto al spec del que deriva; si no hay ninguno, en `specs/` con el nombre del PR.

**Frontmatter obligatorio** (son ~5 ficheros más los que vengan, no 87):

```yaml
---
tipo: revision-adversarial
objeto: docs/superpowers/specs/<fichero>.md
objeto_rev: "1"
commit: 8d9c96c
revisor: Codex
cobertura: ejecutada
veredicto: NO-SHIP
adjudicado_por: Claude
adjudicado_en: docs/superpowers/specs/<fichero>.md §20
estado_remediacion: remediado
---
```

**Contenido, dos secciones y en este orden:**

1. **Informe recibido, sin modificar** — literal, y se declara literal. Es el que permite
   auditar si Claude rebajó o descartó un hallazgo indebidamente.
2. **Evidencia verificada** — qué se comprobó abriendo el fichero, con ruta y línea. Ya se hace
   bien en `2026-07-27-cableado-atomize-sala-maquina-adversarial-review.md`.

La adjudicación **no** se repite aquí: vive en el spec o el plan.

**Cuándo es obligatoria:** siempre que haya informe (decisión de Nikolai, 2026-08-01). Regla
mecánica, sin criterio que discutir en cada caso.

**Las cuatro actas existentes son híbridas** —llevan informe y adjudicación en el mismo
fichero— porque nacieron antes de este reparto. Se les añade frontmatter (G8) y **se les
conserva la adjudicación donde está**: reescribirlas para mover secciones es churn sin lector.
G7 **no** se les aplica; el marcador `tipo: revision-adversarial` del frontmatter es lo que las
exime, y el registro apunta su adjudicación al propio acta. El reparto del §3 rige de aquí en
adelante.

## 7. El registro central

`docs/REVISIONES_ADVERSARIALES.md` — fichero propio, no sección de `INDICE.md`: a dos o tres
revisiones por semana son ~150 filas al año y ahogarían el índice. Lleva **fila en `INDICE.md`**
para no romper G3.

Es **vista derivada**, no hogar del estado — mismo patrón que `INDICE.md §Handoffs` y su guard
G6. El estado sigue viviendo en la sección embebida y en el acta. Orden: reciente primero.

| Columna | Contenido |
|---|---|
| Fecha | `AAAA-MM-DD` de la entrega del informe |
| Objeto | fichero + rev. + commit revisado |
| Revisor | `Codex` · `Claude (no independiente)` · `—` |
| Cobertura | `ejecutada` · `no-ejecutada` |
| Veredicto | del §4, o `—` si no hubo cobertura |
| Recuento | `5c · 0r · 1ref · 0e · 1sv` (confirmados, rebajados, refutados, escalados, sin verificar) |
| Adjudicación | ruta + §, o `—` |
| Informe | acta, o el motivo de su ausencia |
| Remedio | PR #NNN, o `pendiente` |

Las revisiones **no ejecutadas** son filas de pleno derecho. Las cuatro que `docs/DEAD_ENDS.md`
ya registra por el cupo agotado de `agy` entran así: es exactamente el hueco que el registro
existe para hacer visible.

## 8. Guards

Tres tests nuevos en `tests/test_docs_gobernanza.py`, como **población separada** con su propio
vocabulario, siguiendo la disciplina que la cabecera de ese fichero impone.

- **G7 — adjudicación bien formada.** Toda sección de un spec o un plan cuyo encabezado
  **contenga** «Adjudicación de la revisión» (el número es opcional y puede ser `10-bis.`) casa
  el regex del §5, con `veredicto` y `estado_remediacion` de los sets cerrados, y va seguida de
  las cinco líneas de la ficha. Los ficheros con `tipo: revision-adversarial` quedan exentos
  (§6, actas híbridas).
- **G8 — acta bien formada.** Todo `*-adversarial-review.md` lleva el frontmatter del §6 con
  vocabulario válido, y su `adjudicado_en` apunta a un fichero que existe.
- **G9 — censo bidireccional.** Toda adjudicación (sección o acta) tiene fila en el registro, y
  toda fila del registro apunta a una adjudicación o acta existente.

**Lo que los guards NO hacen, declarado para que no derive:**

- No exigen que un spec o un plan tenga revisión.
- No tocan `_ESTADOS_DOCS`, ni `_ESTADOS_HANDOFF`, ni vuelven recursivo el glob de
  `_docs_con_frontmatter`.
- No piden frontmatter a specs ni a planes.
- No comprueban el *contenido* de la adjudicación. Que un hallazgo esté bien refutado no lo
  puede decir un test; para eso está el informe archivado del §6.

## 9. Migración

**Ocho adjudicaciones embebidas** — normalizar encabezado y añadir ficha (G7). Los datos ya
están en prosa en casi todas; donde falte el commit se pone `no registrado`.

- En specs: vista procesal §10, email-atomize-enumeracion §11, dual workspace §20,
  sandwich-firma §9, historial-citado §10-bis.
- En planes: cableado-atomize §Adjudicación del PLAN, sandwich-firma §Adjudicación y
  §Adjudicación de la revisión de rama completa.

**Cuatro actas híbridas** — solo frontmatter (G8). No se les mueve la adjudicación (§6):
`2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md`,
`2026-07-26-gobernanza-indice-adversarial-review.md`,
`2026-07-27-cableado-atomize-sala-maquina-adversarial-review.md`,
`2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md`.

**Las tres pasadas de la Fase 0** — reconstruir desde la bitácora y el historial de PRs
(#166 entre ellos) y darles encabezado en su plan. Es la parte con más valor y la única que
exige leer git.

**Los cuatro registros de cobertura ausente** de `docs/DEAD_ENDS.md` → filas con
`cobertura: no-ejecutada`.

**Los tres handoffs `…-codex-*`** se quedan donde están, declarados **excepción histórica** en
§5, igual que `prompt_handoff_expedientes_seguros.md`. Su contenido encaja con el nuevo papel del
acta, pero moverlos rompe G6 y los `consumido_por` que ya los citan. El registro los referencia
como informe de la revisión de la vista procesal.

**Informes crudos anteriores a esta regla:** perdidos, iban a `%TEMP%`. El registro lo dirá:
`no archivado (anterior a esta regla)`. Se declara, no se disimula.

## 10. Doctrina a modificar

| Documento | Cambio |
|---|---|
| `CLAUDE.md` §Revisión adversarial | Resolver el «o»: adjudicación embebida siempre; acta siempre que haya informe; nombrar el registro |
| `AGENTS.md` | Codex numera hallazgos `H-NN` y entrega en formato archivable literal |
| `docs/GOBERNANZA_FUENTES_VERDAD.md` §5 | El acta es el hogar del informe recibido; excepción histórica de los tres `codex-*` |
| `docs/INDICE.md` | Fila del registro (G3) |
| `tests/test_docs_gobernanza.py` | Cabecera: tercera población de vocabularios |

## 11. Riesgos

- **El registro se desincroniza.** Mitigado por G9 bidireccional. Es el mismo riesgo que ya
  corre `INDICE.md §Handoffs` con G6, y ahí funciona.
- **G7 es un parser de Markdown y los parsers de prosa son frágiles.** Mitigado acotándolo a un
  encabezado con prefijo fijo y a cinco líneas con prefijo `- **Campo:**`. Si el guard resulta
  ruidoso, la salida es relajar el regex, no borrar el campo.
- **Coste por revisión.** Sube: una acta más y una fila más. Es deliberado y acotado (pegar un
  informe y añadir una fila), y compra lo único que hoy no existe: poder auditar la adjudicación
  contra lo que el revisor dijo de verdad.
- **Riesgo de que esto sea el andamio que nadie mantiene.** Es el riesgo real. La defensa es que
  los tres guards fallan en rojo: si nadie mantiene el registro, la suite lo dice el mismo día.

## 12. Criterios de aceptación

1. `python -m pytest -q --tb=no` verde, con G7-G9 incluidos.
2. `docs/REVISIONES_ADVERSARIALES.md` existe, tiene fila en `INDICE.md` y contiene las ≥15
   revisiones conocidas, incluidas las cuatro de cobertura ausente.
3. Las 8 adjudicaciones embebidas casan G7; las 4 actas híbridas casan G8 sin reescritura.
4. Las tres pasadas de la Fase 0 tienen encabezado en su plan y fila en el registro.
5. Ninguna población de vocabulario existente se ha tocado.
6. Responder «qué se revisó en julio, por quién, con qué veredicto y dónde se adjudicó» es leer
   una tabla, no un grep de prosa.

## 13. Mandato para la revisión adversarial de este spec

Puntos de ataque, en orden de daño si están mal:

1. **El censo.** ¿Hay adjudicaciones que ni el grep de encabezados ni la bitácora encuentran?
   Si el «≥15» se queda corto, la migración del §9 nace incompleta.
2. **G7 contra los 12 ficheros reales.** ¿El regex del §5 casa lo que hay, o obliga a reescribir
   encabezados que ya funcionan? Un guard que exige cambiar 12 ficheros para nacer verde es un
   guard mal calibrado.
3. **La tercera población de vocabularios.** ¿`estado_remediacion` evita de verdad la trampa D3,
   o reintroduce la deriva por otra puerta?
4. **G9 y el bucle.** El registro cita ficheros de `docs/superpowers/`; G2
   (`test_citas_a_specs_y_plans_existen`) exige que existan. ¿Puede G9 entrar en conflicto con
   G2 al crear una fila antes que su acta?
5. **La decisión del §3.** ¿Es correcto dejar la adjudicación embebida, o el acta hermana era
   mejor hogar y el argumento del «patrón dominante» es una falacia de statu quo?
6. **Sobreingeniería.** Con el §2 delante, ¿sobra alguna pieza? El candidato más probable es el
   registro central: ¿bastaría con G7 + G8 y un grep?
