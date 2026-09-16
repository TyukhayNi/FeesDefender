# Acta de la revision adversarial R1 - la corrida prepara y una sesion remata

> **Ronda:** R1 (unica). **Revisor:** Codex CLI (modelo `gpt-5.6-sol`, esfuerzo de razonamiento alto).
> **Fecha:** 2026-09-15.
> **Objeto:** el diff completo de la rama, base `480c1b69407659de1de3a5c0add5901d8d9e0077` ->
> head `673463f99be1c424b98dbc0f4a71ed9ced41bc37` (38 commits, 23 ficheros, 4.523 lineas).
> **Patron:** copia externa del arbol via `git archive`, fuera del repo; el revisor trabajo en
> solo lectura y escribio su informe en un directorio hermano. Verifico al cerrar que las copias
> seguian intactas: 1.361 ficheros identicos al head y 1.355 a la base, sin diferencias.
> **Veredicto del revisor:** `NO-SHIP` - 0 criticos, 2 importantes, 6 menores.
>
> **sha256 del objeto revisado (`DIFF.patch`):**
> `d7d0a3e6d56d98b0195bf616ca495bdd310698fb9235eee879ac243d3009d5fd`
> **sha256 de este informe, tal como el revisor lo entrego:**
> `a4717ba336c3c08cf4f8cb788e06e43a239ca5180277c0df23b8d0a7513205df`
> (el revisor reporto ese mismo numero en su mensaje de cierre, asi que el informe que sigue
> es el que el escribio, sin editar)
>
> **Que es este fichero.** El informe **literal** del revisor. La **adjudicacion** -que confirme,
> que refute y que hice con cada hallazgo- vive embebida en el spec
> [`2026-09-15-corrida-prepara-sesion-remata-design.md`](2026-09-15-corrida-prepara-sesion-remata-design.md),
> que es el documento que la decision modifico. Esta acta existe para que cualquiera pueda
> contrastar **que dijo el revisor** con **que decidi yo que dijo**.
>
> **La ronda corrio de verdad**, y eso importa para leer su peso: 285 tests focales con las dos
> semillas, la suite completa, sondas de JSON, cinco mutantes propios y un servicio de Gmail
> sintetico. Descarto ademas 20 rojos de la suite completa reproduciendolos **sobre la base**:
> son ambientales (rutas largas del laboratorio, venv ausente, copia sin `.git`), no del diff.

---

# Revisión adversarial R1 — La corrida prepara y una sesión remata

## 1. Cobertura

Examiné el diff completo (23 ficheros, 4.523 líneas), los 38 mensajes de commit, el spec y el plan del 2026-09-15. Leí en contexto el productor y validador de viabilidad, el consumidor del JSON, las nuevas etapas, la validación de flags y el cierre de la secuencia. Contrasté los tests modificados con la base, el registro de protocolo y los contratos de `ExportReport`, `NuevoColaborador` y `_colaborador_de`. Revisé también las modificaciones de documentación, encoding y marcadores de tests.

No ejecuté Gmail, CRM ni Drive reales, OCR pesado, el despliegue de la skill en Cowork ni una sesión jurídica que rematase un expediente. No consulté expedientes reales ni la blocklist privada. No comprobé enlaces duros sobre el sistema de archivos de Drive for Desktop, ni resistencia a un corte eléctrico. No ejecuté dos semillas de la suite completa ni todo el arnés histórico de mutaciones.

Los árboles recibidos se trataron como entradas de solo lectura. Las ejecuciones se hicieron en `informe/ejecucion/` y `informe/ejecucion-base/`, copias propias, con bytecode y caché de pytest desactivados y temporales fuera de esos árboles. Las mutaciones fueron en memoria. La comparación posterior de contenido dio **1.361 archivos idénticos al head y 1.355 idénticos a la base**, sin diferencias (`copias.log`). No se modificó código del objeto revisado.

## 2. Ejecución y resultados

