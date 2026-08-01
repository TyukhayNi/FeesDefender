# Gobernanza de las revisiones adversariales — hogar, formato y censo

> **Estado:** **rev. 2** (2026-08-01), tras revisión adversarial de Codex con veredicto
> **NO-SHIP** sobre la rev. 1 — los seis hallazgos confirmados y remediados aquí; la adjudicación
> uno a uno está en el §14 y el informe literal en
> `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review.md`.
> **Objeto:** cómo se documenta y se audita el intercambio Claude Code ↔ Codex en las revisiones
> de specs, planes y diffs.
> **Origen:** pregunta de Nikolai (2026-08-01) sobre si el «diálogo interno» necesita
> documentarse, cómo se estructura y cómo puede auditarse.

## 1. Qué es una revisión, y cuántas hay

No hay diálogo: hay un intercambio de dos turnos con bus humano. Claude escribe el objeto → se
encarga la revisión → Codex ataca en solo lectura y entrega un informe → Nikolai lo trae → Claude
adjudica contra la fuente. Lo que se parece a diálogo son las **rondas**.

### 1.1 Identidad de una revisión

La rev. 1 contaba ficheros, secciones, informes y rondas en la misma columna, y por eso su
cardinalidad no era auditable. Se fija primero la unidad:

> Una **revisión** es la tupla **`(objeto, commit o rev. del objeto, ronda, revisor, fecha de
> entrega)`**.

Consecuencias, todas verificadas sobre el corpus:

- El acta dual y el §20 de su spec **son la misma revisión** en dos hogares, no dos.
- `handoff-…-codex-informe.md` y `handoff-…-codex-review.md` son informe completo y resumen de la
  **misma primera pasada**; `…-review-2.md` sí es otra ronda.
- Las tres pasadas sobre el plan de la Fase 0 son **tres revisiones**: mismo objeto, distinta rev.
- Un objeto revisado por Codex y además por Claude en la misma ronda son **dos revisiones** con
  distinto revisor, y así se cuentan.

### 1.2 Corte temporal

**Se migra desde el 2026-07-23**, fecha de la primera acta y del arranque de hecho del contrato
con Codex. Antes de esa fecha hubo revisiones adjudicadas —`PLAN.md:924-928` (Google MCP F1),
`PLAN.md:933` (F2), `PLAN.md:953` (spec MCP sudespacho), `PLAN.md:1033-1044` (14 hallazgos
confirmados; y otra con veredicto SHIP)— que **quedan fuera de alcance y se declaran aquí**: no
existía contrato de revisor estable, no hay informe que archivar y reconstruirlas desde prosa
produciría un censo de exactitud fingida. `PLAN.md` sigue siendo su registro.

### 1.3 Censo desde el corte

**Dieciséis revisiones identificadas** entre 2026-07-23 y 2026-08-01. El plan verifica cada una
antes de tocarla; la lista es punto de partida, no resultado:

| # | Objeto | Ronda | Revisor | Dónde consta hoy |
|---|---|---|---|---|
| 1-2 | emails atomizados sala lectura | 1 y 2 | Codex / Claude | acta 07-23, con una 2ª adjudicación fechada 07-27 en el mismo fichero |
| 3 | diagnóstico gobernanza INDICE | 1 | subagentes | acta 07-26 |
| 4 | cableado atomize — spec | 1 | Codex + Claude | acta 07-27 |
| 5 | cableado atomize — plan | 1 | Codex | §Adjudicación del plan |
| 6-7 | vista procesal — spec v3 y v3.1 | 1 y 2 | Codex | 3 handoffs + §10 del spec |
| 8 | email atomize enumeración | 1 | Codex | §11 del spec |
| 9-11 | sandwich firma — spec, plan y rama | 1 | Codex | §9 del spec, §1061 y §1089 del plan |
| 12 | dual case workspace — spec rev. 1 | 1 | Claude | acta 07-29 + §20 del spec |
| 13-15 | dual workspace Fase 0 — plan | 1, 2 y 3 | Codex | `PLAN.md:587,595`; la 3ª en PR #166 |
| 16 | este spec | 1 | Codex | acta + §14 |

