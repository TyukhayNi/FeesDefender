---
tipo: revision-adversarial
objeto: scripts/abrir_caso.py
objeto_rev: "2"
commit: 318a081
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: v2r2
sha256_informe: 7c15f415909d53233f98be3da00e5df99a677bd2ab6a0a7d95053cc44d60718e
adjudicado_en: docs/superpowers/plans/2026-09-14-apertura-v2-lazo-crm.md §9
---

# Acta — R2 adversarial sobre el DIFF de V2 (el lazo del CRM)

Objeto: el diff `c8c4c48..318a081`, 8 ficheros. Segunda de las dos rondas que el radio de dano
manda para esta pieza (la R1 fue sobre el plan).

## 1. Informe recibido de Codex, sin modificar

Mandato e informe van literales mas abajo, entre marcadores con nonce `v2r2`.

## 2. Evidencia verificada por mi

| Que | Resultado |
|---|---|
| `sha256` del informe | `7c15f415909d53233f98be3da00e5df99a677bd2ab6a0a7d95053cc44d60718e` — recomputado por mi, coincide con el que devolvio el revisor |
| No mutacion | los `sha256` de `scripts/abrir_caso.py` y del censo, identicos al abrir y al cerrar |
| Hallazgos | **7 (3 ALTO, 4 MEDIO)** |
| **H-01** | **CONFIRMADO por mi**: `_verificar_real` llama `va.verificar(cd)` sin fuentes, y el propio comentario de esa funcion dice que con `SinRed` «las cinco de red salen en fallo». Con `--crm api` la etapa daria **fallo siempre** |
| **H-02** | **CONFIRMADO**: `_leer_recibo` devuelve `None` tanto para «no hay» como para «no se pudo interpretar» — la misma frontera que P8 remedio esta manana |
| **H-07** | **CONFIRMADO**: el guard usa `<=`, asi que el conjunto decisorio podria quedarse con 1 de 3 y seguir verde |
| **H-03** | **CONFIRMADO**: el §7 del plan declara cubierta la actuacion y es falso — el recibo se guarda DESPUES del efecto |

**Lo que el revisor NO encontro, y era mi mayor preocupacion:** «No encuentro una relajacion
injustificada de los asertos antiguos bajo el nuevo contrato autorizado». Los **nueve tests
reexpresados** quedan validados por alguien sin nada invertido en mi version.

**Y una critica que acepto entera:** mi `test_verificar_por_el_camino_REAL_llama_al_verificador`
—escrito precisamente para cerrar el patron del doble que tapa— **sigue siendo un doble que
tapa**: sustituye el verificador por una lambda, prueba que se llama e impide observar
justamente la ausencia de fuentes de H-01.

<!-- mandato-literal:inicio:v2r2 -->

# Revisión adversarial — V2, el lazo del CRM (R2, sobre el DIFF)

Eres el revisor adversarial de un cambio en un repositorio legal-tech en Python (Windows).
Trabajas **en solo lectura sobre copias congeladas**: no hay `.git`, y no debes modificar nada
bajo `../head` ni `../base`. Tu directorio de trabajo es el actual (`workdir`), el único sitio
donde puedes escribir además de `/tmp`.

## El objeto

- `../base/` — el árbol ANTES (commit `c8c4c48`).
- `../head/` — el árbol DESPUÉS (commit `318a081`).

El objeto es la **diferencia**, en ocho ficheros:

```
scripts/abrir_caso.py                    | 364 +
tests/test_abrir_caso_modo_v1.py         |  33 +-   <-- tests REEXPRESADOS
tests/test_abrir_caso_v2_autorizacion.py |  74 +
tests/test_abrir_caso_v2_etapas.py       | 403 +
tests/test_alta_crm_resultado.py         | 113 +
tests/test_apertura_v1_costuras.py       |   6 +-   <-- test REEXPRESADO
tests/test_apertura_v1_e2e.py            |  20 +-   <-- tests REEXPRESADOS
tests/test_escritura_censo.py            |  27 +-   <-- TECHO subido
```

`diff -ru ../base ../head` te da el diff. Contexto de diseño: el plan
`../head/docs/superpowers/plans/2026-09-14-apertura-v2-lazo-crm.md` (rev. 2) y su **§8**, que es
mi adjudicación de la R1 — **es también objeto de crítica**, no solo contexto.

