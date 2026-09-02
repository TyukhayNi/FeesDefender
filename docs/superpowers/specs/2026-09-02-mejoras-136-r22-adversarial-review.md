---
tipo: revision-adversarial
objeto: "diff de MEJORAS #136 — el registro deja de admitir el canon como copia local"
objeto_rev: "rama claude/orquestrador-apertura-expediente-8f31bb, commit 55dcb06"
commit: 55dcb06
ronda: "22"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: v9pt
sha256_informe: 42cf4fd7fc25a53a32288d0f3ca6cd73c2cb7601bda45a1c2fc9174d062ec067
adjudicado_en: docs/superpowers/plans/2026-09-02-mejoras-136-el-canon-no-es-una-copia.md §4
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R22.** El §1 conserva la voz del revisor sin una coma cambiada; la
> **adjudicación** vive en el **§4 del documento de `MEJORAS #136`**. Es la ronda del **DIFF**.
>
> Veredicto `NO-SHIP`: **9 hallazgos** — 4 CRÍTICOS, 4 ALTOS, 1 BAJO. Adjudicados: **9 confirmados,
> 0 refutados**; los cuatro graves **reproducidos con sondas propias** antes de tocar el código.
>
> **El bloque literal archiva DOS textos**, por la misma razón que en R21: el guard **G9** exige que
> la palabra del veredicto conste literalmente en el bloque, y el informe no la contiene. Pedirlo en
> un fichero aparte evita que la escriba yo, que es lo que el acta existe para hacer imposible.
>
> ## La primera corrida se cortó, y lo que se cortó fue MI encargo
>
> El primer intento de R22 murió en el filtro de contenido del revisor, sin informe ni veredicto. La
> causa no fue el objeto: fue el mandato, que pedía «rodear las cuatro puertas» y «encontrar una
> forma de meter el canon en el registro» — redactado así se lee como pedir eludir un control de
> seguridad. Es la **segunda** vez que piso esa trampa teniéndola anotada (la primera fue en R15).
>
> **Eso dejó la ronda SIN VERIFICAR, no refutada**, y por eso se relanzó con la misma sustancia
> adversarial reformulada como problema de **clasificación**: «estas doce formas de escribir la
> misma carpeta, ¿se clasifican todas igual?». El informe archivado es el de la segunda corrida.
>
> **Esta ronda EJECUTÓ**: sondas propias, la suite entera desde una copia, junctions reales y
> mutantes escritos por el revisor. Los cuatro graves salieron de ejecutar, no de leer.
>
> **No-mutación acreditada por partida doble.** El hash agregado de `head` (1.123 ficheros) es
> idéntico al abrir y al cerrar, y **lo recomputé yo** antes y después: la garantía no depende de la
> palabra del revisor. El valor absoluto que el revisor publica difiere del mío porque su receta de
> agregación no es la mía; lo que acredita la no-mutación es que **cada uno de los dos** obtuvo el
> mismo valor al abrir y al cerrar.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:v9pt -->
# Revisión adversarial R22 — diff de `MEJORAS #136`

Objeto: árbol `head` del commit `55dcb06`, comparado con `base` en `e24b9c6`. Las dos
copias de `C:/tmp/r22` se trataron como solo lectura. Las importaciones, pruebas, junctions y
mutaciones se ejecutaron únicamente sobre copias y sondas bajo `C:/tmp/r22b`.

## `sha256` agregado de `head` al abrir

`206bfab64396a2652af6e0f8b8645a519e1476e7cdc1dff70f00b0695d4c0574`

Definición ejecutada: para los 1.123 ficheros, se calculó `sha256(bytes)`, se formó una
línea `<sha256>  <ruta-relativa-en-POSIX>`, se ordenaron las rutas por orden de cadenas de
Python, se unieron las líneas con `\n` sin salto final y se calculó el SHA-256 del UTF-8.

## Resumen

