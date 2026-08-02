# Archivo verificable de las revisiones adversariales

> **Estado:** **rev. 9** (2026-08-02). La rev. 9 **no reabre nada del recorte**: registra que el
> retrofit de los encabezados heredados se ejecutó (§7), fija la frontera entre acta y handoff que
> el §3 y `GOBERNANZA_FUENTES_VERDAD.md` §5 contradecían (§3.1), y declara una ceguera medida de G7
> (§6). Todo lo demás sigue como en la rev. 8, cuyo encabezado se conserva íntegro debajo.
>
> **Estado anterior:** **rev. 8** (2026-08-01). **Alcance recortado por decisión de Nikolai**, sobre el H-07 de la
> sexta revisión: el disparador del §11 de la rev. 6 decía «otra costura», aparecieron siete, y yo
> redefiní el disparador después. Un revisor sin nada invertido lo llamó racionalización *ex post* y
> tenía razón. Este documento es lo que queda tras el recorte: **el núcleo probatorio, y nada más**.
> **Origen:** pregunta de Nikolai (2026-08-01) — ¿hace falta documentar el diálogo entre Claude Code y
> Codex en las revisiones de specs y planes, cómo se estructura y cómo puede auditarse?
> **Historia y evidencia del recorte:** §8, con las seis rondas y sus cinco actas.

## 1. Qué problema resuelve

Cuando Codex revisa un spec o un plan, hoy queda mi resumen de lo que dijo. Yo soy la parte revisada, y
soy el único narrador: nadie puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**. Eso
es lo que se arregla.

No es un control de calidad —para eso ya está la revisión misma, que es obligatoria por `CLAUDE.md`—.
Es **cadena de custodia**: el original se conserva, la decisión se escribe al lado, y ambos se pueden
comprobar después sin haber estado delante.

## 2. Alcance

**Dentro:** las revisiones adversariales de un spec, un plan o un diff **que produzcan un informe
externo** — hoy, en la práctica, las de Codex.

**Fuera, y por decisión expresa tras el recorte:**

- El predicado de población y la taxonomía de clases e independencia.
- La regla *fail-closed* que ligaba cobertura a la existencia del acta, y sus allowlists.
- La regla de parada de rondas y el trailer `Revision-cierre:`.
- El censo de las 28 revisiones postcorte **como artefacto normativo**. Sigue fuera: no se mantiene
  al día ni lo comprueba ningún guard. Lo que sí se hizo el 2026-08-02 fue **congelarlo, declararlo
  incompleto e indexarlo** desde `docs/INDICE.md`, para que se pueda encontrar. Vive donde nació,
  en el §Censo del plan archivado.
- El plan de migración de diez tareas, **archivado sin ejecutar**.
- Un registro central, un generador de censo y cualquier guard G9.

> **Lo que sí entró después, y por qué no es reabrir el recorte.** La rev. 8 dejaba fuera el
> **retrofit de los ocho encabezados heredados**; Nikolai lo encargó el 2026-08-02 y está hecho
> (§7). Era la mitad barata de lo que cayó —trabajo documental acotado, sin norma nueva— y su
> resultado es que el corpus de G7 ya no tiene exclusiones. Lo que sigue fuera es lo caro y lo
> normativo: predicado, taxonomía, *fail-closed*, regla de parada, trailer de gate y generador.

**Lo que se pierde, dicho claro:** las revisiones de rama —que son las que más defectos caros han
comprado en este proyecto— vuelven a no dejar rastro obligatorio, y no hay forma de responder «qué se
revisó en julio» salvo con `grep`. Se acepta a cambio de tener un mecanismo pequeño que funcione, en vez
de uno grande que no se termina.

## 3. Los tres artefactos

| Artefacto | Hogar |
|---|---|
| **Mandato** — qué se pidió atacar | Acta, **§0**, literal |
| **Informe recibido** — la voz del revisor | Acta, **§1**, entre marcadores con nonce, con su digest |
| **Adjudicación** — qué acepté, qué refuté y dónde se remedia | Sección embebida en el spec o el plan revisado |

