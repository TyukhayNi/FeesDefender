---
tipo: revision-adversarial
objeto: "diseño c325723 — la cuantía llega a _caso.md comparando, no localizando (MEJORAS #227)"
objeto_rev: "1"
commit: c325723
ronda: "1"
revisor: Codex
veredicto: REQUIERE-REVISION
marcador_nonce: cuan227
sha256_informe: 6836121c99d22aa81d79183b3b4a67fbe979c846b5d67ffc9f745e644e75d745
adjudicado_en: docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-design.md §10
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# Acta de revisión adversarial R1 — la cuantía en `_caso.md`, comparando

- **Objeto revisado:** diseño `c325723` — el spec de `MEJORAS #227` por la vía (d)
- **Ronda:** R1 de 2 (la R2 va sobre el diff; presupuesto por radio de daño)
- **Revisor:** Codex (CLI 0.153.4), copia `git archive` sin `.git`, solo lectura
- **Informe recibido:** 2026-09-11, `C:/t/rev227-r1-1421/wd/INFORME.md`, 52614 bytes
- **Hallazgos:** 9 — 2 ALTOS, 6 MEDIOS, 1 BAJO; **9 confirmados, 0 refutados**
- **Remediado en:** `docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-design.md` §10

**Por qué existe esta acta.** Yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**.

**Qué tumbó el diseño, en una frase.** Los dos ALTOS son el mismo error mío en dos capas: enuncié
la garantía sobre **cadenas** y el fichero está hecho de **bytes**, y creí que una lista blanca de
argumentos acotaba lo que se **escribe**. El revisor lo ejecutó: la rama «conservada» pierde los
espacios finales de la nota del letrado y le cambia los finales de línea, y la fusión de
frontmatter que pensaba reutilizar **revierte** lo que `update_pull_state` acababa de escribir.

**Lo que NO hizo, y es correcto que no lo hiciera:** proponer volver a localizar líneas con
heurísticas. Su cierre lo dice expresamente.

**Custodia.** Árbol `git archive` sin `.git`, directorio de ronda con nombre irrepetible. El
revisor declaró en su primera línea el `_stdout.log` que encontró en su workdir —mi propio fichero
de salida— y dijo no haberlo leído. `sha256` del documento revisado coincidente al abrir y cerrar:
`fbb20a8dec74910b15a5ec7dc907589d211c396caf03c285bda77ca4c7882f56`.

**`sha256` del `INFORME.md` original:** `6836121c99d22aa81d79183b3b4a67fbe979c846b5d67ffc9f745e644e75d745`.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:cuan227 -->
sha256 del documento revisado: `fbb20a8dec74910b15a5ec7dc907589d211c396caf03c285bda77ca4c7882f56` — HIGIENE: el workdir contenía `MANDATO.md` y también `_stdout.log`; no leí `_stdout.log`.

# Revisión adversarial R1 de 2 — diseño de actualización de cuantía

## Higiene, objeto y método

El directorio no cumplía §0 por el fichero adicional indicado en la primera línea. No lo abrí ni lo utilicé como evidencia. Después de ese inventario creé únicamente artefactos propios dentro de `C:/t/rev227-r1-1421/wd`. No escribí en `obj/`, no importé código para ejecutarlo desde `obj/`, no utilicé git ni delegué a Antigravity ni a otros revisores. La instrucción específica de colocar el informe en `wd/`, fuera del repositorio revisado, concreta las preferencias globales; no hubo que resolverlas en sentido contrario.

Objeto: `docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-design.md`, en la copia `../obj`. Todas las anclas de código de este informe son relativas a esa copia. En las respuestas llamo **D** a ese documento; `D:53` identifica su línea 53. El commit `c325723` es la identificación proporcionada por el mandato: genealogía **SIN VERIFICAR**, al no disponer de `.git`.

Interpreto la totalidad del mandato como auditoría de completitud de una garantía de conservación de datos. No es un encargo de evasión. La adjudicación corresponde a Claude contra la fuente; este informe aporta escenarios y límites verificables.

Leí el diseño, el plan retirado y sus dos actas, las funciones indicadas de `case_manager`, el llamante, el lector C9, los serializadores y la entrada 227. Extendí el recorrido a los escritores y consumidores identificados en `core/`, `scripts/`, `streamlit_app.py` y `.claude/skills/`. `rg` no está disponible; utilicé `Select-String` y conservé los censos en `evidencia/censo_caso_md.txt` y `evidencia/censo_cuantia.txt`.

Ejecuté `sondas.py` con el Python 3.14 indicado y `-B`. Extrae y ejecuta nodos AST **sin modificar su cuerpo** de cuatro ficheros copiados a `wd/src`: `case_manager.py`, `utils.py`, `remove_expediente_link.py` y `repository_checkout.py`. Sustituye el localizador y `caso_path` por rutas sintéticas dentro de `wd/evidencia`, fija el reloj y suministra las dependencias de los nodos seleccionados. Usa los lectores, serializadores, escritores atómicos y mutadores reales sobre ficheros físicos. Un audit hook prohíbe escrituras Python fuera de `wd`, conexiones y subprocesos. No es una carga integral del repositorio ni una prueba end-to-end de `ensure_case` o de la CLI.

La corrida final terminó con **exit 0**, incluidas sus aserciones. Resultados: `evidencia/resultados.json`; ejemplos antes/después: `evidencia/*_before.md` y `*_after.md`. Hubo dos ajustes del arnés: crear el directorio de la primera muestra y aislar el checkout con una nueva semilla canónica. Esos intentos fallidos no cuentan como pruebas del objeto. La secuencia denominada `fusion_and_render` llama al registrador viejo con una cuantía nueva: su `canonical=false` incluye que ese registrador no actualiza cuantía; **no** lo atribuyo a un fallo ordinario de canonicidad de `register_expediente`. Las formas ordinarias están aisladas separadamente en `isolated_shapes`.

No existe todavía el `update_meta` propuesto ni el fichero de nueve tests. No he convertido una implementación inventada por el revisor en evidencia del futuro diff. Las conclusiones sobre esa API son consecuencias del contrato y de las primitivas ejecutadas; la muerte efectiva de sus futuros mutantes queda **SIN VERIFICAR**. No ejecuté pytest ni las semillas 777/31337: falta `pytest-randomly`, como advierte el mandato. Tampoco validé la línea base de 5.313 tests de otro commit.

## Hallazgos

### H-01 — ALTO — «Conservado» no conserva el cuerpo y la igualdad no es de bytes

**Anclas:** `core/case_manager.py:325`, `core/case_manager.py:326`; `core/utils.py:255`, `core/utils.py:270`, `core/utils.py:271`, `core/utils.py:277`, `core/utils.py:282`. Promesa: D:42–66 y D:125–134.

**Qué falla.** La prueba matemática razona sobre la cadena ya leída, pero promete conservación del fichero byte a byte y «cero escritura» cuando la comparación falla. La vía obligatoria de escritura vuelve a serializar el cuerpo incluso en ese caso: `body.strip()` elimina caracteres y `Path.write_text` aplica la convención de finales de línea de la plataforma. Además, el lector ya normalizó CRLF/CR y la regex consumió líneas blancas iniciales.

**Escenarios ejecutados, entradas → resultado:**

