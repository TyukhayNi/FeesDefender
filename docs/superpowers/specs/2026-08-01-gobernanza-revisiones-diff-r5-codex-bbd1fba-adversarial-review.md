---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md
objeto_rev: "6"
commit: bbd1fba
ronda: "5"
clase: rama
independencia: independiente
revisor: Codex
cobertura: ejecutada
veredicto: NO-SHIP
mandato: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §13
marcador_nonce: qw5v
sha256_informe: 0f8a95dcd4c908e26c62db3b4c66d950a1e9f6111e106343d4009bed6f46825e
adjudicado_en: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §18
---

# Comprobación dirigida — gobernanza de las revisiones adversariales (rev. 6, ronda 5)

Primera acta de **`clase: rama`** del proyecto: su objeto es el diff `24f8abe` → `bbd1fba`, no un
documento. Por el §3.1 su fichero anfitrión es el propio spec, y el nombre sigue el esquema del §6 con
revisor y commit incluidos.

## 1. Informe recibido de Codex, sin modificar

> Texto íntegro entregado el 2026-08-01 en `%TEMP%\gobernanza-revisiones-diff-r5-codex-bbd1fba.md`,
> 175 líneas, en la ruta que fijó el encargo (§10.1.2). Digest canónico verificado por Claude al
> recibirlo contra la copia externa; el revisor lo devolvió por canal separado (§10.1.3). LF, y digest
> bruto igual al canónico. No se ha corregido ortografía, numeración ni formato.

<!-- informe-literal:inicio:qw5v -->
# Comprobación dirigida — gobernanza de las revisiones adversariales, rev. 6

- **Objeto:** diff `24f8abe` → `bbd1fba` de `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` y acta `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review-r4.md`.
- **Commit comprobado:** `bbd1fba3906dd231c47e0afe688cf392a8c3b507`.
- **Rama/worktree:** `claude/internal-dialogue-documentation-4fbc1c` / `.claude/worktrees/internal-dialogue-documentation-4fbc1c`.
- **Alcance:** exclusivamente los ejes normativos tocados por la rev. 6 y el cumplimiento del acta r4; no se reabren los 24 hallazgos adjudicados, el corpus/censo/corte, los mecanismos retirados ni el plan de migración.
- **Método:** lectura completa del diff y de ambos documentos; contraste de cada supresión normativa; recomputación independiente del bloque literal y de la copia externa; ejecución controlada de `tests/test_docs_gobernanza.py`; comparación de contenidos y estado Git antes/después.

## Veredicto global

**NO-SHIP. El gate no está satisfecho.** No debe promoverse aún el contrato a `CLAUDE.md`/`AGENTS.md` ni abrirse la Tarea 1.

La rev. 6 cierra materialmente los ocho hallazgos de la ronda 4 y mejora mucho la terminación del proceso. Sin embargo, el acortado perdió el hogar de la adjudicación de `clase: rama`; el fail-closed contradice una salida que la ficha todavía declara válida y deja su excepción histórica sin identidad cerrada; y la primera acta sometida al contrato no cumple la gramática de `mandato` que G8 debe aplicar. Son defectos locales, pero afectan al mecanismo que se pretende convertir en doctrina, no a narración prescindible.

## Hallazgos

### H-01 — ALTA — El acortado eliminó el hogar de la adjudicación de rama

En la rev. 5, §1.2 decía expresamente que una revisión `rama` llevaba «acta + encabezado + ficha **en el plan**». Esa obligación desaparece. La rev. 6 conserva `clase: rama` para «diff o rama completa» (§1.2:56), pero §3:128 sitúa la adjudicación en una «sección embebida en el objeto» y el criterio 6 (§12:461-462) exige encabezado y ficha «en su objeto». Una rama, un diff o un PR no son un Markdown en el que se pueda insertar una sección. §5:188-189 solo permite nombrarlos en `Objeto revisado`; no determina el fichero anfitrión.

**Daño:** G7 necesita un corpus de ficheros y la revisión de rama necesita un hogar auditable. Sin regla de colocación, dos implementadores pueden archivarla en PLAN, spec, handoff o ningún objeto, todos creyendo cumplir. Es exactamente una obligación normativa eliminada sin sustituto.

**Remedio mínimo:** restituir una regla única de hogar para `clase: rama` —por ejemplo, plan que gobierna la rama; si no existe, spec/handoff del que deriva— y hacer que §3 y §12 remitan a esa regla en vez de decir «el objeto».

