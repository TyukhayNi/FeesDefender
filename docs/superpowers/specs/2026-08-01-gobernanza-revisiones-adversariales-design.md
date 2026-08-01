# Gobernanza de las revisiones adversariales — población, hogar y formato

> **Estado:** **rev. 3** (2026-08-01), tras **dos** revisiones adversariales de Codex, ambas
> NO-SHIP: seis hallazgos en la rev. 1 y tres en la rev. 2, los nueve confirmados. Adjudicaciones
> en §14 y §15; informes literales en
> `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review.md`.
> **Objeto:** cómo se documenta y se audita la revisión adversarial en este proyecto — sus cuatro
> clases, no solo el intercambio con Codex.
> **Origen:** pregunta de Nikolai (2026-08-01) sobre si el «diálogo interno» necesita documentarse,
> cómo se estructura y cómo puede auditarse. **Alcance ampliado por decisión suya** el mismo día:
> gobernar las cuatro clases de revisión, no solo la que produce informe externo.

## 1. La población

No hay diálogo: hay un intercambio de dos turnos con bus humano. Claude escribe el objeto → se
encarga la revisión → el revisor ataca y entrega hallazgos → Claude adjudica contra la fuente. Lo
que se parece a diálogo son las **rondas**.

La rev. 2 definió cómo distinguir dos revisiones y **nunca dijo qué cuenta como revisión**. De ahí
salieron sus tres defectos en cadena. Se arregla en el orden correcto: primero quién entra, después
qué rastro deja, y solo entonces cuántas hay.

### 1.1 Predicado de inclusión

> Un proceso pertenece a la población si **(a)** su propósito declarado es **refutar** un artefacto
> del proyecto —spec, plan, diff o rama—, y **(b)** produce hallazgos o veredicto.

No exige que alguien lo haya adjudicado: una revisión sin adjudicar es precisamente el caso que hay
que poder ver. **Quedan fuera**, y se declara: el `code-review` de rutina sin veredicto adversarial,
la revisión de estilo (`pase-de-estilo`), los tests automáticos y el brainstorming.

### 1.2 Las cuatro clases y la traza que se les exige

La práctica del proyecto tiene cuatro clases con rastros distintos. Exigirles el mismo artefacto
sería absurdo en un sentido —siete actas para un build de siete tareas— y insuficiente en otro: la
revisión de rama del bundle por hilo encontró **tres caminos de pérdida de datos**
(`PLAN.md:757-761`) y no tiene hoy ni un encabezado. La traza se **gradúa**:

| Clase | Qué es | Informe externo | Traza exigida |
|---|---|---|---|
| **A — diseño con informe** | spec o plan atacado por un revisor externo que entrega informe | Sí | **Acta** (informe literal + `sha256`) **+** encabezado canónico **+** ficha |
| **B — rama o diff** | revisión del build completo antes del PR | A veces | Encabezado **+** ficha en el plan; acta **solo** si hubo informe externo |
| **C — por tarea** | revisiones dentro de un build con subagentes | No | **Agregada**: cuenta como **una** revisión de clase B, con `ronda: por-tarea (N)`. Nunca N encabezados |
| **D — autorrevisión** | pasada propia de Claude sobre su propio objeto | No | Encabezado **+** ficha con `Revisor: Claude (no independiente)`; sin acta |

La agregación de la clase C no es un atajo: una revisión por tarea no produce veredicto sobre el
objeto, sino sobre una porción en construcción. Lo que se adjudica es el resultado de la rama.

### 1.3 Identidad

> Una **revisión** es la tupla **`(objeto, commit o rev. del objeto, ronda, revisor, fecha de
> entrega)`**, con su **clase**.

Consecuencias, verificadas sobre el corpus:

- El acta dual y el §20 de su spec **son la misma revisión** en dos hogares.
- `handoff-…-codex-informe.md` y `…-review.md` son informe completo y resumen de la **misma**
  primera pasada; `…-review-2.md` es otra ronda. Codex lo confirmó en la 2ª pasada.
- El acta de emails declara una «segunda revisión, independiente»: **son dos**, aunque una sola
  adjudicación las consuma.
- Las tres pasadas sobre el plan de la Fase 0 son **tres revisiones**.
- Un objeto revisado por Codex **y** por Claude en la misma ronda son **dos revisiones**. La rev. 2
  escribió esta regla y la incumplió en la fila 4 de su propia tabla: el acta de cableado agrupa
  «Codex + Claude» como una. Corregido.

