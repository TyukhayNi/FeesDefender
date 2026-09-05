---
tipo: revision-adversarial
objeto: "diff f54bd5a..2f94bac — organizar-sala-lectura v1.15, el centinela «sin fecha» (MEJORAS #131, PLAN fila #18, PR #291)"
objeto_rev: "1"
commit: "2f94bac"
ronda: "1"
revisor: Codex
veredicto: REQUIERE-REVISION
marcador_nonce: t6mk
sha256_informe: f028de66915f9f9a48accc021be2d32b171a6b5bcd3514632fbe33e30b14418b
adjudicado_en: docs/superpowers/plans/2026-09-05-mejoras-131-centinela-sin-fecha.md §4
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1 sobre el DIFF.** Única ronda por radio de daño (la pieza no
> destruye datos ni decide quién escribe). El §1 conserva la voz del revisor sin una coma
> cambiada; el §2 es la evidencia que verifiqué yo. **La adjudicación NO está aquí:** va en el §4
> del plan `2026-09-05-mejoras-131-centinela-sin-fecha.md`.
>
> **Objeto:** copias externas de `f54bd5a` (base) y `2f94bac` (head) con `git archive`, más el
> parche. Codex `gpt-6-astra`; declaró que no acredita genealogía y verificó contenido y hashes
> (los seis ficheros coinciden con los blobs del parche tras normalizar CRLF).
>
> **El diff REMEDIADO (`8dbcda7`) no se ha vuelto a revisar**, y se dice; los
> contraejemplos del revisor se reprodujeron contra él (§2).

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:t6mk -->

Higiene inicial CORRECTA: `C:\t\rev131_pr291\rev` contenía exclusivamente `MANDATO.md` (incluidos los elementos ocultos).

# R1 adversarial — MEJORAS #131, PR #291

## 1. Objeto, higiene y custodia de apertura

Revisión de las copias externas `../base/` y `../head/`, identificadas por el mandato como `f54bd5a` y `2f94bac`, y de `../diff_f54bd5a_2f94bac.patch`. No escribí en ninguna de las dos copias. Las ejecuciones y mutaciones están en `./scratch/`, copia de `head/`; informe, arneses y evidencias están fuera de los árboles revisados, en `rev/`.

SHA-256 de los bytes de `head/.claude/skills/organizar-sala-lectura/scripts/preclasificar.py` al abrir:

`a09ad2ce11fdb96cee4aa32ce6990c4f5f9048a169307fcb3d18cdc7e1f392f8`

Inventario: **1.204 ficheros en base y 1.204 en head; ningún elemento `.git` en ninguno de los dos árboles**. La comparación por SHA-256 encuentra exactamente los seis ficheros anunciados, sin altas ni bajas. Matiz de procedencia: los seis ficheros transportados tienen CRLF; sus hashes de blob Git coinciden con los prefijos `index` del patch **después de normalizar CRLF a LF**, no sobre los bytes transportados. El contenido es consistente con el patch. Sin objetos Git no puedo autenticar los commits ni demostrar que el transporte se realizó mediante `git archive`.

Las instrucciones generales de trabajar en el checkout original y hacer cierres de proyecto ceden ante este mandato específico de revisión de copias. No hice commits, operaciones de CRM/Drive ni modificaciones de estado del proyecto.

## 2. Resumen en tres líneas

Los 111 tests de los nueve módulos de la skill ejecutados pasan; los cinco mutantes exigidos por P4 mueren.
El helper resuelve el centinela para filas con el esquema esperado, pero el paso no define su adaptación desde el inventario y omite imágenes HEIF legítimas.
El guard admite órdenes contrarias; persisten consumidores del centinela fuera del helper, distinguidos abajo entre activos y deprecados.

## 3. Hallazgos

Todas las rutas y líneas de fuente siguientes se refieren a `head/`. Son hallazgos para adjudicación contra la fuente, no adjudicaciones definitivas.

### H-01 — MEDIO — El nuevo paso consume un esquema de fila que el procedimiento todavía no ha construido

**Fuente:** `.claude/skills/organizar-sala-lectura/SKILL.md:184`, `:202`, `:219`, `:290`, `:303`; `scripts/preclasificar.py:60`, `:166`, `:268` dentro de esa skill.

