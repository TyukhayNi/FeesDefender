---
tipo: revision-adversarial
objeto: "diff del autorrelleno de fichas de colaborador desde la firma del correo"
objeto_rev: "rama claude/beautiful-gates-438572, commit 8e7a796"
commit: 8e7a796
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: k7qd
sha256_informe: 5f81382f6cb1c318c197d8ea8b2aef1f59c393dde6fcbb2cb84d8b71c0a8d9e7
adjudicado_en: docs/superpowers/plans/2026-09-04-colaboradores-firma-autorrelleno.md §12
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1.** El §1 conserva la voz del revisor sin una coma
> cambiada; el §2 es la evidencia que verifiqué por mi cuenta.
>
> **La adjudicación NO está aquí:** va embebida en el plan
> (`docs/superpowers/plans/2026-09-04-colaboradores-firma-autorrelleno.md`), que es el
> documento que la decisión modificó. Esta acta es el archivo de la voz del revisor, no un
> segundo hogar de la decisión.
>
> **Una ronda, por radio de daño** (`CLAUDE.md` §«Cuántas rondas»). La pieza escribe en el
> CRM del cliente pero **sólo rellena lo vacío**: no decide quién puede escribir sobre qué
> copia. **El diff REMEDIADO no se ha vuelto a revisar**, y se dice: la regla da una ronda
> para esta clase de pieza, y encadenar una segunda porque la primera encontró algo es un
> argumento que nunca se agota. Lo que sí se hizo, y consta en el §2, es **volver a
> ejecutar los contraejemplos concretos del revisor** contra el código remediado.
>
> **Objeto:** dos copias externas de `bf81fa9` (base) y `8e7a796` (head),
> montadas con `git archive` fuera del repo. El revisor declaró que **no acredita la
> genealogía** —sus copias no tienen `.git`— y verificó contenido, que es lo correcto.
>
> **Por qué el bloque archiva DOS textos del revisor, y no uno.** Mi mandato le pidió el
> veredicto de un set de cuatro palabras **que me inventé yo**; el vocabulario real del
> proyecto lo fija el guard `_VEREDICTOS_REV` de `tests/test_docs_gobernanza.py`, y la
> palabra que devolvió no estaba en él. **Traducirla yo es exactamente lo que esta acta
> existe para hacer imposible**, así que hubo una segunda llamada pidiéndole **sólo** el
> veredicto, con instrucción expresa de no reatacar el objeto ni tocar su informe.
> Comprobado por `sha256` antes y después: el informe no cambió. Los dos textos van juntos
> dentro del bloque porque los dos son su voz; esta explicación va fuera porque es mía.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:k7qd -->

Higiene: al abrir, el workdir contenía exclusivamente MANDATO.md; no había otros ficheros que pudieran contaminar esta ronda.

# Revisión adversarial R1 del diff de firmas de colaboradores

## Objeto y custodia

Se ha comparado el contenido de `../base/` y `../head/` para los ficheros modificados de producción y documentación indicados en el mandato, y leído el código nuevo y sus cuatro módulos de tests. El spec y el plan se han consultado para contrastar las garantías, sin ejecutar sus instrucciones de implementación. Las reglas ordinarias del proyecto que exigen trabajar en el checkout habitual, usar Git o consultar el CRM no se han seguido: contradicen el mandato específico de esta revisión.

Las copias no tienen `.git`. **No acredito que correspondan a los commits declarados** `bf81fa98a769dd40ca8ffcf005702741241b8b82` y `8e7a7961331f07a8c4eb5d70efaf72e82a783688`. Los hallazgos se refieren al contenido suministrado, con líneas de `head`, no a su genealogía.

SHA-256 de `../head/core/email_firmas.py` **al abrir**:

```text
5277b1f91c96d1c634c63a2d41ff5cd20825ef554fc7ae64e422fa7213a3e25f
```

No se ha escrito en `base` ni en `head`. La ejecución y las mutaciones se han realizado en `informe/copia/`, con temporales dentro de `informe/`. Las identidades y teléfonos de las sondas son sintéticos. Las operaciones CRM descritas abajo son dobles locales: ninguna escritura se ha enviado al CRM.

