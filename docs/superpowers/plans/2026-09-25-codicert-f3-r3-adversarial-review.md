---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-25-codicert-f3.md
objeto_rev: "3"
commit: 6d950b1
ronda: "3"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: y3ii
sha256_informe: bd46f2204108a2f678c3fc9af86a07f5daa10f904e8bc94ed84414368ae1767d
adjudicado_en: docs/superpowers/plans/2026-09-25-codicert-f3.md §14
---

# Acta — R3 adversarial sobre la REMEDIACIÓN de la R2 de F3 del envío certificado

Objeto: la **remediación** de la R2, `3ae4cbe` → `6d950b1` —el aportable pasa a ser la imagen de
lo conservado con capa de OCR, la relectura una lista blanca, H-02 a H-07, los tests de las ramas
sin cubrir y la documentación—, con los informes de la R1 y la R2 y sus adjudicaciones dentro del
objeto.

**Tercera ronda sobre la pieza, autorizada expresamente por Nikolai el 2026-09-25** («r3»): supera
el techo de dos de `CLAUDE.md`, que solo levanta él. La remediación de la R2 no era un parche sino
otra pieza —la imagen, el perfil y el puerto de OCR, código nuevo que nadie había atacado—, y su
cobertura independiente estaba declarada AUSENTE. **Mismo modelo que la R1 y la R2**
(`gpt-6-astra`·`medium`), por la misma frontera, silenciosa: un aportable con las condiciones dentro
parece correcto, y la relectura es un guard que, mal escrito, deja una cobertura que parece presente.

