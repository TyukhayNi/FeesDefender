---
tipo: revision-adversarial
objeto: diff eb8ac09..c2a2c54 — identidad sin teclado, ya remediado tras la R1
objeto_rev: "2"
commit: c2a2c54
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: p7r2
sha256_informe: 56416e63bea1769bd99322aa41b966914d957472cb5d7ebe9adc33bf5b824dbe
adjudicado_en: docs/superpowers/plans/2026-09-11-identidad-sin-teclado.md §4
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# Acta de revisión adversarial R2 — identidad sin teclado

- **Objeto revisado:** diff `eb8ac09..c2a2c54` — el mismo, ya remediado tras la R1
- **Ronda:** R2 de 2 (presupuesto agotado; una tercera exige autorización expresa de Nikolai)
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` + su propio informe de R1 con hash
- **Informe recibido:** 2026-09-11, `C:/t/rev-p7-r2-085933/wd/INFORME.md`, 40683 bytes
- **Hallazgos:** 9 nuevos + el dictamen de las 8 remediaciones de R1; **todos confirmados, 0 refutados**
- **Remediado en:** `docs/superpowers/plans/2026-09-11-identidad-sin-teclado.md` §4

**Qué se le pidió de más en esta ronda, y es lo que más devolvió.** Además de atacar en fresco, se
le dio su propio informe de R1 con su `sha256` y se le pidió **dictaminar si cada remediación era
real, cosmética o incompleta**. Dictaminó **6 de 8 incompletas**, reproduciendo cada escenario.

**Custodia.** Mismo patrón, más el informe de la R1 (`337f045f…`) entregado como objeto de
lectura. Esta vez sí ejecutó: cuatro corridas de pytest (`head` y `base`, semillas 777 y 31337) y
mutantes dirigidos uno a uno.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:p7r2 -->
HIGIENE: al abrir el workdir encontré MANDATO.md y también _stdout.log; no leí _stdout.log.

# Revisión adversarial R2 del diff remediado

Fecha comprobada con `Get-Date`: 2026-09-11. Objeto: `../base` y `../head`, sin `.git`. Informe del revisor; la adjudicación corresponde a Claude contra las fuentes.

## 1. Hashes de apertura

Medidos antes de leer el código con `Get-FileHash -Algorithm SHA256`. La huella de R1 coincide con la indicada en el mandato.

| Fichero | SHA-256 |
|---|---|
| `../head/scripts/abrir_caso.py` | `0dacfb3ecf5562288ee5be091f321bf2e38823ac6c4fcfbcca50dc2967cba870` |
| `../head/core/case_manager.py` | `b74c6a915eeaed44ab324b7b6237ee85d2f1843257e641958ac02f6af3c34a8a` |
| `../head/tests/test_case_manager_update_meta.py` | `e5d44c2ec0b4abbf88aed09bde72d3aa94823c67f137d1d0fbe2039333b2b8e7` |
| `../INFORME_R1.md` | `337f045fea0b05779c71f6a45fc4d075e9ebff809ac31e89c6bc1b4ced9c7a2f` |

## 2. Método y alcance

Copié los dos árboles a `run_head/` y `run_base/` dentro del workdir. Copié **los dos ficheros de tests de head** sobre `run_base/tests/`. Ejecuté las cuatro combinaciones árbol/semilla, controles por caso y mutantes en una tercera copia, `mutant_tree/`. Las fuentes congeladas no se importaron para ejecutar pruebas ni se modificaron.

La comparación completa de bytes encontró exactamente estos cinco ficheros distintos: `core/case_manager.py`, `scripts/abrir_caso.py`, `docs/MEJORAS_FUTURAS.md`, `tests/test_abrir_caso_cli.py` y el nuevo `tests/test_case_manager_update_meta.py`. No hay una copia del código de R1: se contrasta su informe autenticado con los escenarios reproducidos sobre head; no atribuyo por inferencia contenido a un árbol intermedio ausente.

El arnés `run_suite.py` usa el intérprete indicado, `-B`, caché pytest desactivada, `--basetemp` relativo bajo `wd/tmp/`, y `TMP`/`TEMP` bajo ese mismo workdir. Un audit hook rechaza escrituras Python fuera de `wd`, conexiones y subprocesos durante la suite. `NUL` y los descriptores de captura son infraestructura, no expedientes. Para permitir la inicialización de Faker/pytest, la consulta de versión del SO se realiza antes del guard. Los intentos iniciales bloqueados por esa consulta y por el nombre absoluto de `NUL` **no fueron corridas válidas**; se corrigió el arnés, no el código revisado.

Las sondas `probes.py` usan ficheros reales bajo `tmp/probes/`, el parser, `update_meta` y el escritor atómico reales; solo sustituyen el localizador para dirigirlos a cada caso sintético. La sonda del alta usa dobles del CRM, construcción del payload y registro/localización, con persistencia de cuantía real y fallo inyectado en su primera llamada. Los tests de CLI de head y la sonda adicional `tests/review_extra.py`, creada **solo en run_head**, sí recorren los registradores locales reales y `CliRunner` con las fixtures de aislamiento del proyecto.

## 3. Dictamen de H-01…H-08

“Real” significa que cierra lo que se pidió para ese hallazgo; no certifica propiedades distintas. Una corrección documental puede ser real si la solución contratada era acotar el contrato. “Incompleta” reconoce el arreglo del ejemplo cuando existe, pero identifica la propiedad que sigue rota.

| Hallazgo R1 | Dictamen | Resultado contrastado |
|---|---|---|
| H-01 | **INCOMPLETA** | El prefijo en `# Notas` ya no pisa la cuantía de `## Sede`. El ámbito de referencia CRM todavía alcanza notas bajo `#`/`###`, y los finales de sección ignoran encabezados indentados: H2-01. |
| H-02 | **INCOMPLETA** | La cerca simple con lenguaje y las dos `## Sede` se resuelven correctamente. Fallan cercas de distinto carácter/longitud, inserción con cerca abierta y duplicidad de `## Partes` para referencia: H2-02…H2-04. |
| H-03 | **INCOMPLETA** | Los cuatro campos originales se rechazan sin escribir. Se aceptan `ciudad`, `creado_en` y los dos `ultimo_checkin_*`; tampoco todos los errores nombran una vía: H2-05. |
| H-04 | **INCOMPLETA** | Truncado, YAML lista y `meta` lista producen `ValueError`, con bytes idénticos. YAML sintácticamente inválido conserva bytes, pero lanza `ParserError`, no `ValueError`; `meta: null` se normaliza y las claves duplicadas se pierden: H2-07/H2-09. |
| H-05 | **INCOMPLETA** | El fallo local ya se anuncia como tal y el segundo intento con la misma cuantía la repone, con una sola creación CRM. La nueva rama de reintento sobrescribe una cuantía conocida con el default 0 si se omite el flag: H2-06. |
| H-06 | **REAL** | `Calle - W-ABCDE` y `w_code=' W-ABCDE '` devuelven `Calle`; el test CLI correspondiente pasa y muere al restaurar `.upper()`. |
| H-07 | **INCOMPLETA** | Corregidos el color del test y la cabecera/acotación de `ensure_case`; sobreviven las citas falsas `#184` en el mismo test, líneas 74 y 82, y la generalización en el backlog. |
| H-08 | **REAL, como acotación documental** | Se declara expresamente pérdida de comentarios YAML y espacios de borde. La reproducción confirma esas pérdidas; no se afirma haberlas corregido ni que esa salvedad cubra los daños nuevos. |