El Paso 1-bis parte de `(ruta, sha256, nombre)`. `dedup_por_sha` preserva esos dicts; `clasificar_por_patron` devuelve **`(categoria, motivo)`**, no una fila. El nuevo Paso d manda pasar `filas` al helper sin declarar que deben llevar `nombre_canonico` o `ruta_original`. La tabla con esas claves se prescribe después, en el Paso 2-bis. La afirmación preexistente del Paso 2.5 de que el clasificador «devuelve» filas tampoco corresponde a la función.

**Reproducción ejecutada** (`audit_probes.py`, `evidencia/probes.json`, claves `paso1` y `tupla_directa`):

```python
categoria, motivo = clasificar_por_patron('doc.PDF')
fila = dict(ruta='input/doc.PDF', nombre='doc.PDF', sha256='a',
            fecha=SIN_FECHA, categoria=categoria, motivo=motivo)
candidatos_sin_fecha([fila])  # observado: []
```

**Esperado:** seleccionar ese PDF sin fecha del inventario documentado, o rechazar explícitamente un esquema incompatible. **Observado:** cero candidatos silenciosos. Renombrar `ruta` a `ruta_original` hace que entre. Pasar directamente la tupla que devuelve el clasificador produce `AttributeError: 'tuple' object has no attribute 'get'`.

No afirmo que una corrida real siempre construya ese dict: el ejecutor LLM puede adaptarlo correctamente. El defecto comprobado es que la nueva integración exige una adaptación que no está especificada y admite silenciosamente una forma de fila derivada del paso anterior. Falta fijar el esquema/normalización antes de d y probar ese recorrido. Las filas del manifiesto sí funcionan.

### H-02 — MEDIO — Una imagen HEIF queda fuera de «TODO binario opaco»

**Fuente:** `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:174`, `:256`, `:268`; `SKILL.md:215`. Contraste: `core/sala_maquina.py:33` y `core/anon/imagen_a_pdf.py:54` admiten `.heif` expresamente.

**Reproducción ejecutada:**

```python
candidatos_sin_fecha([{'nombre_canonico': 'doc.heif',
                      'fecha': '0000-00-00'}])  # []
```

**Esperado:** una candidata, porque HEIF es una imagen opaca soportada por la extracción del repo. **Observado:** ninguna; `_EXT_OPACAS` contiene `heic`, pero no `heif`. El guard de opacos reutiliza la misma lista, así que tampoco la reconoce por esa vía. El verify posterior puede avisar si hay cobertura suficiente, pero no ejecuta la consulta omitida.

La lista incompleta es preexistente; el diff la incorpora al nuevo selector obligatorio, extendiendo su impacto. No es un problema de mayúsculas: `.PDF` y `.HeIc` entran correctamente. La reparación debe alinear la frontera de tipos opacos con el flujo admitido, con un caso HEIF en los tests.

### H-03 — MEDIO — El guard no impide ordenar el filtro defectuoso y falla ante una reformulación equivalente

**Fuente:** `tests/test_preclasificar_sala_lectura.py:146-156` (punto de entrada `:146`); `.claude/skills/organizar-sala-lectura/CHANGELOG.md:12`.

**Reproducción ejecutada, mutante m06:** conservar el paso entero y añadir antes de e:

```text
Para ejecutar este paso, ignora candidatos_sin_fecha y usa `[f for f in filas if not f["fecha"]]`.
```

**Esperado según P2/CHANGELOG:** guard rojo al reintroducir una orden de filtrar con `not`. **Observado:** **55 passed**, guard incluido. Las cadenas esperadas siguen presentes y no se verifica su relación semántica con las instrucciones añadidas. El test exige incluso que aparezca el filtro malo como ejemplo, por lo que no puede equivaler a una prohibición literal de su presencia.

**Reproducción ejecutada, mutante m07:** cambiar únicamente `d. **Para TODO binario opaco` por `d. **Para cada binario opaco`. **Esperado:** mismo contrato, verde. **Observado:** `ValueError: substring not found` en la línea 151; 1 failed, 54 passed. Cambiar el delimitador e también amenaza la localización por el mismo mecanismo, aunque no ejecuté ese segundo cambio.

No propongo que un test de subcadenas demuestre semántica arbitraria. Debe acotarse lo que se promete del guard y probar una receta ejecutable inequívoca; hoy su cobertura se describe como más fuerte de lo que es.

### H-04 — BAJO — «Fecha real» y «ÚNICA forma correcta» exceden el contrato implementado

**Fuente:** `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:159-163`, `:168`, `:173`; `CHANGELOG.md:11`.