La adjudicación va embebida porque la decisión pertenece al documento que la decisión modificó. El acta
es el archivo de la voz del revisor, **no** un segundo hogar de la decisión: no lleva estado de
remediación.

### 3.1. Acta o handoff: la frontera, y los cinco que se quedan fuera

Este §3 y el §5 de `GOBERNANZA_FUENTES_VERDAD.md` decían cosas distintas y ninguno lo declaraba. El
§5 recoge una **decisión de Nikolai del 2026-07-30**: un informe **recibido de un agente externo**
para arrancar trabajo aquí es un handoff. Codex es un agente externo, así que un informe suyo caía
en las dos reglas a la vez. Resuelto el 2026-08-02, decisión de Nikolai:

- **Hacia delante:** el informe de una revisión adversarial **de un spec, un plan o un diff** va al
  **acta**, con sus marcadores y su digest. Manda este contrato.
- **Handoff** sigue siendo el hogar del traspaso de contexto que **no** es un informe de revisión.
- **Los cinco que ya están archivados como handoff se quedan donde están**, como conjunto **cerrado
  y nombrado**: `handoff-2026-07-27-vista-procesal-codex-{informe,review,review-2}.md` y
  `handoff-2026-08-01-identidad-segmento-codex-review{,-2}.md`.

**El precio, dicho entero:** esos cinco **no tienen digest y nunca lo tendrán**. El §4 fija que el
valor probatorio del hash viene de calcularlo **al recibir** y contrastarlo con el que declara el
revisor; para estos cinco ese momento pasó. Sellarlos hoy produciría un autosello con aspecto de
prueba —el revisado firmando su propia transcripción—, que es exactamente lo que este documento
existe para impedir. Su integridad la sostiene solo el historial de git. Queda declarado.

**No son «excepción histórica»**, y la palabra importa: dos de los cinco entraron el 2026-08-01, un
commit antes de que mergeara este contrato. Era la práctica viva, no un residuo de julio.

## 4. El acta

**Nombre:** `AAAA-MM-DD-<tema>-r<N>[-<revisor>]-adversarial-review.md`, junto al documento revisado
(`specs/` o `plans/`). El revisor solo cuando dos comparten ronda. **Un acta por ronda**: el frontmatter
es escalar.

> Las cinco actas ya escritas conservan los nombres que tienen, que siguen tres esquemas distintos de las
> revisiones sucesivas. No se renombran: sería churn sin lector.

**Frontmatter:**

```yaml
---
tipo: revision-adversarial
objeto: docs/superpowers/specs/<fichero>.md      # o el diff/rama revisado
objeto_rev: "1"
commit: abc1234                                  # el commit revisado
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: zx7q
sha256_informe: <digest canónico, 64 hex>
adjudicado_en: docs/superpowers/specs/<fichero>.md §14
---
```

`veredicto` es el del revisor, normalizado, y **es inmutable**. No hay guard que lo compruebe: el intento
de la rev. 7 —exigir que apareciera en el bloque literal— resultó inútil porque `SHIP` está contenido en
`NO-SHIP`. Lo que delata una edición es el diff del commit.

**Contenido:** **§0 Mandato** (literal, numerado y en el orden de daño en que se entregó), **§1 Informe
recibido, sin modificar**, **§2 Evidencia verificada** por mí al adjudicar, con ruta y línea. Lo que el
guard exige es el **número y el prefijo** —`## 1. Informe recibido…` y `## 2. Evidencia verificada…`—; el
resto del titular es libre, y de hecho las actas insertan ahí el nombre del revisor.

El mandato va **siempre en §0 y literal**. Las versiones anteriores admitían un puntero al objeto, y eso
produjo dos defectos seguidos: un puntero con sintaxis inválida y otro que resolvía a una sección donde
el mandato numerado no estaba. Copiarlo cuesta menos que gobernar su gramática. **Las cinco actas ya
escritas no lo tienen** —sus mandatos se entregaron por chat y no se archivaron— y no se reconstruyen:
el recorte descarta el retrofit. La obligación rige para las nuevas.