Intérprete: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe` (Python 3.14.4).

| Ejecución | Resultado | Evidencia local |
|---|---|---|
| Los 11 módulos de tests tocados, semilla 777 | **285 passed**, 34,56 s | `pytest-focal.log` |
| Los mismos, semilla 31337 | **285 passed**, 45,22 s | `pytest-focal-31337.log` |
| Suite completa del head, semilla 777, `-n auto` | **20 failed, 5692 passed, 91 skipped, 10 xfailed, 10 errors**, 249,37 s | `pytest-suite-777.log` |
| Cinco módulos que concentraron los rojos, sobre la base | **19 failed, 88 passed, 10 errors** | `pytest-base-comparacion.log` |
| Rojo restante sobre la base, con profundidad de temporal equivalente a xdist | **1 failed**, mismo aserto | `pytest-base-extra-correcto.log` |
| Sondas de JSON y lectura de celdas | Pérdida silenciosa, excepción de residuo y tipos aceptados incompatibles, reproducidos | `sondas.py`, `sondas.log`, `resultados-sondas/` |
| Mutaciones del contrato y de escritura de celdas | Cuatro ampliaciones unilaterales sobreviven; **58 tests pasan** sin escribir los tres valores derivados en INFORMACION | `mutantes.py`, `mutantes.log` |
| Exportador real con servicio Gmail sintético sin etiquetas | La etapa declara `hecha` sin etiqueta resuelta | `sonda_email.py`, `sonda-email.log` |

**Los rojos de la suite completa no se atribuyen al diff.** Los 20 fallos y 10 errores se reprodujeron sobre la base: rutas del laboratorio demasiado largas (`Filename too long` y presupuestos de 247 unidades UTF-16), ausencia del venv esperado y ausencia de `.git`. El fallo restante de `test_la_excepcion_alcanza_una_skill_anidada` reaparece en la base al igualar la profundidad del temporal. Un primer intento de esta última reproducción falló al preparar `basetemp` por no haber creado su padre; no lo conté como evidencia y se conserva en `pytest-base-extra.log`.

Los 91 skips y 10 xfails son los aplicados por la suite existente; **el diff no añade `pytest.mark.skip`, `pytest.mark.xfail` ni `importorskip`**. Entre los skips hay pruebas lentas, Ollama, corpus privado, blocklist y despliegue. Los guards basados en `git ls-files` no acreditan el contenido versionado en una copia sin `.git`, aunque algunos terminen verdes.

Comandos reproducibles, desde este directorio; `$py` designa el intérprete anterior:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$py='C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe'
$focal=@(
  'tests/test_abrir_caso_cli.py', 'tests/test_abrir_caso_modo_v1.py',
  'tests/test_abrir_caso_v2_autorizacion.py', 'tests/test_apertura_v1_cableado.py',
  'tests/test_apertura_v1_costuras.py', 'tests/test_apertura_v1_e2e.py',
  'tests/test_apertura_v1_email.py', 'tests/test_apertura_v1_viabilidad.py',
  'tests/test_intake_control_por_ubicacion.py',
  'tests/test_render_informe_viabilidad.py', 'tests/test_viabilidad_json.py'
)
Push-Location ./ejecucion
& $py -m pytest -p no:cacheprovider --basetemp ../tmp-focal --randomly-seed=777 --tb=short @focal
& $py -m pytest -p no:cacheprovider --basetemp ../tmp-focal-31337 --randomly-seed=31337 --tb=short @focal
& $py -m pytest -p no:cacheprovider --basetemp ../tmp-suite-777 --randomly-seed=777 -n auto --tb=short
Pop-Location
& $py ./sondas.py
& $py ./sonda_email.py
& $py ./mutantes.py
& $py ./auditoria.py
& $py ./comprobar_copias.py
```

`sondas.py` crea salidas deliberadamente no sobrescribibles: para repetirlo hay que usar otro directorio de resultados. La comparación de base utilizó los módulos `test_procedimiento_informe.py`, `test_procedimiento_mapa.py`, `test_session_close_no_pude_medir.py`, `test_precommit_leak_guard.py` y `test_gitignore_no_inerte.py`, con semilla 777 y `--basetemp ../tmp-base-comparacion`. La reproducción adicional utilizó `--basetemp ../tmp-baseX-777/popen-gw7` con su padre precreado.