### H-02 — ALTA — El fail-closed hace imposible la opción `sin informe (revisión del autor)`

§1.2:63-65 establece que una revisión `independencia: autor` entra en la población y se registra. §1.3:69-74 exige acta para toda respuesta textual recuperable y afirma que `Cobertura: ejecutada` requiere un acta válida. G7 repite la implicación sin excepción por independencia (§8:318-324). Pero la ficha canónica sigue admitiendo `Informe recibido: sin informe (revisión del autor)` (§5:183).

Tampoco puede resolverse marcando esa revisión `no-ejecutada`: §4:156-158 reserva ese valor a un encargo terminado sin sustituto **y sin adjudicación**. Por tanto, la alternativa de §5 no tiene estado válido bajo el mismo contrato.

**Daño:** el modelo de dos ejes está bien definido, pero una de sus combinaciones publicadas no se puede representar pasando G7.

**Remedio mínimo:** elegir una semántica y decirla una vez. La compatible con el fail-closed es retirar `sin informe (revisión del autor)` y exigir acta también a la revisión del autor cuando produzca texto; seguirá sin acreditar independencia. Si se quiere conservar la excepción, §1.3 y G7 deben condicionarse expresamente, asumiendo que esa voz no queda archivada.

### H-03 — ALTA — La excepción histórica de G7 no denota identidades y puede abrir el futuro

§1.3:76-78 promete una «lista cerrada» y G7 exceptúa «que **el fichero** esté en la lista» (§8:321-323), pero el spec no enumera esa lista ni define qué fichero identifica: ¿el objeto que contiene la ficha o un acta inexistente? §8:335-336 define otra allowlist, de cuatro **nombres de acta**, para G8; §10:373 habla de «los tres `codex-*`». Son poblaciones y cardinalidades diferentes.

Si G7 permite por nombre del objeto, una adjudicación futura añadida al mismo PLAN/spec histórico hereda la amnistía y vuelve a abrir `no capturado`. Si pretende permitir por nombre de acta, no hay acta a la que pueda resolver la ficha exceptuada. Tal como está, el guard no se puede implementar sin inventar política.

**Daño:** la relación central se anuncia fail-closed, pero su única excepción puede convertirse en una exención permanente por fichero.

**Remedio mínimo:** definir y enumerar la allowlist de G7 por **identidad de revisión** —objeto, commit/rev., ronda, revisor y fecha, o un identificador equivalente del encabezado— y prohibir expresamente allowlistear un objeto entero. Mantener separada la allowlist de formatos legacy de G8.

### H-04 — MEDIA — El acta r4 no cumple la gramática de `mandato` que inaugura

§3:126, la plantilla de §6:247 y G8 (§8:328-331) admiten dos formas: `§0 de este acta`, con §0 presente, o puntero `<ruta> §N` resuelto en el `commit` del frontmatter. El acta r4 no tiene §0 y declara:

`mandato: §13.2 de la rev. 5 del objeto (git 24f8abe)`

El destino humano es inequívoco y existe en `24f8abe`, pero no es `<ruta> §N`. G8 tendría que rechazar la primera acta del contrato o añadir una tercera gramática no especificada.

**Remedio mínimo:** cambiarlo por `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §13.2`. `objeto` y `commit` ya fijan la revisión y el commit contra el que resolver.

### H-05 — MEDIA — Se eliminó la inmutabilidad del veredicto del acta

La rev. 5, §6:295-296, distinguía el estado de remediación mutable del `veredicto`, que «sí [va en el acta]: **es inmutable**». La rev. 6 conserva `veredicto` en frontmatter (§6:246), pero elimina la regla sin sustituto. G8 solo exige vocabulario válido; el digest cubre el informe literal, no el frontmatter (§8:328-334).

**Daño:** editar `veredicto: NO-SHIP` a otro token permitido podría dejar suite verde y desalinear el índice del acta respecto de la voz literal archivada. El informe permitiría descubrirlo manualmente, pero el contrato ya no dice que sea una alteración inválida.

**Remedio mínimo:** restaurar que `veredicto` es el veredicto normalizado del revisor y es inmutable; si se desea comprobación automática, G8 puede al menos exigir que el valor conste en el bloque literal o declarar por qué esa comparación queda manual.

