---
tipo: revision-adversarial
objeto: diff 8f98133..ec5bdc4 (rama claude/audit-log-adversarial-reviews-df1d84)
objeto_rev: 1
commit: ec5bdc4
ronda: 1
revisor: Claude Code (sesión independiente)
veredicto: REQUIERE-REVISION
marcador_nonce: ghjk
sha256_informe: 07ba0f61b487a19aa94cca34aaeb2770cebca8cf1d327df2c431f79dcce4aaac
adjudicado_en: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §14
---

# Revisión adversarial — archivo de auditoría de las revisiones, lente L3 (coherencia doctrinal)

## 0. Mandato, literal y en el orden de daño en que se entregó

**Reglas duras entregadas a los tres revisores, literales:**

1. SOLO LECTURA. No escribes NADA dentro del repo. No `git add/commit/checkout/stash`. No editas
   ficheros del repo.
2. Puedes ejecutar tests si rediriges toda escritura fuera del árbol:
   `PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider --basetemp=<fuera del repo>`.
3. Escribes tu informe EXCLUSIVAMENTE en la ruta fijada por el encargo, fuera del repo.
4. NO das nada por bueno sin ABRIR el fichero fuente. Prohibido razonar solo sobre el diff: el diff
   dice lo que se escribió, no si es cierto.
5. REPRODUCE las mediciones, no las creas.
6. Al terminar devuelves ruta absoluta del informe + su `sha256` canónico + veredicto en una palabra.

**Objeto entregado:** el diff `8f98133..HEAD` de la rama, anclado a los cuatro commits `dffb2cb`,
`4340503`, `29163da`, `ec5bdc4`. Sin contexto de autoría y sin mi adjudicación.

**Lente L3 — COHERENCIA DOCTRINAL Y ALCANCE.** Contexto entregado: el alcance de este contrato se
recortó tras seis rondas y 38 hallazgos, cuando un revisor independiente dictaminó que el autor
estaba RACIONALIZANDO para seguir ampliándolo; el mandato incluye comprobar si ha vuelto a pasar.
Numerado y ordenado por daño:

1. **¿Se reabrió alcance excluido?** El §2 enumera lo que quedó fuera: predicado de población,
   taxonomía de clases e independencia, fail-closed, regla de parada, trailer de gate, registro
   central, generador de censo y G9. ¿Alguna ha vuelto a entrar, disfrazada o no? Con lupa: (a) ¿el
   marco del censo lo convierte de facto en registro central? (b) ¿las fichas reintroducen la
   taxonomía (`Clase`, `Cobertura`, `Independencia`)? (c) ¿la §3.1 crea regla nueva o solo registra
   una decisión ya tomada?
2. **Afirmaciones de la rev. 9 que el diff no sostiene.** Verifica una a una: `_ADJ_LEGACY` retirada
   vacía; los nueve encabezados casan; los cinco handoffs son cinco y esos; dos entraron el
   2026-08-01 en `fbb1cac`, anterior a `8f98133`; el censo indexado desde `docs/INDICE.md`.
3. **Contradicciones vivas.** ¿El choque §3 ↔ `GOBERNANZA` §5 está resuelto o solo reescrito? ¿Queda
   contradicción con `CLAUDE.md` y `AGENTS.md`, que no se han tocado? ¿Debería haberse tocado
   `CLAUDE.md`?
4. **Referencias muertas y citas rotas.** ¿Resuelven todas las nuevas? ¿Y las que el diff DECLARA
   muertas lo están de verdad? ¿Se rompió alguna cita al renombrar el §13 de identidad-segmento?
5. **El marco del censo, ¿es honesto?** ¿Es exacta la lista de ausencias? Cuenta tú las revisiones
   desde el 2026-07-23 y compara con las 28 filas. ¿«Congelado e incompleto pero indexado» es
   solución honesta o excusa?
6. **Supresiones.** Qué prosa se BORRÓ. ¿Se perdió alguna regla, matiz o dato sin sustituto?
   Atención al párrafo de polaridad del §7 y a las citas del censo.

## 1. Informe recibido, sin modificar

<!-- informe-literal:inicio:ghjk -->
# Revisión adversarial L3 — coherencia doctrinal y alcance

- **Objeto:** diff `8f98133..HEAD` de la rama `claude/audit-log-adversarial-reviews-df1d84`
  (4 commits: `dffb2cb`, `4340503`, `29163da`, `ec5bdc4`).
- **Commit revisado:** `ec5bdc4` (HEAD). Base: `8f98133`.
- **Fecha:** 2026-08-02.
- **Revisor:** Claude Code (sesión independiente, sin contexto de autoría), solo lectura.
- **Método:** todos los ficheros abiertos enteros; ninguna conclusión tomada del diff.
  `pytest tests/test_docs_gobernanza.py` ejecutado en solo lectura
  (`PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider --basetemp` fuera del árbol): **26 passed**,
  `git status --porcelain --untracked-files=all` vacío antes y después.

## VEREDICTO: REQUIERE-REVISION

No hay regla perdida, ni guard roto, ni riesgo de dato. Lo que hay es peor para este artefacto en
concreto: **tres afirmaciones que los documentos hacen sobre sí mismos y que la fuente desmiente**
—una ficha que se contradice tres líneas más abajo, un índice que promete digests que no existen y
un índice que reabre en un tercer documento la contradicción que el diff dice haber cerrado— más un
problema de registrabilidad de esta misma revisión (H-01). No es una lista de retoques: obliga a
volver a pasar la regla de recuento por las nueve fichas.

---

# Hallazgos

## H-01 — B0 — Esta revisión no puede registrarse como cobertura del contrato, y la rev. 9 no declara cobertura ninguna