## Resultado

**Hay cambios requeridos.** La protección del email del ancla funciona en los casos comprobados, pero no protege la pertenencia de los teléfonos. Se ha reproducido el recorrido completo desde dos firmas hasta un PUT simulado que pone el teléfono de Ana en la ficha de Berta. También hay una conversión en `apply` que neutraliza el rechazo de teléfonos reinterpretados como octales, y varias vías que convierten incertidumbre en ausencia o éxito.

## Hallazgos

### H-01 — CRITICO — La ventana conserva el email correcto y el teléfono de otra persona

**Localización:** `core/email_firmas.py:204-221`, `:523-528`; consumidor `scripts/crm_colaboradores_firmas.py:218-226`.

**Entrada concreta**, cuerpo de un `.eml` `text/plain; charset=utf-8`:

```text
ENGEL&VOLKERS
*Ana*
Móvil: 611111111
ana@engelvoelkers.com

ENGEL&VOLKERS
*Berta*
Móvil: 622222222
berta@engelvoelkers.com
```

**Resultado ejecutado:** ambos consolidados tienen `movil='611111111'` y `veredicto_movil='ENCONTRADO'`. El de Berta debería conservar su `622222222` o abstenerse si no sabe separar los bloques. Su ventana incluye las dos firmas y `.search()` toma el primer móvil, aunque su email sea el de la segunda ancla.

Se ejecutó además `apply --confirmar` sobre un YAML cuya lista contenía sólo `nombre: BERTA`, `email: berta@engelvoelkers.com`. Escribió `movil: '611111111'`; `cargar_ficha_yaml` lo aceptó, y `_completar_colaborador_existente('berta-id', ...)`, con móvil CRM vacío, llamó al escritor simulado con `{'movil': '611111111'}`. **No hace falta que se dé de alta a nadie ni que se sobrescriba un campo ocupado para corromper la ficha.**

La misma frontera falla hacia delante, incluso con marcador explícito:

```text
Escribe a berta@engelvoelkers.com
-- 
ENGEL&VOLKERS
Móvil: 611111111
ana@engelvoelkers.com
```

También produce una firma de Berta con el móvil de Ana: el marcador posterior al ancla no limita `fin`.

**Cobertura engañosa:** `tests/test_email_firmas.py:353`, `test_el_caso_espejo_dos_firmas_seguidas_la_segunda_compacta`, comprueba los emails pero no la pertenencia de los campos extraídos. Los 250 tests pasan con este defecto presente. La corrección debe cerrar los límites de cada firma y la pertenencia de sus campos; conservar el email del ancla sólo cierra una parte del problema.

**Evidencia:** `repros.json`, claves `vecinas`, `marcador_despues`, `vecinas_hasta_put`.

### H-02 — ALTO — El patrón atribuye una dirección de otro dominio a una persona de E&V

**Localización:** `core/email_firmas.py:47-49`, `:194`, `:221`.

**Entrada concreta:**

```text
ENGEL&VOLKERS
Móvil: 611111111
ana@engelvoelkers.com.tercero.example
```

**Resultado ejecutado:** firma y consolidado para **`ana@engelvoelkers.com`**, móvil `611111111`, `ENCONTRADO`. Esa dirección exacta no figura en el texto: es el prefijo de otra dirección cuyo dominio es `engelvoelkers.com.tercero.example`.

La expresión no exige el final del dominio. El filtro «una dirección de otro dominio no se mira» no se cumple y puede alimentar la ficha de Ana con un teléfono externo. Hace falta reconocer la dirección completa antes de comparar el dominio.

**Evidencia:** `repros.json`, `dominio_sufijo`.

### H-03 — ALTO — Una cabecera de cita partida antes de «escribió» ancla una firma ficticia

**Localización:** `core/email_firmas.py:160-165`, `:197`.

**Entrada concreta:**

```text
ENGEL&VOLKERS
Móvil: 611111111
ana@engelvoelkers.com

El 12 agosto, Berta <berta@engelvoelkers.com>
escribió:
> Hola
```

