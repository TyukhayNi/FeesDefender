---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md
objeto_rev: "1"
commit: 3126214
ronda: "1"
clase: A-diseño
revisor: Codex
cobertura: ejecutada
veredicto: NO-SHIP
sha256_informe: 4f45f867de828badfdcd9f583e1731856001265ee345bb910f450b5142663f58
adjudicado_en: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §14
---

# Revisión adversarial — gobernanza de las revisiones adversariales (rev. 1)

Primera acta escrita bajo el reparto que el propio objeto propone: **§1 es el informe recibido,
literal y sin modificar**; **§2 es lo que Claude abrió para adjudicar**. La adjudicación no está
aquí: vive en el §14 del spec.

## 1. Informe recibido de Codex, sin modificar

> Texto íntegro entregado el 2026-08-01 en `%TEMP%\revision-gobernanza-revisiones.md`. No se ha
> corregido ortografía, numeración ni formato. Las referencias `§N.LLL` son del revisor.

---

# Revisión adversarial — gobernanza de las revisiones adversariales

- **Objeto:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`, rev. 1.
- **Commit revisado:** `31262148da64ab7a1b80d8603cc6770801cb6caa`.
- **Rama/worktree:** `claude/internal-dialogue-documentation-4fbc1c` / `.claude/worktrees/internal-dialogue-documentation-4fbc1c`.
- **Método:** solo lectura; contraste contra `tests/test_docs_gobernanza.py`, `docs/GOBERNANZA_FUENTES_VERDAD.md` §5, `docs/INDICE.md`, el corpus del §9, `PLAN.md` y `docs/DEAD_ENDS.md`.

## Veredicto

**NO-SHIP en rev. 1.** La partición de fondo es recuperable: conservar la adjudicación junto al objeto y archivar aparte el informe recibido es una decisión sensata. El contrato que la rodea no está listo: el censo no tiene unidad de identidad, G7 exige reescribir siete de los ocho encabezados, G7 se autodetecta dentro del ejemplo del propio spec, G9 contradice las filas sin cobertura y el registro central duplica hechos sin aportar una capacidad que no den ya G7, G8 y una consulta derivada.

La corrección mínima es: definir la identidad de una revisión, reconocer expresamente el retrofit de los encabezados, hacer que el parser ignore bloques cercados, conservar G7/G8, dejar la adjudicación embebida y **eliminar el registro central y G9**. Si más adelante se necesita una vista tabular, debe generarse desde los artefactos canónicos, no mantenerse a mano.

## Hallazgos

### H-01 — CRÍTICA — El censo mezcla ficheros, secciones, rondas e intentos de revisor; no puede alimentar G9

El §1 no cuenta una unidad estable. El §9 contiene **ocho secciones embebidas en siete ficheros distintos**, más cuatro actas: no son «12 ficheros», sino once ficheros con doce artefactos de adjudicación. Además:

- el acta dual y el §20 de su spec son dos hogares de la misma revisión;
- `handoff-…-codex-informe.md` y `handoff-…-codex-review.md` son informe completo y resumen de la misma primera pasada de vista procesal; `…-review-2.md` sí es otra ronda;
- el acta de emails declara una segunda revisión independiente dentro del mismo fichero;
- las tres pasadas de Fase 0 son tres rondas sobre un solo plan.

Sin una identidad del tipo `(objeto, commit/rev, ronda, revisor, fecha de entrega)`, G9 no puede decidir si corresponde una fila por fichero, por sección, por informe, por revisor o por ronda. La cardinalidad «≥15» no es auditable.

El censo también es incompleto si el registro pretende cubrir las revisiones adversariales históricas, como indica su columna `Revisor: Claude (no independiente)`: `PLAN.md:924-928` adjudica cuatro defectos de Google MCP F1; `PLAN.md:933` adjudica tres huecos fail-open de F2; `PLAN.md:953` registra una revisión del spec MCP sudespacho con correcciones aplicadas; `PLAN.md:1033-1044` registra una revisión de código con 14 hallazgos confirmados y otra con veredicto SHIP. Ninguna entra en el §9. O bien se fija un corte temporal explícito, o la migración nace incompleta.

**Remedio exigido:** definir primero la unidad e identidad de revisión y el límite temporal. Después rehacer el censo por identidad, deduplicando representaciones del mismo evento.

### H-02 — ALTA — Los cuatro casos de `DEAD_ENDS.md` no son cuatro revisiones sin cobertura

El §7.201-203 y el §9.249-250 convierten cuatro intentos fallidos de `agy` en cuatro filas `cobertura: no-ejecutada`. La fuente real no sostiene esa inferencia:

- `DEAD_ENDS.md:620-630` habla de cuatro **encargos a Gemini** que no corrieron, no de cuatro objetos que nadie revisó;
- el spec de email y el plan de cableado dicen expresamente que, al fallar `agy`, **Codex hizo la revisión**;
- el acta de cableado (`:3-6`) registra Codex + una pasada propia de Claude; lo ausente fue Gemini;
- el acta dual (`:3-20`) registra una revisión ejecutada por Claude con veredicto `REQUIERE REVISIÓN`; falló el barrido mecánico delegado a `agy`.

Registrar esas tentativas como revisiones autónomas sin cobertura duplica los objetos ya censados y falsea quién revisó. Si se quiere auditar disponibilidad de proveedores, ese hecho pertenece a `DEAD_ENDS.md`, no al censo de revisiones.

**Remedio exigido:** retirar las cuatro filas prometidas. `cobertura: no-ejecutada` solo debe existir para un encargo de revisión que terminó sin sustituto y sin adjudicación, identificado como tal.

### H-03 — ALTA — G7 casa uno de ocho encabezados y además se autodetecta en el bloque de ejemplo

El §5 no contiene un regex literal; contiene una plantilla. Traducida de forma fiel —numeración opcional, fecha ISO y vocabularios cerrados—, el resultado sobre las ocho secciones reales es **1/8**:

| Sección existente | Resultado | Motivo principal |
|---|---:|---|
| vista procesal §10 | no | faltan revisor, fecha, veredicto y estado |
| email enumeración §11 | no | `resuelto` no pertenece a `estado_remediacion` |
| dual workspace §20 | no | solo lleva `(rev. 2)` |
| sandwich spec §9 | **sí** | ya tiene la forma canónica |
| historial §10-bis | no | `NO EJECUTABLE` no es `NO-EJECUTABLE` |
| cableado plan | no | inserta `del PLAN` y `veredicto` |
| sandwich plan | no | `NO EJECUTABLE` no es `NO-EJECUTABLE` |
| revisión de rama completa | no | no dice `adversarial`, omite revisor, usa `LISTA CON CAMBIOS` y `aplicados` |

Por tanto, el guard no «formaliza la línea que ya se escribe sola»: obliga a reescribir siete encabezados. El §9 lo admite al ordenar «normalizar encabezado», pero el propio mandato §13.2 declara mal calibrado un guard que nace así. Debe elegirse y documentarse una de dos políticas: parser legacy permisivo + formato estricto solo para lo nuevo, o retrofit intencional de 7/8 con el coste reconocido.

Hay un segundo defecto ejecutable: `tests/test_docs_gobernanza.py` trabaja con regex sobre texto, no con un parser Markdown. La línea de ejemplo del §5 empieza literalmente por `## … Adjudicación de la revisión…` dentro de una cerca de código. El disparador descrito por G7 la encuentra y la rechaza por placeholders y por ausencia de ficha. El spec no ordena retirar bloques cercados antes del match.

