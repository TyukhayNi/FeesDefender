---
estado: pendiente-de-revision
dueño: Nikolai Tyukhay
fecha: 2026-08-26
revision: 1
---

# Apertura V1 — Plan 3: la costura de escritura, y el mutex que empieza a proteger algo

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el mutex de `core/casos/case_mutex.py` (PR #247) **proteja algo**, y que las
escrituras del write-set del §25 pasen por **un** sitio donde se decida si proceden y a dónde van.

**Architecture:** Una **costura única** (`core/casos/escritura.py`) que reúne las dos decisiones
que hoy están separadas o ausentes —¿tengo el mutex? ¿el guard desvía?— y devuelve **un** destino.
Debajo, una capa de **reentrancia** (`core/casos/mutex_sesion.py`) que hace que un `tomado()`
anidado sobre el mismo W-code sea una unión revalidada en vez de un `CaseBusy` contra uno mismo.
Encima, los **entrypoints adquieren** y el core **exige**: ningún módulo de `core/` adquiere el
mutex por su cuenta.

**Tech Stack:** Python 3.14, `pytest`. Sin dependencias nuevas.

---

## 1. Por qué este plan viene en tres tandas, y qué ronda come cada una

El Plan 3 tal como lo enuncia el §25 son **dos problemas distintos** sobre **~85 primitivas de
escritura** (medido el 2026-08-26: `write_text`/`write_bytes`/`json.dump`/`mkdir`/`unlink`/
`os.replace`/`shutil.copy2`/`open(...,"a")`/`append_event` en los ocho ficheros productores). Una
sola ronda sobre el diff tendría que revisar las 85 migraciones a la vez, y **R6 y R8 encontraron
nueve y nueve hallazgos de los que la mayoría eran defectos míos introducidos AL remediar**. Un
diff más grande no mejora esa proporción.

| Tanda | Qué construye | Filas del §25 |
|---|---|---|
| **3A** (este plan) | La costura, la reentrancia, los entrypoints que adquieren, y las escrituras de identidad/protocolo del camino de intake | #4, #5, #6, #7, #8, #9, #10, #11, #12, #13 |
| **3B** | Los diez derivados por la costura ya construida | #14-#17, #19, #21-#24, #26, #27 |
| **3C** | La poda que archiva en vez de borrar, y el hash del destino efectivo | #18, #20, y el cierre de #8 |

### El presupuesto de rondas, y por qué trocear no lo multiplica

`CLAUDE.md` §«Cuántas rondas»: **dos** si la pieza decide quién puede escribir o puede destruir
datos de cliente. Las tres tandas cumplen ese criterio, así que la lectura literal serían **seis**
rondas. Eso es inflación de proceso nacida de una decisión mía de trocear, no del radio de daño.

**Se resuelve así: una ronda de DISEÑO sobre este documento —que es el diseño común de las tres— y
una ronda de DIFF por tanda. Cuatro.** Ninguna pieza llega a una tercera, así que el techo duro se
respeta sin estirarlo. La ronda de diseño es la que va antes de escribir código, y es esta.

### Lo que 3C NO es, corregido antes de venderlo

Iba a poner 3C primero por «pérdida de datos hoy». **Medido, no lo es.** Los tres `unlink`
(`email_atomize/pipeline.py:220,267`, `adjuntos_contenido/pipeline.py:109`) podan **derivados
huérfanos** —espejos MD, vistas renderizadas, contenido extraído— y `00_Input` no se toca: son
regenerables. Incumplen el contrato del §8 (retirada irreversible en vez de archivado), que es
razón para arreglarlo, no para adelantarlo. El daño real y estrecho: si un `.eml` se retira de
`00_Input`, su espejo desaparece sin histórico, y con él cualquier anotación humana que viviera en
el árbol derivado.

---

## 2. La costura (`core/casos/escritura.py`)

```python
CLASES = ("contenido", "protocolo", "derivado", "estructura")

@dataclasses.dataclass(frozen=True)
class Escritura:
    destino: Path                      # DONDE se escribe. El llamador no calcula otra.
    desviada: bool
    clase: str
    protegida_por_mutex: bool
    motivo_sin_mutex: str | None

def destino(case_id, ruta_relativa, origen, *, clase, modo="libre") -> Escritura
```

**El orden importa y es la mitad del diseño:** la costura **exige el mutex ANTES de consultar el
guard**. No es estética. `guard_escritura` emite un evento `pendiente_checkin` en
`_intake_log.jsonl` cuando desvía (fila #13, clase protocolo), así que si el mutex se exigiera
después, la propia escritura del guard quedaría fuera de él. Exigir primero cierra esa costura sin
un caso especial.

**Mapeo de clase a guard:** `protocolo` → `es_protocolo=True` (exento del **desvío**, nunca del
**mutex**). `contenido`, `derivado` y `estructura` → `es_protocolo=False`, guard obligatorio. Una
`clase` desconocida **lanza**: una clase que no se reconoce no puede degradar a exenta.

### Las 7 fronteras de la costura — una por mutante

| # | Frontera |
|---|---|
| C1 | Sin mutex sostenido: en `modo="v1"` **rechaza**; en `libre` escribe con `protegida_por_mutex=False`, `motivo_sin_mutex` poblado, evento en el log **y suma al censo** |
| C2 | Mutex sostenido pero **perdido** → rechaza **en los dos modos**, y con error distinto del de C1. «Lo tenía» no es «lo tengo», y perder no degrada a no tener |
| C3 | Guard dice desviar → `destino` es la bandeja y `desviada=True` |
| C4 | `clase="protocolo"` → exento del desvío, **nunca** del mutex |
| C5 | `clase="derivado"` → guard obligatorio; no hay valor de `clase` que lo exima |
| C6 | Sin W-code: en `modo="v1"` aborta; en `libre` igual que C1, con motivo distinto —«no hay identidad» no es «no se tomó»— y el test comprueba **cuál** de los dos motivos salió |
| C7 | El mutex se exige **antes** que el guard, así que el evento del desvío nace dentro del mutex |

### Por qué C1 no rechaza en `libre`, y qué lo convierte en rechazo

La primera redacción de este plan hacía que C1 rechazara **siempre**. Es el destino correcto y
un primer paso equivocado: cualquier camino que el Task 4 se deje sin cablear pasaría de escribir
a **abortar**, y algunos de esos caminos son las vías de intake de `streamlit_app.py`, que es la
herramienta con la que Paola y Ana trabajan a diario. Un fallo duro ahí lo paga el despacho por un
descuido mío de cableado.

**El remedio no es tolerar el hueco: es contarlo y cerrarlo con un trinquete.** En `libre`, una
escritura sin mutex se ejecuta, se **declara** (`protegida_por_mutex=False`) y **suma al censo** del
Task 6. El censo tiene un tope, el tope solo baja, y **C1 pasa a rechazar en los dos modos cuando el
censo llega a cero** — que es el mismo método con el que el Task 6 de la Fase 1 invirtió su default:
medir (377 roto), migrar, volver a medir (18), y solo entonces cambiar la polaridad.

**Lo que sí rechaza desde el primer día en los dos modos es C2**, porque un mutex perdido a mitad
de operación no es un hueco de migración: es dos procesos creyéndose titulares, que es el daño
entero que la pieza existe para impedir.

---

## 3. La reentrancia (`core/casos/mutex_sesion.py`)

**No se toca `case_mutex.py`.** Lleva cuatro rondas (R10-R13) y 17 mutantes; modificarlo es
reabrirlas. La reentrancia va **encima**, en un módulo nuevo.

```python
_SESIONES: dict[str, list] = {}      # w_code -> [SesionMutex, profundidad]
_CANDADO = threading.Lock()

@contextlib.contextmanager
def sostenido(w_code, *, ahora_fn, raiz=None, lease_seconds=LEASE_POR_DEFECTO): ...

def vigente(w_code, *, raiz=None) -> SesionMutex | None: ...
```

`vigente()` es lo que consume la costura. **Distingue tres estados, no dos:** nunca lo tuve
(`None`), lo tengo (la sesión), y **lo perdí** (`MutexPerdido`). Que perder no colapse en «no
tener» es C2, y es el mismo defecto que R11/H11-02 encontró dentro de `tomado()`: una pérdida
silenciosa deja al cuerpo escribiendo como titular.

### Las 7 fronteras del anidamiento — una por mutante

| # | Frontera |
|---|---|
| M1 | Unirse **revalida contra disco** (`SesionMutex.revalidar()`), no contra memoria |
| M2 | Unirse devuelve **el mismo objeto** de sesión → no arranca un segundo hilo de latido |
| M3 | La salida del bloque **interno** no libera; solo la más externa |
| M4 | La cuenta de profundidad se decrementa en `finally`, así que sobrevive a una excepción del cuerpo |
| M5 | Otro W-code en el mismo proceso es sesión independiente, no una unión |
| M6 | Si la revalidación al unirse falla → `MutexPerdido`. **Nunca adquiere una nueva**: serían dos escritores creyéndose titulares |
| M7 | El mapa es del proceso y la profundidad se toca bajo `_CANDADO`; unirse entre hilos es correcto —el lock del SO es del proceso— y contarlo mal es lo que rompe |

---

## 4. El reloj

`case_mutex` rechaza a propósito un instante sin offset. Los entrypoints pasan
**`now_iso_utc`**, no `now_iso`. Medido el 2026-08-26 en `core/` + `scripts/`: **43 usos de
`now_iso` frente a 7 de `now_iso_utc`**, así que el reloj mayoritario del repo es el que la
primitiva rechaza. Se pasa **explícitamente en cada `sostenido()`**; ningún módulo hereda el reloj
del suyo.

---

## Global Constraints

- Ningún módulo de `core/` adquiere el mutex. `core/` **exige** (vía la costura); los
  **entrypoints** (`scripts/*`, `streamlit_app.py`) adquieren.
- La costura es el **único** sitio que traduce `ruta_relativa` a `destino`. Un llamador que
  componga su propia ruta después de llamar es un defecto, y el Task 6 lo censa.
- Se conserva `guard_escritura` tal cual: la costura lo **envuelve**, no lo sustituye. Los seis
  llamadores actuales siguen funcionando mientras se migran.
- Sin dependencias nuevas.

## File Structure

```
core/casos/mutex_sesion.py      NUEVO  — reentrancia y `vigente()`
core/casos/escritura.py         NUEVO  — la costura
tests/test_mutex_sesion.py      NUEVO  — M1-M7 + sus 7 mutantes
tests/test_escritura_costura.py NUEVO  — C1-C7 + sus 7 mutantes
tests/test_escritura_censo.py   NUEVO  — el guard permanente del Task 6
```

---

## Task 1: `mutex_sesion` — la reentrancia, con sus siete fronteras

- [ ] Escribir `tests/test_mutex_sesion.py` con un test por frontera M1-M7 **antes** del módulo.
- [ ] M2 se prueba contando hilos vivos con nombre `mutex-<W>` antes y dentro del anidamiento:
      un segundo latido sobre el mismo lock es exactamente el fallo que la unión evita.
- [ ] M6 se prueba borrando el fichero de lock desde fuera y comprobando que `sostenido()`
      anidado **lanza** `MutexPerdido` y **no** crea un lock nuevo (comprobar por `leer_estado`).
- [ ] M7 se prueba con dos hilos y una barrera, no con dos llamadas secuenciales.
- [ ] Implementar `core/casos/mutex_sesion.py`.
- [ ] **Commitear antes de mutar.** Perdí una remediación entera con `git checkout` en el 70º
      por no hacerlo, y `git checkout` restaura desde el ÍNDICE.
- [ ] Siete mutantes, uno por frontera, con el arnés que **falla si un ancla no casa**. Un
      arnés que no falla da por buenos mutantes que no ejecutó — pasó dos veces en el 70º.

## Task 2: `escritura` — la costura, con sus siete fronteras

- [ ] Escribir `tests/test_escritura_costura.py` con un test por frontera C1-C7 antes del módulo.
- [ ] C7 se prueba comprobando que, con el mutex NO sostenido y el caso en `prestado`, la costura
      rechaza **sin** haber escrito el evento del desvío. Si el evento aparece, el orden está mal.
- [ ] C2 exige un tipo de error distinto de C1: el test comprueba el **tipo**, no el mensaje.
- [ ] Implementar `core/casos/escritura.py`.
- [ ] Commitear, y siete mutantes por frontera.

## Task 3: Medir el radio ANTES de migrar

- [ ] Con la costura puesta y el trinquete en `libre`, **contar dos cosas distintas**: (a) cuántas
      escrituras llegan sin mutex —el censo, que es el tope inicial del Task 6— y (b) cuántos tests
      rompen, que con el trinquete debería ser **cero o casi**. Si (b) no es casi cero, el trinquete
      no está donde creo y hay que averiguar por qué antes de seguir.
- [ ] Los dos números van **escritos en este plan**, no en el chat. Un radio que solo existió en
      una conversación no se puede comparar con el de después.
- [ ] Precedente del método: el Task 6 de la Fase 1 midió **377 roto antes / 18 después** antes de
      invertir un default. Medir dos veces es lo que hizo esa migración barata.
- [ ] La fixture del mutex en tests es **explícita, no `autouse`**: los tests que quieran afirmar
      que una escritura está protegida tienen que tomarlo a la vista. Una fixture `autouse` haría
      invisible la exigencia, que es la «exención por omisión» que el §25 existe para eliminar.

## Task 4: Los entrypoints adquieren

- [ ] `scripts/abrir_caso.py`, `scripts/sala_maquina.py`, `scripts/sync_sudespacho.py` y las vías
      de intake de `streamlit_app.py` envuelven su trabajo en `sostenido(w, ahora_fn=now_iso_utc)`.
- [ ] `--modo v1` adquiere **una vez**, y las etapas que llame se unen. Ese anidamiento es la
      razón de ser del Task 1 y se prueba con un test que recorra las dos capas.
- [ ] Un entrypoint que no pueda derivar W-code en `--modo v1` **aborta** (C6).

## Task 5: Migrar las filas de 3A a la costura

- [ ] #6 y #9 (clase contenido, las **dos** que ya consultan el guard): añadir mutex, sin cambiar
      su comportamiento de desvío.
- [ ] #4, #5, #7, #10, #11, #12, #13 (protocolo): pasar por la costura con `clase="protocolo"`,
      lo que convierte su exención de **omisión** en **declaración**.
- [ ] #5 además **debe consumir la decisión del guard**: hoy escribe los ids de Drive en `_caso.md`
      tras un desvío como si no lo hubiera habido.
- [ ] #8 queda **abierto y declarado** hasta 3C: hashea el cajón canónico y no el destino efectivo.
      No se cierra aquí porque su remedio es que el hash consuma el `destino` de la costura, y eso
      es la fila de 3C.

## Task 6: El censo permanente

- [ ] Guard AST que comprueba que producción entra por `mutex_sesion.sostenido`, no por
      `case_mutex.tomado` en crudo.
- [ ] Censo de escrituras que no pasan por la costura, con la cifra **actual** como tope: 3B y 3C
      la bajan. Un censo sin número es una intención.
- [ ] El guard **no puede depender de números de línea**: la lista indexada por línea del Task 6
      de la Fase 1 caducó a mitad de su propia migración.
- [ ] Prueba de mutación del propio guard: un guard sin prueba de que muerde no es un guard.

---

## Criterio de salida de 3A

1. `vigente()` distingue los tres estados, y la costura los trata distinto.
2. Un `sostenido()` anidado no se bloquea contra sí mismo, y no arranca un segundo latido.
3. Las diez filas de 3A pasan por la costura; las doce de protocolo están exentas **por
   declaración**.
4. El censo del Task 6 da un número **escrito**, y el guard muerde bajo mutación.
5. `--modo v1` **rechaza** una escritura sin mutex. Si no lo hace, el mutex sigue sin proteger
   nada y 3A no ha cerrado, aunque todo lo demás esté verde.
6. Suite verde con **dos semillas** (`pytest-randomly`). Una corrida no dice nada sobre orden.
7. 14 mutantes, uno por frontera, con arnés que falla si un ancla no casa.

**Lo que 3A NO permite declarar:** «el write-set está protegido». Al cerrar 3A lo estarán las diez
filas de esta tanda en `v1`, y el resto seguirá contado en el censo. La frase honesta es «el mutex
protege las diez filas de 3A», y el número del censo dice cuánto falta.

## Lo que este plan deliberadamente NO hace

- **No toca `case_mutex.py`.** Cuatro rondas y 17 mutantes; se envuelve, no se edita.
- **No migra los diez derivados** (3B) ni cambia la poda (3C).
- **No cierra el orden durable, la monotonía de observación ni el snapshot por ronda** (§25.5):
  esos son contratos del Plan 4 y siguen abiertos.
- **No encadena la secuencia de V1** (Plan 5). `--modo v1` sigue siendo una puerta; aquí
  simplemente adquiere el mutex al pasarla.

## Lo que sigue SIN VERIFICAR, y se declara

- **La reacción del mutex a un salto real de NTP.** Heredado del §3.5 del plan del mutex, sin
  cerrar. Nada de 3A lo cierra: la cota simétrica de R13 acota el `ahora` **inyectado**, no un
  salto del reloj del sistema entre dos latidos.
- **Las seis remediaciones de R13 no tienen ronda propia.** Declarado en el 70º cierre. 3A las
  usa (`revalidar()` con cota contra el lease es una de ellas) sin haberlas revisado.
- **El censo del Task 6 mide llamadas, no cobertura semántica.** Un llamador que pase por la
  costura y luego escriba en otra ruta pasa el censo. Es el hueco de #8 y lo cierra 3C.
