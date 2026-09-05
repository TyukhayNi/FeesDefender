---
tipo: revision-adversarial
objeto: "diff 3fedf54..0b0298b — implementación de la rev. 2 de «Ficheros de protocolo: por dónde están, no por cómo se llaman» (MEJORAS #149, PR #290)"
objeto_rev: "2"
commit: "0b0298b"
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: h3wq
sha256_informe: 0d8e756fa020453bc6bd30fd24f8a30e75e4e257313c753d26935f3b058daeaa
adjudicado_en: docs/superpowers/specs/2026-09-05-ficheros-de-protocolo-por-ubicacion-design.md §9
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R2 sobre el DIFF.** Segunda y última ronda de la pieza (radio
> de daño: decide qué es prueba documental y toca el único `unlink()` del intake). La R1, sobre
> el diseño, la hizo un revisor sustituto (Codex sin cupo aquel rato); esta la hizo **Codex**
> (`gpt-6-astra`, ~184.000 tokens, 19:36–19:4x), así que la independencia vuelve a ser plena.
>
> El §1 conserva la voz del revisor sin una coma cambiada; el §2 es la evidencia que verifiqué
> por mi cuenta al adjudicar. **La adjudicación NO está aquí:** va embebida en el §9 del diseño,
> que además pasa a **rev. 3** porque tres hallazgos cambian el diseño y no solo el código.
>
> **Objeto:** copias externas de `3fedf54` (base) y `0b0298b` (head) con `git archive`, más el
> parche. El revisor declaró que no acredita la genealogía y verificó contenido y hashes al
> abrir y al cerrar; coinciden con los que calculé yo.
>
> **El diff REMEDIADO no se ha vuelto a revisar**, y se dice: la regla da dos rondas para esta
> clase de pieza y prohíbe la tercera sin autorización expresa. Lo que sí se hizo (§2) es
> reproducir los contraejemplos concretos del revisor contra el código remediado.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:h3wq -->

HIGIENE CONFORME: al abrir `C:\t\rev149_193504\rev` contenía exclusivamente `MANDATO.md`; no había otros ficheros que excluir de lectura.

# R2 adversarial del diff de MEJORAS #149

## 1. Custodia al abrir

| Fuente | SHA-256 al abrir |
|---|---|
| `../head/core/intake_control.py` | `7fcd465232c4d775d2d6195ad0bb5a4166f8e27cc829715cf3f55c452fb9bebd` |
| `../head/scripts/migrar_layout_intake.py` | `731755f9e7fd1d710818a51c4cf0fcef02992ba1d10488073a5f2f1e5237081e` |

Los nombres `3fedf54` y `0b0298b` proceden del mandato. Son archivos exportados sin `.git`: **no acredito genealogía**. Comparé los bytes de ambos árboles: cambian los 18 ficheros enumerados en `content_diff_files.json`; el parche suministrado tiene 1.395 líneas. La fuente de esta revisión es `head/`. No escribí en `base/` ni en `head/`; todas las ejecuciones se hicieron en `work/` y `work_base/`, dentro del directorio del revisor.

## 2. Resumen en tres líneas

Los seis mutantes exigidos mueren; las comprobaciones normales del plan, rollback y relectura funcionan en los escenarios probados.
Persisten una carrera que permite borrar estado divergente, una sobrescritura documental previa al diff y exclusiones/entradas incorrectas en el inventario y el validador CRM.
Recomiendo NO-SHIP; distingo expresamente regresiones, defectos preexistentes y garantías no acreditadas, cuya adjudicación corresponde a Claude contra la fuente.

## 3. Hallazgos reproducidos

Las sondas afirman **el comportamiento observado**, no que ese comportamiento sea correcto. Sus verdes significan que reprodujeron el defecto. Las rutas y líneas siguientes corresponden a `head/`.

### H-01 — ALTO — La raíz puede cambiar tras el último hash y aun así se borra el legacy

**Fuente:** `scripts/migrar_layout_intake.py:200–205`.

**Reproducción:** `work/tests/test_review_r2.py::test_carrera_entre_hash_y_unlink`, resultado en `probes3.log`. Se crean raíz y legacy con `{"old":1}` y un correo documental. Se envuelve `compute_sha256`: ejecuta el hash real; en la segunda lectura de la raíz —la de fase 2—, una vez terminada esa lectura y antes de devolver el digest, publica `{"new":2}` en la raíz. Representa un intercalado de otro escritor después de cerrarse el descriptor leído; no se falsea el digest ni se modifica el código de producción.