**Marcadores con nonce**, obligatorios:

```
<!-- informe-literal:inicio:<nonce> -->
…el informe…
<!-- informe-literal:fin:<nonce> -->
```

El nonce se declara en `marcador_nonce` y se elige **de modo que no aparezca en el informe**, con letras
**no hexadecimales** para que no pueda esconderse dentro de un digest citado. No es teoría: el informe de
la cuarta ronda contenía el token de fin, y con marcadores planos su archivado se habría cortado por la
mitad.

**El digest es del texto canonicalizado:** UTF-8, finales `LF`, un único salto final. La misma forma al
recibir y en el guard. Se calcula **al recibir el informe** y se compara con el que declara el revisor:
ese es el único momento en que existe prueba independiente de origen. Después el acta se autoverifica.

**Frontera de confianza, declarada.** El guard detecta que alteren el bloque; una edición coordinada de
bloque y digest pasaría, y lo que la delata es el diff. Pero eso **no es inmutabilidad**: `STATUS.md:6`
documenta que el historial de git fue reescrito y el repo recreado el 2026-07-07. La garantía real es
**consistencia bajo el historial retenido**. Resistir al administrador del repo exigiría un tag firmado o
publicar el digest fuera, y **no se construye**.

## 5. La adjudicación

```
## [N.] Adjudicación de la revisión adversarial [<calificador>] (<revisor>, <AAAA-MM-DD>) — <VEREDICTO>, <estado_remediacion>
```

Debajo, **seis líneas**:

```markdown
- **Objeto revisado:** `<ruta>` rev. N, commit `abc1234`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `<acta>.md` | no capturado — <motivo>
- **Hallazgos:** N confirmados · N rebajados · N refutados · N escalados · N sin verificar
- **Remediado en:** PR #NNN (`hash`) | rev. N de este documento | pendiente
```

Más una tabla hallazgo → severidad → veredicto → dónde se remedia, y la prosa de las divergencias.

`commit: no registrado` y `no capturado` son valores legítimos: **no se inventa lo que no consta**. Un
hallazgo aceptado con remedio distinto del exigido cuenta como confirmado, y la divergencia se razona.

**Vocabularios cerrados.** `veredicto`: `SHIP` · `LISTA-CON-CAMBIOS` · `REQUIERE-REVISION` · `NO-SHIP` ·
`NO-EJECUTABLE` · `SIN-VEREDICTO`. `estado_remediacion`: `remediado` · `parcial` · `sin-cambios` ·
`pendiente`.

> **Tercera población de vocabularios.** No comparte set con `_ESTADOS_DOCS` ni `_ESTADOS_HANDOFF`. La
> cabecera de `tests/test_docs_gobernanza.py` explica por qué unificarlos rompe 11 ficheros (trampa D3).
> El campo se llama `estado_remediacion` y no `estado`: colisión imposible por construcción.

**Y si la revisión no corrió, se declara.** Un revisor que no corre no refuta: deja sin verificar
(`docs/DEAD_ENDS.md`). No se da por cubierto lo que nadie miró.

## 6. Los dos guards

En `tests/test_docs_gobernanza.py`, población separada.

**G7 — adjudicación bien formada.** Toda línea de encabezado que contenga «Adjudicación de la revisión»,
**fuera de bloques cercados**, casa el regex del §5 con `veredicto` y `estado_remediacion` de los sets
cerrados, y va seguida de las seis líneas de la ficha. Los ficheros con `tipo: revision-adversarial`
quedan fuera: el informe literal puede contener cualquier encabezado.

```python
_RE_ADJUDICACION = re.compile(
    r"^#{2,3}\s+(?:\S+\s+)?"
    r"Adjudicación de la revisión adversarial"
    r"[^(\n]*"
    r"\((?P<revisor>[^,)]+),\s*(?P<fecha>\d{4}-\d{2}-\d{2})\)"
    r"\s*—\s*(?P<veredicto>[A-Z-]+),\s*(?P<estado>[a-z-]+)\s*$",
    re.MULTILINE)
```

