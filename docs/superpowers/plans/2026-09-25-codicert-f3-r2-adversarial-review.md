---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-25-codicert-f3.md
objeto_rev: "2"
commit: 3ae4cbe
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: wgpe
sha256_informe: 7fdb90acae94ccea32e33a5c718776b1e15aa8becafb170af1fc713ce638f827
adjudicado_en: docs/superpowers/plans/2026-09-25-codicert-f3.md §13
---

# Acta — R2 adversarial sobre la REMEDIACIÓN de la R1 de F3 del envío certificado

Objeto: la **remediación** de la R1, `a87e2d9` → `3ae4cbe` — 9 ficheros, +1.191 / −123 —, con el
informe de la R1 y su adjudicación dentro del objeto.

**Segunda ronda, por decisión expresa de Nikolai el 2026-09-25.** La tabla de `CLAUDE.md` da una a
F3; la segunda se pidió sobre la remediación porque su hallazgo alto —el formulario de las
condiciones viajando dentro del aportable— era una fuga silenciosa que mi propia verificación no
había visto, y su remedio toca justo esa frontera. **Mismo modelo que la R1** (`gpt-6-astra`·
`medium`), por la misma fila: la frontera sigue siendo silenciosa.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.3` (binario `80f78947ad880e6e`) |
| Modelo y esfuerzo | `gpt-6-astra` · `medium` — **releídos** de la cabecera del `_stdout.log` |
| Velocidad | `service_tier="default"` — **afirmada** desde el lanzador conservado (`C:\t\codicert-f3-r2-1335-lanzador\_lanzar.ps1`) |
| Objeto | dos copias `git archive` (`r1/` 1.411 ficheros, `head/` 1.412), dentro del workdir, sin `.git` |
| `sha256` del informe | `7fdb90acae94ccea32e33a5c718776b1e15aa8becafb170af1fc713ce638f827` |
| Veredicto | **NO-SHIP** |

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:wgpe -->
Higiene inicial conforme: solo estaban `MANDATO.md`, `r1/`, `head/` y `_stdout.log`; no había entradas ajenas.

# R2 adversarial — remediación de F3 Codicert

**La remediación es sustancial, pero no cierra la garantía sobre el fichero.** Con el código de `head/` sin modificar, las sondas producen aportables que conservan contenido económico en recursos PDF que el recorrido no contempla. La ausencia del rótulo en las páginas extraídas no detecta esas fugas. Este defecto basta para impedir el merge bajo el contrato del mandato.

Objeto declarado: `r1/` = `a87e2d99ce6eb610e8fed1f0af2a9f4e16dd1be4`; `head/` = `3ae4cbe19db58414535c478d86dc24005de72e99`. Archivos sin `.git`: no se verifica genealogía. El censo normalizado a LF confirma nueve ficheros distintos; diff conservado en `diff.txt`. Leí primero el informe R1 y la adjudicación del §12. El bloque literal R1 tiene el digest canónico esperado: `c20d75e915f1783840831d66d6c143b26e2f0d621aa7a33c3231e37de24d1253`.

Todo ataque es una entrada sintética o un control positivo del instrumento. No implica que los certificados reales tengan esas estructuras adicionales. No hubo red, humo, expedientes reales ni escrituras fuera de este directorio. `r1/` y `head/` no se modificaron. La copia de ejecución es `scratch/`; los temporales son hermanos de esa copia. La entrega aquí obedece al mandato específico, frente a la preferencia global de entregar fuera del repositorio revisado.

## Evidencia y reproducción común

Python 3.14.4, pytest 9.1.1, pypdf **6.10.1**, reportlab 5.0.0, en el Python indicado por el mandato. No se instaló ni se verificó pypdf 6.12.2, versión citada por la adjudicación.

| Ejecución | Resultado | Evidencia |
|---|---|---|
| Siete módulos del mandato, semilla 777 | 172 passed | `tests-777.log` |
| Los mismos, semilla 31337 | 172 passed | `tests-31337.log` |
| Sondas finales R2, semilla 777 | 20 passed | `sondas-20.log` |
| Versión anterior de las sondas, 31337 | 19 passed | `sondas-final.log` |
| Mutante sin recursión dentro de formularios, siete módulos, 777 | 172 passed: sobrevive | `mutante-r2.log` |
| Ese mutante contra el control R2 específico | 1 failed, por no rechazar la fuga | `mutante-control.log` |

Los primeros intentos de las sondas (`sondas-777.log`, `sondas-31337.log`) contienen un error de construcción del control de recompresión: el stream comprimido no se registraba en el escritor y después se accedía a un atributo inexistente. Se corrigió la sonda, se añadió una aserción que exige que el formulario esté realmente en la salida defectuosa y se volvió a ejecutar. No se cambió el producto para obtener el resultado.

Desde el directorio del mandato:

```powershell
$py = 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location scratch
& $py -m pytest tests/test_r2_sondas.py -q -s -p no:cacheprovider --randomly-seed=777 --basetemp=../_bt-r2-repro -o addopts=
Pop-Location
```

Para cada hallazgo, añadir `-k <selector>` indicado abajo a esa orden. Los tests llamados `fuga_*` y las sondas de regresión **afirman el defecto observado**: pasar reproduce el defecto, no certifica seguridad. Los `control_*` exigen rechazo o ausencia. Los PDF de evidencia quedan en el `--basetemp` correspondiente. Para repetir la suite base se usa literalmente la orden del §3 del mandato, con cada semilla.

## 1. Dictamen de los remedios de la R1

Las referencias H de esta tabla son las de **R1**; las siguientes secciones reinician la numeración para R2.

| Punto R1 | Dictamen | Evidencia y alcance |
|---|---|---|
| H-01, contenido no visible | **Remediación: incompleta** | Los tests `test_H01_el_aportable_NO_arrastra_el_formulario_de_las_condiciones` y `test_H01_un_enlace_a_la_pagina_retirada_NO_la_mete_dentro` pasan. Cierra los formularios compartidos de primer nivel y las anotaciones medidos. Las seis variantes `fuga_recursos_no_Do`, el array indirecto y la reescritura prueban que no cierra el fichero completo (§2). |
| H-02, rótulo partido | **Remediación: real** | `test_H02_el_rotulo_PARTIDO_o_sin_espacios_se_reconoce` y el segundo documento pasan. Cierra la frontera de espacios y saltos alrededor del guion, no solo la cadena de la sonda. Introduce la retirada por una cita del título, medida en R2 H-03. No demuestra reconocimiento de cualquier representación gráfica del rótulo. |
| H-03, lista autoritativa/completa | **Remediación: incompleta** | Los cuatro tests H03 de `test_certificado_aportable.py` pasan para página ajena, falta de cierre, dos páginas y cabecera anterior. Cuenta páginas con bloques, no bloques: dos en una página siguen aceptándose, R2 H-02. |
| H-04, manifiesto alterado/huérfano | **Remediación: real** | La suite rechaza manifiestos alterados y huérfanos incompatibles sin sobrescribirlos; conserva `generado` para coincidencias. La validación es semántica y amplia. El acoplamiento de avisos volátiles del CRM a esa igualdad causa la regresión R2 H-04. |
| H-05, razón social con «Y» | **Remediación: incompleta** | Pasa `test_H05_sobre_conjunto_con_una_razon_social_que_LLEVA_Y`; el nombre completo deja de romperse y las discrepancias ordinarias avisan. Sin embargo, una coincidencia íntegra silencia una composición alternativa posible, R2 H-06. |
| H-06, despedida del primer documento | **Remediación: real** | `test_H06_la_despedida_del_PRIMER_documento_no_corta_las_frases_del_SEGUNDO` pasa. `_cuerpos` agrupa por documento y corta cada despedida por separado. Cierra la frontera entre documentos identificados por nombres distintos. Sigue siendo aviso literal de ocho palabras, no garantía de ausencia económica. |
| H-07, ramas de relectura sin test | **Remediación: real** | Los tres controles H07 de igual número de páginas exigen las causas de página equivocada, copia y rótulo. La antigua sonda de solo contar páginas ya tiene quién la refute. Esto no cubre las nuevas ramas del grafo: un mutante distinto sobrevive (§4). |
| M-4, comprobación por resultado | **Remediación: incompleta** | Rechaza otro segundo documento largo y páginas de más; exige orden, cuenta y similitud. Omite toda comparación para originales de menos de 40 caracteres, incluso con texto: la sonda R2 H-05 sustituye un recibo por una oferta y pasa. No es una comparación exacta de apariencia ni de bytes del fundido. |
| Emisor: decir qué se comprobó | **Remediación: real** | La suite de orquestación comprueba `razon_social_verificada` y `usuario_verificado`, incluido `verificar_plaza=False`. El manifiesto ya no atribuye verificación de cuenta cuando se omitió. No dice verificar criptográficamente la firma. |

No califico ningún remedio de cosmético: todos cambian comportamiento y tienen controles útiles. «Incompleto» distingue el éxito sobre la sonda original del cierre de su frontera.

## 2. H-01 a fondo: propiedad sobre el fichero

### H-01 — La poda y el verificador omiten contenido de recursos y aceptan streams reescritos

- **Severidad: alta. Coste del remedio: estructural.** Puede entregarse un PDF con el contenido económico recuperable dentro de él, sin rótulo visible ni aviso.
- **Dónde:** `head/core/certificado_aportable.py:352-384` (`_podar`), `387-398` (copia), `401-436` (huellas y recorrido), `451-483` (verificador).
- **Afirmación contradicha:** adjudicación §12, «recursos podados a lo que su contenido invoca» y «relectura del grafo entero»; spec §12.4, «para si queda un solo objeto que solo usaban las páginas retiradas».
- **Reproducción:** selectores `fuga_recursos_no_Do`, `fuga_contents_array_indirecto` y `fuga_stream_reescrito`. Todos pasan sobre `head` sin modificar su código. La reescritura es una salida defectuosa inyectada directamente a ambos verificadores, no una afirmación de que el escritor actual haga esa transformación espontáneamente.
- **Remedio:** definir y hacer cumplir un perfil PDF admitido; rechazar estructuras fuera de él hasta soportarlas. Recorrer operadores y dependencias de todas las clases de recursos soportadas, podar recursivamente sus diccionarios y controlar también metadatos/datos auxiliares. La verificación no puede equiparar ausencia de hashes de streams conocidos con ausencia de contenido. Mantener un original inmutable para la clasificación y controles independientes con salidas defectuosas, incluida reserialización equivalente. Una solución general de PDF requiere más que añadir otra clave a la lista.

El mecanismo es concreto: `_nombres_invocados` solo mira `Do`; `_podar` solo filtra `/XObject` de la página, copia las demás categorías enteras y no poda recursos dentro de formularios. `_flujos_usados` solo conoce `/Contents` y la cadena de `Do` de formularios/imágenes. La salida se enumera más ampliamente, pero se compara contra una lista negra incompleta. Un objeto enumerado sin huella prohibida no se rechaza.

| Vía auditada | Resultado y control positivo |
|---|---|
| `/Pattern` | **Abierta.** Variante `pattern`: patrón de teselas con el stream de condiciones, en recursos compartidos; lo invoca la página retirada, no la conservada. Viaja íntegro al aportable, sin rótulo en sus páginas ni avisos. Ni se poda `scn` ni se inventaría el stream del patrón. |
| `/Shading` | **Abierta.** Variante `shading`: sombreado tipo 1 con función PostScript tipo 4; el contenido retirado está en comentarios válidos de la función. Se conserva ese stream y sus datos económicos. Prueba filtración estructural de datos, no que el sombreado pinte letras. No se recorren `sh` ni `/Function`. |
| Fuentes | **Abierta.** Variante `font`: fuente Type3 con un `/CharProcs` que contiene el dibujo de condiciones, invocada en la retirada. El diccionario `/Font` compartido y sus charprocs pasan completos. Se recuperan los bytes del rótulo de los streams del aportable. No se analiza `Tf`/glifos/charprocs; no afirmo haber ensayado todos los formatos de fuente embebida. |
| `/ExtGState` → `/SMask` → `/G` | **Abierta.** Variante `smask`: máscara de luminosidad cuyo grupo es un Form con las condiciones. La retirada invoca `gs`; el recurso compartido queda en la conservada. El Form confidencial sobrevive sin ser detectado. |
| Imagen → `/SMask` | **Abierta para contenido auxiliar.** Variante `image_smask`: la imagen exterior se usa y se registra, su máscara lleva bytes económicos como muestras de imagen y no se registra. Es un control sintético de recuperabilidad de bytes, no de legibilidad visual de esas muestras. El recorrido de `Do` no incluye las dependencias de la imagen. |
| Formularios anidados | La poda **no es recursiva**. `control_recurso_anidado_exactamente_igual_para` demuestra que un recurso sobrante interior se copia pero el verificador actual para si el stream exclusivo está inventariado e idéntico. `control_recursion_formulario_exclusivo` demuestra la necesidad del recorrido interior; el mutante que lo elimina sobrevive a la suite original. No califico la copia anidada exacta probada como fuga aceptada por el código actual. |
| `/Contents` como array indirecto | **Abierta.** `fuga_contents_array_indirecto`: el contenido retirado se referencia mediante un array indirecto y también queda alcanzable desde recursos conservados. `_flujos_usados` registra el identificador del array, no los streams que contiene; `_huella_flujo` lo reduce al fallback vacío. El stream económico sobrevive. La referencia auxiliar de la sonda es deliberadamente defectuosa: comprueba que el control no la rechaza. |
| Imágenes en línea | `control_inline_image_exclusiva_no_sobrevive` confirma que una `BI…EI` exclusiva dentro del contenido retirado sale con su `/Contents`. No tienen objeto independiente: la cobertura depende del stream contenedor. No he demostrado una fuga autónoma por `BI`; las de patrones y de reescritura muestran por qué esa cobertura no constituye una prueba semántica de cada imagen. |
| `/StructTreeRoot`, `/Names`, `/Outlines` en catálogo | `control_catalogo_y_pagina_se_descartan` coloca marcadores en esas entradas y comprueba su ausencia final. Se crea un catálogo nuevo, no se clona el original. No hay evidencia de una vía abierta por esas entradas de raíz. El control usa diccionarios sintéticos con marcador, no un corpus completo de árboles etiquetados o destinos. |
| `/Metadata`, `/Info` | El mismo control elimina metadata de catálogo/página y `/Subject` del Info original. **Pero metadata dentro de un Form conservado sí sobrevive**: variante `metadata`, XML con el texto completo de condiciones, también asociado a la retirada. No hay saneamiento recursivo ni inspección de cadenas de diccionario. |
| Acciones de documento/página | El control anterior elimina `/OpenAction`, `/AA` del catálogo y `/AA` de página. Las anotaciones se eliminan y los tests R1 verifican el enlace y el widget. No se ha probado una vía autónoma de acción que sobreviva por esas posiciones estándar. |
| Flujos de objetos (`/ObjStm`, xref comprimido) | El verificador delega resolución de objetos a pypdf; el escritor usado crea un PDF nuevo. No ensayé una entrada con objetos comprimidos y xref tipo 2: **sin verificar**, no una vía declarada abierta. Contar `1..Size` y silenciar errores de lectura no es una demostración independiente de todos los objetos/bytes posibles. |
| Recompresión sin cambiar datos decodificados | `control_grafo_detecta_copia_exacta_y_recompresion` introduce realmente el Form exclusivo tanto directo como Flate: ambos se rechazan. La comparación de datos decodificados sí cubre este caso. |
| Stream reescrito con otros bytes decodificados | **Abierta en la verificación.** `fuga_stream_reescrito_escapa_relectura` añade un comentario PDF al Form exclusivo y lo introduce como objeto suelto en una salida limpia. `formularios_con_rotulo` recupera el rótulo del objeto 19. `_verificar` y `_verificar_grafo` aceptan. La semántica de dibujo no cambia, el hash sí. No hay que encontrar una colisión SHA-256. |

Dos límites adicionales de la formulación: se excluyen expresamente las huellas compartidas con páginas conservadas, por lo que no se inspecciona qué fracción de un stream compartido es confidencial; y `_sin_paginas` modifica páginas del lector antes de la supuesta relectura del «ORIGINAL». Estos hechos se observan en fuente, pero no presento una fuga adicional por ellos sin una sonda específica. Tampoco un hash de datos de stream acredita su interpretación: fuentes, recursos y parámetros pueden cambiar el significado sin cambiar esos datos.

## 3. Regresiones de la remediación

### H-03 — Citar el título retira el requerimiento como si fuera condiciones

- **Severidad: media. Coste: acotado.** El aportable pierde prueba que sí conservaba R1; el íntegro permanece custodiado.
- **Dónde:** `head/core/certificado_aportable.py:162-176`, `214-221`, `590-595`.
- **Reproducción:** `-k rotulo_citado`. Añadir al requerimiento «El anexo se titula “CONFIDENCIAL - CONDICIONES”» retira páginas 3, 4 y 5 en vez de solo 5. El aviso solo señala la OVC arrastrada, no que el requerimiento con la cita fue clasificado como condiciones.
- **Afirmación contradicha:** docstring `lleva_rotulo`, «La frase con su guion es tan específica como la línea»; documentación aún vigente de `paginas_de_condiciones`, «primera página que lleva el rótulo como línea entera».
- **Remedio:** separar reconocimiento de título y mera mención. Permitir saltos/espacios en un título, pero parar para revisión ante una mención ambigua en prosa, en lugar de retirarla silenciosamente. Avisar también de la página de inicio dudosa. No volver sin más al detector vulnerable de R1.

La política documentada de «retirar de más» explica la preferencia conservadora; no elimina el daño ni justifica presentar una cita en prosa como un título. No produce fuga, por lo que su severidad no es alta.

### H-04 — Una incidencia del CRM invalida un manifiesto y aportable idénticos

- **Severidad: media. Coste: acotado.** Bloquea repetición/recuperación y solicita apartar un artefacto válido por un cambio operacional ajeno a sus bytes.
- **Dónde:** `head/core/expedicion_certificada.py:2701-2704`, `2746-2756`, `2780-2789`, `2803-2812`.
- **Reproducción:** `-k crm_cambia`. Primera corrida `PRODUCIDO`; segunda con los mismos certificados, adjuntos y PDF pero `partes_de` lanzando una excepción: correo `YA_ESTABA`, burofax `PARADO`, «huellas, páginas o avisos distintos». El manifiesto anterior no se modifica.
- **Afirmación contradicha:** spec §7.4 citado por R1, «volver a lanzarlo compara por contenido y ni duplica ni pisa»; el test existente `test_si_el_CRM_no_responde_se_avisa_en_vez_de_callar` solo protege la primera generación.
- **Remedio:** distinguir la procedencia inmutable del artefacto de observaciones operacionales actuales. Validar y conservar el manifiesto histórico; comunicar aparte la falta actual de comprobación. Definir qué cambios sustantivos de atribución sí requieren revisión, sin hacer del texto variable de una excepción parte de la identidad del PDF.

La conservación ante conflicto es correcta y no se propone sobrescribir el manifiesto. El defecto es diagnosticar como conflicto de artefacto la volatilidad del aviso. Recuperarse el CRM o variar el mensaje de su excepción plantea el mismo acoplamiento por igualdad de todo `avisos`; solo la transición disponible → caído se ejecutó.

### Comprobación de reproducción y atribución

Las páginas en blanco **no provocan por sí solas una falsa parada**: la prueba existente y `m4_adjunto_no_pdf_para_y_pagina_blanca_pasa` pasan. En cambio, omitir una página/documento en la reproducción provoca diferencia de cuenta; es la política de identidad estricta nueva, no un error aritmético demostrado.

Un adjunto no PDF produce `AportableError` al leerlo. En la orquestación la extracción previa de condiciones ya intentaba leer todos los adjuntos como PDF antes de esta remediación: **no atribuyo esa incompatibilidad nueva a `comprobar_reproduccion`**. No se ha medido qué tipos de adjunto omite realmente el prestador. Esa compatibilidad queda sin verificar.

La atribución ahora conserva los nombres completos con «Y» y avisa cuando no logra cubrir el destinatario. Sus límites adicionales se detallan como H-06/H-07 en §5. `GARCÍA S.L.` frente a `GARCIA SL` da incertidumbre: la normalización convierte puntos en espacios, no reúne las letras de la abreviatura. La sonda lo reproduce; es un aviso conservador, no una entrega indebidamente atribuida ni una regresión en la función de normalización, que ya existía.

## 4. Los tests nuevos y los 26 mutantes

Los tests nuevos prueban los ejemplos reparados y ramas útiles, incluidas las tres de `_verificar`, las tres del grafo, los conflictos de manifiesto, rótulos partidos y segundo documento. Los mensajes específicos impiden que otra parada encubra la rama que se pretendía probar. Las dos semillas verdes son evidencia real, no una lectura de nombres de tests.

**No se verificó el hecho histórico «26 de 26, cada uno por su test»**: el arnés no está en el objeto. No lo doy por falso; tampoco lo uso como prueba de completitud.

Construí otro mutante, solo en memoria: quitar la llamada recursiva de `_flujos_usados` al contenido de cada Form, manteniendo el registro del Form exterior. Sobrevive con **172 passed**. Añadí una entrada con el Form de condiciones dentro de otro Form exclusivo y una referencia sobrante desde un Form conservado: el código actual la rechaza; el mutante la acepta. El control nuevo falla precisamente porque no se lanza `AportableError`, no por importación o fixture.

Reproducción:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location scratch
& $py ../mutante-r2.py
& $py ../mutante-r2.py --control
Pop-Location
```