**Remedio exigido:** especificar el regex real, ignorar bloques cercados y fixtures, y corregir la afirmación de compatibilidad. Añadir un test que incluya el propio spec para matar el automatch.

### H-04 — ALTA — El registro central sobra y vulnera «un hecho → un hogar»

`docs/REVISIONES_ADVERSARIALES.md` se presenta como vista derivada, pero sería una tabla manual de nueve columnas. Repite `objeto`, `revisor`, `cobertura`, `veredicto`, recuento, adjudicación, informe y remedio que ya viven en el encabezado/ficha y en el acta. El §7.186-187 llega a decir que el estado sigue viviendo en la sección **y** en el acta; la tabla lo copiaría una tercera vez. Esto contradice directamente `GOBERNANZA_FUENTES_VERDAD.md:15-22`.

G9 solo comprueba referencias bidireccionales. No impide que la sección diga `NO-SHIP`, el acta `REQUIERE-REVISION` y el registro `SHIP`, ni que discrepen cobertura, recuento o remedio. Por tanto, los guards no convierten la tabla manual en derivada; solo aseguran que existe una fila.

El beneficio alegado tampoco requiere persistencia: una vez canónicos G7 y G8, «qué se revisó, por quién, con qué veredicto y dónde se adjudicó» se obtiene con un grep o un script lector. `INDICE.md:23-27` excluye deliberadamente los specs/planes fechados y remite su estado a `PLAN.md`; introducir un ledger de ~150 filas/año reabre precisamente la superestructura que la gobernanza ligera intenta evitar.

