---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-08-25-apertura-v1-plan2-mutex.md
objeto_rev: "1"
commit: 13542e0
ronda: "10"
revisor: Codex
veredicto: NO-EJECUTABLE
marcador_nonce: p9xr
sha256_informe: f896aaf988682d43cd6bdc15db2b7ef379ad1fd35b3b38f4806d4a16b3d989ab
adjudicado_en: docs/superpowers/plans/2026-08-25-apertura-v1-plan2-mutex.md §0
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R10.** El §1 conserva literalmente la voz del revisor. La
> adjudicación vive en el **§0 del plan**, no aquí. El acta existe porque yo soy la parte
> revisada: sin el original archivado nadie puede contrastar **qué dijo el revisor** con
> **qué decidí yo que dijo**.
>
> **Qué se revisó:** la **rev. 1 del Plan 2**, un plan TDD **sin ejecutar**. Ninguna línea de
> su código existía. Se corrió antes de escribirlo, que es donde una ronda es más barata.
>
> **Lo que encontró, en una frase.** Que el test que el plan presentaba como su prueba
> rigurosa —dos procesos reales compitiendo— **pasaba en verde con la exclusión entera
> eliminada**, y el revisor lo ejecutó para demostrarlo. Once hallazgos, once confirmados.
>
> **Limitación declarada por el revisor:** no pudo ejecutar el módulo ni sus tests, porque no
> existen, ni instalar dependencias. Sus comprobaciones ejecutables las hizo sobre **arneses
> efímeros equivalentes**, y él marca como SIN VERIFICAR todo lo que dependía del código real.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:p9xr -->
# R10 — revisión adversarial del Plan 2 (mutex de la apertura V1)

**Veredicto:** NO EJECUTABLE
**Hallazgos:** 11 (4 críticos, 2 altos, 3 medios, 2 bajos)
**Qué pude ejecutar:** inspección numerada del plan, la spec y el fuente con `Get-Content`/`Select-String`; búsqueda de imports y requisitos; arneses efímeros con Python 3.14 para reloj, ausencia del guard, rutas y bloqueo nativo de Windows. Salida relevante:

```text
Python 3.14.7
ModuleNotFoundError: No module named 'filelock'

sin_guard_test_principal= PERDEDOR
sin_guard_control_negativo= GANADOR

aware-minus-naive= 7200.0
lease_naive_expired_at_same_wall_Z= True
lease_negative_expired_after_1s= True
lease_zero_expired_after_1s= True

child_unlink: PermissionError [WinError 32] (el .guard estaba bloqueado)
second_fd_same_process_acquired= False
error= PermissionError: [Errno 13] Permission denied

W-TEST01       -> C:\safe\workspaces\W-TEST01.lock
..\escape      -> C:\safe\ESCAPE.lock
C:\tmp\escape -> C:\tmp\ESCAPE.lock

xfail_count=6
test_defecto_doble_titular
test_defecto_rollback_cancela_un_lock_ajeno
línea 305: A-2c — RETIRADO el 2026-08-25: el defecto está ARREGLADO.
```

La búsqueda de `filelock`/`psutil` en `requirements.txt` y de imports Python de ambos en el árbol produjo salida vacía. `WorkspaceRegistry.cargar()` sí está en `workspace_registry.py:183-192` y recorre exclusivamente `*.json`. La tabla extensible de errores está en la spec dual, no en la spec de apertura: `2026-07-29-feesdefender-dual-case-workspace-design.md:719-746` dice «Como mínimo».

