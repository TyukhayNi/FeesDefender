---
tipo: handoff
estado: consumido
consumido_por: "Revisión ejecutada y archivada. Informe literal + digest en el acta `docs/superpowers/specs/2026-08-02-identidad-segmento-bundle-pieza-a-r1-claude-adversarial-review.md` (este mandato es su §0); adjudicación de los 24 hallazgos en el §14 del spec `2026-08-01-identidad-segmento-bundle-design.md` — NO-SHIP, 23 confirmados + 1 rebajado."
creado: 2026-08-02
origen: sesión Claude Code autora del plan de la pieza A (rama `claude/plan-next-step-a429e7`)
destino: revisor adversarial SUSTITUTO — sesión limpia de Claude Code (Opus), chat nuevo, sin el contexto de autoría
titulo: Encargo de revisión adversarial — identidad del segmento de bundle, pieza A (spec rev. 3 + plan)
revisor: Claude Code (sesión independiente)
motivo_sustituto: Codex sin cupo hasta el 2026-08-08 (indisponibilidad real, AGENTS.md §«Revisor sustituto»)
objeto_spec: docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md
objeto_plan: docs/superpowers/plans/2026-08-02-identidad-segmento-bundle-pieza-a.md
commit_revisado: a7f168c
ronda: "1"
ruta_informe: C:\Users\tnm33\Dev\_revisiones\2026-08-02-identidad-pieza-a-r1-claude.md
---

> **Andamio efímero** (gobernanza §5). Este fichero **es el mandato literal**: al archivar la revisión
> se copia entero al **§0 del acta** `2026-08-02-identidad-segmento-bundle-pieza-a-r1-claude-adversarial-review.md`.
>
> **Cómo se usa:** abrir una **sesión limpia** de Claude Code (chat nuevo, sin el contexto de esta
> sesión) y pegarle el texto que va de «MANDATO» hasta el final. No se le da la adjudicación del
> autor ni el razonamiento que llevó a estas decisiones: solo el objeto anclado y el mandato.

---

# MANDATO — revisión adversarial, ronda 1

## 0. Qué eres aquí, y qué no

Eres el **revisor adversarial** de un diseño y su plan de implementación. Tu trabajo es **atacar**:
buscar dónde el documento afirma algo que el código real no sostiene, dónde una promesa no se puede
cumplir, y dónde el plan no es ejecutable tal como está escrito.

**Tú no adjudicas.** No decides qué se acepta ni qué se remedia: eso lo hace, contra la fuente, quien
tiene la intención del encargo en la mano. Un hallazgo tuyo puede ser correcto y su remedio pasarse
de rosca; distinguirlo no es tu papel.

**Eres un revisor sustituto, y eso importa.** El revisor titular (Codex) está sin cupo hasta el
2026-08-08. Tú eres el mismo modelo que escribió el objeto que revisas, así que compartes sus puntos
ciegos y no tienes la tensión de interés que hace útil a un revisor externo. Se compensa así, y es
**obligatorio**:

- **No des por bueno nada sin abrir el fichero.** Ni una cifra, ni una cita de línea, ni una
  afirmación sobre lo que hace una función. Si el documento dice «`x` hace `y`», ábrelo y compruébalo.
- **Reproduce las mediciones en vez de creerlas.** Donde el documento afirme un número medido,
  vuelve a medirlo o declara explícitamente que no lo hiciste.
- **Usa subagentes en paralelo, una lente por hallazgo.** No un barrido único: varias lecturas
  independientes con criterios distintos (corrección, custodia de datos, ejecutabilidad del plan,
  ¿el test mata a su mutante?).

## 1. Objeto, anclado a commit

```text
worktree: C:\Users\tnm33\Dev\FeesDefender\.claude\worktrees\plan-next-step-a429e7
rama:     claude/plan-next-step-a429e7
objeto en:  a7f168c   ← el commit que introduce el plan
tip:        2cfccfe+  ← añade SOLO este encargo y su fila en docs/INDICE.md
```

Los dos documentos revisados son **byte-idénticos** entre `a7f168c` y el tip
(`git diff a7f168c -- <los dos ficheros>` sale vacío): trabaja sobre el tip. Comprueba que el árbol
está limpio antes de empezar, y vuelve a comprobarlo al terminar.

**Se revisan dos documentos, juntos:**

| | Documento | Alcance |
|---|---|---|
| A | `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md` | **rev. 3**, §0 y §3–§9 (la **pieza B**, §10–§12, está bloqueada y NO se revisa) |
| B | `docs/superpowers/plans/2026-08-02-identidad-segmento-bundle-pieza-a.md` | entero |