**Remedio exigido:** suprimir §7, G9 y los criterios de aceptación 2 y 6. Si la consulta tabular llega a tener un consumidor real, generarla bajo demanda desde G7/G8; no versionarla como tercera copia.

### H-05 — ALTA — G9 no puede aceptar las filas sin cobertura que el propio diseño exige

G9 dice que toda fila del registro debe apuntar a una adjudicación o acta existente (§8.217-218). Pero el esquema de fila permite `Adjudicación: —` y `Informe: <motivo de ausencia>` (§7.197-199), y el §7.201-203 exige filas plenas para revisiones no ejecutadas. Esas filas no tienen por definición ni adjudicación ni acta. G9 las rechaza salvo que se añada una excepción que el spec no define.

Esto no es el conflicto planteado con G2. G2 no forma un ciclo: crear acta y referencia en el mismo cambio es una operación atómica normal, y que el test esté rojo durante un paso intermedio es correcto. El conflicto real está dentro de G9.

**Remedio exigido:** si se conserva un censo, modelar explícitamente la variante `no-ejecutada` y su evidencia. La recomendación principal de H-04 —eliminar registro y G9— hace innecesario este parche.

### H-06 — MEDIA — El frontmatter del acta invade el hogar de la adjudicación

El §3 asigna al acta el **informe recibido** y al spec/plan la **adjudicación**. Sin embargo, el frontmatter obligatorio del §6 incluye `adjudicado_por`, `adjudicado_en` y `estado_remediacion`. Los dos primeros describen la decisión posterior; el último copia un estado mutable que ya figura en el encabezado embebido. La frase §7.186-187 confirma que la duplicación es deliberada.

El acta puede llevar un puntero estable `adjudicado_en` para navegar, pero no debe convertirse en segundo hogar del resultado. De lo contrario, una remediación posterior exige sincronizar acta, objeto y registro, justo el drift que el diseño pretende eliminar.

**Remedio exigido:** limitar el frontmatter del acta a identidad/procedencia del informe y un puntero a la adjudicación. `estado_remediacion` y el recuento viven solo en la ficha embebida.

## Resultado de los seis puntos del §13

1. **Censo: refutado.** Falta identidad, hay duplicados representacionales, falsas ausencias de cobertura y precedentes históricos fuera del corte.
2. **G7: refutado.** Casa 1/8 y se autodetecta en el ejemplo cercado.
3. **Tercera población: resiste con matiz.** `estado_remediacion` evita la colisión D3 porque G1-G3 y G4-G6 ya separan deliberadamente sus poblaciones. El problema no es el nombre del campo, sino copiar su valor en varios hogares y no reconocer la migración de vocabulario.
4. **G9/G2: el conflicto propuesto se refuta.** No hay ciclo con G2 si los artefactos se crean juntos. Sí hay una contradicción interna de G9 con `no-ejecutada` (H-05).
5. **Hogar de la adjudicación: resiste.** Dejarla embebida es preferible por proximidad al objeto y hogar único; el argumento debe apoyarse en eso, no solo en «8 de 12». Las cuatro actas híbridas históricas pueden quedar intactas.
6. **Sobreingeniería: confirmada.** El registro central y G9 sobran. También sobran en el acta los campos mutables de la adjudicación.