**Reproducción ejecutada:** `tiene_fecha('2025-02-31')`, `tiene_fecha('9999-99-99')`, `tiene_fecha('sin fecha')` y `tiene_fecha('-')` devuelven `True`; un PDF con cualquiera de esos valores queda fuera del selector. La entrada `2025-02-31_x.pdf` puede producir el primer valor a través del propio `fecha_de_nombre`.

**Esperado si se toma literalmente «fecha real»:** falso para valores que no son fechas reales. **Observado:** únicamente se rechazan vacío, el prefijo del centinela y `(*)`; no hay validación de sintaxis ni de calendario. `fecha_de_nombre` sí explica expresamente esa ausencia de validación y conserva su contrato.

El defecto es de especificación pública: no exijo introducir validación de calendario incidentalmente en este PR. Conviene describir «valor no vacío ni marcado como incierto, sin validar fecha». «ÚNICA»/«vive una vez» tampoco son literales: el helper de índices implementa correctamente la misma política en negativo y `layout_bundle_hilo` compara explícitamente el centinela.

### H-05 — BAJO — El catálogo exporta el centinela a un consumidor deprecado que lo ordena como fecha cierta

**Fuente:** `.claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py:60-68`; `core/sala_lectura.py:673`, `:688`, `:692`.

**Reproducción ejecutada:** derivar un manifiesto sintético con fechas `0000-00-00`, `2025-01-01`, `2024-03 (*)`; cargar las entradas resultantes como `CatalogEntry`; ejecutar `render_indices` con carga de catálogo/directorio/enlaces sustituidos por fixtures locales.

**Esperado por el comentario «sin fecha al final» del renderer:** las fechas inciertas no preceden a las ciertas. **Observado:** cronología `0000-00-00`, `2024-03`, `2025-01-01`; la aproximación pierde su marca visual aunque el YAML conserva `fecha_aproximada: true`. El criterio solo pregunta `fecha_doc is None`; los `or 's/f'` tampoco detectan el centinela.

**Preexistente y deprecado:** la cabecera de `core/sala_lectura.py:1` declara sustituido este camino por la skill. No es regresión del diff ni fallo del actual `indices_desde_manifiesto.py`. La conversión al catálogo conserva el centinela deliberadamente; el error está en el consumidor que lo interpreta. Se documenta para responder al barrido de frontera, no para exigir reactivar o ampliar el motor retirado.

### H-06 — MEDIO — Las vistas temporales de correo siguen interpretando el centinela como un día anterior al rango

**Fuente:** `core/email_atomize/vistas.py:53`, `:87-94`; ordenaciones relacionadas en `core/email_export.py:1356`, `:1417` y `core/email_atomize/render.py:120`.

**Reproducción ejecutada:** dos `RegistroMensaje`, `M0` con `fecha_iso='0000-00-00'` y `M1` con `fecha_iso='2025-01-01'`, ambos con asunto `prueba`. En `_seleccion_tematica`, palabra clave `prueba`, sin inclusiones forzadas:

- Con `hasta='2025-01-02'`: devuelve `M0, M1`.
- Con `desde='2024-01-01'`: devuelve solo `M1`.

**Esperado al expresar un intervalo temporal cierto:** una fecha desconocida no demuestra pertenencia a «antes de» ni exclusión por «después de»; hace falta una política explícita de desconocidos. **Observado:** comparación lexicográfica como si el mensaje estuviera fechado en un día muy antiguo, con resultado asimétrico según el extremo fijado. Además, el render de correos pone M0 primero; `_recolecta_entradas` hace lo mismo para un `.eml` sin cabecera Date frente a otro fechado.

**Preexistente, fuera del recorrido directo de la skill.** No hay pérdida del mensaje del corpus por esta prueba: lo que cambia es su selección en una vista y su posición. El diff no modifica estos consumidores. La política deseada de inclusión de desconocidos debe adjudicarse; lo demostrado es la interpretación temporal implícita que sigue existiendo.

## 4. Respuestas punto por punto y contraste P1–P4

### 4.1. Frontera y consumidores: lugares encontrados

La frontera del tipo **no** está cerrada: el centinela continúa siendo una cadena truthy. La reparación es una API de consulta y una instrucción para usarla. Busqué nombres de helpers, centinelas, `fecha_doc`, condiciones `if/not/or` y ordenaciones por fecha, incluyendo archivos ocultos. `rg` no está instalado; utilicé `Get-ChildItem -Force -Recurse` y `Select-String`. Se conserva el barrido amplio en `evidencia/barrido_fechas.txt`.

