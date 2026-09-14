---
tipo: spec
estado: vigente
creado: 2026-09-14
objeto: scripts/session_close.py + docs/RUNBOOK_APERTURA_EXPEDIENTE.md + CLAUDE.md
rev: "1"
---

# P8 — Una sesión de apertura no toca el repo, y el cierre lo comprueba

Fila **#31** de `PLAN.md`. Origen: `handoff-2026-09-10-consulta-apertura-menos-decisiones.md` §P8.
Decisiones de Nikolai del **2026-09-13** (qué se acepta) y del **2026-09-14** (el aviso, y que
esto deja de ser solo proceso).

## 1. El problema, y su medición

Una sesión de apertura ejecuta el runbook: alta, intake, sala de máquina, sala de lectura,
viabilidad, ficha CRM, archivo. Por el camino encuentra defectos de **nuestro** código. Si se
pone a repararlos, pasan dos cosas a la vez: la apertura se alarga y el arreglo nace sobre la
base que la sesión tenía cargada, que no es `origin/main`.

**Está medido, y el caso es la fila #29.** Las **838 líneas** huérfanas que hubo que rescatar el
2026-09-13 eran exactamente eso: una sesión de apertura que se puso a reparar y dejó código sin
commitear sobre una base que para entonces estaba **21 commits atrás**. Al leerlas resultó que
hacían lo mismo que `verificar_apertura` C1/C2, construido un día después por otra vía. No se
perdió una idea: se perdió un día de trabajo y se ganó un duplicado.

## 2. Qué se acepta, y qué no

Decisión de Nikolai del 2026-09-13, sobre las cuatro sub-propuestas del handoff:

| | Propuesta | Decisión |
|---|---|---|
| (a) | La sesión de apertura **no toca el repo**: anota los defectos en un fichero de trabajo y los ficha **al final**, leyendo `origin/main` al escribir | **sí** |
| (b) | Como mucho **una** sesión de reparación en paralelo, dueña del código | **sí** |
| (c) | Las aperturas del día **en serie** en una sola sesión, o en lote con una cola que el CLI recorra | **aparcado** — es lo único que cuesta construir |
| (d) | En la bitácora, un bloque **«aperturas del día»** en vez de un cierre numerado por caso | **sí** |

**(a) se lee mal con facilidad, y conviene fijarlo:** «ejecuta el runbook» es el **sujeto**, no la
regla. Una sesión de apertura ejecuta el runbook por definición — eso es abrir un expediente. Lo
normativo es **«y no toca el repo»**. No es un requisito de ejecutar nada.

## 3. El agujero de (a), y por qué obliga a escribir código

(a) dice «los ficha **al final**». Nada obliga a ese «al final»: es un paso que depende de que
alguien se acuerde, y ése es el defecto más medido de esta casa — un hecho escrito que nadie
aplica, con **tres apariciones en cinco días**.

Sin disparador, el resultado previsible no es fichar tarde. Es que aperturas enteras terminen con
su fichero de trabajo sin leer, **que es peor que no haberlo anotado**, porque deja la sensación
de que el defecto está registrado.

**Decisión de Nikolai del 2026-09-14:** `scripts/session_close.py` **avisa** si existe un fichero
de apertura con defectos sin fichar. **Aviso, nunca verja** — igual que la cobertura del diff y la
coherencia de `PLAN.md`. La única verja sigue siendo la suite.

Consecuencia sobre la fila #31: **P8 deja de ser «proceso, no código»**. El trozo de código es
pequeño, pero existe, y su ronda se dimensiona **por el diff, no por la ruta**.

## 4. Dónde vive el fichero de trabajo

```
%LOCALAPPDATA%\FeesDefender\aperturas\<AAAA-MM-DD>_<W-code>.md
```

**El dato que decide la ruta:** el fichero lo escribe una sesión y el aviso lo dispara **otra**,
que puede correr días después, en otra rama y en otro worktree. La ruta tiene que ser computable
por las dos **sin coordinarse**. Eso descarta el resto:

| Sitio | Por qué no |
|---|---|
| dentro del caso (`01_Procesado/…`) | `session_close` no sabe de qué caso vienes. Y son notas sobre defectos de **nuestro** código dentro de la carpeta de un cliente que va a Drive y se comparte con E&V |
| dentro del repo, gitignorado | peor para encontrarlo: hay cinco raíces de worktree; la apertura escribiría en una y el cierre correría en otra. Y enturbia la regla: (a) dice «no toca el repo» |
| el scratchpad de la sesión | muere con la sesión — justo lo que hay que evitar |
| `90_Notas personales/` | zona del abogado; ningún módulo del core la lee ni la escribe |

