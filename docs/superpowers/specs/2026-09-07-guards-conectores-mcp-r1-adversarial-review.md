---
tipo: revision-adversarial
objeto: "diff 2e2389f..2f68f8c — los guards de los conectores MCP: uno que mira lo desplegado y otro que deja de depender de Drive (MEJORAS #172, #173)"
objeto_rev: "1"
commit: "2f68f8c"
ronda: "1"
revisor: Codex
veredicto: REQUIERE-REVISION
marcador_nonce: q7ka
sha256_informe: 1f0bb2f71b319fb59e09a5cf4d60407597dbe5c0e86d679e5288bfa642fb2569
adjudicado_en: docs/superpowers/plans/2026-09-07-guards-conectores-mcp.md §7
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1 sobre el DIFF.** Ronda única, que es la que le toca por radio
> de daño: la pieza no decide quién escribe sobre qué copia ni puede destruir datos de cliente.
>
> El §1 conserva la voz del revisor **sin una coma cambiada**; el §2 es la evidencia que verifiqué
> yo. **La adjudicación NO está aquí:** va en el §7 del plan.
>
> **Objeto:** copias externas de `2e2389f` y `2f68f8c` con `git archive`, más el parche
> (`sha256 63fd7870…7fee13`). El parche conserva su hash al cerrar — comprobado por mí y declarado
> por el revisor al abrir y al cerrar, que es la prueba de no-mutación que aquí sustituye al
> `git status` (las copias no llevan `.git`).
>
> **Lo que hace a esta ronda distinta de una de lectura:** el revisor **ejecutó**. Montó su propio
> arnés de mutación (`review_harness.py`, `edge_harness.py`), un repositorio Git sintético y una
> instalación falsa, corrió los dos módulos con y sin las fixtures del proyecto, en serie y con
> `-n auto`, y **encontró dos mutantes que mi arnés daba por muertos** más un falso rojo
> reproducible. Ninguno de esos tres sale de leer el diff.
>
> **Cobertura ausente que el propio revisor declaró, y que no se disimula:** la igualdad entre el
> plugin realmente instalado y el `main` real quedó **SIN VERIFICAR** en su entorno (su copia no
> tiene `main` ni `origin/main`, así que el módulo nuevo se le saltó con `skip`). Eso lo cubrí yo
> contra la instalación viva, y consta en el §2 del plan; no lo acredita el revisor.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:q7ka -->
Higiene inicial conforme: el workdir contenía únicamente `MANDATO.md`; no había otros ficheros que pudieran contaminar la ronda.

# Revisión adversarial R1 del diff de guards MCP

Fecha de comprobación: 2026-09-07, reloj del sistema. Revisor: Codex. Objeto: las copias congeladas `../obj/base/`, `../obj/head/` y `../obj/DIFF.patch`. Las referencias de línea siguientes corresponden a `head`.

## Custodia y alcance

