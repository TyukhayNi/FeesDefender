---
tipo: revision-adversarial
objeto: diff aa46fcc..e55468c de las filas #42 y #47 (MEJORAS #296 y #301; core/intake_drive.py, scripts/abrir_caso.py, scripts/audit_ev_folder_names.py, el precheck de la skill organizar-sala-lectura y sus tests), contra el plan docs/superpowers/plans/2026-09-26-token-drive-y-carpetas-w-delante-296-301.md
objeto_rev: "1"
commit: e55468c
ronda: "1"
revisor: Codex
modelo: gpt-6-sol
esfuerzo: high
velocidad: default
veredicto: NO-SHIP
marcador_nonce: k4vd
sha256_informe: fc0c1e8016e1f5cc3cc2272ae60937f177a41892e2aa6608bff0d3a549111241
adjudicado_en: docs/superpowers/plans/2026-09-26-token-drive-y-carpetas-w-delante-296-301.md §7
---

# Acta — R1 adversarial sobre el DIFF de las filas #42 y #47 (el token y la carpeta de Drive; las carpetas con el W-code delante)

Objeto: el diff `aa46fcc..e55468c`, que hace que el alta diga por qué no lee Drive (`MEJORAS #296`)
y que entienda las carpetas de E&V con el W-code delante (`MEJORAS #301`). **Una ronda**: toca
`core/`, `scripts/` y una skill, sin decidir quién escribe ni poder destruir datos de cliente.
Fila ordinaria de la política: `gpt-6-sol` · `high` · `default`, y **quinta y última fila del
ledger de calibración de la #38**.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.4` (binario `13995fba801849b0`), `gpt-6-sol` · `high` — **releídos** del `turn_context` del rollout y de la cabecera del `_stdout.log`; velocidad `default` **afirmada** desde el lanzador conservado |
| Objeto | `base/` (`aa46fcc`) y `head/` (`e55468c`), copias `git archive` fuera del repo, más `diff.patch` y `commits.txt` |
| `sha256` del objeto | **idéntico al abrir y al cerrar**: 2.889 ficheros, comparados por él y por mí contra una reextracción de los dos commits desde git |
| `sha256` del informe | `fc0c1e8016e1f5cc3cc2272ae60937f177a41892e2aa6608bff0d3a549111241` |
| Tiempos | lanzado a las 20:33:09; `INFORME.md` a las 20:45:43; `exec` salió a las 20:45:59 con `exit=0` |
| Veredicto | `NO-SHIP` — 7 hallazgos: 1 `alta`, 3 `media`, 3 `baja` |

## 0. Mandato, literal

# Mandato — R1 adversarial sobre el diff de las filas #42 y #47: el token y la carpeta de Drive dicen por qué no están, y las carpetas con el W-code delante (MEJORAS #296 y #301, FeesDefender)

## 0. Higiene y reglas

- Tu directorio de trabajo debe contener solo: `MANDATO.md`, `base/`, `head/`, `diff.patch` y
  `commits.txt`. Si hay cualquier otro fichero, **no lo leas** y decláralo en la primera línea del
  informe.
- `base/` es el commit `aa46fcc` (main) y `head/` es `e55468c` (la rama del cambio), extraídos con
  `git archive`, sin `.git`. Son de **solo lectura**: si necesitas ejecutar o modificar algo, copia
  a una carpeta tuya dentro de tu directorio de trabajo. Calcula el SHA-256 de todos los ficheros de
  `base/` y `head/` al abrir y al cerrar, y di si coinciden.
- Python con las dependencias del repo:
  `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe` (tiene pytest; **no** tiene
  pytest-randomly, así que no hacen falta semillas). Usa `--basetemp` con una ruta **relativa**
  dentro de tu directorio de trabajo.
- No accedas a red, a Google Drive, al CRM ni al repositorio real, y no ejecutes `rclone`: la
  configuración de rclone de esta máquina guarda credenciales en claro. Donde el diff habla de lo
  que hace rclone, razona desde el código y los tests, o decláralo SIN VERIFICAR.