**Esperado:** si al borrar la raíz ya difiere, conservar el legacy y reportarlo. **Observado:** raíz `b'{"new":2}'`, legacy inexistente, `duplicados_borrados=['03_Email/_exported_ids.json']`, `no_borrados=[]`. Los bytes antiguos desaparecen y el informe afirma que eran un duplicado conservado.

La relectura añadida existe y mata el mutante (d), pero leer, comparar y eliminar son operaciones separadas. Reduce la ventana; no garantiza P3 frente a un escritor concurrente. No afirmo que haya ocurrido en un expediente real. La reproducción determina el intercalado, no su frecuencia. Es una garantía incompleta del cambio, no una regresión introducida respecto al borrado incondicional anterior. El §6 excluye concurrencia **más allá de no borrar**; este caso afecta precisamente a no borrar.

### H-02 — ALTO — Migrar un `_manifiesto.yaml` documental lo sobrescribe con el albarán del lote

**Fuente:** `scripts/migrar_layout_intake.py:167–169,210–216`; escritor en `core/intake_lotes.py:146–151`.

**Reproducción:** `test_migracion_manifiesto_documental` y la sonda común `test_review_delta.py::test_manifiesto_sobrescrito`. Único fichero en el cajón: `04_Manual/_manifiesto.yaml`, bytes `prueba del cliente`/`prueba original`. En head, el clasificador lo declara documental. La fase 1 lo mueve a `<fecha>_manual_01/_manifiesto.yaml`. Después, `items_desde_disco` lo excluye por su nueva ubicación y `escribir_manifiesto` abre esa misma ruta para escribir el protocolo.

**Esperado:** conservar los bytes del documento o abortar por colisión antes de mover. **Observado:** contenido sustituido por YAML administrativo con `items: []`; no queda la prueba original. No hace falta concurrencia ni un fallo de disco.

**Preexistente, comprobado ejecutando ambos árboles:** `delta_head3.log` y `delta_base3.log` imprimen `MANIFIESTO SOBRESCRITO`. No lo atribuyo como regresión del diff. Lo incluyo porque la migración dentro del radio de revisión sigue destruyendo un homónimo que el contrato nuevo declara documento: revisar solo `unlink()` deja esta pérdida fuera de la garantía anunciada.

### H-03 — MEDIO — El escritor real reutiliza carpetas Windows con otra caja y el inventario incluye su protocolo

**Fuente:** `core/intake_control.py:108–112`; consumidores `core/sala_maquina.py:1229–1230` y `core/inventory.py:93`.

**Reproducción Windows real:** `test_directorio_windows_real`. Se precrea `00_Input/01_drive ev/` y se llama a `intake_drive.pull_drive_ev`; solo se sustituye rclone por un resultado de éxito sin red. El código real crea/escribe mediante `01_Drive EV/.pulled`, que Windows resuelve a la carpeta ya existente. El recorrido devuelve la capitalización almacenada: `01_drive ev/.pulled`.

**Esperado:** el marcador que acaba de escribir el repo queda fuera. **Observado:** `sala_maquina.inventariar` devuelve exactamente `['01_drive ev/.pulled']`; el propio pull, cuya ruta tiene la caja canónica, informa `files_after=0`. Dos consumidores discrepan sobre el mismo fichero físico.

Es una regresión del filtro por basename y una refutación de P4. La comparación sensible a caja del directorio sigue literalmente el diseño y tiene incluso un test que exige `False`; el defecto está en su premisa sobre Windows, no en que falte esa condición. No propongo quitar la comprobación de directorio: hay que representar correctamente su identidad física.

### H-04 — ALTO — Las cinco excepciones CRM ocultan adjuntos documentales y convierten incertidumbre en ausencia

**Fuente:** `core/crm_ficha_validacion.py:43–51,320–335`; efecto en `corpus_legible`, líneas 303–304.

**Reproducción:** `test_crm_cinco_excepciones_son_documentos`. Bajo `<lote>/adjuntos/` se depositan `_cobertura.json`, `_cobertura.md`, `_sala_maquina_state.json`, `_registro.json` y `_tiempos.jsonl`. Se ejecutan `inventariar → plan → ejecutar → cobertura_a_dicts` de la sala, y después `corpus_legible` y `validar` para un NIF no encontrado. No se inventan las rutas de las filas: las produce la sala real.

**Esperado:** esos homónimos son documentos; los no legibles deben figurar como tales y dar `SIN_COMPROBAR`. **Observado:** las cinco filas existen, todas desaparecen al pasar por el validador, `(legibles, ilegibles) == ((), ())`, y el resultado es `NO_ENCONTRADO`.

