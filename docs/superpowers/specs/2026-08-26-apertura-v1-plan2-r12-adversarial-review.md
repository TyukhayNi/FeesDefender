---
tipo: revision-adversarial
objeto: core/casos/case_mutex.py
objeto_rev: "PR #247, diff de remediacion"
commit: b4b82cc
ronda: "12"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: q7wd
sha256_informe: efc690d2176df3e991abfc31b506c40c5b44026cf46b8223f51186af8b37273e
adjudicado_en: docs/superpowers/plans/2026-08-25-apertura-v1-plan2-mutex.md §2
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R12.** El §1 conserva literalmente la voz del revisor; la
> adjudicación vive en el **§2 del plan**. El acta existe porque yo soy la parte revisada:
> sin el original archivado nadie puede contrastar **qué dijo el revisor** con **qué decidí
> yo que dijo**.
>
> **Qué se revisó:** el diff de **remediación de R11**, no el módulo entero. Es la primera
> ronda de esta serie que revisa *correcciones*, y devolvió `NO-SHIP` con **7 hallazgos**.
>
> **Por qué esta ronda sí terminó y R11 no.** R11 se cortó porque su arnés —multiproceso,
> borrado de un lockfile sostenido, escape por enlace— disparó el filtro de contenido de
> su plataforma. El mandato de R12 se reencuadró: verificación defensiva, y **prohibición
> expresa** de escribir arneses que simulen ataques, con instrucción de *describir* en
> prosa lo que no se pudiera ejecutar así. Con eso corrió entero.
>
> **Limitación declarada por el propio revisor:** `filelock` y `dotenv` no estaban
> instalados en su entorno, así que **no pudo correr la batería de tests del repo**. Sus
> sondas sustituyeron `core.config` y el guard por dobles, y él mismo declara que no se
> les atribuye cobertura del bloqueo real. Todo lo que afirma sobre `filelock` en vivo
> queda `SIN VERIFICAR`.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:q7wd -->
# R12 — verificación de las correcciones del mutex

**Veredicto:** NO-SHIP
**Hallazgos:** 7 (2 críticos, 2 altos, 2 medios, 1 bajo)
**Qué pude ejecutar:** revisión completa de `diff_remediacion.patch`, de la adjudicación R11, de `core/casos/case_mutex.py` y de las regresiones del mutex; importación y sondas unitarias ordinarias sobre valores límite y JSON en directorios creados con `tempfile.mkdtemp()`. El árbol `objeto/` se mantuvo en solo lectura; se usó `PYTHONDONTWRITEBYTECODE=1`. Para alcanzar la lógica propia pese a las dependencias ausentes, las sondas sustituyeron únicamente `core.config` por dos raíces temporales y el guard por un context manager que crea el directorio padre; no se atribuye a esas sondas cobertura del bloqueo real de `filelock`.

Comandos y salidas literales relevantes:

```text
> python --version
Python 3.14.7

> python -c "import pytest,filelock; print('pytest',pytest.__version__); print('filelock',filelock.__version__)"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import pytest,filelock; print('pytest',pytest.__version__); print('filelock',filelock.__version__)
    ^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'filelock'
```

La batería enfocada se lanzó sobre la copia temporal
`C:\Users\tnm33\AppData\Local\Temp\r12_mutex_review_20260826_01\objeto`:

```text
> python -m pytest -q tests/test_case_mutex.py tests/test_case_mutex_estados_invalidos.py tests/test_case_mutex_r11.py tests/test_case_mutex_concurrencia.py
EEEEEEEEEEEEEEEEEEEEEEEEE
```

Al aislar el primer error de setup se obtuvo literalmente:

```text
ModuleNotFoundError: No module named 'dotenv'
```

Un segundo intento con `--basetemp=.pytest-r12-pure` eliminó el previo
`PermissionError` del temporal global de pytest, pero confirmó el mismo bloqueo de
setup en la fixture autouse de toda la suite:

```text
E   ModuleNotFoundError: No module named 'dotenv'
=========================== short test summary info ===========================
ERROR tests/test_case_mutex.py::test_filelock_esta_declarado_con_version_fijada
...
ERROR tests/test_case_mutex_r11.py::TestPerderElMutexNoSePuedeCallar::test_MutexPerdido_esta_en_la_tabla_del_10
```

Las sondas unitarias propias, con las sustituciones limitadas descritas arriba,
produjeron literalmente:

```text
PAST_TAKEOVER True True
REVALIDA_LEASE_VENCIDO True False
SCHEMA_PROBE schema_bool ACEPTADO
SCHEMA_PROBE prop_tipos ACEPTADO
SCHEMA_PROBE campos_extra ACEPTADO
CUERPO_Y_LIBERACION_EXCEPTION RuntimeError cause= None context= None notes= None sesion_causa= ValueError
CUERPO_MASCARADO_POR_BASE_LIBERAR KeyboardInterrupt context= RuntimeError
LATIDO_BASE_SILENCIADO False
TIMEOUT_VISIBLE mensaje_contiene_ruta= False causa_contiene_ruta= True tipo= CaseBusy
```

Y las dos sondas específicas de `BaseException` y del salto hacia atrás de la costura:

```text
CUERPO_BASE_LIBERACION_EXCEPTION KeyboardInterrupt cause= None context= None notes= None
ANTES_SALTO True
TRAS_SALTO ValueError
```

**Qué NO pude verificar, y por qué:** **SIN VERIFICAR** la batería real con
`filelock`: el Python del sistema carece de `filelock` y de `python-dotenv`, y la
fixture autouse global importa esta última antes de ejecutar cualquier test. **SIN
VERIFICAR** la exclusión entre procesos y la liberación del guard real por la misma
ausencia de `filelock`. **SIN VERIFICAR** la prueba de junction de
`test_case_mutex_r11.py:270-290`: el mandato prohíbe construir enlaces; se revisó en
fuente. **SIN VERIFICAR** el comportamiento ante un ajuste NTP real y el TOCTOU de
reemplazar la raíz por una junction entre `resolve()` y el uso: ejecutarlo exigiría
manipular enlaces; en prosa, se cambiaría la raíz después de validarla y antes de
`mkdir`/escritura, esperando comprobar si la ruta prohibida recibe el lock. **SIN
VERIFICAR** que un `filelock.Timeout` real solo pueda nacer en `acquire()`; la traducción
se comprobó con la costura `_abrir_guard`, no con la librería ausente.

## Hallazgos

### H12-01 — Un instante muy pasado publica un lease ya vencido y permite la toma inmediata [CRÍTICO]

**Dónde:** `core/casos/case_mutex.py:66-74`, `core/casos/case_mutex.py:361-385`;
ausencia de regresión en `tests/test_case_mutex_r11.py:74-107`.

**Qué está mal:** `_sin_desvio_absurdo()` solo limita el futuro. `adquirir()` acepta un
`ahora` arbitrariamente antiguo y lo publica como `acquired_at` y `renewed_at`. El nombre
de la función promete un desvío, pero la condición es unilateral. La sonda adquirió a
`2000-01-01`, adquirió de nuevo a `2026-08-26`, y el segundo nonce sustituyó al primero:
`PAST_TAKEOVER True True`.

**Por qué importa:** el primer llamador recibe un nonce y entra creyéndose titular, pero
su lease nace vencido; un segundo proceso puede adquirir inmediatamente. Es una ruptura
directa de exclusión mutua, simétrica al reloj futuro que R11 pretendía cerrar.

**Cómo se comprueba:** fijar `_ahora_del_sistema()` a `2026-08-26T12:00:00Z`, llamar a
`adquirir(..., ahora="2000-01-01T00:00:00Z", lease_seconds=60)` y después adquirir con
la hora del sistema. El segundo nonce queda en disco. Un test adecuado debe exigir una
cota inferior, no solo superior. Si se borra el guard del futuro, los tests R11 actuales
sí fallan; ninguno falla si se conserva ese guard y se sigue aceptando el pasado remoto.

### H12-02 — `revalidar()` afirma titularidad aunque el lease haya vencido [CRÍTICO]

**Dónde:** `core/casos/case_mutex.py:473-489`.

**Qué está mal:** `SesionMutex.revalidar()` solo comprueba existencia y nonce. No compara
`renewed_at + lease_seconds` con ningún reloj. Con estado de nonce propio, renovado en
2000 y lease de un segundo, devolvió `True` y dejó `perdido()` en `False`:
`REVALIDA_LEASE_VENCIDO True False`.

**Por qué importa:** precisamente antes de publicar un efecto irreversible, el cuerpo
puede llamar a la API recomendada y recibir una garantía falsa. Desde que vence el lease,
otro proceso está autorizado a adquirir; por tanto ambos pueden escribir aun cuando la
revalidación haya dado `True`.

**Cómo se comprueba:** sembrar un JSON válido con el nonce de la sesión y un
`renewed_at` anterior en más de `lease_seconds`; `revalidar()` debería devolver `False`
y marcar pérdida. El método necesita una fuente temporal coherente con el contrato de
inyección. Ninguna regresión R11 cubre expiración sin cambio de nonce.