El arreglo cierra el caso ordinario que motivó `#136`, pero no cierra la propiedad para
formas equivalentes de ruta de Windows. Una ruta canónica escrita con prefijo extendido
`\\?\` es el mismo directorio según `os.path.samefile`, pero `bajo_catalogo` responde
`False` y `WorkspaceRegistry.alta` la acepta. Además, `revalidar` sigue siendo un escritor
sin la nueva guarda. Son dos vías ejecutadas que mantienen incompleta la invariante.

El veredicto recomendado es `NO-SHIP`. No adjudico los hallazgos; corresponde contrastarlos
con la fuente y decidir su remedio.

## 1. Tabla de equivalencias ejecutada

| Familia | Formas comparadas | Resultado |
|---|---|---|
| Relativa / absoluta | `Catalogo/Caso` desde el padre frente a ruta absoluta | ambas `True` |
| `..` / normalizada | `Catalogo/fantasma/../Caso`; escape a hermano | `True`; escape `False` |
| Mayúsculas y separador | `swapcase()`, `/` y `\` | todas `True` |
| 8.3 / larga | alias real `PREDIC~1/...` frente a nombre largo, en ambos sentidos | ambas `True` |
| Junction exterior → catálogo | junction exacta y un hijo | ambas `True` |
| Catálogo detrás de junction | candidato por alias y por destino real | ambas `True` |
| Prefijo extendido / normal | una sola de las dos partes con `\\?\` | **`False` frente a `True`; H22-01** |
| Volume GUID / letra | mismo directorio existente y `samefile=True` | **`False`; H22-01** |
| UNC / letra | `\\localhost\C$` no estaba accesible y no había unidades de red mapeadas | **SIN VERIFICAR** |
| Hermano `CASOS_x` / `CASOS` | rutas existentes hermanas | ambas `False`, correcto |
| Raíz de volumen | `CASOS_ROOT=C:\`, raíz y descendiente | raíz `True`, descendiente **`False`; H22-06** |

### H22-01 — El prefijo extendido evade la protección del catálogo

**Severidad: ALTO**

**Evidencia.** `core/casos/case_catalog.py:84-95` compara cadenas normalizadas, pero
`Path.resolve()` conserva el espacio de nombres extendido solo en el operando que lo usa.
Sonda independiente:

```powershell
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\verify_h22_paths.py
```

```text
"normal": true,
"extended": false,
"samefile": true,
"normal_resolve": "C:\\tmp\\r22b\\verify_paths_fixture\\Catalog\\Case",
"extended_resolve": "\\\\?\\C:\\tmp\\r22b\\verify_paths_fixture\\Catalog\\Case",
"alta": "accepted"
```

La matriz separada reprodujo el defecto en ambos sentidos (candidato extendido/raíz normal
y candidato normal/raíz extendida) y mediante el nombre Volume GUID. Es la misma carpeta;
la clasificación correcta es `True`.

**Qué habría que hacer.** Comparar en un espacio de nombres canónico común y por identidad
física cuando el objeto exista, sin depender de que ambos operandos lleguen con el mismo
prefijo. Añadir regresiones para `\\?\`, Volume GUID y ambos sentidos; la variante UNC/letra
debe probarse en un host donde exista un recurso accesible.

### H22-02 — `revalidar` sigue siendo un escritor capaz de introducir el canon

**Severidad: ALTO**

**Evidencia.** `WorkspaceRegistry.revalidar` reemplaza `local_path` y llama a `_escribir`
sin `bajo_catalogo` (`core/casos/workspace_registry.py:301-315`). La sonda partió de una
entrada externa admitida y revalidó contra el canon:

```text
"revalidar_raw_path": "C:\\tmp\\r22b\\verify_registry_fixture\\CASOS\\Case",
"revalidar_raw_is_canon": true,
"revalidar_visible_after_write": 0
```

El JSON crudo queda apuntando al catálogo y la lectura siguiente oculta la entrada. Los
tests de registro y los nuevos de `#136` permanecieron verdes; la sonda paralela obtuvo
`35 passed` sobre esos dos ficheros.