## 3. Tabla de hallazgos

Todos los siguientes están confirmados; las limitaciones y sospechas se separan más abajo. Las líneas se refieren a `objeto-head/`.

| ID | Hallazgo | Severidad | Coste del remedio |
|---|---|---|---|
| H-01 | Un residuo de tipo incorrecto rompe la secuencia sin devolver un estado | **importante** | **acotado** |
| H-02 | El aviso de claves desconocidas sigue dejando tres objetos anidados en silencio | **importante** | **acotado** |
| H-03 | El validador acepta valores anidados que el consumidor no puede escribir | menor | acotado |
| H-04 | El candado entre contratos solo comprueba una dirección | menor | trivial |
| H-05 | El test de integración del productor no verifica los datos derivados en las celdas | menor | acotado |
| H-06 | La traducción de `ExportReport` confunde ausencia de etiqueta con trabajo hecho y pierde pendientes manuales | menor | acotado |
| H-07 | El runbook promete saltar el correo ante flags ausentes que el CLI rechaza | menor | trivial |
| H-08 | El plan conserva conteos y una explicación del orden de validación ya desmentidos | menor | acotado |

No encontré un hallazgo crítico confirmado.

## 4. Hallazgos detallados

### H-01 — `_residuo.campos` puede abortar la apertura fuera del protocolo

**Dónde:** `scripts/abrir_caso.py:1309`, `_pendiente_de_viabilidad_existente`, especialmente el `join` de la línea 1340; llamada desde la rama de fichero existente de `etapa_viabilidad`. `core/apertura_v1.py::secuenciar` no captura la excepción de `etapa.correr()`.

**Qué falla:** se comprueba que el JSON y `_residuo` sean diccionarios, pero no que `campos` sea una lista de cadenas. Un JSON editable por la sesión con `"campos": [1]` o `"campos": 1` pasa `json.loads` y llega a `join`. Esta lectura queda fuera del `try` que traduce los errores de escritura. La etapa no devuelve `saltada`/`fallo` con pendiente y no se ejecuta `verificar`. En el flujo de `main`, tampoco se alcanza el registro normal de cierre de la ronda. Con `"campos": "hitos"` no aborta: inventa cinco pendientes, uno por letra.

**Comprobación:** `& $py ./sondas.py`, con JSON sintético ya existente y secuencia real de dos etapas:

```text
lista_numero validar= []
secuencia EXCEPCION= TypeError sequence item 0: expected str instance, int found
entero validar= []
secuencia EXCEPCION= TypeError can only join an iterable
cadena validar= []
... faltan h, i, t, o, s.
```

**Propiedad sin proteger:** §5.4 del spec: los desenlaces de la etapa se expresan mediante estado y pendiente; un fichero preexistente ilegible o incoherente no debe romper la corrida. El test actual solo corrompe la sintaxis JSON, no los tipos del contenido.

**Remedio:** validar la forma de `campos` al leer el fichero existente y devolver un pendiente de contenido no interpretable. Es un arreglo local del lector, con casos de lista mixta, escalar y cadena; no requiere modificar el JSON ajeno ni verificar jurídicamente su contenido.

### H-02 — Persisten claves descartadas sin aviso dentro de hitos, respuestas y avisos

**Dónde:** `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py:94`, `avisa_de_claves_ajenas`; lectores de subcampos en líneas 246, 286 y 297.

**Qué falla:** el recorrido añadido cubre el primer nivel, `equipo`, `importes` y `actividades`. Las claves de cada valor de `hitos`, cada respuesta de `preguntas` y cada objeto de `avisos` siguen entrando por `.get()` sin aviso. Reconocer el identificador del hito o de la pregunta no comprueba las claves de su contenido. Es la misma asimetría que el spec §5.1 promete cerrar para todo el fichero.

**Comprobación:** `sondas.py` envía `hitos.ENCARGO.scrore=3`, una pregunta de la plantilla con `respueta="RESPUESTA CANARIO"` y `avisos=[{"avios":"AVISO CANARIO"}]`. Lee el libro resultante:

