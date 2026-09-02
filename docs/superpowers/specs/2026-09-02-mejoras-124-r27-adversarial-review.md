---
tipo: revision-adversarial
objeto: "partir MEJORAS #124 en dos propiedades: ubicacion e identidad"
objeto_rev: "rama claude/partir-costura-identidad, commit e05d5a6"
commit: e05d5a6
ronda: "27"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: w2xq
sha256_informe: 2af1586c29d4935e29cd35f7331e32ff73e83ace5e64d57c6cd6b163124126e0
adjudicado_en: docs/superpowers/plans/2026-09-02-mejoras-124-copia-de-trabajo.md §14
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R27.** El §1 conserva la voz del revisor sin una coma cambiada; la
> **adjudicación** vive en el **§14 del plan**. Es la ronda del **DIFF** de la partición.
>
> Veredicto `NO-SHIP`: **6 hallazgos** — 1 CRÍTICO, 2 ALTOS, 2 MEDIOS, 1 BAJO. Adjudicados: **6
> confirmados, 0 refutados**; el crítico **reproducido con sonda propia** antes de remediar y cerrado
> con la misma.
>
> **Lo que esta ronda compró, y es la ronda mejor gastada de la sesión.** El crítico es una
> **regresión que introduje al partir**: al separar la función, `ubicacion` se quedó con «¿está
> dentro del catálogo?» —cierto para la raíz del catálogo, un directorio suelto o la bandeja de otro
> caso— y la mitad de identidad se saltaba por un retorno temprano. Tres escrituras dentro del
> catálogo **sin identidad y sin mutex**.
>
> **Y encontró que mi arnés no distinguía «no pude ejecutar» de «cero fallos»** (H27-04): ignoraba
> el código de salida de pytest, así que un error de colección se leía como baseline verde. Lo
> reprodujo apuntándolo a un fichero inexistente. Eso invalidaba, en principio, **todas** las
> afirmaciones que el arnés había hecho antes.
>
> **El bloque literal archiva DOS textos**, por lo mismo que en R21-R26: el guard G9 exige la palabra
> del veredicto dentro del bloque y el informe no la contiene.
>
> **No-mutación acreditada por partida doble:** hash idéntico al abrir y al cerrar en su medición, y
> yo recomputé el mío antes y después (`80346b63…`, 1.137 ficheros).

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:w2xq -->
# Revisión adversarial R27 — partir una pieza en dos propiedades

## sha256 agregado al abrir

`ac47006a76af3304f1406f26c415bd67eee92d9ba8796a6f9b9102ef929ae271` (1.137 ficheros).

Algoritmo: para cada fichero de `C:/tmp/r27/head`, sha256 de sus bytes; después, sha256 del UTF-8 de la lista ordenada por ruta relativa POSIX `<sha256>  <ruta>`, unida con `\n` y sin salto final.

## H27-01 — Un `drive_active` sin canon localizado obtiene capacidad de escritura dentro del catálogo

**Severidad: CRÍTICO**

**Evidencia.** En `head/core/casos/ubicacion.py:66-78`, ubicación solo exige que un `drive_active` esté `DENTRO`. Después, `head/core/casos/escritura.py:249-259` convierte `LocalWorkspaceMissing` en `canon_dir = None` y retorna antes de la igualdad con el canon correcto, que está en `head/core/casos/escritura.py:261-269`. `deposito()` admite identidad no utilizable en modo `libre` (`head/core/casos/escritura.py:348-368`) y considera canónico el destino únicamente por el modo (`head/core/casos/escritura.py:162-170, 376-383`).

La regresión es directa: `base/core/casos/escritura.py:208-214` rechazaba expresamente `canon_dir is None` para `DRIVE_ACTIVE`.

Reproducción ejecutada sobre la copia de `head`:

