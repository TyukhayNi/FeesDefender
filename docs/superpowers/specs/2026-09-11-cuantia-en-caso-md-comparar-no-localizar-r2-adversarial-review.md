---
tipo: revision-adversarial
objeto: "diff b59bb49..335a7b0 — update_meta, la cuantía en _caso.md comparando (MEJORAS #227)"
objeto_rev: "1"
commit: 335a7b0
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: cuan227r2
sha256_informe: ae1405151eac7b23657e94119d47ca8062540989ea2427b18c4c21371700b715
adjudicado_en: docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-design.md §11
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# Acta de revisión adversarial R2 — `update_meta`, sobre el diff

- **Objeto revisado:** diff `b59bb49..335a7b0` — `core/case_manager.py`, `scripts/abrir_caso.py`, sus tests y el diseño
- **Ronda:** R2 de 2 (presupuesto agotado)
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` sin `.git`, solo lectura
- **Informe recibido:** 2026-09-11, `C:/t/rev227-r2-1720/wd/INFORME.md`, 56715 bytes
- **Hallazgos:** 9 nuevos — 1 ALTO, 5 MEDIOS, 3 BAJOS; **9 confirmados, 0 refutados** — más el dictamen de las 9 remediaciones de la R1
- **Remediado en:** `docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-design.md` §11

**Por qué existe esta acta.** Yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**.

**Las dos cosas que devolvió y que yo no tenía.**

1. **Un ALTO que destruye una nota del letrado.** Yo había escrito, textualmente, que la frontera
   del frontmatter «no es una heurística de contenido, es un delimitador». **Lo era.** Ante un
   frontmatter vacío (`---` y `---` seguidos) el regex que comparto con `read_md` no puede casar el
   cierre inmediato y **salta al siguiente `---` del fichero**, tragándose el cuerpo. Reproducido:
   una nota que estaba en el cuerpo entraba como YAML y desaparecía al serializar.
2. **La suite estaba ROJA en mi rama y yo no lo sabía**, porque corrí los módulos tocados y no la
   suite. El censo de escrituras fuera de la costura subía de 91 a 94 y su trinquete solo baja.

**Y se le pidió el trabajo que casi nunca se pide:** dictaminar si cada una de sus nueve
remediaciones de la R1 era real, cosmética o incompleta. Veredicto: **cuatro REALES y cinco
INCOMPLETAS**.

**Custodia.** Dos árboles `git archive` sin `.git`; su propio informe de R1 entregado en el workdir
con su `sha256` para el trabajo B. Directorio de ronda con nombre irrepetible.

**`sha256` del `INFORME.md` original:** `ae1405151eac7b23657e94119d47ca8062540989ea2427b18c4c21371700b715`.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:cuan227r2 -->
# Revisión adversarial R2 de 2 — `update_meta`, diff `b59bb49` → `335a7b0`

## Apertura, higiene y alcance

- SHA-256 de `head/core/case_manager.py` al abrir: `b1327e207f98fd70870cc15829ba9bc4804012a081b88efb8e5c0e623f9fa468`.
- SHA-256 de `INFORME_R1.md` al abrir: `6836121c99d22aa81d79183b3b4a67fbe979c846b5d67ffc9f745e644e75d745`. **Coincide exactamente con el mandato.**
- Inventario inicial del workdir: `MANDATO.md`, `INFORME_R1.md` y **`_stdout.log`**. Este último era ajeno: **no lo leí**. La excepción de higiene queda declarada; no se utilizó como evidencia.
- Todas las escrituras de esta revisión van a `C:/t/rev227-r2-1720/wd`. `src/` es mi copia de `head/`; ejecuciones y mutaciones se hacen allí o sobre muestras de `evidencia/`. No escribí en `base/` ni `head/`, no hice `git add`, commits ni cambios en sistemas externos. No delegué a Antigravity ni a subagentes.
- Las anclas de este informe son **relativas a `head/`**, salvo indicación expresa. Abrevio **D** = `docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-design.md`; **T** = `tests/test_caso_md_update_meta.py`; **TC** = `tests/test_abrir_caso_cli.py`. Por tanto, `D:79`, `T:246` y `TC:1047` son anclas a ficheros, no a secciones del informe.
- Las copias no incluyen `.git`: identidad genealógica de los commits y de los PR citados **SIN VERIFICAR**. El contraste material queda en `evidencia/diff.txt` y `evidencia/manifest.json`. La comparación AST confirma que las funciones preexistentes de `case_manager.py`, incluidos generador, fusión y registradores, no cambian; se añaden las cinco funciones indicadas y las constantes/imports. En la CLI cambian `_alta_crm` y la firma de `main`.

**Dictamen:** la promesa de seguridad física no se cumple para todas las entradas. Hay una entrada concreta que pierde una nota del cuerpo y devuelve `conservado` (H2-01). La copia literal de un sufijo mal delimitado no prueba conservación del cuerpo. Separadamente, se corrigen de verdad la pérdida de sangría/espacios finales del sufijo normal y la fusión que revertía `update_pull_state`; esas mejoras no se niegan por los defectos restantes.

## Método y evidencia ejecutada

Intérprete: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`, con `-B`/`PYTHONDONTWRITEBYTECODE=1`. `rg` no está disponible; se usaron búsquedas de PowerShell y análisis Python. Temporales pytest relativos al workdir, caché pytest desactivada y raíces de casos/registro/TEMP dentro del workdir.

`sondas.py` importa los módulos completos de la copia; no reimplementa `update_meta`. Sustituye el localizador por un mapa de carpetas sintéticas, fija el reloj y usa los lectores, escritores y registradores reales. Para la CLI sustituye las fronteras CRM por dobles y captura mensajes. Un audit hook de las sondas prohíbe escrituras fuera del workdir, conexiones y subprocesos. Hay entradas/salidas físicas `before.bin` / `after.bin` por escenario y resultados en `evidencia/resultados.json`. La corrida válida final se hace después de restaurar y comprobar la copia; los intentos de ajuste del arnés no son resultados del objeto.

La primera ejecución pytest, lanzada con cwd `src`, tuvo **77 errores de setup por acceso denegado al basetemp**; no eran fallos del código. Con cwd del workdir y basetemp relativo allí, **77/77 pasaron** (`pytest-baseline1.xml`). Se amplió a nueve módulos que contienen los usos directos de la pieza, la CLI y registradores: **213/213 pasaron** (`evidencia/baseline.xml`). La colección global encontró **5.338 tests**. Las corridas globales y su comparación se consignan al cerrar este informe.

`mutaciones.py` conserva/restaura los bytes de los dos módulos en `finally`. Evidencia por mutante: `evidencia/mut_*.log`, sus JUnit y `evidencia/mutaciones.json`. No se alteró ningún test del autor para ponerlo verde.

No se ejecutaron las semillas 777/31337. El mandato las excluye por indisponibilidad declarada de `pytest-randomly`: **SIN VERIFICAR**. Una inspección posterior de los entry points del intérprete sí listó `randomly`; no utilicé esa discrepancia para contravenir la orden. Las corridas válidas deshabilitan la carga automática de plugins y no equivalen a las dos semillas.

## Hallazgos nuevos

### H2-01 — ALTO — El delimitador salta un frontmatter vacío y destruye una nota del cuerpo

**Anclas:** `core/case_manager.py:418`, `:504`, `:510`, `:525`, `:550`, `:564`; la misma forma defectuosa existe en `core/utils.py:255`. Promesas en `D:79`, `D:93` y `core/case_manager.py:474`.

**Qué falla.** La regex necesita un `\n` después de la apertura y otro antes del cierre; no pueden ser el mismo carácter. Por eso no reconoce el frontmatter vacío de dos líneas `---\n---\n`. Si encuentra un tercer separador más adelante, puede tomar el segundo `---` como inicio de documento YAML dentro de la captura y el tercero como cierre. `safe_load` acepta esa captura. Texto humano del cuerpo se convierte en frontmatter y sus comentarios desaparecen al serializar.

**Escenario ejecutado**, fichero completo `evidencia/empty_fm_swallow/before.bin`:

```text
---
---
meta: {case_id: X, titulo: T}
# NOTA DEL LETRADO NO BORRAR
---
Texto libre
```

