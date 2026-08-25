---
tipo: revision-adversarial
objeto: "diff 533be06..4aac8b0 (Tasks 10-11 de la Fase 1 dual)"
objeto_rev: "1"
commit: 4aac8b0
ronda: "8"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: q7mz
sha256_informe: 401095e5e42f4a69444fa072aec79b25a5e831eff5478b0e14e3317e0a229f24
adjudicado_en: docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md §14
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R8.** El §1 conserva literalmente la voz del revisor. La
> adjudicación vive en el **§14 del plan**, no aquí. El acta existe porque yo soy la parte
> revisada: sin el original archivado nadie puede contrastar **qué dijo el revisor** con **qué
> decidí yo que dijo**.
>
> **Qué se revisó, y en qué se diferencia de R7.** R7 atacó el **plan** de la Fase 1 antes de
> ejecutarlo. R8 ataca el **diff** de los Tasks 10-11, o sea código y no prosa — que es donde R6
> demostró morder de verdad. Objeto entregado como dos copias externas (`git archive` de
> `533be06` y de `4aac8b0`, sin `.git`) más el diff precalculado, de solo lectura por
> construcción.
>
> **Lo que encontró, en una frase.** Que el arnés que existe para impedir que un test pase por
> vacío **pasaba por vacío en dos sitios**: las filas bloqueadas admitían cualquier código de
> salida distinto de cero, y la fila del fallo externo no miraba ni el canon ni el estado local
> ni los códigos de las dos invocaciones. Nueve hallazgos, **nueve confirmados**.
>
> **Limitación declarada por el propio revisor, y que no se maquilla:** la copia externa no trae
> `.venv`, así que `pytest` no arrancó (`ModuleNotFoundError: typer` / `dotenv`). Todo lo que
> dependía de correr la suite —los 3.358 tests, las dos semillas, los 7 `xfailed`, el
> `leak-scan`— queda **SIN VERIFICAR por el revisor** y lo aporta el adjudicador con sus propias
> corridas. Lo que sí ejecutó: parseo AST de los 493 `.py`, inventario de comandos Typer y
> **tres mutantes puros contra el arnés**, que son los que sostienen H8-01 y H8-02.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:q7mz -->
# R8 — revisión adversarial de los Tasks 10-11 (Fase 1 dual)

**Veredicto:** NO-SHIP  
**Hallazgos:** 9 (0 críticos, 2 altos, 6 medios, 1 bajo)  
**Qué pude ejecutar:** lectura completa de las secciones exigidas de la spec y del plan; lectura de las 1.764 líneas de `CAMBIOS.diff`; trazado fuente a fuente del arnés, sus consumidores, el guard y las dos vías de `_resolver_workspace`; parseo AST de los 493 `.py` de `head` (`AST_PY_FILES=493 ERRORS=0`); inventario AST de comandos Typer (`COMANDOS_TYPER=['plan', 'apply', 'reforzar']`) y de su uso en el test contractual (`plan: 0`, `apply: 4`, `reforzar: 0`); comprobaciones estáticas del censo `strict=False` (cero llamadas de producción), de las 15 subclases de `WorkspaceError` y de los siete `xfail(strict=True)` declarados. Ejecuté además tres mutantes puros contra el arnés:

```text
{'nonce_divergente': 'cero efectos en los 4 planos; salida 99 (plano 3 sin superficie declarada)'}
estado_local_mutado_y_excepcion PASA ... estado_local_final= 2
estado_local_mutado_y_salida_0 PASA ... estado_local_final= 2
CASOS_ROOT_DESPUES= ENTORNO_SUCIO_SIN_RELOAD
```

Intenté ejecutar los tests focales con bytecode y cache de pytest desactivados:

```text
python -B -m pytest tests/test_workspace_matriz_contractual.py tests/test_guard_config_secuestrada.py -q -p no:cacheprovider ...
ERROR collecting tests/test_workspace_matriz_contractual.py
ModuleNotFoundError: No module named 'typer'

python -B -m pytest tests/test_guard_config_secuestrada.py -q -p no:cacheprovider ...
5 errors
ModuleNotFoundError: No module named 'dotenv'
```

