---
estado: pendiente
dueño: Nikolai Tyukhay
fecha: 2026-08-26
revision: 2
---

# Apertura V1 — Plan 3A: la costura de escritura, y el mutex que empieza a proteger algo (rev. 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el mutex de `core/casos/case_mutex.py` (PR #247) **proteja algo**, y que las
escrituras del write-set del §25 pasen por **un** sitio que decida si proceden y **efectúe** el
destino — no que lo aconseje.

**Architecture:** Una **costura única** (`core/casos/escritura.py`) que exige el mutex, consulta el
guard y entrega una **capacidad de escritura** ligada al destino efectivo, no un `Path` desnudo.
Debajo, `core/casos/mutex_sesion.py`: reentrancia con modelo **propietario / prestatarios**, donde
el recurso lo cierra el **último** que sale, no el primero que adquirió. Encima, los **entrypoints
adquieren** y `core/` **exige**. La identidad del mutex sale **siempre** de un `CaseRef` resuelto
contra `meta.id_go`, nunca del nombre de la carpeta.

**Tech Stack:** Python 3.14, `pytest`. Sin dependencias nuevas.

> **Esta es la rev. 2.** La rev. 1 recibió **`NO-EJECUTABLE`** en R14: **9 hallazgos, 9
> confirmados, 0 refutados** (3 CRÍTICOS, 5 ALTOS, 1 BAJO). Adjudicación en el §0; acta literal en
> `docs/superpowers/specs/2026-08-26-apertura-v1-plan3-r14-adversarial-review.md`.
>
> **El título cambió de «Plan 3» a «Plan 3A» a propósito**, y es la mitad de la remediación de
> H14-08: este documento diseña **3A**. No es el diseño común de tres tandas, y no puede
> contabilizarse como la ronda de diseño de 3B ni de 3C.

---

## 0. Adjudicación de la revisión adversarial R14 (Codex, 2026-08-26) — NO-EJECUTABLE, remediado

- **Objeto revisado:** la **rev. 1 de este plan**, en el commit `7c55a13`. Diseño, sin código.
- **Ronda:** R14, la primera de esta pieza, corrida **antes** de escribir código.
- **Revisor:** Codex por CLI sobre copia externa `git archive`, solo lectura por construcción. Informe completo.
- **Informe recibido:** `docs/superpowers/specs/2026-08-26-apertura-v1-plan3-r14-adversarial-review.md`, `sha256` `7a0707142d381a6a…`, recomputado al archivarlo y **coincide**.
- **Hallazgos:** 9 — 3 CRÍTICOS, 5 ALTOS, 1 BAJO. **9 confirmados, 0 refutados.**
- **Remediado en:** esta rev. 2.

### 0.1. La propiedad de la que siete de los nueve son ejemplos

`CLAUDE.md` manda preguntar, ante cada hallazgo, **«¿de qué frontera es esto un ejemplo?»** antes
de remediarlo. Aquí la respuesta es una sola frase: **el nombre de una cosa no es la cosa**, y la
rev. 1 confundía el proxy con el referente **cinco veces**:

| Hallazgo | El proxy que tomé | La cosa que era |
|---|---|---|
| H14-01 | el W-code del **nombre de carpeta** | la identidad canónica, `meta.id_go` |
| H14-02 | la **ruta canónica** al hashear | el destino **efectivo** de los bytes |
| H14-04 | el **W-code** como clave de sesión | `(raíz, W-code)`, que es lo que nombra al lock |
| H14-05 | un `Path` **devuelto** | la escritura **efectuada** |
| H14-03 | el **primer** adquirente como dueño | el **último** usuario que sale |

Las cuatro primeras son el mismo error en el espacio; la quinta es el mismo error en el tiempo. Y
el diagnóstico incómodo: la rev. 1 se anunciaba como «un sitio donde toda escritura pasa» y
construía un sitio donde toda escritura **se consulta**. Autorizar no es efectuar.