El frontmatter físico es vacío; el cuerpo comienza en `meta:`. La llamada `update_meta(..., cuantia=42.0)` debería abstenerse por ausencia de `meta` en ese frontmatter. Sin embargo, la captura llega hasta el offset 71, encuentra `meta` en el cuerpo y devuelve `cuerpo="conservado"`, `frontmatter=["cuantia"]`. La salida es:

```text
---
meta:
  case_id: X
  titulo: T
  cuantia: 42.0
  actualizado_en: '2027-01-01T00:00:00+01:00'
---

Texto libre
```

La nota desapareció. No depende de carreras, normalización de CRLF, llamadas al CRM ni edición del generador. **El sufijo desde `m.end()` sí permanece idéntico**, pero comienza después del texto que se acaba de destruir. Por tanto no es un contraejemplo a la concatenación literal; es un contraejemplo a que esa concatenación preserve el cuerpo de `_caso.md`. La excepción documentada de comentarios *del frontmatter* no cubre un comentario que estaba en el cuerpo.

**Qué lo arreglaría.** Delimitar apertura y **primer cierre de línea** independientemente del contenido del YAML, admitir el frontmatter vacío sin buscar otro cierre y preservar el tramo posterior a ese cierre. Ante frontmatter vacío/sin `meta`, devolver `sin tocar`. Probar la frontera con un oráculo independiente de `_FM_RE_BYTES`, incluyendo este fichero completo. Compartir una regex con el lector no convierte su error en una garantía.

### H2-02 — MEDIO — También en la rama conservada se borran blancos físicos posteriores al cierre

**Anclas:** `core/case_manager.py:418`, `:525`, `:550`, `:564`; `D:79`, `D:86`; oráculo común en `T:49`.

**Qué falla.** El `\s*` posterior al `---` consume todos los blancos hasta el último salto disponible, incluidos saltos, espacios y tabuladores del comienzo del cuerpo. La nueva cabecera los sustituye por la separación fija del serializador. `D:86` declara ese precio para la rama canónica, pero la pérdida también sucede con un cuerpo **no canónico**.

**Escenarios ejecutados.** Frontmatter con `meta` válida + `\n  \nNOTA\n` después de su separación normal: devuelve `conservado`, mantiene `NOTA`, pero pierde el prefijo `\n  \n`. Con cuerpo solo `  \n\t\n`, el sufijo elegido por la regex es vacío y esos bytes desaparecen. Véanse `noncanonical_prefix` y `white_only`. El prefijo adicional del escenario canónico `prefix` también desaparece. El test que compara sufijos delimitados por la misma regex queda verde por construcción.

**Qué lo arreglaría.** Fijar la frontera al final de la línea del cierre, separar explícitamente cualquier separador propiedad del escritor y conservar los bytes restantes. Si se decide normalizar blancos, dejar de prometer identidad física de ese tramo y declarar el precio también en la rama conservada. Esa relajación no satisface la promesa fuerte del mandato.

### H2-03 — MEDIO — La lista blanca no preserva todos los valores YAML ajenos

**Anclas:** `core/case_manager.py:510`, `:540`, `:541`, `:550`; `core/utils.py:259`; promesa `D:224`, `D:251`.

**Qué falla.** `deepcopy` protege el objeto en memoria, pero no hace reversible el ciclo `safe_load` → `safe_dump`. Los tipos YAML `!!omap` y `!!pairs`, admitidos por `safe_load`, se cargan como listas de tuplas. `safe_dump` los emite como secuencias genéricas de secuencias; al volver a cargar son listas de listas. Se pierde la etiqueta y cambia el valor Python de una clave ajena. Esto no es la excepción ya documentada para comentarios y duplicados.

**Escenario ejecutado.** En `yaml_types`, la clave ajena `ordenado: !!omap [{z: 1}, {a: 2}]` pasa de `[('z', 1), ('a', 2)]` a `[['z', 1], ['a', 2]]`; `pares: !!pairs` cambia de la misma forma. Las comparaciones antes/después de esas dos claves dan `false`. Cuantía es el único argumento de negocio. El mismo serializador actúa sobre claves ajenas dentro de `meta`, incluidos valores anómalos de `sudespacho_expedientes`; no se reutiliza la fusión, pero existe esta otra vía de cambio.

**Qué lo arreglaría.** Delimitar y validar los tipos admitidos antes de escribir, absteniéndose ante un roundtrip que cambie valores ajenos; o usar una representación/serializador que preserve sus etiquetas y estructura. Añadir pruebas de tipos y alias, no solo igualdad sobre los valores ordinarios que construye `ensure_case`.

### H2-04 — MEDIO — El llamante anuncia escritura cuando `update_meta` ha rechazado escribir

**Anclas:** `scripts/abrir_caso.py:773`, `:776`, `:785`, `:786`; estados de retorno en `core/case_manager.py:506`, `:517`, `:529`. Falta de verificación del registro en `scripts/abrir_caso.py:760`, `:769` y retornos tolerantes en `core/case_manager.py:609`, `:613`.

**Qué falla.** La condición `informe["cuerpo"] != "reescrito"` agrupa `conservado` y `sin tocar`. En ambos imprime «cuantía escrita en el frontmatter». En el segundo no se escribió ninguna clave. El motivo posterior puede decir literalmente «no se escribe nada», dejando un mensaje contradictorio. Los cuatro desenlaces basados en excepciones no cubren este rechazo normal.

**Escenario ejecutado.** La sonda de integración `cli_no_touch` hace llegar un índice con BOM a la llamada real de `update_meta`, después del doble de registro. Se recibe `sin tocar`, pero se imprime `OK CRM id=9999` y «cuantía escrita ... no se escribe nada». Es una prueba de la frontera entre los dos métodos, no una demostración de que un alta ordinaria produzca BOM espontáneamente. El estado puede aparecer por una modificación entre pasos o por un futuro registrador; el retorno forma parte de la API presente y debe manejarse.

Además, el escenario R1 de un registrador que retorna sin registrar sigue sin comprobarse: ausencia de excepción se toma como éxito. `cli_register_noop` deja el vínculo ausente y obtiene `OK CRM`; el caso de desaparición del índice se reproduce con el registrador real en la ampliación de las sondas. No atribuyo a una ejecución ordinaria de `register_expediente` sobre un índice sano un no-op indebido.

**Qué lo arreglaría.** Tratar los tres estados explícitamente y verificar las claves efectivamente escritas. `sin tocar` debe informar que la cuantía local sigue pendiente, con acción de recuperación. Para el registro, retorno que distinga persistencia de no-op o lectura posterior del vínculo. Añadir pruebas de rechazo sin excepción y de registro que no persiste.

### H2-05 — MEDIO — Dos oráculos de conservación dejan pasar pérdidas y cambios fuera de alcance

**Anclas:** `T:246`, `T:353`, `T:354`; afirmaciones de control positivo `D:468`, `D:490`, `D:494`.

**Qué falla y escenarios ejecutados.**

1. `test_NO_revierte_lo_que_update_pull_state_escribio` compara el espejo **después contra otra lectura después** (`T:246`). Ese aserto no conoce el espejo previo. Mutación en `update_meta`: tras `meta_nuevo.update(campos)`, copiar la lista superior a `meta_nuevo["sudespacho_expedientes"]`. Cambia `old` por `new` en el espejo, fuera de lista blanca. **Los 213 tests relacionados pasan**, incluido el test dedicado. El escenario del índice ordinario del test de claves tampoco diverge, por lo que no lo mata.
2. El delta de líneas basado en pertenencia ignora orden y multiplicidad. Mutación de `core/case_manager.py:557`: aplicar `.replace("\n\n", "\n", 1)` al cuerpo generado antes de escribir. Borra el blanco después del título, pero todavía quedan otras líneas vacías. Las listas `quitadas`/`puestas` solo muestran la cuantía. **Los 213 tests relacionados pasan**, incluida la idempotencia: la segunda llamada conserva el cuerpo ahora no canónico.

