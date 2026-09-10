---
tipo: revision-adversarial
objeto: diff 874111b..7c4a97a — sala de lectura plana + guarda de colisión (core/sala_lectura.py)
objeto_rev: "1"
commit: 7c4a97a
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: q4vk
sha256_informe: 0fd645ec4c36dabb5a8363256a7ca0eddc14a4c99c8f495af3de6a778ea6ec8f
adjudicado_en: docs/superpowers/plans/2026-09-10-sala-lectura-plana.md §5
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-09-10
---

# Acta de revisión adversarial R1 — sala de lectura plana + guarda de colisión

- **Objeto revisado:** diff `874111b..7c4a97a` — `core/sala_lectura.py` y sus dos ficheros de tests
- **Ronda:** R1 (única; radio de daño = no decide quién escribe ni destruye el crudo de `00_Input`)
- **Revisor:** Codex (CLI 0.153.4), copia externa `git archive` de los dos commits, solo lectura
- **Informe recibido:** 2026-09-10, `C:/t/rev-sala-plana-2026-09-10-2148/INFORME.md`, 38925 bytes
- **Hallazgos:** 12 — 5 ALTOS, 6 MEDIOS, 1 BAJO; **12 confirmados, 0 refutados**
- **Remediado en:** `docs/superpowers/plans/2026-09-10-sala-lectura-plana.md` §5

**Por qué existe esta acta.** Yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**. La adjudicación —qué
acepté, qué dejé fuera de alcance y dónde se remedia— vive en el §5 del plan, que es el documento
que la decisión modificó; aquí va la voz literal del revisor y nada más.

**Custodia.** El objeto se le dio como dos árboles `git archive` sin `.git`, en un directorio de
ronda con nombre irrepetible y comprobado vacío antes de lanzar. Los `sha256` de los tres ficheros
revisados coinciden al abrir y al cerrar, y el revisor lo declara en su §1 y §11. El digest de
abajo se computó **con la ronda ya terminada** (la señal es la salida del proceso, no la existencia
del `INFORME.md`: un informe a medio escribir da un digest coherente y falso). Comprobado dos veces
con 10 s de separación: mismo valor. El `sha256` del fichero crudo es
`0fd645ec4c36dabb5a8363256a7ca0eddc14a4c99c8f495af3de6a778ea6ec8f` y coincide con el digest del bloque
canonicalizado, porque el informe viene en LF con un único salto final.

**Higiene del workdir.** El revisor declaró en su primera línea que encontró un `_stdout.log`
además del mandato y los dos árboles, y que no leyó su contenido. Era el log del propio lanzamiento
de esta ronda, redirigido por mí.

## 1. Informe recibido (literal, sin editar)

<!-- informe-literal:inicio:q4vk -->
Higiene de apertura: se encontró `_stdout.log` además de `MANDATO.md`, `base/` y `head/`; no se leyó su contenido.

# Revisión adversarial R1 — sala plana y guarda de colisión

## 1. Objeto, custodia y alcance

Auditoría de completitud y corrección del copiador, según el mandato. No se realizaron operaciones sobre expedientes reales ni sistemas externos. No se proponen parches. El diagnóstico queda sujeto a la adjudicación del autor contra la fuente.

SHA-256 de apertura, obtenidos antes de examinar la pieza:

| Fichero | SHA-256 |
|---|---|
| `head/core/sala_lectura.py` | `b8f40ce8df8ccc1311dced272b00cbdea851737dc750d78d85273c2a6f622da6` |
| `head/tests/test_sala_lectura.py` | `f38ddbaedca0c801b1001ccf46086b8442d89e8c20cb9d6090f7822badd18525` |
| `head/tests/test_sala_lectura_plana.py` | `9aa6164cf0e2ef4dbe862335182050ecdcef32510fb25fb7c6eb2770346323ff` |

La comparación por contenido de los 1.281 ficheros de `base/` y 1.282 de `head/` encuentra exactamente las tres diferencias declaradas. Los manifiestos `custodia_apertura.json` y `custodia_cierre.json` son iguales. No se modificó ninguno de los dos árboles. **SIN VERIFICAR** la atribución a `874111b` y `7c4a97a` y su genealogía: los archivos no contienen `.git`.

Se crearon después de la inspección inicial las copias `run/`, `run_base/`, `run_mutant/`, las pruebas propias y los registros de esta ronda, autorizados por §§4–5. La copia `run_base/` contiene producción de base y los dos ficheros de tests de head para medir discriminación. La única mutación deliberada de producción se hizo en `run_mutant/`. Las instrucciones generales de trabajar en el checkout habitual, consultar bitácoras y cerrar con commits no se aplicaron: contradicen el mandato específico de revisión aislada y solo lectura. No se solicitó otra revisión ni se delegó el veredicto.

## 2. Ejecución y control del instrumento