Los otros dos hallazgos no son de esa familia y son peores de otra manera: **H14-07** es aritmética
mal hecha (la partición dejaba cuatro filas sin dueño y su criterio de salida era imposible), y
**H14-08** es el sesgo que `CLAUDE.md` ya me tiene fichado — inventé una contabilidad de rondas
que hacía cuadrar «cuatro en vez de seis» contando como ronda de diseño de 3B y 3C una revisión de
un documento que no las diseña.

### 0.2. Los nueve, uno por uno

| # | Sev. | Veredicto | Remedio en la rev. 2 |
|---|---|---|---|
| **H14-01** — dos mutex para un mismo expediente | CRÍTICO | **CONFIRMADO** | La costura y `sostenido()` reciben un **`CaseRef` resuelto**; el W-code sale de `meta.id_go` vía catálogo. Nueva frontera **C0**: nombre, registro y `meta.id_go` discordantes → rechaza. Verificado: `_por_w_code` casa `id_go` y `_w_code_de` lee el nombre, sin comprobación entre ambos |
| **H14-02** — custodia calculada sobre el árbol equivocado | CRÍTICO | **CONFIRMADO** | **#8 entra en 3A** y deja de estar «declarada abierta»: `pull_drive_ev` devuelve el destino efectivo y el orquestador hashea **ese** `Path`. 3A **no es desplegable** mientras el E2E de los cuatro planos falle |
| **H14-03** — la unión entre hilos no define quién cierra | CRÍTICO | **CONFIRMADO** | Modelo **propietario / prestatarios**: el `tomado()` subyacente lo cierra el **último** que sale; la transición 1→0 es atómica y **rechaza uniones nuevas** durante el cierre. Nueva frontera **M8** con el orden `A entra → B entra → A sale → B escribe → B sale`, más la variante con excepción de A |
| **H14-04** — la clave de sesión omite `raiz` | ALTO | **CONFIRMADO** | Clave canónica `(raiz_de_locks(raiz) normalizada, w_code canónico)`. Nueva frontera **M9**: misma raíz escrita de dos formas equivalentes, y dos raíces distintas |
| **H14-05** — devuelve una ruta y no obliga a usarla | ALTO | **CONFIRMADO** | La costura entrega una **capacidad** (`Deposito`) que efectúa la escritura y **no expone la raíz canónica**. El censo AST baja a **trinquete sintáctico**; la prueba de cierre son los **E2E por fila del §25.4**, que la rev. 1 había omitido enteros |
| **H14-06** — C1 mezcla tres contadores y no tiene transición | ALTO | **CONFIRMADO** | Tres contratos separados y nombrados; **ningún evento nuevo en `INTAKE_EVENTS`**: el intento sin mutex se registra **fuera** del log del caso. Verificado que el vocabulario es cerrado y que `append_event` lanza — el evento que prometía la rev. 1 **no se podía emitir**, y hacerlo por la costura recurre |
| **H14-07** — la partición no cubre las 27 filas | ALTO | **CONFIRMADO** | Matriz exhaustiva 1-27 con **una** tanda por fila (§1.2). Contado: la rev. 1 dejaba **#1, #2, #3 y #25** sin dueño, 3A tenía **8** protocolos y su criterio exigía «las doce», y 3B era **7 derivados + 4 protocolos** |
| **H14-08** — una ronda de diseño para tres tandas sin diseño | ALTO | **CONFIRMADO** | R14 es la ronda de diseño de **3A y solo de 3A**. 3B y 3C tendrán la suya cuando exista su diseño. Nadie llega a una tercera, así que no hace falta autorización de Nikolai |
| **H14-09** — «SIN VERIFICAR» incompleto y censos no reproducibles | BAJO | **CONFIRMADO** | §5 publica el **comando exacto** de cada censo. Corregido: **43 `now_iso(` vs 5 `now_iso_utc(`** con una sola definición (mi «7» contaba imports), y **80** primitivas sobre los **11** ficheros que la tabla nombra (mi «~85» salió de 8 sin publicar el patrón) |

### 0.3. Lo que refuté de mi propia lectura, antes de escribir la remediación