## 1. Objeto

El diff `aa46fcc..e55468c` (`diff.patch`, `commits.txt`). Cierra dos entradas del backlog salidas
de dos aperturas reales de expedientes:

- **`MEJORAS #296`**: el alta de un expediente (`scripts/abrir_caso.py`) abortaba diciendo que no
  podía derivar `--team-id` por «token/red» con el token vigente. Según el backlog, `rclone config
  show gdrive_ev` tardó 3,9-6,7 s con otra corrida de rclone en marcha, y el lector del token
  (`core/intake_drive.py`) tenía 5 s y tragaba el timeout como «no hay token». El diff introduce un
  lector único con otro timeout y un motivo tipado (`obtener_token_drive`, `_leer_bloque_token`),
  una lectura de la carpeta que devuelve su motivo (`leer_carpeta_drive`), los mensajes del alta y
  del auditor `scripts/audit_ev_folder_names.py`, y el precheck de la skill
  `organizar-sala-lectura` (`scripts/precheck_rclone.py`, versión 1.19) con un código propio para el
  timeout y la detección del remote inexistente.
- **`MEJORAS #301`**: `parse_ev_folder_name` no reconocía las carpetas de Engel & Völkers que llevan
  el W-code delante («W-XXXX - dirección - consultor»). El diff las acepta y el alta quita la ciudad
  que precede a la dirección en una de las plazas, solo si coincide con `--ciudad`.