**Ninguna de ellas es `cobertura: no-ejecutada`.** Los cuatro casos de `DEAD_ENDS.md:620-630` son
**encargos a Gemini** que no corrieron, no objetos sin revisar: en tres de ellos el objeto sí fue
revisado (por Codex o por Claude) y en el cuarto lo que faltó fue el barrido mecánico delegado. Ese
hecho pertenece a `DEAD_ENDS.md` como indisponibilidad de proveedor, no al censo de revisiones.

### 1.4 Por qué está disperso

- `CLAUDE.md` §«Revisión adversarial» dice que la adjudicación «se registra en el spec **o** el
  plan». Ese «o» es la dispersión, escrita como norma.
- `GOBERNANZA_FUENTES_VERDAD.md` §5 añade una partición **ortogonal**: informe recibido de fuera →
  handoff; acta producida dentro → junto al spec. Un evento de revisión es las dos cosas, así que
  se parte en dos ficheros. El caso vista procesal se documenta a sí mismo: el handoff anunciaba
  que la adjudicación se anotaría en él, y tres días después lleva un párrafo corrigiéndose.

### 1.5 Por qué el frontmatter general no es la vía

Solo **14 de 53** specs y **14 de 62** planes lo llevan. Exigirlo son 87 ficheros de migración
para un problema que no lo necesita. **Descartado.**

## 2. Qué se corrige y qué no

**En alcance:** el hogar de cada artefacto; un formato de adjudicación parseable; el archivo del
informe recibido; un censo **calculable**; dos guards que lo sostengan.

**Fuera de alcance, explícitamente:**

- Exigir que todo spec o plan tenga revisión. El guard no juzga si algo debió revisarse.
- Un registro central versionado. Descartado en la rev. 2 (§7).
- Automatizar el puente Codex ↔ Claude Code. Sigue siendo manual y mediado por Nikolai.
- Frontmatter en specs y planes.
- Revisiones anteriores al 2026-07-23 (§1.2).
- Cambiar quién adjudica. Claude sigue siendo el juez; este diseño existe para que ese juicio sea
  contrastable.

## 3. Modelo: cuatro artefactos, cuatro hogares

| Artefacto | Hogar | Obligatorio |
|---|---|---|
| **Mandato** (qué se pidió atacar) | El propio spec/plan, §«Revisión adversarial» previa | No: reconstruible |
| **Informe recibido**, literal | Acta hermana `…-adversarial-review.md` | **Sí, siempre que haya informe** |
| **Adjudicación** (veredicto + hallazgo → decisión → remedio) | Sección embebida en el spec/plan | **Sí** |
| **Cobertura** ausente | Línea declarada en el spec/plan | Sí, cuando no se ejecutó |

La adjudicación se queda **embebida** por proximidad al objeto y hogar único: quien lee el spec
necesita saber qué sobrevivió al ataque sin abrir otro fichero. El argumento no es «8 de 12» —eso
es statu quo—, es que la decisión pertenece al documento que la decisión modificó.

El **acta cambia de papel**: deja de ser «adjudicación larga» y pasa a ser el archivo de lo
recibido de fuera. Con eso la tensión de §5 se disuelve sin tocar la regla.

## 4. Vocabularios cerrados

Un solo campo mezclaba dos cosas, y ya importó: en cableado-atomize **Codex dijo REWORK y Claude
no aceptó ese veredicto global**. Tres ejes.

**`cobertura`** — `ejecutada` · `no-ejecutada`. Sin cobertura no hay veredicto (doctrina de
`docs/DEAD_ENDS.md`). `no-ejecutada` describe **un encargo que terminó sin sustituto y sin
adjudicación**; un encargo fallido a un proveedor que otro revisor cubrió **no** es `no-ejecutada`.

**`veredicto`** — lo que dijo el revisor:

| Valor | Significado |
|---|---|
| `SHIP` | Sin bloqueantes. |
| `LISTA-CON-CAMBIOS` | Se acepta aplicando cambios acotados. |
| `REQUIERE-REVISION` | El objeto necesita reescritura antes de avanzar. |
| `NO-SHIP` | Bloqueante. |
| `NO-EJECUTABLE` | El objeto no se puede ejecutar ni verificar tal como está. |
| `SIN-VEREDICTO` | El revisor no se pronunció globalmente. |