- Frontmatter válido + cuerpo que empieza por `    Nota como codigo\n` → igualdad falsa → pasar ese mismo cuerpo al escritor atómico elimina los cuatro espacios. No se necesita ningún falso positivo para perder texto ajeno.
- Cuerpo con nota final `Conservar  \n\n` → igualdad falsa → termina en `Conservar\n`. La nota no queda byte a byte idéntica.
- Fichero con cuerpo canónico en LF, CRLF o CR → los tres dan igualdad verdadera tras `read_md`; en Windows el escritor produce CRLF. Un fichero LF pierde la identidad de bytes de todas sus líneas ajenas a la cuantía.
- Cuerpo canónico precedido de `\n  \n` después del separador → igualdad verdadera porque `_FM_RE` consume ese prefijo. Es un cuerpo físico distinto admitido sin que un abogado haya escrito toda la plantilla a mano.

**Qué lo arreglaría.** Definir la frontera entre frontmatter, separador y cuerpo, retener los bytes originales de esa frontera y del cuerpo y escribirlos literalmente en la rama conservada. En la rama de regeneración, declarar si la garantía es de caracteres o de bytes y conservar, o rechazar explícitamente, las variantes de codificación y saltos que se quieran proteger. No basta con cambiar `==` ni con conservar una variable llamada `cuerpo`. Si se mantiene el escritor actual, hay que retirar la garantía literal; esa retirada deja de satisfacer la promesa fuerte del mandato.

### H-02 — ALTO — La fusión heredada puede cambiar datos fuera de la lista blanca

**Anclas:** `core/case_manager.py:282`, `core/case_manager.py:284`, `core/case_manager.py:363`, `core/case_manager.py:372`, `core/case_manager.py:377`; divergencia producida en `core/case_manager.py:1676`, `core/case_manager.py:1677`, `core/case_manager.py:1691`, `core/case_manager.py:1698`. Contrato: D:54–57 y D:127–131.

**Qué falla.** La lista blanca restringe los argumentos, pero no los efectos de la fusión. `update_pull_state` modifica la lista superior y deja el espejo en `meta` intacto. `_fusionar_expedientes` aplica encima la entrada «nueva» del espejo, que puede ser más antigua. Tampoco queda decidido con cuál de las dos metas renderiza `update_meta` después de factorizar.

**Escenarios ejecutados:**

1. `register_expediente('C','10','old')` → `update_pull_state('C','10',element='new')` → lista superior dice `new`, espejo y cuerpo dicen `old`. La igualdad contra el espejo sigue siendo cierta. La fusión actual restaura `old` sobre `new`. Un actualizador que la reutilice para fijar únicamente cuantía también pierde el cambio de `element`, fuera de su autorización por campos. No es una mera diferencia cosmética.
2. Caso con expediente 10 → `update_pull_state` crea el 20 solo arriba. El cuerpo todavía es exactamente `G(meta_previa)`, con el 10. La fusión incorpora el 20 al espejo. Si el nuevo render usa la meta fusionada, añade una línea de expediente, fuera de `{cuantia, referencia_crm}`. Si usa la meta sin fusionar, el cuerpo que escribe deja de coincidir con la meta guardada: la siguiente llamada se conserva y ya no repone otra cuantía en el cuerpo. Medido: `old_body_equals_G=true`, incorporación de `ID 20`, y `G(meta_nueva_sin_fusionar) != G(meta_guardada)`.

**Qué lo arreglaría.** Separar en el diseño la preservación de claves ajenas de la reconciliación de expedientes. `update_meta` debe poder escribir sus claves sin mutar las listas ajenas ni sus espejos. Si necesita reconciliarlas, debe declarar esa operación adicional y su autoridad, no deducir que la lista blanca la impide. Una opción conservadora es abstenerse de regenerar ante discrepancias que afecten al render y preservar ambas listas tal como estaban. La refactorización no debe alterar a escondidas el comportamiento de los registradores existentes.

### H-03 — MEDIO — La lista de propietarios no cubre todos los campos tardíos

**Anclas:** `core/case_manager.py:70`, `core/case_manager.py:72`, `core/case_manager.py:73`, `core/case_manager.py:75`, `core/case_manager.py:77`, `core/case_manager.py:78`, `core/case_manager.py:87`; creación en `core/case_manager.py:696`, actualización existente en `core/case_manager.py:730`. Afirmación: D:84–90.

**Qué falla.** Es válido reservar esta pieza a dos campos; no es exacto decir que son los únicos que pueden conocerse después y carecen de registrador. `cliente`, `contraparte` y `organo`, por ejemplo, solo se escriben mediante `ensure_case` al crear. No encontré actualizador público de ellos en el recorrido. Lo mismo sucede con título, enlace Drive y remoto; `estado` y `jurisdiccion` se inicializan por default sin un setter público en esta copia.

**Escenario concreto:** alta mínima con cliente y órgano pendientes → se conocen al leer la documental → `ensure_case(cliente='Cliente', organo='Órgano')` sobre índice existente no los repone; `update_meta` propuesto los rechaza. El operador sigue necesitando otra vía. Decirle simplemente «ensure_case» sería engañoso para actualizar esos campos.

**Qué lo arreglaría.** Mantener la lista blanca por alcance de #227, pero corregir su justificación y publicar la tabla completa de D.1. Distinguir campos inmutables, campos con dueño efectivo y campos sin API posterior; no ampliar la lista automáticamente ni inventar registradores. Declarar el procedimiento o backlog para los huecos.

### H-04 — MEDIO — Cambiar el default a `None` necesita adaptar también el payload CRM

**Anclas:** `scripts/abrir_caso.py:967`, `scripts/abrir_caso.py:734`, `core/abrir_caso.py:261`, `core/abrir_caso.py:286`, `core/sudespacho_create.py:1135`, `core/sudespacho_create.py:1238`, `core/sudespacho_create.py:1431`. Remedio: D:216–218.

**Qué falla.** Cambiar el tipo/default del flag y omitir la clave de `update_meta` cierra la sobrescritura por omisión, pero el flujo actual pasa siempre el argumento explícito a `crm_payload`. Su default numérico no se aplica cuando recibe `None`; el DTO lo conserva y los constructores del CRM hacen aritmética con él.

**Escenario derivado del código:** alta nueva sin `--cuantia` → `cuantia=None` tras el cambio propuesto → `crm_payload(..., cuantia=None)` → `datos.cuantia + datos.costas` falla. Hoy la misma omisión aporta `0.0`. No ejecuté el alta completa ni el CRM; el error de integración futuro es una deducción del paso directo y de esa suma.

**Qué lo arreglaría.** Separar presencia del flag para escritura local de la política del payload. Si se conserva el contrato actual del CRM, convertir solo allí ausencia a `0.0`, manteniendo ausente la clave local. Alternativamente, diseñar una cuantía ausente admitida por toda la cadena CRM. Probar alta nueva sin flag, con cero explícito y con cuantía; el reintento de test 8 no recorre necesariamente este constructor.

### H-05 — MEDIO — Separar mensajes no define recuperación y falta el cuarto desenlace

**Anclas:** `scripts/abrir_caso.py:674`, `scripts/abrir_caso.py:679`, `scripts/abrir_caso.py:720`, `scripts/abrir_caso.py:742`, `scripts/abrir_caso.py:743`, `core/case_manager.py:395`, `core/case_manager.py:399`. Diseño: D:237–239 y D:277–278.

