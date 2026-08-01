---
tipo: handoff
estado: consumido
creado: 2026-08-01
origen: revisión adversarial de Codex (chat, solo lectura) — 2ª pasada sobre la rev. 2, commit `05d985f`
destino: sesión Claude Code — adjudicar los 11 hallazgos nuevos y decidir el corte del alcance
consumido_por: "rev. 3 de la spec (§13 mapea cada hallazgo a la sección que lo corrige). N-M-2 partió el trabajo en pieza A (motor, construible) y pieza B (retrofit/saneamiento, BLOQUEADA por el lock). N-B0-4 estableció la dependencia con la Fase 2 de la fila #3 de PLAN.md."
titulo: Revisión adversarial 2ª pasada — identidad del segmento de bundle (rev. 2)
revisor: Codex
spec: docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md
commit_revisado: 05d985f
veredicto: NO SHIP
pasada_anterior: docs/superpowers/handoffs/handoff-2026-08-01-identidad-segmento-codex-review.md
---

> **Andamio efímero** (gobernanza §5). Texto **recibido de Codex por chat, sin modificar**. Trabajó
> en solo lectura y no modificó el repo.
>
> **Adjudicación de Claude Code:** en el **§13 de la spec**. Los cuatro B0 nuevos se verificaron
> contra la fuente y **los cuatro se sostienen**; tres de ellos son defectos que introdujo la propia
> rev. 2 (`doc_id` como campo de ruta sin formato canónico, la contradicción del ledger, y un guard
> ciego justo en el caso para el que se escribió). El cuarto, N-B0-4, se apoya en `xfail` vivos del
> repo y **no se arregla en esta spec**: bloquea la pieza B hasta la Fase 2 de la fila #3.
>
> **Su crítica a mi adjudicación de la 1ª pasada es correcta y queda aceptada:** cerré B0-1 con una
> solución barata que no cubría el caso de fallo real, y di A-5 por resuelto apoyándome en un
> mecanismo que no excluye.

## VEREDICTO: NO SHIP

La rev. 2 corrige la identidad ordinal, pero el nuevo `doc_id` carece todavía de un contrato seguro
de validación, inmutabilidad y retiro. Además, el archivado previo no cierra B0-1 y el lock actual no
garantiza exclusión: los propios tests documentan dos titulares simultáneos.

## Cierre de la pasada 1

| ID | Estado en rev. 2 | Evidencia y adjudicación |
|---|---|---|
| B0-1 | **A medias** | §5 reconoce correctamente la falsificación de custodia y añade archivo previo + guard de hash. Pero el archivo de PDF/MD/raw tampoco es atómico y el guard solo recorre filas de cobertura, solo comprueba el PDF y solo avisa. Un fallo después de escribir artefactos pero antes de devolver sus filas puede eludirlo por completo. No doy por suficiente la solución barata. |
| B0-2 | **Resuelto** | §3–§3.2 elimina `seg` como identidad y lo sustituye por `doc_id`. El defecto ordinal concreto queda cerrado. Los defectos del nuevo ciclo de vida de `doc_id` se consignan como hallazgos nuevos. |
| A-1 | **A medias** | La rev. 2 corrige con razón mi atribución: `_split_o_md:562` solo cubre `split.detectar`; quien absorbe es `ejecutar:732`. `ManifestValidationError` atravesaría el `except`, pero falta prevalidar el lote: si el manifiesto inválido es el segundo documento, el primero ya escribió y sus filas se pierden al no retornar `ejecutar`. |
| A-2 | **Resuelto** | §6.1 define inequívocamente 0, 1 y N coincidencias; N>1 aborta el grupo. |
| A-3 | **Resuelto** | §6.2 declara no migrables los casos sin `_cobertura.json`; ya no intenta inferir autoridad desde Markdown. |
| A-4 | **A medias** | §6.3 introduce el journal y deja de adivinar por el estado del disco. Faltan ubicación durable, escritura atómica, identificación inequívoca de la corrida y salida operativa cuando el journal se pierde o resulta incoherente. |
| A-5 | **A medias** | §6.4 reconoce `MERGE_EXCLUSIONS`/`GRUPOS_MERGE`, pero sostiene incorrectamente que adquirir "el lock del protocolo" elimina toda copia divergente. El lock actual es de checkout, admite dos titulares en un interleaving ya probado y `cmd_checkin` no verifica nonce al empezar. |
| M-1 | **Resuelto** | §7 incorpora `_intake_log.jsonl`, decide conservarlo byte-idéntico y emitir un evento nuevo. La búsqueda global no encontró un consumidor productivo que cruce los slugs históricos del evento con la cobertura vigente. |
| M-2 | **A medias** | Se añaden hashes, CLI y fault injection, pero los tests 4, 5 y 7 todavía permiten implementaciones vacuas o incompletas. |
| M-3 | **Resuelto** | §2 corrige el censo: 7 PDF + 7 MD + 7 raw = 21 excedentes. No repetí el barrido de Drive. |

