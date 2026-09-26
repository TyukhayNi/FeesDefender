---
tipo: plan
estado: vigente
creado: 2026-09-26
objeto: MEJORAS #303 — el aviso «PLAN.md ↔ git» de scripts/session_close.py: una ruta no es una rama, `claude/` sí lo es, y cada fila de una tabla es su propio ítem
---

# MEJORAS #303: el aviso «PLAN.md ↔ git» que gritaba siempre y no acertaba nunca

> **Estado (2026-09-26):** construido con TDD; la R1 de Codex sobre el diff (§6), `LISTA-CON-CAMBIOS`,
> adjudicada en la §7 y remediada en el mismo PR, sin otra ronda. Fila **#43** de `PLAN.md`.

**Encargo.** Nikolai eligió el `#303` el 2026-09-26 y pidió hacerlo en la sesión de `crm_ficha`,
en un PR aparte. El backlog decía «una ronda: toca `scripts/`, no datos de cliente».

## 1. Lo medido, antes de tocar nada

Sobre el `PLAN.md` de `main` en `4209582` (2026-09-26, antes del #398 y del #400),
`_plan_items_desfasados` daba **49 «ramas fantasma» en un solo ítem** —«🎯 Cola priorizada»— y
**las 49 eran rutas `docs/…`**; sobre `ca250a4`, con esos PRs dentro, el mismo aviso da **56**, todas
rutas `docs/…` también (lo midió la R1). No eran un defecto sino tres, dos independientes y uno de
granularidad:

1. `_RE_RAMA` reconocía una rama por una lista de prefijos convencionales que incluía `docs`, y eso
   choca con el directorio `docs/`: toda ruta de documento casaba.
2. La lista no incluía `claude`, el prefijo que pone la app y el de **19 de las 22** ramas que git
   conocía ese día. Una rama `claude/x` ya podada —el caso que el aviso existe para cazar— no salía
   nunca.
3. La frase de pendiente (`_FRASES_PENDIENTE`) se evaluaba por bloque de encabezado, y la cola es
   UN bloque: una tabla de 37 filas con 68 líneas de notas `>` **debajo** —Markdown no admite citas
   entre filas—. El «sin commitear» de la historia de la fila #31, cerrada, armaba el bloque entero.

**El dato que cambió el remedio del backlog:** en los **400 PRs** de la historia del repo hay ramas
`claude/` (275), `docs/` (62, p. ej. `docs/cierre-117`), `feat/` (26), `fix/` (15), `chore/` (4),
`codex/` (1) y `test/` (1). Quitar `docs` de la lista perdería ramas reales: lo que faltaba era
distinguir una rama `docs/cierre-117` de una ruta `docs/MEJORAS_FUTURAS.md`.

## 2. Diseño

- **Los prefijos que el repo ha usado** (`_PREFIJOS_RAMA`), con `claude` y `codex`.
- **`_RE_RAMA`:** el token no empieza a mitad de una ruta ni de otra palabra (`.claude/skills`,
  `core/docs/x`), tiene **un solo segmento** tras el prefijo, y el lookahead incluye los caracteres
  del nombre, para que el backtracking no corte una ruta como
  `docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto.md` en `docs/superpower`.
- **Una ruta no es una rama:** un nombre que acaba en extensión de fichero (`_RE_EXTENSION`: hasta
  ocho caracteres y al menos una letra —`.md`, `.markdown`, `.ps1`—, así que `release/1.2` sigue
  siendo rama) o que existe en el árbol del repo. Lo segundo va por un parámetro nuevo, `es_ruta`,
  de `_plan_items_desfasados`; por defecto `_es_ruta_del_repo`, que mira `ROOT / token`. El llamador
  no lo pasa: dos tests existentes doblan la función con dos argumentos.
- **Cada fila de una tabla es su propio ítem.** Una fila es la línea cuyo contenido, **tras la
  sangría y las marcas de cita** (`> `), empieza por `|` (R1/H-01, H-04). Se titula «<encabezado> —
  fila <primera celda>», o «— línea <n>» si la primera celda está vacía (R1/H-03). Lo que queda del
  bloque fuera de la tabla —prosa y notas— sigue siendo el ítem del encabezado, como antes. El
  separador `|---|` pasa por la misma rama y, sin frase de pendiente, no avisa nunca: comprobarlo
  aparte era código que no podía cambiar la salida (R1/H-04), y se retiró. El tipo de retorno no
  cambia.

**Probado fuera del código antes de escribirlo**, sobre el `PLAN.md` real: con los dos arreglos, de
49 avisos queda uno. Cada arreglo por separado no basta: el reconocedor solo deja uno, atribuido al
bloque entero; trocear por filas sin el reconocedor deja diez.

## 3. Tests

Diez nuevos en `tests/test_session_close_aviso.py` (`test_303_*`), y los seis que ya tenía el aviso
sin tocar. Vistos en rojo en dos pasos: antes del reconocedor, todos los que usan `es_ruta` fallan
porque el parámetro no existe, y el que no lo pasa falla por su aserto; con el reconocedor y sin
trocear, fallan por su aserto justo los tres de filas —dos de ellos habrían pasado *por casualidad*
contra el código viejo, que no veía ninguna rama `claude/`—.

| Test | Propiedad |
|---|---|
| `una_ruta_docs_en_un_item_pendiente_no_es_una_rama` | `docs/INDICE.md`, un enlace a un plan y `docs/bitacora/2026.md` no salen |
| `una_rama_claude_podada_en_un_item_pendiente_si_sale` | el falso negativo del backlog |
| `una_rama_docs_de_verdad_sigue_saliendo` | `docs/cierre-117` sale: el prefijo se queda |
| `un_directorio_que_existe_no_es_una_rama` | `docs/superpowers`, con `es_ruta` inyectado |
| `una_ruta_con_punto_delante_no_es_una_rama` | `.claude/skills` y `.claude/settings.local.json` |
| `la_frase_de_una_fila_no_arma_las_ramas_de_otra` | el defecto 3, en una cola sintética |
| `una_fila_pendiente_con_su_rama_fantasma_sale_con_su_numero` | «Cola — fila 2» |
| `lo_que_va_fuera_de_la_tabla_no_hereda_la_frase_de_una_fila` | la nota no se arma con la fila |
| `lo_que_va_fuera_de_la_tabla_sigue_siendo_el_item_del_encabezado` | la nota con su frase y su rama sale con el título del encabezado |
| `sin_predicado_una_ruta_que_existe_en_el_repo_no_es_una_rama` | el valor por defecto de `es_ruta` mira el árbol |
| `R1H01_las_filas_de_una_tabla_citada_tambien_son_items` | una tabla dentro de una cita se trocea igual |
| `R1H01_una_fila_citada_pendiente_sale_con_su_numero` | «Cola — fila 1» también citada |
| `R1H04_una_fila_sangrada_es_una_fila` | el mutante que la R1 dejó vivo |
| `R1H03_una_fila_sin_numero_se_identifica_por_su_linea` | «— línea 2», «— línea 3» |
| `R1H02_una_ruta_borrada_con_extension_larga_o_con_digitos_no_es_una_rama` | `.markdown`, `.ps1` |
| `R1H02_una_rama_con_version_solo_de_digitos_sigue_siendo_rama` | `release/1.2` |

Los seis de la R1 se escribieron tras la ronda: cuatro se vieron en rojo contra `8cebec4`, y los otros
dos —la fila sangrada y `release/1.2`— fijan un comportamiento que ya era correcto. El de la fila
sangrada es el que **mata al mutante que la R1 demostró vivo**: comprobado en memoria, junto con los
mutantes de cada remedio (quitar la cita, el identificador de reserva y la extensión vieja), cada
uno detectado por su test.

Y dos más que pidió la **cobertura del diff** —86 % en la primera verja, por debajo del umbral de aviso—: un bloque se cierra al empezar el siguiente encabezado (ningún test tenía dos), y `_ramas_conocidas` quita `origin/` y la referencia `HEAD`. Los dos fijan un comportamiento que ya era correcto; no se bajó el umbral.

## 4. Medido con el aviso real, no con los tests

Tras el arreglo, el aviso sobre el `PLAN.md` real da **un solo resultado**: `claude/verificar-pull-hash`,
en una nota de la cola —la de las decisiones del handoff del 2026-09-10, resueltas el 2026-09-13— que
conservaba el nombre de la rama y del worktree de un trabajo rescatado después en la fila #29. Es un
**acierto** según la doctrina (`docs/GOBERNANZA_FUENTES_VERDAD.md`, Drift #5: `PLAN.md` no restata
hechos de git): se retiró esa prosa y **el aviso queda en cero**.

## 5. Lo que no cubre, dicho

- **Ramas de más de un segmento** tras el prefijo (`feat/equipo/x`): ninguna en la historia del
  repo, y reconocerlas volvería a abrir la puerta a las rutas.
- **La ambigüedad entre rama y ruta que la sintaxis no cierra** (R1/H-02). Una ruta ya borrada sin
  extensión (`docs/carpeta-que-ya-no-existe`), o con una de más de ocho caracteres, se toma por rama:
  no está en el árbol y el nombre no la delata. Y al revés, una rama llamada como un fichero
  (`docs/cierre-117.md`, que git acepta) se toma por ruta. Ninguna de las dos formas aparece en la
  historia del repo.
- **La frase de pendiente sigue siendo la heurística**: una nota que narra historia con «sin
  commitear» y cita una rama **podada** sale, y eso es justo lo que la doctrina pide corregir; con
  una rama viva no sale, porque git la conoce.
- **Una tabla dentro de un bloque de código cercado** se trocea igual, como ya pasaba con los
  encabezados.

## 6. Ronda y modelo

**Una ronda sobre el diff.** Toca `scripts/`, no escribe datos de cliente ni decide qué cuenta como
revisado: es un aviso de higiene de la planificación, que no bloquea. Fila ordinaria de la política:
`gpt-6-sol` · `high` · `default`. Es la **segunda fila del ledger de calibración de la #38**.

## 7. Adjudicación de la revisión adversarial del diff (Codex, 2026-09-26) — LISTA-CON-CAMBIOS, remediado

- **Objeto revisado:** el diff `ca250a4..8cebec4` (`scripts/session_close.py` y `tests/test_session_close_aviso.py`), contra este plan
- **Ronda:** R1 de la pieza y la única de su presupuesto (toca `scripts/`, no datos de cliente)
- **Revisor:** Codex CLI `0.155.0-alpha.16.4`, `gpt-6-sol` · `high` · `default` (modelo y esfuerzo releídos del rollout; la velocidad, afirmada desde el lanzador conservado)
- **Informe recibido:** `docs/superpowers/plans/2026-09-26-mejoras-303-aviso-plan-git-r1-adversarial-review.md`
- **Hallazgos:** 4 — 1 `media`, 3 `baja`; 4 confirmados contra la fuente, 0 refutados
- **Remediado en:** este mismo PR, sobre `8cebec4`: `scripts/session_close.py`, seis tests más en `tests/test_session_close_aviso.py` y este plan (§1, §2, §3 y §5). **Ninguna ronda revisa el remedio**: el presupuesto de la pieza era una

**Los cuatro se reprodujeron contra el código, no contra el informe** (acta §2). Y antes de remediar,
la pregunta de siempre —**¿de qué frontera es esto un ejemplo?**—, porque dos de ellos eran el mismo:

- **H-01 (`media` · `acotado`) y H-04 (`baja` · `trivial`) son una sola frontera: qué es una fila.**
  El código miraba si la línea, sin espacios delante, empezaba por `|`; una fila dentro de una cita
  (`> | 1 | …`) empieza por `>` y volvía al bloque del encabezado, donde la frase de una fila armaba
  las ramas de otra —el defecto que la pieza existía para cerrar—. Y ningún test tenía una fila
  sangrada, así que quitar el `lstrip()` no ponía nada en rojo. **Remedio:** una fila es la línea
  cuyo contenido, **tras la sangría y las marcas de cita**, empieza por `|`; tests para la tabla
  citada, la fila citada con su número y la fila sangrada. La comprobación aparte del separador
  `|---|`, que el revisor señaló como no observable, se retira: sin frase de pendiente no podía
  cambiar la salida.
- **H-02 (`baja` · `acotado`).** La extensión de «hasta cinco letras» dejaba pasar como rama un
  fichero borrado con `.markdown` o `.ps1`, y descartaba como ruta una rama `docs/cierre-117.md`.
  **Remedio:** hasta ocho caracteres con al menos una letra, y **la ambigüedad que la sintaxis no
  cierra, declarada** en el comentario y en el §5, en las dos direcciones: el revisor pidió
  documentarla, no resolverla, y ninguna de las dos formas aparece en la historia del repo.
- **H-03 (`baja` · `trivial`).** Una fila sin primera celda salía titulada «Cola — fila », sin nada
  con que encontrarla. **Remedio:** «— línea <n>», la línea física.

**La cifra que no pudo reproducir, aceptada:** el 49 se midió sobre `4209582`, y el plan no lo decía;
sobre `ca250a4`, el objeto que recibió, son 56, todas `docs/…`. El §1 lo dice ahora, con los dos
commits. Y su observación de que `…sigue_siendo_el_item_del_encabezado` también pasaría sin trocear
la tabla es cierta: ese test fija el **título** de lo que queda fuera de la tabla, no el troceo, que
fijan los tres de filas.

**Y un defecto del objeto que la ronda no vio y la suite sí:** este mismo plan citaba como ejemplo
una ruta que no existe bajo `docs/superpowers/plans/`, y el guard G2 exige que toda cita a un spec o
plan resuelva en disco. No saltó antes porque el plan aún no estaba en git, y el guard solo lee lo
trackeado. Salió en la suite completa tras la ronda, y el ejemplo es ahora una ruta real. Para la
calibración es una **omisión de alcance, no de lectura**: el revisor declaró la suite SIN VERIFICAR,
y el mandato no se la pedía.

**Lo que intentó refutar y no pudo, y se conserva:** las formas de rama del repo se reconocen y las
rutas anidadas no; el separador de alineación y las filas normales se tratan bien; el 1 y el 0 del
§4 se reproducen; el retorno, la llamada con dos argumentos y los seis tests previos no cambian
(43/43 en su copia).

**Lo que NO cambia:** el aviso sigue siendo un aviso —no bloquea—; la frase de pendiente sigue siendo
la heurística, y los límites del §5 siguen declarados.
