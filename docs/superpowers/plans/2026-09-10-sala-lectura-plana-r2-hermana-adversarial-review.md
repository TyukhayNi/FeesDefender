---
tipo: revision-adversarial
objeto: diff 874111b..9ce7183 — la implementación HERMANA del mismo mecanismo (rama claude/caso-w-048uol-7830a6, retirada en fd401af)
objeto_rev: "1"
commit: 9ce7183
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: m9tz
sha256_informe: 7c77fbcfd2cc2785ef5a0df75c8925d69742429530df0fe990d27e73e28d76ac
adjudicado_en: docs/superpowers/plans/2026-09-10-sala-lectura-plana.md §6
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-09-10
---

# Acta de revisión adversarial R2 — el mecanismo de la sala plana, revisado sobre la implementación hermana

- **Objeto revisado:** diff `874111b..9ce7183` — `_sin_colision` + destino plano, la implementación de la sesión «Caso W-048UOL»
- **Ronda:** R2 sobre el MECANISMO; R1 sobre ESE objeto. La numeración es de la pieza, no del fichero: es la segunda ronda que se adjudica aquí
- **Revisor:** Codex, copia externa del objeto, solo lectura; sondas ejecutadas con el Python de sistema
- **Informe recibido:** 2026-09-10, `C:/t/rev_salaplana_102114/INFORME.md`, 23831 bytes
- **Hallazgos:** 5 — 3 ALTOS (H-01, H-02, H-03), 1 MEDIO (H-05), 1 BAJO (H-04); **3 vivos en mi código ya remediado, 2 ya cubiertos**
- **Remediado en:** `docs/superpowers/plans/2026-09-10-sala-lectura-plana.md` §6

**Por qué este acta vive aquí y no en la rama de la otra sesión.** El objeto revisado es
**su** diff, que se retiró (`fd401af`) y no llega a `main`. Pero la ronda no atacó su
sintaxis: atacó el **mecanismo** —discriminar nombres, reservar rutas, migrar el layout—
que es el que entra por esta rama. Tres de sus cinco hallazgos **se reproducían en mi
código ya remediado por la R1**, así que archivar su voz literal aquí es lo que permite
contrastar qué dijo con qué decidí. La alternativa —dejarlo en una rama que se descarta—
habría perdido la única ronda que midió el solapamiento `Manual`/`manual` en Windows.

**Custodia.** El `sha256` del informe que declaró la sesión hermana al pasármelo
—`7c77fbc…`— coincide con el que recomputé al recibirlo, y su `_ultimo_mensaje.txt`
existía, o sea que la ronda había terminado de escribir. El digest de abajo es el del
bloque canonicalizado y coincide con el `sha256` del fichero crudo
(`7c77fbcfd2cc2785ef5a0df75c8925d69742429530df0fe990d27e73e28d76ac`), porque el informe viene en LF con un
único salto final. **No ejecuté sus sondas**: sus fixtures crean directorios con
`exist_ok=False` y él mismo advierte que repetirlas exige otra raíz de datos. Lo que sí
hice fue reproducir los tres hallazgos vivos **contra mi propio árbol**, con tests
propios; están en `tests/test_sala_lectura_plana_r2.py`.

**Lo que no es este acta.** No es una R2 sobre MI diff remediado. Mi remediación de la R1
y estos tres arreglos **no han pasado por una ronda adversarial**, y eso queda declarado
en el §6 del plan en vez de disimularlo con el número de ronda de este acta.

## 1. Informe recibido (literal, sin editar)

<!-- informe-literal:inicio:m9tz -->
HIGIENE: al abrir el workdir encontré `_stdout.log` además de `MANDATO.md`; no leí su contenido.

# Revisión adversarial R1 — sala de lectura plana

Objeto: `C:/t/rev_salaplana_102114_obj/`, base declarada `874111b`, head declarado `9ce7183`. Revisión del diff y de sus dependencias locales. No se proponen parches. La adjudicación corresponde al autor contra la fuente.