La adjudicación demasiado optimista está en B0-1 y A-5: ambos siguen abiertos.

## Hallazgos nuevos

| ID | Severidad | Afirmación atacada | Evidencia | Qué cambiar |
|---|---|---|---|---|
| N-B0-1 | **B0** | §3/§3.3: basta con validar que `doc_id` no se repita. | El manifiesto es editable y `_slug_seg` inserta `doc_id` directamente en una ruta (`spec:80-81`). No se exige formato canónico ni path-safety. `destino_seguro` solo valida `carpeta_bundle` (`sala_maquina.py:582`), no el nombre calculado dentro de `materializar`. Ejecuté en un temporal Windows un `Path.replace` con un `doc_id` que contenía separadores y `..`: el PDF salió de `02_Documentos/.../bundle` y apareció en un `00_Input` sintético. Salida: `doc_id_escape True b'probe'`. | Validar antes de cualquier I/O un formato canónico cerrado —no solo unicidad— y rechazar `/`, `\`, `.`, espacios y formas no canónicas. Validar también cada destino final contra `carpeta_bundle` y `case_dir`. Añadir test real de traversal en Windows. |
| N-B0-2 | **B0** | §3: el `doc_id` "se acuña una sola vez", "nunca se reasigna" y nunca se reutiliza uno retirado. | No existe una memoria autoritativa separada del manifiesto editable. Dos fallos: (1) el letrado puede intercambiar `d01` y `d02`; ambos siguen siendo únicos y `validar_manifiesto` no puede saber que fueron reasignados; el siguiente apply intercambia las identidades semánticas. (2) si se retira el ID máximo, el manifiesto siguiente ya no lo conserva. Aplicando literalmente "máximo existente + 1": se retiró `d02` y la corrida posterior volvió a acuñar `d02`. Salida del probe: `retired ['d02']` y luego nuevo `doc_id='d02'`. | Persistir un high-water mark monotónico (`next_doc_id`) y tombstones de retirados. La correspondencia `pp↔doc_id` inmutable necesita un ledger no editable o una parte protegida del manifiesto contra la que validar cambios. Un intercambio manual de IDs debe abortar. |
| N-B0-3 | **B0** | §5: archivar antes y comprobar `fila.sha256 == PDF.sha256` convierte B0-1 en detectado. | Escenario ejecutado en temporal: la ruta de split escribió PDF, MD y raw nuevos y después falló —equivalente a que `append_event` de `sala_maquina.py:602` falle tras escribirlos—. `ejecutar:732` devolvió una sola fila del bundle físico: `('bundle__aaaaaaaa','error','empty', parent_slug='')`. Los tres artefactos existían. Bajo `--force`, `previa=[]`; el guard que recorre "cada fila de segmento" no ve ninguna y no salta. Además, si el archivo previo falla después de mover solo uno o dos de PDF/MD/raw, el caso queda partido antes de escribir la generación nueva. | El archivo de la generación necesita operación transaccional/journal y rollback. El fallo del evento no debe descartar las filas ya construidas. El guard debe ser bidireccional —fila→fichero y fichero de segmento→fila—, verificar las tres representaciones y abortar con exit no cero, no limitarse a avisar. |
| N-B0-4 | **B0** | §6.4: con el lock adquirido "no hay copia operativa divergente" y el merge deja de plantearse. | `ESTADO_REPO_PRESTADO` significa precisamente "checked out, copia de trabajo local" (`config.py:357-359`); no es un mutex genérico. La suite ejecutó como `xfail` el defecto `test_defecto_doble_titular`: dos checkouts pueden terminar ambos con exit 0. Otro `xfail` demuestra que un rollback puede cancelar el lock ajeno. AST sobre `cmd_checkin` dio `verificar_nonce=0`; solo consulta `estado_de_fm` al final, después del merge. Con una copia local antigua que contiene un slug viejo nuevo respecto de su baseline y el canon ya migrado, `plan_merge` produjo simultáneamente `PRESERVE_DRIVE` para el nuevo y `COPY_LOCAL` para el slug viejo: lo resucita. | Crear un lease específico de migración o reforzar el protocolo: nonce/propietario verificados al principio y antes de cada mutación/checkin, baseline vinculado al nonce y rechazo de copias stale. Mientras los `xfail` de doble titular estén vivos, la migración no puede depender de ese lock como exclusión. |
| N-A-1 | **A** | §3.3: dejar pasar `ManifestValidationError` hace que la CLI aborte "antes de materializar nada". | La validación sigue dentro de `_split_o_md` (`sala_maquina.py:586`), que se invoca documento a documento desde el bucle de `ejecutar:684`. `apply` solo guarda cobertura, estado y evento después de que `ejecutar` retorne (`scripts/sala_maquina.py:299-327`). Si el segundo bundle es inválido, el primero puede haber escrito todo; la excepción impide que sus filas se persistan. | Preflight de todos los manifiestos y reconciliaciones antes de procesar el primer documento. Alternativamente, capturar un resultado parcial y persistirlo antes de devolver exit no cero, pero el preflight es más limpio. |
| N-A-2 | **A** | §3: cambiar `TIPO` es "inocuo", un renombrado detectable. | El tipo sigue formando parte del slug. Al cambiar `DOC_A→DOC_B`, el destino nuevo no existe, por lo que la regla "si el destino existe, archivar" de §5 no encuentra el nombre anterior. La fusión vigente indexa por `(rel_path, slug)` (`sala_maquina.py:323-355`) y conserva ambos. Probe ejecutado: `tipo_rename_coverage_rows 2 ['parent__d01_DOC_A','parent__d01_DOC_B']`. El `doc_id` tampoco aparece como campo estructurado de `DocCobertura`. | Añadir `doc_id` a `DocLogico` y `DocCobertura`; fusionar segmentos por `(rel_path, doc_id)`; detectar el cambio del slug derivado del tipo y renombrar/archivar PDF, MD, raw e índices como grupo. O retirar `TIPO` del nombre estable. |
| N-A-3 | **A** | §3.2: el `doc_id` se conserva a través de regeneraciones mediante igualdad exacta de `pp`. | Es una regla conservadora, pero no cumple la promesa general. Probe: `d01:1-3,d02:5-7` → OCR con rangos `2-4,6-8` acuña `d03,d04` y retira ambos; si los rangos originales reaparecen, acuña `d05,d06`. El mismo documento lógico recibe tres identidades sucesivas. En un split real `1-6→1-3+4-6`, ninguno conserva el `pp` original; el test 4 de §9 presupone que uno lo conserva, por lo que no prueba ese caso. | Elegir explícitamente: o aceptar que un cambio de límites crea nuevas identidades y rebajar la promesa de persistencia, o detener `--force` ante split/merge sin coincidencia exacta y pedir una reconciliación humana. No recomiendo emparejamiento difuso automático. |
| N-A-4 | **A** | §6.3: el journal exterior permite reanudar sin adivinar. | "Fuera del caso, junto al informe" (`spec:209`) no identifica una ruta ni cómo la siguiente ejecución lo descubre. Tampoco se define escritura atómica, run-id, retención o qué hacer si el journal se pierde después de mover artefactos. "Fallar cerrado" puede dejar permanentemente el caso a medias y sin procedimiento de rollback o adopción. El patrón citado, `migrar_nombres_informe`, no ofrece journal alguno. | Ruta determinista durable, journal atómico, `case_id+run_id`, versión de esquema y comando explícito de `resume/rollback/adopt`. Si falta el journal pero existen marcas de migración parcial, no debe empezar una corrida nueva. |
| N-A-5 | **A** | §8: el retrofit por orden de `seg` es suficiente y re-ejecutable. | El orden numérico puede ser reproducible, pero no se definen manifiestos mixtos —unas entradas con `doc_id` y otras sin él— ni la precondición que une el superviviente elegido por cobertura con el `pp` del manifiesto. Si un `--force` histórico renumeró antes del retrofit, el `segNN` del artefacto superviviente puede no representar el `pp` actual. La migración podría congelar la identidad equivocada. | Validar primero tipos/unicidad/orden de `seg`; exigir `cobertura.paginas == manifiesto.pp` para el superviviente; abortar cualquier grupo que no case; definir recuperación de JSON inválido o manifiesto mixto; probar doble retrofit y retrofit posterior a renumeración histórica. |
| N-M-1 | **M** | §9: los tests 4, 5 y 7 matan las implementaciones defectuosas. | Test 4 llama "partido en dos" a un caso donde una parte conserva exactamente el rango: no cubre `1-6→1-3+4-6`. Test 5 puede pasar si la implementación acuña IDs nuevos siempre: evita sobrescribir, pero no conserva identidad. Test 7 puede pasar comprobando solo que exista algún fichero archivado y aparezca un aviso, aunque falten MD/raw o la cobertura no tenga filas de segmento. | Asertar mapas exactos `pp→doc_id`, conjunto de retirados, high-water, bytes de las tres representaciones, cobertura antes/después y exit code. Incluir una mutación que "acuña siempre" y demostrar que el test 5 la mata. |
| N-M-2 | **M** | Alcance: una sola pieza sigue siendo manejable. | La rev. 2 reúne dos superficies con fallos y despliegues distintos: cambio permanente del motor/esquema y migración única de datos reales bajo protocolo de préstamo. El contrato pasó de una función y un script a identidad, reconciliación, preflight, archivo, guard, journal, lock y retrofit. | Partir en dos piezas: **A)** motor y esquema (`doc_id`, ledger, reconciliación, validación, archivo y cobertura); **B)** retrofit/saneamiento de los cinco grupos, journal y protocolo. La pieza B consume helpers cerrados y probados de A. No activar nombres estables sobre casos legacy hasta completar el retrofit. |

## Verificado ejecutando

### Objeto exacto

```text
C:\Users\tnm33\Dev\FeesDefender\.claude\worktrees\musing-engelbart-162f92
branch: claude/proximo-paso-464808
HEAD:   05d985f129c84c45935ab15df4c8f6f0c4e1752c
status: limpio
```

El worktree siguió limpio después de las pruebas.

### Suite completa

```text
2612 passed, 77 skipped, 7 xfailed in 190.67s
PYTEST_EXIT=0
```

Entre los `xfail` relevantes para esta spec: dos titulares simultáneos del lock; rollback que cancela
un lock ajeno; checkin reentrante que duplica evento; log canónico que no conserva bytes append-only.

E2E lentos del split: `3 passed in 6.48s`, `PYTEST_SLOW_EXIT=0`.

### Probes dirigidos

- Retiro del máximo y corrida posterior: `d02` se retiró y volvió a acuñarse.
- Jitter exacto de páginas: `d01,d02 → d03,d04 → d05,d06`.
- Checkin stale: `PRESERVE_DRIVE` para el slug migrado y `COPY_LOCAL` para el slug viejo.
- AST de `cmd_checkin`: cero llamadas a `verificar_nonce`.
- `doc_id` con traversal: `Path.replace` escribió en un `00_Input` sintético fuera del bundle.
- Cambio de tipo: la fusión vigente conservó dos filas del mismo `doc_id`.
- Fallo después de escribir PDF/MD/raw: `ejecutar` devolvió solo una fila de error del bundle, sin
  fila de segmento que el guard pudiera comprobar.

Todos los probes escribieron únicamente en temporales, nunca en el repositorio ni en Drive.

## Verificado leyendo

Spec rev. 2 y handoff anterior completos, y el fuente vigente del commit: `core/split_documental.py`,
`core/sala_maquina.py`, `scripts/sala_maquina.py`, `core/repository_checkout.py`,
`scripts/repository_cli.py`, `core/case_manager.py`, `core/config.py`, `core/intake_log.py`,
`core/migrar_nombres_informe.py`, y los tests del split, cobertura, checkout/checkin y defectos
`xfail`. No se revisó solo el diff.

## Lo que intenté refutar y NO pude

1. **La sustitución del ordinal por un identificador persistente es la dirección correcta.**
2. **La igualdad exacta de `pp` evita falsas asociaciones.** Produce falsos negativos, pero no
   encontré un desempate automático por solapamiento que fuera seguro.
3. **El contrato 0/1/N de cobertura es suficiente y fail-closed.**
4. **Rechazar la migración legacy sin JSON es correcto.**
5. **Conservar los slugs históricos del log es correcto.** No hay consumidores productivos que los
   resuelvan contra la cobertura actual.
6. **Los hashes del journal no se vuelven ambiguos porque dos representaciones tengan bytes iguales.**
7. **Un checkout verdaderamente posterior a una migración terminada es seguro.** El problema es la
   copia stale anterior.
8. **Las cifras de §2 y la extensión `.txt` ya están corregidas.**

## NO VERIFICADO

- La implementación de `doc_id`, reconciliación, guard, journal y migrador: todavía no existe.
- Dry-run o aplicación real de la migración.
- Una carrera real entre migración y checkin sobre Drive, y el comportamiento de `rclone` en ella:
  los hallazgos de lock se apoyan en código, probes puros y `xfail` ejecutados.
- Recuperación tras pérdida física del journal.
- Consumidores externos al repositorio que pudieran interpretar los slugs históricos del log.
- El censo de `G:\`, por instrucción expresa de no repetirlo sin sospecha nueva.