Al verificar H14-01 creí encontrar algo peor: que `W-abc` y `W-ABC` producían **dos** lockfiles.
**Falso.** `_w_code_valido` normaliza a mayúsculas *antes* de casar el patrón y `ruta_del_lock`
compone con el valor canónico que devuelve, así que las dos grafías colisionan en un solo fichero.
La primitiva de #247 está bien; lo que estaba mal era mi plan. Lo anoto porque el error simétrico
—adjudicar como defecto del código lo que es defecto del diseño que lo va a usar— habría gastado
una ronda del mutex, que es justo lo que el techo duro impide.

### 0.4. Lo que sigue SIN VERIFICAR de esta ronda

El revisor lo declaró y no se maquilla: **no acreditó la genealogía de la copia** (el `git archive`
no lleva metadatos Git, así que verificó contenido y hash, no ascendencia), **no ejecutó `filelock`**
(ausente en su entorno, luego no hay prueba de exclusión entre procesos en esta ronda) y **no
ejecutó un `fork`** (host Windows, `spawn`). Nada de eso está refutado: está sin mirar.

---

## 1. Alcance

### 1.1. Por qué 3A es una pieza y no un tercio de un plan

El write-set del §25 son 27 clases de artefacto sobre **80 primitivas de escritura** en **11**
ficheros (censo reproducible en el §5). Una sola ronda sobre el diff tendría que revisar las 80
migraciones a la vez, y las dos rondas de código de este diseño —R6 y R8— encontraron nueve
hallazgos cada una, **la mayoría defectos míos introducidos al remediar**. Un diff más grande no
mejora esa proporción.

**Lo que cambió respecto de la rev. 1:** este documento diseña **3A**. No pretende ser el diseño
común de tres tandas ni reclama su presupuesto de rondas (H14-08).

### 1.2. La matriz 1-27: una tanda por fila, sin huecos

| Tanda | Filas | Clases |
|---|---|---|
| **3A** | #4, #5, #6, #7, #8, #9, #10, #11, #12, #13 | 8 protocolo + 2 contenido |
| **3A-alta** | #1, #2, #3 | 3 estructura |
| **3B** | #14, #15, #16, #17, #19, #21, #22, #23, #24, #26, #27 | 7 derivado + 4 protocolo |
| **3C** | #18, #20, #25 | 3 derivado |

**Las tres de estructura entran en 3A como sub-pieza `3A-alta`, y no por completitud: por
dependencia.** `ensure_case` crea la raíz **antes** de que exista un caso que el guard vigente
pueda resolver, así que el alta no puede pasar por la misma puerta que una escritura sobre un caso
ya existente. Necesita **operación propia**, bajo el **mismo mutex de W-code** —que existe antes
que la carpeta, y ésa era la razón declarada de indexar por identidad en D2—. Diseñarla es parte de
3A; sin ella, «toda escritura pasa por un sitio» es falso desde el primer comando.

**#25 (`99_Versiones anteriores/**`) se mueve a 3C**, que es donde se construye el archivado del que
es destino. En la rev. 1 no tenía tanda.

---

## 2. La costura (`core/casos/escritura.py`)

```python
CLASES = ("contenido", "protocolo", "derivado", "estructura")

@dataclasses.dataclass(frozen=True)
class Deposito:
    """Capacidad de escritura sobre UN destino ya autorizado.

    No expone la raíz canónica del caso: quien la tiene puede escribir donde la costura
    decidió y en ningún otro sitio. Eso es la diferencia entre autorizar y efectuar, y es
    la remediación de H14-05.
    """
    clase: str
    desviada: bool
    protegida_por_mutex: bool
    motivo_sin_mutex: str | None

    def escribir_texto(self, rel: str, contenido: str) -> Path: ...
    def escribir_bytes(self, rel: str, contenido: bytes) -> Path: ...
    def dir_para(self, rel: str) -> Path:      # para motores que escriben ellos (rclone, OCR)
        """El directorio efectivo, y **registra** que se entregó."""

def deposito(ref: CaseRef, ruta_relativa, origen, *, clase, modo="libre") -> Deposito
```

**`ref` es un `CaseRef` resuelto, no un `case_id`** (H14-01). El W-code sale de `meta.id_go` vía
`CaseCatalog`; el nombre de la carpeta no es identidad y su propio docstring lo dice.

