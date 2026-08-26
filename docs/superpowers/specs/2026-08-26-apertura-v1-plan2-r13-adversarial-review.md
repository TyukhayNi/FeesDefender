---
tipo: revision-adversarial
objeto: core/casos/case_mutex.py
objeto_rev: "PR #247, diff de remediacion de R12"
commit: 21714c8
ronda: "13"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: v5nk
sha256_informe: 05dd51bc1f724ae53e410e46b3f3a4beff9ad4dcbbe52a2ed5a26aff74a0bc06
adjudicado_en: docs/superpowers/plans/2026-08-25-apertura-v1-plan2-mutex.md §3
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R13.** El §1 conserva literalmente la voz del revisor; la
> adjudicación vive en el **§3 del plan**.
>
> **Cuarta ronda sobre el mismo componente.** R11 encontró 6 defectos, R12 encontró 7 en
> las correcciones de R11, y R13 encuentra 8 en las de R12 — de los cuales **2 ya estaban
> cerrados** por trabajo propio anterior al archivado del objeto, y **6 seguían vivos**.
>
> **El que justifica la ronda entera:** la cota de desvío temporal protegía los leases
> **largos** y no los cortos. `DESVIO_MAXIMO` son 600 s y `_lease_valido` admite desde
> 1 s, así que cualquier lease más corto que el desvío tolerado se agota con un reloj
> **dentro** de lo admitido. Y mi propio control negativo de R12 usaba exactamente esa
> combinación (`±5 min` con `lease_seconds=60`) para demostrar que el arreglo «no era
> demasiado estricto»: el test escrito para defender la corrección documentaba su agujero.
>
> **Limitación declarada por el revisor:** su entorno no tenía `filelock` ni `dotenv`, así
> que usó dobles y **no acredita exclusión entre procesos ni el backend Windows real**.
> Lo dice él, y se conserva.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:v5nk -->
# R13 — verificación de las correcciones de R12

**Veredicto:** NO-SHIP
**Hallazgos:** 8 (2 críticos, 1 alto, 3 medios, 2 bajos)
**Qué pude ejecutar:** Python 3.14.7 y pytest 9.1.1. Todo se ejecutó sobre
`scratch_r13/`, copia de `objeto/`; el árbol revisado no se modificó. Como el entorno no
trae `filelock` ni `python-dotenv`, usé dobles mínimos solo para la lógica unitaria: el
doble de `filelock` serializa hilos del mismo proceso, pero **no acredita exclusión entre
procesos ni el backend Windows real**.

Comandos y salidas literales relevantes:

```text
> python --version
Python 3.14.7

> python -c "import filelock, dotenv, pytest; print('filelock='+filelock.__version__); print('dotenv=OK'); print('pytest='+pytest.__version__)"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import filelock, dotenv, pytest; print('filelock='+filelock.__version__); print('dotenv=OK'); print('pytest='+pytest.__version__)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'filelock'

> python -c "import pytest; print('pytest='+pytest.__version__)"
pytest=9.1.1

> python -c "import dotenv; print('dotenv=OK')"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import dotenv; print('dotenv=OK')
    ^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'dotenv'
```

```text
> python -m pytest r13_suite/test_case_mutex_r12.py -q --basetemp=..\pytest_tmp_r13_r12b
..................                                                       [100%]
```

```text
> python -m pytest r13_suite/test_case_mutex.py r13_suite/test_case_mutex_r11.py r13_suite/test_case_mutex_r12.py r13_suite/test_case_mutex_estados_invalidos.py r13_suite/test_case_mutex_reloj_real.py -k "not test_bajo_CASOS_ROOT_se_rechaza" --basetemp=..\pytest_tmp_r13_based -o addopts=
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\tnm33\AppData\Local\Temp\r13\scratch_r13
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 112 items / 1 deselected / 111 selected

r13_suite\test_case_mutex.py ........................................... [ 38%]
.                                                                        [ 39%]
r13_suite\test_case_mutex_r11.py ...................                     [ 56%]
r13_suite\test_case_mutex_r12.py ..................                      [ 72%]
r13_suite\test_case_mutex_estados_invalidos.py ......................... [ 95%]
...                                                                      [ 98%]
r13_suite\test_case_mutex_reloj_real.py ..                               [100%]

====================== 111 passed, 1 deselected in 2.97s ======================
```

