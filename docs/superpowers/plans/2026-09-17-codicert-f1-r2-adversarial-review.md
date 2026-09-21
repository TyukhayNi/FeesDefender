---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-17-codicert-f1.md
objeto_rev: "1"
commit: 52c2c0e
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: r2k4
sha256_informe: a936c008984a256e48bbe5da56d8e3f26552f9be4488cf9f255a81a991dfee4c
adjudicado_en: docs/superpowers/plans/2026-09-17-codicert-f1.md §13
---

# Acta — R2 adversarial sobre el DIFF del envío certificado por Codicert

Objeto: el **diff** de la rama `claude/codicert-burofax-ovcs-89e7aa` contra `main`, en el commit
`52c2c0e` — 8.102 líneas, 41 commits, las doce tareas de F1. La R1 revisó el diseño; esta revisa
el código que lo implementa, que es donde un defecto deja de ser una frase y pasa a gastar
16,97 € y mandar una comunicación irreversible.

**Esta ronda sí la ejecutó Codex**, con su propia bolsa, y no un revisor sustituto: recuperó cupo
el 2026-09-19. La independencia es por tanto la fuerte, no la débil de la R1.

| | |
|---|---|
| Revisor | Codex CLI `0.154.0-alpha.6.2`, `model_reasoning_effort=high` |
| Objeto | copia externa de 1.385 ficheros, fuera del repo, sin `.git` |
| `sha256` del objeto | `a4db810ed65cb3c8c97e7ccbb31c609d2d861b870365b8ca2cfc0b8ae13e1298` — **idéntico al abrir y al cerrar**, reproducido por las dos partes |
| `sha256` del informe | `a936c008984a256e48bbe5da56d8e3f26552f9be4488cf9f255a81a991dfee4c` |
| Veredicto | **NO-SHIP** |
| Hallazgos | 16 — **7 `alta`, 9 `media`, 0 `baja`** |

**Y esta ronda corrió la suite, que es lo que la hace distinta de una lectura.** 128 pruebas del
ámbito del diff en verde, y encima de eso **sondas ejecutables que reproducen cada defecto** y un
mutante que sobrevive a las 128 (H-14). Un hallazgo con su sonda no se discute: se reproduce.

**Lo que encontró y ninguna lectura mía habría encontrado**, en una frase por pieza:

- **Los apellidos del CRM no se leen.** `clientes_contrarios` tiene `1apellido` y `2apellido`, el
  atlas del repo los declara, y el código usa solo `nombre`. ANA LÓPEZ GIL sale como **«ANA»** en
  los tres canales. Mis fixtures ponían el nombre completo en `nombre`, así que **ningún test
  podía verlo**: el doble tapaba la condición.
- **El digest no sella lo que se envía.** Omite el ordinal, el asunto, el cuerpo, el coste y la
  cuenta emisora — y `frozen=True` no inmoviliza las listas que contiene. Una confirmación de
  `W-000AAA - REQ` autoriza tres envíos con `W-000AAA - REQ 2`, por la vía pública `--ordinal`.
- **El PDF se reabre después de comprobar su huella**, y entre ambas lecturas se pagina el
  listado remoto: sobrescribir la ruta durante esa ventana manda un documento distinto del
  aprobado.
- **Un listado remoto vacío reactiva envíos ya cerrados en disco**: 6 POST donde debían ser 3.
- **El registro no distingue entorno ni cuenta**, así que los cierres de sandbox dan por completa
  una expedición de producción.
- **Dos ejecuciones simultáneas pasan las dos guardas** y duplican, reproducido con una barrera
  de dos hilos.
- **Olvidar `cliente=` elude el guard entero**: llamar a la API pública sin inyectar cliente no
  importa `httpx`, no nombra una URL y no llama a `_cliente_real`, así que los cinco checks pasan
  mientras la llamada alcanza la puerta real.

**Y lo que intentó refutar y no pudo**, que vale tanto como lo anterior: la confirmación cruzada,
el cambio de plaza o entorno, el PDF cambiado antes de ejecutar, el saldo vivo insuficiente, el
pendiente sin resolver y el identificador remoto desconocido **sí bloquean**. El censo del guard
**sí** incluye el doble, y su control positivo falla donde dice.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:r2k4 -->
# R2 adversarial — diff del envío certificado por Codicert
objeto: rama claude/codicert-burofax-ovcs-89e7aa, commit 52c2c0e
revisor: Codex
fecha: 2026-09-21
veredicto: NO-SHIP

La puerta humana y la idempotencia permiten comunicaciones distintas de las aprobadas y envíos duplicados. Hay también omisiones silenciosas al reanudar. **16 hallazgos: 7 de severidad alta, 9 media y 0 baja.** La adjudicación corresponde a Claude contra las fuentes y las reproducciones que se adjuntan; este es el veredicto del revisor.