**El orden importa y es la mitad del diseño:** la costura **exige el mutex ANTES de consultar el
guard**. Verificado en la fuente: `guard_escritura` llama a `append_event` cuando desvía
(`core/case_manager.py:812-816`), y eso es la fila #13, protocolo, obligada a ir bajo mutex. Si el
mutex se exigiera después, la escritura del propio guard quedaría fuera de él.

**Mapeo de clase a guard:** `protocolo` → `es_protocolo=True` (exento del **desvío**, nunca del
**mutex**). `contenido`, `derivado` y `estructura` → guard obligatorio. Una `clase` desconocida
**lanza**: lo que no se reconoce no puede degradar a exento.

### Las fronteras de la costura — una por mutante

| # | Frontera |
|---|---|
| **C0** | Nombre de carpeta, registro y `meta.id_go` discordantes → **rechaza** en los dos modos. Es H14-01 y va primero porque sin identidad no hay namespace |
| C1 | Sin mutex sostenido: en `v1` **rechaza**; en `libre` deposita, `protegida_por_mutex=False` y **suma al contador dinámico** (§4) |
| C2 | Mutex sostenido pero **perdido** → rechaza **en los dos modos**, con error distinto de C1 |
| C3 | Guard dice desviar → el `Deposito` escribe en la bandeja y `desviada=True` |
| C4 | `clase="protocolo"` → exento del desvío, **nunca** del mutex |
| C5 | `clase="derivado"` → guard obligatorio; ningún valor de `clase` lo exime |
| C6 | **Tres** estados de identidad, no dos: namespace usable; sin W-code; y **W-code que el mutex no admite** (`_w_code_de` extrae `W-AB` y códigos de 22 caracteres que `_w_code_valido` rechaza). Los tres con salida declarada, ninguno con `ValueError` crudo escapando |
| C7 | El mutex se exige **antes** que el guard, así que el evento del desvío nace dentro del mutex |
| **C8** | El `Deposito` **no expone** la raíz canónica: no hay método que la devuelva, y `dir_para` registra lo que entrega (H14-05) |

---

## 3. La reentrancia (`core/casos/mutex_sesion.py`)

**No se toca `case_mutex.py`.** Lleva cuatro rondas (R10-R13) y 17 mutantes; editarlo es reabrirlas.

```python
#: clave = (raiz_de_locks(raiz) normalizada, w_code canónico)  — H14-04
_SESIONES: dict[tuple[str, str], "_Entrada"] = {}
_CANDADO = threading.Lock()

@contextlib.contextmanager
def sostenido(ref: CaseRef, *, ahora_fn, raiz=None, lease_seconds=LEASE_POR_DEFECTO): ...

def vigente(ref: CaseRef, *, raiz=None) -> SesionMutex | None: ...
```

**Propietario y prestatarios son cosas distintas** (H14-03). `tomado()` liga el hilo de latido y la
liberación al `finally` del que adquirió, así que si el adquirente sale mientras otro hilo sigue
dentro, **libera bajo sus pies**. El modelo: el `tomado()` subyacente lo cierra el **último**
prestatario que sale; la transición 1→0 es atómica y **rechaza uniones nuevas** mientras cierra.

`vigente()` distingue **tres** estados: nunca lo tuve (`None`), lo tengo (la sesión), y **lo perdí**
(`MutexPerdido`). Que perder no colapse en «no tener» es C2.

### Las fronteras del anidamiento — una por mutante

