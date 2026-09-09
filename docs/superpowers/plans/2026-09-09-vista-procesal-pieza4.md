---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-09
rev: 2
spec: docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md
---

# Vista procesal de `05_Procedimiento` — pieza 4 · Diseño de la rev. 2 y reparto

> **Este documento no es ejecutable.** Es donde viven las decisiones y la adjudicación de la
> R1. Los planes ejecutables son sus dos mitades:
>
> - **4a — la vista que solo lee:** `docs/superpowers/plans/2026-09-09-vista-procesal-pieza4a.md`
> - **4b — la vista que escribe:** pendiente de escribir, **después** de que 4a esté mergeada.

## Por qué hay una rev. 2

La rev. 1 fue a revisión adversarial y volvió **NO-SHIP con 23 hallazgos, 6 de ellos
CRÍTICO**. Los adjudiqué todos contra la fuente: **23 confirmados, 0 refutados**. La
adjudicación completa, con la evidencia que verifiqué yo, está en el **§10** de este
documento; el informe literal del revisor y su digest, en el acta hermana
`2026-09-09-vista-procesal-pieza4-r1-adversarial-review.md`.

**Las tareas de la rev. 1 quedan retiradas y no se conservan aquí.** Dejarlas al lado de la
versión buena es una trampa para quien lea esto en seis meses: un plan retirado con código
completo se ejecuta solo. Están en el historial (`8f9ad84`) si alguien necesita verlas.

## Los ocho invariantes

No son ocho arreglos: son las ocho propiedades que la rev. 1 rompía, cada una con varios
hallazgos como ejemplos. Están para que **cualquiera** de las dos mitades se pueda juzgar
contra ellas.

| | Invariante | La rompía |
|---|---|---|
| **I0** | La autoridad para tocar un caso viene del **resolver del workspace** (`Capability`, `ws.working_root`), no de una ruta del catálogo ni del mutex local | H-06 |
| **I1** | **Toda** ruta que la transacción escriba o borre pasa la misma puerta de propiedad; un hash ausente **bloquea**, nunca amplía el permiso; y ninguna comprobación vale más allá del instante en que se hizo | H-01, H-04, H-05 |
| **I2** | La recuperación **se acredita, no se infiere**: hay evidencia durable escrita *antes* de publicar, o la recuperación es manual. La igualdad de bytes no prueba autoría | H-02 |
| **I3** | La raíz autorizada se identifica **primero** y jamás se re-deriva de la ruta que se juzga; los *reparse points* de la cadena de ancestros se vetan; nada que venga del mapa es componente de ruta sin gramática propia | H-03, H-16 |
| **I4** | **Tres** conjuntos distintos y ninguna puerta usa uno por otro: universo `listadas`, materialización `materializadas`, y `pull_state.doc_ids` = lo que bajó *la última corrida* | H-08, H-09 |
| **I5** | *Clase* y *estado* de la cobertura son ejes distintos; el bundle es un grupo de primera clase que resuelve al artefacto **del padre**; la cadena ocurrencia → cobertura → bytes se **verifica** | H-10, H-11, H-12 |
| **I6** | Un test se acepta cuando se le ha visto **ponerse rojo** con su defecto puesto. El nombre y el docstring no acreditan nada | H-21 |
| **I7** | Lo que se deja fuera de alcance se declara **con su coste**, y la justificación no puede apoyarse en un mecanismo inventado para poder dejarlo fuera | H-07, H-13, H-14, H-15, H-18, H-19, H-20, H-22 |

Los tres restantes: **H-17** (presupuesto de longitud que olvidaba el temporal) y **H-18**
(el flujo que hace usable la pieza) entran en 4a; **H-23** (PII en el propio plan) quedó
remediado en `8f9ad84` y su relato está en el §10.

## El reparto en dos mitades, y por qué mejora el diseño

La rev. 1 metía en una sola pieza dos cosas de radio de daño **incomparable**: *decir* qué
hay en el procedimiento, y *publicar* ficheros en él. Cuatro de los seis críticos viven en
la primera mitad, donde no hay una sola escritura — y estaban ahí porque la mitad que
escribe contaminaba el diseño de la que lee.

**4a — la vista que solo lee.** Autorización, raíz autorizada, gramática del mapa, los tres
conjuntos del CRM, el selector de artefacto, y un informe. **No existe ruta de escritura en
el código**: no hay `copiar`, no hay ledger, no hay `os.replace`. Entrega algo útil por sí
solo —el letrado ve sus 76 documentos, qué fase tiene cada uno, qué falta y qué bloquea— y
es lo que permite escribir el mapa, que hoy no tiene quién lo prepare (H-18).

**4b — la vista que escribe.** Journal de intención, ledger de propiedad, la transacción, el
índice. Se planifica **cuando 4a esté mergeada**, sobre un suelo ya revisado.