La primera orden termina en 0; la segunda debe terminar en 1 para demostrar que el control mata el mutante. El módulo de producto no se escribe ni se restaura: la sustitución desaparece al acabar el proceso.

Propiedades que los tests entregados no ponen en rojo, demostradas por las sondas: ausencia de contenido en patrones/fuentes/máscaras/metadata de Form; inventario correcto de `/Contents` array indirecto; relectura de un stream semánticamente igual y reescrito; unicidad intrapágina del bloque; cita del rótulo; estabilidad frente al CRM; reproducción de páginas cortas; atribución ambigua y coste de la búsqueda. Un recuento de mutantes muertos no cubre entradas que no existen en sus fixtures.

## 5. Todo lo nuevo, en fresco

### H-02 — La unicidad de FICHEROS se verifica por página, no por bloque

- **Severidad: media. Coste: acotado.** Puede aceptarse una lista equivocada como autoritativa, anterior a la lista que se pretendía leer.
- **Dónde:** `head/core/certificado_aportable.py:79-96`, `99-102`.
- **Reproducción:** `-k parser_dos_bloques`. Una misma cadena de página de acta contiene dos bloques completos, uno con `FALSO.pdf` y otro con `REAL.pdf`. Devuelve solo `FALSO.pdf`. Los bloques se cierran correctamente: no depende de una huella rota.
- **Afirmación contradicha:** docstring de `ficheros_listados_de_textos`, «tiene que ser el único»; adjudicación H-03, «Solo cuenta el bloque de una página del acta, único».
- **Remedio:** contar y delimitar ocurrencias de bloques, no páginas con alguna ocurrencia; rechazar duplicados intrapágina y cierres/cabeceras ambiguos. El cerco textual de «acta» no debe presentarse como autenticación criptográfica.