**Resultado ejecutado:** Berta recibe `movil='611111111'`, `ENCONTRADO`, aunque sólo aparece en la atribución de una cita. La función mira la línea del email y la anterior, pero no la siguiente. No es un idioma fuera del alcance declarado: es el verbo español soportado y la cabecera que el propio docstring de `localizar_bloques` describe como excluida.

La separación de cabeceras debe abarcar el bloque de atribución completo; reconocer sólo dos posiciones concretas deja abierto el cruce de identidad que motivó el filtro.

**Evidencia:** `repros.json`, `cita_verbo_siguiente`.

### H-04 — ALTO — Dos móviles incompatibles en una misma firma no producen conflicto

**Localización:** `core/email_firmas.py:523-528`, `:593-595`.

**Entrada concreta:**

```text
ENGEL&VOLKERS
Móvil: 611111111
Móvil: 622222222
ana@engelvoelkers.com
```

**Resultado ejecutado:** `movil='611111111'`, `veredicto_movil='ENCONTRADO'`. Ambas líneas tienen la misma etiqueta y procedencia; no existe información que permita elegir una. La segunda desaparece en `.search()`, antes de que `consolidar` pueda comparar los valores.

La propiedad 9 se cumple para dos `DatosFirma` discrepantes, pero falla si el conflicto está dentro de un bloque. Hay que conservar la multiplicidad o declarar incertidumbre en la lectura, antes de consolidar. La mutación M2 demuestra que los tests protegen el vacío de un conflicto ya detectado; no protegen su detección completa.

**Evidencia:** `repros.json`, `dos_moviles`.

### H-05 — ALTO — `apply` convierte un teléfono octal inválido en una cadena aceptada

**Localización:** `scripts/crm_colaboradores_firmas.py:257-261`; validación neutralizada en `core/crm_ficha.py:47-70`.

**Entrada concreta**, YAML:

```yaml
colaboradores:
- nombre: BERTA
  email: berta@engelvoelkers.com
  movil: 0601234567
- nombre: ANA
  email: ana@engelvoelkers.com
```

Corpus: el `.eml` de H-01, que permite rellenar el móvil vacío de Ana.

**Resultado ejecutado:** antes de `apply`, `cargar_ficha_yaml` rechaza el móvil de Berta porque PyYAML lo ha interpretado como el entero octal `101005687`. Después de `apply --confirmar`, el YAML contiene `movil: '101005687'` para Berta y `movil: '611111111'` para Ana. La carga posterior acepta el teléfono corrupto de Berta como cadena de nueve dígitos.

El bucle de serialización recorre **todos** los teléfonos, también los que no se rellenaron. El comentario afirma que `_escalar` rechazará el entero, pero la conversión previa a `str` elimina la información de tipo necesaria para rechazarlo. No se puede reconstruir el literal original a partir del entero; hay que validar antes de reserializar y no legitimar datos preexistentes inválidos al completar otra persona.

**Evidencia:** `repros.json`, `yaml_octal`. No es el falso ejemplo con dígitos 8/9: `0601234567` sí se resuelve como octal.

### H-06 — MEDIO — Se clasifica la procedencia por el inicio de la ventana, no por la firma

**Localización:** `core/email_firmas.py:221`, `:301-302`.

**Entrada concreta**, sin salto final:

```text
Conforme.

> ENGEL&VOLKERS
> Móvil: 611111111
> ana@engelvoelkers.com
```

**Resultado ejecutado:** el bloque tiene `linea=1` y `procedencia='directo'`, aunque toda la firma está citada. `inicio` alcanza «Conforme», y `atribuir` consulta la procedencia de esa línea. Al consolidarlo con una firma directa independiente de Ana con `622222222`, sale `CONFLICTO` y campo vacío; la jerarquía declarada debería elegir el directo `622222222`.

El mismo fallo se reprodujo con CRLF y con variantes de salto final y cita vacía final. El recuento de `desmarcar(...).split('\n')` se conserva en esas variantes: **ese invariante no demuestra que se esté consultando la línea pertinente**.

Hay además un segundo contraejemplo al comentario de `zonas_citadas` (`:236-245`): no es cierto que `splitlines()` y `split('\n')` sólo difieran por el segmento vacío final. La cadena Python