## Qué hace el cambio

`scripts/abrir_caso.py --modo v1` corría tres etapas (`drive`, `crm`, `sala_maquina`) y tenía una
puerta que le **prohibía escribir en el CRM**. Ahora corre seis: se añaden `crm_alta`, `actuacion`
y `verificar`, y la puerta pasa de prohibir la escritura a **exigir que se declare** (`--crm` sin
default; omitirlo aborta).

## Puedes ejecutar, y conviene

El Python del sistema —`C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`— tiene
`pytest`, `yaml`, `dotenv`, `typer`, `httpx` y `filelock`. Copia `../head` a tu workdir y corre lo
que quieras. Usa `--basetemp` corto (p. ej. `C:/t/v2r2`). **No mutes `../head`.**

**No hay acceso al CRM real y no lo necesitas**: todo el diff se prueba con dobles. Si algo exige
red, dilo como SIN VERIFICAR.

## Qué quiero de ti

**1. Los tests que REEXPRESÉ son el primer foco, y el más incómodo.** Toqué nueve tests que ya
existían, en `test_abrir_caso_modo_v1.py`, `test_apertura_v1_e2e.py`, `test_apertura_v1_costuras.py`
y `test_escritura_censo.py`. Mi afirmación es que **ninguno quedó debilitado**: que cambié la
propiedad cuando el contrato cambió por decisión expresa, y que lo dejé escrito en el propio test.
**Atácalo.** ¿Alguno afirma ahora menos que antes? ¿Alguno pasaría con una implementación rota que
antes habría cazado? Compara aserto por aserto contra `../base`.

**2. La propiedad central: nadie escribe en el CRM sin declararlo.** El default de `--crm`
desapareció y la puerta rechaza su ausencia. ¿Hay algún camino —flag, modo, orden de validación,
`--hasta`, modo `libre`— por el que se alcance un POST sin que el operador lo haya pedido? ¿Y al
revés: algún camino que ahora aborte cuando antes funcionaba, rompiendo al modo `libre`?

**3. La reentrada, que es donde el dinero está.** `etapa_actuacion` persiste un recibo en
`00_Input/_recibo_actuacion.json` y lo pasa como `desde` para reanudar. La R1 midió que sin eso dos
corridas crean dos actuaciones. ¿La implementación lo consigue **de verdad**? ¿Qué pasa con un
recibo de otro caso, un recibo a medias, dos procesos a la vez, un `act_id` nulo, un fichero de
solo lectura? ¿Y si el recibo se guarda pero el proceso muere antes de devolverlo?

**4. La traducción de estados.** `_alta_crm` tiene seis desenlaces y `Recibo` cuatro; el
verificador, cuatro. ¿Alguno se colapsa, se pierde o se traduce al revés? Fíjate especialmente en
si algún fallo puede acabar declarado `hecha` o `saltada`.

**5. `COMPROBACIONES_DE_V2` y el bloqueo.** Solo esas tres comprobaciones deciden el estado de
`verificar`, y **solo cuando `crm == "api"`**. ¿Es correcta esa condición? ¿Deja pasar algo que
debería bloquear? ¿El conjunto puede quedarse vacío o desalineado de `verificar_apertura`?

**6. El techo del censo subió de 92 a 94** (`tests/test_escritura_censo.py`), con su declaración.
¿Es cierta esa declaración? ¿Son exactamente dos escrituras nuevas, o hay más sin contar? ¿Y era
cierto que `core/apertura_v1_estado.py` no servía de hogar?

**7. Lo de siempre: ¿los tests prueban lo que dicen?** Hay muchos dobles. ¿Alguno tapa el camino
real? (Ya me pasó en esta pieza con `alta_actuacion` y lo corregí; busca los que queden.)

Y dime si alguna decisión de diseño te parece equivocada aunque esté bien implementada.

## Formato de cada hallazgo

Escribe `INFORME.md` en tu workdir. Para cada hallazgo: **Id**, **título** de una línea, **dónde**
(fichero y línea de `../head`), **qué pasa** con el camino concreto, **cómo lo verificaste**
(comando y salida, o `SIN VERIFICAR` y por qué), **severidad** (`ALTO`/`MEDIO`/`BAJO`) y **coste
del remedio** (`trivial` / `acotado` / `estructural`).