**Qué habría que hacer.** Aplicar la misma guarda antes de que `revalidar` escriba, o
eliminar de su contrato la posibilidad de cambiar `local_path` si solo debe renovar la
marca temporal. Añadir un mutante específico de este segundo escritor y comprobar también
que un rechazo no altera el JSON previo.

### H22-03 — La raíz del propio registro conserva una definición divergente y puede vivir en el catálogo

**Severidad: ALTO**

**Evidencia.** Pese a que `case_catalog.py:51-59` declara una definición única,
`WorkspaceRegistry.__init__` usa todavía `_bajo` (`workspace_registry.py:94-96,149-155`),
que no hace `abspath`, no resuelve junctions y no falla cerrado. La sonda propia ejecutó:

```text
"relative_registry_written_under_catalog": true,
"junction_created": true,
"junction_registry_written_under_catalog": true
```

La junction estaba fuera léxicamente pero apuntaba a `CASOS/junction_registry`; el alta
escribió allí `W-JUNC.json`. El caso relativo hizo lo mismo desde el padre del catálogo.
La divergencia ya existía en `base`, pero contradice directamente la decisión de unificar
el concepto que se revisa y mantiene una escritura privada dentro del catálogo.

**Qué habría que hacer.** Hacer que el constructor reutilice la definición robusta —o una
primitiva común explícitamente apta para raíces aún inexistentes— y cubrir ruta relativa,
junction y espacios de nombres alternativos. Revisar también el clasificador separado de
`case_mutex.py:173-235`; `escritura._bajo` protege una base distinta y no es por sí solo
otra definición de “bajo el catálogo”.

### H22-04 — El fallo cerrado cambia de polaridad al filtrar la lectura

**Severidad: ALTO**

**Evidencia.** Ante `OSError`/`ValueError`/`RuntimeError`, `bajo_catalogo` devuelve `True`
(`case_catalog.py:86-94`). En `alta`, adopción y resolución por ruta eso significa
“rechazar”. En `_sin_canonicas`, `True` significa “la entrada no existe”
(`workspace_registry.py:174-195`). Una ruta externa válida con fallo de resolución
selectivo produjo:

```text
{
  "normal": "AmbiguousCase",
  "on_resolve_error_mode": "drive_active",
  "on_resolve_error_root_is_canon": true
}
```

Sin el error, el scratch local y el canon publicado son ambiguos; con el error inducido,
el scratch desaparece y el resolver autoriza el canon. La pérdida puede persistir: con dos
entradas del mismo W-code, una alta posterior reescribió el fichero filtrado:

```text
"visible_during_indeterminate": 0,
"raw_after": ["...\\Desktop\\Two"],
"hidden_survived": false
```

La propagación está ejecutada. **SIN VERIFICAR:** no se consiguió provocar en este host un
`Path.resolve()` natural sobre una ruta local/UNC legítima; se indujo exactamente una de
las excepciones que producción captura.

**Qué habría que hacer.** No colapsar “dentro”, “fuera” e “indeterminado” en un booleano
cuando los consumidores tienen polaridades opuestas. La lectura debe preservar o elevar el
estado indeterminado, nunca convertirlo en ausencia ni usar una vista filtrada para una
reescritura destructiva.

### H22-05 — La segunda guarda no es imposible en el contrato inyectable del resolver

**Severidad: MEDIO**

**Evidencia.** En el grafo productivo actual, el único constructor está en
`scripts/sala_maquina.py:392-395`, usa el `WorkspaceRegistry` concreto y
`resolver_por_identidad` llega a `_leer` a través de `buscar`; no se encontraron subclasses
ni adaptadores en `core/` o `scripts/`. En ese sentido estrecho, el argumento del autor se
verifica hoy.

Pero el resolver recibe el registro por inyección y confía en cualquier resultado de
`buscar` (`workspace_resolver.py:54-68,122-136`). Una implementación mínima de ese seam
devolviendo una entrada canónica produjo:

```text
INJECTED_REGISTRY_MODE local_checkout
INJECTED_REGISTRY_ROOT_IS_CANON True
```

Por tanto, la afirmación de que una segunda comprobación “no podría ser falsa nunca” no es
cierta para la API publicada, aunque hoy no haya un llamador productivo interno que la
active.