**Qué NO pude verificar, y por qué:** la matriz contra `sala_maquina`, el guard bajo pytest real, la suite completa, las dos semillas, el `leak-scan`, los 3.358 tests, los 223 tests/17 módulos, los 7 `xfailed`/0 `xpassed`, el coste de `reload` ni el comportamiento con `pytest-xdist` quedan **SIN VERIFICAR**: la copia no trae `.venv` y el Python disponible carece de `typer` y `python-dotenv`; pytest no superó colección/setup. Las copias tampoco contienen `.git`, por lo que no pude recomputar la identidad de los commits, solo contrastar los árboles suministrados y el diff.

## Hallazgos

### H8-01 — Las filas bloqueadas aceptan cualquier error no cero y no prueban el código de §10 [ALTO]

**Dónde:** `tests/_matriz_contractual.py:371-380` (`Escenario`) y `:514-536` (`_correr_efectos`).  
**Qué está mal:** `Escenario` no contiene el error esperado. Para `checkout_ajeno`, `conflicto`, `registro_local_ausente`, `nonce_divergente` y `runtime_sin_acceso`, el juez solo exige `codigo != 0`, que no haya una excepción Python sin controlar y que no cambien sus instantáneas. No captura ni contrasta `CASE_LOCKED`, `CASE_CONFLICT`, `LOCAL_WORKSPACE_MISSING`, `LOCK_MISMATCH` o `RUNTIME_CANNOT_ACCESS_WORKSPACE`. Un `typer.Exit(99)` disparado por cualquier guarda equivocada queda verde. Lo ejecuté contra `nonce_divergente` y el informe devolvió literalmente `cero efectos ... salida 99`.  
**Por qué importa:** el criterio de salida (1) afirma una resolución única y §10 exige errores con significado estable. Este arnés solo demuestra “algún aborto controlado”; un montaje que cae por la guarda equivocada conserva verde la fila que dice aislar otra.  
**Cómo se comprueba:** sustituir el adaptador de una de esas cinco filas por `lambda _: raise typer.Exit(99)`. El test contractual debería exigir el código de §10 correspondiente; hoy `matriz_para` devuelve un veredicto verde.

### H8-02 — La fila de fallo externo queda ciega al primer intento, al canon, al estado local y al éxito falso [ALTO]

**Dónde:** `tests/_matriz_contractual.py:549-604`, especialmente `:575-603` (`_correr_idempotencia`).  
**Qué está mal:** esta fila no toma `Planos` antes del primer intento; después solo compara `hash_arbol(raiz_trabajo)` entre el primer y el segundo intento y cuenta entradas del log. No observa `canon`, `estado_local` ni el baseline previo al fallo. El parámetro `contador_externo` se recibe pero no se usa. Tampoco juzga los `(codigo, error)` que devuelve `_ejecutar`: ambos resultados se descartan. Ejecuté dos mutantes: uno incrementó estado local en cada intento y dejó propagar el fallo; el otro hizo lo mismo, tragó el fallo externo y devolvió salida 0. Los dos quedaron verdes y fueron rotulados `aborto idempotente`, con `estado_local_final=2`.  
**Por qué importa:** un reintento puede mutar el registro/sentinels o el canon en cada llamada, o informar éxito aunque el servicio haya fallado, y el arnés certifica idempotencia. Es una vía de pase por vacío precisamente en los planos 2 y 4 que el Task 10 dice contratar.  
**Cómo se comprueba:** cablear el doble de la fila 9 y hacer que `invocar` escriba un contador creciente bajo `raiz_registro` o cree/modifique una carpeta canónica en cada intento; alternativamente, capturar `RuntimeError` y devolver 0. Hoy ambos pasan. El juez debe comparar los cuatro planos contra baseline y entre intentos, y juzgar la salida.

### H8-03 — La “matriz de sala_maquina” solo ejecuta uno de sus tres entrypoints mutantes [MEDIO]

**Dónde:** `tests/test_workspace_matriz_contractual.py:99-118` (`adaptador`) frente a `scripts/sala_maquina.py:580` (`plan`), `:649` (`apply`) y `:789` (`reforzar`).  
**Qué está mal:** el adaptador llama exclusivamente a `cli.apply`. El inventario AST dio tres comandos Typer mutantes y cero llamadas a `plan` o `reforzar` en el adaptador contractual. Los tests anteriores de Task 9 comprueban algunos bloqueos compartidos, pero no someten esos dos comandos a las nueve filas del §14.1. La spec pide matriz mínima **por entrypoint mutante**, no una vez por fichero.  
**Por qué importa:** `plan` escribe manifiestos condicionalmente y `reforzar` tiene preflight, persistencia y log propios. Un defecto exclusivo de cualquiera de esas rutas no puede matar la nueva matriz, aunque la documentación diga que `sala_maquina` la corre entera.  
**Cómo se comprueba:** parametrizar el consumidor por `plan`, `apply` y `reforzar`, sembrando para cada uno una operación que de verdad escriba. Hoy la matriz completa solo produce invocaciones de `apply`.