Los dos ejes son independientes y los necesito **los dos**: sin el segundo, un defecto menor con
remedio estructural llega indistinguible de uno grave que se arregla en una línea.

Cierra con un **veredicto**: `SHIP`, `LISTA-CON-CAMBIOS` o `NO-SHIP`, y una línea de por qué.

## Dos cosas sobre el encargo

- **Volver sin hallazgos es un resultado válido.** Si el diff te parece correcto, dilo; no busques
  defectos para justificar la ronda. Prefiero un informe corto y cierto que uno largo y
  especulativo.
- **No apliques cambios.** Tu salida es el informe. Quien adjudica contrasta cada hallazgo contra
  la fuente y decide; no tienes la última palabra, y eso no te resta.

## Evidencia de no-mutación

Al empezar y al terminar, reporta el `sha256` de:

```
../head/scripts/abrir_caso.py
../head/tests/test_escritura_censo.py
```


<!-- mandato-literal:fin:v2r2 -->

<!-- informe-literal:inicio:v2r2 -->

# Revisión adversarial V2 — R2 sobre el diff

Objeto: `c8c4c48` (`../base`) → `318a081` (`../head`), ocho ficheros indicados en el encargo. Leídos también el plan rev. 2 y su §8, los productores y los consumidores reales. No se modificó ninguno de los árboles congelados. No se consultó el CRM ni Drive.

**Resultado: siete hallazgos; tres ALTO y cuatro MEDIO.** No encuentro una relajación injustificada de los asertos antiguos bajo el nuevo contrato autorizado. Sí encuentro defectos en las etapas nuevas que la suite verde no detecta.

## Evidencia y reproducción

La copia ejecutable es `workdir/review_copy`. Sólo se añadió allí `tests/test_review_r2_probes.py`; no se cambió código de producto. Las sondas usan casos sintéticos. En las de actuaciones se conserva `alta_actuacion` y su validación de recibos; se sustituyen resolución remota, aprendizaje, creación, vínculo y lectura de comprobación. Los IDs 900/901 son efectos contados por esos dobles, no creaciones en el CRM real.

Comandos PowerShell, desde `workdir`:

```powershell
$P = 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
& $P auditar_estatico.py
& $P repro_mutante.py
Set-Location .\review_copy
$Q = @('-o', 'addopts=', '-p', 'no:cacheprovider', '-q', '--tb=short', '--basetemp=../probe_tmp')
& $P -m pytest @Q -s tests/test_review_r2_probes.py
```

Los comandos de cada hallazgo usan estas variables y este último directorio. Los temporales quedan dentro de `workdir`, fuera de la copia ejecutada.

| Ejecución | Resultado | Evidencia |
|---|---|---|
| Siete ficheros de tests del diff | 96 pasan | `suite_diff.log` |
| CLI anterior, salidas bajo mutex, concurrencia y registro de control | 79 pasan | `suite_ampliada.log` |
| Sondas de esta revisión | 23 pasan, reproduciendo los comportamientos descritos | `probes.log` |
| Mutante que elimina dos comprobaciones decisorias | 96 pasan: sobrevive | `mutante_comprobaciones.log` |
| Censo y comparación AST de asertos | 92 → 94; detalle por test | `censo_asertos.log` |

La batería adicional se ejecutó con `python -m pytest -o addopts= -p no:cacheprovider -q --tb=short --basetemp=../mutex_tmp tests/test_abrir_caso_cli.py tests/test_abrir_caso_exit_bajo_mutex.py tests/test_case_mutex_concurrencia.py tests/test_apertura_v1_control_files.py`. La batería del diff es la lista completa de siete módulos que conserva `repro_mutante.py`, ejecutada primero sin mutación.

No se ejecutó la suite completa del repositorio ni la aceptación contra el expediente 636. Payloads, efectos y lectura del servicio real: **SIN VERIFICAR**, por ausencia de acceso y por el alcance de solo lectura. Los verdes de las sondas significan reproducción confirmada, no corrección del producto.

## 1. Tests reexpresados: comparación aserto por aserto