**Consecuencia en el presupuesto de rondas, que no es un atajo sino el criterio del propio
contrato:** el número de rondas lo fija el **radio de daño**. 4a no decide quién escribe
sobre qué copia y no puede destruir datos de cliente —por construcción, no por promesa—, así
que le corresponde **1** ronda, sobre su diff. 4b sigue mereciendo **2**. Partirlo no evita
revisión: la concentra donde el daño está.

Y una nota sobre `adoptar`, que fue mi invención de la rev. 1: **desaparece**. No se
sustituye por una versión más lista. En 4b la recuperación será un journal escrito antes de
publicar, que es lo que declaré fuera de alcance y lo que no debí dejar fuera.

## Lo que sigue fuera de las dos mitades

Copiado del alcance del spec §7, más lo que la R1 añadió:

- **Que `plan` proponga la carpeta.** La asignación es del letrado, por decisión cerrada de
  §0. 4a **sí** propone `orden` y `descripción` — eso es lo que el spec §2.5 cierra y la rev.
  1 dejó fuera sin declararlo (H-18).
- **Cualquier modificación de `00_Input/05_CRM`.**
- La reescritura de `intake_manifest` al modelo de ocurrencias (opción A).
- La preparación de la documental numerada, la subida carpeta → CRM y la resolución de
  `.eml`: tres proyectos propios, cada uno con su decisión.
- **La ampliación de `DESTINOS_VALIDOS`** —lo único que §7 mete en alcance de la vista— tiene
  desde el 2026-09-09 **su propia pieza**:
  `docs/superpowers/plans/2026-09-09-destinos-de-fase-registrar-outputs.md`. Estaba dentro de
  4a y su revisión adversarial la sacó (H-01): ampliar esa tupla amplía dónde puede escribir un
  helper que escribe, y contradecía la restricción de 4a de no escribir nada. Decisión de
  alcance de Nikolai; con ella fuera, 4a recupera su radio de daño cero y su ronda única.
- **El cambio de comportamiento de las seis skills del spec §8.1**, el handoff de §8.2 y la
  documentación de §8.4: pieza 5. Abrir el destino (la pieza de arriba) da la **capacidad**;
  que `escritos-judiciales` pregunte la fase y escriba ahí es el **consumo**, y toca el cuerpo
  de seis skills que hay que re-empaquetar e importar en el servidor.
- **Retirar los procesales de `01_Procesado/Sala lectura`**: necesita el mapa primero.
- **Y lo que la R1 corrigió de mí:** los tests de biblioteca del spec §6 **no** están
  cubiertos por la pieza 1 en su mitad de los PDF. `core/config.py:436-441` dice
  explícitamente que los PDF **se desacoplan sin peligro** y su grupo son los tres ficheros
  de control. Mi rev. 1 afirmaba lo contrario (H-22). Lo que falte ahí se decide en 4b, que
  es quien crea el ledger.

## 10. Adjudicación de la revisión adversarial (Codex, 2026-09-09) — NO-SHIP, parcial

- **Objeto revisado:** este plan en el commit `25c07bc` (`sha256 aaaf72e7…955050`), copia externa sin `.git`
- **Ronda:** 1 de 2 — la del diseño; la del diff queda pendiente
- **Revisor:** Codex (`codex-cli 0.153.4`, `model_reasoning_effort=high`), en solo lectura sobre copia congelada
- **Informe recibido:** `docs/superpowers/plans/2026-09-09-vista-procesal-pieza4-r1-adversarial-review.md` (`sha256 b39f7bce…e037f8`)
- **Hallazgos:** 23 — 6 CRÍTICO, 14 ALTO, 3 MEDIO. **23 confirmados, 0 refutados.** Dos acotados en su alcance, ninguno rebajado de severidad
- **Remediado en:** H-23 en `8f9ad84`; los 22 restantes exigen reescribir el plan (v2), no parchearlo

**Acepto el NO-SHIP y retiro este plan como ejecutable.** No se escribe una línea de producción
sobre él. Lo que sigue no es una lista de 23 arreglos: son **siete fronteras**, porque casi todos
los hallazgos son ejemplos de una de ellas, y remediar el ejemplo en vez de la frontera es el
error que ya me costó una regresión peor.

### Las siete fronteras

**F1 — La propiedad se comprueba en la ruta que se lee, no en todas las que se escriben o
borran.** (H-01, H-04, H-05, y la mitad de H-02.) Mi puerta miraba el fichero *anterior* de un
`mover`/`reemplazar` y nunca el destino *nuevo*; y solo miraba si había SHA, porque escribí
`if asiento.destination_sha256`, de modo que **un asiento sin SHA ampliaba el permiso en vez de
bloquearlo**. La frontera: *toda* ruta que esta transacción vaya a escribir o borrar pasa la
misma puerta, la ausencia de hash bloquea, y ninguna comprobación vale más allá del instante en
que se hizo — entre `plan` y `apply` hay un hueco que el mutex no cierra, porque el mutex no
gobierna a Word ni a Drive.