```text
claves_anidadas validar= [] error= None
stdout= ['OK · Informe generado: ...'] stderr=
celdas: {'hito_F26': None, 'respuesta': None, 'aviso_D5': None}
```

**Propiedad sin proteger:** toda clave desconocida debe avisarse; el éxito del render no debe ocultar que se perdió una valoración, respuesta o aviso enviado por la sesión. El defecto de descarte precede al diff, pero el remedio general que este añade y anuncia sigue sin cubrirlo. No se acusa que el render deba rellenar esos datos por su cuenta.

**Remedio:** extender localmente el recorrido del consumidor a las claves de esos objetos, manteniendo los formatos de hito escalar que ya admite. Probar claves equivocadas y conocidas con valores no vacíos y lectura de celdas. No exige importar el core en Cowork.

### H-03 — `validar` acepta JSON no consumible dentro de los objetos

**Dónde:** `core/viabilidad_json.py:78`, `validar`, y `_problemas_de_importes`.

**Qué falla:** los tipos se comprueban en primer nivel y las claves de algunos objetos, pero no sus valores. `{"importes":{"precio":{"cantidad":12000}}}` se considera válido; `escribir` usa precisamente ese criterio como permiso para persistirlo.

**Comprobación:** `sondas.py` pasa ese valor sobre un JSON preparado válido y ejecuta el consumidor:

```text
tipo_anidado validar= [] error= ValueError: Cannot convert {'cantidad': 12000} to Excel
```

**Propiedad sin proteger:** la declaración de que la validación previa evita persistir entradas incompatibles con el consumidor. El camino actual de `preparar` solo genera objetos vacíos y no activa este defecto; por eso lo clasifico como menor, no como fallo de toda apertura.

**Remedio:** validar los tipos admitidos de los valores anidados que se escriben en celdas, con tests de rechazo. Debe conservarse la flexibilidad deliberada del consumidor; no convertirlo en una validación jurídica ni exigir campos que hoy son opcionales.

### H-04 — El test que ata los contratos no detecta ampliaciones solo del consumidor

**Dónde:** `tests/test_render_informe_viabilidad.py:818`, `_contrato_cumplido`.

**Qué falla:** comprueba pertenencia de cada clave del core en la skill, no igualdad de conjuntos. Su docstring promete detectar un campo añadido «en uno y no en el otro», pero solo muerde al faltar en el consumidor. También omite `MARCA` de la comparación de primer nivel.

**Comprobación:** `& $py ./mutantes.py`. El contrato original pasa; se añade en memoria `CLAVE_NUEVA_SOLO_CONSUMIDOR`, por separado, a `CAMPOS_CONOCIDOS`, `CLAVES_IMPORTES`, `CLAVES_EQUIPO` y `CLAVES_ACTIVIDADES`. En los cuatro casos `_contrato_cumplido()` sigue pasando:

```text
CONTROL contrato original: PASS
MUTANTE CAMPOS_CONOCIDOS + clave exclusiva consumidor: SOBREVIVE
MUTANTE CLAVES_IMPORTES + clave exclusiva consumidor: SOBREVIVE
MUTANTE CLAVES_EQUIPO + clave exclusiva consumidor: SOBREVIVE
MUTANTE CLAVES_ACTIVIDADES + clave exclusiva consumidor: SOBREVIVE
```

**Propiedad sin proteger:** sincronía bidireccional de las constantes repetidas entre entornos. No afirmo que hoy sus conjuntos difieran.

**Remedio:** dos comparaciones de conjuntos: `set(vj.CAMPOS) | {vj.MARCA}` igual al registro de primer nivel, e igualdad en el bucle de las tres colecciones de subclaves. Añadir control de ampliación unilateral.

### H-05 — El test de integración puede pasar perdiendo todos los valores derivados visibles

**Dónde:** `tests/test_render_informe_viabilidad.py:717`, `test_el_json_que_produce_preparar_corre_de_verdad`.

