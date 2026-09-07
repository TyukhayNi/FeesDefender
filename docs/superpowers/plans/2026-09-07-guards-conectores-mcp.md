---
titulo: "Los guards de los conectores MCP: mirar lo desplegado, y dejar de depender de Drive"
fecha: 2026-09-07
estado: implementado
rev: "2"
relacionado: "MEJORAS #172, #173, #174"
---

# Los guards de los conectores MCP: mirar lo desplegado, y dejar de depender de Drive

> **Este plan no existía cuando el trabajo empezó**, y decirlo es parte de él. Salió de un
> diagnóstico —«mira el guard rojo y los dos conectores caídos»— que destapó tres defectos, y se
> escribe *después* para sostener la adjudicación de la ronda adversarial, que es la función que
> el §5 del contrato de gobernanza le asigna. Una adjudicación que vive solo en un mensaje de
> commit no está donde el contrato la busca.
>
> **Rev. 2 (2026-09-07): R1 adversarial de Codex adjudicada en el §7** — `REQUIERE-REVISION`,
> 8 hallazgos, **8 confirmados y 0 refutados**. Tres eran errores de manual míos y dos eran
> mutantes que mi propio arnés daba por muertos. El acta, con el informe literal, en
> `docs/superpowers/specs/2026-09-07-guards-conectores-mcp-r1-adversarial-review.md`.
>
> **Presupuesto de rondas: UNA.** Por radio de daño (`CLAUDE.md`): esta pieza no decide quién
> puede escribir sobre qué copia ni puede destruir datos de cliente — son dos guards de test y
> una costura de diagnóstico en un `.bat`. Una ronda sobre el diff.

## 1. De dónde sale

El 2026-09-07, en el checklist de apertura, la suite traía **un rojo** y dos conectores MCP no
arrancaban: `email-export` con `CONNECTION_CLOSED` y `expedientes-xl` con `CONNECT_TIMEOUT`.
Parecían el mismo problema. Eran tres, y ninguno era el que parecía.