El plan con lo medido, el diseño, los tests y lo que declara no cubierto está en
`head/docs/superpowers/plans/2026-09-26-token-drive-y-carpetas-w-delante-296-301.md`; las entradas
del backlog, en `head/docs/MEJORAS_FUTURAS.md` (#296 y #301). El censo de nombres de carpeta y las
mediciones de tiempos del plan salen de datos reales a los que no tienes acceso: decláralos SIN
VERIFICAR, salvo lo que puedas razonar desde el código.

## 2. Qué te pido, numerado

1. **El lector del token** (`_leer_bloque_token`, `obtener_token_drive`, `_get_drive_access_token`
   en `head/core/intake_drive.py`). ¿Distingue de verdad cada causa, o hay caminos en que una causa
   sale con el nombre de otra? ¿Conserva el comportamiento anterior que los demás consumidores de
   `_get_drive_access_token` esperan (lo defensivo con `expiry`, la renovación, no lanzar)? ¿Es
   razonable el nuevo timeout y su coste cuando rclone se cuelga de verdad? ¿Puede el motivo
   arrastrar algo de la salida de rclone, que lleva el token y el `client_secret`?
2. **`leer_carpeta_drive`** y el envoltorio `get_drive_folder_info`. ¿Se conserva el comportamiento
   anterior (reintentos por cuota, `None` ante los mismos fallos)? ¿Los motivos son ciertos para cada
   salida?
3. **El alta** (`head/scripts/abrir_caso.py`: `_autoderivar_drive_ev`, `_direccion_de_la_carpeta`,
   `_sin_la_ciudad_delante`, `_derivar_team_id` y el bloque 5.1.b). ¿Llega el motivo a los dos
   mensajes? ¿Puede la retirada de la ciudad quitar algo que es parte de la dirección, o dejar la
   ciudad donde debía quitarla? ¿Cambia algo más del flujo del alta que el diff no declara?
4. **El parser** (`parse_ev_folder_name`). ¿Qué acepta ahora que no debería —un nombre del que la
   «dirección» derivada no es una dirección— y qué rechaza que sí? Ataca la regla del último « - »
   (consultor), el separador tras el W-code, los guiones sin espacios, el W-code solo y la
   convivencia con el formato de siempre. Recuerda que la dirección derivada acaba en el
   identificador del expediente, que se propaga a otros sistemas: una derivación equivocada es peor
   que pedir el dato.
5. **El precheck de la skill** (`head/.claude/skills/organizar-sala-lectura/scripts/precheck_rclone.py`
   y el Paso 4 de su `SKILL.md`). ¿Son correctos los códigos? ¿La detección del remote inexistente es
   frágil respecto a versiones de rclone, y qué pasa si falla?
6. **La costura de los tests del alta**: nueve stubs de `head/tests/test_abrir_caso_cli.py` pasaron de
   `get_drive_folder_info` a `leer_carpeta_drive`. ¿Queda algún test que ya no ejerza lo que dice, o
   algún camino del alta que llame a la red en un test?
7. **Los tests nuevos y el endurecido.** ¿Prueba cada uno lo que su nombre dice? ¿Alguno pasaría con
   una implementación equivocada? Si puedes, introduce en una copia tuya variantes defectuosas
   concretas y di qué test las detecta y cuál no.
8. **El arnés de mutación** (`head/tests/_mutantes_intake_drive_296_301.py`). ¿Sus mutantes atacan las
   fronteras que el plan declara, o dejan alguna sin mutante? No hace falta que lo ejecutes entero.
9. **El §5 del plan.** ¿Alguno de esos límites es en realidad un defecto que merece remedio ahora?

## 3. Formato del informe

Escribe `INFORME.md` en tu directorio de trabajo, en castellano. Por cada hallazgo: identificador
(H-01, H-02…), **severidad** (alta · media · baja) y **coste del remedio** (trivial · acotado ·
estructural), dónde (fichero:línea en `head/`), la evidencia reproducible y el remedio que propones.
Añade una sección «Lo que intenté refutar y no pude» y otra «SIN VERIFICAR».

No encontrar defectos es un resultado legítimo: si es tu conclusión, dilo, con la evidencia de lo
que probaste. Termina el informe con una línea que contenga solo el veredicto, uno de: SHIP,
LISTA-CON-CAMBIOS, REQUIERE-REVISION, NO-SHIP.

Como último mensaje, da la ruta de `INFORME.md` y su SHA-256 calculado sobre el contenido en UTF-8,
con saltos LF y un único salto final.

## 1. Informe recibido, sin modificar (Codex, 2026-09-26)

<!-- informe-literal:inicio:k4vd -->
Al abrir el directorio había un fichero adicional, `_stdout.log`; no lo leí.

# R1 adversarial — `aa46fcc..e55468c` (#296 y #301)

**Veredicto propuesto:** detener la derivación automática de direcciones ambiguas antes de usarla en un alta real. La dirección entra en el identificador del expediente y se propaga al CRM y a Gmail. Los demás defectos afectan sobre todo a la veracidad del diagnóstico.

**Método y custodia.** Revisé `diff.patch`, `commits.txt`, el plan, el código de `base/` y `head/`, y ejecuté pruebas y sondas exclusivamente en `scratch/work/`, copia de `head/`. No ejecuté `rclone` ni accedí a red, Drive, CRM o repositorio real. Al abrir y cerrar calculé SHA-256 de **todos** los ficheros: `base/` 1.443/1.443 y `head/` 1.446/1.446; los manifiestos ordenados coinciden exactamente. El directorio contiene además `scratch/` e `INFORME.md`, creados para esta revisión.

## Hallazgos

### H-01 — Alta; coste estructural. El último separador puede truncar la dirección o convertir un consultor en dirección

**Dónde:** `head/core/intake_drive.py:376-417`; consumidor `head/scripts/abrir_caso.py:1848-1874`.

**Evidencia reproducible:** `parse_ev_folder_name("W-02UIQU - Calle Mayor 5 - Portal 2")` devuelve `("Calle Mayor 5", "W-02UIQU")`: si «Portal 2» pertenece a la dirección y no hay consultor, se pierde. `parse_ev_folder_name("W-02UIQU - Ana P")` devuelve `("Ana P", "W-02UIQU")`: si solo consta el consultor, se inventa una dirección. Ambas formas son indistinguibles por la sintaxis que admite el parser. `_direccion_de_la_carpeta` solo comprueba que la cadena no esté vacía y que coincida el W-code; por tanto puede pasarla al `case_id`. Los seis parámetros positivos de `test_parse_folder_w_code_DELANTE` (`head/tests/test_intake_drive.py:588-603`) no prueban estas dos fronteras; el arnés tampoco las muta (`head/tests/_mutantes_intake_drive_296_301.py:114-143`). El test del auditor (`head/tests/test_audit_ev_folder_names.py:25-42`) solo exige código 0 para la carpeta con W-code delante, no la dirección resultante.

**Remedio:** no asignar automáticamente una dirección cuando el sufijo pueda ser tramo de dirección o el único tramo pueda ser consultor. Exigir `--direccion` o una confirmación explícita hasta disponer de un dato independiente que identifique al consultor o a la dirección; añadir pruebas de ambos contraejemplos en parser y CLI. Un heurístico de «parece persona» o «parece portal» no cierra la ambigüedad.

### H-02 — Media; coste acotado. Un 403 de cuota recibe el nombre de un fallo de permisos

**Dónde:** `head/core/intake_drive.py:683-691`.

**Evidencia reproducible:** en la copia, con token simulado y respuesta HTTP 403 cuyo JSON lleva `reason: dailyLimitExceeded`, `leer_carpeta_drive("FID")` devuelve `(None, "la Drive API respondió HTTP 403: sin permiso sobre la carpeta")`. `_is_rate_limit_response` solo reconoce `rateLimitExceeded` y `userRateLimitExceeded` (`head/core/intake_drive.py:617-627`); otros motivos de 403 reciben indiscriminadamente la pista «sin permiso». Si se agotan los reintentos con `userRateLimitExceeded`, la última frase también dice literalmente `rateLimitExceeded`. El test nuevo solo comprueba que un 404 incluya «404» (`head/tests/test_intake_drive.py:1125-1136`); las pruebas heredadas sí conservan el número de reintentos, pero no la exactitud del motivo.

**Remedio:** reservar «sin permiso» para un motivo de permisos identificado; en los demás 403 dar el código sin atribución causal, o leer y clasificar un `reason` permitido sin incluir el cuerpo completo. Mantener el motivo de cuota observado al agotar reintentos.

### H-03 — Media; coste acotado. La retirada de la ciudad también cambia el formato antiguo

**Dónde:** `head/scripts/abrir_caso.py:1848-1873`, especialmente línea 1868; `head/scripts/abrir_caso.py:1877-1888`.

**Evidencia reproducible:** `_direccion_de_la_carpeta("Santander. Calle Mayor 5 - W-02UIQU", "W-02UIQU", "Santander")` devuelve `"Calle Mayor 5"`. En `base/scripts/abrir_caso.py:1839-1860`, ese mismo formato conserva `"Santander. Calle Mayor 5"`. El código nuevo aplica `_sin_la_ciudad_delante` a ambos órdenes de carpeta, aunque el caso medido del plan es el W-code delante en SaRS1. Si el prefijo del nombre antiguo forma parte de la dirección, se pierde sin confirmación. A la inversa, `"SANTANDER, Calle Mayor 5"` no se recorta porque se exige el literal `". "`; no hay evidencia accesible de que esa variante exista. Los dos tests CLI nuevos cubren ciudad coincidente en formato nuevo y `AVDA.` distinta (`head/tests/test_abrir_caso_cli.py:876-900`), no el cambio del formato antiguo.

**Remedio:** limitar la transformación al formato y plaza cuya convención se conoce, o pedir `--direccion` ante un prefijo dudoso. Probar que el formato antiguo conserva su resultado y que una variante de puntuación documentada se maneja de forma consciente.

### H-04 — Baja; coste trivial. «Caducado» puede describir un token aún vigente

**Dónde:** `head/core/intake_drive.py:559-597`.

**Evidencia reproducible:** con `expiry` dentro de dos minutos y `rclone about` simulado con retorno 1, `obtener_token_drive()` devuelve `token=None` y el motivo «el token estaba caducado y la renovación ... salió con código 1». El margen es cinco minutos (`head/core/intake_drive.py:88-92`). No es regresión de retorno: `base/core/intake_drive.py:500-525` también fuerza el refresco y devuelve `None`; sí es una causa nueva mal nombrada. `test_si_RENOVAR_tarda_lo_dice` solo ensaya un token ya vencido (`head/tests/test_intake_drive.py:1072-1086`).

**Remedio:** decir «caducado o próximo a caducar» en las salidas de renovación, y probar el caso aún vigente dentro del margen.

### H-05 — Baja; coste acotado. La clasificación de remote inexistente depende de un comentario en inglés

**Dónde:** `head/core/intake_drive.py:101-103,525-532`; `head/.claude/skills/organizar-sala-lectura/scripts/precheck_rclone.py:27-29,48-65` y Paso 4 de `head/.claude/skills/organizar-sala-lectura/SKILL.md:367-382`.

**Evidencia reproducible:** los tests simulan exactamente `# couldn't find type of fs ...` y dan respectivamente motivo «no existe» y exit 4. Con una respuesta simulada de código 0 y comentario alternativo `# remote gdrive_tl not found`, `precheck("gdrive_tl:")` da **3** («client compartido») en vez de 4; el lector del token diría «sin bloque token» en vez de «remote inexistente». No afirmo que una versión real de rclone emita ese texto: la dependencia de la cadena y la clasificación incorrecta si cambia son deducciones del código. La ruta de copia sigue siendo secuencial para 3 y 4, así que el riesgo aquí es de diagnóstico. El exit 5 por `TimeoutExpired` y el exit 4 por `FileNotFoundError` sí corresponden a sus causas en los tests.

**Remedio:** comprobar la presencia de una sección válida para el remote solicitado y de `type = drive`, además del comentario conocido; si no se puede distinguir inexistencia de configuración incompleta, usar un motivo/código neutral sin afirmar «client compartido». Añadir test con salida vacía o comentario alternativo.

### H-06 — Media; coste acotado. El diagnóstico legado de §5 sigue exponiendo parte del token

**Dónde:** `head/scripts/diag_drive_autofill.py:55-85,105-119` (anterior a este diff); límite declarado en `head/docs/superpowers/plans/2026-09-26-token-drive-y-carpetas-w-delante-296-301.md:95-103`.

**Evidencia reproducible:** el script usa `timeout=5` para `config show`, afirma que el remote existe al obtener retorno 0, y escribe los primeros 30 caracteres de `access_token` antes y después del refresco. Contradice la precaución de no exponer la salida de rclone que ya aplican el lector y el precheck. No he ejecutado el script ni visto ningún token; la lectura estática basta para esta conclusión. C1 de `verificar_apertura` enumera causas sin elegir una falsa, y las 331 carpetas intermedias sin separador piden el flag deliberadamente; no encuentro en esos dos límites un bloqueo adicional de este diff.

**Remedio:** cambiar ese diagnóstico para consumir `obtener_token_drive` y mostrar solo presencia, caducidad y motivo seguro; retirar ambos prefijos del token. Merece arreglo en la misma limpieza de #296, aunque es un defecto preexistente.

### H-07 — Baja; coste trivial. La prueba de timeout no pone límite superior al coste de un cuelgue

**Dónde:** `head/tests/test_intake_drive.py:1027-1048`; `head/tests/_mutantes_intake_drive_296_301.py:49-53`.

**Evidencia reproducible:** en `scratch/work/core/intake_drive.py` cambié temporalmente `_TIMEOUT_RCLONE_TOKEN = 30` por `3000`. El test `test_el_timeout_de_las_dos_ordenes_es_holgado` siguió verde (`pytest_exit=0`) porque compara las llamadas con la propia constante y solo exige `>=20`. Restauré el fichero de la copia. El mutante T01 prueba bajar a 5, pero no subir sin límite. Con expiración próxima, hay hasta tres órdenes sucesivas (`config show`, `about`, `config show`): a 30 s cada una el peor bloqueo acumulado ronda 90 s; antes los límites eran 5 + 10 + 5 s. Los 30 s dan margen sobre los 6,7 s declarados, pero no hay prueba que limite el coste de un cuelgue.

**Remedio:** fijar en el test un intervalo superior aceptado o el valor decidido en el plan; añadir un mutante que lo exceda. Si la experiencia del alta exige menos de 90 s, imponer un presupuesto total, no solo por orden.

## Lo que intenté refutar y no pude

- `obtener_token_drive` conserva las rutas defensivas de `expiry` ausente o malformado y la renovación; `_get_drive_access_token` devuelve solo token/`None` sin propagar excepciones ordinarias del subproceso. Los motivos inspeccionados no incorporan `stdout`, `stderr`, `access_token` ni `client_secret`. El test de secretos ensaya JSON inválido y la sonda no encontró fuga.
- `leer_carpeta_drive` y `get_drive_folder_info` mantienen cuatro intentos con pausas de 2, 5 y 10 s para los dos `reason` reconocidos, y `None` para token ausente, HTTP no 200, fallo de red o nombre vacío. Las pruebas heredadas lo comprueban. El mensaje del alta en `_autoderivar_drive_ev` y el de 5.1.b reciben el motivo en sus respectivas vías.
- Los nueve stubs modificados de `test_abrir_caso_cli.py` apuntan a `leer_carpeta_drive`; los tres guardas `boom` impiden llamar también a la API antigua. La ejecución de **todo ese fichero** con `socket.connect`, `connect_ex` y `create_connection` bloqueados terminó verde: no observé llamadas de red en esas pruebas.
- El parser sigue reconociendo `"Calle Mayor 5 - W-02UIQU - Ana P"`; rechaza `"W-02UIQU-Calle Mayor 5"` (guion sin espacios) y devuelve dirección vacía para `"W-02UIQU"`, que el alta no usa. La separación con espacios preserva `1-2`. Rechazar el guion pegado es conservador; no hay dato accesible para decir que esa forma deba aceptarse.
- En una copia corrí los cuatro ficheros seleccionados (`test_intake_drive.py`, `test_abrir_caso_cli.py`, `test_precheck_rclone.py`, `test_audit_ev_folder_names.py`) con Python 3.14, `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1` y `--basetemp scratch/pytest-temp` relativo al directorio de trabajo: **exit 0**. El primer intento desde `scratch/work/` con `--basetemp ..\pytest-temp` falló por permisos del sandbox antes de ejecutar tests; repetí desde la raíz del mandato. No extrapolo este resultado a los 1.310 tests que declara el plan.

## SIN VERIFICAR

- Las mediciones de 3,9–6,7 s, el censo de 53 unidades y 231/331 carpetas, las 226 derivaciones declaradas y la corrida del precheck contra rclone real proceden del plan, no de esta revisión. Tampoco comprobé el comportamiento de otras versiones o idiomas de rclone.
- No comprobé la Drive API, el CRM, expedientes reales, el `rclone.conf`, ni que el refresh de `rclone about` reescriba realmente el token. El HTTP 403 y las salidas de rclone de las sondas son dobles controlados.
- No ejecuté el arnés completo de 18 mutantes ni la suite de 1.310 tests. Por lectura, sus mutantes cubren el timeout demasiado corto, la pérdida de motivos, los dos códigos nuevos del precheck, el W-code delante, un consultor final, `1-2`, el rechazo del W-code intermedio y la ciudad; no cubren H-01, H-02, H-03 ni un timeout desmesurado. La afirmación «18/18 muertos» queda SIN VERIFICAR aquí.

NO-SHIP

<!-- informe-literal:fin:k4vd -->

## 2. Evidencia verificada por mí al adjudicar

- **Digest.** Recomputado sobre el `INFORME.md` entregado (UTF-8, LF, un único salto final):
  `fc0c1e8016e1f5cc3cc2272ae60937f177a41892e2aa6608bff0d3a549111241`, **el mismo que declara el revisor en su último mensaje**. El crudo y el canónico
  coinciden.
- **La ronda terminó, y así se supo.** Vigía armado antes de lanzar, con fin y muerte, por
  `powershell -File`. `_exit.txt` con `exit=0` y el `-o` a las 20:45:59; el vigía dijo `TERMINO` a
  las 20:46:14. Ninguna de las cuatro muertes conocidas en el log.
- **Modelo y esfuerzo, releídos:** `gpt-6-sol` · `high` en el `turn_context` de
  `rollout-2026-09-26T20-33-09-01a0defe-1919-7782-84e0-2e490f84dbd3.jsonl` (`originator:
  codex_exec`) y en la cabecera del `_stdout.log`. Binario sondado antes con los tres flags
  (`C:\t\sonda-sol-296-2032`): `VIVO`, sin aviso de tier. La velocidad `default`, **afirmada**
  desde el lanzador (`C:\t\drive-296-301-r1-2032-lanzador\_lanzar.ps1`).
- **El objeto no se tocó, y lo mido yo:** reextraje `aa46fcc` y `e55468c` desde git y comparé
  fichero a fichero con las copias del revisor: **2.889 ficheros, cero diferencias** (1.443 +
  1.446, sus mismas cuentas).
- **Tokens y cupo, para la calibración:** 3.950.778 tokens totales, 3.807.104 en caché; **entrada
  nueva + salida = 143.674**. El contador semanal de la cuenta marcaba **4 %** al empezar
  (18:33:21 UTC) y **5 %** al acabar (18:45:58 UTC) —la ventana se había reiniciado desde la ronda
  anterior, que marcaba 78-79 %—. **Ningún otro rollout de Codex en la ventana**: la ronda de otro
  proyecto acabó a las 18:25:48 UTC y la sonda, a las 18:32:11.
- **Los siete hallazgos, reproducidos contra el código de `e55468c`:**
  - **H-01.** `parse_ev_folder_name("W-02UIQU - Calle Mayor 5 - Portal 2")` da «Calle Mayor 5» y
    `("W-02UIQU - Ana P")` da «Ana P», y `_direccion_de_la_carpeta` los aceptaría.
  - **H-02.** Leído en el código: todo 403 que no fuera de cuota llevaba la pista «sin permiso», y
    el mensaje de cuota agotada decía `rateLimitExceeded` fuera cual fuera la razón.
  - **H-03.** Leído en el código: `_sin_la_ciudad_delante` se aplicaba a los dos órdenes.
  - **H-04.** Leído en el código: las salidas de la renovación decían «caducado» también dentro
    del margen de 5 min.
  - **H-05.** Leído en el código: sin el comentario inglés, un remote inexistente salía 3 en el
    precheck y «sin bloque token» en el lector.
  - **H-06.** Leído en el código: `scripts/diag_drive_autofill.py` imprimía 30 caracteres del
    access_token dos veces.
  - **H-07.** El test del timeout comparaba con la propia constante y solo exigía `>= 20`.
- **Y lo que medí antes de remediar H-01**, en el censo de solo lectura (Drive API, formas, sin
  nombres): de 229 carpetas con el W-code delante y un separador reconocible, **161** son
  «dirección con número - consultor sin número», **57** «dirección con número» y **1** «número -
  número - consultor»: **219** cumplen la convención. Las **10** que no: 3 con un tramo sin número,
  2 con dos tramos sin número, 1 «número - número - número», 1 «sin número - número» y 3 que son el
  W-code solo. Las 2 que faltan hasta las 231 del censo general llevan otro separador tras el
  W-code y tampoco se derivan.
- **Adjudicación:** `docs/superpowers/plans/2026-09-26-token-drive-y-carpetas-w-delante-296-301.md` §7.