**Qué falla.** El remedio separa tres actos pero los tests enumeran solo alta fallida, registro fallido y éxito. Falta alta y registro correctos con actualización del índice fallida. Tampoco se especifica cómo reponer el índice cuando el retorno «ya registrado» evita el bloque de creación. Además, `register_expediente` puede retornar sin registrar si falta caso/índice, sin lanzar.

**Escenarios concretos:**

- Alta devuelve 9999, registro local correcto, falla la futura escritura de cuantía por E/S → reintento con cuantía explícita encuentra el 9999 y retorna en línea 679. Si solo se inserta `update_meta` detrás del alta, la reparación no se ejecuta.
- Alta correcta, registro falla → repetir llega a la búsqueda remota y, si esta identifica el expediente existente, la rama VINCULAR bloquea y exige vincularlo. Separar el aviso no automatiza esa recuperación. El código no permite afirmar que ese reintento duplique necesariamente el CRM.
- Desaparece el índice antes de registrar → retorno normal del registrador → un mensaje basado solo en ausencia de excepción puede decir «registro correcto» sin vínculo persistido.

**Qué lo arreglaría.** Definir estados y salidas de los tres actos, con ID remoto conocido, resultado local verificable y acción de recuperación concreta. Cablear la reparación local con campos explícitos también en «ya registrado», si ese es el contrato elegido; no recrear el remoto. Añadir el cuarto caso y contar llamadas al CRM. Verificar registro mediante lectura o un resultado explícito del registrador. El visor de UI ya relee al vincular (`streamlit_app.py:2100`, `streamlit_app.py:2111`).

### H-06 — MEDIO — Algunos controles positivos pueden seguir verdes

**Anclas:** `docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-design.md:272`, `docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-design.md:275`, `docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-design.md:288`; retorno que el test 8 puede no atravesar: `scripts/abrir_caso.py:679`; resolución del reloj: `core/utils.py:86`.

**Qué falla / escenarios:**

- Test 6 solo compara primera y segunda salida. Añadir `actualizado_en` al cuerpo al regenerar puede hacer la primera salida no canónica; la segunda se conserva entera. El fichero es idempotente **con el texto indebido dentro**. Contramodelo ejecutado en `test6_countermodel`: `bytes_idempotent=true`, `unrequested_timestamp_present=true`, segunda regeneración falsa. No es la ejecución de un mutante del futuro diff. Incluso un generador que considere canónica esa línea necesita un reloj controlado: `now_iso` tiene resolución de segundos.
- Test 8 puede conservar el primer importe porque la segunda llamada retorna por «ya registrado» antes de usar el flag. Entonces restaurar `0.0` no lo vuelve rojo; tampoco prueba que exista recuperación local.
- Test 7 no tiene mutante asignado en la tabla.

**Qué lo arreglaría.** Definir puntos de mutación exactos y oráculos sobre la **primera** salida, el delta permitido y las llamadas efectivas. Para test 6 exigir también ausencia de contenido no renderizado por los campos permitidos; para test 8 acreditar que se recorrió la frontera de reparación, omisión y cero explícito. Añadir mutantes de pérdida de `bucket_override`, claves ajenas en `meta` y estado de expedientes. Matriz completa en F.

### H-07 — BAJO — «No hay ningún otro lector» es una conclusión demasiado amplia

**Anclas:** `streamlit_app.py:2675`, `streamlit_app.py:2679`, `streamlit_app.py:2689`; `.claude/skills/preparacion-audiencia-previa/references/flujo.md:10`, `.claude/skills/preparacion-audiencia-previa/references/flujo.md:11`; lector específico: `core/verificar_apertura.py:799`. Afirmación: D:190–195.

**Qué falla.** C9 sí consume el frontmatter. Sin embargo, el visor lee y renderiza el fichero completo, incluida la línea de cuantía, y el flujo de la skill manda leer la cuantía de `_caso.md` sin fijar precedencia entre sus dos representaciones. El barrido por `cuantia` de Python no certifica el consumo por prompts.

**Escenario:** se conserva un cuerpo con `_(pendiente)_` y se fija cuantía en frontmatter → el visor sigue presentando la línea pendiente. La skill recibe el fichero contradictorio en otra sesión, sin el informe de consola de `update_meta`. No he demostrado qué valor escogería el modelo; eso queda **SIN VERIFICAR**. No atribuyo a la skill una instrucción expresa de preferir el cuerpo: no la hay.

**Qué lo arreglaría.** Acotar «único lector» a lector determinista específico del valor encontrado en Python. Incluir visor y skill en la evaluación del precio, fijar precedencia del dato y dar un aviso persistente o comprobación en el consumidor. El visor es parte del coste humano ya reconocido; la skill añade una cobertura que el argumento no analizó. No se acredita con esta ronda una generación errónea de escritos reales.

### H-08 — MEDIO — Falta un contrato de entrada segura antes del «SIEMPRE»

**Anclas:** `core/utils.py:278`, `core/utils.py:281`; `core/case_manager.py:69`, `core/case_manager.py:70`, `core/case_manager.py:365`, `core/case_manager.py:368`, `core/case_manager.py:353`. Diseño: D:99–108, D:125–131, D:142.

**Qué falla.** La reconstrucción filtrada se describe en la sonda, no como contrato completo de la API. Faltan caso/índice inexistente, llamada vacía, `fm` o `meta` no mapa, meta sin campos obligatorios, YAML inválido/duplicado y BOM. El «frontmatter SIEMPRE» y reutilizar un helper tolerante no definen cómo fallar sin normalizar entradas que no se pueden preservar.

**Escenarios:** `CaseMeta(**m)` con `proyeccion_local=True` produce `TypeError`, ejecutado; el filtrado lo acepta. `meta={}` no aporta `case_id`/`titulo`, requeridos por el dataclass. Un fichero con BOM inicial no se reconoce como frontmatter. El ciclo real `read_md` → escritor pierde comentarios humanos y la primera de dos claves YAML duplicadas (`ajena: NO BORRAR`, `ajena: segunda`); ambos casos ejecutados. La fusión de dicts no puede preservar texto que el parser ya eliminó.

**Qué lo arreglaría.** Contratar reconstrucción filtrada, conservación de claves desconocidas, validación de tipos y tratamiento explícito de defaults/identidad. Ante entradas ilegibles o ambiguas, parar antes de escribir con diagnóstico y bytes intactos, o definir una reparación separada. Aclarar que preservar claves semánticas no preserva comentarios YAML. No convertir silenciosamente un índice roto en alta nueva mediante `_write_case_index`. Los comentarios son además texto humano fuera del cuerpo: si la promesa se limita al cuerpo, debe decirlo.

### H-09 — MEDIO — La garantía necesita una precondición de exclusión

**Anclas:** `core/case_manager.py:323`, `core/case_manager.py:325`, `core/case_manager.py:326`, `core/case_manager.py:1547`, `core/case_manager.py:1561`; editor de navegación: `.claude/skills/_shared/registrar_outputs.py:174`, `.claude/skills/_shared/registrar_outputs.py:179`. Cobertura del llamante: `scripts/abrir_caso.py:1126`, `scripts/abrir_caso.py:1203`.

**Qué falla.** La igualdad acredita la versión leída, no la versión que existe al reemplazar. Un `os.replace` atómico no es comparación e intercambio. §7 reconoce el riesgo futuro, pero §2.1 y el docstring mantienen la promesa incondicional de no poder destruir el cuerpo.