El test deseleccionado necesita la fixture global `tmp_casos_root`. Copiar esa fixture
arrastraba la barrera global del repositorio, que no podía importarse porque además falta
`yaml`; no tiene relación con las correcciones R12.

Las diez sondas R13 afirman el **resultado defectuoso observado**, de modo que `PASSED`
confirma el contraejemplo:

```text
> python -m pytest r13_suite/test_r13_probes.py -vv --basetemp=..\pytest_tmp_r13_probes -o addopts=
collecting ... collected 10 items

r13_suite/test_r13_probes.py::test_desvio_futuro_admitido_roba_lease_corto PASSED [ 10%]
r13_suite/test_r13_probes.py::test_desvio_pasado_admitido_publica_lease_ya_vencido PASSED [ 20%]
r13_suite/test_r13_probes.py::test_los_bordes_exactos_de_600_segundos_se_aceptan PASSED [ 30%]
r13_suite/test_r13_probes.py::test_revalidar_da_true_con_reloj_que_deriva_al_pasado PASSED [ 40%]
r13_suite/test_r13_probes.py::test_revalidar_con_ahora_none_omite_el_lease PASSED [ 50%]
r13_suite/test_r13_probes.py::test_revalidar_si_el_reloj_lanza_no_marca_perdida PASSED [ 60%]
r13_suite/test_r13_probes.py::test_perdida_sin_causa_no_se_anota_al_error_del_cuerpo PASSED [ 70%]
r13_suite/test_r13_probes.py::test_nota_de_perdida_reproduce_texto_sensible_de_la_causa PASSED [ 80%]
r13_suite/test_r13_probes.py::test_systemexit_de_liberar_se_convierte_en_mutex_perdido PASSED [ 90%]
r13_suite/test_r13_probes.py::test_campo_desconocido_dentro_de_propietario_se_acepta PASSED [100%]

============================= 10 passed in 0.41s ==============================
```

Ejecuté además dos mutantes dirigidos. El primero sustituyó, solo en la copia,
`_ahora_del_sistema()` por una lectura directa del reloj dentro de
`_sin_desvio_absurdo()`; los dos tests que supuestamente prueban el cableado siguieron
verdes. El segundo añadió una nota a **todo** fallo del cuerpo, incluso sin pérdida; el
test que dice probar que eso no ocurre también siguió verde:

```text
> python -m pytest r13_suite/test_case_mutex_reloj_real.py -vv --basetemp=..\pytest_tmp_r13_mut_clock -o addopts=
collecting ... collected 2 items
r13_suite/test_case_mutex_reloj_real.py::test_la_costura_devuelve_el_reloj_de_verdad_en_segundos_UTC PASSED [ 50%]
r13_suite/test_case_mutex_reloj_real.py::test_la_cota_se_mide_contra_esa_costura_y_no_contra_otra_cosa PASSED [100%]
============================== 2 passed in 0.08s ==============================

> python -m pytest r13_suite/test_case_mutex_r12.py::test_sin_perdida_no_se_anota_nada -vv --basetemp=..\pytest_tmp_r13_mut_note -o addopts=
collecting ... collected 1 item
r13_suite/test_case_mutex_r12.py::test_sin_perdida_no_se_anota_nada PASSED [100%]
============================== 1 passed in 0.11s ==============================
```

**Qué NO pude verificar, y por qué:** no pude ejecutar `filelock` real, el test de
concurrencia multiproceso ni la liberación nativa de Windows porque `filelock` no está
instalado. Tampoco la suite completa del repositorio: faltan `python-dotenv` y `yaml`.
No ejecuté saltos reales de NTP. No maté procesos, no borré locks sostenidos por otro
proceso y no construí enlaces del sistema de ficheros, conforme al mandato. Quedan por
tanto `SIN VERIFICAR` la contención nativa real, la reacción a un salto real de reloj y
las rutas que solo se manifiestan al bloquear dos procesos de verdad.

## Hallazgos

### H13-01 — La cota simétrica sigue permitiendo robar o publicar vencido cualquier lease menor que el desvío [CRÍTICO]

**Dónde:** `core/casos/case_mutex.py:47-88`, `core/casos/case_mutex.py:392-425`;
`tests/test_case_mutex_r12.py:66-81`.