```python
'a\u2028b\u2028c\u2028d\u2028e\n--\n> ENGEL&VOLKERS\n> Móvil: 611111111\n> ana@engelvoelkers.com'
```

produce zonas `[(2, 5)]`, pero bloque `linea=7`, `directo`. Aquí el marcador sí hace empezar el bloque en la firma: el desfase se debe a U+2028. Hace falta una convención de líneas compartida y conservar la posición del ancla o del contenido cuya procedencia se decide.

**Evidencia:** `repros.json`, `cita_corta`, `cita_corta_con_directa`, `indices_*`, `indice_unicode_aislado`.

### H-07 — MEDIO — Una etiqueta de móvil compuesta oculta el fijo real y se afirma que falta

**Localización:** `core/email_firmas.py:388-390`, `:523-528`, `:588-589`; leyenda en `scripts/crm_colaboradores_firmas.py:62`.

**Entrada concreta:**

```text
ENGEL&VOLKERS
Teléfono móvil: 611111111
Telf: 931111111
ana@engelvoelkers.com
```

**Resultado ejecutado:** móvil `611111111`, pero `telefono=''` y `veredicto_telefono='FIRMA_SIN_CAMPO'`. La firma sí trae el fijo `931111111`.

`_RE_FIJO.search()` también casa con «Teléfono móvil» y captura `móvil: 611111111`; la limpieza lo rechaza, y ya no se busca la línea `Telf:` posterior. El comentario que dice que se prueba móvil primero no supone consumo ni exclusión: son dos búsquedas independientes sobre el mismo texto. Hay que separar las etiquetas y distinguir ausencia de fallo de lectura. El aviso del informe sobre la incertidumbre del cargo no cubre este falso negativo de teléfono.

**Evidencia:** `repros.json`, `fijo_despues_compuesta`.

### H-08 — MEDIO — Los fallos de consulta al CRM se presentan como inexistencia o campo vacío

**Localización:** `scripts/crm_colaboradores_firmas.py:90-103`, `:108-117`.

**Entrada concreta:** consolidado de Ana con móvil `611111111`, `ENCONTRADO`; dos respuestas simuladas:

1. `resolver_parte` lanza `RuntimeError('consulta fallida')`.
2. `resolver_parte` devuelve `id='466'`, pero `get_colaborador` lanza `RuntimeError('500')`.

**Resultado ejecutado:** en el primer caso la fila afirma `no existe como colaborador` y `el CRM lo tiene vacio`. En el segundo afirma `id 466` y `el CRM lo tiene vacio`. Ninguno conserva ni muestra el fallo.

Esto contradice literalmente el docstring: «el informe lo dice; no se afirma que el campo del CRM esté vacío cuando no se pudo mirar». El estado desconocido debe viajar separado de ausencia y de ficha leída. Este hallazgo afecta a la información con la que el usuario revisa la propuesta; no demuestra por sí solo que el escritor posterior sobreescriba un teléfono ocupado.

**Evidencia:** `repros.json`, `crm_consulta_fallida`, `crm_get_fallido`.

### H-09 — MEDIO — `_completar_colaborador_existente` puede lanzar y perder el vínculo

**Localización:** `core/sudespacho_relations.py:799`, `:2219-2223`, `:2248`.

**Entrada concreta:** DTO `NuevoColaborador(nombre='ANA', movil='611111111')`; colaborador resuelto `466`; GET simulado HTTP 200 con este JSON:

```json
{"values":[{"property":{"name":"movil"},"value":612345678}]}
```

**Resultado ejecutado:** `ensure_colaborador_vinculado('600', datos, client=doble)` lanza `AttributeError("'int' object has no attribute 'strip'")`; el doble de `link_colaborador` tiene **cero llamadas**.

`_parse_values` preserva el tipo JSON; la anotación `dict[str, str]` no lo valida. La preparación de cambios está fuera de ambos `try`, de modo que una respuesta con tipo inesperado derriba el vínculo en vez de registrar que no se pudo completar. La garantía «no lanza» no cubre toda la función. Debe abstenerse de completar ante una respuesta no interpretable y permitir el vínculo.

