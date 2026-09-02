---
tipo: revision-adversarial
objeto: "diff remediado de MEJORAS #136 — tras los nueve hallazgos de R22"
objeto_rev: "rama claude/orquestrador-apertura-expediente-8f31bb, commit c2a9b86"
commit: c2a9b86
ronda: "23"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: z4mh
sha256_informe: 1ac2d56e0fae1510ef9792cf363acfb597f836bf178d0513fd0dd557185e3a80
adjudicado_en: docs/superpowers/plans/2026-09-02-mejoras-136-el-canon-no-es-una-copia.md §5
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R23.** El §1 conserva la voz del revisor sin una coma cambiada; la
> **adjudicación** vive en el **§5 del documento de `MEJORAS #136`**. Ronda del **DIFF REMEDIADO**,
> **autorizada expresamente por Nikolai** — el techo duro de `CLAUDE.md` prohíbe una tercera ronda
> sobre la misma pieza sin ese permiso, y aquí lo hubo.
>
> Veredicto `NO-SHIP`: **7 hallazgos** — 1 CRÍTICO, 2 ALTOS, 3 MEDIOS, 1 BAJO. Adjudicados: **7
> confirmados, 0 refutados**; los cuatro que tocan este diff **reproducidos con sondas propias**
> antes de tocar el código, y cerrados con **las mismas sondas**.
>
> **El bloque literal archiva DOS textos**, por lo mismo que en R21 y R22: el guard G9 exige la
> palabra del veredicto dentro del bloque, y el informe no la contiene.
>
> **Lo que esta ronda compró, y justifica haberla gastado:** el CRÍTICO no era una variante del
> defecto ya cerrado, era **la misma frontera mal cerrada por cuarta vez**. Yo había contratado
> «una *junction* que apunta a la raíz» y di por generalizada la propiedad, que es «cualquier alias
> cuyo destino físico caiga dentro del catálogo». La *junction* hacia un **descendiente** pasaba.
>
> **No-mutación acreditada por partida doble.** El hash agregado de `head` es idéntico al abrir y al
> cerrar en la medición del revisor, y **yo recomputé el mío** antes y después con el mismo
> resultado (`fb6b7a1d…`, 1.123 ficheros). Los valores absolutos de los dos difieren porque las
> recetas de agregación difieren; lo que acredita la no-mutación es que **cada uno** obtuvo el mismo
> valor en las dos tomas.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:z4mh -->
# Revisión adversarial R23 — remediación de `MEJORAS #136`

Objeto: `C:/tmp/r23/base` (`e24b9c6`) frente a `C:/tmp/r23/head` (`c2a9b86`). Las
copias objeto se trataron como solo lectura; toda ejecución se hizo sobre copias bajo
`C:/tmp/r23/informe`.

**SHA-256 agregado de `head` al abrir:**
`2fd7b56f2e4a8490d5589e8198f18f2c113781405cc8fb9ce59f102041889867`
(1.123 ficheros; hashes individuales de bytes, rutas relativas con `/`, orden ordinal
sensible a mayúsculas, UTF-8, `\n` real entre líneas y sin salto final).

## Resumen

La propiedad no quedó cerrada. Dos nombres de una carpeta físicamente canónica —una
junction externa dirigida a un descendiente del catálogo y un nombre Volume GUID— se
clasifican `FUERA`. Ambos atraviesan `alta`; la junction atraviesa también `revalidar`, y
el resolver puede devolver `LOCAL_CHECKOUT` cuyo `working_root` es físicamente el canon.

La separación entre invariante y política sí resuelve el bloqueo que motivó el diseño:
una entrada ya presente que pasa a `INDETERMINADO` conserva sus bytes y se puede dar de
baja. Pero la misma entrada indeterminada se entrega al resolver como candidata operativa;
conservar datos y autorizar uso necesitan polaridades distintas.

## H23-01 — Una junction a un descendiente canónico se clasifica `FUERA`

**Severidad:** CRÍTICO

**Evidencia.** `core/casos/case_catalog.py:94-124` compara cada `stat` con el de la raíz,
pero asciende con `p.parent`, que sigue el árbol **léxico**. Si la junction apunta a la
raíz, el ascenso llega al enlace y funciona. Si apunta directamente a `CASOS_ROOT/<caso>`,
primero compara la identidad del caso con la raíz (no son iguales) y después salta al
padre externo; nunca visita el padre físico canónico.

Comando:

```powershell
$env:PYTHONPATH=(Resolve-Path '.\head_work').Path
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\r23_path_probe.py
```

Salida relevante:

