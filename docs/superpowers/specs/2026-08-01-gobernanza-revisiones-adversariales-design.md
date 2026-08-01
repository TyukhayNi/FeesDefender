# Gobernanza de las revisiones adversariales — población, hogar y formato

> **Estado:** **rev. 6** (2026-08-01), tras **cuatro** revisiones adversariales de Codex:
> NO-SHIP (6) → NO-SHIP (3) → LISTA-CON-CAMBIOS (7) → **NO-SHIP (8)**. **24 hallazgos, 24
> confirmados, ninguno refutado.** Adjudicaciones en §14-§17; informes literales en las cuatro actas
> `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review*.md`.
> **Objeto:** cómo se documenta y se audita la revisión adversarial en este proyecto.
> **Origen:** pregunta de Nikolai (2026-08-01) sobre si el «diálogo interno» necesita documentarse,
> cómo se estructura y cómo puede auditarse.
>
> **Nota de forma de la rev. 6.** Es más corta que la rev. 5 a propósito. El patrón de las cuatro
> rondas fue estable: cada remediación cerraba su defecto y abría otro **en la costura de al lado**,
> casi siempre porque la prosa restataba una regla con palabras distintas en dos sitios. La rev. 6
> **dice cada regla una vez**; la narración de por qué cambió vive en las adjudicaciones §14-§17 y en
> las actas.

## 1. La población

No hay diálogo: hay un intercambio de dos turnos con bus humano. Claude escribe el objeto → se encarga
la revisión → el revisor ataca y entrega hallazgos → Claude adjudica contra la fuente. Lo que se parece
a diálogo son las **rondas**.

### 1.1 Predicado de inclusión

> **Prospectivo.** Un proceso pertenece a la población cuando **el encargo lo declara expresamente
> revisión adversarial**, nombrando **el objeto** y **el gate** que debe satisfacer, y produce
> hallazgos o veredicto.

La pertenencia se decide por **lo que se encargó**, no por la forma del resultado. La rev. 5 la hacía
depender de que el proceso «atacara un artefacto» y produjera «hallazgos o veredicto», y con eso
entraba cualquier `code-review` y cualquier comprobación por tarea.

**Excluidos por definición**, no por etiqueta:

- **Las comprobaciones subordinadas por tarea** de un build. Revisan un **fragmento en construcción**,
  no el objeto, y no pueden satisfacer su gate. Sus respuestas recuperables se **incorporan o enlazan,
  con autor y hash**, en el informe consolidado de la revisión de rama. Si se quiere que una cuente,
  necesita **su propia identidad y su acta**: no puede entrar en la población y desaparecer del censo.
- El `code-review` de rutina, `pase-de-estilo`, los tests automáticos y el brainstorming: su encargo no
  las declara revisión adversarial.

**Retrospectivo (solo migración).** Para lo anterior a la regla se aplica una heurística: lo que el
proyecto trató como revisión adversarial, según el inventario del plan de migración. Es una heurística
de reconstrucción, no el predicado.

**Adjudicador.** Claude por defecto (`CLAUDE.md`); puede ser Nikolai. Cuando no sea Claude, se dice en
la prosa de la adjudicación. **La independencia no se mide contra el adjudicador** (§1.2).

### 1.2 Dos ejes: qué se revisó y quién lo revisó

La rev. 5 los mezclaba en un solo campo, y por eso una pasada propia sobre un spec podía etiquetarse
honestamente `diseño` y reclamar cobertura.

| Eje | Campo | Valores |
|---|---|---|
| **Qué se revisó** | `clase` | `diseño` (spec, plan, diagnóstico, handoff) · `rama` (diff o rama completa) |
| **Quién lo revisó** | `independencia` | `independiente` · `autor` |

**`independencia` se mide contra el autor del objeto**, no contra el adjudicador. Claude revisando su
propio spec es `autor` aunque adjudique Nikolai. Codex revisando un objeto de Claude es `independiente`
aunque adjudique Claude.

**La cobertura de la revisión obligatoria de `CLAUDE.md` la acredita solo una revisión con
`independencia: independiente`.** Una de `autor` se registra —entra en la población, lleva encabezado y
ficha— y **no satisface el gate**.

### 1.3 Traza exigida, y por qué es fail-closed

**Acta obligatoria para toda revisión de la población que haya producido respuesta textual
recuperable**, sea Codex, un Opus de otra sesión o un subagente. Lo que se conserva es la **voz del
revisor**, y eso no depende del eje ni del proveedor.

> **`cobertura: ejecutada` exige que `Informe recibido` resuelva a un acta existente y válida.** Sin
> acta no hay cobertura: la revisión **no es adjudicable** y el gate queda sin satisfacer.

