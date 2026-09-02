---
tipo: plan
objeto: "MEJORAS #124 — quién contesta «¿cuál es la copia de trabajo?» en el camino de escritura"
estado_remediacion: pendiente
creado: 2026-09-02
---

# `MEJORAS #124` — la copia de trabajo la contesta el resolver, y la capacidad la transporta (rev. 2)

> ## ✅ ALCANCE RECORTADO Y CONSTRUIDO. La rev. 2 sigue `NO-EJECUTABLE` y no se construye.
>
> **Decisión de Nikolai del 2026-09-02, tras R24: recortar en vez de escribir una rev. 3.** Lo
> construido es el **§10**: `deposito()` acepta un `CaseWorkspace` **ya resuelto por el llamador**.
> Cierra `H18-01`. Los §§1-9 se conservan como el diseño que las dos rondas tumbaron — no describen
> lo que hay en el árbol.
>
> **Cobertura de revisión de la última remediación: AUSENTE**, y mergeado con esa declaración
> (decisión de Nikolai). Ver §12.3.
>
> **R24 devolvió `NO-EJECUTABLE`: 12 hallazgos, 12 confirmados, 0 refutados, 3 críticos.**
> Adjudicación en el **§9**; acta en `docs/superpowers/specs/2026-09-02-mejoras-124-r24-adversarial-review.md`.
>
> **Es el segundo `NO-EJECUTABLE` sobre esta pieza, y con él se agota su presupuesto de rondas sin
> una línea de código.** La decisión que toca no es escribir una rev. 3: es la del §9.4, y es de
> Nikolai.
>
> **Lo que NO sobrevive, y hay que leerlo antes que nada:** el «teorema» del §1 es **falso**
> (§9.1), y el criterio 1 del §7 es **insatisfecho por construcción** con el entrypoint que el §6
> elige (§9.2). Los §§1-8 se conservan tal como los revisó R24.
>
> **Presupuesto de rondas: 2.** La pieza decide **quién puede escribir sobre qué copia**. R21 se
> gastó en la rev. 1 y **no cuenta como cobertura de ésta**: lo que revisó ya no es el diseño que
> hay. Queda **una ronda sobre este documento** antes de escribir código, y una sobre el diff.
> Ese reparto lo decide Nikolai, no yo.

> **Qué cambió desde la rev. 1, y no es cosmético.** El punto 1 del §8.4 —la invariante del
> registro— está **cerrado y mergeado**: `MEJORAS #136`, PR #255, `9c947ba`, con dos rondas
> adversariales propias. Sin él, `es_canon` no discriminaba nada y el resto del diseño colgaba del
> aire.

---

## 1. Lo que #136 cambió para este plan, que es más de lo que parece

**`MEJORAS #124` pasó de accidente a teorema.** Antes, `es_copia_prestada` devolvía `False` siempre
por una coincidencia de dos hechos que podían dejar de serlo. Ahora:

- `case_locator.buscar()` devuelve **solo** rutas bajo `CASOS_ROOT`.
- El registro **no puede** contener rutas bajo `CASOS_ROOT`: se rechaza al escribir
  (`WorkspaceRegistry._escribir`) y se filtra al leer (`_visibles`), con 14 mutantes que lo
  contratan.

La intersección de los dos conjuntos es **vacía por construcción**. `es_copia_prestada` no es
«inerte hoy»: es **demostrablemente `False` siempre**. Eso cierra la discusión sobre si conviene
arreglarlo — no hay nada que arreglar ahí dentro, la función pregunta lo imposible.

**Y de paso desaparece el riesgo que hacía urgente esta rev. 2.** La rev. 1 avisaba de que arreglar
el discriminante en solitario sería una regresión. Ya no es posible cometerla: la vía por la que el
canon entraba al registro está cerrada.

---

## 2. Lo medido hoy, sobre `9c947ba`

### 2.1. La «puerta única» no tiene puerta