```text
python -m pytest ../test_r27_adversarial.py -q -s ... --basetemp=../pytest_tmp/repro
ACEPTADO (): w=None; escrito=...\CATALOGO\00_Input\prueba.txt
ACEPTADO ('directorio_suelto',): w=None; escrito=...\CATALOGO\directorio_suelto\00_Input\prueba.txt
ACEPTADO ('Caso_B', '_pendiente_checkin', 'otro'): w=None; escrito=...\CATALOGO\Caso_B\_pendiente_checkin\otro\00_Input\prueba.txt
4 passed in 0.51s
```

El cuarto caso comprueba la otra polaridad: un canon A conocido con raíz B sí lanza `IdentidadDiscordante`. La misma sonda contra `base` dio:

```text
BASE RECHAZA: ValueError: un workspace `drive_active` tiene que ser el expediente canonico...
1 passed in 0.41s
```

El resolver ordinario no fabrica este estado: produce `DRIVE_ACTIVE` después de localizar el canon. Pero `CaseWorkspace` es público y el propio cambio dice que `deposito()` debe defenderse frente a valores construidos por otros llamadores. El efecto es una capacidad sin identidad ni mutex sobre la raíz del catálogo, un directorio suelto o una bandeja de otro caso.

**Qué habría que hacer.** Antes del retorno de `canon_dir is None`, rechazar todo `WorkspaceMode.DRIVE_ACTIVE` con `IdentidadDiscordante` (o error específico equivalente). Mantener luego la igualdad con el canon localizado. Añadir pruebas por la puerta pública `deposito(..., modo="libre")` para las tres raíces reproducidas.

## H27-02 — Dos mutantes de las propiedades nuevas sobreviven: falta contrato de identidad y cableado `drive_active`

**Severidad: ALTO**

**Evidencia.** El baseline dirigido fue 56/56 verde. Los seis mutantes oficiales se ejecutaron individualmente con el mismo conjunto de cuatro ficheros: A1, A2 y A3 solo mataron tests de `test_ubicacion_del_workspace.py`; B1, B2 y B3 solo mataron tests de `test_escritura_sobre_workspace.py`.

Dos mutantes propios, distintos de esos seis, sobrevivieron con los 56 tests verdes:

```text
I-DRIVE-EXACT: cambiar la condición de escritura.py:264 a
    if False and WorkspaceMode(workspace.mode) is WorkspaceMode.DRIVE_ACTIVE ...
resultado: 56 passed

U-DRIVE-WIRING: no llamar ubicacion.exigir_coherente(workspace) cuando el modo
    es DRIVE_ACTIVE
resultado: 56 passed
```

El traslado borró la integración `deposito(... DRIVE_ACTIVE, copia_local)` del fichero de identidad. El nuevo rechazo externo solo llama directamente a `ubicacion.exigir_coherente` (`head/tests/test_ubicacion_del_workspace.py:93-104`). La única integración conservada usa `LOCAL_CHECKOUT` sobre el canon (`head/tests/test_ubicacion_del_workspace.py:159-184`). Tampoco hay un test que obligue a la nueva igualdad `drive_active == canon de este caso`.

Así, el criterio “cada mutante oficial mata solo su fichero” se satisface aunque dos piezas esenciales del diff puedan desaparecer. Esta carencia permitió que H27-01 entrara verde.

**Qué habría que hacer.** Añadir en el fichero de ubicación un test de `deposito()` con `DRIVE_ACTIVE` fuera del catálogo; añadir en identidad tests de canon A/raíz B y canon ausente; e incorporar mutantes explícitos para el cableado de la llamada y para `escritura.py:264-269`.

## H27-03 — Un mutante nuevo de ubicación sí cruza al fichero de identidad

**Severidad: MEDIO**

**Evidencia.** Se mutó solo `head/core/casos/ubicacion.py:64-69` para desactivar el rechazo temprano de modo bloqueado:

```text
if False and (modo.es_bloqueado or workspace.working_root is None):

FAILED tests/test_ubicacion_del_workspace.py::TestModoBloqueado::test_no_tiene_ubicacion_que_comprobar
FAILED tests/test_escritura_sobre_workspace.py::TestModoBloqueado::test_un_workspace_bloqueado_se_rechaza
```

El segundo test sigue en el fichero declarado como identidad (`head/tests/test_escritura_sobre_workspace.py:293-301`). Por tanto, la afirmación general del arnés —que romper ubicación no pone rojo identidad— solo vale para los tres mutantes escogidos, no para la propiedad completa.

**Qué habría que hacer.** Clasificar expresamente “modo bloqueado/no hay raíz” como ubicación y mover su prueba de integración al fichero de ubicación, o abandonar la exclusividad por nombre de fichero y definir una matriz que permita tests de integración declarados. En ambos casos, añadir este mutante al arnés.

## H27-04 — El arnés confunde errores de pytest/Git con resultados de tests

**Severidad: ALTO**

**Evidencia.** `head/tests/_mutantes_particion_124.py:73-79` descarta `returncode` y `stderr` de pytest y devuelve únicamente líneas `FAILED `. `main()` interpreta el conjunto vacío como baseline verde en `:88-91`. La misma omisión existe para `git status` en `:83-87`.

Reproducción:

```text
python -c "import tests._mutantes_particion_124 as m;
m.FICHEROS=('tests/NO_EXISTE_R27.py',); print(m._corre())"
resultado_de__corre= set()
exit=0
```

Pytest había terminado con error de uso/colección, no con tests verdes. En un mutante, una corrida con errores adicionales y al menos un `FAILED` propio puede incluso imprimirse como `[ok]`, porque los `ERROR` no entran en `ajenos`.

**Qué habría que hacer.** Hacer que `_corre()` devuelva `returncode`, stdout y stderr. El baseline debe exigir `returncode == 0`; una corrida mutada solo debe contar como muerte contractual si terminó como ejecución válida de pytest y no contiene errores de colección, setup ni error interno. Validar también el `returncode` de `git status`.

## H27-05 — La restauración no cubre la propia escritura y repone todo el árbol

**Severidad: MEDIO**

**Evidencia.** En `head/tests/_mutantes_particion_124.py:101-105`, `p.write_text(...)` está antes del `try`. Una escritura parcial, un `PermissionError` o una interrupción en ese punto no ejecutan el `finally`. La restauración usa además `git checkout -- .`, no el fichero mutado.

En la copia ejecutable, la primera ejecución terminó precisamente en `:101` con `PermissionError`, antes de entrar en el `try`. La sandbox también impidió que Git sustituyera ficheros con `checkout`; por eso los seis mutantes se ejecutaron de forma equivalente uno por uno, restaurando cada fichero desde `head` en un proceso separado. El defecto del alcance existe con independencia de esa limitación ambiental: un cambio concurrente en cualquier otro fichero sería descartado por `checkout -- .`.

**Qué habría que hacer.** Leer y guardar los bytes originales, meter la escritura dentro del `try`, y restaurar exclusivamente `p` desde esos bytes en el `finally`. Comprobar la restauración y abortar si no coincide el hash original.

## H27-06 — Ubicación acepta aliases físicos del canon e identidad rechaza el mismo expediente por texto

**Severidad: BAJO**

**Evidencia.** `clasificar_bajo` resuelve físicamente junctions, alias 8.3, prefijo extendido y Volume GUID (`head/core/casos/case_catalog.py:91-149`). La igualdad de identidad usa en cambio `_normal`, que es solo `normcase(abspath(...))` (`head/core/casos/case_mutex.py:173-179`), en `head/core/casos/escritura.py:264-265`.

La sonda real de Windows dio `dentro` para `.claude`, `CLAUDE~1`, `\\?\C:\...\.claude` y descendientes inexistentes con y sin prefijo. Nueve pruebas existentes de junction, Volume GUID y rutas inexistentes pasaron. Sin embargo, al encadenar ambas propiedades:

```text
ALIAS 8.3: ubicacion=DENTRO; identidad=IdentidadDiscordante
1 passed in 0.63s
```

No encontré un camino ordinario del resolver que entregue `DRIVE_ACTIVE` con alias: el caso afecta sobre todo a `CaseWorkspace` construido por un llamador. La comparación léxica ya existía antes del diff, por lo que es una incompatibilidad retenida, no la regresión de H27-01.

**Qué habría que hacer.** Fijar el contrato: si “el expediente correcto” es identidad física, comparar con `samefile`/`realpath` y definir qué ocurre cuando la ruta no existe; si solo se admite la forma canónica textual del resolver, rechazar y documentar los aliases en la frontera de ubicación para que ambas propiedades no den respuestas contradictorias.

## Lo que NO pude verificar

- **SIN VERIFICAR:** suite completa verde. Con `PYTHONHASHSEED=777` llegó al 100%, pero hubo 11 fallos ambientales: ocho tests intentaron crear/borrar dentro del repo copiado y la sandbox lo denegó, uno dependía del comando `ping`/wrapper y dos esperaban un `.venv` presente en la copia. No atribuí esos fallos al diff ni los conté como refutación.
- **Verificado parcialmente:** 56/56 tests de los cuatro ficheros del arnés pasaron en baseline; 126/126 de resolver, matriz de workspaces, Sala de máquina, offline/legacy, `--case-dir`, ubicación e identidad pasaron con `PYTHONHASHSEED=31337`; 9/9 pruebas físicas dirigidas pasaron. No ejecuté los tests `slow`.
- El arnés original no pudo completar una corrida monolítica en esta sandbox por su estrategia de escritura/restauración. Sí ejecuté separadamente y restauré los seis mutantes exactos, además de tres mutantes propios.
- No validé un montaje Drive Stream real, una ruta UNC remota desconectada ni una carrera TOCTOU mientras cambia un punto de reanálisis. Los alias 8.3, prefijo extendido, Volume GUID, junction y rutas inexistentes sí se ejercitaron en el host local.
- No apareció un estado ordinario de producción de `resolver`/`sala_maquina` que ahora fuese rechazado y antes pasase. H27-01 se alcanza mediante el valor público `CaseWorkspace`, que es precisamente la superficie defensiva declarada por el cambio.

## sha256 agregado al cerrar

`ac47006a76af3304f1406f26c415bd67eee92d9ba8796a6f9b9102ef929ae271` (1.137 ficheros).

----- VEREDICTO.md (fichero aparte, pedido asi en el mandato) -----

NO-SHIP
Regresión crítica: un `drive_active` sin canon localizado obtiene una capacidad sin identidad ni mutex para escribir dentro del catálogo.
<!-- informe-literal:fin:w2xq -->

## 2. Evidencia verificada por el adjudicador

Reproducido por mí **antes** de remediar, con sonda propia:

```
la RAIZ del catalogo        ACEPTADO | mutex=False | dentro del catalogo=True
un directorio suelto        ACEPTADO | mutex=False | dentro del catalogo=True
la bandeja de OTRO caso     ACEPTADO | mutex=False | dentro del catalogo=True
```

Y cerrado con **la misma sonda**: las tres devuelven `IdentidadDiscordante`.

El defecto del arnés (H27-04) también se comprobó por las dos polaridades: apuntado a un fichero
inexistente devuelve ahora `valida=False`, y sobre los ficheros reales `valida=True`. Antes las dos
situaciones daban el mismo conjunto vacío.

**Los tres mutantes que el revisor escribió y yo no tenía están incorporados al arnés**, que pasa de
seis a diez. Dos de ellos **sobrevivían** —el cableado de `ubicacion` para `drive_active` y la
igualdad «el expediente correcto»— y uno **cruzaba** la partición.