**Qué está mal:** la aritmética `abs(desvio) > 600` es simétrica y sus bordes exactos se
aceptan, pero la propiedad relevante no es «desvío menor que 600»: es que el error de
reloj no pueda agotar el lease que se está protegiendo. `_lease_valido()` admite desde
1 segundo. Con un lease de 60 s, un llamador 300 s adelantado —aceptado— considera
caducado el lease vivo y lo sustituye; uno 300 s atrasado publica un lease que el reloj
correcto considera vencido inmediatamente. En ambos sentidos quedaron dos cuerpos que
recibieron nonce y pudieron creerse titulares.

Los bordes `±600` también se aceptan porque la comparación es estricta (`>`). Eso es
aritméticamente coherente con «más de 600», pero maximiza el mismo defecto para cualquier
lease de hasta 600 s. Los leases grandes no introducen otra anomalía: el fallo aparece
precisamente cuando `lease_seconds <= abs(desvio_admitido)`.

**Por qué importa:** es una ruptura directa de exclusión mutua, el mismo daño crítico de
R11/R12. La corrección volvió a cerrar el ejemplo («pasado remoto») y no la frontera: el
propio control negativo acepta ±5 minutos con `lease_seconds=60`, combinación que ya es
insegura.

**Cómo se comprueba:** fijar el reloj del sistema a `12:00`, adquirir con lease 60 a
`12:00` y volver a adquirir a `12:05`; el segundo nonce reemplaza al primero. En sentido
opuesto, adquirir a `11:55` con lease 60 y después a `12:00`; vuelve a entrar un segundo
titular. Ambas sondas pasaron. Una regresión eficaz debe relacionar el desvío permitido
con el lease efectivo y comprobar el daño, no solo extremos de 2000/2099.

### H13-02 — `revalidar()` aún puede devolver `True` con un lease vencido y falla abierto si su reloj no es utilizable [CRÍTICO]

**Dónde:** `core/casos/case_mutex.py:498-538`, en especial la condición de la línea 535;
`tests/test_case_mutex_r12.py:86-115`.

**Qué está mal:** el lease solo se mira si `ahora_fn is not None`, aunque la dataclass lo
declara opcional con valor por defecto `None`. En ese caso un estado con nonce propio y
lease vencido devuelve `True`. En la ruta normal de `tomado()` también hay un hueco: el
callable se validó al adquirir, pero puede devolver después un pasado remoto;
`revalidar()` llama `_caducado()` directamente, sin `_sin_desvio_absurdo()`, y vuelve a
dar `True` para un lease ya vencido. Si el callable lanza, la excepción sale y la sesión
queda con `perdido() == False`; un llamador que capture el fallo puede continuar sin
señal de pérdida.

**Por qué importa:** `revalidar()` es la barrera recomendada antes de publicar un efecto
irreversible. Un `True` falso permite escribir después de que otro proceso esté
autorizado a adquirir. Es exactamente la garantía que H12-02 pretendía reparar.

**Cómo se comprueba:** (a) construir `SesionMutex(..., ahora_fn=None)` sobre el nonce de
un estado vencido; devuelve `True`; (b) entrar con un reloj que primero devuelve
`12:00` y después `2000-01-01`, atrasar `renewed_at` a `11:00` y llamar `revalidar()`;
devuelve `True` y no marca pérdida; (c) hacer que el segundo acceso al reloj lance y
comprobar que, tras capturarlo, `perdido()` sigue falso. Las tres sondas pasaron. El
método debe tener reloj obligatorio y fallar cerrado ante timestamp inválido, desviado o
excepción.

### H13-03 — Una pérdida conocida sin excepción causal vuelve a desaparecer cuando el cuerpo falla [ALTO]

**Dónde:** `core/casos/case_mutex.py:509-512`, `core/casos/case_mutex.py:527-529` y
`core/casos/case_mutex.py:596-605`; `tests/test_case_mutex_r12.py:152-178`.

**Qué está mal:** la nota se añade solo si `sesion._causa is not None`. Sin embargo,
`revalidar()` llama `marcar_perdido()` **sin causa** cuando el lock desapareció o cambió
de nonce. Si después falla el cuerpo y `liberar()` no genera una nueva excepción —por
ejemplo, porque el lock sigue ausente y liberar es idempotente— la pérdida está marcada
pero no aparece en `__notes__` ni en ninguna otra parte de la excepción entregada.