`CLAUDE.md:44` y `AGENTS.md:79` dicen lo mismo y sin matices: el revisor sustituto —una sesión limpia de Claude Code— **«No cubre revisar el propio
contrato de revisión: ahí el sesgo compartido es justo el riesgo, y eso espera a Codex»**.

El objeto de esta rama **incluye el propio contrato**: `docs/superpowers/specs/2026-08-01-gobernanza-
revisiones-adversariales-design.md` cambia su §2 (lista de exclusiones), estrena §3.1 (frontera
acta/handoff, normativa), amplía §6 y reescribe §7. Yo soy una sesión de Claude Code. Por tanto:

- Mi lectura del **retrofit** (las nueve fichas, `tests/test_docs_gobernanza.py`, el censo,
  `docs/INDICE.md`) sí es cobertura admisible: el objeto no es el contrato.
- Mi lectura de **§2, §3.1, §6 y §7 del contrato y del §5 de `GOBERNANZA_FUENTES_VERDAD.md`** no lo
  es. Por doctrina propia del proyecto, eso **espera a Codex**.

Y hay un segundo tramo del mismo hallazgo, independiente de quién revise: **la rev. 9 no declara su
propia cobertura**. El §8 sigue publicando seis rondas y se cierra en la sexta; nada en el documento
dice si la rev. 9 pasó revisión, ni por quién. `CLAUDE.md` es explícito —«Un revisor que no corre no
refuta: deja sin verificar… se declara la cobertura ausente en el documento»—, y el propio §5 del
contrato lo repite (línea 183). Una rev. 9 del contrato de revisión que no dice quién la revisó es
justo el silencio que el documento existe para impedir.

**Remedio:** registrar la cobertura partida —presente para el retrofit, **ausente/pendiente de
Codex** para los cambios del contrato— en el encabezado de la rev. 9, con el nombre correcto del
revisor (`revisor: Claude Code (sesión independiente)`, nunca «Codex»).

## H-02 — A — La ficha del §10 de vista procesal declara «0 rebajados» y su propia tabla, tres líneas más abajo, publica seis ajustes de severidad

`docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:677`

```
- **Hallazgos:** 25 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
```

Línea 684, prosa **preexistente** que la ficha no tocó: «Los 25 hallazgos se aceptan en sustancia.
**Seis ajustes de severidad** y dos recortes de alcance». Y la tabla de las líneas 686-710 los
nombra uno a uno: H2 `BLOQ → ALTA`, H7 `BLOQ → ALTA`, H8 «Acepto **parcial**, ALTA», H9
`BLOQ → ALTA`, H19 «**baja a MEDIA**» (cinco a la baja), más H3 «**sube a BLOQ**» y H17 «**sube a
ALTA**» (dos al alza).

Cinco rebajas explícitas de severidad y una aceptación parcial, contadas como `25 confirmados · 0
rebajados`. Esto no es un matiz de vocabulario: es el §7 del propio diff —«**Cómo se escribieron los
recuentos, que es donde se inventa sin querer:** se **copia** lo que cada documento publica»—
incumplido en la misma tanda que lo escribe. El documento publica seis ajustes de severidad; la
ficha publica cero.

Agravante de método: en la **misma tanda de commits**, `rebajados` se usa con el sentido contrario.
`docs/superpowers/plans/2026-07-29-sandwich-firma-falso-positivo.md:1067` declara `1 rebajados` y la
prosa añadida explica que el rebajado es un hallazgo «parcialmente refutado» —refutado el método,
aceptada la conclusión—, que no es una rebaja de severidad. Dos significados incompatibles de la
misma casilla, escritos el mismo día. El contrato **no define ninguna de las cinco casillas** (§5,
líneas 159-173, solo resuelve el caso «remedio distinto del exigido»), y este diff, que estrena la
regla de recuento, tampoco.

## H-03 — A — `docs/INDICE.md:68` promete digest en nueve ficheros y solo cinco lo tienen