El diff afecta al cuerpo/firma de **once funciones de test existentes**, contando el renombrado: seis en modo, cuatro E2E y una costura. Además cambia el techo global del censo; ningún cuerpo de test de ese fichero cambia. Es un conteo del diff, no una inferencia a partir de los nueve anunciados.

| Test en `head` | Antes → después; evaluación |
|---|---|
| `test_abrir_caso_modo_v1.py:31`, `test_v1_admite_crm_api_DECLARADO` | Un error y texto `--crm skip` → lista vacía para `api`. Sustitución deliberada de la prohibición absoluta; justificada por el contrato nuevo. |
| `:48`, `test_v1_rechaza_el_default_de_crm` | Default exactamente `api` → exactamente `None`; se mantiene el rechazo de la omisión por el validador. No pierde la propiedad de autorización. |
| `:77`, `test_v1_acumula_los_errores` | Entrada CRM `api` → `None`; conserva exactamente dos errores. |
| `:100`, `test_v1_aborta_antes_de_crear_el_esqueleto` | Conserva exit 1 y raíz vacía; cambia el mensaje esperado a `--crm` + `declarar`. Coherente con el rechazo nuevo. |
| `:238`, `test_v1_acumula_todos_los_errores` | Entrada `api` → `None`; conserva exactamente cinco errores. |
| `:245`, `test_v1_aborta_antes_de_la_autoderivacion_y_de_la_identidad` | Conserva los dobles que impiden esas operaciones, exit 1 y raíz vacía; cambia sólo la señal del error CRM. |
| `test_apertura_v1_costuras.py:117`, `test_costura_main_PASA_el_hasta_a_la_secuencia` | Añade `crm` a la firma del doble. Conserva exactamente `visto['hasta'] == 'drive'`. No pierde cobertura anterior; tampoco prueba la propagación de `crm`. |
| `test_apertura_v1_e2e.py:107`, recorrido | Lista completa V1 → lista completa V2. Conserva los tres estados `hecha`, contadores 1/1/1, estado global, ninguna no ejecutada y valores de `force`/`element`. Añade `saltada` para posiciones 3 y 4. |
| `:124`, evento | Conserva tipo de evento, estado global y diccionarios completos de las tres etapas antiguas. Añade nombres de las seis y estados de las dos escritoras. |
| `:166`, fallo CRM | Conserva bloqueo y cero OCR; amplía exactamente las no ejecutadas a las cuatro posteriores. |
| `:179`, parada Drive | Conserva contadores 1/0/0 y `force`; amplía exactamente las no ejecutadas a las cinco posteriores. |
| Censo | Conserva detector, productores, desigualdad y prueba de igualdad contra el techo. Cambio de umbral explicado y numéricamente exacto: apartado 6. |

**No he encontrado un defecto antiguo que esos cambios de aserto dejen ahora pasar, descontando la autorización expresa de `api`.** La afirmación adicional de los E2E es más amplia que su evidencia: sus comentarios dicen que las tres nuevas salen `saltada`, pero el código sólo lo exige para dos; `verificar` sale `hecha`. Tampoco afirmar `saltada` demuestra cero POST. Los tests nuevos de autorización de cada escritora sí incorporan un efecto que falla si se llama. No confundo esa cobertura añadida incompleta con una pérdida del contrato antiguo.

## 2. Autorización y modo libre

No encontré un bypass en `main`: `validar_modo` corre antes de resolver el default, identidad, mutex e intake. `None` es rechazado en V1 y sólo después se transforma en `api` para libre. `force`, `dry_run`, fuente y parada inválidos no esquivan esa puerta.

La sonda `test_cli_autorizacion_y_hasta` ejecuta el CLI real con efectos aislados. Omitir CRM con `hasta=None` y con cada una de las seis etapas da exit 1, cero llamadas al alta y cero casos. `skip` no llama al alta en V1; `api --hasta sala_maquina` tampoco; `api --hasta crm_alta` sí. Libre sin flag llega a `_alta_crm(crm_mode='api')` y termina con exit 0; libre con skip conserva `skip`. No es una garantía universal de «nadie escribe sin flag»: libre mantiene intencionadamente la autorización por su gate/`--yes` y su default histórico.

La ayuda conserva textos anteriores (`scripts/abrir_caso.py:1656` exige skip y `:1659` enumera sólo tres etapas), aunque sí dice que la parada es DESPUÉS. Conviene alinearla al contrato; no afecta a las pruebas de autorización anteriores.