### H-01: escenario original

Entrada del cuerpo, con un frontmatter mapa válido:

```markdown
# Notas
- Cuantía: comprobar oferta, NO BORRAR

## Sede
- Cuantía: _(pendiente)_
```

`update_meta('C', cuantia=42)` conserva literalmente la nota y deja `- Cuantía: 42` bajo Sede. Informe: `cuerpo=['cuantia']`, `insertadas=[]`, `sin_linea=[]`, `ambiguas=[]`. Sonda `R1_H01`. El caso original está cerrado; las variantes de H2-01 todavía destruyen notas.

### H-02: los dos escenarios originales

Sonda `R1_H02_fence`: entrada ` ```md\n## Sede\n```\n\n## Sede\nTexto real\n` (sin el espacio tipográfico inicial). Resultado: el ejemplo cercado conserva solo su encabezado; la línea `- Cuantía: 42` aparece tras `Texto real`, en la sección real. `insertadas=['cuantia']`, `ambiguas=[]`.

Sonda `R1_H02_duplicate`: entrada `## Sede\nEjemplo histórico\n\n## Sede\nSede vigente\n`. Resultado: ambos cuerpos quedan sin cuantía, `meta.cuantia=42`, `ambiguas=['cuantia']`, `cuerpo=[]`, `insertadas=[]`. Detecta la duplicidad y no elige una sede.

### H-03: rechazo y límites

Repetí la llamada conjunta con `estado='archivado'`, `titulo='Nuevo'`, `drive_ev_folder_id='NEW'` y `sudespacho_expedientes=[{'id':'20'}]`, y también cada campo por separado. Todas producen `KeyError` y **bytes idénticos antes/después**. El mensaje conjunto incluye `register_drive_ev`, `register_expediente` y `_write_case_index`.

El error individual de título dice únicamente `titulo: es el encabezado '# ' del cuerpo, que este actualizador no toca`. El de `drive_remote_path` describe sus hogares pero no proporciona una vía sancionada. Rechazar es una mejora real; no equivale a cumplir todo lo prometido en los mensajes ni a completar la tabla. Los otros campos omitidos están reproducidos en H2-05.

### H-04: frontera del parser

| Entrada sintética | Salida real | Bytes |
|---|---|---|
| `---\ncase_id: C\nmeta:\n  checkout_nonce: N\n`, sin cierre | `ValueError`, contiene `frontmatter legible como mapa` | Idénticos |
| Frontmatter `- nota_a_preservar` | `ValueError`, mismo diagnóstico | Idénticos |
| Frontmatter `case_id: C\nmeta: [una, lista]` | `ValueError`, `meta ... no es un mapa: list` | Idénticos |
| Frontmatter `case_id: C\nmeta: [` | `yaml.parser.ParserError`; `isinstance(exc, ValueError) == False` | Idénticos |
| Frontmatter `case_id: C\nmeta: null` | Retorno normal; `meta` se convierte en mapa con cuantía | Cambiados |
| Cuerpo sin frontmatter `  Nota del abogado\n` | `ValueError` | Idénticos |

Son `fm_truncated`, `fm_list`, `fm_meta_list`, `fm_syntax`, `fm_meta_null`, `fm_no_fm`. No confundo excepción de tipo distinto con escritura destructiva: el YAML sintácticamente inválido **sí para sin escribir**. La pérdida nueva por duplicados se describe separadamente en H2-07.

### H-05: fallo local y reparación

Sonda `R1_H05`: primera creación simulada devuelve `9999`, registro local completado y primera persistencia de cuantía lanza `OSError('disk full')`. Salida:

```text
OK CRM id=9999
[AVISO] el alta CRM si se completo, pero la cuantia NO se escribio en _caso.md (OSError('disk full')). Reponla con `case_manager.update_meta(<case_id>, cuantia=42)`.
CRM ya registrado (element=extrajudiciales, id=9999), no se re-da de alta
```

Después de dos llamadas con cuantía 42: `create=1`, `update=2`, `meta.cuantia=42`, cuerpo con `- Cuantía: 42`. También pasan los dos tests de head para aviso y reintento en ambas semillas. La sonda adicional del helper comprueba que tanto `sin_linea=['cuantia']` como `ambiguas=['cuantia']` emiten `frontmatter pero NO en el cuerpo`. No queda silenciosa esa rama.

La separación del `try` solo cubre la escritura de cuantía: `register_expediente` sigue dentro del `try` del alta (`abrir_caso.py:747–756`). Un fallo de registro después de crear sigue clasificado como fallo de alta; es una frontera preexistente, distinta del fallo de `update_meta` originalmente denunciado. No la presento como regresión introducida en R2. La regresión nueva medida está en H2-06.