**`estado_remediacion`** — `remediado` · `parcial` · `sin-cambios` · `pendiente`.

**Recuento** — `confirmados · rebajados · refutados · escalados · sin-verificar`. Un hallazgo
aceptado **con un remedio distinto del exigido** cuenta como confirmado; la divergencia se razona
en la prosa de la adjudicación. No se añade un sexto contador para eso.

**Migración de tokens.** El corpus usa hoy `resuelto`, `aplicados`, `NO EJECUTABLE` y
`LISTA CON CAMBIOS`. Se normalizan al retrofit (§9). Normalizar el token no falsea nada: el
veredicto literal del revisor queda en el acta.

> **Tercera población de vocabularios.** Estos ejes NO comparten set con `_ESTADOS_DOCS` ni con
> `_ESTADOS_HANDOFF`. La cabecera de `tests/test_docs_gobernanza.py` documenta por qué unificarlos
> rompe 11 ficheros (trampa D3). El campo se llama **`estado_remediacion`** y no `estado`:
> colisión imposible por construcción. Codex confirmó que la separación resiste.

## 5. Encabezado canónico, ficha y parser

```
## [N.] Adjudicación de la revisión adversarial [<calificador>] (<revisor>, <AAAA-MM-DD>) — <VEREDICTO>, <estado_remediacion>
```

El calificador opcional cubre `del PLAN` y `de rama completa`. Debajo, cinco líneas:

```markdown
- **Objeto revisado:** `<ruta>` rev. N, commit `abc1234`
- **Revisor:** Codex (solo lectura) | Claude (no independiente: autor del objeto)
- **Informe recibido:** `<acta>.md` | sin informe (revisión propia) | no archivado (anterior a esta regla)
- **Hallazgos:** N confirmados · N rebajados · N refutados · N escalados · N sin verificar
- **Remediado en:** PR #NNN (`hash`) | rev. N de este documento | pendiente
```

Cuando el objeto es un diff, «Objeto revisado» admite `rama <nombre>` o `PR #NNN`.
`commit: no registrado` es legítimo al migrar: **no se inventa lo que no consta**.

### 5.1 El parser, especificado

La rev. 1 daba una plantilla y la llamaba regex. El contrato ejecutable es:

```python
_RE_ADJUDICACION = re.compile(
    r"^#{2,3}\s+(?:\S+\s+)?"                       # ## o ###, numeracion opcional (10., 10-bis.)
    r"Adjudicación de la revisión adversarial"
    r"[^(\n]*"                                     # calificador libre: "del PLAN", "de rama completa"
    r"\((?P<revisor>[^,)]+),\s*(?P<fecha>\d{4}-\d{2}-\d{2})\)"
    r"\s*—\s*(?P<veredicto>[A-Z-]+),\s*(?P<estado>[a-z-]+)\s*$",
    re.MULTILINE)
```

**Disparador y bloques cercados.** El guard no busca solo lo que casa: busca **toda línea de
encabezado que contenga «Adjudicación de la revisión»** y exige que case. Sin eso, un encabezado
mal formado no se detecta y pasa en silencio — que es el modo de fallo caro.

Y **antes de cualquier match se eliminan los bloques cercados** (``` … ```). No es una precaución
teórica: la plantilla de arriba, dentro de su cerca, fue detectada como encabezado real por el
grep de censo de la rev. 1. El defecto se observó, no se dedujo.

## 6. El acta hermana

**Ubicación y nombre:** junto a su objeto —`specs/` o `plans/`— como
`AAAA-MM-DD-<tema>-adversarial-review.md`. Si el objeto es un diff sin plan, junto al spec del que
deriva; si no hay ninguno, en `specs/` con el nombre del PR.

**Frontmatter obligatorio — solo identidad y procedencia del informe, más un puntero:**

```yaml
---
tipo: revision-adversarial
objeto: docs/superpowers/specs/<fichero>.md
objeto_rev: "1"
commit: 3126214
revisor: Codex
cobertura: ejecutada
veredicto: NO-SHIP
adjudicado_en: docs/superpowers/specs/<fichero>.md §14
---
```

`adjudicado_por` y `estado_remediacion` **no van aquí**: describen la decisión, y el segundo es
mutable. Si vivieran en el acta, cada remediación obligaría a sincronizar dos ficheros — el drift
exacto que este diseño elimina. `veredicto` sí se queda: es lo que el revisor dijo, y es inmutable.