**Qué lo arreglaría.** Capturar ambas listas antes de actuar y compararlas después; usar una comparación secuencial exacta del cuerpo esperado mediante sustitución controlada de la línea permitida. Un `Counter` mejora multiplicidad, pero todavía no acredita el orden: hace falta secuencia. Mantener estos dos mutantes entre los controles positivos. La cifra de 13 mutantes muertos no demuestra completitud.

### H2-06 — BAJO — El contrato de entrada confunde construir un dataclass con validar sus tipos

**Anclas:** `core/case_manager.py:421`, `:429`, `:519`, `:530`, `:176`; `D:230`, `D:242`.

**Qué falla.** Las anotaciones no se validan al construir `CaseMeta`. Con `cuantia: no-numero`, `case_id: null`, `titulo: []` o `sudespacho_expedientes` mapa, el constructor funciona y se escribe. Con `sudespacho_expedientes: 42`, también funciona el constructor, pero `_seccion_expedientes` lanza `TypeError` fuera del bloque capturado. El fichero queda intacto, pero falta el informe prometido para un índice no interpretable. La tabla tampoco enumera expresamente `fm` no mapa ni cuerpo no UTF-8.

**Escenarios:** `type_cuantia_str`, `type_case_id_NoneType`, `type_titulo_list`, `type_sudespacho_expedientes_dict` escriben; `type_sudespacho_expedientes_int` lanza `'int' object is not iterable`, sin escribir. No afirmo que los primeros cuatro casos destruyan una nota por sí solos: demuestran que no hay validación de tipos. Tampoco la tabla actual dice expresamente «cuantía debe ser numérica»; esa exigencia quedó sin contratar, no implementada a escondidas.

**Qué lo arreglaría.** Publicar tipos/estructuras admitidos y validarlos antes de comparar o serializar; devolver un resultado de abstención coherente para datos persistidos inválidos. Distinguir validación de claves, de tipos y fallos de E/S; no envolver indiscriminadamente todos los errores en un éxito.

### H2-07 — BAJO — El diagnóstico de campos rechazados sigue recomendando un actualizador inexistente

**Anclas:** `core/case_manager.py:396`, `:397`, `:398`, `:491`, `:944`; corrección declarada en `D:146`.

**Escenario ejecutado.** Alta ya existente con cliente/órgano pendientes: `ensure_case(cliente='Cliente', organo='Organo', titulo='Nuevo titulo')` los deja en `null`, `null`, `T`. `update_meta(cliente='Cliente')` rechaza con «su hogar es ensure_case». El operador sigue recibiendo precisamente la indicación que H-03 de R1 consideraba engañosa para actualizar. `late_fields` reproduce ambos pasos. El nuevo párrafo del diseño reconoce la limitación; `_HOGAR_DE` no la distingue.

**Qué lo arreglaría.** El diagnóstico debe decir «solo al crear mediante ensure_case; sin API posterior» para esos campos. Registrar el hueco en una entrada de backlog identificable, o señalar la existente. No ampliar por ello la lista blanca de #227.

### H2-08 — BAJO — La documentación revisada aún describe otra implementación y controles que no existen

**Anclas:** `D:81`, `D:97`, `D:105`, `D:443`, `D:455`, `D:459`; `PLAN.md:45`, `PLAN.md:93`.

**Qué falla.** El pseudocódigo de §2.3 vuelve a leer mediante `read_text`, que ya normalizó saltos antes de escribir con `newline=""`; no conserva CRLF del cuerpo. La rama canónica real no usa `write_md` ni la convención de la plataforma: usa bytes y la detección de CRLF del frontmatter. D:443 exige que el espejo sea `extrajudiciales`, cuando conservarlo exige que siga siendo el valor viejo. D:455 anuncia un aserto de primera salida que el test de idempotencia ya no contiene; D:459 exige atravesar la escritura en el reintento, mientras TC:1047 exige que no haya escrituras. `PLAN.md:45` da #227 por completa con PR #351 y `PLAN.md:93` la mantiene de vuelta al diseño como siguiente.

**Escenario.** Ejecutar literalmente el pseudocódigo D:97 sobre frontmatter LF y cuerpo CRLF no canónico normaliza el cuerpo a LF. El código de producción evita ese error, pero el documento afirma que ese mismo pseudocódigo es su remedio. Los controles contradictorios se comprueban leyendo los asertos reales y con los mutantes de H2-05.

**Qué lo arreglaría.** Reescribir los apartados normativos conforme al código y a la frontera que finalmente se apruebe, y mantener un único estado de ciclo de vida. No corregir solo la adjudicación dejando la regla ejecutable anterior en el cuerpo del diseño. La identidad histórica del PR #351 no se adjudica sin git.

### H2-09 — MEDIO — El diff deja rojos dos guards de la suite: censo 91 → 94

**Anclas:** `core/case_manager.py:445`, `:446`, `:450`; `tests/test_escritura_censo.py:125`, `:268`, `:281`.

**Qué falla.** El helper nuevo incorpora tres llamadas de escritura fuera de la costura (`write_bytes`, `os.replace`, `unlink`). El censo explícito permanece en 91. Los tests `test_el_censo_solo_baja` y `test_el_techo_no_esta_holgado` fallan en `head` sin mutaciones. No es una consecuencia de los 13 mutantes ni de `pytest-randomly`.

**Escenario ejecutado.** Tras corregir el cwd de ejecución, ambos tests fallan con total 94. `censo_base_head.py` llama al detector real del test contra las fuentes de ambas copias: **base 91**, **head 94**; solo cambia `core/case_manager.py`, de 9 a 12 llamadas. Identifica exactamente las tres líneas nuevas indicadas. Evidencia: `evidencia/censo_base_head.json` y `evidencia/failures_correct_cwd.log`. No atribuyo a este diff los otros cinco rojos por falta de `.git`/venv.

**Qué lo arreglaría.** Resolver la integración de esta escritura de protocolo con la política de la costura y su censo. Si se mantiene como deuda diferida, declararla y actualizar el contrato del censo conforme al procedimiento ya documentado por sus precedentes; no desactivar el guard, ocultar el productor o subir el número sin justificarlo. La suite del `head` congelado no está verde.

## Trabajo B — dictamen de las nueve remediaciones de R1

### H-01 — INCOMPLETA

Anclas: `core/case_manager.py:418`, `:525`, `:527`, `:549`, `:557`, `:564`.

Se reprodujeron las **cuatro variantes originales**, no solo las dos citadas por el autor:

1. Sangría inicial `    Nota como codigo\n`: **corregida**, sufijo idéntico (`indent`).
2. Nota final `Conservar  \n\n`: **corregida**, sufijo idéntico (`tail`).
3. Canónico LF/CRLF/CR: LF completo queda LF; CRLF completo queda CRLF. Frontmatter enteramente CR ya no se reconoce y la función **se abstiene**, conservando el fichero entero; no es una actualización exitosa. Con frontmatter LF y cuerpo CR o CRLF sí compara verdadero y convierte el cuerpo a LF; con frontmatter CRLF convierte a CRLF. Se ejecutó la matriz 3×3, también con notas. El contrato canónico ahora renuncia a los bytes, pero el doc no describe la política real de salida.
4. Canónico precedido de `\n  \n`: sigue comparando verdadero y pierde el prefijo. Se declara una parte del precio, pero no se cierra. La misma pérdida aparece ante una nota no canónica, fuera de la excepción declarada: H2-02. H2-01 muestra que la frontera tampoco se limita siempre a blancos.

La sustitución del tramo mejora dos casos de forma real. No cierra las cuatro variantes ni la promesa física completa.

### H-02 — REAL para los dos escenarios originales de fusión

Anclas: `core/case_manager.py:534`, `:540`, `:541`, `:544`, `:555`; registradores `:624`, `:1822`.

`pull_changed`: registro 10 con `element=old` → pull escribe `new` arriba → `update_meta` devuelve `reescrito`; arriba permanece `new` con `last_sync`, espejo permanece `old`. **Ambas listas son iguales a sus propios valores anteriores.**

`pull_added`: registro 10 → pull crea 20 solo arriba → actualización de cuantía devuelve `reescrito`; arriba conserva 10+20, espejo conserva solo 10. No incorpora el 20 al espejo ni al cuerpo y no reutiliza la fusión. El AST de la fusión preexistente permanece igual respecto de `base`.

