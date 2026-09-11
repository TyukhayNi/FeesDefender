---
tipo: revision-adversarial
objeto: "diff b59bb49..722d063 — el filtro y el rojo de la plantilla de viabilidad (MEJORAS #242, #243)"
objeto_rev: "1"
commit: 722d063
ronda: "1"
revisor: Codex
veredicto: LISTA-CON-CAMBIOS
marcador_nonce: plant243
sha256_informe: 2370fe4c291c6fc6727f5b8bbac26ee03b617923934f455cf3ab56cc96b164e6
adjudicado_en: docs/superpowers/plans/2026-09-11-plantilla-viabilidad-filtro-y-rojo.md §3
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# Acta de revisión adversarial R1 — el filtro y el rojo de la plantilla

- **Objeto revisado:** diff `b59bb49..722d063` — la plantilla `.xlsx`, sus tests, su referencia, el CHANGELOG y el backlog
- **Ronda:** R1 (única por presupuesto: no decide quién escribe ni destruye datos de cliente)
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` sin `.git`, solo lectura
- **Informe recibido:** 2026-09-11, `C:/t/rev-plantilla-1435/wd/INFORME.md`, 44023 bytes
- **Hallazgos:** 7 — 1 ALTO, 5 MEDIOS, 1 BAJO; **7 confirmados, 0 refutados**
- **Remediado en:** `docs/superpowers/plans/2026-09-11-plantilla-viabilidad-filtro-y-rojo.md` §3

**Por qué existe esta acta.** Yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**.

**Qué se le pidió, y es lo que hacía falta.** Lo primero del mandato fue comparar los dos `.xlsx`
**a nivel de zip**, no con openpyxl — «openpyxl enseña lo que entiende, y la pregunta es qué no
entendió». Lo confirmó: 9 entradas idénticas, 3 modificadas, y solo las tres sustituciones
declaradas.

**Y lo segundo, que es lo que devolvió el valor:** no se limitó a leer los tests, **los mutó**.
Siete mutaciones del binario que **pasaban los 45 casos del módulo** — entre ellas poner a cero la
fórmula que calcula los honorarios que lee el CFO.

**Custodia.** Dos árboles `git archive` sin `.git`, directorio de ronda con nombre irrepetible
comprobado vacío antes de lanzar. `sha256` de los dos `.xlsx` coincidentes al abrir y al cerrar.

**`sha256` del `INFORME.md` original:** `2370fe4c291c6fc6727f5b8bbac26ee03b617923934f455cf3ab56cc96b164e6`.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:plant243 -->
HIGIENE INCUMPLIDA AL INICIO: además de `MANDATO.md` estaba `_stdout.log`; se enumeró su nombre y NO se leyó su contenido.

# Informe adversarial R1 — plantilla de viabilidad

Objeto: copias congeladas `base` (commit declarado `b59bb49`) y `head` (commit declarado `722d063`). Revisión única del diff, en castellano, sin modificación de las fuentes. Fecha de ejecución comprobada en el reloj local: 2026-09-11. Este informe aporta evidencia para la adjudicación de Claude; no la sustituye.

**Resultado principal:** el contenido descomprimido del XLSX solo cambia en las tres sustituciones declaradas. No hay una cuarta alteración de XML. Sin embargo, los tests dejan pasar daños demostrados en el informe del CFO y en el filtro, la documentación contiene errores numéricos e inferencias presentadas como mediciones, y el libro conserva una infracción preexistente del esquema en `sheetView`.

## 1. Custodia, método y ejecución

Fichero en ambas copias: `.claude/skills/viabilidad-prerelleno/assets/plantilla_informe_viabilidad.xlsx`.

| Momento | Copia | SHA-256 |
|---|---|---|
| Apertura | base | `d2728f952281799739f7bb0c9f2f8502fa45bcb05d979ad1ed11e4fdf711fa22` |
| Apertura | head | `dd1cefcd2016b65c85cc9e5333e114180b9498bf9d90714efe8583760339e63d` |

Los dos hashes coinciden con el mandato. La atribución a los commits es la recibida en él; no se ha acreditado mediante un historial Git independiente.

La primera línea registra la excepción de higiene antes de crear material propio. Después se crearon únicamente dentro de `wd` scripts de auditoría, pruebas y temporales, copias de ejecución, logs, evidencias y este informe. No se ha leído `_stdout.log`, ni ejecutado código desde `base` o `head`, ni escrito en esos árboles. No se usó `agy`, no se delegó el razonamiento ni se tocó ningún sistema de cliente. No se aplicaron las instrucciones genéricas del repositorio de abrir/cerrar sesión, modificar estado o ejecutar toda la suite: contradicen el alcance de solo lectura y el mandato específico de esta ronda.

La comparación de A y el análisis de B/C se hicieron con `zipfile`, bytes y XML, **sin openpyxl**. Se aplicaron las instrucciones de `Spreadsheets` para auditoría de solo lectura y de verificación antes de declarar resultados, prevaleciendo la metodología expresa del mandato. `openpyxl` solo se usó al ejecutar el módulo de tests copiado. Entorno medido: Python 3.14.4, pytest 9.1.1 y openpyxl 3.1.5.

Se copiaron literalmente el módulo de tests, `render_informe.py` y el XLSX a `wd/test_copy`, preservando sus rutas relativas. Los dos ficheros Python se comprobaron byte a byte contra `head`; no se cambiaron sus asertos. El generador es idéntico en `base` y `head`.

Comando de cada ejecución, sustituyendo `<caso>` por el nombre de la tabla de D.4:

```text
C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe -B -m pytest -q -p no:cacheprovider --noconftest --basetemp pytest_tmp/<caso> --rootdir test_copy test_copy/tests/test_render_informe_viabilidad.py --tb=short
```

`cwd=wd`; `TEMP` y `TMP` apuntan a `wd/temp`; `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8` y `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. `--basetemp` es relativo y queda en `wd`. Se ejecuta **el módulo aislado**, sin el `conftest.py`, los guards globales ni los plugins del repositorio. Esa integración no se acredita. Hubo intentos preliminares inválidos del arnés propio: un regex agrupaba varios `xf` y faltaba crear el padre de `--basetemp`. Se corrigió el arnés y se repitieron todos los casos afectados; los resultados que figuran aquí no contienen errores de preparación.

**Dos semillas: SIN VERIFICAR**, por instrucción expresa del mandato. La sonda de disponibilidad local encontró un módulo `pytest_randomly`, en contra de la premisa ambiental del encargo; no se activó, ni se intentaron las dos semillas, ni se confunde disponibilidad con ejecución.