También inspeccioné el fuente oficial de las dependencias. `filelock` 3.29.0 documenta una API recursiva por instancia, y su backend Windows abre con `O_CREAT|O_TRUNC` y bloquea con `msvcrt`, no con `O_EXCL` ([advisory y fuente del proyecto](https://github.com/tox-dev/filelock/security/advisories/GHSA-w853-jp5j-5j7f)). El changelog de `psutil` posterior a 7.2.2 registra arreglos Windows para fluctuación entre llamadas/procesos y para suspensión/hibernación ([changelog oficial](https://github.com/giampaolo/psutil/blob/master/docs/changelog.rst)).

`rg` no estaba disponible (`The term 'rg' is not recognized`), por lo que usé las herramientas nativas de PowerShell. Dos primeros intentos auxiliares no produjeron evidencia por errores de sintaxis del propio arnés (un pipeline PowerShell y una cadena `python -c`); ambos se repitieron corregidos y las salidas válidas son las anteriores.

**Qué NO pude verificar, y por qué:** **SIN VERIFICAR** la ejecución del módulo y de sus tests: por definición aún no existen y el Python disponible no tiene `filelock` ni `psutil`; no forcé una instalación ni `pytest`. **SIN VERIFICAR** dinámicamente el backend de la versión que acabaría resolviendo `filelock>=3.12` o `psutil>=5.9`; el plan no fija esas versiones y el entorno no trae el venv citado. **SIN VERIFICAR** un corte real de proceso exactamente entre `os.replace` y la salida del guard: no existe aún el módulo que habría que matar. El análisis estático indica que ese corte dejaría el estado publicado y el bloqueo nativo se soltaría al morir, pero no lo declaro probado. **SIN VERIFICAR** los cambios reales de `psutil.boot_time()` tras hibernación o ajuste de hora en este PC: no era seguro alterar el reloj/suspender la máquina durante la revisión.

## Hallazgos

### H10-01 — La supuesta prueba concurrente queda verde sin ninguna exclusión atómica [CRÍTICO]
**Dónde:** Task 7, plan:730-799; en especial `test_de_dos_procesos_solapados_entra_EXACTAMENTE_uno`, plan:774-783.

**Qué está mal:** el padre termina `adquirir()` en la línea 779 y solo después crea al hijo. Cuando el hijo arranca, la sección crítica `leer → decidir → escribir` del padre ya terminó: nunca hay dos adquisiciones compitiendo. El test solo comprueba que un estado ya publicado y con lease vivo produce `CaseBusy`. El control negativo solo descarta una implementación que rechace siempre. La mutación prescrita en plan:799 elimina `raise CaseBusy`, pero no elimina ni rompe `_guard`, por lo que tampoco aísla la propiedad decisiva. Ejecuté el mismo montaje con el guard sustituido por nada y obtuve exactamente las dos salidas esperadas por el plan: `PERDEDOR` y luego `GANADOR`.

**Por qué importa:** una implementación sin guard —dos procesos leen ausencia, ambos deciden libre y ambos escriben— superaría todos los tests propuestos. Esa es la carrera que permite dos escritores y es la única que la primitiva debe impedir.

**Cómo se comprueba:** sustituir `_guard` por `contextlib.nullcontext()` y correr los dos tests propuestos: deben seguir verdes. Añadir después dos hijos liberados por una barrera común y un hook determinista justo después de `leer_estado`; ambos tienen que observar `None` en el mutante y el test debe exigir un solo retorno exitoso. El mutante sin guard solo queda muerto si esa nueva prueba falla por dos ganadores.

### H10-02 — Un timestamp naïve o un `ahora` futuro roba un lease vivo [CRÍTICO]
**Dónde:** `adquirir`, plan:469-487; `_a_epoch`/`_caducado`, plan:573-592; tests del Task 5, plan:520-553.

**Qué está mal:** la API persiste cualquier cadena `ahora` y `_a_epoch` acepta fechas sin zona. `datetime.timestamp()` interpreta un datetime naïve en la zona local. En este entorno (Europe/Madrid), `2026-08-25T12:00:00` y `2026-08-25T12:00:00Z` difieren en 7.200 segundos; con el lease por defecto, el segundo proceso considera vencido de inmediato el lock naïve del primero. No hay validación de zona, UTC, proximidad al reloj autorizado ni monotonicidad de una renovación. Un llamador también puede pasar deliberada o accidentalmente un `ahora` aware muy futuro y hacer caducar el estado ajeno.

**Por qué importa:** el primer proceso sigue ejecutando después de que el segundo sobrescriba el estado y entre: exclusión mutua rota.

**Cómo se comprueba:** adquirir con `ahora="2026-08-25T12:00:00"` y lease 300; sin liberar, adquirir desde otro proceso con `ahora="2026-08-25T12:00:00Z"`. En Madrid el segundo no debe entrar. Añadir casos para renovación que retrocede, zona ausente y `ahora` futuro. La frontera debe rechazar timestamps sin offset y definir quién suministra el reloj de producción, no confiar en cualquier cadena del llamador.

### H10-03 — `lease_seconds` cero, negativo o truncado permite dos titulares [CRÍTICO]
**Dónde:** firma y serialización de `adquirir`, plan:469-487; cálculo de vencimiento, plan:586-592.

**Qué está mal:** no se exige un entero positivo y finito. `int(lease_seconds)` acepta `0`, negativos, booleanos y trunca flotantes (`0.5 → 0`). Un primer proceso recibe nonce y continúa normalmente con `-1`; un segundo, un segundo después, calcula el estado como vencido y lo sustituye. El `except` de `_caducado` no interviene porque el estado es perfectamente parseable.

**Por qué importa:** dos procesos pueden operar a la vez mediante un valor que la propia API pública admite y persiste.

**Cómo se comprueba:** parametrizar `lease_seconds` con `0`, `-1`, `0.5`, `True`, `"60"` y valores no finitos; exigir `TypeError`/`ValueError` antes de escribir para todo lo que no sea `int` positivo (decidiendo expresamente si `bool` se rechaza). Con `-1`, mantener vivo al primer hijo y demostrar que el segundo hoy imprime `GANADOR`.

### H10-04 — `tomado()` puede perder el lock y seguir ejecutando su cuerpo [CRÍTICO]
**Dónde:** constante y afirmación de duración, plan:408-415; `tomado`, plan:691-704; exclusión deliberada del renovador, plan:831-836.

**Qué está mal:** el gestor adquiere una vez y no renueva ni comprueba que conserve la titularidad durante el cuerpo. Al vencer el lease, otro proceso puede adquirir; el primero no se entera y sigue dentro de `with tomado(...)`. Solo al salir intenta `liberar` y recibe `MutexNotMine`, después de que ambos ya hayan escrito. Exponer el nonce permite que cada consumidor programe renovaciones manuales, pero el contrato del gestor no las exige ni impide usarlo sin ellas. La frase «cinco minutos: más que cualquier sección crítica de V1» no tiene medición ni test, y el objeto de la feature nace precisamente de corridas OCR de duración incierta.

**Por qué importa:** con un lease positivo y timestamps correctos aún pueden coexistir dos escritores; no es un caso de input inválido.

**Cómo se comprueba:** padre entra en `tomado(..., lease_seconds=1)`, señala que sigue dentro y espera dos segundos; hijo adquiere con un `ahora` dos segundos posterior mientras el padre no ha salido. El test correcto debe impedir `GANADOR` o hacer que el primer titular deje de publicar mediante fencing. El plan debe decidir heartbeat/renovación obligatoria, secciones acotadas con prueba de duración, o token de fencing; una afirmación no sustituye ese mecanismo.

### H10-05 — El fail-closed de estados ilegibles o parciales no tiene prueba y no valida esquema [ALTO]
**Dónde:** `leer_estado`, plan:436-458; `_caducado`, plan:578-592; tests Tasks 4-6, plan:352-391, 520-562 y 637-663.

**Qué está mal:** ningún test siembra JSON corrupto, un valor no objeto, un objeto parcial o campos de tipo/dominio inválido. Por eso un mutante que haga que `leer_estado` devuelva `None` ante `JSONDecodeError`, o que `_caducado` devuelva `True` ante `KeyError`, pasa toda la suite propuesta. Además, `leer_estado` solo valida que el nivel superior sea `dict`: `{}` se convierte en `CaseBusy`, un `propietario` string puede provocar `AttributeError`, y un `lease_seconds` negativo cae por el camino fail-open de H10-03 en vez de `MutexIlegible`.

**Por qué importa:** la propiedad de fallo cerrado que el plan presenta como defensa central no queda protegida por TDD; regresiones o estados semánticamente inválidos pueden abrir el caso o escapar como errores no estructurados.

**Cómo se comprueba:** añadir casos separados para bytes no UTF-8, JSON truncado, lista, `{}`, propietario no objeto, nonce vacío, timestamp sin zona y duración no positiva. Todos deben conservar los bytes, no sobrescribir el estado y lanzar `MutexIlegible` (o el error cerrado que se decida). Ejecutar mutantes `except: return None` y `except: return True`; cada uno debe ser matado por su test específico.

### H10-06 — La primitiva elegida no es el `O_CREAT|O_EXCL` decidido en D2 [ALTO]
**Dónde:** spec de apertura:1645-1659; comentarios de requisitos, plan:97-101; `_guard`, plan:429-433.

**Qué está mal:** D2 fija un lockfile de existencia con `O_CREAT|O_EXCL` «vía filelock», pero el plan instancia `FileLock`. En Windows, `FileLock` es un lock nativo: abre el fichero con `O_CREAT|O_TRUNC` y aplica `msvcrt.locking`; no adjudica la creación con `O_EXCL`. La exclusión nativa puede ser válida, pero es otro mecanismo y tiene otros modos de fallo. Ninguna tarea resuelve la contradicción ni prueba qué backend se usa. `filelock>=3.12` tampoco reproduce la versión 3.29.0 citada por el plan.

**Por qué importa:** el plan se declara implementación de una decisión exacta mientras construye otra primitiva. Adjudicarla por el nombre de la librería ocultaría si D2 exige realmente creación exclusiva, lock nativo o una clase concreta de `filelock`.

**Cómo se comprueba:** en el venv de implementación, imprimir `filelock.__version__`, `type(FileLock(...))` e inspeccionar/monkeypatchear `os.open` durante `_acquire`; comprobar la presencia o ausencia de `os.O_EXCL`. Decidir contra la spec y fijar versión/backend. El borrado externo mientras el descriptor Windows estaba bloqueado devolvió `WinError 32` en esta máquina; por tanto este hallazgo no afirma que un borrado ordinario del `.guard` sostenido haya roto la exclusión, sino que la primitiva normativa no es la implementada.

### H10-07 — `psutil.boot_time()` 7.2.2 no es un `boot_id` estable en Windows [MEDIO]
**Dónde:** `identidad_proceso`, plan:197-207; tests de identidad, plan:131-153; requisito `psutil>=5.9`, plan:100-101.

**Qué está mal:** el plan convierte a entero un instante de arranque derivado del reloj. El changelog oficial posterior registra que en Windows `boot_time()` fluctuaba entre llamadas/procesos y no contabilizaba correctamente suspensión/hibernación; ambos arreglos son posteriores al 7.2.2 que el plan dice tener instalado. `int()` no garantiza identidad: valores cercanos a un borde de segundo pueden truncarse a enteros distintos. Los tests solo exigen que el campo no esté vacío y comparan contra la cadena artificial `otro-arranque`; nunca comparan dos procesos del mismo arranque ni el mismo proceso antes/después de suspensión o sincronización de hora.

**Por qué importa:** `ProcesoID.es_el_mismo()` puede negar que el mismo proceso/mismo arranque sea el dueño. En el código propuesto liberar y renovar dependen solo del nonce, por lo que hoy no abre el mutex; sí incumple el contenido/semántica de propietario de D2 y deja una identidad falsa lista para consumidores posteriores.

**Cómo se comprueba:** con la versión realmente fijada, recoger el `boot_id` desde muchos subprocesos y repetir tras suspensión/hibernación y resincronización horaria; todos los procesos del mismo arranque deben coincidir y un reinicio debe cambiarlo. Sustituir el timestamp por un identificador de arranque estable de Windows o por un token de proceso/arranque cuyo contrato esté documentado y probado.

### H10-08 — El mutex no hereda la barrera de ubicación del registro y el W-code puede escapar de la raíz [MEDIO]
**Dónde:** constraint del plan:35; `_raiz`/`ruta_del_lock`, plan:418-426; `workspace_registry.py:85-91,149-156`; `workspace_model.py:322-325`; `core/abrir_caso.py:82-101`.

**Qué está mal:** la validación contra `CASOS_ROOT` y el repo solo ocurre al construir `WorkspaceRegistry`. El mutex no construye uno: llama directamente a `raiz_por_defecto()`, que acepta el override de entorno, o usa cualquier `raiz` inyectada. Por tanto no «hereda» esa garantía. Además, el W-code se concatena como path sin validar su gramática ni comprobar contención tras resolver. Ejecuté la función equivalente: `..\escape` resolvió a `C:\safe\ESCAPE.lock` y `C:\tmp\escape` a `C:\tmp\ESCAPE.lock`, fuera de `C:\safe\workspaces`. `CaseRef.normalizar()` solo recorta y pone mayúsculas, y el alta nueva recibe `--w-code` sin una validación cerrada en `resolver_identidad`.

**Por qué importa:** el namespace deja de estar confinado al registro, puede crear/bloquear rutas ajenas y un valor inválido puede no compartir el mutex esperado por el caso. También vuelve falsa una constraint usada para justificar la arquitectura.

**Cómo se comprueba:** tests con W-code vacío, separadores, `..`, ruta absoluta, punto/espacio final y nombres reservados de Windows; todos deben rechazarse antes de `mkdir`. Resolver la ruta y exigir `candidate.parent == raiz.resolve()` (además de validar la gramática canónica). Probar que el override del registro bajo `CASOS_ROOT` o el repo se rechaza también por la primitiva.

### H10-09 — Task 7 se atribuye el criterio 41, pero no prueba sus efectos [MEDIO]
**Dónde:** afirmación del plan:730; criterio 41 de la spec:979-981; alcance declarado del plan:37 y 829-834.

**Qué está mal:** el criterio 41 no dice solo «dos procesos»: exige staging disjunto, paso por el mismo mutex, unión conservada en manifest, log, `_caso.md` y `estado.json`, y que un proceso no libere el lock del otro. Task 7 únicamente comprueba denegación ante un estado preexistente y entrada después de borrarlo. No descarga, no hace commits, no comprueba unión y ni siquiera llama `liberar` con nonce ajeno desde el segundo proceso. Sacar el write-set al Plan 3 es el alcance declarado; afirmar a la vez que este montaje «cumple» literalmente el criterio 41 es falso.

**Por qué importa:** el mapa de cobertura declararía cerrado un criterio E2E cuyos lost updates y titularidad cruzada siguen sin observarse.

**Cómo se comprueba:** cambiar la trazabilidad del Plan 2 para reclamar solo el contrato unitario de D2 y reservar el criterio 41 completo al Plan 3. El test E2E posterior debe arrancar dos procesos con staging distinto, serializar sus commits y comparar la unión byte/semántica de los cuatro artefactos, además de intentar una liberación cruzada.

### H10-10 — Las dependencias no están «ya usadas» y el test no acredita una declaración [BAJO]
**Dónde:** título/Interfaces Task 1, plan:51-58; test, plan:73-84; `requirements.txt:1-55`.

**Qué está mal:** la búsqueda del árbol encontró cero imports de `filelock` y `psutil`; el propio plan dice que `case_mutex.py` aún no existe. No son dependencias «ya usadas sin declarar», sino dependencias que este plan pretende introducir. Además, `assert paquete in texto` pasa si el nombre aparece solo en un comentario o como substring de otro requisito.

**Por qué importa:** el red del TDD se apoya en una premisa histórica falsa y el verde no demuestra que un clon instale el paquete correcto.

**Cómo se comprueba:** repetir la búsqueda de imports antes del cambio (salida vacía) y mutar `requirements.txt` para dejar `# filelock se añadirá después`: el test actual pasa. Parsear las líneas de requisitos con `packaging.requirements.Requirement` y comparar nombres canónicos; renombrar la tarea como introducción de dependencias nuevas.

### H10-11 — La justificación contra hilos generaliza una reentrancia que aquí no existe [BAJO]
**Dónde:** plan:730 y 738-740; `_guard`, plan:429-433.

**Qué está mal:** `filelock` es recursivo cuando se readquiere la misma instancia (o una instancia singleton configurada para ello). `_guard()` crea una instancia nueva en cada llamada. El plan afirma, sin esa distinción, que dos hilos «pasarían aunque la exclusión no existiera». En el backend Windows, dos descriptores distintos del mismo proceso sí contendieron en el experimento local: el segundo `msvcrt.locking` devolvió `PermissionError`. Y, si se eliminara la exclusión, dos hilos no quedarían mágicamente serializados por `filelock`: ya no habría `filelock` que los serializase.

**Por qué importa:** el argumento técnico usado para descartar un montaje es falso, aunque el criterio normativo siga exigiendo procesos reales. Confunde reentrancia por objeto con identidad de proceso.

**Cómo se comprueba:** con la versión fijada, crear dos instancias `FileLock` sobre la misma ruta desde dos hilos, mantener la primera y medir si la segunda bloquea; repetir readquiriendo la misma instancia para aislar la recursividad. Mantener el test multiproceso por el criterio 41, pero retirar la afirmación falsa.

<!-- informe-literal:fin:p9xr -->

## 2. Evidencia verificada al adjudicar (Claude Code, 2026-08-25)

**Digest del informe** recomputado al archivarlo: coincide con el declarado por el revisor.

**Dos hallazgos los encontré yo por mi cuenta mientras la ronda corría**, y conviene
distinguirlo de la convergencia casual: los busqué porque el **mandato** se los señalaba al
revisor, o sea que la pregunta estaba bien puesta antes de que ninguno de los dos mirara.

| Hallazgo | Cómo lo comprobé | Resultado |
|---|---|---|
| H10-02 | `datetime.fromisoformat` con y sin `Z`, medido en esta máquina | **CONFIRMADO**: 7.200 s de diferencia. El revisor añade el `ahora` futuro, que yo no vi |
| H10-07 | docstring de `psutil.boot_time()` | **CONFIRMADO**: declara sensibilidad a ajustes de hora y NTP |
| H10-01 | lectura del montaje del test | **CONFIRMADO**, y lo decisivo es que el revisor **lo ejecutó** sin exclusión y salió verde |
| H10-03 | `int(0.5) == 0`, `int(True) == 1` | **CONFIRMADO** |
| H10-06 | fuente del backend Windows de `filelock` | **CONFIRMADO**: `O_CREAT|O_TRUNC` + `msvcrt.locking`, no `O_EXCL` |
| H10-08 | el revisor resolvió `..\escape` fuera de la raíz | **CONFIRMADO** |
| H10-10 | búsqueda de imports de `filelock`/`psutil` en el árbol | **CONFIRMADO**: cero. Mi premisa era falsa |

**Lo que aporta el adjudicador.** Al remediar H10-07 apareció que el bloque de propietario
**no gobierna nada**: `renovar` y `liberar` comparan **nonce**. Así que no hacía falta un
`boot_id` estable, sino admitir que la identidad del proceso es **diagnóstica** — y con eso
desaparece la dependencia entera de `psutil`, que existía solo por ese campo. El revisor pedía
un identificador de arranque estable; el remedio correcto era más simple que el pedido.

**Y una corrección a mí mismo, dicha antes que a nadie:** le comuniqué a Nikolai que `filelock`
y `psutil` «se usan y no están declarados». Era **falso** — están instalados y nada los importa.
Confundí «instalado» con «usado» y sobre esa premisa escribí la Task 1 entera, test incluido.