**Qué falla:** solo exige `salida.exists()`. El test de `precio` sí lee H13, pero introduce ese dato aparte: no comprueba que los datos derivados de `preparar` lleguen a la salida. El spec §5.6 exige lectura de celdas justamente para no confundir crear el archivo con trasladar el dato.

**Comprobación:** `mutantes.py` sustituye `set_cell` en memoria para que omita exclusivamente INFORMACION!E4, E5 y E11, conservando todo lo demás. Corre todo el módulo de tests del render:

```text
58 passed in 64.25s (0:01:04)
MUTANTE EXIT= 0
```

La sonda sin mutación verificó que el código actual sí escribe `2026-09-15`, `W-TEST01` y `Vuelta` en esas celdas. **El hallazgo es de cobertura; no de pérdida actual de esos tres datos.**

**Propiedad sin proteger:** integración por resultado entre productor y consumidor para fecha, referencia y observaciones. `case_id` tiene además un papel distinto en el nombre automático de salida, que los tests con `--salida` explícito no ejercitan.

**Remedio:** leer y afirmar E4/E5/E11 con valores canario en el test de integración; probar por separado el nombre derivado si se desea cubrir también `case_id`.

### H-06 — `ExportReport` contiene más estados que los que traduce la nueva etapa

**Dónde:** `scripts/abrir_caso.py:796`, traducción final de `etapa_email`; contrato real en `core/email_export.py:1118` y retorno sin etiqueta alrededor de la línea 1246.

**Qué falla:** toda devolución normal del exportador se convierte en `hecha`, incluso `label_id=None` por etiqueta inexistente. El pendiente afirma «El export escribió» con cero mensajes y sin haber encontrado la fuente. Además, `links_manual` puede indicar trabajo pendiente con `errors=[]`; en ese caso la etapa no añade ningún pendiente.

**Comprobación:** `& $py ./sonda_email.py`. Para la etiqueta inexistente corre `export_label` real con un servicio sintético que devuelve cero etiquetas:

```text
label_id= None written= 0 errores= 1
etapa= hecha detalle= etiqueta 'ETIQUETA_INEXISTENTE': 0 de 0 mensajes escritos
corrida= preparado_con_pendientes se_ejecuta_siguiente= True
```

Para `links_manual=1`, se inyecta un `ExportReport` real de esa forma:

```text
enlace_manual: estado= hecha pendientes= () detalle= etiqueta 'L': 1 de 1 mensajes escritos
```

El estado manual es alcanzable: `_rescata_file` incrementa `links_manual` y retorna sin añadir `errors` cuando no puede obtener los metadatos o descargar el enlace. Esta rama se contrastó por lectura; no se llamó a Drive real.

**Propiedad sin proteger:** la etapa debe trasladar lo que se hizo y lo que requiere intervención. No se pierde toda evidencia: la etiqueta inexistente aparece en el pendiente de error y los enlaces conservan su traza en el exportador. Esa observabilidad parcial limita la severidad a menor.

**Remedio:** distinguir fuente no resuelta de exportación parcial y etiqueta legítimamente vacía; traducir pendientes manuales relevantes. No usar simplemente `written == 0` como fallo: también puede ser una repetición idempotente.

### H-07 — Flags ausentes: el runbook dice `saltada` donde el CLI aborta

**Dónde:** `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:245`, añadido en este diff.

**Qué falla:** al explicar `--fuente email`, `--cuenta` y `--label`, dice «sin los tres la etapa email sale saltada, no falla». Con `--fuente email` y falta de cuenta o etiqueta, `validar_modo` devuelve error antes de alcanzar la etapa. El propio runbook describe correctamente esa validación más abajo.

**Comprobación:** lectura cruzada con `scripts/abrir_caso.py::validar_modo`; los casos de ausencia de cuenta y label se ejecutaron en `test_email_sin_cuenta_o_sin_label_se_rechaza_EN_validar_modo`, dentro de las dos suites focales verdes.

**Propiedad sin proteger:** que el operador distinga no solicitar correo de solicitarlo con argumentos incompletos.