## 3. Reentrada

### H-02 — Un recibo ilegible se convierte en permiso para crear otra actuación

- **Dónde:** `../head/scripts/abrir_caso.py:998-1008`, consumido en `:1085` y `:1114`; test que sanciona el comportamiento en `tests/test_abrir_caso_v2_etapas.py:335` (función `test_un_recibo_corrupto_se_ignora_y_no_tumba_la_etapa`).
- **Qué pasa:** después de crear 900, un recibo truncado o con esquema incorrecto retorna `None`, igual que un fichero inexistente. `alta_actuacion(desde=None)` crea 901. Un `OSError` de lectura tiene la misma traducción. Con un recibo corrupto de solo lectura, el POST sucede antes de descubrir que tampoco puede guardarse: dos intentos crean dos actuaciones y ambos devuelven fallo de persistencia.
- **Cómo lo verifiqué:** `& $P -m pytest @Q -s tests/test_review_r2_probes.py -k 'recibo_corrupto or recibo_solo_lectura'`. Salidas: `RECIBO_CORRUPTO ... hecha CREADAS ['900', '901']`; `SOLO_LECTURA fallo fallo CREADAS ['900', '901']`, con `Permission denied` real de Windows.
- **Severidad:** ALTO. **Coste del remedio:** acotado. Distinguir ausencia de ilegibilidad y fallar cerrado en la segunda; persistencia atómica para no destruir un recibo previo durante su actualización. El test actual debe cambiar de propiedad: un JSON roto no acredita que no hubo escritura.

### H-03 — La actuación tampoco queda cubierta frente al corte anterior al recibo

- **Dónde:** `../head/scripts/abrir_caso.py:1113-1120`; afirmación contraria en el plan `docs/superpowers/plans/2026-09-14-apertura-v2-lazo-crm.md:697` y cierre de R1 en su §8.
- **Qué pasa:** la primera huella de la operación se guarda sólo después de que `alta_actuacion` termine. Si el proceso muere después del efecto remoto y antes de guardar, la siguiente corrida no tiene `desde` y crea otra. Una escritura atómica del recibo posterior no cierra esta ventana. El marcador general de ronda abierta sólo avisa; `main` abre una ronda nueva y continúa.
- **Cómo lo verifiqué:** `& $P -m pytest @Q -s tests/test_review_r2_probes.py -k crash_antes`. Inyecté `KeyboardInterrupt` en el límite previo a `_guardar_recibo`, una vez retornado el helper real: `CRASH_ANTES_GUARDAR hecha CREADAS ['900', '901']`. Control opuesto: guardar y morir antes de devolver la etapa deja el relanzamiento en `saltada`, sin nueva creación (`CRASH_DESPUES_GUARDAR`). Se simula la interrupción del proceso; no se pretende haber probado un corte eléctrico.
- **Severidad:** ALTO. **Coste del remedio:** estructural. Hace falta intención durable previa y una política de conciliación/bloqueo para el intento sin recibo, o una aceptación explícita de esta deuda también para actuaciones. El §7 sólo reconoce la ventana del alta de expediente y declara cubierta la actuación: esa distinción es falsa.

### H-04 — El atajo de `verificada` evita la validación de identidad y de `act_id`

- **Dónde:** `../head/scripts/abrir_caso.py:1085-1089`; contrato evitado: `core/sudespacho_actuaciones.py:1025-1074`.
- **Qué pasa:** antes de leer el destino, se acepta cualquier dataclass con `estado='verificada'`. Un recibo de otro expediente o incluso `{"estado":"verificada"}` produce `saltada`, sin pendiente, diciendo que ya existe una actuación. El core rechaza ambos recibos, pero este atajo nunca lo llama. No crea ni vincula una actuación ajena: oculta que falta la propia. Con `--hasta actuacion` tampoco corre la comprobación posterior como etapa decisoria.
- **Cómo lo verifiqué:** `& $P -m pytest @Q -s tests/test_review_r2_probes.py -k recibo_verificado`. Para `exp_id='OTRO', act_id='999'` y para ID nulo: `saltada ... POST []`; ambas entradas levantan `ActuacionError` al pasarlas al validador real del core.
- **Severidad:** MEDIO. **Coste del remedio:** acotado. Validar estructura y pertenencia al destino antes del atajo, reutilizando el contrato del core.