**Un primer intento murió sin informe, y se dice.** El lanzado a las 17:02 en
`C:\t\codicert-f3-r3-1700` lo cortó a los ~100.700 tokens el **filtro de contenido** de Codex
(`This content was flagged for possible cybersecurity risk`), cuando el revisor ya había corrido
la suite y construía sondas con marcadores llamados «SECRET». Sin informe, ese intento **no cubre
nada**: su `_stdout.log` se conserva como prueba de que existió. Este informe es del **segundo**,
relanzado en un directorio nuevo con el mismo encargo redactado como pruebas de conformidad —y un
marcador neutro para las sondas—, que es la forma que ya había sorteado el filtro el 2026-09-09.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.3` (binario `80f78947ad880e6e`), sondeado `VIVO` antes de montar el objeto |
| Modelo y esfuerzo | `gpt-6-astra` · `medium` — **releídos** de la cabecera del `_stdout.log` |
| Velocidad | `service_tier="default"` — **afirmada** desde el lanzador conservado (`C:\t\codicert-f3-r3b-1715-lanzador\_lanzar.ps1`) |
| Objeto | dos copias `git archive` (`r2/` 1.412 ficheros, `head/` 1.413), dentro del workdir, sin `.git`; cotejadas contra el commit por `sha256` en LF |
| `sha256` del informe | `bd46f2204108a2f678c3fc9af86a07f5daa10f904e8bc94ed84414368ae1767d` |
| Veredicto | **NO-SHIP** |

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:y3ii -->
Higiene inicial conforme: solo estaban `MANDATO.md`, `r2/`, `head/` y `_stdout.log`; no había entradas ajenas que excluir.

# R3 — Remediación de la R2 de F3 Codicert

**El cambio a imagen cierra la copia de las estructuras originales ensayadas en R2, pero la comprobación final no cumple el perfil que declara.** Acepta contenido residual de revisiones anteriores, objetos de generación no cero, estructuras auxiliares no enumeradas y páginas que no dibujan su imagen. También acepta un aportable sin texto. Una mención del título partida por un salto de línea vuelve a retirar el requerimiento. Estos resultados impiden dar por cerrada la remediación.

Objeto declarado: `r2/` = `3ae4cbe19db58414535c478d86dc24005de72e99`; `head/` = `6d950b1a61ed6e3d2b790b8d106e287800ed3066`. Son archivos sin `.git`: no verifico genealogía. El censo normalizado a LF encuentra **14 ficheros distintos**, recogidos en `diff.txt`; lo reproduce `auditar_objeto.py`. Leí los informes R1/R2 y su adjudicación (§12/§13). Los bloques literales tienen los hashes canónicos esperados: R1 `c20d75e915f1783840831d66d6c143b26e2f0d621aa7a33c3231e37de24d1253`; R2 `7fdb90acae94ccea32e33a5c718776b1e15aa8becafb170af1fc713ce638f827`.

No hubo red, humo, documentos de terceros ni cambios en el producto. La ejecución usa `scratch/`, copia de `head/`; las pruebas nuevas y el mutante están fuera de esa copia, en este directorio. El mutante solo sustituye una función en memoria. La entrega dentro de este directorio cumple el mandato específico y sigue estando fuera de los repositorios revisados `r2/` y `head/`.

## Evidencia y reproducción

| Ejecución | Resultado | Registro |
|---|---|---|
| Siete módulos pedidos, venv, semilla 777 | 242 pasados, 1 omitido | `tests-777.log` |
| Los mismos, venv, semilla 31337 | 242 pasados, 1 omitido | `tests-31337.log` |
| Test lento `OCR_REAL`, OCRmyPDF 17.11 | 1 pasado, 41 deseleccionados | `ocr-real-17.11.log` |
| El mismo, OCRmyPDF 17.4.1 | 1 pasado, 41 deseleccionados | `ocr-real-17.4.1.log` |
| Sondas R3, primera versión corregida, venv/777 | 32 pasadas | `conformidad-verificada-777.log` |
| Esas 32, Python de sistema/31337 | 32 pasadas | `conformidad-sistema-31337.log` |
| Sondas finales R3, venv/31337 | 34 pasadas | `conformidad-final-31337.log` |
| Mutante que guarda las imágenes pero no las dibuja, siete módulos, venv/777 | **242 pasados, 1 omitido: sobrevive** | `control-mutante-dibujo.log` |

La versión desplegada ensayada usa pypdf **6.12.2**, y el contraste de sistema, **6.10.1**. No instalé paquetes. `TEMP` y `TMP` se dirigieron a `_temp/`, dentro de este directorio, también para OCRmyPDF/Tesseract. Se desactivaron bytecode y caché de pytest. Los temporales de pytest son hermanos de `scratch/`, no parte de `head/`.

Para repetir todas las sondas finales desde el directorio del mandato:

```powershell
$py = 'C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TEMP = "$PWD\_temp"
$env:TMP = $env:TEMP
$env:PATH = 'C:\Program Files\Tesseract-OCR;' + $env:PATH
& $py -m pytest conformidad_r3.py -q -p no:cacheprovider --randomly-seed=31337 --basetemp=_bt-repeticion -o addopts=
```

Cada reproducción de hallazgo indica un selector que se puede añadir con `-k`. **Las pruebas de aceptación afirman el defecto observado: pasar significa reproducirlo**, no acreditar conformidad. Los controles de rechazo usan `pytest.raises`. Los PDF y algunas imágenes renderizadas quedan en `evidencias/`; todos son sintéticos. El marcador es `MARCA-CONDICIONES-PRUEBA`.

Los registros iniciales conservan dos errores del instrumento, ya corregidos: se buscaba el marcador de `/Info` en bytes sin decodificar los escapes de pypdf; y se intentaba modificar directamente un stream ReportLab con dos filtros que `set_data` no admite. Se corrigieron las sondas, no el producto. Las 34 finales pasan. Las dos añadidas al final son la segunda capa no invocada y la comparación de programación dinámica con enumeración exhaustiva; no atribuyo esas dos al contraste de sistema de 32 casos.

## 1. Dictamen de cada remedio de la R2

Los H de esta tabla son los de **R2**. La numeración de hallazgos R3 se reinicia en el apartado 2.

| R2 | Dictamen | Prueba y frontera |
|---|---|---|
| H-01, copia de recursos y relectura incompleta | **Remediación: incompleta** | El generador cambia realmente de frontera: deja de copiar estructura original y los siete casos de `test_R2_H01_lo_que_la_pagina_conservada_NO_dibuja_no_viaja` pasan; también catálogo, formularios anidados, imagen en línea, enlaces y widgets. Sin embargo, la relectura del fichero admite las salidas de R3 H-01/H-02/H-03/H-04. La parte constructiva es real; la garantía final de perfil completo no lo es. |
| H-02, dos bloques FICHEROS en una página | **Remediación: real** | `test_R2_H02_dos_bloques_en_la_MISMA_pagina_del_acta_paran` pasa. La comprensión cuenta ocurrencias por página, no páginas con alguna ocurrencia. Cierra la multiplicidad intrapágina y entre páginas del formato literal reconocido. No autentica criptográficamente el acta ni promete reconocer cualquier título gráfico. |
| H-03, mención confundida con título | **Remediación: incompleta** | Pasan los tres tests R2_H03: una mención en la misma línea ya no inicia retirada y provoca parada si se conserva. Pero `conformidad_mencion_partida_retira_requerimiento` retira 3, 4 y 5 de nuevo: el inicio de línea de extracción no acredita que sea título. R3 H-05. |
| H-04, volatilidad del CRM | **Remediación: real** | Los cuatro tests R2_H04 de orquestación pasan: caída posterior, nuevo aviso con histórico silencioso, histórico que avisaba y cambio entre avisos. `destinatario` sale de la identidad del artefacto; las diferencias se comunican por separado. La regla implementada coincide con la adjudicada, con los límites explicados en §3. |
| H-05, páginas cortas no comparadas | **Remediación: real** | Los tests de sustitución de texto corto, copia idéntica y original vacío/copia con texto pasan. Ahora compara el texto normalizado corto; para páginas sin texto exige otra sin texto y avisa de la limitación. La sonda `control_pagina_corta_ruido_para` confirma el coste: una separación de palabras distinta para. No se acredita identidad visual de escaneos. |
| H-06, coincidencia íntegra que calla composición | **Remediación: real** | `test_R2_H06_un_destinatario_que_se_lee_como_UNA_parte_o_como_VARIAS_avisa` pasa. Se evalúa la composición aun cuando el nombre entero coincide y se emite el aviso ambiguo. Cierra el orden de decisión, no solo esos nombres. |
| H-07, recursión exponencial | **Remediación: real** | Pasa el test de 18/200 segmentos. La fuente llena cada posición una vez y consulta sufijos ya resueltos. `control_cobertura_dp_contra_enumeracion` contrasta 750 combinaciones pequeñas contra una referencia exhaustiva. No hay recursión de subproblemas repetidos. |

Ninguno es cosmético. «Incompleto» no niega que las reproducciones originales hayan sido atendidas; distingue eso del cierre de su frontera.

## 2. La propiedad nueva, a fondo

### H-01 — El inventario no cubre el fichero físico ni todas las generaciones

- **Severidad: alta. Coste del remedio: estructural.** La comprobación puede aprobar un PDF que conserve contenido de la página retirada fuera de la versión lógica actual de sus páginas.
- **Dónde:** `head/core/certificado_aportable.py:793-848`, especialmente `851-863` (`_sin_sueltos`); identidad de objetos solo por número en `617-641`.
- **Afirmación contradicha:** docstring de `verificar_aportable`, «se relee el aportable ENTERO —el fichero, no sus páginas visibles—»; adjudicación §13, «ningún objeto del fichero suelto»; spec rev. 14, líneas 913-915, «nada suelto en el fichero».
- **Reproducción:** `-k 'historial_incremental or generacion_no_cero or stream_tipado_suelto'`.
- **Remedio:** fijar un perfil de serialización además del grafo lógico: prohibir revisiones incrementales/`Prev` y generaciones no soportadas, o inventariarlas todas explícitamente; no descartar errores de resolución como si fueran necesariamente entradas libres. Validar realmente los contenedores xref/ObjStm y sus datos, no admitirlos por su etiqueta. Una alternativa es reconstruir una salida nueva y estrictamente acotada a partir de componentes validados, sin conservar bytes del archivo de OCR, y verificar esa salida final.

La sonda incremental añade un `/Info` con el marcador y una tercera revisión con `/Info` limpio. El archivo contiene **tres `startxref`** y cadenas `/Prev`; pypdf devuelve la metadata actual limpia, pero los bytes de la revisión anterior siguen dentro. El verificador acepta. Es una actualización sintética válida, no una mera cadena después de EOF.

La segunda sonda añade un objeto **de generación 1** con entrada xref y tamaño correctos. Se recupera mediante `IndirectObject(num, 1, lector)`. `_sin_sueltos` llama `get_object(num)`, que busca la generación cero; el error se silencia y se acepta el archivo. Además, los conjuntos de admitidos no distinguen generaciones.

Las otras dos salidas añaden streams sueltos etiquetados `/ObjStm` y `/XRef`, con el marcador en sus datos. Se aceptan por la excepción de la línea 862, aunque no sean contenedores necesarios y conformes de la serialización. Son deliberadamente estructuras fuera de perfil: prueban la ausencia de validación de esa excepción. Por separado, `control_objstm_xref_comprimidos_validos` produce con pikepdf un PDF real con objetos comprimidos y xref stream y confirma que pasa. No propongo prohibir los contenedores legítimos que usa OCRmyPDF; propongo distinguirlos de cualquier stream que diga tener ese tipo.

### H-02 — La lista blanca admite subgrafos, cadenas y streams que nunca enumera

- **Severidad: alta. Coste del remedio: estructural.** Puede sobrevivir contenido de la página retirada en datos auxiliares no dibujados, mientras la relectura declara conforme el resultado.
- **Dónde:** `head/core/certificado_aportable.py:617-632`, `675-702`, `760-773`, `830-842`; operadores admitidos en `604-607`.
- **Afirmación contradicha:** líneas 589-591, «lo único que puede llevar dentro» y «lo que no está aquí, para»; adjudicación §13, «catálogo, árbol y metadatos mínimos» y «como mucho una capa de texto invisible».
- **Reproducción:** `-k 'estructura_no_enumerada or segunda_capa_no_dibujada'`.
- **Remedio:** validar tipos, claves, valores y dependencias en cada nivel, con límites explícitos para fuentes, descriptores, programas de fuente, mapas Unicode y metadata. Preferir metadata propia regenerada y fuentes controladas para reconstruir una capa de texto acotada. Validar la gramática y operandos del contenido, incluida metadata de contenido marcado; no confundir operadores permitidos con todos sus operandos permitidos. Exigir el número previsto de formularios y su uso efectivo.

Las nueve variantes aceptadas contienen el marcador en `/Info /Subject`, XMP, una clave auxiliar de una fuente Type1, `/FontDescriptor /FontFile2`, una dependencia del stream `/Contents`, un stream dentro de `/ProcSet`, `/ActualText` de un `BDC`, un comentario del stream de texto y un subgrafo auxiliar cíclico de fuente. Para Info se comprueba la cadena decodificada; para las demás, la presencia de los bytes del marcador además de la aceptación.

El ejemplo de `FontFile2` contiene deliberadamente datos que no son un programa de fuente válido: precisamente debe ser rechazado por un perfil completo. No sostengo que Tesseract emita espontáneamente ese programa. El recorrido solo excluye Type3, `/CharProcs` y `/Resources` en la fuente y sus descendientes inmediatos; luego `_admitir` admite **todo** lo que cuelgue de ellos sin validar semántica. Un ciclo indirecto termina por el conjunto de visitados, pero se **admite**, no se rechaza por perfil.

XMP e Info vuelven a usar una lista negativa: solo se busca el rótulo. El contenido de una página retirada sin ese rótulo, como su marcador o un fragmento, pasa. Tampoco se enumeran claves de Info ni un esquema XMP mínimo. Los comentarios se eliminan al analizar operaciones, pero permanecen físicamente en el PDF; `BDC` admite diccionarios de propiedades no comprobados. No se afirma aquí que pypdf extraiga `/ActualText`: se acredita que el fichero lo contiene.

`segunda_capa_no_dibujada` añade un **segundo Form**, modo 3 y fuente permitida, con el marcador. No se invoca y no aparece en el texto extraído. Aun así pasa: `_recorrer_pagina` itera cualquier número de formularios y `_lo_que_lee_el_ocr` solo ve los invocados. La frase «como mucho una capa» carece de un límite equivalente en código.

### H-03 — Una imagen correcta en recursos no acredita que la página la dibuje correctamente

- **Severidad: media. Coste del remedio: acotado.** Se puede entregar una página en blanco, desplazada, reflejada o con dibujo adicional conservando todas las huellas de imagen esperadas; se pierde o altera prueba visible.
- **Dónde:** `head/core/certificado_aportable.py:741-760` y `655-659`; generación en `451-459`; cobertura en `head/tests/test_certificado_aportable.py:601-615`.
- **Afirmación contradicha:** `_recorrer_pagina`, «su contenido solo la dibuja (y a la capa de texto)»; test citado, «cada página del aportable es la IMAGEN de la que se conserva».
- **Reproducción:** `-k dibujo_distinto`. Cuatro salidas conservan imagen y capa de texto, pero eliminan `/Im0 Do`, trasladan el dibujo fuera de la página, lo reflejan o lo dibujan otra vez a otra escala. Todas pasan. Se renderizan con PDFium y se exige diferencia de píxeles frente al aportable limpio. `evidencias/dibujo_sin_imagen.png` es blanco y fue inspeccionado visualmente.
- **Remedio:** comprobar la secuencia de dibujo efectiva, cantidad de invocaciones y matrices acumuladas frente a caja/imagen esperadas; o construir ese contenido directamente después de extraer de forma acotada el OCR. Añadir comparación del **render final** y controles de transformaciones, no solo de la imagen almacenada.

El verificador permite cualquier secuencia de `q Q cm Do`; solo comprueba que el nombre de `Do` exista. No exige dibujar la imagen, dibujarla una vez ni mantener escala/posición/orientación. Una imagen almacenada byte a byte correcta puede no contribuir a un solo píxel de la página.

La cobertura se midió con `control_mutante_dibujo.py`: envuelve `_rasterizar` y elimina únicamente `/Im0 Do`, dejando el recurso imagen intacto. **Los siete módulos rápidos siguen con 242 pasados y 1 omitido**. Esto refuta la completitud de esos controles, no la ejecución histórica de las 75 mutaciones. El test lento de OCR no se incluyó en esa corrida mutante; no afirmo que también lo supere.

### H-04 — La relectura admite ausencia de OCR y texto no acreditado por la imagen

- **Severidad: media. Coste del remedio: acotado para exigir capa; estructural para acreditar su procedencia.** El resultado puede carecer de texto buscable o llevar texto añadido/ajeno sin que la comprobación lo detecte.
- **Dónde:** `head/core/certificado_aportable.py:570-586`, `733-750`, `878-907`; doble de orquestación en `head/tests/test_expedicion_aportable.py:34-45`.
- **Afirmación contradicha:** `aportable_de`, «Sin capa de texto no hay aportable»; spec líneas 911-912, «Sin OCR no hay aportable»; plan §13, «lo que el OCR lee no puede […] parecerse más […] a su vecina […] que a la suya», como garantía independiente de índices.
- **Reproducción:** `-k 'capa_no_acreditada or vecina_no_proxima'`. El puerto identidad `lambda raster: raster` devuelve un PDF sin capa y se acepta; una capa formada únicamente por el marcador también pasa; añadir el marcador al texto correcto de una página pasa. Otra sonda muestra que la preferencia por una página distante no se compara, usando textos de control explícitos en `Recorte.normal`.
- **Remedio:** comprobar la existencia y uso de la capa en páginas que deberían producir texto, con una política explícita para blancos y escaneos ilegibles. Separar esa comprobación de la calidad/procedencia del reconocimiento. Para errores de índices, comparar con todas las candidatas relevantes y la representación visual; para procedencia, no anunciar que una similitud textual la demuestra. Acotar la salida del OCR y hacer explícita la confianza que se deposita en él.

El modo 3 solo prueba invisibilidad de los operadores de mostrar texto, no que el texto se haya reconocido en los píxeles. El rótulo se comprueba antes del mínimo y por tanto también se rechaza en capas cortas si está escrito exactamente de forma reconocible. Pero si el texto leído **o el original** tienen menos de 40 caracteres se omite toda comparación de similitud. No hay mínimo de calidad; basta ganar a retiradas y vecinas inmediatas. No se comparan otras conservadas. Una adición puede dejar ganando al texto propio.

El doble `OcrContado` documenta expresamente que devuelve el raster sin texto, y los escenarios ordinarios de orquestación lo dan por válido. No es solo una entrada hipotética que nadie haya usado en tests.

### Lo que dibuja el render y lo que ven las comprobaciones previas

`_rasterizar` crea un escritor nuevo, renderiza a 200 ppp con anotaciones y formularios interactivos desactivados, convierte a RGB y codifica JPEG. No copia catálogo, recursos, metadata ni streams originales. Los tests de R2 y la revisión del código sostienen esta mejora de frontera. La imagen es una representación con pérdida: no preserva vectores ni todo detalle a resolución arbitraria. Las mediciones de legibilidad de los reales son históricas, no verificadas aquí.

La clasificación y la reproducción se basan en `extract_text`, no en lo que finalmente dibuja PDFium. `control_render_y_extraccion_no_equivalen` ejercita una capa opcional apagada, transparencia cero, texto fuera de la caja y texto en modo 3: pypdf extrae el marcador en los cuatro, pero el raster resulta blanco. Pueden provocar clasificaciones o paradas por texto no visible. No prueban que ese texto no dibujado se copie por el raster; de hecho, desaparece de sus píxeles.

La dirección contraria también existe: imágenes, contornos de glifos y gráficos pueden dibujar contenido sin texto extraíble. **Se ejecutó con el adaptador real** `conformidad_escaneo_contenido_retirado_y_doble_ocr`: una página conservada escaneada reproduce un fragmento de la retirada, con el marcador y una frase de pago; otra página completa lleva el rótulo y se retira. El original de la conservada no tiene texto; el OCR real lee el fragmento, y la salida se acepta. La capa del doble `ocr_fiel` sobre esa misma imagen queda vacía. La evidencia textual está en `evidencias/escaneo-ocr.txt`.

Este caso **no contradice por sí solo** la propiedad más estrecha «lo que ninguna página conservada dibuja no está»: el fragmento sí se dibuja en una conservada. Sí demuestra que esa propiedad no equivale a «el documento no contiene contenido de condiciones». El aviso de ocho palabras analiza el texto original y no cubre este escaneo. En orquestación, una página sin texto recibe el aviso de comprobación visual por cuenta, pero sigue siendo entregable. Si el OCR lee el rótulo se detendrá; si no lo lee, la clasificación gráfica no tiene una garantía general. Las capas opcionales/transparencias se aplanan según el estado que PDFium renderiza, no según todas las apariencias posibles de otros lectores.

### Inventario del perfil, por clase de estructura

| Clase | Decisión efectiva y prueba |
|---|---|
| Actualizaciones incrementales, varias xref, `/Prev` | **Admitidas sin control específico.** H-01 conserva una revisión anterior con marcador; la API de lectura solo ofrece la versión actual al recorrido ordinario. |
| Generación distinta de cero | **No inventariada correctamente.** H-01 recupera un objeto 1 que el bucle de generación 0 ignora. Los visitados son solo `idnum`. |
| `/ObjStm` y xref comprimido | **Admitidos.** Control válido generado por pikepdf y OCR reales pasan. También pasan streams sueltos meramente etiquetados así: la excepción no comprueba su conformidad. |
| Atributos heredables en `/Pages` | **Rechazados en el árbol ordinario recorrido.** Control propio de `/Resources` y test de suite pasan. `_recorrer_nodos` solo permite Type/Kids/Count/Parent. No acredita todos los árboles malformados o rutas alternativas. |
| Referencias cíclicas | **Se toleran en subgrafos admitidos.** La sonda de fuente con referencia a sí misma termina y pasa. `_admitir` evita repetir objetos, no verifica un perfil del ciclo. No se ensayó un árbol de páginas cíclico. |
| Fuentes y dependencias | Type3/CharProcs/Resources inmediatos se rechazan, con test. **El resto se admite recursivamente**, incluidos campos y streams auxiliares no enumerados: H-02. |
| Streams de fuente | **Sin validación del programa ni de sus datos auxiliares.** H-02 admite el `FontFile2` fuera de perfil. No se afirma cobertura de todos los formatos tipográficos. |
| XMP | **Admitido salvo coincidencia textual del rótulo.** El esquema y las dependencias no están restringidos; el marcador sin rótulo pasa. El test de suite con rótulo para. |
| `/Info` | **Admitido salvo coincidencia del rótulo en valores inmediatos convertidos a cadena.** No hay lista de claves/valores; Subject con marcador pasa. El histórico tampoco se inspecciona. |
| Contenido y formularios OCR | Operadores gráficos no listados y texto visible se rechazan; **comentarios, operandos BDC, varios formularios y dependencias arbitrarias** pueden pasar. H-02/H-03/H-04. |

No son fronteras cerradas por el mero hecho de que un objeto «cuelgue» de otro admitido. La alcanzabilidad es una propiedad distinta de la conformidad del contenido.

### Capa de texto: errores de índices y falsas paradas

Los tests existentes detectan la copia de las condiciones, el rótulo y la sustitución por una vecina sobre su corpus, incluso deformando el reconocimiento del rótulo. Son controles útiles. No garantizan cualquier error de índices: texto corto se omite, otras conservadas no se comparan y los empates con vecinas se admiten. El empate con una retirada, en cambio, para.

`conformidad_ocr_empate_falso_para` reproduce un falso rechazo: dos páginas de plantilla difieren solo en una letra y el OCR no reconoce esa letra. El texto leído empata con ambas, y se informa «se parece más» aun siendo empate. Es una parada conservadora, no entrega de contenido indebido. La formulación «No hay umbral que calibrar: basta con que la suya gane» depende de separabilidad del corpus; las mediciones de dos certificados no prueban separabilidad universal. No propongo relajar el rechazo de empates sin otro criterio.

### Adaptador `_ocr_aportable`

Las opciones son coherentes con conservar el raster: `language=['spa']`, `output_type='pdf'`, `optimize=0`, sin deskew, rotación ni limpieza, y `fast_web_view=1e9`. Este último es un umbral práctico inalcanzable para estos documentos, no una validación de formato. El test lento supera 1 MB, confirma ausencia de `/Linearized` y pasa en **17.11 y 17.4.1** con Tesseract local. No encontré una incompatibilidad entre esas dos versiones en ese documento sintético.

Se restaura el objeto `sys.stderr` en `finally`, incluso al recibir un código no cero o una excepción; el test del código de error pasa. `aportable_de` convierte errores del puerto en `AportableError` y no entrega. La lectura del archivo de salida está dentro del `try/finally`. No hay reparación de páginas que el OCR no haya reconocido: H-04 muestra la falta de control de capa.

La compatibilidad con **cualquier otra versión** no está demostrada. Se permiten operadores adicionales, pero se espera que OCRmyPDF siga produciendo texto en Forms y conserve el diccionario/bytes JPEG. Una versión que escriba texto directamente en `/Contents` o cambie representación de imagen puede parar por perfil aunque visualmente sea válida. `requirements.txt:45` admite `ocrmypdf>=16.0`, sin acotar a las dos versiones probadas. Esto es una dependencia de formato que necesita matriz de compatibilidad y actualización controlada; no atribuyo un fallo concreto a una versión no ejecutada.

## 3. Regresiones de la remediación

### H-05 — Inicio de línea sigue confundiendo una mención partida con un título

- **Severidad: media. Coste del remedio: acotado.** Se retira el requerimiento y la OVC de un refundido aunque el título solo se mencione en prosa, perdiendo prueba.
- **Dónde:** `head/core/certificado_aportable.py:200-204`, `220-230`, `258-266`, `535-552`.
- **Afirmación contradicha:** docstring de `abre_condiciones`, «la mención no se retira en silencio»; adjudicación §13/H-03, «una mención en prosa no las abre».
- **Reproducción:** `-k mencion_partida`. Se añade al requerimiento `El anexo se titula\nCONFIDENCIAL - CONDICIONES y se adjunta para su examen.`. Son dos líneas reales del PDF sintético. `paginas_de_condiciones` devuelve las tres páginas del refundido; se retiran **3, 4 y 5**, y la salida final pasa la relectura.
- **Remedio:** no usar únicamente el inicio de una línea extraída como evidencia de título. Delimitar el bloque de título y su contexto, conservando tolerancia a títulos partidos; ante ambigüedad, parar para revisión en vez de iniciar retirada. Incorporar menciones con ajuste de línea y títulos con prefijos de extracción al corpus.

La red posterior no ayuda: la página ya está clasificada como retirada y no entra en el bucle de conservadas. El aviso de arrastre puede nombrar la OVC, pero no corrige la falsa clasificación de la página inicial. El test R2_H03 únicamente cubre una mención que permanece en una línea. Una extracción que anteponga membrete al título en la misma línea puede producir el caso inverso: no reconocer apertura y parar. Esa parada no debe confundirse con una retirada correcta.

Los demás cambios examinados:

- **Texto corto:** `Recibo 40 EUR` frente a `Recibo 40EUR` para, probado. La normalización tolera caja, acentos, ligaduras y espacios repetidos, pero no una palabra pegada. Es el endurecimiento declarado de H-05, con potenciales falsos rechazos; no lo presento como un remedio cosmético ni como razón para volver a omitir páginas cortas.
- **Destinatario volátil:** `_CLAVES_VOLATILES` excluye generado/destinatario; las huellas, páginas y avisos del artefacto siguen comparándose. Si hoy no se comprobó, no invalida el histórico. Si hoy avisa y antes no, para. Si antes había cualquier aviso, no para y comunica el cambio. Esto incluye un histórico de CRM caído frente a un aviso actual concreto: conserva el aviso histórico, no actualiza el manifiesto. Es la política adjudicada, no identidad histórica de destinatarios comprobada contra el prestador. No encontré un silencio nuevo en las transiciones cubiertas.
- **Manifiesto huérfano:** ahora para incluso si correspondería semánticamente. Es una regresión de recuperación **expresa y probada**, motivada por OCR no determinista. No se pisa el archivo. Un aportable sin manifiesto se relee y permite reponerlo sin OCR. Los tests de ambos estados pasan.
- **Idempotencia:** se vuelve a renderizar y se exige igualdad de diccionario/bytes JPEG; no se repite OCR. Un cambio de PDFium, Pillow, parámetros o versión capaz de cambiar esos bytes puede hacer parar una salida antes válida. El plan lo declara; evita sobrescritura pero no garantiza reutilización entre versiones del render. No probé una actualización de render distinta entre dos corridas.
- **Aviso ambiguo y coste:** las dos lecturas se evalúan antes de decidir. La programación dinámica cierra la repetición exponencial; el coste aún depende de longitud, número de nombres y coste de `startswith`, sin límite explícito de entrada. No es una explosión exponencial por sufijos repetidos. El test existente cuenta llamadas recursivas, no todas las comparaciones internas del algoritmo iterativo.

## 4. Los tests nuevos: qué acreditan y qué dejan fuera

La cifra **75/75** es una afirmación histórica de la adjudicación. El arnés, los cambios exactos y sus registros no forman parte del objeto; no puedo certificar que cada mutante compilase, corriera solo su test y muriera por su causa. No la declaro falsa. Las dos semillas y el OCR real sí se han ejecutado aquí.

`ocr_fiel` mejora sobre un doble basado en los índices esperados: casa miniaturas por píxeles, comprueba distancia y separación, y por ello puede detectar intercambios de páginas visualmente diferenciadas. Pero **identifica una imagen y luego copia `extract_text` del original**, no reconoce el contenido de la imagen. De ello resultan tres límites medidos o directamente ejercitados:

1. En un escaneo, el OCR real lee el fragmento y el doble devuelve vacío: la sonda real del §2 lo demuestra. En el sentido inverso, el texto invisible/fuera de caja/opcional no dibujado puede existir en la extracción original aunque no en los píxeles.
2. La correspondencia usa las imágenes embebidas extraídas por `imagenes`, no el render del PDF final. El mutante que no las dibuja conserva todas esas imágenes y pasa los **242 tests rápidos**.
3. Usa texto original prácticamente perfecto y una anatomía de Forms/Helvetica sencilla. Puede ocultar errores reales de reconocimiento y formato, o rechazar páginas visualmente casi iguales por falta de separación del doble aunque un OCR real pudiera leerlas. El control de empate de §2 modela un rechazo plausible por ruido que el doble habitual no genera.

La bajada a **72 ppp** solo afecta a los tests rápidos de orquestación; el módulo puro y el lento trabajan a 200. Es razonable para el cableado y la idempotencia, pero esos tests no acreditan legibilidad, tamaño, memoria, calidad OCR ni cambios de formato dependientes de tamaño a 200 ppp. El test lento de más de 1 MB atiende el defecto de linealización concreto, y lo he ejecutado. No sustituye un corpus de imágenes escaneadas, texto pequeño, páginas similares o distintas salidas de OCR.

Propiedades sin control discriminante en la suite entregada, demostradas por las sondas: rechazo de historial incremental y generaciones no cero; conformidad de contenedores tipados sueltos; validación de subgrafos de fuentes y metadata; límite/uso de capas; presencia de texto; transformación de dibujo final; menciones partidas por ajuste de línea. Las pruebas de ramas actuales son útiles, pero no implican que la lista de ramas o el propio perfil sean completos.

## 5. Todo lo nuevo, en fresco

El diff se examinó además de las reproducciones de R2. Los hallazgos nuevos son los cinco anteriores: inventario físico, cierre recursivo del perfil, dibujo final, capa de texto y clasificación del título. H-03 incluye una carencia de cobertura nueva medida con mutante independiente. No duplico esa misma causa como un sexto hallazgo.

No encontré otro defecto confirmado que justifique una numeración adicional en el cableado del puerto OCR, el mensaje de la CLI, la restauración de stderr o el tratamiento adjudicado del destinatario. Las dependencias PDF/OCR ya existen en `requirements.txt`; no hay una nueva dependencia completamente ausente. Sí persiste la necesidad de compatibilidad por versión explicada arriba.

El rechazo de estructuras malformadas no está convertido universalmente a `AportableError`: varias operaciones posteriores a `_lector` pueden lanzar excepciones de librería. No se ejecutó una sonda de caída de lote por esa causa y por eso **no** se presenta como hallazgo probado. Tampoco se confunde pérdida JPEG prevista con un defecto visual demostrado a 200 ppp sobre los certificados reales, que no están disponibles.

## Lo que intenté refutar y NO pude

- La eliminación por raster de las siete estructuras originales de R2: pasan todos sus controles de regresión y no se copia su grafo al escritor nuevo.
- La ausencia del widget/sello y la advertencia por otras anotaciones: tests verdes; el render se solicita sin anotaciones.
- El rechazo de Type3, texto visible, operadores gráficos no admitidos, anotaciones, cambios de imagen, caja y giro, recursos de página extra y objetos sueltos ordinarios de generación cero: controles del ámbito y controles propios pasan.
- El rechazo ordinario de `/Resources` heredable y la aceptación de objetos comprimidos legítimos: ambos ejercitados, sin extrapolar a cualquier grafo.
- La unicidad intrapágina de FICHEROS, la comparación de texto corto y el aviso de escaneos no comprobados por texto.
- Las transiciones del destinatario expresamente adjudicadas, la no sobrescritura de artefactos y la relectura sin OCR de los ya existentes.
- La compatibilidad del test lento sintético con OCRmyPDF 17.11 y 17.4.1; ausencia de linealización sobre más de 1 MB y restauración de stderr.
- La corrección de la recurrencia de `_cubre` en las entradas pequeñas enumeradas y su terminación en el control de 200 segmentos.

## SIN VERIFICAR

- Certificados reales, las cifras históricas de distancia/similitud, crédito, CRM, HTTP, firma criptográfica y humo. No fueron entregados y la red está prohibida. Los resultados aquí no los confirman ni los refutan.
- Las 75 mutaciones históricas exactas y la suite completa del repositorio. Se ejecutaron los siete módulos pedidos, el lento en dos versiones, 34 sondas finales y un mutante adicional.
- Todas las versiones permitidas por `ocrmypdf>=16.0`, plataformas, idiomas y cambios de PDFium/Pillow. Solo se contrastaron las dos instalaciones indicadas; no se instaló ni actualizó nada.
- Un corpus completo de fuentes, codificaciones, XML, árboles de páginas cíclicos, sintaxis PDF dañada, generaciones y revisiones arbitrarias. Las clases pedidas tienen dictamen en §2 y pruebas concretas; los controles no son una demostración formal de todos sus miembros.
- Cambios reales de render entre corridas, OCR a 200 páginas, agotamiento de recursos, concurrencia multiproceso, carreras externas y cortes de energía/proceso. No hubo monitor general de escrituras del sistema operativo; el confinamiento se basa en comandos, rutas, fixtures y variables temporales.
- Genealogía de commits: los objetos carecen de `.git`; la identidad de lo revisado se custodia con los hashes de todos sus ficheros.

El encargo no se abandonó por esfuerzo: se han contestado sus cinco puntos. Las coberturas ausentes quedan delimitadas y no se dan por refutadas. Las aceptaciones fuera de perfil y el mutante superviviente bastan para el veredicto sin inferir defectos en documentos reales no recibidos.

## Evidencia de no mutación y entrega

`hashes-apertura.json` y `hashes-cierre.json` inventarían los SHA-256 de **todos los ficheros** de `r2/` y `head/`, sobre bytes originales, sin normalizar CRLF: **1.412 en `r2/`, 1.413 en `head/`, 2.825 en total; coinciden íntegramente, sin diferencias**. `evidencia-cierre.json` registra la comparación, las cuentas y las versiones. Los dos módulos de producto de `scratch/` también coinciden byte a byte con `head/`; el mutante no los escribe.

El informe se entrega en UTF-8 sin BOM, LF y un único salto final. El digest canónico del fichero terminado se comunica en el mensaje final.

NO-SHIP
<!-- informe-literal:fin:y3ii -->

## 2. Evidencia verificada por mí contra la fuente

**El objeto es el commit.** Los tres ficheros de F3 de la copia `git archive` de `6d950b1` con que
reproduje las sondas coinciden, en LF, con `git show 6d950b1:<fichero>`: `core/certificado_aportable.py`
(`e552d01f…`), `core/expedicion_certificada.py` (`7cd57461…`) y `tests/_certificado_sintetico.py`
(`1b195366…`).

**Las 34 sondas del revisor reproducen sobre esa copia limpia: 34 de 34** (`pytest` del venv,
`pypdf` 6.12.2, Tesseract `5.4.0.20240606`; «pasar» es reproducir, como en su informe). El fichero
es el suyo (`conformidad_r3.py`, `sha256` `5789cb64…`) con **una sola línea cambiada**, la de
`sys.path`, que apunta a la copia; log `sondas_6d950b1.log` (`8b739abb…`), en el scratchpad de la
sesión.

**Dónde está cada defecto en `6d950b1`**, leído en la fuente y no en el diff:

| # | Dónde | Qué hace |
|---|---|---|
| H-01 | `_sin_sueltos` (l. 851) | recorre `range(1, /Size)` con `get_object(num)` —solo generación 0— y un `except: continue`; deja pasar cualquier stream que diga `/XRef` u `/ObjStm`; y no mira más allá de la última revisión |
| H-02 | `_admitir` (l. 617), `_capa_de_texto` (l. 662) | admite todo lo que cuelga de algo admitido; de las fuentes solo excluye Type3, `/CharProcs` y `/Resources`; `/Info` y XMP solo se miran por el rótulo; la página puede llevar cualquier número de formularios |
| H-03 | `_recorrer_pagina` (l. 705) | exige que los operadores sean `q Q cm Do` y que el `Do` nombre algo que exista, no que la imagen se dibuje, una vez y a página completa |
| H-04 | `aportable_de` (l. 570), `_lo_que_lee_el_ocr` (l. 878) | acepta cualquier PDF del puerto; se salta la comparación si el texto leído o el original tienen menos de 40 caracteres; compara solo con retiradas y vecinas |
| H-05 | `_RE_TITULO` (l. 198) | exige solo que la frase abra una línea |

**El dictamen de los siete remedios de la R2 coincide con el mío**: H-02, H-04, H-05, H-06 y H-07,
reales; H-01 y H-03, incompletos, y por las razones que da —la parte constructiva de H-01 es real y
la garantía del perfil no; la mención partida de H-03 abre una línea—.

**Las sondas contra el remedio.** Corridas **literales**, 32 de las 34 fallan, y 30 por la API:
`aportable_de` devuelve ahora un `Aportable` y el recorte ya no lleva `imagen`. Un fallo por API no
prueba nada, así que las corrí también **adaptadas solo en la API** (`adaptar_sondas.py`, ocho
sustituciones exactas; `sha256` del resultado `077ac063…`, log `cb6f922d…`): no cambia lo que cada
sonda fabrica ni lo que afirma, y dos controles casan el mensaje de la recomposición en vez del de
una rama de la lista blanca que ya no existe. De las 25 que reproducían un defecto:

- **13 las para ya el remedio**, cada una con su mensaje: `/Info`, XMP, la dependencia del
  contenido y los dos streams sueltos («no es, byte a byte»); los cuatro dibujos («no tiene la
  forma»); la imagen sin capa («no devolvió líneas»); la capa hecha de marca y la página lejana
  («no se parece»); la mención partida («menciona el rótulo»).
- **El falso rechazo por empate ya no ocurre** («DID NOT RAISE»: el resultado buscado).
- **9 no se pueden fabricar tal cual**, porque atacan estructura que la forma canónica no tiene
  —la capa `/OCR` de OCRmyPDF (seis), el `/Info` (dos) y un `/ProcSet` al que añadir (una)—. Sus
  equivalentes sobre la forma nueva están en la suite
  (`test_R3_toda_salida_fuera_de_la_forma_canonica_PARA`) y paran.
- **1 sigue pasando, y está declarado**: la marca añadida al texto bueno de una página. La
  relectura acredita parecido y ausencia del rótulo, no la procedencia de cada palabra (§14, H-04).
- **El escaneo pasa por diseño, y ahora con su aviso**: «la página 2 del certificado muestra en su
  imagen 6 frase(s) de las condiciones que su texto no lleva…».

De los nueve controles se mantienen ocho; el noveno —un PDF válido de pikepdf con `/ObjStm` y xref
comprimido— **ya no se admite, a propósito**: solo vale la forma que compone el motor.

**Mutantes del remedio: 76 de 76 muertos, cada uno por su test** (`mutantes_f3_r3.py`, `8da35207…`;
salida `b265ab04…`), con los dos módulos restaurados byte a byte y comprobados por `sha256`. Entre
ellos, el del revisor —la página que guarda su imagen y no la dibuja—, que en la R2 sobrevivía a
los 242 tests rápidos: ahora lo mata dibujar el fichero.

**Lo que el revisor declaró sin verificar**, contrastado donde se pudo: los certificados reales, sin
red, con el remedio (§14, M-16); las 75 mutaciones de la R2 no se vuelven a ejecutar —el arnés nuevo
las sustituye—; y la compatibilidad con otras versiones de OCRmyPDF deja de aplicar, porque OCRmyPDF
sale del camino del aportable.