**Contenido, dos secciones:**

1. **Informe recibido, sin modificar** — literal, y se declara literal.
2. **Evidencia verificada** — qué abrió Claude para adjudicar, con ruta y línea.

La adjudicación **no** se repite aquí.

**Cuándo es obligatoria:** siempre que haya informe (decisión de Nikolai, 2026-08-01).

**Las cuatro actas existentes son híbridas** —llevan informe y adjudicación juntos— porque
nacieron antes de este reparto. Se les añade frontmatter y **se les conserva la adjudicación donde
está**; el marcador `tipo: revision-adversarial` las exime de G7. Codex confirmó que pueden quedar
intactas.

## 7. El censo se calcula, no se mantiene

**No hay registro versionado.** La rev. 1 proponía `docs/REVISIONES_ADVERSARIALES.md`: una tabla
manual de nueve columnas que habría copiado por tercera vez hechos que ya viven en la ficha y en el
acta, con un guard que solo comprobaba que la fila existiera — nunca que sus valores coincidieran.
Eso no es una vista derivada: es una copia con permiso para divergir, y contradice
`GOBERNANZA_FUENTES_VERDAD.md` §«un hecho → un hogar».

En su lugar, **`scripts/censo_revisiones.py`**: un lector que recorre los encabezados canónicos
(§5) y el frontmatter de las actas (§6) y escupe la tabla por stdout. No puede derivar porque no se
mantiene: se recalcula. Precedente en el repo: `docs/CRM_SUDESPACHO_ATLAS.md` es un inventario
generado y re-ejecutable.

```bash
python -m scripts.censo_revisiones --desde 2026-07-23
```

Columnas: fecha · objeto (rev./commit) · ronda · revisor · cobertura · veredicto · recuento ·
adjudicación · informe · remedio. Su salida **no se commitea**.

Las revisiones **no ejecutadas** no son filas fantasma: son una línea declarada en el spec o el
plan afectado (§3), y el lector las recoge de ahí.

## 8. Guards

Dos tests nuevos en `tests/test_docs_gobernanza.py`, como **población separada** con vocabulario
propio, según la disciplina que impone la cabecera de ese fichero.

- **G7 — adjudicación bien formada.** Toda línea de encabezado que contenga «Adjudicación de la
  revisión», fuera de bloques cercados, casa `_RE_ADJUDICACION` con `veredicto` y
  `estado_remediacion` de los sets del §4, y va seguida de las cinco líneas de la ficha. Los
  ficheros con `tipo: revision-adversarial` quedan exentos (§6) — hoy la exención es **cautelar y
  no portante**: los encabezados de las cuatro actas híbridas (`## Adjudicación`,
  `## Tabla de adjudicación`) ni siquiera contienen la frase disparadora. Se conserva porque un
  informe futuro sí puede citarla.
- **G8 — acta bien formada.** Todo `*-adversarial-review.md` lleva el frontmatter del §6 con
  vocabulario válido, y su `adjudicado_en` apunta a un fichero que existe.

**Anti-automatch:** el corpus de G7 incluye **este mismo spec**. Si el guard vuelve a detectar la
plantilla del §5 dentro de su cerca, G7 falla. Es el test de regresión del defecto que Codex
encontró.

**Lo que los guards NO hacen:**

- No exigen que un spec o un plan tenga revisión.
- No tocan `_ESTADOS_DOCS`, ni `_ESTADOS_HANDOFF`, ni vuelven recursivo el glob de
  `_docs_con_frontmatter`.
- No piden frontmatter a specs ni a planes.
- No comprueban el *contenido* de la adjudicación. Que un hallazgo esté bien refutado no lo dice un
  test; para eso está el informe archivado.
- **No hay G9.** El censo se calcula; no hay fila que sincronizar.

## 9. Migración

**Retrofit declarado de siete de ocho encabezados.** El formato del §5 casa hoy **1 de 8**
(`2026-07-29-sandwich-firma-falso-positivo-design.md:287`). La rev. 1 afirmaba que «formaliza la
línea que ya se escribe sola»: **era falso**, converge la forma y no los tokens. Se elige el
retrofit —siete ediciones de una línea, una vez— frente a un parser permisivo permanente, porque
la complejidad del parser dual se paga siempre y el retrofit solo hoy. El coste queda reconocido
aquí, no escondido en un «normalizar».