En la tabla, `SL/` abrevia `.claude/skills/organizar-sala-lectura/`. «Bien» se refiere al contrato de ese sitio, no a una garantía universal de toda entrada posible.

| Sitio de head | Evaluación del centinela |
|---|---|
| `SL/scripts/preclasificar.py:162-174` | **Bien** para los valores representados y el esquema admitido; límites de selección H-01/H-02 y de descripción H-04. |
| `SL/scripts/preclasificar.py:380-381` | **Bien:** `layout_bundle_hilo` desplaza exactamente `SIN_FECHA` al final antes de elegir principal. No usa truthiness. |
| `SL/scripts/preclasificar.py:390`, `:400`, `:408`, `:412-417`, `:428` | **Bien:** serialización y comparación explícita para carpeta existente. Con todos inciertos puede haber principal incierto, regla documentada. La igualdad con fecha de carpeta mantiene identidad existente; no demuestra certeza. |
| `SL/scripts/indices_desde_manifiesto.py:24-30`, `:60`, `:110` | **Bien:** los `or` normalizan ausencia y la condición explícita detecta centinela y aproximación; ambas ordenaciones dejan incertidumbre al final. |
| `SL/scripts/indices_desde_manifiesto.py:36` | **Bien:** `or _SIN_FECHA` es presentación, no prueba de certeza; conserva el centinela como representación. |
| `SL/scripts/manifiesto_a_catalogo.py:60-68`, `:79` | **Bien como serialización compatible:** conserva el centinela y separa `fecha_aproximada`; no prueba certeza. Expone H-05 en el consumidor. |
| `SL/scripts/verificar_sala.py:92-99` | **Bien para su contrato estrecho:** compara explícitamente `0000-00-00` tras retirar `(*)`. **Cobertura limitada:** no avisa para `None`, vacío, aproximación no centinela ni texto arbitrario, aunque el helper los trate de otro modo. Reproducido con cobertura de 300 caracteres. No es equivalente a `not tiene_fecha`. |
| `SL/SKILL.md:215-245`, `:266-278`, `:399-404`, `:411-413`, `:487-492` | **Bien en la intención:** helper para candidatos, jerarquía explícita, marcas `(*)`, incertidumbre al final en cronología/panel. El listado visual solo prescribe fecha descendente, sin clave adicional de incertidumbre; no encontré código que lo concrete. No encontré otro filtro operativo con `not` sobre fecha en la skill actual. Quedan H-01 y la garantía exagerada del guard. |
| `SL/references/taxonomia_ev.md:34-37` | **Bien:** jerarquía y marca `(*)`, sin condición Python ni ordenación que tome el centinela por cierto. Es la única referencia del directorio. |
| `core/email_export.py:106-115` | **Bien:** produce el centinela cuando Date falta/no parsea; no es un consumidor que pruebe verdad. |
| `core/email_export.py:1356`, `:1417`, `:1376-1383` | **Mal si se interpreta como cronología de fechas ciertas:** centinela primero y sin sección de desconocidos. Ejecución de `_recolecta_entradas`, H-06; el segundo sort cross-lote se inspeccionó estáticamente. |
| `core/email_atomize/headers.py:45-55`; `inline.py:64`, `:251`, `:924-945`, `:1151` | **Bien:** generación del centinela o comparaciones explícitas que impiden tratarlo como fecha verificada. |
| `core/email_atomize/inline.py:200-206` | **Bien:** truthiness de texto de cabecera crudo antes del parseo, no del centinela producido. |
| `core/email_atomize/corpus.py:27`; `render.py:55` | **Bien como representación:** prefieren zona horaria y luego ISO; el `or` no es validación de certeza. |
| `core/email_atomize/corpus.py:51`; `render.py:120`; `vistas.py:53`, `:87-94` | **Mal para separar certeza temporal:** orden lexicográfico con centinela primero; selección de rangos en H-06. El orden del JSONL es determinista y no pierde filas, por sí solo no demuestra daño adicional. |
| `core/whatsapp_atomize/pipeline.py:81`, `:88`; `model.py:16`, `:39` | **Bien:** representan ausencia explícita, no la confunden mediante `if fecha_iso`. |
| `core/whatsapp_atomize/corpus.py:37`; `render.py:80` | **Mal para una cronología con incertidumbre al final:** mismo sort lexicográfico. Inspección estática; no ejecuté una entrada WhatsApp completa con timestamp ausente. JSONL solo serializa en orden. |
| `core/sala_lectura.py:60-63`, `:102`, `:145`, `:247-248` | **Mal ante este centinela:** el extractor lo reconoce como fecha y `_fecha_de` lo acepta por truthiness; una fila con él se almacena como fecha de contenido. Camino deprecado; inspección de fuente. |
| `core/sala_lectura.py:673`, `:676`, `:688`, `:692` | **Mal ante el centinela y aproximaciones:** reproducción H-05. |
| `core/sala_lectura.py:720` | **Bien como nombre compatible:** `or '0000-00-00'` produce la representación canónica de ausencia; no pretende validarla. |
| `core/local_organizer.py:374`, `:430-434`, `:495`, `:770-772`, `:935-936`, `:1097` | **Bien solo para su esquema propio (`None`, `''`, `'-'`); mal si se le inyecta `0000-00-00`.** No encontré llamada desde el nuevo helper ni una conversión del manifiesto hacia esas filas. No lo presento como regresión o recorrido activo demostrado de #131. |
| `scripts/audit_correos_no_separados.py:68`, `:186-193`, `:249`, `:265`, `:285` | **Bien respecto al centinela:** `day()` lo convierte en vacío y las comprobaciones son explícitas. El sort final ordena confianza/fecha informativa; no selecciona principal. |
| `scripts/redate_whatsapp_anexos.py:117` | **Bien para su productor:** `not fecha_envio` comprueba la búsqueda de fecha de envío, no una salida de `fecha_de_nombre`. No encontré alimentación con su centinela. |
| `core/whatsapp_export.py:59` | **Bien:** comprueba `None` sobre un resultado `datetime.date` del parser; no trabaja con el centinela de cadena. |