No demuestra que el proveedor genere tal página ni que toda explotación complete el recorte: la comprobación posterior de reproducción puede parar si cambia el documento. Sí demuestra que el remedio del parser acepta la ambigüedad que dice rechazar.

### H-05 — M-4 no compara páginas que sí tienen texto pero menos de 40 caracteres

- **Severidad: media. Coste: acotado.** Se acepta como reproducción del documento un contenido distinto; la procedencia del aportable queda afirmada con una comprobación incompleta.
- **Dónde:** `head/core/certificado_aportable.py:279-308`, especialmente `301-303`; invocación en `head/core/expedicion_certificada.py:2738`.
- **Reproducción:** `-k m4_acepta_sustitucion`. El segundo adjunto original dice `Recibo 40 EUR`; su página de reproducción se sustituye por una quita del setenta por ciento. La comprobación pasa y `recortar` conserva la quita sin aviso. La cuenta y el resto de páginas son iguales. El código actual no exige que la copia también sea corta o vacía.
- **Afirmación contradicha:** adjudicación de M-4, «página a página, la copia de cada una que tenga texto»; docstring «reproduce EXACTAMENTE los documentos enviados».
- **Remedio:** separar el mínimo de texto necesario para localizar condiciones del criterio de identidad de una página. Comparar también texto corto con una regla apropiada; para páginas sin texto, verificar representación gráfica/contenido soportado o declarar y detener la comprobación insuficiente. No dar por acreditada identidad con la mera cuenta.