**F2 — Igualdad de bytes no es prueba de autoría, y `adoptar` la usaba como si lo fuera.**
(H-02, y el test de PLAN:1814, que *bendecía* el defecto en vez de cazarlo.) Esto lo inventé yo
en el self-review para cerrar un agujero, y abrí uno peor. El caso que lo mata no necesita
coincidencia improbable: si el ledger ya posee `00_f.pdf` para el `doc_id` 2 y el mapa lo pide
para el 1 con idéntico contenido, se emiten `adoptar(1)` y `borrar(2)`, y **el borrado final
elimina el fichero que la misma corrida acaba de adoptar**, dejando un asiento que afirma poseer
algo que ya no existe. Y hay un daño colateral que no vi: `core/config.py:436-441` justifica
desacoplar los PDF del grupo de merge **precisamente porque** «un fichero sin línea en el ledger
se reporta como ajeno». Mi adopción convertía eso en propiedad, así que debilitaba en silencio
la garantía de una pieza **ya mergeada**. La frontera: *la recuperación se acredita, no se
infiere*. O hay un journal de intención escrito **antes** de publicar, o la recuperación es
manual y explícita. Lo que no cabe es deducir la propiedad del contenido.

Y una lección sobre mí, no sobre el código: declaré el journal fuera de alcance y justifiqué la
omisión con este mecanismo. Cuando mi propia regla me obligaba a construir el journal, inventé
un atajo. Es el patrón exacto que ya tengo anotado y no me disparó.

**F3 — Contención: resolver la raíz permite que la propia ruta legitime su desvío.** (H-03,
H-16.) Comprobaba `destino.resolve().relative_to((case_dir / "05_Procedimiento").resolve())`, y
si `05_Procedimiento` es una *junction* al crudo, **las dos partes resuelven al mismo sitio y la
comprobación se aprueba a sí misma**: el revisor creó la junction de verdad y apply borró un
fichero de `00_Input/05_CRM` y escribió el ledger dentro del crudo. `is_symlink()` sobre el
fichero no ve un reparse point en un directorio padre. Y por el otro lado, `orden: ../00` entra
sin gramática y sale de la carpeta de fase. La frontera: la raíz autorizada se identifica
**primero** y jamás se re-deriva de la ruta que se está juzgando; ninguna cadena que venga del
mapa se convierte en componente de ruta sin gramática propia.

**F4 — `pull_state.doc_ids` es el subconjunto DESCARGADO; el universo es `listadas`.** (H-08.)
Verificado por mí: `core/case_manager.py:1638` lo dice literalmente y
`core/sync_sudespacho.py:1669` solo hace `append` dentro del bucle de descarga, después de
filtrar `only_doc_ids`. Los conflaté, y el efecto es doble y grave: en el **régimen acotado**
—el que usó este mismo caso, 2 documentos de 76— mi puerta habría bloqueado los otros 74; y con
`doc_ids` vacío el cruce se salta entero y las `solo_listadas` **no bloquean ni aparecen en
`sin_asignar`**, porque calculaba `sin_asignar` sobre `materializadas`. O sea: la pieza habría
sido inservible en el expediente para el que la diseñé, y a la vez habría ocultado en silencio
lo que el CRM tiene y el caso no bajó. La frontera: universo enumerado, materialización y
decisión del letrado son **tres** conjuntos distintos y ninguna puerta puede usar uno por otro.

**F5 — La cobertura tiene más clases de las que enumeré, y el bundle no es una fila.** (H-10,
H-11, H-12.) Verificado: `duplicado` (`METODO_DUPLICADO`, `MEJORAS #147`) y `error`
(`sala_maquina.py:1409`) son métodos reales que mi selector mandaba a «desconocido → bloqueo», y
`alias_de` no se resolvía. El OCR de un bundle se escribe en `01_OCR/<parent_slug>.pdf`
(`:1023`) mientras las filas de segmento llevan el slug del **segmento** (`:975`), así que mi
grupo —que conservaba la fila de peor calidad— derivaba una ruta inexistente y bloqueaba teniendo
el PDF íntegro al lado. Además nunca cruzaba el **SHA actual** del crudo con el de la ocurrencia
y la cobertura: bastaba que el fichero existiera. La frontera: *clase* y *estado* son ejes
distintos; el bundle es un grupo de primera clase que resuelve al artefacto del padre; y la
cadena ocurrencia → cobertura → bytes se verifica, no se presume.