La rev. 3 del spec **no ha pasado revisión**: las dos pasadas anteriores (Codex, ambas NO SHIP)
fueron sobre las rev. 1 y rev. 2, y la rev. 3 introdujo material nuevo — el corte en dos piezas, el
ledger monotónico, el preflight y el guard bidireccional. Su §13 adjudica esas dos pasadas.

**Fuente que tienes que leer, no solo el diff** (un hallazgo que solo se sostiene mirando el diff
suele ser falso positivo): `core/split_documental.py`, `core/sala_maquina.py`,
`scripts/sala_maquina.py`, `core/anon/separar.py`, `core/utils.py`, `core/intake_log.py`, y los tests
`tests/test_split_documental.py`, `tests/test_split_sala_maquina_e2e.py`,
`tests/test_sala_maquina*.py`.

## 2. Solo lectura, y qué significa

El repo, los ficheros ignorados por git, `data/CASOS/`, la unidad `G:` y los sistemas externos (CRM,
Drive) son **entradas de solo lectura durante toda la revisión**.

**Sí** puedes ejecutar código y tests cuando **todas** sus escrituras van fuera del repo y no hay
efectos externos: `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, `--basetemp` fuera del árbol.
`git status --porcelain --untracked-files=all` antes y después es evidencia adicional, **no
sustituto** de la prohibición.

No escribas **nada** en `G:`. Si necesitas un caso real para medir, cópialo antes a un temporal fuera
del repo y mide sobre la copia.

## 3. Los puntos a atacar, ordenados por daño

Contéstalos **punto por punto, en una sección propia del informe**, con su número. Además, numera
tus hallazgos `H-NN` con severidad `B0` (bloqueante) · `A` (alto) · `M` (menor).

1. **¿Puede la pieza A dejar un caso real sin poder procesarse, o publicar una generación
   incoherente?** El plan afirma dos cosas que se sostienen la una a la otra: un manifiesto legacy
   sin `doc_id` **aborta** la corrida normal (decisión 4) y la vía de escape es `apply --force`,
   que reconcilia y acuña identidades nuevas; y al publicar se archiva **toda generación ajena al
   manifiesto** (decisión 10), incluidos los slugs del esquema viejo con sha. Monta un caso
   sintético con un bundle ya materializado con el esquema viejo (`parent__segNN_TIPO__sha8` + su
   MD + su `raw_text` + `_cobertura.json` + `_segmentacion.json` sin `doc_id`) y recorre el código:
   ¿qué pasa exactamente en `apply` normal, en `apply --force` y en `apply --solo`? ¿Queda algún
   camino en el que el guard aborte con salida 3 sin que el operador tenga forma de salir?
2. **¿Muerde el guard en el caso para el que se escribe?** Es el hallazgo N-B0-3 de la ronda
   anterior: cuando el bundle falla, `ejecutar` aísla el fallo y emite **una** fila de error con el
   slug del documento físico y **sin `parent_slug`**. El plan responde tomando el alcance del guard
   del **plan de la corrida** (`{d.slug for d in p if not d.skip}`) y no de las filas. Recorre todas
   las rutas —`apply`, `apply --solo`, `apply --force`, `reforzar`, camino imagen, camino
   passthrough, documento que falla antes de crear la carpeta del bundle— y di si hay alguna en la
   que el guard salga vacío o no llegue a correr.
3. **¿Es cierto el «cero bytes escritos» del preflight?** El plan dice que el preflight corre antes
   de procesar el primer documento, pero `_atomizar_correo` corre **antes** que él y escribe en
   `01_Procesado/Emails`, y el comando `plan` escribe manifiestos. ¿La promesa está acotada con
   honestidad en el documento, o promete de más? ¿Hay algún otro escritor entre el inicio de `apply`
   y el preflight?
4. **¿La reconciliación conserva la identidad correcta, y se detiene cuando debe?** Ataca
   `reconciliar_manifiesto` tal como el plan lo escribe: ¿alguna entrada puede heredar la identidad
   equivocada? ¿Puede `next_doc_id` decrecer, colisionar o saltarse un tombstone? ¿Qué hace con un
   manifiesto **mixto** (unas entradas con `doc_id` y otras sin él) — algo razonable o algo
   silencioso? ¿Y con un manifiesto cuyo `retirados` contiene un `doc_id` que también está en
   `segmentos`?
5. **¿Es correcta la publicación por generación bajo fallo parcial?** El contrato dice que las tres
   representaciones se publican por renames tras archivar la anterior como conjunto, y que si el
   archivado no puede completarse no se publica ninguna. Con **N** segmentos: ¿qué queda en disco si
   falla al mover el tercero de cinco? ¿Puede una fila de cobertura acabar declarando un `sha` que
   no corresponde a los bytes publicados? ¿Puede el `_staging` residual de una corrida abortada
   publicarse por error en la siguiente?
6. **¿La fusión por `doc_id` colapsa algo que no debe?** Casos a probar: dos bundles distintos cuyos
   segmentos comparten `doc_id`; un documento suelto (sin `doc_id`); filas **reconstruidas del MD**
   (que salen sin `doc_id` ni `parent_slug`, ver `reconstruir_cobertura_desde_md`) conviviendo con
   filas nuevas del mismo segmento. ¿Duplican? ¿Se pisan?
7. **¿Los tests del plan matan a sus mutantes?** Para cada uno de los diez tests del §8 del spec, di
   si el test que el plan escribe admite una implementación vacua. La ronda anterior encontró
   exactamente eso (N-M-1: los tests 4, 5 y 7 de la rev. 2 lo admitían) y el plan afirma haberlo
   cubierto con mutaciones explícitas. Compruébalo, no lo aceptes.
8. **¿Alguien más depende de la forma del slug?** El plan sostiene que fuera de
   `core/split_documental.py` y `core/sala_maquina.py` nadie parsea la forma
   `parent__segNN_TIPO__sha8` — que `preclasificar.py` y `scripts/detectar_ocr_ciego.py` lo tratan
   como opaco. Refútalo con un barrido propio sobre todo el repo, incluidas skills, plugins y
   scripts.
9. **¿Es EJECUTABLE el plan tal como está escrito?** ¿Alguna tarea usa algo que otra tarea todavía
   no ha creado? ¿Firmas incoherentes entre tareas? ¿Algún test del plan que no compile, que dependa
   de un fixture inexistente, o que en Windows se comporte distinto de lo que el plan afirma? ¿Algún
   paso que diga qué hacer sin decir cómo?
10. **¿Los límites que el plan declara están declarados o disimulados?** Las diez «decisiones que
    este plan cierra» y la entrada `MEJORAS #113`. ¿Alguno de esos límites es en realidad un defecto
    que se está normalizando por escrito?