Es un hueco de la comprobación nueva, no prueba de que el código anterior fuese más seguro. El caso sin texto ya está expresamente exceptuado en código y test; por eso la sonda usa texto no vacío. Tampoco se ha refutado la medición de igualdad de los certificados reales.

### H-06 — Una coincidencia de nombre íntegro oculta una composición igualmente posible

- **Severidad: media. Coste: acotado.** Puede faltar el aviso de sobre conjunto/incertidumbre que limita lo que se afirma sobre la entrega a cada parte.
- **Dónde:** `head/core/expedicion_certificada.py:2626-2632`.
- **Reproducción:** `-k atribucion_normalizacion`. Destinatario `ANA Y LUIS`, partes con nombres completos `ANA`, `LUIS` y `ANA Y LUIS`. Devuelve `None` por coincidencia íntegra, sin examinar la lectura de dos destinatarios. Es una ambigüedad sintética, no evidencia de este censo en un expediente real.
- **Afirmación contradicha:** docstring de atribución, «no se puede atribuir [...] y eso se dice, en vez de callar como si fuera a una sola persona»; frontera del aviso del spec §5 regla 3.
- **Remedio:** evaluar también la composición cuando existe coincidencia íntegra; si ambas lecturas son posibles, avisar de incertidumbre o contrastar con destinatarios históricos del envío. No inferir una atribución unívoca de un nombre actual ambiguo.

