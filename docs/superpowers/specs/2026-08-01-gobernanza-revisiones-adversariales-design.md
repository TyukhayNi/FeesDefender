# Gobernanza de las revisiones adversariales — población, hogar y formato

> **Estado:** **rev. 4** (2026-08-01), tras **tres** revisiones adversariales de Codex:
> NO-SHIP (6 hallazgos), NO-SHIP (3) y **LISTA-CON-CAMBIOS (7)**. Los dieciséis confirmados, ninguno
> refutado. Adjudicaciones en §14, §15 y §16; informes literales en las tres actas
> `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review*.md`.
> **Objeto:** cómo se documenta y se audita la revisión adversarial en este proyecto — sus clases, no
> solo el intercambio con Codex.
> **Origen:** pregunta de Nikolai (2026-08-01) sobre si el «diálogo interno» necesita documentarse,
> cómo se estructura y cómo puede auditarse. **Alcance ampliado por decisión suya** el mismo día:
> gobernar todas las clases de revisión, no solo la que produce informe externo.

## 1. La población

No hay diálogo: hay un intercambio de dos turnos con bus humano. Claude escribe el objeto → se
encarga la revisión → el revisor ataca y entrega hallazgos → Claude adjudica contra la fuente. Lo que
se parece a diálogo son las **rondas**.

La rev. 2 definió cómo distinguir dos revisiones sin decir qué cuenta como revisión. La rev. 3 definió
el predicado y lo dejó más estrecho que la práctica que ella misma migraba. Orden correcto: quién
entra, qué rastro deja, y solo entonces cuántas hay.

### 1.1 Predicado de inclusión

> Un proceso pertenece a la población si **(a)** su mandato es **atacar** un artefacto concreto y
> versionable del proyecto —refutarlo o buscarle defectos—, acreditado por el encargo o por el propio
> informe, y **(b)** produce hallazgos o veredicto.

**Artefacto** incluye spec, plan, diagnóstico, **handoff**, diff y rama. La rev. 3 lo limitaba a
«spec, plan, diff o rama» y por eso excluía un objeto cuya acta ella misma mandaba migrar: la del
2026-07-26 revisa `handoff-2026-07-26-gobernanza-indice-adversarial.md`.

**El mandato se acredita por su función, no por un token.** Un panel «4 lentes» que consolida
perspectivas y produce correcciones es una revisión aunque no use la palabra «refutar».

No exige que alguien lo haya adjudicado: una revisión sin adjudicar es precisamente el caso que hay
que poder ver. **Quedan fuera**, y se declara: el `code-review` de rutina sin veredicto adversarial,
la revisión de estilo (`pase-de-estilo`), los tests automáticos y el brainstorming.

**Adjudicador.** Es Claude por defecto (`CLAUDE.md`). Puede no serlo —el acta de gobernanza de
2026-07-26 quedó a adjudicación de Nikolai—; cuando no lo sea, se dice en la prosa de la adjudicación.
No se añade campo para eso.

### 1.2 Las clases y la traza que se les exige

| Clase | Qué es | Traza exigida |
|---|---|---|
| **`diseño`** | spec, plan, diagnóstico o handoff atacado por un revisor | **Acta** + encabezado canónico + ficha |
| **`rama`** | revisión de un diff o de la rama completa, antes del PR | **Acta** + encabezado + ficha en el plan |
| **`autorrevision`** | pasada propia de Claude sobre su propio objeto | Encabezado + ficha; **sin acta** |

**El acta se exige siempre que exista una respuesta textual recuperable del revisor**, sea Codex, un
Opus de otra sesión o un subagente. La rev. 3 la exigía solo con «informe externo», y esa frontera no
protege nada: lo que hay que conservar es la **voz independiente**, y un subagente que escribe
hallazgos la tiene. `sin informe` queda para lo histórico y para un proceso que genuinamente solo
emitiera un estado estructurado.

Por eso la `autorrevision` no lleva acta: el revisor y el adjudicador son la misma persona, así que no
hay voz independiente que preservar. El acta no es burocracia de simetría; existe para que la parte
revisada no sea la única narradora.

**Las revisiones por tarea no son una clase.** En la rev. 3 eran «clase C» y a la vez «se cuentan como
una revisión B»: figuraban en la población y desaparecían al aplicar el criterio de encabezado. Ahora
son **cobertura de su revisión de rama**, declarada en su ficha (`Cobertura: ejecutada (7 revisiones
por tarea agregadas)`), y **la adjudicación de la rama enumera sus hallazgos sustantivos y su
procedencia**. Si alguna produjera un veredicto sobre el objeto y no sobre su porción, deja de ser
cobertura y es una revisión de rama propia.

