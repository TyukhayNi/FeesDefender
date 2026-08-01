---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md
objeto_rev: "2"
commit: 2c2a6d0
ronda: "2"
clase: A-diseño
revisor: Codex
cobertura: ejecutada
veredicto: NO-SHIP
sha256_informe: 20c45f93c0460a8f91ba426c9570ac918b01882a43f07aec9f549166070f4114
adjudicado_en: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §15
---

# Revisión adversarial — gobernanza de las revisiones adversariales (rev. 2, ronda 2)

Segunda ronda sobre el mismo objeto. Acta separada de la ronda 1 porque el frontmatter es escalar
(§6 del spec): un fichero no puede representar dos rondas.

## 1. Informe recibido de Codex, sin modificar

> Texto íntegro entregado el 2026-08-01 en `%TEMP%\revision-gobernanza-revisiones-rev2.md`, 107
> líneas, `sha256` en el frontmatter. No se ha corregido ortografía, numeración ni formato. Las
> referencias `§N:LLL` son del revisor.

---

# Segunda revisión adversarial — gobernanza de las revisiones adversariales

- **Objeto:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`, rev. 2.
- **Commit revisado:** `2c2a6d09393ea472712cd37847bff77165227672`.
- **Rama/worktree:** `claude/internal-dialogue-documentation-4fbc1c` / `.claude/worktrees/internal-dialogue-documentation-4fbc1c`.
- **Alcance adicional:** `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review.md` contra el §6 que estrena.
- **Método:** solo lectura; contraste contra `tests/test_docs_gobernanza.py`, los nueve disparadores reales —los ocho legacy más el §14 del objeto—, `PLAN.md`, `docs/bitacora/2026.md`, `docs/DEAD_ENDS.md`, `docs/INDICE.md` y `docs/GOBERNANZA_FUENTES_VERDAD.md` §5.

## Veredicto global

**NO-SHIP en rev. 2.** La rev. 2 arregla de verdad la mayoría de los seis defectos anteriores: elimina el ledger y G9; declara el retrofit; especifica un regex reproducible y excluye cercas; reduce el frontmatter; separa informe y adjudicación; y fija un corte temporal defendible. La primera acta escrita bajo el contrato conserva literalmente el informe y cumple su §6.

Lo que no resiste es el sustituto del ledger. El censo no contiene 16 revisiones bajo su propia identidad, sino **al menos 24** con la evidencia conservadora disponible. Además, los artefactos que el generador dice leer no contienen `ronda` ni representan de forma uno-a-uno las revisiones. El script no puede producir la tabla prometida sin excepciones legacy codificadas a mano y no tiene consumidor fuera de su propio criterio de aceptación. Es código muerto propuesto para preservar una solución, no una capacidad derivable.

## Hallazgos

### H-01 — CRÍTICA — El censo de 16 contradice la identidad del §1.1 y omite al menos ocho revisiones posteriores al corte

La tupla de `§1.1:23-24` sirve para deduplicar representaciones, pero el §1.3 no la aplica de forma consistente y tampoco define el predicado de inclusión: qué procesos llamados «revisión adversarial» entran y cuáles no.

La cuenta conservadora es:

| Ajuste sobre las 16 declaradas | Incremento | Evidencia |
|---|---:|---|
| La fila 4 agrupa «Codex + Claude» como una sola, pese a que `§1.1:32-33` ordena contarlos como dos | +1 | `§1.3:53`; `2026-07-27-cableado-atomize-sala-maquina-adversarial-review.md:4`; `docs/bitacora/2026.md:142` |
| Bundle por hilo: tras las dos revisiones de diseño hubo una revisión final de la rama que encontró tres caminos de pérdida/sobrescritura | +1 | `PLAN.md:757-768,2127`; `docs/bitacora/2026.md:150` |
| Cableado: el censo incluye spec y plan, pero no la revisión final Opus de la rama, que devolvió NO-SHIP con un Critical destructivo | +1 | `docs/bitacora/2026.md:138` |
| Enumeración recursiva: el censo solo apunta al §11 de la spec; faltan la revisión del plan y la de la rama construida | +2 | `docs/bitacora/2026.md:134`; `PLAN.md:383-386`; el §11 de la spec registra otra revisión, con seis bloqueantes distintos |
| `MEJORAS #109` / historial citado: faltan la revisión del plan y la de la rama, ambas NO EJECUTABLE | +2 | `docs/bitacora/2026.md:62,70`; una de ellas dejó adjudicación en `2026-07-30-historial-citado-localizable-design.md:238` |
| OCR ciego: revisión adversarial propia sobre el diff, con tres correcciones | +1 | `docs/bitacora/2026.md:144` |
| **Total mínimo** | **16 + 8 = 24** | No cuenta las «revisiones por tarea» de `docs/bitacora/2026.md:138`, porque el spec no dice si pertenecen a la población |