### 1.4 Corte temporal

**Se migra desde el 2026-07-23**, primera acta y arranque de hecho del contrato con Codex. Antes de
esa fecha hubo revisiones adjudicadas —`PLAN.md:924-928`, `:933`, `:953`, `:1033-1044`— que **quedan
fuera de alcance y se declaran aquí**: no había contrato de revisor estable, no hay informe que
archivar, y reconstruir la tupla desde párrafos fingiría exactitud. `PLAN.md` sigue siendo su
registro. Codex confirmó el corte como frontera defendible, y señaló —con razón— que **no amnistía
nada**: todas las omisiones de su H-01 son posteriores.

### 1.5 La cardinalidad no se publica aquí

La rev. 1 dijo «≥15». La rev. 2 dijo 16 y era falso: Codex documentó **al menos 24** con evidencia
en `docs/bitacora/2026.md:70,138,144,150` y `PLAN.md:383-386,757-768` — revisiones de rama de
bundle, cableado, enumeración recursiva e historial citado, más una autorrevisión de OCR, todas
postcorte.

Publicar una tercera cifra sin haber aplicado el predicado sería el mismo error por tercera vez.
**El censo definitivo lo produce la migración** (§9), aplicando §1.1 y §1.2 fuente por fuente, y no
se publica ninguna cardinalidad hasta poder explicar cada inclusión y cada exclusión con la misma
regla. Es el remedio que exigió Codex, literal.

### 1.6 Por qué está disperso

- `CLAUDE.md` dice que la adjudicación «se registra en el spec **o** el plan». Ese «o» es la
  dispersión escrita como norma.
- `GOBERNANZA_FUENTES_VERDAD.md` §5 añade una partición ortogonal —informe de fuera → handoff; acta
  de dentro → junto al spec— y un evento de revisión es las dos cosas, así que se parte en dos
  ficheros.
- Solo **14 de 53** specs y **14 de 62** planes llevan frontmatter: exigirlo son 87 ficheros de
  migración. **Descartado.**

## 2. Qué se corrige y qué no

**En alcance:** el predicado de población y sus cuatro clases; la traza graduada; el hogar de cada
artefacto; un formato de adjudicación parseable; el archivo verificable del informe recibido; dos
guards; y la migración que produce el censo.

**Fuera de alcance, explícitamente:**

- Exigir que todo spec o plan tenga revisión. El guard no juzga si algo debió revisarse.
- Un registro central versionado y su guard G9. Descartados en la rev. 2.
- **`scripts/censo_revisiones.py`.** Diferido en la rev. 3 (§7).
- Automatizar el puente con el revisor: sigue siendo manual y mediado por Nikolai.
- Frontmatter en specs y planes.
- Revisiones anteriores al 2026-07-23 (§1.4).
- Cambiar quién adjudica. Claude sigue siendo el juez; esto existe para que ese juicio sea
  contrastable.

## 3. Modelo: cuatro artefactos

| Artefacto | Hogar | Obligatorio en |
|---|---|---|
| **Mandato** (qué se pidió atacar) | El propio spec/plan, §«Revisión adversarial» previa | Recomendado en A y B |
| **Informe recibido**, literal + `sha256` | Acta hermana `…-adversarial-review.md` | **A**, y B cuando hubo informe |
| **Adjudicación** (veredicto + hallazgo → decisión → remedio) | Sección embebida en el spec/plan | **A, B, C-agregada y D** |
| **Cobertura** ausente | Ficha, campo `Cobertura` | Siempre que no se ejecutara |

La adjudicación se queda **embebida** porque la decisión pertenece al documento que la decisión
modificó, y quien lee el spec necesita saber qué sobrevivió al ataque sin abrir otro fichero. El
**acta** es el archivo de lo recibido de fuera, no un segundo hogar de la decisión.

La `cobertura` sube del cuerpo a la ficha: en la rev. 2 era prosa libre y por eso ningún lector
podía encontrarla — uno de los defectos que hundieron al generador.

## 4. Vocabularios cerrados

**`clase`** — `A-diseño` · `B-rama` · `C-por-tarea` · `D-autorrevisión`.