Anclas: salvo indicación contraria, `tests/...`, `docs/...` y las rutas de la skill son de **head**. `skill/` abrevia `.claude/skills/viabilidad-prerelleno/`. Los offsets del binario son **bytes UTF-8 descomprimidos, base cero**, relativos a la entrada ZIP, no posiciones del archivo XLSX completo. Cuando se cita base expresamente, se usa su entrada. Los anclajes principales previos a la ampliación tienen el mismo offset en ambas copias.

## 2. Hallazgos

### H-01 — MEDIO — El contrato del filtro excede ampliamente lo que sus tests verifican

**Anclas:** `tests/test_render_informe_viabilidad.py:509`, `:523`, `:544`, `:547` y `:482`; `xl/worksheets/sheet2.xml:66436` y `:66160`; `xl/workbook.xml:978`.

**Qué falla:** comprobar solo el último número del rango no acredita que las preguntas y la columna M queden dentro. Igualar dos cadenas no acredita el ámbito del nombre definido. Comprobar `protection.sheet` no acredita que el filtro sea utilizable bajo protección.

**Escenarios ejecutados:** sincronizar ambos rangos a `B3:L103` quita M del filtro; sincronizarlos a `B100:M103` deja casi todo el cuestionario fuera; cambiar `localSheetId="1"` a `"0"` atribuye el nombre a INFORMACION; cambiar `sheetProtection autoFilter="0"` a `"1"` prohíbe el uso del filtro. **Cada mutante pasa los 45 casos del módulo.** El artefacto head actual sí tiene el rango y los permisos correctos: el hallazgo es una laguna de los tests nuevos y del invariante, no una regresión ya introducida.

**Qué lo arreglaría:** analizar los rectángulos, comprobar cabecera y columnas de trabajo, y que todas las coordenadas de preguntas estén dentro; verificar una única definición pertinente con ámbito local de PREGUNTAS y `hidden=1`; comprobar `sheet=True`, `autoFilter=False` y el permiso de ordenación si se promete. Repetir el contrato en la salida del generador. Para un rango fijo, afirmar explícitamente `B3:M103`; para uno evolutivo, fijar inicio/columnas y derivar el extremo inferior de IDs independientes.

### H-02 — MEDIO — «Sin color» se reduce a «no sólido» e «iguales» a dos campos del relleno

**Anclas:** `tests/test_render_informe_viabilidad.py:569` y `:582`; `xl/styles.xml:1444`, `:26715`, `:29353`; `xl/worksheets/sheet1.xml:16603`, `:17392`.

**Qué falla:** un relleno tramado también pinta. La comparación de `patternType` y `start_color.rgb` no abarca los colores de fondo, tipos de color, tintes, resto del bloque, bordes, geometría combinada ni todas las reglas que pudieran cubrirlo.

**Escenario ejecutado:** sustituir el `fill` 0 por un `patternFill darkGrid` con primer plano rojo y fondo blanco conserva las dos anclas vacías y el patrón distinto de `solid`. **45 casos verdes**, pese a introducir relleno visible en las dos filas y en muchos otros usuarios de ese fill. No se ha renderizado este mutante en Excel; el daño de formato queda codificado en XML.

**Qué lo arreglaría:** exigir el estado sin relleno y comparar el perfil completo pertinente de todos los bloques E:H, incluidas otras reglas aplicables. Nombrar el test de igualdad según su contrato real: neutralidad del fondo. La igualdad visual total no es una propiedad de esta plantilla, como explica B.5.

### H-03 — MEDIO — La prueba de conservación de estilo no conserva la fuente ni el borde completo

**Anclas:** `tests/test_render_informe_viabilidad.py:600`, `:601`, `:602`; `xl/styles.xml:29353`, `:579`, `:492`, `:8011`.

**Qué falla:** `font.b or font.sz` es verdadero con cualquier tamaño no nulo; no exige negrita, nombre ni tamaño original. El borde se acepta si queda solo arriba **o** a la izquierda; no fija los cuatro lados, colores o grosores. La alineación se reduce a su componente horizontal.

**Escenario ejecutado:** cambiar únicamente `fontId="1"` por `"0"` en el xf 104 sustituye Arial 8 por Calibri 11. **45 casos verdes**. La mutación del autor a estilo 0 falla por perder el centrado, pero eso no demuestra conservación de cada componente del estilo.

**Qué lo arreglaría:** comparar todos los atributos e hijos del xf original, exceptuando exclusivamente `fillId`, y conservar sus tablas referidas. Añadir asertos semánticos del perfil esperado de fuente, borde, alineación y formato numérico, con verificación del bloque combinado. No basta la verdad lógica de un atributo.

### H-04 — ALTO — El módulo acepta corromper la fórmula de honorarios que alimenta el informe del CFO

**Anclas:** `tests/test_render_informe_viabilidad.py:472` y `:483`; `skill/references/modelo_xlsx.md:12`; `skill/scripts/render_informe.py:183` y `:268`; `xl/worksheets/sheet1.xml:11132`.

**Qué falla:** el invariante comprueba `F39` pero no las otras tres fórmulas de INFORMACION, ni una conservación exhaustiva de las partes del paquete fuera de la lista de cambios. Los nuevos tests no cubren esta frontera.

**Escenario ejecutado:** cambiar solo `<f>H13/100*E14*1.21</f>` por `<f>0</f>` en H14. **Los 45 casos pasan**. Se inspeccionó también un XLSX generado por esa ejecución: la fórmula de H14 sigue siendo `0`. Para inputs de prueba H13=100.000 y E14=5, la fórmula original da 6.050; la mutada da 0 y propaga el error a H16/H18. Esta comparación es aritmética independiente, no una sesión de recálculo de Excel. La fórmula de head **no está dañada**; el mutante demuestra que el módulo no lo detectaría.

**Qué lo arreglaría:** ampliar las invariantes con las cuatro fórmulas y probar un caso económico sencillo en la salida. Para esta edición binaria, añadir una prueba de preservación del paquete contra una referencia aprobada: inventario de partes y comparación exacta permitiendo solo las tres sustituciones. El test de fórmulas y la preservación de partes cubren riesgos distintos y son complementarios.

### H-05 — MEDIO — El XLSX conserva una infracción de cardinalidad del esquema, anterior al diff

