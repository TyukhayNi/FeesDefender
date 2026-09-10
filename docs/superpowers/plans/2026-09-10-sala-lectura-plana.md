---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-10
---

# La sala de lectura queda plana y deja de pisar documentos (`MEJORAS #67.b`, `#67.c`, `#36`)

> Pieza pequeña con documento propio por una razón: la decisión la tomaron **dos sesiones a la
> vez**, sobre el mismo fichero y desde dos casos distintos, y el contrato del nombre de los
> ficheros de la sala **estaba escrito dos veces y en desacuerdo**. Eso necesita un hogar.

## 1. Los dos defectos, y por qué van juntos

`poblar_sala_lectura` construía el destino como `Sala lectura/{fuente}/{nombre}`, una carpeta por
fuente, cuando la estructura canónica de la skill `organizar-sala-lectura` es **plana**: la
categoría vive en `INDICE.md`, no en carpetas. Es el tercer defecto de `MEJORAS #67` (**#67.c**),
que se venía aplanando **a mano** caso por caso — y el workaround se deshace en el siguiente
`organizar`.

Aplanar solo, sin embargo, **pierde documentos**: el layout por fuente estaba *tapando* la
colisión de nombre canónico que el backlog tenía escrita en **`#67.b`** y **`#36`**. Dos documentos
distintos con la misma fecha, tipo y descripción derivan el mismo nombre, y el `shutil.copy2` del
segundo sobrescribía al primero sin dejar rastro. El dedup por hash no protege: solo cubre bytes
idénticos.

**Medido, en dos casos y por dos sesiones:**

| Caso | Medición |
|---|---|
| W-02YZO4 (2026-09-10) | 3 colisiones reales: el encargo, la nota simple previa y el burofax llegan por Drive **y** por correo con **bytes distintos** (la copia del Drive pesa unos cientos de bytes más), así que el dedup no los une. Y 5 correos del mismo día con la misma descripción colapsando en un fichero. |
| W-048UOL (2026-09-10, sesión hermana) | `indice_documental.yaml` con **32** documentos y **15** ficheros en la sala; 17 imágenes descritas todas como «Fotografía» colapsadas en **dos** nombres. Y el síntoma que lo hacía invisible: `organizar` imprimió `COPY: 31` con 15 ficheros en disco — **el resumen contaba copias intentadas, no ficheros escritos**. |

El disparador declarado de `#36` era «la primera colisión observada en un caso real». Ya son dos
casos, y aplanar la convierte de latente en cierta.

## 2. La decisión sobre el nombre: `__<sha8>` para todos los del grupo

Tres esquemas estaban sobre la mesa, dos de ellos escritos en contratos que se contradecían — la
skill decía `_2`/`_3` y `MEJORAS #67.b` decía `__<sha8>`.

| Esquema | Falla cuando… |
|---|---|
| `_2`/`_3` por orden de llegada | el catálogo se reordena: el pelado y los ordinales mudan de documento |
| `_2`/`_3` con el pelado al `hash` menor | al grupo entra un tercero: el `_2` de ayer es el `_3` de hoy |
| **`__<sha8>` para TODOS los del grupo** | solo en la transición inevitable de uno a dos miembros |

**Decidido:** el tercero. En un grupo colisionado **nadie** conserva el nombre pelado; cada
documento lleva los 8 primeros hex de su `sha256`. Es estable frente a la reordenación **y** frente
al crecimiento del grupo, que son las dos formas en que una cita del letrado a un fichero pasa a
señalar otro documento. Y son 8 y no 6 porque `#67.b` ya fijaba 8: así solo hay **un** literal que
corregir (el de la skill), no dos.

Consecuencia: la skill `organizar-sala-lectura` pasa a **v1.17** con ese literal corregido en sus
dos apariciones (Paso 2 y Paso 4). **Pendiente empaquetar y re-importar el `.skill` en Cowork**:
la fuente corregida no es la skill desplegada.

## 3. Lo que entra en el código

- `_directorio_destino` — destino plano; la subcarpeta del documento compuesto sobrevive como
  única excepción. Devuelve `None` como relación **cuando no se detectó bundle**, para no pisar
  una relación previa (ver H-09 en el §5).
- `_asignar_destinos` — reserva **global** de rutas finales, no por grupo, y sufijado `__<sha8>`.
  Incluye las rutas de las filas que no entran al plan: su copia sigue en disco.
- `_discriminante` — el `sha8` del documento, o el del `ruta_relativa` si la fila llega sin hash.
- `_podar_directorios_vacios` — retira el cascarón de la carpeta por fuente al migrar, sin seguir
  enlaces, confinada físicamente bajo la sala, respetando el subárbol de `_plan` y **devolviendo**
  los errores que no son «el directorio no está vacío».
- `poblar_sala_lectura` — dos pases (el nombre definitivo depende de con quién colisione), no
  borra como «ruta vieja» lo que es destino nuevo de otra fila, rechaza un directorio ocupando el
  destino, dice cuándo sobrescribe un fichero sin fila, y devuelve **`n_en_sala`**: ficheros
  escritos, no copias intentadas.

Un caso ya poblado con el layout anterior **se aplana solo** en la corrida siguiente (rama
`MOVED`).

## 4. Cómo se decidió quién lo implementaba

Dos sesiones arreglaron esto a la vez, sin saberlo: esta (desde W-02YZO4, citando `#67.b`/`#67.c`)
y «Caso W-048UOL» (desde su caso, abriendo una entrada de backlog propia). Ninguna pisó a la otra en disco —worktrees
separados— pero el choque llegaba al mergear el segundo PR, y el modo de fallo caro era
«resolverlo» quedándose los dos mecanismos.

Se resolvió comparando las dos implementaciones por propiedades, no por antigüedad: la de
W-048UOL era estable frente al crecimiento del grupo y la de aquí frente a la reordenación, así que
**ninguna de las dos era la buena** y el esquema del §2 sale de juntarlas. La sesión de W-048UOL
retiró su diff (`fd401af`) y esta lo absorbe con su medición citada.

**Y un detalle que casi entró en el código como referencia falsa:** su entrada de backlog es el
`#215` **de su rama**, y en `main` el `#215` es otra cosa (`_MAGIC_BYTES`). Un número de backlog es
una **reserva** hasta que se mergea, así que aquí se cita la medición con su fecha y no el número.
Memoria [[feedback-numero-de-backlog-es-una-reserva]].

**La lección de método, que es lo que hay que llevarse:** al abrir comprobé duplicidad **del caso**
(grep del W-code, `git log`) y no duplicidad **del fichero que iba a cambiar**. La comprobación
tiene que cubrir las dos cosas — `git status` de los worktrees hermanos sobre los ficheros del diff,
antes de escribir. Memoria [[feedback-verificar-pr-duplicado-antes-ejecutar]].

## 5. Adjudicación de la revisión adversarial (Codex, 2026-09-10) — NO-SHIP, remediado

- **Objeto revisado:** diff `874111b..7c4a97a` — sala plana + guarda de colisión en `core/sala_lectura.py`
- **Ronda:** R1 (única; radio de daño = no decide quién escribe ni destruye el crudo de `00_Input`)
- **Revisor:** Codex (CLI 0.153.4), copia externa `git archive` de los dos commits, solo lectura
- **Informe recibido:** 2026-09-10, `2026-09-10-sala-lectura-plana-r1-adversarial-review.md`, 38.925 bytes
- **Hallazgos:** 12 — 5 ALTOS (H-01, H-02, H-03, H-04, H-10), 6 MEDIOS, 1 BAJO; **12 confirmados, 0 refutados**
- **Remediado en:** commit de este PR, `core/sala_lectura.py` + `tests/test_sala_lectura_plana_r1.py`

**El veredicto era correcto y la ronda se pagó sola.** Dos de los ALTOS los reprodujo
**ejecutando**, no leyendo, y uno de ellos —H-01— era un hueco que mi propia guarda abría: razonaba
dentro de cada grupo de colisión y no reservaba los nombres finales de los demás, así que
descripciones `mismo`, `mismo` y `mismo_2` producían dos rutas idénticas. También montó el control
que el mandato le pedía: corrió mis seis tests contra el código **base** (los seis rojos: sí
discriminan) y construyó un **mutante** que invertía la ordenación por hash y **pasaba los seis**,
lo que prueba que no fijaban la correspondencia documento→nombre. Ese mutante hoy muere en tres
tests.

| Hallazgo | Severidad | Veredicto | Remedio |
|---|---|---|---|
| H-01 · el sufijo generado choca con un nombre natural | ALTA | confirmado | reserva **global** de rutas finales en `_asignar_destinos`; test `test_h01_…` |
| H-02 · cambio de participantes reasigna citas; los traslados se borran entre sí | ALTA | confirmado | `__<sha8>` para todo el grupo (§2); no se borra como ruta vieja lo que es destino nuevo; las filas excluidas **reservan** su ruta; dos tests |
| H-03 · varias filas sin hash comparten casilla | ALTA | confirmado | regresión mía: el resultado se indexaba por `hash`. Ahora por índice, con `_discriminante` derivado del `ruta_relativa`; dos tests |
| H-04 · una ruta existente se acepta sin mirar sus bytes | ALTA | confirmado, **PREEXISTENTE** | fuera de alcance → `MEJORAS #232`. Verificar el destino por hash en cada corrida es una decisión de coste, no un arreglo de este diff |
| H-05 · el dedup no repara referencias; la reconstrucción deja huérfanos | MEDIA | confirmado, **PREEXISTENTE** | fuera de alcance → `MEJORAS #233` |
| H-06 · la poda sigue enlaces y borra fuera de la sala | MEDIA | confirmado | riesgo **nuevo** mío, y lo midió con junctions reales: se salta enlaces y exige confinamiento físico; test |
| H-07 · la exclusión de `_plan` no protege su subárbol | MEDIA | confirmado | riesgo nuevo mío: se filtra el subárbol, no el nombre; test |
| H-08 · un error de poda es indistinguible de un directorio ocupado | BAJA | confirmado | se distingue por `errno` y se devuelve; test |
| H-09 · sin bundle se borra `parent_id` y se conserva `orden_en_bundle` | MEDIA | confirmado | regresión mía frente al comportamiento anterior: solo se escriben esos dos campos si se detectó bundle; test |
| H-10 · no hay transacción ni exclusión entre corridas solapadas | ALTA | confirmado, **PREEXISTENTE** | fuera de alcance → `MEJORAS #229`. Es la deuda de `MEJORAS #126` («la UI y `sala_lectura` siguen sin mutex»), no algo que estos dos pases introduzcan |
| H-11 · el plan no inventaría lo ya presente en el destino | MEDIA | confirmado, **mitad y mitad** | el directorio en el destino se rechaza y se cuenta (test); sobrescribir un **fichero** sin fila se mantiene —es el destino canónico de esa fila— pero ahora **se dice** (`SOBRESCRITO_SIN_FILA`) |
| H-12 · aserto de parada debilitado; prioridad exacta sin probar | MEDIA | confirmado | **tenía razón y es la regla de la casa**: al aplanar cambié `not (…/"Drive E&V").exists()` por un `glob("*.pdf")` en la raíz, que es más débil. Restaurado a «con residuo, la sala no tiene ningún documento». Y el nombre exacto por documento queda fijado en `test_h12_…` |

**Lo que la R1 dejó SIN VERIFICAR y sigue así:** la genealogía de los commits (su copia no lleva
`.git`); dos procesos realmente simultáneos; ACL reales, disco lleno y corte físico durante la
escritura del YAML; y el comportamiento de enlaces en Linux/macOS. Lo declaró él y no se da por
cubierto.

**Cobertura de la remediación:** ver el §6, que es donde acabó la ronda que la cubre en parte.

## 5-bis. Los números de backlog de este trabajo se movieron, y los dos commits citan los viejos

Las cuatro entradas de los preexistentes nacieron como `#227`-`#230` y acabaron siendo **`#229`,
`#230`, `#232` y `#233`**; la del `_bundle_map` es `#231`. El motivo: `origin/main` llegó a `#223`
mientras yo trabajaba y el PR **#324**, abierto, reclama `#224`-`#228`. Medido contra `origin`, no
contra los mensajes de coordinación que me llegaron — los dos traían la foto rancia (uno daba por
abierto un PR ya mergeado y el otro daba mi `#231` por sin commitear).

| Nació como | Es | Qué es |
|---|---|---|
| `#227` | **`#232`** | una copia existente se acepta por su ruta, sin mirar sus bytes (H-04) |
| `#228` | **`#233`** | el dedup no repara referencias y reconstruir deja huérfanos (H-05) |
| `#229` | `#229` | sin transacción ni exclusión entre corridas solapadas (H-10) |
| `#230` | `#230` | un fichero sin fila ocupa el nombre canónico de un documento (H-11, mitad) |
| — | `#231` | `_bundle_map` indexa por hash (de la R2) |

**Los dos commits de la remediación (`7ca454d` y `d9858ea`) citan en su mensaje los números
viejos**, y no se reescriben: el repo prohíbe el `--force-with-lease` y una reescritura de historial
por cinco referencias de prosa cuesta más de lo que arregla. Esta tabla es el mapeo, y queda aquí
porque es donde alguien la buscará. La lección, que ya estaba escrita y me tocó dos veces el mismo
día: **un número de backlog es una reserva hasta que se mergea**, así que no se cita en código,
tests ni mensajes de commit antes de tenerlo firme — o se cita la medición, que sí es estable.

## 6. Adjudicación de la revisión adversarial (Codex, 2026-09-10) — NO-SHIP, remediado

- **Objeto revisado:** diff `874111b..9ce7183` — la implementación HERMANA del mismo mecanismo, retirada en `fd401af`
- **Ronda:** R2 de la pieza (R1 sobre ese objeto); la corrió la sesión «Caso W-048UOL» y me pasó el informe
- **Revisor:** Codex, copia externa del objeto, solo lectura, con sondas ejecutadas
- **Informe recibido:** 2026-09-10, `2026-09-10-sala-lectura-plana-r2-hermana-adversarial-review.md`, 23.831 bytes
- **Hallazgos:** 5 — 3 ALTOS, 1 MEDIO, 1 BAJO; **3 vivos en mi código ya remediado, 2 ya cubiertos**
- **Remediado en:** commit de este PR, `core/sala_lectura.py` + `tests/test_sala_lectura_plana_r2.py`

**Una ronda sobre otro objeto que resultó ser sobre el mío.** El diff que revisó es el de la
sesión hermana, que se retiró y no llega a `main`. Pero atacó el **mecanismo**, no su sintaxis, y
**tres de sus cinco hallazgos sobrevivían a mi remediación de la R1**. Que dos rondas
independientes, sobre dos implementaciones distintas del mismo mecanismo, encuentren defectos
distintos es el argumento más fuerte que he visto para el contrato de revisión de este repo.

| Hallazgo | Severidad | Veredicto sobre MI código | Remedio |
|---|---|---|---|
| su H-01 · el `unlink` borra el destino de otra fila — **mitad por reordenación** | ALTA | **ya cubierto** por la asignación por hash de la R1: quién se lleva cada nombre no depende del recorrido | — |
| su H-01 · **mitad por capitalización** | ALTA | **VIVO**. Mi barrera comparaba cadenas, y en Windows `Manual/` y `manual/` son la misma carpeta: al migrar, el `unlink` de una fila borraba la copia recién escrita de otra. Lo reprodujo **ejecutando en Windows**, y sin reordenar nada | `clave_ruta` normaliza separador y capitalización, y la barrera compara por esa clave; test |
| su H-02 · hashes vacíos | ALTA | **VIVO**. El dueño de una reserva era `hash or ""`, así que todas las filas sin hash lo compartían y una podía tomar la ruta de otra. Su tabla de `("","")`, `(None,None)`, `(None,"")`, `("",None)` es el mapa exacto del defecto | `clave_dueno`: el hash cuando lo hay, algo único por fila cuando no — conservando que las deduplicadas SÍ compartan dueño; dos tests |
| su H-03 · las filas saltadas no reservan su ruta | ALTA | **ya cubierto** por la R1 (`reservadas`), comprobado contra la fuente y no por fecha | — |
| su H-04 · la migración deja la estructura vieja | BAJA | **ya cubierto** por `_podar_directorios_vacios`, y su medición en vivo es la confirmación de que hacía falta | — |
| su H-05 · debilitó el aserto de parada por residuo | MEDIA | **el mismo aserto que yo había debilitado**, ya restaurado por la R1. Su aviso me hizo pasar la mutación por los otros cuatro: dos `any(...)` quedan reforzados | test reforzado |
| extra · **borrar antes de copiar** | — | **VIVO**, y preexistente a los dos diffs. Un fallo de copia dejaba el destino viejo borrado, el nuevo sin crear y el catálogo apuntando a la nada. **La migración lo activa sobre el expediente entero**: en W-02YZO4 fueron 26 documentos en una corrida | se copia y **después** se borra; test con `OSError` inyectado + control positivo de que la migración sigue retirando la copia vieja |
| extra · `_bundle_map` indexa por hash | — | confirmado, **PREEXISTENTE** | fuera de alcance → `MEJORAS #231` |

**Y lo que sigue SIN cubrir, dicho sin adornos:** ni la remediación de la R1 ni estos tres
arreglos han pasado por una ronda adversarial. Son dos remediaciones sin revisar sobre una pieza
cuyo presupuesto declarado era **una** ronda. El techo de dos rondas por pieza ya está consumido, y
una tercera **necesita autorización expresa de Nikolai** — no la pido escondida en un documento:
queda dicho aquí y en el resumen de la sesión. Lo que sí acredita el estado actual son los tests
(16 de la R1 + 7 de la R2, con sus controles positivos y el mutante muerto) y la verificación por
contenido sobre el expediente real.