La selección es internamente incompatible. La revisión de rama de sandwich sí cuenta como la fila 11; las revisiones de rama de bundle, cableado, enumeración e historial no. La pasada propia de Claude cuenta dentro de la fila 4; la pasada propia de OCR no. Los subagentes cuentan en la fila 3, pero las revisiones por tarea quedan sin regla.

Los dos casos que el mandato señalaba como sospechosos no reducen la cuenta:

- **Filas 1-2:** son dos revisiones. El acta de emails declara expresamente una «Segunda revisión, independiente» el 2026-07-27 (`…emails-atomizados-sala-lectura-adversarial-review.md:9-16`), distinta de Codex 2026-07-23 (`:3`). Que una sola adjudicación consuma ambas no las convierte en una.
- **Filas 6-7:** son dos revisiones. `handoff-…-codex-informe.md` y `…-review.md` son dos formatos de la primera; `…-review-2.md:5-13` declara una segunda pasada sobre v3.1, commit `972da2d`, con seis hallazgos nuevos.

**Remedio exigido:** definir el predicado de inclusión además de la identidad —incluidas revisiones de rama, autorrevisiones, revisiones por tarea y revisores subagente— y rehacer el censo desde las fuentes postcorte. No publicar otra cardinalidad hasta poder explicar cada inclusión y cada exclusión con la misma regla.

### H-02 — ALTA — `scripts/censo_revisiones.py` no puede derivar la salida prometida y no tiene consumidor real

La divergencia sobre H-04 fue solo parcialmente correcta. **Conservar el criterio 2 sí era correcto:** G7 y G8 necesitan una aceptación explícita. Conservar el objetivo humano «poder auditar qué se revisó» también era legítimo. Lo que no se sostiene es materializarlo ahora como generador y criterio 6.

El generador se especifica como lector de encabezados y frontmatter (`§7:235-245`), pero esas fuentes no contienen su clave de identidad ni sus columnas:

- la tabla de salida exige `ronda` (`§7:244`), pero ni el encabezado, ni sus grupos regex, ni la ficha de cinco líneas (`§5:150-160`) tienen ese campo;
- `cobertura` solo vive en el acta; las adjudicaciones migradas sin acta no la aportan;
- una sola acta de emails contiene dos revisiones, y su frontmatter escalar solo puede declarar un `revisor`, una rev., un commit y un veredicto;
- el acta de cableado agrupa dos revisores que §1.1 obliga a contar por separado;
- la segunda revisión de vista solo vive en el handoff `review-2`, población que el lector de §7 no recorre;
- el lector no tiene una clave estable para deduplicar acta y encabezado ni para separar varias revisiones consumidas por una sola adjudicación.

Por tanto, no puede reconstruir ni las 16 filas declaradas —menos aún las ≥24 reales— sin una tabla de excepciones o datos hardcodeados. Eso ya no sería «derivar»: sería esconder el ledger dentro de Python.