**Remedio:** precisar en una frase que no pedir correo permite `saltada`, mientras que `--fuente email` exige ambos flags y aborta si faltan.

### H-08 — El plan conserva premisas incorrectas en sus bloques ejecutables

**Dónde:** `docs/superpowers/plans/2026-09-15-corrida-prepara-sesion-remata.md:107`, `:421-423` y `:606`.

**Qué falla:** siguen escritos «4 de los 11 campos», «Los cinco defectos […] publicados» y que `_validar_flags` corre después de `ensure_case` y deja el esqueleto creado al abortar. Las secciones corregidas del mismo plan dicen doce campos, cuatro defectos y validación anterior a `ensure_case`. Los bloques no están identificados como ejemplos obsoletos que no deban ejecutarse.

**Comprobación:** `& $py ./auditoria.py` localiza esos tres pasajes. Contrasté `CAMPOS` (12), la tabla del contrato base de #262 y el orden real de `main`: `_validar_flags` precede al mutex y a `ensure_case`.

**Propiedad sin proteger:** consistencia del contrato de implementación que el encargo pide usar como fuente. No altera el resultado del código actual y no es motivo autónomo para bloquear el merge.

**Remedio:** corregir los tres pasajes del plan, conservando la explicación normativa. La corrección no exige eliminar el historial del razonamiento.

## 5. Tests ajenos modificados: conservación de sus propiedades

| Fichero | Cambio y evaluación |
|---|---|
| `test_abrir_caso_modo_v1.py` | Retirar `email` del parámetro de fuentes ajenas responde al alcance autorizado; quedan `manual` y `whatsapp`. Cambiar `email` por `manual` conserva el test de acumulación de dos errores. El otro conteo pasa de cinco a seis por las dos exigencias nuevas de correo. No encontré debilitamiento. |
| `test_abrir_caso_v2_autorizacion.py` | El renombrado de tres a cuatro etapas conserva el test. El aserto literal de `ETAPAS_V1` más el prefijo relacional y la cola literal fijan la composición nueva; no queda solo una identidad tautológica. |
| `test_apertura_v1_cableado.py` | `no_ejecutadas == ETAPAS_V1[1:]` protege que se enumeren todas las etapas posteriores a la parada sobre la composición vigente; la composición está fijada independientemente. |
| `test_apertura_v1_costuras.py` | Ampliar la firma explícita del doble permite los nuevos argumentos; permanece el aserto de que `hasta` llega al secuenciador. |
| `test_apertura_v1_e2e.py` | Se conserva la comparación de orden y se fijan los ocho estados por nombre. Siguen los contadores de invocaciones reales a los límites y las comprobaciones de bloqueo/parada. Añadir `tipo_caso` al doble permite ejecutar la etapa real de viabilidad; no la sustituye. |
| `test_abrir_caso_cli.py`, `test_intake_control_por_ubicacion.py`, `test_render_informe_viabilidad.py` | Añaden casos sin retirar los existentes. Hay huecos nuevos de cobertura del contrato y del dato renderizado, H-04/H-05, pero no eliminación de pruebas previas. |

El único nombre de test antiguo desaparecido en el barrido AST es `test_las_tres_etapas_nuevas_estan_y_en_orden`, sustituido por su versión de cuatro. No encontré snapshots cambiados ni nuevas excepciones a guards. Los tests añadidos escriben sus fixtures y salidas en temporales o utilizan dobles; la plantilla real solo se lee.

## 6. Lo que intenté refutar y NO pude