Con un recibo válido `incompleta`, la reentrada real reutiliza el ID y no crea otro. Con `incierta`, el core rechaza el reintento y no crea nada. Un recibo válido ya guardado sobrevive a la muerte antes del retorno: control positivo de H-03.

Sobre dos procesos: el CLI envuelve las nuevas etapas en el mutex existente (`main:1846` y siguientes). Las doce carreras del test de concurrencia dieron un ganador y un perdedor; también pasó el control de un proceso solo. No hay evidencia de un bypass nuevo de esa exclusión en el diff. No he ejecutado dos CLI V2 completos contra un CRM compartido ni una pérdida de lease durante el POST: **SIN VERIFICAR**. Invocar `etapa_actuacion` suelta carece de mutex propio; no presento ese uso fuera del wrapper como un fallo de concurrencia del CLI.

## 4. Traducción de estados

Los seis resultados de `_alta_crm` tienen correspondencia expresa: `creado` → hecha; `ya_vinculado`, `declinado`, `omitido` → saltada; `fallo_post`, `fallo_registro` → fallo. La excepción de política se convierte en fallo por la etapa. `fallo_registro` conserva el ID en su detalle. No he encontrado una inversión en esa tabla. El estado creado con aviso de cuantía local pertenece al llamador libre; V2 pasa `cuantia=None`.

Los cuatro estados válidos del recibo recién devuelto se traducen como se pide: sólo verificada es hecha; los otros tres fallan. Los problemas están antes de esa tabla (H-02/H-04), y el mensaje de persistencia afirma «creada» incluso si el recibo era no_intentada o incierta; no transforma por ello la etapa en éxito.

### H-06 — Un YAML presente pero inválido se presenta como firmante ausente

- **Dónde:** `../head/scripts/abrir_caso.py:1043-1052`, `:1071-1083`; plan rev. 2, línea 32.
- **Qué pasa:** `_firmante_de` captura cualquier error del cargador y devuelve cadena vacía. Un YAML mal escrito, o un error en otro campo de la ficha que impida cargarla, termina en `saltada` + `actuacion_sin_firmante`. Se pierde la causa y no se aplica la excepción explícita del plan: dato humano presente y mal escrito corta. Un username inválido que sí se consigue cargar, en cambio, falla al pasar por el core.
- **Cómo lo verifiqué:** `& $P -m pytest @Q -s tests/test_review_r2_probes.py -k yaml_invalido`. Con `firmante: [mal` en el fichero: `YAML_MAL_ESCRITO saltada ['actuacion_sin_firmante']`, cero creaciones. El test existente `test_un_yaml_ilegible_no_inventa_firmante` exige precisamente esta salida y no exige revelar el error de lectura.
- **Severidad:** MEDIO. **Coste del remedio:** acotado. Separar fichero/dato ausente de ficha inválida y propagar esta última como fallo con su causa.

## 5. Comprobaciones de V2 y bloqueo

### H-01 — La verificación decisoria usa `SinRed` y la comprobación real se repite sin poder corregir el bloqueo

- **Dónde:** `../head/scripts/abrir_caso.py:1160-1162`, `:1175-1187` y `:1960`; defaults en `core/verificar_apertura.py:1145-1148`.
- **Qué pasa:** `va.verificar(cd)` selecciona `SinRed`. Con un expediente registrado en el frontmatter real, las tres comprobaciones CRM fallan por no poder consultar, aunque el alta y la actuación estén bien. `crm='api'` convierte eso en bloqueo. Después se sigue llamando a `_informar_v1_y_verificar`, que sí construye `DeLaRed`: hay dos verificaciones y la segunda no cambia el exit. Contradice la retirada expresa de la verificación duplicada del plan, línea 638.
- **Cómo lo verifiqué:** `& $P -m pytest @Q -s tests/test_review_r2_probes.py -k verificador_default`. Verificador real y fixture con ambas listas del índice, top-level y espejo `meta`: `VERIFICAR_DEFAULT fallo ... crm_actuacion, crm_ficha, cuantia_coherente`. El mismo caso con fuente sintética legible devuelve las tres `ok`. Al encadenar etapa e informe final: `DOS_VERIFICACIONES ['SinRed', 'Fuente'] EXIT 1`; el segundo informe dice cero fallos. Mi primera fixture sólo tenía el espejo `meta`, como el E2E existente, y daba pendientes: se corrigió la sonda antes de confirmar el hallazgo.
- **Severidad:** ALTO. **Coste del remedio:** acotado. Cablear las fuentes reales en la comprobación decisoria y reconciliar el único punto de verificación, preservando el diagnóstico en paradas anticipadas según el contrato que se decida.