**Por qué importa:** H12-04 pretendía que el fallo del cuerpo mandase sin evaporar la
pérdida del mutex. Esa propiedad sigue dependiendo accidentalmente de que exista un
objeto excepción secundario. En la rama «estado ausente», el llamador vuelve a perder la
información de concurrencia.

**Cómo se comprueba:** dentro de `tomado()`, marcar pérdida sin causa y lanzar un
`RuntimeError` del cuerpo; la excepción recibida conserva `__notes__ == []`. La sonda
pasó. Debe añadirse una nota genérica siempre que `perdido()` sea verdadero, enriquecida
con la causa solo cuando exista.

### H13-04 — Capturar `BaseException` también en `liberar()` convierte una terminación en `MutexPerdido` [MEDIO]

**Dónde:** `core/casos/case_mutex.py:585-611`, especialmente líneas 590 y 606-611.

**Qué está mal:** R12 necesitaba `BaseException` en el **hilo** y necesitaba preservar el
error del cuerpo si el cleanup también fallaba. El diff amplió además el `except` de
`liberar()`. Cuando el cuerpo terminó bien y `liberar()` lanza `SystemExit` o
`KeyboardInterrupt`, se captura como pérdida y luego se sustituye por `MutexPerdido`.
El control de terminación queda relegado a `__cause__`.

**Por qué importa:** una salida o cancelación puede ser interceptada por código que
capture `WorkspaceError`, haciendo continuar al proceso cuando debía terminar. La
corrección es más amplia que la propiedad que pretendía cerrar.

**Cómo se comprueba:** sustituir `liberar()` por una función que lance `SystemExit(9)` y
dejar que el cuerpo termine normalmente. La salida observada es `MutexPerdido` con
`SystemExit` como causa; la sonda pasó. Deben distinguirse el caso «hay excepción del
cuerpo que debe prevalecer» del caso «el cleanup es la única fuente de una
`BaseException` de control».

### H13-05 — La nota reproduce sin sanear el texto de la causa y puede filtrar rutas [MEDIO]

**Dónde:** `core/casos/case_mutex.py:596-605`, en concreto `str(sesion._causa)`.

**Qué está mal:** cualquier excepción del renovador se guarda en `_causa`. Si es un
`OSError` de lectura, escritura o `os.replace`, su texto normal puede contener rutas
absolutas. Al fallar también el cuerpo, `add_note()` copia ese texto literalmente. H12-06
sanea con cuidado la ruta del `Timeout`, pero H12-04 abre otra salida en el mismo
traceback.

**Por qué importa:** contradice la política del componente de no filtrar rutas internas
en errores observables. Además, una nota se muestra normalmente en el traceback, justo
el artefacto que se comparte para diagnóstico.

**Cómo se comprueba:** marcar la sesión perdida con
`OSError("C:\\interno\\cliente-secreto\\lock.tmp")`, lanzar el error del cuerpo e
inspeccionar `__notes__`; la ruta aparece completa. La sonda pasó. Conservar el tipo de
causa, un código y un mensaje saneado aporta diagnóstico sin reproducir `str(exc)`.

### H13-06 — El rechazo de campos desconocidos solo cubre el nivel superior del esquema [MEDIO]

**Dónde:** `core/casos/case_mutex.py:246-286`; `tests/test_case_mutex_r12.py:216-222`.

**Qué está mal:** `sobrantes` se calcula únicamente sobre el dict superior. El objeto
`propietario`, cuyo esquema se declara como `host/pid/proceso_uid`, acepta cualquier
campo adicional. Esto no es coherente con la política escrita en la corrección: que la
compatibilidad hacia delante se hace subiendo `SCHEMA_MUTEX`, no aceptando lo que esta
versión no entiende.

**Por qué importa:** no rompe por sí solo la exclusión, pero deja una semántica de versión
partida: una extensión superior exige nueva versión y la misma extensión dentro del
propietario entra silenciosamente. Puede ocultar corrupción o una evolución de formato.