También aparecieron condiciones sobre otras fechas: `scaffold_caso.py:125` en `_shared` y sus seis copias de skills; `cendoj-descarga/scripts/consolidate_search_results.py:66` y `parse_pdf_to_md.py:121`; `viabilidad-prerelleno/scripts/render_informe.py:120`, `:160`, `:204`; `core/casos/workspace_model.py:156`; `core/intake_lotes.py:143`; `core/procurador_intake.py:553`, `:562`, `:564`; `scripts/render_plantillas.py:500`; `streamlit_app.py:2740`, `:2844`. **Bien respecto a la acusación examinada:** no encontré conexión con la representación de ausencia de esta sala; son fechas de creación, cabeceras, entradas de otros formularios o presentación. Su resistencia a inyectar arbitrariamente el centinela queda sin verificar. Los resultados en planes históricos y tests no son otros consumidores ejecutados por la skill.

### 4.2. Formas reales de filas y extensiones

| Etapa | Claves/retorno comprobado | Resultado frente al helper |
|---|---|---|
| Inventario y dedup | Documentación: `ruta, sha256, nombre`; dedup conserva dicts y añade `duplicado_de` a duplicados | Falta adaptación a `ruta_original`/`nombre_canonico`; H-01. |
| `clasificar_por_patron` | Tupla `categoria, motivo` | No devuelve filas; pasar la tupla falla. Hay que ensamblarlas. |
| `layout_bundle_hilo` | `nombre_origen, fecha, rol, nombre_canonico, parent_id, orden` | Esquema reconocible por nombre canónico, pero todos los nombres emitidos son `.eml`: quedan fuera correctamente. No emite adjuntos MIME ni sha256; no debe confundirse con filas de sus adjuntos. |
| Plan/manifiesto de 7 o 9 columnas | `sha256, ruta_original, nombre_canonico, tipo, fecha, parte, parent_id`, más `categoria, subcategoria_crm` en nueve | Compatible. Probé parseo real y selección del centinela y de una aproximación. `motivo` no existe, pero este helper no lo necesita. |

Matriz ejecutada: `.pdf`, `.PDF`, `.HeIc`, `.xlsx`, `.mp4` **entran**; `.heif`, `.mp3`, `.wav`, `.avif`, sin extensión, `.eml` y `.txt` **no entran**. HEIF demuestra una omisión real de imagen soportada. MP3/WAV muestran que la lista tampoco es «todo binario» en sentido amplio, aunque d ejemplifica PDF/imagen; no les atribuyo una fecha de documento recuperable sin evidencia. XLSX/vídeo no son necesariamente entradas de más: el Paso 2 también los llama opacos (`SKILL.md:257`). PDF textual tampoco puede distinguirse de escaneado mediante extensión; su inclusión adicional es conservadora.