```
| `docs/superpowers/specs/*-adversarial-review.md` | vigente | **Las actas:** el informe del
revisor, literal y con su digest. Nueve al 2026-08-02. |
```

El glob casa nueve ficheros. **Cuatro no son actas y no tienen digest** — no tienen frontmatter en
absoluto (verificado abriendo los cuatro):

| Fichero | Primera línea |
|---|---|
| `2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md` | `# Revisión adversarial — Consumo de emails atomizados…` |
| `2026-07-26-gobernanza-indice-adversarial-review.md` | `# Revisión adversarial — Diagnóstico de gobernanza documental…` |
| `2026-07-27-cableado-atomize-sala-maquina-adversarial-review.md` | `# Revisión adversarial adjudicada — cableado atomize…` |
| `2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md` | `# Revisión adversarial — FeesDefender dual…` |

Los cinco restantes (las de gobernanza r1-r5) sí llevan `tipo: revision-adversarial` y
`sha256_informe`. Es decir: la fila del índice **atribuye a cuatro ficheros la propiedad probatoria
que el documento entero existe para garantizar**, y lo hace en la tabla cuyo encabezado dice «Dónde
vive cada pieza del rastro» (`docs/INDICE.md:61`). Un auditor que confíe en esa fila creerá que hay
nueve informes sellados y hay cinco.

Añadido: el contrato dice **«cinco actas»** en su §4 (línea 95) y en su §8 (línea 294); el índice
dice «nueve». Ninguno de los dos declara que hablan de poblaciones distintas.

## H-04 — A — `docs/INDICE.md:69` reabre, en un tercer documento, la contradicción que el §3.1 dice haber cerrado

```
| `docs/superpowers/handoffs/handoff-*-codex-*.md` | vigente | Informes de Codex archivados como
**handoff**, no como acta (`GOBERNANZA_FUENTES_VERDAD.md` §5, decisión de Nikolai del 2026-07-30).
**Sin digest:** su integridad no es comprobable. Cinco al 2026-08-02. |
```

Tres problemas, y son del diff, no heredados:

1. **Cita como regla viva la decisión que este mismo diff acota.** `GOBERNANZA_FUENTES_VERDAD.md`
   :189-191 dice literalmente que la decisión del 2026-07-30 queda **acotada** por la del
   2026-08-02, y §3.1 del contrato (líneas 73-74) manda el informe al acta «hacia delante». El
   índice presenta la decisión derogada como el porqué vigente de la fila.
2. **El estado es `vigente` sobre un glob abierto.** `handoff-*-codex-*.md` casa cualquier fichero
   futuro. El §3.1 (líneas 76-78) y `GOBERNANZA` :192-193 declaran el conjunto **cerrado y nombrado
   en cinco**. La fila no dice «cerrado» en ninguna parte: dice «Cinco al 2026-08-02», que es la
   gramática de un contador que crece. Un lector que archive el próximo informe de Codex como
   handoff estará siguiendo el índice y violando el contrato.
3. **«Informes» es impreciso para uno de los cinco.** El propio `docs/INDICE.md:103` llama a
   `handoff-2026-07-27-vista-procesal-codex-review.md` «**Handoff resumido** de esa misma 1ª
   pasada», y su frontmatter (`origen:`) lo confirma. Los cinco ficheros cubren **cuatro**
   revisiones: la 1ª de vista procesal tiene dos ficheros, informe completo y resumen. El §3.1 los
   presenta como cinco informes en bloque; por su propia frontera («handoff es el traspaso que no es
   un informe de revisión»), el resumen no necesitaba estar en la lista de excepciones.

## H-05 — A — El argumento «no estaba en el encargo» se aplica a una cosa y no a las otras dos del mismo diff

Esto es el punto 1 del mandato en su forma no disfrazada, y es el hallazgo que más me costó decidir
porque hay evidencia genuina en las dos direcciones.

**A favor del autor, y hay que decirlo:** el §6 (líneas 236-238) encuentra una ceguera de G7,
**mide** que se reproduce, y **se niega a arreglarla** —una línea de regex— con este razonamiento:
«No se hace en la rev. 9 porque el encargo del retrofit no lo incluía y ampliarlo por mi cuenta
sería la misma deriva que causó el recorte». Eso es contención real, contra el propio interés, sobre
el hallazgo que el autor mismo encontró. No es frecuente y no debe pasarse por alto.

**En contra:** ese mismo diff hace dos cosas que tampoco estaban en el encargo del retrofit y a las
que no se aplica el test:

- **El reencuadre del censo** (commit `29163da`). El §2 del contrato excluía, en rev. 8, «El censo de
  las 28 revisiones postcorte **y el retrofit** de los ocho encabezados heredados» (una sola línea,
  dos ítems). La rev. 9 saca el retrofit de la lista y **cualifica** el censo: «El censo … **como
  artefacto normativo**» (líneas 36-39). Ese «como artefacto normativo» no venía en el recorte: es
  una re-lectura del texto excluido que permite hacerle algo. Lo que se le hace —congelar, enmarcar,
  indexar desde `docs/INDICE.md`— no es normativo y no lo resucita, pero **la reescritura de una
  exclusión expresa para acomodar trabajo nuevo es exactamente la forma del H-07 de la sexta
  ronda**. El commit no la atribuye a nadie; el retrofit y el §3.1 sí se atribuyen a Nikolai.
- **El §3.1**, que sí se atribuye a una decisión de Nikolai del 2026-08-02.

**Mi juicio, para que no quede en insinuación:** ninguna de las siete cosas del §2 vuelve a entrar
en sustancia (respuesta detallada en el punto 1 de abajo). El censo no se convierte en registro
central: nadie está obligado a escribir en él, ningún guard lo mira y su propio marco lo declara
muerto. Pero la **asimetría del criterio** es real y es un defecto de coherencia: si «no estaba en el
encargo» basta para no tocar un regex de una línea que cierra una vía de fallo medida, no puede a la
vez no bastar para reescribir un bullet del §2 y añadir una sección al índice. Una de las dos
decisiones está mal calibrada, y la que protege menos es la que se tomó.

## H-06 — M — «Los nueve encabezados de adjudicación del corpus»: el corpus tiene quince, y el retrofit produjo diez

`docs/superpowers/plans/2026-08-01-migracion-revisiones-adversariales.md:71-73`:

> **Superado por el retrofit del 2026-08-02.** … Hoy **los nueve encabezados de adjudicación del
> corpus** casan el formato canónico y llevan ficha.

Reproduciendo la lógica exacta de `_adjudicaciones` + `_sin_cercas` + `_es_acta` sobre
`docs/superpowers/**/*.md`, el corpus de G7 contiene **15** encabezados disparadores fuera de cerca:
1 (`cableado…plan`) + 2 (`sandwich…plan`) + 1 (vista procesal) + 1 (email atomize) + 1 (dual
workspace) + 1 (sandwich design) + 1 (historial citado) + **5 del propio contrato** (§9-§13) + 2
(identidad segmento 13.1/13.2). Los quince casan; el conteo es el que está mal.

Y bajo la lectura caritativa —«nueve» = los ocho heredados más el noveno descubierto— tampoco cuadra
como **encabezados**: el noveno se partió en `13.1` y `13.2`, así que el retrofit dejó **diez**
encabezados canónicos, no nueve. El §7 del contrato (líneas 251-255) lo dice correctamente en
prosa; el marco del censo lo resume mal.

## H-07 — M — El marco del censo afirma que «sigue valiendo … dónde consta hoy», y esa columna tiene tres celdas rotas, una rota por este mismo diff

`…/2026-08-01-migracion-revisiones-adversariales.md:66-69` declara muertas `Clase`, `Tarea` y las
citas a `spec §1.3`/`§1.5`/«criterio 6», y remata: «**Sigue valiendo el resto:** objeto, ronda,
revisor y **«dónde consta hoy»**». No vale:

- **Filas 26-28** (líneas 105-107): «**§14** + acta r1», «**§15** + acta r2», «**§16** + acta r3».
  El contrato rev. 9 **termina en §13**; esas adjudicaciones son hoy §9, §10 y §11. Tres punteros a
  secciones inexistentes en la única columna que el marco declara sana.
- **Fila 19** (línea 98): «mismo plan, `:1089`». El encabezado está hoy en la **línea 1099**: el
  commit `dffb2cb` insertó diez líneas de ficha encima. **La rompió este diff**, y el mismo diff
  escribió, tres líneas más arriba, que esa columna sigue valiendo.
- **Fila 14** (línea 93): «§11 del spec: `NO-SHIP, **resuelto**`». El token es hoy `remediado`
  (lo cambió `dffb2cb`). El marco mete la fila 14 en el saco de las «notas de conformidad», que no
  es lo que le pasa.

Y una cita muerta más, dentro del bloque del censo y no declarada: línea 109, «Cobertura agregada,
no filas propias (**spec §1.2**)».

## H-08 — M — La lista de ausencias del censo no es exacta: faltan además las siete revisiones por tarea, excluidas por una regla que ya no existe

El marco (líneas 61-65) dice: «Le faltan, **como mínimo**, las rondas 4, 5 y 6 sobre el spec de
gobernanza … y las dos de `2026-08-01-identidad-segmento-bundle-design.md`». Las cinco son ciertas y
verificadas (§8 del contrato publica seis rondas y el censo solo tiene tres; `fbb1cac` mete los dos
handoffs de identidad-segmento).

Lo que el marco no dice: la línea 109 del propio censo excluye **siete revisiones más** —«las **7
revisiones por tarea** del build de cableado … se declaran en la `Cobertura` de la fila 7»— por una
regla del **`spec §1.2`**, que es una de las secciones que el recorte eliminó. O sea: siete
revisiones reales que no tienen fila, agregadas bajo una columna (`Cobertura`) que el marco no
menciona y por una regla que el marco no declara muerta aunque declara muertas sus vecinas §1.3 y
§1.5. El «como mínimo» cubre el flanco lógico, pero el inventario pasa de «28 + 5 ausentes» a
«**28 + 5 + 7**» y eso cambia cómo se lee el «único inventario» del índice.

## H-09 — M — «5 escalados» sin destino, contra la regla que el propio §7 estrena

`…/2026-07-29-sandwich-firma-falso-positivo.md:1105`: `6 confirmados · 0 rebajados · 0 refutados ·
**5 escalados** · 0 sin verificar`. Los cinco son los Minor 3, 4, 5, 6 y 8, y la tabla de la línea
1124 dice qué se hizo con ellos: «**ANOTADOS, no aplicados** … Quedan aquí por si el §6.7 se quiere
cerrar en una pasada futura».

El §7 del contrato, escrito en este mismo diff (línea 259): «los `escalados` se declaran **solo con
destino verificado**». En todas las demás fichas del diff `escalado` significa «tiene entrada propia
en `MEJORAS #NNN`» (#101, #102, #103, #107 — las cuatro verificadas y existentes). Aquí significa
«se quedan sin aplicar en este documento», que es precisamente lo que ya dice el
`estado_remediacion: parcial` del encabezado. Contarlos como escalados infla la casilla y le da un
segundo significado.