**El desfase de despliegue.** `feesdefender@despacho-tyukhay` llevaba instalado en **0.4.0 desde
el 2026-07-20**. La reparación de los conectores del 2026-08-31 (PR #253) estaba en `dist/plugin`
como 0.4.1 y **nunca se instaló**: Claude Code arrancaba los wrappers de junio y julio —el de
`email-export` eran 136 bytes contra los 4.178 de la fuente— con la suite en verde. Lo acreditado
es el `lastUpdated 2026-07-20` del registro y el fallo de hoy; que la avería fuera **continua**
entre las dos fechas es inferencia, y la R1 hizo bien en señalar que la escribí como medición.

**El gate de montaje.** `expedientes-xl` no arrancaba porque G:/H: no estaban montados: su
wrapper espera hasta ~50 s y el cliente lo mata a los 30, sin dejar rastro en su log. Al montarlos,
conectó — verificado por resultado, no por que apareciera en la lista de tools.

**El rojo de la suite.** No era ninguno de los dos. Era que el guard de comportamiento de
`tests/test_mcp_wrappers.py` **cambia de veredicto según si Drive está montado**.

## 2. Las tres decisiones de diseño

### 2.1 El guard nuevo compara contra un commit canónico, no contra el árbol de trabajo

La propiedad que importa es **«lo que corre es lo que el equipo da por bueno»**, y lo que uno
tiene a medias en su rama no es eso. Comparar contra el árbol pondría rojo cualquier rama que
toque un conector, desde el primer minuto y hasta el despliegue: un rojo que no significa nada.
Y un rojo que no significa nada acaba ignorado — el mismo razonamiento con el que `MEJORAS #171`
describe cómo muere una verja.

Al mergear, en cambio, el guard **sí** se pone rojo hasta que se despliega de verdad. Esa es
exactamente la presión que faltaba.

**Cuál commit, que la R1 (H-03) obligó a precisar:** «existe una rama local llamada `main`» no
demuestra «es lo que el equipo da por bueno ahora». Manda `origin/main`, y se resuelve a un
**SHA una sola vez** que reutiliza toda la corrida, para que la referencia no se mueva a mitad.
No era hipotético: al medirlo en este repo, `main..origin/main` daba **2**.

### 2.2 La frontera del guard nuevo se declara, no se deja implícita

Cubre los **conectores**, que son lo que se rompió y lo que falla en silencio. **No** cubre las
skills del bundle: tienen otra vía de despliegue —el `.skill` que se importa a mano en Cowork— y
hay varias pendientes de reimportar a sabiendas, así que exigirlas daría un rojo permanente sobre
un estado aceptado.

Y donde el plugin no está instalado el guard hace `skip` **con el motivo escrito entero**. Un
`skip` mudo aquí reproduciría el silencio que el guard viene a romper: «no lo sé» no es «no hay».

### 2.3 El gate de montaje gana una costura, y NO se amplía la lista blanca

El arreglo fácil de `#173` era añadir el mensaje del gate a la lista de palancas aceptadas. **Eso
es cerrar el ejemplo por tercera vez**: la primera versión del guard exigía UNA palanca
(`FEESDEFENDER_PYTHON`) y se amplió a DOS cuando `email-export` la puso roja por morir antes,
resolviendo la raíz del repo. Una tercera cadena sería la misma operación otra vez.

La frontera es que **el test controle toda precondición capaz de desviar al wrapper de la
propiedad que mide**. De ahí `FEESDEFENDER_PROBE_G`, `_H` y `_MAXTRIES`, con los valores de
producción como default y un guard que verifica que el default no se ha movido.

## 3. Lo medido

| Qué | Medición |
|---|---|
| Dependencia del guard respecto a Drive | Con G:/H: caídos, `test_mcp_wrappers.py` da **1 rojo**; con los drives montados, **23/23 verdes**. Mismo día, sin tocar una línea |
| Distancia entre las tres copias | `run_server.bat` de `email_export_mcp`: fuente 4.178 B · `dist` 4.100 B · **instalado 136 B** (23-06). El de `expedientes_xl`: 5.047 · 4.950 · **2.634** (19-07) |
| `dist` vs fuente | Idénticos salvo fin de línea (el empaquetador escribe LF, git deja CRLF) |
| El LF no rompe el `.bat` | La copia de `dist` pasa el gate, resuelve intérprete y muere con `exit 1` nombrando la palanca. Los `goto` funcionan con LF |
| El intérprete cableado del wrapper viejo | Existe y tiene `mcp 1.29.1` — el pin `<2` aguanta. **La avería de agosto por mcp 2.0 NO es la causa de la caída de hoy** |
| Causa medida de `CONNECTION_CLOSED` en email-export | El wrapper de junio lanza `%~dp0server.py` sin `--repo-root` y **el bundle no lleva `core/`**: muere importando `core.email_export` antes de contestar `initialize` |
| La regla del `2>>` **no se reprodujo** | `expedientes_xl` 0.4.0 lleva `2>>"%LOG%"` en su línea de lanzamiento y **conectó y sirvió tools** en Claude Code 2.1.231. No refuta el experimento del 2026-08-31, pero **no explica lo de hoy**, y atribuírselo sería atribuir sin medir |
| `claude plugin update` compara por VERSIÓN, no por contenido | Con la versión igual responde «already at the latest version» y **no copia nada**. No hay `--force`. **Explica el desfase DENTRO de una versión** (el `tiers.py`), y NO el salto 0.4.0 → 0.4.1, donde las versiones sí diferían: ese otro no tiene causa medida. Atribuírselo fue un error mío que levantó la R1 |
| Segundo desfase, encontrado por el guard nuevo en su primera corrida | `tiers.py` desplegado sin `_apertura_v1.json` ni los temporales de escritura atómica en `PROTOCOL_EDIT` (`#149`, `#146`) |

## 4. El arnés de mutación, que es quien corrigió el diseño

**La primera versión del guard del gate SOBREVIVÍA a borrar el override de `PROBE_G`.** Apuntaba
las dos sondas a la vez a rutas inexistentes y exigía morir en el gate; como el gate es un AND,
bastaba con que `PROBE_H` siguiera vivo. El test exigía «al menos un override», no «los dos» —
cerraba el ejemplo, no la frontera, en el mismo diff cuyo objeto era dejar de hacer eso.

Rehecho como **experimento diferencial**: tres corridas idénticas salvo una sonda. Ninguna corrida
suelta prueba nada, porque el gate lee el sistema de ficheros y en una máquina con los drives
montados un override ignorado se ve igual que uno respetado. Es la forma del experimento del
2026-08-31 con el `2>>`.

**Con el montaje ESTABLE durante las tres corridas**, y esa acotación la puso la R1 (H-08): yo
había escrito que la diferencia es independiente de la máquina a secas, y no lo es —las tres
corridas ocurren en instantes distintos, y un montaje que apareciera y desapareciera entre ellas
podría dar verde con una sonda ignorada—. La garantía que no depende de ningún montaje es el
guard de los defaults, que no ejecuta nada; por eso H-04 importaba tanto.

Resultado del arnés **después de remediar la R1** (en negrita, los que ella dejó vivos):

| Mutante del wrapper (9) | | Mutante del despliegue (7) | |
|---|---|---|---|
| Sin override de `PROBE_G` | MUERTO | Fichero instalado alterado | MUERTO |
| Sin override de `PROBE_H` | MUERTO | Fichero instalado ausente | MUERTO |
| Sin override de `MAXTRIES` | MUERTO | Fichero instalado **sobrante** | MUERTO |
| Default de `PROBE_G` movido | MUERTO | Versión del registro movida | MUERTO |
| Gate suprimido entero | MUERTO | **`.mcp.json` vaciado (R1 H-01)** | MUERTO |
| **Defaults a `nonexistent` (R1 H-04)** | MUERTO | **`plugin.json` vaciado (R1 H-01)** | MUERTO |
| **Tope `+1` (R1 H-05)** | MUERTO | **2ª instalación rota, 2º lugar (R1 H-02)** | MUERTO |
| Vuelta a `%VAR%` en la sonda (H-06) | MUERTO | | |
| Sin validación del tope (H-07) | MUERTO | | |

Restauración verificada por hash en los siete del despliegue, que tocan la instalación viva. Y el
falso rojo que la R1 reprodujo —`pytest --basetemp=shipping`— ya no ocurre: 29 verdes.

## 5. Lo construido

- `plugins/expedientes_xl/run_server.bat` — costura del gate (`FEESDEFENDER_PROBE_G`/`_H`/
  `_MAXTRIES`), defaults de producción intactos, y las sondas al diagnóstico de stderr.
- `tests/test_mcp_wrappers.py` — el guard de comportamiento fija el gate abierto; tres guards
  nuevos: el diferencial por sonda, el tope de intentos y el default de producción.
- `tests/test_plugin_desplegado.py` — nuevo: lo instalado contra `main`, por versión y fichero
  a fichero.
- `plugin-src/.claude-plugin/plugin.json` — 0.4.1 → 0.4.2.
- `plugin-src/README.md` — el procedimiento de redespliegue, con el hallazgo del versionado.
- `docs/MEJORAS_FUTURAS.md` — #172 y #173 resueltas; **#174 abierta** (el `display_name` del
  `.dxt` con `/` y `:`).