El remedio concreto es real, aunque su test tiene la tautología de H2-05. **No significa que sea cierta la preservación universal de toda representación YAML:** H2-03 identifica otra vía, por serialización. En `evidencia/extra.json`, `omap_mirror` ejecuta el caso dentro de `meta.sudespacho_expedientes`: pasa de `[('id', 10)]` a `[['id', 10]]`. Es un límite distinto, no la reaparición de la fusión que se acaba de reproducir.

### H-03 — INCOMPLETA

Anclas: `D:146`, `core/case_manager.py:389`, `:396`, `:944`.

El escenario original sigue igual funcionalmente: `ensure_case` no repone cliente/órgano/título en un índice existente, y la lista blanca los rechaza. Mantener ese alcance era admisible en R1. La justificación se corrige en prosa, pero la ayuda ejecutable sigue indicando `ensure_case` sin «solo al crear» (`late_fields`, H2-07). El diff de `MEJORAS_FUTURAS.md` añade el cierre de #227 y la limitación de reintento; no aporta la tabla completa de propietarios ni una entrada identificada para estos campos tardíos. No doy por cumplido «va al backlog» solo porque el diseño lo diga.

### H-04 — REAL

Anclas: `scripts/abrir_caso.py:738`, `:773`, `:1005`, `:1241`; `TC:1050`.

Alta sin flag, con cero y con 500.5 recorren la frontera CRM en tres casos separados y el test pasa. El constructor recibe `0.0` cuando el flag es `None`; la escritura local se omite solo en esa ausencia. El camino original que propagaba `None` a la aritmética del DTO está cerrado en este llamante. No se hizo un alta real en el CRM. El test aún no exige la secuencia completa `[0.0, 0.0, 500.5]`: el mutante que envía siempre cero pasa ese test concreto, límite de prueba que no invalida el arreglo observado.

### H-05 — INCOMPLETA

Anclas: `scripts/abrir_caso.py:674`, `:750`, `:759`, `:775`, `:785`; `core/case_manager.py:609`, `:613`.

Los fallos por excepción de alta, registro e índice tienen mensajes separados; los tests correspondientes pasan. Se reprodujo registro correcto + `OSError` al actualizar: queda ID 9999 vinculado y cuantía local `null`. El reintento devuelve «CRM ya registrado», hace **cero altas remotas** y deja `null`. La llamada directa a `case_manager.update_meta` la repone a 10 sin editar a mano. Ese límite ya está declarado y el mensaje da la vía de reparación.

También se ejecutó la secuencia alta hecha + registro que lanza + reintento cuya búsqueda remota encuentra 9999: el segundo intento levanta `AbortarApertura(1)` y exige vincularlo, con **una sola llamada de creación remota en toda la secuencia** (`failed_register_retry_remote`). No es correcto afirmar que ese reintento necesariamente duplica.

El escenario original de registro que retorna normalmente sin persistir sigue sin verificación posterior. `real_register_missing_index` elimina el índice en el doble de alta remota y ejecuta el registrador real; con flag ausente termina en `OK CRM id=9999` aunque el índice no existe. Además, `sin tocar` se presenta como escritura exitosa, H2-04. El arreglo no es cosmético: mejora realmente las excepciones, pero no agota los estados ni satisface toda mi remediación original.

### H-06 — INCOMPLETA

Anclas: `T:215`, `T:246`, `T:326`, `T:333`, `T:353`, `TC:1025`, `TC:1047`.

Se fija el reloj y existe un nuevo oráculo sobre el delta. Es una mejora real. Se reprodujo el contramodelo original añadiendo `<!-- actualizado_en: sello -->` solo en la rama canónica: **el test de idempotencia pasa** y **el nuevo test del delta falla** (`evidencia/mutante_sello.json`). El escenario de la línea indebida queda detectado por el conjunto, aunque el docstring del test de idempotencia promete más que sus asertos. Restaurar el default CLI a `0.0` deja **verde el test de reintento** (ejecutado, `restore_default`), exactamente el otro escenario original: retorna antes de mirar el flag. Otros tests de alta nueva sí vigilan el default, por lo que no afirmo que sobreviva en toda la suite.

El espejo después/después es tautológico y el delta no cuenta repeticiones: sobreviven los dos mutantes de H2-05. La comprobación de hogares sí tiene un control positivo real: añadir `cuantia` superior pone rojo su test (`new_hogar`, ejecutado). La tabla de trece mutantes no acredita que todos sus oráculos hayan cerrado la propiedad.

### H-07 — REAL como corrección del alcance de la afirmación

Anclas: `D:311`, `D:316`, `D:318`, `D:321`; `streamlit_app.py:2689`; `.claude/skills/preparacion-audiencia-previa/references/flujo.md:10`.

Se reproduce el fichero contradictorio: con nota, `update_meta` conserva el cuerpo que dice pendiente y escribe la cuantía en frontmatter. El visor sigue leyendo el fichero entero y la skill sigue pidiendo cuantía sin fijar precedencia; esos consumidores no cambiaron. Lo corregido es la afirmación «no hay otro lector»: el diseño ahora los enumera y reconoce que no ven el aviso de consola. Ese era el error de alcance de H-07 y su rectificación es real. **No equivale a haber implementado un aviso persistente ni a corregir los consumidores.** La elección del modelo y el render visual efectivo no se ejecutaron: SIN VERIFICAR; no hay evidencia de un escrito real equivocado.

### H-08 — INCOMPLETA

Anclas: `core/case_manager.py:486`, `:496`, `:504`, `:510`, `:513`, `:516`, `:519`, `:527`, `:530`; `D:248`.

El filtrado admite `proyeccion_local` y las otras claves ajenas; no se reconstruye indiscriminadamente un índice ilegible. `meta={}`, `meta` lista/null, falta de campos requeridos, BOM, UTF-16 y bytes no UTF-8 quedan sin escribir; hay estados explícitos. Comentarios y duplicados continúan perdiéndose, pero ahora se declara su exclusión dentro del frontmatter.

Faltan tipos válidos y fronteras completas: un entero en expedientes lanza fuera de la captura; mapas/valores de tipo equivocado se aceptan; `!!omap` cambia de valor; el frontmatter vacío con YAML aparente en el cuerpo se transforma en un índice escrito (H2-01). El contrato nuevo cierra varios escenarios originales, no la clase «entrada que no se puede preservar».

### H-09 — REAL como precondición explícita; no como mecanismo de exclusión

Anclas: `core/case_manager.py:478`, `:479`, `:481`, `:570`; `D:403`, `D:408`; llamante `scripts/abrir_caso.py:1164`, `:1241`.

La intercalación dirigida original sigue destruyendo la nota: A lee canónico; antes del escritor atómico, B añade `NO BORRAR`; A reemplaza y la nota desaparece (`race`). No se ha cerrado la carrera con código.

**La declaración sí basta para la remediación que R1 permitía:** yo pedí expresar la garantía bajo exclusión vigente de todos los escritores si se mantenía la decisión de no exigir mutex. El docstring completo ahora incluye esa precondición; su primera frase aislada es absoluta, pero el contrato leído entero ya no lo es. No cuento como cosmética una reducción de alcance que mi propia R1 ofrecía explícitamente como solución. El llamante normal está lexicalmente dentro del mutex. Queda SIN VERIFICAR que todos los escritores reales cooperen o que el lease cubra cualquier intercalación real. El aviso de recuperación por llamada directa debería recordar esa precondición.

## Trabajo A — respuestas explícitas 1 a 15

### 1. Recorrido de `update_meta` y promesa de bytes

Recorrido por todos los bloques ejecutables (`core/case_manager.py`):

