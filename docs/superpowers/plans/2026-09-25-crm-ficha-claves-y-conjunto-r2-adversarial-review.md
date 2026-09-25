---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto.md
objeto_rev: "1"
commit: 0177559
ronda: "2"
revisor: Codex
veredicto: REQUIERE-REVISION
marcador_nonce: k4wz
sha256_informe: eeca36555fd1af94155d6b9e172fd86d8fed71c74008e63d6b991b242aa981c8
adjudicado_en: docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto.md §9
---

# Acta — R2 adversarial sobre el PLAN de `crm_ficha` (y sobre si el spec rev. 2 remedia la R1)

Objeto: el plan de implementación rev. 1 de `crm_ficha` (`MEJORAS #283` + `#288`) y, como
segundo encargo, el dictamen sobre los remedios del spec rev. 2 a los cuatro hallazgos de la R1;
los dos en `0177559`.

**Segunda ronda de la pieza, y la tercera ya está autorizada.** La tabla de `CLAUDE.md` da dos a
una pieza que escribe sobre datos de cliente —una sobre el diseño y otra sobre el diff—, y la R1
fue sobre el spec rev. 1. Nikolai autorizó expresamente el 2026-09-25 que esta R2 fuera sobre el
plan y que la del diff sea una **tercera** (spec §7). Fila de modelo: diseño de escritura sobre
datos de cliente → `gpt-6-astra` · `medium`.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.3` (binario `80f78947ad880e6e`), `gpt-6-astra` · `medium` — **releídos** del `turn_context` de `rollout-2026-09-25T17-47-24-01a0d93f-….jsonl` (`originator: codex_exec`) y de la cabecera del `_stdout.log`; velocidad `default` **afirmada** desde el lanzador, no acreditada |
| Objeto | copia `git archive 0177559` fuera del repo, sin `.git` (`head/`, 1.410 ficheros) |
| `sha256` del objeto | **idéntico al abrir y al cerrar**: los 1.410 digests, comparados por mí por ruta y contenido |
| `sha256` del informe | `eeca36555fd1af94155d6b9e172fd86d8fed71c74008e63d6b991b242aa981c8` |
| Tokens | 323.153 |
| Veredicto | `REQUIERE-REVISION` — 9 hallazgos: 2 `alta`, 7 `media` |

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:k4wz -->
Higiene inicial: conforme; solo estaban `MANDATO.md`, `head/` y `_stdout.log`.

# R2 adversarial del plan de `crm_ficha` y del spec rev. 2

Objeto: plan `docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto.md` y spec rev. 2 `docs/superpowers/specs/2026-09-25-crm-ficha-claves-y-conjunto-design.md`, en la extracción atribuida por el mandato al commit `017755917d1b7681074c9f2ee67d645e6e480fad`. En adelante, «plan» y «spec» designan esos documentos; las rutas de fuentes son relativas a `head/`. No se ha implementado el plan ni modificado `head/`.

El diseño mejora sustancialmente la R1, pero el plan necesita revisión antes de ejecutarse: abre una transición en la que `id_crm` se acepta y se ignora, permite vincular por ID una ficha cuyos identificadores declarados la contradicen, pierde la declaración de ciertos teléfonos antes de auditarla y contiene incompatibilidades reproducibles con los tests. No cuestiono la lista completa ni propongo desvincular o pisar datos.

## 1. Cobertura del spec rev. 2

No: todas las áreas tienen una tarea nominal, pero no todas las reglas tienen construcción inequívoca y prueba discriminante.

| Decisión o regla | Construcción prevista | Prueba y cobertura faltante |
|---|---|---|
| §2.1 lista completa, §4 B.1 igualdad | T5 + T6 | Sobrantes en los tres bloques, ceros en contrarios/colaboradores y multiplicidad cubiertos en funciones puras. Falta un caso CLI con FALTA y SOBRA simultáneos. |
| §2.2 rechazo, A.1 sin pérdida | T1 + T4 | Duplicados en tres niveles y alias cubiertos. El test llamado «con su línea» no afirma ninguna línea; merge solo se prueba acompañado de alias. No hay prueba CLI de cero writers para estas entradas. H-04. |
| §2.3 no desvincular/no pisar | Conserva `ensure_*` y `_COMPLETABLES_*`; T6 | No hay test del completado real con dato distinto y espía de PUT. El doble de `ensure_*` no cubre efectos internos. H-01. |
| §2.4 lógica pura en core | T1-T3 + T5 | Auditorías y validación estructural sí. `validar_id_crm` figura en File Structure, pero ninguna tarea define su firma/cuerpo/test: T6 describe la comparación de nombre en la orquestación. H-09. |
| §2.5 alcance de VERIFICADA y notas | T6; se conserva auditoría de notas | Notas truncadas y HTML tienen tests existentes. Hay que preservar su acumulación con faltan/sobran/datos; cambiar la frase rompe el positivo antiguo. H-07. `firmante` queda correctamente fuera. |
| A.2 claves conocidas, ruta y sugerencia | T2 | Hay casos en los tres niveles y problemas agregados. El empate real de `difflib` no da la sugerencia esperada por dos tests. H-07. Falta el control sin sugerencia cuando no hay candidata cercana. |
| A.3 tipos | T2 | Solo se prueban estructuras en `apellido1` y `notas_html`; falta matriz mapping/lista en cada escalar de ambos roles y `firmante`, y `cliente_propio: {}`. Los controles null/ausente no están separados exhaustivamente; varios antiguos dejarían de llegar a su aserto. H-07/H-09. |
| A.4 identidad estable | T3 + T6 | Rechazo sin identidad y formas de ID en contrario; test CLI de contrario por ID. Faltan colaborador por ID, ID inexistente/GET fallido, segunda parte inválida antes de cualquier writer, y dos corridas con estado. H-01/H-06. |
| A.5 todos los problemas juntos | T2 | Agrupa errores del diccionario superviviente. T1 aborta en la primera repetida; no entrega todos los duplicados ni los combina con problemas semánticos. H-04. |
| B.2 datos declarados | T5 + T6 | Apellido vacío/distinto, móvil normalizado y provincia desconocida. Falta recorrer todos los campos con lecturas iguales/vacías/distintas, en ambos roles y tanto recién creados como existentes. H-02/H-03/H-09. |
| B.3 veredicto | T6 | FALTA/SOBRA/DATO y lectura fallida previstos. Falta prioridad del fallo conocido sobre SIN VERIFICAR simultáneo, y prueba del texto de corrección humana. |
| B.4 parcial | T6 | Nuevo fallo de colaborador; existen fallo de contrario y comprobación de lo ya escrito. No se prueba cada writer: faltan cliente propio, notas y vínculos directos de la vía ID. |
| §5 exclusiones | T8 y preservación del código | No hace falta implementar apellidos, cliente propio múltiple, C6 ni investigar 653. La ubicación literal del preflight ID sí contradice dry-run sin CRM: H-08. |
| §6 centinelas/convergencia/mutantes | T2, T7 | Centinelas en DTO: pertinentes para cruces, no prueban mapas CRM. No existe la prueba de convergencia con estado. Mutantes: evaluación en §5 de este informe. |

### H-01 — La vía `id_crm` puede vincular una identidad contradicha por el propio YAML; B.2 llega después

- **Severidad:** alta. **Coste:** estructural.
- **Dónde:** spec A.4, B.2 y §6 «dato distinto → [DATO] sin PUT»; plan T6 Step 3, líneas 483-486. Código conservado: `scripts/crm_ficha.py:153-168`; `core/sudespacho_relations.py:1669-1681`, `1698-1736`, `2292-2340`.
- **Evidencia:** YAML sintético `{nombre: JUAN, apellido1: PEREZ, nif: '11111111H', id_crm: '1128'}`; GET 1128 devuelve `{nombre: JUAN, '1apellido': LOPEZ, nif_cif: '22222222J'}`. La comparación de nombre especificada devuelve `True` (`sondas-final.log`). T6 ordena vincular y solo después auditar los otros campos. Se detectaría el error, pero la ficha ajena ya quedaría vinculada y la herramienta no la desvincula. No hace falta suponer falso ningún dato real del autor. La vía NIF/email actual sí trata conflictos de identidad antes de vincular; la vía ID la evita.
- **Evidencia adicional sobre «sin PUT»:** ejecuté `_completar_contrario_existente` real con IO doblado: apellido CRM `OTRO`, YAML `PEREZ`, email CRM vacío y email YAML declarado. Se emitió PUT de email pese a la discrepancia de apellido. T6 mantiene ese completado dentro de `ensure_*` antes de B.2. El test propuesto, que sustituye `ensure_c` y pide «cero llamadas de actualización nuevas desde el CLI», no ve ese PUT.
- **Afirmaciones contradichas:** «la corrida no busca ni crea, lee esa ficha por id [...] su nombre tiene que coincidir» no basta para la finalidad de identidad validada cuando otro identificador declarado la contradice; «dato distinto → [DATO] sin PUT» no queda garantizado por auditar después de `ensure_*`.
- **Remedio:** separar la resolución/lectura previa de los efectos. Antes de vincular por ID, comprobar al menos todos los identificadores declarados y los datos de nombre disponibles, sin resolver contradicciones escogiendo el ID. Si se exige cero escrituras ante discrepancias preexistentes, comprobarlas para todas las partes antes del primer writer, conservando la política de completar solo vacíos. Probar con el completado real y transportes doblados, incluyendo espías de todos los writers y conflicto en la segunda parte. Precisar en el spec que detectar una omisión producida durante la creación exige una lectura posterior y no promete deshacer la creación.

### H-02 — B.2 recibe DTOs que ya pueden haber borrado un valor declarado

- **Severidad:** media. **Coste:** acotado.
- **Dónde:** plan T5 `auditar_datos(..., declarado, ...)`, Step 3; spec B.2. `core/crm_ficha.py:81-95`, `135-141`; `core/sudespacho_relations.py:230-232`, `259-261`; `core/utils.py::normalize_es_phone`.
- **Reproducción:** `NuevoClienteContrario(nombre='A', nif='1', movil='+34').movil == ''`, comprobado con el DTO real. Sucede también con `telefono` y en colaboradores. El YAML trae un texto no vacío admitido por A.3; el constructor lo reduce a vacío. T5 manda saltar campos vacíos y T6 le pasa la parte resuelta, por lo que no queda información para distinguir esto de un campo ausente. El POST omite el móvil vacío; una relectura perfecta de los otros datos puede terminar VERIFICADA. Afecta a creados y existentes.
- **Afirmación contradicha:** «compara cada campo que el YAML declara no vacío» y la promesa «el YAML entero».
- **Remedio:** conservar la declaración original para la auditoría o rechazar antes de construir los teléfonos originalmente no vacíos cuya normalización produzca vacío. No es necesario introducir aquí una validación telefónica completa. Añadir control positivo para teléfono legítimo y tests de esta pérdida en los dos roles.

### H-09 — Faltan pruebas de integración exigidas expresamente por el spec

- **Severidad:** media. **Coste:** acotado.
- **Dónde:** spec §6; plan T2, T5-T7; matriz anterior.
- **Evidencia:** ninguna tarea añade el doble con estado ni las dos corridas de convergencia. T6 sustituye `ensure_*`, por lo que no ejercita GET/PUT fallidos del completado real. T5 prueba discrepancias de apellidos de contrario; `test_lo_que_el_yaml_no_declara_no_se_compara` es el único test de datos de colaborador y no exige fallo por ningún campo suyo. Quitar la auditoría solo para colaboradores o solo para partes `creado=True` no queda refutado por los nuevos negativos enumerados. El centinela del DTO no prueba el segundo mapa, DTO → propiedades CRM.
- **Afirmación contradicha:** Self-review «§6 → tests de T1-T6 y T7» y las filas explícitas «Convergencia», «GET o PUT de completar fallidos» y «fallar cada writer» del spec.
- **Remedio:** añadir una tarea de pruebas discriminantes con resolución/completado reales e IO doblado, doble persistente para dos ejecuciones, matriz de campos/roles/creación-existencia, cero writers ante entrada inválida y fallos de cada writer. Incorporar el test y la función pura de validación ID que anuncia File Structure. Mantener los controles positivos separados de negativos y las fixtures válidas salvo la propiedad atacada.

## 2. Código del plan contra código real

Las firmas de `get_cliente_contrario(id)`, `get_colaborador(id)`, `link_contrario(exp_id, id)` y `link_colaborador(exp_id, id, *, client=None)` existen y admiten las llamadas propuestas. Los GET devuelven mappings aplanados. `CLIENTES_PROPIOS_EV` es un diccionario: tomar sus claves es correcto. Los DTOs normalizan ambos teléfonos al construirlos; los centinelas `V_movil`/`W_telefono` no sufren esa normalización, por lo que sirven para destinos, aunque no para la normalización de teléfonos.

La fixture `caso_con_ficha` existe en `tests/test_crm_ficha_cli.py:12-33`: expediente 606; JUAN/PEREZ, NIF `00000000T`, **también móvil `600111222`**, ANA con email y notas. Las lecturas sintéticas deben incluir ese móvil. Las rutas `scripts.crm_ficha.get_*` aún no existen en head, pero T6 exige importarlas antes de usar los dobles: no es un error de API del plan final.

Las propiedades CRM propuestas sí coinciden con el código y el atlas, como se detalla en §7. No he encontrado un endpoint inexistente que invalide T5/T6. Sí estos defectos de código literal:

### H-03 — La normalización de provincia es asimétrica

- **Severidad:** media. **Coste:** trivial.
- **Dónde:** plan T5 Step 3, línea 433; `core/sudespacho_relations.py:1561-1575`; atlas `1924`.
- **Reproducción:** `provincia_canonica('barcelona')` devuelve `'Barcelona'`; `_texto('Barcelona')`, tal como se define en T5, devuelve `'barcelona'`. Su igualdad es `False` (`sondas-final.log`). Siguiendo literalmente las dos transformaciones prescritas, se informa discrepancia aun cuando el CRM guardó el literal correcto. El único test de provincia usa `Atlantida` y no detecta este falso negativo.
- **Afirmación contradicha:** «normaliza los dos lados» y la igualdad bajo las normalizaciones de escritura.
- **Remedio:** comparar `_texto(provincia_canonica(yaml))` con `_texto(crm)` después de comprobar por separado el `None`. Añadir provincia válida con caja/tildes distintas y CRM con el literal canónico. Si el autor pretendía esa composición, debe escribirla: no figura en la receta actual.

### H-04 — El lector no cumple su contrato uniforme de error ni la agregación prometida

- **Severidad:** media. **Coste:** acotado.
- **Dónde:** plan T1, funciones `_mapping_sin_perdida` y `leer_yaml_ficha`; spec A.5 y efecto en llamadores. `scripts/crm_ficha.py:78-85`; `scripts/crm_colaboradores_firmas.py:216-219`.
- **Reproducción con el bloque literal de T1:** `? [a,b]\n: c\n` produce `TypeError` al buscar la lista en `vistas`; `notas_html: ["*",\n` produce `yaml.parser.ParserError` en `yaml.parse`, que está fuera del `try`. Ninguna se convierte en `ValueError`. Con `a: 1\na: 2\nb: 1\nb: 2\n` solo se devuelve el problema de `a`. Evidencia: `sondas-final.log` y `run_review.py`.
- **Afirmaciones contradichas:** interfaz «lanza ValueError»; «Todos los problemas en un solo ValueError, no el primero». El contrato de mensajes y salidas de los llamadores depende de ese tipo de excepción. Se sigue abortando antes de escribir; no atribuyo a estas excepciones un éxito falso.
- **Remedio:** cubrir también el escaneo de eventos con la traducción de errores YAML, rechazar claves no admitidas/no hashables con ubicación y acumular duplicados detectables sin construir un mapping con pérdida. Delimitar expresamente lo que puede agregarse cuando la sintaxis impide continuar. Probar tipo de error y línea en el CLI y conservación de bytes en `apply`.

## 3. Los tests y el ayudante `_declara_fichas`

### H-05 — Una lectura no declarada en el doble se convierte en SIN VERIFICAR y puede dejar el test verde

- **Severidad:** media. **Coste:** acotado.
- **Dónde:** plan T6, `_declara_fichas` líneas 466-473 y política de fallo de lectura. `tests/test_crm_ficha_cli.py:36-63`, `485-497`, `518-552`; contraste con su guarda `184-200`.
- **Evidencia:** el helper literal ejecuta `c[str(i)]`/`k[str(i)]`. Un ID no declarado levanta `KeyError`, comprobado en `sondas-final.log`. Es una `Exception` que T6 convierte en SIN VERIFICAR y salida 0. `test_crm_ficha_orquesta_todo`, el positivo de entidades HTML y el test de vincular todos los contrarios comprueban salida 0 y sus efectos específicos, pero no exigen VERIFICADA ni ausencia de SIN VERIFICAR. Si la declaración se omite, se usa el ID equivocado o se audita una parte que no debía, ese defecto del arnés puede pasar como fallo legítimo de lectura. La guarda de red actual usa deliberadamente `BaseException` para impedir exactamente esta degradación.
- **Afirmación contradicha:** «cada test que llega a la verificación dice qué ficha devuelve el CRM para cada id» como preparación suficiente para no debilitar la evidencia.
- **Remedio:** el doble debe lanzar una excepción de arnés fuera de `Exception` para IDs no declarados; reservar excepciones de lectura explícitas para tests de SIN VERIFICAR. En los controles positivos, exigir la nueva certificación completa y que no aparezca SIN VERIFICAR. Comprobar llamadas a GET por ID cuando esa sea la propiedad.

No todo cambio de preparación debilita asertos. El test de dos colaboradores ANA/BEA que colapsan a 776 (`405-429`) exige literalmente «la corrida escribió 2, la lectura ve 1»: un `[DATO]` adicional no puede sustituir ese aserto. Además, no existe **una** ficha por ID coherente con ambos YAML; el helper debe declarar cuál devolvió el CRM, no fabricar dos fichas simultáneas ni alterar las partes para que coincidan. El positivo de vínculos (`228-244`) sí exige VERIFICADA y los tres `[ok]`, y por eso detectaría una lectura omitida, una vez actualizado el texto.

Otros falsos caminos:

- El test de duplicados «con su línea» solo busca `repetida` y el nombre; puede pasar sin ubicación.
- El test de merge usa `&b`/`*b`; puede pasar con la comprobación de merge eliminada. Un merge **no necesita alias**, como confirma la sonda `{<<: {nombre: A}}`.
- Al exigir identidad, el primer elemento de `test_se_valida_la_coleccion_ENTERA_antes_de_construir_nada` ya es inválido. Su `raises(ValueError)` puede pasar aunque se ignore el segundo. Hay que dotar de identidad al primer elemento y espiar la construcción si se quiere probar su nombre.
- El control de datos de T6 W-030A13 debe conservar el móvil de la fixture en la lectura. De lo contrario añade otra discrepancia accidental; el aserto específico del apellido sigue siendo necesario.

## 4. Orden y dependencias entre tareas

### H-06 — Se publica soporte de `id_crm` antes de que el CLI lo consuma

- **Severidad:** alta. **Coste:** estructural.
- **Dónde:** commits T3 → T4 → T5 → T6; `scripts/crm_ficha.py:157-163`; `core/sudespacho_relations.py:1669-1681`, `2292-2340`, `2436-2452`.
- **Evidencia:** T3 acepta y construye `{nombre: JUAN, id_crm: '1128'}` sin NIF/email. Hasta T6, el CLI llama incondicionalmente a `ensure_*`. Esos resolutores solo pasan NIF/email a `resolver_parte`; T3 dice expresamente que los payloads no leen `id_crm`. Por tanto, antes de T6 una entrada que T3 ya considera válida sigue el camino de creación en vez de leer y vincular 1128. El defecto existe aunque se arreglen todos los tests de T3.
- **Afirmación contradicha:** A.4 «la corrida no busca ni crea, lee esa ficha por id»; la separación en commits supuestamente verdes y ejecutables.
- **Remedio:** integrar aceptación de ID, DTO y consumo del CLI en un mismo commit, o añadir el campo de forma aditiva pero no habilitar la entrada hasta completar T6. Probar sobre cada frontera de commit que ninguna entrada aceptada por ID llama a creación.

### H-07 — Los pasos que dicen PASAN son incompatibles con los tests y DTOs actuales

- **Severidad:** media. **Coste:** acotado.
- **Dónde:** T2 Step 3/4; T3 Step 4; T6 Step 3/4; `tests/test_crm_ficha_cli.py:164`, `237`, `555-567`; `tests/test_crm_ficha_yaml_none.py`; `tests/test_crm_ficha_n_contrarios.py:38-42`, `92-97`.
- **Reproducción/evidencia:**
  - T2 incluye `id_crm` en las tuplas y manda construir recorriéndolas; el campo solo se añade al DTO en T3. Expandir esa tupla contra el DTO de head produce `TypeError: unexpected keyword argument 'id_crm'` (sonda). Hay que mover el campo o excluirlo explícitamente hasta entonces.
  - `difflib.get_close_matches` con la tupla literal sugiere `apellido2` para `apellido`, mientras dos tests de T2 exigen `apellido1`. Es un empate real, no una importación ausente.
  - Aplicando el validador literal T2 delante del loader actual se obtienen **2 fallos**: la nueva frase de cliente desconocido no contiene el literal exigido por el CLI, y el test que admite `OTRO_CLIENTE` contradice el catálogo cerrado.
  - Añadiendo la condición de identidad de T3 a esa sonda se obtienen **17 fallos** en las cinco suites del mandato: casos null/ausente, orden, mapping y dry-run carecen de identidad. El plan solo prevé añadir GETs a quince tests CLI; eso no arregla estos YAML. Véanse `fixtures-t2.log` y `fixtures-t3.log`. Son sondas de compatibilidad de reglas, no ejecución de una implementación completa.
  - T6 cambia el éxito a `VERIFICADA: vínculos y datos de la ficha`; el test positivo actual exige `VERIFICADA por lectura`. Añadir `_declara_fichas` no cambia esa desigualdad.
- **Afirmaciones contradichas:** «Los tests existentes de _escalar (octal, None) siguen pasando sin tocarlos»; «Ningún aserto se toca»; los Steps «PASAN».
- **Remedio:** incluir la migración explícita de fixtures en las tareas que endurecen la entrada: identidades sintéticas, `id_crm` para pruebas que dejan NIF/email vacíos, y una clave real no predeterminada del catálogo para probar conservación del cliente. Mantener la propiedad de los asertos; adaptar por escrito los literales del nuevo contrato. Resolver el empate de sugerencia sin convertirlo en alias de entrada. Coordinarlo con H-06.

### H-08 — El preflight de IDs está situado antes del corte de dry-run

- **Severidad:** media. **Coste:** trivial.
- **Dónde:** T6 Step 3, línea 485; spec §5; `scripts/crm_ficha.py:79`, `105-110`, `154`.
- **Evidencia:** T6 manda comprobar todas las partes por ID «justo después de cargar el YAML». En el CLI real, la carga precede al `if dry_run`. Implementado en esa posición, un dry-run con ID hace GET al CRM y puede fallar por indisponibilidad/nombre, aunque §5 excluye esa lectura. El test dry-run existente usa NIF/email, no ID, y no cubre la nueva rama.
- **Afirmación contradicha:** «--dry-run sigue sin leer el CRM».
- **Remedio:** ubicar el preflight después de las salidas dry-run/cancelación y antes del primer writer. Añadir dry-run con ID cuyos GETs fallen el test si se invocan.

T1 puede ser aditiva hasta que T2 conecte el loader, y T5 puede añadir las auditorías puras antes de conectarlas: esas transiciones no son por sí mismas defectos. T4 sustituye correctamente el lector antes de cualquier reescritura de `apply`.

## 5. Mutantes de Task 7

No he ejecutado un arnés futuro inexistente ni afirmo «ocho muertos». Evalué los tests literales y ejecuté el mutante de mappings contra la validación literal, conservando el loader/DTO real donde procede.

| Mutante | Evaluación de muerte por su propiedad |
|---|---|
| Quitar rechazo de duplicados | El `raises` de duplicados detecta la pérdida. No acredita línea ni cero writers. |
| Aceptar mappings en escalar | **Reproducido:** los casos `contrario.apellido1` y `notas_html` fallan con `DID NOT RAISE ValueError`; llegan al camino esperado. No extiende la cobertura a todos los campos. |
| Quitar sobrantes | El test 653 exige los dos IDs concretos de más: discriminante. |
| Counter por set | El aserto de multiplicidad es pertinente, pero el mutante debe seguir siendo un algoritmo ejecutable. Cambiar solo el tipo y conservar subscripción/resta incompatible puede matar por TypeError, no por pertenencia. |
| `auditar_datos` siempre `[]` | El test del apellido vacío lo mata por el aserto correcto. No prueba que el CLI llame a la función para cada rol y cada parte creada. |
| Cruzar asignaciones DTO | Los centinelas distintos lo detectan, siempre que el campo mutado esté incluido. No prueba cruces en `CAMPOS_*_CRM`; conviene fijar el inventario esperado independientemente de la tupla que implementa el loader. |
| Parcial calcula sobrantes | El test T6 observa salida, no cálculo. T6 ya ordena imprimir solo faltan: calcular `sobran` y descartarlo podría sobrevivir y no sería un defecto observable. Definir el mutante como **emitir/usar** sobrantes en parcial. |
| Quitar identidad obligatoria | El test sin identificadores exige el diagnóstico concreto y lo detecta. No cubre bypass del consumidor ID ni validación de identidad incompatible. |

El precedente `tests/_mutantes_mejoras_214.py` **no** aplica cada mutante sobre copia: escribe en `RAIZ/OBJETIVO` y restaura; además considera muerto cualquier retorno distinto de 0 después de una base verde (`_corre`/`main`). La instrucción explícita de T7 de usar copias prevalece y debe implementarse, no copiarse ese comportamiento. Seleccionar el test por nombre no basta para excluir error de colección/setup o arnés roto. Exigir base verde, mutante aplicable una vez, ejecución del test objetivo y fallo de su aserto, conservando el resultado detallado.

Faltan mutantes para desconectar el lector en uno de los dos consumidores, quitar merge sin alias, omitir un rol/parte creada en la auditoría, quitar la validación ID o moverla tras un writer, permitir GET en dry-run y eliminar el control de discrepancias preexistentes. Son fronteras distintas de las ocho mutaciones globales. No hace falta multiplicar mutantes equivalentes: cada uno debe corresponder a una propiedad y un test positivo/negativo aislado.

## 6. Remedios de la rev. 2 a la R1

El informe literal embebido de R1 se extrajo y canonicalizó: su SHA-256 coincide exactamente con `42c9c2a575753cd38b2c830f4130ce574db12986a4ee2939d961c3b65b756c6b`. Dictamen sobre los remedios, sin adjudicar por el tono del autor:

| Hallazgo R1 | Dictamen | Razón |
|---|---|---|
| H-01, claves perdidas antes de validar | **Real** | A.1 actúa antes de construir el diccionario y alcanza también `apply`. Repetidas, alias y merge se rechazan; comprobé duplicados y merge sin alias. Los escapes de excepción/agregación de H-04 de esta R2 son defectos pendientes, pero no vuelven a consolidar silenciosamente el duplicado de la R1. |
| H-02, estructuras/coerciones/nombres vacíos | **Real** | A.3 y el validador literal rechazan tipos distintos de texto/null, verifican nombre tras strip y separan falsos inválidos del default. La regresión de fixtures no convierte en cosmética la mejora. Faltan los tests de toda la clase que se enumeran en §1. |
| H-03, IDs exactos con datos que no llegaron | **Incompleto** | B.2 relee tanto partes creadas como existentes: en el diseño no hay excepción para `creado=True`. Detectaría el apellido vacío de 1128/1129 y el completado que no dejó el valor. Sin embargo, el DTO puede haber perdido la declaración (H-02 de esta R2), la provincia positiva falla (H-03), y el test CLI no ejercita el completado real ni garantiza «sin PUT» (H-01/H-09). |
| H-04, relanzamiento sin identidad crea otra ficha | **Incompleto** | La identidad obligatoria y el ID explícito dan una salida persistente real al caso original. La comprobación solo por nombre no impide una contradicción con NIF/email/apellidos declarados, falta el doble de dos corridas y la transición T3→T6 vuelve a permitir creación con ID explícito. H-01/H-06. |

Ninguno es meramente cosmético. Los dos primeros cambian la frontera adecuada; los dos últimos requieren completar la integración y las pruebas.

**Precisiones sobre B.2 y «[DATO] falla sin escribir».** Una lectura final puede detectar tanto datos de creación omitidos como campos existentes no completables. Los fallos de GET/PUT de completado que dejen el valor ausente/distinto se reflejarían en esa lectura; si la lectura final también cae, la cobertura queda SIN VERIFICAR. Una incidencia interna cuyo resultado finalmente sí coincide no necesita falsear el veredicto de datos para reproducir el log: B.2 es verificación por resultado, no auditoría histórica de cada petición.

En cambio, ni el spec ni T6 construyen una transacción sin efectos: la lectura de datos viene después de crear/completar/vincular y escribir notas. No se puede afirmar que todo `[DATO]` significa cero escrituras de esa corrida. Sí debe impedirse escribir ante un conflicto preexistente comprobable, y especialmente vincular una identidad ya contradicha. La reparación automática no es necesaria para remediarlo. El test «cero actualizaciones nuevas desde el CLI», con `ensure_*` sustituido, no prueba esa garantía.

## 7. Propiedades CRM pendientes de medir

El ámbito está bien delimitado a los mapas de campos y no invalida las firmas ni los endpoints previstos. De hecho, las tres propiedades presentadas como pendientes ya tienen evidencia en este objeto:

- `1apellido`, `2apellido`, `nif_cif`: payload en `core/sudespacho_relations.py:872-882`; GET en `1751-1754`; atlas `docs/CRM_SUDESPACHO_ATLAS.md:1892-1926`; contrato `docs/INTEGRACION_SUDESPACHO.md:746`, `769-774`.
- `telefono` → `telefono1`, `movil`, dirección, población y CP: escritura y GET coinciden con ese atlas. `provincia` es un Select con literales, incluido `Barcelona`, no un texto que haya que inventar.
- Colaborador: el DTO no separa apellidos y el mapa propone correctamente nombre completo. El contrato confirma `nif_cif` y `telefono1`; `get_colaborador` devuelve las propiedades aplanadas.

No he encontrado un mapa inventado que necesite descubrir un campo antes de poder escribir T5. Recomiendo sustituir el «por fijar» por estas referencias concretas y mantener la regla del spec: si al implementar surge una discrepancia no resuelta por fuente, no adivinar; medirla antes de codificar ese campo. No se puede acreditar aquí el comportamiento vivo del servidor, pero esa limitación no justifica omitir controles positivos de provincia ni las pruebas offline por campo.

## Evidencia y no mutación

- Inventario inicial: 1.410 ficheros en `head/`. `hashes-apertura.json` registra SHA-256 de los bytes de cada fichero extraído, sin normalizar CRLF, junto con su ruta relativa.
- Ejecución sobre `scratch/`, copia local de `head/`, mediante `run_review.py`. Python 3.14, sin bytecode ni caché pytest, temporales y registro bajo este directorio, sockets bloqueados y datos sintéticos. No se accedió a CRM, Drive ni al repositorio real.
- `baseline.log` contiene la primera ejecución de las cinco suites del mandato más `test_crm_colaboradores_firmas_cli.py`. La verificación final de esas seis suites en `baseline-final.log` dio **107 passed in 120.00s**, con **código Python/pytest 0**, semilla 777. `fixtures-t2.log` y `fixtures-t3.log` registran las sondas de incompatibilidad; `sondas-final.log`, los bloques literales y comportamientos indicados. Los programas no reimplementan una supuesta versión final del CLI.
- Las sondas de T2/T3 anteponen las reglas nuevas al loader actual para aislar su efecto sobre las fixtures: no se presentan como commits implementados. Los fallos de esas sondas no son fallos de la línea base.
- Cierre: hashes-cierre.json contiene los mismos **1.410 ficheros**. Comparación por ruta y SHA-256: **idénticos; cero ficheros añadidos, eliminados o modificados en head/**.

## Lo que intenté refutar y NO pude

- La igualdad por multiplicidad, con IDs resueltos correctamente, detecta sobrantes y colapsos. No encontré un contraejemplo matemático ni necesidad de cambiar la decisión de lista completa.
- La corrección de duplicados a nivel de construcción actúa antes de la pérdida. El merge sin alias se rechaza y `&amp;` literal no se confunde con un alias. Estos resultados son compatibles con el prototipo del autor.
- Las firmas y propiedades CRM enumeradas en §7 existen en el código/contrato; no encontré un endpoint nuevo oculto.
- La mutación de aceptación de mappings muere por el `raises(ValueError)` de su propiedad, no por importación, fixture ni red.
- La política de completar solo lo vacío no necesita ampliarse a apellidos para **detectar** el caso de la R1. La auditoría final aporta una mejora real aunque su garantía de ausencia de efectos sea insuficiente.
- El aserto específico de multiplicidad del CLI no puede satisfacerse con un `[DATO]` incidental. El ayudante no destruye por sí mismo todos los asertos existentes.
- La parcial que solo informa faltantes y mantiene código 1 no abre un falso VERIFICADA. `None` debe seguir significando lectura ausente, no bloque vacío.
- No encontré razón para implementar C6, ampliar el catálogo de clientes propios, desvincular automáticamente o investigar el origen del 653 como requisito de este cambio.

## SIN VERIFICAR

- Censo de las 14 fichas reales y ejecución histórica del prototipo del autor: no accesibles en este encargo. No he dado por falsa ninguna de esas mediciones; ningún hallazgo depende de ello. Solo he reproducido variantes locales del código propuesto.
- Estado real de 653/1128/1129, normalizaciones vivas del CRM, automatismos, concurrencia y completitud efectiva de GET: sin red, por mandato.
- No existe todavía implementación final ni arnés T7: no se acredita una suite final del plan, ocho mutantes muertos, `session_close` ni revisión de diff. Las inferencias sobre T6 se identifican como seguimiento del orden que prescribe, no como un CLI futuro ejecutado.
- La extracción carece de `.git`: el commit es el anclaje aportado por el mandato, no una procedencia que pueda comprobarse con Git aquí. Sí se verifica integridad de todos los bytes entregados entre apertura y cierre.
- El objeto no me ha desbordado; he contestado los siete puntos. Las limitaciones anteriores son de acceso y de inexistencia de la implementación, no cobertura omitida por esfuerzo.

REQUIERE-REVISION
<!-- informe-literal:fin:k4wz -->

## 2. Evidencia verificada por mí contra la fuente

- **Digest.** Recomputado sobre el fichero entregado (UTF-8, LF, un único salto final): coincide
  con el que da el revisor en su mensaje final (`eeca3655…`).
- **El objeto es el commit.** `head/` se extrajo con `git archive 0177559`. El revisor acredita la
  integridad de los bytes entre apertura y cierre, no la procedencia, y lo declara en su «SIN
  VERIFICAR».
- **Los nueve se reproducen contra la fuente, no contra el informe:**
  - **H-01:** `core/sudespacho_relations.py:1669-1736` —`_resolver_o_crear_contrario` resuelve por
    NIF o email y `_completar_contrario_existente` rellena lo vacío sin comparar nombre ni
    apellidos— y el Step 3 de la Task 6 del plan, que vincula por `id_crm` tras comparar **solo**
    el nombre y deja los demás datos para después de escribir.
  - **H-02:** `NuevoClienteContrario(nombre="A", nif="1", movil="+34").movil == ''`, con el DTO real.
  - **H-03:** `provincia_canonica('barcelona')` devuelve `'Barcelona'`, y el `_texto` de la Task 5
    lo pasa a minúsculas: los dos lados nunca coinciden.
  - **H-04:** el bloque literal de la Task 1, ejecutado tal cual: una clave lista da `TypeError`;
    una sintaxis rota con `*`, `ParserError`; dos claves repetidas, solo la primera.
  - **H-05:** `KeyError` es `Exception`, y `test_crm_ficha_orquesta_todo`
    (`tests/test_crm_ficha_cli.py:36-64`) solo exige la salida 0.
  - **H-06:** la Task 3 acepta `id_crm` y el CLI (`scripts/crm_ficha.py:157-163`) sigue llamando
    a `ensure_*`, que sin NIF ni email crea, hasta la Task 6.
  - **H-07:** `difflib` sugiere `apellido2` para `apellido`; el literal que exige
    `tests/test_crm_ficha_cli.py:164`, el `OTRO_CLIENTE` de `tests/test_crm_ficha_yaml_none.py:114-115`
    y el positivo de `tests/test_crm_ficha_cli.py:237`. **Y dos negativos que el revisor no citó:**
    `:283` y `:403` afirman `"VERIFICADA por lectura" not in r.output`, que con el literal de éxito
    nuevo pasarían **siempre**.
  - **H-08:** `scripts/crm_ficha.py:79` carga el YAML; el corte de `--dry-run` está en `:105`.
  - **H-09:** ninguna tarea construye las filas «Convergencia», «GET o PUT de completar fallidos»
    ni «fallar cada writer» del spec §6.
- **Higiene.** El revisor declara en su primera línea un directorio sin ficheros ajenos.
- **Tiempos.** El rollout arranca a las 17:47:24; `INFORME.md` se escribió a las 18:11:42 y `exec`
  salió a las 18:11:51 con `exit=0` (`_exit.txt` del lanzador, que es la señal de fin del vigía).
- **Adjudicación:** `docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto.md` §9.