**Qué habría que hacer.** O revalidar la raíz en el resolver, o cerrar y documentar el
contrato de modo que solo pueda recibir un registro cuya lectura tenga esa garantía. La
fuente de raíz del filtro y la del catálogo inyectado tampoco deberían poder divergir.

### H22-06 — Un catálogo configurado en la raíz de volumen no reconoce descendientes

**Severidad: MEDIO**

**Evidencia.** Con `CASOS_ROOT=C:\`, `r` ya termina en separador y las expresiones
`r + os.sep` de `case_catalog.py:88,95` buscan el prefijo `c:\\`. Sonda:

```text
root='C:\\'
r_plus_sep='c:\\\\'
actual_root=True
actual_child=False
```

La clasificación correcta del descendiente es `True`. El mismo patrón afecta a una raíz
de recurso UNC.

**Qué habría que hacer.** Comparar componentes o normalizar la raíz antes de añadir el
separador. Añadir casos de raíz de volumen y raíz UNC.

### H22-07 — La prueba de mutación declarada sobreestima dos fronteras

**Severidad: MEDIO**

**Evidencia.** Los cinco mutantes declarados sí murieron de forma focal: `alta` sin rechazo
(2 rojos), adopción sin rechazo (2), lectura sin filtro (4), predicado sin comparación
física (solo el test de junction) y fallo cerrado globalmente invertido (solo el test que
fuerza `Path.resolve`). No hubo falsos matadores fuera de esas fronteras.

Sin embargo, sobrevivieron mutantes razonables más finos:

- invertir solo el primer `except` léxico a `return False`: los 30 tests enfocados verdes;
  una corrida completa llegó al 100 % y solo tuvo el fallo ambiental ajeno del wrapper;
- retirar solo `RuntimeError` del segundo `except`: los mismos 30 verdes;
- descartar el fichero entero si contiene alguna entrada canónica, en lugar de conservar
  las externas: `61 passed, 4 xfailed`;
- retirar únicamente `cf == rf` manteniendo el prefijo físico: los ocho tests de
  `TestPredicado` y `TestBajoCatalogo` quedaron verdes, aunque una junction que apunta
  exactamente a la raíz cambia de `True` a `False`.

Esto demuestra que el mutante global de “fallo cerrado” solo prueba la rama física de
`OSError`, y que no hay contrato ejecutable para un fichero mixto ni para la igualdad
física exacta. Eliminar a la vez `c == r` y `cf == rf` sí muere por el test anterior de la
raíz léxica, pero ese matador no cubre `cf == rf` por separado.

**Qué habría que hacer.** Añadir mutantes independientes por rama de excepción y por
igualdad/prefijo físico, más un registro mixto con una entrada heredada canónica y otra
externa válida que deba sobrevivir.

### H22-08 — El test del registro ilegible sí distingue la polaridad que su docstring niega

**Severidad: BAJO**

**Evidencia.** `tests/test_guard_copia_prestada.py:222-233` dice que hoy el test no puede
distinguir su promesa. Mutar únicamente `case_manager.es_copia_prestada` para devolver
`True` en su `except Exception` produjo:

```text
1 failed
assert decision.desviar is True
E assert False is True
```

El `monkeypatch` obliga a pasar por la excepción; que la vía sana de `#124` también devuelva
`False` no impide distinguir entre fallo cerrado (`False`) y fallo abierto (`True`).

**Qué habría que hacer.** Mantener el test como guard de polaridad y corregir su docstring;
no diferir su valor probatorio a la futura revisión de `#124`.

### H22-09 — Un nombre Windows inválido con NUL evade el fallo cerrado

**Severidad: BAJO**

**Evidencia.** En CPython 3.14, `abspath`, `normcase` y `Path.resolve(strict=False)` no
lanzaron para `C:\outside\bad\0name`; la función llegó al `False` final y `alta` persistió
la entrada. La sonda propia obtuvo `"nul": false`; la sonda separada confirmó el JSON
aceptado. No es un directorio legítimo, pero contradice la política declarada “no puedo
saber dónde cae ⇒ rechazo”.