`no capturado` **no es un valor de uso corriente**: solo se admite para el corpus anterior a esta regla,
por **lista cerrada** en el guard. En un encargo nuevo, perder el informe obliga a **repetir la
revisión**. La rev. 5 lo llamaba «defecto de proceso declarado» sin asignarle consecuencia, que es la
forma exacta en que una excepción visible se convierte en la vía normal.

Para que eso sea cumplible, **el encargo fija la ruta de destino antes de empezar y exige que el
revisor devuelva `ruta + sha256` antes de que se adjudique** (§10.1.5). Es lo que hace que la prueba de
origen no dependa de que el autor calcule los dos lados.

### 1.4 Identidad

> Una **revisión** es la tupla **`(objeto, commit o rev. del objeto, ronda, revisor, fecha de
> entrega)`**, con su `clase` y su `independencia`.

- El acta dual y el §20 de su spec son **la misma** revisión en dos hogares.
- `handoff-…-codex-informe.md` y `…-review.md` son dos formatos de la **misma** primera pasada;
  `…-review-2.md` es otra ronda.
- El acta de emails declara una «segunda revisión, independiente»: **son dos**.
- Las tres pasadas sobre el plan de la Fase 0 son **tres**.
- Dos revisores del mismo objeto y ronda son **dos**.
- Un panel con orquestador y subagentes en paralelo es **una** si hubo mandato único y veredicto
  consolidado: sus lentes son metodología.

### 1.5 Corte temporal y cardinalidad

**Se migra desde el 2026-07-23**, primera acta y arranque de hecho del contrato con Codex. Lo anterior
—`PLAN.md:924-928`, `:933`, `:953`, `:1033-1044`— **queda fuera de alcance y se declara aquí**: no había
contrato de revisor estable, no hay informe que archivar, y reconstruir la tupla desde párrafos
fingiría exactitud. El corte **no amnistía nada**: todas las omisiones detectadas en las cuatro rondas
son posteriores.

**Aquí no se publica ninguna cardinalidad.** El censo, con una fila por identidad, lo produce el plan
de migración. La rev. 1 dijo «≥15» y la rev. 2 dijo 16; ambas eran falsas.

## 2. Alcance

**Dentro:** el predicado; los dos ejes; la traza fail-closed; el hogar de cada artefacto; un formato de
adjudicación parseable; el archivo verificable del informe; dos guards; la política de migración; y la
regla de parada.

**Fuera, explícitamente:** exigir que todo objeto tenga revisión (el guard no juzga eso); un registro
central versionado y G9; `scripts/censo_revisiones.py`; el inventario y las tareas de migración, que
viven en su plan; automatizar el puente con el revisor; frontmatter en specs y planes; las revisiones
anteriores al corte; cambiar quién adjudica; y **una cadena de custodia resistente al administrador del
repo** (§6.1).

## 3. Los cuatro artefactos

| Artefacto | Hogar | Obligatorio |
|---|---|---|
| **Mandato** | Acta §0, o puntero `mandato:` a `<ruta> §N` del objeto en su commit | **Sí** |
| **Informe recibido**, canonicalizado + digest | Acta, §1, entre marcadores con nonce | **Sí**, si hubo respuesta textual recuperable |
| **Adjudicación** | Sección embebida en el objeto | **Sí** |
| **Cobertura** | Ficha, campo `Cobertura` | **Sí** |

La adjudicación va **embebida** porque la decisión pertenece al documento que la decisión modificó. El
acta es el archivo de la voz del revisor, **no** un segundo hogar de la decisión: no lleva
`adjudicado_por` ni `estado_remediacion`.

## 4. Vocabularios cerrados

`clase` — `diseño` · `rama`.
`independencia` — `independiente` · `autor`.
`cobertura` — `ejecutada` · `no-ejecutada`, con matiz libre entre paréntesis.
`estado_remediacion` — `remediado` · `parcial` · `sin-cambios` · `pendiente`.

`veredicto`:

| Valor | Significado |
|---|---|
| `SHIP` | Sin bloqueantes. |
| `LISTA-CON-CAMBIOS` | Se acepta aplicando cambios acotados. |
| `REQUIERE-REVISION` | Necesita reescritura antes de avanzar. |
| `NO-SHIP` | Bloqueante. |
| `NO-EJECUTABLE` | No se puede ejecutar ni verificar tal como está. |
| `SIN-VEREDICTO` | El revisor no se pronunció globalmente. |