| # | Frontera |
|---|---|
| M1 | Unirse **revalida contra disco** (`SesionMutex.revalidar()`), no contra memoria |
| M2 | Unirse devuelve **el mismo objeto** → no arranca un segundo hilo de latido |
| M3 | La salida del bloque **interno** no libera; solo la del último |
| M4 | La profundidad se decrementa en `finally`, así que sobrevive a una excepción del cuerpo |
| M5 | Otro W-code es sesión independiente, no una unión |
| M6 | Revalidación fallida al unirse → `MutexPerdido`. **Nunca adquiere una nueva**: serían dos escritores creyéndose titulares |
| M7 | El mapa es del proceso y la profundidad se toca bajo `_CANDADO`; unirse entre hilos es correcto —el lock del SO es del proceso— y contarlo mal es lo que rompe |
| **M8** | **El adquirente puede salir antes que un prestatario.** Orden `A entra → B entra → A sale → B escribe → B sale`: el lock sigue vivo mientras B está dentro, y se libera al salir B. Más la variante en que A sale **por excepción** (H14-03) |
| **M9** | Mismo W-code y **raíz distinta** son sesiones distintas; misma raíz escrita de dos formas equivalentes es **una** (H14-04) |
| **M10** | `vigente()` distingue **tres** estados —nunca lo tuve / lo tengo / **lo perdí**— y exige identidad ya resuelta. Añadida al enumerar: el §3 la contrataba en prosa y no tenía número, así que no habría tenido mutante |

---

## 4. Los tres contadores, separados y nombrados (H14-06)

La rev. 1 los mezclaba en una frase y no conectaba ninguno con la conducta. Son tres cosas:

| Contrato | Qué mide | Para qué sirve |
|---|---|---|
| **(a) Métrica dinámica** | escrituras que llegan a la costura sin mutex, en ejecución | **solo diagnóstico**. No gobierna nada |
| **(b) Censo AST** | sitios de escritura que no pasan por la costura, estático, con tope | trinquete sintáctico: el tope **solo baja** |
| **(c) Polaridad de C1** | si `libre` rechaza o deposita-y-cuenta | **una constante en el código**, cambiada por un task con test propio |

**(c) no se invierte sola al llegar (b) a cero.** El precedente que la rev. 1 citaba mal —el
`TECHO_ESCOTILLA` del Task 6 de la Fase 1— tampoco invertía conducta automáticamente: el default se
cambió a mano, con su task. Un número que cambia el comportamiento sin que nadie lo decida es peor
que un número que no lo cambia.

**Y ningún evento nuevo.** `INTAKE_EVENTS` es un `frozenset` cerrado (`core/intake_log.py:41-75`) y
`append_event` lanza ante un evento desconocido, así que el «evento en el log» que prometía la
rev. 1 **no se podía emitir**. Peor: emitirlo por `append_event` —fila #13, protocolo, obligada a
pasar por la costura— **recurre**. La métrica (a) se registra **fuera del log del caso**.

---

## 5. Los censos, con su comando (H14-09)

Las cifras de la rev. 1 no eran reproducibles. Estas lo son.

**Relojes** — una sola definición de «uso»: llamada con paréntesis, en `core/` + `scripts/`.

```bash
grep -rnoE '(^|[^_a-zA-Z])now_iso\(' --include=*.py core/ scripts/ | wc -l      # 43
grep -rnoE '(^|[^_a-zA-Z])now_iso_utc\(' --include=*.py core/ scripts/ | wc -l  # 5
```

**43 frente a 5**, no «43 frente a 7»: el 7 de la rev. 1 contaba además imports y menciones, o sea
dos definiciones distintas dentro de una misma comparación.

**Primitivas de escritura** — sobre los **11** ficheros que la tabla del §25 nombra como productores
(`case_manager`, `intake_drive`, `intake_manifest`, `intake_log`, `sync_sudespacho`,
`email_atomize/pipeline`, `adjuntos_contenido/pipeline`, `sala_maquina`, `split_documental`,
`scripts/abrir_caso`, `scripts/sala_maquina`):

```bash
grep -cE 'write_text\(|write_bytes\(|json\.dump\(|\.mkdir\(|\.unlink\(|os\.replace\(|shutil\.copy2?\(|open\([^)]*["'"'"']a["'"'"']|append_event\(' <fichero>
```

**Total 80.** La rev. 1 dijo «~85» midiendo **8** ficheros y sin publicar el patrón; el revisor
obtuvo 79 con el suyo. La cifra no importa tanto como que ahora se puede recomputar y discrepar.

**El reloj que se pasa a la primitiva es `now_iso_utc`.** `case_mutex` rechaza a propósito un
instante sin offset, y se pasa **explícitamente en cada `sostenido()`**: ningún módulo hereda el
reloj del suyo.

