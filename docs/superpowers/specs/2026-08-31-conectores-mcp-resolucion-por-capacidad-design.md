---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-08-31
---

# Los wrappers de los conectores MCP: resolución por capacidad, y nada detrás del lanzamiento

> **Qué decide este documento.** Cómo eligen los `run_server.bat` del despacho el intérprete
> con el que arrancan un server MCP, y qué no puede haber en la línea que lo lanza. Nació de
> un apagón de ocho días, y su versión definitiva salió de la ronda R1 adversarial, que
> encontró que **el primer arreglo cerraba el ejemplo y no la frontera**.

## 1. Lo que pasó, medido

Del **2026-08-23 al 2026-08-31**, tres de los cuatro conectores del despacho estuvieron
caídos en Claude Code con `CONNECTION_CLOSED`, y los tres de Claude Desktop con ellos. Dos
causas independientes, ninguna visible desde la suite:

1. **`mcp 2.0.0` en el site de usuario.** Un `pip install --user mcp` sin techo lo trajo el
   2026-08-23 (`REQUESTED` en el `dist-info`, o sea instalación manual). La 2.0 **retiró
   `mcp.server.fastmcp`**, que es la API que importan los cuatro servers. Los wrappers
   eligieron ese intérprete —porque su ruta existía— y los servers arrancaron y murieron con
   `ModuleNotFoundError` enterrado en su propio log.
2. **La línea de lanzamiento redirigía stderr.** Los `.bat` terminaban en
   `python server.py 2>>"%LOG%"`, siguiendo una «regla de oro» escrita en ellos mismos:
   «jamás `1>`, **solo** `2>>`». Con esa redirección Claude Code cierra la conexión y el
   server muere en `stdout.flush()` con `OSError 22` **sin haber recibido `initialize`**.
   Claude Desktop lo toleraba, y por eso la regla sobrevivió un año.

**Experimento de control de (2), porque la causalidad importaba:** dos `.bat` idénticos salvo
el `2>>`, registrados los dos con `claude mcp add` y medidos con `claude mcp list`. Sin la
redirección, `✔ Connected`; con ella, `✘ CONNECTION_CLOSED`. Descartados por el mismo método
el tamaño del log, las barras del path y `cmd /c` en sí.

Sobrevivió solo `gmail-multiaccount`, y no por mérito del wrapper: su entrada de config
apunta al `python.exe` del venv del repo y **no pasa por su `.bat`**.

## 2. El primer arreglo, y por qué no valía

La primera versión (commit `0bb56db`) hizo lo obvio y lo hizo mal: **prohibió el PATH**.
Sustituyó la cadena de candidatos por una lista cerrada de venvs y quitó el fallback.

La R1 lo tumbó con un caso que estaba escrito en el propio repo: `plugin-src/README.md`
anuncia `expedientes-xl` como **auto-contenido**, con prerrequisitos «Python 3 +
`pip install mcp`», sin clonar FeesDefender. Desde el bundle del plugin,
`%~dp0..\..\.venv` resuelve a `dist/plugin/.venv`, que el empaquetador no crea. Resultado:
un compañero que siguiera la documentación se quedaba **sin ningún candidato** y el wrapper
salía por `exit /b 1`.

Es la cuarta aparición del mismo modo de fallo propio: **remediar el caso del informe en vez
de la propiedad de la que es ejemplo.** La propiedad no era «el PATH es peligroso». Era:

> **No lanzar un intérprete cuya capacidad no se ha comprobado.**

Un intérprete del PATH que importa `mcp.server.fastmcp` sirve. Un venv cableado que no lo
importa, no. La ruta nunca fue la pregunta.

## 3. El contrato que rige ahora los cuatro wrappers

**C1 — El intérprete se elige probando, no mirando.** Se recorren candidatos en orden
—`FEESDEFENDER_PYTHON`, el venv del árbol (`%~dp0..\..\.venv`), el venv en la ubicación
convencional (`%USERPROFILE%\Dev\FeesDefender\.venv`), `%LOCALAPPDATA%\Python\bin`, y el
PATH— y se toma **el primero que demuestra** poder importar la API que el server usa. El
stub de la Microsoft Store cae por sí solo al no pasar la prueba: **no hace falta nombrarlo**,
y nombrarlo era justo el error, porque el intérprete de agosto no era el stub.

**C2 — Si ninguno pasa, se falla ruidosamente.** Código de salida ≠ 0, mensaje en **stderr**
(nunca en stdout, que es el pipe JSON-RPC) y **la palanca accionable por su nombre**
(`FEESDEFENDER_PYTHON` o `FEESDEFENDER_ROOT`). Morir en silencio fue la mitad del coste de
agosto: los tres conectores llevaban ocho días caídos y el diagnóstico estaba en un log que
nadie miraba.