## H-10 — M — «El corpus de G7 es ahora todo `docs/superpowers/**/*.md` menos las actas» no es exacto: cuatro actas están dentro

Contrato §7, línea 249. El filtro real es `_es_acta`
(`tests/test_docs_gobernanza.py:347-348`), que exige `tipo: revision-adversarial` en el
frontmatter. Los cuatro ficheros de H-03 no lo tienen, así que **no se excluyen**: están en el
corpus de G7 pese a ser, materialmente, texto de revisor.

Hoy no falla (ninguno tiene un encabezado con el disparador; comprobado). Pero es exactamente el
modo de fallo que la exclusión existe para evitar y que el docstring del test nombra: «su informe
literal puede contener cualquier encabezado y no debe reinterpretarse como adjudicación del
proyecto». Con la lista `_ADJ_LEGACY` retirada, la frase del §7 describe un corpus que el código no
implementa, y la diferencia es de cuatro ficheros con texto de revisor dentro.

## H-11 — M — El §7 se corrigió a medias: «Construir: G7 y G8» y «Doctrina a tocar» siguen en futuro para trabajo ya mergeado

El mensaje de `ec5bdc4` fija el criterio: «El §2 y el §7 quedaron FALSOS en cuanto aterrizó el
retrofit … Dejar el contrato afirmando una exclusión que el trabajo acaba de levantar es la deriva
que este documento existe para impedir». De acuerdo. El criterio se aplicó al párrafo «No se
migra» y no a los dos párrafos que lo rodean, en la misma sección:

- Línea 242: «**Construir:** G7 y G8, con sus fixtures negativas. Es una tarde.» — construidos y
  mergeados en el PR #188 (`8f98133`), con 18 tests.
- Líneas 261-265: «**Doctrina a tocar:** `CLAUDE.md` … y `AGENTS.md` añade tres cosas…» — tocada en
  el mismo PR #188 (`CLAUDE.md` §Revisión adversarial y `AGENTS.md` :31-83, ambos vigentes hoy).