Python utilizado: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`, versión observada 3.14.4; pytest 9.1.1; Windows. Para los comandos siguientes, `$py` representa esa ruta y se fijó `$env:PYTHONDONTWRITEBYTECODE='1'`. Todos parten del workdir del mandato, hacen `Set-Location` a la copia indicada y usan temporales relativos. Los registros citados están en el workdir, fuera de los árboles revisados.

| Evidencia | Comando ejecutado, tras entrar en la copia | Resultado y registro |
|---|---|---|
| E1 | En `run`: `& $py -m pytest -q tests/test_sala_lectura_plana.py tests/test_sala_lectura.py --basetemp=./bt_ok -p no:cacheprovider --randomly-seed=777` | 50 pasan, salida 0; `suite_head_777.txt` |
| E2 | En `run`: mismo comando, `--basetemp=./bt_31337 --randomly-seed=31337` | 50 pasan, salida 0; `suite_head_31337.txt` |
| E3 | En `run`: `& $py -m pytest -v -s tests/test_probe_r1.py --basetemp=./bt_probe -p no:cacheprovider --randomly-seed=777 --tb=short` | 19 casos: 10 fallan por aserción, 9 pasan; `probes_r1.txt` |
| E4 | En `run`: `& $py -m pytest -v -s tests/test_probe_extra_r1.py --basetemp=./bt_extra2 -p no:cacheprovider --randomly-seed=777 --tb=short` | 4 casos: 2 fallan por aserción, 2 pasan; `probes_extra_r1_corregido.txt` |
| E5 | En `run_base`: `& $py -m pytest -v tests/test_sala_lectura_plana.py tests/test_sala_lectura.py --basetemp=./bt_base -p no:cacheprovider --randomly-seed=777 --tb=short` | 10 fallan, 40 pasan; los seis nuevos fallan; `suite_base_con_tests_head.txt` |
| E6 | En `run_mutant`: `& $py -m pytest -v tests/test_sala_lectura_plana.py --basetemp=./bt_mutante -p no:cacheprovider --randomly-seed=777` | 6 pasan aun dando el nombre pelado al hash MAYOR; `suite_mutante_hash_mayor.txt` |
| E7 | En `run`: `& $py probe_links.py` | Salida 0; poda real de symlink y junction; `poda_enlaces.txt` |

Los rojos de E3/E4 son aserciones de invariantes deseables, no doce defectos necesariamente independientes: varios prueban distintas consecuencias de una misma causa. Los casos que cuentan estados defectuosos observados y pasan se identifican como tales; no se presentan como aceptación del producto.

Incidencias del instrumento: el primer lanzamiento, usando `workdir=.../run` en la herramienta, coleccionó 50 casos pero produjo errores de preparación `WinError 5` al crear el temporal absoluto. Se reprodujo el problema con una operación mínima. Al iniciar desde la raíz autorizada y hacer `Set-Location run`, tanto la operación absoluta mínima como pytest funcionaron, sin modificar bibliotecas ni producción. Es un resultado del entorno de lanzamiento, no un defecto del copiador; no se ha determinado su causa interna. La primera E4 tuvo un error propio de fixture por `mkdir` sobre una carpeta ya existente: se añadió `exist_ok=True` únicamente al test propio y se repitió el fichero completo; se conserva `probes_extra_r1.txt` como registro del intento inválido. Ningún fallo de preparación se cuenta como hallazgo del objeto.

## 3. Dictamen sobre las cuatro afirmaciones (§3.1)

| Afirmación | Dictamen, condiciones y anclas de head |
|---|---|
| Sala plana | **Cumple para los nuevos destinos ordinarios**: `core/sala_lectura.py:774`; cabecera y adjuntos de bundle conservan subcarpetas en `:777` y `:778`. **No garantiza que toda una sala existente quede plana**: se omiten fuentes ausentes y duplicados (`:847`, `:850`); la poda no retira carpetas con archivos (`:832`), y preserva nombres que empiezan por `_` (`:829`). Un documento ya anidado puede permanecer allí. E1/E2 y E4 verifican ambos lados. |
| Ninguna colisión pierde un documento | **Falsa en general.** Resuelve grupos directos de nombres iguales, con hashes únicos y no vacíos, siempre que los nombres generados no choquen con otros grupos, reservas previas ni objetos existentes. No hay comprobación global después de sufijar (`:804`, `:815`, `:883`). H-01 a H-04 y H-11. |
| Desambiguación independiente del orden, por hash menor | **Cierta para el mismo conjunto planificado, con hashes únicos, directorios/nombres fijos** (`:804`, `:809`). Las seis permutaciones propias de un grupo de tres dan la misma asignación. **No implica estabilidad histórica de citas**, ni conservación de bytes durante el traslado: una incorporación o exclusión por fuente ausente cambia el conjunto; hashes vacíos y selección de duplicados vuelven a depender del orden (`:847`, `:850`, `:866`). H-02/H-03/H-05. |
| Migra solo desde layout anterior | **Cierta con originales disponibles, referencias antiguas correctas, destino utilizable y corrida completa** (`:875`–`:887`). E1/E2 cubren un documento; la prueba propia E3 también recupera dos originales que antes compartían una copia sobrescrita. **No es universal ni transaccional**: H-02/H-04/H-05/H-10/H-11. E4 conserva sin migrar una copia legacy cuyo original falta. La poda puede dejar carpetas no vacías y tiene los límites H-06/H-07/H-08. |

## 4. Hallazgos

### H-01 · ALTA · El sufijo generado colisiona con un nombre natural

**Ancla:** `head/core/sala_lectura.py:804`, `:807`, `:815`, `:883`.

**Qué falla:** la agrupación considera los nombres de entrada, pero no reserva los nombres finales de otros grupos. Se producen dos rutas finales idénticas para hashes distintos; `copy2` sobrescribe una copia y la siguiente corrida acepta el estado incorrecto.

**Disparador concreto:** tres originales `a.pdf`, `b.pdf`, `c.pdf`, bytes respectivos `%PDF-A`, `%PDF-B`, `%PDF-C`; tipo `01. ACTIVACIÓN`, fecha `2025-02-27`; descripciones `mismo`, `mismo`, `mismo_2`. A recibe `..._mismo.pdf`; B y C reciben ambos `..._mismo_2.pdf`. Quedan los bytes de C donde el catálogo también señala B. Se produce sin hashes vacíos ni catálogo corrupto.

**Evidencia:** leído y ejecutado, E3, `test_natural_suffix_is_not_overwritten`. La corrida siguiente devuelve `SKIP_UNCHANGED: 3` y no repara B. La misma frontera alcanza `_3`, etc. Es un hueco de la guarda nueva; la sobrescritura subyacente existía en base.

### H-02 · ALTA · Un cambio de participantes reasigna citas y los traslados pueden borrarse entre sí

**Ancla:** `head/core/sala_lectura.py:809`, `:850`, `:864`, `:872`, `:878`, `:884`.

**Qué falla:** el reparto se recalcula sin conservar asignaciones históricas ni reservar rutas de filas excluidas. El segundo pase sigue el orden del catálogo y borra `prev` sin comprobar quién ocupa ahora esa ruta.

**Disparador concreto 1:** A=`%PDF-A` (hash `48f6ee…`), B=`%PDF-B` (`585ed6…`) ya tienen `mismo.pdf` y `mismo_2.pdf`. Entra C=`%PDF-C` (`12ce5e…`), menor que ambos. Con orden de filas A,B,C, A pasa a `_2`; B borra su anterior `_2`, que acaba de recibir A, y pasa a `_3`; C ocupa el nombre pelado. A queda sin copia aunque su nueva ruta se guarda. Una segunda corrida repone A, pero no restaura las citas anteriores. No hubo interrupción ni concurrencia.

**Disparador concreto 2:** después de poblar A y B se retira el original de A. A sale del plan por `MISSING_SRC`; B toma el nombre pelado de A. Ambas filas del catálogo apuntan al mismo fichero, con bytes de B. La copia válida de A que aún quedaba en la sala se ha sobrescrito.

**Evidencia:** leído y ejecutado, E3, `test_late_lower_hash_keeps_citations_and_copies`, `test_missing_source_does_not_reassign_its_path` y los dos casos `test_late_middle_or_high_observed_order`. La inserción intermedia cambia un nombre previo; la inserción del hash mayor conserva los anteriores. La nueva reasignación amplía un riesgo ya presente en los renombrados de base.

### H-03 · ALTA · Varias filas sin hash se unen aunque sus nombres sean distintos

**Ancla:** `head/core/sala_lectura.py:806`, `:812`, `:815`, `:847`, `:858`, `:866`; admisión de hash vacío en `head/core/catalogo_documental.py:42`, `:84`, `:113`.

**Qué falla:** los vacíos no se deduplican, pero el resultado se indexa exclusivamente por hash. Todas las filas con `hash=''` comparten una única casilla del diccionario, incluso perteneciendo a grupos distintos.

**Disparador concreto:** A y B con bytes distintos, `hash=''`, mismo directorio y descripciones `uno`/`dos`. Ambas reciben `..._dos.pdf`; B pisa A. Al invertir el catálogo ambas pasan a `..._uno.pdf` y queda A. Si el nombre original coincide, el último valor del grupo será `_2`, sin un resultado independiente para la primera fila.

**Evidencia:** leído y ejecutado, E3, `test_empty_hash_different_names_keep_separate_paths` y `test_pure_allocator_case_extension_and_permutations`. Regresión introducida por el diccionario nuevo. El inventario normal calcula hashes, pero el modelo y el cargador admiten vacíos; no se presume que existan actualmente en un caso real.

### H-04 · ALTA · Una ruta existente se acepta sin verificar tipo ni contenido; la corrupción puede persistir

**Ancla:** `head/core/sala_lectura.py:872`, `:873`, `:883`, `:887`.

**Qué falla:** igualdad de texto de ruta más `exists()` equivale a copia correcta. No se compara el hash del destino con el catálogo ni se verifica que sea un archivo completo. Esto perpetúa los errores H-01/H-02 y copias parciales.

**Disparador concreto:** poblar A, reemplazar los bytes de su destino por `OTRO DOCUMENTO` y repetir: `SKIP_UNCHANGED: 1`. Variante sin modificación ajena: eliminar una copia ya registrada, interrumpir su reposición después de escribir `PARCIAL`, repetir. La ruta del catálogo ya coincide y el fichero parcial existe: vuelve a saltarlo indefinidamente.

**Evidencia:** leído y ejecutado, E3, `test_preexisting_wrong_bytes_are_not_accepted` y `test_interrupt_repair_at_same_catalog_path`. Preexistente en base, relevante para evaluar la recuperación prometida. No se ha perdido el original en estos ensayos.

### H-05 · MEDIA · Deduplicar no mantiene todas las referencias y reconstruir puede dejar huérfanos

**Ancla:** `head/core/sala_lectura.py:847`–`:849`, `:887`; `head/core/catalogo_documental.py:107`, `:115`.

**Qué falla:** la primera fila con fuente existente gana; las siguientes del mismo hash se saltan sin actualizar su ruta ni relaciones. Sus rutas previas o nulas se guardan intactas. No se limpian copias sin referencia. La reconstrucción preserva la última fila del mismo hash y puede descartar la que sí tenía asignada la copia.

**Disparador concreto:** `a.pdf` en Drive y `b.pdf` en Email, ambos bytes `IGUAL`, descripciones `uno`/`dos`. Primera población: A tiene `..._uno.pdf`, B tiene ruta nula. `inventory.scan` + `build_catalog` conservan por hash los metadatos de B; otra población crea `..._dos.pdf`. `..._uno.pdf` queda huérfana. En una variante distinta, si la entrada preservada por hash ya contiene una ruta, `build_catalog` puede serializar dos filas con esa misma ruta al reutilizarla para dos archivos del inventario.

**Evidencia:** leído y ejecutado el huérfano en E3, `test_duplicate_rebuild_does_not_orphan_previous_copy`; la variante de filas clonadas con ruta se deriva de `:115`. Comportamiento previo al diff. Dos filas con igual hash y una copia compartida no implican por sí solas bytes erróneos; el defecto es la referencia ausente, obsoleta o perdida, y la selección dependiente del orden.

### H-06 · MEDIA · La poda no queda confinada al árbol físico de la sala y elimina enlaces

**Ancla:** `head/core/sala_lectura.py:825`, `:827`, `:832`.

**Qué falla:** `is_dir()` admite enlaces a directorios; no hay comprobación de tipo de enlace ni confinamiento físico. En Windows/Python ensayado, `rglob` recorre una junction y `rmdir` elimina enlaces a directorios cuyo destino no está vacío.

**Disparador concreto:** bajo la sala se crean `junction` y `symlink` hacia `run/link_checks/fuera_de_sala`, que contiene `vacio/` y `con_dato/documento.txt`. La poda enumera `junction/vacio` y lo borra en el destino exterior. Después elimina la junction y el symlink. `documento.txt` sobrevive y el directorio destino sigue existiendo.

**Evidencia:** ejecución real E7, sin simulación de `rglob`/`rmdir`; registro `poda_enlaces.txt`. Se refuta que solo borre cascarones vacíos situados físicamente bajo la sala. **No se observó ni se afirma borrado de archivos regulares o borrado recursivo del contenido no vacío.** Riesgo nuevo. Otras plataformas y otros tipos de reparse point no están verificados.

### H-07 · MEDIA · La exclusión de `_plan` no protege su subárbol

**Ancla:** `head/core/sala_lectura.py:822`–`:823`, `:827`, `:829`.

**Qué falla:** se filtra únicamente el nombre del directorio visitado, después de recorrer sus descendientes. Se conservan `_plan/` y los archivos que contiene, pero se borran sus descendientes vacíos cuyo nombre no empieza por `_`.

**Disparador concreto:** `_plan/lote/pendiente/` vacío y `_plan/plan.json` con `{}`. Se conserva `_plan/plan.json`, se eliminan `pendiente/` y `lote/`.

**Evidencia:** leído y ejecutado, E3, `test_plan_subtree_is_preserved`. Contradice la exclusión funcional declarada en el docstring. No se ha verificado si un flujo real concreto depende de esos directorios vacíos.

### H-08 · BAJA · Los errores de poda quedan indistinguibles de un directorio no vacío

**Ancla:** `head/core/sala_lectura.py:832`–`:834`, `:887`–`:889`.

**Qué falla:** se absorbe todo `OSError` de `rmdir`, incluido `PermissionError`, sin contadores ni diagnóstico. La corrida puede terminar normalmente y dejar restos por falta de permisos, sin distinguirlos de una conservación deliberada. El `try` no cubre todos los pasos de enumeración; no equivale a tolerancia general de cualquier error de la función.

**Disparador concreto:** `rmdir` sobre `Sala lectura/sin_permiso` lanza `PermissionError`. La función devuelve `None` y la carpeta permanece, sin señal de error.

**Evidencia:** leído y ejecutado con inyección de ese error en E3, `test_prune_permission_error_is_silent`. No es un ensayo de ACL reales. Absorber el caso «no vacío» sirve al diseño; absorber a la vez errores de permisos oculta por qué la migración no terminó de limpiar.

### H-09 · MEDIA · Sin bundle se borra `parent_id` y se conserva `orden_en_bundle`

**Ancla:** `head/core/sala_lectura.py:772`–`:778`, `:854`–`:856`.

**Qué cambia:** base no escribía `parent_id` ni `orden_en_bundle` para una fila sin bundle detectado. Head asigna siempre el `parent_id` devuelto, que es `None` en ese caso, y solo escribe el orden si no es `None`. Una corrida sin `crm_docs` puede eliminar una relación previa y conservar su ordinal.

**Disparador concreto:** fila con original existente, `parent_id='padre_existente'`, `orden_en_bundle=7`; llamada sin `crm_docs`. Base deja `('padre_existente', 7)`; head guarda `(None, 7)`.

**Evidencia:** comparación ejecutada entre ambas implementaciones copiadas, E3, `test_nonbundle_metadata_compared_with_base`. Es una diferencia observable del diff, no una escritura de adjunto olvidada en el segundo pase. Si la degradación pretende retirar esa relación, el autor debe adjudicar esa intención; la conservación del ordinal y el cambio respecto de base quedan acreditados. No se presume que toda relación previa deba conservarse.

### H-10 · ALTA · No hay transacción de copia y catálogo ni exclusión de corridas solapadas

**Ancla:** `head/core/sala_lectura.py:838`, `:878`, `:883`–`:887`; `head/core/catalogo_documental.py:90`; llamada CLI directa en `head/scripts/sala_lectura.py:83` y `:209`.

**Qué falla:** se carga una instantánea, se hacen escrituras/borrados de disco y se reescribe todo el catálogo al final, sin lock ni publicación atómica en este recorrido. Una instantánea antigua puede sobreescribir una actualización posterior y dejar copias sin fila. También hay ventanas entre `exists()` y `unlink()` y entre creación, copia y guardado.

**Disparador concreto ejecutado:** corrida A carga una fila y copia; antes de su guardado, se añade una segunda fila al catálogo y se ejecuta B completa con dos filas. A reanuda y guarda su instantánea de una fila. Resultado: un catálogo con una fila y dos archivos.

**Evidencia:** intercalación determinista de dos invocaciones, E3, `test_stale_overlapping_run_loses_catalog_update`; no se presenta como prueba con dos procesos del sistema operativo. Los cortes se detallan en §7. Riesgo preexistente; los dos pases no lo resuelven. No se ha auditado todo posible envoltorio externo, pero el recorrido CLI citado llama directamente a estas funciones.

### H-11 · MEDIA · El plan no inventaría objetos ya presentes en el destino

**Ancla:** `head/core/sala_lectura.py:804`, `:870`, `:872`, `:882`–`:884`.

**Qué falla:** la guarda solo ve filas planificadas. Un archivo preexistente sin reserva se sobrescribe. Si `dst` es un directorio, `shutil.copy2(src, dst)` deposita el archivo dentro con su nombre original; el catálogo registra el directorio como si fuese la copia y la siguiente corrida lo acepta.

**Disparadores concretos:** (1) archivo `2025-02-27_activacion_mismo.pdf` con bytes `DOCUMENTO PREEXISTENTE SIN FILA`; tras poblar A contiene `%PDF-A`; (2) directorio con ese mismo nombre: queda `...mismo.pdf/a.pdf`; el catálogo señala `...mismo.pdf` y la segunda corrida devuelve `SKIP_UNCHANGED: 1`.

**Evidencia:** leído y ejecutado, E4, `test_untracked_existing_destination_not_silently_replaced` y `test_directory_at_destination_is_not_accepted`. Preexistente en la primitiva de copia; la nueva guarda no cubre ese espacio de nombres.

### H-12 · MEDIA · Se debilita el aserto de parada con residuo; la prioridad exacta de hash no se prueba

**Ancla:** `head/tests/test_sala_lectura.py:335`; `head/tests/test_sala_lectura_plana.py:176`, `:199`, `:228`–`:241`.

**Qué falla:** el aserto anterior exigía que no existiera `Sala lectura/Drive E&V`. El nuevo únicamente exige ausencia de PDF en la raíz de la sala. Una copia indebida en `Drive E&V/x.pdf`, una carpeta vacía por fuente u otro formato pasan ese aserto. Es una relajación verificable por lectura, no una nueva política de parada. Además, los tests nuevos comprueban conjuntos de nombres y estabilidad al invertir filas, pero no que el hash menor tenga el nombre pelado.

**Disparadores concretos:** el estado `Sala lectura/Drive E&V/x.pdf` satisface la expresión nueva y viola la vieja; cambiar únicamente el orden de clasificación a `sorted(..., reverse=True)` da el nombre pelado al hash mayor y mantiene verdes los seis tests nuevos.

**Evidencia:** leído el cambio del aserto; mutante ejecutado E6. Los seis nuevos sí fallan contra base (E5): no se les atribuye falsamente ausencia total de discriminación. Véase §9.

## 5. Recorrido de casos del copiador (§3.2)

Inventario por fronteras de decisión y efectos, para entradas cargables por el modelo. «Sin copia» se refiere a una copia válida propia, no a que se borre el original.

| Camino y estado resultante | ¿Lo evita head? Disparador y ancla |
|---|---|
| (a) Fila sin fuente | No copia y registra `MISSING_SRC`; conserva sus campos y su copia antigua si la había. `core/sala_lectura.py:850`–`:852`. E4 verifica que no migra la copia legacy. Puede además perder esa copia por H-02. |
| (a) Fila deduplicada | Omisión deliberada de segunda copia por hash, pero no asegura referencia a la primera: H-05, `:847`–`:849`. Si el hash está mal declarado, puede omitir bytes distintos; el copiador no recalcula hashes. |
| (a) Fuente existe al planificar y desaparece antes de copiar | Excepción antes del guardado, con efectos previos en disco. E4 lo reproduce al terminar el plan; `:850`, `:865`, `:883`. Una fuente que sea directorio también supera `exists()` y falla al copiar: leído, no ejecutado. |
| (a) Error de nombre/ruta, permisos, espacio, `mkdir`, `unlink` o copia | No hay rollback del prefijo ejecutado: `:866`–`:884`. Una excepción anterior al primer efecto no produce copias nuevas; una posterior puede dejar migraciones a medias. Cortes de copia ejecutados; errores físicos específicos no todos ensayados. |
| (a) Renombrados solapados de filas distintas | La ruta de una fila recién copiada puede ser borrada por otra: H-02, `:878`. Ejecutado sin fallo externo. |
| (b) Copia con bytes de otra fila | H-01/H-03/H-02: nombres finales duplicados o ruta reservada por una fila fuera del plan; `:815`, `:866`, `:883`. Las mismas colisiones son también (c). |
| (b) Bytes anteriores, externos o parciales aceptados | H-04: `:872` solo mira existencia. Si cambian los bytes de la fuente manteniendo la fila/hash/ruta, el copiador tampoco detecta ese cambio; leído. |
| (c) Dos filas de hashes distintos con la misma ruta | H-01, H-02 por fuente ausente, H-03. No lo evita, y puede perpetuarlo mediante `SKIP_UNCHANGED`. |
| (c) Dos filas de igual hash con una ruta | Puede proceder de referencias previas o `build_catalog` reutilizando una entrada; H-05. Compartir bytes idénticos no es corrupción por sí solo. |
| (d) Archivo existente sin fila o fila eliminada del catálogo | No se inventaría ni reconcilia; `:838`, `:886`. La poda solo trata directorios, no copias. Si coincide con una ruta planificada lo sobrescribe (H-11); si no, permanece huérfano. |
| (d) Copia final creada pero catálogo no guardado | Corte tras `copy2`, fallo de guardado o corrida solapada; `:883`–`:887`, H-10. Ejecutados corte y solapamiento. El destino puede ser temporalmente huérfano hasta reintentar. |
| (d) Dedup, reconstrucción o cambio de representante | La copia que pierde la referencia no se retira: H-05, ejecutado. |
| (d) Destino directorio o alias de filesystem | H-11 ejecuta copia dentro de un directorio sin referencia al archivo interior. Alias, enlaces duros o destinos equivalentes por reparse points no son reservados por la agrupación de cadenas (`:804`); el copiador completo sobre esos alias no se ensayó. |

No hay limpieza general de archivos sobrantes. Tampoco hay validación local de confinamiento de `ruta_relativa` o `ruta_sala_lectura`: se concatenan en `head/core/sala_lectura.py:97` y `:876`. Con rutas absolutas o `..` fuera del contrato, el recorrido puede leer/copiar o desvincular fuera del lugar previsto; se constata por lectura, sin ensayo de rutas externas. No es una novedad del diff ni se atribuye ese riesgo a la poda.

## 6. Cobertura de `_desambiguar` (§3.3)

| Caso | Resultado y evidencia |
|---|---|
| Hash vacío | No dedup previo; un único valor `final['']` para varias filas: H-03. Un solo vacío, sin otro vacío ni colisión de sufijo, funciona; dentro de un grupo con hashes válidos ordena antes que ellos (`:809`). |
| Hash repetido no vacío | El llamador retiene la primera fila con fuente existente y salta las demás (`:847`); `_desambiguar` por sí sola no defiende duplicados y sobrescribe su entrada de resultado. Ambas capas examinadas; llamada directa con repetido ejecutada en E3. No debe confundirse el contrato de esa función con el de su llamador. |
| Solo mayúsculas en nombre | `nombre.lower()` une el grupo (`:804`). E3 prueba `X.PDF`/`x.pdf` y obtiene `X.PDF`/`x_2.pdf`. En el flujo normal, `_nombre_canonico` ya normaliza extensión (`:719`) y descripción mediante slug minúsculo (`:723`; `head/core/utils.py:67`). No se cubren así todos los posibles alias de nombres de un filesystem. |
| Solo extensión diferente | `.pdf` frente a `.docx` forma grupos distintos y mantiene ambos nombres: E3. No es colisión ordinaria de archivo. `.PDF` frente a `.pdf` sí se une/normaliza. Sin extensión frente a `.pdf` también conserva dos nombres en la prueba pura. |
| Nombre natural terminado en `_2` | No hay reserva cruzada: H-01. Con varias colisiones, un grupo natural `x_2.pdf` puede a su vez generar `x_2_2.pdf`; solo se razona dentro de cada grupo, nunca sobre el conjunto final (`:807`–`:815`). |
| Entra un documento después | No se consulta `nombre_canonico` ni `ruta_sala_lectura` al repartir. Si su hash es menor, desplaza todos los anteriores; si es intermedio, desplaza a los mayores; si es el mayor, añade el siguiente sufijo. E3 ejecuta las tres posiciones. Las citas no quedan fijadas históricamente. |
| Crece de dos a tres | Orden total ascendente del hash, no orden de llegada de sufijos. El plan de nombres es determinista para el conjunto fijo; la ejecución de movimientos sigue las filas (`:864`) y puede eliminar una copia recién hecha. E3 prueba tanto las permutaciones puras como la llegada del tercero. |
| Cambia disponibilidad o clasificación | Una fuente ausente deja de reservar nombre (`:850`). Un cambio de fecha, descripción, tipo o bundle cambia el grupo (`:853`, `:857`). Es la misma frontera de H-02; la fuente ausente está ejecutada, no todas las combinaciones de metadatos. |

## 7. Poda, idempotencia, interrupciones y concurrencia (§3.4–§3.5)

**Poda sobre directorios ordinarios:** trabaja de mayor profundidad a menor (`head/core/sala_lectura.py:827`–`:828`), no intenta quitar el directorio raíz recibido, y `rmdir` falla si contiene archivos. E3 intercala la creación de `escritor/llegada.txt` justo antes de `rmdir`: el archivo y el directorio sobreviven. Si un escritor todavía no ha creado nada cuando se hace `rmdir`, puede desaparecer el directorio que pensaba usar. No hay coordinación con ese escritor. E7 limita el argumento de confinamiento: junctions y symlinks no equivalen a directorios ordinarios. `_plan` y errores, H-07/H-08.

**Dos corridas completas seguidas:** con conjunto de filas/metadata/bundles fijo, originales presentes, destinos correctos y sin interferencia, convergen al mismo contenido y las copias se omiten; los tests originales de copia y bundles lo verifican (`head/tests/test_sala_lectura.py:264`, `:366`–`:373`). No es una garantía incondicional: tras la incorporación H-02, la corrida siguiente cambia el estado del disco porque repone una copia que la anterior acaba de borrar; en H-01/H-04 el estado es estable pero incorrecto. Idempotencia no acredita integridad. `organizar` además reconstruye catálogo e índices (`head/core/sala_lectura.py:921`, `:922`, `:949`), por lo que esta afirmación de estabilidad se refiere a las copias/rutas, no a todos los timestamps de sus renders.

| Punto de corte | Catálogo y disco; recuperación |
|---|---|
| Primer pase o antes del primer efecto | Los campos modificados solo están en objetos cargados; sin `save_catalog` no se persisten. No hay movimientos nuevos todavía (`:854`, `:887`). |
| Entre `old.unlink()` y `copy2` | El catálogo sigue apuntando a la ruta vieja que ya no existe; no hay copia nueva. Con original disponible, mismo reparto y permisos, el reintento encuentra la vieja ausente y copia al destino correcto. **Ejecutado y reparado** en E3, `before_copy`. |
| Durante la copia de una migración | Ruta vieja borrada, copia nueva parcial sin nueva referencia persistida. **Ejecutado y reparado** en E3, `partial_copy`: como `prev` sigue siendo distinto, el reintento reescribe el parcial. |
| Tras copiar una migración, antes de guardar | Copia nueva completa, catálogo viejo: huérfano temporal y referencia vieja rota. **Ejecutado y reparado** en E3, `after_copy`. También se reescribe el destino en el reintento. |
| Durante la reposición en la misma ruta ya registrada | El catálogo ya contiene `dst_rel`; si queda un parcial, `exists()` provoca un falso `SKIP_UNCHANGED`. **Ejecutado y no reparado**, H-04. Si no se crea ningún destino, el siguiente intento sí intentará copiar. |
| En medio del guardado YAML | `head/core/catalogo_documental.py:90` usa escritura directa, sin temporal/replace. Puede quedar un YAML parcial o inválido; el siguiente `load_catalog` puede fallar o cargar datos incompletos. Leído; no se mató un proceso durante esta escritura. |
| Corridas solapadas | Una guarda de existencia puede quedar obsoleta antes del borrado; un guardado tardío pisa una instantánea nueva. E3 ejecuta esta última intercalación. No existe recuperación general por `poblar` de una fila ya perdida: este carga el catálogo disponible (`:838`); `organizar` podría reconstruir filas desde inventario, pero no recupera por eso todas las referencias históricas. |

Los tres ensayos de migración cortada son controles positivos: el código **sí aguanta esos reintentos** bajo las condiciones declaradas. No prueban atomicidad frente a apagado, disco lleno o sincronización de Drive.

## 8. Comparación de escrituras fila por fila con base (§3.6)

Se comparó el cuerpo completo de base `core/sala_lectura.py:759`–`:810` con head, no solo los añadidos.

| Clase de fila/campo | Base | Head y ancla |
|---|---|---|
| Duplicado con hash no vacío | `continue` antes de cambios | Igual, `head/core/sala_lectura.py:847`–`:849`; no se actualizan ruta, nombre, padre ni orden. |
| Fuente ausente | `continue` antes de cambios | Igual para una ausencia al comprobar, `:850`–`:852`; la comprobación se adelanta al primer pase. |
| Cabecera reconocida | `parent_id=None`; no reescribía orden | Igual, `:777`, `:854`–`:856`; un orden antiguo tampoco se limpia aquí. |
| Adjunto reconocido | Padre de cabecera y ordinal del detector | Igual para ordinal válido, `:778`, `:854`–`:856`. `_bundle_map` produce ordinal entero mediante `enumerate` en `:750`, `:755`; no se ha perdido su escritura normal. |
| Fila sin bundle | No cambiaba padre ni orden | Ahora escribe padre `None`, deja orden anterior: H-09. |
| `nombre_canonico` de fila planificada | Se escribía antes de comprobar `SKIP_UNCHANGED` | Se sigue escribiendo, ahora con nombre desambiguado en segundo pase (`:866`–`:867`). |
| `ruta_sala_lectura` | Se escribía tras copiar; se conservaba en skip | Igual, `:872`–`:884`. Una excepción tras copiar y antes de guardar impide persistir la nueva referencia. |
| `vistos_hash` | Se añadía al terminar la fila copiada/saltada por no cambiar | Se añade al terminar su planificación (`:858`–`:859`). Es estado local, no escritura de catálogo. Con corrida exitosa y fuentes estables selecciona el mismo representante; cambia la ventana temporal si el original desaparece. |
| Resto de campos | No los cambiaba el copiador | Tampoco head; `save_catalog` serializa todas las filas al final (`:887`). |

No se detectó pérdida de la escritura normal de `parent_id`/`orden_en_bundle` de los adjuntos detectados. Sí se detectó la nueva puesta a `None` de filas no detectadas, y las ventanas de fallo descritas. Sin terminar la función, ninguno de los dos cuerpos garantizaba guardar sus cambios parciales de catálogo.

## 9. Qué prueban los tests y qué falta (§3.7)

**Discriminación frente a base:** E5 da 40 verdes y 10 rojos. Todos los seis tests nuevos son rojos, incluidos el de conservación de dos documentos por su aserto de nombres (`head/tests/test_sala_lectura_plana.py:176`) y el de orden por su aserto de padre único (`:228`). Los asertos de bytes de dos fuentes distintas, considerados aisladamente, sí pasaban ya con las carpetas separadas de base (`:169`–`:173`); el test completo no pasa en base.

Ejemplos concretos de **tests completos que pasan con base**: `test_poblar_dedup_por_hash` (`head/tests/test_sala_lectura.py:269`–`:278`) y `test_poblar_bundles_idempotente` (`:349`–`:373`). Son regresiones válidas de comportamiento anterior, no pruebas de este arreglo. También pasa en base el test de parada con residuo cuyo aserto se modificó (`:327`–`:335`).

**Los cinco ajustes de layout:** copia simple (`:257`–`:266`) cambia el lugar que cuenta, sin relajar su cardinalidad ni bytes; bundle CRM (`:304`–`:312`) cambia raíz y añade prohibición de `CRM`; degradación (`:322`–`:324`) cambia raíz y añade esa prohibición, conservando el débil `any` ya previo; parada con residuo (`:335`) sí relaja la exclusión, H-12; organización completa (`:345`–`:346`) traslada el mismo `any`. No se afirma que los cinco hayan sido debilitados.

**Límites de los seis nuevos:** el test de migración (`head/tests/test_sala_lectura_plana.py:144`–`:148`) comprueba existencia, acción y eliminación de carpeta, no bytes ni la nueva ruta persistida. El de bundle (`:116`–`:119`) comprueba estructura, no composición completa ni bytes. La colisión doble comprueba el conjunto de bytes y rutas únicas, pero no la correspondencia hash→archivo (`:171`, `:181`–`:182`); la triple verifica nombres/bytes como conjuntos (`:199`–`:204`), no cada referencia. El de orden verifica estabilidad de rutas, no el dueño mínimo ni los bytes tras invertir (`:237`–`:241`). E6 confirma el hueco de prioridad exacta: un mutante que ordena hashes en sentido contrario pasa los seis.

**Inventario explícito de casos de §3.2/§3.3 sin test en los dos ficheros entregados:** colisiones entre sufijos generados y nombres naturales; varias filas con hash vacío; prioridad exacta del menor hash; mayúsculas/extensiones como casos de la guarda; llegada de hash menor/intermedio/mayor después de una población; crecimiento de dos a tres con rutas previas (el triple existente empieza con tres); retirada o ausencia de un participante ya copiado; movimientos que se borran entre sí; archivo o directorio preexistente en destino; copia parcial/corrupta aceptada; dedup con referencias previas/reordenación/reconstrucción y huérfanos; fallo entre pases, durante copia o guardado; concurrencia. El dedup básico y el triple desde cero sí tienen tests: se distinguen de esas variantes.

Tampoco tienen prueba específica entregada la poda de `_plan` descendiente, symlink/junction, permisos o escritor concurrente, ni la transición de metadatos al perder un bundle. Las pruebas propias de esta revisión cubren parte de ese inventario, sin convertirlo en cobertura preexistente del PR. No se calculó un porcentaje de cobertura ni se afirma ausencia de tests equivalentes en toda la suite ajena al alcance.

## 10. No verificado (§3.8)

- Genealogía, autenticidad y correspondencia de los identificadores de commit con los archivos: no hay `.git`.
- Contenido, origen o pertenencia real de `_stdout.log`: no se abrió, por §0. Su presencia impide declarar higiene inicial perfecta, pero no se utilizó su contenido para razonar.
- Reproducción sobre los expedientes citados en comentarios del código o mandato: no se accedió a datos reales. Todos los ejemplos ejecutados son sintéticos.
- Causa interna del fallo de permisos del primer modo de lanzamiento. Se aisló y la suite se ejecutó por el modo que funcionaba, sin atribuir el incidente al objeto.
- Suite completa del repositorio, cobertura porcentual, todos los CLI/UI/MCP y sincronización real de Drive. Se ejecutaron los dos ficheros solicitados, pruebas propias y los controles indicados.
- Dos procesos realmente simultáneos, carrera de sustitución de enlaces durante la poda, ciclos de junctions y otros reparse points. La intercalación de invocaciones y los enlaces de E7 sí se ejecutaron, con el alcance descrito.
- ACL reales denegando la poda, disco lleno, fallo de red, apagado brusco y corte físico durante el guardado YAML. Se inyectaron errores/cortes de copia y `PermissionError`; no se equiparan a una prueba de durabilidad física.
- Comportamiento de enlaces y normalización de nombres en Linux/macOS, volúmenes Windows configurados de otra forma, alias de nombres cortos y enlaces duros. La observación real de E7 vale para el Windows/Python indicado.
- Todas las combinaciones de reclasificación, desaparición/restauración de fuentes y bundles complejos. Se auditaron las ramas y se ejecutaron casos representativos, no una exploración exhaustiva del espacio de estados.
- Efecto operativo real de borrar descendientes vacíos de `_plan` y política deseada de retirada de `parent_id` al degradar un bundle. El comportamiento y la diferencia frente a base están acreditados; esa intención corresponde al autor.
- Catálogos de forma arbitrariamente inválida y rutas externas al contrato. Se leyeron los puntos de carga y concatenación; no se ensayó escritura fuera del scratchpad.

## 11. Custodia de cierre y dictamen

SHA-256 de cierre, recalculados sobre los objetos originales; coinciden con apertura. También coinciden los manifiestos completos de los dos árboles.

| Fichero | SHA-256 |
|---|---|
| `head/core/sala_lectura.py` | `b8f40ce8df8ccc1311dced272b00cbdea851737dc750d78d85273c2a6f622da6` |
| `head/tests/test_sala_lectura.py` | `f38ddbaedca0c801b1001ccf46086b8442d89e8c20cb9d6090f7822badd18525` |
| `head/tests/test_sala_lectura_plana.py` | `9aa6164cf0e2ef4dbe862335182050ecdcef32510fb25fb7c6eb2770346323ff` |

Dictamen del revisor: el aplanamiento básico y la colisión directa están acreditados, pero H-01 y H-02 producen pérdida de copias o referencias incorrectas con entradas ordinarias de hashes válidos. Los verdes de la suite no cubren esas fronteras; la poda tampoco satisface el confinamiento declarado. Estos resultados impiden aceptar las cuatro afirmaciones generales del cambio. No se formula remedio ni se sustituye la adjudicación del autor.

veredicto: NO-SHIP
<!-- informe-literal:fin:q4vk -->

## 2. Evidencia verificada por el autor

- **Los tres `sha256` de apertura y cierre** que declara el informe coinciden con los del árbol
  archivado: el objeto no se mutó.
- **H-01 reproducido en el árbol de trabajo** antes de tocar nada, con el disparador que da el
  informe (descripciones `mismo`, `mismo`, `mismo_2`): dos rutas finales idénticas para hashes
  distintos. Es un hueco de la guarda nueva, no un defecto heredado.
- **El mutante de E6 confirmado y muerto:** con el discriminante alterado, tres tests se ponen
  rojos (antes de la remediación, los seis pasaban). Se comprobó aplicando el mutante al árbol y
  retirándolo.
- **Los cuatro hallazgos que se declaran PREEXISTENTES** (H-04, H-05, H-10 y la mitad de H-11) se
  contrastaron contra el cuerpo de `base/core/sala_lectura.py`: están en el código anterior al
  diff. No se remedian aquí y quedan en `docs/MEJORAS_FUTURAS.md` con su disparador.