### H8-04 — “Runtime sin acceso” prueba una bandera con el canon montado; por identidad, el offline real no llega al resolver [MEDIO]

**Dónde:** `tests/_matriz_contractual.py:427-431`; `scripts/sala_maquina.py:287-324` (`_drive_accesible`) y `:406-425` (`_resolver_workspace`).  
**Qué está mal:** la semilla deja `CASOS_ROOT` íntegramente legible y solo fija `FEESDEFENDER_OFFLINE=1`; no induce indisponibilidad de I/O. En producción, la vía por identidad ejecuta `case_locator.resolve_ref` y `catalogo.localizar` antes de `resolver_por_identidad`. Si el catálogo está realmente desmontado, entra en el fallback legacy y `caso_path` vuelve a consultar ese catálogo; termina como “caso no encontrado” sin consultar el checkout verificado del registro. La rama §7.2.9-10 solo es alcanzable por identidad cuando el canon sigue legible pero el operador lo declara offline. La vía `--case-dir` sí toma otro camino.  
**Por qué importa:** §7.2.9 permite trabajar por identidad con el único checkout local previamente verificado cuando Drive no es accesible. El cambio hace alcanzable una simulación por bandera, pero no ese caso de producción, y la fila 8 no distingue ambos. Falla cerrado, por lo que no lo clasifico como alto, pero la capacidad offline declarada no funciona.  
**Cómo se comprueba:** registrar un único checkout local válido, apuntar `CASOS_ROOT` a una raíz ausente/inaccesible, fijar `FEESDEFENDER_OFFLINE=1` e invocar `apply(case_id)`. Debe resolver el registro local; el control de flujo actual sale por el fallback legacy. Repetir con `--case-dir` muestra la asimetría.

### H8-05 — La segunda rama prometida del fallo externo no existe en los datos [MEDIO]

**Dónde:** `tests/_matriz_contractual.py:228-230`, `:377-380` y `:457-459`; plan §13.3.  
**Qué está mal:** el docstring afirma que `falla_en=1` prueba cero publicación y `falla_en=2` una publicación única estable, “las dos ramas” de la fila. `ESCENARIOS` contiene una sola instancia, con `falla_externa_en=1` y `publicaciones_admitidas=0`. No hay escenario ni parametrización con `falla_en=2`/`publicaciones_admitidas=1`.  
**Por qué importa:** cualquier defecto que aparezca cuando el primer efecto se publica y el fallo llega en la segunda llamada queda fuera de la suite, aunque la documentación lo declare contratado.  
**Cómo se comprueba:** introducir un mutante que solo rompa la ruta de `falla_en=2`, o enumerar los valores de `falla_externa_en` ejecutados: hoy el conjunto es `{1}`. Añadir la segunda variante debe volver rojo ese mutante.

### H8-06 — El guard retorna antes de restaurar un `CASOS_ROOT` ambiental sucio [MEDIO]

**Dónde:** `tests/conftest.py:44-70`, en particular el retorno de `restaurar_config_si_secuestrada` en `:64-65`.  
**Qué está mal:** si `cfg.settings.casos_root` aún coincide con `antes`, la función retorna sin comparar ni reponer `os.environ['CASOS_ROOT']`. Un test que cambie el entorno directamente —o mediante una fixture que todavía no haya recargado `core.config`— deja una bomba para el siguiente test que sí haga `reload`. Ejecuté la función con módulo sin cambio, entorno sucio y `antes_env` original; el resultado fue `CASOS_ROOT_DESPUES=ENTORNO_SUCIO_SIN_RELOAD`. Ningún test nuevo cubre esta rama: los dos casos de restauración recargan `cfg` antes de llamar.  
**Por qué importa:** el guard `autouse` se presenta como independiente del orden de teardown, pero puede dejar el entorno peor de como lo encontró y reintroducir dependencia de orden. Con fixtures de scope superior, además, su teardown puede ocurrir después del último guard de función y queda fuera de observación.  
**Cómo se comprueba:** en un test, guardar el entorno, asignar `os.environ['CASOS_ROOT']` sin recargar `core.config`, llamar al restaurador con la raíz de entrada y comprobar el entorno. Hoy conserva el valor sucio. Repetir con una fixture `module` que restaure entorno después del último test comprueba el límite de scope.