La prueba de utilidad también falla. Una búsqueda completa de `censo_revisiones` fuera del propio spec da cero referencias; no hay integración con cierre de sesión, runbook, `CLAUDE.md`, `INDICE.md` ni otro consumidor. El propio riesgo de `§11:336-338` admite que nadie puede correrlo y que entonces será código muerto. El criterio 6 es su único consumidor y el generador existe para satisfacer ese mismo criterio: circuito cerrado, no demanda externa.

**Remedio exigido:** no escribir `scripts/censo_revisiones.py` en este cambio y retirar o diferir el criterio 6. Mantener el criterio 2. Si aparece un consumidor real, primero hacer representable cada revisión —por ejemplo, `revision_id` y `ronda`, con un registro estructurado por revisión y cardinalidad uno-a-uno—, después escribir un lector probado contra identidades esperadas. La ausencia de tabla versionada y de G9 debe conservarse.

### H-03 — ALTA — La exención global de actas deja sin guard el contrato corporal de §6

La exención de G7 tiene una razón válida: el informe literal puede contener cualquier encabezado y no debe reinterpretarse como adjudicación del proyecto. El problema está en el guard sustituto. G8 solo exige frontmatter y que el fichero citado por `adjudicado_en` exista (`§8:262-263`); no comprueba ninguno de estos mandatos de §6:

- que existan las dos secciones «Informe recibido, sin modificar» y «Evidencia verificada»;
- que el informe se conserve literal;
- que la adjudicación no se vuelva a redactar en el acta;
- que `adjudicado_en` señale una sección real, no solo un fichero real.

Además, `tipo: revision-adversarial` exime por igual a las cuatro actas híbridas y a todas las futuras (`§6:222-225`, `§8:258-261`). No hay marcador que distinga el legado híbrido. Así, una acta futura con frontmatter válido, cuerpo vacío o una adjudicación duplicada pasa G8. La excepción cautelar se convierte en una clase permanente parcialmente fuera de guard.

La primera acta no explota el hueco: **cumple**. Tiene exactamente las ocho claves permitidas; `adjudicado_en` llega al §14; contiene las dos secciones; y las 106 líneas del informe archivado son literales, descontando la línea en blanco separadora. Esto demuestra que el contrato es verificable al menos en estructura y literalidad, no que G8 lo imponga.

**Remedio exigido:** mantener las actas fuera de G7, pero reforzar G8. Marcar las cuatro heredadas mediante una allowlist cerrada o `formato: hibrido-legacy`; para toda acta nueva, comprobar las dos secciones, el destino concreto de `adjudicado_en` y la presencia del bloque literal. La excepción legacy no debe aplicarse automáticamente a documentos futuros.

## Comprobaciones que resistieron

### Regex y retrofit

Ejecutado el regex literal de §5.1 sobre `docs/superpowers/**/*.md`, eliminando cercas antes del match:

- **9** encabezados disparadores fuera de cerca;
- **3** casan el regex bruto;
- de esos, **2** pasan también vocabularios (`sandwich` §9 y este spec §14);
- **1** tiene solo token inválido (`resuelto`);
- **6** fallan estructura.

El desglose «1 casa / 1 solo token / 6 estructura» de §9 es correcto. La plantilla cercada queda fuera. La frase «2 casan limpio» es correcta si «limpio» incluye la validación de vocabulario; el regex bruto, aisladamente, casa tres.

### Corte temporal

**No hay hallazgo contra el 2026-07-23 como corte de migración.** Es una frontera declarada y defendible: antes no había contrato estable ni informes archivables, y reconstruir la tupla completa desde párrafos de `PLAN.md` fingiría exactitud. Debe seguir describiéndose como «cobertura desde el corte», no como historia total. Todas las omisiones de H-01 son posteriores al corte; por tanto, el corte no las amnistía.

### Fuentes de verdad, índice y proveedor fallido