**Límite:** se ha probado la reacción al JSON indicado, no que el tenant real devuelva números en ese campo. No se ha consultado el CRM.

**Evidencia:** `repros.json`, `crm_valor_numerico`.

### H-10 — MEDIO — La puerta de corroboración admite ausencia de teléfono y razón social repartida en líneas

**Localización:** `core/email_firmas.py:78-82`, `:210`.

**Entrada concreta A:**

```text
Móvil: ---
Puedes escribir a ana@engelvoelkers.com
```

**Resultado ejecutado:** se crea firma de Ana, con `FIRMA_SIN_CAMPO` en todos sus campos. No hay marca, razón social ni un solo dígito. La clase `[0-9+()*<>.\- \t]+` admite sólo signos: no exige algo con forma de teléfono.

**Entrada concreta B**, cadena Python: `'EV\nMMC\nSPAIN\nana@engelvoelkers.com\n'`. También crea firma. Los `\s+` de la razón social atraviesan saltos de línea y contradicen la exigencia de razón social en línea propia. Se cerró ese problema para la marca, pero quedó abierto para la otra alternativa de la misma puerta.

No se propone un número en estos dos ejemplos; el daño medido es inventar una firma y una ausencia. La corroboración debe aplicar las mismas restricciones a todas sus alternativas.

**Evidencia:** `repros.json`, `corrobora_sin_numero`, `razon_multilinea`.

### H-11 — MEDIO — La suite no detecta que desaparezcan los `.eml` con fallo de apertura

**Localización de la mutación:** `core/email_firmas.py:648`. Test representativo insuficiente: `tests/test_email_firmas.py:1224`, `test_un_eml_que_no_parsea_es_NO_LEIBLE_no_una_ausencia`.

**Entrada concreta:** `extraer_de_eml(Path('denegado.eml'))`, con `Path.open` simulado para lanzar `PermissionError('sin acceso')`.

**Producción sin mutar:** devuelve `ilegible="denegado.eml: no parsea (PermissionError('sin acceso'))"`. Esta rama funciona en el objeto revisado.

**Mutación deliberada M1, sólo en la copia:** sustituir

```python
return ResultadoEml(ilegible=f"{path}: no parsea ({exc!r})")
```

por

```python
return ResultadoEml()
```

**Resultado ejecutado:** los **250 tests de los cuatro módulos del cambio siguen pasando**. La sonda con `PermissionError` devuelve entonces `firmas=()`, `emails_vistos=frozenset()`, `sin_atribuir=0`, `ilegible=''`: el archivo desaparece sin declaración de `NO_LEIBLE`.

El test del archivo de bytes inválidos ejerce la rama «sin cabeceras reconocibles», no necesariamente la excepción de apertura/parseo. La propiedad 11 está parcialmente probada, pero su frontera de I/O no queda protegida por esa suite. Es un hallazgo de cobertura, **no una afirmación de que la rama actual ya silencie ese error**.

**Evidencia:** `M1_io_silenciada.diff`, `M1_io_silenciada.log`, `mutaciones.json`. La mutación fue restaurada.

### H-12 — MEDIO — Se registra «completado» sin comprobar el resultado de la escritura

**Localización:** `core/sudespacho_relations.py:824-828`, `:2228-2229`.

**Entrada concreta:** GET simulado `{'movil': ''}`, DTO con móvil `611111111`, y PUT simulado HTTP 200 con JSON `{}` que no acredita ningún campo actualizado.

**Resultado ejecutado:** se registra `colaborador 466 completado con ['movil']`. No se comprueba lo devuelto ni se hace GET posterior. Si el JSON del 200 es ilegible, el `except` de `update_colaborador` incluso fabrica como respuesta una copia de los cambios solicitados.

El plan exige verificar por resultado y el spec mantiene el GET posterior. El CLI existente `scripts/crm_ficha.py` comprueba relaciones y notas; no hace lectura posterior del móvil/fijo del colaborador. Por tanto, ese consumidor tampoco cierra la verificación de esta escritura nueva.

