---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md
objeto_rev: "3"
commit: 1a6e3d8
ronda: "3"
clase: diseño
revisor: Codex
cobertura: ejecutada
veredicto: LISTA-CON-CAMBIOS
sha256_informe: 43b945e24a9aa990bc7aea1ffc0d4aae205e21a55f6f3241383bc6781587a325
adjudicado_en: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §16
---

# Revisión adversarial — gobernanza de las revisiones adversariales (rev. 3, ronda 3)

## 1. Informe recibido de Codex, sin modificar

> Texto íntegro entregado el 2026-08-01 en `%TEMP%\revision-gobernanza-revisiones-r3.md`, 147
> líneas, `sha256` en el frontmatter y verificado por Claude al recibirlo. No se ha corregido
> ortografía, numeración ni formato. Las referencias `§N:LLL` son del revisor.

---

# Tercera revisión adversarial — gobernanza de las revisiones adversariales

- **Objeto:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`, rev. 3.
- **Commit revisado:** `1a6e3d86f3ff3a254861e2ea732ff602a983f150`.
- **Rama/worktree:** `claude/internal-dialogue-documentation-4fbc1c` / `.claude/worktrees/internal-dialogue-documentation-4fbc1c`.
- **Alcance adicional:** las actas `…-adversarial-review.md` y `…-adversarial-review-r2.md` contra el §6 de la rev. 3.
- **Método:** solo lectura; contraste contra el código y corpus reales, no solo contra el delta. Tests y temporales fuera del repo.

## Veredicto global

**LISTA-CON-CAMBIOS.** La arquitectura ya es aceptable: no hay ledger ni generador prematuro; la adjudicación conserva hogar único; la ficha ya representa clase, ronda y cobertura; la allowlist legacy es cerrada; y las dos actas nuevas forman una cadena verificable. No hay un tercer defecto que obligue a replantear el diseño entero.

Antes de escribir el plan o los guards deben corregirse **siete hallazgos acotados**. Cuatro afectan a la población, la pérdida del informe, la seguridad del revisor y la comprobación criptográfica; los demás cierran la migración, el nombre de las actas y una medición obsoleta. Son cambios locales, pero los cuatro primeros no son opcionales.

## Hallazgos

### H-01 — ALTA — El predicado y las cuatro clases no forman una partición de la práctica que el propio spec migra

El predicado de `§1.1:25-27` limita el objeto a «spec, plan, diff o rama». Sin embargo, una de las cuatro actas heredadas revisa expresamente un **handoff**: `2026-07-26-gobernanza-indice-adversarial-review.md:3-6` fija como objeto `handoff-2026-07-26-gobernanza-indice-adversarial.md`. Ese handoff contiene un diagnóstico originado en chat y un mandato de buscar activamente por qué era falso (`handoff…:18-25`). El proyecto lo llama revisión adversarial, lo cerró en `PLAN.md:2128` y el §9 quiere migrar su acta, pero §1.1 lo deja fuera.

Los paneles «4 lentes» muestran el mismo límite, aunque el ejemplo de `PLAN.md:953` sea anterior al corte: la práctica llama «revisión adversarial del spec» a un panel que consolida perspectivas y produce correcciones, sin que necesariamente declare con la palabra exacta «refutar». Debe entrar por su función y mandato, no depender de un token histórico.

La clase C añade una contradicción distinta. Una revisión por tarea que ataca un diff y produce un hallazgo cumple literalmente §1.1. Pero `§1.2:43` dice que nunca recibe identidad propia y se convierte en una revisión B. Así, C figura en el vocabulario y en la población, pero desaparece al contar y al aplicar el criterio 5 («toda revisión… tiene encabezado»). El umbral de §11 —solo separar cuando produce un veredicto sobre el objeto— tampoco coincide con el predicado, que admite **hallazgos o veredicto**.

**Cambio exigido:** ampliar «artefacto» a cualquier propuesta o artefacto concreto y versionable del proyecto —incluido diagnóstico/handoff— y definir evidencia funcional del mandato adversarial. Para C, elegir una sola semántica: o las revisiones por tarea quedan fuera de la población y se registran como cobertura del B, o C es un evento agregado propio, con una ficha C y una adjudicación que enumera revisores, tareas y todos los hallazgos sustantivos. No puede ser clase C y revisión B a la vez.

### H-02 — ALTA — La clase B conserva la adjudicación del autor y puede perder el texto del revisor que encontró el defecto

`§1.2:42` y §3 exigen acta en B solo «si hubo informe externo». La distinción externo/interno no protege la evidencia. Una revisión final de Opus o de un subagente produce texto con hallazgos aunque ocurra dentro de la sesión; si solo se conserva el encabezado y la adjudicación escrita por Claude, ya no se puede contrastar qué dijo el revisor con lo que el autor decidió que dijo.

Son precisamente las B las que compraron los defectos más caros: la rama del bundle encontró tres caminos de pérdida/sobrescritura (`PLAN.md:757-761`), y la de cableado un Critical destructivo (`docs/bitacora/2026.md:138`). La traza graduada conserva menos fuente independiente en la clase con más riesgo material.

**Cambio exigido:** acta para toda A o B que haya producido una respuesta textual recuperable, sea el revisor «externo», Opus, subagente o Codex. `sin informe` debe quedar como excepción histórica o para un proceso que genuinamente solo emitió un estado estructurado. Las C agregadas pueden conservar una síntesis única, pero la adjudicación B debe enumerar sus hallazgos sustantivos y procedencia.

### H-03 — ALTA — §10.1 sustituye una prohibición continua por una comprobación final que no cubre ignorados, datos ni efectos externos

La premisa de `§10.1:381-393` es falsa: el `AGENTS.md` actual no prohíbe ejecutar. Dice «solo lectura, no escribes en el repo» y a la vez ordena contrastar contra el código. Ejecutar `pytest` con bytecode/cache desactivados y `--basetemp` externo cumple ambas cosas; así se hicieron las tres rondas.

«El árbol queda idéntico + git status limpio + sin ficheros nuevos» es más débil si reemplaza la regla actual:

- permite escribir y revertir antes de la comprobación final;
- `git status` no detecta cambios en ficheros ignorados existentes: `.gitignore:11,17-18,23,29-35` excluye caches, `dist/`, `.env*` y `data/CASOS/*`;
- no cubre escrituras en CRM, Drive u otros sistemas externos;
- «sin ficheros nuevos» no detecta la modificación de un expediente o cache ignorado preexistente.

La ejecución necesaria no requiere ninguno de esos permisos. En esta pasada `pytest` corrió con todos los artefactos fuera, y una instantánea de **1.368 ficheros** antes/después dio 0 añadidos, 0 borrados y 0 modificados.

**Cambio exigido:** conservar la prohibición continua y añadir la capacidad: «repo, ignorados, `data/CASOS/` y sistemas externos son entradas de solo lectura durante toda la revisión; se permite ejecutar código/tests solo cuando todas sus escrituras están redirigidas fuera del repo y no hay side effects externos». `git status --porcelain --untracked-files=all` antes/después es evidencia adicional, no sustituto. Mantener la receta de `PYTHONDONTWRITEBYTECODE`, `-p no:cacheprovider` y `--basetemp` externo. No queda prohibida ninguna ejecución legítima de esta revisión.

### H-04 — ALTA — G8 exige que el hash exista, pero no lo compara, y su regla para legacy contradice §9

`§8:307-315` exige `sha256_informe` presente y un bloque literal, pero no ordena calcular el SHA-256 del bloque §1 y compararlo con el frontmatter. Por tanto, una transcripción alterada y un hash que solo «está presente» pasan el guard descrito. El hash sí permite una comprobación autónoma aun si la copia externa se pierde: normalizar el bloque literal a UTF-8/LF, añadir su salto final, calcular SHA-256 y exigir igualdad. Lo que se pierde sin original externo es la prueba independiente de que el digest inicial provenía del informe recibido, no la capacidad de detectar alteraciones posteriores.

La política legacy es además inconsistente. G8 exige hash siempre que `cobertura: ejecutada` (`§8:311`), mientras §9 ordena omitirlo para los informes crudos perdidos (`§9:365-367`). Las cuatro actas heredadas son revisiones ejecutadas. No pueden satisfacer ambas reglas.

**Cambio exigido:** una desigualdad de hash es **rojo**, nunca aviso. G8 debe recomputar el digest del bloque literal con una canonicalización explícita. La allowlist cerrada resuelve la clase permanente fuera de guard, pero debe llevar una excepción igualmente cerrada para `sha256_informe`/cuerpo legacy, o un token tipado `no-disponible-legacy`; no una omisión que contradiga la regla general. `%TEMP%` no es almacenamiento duradero: o se define un archivo externo con retención, o el acta + digest + verificación independiente al recibirla pasan a ser el archivo durable.

### H-05 — MEDIA — La migración no crea los encabezados que sus criterios exigen y debe trocearse por dependencia, no puramente por clase

El modelo exige adjudicación embebida y el criterio 5 exige encabezado/ficha para toda revisión. Pero §9 dice que a las cuatro actas híbridas solo se añade frontmatter y que no se mueve su adjudicación. Tres objetos siguen sin encabezado canónico:

- `2026-07-23-emails-atomizados-sala-lectura-design.md` — el acta contiene dos revisiones y la adjudicación;
- `2026-07-27-cableado-atomize-sala-maquina-design.md` — el acta contiene Codex + Claude y la tabla;
- el handoff de gobernanza de 2026-07-26 — el acta contiene el resultado.

Solo dual workspace ya tiene §20. La tabla «Revisiones sin encabezado» de §9 añade la pasada Claude de cableado, pero omite la revisión Codex del mismo objeto, las dos de emails y la gobernanza. Conservar intacto el cuerpo legacy es compatible con añadir al objeto un encabezado/ficha/puntero; no hacerlo deja incumplidos §3 y §12.5.

No hace falta un PR gigante. Sí es inviable activar G7/G8 en el primer PR de una serie: los guards recorren toda la población y fallarán hasta completar el retrofit. La secuencia ejecutable es migrar por **verticales/dependencias** —A con su acta y encabezado; B+C juntas; D— y añadir los guards al final. G2 solo exige que cada referencia y su acta entren en el mismo PR.

**Cambio exigido:** inventario de migración una fila por identidad, incluyendo las revisiones acta-only; headers/punteros en sus objetos; excepción legacy explícita; y orden de PRs con guards al final. El predicado y el contrato de artefactos sí pertenecen al mismo spec porque la clase decide la traza. El inventario, tareas y orden de PRs pertenecen a un **plan de migración separado**, no deben seguir creciendo dentro del spec.

### H-06 — MEDIA — El nombre `-rN` no es inyectivo respecto de la identidad que §1.3 permite

La identidad incluye objeto y revisor; el nombre del acta solo incluye fecha, tema y ronda. Dos revisores externos del mismo objeto en la misma ronda son dos revisiones según §1.3, pero intentarían escribir el mismo fichero. También colisionan una revisión de spec y otra de plan/rama del mismo tema y fecha si ambas son ronda 1; la enumeración recursiva ya demuestra que spec, plan y rama pueden revisarse en la misma jornada.

**Cambio exigido:** incorporar al nombre un discriminante del objeto/clase y, cuando proceda, del revisor o un `revision_id` estable: por ejemplo `…-spec-r1-codex-adversarial-review.md` / `…-branch-r1-opus-adversarial-review.md`. No confiar en que `ronda` sea global entre objetos distintos.

El sufijo no rompe por sí mismo G2, `INDICE.md` ni la excepción de handoffs: G2 acepta el fichero si existe, los specs fechados no se indexan y los tres handoffs históricos siguen en su población. La acta `…-adversarial-review-r2.md` cumple el esquema actual.

### H-07 — BAJA — La medición incorporada en §5.1 quedó obsoleta al añadir §15

El corpus actual contiene **10** disparadores, no 9. El regex bruto casa **4**, no 3; pasan vocabulario **3**, no 2; quedan 1 solo-token y 6 estructurales. El tercer limpio es el nuevo §15. La afirmación `§5.1:211-213` reproduce todavía la foto de la rev. 2.

**Cambio exigido:** actualizar a `10 / 4 bruto / 3 limpio / 1 token / 6 estructura` y fijar la medición en un test/fixture para que añadir otra adjudicación no vuelva a dejar prosa obsoleta.

## Respuesta al mandato, punto por punto

### 1. §1.1 y §1.2 — población, paneles, C y traza B

- El predicado deja fuera al menos el diagnóstico/handoff de gobernanza que el propio corpus trata como revisión (H-01).
- Un panel «4 lentes» cuenta como **una** revisión de diseño si hubo un único mandato y veredicto consolidado; sus lentes son metodología/revisores, no clase C. La palabra exacta «refutar» no debe ser condición histórica.
- La agregación C es proporcionada como reconstrucción legacy, pero es coladero como norma futura mientras oculte identidad y hallazgos. Debe ser cobertura de B o un agregado C explícito, no ambos.
- Exigir acta solo en B «con informe externo» pierde la fuente independiente de revisiones de rama; debe archivarse toda respuesta textual recuperable (H-02).

### 2. §9 y §11 — ejecución, PRs y descomposición

- No obliga a un PR gigante si G7/G8 se activan al final. La partición correcta es por dependencia/vertical, con B+C juntas; no por cuatro clases completamente independientes.
- La migración actual omite encabezados acta-only y no puede cumplir el criterio 5 (H-05).
- Población y contrato de artefactos pertenecen al mismo spec. El censo histórico, tareas, orden y PRs son otro artefacto: un plan de migración.

### 3. §10.1 — permisos del revisor

- La invariante final no reemplaza «solo lectura»: no ve ignorados modificados ni efectos externos y permite mutación transitoria (H-03).
- Mantener no-escritura durante toda la revisión y autorizar ejecución con outputs externos cubre cache, untracked, `data/CASOS/`, CRM y Drive.
- No prohíbe nada necesario: regex, lectura de git y pytest funcionaron bajo ese contrato.

### 4. §8 y §6 — integridad, hash y allowlist

- Con solo presencia del hash, G8 no verifica literalidad. Recomputando el bloque §1 sí puede verificar integridad posterior aunque se pierda el original; no puede recrear la prueba independiente de origen.
- Mismatch = **fallo rojo**. Un aviso convierte una cadena rota en suite verde.
- La allowlist cerrada de cuatro nombres sí resuelve la exención permanente; falta armonizar su excepción de hash/cuerpo con G8 (H-04).

### 5. Acta por ronda y sufijo `-rN`

- No rompe G2, `INDICE.md` ni los handoffs históricos.
- El nombre colisiona para revisores u objetos distintos con la misma ronda/tema/fecha (H-06).
- `…-adversarial-review-r2.md` cumple §6: nombre, ronda 2, clase A, puntero §15, dos secciones, 107/107 líneas literales y hash correcto.

### 6. Generador diferido y criterio 6

- Diferir el generador es correcto y debe mantenerse; no hay consumidor real.
- «Representable» aislado es propiedad del esquema y puede cumplirse con datos ausentes. Junto con el criterio 5 se vuelve verificable, pero conviene escribir **«cada revisión postcorte está representada exactamente una vez»** y exigir una matriz de inventario fuente → identidad → encabezado/acta. Así deja de ser prosa aspiracional.

### 7. Mediciones y cadena de hashes

- Regex: **10 disparadores / 4 matches brutos / 3 limpios / 1 solo-token / 6 estructurales**. Plantilla cercada descartada.
- Ronda 1: `sha256_informe = 4f45f867de828badfdcd9f583e1731856001265ee345bb910f450b5142663f58`; coincide con la copia externa y con el bloque literal, **106/106 líneas**.
- Ronda 2: `sha256_informe = 20c45f93c0460a8f91ba426c9570ac918b01882a43f07aec9f549166070f4114`; coincide con la copia externa y con el bloque literal, **107/107 líneas**.

## Comprobaciones que resistieron

- Corte del 2026-07-23: sigue siendo una frontera de migración defendible.
- Retirada del ledger, G9 y generador: correcta; `scripts/censo_revisiones.py` y `docs/REVISIONES_ADVERSARIALES.md` no existen.
- `DEAD_ENDS.md`: los fallos de `agy` siguen siendo indisponibilidad de proveedor, no revisiones fantasma autónomas.
- `INDICE.md`: no debe indexar las actas fechadas; su `:23-28` excluye specs/planes fechados.
- La allowlist cerrada es el remedio correcto para los cuatro híbridos, una vez explicitada su excepción de G8.
- Las dos actas nuevas no duplican la adjudicación y sus punteros resuelven a §14/§15.

## Verificaciones ejecutadas

- `HEAD`: `1a6e3d86f3ff3a254861e2ea732ff602a983f150`.
- `tests/test_docs_gobernanza.py`: **8 passed**. Son G1-G6 actuales; G7/G8 aún son diseño.
- Ejecución: `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, `--basetemp` bajo `%TEMP%`.
- Instantánea integral antes/después de pytest: **1.368 → 1.368 ficheros; 0 añadidos, 0 borrados, 0 modificados; 0 directorios añadidos/borrados**.
- `git status --porcelain=v1 --untracked-files=all`: vacío.
- Los dos informes previos conservaron sus hashes durante la ejecución.
- Este informe se escribió fuera del repo; no se modificó ningún fichero del worktree.

---

## 2. Evidencia verificada por Claude al adjudicar

Comprobado abriendo la fuente. La adjudicación razonada está en el §16 del spec.

- **H-01, el objeto que el predicado excluye.**
  `2026-07-26-gobernanza-indice-adversarial-review.md:4` fija como objeto
  `docs/superpowers/handoffs/handoff-2026-07-26-gobernanza-indice-adversarial.md` — un **handoff**,
  que el predicado del §1.1 no admite, y cuya acta el §9 manda migrar. **Confirmado.**
  *Hallazgo adicional al abrirlo:* su línea 3 declara como revisor «Claude Code (orquestador + 5
  subagentes en paralelo, uno por hallazgo)», una forma que las cuatro clases tampoco cubren, y su
  línea 5 dice «pendiente de adjudicación por **Nikolai**» — un adjudicador que el modelo no
  contempla. El hallazgo es más ancho de lo que el informe describe.
- **H-01, clase C contra el criterio 5.** §1.2 dice que C «nunca» recibe encabezado y §12.5 exige
  encabezado a toda revisión de la población. Contradicción literal entre dos secciones del mismo
  documento. **Confirmado.**
- **H-03, la premisa que yo daba por buena era falsa.** `AGENTS.md:33` dice literalmente «**solo
  lectura**, no escribes en el repo»: la prohibición está glosada como **no escribir**, no como no
  ejecutar. Y el mismo fichero ordena contrastar «contra el código real, no solo contra el diff».
  Mi §10.1 diagnosticaba un problema que el texto no tiene. **Confirmado contra mí.**
- **H-03, el agujero que mi invariante abría.** `.gitignore` excluye `__pycache__/`,
  `.pytest_cache/`, `.coverage`, `dist/`, `.env`, `.env.*` y **`data/CASOS/*`**. «`git status`
  limpio y sin ficheros nuevos» **no detecta la modificación de un expediente real preexistente**.
  Es lo más peligroso que se escribió en las tres rondas, y lo escribí yo. **Confirmado.**
- **H-04, presencia contra comparación.** §8 exigía `sha256_informe` **presente**; en ninguna parte
  ordenaba recomputarlo y compararlo. **Confirmado.**
- **H-04, contradicción §8 ↔ §9.** §8 exige hash siempre que `cobertura: ejecutada`; §9 manda
  omitirlo en los informes perdidos, que son revisiones ejecutadas. **Confirmado.**
- **H-05, §9 contra §12.5.** Las cuatro actas heredadas conservan su adjudicación y sus objetos
  quedan sin encabezado, mientras §12.5 lo exige a toda revisión. **Confirmado.**
- **H-06.** La identidad del §1.3 incluye objeto y revisor; el nombre del acta solo fecha, tema y
  ronda. Dos revisores del mismo objeto y ronda colisionan. **Confirmado.**
- **H-07, medición obsoleta.** El §5.1 seguía diciendo 9/3/2/1/6 cuando mi propia sonda imprimió
  10 disparadores y 3 limpios al añadir el §15. Lo reporté en el chat y no lo llevé al documento.
  **Confirmado.**
- **Cadena de hashes, verificada por mí también.** `sha256sum` del informe de esta ronda da
  `43b945e2…325`, idéntico al declarado. 147 líneas.

### Nota de método

Tercera ronda, siete de siete confirmados, ninguno refutado: **16 de 16 en las tres rondas**. Dos
lecturas, y las dos importan. La primera, que el revisor está encontrando defectos reales y no
ceremonia. La segunda, que mi autorrevisión no detecta contradicciones entre secciones vecinas del
mismo documento —H-01, H-04 y H-05 son todas de esa forma— y que eso no ha mejorado en tres rondas.

El hallazgo de más valor es **H-03**, y por un motivo que conviene dejar escrito: el revisor
argumentó **contra la ampliación de sus propios permisos**. Yo había declarado en el §10.1 que su
opinión ahí sería insumo y no veredicto por ser parte interesada; resultó que el interés apuntaba en
la dirección contraria a la esperada, y que quien se equivocaba era el autor.