- Retirar el registro versionado respeta «un hecho → un hogar» de `GOBERNANZA_FUENTES_VERDAD.md:15-22`.
- No añadirlo a `INDICE.md` es coherente con `INDICE.md:23-28`, que excluye specs/planes fechados y remite su estado a `PLAN.md`.
- La corrección de `DEAD_ENDS.md` resiste: los cuatro fallos de `agy` son indisponibilidad de proveedor, no cuatro revisiones autónomas sin cobertura.

## Verificaciones ejecutadas

- `HEAD`: `2c2a6d09393ea472712cd37847bff77165227672`.
- `tests/test_docs_gobernanza.py`: **8 passed** con bytecode y cache desactivados y `--basetemp` en `%TEMP%`. Son los G1-G6 actuales; no validan todavía los G7/G8 propuestos.
- Regex del §5.1: **9 disparadores / 3 match bruto / 2 limpios / 1 solo token / 6 estructura**.
- Acta nueva: frontmatter permitido; destino existente; dos secciones; **106/106 líneas literales**.
- `scripts/censo_revisiones.py`: no existe aún; fuera del spec hay **0 consumidores o referencias**.
- Árbol objetivo limpio antes de escribir este informe; no se modificó ningún fichero del repositorio.

---

## 2. Evidencia verificada por Claude al adjudicar

Comprobado abriendo la fuente. La adjudicación razonada está en el §15 del spec.

**H-02 y H-03 son autoevidentes dentro del objeto revisado**, sin salir de él:

- La rev. 2 pedía en su §7 una columna `ronda` y su ficha del §5 tenía cinco campos, ninguno de
  ellos `ronda`. Tampoco `cobertura`, que el §3 dejaba como prosa libre. **Confirmado.**
- Su G8 (§8) exigía frontmatter válido y que `adjudicado_en` apuntara a un fichero existente, y
  **nada más**: ninguno de los cuatro mandatos corporales del §6. **Confirmado.**

**H-01 se contrastó contra la fuente**, no contra la tabla del informe:

- `docs/bitacora/2026.md:150` — «brainstorming → spec → **dos** revisiones adversariales → re-tajo →
  plan TDD → build → **revisión final** → merge». La revisión final existe y no estaba censada.
  **Confirmado.**
- `PLAN.md:757-761` — esa revisión final encontró «tres caminos de pérdida/sobrescritura» y forzó
  «nombres como función pura del fichero de origen». No es una revisión menor. **Confirmado.**
- `docs/bitacora/2026.md:138` — «revisión **por tarea** + revisión **de rama**» en un build de siete
  tareas. Dos poblaciones que la rev. 2 no contemplaba. **Confirmado.**
- `docs/bitacora/2026.md:70` — «La del **plan** devolvió NO EJECUTABLE y la de la **rama
  construida** otro, con dos defectos vivos que yo no habría encontrado». **Confirmado.**
- `docs/bitacora/2026.md:62,134,144` y `PLAN.md:383-386` — las demás entradas de la tabla del
  informe resuelven a cierres reales con revisiones no censadas. **Confirmado en dirección y
  magnitud**; la cifra exacta no se adopta, porque el remedio del propio hallazgo prohíbe publicar
  cardinalidad antes de aplicar el predicado.

**Contradicción interna propia**, verificable sin fuente externa: la rev. 2 escribió en §1.1 que
Codex y Claude cuentan como dos revisiones, y agrupó «Codex + Claude» como una en la fila 4 de la
tabla inmediatamente siguiente. **Confirmado.**

### Nota de método

Tres de tres confirmados, ninguno refutado, y por segunda vez seguida. Dos de los tres no
necesitaban fuente externa: estaban dentro del documento que yo mismo había escrito y revisado. Eso
no es un problema del revisor: es la medida de lo que una autorrevisión no ve.

La única divergencia con el informe en las dos rondas fue la del H-04 de la ronda 1, y esta ronda
demostró que fue medio equivocada. Queda anotada en el §14 del spec, no borrada.