- `:484`: importa el localizador; `:486–494`: rechaza llamada vacía y claves no enumeradas antes de escribir.
- `:496–501`: localiza y exige índice; ausencia lanza `FileNotFoundError`.
- `:503–508`: lee bytes y busca el límite; sin coincidencia retorna `sin tocar`.
- `:509–514`: decodifica/carga YAML; errores YAML/Unicode y resultados no mapa se abstienen. `or {}` convierte resultados falsy en mapa vacío, sin autorizar escritura.
- `:515–523`: exige `meta` mapa y construye el dataclass filtrado; captura solo `TypeError` de esa construcción.
- `:525–530`: recorta por `m.end()`, exige UTF-8 para el cuerpo, normaliza CRLF/CR y compara con G. No se compara en bytes, pese al comentario `:378`.
- `:539–547`: fija reloj, copia el frontmatter, sustituye únicamente las claves pedidas en una copia superficial de `meta`, sella `actualizado_en` y actualiza el hogar superior de referencia si vino.
- `:549–552`: elige finales para la cabecera y serializa **todo** el frontmatter.
- `:554–561`: regenera si la igualdad fue cierta, aplica `strip` y final LF/CRLF.
- `:562–568`: concatena literalmente `cuerpo_bytes`; no lo recodifica ni normaliza.
- `:570–571`: reemplazo mediante temporal y devuelve el informe; errores de E/S se propagan.

**Respuesta precisa:** bajo exclusión y terminación normal, la línea 564 preserva siempre el sufijo capturado. No encontré una ruta que modifique bytes *dentro de ese sufijo* en la rama conservada. **No preserva siempre el cuerpo físico desde su cierre real**: H2-01 y H2-02 son contraejemplos ejecutados. Conservar el sufijo escogido por la misma regex que usa el test no refuta esos hallazgos.

BOM inicial: no reconoce la apertura y no escribe. BOM dentro del cuerpo: es un carácter adicional, no se elimina por UTF-8 ni por `_normalizar_saltos`; impide igualdad y queda en el sufijo. UTF-16 y bytes UTF-8 inválidos: abstención. Un encoding distinto cuyo contenido sea solo ASCII es indistinguible de UTF-8 y no aporta diferencia de bytes. CR sueltos en el cuerpo no canónico se conservan; frontmatter enteramente CR no coincide. Fichero vacío y `---\n---\n`: sin coincidencia, intactos. `---\n\n---\n`: YAML vacío sin `meta`, intacto. Frontmatter válido con `meta` y sin cuerpo: escribe la cabecera y añade su separación fija, con sufijo vacío; no inventa el cuerpo canónico. Si falta el salto final exigido al cierre, se abstiene.

### 2. ¿Delimitan lo mismo `_FM_RE_BYTES` y `_FM_RE`?

No. `core/utils.py:277` normaliza saltos al leer; el matcher byte exige LF real. `\s` en `str` reconoce blancos Unicode; en bytes, solo la clase ASCII. Se ejecutaron:

- `unicode_space`: U+00A0 + LF entre cierre y título. Ambos encuentran frontmatter; el matcher de texto consume el blanco Unicode y el de bytes lo deja en el cuerpo. Fronteras distintas, actualización conservadora en bytes.
- `close_nbsp`: cierre `---` + U+00A0 + LF. El lector de texto reconoce el frontmatter; el byte no coincide y `update_meta` no escribe.
- `close_cr` y frontmatter CR puro: el lector con saltos universales lo reconoce; el byte se abstiene.

La diferencia tiende aquí a abstención/conservación, no a borrar el U+00A0. El bug de frontmatter vacío de H2-01 **es común a ambos**. Comparar offsets numéricos de caracteres UTF-8 y bytes sin convertirlos no sería una prueba válida; las sondas comparan los sufijos normalizados o la existencia de coincidencia.

### 3. Saltos mixtos

`core/case_manager.py:549` mira el tramo capturado como cabecera, que incluso incluye los blancos tragados del comienzo físico del cuerpo. La rama conservada usa ese booleano solo para la nueva cabecera: el sufijo queda literalmente igual aunque el frontmatter sea LF y el cuerpo CRLF, o al revés. Esto está ejecutado en la matriz `notes_*`.

La rama canónica normaliza la comparación y después impone **a todo el cuerpo** LF si no encontró CRLF en ese tramo, o CRLF si encontró al menos uno (`:557–559`). Por tanto LF/CRLF mezclados y CR sueltos pierden su distribución original. No rompe el contrato **de contenido normalizado** que D:82 admite; sí rompe cualquier lectura de «solo cambian los bytes renderizados por el campo». Además D:83 habla de la plataforma, política que este código no usa.

### 4. Diferencias posibles cuando la comparación da verdadero

Anclas: generador `core/case_manager.py:187–216`, normalización `:434`, salida `:549–560`.

1. Cambia la representación renderizada de cuantía, incluso a `_(pendiente)_` al escribir `None`; con referencia CRM cambia/inserta/retira su línea completa según su verdad lógica. Pueden cambiar longitud y número de líneas si se admiten valores multilínea, porque no hay validación de esos tipos.
2. El frontmatter se vuelve a serializar entero: claves permitidas/sello, representación YAML, comentarios, duplicados, anclas/etiquetas, estilos y separadores. El detalle semántico está en 5–6.
3. Se pierden los blancos entre cierre y cuerpo absorbidos por la regex y se escribe la separación fija.
4. Todos los finales del cuerpo se convierten a la convención derivada de la cabecera; se pierde la distinción LF/CRLF/CR y su mezcla.
5. Se aplica `strip()` al nuevo G y se añade un salto final. Para el generador actual empieza siempre por `#` y termina por `- [[demanda]]\n`: con campos ordinarios esta operación no elimina texto adicional del cuerpo aceptado. Un cuerpo con espacios finales o saltos extra tras G no habría comparado verdadero. No atribuyo al `strip` actual pérdidas que esa precondición impide.
6. El reemplazo atómico crea otro fichero y cambia metadatos físicos como mtime; preservación de atributos/ACL, ADS y durabilidad no forma parte de lo comprobado. Se conserva la codificación UTF-8 de las cadenas aceptadas; un BOM inicial nunca llega a esta rama.

`actualizado_en` no se renderiza en G. No encontré un tercer campo ordinario que cambie espontáneamente en la cadena canónica. La igualdad demuestra igualdad de contenido del snapshot, **no autoría histórica** del texto.

### 5. ¿Puede cambiar claves del frontmatter fuera de las cuatro autorizadas?

Sí, en representación y en ciertos valores, H2-03. En mapas/listas/escalares ordinarios, la asignación explícita de `:540–547` solo cambia `meta.cuantia`/`meta.referencia_crm` pedidas, `meta.actualizado_en` y referencia superior si se pidió. No reconcilia otras claves. Nótese que `meta_nuevo=dict(meta_previo)` usa el objeto original, no la copia profunda: los hijos se comparten con el objeto cargado, aunque esta función no los muta explícitamente.

`safe_dump` cambia comentarios, comillas, estilos bloque/flujo, nombres de anclas y forma léxica de números/booleanos/fechas; expande merges YAML. `deepcopy` no evita eso. Los alias ordinarios entre dos claves superiores se conservaron como identidad compartida en `yaml_types`. Pero el escenario ejecutado `alias_cross` comparte una lista entre `shared` superior y `meta.ajena`: después pierde esa compartición porque se mezclan hijos copiados y originales; sus valores ordinarios sí permanecen iguales. No se promete una identidad de objetos/etiquetas estable con esta composición. Claves duplicadas y colisiones de resolución YAML 1.1 ya se colapsan al cargar; D:248 solo reconoce una parte de este precio.

### 6. Orden y tipos en el roundtrip

`core/utils.py:259–264` usa `sort_keys=False`. El orden de inserción de un dict cargado se mantiene; asignar a una clave existente no la mueve, y añadir una clave ausente la coloca al final. Esto se ejecutó: `order_equal=true`. No significa conservar el orden textual previo de merges, entradas duplicadas o conjuntos sin orden.

| Entrada | Resultado observado/semántica |
|---|---|
| `id: "10"` | Sigue siendo cadena, el dumper la cita para evitar convertirla a número. |
| `on: yes`, `no: off` sin comillas | `safe_load` YA los resuelve como claves/valores booleanos YAML 1.1; después se escriben `true`/`false`. No era un string Python que el dumper convirtiese después. Con `on`/`yes` juntos como claves puede haber colisión antes de escribir. |
| `cadena_yes: "yes"` | Sigue cadena; el dumper usa comillas protectoras. |
| `fecha: 2026-09-11` | Sigue `datetime.date`, con la misma fecha. |
| entero de 39 dígitos | Conserva el entero exacto de Python. |
| `null` / `None` | Sigue `None`, se serializa `null`. |
| `!!omap`, `!!pairs` | Se pierde la etiqueta y tuplas internas pasan a listas; H2-03. |
| ancla/alias ordinario en dos listas superiores | Conserva compartición en la muestra, con nombres de anclas regenerados. No garantiza grafos arbitrarios. |

