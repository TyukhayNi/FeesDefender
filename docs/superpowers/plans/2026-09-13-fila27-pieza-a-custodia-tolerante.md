---
tipo: plan
estado: vigente
creado: 2026-09-13
rev: 1
---

# Pieza A de la fila #27 — el recorrido de custodia declara lo que no pudo leer (`MEJORAS #214`)

**Este documento existe para tener un hogar de la decisión.** El diseño de la pieza A se
escribió en `docs/superpowers/handoffs/handoff-2026-09-13-fila27-tipo-por-bytes.md` §3, que
es un **andamio efímero** (`GOBERNANZA_FUENTES_VERDAD §5`) y por tanto mal sitio para una
adjudicación permanente. Aquí va lo que sobrevive al andamio: qué se construyó, qué se
decidió y qué quedó declarado sin cubrir. El estado de ciclo de vida del ítem sigue viviendo
en `PLAN.md` fila #27, que es su hogar autoritativo.

## 1. El defecto, medido

El montaje de Google Drive for Desktop **presenta** una extensión inferida del content-type
para los ficheros que en Drive no la llevan, poco después de que `rclone` haya escrito el
nombre pelado. `hash_tree_local` (`scripts/abrir_caso.py`) **lista y luego abre**, así que
moría con `FileNotFoundError` sobre un fichero que está — y la etapa `drive` de la secuencia
V1 pasaba a `bloqueado` con el pull ya hecho.

Medido el 2026-09-10 abriendo **W-048U77**: la carpeta de E&V traía **11 de 58 ficheros sin
extensión**, que en ese Drive es la norma (escaneos y fotos de móvil). Diagnóstico completo
con las cifras: `MEJORAS #214`. Remedio manual mientras tanto:
`RUNBOOK_APERTURA_EXPEDIENTE.md [APER-65]`.

## 2. La frontera, que es lo que se remedia

No es «`hash_tree_local` necesita un `try`». La propiedad mal cerrada es que **un fichero que
no se pudo leer no ha medido cero**: ha quedado **sin verificar**, y eso hay que decirlo. Un
remedio que solo capturase la excepción convertiría un documento perdido en silencio, que es
peor que el fallo ruidoso de partida — en un ledger forense, un hueco callado es una
afirmación falsa sobre el expediente.

## 3. Qué se construyó

- **`core.abrir_caso`** gana `FicheroSinVerificar` y `ArbolLocal` (hashes + `sin_verificar` +
  `renombrados`), junto a `Reconciliacion`, porque son vocabulario de custodia.
- **`hash_tree_local`** devuelve `ArbolLocal`. Enumera con `os.walk(onerror=…)` —`rglob`
  **suprime** los errores de recorrido, así que una carpeta irrecorrible devolvía «cero
  ficheros»— y lee tolerante por fichero: ante un `FileNotFoundError` relee el directorio
  buscando el mismo nombre **más un punto y algo**. Exactamente un candidato nuevo → se
  hashea bajo su clave efectiva y se anota en `renombrados`; cero, o dos o más →
  `sin_verificar`. **La ambigüedad no se resuelve adivinando.** El protocolo por ubicación
  (`MEJORAS #149`) se decide sobre la clave **efectiva**.
- **`_inventario_desde_hashes`** tolera la misma carrera en su `stat()` y devuelve
  `(inventario, sin_verificar)`.
- **La declaración viaja a los tres destinos**: al valor de retorno
  (`DriveIntakeResult.custodia_sin_verificar`, que rellena la custodia y **no** el pull), a
  los `details` del evento forense, y al `Pendiente(custodia_sin_verificar)` de `etapa_drive`
  — **sin tumbar la etapa**. El camino del pull **fallido** (R15/H15-06) recorre el mismo
  montaje y recibe el mismo trato.

## 4. Tres decisiones de alcance, declaradas

1. **`hash_tree_local` NO se muda a `core/`.** El guard AST de
   `tests/test_abrir_caso_exit_bajo_mutex.py` exige que esté definida en
   `scripts/abrir_caso.py`. Mudarla **no obliga a debilitar la propiedad** —la R1 señaló que
   el guard podría ampliarse al módulo destino, y tiene razón— pero sí obliga a **rehacer el
   guard**, que es trabajo propio y no el de esta pieza. Los tipos sí van a `core/`.
2. **`Reconciliacion` NO gana `sin_verificar`/`completa`**, como proponía el handoff §3.3.
   Ningún llamador los leería: sería una pieza que nadie encadena. `_intake_generico` declara
   por su cuenta. **Y el §3.3 queda además acotado por un hecho medido:** «`extras` es siempre
   vacío porque `reconcile` cuadra consigo mismo» deja de ser cierto en cuanto el inventario y
   los hashes pueden diferir — ver §6.
3. **La reconciliación contra el remoto NO se mete dentro del pull.** Ya está construida en
   `core/verificar_apertura.py::c1_censo_remoto` (compara multiconjuntos del censo remoto
   contra `01_Drive EV` y reporta `sobran_en_local`) y `c2_hash_contra_drive`, las dos de la
   fila #28/P2. Meter red en el camino del intake cambiaría el modo por defecto y necesitaría
   su propio puerto cerrado. El punto 3 del plan —persistir el mapa junto al `.pulled`— queda
   **diferible y con su premisa corregida**: hoy no elegimos qué pedir (`rclone copy` va sobre
   la carpeta entera), así que un mapa no cambia nada por sí solo; haría falta `--files-from`
   o una poda posterior contra el censo.

## 5. Lo que queda SIN VERIFICAR, y no se da por cubierto

- **El montaje real de Drive for Desktop renombrando bajo los pies.** No se reproduce ni en
  Linux ni sin `G:`; lo que hay son carreras deterministas equivalentes en sus límites de
  I/O. Solo una apertura real lo comprueba.