Medido ejecutando el regex del §5.1 sobre el corpus (no estimado), el retrofit tiene **tres
grados de coste**, no uno:

| Sección | Grado | Qué falta |
|---|---|---|
| sandwich spec §9 | **casa** | nada |
| email enumeración §11 | **solo token** | `resuelto` → `remediado`; la estructura ya es correcta |
| historial §10-bis | estructura | `NO EJECUTABLE` → `NO-EJECUTABLE` |
| sandwich plan §1061 | estructura | `NO EJECUTABLE` → `NO-EJECUTABLE` |
| cableado plan | estructura | `veredicto ` sobra; `del PLAN` pasa a calificador |
| vista procesal §10 | estructura | revisor, fecha, veredicto y estado (se toman de sus handoffs) |
| dual workspace §20 | estructura | todo salvo `(rev. 2)`; se toma del acta |
| rama completa §1089 | estructura | falta «adversarial» y revisor; `LISTA CON CAMBIOS` → `LISTA-CON-CAMBIOS`; `aplicados` → `remediado` |

Los ocho llevan además la ficha de cinco líneas, con `no registrado` donde el commit no conste.

**Cuatro actas híbridas** — solo frontmatter (G8), sin mover su adjudicación.

**Las tres rondas de la Fase 0** — reconstruir desde `PLAN.md:587,595`, la bitácora y el PR #166, y
darles encabezado en su plan. Es la parte con más valor y la única que exige leer git.

**Los tres handoffs `…-codex-*`** se quedan, declarados **excepción histórica** en §5 de la
gobernanza, igual que `prompt_handoff_expedientes_seguros.md`: su contenido encaja con el nuevo
papel del acta, pero moverlos rompe G6 y los `consumido_por` que ya los citan.

**Informes crudos anteriores a esta regla:** perdidos, iban a `%TEMP%`. La ficha lo dirá:
`no archivado (anterior a esta regla)`. Se declara, no se disimula.

## 10. Doctrina a modificar

| Documento | Cambio |
|---|---|
| `CLAUDE.md` §Revisión adversarial | Resolver el «o»: adjudicación embebida siempre; acta siempre que haya informe |
| `AGENTS.md` | Codex numera hallazgos `H-NN` y entrega en formato archivable literal |
| `docs/GOBERNANZA_FUENTES_VERDAD.md` §5 | El acta es el hogar del informe recibido; excepción histórica de los tres `codex-*` |
| `tests/test_docs_gobernanza.py` | Cabecera: tercera población de vocabularios |

`docs/INDICE.md` **no** se toca: al no haber registro versionado, no hay documento nuevo de raíz.

## 11. Riesgos

- **G7 es un parser de prosa.** Mitigado acotándolo a encabezado con frase fija, cinco líneas con
  prefijo `- **Campo:**` y eliminación previa de cercas. Si resulta ruidoso, la salida es relajar
  el regex, no borrar el campo.
- **El retrofit toca ocho documentos vivos.** Son ediciones de una línea más una ficha; el
  contenido no se altera y el veredicto literal queda en las actas.
- **Coste por revisión.** Sube: un acta más. Es deliberado y compra lo único que hoy no existe —
  poder auditar la adjudicación contra lo que el revisor dijo de verdad.
- **El generador se queda sin mantener.** Riesgo real y asumido: si nadie corre el censo, no pasa
  nada grave — G7 y G8 siguen sosteniendo los artefactos, que es donde vive el dato. Un generador
  sin uso es código muerto; una tabla sin mantener es información falsa. Se prefiere el primero.

## 12. Criterios de aceptación

1. `python -m pytest -q --tb=no` verde, con G7 y G8 incluidos.
2. Los ocho encabezados casan G7 tras el retrofit; las cuatro actas híbridas casan G8 sin
   reescritura.
