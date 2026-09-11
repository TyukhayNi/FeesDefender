---
tipo: revision-adversarial
objeto: diff 763aba8..ef64131 — el semáforo E22 de la plantilla de viabilidad (MEJORAS #228)
objeto_rev: "1"
commit: ef64131
ronda: "1"
revisor: Codex
veredicto: LISTA-CON-CAMBIOS
marcador_nonce: e22r
sha256_informe: cbfe1a56cb84eb5f82201050c17828e77e4914bc42a8f815a649140969eac418
adjudicado_en: docs/superpowers/plans/2026-09-11-semaforo-e22.md §2
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# Acta de revisión adversarial R1 — el semáforo `E22`

- **Objeto revisado:** diff `763aba8..ef64131` — la plantilla `.xlsx`, su referencia, el CHANGELOG y los tests
- **Ronda:** R1 (única por presupuesto: no decide quién escribe ni destruye datos de cliente)
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` sin `.git`, solo lectura
- **Informe recibido:** 2026-09-11, `C:/t/rev-e22-123249/wd/INFORME.md`, 33751 bytes
- **Hallazgos:** 6 — 4 MEDIOS, 2 BAJOS; **6 confirmados, 0 refutados**
- **Remediado en:** `docs/superpowers/plans/2026-09-11-semaforo-e22.md` §2

**Por qué existe esta acta.** Yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**.

**Qué se le pidió, y es lo que hacía falta.** La amenaza real de este cambio no era la lógica sino
el binario: un `.xlsx` es un zip de XML y openpyxl no conserva todo. El mandato le pidió comparar
**el zip entrada por entrada**, no lo que openpyxl entiende — «openpyxl te enseña lo que entiende,
y la pregunta es qué no entendió». Mi propia verificación tenía justo ese punto ciego.

**El resultado principal es un descarte, y vale tanto como un hallazgo:** *«no se ha perdido
contenido del libro anterior»*. Medido por él sobre el zip, no afirmado por mí.

**Custodia.** Dos árboles `git archive` sin `.git`, directorio de ronda con nombre irrepetible
comprobado vacío. Hashes de los dos `.xlsx` y del fichero de tests, coincidentes al abrir y cerrar.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:e22r -->
# R1 — Semáforo de FINANZAS en la plantilla de viabilidad

## Higiene, alcance y método

Revisión realizada el 2026-09-11 sobre `C:/t/rev-e22-123249/base` y `C:/t/rev-e22-123249/head`, sin `.git`. Revisor: Codex. La adjudicación corresponde al autor contra las fuentes.

**Incidencia de apertura:** el listado inicial del workdir contenía `MANDATO.md` y **`_stdout.log`**. No abrí ni leí `_stdout.log`. No se cumple, por tanto, la condición de que solo hubiera `MANDATO.md`; se declara sin atribuir contenido al fichero adicional.

No escribí en las dos copias congeladas. Las ejecuciones, mutaciones, extracción de XML y pruebas de render se hicieron en copias bajo `wd`. El único entregable es este informe; los demás ficheros creados son material de prueba. No utilicé subagentes ni Antigravity.

Ejecuté `C:/Program Files/Git/usr/bin/diff.exe -ru ../base ../head`; terminó con código 1, correspondiente a diferencias. **Exactamente cinco ficheros distintos**, sin altas ni bajas:

- `.claude/skills/viabilidad-prerelleno/assets/plantilla_informe_viabilidad.xlsx`
- `.claude/skills/viabilidad-prerelleno/references/modelo_xlsx.md`
- `.claude/skills/viabilidad-prerelleno/CHANGELOG.md`
- `tests/test_render_informe_viabilidad.py`
- `docs/MEJORAS_FUTURAS.md`

Comparé todas las entradas descomprimidas del XLSX con `zipfile`, no solo los objetos que entiende openpyxl. Contrasté los árboles XML completos y comprobé que, retirando exclusivamente las adiciones identificadas, los XML de hoja y estilos vuelven a ser iguales a los de `base`. Complementé esa prueba con openpyxl, ejecuciones de pytest, mutantes dirigidos y ocho renders de LibreOffice. No se ha reparado el objeto revisado.

## Hashes de apertura

SHA-256 de los bytes, sin normalización:

| Fuente | SHA-256 |
|---|---|
| `base/.claude/skills/viabilidad-prerelleno/assets/plantilla_informe_viabilidad.xlsx` | `fd04c997be7281380fae39f31c57dd04eea447cab80961509614e0c8a4500f98` |
| `head/.claude/skills/viabilidad-prerelleno/assets/plantilla_informe_viabilidad.xlsx` | `0f6016baf7468f815d3341ed654bd2706429944d7b8d49a57e861efb832c4b95` |
| `head/tests/test_render_informe_viabilidad.py` | `50f1969088ee68caef35f9738b1c345965225a8ea44cbb514f47d72f3d0fc223` |

## Hallazgos

### H-01 — MEDIO — La validación nueva no replica la antigua; la explicación de la asimetría es falsa

**Ancla:** ambos XLSX, `xl/worksheets/sheet1.xml`, `dataValidation[@sqref='E21']`; `head`, el mismo elemento para `E22`. Prosa: `docs/MEJORAS_FUTURAS.md:10822` y `.claude/skills/viabilidad-prerelleno/CHANGELOG.md:22`.

| Propiedad | E21 base | E21 head | E22 head |
|---|---|---|---|
| `type` | list | list | list |
| `formula1` | `"verde,amarillo,rojo"` | igual | igual |
| `showErrorMessage` | **1** | **1** | **0** |
| `allowBlank` | 1 | 1 | 1 |
| `showDropDown` | 0 | 0 | 0 |

No se endureció E21: su validación se conservó literalmente. Pero **ya tenía activado el aviso de error**. Es incorrecto afirmar que llevaba `False` y que poner `True` solo en E22 introduciría la diferencia. La diferencia la introduce precisamente esta adición.

**Escenario:** teclear `ámbar` en E22 → entrada sin alerta y sin fondo condicional. La misma entrada directa en E21 tiene habilitada la alerta; no corresponde describir ambas como aceptación silenciosa. La interpretación de la alerta procede del XML y de la documentación de Microsoft; no de una interacción ejecutada en Excel, que no estuvo disponible. Microsoft distingue la entrada directa del pegado que puede eludir validación: [validación y alertas en Excel](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/excel-add-ins-data-validation).

**Cambio propuesto para adjudicar:** corregir la explicación y decidir la nueva validación tomando como referencia el `True` real de E21. Igualarlas a ese valor no exige modificar JURÍDICO. Si se quiere una FINANZAS permisiva, declararla como decisión distinta, no como réplica.

### H-02 — MEDIO — Los tests detectan ausencia del semáforo, pero permiten un semáforo mal conectado y pérdidas del libro

**Ancla:** `tests/test_render_informe_viabilidad.py:310` (pertenencia mediante subcadena), `:334` (extrae solo texto entre comillas), `:356` (comparación relativa de fondos), `:372` (solo valores de dos anclas).

**Escenarios reproducidos con mutantes, sin modificar los tests:**

- Cambiar la validación de E22 a **E220** → E22 pierde el desplegable, pero pasan los seis casos nuevos. `"E22" in "E220"` es verdadero.
- Hacer que las tres fórmulas de FINANZAS lean **`$E$21`** → elegir jurídico verde y finanzas rojo pinta FINANZAS según JURÍDICO, pero pasan los seis casos nuevos. Los tests extraen `verde/amarillo/rojo`, sin comprobar qué celda gobierna ni el operador.
- Eliminar la protección de PREGUNTAS → desaparece la barrera para modificar las columnas fijas, pero pasan **los 32 casos del módulo completo**.

Cada una de las cuatro funciones nuevas sí tiene un mutante que la pone roja. Eso acredita sensibilidad a un defecto concreto, **no** conservación del libro ni funcionamiento visual. La tabla de mutaciones de §D detalla los controles y los supervivientes.

**Cambio propuesto:** comprobar pertenencia geométrica de la celda al rango; fórmula completa y tipo de regla; dominio y colores esperados contra una referencia independiente; opciones de validación; e invariantes del resto del libro. No anunciar conservación de hojas/protección/TOTAL como propiedad vigilada por estos cuatro tests.

### H-03 — MEDIO — PREEXISTENTE: «sin valor» en JURÍDICO se muestra rojo

**Ancla:** ambos XLSX, `INFORMACION!E21`, estilo 104; `xl/styles.xml`, relleno sólido con `fgColor="FFFF0000"`. `test_el_prerelleno_deja_el_semaforo_en_blanco`, línea 372, solo exige `value is None`.

**Escenario medido:** E21 y E22 sin valor → LibreOffice muestra JURÍDICO con fondo **rojo puro `#FF0000`** y FINANZAS sin fondo. Con `ámbar` ya almacenado ocurre lo mismo: no se activa ninguna regla y queda el estilo fijo. El rojo condicional válido es otro, `#FFC7CE`.

La estructura que causa el resultado es idéntica en `base` y `head`. No es una pérdida causada por la reescritura ni una escritura del generador. Sí contradice la lectura operacional «lo firma una persona» si el lector interpreta cualquier rojo como una valoración. El generador conserva ausencia de valores, no neutralidad visual. Conviene separar ambas propiedades al adjudicar, sin presentar una corrección de este defecto preexistente como parte ya realizada del diff.

### H-04 — BAJO — Los fondos coinciden; el aspecto completo del semáforo no

**Ancla:** `xl/styles.xml`, `dxfs` con índices 0–2 frente a 3–5; nuevos tests `:334` y `:354`.

Los tres estilos de JURÍDICO contienen fuente en **negrita**, con colores `FF006100`, `FF9C5700` y `FF9C0006`. Los tres nuevos contienen **solo relleno**, sin fuente.

**Escenario medido:** escribir `amarillo` en ambas anclas → mismo fondo `#FFEB9C`, pero JURÍDICO aparece centrado con texto marrón y negrita; FINANZAS conserva su texto negro normal y alineación de base. El render de LibreOffice confirma la diferencia. Los tests de «LOS_MISMOS_colores» no comparan fuente.

No se perdió la fuente antigua: se preservó íntegra. La afirmación sobre **`bgColor` y alfa** es exacta; si «mismo semáforo» pretende equivalencia visual completa, falta copiar la parte de fuente o acotar esa promesa. La alineación diferente pertenece al layout preexistente.

### H-05 — MEDIO — PREEXISTENTE: el filtro que debe producir el guion deja fuera 12 preguntas

**Ancla:** ambos XLSX, `xl/worksheets/sheet2.xml`, `autoFilter ref="B3:M88"`; `xl/workbook.xml`, nombre `_xlnm._FilterDatabase` de PREGUNTAS. `.claude/skills/viabilidad-prerelleno/references/modelo_xlsx.md:26` y la línea siguiente.

La plantilla tiene **88 IDs**, hasta la fila 103. Doce quedan fuera del filtro: `tl_01`, `esc_01`, `esc_01_fecha`, `esc_02`, `esc_03`, `esc_03_fecha`, `rec_02`, `rec_02_fecha`, `rec_03`, `rec_03_fecha`, `rec_04`, `rec_04_fecha`.

**Escenario:** resolver `rec_04` documentalmente, de modo que M102 sea `no`, y filtrar M por `sí` para preparar la entrevista → la fila 102 queda fuera del ámbito del filtro y no se oculta por ese criterio. La referencia es exacta cuando da `B3:M88`, pero no sostiene que el filtro entregue exclusivamente las preguntas pendientes de todo el cuestionario.

Es un problema del libro anterior, conservado sin cambios. Se declara por el barrido de completitud solicitado en §E; no se atribuye a este diff ni se exige arreglarlo de paso.

### H-06 — BAJO — PREEXISTENTES: quedan referencias contradictorias sobre el contrato de la plantilla

**Anclas y escenarios:**

- `references/modelo_xlsx.md:3` dice que la Skill A **no escribe BITACORA**, mientras su sección BITACORA y `scripts/render_informe.py` sí establecen y ejecutan una primera entrada. JSON mínimo → se rellenan B5:G5 de BITACORA. Un consumidor que trate la cabecera como contrato de no escritura recibe una modificación expresamente negada allí.
- `docs/CONVENCIONES_DESPACHO.md:366` llama canónica a `docs/PLANTILLA_INFORME_VIABILIDAD.xlsx`, ausente en las dos copias entregadas; su sección 19 describe unas **50 preguntas**, frente a los 88 IDs medidos en la plantilla que usa el generador. Seguir esa ruta o dimensionar una revisión con esa descripción no conduce al artefacto auditado ni a su cuestionario completo. No he comprobado si aquel fichero existe fuera de las copias congeladas.

Los pasajes históricos del backlog y las actas anteriores no son, por sí solos, nuevas falsedades: describen el estado anterior y deben conservar su carácter histórico. La falsedad introducida en la explicación de cierre sobre `showErrorMessage` se recoge separadamente en H-01.

## §A — Dictamen de las seis afirmaciones

| Nº | Dictamen | Medición propia |
|---|---|---|
| 1. Añadió sin regenerar | **Sostenida como conservación del contenido anterior**, con matiz de empaquetado | Todos los elementos previos de la hoja y estilos permanecen iguales. Se añadieron una validación, tres reglas y tres `dxf`. Se reescribió el ZIP y se actualizó `modified`; no puedo certificar el procedimiento de autoría a partir de dos archivos. |
| 2. E22:H22 cubre dos merges | **Exacta para el diseño descrito** | Merges `E21:H21`, `E22:F22`, `G22:H22` idénticos antes/después. Las fórmulas nuevas leen `$E$22` de forma absoluta. Los renders pintan ambas mitades. `E22:F22` excluiría el bloque derecho. |
| 3. Mismos colores y alfa | **Exacta para el relleno; no para toda la presentación** | Fondos `FFC6EFCE`, `FFFFEB9C`, `FFFFC7CE` en ambas filas. Las fuentes condicionales solo están en E21 (H-04). |
| 4. Nada más cambió | **Exacta para los invariantes funcionales enumerados; no literalmente para todo el fichero** | Hojas, otras validaciones, protección, merges, fórmulas, estilos existentes y CF de E21 conservados. Cambian también `docProps/core.xml/modified` y las fechas de las entradas ZIP. No hay pérdida funcional del contenido anterior. |
| 5. El generador deja el semáforo en blanco | **Exacta para los valores usando esta plantilla** | E21/E22 vacías en ambas plantillas y en las salidas ejecutadas; script sin cambios, sin asignaciones a esas anclas. No equivale a ausencia de color: H-03. El modo `--plantilla` conserva los valores de una plantilla alternativa, no los borra expresamente. |
| 6. No endureció E21; ambas aceptan errores en silencio | **Primera parte exacta; segunda falsa** | E21 conserva `showErrorMessage=1`; E22 añade `0`. La asimetría es nueva y no está descrita correctamente (H-01). |

## §B — ¿Qué se perdió al reescribir el binario?

**No encontré ninguna pérdida del contenido anterior del libro.** La evidencia permite una respuesta más fuerte que «openpyxl lo abre»: nueve de las doce entradas son iguales byte a byte, y en las otras tres se explica toda la diferencia.

### Inventario completo del ZIP

Tamaños descomprimidos en bytes. El XLSX completo pasa de **37.204 a 37.283 bytes** (+79).

| Entrada | Base | Head | Resultado |
|---|---:|---:|---|
| `docProps/app.xml` | 205 | 205 | Idéntica |
| `docProps/core.xml` | 609 | 609 | Solo fecha `modified` |
| `xl/theme/theme1.xml` | 3.733 | 3.733 | Idéntica |
| `xl/worksheets/sheet1.xml` | 221.432 | 221.985 | +CF E22 y +validación E22 |
| `xl/worksheets/sheet2.xml` | 67.312 | 67.312 | Idéntica |
| `xl/worksheets/sheet3.xml` | 5.388 | 5.388 | Idéntica |
| `xl/worksheets/sheet4.xml` | 3.717 | 3.717 | Idéntica |
| `xl/styles.xml` | 37.290 | 37.518 | +3 `dxf`, preservando los 3 anteriores |
| `_rels/.rels` | 531 | 531 | Idéntica |
| `xl/workbook.xml` | 1.366 | 1.366 | Idéntica |
| `xl/_rels/workbook.xml.rels` | 939 | 939 | Idéntica |
| `[Content_Types].xml` | 1.383 | 1.383 | Idéntica |

**Entradas eliminadas: 0. Añadidas: 0. Orden de entradas: idéntico**, el de la tabla. No hay renombrados, cambio de método de compresión (DEFLATE/8 en todas), campos extra ni comentarios ZIP. Permanecen los atributos externos. Cambian las fechas ZIP de todas las entradas de `2026-06-07 04:23:20` a `2026-09-11 12:25:24`; no se les atribuye zona horaria que el formato no guarda. Los tamaños comprimidos que cambian son core 275→278, sheet1 18.451→18.519 y styles 2.309→2.317; el resto es igual. Los offsets posteriores se desplazan por esos incrementos, no por una reordenación.

### Diferencias semánticas exhaustivas

1. `docProps/core.xml`: `modified` pasa de `2026-06-07T02:23:20Z` a `2026-09-11T10:25:24Z`. Creator, created y lastModifiedBy se conservan. **Se sustituye la fecha de última modificación anterior**, algo normal al guardar; no se rompe el uso de la hoja, aunque «no cambió nada más del fichero» no es literal y no debe confundirse con custodia de bytes.
2. `sheet1.xml`: tras el CF antiguo se añade `conditionalFormatting sqref="E22:H22"`, reglas `type="expression"`, prioridades 4/5/6, `dxfId` 3/4/5 y `stopIfTrue="0"`. Fórmulas `$E$22="verde"`, `$E$22="amarillo"`, `$E$22="rojo"`. Se añade la validación E22; su contador pasa 1→2. Retirados esos dos elementos y restaurado el contador, **el árbol completo coincide con base**.
3. `styles.xml`: `dxfs count` pasa 3→6, con tres nuevos rellenos. Quitados únicamente los índices 3–5 y restaurado el contador, **el árbol completo coincide con base**. No se sustituyó ni renumeró un estilo anterior.

Además del contraste estructural, retiré las adiciones mediante sustituciones sobre los **bytes XML originales**: una coincidencia para el CF nuevo, otra para la validación nueva y los tres últimos `dxf`, restaurando sus contadores. Sheet1 y styles quedaron **idénticos byte a byte a base**. Revirtiendo solo el timestamp, core también quedó idéntico. No aparece ninguna normalización o reordenación adicional de elementos XML preexistentes. Por tanto, no hay una pérdida oculta atribuible a que openpyxl no entienda una extensión que sí estuviera en estas entradas de `base`.

### Inventario de conservación funcional

| Familia | Resultado antes/después |
|---|---|
| Hojas y visibilidad | 4: INFORMACION, PREGUNTAS, AVISOS LLM, BITACORA; mismo orden, todas visibles |
| Estilos de base | 14 fuentes, 19 rellenos, 87 bordes, 4 formatos numéricos propios, 147 `cellXfs`, 1 `cellStyleXf`, 1 estilo nombrado; idénticos y en el mismo orden |
| Celdas con estilo | INFORMACION 6.127; PREGUNTAS 1.093; AVISOS 74; BITACORA 50. Coordenadas, valores y referencias de estilo iguales |
| Dimensiones y layout | A1:Z245, B1:M103, B1:J10 y B1:H10; anchos de columnas, atributos y alturas de filas conservados |
| Combinaciones | 67/13/2/2 por hoja, con los mismos rangos y orden |
| Fórmulas | H14=`H13/100*E14*1.21`; H16=`H14-H15`; H18=`H16-H17`; F39=`SUM(F25:G38)`; cuatro, idénticas |
| Cachés de fórmulas | Los cuatro `<v>` ya estaban vacíos en base y siguen vacíos; **no se perdió ningún valor cacheado** |
| Recálculo | `calcId=191029`, `fullCalcOnLoad=1`, sin cambios |
| Protección | Solo PREGUNTAS tiene `sheetProtection`; todas sus opciones son idénticas. INFORMACION, AVISOS y BITACORA no estaban protegidas y siguen sin estarlo |
| Validaciones fuera de INFORMACION | PREGUNTAS K6:K103 y M6:M103; AVISOS G5:G10, I5:I10 y J5:J10; BITACORA ninguna. XML idéntico |
| CF previo | Solo E21:H21, tres reglas, prioridades 1/2/3 y `dxfId` 0/1/2; idénticas |
| Vistas y paneles | Se conserva incluso la vista inicial A44 / selección B49:H93 de INFORMACION; paneles F5, C5 y B5 en las otras hojas |
| Filtros y nombres | B3:M88, B3:J10 y B3:G10; sus tres `_xlnm._FilterDatabase` y ámbitos permanecen iguales |
| Impresión | Márgenes y configuración existentes preservados; INFORMACION mantiene A4 vertical. No había áreas/títulos de impresión definidos que se hayan eliminado |
| Objetos y extensiones | No existen en ninguno entradas de imágenes, dibujos, gráficos, OLE, VBA, comentarios/notas, VML, vínculos externos ni tablas. No hay hipervínculos ni `extLst` perdidos; tampoco `sharedStrings` ni `calcChain` eliminados: ya estaban ausentes |

Que un elemento estuviera ausente en `base` no constituye pérdida de `head`. No se puede reconstruir con estas dos copias qué hubiera podido perderse en guardados anteriores a `base`.

## §C — Funcionamiento efectivo del semáforo

### Regla, rango y entradas

Las referencias **absolutas** `$E$22` hacen que todas las celdas de `E22:H22`, incluidos los dos merges, dependan de una sola decisión: E22. La fila 21 depende de `$E$21`. No se solapan sus rangos; las prioridades nuevas 4–6 no colisionan con 1–3 y no existen otros CF en esta hoja. Los tres literales son mutuamente excluyentes. No observé interferencia entre filas.

Los fondos son, en orden verde/amarillo/rojo: `#C6EFCE`, `#FFEB9C`, `#FFC7CE`, todos almacenados con alfa `FF`. El blanco está admitido por `allowBlank="1"`. `showDropDown="0"` no oculta la flecha. La diferencia de alertas está en H-01.

### Comprobación con motor de hoja de cálculo

Se prepararon ocho copias cambiando únicamente los valores del semáforo y el encuadre de impresión: B20:H22, otras hojas ocultas solo en esas sondas. LibreOffice **26.2.2.2**, en modo headless y con perfil propio dentro de `wd/tmp/native`, produjo ocho PDF, una página cada uno. Inspeccioné el resultado rasterizado y los rectángulos y fuentes del PDF. **Es ejecución de Calc, no de Excel.**

| Valores almacenados | Resultado medido |
|---|---|
| E21=E22=`verde` | Ambos bloques verdes; ambas mitades de fila 22 cubiertas |
| E21=E22=`amarillo` | Ambos amarillos; ambas mitades cubiertas |
| E21=E22=`rojo` | Ambos rojo claro condicional; ambas mitades cubiertas |
| E21=E22=`AMARILLO` | Igual fondo amarillo que en minúsculas |
| E21=E22=`ámbar` | Ninguna regla; E21 conserva rojo fijo, E22 sin relleno |
| E21 y E22 vacías | Ninguna regla; mismo resultado anterior de fondos |
| E21/E22 vacías, G22=`amarillo` | FINANZAS sin fondo: G22 no gobierna las reglas |
| E21=E22=`verde`, G22=`rojo` | Toda FINANZAS verde, con el texto `rojo` dentro del bloque derecho verde |

Las comparaciones usadas son igualdad de texto, no `EXACT`; Calc no distingue mayúsculas para estos casos. No debe confundirse esa evaluación de CF con la comprobación de una lista literal por la interfaz de Excel: **no ejecuté el tecleo ni la alerta de Excel**, por lo que no doy por medida allí la admisión de `AMARILLO` en E21.

**Celdas no ancla:** F22 pertenece al merge E22:F22; H22 al merge G22:H22. Asignarles un valor con openpyxl lanza `AttributeError: 'MergedCell' object attribute 'value' is read-only`. El helper `render_informe.set_cell` contiene precisamente la comprobación de `MergedCell`, avisa y omite esa escritura. No hay un segundo valor independiente válido en esas celdas. **G22 sí es un ancla independiente**, editable porque INFORMACION no está protegida, pero carece de validación y no interviene en ninguna fórmula del semáforo. El rango pinta ambas mitades; no convierte sus dos anclas en un único campo. La contradicción visual del último caso es un límite real del layout, no una pérdida del ZIP.

Los valores fuera del dominio que lleguen a estar almacenados no reciben un color de respaldo por CF. Sobre el estilo fijo, el resultado de ambas filas es diferente (H-03). Las escrituras programáticas de las sondas no prueban que una validación de Excel hubiera aceptado el tecleo; Microsoft documenta diferencias según el modo de entrada: [alcance de la validación](https://support.microsoft.com/en-us/excel/more-on-data-validation).

También inspeccioné el XLSX producido por el test real de pre-relleno: E21/E22/G22 son `None`; conserva ambos CF, sus seis fórmulas y fondos, ambas validaciones y el relleno fijo rojo de E21. Por tanto, el semáforo añadido llega a la salida del generador, aunque esa conservación del CF no sea un aserto de los tests nuevos.

## §D — Ejecuciones y fuerza de los tests

### Entorno y comandos

Python requerido: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`, versión **3.14.4**. `pytest 9.1.1`, `openpyxl 3.1.5`; pytest-randomly activo. `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, `TEMP` y `TMP` redirigidos a `wd/tmp/process`; `-p no:cacheprovider`.

Copié `head` a un árbol ejecutable dentro de `wd`. Para el control negativo copié `base` y sustituí **solo** `tests/test_render_informe_viabilidad.py` por el de `head`. Las dos semillas se pasaron explícitamente mediante `--randomly-seed=777` y `--randomly-seed=31337`. Se crearon previamente los padres de todos los `--basetemp`, siempre relativos y dentro del workdir.

Comando del módulo, desde cada copia: `python -m pytest tests/test_render_informe_viabilidad.py -p no:cacheprovider --randomly-seed=<semilla> --basetemp=_tmp/<corrida> --junitxml=../tmp/results/<corrida>.xml --tb=short`.

| Copia y pruebas | Semilla | Pasan | Fallan | Errores | Omitidos |
|---|---:|---:|---:|---:|---:|
| Head, módulo completo | 777 | 32 | 0 | 0 | 0 |
| Head, módulo completo | 31337 | 32 | 0 | 0 | 0 |
| Base + tests head, módulo completo | 777 | 29 | 3 | 0 | 0 |
| Base + tests head, módulo completo | 31337 | 29 | 3 | 0 | 0 |

Son **cuatro funciones nuevas y seis casos**: dos funciones parametrizadas por fila y dos simples. En base fallan exactamente:

1. `test_las_dos_filas_del_semaforo_tienen_desplegable[22]`: cero validaciones.
2. `test_las_dos_filas_del_semaforo_tienen_sus_tres_colores[22]`: no hay CF E22:H22.
3. `test_las_dos_filas_del_semaforo_usan_LOS_MISMOS_colores`: `StopIteration` al buscar el bloque 22.

Pasan los dos casos de fila 21 y el del pre-relleno en blanco. **Confirmo el reparto declarado por el autor**, distinguiendo funciones y casos parametrizados.

### Suite completa

La ejecución válida usa una copia limpia `wd/runfull` y temporales **fuera de esa copia**, dentro del workdir. Comando desde `runfull`: `python -m pytest -n 4 -p no:cacheprovider --randomly-seed=<semilla> --basetemp=../tmp/full/clean<semilla> --junitxml=../tmp/results/clean<semilla>.xml --tb=short`. No se añadieron exclusiones ni se alteraron tests.

| Semilla | Casos | Pasan | Fallan | Errores | Skip | Xfail | Salida |
|---|---:|---:|---:|---:|---:|---:|---:|
| 777 | 5.306 | 5.200 | 5 | 0 | 91 | 10 | 1 |
| 31337 | 5.306 | 5.200 | 5 | 0 | 91 | 10 | 1 |

**La suite completa no está verde en estas copias.** Los cinco fallos coinciden exactamente entre semillas y se reprodujeron ejecutando esos cinco casos sobre la copia de **base** (5 fallos / 0 errores):

- `test_session_close_no_pude_medir.py::TestLaRutaQueSugiere::test_en_este_repo_encuentra_uno_que_existe` y `::TestLaVerja::test_el_mensaje_sugiere_un_interprete_QUE_EXISTE`: esperan un `.venv` local que no existe en las copias congeladas; la resolución devuelve `None`.
- `test_gitignore_no_inerte.py::test_una_negacion_no_cuenta_como_regla_inerte`, `::test_ninguna_regla_de_gitignore_es_inerte` y `::test_los_readme_de_telemetria_estan_rescatados_y_la_telemetria_no`: `git ls-files` / `git check-ignore` devuelven 128 porque no hay `.git`.

Esto acredita limitaciones del entorno recibido para esos tests, no un verde ni una regresión del XLSX. No fabriqué un índice Git ni un venv para satisfacer sus premisas. Los 32 casos del módulo revisado pasan también dentro de cada corrida completa. No se usó `--runslow`: los **91 skip** y **10 xfail** son cobertura no ejecutada o defectos esperados, no aprobaciones.

**Incidencias del montaje, conservadas como diagnóstico:** dos lanzamientos iniciales del módulo fallaron por permisos al crear basetemp/salida JUnit con el cwd de la herramienta; no aportan evidencia de ejecución de los cuerpos. Se resolvió lanzando desde `wd` y cambiando de directorio dentro del comando. Además, mi primera corrida completa colocó basetemp bajo `runhead`, y provocó rechazos de `case_mutex.raiz_de_locks` porque prohíbe locks bajo `settings.project_root`: dio **365 failed, 4.817 passed, 91 skipped, 6 xfailed, 27 errors**, semilla 777. Interrumpí la segunda corrida con ese montaje incorrecto y repetí ambas semillas con el comando válido anterior. No uso aquel resultado como evidencia contra el diff. Las pruebas focalizadas del semáforo no ejercitan esa barrera y sus resultados se confirman con las corridas completas válidas.

### Mutación dirigida

Cada mutante parte de los bytes originales de `head` en una copia independiente; se restauran plantilla y generador entre corridas. Para mutar el binario se sustituye el XML indicado dentro del ZIP, sin reconstruir el libro entero con openpyxl. Se ejecutan los seis casos nuevos (`-k semaforo`), salvo donde se indica el módulo completo. Semilla 777.

| Mutante | Cambio dirigido | Resultado |
|---|---|---|
| M01 | Eliminar validación E22 | **Muerto:** desplegable[22] falla; 5 pasan |
| M02 | Eliminar CF E22:H22 | **Muerto:** tres_colores[22] e igualdad de colores fallan; 4 pasan |
| M03 | Fondo verde de fila 22 → `FF112233` | **Muerto:** igualdad de colores falla; 5 pasan |
| M04 | Generador escribe E22=`verde` antes de guardar | **Muerto:** pre-relleno en blanco falla; 5 pasan |
| M05 | `sqref` de validación E22 → E220 | **Sobrevive:** 6 pasan; E22 queda sin desplegable |
| M06 | Las tres fórmulas nuevas leen `$E$21` | **Sobrevive:** 6 pasan; FINANZAS obedece a JURÍDICO |
| M07 | `allowBlank` de E22 → 0 | **Sobrevive:** 6 pasan; no comprueban ese atributo. Con alerta desactivada, este mutante no demuestra por sí solo bloqueo efectivo del blanco |
| M08 | Eliminar `sheetProtection` de PREGUNTAS | **Sobrevive:** los **32** casos del módulo pasan |
| M09 | Eliminar `<f>` de F39, perdiendo TOTAL | **Sobrevive:** los **32** casos del módulo pasan |
| M10 | Los seis fondos condicionales → `FF000000` | **Sobrevive:** 6 pasan; igualdad entre filas y alfa FF permiten tres colores nominales que son todos negros |
| M11 | Eliminar la fuente condicional del verde de E21 | **Sobrevive:** 6 pasan; pérdida de presentación antigua no detectada |
| M12 | Generador escribe G22=`rojo` antes de guardar | **Sobrevive:** 6 pasan; el test de blanco solo mira E21 y E22 |
| M13 | El binario de plantilla trae E22=`verde`, sin cambiar el generador | **Muerto:** pre-relleno en blanco falla; 5 pasan. El generador conserva ese valor, aunque imprime «VIABILIDAD en blanco» |

Balance: **5 mutantes muertos / 8 supervivientes**, sin errores de colección/setup usados como muerte de mutante. Las cinco muertes corresponden a los fallos de aserción o búsqueda indicados. Cada fila representa una ejecución real, no una predicción por lectura. M01–M03 y M13 dan además un control de muerte de las cuatro funciones mediante cambios exclusivamente en el binario.

No hay un test nuevo que nunca pueda ponerse rojo: M01–M04 matan las cuatro funciones. Sí sobreviven defectos dentro de lo que se afirma comprobar, y la conservación general está fuera de su alcance. La prueba del binario real de §B acredita conservación **en este diff**; no convierte esa propiedad en una garantía de la suite.

### Escrituras fuera de `tmp_path`

**Sí, por openpyxl.** Una corrida adicional del módulo con un `sys.addaudithook` de observación, sin cambiar sus asertos ni su generador, dio **32 passed**. Registró **104 creaciones `tempfile.mkstemp`**, cuatro por cada una de las 26 serializaciones de las cuatro hojas, bajo `wd/tmp/process/openpyxl.*`, fuera del `tmp_path` individual. El test nuevo de pre-relleno produce **cuatro** de esos temporales. Los otros tres tests nuevos solo cargan la plantilla.

Las escrituras explícitas de `_generar` —JSON y XLSX de salida— sí van a `tmp_path`. El propio preámbulo del módulo, líneas 11–15, ya reconoce el temporal del proceso; no es un defecto nuevo ocultado. En mi ejecución esos temporales se dirigieron al workdir. El rastreo Python del módulo no constituye una auditoría de todos los syscalls de toda la suite ni de los procesos nativos.

## §E — Prosa y cierre del backlog

La línea 13 de `modelo_xlsx.md` describe ahora correctamente las dos validaciones, los dos CF y los tres merges. Su explicación de E22:H22 se sostiene con el XML y con los renders. El arreglo sí añade desplegable y color a FINANZAS; el cierre de esa carencia concreta tiene soporte.

El changelog y el cierre de `MEJORAS #228` mezclan hechos ciertos con dos excesos: dicen que E21 era permisiva cuando no lo era (H-01), y atribuyen a los cuatro tests vigilancia de invariantes que dejan caer mutantes destructivos (H-02). «Sin regenerar» es defendible como no reconstruir el formato anterior desde cero, pero no como ausencia de reescritura ni de cambios de metadatos.

Los textos históricos sobre E22 sin semáforo permanecen en un backlog fechado y con cierre posterior; no los trato como descripciones actuales falsas. El alcance no incluye acreditar el reempaquetado/reimportación del `.skill` en Cowork, que el propio changelog deja pendiente. Los otros desajustes encontrados en el barrido de referencias están en H-03, H-05 y H-06.

## Inventario de lo NO cubierto por los cuatro tests nuevos

- Conservación del inventario ZIP, propiedades, objetos, extensiones, estilos previos, protección, impresión, vistas, paneles, filtros, nombres definidos y cachés.
- Fórmulas del TOTAL y de importes, referencias y resultados de cálculo.
- Fórmula completa, referencia gobernante, operador, tipo, duplicados y prioridades de las reglas CF; interferencias futuras por solapamiento.
- Correspondencia de los colores con sus valores RGB originales, cuando ambas filas se alteran de igual manera; fuente condicional y aspecto real.
- Semántica geométrica de `sqref`, `allowBlank`, `showErrorMessage`, visibilidad del desplegable y demás opciones de validación.
- Render de las dos mitades del merge, interacción mediante teclado/pegado y entrada en el ancla derecha G22.
- Neutralidad visual del pre-relleno, G22/H22, plantillas alternativas y conservación del CF en la salida generada (los tests de CF cargan la plantilla, no la salida).

Varias de esas propiedades se midieron en esta revisión; **no forman parte de la cobertura permanente de esos tests**.

## Lo que NO pude verificar

- **Excel nativo:** crear una instancia aislada de `Excel.Application` falló con HRESULT `0x80070520`, «Una sesión de inicio especificada no existe». No se abrió ningún original con Excel. No afirmo haber probado el desplegable mediante clic, las alertas de entrada ni el comportamiento de selección de una celda combinada en Excel. Los resultados visuales corresponden a LibreOffice.
- No hice una prueba exhaustiva de todos los modos de entrada, locales, versiones de Excel/Calc ni de Excel web. Las ocho sondas no son esa matriz.
- No recalculé y concilié importes de un expediente real: comparé todas las fórmulas y cachés, y ejecuté entradas sintéticas del generador. No realicé valoraciones jurídicas ni actos fiscales.
- No comprobé un paquete instalado en Cowork, el uso histórico de FINANZAS ni los informes cerrados de casos reales.
- No puedo probar cómo se produjo el binario ni pérdidas anteriores a `base`; solo la transformación entre las dos copias recibidas.
- No pude acreditar una suite enteramente verde: cinco tests dependen del índice Git o del `.venv` no incluidos. Se ejecutaron y fallaron igual sobre base; quedan sin verificar sus contratos en un checkout real. Tampoco se ejecutaron los tests omitidos ni se resolvieron los defectos marcados xfail. El desglose y los intentos de montaje están en §D.

## Hashes de cierre

Recalculados al cierre; **los tres coinciden con la apertura**.

| Fuente | SHA-256 de cierre |
|---|---|
| `base/.claude/skills/viabilidad-prerelleno/assets/plantilla_informe_viabilidad.xlsx` | `fd04c997be7281380fae39f31c57dd04eea447cab80961509614e0c8a4500f98` |
| `head/.claude/skills/viabilidad-prerelleno/assets/plantilla_informe_viabilidad.xlsx` | `0f6016baf7468f815d3341ed654bd2706429944d7b8d49a57e861efb832c4b95` |
| `head/tests/test_render_informe_viabilidad.py` | `50f1969088ee68caef35f9738b1c345965225a8ea44cbb514f47d72f3d0fc223` |

## Recomendación para adjudicación

La incorporación de color y desplegable en E22 está acreditada y **no se ha perdido contenido del libro anterior**. Antes de dar el cierre por exacto, corregir la afirmación sobre la validación de E21 y la cobertura anunciada, y reforzar los controles contra rangos y fórmulas mal conectados. Los defectos preexistentes se separan del diff para que el autor decida su alcance, sin exigir una ampliación silenciosa del encargo.

VEREDICTO: LISTA-CON-CAMBIOS
<!-- informe-literal:fin:e22r -->

## 2. Evidencia verificada por mí, contra la fuente

La adjudicación razonada vive en el §2 del plan hermano. Aquí va la voz literal del revisor.