**Tests:** con las **dos semillas** (777 y 31337). El conteo del cierre, en la bitácora.

## 6. Lo que este trabajo NO cierra, y por qué

- **`MEJORAS #174`** — el `display_name` del `.dxt`. El cambio de fuente son diez segundos; lo que
  arregla el problema es reconstruir el `.dxt` y **reinstalarlo a mano en Desktop**, que es acción
  de Nikolai y arrastra `MEJORAS #125`. `DEAD_ENDS` dice que dejar el fuente «arreglado» sin
  desplegar es justo la trampa, así que no se toca a medias.
- **La conexión de `email-export`** queda **sin verificar**. El artefacto desplegado ya es el
  correcto —comprobado fichero a fichero—, pero `plugin update` avisa de que hace falta reiniciar,
  y esta sesión corre con el binario viejo cargado. La verificación por resultado
  (`[LocalMcpServerManager] Connected to email-export (N tools)` en `main.log`, o una tool suya
  respondiendo) es de la próxima sesión.
- **La regla de oro del `2>>`** queda marcada para **volver a medir**. Hoy no se reprodujo; eso no
  la refuta, pero impide apoyarse en ella como explicación.

## 7. Adjudicación de la revisión adversarial (Codex, 2026-09-07) — REQUIERE-REVISION, remediado