La condición `crm == 'api'` es defendible para no exigir efectos omitidos voluntariamente con skip; también convierte defectos de un CRM ya existente en pendientes. Eso es una política de diagnóstico, no una prueba de que el CRM esté sano. No atribuyo a skip una falsa certificación de completitud: el estado global mantiene pendientes. `pendiente` y `sin_implementar` se conservan como pendientes, y los fallos ajenos a V2 tampoco bloquean. Las filas decisorias en fallo pierden su explicación concreta: sólo se conserva su ID; el informe posterior puede aportar una foto distinta, como reproduce H-01.

### H-07 — El guard permite perder dos de las tres comprobaciones decisorias

- **Dónde:** `../head/tests/test_abrir_caso_v2_etapas.py:223` (función `test_las_comprobaciones_de_v2_existen_de_verdad`), y pruebas de bloqueo de ese fichero; constante en `scripts/abrir_caso.py:936`.
- **Qué pasa:** el guard sólo exige subconjunto no vacío de IMPLEMENTADAS. La prueba que exige bloqueo usa únicamente `cuantia_coherente`. Eliminar `crm_ficha` y `crm_actuacion` deja sin bloqueo sus fallos y toda la batería del diff sigue verde. El conjunto actual sí contiene los tres nombres correctos; el hallazgo es una protección incompleta de la propiedad central, no afirmar que hoy está vacío.
- **Cómo lo verifiqué:** desde `workdir`, `& $P repro_mutante.py`. Sustitución sólo en memoria por `frozenset({'cuantia_coherente'})`; resultado: `96 passed in 7.17s`. Código y salida conservados.
- **Severidad:** MEDIO. **Coste del remedio:** acotado. Exigir cada comprobación requerida y parametrizar su efecto decisorio; verificar también que las filas reales emitidas corresponden al conjunto, en vez de confiar sólo en otra constante.

## 6. Censo, hogar del recibo y fichero de protocolo

El censo es correcto: 92 → 94; `abrir_caso.py` pasa de tres a cinco sitios y los dos añadidos son exactamente `mkdir` y `write_text` de `_guardar_recibo`, líneas 1013-1014. No hay otra primitiva de escritura añadida en el diff de producto. Esto cuenta sitios locales, no el número de efectos remotos que ahora se pueden ejecutar. No he verificado la conversación en que se autorizó subir el techo; sí la declaración y su correspondencia con el código.

El formato vigente de `apertura_v1_estado.RondaV1` no almacena un recibo entre corridas: `abrir()` crea una ronda sin etapas previas y sobrescribe el marcador. Usarlo sin cambiar el contrato perdería la reentrada. Eso no demuestra que el módulo sea incapaz de alojar un almacén distinto, ni justifica omitir la escritura atómica que ya tiene en `:73-96`. La necesidad de persistir es cierta; la inevitabilidad de esta forma concreta no lo es.

### H-05 — El nuevo recibo se clasifica como documento y carece de política de sincronización