### H-06: normalización

Sonda `R1_H06`: `_direccion_de_la_carpeta('Calle - W-ABCDE', ' W-ABCDE ')` devuelve `Calle`; salida `[auto] --direccion del nombre de la carpeta: 'Calle'`. El test CLI con espacios pasa sobre head y falla sobre base. M09 restituye `.upper()` y lo mata: el test comprueba esta corrección de verdad.

### H-07: prosa y test de conservación

Ejecuté `test_ensure_case_sigue_sin_poder_reponerla`: verde sobre base y head con las dos semillas. Eso confirma que `ensure_case` deja la cuantía pendiente en un caso existente. Su docstring actual ya interpreta correctamente el verde; M13 cambia esa conducta y lo vuelve rojo (`assert 73140.0 is None`).

La acotación en `case_manager.py:385–389` y en la cabecera del test, líneas 3–11, corresponde al código: `ensure_case` sí contempla `tipo_caso`, `direccion`, `id_go`, `ciudad` en `:993–1015`. Pero `test_case_manager_update_meta.py:74` todavía identifica `MEJORAS #184` con referencia CRM, y `:82` repite la cita. La entrada real de sondeos de correo sigue en `docs/MEJORAS_FUTURAS.md:8122`; la corrección del backlog en `:10669` no elimina las citas residuales ni la frase general de `:10667`. El remedio documental es parcial.

### H-08: qué sigue perdiéndose y qué se prometió

Sonda `fm_comments`: frontmatter con `# Nota crucial del abogado` y `ajena: 1 # manual`, seguido de cuerpo que comienza con dos espacios antes de `Nota del abogado`. Tras actualizar, `ajena=1` permanece, desaparecen los dos comentarios y el cuerpo comienza por `Nota del abogado` sin esos espacios. El docstring `case_manager.py:529–533` ya declara esas pérdidas. El antiguo ejemplo sin frontmatter ahora se rechaza por H-04; por eso la reproducción de espacios se hace con un mapa válido para alcanzar el escritor.

Acotar el contrato resuelve H-08 tal como fue planteado. No ampara sobrescribir notas dentro de un ámbito que el parser identificó mal, ni descartar valores de YAML ambiguo.

### Matriz adicional de variantes Markdown

Todas las filas se ejecutaron contra head en ficheros reales; no son predicciones a partir del diff.

| Variante | Resultado |
|---|---|
| `## Sede` seguido de `### Nota del letrado` a columna cero | Se inserta cuantía entre los dos encabezados; nota inferior intacta. Corte conservador ante subsección, correcto para la propiedad de conservación. |
| Encabezado `  ### Nota del letrado` con dos espacios | No corta el ámbito; pierde `- Órgano: NO BORRAR` al actualizar órgano. |
| Cerca ` ```md ` convencional, cerrada con el mismo delimitador | Ejemplo intacto; línea real actualizada. |
| Cerca `~~~md` convencional, cerrada con `~~~` | Ejemplo intacto; línea real actualizada. |
| Apertura de backticks, `~~~` en su interior | Se trata como cierre; se sobrescribe texto literal del ejemplo. |
| Apertura de cuatro backticks, línea interior de tres | Mismo daño. |
| Línea interior ` ```python ` con texto de lenguaje | Se trata como cierre y se sobrescribe el ejemplo. |
| `## Sede` antes de una cerca sin cerrar | Inserta la cuantía dentro del bloque cercado hasta EOF, y anuncia inserción correcta. |
| Lista con continuación indentada en Sede | Conserva el item y su continuación unidos; cuantía se añade después. |
| Sede vacía ante `## Fin` | Inserta en Sede antes de Fin. |
| Cuerpo que empieza directamente por `## Sede` | Reemplaza su cuantía correctamente. |
| `    ## Sede` como código indentado | Se toma como sección mediante `.strip()` y se inserta una cuantía; además el escritor elimina la sangría del primer borde. No reconoce código indentado. |
| Referencia en nota bajo `###` o segundo `#` | Pisa la nota al considerarla preámbulo. |
| Dos `## Partes`, sin referencia | Elige la primera para insertar, `ambiguas=[]`. |
| `## Sede` antes de `## Partes`, sin referencia | Inserta referencia en Sede; segunda llamada idéntica crea otra línea. |

## 4. Hallazgos nuevos

### H2-01 — ALTO — El ámbito todavía permite destruir notas ajenas

**Anclas:** `core/case_manager.py:455–458`, `:465–466`, `:618–625`; sondas `md_preamble_h3`, `md_preamble_h1`, `md_indented_heading`.

Entrada → operación → salida:

```text
# Original
### Notas
- Referencia CRM: NO BORRAR
## Partes
```

`update_meta('C', referencia_crm='NEW')` cambia la nota a `- Referencia CRM: **NEW**`; devuelve `cuerpo=['referencia_crm']`, `ambiguas=[]`. El preámbulo termina solo ante `## `, por lo que incorpora una sección manual `###`; también reproduce el daño con un segundo `# Notas`.