Debe conservarse el vínculo sin convertir «se envió y hubo un 200» en «se completó». Hace falta verificación del dato o un resultado explícitamente no verificado. **No se afirma que el CRM real esté ignorando PUTs**: el defecto medido es que la implementación declara éxito con una respuesta que no lo acredita.

**Evidencia:** `repros.json`, `crm_200_sin_verificacion`.

## Contraste punto por punto de las propiedades del mandato

| §4 | Resultado de la revisión |
|---|---|
| 1. Atribuir por firma, nunca por `From` | El uso de `From` sólo para candidatos está confirmado por lectura y tests de `.eml`. No basta para proteger la identidad: H-01, H-02 y H-03 producen atribuciones incorrectas sin usar la cabecera. |
| 2. Conservar email del ancla | Confirmado en el código y casos ejecutados. H-01 demuestra que los campos de la ventana no quedan ligados a esa ancla. |
| 3. La cabecera citada no ancla | Incumplido en la cabecera partida de H-03. No se necesita ampliar idiomas para reproducirlo. |
| 4. Corroboración obligatoria | Hay puerta, pero admite las entradas sin corroboración real de H-10 y el arrastre del vecino de H-01. |
| 5. Forma del teléfono limpio | Los tests de forma y longitud pasan; se rechazan las cadenas ensayadas fuera del patrón y se conservan los extranjeros del contrato. Esto valida la forma, no la pertenencia ni la corrección del número. H-05 produce un número corrupto con forma aceptable por otra vía. No se ha verificado un plan de numeración internacional. |
| 6. Sólo rellenar lo vacío en CRM | Confirmado para respuestas simuladas con cadenas, espacios y nulos, y valores existentes. No se ha probado atomicidad frente a una edición concurrente entre GET y PUT ni la semántica del endpoint real. |
| 7. Completar no lanza y registra | Excepciones de GET/PUT ordinarias están cubiertas, pero H-09 deja fuera la interpretación de la respuesta y pierde el vínculo. H-12 registra éxito sin comprobar el resultado. |
| 8. Mismo resolvedor en ambas jurisdicciones | Confirmado por lectura y tests de las dos llamadas a `_resolver_o_crear_colaborador`. Esto no implica que el CLI general soporte judicial: esa limitación previa está documentada en MEJORAS #150/#128. |
| 9. Conflicto implica campo vacío | Funciona para discrepancias que llegan a `_elegir`; la mutación M2 es detectada. H-04 demuestra que otras discrepancias se pierden antes de llegar. |
| 10. Firma sin campo tiene veredicto propio | Existe, pero H-07 lo emite cuando sí hay fijo y no se ha sabido leer. No basta con que exista la constante. |
| 11. `.eml` no legible se declara | Funciona en los errores ensayados sobre el original, pero la mutación M1 demuestra la cobertura ausente de errores de I/O. El mojibake por charset incorrecto está ya reconocido en MEJORAS #151; no se presenta como descubrimiento de esta revisión. |
| 12. `apply` no da de alta | En lectura y ejecución sólo modifica entradas existentes del YAML; los tests correspondientes pasan. H-01 y H-05 afectan precisamente a entradas ya existentes. |
| 13. Frontera de imports | AST inspeccionado: `email_firmas.py` sólo importa biblioteca estándar y `core.utils.normalize_es_phone`; no importa `core.sudespacho_*`. |
| 14. Nulo YAML significa ausencia | Los tests de claves vacías pasan y se usa `_escalar`. H-05 afecta a enteros reinterpretados, no a `None`, y muestra que el recorrido de `apply` evade otra protección del constructor. |

## Ejecución, mutaciones y evidencia reproducible

Intérprete: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`. Variables de ejecución: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`. Se copió `core/`, `scripts/`, `tests/` y `pyproject.toml` a `copia/`.

Comando de la suite específica, desde este workdir:

```powershell
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest -c copia/pyproject.toml -p no:cacheprovider --basetemp=./bf copia/tests/test_email_firmas.py copia/tests/test_crm_colaboradores_firmas_cli.py copia/tests/test_crm_colaborador_props.py copia/tests/test_crm_ficha_yaml_none.py
```