---

## Global Constraints

- Ningún módulo de `core/` adquiere el mutex. `core/` **exige** (vía la costura); los
  **entrypoints** (`scripts/*`, `streamlit_app.py`) adquieren.
- La identidad del mutex sale **siempre** de un `CaseRef` resuelto contra `meta.id_go`. Nunca del
  nombre de la carpeta.
- La costura **efectúa** o entrega una capacidad ligada al destino. No devuelve la raíz canónica.
- Se conserva `guard_escritura` tal cual: la costura lo **envuelve**, no lo sustituye.
- Sin dependencias nuevas.

## File Structure

```
core/casos/mutex_sesion.py       NUEVO  — reentrancia, propietario/prestatarios, `vigente()`
core/casos/escritura.py          NUEVO  — la costura y `Deposito`
tests/test_mutex_sesion.py       NUEVO  — M1-M9 + sus 9 mutantes
tests/test_escritura_costura.py  NUEVO  — C0-C8 + sus 9 mutantes
tests/test_escritura_e2e.py      NUEVO  — el E2E por fila del §25.4 (los cuatro planos)
tests/test_escritura_censo.py    NUEVO  — el trinquete sintáctico del Task 7
```

---

## Task 1: `mutex_sesion` — reentrancia y ciclo de vida ✅ COMPLETO (`fb3ffd1`)

- [x] `tests/test_mutex_sesion.py` con un test por frontera **M1-M10**, antes del módulo. **13
      tests**, verdes.
- [x] **M8 es la frontera que R14 compró** y se prueba con dos hilos y barreras en el orden
      `A entra → B entra → A sale → B verifica el lock vivo y escribe → B sale → lock liberado`.
      Más la variante con A saliendo por excepción.
- [x] M9 con dos raíces distintas **y** la misma raíz escrita de dos formas equivalentes.
- [x] M2 contando hilos vivos con nombre `mutex-<W>` antes y dentro del anidamiento.
- [x] M6 borrando el lock desde fuera: `sostenido()` anidado **lanza** y **no** crea uno nuevo.
- [x] Implementar `core/casos/mutex_sesion.py`.
- [x] **Commitear antes de mutar** — hecho en `fb3ffd1`, antes de la primera mutación.
- [x] **12 mutantes: 11 mueren cada uno por su frontera; M7 se declara SIN CUBRIR.**

### 1.1. Lo que el arnés encontró, que es de él y no del módulo

El arnés **falla si un ancla no casa o casa más de una vez**, y además exige que cada mutante
mate **exactamente** los tests previstos. Esa segunda exigencia paró la primera corrida con
**cuatro** discrepancias, y adjudicarlas una por una fue el trabajo útil:

- **Tres eran expectativas mías demasiado estrechas**, no mala puntería. Cuando un mutante mata
  tests de más porque esos tests **contratan la misma propiedad** por otra vía, eso es
  coherencia: el mutante de la clave incompleta mata M5 *y* M9 porque «clave distinta → sesión
  distinta» es lo que contratan los dos, uno por el W-code y otro por la raíz.
- **Una era un mutante genuinamente mal apuntado:** el primero de M2 mataba **siete** tests
  porque fabricaba una sesión nueva dentro de la rama de unión. Se sustituyó por el mínimo que
  rompe la propiedad —ceder una **copia** de la sesión—, y entonces mueren exactamente los
  cuatro tests que afirman identidad de objeto.

**La distinción que el arnés no puede hacer solo:** muerte conjunta legítima frente a mutante
demasiado ancho. Eso lo adjudica quien lo lee, y por eso el arnés para en vez de decidir.

### 1.2. M7 queda SIN CUBRIR por mutación, y se declara

Quitar `_CANDADO` de la sección crítica **no produce un rojo determinista**: con el GIL y sin
contención real, los dos hilos del test casi nunca se intercalan en el `-= 1`. Un mutante que
sobrevive aquí **no** prueba que la propiedad esté contratada; prueba que este test no puede
medirla. La propiedad se sostiene por lectura del código y consta como no verificada.

### 1.3. Un defecto del TEST, no del módulo