### H12-03 — La señal del renovador aún puede perderse y su regresión principal no mata el mutante [ALTO]

**Dónde:** `core/casos/case_mutex.py:514-522`, `core/casos/case_mutex.py:532-545`;
`tests/test_case_mutex_r11.py:113-159`.

**Qué está mal:** `_latir()` captura `Exception`, no `BaseException`, y al terminar no se
comprueba que el hilo haya muerto por la vía esperada. Una sonda hizo que `renovar()`
lanzase `SystemExit`: tras el latido, `perdido()` seguía siendo `False` y el contexto
salió sin `MutexPerdido` (`LATIDO_BASE_SILENCIADO False`). Además, las tres regresiones
de H11-02 nunca provocan un fallo del hilo: una llama expresamente a `revalidar()` y las
otras descubren el nonce ajeno al liberar. El barrido de los tests no contiene ningún
doble de `renovar`, `BaseException`, `KeyboardInterrupt` ni `SystemExit`.

**Por qué importa:** el defecto adjudicado en R11 era exactamente «el hilo muere y el
cuerpo continúa». Un mutante que elimine `sesion.marcar_perdido(exc)` de la rama del hilo
deja verdes las regresiones R11; solo rompe una ruta que esos tests no recorren. Una
terminación no capturada vuelve a dejar que el lease venza sin avisar al cuerpo.

**Cómo se comprueba:** sustituir `renovar` por una función que lance primero
`RuntimeError` (debe marcar pérdida y lanzar `MutexPerdido` al salir) y luego por una que
lance `SystemExit` (también debe dejar señal). Como prueba de mutante, retirar únicamente
la llamada de la línea 521: la clase `TestPerderElMutexNoSePuedeCallar` actual seguiría
verde, aunque la corrección esencial hubiera desaparecido.

### H12-04 — La liberación pierde información y una `BaseException` puede enmascarar el error del cuerpo [ALTO]

**Dónde:** `core/casos/case_mutex.py:526-548`.

**Qué está mal:** para una excepción ordinaria de liberación, el error del cuerpo sí
prevalece, incluso si el cuerpo lanza `KeyboardInterrupt`; eso quedó comprobado. Pero el
fallo de liberación solo se guarda en `sesion._causa`: no queda como `__cause__`,
`__context__` ni nota del error que recibe el llamador. La salida fue
`RuntimeError cause=None context=None notes=None`, aunque `_causa` era `ValueError`.
Además, el `except Exception` no captura una `BaseException` de liberación: una
`KeyboardInterrupt` durante `liberar()` sustituyó al `RuntimeError` del cuerpo.

**Por qué importa:** la adjudicación decía que el error de liberación «se registra», pero
el llamador normal pierde esa evidencia; y en el caso de interrupción durante el cleanup
se incumple la regla más fuerte de que el error del cuerpo prevalezca. Esto dificulta
diagnosticar a la vez el fallo funcional y la pérdida del mutex.

**Cómo se comprueba:** hacer que el cuerpo lance `RuntimeError` y `liberar` lance primero
`ValueError`: comprobar que el error primario sale con el secundario adjunto de forma
observable. Repetir con `KeyboardInterrupt` en `liberar`: el primario debe seguir siendo
el del cuerpo. Los tests R11 solo cubren `RuntimeError` del cuerpo más `MutexNotMine` de
liberación y no inspeccionan el encadenamiento.

### H12-05 — El esquema acepta versiones y propietarios de tipos inválidos [MEDIO]

**Dónde:** `core/casos/case_mutex.py:232-265`; cobertura parcial en
`tests/test_case_mutex_r11.py:199-243`.

**Qué está mal:** `crudo["schema"] != 1` acepta `True` porque en Python
`True == 1`. Los campos `host`, `pid` y `proceso_uid` solo se validan por truthiness, de
modo que se aceptaron `host=7`, `pid="x"` y `proceso_uid=["u"]`. También se aceptan
campos superiores inesperados. Las salidas fueron `schema_bool ACEPTADO`,
`prop_tipos ACEPTADO` y `campos_extra ACEPTADO`.

**Por qué importa:** un lock que no cumple la versión ni el tipo declarado se trata como
válido en vez de fallar cerrado. Los tipos del propietario alimentan el diagnóstico de
`CaseBusy`; aceptar extensiones sin una política explícita debilita el significado de
`SCHEMA_MUTEX` y puede ocultar corrupción o una versión incompatible.