**Qué habría que hacer.** Validar que la representación es una ruta Windows utilizable
antes de clasificar/persistir, y probar caracteres inválidos sin confiar en que las
primitivas de Python lancen.

## 2. Decisiones de diseño

1. **Fallo cerrado.** No apareció un falso positivo natural sobre destinos externos no
   existentes: una ruta bajo un padre aún no creado y `Z:\New Workspace` dieron `False`.
   En consumidores que rechazan `True`, la nueva polaridad es coherente. En el filtro de
   lectura, la misma polaridad es incorrecta por H22-04.
2. **Descartar en lectura.** Para una entrada inequívocamente canónica heredada, descartar
   recupera la conducta segura y evita inutilizar el registro completo. Sí oculta el dato
   defectuoso sin aviso; más grave, el diseño no separa ese caso del indeterminado y no
   prueba que conserve otras entradas válidas del fichero (H22-04/H22-07).
3. **Sin segunda comprobación en identidad.** Todos los llamadores productivos internos
   actuales pasan por `_leer`. El seam público de inyección sí puede evitarla y reproduce
   `LOCAL_CHECKOUT` sobre el canon (H22-05).
4. **Función de módulo.** El método de `CaseCatalog` delega correctamente. No obstante,
   quedan `_bajo` en `workspace_registry` y `case_mutex`; la primera protege exactamente
   una frontera del catálogo y ya diverge de forma ejecutada (H22-03). La de `escritura`
   comprueba contención bajo una capacidad concreta, no pertenencia a `CASOS_ROOT`.

## 3. Guard, fixtures y atribución de `#124`

Con `--runxfail`, las cuatro pruebas modificadas fallaron de la misma forma ejecutando el
test nuevo contra `head` y contra producción de `base`: desvío `True`, destino en
`_pendiente_checkin`, evento emitido y scratch también desviado. El diff no toca
`case_manager.es_copia_prestada` ni el cálculo de destino. La atribución a `MEJORAS #124`
queda confirmada.

No se encontraron otras fixtures que den de alta inadvertidamente una ruta canónica. Las
restantes apariciones están en las nuevas pruebas negativas o en la siembra manual y
declarada del estado heredado.

El quinto test pasa y, contra su docstring, sí discrimina su polaridad (H22-08).

## 4. Efectos no buscados y censo de escrituras

- El diff no modifica `checkout`, `checkin`, `sala_maquina` ni el mutex. El corte ampliado
  de 17 ficheros de pruebas —incluidos esos subsistemas y el censo— terminó con código 0 y
  solo los cuatro `xfail` de `#124`.
- El censo estático encontró tres escritores públicos del registro: `alta`, `baja` y
  `revalidar`, todos sobre `_escribir`. El diff protegió `alta`, pero no `revalidar`
  (H22-02). En el código productivo solo `adoptar` llama hoy a `alta`; no hay llamada
  productiva a `baja` o `revalidar`.
- `cmd_checkout` y `cmd_checkin` tampoco llaman hoy al registro. Es una discrepancia
  preexistente respecto del flujo normativo, presente también en `base`; no se atribuye a
  este diff, pero limita su efecto productivo a adopción y lecturas.
- `sala_maquina` construye el registro concreto y sus candidatos pasan por `_leer`; el mutex
  no construye un registro, aunque vuelve a clasificar su raíz con lógica propia.

## 5. Condiciones nuevas

Se ejecutaron ambos valores de las guardas de `alta`, `verificar_adopcion` y filtrado; la
igualdad, el prefijo y el `False` final de las comparaciones léxica y física; y las dos
ramas de excepción mediante fallos inducidos. Por tanto, ninguna condición nueva es
semánticamente constante. La cobertura automatizada no coincide con esa alcanzabilidad:
las ramas y composiciones sin matador están enumeradas en H22-07.

## 6. Ejecución

