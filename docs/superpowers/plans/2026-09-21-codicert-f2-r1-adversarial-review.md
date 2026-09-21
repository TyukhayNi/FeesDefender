---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-21-codicert-f2.md
objeto_rev: "1"
commit: 8dd3952
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: q7wk
sha256_informe: 543385cf0340bd070317f1464b1d18ddfa52dbd1f1867ff146516c20c6638898
adjudicado_en: docs/superpowers/plans/2026-09-21-codicert-f2.md §11
---

# Acta — R1 adversarial sobre el DIFF de F2 del envío certificado por Codicert

Objeto: el **diff** de `claude/codicert-f2-envio-2f9b7f` contra la base de F1
(`6d60187`), en el commit `8dd3952` — 18 ficheros, +5.659 / −12.

**Una ronda y no dos, y eso es lectura de la tabla, no decisión.** El spec §12.2 dio dos
a F1 **por decisión expresa**, porque gastaba dinero y mandaba comunicaciones
irreversibles a terceros. Ese fundamento **no se traslada a F2**: `refrescar` solo lee y
`cosechar` escribe un PDF y crea un documento en el CRM, las dos cosas reversibles. La
tabla de `CLAUDE.md` le asigna una, y una es.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.9.2`, `model_reasoning_effort=high` |
| Objeto | dos copias externas (`base-f1/` 1.387 ficheros, `head/` 1.401), fuera del repo, sin `.git` |
| `sha256` del objeto | **idéntico al abrir y al cerrar**, verificado por las dos partes con manifiestos completos de los dos árboles |
| `sha256` del informe | `543385cf0340bd070317f1464b1d18ddfa52dbd1f1867ff146516c20c6638898` |
| Veredicto | **NO-SHIP** |
| Hallazgos | 10 — **3 `alta`, 7 `media`, 0 `baja`** |

**Esta ronda corrió.** Las dos semillas de la casa (777 y 31337, 280 tests del ámbito
por semilla), una subauditoría separada de los guards cuyo resultado reejecutó el
revisor principal, y **una sonda ejecutable por hallazgo**. Un hallazgo con su sonda no
se discute: se reproduce.

**Dos de los diez los había encontrado yo por mi cuenta**, releyendo el diff mientras el
revisor trabajaba, y estaban remediados antes de leer el informe: H-01 (el transporte
real sin `estados` ni `certificado`) y H-07 (la ruta local devuelta sin comprobar). Que
dos lectores independientes den con lo mismo no resta valor a la ronda — lo añade: el
resto de los ocho **no** los vi.

**Lo que encontró y ninguna lectura mía habría encontrado**, en una frase por pieza:

- **La recuperación de una reserva da por bueno un binario que ya se sabía malo** (H-02).
  La primera cosecha detecta que los bytes del CRM no coinciden y aborta; la segunda
  encuentra el `origen_id`, cierra con hash vacío y devuelve éxito **sin descargar
  nada**. La detección anterior queda anulada.
- **Dos partes con el mismo email atribuyen la recepción a la primera de la lista**
  (H-04), y al invertir el orden del CRM cambia quién consta como receptor de la misma
  prueba. No es hipotético en este CRM: hay fichas que comparten email.
- **La cuenta emisora se lee de la primera mención del texto**, no del bloque
  certificante (H-03). Un asunto que diga «con nombre de usuario madrid.bd» gana sobre
  el acta que certifica `valencia.bd`. Yo acoté la razón social y **no** el usuario.
- **Los tres guards tienen menos alcance del que declaran** (H-08, H-09, H-10), y el
  tercero es el que más escuece: mi propio docstring afirmaba cubrir «el único camino»
  por el que un test escribiría fuera de `tmp_path`, y el guard solo comprueba la
  presencia sintáctica de una keyword.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:q7wk -->
Higiene inicial conforme: solo MANDATO.md, base-f1/, head/, base/ y _stdout.log; no se leyó base/ ni _stdout.log, ni apareció ningún otro elemento inicial.

# Revisión adversarial F2 Codicert — ronda 1

Objeto declarado: base `6d601872e54182b5da68dccc2507844dc2d4d3a4`, head `8dd3952c3ee655fcb1aef74d86b2f7ae0ca31c2a`. Son archivos extraídos sin `.git`: los commits son la identificación del mandato, no una vinculación criptográfica comprobada por este revisor. Comparación realizada exclusivamente contra **base-f1/**. Se identifican 18 ficheros distintos entre los árboles.

La pieza requiere cambios antes de publicarse: el montaje real no conecta las dos lecturas nuevas de F2; la recuperación de una subida fallida puede dar por verificado un binario incorrecto; y el casado por contacto puede atribuir la recepción a una persona distinta al cambiar el orden de las partes. Hay **10 hallazgos: 3 de severidad alta y 7 media**. No se modificó el objeto.

Interpretación del §0-bis: esta es una auditoría de completitud de controles. Los módulos sintéticos defectuosos solo prueban si los guards detectan los defectos declarados; no se han usado para alcanzar servicios ni árboles de producción. Los demás hallazgos se reproducen con dobles y datos sintéticos. Los fallos de dominio posteriores a H-01 son alcanzables mediante el puerto inyectado y seguirán presentes al conectar el adaptador real; no afirmo haberlos observado en producción.

## Ejecución y evidencias

Se leyeron las diez Mediciones antes de las sondas, el diseño rev. 12, el plan F2, los módulos y tests del diff y el contrato documental §17. Se separó una subauditoría de guards, cuyo resultado volvió a ejecutar el revisor principal. El análisis final, las severidades y el veredicto se contrastaron con la fuente.

- Copia de ejecución: `scratch/`, creada desde `head/`. No se aplicaron remedios al código de esta copia para lograr un verde.
- Semilla **777: 280 passed**, 26,75 s; `suite-final-777.log`.
- Semilla **31337: 280 passed**, 27,21 s; `suite-final-31337.log`.
- Sondas de dominio: `audit-root/sondas.py`; resultados en `audit-root/resultados.json`. Ocho reproducciones/control de ventanas, ejecutadas dos veces salvo la última sonda S3, añadida en la segunda pasada. El PDF sintético de H-03 queda en `audit-root/datos/cuenta-ajena.pdf`.
- Sondas de guards: `audit-guards/build_probe.py`; `audit-guards/no-key.log` (**1 failed**, control sin clave) y `audit-guards/probes.log` (**10 passed**, ocho guards y dos módulos deliberadamente defectuosos). Subinforme: `audit-guards/findings.md`.
- Diff reconstruido: `diff-audit.patch`. Manifiestos completos: `hashes-apertura.json` y `hashes-cierre.json`.

Comando reproducible del ámbito, desde la raíz de este workdir, para cada semilla:

```powershell
Set-Location scratch
$tests = @(Get-ChildItem tests/test_expedicion_*.py,tests/test_codicert_*.py | ForEach-Object { $_.FullName })
& 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe' -m pytest @tests tests/test_certificado_lectura.py tests/test_sudespacho_documentos.py tests/test_guard_cosecha_sin_red_ni_escritura.py -q -o addopts= --basetemp=../_t777 -p no:cacheprovider --randomly-seed=777
```

Para 31337, sustituir ambas apariciones de 777. Los temporales son relativos y permanecen dentro del workdir autorizado, pero **fuera de la copia del repo**. Esto último importa: los intentos con temporales bajo `scratch/` produjeron `WorkspaceUnderCatalogRoot` en los tests F1 del mutex, que rechaza locks bajo el repo. Una primera invocación con el directorio del ejecutor fijado a `scratch/` también produjo errores de permisos al crear temporales. Esos intentos quedan en `suite-777.log` y `suite-valida-*.log`; no los cuento como defectos del diff ni como verificación satisfactoria. Cambiar al directorio desde una invocación en la raíz y usar `../_t<semilla>` resolvió ambas condiciones sin cambiar código. `-o addopts=` evita duplicar `-q` y permite conservar el recuento final; se desactiva solo la caché de pytest.

Reproducción de las sondas desde la raíz:

```powershell
& 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe' -B audit-root/sondas.py
& 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe' -B audit-guards/build_probe.py
```

## Hallazgos

Las líneas siguientes pertenecen a **head/**; cuando la causa usa código heredado, se distingue del punto nuevo del diff.

### H-01 — El adaptador real no implementa `estados` ni `certificado`

**Severidad: alta. Coste del remedio: acotado.**

**Dónde:** `core/expedicion_certificada.py:1329-1330` y `2239`, llamadas nuevas; montaje de F2 en `2091-2094`. La clase heredada `_Transporte`, `2068-2081`, solo implementa crédito, listado y dos envíos.

`estado` y `cosechar` construyen ese adaptador mediante `entorno_real()`. En cuanto el listado contiene un envío coincidente, `refrescar()` lanza `AttributeError: '_Transporte' object has no attribute 'estados'`. Conectar solo `estados` dejaría el mismo defecto en `certificado`. No es ausencia de credenciales ni del servicio: faltan métodos Python.

**Reproducción:** `sondas.py::transporte_real` construye el entorno real sustituyendo únicamente autenticación, credenciales y listado por dobles. El resultado enumera ambos métodos ausentes y reproduce el `AttributeError`. No reemplaza `_Transporte`.

**Afirmación contradicha:** Goal del plan, línea 13: que `estado` diga qué ha recibido cada requerido y `cosechar` archive el certificado. El humo `scripts/_codicert_humo_f2.py:44-56` llama directamente a `core.codicert`, por lo que no prueba este montaje. Los tests F2 también suministran transportes con ambos métodos ya implementados.

**Remedio:** conectar ambos métodos al transporte con la ficha y el entorno resueltos, y probar el recorrido CLI → entorno real → transporte usando un cliente HTTP sintético.

### H-02 — Recuperar una reserva convierte un binario incorrecto en cosecha cerrada

**Severidad: alta. Coste del remedio: acotado.**

**Dónde:** `core/expedicion_certificada.py:2218-2236`, especialmente `registro.cerrar(..., sha256="")` en `2228`; verificador inicial en `core/sudespacho_documentos.py:203-211`.

La subida inicial compara bytes y rechaza correctamente una descarga distinta. Sin embargo, el documento ya existe y la reserva queda abierta. La siguiente cosecha encuentra el `origen_id`, **no descarga ni compara el documento**, escribe un cierre con hash vacío y devuelve `ya_estaba=True`. La detección anterior del defecto queda anulada y las siguientes corridas tampoco lo revisan. La presencia del registro CRM no acredita los bytes; además, el contrato reconoce relaciones fantasma.

**Reproducción:** `sondas.py::recuperacion_sin_verificar` usa el verdadero `subir_documento` con HTTP sintético. El POST crea `42990` y su descarga devuelve `BINARIO INCORRECTO`. La primera cosecha falla por hash; la segunda devuelve éxito, hash vacío y **cero nuevas verificaciones HTTP**. Solo se simula el reencuentro de ese documento por su origen.

**Afirmación contradicha:** Global Constraints del plan: «Verificar por resultado, nunca por status»; spec §7.1: «se baja lo subido y se compara el sha256». La reserva no conserva el hash esperado ni una evidencia de emisor que permita reconstruir esta verificación sin recuperar el PDF local.

**Remedio:** persistir la identidad del artefacto esperado y terminar la verificación pendiente antes de cerrar. Si falta el PDF, no coincide el hash o el documento solo es un fantasma, mantener `SIN VERIFICAR`, sin volver a subir automáticamente.

### H-03 — La cuenta emisora se toma de una mención ajena al bloque `CERTIFICADO`

**Severidad: media. Coste del remedio: acotado.**

**Dónde:** `core/certificado_lectura.py:105`, `130-134`.

La razón social sí se lee en su bloque delimitado. La cuenta, en cambio, es la **primera** aparición de «con nombre de usuario …» en la página 1, o en todo el PDF si no estaba allí. Una mención en el asunto/cuerpo anterior a la certificación prevalece sobre la cuenta certificada. También se permite obtenerla de la reproducción cuando el acta no ofrece una legible.

**Reproducción:** `sondas.py::usuario_fuera_acta` genera un PDF de dos páginas, leído por `pypdf`: página 1 con razón social correcta y asunto «Consulta con nombre de usuario madrid.bd.»; página 2 con bloque `CERTIFICADO` que atribuye el envío a `valencia.bd`. Resultado: cuenta leída `madrid.bd` y `es_emisor_esperado(..., usuario="madrid.bd") == True`.

**Afirmación contradicha:** M-4: «el bloque CERTIFICADO da la cuenta» y «Se verifican las dos cosas». No afirmo que una sociedad rival pase el control de razón social: el fallo demostrado es la atribución a otra plaza de la misma sociedad. Por eso su severidad es media.

**Remedio:** delimitar también el párrafo certificante de la cuenta dentro del acta y rechazar ausencia/ambigüedad. Mantener controles negativos separados para razón social y plaza.

### H-04 — Un contacto compartido atribuye la recepción al primer requerido de la lista

**Severidad: alta. Coste del remedio: acotado.**

**Dónde:** `core/expedicion_certificada.py:1194-1203`, particularmente `indice.setdefault(contacto, clave)`.

Dos partes con igual email, móvil o nombre no quedan ambiguas: gana la primera. Todos los envíos que coincidan con ese contacto se asignan a ella. Invertir el orden del CRM cambia quién aparece como receptor de la misma prueba, sin aviso `SIN_CASAR`. No basta con que las fechas se agreguen mediante `min`: su titular también debe estar acreditado.

**Reproducción:** `sondas.py::contactos_ambiguos`, dos personas con `comun@example.test` y un envío leído. Orden A/B: A tiene recepción y B ninguna. Orden B/A: B tiene recepción y A ninguna. Nunca aparece el cajón de ambiguos. F1 `destinatarios_de` admite esas fichas; no hay precondición que excluya contactos compartidos.

**Afirmación contradicha:** docstring `1186-1188`: «Atribuirlo a la primera parte inventaría un reloj sobre alguien a quien quizá no se le entregó nada»; spec §6.1, fechas por requerido. La gravedad es la atribución afirmativa errónea en la salida que el CLI presenta como nivel relevante para plazos, no un cálculo automático de plazos que F2 no hace.

**Remedio:** índice contacto → conjunto de partes; resolver solo coincidencias unívocas o mediante evidencia adicional del envío. Declarar la ambigüedad sin otorgar recepción personal a ninguno por orden de lista.

### H-05 — Cambiar de directorio pierde la memoria de cosecha y permite duplicar

**Severidad: media. Coste del remedio: acotado.**

**Dónde:** `core/expedicion_certificada.py:2186-2188`, registro nuevo bajo `entorno_exp.raiz`. La raíz real usa `Path.cwd()` en `2087`, heredado de F1.

El registro que autoriza a no subir depende del directorio de lanzamiento, no del expediente ni de una ubicación persistente compartida por cuenta. Dos ejecuciones sucesivas desde checkouts/worktrees distintos tienen registros distintos y suben el mismo `IdEnvio`. La clave del mutex sí coincide, pero serializar no repara la pérdida de memoria entre corridas.

**Reproducción:** `sondas.py::raiz_variable`, mismo transporte, cuenta, envío y gestor, con dos raíces locales distintas: **dos subidas**, claves de mutex iguales. Es la variación que introduce `Path.cwd()` en el montaje real. El test existente `test_MUTANTE_una_idempotencia_por_el_LISTADO_no_sirve` incluso borra el registro y exige duplicar.

**Afirmación contradicha:** Goal del plan: «sin poder duplicarlo». El test citado dice «sin registro no se puede sostener la ausencia... ni la presencia», pero de ahí deduce permiso para subir, contrario al criterio conservador del spec §5.2.

**Remedio:** ubicación estable del registro y política explícita para pérdida/migración de ese registro. No inferir ausencia porque se lanzó la orden desde otra carpeta. Es una dependencia heredada de F1 que F2 reutiliza; no se da por refutada por la dispensa de aquella ronda.

### H-06 — La función pública `cosechar` carece de exclusión propia y de exigencia de mutex

**Severidad: media. Coste del remedio: acotado.**

**Dónde:** `core/expedicion_certificada.py:2184-2256`; el CLI sí adquiere exclusión en `scripts/codicert.py:250-262`.

Dos llamadas concurrentes al core pueden leer «no está» y subir ambas. A diferencia de `ejecutar` en F1, `cosechar` no exige una sesión vigente ni sostiene el candado intraproceso. El mutex del CLI protege dos procesos que entren por ese CLI; no constituye la garantía de la función pública. El propio código F1 documenta que las sesiones son reentrantes entre hilos y exige un candado adicional.

**Reproducción:** `sondas.py::carrera_core`: dos hilos sobre el mismo entorno/registro, detenidos con una barrera en la entrada de `gestor.subir`. Ambos llegan y se producen **dos subidas**. No se simula la exclusión: precisamente se comprueba que el core acepta llamadas sin ella.

**Afirmación afectada:** el comentario de `clave_mutex_cosecha`, `1684-1687`, identifica correctamente esta carrera, pero la protección solo se aplica en un llamador. No afirmo que dos CLI correctamente serializadas tengan esta carrera; H-05 es el problema distinto de esas corridas sucesivas.

**Remedio:** exigir la sesión en el core y proteger la secuencia comprobar/reservar/subir dentro del proceso, siguiendo el patrón F1, con pruebas de llamada directa y dos hilos.

### H-07 — Un cierre local hace devolver un PDF archivado que ya no existe

**Severidad: media. Coste del remedio: acotado.**

**Dónde:** `core/expedicion_certificada.py:2231-2237`.

La rama `hecho` reconstruye una ruta con el asunto actual y la devuelve sin comprobar existencia ni hash local. Tras borrar, mover o perder el PDF archivado, la cosecha sigue mostrando `ya estaba` y una ruta inexistente. Un cambio del asunto en origen también puede reconstruir una ruta diferente de la efectivamente escrita. La anotación acredita una subida previa, no la conservación de ambos artefactos que promete `CertificadoCosechado`.

**Reproducción:** `sondas.py::local_ausente`: cosecha correcta, borrado únicamente del PDF sintético, nueva cosecha. Resultado `ya_estaba=True`, `ruta_local.exists()==False`. No se pide otro certificado ni se avisa.

**Afirmación contradicha:** docstring de `CertificadoCosechado`, `2132`: «Un certificado ya archivado y colgado del expediente en el CRM».

**Remedio:** conservar la ruta real y el hash en el cierre; comprobar la copia local. Repararla a partir de una copia verificada o declarar la falta, sin repetir la subida CRM.

### H-08 — El control positivo de la barrera depende de una API key externa

**Severidad: media. Coste del remedio: trivial.**

**Dónde:** `tests/test_guard_cosecha_sin_red_ni_escritura.py:29-40`; orden de resolución en `core/sudespacho_documentos.py:222-223`.

El control llama `descargar_documento` sin cliente y espera `BarreraSudespachoViolada`, pero no fija una clave sintética. `_api_key()` se ejecuta antes del transporte parcheado. En un entorno sin clave se recibe `SudespachoDocumentosError` y el test falla sin alcanzar el instrumento que pretende probar.

**Reproducción:** `audit-guards/build_probe.py` elimina esa variable únicamente del entorno del subproceso y ejecuta el test con la fixture F2 literal: **1 failed** en `no-key.log`. Con una clave ficticia, el mismo control pasa. Las dos suites del ámbito verdes no demuestran hermeticidad frente a esta variable.

**Remedio:** `monkeypatch.setenv` con una clave sintética en el control, como ya hacen los tests del módulo documental. No necesita ninguna credencial real.

### H-09 — La barrera CRM deja sin cubrir la colección de tests

**Severidad: media. Coste del remedio: acotado.**

**Dónde:** `tests/conftest.py:182-195` y `tests/_barrera_sudespacho_documentos.py:68-78`.

La fixture de función se instala después de importar los módulos de test. Una llamada a la API pública en ámbito de módulo resuelve el transporte real antes de la barrera. El guard AST permite la llamada porque el test no necesita importar `httpx`. El inventario «Qué NO hace» de la barrera solo menciona el segundo import/puerta de red; no declara esta fase descubierta.

**Reproducción:** `audit-guards/mini/tests/test_collection_probe.py` llama `doc.descargar_documento("SYNTHETIC-ID")` durante colección. El verdadero `_cliente_real()` alcanza un módulo `httpx.py` local sintético que no abre sockets. El control acredita que la llamada se ejecutó, y los ocho guards más ambas sondas pasan: **10 passed**.

**Afirmación contradicha:** cabecera de la barrera: «ningún test alcanza el CRM real» y protección «independientemente de por qué camino se llegó». Se ha demostrado una fase no protegida, no una conexión real efectuada por los tests existentes.

**Remedio:** instalar protección antes de colección, mantenerla en ejecución y añadir este control positivo. La limitación del patrón heredado F1 no queda refutada: F2 la reproduce en un módulo capaz de escribir.

### H-10 — El guard de disco comprueba una keyword, no el destino de la escritura

**Severidad: media. Coste del remedio: acotado.**

**Dónde:** `tests/test_guard_cosecha_sin_red_ni_escritura.py:127-153` y premisa de su docstring `11-14`.

El AST detecta algunas construcciones de `EntornoExpedicion` sin `carpeta_certificados`, pero no comprueba que el valor esté bajo `tmp_path`. Un entorno con destino explícito equivocado, o modificado con `dataclasses.replace`, pasa. Además, la ausencia del puerto ya detiene el core en `2177-2183`: no existe el supuesto default a producción que el texto del guard dice impedir.

**Reproducción:** `audit-guards/mini/tests/test_disk_probe.py` sustituye el destino por `audit-guards/outside-test-tmp/`, fuera de `tmp_path` pero dentro del scratch de auditoría. Ejecuta la cosecha, verifica el PDF escrito allí y mantiene los ocho guards verdes. No se tocó un expediente real.

**Afirmación contradicha:** cabecera «nadie escribe en el árbol real» y «el único camino» del docstring. El control acredita presencia sintáctica parcial de un puerto, no confinamiento de escritura.

**Remedio:** comprobar durante ejecución el destino de PDFs y registros frente a la raíz sintética autorizada del test, con control positivo de raíz equivocada. Mantener el AST como apoyo, corrigiendo su alcance declarado.

## Controles que sí se sostienen y ventanas entre pasos

- `recibido_en` y `accedido_en` toman el mínimo del histórico y después el mínimo por requerido; el estado 20 cuenta también como recepción. El ejemplo M-1 del 14 frente al 17 queda cubierto por un test que pasa. H-04 afecta al titular de esas fechas, no a la operación `min`.
- El filtro exacto de `id_personalizado`, los estados desconocidos, la expedición vacía y el cajón de contactos que no coinciden tienen controles que pasan. Un contacto **ambiguo** es un caso distinto del contacto sin coincidencia.
- La razón social ajena mencionando ocho veces a la esperada **es rechazada** por el control negativo existente. El bloque acotado sí permite el otro valor. H-03 identifica la asimetría en la lectura de la cuenta.
- Los provisionales `id@codigo` y el definitivo `id` no se pisan en la secuencia probada; el test provisional → definitivo pasa y realiza dos subidas intencionadas de artefactos distintos. Una reserva abierta bloquea su propia clave si no se reencuentra. No declaro esa separación un duplicado defectuoso; no amplía la garantía a pérdida del registro, concurrencia o recuperación sin hash.
- El módulo documental usa el POST singular, pone el identificador en `origen_id`, envía el PUT sin API key CRM y verifica los bytes en el camino feliz. Los tests pasan. La desviación de H-02 está en la recuperación que hace el consumidor.

| Interrupción | Rastro y resultado observado en el código |
|---|---|
| Antes del PUT | No hay documento CRM; no se ha llamado al gancho. |
| PUT aceptado, respuesta perdida, o muerte antes del gancho | Puede haber bytes en S3 sin `origen_id` persistido. `sondas.py::s3_sin_reserva` reproduce esta ventana con timeout sintético tras aceptar el PUT. Un nuevo intento puede dejar otra copia S3. No equivale a dos documentos CRM, pues aún no se hizo POST. Limpieza/retención del objeto S3: SIN VERIFICAR. |
| Gancho persistido, antes del POST | Reserva abierta, documento ausente: la próxima cosecha para. Conservador, pero exige conciliación humana. |
| POST aplicado, respuesta perdida | Se conserva origen para buscar el documento. El momento del gancho sí cubre esta ventana. Reencontrarlo no basta para acreditar bytes: H-02. |
| Verificación fallida o muerte antes de cerrar | Misma reserva abierta. H-02 permite cierre posterior sin terminar la verificación. |
| Cierre escrito | Evita nueva subida con la misma raíz/cuenta/clave; no comprueba conservación local: H-07. |

Por tanto, `origen_id` **sí** se anota antes de crear el registro CRM, como promete la función, pero **no** antes de que exista un objeto S3. No atribuyo al autor una promesa de atomicidad entre todos los pasos que el contrato no contiene. No se simularon cortes eléctricos ni se verificó durabilidad física con `fsync`.

## Qué cambió de F1

Los cuatro campos nuevos de `EntornoExpedicion` se añaden al final con defaults `None`; las construcciones de F1 siguen funcionando. `cosechar` rechaza la falta de puertos explícitamente. La comparación AST de funciones/métodos preexistentes de `core/expedicion_certificada.py` encuentra **48 sin cambios y solo `entorno_real` modificado**; el método `primera_anotacion_de` es aditivo. En el CLI cambia `main`; los tres helpers preexistentes quedan iguales. `core/codicert.py`, la barrera Codicert F1 y su guard son idénticos entre árboles; `conftest` solo añade la fixture documental.

Las pruebas F1 incluidas en el ámbito pasaron junto con F2 en ambas semillas. No he encontrado que una de ellas haya pasado por una excepción nueva de la barrera documental en vez de su condición original. Esto no acredita toda F1 ni todas sus remediaciones dispensadas. H-05 señala una decisión heredada que afecta a F2, y H-06/H-09 muestran límites que el código/documentación de F1 ayudan a reconocer, sin darlos por resueltos por aquella dispensa.

## SIN VERIFICAR

1. **Producción Codicert y CRM, y las mediciones M-1 a M-10 como hechos externos.** Se contrastó su traducción a código; no se accedió a cuentas ni se descargaron certificados reales. No se reprodujeron latencias, credenciales disponibles, saldo, anatomía de PDFs reales ni el fallo del sandbox.
2. **Primera subida real de este módulo y relación efectiva con un expediente.** Solo HTTP y gestores sintéticos; no se creó ni borró ningún registro externo. Continúa pendiente la prueba sobre expediente de prueba que declara el plan.
3. **Regeneración del certificado cuando cambia el estado.** El diseño separa claves, pero no prueba que el PDF descargado como definitivo contenga ya ese estado. M-5 lo deja abierto; el docstring de `RegistroCosecha:862-867` lo enuncia como «se regenera» sin esta reserva. Debe conservarse la incertidumbre en la documentación, no tratar esa frase como medición.
4. **Validación criptográfica del PDF, identidad/CIF fuera de la razón social, integridad del contenido frente al envío y suficiencia jurídica.** El lector extrae texto; no se auditó confianza de firmas ni se contrastaron preceptos con fuentes legales externas. Las referencias legales del informe describen el contrato del autor, no un dictamen jurídico nuevo.
5. **Plazas distintas de Madrid, variaciones reales de plantilla y PDFs escaneados.** No había esos objetos probatorios en el encargo. El PDF de H-03 prueba el parser, no afirma que un certificado de producción concreto tenga ese asunto.
6. **Fallos físicos, máquinas distintas, renovación/pérdida de lease durante cosecha y todas las formas de corrupción del JSONL.** Se ejecutó la carrera determinista de dos hilos y se inspeccionó el contrato de exclusión; no es una prueba distribuida ni de durabilidad. `RegistroCosecha` valida JSON sintáctico, pero no toda la máquina de estados como `RegistroIntencion`; no se certifica cobertura de corrupción semántica.
7. **Toda la suite del repositorio y métricas de cobertura del diff.** Se ejecutó el ámbito pedido de 280 tests con dos semillas, no `session_close` ni la suite global. No se midió porcentaje de líneas/ramas ni se efectuó una campaña exhaustiva de mutaciones. Tampoco se corrió la suite de base-f1 por separado.
8. **Cobertura universal de las barreras.** H-09/H-10 amplían el inventario omitido. Las sondas de guards usan una copia mínima con la fixture F2 extraída literalmente, no todo `conftest`; la lectura del conftest completo confirma que esa barrera no se instala antes de colección. No se ensayaron todos los imports indirectos, otros clientes HTTP, subprocesos, recargas de módulos o escrituras por APIs distintas. No se afirma que los tests actuales hagan esas operaciones indebidas.
9. **F3 y las funciones expresamente excluidas por F2.** Aportable, manifiesto, aceptación entrante, cálculo de plazos, causa de cierre e idoneidad del canal no se implementan ni se verifican aquí. El discriminante textual del acta no queda acreditado como barrera de confidencialidad para F3 por pasar sus tests F2.

## Integridad del objeto al abrir y al cerrar

Algoritmo reproducible: SHA256 de los bytes originales de cada fichero, incluidos CRLF; luego SHA256 del manifiesto UTF-8 formado por líneas `ruta_relativa<TAB>sha256_hex<LF>`, ordenadas lexicográficamente por ruta con `/`. El objeto conjunto antepone `base-f1/` o `head/` a cada ruta. Incluye **todos** los ficheros de ambos árboles, no solo el diff; excluye directorios vacíos/metadatos de sistema de archivos. No es un hash de commit ni de un ZIP.

**SHA256 del objeto conjunto al abrir:**

`42d2124b930ba94d8306be26b643bce74a48a52122d62e1e703d10ddfa46935a`

**SHA256 del objeto conjunto al cerrar:**

`42d2124b930ba94d8306be26b643bce74a48a52122d62e1e703d10ddfa46935a`

| Árbol | Ficheros | SHA256 apertura | SHA256 cierre |
|---|---:|---|---|
| base-f1 | 1387 | `12c1f2a10ed59f42f696cf069651bdd651d738ae8e2b093c7e557511d748e135` | `12c1f2a10ed59f42f696cf069651bdd651d738ae8e2b093c7e557511d748e135` |
| head | 1401 | `12161f077d42dc0cb8c59af5f9a288580b89f22bb168c46725e8172b5d2b37d3` | `12161f077d42dc0cb8c59af5f9a288580b89f22bb168c46725e8172b5d2b37d3` |

`verificar_objeto.py` recalcula el cierre y exige igualdad completa de los manifiestos de apertura y cierre; `integridad.json` registra el resultado. Los árboles permanecen idénticos, incluidos sus inventarios de ficheros. Los ficheros de auditoría y temporales citados se crearon después del inventario inicial, fuera de ambos objetos.

NO-SHIP
<!-- informe-literal:fin:q7wk -->

## 2. Evidencia verificada por mí contra la fuente

**Los diez, confirmados.** Ninguno refutado. La adjudicación hallazgo por hallazgo, con
el remedio de cada uno, está en el **§11 del plan**
(`docs/superpowers/plans/2026-09-21-codicert-f2.md`), que es donde vive la decisión; aquí
queda la voz del revisor, que es lo que este acta existe para archivar.

**Lo que comprobé de la propia ronda, no de sus hallazgos:**

- El `sha256` del informe se computó **sobre el fichero terminado**: dos lecturas
  separadas del mismo fichero dieron el mismo digest, y el vigía esperó a la
  **terminación del revisor** (`-o _ultimo_mensaje.txt`), no a la aparición de
  `INFORME.md`. La R3 de P6 se perdió por confundir esas dos señales.
- El digest canónico del bloque literal **coincide con el `sha256` del `INFORME.md`
  original**, así que la cadena se verifica contra la salida del revisor y no solo
  contra sí misma.
- El revisor declaró la higiene de su workdir y no leyó el árbol `base/` que yo había
  montado contra la base equivocada y descartado.

**Dos falsos positivos de MI vigía, que conviene dejar escritos** porque el contrato de
`CLAUDE.md` los prohíbe en la dirección contraria y estos van en esta: declaró «MUERTE»
dos veces sobre un revisor vivo. La primera, porque `ps` de Git Bash no ve los procesos
de Windows; la segunda, porque mi patrón `^ERROR` casaba con la salida de **pytest que
el propio revisor estaba ejecutando** dentro del log. Un vigía que grita muerte sobre un
proceso vivo hace relanzar y tirar la ronda, que es simétrico de callar ante uno muerto.
La señal de vida que sí sirve en Windows es `tasklist`, y los patrones de fallo tienen
que ser los cuatro literales de Codex, no un `ERROR` genérico.