**Cómo se comprueba:** adquirir, añadir
`propietario.inventado = "aceptado"` al JSON y leerlo. `leer_estado()` lo devuelve como
válido; la sonda pasó. Si la política cerrada es deliberada, debe aplicarse a cada objeto
con forma declarada y tener regresión; si se permiten extras anidados, hay que documentar
esa excepción a la política.

### H13-07 — El test que dice probar el cableado del reloj no mata la desconexión [BAJO]

**Dónde:** `tests/test_case_mutex_reloj_real.py:20-35`.

**Qué está mal:** el primer test sí verifica que la costura real se aproxima a
`time.time()`. El segundo llama `_sin_desvio_absurdo()` con la hora real, pero nunca
sustituye la costura ni demuestra que la función la consulte. Un mutante que reemplaza
`_ahora_del_sistema()` por una lectura directa
`datetime.now(timezone.utc).timestamp()` dentro de `_sin_desvio_absurdo()` deja los dos
tests verdes (2 passed). Por tanto no prueba «contra esa costura y no contra otra cosa».

**Por qué importa:** hoy el código está cableado correctamente, pero la regresión no
protege la costura inyectable. Una futura desconexión puede dejar verde la suite y volver
inútiles las fixtures que fijan el reloj.

**Cómo se comprueba:** el mutante ejecutado dio `2 passed`. El test debe monkeypatchar
`_ahora_del_sistema` a un instante deliberadamente distinto del reloj real y elegir un
timestamp cuyo resultado cambie según se use la costura o una lectura directa.

### H13-08 — `test_sin_perdida_no_se_anota_nada` no inspecciona las notas [BAJO]

**Dónde:** `tests/test_case_mutex_r12.py:172-178`.

**Qué está mal:** el test solo exige que salga `RuntimeError`; no captura la excepción ni
lee `__notes__`. Un mutante que ejecuta el bloque de `add_note()` ante cualquier fallo del
cuerpo, aunque `sesion.perdido()` sea falso, deja el test verde (1 passed).

**Por qué importa:** el control negativo afirmado por el nombre y el docstring no existe.
Una remediación que llenase todos los errores del cuerpo de ruido pasaría la regresión.

**Cómo se comprueba:** el mutante ejecutado cambió la condición de anotación por
`if fallo_del_cuerpo:`; el test siguió pasando. Debe capturar `as exc` y afirmar que
`getattr(exc.value, "__notes__", []) == []`.

## Balance de las siete correcciones

1. **Cota simétrica:** la resta, el valor absoluto y el borde estricto son coherentes,
   pero la cota fija no protege leases más cortos; corrección parcial y crítica.
2. **Lease en `revalidar()`:** mata el caso exacto de R12, pero `None`, deriva posterior
   y excepción del reloj dejan huecos; corrección parcial y crítica.
3. **`BaseException` en el hilo:** la llamada al reloj y `renovar()` están dentro del
   `try`, y no encontré otra muerte ordinaria sin señal. La ampliación a `liberar()` sí
   introduce H13-04. La ejecución con hilo real + doble de guard pasó; backend nativo,
   `SIN VERIFICAR`.
4. **`add_note()`:** se adjunta al error correcto en el caso cubierto (fallo del cuerpo +
   `MutexNotMine` de liberación), pero falta sin `_causa` y no se sanea su texto.
5. **Esquema:** los tipos añadidos, `schema is int`, PID positivo y extras superiores
   están cubiertos y pasan; queda la incoherencia de extras anidados.
6. **`Timeout` fuera del `except`:** la inspección y la regresión confirman causa y
   contexto vacíos, detalle sin ruta y tipo conservado. El `finally` libera en salida
   normal o excepcional. El `filelock` real y su liberación efectiva quedan
   `SIN VERIFICAR`.
7. **Reloj real:** la costura real devuelve epoch en segundos y ambos tests pasan, pero
   el segundo no prueba su propio enunciado y sobrevive al mutante de desconexión.

NO-SHIP se apoya en H13-01 y H13-02: ambas permiten que la API vuelva a afirmar o entregar
titularidad cuando otro proceso ya está autorizado a entrar. Los demás hallazgos no
cambian por sí solos el veredicto, pero muestran el mismo patrón de remediación parcial
que el mandato pedía buscar.

<!-- informe-literal:fin:v5nk -->