**No es un hogar nuevo:** `%LOCALAPPDATA%\FeesDefender\` ya es donde vive el estado que queda
fuera del repo — lo usa `core/casos/workspace_registry.raiz_por_defecto()` para
`…\FeesDefender\workspaces`. Se reutiliza la convención, con su propia carpeta hermana.

**Lo que quedaba sin verificar, y lo cerró Nikolai el 2026-09-14:** si una apertura puede correr
en otro PC, en cuyo caso `%LOCALAPPDATA%` no viaja y el aviso callaría en la máquina equivocada.
«Las aperturas por el momento las hago yo», en este PC. La ruta local es segura **hoy**. Lo que la
rompería, para que conste: que abra otra persona, o que él abra desde otra máquina. **No se
arregla por anticipación, pero tampoco se da por eterno.**

## 5. El contrato del fichero

```markdown
---
caso: W-02UDC1
fecha: 2026-09-14
estado: pendiente
fichas: []
---

## El pull de Drive rellenó con ceros dos ficheros

Lo observado, con su medición …
```

- **`estado`**: `pendiente` · `fichado` · `descartado`. Sin este campo el aviso dispararía para
  siempre en cuanto existiera el primer fichero, y **un aviso que siempre salta es un aviso que
  nadie lee**.
- **`descartado`** es la salida del defecto que se decide **no** fichar (decisión de Nikolai,
  2026-09-14). Sin ella, el único modo de callar el aviso sería abrir un `MEJORAS #NN` por cada
  nimiedad, y un número de backlog es una reserva, no un vertedero. La alternativa que se
  descartó —una ventana temporal de N días— es **silencio por reloj**: deja caer un pendiente
  real sin que nadie lo decida.
- **`fichas`**: al pasar a `fichado`, la lista de `MEJORAS #NN` abiertos. Es lo que hace la
  operación **auditable**: se puede contrastar lo anotado con lo fichado.

**Quién lo escribe: la sesión de apertura, a mano, siguiendo el bloque literal del RUNBOOK.** No
se construye un escritor: no hay ninguno que lo pida hoy (YAGNI). El riesgo de que escritor y
lector diverjan lo cubre el guard del §7, no un módulo compartido.

## 6. El lector y el aviso

Ambos en `scripts/session_close.py`, junto a los otros cinco lectores del script
(`cobertura_del_diff`, `_plan_items_desfasados`, `_disenos_sin_traza`), que viven ahí y se
testean desde ahí. Se sigue el precedente en vez de abrir módulo.

**La raíz se INYECTA; la función que lee no tiene default.** Es la doctrina literal de
`workspace_registry`: la barrera de test cubre rclone y `subprocess`, **no** las escrituras al
perfil del usuario, así que un test que se olvidara de redirigirla escribiría en el
`%LOCALAPPDATA%` **real** — y chocaría con la regla de que ningún test escribe en el árbol de
producción. **Sin default no hay dónde caerse.** Para el llamador, `raiz_aperturas_por_defecto()`
resuelve `FEESDEFENDER_APERTURAS` → `LOCALAPPDATA` → `~/AppData/Local`.

**El lector devuelve DOS listas, no una:**

- `pendientes`: los `estado: pendiente`, con su caso y su fecha.
- `ilegibles`: los que **no se pudieron interpretar** — sin frontmatter, YAML roto, `estado:`
  desconocido, `caso:` ausente.

Un fichero ilegible **no se cuenta como pendiente ni se traga en silencio**: se declara aparte.
Es la lección de la pieza A de la fila #27 —la custodia declara lo que no pudo leer— y aquí es
exacta: un frontmatter que alguien tecleó mal es justo el caso que, tragado, deja el defecto sin
fichar creyendo que está fichado.

**Cuatro detalles que, sin fijar, los decidiría el código por su cuenta:**

1. **Qué ficheros mira:** los `*.md` de la carpeta, **sin recursión**. Cualquier otra cosa que
   haya ahí se ignora sin declararla — no es un fichero de apertura mal escrito, es que no es uno.
2. **La fuente es el frontmatter, no el nombre del fichero.** El nombre es nombre. `caso:` o
   `fecha:` ausentes hacen el fichero **ilegible**, sin derivarlos del nombre: derivar taparía
   justo el error de tecleo que este lector existe para enseñar, y dejaría un fichero medio
   escrito pasando por bueno.
3. **`estado` se compara en minúsculas y sin espacios alrededor.** `Pendiente` y `pendiente ` son
   el mismo estado; cualquier otro valor es **ilegible**, nunca «fichado por defecto» — la
   dirección del fallo importa: ante la duda, el aviso habla.
4. **`fichas` no lo lee el aviso.** Es para auditar a mano lo anotado contra lo fichado. Que esté
   vacía en un fichero ya `fichado` no dispara nada: sería una verja disfrazada de aviso.