```text
junction                 result=dentro  samefile=True
junction-to-case         result=fuera   samefile=True
alta(junction-to-case)   ACCEPTED
junction.persisted       [WorkspaceEntry(... local_path=.../junction_to_case ...)]
revalidar(junction)      C:\tmp\r23\informe\path_probe\junction_to_case
```

La sonda pytest independiente confirma además el efecto de punta a punta:

```text
test_current_behavior_persists_junction_to_canonical_case PASSED
test_current_behavior_resolves_persisted_canonical_junction_as_local PASSED
```

El segundo control obtiene `LOCAL_CHECKOUT` y
`samefile(workspace.working_root, canon) == True`. Las pruebas del autor solo cubren una
junction que apunta exactamente a la raíz (`tests/test_registro_no_admite_el_canon.py:221-230`
y `:386-395`), frontera insuficiente.

**Qué habría que hacer.** Basar la contención en el destino final/físico de la candidata y
de la raíz, no en los padres léxicos del alias. Contratar al menos junction→raíz,
junction→caso y junction→subdirectorio, exigiendo el estado exacto `DENTRO` y una
precondición `samefile`; repetir los controles por `alta`, `revalidar` y resolver.

## H23-02 — El nombre Volume GUID de la misma carpeta sigue dando `FUERA`

**Severidad:** ALTO

**Evidencia.** `core/casos/case_catalog.py:68-79` retira `\\?\` de toda forma extendida.
Para `\\?\Volume{GUID}\...` produce `Volume{GUID}\...`, una ruta relativa falsa que
`_componentes` y `_dentro_fisicamente` reciben ya dañada (`:90-91`, `:112`).

En el volumen C: real del host:

```text
normal      C:\tmp\r23\informe\path_probe\catalog\Caso (W-R23)
Volume GUID \\?\Volume{a264b66e-e53c-46c9-8e11-075708bc9069}\tmp\...\Caso (W-R23)
samefile=True
normal=result=dentro
volume-guid=result=fuera
alta(volume-guid)=ACCEPTED
resolver.mode=local_checkout
resolver.samefile(canon)=True
```

La prueba existente llamada «catálogo en la raíz del volumen» (`tests/test_registro_no_admite_el_canon.py:285-295`)
solo usa `C:\`; no usa un nombre `Volume{GUID}`.

**Qué habría que hacer.** No tratar un nombre `Volume{GUID}` como un simple prefijo de
unidad extendida. Preservarlo para la consulta física o normalizarlo mediante el nombre
final del volumen, y añadir una prueba con el GUID real que demuestre `samefile`,
`clasificar_bajo(...) == DENTRO`, rechazo de ambos escritores y rechazo operativo.

## H23-03 — El resolver autoriza entradas `INDETERMINADO`

**Severidad:** ALTO

**Evidencia.** `_visibles` conserva correctamente lo indeterminado
(`core/casos/workspace_registry.py:198-217`), pero
`CaseWorkspaceResolver._sin_canonicos` aplica la misma regla `!= DENTRO`
(`core/casos/workspace_resolver.py:209-220`). `resolver_por_identidad` usa esa lista para
conceder un workspace (`:64-77`).

Una junction físicamente canónica con más de 64 ancestros produce:

```text
samefile                 True
classification           indeterminado
alta                     REJECTED
private_write            [WorkspaceEntry(...)]
resolver.mode            local_checkout
resolver.samefile(canon) True
baja_after_unknown       []
```

`private_write` representa una entrada heredada ya existente; no pretende ser una vía
pública nueva. La sonda demuestra simultáneamente que el argumento del autor es correcto:
si `_escribir` rechazara todo `INDETERMINADO`, la baja quedaría bloqueada. Lo que no se
sigue de ello es que el resolver deba convertir esa entrada conservada en un workspace.

Mutación propia:

```diff
- if clasificar_bajo(Path(e.local_path), raiz) != DENTRO
+ if clasificar_bajo(Path(e.local_path), raiz) == FUERA
```

Sobrevivió a los 126 tests relevantes y hace pasar la sonda que exige rechazo. Otra
mutación, `samestat(...)=True -> return None`, sobrevivió incluso a los 32 tests nuevos:
las pruebas llaman al booleano `bajo_catalogo`, donde `DENTRO` e `INDETERMINADO` colapsan
ambos a `True`.

**Qué habría que hacer.** Mantener la vista de persistencia que conserva
`INDETERMINADO`, pero exigir `FUERA` en toda frontera que autoriza usar una entrada. El
resolver debe bloquear o devolver diagnóstico explícito ante una entrada no clasificable.

## H23-04 — Un error al leer la raíz se convierte en `FUERA`

**Severidad:** MEDIO

**Evidencia.** `core/casos/case_catalog.py:106-111` captura cualquier `OSError` de
`os.stat(raiz)` y devuelve `False`. Esto incluye `PermissionError`, aunque el comentario y
la semántica solo justifican `False` para una raíz inexistente.

Sonda con una junction cuya identidad física se comprobó antes de inyectar la denegación:

```text
samefile_before_error    True
classification           fuera
authorization_boolean    False
alta_persisted           [WorkspaceEntry(... junction_to_case ...)]
```

El test de permisos del autor (`tests/test_registro_no_admite_el_canon.py:232-250`) falla
el `stat` de la **candidata**, después de leer correctamente la raíz; no ejecuta esta
rama. El mutante que separa `FileNotFoundError -> False` de los demás
`OSError -> None` sobrevivió a 126 tests relevantes. Un mutante más grueso que convierte
todo error de raíz en `None` muere por el `project_root` inexistente del constructor, no
por la frontera de permisos que supuestamente mediría.

**Qué habría que hacer.** Separar `FileNotFoundError` de los demás `OSError`; los errores
de permisos/dispositivo/transitorios deben producir `INDETERMINADO`. Añadir una prueba
específica de cada rama y evitar que un test muera incidentalmente al comprobar la otra
raíz prohibida.

## H23-05 — `revalidar` destruye la ruta de las demás entradas del mismo W-code

**Severidad:** MEDIO

**Evidencia.** El registro contrata que dos entradas del mismo W-code pueden coexistir,
pero `revalidar` toma `halladas[0]` y luego reemplaza `local_path` en **todas** las entradas
que casan con el `CaseRef` (`core/casos/workspace_registry.py:381-395`). Con un checkout y
un scratch legítimos del mismo caso:

```text
before
  checkout a -> ...\workspace-a
  scratch  b -> ...\workspace-b