## 2. Evidencia verificada al adjudicar (Claude Code, 2026-08-26)

**Los ocho verificados contra la fuente antes de aceptarlos.**

| # | Sev. | Estado | Comprobación propia |
|---|---|---|---|
| H13-01 | CRÍTICO | **VIVO → remediado** | lease 60 s + `ahora` a +300 s (admitido): el titular es sustituido |
| H13-02 | CRÍTICO | **SUPERADO** por `97670d2` | `ahora_fn` sin default y `revalidar` ya acotaba, ambos verificados |
| H13-03 | ALTO | **SUPERADO** por `97670d2` | la nota ya no exige `_causa`; lo prueba `test_la_perdida_por_caducidad_tambien_se_anota` |
| H13-04 | MEDIO | **VIVO → remediado** | `SystemExit` en `liberar` salía como `MutexPerdido` |
| H13-05 | MEDIO | **VIVO → remediado** | la nota copiaba el texto de un `OSError`, con la ruta dentro |
| H13-06 | MEDIO | **VIVO → remediado** | un campo extra **dentro** de `propietario` se aceptaba |
| H13-07 | BAJO | **VIVO → remediado** | el test del reloj no mataba la desconexión de la costura |
| H13-08 | BAJO | **VIVO → remediado** | el control negativo de la nota no inspeccionaba las notas |

**Sobre los dos superados:** el objeto se archivó en `21714c8`, y `97670d2` es posterior.
No son refutaciones: son hallazgos ciertos sobre un estado que ya no existía cuando el
informe llegó. Se declaran así y no como aciertos míos frente al revisor — los dos los
había encontrado yo buscando *la misma pregunta* que el mandato le hacía a él.

### Lo que aporta el adjudicador

**H13-01 es la cuarta ronda seguida con la misma forma de fallo, y la más instructiva.**

| Ronda | Dijo | Cerré | Quedó abierto |
|---|---|---|---|
| R10 | «naïve **o futuro**» | el naïve | el futuro |
| R11 | «futuro» | el futuro | el pasado |
| R12 | «pasado» | los dos, con cota simétrica | **la relación con el lease** |
| R13 | «la cota no protege leases cortos» | la cota se mide **contra el lease** | — |

La propiedad nunca fue «rechazar el futuro», ni «rechazar el pasado», ni «acotar el
desvío». Era **«el error de reloj no puede agotar el lease que protege»**, que es una
*relación entre dos magnitudes* y no una cota sobre una. Las tres primeras veces remedié
una cota; solo a la cuarta apareció la relación.

**Y tres defectos de mi propio instrumental, ninguno del revisor:**

- **Mi arnés de mutación imprimió «los N mutantes mueren» habiendo ejecutado menos**, dos
  veces, por anclas que quedaban rancias al reescribir las líneas que mutaban. Ahora
  **falla** si un ancla no casa — y esta ronda lo demostró: paró con dos anclas ambiguas y
  un mutante mal apuntado que habrían pasado por verdes.
- **Perdí una remediación entera con `git checkout`** tras un `crash` del arnés, por no
  haber commiteado antes de mutar. Mi propia nota lo dice.
- **Dos tests existentes estaban calibrados sobre el agujero:** el control negativo de R12
  y el reloj falso del test de renovación, que saltaba un minuto por lectura con un lease
  de 1 s. Los dos se recalibraron; ninguno de los dos era el contrato, eran el montaje.

**Diecisiete mutantes se ejecutaron y murieron**, cada uno por su frontera. Suite: **3.577
tests, 0 fallos con las semillas 777 y 31337**.

### Lo que sigue SIN VERIFICAR, y se declara

- **El revisor no pudo correr la batería del repo** ni acreditar la exclusión entre
  procesos: sin `filelock`, su doble serializa hilos del mismo proceso. Lo cubre la prueba
  de concurrencia de aquí, no su ronda.
- **La reacción a un salto real de NTP** sigue sin medirse.
- **Las seis remediaciones de R13 no tienen ronda propia.** Es la cuarta vez que se dice
  lo mismo, y merece leerse como lo que es: cada ronda deja su propia deuda, y el
  rendimiento decreciente (6 → 7 → 6 vivos, cada vez más finos) es el dato con el que se
  decide cuándo parar.