**C3 — La sonda prueba lo que el server hace, no un proxy.** Para tres wrappers eso es
`import mcp.server.fastmcp`. Para `email-export`, que **no es auto-contenido** y necesita
`core/`, la sonda importa `mcp.server.fastmcp` **y** `core.email_export` con la raíz elegida.
Eso cierra de paso el desacoplamiento silencioso que permitía la pareja incoherente «python
del repo A, `--repo-root` del repo B».

**C4 — Nada redirige en la línea de lanzamiento, y nada ejecutable va detrás.** Ni `1>` ni
`2>>` ni tuberías. Las líneas **anteriores** sí pueden escribir al log del wrapper: en cmd la
redirección pertenece al comando, no a la sesión — comprobado con un probe de dos comandos,
y confirmado por el revisor. Y detrás del lanzamiento no va nada ejecutable: no por estética,
sino porque un `exit /b 0` detrás basta para que un guard mire otra línea y certifique un
lanzamiento sucio.

**C5 — `email-export` recibe la raíz explícitamente.** Su detección automática
(`Path(__file__).parents[1]`) apunta **dentro** del bundle, donde no hay `core/`. El wrapper
resuelve la raíz por marcador (`core\__init__.py`) y la pasa con `--repo-root`.

**C6 — Quien declare `mcp` lo declara con techo.** `<2`, y comprobado **evaluando** el
especificador: `mcp>=1,<20` contiene la subcadena `<2` y admite la 2.0. Aplica a
`requirements-dev.txt` tanto como a los de los conectores — es el fichero que puebla el venv
que los wrappers **prefieren**, y dejarlo abierto reinstala la avería.

## 4. Lo que NO cubre este contrato

Las **extensiones `.dxt` de Claude Desktop** siguen cableando un intérprete absoluto y no
pasan por wrapper. Es la vía por la que cayeron los tres conectores de Desktop en agosto.
No se arregla aquí porque el `.dxt` empaqueta una copia y el arreglo exige **reconstruir y
reinstalar a mano** las tres extensiones: queda en `docs/MEJORAS_FUTURAS.md` **#125** con
disparador, sostenida entre tanto por C6.

## 5. Adjudicación de la revisión adversarial (Codex, 2026-08-31) — NO-SHIP, remediado

- **Objeto revisado:** diff `d585daf..0bb56db` de la rama `claude/mcps-revision-bb6cf5`, commit `0bb56db`
- **Ronda:** 1 (única; el radio de daño de la pieza no llega a las dos del presupuesto)
- **Revisor:** Codex (`gpt-5.6-sol`, solo lectura sobre copia externa vía `git archive`)
- **Informe recibido:** `2026-08-31-conectores-mcp-r1-adversarial-review.md`
- **Hallazgos:** 9 — 4 ALTOS, 4 MEDIOS, 1 BAJO; veredicto `NO-SHIP`. Adjudicados: **9 confirmados, 0 refutados**
- **Remediado en:** este documento §3, los cuatro `run_server.bat`, `requirements-dev.txt`, `tests/test_mcp_wrappers.py`, `plugin-src/README.md`, `plugins/{expedientes_xl,google_despacho_mcp}/README.md`, `docs/DESPLIEGUE_MCP_DRIVE_DISCO.md`, `docs/DEAD_ENDS.md` y `docs/MEJORAS_FUTURAS.md` #125

**La ronda ejecutó**, y eso decide su valor: el revisor calculó resoluciones de ruta reales,
corrió los dos módulos de test sobre una copia (20/20), ejecutó **probes de `cmd.exe`** y
cargó mi propio helper con `runpy` para pasarle contraejemplos. Los tres hallazgos que más
duelen salieron de ejecutar, no de leer.

**Nada de lo que no pudo correr se dio por refutado.** No tenía el cliente de Claude Code, así
que la causalidad de §1(2) —`CONNECTION_CLOSED`, `OSError 22`, el A/B con y sin `2>>`— quedó
declarada **SIN VERIFICAR** por él, no rebatida. La sostiene la medición del autor con
`claude mcp add`/`claude mcp list`, que es reproducible y está descrita arriba. Igual con el
histórico del 23 al 31 de agosto y con el contenido de la 2.0.