after revalidar(w_code, local_path=a)
  checkout a -> ...\workspace-a
  scratch  b -> ...\workspace-a
```

Comando: `python .\r23_data_probe.py` con `PYTHONPATH=head_work`. La segunda ruta se pierde
y el registro queda con dos entradas distintas apuntando al mismo lugar. El defecto ya
existía en `base`, pero `revalidar` forma parte expresa de la remediación y del encargo;
no encontré llamadores productivos actuales fuera de tests.

**Qué habría que hacer.** Hacer inequívoca la entrada que se revalida (por ruta anterior,
nonce/tipo o una clave propia) y modificar solo esa entrada; si el selector casa con más
de una, lanzar ambigüedad sin escribir. Añadir el caso checkout+scratch del mismo W-code.

## H23-06 — La unicidad de carpeta sigue comparando cadenas, no identidad

**Severidad:** MEDIO

**Evidencia.** `alta` promete rechazar reutilizar una carpeta para otro caso, pero compara
`normcase(str(path))` (`core/casos/workspace_registry.py:343-352`). La misma carpeta, una
vez absoluta y otra relativa, atraviesa la guarda:

```text
samefile                 True
second_alta              ACCEPTED
entry W-DUPA -> C:\tmp\r23\informe\duplicate_probe\same_workspace
entry W-DUPB -> duplicate_probe\same_workspace
```

Comando: `python .\r23_duplicate_probe.py` con `PYTHONPATH=head_work`. Junction, 8.3 y
otros alias físicos ofrecen la misma discrepancia. También es preexistente en `base`, por
lo que no determina por sí solo el veredicto sobre esta remediación.

**Qué habría que hacer.** Para rutas existentes, comprobar identidad física; para destinos
inexistentes, comparar componentes absolutos normalizados. Probar relativa/absoluta,
junction y 8.3 contra la excepción `RutaYaRegistrada`.

## H23-07 — La prueba de mutación declarada no cubre varias fronteras reales

**Severidad:** BAJO

**Evidencia.** No hay en `head`, `DIFF_codigo.patch` ni `DIFF_remediacion.patch` un
manifiesto reproducible con los 13 parches, comandos y test esperado por mutante. La
afirmación conjunta «13 mutantes mueren cada uno por su frontera» queda por ello sin
verificar.

Mutantes propios que sobrevivieron a las pruebas relevantes del autor:

- `_MAX_ANCESTROS = 64 -> 63`: `32 passed`; una junction idéntica situada justo en la
  iteración 64 cambia de `DENTRO` a `INDETERMINADO`.
- `samestat(...)=True -> return None`: `32 passed`; falta afirmar el estado triestatal
  exacto, no solo el booleano que colapsa dos estados.
- Resolver `!= DENTRO -> == FUERA`: sobreviven 126 tests; no hay frontera de autorización
  para `INDETERMINADO`.
- Quitar `_visibles` separadamente de `alta`, `baja` y `revalidar`: sobreviven 126 tests.
  Las sondas propias de estado mixto sí matan cada mutante.
- Eliminar la rama `\\?\UNC\`: sobreviven 126 tests; no se ejecuta esa rama con una UNC
  real.

El código actual **sí** pasa las tres sondas mixtas: una entrada canónica heredada se purga
sin borrar la externa válida por `alta`, `baja` o `revalidar` (`6 passed` incluyendo los
controles de junction e indeterminado). El hallazgo es de contrato/prueba, no de conducta
actual en esos tres casos.

**Qué habría que hacer.** Versionar el manifiesto de los 13 mutantes con parche mínimo,
comando y test exclusivo; añadir mutantes para junction→descendiente, Volume GUID, error de
raíz, autorización de indeterminado y cada reescritor con estado mixto. Los tests de la
clasificación deben exigir `DENTRO`/`FUERA`/`INDETERMINADO`, no pasar siempre por el booleano.

## Cobertura ejecutada y efectos no buscados

### Tabla de equivalencias

| Forma | Precondición/resultado |
|---|---|
| absoluta, relativa, `..`, mayúsculas, `/`/`\` | `DENTRO` |
| alias 8.3 real | `samefile=True`, `DENTRO` |
| `\\?\C:\...` | `samefile=True`, `DENTRO` |
| junction→raíz | `samefile=True`, `DENTRO` |
| catálogo configurado detrás de junction | `DENTRO` |
| junction→caso/descendiente | `samefile=True`, **`FUERA`** |
| `\\?\Volume{GUID}\...` | `samefile=True`, **`FUERA`** |
| raíz de volumen `C:\` y descendiente | `DENTRO` |
| hermano `CASOS_x` | `FUERA` |
| UNC extendida | saneado puro ejercitado; I/O real SIN VERIFICAR |

### Escrituras y pérdida de datos

El censo de `core/` y `scripts/` encuentra tres escritores efectivos del registro:
`alta`, `baja` y `revalidar`; los tres terminan en `_escribir`. La entrada canónica puede
entrar por los dos escritores que aceptan una ruta (`alta` y `revalidar`) a causa de
H23-01/H23-02. Para el defecto de pérdida de R22, las sondas mixtas confirman que lo
`INDETERMINADO` se conserva y que una canónica heredada se purga sin borrar entradas
externas; esa remediación concreta está cerrada.

### Coste de `_dentro_fisicamente`

En una ruta local externa, una clasificación hizo 8 llamadas a `os.stat`; `cargar()` con
20 entradas hizo 160 y una `alta` con esas 20 hizo 176:

```text
single_classification     result=fuera os.stat_calls=8
cargar_20_entries         os.stat_calls=160
alta_with_20_existing     os.stat_calls=176
```

En general, una clasificación física cuesta 1 `stat` de raíz y hasta 64 de candidata y
ancestros. `alta` clasifica `N + 2m + 2` veces, `revalidar` `3m + 1`, `baja` hasta `2m` y
el resolver con registro real hasta `2m` (`N`: total; `m`: entradas del W-code).
`case_manager.es_copia_prestada` llama `registry.cargar()` desde el guard de cada escritura
(`core/case_manager.py:803-849`), de modo que el coste nuevo sí está en un camino caliente.
No medí la latencia de una UNC o unidad desconectada; queda como riesgo, no como hallazgo
autónomo.

El tope 64 no evita un ciclo lógico de `p.parent`: ese ascenso es léxico y siempre acorta
la ruta. La sonda de frontera dio `DENTRO` con el encuentro en la iteración 64 y
`INDETERMINADO` al bajar el tope a 63; en rutas más profundas el tope crea el estado que
H23-03 autoriza incorrectamente.

### Condiciones nuevas

Se ejercitaron ambos resultados de los guards de `alta`, `revalidar`, `_escribir`,
constructor del registro y seam inyectado; los tres estados de `_visibles`; éxito/fallo de
`samestat`; candidato inexistente; error de candidata; error de raíz; llegada a la raíz de
volumen y agotamiento del tope. Las condiciones son alcanzables. Las observaciones
incorrectas son las descritas en H23-01 a H23-04. La rama UNC se ejercitó solo como
transformación de cadena.

### Pruebas

- Suite relevante propia: `103 passed, 4 xfailed, 0 xpassed`.
- Los cuatro `xfail(strict=True)` ejecutados con `--runxfail` fallaron por los cuatro
  `AssertionError` documentados: el guard desvía, el destino va a la bandeja canónica, se
  emite `pendiente_checkin` y el scratch también se desvía. `core/case_manager.py` no cambió;
  la atribución a `MEJORAS #124` es correcta.