**Escenario concreto ejecutado como intercalación dirigida:** A lee cuerpo canónico; B escribe una nota `NO BORRAR`; A sustituye el fichero con su frontmatter y cuerpo basados en la lectura vieja. La nota desaparece. Se usaron lectura y escritor atómico reales, sin carrera aleatoria ni dos procesos. La misma intercalación con `_atomic_write_caso_md` y los mutadores de checkout restaura un lock antiguo; con `registrar_outputs` pierde navegación. Los dos escritores del mismo proceso además comparten `._caso.<pid>.tmp`; esa carrera de hilos no se ejecutó.

**Qué lo arreglaría.** Si se mantiene la decisión de no exigir mutex dentro de la función, expresar la garantía bajo exclusión vigente de **todos** los escritores relevantes durante lectura, comparación y reemplazo, y exigirlo en el contrato del llamante. Una comprobación de versión sin cerrar la ventana posterior no basta. Una protección frente a editores no cooperantes requiere otra estrategia de coordinación/conflicto. No es necesario cambiar ahora los cuatro registradores para corregir el alcance de lo prometido; tampoco su ausencia de guard convierte en imposible el escenario.

## Respuestas explícitas al §2

### A.1 — Roundtrip y tipos

Para los tipos ordinarios persistidos por este código, no encontré el supuesto cambio automático de entero a float. `CaseMeta` no coacciona tipos: `core/case_manager.py:67–107`. La sonda verificó `None`, `0`, `0.0`, `73140`, `73140.0`, `73140.5`, `-0.0`, infinito, NaN y cadena vacía: mismo tipo y misma representación del generador después de `asdict → safe_dump → safe_load → CaseMeta`. Que infinito/NaN rendericen igual **no** valida su admisibilidad económica; C9 tiene otra validación.

`None` y `''` se conservan como valores distintos en YAML. En cliente/contraparte/órgano ambos renderizan el placeholder por `or` (`core/case_manager.py:195`, `:196`, `:199`); en cuantía solo `None` da placeholder (`:200`). Un entero leído como `int` sigue renderizando sin `.0`. Si un editor cambia `73140.0` a `73140` solo en YAML, el cuerpo anterior puede dejar de ser canónico: falso negativo seguro en la lógica de comparación, no en la conservación literal del escritor.

`sudespacho_expedientes=None` se convierte en `[]` en `__post_init__`, pero ambos producen sección vacía (`:106`, `:172`). Las listas de dicts ordinarias con strings, números y estado D8 se conservan en lo que usa el render. **No hay garantía para cualquier valor que Python acepte:** se ejecutó `input_dir=('a','b')` dentro de un dict; YAML lo devuelve como lista y cambia su representación interpolada en `:179`. Es un valor no habitual, sin validación de tipos; genera un falso negativo. Cadenas con CR embebido pueden divergir entre meta escapada y cuerpo normalizado. No prueba un falso positivo capaz de borrar palabras ajenas en un snapshot íntegro; H-01 es el contraejemplo de E/S.

### A.2 — Lista fusionada y divergencias

En una llamada individual de `_actualizar_indice`, el espejo guardado es una copia profunda de `expedientes` (`:372`) y el render recibe esa misma lista por `replace` (`:377`). No hay un camino ordinario de esa función que elija deliberadamente dos listas diferentes. Eso no equivale a que `_actualizar_cuerpo` produzca siempre el cuerpo canónico: conserva el resto del cuerpo y puede no encontrar sus fragmentos.

**Sí hay divergencia entre llamadas:** `update_pull_state` modifica únicamente top-level (`:1655–1698`), incluso creando una entrada o cambiando `element`; no actualiza espejo ni cuerpo. Los campos D8 que no se renderizan no rompen la igualdad contra el espejo; una entrada nueva también puede dejarla verdadera, aunque falte en cuerpo. La siguiente fusión puede cambiar el espejo, restaurar campos antiguos o hacer que el render proyectado difiera: H-02. `remove_expediente_link` modifica las dos listas pero conserva el cuerpo (`scripts/remove_expediente_link.py:70`, `:76`, `:81`): aquí la igualdad pasa a falsa si eliminó una entrada visible.

### A.3 — Todos los campos que toca el generador y qué puede mover la pieza

Inventario completo de dependencias directas y helpers:

| Campo | Render / ancla | ¿Lo puede mover `update_meta` según la lista? |
|---|---|---|
| `titulo` | encabezado, `core/case_manager.py:191` | No |
| `case_id` | línea estado, `core/case_manager.py:156` | No; selector, no campo de `**campos` |
| `estado` | misma línea, `core/case_manager.py:156` | No |
| `referencia_crm` | línea opcional, `core/case_manager.py:185` | Sí |
| `cliente` | `core/case_manager.py:195` | No |
| `contraparte` | `core/case_manager.py:196` | No |
| `jurisdiccion` | `core/case_manager.py:198` | No |
| `organo` | `core/case_manager.py:199` | No |
| `cuantia` | `core/case_manager.py:200` | Sí |
| `drive_link` | `core/case_manager.py:202` | No |
| `drive_remote_path` | `core/case_manager.py:203` | No |
| `drive_ev_team_id` | `core/case_manager.py:160–161` | No |
| `drive_ev_folder_id` | `core/case_manager.py:160–161` | No |
| `sudespacho_expedientes` | `core/case_manager.py:172–179` | No por argumento; sí por la fusión si se reutiliza sin separar efectos |

La sección lee `id`, `element`, `input_dir` de cada dict, en orden; ignora elementos que no son dict. El resto de campos de CaseMeta **no se renderiza**. Bajo la hipótesis estricta de mismo generador, snapshot fijo y M' obtenido solo por sustituir los dos campos, el lema sobre caracteres es correcto: no encontré un tercer campo que varíe espontáneamente. El diseño operativo no satisface automáticamente esas hipótesis: fusión, serialización y concurrencia son H-01/H-02/H-09. No debe confundirse el cambio de `actualizado_en` en metadatos con uno en cuerpo: hoy no aparece en G.

### A.4 — Aparición/desaparición de referencia CRM

No rompe el lema acotado. `core/case_manager.py:185` renderiza una línea completa con salto final si el valor es truthy; con `None` o cadena vacía renderiza vacío. Cambiar ese campo permite insertar, sustituir o retirar esa línea y desplazar la posición de lo siguiente, preservando su secuencia textual. «Solo ese campo» no significa mismos offsets ni mismo número de líneas. La frase D:62–63 de que incluso una plantilla escrita a mano recibe «ese mismo texto» necesita la excepción de los campos actualizados: un valor viejo sí se sustituye. La igualdad no acredita autoría histórica.

### A.5 — Falsos positivos de la igualdad y BOM

Sí existen variantes **físicas** no canónicas que acepta sin escritura manual de toda la plantilla: LF/CRLF/CR y líneas blancas iniciales consumidas por la regex. Medidas en `io_variants`; H-01. Si se define «canónico» exclusivamente como la cadena ya normalizada por `read_md`, llamarlas falsos positivos es una cuestión de definición, pero entonces hay que retirar «byte a byte» y «difiere en cualquier cosa» del contrato físico.