**`cobertura`** — `ejecutada` · `no-ejecutada`. Sin cobertura no hay veredicto (doctrina de
`docs/DEAD_ENDS.md`). `no-ejecutada` describe **un encargo que terminó sin sustituto y sin
adjudicación**; un encargo fallido a un proveedor que otro revisor cubrió **no** lo es — los cuatro
fallos de `agy` son indisponibilidad de proveedor, y ese hecho vive en `DEAD_ENDS.md`.

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
aceptado **con un remedio distinto del exigido** cuenta como confirmado; la divergencia se razona en
la prosa. No se añade un sexto contador.

**Migración de tokens.** El corpus usa `resuelto`, `aplicados`, `NO EJECUTABLE` y
`LISTA CON CAMBIOS`. Se normalizan (§9); el veredicto literal queda en el acta.

> **Tercera población de vocabularios.** Estos ejes NO comparten set con `_ESTADOS_DOCS` ni con
> `_ESTADOS_HANDOFF`. La cabecera de `tests/test_docs_gobernanza.py` documenta por qué unificarlos
> rompe 11 ficheros (trampa D3). El campo se llama `estado_remediacion` y no `estado`: colisión
> imposible por construcción. Codex confirmó que la separación resiste.

## 5. Encabezado canónico, ficha y parser

```
## [N.] Adjudicación de la revisión adversarial [<calificador>] (<revisor>, <AAAA-MM-DD>) — <VEREDICTO>, <estado_remediacion>
```

El calificador opcional cubre `del PLAN` y `de rama completa`. Debajo, **ocho líneas**:

```markdown
- **Clase:** A-diseño | B-rama | C-por-tarea | D-autorrevisión
- **Objeto revisado:** `<ruta>` rev. N, commit `abc1234`
- **Ronda:** 1 | 2 | 3 | por-tarea (N)
- **Revisor:** Codex (solo lectura) | Claude (no independiente: autor del objeto)
- **Cobertura:** ejecutada | no-ejecutada — <motivo>
- **Informe recibido:** `<acta>.md` | sin informe (clase B/C/D) | no archivado (anterior a esta regla)
- **Hallazgos:** N confirmados · N rebajados · N refutados · N escalados · N sin verificar
- **Remediado en:** PR #NNN (`hash`) | rev. N de este documento | pendiente
```

`Ronda` y `Clase` entran porque son parte de la identidad (§1.3) y de la traza (§1.2), y sin ellas
ninguna lectura puede distinguir dos revisiones del mismo objeto por el mismo revisor el mismo día
— que es exactamente el caso de §14 y §15 de este documento.

Cuando el objeto es un diff, «Objeto revisado» admite `rama <nombre>` o `PR #NNN`.
`commit: no registrado` es legítimo al migrar: **no se inventa lo que no consta**.

### 5.1 El parser, especificado

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
encabezado que contenga «Adjudicación de la revisión»** y exige que case. Sin eso, un encabezado mal
formado no se detecta y pasa en silencio, que es el modo de fallo caro.

**Antes de cualquier match se eliminan los bloques cercados** (``` … ```). No es precaución teórica:
la plantilla de arriba, dentro de su cerca, fue detectada como encabezado real por el grep de censo
de la rev. 1. El defecto se observó, no se dedujo.

**Medición reproducida dos veces** (Claude y Codex, por separado, sobre `docs/superpowers/**/*.md`):
**9** disparadores fuera de cerca · **3** casan el regex bruto · **2** pasan además vocabulario
(`sandwich` §9 y el §14 de este spec) · **1** falla solo por token (`resuelto`) · **6** fallan
estructura.

## 6. El acta hermana

**Ubicación y nombre:** junto a su objeto —`specs/` o `plans/`— como
`AAAA-MM-DD-<tema>-adversarial-review.md`, con sufijo **`-rN` a partir de la segunda ronda**. Si el
objeto es un diff sin plan, junto al spec del que deriva; si no hay ninguno, en `specs/` con el
nombre del PR.

**Un acta por ronda, no por objeto.** Lo impone el propio frontmatter: `ronda`, `commit`, `veredicto`
y `sha256_informe` son escalares, así que un fichero no puede representar dos rondas sin volver al
defecto que Codex señaló en el generador. El acta heredada de emails, que contiene dos revisiones en
un solo fichero, es precisamente por eso `formato: hibrido-legacy`.