### 1.3 Identidad

> Una **revisión** es la tupla **`(objeto, commit o rev. del objeto, ronda, revisor, fecha de
> entrega)`**, con su **clase**.

Consecuencias, verificadas sobre el corpus:

- El acta dual y el §20 de su spec **son la misma revisión** en dos hogares.
- `handoff-…-codex-informe.md` y `…-review.md` son informe completo y resumen de la **misma** primera
  pasada; `…-review-2.md` es otra ronda.
- El acta de emails declara una «segunda revisión, independiente»: **son dos**.
- Las tres pasadas sobre el plan de la Fase 0 son **tres revisiones**.
- Un objeto revisado por dos revisores en la misma ronda son **dos revisiones**. La rev. 2 escribió
  esta regla y la incumplió agrupando «Codex + Claude» en una fila.
- Un panel con orquestador y subagentes en paralelo es **una** revisión si hubo un mandato único y un
  veredicto consolidado; sus lentes son metodología, no revisiones distintas.

### 1.4 Corte temporal

**Se migra desde el 2026-07-23**, primera acta y arranque de hecho del contrato con Codex. Antes hubo
revisiones adjudicadas —`PLAN.md:924-928`, `:933`, `:953`, `:1033-1044`— que **quedan fuera de alcance
y se declaran aquí**: no había contrato de revisor estable, no hay informe que archivar, y
reconstruir la tupla desde párrafos fingiría exactitud. `PLAN.md` sigue siendo su registro. El corte
**no amnistía nada**: todas las omisiones detectadas en las tres rondas son posteriores.

### 1.5 La cardinalidad no se publica aquí

La rev. 1 dijo «≥15». La rev. 2 dijo 16 y era falso: se documentaron **al menos 24**, con evidencia en
`docs/bitacora/2026.md:70,138,144,150` y `PLAN.md:383-386,757-768`. Publicar una tercera cifra sin
haber aplicado el predicado sería el mismo error por tercera vez.

**El censo lo produce el plan de migración** (§9), aplicando §1.1 y §1.2 fuente por fuente, con una
fila por identidad. Aquí no se publica ninguna cardinalidad.

### 1.6 Por qué está disperso

- `CLAUDE.md` dice que la adjudicación «se registra en el spec **o** el plan». Ese «o» es la dispersión
  escrita como norma.
- `GOBERNANZA_FUENTES_VERDAD.md` §5 añade una partición ortogonal —informe de fuera → handoff; acta de
  dentro → junto al spec— y un evento de revisión es las dos cosas.
- Solo **14 de 53** specs y **14 de 62** planes llevan frontmatter: exigirlo son 87 ficheros de
  migración. **Descartado.**

## 2. Qué se corrige y qué no

**En alcance:** el predicado y las clases; la traza por clase; el hogar de cada artefacto; un formato
de adjudicación parseable; el archivo **verificable** del informe recibido; dos guards; y la política
de migración.

**Fuera de alcance, explícitamente:**

- Exigir que todo spec o plan tenga revisión. El guard no juzga si algo debió revisarse.
- Un registro central versionado y su guard G9. Descartados en la rev. 2.
- `scripts/censo_revisiones.py`. Diferido en la rev. 3 (§7).
- **El inventario de migración, sus tareas y su orden de PRs.** Salen a un plan propio en la rev. 4
  (§9); si siguieran creciendo dentro del spec, el spec dejaría de ser un contrato.
- Automatizar el puente con el revisor: sigue siendo manual y mediado por Nikolai.
- Frontmatter en specs y planes.
- Revisiones anteriores al 2026-07-23.
- Cambiar quién adjudica.

## 3. Modelo: cuatro artefactos

| Artefacto | Hogar | Obligatorio en |
|---|---|---|
| **Mandato** (qué se pidió atacar) | El propio objeto, §«Revisión adversarial» previa | Recomendado siempre |
| **Informe recibido**, literal + `sha256` | Acta hermana `…-adversarial-review.md` | `diseño` y `rama`, siempre que haya respuesta textual recuperable |
| **Adjudicación** (veredicto + hallazgo → decisión → remedio) | Sección embebida en el objeto | **Todas las clases** |
| **Cobertura** | Ficha, campo `Cobertura` | Siempre |