BOM inicial: se lee con `utf-8`, no `utf-8-sig`; impide que `^---` coincida, devuelve `{}` y todo el fichero como cuerpo (`core/utils.py:277–280`). BOM dentro del cuerpo: queda como carácter extra y da desigualdad. Ninguno fue falso positivo en la sonda. El diseño no especifica cómo gestionar la reconstrucción fallida del primer caso; no afirmo que una implementación todavía inexistente vaya a sobrescribirlo. Una cadena no canónica después de la lectura no puede satisfacer una igualdad exacta por sí sola; el hueco está antes y después de la comparación.

### B.1 — Inventario de formas no cubiertas por la tabla de §4

La tabla acredita ejemplos, no familias completas de estados. Inventario por productores y variantes relevantes que no enumera:

| Forma producible / frontera | Efecto y evidencia |
|---|---|
| Desvincular uno, varios o el último expediente; desvinculación sin coincidencia | Cambia listas y deja cuerpo viejo; si no eliminó nada visible puede seguir canónico. `scripts/remove_expediente_link.py:63–81`; duplicado operativo en `scripts/limpieza_post_audit.py:161–178`. Ejecutado eliminar uno. |
| `update_pull_state` creando entrada nueva, cambiando `element`, o con estado D8 diferente del espejo | Puede mantener igualdad con espejo **obsoleto** y preparar la discrepancia de H-02. `core/case_manager.py:1662–1698`. Ejecutados los tres tipos. |
| Registro posterior a esos pulls o a una desvinculación; no-op por IDs/cache ya iguales | La recomposición y sus retornos importan: `core/case_manager.py:413`, `:820–824`, `:932–936`. La tabla no da estados iniciales, argumentos ni orden completos. |
| Escritura/liberación/cancelación/conflicto de checkout | Mutan metadatos no renderizados, normalmente conservan canonicidad si ya existía. `core/case_manager.py:1071`, `:1092`, `:1110`, `:1120`. Ejecutado adquirir lock sobre semilla canónica. |
| Checkout/checkin por CLI remota, cuerpo vacío con fallback | `scripts/repository_cli.py:1159`, `:1176`; devuelve cuerpo leído, pero el push de uno vacío usa `# Caso`. Lectura de fuente, no ejecución de Drive. |
| Segundo `ensure_case` que de verdad cambia `tipo_caso`, `direccion`, `id_go` o `ciudad` | No son campos renderizados; canonicidad previa puede mantenerse. Diferente del no-op de idempotencia. `core/case_manager.py:730–750`. Inspección. |
| Movimiento de ciudad y migración de buckets | `core/casos/case_locator.py:335–341` modifica ciudad y reserializa; `scripts/migrate_05crm_buckets.py:337–339` modifica estado no renderizado. Inspección. |
| Navegación añadida por `registrar_outputs` | Nueva línea ajena a G, por tanto desigualdad: `.claude/skills/_shared/registrar_outputs.py:174–179`, con copias en siete bundles. No es edición manual ni legacy. |
| `_caso.md` mínimo del scaffolder de skills | Frontmatter sin `meta` y cuerpo distinto, aun producido hoy: `.claude/skills/_shared/scaffold_caso.py:68–89`, `:127`. No es necesariamente expediente E&V del flujo objetivo. |
| Fichero sin frontmatter, truncado, mapa vacío, lista, meta mal tipada o con campos obligatorios ausentes | Hay ramas de producción/tolerancia en `core/case_manager.py:345–357`; falta política en la nueva API. No son estados incluidos por «caso mínimo». |
| Metas con claves ajenas como `proyeccion_local`, listas con entradas sin `input_dir`/sin ID/no dict, mirrors discordantes | `core/case_manager.py:168–179`, `:277–294`, `:368`. El filtrado de nombres y defaults necesita cobertura propia. |
| Valores vacíos, `None`, cero, int/float, strings multilineales/CR, contenedores internos de tipo inesperado | No los acredita una fila «completo». `core/case_manager.py:105–107`, `:172–203`; parte ejecutada en A.1. |
| Codificación, BOM, LF/CRLF/CR/mixtos, blancos de borde, YAML comentado o duplicado | No los mide un espacio tras `## Partes`. H-01/H-08. |
| Escritura de tercero entre lectura y reemplazo | No es una forma estática, pero sí una población excluida por la sonda. H-09. |

No afirmo que todos esos estados sean no canónicos. Precisamente algunos conservan igualdad y otros la rompen; falta diferenciarlos. Tampoco presento el inventario como una enumeración de todas las combinaciones posibles.

### B.2 — Desvinculación, escritor genérico y guard de checkout

Desvincular una entrada visible deja cuerpo no canónico: medido. `_atomic_write_caso_md` **no garantiza** canonicidad: entrega el frontmatter al mutador, estampa `actualizado_en` y pasa el cuerpo leído al escritor (`core/case_manager.py:1547–1561`). Depende de qué cambie el mutador y del estado anterior.

Los `checkout_*`, `estado_repositorio` y `ultimo_checkin_*` no son `estado` del caso y G no los lee. Sus mutadores en `core/repository_checkout.py:176–218` pueden mantener la igualdad; la adquisición ejecutada la mantiene. El `guard_escritura` propiamente dicho decide si se desvía y puede emitir un evento (`core/case_manager.py:1209–1214`): no regenera `_caso.md`. Los escritores del protocolo sí lo hacen por otras vías. Conservar sus campos no equivale a cumplir su protocolo de autorización ni a tener mutex.

### B.3 — Reconstrucción filtrada

Es lo que hace la **sonda descrita**; la API aún no fija todos los detalles. Debe convertirse en contrato explícito, con tests. Hay precedente real en los tres registradores: `core/case_manager.py:428–434`, `:831–837`, `:943–949`, con defaults de título/identidad y timestamp que tampoco conviene copiar sin analizar.

`CaseMeta(**m)` con una clave ajena válida como `proyeccion_local` levanta `TypeError`: ejecutado. Filtrar permite construir CaseMeta y conservar la clave fuera del dataclass mediante la fusión apropiada. Filtrar **no** basta para tipos erróneos, mapas ausentes o campos obligatorios; H-08. Falta implementación para dictaminar qué hará realmente: **SIN VERIFICAR**.

### B.4 — No haber mirado el Drive real

Es una limitación suficiente para no prometer una tasa de éxito sobre índices históricos; no invalida por sí misma un lema matemático sobre una igualdad exacta. Tampoco confirma ese lema aplicado a E/S. «Sobre un índice legacy la igualdad fallará» (D:169) es demasiado absoluto: uno antiguo que coincida con G la pasará, y uno producido hoy por otros escritores puede no pasarla. Debe decir «puede fallar» y medir la población si se quiere asegurar utilidad práctica.

No se necesita el Drive para refutar «no se toca el cuerpo»: las muestras sintéticas con el escritor real lo hacen. El alcance de «camino normal» queda sostenido por ejemplos locales, no por un inventario completo ni por producción. Casos reales y tasa de degradación: **SIN VERIFICAR**.

### C — Lectores y precio de dejar el cuerpo obsoleto

C9 toma `fm['meta']['cuantia']` en `core/verificar_apertura.py:795–800`; contrasta con la cuantía de cada ficha CRM (`:806–829`). El hecho técnico central del §5 es correcto. En el barrido no encontré otro parser determinista específico que extraiga el número de la línea `- Cuantía:` en las rutas solicitadas. `scripts/init_caso.py:48`, `:65` y el formulario de Streamlit son productores; `core/verificar_apertura_fuentes.py:244` lee del CRM; los scaffolders escriben la línea, no la extraen.