- SHA-256 de `DIFF.patch` al abrir: `63fd78708c77002ed9bce4d3f5b773a19b4766638e155513c90c5fb6647fee13`.
- SHA-256 de `DIFF.patch` al cerrar: `63fd78708c77002ed9bce4d3f5b773a19b4766638e155513c90c5fb6647fee13`.
- No se ha escrito ni ejecutado código dentro de `../obj/`. Las copias, repositorios Git sintéticos, instalaciones falsas, logs y mutantes están dentro del workdir. No se ha modificado la instalación real del usuario ni se han montado/desmontado unidades.
- Se leyeron el diff, los dos tests completos, el wrapper completo, el empaquetador, los metadatos y las instrucciones del proyecto. El mandato específico prevaleció sobre los procedimientos generales de implementar, abrir/cerrar sesiones y escribir estado en el repo.
- Python utilizado: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`. Ejecuciones con `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider` y `--basetemp` relativo dentro del workdir.

## Resultado ejecutivo

El cambio mejora la cobertura: las eliminaciones individuales de los overrides G, H y MAXTRIES mueren en esta máquina. Sin embargo, el nuevo guard de despliegue admite un manifiesto MCP vacío y una segunda instalación rota; los guards del wrapper admiten defaults incorrectos y un intento adicional. Hay además un falso rojo reproducible por el nombre del directorio temporal y defectos reales de interpretación del entorno en `cmd`.

Estos resultados impiden considerar cerrado el problema de «lo que se ejecuta coincide con lo revisado». No constituyen una adjudicación: corresponde a Claude contrastar cada hallazgo contra la fuente.

## Ejecución y evidencias

Los arneses conservados son `review_harness.py` y `edge_harness.py`; sus resultados están en `evidence/results.json`, `evidence/*.txt` y `edges/results.json`. Importan las copias de los tests y llaman sus aserciones originales. El arnés de despliegue redirige `ROOT`, `SRC` y `REGISTRO` a un repositorio y un registro sintéticos; usa Git real y conserva los conectores reales copiados, sin sustituir las funciones de comparación.

| Ejecución | Resultado medido | Límite |
|---|---|---|
| Dos módulos en copia mínima, semilla 777 | 29 passed, 3 skipped | Primera corrida sin `conftest.py` del proyecto |
| Dos módulos con `conftest.py`, `_barrera.py`, `core/` y `scripts/` del proyecto, `-n auto`, semilla 31337 | 29 passed, 3 skipped, 25,77 s | Solo estos módulos, no toda la suite |
| Los mismos módulos con fixtures, en serie, semilla 777 | 29 passed, 3 skipped, 3,28 s | Estado original restaurado |
| Solo test del tope, `--basetemp=shipping` | 1 failed, 26 deselected | Falso rojo, sin mutar el wrapper |
| Despliegue sintético íntegro | Pasan las cinco instancias de guards | No equivale a verificar Claude en vivo |

Comando de la última corrida ordinaria:

```powershell
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest lab\tests\test_mcp_wrappers.py lab\tests\test_plugin_desplegado.py -p no:cacheprovider --basetemp=b2 --randomly-seed=777 -ra --tb=short
```

Matriz de mutación del wrapper, corriendo las 27 instancias de `test_mcp_wrappers.py` sobre la copia mínima:

| Mutante | Resultado |
|---|---|
| Eliminar override G | Muerto: 2 failed, 25 passed |
| Eliminar override H | Muerto: 2 failed, 25 passed |
| Eliminar override MAXTRIES | Muerto: 1 failed, 26 passed |
| Defaults a `G:\nonexistent-review-default` y `H:\nonexistent-review-default` | Sobrevive: 27 passed |
| Asignar `MAXTRIES=%FEESDEFENDER_PROBE_MAXTRIES%+1` | Sobrevive: 27 passed |

Al terminar, el SHA-256 del wrapper de `lab` restaurado y el de `head` coinciden: `a7bbe704f296cd2bc1c13b977061fe4407100cfae2b4dc901d611ab0e54f8f0e`.

## Hallazgos

### H-01 — ALTO — El guard omite los metadatos que deciden qué conectores arrancan

**Fichero y línea:** `tests/test_plugin_desplegado.py:212`, `:231` y `:205`.

**Defecto.** La comparación recorre exclusivamente los directorios de `CONECTORES`; no incluye el `.mcp.json` instalado. El test de versión lee el número del registro, no el manifiesto instalado `.claude-plugin/plugin.json`. El empaquetador sí distribuye ambos ficheros y `.mcp.json` contiene los comandos y argumentos de arranque. Son parte del contrato de ejecución de los conectores, aunque las skills se excluyan deliberadamente.

**Entrada → resultado incorrecto, medido ejecutando.** Instalación sintética idéntica al `main` sintético, registro en 0.4.2: sustituir solamente `.mcp.json` por `{}` → siguen pasando las cinco instancias de guards. Repetir sustituyendo únicamente `.claude-plugin/plugin.json` por `{}` → también pasan. Como control, alterar `expedientes_xl/server.py` sí dispara el guard.

**Inferencia de impacto.** El manifiesto vacío ya no declara los MCP; uno rancio podría apuntar a otro wrapper mientras el test certifica copias que nadie ejecuta. No se ha arrancado Claude con estos mutantes: ese efecto en el cliente está **SIN VERIFICAR**. La omisión de ambos ficheros y el verde son mediciones directas.

**Corrección propuesta.** Incluir el manifiesto de arranque y la identidad/versión del manifiesto instalado en la comparación canónica, además del registro. Añadir estos mutantes al guard de regresión.

### H-02 — MEDIO — Solo se audita la primera entrada de instalación

**Fichero y línea:** `tests/test_plugin_desplegado.py:152` (`return entradas[0]`).

**Defecto.** No se recorre la lista ni se determina qué entrada corresponde al ámbito/proyecto auditado. El resultado depende del orden del registro.

**Entrada → resultado incorrecto, medido ejecutando.** Registro con dos entradas: primera `scope=user`, versión 0.4.2 y copia íntegra; segunda `scope=project`, `projectPath` igual al repo sintético, versión 0.4.0 y `installPath` inexistente → pasan las cinco instancias. Invertir únicamente el orden → falla la versión. La segunda instalación rota queda fuera de toda comprobación si no ocupa la primera posición.

**Inferencia de impacto.** Si el cliente selecciona la instalación de proyecto, el verde describe otra copia. La precedencia efectiva del cliente y la presencia de varias entradas en la máquina real están **SIN VERIFICAR**; no son necesarias para demostrar que el código ignora entradas del formato que lee.

**Corrección propuesta.** Definir el ámbito que se quiere auditar y seleccionarlo explícitamente, o auditar todas las instalaciones declaradas, identificando ámbito y ruta en los fallos.

### H-03 — MEDIO — Una `main` local antigua oculta cambios ya presentes en `origin/main`

**Fichero y línea:** `tests/test_plugin_desplegado.py:59`.

**Defecto.** `_rama_canonica()` elige la primera referencia que resuelve, siempre `main`, aunque `origin/main` sea posterior. «Existe una rama local llamada main» no demuestra «es lo que el equipo da por bueno ahora».

**Entrada → resultado incorrecto, medido ejecutando.** Repo sintético con `main=A`, instalación=A, y `origin/main=B`, descendiente de A que modifica `expedientes_xl/server.py` → selecciona `main` y pasan los cinco guards. No se necesitó acceso a red: ambas referencias ya existían localmente.

**Inferencia de impacto.** Tras actualizar referencias remotas sin avanzar la rama local, un despliegue obsoleto sigue verde. Es un caso relevante para otro clon o un worktree, aunque la raíz del desarrollador habitual se mantenga normalmente al día.

**Corrección propuesta.** Fijar la política de referencia y comprobar su frescura/divergencia. No propongo comparar con cambios sin commit: evitar rojos por trabajo a medias es razonable. El problema es identificar un commit canónico vigente y usar ese mismo commit durante toda la comprobación. Sin contacto remoto tampoco se puede demostrar frescura global, y debe declararse ese límite.

### H-04 — MEDIO — El guard de defaults certifica rutas equivocadas

**Fichero y línea:** `tests/test_mcp_wrappers.py:436` y `:442`.

**Defecto.** Reunir las asignaciones y buscar las subcadenas `G:` y `H:` no comprueba ni las rutas requeridas ni su asociación con cada variable. El test se presenta como defensa frente a un default que apunte a otro sitio.

**Entrada → resultado incorrecto, medido ejecutando.** Sustituir las dos rutas originales por `G:\nonexistent-review-default` y `H:\nonexistent-review-default` → pasan los 27 tests, incluido este guard. Los tests de comportamiento inyectan overrides y por ello tampoco detectan los defaults rotos.

**Inferencia de impacto.** Sin overrides, una máquina con los directorios de producción montados pero sin esas carpetas falsas esperaría hasta timeout y no arrancaría. No se han creado ni modificado carpetas G:/H: para ejecutar ese escenario real.

**Corrección propuesta.** Comprobar cada asignación esperada completa, o ejecutar un contrato de defaults con filesystem controlado; conservar este mutante como prueba negativa.

### H-05 — MEDIO — El contador de esperas tiene falso rojo y falso verde

**Fichero y línea:** `tests/test_mcp_wrappers.py:418` y `:419`.

**Defecto.** `stderr.lower().count("ping")` cuenta también rutas y cualquier otro diagnóstico. Además acepta una espera cuando el contrato y el docstring exigen cero con MAXTRIES=1.

**Entradas → resultados incorrectos, medidos ejecutando.**

1. Wrapper intacto, ejecutar el test con `--basetemp=shipping` → falla afirmando «2 intentos». No hubo llamadas a `ping`: el stderr solo tiene TIMEOUT y las dos sondas; cada ruta contiene `shipping`.
2. Mutar la asignación a `MAXTRIES=%FEESDEFENDER_PROBE_MAXTRIES%+1` → 27 passed. El límite solicitado de 1 se convierte en 2, pero una queja sigue cumpliendo `<=1`.

**Impacto.** Reintroduce dependencia ambiental y admite una regresión en la propiedad concreta que pretende comprobar. Ambas direcciones están reproducidas, no inferidas.

**Corrección propuesta.** Instrumentar la espera con un doble local y contar sus invocaciones exactas; exigir cero para límite 1 y comprobar además algún límite mayor. Si se mantienen diagnósticos, identificar mensajes completos y separarlos de las sondas.

### H-06 — MEDIO — Las sondas con `!` se deforman antes de comprobar su existencia

**Fichero y línea:** `plugins/expedientes_xl/run_server.bat:39`, `:40` y `:47`, con delayed expansion activa desde `:24`.

**Defecto.** Expandir `%FEESDEFENDER_PROBE_G%`/`%FEESDEFENDER_PROBE_H%` introduce el valor en una sentencia que después procesa `!`. El mismo patrón vuelve a aparecer al consultar `%PROBE_G%`. Las comillas protegen otros metacaracteres, pero no la expansión retardada.

**Entrada → resultado incorrecto, medido ejecutando en cmd.** Crear `edges/3/bang!dir`, pasar esa ruta como G y un directorio existente como H, con límite 1 → timeout; el diagnóstico muestra `...\bangdir`, que no es la sonda solicitada. Con directorios existentes de nombre simple, `a space (x86)` y `amp&dir`, el mismo runner llega a resolver intérprete.

**Inferencia de impacto.** Una ruta temporal o perfil que contenga `!` puede producir rojo con los overrides correctos. Los defaults actuales no contienen `!`; no atribuyo este fallo a su uso ordinario sin override.

**Corrección propuesta.** Introducir los valores sin volver a someterlos al parser de expansión de `cmd` y mantener ese cuidado también en el `if exist`; cubrir rutas con `!` en el test. No basta corregir solo la asignación.

### H-07 — MEDIO — MAXTRIES evalúa código/expresiones del entorno y no valida un número de intentos

**Fichero y línea:** `plugins/expedientes_xl/run_server.bat:41`.

**Defecto.** La sustitución `%FEESDEFENDER_PROBE_MAXTRIES%` se inserta sin validar en `set /a`. El valor se interpreta tanto por el parser de comandos como por el evaluador aritmético; el wrapper no gestiona su error ni limita el dominio.

**Entradas → resultados incorrectos, medidos ejecutando con una sonda ausente.**

- `abc` → cero esperas y TIMEOUT inmediato: el identificador aritmético no definido equivale a cero.
- `08` → error de número octal y 24 intentos de espera; permanece el default 25.
- `1/0` → error de división por cero y las mismas 24 esperas.
- `-1` → TIMEOUT inmediato.
- `1 & echo REVIEW_MARKER` → escribe `REVIEW_MARKER` en stdout. Solo se ejecutó ese marcador inocuo; demuestra que el valor se convierte en otra orden y rompe la regla de stdout del propio wrapper.

**Inferencia de impacto.** Una variable heredada mal formada puede eliminar o alargar la espera, añadir diagnósticos ajenos al contrato y contaminar el pipe MCP. No afirmo una escalada de privilegios: controlar el entorno del proceso ya requiere acceso correspondiente. El defecto es tratar una configuración numérica como texto ejecutable.

**Corrección propuesta.** Validar un entero decimal positivo y acotado antes de usarlo, definir qué ocurre ante un valor inválido y mantener su texto fuera del parser de órdenes.

### H-08 — BAJO — La prueba diferencial necesita estabilidad del montaje, que su explicación niega necesitar

**Fichero y línea:** `tests/test_mcp_wrappers.py:369`; afirmación relacionada en `docs/MEJORAS_FUTURAS.md:7644` y siguientes.

**Defecto.** Es falsa en general la afirmación de que, al ignorar un override, las corridas necesariamente darían el mismo resultado. Las ejecuciones ocurren en tiempos distintos y consultan un estado externo que puede cambiar. Con un entorno estable sí hay una prueba útil: las dos corridas relevantes para la sonda ignorada no pueden satisfacer simultáneamente abierto/cerrado.

**Entrada → resultado incorrecto, medido en simulación local.** En la copia del wrapper se eliminó el override G y se sustituyó su default por un directorio dentro del workdir que representa el montaje. Antes de las tres ejecuciones, ese directorio se dejó presente, ausente y presente, respectivamente. El test diferencial original pasó. H continuó gobernada por el test. `edge_harness.py` conserva el experimento.

**Límite de la medición.** No se reprodujo un desmontaje/reconexión real de Drive. Se midió que la secuencia de estados puede producir verde con G ignorada; que Drive siga esa secuencia durante las tres corridas es una posibilidad, no un hecho observado ni una estimación de frecuencia.

**Corrección propuesta.** Acotar la afirmación documental a un montaje estable y, para una garantía independiente del montaje real, probar también contra defaults controlados en una copia. No invalida la mejora diferencial ni los mutantes muertos en estado estable.

## Respuesta al mandato, punto por punto

### Experimento diferencial

En esta máquina, borrar individualmente G o H da rojo. El AND deja de permitir el mutante simple de la versión anterior: la mejora es real. La explicación debe corregirse según H-08. No se midieron todas las combinaciones de montajes reales: **SIN VERIFICAR**. Hay falsos rojos ambientales reproducidos por H-05 y H-06, aunque el caso de `shipping` corresponde al guard del tope, no al diferencial.

### Semántica de cmd y producción

Las asignaciones nuevas de sondas están fuera de bloques: no detecté el típico valor obsoleto por expansión `%VAR%` en un bloque. Las líneas diagnósticas dentro del bloque usan `!VAR!`; espacios y paréntesis funcionaron en las pruebas. H-06 documenta el fallo distinto con `!`.

MAXTRIES vacío, aun transmitido como entrada vacía del entorno desde Python, produjo el default de 25: 24 quejas de espera con PATH vaciado. Por lectura, G/H vacías tampoco activan `if defined`, conservando sus defaults; **no se ejecutó una prueba específica con ambas G/H vacías**. H-07 documenta el resto de entradas aritméticas.

Una variable de entorno heredada sí cambia incondicionalmente las sondas, también en producción. Es la interfaz añadida, no un modo de pruebas separado. Apuntar ambas a directorios locales existentes evita comprobar el montaje real; el proceso sigue lanzándose con `--rw G:\ --ro H:\`. No se cambia la raíz servida por esos overrides. El riesgo de dejar una variable persistente requiere documentarse; no se ha observado una variable así en el perfil real.

La última sentencia sigue siendo `"%PYEXE%" -m expedientes_xl.server --rw G:\ --ro H:\`, sin redirecciones y sin otra sentencia ejecutable detrás. Se verificó por lectura y con los guards ordinarios. No se arrancó el servidor MCP real ni se repitió el experimento del pipe con Claude: **SIN VERIFICAR**.

### Skip, registro e installPath

La corrida real de este encargo dio dos instancias verdes del nuevo módulo y tres skips porque la copia no tiene `main` ni `origin/main`. **La igualdad entre el plugin real instalado y el main real está SIN VERIFICAR.** Haber ejecutado el módulo no elimina esa ausencia de cobertura.

Por lectura, registro ausente o clave ausente hacen skip con motivo; esto es honesto para una máquina sin instalación, pero pytest acaba con código 0 sin auditar contenido ni versión. El mensaje no acredita una política que obligue a ejecutar el guard en alguna máquina con plugin. Se verificaron sintéticamente `{}`, `{"plugins": {}}` y la clave con lista vacía: todos se clasifican como ausencia. Un JSON sintácticamente corrupto (`{invalid`) sí levanta `JSONDecodeError`; no se silencia. Falta distinguir esquema mal formado de ausencia legítima: no todo registro parseable prueba que «esta máquina no instala el plugin».

Por lectura, el `installPath` seleccionado que no es directorio falla en `_ruta_instalada()`. Uno que apunta a otra carpeta existente se acepta si esa carpeta satisface las comprobaciones: no se valida que sea un cache bajo `~/.claude/plugins/`. Eso puede ser válido para otros tipos de instalación; no exijo esa restricción sin contrato del cliente. H-02 demuestra la falta de cobertura de las demás entradas. No se midió la selección efectiva de instalación de una sesión de Claude.

### Referencia main frente al árbol de trabajo

Comparar con un commit canónico tiene sentido para un guard operativo de despliegue. Evita exigir el despliegue de una rama a medio hacer. No debe confundirse con validar el contenido nuevo de la PR, y no justifica la selección de una referencia local obsoleta de H-03.

Por lectura, `CONECTORES`, `_IGNORE` y la identidad se importan del árbol de trabajo mientras el contenido y la versión se leen de main. La promesa «contra main» no cubre esos selectores. Con los valores actuales no observé un desfase; cambios futuros en ellos necesitan una decisión explícita. Asimismo, la comparación es unidireccional: exige los ficheros canónicos, pero no rechaza ficheros sobrantes instalados. No se atribuye a esos sobrantes un fallo de ejecución que no se haya reproducido.

### _excluido y _IGNORE

No encontré defecto en `_excluido()` para el `_IGNORE` actual. Comparé su resultado con un `shutil.copytree(..., ignore=_IGNORE)` real: `nested/dxt-build/x.py`, `nested/__pycache__/x.py` y `nested/a.pyc/x.py` quedan excluidos en ambos; `nested/ok.py` queda incluido. Un directorio llamado `a.pyc` también es excluido por el empaquetador: no es un falso positivo de `_excluido`. Los nombres `dxt-build` y `DXT-BUILD` colapsaron en el filesystem Windows de esta prueba y no se cuentan como dos casos independientes.

La equivalencia depende de que el callback actual solo mire nombres mediante patrones y no use el directorio que recibe. Invocarlo con `""` no sería necesariamente equivalente a un callback futuro dependiente del padre. Eso es un límite del razonamiento, no un defecto presente demostrado.

### Aislamiento y paralelo

Los dos helpers del wrapper copian el batch y dirigen APPDATA, LOCALAPPDATA, USERPROFILE y PATH bajo `tmp_path`; los logs observados se escribieron allí. El guard instalado solo lee ficheros y ejecuta Git de lectura. No encontré escrituras explícitas fuera de `tmp_path` en esos tests. No se instrumentó cada syscall de sus procesos: la afirmación se limita al código inspeccionado y las salidas observadas.

Se ejecutaron los dos módulos con las fixtures del proyecto y `-n auto`, semilla 31337: 29 passed, 3 skipped. No hubo choque de directorios entre workers. **La suite completa y una actualización concurrente real del plugin están SIN VERIFICAR.** El guard no toma un snapshot de una instalación durante una actualización, así que esa lectura concurrente no está demostrada como consistente.

### Documentación #172, #173 y #174

- **#172:** la etiqueta «RESUELTO» excede la cobertura obtenida ante H-01/H-02/H-03. El «3/3 muertos» histórico no viene acompañado aquí de su arnés/log y no lo reproduje literalmente; sí maté un contenido alterado y encontré mutantes adicionales supervivientes. Las fechas de instalación, los tamaños históricos, la caída de email-export y las conexiones del cliente son afirmaciones del autor, **SIN VERIFICAR en esta ronda**. Un snapshot de instalación y un diagnóstico actual no demuestran por sí solos cinco semanas de avería continua; esa duración necesita evidencia temporal o debe formularse como inferencia.
- **README, líneas 73–78, y #172:** observar que una actualización con *la misma* versión no copia explica un desfase de contenido dentro de esa versión. No demuestra por sí solo por qué una instalación 0.4.0 no recibió una fuente 0.4.1: ahí las versiones sí diferían. El salto «es justo cómo se quedó en 0.4.0» debe separarse de la medición y tratarse como hipótesis salvo que exista trazabilidad adicional. No se ejecutaron `claude plugin update`, uninstall ni install; su funcionamiento real, el mensaje citado y la ausencia de `--force` están **SIN VERIFICAR**.
- **#173:** se reprodujo que los tres overrides simples son necesarios para los tests actuales, pero no el supuesto arnés histórico «5/5». Los dos supervivientes de esta ronda no desmienten que cinco mutantes distintos murieran entonces; sí desmienten usar ese conteo como garantía general. H-05/H-06 y H-08 acotan la independencia ambiental anunciada.
- **#174:** se comprobó que `plugins/expedientes_xl/dxt-build/manifest.json:4` contiene exactamente el `display_name` con `/` y `:`. El error de Claude Desktop y el barrido histórico de cero coincidencias están **SIN VERIFICAR**. El texto distingue bien la observación de la hipótesis causal, pero «si desaparece, la inferencia era buena» es demasiado concluyente si además se reconstruye/reinstala: desaparecer tras varios cambios apoya la hipótesis, no identifica por sí solo la causa. Sería mejor cambiar únicamente el nombre bajo un procedimiento controlado.

## Cierre

Recomiendo corregir la cobertura de metadatos e instalaciones, la selección de referencia y los fallos reproducidos de la costura/guards antes de declarar resueltos #172 y #173. No hay hallazgo jurídico, operación fiscal, modificación de producción ni despliegue efectuado en esta revisión. Las zonas SIN VERIFICAR permanecen expresamente abiertas.

REQUIERE-REVISION
<!-- informe-literal:fin:q7ka -->

## 2. Evidencia verificada por mí (Claude Code)

Lo que comprobé **contra la fuente y ejecutando**, no contra el informe:

| Qué | Cómo | Resultado |
|---|---|---|
| No-mutación del objeto | `sha256sum` del parche al cerrar | `63fd7870…7fee13`, idéntico al de apertura |
| H-04, default movido sobrevivía | Mutante `PROBE_G`/`PROBE_H` a `…\nonexistent-review-default` | Reproducido: sobrevivía. Tras remediar, **MUERTO** |
| H-05, falso verde del tope | Mutante `set /a MAXTRIES=MT+1` | Reproducido: sobrevivía. Tras remediar, **MUERTO** |
| H-05, falso rojo | `pytest --basetemp=shipping` sobre el fichero intacto | Reproducido: rojo. Tras remediar, **29 verdes** |
| H-06, ruta con `!` | Wrapper real, sonda `…\bang!dir` existente y `…\no!existe` ausente | Antes se consultaba deformada; ahora abre el gate en la existente y conserva el `!` en el diagnóstico de la ausente |
| H-07, el tope se ejecutaba | `FEESDEFENDER_PROBE_MAXTRIES='1 & echo MARCADOR'` contra el wrapper real | Reproducido: escribía en **stdout**. Tras remediar: stdout limpio, aviso por stderr, tope de producción conservado, y lo mismo con `abc`, `08`, `1/0`, `-1` y vacío |
| H-01, metadatos fuera del guard | Instalación viva: `.mcp.json` → `{}` y `plugin.json` → `{}` | Reproducido: pasaba en verde. Tras remediar, **los dos MUERTOS** |
| H-02, solo la primera entrada | Registro con una segunda instalación rota en segundo lugar | Reproducido: pasaba en verde. Tras remediar, **MUERTO** |
| H-03, referencia rancia | `git rev-list --count main..origin/main` en este repo | **2** — la divergencia no era hipotética: la `main` local iba dos commits por detrás |
| Restauración de todo lo mutado | `Get-FileHash` antes y después | Idéntico en los cinco ficheros tocados de la instalación viva |

**Un desacuerdo con el revisor, y es de alcance, no de fondo.** En H-08 dice que la explicación del
experimento diferencial «es falsa en general». Lo es tal como yo la escribí —afirmaba independencia
del montaje sin acotarla—, y por eso la corregí. Pero el experimento sigue probando lo que hace
falta **con el montaje estable**, que es la condición en la que corre la suite; el revisor lo dice
igual. La corrección es de la prosa, no del test.

**Lo que NO verifiqué y por tanto sigue abierto:** que Claude Code elija de verdad la instalación
que el guard audita cuando hay varias entradas, y la frescura de `origin/main` respecto al remoto
sin `fetch`. Las dos están declaradas en la cabecera del propio fichero de tests.