No hay evidencia de que `safe_dump` convierta indiscriminadamente cadenas ordinarias entrecomilladas en booleanos o fechas. Confundir la resolución inicial con un cambio introducido al volcar sería un falso positivo.

### 7. Hogares superiores y control positivo

`_frontmatter_del_indice` (`core/case_manager.py:302`) produce `case_id`, `tipo`, `fase`, `fecha`, `estado`, `ciudad`, `referencia_crm`, `sudespacho_expedientes`, `drive`, `meta`. Intersección con `{cuantia, referencia_crm}`: **solo referencia_crm**. La enumeración actual está completa.

El test `T:260` **sí puede ponerse rojo**: mutación real que añade `"cuantia": meta.cuantia` al retorno → **1 fallo**, exige enumerarla. Su límite: intersecta nombres iguales; no descubriría un hogar futuro bajo otro nombre como `importe`, ni valida los valores de `_HOGARES_SUPERIORES`. Completo hoy no significa descubrimiento automático de cualquier mapeo futuro.

### 8. Tabla de abstenciones y tipos raros

La tabla D:235 no es exhaustiva. El código contempla además `fm` no mapa y cuerpo no UTF-8; E/S y fallos del render pueden lanzar sin informe. `safe_load` de `null`, `false`, `0`, `[]` acaba en `{}` por `or {}`, después se abstiene por falta de `meta`; lista no vacía, escalar verdadero, número y string se abstienen por no mapa. Todas esas muestras quedaron intactas. El diagnóstico cambia, no la seguridad de esas ramas.

Construir el dataclass no valida anotaciones. Cuantía string se renderiza como string; expedientes dict se itera por claves string y se filtra a sección vacía; entero truthy lanza fuera de la captura. Se escriben varios tipos inválidos según el dominio, pero el código no había contratado ese dominio: H2-06. Sí hay escritura donde la tabla exige abstenerse si se respeta la frontera física: H2-01 tiene frontmatter vacío/sin `meta`, y encuentra una `meta` falsa en el cuerpo. A la inversa, frontmatter CR o cierre con blanco Unicode puede ser legible por `read_md` pero `update_meta` se abstiene.

### 9. Temporales, hilos, merge y plugin

`core/case_manager.py:443` usa `._caso.<pid>.upd.tmp`; `:327` usa `._caso.<pid>.tmp`: **no colisionan entre estas dos funciones**. Dos llamadas al primer helper para el mismo índice y proceso sí comparten nombre. En `same_process_threads`, dos hilos reales sincronizados con eventos ejecutan el helper real: A escribe temporal, B lo sobrescribe, A reemplaza y devuelve éxito habiendo publicado **B**, B recibe `FileNotFoundError`. La exclusión de todos los escritores evita el caso; el nombre por sí solo no ofrece seguridad entre hilos. Esta intercalación dirigida no se confunde con una prueba de exclusión distribuida. Un temporal único por invocación evitaría la colisión, pero no resolvería por sí mismo la actualización perdida del índice.

El nombre **sí casa con** `MERGE_EXCLUSIONS` (`core/config.py:405`), `._caso.*.tmp`; `repository_checkout.esta_excluido` usa `fnmatch` (`core/repository_checkout.py:258`), y devuelve verdadero en la sonda. También está cubierto por el **patrón declarado** de `PROTOCOL_EDIT` (`plugins/expedientes_xl/tiers.py:39`).

Hay una salvedad preexistente y ejecutada: `tiers.check_write` compara `nombre in PROTOCOL_EDIT` por igualdad literal (`plugins/expedientes_xl/tiers.py:107`), sin aplicar glob. Rechaza sobrescribir **tanto** `._caso.123.tmp` como `._caso.123.upd.tmp`; crear un fichero nuevo se permite en `:104`. No es un olvido de añadir el nuevo patrón ni una regresión del diff. El test de espejo puede verificar la constante sin verificar su consumo. Remedio para ese defecto preexistente: `any(fnmatch(nombre, pat) ...)` y test de la operación real; no hace falta añadir otra exclusión.

### 10. Desenlaces de `_alta_crm`

Los cuatro describen solo el tramo que ya llegó a intentar crear en `scripts/abrir_caso.py:750`: alta lanza; alta bien/registro lanza; ambos bien/update lanza; éxito. Aun allí faltan registro que retorna sin persistir y `update_meta` que devuelve `sin tocar` (H2-04); también existe éxito de alta/registro **sin flag**, que retorna sin actualizar (`:773`), y éxito con cuerpo conservado que necesita su aviso.

Los otros caminos pedidos **sí tienen mensajes**, no los invento como silenciosos: modo distinto de API (`:664–666`) dice CRM omitido; confirmación declinada (`:741–743`) dice omitido por usuario; `BLOQUEAR` (`:709–718`) y `VINCULAR` (`:720–732`) imprimen motivo y levantan `AbortarApertura`; el entrypoint lo traduce fuera del mutex (`:1247–1254`). `ya registrado` también imprime (`:674–679`). La cuantía no se persiste por esos caminos. No todos sus mensajes explicitan esa consecuencia local, pero ninguno de esos tres ejemplos es un quinto alta remota completada y silenciada. Interrupciones de terminal/errores inesperados antes del try no forman parte de los cuatro desenlaces de negocio.

### 11. Reintento y recuperación sin editar a mano

Confirmado en código y ejecutado: la guarda `:674–679` retorna antes de `:776`, también si se reintenta con cuantía explícita. `--force` no salta esa guarda. `ensure_case` tampoco repone cuantía en índices existentes (`core/case_manager.py:944`).

**Sí hay otra vía:** invocar la API `case_manager.update_meta(case_id, cuantia=...)`, como el propio aviso `scripts/abrir_caso.py:782` indica. La sonda la ejecuta tras un índice fallido y un reintento estéril: pasa de `null` a 10 sin alta remota adicional. Debe hacerse bajo la exclusión exigida por su contrato. No encontré otro entrypoint de producción que la invoque: la única llamada es `_alta_crm`. En un cuerpo con notas esa reparación actualiza el frontmatter y declara la conservación; no promete reponer la línea del cuerpo.

### 12. Todos los usos de `cuantia` en la CLI

`scripts/abrir_caso.py:1005`: flag `float | None`, default `None` → `:1241`: pasa ese valor a `_alta_crm` → `:657`: lo recibe. `:738` traduce `None` a `0.0` únicamente para `crm_payload`; `:740` imprime la cuantía del DTO. `:773` retorna si es `None`; `:776` llama al actualizador únicamente cuando no es `None`. El resto son comentarios o mensajes (`:735`, `:771`, `:780`, `:786`).

`None` se propaga hasta la guarda local deliberadamente, **no hasta el DTO CRM ni a `update_meta` desde esta CLI**. Cero explícito no satisface `is None` y se escribe. No encontré otro uso de `cuantia` en el fichero que el cambio haya dejado sin adaptar.

### 13. Los 18 tests nuevos del core y los 7 nuevos de CLI, uno por uno

«Sí» significa que acredita su escenario concreto, no que prueba una propiedad universal. En los parciales se especifica qué mutación podría dejarlos verdes indebidamente. Las mutaciones marcadas **ejecutada** tienen log/JUnit; las demás son deducciones de los asertos, no ejecuciones reclamadas.