- Suite global: 3.727 tests recolectados. La ejecución terminó con 9 fallos ajenos al diff:
  ocho `PermissionError` de tests que intentan escribir dentro de la copia de scratch y uno
  del wrapper `expedientes_xl` porque su `PATH` deliberadamente vacío oculta `ping`. Por
  ello no declaro la suite global verificada en verde.

## Lo que NO pude verificar

- Las dos ejecuciones con semillas 777 y 31337: el entorno no tiene `pytest-randomly`.
- La declaración conjunta de los 13 mutantes del autor: falta un manifiesto reproducible.
- Una UNC accesible real, incluido `\\?\UNC\...`; `\\localhost\C$` devolvió acceso
  denegado. Tampoco pude probar un directorio NTFS con sensibilidad de mayúsculas activada.
- Un error de permisos natural que deniegue solo el nombre configurado de la raíz y deje
  accesible un alias; H23-04 se demostró mediante inyección después de comprobar `samefile`.
- Retarget concurrente de junctions, desaparición entre dos `stat` y latencia sobre
  unidades de red/desconectadas.
- La suite global completamente verde por las nueve limitaciones ambientales descritas;
  sí quedó verde la suite relevante.

**SHA-256 agregado de `head` al cerrar:**
`2fd7b56f2e4a8490d5589e8198f18f2c113781405cc8fb9ce59f102041889867`.