- Foco nuevo/guard: código 0, `18 passed, 4 xfailed`.
- Corte registro/resolver/adopción/guard/mutex: `145 passed, 4 xfailed`.
- Corte ampliado con catálogo, checkout/checkin, sala de máquina y censos: código 0; cuatro
  `xfail` de `#124`.
- Suite completa de `head`: llegó al 100 %, con un único fallo en
  `test_mcp_wrappers.py::...expedientes_xl`. El mismo test aislado falla idénticamente en
  `base`: el test vacía `PATH` y el `.bat` intenta usar `ping`. No se atribuye al diff.
- Se usó siempre `-p no:randomly`, `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1` en las
  corridas propias y `--basetemp` relativo bajo `C:/tmp/r22b`.

## Lo que NO pude verificar

- La identidad UNC frente a letra de unidad: `\\localhost\C$` no era accesible y `net use`
  no mostró una unidad de red mapeada.
- Directorios NTFS sensibles a mayúsculas: `fsutil` denegó habilitar el atributo. Solo se
  verificó el comportamiento ordinario insensible a caja.
- Un disparador natural de `OSError`/`RuntimeError` de `Path.resolve()` sobre una ruta de
  workspace legítima; H22-04 ejecuta la propagación completa con excepción inducida.
- Comportamiento dependiente del orden o de semillas: este entorno no tiene
  `pytest-randomly`.
- Tests lentos, Ollama y el fixture PII SaRS1. La suite completa limpia queda **SIN
  VERIFICAR** por el fallo ambiental preexistente del wrapper, aunque los cortes relevantes
  terminaron verdes.
- Consumidores externos al repositorio que puedan inyectar un registro alternativo en el
  resolver.

## `sha256` agregado de `head` al cerrar

`206bfab64396a2652af6e0f8b8645a519e1476e7cdc1dff70f00b0695d4c0574`

Coincide con el hash de apertura: las copias objeto no cambiaron.

----- VEREDICTO.md (fichero aparte, pedido asi en el mandato) -----

NO-SHIP
El canon aún puede entrar por rutas Windows equivalentes y por `revalidar`, de modo que la invariante de `MEJORAS #136` no queda cerrada.
<!-- informe-literal:fin:v9pt -->

## 2. Evidencia verificada por el adjudicador

Reproducido por mí contra la fuente **antes** de remediar, no leído del informe:

```
H22-01  extendida \\?\...\CASOS\Caso  : False   (normal: True, samefile: True)
H22-06  CASOS_ROOT=C:\ , hijo C:\tmp     : False   (deberia ser True)
H22-02  revalidar escribe el canon        : True    (segundo escritor sin guarda)
H22-04  'Uno' sigue en el JSON crudo      : False   ← PERDIDA DE DATOS
```

- **H22-02** verificado además por lectura: `revalidar` hace
  `dataclasses.replace(e, …, local_path=Path(local_path))` y llama a `_escribir` sin comprobar nada
  (`core/casos/workspace_registry.py`, antes del arreglo). Mi censo de «cuatro puertas» lo omitió.
- **H22-04 es un defecto que introduje yo al arreglar**, no un defecto de `main`: filtrar al leer con
  un booleano que falla cerrado ocultaba también lo *indeterminado*, y `alta` reescribía desde la
  vista filtrada.
- **H22-08 va en la dirección contraria a la habitual**: el revisor demostró que
  `test_un_registro_ilegible_NO_desactiva_el_guard` **sí** discrimina su polaridad, mutando el
  `except` de `es_copia_prestada`. Yo había escrito en su docstring que no podía distinguir. No
  inflé lo que el test probaba: lo **rebajé**, y una nota de humildad falsa habría retirado de la
  vista la única prueba de esa polaridad.
- **Matiz sobre H22-07**: sus cuatro mutantes finos supervivientes son ciertos y se cerraron, pero
  su afirmación de que los cinco declarados «sí murieron de forma focal» resultó **optimista** —
  al rehacer la mutación sobre el diff remediado, tres de la frontera de escritura sobrevivían
  porque las capas se tapaban entre sí. Eso no lo vio la ronda; lo vio la mutación posterior.