`core/casos/escritura.deposito()` —la costura que 3A construyó, con 18 tests y 12 mutantes— tiene
**cero llamadores en producción**. Censo por AST sobre `core/`, `scripts/` y `streamlit_app.py`.

Es la misma enfermedad que el mutex antes de 3A: construida, probada y **sin cablear**. La rev. 1
daba por hecho que la puerta existía y solo había que enseñarle a resolver; existe la pieza, no la
puerta.

### 2.2. El censo transitivo del §8.4 punto 4, por consumidor

Siete puntos consultan el guard (dos directos, cinco vía `dir_intake`). En **sus mismos módulos**
hay **28** llamadas que resuelven el expediente por `case_id` —o sea, contra el canon—:

| Módulo | guard | transitivas por canon |
|---|---|---|
| `case_manager.py` | 1 | `caso_path`×5, `append_event`, `localizar`, `read_bucket_overrides` |
| `intake_drive.py` | 1 | `register_drive_ev`, `cache_drive_folder_info`, `localizar` |
| `intake_lotes.py` | 1 | `caso_path` |
| `intake_manual.py` | 1 | `caso_path`×3, `IntakeManifest`, `localizar` |
| `sync_sudespacho.py` | 1 | `IntakeManifest`, `RegistroOcurrencias`, `crm_branch_path`, `update_pull_state`, `caso_path`×2, `read_bucket_overrides` |
| `whatsapp_intake.py` | 1 | `IntakeManifest`, `append_event`, `localizar` |
| `casos/escritura.py` | 1 | `localizar` ← **H18-01** |

**Mover solo los bytes parte el expediente**: los bytes irían a la copia local y el manifiesto, las
ocurrencias, el estado del pull y la ficha se quedarían en el canon.

### 2.3. Una ausencia que el censo destapa y que no estaba en ningún informe

**`core/email_export.py` no consulta el guard.** Sus bytes pasan por él de rebote —usa
`reservar_lote`, que llama a `dir_intake`— pero su `IntakeManifest(case_id)` no. O sea que ya hoy,
sin tocar nada, un caso prestado deja los bytes en la bandeja del canon y el manifiesto apuntando a
`00_Input`. Es la misma partición que el §2.2 anticipa, **ocurriendo ya**.

No es de este plan arreglarlo —es la fila #17, `MEJORAS #126`— pero sí lo es contarlo: el censo del
§2.2 mide «quién llama al guard», y la superficie real es «quién escribe en el expediente».

---

## 3. Los cinco puntos del §8.4