**Recuento** — `confirmados · rebajados · refutados · escalados · sin-verificar`. Un hallazgo aceptado
con **remedio distinto** del exigido cuenta como confirmado; la divergencia se razona en la prosa.

`no-ejecutada` describe **un encargo que terminó sin sustituto y sin adjudicación**. Un encargo fallido
a un proveedor que otro revisor cubrió **no** lo es: los cuatro fallos de `agy` son indisponibilidad de
proveedor y ese hecho vive en `docs/DEAD_ENDS.md`.

**Migración de tokens.** El corpus usa `resuelto`, `aplicados`, `NO EJECUTABLE` y `LISTA CON CAMBIOS`;
se normalizan. El veredicto literal queda en el acta.

> **Tercera población de vocabularios.** No comparte set con `_ESTADOS_DOCS` ni con
> `_ESTADOS_HANDOFF`. La cabecera de `tests/test_docs_gobernanza.py` documenta por qué unificarlos rompe
> 11 ficheros (trampa D3). El campo se llama `estado_remediacion` y no `estado`: colisión imposible por
> construcción.

## 5. Encabezado canónico y ficha

```
## [N.] Adjudicación de la revisión adversarial [<calificador>] (<revisor>, <AAAA-MM-DD>) — <VEREDICTO>, <estado_remediacion>
```

Calificador opcional: `del PLAN`, `de rama completa`. Debajo, **nueve líneas**:

```markdown
- **Clase:** diseño | rama
- **Independencia:** independiente | autor
- **Objeto revisado:** `<ruta>` rev. N, commit `abc1234`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada | no-ejecutada — <motivo>
- **Informe recibido:** `<acta>.md` | sin informe (revisión del autor) | no capturado (excepción histórica cerrada)
- **Hallazgos:** N confirmados · N rebajados · N refutados · N escalados · N sin verificar
- **Remediado en:** PR #NNN (`hash`) | rev. N de este documento | pendiente
```

Cuando el objeto es un diff, «Objeto revisado» admite `rama <nombre>` o `PR #NNN`. `commit: no
registrado` es legítimo al migrar: **no se inventa lo que no consta**.

### 5.1 El parser

```python
_RE_ADJUDICACION = re.compile(
    r"^#{2,3}\s+(?:\S+\s+)?"                       # ## o ###, numeracion opcional (10., 10-bis.)
    r"Adjudicación de la revisión adversarial"
    r"[^(\n]*"                                     # calificador: "del PLAN", "de rama completa"
    r"\((?P<revisor>[^,)]+),\s*(?P<fecha>\d{4}-\d{2}-\d{2})\)"
    r"\s*—\s*(?P<veredicto>[A-Z-]+),\s*(?P<estado>[a-z-]+)\s*$",
    re.MULTILINE)
```

**Disparador:** el guard busca **toda línea de encabezado que contenga «Adjudicación de la revisión»** y
exige que case. Sin eso, un encabezado mal formado pasa en silencio.

**Bloques cercados:** se eliminan **antes** de cualquier match. La plantilla de arriba, dentro de su
cerca, fue detectada como encabezado real por el grep de censo de la rev. 1.

**La medición no vive en esta prosa.** El **corpus legacy es estable** hasta la migración: **ocho**
encabezados, de los que **1 casa**, **1 falla solo por token** (`resuelto`) y **6 fallan estructura** —
reproducido por Claude y por Codex por separado. Los **totales vivos** se fijan en el **fixture de G7**,
porque cada adjudicación nueva los mueve y el guard es lo que debe notarlo.

## 6. El acta

**Nombre**, función inmutable de la identidad:

```
AAAA-MM-DD-<tema>-<objeto>-r<N>-<revisor>-<commit7>-adversarial-review.md
```

`<objeto>` ∈ `spec` · `plan` · `diagnostico` · `handoff` · `rama` · `diff`. **Revisor y commit van
siempre**, no solo al colisionar: si se omiten hasta que aparece un segundo revisor, la primera acta hay
que renombrarla y se rompen los punteros ya escritos. Si el objeto es un diff sin plan, el acta va junto
al spec del que deriva; si no hay ninguno, en `specs/`.

**Un acta por ronda.** El frontmatter es escalar; el acta heredada de emails, que contiene dos
revisiones, es por eso `formato: hibrido-legacy`.

> Las cuatro actas de este spec conservan nombres anteriores a este esquema hasta que el plan de
> migración las renombre. No colisionan entre sí.

**Frontmatter:**