Un §7 titulado «Qué hay que construir» que enumera como pendiente lo que ya está en `main` es la
misma falsedad de estado que el commit dice venir a corregir, dos párrafos más abajo.

## H-12 — M — La regla de polaridad pasó de norma del contrato a comentario de test

Suprimido en `docs/superpowers/specs/…-design.md` §7:

> «La polaridad **es la decisión**: una lista de inclusión … dejaría escapar cualquier fichero
> **nuevo** con una adjudicación mal formada; la de exclusión cubre el futuro por defecto y **solo
> puede encoger**.»

La sustitución conserva el razonamiento pero **en pasado** («Esa lista **solo podía encoger**, y
encogió a cero», línea 247) y traslada la forma prospectiva a un comentario de
`tests/test_docs_gobernanza.py:294-298` («se deja dicha **por si alguien vuelve a necesitarla**»).
Resultado: el contrato ya no contiene la regla que gobierna el día en que alguien necesite volver a
excluir un fichero; la contiene un comentario en un `.py`. No es pérdida total —está escrita— pero
sí degradación de rango, y el hogar del razonamiento normativo es el contrato, no el test que lo
implementa. Es el patrón «suprimir prosa normativa es cambio de contenido» en versión suave.

## H-13 — M — Tres redacciones distintas del nombre del acta, y esto sí obligaba a tocar `CLAUDE.md`

- Contrato §4, línea 91: `AAAA-MM-DD-<tema>-r<N>[-<revisor>]-adversarial-review.md`.
- `docs/GOBERNANZA_FUENTES_VERDAD.md:183`: `docs/superpowers/specs/AAAA-MM-DD-<tema>-adversarial-review.md`.
- `CLAUDE.md:29`: «un **acta hermana** `…-adversarial-review.md`».

Las dos últimas **omiten el `-r<N>`**, que es lo único que hace el nombre función de la identidad
(una acta por ronda, §4 línea 92). Ningún guard comprueba el nombre del acta —G8 valida frontmatter,
no fichero—, así que la única defensa es la prosa, y la prosa dice dos cosas. El diff tocó
`GOBERNANZA` §5 justo dos líneas por debajo de :183 y no lo alineó. La bitácora del 55º cierre
identifica esta causa raíz por su nombre: «restatar la misma regla con palabras distintas en dos
sitios».

## H-14 — M — Puntero muerto al `§12` en el handoff que la propia ficha 13.1 cita como su informe

`docs/superpowers/handoffs/handoff-2026-08-01-identidad-segmento-codex-review.md`:

- línea 7 (`consumido_por`): «rev. 2 de la spec (**§12** mapea cada hallazgo a la sección que lo corrige)».
- línea 18 (cuerpo): «**Adjudicación de Claude Code:** en el **§12 de la spec**, no aquí».

El §12 de `2026-08-01-identidad-segmento-bundle-design.md` es hoy «Radio de la migración (medido)»
(línea 282). La adjudicación está en §13 / §13.1. El §7 del contrato afirma que el partido de §13 se
hizo «sin renumerar, **para que las citas al §13 sigan resolviendo**» — y es cierto para las tres
citas a §13 (`docs/INDICE.md:98`, `:99`, y el cuerpo del handoff `-review-2.md:19`), que verifiqué
una a una. Pero el barrido buscó «§13» y no vio que el fichero hermano —el que la nueva ficha 13.1
nombra como su «Informe recibido»— apunta a **§12**. Es preexistente; el diff lo hereda y su propia
declaración de integridad de citas lo tapa.

## H-15 — M — `PLAN.md:2193` sigue diciendo que el retrofit y el censo quedaron fuera

La entrada del ledger `[GOBERNANZA-REVISIONES]` (`PLAN.md:2193`) enumera lo excluido por el recorte:
«fuera el predicado de población, los ejes de clasificación, el *fail-closed*, **el censo de 28 y el
retrofit de los ocho encabezados heredados**» y cita el contrato como «(rev. 8)». Tras esta rama, el
retrofit está hecho y el contrato es rev. 9. `PLAN.md` no se toca en el diff.

Es defendible como descripción histórica del PR #188, pero el ledger no está redactado en pasado:
está redactado como el estado del asunto. Si el cierre de sesión no añade la entrada de esta rama,
el ledger queda afirmando una exclusión levantada — el mismo defecto que `ec5bdc4` corrige en el §2.
**SIN VERIFICAR** si el `/cierre` previsto lo cubre.

---

# Respuesta al mandato, punto por punto

## 1. ¿Se reabrió alcance excluido?

**No en sustancia, ninguna de las siete.** Comprobado abriendo el §2 (líneas 31-47) y buscando cada
ítem en el árbol:

| Excluido en rev. 8 | ¿Vuelve? | Evidencia |
|---|---|---|
| Predicado de población | No | Sin predicado en el spec; `_md_superpowers()` recorre todo `docs/superpowers/**` sin condición de pertenencia. |
| Taxonomía de clases e independencia | No | `_CAMPOS_FICHA` (`tests/…:285-286`) son seis y no incluyen `Clase`/`Cobertura`/`Independencia`; **ninguna de las nueve fichas nuevas los lleva** (comprobadas las nueve). |
| Regla *fail-closed* y allowlists | No | El §6 (líneas 215-222) mantiene G8 como *opt-in* por campo y **declara el agujero** en vez de cerrarlo. |
| Regla de parada de rondas | No | Sin disparador de parada en el texto. |
| Trailer `Revision-cierre:` | No | Cero ocurrencias en el árbol. |
| Registro central | No — ver (a) | — |
| Generador de censo / G9 | No | Sin script; `test_censo_suma_28` **no existe** (grep en `tests/`). |