## Alcance y evidencia reproducible

Revisado el diff suministrado y el contexto que consumen sus módulos, especialmente la adaptación de `clientes_contrarios`. Recontado: **8.102 líneas, 24 rutas y 41 commits enumerados**. Los **19 ficheros nuevos** del diff coinciden, normalizando los finales de línea, con los del árbol entregado. Evidencia: `comprobar_objeto_diff.py` y `objeto_diff_verificado.json`.

Todas las rutas de código citadas abajo son relativas a `objeto/`. Los programas, logs y XML de esta revisión están junto a este informe, **fuera de `objeto/`**. Las pruebas se ejecutaron sobre `scratch/`, copia del objeto. No se ejecutó `_codicert_humo.py`, no se resolvieron credenciales reales y no se hicieron llamadas a Codicert ni al CRM. Los arneses bloquean mediante audit hooks las conexiones, la resolución DNS y el lanzamiento de subprocesos durante las pruebas. Los transportes de las reproducciones son dobles locales.

Comandos ejecutados con `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`:

```text
python.exe -B ejecutar_suite_segura.py
python.exe -B reproducir_r2.py
python.exe -B sondas_adicionales_r2.py
python.exe -B mutantes_r2.py
python.exe -B comprobar_objeto_diff.py
python.exe -B comprobar_digest.py
```

- Suite focalizada original: **128 pruebas aprobadas**, código 0 (`suite_focalizada_2.log`). Incluye todos los `test_codicert_*.py`, `test_expedicion_*.py` y `test_guard_codicert_sin_red.py` del diff.
- Sondas: ambos programas terminaron con código 0, verificando mediante aserciones los comportamientos descritos (`sondas_r2.log`, `sondas_adicionales_r2.log`). Que estas sondas pasen significa que **reprodujeron el defecto**, no que la implementación sea correcta.
- Mutación que elimina la conexión de la guarda de texto: **128 passed**, código 0 (`mutante_guarda_texto.log` y `.xml`).
- Guard frente a omisión de cliente: **5 passed**. Control positivo con llamada explícita al cliente real: **1 failed, 4 passed**, sin importar ni ejecutar la sonda peligrosa (`guard_omision_cliente.*`, `guard_control_positivo.*`).
- Las mutaciones se restauraron con los bytes originales en `finally`. No se corrigió código de producción.

El primer intento de suite se detuvo al bloquear un subproceso de consulta de versión de Windows durante la carga automática de Faker, antes de ejecutar tests (`suite_focalizada.log`). Se precargó esa información local y se desactivó la carga automática de plugins; después pasaron las 128 pruebas. Se usó `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1` y un `--basetemp` fuera del objeto. No se presenta esa corrida como la suite completa ni como el cierre con dos semillas.

## Hallazgos

### H-01 — El digest no sella lo que realmente se va a enviar
**Severidad:** alta
**Coste del remedio:** estructural
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:435-491,533-545,573-595`; `scripts/codicert.py:145-152`; spec §4.2 y §5.1. Sondas `confirmacion_otro_ordinal`, `destinatario_mutado`, `texto_coste_no_sellados` y `emisor_no_sellado`.

**El defecto:** `_digest_de` omite el identificador con ordinal, asunto, cuerpo, coste y cuenta emisora. Además, `ejecutar` recalcula el digest con los destinatarios del CRM, pero manda los de `plan.envios`, sin verificar que sean esos mismos. `frozen=True` no inmoviliza las listas ni los diccionarios contenidos.

**Modo de fallo concreto:** planificar `REQ` con ordinal 1 y luego con ordinal 2 produce el mismo digest. La confirmación de `W-000AAA - REQ` autoriza tres envíos con `W-000AAA - REQ 2`; es un camino disponible mediante `--ordinal`, sin manipular internamente el plan. También se reprodujo que modificar `plan.envios[0].destinatario['correo']` tras aprobarlo manda a otro correo mientras el CRM conserva el original. Sustituir asunto/cuerpo y poner coste cero mediante `dataclasses.replace` permite enviar con saldo 0,01. Cambiar el usuario resuelto, manteniendo plaza y entorno, tampoco invalida la confirmación.

**Remedio:** definir una representación canónica del contenido ejecutable aprobado: identidad completa de la expedición y cuenta, destinatarios, textos, metadatos/huellas de adjuntos y presupuesto. Sellarla y comparar tanto el plan recibido como el recalculado. Ejecutar exclusivamente la instantánea validada, con estructuras inmutables o copias defensivas. Probar estas variaciones desde la puerta pública y el CLI. No incluir contraseñas en el sello ni en el registro.

### H-02 — El PDF se vuelve a abrir después de verificar su hash
**Severidad:** alta
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:543,558,582`; `core/codicert.py:199-203`. Sonda `cambio_durante_listado`.