| # | Punto | Estado |
|---|---|---|
| 1 | la invariante del registro | ✅ **cerrado y mergeado** (`MEJORAS #136`, PR #255) |
| 2 | resultado que transporta autorización + destino sin exponer la raíz | §4.1 |
| 3 | tabla cerrada error→resultado, con un tipo que sepa decir «no hay raíz» | §4.2 |
| 4 | censo transitivo por consumidor | §2.2, y el reparto en §5 |
| 5 | F3 reformulada y matriz por escenarios | §4.3 y §5 |

---

## 4. El diseño

### 4.1. El tipo que transporta las dos cosas ya existe, y no es `Destino`

**Se retira `Destino`.** La rev. 1 inventaba un valor con `raiz: Path` público, y R21/H21-02 tenía
razón dos veces: no podía transportar el veredicto —le faltaban `ruta_relativa`, `origen` y
`es_protocolo`, que es de lo que depende `decidir_escritura`— y exponer un `Path` reabría lo que 3A
había cerrado por escrito (*«si devuelve un `Path`, el llamador escribe donde quiera»*).

**La puerta es `deposito()`**, que ya devuelve una capacidad con base privada. Lo único que le falta
es resolver **dónde**:

```python
# hoy   — solo sirve para el canon (H18-01)
case_dir = CaseCatalog().localizar(ref)

# rev. 2 — la raíz sale del resolver, y sigue siendo privada
ws = resolver.resolver_por_identidad(ref, drive_accesible=..., diagnostico=True)
```

> **D124 (rev. 2).** La autorización y el destino salen de la misma resolución **y viajan dentro de
> una capacidad que efectúa la escritura**. No hay API que entregue la raíz.

Esto cierra **H18-01** por el camino: la costura de 3A deja de servir solo al canon.

### 4.2. La tabla cerrada de resolución → resultado

R21/H21-03 pedía «un tipo capaz de representar “no hay raíz” sin fingir un canon». **La respuesta no
es un tipo: es que no se entregue capacidad.** Una capacidad que no puede escribir no debe existir —
es la doctrina que `escritura.py` ya aplica.

| Resolución | `modo="v1"` | `modo="libre"` |
|---|---|---|
| `DRIVE_ACTIVE` | raíz = canon, reglas de desvío vigentes | igual |
| `LOCAL_CHECKOUT` / `LOCAL_SCRATCH` | raíz = `working_root`, **sin bandeja** | igual |
| `BLOCKED_CONFLICT` / `BLOCKED_FOREIGN_CHECKOUT` | **aborta** | raíz = canon + desvío (conducta de hoy) |
| `AmbiguousCase` | **aborta** | **aborta** |
| `LockMismatch` | **aborta** | **aborta** |
| `RegistryUnreadable` / `SchemaNoSoportado` | **aborta** | **aborta** |
| `LocalWorkspaceMissing` con canon conocido | raíz = canon | igual |
| `LocalWorkspaceMissing` sin canon | **aborta** | **aborta** |
| offline sin checkout verificado | **aborta** | **aborta** |

**Por qué `libre` no aborta en los `BLOCKED_*` y sí en el resto.** Un caso prestado a otra máquina
es el estado **normal** que el guard existe para gestionar, y hacerlo abortar convertiría la pantalla
diaria de Paola y Ana en un fallo duro. Los demás son **errores de custodia**: ambigüedad de
identidad, nonce que no casa, registro no confiable. Ahí «seguir en el canon» no es prudencia, es
escribir sin saber sobre qué.

**Ambigüedad y `LockMismatch` abortan en los dos modos, y eso es un cambio de conducta declarado**
respecto de hoy, donde `guard_escritura` desvía sin mirar nada de eso.

### 4.3. F3, reformulada

La rev. 1 decía «`es_canon=True` y canon `prestado`/`conflicto` ⇒ **siempre** desvío». **Es falsa**
(R21/H21-05): `decidir_escritura` exime al protocolo **antes** de mirar el estado, y `deposito` hace
alcanzable ese valor con `clase="protocolo"`.

> **F3 (rev. 2).** Sobre el **canon** y con el caso `prestado`/`conflicto`, **toda escritura no
> protocolaria** se desvía. La exención del protocolo es una frontera **propia**, con su propio
> mutante.

---

## 5. Las fronteras, y cómo se prueban

**Por escenarios productivos, no por producto cartesiano** (R21/H21-07): el modo **es función** del
estado, así que una tabla modo × estado fabricaría celdas que producción no genera — el mismo
defecto que la fixture que este plan denuncia. Cada escenario se obtiene **llamando al resolver
real**.

| F | Frontera | Mutante observable |
|---|---|---|
| F1 | la raíz sale del resolver, no de `localizar` | volver a `CaseCatalog().localizar` ⇒ los bytes caen en el canon con checkout vivo |
| F2 | la capacidad **no** expone la raíz | añadir una propiedad pública que la devuelva ⇒ guard AST |
| F3 | sobre el canon prestado, toda escritura **no protocolaria** se desvía | invertir la condición |
| F3-bis | y el **protocolo** está exento | quitar `es_protocolo` de la llamada |
| F4 | sobre copia local, **cero** bandeja y los bytes en `working_root` | forzar `desviar=True` |
| F5 | error de custodia ⇒ **aborta**, en los dos modos | degradarlo a desvío |
| F6 | `BLOCKED_*` en `libre` ⇒ conducta de hoy, sin excepción | dejar escapar `CaseLocked` ⇒ revienta Streamlit |
| F7 | `deposito` tiene llamadores **de producción** | censo AST con tope que solo baja |

**F7 es la frontera que la rev. 1 no tenía y el §2.1 obliga a poner.** Sin ella, este plan puede
declararse cumplido con la puerta perfecta y ningún cliente — que es exactamente lo que le pasó al
mutex de 3A y a `deposito` mismo. El tope del censo **solo baja**, como el `TECHO_CENSO` de 3A.

---

## 6. Los Tasks

**T1 — `deposito` resuelve por workspace.** La tabla del §4.2 completa. Cierra **H18-01**. Mutantes
F1, F4, F5, F6.

**T2 — F3 y su exención**, con los dos mutantes separados (F3, F3-bis).

**T3 — El primer llamador real.** `abrir_caso --modo v1` deposita por la costura. Sin esto el plan
no ha cambiado nada: es el criterio de salida, no un adorno. Mutante F7.

**T4 — El guard AST de la raíz privada** (F2) y el censo de llamadores con tope (F7).

**T5 — Los cuatro `xfail` de `test_guard_copia_prestada.py`.** Se revisan **uno por uno**: la rama
que describen vuelve a estar viva, así que o pasan —y se retira el marcador— o la promesa era otra y
se reescribe. `xfail(strict=True)` los pondrá en rojo al pasar, que es la señal.

**T6 — `es_copia_prestada` desaparece**, con guard AST. Ya no pregunta nada: el §1 lo demuestra.

**T7 — El censo transitivo (§2.2) NO se migra aquí.** Se enumera, se le pone tope y se reparte entre
3B y 3C. Ver §7.

---

## 7. Criterios de salida

1. Un caso **prestado a esta máquina** recibe el intake en su **copia local**, verificado **por
   hash de los dos árboles**: bytes en la copia, canon intacto, bandeja vacía.
2. Un caso prestado a **otra** máquina sigue desviando a la bandeja del canon, en `libre` — la
   conducta de hoy, sin cambio.
3. En `v1`, un error de custodia **aborta con cero bytes escritos**, verificado por hash.
4. `deposito` tiene **≥1 llamador de producción** y el censo tiene tope.
5. Los siete mutantes (más F3-bis) mueren, **cada uno por su frontera**, con el manifiesto
   ejecutable en el repo — como `tests/_mutantes_mejoras_136.py`, que existe porque decirlo en un
   commit no es verificable.
6. Suite verde con **dos semillas**. Base de hoy: **3.735 / 0 / 0 / 87**, `XFAIL 10`, `XPASS 0`.
7. Los cuatro `xfail` de `#124` **resueltos en una dirección u otra**, ninguno en silencio.

---

## 8. Lo que este plan NO hace

- **No migra las 28 escrituras transitivas** (§2.2). Las enumera y las reparte; migrarlas es 3B/3C.
- **No arregla `email_export`** (§2.3), que es la fila #17 / `MEJORAS #126`.
- **No toca `case_mutex.py`** — cuatro rondas y 17 mutantes.
- **No cierra la fila #5** (3A-bis), que sigue esperando su propia rev. 2 y ahora tiene la respuesta
  que le faltaba.
- **No resuelve UNC ↔ letra de unidad**, límite heredado de `#136` y **sin verificar**.

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

---

## 9. Adjudicación de la revisión adversarial (Codex, 2026-09-02) — NO-EJECUTABLE, pendiente

- **Objeto revisado:** la rev. 2 de este plan, commit `b01dabe`
- **Ronda:** R24 (diseño, antes de escribir código)
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-02-mejoras-124-r24-adversarial-review.md`
- **Hallazgos:** 12 — 3 CRÍTICOS, 8 ALTOS, 1 BAJO; **12 confirmados, 0 refutados**
- **Remediado en:** nada todavía; ver §9.4

### 9.1. El «teorema» del §1 es falso, y lo reproduje

Afirmé que `es_copia_prestada` es demostrablemente `False` **siempre**. No lo es:

```
buscar('..\workspace')    : <CASOS>\..\workspace   ← escapa del catalogo
es_copia_prestada         : True
guard: permitido/desviar  : True / False            ← permite SIN desviar
```

`buscar()` compone `root / case_id` **sin validar** que `case_id` sea un nombre simple, y
`resolve_ref` devuelve sin tocar lo que no reconoce. Alcanzable: `export_label_emails.py` toma
`--ref` como texto libre.

**Es la afirmación que más me convenía que fuera cierta** —cerraba el §1 con un resultado fuerte— y
la escribí sin sondearla, razonando sobre dos conjuntos en vez de medir la función. La lección no es
«validar el `case_id`»: es que **un teorema sobre código se prueba ejecutándolo**, y yo tenía la
sonda escrita desde R21.

**Calibración de la severidad, que el informe no hace:** son CLI locales, no un servicio expuesto.
El riesgo real es el **error de operador**, no un atacante. Va a `MEJORAS #141` con esa lectura.

### 9.2. Los otros dos críticos, y los dos son contradicciones internas

**H24-02.** La fila «`BLOCKED_*` en `libre` ⇒ raíz = canon + desvío» **no se puede construir**:
`CaseWorkspace` prohíbe por invariante que un modo bloqueado lleve raíz, y `diagnostico=True`
devuelve `working_root=None`. Para cumplirla haría falta una segunda resolución — que es justo lo
que **D124 prohíbe**. Es la misma clase que R21/H21-03: la cerré para los *errores* y no para los
*bloqueos*.

**H24-03.** El criterio 1 exige «canon intacto, verificado por hash», y el único entrypoint que el
§6 caba (`abrir_caso --modo v1`) llama a `pull_drive_ev`, que sella el `_caso.md` canónico — un
efecto que **mi propio §8 excluye**. El criterio y la exclusión se contradicen dentro del mismo
documento.

### 9.3. Y una cita heredada que no comprobé

**H24-04.** Escribí que la capacidad «no expone la raíz», repitiendo la doctrina de 3A. Pero
`dir_para(".")` devuelve la base y `escribir_texto`/`escribir_bytes` devuelven el `Path` escrito.
3A no *devuelve* la raíz; entrega un directorio dentro de ella. **Séptima aparición de «el nombre de
una cosa no es la cosa»**, y la primera en que la frase no comprobada era de mi propio repo — que es
peor, porque una cita interna se lee como verificada.

### 9.4. La decisión que toca, y es de Nikolai

**El presupuesto de esta pieza está agotado**: dos rondas, las dos de diseño, las dos
`NO-EJECUTABLE`, cero líneas de código. El §13 de `PLAN.md` previó este punto exacto — *«cuántas
rondas come un documento antes de que la conclusión razonable sea recortar alcance en vez de revisar
otra vez»*—, y escribir una rev. 3 sería justo el movimiento que ese ítem existe para frenar.

**Lo que los doce hallazgos dicen en conjunto no es que el diseño esté mal ejecutado, sino que es
demasiado ancho.** Intenta a la vez: redirigir los bytes, cubrir todos los desenlaces del resolver,
conservar la conducta de Streamlit, desbloquear la fila #5 y entregar un E2E — y H24-03 demuestra
que dos de esos objetivos son **incompatibles** con sus propias exclusiones.

**Las opciones, sin elegir aquí:**

1. **Recortar a lo que sí cierra una propiedad**: que `deposito()` acepte un workspace **ya
   resuelto por el llamador**, dueño de la resolución y de sus errores — que es exactamente lo que
   `sala_maquina` ya hace hoy. Cierra **H18-01**, no necesita la tabla del §4.2 (los errores los
   trata el entrypoint), no promete E2E y no toca la fila #5. Una frontera, un task.
2. **Rev. 3 con los doce puntos**, aceptando una tercera ronda de diseño sobre la misma pieza —
   que el techo duro prohíbe sin autorización expresa.
3. **Aparcar `#124`** y dejar la fila #15 avanzando por otro lado.

**Mi recomendación es la 1**, y no por prudencia: porque es la única de las tres que produce código
esta semana, y porque las dos rondas coinciden en que el problema del diseño es el **alcance**, no
el detalle.

**No se pide tercera ronda.**

---

## 10. El alcance recortado, que es lo que existe en el árbol

Las rev. 1 y 2 querían que la costura **resolviera** el workspace. R21 y R24 las tumbaron con 20
hallazgos confirmados y **las dos coincidieron en que el problema era el alcance**. Lo que se
construyó es una sola propiedad:

> `deposito(ref, …, workspace=…)` escribe bajo `workspace.working_root`. **Quien resuelve es el
> llamador**, que tiene el contexto y ya sabe tratar los errores del resolver — como
> `scripts/sala_maquina.py` hace desde el Task 9 de la Fase 1.

Sin `workspace`, la conducta es la de siempre. Cierra **H18-01**: hasta hoy la costura de 3A solo
servía para el canon.

**Primer cliente de producción:** `sala_maquina`, en `apply` y `reforzar`. **No mueve un byte de
sitio** —ya escribía en `ws.working_root`—; lo que gana es pasar por la puerta, y lo que gana el
proyecto es que la puerta deje de tener cero clientes, que era la frontera **F7** que la rev. 2
añadió tras medir que `deposito()` no lo llamaba nadie.

### 10.1. Las dos cosas que el diseño destapó y ningún informe traía

1. **Una copia local no tiene `_caso.md`** (`MERGE_EXCLUSIONS`). Cambia dónde caen los **bytes**,
   no dónde vive la **prueba** de identidad — que sigue siendo `meta.id_go` del canon.
2. **La bandeja vive en el canon.** Sobre una copia local no se consulta el guard, y el
   discriminante es el **modo** que el llamador resolvió. Eso lo deja inmune a `MEJORAS #141`,
   porque el modo no depende de clasificar una ruta.

---

## 11. Adjudicación de la revisión adversarial (Codex, 2026-09-02) — NO-SHIP, remediado

- **Objeto revisado:** el diff del alcance recortado, commit `5e75553`
- **Ronda:** R25
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-02-mejoras-124-r25-adversarial-review.md`
- **Hallazgos:** 8 — 1 CRÍTICO, 5 ALTOS, 2 BAJOS; **8 confirmados, 0 refutados**
- **Remediado en:** `6c42102`, `43471be`

### 11.1. Una regresión mía, nacida de una frase sin comprobar

Escribí que «el resolver ya validó la identidad contra el canon». **Es falso**: el resolver conserva
el `CaseRef` **pedido** sin enriquecerlo. Medido:

```
via HISTORICA (sin workspace) : rechazada IdentidadDiscordante
via NUEVA (con workspace)     : ACEPTADA — escribe en el canon real con el W-code falso
```

**Mi cambio abría una puerta que el código ya tenía cerrada.** La frontera es la contraria de la que
escribí: el `case_ref` de un workspace es la **petición**, no la **prueba**.

R25 midió además que **mis tests no protegían el cableado**: mutó los cuatro `dep=_dep_sala` y los
diez pasaron, porque llamaban a los *helpers* y no a los *comandos*.

---

## 12. Adjudicación de la revisión adversarial (Codex, 2026-09-02) — NO-SHIP, remediado

- **Objeto revisado:** el diff remediado tras R25, commit `43471be`
- **Ronda:** R26
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-02-mejoras-124-r26-adversarial-review.md`
- **Hallazgos:** 6 — 1 CRÍTICO, 2 ALTOS, 2 MEDIOS, 1 BAJO; **6 confirmados, 0 refutados**
- **Remediado en:** `db6e4a3` (5 de 6; el sexto declarado sin cubrir en el §12.2)

### 12.1. Cerré el ejemplo, no la frontera — por quinta vez

Tres graves, los tres míos:

- **H26-01 (CRÍTICO).** Contraté «la raíz local no puede ser *el* canon de este caso». La propiedad
  es **«está fuera del catálogo entero»**. Un workspace local del caso A apuntando al canon de B
  escribía en B **sin desviar**, con B prestado a otra máquina.
- **H26-02.** Usé la petición como respaldo de la identidad **tres líneas debajo** del docstring que
  dice que la petición no es prueba. Mi vía seguía siendo más permisiva que la histórica.
- **H26-03.** Los `case_id` se fusionaban con un `or` sin compararse, y al localizar se descartaba
  el W-code.

**Y H26-04 invalidaba mi evidencia:** `ensure_case` escribe `id_go: null`, mi fixture comprobaba
`if "id_go" not in txt` —la cadena sí estaba— y el valor real nunca entraba. Los 26 tests pasaban
por el **nombre de la carpeta**. Arreglar la fixture **no bastó**: hizo falta un caso con nombre
neutro para que el mutante del metadato muriera. Tercera vez en esta pieza que un verde no probaba
lo que decía.

### 12.2. Lo declarado sin cubrir

**H26-05**: no hay test de comando para `reforzar`, ni canario de propagación de
`IdentidadDiscordante`, ni canario en `plan`. Son **regresiones posibles sin test**, no defectos
vivos: el arnés del revisor comprobó que los tres caminos se comportan bien hoy.

### 12.3. Por qué se mergea sin una tercera ronda

**La pieza gastó sus dos rondas** (R25, R26), las dos `NO-SHIP`. Una tercera exige autorización
expresa de Nikolai, y **no se pidió**: el argumento «pero la última encontró un crítico» es el que
`CLAUDE.md` identifica como el que nunca se agota.

Los dos datos que sostienen la decisión, que es suya:

1. **El coste de un defecto residual es hoy casi cero.** Nada en producción escribe por esta vía
   salvo `sala_maquina`, que ya escribía donde escribe. Los tres defectos de R26 solo eran
   alcanzables construyendo un `CaseWorkspace` a mano; ningún entrypoint los produce.
2. **Seis rondas en la sesión, ninguna limpia, y cada remediación mía dejó la misma frontera abierta
   por otro lado.** El rendimiento por ronda no cae, lo que sugiere que el problema no es cuánto se
   revisa sino que estoy iterando sobre una pieza cuyo espacio de estados no controlo.

La alternativa que se dejó anotada y **no** se tomó: partir la pieza en dos —la invariante modo/raíz
y la regla de identidad son propiedades independientes, y cada arreglo de una rompió la otra—.

---

## 13. La partición: dos propiedades, dos módulos

`MEJORAS #124` recibió **cuatro rondas y ninguna volvió limpia**, y el §12.3 dejó anotada —sin
tomar— la alternativa: **partir la pieza**. Se tomó el 2026-09-02.

| | Propiedad | Dónde | ¿Necesita identidad? |
|---|---|---|---|
| **A** | local ⇒ **FUERA** del catálogo · `drive_active` ⇒ **DENTRO** · lo indeterminado se rechaza en los dos | `core/casos/ubicacion.py` | **no** |
| **B** | el W-code se prueba contra `meta.id_go` del canon; y la raíz de un `drive_active` es el expediente **correcto** | `escritura._identidad_de_workspace` | sí |

**Lo que aparece al partirlas, y explica las cuatro rondas: la ubicación no necesita saber qué caso
es.** La versión acoplada preguntaba «¿es *el* canon de *este* caso?», que sí lo necesita, y por eso
las dos vivían en una función compartiendo `canon_dir`. Enunciada como pertenencia al catálogo, los
dos defectos de R26 —el canon de otro caso y un descendiente— dejan de ser excepciones: son el mismo
caso de la misma frontera.

**Condición de cierre ejecutable:** `python -m tests._mutantes_particion_124` — **diez mutantes**,
y cada uno mata **solo** tests de su propiedad. Que los dos ficheros pasen no demuestra nada.

---

## 14. Adjudicación de la revisión adversarial (Codex, 2026-09-02) — NO-SHIP, remediado

- **Objeto revisado:** el diff de la partición, commit `e05d5a6`
- **Ronda:** R27
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-02-mejoras-124-r27-adversarial-review.md`
- **Hallazgos:** 6 — 1 CRÍTICO, 2 ALTOS, 2 MEDIOS, 1 BAJO; **6 confirmados, 0 refutados**
- **Remediado en:** esta rama, todos

### 14.1. El crítico es una regresión que introdujo la propia partición

Un `drive_active` cuyo caso el catálogo **no conoce** escribía dentro del catálogo **sin identidad y
sin mutex**. Reproducido con sonda propia y cerrado con la misma:

```
antes    la RAIZ del catalogo     ACEPTADO | mutex=False | dentro del catalogo=True
         un directorio suelto     ACEPTADO | …
         la bandeja de OTRO caso  ACEPTADO | …
despues  las tres                 rechazado: IdentidadDiscordante
```

**El mecanismo, que es la lección:** la función acoplada rechazaba ese estado porque recibía
`canon_dir` y comprobaba `canon_dir is None or raiz != canon_dir`. Al partirla, `ubicacion` se quedó
con «¿está DENTRO?» —cierto para la raíz del catálogo— y la mitad de identidad se saltaba por el
retorno temprano de «el catálogo no conoce este caso».

> **Al partir una función hay que preguntarse qué rechazaba la unión que no rechaza ninguna de las
> partes.** No lo pregunté.

### 14.2. Y un hallazgo que invalidaba mis propias afirmaciones

**H27-04:** el arnés de partición ignoraba el código de salida de pytest, así que un error de
colección devolvía el conjunto vacío — o sea «cero fallos», o sea **baseline verde**. El revisor lo
reprodujo apuntándolo a un fichero inexistente.

Es la clase «una búsqueda mutilada leída como ausencia»: *«no hay fallos»* y *«no pude ejecutar»* se
veían igual. Y significa que **«cero mutantes cruzan» pudo haberse dicho sobre corridas que no
ejecutaron nada**. Corregido y comprobado en las dos polaridades.

### 14.3. Los otros cuatro

| # | Sev. | Qué era |
|---|---|---|
| **H27-02** | ALTO | Dos mutantes suyos **sobrevivían**: el cableado de `ubicacion` para `drive_active` y la igualdad «el expediente correcto». Al mover los tests se perdió la integración canónica |
| **H27-03** | MEDIO | Un mutante suyo **cruzaba**: `TestModoBloqueado` es ubicación y vivía en identidad. Mi «cero cruzan» era cierto **de mis tres mutantes**, no de la propiedad — dije lo segundo habiendo medido lo primero |
| **H27-05** | MEDIO | El arnés escribía **fuera** del `try` y restauraba con `git checkout -- .`, que se lleva por delante cualquier cambio concurrente. Ahora guarda bytes, escribe dentro y restaura solo ese fichero, comprobándolo |
| **H27-06** | BAJO | `ubicacion` resuelve físicamente y la identidad compara léxicamente. **No se cambia**: la asimetría es deliberada —ubicación pregunta «¿pertenece?», donde un alias cuenta; identidad pregunta «¿es la forma canónica?», donde no— y ahora está **declarada** en el código |

### 14.4. Estado

**Diez mutantes, cero cruzan.** Suite **3.793 / 0 / 0**, 77 omitidos + 10 `xfailed`, `XPASS 0`, con
las semillas 777 y 31337.

**Cobertura de esta remediación: AUSENTE.** La pieza ha gastado **una** ronda de las dos que su radio
compra; la segunda está disponible sin techo duro, y la decisión de gastarla es de Nikolai.