**Sí hay otro lector del cuerpo:** el visor de Markdown (`streamlit_app.py:2679–2689`) permite seleccionar `_caso.md` en `00_Input` y renderiza el fichero entero. Es consumo para un humano, ya perteneciente al precio reconocido, pero no recibe automáticamente `motivo`. La skill de audiencia previa consume la cuantía del fichero (`.claude/skills/preparacion-audiencia-previa/references/flujo.md:10–12`) sin un selector de frontmatter ni regla ante contradicción. Por tanto, la afirmación amplia de que solo se degrada la lectura humana no queda acreditada por el grep original; H-07. No encontré un export que parseara específicamente esa línea. No he ejecutado el visor ni una generación por la skill; su comportamiento efectivo ante discrepancia queda **SIN VERIFICAR**.

### D.1 — CaseMeta completo: quién escribe cada campo hoy

Esta tabla describe las vías encontradas en la copia, no concede autorización para editar a mano los campos reservados. Todos se serializan por `asdict` (`core/case_manager.py:309`) y la actualización interna puede reescribirlos; «sin actualizador» significa sin API pública posterior específica encontrada, no imposibilidad física de escribir el fichero.

| Campo | Escritor / situación actual |
|---|---|
| `case_id` | Identidad de creación en `ensure_case`, `core/case_manager.py:697`; `register_expediente` reafirma el selector en `:430`. No es corrección libre de metadatos. |
| `titulo` | Creación, `core/case_manager.py:698`; fallback de reconstrucción `:431`, `:834`, `:946`. Sin actualizador público posterior encontrado. |
| `referencia_crm` | Creación `core/case_manager.py:699`; caller copia `ident.case_id`, `scripts/abrir_caso.py:1131`. Sin registrador posterior; entra en lista propuesta. |
| `cliente` | Creación `core/case_manager.py:700`; sin actualizador posterior encontrado. |
| `contraparte` | Creación `core/case_manager.py:701`; sin actualizador posterior encontrado. |
| `jurisdiccion` | Default `civil`, `core/case_manager.py:74`; `ensure_case` no ofrece kwarg. Sin setter público encontrado. |
| `organo` | Creación `core/case_manager.py:705`; sin actualizador posterior encontrado. |
| `cuantia` | Creación `core/case_manager.py:704`; sin registrador posterior; entra en lista propuesta. |
| `drive_link` | Creación `core/case_manager.py:702`; no lo actualiza `register_drive_ev`. Sin registrador posterior encontrado. |
| `drive_remote_path` | Creación `core/case_manager.py:703`; no lo actualiza `register_drive_ev`. Sin registrador posterior encontrado. |
| `drive_ev_team_id` | `register_drive_ev`, `core/case_manager.py:826`. |
| `drive_ev_folder_id` | `register_drive_ev`, `core/case_manager.py:827`. |
| `drive_ev_folder_name` | `cache_drive_folder_info`, `core/case_manager.py:938`. |
| `drive_ev_drive_id` | `cache_drive_folder_info`, `core/case_manager.py:939`. |
| `direccion` | Creación `core/case_manager.py:706` y `ensure_case` existente `:742`. |
| `id_go` | Creación `core/case_manager.py:707` y existente `:744`; en modo v1 hay concordancia de identidad previa `:561–576`. |
| `tipo_caso` | Creación `core/case_manager.py:708` y existente `:740`. |
| `ciudad` | Creación `core/case_manager.py:709`, existente `:746–747`; además cambio de ciudad en `core/casos/case_locator.py:336–339`. |
| `estado` | Default `instruccion`, `core/case_manager.py:87`; serializa/renderiza al pasar por escritores internos. Sin setter público posterior encontrado. No es `estado_repositorio`. |
| `sudespacho_expedientes` | Inicialización `core/case_manager.py:106–107`; registro `:414–432`; fusión/espejo `:363–377`; pull **solo arriba** `:1655–1698`; eliminación en `scripts/remove_expediente_link.py:70–76` y `scripts/limpieza_post_audit.py:171–175`. |
| `creado_en` | `ensure_case` al crear, `core/case_manager.py:710`; default vacío `:89`. No debe ser dato tardío libre. |
| `actualizado_en` | Creación `core/case_manager.py:711`; registradores `:433`, `:835`, `:947`; escritor mutador `:1555`. `_actualizar_indice` por sí solo no lo refresca. |
| `estado_repositorio` | Mutadores `core/repository_checkout.py:177`, `:194`, `:209`, `:218`; wrappers `core/case_manager.py:1071`, `:1092`, `:1110`, `:1120`; protocolo remoto también los usa. |
| `checkout_user` | Adquirir `core/repository_checkout.py:178`; limpiar al liberar/cancelar `:195`, `:210–212`. |
| `checkout_timestamp` | Adquirir `core/repository_checkout.py:179`; limpiar `:196`, `:210–212`. |
| `checkout_nonce` | Adquirir `core/repository_checkout.py:180`; limpiar `:197`, `:210–212`. |
| `checkout_maquina` | Adquirir `core/repository_checkout.py:181`; limpiar `:198`, `:210–212`. |
| `checkout_notas` | Adquirir `core/repository_checkout.py:182`; limpiar `:199`, `:210–212`. |
| `ultimo_checkin_timestamp` | Liberar tras checkin, `core/repository_checkout.py:200`; no actualizar al cancelar. |
| `ultimo_checkin_auditlog` | Liberar tras checkin si viene auditlog, `core/repository_checkout.py:201–202`. |

El scaffolder genérico de skills también escribe título, partes, órgano, cuantía y estado en el **cuerpo**, sin `meta`, al crear (`.claude/skills/_shared/scaffold_caso.py:68–89`). Es otro productor de `_caso.md`, no un registrador posterior de CaseMeta.

Dictamen: `{cuantia, referencia_crm}` es un alcance prudente para #227, **no** un inventario completo de todos los datos tardíos sin hogar. H-03 identifica el hueco y evita responder a los rechazos con una vía que no funciona sobre caso existente.

### D.2 — `None` explícito y comprensiones

El contrato es coherente si presencia y valor son conceptos separados. Hay dos trampas opuestas:

- `{k: valores.get(k) for k in permitidas}` fabrica claves ausentes con `None` y ordena borrar un valor conocido.
- `{k: v for k, v in campos.items() if v is not None}` impide una limpieza explícita; `if v` pierde además el cero legítimo y la cadena vacía.

Se necesita un sentinel de ausencia o conservar el conjunto original de claves aportadas. El CLI debe aplicar `cuantia is not None` para distinguir ausencia del flag de cero; un borrado explícito vía API sigue pasando `None`. No es necesario cambiar esta semántica por la de `update_pull_state`, que documenta justo lo contrario en `core/case_manager.py:1626`; sí conviene señalar la diferencia. Probar omisión, cero y null desde valores anteriores no nulos.

### D.3 — Suficiencia del informe

`frontmatter`, `cuerpo`, `motivo` distingue el resultado básico, pero no basta para saber qué corregir ni para los fallos del flujo completo. Faltan una identificación accionable del índice, campos y valores efectivos tras la escritura, y una indicación explícita de que el **cuerpo puede seguir obsoleto**, con la acción siguiente. Un cuerpo distinto no implica necesariamente cuantía distinta: puede ya tener el dato correcto y solo contener una nota; `motivo` no debe inventar el estado de la línea.