- **Objeto revisado:** diff `2e2389f..2f68f8c`, copias externas con `git archive` (parche `sha256 63fd7870…7fee13`, intacto al cerrar)
- **Ronda:** 1 de 1 — la que le toca por radio de daño; no decide quién escribe sobre qué copia ni puede destruir datos de cliente
- **Revisor:** Codex (`codex-cli 0.153.0-alpha.5`), solo lectura sobre el objeto, con ejecución en su propio workdir
- **Informe recibido:** `docs/superpowers/specs/2026-09-07-guards-conectores-mcp-r1-adversarial-review.md` (`sha256 1f0bb2f7…fb2569`, coincidente con el que declaró el revisor)
- **Hallazgos:** 8 — **8 confirmados, 0 refutados, 0 rebajados**
- **Remediado en:** esta misma rama, sobre `2f68f8c`

**Ninguno refutado, y tres de los ocho eran errores de manual míos.** Contrasté cada hallazgo
contra la fuente y reproduje todos los que traían un procedimiento. La ronda se pagó sola: el
revisor **ejecutó** —montó su arnés de mutación, un repositorio Git sintético y una instalación
falsa— y encontró **dos mutantes que mi propio arnés daba por muertos**, más un falso rojo
reproducible. Ninguna de las tres cosas sale de leer el diff.

| # | Sev. | Qué | Adjudicación | Remedio |
|---|---|---|---|---|
| H-01 | ALTO | El guard omitía `.mcp.json` y el `plugin.json` instalado | **CONFIRMADO** — reproducido: vaciarlos a `{}` pasaba en verde, con el manifiesto ya sin declarar ningún MCP | Guard nuevo de metadatos de arranque + versión comprobada en **tres** sitios (registro, manifiesto instalado, canónico) |
| H-02 | MEDIO | Solo se auditaba `entradas[0]` del registro | **CONFIRMADO** — literal en el código; reproducido con una segunda instalación rota en segundo lugar | `_instalaciones()` devuelve **todas**; cada guard recorre todas, con ámbito y ruta en el mensaje |
| H-03 | MEDIO | Una `main` local rancia oculta lo que ya está en `origin/main` | **CONFIRMADO — y no era hipotético aquí:** `main..origin/main` daba **2** en este mismo repo | Política explícita (`origin/main` manda) y resolución a **un SHA** cacheado, reusado por toda la corrida |
| H-04 | MEDIO | El guard de defaults solo miraba las subcadenas `G:` y `H:` | **CONFIRMADO** — mutante a `G:\nonexistent` sobrevivía. Es el guard cuyo objeto era «el default no se ha movido» mirando solo la letra de unidad | Comparación con el diccionario `_DEFAULTS_PRODUCCION` **entero**, por variable |
| H-05 | MEDIO | El contador de esperas tenía falso rojo y falso verde | **CONFIRMADO en las dos direcciones** — `--basetemp=shipping` daba rojo (las rutas del diagnóstico que yo añadí en este mismo diff contienen «ping»), y `<=1` dejaba vivo el mutante `tope+1` | Token **entrecomillado** (`"ping"`/`'ping'`) e igualdad **exacta** contra **dos** topes distintos |
| H-06 | MEDIO | Las sondas con `!` se deformaban por la expansión retardada | **CONFIRMADO** — reproducido con `…\bang!dir` | `!VAR!` en la lectura del entorno **y** en el `if exist`; test de regresión en las dos direcciones |
| H-07 | MEDIO | `set /a` metía el entorno en el parser de órdenes | **CONFIRMADO, y es el más serio** — `1 & echo X` escribía en **stdout**, o sea la regla de oro de la cabecera del propio wrapper rota por su costura de pruebas | Validación previa: entero decimal de 1 a 3 cifras sin cero a la izquierda; si no, tope de producción y aviso por stderr |
| H-08 | BAJO | La explicación del diferencial afirmaba independencia del montaje | **CONFIRMADO en cuanto a la prosa, no al test** — el experimento sigue valiendo con montaje estable, que es su condición de uso; lo que sobraba era mi afirmación general | Docstring y `MEJORAS #173` acotados; se nombra el guard de defaults como la garantía que no depende de ningún montaje |