La adjudicación se queda **embebida** porque la decisión pertenece al documento que la decisión
modificó. El **acta** es el archivo de la voz del revisor, no un segundo hogar de la decisión.

## 4. Vocabularios cerrados

**`clase`** — `diseño` · `rama` · `autorrevision`.

**`cobertura`** — `ejecutada` · `no-ejecutada`, con matiz libre entre paréntesis (número de revisiones
por tarea agregadas, motivo de la ausencia). Sin cobertura no hay veredicto (doctrina de
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

**Recuento** — `confirmados · rebajados · refutados · escalados · sin-verificar`. Un hallazgo aceptado
**con un remedio distinto del exigido** cuenta como confirmado; la divergencia se razona en la prosa.

**Migración de tokens.** El corpus usa `resuelto`, `aplicados`, `NO EJECUTABLE` y `LISTA CON CAMBIOS`.
Se normalizan; el veredicto literal queda en el acta.

> **Tercera población de vocabularios.** Estos ejes NO comparten set con `_ESTADOS_DOCS` ni con
> `_ESTADOS_HANDOFF`. La cabecera de `tests/test_docs_gobernanza.py` documenta por qué unificarlos
> rompe 11 ficheros (trampa D3). El campo se llama `estado_remediacion` y no `estado`: colisión
> imposible por construcción.

## 5. Encabezado canónico, ficha y parser

```
## [N.] Adjudicación de la revisión adversarial [<calificador>] (<revisor>, <AAAA-MM-DD>) — <VEREDICTO>, <estado_remediacion>
```

El calificador opcional cubre `del PLAN` y `de rama completa`. Debajo, **ocho líneas**:

```markdown
- **Clase:** diseño | rama | autorrevision
- **Objeto revisado:** `<ruta>` rev. N, commit `abc1234`
- **Ronda:** 1 | 2 | 3
- **Revisor:** Codex (solo lectura) | Claude (no independiente: autor del objeto) | <otro>
- **Cobertura:** ejecutada | ejecutada (N revisiones por tarea agregadas) | no-ejecutada — <motivo>
- **Informe recibido:** `<acta>.md` | sin informe (autorrevisión) | no archivado (anterior a esta regla)
- **Hallazgos:** N confirmados · N rebajados · N refutados · N escalados · N sin verificar
- **Remediado en:** PR #NNN (`hash`) | rev. N de este documento | pendiente
```

`Ronda` y `Clase` son parte de la identidad (§1.3) y de la traza (§1.2): sin ellas ninguna lectura
distingue dos revisiones del mismo objeto por el mismo revisor el mismo día — el caso de §14, §15 y
§16 de este documento.

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

**Disparador y bloques cercados.** El guard no busca solo lo que casa: busca **toda línea de encabezado
que contenga «Adjudicación de la revisión»** y exige que case. Sin eso, un encabezado mal formado no se
detecta y pasa en silencio, que es el modo de fallo caro.

**Antes de cualquier match se eliminan los bloques cercados** (``` … ```). La plantilla de arriba,
dentro de su cerca, fue detectada como encabezado real por el grep de censo de la rev. 1: el defecto se
observó, no se dedujo.

**La medición no vive en esta prosa, y hay una razón medida.** La rev. 3 publicaba la foto de la
rev. 2 (9/3/2/1/6) porque añadir el §15 la dejó obsoleta; al corregirla en la rev. 4 volvió a quedar
obsoleta **en el mismo acto**, porque el §16 sumó un disparador más. Un total que cambia cada vez que
se adjudica una revisión no puede tener su hogar en un párrafo.

Se separan dos cosas:

- **El corpus legacy es estable** hasta que lo toque la migración: **ocho** encabezados, de los que
  **1 casa** (sandwich §9), **1 falla solo por token** (`resuelto`, email enumeración §11) y **6 fallan
  estructura**. Reproducido por Claude y por Codex por separado. Ese desglose sí se declara aquí,
  porque es el alcance del retrofit.
- **Los totales vivos** —disparadores fuera de cerca y cuántos casan— se fijan en el **fixture de
  G7**, que es su única fuente. Cada adjudicación nueva los mueve, y el guard es lo que debe notarlo.

## 6. El acta hermana

**Ubicación y nombre:** junto a su objeto —`specs/` o `plans/`— como

```
AAAA-MM-DD-<tema>-<objeto>-r<N>[-<revisor>]-adversarial-review.md
```

`<objeto>` ∈ `spec` · `plan` · `rama` · `handoff` · `diff`, y `<revisor>` **solo** cuando dos
revisores comparten objeto y ronda. El nombre de la rev. 3 —solo fecha, tema y ronda— **no era
inyectivo** respecto de la identidad del §1.3: dos revisores del mismo objeto y ronda escribirían el
mismo fichero, y una revisión de spec y otra de plan del mismo tema y día colisionan (la enumeración
recursiva demuestra que ocurre). Si el objeto es un diff sin plan, el acta va junto al spec del que
deriva.

> **Las tres actas de este spec conservan el nombre antiguo** (`…-adversarial-review.md`, `-r2`,
> `-r3`) hasta que el plan de migración las renombre. No hay colisión entre ellas: mismo objeto,
> mismo revisor, rondas distintas.

**Un acta por ronda, no por objeto.** Lo impone el frontmatter: `ronda`, `commit`, `veredicto` y
`sha256_informe` son escalares. El acta heredada de emails, que contiene dos revisiones, es por eso
`formato: hibrido-legacy`.

**Frontmatter obligatorio:**

```yaml
---
tipo: revision-adversarial
objeto: docs/superpowers/specs/<fichero>.md
objeto_rev: "1"
commit: 3126214
ronda: "1"
clase: diseño
revisor: Codex
cobertura: ejecutada
veredicto: NO-SHIP
sha256_informe: <hash en minusculas> | no-disponible-legacy
adjudicado_en: docs/superpowers/specs/<fichero>.md §14
---
```

`adjudicado_por` y `estado_remediacion` **no van aquí**: describen la decisión, y el segundo es
mutable. `veredicto` sí: es inmutable.

**Contenido, dos secciones.** **§1 Informe recibido, sin modificar**, con el bloque literal delimitado
por marcadores explícitos:

```
<!-- informe-literal:inicio -->
…texto del informe, byte a byte…
<!-- informe-literal:fin -->
```

Los marcadores no son adorno: sin una delimitación inequívoca, «recomputar el hash del bloque
literal» (§8) no es implementable, porque el propio informe puede contener separadores `---`. **§2
Evidencia verificada**: qué abrió Claude para adjudicar, con ruta y línea. La adjudicación **no** se
repite aquí.

### 6.1 Integridad: el hash y su alcance real

`sha256_informe` es el digest del **fichero recibido**. Cierra el agujero de que el §1 lo transcribe
Claude, que es la parte revisada, y nadie verificaba la literalidad.

**Verificación al recibir, obligatoria.** Claude calcula el digest de la copia externa al archivarla y
lo compara con el que declara el revisor. Ese es el único momento en que existe **prueba independiente
de origen**.

**Después, el acta se autoverifica.** Recomputando el bloque literal se detecta cualquier alteración
posterior aunque la copia externa desaparezca. Lo que se pierde sin original no es la detección de
manipulación: es la prueba de que el digest inicial venía del informe recibido.

Corolario, contra lo que decía la rev. 3: **`%TEMP%` no es almacenamiento duradero y no hace falta que
lo sea**, siempre que la verificación al recibir sea obligatoria. Lo que sí se exige es no sobrescribir
un informe anterior — de ahí el nombre por identidad.

**Las cuatro actas heredadas** llevan `formato: hibrido-legacy` con **allowlist cerrada de cuatro
nombres**: nacieron con informe y adjudicación juntos, se les añade frontmatter y no se les mueve
nada. Sus informes crudos se perdieron, así que llevan `sha256_informe: no-disponible-legacy` — un
**token tipado**, no una omisión, para que no contradigan la regla general (§8).

## 7. El censo se calcula, no se mantiene

**No hay registro versionado** (rev. 2) y **no se escribe el generador** (rev. 3).

La rev. 2 especificó `scripts/censo_revisiones.py` como lector de encabezados y actas. No podía
funcionar: sus columnas pedían `ronda` y `cobertura`, y ninguna existía en la ficha; un acta con dos
revisiones no cabe en un frontmatter escalar; y una ronda de vista procesal solo vive en un handoff que
el lector no recorría. Habría necesitado excepciones a mano — el ledger escondido en Python. Y tenía
**cero consumidores**.

Secuencia correcta: **primero representable, después legible.**

1. La ficha (§5) y el frontmatter (§6) contienen `clase`, `ronda`, `cobertura` y `sha256`. Cada
   revisión es representable y la relación revisión ↔ artefacto es uno-a-uno para todo lo nuevo.
2. El **plan de migración** (§9) produce el censo una vez, con una fila por identidad.
3. El generador se escribe **cuando exista un consumidor real** —cierre de sesión, runbook o petición
   concreta— y no antes.

## 8. Guards

Dos tests nuevos en `tests/test_docs_gobernanza.py`, **población separada** con vocabulario propio.

**G7 — adjudicación bien formada.** Toda línea de encabezado que contenga «Adjudicación de la
revisión», fuera de bloques cercados, casa `_RE_ADJUDICACION` con `veredicto` y `estado_remediacion` de
los sets del §4, y va seguida de las ocho líneas de la ficha con `clase` y `cobertura` de vocabulario
válido. Su fixture fija la medición del §5.1. Los ficheros con `tipo: revision-adversarial` quedan
fuera: el informe literal puede contener cualquier encabezado y no debe reinterpretarse como
adjudicación del proyecto.

**G8 — acta bien formada y cadena íntegra.**

- frontmatter con las claves del §6 y vocabulario válido;
- `adjudicado_en` apunta a un fichero **y a una sección que existen** — no solo al fichero;
- **el digest del bloque literal se recomputa y debe coincidir** con `sha256_informe`. Canonicalización
  explícita: extraer lo que hay entre los marcadores del §6, codificar en UTF-8, finales de línea `LF`,
  un único salto final. **Una desigualdad es rojo, nunca aviso**: un aviso convierte una cadena de
  custodia rota en suite verde;
- `sha256_informe: no-disponible-legacy` **solo** en los cuatro nombres de la allowlist, y en ese caso
  se omiten la comprobación de digest y la de cuerpo;
- para toda acta fuera de la allowlist: existen las dos secciones del §6 y los dos marcadores.

**Anti-automatch:** el corpus de G7 incluye este mismo spec. Si vuelve a detectar la plantilla del §5
dentro de su cerca, G7 falla.

**Lo que los guards NO hacen:** no exigen que un spec tenga revisión; no tocan `_ESTADOS_DOCS` ni
`_ESTADOS_HANDOFF` ni vuelven recursivo el glob de `_docs_con_frontmatter`; no piden frontmatter a
specs ni a planes; no juzgan el contenido de la adjudicación. **No hay G9.**

## 9. Política de migración

El inventario, las tareas y el orden de PRs **salen de este spec** a un plan de migración propio, en
`docs/superpowers/plans/`, todavía sin escribir. El spec fija el contrato; el plan ejecuta. Si el inventario siguiera creciendo aquí, el spec dejaría de ser un contrato y
pasaría a ser un registro — el defecto que existe para arreglar.

La política que el plan debe respetar:

1. **Los guards se activan en el ÚLTIMO PR.** G7 y G8 recorren toda la población, así que estarán en
   rojo hasta completar el retrofit. Activarlos antes obliga a un PR gigante; activarlos al final
   permite trocear.
2. **Troceo por vertical y dependencia**, no por clase pura: `diseño` con sus actas y encabezados →
   `rama` junto con la cobertura por tarea que agrega → `autorrevision`. G2 solo exige que cada
   referencia y su acta entren en el mismo PR.
3. **Los objetos de las actas heredadas reciben encabezado, ficha y puntero**, aunque el cuerpo del
   acta no se toque. Sin eso, §3 y el criterio 5 quedan incumplidos: hoy solo dual workspace tiene su
   §20, mientras emails, cableado y la gobernanza de 2026-07-26 no tienen encabezado en su objeto.
4. **Retrofit declarado de siete de ocho encabezados.** El formato casa 1 de 8. La rev. 1 afirmaba que
   «formaliza la línea que ya se escribe sola»: era falso, converge la forma y no los tokens. Se elige
   el retrofit —siete ediciones, una vez— frente a un parser permisivo permanente, cuya complejidad se
   paga siempre. Grados medidos: **1 casa** (sandwich §9), **1 solo-token** (`resuelto` en email
   enumeración §11), **6 estructurales** (historial §10-bis, sandwich plan, cableado plan, vista
   procesal §10, dual §20, rama completa §1089).
5. **Una fila por identidad**, incluidas las revisiones que hoy solo viven en un acta, y los tres
   marcadores `informe-literal` que las actas de este spec aún no llevan.
6. **Renombrado de las tres actas de este spec** al esquema del §6.
7. **Los tres handoffs `…-codex-*`** se quedan, declarados excepción histórica en la gobernanza §5.
8. **Informes crudos anteriores a esta regla:** perdidos. `no archivado (anterior a esta regla)` en la
   ficha y `no-disponible-legacy` en el acta. Se declara, no se disimula.

## 10. Doctrina a modificar

| Documento | Cambio |
|---|---|
| `CLAUDE.md` §Revisión adversarial | Resolver el «o»; las clases y su traza; acta siempre que haya respuesta textual recuperable |
| `AGENTS.md` | Cuatro cambios al contrato del revisor: **§10.1** |
| `docs/GOBERNANZA_FUENTES_VERDAD.md` §5 | El acta es el hogar del informe recibido; excepción histórica de los tres `codex-*` |
| `tests/test_docs_gobernanza.py` | Cabecera: tercera población de vocabularios |

`docs/INDICE.md` **no** se toca: sin registro versionado no hay documento nuevo de raíz, y su `:23-28`
excluye deliberadamente los specs fechados.

### 10.1 El contrato del revisor (`AGENTS.md`)

**1. La prohibición continua se conserva; lo que falta es declarar la capacidad.** La rev. 3 decía que
«solo lectura» estaba mal recortado y que invitaba a leer solo el diff. **Era falso, y el error era
mío:** `AGENTS.md:33` dice «**solo lectura**, no escribes en el repo» —la prohibición está glosada como
*no escribir*, no como *no ejecutar*— y el mismo fichero ya ordena contrastar «contra el código real,
no solo contra el diff». Las tres rondas ejecutaron `pytest` sin que nadie cambiara nada.

Peor: la invariante que la rev. 3 proponía en su lugar —«árbol idéntico, `git status` limpio, sin
ficheros nuevos»— era **más débil** que la regla vigente. Permite escribir y revertir antes de la
comprobación; no ve modificaciones de ficheros **ignorados preexistentes**, y `.gitignore` excluye
`__pycache__/`, `.pytest_cache/`, `.coverage`, `dist/`, `.env*` y **`data/CASOS/*`**; y no cubre
escrituras en CRM, Drive u otros sistemas externos. Habría autorizado tocar un expediente real y pasar
la comprobación.

Redacción correcta: **el repo, los ficheros ignorados, `data/CASOS/` y los sistemas externos son
entradas de solo lectura durante toda la revisión; se permite ejecutar código y tests cuando todas sus
escrituras están redirigidas fuera del repo y no hay efectos externos.** `git status --porcelain
--untracked-files=all` antes y después es **evidencia adicional, no sustituto**. La receta se escribe:
`PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, `--basetemp` fuera del árbol. No queda prohibida
ninguna ejecución que las tres rondas necesitaran.

**2. Ruta del informe: nombrada por identidad, sin sobrescribir.** La razón documentada del `%TEMP%`
con nombre fijo era el guard G2, y ese ciclo se refutó. La conclusión **no se invierte** —el informe
sigue fuera del repo porque el revisor no escribe en el repo que revisa—, pero el nombre pasa a
`(objeto, ronda)`: esta sesión hubo que inventar `-rev2` a mano y con otro orden habría pisado un
informe sin archivar. Con la verificación al recibir (§6.1), la permanencia de la copia externa deja de
ser crítica; **no sobrescribirla, sí**.

**3. El porqué, con el caso resuelto.** La norma ya dice que el revisor no adjudica. Le falta el caso:
el H-04 de la ronda 1 era **correcto**, y lo que se pasó de rosca fue **el remedio** —exigía suprimir
los criterios 2 y 6, y el 6 era el objetivo del encargo—. Distinguir un hallazgo bueno de un remedio
que se lleva por delante el objetivo solo lo puede hacer quien tiene la intención del encargo.

**4. Mandato numerado y jerarquizado por daño**, contestado punto por punto en sección propia, con el
objeto anclado a un **commit**. Es lo que más subió la calidad de las tres rondas: sin el anclaje no se
puede pedir «reproduce mi medición».

**Independencia, y lo que pasó con ella.** El punto 1 parecía ampliar los permisos del propio revisor,
y por eso se declaró su opinión como insumo y no veredicto. Resultó que **argumentó contra su propia
ampliación** y que quien se equivocaba era el autor. La cautela era correcta; la dirección del sesgo,
no la que se esperaba.

## 11. Riesgos

- **G7 y G8 son parsers de prosa.** Acotados a encabezado con frase fija, ocho líneas con prefijo
  `- **Campo:**`, marcadores explícitos para el bloque literal y eliminación previa de cercas.
- **La migración es el 80 % del trabajo.** Vive en su plan, troceada por vertical, con los guards al
  final.
- **La cobertura por tarea puede ocultar.** Agregar siete revisiones por tarea en la ficha de su rama
  es proporcionado; treinta con hallazgos sustantivos, no. Señal de revisión: cuando una revisión por
  tarea produzca un veredicto sobre el objeto y no sobre su porción, se separa.
- **Coste por revisión.** Sube: un acta con su hash y una ficha de ocho líneas, ahora también en las
  revisiones de rama. Compra la única cosa que no existía — poder contrastar lo que el revisor dijo con
  lo que el autor decidió que dijo.

## 12. Criterios de aceptación

1. `python -m pytest -q --tb=no` verde, con G7 y G8 incluidos.
2. Los ocho encabezados casan G7 tras el retrofit; las cuatro actas heredadas casan G8 con
   `formato: hibrido-legacy` y `sha256_informe: no-disponible-legacy`.
3. G7 corre sobre este spec y **no** detecta la plantilla del §5; su fixture es la única fuente de los
   totales vivos, y añadir una adjudicación nueva lo hace fallar hasta actualizarlo.
4. G8 rechaza: un acta con frontmatter válido y cuerpo vacío; una cuyo `adjudicado_en` apunte a una
   sección inexistente; y **una cuyo bloque literal haya sido alterado** respecto de su digest.
5. Toda revisión de la población postcorte tiene encabezado y ficha en su objeto, con clase y ronda —
   incluidas las que hoy solo viven en un acta.
6. **Cada revisión postcorte está representada exactamente una vez**, acreditado por la matriz
   fuente → identidad → encabezado/acta del plan de migración. *(Reformulado: «representable» era
   propiedad del esquema y se cumplía con datos ausentes.)*
7. No existe `docs/REVISIONES_ADVERSARIALES.md`, ni G9, ni `scripts/censo_revisiones.py`.
8. Ninguna población de vocabulario existente se ha tocado.

## 13. Estado de la revisión adversarial de este spec

Tres rondas, veredictos NO-SHIP → NO-SHIP → **LISTA-CON-CAMBIOS**, dieciséis hallazgos, todos
confirmados. La tercera declara la arquitectura aceptable y los cambios locales, así que **no se pide
una cuarta pasada**: la rev. 4 aplica los siete remedios y el siguiente paso es el plan de migración.

Si se quisiera una cuarta, esto es lo que queda sin atacar: los marcadores `informe-literal` y la
canonicalización del §8 (nuevos); el esquema de nombre del §6.1 (nuevo); la exigencia de acta a las
revisiones de rama, que sube el coste en la clase más frecuente; y si el criterio 6 es verificable con
la matriz del plan o sigue siendo aspiracional.

## 14. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Clase:** diseño
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
| H-02 los cuatro de `DEAD_ENDS` no son cobertura ausente | ALTA | **Confirmado** | §4 |
| H-03 G7 casa 1/8 y se autodetecta en la cerca | ALTA | **Confirmado** | §5.1, §9.4 |
| H-04 el registro central sobra | ALTA | **Confirmado, remedio acotado** | §7 |
| H-05 G9 rechaza las filas `no-ejecutada` | ALTA | **Confirmado** | Disuelto al retirar G9 |
| H-06 el frontmatter invade el hogar de la decisión | MEDIA | **Confirmado** | §6 |

**Divergencia sobre H-04, y su desenlace.** Acepté el hallazgo y retiré la tabla y G9, pero rechacé
suprimir los criterios 2 y 6 y añadí un generador. La 2ª ronda demostró que fue **medio equivocada**:
acerté conservando el objetivo —Codex concede que el criterio 2 debía quedarse— y me equivoqué al
materializarlo ya como script. Única divergencia de las tres rondas.

**Refutado a favor del spec:** el §13.4 de la rev. 1 temía un ciclo entre G9 y G2. No existe.

## 15. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 2, commit `2c2a6d0`
- **Ronda:** 2
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review-r2.md`
- **Hallazgos:** 3 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 3 de este documento

| Hallazgo | Severidad | Veredicto | Dónde se remedia |
|---|---|---|---|
| H-01 el censo da ≥24, no 16; falta el predicado | CRÍTICA | **Confirmado** | §1.1, §1.2, §1.5 |
| H-02 el generador no puede derivar y no tiene consumidor | ALTA | **Confirmado** | §7, §5 |
| H-03 G8 no verifica el cuerpo del §6; exención global | ALTA | **Confirmado** | §6.1, §8 |

**Contradicción propia que destapó:** la rev. 2 escribió que dos revisores son dos revisiones y agrupó
«Codex + Claude» como una en la tabla siguiente.

**Lo que resistió:** el regex y el desglose del retrofit; que las filas 1-2 y 6-7 son dos revisiones
cada una; el corte del 23 de julio; la retirada del registro y de G9; no tocar `INDICE.md`; y la
corrección sobre `DEAD_ENDS`. La primera acta cumple su propio §6: 106/106 líneas literales.

**Decisión de alcance de Nikolai, contra mi recomendación.** Recomendé estrechar la población a las
revisiones con informe externo. Decidió gobernarlas todas. La rev. 3 lo implementó entero.

## 16. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — LISTA-CON-CAMBIOS, remediado

- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 3, commit `1a6e3d8`
- **Ronda:** 3
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review-r3.md`
- **Hallazgos:** 7 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 4 de este documento

| Hallazgo | Severidad | Veredicto | Dónde se remedia |
|---|---|---|---|
| H-01 el predicado excluye un objeto que el propio spec migra; clase C incoherente | ALTA | **Confirmado** | §1.1 (artefacto amplio, mandato por función), §1.2 (tres clases; por-tarea = cobertura) |
| H-02 la clase B puede perder el texto del revisor | ALTA | **Confirmado** | §1.2 (acta por respuesta textual recuperable), §3 |
| H-03 §10.1 debilitaba «solo lectura» | ALTA | **Confirmado contra el autor** | §10.1.1, reescrito |
| H-04 G8 exige el hash pero no lo compara; §8 contradice §9 | ALTA | **Confirmado** | §6 (marcadores), §6.1, §8 (recómputo, rojo, token legacy) |
| H-05 la migración no crea los encabezados que exige | MEDIA | **Confirmado** | §9 (política; inventario al plan), §9.3 |
| H-06 `-rN` no es inyectivo | MEDIA | **Confirmado** | §6 (nombre por identidad) |
| H-07 la medición del §5.1 quedó obsoleta | BAJA | **Confirmado, y reproducido al remediarlo** | §5.1 (corpus legacy estable en prosa; totales vivos al fixture) |

**El hallazgo de más valor es H-03, y conviene dejar escrito por qué.** El revisor argumentó **contra
la ampliación de sus propios permisos**. La rev. 3 sostenía que «solo lectura» estaba mal recortado;
`AGENTS.md:33` lo desmiente —dice «solo lectura, **no escribes en el repo**»— y la invariante que se
proponía en su lugar era más débil que la vigente: `git status` no ve modificaciones de ficheros
ignorados preexistentes, y `.gitignore` excluye `data/CASOS/*`. Habría autorizado tocar un expediente
real de un cliente y pasar la comprobación. Es lo más peligroso escrito en las tres rondas, lo escribí
yo, y lo paró la parte interesada.

**Añadido al adjudicar, más ancho que el hallazgo.** Al abrir el acta de gobernanza para verificar
H-01 aparecieron dos cosas que el informe no menciona: su revisor es «Claude Code (orquestador + 5
subagentes en paralelo, uno por hallazgo)», una forma que las clases no cubrían, y su adjudicador
declarado es **Nikolai**, no Claude. Ambas entran en §1.1 y §1.3.

**Cómo se verificó.** H-01, H-04 y H-05 son contradicciones **entre secciones vecinas del propio
documento**, comprobables sin fuente externa. H-03 se verificó contra `AGENTS.md:33` y `.gitignore`.
H-07 contra mi propia sonda, que ya imprimía 10 y 3 mientras el §5.1 decía 9 y 2. El detalle, en el §2
del acta.

**Nota de método.** Dieciséis de dieciséis confirmados en tres rondas, cero refutados. Dos lecturas, y
las dos importan: el revisor encuentra defectos reales, y mi autorrevisión no detecta contradicciones
entre secciones adyacentes del mismo documento — H-01, H-04 y H-05 son todas de esa forma, y no ha
mejorado en tres rondas.
