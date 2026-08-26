---
tipo: plan
objeto: "Apertura V1 — Plan 3A-bis: la fila #5 del write-set (la ficha sigue a los bytes)"
estado_remediacion: pendiente
creado: 2026-08-26
---

# Apertura V1 — Plan 3A-bis: la ficha sigue a los bytes, y la clase de la que tres registradores son ejemplo (rev. 1)

> **Predecesores.** [Plan 3A](2026-08-26-apertura-v1-plan3-write-set.md) (PR #251, `6bd78ad`),
> cuyo **Task 6 quedó PARCIAL** precisamente por esta fila. La spec canónica es
> [`2026-08-15-orquestador-apertura-expediente-design.md`](../specs/2026-08-15-orquestador-apertura-expediente-design.md),
> §25 fila **#5**.
>
> **Por qué es una pieza propia y no un remate de 3A.** El Task 6 de 3A dejó siete filas de
> protocolo sin migrar y declaró que *«la que explica el resto es #5»*, porque su remedio es un
> cambio de **comportamiento** y no de destino. 3A ya consumió sus dos rondas (R14 diseño, R15
> diff). Código nuevo exige ronda nueva: este documento es el objeto de la **R16** (diseño) y su
> diff lo será de la **R17**.
>
> **Presupuesto de rondas: 2.** La pieza decide **quién puede escribir sobre qué copia** y puede
> **corromper la ficha canónica de un expediente de cliente** — las dos condiciones del cuadro de
> `CLAUDE.md`, cada una por separado suficiente.

---

## 1. Lo que se midió, antes de decidir nada

Sonda ejecutada el 2026-08-26 contra un `CASOS_ROOT` temporal, con el intérprete del venv del
repo. No es un test: es una medición previa al diseño, y su resultado **corrigió la recomendación
que el 71º cierre dejó escrita** (que hablaba de una sola pérdida, la de la carrera).

| Qué se observó | Resultado | ¿Necesita carrera? |
|---|---|---|
| Lock adquirido por una tercera máquina entre la lectura y la escritura | queda el lock **de la máquina anterior** — pisado | **sí** |
| Clave de frontmatter que no es campo de `CaseMeta` | `sobrevive?` → `None` | **no** |
| Cuerpo del `_caso.md` (nota escrita a mano) | **borrada** | **no** |

El mecanismo: `register_drive_ev` **no muta** el fichero, lo **reconstruye** llamando a
`_write_case_index`, que es el *constructor* del alta. Reconstruye el cuerpo desde una plantilla
y el frontmatter desde un conjunto fijo de claves, rellenando con `CaseMeta` los defaults de todo
lo que no venía en la foto.

**Y el sitio no es uno, son tres**, con la misma forma:

| Función | Línea | Lee de | Escribe en |
|---|---|---|---|
| `register_expediente` | `core/case_manager.py:215` | `buscar(case_id)` | `caso_path(case_id)` |
| `register_drive_ev` | `core/case_manager.py:515` | `buscar(case_id)` | `caso_path(case_id)` |
| `cache_drive_folder_info` | `core/case_manager.py:629` | `buscar(case_id)` | `caso_path(case_id)` |

Los tres **leen de una ruta y escriben en otra**: `buscar` resuelve por catálogo y puede devolver
una copia local; `caso_path` compone la ruta canónica. Que hoy coincidan en el uso normal no es
una garantía, es una coincidencia — y es la clase que la Fase 1 dual cerró en otros veintitantos
sitios.

### 1.1. La creencia falsa estaba escrita, y por eso se copió tres veces

`core/case_manager.py:199-203` afirma literalmente que el patrón «known fields» se usa

> *«así se preservan TODOS los campos de `CaseMeta` —incluidos los del lock de checkout
> (`estado_repositorio`, `checkout_*`)— y no se resetean al reescribir el índice de un caso que
> pudiera estar prestado»*

…y **nombra `register_drive_ev` como modelo**. La afirmación es falsa en el punto exacto que
pretende cubrir: conservar los **nombres** de los campos de una foto no conserva el **estado**,
conserva la foto. El comentario no es un adorno del defecto, es su **vector de propagación**.

### 1.2. La clase ya está cerrada en este repo, en otro sitio

El **CP11 del checkin** (`scripts/repository_cli.py:889-893`) relee el `_caso.md` pegado al push,
y su comentario dice por qué:

> *«Adelantar la lectura ensanchaba la ventana en la que otro escritor puede tocar el frontmatter
> canónico y este push lo pisaría desde una foto vieja (R9/H9-03, que era una regresión
> introducida por el primer intento de arreglo).»*

Mismo defecto, encontrado por una ronda adversarial, remediado una vez. Los tres registradores se
quedaron fuera porque **el remedio se aplicó al sitio del informe y no a la propiedad**. Es la
misma reincidencia que R14 y R15 castigaron en 3A, y ésta es su cuarta aparición.

---

## 2. La clase, contestada con la clase y no con el sitio

> **C1 — Ninguna escritura sobre `_caso.md` nace de una foto del fichero tomada antes de la
> escritura.** Toda mutación lee y escribe dentro de la misma operación y toca **solo sus propias
> claves**. Reconstruir el fichero desde un snapshot es pisar a quien escribió en medio.

La primitiva que ya cumple C1 existe y está en producción desde D10: `_atomic_write_caso_md`, que
lee, aplica un `mutator(fm)` y cierra con `os.replace`. La usan las cinco transiciones del lock y
el `ensure_case` de caso existente. **Los tres registradores son las únicas mutaciones del
fichero que no la usan.**

Regla operativa que se deriva de C1, y que es lo que un guard puede comprobar:

> `_write_case_index` es un **constructor**, no un mutador. Su único llamador legítimo es el alta.

La fila #5 pregunta además por una **segunda** clase, ortogonal a C1:

> **C2 — Un artefacto de protocolo que describe unos bytes vive donde viven esos bytes.**

La fila **#7** (`.pulled`) ya cumple C2 desde 3A: el marcador se escribe en `target_dir`, que es
el destino efectivo que devuelve el guard. La fila **#5** —el sello de la ficha— no la cumple: se
estampa en el canon aunque los bytes se hayan desviado a la bandeja. **Mitad dentro, mitad
fuera.**

Y una tercera, que aparece al preguntar *dónde* puede llegar un sello:

> **C3 — Un sello sobre `_caso.md` solo se estampa donde ese fichero ES el canon.** En cualquier
> otro caso no se pierde en silencio: queda **declarado como pendiente**, viaja al llamador y se
> avisa por pantalla.

C3 cubre de una vez los **tres** estados posibles, y no solo el que la fila #5 nombra:

| Estado | Hoy | Con C3 |
|---|---|---|
| `disponible`, sobre el canon | estampa | **estampa** |
| `prestado`/`conflicto` (otra máquina lo tiene) | estampa el canon **durante un checkout** | aplaza + aviso |
| copia local prestada (esta máquina lo tiene sacado) | estampa el **local**, que `MERGE_EXCLUSIONS` no devuelve nunca al Drive → **se pierde en silencio** | aplaza + aviso |

El tercer caso no estaba en la fila #5 ni en mi recomendación del 71º. Sale de contestar la
pregunta como clase: *¿dónde puede llegar este sello?* — y la respuesta es que en dos de los tres
estados no llega al canon, no en uno.

---

## 3. La decisión de la fila #5 (D5)

> **D5 — La ficha acompaña a los bytes.** Cuando el guard desvía el pull a la bandeja, el sello de
> los ids de Drive **no se estampa** en la ficha canónica. Queda declarado como pendiente, con
> aviso en pantalla, y se aplica en el siguiente pull cuando el caso vuelva a estar disponible.
>
> **Autorizada por Nikolai el 2026-08-26**, incluido el aviso en pantalla, sobre la medición del
> §1 y el coste operativo del §6.

Las otras dos salidas se caen por medición, no por preferencia:

- **Estampar igual (statu quo)** es mutar el canon durante un checkout, que es exactamente lo que
  la arquitectura dual del expediente activo existe para impedir. Y con el §1 delante, además
  pisa el lock de la máquina que lo tiene.
- **Abortar el pull** contradice al propio guard de 3A, que para esta misma operación ya decidió
  **desviar** los bytes en vez de rechazarlos. La fila #5 es esa misma escritura, exenta por
  omisión; darle una política opuesta a la de sus propios bytes es inventar una tercera regla
  donde ya hay una.

### 3.1. Por qué «aplazar» necesitaba una tercera pieza

«El sello espera» solo vale si alguien lo pone después, y **hoy no lo pondría nadie**:

```
if marker.exists() and not force:
    ...
    if prev_returncode == 0:
        ...
        return DriveIntakeResult(..., skipped=True)     # ← vuelve AQUÍ
...
if returncode == 0:
    register_drive_ev(case_id, team_id, folder_id)      # ← nunca se alcanza
```

El atajo de idempotencia vuelve **antes** de la línea que sella. Así que tras el checkin ningún
pull posterior repara la ficha: se lo salta el atajo.

**Es un defecto vivo hoy, sin relación con los préstamos:** si el primer sellado falla o no
ocurre por cualquier motivo, nada lo repone jamás. Lo encontré preguntando *quién consume el
aplazamiento*, que es la lección de las piezas construidas que nadie encadena.

---

## 4. Las tres piezas

### Pieza A — los tres registradores mutan, no reconstruyen (C1)

Los tres pasan a `_atomic_write_caso_md` con un mutator que toca **solo sus claves**:

| Función | Claves que toca |
|---|---|
| `register_expediente` | `sudespacho_expedientes` (nivel superior y `meta`) |
| `register_drive_ev` | `meta.drive_ev_team_id`, `meta.drive_ev_folder_id` |
| `cache_drive_folder_info` | `meta.drive_ev_folder_name`, `meta.drive_ev_drive_id` |

Cuatro detalles que la migración **no** puede perder, y que son los que la hacen no mecánica:

1. **El no-op cuando el caso no existe.** Los tres devuelven en silencio si `buscar` da `None` o
   si falta `_caso.md`; `_atomic_write_caso_md` **lanza** (`localizar` con el error del §10, y
   `FileNotFoundError`). El contrato público de los tres se conserva: la comprobación previa se
   mantiene y se documenta como parte del contrato, no como un resto.
2. **La idempotencia.** Sigue siendo del llamador, no del mutator: si los valores ya coinciden, no
   se abre la escritura. Esto además evita reabrir la ventana de escritura sin necesidad.
3. **`meta.actualizado_en`.** Hoy lo estampan los tres; `_atomic_write_caso_md` ya lo hace por su
   cuenta cuando `meta` es un dict. No se estampa dos veces ni se pierde.
4. **La ruta única.** Al usar la primitiva desaparece el par lee-de-`buscar` / escribe-en-
   `caso_path`: `_atomic_write_caso_md` resuelve **una** vez con `localizar`.

**Lo que A pierde a propósito, y se declara:** el **cuerpo** del `_caso.md` deja de refrescarse.
Hoy la línea legible `- Drive E&V team: … / folder: …` la reescribe el constructor; a partir de
A puede quedar ausente aunque los ids sí estén en el frontmatter.

Es una regresión de **una línea de cortesía** en un fichero cuya parte canónica es el
frontmatter, y la alternativa es seguir borrando notas del abogado. Además **no introduce una
clase nueva de obsolescencia**: `estado`, `cliente`, `cuantía`, `tipo_caso`, `dirección` y
`ciudad` ya se mutan por `_atomic_write_caso_md` sin refrescar el cuerpo, así que A **alinea** los
tres registradores con lo que hace toda mutación del fichero desde D10, en vez de dejarlos como
la excepción. El sitio donde el dato se hace visible pasa a ser la salida del pull (pieza C-bis).

### Pieza B — el sello solo se estampa donde el fichero es el canon (C2 + C3)

`pull_drive_ev` deja de tirar la decisión del guard. Hoy hace:

```python
target_dir = dir_intake(case_id, f"00_Input/{_DRIVE_EV_INPUT_SUBDIR}", "drive_ev")
```

`dir_intake` llama al guard, usa `decision.desviar` para componer el path y **descarta la
decisión**. B la conserva: el pull consulta `guard_escritura` una vez, compone el destino con la
misma regla que `dir_intake` (que es literalmente dos líneas) y se queda con la decisión.

Regla de sellado, que es C3 escrita como código:

```
sellar  ⟺  el caso está disponible en el canon
        ⟺  NOT decision.desviar  AND  NOT es_copia_prestada(case_id)
```

Las dos condiciones son necesarias y **ninguna implica la otra**: sobre una copia local prestada
el guard devuelve `desviar=False` a propósito (la bandeja no aplica, `MEJORAS #96`), así que
mirar solo `desviar` deja el tercer caso del §2 abierto — y es el que hoy pierde el dato en
silencio.

**El evento no se duplica.** `guard_escritura` emite `pendiente_checkin` cuando desvía. B no emite
un segundo evento por el sello: el desvío ya está registrado y el sello aplazado es una
consecuencia del mismo hecho, no un hecho nuevo. Lo que sí se emite es el `pull_drive_ev` que ya
emite el llamador, con el aplazamiento en sus `details`.

### Pieza C — el aplazamiento tiene consumidor

Dos mitades, y la segunda es la que hace honesta a la primera.

**C-1: el sello se reconcilia también en el camino del *skip*.** El sellado sale del `if
returncode == 0` final y pasa a ser un paso propio que corre en los dos caminos:

- pull ejecutado con `returncode == 0` → sellar (si B lo permite);
- pull saltado por marcador con `prev_returncode == 0` → **sellar igual** (si B lo permite).

Lo que **no** cambia: el skip con `prev_returncode != 0` sigue reintentando el pull, que es el
comportamiento que cierra el modo «pull eternamente bloqueado».

**C-2: el aplazamiento viaja al llamador y sale por pantalla.** `DriveIntakeResult` gana dos
campos:

```python
registro_aplazado: bool = False
registro_aplazado_motivo: str | None = None   # vocabulario cerrado, ver abajo
```

Core **no imprime**. Los tres llamadores de `pull_drive_ev` avisan:
`scripts/abrir_caso.py:144`, `streamlit_app.py:511` y `streamlit_app.py:2398`.

Vocabulario cerrado del motivo, para que el aviso no sea prosa libre y el test pueda fijarlo:

| Motivo | Cuándo |
|---|---|
| `caso_prestado` | el guard desvió: otra máquina lo tiene sacado |
| `copia_local_prestada` | esta máquina lo tiene sacado; `_caso.md` no vuelve al Drive |

**C-bis: el cuarto sitio que sella, fuera del pull.** `streamlit_app.py:2172` llama a
`register_drive_ev` **directamente**, sin pull. Queda sujeto a la misma regla de C3: si el caso no
está disponible en el canon, no sella y avisa. Sin esto, B cierra la puerta del pull y deja
abierta la de al lado — que es la forma exacta del defecto que este plan viene a arreglar.

---

## 5. Las fronteras — una por mutante

Un mutante por frontera. Un mutante que mate **más** tests de los previstos está mal apuntado, no
bien elegido; el arnés aborta si el ancla no casa y restaura en binario.

| # | Frontera | El mutante |
|---|---|---|
| **F1** | los tres registradores conservan una clave de frontmatter ajena a `CaseMeta` | volver a `_write_case_index` en uno de ellos |
| **F2** | los tres conservan el cuerpo escrito a mano | ídem, comprobando el cuerpo |
| **F3** | ninguno lee de una ruta y escribe en otra | reintroducir `caso_path` como destino de la escritura |
| **F4** | un lock escrito **entre** la lectura y la escritura del sello no se pisa | ensanchar la ventana a lectura-anticipada |
| **F5** | con el guard desviando, **no** se sella el canon | forzar `sellar = True` |
| **F6** | sobre una copia local prestada, **no** se sella | quitar el `es_copia_prestada` de la conjunción |
| **F7** | con el caso disponible, **sí** se sella | forzar `sellar = False` |
| **F8** | el aplazamiento llega al resultado con su motivo del vocabulario cerrado | devolver `registro_aplazado=False` siempre |
| **F9** | el motivo distingue `caso_prestado` de `copia_local_prestada` | fijar un motivo constante |
| **F10** | el *skip* por marcador con `rc == 0` reconcilia la ficha | devolver antes del sellado |
| **F11** | el *skip* por marcador con `rc != 0` sigue reintentando | tratar todo marcador como éxito |
| **F12** | el aviso sale en el entrypoint cuando hay aplazamiento | suprimir la impresión |
| **F13** | la idempotencia del sello se conserva (mismos ids → no reescribe) | quitar la comparación previa |
| **F14** | el no-op de los tres cuando el caso o su `_caso.md` no existen | quitar la comprobación previa y dejar que lance |
| **F15** | `streamlit_app.py:2172` obedece C3 igual que el pull | dejar el sellado incondicional en ese sitio |

**Guard permanente (F3-bis):** `_write_case_index` tiene **un** llamador de producción, el alta.
Guard AST sin números de línea, con su propia prueba de mutación, en la línea del trinquete del
Task 7 de 3A. Sin él, C1 se reabre la próxima vez que alguien necesite escribir dos claves.

---

## Global Constraints

- **No se toca `case_mutex.py`** (cuatro rondas, 17 mutantes) ni `mutex_sesion.py` (R14/R15).
- **No se toca `_atomic_write_caso_md`.** Se usa. Si hiciera falta cambiarla, es señal de que el
  mutator está haciendo demasiado.
- **El reloj se pasa explícito donde importe.** `now_iso()` es **naïve** (43 usos frente a 5 de
  `now_iso_utc`); ningún camino nuevo compara instantes, y si lo hiciera pasaría `now_iso_utc`.
- **Core no imprime.** El aviso vive en los entrypoints.
- **Suite con dos semillas** (777 y 31337) antes de declarar verde.
- **Rama + PR.** `main` protegida; `pytest` no corre en CI.

## File Structure

```
core/case_manager.py          los tres registradores → _atomic_write_caso_md (A)
core/intake_drive.py          decisión del guard conservada; sellado en un paso propio (B, C-1)
                              DriveIntakeResult + registro_aplazado(+motivo) (C-2)
scripts/abrir_caso.py         aviso en pantalla (C-2)
streamlit_app.py              aviso en los dos pull + C3 en el sellado directo (C-2, C-bis)
tests/test_caso_md_mutacion_atomica.py     nuevo — A, F1-F4, F13, F14
tests/test_intake_drive_sello_ficha.py     nuevo — B y C, F5-F12
tests/test_guard_write_case_index.py       nuevo — el trinquete de F3-bis
```

## Task 1: la sonda del §1, convertida en test que falla

- [ ] Los tres hechos medidos, como tests rojos **antes** de tocar producción: clave ajena,
      cuerpo, y la carrera del lock con la escritura instrumentada.
- [ ] La carrera se induce **sin `sleep`**: se envuelve la escritura para que el lock ajeno se
      adquiera entre la lectura y la escritura. Un test de carrera con temporización es un test
      que pasa por azar.

## Task 2: Pieza A — los tres mutan

- [ ] Migrar los tres a `_atomic_write_caso_md`, preservando los cuatro detalles del §4-A.
- [ ] Borrar el comentario falso de `:199-203` y **sustituirlo** por la regla C1. Suprimir prosa
      normativa sin sustituto es perder la regla.
- [ ] F1-F4, F13, F14 con su mutante.

## Task 3: el trinquete de `_write_case_index`

- [ ] Guard AST: un solo llamador de producción. Prueba de mutación del guard.

## Task 4: Pieza B — la regla de sellado

- [ ] `pull_drive_ev` conserva la decisión del guard; sellado ⟺ disponible en el canon.
- [ ] F5-F7 con su mutante. **Verificar que el evento `pendiente_checkin` no se duplica.**

## Task 5: Pieza C — reconciliación, resultado y aviso

- [ ] C-1 (sellado en el camino del skip), C-2 (campos + aviso en los tres llamadores),
      C-bis (`streamlit_app.py:2172`).
- [ ] F8-F12, F15 con su mutante.

## Task 6: E2E de los dos planos

- [ ] Por cada uno de los tres estados del §2, doblar **los dos** destinos (canon y bandeja) y
      comprobar **cuál** cambió, y que el otro no. El censo no es la prueba de cierre.

## Task 7: censo y cierre

- [ ] Recontar el censo (b) y **declarar** su variación, no absorberla. El sellado sale de un
      sitio y entra en otro: si el total no se mueve, decir por qué.
- [ ] Corregir la cifra rancia del plan de 3A: su §«Por qué el Task 6 es PARCIAL» dice «las 93
      escrituras del censo» y el censo medido es **83**. El 93 es el número que el detector
      inflaba contando `str.replace`.

## Criterio de salida

1. Los tres registradores conservan cuerpo y claves ajenas, medido sobre los tres.
2. El lock de otra máquina no se pisa en la carrera del §1.
3. El sello no llega al canon en ninguno de los dos estados en que el fichero no es el canon.
4. Un pull que hace *skip* por marcador reconcilia la ficha.
5. El aplazamiento sale por pantalla en los tres llamadores.
6. Quince fronteras, quince mutantes, cada uno muerto por la suya.
7. Suite verde con dos semillas, con la variación del conteo explicada.

## Lo que este plan deliberadamente NO hace

- **No migra las otras seis filas de protocolo** (#4, #7, #10, #11, #12, #13) que el Task 6 de 3A
  dejó fuera. La decisión que las bloqueaba era la #5 y aquí se toma, pero su migración es diff
  propio y ronda propia.
- **No refresca el cuerpo del `_caso.md`.** Declarado en el §4-A con su motivo.
- **No integra el sello aplazado en el checkin.** CP10 mueve ficheros de la bandeja al árbol; no
  escribe el frontmatter, y darle esa competencia es cambiar el checkin, que es la pieza con más
  radio de daño del repo. El consumidor del aplazamiento es el siguiente pull (C-1).
- **No toca 3B ni 3C**, que tienen sus propios documentos y sus propias rondas.

## Lo que sigue SIN VERIFICAR, y se declara

- **La ventana de `_atomic_write_caso_md` no es cero.** Es un read-modify-write con `os.replace`,
  «sin lock, sin versionado» por su propio docstring. A la estrecha al mínimo que el resto del
  sistema ya acepta —el mismo que usan las transiciones del lock— pero **no la elimina**. Cerrarla
  del todo exige versionado optimista sobre el fichero, que no está en este alcance.
- **El mutex de D2 no protege entre máquinas.** Su ámbito es una máquina (decisión D2). Lo que
  protege el canon frente a otra máquina es el protocolo de checkout, no el mutex. Nada de este
  plan cambia eso, y conviene no leer «bajo mutex» como «a salvo de la otra máquina».
- **Si nadie vuelve a lanzar un pull, la ficha queda sin sellar.** C-1 reconcilia en el siguiente
  pull; no hay tarea que lo haga sola. El aviso en pantalla es lo que hace visible esa deuda, y es
  la razón por la que Nikolai lo eligió.
- **El coste operativo del aplazamiento está medido en un solo consumidor.**
  `get_drive_ev_ids` tiene **un** llamador (`streamlit_app.py:1286`, el flujo de compartir). Si
  apareciera un segundo consumidor, el coste del aplazamiento cambia y esta cuenta caduca.
- **La reacción del mutex a un salto real de NTP**, heredada de 3A y del plan del mutex.
- **Las seis remediaciones de R13 no tienen ronda propia** y 3A las usa; este plan las usa por
  transitividad, sin revisarlas.