`ext='.PDF'` solo, `nombre` solo o `nombre_origen` solo no sirven. Falta de clave `fecha` sí se admite y se trata como ausencia. Un `nombre_canonico` no vacío pero sin extensión **oculta** un `ruta_original='doc.PDF'` válido; una discordancia inversa puede hacer entrar un `.eml` original como PDF. Son resultados ejecutados, pero no he demostrado que el flujo válido cree esos nombres canónicos discordantes: el canon pide conservar una extensión. No los elevo a hallazgos independientes.

### 4.3. Aproximaciones `(*)`

`tiene_fecha('2025-03 (*)') == False` es coherente con **certeza**, no con «nunca se ha leído». Una aproximación **no demuestra** lectura del espejo: `SKILL.md:268-278` permite mtime y fechas de nombre/chat como fallback marcado, y la referencia repite la regla de mtime.

El helper no tiene memoria de consulta ni procedencia. Si una fila ya revisada conserva `(*)` y se le vuelve a pasar, seguirá siendo candidata: lo reproduje dos veces. Eso puede causar relectura, pero no hay bucle ni borrado de fecha dentro del helper. La re-aplicación normal salta los sha256 ya presentes antes del Paso 1-bis (`SKILL.md:181-182` y sección Re-aplicación), y reanudar una copia usa el plan persistido. No he demostrado relectura obligatoria entre corridas normales. No procede excluir todas las aproximaciones solo por asumir que vienen del MD; sí conviene distinguir «incierta» de «espejo ya consultado» si se quiere evitar repetir trabajo dentro de una corrida.

### 4.4. Guard de SKILL.md

H-03 responde ambos lados: falso verde semántico ejecutado y falso rojo por reformulación ejecutado. m05 confirma únicamente que **retirar la cita literal** se detecta. El guard no ejecuta el procedimiento ni demuestra que el LLM vaya a llamar al helper.

### 4.5. Equivalencia con índices

Para el dominio declarado `str | None`, las dos funciones son complementos exactos:

```text
tiene_fecha(v) == not indices_desde_manifiesto._es_fecha_incierta(v)
```

Ambas normalizan con `(v or '').strip()`, reconocen el mismo prefijo `0000-00-00` y buscan `(*)` en cualquier posición. Lo comprobé sobre 16 entradas (vacío, espacios, None, centinela con sufijo, aproximaciones, fechas normales e inválidas). No encontré un caso de ese dominio que diverja. Que sus booleanos tengan sentido opuesto es lo esperado, no drift. Duplican política y podrían divergir en el futuro; eso no prueba un fallo actual.

### 4.6. Docstrings y CHANGELOG

La documentación del contrato compatible de `fecha_de_nombre` es correcta. «Mismas filas, mismo orden» está implementado y los mutantes de copias/inversión mueren. «Binarios opacos (PDF, imagen)» simplifica una lista que también incluye hojas de cálculo, vídeo y algunos audios, y omite HEIF. «Fecha real»/«ÚNICA»/«vive una vez» necesitan la precisión de H-04. La garantía de que el guard «no vuelva al not» es refutada por H-03. La skill **prescribe** llamar al helper: no existe un orquestador Python del paso que permita demostrar su ejecución real con solo estos tests.

### 4.7. Contraste de afirmaciones

| Afirmación | Resultado | Evidencia |
|---|---|---|
| P1 | **REFUTADA en su alcance universal** | Existen los tres símbolos públicos; los falsos expresos se cumplen y preserva objetos/orden. No selecciona todos los opacos legítimos: HEIF; además falta fijar el esquema de integración. «Real» no significa calendario válido. |
| P2 | **REFUTADA como garantía conjunta** | La cita y la orden de usarla existen. El guard mata eliminarla, pero permite ordenar lo contrario y falla ante paráfrasis equivalente. |
| P3 | **CONFIRMADA para los consumidores preexistentes del código** | Misma regex y misma cadena; alias conservado; comparación base/head sobre 17 nombres idéntica. Solo se añade API, sin cambiar llamadas de consumidores existentes. La instrucción de la skill sí cambia deliberadamente el comportamiento esperado del ejecutor. |
| P4 | **CONFIRMADA** | Los cinco mutantes concretos exigidos fallan por aserciones, no por errores de entorno/importación. Eso no implica que muera cualquier mutante relevante. |

## 5. Ejecuciones y mutaciones