## Verificaciones ejecutadas

- `HEAD` del worktree objetivo: `31262148da64ab7a1b80d8603cc6770801cb6caa`; árbol limpio antes y después.
- `tests/test_docs_gobernanza.py`: **8 passed**, con `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1` y `--basetemp` fuera del repo.
- Prueba del encabezado canónico contra el corpus §9: **1/8**.
- Búsqueda del disparador G7 en el propio spec: **1 automatch**, la plantilla dentro del bloque cercado.
- No se modificó ningún fichero del repositorio.

---

## 2. Evidencia verificada por Claude al adjudicar

Comprobado abriendo la fuente, no aceptado por la cita del revisor. La adjudicación razonada está
en el §14 del spec; aquí solo consta **qué se miró**.

- **H-01, precedentes de `PLAN.md`.** `PLAN.md:924-928, 933, 953, 1033-1044` contienen revisiones
  adjudicadas con veredicto y recuento (una de ellas «14 hallazgos confirmados, 8 HIGH, TODOS
  corregidos»; otra con veredicto SHIP). Ninguna figuraba en el §9 de la rev. 1. **Confirmado.**
- **H-01, rondas de la Fase 0.** `PLAN.md:587` y `PLAN.md:595` registran la 2ª y la 3ª pasada como
  gates consumidos. **Confirmado**, y de paso queda refutada una afirmación de la propia rev. 1:
  no constaban «solo en la bitácora».
- **H-02, `DEAD_ENDS.md:610-640` leído entero.** Son cuatro **encargos a Gemini**, no cuatro
  objetos sin revisar. La tercera viñeta dice literalmente «la revisión la hizo **Codex** en solo
  lectura». **Confirmado.**
- **H-02, acta de cableado `:3-6`.** «Revisores: Codex (independiente) + pasada propia de Claude».
  Lo ausente fue Gemini, no la revisión. **Confirmado.**
- **H-03, los ocho encabezados extraídos del corpus.** Solo
  `2026-07-29-sandwich-firma-falso-positivo-design.md:287` casa la plantilla. Los demás fallan por
  `resuelto`, `(rev. 2)`, `NO EJECUTABLE` con espacio, `del PLAN`, `veredicto ` como prefijo, y un
  encabezado que ni siquiera dice «adversarial». **1/8 confirmado.**
- **H-03, automatch reproducido.** Un `grep` de encabezados sobre `docs/superpowers/` devolvió la
  **línea 118 del propio spec** —la plantilla dentro de la cerca— junto a los encabezados reales.
  El defecto no se dedujo: se observó. **Confirmado.**
- **H-04, alcance real de G9.** El §8 de la rev. 1 especifica G9 como comprobación de existencia
  bidireccional. No hay en todo el spec ninguna comprobación de igualdad de valores entre fila,
  ficha y acta. **Confirmado.**
- **H-05, contradicción interna.** §7 («las revisiones no ejecutadas son filas de pleno derecho»)
  contra §8 G9 («toda fila apunta a una adjudicación o acta existente»). Literal, en el mismo
  documento. **Confirmado.**
- **H-06.** El frontmatter del §6 incluía `adjudicado_por` y `estado_remediacion`, ambos hechos de
  la decisión y el segundo mutable. **Confirmado.**

### Nota de método

Ninguno de los seis hallazgos se refutó. Eso es inusual y no se firma por deferencia: cinco se
comprobaron contra la fuente en el momento de adjudicar y el sexto (H-01) contra `PLAN.md`. La
disciplina de `feedback-agy-review-adjudicar-severidad` exige verificar también cuando el informe
acierta — un acta que dijera «6/6 confirmados» sin decir **qué se abrió** no sería auditable.