## 4. Lo que NO tienes que hacer

- **No adjudiques** (§0).
- **No vuelvas a censar `G:`.** El censo del §2 del spec (5 grupos duplicados, 21 ficheros
  excedentes, 2 casos) está medido y no hay sospecha nueva que lo justifique. Si crees que la hay,
  dilo como hallazgo en vez de barrer.
- **No rediseñes la pieza B.** Está bloqueada por un lock roto que otra línea de trabajo arregla; su
  diseño (§10–§12 del spec) queda fuera de este encargo.
- **No propongas ampliar el alcance de la pieza A** salvo que la ampliación sea la única forma de
  cerrar un `B0`.

## 5. Cómo se entrega el informe

- **Ruta fijada, fuera del repo** (créala si no existe; **no sobrescribas informes anteriores**: sus
  digests son la cadena de custodia):

  ```text
  C:\Users\tnm33\Dev\_revisiones\2026-08-02-identidad-pieza-a-r1-claude.md
  ```

- **Devuelve por chat `ruta` y `sha256` canónico** —UTF-8, finales `LF`, un único salto final— antes
  de que se adjudique. Sin esa declaración tuya, la prueba de origen se reduce a que el autor
  calcule y escriba los dos lados.
- **Veredicto** del vocabulario cerrado, en la primera línea del informe: `SHIP` ·
  `LISTA-CON-CAMBIOS` · `REQUIERE-REVISION` · `NO-SHIP` · `NO-EJECUTABLE` · `SIN-VEREDICTO`.
- **Secciones obligatorias del informe**, además de la respuesta punto por punto al §3 y de la tabla
  de hallazgos `H-NN`:
  - `## Verificado ejecutando` — qué corriste y con qué salida, literal.
  - `## Verificado leyendo` — qué ficheros abriste enteros.
  - `## Lo que intenté refutar y NO pude` — lo que atacaste y aguantó. Esta sección es tan útil como
    los hallazgos.
  - `## NO VERIFICADO` — lo que no miraste, dicho sin adornos. **Un revisor que no corre no refuta:
    deja sin verificar**, y eso se declara en vez de disimularse.

## 6. Cómo se registrará tu revisión

Tu informe se archiva **literal**, con su digest, en un acta hermana del objeto revisado, y la
adjudicación va aparte, embebida en el spec y en el plan. En el acta constará
`revisor: Claude Code (sesión independiente)` — **nunca «Codex»** — y la adjudicación declarará en
prosa que la independencia de esta ronda es **más débil**, porque autor y revisor son el mismo
modelo. Si eso no se escribe, el registro miente y el mecanismo pierde su único sentido.