**Frontmatter obligatorio — identidad y procedencia del informe, más un puntero:**

```yaml
---
tipo: revision-adversarial
objeto: docs/superpowers/specs/<fichero>.md
objeto_rev: "1"
commit: 3126214
ronda: "1"
clase: A-diseño
revisor: Codex
cobertura: ejecutada
veredicto: NO-SHIP
sha256_informe: <hash del fichero recibido, en minusculas>
adjudicado_en: docs/superpowers/specs/<fichero>.md §14
---
```

`adjudicado_por` y `estado_remediacion` **no van aquí**: describen la decisión, y el segundo es
mutable. Si vivieran en el acta, cada remediación obligaría a sincronizar dos ficheros — el drift
que este diseño elimina. `veredicto` sí se queda: es inmutable.

**`sha256_informe` es la pieza que cierra el agujero de integridad.** El §1 del acta dice «informe
literal» y lo transcribe Claude, que es la parte revisada: nadie verificaba esa literalidad. Con el
hash, cualquiera la verifica en un comando contra la copia externa. Dos rutas independientes
llegaron a este remedio: el H-03 de la 2ª pasada, que exige a G8 comprobar la literalidad —
imposible sin algo contra lo que comparar—, y una observación de Nikolai por otra vía. Es además el
patrón de cadena de custodia que el repo ya usa en el intake.

> La copia externa del informe se conserva de forma duradera y con nombre por `(objeto, ronda)`.
> No es teoría: la 2ª pasada verificó **106/106 líneas literales** de la primera acta, y solo pudo
> hacerlo porque el original seguía disponible.

**Contenido, dos secciones:** **§1 Informe recibido, sin modificar** (literal, y se declara literal)
y **§2 Evidencia verificada** (qué abrió Claude para adjudicar, con ruta y línea). La adjudicación
**no** se repite aquí.

**Las cuatro actas heredadas** llevan `formato: hibrido-legacy`: nacieron con informe y adjudicación
en el mismo fichero, se les añade frontmatter y **no se les mueve nada**. El marcador es una
**allowlist cerrada de cuatro nombres**, no una categoría abierta: sin él, la exención se aplicaría
automáticamente a toda acta futura y crearía una clase permanente fuera de guard (H-03).

## 7. El censo: migración una vez, generador diferido

**No hay registro versionado** (rev. 2) y **no se escribe el generador** (rev. 3).

La rev. 2 especificó `scripts/censo_revisiones.py` como lector de encabezados y actas. No podía
funcionar, y la razón no es de gusto: sus columnas pedían `ronda` y `cobertura`, y **ninguna de las
dos existía en la ficha**; un acta con dos revisiones no cabe en un frontmatter escalar; y la 2ª
pasada de vista procesal solo vive en un handoff, población que el lector no recorría. Habría
necesitado excepciones a mano — el ledger escondido dentro de Python. Además tenía **cero
consumidores** fuera de su propio criterio de aceptación.

La rev. 3 aplica la secuencia correcta, que es la que exigió Codex: **primero representable,
después legible.**

1. La ficha (§5) y el frontmatter (§6) pasan a contener `clase`, `ronda`, `cobertura` y `sha256`.
   Con eso cada revisión de la población es representable y la relación revisión ↔ artefacto es
   uno-a-uno para todo lo nuevo.
2. La **migración** (§9) produce el censo **una vez**, a mano, aplicando el predicado §1.1 fuente
   por fuente. Es reconstrucción histórica, no automatización.
3. El generador se escribe **cuando exista un consumidor real** —cierre de sesión, runbook o
   petición concreta— y no antes. Precondición declarada: fichas uniformes en toda la población
   postcorte.

Auditar el proceso, mientras tanto, es leer los artefactos: cada revisión lleva su clase, su ronda,
su cobertura, su veredicto, su recuento y su remedio en un encabezado con formato fijo.

## 8. Guards

Dos tests nuevos en `tests/test_docs_gobernanza.py`, **población separada** con vocabulario propio,
según la disciplina que impone la cabecera de ese fichero.

**G7 — adjudicación bien formada.** Toda línea de encabezado que contenga «Adjudicación de la
revisión», fuera de bloques cercados, casa `_RE_ADJUDICACION` con `veredicto` y `estado_remediacion`
de los sets del §4, y va seguida de las ocho líneas de la ficha con `clase`, `ronda` y `cobertura`
de vocabulario válido. Los ficheros con `tipo: revision-adversarial` quedan fuera: el informe
literal puede contener cualquier encabezado y no debe reinterpretarse como adjudicación del
proyecto.