----- VEREDICTO.md (fichero aparte, pedido asi en el mandato) -----

NO-SHIP
La remediación aún admite y resuelve como copia local rutas físicamente canónicas mediante junction a descendiente y Volume GUID.
<!-- informe-literal:fin:z4mh -->

## 2. Evidencia verificada por el adjudicador

Reproducido por mí **antes** de remediar, con sonda propia y sobre el árbol real:

```
H23-01  junction -> RAIZ        : dentro | samefile: True
H23-01  junction -> CASO        : fuera  | samefile: True     ← el CRITICO
H23-01  junction -> CASO / sub  : fuera
H23-02  Volume GUID             : fuera  | samefile: True
H23-03  el resolver filtra con '!= DENTRO'                    ← conservar != autorizar
H23-04  raiz ilegible           : fuera
```

Y **cerrado con las mismas sondas**, que es la única forma de que el arreglo no sea una hipótesis:

```
H23-01  junction -> CASO        : dentro
H23-01  junction -> CASO / sub  : dentro
H23-02  Volume GUID             : dentro
H23-03  el resolver filtra con '!= DENTRO'  ->  False
H23-04  la rama desaparece con el ascenso
```

**El remedio de fondo no fue parchear el ascenso por ancestros, fue retirarlo.**
`os.path.realpath` resuelve *junctions* estén donde estén en la cadena, expande el alias 8.3 y
traduce el nombre Volume GUID; con él se van también el tope de 64 ancestros y la rama del `stat`
de la raíz, que eran superficie propia y donde R23 encontró otros dos defectos. Menos código mío,
más sistema operativo.

**Los dos MEDIOS que este PR NO arregla, y por qué.** H23-05 (`revalidar` pisa la ruta de las demás
entradas del mismo W-code) y H23-06 (la unicidad de carpeta compara cadenas) son **preexistentes en
`base`** — el propio revisor lo dice — y no tienen llamador productivo. Van a `MEJORAS` con su
medición en vez de ensancharse aquí: un PR que arregla lo que encuentra por el camino deja de ser
revisable.

**H23-07 tenía razón y se cerró:** «catorce mutantes mueren cada uno por su frontera» en un mensaje
de commit no es verificable. El manifiesto ejecutable vive ahora en `tests/_mutantes_mejoras_136.py`.
Al ejecutarlo aparecieron **cuatro** problemas más que ninguna ronda vio: dos expectativas mías
demasiado estrechas y dos mutantes rotos —uno retiraba una *llamada* que otro test parchea, otro
dejaba un nombre sin importar y moría por `NameError`, no por contrato—.

**Diferencia de entorno, dicha aquí y no en el plan:** el revisor reporta nueve fallos en la suite
global que atribuye a su sandbox. Mis dos corridas del mismo commit dan 0 fallos, así que son de su
entorno y no del objeto.