| Test y ancla | Dictamen del oráculo |
|---|---|
| `test_reescribe_el_cuerpo_cuando_es_canonico`, T:70 | **Sí**, comprueba estado, motivo, cuantía en cuerpo y frontmatter. No acredita ausencia de otros cambios: borrar un blanco también lo deja verde (**ejecutada**). |
| `test_con_una_nota_del_letrado_el_cuerpo_queda_IDENTICO_EN_BYTES`, T:83 | **Parcial para la frontera; sí para el sufijo de la muestra.** La nota y sus blancos están dentro del cuerpo; no prueba sangría inicial ni espacios en EOF. Usa la regex productiva para delimitar ambos lados. Un `strip()+salto` del cuerpo completo puede dejar esta muestra igual, aunque destruya los bordes en otras entradas; tragarse el prefijo de blancos sigue verde con el código actual. |
| `test_un_cuerpo_en_CRLF_sigue_en_CRLF`, T:107 | **Sí a igualdad de bytes de la muestra; premisa de formato defectuosa en Windows.** `ensure_case` ya escribe CRLF; sustituir todo LF por CRLF crea CRCRLF. El test sigue siendo útil contra normalización, pero no certifica por sí mismo un cuerpo puramente CRLF ni la rama canónica. |
| `test_un_solo_espacio_de_mas_ya_no_es_canonico`, T:121 | **Sí**, controla un espacio al final de `## Partes` y compara el sufijo. No prueba todos los blancos ni la frontera; una excepción que tolere blancos solo al principio/EOF seguiría verde. |
| `test_un_indice_sin_frontmatter_NO_SE_ESCRIBE`, T:134 | **Sí para el índice de la muestra.** El comentario dice «ÁRBOL», pero solo compara hash del fichero: crear un temporal/otro archivo sin cambiar `_caso.md` no lo haría rojo. No prueba vacío, BOM ni cierre ambiguo. |
| `test_un_frontmatter_con_YAML_invalido_NO_SE_ESCRIBE`, T:148 | **Sí** para un corchete sin cerrar. Compara hash y estado. No acredita todos los errores YAML ni ausencia de efectos en el resto del árbol. |
| `test_un_meta_que_no_reconstruye_CaseMeta_NO_SE_ESCRIBE`, T:159 | **Sí** para falta de `case_id`; **parcial** como contrato de tipos. Aceptar cualquier tipo en expedientes mantiene este test verde, y el entero hoy lanza fuera de la captura. |
| `test_una_clave_ajena_en_meta_no_impide_comparar`, T:175 | **Sí**: exige regeneración y preservación de la clave ajena específica. No certifica todas las demás claves; eliminarlas salvo esa podría dejarlo verde. |
| `test_solo_toca_sus_claves_del_frontmatter`, T:194 | **Sí** para valores ordinarios de su fixture y reloj cambiado. **Parcial** frente a orden, tipos especiales y diferencia entre clave ausente/valor null: usa dicts y `.get`. Suprimir una clave ajena con valor `None` no aparece en `cambiadas`. No compara cuerpos. |
| `test_NO_revierte_lo_que_update_pull_state_escribio`, T:228 | **Sí** para la lista superior; **no** para el espejo. T:246 se compara consigo mismo. Copiar superior sobre espejo pasa (**ejecutada**, también los 213). |
| `test_referencia_crm_llega_a_sus_DOS_hogares`, T:250 | **Sí** para ambos hogares del frontmatter. No exige la línea del cuerpo: forzar conservación cuando solo se actualiza referencia puede dejarlo verde. |
| `test_los_hogares_superiores_estan_todos_enumerados`, T:260 | **Sí** para nombres iguales y lista blanca actual. Añadir `cuantia` superior lo mata (**ejecutada**). Un hogar renombrado `importe` se le escapa. |
| `test_un_campo_fuera_de_la_lista_blanca_se_rechaza_SIN_ESCRIBIR`, T:275 | **Sí** para `direccion`, su diagnóstico y hash. Una whitelist que admita indebidamente solo `cliente` seguiría pasando este test. |
| `test_llamar_sin_campos_es_un_error_del_llamante`, T:287 | **Sí**, exige ValueError y hash idéntico. Como los otros hashes no detecta escrituras transitorias/restauradas ni archivos extra. |
| `test_una_clave_con_None_SE_ESCRIBE_y_una_ausente_no_se_toca`, T:295 | **Sí** para las dos operaciones sobre frontmatter. Su docstring menciona cero, pero no lo prueba aquí. No detectaría dejar atrasado el cuerpo después de `None`. |
| `test_un_caso_que_no_existe_levanta`, T:308 | **Sí** al nombre. No prueba caso existente sin índice ni integridad del árbol. |
| `test_dos_llamadas_iguales_dejan_el_fichero_IDENTICO`, T:317 | **Sí** a idempotencia con reloj fijo; **no** a la afirmación adicional del docstring sobre primera salida. Borrar un blanco vuelve la primera salida no canónica y la segunda la conserva: pasa (**ejecutada**). Un añadido indebido estable también puede pasar este test aislado. |
| `test_al_reescribir_SOLO_cambia_lo_que_renderiza_el_campo`, T:336 | **No acredita el SOLO.** Ignora orden y multiplicidad. Borrar un blanco pasa (**ejecutada**); también permutar líneas existentes conserva sus conjuntos. |
| `test_cli_la_cuantia_del_flag_llega_a_caso_md`, TC:1006 | **Sí**: llega a frontmatter y cuerpo, exit 0. No valida cuantía enviada al CRM ni otros cambios. |
| `test_cli_sin_el_flag_la_cuantia_no_se_inventa`, TC:1015 | **Sí** para alta nueva sin flag. Un mutante que altere campos ajenos o llame a update con `cuantia=None` manteniendo null podría pasar: no prueba ausencia de llamada. |
| `test_cli_repetir_SIN_el_flag_no_pisa_la_cuantia_ya_escrita`, TC:1022 | **Sí** a conservación por guarda; **no** a controlar el default. Exige justamente cero escrituras. Restaurar default `0.0` pasa (**ejecutada**). El comentario TC:1025 invierte la objeción de R1, no la resuelve. |
| `test_cli_el_payload_del_CRM_recibe_un_numero_aunque_no_venga_el_flag`, TC:1050 | **Sí** a valor float por los DTO observados y primer cero. **Parcial**: no exige tres observaciones ni valores de cero explícito/500.5. Enviar siempre `0.0` pasa (**ejecutada**). |
| `test_cli_el_alta_hecha_y_el_registro_fallido_NO_dicen_que_fallo_el_alta`, TC:1074 | **Sí** al mensaje para la excepción de registro simulada. No comprueba registro realmente ausente ni ausencia de llamadas posteriores; imprimir el aviso y continuar podría pasar este test aislado. |
| `test_cli_el_indice_fallido_es_su_PROPIO_desenlace`, TC:1093 | **Sí** al aviso de OSError y explicación del reintento. No comprueba el vínculo persistido ni el ID en estado real: basa esa premisa en `OK CRM`. Omitir el registro y conservar esos mensajes podría dejar este test verde. |
| `test_cli_si_el_cuerpo_se_CONSERVA_el_aviso_llega_a_la_pantalla`, TC:1108 | **Sí** al cableado del estado `conservado` y motivo. Declara honestamente que usa un informe falso, no una nota real. No prueba `sin tocar`; silenciar solo ese estado pasa (**ejecutada**, también los 213). |

### 14. Mutante obvio ausente y alcance de su ejecución

Dos mutantes dirigidos adicionales sobrevivieron a los **213 tests relacionados**:

```python
# En update_meta, rama canonica:
cuerpo_nuevo = _cuerpo_del_indice(meta_new).replace("\n\n", "\n", 1).strip() + "\n"
```

```python
# Tras meta_nuevo.update(campos):
meta_nuevo["sudespacho_expedientes"] = copy.deepcopy(fm.get("sudespacho_expedientes", []))
```

El primero pierde formato no renderizado por los campos autorizados y el segundo cambia un espejo ajeno. También sobrevive limitar el aviso del llamante exclusivamente a `conservado`, omitiendo `sin tocar`. Los tests aislados de reintento y payload dejan pasar respectivamente default `0.0` y payload siempre cero. Añadir un hogar superior no enumerado **sí muere**. Esto refuta que los controles existentes agoten la propiedad, sin necesidad de negar que el autor matase sus trece mutantes concretos. La reproducción exacta de esos trece, cuyo arnés no se aportó en el diff, queda SIN VERIFICAR.

