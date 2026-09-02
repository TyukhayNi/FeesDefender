---
tipo: plan
objeto: "MEJORAS #124 — quién contesta «¿cuál es la copia de trabajo?» en el camino de escritura"
estado_remediacion: pendiente
creado: 2026-09-02
---

# MEJORAS #124 — la copia de trabajo la contesta el resolver, y el veredicto viaja con su raíz (rev. 1)

> ## ⛔ ESTADO: rev. 1 `NO-EJECUTABLE`. NO se construye con este diseño.
>
> **R21 (diseño) devolvió `NO-EJECUTABLE`: 8 hallazgos, 8 confirmados, 0 refutados, 4 críticos.**
> Adjudicación en el **§8**; acta en
> `docs/superpowers/specs/2026-09-02-mejoras-124-r21-adversarial-review.md`.
>
> **Lo que sobrevive:** el diagnóstico del §1.1-1.2 (reproducido por el revisor) y la **decisión
> D124** — que el veredicto y el destino salgan de una sola resolución. Lo que la ronda tumbó es el
> diseño de su implementación.
>
> **Lo que NO sobrevive, y hay que leerlo antes que nada:** la frase del §1.3 «hoy eso no ocurre
> porque la guarda es inerte» es **FALSA**. Hay una vía productiva —`repository_cli adoptar` sobre
> la ruta del canon— que la vuelve verdadera y abre el agujero **hoy, en `main`**. Es un defecto
> vivo, no del plan: `MEJORAS #136`. Detalle y sonda en el **§8.1**.
>
> **Pendiente: rev. 2**, con los cinco puntos del §8.4 resueltos y `MEJORAS #136` cerrada antes que
> ninguno. Su cobertura de revisión será **ausente** hasta que alguien la mire.
>
> **Presupuesto de rondas: 2** (`CLAUDE.md` §«Cuántas rondas»). La pieza decide **quién puede
> escribir sobre qué copia** — la primera condición del cuadro, y por sí sola suficiente. R21 sobre
> este diseño, R22 sobre el diff. **Sin tercera** sin autorización expresa de Nikolai.