La primera versión de M8-bis dejaba salir a A **antes** de que B se uniera, así que lo que
saltaba era la guarda `cerrando` —«no se admiten uniones nuevas»—, que es correcta y no es lo
que ese test mide. Lo diagnostiqué imprimiendo el `detalle` de la excepción en vez de
teorizar: el mensaje visible de `MutexPerdido` es su `descripcion` de clase y **no** dice de
qué `raise` viene, así que a ojo era indistinguible del cierre de `tomado()`.

## Task 2: `escritura` — la costura y la capacidad

- [ ] `tests/test_escritura_costura.py` con un test por frontera **C0-C8**, antes del módulo.
- [ ] **C0 primero:** montar un caso cuyo nombre de carpeta y cuyo `meta.id_go` discrepen, y
      exigir rechazo. Es el CRÍTICO de R14 y sin este test la pieza no vale.
- [ ] C6 con los tres estados y **tres** salidas distinguibles; el test comprueba **cuál**.
- [ ] C7: con el mutex NO sostenido y el caso `prestado`, la costura rechaza **sin** haber escrito
      el evento del desvío. Si el evento aparece, el orden está mal.
- [ ] C8: buscar por AST un método de `Deposito` que devuelva la raíz del caso. No debe existir.
- [ ] Implementar `core/casos/escritura.py`. Commitear. Nueve mutantes por frontera.

## Task 3: `3A-alta` — la operación de alta bajo el mismo mutex