### H-07 — La búsqueda de cobertura repite exponencialmente los mismos sufijos

- **Severidad: baja. Coste: acotado.** Puede ralentizar la preparación completa ante nombres compuestos solapados; no demuestra una fuga.
- **Dónde:** `head/core/expedicion_certificada.py:2594-2608`.
- **Reproducción:** `-k cubre_coste`. Siete nombres que son prefijos compuestos de `ana y ana...`, destinatario de 18 segmentos y un último segmento no cubrible: **250.904 llamadas**. Se cuenta trabajo, no se fija un umbral frágil de milisegundos. Es una entrada adversarial, no una estimación del coste de un censo corriente.
- **Afirmación contradicha:** ninguna promesa cuantitativa publicada; el defecto nuevo es repetir el mismo subproblema en una función usada sin límite de coste durante la preparación.
- **Remedio:** memoizar por posición dentro de una invocación o usar programación dinámica iterativa. Indexar los prefijos si hay muchas partes y limitar el tamaño de entrada. La salida debe ser la misma, incluida la incertidumbre.

Con nombres no solapados no hay evidencia de explosión exponencial: el conjunto grande por sí solo implica más comparaciones, no necesariamente esta ramificación. No convierto esa peor entrada en una afirmación sobre rendimiento de producción.

## Lo que intenté refutar y NO pude