**El defecto:** los bytes comprobados por `_rehash_documentos` no son los bytes que se codifican en los adjuntos. Entre ambas lecturas se pagina el listado remoto.

**Modo de fallo concreto:** aprobar el PDF A; durante `listar()` sobrescribir esa misma ruta con el PDF B. El digest ya se comprobó contra A, pero los tres POST llevan B. La sonda modifica el fichero desde el doble de `listar` y comprueba el base64 enviado: contiene `%PDF VERSION B`. No necesita una modificación durante una operación indivisible, sino durante la consulta remota intermedia.

**Remedio:** leer una sola vez los documentos al ejecutar, calcular sus hashes sobre esos bytes y construir los adjuntos desde esos mismos buffers. No reabrir las rutas después de la validación.

### H-03 — Un listado vacío invalida de hecho los cierres locales y permite repetir todo
**Severidad:** alta
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:556-580`; spec §5.2. Sonda `listado_negativo_con_cierres`.

**El defecto:** `pares_cerrados` solo se consulta dentro de `if ids_en_plataforma`. Cuando el listado no muestra esta expedición, `pendientes = list(plan.envios)` vuelve a habilitar incluso los envíos con `IdEnvio` ya cerrado en disco.

**Modo de fallo concreto:** una primera ejecución completa tres envíos y escribe sus tres cierres; la segunda consulta devuelve un listado vacío. Reejecutar el mismo plan manda otros tres. La reproducción termina con **6 POST frente a 3 necesarios**. El registro local aporta evidencia inmediata que contradice el vacío remoto, pero se ignora justo en esa rama.

**Remedio:** considerar los cierres locales también ante un censo negativo. Si el servicio no refleja un ID ya confirmado, conservarlo como hecho o detenerse para reconciliar; nunca autorizar su repetición por esa ausencia. Añadir la combinación «cierres presentes + listado vacío» a los tests.

### H-04 — El registro no identifica el entorno ni el contenido del envío que da por hecho
**Severidad:** alta
**Coste del remedio:** estructural
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:180,225-232,305-306,340-376,550,564-578,708`; spec §4.3 y §5.2. Sondas `cierres_sandbox_completan_produccion` y `cp_distinto_dado_por_hecho`.

**El defecto:** todos los entornos/cuentas comparten `_codicert_intencion.jsonl` bajo el directorio actual. La identidad persistida solo contiene `id_personalizado`, canal y hash de la etiqueta de presentación. No incluye cuenta/entorno ni el payload: en el burofax la etiqueta tampoco contiene CP, provincia o persona de atención. No se conserva el hash documental de lo que salió.

**Modo de fallo concreto:** enviar los tres canales de un caso en sandbox; en el mismo directorio, iniciar su expedición en producción y quedar interrumpido después de cerrar el primer envío. En la reanudación, el listado de producción muestra ese único ID, pero los pares cerrados de sandbox cubren los otros dos. El motor responde **«ya está completa: sus 1 envío(s)»** y no manda los pendientes. En otra sonda, cambiar el CP de un burofax y aprobar el nuevo plan también produce «completa», aunque el único envío existente usó el CP anterior. Cambiar el documento presenta la misma falta de vinculación en el registro.

**Remedio:** versionar el registro y usar identidad de cuenta/entorno, expedición y huella canónica del payload aprobado. No usar la etiqueta visual como clave operativa. Rechazar una reanudación incompatible con la instantánea que produjo los cierres; exigir nueva expedición o reconciliación explícita. Los registros antiguos, sin estos datos, no permiten inferirlos con seguridad.

### H-05 — Dos ejecuciones simultáneas pasan las guardas y duplican el envío
**Severidad:** alta
**Coste del remedio:** estructural
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:550-597`, `RegistroIntencion.anotar` en `287-307`. Sonda `ejecucion_concurrente`.

**El defecto:** comprobar pendientes/listado y reservar la intención son operaciones separadas, sin exclusión entre ejecutores. El UUID nuevo de cada anotación no reserva de forma exclusiva un envío previsto.

**Modo de fallo concreto:** dos invocaciones del mismo plan leen el registro sin pendientes. Ambas quedan en `listar()` y ambas reciben vacío; después las dos anotan UUID distintos y hacen el POST. Con una barrera de dos hilos en el doble del listado se reprodujeron **2 POST para 1 envío aprobado, sin errores**. Dos procesos del CLI pueden recorrer esa misma secuencia; no depende de un actor que altere el plan.

**Remedio:** proteger la admisión y ejecución de una expedición con exclusión interproceso bajo una raíz estable, identificada por cuenta/entorno/expedición, y volver a comprobar el estado dentro de esa exclusión. Si se opta por reservas por envío, la reserva debe ser atómica y persistente. No basta con bloquear cada escritura individual del JSONL.

### H-06 — Los apellidos del CRM desaparecen del destinatario
**Severidad:** alta
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:97,142-154,176-179,660-662`; contexto `core/sudespacho_relations.py:237-245,872-876,2014-2015,2096-2115`; spec §5, que enumera `1apellido` y `2apellido`. Sonda `apellidos_omitidos`.