> **Por qué existe.** `MEJORAS #124`, abierta el 2026-08-26 por el hallazgo **H16-01** de la R16
> (revisión del diseño del Plan 3A-bis). Es el **gate declarado** de la rev. 2 del Plan 3A-bis y del
> Plan 3B: las reglas de sellado de los dos cuelgan de la respuesta a «¿cuál es la copia de
> trabajo?», y hoy la contesta una guarda inerte. Fila **#15** de `PLAN.md`.
>
> **Predecesores.** [Plan 3A](2026-08-26-apertura-v1-plan3-write-set.md) (PR #251), que construyó la
> costura `core/casos/escritura.py`; la **Fase 1** de la arquitectura dual (PR #236), que construyó
> el `CaseWorkspaceResolver`; y `MEJORAS #96`, que es la intención que esta pieza nunca cumplió.

---

## 1. Lo que se midió, hoy, antes de diseñar nada

Todas las sondas de este §1 son del **2026-09-02**, sobre `origin/main` en `e24b9c6`, con el
intérprete del venv del repo. No son tests: son mediciones previas al diseño.

### 1.1. La guarda sigue inerte (reproducción de H16-01)

Sonda con un `CASOS_ROOT` temporal y una copia local **fuera** del catálogo, registrada como manda
el contrato:

```
buscar()          : <TMP>\CASOS\BaXX1 - Sonda - (W-SONDAEC) - NEGATIVA_OFERTA
copia registrada  : <TMP>\Desktop\BaXX1 - Sonda - (W-SONDAEC) - NEGATIVA_OFERTA
es_copia_prestada : False
```

Los dos hechos que se tocan siguen en pie, verificados sobre el código vigente:

- `case_locator.buscar()` mira **solo** bajo `CASOS_ROOT` — plano, por ciudad, por ciudad de
  reserva (`core/casos/case_locator.py:121-143`).
- El registro **solo** contiene rutas fuera del catálogo: `WorkspaceUnderCatalogRoot`
  (`core/casos/workspace_model.py:224-225`), aplicado en `resolver_por_ruta`.

### 1.2. Los cuatro consumidores del veredicto, y de dónde sacan el destino

Esto es lo que **no** estaba medido cuando se abrió `MEJORAS #124`, y es lo que cambia el diseño.

| Consumidor | Llama al guard | Y la base la calcula con | ⇒ raíz efectiva |
|---|---|---|---|
| `case_manager.dir_intake` (`:912-916`) | sí | `caso_path(case_id)` | **canon** |
| `casos/escritura.deposito` (`:210-213`) | sí | `CaseCatalog().localizar(ref)` (`:119-131`) | **canon** |
| `intake_manual` (`:255-270`) | sí | `case_locator.localizar(case_id)` | **canon** |
| `sync_sudespacho` (`:1494`) | sí | `case_root`, del canon | **canon** |

**Los cuatro. Sin excepción.** El veredicto lo da una resolución y el destino lo da otra, y la
segunda no puede ver una copia local.

### 1.3. La medición que convierte el arreglo ingenuo en una regresión

**No se dedujo: se ejecutó.** Caso con el canon en estado `prestado` a otra persona; se sustituye
`es_copia_prestada` por la constante `True` —que es exactamente lo que sería «arreglar la
comparación»— y se pregunta a `dir_intake` dónde caerían los bytes:

```
estado canon                        : prestado
dir_intake (hoy, guarda inerte)     : <CASO>\_pendiente_checkin\email\00_Input\03_Email
dir_intake (guarda «arreglada»)     : <CASO>\00_Input\03_Email        ← el CANON, sin desviar
```

> ### ❌ CORRECCIÓN (R21/H21-01): el párrafo que sigue es FALSO
>
> Se conserva tal como lo revisó R21, tachado y no borrado, porque el §8.1 lo cita. **La guarda no
> es inerte por todos los caminos:** `repository_cli adoptar` sobre la ruta del canon la vuelve
> verdadera, y entonces el agujero está abierto **hoy en `main`** — reproducido con sonda propia.
> `MEJORAS #136`.

~~Hoy el desvío ocurre **porque la guarda es inerte**. O sea: la avería que H16-01 denuncia es lo
único que hoy impide una escritura sin desvío sobre un expediente que otra máquina tiene tomado.~~

**Arreglar la comparación, en solitario, no es un arreglo: abre la puerta que la avería mantenía
cerrada.** Ésta es la razón por la que `MEJORAS #124` acierta al decir que la pregunta no es «cómo
se compara» sino **quién contesta**.

### 1.4. La pieza que sí sabe la respuesta, y quién la usa

`CaseWorkspaceResolver` contesta la pregunta entera (`core/casos/workspace_resolver.py`) y entrega
`CaseWorkspace.working_root`, que es la raíz real. **Lo consulta un solo entrypoint**:
`scripts/sala_maquina.py:363` (`_resolver_workspace`, Task 9 de la Fase 1). Ningún camino del guard
lo consulta.

Y los tres ayudantes que hacen falta para construirlo viven en `scripts/`, dos de ellos
**duplicados literales**: `_identidad_actor` y `_registro_de_workspaces` en `sala_maquina.py:274-286`
y `repository_cli.py:1216-1227` (comparados: idénticos), y `_drive_accesible` solo en
`sala_maquina.py:288-325`. Una pieza de `core/` no puede importarlos de `scripts/`.

### 1.5. Nueve tests verdes defienden el defecto

`tests/test_guard_copia_prestada.py:81-87` da de alta `local_path=caso_path(case_id)` —**el
canon**— llamando a `registro.alta` directamente, **sin pasar por el resolver que lo prohíbe**. La
fixture fabrica el estado que producción tiene prohibido, y en ese estado la rama sí funciona.

---

## 2. La frontera de la que todo esto es ejemplo

Antes de remediar, la pregunta obligatoria de `CLAUDE.md`: **¿de qué frontera es esto un ejemplo?**

> **El veredicto sobre si una escritura procede y el destino al que procede salen de dos
> resoluciones distintas, y solo una de las dos puede ver una copia local.**

Los ejemplos conocidos de esa frontera, que se cierran o se declaran **juntos**:

| # | Ejemplo | Dónde |
|---|---|---|
| E1 | `es_copia_prestada` compara canon contra un conjunto que nunca contiene canon | `case_manager.py:803-849` |
| E2 | `deposito(ref, …)` no transporta `working_root` (**H18-01**) | `casos/escritura.py:119-131` |
| E3 | `dir_intake` calcula `base` con `caso_path` | `case_manager.py:912` |
| E4 | `intake_manual` y `sync_sudespacho`, cada uno por su vía | §1.2 |

Cerrar E1 sin cerrar E2-E4 es exactamente lo que el §1.3 midió. **La unidad de remedio es la
frontera, no E1.**

---

## 3. La decisión

Las dos opciones que `MEJORAS #124` dejó enunciadas y sin elegir:

1. `guard_escritura` recibe (o resuelve) un `CaseWorkspace` y pregunta por `working_root`.
2. `es_copia_prestada` deja de existir y su pregunta se contesta en el resolver.

**Se toman las dos, porque son la misma con distinto radio y por separado ninguna cierra la
frontera.** Lo que se construye:

> **D124. Una sola resolución entrega el veredicto Y la raíz, en el mismo valor. No existe API que
> dé lo uno sin lo otro.**

Es el mismo principio que 3A ya aplicó un piso más abajo y por escrito: *«no devuelve la raíz
canónica: si devuelve un `Path`, el llamador escribe donde quiera»* (`escritura.py`, decisión 1).
Aquí se aplica al piso de arriba, que es donde 3A no llegó.

### 3.1. La pieza

`core/casos/copia_trabajo.py`, con un solo valor público:

```python
@dataclass(frozen=True)
class Destino:
    raiz: Path                  # la raíz de trabajo REAL: canon o copia local
    es_canon: bool              # si es False, la bandeja no aplica (MEJORAS #96)
    modo: WorkspaceMode | None  # None = no hubo resolución utilizable (§3.3)
    procedencia: str            # "resolver" | "catalogo_legacy"
```

y una sola puerta: `resolver_destino(ref, *, drive_accesible, ahora, usuario, maquina) -> Destino`.
Los cuatro parámetros de contexto **se inyectan**, por la misma razón que el resolver los inyecta:
un `datetime.now()` por dentro hace irrepetible el resultado, y con él la auditoría de qué autorizó
una operación pasada.

### 3.2. Cómo se conecta al guard

Lo que importa es la propiedad contratada, no la firma: los cuatro consumidores **dejan de calcular
la base** y la reciben junto al veredicto.

- `es_canon == False` → no hay bandeja, y los bytes caen en `Destino.raiz`. Las dos mitades a la
  vez: es lo que `MEJORAS #96` quería y lo que E1 solo prometía.
- `es_canon == True` → reglas de desvío de hoy, sin cambio alguno.

### 3.3. Falla cerrado, y «cerrado» aquí significa «como hoy»

Cuando no hay resolución utilizable —registro ilegible, caso que el resolver bloquea, catálogo
mudo, `WorkspaceError` de cualquier clase— `resolver_destino` devuelve
`Destino(raiz=canon, es_canon=True, modo=None, procedencia="catalogo_legacy")`, y el guard se
comporta **exactamente como hoy**.

No es prudencia decorativa. El guard se consulta desde las vías de intake de `streamlit_app.py`,
que es la herramienta diaria de Paola y Ana: un `CaseLocked` propagado desde aquí convertiría un
desvío silencioso en un fallo duro de su pantalla. Por eso la resolución se pide con
**`diagnostico=True`** — los modos `BLOCKED_*` vuelven como valor y no como excepción, y caen por
esta rama.

**Consecuencia declarada, no escondida:** un checkout anterior al registro y sin adoptar sigue
desviando al canon. Es la misma no-cobertura que `es_copia_prestada` ya declaraba en su docstring,
y la vía de desbloqueo sigue siendo explícita (`core.casos.workspace_adopcion`, §15).

---

## 4. Las fronteras, una por mutante

`CLAUDE.md`: *«si el contrato enumera N fronteras, hacen falta N mutantes»*. Son **siete**.

| F | Frontera | Mutante que la mata |
|---|---|---|
| **F1** | El veredicto y la raíz salen de la MISMA resolución: no hay API que dé uno sin la otra | devolver `bool` en vez de `Destino` |
| **F2** | `es_canon=False` ⇒ **cero** desvío, y los bytes caen en `raiz` | forzar `desviar=True` con `es_canon=False` |
| **F3** | `es_canon=True` y canon `prestado`/`conflicto` ⇒ **siempre** desvío | invertir la condición ⇒ escritura sin desvío sobre canon prestado |
| **F4** | Sin resolución utilizable ⇒ canon + conducta de hoy, sin excepción propagada | dejar escapar `WorkspaceError` |
| **F5** | La llamada al resolver lleva `diagnostico=True` | quitarlo ⇒ `CaseLocked` sube a Streamlit |
| **F6** | `es_copia_prestada` **no existe**, y nadie puede reintroducir la pregunta por `buscar()` | reintroducir la función ⇒ guard AST rojo |
| **F7** | Los tres ayudantes viven **una vez**, en `core/casos/` | duplicar uno en `scripts/` ⇒ guard AST rojo |

**F3 es la frontera nueva de esta pieza**, y la que el §1.3 obliga a contratar: hoy la sostiene un
accidente —que E1 sea inerte— y no un contrato. Es la lección de
[la guarda inerte](../specs/2026-08-26-apertura-v1-plan3a-bis-r16-adversarial-review.md) leída al
revés: si una condición no puede ser verdadera, tampoco está probado lo que pasa cuando lo sea.

---

## 5. Los Tasks

**T1 — Ayudantes a `core/casos/contexto.py`.** Mover `_identidad_actor`,
`_registro_de_workspaces` y `_drive_accesible`; `sala_maquina.py` y `repository_cli.py` importan de
ahí. Guard AST contra la redefinición (**F7**). Sin cambio de conducta: se comprueba que los dos
duplicados son idénticos **antes** de mover, no después.

**T2 — `core/casos/copia_trabajo.py` y su `Destino`.** TDD. La matriz completa modo × estado del
canon, con los cinco modos del §5.2. Mutantes de **F1**, **F4** y **F5**.

**T3 — El guard consume `Destino`.** Mutantes de **F2** y **F3**. Los nueve tests de
`test_guard_copia_prestada.py` **se rehacen**: la fixture registra una copia **fuera** del
catálogo, que es el estado que producción sí produce. Es la condición de cierre de `MEJORAS #124`,
y es dura: *el arreglo no vale si los nueve siguen pasando con la fixture actual*.

**T4 — Los cuatro consumidores reciben la raíz.** `dir_intake`, `deposito` (cierra **H18-01**),
`intake_manual`, `sync_sudespacho`. Ninguno vuelve a calcular la base por su cuenta.

**T5 — `es_copia_prestada` desaparece**, con su guard AST (**F6**).

**T6 — E2E sobre los cuatro planos** que 3A exige: canon intacto, copia local escrita, bandeja
vacía, log junto a los bytes.

---

## 6. Criterios de salida

1. La sonda del §1.1, re-ejecutada, da `es_canon=False` sobre la copia registrada fuera del
   catálogo — **y los bytes caen ahí**, verificado por hash y no por la ruta devuelta.
2. La sonda del §1.3, re-ejecutada, sigue dando desvío a la bandeja sobre el canon prestado. Es el
   criterio que impide que este plan se convierta en la regresión que lo motivó.
3. Los siete mutantes del §4 mueren, **cada uno por su frontera**: el aserto nombra la suya y no
   las otras seis.
4. La fixture del §1.5 registra fuera del catálogo, y la rama muere sin el arreglo.
5. Suite verde con **dos semillas** (777 y 31337). Base de partida medida hoy: **3.695 tests, 0
   fallos, 0 errores, 83 skip** con la 777.
6. Cero cambio de conducta en las vías de `streamlit_app.py` sobre casos no prestados, verificado
   por test y no por lectura.

---

## 7. Lo que este plan NO hace, dicho aquí para que no se cuele

- **No migra las 83 escrituras del censo.** Eso es 3B/3C.
- **No toca `case_mutex.py`.** Cuatro rondas y 17 mutantes: editarlo es reabrirlas.
- **No decide la regla de sellado de 3A-bis.** Le entrega la respuesta que le faltaba; la regla la
  escribe la rev. 2 de aquel plan.
- **No arregla los siete defectos del frontal** (Fase 2 de la fila #3), aunque `MEJORAS #124`
  nombra esa fase como uno de sus dos disparadores posibles.

---

## 8. Adjudicación de la revisión adversarial (Codex, 2026-09-02) — NO-EJECUTABLE, pendiente

- **Objeto revisado:** el diseño de este plan, rev. 1, commit `f062639`
- **Ronda:** R21 (diseño, antes de escribir código)
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-02-mejoras-124-r21-adversarial-review.md`
- **Hallazgos:** 8 — 4 CRÍTICOS, 3 ALTOS, 1 BAJO; **8 confirmados, 0 refutados**
- **Remediado en:** rev. 2 de este plan (pendiente)

### 8.1. El hallazgo que cambia el problema, y no solo el plan

**H21-01. La adopción productiva registra EL CANON como copia local.** Lo reproduje con sonda
propia, y desmiente una frase de mi §1.3.

`verificar_adopcion` comprueba cinco cosas —que el directorio existe, que tiene
`MANIFEST_CHECKOUT.json`, que el W-code del nombre casa, que el canon lo da por `prestado` y que el
lock es mío— y **ninguna de ellas es «está fuera del catálogo»**
(`core/casos/workspace_adopcion.py:68-105`). `WorkspaceRegistry.alta` tampoco: solo rechaza reusar
la ruta de **otro** caso (`core/casos/workspace_registry.py:235-247`). Y el canon **sí** tiene
`MANIFEST_CHECKOUT.json` mientras está prestado — lo dice el docstring de `es_copia_prestada`, que
lo usó como argumento para descartar ese discriminante.

Sonda mía, con el canon prestado a mi propio usuario y máquina:

```
verificar_adopcion.ok  : True | checkout propio con manifest y nombre coherente
adoptar(CANON)         : ACEPTADO
es_copia_prestada      : True
dir_intake             : <CANON>\00_Input\03_Email      ← SIN desviar, con el canon PRESTADO
resolver .mode         : local_checkout
resolver .working_root : <CANON>
```

**Mi §1.3 dice «hoy eso no ocurre porque la guarda es inerte». Es falso.** La guarda es inerte por
el camino que yo sondeé; hay un camino productivo —`repository_cli adoptar`— que la vuelve
verdadera y abre exactamente el agujero que el §1.3 describía como hipotético. **No es un defecto
del diseño: es un defecto vivo de `main`,** y va a `docs/MEJORAS_FUTURAS.md` **#136** con su
medición.

**Y el error de método que lo escondió es mío y tiene nombre.** Cité
`workspace_model.py:224-225` como prueba de que «el registro solo contiene rutas fuera del
catálogo». Ahí solo está **declarada la clase de excepción**. El rechazo vive en
`workspace_resolver.py:150-152` y **no gobierna a `alta`**. Cité el nombre de la garantía en vez de
su cumplimiento — sexta aparición de *el nombre de una cosa no es la cosa*, y esta vez me costó el
crítico entero. Lo peor es que la mis-cita es de H21-08, severidad BAJO: **el hallazgo barato era
la puerta del caro**.

### 8.2. El mutante inerte que yo mismo escribí

**H21-06.** Bajo el diseño literal de mi §3.3, quitar `diagnostico=True` **no cambia nada
observable**: sin él, `CaseLocked` se lanza, el `except WorkspaceError` la captura y produce el
mismo fallback. El revisor lo midió:

```
F5 conflicto diagnostico_true= FALLBACK diagnostico_false= FALLBACK
```

O sea que **F5 no muere**, y el mutante que la mata no existe. Lo escribí en el mismo documento
cuyo §4 cita la regla de las guardas inertes. Cuarta aparición de la clase, y la primera **dentro
de la prueba de mutación que existe para cazarla**: no basta comprobar que una *guarda* puede tener
el otro valor; hay que comprobar que el *mutante* puede producir el otro resultado.

### 8.3. Los ocho, uno por uno

| # | Sev. | Veredicto | Qué se hace |
|---|---|---|---|
| **H21-01** la adopción registra el canon | CRÍTICO | **CONFIRMADO** (sonda propia, §8.1) | `MEJORAS #136` + la invariante se cierra **en la escritura del registro**, no solo en `resolver_por_ruta`. `es_canon` no puede derivarse del modo hasta entonces |
| **H21-02** `Destino` no transporta el veredicto | CRÍTICO | **CONFIRMADO** | Mi `resolver_destino` no recibe `ruta_relativa`/`origen`/`es_protocolo`, que es de lo que depende `decidir_escritura`. **Rev. 2**: la puerta entrega una **capacidad** con base privada —un `Deposito`—, no un `Path` público. Exponer `raiz: Path` reabría justo lo que 3A cerró |
| **H21-03** el fallback no tiene canon en todos los caminos | CRÍTICO | **CONFIRMADO** | `CaseWorkspace` prohíbe que un modo bloqueado lleve raíz (`workspace_model.py:509-513`), y con «catálogo mudo» no hay canon que poner en `raiz: Path`. **Rev. 2**: tabla cerrada error→resultado, y un tipo que sepa decir «no hay raíz» sin fingir un canon |
| **H21-04** el write-set transitivo queda partido | CRÍTICO | **CONFIRMADO** (`intake_manifest.py:86-88`, `ocurrencias_crm.py:70-72`) | Mover solo los bytes deja manifiesto, ocurrencias, estado y ficha en el canon. **Rev. 2**: censo transitivo por consumidor, y E2E que compare los DOS árboles |
| **H21-05** F3 es falsa: el protocolo está exento | ALTO | **CONFIRMADO** (`repository_checkout.py:565`) | F3 se reformula a «toda escritura **no protocolaria**», y la excepción se prueba aparte |
| **H21-06** F5 es un mutante inerte | ALTO | **CONFIRMADO** (§8.2) | La matriz se rehace por **mutantes observables e independientes**, no por fronteras enunciadas |
| **H21-07** matriz cartesiana + criterios inejecutables | ALTO | **CONFIRMADO, con un matiz** | El modo **es función** del estado: la tabla cartesiana fabricaría celdas que producción no genera — el mismo defecto de la fixture que este plan denuncia. **Matiz:** su sub-punto sobre el criterio 5 (dos semillas) es cierto **de su entorno**, que no tiene `pytest-randomly`; en el mío se ejecuta y se ejecutará. No es un defecto del plan |
| **H21-08** citas que no prueban lo que sostienen | BAJO | **CONFIRMADO** | Se corrigen todas. La de `workspace_model.py:224-225` **no es cosmética**: es la que escondió H21-01 (§8.1) |

### 8.4. Qué tiene que resolver la rev. 2, en orden de dependencia

1. **La invariante del registro**, cerrada donde se escribe (`MEJORAS #136`). Todo lo demás cuelga
   de ella: sin invariante, `es_canon` no es un discriminante.
2. **El resultado que transporta autorización + destino sin exponer la raíz** (H21-02).
3. **La tabla cerrada de error→resultado**, con un tipo capaz de decir «no hay raíz» (H21-03).
4. **El censo transitivo por consumidor** (H21-04).
5. **F3 reformulada** y la matriz rehecha como mutantes observables (H21-05, H21-06, H21-07).

**No se pide tercera ronda.** El techo duro de `CLAUDE.md` la prohíbe sin autorización expresa de
Nikolai, y no hace falta: lo que toca es una **rev. 2 del diseño**, cuya cobertura de revisión será
**ausente** hasta que alguien la mire.