La corrida global del mutante que borra un blanco y su comparación con la línea base se describen al cierre. No se confunde una supervivencia en selección con «ningún test del repositorio» sin comprobar el resto.

### 15. Líneas repetidas en el oráculo

No es correcto. `l not in despues` responde si existe al menos una copia, no cuántas ni dónde. Ejemplo: antes `['A', '', '', 'B']`, después `['A', '', 'B']`; no detecta ninguna línea quitada. Tampoco detecta permutar `A` y `B`. La plantilla ya trae muchas líneas vacías: no hace falta inventar un caso remoto. El mutante ejecutado de H2-05 elimina una de ellas y el test pasa.

El oráculo adecuado debe comparar secuencias completas contra una transformación independiente y estrictamente acotada del cuerpo anterior, o un diff que conserve posiciones/multiplicidad y permita solo el cambio esperado. Para referencia CRM debe contemplar aparición/desaparición de su línea, sin convertirlo en permiso de reordenar las demás.

## Inventario de lo NO cubierto y límites

1. Semillas 777/31337: SIN VERIFICAR; no se intentaron. La colección global no equivale a ejecución, y la ejecución sin esas semillas no equivale a su requisito.
2. Los trece mutantes originales exactos del autor: SIN VERIFICAR. Se ejecutaron los adicionales identificados, con resultados propios, sin inferir cuáles probó realmente el autor.
3. CRM, Drive, rclone y expedientes reales: no se consultaron ni modificaron. Altas y duplicados remotos son dobles de prueba. No se verifica la política efectiva del tenant ni la recuperación operativa completa.
4. Genealogía git, pertenencia a `origin/main`, PR #338/#344/#351 y tiempos de integración: SIN VERIFICAR. Solo se contrastó el contenido de las dos copias congeladas.
5. Concurrencia distribuida, expiración/renovación real de leases, cooperación de editores humanos, Drive y todos los escritores: SIN VERIFICAR. Las intercalaciones dirigidas demuestran ventanas, no certifican un mutex ni una frecuencia de fallo.
6. UI Streamlit real y ejecución de las skills jurídicas frente a frontmatter/cuerpo contradictorios: SIN VERIFICAR. Se leyeron sus consumidores y se produjo el fichero contradictorio, no un escrito judicial equivocado.
7. Corpus legacy y frecuencia práctica de entradas vacías, tags YAML, Unicode o finales mixtos: SIN VERIFICAR. Los contraejemplos son sintéticos y no se atribuyen a un caso real.
8. Exhaustividad formal de YAML, alias recursivos, todos los encodings, objetos arbitrarios pasados en `**campos` y todos los errores del sistema de archivos: SIN VERIFICAR. Se probaron clases concretas; no se afirma una prueba formal del parser.
9. Cortes de alimentación/proceso, disco lleno físico, durabilidad `fsync`, preservación de ADS/ACL/atributos, enlaces y junctions: SIN VERIFICAR. La escritura normal y las sustituciones de las sondas sí fueron físicas.
10. Seguridad general de `_actualizar_cuerpo` y otros escritores preexistentes: fuera del objeto. El fallo efectivo del carve-out se declara como preexistente; no se reabre su diseño entero ni se da por cerrado #184/#192.

## Cierre y ejecución global

La suite global se ejecutó dos veces sobre la copia: primero `head` sin modificar y después con **únicamente** el mutante que borra un blanco. Se usaron cuatro workers, sin plugin de aleatorización, con basetemp relativo dentro del workdir. JUnit: `evidencia/full_baseline.xml` y `evidencia/full_remove_blank.xml`.

| Ejecución | Aprobados | Fallos | Skipped | Xfail |
|---|---:|---:|---:|---:|
| Head sin modificar | 5.216 | 21 | 91 | 10 |
| Mutante `remove_one_blank` | 5.216 | 21 | 91 | 10 |

La comparación de JUnit por identidad de test da **el mismo conjunto de 21 fallos**, cero casos desaparecidos y cero fallos adicionales (`evidencia/global_comparison.json`). Los 21 se reejecutaron después con cwd `src` y basetemp `../...`: **14 pasan**, tanto sin mutante como con él. Los **7 restantes** son idénticos en ambas variantes: **2 fallos reales nuevos del censo** (H2-09), **3 por ausencia de `.git`** y **2 por ausencia del venv local esperado**. No se inventó un repo git ni un venv para maquillar esos resultados.

Resultado combinado, contando cada test una vez: **5.230 aprobados**, 2 fallos del diff, 5 casos no verificables en este archivo sin `.git`/venv, 91 skips y 10 xfails. **Ningún test ejecutable añadió un fallo por borrar ese blanco.** El mutante sobrevive a la comparación global disponible; no afirmo cobertura de los 101 casos omitidos/xfail ni de los 5 bloqueados por entorno, ni una suite global verde. Los otros mutantes supervivientes conservan el alcance declarado de 213 tests o test aislado.

Las sondas ampliadas (`sondas_extra.py`, `evidencia/extra.json`) terminaron con exit 0 sobre la copia restaurada y acreditan además registro real sin índice, cambio del espejo `!!omap`, pérdida de alias entre hogares, colisión dirigida de dos hilos y normalización del pseudocódigo del diseño. El contraste del censo con `base` terminó con exit 0 y total 91 frente a 94. Los scripts de mutación restauraron los bytes originales de los módulos; esa identidad se comprueba en el cierre.

La adjudicación corresponde a Claude contra la fuente. Esta ronda aporta una pérdida de nota reproducida en `head`, límites de remediaciones y mutantes supervivientes; no propone una tercera ronda automática ni volver a localizar líneas del cuerpo con heurísticas.

SHA-256 de `head/core/case_manager.py` al cerrar: `b1327e207f98fd70870cc15829ba9bc4804012a081b88efb8e5c0e623f9fa468`.
SHA-256 de `INFORME_R1.md` al cerrar: `6836121c99d22aa81d79183b3b4a67fbe979c846b5d67ffc9f745e644e75d745`.

NO-SHIP
<!-- informe-literal:fin:cuan227r2 -->

## 2. Evidencia verificada por mí, contra la fuente

**H2-01, reproducido con el fichero exacto del informe.** Salida de mi sonda:

```
_FM_RE_BYTES casa hasta el offset 77
captura = b'---\nmeta: {case_id: EV-H201, titulo: T}\n# NOTA DEL LETRADO NO BORRAR'
¿sobrevive la nota? **NO**
```

La captura llega al **tercer** `---`, así que la nota del cuerpo entra como YAML y desaparece.

**H2-02, reproducido.** Con `---\nmeta: …\n---\n\n  \nNOTA\n`, el `\n  \n` desaparecía: el `\s*`
del regex lo contaba como parte del frontmatter y la cabecera nueva lo sustituía.

**H2-09, reproducido y es el más vergonzoso porque lo tenía delante:**

```
tests/test_escritura_censo.py::test_el_censo_solo_baja      FAILED  (94 > 91)
tests/test_escritura_censo.py::test_el_techo_no_esta_holgado FAILED
```

Corrí `test_caso_md_update_meta.py`, `test_abrir_caso_cli.py` y tres módulos más, y **no la suite**.
Las dos semillas que sí corrí eran de la **otra** pieza de la sesión.

Los demás se comprobaron leyendo el código y con los mutantes: los dos de H2-05 sobreviven a mis
tests anteriores y mueren contra los remediados.

**Lo que el revisor declaró SIN VERIFICAR:** las dos semillas (su Python de sistema no trae
`pytest-randomly`), la genealogía del commit, y la identidad del PR #351 que yo había escrito en
`PLAN.md` — que en efecto estaba mal, porque ese número se lo llevó otra pieza.

## 3. Lo que esta acta NO cubre

**La remediación de esta R2 no ha pasado por ninguna ronda.** El presupuesto era de dos y está
agotado; el techo duro dice que la tercera la autoriza Nikolai, y **el 2026-09-11 decidió no
abrirla**: entra declarada **SIN VERIFICAR**. Lo que sí la acompaña es medición propia — 18
mutantes dirigidos, 18 muertos, incluido uno que restaura literalmente el regex compartido que
causó H2-01.