**Defecto preexistente conservado deliberadamente por el diff.** La excepción «fuera de Input» se aplica por basename sin comprobar que la fila esté fuera de Input. El hogar del protocolo administrativo no determina el hogar de un adjunto homónimo. Se reproduce exactamente el tipo de pérdida semántica de R1/H-08, ahora para los cinco nombres retenidos. La afirmación de que estas excepciones solo reconocen cosas externas es falsa.

### H-05 — MEDIO — El censo de escritores deja entrar un temporal real de descarga

**Fuente:** omisión en `core/intake_control.py:44–69` y alcance afirmado por `tests/test_intake_control_por_ubicacion.py:246–306`; escritor real en `core/sync_sudespacho.py:1099–1124`.

**Reproducción:** `test_sync_temporal_real`. Se ejecuta `sync_sudespacho.pull_expediente` con un cliente falso que devuelve un documento REST y escribe bytes parciales en el destino que el motor le pasa. Se inyecta una interrupción después de escribir el temporal y antes de renombrarlo. Resultado literal de `inventariar`: `['sudespacho_648/civil/sudespacho_17.tmp']`.

**Esperado según P4:** un temporal generado por el repo no pasa a prueba documental. **Observado:** se inventaría y hashea el parcial. El escritor decide ese nombre, no el supuesto cliente documental.

**Preexistente; el diff no lo remedia.** El diseño deja `sync*` sin cambios, pero P4/T7 afirman una cobertura universal que no ofrecen. El test T7 escribe a mano los marcadores de Drive/sync; no ejecuta todos esos escritores. El fallo inyectado del test nuevo se limita a tres escritores atómicos de raíz y no cubre esta descarga. La solución no es excluir cualquier `.tmp` aportado por un cliente: debe estrecharse la garantía o definir la ubicación/vida del temporal propio.

### H-06 — MEDIO — P5 omite cambios de expectativas y cambios observables en los listados

**Fuente:** `core/intake_manual.py:304–307,341–342`; `tests/test_crm_ficha_validacion_r1.py:127–142`; lista de expectativas del §5 del diseño.

**Reproducción A:** la misma `test_review_delta.py::test_matrix` en base y head. `list_crm_branch_files(case_id,'civil/')` excluye en base seis nombres del registro antiguo y los incluye en head: `.pulled`, `.synced`, `_inventory.json`, `_exported_ids.json`, `_resolved_links.json`, `_apertura_v1.json`. Sucede también con subcarpetas y barras finales. El filtro anterior por basename **sí tenía efecto** a profundidad tres. La lista del §5 no declara el cambio de esta API. Además, `list_files` pasa a devolver `04_Manual/_manifiesto.yaml`, que antes excluía; el §5 anuncia tres nombres en ese cajón, pero omite este cambio específico del manifiesto legacy.

**Reproducción B:** copié el test CRM original de base como `work/tests/test_review_original_crm.py`, sin alterar producción, y lo ejecuté sobre head: **2 fallos, 40 aprobados**. Fallan exactamente los parámetros `sub/_caso.md` y `sub\\_ficha_crm.yaml` de `test_el_control_se_reconoce_con_ruta_y_caja`. En head se sustituyeron por expectativas opuestas; el bloque cerrado «Tests hoy verdes que cambian de expectativa» del §5 no incluye ese test CRM.

**Esperado:** que el inventario de cambios anunciados sea completo. **Observado:** no lo es. El sentido del cambio CRM sí está anunciado por T13 y §3.3; no lo califico de error funcional por admitir esos adjuntos. El hallazgo es la falsedad del «exactamente» de P5 y la cobertura incompleta de cambios que el mandato exige declarar. Véase la matriz exhaustiva **del fixture** en `delta_results.json`.

### H-07 — BAJO — Docstrings mantienen contratos que el código ya no cumple

**Fuente:** `core/intake_manual.py:288,314–316`; `scripts/migrar_layout_intake.py:25–29`.

**Reproducción:** las sondas de listados y matriz devuelven `.pulled` y `_inventory.json` de `04_Manual`, aunque el docstring de `list_files` afirma expresamente que los excluye. `list_crm_branch_files` sigue diciendo que excluye control interno, aunque su filtro actual no excluye los seis antiguos basenames en una rama normal.

Además, el docstring de migración afirma que la identidad por sha256 se comprueba «TRES veces». Con el espía de hashes de `test_carrera_entre_hash_y_unlink` y la lectura del bucle de fase 1 se comprueba que hay dos lecturas de hash de la raíz: plan y fase 2. La fase 1 comprueba existencia para la decisión `mover`, no identidad por hash. Esa comprobación de existencia es la que el diseño pide y pasa su test; el error es describirla como otra comparación de hash.

**Esperado:** documentación que describa la clasificación y comprobaciones ejecutadas. **Observado:** exclusiones que dejaron de existir y una tercera comprobación de hash que no existe. Se trata de documentación engañosa, no de exigir aquí una tercera lectura por sí misma.