**El defecto:** se trata `nombre` como nombre completo. En `clientes_contrarios`, a diferencia de colaboradores, los apellidos están separados y la lectura de relaciones conserva esos campos sin concatenarlos. Las fixtures de los tests de expedición ponen artificialmente el nombre completo dentro de `nombre`.

**Modo de fallo concreto:** el CRM devuelve `nombre='ANA', 1apellido='LOPEZ', 2apellido='GIL'`. Los tres destinatarios salen como **ANA**, incluido `nombre`/`a_atencion` del sobre postal; en un sobre conjunto pueden salir solamente los nombres de pila de ambos requeridos. Los apellidos existen en la fuente, pero se pierden antes del envío irreversible.

**Remedio:** adaptar explícitamente la ficha del contrario: componer el nombre completo a partir de los campos reales, conservando correctamente las razones sociales cuando no tienen apellidos separados. Usar ese nombre de forma uniforme en payload, presentación e identidad del envío. Probar el formato que devuelve `get_relaciones`, no solo nombres completos prefabricados.

### H-07 — Un rechazo conocido deja una intención que no tiene transición de recuperación
**Severidad:** media
**Coste del remedio:** estructural
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:309-386,587-597`; `tests/test_expedicion_ejecutar.py:233-272`. Sonda `fallo_tercero_422`.

**El defecto:** cualquier excepción después de `anotar` deja `en_vuelo`, incluso `CodicertDatosInvalidosError` por un rechazo 422. El registro solo permite cerrar con un ID de envío; no ofrece una transición auditada «no salió/rechazado» ni el CLI una reconciliación negativa.

**Modo de fallo concreto:** de seis envíos, los dos primeros terminan; el tercero devuelve un 422 sintetizado por el doble. Quedan **2 hechos y 1 en vuelo**. La segunda ejecución queda bloqueada antes de enviar, incluso después de corregir el problema. Si el humano verifica que ese tercero no existe, no tiene un ID legítimo con el que cerrarlo. Borrar la línea, inventar un ID o cambiar de ordinal no son una reanudación trazable y segura. El test existente siembra dos cierres y ningún intento tercero; acredita esa reanudación preparada, pero no la secuencia de fallo que acabo de ejecutar.

**Remedio:** distinguir rechazo definitivo de desenlace desconocido y añadir una transición persistida para resolver que no hubo envío. Los timeouts deben seguir bloqueados hasta reconciliación humana; no se propone reintentarlos automáticamente. Ejercitar un fallo real del doble en el tercer POST y su recuperación completa, sin editar el registro a mano.

### H-08 — Reanudar exige saldo para pagar otra vez lo que ya está hecho
**Severidad:** media
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:536-540,572-580`. Sonda `saldo_suficiente_para_pendientes_rechazado`.

**El defecto:** la comprobación de crédito compara contra `plan.coste` antes de determinar los pendientes. Ese coste incluye también todos los envíos cerrados.

**Modo de fallo concreto:** correo y SMS ya enviados y explicados; falta únicamente el burofax. Saldo vivo **16,9716**, exactamente suficiente para ese pendiente según la tarifa del propio módulo. El motor exige **18,2348** y rechaza la reanudación. Volver a planificar no ayuda: vuelve a presupuestar los tres canales.

**Remedio:** determinar de forma segura los pendientes y calcular su coste residual antes del control de saldo. Mostrar en el plan/reanudación el total, lo ya realizado y lo que queda por gastar.

### H-09 — Los documentos no tienen preflight de formato, límites ni presupuesto de bytes
**Severidad:** media
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:187-189,477-491,582`; `core/codicert.py:199-203`; spec §1.4 y §7. Sondas `preflight_adjuntos` y `coste_ignora_bytes`.

**El defecto:** planificar solo lee y hashea los ficheros; todos se etiquetan como PDF. No se valida número, formato, tamaño ni páginas. `coste_de` suma exclusivamente tarifas por canal, con independencia del volumen. El spec prescribe el suelo seguro de seis adjuntos electrónicos, límites de tamaño/páginas y estimación del sobrecoste por MB.

**Modo de fallo concreto:** once `.txt` con contenido `no es PDF` generan un plan ejecutable y llegan a los tres métodos de envío del doble. Un fichero pequeño y otro de más de 7 MiB tienen exactamente el mismo coste de correo: **0,7931**. Si el servidor aplica los límites documentados, el rechazo se descubre en el POST, no al aprobar el plan; límites diferentes por canal pueden dejar una expedición parcial. Un saldo que solo cubra las tarifas base tampoco está protegido frente al sobrecoste documental.

**Remedio:** validar los documentos completos contra los canales previstos antes del primer POST y devolver sus metadatos para calcular el presupuesto. Incorporar el volumen/tarifa o bloquear tamaños cuyo coste no pueda estimarse; no declarar margen suficiente ignorando ese componente. Las pruebas deben incluir límites y un formato realmente inválido.

No se afirma haber reproducido un 422 ni un cargo real por estos documentos: se acreditó localmente que ninguna validación los detiene y que el cálculo ignora los bytes. Las tarifas/límites externos se toman del diseño entregado, no de una medición nueva de Codicert.

### H-10 — La ficha postal reutiliza el móvil internacional y convierte cualquier país en España
**Severidad:** media
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:71-100`; spec §1.1, líneas 154-161, y §5 regla 5. Sondas `apellidos_omitidos` y `postal_pais_y_telefono`.