```yaml
---
tipo: revision-adversarial
objeto: docs/superpowers/specs/<fichero>.md
objeto_rev: "1"
commit: abc1234
ronda: "1"
clase: diseño
independencia: independiente
revisor: Codex
cobertura: ejecutada
veredicto: NO-SHIP
mandato: §0 de este acta | docs/…/<fichero>.md §13
marcador_nonce: zx7q
sha256_informe: <digest canonico, 64 hex>
sha256_recibido: <opcional: digest del fichero tal como llego, si difiere del canonico>
adjudicado_en: docs/superpowers/specs/<fichero>.md §14
---
```

**Contenido, tres secciones.** **§0 Mandato** —qué se pidió atacar, numerado y en su orden de daño—
salvo que `mandato:` apunte al objeto. Sin él, quien lea el acta no puede distinguir **si el revisor
pasó algo por alto o si nunca se le pidió**. **§1 Informe recibido, sin modificar.** **§2 Evidencia
verificada** por Claude al adjudicar, con ruta y línea. La adjudicación **no** se repite aquí.

**Marcadores con nonce**, obligatorios:

```
<!-- informe-literal:inicio:<nonce> -->
…el informe…
<!-- informe-literal:fin:<nonce> -->
```

El nonce se declara en `marcador_nonce` y **se elige de modo que no aparezca en el informe**;
conviene que lleve letras **no hexadecimales**, porque un informe sobre este contrato cita digests y un
nonce hexadecimal puede esconderse dentro de uno. No es teoría: el informe de la ronda 4 **contiene el
token de fin**, y con los marcadores planos de la rev. 5 su archivado se habría cortado por la mitad.
G8 exige **exactamente un par** con ese nonce y en orden.

### 6.1 Integridad: una sola semántica, y su frontera de confianza

**`sha256_informe` es el digest del texto canonicalizado** del informe: UTF-8, finales `LF`, un único
salto final. **La misma forma al recibir y en G8.** La rev. 5 definía el digest sobre «el fichero
recibido» y hacía que G8 recomputase otro objeto: un informe con CRLF —el caso natural en Windows— no
podía satisfacer ambas reglas ni con una transcripción perfecta. Se abandona «fichero» y «byte a byte»:
lo que se conserva y se hashea es **el texto**.

Cuando el fichero tal como llegó difiere del canónico, su digest se anota además en
`sha256_recibido`. Así la **prueba independiente de origen** sobrevive sin romper la comprobación
automática.

**Verificación al recibir, obligatoria.** Claude calcula el digest canónico de la copia externa al
archivarla y lo compara con el que declara el revisor (§1.3). Ese es el único momento en que existe
prueba independiente de origen. Después, el acta se autoverifica: recomputar el bloque detecta
cualquier alteración posterior aunque la copia externa desaparezca.

**Frontera de confianza, declarada.** G8 detecta que alteren **el bloque**. Una edición coordinada de
bloque **y** digest pasa verde, y lo que la delata es el diff del commit. Pero **eso no es
inmutabilidad**: `STATUS.md:6` documenta que **el historial de git fue reescrito y el repo recreado el
2026-07-07**, sin ancestro común. El supuesto «append-only» es una **política revocable por quien
administra el repo**, no una propiedad del sistema. Por tanto la garantía real es: **consistente bajo el
historial Git retenido**. Resistencia frente al administrador exigiría un ancla fuera de ese historial
—tag firmado o publicación externa del digest— y **no se construye**: se declara el límite.

**Las cuatro actas heredadas** llevan `formato: hibrido-legacy` con **allowlist cerrada de cuatro
nombres**, `sha256_informe: no-disponible-legacy` —token tipado, no omisión— y conservan su adjudicación
donde está.

## 7. El censo se calcula, no se mantiene

No hay registro versionado y **no se escribe el generador**. La rev. 2 lo especificó sobre artefactos que
no contenían sus columnas y sin ningún consumidor. Secuencia correcta: **primero representable, después
legible.**

1. Ficha (§5) y frontmatter (§6) contienen `clase`, `independencia`, `ronda`, `cobertura` y los digests.
2. El **plan de migración** produce el censo una vez, con una fila por identidad.
3. El generador se escribe **cuando exista un consumidor real** —cierre de sesión, runbook, petición
   concreta— y no antes.

## 8. Guards

Dos tests en `tests/test_docs_gobernanza.py`, **población separada** con vocabulario propio.

**G7 — adjudicación bien formada.** Toda línea de encabezado que contenga «Adjudicación de la revisión»,
fuera de cercas, casa `_RE_ADJUDICACION` con `veredicto` y `estado_remediacion` de los sets del §4, y va
seguida de las **nueve** líneas de la ficha con `clase`, `independencia` y `cobertura` válidos. Además
**aplica la relación del §1.3**: si `Cobertura` empieza por `ejecutada`, `Informe recibido` **resuelve a
un acta existente**, salvo que el fichero esté en la lista cerrada de excepciones históricas. Su fixture
fija los totales vivos. Los ficheros con `tipo: revision-adversarial` quedan fuera: el informe literal
puede contener cualquier encabezado.