- Original, primera ejecución útil: **250 passed**.
- M1, silenciar error de apertura/parseo: **250 passed**; mutante superviviente, H-11.
- M2, devolver `candidatos[-1]` en vez de `''` al detectar conflicto: **3 failed, 247 passed**. Fallan el test del móvil vacío en conflicto y dos de cargo vacío en conflicto. Esta protección sí reacciona a la rotura.
- Original restaurado, comprobación final: **250 passed in 3.18s**, salida 0. El hash de la copia restaurada coincide con el del objeto.

La primera invocación, ejecutada desde `copia/` con `--basetemp=./bt`, produjo **250 errores de setup por `WinError 5`** al crear el temporal. No ejecutó los cuerpos de los tests y no se cuenta como regresión. Ejecutar desde `informe/`, con configuración en `copia/` y temporal relativo a `informe/`, permitió la ejecución sin parches a pytest ni a los tests.

Ejecución ampliada mediante `audit_tests.py`: **507 passed, 3 failed**, sobre 510 tests de los cuatro módulos nuevos y siete módulos cercanos del flujo CRM. El lanzador bloqueó `socket.create_connection` y `socket.connect` con una excepción derivada de `BaseException`. Los tres fallos son intentos de llamada HTTP no simulada en el camino de **contrarios**:

- `test_crm_dedup_partes.py::TestJudicialYExtrajudicialResuelvenIGUAL::test_el_contrario_existente_se_reutiliza_en_judicial`.
- `test_crm_dedup_partes.py::TestJudicialYExtrajudicialResuelvenIGUAL::test_el_email_tambien_deduplica_al_contrario`.
- `test_sudespacho_relations.py::test_ensure_contrario_vinculado_existente`.

Las conexiones quedaron bloqueadas antes de salir. Los dos ficheros de tests son idénticos por bytes en `base` y `head`; los AST de `_completar_contrario_existente`, `_resolver_o_crear_contrario` y `get_cliente_contrario` también son idénticos. **No se atribuyen esos fallos al diff ni se convierten en hallazgos de esta ronda.** No se ha repetido esa suite contra una copia de `base`.

Artefactos locales conservados para adjudicación:

- `audit_repros.py` y `repros.json`: entradas y salidas de las sondas, incluidos el recorrido a YAML/PUT simulado y casos de líneas.
- `audit_mutations.py`, `mutaciones.json`, `M1_io_silenciada.diff/.log` y `M2_conflicto_con_valor.diff/.log`: mutaciones y resultados.
- `audit_tests.py` y `tests_ampliados.log`: selección ampliada y barrera de red.

Las salidas incluyen también sondas exploratorias no elevadas a hallazgo separado. No se han contado como tests de aceptación añadidos al producto.

## Sin verificar y límites

- **SIN VERIFICAR: semillas 777 y 31337.** No está disponible `pytest-randomly`, como advierte el mandato. No se ha simulado ni declarado esa cobertura.
- **SIN VERIFICAR: suite completa del repositorio.** Se ejecutaron los 510 tests seleccionados, con el resultado y las exclusiones anteriores; no se afirma que todo el repositorio esté verde.
- **SIN VERIFICAR: CRM real**, credenciales, tipos efectivos de respuesta, persistencia de PUT, comportamiento parcial del endpoint de colaboradores y edición concurrente. Las sondas son locales. La evidencia documental sobre PUT genérico no sustituye a una medición del elemento; tampoco permite afirmar que el endpoint sea de reemplazo.
- **SIN VERIFICAR: los seis `.eml` reales de W-02Q38C** y la frecuencia de los contraejemplos en producción. Se usaron las plantillas sintéticas del objeto y entradas sintéticas propias.
- **SIN VERIFICAR: todos los formatos MIME, charsets, idiomas y clientes de correo.** Se probaron lectura plana, errores concretos, ventanas y variantes de cita. La limitación ya documentada de cargo/charset no se da por resuelta.
- **SIN VERIFICAR: genealogía de las copias.** No hay metadatos Git para acreditar los commits suministrados.
- No se ejecutó `tests/test_crm_dedup_incertidumbre.py`: el fallo de `SUDESPACHO_LEGACY_HOST` está expresamente excluido por el mandato.
- El hash exigido acredita que `core/email_firmas.py` conserva sus bytes al abrir y cerrar. No lo presento como hash de todo el árbol. Todas las escrituras de esta revisión se dirigieron al workdir, no a las copias congeladas.