**F6 — Los tests compraban garantías que no ejercitaban.** (H-21 y la tabla de 70 filas.) Tres
mutantes **ejecutados** pasan con el defecto puesto: el de «despacho no destructivo» solo corría
`desregistrar`, el de atomicidad solo miraba que no quedaran temporales, y el de reejecución le
pasaba a mano un plan vacío. Cuatro tests de fachada **ya estaban rojos** por un fixture que no
redirige a todos los lectores, y uno más por H-16. Y los tres del corpus pasarían con todo
bloqueado o con todos los crudos ausentes. La frontera: un test se acepta cuando se le ha visto
**ponerse rojo** con su defecto puesto; el nombre y el docstring no acreditan nada.

**F7 — Lo que declaré fuera de alcance con una justificación que no se sostiene.** (H-07, H-09,
H-13, H-14, H-15, H-18, H-19, H-20, H-22.) El journal (F2). La puerta de registro ausente, que
delegué a un `load()` cuyo contrato legítimo es devolver vacío. La procedencia doble, que en
`converted` guardaba `raw_path`/`raw_sha256` **vacíos** — justo en el único caso donde la cadena
importaba. `eco_crm` sin puerta ni persistencia. El override de cobertura sin evento ni actor, y
autorizado por un `'false'` que `bool()` hace `True`. El flujo que hace usable la pieza
—proponer `orden` y `descripción`, emitir el borrador del mapa— que el spec §2.5 cierra y yo
dejé fuera sin declararlo. El punto de commit de los índices, que consolida un estado incompleto
como «sin cambios». Un marcador de índice roto que se come el trabajo manual del letrado. Y la
atribución errónea a la pieza 1.

### Los dos que acoto, sin rebajarlos

- **H-17 (MEDIO).** El defecto real es la **promesa incumplida**: presupuesté la ruta final y no
  el temporal, que sale 11 caracteres más largo. Lo que *no* está demostrado —y el propio
  revisor lo dice— es que este host falle por MAX_PATH. Se remedia el presupuesto; no se afirma
  el fallo.
- **H-18 (MEDIO).** El revisor **corrige el marco de mi propio mandato**, que pintaba la puerta
  de `sin_asignar` como incumplible: con 76 materializados y nombres únicos, vaciarla a mano es
  posible. Lo que sí falta es el flujo que lo hace razonable. Lo apunto porque es la clase de
  precisión que distingue una revisión de una queja.

### Qué pasa ahora

El plan se reescribe (**v2**) sobre las siete fronteras, y **hasta entonces no hay código**. El
orden de tareas cambia: la autorización por workspace y el journal de intención dejan de ser
detalles de la Tarea 8 y pasan a ser la Tarea 1, porque son la frontera de la que dependen las
puertas. `adoptar` desaparece. Los tests se rescriben con su mutante delante.

**Cobertura ausente que no se disimula:** el corpus real y el reparto del piloto siguen
**SIN VERIFICAR** — el revisor no abrió los expedientes ni generó los fixtures, así que los tres
tests de regresión no corrieron. Trece declaraciones SIN VERIFICAR en su informe, y ninguna es
un «está bien».

### Corrección de esta adjudicación (2026-09-09, misma fecha)

Al agrupar los 23 hallazgos en siete fronteras **dejé H-06 sin asignar a ninguna**, y es
un CRÍTICO. Lo detecté contando las menciones de `H-NN` en esta propia sección: 22 de 23.
El reparto de arriba se lee, por tanto, con una frontera más, que va **primera** porque
todas las demás dependen de ella:

**F0 — La autoridad para escribir no la da el mutex local: la da el resolver del
workspace.** (H-06.) Mi fachada elegía el caso con `case_locator.buscar` y escribía; el
mutex de `MEJORAS #126` solo impide que **otro proceso de esta máquina** entre a la vez, y
no dice nada sobre si este caso está **prestado a otra máquina**. `scripts/sala_maquina.py`
ya resolvió esto y su docstring describe mi defecto palabra por palabra: «antes esto
resolvía una ruta y escribía sin preguntar a nadie: si el caso estaba prestado a otra
máquina, el motor arrancaba igual». La frontera: la resolución **y la autorización** vienen
del mismo sitio (`_resolver_workspace` + `Capability`), la raíz de trabajo es
`ws.working_root` y **no** una ruta del catálogo, y el mutex se sostiene en el entrypoint,
no se promete en un docstring.

Que se me escapara justo el hallazgo sobre «de dónde viene la autoridad» mientras escribía
las fronteras es el tipo de omisión que solo aparece contando. La lección operativa: **al
agrupar N hallazgos en M fronteras, contar que los N estén repartidos** — el reparto es una
afirmación verificable, no una impresión.