## 4. Contraste de P1–P5

| Proposición | Resultado | Evidencia |
|---|---|---|
| P1: protocolo por ubicación real | **REFUTADA como garantía sobre ficheros reales** | La implementación sigue el algoritmo literal de la rev. 2 y pasan sus casos normales y la matriz de normalización. H-03 demuestra que la caja textual del directorio no identifica de forma consistente la ubicación Windows utilizada por el escritor. H-02 muestra además que una migración puede convertir ubicación documental en ubicación administrativa y destruir el contenido. |
| P2: nueve consumidores conectados por ruta; sin alias clasificadores | **CONFIRMADA en el cableado inspeccionado** | Se abrieron los nueve sitios; tabla siguiente. Pasan T14 por AST, retirada de alias, registro derivado y mutantes (e)/(f). Esto no acredita la corrección universal de las rutas sintetizadas ni de las cinco excepciones por nombre de CRM: véanse H-03/H-04 y la precondición de email externo. |
| P3: no borrar estado distinto/no conservado | **REFUTADA en su garantía concurrente** | T4/T5/T5b/T5c/T6 y sondas de desaparición de raíz, rollback y directorio homónimo pasan. La relectura existe; H-01 prueba el intervalo posterior a ella. |
| P4: ningún producto del repo entra, incluidos temporales | **REFUTADA** | H-03 y H-05. Además, el propio §3.5 exceptúa índices legacy `INDICE.md`/`CRONOLOGIA.md` y `_descarga_bruta.bin`; por tanto el enunciado absoluto tampoco coincide con el alcance del diseño. No cuento esas excepciones anunciadas como nuevos hallazgos. |
| P5: exactamente los cambios anunciados y ningún otro resultado cambia | **REFUTADA en la lista declarada; resto global SIN VERIFICAR** | H-06, con test antiguo ejecutado y matriz base/head. En los 659 tests de head de las dos selecciones, los 119 fallos tienen los mismos identificadores que en base: no encontré otro test inalterado que cambiara de resultado dentro de esa selección. No ejecuté toda la suite. |

### Auditoría de rutas de los consumidores

| Consumidor y sitio de head | Ruta que recibe el clasificador y comprobación |
|---|---|
| `inventory.scan`, `core/inventory.py:93` | `path.relative_to(input_dir).as_posix()`, relativo real al Input recorrido. El YAML documental puede aparecer en `skipped`, no necesariamente en `files`; se comprobaron ambas listas. |
| `intake_manual.list_files`, línea 342 | `d.name/p.name`: correcto para las bases de primer nivel que selecciona. Excluye el manifiesto del lote válido; lista ahora el homónimo legacy. |
| `intake_manual.list_crm_branch_files`, línea 307 | `05_CRM/branch.as_posix()/p.name`. Se probaron `civil`, `civil/`, `civil/sub/`, `civil\\sub\\`: las rutas mantienen el anclaje correcto. No es recursivo. La matriz también ejerció `civil/sub/../`: el clasificador falla hacia documento por `..`. |
| `intake_drive._count_files`, línea 867 | `directory.name/p.name`, no recursivo. Dos ficheros `.pulled` y `_inventory.json` dan 1 en `01_Drive EV`, 2 en `Otro`. El escritor ordinario fija el nombre canónico; un directorio arbitrario no se interpreta como E&V. H-03 cubre la discrepancia física por caja. |
| `intake_lotes.items_desde_disco`, línea 203 | `lote_dir.name/rel`. En `_pendiente_checkin/email/00_Input/<lote>` se excluye el manifiesto raíz y se conserva `x/_manifiesto.yaml`: funciona el nombre lógico preservado. En `CarpetaRara` ambos manifiestos se incluyen; la API no valida `PATRON_LOTE` y su escritor acepta esa ruta. No encontré un llamador ordinario que reserve lotes con ese nombre inválido. |
| `email_export.export_label`, líneas 1079–1097 | Solo entra en esta rama con `case_id` y nombre que case el patrón. Construye `dest.name/rel`. La sonda diferencial con `_inventory.json` como único contenido pasa de `OSError` en el intento de retirar el lote de base a conservarlo/escribir albarán en head. Se probaron también los destinos externos descritos debajo. |
| `sala_maquina`, líneas 1186–1187,1229–1230 | `rel` se calcula **antes** de filtrar y usa `relative_to(root).as_posix()`. Para `00_Input/90_Notas personales/_caso.md`, `inventariar` lo incluye y `plan` lo excluye, como documenta el código; el `90_Notas personales` hermano de Input no entra en ese recorrido. |
| `abrir_caso.hash_tree_local`, líneas 89–95; `etapa_drive`, 407–410 | Hash: `prefijo/rel`; llamador E&V utiliza `01_Drive EV`. Recuento: `res.target_dir.name/rel`. Ambos son recursivos. En la sonda con `.pulled`, `_inventory.json`, `_exported_ids.json`, `doc.pdf`, la etapa informa 1 documento en base y 3 en head; `.pulled` sigue fuera. |
| Migración, `scripts/migrar_layout_intake.py:85,106–107,148` | Plan/clasificación: `mov.cajon/hijo.name`; mapping: claves ya relativas a Input. `03_Email/hilo/_exported_ids.json` se mueve y remapea. Un **directorio** `03_Email/_exported_ids.json/` con `adjunto.pdf` se mueve como directorio y el M9 apunta al adjunto existente: no se hashea ni borra como estado de canal. |
| `crm_ficha_validacion`, líneas 332–335 | Normaliza separadores y delega la ruta; luego vuelve a basename para cinco excepciones. H-04. Se inspeccionó la producción de `DocCobertura` en la sala: usa `d.rel_path`, incluido el split. La reconstrucción legacy toma `source_path` del frontmatter sin validar su base; no hay evidencia aquí de que los escritores actuales produzcan sistemáticamente un prefijo `00_Input/` o una ruta absoluta en esas filas. |