**G8 — acta bien formada.** Reforzado respecto a la rev. 2, que solo miraba el frontmatter:

- frontmatter con las claves del §6 y vocabulario válido;
- `adjudicado_en` apunta a un fichero **y a una sección que existen** — no solo al fichero;
- `sha256_informe` presente cuando `cobertura: ejecutada`;
- para toda acta **sin** `formato: hibrido-legacy`: existen las dos secciones del §6, y la §1
  contiene el bloque literal;
- `formato: hibrido-legacy` solo se admite en los **cuatro nombres de la allowlist**.

**Anti-automatch:** el corpus de G7 incluye este mismo spec. Si vuelve a detectar la plantilla del
§5 dentro de su cerca, G7 falla. Es el test de regresión del defecto de la 1ª pasada.

**Lo que los guards NO hacen:** no exigen que un spec tenga revisión; no tocan `_ESTADOS_DOCS` ni
`_ESTADOS_HANDOFF` ni vuelven recursivo el glob de `_docs_con_frontmatter`; no piden frontmatter a
specs ni a planes; no juzgan el contenido de la adjudicación. **No hay G9.**

## 9. Migración

Es la parte grande, y con el alcance ampliado crece: la rev. 2 la medía en ocho encabezados y ahora
son ocho más las revisiones que Codex documentó, cada una a verificar en su fuente.

**Retrofit declarado de siete de ocho encabezados.** El formato casa hoy **1 de 8**. La rev. 1
afirmaba que «formaliza la línea que ya se escribe sola»: era falso — converge la forma, no los
tokens. Se elige el retrofit —siete ediciones, una vez— frente a un parser permisivo permanente,
cuya complejidad se paga siempre. Coste reconocido, no escondido en un «normalizar»:

| Sección | Grado | Qué falta |
|---|---|---|
| sandwich spec §9 | **casa** | nada |
| email enumeración §11 | **solo token** | `resuelto` → `remediado` |
| historial §10-bis | estructura | `NO EJECUTABLE` → `NO-EJECUTABLE` |
| sandwich plan §1061 | estructura | `NO EJECUTABLE` → `NO-EJECUTABLE` |
| cableado plan | estructura | `veredicto ` sobra; `del PLAN` pasa a calificador |
| vista procesal §10 | estructura | revisor, fecha, veredicto y estado (de sus handoffs) |
| dual workspace §20 | estructura | todo salvo `(rev. 2)`; se toma del acta |
| rama completa §1089 | estructura | falta «adversarial» y revisor; `LISTA CON CAMBIOS` → `LISTA-CON-CAMBIOS`; `aplicados` → `remediado` |

Los ocho llevan además la ficha de ocho líneas.

**Revisiones sin encabezado, a reconstruir y censar** — con su fuente, todas postcorte:

| Revisión | Clase | Fuente |
|---|---|---|
| Fase 0 dual, rondas 1, 2 y 3 | A | `PLAN.md:587,595`, bitácora, PR #166 |
| Cableado atomize: pasada propia de Claude sobre la spec | D | acta de cableado `:3-6` |
| Bundle por hilo: revisión final de rama | B | `PLAN.md:757-761`, `bitácora:150` |
| Cableado atomize: revisión de rama | B | `bitácora:138` |
| Cableado atomize: revisiones por tarea (7) | C, agregada en la anterior | `bitácora:138` |
| Enumeración recursiva: plan y rama | B | `bitácora:134`, `PLAN.md:383-386` |
| Historial citado: plan y rama | B | `bitácora:62,70` |
| OCR ciego: autorrevisión sobre el diff | D | `bitácora:144` |

**Cuatro actas heredadas** — frontmatter + `formato: hibrido-legacy`, sin mover su adjudicación.

**Los tres handoffs `…-codex-*`** se quedan, declarados **excepción histórica** en la gobernanza §5,
igual que `prompt_handoff_expedientes_seguros.md`: su contenido encaja con el papel nuevo del acta,
pero moverlos rompe G6 y los `consumido_por` que los citan.