Segunda entrada: `## Sede\nTexto sede\n\n  ### Nota del letrado\n- Órgano: NO BORRAR\n## Fin\n`. `organo='NEW'` sustituye la nota por `- Órgano: NEW`. El detector de fin no admite espacios iniciales, aunque el buscador de sección usa `.strip()`. Los encabezados ATX permiten hasta tres espacios iniciales. [CommonMark, encabezados ATX](https://spec.commonmark.org/0.31.2/#atx-headings).

La propiedad que debe cerrar es pertenencia al fragmento del índice y abstención ante ambigüedad, no solo excluir otra `## Sede`.

### H2-02 — ALTO — Alternar un booleano no reconoce el cierre de una cerca

**Anclas:** `core/case_manager.py:420`, `:430–436`, `:617–624`; sondas `md_mixed_fence`, `md_short_close`, `md_false_close_info`.

Entrada del cuerpo:

`````text
## Sede
```md
~~~
- Cuantía: NO BORRAR
```
`````

`cuantia=42` sustituye `NO BORRAR` por `42` dentro del ejemplo y devuelve `cuerpo=['cuantia']`. El `~~~` interior cambia `dentro` a falso. Igual resultado con apertura de cuatro backticks y supuesto cierre de tres, o con una línea interior de backticks seguida de `python`.

Una cerca cierra con el mismo carácter, longitud suficiente y sin texto de lenguaje en el cierre. [CommonMark, bloques cercados](https://spec.commonmark.org/0.31.2/#fenced-code-blocks). El helper no conserva ninguno de esos atributos. Son pérdidas de texto nuevo, no mero formato YAML heredado.

### H2-03 — MEDIO — La referencia se inserta fuera de su propio ámbito y se duplica

**Anclas:** `core/case_manager.py:455–458`, `:627–634`; sondas `md_preamble_duplicate`, `md_preamble_late`, `md_preamble_late_second`.

Entrada: `# Original\n## Sede\nSede\n## Partes\nPartes\n`. Primera llamada `referencia_crm='NEW'` inserta la línea justo antes de Partes, **dentro de Sede**, aunque el ámbito de búsqueda terminó antes, ante Sede. Segunda llamada idéntica vuelve a no encontrarla en el preámbulo y añade otra. Resultado: dos líneas `- Referencia CRM: **NEW**`, ambas fuera del preámbulo; cada informe dice `insertadas=['referencia_crm']`, `ambiguas=[]`.

Variante: con dos `## Partes` se inserta ante la primera sin `ambiguas`. La comprobación de secciones duplicadas no se aplica a este campo porque `_ambito_de` recibe `None`. Búsqueda e inserción deben compartir el mismo ámbito validado.

### H2-04 — MEDIO — Con una cerca abierta, la inserción cae dentro de código

**Anclas:** `core/case_manager.py:465–467`, `:635–642`; sonda `md_unclosed`.

Entrada: `## Sede\n` seguida de una apertura de tres backticks con `md`, y `Ejemplo sin cerrar\n`. `cuantia=42` añade `- Cuantía: 42` al final. Sigue dentro del bloque cercado, que se extiende hasta EOF. El informe devuelve `insertadas=['cuantia']`, `sin_linea=[]`, `ambiguas=[]`, y `_persistir_cuantia_local` no avisaría con ese informe.

El helper excluye líneas cercadas al buscar candidatos, pero la posición `k` de inserción no se valida contra esa exclusión. No basta con corregir el reconocedor de cierres de H2-02: una apertura sin cierre seguirá necesitando una posición segura o abstención.

### H2-05 — MEDIO — La tabla de propietarios omite campos con hogar existente

**Anclas:** `core/case_manager.py:500–517`, `:589–606`; hogares en `:303–305`, vía ciudad en `:1013–1015`, y checkin en `:1352–1365`.

Entradas con mapa legible y actualización individual:

| Campo | Antes → después medido | Otro hogar/vía |
|---|---|---|
| `ciudad='Madrid'` | `meta.ciudad`: Barcelona → Madrid; `ciudad` superior sigue Barcelona | `ensure_case` actualiza ambas claves. |
| `creado_en='NEW'` | `meta.creado_en`: OLD → NEW; `fecha` superior sigue OLD | `_frontmatter_del_indice` deriva `fecha` de `creado_en`. |
| `ultimo_checkin_timestamp='2099-01-01'` | Se acepta y escribe sin transición de checkin | `liberar_lock` / `aplicar_lock_liberado`. |
| `ultimo_checkin_auditlog='INVENTADO'` | Se acepta y escribe sin checkin | Misma vía, dueña de la trazabilidad del checkin. |

Todos devuelven el campo en `frontmatter`, con `cuerpo=[]`, `sin_linea=[]`, `ambiguas=[]`. Los dos primeros dejan representaciones discrepantes; los dos últimos permiten alterar campos de la misma familia de lock que se pretendía reservar. No se ha demostrado que esto libere un checkout por sí solo.

`case_id` es el selector de la firma, no un campo actualizable dentro de `**campos`. `drive_link` sí mantiene su línea; no debe rechazarse por compartir el prefijo `drive_`. No atribuyo a `direccion`, `id_go` y `tipo_caso` una duplicidad de frontmatter que no tienen. Para título y remoto, además, los mensajes actuales explican por qué no los mantienen pero no nombran la vía prometida.

### H2-06 — ALTO — Reintentar sin cuantía reemplaza el dato conocido por cero

**Anclas:** `scripts/abrir_caso.py:681–684`, `:765–778`, `:1004`; sonda `test_default_retry_overwrites_known_amount` en la copia.

Escenario completo por `CliRunner`, con CRM simulado y expediente local real:

1. Apertura con los flags explícitos de `_args` y `--cuantia 73140.50`. Salida 0; CRM recibe 73140.5; el índice tiene 73140.5.
2. Misma apertura con `--force`, omitiendo `--cuantia`. Typer pasa el default `0.0`. Hay expediente registrado; no se crea otro.
3. El helper nuevo escribe 0.0 en el índice y el cuerpo; salida 0, `CRM ya registrado ... no se re-da de alta`, seguida de `OK Caso abierto`. Sin aviso sobre la cuantía.

Salida medida: `before=73140.5`, `after=0.0`, `crm_amounts=[73140.5]`. Se pierde un dato local válido y se fabrica discrepancia con el CRM. La guarda de base no hacía esa escritura. La reparación del intento fallido debe distinguir cuantía suministrada de default ausente y no tratar cualquier repetición del comando como una corrección intencionada del importe.

### H2-07 — MEDIO — El YAML con claves duplicadas pierde contenido sin diagnóstico

**Anclas:** `core/case_manager.py:583–596`, `:645`; parser/escritor heredados `core/utils.py:254–283`; sonda `fm_duplicate_yaml`.

Entrada del frontmatter:

```yaml
case_id: C
meta: {}
nota: NO BORRAR
nota: segunda
```

Con cuerpo `## Sede`, `cuantia=42` retorna éxito y deja solo `nota: segunda`. `NO BORRAR` desaparece del fichero. El parser colapsa las claves antes de comprobar `isinstance(fm, dict)`; esa comprobación no acredita un mapa sin ambigüedad.

Es una entrada defectuosa y el comportamiento del parser es heredado. La responsabilidad de la API nueva es escribir pese a que no puede conservar lo recibido, dentro del contrato de no normalizar un índice defectuoso. No afirmo que el primer valor fuese antes el valor efectivo que consumía `safe_load`: denuncio su desaparición física silenciosa, que la salvedad de comentarios/espacios no cubre.

### H2-08 — MEDIO — Hay tests verdes pese a ejecutar la conducta que prohíben

**Anclas:** `tests/test_abrir_caso_cli.py:787–789`, `:850–866`, `:984–1014`; `tests/test_case_manager_update_meta.py:134–140`, `:298–313`, `:316–339`.

Resultados de mutantes dirigidos, manteniendo los tests intactos:

- **M05:** el helper advierte sobre otro W-code pero devuelve su dirección. El CLI llega al pull, cuyo doble lanza `AssertionError`. `CliRunner` lo convierte en resultado de salida 1; como el test solo exige ese código y substrings del aviso, **pasa**. Una función `boom` no acredita “no se llamó” si su excepción se convierte en la salida admitida. Falta observar la llamada o discriminar la excepción/estado creado.
- **M20:** `update_meta` crea la carpeta del caso ausente antes de lanzar el `FileNotFoundError` esperado. `test_un_caso_que_no_existe_no_se_crea` **pasa**; no inspecciona el árbol.
- **M29:** los seis errores de propietario se cambian por `<campo>: vía equivocada`, sin vía sancionada. Las seis parametrizaciones **pasan**: solo comprueban campo y prefijo fijo.
- **M30/M31:** se destruye el índice antes de lanzar el `ValueError` esperado. En el truncado se deja únicamente `checkout_nonce: N`; en el `meta` lista se deja `DESTRUIDO`. Ambos tests **pasan**. El primero solo busca el substring del nonce y el segundo no relee el fichero.
- **M32:** se hace otra llamada a `create_expediente` dentro de la rama ya registrada, conservando la reparación de cuantía. El test de reintento **pasa**: su doble devuelve siempre `9999` y no cuenta altas. M11 demuestra por separado que sí detecta perder la reparación de cuantía.

Estas supervivencias no invalidan todos los asertos de esos tests: delimitan exactamente qué parte de su título/docstring no queda probada. El cuadro individual de ejecución registra también los mutantes muertos y sus causas.

Comprobación adicional sin cambiar los tests: repetí M05 y M32 con trazado de llamadas Python. M05 siguió verde y ejecutó una vez `boom`, línea 787, el doble del pull prohibido. M32 siguió verde y ejecutó dos veces la lambda de `create_expediente`, línea 990. No se deduce la ejecución de esas llamadas solo del diff del mutante: quedó observada en `witness_mut_05_audit.json` y `witness_mut_32_audit.json`.

### H2-09 — BAJO — El contrato de `ValueError` no cubre toda la frontera declarada

**Anclas:** `core/case_manager.py:556–559`, `:583–592`; sondas `fm_syntax` y `fm_meta_null`.

`meta: [` con delimitadores completos → `yaml.parser.ParserError`, **no** subclase de `ValueError`. Un llamador que capture la excepción documentada no captura esta entrada. El fichero queda intacto.

`meta: null` en un frontmatter no vacío → se acepta y se escribe un mapa nuevo, porque `None` está exceptuado de la guarda. Si se quiere admitir explícitamente ausencia/null por compatibilidad, debe declararse esa excepción al mandato “meta no mapa para sin escribir”; actualmente la promesa estricta no es la conducta. No se equipara este caso a la pérdida de una lista no vacía.

## 5. Resultados de ejecución

### Suites con ambas semillas

Comando reproducible desde `wd` (el arnés cambia a la copia seleccionada):

```powershell
& 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe' -B run_suite.py run_head 777 run_head_777
```

Repetido con `run_head 31337`, `run_base 777` y `run_base 31337`, y su etiqueta correspondiente. Argumentos pytest efectivos: `-o addopts= -vv --tb=short -p no:cacheprovider --randomly-seed=<semilla> --basetemp=../tmp/<etiqueta> --junitxml=../<etiqueta>.xml tests/test_abrir_caso_cli.py tests/test_case_manager_update_meta.py`. El padre `tmp/` se creó antes. No se usó xdist; las dos semillas se ejecutaron en procesos independientes.

| Código / tests | Semilla | Verdes | Rojos | Errores | Salida | Tiempo |
|---|---:|---:|---:|---:|---:|---:|
| head / head | 777 | 81 | 0 | 0 | 0 | 27.00 s |
| head / head | 31337 | 81 | 0 | 0 | 0 | 27.07 s |
| base / head | 777 | 49 | 32 | 0 | 1 | 19.19 s |
| base / head | 31337 | 49 | 32 | 0 | 1 | 19.16 s |

Los tiempos del cuadro proceden de los XML JUnit; el resumen de consola incluye unas centésimas adicionales de cierre.

En cada corrida: **56 casos CLI + 25 casos de metadatos = 81**. Head tiene 31 funciones de test nuevas frente a base, que generan **36 casos** por las seis parametrizaciones de propietarios. Los 45 tests anteriores del CLI mantienen su cuerpo AST. No hay skip, xfail, xpass ni errores de setup/colección en las cuatro corridas finales.

Los dos tests adicionales del revisor pasan (8,07 s): uno **constata el defecto del cero** con asertos sobre el resultado erróneo y el otro comprueba los dos avisos del helper. Su verde no se suma a la suite entregada ni significa que la regresión esté corregida.

### Control positivo individual y mutantes

Cada fila identifica una función nueva y el resultado medido sobre base con **ambas semillas**. `ROJO` significa fallo de aserto o `AttributeError` por API ausente, no problema de infraestructura. En base, los 24 casos de metadatos que usan `update_meta` fallan por ausencia de la API; su único verde es conservación de `ensure_case`. En CLI hay ocho rojos nuevos; en los tests que intentan parchear `update_meta` el control puede morir ya al preparar ese parche porque base no tiene la función. No lo presento como prueba de sensibilidad al detalle de una remediación: esa sensibilidad se mide con el mutante dirigido.

Los cuatro nuevos que quedan verdes sobre base son **correctamente de conservación**: prioridad de dirección explícita, ausencia de consulta sin folder_id, cuantía pendiente con CRM skip y conducta anterior de ensure_case. No son controles positivos del cambio.

Los mutantes se escriben uno cada vez sobre una copia restaurada de head, sin editar los tests. Cada proceso ejecuta **solo su test objetivo**, semilla 777, con el mismo guard y basetemp propio. Los seis parámetros de propietarios se ejecutan individualmente por pytest bajo el mismo mutante de diagnóstico. “Muerto” exige fallo observado del test; error de colección/infraestructura no cuenta como muerte.

| Mutante / test objetivo | Base 777 / 31337 | Cambio mínimo en producción | Resultado individual sobre head mutado |
|---|---|---|---|
| M01 — `test_cli_drive_ev_autoderiva_direccion_del_nombre_de_carpeta` | ROJO / ROJO | Conservar el sufijo del consultor en la dirección | **MUERTO**: Aserto del case_id incluye indebidamente consultor |
| M02 — `test_cli_drive_ev_direccion_con_acento_se_conserva` | ROJO / ROJO | Quitar el acento de Marítim | **MUERTO**: No se conserva Marítim |
| M03 — `test_cli_drive_ev_carpeta_sin_w_code_pide_el_flag` | ROJO / ROJO | Omitir el nombre de carpeta del diagnóstico sin W-code | **MUERTO**: Falta nombre de carpeta en aviso |
| M04 — `test_cli_drive_ev_direccion_explicita_gana` | VERDE / VERDE | Sobrescribir dirección explícita con la derivada | **MUERTO**: Pierde prioridad de dirección explícita |
| M05 — `test_cli_drive_ev_carpeta_de_otro_w_code_no_deriva` | ROJO / ROJO | Avisar de otro W-code pero devolver su dirección y llegar al pull prohibido | **SOBREVIVE**: 1 verde |
| M06 — `test_cli_drive_ev_sin_folder_id_no_intenta_derivar` | VERDE / VERDE | Consultar Drive sin folder_id | **MUERTO**: Falta --direccion tras excepción de llamada Drive |
| M07 — `test_cli_alta_crm_escribe_la_cuantia_en_caso_md` | ROJO / ROJO | Omitir persistencia local de cuantía | **MUERTO**: None != 73140.5 |
| M08 — `test_cli_sin_alta_crm_la_cuantia_no_se_inventa` | VERDE / VERDE | Escribir cuantía también con crm skip | **MUERTO**: Desaparece cuantía pendiente con skip |
| M09 — `test_cli_w_code_con_espacios_no_es_una_discrepancia` | ROJO / ROJO | Restaurar comparación sin strip | **MUERTO**: CLI retorna 1 en vez de 0 |
| M10 — `test_cli_si_la_cuantia_no_se_escribe_NO_se_dice_que_fallo_el_alta` | ROJO / ROJO | Confundir fallo local con fallo de alta | **MUERTO**: Aparece Alta CRM falló |
| M11 — `test_cli_el_reintento_repone_la_cuantia_aunque_no_re_de_de_alta` | ROJO / ROJO | No reponer cuantía en rama ya registrado | **MUERTO**: None != 73140.5 tras reintento |
| M12 — `test_la_cuantia_llega_al_frontmatter_y_al_cuerpo` | ROJO / ROJO | Omitir cuantía en meta | **MUERTO**: None != 73140.0 en meta |
| M13 — `test_ensure_case_sigue_sin_poder_reponerla` | VERDE / VERDE | Hacer que ensure_case reponga cuantía en caso existente | **MUERTO**: 73140.0 ya no es None |
| M14 — `test_la_referencia_crm_tambien_y_en_las_dos_claves` | ROJO / ROJO | No actualizar referencia superior | **MUERTO**: Referencia superior sigue None |
| M15 — `test_no_pisa_la_nota_escrita_a_mano` | ROJO / ROJO | Descartar sección manual del letrado | **MUERTO**: Desaparece sección del letrado |
| M16 — `test_conserva_las_claves_ajenas_del_frontmatter` | ROJO / ROJO | Eliminar clave ajena bucket_override | **MUERTO**: KeyError: bucket_override |
| M17 — `test_varios_campos_en_una_llamada` | ROJO / ROJO | Omitir órgano en el cuerpo al actualizar varios campos | **MUERTO**: Órgano no actualizado |
| M18 — `test_un_campo_que_no_es_de_casemeta_duele_aqui` | ROJO / ROJO | Devolver excepción incorrecta para typo | **MUERTO**: ValueError no cumple KeyError |
| M19 — `test_sin_campos_tambien_duele` | ROJO / ROJO | Aceptar actualización vacía | **MUERTO**: No lanza KeyError |
| M20 — `test_un_caso_que_no_existe_no_se_crea` | ROJO / ROJO | Crear carpeta del caso ausente y luego lanzar excepción esperada | **SOBREVIVE**: 1 verde |
| M21 — `test_un_cuerpo_sin_la_seccion_lo_DICE_en_vez_de_adivinar` | ROJO / ROJO | No informar ausencia de sección | **MUERTO**: sin_linea queda vacío |
| M22 — `test_una_seccion_sin_la_linea_la_INSERTA_donde_toca` | ROJO / ROJO | Insertar cuantía al final del documento, fuera de Sede | **MUERTO**: Cuantía fuera de Sede |
| M23 — `test_un_valor_None_vuelve_a_pendiente` | ROJO / ROJO | Pintar None como cero | **MUERTO**: None se pinta como 0 |
| M24 — `test_no_toca_el_lock_de_checkout` | ROJO / ROJO | Perder nonce de checkout al actualizar | **MUERTO**: KeyError: checkout_nonce |
| M25 — `test_no_pisa_una_nota_QUE_EMPIEZA_IGUAL_que_la_linea` | ROJO / ROJO | Buscar candidatos en todo el cuerpo sin ámbito | **MUERTO**: No actualiza la línea de Sede |
| M26 — `test_no_confunde_un_encabezado_dentro_de_un_bloque_de_codigo` | ROJO / ROJO | Considerar visibles todas las líneas cercadas | **MUERTO**: No actualiza la sección real |
| M27 — `test_dos_secciones_con_el_mismo_nombre_son_AMBIGUAS_y_no_se_adivina` | ROJO / ROJO | Elegir primera sección duplicada | **MUERTO**: No informa sección ambigua |
| M28 — `test_dos_lineas_del_mismo_campo_en_la_seccion_tambien_son_ambiguas` | ROJO / ROJO | Elegir primera línea duplicada | **MUERTO**: No informa línea ambigua |
| M29 — `test_los_campos_con_otro_dueno_se_RECHAZAN_y_se_dice_adonde_ir` | ROJO / ROJO (6 parámetros) | No nombrar ninguna vía sancionada, conservar campo y prefijo del error | **SOBREVIVE**: 6 verdes |
| M30 — `test_un_indice_sin_frontmatter_legible_PARA_en_vez_de_normalizarlo` | ROJO / ROJO | Destruir índice truncado conservando solo el substring que comprueba el test | **SOBREVIVE**: 1 verde |
| M31 — `test_un_meta_que_no_es_un_mapa_tambien_para` | ROJO / ROJO | Destruir índice con meta no mapa antes de lanzar ValueError | **SOBREVIVE**: 1 verde |
| M32 — `test_cli_el_reintento_repone_la_cuantia_aunque_no_re_de_de_alta` | ROJO / ROJO | Volver a crear expediente externo pese al registro local | **SOBREVIVE**: 1 verde |

**32 mutantes dirigidos: 26 muertos, 6 supervivientes; 37 ejecuciones de casos objetivo: 26 rojas y 11 verdes.** La diferencia entre 32 y 37 corresponde a los seis parámetros de M29. No hubo errores de colección/setup en esta batería. Las filas cubren las 31 funciones nuevas (36 casos) y M32 añade una segunda lente al test de reintento. Artefactos: `mutants.json`, `mut_01.log`…`mut_32.log` y sus XML; `mutants.py` contiene los reemplazos exactos por función.

Los seis casos de M29, todos rojos sobre base y verdes sobre head mutado, son: `estado='archivado'`, `titulo='Otro título'`, `sudespacho_expedientes=[{'id':'20'}]`, `drive_ev_folder_id='NEW'`, `checkout_nonce='robado'` y `drive_remote_path='otro:remoto'`.

Los tests verdes antiguos del control, por nombre (los 45, ambas semillas):

```text
test_hash_tree_local
test_cli_fuente_drive_ev_explicita_equivale_a_default
test_cli_pasada_completa_crea_intake_log_y_crm
test_cli_persiste_id_go_para_resolve_ref
test_cli_idempotente_no_dobla_intake_ni_crm
test_cli_dry_run_no_escribe_crm
test_cli_crm_falla_no_rompe_pipeline
test_cli_crm_skip
test_cli_colision_sin_force_exit_1
test_hash_tree_local_excluye_solo_el_protocolo_de_su_ubicacion
test_cli_excluye_pulled_del_ledger
test_cli_ciudad_desconocida_exit_1
test_cli_dry_run_es_honesto_sobre_lo_ejecutado
test_cli_manual_sin_src_exit_1
test_cli_whatsapp_sin_rol_exit_1
test_cli_email_flags_ajenos_exit_1
test_cli_whatsapp_rol_invalido_exit_1
test_cli_manual_carpeta_deposita_y_loguea
test_cli_manual_zip_deposita
test_cli_manual_dry_run_no_deposita
test_cli_manual_reentrante_dedup
test_cli_manual_src_inexistente_exit_1
test_cli_codigo_duplicado_declina_confirmacion_exit_1
test_cli_crm_gate_declinado_exit_0
test_cli_whatsapp_delega_en_deposit_export
test_cli_whatsapp_dry_run_no_llama
test_cli_email_delega_en_export_label
test_cli_email_dry_run_no_llama
test_cli_whatsapp_dedup_reporta
test_cli_case_id_resuelve_identidad_por_wcode
test_cli_case_id_excluyente_con_flags_de_identidad
test_cli_sin_case_id_ni_flags_falla
test_cli_case_id_caso_inexistente_falla
test_cli_case_id_formato_no_canonico_falla_limpio
test_cli_drive_ev_autoderiva_codigo_team_sufijo
test_cli_drive_ev_flags_explicitos_ganan
test_cli_drive_ev_codigo_no_derivable_error
test_cli_drive_ev_folder_info_none_degrada_limpio
test_cli_drive_ev_sufijo_autoderivado_sin_api
test_cli_case_id_drive_ev_autoderiva_team_id
test_cli_drive_ev_team_id_no_derivable_error_limpio
test_intake_email_propaga_extraer_adjuntos_al_motor
test_intake_email_extrae_adjuntos_POR_DEFECTO
test_cli_extraer_adjuntos_llega_al_intake_de_email
test_cli_una_barra_en_la_direccion_ABORTA_sin_crear_nada
```

### ¿Algún test escribe fuera de `tmp_path`?

**Sí, indirectamente.** Openpyxl crea temporales de hojas `openpyxl.*` en el directorio temporal global del proceso cuando `ensure_case` prepara las plantillas. En estas corridas se redirigió ese directorio a `wd/tmp`, pero sigue estando **fuera del tmp_path individual**. Por ejemplo, `test_cli_email_dry_run_no_llama` genera y elimina tales ficheros. También se observa en el fichero nuevo, incluido el control de `ensure_case`.

Por semilla, en head se registraron 244 operaciones sobre esos nombres: **122 creaciones/aperturas de temporales y 122 eliminaciones**. No son 244 ficheros supervivientes. Pytest además crea el basetemp y gestiona sus nombres `current` y numeración de directorios; esas operaciones de infraestructura tampoco pertenecen al tmp_path individual.

El audit hook registra **0 escrituras bloqueadas fuera del workdir** en las cuatro corridas finales. No se observaron escrituras de expedientes ni locks en producción. Los roots del caso y el registro de workspaces quedan aislados por las fixtures; la afirmación estricta “nada fuera de tmp_path” necesita distinguir los temporales de openpyxl o fijar también el directorio temporal por test. No atribuyo este comportamiento, que también se mide en base, como regresión de R2.

## 6. Inventario de lo NO cubierto por los tests entregados

1. Pertenencia de referencia al preámbulo ante `#`/`###`, encabezados indentados, inserción antes de Partes fuera del preámbulo y segunda llamada sin duplicación.
2. Cercas heterogéneas, cierres demasiado cortos, falso cierre con lenguaje, inserción ante una cerca abierta, código indentado. Los tests de cerca solo compran el ejemplo convencional.
3. Los casos manuales de lista con continuación, sección vacía y cuerpo que empieza por sección no tienen sus propios tests; las sondas de esta revisión sí los recorrieron.
4. Todos los campos de CaseMeta frente a la tabla de propietarios: en especial ciudad/fecha y los dos campos de último checkin. Los seis parámetros existentes tampoco verifican la vía concreta del error.
5. YAML sintácticamente inválido y tipo uniforme de excepción, null explícito, claves duplicadas, comentarios/espacios y ausencia completa de frontmatter. Las dos pruebas nuevas de corrupción no acreditan conservación byte a byte, según M30/M31.
6. Reintento del CLI sin cuantía, reintento con otra cuantía y coherencia con el CRM ya creado. El test entregado repite exactamente el mismo importe.
7. Ausencia real de segundo alta, de pull y de creación de caso en las ramas negativas correspondientes, según los mutantes supervivientes.
8. Pruebas combinadas de claves ajenas dentro de meta, estructuras anidadas, estado D8, todos los campos de lock y cuerpo completo. Las aserciones de conservación actuales comprueban muestras concretas.
9. Fallos físicos de escritura/reemplazo, limpieza de temporal bajo fallos, concurrencia entre procesos/hilos, durabilidad y llamada a update_meta sin mutex. No son garantías adquiridas por pasar estos dos ficheros.
10. Valores multilineales o de tipo inesperado para campos del cuerpo, variantes de encabezados Setext/HTML/blockquote, cadenas vacías y nombres de Drive con varios W-codes. No hay una certificación completa de parser Markdown.
11. Citas de backlog/docstrings como parte verificable del cambio; las citas residuales se detectaron por lectura de fuente, no por pytest.

## 7. Lo que NO pude verificar

- No hay commits ni `.git`: identidad histórica del diff, procedencia de las renumeraciones, correspondencia con una rama remota y código exacto intermedio de R1, **SIN VERIFICAR**. Sí se verifica el contenido de estas copias y el digest del informe anterior.
- Suite completa del repositorio, fuera de los dos ficheros contratados: **SIN VERIFICAR**. No extrapolo 81 verdes al resto del proyecto.
- CRM/Drive/red reales, consulta de importes remotos, exclusión distribuida, permisos efectivos de checkout y efecto en Gmail: **SIN VERIFICAR**; se usaron dobles y barreras locales.
- Disco lleno real, corte abrupto de proceso, reemplazo fallido real en Windows y carreras: **SIN VERIFICAR**. La sonda inyecta `OSError`, no llena el disco. Se ejecutó el escritor real en los caminos normales.
- El audit hook acredita operaciones Python observadas; no equivale a una traza de todas las syscalls de bibliotecas nativas. No se afirma cobertura de vías no ejecutadas ni de todos los renderizadores Markdown. Para interpretar cercas/ATX se contrastó CommonMark.
- La batería dirigida de mutantes no es enumeración exhaustiva de mutaciones posibles. Sus resultados y límites están individualizados; ningún escenario no ejecutado se considera refutado.

## 8. Hashes de cierre y veredicto

| Fichero | SHA-256 | Comparación |
|---|---|---|
| `../head/scripts/abrir_caso.py` | `0dacfb3ecf5562288ee5be091f321bf2e38823ac6c4fcfbcca50dc2967cba870` | Igual a apertura |
| `../head/core/case_manager.py` | `b74c6a915eeaed44ab324b7b6237ee85d2f1843257e641958ac02f6af3c34a8a` | Igual a apertura |
| `../head/tests/test_case_manager_update_meta.py` | `e5d44c2ec0b4abbf88aed09bde72d3aa94823c67f137d1d0fbe2039333b2b8e7` | Igual a apertura |
| `../INFORME_R1.md` | `337f045fea0b05779c71f6a45fc4d075e9ebff809ac31e89c6bc1b4ced9c7a2f` | Igual a apertura |

Los cuatro pares coinciden. El informe se entrega en UTF-8 sin BOM, LF y un único salto final; su propio SHA-256 se declara por separado al devolverlo.

El motivo de no envío es concreto: persisten escenarios de destrucción de notas y se añade una sobrescritura silenciosa del importe al repetir el CLI. Los 81 verdes por semilla no contradicen esos escenarios, y las supervivencias medidas explican parte del hueco de cobertura. No se exige otra ronda por inercia: corresponde al autor adjudicar estos escenarios contra fuente y remediar lo que confirme.

VEREDICTO: NO-SHIP
<!-- informe-literal:fin:p7r2 -->

## 2. Evidencia verificada por mí, contra la fuente

La adjudicación razonada, hallazgo a hallazgo, vive en el §4 del plan hermano, que es
el documento que la decisión modificó. Aquí va la voz literal del revisor y nada más.