- [ ] Diseñar y construir el alta (#1, #2, #3) como operación **distinta** del guard de caso
      existente: crea la raíz **bajo el mutex del W-code**, que existe antes que la carpeta.
- [ ] Aplicar las decisiones del §25 sobre qué se crea: solo `00_Input`, `01_Procesado` y la base
      `05_CRM`; `90_Notas personales` sigue eager y **exenta declarada**; **no** se crean
      `{Sala lectura, MD, _revisar}` ni las plantillas de viabilidad.
- [ ] Test de no regresión: `ensure_case` en modo `libre` conserva su comportamiento.

## Task 4: Medir el radio ANTES de migrar

- [ ] Contar **las tres cosas del §4 por separado**: (a) llegadas sin mutex, (b) censo AST, y
      cuántos tests rompen. Los tres números **escritos aquí**, no en el chat.
- [ ] Si los tests roto no son casi cero, el trinquete no está donde creo: averiguar por qué antes
      de seguir.
- [ ] Fixture del mutex en tests **explícita, no `autouse`**: una fixture `autouse` haría
      invisible la exigencia, que es la «exención por omisión» que el §25 existe para eliminar.

## Task 5: Los entrypoints adquieren

- [ ] `scripts/abrir_caso.py`, `scripts/sala_maquina.py`, `scripts/sync_sudespacho.py` y las vías
      de intake de `streamlit_app.py` envuelven su trabajo en
      `sostenido(ref, ahora_fn=now_iso_utc)`, con `ref` **resuelto**.
- [ ] `--modo v1` adquiere **una vez** y las etapas se unen; test que recorra las dos capas.
- [ ] Un entrypoint que no pueda resolver identidad en `--modo v1` **aborta** (C0/C6).

## Task 6: Migrar las filas de 3A, incluida #8

- [ ] #6 y #9 (contenido, las dos que ya consultan el guard): pasar por `Deposito`, más mutex.
- [ ] #4, #5, #7, #10, #11, #12, #13 (protocolo): por la costura con `clase="protocolo"`, lo que
      convierte su exención de **omisión** en **declaración**.
- [ ] #5 **debe consumir la decisión del guard**: hoy escribe los ids de Drive en `_caso.md` tras
      un desvío como si no lo hubiera habido.
- [ ] **#8 se cierra aquí, no en 3C** (H14-02): `pull_drive_ev` devuelve el destino efectivo y
      `_intake_drive_ev` hashea **ese** `Path`, no `case_dir / "00_Input" / subdir`.
- [ ] **E2E de los cuatro planos del §25.4**, que la rev. 1 había omitido: por cada fila de
      contenido, doblar **los dos** destinos y probar **cuál** cambió. Es la prueba de cierre; el
      censo AST no lo es.

## Task 7: El trinquete sintáctico

- [ ] Guard AST: producción entra por `mutex_sesion.sostenido`, no por `case_mutex.tomado` crudo.
- [ ] Censo (b) del §4 con su tope actual **escrito**. El tope solo baja.
- [ ] **Sin números de línea**: la lista indexada por línea del Task 6 de la Fase 1 caducó a mitad
      de su propia migración.
- [ ] Prueba de mutación del propio guard: un guard sin prueba de que muerde no es un guard.

---

## Criterio de salida de 3A

1. **C0 muerde:** un caso con nombre e `id_go` discordantes no se escribe. Sin esto no hay pieza.
2. `vigente()` distingue los tres estados y la costura los trata distinto.
3. Un `sostenido()` anidado no se bloquea contra sí mismo, no arranca un segundo latido, y **el
   lock sobrevive a la salida del adquirente mientras quede un prestatario**.
4. Las diez filas de 3A **más las tres del alta** pasan por la costura; los ocho protocolos de esta
   tanda están exentos **por declaración**. Los otros cuatro son de 3B y no se cuentan aquí.
5. **El E2E de los cuatro planos pasa, incluida #8.** Mientras falle, 3A no es desplegable.
6. `--modo v1` **rechaza** una escritura sin mutex.
7. Suite verde con **dos semillas** (`pytest-randomly`).
8. Un mutante por frontera, cada uno muerto por **la suya**, con arnés que falla si un ancla no
   casa **y** si el mutante mata de más. Del anidamiento: **11 muertos + M7 declarado sin
   cubrir**. De la costura: 9 (C0-C8), pendientes del Task 2. Lo que **no** vale como criterio
   es un número de mutantes: vale que ninguna frontera se quede sin el suyo, y que las que no
   puedan tenerlo se declaren.

**Lo que 3A NO permite declarar:** «el write-set está protegido». Al cerrar 3A lo estarán las trece
filas de esta tanda en `v1`; las catorce restantes siguen contadas en el censo. La frase honesta es
«el mutex protege las trece filas de 3A», y el número del censo dice cuánto falta.

## Lo que este plan deliberadamente NO hace

- **No toca `case_mutex.py`.** Se envuelve, no se edita.
- **No migra 3B ni 3C**, y **no reclama su ronda de diseño** (H14-08).
- **No cierra el orden durable, la monotonía de observación ni el snapshot por ronda** (§25.5):
  son contratos del Plan 4.
- **No encadena la secuencia de V1** (Plan 5). `--modo v1` sigue siendo una puerta; aquí adquiere
  el mutex al pasarla.

## Lo que sigue SIN VERIFICAR, y se declara

- **La reacción del mutex a un salto real de NTP.** Heredado del §3.5 del plan del mutex. La cota
  simétrica de R13 acota el `ahora` **inyectado**, no un salto del reloj del sistema entre latidos.
- **Las seis remediaciones de R13 no tienen ronda propia.** 3A usa `revalidar()` con cota contra el
  lease, que es una de ellas, sin haberla revisado.
- **Comportamiento tras `fork`.** En Windows `multiprocessing` usa `spawn`, así que `_SESIONES` no
  se hereda. En una plataforma con `fork`, el mapa, el nonce y `_PROCESO_UID` se copiarían mientras
  los hilos de latido **no** sobreviven: un hijo con un mapa que afirma titularidad y nadie
  renovando. No se diseña `register_at_fork` porque el repo es Windows; **queda sin verificar**, no
  refutado.
- **Exclusión real entre procesos en esta ronda.** R14 no pudo ejecutar `filelock`. La prueba de
  dos procesos vive en la suite del mutex (#247), no en R14.
- **El censo (b) mide llamadas, no flujo de datos.** Un llamador que use `Deposito` y además
  escriba por su cuenta lo pasa. Lo que cierra eso es el E2E del Task 6, no el censo.
- **La cobertura de 3B y 3C.** Sus filas están asignadas (§1.2) pero su diseño no existe, así que
  nada de este plan dice cómo se resuelven.