Eliminar las cercas **antes** del match no es precaución: la plantilla de arriba, dentro de su cerca, fue
detectada como encabezado real por el grep de censo de la primera revisión. El corpus de G7 incluye este
documento, y si vuelve a detectarla, falla.

**G8 — acta bien formada.** Frontmatter con las claves del §4 y vocabulario válido; `adjudicado_en`
resuelve a **fichero y sección** existentes; existen §1 y §2; **exactamente un par** de marcadores con el
`marcador_nonce`, en orden; y el digest del bloque canonicalizado **se recomputa y coincide** con
`sha256_informe`. **Una desigualdad es roja, nunca aviso**: un aviso convierte una cadena rota en suite
verde.

**G8 es opt-in por campo, y esa es su frontera declarada.** Se aplica a toda acta que declare
`marcador_nonce`, que es lo que el §4 exige a las nuevas. Las tres primeras —`…-adversarial-review.md`,
`-r2` y `-r3`— son anteriores a ese contrato: delimitan el bloque con `---` y **quedan fuera**. No se
retrofitan y no hay lista que mantener: el campo es la adhesión.

El precio, dicho sin adornos: **omitir `marcador_nonce` sería una vía para escapar de la comprobación del
digest.** Con el recorte se renuncia a las garantías *fail-closed*, y esta es una de ellas. Queda
declarado en vez de disimulado.

**Lo que los guards NO hacen:** no exigen que un documento tenga revisión; no ligan cobertura a la
existencia del acta; no tocan `_ESTADOS_DOCS` ni `_ESTADOS_HANDOFF` ni vuelven recursivo el glob de
`_docs_con_frontmatter`; no piden frontmatter a specs ni planes; no juzgan el contenido de la
adjudicación.

**Y una ceguera medida, no deducida.** G7 valida las adjudicaciones que **encuentra**, y las
encuentra por una cadena literal: `Adjudicación de la revisión`. Un encabezado que diga
`Adjudicación de las revisiones` —plural— no dispara el guard, y **el corpus se queda verde**. No es
hipótesis: es lo que pasó con el §13 de `2026-08-01-identidad-segmento-bundle-design.md` durante el
día que estuvo en `main`, y se reprodujo el 2026-08-02 mutando el encabezado retrofitado de vuelta al
plural — G7 en verde con la adjudicación fuera de formato.

Ampliar el disparador es barato y cerraría esta vía. **No se hace en la rev. 9** porque el encargo
del retrofit no lo incluía y ampliarlo por mi cuenta sería la misma deriva que causó el recorte. Se
declara con su evidencia, y la decisión de tocarlo o no es de Nikolai o del siguiente revisor.

## 7. Qué hay que construir, y qué no se migra

**Construir:** G7 y G8, con sus fixtures negativas. Es una tarde.

**Migrado el 2026-08-02, por encargo de Nikolai.** La rev. 8 dejaba los ocho encabezados heredados
«como están», fuera del corpus de G7 por una **lista de exclusión de siete ficheros** —de exclusión y
no de inclusión, porque una de inclusión («el corpus son los ficheros que ya cumplen») dejaría escapar
cualquier fichero **nuevo** con una adjudicación mal formada—. Esa lista **solo podía encoger**, y
encogió a cero: los ocho llevan hoy encabezado canónico y ficha, y `_ADJ_LEGACY` se retiró vacía. El
corpus de G7 es ahora todo `docs/superpowers/**/*.md` menos las actas.

**Y apareció un noveno**, que nadie había contado: el §13 de
`2026-08-01-identidad-segmento-bundle-design.md` adjudicaba dos rondas reales de Codex bajo el título
«Adjudicación de **las revisiones** adversariales», en plural. No estaba en la lista de exclusión
porque nadie sabía que estaba. Retrofitado también, partido en `13.1` y `13.2` —una adjudicación por
ronda— sin renumerar, para que las citas al §13 sigan resolviendo.

**Cómo se escribieron los recuentos, que es donde se inventa sin querer:** se **copia** lo que cada
documento publica; donde no publica desglose y dice que aceptó todo, el total va a `confirmados`. No
se deriva ni se estima ninguno, y los `escalados` se declaran solo con destino verificado.