**Cómo se comprueba:** parametrizar `schema` con `True`, `1.0` y `"1"`; parametrizar
cada campo del propietario con booleanos, números, cadenas vacías, listas y PID no
positivo; decidir y fijar una política de campos extra. Las regresiones actuales matan
el mutante que vuelve a aceptar `schema=999` o `propietario={}`, pero pasan con todos los
valores anteriores.

### H12-06 — La ruta no aparece en `str(CaseBusy)`, pero sí en su causa encadenada [MEDIO]

**Dónde:** `core/casos/case_mutex.py:321-336`;
`core/casos/workspace_model.py:109-138`; cobertura incompleta en
`tests/test_case_mutex_r11.py:315-348`.

**Qué está mal:** la traducción construye un mensaje propio seguro, pero usa
`raise CaseBusy(...) from exc`. Si el `Timeout` contiene el path del guard, la ruta queda
en `CaseBusy.__cause__` y en un traceback encadenado. La sonda dio
`mensaje_contiene_ruta=False` y `causa_contiene_ruta=True`. El test solo inspecciona
`str(exc.value)`.

**Por qué importa:** el contrato de `WorkspaceError` pretende que la ruta local no se
filtre. Una interfaz o logger que muestre el traceback —comportamiento normal para una
excepción no capturada— revelará la ruta aunque la primera línea sea segura.

**Cómo se comprueba:** hacer que `_abrir_guard` lance `Timeout(<ruta>)`, capturar
`CaseBusy` y comprobar tanto `str(exc)` como la cadena completa de causas/traceback. Si
la política limita expresamente la prohibición a `str()`, debe documentarse; si abarca la
presentación normal de errores, hay que sanear o suprimir la causa externa conservando
diagnóstico no sensible.

### H12-07 — La fixture horaria hace deterministas los tests, pero deja sin probar la costura real [BAJO]

**Dónde:** `tests/test_case_mutex.py:19-31`,
`tests/test_case_mutex_estados_invalidos.py:44-56`,
`tests/test_case_mutex_r11.py:55-67`; implementación en
`core/casos/case_mutex.py:56-63`.

**Qué está mal:** la fixture autouse no desactiva la comparación de desvío —eso es
correcto y evita depender de la fecha de ejecución—, pero reemplaza
`_ahora_del_sistema()` en todos los tests de esos tres ficheros. Un mutante que haga que
la implementación real de la costura devuelva una época incorrecta seguirá pasando
esas pruebas. Tampoco hay una prueba aislada que la compare con el reloj real dentro de
una tolerancia.

**Por qué importa:** la nueva barrera depende de dos piezas: la comparación y la costura.
Las regresiones verifican bien la primera bajo reloj fijo, pero no el cableado real de la
segunda. El salto simulado de 601 segundos hacia atrás cambió una entrada antes válida en
`ValueError`; ante NTP real esto es fallo seguro de disponibilidad, no una confirmación
ejecutada de comportamiento operativo.

**Cómo se comprueba:** mantener la fixture en los tests de fechas fijas y añadir fuera de
su alcance un test de `_ahora_del_sistema()` contra `time.time()` con tolerancia pequeña.
La reacción a un salto real queda **SIN VERIFICAR**; en una prueba autorizada se
inyectarían lecturas sucesivas antes/después del salto y se exigiría pérdida explícita,
nunca continuidad silenciosa.

## Evaluación mutante de las seis regresiones R11

| Corrección R11 | ¿La regresión se pondría roja al borrar la corrección? | Resultado de R12 |
|---|---|---|
| H11-01, futuro | Sí para retirar la cota superior; no para el hueco simétrico del pasado | Cobertura parcial; H12-01 queda abierto |
| H11-02, pérdida | Sí si se borra toda `SesionMutex`; **no** si se borra solo `marcar_perdido()` en el hilo | Mutante esencial superviviente; H12-03 |
| H11-03, enmascaramiento | Sí para cuerpo `RuntimeError` + liberación `Exception` | No cubre información secundaria ni `BaseException` de liberación; H12-04 |
| H11-04, esquema | Sí para `schema=999` y propietario vacío/parcial | No cubre tipos, `bool == 1` ni extras; H12-05 |
| H11-05, junction | En Windows solo si `mklink /J` funciona; si no, hace `skip`. El guard de fuente solo busca el texto `.resolve()` | **SIN VERIFICAR** por prohibición expresa de construir enlaces |
| H11-06, timeout | Sí para retirar la traducción en la costura `_abrir_guard` | No cubre `filelock` real ni la fuga por `__cause__`; H12-06 |