### H-06 — MEDIA — El gate de §10.2 termina, pero su «enlace» no tiene forma comprobable

La cláusula de cierre de §10.2:419-431 sí termina: SHIP cierra; LISTA-CON-CAMBIOS solo cierra por atestiguación cuando el cambio no toca seis ejes cerrados; si los toca, ordena una comprobación dirigida, y cualquier renuncia queda atribuida a Nikolai. No queda una recursión automática.

La costura está en §10.2:428-429: «el commit ... enlaza la revisión de cierre» no dice **dónde** ni **con qué sintaxis**. Un tercero no puede distinguir de modo determinista un enlace contractual de una mención libre en el mensaje, una ruta añadida al árbol o un comentario de PR. Tampoco se especifica si el enlace debe anclar acta, informe externo o digest.

**Remedio mínimo:** fijar un único soporte, por ejemplo un trailer del commit `Revision-cierre: <ruta-del-acta>@sha256:<digest-canónico-del-informe>`, o un campo equivalente versionado. No hace falta un guard nuevo; sí una forma que un tercero pueda verificar sin interpretar prosa.

### H-07 — BAJA — §1.3 remite al apartado equivocado del contrato del revisor

§1.3:81-83 atribuye la ruta y la devolución `ruta + sha256` a «§10.1.5». En realidad son §10.1.2 y §10.1.3 (§10.1:390-396); §10.1.5 explica que el revisor no adjudica. El propio mandato de esta comprobación usa las referencias correctas.

**Remedio mínimo:** sustituir `§10.1.5` por `§10.1.2-3`.

## Respuesta al mandato, punto por punto

### 1. Lo que el acortado se llevó

Revisé las supresiones del diff por bloques normativos, no solo el saldo de 86 líneas:

| Bloque suprimido o condensado | Resultado |
|---|---|
| Predicado por función, clases y autorrevisión | Sustituido por predicado prospectivo + ejes `clase`/`independencia`; no queda token `autorrevision`. |
| Traza de `rama` y de `autorrevision` | El fail-closed sustituye la captura defectuosa, pero se pierden el hogar «en el plan» (H-01) y la semántica sin acta del autor queda contradictoria (H-02). |
| Identidad, corte y no-cardinalidad | Conservados, reordenados y abreviados. |
| Cuatro artefactos y vocabularios | Conservados; `mandato` gana resolución contra commit. |
| Regex, medición narrativa y retrofit | El contrato del parser se conserva; los totales vivos quedan en fixture. El plan de migración está fuera de esta comprobación por mandato. |
| Un acta por ronda, nombres y legacy | Conservados por el título de §6, la identidad/nombre y la excepción expresa de cuatro actas. |
| Hash bruto, canonicalización, marcadores y confianza en Git | Sustituidos de forma materialmente más precisa por digest canónico, `sha256_recibido` opcional, nonce y frontera de confianza. |
| Mutabilidad de metadatos del acta | `estado_remediacion` sale correctamente del acta; la inmutabilidad de `veredicto` desaparece sin sustituto (H-05). |
| Generador/ledger/G9 | Su retirada sigue expresa; no se reabre. |
| Detalle de migración | Trasladado al plan; solo queda política. Fuera de alcance por mandato. |
| Regla de parada anterior | Sustituida por cierre por naturaleza del cambio; termina, con la carencia de forma del enlace de gate (H-06). |
| Narración de M-1 a M-5 y cobertura pendiente | Trasladada a §17/acta y resumida en §13; no se perdió obligación vigente. |
| Adjudicaciones §14-§16 | Condensadas sin cambiar sus resultados; §17 incorpora la ronda 4. |

Las pérdidas normativas no sustituidas son, por tanto, las de H-01 y H-05. H-02 y H-03 son costuras abiertas al reexpresar el fail-closed; H-04 es incumplimiento del nuevo formato, no una pérdida.

### 2. Los ocho remedios de la ronda 4