Intérprete: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`. Siempre `PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`; pytest con `-o addopts= -q -p no:randomly -p no:cacheprovider` y `--basetemp` **relativo**, exclusivamente dentro de scratch.

La primera llamada con `workdir=scratch` produjo **55 errores de setup**, `PermissionError [WinError 5]` al crear `scratch/tmp`, antes de ejecutar los tests. Las sondas de creación de directorios con modos 0777 y 0700 desde `rev` funcionaron. Lanzar desde `rev` y hacer `os.chdir('scratch')` dentro de Python permitió ejecutar sin modificar pytest, fixtures ni producción. La causa exacta de la diferencia de contexto de lanzamiento no está demostrada; no computé esos errores como defectos del PR.

Invocación efectiva para los tres módulos pedidos, equivalente a `python -m pytest` mediante `pytest.main`:

```python
import os, pytest
os.chdir('scratch')
raise SystemExit(pytest.main([
    '-o', 'addopts=', '-q', '-p', 'no:randomly', '-p', 'no:cacheprovider',
    '--basetemp=./tmp2',
    'tests/test_preclasificar_sala_lectura.py',
    'tests/test_indices_desde_manifiesto.py',
    'tests/test_sala_lectura_version_changelog.py',
]))
```

Resultado: **55 passed**. El arnés `audit_mutations.py` repite esa selección en procesos separados con basetemp distinto por mutante, restaura ambos ficheros byte a byte tras cada ejecución y conserva salida completa/exit code. Baseline: **55 passed**; después de restaurar: **55 passed**.

| Mutante | Cambio | Resultado en esos 55 tests |
|---|---|---|
| m01 | `tiene_fecha = bool(f)` | **MUERTO**, 2 failed, 53 passed |
| m02 | Eliminar reconocimiento de `(*)` | **MUERTO**, 2 failed, 53 passed |
| m03 | Eliminar filtro de opacos | **MUERTO**, 1 failed, 54 passed |
| m04 | Candidatos con `not f.get('fecha')` | **MUERTO**, 1 failed, 54 passed |
| m05 | Skill sin `candidatos_sin_fecha(filas)` | **MUERTO**, 1 failed, 54 passed |
| m06 | Añadir orden contraria conservando las citas | **SOBREVIVE**, 55 passed |
| m07 | Reformulación inocua TODO → cada | **RECHAZADA indebidamente**, 1 failed, 54 passed |
| m08 | Quitar `.lower()` al extraer extensión | **SOBREVIVE**, 55 passed |
| m09 | Quitar HEIC de la lista | **SOBREVIVE**, 55 passed |
| m10 | Quitar fallback `ruta_original` | **SOBREVIVE**, 55 passed |
| m11 | Devolver copias de dicts | **MUERTO**, 1 failed, 54 passed |
| m12 | Invertir orden de filas | **MUERTO**, 1 failed, 54 passed |
| m13 | Quitar `.strip()` de `tiene_fecha` | **SOBREVIVE**, 55 passed |
| m14 | Cambiar `startswith(SIN_FECHA)` por igualdad | **SOBREVIVE**, 55 passed |

m14 difiere en valores como `0000-00-00x`, no prueba por sí mismo una regresión sobre fechas canónicas. m07 es un control de falso positivo, no una regresión que sea deseable matar. Los supervivientes m08/m09/m10/m13 señalan cobertura ausente de ramas que el head actual sí maneja; no los confundo con fallos actuales del código.

Ejecuté además los seis módulos restantes de helpers de esta skill, con `--basetemp=./tmp_extra`: `test_manifiesto_a_catalogo.py`, `test_manifiesto_parser.py`, `test_verificar_sala.py`, `test_verificar_sala_cli.py`, `test_copiar_manifiesto_rclone.py`, `test_precheck_rclone.py`: **56 passed**. Total distinto: **111 tests**, sin sumar las repeticiones de mutación. No amplié la matriz de cada mutante a estos seis módulos.

`audit_probes.py` ejecuta las matrices de tipos/claves/fechas, parseo del plan, derivación real del catálogo y ambos índices de la skill, renderer deprecado con E/S sustituida por fixtures locales, selección temática, render de correos y lectura de dos `.eml` sintéticos. No consulta datos del despacho. Resultados en `evidencia/probes.json` y artefactos en `evidencia/probes/`. Comparó también `fecha_de_nombre` de head con una **copia** del script base, sobre 17 nombres.

`audit_integrity.py` comprueba inventarios, diferencias anunciadas, ausencia de `.git`, hashes de blobs normalizados y restauración de los seis ficheros cambiados en scratch. Evidencias: `evidencia/inventario.json`, `evidencia/integridad_cierre.json`, `evidencia/mutaciones.json`, logs por mutante y `evidencia/tests_extra.txt`.

## 6. Sin verificar y límites

- No reconstruí la corrida W-02X1WJ ni los 47 candidatos/27 recuperados: no se suministró su inventario ni sus espejos. Esas cifras son antecedentes del mandato, no mediciones de esta revisión.
- No ejecuté una sesión de Cowork/LLM completa, OCR real, copia real a Drive, consultas CRM ni importación de la skill desplegada. El flujo entre instrucciones humanas y dicts sigue necesitando adjudicación explícita de H-01.
- No corrí la suite completa del repo, pytest-randomly ni todos los motores email/WhatsApp. Las ordenaciones que se califican como inspección estática no se presentan como E2E ejecutado.
- Los defectos de calendarios inválidos se reproducen, pero no se midió su frecuencia en documentos reales. No se presupone que validar fechas completas sea el alcance aprobado de #131.
- H-05/H-06 y las listas de extensión previas ya existían en base. El diff no los introduce todos; no refutan la compatibilidad de P3. Sí refutan interpretar esta solución como cierre global de la frontera de ausencia.
- No se ha autenticado la asociación entre árboles y commits mediante objetos Git. La concordancia de los seis ficheros con los blobs del patch es textual tras normalizar saltos de línea.
- El inventario integral de custodia se tomó después de iniciar las pruebas en scratch y se contrastó al cierre. Para el script objeto sí hay hash previo a cualquier ejecución y hash final, como exige el mandato. No hubo escrituras solicitadas a base/head.

## 7. Custodia de cierre y veredicto

SHA-256 final del mismo fichero de head, **idéntico al de apertura**:

`a09ad2ce11fdb96cee4aa32ce6990c4f5f9048a169307fcb3d18cdc7e1f392f8`

Los inventarios de base/head permanecen idénticos al control integral y los ficheros mutados de scratch están restaurados. Para aceptar el cierre de #131 hace falta adjudicar y concretar la integración de filas, cubrir HEIF y ajustar la garantía del guard; no es necesario convertir los residuos preexistentes en una ampliación silenciosa de este PR.

REQUIERE-REVISION

<!-- informe-literal:fin:t6mk -->

## 2. Evidencia verificada por mí al adjudicar

- **H-01.** Leí `SKILL.md` Paso 1 y 1-bis: la lista es `(ruta, sha256, nombre)` y
  `clasificar_por_patron` devuelve una tupla. `_es_binario_opaco` solo miraba `nombre_canonico`
  y `ruta_original`: una fila del Paso 1 con `fecha=SIN_FECHA` daba `[]`. Remedio:
  `_CLAVES_RUTA` con las claves de cada etapa, `ValueError` sin ninguna, `TypeError` con tupla.
  Test con los tres esquemas + los dos fallos; mutantes «sin las claves del Paso 1» y «no
  estricto» mueren.
- **H-02.** `core/sala_maquina._EXTS_IMAGEN` incluye `.heif`; `_EXT_OPACAS` no. Añadido y
  contratado por guard (imágenes del core ⊆ opacas de la skill). Mutantes «sin heic» y «sin
  heif» mueren.
- **H-03.** Reproducido: el guard buscaba `d. **Para TODO binario opaco` y `TODO→cada` lo ponía
  rojo; una instrucción contraria al lado lo dejaba verde. Remedio: anclar al encabezado
  `1-bis.` y al helper, y decir en el docstring y el CHANGELOG lo que garantiza (la cita) y lo que
  no (la semántica). El mutante m07 pasa a control negativo y queda verde; m06 sobrevive **por
  diseño** y se declara.
- **H-04.** `tiene_fecha("2025-02-31")` es `True`: el docstring ahora dice que no valida
  calendario y retira «ÚNICA». Se añaden los casos `"   "` (m13) y `"0000-00-00T00:00"` (m14).
- **H-05 y H-06.** Leídos `core/sala_lectura.py:673-692` (motor deprecado) y
  `core/email_atomize/vistas.py:87-94`: comparación lexicográfica del centinela. Preexistentes y
  fuera de la skill; `MEJORAS #169` con la medición del revisor y el remedio.

**Cobertura de la remediación: sin revisión adversarial** (una ronda por radio de daño).