**El defecto:** `movil_normalizado` devuelve once dígitos con `34` y `ficha_postal` los copia en `telefono`. El diseño distingue expresamente ese campo postal, cuyo patrón es `^[67]\d{8}$`, del destinatario electrónico. Además, no se valida el país de entrada: se escribe siempre `España`.

**Modo de fallo concreto:** móvil `600000001` produce teléfono postal `34600000001`, incompatible con el patrón postal documentado. Una ficha con `pais='Francia'`, población/provincia París y CP 75001 se convierte en un envío dirigido a España, sin error. La secuencia normal prepara primero los envíos electrónicos y deja el postal para el final; un rechazo postal por contrato se descubriría después de esos primeros envíos.

**Remedio:** separar la representación de móvil por canal: nueve dígitos para el campo postal y la forma internacional para EEC. Validar o resolver explícitamente el país antes de fabricar el destinatario; rechazar domicilios extranjeros en el plan. El comportamiento actual del servidor frente al teléfono prefijado **no se ha verificado por red**: el incumplimiento comprobado es respecto del contrato aportado.

### H-11 — El transporte sigue propagando excepciones ajenas a su contrato
**Severidad:** media
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `core/codicert.py:181-193,226-240,249-277,292-310`; `scripts/codicert.py:153-159`. Seis sondas de errores en `sondas_r2.log`.

**El defecto:** las llamadas `cliente.request` no traducen errores de transporte. La normalización del JSON tampoco valida de forma uniforme su tipo ni el esquema de autenticación. El CLI solo captura los errores de dominio y `ValueError`, no los errores HTTP ni `KeyError`/`AttributeError`.

**Modo de fallo concreto:** un doble que levanta `httpx.ReadTimeout` produce ese mismo tipo crudo en acceso, crédito y burofax. Un acceso `200 {'estado':'OK'}` sin `datos` produce `KeyError`; crédito con JSON `null` y burofax con JSON `[]` producen `AttributeError`. Las seis salidas incumplen `CodicertError`/`CodicertAuthError`; en un POST puede haberse pagado antes del fallo y el frontal no ofrece el diagnóstico previsto.

**Remedio:** centralizar la traducción de fallos HTTP y validar los sobres de respuesta antes de acceder a campos. Conservar el carácter incierto de los POST fallidos y la intención abierta; no introducir reintentos automáticos. Probar errores de transporte y JSON válido de forma incorrecta en todos los endpoints, además del JSON ilegible ya cubierto.

### H-12 — Un mensaje de autenticación que refleje la clave se imprime sin filtrar
**Severidad:** media
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `core/codicert.py:181-191`; `scripts/codicert.py:153-159`; `tests/test_codicert_token.py:32-36`. Sonda `eco_clave_en_error`.

**El defecto:** el mensaje remoto se copia literalmente al `CodicertAuthError`, pese al contrato «La clave no aparece nunca en el error». La clave está disponible en ese punto y no se elimina del diagnóstico.

**Modo de fallo concreto:** autenticar con una clave canario y recibir un 400 cuyo `mensaje` contenga esa clave. El `str` de la excepción la contiene íntegra, y el CLI la imprime en stderr. Se verificó únicamente con **credenciales sintéticas**. No se ha observado ni se afirma que el servicio real refleje contraseñas; lo demostrado es que esta respuesta rompe la garantía declarada. La exposición del nombre de usuario en la cabecera del plan está exigida por el diseño y no se denuncia como fuga.

**Remedio:** no trasladar texto remoto no filtrado en fallos de autenticación: usar diagnóstico local o sanitizar explícitamente los secretos, también al encadenar excepciones. Añadir respuestas con eco de la clave al test; el actual utiliza `mensaje='no'` y no cubre esta vía.