**Informes crudos anteriores a esta regla:** perdidos, iban a `%TEMP%` con nombre fijo. La ficha lo
dirá: `no archivado (anterior a esta regla)`, y su `sha256_informe` se omite. Se declara, no se
disimula.

## 10. Doctrina a modificar

| Documento | Cambio |
|---|---|
| `CLAUDE.md` §Revisión adversarial | Resolver el «o»; las cuatro clases y su traza; acta siempre que haya informe |
| `AGENTS.md` | Hallazgos `H-NN`; informe archivable literal; **ruta estable por `(objeto, ronda)`**, no nombre fijo; qué significa «solo lectura» cuando el revisor ejecuta tests |
| `docs/GOBERNANZA_FUENTES_VERDAD.md` §5 | El acta es el hogar del informe recibido; excepción histórica de los tres `codex-*` |
| `tests/test_docs_gobernanza.py` | Cabecera: tercera población de vocabularios |

`docs/INDICE.md` **no** se toca: sin registro versionado no hay documento nuevo de raíz, y su
`:23-28` excluye deliberadamente los specs fechados.

## 11. Riesgos

- **G7 y G8 son parsers de prosa.** Acotados a encabezado con frase fija, ocho líneas con prefijo
  `- **Campo:**` y eliminación previa de cercas. Si resultan ruidosos, la salida es relajar el
  regex, no borrar el campo.
- **La migración es el 80 % del trabajo** y toca ocho documentos vivos más una decena de
  reconstrucciones desde bitácora y PLAN. Es donde puede morir el cambio por agotamiento; el plan
  debe trocearla en PRs por clase, no en uno.
- **La clase C puede volverse coladero.** Agregar siete revisiones por tarea en una es proporcionado
  hoy; si un build llega a treinta tareas con hallazgos sustantivos, la agregación oculta. Señal de
  revisión: cuando una revisión por tarea produzca un veredicto sobre el objeto y no sobre su
  porción.
- **Coste por revisión.** Sube: un acta y una ficha de ocho líneas. Compra lo que no existe — poder
  auditar la adjudicación contra lo que el revisor dijo de verdad, ahora con hash.

## 12. Criterios de aceptación

1. `python -m pytest -q --tb=no` verde, con G7 y G8 incluidos.
2. Los ocho encabezados casan G7 tras el retrofit; las cuatro actas heredadas casan G8 con
   `formato: hibrido-legacy`.
3. G7 corre sobre este spec y **no** detecta la plantilla del §5.
4. G8 rechaza un acta nueva con frontmatter válido y cuerpo vacío, y una cuyo `adjudicado_en`
   apunte a una sección inexistente.
5. Toda revisión de la población postcorte tiene encabezado y ficha, con su clase y su ronda.
6. Cada revisión es **representable**: clase, ronda, revisor, cobertura, veredicto, recuento,
   informe y remedio constan en un artefacto de formato fijo. *(Reformulado en la rev. 3: la
   promesa no es «un comando» sino «el dato está y es parseable»; el generador se difiere hasta que
   haya consumidor.)*
7. No existe `docs/REVISIONES_ADVERSARIALES.md`, ni G9, ni `scripts/censo_revisiones.py`.
8. Ninguna población de vocabulario existente se ha tocado.

## 13. Mandato para una eventual tercera pasada

1. **El predicado del §1.1 contra el corpus postcorte.** ¿Deja fuera algo que la práctica trata
   como revisión, o mete algo que nadie llamaría así? Candidato: los paneles «4 lentes».
2. **La agregación de la clase C.** ¿Es proporcionada o es el coladero del §11? ¿Qué se pierde al no
   dar encabezado a una revisión por tarea que encontró un defecto real?
3. **La traza graduada del §1.2.** ¿Exigir acta solo en A y en B-con-informe deja sin rastro
   verificable las revisiones de rama que más defectos han comprado?
4. **G8 reforzado.** ¿Puede verificar «el informe es literal» con solo el hash, si la copia externa
   se pierde? ¿Y qué hace G8 cuando `sha256_informe` no cuadra: rojo, o aviso?
5. **El diferimiento del generador.** ¿Es la decisión correcta, o «representable» es una promesa que
   nadie cobrará nunca?
6. **La migración del §9.** ¿Es ejecutable en PRs por clase, o hay dependencias entre clases que la
   obligan a ser un solo PR gigante?