**(a) ¿El marco convierte el censo en registro central de facto?** No. Un registro central es un
artefacto **que hay que mantener**; este está congelado por decisión escrita, no lo comprueba ningún
guard, no impone obligación de escritura a nadie, y su propio encabezado se declara incompleto y
nombra sus columnas muertas. La medición que justifica indexarlo es además **cierta y la verifiqué**:
`git grep migracion-revisiones-adversariales 8f98133` devuelve **una sola línea, dentro del propio
fichero** — cero referencias externas antes del diff. Dicho eso, la re-escritura del bullet («como
artefacto normativo») es una cualificación *ex post* de una exclusión expresa: ver **H-05**.

**(b) ¿Las fichas reintroducen la taxonomía?** No. Verificado campo a campo en las nueve. Los campos
`Clase:` y `Cobertura:` sí existen en el árbol, pero **solo dentro de las plantillas cercadas del
plan archivado** (p. ej. `…-migracion-…md:1007-1015`), que el diff no toca y que `_sin_cercas`
neutraliza. Ninguna ficha viva los lleva.

**(c) ¿La §3.1 crea regla nueva o registra una decisión ya tomada?** **Registra**, con un matiz que
conviene decir. El «hacia delante» (el informe al acta) ya estaba en §3 y en `CLAUDE.md`; §3.1 no lo
inventa, lo hace explícito frente al §5. Lo genuinamente nuevo es el **cierre del conjunto en cinco**
y la declaración de que nunca tendrán digest — y eso es una decisión, atribuida a Nikolai el
2026-08-02. **SIN VERIFICAR** esa atribución: no hay artefacto en el repo que la acredite (igual que
la del 2026-07-30, que sí tiene rastro en `docs/bitacora/2026.md`). Es la práctica establecida del
proyecto y no la trato como hallazgo, pero el lector debe saber que en un documento cuya tesis es
«nadie puede contrastar lo que dijo el revisor con lo que yo digo que dijo», las decisiones del
principal se sostienen solo en mi narración.

## 2. Afirmaciones de la rev. 9 que el diff no sostiene

Verificadas una a una:

| Afirmación | Veredicto | Cómo |
|---|---|---|
| `_ADJ_LEGACY` se retiró vacía | **CIERTA** | `git grep _ADJ_LEGACY` → solo dos menciones en prosa/comentario; el `frozenset` ya no existe; `test_adjudicaciones_bien_formadas` filtra solo por `_es_acta`. Suite de guards **26 passed**. |
| Los nueve encabezados casan | **FALSA como está escrita** | Casan **quince**; el retrofit produjo **diez**. Ver **H-06**. La sustancia (todo lo retrofitado conforma) sí se sostiene. |
| Los cinco handoffs son cinco y esos cinco | **CIERTA con imprecisión** | `ls` da exactamente los cinco nombrados. Pero cubren **cuatro** revisiones y uno es un resumen, no un informe (**H-04.3**). El sexto candidato, `handoff-2026-07-26-gobernanza-indice-adversarial.md`, lo abrí: es el **encargo**, no un informe — correctamente fuera. |
| Dos entraron el 2026-08-01 en `fbb1cac`, un commit antes del contrato | **CIERTA, exacta** | `git log --diff-filter=A` sitúa los dos en `fbb1cac` (2026-08-01 12:51); `git log --format=%p 8f98133` → `fbb1cac` es su **padre directo**. Los otros tres entraron en `404630f`. |
| El censo está indexado desde `docs/INDICE.md` | **CIERTA** | `docs/INDICE.md:67`. Y la premisa («no lo citaba nadie») verificada en `8f98133`. |

Extra no pedido y falso: `docs/INDICE.md:68`, «nueve actas con su digest» (**H-03**).

## 3. Contradicciones que queden vivas

**¿Está resuelto el choque §3 / `GOBERNANZA` §5?** En los dos textos nuevos, **sí, y bien**: los leí
enteros (contrato :66-87 y `GOBERNANZA` :164-202). Dicen lo mismo, con la misma frontera («informe de
revisión de spec/plan/diff → acta; traspaso que no es informe → handoff»), el mismo conjunto cerrado
de cinco, el mismo precio declarado (sin digest, y por qué sellarlos ahora sería peor) y referencia
cruzada en ambos sentidos. No es una reescritura cosmética: la regla anterior era genuinamente
ambigua para un informe de Codex y ahora no lo es.

**Pero el choque migró a un tercer documento:** `docs/INDICE.md:69` (**H-04**), que cita la decisión
derogada como vigente sobre un glob abierto. Resuelto en dos sitios, reabierto en el tercero.

**Contradicciones residuales:**

- `GOBERNANZA:179-180` sigue hablando de «los handoffs de **revisión adversarial recibida**» como
  categoría con ejemplos de campos, dos líneas antes de que :192-193 la cierre en cinco. No es
  falso, pero se lee como categoría abierta.
- El nombre del acta, en tres versiones (**H-13**).

**¿Debería haberse tocado `CLAUDE.md`?** Lo abrí y lo comparé con los dos textos nuevos:

- **Para la frontera acta/handoff: no.** `CLAUDE.md:27-32` nunca mencionó el handoff; dice
  «adjudicación embebida, informe al acta», que es exactamente lo que la §3.1 confirma hacia
  delante. No hay contradicción que arreglar.