**El aviso:**

- Imprime la sección **solo** si hay pendientes o ilegibles. Si no hay nada, o la carpeta no
  existe, **silencio total** (decisión de Nikolai, 2026-09-14): una cabecera vacía en cada cierre
  es exactamente el aviso que nadie lee. La carpeta ausente es además el caso normal de cualquier
  máquina que nunca haya abierto un expediente.
- Va envuelto en `try/except` en `main()`, con el comentario de la casa: **el aviso nunca debe
  romper el cierre**.

## 7. El guard que ata el documento al código

`tests/test_guard_formato_apertura.py` **extrae del RUNBOOK el bloque de frontmatter literal** y
se lo pasa al lector. Si alguien cambia el formato en la prosa y no en el código —o al revés—,
rojo.

Sin él, (a) es una regla escrita que nada aplica, y el formato del fichero viviría en dos sitios
que nadie compara. Es el mismo patrón que ya usan los guards de gobernanza: el documento
normativo es la fuente, y el test la verifica contra el código.

## 8. Tests, y el control positivo que el silencio obliga a tener

El silencio total tiene un coste conocido y hay que pagarlo en la suite: **un lector roto es
indistinguible de un lector que no encuentra nada**. Esta casa lo tiene medido dos veces («el
instrumento que no puede dar el otro valor», «el guard que mide y solo susurra»). El remedio no es
imprimir siempre —eso es lo que se acaba de descartar—: es que la prueba de que el instrumento
muerde la dé el test, no la salida diaria.

Casos que la suite debe cubrir:

1. **Control positivo:** una carpeta con un `pendiente` produce aviso. Sin este test, todos los
   demás pueden pasar con un lector que devuelve siempre vacío.
2. `fichado` y `descartado` **no** avisan.
3. Un frontmatter roto sale por `ilegibles`, **no** por `pendientes`, y **no** revienta.
4. `estado:` con un valor desconocido cuenta como **ilegible**, no como fichado.
5. Carpeta inexistente: cero, cero, sin excepción.
6. El aviso no rompe `main()` si el lector lanza.
7. El guard del §7: el bloque del RUNBOOK lo parsea el lector.
8. Un fichero que no es `.md` se ignora **sin** aparecer en `ilegibles`, y un `.md` de una
   subcarpeta no se mira.
9. `caso:` ausente → `ilegible`, **aunque el nombre del fichero lleve el W-code**. Es el test que
   impide que alguien «arregle» el lector derivándolo del nombre.
10. `Pendiente ` (mayúscula y espacio) cuenta como pendiente; `archivado` cuenta como ilegible.

**Ningún test toca el `%LOCALAPPDATA%` real**: todos reciben `tmp_path` por inyección, que es
para lo que la raíz se inyecta.

## 9. Lo documental: (a), (b) y (d)

- **(a)** → `RUNBOOK_APERTURA_EXPEDIENTE.md` §0 (entrada nueva `[APER-73]`, con el bloque
  literal del frontmatter) y §11 (al cerrar: fichar y poner `estado: fichado`).
- **(b)** → `CLAUDE.md`. **No** al runbook: la sesión de reparación no está abriendo nada, luego
  nunca lee el runbook de apertura. Una regla en el sitio equivocado no gobierna a nadie.
- **(d)** → `CLAUDE.md`, en el apartado de cierre de sesión.

## 10. Qué NO se construye

**(c), el lote en serie: aparcado por decisión expresa.** Es lo único que cuesta construir y no
entra en esta pieza. No se empieza, no se prepara el hueco, no se deja andamio.

## 11. Radio de daño y rondas

**1 ronda, sobre el diff.** Por la tabla de `CLAUDE.md`: la pieza **no** decide quién puede
escribir sobre qué copia y **no** puede destruir ni corromper datos de cliente — lee ficheros de
un directorio del perfil y escribe texto en la consola.

**No es exenta**, aunque el diff sea pequeño y la mayor parte documental: toca un **guard**, y los
guards no quedan exentos nunca. El aviso, además, es código nuevo en el camino del cierre.

## 12. Lo que queda sin verificar, declarado

- **La ruta deja de servir si abre otra persona o si Nikolai abre desde otra máquina** (§4). Hoy
  no ocurre; no se arregla por anticipación.
- **Nada obliga a la sesión de apertura a escribir el fichero.** El aviso detecta el fichero que
  existe y no se fichó; no puede detectar la apertura que no anotó nada. Eso sigue dependiendo
  del runbook, es decir, de que la sesión lo lea — que es el mismo tipo de dependencia que este
  spec acaba de llamar defectuosa en el §3. Se declara en vez de fingir que la cubre.