- **Las otras dos instancias de la misma frontera** que `MEJORAS #214` enumera: el inventario
  de la sala de máquina y el `hash_tree` del MCP. Son otro módulo y otro momento del flujo;
  van a backlog, no se cuelan aquí.

## 6. Adjudicación de la revisión adversarial (Codex, 2026-09-13) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/plans/2026-09-13-fila27-pieza-a-custodia-tolerante.md` rev. 1, commit `436f23d`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-09-13-fila27-pieza-a-r1-adversarial-review.md`
- **Hallazgos:** 12 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** PR #358 (`8fe0e18`)

**Doce hallazgos, doce confirmados contra la fuente, cero refutados.** Y no son doce defectos
sueltos: son **cuatro fronteras**, que es lo que la casa manda preguntar antes de remediar.

| # | Sev. | Frontera | Qué rompía | Remedio |
|---|---|---|---|---|
| H-01 | ALTO | A — nombres por igualdad de cadena | En Windows `X.PDF` ya listado reaparece como `x.pdf` y se **adoptaba**: el hash de otro documento bajo dos claves, y el original perdido en silencio | `os.path.normcase` en las dos comparaciones |
| H-09 | BAJO | A | Lo simétrico: `Photo` → `photo.jpg` no se reconocía, y `x` → `x.tar.gz` tampoco (el `stem` solo quita la última extensión) | mismo `normcase` + criterio por prefijo `nombre + "."` |
| H-02 | ALTO | B — la declaración al final de funciones con cinco salidas | El evento se escribía solo `if plan.con_sha`: la corrida en que **ningún** fichero se pudo leer era la única sin rastro en el ledger | la condición pasa a «hay algo que contar **o** algo que declarar» |
| H-07 | MEDIO | B | Un fallo del **recuento** del destino devolvía `hecha` con `pendientes=()`, tirando una declaración ya calculada | la custodia se calcula **antes** de cualquier `return`; `_pendientes_de_custodia` |
| H-08 | MEDIO | B | El pull fallido calculaba la declaración, la escribía en el evento y **no** la adjuntaba a `exc.result`, así que V1 daba un fallo genérico | `dataclasses.replace` sobre `exc.result`; `etapa_drive` lo lee |
| H-03 | ALTO | C — el recorrido afirma más de lo que mide | `_inventario_desde_hashes` hace `stat()` sobre la clave un instante después del hash: **la misma carrera** volvía a matar la etapa dos líneas más abajo | `stat` tolerante; devuelve `(inventario, sin_verificar)` |
| H-04 | MEDIO | C | `is_dir()` colapsa tres cosas en un booleano: una raíz ilegible o que resulta ser un fichero salía como «cero ficheros» | `stat` + `S_ISDIR`, con las tres ramas separadas |
| H-05 | MEDIO | C | Los subdirectorios **enlazados** salían del inventario sin declararse (`os.walk` no los sigue, y hace bien) | se declaran como excluidos, con su motivo |
| H-06 | MEDIO | C | La prosa prometía una completitud que un recorrido no puede dar | corrección de prosa: mide **lo enumerado**, y de lo enumerado nada se pierde callando |
| H-10 | MEDIO | D — oráculos de un solo elemento | Su mutante `tuple(sin_verificar)[:1]` **sobrevivía** a los 23 tests: todos los oráculos tenían una sola incidencia | tests con dos huecos; hoy es `M15` y muere |
| H-11 | MEDIO | D | A18 sacaba el motivo esperado **de la propia salida**: su mutante `motivo=""` pasaba | el oráculo viene de la entrada; hoy es `M16` y muere |
| H-12 | BAJO | — | El aviso decía «se hasheó bajo el nombre efectivo» también cuando el reaparecido era ilegible, y la línea siguiente lo desmentía | el aviso dice lo que pasó, no lo que se hizo después |

**Las dos divergencias de remedio** (razonadas en el §2 del acta): H-06 se cierra con prosa y
no con código —no existe la instantánea de un árbol que cambia mientras se recorre—; y sobre
P6.1 el revisor rebate con razón mi afirmación de que mudar la función «obligaría a debilitar
el guard», así que la prosa se corrigió sin mudar nada.

**Un defecto que encontré yo al remediar H-03, y que la R1 no pudo ver porque no existía.**
Al desacoplar el inventario de los hashes, la clave que el `stat` no pudo medir seguía
llegando a `reconcile` dentro de `hashes`: salía como `extra`, `ok` pasaba a `False` y la
apertura **abortaba entera**. Un hueco declarado no es un sobrante — confundirlos convertía el
remedio en una vía nueva de tumbar la etapa. Fijado en
`test_r1_h03c_un_hueco_del_stat_NO_aborta_la_apertura_como_si_sobrara`.

**Lo que la ronda costó y lo que devolvió, para el presupuesto.** Una ronda (radio de daño: la
pieza **lee** y **clasifica**, no decide quién escribe ni destruye datos de cliente). Devolvió
tres `ALTO`, y **dos de ellos —H-02 y H-03— eran el mismo defecto que la pieza venía a
arreglar, un nivel más abajo**: un hueco que se pierde en silencio. Dos hallazgos más
(H-10, H-11) no iban contra el código sino **contra el arnés**, y esos no los encuentra
releer el diff.

**Y un límite que fue culpa del mandato:** pedí controles positivos «distintos de los 14
mutantes del autor» sin poner esos 14 dentro del objeto. El revisor declaró la comparación
**SIN VERIFICAR**, correctamente. Remediado: el arnés vive ahora en
`tests/_mutantes_mejoras_214.py`, con **23 mutantes, 23 muertos**, cada uno verificado verde
antes de mutar.