La adjudicación de los hallazgos corresponde a Claude contra la fuente. El veredicto de revisión se basa en los cruces de identidad reproducidos y en los demás incumplimientos descritos, no en los fallos ambientales de la suite ampliada.

SHA-256 de `../head/core/email_firmas.py` **al cerrar**, idéntico al de apertura:

```text
5277b1f91c96d1c634c63a2d41ff5cd20825ef554fc7ae64e422fa7213a3e25f
```

CAMBIOS_REQUERIDOS

---

*(Segunda entrega del revisor: el veredicto, pedido aparte. Ver la cabecera de esta acta para el porque.)*

El dictamen CAMBIOS_REQUERIDOS, sustentado en 12 hallazgos y uno crítico reproducido hasta un PUT simulado que atribuye a Berta el teléfono de Ana, corresponde a NO-SHIP: el objeto no debe integrarse en el estado revisado. Este veredicto se refiere exclusivamente a ese objeto y no presupone ninguna remediación posterior.

NO-SHIP

<!-- informe-literal:fin:k7qd -->

## 2. Evidencia verificada por el adjudicador

**No adjudiqué contra el informe: adjudiqué contra la fuente.** Antes de aceptar el lote,
ejecuté cinco de los doce contraejemplos del revisor contra el código tal como estaba, y
los cinco reprodujeron el defecto que describía:

| Hallazgo | Entrada del revisor | Resultado medido ANTES de remediar |
|---|---|---|
| H-01 | dos firmas seguidas, cada una con su móvil | **las dos personas salían con `611111111`** |
| H-02 | `ana@engelvoelkers.com.tercero.example` | se atribuía a `ana@engelvoelkers.com`, dirección **que no está en el texto** |
| H-04 | dos líneas `Móvil:` en la misma firma | devolvía la primera y declaraba `ENCONTRADO` |
| H-07 | `Teléfono móvil:` seguido de `Telf:` | el fijo salía **vacío**, con la firma trayéndolo |
| H-10 | `Móvil: ---` y razón social partida en tres líneas | **creaban firma** las dos |

Tras la remediación volví a ejecutar los mismos cinco: cada persona conserva su móvil, el
dominio parecido no produce bloque, los dos móviles dan campo vacío, el fijo de más abajo
se encuentra, y los dos casos de corroboración dejan de crear firma.

**Y la verificación que ninguna fixture puede dar: el corpus real.** Sobre W-02Q38C
(cuatro firmas, cuatro candidatos, cero ilegibles), antes y después de remediar: **ningún
móvil se comparte entre personas**. El único valor compartido es un fijo que tienen tres
colaboradores del mismo Market Center, y es la **centralita de la oficina** — no una
misatribución. Lo comprobé por hash, sin que ningún dato personal saliera a la consola.

**Suite:** 4.371 tests, mismo conteo con las semillas 777 y 31337.

**Los dos fallos de `tests/test_crm_dedup_incertidumbre.py` no son de esta rama, y su
diagnóstico heredado era falso.** Seis informes seguidos los explicaron como «el worktree
no hereda el `.env`». Los ejecuté con la variable puesta y **siguen fallando**: piden
además `SUDESPACHO_LEGACY_PHPSESSID`, que es una cookie de sesión que caduca. Los corrí
contra el árbol **base** congelado del objeto y fallan igual, así que preexistentes sí son
— pero por depender de credenciales vivas, no por el `.env`. Anotado en `MEJORAS_FUTURAS`.

**Lo que el revisor declaró SIN VERIFICAR, y sigue así:** no pudo correr las dos semillas
(su Python de sistema no trae `pytest-randomly`) — lo cubro yo arriba; y no acredita que
las copias correspondan a los commits declarados, porque no tienen `.git`.