### H-13 — Olvidar `cliente=` elude todo el guard de red
**Severidad:** alta
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `tests/test_guard_codicert_sin_red.py:100-159`; `core/codicert.py:184,248,263,275`; `tests/conftest.py` y `tests/_barrera.py`. Sondas `guard_olvido_cliente` y `guard_olvido_cliente_dinamico`; ejecuciones pytest `guard_omision_cliente` y `guard_control_positivo`.

**El defecto:** el guard busca llamadas explícitas a `_cliente_real` e imports de `httpx`; no detecta la forma ordinaria de llegar allí: llamar a la API pública sin cliente inyectado. Tampoco hay una barrera de ejecución para Codicert en `conftest`; la barrera existente tiene otro alcance.

**Modo de fallo concreto:** añadir un test con `codicert.acceso('usuario-falso', 'clave-falsa', entorno='sandbox')`. No importa `httpx`, no escribe una URL ni llama expresamente a `_cliente_real`. **Los cinco checks del guard pasan**. La ejecución local de esa llamada, sustituyendo `_cliente_real` por una excepción centinela, demuestra que alcanza la puerta real. Un olvido equivalente en un test de envío hace la petición POST con la ficha suministrada.

**Remedio:** instalar una barrera efectiva de transporte para los tests, activa antes de que puedan ejecutarse llamadas de red, y mantener los barridos como controles auxiliares. Probar una llamada pública sin inyección y exigir que se bloquee antes de abrir conexiones. Un test que examina texto al final de la suite no impide por sí solo una llamada previa.

### H-14 — La suite no detecta que `texto_de` deje de llamar a la guarda de prohibidos
**Severidad:** media
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `tests/test_expedicion_plan.py:65-72,103-112`; `core/expedicion_certificada.py:219-222`; `mutantes_r2.py`, `mutante_guarda_texto.log` y `.xml`.

**El defecto:** el test que dice acreditar que la guarda sigue saltando sobre el texto compuesto llama directamente a `_asegurar_sin_prohibidos`. No recorre la conexión desde `texto_de` ni suministra una plantilla prohibida a esa función. Los tests de composición usan plantillas ya limpias.

**Modo de fallo concreto:** sustituir exclusivamente la llamada de la línea 221 por `pass` en la copia. La guarda deja de aplicarse a cualquier texto generado, pero **siguen pasando las 128 pruebas del ámbito**, incluido el test que dice verificarla. El mutante se restauró después. No se afirma que ese helper sea una tautología: comprueba su lógica; lo que no puede refutar es la desconexión de producción que su descripción promete cubrir.

**Remedio:** introducir temporalmente en el test una plantilla que contenga un término prohibido y llamar a `texto_de`; exigir `ExpedicionError`. Mantener también el control del W-code que contiene casualmente `ovc`, para no reintroducir el falso positivo ya corregido.