**Email fuera de caso, reproducido, precondición incumplida:** sin `case_id`, un destino externo genera `doc.eml`, `INDICE.md`, `CRONOLOGIA.md`; no pasa por la rama de lotes. Con `case_id` y un destino externo llamado como lote, escribe el manifiesto y registra `2026-09-05_email_01/doc.eml` en el M9 del caso, aunque esa ruta no existe en su Input; `report.errors == []`. El docstring exige que el destino esté bajo el Input del caso, pero no lo valida. La traza usa `dest.parent` como raíz (`email_export.py:1247`). Es comportamiento previo al diff en ese código, y una limitación real de tomar el nombre del destino como ruta lógica; no lo presento como nueva regresión del filtro.

### Normalización e importaciones

Se ejecutaron `\\`, `./`, separadores duplicados y `.` intermedio: normalizan correctamente en los casos observados. Vacía, absoluta POSIX, unidad Windows, UNC y componente `..` devuelven documento. `a..b` no se confunde con `..`: un fichero con ese nombre bajo `_organizado` sigue siendo protocolo. `_CASO.MD` se excluye; la caja del directorio produce H-03. `_caso.md ` devuelve documento; no afirmo que Windows conserve ese espacio como nombre físico independiente. NFC/NFD en directorios documentales permanecen documentales; el registro es ASCII y no se demostró una colisión de normalización Unicode. Una entrada textual de 10.000 caracteres termina sin error; no se creó un fichero de esa longitud.

Pasar `Path('_caso.md')` directamente da `TypeError`: la API declara `str`. Los sitios auditados pasan strings mediante `as_posix` o interpolación; no encontré un consumidor de los nueve que le pase un `Path` desnudo o anteponga `00_Input/` en el caso ordinario.

Se ejecutó `importlib.reload(config)` tres veces conservando `intake_lotes.PATRON_LOTE is intake_control.PATRON_LOTE`; también pasan las fixtures de los tests nuevos. `intake_control` solo importa `re`: no se reprodujo ciclo de importación. La selección de 68 tests pasa en el orden de módulos normal y en el inverso.

### Cambios observables base → head

El fixture común contiene 15 nombres en nueve ubicaciones; `delta_results.json` enumera cada entrada y salida. Estos números describen ese fixture, no un censo de expedientes reales. «Entra» en inventory incluye su lista `skipped`.