La asimetría de contención es coherente en estado estático: resolver la raíz detecta una
junction a una zona prohibida y mantener léxica la ruta hija evita reabrir la carrera de
creación. No se encontró por lectura una aceptación estática adicional. Queda **SIN
VERIFICAR** el reemplazo concurrente de la raíz entre validación y uso, conforme a la
prohibición del mandato.

<!-- informe-literal:fin:q7wd -->

## 2. Evidencia verificada al adjudicar (Claude Code, 2026-08-26)

**Las siete verificadas contra la fuente antes de aceptarlas**, con sondas propias:

| Hallazgo | Mi comprobación | Resultado |
|---|---|---|
| H12-01 | `adquirir(ahora="2000-01-01")` y luego con la hora del sistema | **CONFIRMADO**: el titular pierde el caso al instante |
| H12-02 | `revalidar()` con el mismo nonce y `renewed_at` de 2000 | **CONFIRMADO**: devuelve `True`, `perdido()` sigue `False` |
| H12-03 | lectura de `_latir`: captura `Exception`, no `BaseException` | **CONFIRMADO** |
| H12-04 | cuerpo con `RuntimeError` + liberación fallida | **CONFIRMADO**: `__cause__` y `__context__` a `None` |
| H12-05 | `schema=True`, `host=7`, `pid="x"`, `proceso_uid=["u"]`, campo extra | **CONFIRMADO**: los cinco aceptados |
| H12-06 | `Timeout(str(raiz))` y lectura de `__cause__` | **CONFIRMADO**: la ruta viaja en la causa |
| H12-07 | estructural: la fixture `autouse` alcanza todo el fichero | **CONFIRMADO** |

**Una precisión sobre H12-03, y es a mi favor solo a medias.** El hallazgo tiene dos
mitades. La segunda —«las regresiones de H11-02 no matan a su mutante»— **ya la había
encontrado y arreglado yo** en el commit `0165037`, corriendo mi propia prueba de mutación
antes de que llegara el informe; el revisor trabajaba sobre `b4b82cc`, anterior. La
primera —`except Exception` en vez de `BaseException`— era **nueva y real**. Se adjudica
como confirmada, con la parte superada declarada.

### Lo que aporta el adjudicador, y no está en el informe

**H12-01 es la TERCERA ronda consecutiva cerrando media frontera del mismo hallazgo.**
R10 dijo «naïve **o futuro**» y cerré el naïve. R11 dijo «futuro» y cerré el futuro. R12
dice «pasado». Tres rondas para una propiedad de una línea, porque cada vez remedié **el
caso que el revisor escribió** en vez de preguntarme de qué **frontera** era ejemplo. El
remedio bueno no era rechazar el futuro ni el pasado: era **acotar el desvío**.

**Y dos defectos míos que aparecieron al remediar, ninguno del revisor:**

- **Mi arnés de mutación mentía.** Imprimía «los seis mutantes mueren» habiendo ejecutado
  tres: las otras tres anclas habían quedado rancias al reescribir esas líneas, y el
  resumen solo miraba los mutantes aplicados. Un arnés de mutación que da por bueno lo que
  no ejecutó es exactamente el defecto que existe para detectar. Ahora falla si un ancla
  no casa.
- **Perdí la remediación entera de R12 con un `git checkout`.** El arnés reventó a mitad
  por un `ñ` en un nombre de test contra una consola cp1252, dejando el módulo mutado;
  restauré con `git checkout` **sin haber commiteado el remedio**, y `checkout` restaura
  desde el índice. Mi propia nota lo dice —*commitea antes de mutar*— y no la seguí. Se
  reaplicó y ahora el arnés restaura en un `finally`.

**Los once mutantes se ejecutaron y murieron**, cada uno por su frontera. Suite: **3.560
tests, 0 fallos con las semillas 777 y 31337**.

### Lo que sigue SIN VERIFICAR, y se declara

- **El revisor no pudo correr la batería del repo** (sin `filelock` ni `dotenv`). Sus
  sondas usaban dobles; el comportamiento con `filelock` real no lo verificó nadie en esta
  ronda salvo la suite del repo, que sí corre aquí.
- **La reacción a un salto real de NTP** a mitad de operación. La cota de 600 s es una
  decisión, no una medición.
- **Las siete remediaciones de R12 no tienen ronda propia.** Es la misma deuda con la que
  R11 salió, y merece decirse en vez de dejarla implícita.