- **Cableado alcanzable del correo.** Los tests del CLI recorren `--modo v1 --fuente email` con identidad, cuenta, etiqueta y Drive, hasta observar ambas etapas `hecha`. Se verifica también la derivación de `team_id` y el viaje de `--no-extraer-adjuntos` hasta el exportador. No encontré una función nueva sin llamador en ese recorrido.
- **Conservación de las puertas.** `manual` y `whatsapp` siguen rechazadas en V1; `--hasta email` es válido; el correo precede a sala de máquina, y viabilidad precede al verificador. El permiso de CRM sigue siendo explícito e independiente del correo.
- **No sobrescritura del JSON en el disco local de prueba.** Pasaron los tests con destino previo, con creación concurrente entre el chequeo y la publicación, con escritura que falla tras depositar bytes y con fallo de `os.link`. Comprobaron contenido y restos, no solo excepciones. No conseguí refutar esas garantías ante fallos interceptables sobre este sistema de archivos.
- **Separación entre protocolo y documental.** `_viabilidad.json` y sus temporales se excluyen en raíz; el homónimo dentro de un lote sigue siendo documento. El registro se incorpora a los consumidores mediante el mecanismo existente y los tests de ubicación pasan.
- **Los dos hechos del spec.** La comparación del contrato base con los accesos del consumidor respalda cuatro campos incorrectos, no cinco. El código actual del colaborador respalda la ausencia de rol/lado en el dato de apertura; no repetí el muestreo histórico de diez fichas reales. Los grupos/usuarios de permisos del modelo no son roles comerciales.
- **Preparación limitada y explícita.** El JSON actual contiene doce campos de negocio: cuatro derivados, siete en residuo y `bitacora_inicial=True`. No inventa equipo, hitos ni respuestas. La sonda leyó los valores derivados correctos en E4/E5/E11. La falta de sala de lectura automática, una décima comprobación del JSON y el clasificador LLM no son hallazgos: están fuera de alcance.
- **Encoding y prosa.** Los 23 archivos modificados decodifican como UTF-8 sin BOM; no encontré los patrones de mojibake buscados. En los cambios de documentación leídos se conserva la condición histórica de promoción y la alternativa descartada de ubicación del JSON. No identifiqué una supresión normativa encubierta ni terminología nueva de partes contraria a propietario/buscador.

## 7. Reservas y sospechas no convertidas en hallazgos

1. **Publicación mediante enlaces duros.** La pieza depende de `os.link`. Los tests solo acreditan el disco local del laboratorio. No verifiqué soporte en Drive for Desktop, ni durabilidad ante pérdida de alimentación; no hay `fsync` en la escritura. No presento como comprobada la promesa absoluta del docstring ante corte eléctrico, ni como defecto confirmado una incompatibilidad con el Drive del despacho.
2. **Despliegue del consumidor.** `PLAN.md` declara pendiente empaquetar/reimportar la skill. El cambio de versión en el repo no demuestra que Cowork ya ejecute estos avisos. Es deuda declarada, no un despliegue verificado por esta ronda.
3. **Higiene de fixtures heredados.** Las adiciones de `test_abrir_caso_cli.py` reutilizan una identidad y un rótulo de carpeta asociados a W-02Z2NR que ya estaban en fixtures de la base. No pude certificar si los literales descriptivos son sintéticos o reales; la blocklist privada no está disponible y su test se salta. No certifico ausencia de PII ni atribuyo procedencia real por apariencia. La adjudicación debe comprobar ese origen sin copiar esos literales al acta.
4. **Arnés histórico de mutaciones.** No ejecuté `tests/_mutantes_plan5.py` completo; su cobertura no se da por satisfecha con los cinco mutantes propios de esta ronda.

## 8. Objeto y veredicto

- Base: `480c1b69407659de1de3a5c0add5901d8d9e0077`.
- Head: `673463f99be1c424b98dbc0f4a71ed9ced41bc37`.
- Objeto revisado: `../DIFF.patch`.
- **SHA-256 de los bytes de `../DIFF.patch`:** `d7d0a3e6d56d98b0195bf616ca495bdd310698fb9235eee879ac243d3009d5fd`.

Antes de mergear deben cerrarse H-01 y H-02: el primero rompe el protocolo de la corrida al releer un archivo manual; el segundo deja vigente pérdida silenciosa de contenido dentro de la frontera que este diff promete proteger. Los rojos ambientales de la suite completa no fundamentan este veredicto. Los demás hallazgos pueden adjudicarse por separado según su coste y deuda aceptable. La adjudicación corresponde a Claude contra la fuente.

NO-SHIP