| Consumidor | Cambio medido | Contraste con §5 |
|---|---|---|
| Inventory | 49 rutas entran y 15 salen | Entran antiguos basenames fuera de su hogar y `_caso_anexo.pdf`; salen protocolo de raíz, manifiesto de lote y contenido de `_organizado`. Las familias están explicadas por T1/T2/T9/T10/T12 y §3.3; §5 no enumera todos los ejemplos ni `_intake_log.jsonl` como nueva exclusión de inventory. |
| Manual | 13 entran, ninguna sale | Se anuncian `.pulled`, `.synced`, `_inventory.json` legacy y homónimos de lote; falta declarar el efecto específico sobre `04_Manual/_manifiesto.yaml` (H-06). |
| Rama CRM | 6 entran, ninguna sale | Cambio no consignado como tal en §5; contradice que el filtro anterior fuese un no-op por profundidad. |
| Drive, primer nivel | 9 → 14 ficheros | Solo `.pulled` queda excluido de los quince. T9 menciona `.synced` y `_inventory.json`; es la extensión de la regla a los otros estados administrativos homónimos. |
| Albarán de lote | 13 rutas entran, ninguna sale | Se mantienen fuera solo manifiesto raíz; entran seis basenames antiguos en raíz/anidado y el manifiesto anidado. Familias previstas por T1/T2/T9 y test anunciado. |
| Email | Único `_inventory.json`: de error al retirar el lote a contenido conservado con manifiesto | Consecuencia observable de aplicar el mismo contrato de lote; no equivale a una ejecución completa de Gmail. |
| Sala | 55 entran, 13 salen | Entran estados/prefijos fuera de su ubicación; salen `_caso.md`, protocolo añadido en raíz, manifiesto de lote y derivados. Cubierto por familias T1/T3/T9/T10/T12; H-03/H-05 muestran dónde la generalización falla. |
| Hash E&V / recuento de etapa | Hash: 11 entran, 9 salen; etapa reducida: 1 → 3 | Homónimos entran, derivados `_organizado` salen. §5 anuncia cambio del test de hash, aunque el nuevo docstring simplifica que «solo» sale `.pulled`: también sale el directorio derivado registrado. |
| Migración | El homónimo anidado entra en mapping; raíz divergente aborta; duplicado se borra condicionado | T4–T6. Sigue la sobrescritura H-02; H-01 delimita la garantía concurrente. |
| Validador CRM | Los dos parámetros antiguos de homónimos pasan de control a documento | T13 anuncia el objetivo, pero el test antiguo alterado falta en la lista cerrada de expectativas; las cinco excepciones mantienen H-04. |

## 5. Ejecuciones y mutantes