- **Dónde:** `../head/scripts/abrir_caso.py:987-1016`, al crear `00_Input/_recibo_actuacion.json`; registros consumidores en `core/intake_control.py:38`, `core/config.py:391` y `tests/test_apertura_v1_control_files.py`.
- **Qué pasa:** el recibo no está registrado como protocolo. La siguiente sala de máquina lo inventaría con hash y extensión JSON como documento del expediente. Tampoco lo reconocen las exclusiones del merge ni el permiso de edición de protocolo del plugin. Dos versiones modificadas se tratan como contenido concurrente y dan CONFLICT. El guard existente sólo recorre lo que declara `apertura_v1_estado`, por lo que este nuevo productor queda fuera y el guard pasa.
- **Cómo lo verifiqué:** `& $P -m pytest @Q -s tests/test_review_r2_probes.py -k 'entra_en_inventario or merge_recibo'`. `REGISTROS_RECIBO False False False False`; `inventariar()` devuelve una fila con `rel_path='_recibo_actuacion.json'`; `plan_merge()` devuelve `CONFLICT` para esa ruta cuando local y remoto difieren del baseline. No se ejecutó un checkin remoto.
- **Severidad:** MEDIO. **Coste del remedio:** estructural. Excluirlo del inventario documental es acotado; completar el remedio requiere definir quién conserva y transporta el recibo entre copias. No recomiendo copiar a ciegas la exclusión de `_apertura_v1.json`: aquel estado es de la ronda/copia, mientras que perder este recibo al cambiar de copia puede volver a crear la actuación. Hace falta una política explícita de recibo entre copias, con su registro y pruebas.

## 7. ¿Los dobles prueban lo que dicen? Decisiones de diseño

El test llamado `test_verificar_por_el_camino_REAL_llama_al_verificador` sustituye el propio verificador por una lambda de un argumento que devuelve informe vacío. Prueba que se llama, pero precisamente impide observar la ausencia de fuentes y sanciona `hecha` sin ninguna comprobación. Explica H-01; no prueba el extremo consumidor. Los tests E2E construyen sólo el espejo `meta.sudespacho_expedientes`, que lee la etapa CRM, mientras que el verificador lee la lista top-level: no ejercitan el bloqueo CRM sobre un índice producido completo.

El espía de `alta_actuacion` mejoró la cobertura de argumentos y asunto; sigue sustituyendo el helper entero. Las sondas de esta revisión bajan un nivel para ejercer el contrato real de `desde`. Así se distingue la reentrada incompleta que sí funciona de los atajos que la eluden. El test de recibo corrupto no sólo omite un ataque: fija como comportamiento deseable volver a intentar sin evidencia.

Discrepo de tres decisiones: equiparar recibo ilegible a inexistente; declarar cubierta la actuación con persistencia únicamente posterior al efecto; introducir un recibo por caso sin definir su vida entre copias. Son problemas de contrato aunque el código siga el plan. El recorte de `crm_ficha` y la condición no bloqueante para diagnóstico V3, en cambio, son coherentes con el alcance autorizado. El §8 de adjudicación no basta para cerrar H-03: la reproducción de la reentrada normal no acredita recuperación ante interrupciones.

## Lo que intenté refutar y NO pude

- Conservación de los asertos antiguos bajo la sustitución de contrato autorizada: no encontré una relajación injustificada.
- Rechazo temprano de la omisión de CRM en V1, incluso con parada anticipada; conservación del default de libre.
- Parada inclusiva: el alta se ejecuta al pedir `--hasta crm_alta`.
- Cero llamada al alta con skip en las dos nuevas escritoras; distinción explícita de los seis desenlaces de `_alta_crm`.
- Reentrada de un recibo válido incompleto; rechazo sin creación de uno incierto; recuperación después de guardar un recibo válido y antes del retorno.
- Exclusión de dos procesos que compiten por el mutex existente, dentro de la cobertura descrita.
- Exactitud del incremento del censo y limitación del formato actual del estado por ronda.

## Evidencia de no mutación

SHA-256 calculados al empezar y al terminar; coinciden:

| Fichero congelado | Inicial | Final |
|---|---|---|
| `../head/scripts/abrir_caso.py` | `64d06109c2a60adfa789ce49859906ddea0520872985e3989e27508d27af6bd3` | `64d06109c2a60adfa789ce49859906ddea0520872985e3989e27508d27af6bd3` |
| `../head/tests/test_escritura_censo.py` | `7dba6838beced5744df2fd40dbd5f27a4dbc48d39a7dc1655e0cce3f97965ea5` | `7dba6838beced5744df2fd40dbd5f27a4dbc48d39a7dc1655e0cce3f97965ea5` |

## Veredicto

**NO-SHIP** — la verificación decisoria bloquea sin consultar el CRM y la reentrada todavía puede duplicar actuaciones o aceptar un recibo ajeno; la suite del diff no detecta esos caminos.


<!-- informe-literal:fin:v2r2 -->