### H8-07 — El propio backstop del guard filtra rutas absolutas en el mensaje [MEDIO]

**Dónde:** `tests/conftest.py:71-76`.  
**Qué está mal:** el `AssertionError` interpola `antes` y `cfg.settings.casos_root`. Son rutas absolutas locales; pueden incluir usuario, montaje y estructura de carpetas. Es un mensaje nuevo y contradice §16, que prohíbe publicar rutas locales en mensajes. El test de `test_guard_config_secuestrada.py:89-117` solo busca la palabra `secuestrado` y no contiene un canario de ruta.  
**Por qué importa:** el backstop se dispara precisamente en una suite/CI y vuelca ambas rutas al log que se comparte para diagnosticar el fallo. No hace falta que exista un caso real para revelar información de máquina.  
**Cómo se comprueba:** forzar el `reload` inerte como hace el test existente y examinar `str(exc.value)` con raíces canario Windows, UNC y POSIX. Hoy las contiene literalmente.

### H8-08 — El criterio universal contra carpetas fantasma no está demostrado por el plano 2 [MEDIO]

**Dónde:** `PLAN.md:914-918`; `tests/_matriz_contractual.py:346-355`; `tests/test_guard_localizador.py:56-90`.  
**Qué está mal:** `PLAN.md` declara cumplido que “ninguna ruta del código” crea un directorio bajo `CASOS_ROOT` para una identidad desconocida y aduce que el plano 2 lo comprueba en cada fila. Ese plano solo observa las nueve ejecuciones de un adaptador de `sala_maquina.apply`. El guard global complementario únicamente cuenta llamadas AST explícitas a `path_for`/`caso_path(..., strict=False)`; no detecta un escritor nuevo que componga directamente una ruta, use otra API o simplemente no sea invocado por la matriz. Por tanto, la prueba citada no tiene el alcance universal del criterio.  
**Por qué importa:** es el criterio que cierra el defecto de expedientes fantasma. Marcar la fase cerrada con una prueba de un solo consumidor deja a rutas no ejecutadas fuera del gate sin declararlas `SIN VERIFICAR`.  
**Cómo se comprueba:** añadir en una copia una función de producción no invocada que haga `(settings.casos_root / 'W-FANTASMA').mkdir()`. La matriz y `test_guard_localizador` permanecen verdes: no existe un inventario/guard de escritores que pueda verla. La adjudicación debe aportar ese barrido o acotar la afirmación a los entrypoints realmente ejecutados.

### H8-09 — “intake_log ya no depende de config.caso_path” es falso en el árbol entregado [BAJO]

**Dónde:** `docs/ARQUITECTURA.md:200-204`; `core/intake_log.py:31` y comentario `:283-288`.  
**Qué está mal:** la documentación nueva dice “Dependencia retirada: `core/intake_log` ya no pasa por `config.caso_path`”, pero el módulo aún ejecuta `from .config import caso_path`. El símbolo está sin uso; además el comentario de `read_events` todavía afirma que `log_path` pasa por `caso_path`, aunque el código usa `case_locator.buscar`. La ruta funcional nueva evita el fallback, pero la afirmación de dependencia retirada y el comentario no describen el fuente.  
**Por qué importa:** Task 11 actualiza el mapa de acoplamiento; dejar una importación muerta y prosa contradictoria hace que el mapa no sea verificable por import/AST y confunde futuras auditorías del mismo fallback.  
**Cómo se comprueba:** buscar `\bcaso_path\b` en `core/intake_log.py`: aparecen la importación y el comentario obsoleto, mientras la implementación de `read_events` llama a `buscar`. Eliminar la dependencia real o corregir la afirmación hace falsable el mapa.

<!-- informe-literal:fin:q7mz -->

## 2. Evidencia verificada al adjudicar (Claude Code, 2026-08-25)

**No-mutación del objeto, recomputada por el adjudicador y no solo declarada.** Las dos copias
externas se rehicieron desde `git archive` de los mismos commits y se compararon por SHA-256 de
árbol (ruta relativa + bytes, orden sin distinción de mayúsculas):