- **Sí para el nombre del acta** (`CLAUDE.md:29`, sin `-r<N>`): **H-13**.
- **Y hay un tercer motivo, más importante:** `CLAUDE.md` es la doctrina que se carga en toda sesión,
  y hoy no dice en ninguna parte que existan cinco informes sin digest. Un lector de `CLAUDE.md`
  concluye que el rastro de toda revisión está sellado. La corrección la lleva `docs/INDICE.md`… que
  es justo donde está mal escrita (**H-03**, **H-04**). Una línea en `CLAUDE.md` —«cinco informes
  anteriores al contrato viven como handoff, sin digest; conjunto cerrado»— cerraría el círculo.

## 4. Referencias muertas y citas rotas

**Resuelven** (abiertas una a una): `§3.1`, `§7`, `§6` del contrato existen con esos números; los
cinco nombres de handoff existen en `docs/superpowers/handoffs/`; `MEJORAS #101` (línea 4012), `#102`
(4041), `#103` (4070), `#105` (4136) y `#107` (4215) existen **y describen lo que la ficha dice que
describen** (contrastados contra los hallazgos M-3/M-4/M-5 del acta dual, líneas 454-462); los doce
hashes citados en las fichas resuelven en `git log` (`aaf7dc1`, `12c8a91`, `31b5943`, `8d9c96c`,
`f965716`, `05d985f`, `3126214`, `2c2a6d0`, `1a6e3d8`, `24f8abe`, `bbd1fba`, `95ec3fe`);
`docs/INDICE.md` §Censo apunta al `## Censo de la población postcorte` real.

**Las declaradas muertas lo están de verdad:** `grep` sobre el contrato rev. 9 → sin `§1.3`, sin
`§1.5`, sin «criterio 6»; el §1 no tiene subsecciones. Correcto.

**No resuelven, y no están declaradas:**
- Filas 26-28 del censo → `§14`, `§15`, `§16` (hoy §9/§10/§11). **H-07**.
- Fila 19 → `:1089`, hoy `:1099`, **rota por este diff**. **H-07**.
- Censo línea 109 → `spec §1.2`. **H-07** / **H-08**.
- Y fuera del bloque del censo, en el mismo plan ahora indexado: 15 ocurrencias de `spec §…`
  (líneas 134, 1173, 1247, 1306, 1389…) apuntando a la numeración de la rev. 5. Varias no solo
  están muertas: **resuelven a otra cosa** (el «spec §10 y §10.1 = doctrina» de la línea 134 cae hoy
  en la adjudicación de la ronda 2). Indexar el fichero desde `docs/INDICE.md` sube el coste de esto.

**El renombrado del §13 de identidad-segmento no rompió nada.** Las tres citas existentes a `§13`
(`docs/INDICE.md:98`, `:99`, `handoff-…-review-2.md:19`) siguen resolviendo: verificadas. Lo que el
barrido no vio es el puntero a `§12` del handoff hermano: **H-14**.

## 5. El marco del censo, ¿es honesto?

**La lista de ausencias no es exacta.** Las cinco declaradas son ciertas (§8 del contrato publica
seis rondas y el censo tiene tres; los dos de identidad-segmento entraron en `fbb1cac`). Falta,
además, el bloque de **7 revisiones por tarea** del build de cableado, que la propia línea 109
excluye de tener filas por una regla (`spec §1.2`) que ya no existe — **H-08**. El inventario real
desde el 2026-07-23 no es 28 ni 33: es **≥ 40**.