## Custodia y ejecución

Hashes SHA-256 de apertura, calculados antes de leer el código:

| Objeto | Apertura |
|---|---|
| `head/core/sala_lectura.py` | `de6bd11a49fe7e7ac944e798b86c27b8c410c180a982daf98a4a1584836a70e2` |
| `DIFF.patch` | `378b6e77499606ee760e26f4610f67a1900f156094b2405c80c0a5001cd2e785` |

Todas las escrituras deliberadas se hicieron en `C:/t/rev_salaplana_102114/`. Copié `head/` a `repro/` y el módulo de base a `base_sala.py`. No importé código desde el objeto archivado. El mandato específico prevalece sobre las instrucciones generales del proyecto de ejecutar desde el repositorio vivo o actualizar su estado: no se realizaron esas operaciones.

Intérprete empleado: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`, abreviado como `PY` en los comandos siguientes. Entorno: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, `CASOS_ROOT=C:/t/rev_salaplana_102114/casos_default`. Los `--basetemp` de pytest son relativos y resuelven dentro del workdir.

Las sondas usan `CatalogEntry`, `save_catalog`, `load_catalog`, `_nombre_canonico`, `_bundle_map` y `poblar_sala_lectura` reales de la copia. Solo sustituyen la resolución `caso_path` para apuntar al expediente sintético. Los bundles utilizan `GdocuDocInfo` y el detector real, sin conexión al CRM. Los hashes normales son SHA-256 de los bytes de cada documento. La sonda de prefijos usa valores sintéticos declarados; la de fallo de copia inyecta un `OSError` explícito.

Evidencia reproducible conservada:

- `r1_probes.py` y `probes.jsonl`: vacíos/None, dos corridas, reordenación, deduplicación, fuente ausente, bundles, migración ordinaria, error de copia y prefijos iguales. Comando desde el workdir: `PY r1_probes.py`. Salida final: `ALL_PROBES_CONFIRMED`; código 0.
- `r1_extra.py` y `extra.jsonl`: migración con solapamiento y cambio de representante duplicado. Comando: `PY r1_extra.py`. Salida final: `EXTRA_PROBES_CONFIRMED`; código 0.
- Las sondas crean directorios nuevos con `exist_ok=False`: para repetirlas, utilizar otra copia de trabajo o cambiar su raíz de datos, sin ejecutarlas sobre el objeto.
- `r1_mutations.py`, `mutations.jsonl` y `mutation_*.txt`: controles de sensibilidad de los tests, alterando exclusivamente la copia y restaurándola al terminar.
- `lectores_nombre_canonico.txt`: barrido literal de referencias en `head/`, incluidos archivos ocultos. `rg` no estaba instalado; se utilizó `Get-ChildItem -Recurse -File -Force | Select-String -SimpleMatch 'nombre_canonico'`.

## H-01 — El borrado de la ruta anterior elimina destinos de otras entradas

**Severidad: ALTA.** **Anclaje:** `head/core/sala_lectura.py:793`, `:818`, `:823` y `:826–835`.

**Por qué es un defecto.** `ocupadas` comienza vacía en cada corrida. El primer documento obtiene el nombre sin sufijo y los posteriores los discriminados. Un SHA estable no convierte en estable esa elección del primer ocupante. Además, `old.unlink()` no comprueba si otra entrada ya ha recibido ese destino en la corrida actual. La combinación produce pérdida de una copia de lectura y un catálogo que declara una ruta inexistente, sin error.

**Comprobación 1: cambiar el orden.** Sonda `reorder`, `PY r1_probes.py`. Dos documentos con bytes `A` y `B`, fecha `2026-03-17`, tipo `00. FOTOS`, descripción `Fotografia` y extensión `.pdf`. Sus SHA comienzan por `559aea` y `df7e70`. Sea `N = Sala lectura/2026-03-17_foto_fotografia.pdf`:

1. Primera corrida `[A,B]`: A ocupa `N`; B ocupa `N__df7e70` (sufijo antes de `.pdf`). Dos ficheros correctos.
2. Otra corrida con el mismo orden: `SKIP_UNCHANGED: 2`; disco y rutas idénticos.
3. Cambiar solo el orden a `[B,A]`: B borra su destino discriminado anterior y copia B sobre `N`. A recibe el nombre discriminado `N__559aea`, pero antes borra su antigua ruta `N`, que ahora contiene B.
4. Salida: `MOVED: 2`; queda solamente el fichero de A. El catálogo persiste B → `N`, aunque `N` no existe. La sonda devuelve `missing: ["B"]`.
5. Una corrida adicional, ya sin cambiar el orden, devuelve `COPY: 1, SKIP_UNCHANGED: 1` y repone B desde el original. Por tanto, tampoco es una operación idempotente para ese estado de entrada: aplicar una segunda vez cambia el conjunto de ficheros.

La sonda `bundle_reorder` reproduce el mismo defecto entre dos adjuntos: `SKIP_UNCHANGED: 1, MOVED: 2`, con la cabecera intacta y B ausente de `ordinario/adjuntos/`.

**Comprobación 2: migrar sin reordenar.** Sonda `migration_overlap`, `PY r1_extra.py`, ejecutada en Windows. Se puebla primero con el código de base. La cabecera CRM H se llama `Manual.pdf`; su bundle se denomina `manual`. Otro documento A tiene fuente `manual`. Ambos producen el mismo nombre canónico N. Orden constante `[H,A,B]`, siendo B el adjunto:

- Antes: H en `Sala lectura/CRM/manual/N`; A en `Sala lectura/Manual/N`.
- Head copia H a `Sala lectura/manual/N`. En este sistema `manual` y `Manual` designan la misma carpeta, por lo que ocupa la ruta antigua de A.
- Al migrar A a `Sala lectura/N`, `old.unlink()` borra H. Resultado: `MOVED: 3`, `missing: ["H"]`.
- Repetir con el mismo catálogo y `crm_docs` repone H: `COPY: 1, SKIP_UNCHANGED: 2`.

Esta segunda reproducción nace directamente de quitar la carpeta por fuente. Los originales de las sondas permanecen disponibles; la pérdida descrita es la de la copia de lectura, no una eliminación de `00_Input`.

## H-02 — Los hashes vacíos siguen permitiendo sobrescrituras

**Severidad: ALTA.** **Anclaje:** `head/core/sala_lectura.py:773–784`; interacción con `:796` y `:836`.

**Por qué es un defecto.** La ocupación se almacena como `hash_ or ""`, pero se compara con el valor original de `hash_`. Dos hashes vacíos se tratan como el mismo documento. Al ser falsos, tampoco pasan por la deduplicación de `vistos_hash`: se copian ambos al mismo destino. El caso vacío es admitido por `CatalogEntry` (`core/catalogo_documental.py:42`, valor por defecto) y por el cargador; no depende de inventar dos SHA iguales para contenidos distintos.

**Cómo lo comprobé.** `PY r1_probes.py`, sondas `empty`, `none`, `none_empty`, `empty_none` y `suffix_empty`, todas con fuentes existentes y contenidos diferentes:

| Hashes, en orden | Ficheros finales | Resultado |
|---|---:|---|
| `"", ""` | 1 | Ambas rutas son N; queda B. `COPY: 2`. |
| `None, None` | 2 | N y `N__sin_hash`. No colisionan entre sí. |
| `None, ""` | 1 | Ambas rutas son N; queda B. |
| `"", None` | 2 | N y `N__sin_hash`. |
| SHA válido, `"", ""` | 2 | Los dos vacíos comparten `N__sin_hash`; el último sobrescribe al anterior. `COPY: 3`. |

Las segundas corridas mantienen esos resultados, incluso los incorrectos, y devuelven `SKIP_UNCHANGED` por cada entrada. Comprobar existencia sin contenido no descubre la sobrescritura.

En `bundle_empty`, una cabecera con SHA válido y dos adjuntos distintos con hash vacío dejan solo dos ficheros en total: cabecera y último adjunto. Los dos adjuntos persisten exactamente la misma ruta. `bundle_none` conserva tres ficheros. Por tanto, no se generaliza incorrectamente el fallo de `""` a toda pareja de `None`.

## H-03 — Las entradas saltadas dejan rutas sin reservar que se reasignan a otro documento

**Severidad: ALTA.** **Anclaje:** `head/core/sala_lectura.py:793–802`, `:818` y `:839`.

**Por qué es un defecto.** Los saltos `SKIP_DEDUP` y `MISSING_SRC` ocurren antes de reservar el destino anterior. Sin embargo, las entradas saltadas conservan `ruta_sala_lectura` al guardarse el catálogo. El nuevo asignador puede dar esa ruta a un documento de hash diferente. La discriminación protege únicamente lo que ha atravesado el asignador en esa corrida, no todas las referencias persistidas.

**Cómo lo comprobé.** `PY r1_probes.py`:

- Sonda `dedup`: A y D tienen los mismos bytes/hash; A y B comparten nombre canónico, mientras D tiene descripción `Otra`. Primera corrida `[A,D,B]`: A → N, D sin ruta por deduplicación, B → `N__df7e70`. Segunda `[D,B,A]`: D copia A a otra ruta; B ocupa N; A se salta por hash y conserva N. Salida: `COPY: 1, MOVED: 1, SKIP_DEDUP: 1`. El catálogo contiene **A y B, de hashes diferentes, apuntando a N**, cuyo contenido es B. No es una pareja hipotética de SHA colisionados.
- Sonda `missing_src`: primera corrida normal `[A,B]`; después se elimina únicamente el original sintético A para simular un origen ausente. Al repetir, A se salta y B toma N. Salida: `MISSING_SRC: 1, MOVED: 1`; ambas entradas apuntan a N y solo quedan bytes B en la sala. Se pierde incluso la copia conservada de A, aunque la función había detectado que no podía recuperarla del origen.

El salto por hash ya existía en base; la interacción aquí demostrada con la reasignación de nombres discriminados corresponde al cambio. Distinto caso, también medido en `dedup_orphan`: cambiar el representante de dos duplicados con nombres distintos puede conservar dos copias; ese comportamiento es anterior al diff y no se cuenta como una regresión nueva.

## H-04 — La migración deja la estructura antigua de fuentes

**Severidad: BAJA.** **Anclaje:** `head/core/sala_lectura.py:826–834`.

**Por qué es un defecto.** La migración elimina ficheros individuales y crea sus nuevos padres, pero nunca retira los directorios antiguos vacíos. Un expediente que ya estaba poblado no cumple el resultado de «sin carpeta por fuente», aunque los documentos que se procesan correctamente sí terminen en el layout nuevo. No se atribuye pérdida documental a una carpeta vacía.

**Cómo lo comprobé.** Sonda `migration`, `PY r1_probes.py`: cinco entradas, incluyendo un bundle y dos parejas que se sobrescribían en base. Base deja tres ficheros; head devuelve `MOVED: 5`, recupera los cinco desde `00_Input` y no deja ninguna ruta del catálogo sin fichero. Subsisten, vacíos:

```text
Sala lectura/Manual
Sala lectura/CRM
Sala lectura/CRM/ordinario
Sala lectura/CRM/ordinario/adjuntos
```

No quedaron ficheros antiguos huérfanos en esa reproducción completa. Por lectura, el alcance no es una limpieza global: un fichero no referenciado en el catálogo queda intacto, y una entrada saltada antes de `old.unlink()` conserva su copia y ruta antiguas. El caso de solapamiento destructivo durante la migración está separado en H-01.

## H-05 — Se debilitó el test de parada por residuo

**Severidad: MEDIA.** **Anclaje:** `head/tests/test_sala_lectura.py:331`.

**Por qué es un defecto.** La aserción anterior exigía que no existiera `Sala lectura/Drive E&V`. La nueva exige únicamente que no haya un `*.pdf` directamente en `Sala lectura`. Una ejecución que escribe el PDF ambiguo en la antigua subcarpeta y luego declara que se ha detenido pasa ahora. También deja de detectar la mera creación de aquella carpeta. Los otros dos asertos del test solo comprueban el resumen devuelto.

**Cómo lo comprobé.** `PY r1_mutations.py`: mutación confinada a la copia que, en la rama de residuo de `organizar`, crea `Sala lectura/Drive E&V/ambiguo.pdf` y mantiene el retorno original. Se ejecuta el mismo test con la aserción nueva y con la antigua. Resultados registrados en la sección de tests. La mutación es una sonda de sensibilidad, no un parche propuesto.

## Respuesta a §3.1 — Discriminación completa

**No.** H-02 construye parejas que se pisan incluso en la primera corrida; H-03 construye rutas iguales persistidas para hashes distintos mediante los saltos. `vistos_hash` solo incluye hashes verdaderos y solo después de procesar una fuente existente.

Para entradas procesadas con SHA distintos y nombres de ruta exactos, el bucle sí resuelve también la coincidencia del prefijo de seis caracteres: la sonda `prefix_collision` obtiene `doc.pdf`, `doc__aaaaaa.pdf` y `doc__aaaaaa_2.pdf`. No considero que compartir los seis caracteres baste para refutar el algoritmo: el contador cubre ese caso.

La misma tabla `ocupadas` cubre documentos planos, cabeceras y adjuntos, y compara rutas completas. Una cabecera y un adjunto con el mismo basename no chocan si sus directorios son diferentes; `bundle_valid` lo comprueba. Si varios bundles comparten un slug, sus destinos de ficheros siguen pasando por esa tabla; compartir carpeta y distinguir documentos son propiedades diferentes.

Hay además una limitación **preexistente**, comprobada al ejecutar `bundle_empty` y `bundle_none`: `_bundle_map` indexa por hash (`:755`), de modo que dos adjuntos sin hash comparten el último registro de rol/orden. Ambos reciben `orden_en_bundle=2`, incluso cuando `None` permite conservar los dos ficheros. El diff no introdujo esa indexación y `_sin_colision` no la corrige. Las cabeceras y adjuntos con hash válido conservan en la sonda sus relaciones y órdenes.

## Respuesta a §3.2 — Idempotencia

**Con orden, fuentes y `crm_docs` constantes, sobre una sala recién poblada sin solapamientos anteriores**, las sondas planas y de bundles dejan el mismo conjunto de ficheros y las mismas rutas en la segunda corrida. Esto también ocurre con los vacíos que ya perdieron contenido: estabilidad no equivale a corrección.

**No existe una garantía general entre corridas.** Cambiar el orden cambia quién obtiene el nombre sin sufijo. H-01 acredita rutas reasignadas y una copia borrada; la siguiente corrida cambia otra vez el conjunto de ficheros al repararlo. La migración `migration_overlap` muestra el incumplimiento incluso sin reordenar. H-03 documenta cómo cambiar el representante deduplicado permite rutas incorrectas.

## Respuesta a §3.3 — Traza de pérdida documental

**Sí**, `old.unlink()` puede borrar el único destino de otra entrada y persistir una ruta inexistente: H-01 ofrece dos secuencias ejecutadas sin fallos de E/S. H-03 acredita que también se puede sustituir el contenido bajo una referencia conservada.

Se comprobó además un riesgo **anterior al diff**, activado masivamente por la migración: borrar antes de copiar. Sonda `copy_failure`: poblar un documento con base, ejecutar head e inyectar `OSError('simulated copy failure')` en `shutil.copy2`. El destino viejo se borra, no se crea el nuevo y no se llega a `save_catalog`; el catálogo persistido conserva la ruta vieja inexistente. Resultado: `files: {}`, `missing: ["A"]`. Se verificó el error inyectado, no un fallo real de disco. No se presenta como una novedad de `_sin_colision`.

## Respuesta a §3.4 — Lectores de `nombre_canonico`

**No encuentro una incompatibilidad nueva demostrada con los lectores del módulo.** Antes se persistía el basename producido por `_nombre_canonico`; ahora se persiste el basename final, incluido el discriminante (`:819`). Para una entrada procesada, sigue siendo el componente final de `ruta_sala_lectura`. `_nombre_canonico` (`:718–724`) reconstruye el candidato desde fecha, tipo, descripción/nombre original y extensión; no lee el campo persistido. Por ello no se van acumulando sufijos al repetir.

Resultado del barrido de `head/`, separando lectores efectivos y homónimos:

| Lugar | Uso comprobado |
|---|---|
| `core/catalogo_documental.py:50,80–105,117–126` | Declaración y carga/serialización genérica; `build_catalog` conserva la entrada por hash. No interpreta la forma del basename. |
| `core/sala_lectura.py:803,819` | Construcción del candidato y escritura del campo. No hay lector del atributo persistido en el módulo. |
| `core/sala_lectura.py:294–335,626–698` | Los MD se resuelven por ruta original y hash; los índices enlazan originales y MD, no `nombre_canonico`. |
| `tests/test_sala_lectura.py:47,361` | Lecturas del atributo: valor inicial `None` y presencia tras poblar bundles. Las llamadas al helper `_nombre_canonico` no leen el atributo persistido. |
| `.claude/skills/organizar-sala-lectura/scripts/indices_desde_manifiesto.py:34,45` | Lee el campo homónimo de filas del manifiesto; allí puede contener subcarpetas. |
| `.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py:46–79,146` | Lee nombres/rutas de filas del manifiesto para cobertura, colisiones, padres y hashes. |
| `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:274,323–355` | Lee campos de filas/planes; otras referencias producen nombres nuevos. |
| `.claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py:74` | Lee del manifiesto y escribe catálogo; es otro escritor del campo, no un consumidor de la salida de `poblar`. |
| `scripts/redate_whatsapp_anexos.py:98–140` | Lee y reescribe la columna del manifiesto. |
| `manifiesto_parser.py`, `copiar_manifiesto_rclone.py` y tests de esos helpers | Esquema/nomenclatura, diagnósticos o comprobaciones sobre manifiestos; no lectores del atributo producido por `poblar`. |

Existe una diferencia previa entre el nombre de catálogo producido por la skill y el producido por este motor en bundles: el primero puede incluir la subruta. No he encontrado una conexión de lectura que convierta el nuevo sufijo de este diff en un fallo de esos helpers. No se confunde ese homónimo con una dependencia probada.

## Respuesta a §3.5 — Migración del layout

La migración ordinaria ejecutada elimina las copias antiguas referenciadas, repone documentos antes sobrescritos y actualiza sus rutas. Quedan los directorios de fuente y de bundles vacíos, H-04. No recorre el árbol para gestionar ficheros ajenos al catálogo. Con entradas saltadas pueden coexistir los dos layouts; con solapamientos entre el nuevo bundle y un antiguo directorio de fuente puede faltar un documento, H-01. En consecuencia, el cambio no garantiza una migración completa ni inocua de cualquier sala existente.

## Respuesta a §3.6 — Tests existentes y nuevos

Los cinco cambios en pruebas existentes no son todos reemplazos literales de `assert`: algunos cambian la ruta usada por los asertos que siguen. Evaluación uno por uno:

| Test y línea de head | Dictamen |
|---|---|
| `test_poblar_sala_lectura_copia_idempotente`, `:255–265` | Conserva la comprobación de una copia con bytes correctos, original intacto y segunda corrida sin duplicar para su caso de un documento. Se adapta la raíz al nuevo layout; no probaba colisiones antes ni las prueba ahora. |
| `test_poblar_con_bundles_crm`, `:302–310` | Conserva un bundle, carpeta de adjuntos, dos PDFs y parent_id. Al contar todos los directorios de la sala, podría detectar más directorios indebidos que contando solo CRM. No se debilita para su fixture recién creada. |
| `test_poblar_sin_crm_docs_degrada_a_plano`, `:319–320` | Conserva que el documento de su fixture queda en el nivel plano previsto cuando no se aportan `crm_docs`. Cambia el nivel previsto conforme al nuevo contrato. El `any` ya era una comprobación de existencia, no de ausencia de toda subcarpeta. |
| `test_cli_organizar_se_detiene_con_residuo`, `:331` | **Más débil**: H-05; ignora PDFs anidados y directorios creados. |
| `test_organizar_completo_sin_residuo`, `:342` | Conserva para su fixture la presencia de al menos un PDF tras organizar y la del índice comprobada en el aserto anterior. La raíz cambia conforme al layout nuevo; sigue sin comprobar bytes ni exactitud del catálogo. |

Los dos tests nuevos **sí pueden ponerse rojos**. No son tautologías:

- `test_poblar_deja_la_sala_plana_sin_subcarpeta_por_fuente` (`:868–888`) detecta que vuelvan las carpetas de fuente al crear una sala nueva. La igualdad entre PDFs directos y recursivos se acompaña de `len == 2`, por lo que no pasa vacíamente si no se copia nada. Deja pasar la migración que conserva carpetas antiguas de H-04: nunca parte de una sala existente. Tampoco comprueba bytes ni rutas del catálogo de esos PDFs, ni extensiones distintas de PDF.
- `test_poblar_no_pisa_dos_documentos_con_el_mismo_nombre_canonico` (`:891–922`) detecta la sobrescritura de la pareja JPEG con SHA válidos de su fixture: comprueba cantidad, ambos contenidos y dos rutas distintas. Deja pasar H-01/H-03, porque solo hace una corrida y no cambia el orden, y H-02, porque sus hashes están poblados. No prueba colisiones entre adjuntos ni el contador para prefijos SHA iguales.

Ejecución inicial de todo el módulo, desde `repro/`:

```text
PY -m pytest tests/test_sala_lectura.py -p no:cacheprovider --basetemp ../pt1 -q
..............................................                           [100%]
Código de salida: 0 (46 pruebas).
```

Controles ejecutados por `PY r1_mutations.py` y `PY r1_mutations.py --residue-only`. Cada subproceso usa `PY -m pytest <nodeids> -p no:cacheprovider --basetemp ../ptm_<sonda> -o addopts= -q --tb=short`; los comandos y salidas completos están en `mutations.jsonl` y `residue_mutations.jsonl`.

| Código sometido a los tests | Tests | Salida real | Código |
|---|---|---|---:|
| Head sin cambios | Los dos nuevos | `2 passed in 17.87s` | 0 |
| Reintroducir fuente en los destinos, conservando discriminador | Los dos nuevos | `1 failed, 1 passed in 18.49s`; falla sala plana, `hay PDFs anidados` | 1 |
| Omitir la llamada a `_sin_colision`, conservando layout plano | Los dos nuevos | `1 failed, 1 passed in 14.67s`; falla colisión, `assert 1 == 2` | 1 |
| Escribir el PDF bajo `Drive E&V` en la rama de residuo | Aserción nueva | `1 passed in 10.45s` | 0 |
| La misma mutación | Aserción antigua | `1 failed in 9.09s`; falla `assert not ...exists()` | 1 |

El primer lanzamiento del harness se detuvo antes de preparar la mutación de residuo porque su sustitución literal no contemplaba los finales CRLF. Se corrigió únicamente el harness y se ejecutaron los dos controles pendientes con `--residue-only`; no fue un fallo de producción ni se reemplazó por una conjetura. El `finally` restauró los bytes de la copia en ambos lanzamientos. SHA-256 del módulo restaurado: `de6bd11a49fe7e7ac944e798b86c27b8c410c180a982daf98a4a1584836a70e2`.

## Cierre de custodia

Al cerrar se volvió a ejecutar `Get-FileHash -Algorithm SHA256` sobre los dos objetos, con estos resultados:

| Objeto | Cierre | Comparación |
|---|---|---|
| `head/core/sala_lectura.py` | `de6bd11a49fe7e7ac944e798b86c27b8c410c180a982daf98a4a1584836a70e2` | Igual a apertura |
| `DIFF.patch` | `378b6e77499606ee760e26f4610f67a1900f156094b2405c80c0a5001cd2e785` | Igual a apertura |

No se escribió en `base/`, `head/` ni `DIFF.patch`. Los hashes acreditan la igualdad de los dos objetos exigidos; no se presentan como un inventario criptográfico de todo el árbol. El informe se entrega en UTF-8 sin BOM, con LF y un único salto final; su SHA-256 se devuelve por separado.

## SIN VERIFICAR

1. No se ejecutó la suite completa del repositorio ni servicios externos. La revisión no acredita integración general con CRM/Drive ni todos los módulos ajenos al diff.
2. No se reprodujo el expediente real de 32 documentos/15 ficheros descrito por el autor: no fue aportado. Las conclusiones proceden de fixtures sintéticas reproducibles, no de esa medición.
3. No se ensayaron interrupciones de proceso, concurrencia, permisos o fallos reales de almacenamiento. El error de copia consignado fue inyectado; no se extrapola a una medición física de disco.
4. No se realizó una prueba exhaustiva de todos los nombres, equivalencias de rutas y sistemas de archivos. Sí se ejecutó el solapamiento `Manual`/`manual` en el Windows disponible y el caso de prefijos iguales del asignador.
5. `_stdout.log` no se leyó por el mandato de higiene. Su contenido no aporta evidencia a esta revisión.

VEREDICTO: NO-SHIP
<!-- informe-literal:fin:m9tz -->

## 2. Evidencia verificada por el autor

- **Los dos `sha256` de apertura y cierre** que declara el informe son iguales entre sí, y
  el del informe coincide con el que la sesión hermana declaró al pasármelo.
- **Su H-01, la mitad del solapamiento por capitalización, reproducida en mi árbol**: una
  ruta vieja que solo difiere en mayúsculas no la reconocía mi barrera
  `prev not in destinos_nuevos`, que comparaba cadenas. Test
  `test_una_ruta_vieja_que_solo_difiere_en_MAYUSCULAS_no_se_borra`.
- **Su H-02, hashes vacíos, reproducido en mi árbol**: mi `reservadas` guardaba
  `hash or ""` como dueño, así que dos filas sin hash eran el mismo dueño. Tests
  `test_una_fila_sin_hash_no_toma_la_ruta_reservada_por_otra_sin_hash` y
  `test_clave_dueno_distingue_filas_sin_hash_y_agrupa_las_deduplicadas` — el segundo fija
  que arreglar eso **no puede** romper el dedup, que sí necesita compartir dueño.
- **Su extra de «borrar antes de copiar», reproducido inyectando el fallo**: el
  `old.unlink()` iba antes del `copy2`. Test
  `test_un_fallo_de_copia_no_deja_la_copia_vieja_borrada`, con su control positivo de que
  la migración normal sigue retirando la copia vieja.
- **Su H-01 por reordenación y su H-03 por saltos: ya cubiertos** por la remediación de la
  R1 (asignación por hash, y las filas excluidas reservan su ruta). Se comprobó contra la
  fuente antes de darlos por cubiertos, no por fecha.
- **Su H-04**: coincide con lo que mi poda ya hace, y su medición
  (`Sala lectura/Manual`, `CRM`, `CRM/ordinario`, `CRM/ordinario/adjuntos` vacíos tras
  migrar) es la confirmación en vivo de que la poda hacía falta.
- **Su H-05** es una corrección sobre su propio trabajo, y **valía para mí**: el mismo
  aserto de parada por residuo que yo también había debilitado. Ya estaba restaurado por
  la R1; su aviso me hizo revisar los otros cuatro con la mutación en la mano, y dos
  `any(...)` —débiles ya antes del diff— quedan reforzados.