| Copia | Ficheros | SHA-256 revisado | Recién archivado | |
|---|---|---|---|---|
| `objeto/base` (`533be06`) | 1.077 | `2c272198…c8c20c` | `2c272198…c8c20c` | coincide |
| `objeto/head` (`4aac8b0`) | 1.080 | `2e2fbc46…14c67669` | `2e2fbc46…14c67669` | coincide |

`CAMBIOS.diff` = `0f4a2ef7…6d9a1ed`. El informe recibido = `401095e5…a229f24`, **recomputado al
archivarlo y coincidente** con el que declaró el revisor en su último mensaje.

**Reproducciones propias, contra el árbol real y no contra el informe.** Regla de la casa: un
hallazgo se confirma o se refuta **contra la fuente**, no contra la seguridad con que venga
redactado, y menos aún contra un probe que corrió en el arnés del revisor.

| Hallazgo | Cómo lo reproduje | Resultado |
|---|---|---|
| H8-01 | adaptador sustituido por uno que lanza `typer.Exit(99)`, sobre `nonce_divergente` | la fila devolvía **verde** («cero efectos … salida 99») → **CONFIRMADO** |
| H8-02 | dos adaptadores: uno muta el registro en cada intento; otro además **se traga** el `RuntimeError` y devuelve 0 | los dos **verdes**, rotulados «aborto idempotente» → **CONFIRMADO** |
| H8-03 | censo AST de comandos Typer del módulo + llamadas del adaptador | comandos = `{plan, apply, reforzar}`; el adaptador solo invocaba `apply` → **CONFIRMADO** |
| H8-04 | **en vivo**: checkout local registrado + `CASOS_ROOT` a una ruta inexistente + `FEESDEFENDER_OFFLINE=1` → `cli.plan(case_id)` | `[ERROR] Caso no encontrado` **teniendo el checkout delante** → **CONFIRMADO** |
| H8-05 | lectura de `ESCENARIOS` | el conjunto de instantes ejecutados era `{1}` → **CONFIRMADO** |
| H8-06 | entorno sucio **sin** `reload` + llamada al restaurador | el entorno quedaba sucio y la función salía por la rama «nada que hacer» → **CONFIRMADO** |
| H8-07 | backstop forzado con canarios Windows, UNC y POSIX | volcaba la ruta absoluta literal → **CONFIRMADO** |
| H8-08 | lectura del alcance del plano 2 y del guard del localizador | ninguno de los dos puede ver a un escritor que la matriz no invoque → **CONFIRMADO** |
| H8-09 | AST sobre `core/intake_log.py` | `caso_path`: **1 import, 0 usos**; nadie lo importa ni lo parchea desde fuera → **CONFIRMADO** |

**Lo que aporta el adjudicador y el revisor no vio.** Arreglar H8-04 —hacer que el registro se
consulte cuando el canon calla— **reabre el defecto que la prueba de mutación del Task 7 había
cerrado en el otro camino**: `_solo_local` no recibía `drive_accesible`, así que un checkout
resuelto por esa rama sin Drive seguía anunciando `CHECKIN`, una capacidad que sin red no se
puede ejercer. Hasta R8 nadie llegaba a esa rama sin Drive, de modo que el hueco existía y era
inalcanzable; el remedio del hallazgo lo habría hecho alcanzable. Se cierra en el mismo commit,
con su test.

**Y una corrección de mi propia remediación, cazada por el canario de H8-07.** Mi primer arreglo
recortaba la ruta a «los dos últimos componentes», y en `…/servidor/SECRETO/CASOS` el penúltimo
tramo **es** un tramo interno: seguía filtrando. El canario en las tres formas de ruta lo puso
rojo. Es la tercera vez medida en este repo de que **el arreglo de un hallazgo introduce el
siguiente**, y la razón de que el canario se escribiera antes de dar por bueno el remedio.

**Limitación de la ronda, declarada y no maquillada.** El revisor **no pudo ejecutar la suite**:
la copia externa no lleva `.venv` y su Python carecía de `typer` y `python-dotenv`. Todo lo que
dependía de correr los tests —las dos semillas, los 3.358 casos, los 7 `xfailed`, el
`leak-scan`— lo aporta el adjudicador con sus propias corridas, y queda **SIN VERIFICAR por el
revisor**. No se presenta como si lo hubiera comprobado él.