Verifiqué también los candidatos que podrían faltar y **no faltan**: las revisiones de rama de la
Fase 0 dual (PR #170/#174) no existen como pasadas propias —`PLAN.md:21` dice «Gate de revisión
consumido (**3 pasadas** adjudicadas, sin 4ª)», que son las filas 11-13—; y el
`handoff-2026-07-26-gobernanza-indice-adversarial.md` está cubierto por la fila 3.

**¿«Congelado e incompleto pero indexado» es honesto o una excusa?** **Honesto en la decisión, y
sobrevendido en la ejecución.** A favor: congelar y declarar incompleto es estrictamente mejor que
mantener a mano un inventario que nadie comprueba, y el razonamiento («el contrato §2 excluye un
registro central, y un inventario actualizado a mano es eso mismo mal hecho») es correcto y coherente
con el recorte, no una excusa para no trabajar — el trabajo alternativo estaba **prohibido** por el
recorte. Y el problema que arregla es real y medido: cero referencias externas al fichero.

En contra, y por eso no lo doy por bueno sin más: un artefacto que se congela debe dejar dicho **qué
partes de él ya no se pueden usar**, y este se queda corto en tres sitios —afirma que «dónde consta
hoy» sigue valiendo cuando tres celdas apuntan a secciones inexistentes y una la rompió el propio
diff (**H-07**), omite siete revisiones de la cuenta de ausencias (**H-08**), y `docs/INDICE.md:67`
lo vende como «**El único inventario**» sin advertir que sus referencias cruzadas están caducadas—.
La honestidad de la etiqueta no se transfiere automáticamente al contenido etiquetado.

## 6. Supresiones

Repasado el diff con `-U0` filtrando solo las líneas eliminadas (32 líneas). Ninguna supresión deja
una regla sin sustituto **en sentido estricto**, pero hay una degradación de rango y dos matices:

- **Párrafo de polaridad exclusión/inclusión (§7).** Sobrevive el razonamiento, dos veces —en pasado
  en el spec (:244-249) y como comentario en `tests/…:294-298`—. Lo que se pierde es la **forma
  prospectiva dentro del contrato**: la regla que gobierna el próximo intento de excluir un fichero
  ya no vive en el documento normativo. **H-12**.
- **Frase del censo sobre «spec §1.5» y «criterio 6».** Suprimida y **correctamente** declarada
  muerta en el marco; verifiqué que ni `§1.3`, ni `§1.5`, ni «criterio 6» existen ya en el contrato.
  Sin hallazgo. (Pero la misma frase suprimida contenía `spec §1.3` **y sobrevive `spec §1.2`** en la
  línea 109, no declarada: **H-07**.)
- **Bullet del §5 de `GOBERNANZA`** («un informe recibido de un agente externo … sí es un handoff»).
  Sustituido con ganancia: el nuevo texto conserva la regla para lo que no es informe de revisión y
  acota lo demás. Sin pérdida.
- **Encabezados de adjudicación viejos.** Los ocho se reescriben con **más** información, no menos.
  Dos cambios de token merecen elogio explícito porque van contra el interés del autor: `aplicados` →
  `parcial` en `sandwich…plan:1099` («El token anterior … los daba por cerrados») y `resuelto` →
  `remediado` en `email-atomize…:455`. Eso es corregir a la baja el propio historial.
- **`## 13. Adjudicación de las revisiones adversariales`** → `## 13. Las dos revisiones
  adversariales de Codex`. La prosa de la 1ª y 2ª pasada se conserva íntegra dentro de 13.1/13.2.
  Sin pérdida.

---

# SIN VERIFICAR

1. **La atribución a Nikolai** del encargo del retrofit y de la decisión del 2026-08-02 (§3.1). No
   hay artefacto en el repo que la acredite; la del 2026-07-30 sí tiene rastro en
   `docs/bitacora/2026.md`. No lo trato como hallazgo (es la práctica del proyecto), pero queda dicho.
2. **Si el cierre de sesión previsto actualizará `PLAN.md`** y la bitácora con esta rama (**H-15**).
3. **La suite completa.** Corrí solo `tests/test_docs_gobernanza.py` (26 passed). El diff no toca
   producción, pero el conteo global de la suite no lo verifiqué.
4. **El contenido de los cinco handoffs de Codex frente a lo que las fichas dicen que dicen.** Abrí
   sus cabeceras y frontmatter, no los informes íntegros; los recuentos de 13.1/13.2 los contrasté
   contra `docs/INDICE.md:98-99` y la tabla del §13.2, no contra el texto del revisor.
5. **Cobertura adversarial de los cambios del contrato (§2, §3.1, §6, §7) y del §5 de
   `GOBERNANZA`:** **AUSENTE**. Por `CLAUDE.md` y `AGENTS.md`, un revisor sustituto de Claude Code no
   cubre el propio contrato de revisión. Lo que digo arriba sobre esas secciones es lectura, no
   cobertura. **H-01**.
<!-- informe-literal:fin:ghjk -->

## 2. Evidencia verificada al adjudicar

Verificado por mí, contra la fuente y no contra el diff, antes de adjudicar. Detalle
hallazgo por hallazgo en el §14 del objeto; aquí lo que reproduje con ruta y línea:

- **`2955f65` consta** en `docs/superpowers/handoffs/handoff-2026-07-27-vista-procesal-codex-informe.md:34`
  («El spec se revisó desde la rama local `claude/intake-crm-sudespacho-a7fc5a` (`2955f65`)») y el
  commit existe en git. Mi ficha decía `commit: no registrado`: declaraba ausente lo que la fuente
  que ella misma cita registra.
- **`docs/bitacora/2026.md:146` nombra al revisor** de la rama del sándwich: «La de rama (opus)
  devolvió LISTA CON CAMBIOS con 3 Important». Mi ficha decía `no registrado`.
- **La tabla del §10-bis de historial citado da 8 B0 + 3 A + 2 M** contando su columna `Sev`
  (`9`,`1`,`3,4,5,6`,`2,7` → 8 B0; `8`,`10`,`11` → 3 A; `13`,`12` → 2 M), no el «7 B0 + 4 A + 2 M»
  que escribí «de la tabla». El total, 13, sí cuadra por las dos vías.
- **G7 era vacuo**: mutando los 15 encabezados del corpus al plural, `_adjudicaciones` observa 0 y
  `_errores_adjudicacion` devuelve 0 errores → módulo entero verde. Reproducido con los propios
  helpers del guard y luego sobre el árbol real.
- **Las actas no tienen garantía uniforme**: 9 ficheros `*-adversarial-review*.md`, 5 declaran
  `sha256_informe`, y solo 2 llevan `marcador_nonce` (las únicas que G8 recomputa). Mi fila del
  `INDICE` prometía digest en las nueve.
- **El corpus de G7 tiene 15 encabezados en 9 ficheros**, no nueve.
- **Los 5 Minor del sándwich de rama no tienen destino**: sin entrada en `docs/MEJORAS_FUTURAS.md`
  ni en `PLAN.md`. Contra los que sí lo tienen y verifiqué existiendo y diciendo lo afirmado:
  `MEJORAS #107`, `#101`, `#102`, `#103`.
- **`plans/2026-08-01-migracion-revisiones-adversariales.md:1262` ya avisaba** de que un encabezado
  de autorrevisión no lo detecta el disparador. Está en el fichero que yo reencuadré.
- **Suite** tras la remediación: `python -m pytest tests/test_docs_gobernanza.py` → 27 tests, y la
  mutación al plural sobre el corpso real ahora sale ROJA con diagnóstico.

**Independencia, sin maquillaje.** Los tres revisores son sesiones de Claude Code sin contexto de
autoría, no Codex. Misma familia de modelo que el autor: **puntos ciegos compartidos**, y sin la
tensión de interés que en rondas anteriores hizo que Codex argumentara contra la ampliación de sus
propios permisos. Compensado con tres lentes en paralelo y mandatos que prohíben dar nada por bueno
sin abrir el fichero. Registrado como `Claude Code (sesión independiente)` y **nunca como «Codex»**,
según `AGENTS.md` §«Revisor sustituto».