- El ejemplo real modelado de `/Resources` compartidos con `/TPLn Do` ya no arrastra el Form de condiciones: test específico verde. La R1 no era solo un enlace y el remedio sí atiende esa anatomía.
- Los enlaces a páginas retiradas y los widgets se eliminan. El grafo detecta páginas adicionales, anotaciones restantes y streams exclusivos inventariados con datos idénticos, incluso recompresos.
- La recursión actual de formularios sí rechaza el control anidado específico; es su cobertura original lo que falla, no esa llamada del código actual.
- Los rótulos partidos y sin espacios salen; las palabras sueltas habituales del requerimiento/factura no se confunden con ellos.
- El parser rechaza bloques fuera de las páginas de acta, listas sin cierre y dos páginas con bloques, y recompone huellas partidas.
- La reproducción distinta de un segundo documento largo y las diferencias de cuenta paran; una página sin texto no causa por sí sola parada.
- Los manifiestos alterados/incompatibles y los PDF distintos no se pisan. La repetición con datos y avisos estables funciona; el emisor declara por separado las comprobaciones realizadas.
- El aviso del segundo documento y el sobre conjunto con una sociedad que contiene «Y» funcionan.
- Los marcadores de catálogo, Info, metadata/acciones de página que ensayé no sobreviven a la reconstrucción.