| ID | Sev. | Qué dijo | Adjudicación |
|---|---|---|---|
| H1 | ALTO | El wrapper de `expedientes-xl` no encuentra intérprete en el bundle, contra los prerrequisitos que su propio README publica | **CONFIRMADO.** Es el hallazgo que reescribió el diseño: §2. Verificado por resolución de rutas (`%~dp0..\..` desde el bundle = `dist/plugin/`) y contra `plugin-src/README.md`. Remediado devolviendo el PATH como candidato **probado** (C1). Su caso hermano —checkout con `core/` pero sin `.venv`— también queda cubierto, y comprobado por resultado: los cuatro wrappers arrancan desde este worktree, que no tiene venv propio |
| H2 | ALTO | `requirements-dev.txt` sigue en `mcp>=1.28`, sin techo, y es el fichero que puebla el venv que los wrappers prefieren | **CONFIRMADO.** `packaging` confirma que esa spec admite 2.0.0, y el glob del guard solo miraba `plugins/*/requirements.txt`. Remediado: pin `<2` ahí y corpus del guard ampliado a `requirements*.txt` de la raíz (C6) |
| H3 | ALTO | Las tres superficies `.dxt` siguen lanzando por ruta absoluta, sin wrapper ni prueba de capacidad | **CONFIRMADO**, y ya detectado por el autor antes del informe. **Diferido con motivo, no descartado:** el `.dxt` empaqueta una copia y el arreglo exige reconstruir y reinstalar tres extensiones a mano. §4 y `MEJORAS_FUTURAS.md` #125, sostenido entre tanto por C6 |
| H4 | MEDIO | `%PYEXE%` sin comillas dentro de un bloque `( )` rompe el parser de cmd con rutas como `C:\Program Files (x86)\...` | **CONFIRMADO** con el probe del revisor. Remediado en los cuatro wrappers con `setlocal enabledelayedexpansion` y `!VAR!` dentro de los bloques, que expande en ejecución y no al parsear |
| H5 | MEDIO | `FEESDEFENDER_PYTHON` desacopla el Python de la raíz elegida en `email-export`: puede cargar `core/` del repo A con el entorno del B | **CONFIRMADO** por construcción. Remediado por la vía fuerte en vez de documentándolo: la sonda de `email-export` importa **`core.email_export` con la raíz elegida** (C3), así que una pareja incoherente ya no pasa la prueba |
| H6 | MEDIO | El guard de la línea de lanzamiento da verdes falsos y un rojo falso | **CONFIRMADO**, y reproducido por el autor contra el helper: un `exit /b 0` o un `:: fin` detrás del lanzamiento dejaban el guard verde sobre un `2>>` real. Guard reescrito: parsea sentencias (une continuaciones `^`, descarta `REM`/`@REM`/`::`), exige que el lanzamiento sea la **última** sentencia y busca el operador de redirección, no el carácter `>` |
| H7 | MEDIO | Los guards comprueban subcadenas, no propiedades: un `REM` satisface el de capacidad, `mcp>=1,<20` el del pin, y el del fallback ciego se esquiva con `set PYEXE=python.exe` | **CONFIRMADO** en las tres patas. Remediado: la sonda se exige en una sentencia **ejecutable**; el pin se **evalúa** con `packaging`; y el guard textual del fallback **se retira** —porque con C1 el PATH ya es legítimo— sustituido por un guard de **comportamiento** que ejecuta el wrapper con el entorno envenenado y exige salida ≠ 0, stdout vacío y palanca nombrada |
| H8 | ALTO | La documentación operativa vigente reinstala las vías que el diff cierra: `command: "python"`, `claude mcp add -- python …`, y un `DESPLIEGUE` que describe un wrapper que ya no existe | **CONFIRMADO** por lectura directa. Es el hallazgo más fácil de subestimar: un README que manda `python` pelado deshace el arreglo con la mejor intención. Remediado en los cuatro documentos, con la razón embebida en cada uno |
| H9 | BAJO | La entrada de `DEAD_ENDS` atribuye a PATH tres wrappers, y `google-despacho` estaba cableado a una ruta absoluta | **CONFIRMADO.** Mi frase era falsa. Reescrita distinguiendo los dos mecanismos y nombrando la clase que sí los une: elegir por ruta sin comprobar capacidad |

**Lo que el revisor atacó y no cayó**, porque también es información: la resolución en el
árbol del repo es correcta para los tres wrappers; el anidamiento `if defined` / `if exist` y
las comillas de las invocaciones son válidos; el `expedientes_mcp` jubilado conserva su `2>>`
pero **ninguna config viva lo lanza** (verificado por él contra `.claude.json`,
`claude_desktop_config.json` y `extensions-installations.json`); la sonda redirigida **no**
contamina el pipe del lanzamiento posterior; y el test reescrito que sustituyó a
`test_wrapper_bat_evita_stub_windowsapps` no pierde cobertura real.

**Su matiz sobre ese último punto era justo y lo acepté:** dijo que el test nuevo «no es más
débil en intención, pero tampoco demuestra la subsunción que proclama». Cierto de la versión
que revisó. Lo que la demuestra ahora es el guard de comportamiento, que no depende de que el
`.bat` contenga ninguna cadena.

**Verificación después de remediar:** 7 mutantes contra los guards nuevos, **7 muertos**, más
un control negativo que comprueba que no aparecen rojos falsos; los cuatro wrappers
respondiendo `initialize` por handshake real; y `claude mcp list` con los cuatro conectores
`Connected`.