### H-15 — El lector del registro acepta corrupción semántica que hace desaparecer pendientes
**Severidad:** media
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:259-281,324-357`; tests de registro. Sondas `estado_corrupto_valido_json` y `lectura_cierre_duplicado`.

**El defecto:** se detecta JSON sintácticamente inválido, pero no se valida esquema ni secuencia. En `en_vuelo`, cualquier estado distinto de `en_vuelo` se interpreta como cierre. Los cierres duplicados se impiden al llamar a `cerrar`, pero se aceptan si ya están en el archivo leído.

**Modo de fallo concreto:** tras una intención legítima, una línea JSON con la misma clave y `estado='hehco'` elimina el pendiente y no lo incluye entre los hechos. La sonda obtiene **`en_vuelo=[]` y `hechos=[]`**: el rastro del envío ha desaparecido de ambos controles sin aviso. Con dos líneas `hecho` para una misma clave e IDs distintos, `ids_hechos_de` devuelve los dos como explicados. Puede surgir al reparar manualmente el fichero o al importar un registro dañado; la mera validez JSON no acredita la integridad de sus transiciones.

**Remedio:** validar al leer campos, estados y transiciones por clave; detenerse con ruta y línea ante estado desconocido, cierre duplicado/huérfano o esquema inválido. Compartir esa validación con las escrituras y con la recuperación de H-07. No consumir un estado desconocido como si cerrara una intención.

### H-16 — Un expediente sin contrarios termina con éxito y «ENVIADO» vacío
**Severidad:** media
**Coste del remedio:** acotado
**Qué he leído o corrido para afirmarlo:** `core/expedicion_certificada.py:132-184,455-457,477-491,599,662`; `scripts/codicert.py:161-162`; contexto `core/sudespacho_relations.py:2006-2012`. Sondas `sin_requeridos` y `cli_sin_requeridos`.

**El defecto:** se rechaza un requerido sin canales, pero no la ausencia de requeridos. `get_relaciones` puede devolver legítimamente ninguna relación; `partes_de` lo convierte en `[]`. Coste cero y cero envíos se consideran un plan ejecutable.

**Modo de fallo concreto:** caso local con expediente extrajudicial, pero sin contrarios vinculados en CRM. Aprobar ese plan y llamar a `enviar` no manda nada, devuelve **código 0** e imprime **`ENVIADO: `**. No es la detección de una expedición ya completa: no existe ningún envío previo ni ningún destinatario.

**Remedio:** impedir planificar una comunicación de este tipo sin requeridos y explicar que faltan las relaciones del CRM. Añadir un test del CLI que exija error y ausencia de POST para ese escenario.

## Respuesta a los seis puntos del mandato

1. **Puerta de gasto:** atacada con variación de ordinal, cuenta, destinatario en memoria, texto, coste y bytes entre comprobación y envío. H-01/H-02 son bloqueantes. Los preflight omitidos se detallan en H-09/H-10; H-06 muestra una pérdida de datos en la adaptación real del CRM.
2. **Idempotencia y reanudación:** H-03/H-04/H-05 reproducen duplicación u omisión. Ejecuté también el tercer POST fallido: quedan dos cierres y una intención pendiente; la reanudación se bloquea. Esa parada ante incertidumbre es correcta, pero faltan la recuperación negativa y el presupuesto residual (H-07/H-08).
3. **Registro:** corrupción sintáctica, cierres duplicados y huérfanos por su API pública sí tienen pruebas que pasan. La corrupción semántica y las transiciones que ya vienen escritas no están protegidas (H-15). No se ha acreditado durabilidad ante corte de alimentación; cerrar el fichero no equivale por sí solo a probar esa propiedad.
4. **Errores/secretos del transporte:** seis contraejemplos al contrato de excepciones y un canario de eco de contraseña, todos sin red ni credenciales reales (H-11/H-12).
5. **Tests y guardas:** 128 pruebas originales pasan. La mutación de desconexión de la guarda de texto sobrevive a las 128 (H-14). El test de reanudación siembra un estado previo a intentar el tercero; no cubre el fallo tercero real (H-07). No se presentan como defectuosos tests cuyo alcance más estrecho está correctamente explicado.
6. **Guard de red:** control positivo visto en rojo; olvido ordinario de `cliente` visto en verde y puerta real alcanzada con centinela previo a red (H-13). El censo recursivo sí incluye los dobles; eso no sustituye una barrera de ejecución.

## Lo que he comprobado y está bien

- Un digest que no coincide se rechaza antes de gastar. Plaza y entorno distintos entre `Plan` y `EntornoExpedicion` también se rechazan. El CLI mantiene sandbox por defecto incluso con `CODICERT_ENTORNO=produccion`; exige la opción explícita para producción.
- Un cambio de dirección en CRM o un cambio/desaparición del PDF **anterior** al rehash bloquea. H-02 se refiere exclusivamente a la segunda lectura posterior, no niega esos controles.
- Se relee el saldo vivo y se bloquea cuando no cubre el coste comparado. H-08/H-09 precisan los errores del importe contra el que se compara.
- Un ID remoto no explicado por el registro detiene el envío. Un `en_vuelo` del mismo identificador bloquea aunque el listado no lo muestre; uno de otro identificador no bloquea. La reanudación preparada con cierres compatibles y visibles manda solo los pendientes.
- `REQ` y `OVC` no colisionan entre sí y el identificador tiene control de longitud. Esto no corrige la ausencia del ordinal en el sello de aprobación de H-01.
- Se envía un correo y un SMS por requerido y se agrupan domicilios con normalización de espacios. El sobre conjunto conserva atención individual y muestra su aviso. Las siete traducciones de provincia y las variantes de normalización de móvil tienen pruebas; H-10 distingue su aplicación al campo postal.
- Ambos POST construyen `Authorization` y `x-json-ficheros: 1`. Un tipo EEC o entorno desconocidos se rechazan antes del cliente. El 422 conserva campos y un 200 de envío sin ID informa de posible salida, en las formas de objeto previstas por los tests.
- La paginación prueba dos páginas con contenidos distintos; la longitud reservada gana a filtros y un cuerpo ilegible en página intermedia no se interpreta como final vacío.
- El registro escribe intención antes del POST y cierre después del retorno; usa el reloj inyectado. No escribe las etiquetas personales en claro. La línea sintácticamente corrupta produce error con fichero y número de línea. `cerrar` rechaza una clave huérfana o ya cerrada por esa misma API.

## Lo que intenté refutar y NO pude

No pude hacer que pasaran las guardas de confirmación distinta, cambio de plaza/entorno, PDF ya cambiado antes de ejecutar, saldo vivo insuficiente, pendiente sin resolver o ID remoto desconocido utilizando sus escenarios de test. Tampoco pude sostener que el guard actual omita `tests/_dobles/fake_codicert.py`: el censo lo incluye. Su control positivo falla donde dice. Los hallazgos anteriores describen entradas o secuencias diferentes y reproducidas, no descartan estas protecciones que sí funcionan.

## Lo que NO he podido verificar

- **Servicio real:** autenticación, entrega, cobros, rechazo concreto del móvil postal, límites efectivos, latencia de listados, tarifa de cada cuenta y correspondencia real de remitente. No se han consultado Codicert, el CRM ni credenciales reales. Las mediciones históricas del spec no se han reproducido; quedan **no verificadas en esta ronda**, nunca refutadas por falta de acceso.
- **Cobertura externa a F1:** cosecha, aportable, firmas y cómputos de plazos pertenecen a F2/F3 según el propio plan. No se atribuyen a esta implementación ni se certifica su corrección jurídica. Tampoco se repite aquí una revisión jurídica independiente de la R1 histórica incluida en el diff.
- **Suite completa y durabilidad:** no se ejecutaron todos los tests del repositorio, las dos semillas de `session_close`, integración real, ni pruebas de corte de alimentación/fsync. Se ejecutó íntegramente el ámbito de tests nuevo del diff, con el aislamiento descrito.
- **Anclaje Git del paquete:** no hay `.git` dentro de `objeto/`. El encabezado conserva el commit indicado por el mandato, pero `_COMMITS.txt` empieza por **`8bf1574`** (humo), seguido de `52c2c0e`, y el árbol/diff incluyen ese script. Se puede acreditar el paquete exacto por su digest y la coincidencia de sus altas con el diff, pero **no** que cada byte sea el árbol Git puro de `52c2c0e`.
- **Bajas documentales frente a `main`:** el diff suministrado elimina `docs/PROCESO_BAD_DEBT_EV.md` (273 líneas), su entrada en el índice y fragmentos recientes de `DEAD_ENDS`, backlog y bitácora (`_DIFF_COMPLETO.diff:1092-1481`). El fichero efectivamente falta en el objeto. Sin el historial/base común no se puede determinar si son borrados de la rama o diferencias por compararla contra un `main` posterior. No se inventa una regresión de merge ni se cuenta como hallazgo adjudicado; aplicar este diff literalmente sí contiene esas bajas. Conviene resolver esa identidad antes de usar el paquete como instrucción de integración.

## Integridad del objeto

Digest de apertura facilitado y reproducido:

```text
a4db810ed65cb3c8c97e7ccbb31c609d2d861b870365b8ca2cfc0b8ae13e1298
```

Algoritmo que reproduce el digest: los 1.385 ficheros, ordenados por ruta relativa sin distinguir mayúsculas, ruta con separador `/` codificada en UTF-8, seguida inmediatamente de sus bytes, sin delimitador entre ambos. Se conserva además `manifest_apertura.json`, con hash individual de cada fichero. `comprobar_digest.py` permite repetir la comparación al cierre. El resultado de cierre se declara también por el canal final, separado de este fichero.

**Comprobación de cierre ejecutada:** `integridad_cierre.log` devuelve el mismo digest `a4db810ed65cb3c8c97e7ccbb31c609d2d861b870365b8ca2cfc0b8ae13e1298`, `manifest_unchanged True` y `files 1385`. El objeto permanece intacto respecto de la apertura.
<!-- informe-literal:fin:r2k4 -->

## 2. Evidencia verificada por mí contra la fuente

- **H-06, los apellidos: CONFIRMADO de forma inequívoca.** `grep` de `1apellido|2apellido` sobre
  `core/expedicion_certificada.py` y `scripts/codicert.py` no devuelve **ninguna** ocurrencia, y
  `docs/CRM_SUDESPACHO_ATLAS.md:1896` declara ambos campos en `clientes_contrarios`. El nombre
  del destinatario se compone en tres sitios (`ficha_postal` y las dos ramas de
  `destinatarios_de`) y los tres usan `parte["nombre"]` a secas.
- **La alarma documental del final del informe queda resuelta, y Codex hizo bien en no
  afirmarla.** Dijo que sin historial no podía determinar si las bajas de
  `docs/PROCESO_BAD_DEBT_EV.md` eran borrados de la rama o diferencias por comparar contra un
  `main` posterior. Es lo segundo: `main` avanzó con `c8b99d1` (PR #389) después de que esta rama
  saliera de `4c0634e`. **Medido, no predicho**, con `git merge-tree --write-tree`: el merge sale
  **limpio** y ese fichero **sobrevive**, igual que los cuatro ficheros nuevos de la rama.

**Lo que el informe declara como no verificado, y comparto:** nada se comprobó contra el servicio
real —ni Codicert ni el CRM—, no se corrió la suite completa ni las dos semillas, y la cobertura
de F2 y F3 queda fuera por pertenecer a fases que no existen todavía.