## SIN VERIFICAR

- Certificados reales, igualdad píxel a píxel, mediciones de producción, CRM real, HTTP, firma criptográfica y humo: excluidos por mandato. No se usó la red. El análisis no pretende confirmar ni refutar la medición histórica con datos que no se han facilitado.
- pypdf 6.12.2 y otras versiones. Los hallazgos deben adjudicarse también sobre la versión de despliegue; las sondas entregadas lo permiten. Los defectos de parser, regex, manifiesto y atribución son de lógica del código revisado.
- Los 26 mutantes históricos exactos y la suite entera. Se ejecutaron los siete módulos pedidos, las sondas y un mutante independiente con su control discriminante.
- `/ObjStm` con xref comprimido; todas las variantes de fuentes, patrones, espacios de color, filtros, imágenes, estructuras etiquetadas, generaciones de objetos y PDFs malformados. No afirmo que cada estructura no ensayada esté abierta. El inventario del §2 distingue ausencia probada en un control de completitud universal.
- Apariencia rasterizada de las sondas. Las fugas se prueban por recuperación de contenido de los streams y, para el Form reescrito, por dibujarlo aparte mediante el helper y extraer su rótulo. No se ha acreditado equivalencia visual universal entre capa textual y dibujo.
- Compatibilidad real con adjuntos que el prestador no reproduzca, carga operacional típica de muchas partes y censos históricos de nombres. Solo se ensayaron las entradas sintéticas descritas.
- Concurrencia multiproceso, cortes de energía/proceso, carreras externas y auditoría de todas las escrituras mediante monitor del sistema operativo. La conclusión de confinamiento se basa en rutas, fixtures y acciones ejecutadas.
- Genealogía de commits: no hay `.git`. No se consultó el repositorio real.