**Doctrina a tocar:** `CLAUDE.md` §Revisión adversarial resuelve el «o» —la adjudicación va embebida y el
informe al acta— y `AGENTS.md` añade tres cosas que sí compraron calidad medible en las seis rondas: el
encargo **fija la ruta del informe** y prohíbe sobrescribir los anteriores; el revisor **devuelve `ruta` y
`sha256` canónico** antes de que se adjudique; y el mandato llega **numerado y ordenado por daño**, con el
objeto anclado a un **commit**, y el informe lo contesta punto por punto.

## 8. Las seis rondas de este documento

| Ronda | Objeto | Veredicto | Hallazgos | Informe |
|---|---|---|---|---|
| 1 | rev. 1, `3126214` | NO-SHIP | 6 confirmados | `…-adversarial-review.md` |
| 2 | rev. 2, `2c2a6d0` | NO-SHIP | 3 confirmados | `…-adversarial-review-r2.md` |
| 3 | rev. 3, `1a6e3d8` | LISTA-CON-CAMBIOS | 7 confirmados | `…-adversarial-review-r3.md` |
| 4 | rev. 5, `24f8abe` | NO-SHIP | 8 confirmados | `…-adversarial-review-r4.md` |
| 5 | diff → `bbd1fba` | NO-SHIP | 7 confirmados | `2026-08-01-gobernanza-revisiones-diff-r5-codex-bbd1fba-adversarial-review.md` |
| 6 | diff → `95ec3fe` | NO-SHIP | 7, **no adjudicados** | **no capturado** — la plataforma denegó por límite de uso la escritura en `%TEMP%` |

**38 hallazgos, 38 confirmados, ninguno refutado.** El detalle de las cinco primeras vive en sus actas,
con el informe literal y su digest; las adjudicaciones razonadas están en el historial de git, en las
revisiones 2 a 7 de este documento.

**La sexta ronda no es adjudicable** y así consta: sin informe archivado no hay original contra el que
contrastar, y adjudicar desde un resumen mío sería exactamente el fallo que este documento existe para
impedir. Su H-07 —que mi §13.1 era una racionalización *ex post*— **lo acepté por su razonamiento, no por
su forma**, y es la causa de este recorte. Cuando `%TEMP%` vuelva a ser escribible, se repite para el
registro.

**Qué compró el proceso, que es la respuesta a si merecía la pena:** paró una invariante que habría
autorizado modificar un expediente real de cliente bajo `data/CASOS/` y pasar la comprobación; paró una
cláusula que habría metido doctrina sin revisar; y produjo, en la última ronda, el juicio de que yo
estaba estirando mi propia regla de parada para seguir. Las tres cosas las encontró un revisor
independiente, y ninguna la habría visto yo.

**Qué costó:** siete revisiones, seis rondas, cinco actas y cero líneas de código. De ahí el recorte.

---

Las cinco adjudicaciones van a continuación en el formato que el §5 define, comprimidas: veredicto,
ficha y un párrafo. El detalle —informe literal, evidencia verificada y razonamiento hallazgo por
hallazgo— vive en su acta, que es su hogar. **La sexta ronda no tiene sección porque no es
adjudicable** (§8).

## 9. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 1, commit `3126214`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review.md`
- **Hallazgos:** 6 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento

Censo sin unidad de identidad y ciego a `PLAN.md`; los cuatro fallos de `agy` contados como cobertura
ausente cuando eran indisponibilidad de proveedor; el formato casando **1 de 8** encabezados y
autodetectándose dentro de su propia plantilla cercada; el registro central de más; G9 rechazando las
filas que el propio diseño exigía; y el frontmatter del acta invadiendo el hogar de la decisión.

**Única divergencia de las seis rondas:** acepté retirar el registro y G9, rechacé suprimir dos
criterios de aceptación y añadí un generador. La ronda 2 demostró que fue medio equivocada — acerté
conservando el objetivo, me equivoqué al materializarlo como script.