**G8 — acta bien formada y cadena íntegra.**

- claves del §6 con vocabulario válido, incluidas `independencia`, `mandato` y `marcador_nonce`;
- `adjudicado_en` resuelve a fichero **y** sección;
- `mandato` resuelve: `§0 de este acta` **con §0 presente**, o `<ruta> §N` que exista **en el `commit`
  del frontmatter**, no en el HEAD mutable. Mismo helper que `adjudicado_en`;
- **exactamente un par** de marcadores con el `marcador_nonce`, en orden;
- el digest del bloque canonicalizado **se recomputa y debe coincidir** con `sha256_informe`. **Una
  desigualdad es roja, nunca aviso**: un aviso convierte una cadena rota en suite verde;
- allowlist cerrada de cuatro nombres para `formato: hibrido-legacy` y `no-disponible-legacy`, que
  eximen digest y cuerpo;
- fuera de la allowlist: existen §1 y §2, y §0 si `mandato` apunta a él.

**Anti-automatch:** el corpus de G7 incluye este spec. Si vuelve a detectar la plantilla del §5 dentro de
su cerca, G7 falla.

**Lo que NO hacen:** no exigen que un objeto tenga revisión; no tocan `_ESTADOS_DOCS` ni
`_ESTADOS_HANDOFF` ni vuelven recursivo el glob de `_docs_con_frontmatter`; no piden frontmatter a specs
ni planes; no juzgan el contenido de la adjudicación. **No hay G9.**

## 9. Política de migración

El inventario, las tareas y el orden de PRs viven en el plan de migración, en
`docs/superpowers/plans/`. El spec fija el contrato; el plan ejecuta. La política que el plan respeta:

1. **Los guards se activan en el ÚLTIMO PR** o crecen sobre una población migrada explícita que la
   última tarea retira. Recorren todo el corpus: activarlos de golpe al principio obliga a un PR
   gigante.
2. **Troceo por vertical y dependencia:** `diseño` con sus actas y encabezados → `rama` con la cobertura
   por tarea que incorpora → revisiones de `independencia: autor`. G2 solo exige que cada referencia y su
   acta entren en el mismo PR.
3. **Los objetos de las actas heredadas reciben encabezado, ficha y puntero**, aunque el cuerpo del acta
   no se toque.
4. **Retrofit declarado de siete de ocho encabezados**, medido: 1 casa, 1 solo-token, 6 estructurales. Se
   elige el retrofit frente a un parser permisivo permanente, cuya complejidad se paga siempre.
5. **Una fila por identidad**, incluidas las revisiones que hoy solo viven en un acta.
6. **Renombrado de las cuatro actas de este spec** al esquema del §6.
7. **Los tres handoffs `…-codex-*`** se quedan, excepción histórica declarada en la gobernanza §5.
8. **Informes crudos anteriores a esta regla:** perdidos. `no capturado (excepción histórica cerrada)` en
   la ficha y `no-disponible-legacy` en el acta.

## 10. Doctrina a modificar

| Documento | Cambio |
|---|---|
| `CLAUDE.md` §Revisión adversarial | Resolver el «o»; los dos ejes; **solo `independencia: independiente` acredita cobertura**; acta obligatoria y fail-closed; la regla de parada del §10.2 |
| `AGENTS.md` | El contrato del revisor: **§10.1** |
| `docs/GOBERNANZA_FUENTES_VERDAD.md` §5 | El acta es el hogar del informe recibido; excepción histórica de los tres `codex-*` |
| `tests/test_docs_gobernanza.py` | Cabecera: tercera población de vocabularios |

`docs/INDICE.md` **no** se toca: sin registro versionado no hay documento nuevo de raíz.

### 10.1 El contrato del revisor (`AGENTS.md`)