No abandoné ningún apartado por esfuerzo. La revisión no es una prueba formal de todos los formatos PDF: las coberturas ausentes están delimitadas arriba y no se dan por refutadas. La garantía central ya queda contradicha por controles positivos ejecutados, sin necesitar inferencias sobre las vías pendientes.

## Evidencia de no mutación y entrega

`hashes-apertura.json` y `hashes-cierre.json` contienen SHA-256 de bytes de todos los archivos: **1.411 en `r1/` y 1.412 en `head/`, 2.823 en total; coinciden íntegramente, sin diferencias**. `evidencia-cierre.json` registra esa comparación. Son hashes de custodia de bytes CRLF cuando corresponde; el diff y el digest del informe se normalizan a LF.

Las únicas modificaciones de la copia de ejecución son las sondas en `scratch/tests/test_r2_sondas.py`; el mutante de `mutante-r2.py` actúa en memoria. El informe se entrega en UTF-8 sin BOM, LF y un único salto final. Su SHA-256 canónico figura en el mensaje final.

NO-SHIP
<!-- informe-literal:fin:wgpe -->

## 2. Evidencia verificada por mí contra la fuente

Cada hallazgo se contrastó contra el código de `3ae4cbe`, no contra el informe: las sondas del
revisor (`scratch/tests/test_r2_sondas.py`, en su workdir) se corrieron con el `pypdf` **6.12.2** del
venv —él usó 6.10.1—, y **las 20 reproducen**. La adjudicación, con el remedio de cada uno, está en
el §13 del plan.

| # | Qué dice la fuente | Veredicto |
|---|---|---|
| H-01 | `_nombres_invocados` solo recoge operandos de `Do`; `_podar` filtra el `/XObject` de la página y copia enteras las demás categorías de recursos, sin bajar a los formularios; `_flujos_usados` registra el id de un `/Contents` en array indirecto y no sus streams; `_verificar_grafo` compara lo presente contra huellas de lo prohibido. Las seis `fuga_recursos_no_Do`, `fuga_contents_array_indirecto` y `fuga_stream_reescrito` pasan: el defecto se reproduce | **Confirmado** |
| H-02 | `bloques = [n for n, t in … if n in acta and "FICHEROS ADJUNTOS" in …]`: una página con dos bloques cuenta uno | **Confirmado** |
| H-03 | `paginas_de_condiciones` abría en la primera página con `lleva_rotulo`, que casa la frase en cualquier sitio: la cita del requerimiento lo retira | **Confirmado** |
| H-04 | `_manifiesto_corresponde` compara todo salvo `generado`, y `avisos` lleva el texto de la excepción del CRM: su caída cambia la identidad | **Confirmado** |
| H-05 | `comprobar_reproduccion` hace `continue` con menos de `MIN_CARACTERES`, tenga la página texto o no | **Confirmado** |
| H-06 | `_atribucion_burofax` devuelve `None` ante la coincidencia íntegra antes de mirar si el nombre se lee también como varias partes | **Confirmado** |
| H-07 | `_cubre` es recursivo y sin memoria: el mismo sufijo se recalcula por cada manera de llegar a él | **Confirmado** |

**Del dictamen sobre los remedios de la R1**, los cuatro «incompletos» son justamente H-01, H-02,
H-06 y H-05 de esta ronda; los cinco «reales» (H-02, H-04, H-06 y H-07 de la R1, y el emisor) no se
discuten. **Las observaciones sin hallazgo** —«GARCÍA S.L.» contra «GARCIA SL» avisa de
incertidumbre; un adjunto no PDF para al leerlo— se comparten: la primera es un aviso conservador y
se deja; la segunda queda **sin verificar**, porque no se ha medido qué adjuntos reproduce el
prestador.