## 10. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 2, commit `2c2a6d0`
- **Ronda:** 2
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review-r2.md`
- **Hallazgos:** 3 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 3 de este documento

El censo daba **≥24**, no 16, y faltaba el predicado de inclusión; el generador no podía derivar porque
los artefactos no contenían sus columnas, y no tenía consumidor; G8 no verificaba el cuerpo del acta y su
exención era global. Destapó además una contradicción propia: la rev. 2 escribió que dos revisores son dos
revisiones y agrupó «Codex + Claude» como una en la tabla siguiente.

## 11. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — LISTA-CON-CAMBIOS, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 3, commit `1a6e3d8`
- **Ronda:** 3
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review-r3.md`
- **Hallazgos:** 7 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 4 de este documento

Predicado demasiado estrecho —excluía un handoff cuya acta el propio spec mandaba migrar—; la clase de
revisiones por tarea entrando por el predicado y desapareciendo del censo; la clase de rama pudiendo
perder el texto del revisor; G8 exigiendo el hash sin compararlo; y la medición del parser obsoleta, que
volvió a quedarse obsoleta **dentro de su propio remedio**.

**El de más valor fue contra el autor:** sostuve que «solo lectura» estaba mal recortado en `AGENTS.md`, y
su línea 33 lo desmiente. La invariante que propuse en su lugar era **más débil** que la vigente —`git
status` no ve modificaciones de ficheros ignorados preexistentes, y `.gitignore` excluye `data/CASOS/*`—:
habría autorizado modificar un expediente real de cliente y pasar la comprobación. Lo paró la parte
interesada, argumentando contra la ampliación de sus propios permisos.

## 12. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` rev. 5, commit `24f8abe`
- **Ronda:** 4
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review-r4.md`
- **Hallazgos:** 8 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 6 de este documento

La **crítica** fue una cláusula que yo había escrito dos días antes: permitía promover a doctrina una
remediación normativa que nadie había leído, rebautizada «riesgo residual declarado». La refutación estaba
en la historia de este mismo documento — la ronda 3 fue `LISTA-CON-CAMBIOS` y su remediación cambió el
predicado, las clases, el contrato de actas, el hash, los nombres y la migración: el token del veredicto
no acota el radio material.

Más: la obligación de informe de rama era *fail-open*; la clase mezclaba **qué** se revisa con **quién**;
el predicado seguía admitiendo lo que otra sección expulsaba; había dos digests distintos y marcadores
ambiguos; `mandato` era obligatorio sin resolver; el nombre del acta no era función estable de la
identidad; y llamar a git «de facto append-only» lo desmiente `STATUS.md:6`, que documenta el historial
reescrito el 2026-07-07.

**Se materializó al archivar el propio informe:** contenía el token de fin, así que con marcadores planos
el bloque se habría cortado por la mitad. De ahí el nonce.

## 13. Adjudicación de la revisión adversarial de rama completa (Codex, 2026-08-01) — NO-SHIP, remediado

- **Objeto revisado:** diff `24f8abe`..`bbd1fba` de este documento, commit `bbd1fba`
- **Ronda:** 5
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-08-01-gobernanza-revisiones-diff-r5-codex-bbd1fba-adversarial-review.md`
- **Hallazgos:** 7 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 7 de este documento

Comprobación dirigida, no pasada completa. Acreditó que los ocho remedios de la ronda 4 **cierran** y que
el acortado de la rev. 6 fue seguro salvo en dos líneas — y esas dos son lo que más escuece, porque el
primer punto de mi propio mandato era «¿qué se llevó el acortado?» y no las vi: el hogar de la adjudicación
de rama y la inmutabilidad del veredicto, ambas normativas, ambas suprimidas sin sustituto.

Más: el *fail-closed* hacía imposible una salida que la ficha seguía publicando; la excepción histórica se
cerraba por fichero, amnistiando cualquier adjudicación futura en el mismo anfitrión; **la primera acta del
contrato incumplía el contrato** en la gramática de `mandato`; el enlace del gate no tenía sintaxis; y una
referencia cruzada apuntaba a la sección equivocada.