Intérprete: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`. Ninguna llamada real a Gmail, rclone, CRM ni a expedientes del despacho. Los escritores se ejercitaron con clientes o subprocess falsos cuando requerían servicios externos.

El primer comando se lanzó con `work/` como `workdir` de la herramienta: **205 errores de setup**, `PermissionError` creando `work/tmp`, antes de ejercer el código. Una sonda mínima reprodujo el fallo de creación al arrancar así. Arrancando desde `rev/` y haciendo `Set-Location ./work` dentro de PowerShell se pudo escribir en la misma copia. No se cambió ACL ni se elevó permiso. `pytest_target.log` conserva esa incidencia; no cuenta como refutación de código.

Comando válido principal, precedido de `Set-Location ./work`:

```powershell
& C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest -o addopts= -q -p no:randomly --basetemp=./tmp2 tests/test_intake_control_por_ubicacion.py tests/test_migrar_layout.py tests/test_intake_lotes.py tests/test_intake_manual.py tests/test_abrir_caso_cli.py tests/test_apertura_v1_control_files.py tests/test_crm_ficha_validacion_r1.py tests/test_inventory.py
```

- Head: **178 passed, 27 failed**, 10,72 s, `pytest_target2.log`.
- Base, mismos siete módulos existentes, sin el nuevo `test_intake_control_por_ubicacion.py`, temporal `./tmp_base`: **120 passed, 27 failed**, 7,83 s, `pytest_base.log`.
- Los 27 fallos de CLI aparecen en ambos árboles por `WORKSPACE_UNDER_CATALOG_ROOT`: la fixture coloca el registro de workspace bajo el temporal dentro del propio repo, que el guard rechaza. No se eliminaron guards para obtener un verde.

Ampliación, aplicada a cada copia con temporal propio:

```powershell
$reviewTests = Get-ChildItem ./tests -File | Where-Object {$_.Name -match '^test_(sala_maquina|email_export|intake_drive|sync_sudespacho|whatsapp_intake|intake_traza|intake_manifest)' } | ForEach-Object { 'tests/' + $_.Name }
& C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest -o addopts= -q -p no:randomly --basetemp=./tmp_extended @reviewTests
```

Head: **362 passed, 92 failed**, 25,55 s. Base: **362 passed, 92 failed**, 21,75 s (`./tmp_extended_base`). Comparación programática de los identificadores `FAILED`: ningún fallo exclusivo de head y ninguno exclusivo de base. Logs: `pytest_extended.log`, `pytest_extended_base.log`. No equivale a confirmar que esos 92 escenarios funcionen: fallan en este entorno en ambos árboles.

**Mutación ejecutada:** `python ./run_mutants.py`, que restaura cada fichero en `finally`, ejecuta subprocess independientes con `-B -m pytest -o addopts= -q -p no:randomly --basetemp=./tmp_mut_<nombre> tests/test_intake_control_por_ubicacion.py tests/test_migrar_layout.py`, y guarda logs individuales. Baseline: **68 passed**. Evidencia estructurada en `mutants_results.json`.

| Mutante | Alteración concreta | Resultado final | Prueba que lo mata, entre otras |
|---|---|---|---|
| (a) basename | Tras `_partes`, conserva solo el último componente | 21 failed / 47 passed | T9 de homónimos y T1 |
| (b) ENTREGA sin directorio | Elimina `pat.match(directorio)` de la condición | 5 failed / 63 passed | `CarpetaRara/_manifiesto.yaml`, `01_Drive EV/.synced` |
| (c) plan sin comparación | Sustituye `if sha_raiz != sha` por `if False` | 1 failed / 67 passed | T5 divergente, incluido dry-run |
| (d) unlink sin relectura | Sustituye ambas lecturas de fase 2 por `sha_plan` | 1 failed / 67 passed | T5c raíz cambiada durante fase 1 |
| (e) sala por nombre | `_es_control(rel)` → `_es_control(p.name)` | 3 failed / 65 passed | T1, T3, T7 |
| (f) mapping por basename | Clasifica `k.rsplit('/',1)[-1]` | 1 failed / 67 passed | T6 mapping del adjunto anidado |

Se detectó y corrigió un error del arnés de mutación que doblaba finales CRLF al usar `write_text`; se repitieron baseline y los seis mutantes conservando bytes/finales de línea. La tabla y JSON recogen exclusivamente la ejecución corregida; ninguna muerte por error sintáctico se cuenta. Los 18 ficheros originales cambiados de `work/` volvieron a coincidir byte a byte con head al terminar.

Otras ejecuciones:

- `pytest ... --basetemp=./tmp_probes3 -q -s tests/test_review_r2.py`: **11 passed**, 1,44 s; `probes3.log`. Dos fallos anteriores eran errores del arnés del revisor —firma posicional de `ejecutar` y expectativa equivocada del prefijo de M9—; fueron corregidos y no se cuentan como defectos de producción.
- `pytest ... --basetemp=./tmp_delta3 -q -s tests/test_review_delta.py` en cada árbol: **3 passed** en cada uno; `delta_head3.log`, `delta_base3.log`. Incluye matriz, sobrescritura y adaptadores email/etapa. Se corrigió previamente una llamada posicional errónea del arnés a `etapa_drive`.
- `pytest ... --basetemp=./tmp_oldcrm tests/test_review_original_crm.py`: **2 failed, 40 passed**, reproduciendo H-06.
- `pytest ... --basetemp=./tmp_reverse tests/test_migrar_layout.py tests/test_intake_control_por_ubicacion.py`: **68 passed**, 2,24 s, con el orden de módulos invertido.
- Dry-run positivo: snapshot de bytes **y directorios** del caso antes/después, más espía de `_write_atomico`: sin cambios y cero llamadas. Dry-run divergente: T5. No apareció `._intake_hashes.json.<pid>.tmp`. La sonda de rollback comprobó también que no quedasen lotes vacíos tras deshacer movimientos de dos cajones.
- Raíz desaparecida durante fase 1: el CLI termina, conserva el legacy, deja motivo en `intake_log` y emite `[AVISO] NO borrado ... la raíz ya no tiene el fichero`. T5c verifica además el diccionario `informe` para divergencia.

## 6. Sin verificar y límites

- **Semillas aleatorias SIN VERIFICAR:** `importlib.util.find_spec('pytest_randomly')` devuelve `None`. Invertir dos módulos no acredita independencia respecto a todos los órdenes, ni equivale a ejecutar semillas.
- **Los otros siete mutantes de la afirmación «13 mueren» SIN VERIFICAR.** Se ejecutaron las seis clases mínimas especificadas, con alteraciones exactas arriba; no se certifica el total de trece.
- **Suite global SIN VERIFICAR:** se ejecutaron 659 tests originales de head en dos selecciones y los correspondientes 601 de base, más sondas y repeticiones indicadas. No se ejecutaron los restantes módulos del repo ni una campaña completa de todos sus tests antiguos contra head.
- No se ejercitaron todas las secuencias de importación/reload; sí la identidad solicitada y ambos órdenes de los módulos nuevos. No se probaron Linux/macOS, sistemas sensibles a caja, nombres físicos de longitud extrema, ADS, enlaces simbólicos/junctions ni todas las formas Unicode. La prueba de caja es del Windows disponible.
- No se certifica un NO-OP de todo tipo de metadato del sistema de ficheros: el dry-run se verificó para creación/eliminación de entradas, bytes del caso y llamadas de escritura atómica; no para políticas de actualización de tiempos de acceso del SO.
- No se midió la frecuencia real del intercalado de H-01, ni se ejecutó una carrera estocástica con Gmail real. La pérdida bajo el intercalado indicado sí se reprodujo. Tampoco se certifica rollback cuando falla a su vez el movimiento de restauración: el código lo trata como best-effort y silencia esa excepción.
- No se examinó ningún expediente real, catálogo del despacho, `G:`, ni OAuth. No se acredita cuántos casos tienen carpetas con otra caja o documentos con estos nombres.
- `_cobertura` ordinaria y la de split usan rutas de Input en el código inspeccionado. Las coberturas legacy ya almacenadas y sus `source_path` no se censaron; no se inventa evidencia de prefijos absolutos en casos reales.
- Los defectos H-02/H-04/H-05 son preexistentes conservados; H-01 es una garantía concurrente todavía incompleta; H-03 es una regresión reproducida; H-06/H-07 son incumplimientos de declaración/documentación. No se mezclan estas categorías con los fallos ambientales comunes a ambos árboles.

## 7. Custodia al cerrar

Recalculados tras finalizar las lecturas y ejecuciones sobre las copias:

| Fuente | SHA-256 al cerrar | Comparación |
|---|---|---|
| `../head/core/intake_control.py` | `7fcd465232c4d775d2d6195ad0bb5a4166f8e27cc829715cf3f55c452fb9bebd` | Idéntico al de apertura |
| `../head/scripts/migrar_layout_intake.py` | `731755f9e7fd1d710818a51c4cf0fcef02992ba1d10488073a5f2f1e5237081e` | Idéntico al de apertura |

NO-SHIP

<!-- informe-literal:fin:h3wq -->

## 2. Evidencia verificada por mí al adjudicar

Los siete se **confirman**; tres son preexistentes en `main` y el diff los conservaba, y el
revisor lo distinguió correctamente. Lo que yo reproduje, contra la fuente:

- **H-01.** Leí `_migrar_bajo_mutex` (antes `migrar`): entre `compute_sha256(destino)` y
  `hijo.unlink()` no hay exclusión. Es cierto que ninguna relectura la crea. Remedio: el mutex
  del caso (`mutex_sesion.sostenido`, el mismo de `abrir_caso` y `sala_maquina`). Verificado con
  tres tests: otro proceso con el lock → `CasoOcupadoError` y árbol byte a byte igual; durante
  la fase 2 `mutex_sesion.vigente(CaseRef(w_code))` no es `None` y al terminar sí; caso sin
  W-code → aviso y sigue. Mutante «sin mutex»: mueren 3.
- **H-02.** Reproducido: `04_Manual/_manifiesto.yaml` con bytes `prueba original del cliente` →
  tras `migrar`, el fichero del lote era el albarán YAML. Remedio en el plan, verificado en dry-run
  y real: aborta, nombra la ruta, árbol intacto. El anidado (`04_Manual/sub/_manifiesto.yaml`)
  migra con sus bytes.
- **H-03.** Reproducido con el escritor: `01_drive ev/` precreada, `marker = inp / "01_Drive EV" /
  ".pulled"`, `mkdir(exist_ok)` + `write_text` → en Windows el fichero físico es
  `01_drive ev/.pulled` y `inventariar` lo devolvía. Remedio: `IGNORECASE` en los patrones de
  `ENTREGA` y `casefold` en `DIRECTORIOS`. El test que exigía `False` para `01_drive ev/.pulled`
  se invirtió con la razón escrita. Mutantes: 3 y 2 muertos.
- **H-04.** Leí `corpus_legible` (línea 303): el único llamador; sus `rel_path` vienen de
  `_cobertura`, relativas a `00_Input/`. Las cinco excepciones no podían acertar nunca y sí
  fallar. Retiradas; T13 ampliado a los cinco nombres bajo `<lote>/adjuntos/`. Mutante que las
  devuelve: mueren 5.
- **H-05.** Leí `sync_sudespacho.py:1099-1112`: solo `except SudespachoError` limpiaba. Remedio:
  `except BaseException: tmp.unlink(); raise`. Test con `download_document_rest` que escribe
  bytes parciales y lanza `OSError`: sin `.tmp` y `inventariar == []`. Mutante: muere.
- **H-06/H-07.** Leídos los docstrings citados; decían exclusiones que ya no existen y «TRES»
  comprobaciones por hash donde hay dos más una de existencia. Corregidos; §5 del diseño
  completado con los tres cambios omitidos.

**No remediado, con razón:** `email_export` con destino externo llamado como lote registra en el
M9 una ruta inexistente — preexistente y fuera del alcance de este diseño; `MEJORAS #168`.

**Cobertura de la remediación: sin revisión adversarial** (dos rondas por radio de daño; sin
tercera sin autorización expresa).