«Claves efectivamente escritas» es ambiguo entre solicitadas, cambiadas y todas las reserializadas por el helper. Con fusión actual hay más cambios que esos dos campos; H-02. Falta decidir cómo informar no-op/llamada vacía y fallo de E/S; no se puede devolver «escrito» si `os.replace` falla. Para el alta hacen falta estado remoto/ID, estado del registro y estado del índice por separado; H-05. El aviso de consola no acompaña al documento en el visor o en una sesión futura de una skill; H-07. Se puede mantener el dict pequeño si el llamante aporta esos datos y la política queda explícita.

### D.4 — ¿Puede factorizarse sin cambiar `_actualizar_indice`?

**Sí, es posible**, pero no basta con extraer `{**fm, **propias}`. La función completa realiza:

1. Fusión de expedientes con orden, conservación de entradas y precedencia actuales (`core/case_manager.py:363–364`, helper `:266–295`).
2. Recuperación tolerante de meta previa y conservación de claves desconocidas, con CaseMeta por encima (`:365–368`).
3. Espejo mediante `deepcopy` para evitar alias entre las dos listas (`:372`).
4. Regeneración de las diez claves propias superiores y meta (`:373–376`, definición `:298–310`), no solo los campos del argumento de actualización.
5. `replace(meta, sudespacho_expedientes=expedientes)` para el render (`:377`).
6. Actualización por los tres fragmentos del cuerpo y escritura atómica, con sus errores/retorno (`:378`, `:313–334`).

Un helper de frontmatter puede devolver también la lista fusionada/meta de render, o el llamante recuperarla de un resultado definido; perder el paso 5 hace que cuerpo y meta usen listas diferentes. Los pasos 5–6 quedan fuera de un helper que solo devuelva un dict, y deben mantenerse explícitos. No hay incremento de timestamp dentro de `_actualizar_indice`: hoy lo aportan los registradores antes de llamarla. No añadirlo al factorizar, porque cambiaría su conducta y la idempotencia.

También deben quedar fuera el resolver, comprobación de existencia, lectura, ramas de creación/truncado de `_write_case_index`, retornos tempranos de los registradores y sus defaults/stamps. No trasladar a `update_meta` por accidente la tolerancia de creación. Puede conservarse exactamente el comportamiento viejo y a la vez reconocer que parte de ese comportamiento **no sirve** para un actualizador limitado a dos campos: H-02/H-08. La «diferencia en una línea» de D:131 no es prueba de equivalencia ni de preservación.

### E — Decisión del mutex

Es defendible como distribución de responsabilidades **con precondición expresa**, coherente con los registradores actuales. La llamada normal inspeccionada a `_alta_crm` está dentro de `mutex_sesion.sostenido` (`scripts/abrir_caso.py:1126–1128`, `:1203`). El v1 de `ensure_case` comprueba vigencia (`core/case_manager.py:541`), y los otros tres registradores no lo exigen en sus cuerpos. No encontré una carrera demostrada del camino normal por el mero hecho de no repetir esa exigencia en el nuevo método.

El daño abierto está descrito y ejecutado como intercalación en H-09: A compara una versión canónica, B añade nota/lock/link, A hace `os.replace` con la versión vieja. Puede destruir texto que G jamás reprodujo. «Todos sus vecinos lo hacen» no es un argumento de seguridad; es una decisión de compatibilidad que obliga a acotar el teorema. La exclusión cooperativa tampoco protege automáticamente de un editor externo o de una escritura remota de otro protocolo. Vigencia real del lease, concurrencia multiproceso, hilos y coordinación Drive: **SIN VERIFICAR**.

### F — Cada test y su mutante

Dictamen de suficiencia **del test descrito**, no resultado de una corrida futura. No hay implementación ni tests que mutar. La columna «mata» es condicional a que el test haga los asertos que el diseño exige.

| Test | Mutante anunciado | ¿Lo mata el test descrito? / qué falta |
|---|---|---|
| 1. Canónico se reescribe | Comparación siempre `False` | **Sí**, si parte de cuantía pendiente y exige el valor nuevo en cuerpo y `cuerpo=reescrito`. El FM solo no serviría. |
| 2. Nota se conserva | Comparación siempre `True` | **Sí** para una nota que no forma parte de G: regenerar la elimina. Comprobar solo la nota no acredita el resto del cuerpo ni blancos de borde. |
| 3. Un espacio de más | Comparación siempre `True` | **Sí**, si compara el cuerpo completo o verifica que el espacio adicional permanece. Comprobar solo cuantía/frontmatter sería insuficiente. |
| 4. Campo ajeno | Eliminar comprobación de lista blanca | **Sí** para retirar el guard, si exige el `ValueError` correcto, hogar y hash idéntico. Si «vaciar» significa dejar el conjunto vacío pero mantener el guard, ese test seguiría verde: aún rechaza dirección. Precisar el parche del mutante. Falta mezcla de campo permitido/prohibido y árbol de caso ausente. |
| 5. Null vs omisión | Filtrar los `None` | **Sí para null**, solo si el valor previo es no nulo y se comprueba que se limpia. Empezar ya con null deja verde al mutante. Ese mutante **no** acredita la mitad de omisión: hace falta otro que materialice la clave ausente y un valor previo distinto para esa mitad. |
| 6. Idempotencia de bytes | Añadir `actualizado_en` al cuerpo | **No necesariamente**: el añadido puede congelar la primera salida no canónica; dos salidas iguales con contenido indebido. También puede coincidir el reloj por segundos. H-06 y contramodelo ejecutado. Si se añade incondicionalmente en cada escritura, sí lo mataría, pero eso es otro parche concreto que hay que fijar. |
| 7. Claves ajenas y expedientes | **Ninguno asignado** | No se puede atribuir un control positivo que la tabla omite. Añadir pérdida de clave superior, clave ajena en meta, D8 y sección, con asertos independientes y conservación completa. |
| 8. CLI no pisa con cero | Volver al default `0.0` | **Condicional; puede sobrevivir** por retorno de idempotencia antes de update. Debe verificar que el reintento sí puede reparar cuando viene dato y que no escribe cuando está ausente; contar escrituras/altas. Añadir cero explícito y alta nueva sin cuantía. |
| 9. Mensajes distinguibles | Un `except` común a alta/registro | **Sí**, si inyecta fallo solo del registro después de alta correcta y prohíbe «Alta CRM falló», no meramente busca un aviso genérico. No prueba fallo del tercer acto ni recuperación, ni que un retorno silencioso registrara realmente. |

La propiedad central sin un test directo es: **el delta del cuerpo completo solo puede corresponder a los campos autorizados, y todo el cuerpo físico ajeno se preserva incluso en la rama conservada**. Los nueve ejemplos no comparan exhaustivamente el resto de G antes/después, ni el cuerpo bruto en ambas ramas bajo la E/S real. Faltan también transiciones de referencia presente/ausente/`None`/vacía, roundtrip de tipos, fusión discordante, desconocidas de meta, corrupción/BOM, fallos de escritor y precondición de concurrencia. Una nota conservada y una sección de expedientes no equivalen a esa propiedad universal.