## 14. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Clase:** A-diseño
- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 1, commit `3126214`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review.md`
- **Hallazgos:** 6 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento

| Hallazgo | Severidad | Veredicto | Dónde se remedia |
|---|---|---|---|
| H-01 censo sin identidad; omite precedentes de `PLAN.md` | CRÍTICA | **Confirmado** | §1.3, §1.4 |
| H-02 los cuatro de `DEAD_ENDS` no son cobertura ausente | ALTA | **Confirmado** | §4, definición de `no-ejecutada` |
| H-03 G7 casa 1/8 y se autodetecta en la cerca | ALTA | **Confirmado** | §5.1, §9, §12.3 |
| H-04 el registro central sobra | ALTA | **Confirmado, remedio acotado** | §7 |
| H-05 G9 rechaza las filas `no-ejecutada` | ALTA | **Confirmado** | Disuelto al retirar G9 |
| H-06 el frontmatter invade el hogar de la decisión | MEDIA | **Confirmado** | §6 |

**Divergencia sobre H-04, y su desenlace.** Acepté el hallazgo y retiré la tabla y G9, pero rechacé
suprimir los criterios 2 y 6 y añadí un generador. La 2ª pasada demostró que la divergencia fue
**medio equivocada**: acerté conservando el objetivo —Codex concede que el criterio 2 debía
quedarse— y me equivoqué al materializarlo ya como script. Queda como aviso: conservar el objetivo
de un encargo frente a un remedio que se lo lleva por delante es correcto; elegir de inmediato la
implementación que lo sustituye, no.

**Refutado a favor del spec:** el §13.4 de la rev. 1 temía un ciclo entre G9 y G2. No existe: crear
acta y referencia en el mismo cambio es atómico. La preocupación era infundada.

## 15. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Clase:** A-diseño
- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 2, commit `2c2a6d0`
- **Ronda:** 2
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review-r2.md`
- **Hallazgos:** 3 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 3 de este documento

| Hallazgo | Severidad | Veredicto | Dónde se remedia |
|---|---|---|---|
| H-01 el censo da ≥24, no 16; falta el predicado de inclusión | CRÍTICA | **Confirmado** | §1.1 (predicado), §1.2 (clases), §1.5 (no se publica cifra), §9 |
| H-02 el generador no puede derivar y no tiene consumidor | ALTA | **Confirmado** | §7 (diferido), §5 (`ronda`/`cobertura` en la ficha), §12.6 |
| H-03 G8 no verifica el cuerpo del §6; exención global | ALTA | **Confirmado** | §6 (`formato: hibrido-legacy`, allowlist), §8 (G8 reforzado), §12.4 |

**Cómo se verificó.** H-02 y H-03 son autoevidentes dentro del propio documento: la rev. 2 pedía una
columna `ronda` que su ficha no tenía, y su G8 no comprobaba ninguno de los cuatro mandatos
corporales del §6. H-01 se contrastó contra la fuente: `bitácora:150` («spec → **dos** revisiones
adversariales → … → **revisión final** → merge»), `PLAN.md:757-761` (la revisión final encontró tres
caminos de pérdida), `bitácora:138` («revisión por tarea + revisión de rama»), `bitácora:70` («la del
plan devolvió NO EJECUTABLE y la de la rama construida otro, con dos defectos vivos»).

**Contradicción propia que el hallazgo destapó:** la rev. 2 escribió en §1.1 que Codex y Claude se
cuentan como dos revisiones y agrupó «Codex + Claude» como una en la fila 4 de la tabla siguiente.

**Lo que resistió, medido por ambos por separado:** el regex y el desglose del retrofit (9/3/2/1/6);
que las filas 1-2 y 6-7 son dos revisiones cada una; el corte del 23 de julio como frontera de
migración; la retirada del registro y de G9 frente a «un hecho → un hogar»; no tocar `INDICE.md`; y
la corrección sobre `DEAD_ENDS`. La primera acta **cumple su propio §6**: 106/106 líneas literales.

**Decisión de alcance de Nikolai, contra mi recomendación.** Recomendé estrechar la población a las
revisiones con informe externo. Decidió gobernar las cuatro clases, con la cardinalidad completa.
Queda registrado: la rev. 3 lo implementa entero, y el coste está en el §11 —la migración es el 80 %
del trabajo— y en el §9, que la trocea por clase.