**Anclas:** base y head, `xl/worksheets/sheet2.xml:194`; quinto `selection` en `:555`. Regla primaria: [Open XML SDK, definición de SheetView](https://github.com/dotnet/Open-XML-SDK/blob/main/data/schemas/schemas_openxmlformats_org_spreadsheetml_2006_main.json#L13938).

**Qué falla:** el `sheetView` tiene cinco `selection`: topRight, bottomLeft, bottomRight, bottomLeft y bottomRight. La secuencia del esquema permite como máximo cuatro. El conteo y una validación XSD limitada a esta restricción fallan en ambas copias; `openpyxl` las acepta. El bloque no ha cambiado.

**Escenario concreto:** un consumidor o validador que aplique esa restricción rechaza esta vista. **SIN VERIFICAR** si una versión concreta de Excel repara, ignora o rechaza el libro: no se ha abierto Excel. No se afirma que el XLSX sea imposible de abrir.

**Qué lo arreglaría:** depurar las selecciones duplicadas conservando las correspondientes a los paneles, validar el paquete y comprobar la apertura/guardado con Excel. Es deuda preexistente; no debe adjudicarse como una cuarta modificación de este diff ni repararse silenciosamente dentro de la auditoría.

### H-06 — BAJO — Dos recuentos documentales no coinciden con el artefacto

**Anclas:** `skill/CHANGELOG.md:10`, `:15`; `docs/MEJORAS_FUTURAS.md:11278`; `xl/worksheets/sheet2.xml:4314`, `:58359`, `:65519`.

**Qué falla:** se omite la sección de la fila 5 al decir que ya había siete dentro de B3:M88. Hay **ocho**. El CHANGELOG intercambia los subtotales: hay **cinco** `esc_*` y **seis** `rec_*`, no seis y cinco. El total doce sí es correcto.

**Escenario concreto:** una persona que reproduzca la medición o diseñe un test a partir del cierre recibe un inventario incompleto o asigna preguntas a la sección equivocada.

**Qué lo arreglaría:** incluir la fila 5, corregir los subtotales y derivarlos del inventario explícito de C.3/E.

### H-07 — MEDIO — Una explicación histórica plausible aparece como medición concluyente

**Anclas:** `skill/CHANGELOG.md:13`, `:21`; `docs/MEJORAS_FUTURAS.md:11244`, `:11275`; `xl/worksheets/sheet2.xml:56753`, `:57412`.

**Qué falla:** que el filtro acabe en `vue_05` no fecha cuándo se añadieron las secciones 9–11. Ambas copias ya contienen las mismas preguntas. La ausencia de función documentada del rojo y el hecho de que el render no escriba E21 tampoco prueban que nunca tuviera una función humana de «pendiente».

**Escenario concreto:** se cierra una decisión de diseño como si se hubiera contrastado su historia y uso con fuentes que estas copias no aportan. La coincidencia con el fin de la sección 8 apoya una hipótesis, no la causalidad narrada.

**Qué lo arreglaría:** etiquetar esas explicaciones como inferencias, o aportar una versión anterior que muestre la incorporación de secciones y evidencia del contrato de uso del color. No hace falta inventar historia para justificar el rango actual: los 88 IDs, el texto de instrucciones y M6:M103 ya sustentan su cobertura.

## 3. Respuestas al §2

### A. Comparación del ZIP

**A.1. Nombres y orden.** Coinciden exactamente. Inventario completo, con el orden físico/lógico de entradas en ambos archivos:

| Nº | Entrada | Bytes descomprimidos base → head | Comparación |
|---|---|---|---|
| 1 | `docProps/app.xml` | 205 → 205 | IDÉNTICA |
| 2 | `docProps/core.xml` | 609 → 609 | IDÉNTICA |
| 3 | `xl/theme/theme1.xml` | 3733 → 3733 | IDÉNTICA |
| 4 | `xl/worksheets/sheet1.xml` | 221985 → 221985 | IDÉNTICA |
| 5 | `xl/worksheets/sheet2.xml` | 67312 → 67313 | MODIFICADA |
| 6 | `xl/worksheets/sheet3.xml` | 5388 → 5388 | IDÉNTICA |
| 7 | `xl/worksheets/sheet4.xml` | 3717 → 3717 | IDÉNTICA |
| 8 | `xl/styles.xml` | 37662 → 37662 | MODIFICADA |
| 9 | `_rels/.rels` | 531 → 531 | IDÉNTICA |
| 10 | `xl/workbook.xml` | 1366 → 1367 | MODIFICADA |
| 11 | `xl/_rels/workbook.xml.rels` | 939 → 939 | IDÉNTICA |
| 12 | `[Content_Types].xml` | 1383 → 1383 | IDÉNTICA |

**A.2. Identidad de cada entrada.** La tabla enumera por completo las **nueve idénticas** y las **tres modificadas**. «Idénticas» aquí significa bytes devueltos por descompresión, no equivalencia reconstruida con una biblioteca de hojas de cálculo. Se comprobó cada entrada; no se infiere identidad por CRC. Véase A.4 para la distinción con el flujo comprimido.

**A.3. Diff textual completo.** A continuación están todos los hunks, sin excluir atributos ni elementos. Para hacer legible el XML minificado solo se introducen saltos entre `><`, sin reserializar, ordenar atributos ni normalizar entidades. Los números de línea de este bloque pertenecen a esa vista; los anclajes probatorios son los offsets de la tabla posterior. El [diff completo de las líneas XML originales](diff_xml_completo.patch) conserva también las líneas minificadas completas y las marcas de ausencia de salto final.

```diff
--- base/xl/worksheets/sheet2.xml
+++ head/xl/worksheets/sheet2.xml
@@ -4120,7 +4120,7 @@
 </row>
 </sheetData>
 <sheetProtection selectLockedCells="0" selectUnlockedCells="0" sheet="1" objects="0" insertRows="1" insertHyperlinks="1" autoFilter="0" scenarios="0" formatColumns="1" deleteColumns="1" insertColumns="1" pivotTables="1" deleteRows="1" formatCells="0" formatRows="1" sort="0"/>
-<autoFilter ref="B3:M88"/>
+<autoFilter ref="B3:M103"/>
 <mergeCells count="13">
 <mergeCell ref="B2:M2"/>
 <mergeCell ref="B54:M54"/>
--- base/xl/styles.xml
+++ head/xl/styles.xml
@@ -1364,7 +1364,7 @@
 <xf numFmtId="0" fontId="0" fillId="0" borderId="5" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0">
 <alignment horizontal="right"/>
 </xf>
-<xf numFmtId="0" fontId="1" fillId="7" borderId="28" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0">
+<xf numFmtId="0" fontId="1" fillId="0" borderId="28" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0">
 <alignment horizontal="center"/>
 </xf>
 <xf numFmtId="0" fontId="0" fillId="8" borderId="4" pivotButton="0" quotePrefix="0" xfId="0"/>
--- base/xl/workbook.xml
+++ head/xl/workbook.xml
@@ -10,7 +10,7 @@
 <sheet xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" name="BITACORA" sheetId="4" state="visible" r:id="rId4"/>
 </sheets>
 <definedNames>
-<definedName name="_xlnm._FilterDatabase" localSheetId="1" hidden="1">'PREGUNTAS'!$B$3:$M$88</definedName>
+<definedName name="_xlnm._FilterDatabase" localSheetId="1" hidden="1">'PREGUNTAS'!$B$3:$M$103</definedName>
 <definedName name="_xlnm._FilterDatabase" localSheetId="2" hidden="1">'AVISOS LLM'!$B$3:$J$10</definedName>
 <definedName name="_xlnm._FilterDatabase" localSheetId="3" hidden="1">'BITACORA'!$B$3:$G$10</definedName>
 </definedNames>
```

| Entrada | Intervalo base [inicio, fin) | Intervalo head | Sustitución |
|---|---|---|---|
| `xl/worksheets/sheet2.xml` | [66457,66459) | [66457,66460) | `88` → `103` |
| `xl/workbook.xml` | [1068,1070) | [1068,1071) | `88` → `103` |
| `xl/styles.xml` | [29389,29390) | [29389,29390) | `7` → `0` |

Se volvió a comprobar por una vía independiente que aplicar las tres sustituciones completas y únicas a los bytes de base produce exactamente los bytes de head de cada parte. **No hay ningún otro cambio de contenido XML**, incluidos nodos que openpyxl pudiera ignorar. El digest del anexo con el diff original es `36c11b0a047a1286147d308de08bfffb1c821cee6891c06791877587f9f3b8f3`.

**A.4. Metadatos y compresión.** No cambian los nombres, el orden, las fechas DOS (2026-09-11 12:57:40 en las 12 entradas, sin zona horaria), el método DEFLATE=8, los flags=0, la plataforma creadora=0, las versiones 20/20, atributos internos/externos, campos extra o comentarios. No hay cifrado ni comentario de archivo. Cambian los CRC de las tres partes editadas; `sheet2.xml` y `workbook.xml` ganan un byte descomprimido; `styles.xml` pasa de 2.314 a 2.310 bytes comprimidos. Las posiciones posteriores a styles y el directorio central se desplazan cuatro bytes. El archivo completo pasa de **37.276 a 37.272 bytes**; el directorio central conserva 784 bytes y empieza en 36.470 → 36.466.

Matiz de completitud: **solo ocho flujos comprimidos son idénticos**. Además de las tres partes editadas, cambia el flujo DEFLATE de `sheet1.xml`, sin cambiar su tamaño comprimido, CRC ni un solo byte descomprimido. Por tanto, «se copió cada entrada byte a byte» es cierto para los nueve contenidos lógicos preservados, pero no si se interpreta como copia literal de sus secuencias comprimidas. No se puede deducir el algoritmo de edición empleado solo del resultado.

Se comprobaron las cabeceras locales frente al directorio central, sus tamaños/CRC/nombres y el directorio final; `ZipFile.testzip()` devuelve `None` para ambos. No se detecta un problema de empaquetado que explique un fallo de apertura. **La apertura con Excel no se ejecutó**; se distingue este resultado de la infracción XML de A.5.

**A.5. Validez OOXML.** **No es plenamente conforme:** se ha demostrado una violación preexistente en `CT_SheetView`, H-05. Cinco selecciones exceden el máximo cuatro del modelo de contenido de Open XML SDK. Se hizo un conteo en las cuatro hojas y una validación ejecutable con lxml y un XSD mínimo que reproduce exclusivamente esa secuencia; falla sheet2 en base y head. Las otras hojas tienen 1, 3 y 3 selecciones. El XSD mínimo deja abiertos atributos y contenido de cada selección: **no se presenta como validación integral ECMA/ISO**.

Además, se verificaron: integridad ZIP, XML bien formado en las doce entradas, ausencia de entradas duplicadas, destinos de relaciones presentes, IDs de relación no duplicados, tipos de contenido correspondientes a partes existentes, conteos declarados de tablas de estilos/merges/validaciones y límites de las referencias de estilos y dxf. Esos controles estructurales no dieron incidencias. No convierten un XML bien formado o una carga con openpyxl en prueba de conformidad.

**SIN VERIFICAR:** validación completa de todos los XSD y restricciones semánticas de ECMA-376/ISO 29500. Se localizó el [paquete oficial ECMA-376](https://ecma-international.org/publications-and-standards/standards/ecma-376/); su descarga al workdir fue bloqueada por los permisos de red del entorno. No se eludió ese bloqueo. La fuente primaria consultada para la restricción concreta fue [el esquema del Open XML SDK](https://github.com/dotnet/Open-XML-SDK/blob/main/data/schemas/schemas_openxmlformats_org_spreadsheetml_2006_main.json#L13938). Una sola infracción comprobada basta para descartar la afirmación global de conformidad.

### B. Estilos — MEJORAS #242

**B.1. Usuarios del xf 104.** Recuento sobre todas las celdas XML de **base**:

| Parte / hoja | Celdas con `s="104"` |
|---|---|
| sheet1 / INFORMACION | 1: E21, offset 16603 |
| sheet2 / PREGUNTAS | 0 |
| sheet3 / AVISOS LLM | 0 |
| sheet4 / BITACORA | 0 |

Tampoco hay referencias a ese estilo en filas o columnas. Es correcta la afirmación de una sola **celda almacenada**. Como E21 es el ancla combinada, su formato puede afectar visualmente al bloque E21:H21: no debe interpretarse «una celda» como un solo cuadrado visible independiente.

**B.2. Conservación del xf.** La celda E21 y su índice 104 son idénticos. Comparación de su definición en `xl/styles.xml:29353`:

| Componente | base | head |
|---|---|---|
| fillId | 7 | 0 |
| fontId | 1 | 1 |
| borderId | 28 | 28 |
| numFmtId | 0 | 0 |
| xfId | 0 | 0 |
| alignment | horizontal=center | horizontal=center |
| applyAlignment | 1 | 1 |
| otros `apply*` | ausentes | ausentes |
| pivotButton / quotePrefix | 0 / 0 | 0 / 0 |

No se pierde ningún otro atributo o hijo, ni se modifican las definiciones de fuente, borde o formato. Que los tests no lo aseguren no invalida la comparación directa, que aquí sí lo demuestra.

**B.3. Fill 7 sin usuarios.** La tabla conserva 19 fills. El índice 7 (`xl/styles.xml:2050`) es sólido, `fgColor=FFFF0000`, `bgColor=FFFFFF00`; el 0 (`:1444`) contiene `<patternFill/>`. En base solo xf 104 usa 7; en head ningún `cellXf` lo usa. Dejar una entrada sin uso no desplaza índices ni rompe referencias; no se conoce una obligación de que cada fill sea utilizado. Su mera presencia no produce una infracción de esquema ni implica que se pinte una celda. Eliminarla exigiría actualizar todos los índices posteriores y aumentaría el riesgo de edición.

No se afirma haber verificado la respuesta de todos los validadores o Excel. La tabla contiene además otro fill rojo (8), referido por xfs 105/106, **sin celdas usuarias** en base ni head; no contradice «una única celda con rojo puro», que cuenta celdas, no definiciones. Los colores de relleno no deben identificarse solo por fgColor si se pretende comparar estilos completos.

**B.4. cellStyleXfs y nombres.** Hay un único `cellStyleXf`, índice 0, con `fontId=0`, `fillId=0`, `borderId=3`, `numFmtId=0` (`xl/styles.xml:16706`). El único estilo con nombre es `Normal`, con `xfId=0` y `builtinId=0`. Ninguno referencia fill 7. El `xfId` de un estilo con nombre indexa `cellStyleXfs`, no `cellXfs`: no es una referencia indirecta al xf de celda 104. Ambos bloques permanecen idénticos.

**B.5. ¿E21 vacía se ve igual que E22 vacía?** **Igual neutralidad de relleno, sí, según XML; identidad visual completa, no acreditada y no descrita por el XML.** En head E21 (xf 104) y E22 (xf 83) están vacías y usan fill 0. F21:H21 y F22:H22 tampoco tienen relleno fijo. Las tres reglas por fila comparan `$E$21` o `$E$22` con `verde`, `amarillo` y `rojo`; ninguna condición es verdadera para una celda vacía. Ambas filas referencian los mismos dxf 0/1/2, con fondos `FFC6EFCE`, `FFFFEB9C`, `FFFFC7CE` y fuente en negrita de color asociado. Los dxf 3/4/5 son copias sin uso en esas reglas, conservadas.

Anclas del condicional: `xl/worksheets/sheet1.xml:220734` y `:221069`. Las diferencias de prioridad y `stopIfTrue` ya existían; con las anclas vacías y esas reglas mutuamente excluyentes no activan un relleno adicional.

E21:H21 es un solo merge (`sheet1.xml:219597`); la fila 22 contiene E22:F22 y G22:H22 (`:220513` para el primero). E21 usa borde 28 y alineación horizontal centrada; E22 usa borde 22 sin esa alineación explícita. Hay un borde interior fino en la separación F/G de la fila 22; el borde exterior superior/inferior también cumple posiciones diferentes dentro del recuadro. Así, «se ven IGUAL» es excesivo si abarca geometría y bordes. Que estén vacías hace invisible el distinto centrado, pero no elimina los bordes.

**SIN VERIFICAR:** render nativo, resolución de bordes entre merges, apariencia final según versión/tema/zoom, interacción del formato condicional al introducir valores, impresión/PDF y apertura sin reparaciones. No se ha abierto Excel ni se aporta una captura como evidencia visual.

### C. Filtro — MEJORAS #243

**C.1. Otros sitios.** Se buscaron en las cuatro hojas y en el inventario del paquete `sortState`, `tableParts`, `extLst`, `sheetView/sheetViews`, `sheetPr`, `filterColumn` y partes `xl/tables/*`. No hay `sortState`, `tableParts`, `filterColumn`, `extLst` de hoja ni tablas. PREGUNTAS tiene `sheetPr` con outline/pageSetUp y `sheetViews` con panel congelado F5, cinco selecciones A1 y sin rango de filtro adicional. `sheetProtection autoFilter="0"` es un permiso, no otra copia del rango. `workbookView autoFilterDateGrouping` tampoco almacena ese rectángulo.

Para **PREGUNTAS**, los dos lugares del rango son el autoFilter de `sheet2.xml:66436` y `_xlnm._FilterDatabase` de `workbook.xml:978`, ámbito `localSheetId=1`, oculto. Hay otros filtros legítimos en AVISOS LLM (B3:J10) y BITACORA (B3:G10), con sus nombres locales (`workbook.xml:1085` y `:1192`). No son rangos olvidados de PREGUNTAS y permanecen idénticos.

**C.2. Filas de sección.** Las nuevas filas 89, 91 y 97 contienen cabeceras combinadas B:M, igual tipo de estructura que las secciones anteriores. Antes estaban fuera del filtro y sus filas no podían ocultarse por ese criterio; ahora están incluidas como filas dentro del rango, sin una excepción que las preserve como encabezados de grupo. Las secciones antiguas ya estaban incluidas: **5, 29, 32, 44, 54, 58, 66 y 83**, ocho. Después son once. La fila 3 es la única cabecera de autoFilter; la fila 4 de descriptores también cae en el cuerpo del filtro.

M está vacía/no almacenada como celda independiente en esas filas combinadas. Al filtrar M por `sí`, es esperable que esas cabeceras no satisfagan el criterio y se oculten; no constituyen preguntas para el render. Esto es una inferencia de la estructura y el criterio, **no una reproducción en Excel**: el tratamiento nativo exacto de filtros con merges y la ordenación permanecen SIN VERIFICAR. La ampliación no introduce una clase nueva de fila, pero sí somete tres cabeceras antes excluidas a ese comportamiento. «Excel las trata igual que antes» sería incorrecto si se refiere a esas tres filas concretas.

**C.3. ¿Residuo demostrado?** Se acredita el dato espacial: la sección 8 empieza en B83, su último ID `vue_05` está en C88, y Team leader empieza en B89. Son anclas `sheet2.xml:53815`, `:56753` y `:57412`. No se acredita la cronología de construcción. Es una hipótesis razonable que el filtro quedara sin ampliar; la afirmación «se añadieron después» exige historial anterior no presente en la comparación. La presencia anterior de ocho secciones refuta que B3:M88 excluyera **todas** las cabeceras, pero no prueba todos los motivos por los que alguien eligió ese final.

Inventario de las preguntas que pasan a estar dentro:

| Fila | ID |
|---|---|
| 90 | `tl_01` |
| 92 | `esc_01` |
| 93 | `esc_01_fecha` |
| 94 | `esc_02` |
| 95 | `esc_03` |
| 96 | `esc_03_fecha` |
| 98 | `rec_02` |
| 99 | `rec_02_fecha` |
| 100 | `rec_03` |
| 101 | `rec_03_fecha` |
| 102 | `rec_04` |
| 103 | `rec_04_fecha` |

Hay 88 IDs distintos, 76 con fila ≤88 y doce después. El rango crece quince filas: doce preguntas y tres secciones. El final 103 está comprobado en C103 (`sheet2.xml:65519`).

**C.4. Protección y validación.** El bloque de protección es idéntico (`sheet2.xml:66160`): `sheet="1"`, `autoFilter="0"`, `sort="0"`. Esos dos últimos valores indican que las operaciones no están bloqueadas por esos flags; el permiso de autofiltro **sigue presente**. La propiedad OOXML es un bloqueo, según [Microsoft, SheetProtection.AutoFilter](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.sheetprotection.autofilter?view=openxml-3.0.1). Esto no certifica que Excel permita cualquier ordenación sobre un rango con merges/celdas bloqueadas.

La validación de M ya era y sigue siendo `list`, `sqref="M6:M103"`, `formula1="sí,no"`, `allowBlank=1`, `showErrorMessage=0`, `showDropDown=0` (`head sheet2.xml:67031`; en base empieza un byte antes). No depende del rango de autoFilter: filtrar no modifica esa regla ni crea valores. K6:K103 también permanece igual. El cambio incluye en el filtro las doce preguntas que ya estaban bajo validación, sin añadir validaciones. El comportamiento de desplegables y alertas de la UI sigue SIN VERIFICAR; el XML de M no solicita mostrar error y admite blanco.

**C.5. Estado aplicado persistido.** No hay filas con `hidden` verdadero en ninguna de las cuatro hojas de ninguna copia, ni `filterColumn` persistidos. `sheetPr` de PREGUNTAS no trae `filterMode`; el `autoFilter` solo contiene `ref`, sin criterios ni sortState. No se descubre un filtro ya aplicado que, por el cambio, empiece a ocultar preguntas distintas. El libro declara el ámbito, no una selección activa de `sí`.

### D. Tests

Se añadieron cinco funciones de test, que producen **seis casos** porque `test_el_semaforo_SIN_VALORAR_no_pinta_ningun_color` se parametriza en 21 y 22. El módulo de head tiene 45 casos. El control con la plantilla base produce 3 fallos y 42 aciertos: cobertura del final del filtro, ausencia de sólido en E21 y comparación de rellenos vacíos. El caso E22 ya pasaba.

**Dictamen individual de los cinco tests:**

| Test (nombre abreviado inequívoco) | Qué acredita realmente | Mutación que lo deja verde indebidamente |
|---|---|---|
| `test_el_filtro_del_guion_alcanza_a_TODAS_las_preguntas` (:514) | Existe un ref legible y su último número no es menor que la fila máxima de IDs encontrada | Ambos rangos a B100:M103; también B3:L103. Ejecutadas: todo el módulo verde. No exige cabecera ni columnas ni pertenencia completa. |
| `test_el_FilterDatabase_dice_lo_MISMO_que_el_autoFilter` (:530) | Un fragmento textual con ese nombre y destino PREGUNTAS coincide, quitando `$`, con el ref de hoja | `localSheetId=0` conservando el texto de destino. Ejecutada: todo el módulo verde. No verifica ámbito, unicidad ni hidden. El regex además depende del orden/forma serializada de atributos. |
| `test_el_semaforo_SIN_VALORAR_no_pinta_ningun_color` (:564), 21/22 | E21/E22 son None y su fill no es `solid` | Fill 0 con patrón darkGrid rojo. Ejecutada: ambos casos y todo el módulo verdes. No equivale a ausencia de relleno ni evalúa CF. |
| `test_las_dos_filas_del_semaforo_se_ven_IGUAL_estando_vacias` (:578) | Coinciden patternType y start_color.rgb de las dos anclas | El mismo fill tramado en ambas, o la mutación ejecutada de fuente en E21. Ambas sobreviven al módulo. Igualar dos valores también acepta dos perfiles igualmente incorrectos. |
| `test_quitar_el_relleno_de_E21_no_se_llevo_su_borde_ni_su_alineacion` (:591) | Horizontal=center, queda algún borde superior o izquierdo, y fuente negrita o tamaño no cero | fontId 1→0: Arial 8→Calibri 11. Ejecutada: todo el módulo verde. Propuesta adicional, NO EJECUTADA: alterar únicamente color/grosor de borde manteniendo un lado no vacío. |

**D.1. ¿Pasa por otro motivo?** `_ultima_fila_del_rango` (`:509–511`) busca `r"(\d+)$"`; no extrae un rectángulo. En el head sano devuelve 103 correctamente, por lo que no se acusa un falso cálculo de 103. Lo defectuoso es que el aserto acepta un rango que termina en 103 aunque empiece en 100 o no incluya M: pasa por una condición más débil que el nombre del test. Se ejecutaron ambos contraejemplos. El test del nombre definido sí mira el ZIP, pero su éxito solo prueba coincidencia textual, no la semántica local del nombre.

**D.2. `celda.font.b or celda.font.sz`.** Solo acredita que uno de esos valores es verdadero. En head la fuente es Arial 8 sin negrita; pasa por `sz=8`. El estilo predeterminado Calibri 11 también pasa por `sz=11`. No acredita conservación de fuente ni negrita. La prueba de mutación de H-03 elimina la duda experimental.

**D.3. Inventario de propiedades sin test suficiente en este módulo.**

- Preservación byte a byte de las nueve partes no editadas y lista exhaustiva de cambios permitidos en las tres restantes; nombres/orden/metadatos del ZIP y referencias OPC; conformidad de esquema. Esta ronda sí hace la comparación, pero el módulo no la automatiza.
- Geometría íntegra del filtro (inicio, cabecera, columnas y pertenencia de cada ID), ámbito/unicidad/hidden del nombre, permisos concretos bajo protección y ausencia de estados ocultos/criterios inesperados. No se prueba el uso del filtro ni su conservación en la salida generada.
- Usuarios del xf 104 en todas las hojas; identidad de todos sus atributos salvo fillId; conservación de las tablas referidas y de índices; fill 7 huérfano y ausencia de otros usuarios.
- Neutralidad real frente a patrones de relleno no sólidos, bgColor/fgColor y sus tipos/tintes; estilos de F:H y bordes completos; otras reglas CF superpuestas y formato a nivel de fila/columna. Los tests existentes sí vigilan algunas fórmulas, rangos y perfiles dxf, no todo su efecto visual.
- Fórmulas H14/H16/H18, valores económicos resultantes, contenidos fijos/cabeceras del CFO, impresión y diseño fuera de los asertos puntuales. F39 sí está vigilada; no se dice que no haya ningún test de fórmulas.
- Conducta visual y funcional nativa de Excel con merges, filtros, protección, desplegables, selección, guardado y recálculo. Los tests nuevos miran sobre todo la plantilla, no el perfil de estilo completo de la salida serializada por openpyxl.
- Correspondencia de cada afirmación documental con inventarios medidos y con fuentes históricas. Los errores de conteo de E no son detectados.

**D.4. Mutaciones.** Se reconstruyeron por ZIP los cuatro mutantes descritos en el CHANGELOG y siete adicionales, siempre partiendo de head y alterando solo las cadenas registradas. Cada caso se ejecutó contra **todo el módulo**, no únicamente contra el nuevo test.

| Caso / log `pytest_<caso>.log` | Resultado final |
|---|---|
| `head_control` | `45 passed in 26.23s`; exit 0 |
| `base_control` | `3 failed, 42 passed in 29.20s`; exit 1 |
| `autor_rojo` | `2 failed, 43 passed in 18.46s`; exit 1 |
| `autor_filtro_corto` | `1 failed, 44 passed in 20.86s`; exit 1 |
| `autor_nombre_corto` | `1 failed, 44 passed in 19.11s`; exit 1 |
| `autor_estilo_cero` | `1 failed, 44 passed in 18.07s`; exit 1 |
| `cfo_formula_cero` | `45 passed in 30.30s`; exit 0 |
| `filtro_sin_M` | `45 passed in 22.12s`; exit 0 |
| `filtro_desde_100` | `45 passed in 30.31s`; exit 0 |
| `fuente_distinta` | `45 passed in 18.17s`; exit 0 |
| `fondo_tramado` | `45 passed in 18.54s`; exit 0 |
| `filtro_bloqueado` | `45 passed in 19.12s`; exit 0 |
| `nombre_ambito_erroneo` | `45 passed in 23.37s`; exit 0 |

Los cuatro del autor **mueren en esta reproducción**. Eso corrobora su comportamiento actual, no prueba cuándo ejecutó el autor sus corridas históricas. Los siete adicionales sobreviven, y la mutación de H14 contesta expresamente a la pregunta del CFO. El manifiesto [mutaciones.json](mutaciones.json) incluye comandos, cambios literales, hash del XLSX mutado, stdout/stderr y código de salida. Las mutaciones se aplican a copias; al terminar se restaura la copia de ejecución a head.

**D.5. Invariantes existentes.** Sí, debían ampliarse para sostener el contrato de conservación que acompaña a esta edición binaria. `test_la_plantilla_conserva_sus_invariantes` (`:472`) solo fija nombres de hojas, `protection.sheet`, F39, cantidades de validaciones y cinco merges del semáforo. Un mismo número de validaciones no preserva sus rangos ni contenido. Se recomienda añadir el perfil completo pertinente, fórmulas económicas y geometría/permisos del filtro, y una prueba separada de preservación OOXML para la edición concreta. La referencia aprobada debe ser explícita; actualizar un hash a ciegas convertiría la prueba en una aceptación del daño.

### E. Documentación

Revisión de las líneas modificadas en `modelo_xlsx.md`, la entrada nueva del CHANGELOG y los cierres 242/243. Se distinguió texto histórico que explica el defecto anterior de las afirmaciones sobre head.

| Afirmación y ancla | Dictamen frente al artefacto |
|---|---|
| «88 IDs», «fila 103», «12 preguntas», `modelo_xlsx.md:26`, `CHANGELOG.md:9`, `MEJORAS:11254` | Correcto: 88 IDs no duplicados, máximo 103, doce después de 88. Se comprueba directamente en C de XML, no con el helper del render como oráculo. |
| «tl_01, los seis esc_* y los cinco rec_*», `CHANGELOG.md:10` | Incorrecto: 1 + **5** + **6**. La lista explícita de `MEJORAS:11255` sí coincide con las doce filas. |
| «siete filas de sección», `CHANGELOG.md:15`, `MEJORAS:11278` | Incorrecto: falta B5, sección 1. Son ocho antes y once después; las tres nuevas enumeradas sí son 89/91/97. |
| «última fila de la sección 8», `CHANGELOG.md:13`, `MEJORAS:11275` | Correcto como posición: C88=vue_05. |
| «residuo, medido», «se añadieron después», mismas anclas | No acreditado como historia causal. En ambas copias las secciones ya existen; hace falta una fuente anterior. H-07. |
| «única celda del libro con ese relleno», `CHANGELOG.md:21`, `MEJORAS:11244` | Correcto para las celdas almacenadas de base: solo E21 usa el fill 7, y solo ella tiene un fill sólido de primer plano FFFF0000. Hay otra definición roja sin usuarios; contar fills no es contar celdas. |
| «ningún documento lo menciona» / «no cumplía ningún papel de pendiente», `CHANGELOG.md:22`, `MEJORAS:11245` | No se acredita la ausencia en todo el corpus ni la inexistencia de un uso humano. El contexto aportado no asigna esa función y el render no toca E21/E22; la inferencia más fuerte no se sigue. Los documentos del diff sí mencionan el rojo para describir el defecto, por lo que la frase necesita acotarse a una función normativa documentada. |
| «xf 104, una sola celda», `CHANGELOG.md:25`, `MEJORAS:11246` | Correcto contando en todas las hojas. Su efecto visual abarca un merge; B.1. |
| «9 entradas idénticas, 3 modificadas», `CHANGELOG.md:25` | Correcto para los contenidos descomprimidos. No para los flujos comprimidos: ocho iguales; A.4. |
| «solo tres cadenas», `CHANGELOG.md:24` | Resultado corroborado exhaustivamente. El procedimiento histórico «se cambió por ZIP, no con openpyxl» no es deducible como hecho del autor solo de estos archivos, aunque el resultado es compatible. |
| «relleno 7 se queda», `CHANGELOG.md:26` | Correcto. Evita tener que ajustar índices posteriores si se suprime. No perjudica por sí mismo la validez. |
| «ninguna lleva relleno base», «color solo condicional», `modelo_xlsx.md:13` | Correcto para E21/E22 y sus bloques en el estado actual. La neutralidad se deduce de XML; no se ha acreditado por render de Excel. «Iguales» no debe extenderse a bordes/geometría. |
| «autoFilter B3:M103», «dos sitios», `modelo_xlsx.md:26` | Correcto para este rango de PREGUNTAS. El libro contiene además dos filtros de otras hojas; no son un tercer lugar para este rango. |
| «5 tests», «3 rojos antes», «4 mutantes muertos», `CHANGELOG.md:28` | Cinco funciones/seis casos; tres fallos en el control con base; cuatro mutantes reproducidos muertos. El alcance de lo que vigilan está sobreafirmado en sus nombres, H-01/H-02/H-03. |
| «sigue sin verificarse […] desplegable y alerta», `CHANGELOG.md:32` | Se mantiene SIN VERIFICAR en esta ronda. El añadido «no lo puede hacer una máquina» es una generalización no acreditada: esta auditoría no evalúa todas las posibilidades de automatización de Excel. |

La redacción de `MEJORAS:11223`, `:11234` y `:11254` conserva presentes («tiene», «hoy») al describir base: leída aisladamente es falsa sobre head, aunque el bloque «Cerrada» posterior desambigua la cronología. Conviene poner ese diagnóstico en pasado.

Defecto documental **preexistente y ya reconocido en #244, fuera de la reparación de este diff**: `modelo_xlsx.md:3` niega escritura de BITACORA, pero `:33` dice que se añade la primera entrada y `render_informe.py:258` la escribe por defecto. No se presenta como hallazgo nuevo introducido por 242/243. Otras reglas de negocio y afirmaciones sobre quién lee cada hoja no son inferibles de un XLSX y no se han auditado jurídicamente.

## 4. Inventario de lo NO cubierto por esta ronda

- **SIN VERIFICAR:** apertura, reparación, render, interacción, ordenación/filtrado efectivos, permisos efectivos en cada versión de Excel, impresión/PDF y recálculo nativo. No se ejecutó Excel, LibreOffice ni un sustituto visual como prueba de equivalencia.
- **SIN VERIFICAR:** validación XSD integral y todas las restricciones semánticas OOXML. Sí se refuta la conformidad plena mediante una infracción concreta validada, y sí se comprueba el empaquetado y las referencias enumeradas en A.5.
- **SIN VERIFICAR:** dos semillas, suite completa, plugins, conftest y guards globales del proyecto. El resultado medido corresponde a 45 casos del módulo aislado, sin reescribir sus asertos.
- **SIN VERIFICAR:** historial anterior a base que establezca la creación de secciones, proceso exacto de edición del autor, todas sus ejecuciones históricas y ausencia de documentación de uso del rojo en todo el corpus del despacho.
- No se hicieron todas las mutaciones posibles. Se ejecutaron once mutantes de XLSX más los controles head/base; las propuestas adicionales se distinguen de las ejecutadas. No se realizó una auditoría funcional completa del generador ni del resto del repositorio.
- No se acredita una conservación exhaustiva de características en todos los informes históricos o producidos por otras versiones de openpyxl. La comparación exhaustiva de partes corresponde a las dos plantillas congeladas objeto del mandato.
- No se repararon artefacto, tests o documentación; no se publicó, integró ni entregó un libro modificado al cliente. Los defectos preexistentes se separan de las lagunas nuevas de cobertura.

## 5. Evidencia de cierre y dictamen

Los scripts y evidencias quedan en el workdir: `audit_zip.py`, `evidencia_zip.json`, `inspect_details.py`, `detalles.json`, `check_schema_constraint.py`, `sheetview_constraint.xsd`, `validacion_estructura.json`, `run_mutations.py`, `mutaciones.json`, los logs `pytest_*.log`, los diffs textuales y `cierre_evidencia.json`. El informe es autosuficiente para los dictámenes; los anexos permiten reproducir los detalles y la diferencia minificada completa.

| Momento | Copia | SHA-256 |
|---|---|---|
| Cierre | base | `d2728f952281799739f7bb0c9f2f8502fa45bcb05d979ad1ed11e4fdf711fa22` |
| Cierre | head | `dd1cefcd2016b65c85cc9e5333e114180b9498bf9d90714efe8583760339e63d` |

Ambos hashes de cierre coinciden exactamente con los de apertura. La comparación final vuelve a demostrar las tres sustituciones y la identidad de las demás partes. Los hashes acreditan la no alteración de estos dos XLSX; no se presentan como digest de los repositorios completos.

El diff binario cumple el cambio declarado y no muestra pérdida colateral de contenido. Antes de aceptar las afirmaciones de completitud deben corregirse los tests y la documentación señalados; la infracción de esquema anterior debe adjudicarse expresamente como deuda preexistente. No se solicita otra ronda: este es el dictamen de la R1 única encargada, sujeto a la adjudicación contra fuente.

LISTA-CON-CAMBIOS
<!-- informe-literal:fin:plant243 -->

## 2. Evidencia verificada por mí, contra la fuente

Los siete hallazgos se comprobaron contra el artefacto antes de aceptarlos, y los siete salieron.
Las mediciones, con el fichero delante:

| Afirmación del revisor | Medido |
|---|---|
| las fórmulas de `INFORMACION` son **cuatro**, no una | `H14 = =H13/100*E14*1.21`, `H16 = =H14-H15`, `H18 = =H16-H17`, `F39 = =SUM(F25:G38)` |
| hay **ocho** filas de sección dentro de `B3:M88`, no siete | 5, 29, 32, 44, 54, 58, 66, 83 — **olvidé la 5** |
| son **cinco** `esc_*` y **seis** `rec_*`, no seis y cinco | `esc_01`, `esc_01_fecha`, `esc_02`, `esc_03`, `esc_03_fecha` (5); `rec_02`, `rec_02_fecha`, `rec_03`, `rec_03_fecha`, `rec_04`, `rec_04_fecha` (6) |
| `E21` es Arial 8, bordes `medium/hair/hair/medium`, centrado | idéntico a lo que dice el informe |
| la protección permite filtrar | `<sheetProtection … sheet="1" autoFilter="0" sort="0"/>` — en OOXML el atributo es una **prohibición**, así que `0` = permitido |

**Y sus siete mutantes se reprodujeron uno a uno**, primero contra los tests de `722d063` —donde
los siete sobrevivían— y después contra los remediados, donde los siete mueren. Con los cuatro
míos, **11 mutantes, 11 muertos**, cada uno matando el test que dice vigilar y ninguno más. La
plantilla quedó restaurada por `sha256` tras cada corrida.

**Lo que el revisor declaró SIN VERIFICAR y sigue sin verificarse:** todo lo que exige abrir Excel
—que el desplegable se despliegue, que la alerta salte, y qué hace Excel con las cinco
`<selection>` de `PREGUNTAS`—, y las dos semillas (su Python de sistema no trae `pytest-randomly`).
