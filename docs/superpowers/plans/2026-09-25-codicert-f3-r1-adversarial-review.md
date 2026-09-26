---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-25-codicert-f3.md
objeto_rev: "1"
commit: a87e2d9
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: 62o6
sha256_informe: c20d75e915f1783840831d66d6c143b26e2f0d621aa7a33c3231e37de24d1253
adjudicado_en: docs/superpowers/plans/2026-09-25-codicert-f3.md §12
---

# Acta — R1 adversarial sobre el DIFF de F3 del envío certificado por Codicert

Objeto: el **diff** de `claude/feesdefender-codicert-connection-32083b` contra `origin/main`
(`9880165`), en el commit `a87e2d9` — 13 ficheros, +4.154 / −14.

**Una ronda, por lectura de la tabla de `CLAUDE.md`**: F3 no decide quién escribe sobre qué copia
ni destruye datos de cliente —crea dos ficheros nuevos junto al íntegro y no pisa ninguno—.
**Modelo `gpt-6-astra`·`medium`**, la fila de «escritura sobre datos de cliente… idempotencia», y
la frontera que lo justificó es **silenciosa**: un aportable con la página de condiciones dentro
*parece* correcto y su defecto solo aparece cuando la otra parte lo lee en el juzgado.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.3` (binario `80f78947ad880e6e`) |
| Modelo y esfuerzo | `gpt-6-astra` · `medium` — **releídos** de la cabecera del `_stdout.log` |
| Velocidad | `service_tier="default"` — **afirmada** desde el lanzador conservado (`C:\t\codicert-f3-r1-1225-lanzador\_lanzar.ps1`), que es su única prueba; no consta en el log |
| Objeto | dos copias `git archive` (`base/` 1.404 ficheros, `head/` 1.411), dentro del workdir, sin `.git` |
| `sha256` del objeto | **idéntico al abrir y al cerrar**, en los 2.815 ficheros, según los manifiestos del revisor |
| `sha256` del informe | `c20d75e915f1783840831d66d6c143b26e2f0d621aa7a33c3231e37de24d1253` |
| Veredicto | **NO-SHIP** |

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:62o6 -->
Higiene inicial conforme: solo estaban `MANDATO.md`, `base/`, `head/` y `_stdout.log`; no había entradas ajenas.

# R1 adversarial — diff F3 Codicert

Objeto declarado: base `98801655f0a4cdc5477c7182def1ee12476858fe`; head `a87e2d99ce6eb610e8fed1f0af2a9f4e16dd1be4`. Son archivos sin genealogía Git comprobable. El censo por contenido normalizado a LF confirma los 13 ficheros indicados (`diff-censo.json`). Se leyeron primero M-1 a M-10. No se cuestionan las mediciones reales: las sondas prueban entradas sintéticas adicionales, no afirman que los certificados medidos tuvieran estos defectos.

**Resultado: la garantía central no es completa.** Hay dos vías reproducidas para conservar condiciones: una página referenciada desde una anotación PDF, fuera del árbol ordinario de páginas, y otro documento cuyo rótulo se extrae en dos líneas. La segunda llega a `PRODUCIDO`, con manifiesto y sin avisos, en ambos canales. Además hay defectos de manifiestos, parser, aviso de fuga y sobre conjunto. Claude debe adjudicar contra fuente y sondas.

Todo se ejecutó dentro de este directorio, sobre `scratch/`, copia de `head/`. No hubo red, humo de producción, expedientes reales, commits ni modificaciones de `base/` o `head/`. Las sondas son controles positivos de una auditoría de completitud.

## Evidencia y reproducción común

Python de sistema: 3.14.4; pytest 9.1.1; pypdf **6.10.1**; reportlab 5.0.0. El plan cita pypdf 6.12: no se verificó esa versión ni se instalaron dependencias.

| Ejecución | Resultado | Evidencia |
|---|---|---|
| Seis módulos pedidos, semilla 777 | 99 passed | `tests-777-final.log` |
| Los mismos, semilla 31337 | 99 passed | `tests-31337-final.log` |
| Ocho sondas iniciales, 777 | 8 passed, reproduciendo defectos | `sondas-final.log` |
| Once sondas y controles, 31337 | 11 passed | `sondas-final2.log` |
| Mutante de relectura, seis módulos, 777 | 99 passed: sobrevive | `mutante-relectura.log` |

Los primeros intentos también se conservaron: `tests-777.log` y `tests-31337.log` fallaron creando temporales con `WinError 5` al usar el directorio de trabajo del ejecutor. Cambiar de directorio desde la raíz autorizada resolvió esa limitación. Los reintentos `tests-*-reintento.log` alcanzaron los tests, pero el mutex rechaza un registro bajo el repo, que era donde quedaba `_bt*`. La ejecución final usa `../_bt777` y `../_bt31337`: rutas relativas, hermanas de `scratch/` y dentro del directorio autorizado. No se desactivó el mutex ni se modificó código para conseguir el verde. `-o addopts=` solo evita el segundo `-q` de la configuración y permite conservar el resumen.

Desde el directorio del mandato, reproducción de las sondas:

```powershell
$py = 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location scratch
& $py -m pytest tests/test_r1_sondas.py -q -s -p no:cacheprovider --randomly-seed=31337 --basetemp=../_bt-repro-r1 -o addopts=
Pop-Location
```

Los nombres de test de cada hallazgo permiten seleccionar una sonda con `-k`. Son aserciones del comportamiento defectuoso observado: que pasen significa que el defecto se reprodujo, no que el producto sea correcto. Los controles identificados como tales sí exigen una parada segura.

## 1. Propiedad central: ausencia de condiciones

### H-01 — La página retirada sigue dentro del PDF a través de un enlace

- **Severidad:** alta. **Coste:** estructural, si se mantiene la garantía sobre el contenido completo del PDF.
- **Dónde:** `head/core/certificado_aportable.py:267-299`, especialmente `add_page` en 296; relectura en 302-325.
- **Reproducción:** `test_sonda_destino_link_conserva_objeto_retirado`. Sobre el sintético normal se añade un enlace `/Link` desde la página de requerimiento a la página de condiciones mediante `/Dest`. El recorte elimina esa página de `reader.pages`, pero conserva la anotación y clona el objeto de destino. La sonda recupera su texto completo desde `/Annots[0]/Dest[0]` y comprueba que contiene el rótulo. `_verificar` acepta el PDF. Se guarda `aportable-con-objeto.pdf` bajo el `tmp_path` de esa sonda.
- **Afirmación contradicha:** docstring de `_verificar`, «exactamente las páginas conservadas, sin rastro de condiciones»; objetivo del plan, «sin producir jamás uno que las contenga».
- **Remedio:** delimitar y validar el grafo PDF permitido, incluyendo anotaciones, acciones y referencias a páginas retiradas; impedir que la copia arrastre objetos excluidos y verificar el resultado completo. Una contención inmediata más acotada sería parar ante anotaciones distintas de la firma medida hasta tener soporte seguro, en vez de copiar silenciosamente enlaces. Añadir este control positivo. No basta con contar páginas ni buscar texto en `reader.pages`.

No depende de que M-3 o M-4 sean falsas: el texto visible y la reproducción normal siguen siendo idénticos. La presencia de enlaces no fue medida; la reproducción se acredita con pypdf 6.10.1, no con 6.12.

### H-02 — Un segundo documento con rótulo partido se conserva íntegro y sin aviso

- **Severidad:** alta. **Coste:** acotado.
- **Dónde:** `head/core/certificado_aportable.py:141-144`, 183-189 y 463-474; `head/core/expedicion_certificada.py:2660-2667`.
- **Reproducción:** `test_sonda_rotulo_partido_de_otro_documento`. Se envían el refundido habitual y `OTRAS CONDICIONES.pdf`, cuya extracción empieza por `CONFIDENCIAL -\nCONDICIONES` y ofrece una quita del setenta por ciento. Todos los adjuntos tienen sus huellas correctas; la reproducción es exacta y el burofax concatena los mismos documentos. Ambos resultados son `PRODUCIDO`, conservan esa segunda oferta y llevan cero avisos.
- **Afirmación contradicha:** plan, «Retirar de más, nunca de menos» y «sin producir jamás uno que las contenga».
- **Remedio:** reconocer el rótulo específico aunque la extracción separe sus componentes en líneas o altere el espaciado junto al guion; ante una variante sospechosa no resoluble, parar. Aplicar el control a todos los documentos y a lo conservado, sin confundir las menciones ordinarias de «condiciones» de M-7. Probar combinaciones de un documento reconocible y otro ambiguo; probar solo la ausencia global no cubre esto.

M-7 demuestra una línea completa en la plantilla medida; no acredita ese formato para cualquier adjunto que el operador pueda suministrar (M-9). Esta sonda amplía ese dominio, no refuta la medición. La ausencia global del rótulo pararía; la presencia en el primer documento evita esa parada.

**Resto del razonamiento:** la extensión desde el primer rótulo hasta el final del mismo documento está implementada correctamente para documentos reconocidos. El mínimo de 40 caracteres se aplica a todas sus páginas, incluidas las arrastradas; un escaneo en ese tramo para. No se impone ese mínimo a un documento omitido por no reconocer su rótulo.

`quick_ratio` es una cota superior y se usa correctamente como prefiltro: solo se acepta tras el `ratio` real cuando la cota alcanza 0,98. El algoritmo no elige una única «mejor» página: retira **todas** las que superan el umbral. No encontré un error aritmético de índices en las tres numeraciones. Con todas las condiciones conocidas y sus copias exactas extraíbles, se retiran todas. Fuera de ese dominio, un parecido aceptado en otra página no prueba que no exista una reproducción distinta bajo el umbral; la segunda red solo para si reconoce el rótulo. La relectura repite esos mismos criterios, no aporta independencia frente a sus puntos ciegos.

Normalización: tolera ligaduras, caja, tildes, espacios repetidos y los cinco guiones enumerados. No tolera separar el rótulo en líneas ni eliminar los espacios alrededor de `-`. La independencia entre casado y rótulo es parcial, no una prueba independiente de ausencia de contenido gráfico u objetos PDF.

## 2. Nunca declarar aportable el íntegro sin retirar nada

No encontré una vía normal que produzca un aportable vacío de retiradas: `recortar` rechaza condiciones vacías (412-416); cada condición debe localizar al menos una página de reproducción (442-453). La orquestación para antes si ningún documento lleva el rótulo (2661-2667). Los tests de ambos niveles pasaron.

H-02 es otra propiedad: **sí retira algo**, pero no todo. La parada global por ausencia de rótulo no garantiza completitud cuando hay varios documentos.

## 3. Procedencia, huellas y premisa M-4

### H-03 — El parser acepta un bloque no autenticado por su ubicación o una lista truncada

- **Severidad:** media. **Coste:** acotado.
- **Dónde:** `head/core/certificado_aportable.py:69-97`, en particular 73 y el retorno de 97; consumidor en `head/core/expedicion_certificada.py:2564-2583`.
- **Reproducción:** `test_sonda_parser_acepta_bloque_fuera_acta` devuelve el nombre y sha256 de un bloque sintético anterior que ni siquiera lleva la marca del acta, ignorando el bloque real posterior. `test_sonda_parser_acepta_lista_incompleta` entrega dos páginas de listado: el parser acepta A al llegar al fin de la primera, sin cierre, y omite B.
- **Afirmación contradicha:** «Los documentos que salieron, bajados de Codicert y verificados contra el acta» (docstring de `documentos_enviados`); «un formato que nadie ha medido, no se adivina» (docstring del parser).
- **Remedio:** acotar la lectura al bloque certificante del acta, exigir unicidad y cierre o manejar expresamente continuaciones entre páginas; rechazar bloques ambiguos y listas incompletas. No anclar `Huella digital` a cualquier aparición anterior de la página.

No se encontró ni se pretende una colisión SHA-256. La comparación criptográfica de cada entrada elegida es correcta. El defecto está **antes**: un hash de 64 caracteres puede pertenecer a una entrada que el parser eligió fuera del bloque autoritativo. Si el puerto devuelve bytes de ese hash, la comparación pasa aunque no se haya acreditado que sea el documento que certifica el bloque correcto. Las sondas no demuestran que el proveedor emita esos formatos; demuestran que se aceptan silenciosamente en vez de parar.

La igualdad de las listas electrónicas es estricta, incluyendo orden, nombre y huella. El control adicional `test_control_listas_electronicas_distintas` confirma que listas distintas paran antes de descargar adjuntos. Se descargan los documentos de la primera electrónica y se verifica cada digest; la igualdad de listas vincula las demás, sujeto a H-03. Las listas usadas proceden de certificados descargados, mientras que el recorte usa los íntegros locales: F3 no compara ambos íntegros ni contrasta sus identificadores de envío, y se apoya en el archivo correcto de F2.

**M-4 está protegida en la construcción de F1, no comprobada completamente por F3.** F1 pasa el mismo `adjuntos` a ambos transportes (`expedicion_certificada.py:1951-1958`). F3 no descarga el fundido del burofax ni valida su huella ni casa todas sus páginas con la concatenación: solo busca las condiciones del correo. `test_sonda_m4_no_se_comprueba_por_resultado` cambia el segundo adjunto del burofax conservando las condiciones conocidas: F3 produce el aportable. No se afirma que la medición M-4 fuese falsa. La garantía depende de que el envío observado provenga de esa construcción y de que el prestador la reproduzca como se midió; no cubre un envío externo o discrepante por el mero hecho de compartir identificador de expedición.

## 4. Escrituras, idempotencia y exclusión

### H-04 — Un manifiesto existente no se valida y uno huérfano se sobrescribe

- **Severidad:** media. **Coste:** acotado.
- **Dónde:** `head/core/expedicion_certificada.py:2734-2748`; sustitución de destino en 2612.
- **Reproducción:** `test_sonda_manifiesto_erroneo_se_acepta` cambia el digest del manifiesto tras una generación correcta: la repetición responde `YA_ESTABA` y deja la huella incorrecta. `test_sonda_manifiesto_huerfano_se_pisa` coloca un manifiesto sin aportable: F3 responde `PRODUCIDO` y lo sustituye silenciosamente.
- **Afirmación contradicha:** spec §7.4, «volver a lanzarlo compara por contenido y ni duplica ni pisa»; requisito del manifiesto con el `sha256` del íntegro.
- **Remedio:** validar semánticamente el manifiesto existente frente al íntegro, recorte, envío y avisos comprobados; conservar el instante original si lo demás coincide. Ante divergencias o un huérfano incompatible, parar sin sobrescribir. Probar los cuatro estados de existencia de la pareja y los conflictos de contenido.

El PDF existente sí se compara byte a byte y uno distinto no se pisa. `_escribir_atomico` escribe temporal en el mismo directorio, hace flush/fsync y publica con `os.replace`; protege cada fichero contra una escritura parcial ordinaria, no constituye una transacción de dos ficheros. Morir entre aportable y manifiesto deja un PDF sin manifiesto: el test existente demuestra que la siguiente ejecución lo repone **si vuelve a obtener los mismos datos y completa todas las comprobaciones previas**. No hay reparación incondicional offline: una caída del transporte o discrepancia posterior puede impedir llegar a la reposición. No califico ese estado recuperable previsto como un defecto adicional. Un corte abrupto también puede dejar un temporal sin publicar; no se probó corte de energía.

La CLI usa la misma clave y `sostener` que cosecha; el cuerpo entra en el mismo candado intraproceso. Matiz preexistente relevante: `_exigir_mutex_de_cosecha` permite continuar si no hay ningún mutex vivo en el proceso (2247-2257). Por tanto, la exigencia entre procesos es efectiva en la CLI, no universal para llamadas directas al core; el propio humo llama directamente. No se ensayó concurrencia real multiproceso. La suite requerida sí ejerció el caso de dos hilos de cosecha y el cableado CLI.

## 5. Manifiesto frente a §7.4

La generación nueva incluye código, canal, identificador personalizado, sha256 del íntegro y aportable, lista del acta, documentos de referencia, páginas en las tres numeraciones, emisor y avisos. No falta un campo general pedido. El significado de `emisor.verificado` es comparación del texto de razón social y cuenta, no validación criptográfica de firma. Con el parámetro público `verificar_plaza=False`, se omite la comparación de cuenta aunque el manifiesto sigue diciendo `verificado: true`; la CLI usa el valor seguro por defecto. En burofax distingue correctamente el hash del fundido listado y los hashes de los documentos del correo, pero no acredita que el primero se haya descargado/verificado (punto 3). H-04 afecta a manifiestos reutilizados.

### H-05 — Falta el aviso de sobre conjunto si un nombre ya contiene « Y »

- **Severidad:** media. **Coste:** acotado.
- **Dónde:** `head/core/expedicion_certificada.py:2587-2599`, consumidor en 2713-2720.
- **Reproducción:** `test_sonda_sobre_con_razon_social_compuesta`: dos partes, `GARCIA Y ASOCIADOS, S.L.` y `ANA LOPEZ`, destinatario conjunto `GARCIA Y ASOCIADOS, S.L. Y ANA LOPEZ`. El manifiesto carece del aviso: el split destruye el primer nombre y solo cuenta una parte.
- **Afirmación contradicha:** spec §7.4, «el aviso del §5 regla 3 cuando el sobre fue conjunto».
- **Remedio:** reconstruir/comparar la composición con nombres completos, preservando sus separadores internos, y avisar de incertidumbre si no se puede resolver; probar el nombre compuesto junto a otro requerido, además del caso unitario ya cubierto.

La comparación usa las partes actuales del CRM, no un censo histórico del envío. Un cambio de nombres o una lista vacía sin excepción puede hacer perder también el aviso; no se presenta como reproducción histórica, que no está disponible.

## 6. Avisos de fuga y de páginas arrastradas

### H-06 — La despedida del primer documento anula el análisis de los siguientes

- **Severidad:** media. **Coste:** acotado.
- **Dónde:** `head/core/certificado_aportable.py:342-358` y 376.
- **Reproducción:** `test_sonda_aviso_olvida_segundo_documento`. Se añade otro documento, con rótulo correcto, que ofrece una quita en una frase de más de ocho palabras; esa misma frase se reproduce en el acta. Se retiran ambos documentos de condiciones, pero el acta conserva la frase y `avisos == ()`.
- **Afirmación contradicha:** spec §7.4 rev. 13, «se buscan sus frases de 8 palabras —tras el rótulo y antes de la despedida— en todo lo que se conserva, acta incluida».
- **Remedio:** delimitar los cuerpos por documento antes de reunir sus frases; el primer «Sin otro particular» no debe cortar documentos posteriores. Añadir una prueba de dos cuerpos distintos con sus respectivas despedidas.

El defecto nace de concatenar todas las palabras y aplicar después un único corte global. El aviso de arrastre sí enumera cada página seleccionada que no lleva rótulo; no pretende demostrar que sea ajena a las condiciones. Sus tests pasaron.

Límites expresos del aviso de fuga: menos de ocho palabras, paráfrasis, imágenes y frases partidas entre páginas conservadas pueden no avisar. Eso no contradice un detector de coincidencias literales de ocho palabras. **Y avisar no detiene la generación**, por diseño explícito del spec: incluso un aviso correcto no sostiene la prohibición absoluta de que quede *contenido* económico. No lo confundo con un fallo de implementación; es una limitación del contrato frente a la formulación absoluta del mandato.

## 7. Qué prueban los tests y qué no

### H-07 — La suite no protege las comprobaciones de contenido de la relectura

- **Severidad:** media. **Coste:** acotado.
- **Dónde:** `head/tests/test_certificado_aportable.py:243-249`, test `test_PARADA_3_se_verifica_el_resultado_no_la_aritmetica`; control que pretende proteger: `head/core/certificado_aportable.py:315-325`.
- **Reproducción:** desde la raíz, `$env:PYTHONDONTWRITEBYTECODE='1'; & $py mutante-relectura.py`. El script sustituye `_verificar` **solo en memoria** por una función que cuenta páginas. Elimina la comparación de texto, rótulo y similitud del resultado. Los seis módulos originales siguen dando **99 passed**.
- **Afirmación contradicha:** el docstring del test, «Si el PDF producido no es el que tocaba, no se entrega (verificar por resultado)», como afirmación de cobertura. No se afirma que el código actual carezca del control.
- **Remedio:** fabricar una salida con el número correcto de páginas pero una página equivocada; otra con condiciones y otra con rótulo; exigir rechazo por su causa concreta. `test_control_relectura_misma_cuenta_distinto_contenido` demuestra dos de esos controles sobre el código actual.

El test original devuelve el íntegro completo, con una página de más: lo mata el conteo y no exige ninguna comparación de contenido. La declaración de **18 mutantes muertos** no queda refutada como hecho histórico: el arnés y las mutaciones exactas no están en el objeto entregado y no se reconstruyeron las dieciocho. Sí se acredita que esa cifra no implica completitud: este mutante distinto sobrevive.

Los tests existentes cubren retirada normal, extensión, duplicado exacto, umbral con otra expedición, ausencia de condiciones, rótulo literal conservado/acta, widget directo/con padre, determinismo, aviso calibrado, reposición del manifiesto y conflicto de PDF. No había controles positivos de H-01 a H-06. Tampoco una permutación de páginas de igual cantidad que ejerciese las ramas de contenido de `_verificar`.

## 8. Guards y frontera de los tests

El caso nuevo del transporte sustituye `core.codicert.descargar_adjunto` y comprueba bytes devueltos, envío, nombre y entorno sandbox. Junto al censo existente y las dos corridas verdes, aporta evidencia de cableado real del adaptador; no prueba el HTTP del proveedor ni debe hacerlo aquí.

El censo de `test_guard_codicert_sin_red.py` es recursivo por nombre/contenido. Los ficheros nuevos están alcanzados por sus menciones de Codicert o expedición, incluido el helper. Es un guard textual, complementado por la barrera autouse de ejecución. Esa barrera de Codicert se instala al preparar cada test, no antes de la colección; no convierte cualquier import futuro en seguro. Los imports nuevos revisados no hacen llamadas de red. No se ejecutó el humo.

Las escrituras revisadas de tests F3 se hacen en `tmp_path`; la fixture `_registro_y_locks_aislados` dirige también los locks allí. Los módulos puros usan memoria. Los escenarios de CLI inyectan el entorno y la carpeta. Los tests requeridos y las sondas se ejecutaron con temporales internos al directorio autorizado y externos a la copia-repo. No se instaló un monitor general de todas las llamadas de filesystem: la conclusión se basa en lectura, fixtures y ejecución, no en una auditoría del sistema operativo.

## Lo que intenté refutar y NO pude

- El caso normal elimina condiciones y conserva factura: tests de extracción, numeraciones y PDF final en ambas semillas.
- Una condición ausente, demasiado corta o una página conservada con rótulo completo debe parar: controles existentes pasaron, también sobre el acta.
- Dos copias exactas deben salir ambas: test de duplicadas pasó; no hay elección exclusiva de la primera coincidencia.
- Un documento descargado con huella distinta debe parar: test de orquestación pasó. Una huella partida 46+18 se reconstruye; una corta y una línea no reconocida se rechazan.
- Listas electrónicas distintas: la sonda adicional confirmó parada antes de descargar adjuntos.
- Un aportable distinto no debe sobrescribirse y el íntegro no debe tocarse: ambos controles pasaron. Quitar solo el manifiesto permite reponerlo en condiciones estables.
- Firma con widget directo o con padre: los tests confirman retirada del widget y ausencia de `/AcroForm` en esos dos casos, sin acreditar todos los grafos PDF posibles.
- La relectura actual rechaza una salida de igual tamaño pero contenido equivocado, y una salida con condiciones: controles adicionales ejecutados. Lo que falla es su cobertura original y su alcance al grafo completo, no estas ramas de código.
- La cifra de deuda y la despedida comunes no deben inundar de avisos el caso medido: tests de calibración pasaron; con umbrales de cinco/seis palabras sí avisan los sintéticos de control.

## SIN VERIFICAR

- Los certificados reales, el humo histórico, crédito, siete plazas, CRM, HTTP y firma criptográfica: excluidos por mandato y sin fuentes locales de esos bytes. No se usó la red.
- pypdf 6.12: la reproducción PDF usa 6.10.1, instalada en el Python indicado. H-01 debe verificarse también con la versión de despliegue; H-02 y los defectos de lógica reproducidos no dependen de inferir falsas las mediciones históricas.
- Las dieciocho mutaciones históricas exactas y la suite completa del repositorio. Se corrieron los seis módulos pedidos y un mutante adicional explícito.
- Caída real de proceso/energía, fsync del directorio, concurrencia multiproceso y alteraciones externas simultáneas de ficheros. La reposición se ejerció mediante ausencia de manifiesto, como hace la suite, no matando un proceso.
- Correspondencia universal entre capa de texto y apariencia rasterizada, escaneos fuera de los tramos reconocidos, todos los tipos de anotación, adjuntos internos y demás grafos PDF. La garantía absoluta requiere acotar esos formatos o verificarlos; el presente ataque al enlace basta para demostrar incompletitud.
- Genealogía de los commits: las copias no contienen `.git`. El objeto leído se fija por los hashes de apertura/cierre, no por una comprobación contra Git remoto.

No se abandonó ningún punto del mandato por esfuerzo; las coberturas ausentes están delimitadas arriba.

## Evidencia de no mutación y entrega

`hashes-apertura.json` y `hashes-cierre.json` contienen SHA-256 de bytes de **todos** los archivos: **1.404 en base y 1.411 en head; coinciden íntegramente**. Los hashes de custodia son de bytes, sin normalizar CRLF; el censo del diff sí normalizó a LF. `evidencia-cierre.json` registra el resultado y versiones. Las nuevas sondas viven exclusivamente en `scratch/tests/test_r1_sondas.py`; el mutante vive en `mutante-relectura.py` y actúa en memoria.

El informe se entrega en UTF-8 sin BOM, LF y un único salto final. Su digest canónico se comunica en el mensaje final.

NO-SHIP
<!-- informe-literal:fin:62o6 -->

## 2. Evidencia verificada por mí contra la fuente

**Los siete, confirmados; ninguno refutado**, y las dos observaciones laterales del informe (M-4
sin comprobar por resultado, `emisor.verificado` que afirma de más) también. La adjudicación
hallazgo por hallazgo, con su remedio y su commit, está en el **§12 del plan**
(`docs/superpowers/plans/2026-09-25-codicert-f3.md`), que es donde vive la decisión; aquí queda la
voz del revisor.

**H-01 era peor de lo que la sonda del revisor enseñaba, y eso se vio al adjudicarlo contra lo
real, no contra el informe.** En los certificados de producción cada página de la reproducción
dibuja un Form XObject desde un `/Resources` que comparten todas, y los dos aportables del humo
—producidos por este objeto, en el directorio temporal de la sesión— llevaban dentro el formulario
de la página de condiciones, con el rótulo y 1.327 caracteres. Nunca salieron de ese directorio.

**Lo que comprobé de la propia ronda, no de sus hallazgos:**

- El digest se computó **sobre el fichero terminado**: el vigía esperó la terminación del revisor
  (`_ultimo_mensaje.txt` escrito por `-o` y la salida del lanzador), no la aparición de
  `INFORME.md`, y dos lecturas del informe separadas dieron los mismos bytes.
- El digest canónico del bloque literal **coincide con el `sha256` del `INFORME.md` original y con
  el que el revisor declaró en su mensaje final**, por un canal distinto del fichero.
- **Modelo y esfuerzo releídos**, no declarados: `model: gpt-6-astra` y `reasoning effort: medium`
  en la cabecera del `_stdout.log`. La velocidad (`service_tier="default"`) se **afirma** desde el
  lanzador conservado, que es su única prueba; no aparece aviso de tier no admitido.
- Esta versión de Codex **ignora `sandbox_permissions`** (aviso en el log). No afectó: el objeto
  vivía dentro del workdir.
- El revisor declaró la higiene de su workdir y la no mutación del objeto: 2.815 ficheros con el
  mismo `sha256` al abrir y al cerrar según sus manifiestos.
- El vigía no dio falsos «muerte» esta vez: la señal de fin fue el `_exit.txt` del lanzador más el
  `-o`, no `tasklist` —donde la app de Codex también aparece como `codex.exe`— ni un `ERROR`
  genérico, que la salida de pytest del propio revisor habría disparado.
