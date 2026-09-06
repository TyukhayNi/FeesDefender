---
estado: historico
dueno: Nikolai Tyukhay
fecha: 2026-09-06
veredicto: NO-SHIP
revisor: Codex (CLI 0.153.0-alpha.5, gpt-5.6-sol)
objeto: diff 727190f..17d9336 (accion 6a + MEJORAS #168)
sha256_informe: 1e4fa0ff184efe6c5c42e0b5b5f898de7a29d977ce1171395f12cdc9fcc1da97
---

# Acta de revision adversarial R1 — accion 6a (filtro de ruido) + `MEJORAS #168`

- **Objeto revisado:** diff `727190f..17d9336` — filtro de ruido en `core/email_export.py` y `MEJORAS #168`
- **Ronda:** R1 (unica; radio de dano = no decide quien escribe ni destruye datos de cliente)
- **Revisor:** Codex (CLI 0.153.0-alpha.5, `gpt-5.6-sol`), copia externa `git archive`, solo lectura
- **Informe recibido:** 2026-09-06, `C:/t/r6a2115/INFORME.md`, 19.788 bytes
- **Hallazgos:** 6 — 3 ALTOS (H-01, H-02, H-03), 3 MEDIOS (H-04, H-05, H-06); **6 confirmados, 0 refutados**
- **Remediado en:** ver el §6 del plan `docs/superpowers/plans/2026-09-06-accion-6a-filtro-de-ruido-email-export.md`

**Por que existe esta acta.** Yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **que dijo el revisor** con **que decidi yo que dijo**. La adjudicacion —cada
hallazgo confirmado o refutado contra la fuente— vive en el §6 del plan, no aqui.

**Digest.** `sha256_informe` se computa sobre el BLOQUE canonicalizado de abajo
(`bloque.replace("\r\n","\n").strip("\n") + "\n"`, UTF-8), que es lo que recomputa el guard G8.
El `sha256` del fichero crudo entregado por el revisor es
`1e4fa0ff184efe6c5c42e0b5b5f898de7a29d977ce1171395f12cdc9fcc1da97` — coincide.

**El revisor EJECUTO, no leyo.** Corrio 152 tests de la suite afectada, los 15 de
`contaminacion`, los 9 mutantes del arnes adaptados a su entorno (9/9 muertos), **un decimo
mutante propio** que destapo H-06, y 19 sondas adversariales escritas por el. Tres de sus seis
hallazgos vienen con el escenario ejecutado y su log. La independencia esta acreditada: el
`sha256` de `core/email_export.py` en la copia coincide al abrir y al cerrar.

**Lo que el propio revisor declaro SIN VERIFICAR**, y que por tanto no esta cubierto: la suite
completa del repositorio, las dos semillas de cierre, los servicios externos, el corpus real y la
frecuencia real de falsos positivos, los enlaces simbolicos distintos de junction NTFS, UNC y las
condiciones de carrera. Esas las cubre el autor, no el acta.

---

## 1. Informe recibido — texto LITERAL del revisor

> Lo que sigue es la voz del revisor sin una sola edicion. Las erratas, los enfasis y el orden son
> suyos. Nada de lo de abajo es adjudicacion: la adjudicacion esta en el §6 del plan.

Higiene inicial: había `MANDATO.md`, `_stdout.log` y `.hora`; no leí `_stdout.log` ni `.hora`. La enumeración fue anterior a crear la copia y las evidencias de esta revisión.

# R1 — acción 6a, filtro de ruido

## Integridad al abrir y alcance

SHA-256 inicial de `C:/t/r6a2115obj/head/core/email_export.py`:

`336fe156e2a7df5fc53dc1c40211e97c9073ae714ac59e5cde541fbc88bb9194`

Objeto leído: las copias `base/` y `head/` entregadas. `git diff --no-index --stat` confirma diferencias en exactamente los nueve ficheros enumerados en el mandato. Se revisaron los diffs y las implementaciones y dependencias relevantes. Ninguna escritura se dirigió al objeto. La copia de ejecución es `C:/t/r6a2115/h/`.

**Genealogía: SIN VERIFICAR.** Ninguna copia contiene `.git`; sus correspondencias con `727190f` y `17d9336` son declaraciones del encargo, no acreditaciones de esta revisión.

## Qué ejecuté y qué salió

Intérprete: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`. Ejecución desde `C:/t/r6a2115/h`, con `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, caché pytest desactivada y temporales relativos dentro del workdir. Servicios Gmail y datos sintéticos; ninguna operación contra Gmail, CRM o Drive reales.

1. **Suite afectada: 152 tests, salida 0, sin fallos.** Comando: `python -m pytest tests/test_email_export_filtro_ruido.py tests/test_email_export.py tests/test_intake_log.py tests/test_intake_log_workspace.py -q -p no:cacheprovider -p no:randomly --basetemp=../t0`. El conteo se confirmó mediante colección independiente (`collection.log`). Los 30 tests nuevos están incluidos.
2. **Contaminación: 15 passed.** `python -m pytest tests/test_email_atomize_contaminacion.py -o addopts= -q -p no:cacheprovider -p no:randomly --basetemp=../ct`. Evidencia: `contaminacion.log`.
3. **Mutaciones originales: 9/9 muertos en los tests esperados.** Adaptación en `run_mutants.py`: importa las nueve sustituciones originales, exige una única ancla, compila cada versión en memoria en un proceso separado y ejecuta el fichero de 30 tests. No ejecuté el `main()` original ni su `git checkout`. Se verificaron códigos de salida y conjuntos de tests fallidos; base sin mutación: salida 0. Evidencias: `mutation_evidence/results.json` y `m00.log`–`m09.log`.
4. **Mutante adicional de deduplicación: sobrevive a los 30 tests**, salida 0. Añade el Message-ID excluido a `vistos` antes del `continue`. Contra mi sonda con una colisión real, el mismo mutante falla: `duplicados == 1` donde el código original devuelve 0. Evidencias: `m10.log`, `m10_validation.log` y H-06.
5. **Sondas adversariales propias:** `tests/review_r1.py`, 19 passed en `probes2.log`, más 3 passed y 19 deselected en `boundaries.log`. Comandos: `python -m pytest tests/review_r1.py -o addopts= -q -s -p no:cacheprovider -p no:randomly --basetemp=../rt2`; y el mismo comando con `-k 'windows_path_boundaries or config_failure or absent_case' --basetemp=../rt3`. Son aserciones de caracterización: que pasen confirma los resultados descritos, incluidos defectos; **no significa aceptación del producto**.

La primera versión de la sonda de anidados tuvo tres fallos del propio instrumento: buscaba el contenido de un adjunto como texto literal en un MIME que lo codificaba en base64. Se corrigió para comprobar la inclusión de los bytes RFC822 originales. Se conserva `probes.log` con esos fallos; la repetición corregida figura en `probes2.log`. No se alteró producción para obtener el resultado.

Resumen de fronteras de mutación:

| Mutante | Tests fallidos | Evaluación |
| --- | ---: | --- |
| M01 desactivar exclusión | 5 | Exclusión y sus consecuencias dependientes |
| M02 omitir Cc | 1 | Integración de facturación en copia |
| M03 marcar excluido como exportado | 1 | Aserción del índice en reversibilidad |
| M04 repositorio por buzón solo | 1 | Conjunción con referencias |
| M05 separador CRM incorrecto | 5 | Misma propiedad; cuatro integraciones contienen `g-repo` |
| M06 acta sin CFO | 2 variantes | Falsos positivos de actas ordinarias |
| M07 suprimir evento | 1 | Evento durable |
| M08 comprobar nombre | 1 | Destino externo |
| M09 trazar destino externo | 1 | Destino externo |

No encuentro un mutante original mal apuntado en estas ejecuciones. La muerte de M03 ocurre en el índice, antes de la segunda corrida: eso prueba la frontera que muta. El test original sí ejecuta una recuperación real cuando el índice es correcto. M09, pese a su nombre, deja vigente la generación del aviso: prueba que no se trace fuera; no suprime por sí mismo el aviso. La parsificación original de los nombres de test corta los parámetros con espacios; comprobé las dos variantes de M06 en su log.

**SIN VERIFICAR:** suite completa del repositorio, dos semillas de cierre, servicios externos, corpus real y frecuencia de falsos positivos/negativos, enlaces simbólicos distintos de junctions NTFS, UNC y condiciones de carrera. No se ejecutó un rescate real de Drive; el recorrido de `.eml` de Drive se inspeccionó en fuente y comparte el depósito sin filtro descrito en H-01.

## Hallazgos

### H-01 — ALTO — Un mensaje declarado excluido vuelve a depositarse por anidados o enlaces

**Fuente:** `head/core/email_export.py:1148` (filtro limitado al bucle principal), `:1197`–`:1198` (aplanado y enlaces), `:445`–`:458` y `:635`–`:655` (depósitos alternativos sin clasificación).

**Escenario ejecutado:** la etiqueta contiene un correo `noise`, asunto `Circularizacion de auditoria 2026`, con un adjunto sintético que representa la cartera; también un padre `RV bloque` que lo transporta como `message/rfc822`. Se procesa primero `noise` y se declara excluido. Después se escribe el padre y se aplana el hijo: `written=1`, `nested_flattened=1`, `errors=[]`; el M9 registra tanto el padre como la circularización. El evento afirma que el correo no se depositó, aunque sus bytes están en el expediente.

Un segundo escenario aún más directo: el padre contiene un permalink al mismo Gmail ID excluido, `deadbeef1234`. `_rescata_gmail` lo obtiene otra vez y `_deposita_mensaje_rescatado` lo escribe; `links_resolved=1`, `errors=[]`, y el fichero de circularización aparece en `report.files`. Esto usa cabeceras del correo rescatado perfectamente clasificables, sin necesidad de inferir nada del cuerpo.

**Por qué es defecto:** rompe la propiedad 1 y el objetivo de impedir la entrada de anexos administrativos. No basta con que el `gmail_id` no entre en el índice: los bytes ya se han publicado y el rastro de exclusión induce a creer lo contrario. También se introduce el Message-ID del ruido en `vistos` por esos recorridos.

Desactivar `flatten_nested_emails` evita el fichero hijo separado, pero **no** elimina el correo administrativo embebido en el padre fiel; se comprobó esa inclusión exacta. `extract_attachments=True` tampoco cierra la entrada. Filtrar únicamente `_aplana_anidados` sería un remedio incompleto.

**Dirección del remedio:** extender la decisión a los correos rescatados y definir expresamente el tratamiento del contenedor fiel con hijos administrativos antes de depositarlo. Esa decisión debe preservar la doctrina probatoria; no se propone mutilar silenciosamente el padre.

**Evidencia:** `probes2.log`, `EVIDENCE nested` (tres configuraciones) y `EVIDENCE gmail_link`.

### H-02 — ALTO — La validación física acepta destinos para los que el M9 calcula rutas falsas

**Fuente:** `head/core/email_export.py:1227`, `:1253`, `:1280`–`:1284`; consumidor en `:1424` y cálculo relativo en `_emit_traza`.

**Escenario 1 ejecutado:** destino `caso/00_Input/subcarpeta/2026-09-06_email_01`. `_cae_bajo` devuelve verdadero. `_emit_traza` usa `dest.parent` como si fuera `00_Input` y registra `2026-09-06_email_01/2026-06-12_oferta.eml`, omitiendo `subcarpeta/`. Esa ruta no existe bajo el `00_Input` del caso. Resultado: `intake_logged=True`, `errors=[]`.

**Escenario 2 ejecutado en Windows:** junction externa llamada `2026-09-06_email_02` que apunta al lote físico interno `2026-09-06_email_01`. La validación física la admite, conforme al comentario sobre alias. El manifiesto, sin embargo, registra el nombre lógico `..._02/2026-06-12_oferta.eml`, inexistente en el caso; de nuevo no hay errores.

**Por qué es defecto:** #168 no queda cerrado por pertenencia física si el escritor posterior mantiene una base relativa incompatible. La comparación física es correcta para rechazar un destino realmente externo, pero insuficiente para acreditar la validez de las rutas que se van a registrar. La suposición `dest.parent == 00_Input` es preexistente; el nuevo guard pretende protegerla y admite entradas que la incumplen. Los índices cross-lote tampoco enumeran un lote situado dentro de `subcarpeta`.

**Dirección del remedio:** mantener una raíz canónica y calcular contra ella las rutas de manifiesto y referencias de duplicados, o rechazar explícitamente las topologías que los consumidores no soportan. Resolver para validar y volver a la ruta lógica para registrar no basta.

**Evidencia:** `probes2.log`, dos entradas `EVIDENCE m9_path`, con las rutas registradas y su inexistencia comprobada.

### H-03 — ALTO — Las regex excluyen asuntos probatorios que no describen administración del despacho

**Fuente:** `head/core/email_export.py:133`–`:140`, uso en `:181`–`:184`. Contraste: plan §3.1 y tabla de §3.2.

**Entradas ejecutadas, tras construir y parsear RFC822:**

- `W-ABC123 · Acta notarial aportada por el CFO del propietario` → `gobernanza_interna`.
- `W-ABC123 · Carta de auditoria tecnica del inmueble` → `auditoria`.

**Por qué es defecto:** son descripciones de documentación de un caso, sin señal de administración interna. Gobernanza solo exige `acta` seguida, a cualquier distancia, de `CFO`: no exige reunión ni Legal, aunque el plan y la CLI anuncian actas CFO+Legal. Auditoría admite el prefijo `auditor`, de modo que `carta de auditoría técnica` se trata como carta de auditores administrativos. En una exportación ordinaria esas clasificaciones activan el `continue` y omiten prueba por defecto.

Que `acta` o `auditoría` aisladas sobrevivan está probado, pero no acredita la especificidad contratada. El W-code del ejemplo no causa la exclusión; la causa es la regex demasiado amplia.

**Dirección del remedio:** ajustar las señales a la categoría administrativa concreta y añadir negativos próximos a cada regla, incluidos asuntos con referencias de expediente y actores de terceros. No basta con negativos de palabras aisladas.

**Evidencia:** `probes2.log`, `EVIDENCE subject`. Los ejemplos son sintéticos; no afirmo que se haya omitido un correo real con esos asuntos.

### H-04 — MEDIO — Resolver `00_Input` y tomar su padre puede enviar el evento a otra raíz

**Fuente:** `head/core/email_export.py:1243`–`:1245`, `:1263`; receptor `head/core/intake_log.py:253`–`:262`.

**Escenario ejecutado:** el caso existe y su `00_Input` es una junction a una carpeta física llamada `physical_input`. El export funciona hasta terminar el filtrado y eliminar el lote vacío. `_input_root_de` devuelve la carpeta física; el evento se dirige a `physical_input.parent`. `append_event` añade otra vez `/00_Input`, buscando un directorio que no es el original.

**Resultado:** `LocalWorkspaceMissing` en `append_event`, ningún evento durable y ninguna devolución del `ExportReport`. La traza conservada identifica `email_export.py:1243` e `intake_log.py:258`; no es un fallo previo del localizador. Si en ese padre existiera otro `00_Input`, la misma construcción dirigiría allí el evento (consecuencia de fuente; esa variante no se ejecutó).

**Por qué es defecto:** la raíz física de un subdirectorio no permite reconstruir el caso mediante `.parent`. Introduce un destino erróneo precisamente en el nuevo evento y rompe el rastro cuando todo fue excluido.

**Dirección del remedio:** conservar la raíz del caso resuelta como entidad separada de la raíz física usada para comprobar pertenencia, o permitir al emisor recibir directamente la ubicación correcta del log.

**Evidencia:** `probes2.log`, `EVIDENCE input_junction`, incluida la pila de llamadas.

### H-05 — MEDIO — La señal de destinatario es una subcadena, no una dirección

**Fuente:** `head/core/email_export.py:149`–`:157`.

**Entrada ejecutada:** `To: "proveedores.es@engelvoelkers.com" <abogado@ejemplo.test>`, asunto `Oferta`. `parse_headers` conserva la cabecera y `clasificar_ruido` devuelve `facturacion_despacho`.

**Por qué es defecto:** el destinatario real es `abogado@ejemplo.test`; la dirección de proveedores solo es el nombre mostrado. La exclusión por defecto se dispara sin la señal estructural que justifica la regla. La misma búsqueda tampoco comprueba fronteras del addr-spec. El comentario descarta el falso positivo como no realista, pero no evita que una cabecera válida lo produzca.

**Dirección del remedio:** comparar direcciones efectivas con el buzón completo y tratar explícitamente los formatos problemáticos de listas. Un fallo de parseo no justifica equiparar texto arbitrario a un destinatario.

**Evidencia:** `probes2.log`, `EVIDENCE recipient`. No se ha medido la frecuencia de este formato en el corpus del despacho.

### H-06 — MEDIO — El test de no contaminación de dedup no ejerce ninguna colisión

**Fuente:** `head/tests/test_email_export_filtro_ruido.py:191`–`:198` y fixture `_raws_mixtos` en `:156`–`:173`; el arnés original no contiene un mutante de esta frontera.

**Por qué es defecto:** el docstring promete que un segundo correo con el mismo Message-ID detectaría una contaminación de `vistos`, pero todos los mensajes de `_raws_mixtos()` tienen IDs distintos. `duplicados == 0` sigue siendo cierto aunque se inserten todos los excluidos en `vistos`.

**Mutación ejecutada:** insertar, inmediatamente antes del `continue` del filtro, `vistos.add((cabeceras.get("message-id") or "").strip().strip("<>"))`. Los 30 tests pasan. Con dos Gmail IDs, primero uno de ruido y después uno admisible, ambos con `<same@x>`, el mutante produce `duplicados=1`; el original produce 0. Mi sonda mata el mutante por esa aserción exacta.

**Dirección del remedio:** ejercer colisiones de Message-ID entre ruido y material admisible, en ambos órdenes, y comprobar también `duplicados_map` y las referencias de manifiesto pertinentes. Añadir un mutante que ataque esta propiedad.

**Evidencia:** `mutation_evidence/m10.log` y `m10_validation.log`; control sin mutación en `probes2.log`, `EVIDENCE collision_force`. Es un defecto de cobertura, no una acusación de que el bucle principal actual contamine `vistos`.

## Respuesta punto por punto al mandato

| Propiedad | Resultado y límite |
| --- | --- |
| A1. Excluido no escrito | Cumple en el recorrido directo; **refutada como propiedad de la exportación** por H-01. |
| A2. Reversible sin force | Verificada con la segunda corrida del test original y con un lote enteramente ruidoso: índice vacío para la cuenta, recuperación de 1 correo. |
| A3. No contamina dedup | Verificada para el recorrido directo con colisión real. Cobertura original insuficiente (H-06); los depósitos alternativos sí añaden el ruido a `vistos` (H-01). |
| A4. Rastro durable y nada si no hay exclusiones | Tests normales pasan, incluido el evento con lista y motivo por mensaje. Es un evento agregado, no uno por mensaje. La junction de `00_Input` rompe el destino (H-04). Sin `case_id`, el código solo conserva el report, no emite evento durable. |
| A5. Reglas solo sobre cabeceras | Confirmado en fuente. `clasificar_ruido` usa To/Cc/Subject; no usa cuerpo. Que otras fases lean el cuerpo para rescatar enlaces no cambia ese hecho. |
| A6. Especificidad | Las palabras aisladas no excluyen, pero existen falsos positivos próximos y ejecutados (H-03 y H-05). |
| B. #168 | El destino externo ordinario no entra en M9 y genera aviso. La frontera no garantiza rutas válidas para profundidad adicional o alias físico (H-02). |

Otras interacciones examinadas:

- **`force`:** sigue aplicando el filtro; no lo desactiva. En la sonda con un ruido y un admisible con el mismo Message-ID, la primera corrida da 0 duplicados y la repetición forzada da 1 por el admisible ya presente. El excluido no figura en el índice.
- **Lote completamente ruidoso:** en el caso ordinario se elimina el lote vacío, se conserva el evento y la recuperación funciona. Se escriben ficheros de protocolo/índices del caso; «no se escribe un solo fichero» en el comentario de `:1241` no debe entenderse literalmente como ausencia total de escrituras.
- **Destinos físicos Windows:** probadas junction saliente (rechazada), igualdad `dest == 00_Input` (rechazada), mayúsculas y destino relativo (admitidos correctamente). Los problemas de alias entrante y raíz redirigida son H-02/H-04.
- **`caso_path` que lanza:** inyectando su fallo con el caso todavía resoluble por el localizador legacy, se devuelve aviso de raíz no resuelta y el evento llega al caso. Un caso realmente ausente aborta antes, en `_dir_estado_canal → path_for`; el comentario «un caso irresoluble no aborta el export» solo describe el helper nuevo, no toda la función. Ese aborto temprano es preexistente.
- **Fallo del emisor durable:** inyectado `OSError` solo en `email_excluido_ruido`. Se propaga después de escribir el correo admisible y su Gmail ID, y antes de registrar sus rutas en M9. Resultado observado: fichero presente, índice con `ok`, M9 vacío, sin report devuelto. La API no contiene esa excepción. No lo equiparo por sí solo a un fallo de política: abortar al perder trazabilidad puede ser deliberado; sí documenta que la operación puede quedar parcialmente materializada.
- **Índice de canal y destino externo:** la exportación externa aún marca el Gmail ID en el índice del caso. Una corrida posterior a un lote interno salta ese ID, escribe 0 y elimina el lote vacío. Es un comportamiento **preexistente**, conservado por este diff; el aviso de #168 no lo remedia. No se presenta como regresión nueva.
- **Plan:** la CLI y el valor por defecto coinciden con T6; reversibilidad, Cc y evento ordinario tienen pruebas reales. La tabla de gobernanza describe una señal más estrecha que el código (H-03), la promesa general de no depositar no cubre recorridos alternativos (H-01), y la comprobación física no basta para las rutas que traza el escritor (H-02). El separador U+00B7 está en el patrón y en `docs/INTEGRACION_SUDESPACHO.md:900`. Un asunto `S/R: · M/R: / · Cliente: EV · Contrario:` no se excluye; el documento muestra `{num}/{serie}`, pero no acredita cómo renderiza el CRM cuando ambos valores faltan. **SIN VERIFICAR** ese render vacío real; no lo elevo a defecto confirmado.

**Contaminación por otros W-codes:** `core/email_atomize/contaminacion.py` es byte-idéntico en ambas copias, SHA-256 `ed10d3f595518c0312622b33202f6d1bbd55029131adaff441fb4e784b59fee0`. Sus 15 tests pasan; la implementación devuelve hallazgos y avisos, sin borrar ni excluir mensajes. El nuevo clasificador no llama al detector ni clasifica por W-code. La doctrina sigue separada en código, aunque los falsos positivos de asunto de H-03 puedan omitir correspondencia de expediente.

## Integridad al cerrar

SHA-256 final de `C:/t/r6a2115obj/head/core/email_export.py`:

`336fe156e2a7df5fc53dc1c40211e97c9073ae714ac59e5cde541fbc88bb9194`

Coincide con el inicial y con la copia de producción ejecutada en `h/core/email_export.py`. Los mutantes se ejecutaron en memoria; las únicas modificaciones de la copia fueron instrumentos de revisión. Evidencia adicional: `closing_integrity.json`.

NO-SHIP


---

## 2. Evidencia verificada por el adjudicador

Contrastado contra la fuente ANTES de remediar, que es lo que la casa exige:

- **H-01** — `core/email_export.py:430` (`_aplana_anidados`) y `:636`
  (`_deposita_mensaje_rescatado`) escriben al expediente **sin pasar por `clasificar_ruido`**.
  Son dos puertas reales al mismo deposito. CONFIRMADO por lectura de la fuente, ademas del
  escenario que el revisor ejecuto.
- **H-02** — `_emit_traza` toma `input_root = dest.parent` (`:1424`) mientras el guard nuevo solo
  comprobaba pertenencia **bajo** `00_Input`. Un `dest` a dos niveles pasa el guard y rompe la
  suposicion del escritor. CONFIRMADO: la frontera correcta es **hijo directo**, no descendiente.
- **H-03** — `\bacta\b.*\bcfo\b` casa a cualquier distancia, y `auditor` es prefijo de
  `auditoria`. CONFIRMADO por inspeccion de los patrones.
- **H-04** — `_input_root_de` hace `.resolve()`, asi que con `00_Input` como junction el `.parent`
  no es el caso. CONFIRMADO.
- **H-05** — la comprobacion por subcadena mira el header crudo, display name incluido.
  CONFIRMADO; el comentario que escribi descartando el falso positivo como "no realista" era una
  afirmacion sin medir, y el revisor construyo uno.
- **H-06** — **detectado en paralelo por el adjudicador**, mirando el runner del revisor mientras
  corria, y **ya remediado** antes de leer el informe: el mutante que mete el excluido en `vistos`
  sobrevivia a los 30 tests. Se deja constancia de la procedencia para no atribuirme un hallazgo
  ajeno ni fingir que el informe llego antes.

Digest del bloque literal recomputado por el guard G8 de `tests/test_docs_gobernanza.py`.