**El desacuerdo, que es de alcance y lo declaro como tal.** En H-08 el revisor dice que la
explicación «es falsa en general». Lo es tal como yo la escribí. Pero el hallazgo no toca el test:
con el montaje estable —la condición en la que corre la suite— el diferencial sigue siendo
concluyente, y el propio revisor lo dice («con un entorno estable sí hay una prueba útil»). Por eso
figura como confirmado con remedio **documental**, no de código.

**Tres correcciones documentales más, que el revisor levantó fuera de los hallazgos numerados y que
son las que más me interesan:**

1. **Un error causal mío.** Escribí que el versionado de `plugin update` explica el desfase
   0.4.0 → 0.4.1. No lo explica: ahí las versiones **sí** diferían y `update` habría copiado.
   Explica un desfase *dentro* de una misma versión — el `tiers.py` del 2026-09-07. Confundí dos
   averías distintas y le atribuí a una la causa de la otra. Corregido en `plugin-src/README.md` y
   en `MEJORAS #172`.
2. **«Cinco semanas de avería continua» no está medido.** Lo acreditado es el `lastUpdated
   2026-07-20` del registro y el fallo de hoy; la continuidad entre ambos es inferencia. Reescrito
   como tal.
3. **`MEJORAS #174` era demasiado concluyente:** «si el aviso desaparece, la inferencia era buena»
   no vale si a la vez se renombra, se reconstruye y se reinstala. Reescrito para exigir que se
   cambie **solo** el nombre.

**Arnés después de remediar** — los dos supervivientes de la R1 incluidos:

| Wrapper (9) | Despliegue (7) |
|---|---|
| sin override `PROBE_G` · sin override `PROBE_H` · sin override `MAXTRIES` · default movido · gate suprimido · **defaults a `nonexistent` (R1 H-04)** · **tope `+1` (R1 H-05)** · vuelta a `%VAR%` (H-06) · sin validación del tope (H-07) | fichero alterado · ausente · **sobrante** · versión del registro · **`.mcp.json` vaciado (R1 H-01)** · **`plugin.json` vaciado (R1 H-01)** · **2ª instalación rota en 2º lugar (R1 H-02)** |
| **9/9 muertos** | **7/7 muertos**, restauración verificada por hash |

**Cobertura que sigue AUSENTE, declarada y no disimulada.** El revisor no pudo comparar el plugin
realmente instalado contra el `main` real: su copia no lleva `.git`, así que el módulo nuevo se le
saltó con `skip` y él lo dijo. Esa parte la cubrí yo contra la instalación viva, y la evidencia
está en el §2 del acta — pero **la acredito yo, no el revisor**. Y quedan dos cosas que no puede
comprobar nadie desde aquí: que Claude Code elija de verdad la instalación que el guard audita
cuando hay varias, y la frescura de `origin/main` sin `fetch`. Las dos constan en la cabecera del
propio fichero de tests.