**1. Prohibición continua, capacidad declarada.** El repo, los ficheros ignorados por git,
`data/CASOS/` y los sistemas externos (CRM, Drive) son **entradas de solo lectura durante toda la
revisión**. Se permite **ejecutar código y tests** cuando todas sus escrituras van fuera del repo y no
hay efectos externos: `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, `--basetemp` fuera del árbol.
`git status --porcelain --untracked-files=all` antes y después es **evidencia adicional, no sustituto**.

La rev. 3 sostuvo que «solo lectura» estaba mal recortado; era falso —`AGENTS.md:33` dice «solo lectura,
**no escribes en el repo**»— y la invariante que se propuso en su lugar era **más débil**: `git status`
no ve modificaciones de ficheros ignorados preexistentes, y `.gitignore` excluye `data/CASOS/*`.

**2. Ruta del informe, fijada por el encargo.** El informe vive **fuera del repo** porque el revisor no
escribe en el repo que revisa. El encargo **fija la ruta y el nombre antes de empezar**, derivados de la
identidad (§1.4), y **prohíbe sobrescribir** informes anteriores: sus digests son la cadena.

**3. El revisor devuelve `ruta + sha256` antes de la adjudicación.** Por un canal separado del fichero.
Sin esa declaración, la «prueba independiente de origen» del §6.1 se reduce a que el autor calcule y
escriba los dos lados.

**4. Mandato numerado y jerarquizado por daño**, contestado punto por punto en sección propia, con el
objeto anclado a un **commit**. Es lo que más subió la calidad de las cuatro rondas: sin el anclaje no se
puede pedir «reproduce mi medición».

**5. El revisor no adjudica, y el caso que lo explica.** El H-04 de la ronda 1 era **correcto**, y lo que
se pasó de rosca fue **el remedio**: exigía suprimir dos criterios de aceptación, y uno era el objetivo
del encargo. Distinguir un hallazgo bueno de un remedio que se lleva por delante el objetivo solo lo
puede hacer quien tiene la intención del encargo.

**Independencia, y lo que pasó con ella.** El punto 1 parecía ampliar los permisos del propio revisor, y
por eso se declaró su opinión insumo y no veredicto. **Argumentó contra su propia ampliación**, y quien
se equivocaba era el autor.

### 10.2 Regla de parada de rondas

> Con **`LISTA-CON-CAMBIOS`** se aplican los cambios y **se cierra la ronda**: no se abre otra para
> atacar el material de la remediación mientras el documento siga siendo borrador.
>
> La remediación **acumula**. Antes de que el objeto **pase a doctrina o abra la ejecución de un plan**
> se le hace **una pasada completa sobre todas las capas sin revisar**.
>
> **Cierre por naturaleza del cambio, no por número de pasadas.** Esa pasada cierra con `SHIP`. Con
> `LISTA-CON-CAMBIOS` cierra sin nueva revisión **solo si la adjudicación enumera los cambios y
> atestigua que ninguno toca**: población o predicado, obligaciones de traza, vocabularios, guards,
> permisos del revisor, o esta regla. Si toca alguno de esos ejes, hace falta una **comprobación
> dirigida del diff final**, acotada a los ejes tocados — **no** otra pasada completa.
>
> Una renuncia a esa comprobación es **decisión expresa de Nikolai**, con los cambios y el riesgo
> enumerados.
>
> **El gate es observable:** el commit que promociona a `CLAUDE.md`/`AGENTS.md`, o que abre la primera
> tarea del plan, **enlaza la revisión de cierre**. Sin ese enlace, el gate no está satisfecho.
>
> Con `NO-SHIP`, `REQUIERE-REVISION` o `NO-EJECUTABLE` se remedia y se vuelve a pasar.

La primera mitad evita que el proceso se coma al trabajo. La segunda evita lo contrario, y su necesidad
está medida: la rev. 5 decía que la remediación final se acepta como «riesgo residual declarado», y la
ronda 3 —`LISTA-CON-CAMBIOS`— había cambiado con su remediación el predicado, las clases, el contrato de
actas, el hash, los nombres y la migración. El token del veredicto **no acota** el radio material.

## 11. Riesgos

- **G7 y G8 son parsers de prosa.** Acotados a encabezado con frase fija, nueve líneas con prefijo
  `- **Campo:**`, marcadores con nonce y eliminación previa de cercas.
- **La migración es el 80 % del trabajo**, vive en su plan y se trocea por vertical.
- **Coste por revisión.** Un acta con mandato, informe y digest, y una ficha de nueve líneas. Compra lo
  único que no existía: poder contrastar lo que el revisor dijo con lo que el autor decidió que dijo.
- **La cadena no resiste al administrador del repo** (§6.1). Declarado, no mitigado.
- **Cuatro rondas y 24 hallazgos confirmados** dicen que este contrato es difícil de mantener coherente.
  La rev. 6 responde acortando y diciendo cada regla una vez; si la quinta ronda encuentra otra costura,
  la conclusión razonable no será otra rev. 7 sino recortar alcance.

## 12. Criterios de aceptación

1. `python -m pytest -q --tb=no` verde, con G7 y G8 incluidos.
2. Los ocho encabezados casan G7 tras el retrofit; las cuatro actas heredadas casan G8 con
   `formato: hibrido-legacy` y `no-disponible-legacy`.
3. G7 corre sobre este spec y **no** detecta la plantilla del §5; su fixture es la única fuente de los
   totales vivos.
4. G8 rechaza: acta con cuerpo vacío; `adjudicado_en` a sección inexistente; `mandato` que no resuelve;
   bloque literal alterado; y **más o menos de un par de marcadores** con el nonce.
5. G7 rechaza una ficha con `Cobertura: ejecutada` cuyo `Informe recibido` no resuelva a un acta, salvo
   excepción histórica de lista cerrada.
6. Toda revisión de la población postcorte tiene encabezado y ficha en su objeto, con `clase`,
   `independencia` y `ronda`.
7. **Cada revisión postcorte está representada exactamente una vez**, acreditado por la matriz
   fuente → identidad → encabezado/acta del plan.
8. Ningún objeto cuenta como cubierto sin al menos una revisión con `independencia: independiente`.
9. No existe `docs/REVISIONES_ADVERSARIALES.md`, ni G9, ni `scripts/censo_revisiones.py`.
10. Ninguna población de vocabulario existente se ha tocado.

## 13. Estado de la revisión de este spec

Cuatro rondas: NO-SHIP (6) → NO-SHIP (3) → LISTA-CON-CAMBIOS (7) → NO-SHIP (8). **24 de 24
confirmados, cero refutados.**

**Camino de salida, el que fijó la ronda 4 y que la rev. 6 sigue:** cerrados H-01 a H-08, procede una
**comprobación dirigida del diff `24f8abe` → HEAD**, acotada a los ejes que la rev. 6 toca —predicado,
ejes de clasificación, traza fail-closed, semántica del digest, marcadores, guards y regla de parada—.
**No otra pasada completa del corpus histórico.** Es exactamente lo que ordena el §10.2, aplicado a sí
mismo: la rev. 6 cambia varios de esos ejes, así que no puede cerrarse por atestiguación.

**Sin esa comprobación dirigida, el gate no está satisfecho** y no se toca `CLAUDE.md` ni `AGENTS.md` ni
se abre la Tarea 1 del plan.

## 14. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Clase:** diseño
- **Independencia:** independiente
- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 1, commit `3126214`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review.md`
- **Hallazgos:** 6 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento

| Hallazgo | Severidad | Veredicto | Remedio |
|---|---|---|---|
| H-01 censo sin identidad; omite `PLAN.md` | CRÍTICA | **Confirmado** | §1.4, §1.5 |
| H-02 los cuatro de `DEAD_ENDS` no son cobertura ausente | ALTA | **Confirmado** | §4 |
| H-03 G7 casa 1/8 y se autodetecta en la cerca | ALTA | **Confirmado** | §5.1, §9.4 |
| H-04 el registro central sobra | ALTA | **Confirmado, remedio acotado** | §7 |
| H-05 G9 rechaza las filas `no-ejecutada` | ALTA | **Confirmado** | G9 retirado |
| H-06 el frontmatter invade el hogar de la decisión | MEDIA | **Confirmado** | §3, §6 |

**Divergencia sobre H-04.** Acepté el hallazgo y retiré tabla y G9, pero rechacé suprimir dos criterios
de aceptación y añadí un generador. La ronda 2 demostró que fue **medio equivocada**: acerté conservando
el objetivo, me equivoqué al materializarlo como script. Única divergencia de las cuatro rondas.

## 15. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Clase:** diseño
- **Independencia:** independiente
- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 2, commit `2c2a6d0`
- **Ronda:** 2
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review-r2.md`
- **Hallazgos:** 3 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 3 de este documento

| Hallazgo | Severidad | Veredicto | Remedio |
|---|---|---|---|
| H-01 el censo da ≥24, no 16; falta el predicado | CRÍTICA | **Confirmado** | §1.1, §1.2, §1.5 |
| H-02 el generador no puede derivar ni tiene consumidor | ALTA | **Confirmado** | §7 |
| H-03 G8 no verifica el cuerpo; exención global | ALTA | **Confirmado** | §6.1, §8 |

**Contradicción propia que destapó:** la rev. 2 escribió que dos revisores son dos revisiones y agrupó
«Codex + Claude» como una en la tabla siguiente.

**Decisión de alcance de Nikolai, contra mi recomendación.** Recomendé estrechar la población a las
revisiones con informe externo; decidió gobernarlas todas.

## 16. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — LISTA-CON-CAMBIOS, remediado

- **Clase:** diseño
- **Independencia:** independiente
- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 3, commit `1a6e3d8`
- **Ronda:** 3
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review-r3.md`
- **Hallazgos:** 7 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 4 de este documento

| Hallazgo | Severidad | Veredicto | Remedio |
|---|---|---|---|
| H-01 predicado estrecho; clase C incoherente | ALTA | **Confirmado** | §1.1, §1.2 |
| H-02 la clase rama puede perder el texto del revisor | ALTA | **Confirmado** | §1.3 |
| H-03 §10.1 debilitaba «solo lectura» | ALTA | **Confirmado contra el autor** | §10.1.1 |
| H-04 G8 exige el hash pero no lo compara | ALTA | **Confirmado** | §6.1, §8 |
| H-05 la migración no crea los encabezados que exige | MEDIA | **Confirmado** | §9 |
| H-06 `-rN` no es inyectivo | MEDIA | **Confirmado** | §6 |
| H-07 la medición del §5.1 quedó obsoleta | BAJA | **Confirmado, y reproducido al remediarlo** | §5.1 |

**El de más valor fue H-03, y va contra el autor.** `AGENTS.md:33` desmiente que «solo lectura» prohíba
ejecutar, y la invariante que se proponía en su lugar era más débil que la vigente: habría autorizado
modificar un expediente real de cliente bajo `data/CASOS/` y pasar la comprobación. Lo paró la parte
interesada.

## 17. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Clase:** diseño
- **Independencia:** independiente
- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 5, commit `24f8abe`
- **Ronda:** 4
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review-r4.md`
- **Hallazgos:** 8 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 6 de este documento

| Hallazgo | Severidad | Veredicto | Remedio |
|---|---|---|---|
| H-05 la cláusula de cierre promueve remediación normativa sin revisar | **CRÍTICA** | **Confirmado** | §10.2, cierre por naturaleza del cambio + gate observable |
| H-01 `no capturado` deja la obligación de informe *fail-open* | ALTA | **Confirmado** | §1.3, §5, §8 (G7 aplica la relación), §10.1.2-3 |
| H-02 `clase` mezcla tipo de objeto e independencia | ALTA | **Confirmado** | §1.2, dos ejes; `independencia` medida contra el **autor** |
| H-03 el predicado incluye lo que §1.2 expulsa | ALTA | **Confirmado** | §1.1, predicado por **declaración del encargo** |
| H-04 dos digests distintos; marcadores ambiguos | ALTA | **Confirmado** | §6 nonce, §6.1 una sola semántica + `sha256_recibido` |
| H-06 `mandato` obligatorio pero sin resolver | MEDIA | **Confirmado** | §8, resuelve contra el `commit` del frontmatter |
| H-07 el nombre no es función estable de la identidad | MEDIA | **Confirmado** | §6, revisor y commit **siempre**; `diagnostico` añadido |
| H-08 la confianza en git es revocable, y se revocó | MEDIA | **Confirmado** | §6.1, frontera de confianza declarada |

**Cinco de los ocho eran contradicciones internas** verificables sin salir del documento. El único que
exigía fuente externa es el más elegante: `STATUS.md:6` documenta que el historial de git fue reescrito
y el repo recreado el 2026-07-07, así que llamar «append-only» al historial era un supuesto que este
proyecto **ya revocó una vez**.

**H-04 se materializó al archivar el propio informe:** contiene el token de fin, y con los marcadores
planos de la rev. 5 el bloque se habría cortado por la mitad. El acta de la ronda 4 es la primera con
nonce, y su digest recomputado coincide — 169 líneas.

**Agravante propio en H-04:** el plan de migración **ya** definía el digest sobre la forma canónica. Lo
supe al escribir el plan y no lo llevé al spec, así que spec y plan discrepaban entre sí.

**Y la decisión de Nikolai fue la correcta.** Pidió revisar la rev. 5 **completa** en contra de la regla
de parada que yo acababa de escribir. Esa regla, tal como estaba, habría dejado pasar a doctrina las dos
capas sin revisar donde vivía la CRÍTICA. La regla se corrigió, y su corrección es lo que ahora obliga a
la comprobación dirigida del §13.

**Nota de método.** 24 de 24 en cuatro rondas. El patrón fue estable y conviene no adornarlo: cada
remediación cerraba su defecto y abría otro en la costura de al lado, casi siempre por restatar una
regla con palabras distintas en dos sitios. La rev. 6 responde acortando el documento y diciendo cada
regla una vez. Si la comprobación dirigida encuentra otra costura, la conclusión razonable no es una
rev. 7: es recortar alcance.