| Hallazgo de r4 | ¿Cierra? | Costura nueva |
|---|---|---|
| H-01 `no capturado` fail-open | **Cierra la regla prospectiva**: ruta previa, entrega de ruta+hash, repetición si se pierde. | H-02/H-03: opción de autor incompatible y excepción histórica sin identidad. |
| H-02 clase e independencia mezcladas | **Sí.** Dos ejes, independencia contra autor y gate solo independiente. | La representación sin informe del valor `autor` contradice G7 (H-02). |
| H-03 revisiones por tarea dentro y fuera a la vez | **Sí.** Prospectivamente quedan fuera y sus voces se incorporan/enlazan con autor+hash; una revisión autónoma obtiene identidad y acta. | Ninguna adicional en ese remedio. |
| H-04 dos digests y delimitación ambigua | **Sí.** Una canonicalización, raw opcional, nonce único, exactamente un par y fallo rojo. | Ninguna: la prueba real del acta r4 pasa. |
| H-05 cierre promueve material normativo no revisado | **Sí en terminación y radio.** La presente comprobación demuestra que la bifurcación por ejes es operable. | El enlace observable carece de gramática (H-06). |
| H-06 mandato obligatorio pero no resoluble | **Sí en el spec.** G8 resuelve contra el commit. | El acta r4 usa una tercera forma no admitida (H-04). |
| H-07 nombre no inyectivo / falta `diagnostico` | **Sí.** Nombre por identidad con revisor+commit y vocabulario ampliado; legacy temporal explícito. | Ninguna. |
| H-08 confianza revocable en Git | **Sí.** §6.1 declara la frontera y excluye resistencia al administrador. | Ninguna. |

### 3. Los dos ejes contra el resto del documento

Los valores son consistentes en §1.2, §4, §5, §6, §8 y §12: `clase = diseño|rama`; `independencia = independiente|autor`; solo `independiente` acredita el gate. La búsqueda completa no encuentra ningún resto de `autorrevision` como clase. §3 aplica obligaciones a toda la población sin inventar valores distintos.

Las divergencias no están en el vocabulario, sino en los hogares y relaciones: `rama` carece de fichero anfitrión (H-01) y `autor` conserva una salida sin acta que el fail-closed rechaza (H-02).

### 4. Fail-closed y G7

La relación positiva es implementable: parsear una ficha con `Cobertura: ejecutada`, leer el valor de `Informe recibido`, resolver una ruta de acta y validarla con G8. No es implementable **tal como está escrito** por H-02 y H-03. En particular, una allowlist por fichero de objeto sería una nueva vía de fallo abierto para futuras rondas. Debe cerrarse por identidad exacta y separarse de la allowlist de formatos legacy de G8.

### 5. §10.2: terminación y observabilidad

La regla termina y el autor no puede cerrar por mera atestiguación si el diff toca alguno de los seis ejes enumerados; esta comprobación es la prueba de que la condición se puede aplicar. Un tercero puede comparar el diff y detectar una atestiguación falsa. La renuncia también tiene un decisor identificado.

Lo no determinista es el último paso: qué cuenta como «enlazar» la revisión desde el commit (H-06). El momento del gate sí está acotado —commit de promoción o de apertura de primera tarea—; falta el formato de la evidencia.

### 6. Acta r4 contra §6

Resultado de la recomputación independiente:

- `independencia: independiente`: presente y coherente con autor/revisor.
- `marcador_nonce: zx7q`: exactamente un inicio y un fin, en orden; `zx7q` no aparece en el informe literal.
- `sha256_informe` declarado: `f67d6ec53f8070898e75920a6913f0a1857b4e11da9c27439e38f003d47ad089`.
- Digest del bloque literal canonicalizado: el mismo.
- Digest de `%TEMP%\revision-gobernanza-revisiones-r4.md`, canonicalizado: el mismo.
- Digest bruto de la copia externa: el mismo; `sha256_recibido` puede omitirse.
- Bloque literal y copia externa: idénticos, **169 líneas** cada uno.
- Nombre legacy: cubierto por la excepción expresa de §6:230-231 hasta la migración.
- `adjudicado_en`: resuelve a §17.
- `mandato`: destino humano existente, pero forma no conforme; H-04.

Por tanto, la declaración `f67d6ec5…089` y 169 líneas es correcta. El acta no cumple íntegramente §6/G8 solo por el puntero de mandato.

### 7. Ejecución y solo lectura

Comando válido final:

`PYTHONDONTWRITEBYTECODE=1 python -m pytest -q tests/test_docs_gobernanza.py -p no:cacheprovider --basetemp %TEMP%\fd-gob-bbd1fba-...`

Resultado: **8 passed**, exit 0. Son los guards actuales G1-G6; G7/G8 aún no existen y esta suite no acredita su diseño futuro.

Antes y después del run válido:

- `git status --porcelain --untracked-files=all`: vacío / vacío.
- 1.021 ficheros versionados o no ignorados inventariados: 0 añadidos, 0 eliminados, 0 modificados.
- 345 entradas ignoradas inventariadas: 0 añadidas, 0 eliminadas, 0 modificadas.

Un intento previo con `--basetemp C:\tmp\...` no llegó a ejecutar aserciones por denegación de permisos al crear ese directorio; también dejó cero cambios. Se repitió correctamente en `%TEMP%`. No se accedió a CRM ni Drive.

## Condición mínima para repetir la comprobación

No hace falta otra pasada completa. Basta un diff dirigido que:

1. restituya el hogar de la adjudicación `rama`;
2. haga coherentes `autor`, acta y `Cobertura`;
3. enumere la allowlist histórica de G7 por identidad;
4. normalice el `mandato` del acta r4;
5. restaure la inmutabilidad de `veredicto`;
6. dé forma verificable al enlace del gate; y
7. corrija la referencia §10.1.5.

Hasta entonces, el contrato es cercano a operable, pero no promovible como doctrina auditable por un tercero.
<!-- informe-literal:fin:qw5v -->

## 2. Evidencia verificada por Claude al adjudicar

Comprobado abriendo la fuente. La adjudicación razonada está en el §18 del spec.

**Las dos pérdidas del acortado, con línea exacta a los dos lados del diff:**

- **H-01.** `git show 24f8abe:…-design.md` línea **50**: «`rama` … **Acta** + encabezado + ficha **en el
  plan**». En la rev. 6, línea **128** dice «Sección embebida en el objeto» y la **461** «encabezado y
  ficha en su objeto». Una rama no es un Markdown: el hogar desapareció. **Confirmado.**
- **H-05.** `git show 24f8abe:…-design.md` línea **296**: «`veredicto` sí: **es inmutable**». No queda
  nada equivalente en la rev. 6. **Confirmado.**

**Las cinco costuras y el incumplimiento, verificables dentro del documento:**

- **H-02.** Línea **183** de la rev. 6 admitía `sin informe (revisión del autor)` mientras el §1.3 y G7
  exigen acta para `Cobertura: ejecutada`, y `no-ejecutada` está reservada a un encargo **sin
  adjudicación**. Combinación publicada sin estado válido. **Confirmado.**
- **H-03.** El §1.3 prometía «lista cerrada» y G7 exceptuaba «que el **fichero** esté en la lista», sin
  enumerarla y sin decir qué fichero. Con permiso por fichero, cualquier adjudicación futura añadida a
  ese anfitrión heredaría la amnistía. **Confirmado.**
- **H-04.** El `mandato` del acta r4 era `§13.2 de la rev. 5 del objeto (git 24f8abe)`: destino humano
  inequívoco, pero ninguna de las dos gramáticas que el §8 admite. **La primera acta del contrato
  incumplía el contrato.** **Confirmado.**
- **H-06.** El §10.2 decía «enlaza la revisión de cierre» sin soporte ni sintaxis. **Confirmado.**
- **H-07.** La línea **82** citaba §10.1.5 —«el revisor no adjudica»— para la ruta y la devolución de
  `ruta + sha256`, que son §10.1.2 y §10.1.3. **Confirmado.**

**Cadena verificada por mí también:** digest canónico de la copia externa
`0f8a95dcd4c908e26c62db3b4c66d950a1e9f6111e106343d4009bed6f46825e`, bruto idéntico al canónico, 175
líneas; nonce `qw5v` ausente del informe y con letras no hexadecimales.

### Nota de método

**31 de 31 en cinco rondas, cero refutados.** Y esta ronda es la primera **sin ningún hallazgo
estructural**: el revisor comprueba que los dos ejes son consistentes en los seis sitios donde aparecen,
que los ocho remedios de la ronda 4 cierran, y que el §10.2 termina — la propia comprobación es la
prueba de que su bifurcación es operable.

Lo que sí conviene no adornar: **dos de los siete son regresiones que yo introduje al acortar la
rev. 6**, presumiendo de decir cada regla una vez. El primer punto de mi propio mandato era «¿qué se
llevó el acortado?», y ni sabiéndolo las vi al reescribir. La lección no es que acortar esté mal: es que
suprimir prosa en un documento normativo es un cambio de contenido, y hay que tratarlo como tal.