Semillas, suite completa, conteo JUnit y muertes reales de los nueve mutantes: **SIN VERIFICAR**. El contramodelo del test 6 demuestra insuficiencia de su oráculo descrito; no se cuenta como mutante muerto o superviviente de código productivo inexistente.

### G — Hechos y remedios de §6.1 y §6.2

**§6.1: contenido confirmado con matices.** `scripts/abrir_caso.py:967` contiene exactamente `cuantia: float = typer.Option(0.0, "--cuantia")`; no hay `update_meta` en esta copia. La cuantía sigue hasta `crm_payload` por `:1203` y `:734`; `ensure_case` en `:1130–1134` no la recibe. La frase del plan retirado en `docs/superpowers/plans/2026-09-11-identidad-sin-teclado.md:117–120` dice que se conservó el cambio y contradice ese contenido. El cero no destruye hoy una cuantía local por la API retirada; esa precisión del diseño es correcta. No convierte el cero en dato conocido ni juzga su política económica.

Cambiar a `None` y no pasar la clave cuando falta es correcto para evitar el borrado local; **insuficiente como integración** sin política de payload (H-04), semántica del reintento y test sensible (H-05/H-06). Corregir la frase del plan es necesario. Que «se fue entero con PR #338», fechas y relación exacta con `origin/main` queda **SIN VERIFICAR**: no hay genealogía.

**§6.2: el bloque citado coincide con el contenido.** `scripts/abrir_caso.py:741–749` pone create y register bajo un único `except Exception`; el mensaje acusa al alta aunque falle solo el registro. El `typer.echo` de éxito también está dentro del try. Separar resultados es correcto. La deducción «el reintento duplica» no es inevitable: hay control de duplicados remoto y la rama VINCULAR bloquea (`:684–732`). El remedio debe proporcionar el ID/acción de recuperación y cubrir un registro que no lanza pero no escribe; separar tres try/except sin contrato posterior no basta. Falta además el caso alta y registro correctos con fallo del índice, y reparación en ya registrado. H-05.

El hecho de que el defecto pertenezca al código congelado está comprobado. Su pertenencia histórica a `origin/main`, cuándo entró/salió cada PR y la causalidad de la retirada: **SIN VERIFICAR**.

## Inventario de lo NO cubierto por esta ronda

1. Implementación de `update_meta`, extracción definitiva del helper, API de errores y pruebas futuras: no existen en el objeto. No se certifica que una elección concreta del implementador vaya a incurrir en todas las alternativas descritas.
2. Suite completa, semillas 777/31337, JUnit, regresiones sobre los 5.313 tests declarados y mutación real de los nueve tests. No se intentó instalar ni ejecutar `pytest-randomly`.
3. Ejecución integral de `ensure_case`, CLI/Typer, UI/Streamlit y skills con su runtime. Las sondas aíslan nodos de código copiado y ficheros sintéticos; creación cubierta por el sumidero, no por plantillas ni estructura completa de alta.
4. Drive/CRM/red reales, fichero de producción alguno, corpus legacy y tasa de canonicidad en usuarios. No se comprobó una salida judicial o exportación incorrecta por la contradicción cuerpo/frontmatter.
5. Genealogía git, identidad verificable del commit/branch, PR #338/#344, fecha/hora de integración y baseline de `b59bb49`.
6. Concurrencia real de procesos/hilos, validez/renovación del lease, exclusión distribuida, conflictos de sincronización Drive y escritores no cooperantes. Se ejecutó una intercalación dirigida local; no una certificación del mutex.
7. Disco lleno real, cortes de proceso/alimentación, durabilidad, errores físicos de `os.replace`, junctions/permisos y otros fallos del sistema de archivos. La escritura normal fue física; no se provocaron esos fallos.
8. Exhaustividad combinatoria de tipos YAML, Unicode y Markdown. Se midieron casos concretos de número, tuple interno, BOM, CR/LF/CRLF, blancos, comentarios y duplicados; no un parser completo ni una prueba formal de todos los objetos Python aceptables.
9. Todos los efectos posibles de escritores fuera del inventario solicitado o del árbol congelado. El barrido de referencias es evidencia de cobertura estática, no una demostración de ausencia de accesos dinámicos con nombres construidos.
10. Seguridad de las heurísticas de `_actualizar_cuerpo` preexistentes. Se inspeccionó su interacción con el diseño; no se reabrieron ni certificaron las rondas de #146, ni se dan #184/#192 por cerradas.

## Cierre

El núcleo de comparación es defendible como lema sobre un snapshot de cadenas y una sustitución estricta de campos. **El diseño tal como está no acredita su promesa operativa:** el escritor pierde texto del cuerpo conservado y la fusión puede modificar datos ajenos a la lista blanca. Se requieren cambios concretos de frontera, contrato y cobertura antes de implementar y presentar el diff de R2. No propongo volver a localizar líneas con heurísticas.

sha256 del documento revisado, recalculado al cerrar: `fbb20a8dec74910b15a5ec7dc907589d211c396caf03c285bda77ca4c7882f56`
REQUIERE-REVISION
<!-- informe-literal:fin:cuan227 -->

## 2. Evidencia verificada por mí, contra la fuente

No di por bueno ninguno de los dos ALTOS por venir bien redactados. Los reproduje con una sonda
propia sobre el código de `main`, y **los dos salieron**:

**H-01** — `core/utils.py:270-271`. `write_md` hace `body.strip()` y `path.write_text(...)` con la
convención de la plataforma:

```
cuerpo pasado   : '# T\n\n## Notas\n\n    nota indentada del letrado\n\nCONSERVAR  \n'
cuerpo releído  : '# T\n\n## Notas\n\n    nota indentada del letrado\n\nCONSERVAR\n'
¿sobrevive el ORIGINAL? False
```

Y sobre un fichero con `CRLF`, el cuerpo vuelve del disco en `\n` y se reescribe en `\r\n`:
`b'---\r\na: 1\r\n---\r\n\r\n# T\r\n\r\nnota\r\n'`. La tercera mitad del hallazgo también sale:
`_FM_RE` termina en `\n---\s*\n`, así que un fichero con `'\n  \n'` entre el frontmatter y el
cuerpo **iguala** al canónico sin que nadie haya escrito la plantilla a mano.

**H-02** — `core/case_manager.py:1676` y `:266-295`. `update_pull_state` escribe en la lista
**superior** y deja el espejo de `meta` como estaba; `_fusionar_expedientes(superior, espejo)`
aplica el espejo **encima**:

```
lista TOP LEVEL : [{'id': '10', 'element': 'extrajudiciales',        'last_sync': '2026-09-11'}]
ESPEJO en meta  : [{'id': '10', 'element': 'expedientes_judiciales'}]
_fusionar(...)  -> [{'id': '10', 'element': 'expedientes_judiciales', 'last_sync': '2026-09-11'}]
```

El `element` **vuelve atrás**. Un `update_meta` que reutilizara esa fusión para fijar solo la
cuantía revertiría un dato ajeno a su lista blanca, en silencio.

Los otros siete se adjudican en el §10 del diseño, uno a uno.

**Lo que el revisor declaró SIN VERIFICAR y sigue sin verificarse:** la suite con las dos semillas
(su Python de sistema no trae `pytest-randomly`), la genealogía del commit (sin `.git`), el
comportamiento sobre los `_caso.md` reales del Drive, y la concurrencia real de procesos — su
escenario de H-09 es una intercalación dirigida en un proceso, no una carrera medida.