3. G7 corre sobre este spec y **no** detecta la plantilla del §5.
4. Las tres rondas de la Fase 0 tienen encabezado en su plan.
5. Ninguna población de vocabulario existente se ha tocado.
6. Responder «qué se revisó desde el 23 de julio, por quién, con qué veredicto y dónde se
   adjudicó» es **un comando reproducible**, no un grep de prosa.
7. No existe `docs/REVISIONES_ADVERSARIALES.md` ni ningún guard G9.

> **Contrato ya validado antes del plan (2026-08-01).** El regex del §5.1 se ejecutó contra todo
> `docs/superpowers/`: **9 disparadores fuera de cerca**, de los que casan limpio **2** — el §9 de
> sandwich-firma y el §14 de este spec. La plantilla cercada del §5 fue detectada y descartada por
> el filtro de cercas: el criterio 3 ya pasa. El desglose 1 casa / 1 solo token / 6 estructura del
> §9 es medición, no estimación.

## 13. Mandato para una eventual segunda pasada

1. **El censo del §1.3.** ¿Las dieciséis son dieciséis bajo la identidad del §1.1? El candidato a
   error es la fila 1-2 (¿dos rondas o una adjudicación en dos tiempos?) y las 6-7.
2. **El regex del §5.1 contra los ocho encabezados retrofitados** y contra este spec. ¿Casa lo que
   dice casar, y solo eso?
3. **El corte del §1.2.** ¿Dejar fuera lo anterior al 23 de julio es una línea defendible o una
   amnistía cómoda?
4. **El generador del §7.** ¿Es código muerto disfrazado de solución? Si nadie va a correrlo, la
   respuesta honesta es no escribirlo y quedarse con G7 + G8.
5. **La exención de las actas híbridas.** ¿Crea una clase permanente de documentos fuera de guard?

## 14. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 1, commit `3126214`
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review.md`
- **Hallazgos:** 6 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento

| Hallazgo | Severidad | Veredicto | Dónde se remedia |
|---|---|---|---|
| H-01 censo sin identidad; omite precedentes de `PLAN.md` | CRÍTICA | **Confirmado** | §1.1 (identidad), §1.2 (corte), §1.3 (censo) |
| H-02 los cuatro de `DEAD_ENDS` no son cobertura ausente | ALTA | **Confirmado** | §1.3 párrafo final, §4 (definición de `no-ejecutada`) |
| H-03 G7 casa 1/8 y se autodetecta en la cerca | ALTA | **Confirmado** | §5.1 (regex + cercas), §9 (retrofit declarado), §12.3 |
| H-04 el registro central sobra | ALTA | **Confirmado, remedio acotado** | §7 (censo calculado), §8 (sin G9) |
| H-05 G9 rechaza las filas `no-ejecutada` | ALTA | **Confirmado** | Disuelto al retirar G9; la sustancia, en §7 |
| H-06 el frontmatter invade el hogar de la decisión | MEDIA | **Confirmado** | §6 (frontmatter reducido) |

**Divergencia sobre H-04.** Se acepta el hallazgo y se retira la tabla manual y G9. **No** se
aceptan sus dos últimos remedios: suprimir los criterios de aceptación 2 y 6. El criterio 6 es la
pregunta que originó el encargo —poder auditar qué se revisó— y borrarlo habría eliminado el
objetivo en vez del defecto. Se conserva reformulado como «un comando reproducible» (§12.6), con el
generador del §7 en lugar del ledger. Es la única divergencia con el informe.

**Refutado a favor del spec:** el §13.4 de la rev. 1 temía un ciclo entre G9 y G2. Codex demostró
que no existe: crear acta y referencia en el mismo cambio es atómico, y un test rojo en un paso
intermedio es correcto. La preocupación era infundada y se retira.

**Errores propios que la revisión destapó**, más allá de los seis hallazgos: la rev. 1 afirmaba que
las rondas de la Fase 0 constaban «solo en la bitácora» —también están en `PLAN.md:587,595`— y que
el formato «se formaliza solo», cuando casaba 1 de 8. Ambos venían de censar únicamente
`docs/superpowers/` y no `PLAN.md`.

**Nota de método.** Seis de seis confirmados es un resultado inusual y no se firma por deferencia:
cinco se comprobaron contra la fuente al adjudicar y el sexto contra `PLAN.md`. La evidencia
concreta —qué fichero y qué línea— está en el §2 del acta.
