---
tipo: plan
estado: vigente
creado: 2026-09-26
objeto: MEJORAS #303 — el aviso «PLAN.md ↔ git» de scripts/session_close.py: una ruta no es una rama, `claude/` sí lo es, y cada fila de una tabla es su propio ítem
---

# MEJORAS #303: el aviso «PLAN.md ↔ git» que gritaba siempre y no acertaba nunca

> **Estado (2026-09-26):** construido con TDD; una ronda de Codex sobre el diff (§6), adjudicada
> en la §7. Fila **#43** de `PLAN.md`.

**Encargo.** Nikolai eligió el `#303` el 2026-09-26 y pidió hacerlo en la sesión de `crm_ficha`,
en un PR aparte. El backlog decía «una ronda: toca `scripts/`, no datos de cliente».

## 1. Lo medido, antes de tocar nada

Sobre el `PLAN.md` de `main` del 2026-09-26, `_plan_items_desfasados` daba **49 «ramas fantasma»
en un solo ítem** —«🎯 Cola priorizada»— y **las 49 eran rutas `docs/…`**. No eran un defecto sino
tres, dos independientes y uno de granularidad:

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
  del nombre, para que el backtracking no corte `docs/superpowers/plans/x.md` en `docs/superpower`.
- **Una ruta no es una rama:** un nombre que acaba en extensión de letras (`_RE_EXTENSION`: `.md`,
  `.py`; `release/1.2` sigue siendo rama) o que existe en el árbol del repo. Lo segundo va por un
  parámetro nuevo, `es_ruta`, de `_plan_items_desfasados`; por defecto `_es_ruta_del_repo`, que mira
  `ROOT / token`. El llamador no lo pasa: dos tests existentes doblan la función con dos argumentos.
- **Cada fila de una tabla es su propio ítem**, titulado «<encabezado> — fila <primera celda>»; lo
  que queda del bloque fuera de la tabla —prosa y notas— sigue siendo el ítem del encabezado, como
  antes. El separador `|---|` no es fila. El tipo de retorno no cambia.

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

## 4. Medido con el aviso real, no con los tests

Tras el arreglo, el aviso sobre el `PLAN.md` real da **un solo resultado**: `claude/verificar-pull-hash`,
en una nota de la cola —la de las decisiones del handoff del 2026-09-10, resueltas el 2026-09-13— que
conservaba el nombre de la rama y del worktree de un trabajo rescatado después en la fila #29. Es un
**acierto** según la doctrina (`docs/GOBERNANZA_FUENTES_VERDAD.md`, Drift #5: `PLAN.md` no restata
hechos de git): se retiró esa prosa y **el aviso queda en cero**.

## 5. Lo que no cubre, dicho

- **Ramas de más de un segmento** tras el prefijo (`feat/equipo/x`): ninguna en la historia del
  repo, y reconocerlas volvería a abrir la puerta a las rutas.
- **Una ruta ya borrada**, sin extensión y de un solo segmento (`docs/carpeta-que-ya-no-existe`), se
  tomaría por rama: no está en el árbol y el nombre no la delata.
- **La frase de pendiente sigue siendo la heurística**: una nota que narra historia con «sin
  commitear» y cita una rama **podada** sale, y eso es justo lo que la doctrina pide corregir; con
  una rama viva no sale, porque git la conoce.
- **Una tabla dentro de un bloque de código cercado** se trocea igual, como ya pasaba con los
  encabezados.

## 6. Ronda y modelo

**Una ronda sobre el diff.** Toca `scripts/`, no escribe datos de cliente ni decide qué cuenta como
revisado: es un aviso de higiene de la planificación, que no bloquea. Fila ordinaria de la política:
`gpt-6-sol` · `high` · `default`. Es la **segunda fila del ledger de calibración de la #38**.
