---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-08-02-identidad-segmento-bundle-pieza-a.md
objeto_rev: "1"
objeto_secundario: docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md (rev. 3, §0 y §3-§9)
commit: a7f168c
ronda: "1"
revisor: Claude Code (sesión independiente)
independencia: sustituto-mismo-modelo
veredicto: NO-SHIP
marcador_nonce: qzwx
sha256_informe: 56422b0c3d9de1817b0205a3db6528f65ffe0a47d0b326a9298d8216309b36a4
adjudicado_en: docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md §14
---

> **Acta de revisión adversarial.** El §1 es la voz del revisor, archivada sin modificar. La
> **adjudicación** —qué acepté, qué rebajé y dónde se remedia— NO vive aquí: vive en el §14 del spec
> revisado. Esta acta no lleva estado de remediación.
>
> ⚠️ **La independencia de esta ronda es MÁS DÉBIL de lo habitual, y hay que decirlo.** El revisor
> no fue Codex —sin cupo hasta el 2026-08-08— sino una **sesión limpia de Claude Code**: el mismo
> modelo que escribió el objeto revisado. Comparte por tanto sus puntos ciegos y carece de la tensión
> de interés que hace útil a un revisor externo. Se compensó como manda `AGENTS.md` §«Revisor
> sustituto» (cuatro lentes en paralelo, prohibición de dar nada por bueno sin abrir el fichero,
> obligación de reproducir las mediciones), pero **esta ronda no sustituye a una de Codex**. El campo
> `independencia: sustituto-mismo-modelo` es nuevo: hasta hoy el único valor usado era
> `independiente`, y esta ronda no lo es. **Valor propuesto, pendiente de que lo cierre Nikolai.**

## 0. Mandato (literal, tal como se entregó)

> Copia literal de `docs/superpowers/handoffs/handoff-2026-08-02-identidad-pieza-a-encargo-revision.md`.
> Sus encabezados numerados (`## 0.` … `## 6.`) son del mandato, no de esta acta.

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

## 1. Informe recibido de Claude Code (sesión independiente), sin modificar

Digest declarado por el revisor por chat, antes de la adjudicación, y comprobado contra el fichero
recibido en `C:\Users\tnm33\Dev\_revisiones\2026-08-02-identidad-pieza-a-r1-claude.md`:
`56422b0c3d9de1817b0205a3db6528f65ffe0a47d0b326a9298d8216309b36a4`. Coinciden.

<!-- informe-literal:inicio:qzwx -->
NO-SHIP

# Revisión adversarial — identidad del segmento de bundle, PIEZA A (ronda 1)

| | |
|---|---|
| **Objeto A** | `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md` — rev. 3, §0 y §3–§9 |
| **Objeto B** | `docs/superpowers/plans/2026-08-02-identidad-segmento-bundle-pieza-a.md` — entero |
| **Commit del objeto** | `a7f168c` (verificado byte-idéntico al tip `4d4d23a`; árbol limpio antes y después) |
| **Revisor** | Claude Code (sesión independiente) — **revisor sustituto**, mismo modelo que el autor |
| **Fecha** | 2026-08-02 |
| **Ronda** | 1 |

> **Sobre la independencia de esta ronda.** Soy el mismo modelo que escribió lo que reviso, así que
> comparto sus puntos ciegos y no tengo la tensión de interés que hace útil a un revisor externo.
> Lo he compensado como manda el encargo: no he dado por buena ninguna cifra ni ninguna afirmación
> sobre el código sin abrir el fichero, he reproducido las mediciones en vez de creerlas, y he usado
> cuatro lentes en paralelo con criterios distintos. Aun así, esta ronda **no sustituye** a Codex, y
> el §6 declara sin adornos lo que no miré.

---

## 1. Respuesta punto por punto

### 1. ¿Puede la pieza A dejar un caso real sin poder procesarse, o publicar una generación incoherente?

**Sí. Es el hallazgo peor de esta ronda, y no es el camino que el punto anticipaba.**

Recorrí los tres caminos sobre un bundle ya materializado con el esquema viejo:

| camino | qué pasa |
|---|---|
| `apply` normal | El bundle **ni siquiera entra**: su sha está en `_sala_maquina_state.json`, así que `plan()` lo marca `skip=True` y el preflight lo salta (`if d.skip: continue`). El aborto de la decisión 4 solo se dispara si el estado se perdió. |
| `apply --force` | **Funciona, y la decisión 10 es genuinamente necesaria.** Reproduje que sin el barrido de generación ajena el guard aborta con salida 3 (escenario C de `probe_guard.py`). Con él, los slugs `…__segNN_TIPO__sha8` se archivan y la corrida cierra limpia. |
| `apply --solo <bundle>` | **Exit 2, sin salida.** `acotar_plan` fuerza `skip=False`, el preflight corre con `force=False` y exige `doc_id` → aborta. Y `--solo` **no se puede combinar con `--force`** (`scripts/sala_maquina.py:283-289` lo rechaza explícitamente). |

Es decir: la única vía para reprocesar **un** bundle legacy es un `--force` de **todo el caso**. `--solo` —la herramienta quirúrgica que D1 de `MEJORAS #90` construyó para exactamente esto— queda estructuralmente fuera de alcance. `MEJORAS #113` punto 3 dice «solo se reprocesa con `--force`», pero no dice que eso cancela la vía acotada. **→ H-03.**

**Y hay un camino que sí deja el caso sin poder procesarse, con salida 3 y sin remedio dentro de la
herramienta: la transición bundle → passthrough.** Toda la maquinaria nueva (reconciliación,
staging, `publicar_segmentos`, decisión 10) vive en la **rama split** de `_split_o_md`. La rama
passthrough (`core/sala_maquina.py:568-579`) queda intacta: escribe un MD suelto en `d.slug`,
devuelve **una** fila sin `parent_slug` ni `doc_id`, y **nunca llama a `publicar_segmentos`**.

Que un bundle se vuelva passthrough en un reproceso está vivo por dos vías, las dos en código real:

- `detectar` lanza → `core/sala_maquina.py:562-566` **degrada a passthrough a propósito** («PDF
  ilegible/corrupto/vacío para el detector»). Cualquier fallo de `cobertura_tinta` /pypdfium2 cae aquí.
- `detectar` devuelve 1 segmento. El delimitador exige `len(txt.strip()) < 10`
  (`core/split_documental.py:25,153-158`); un re-OCR que deposite diez caracteres de ruido en la hoja
  en blanco mata el separador. Que el re-OCR cambia el texto de forma no aditiva ya está medido en
  este proyecto (`MEJORAS #111`).

Reproducido con el guard **literal** del plan (`probe_guard.py`, escenario A):

```
--- A. reproceso que degrada a passthrough (orfanos de la generacion anterior)
    parents={'a__11223344'}
      FALLO: a__11223344__d01_DOC.pdf: PDF de segmento sin fila en la cobertura
      FALLO: a__11223344__d02_DOC.pdf: PDF de segmento sin fila en la cobertura
      FALLO: a__11223344__d03_DOC.pdf: PDF de segmento sin fila en la cobertura
    => EXIT 3
```

Las dos mitades son malas y son opuestas:

- **con `--force`:** `previa=[]`, los N PDF de segmento viejos son huérfanos → **salida 3**. Volver a
  lanzar da lo mismo, porque `detectar` sigue degradando. El archivado de la decisión 10, escrito
  justo para que `--force` no se atasque en salida 3, **no se ejecuta** porque vive en la otra rama.
  Sin borrar `02_Documentos/<slug>/` a mano no se sale.
- **sin `--force`** (vía `--solo`): las filas de segmento previas sobreviven a la fusión (su clave es
  `(rel_path, doc_id)`, la nueva fila passthrough es `(rel_path, slug)`), así que `con_fila` sigue
  conteniendo los slugs de segmento y **el guard pasa**. Quedan N artefactos viejos + el MD nuevo y
  N+1 filas para un `rel_path`: **el defecto que toda la spec existe para eliminar, reintroducido por
  la puerta del passthrough, en silencio y con el guard nuevo ciego.**

El test de aceptación no puede verlo: `_escalera_que_reescribe` emite siempre el mismo layout de 5
páginas con los mismos dos separadores, así que N→1 no se ejerce nunca. **→ H-01 (B0).**

### 2. ¿Muerde el guard en el caso para el que se escribe?

**Sí para N-B0-3, que es lo que se preguntaba. Con dos agujeros de alcance.**

Tomar el alcance del **plan** (`{d.slug for d in p if not d.skip}`) y no de las filas es correcto y
resuelve N-B0-3: verifiqué que cuando `ejecutar` aísla el fallo de un bundle emite **una** fila de
error con el slug del documento físico y `parent_slug=""` (`core/sala_maquina.py:732-733`), de modo
que un alcance derivado de filas saldría vacío; el del plan no. Recorrí `apply`, `apply --solo`,
`apply --force`, el camino imagen y el passthrough: en todos ellos el alcance sale no vacío y el
guard corre. El camino imagen está bien cubierto —el preflight filtra `d.ruta not in ("pdf",
"imagen")` y una imagen sí puede acabar en bundle vía `_ocr_y_extraer`—.

Los dos agujeros:

- **`reforzar` no tiene preflight.** El plan solo cablea el preflight en `apply`. Sobre un manifiesto
  legacy, `reforzar` entra en `_split_o_md` con `force=False` (no acepta `--force`: `sm.ejecutar(...,
  vision=True)` sin `force`), `validar_manifiesto` → `validar_identidad(exigir_doc_id=True)` lanza,
  `ejecutar` lo aísla, y el guard cierra con **salida 3 después de haber escrito**. `reforzar` no
  tiene válvula propia. Un bundle es alcanzable por `reforzar`: sus filas de segmento salen con
  `metodo` `pypdf`/`ocr`, que están en `_REFORZABLES`. **→ H-02.**
- **El guard solo audita `carpeta.glob("*.pdf")`.** Los `.md`/`.txt` que caigan en la carpeta del
  bundle son invisibles para siempre (ver punto 5). **→ H-10.**

### 3. ¿Es cierto el «cero bytes escritos» del preflight?

**No. El preflight en sí no escribe nada —eso lo verifiqué—, pero la promesa está redactada sobre la
corrida, y la corrida ya escribió.**

Mapeé `apply` línea a línea (`scripts/sala_maquina.py:273-299`). Entre el inicio y el punto donde el
plan inserta el preflight:

1. `_resolver_caso` — solo lee (verificado: `case_locator.resolve_ref`, `caso_path`, `path_for`).
2. `_exigir_vision_cableada` — solo `echo`.
3. **`_atomizar_correo(case_id, case_dir)` (`:293`) — ESCRIBE.** `atomize_dir` crea
   `01_Procesado/Emails/` con `mensajes/` y `adjuntos/`, y `_registrar_atomizado` (`:224`) **añade una
   línea a `00_Input/_intake_log.jsonl`** — la zona que `destino_seguro` veta para todo lo demás.
   Solo se libra un caso sin correo alguno (`:180`).
4. `_construir_plan` / `acotar_plan` — solo leen. Confirmé que `_sala_maquina_dir` es un join puro
   (sin `mkdir`), que `inventariar` solo hace `rglob`+`sha256`, y que `_cobertura_previa` (incluida
   la reconstrucción desde MD) no tiene efecto lateral.
5. El preflight: `carpeta_bundle_de` → `destino_seguro` no crea nada; `manifiesto_existe` y
   `leer_manifiesto` solo leen. **Cero escrituras: cierto.**

Cotejo literal de cada redacción:

| dónde | texto | veredicto |
|---|---|---|
| Spec §4 | «salida distinta de cero, **cero bytes escritos**» | **falso** |
| Spec §9 | «aborta desde la CLI con exit ≠ 0 y cero bytes escritos» | **falso** |
| Plan, Tarea 4 (docstring) | «Aquí no se escribe nada […] **así que la corrida muere antes de tocar disco**» | 1.ª mitad cierta, 2.ª **falsa** |
| Plan, Criterio de salida | «exit ≠ 0 y **cero artefactos escritos**» | **cierto** si «artefacto» = artefacto de Sala de máquina |

Ningún otro escritor entre el inicio y el preflight. El comando `plan` sí escribe manifiestos, pero
`apply` nunca lo invoca; su escritura de manifiesto ocurre en `_split_o_md`, **después** del
preflight. Ese trozo del diseño está limpio.

Lo que agrava: **ningún test del plan puede detectarlo**, porque `_caso` y la fixture `caso`
monkeypatchean `_atomizar_correo` a un no-op. Y el efecto está medido en la bitácora del propio
proyecto el día anterior (`docs/bitacora/2026.md:56`: «`apply` **atomiza el correo
incondicionalmente** antes del OCR»). **→ H-04.**

### 4. ¿La reconciliación conserva la identidad correcta, y se detiene cuando debe?

**En lo nuclear, sí.** Ejecuté el código verbatim de la Tarea 2 contra entradas que el plan no cubre:

- **`next_doc_id` no puede decrecer, colisionar ni saltarse un tombstone.** `validar_identidad` exige
  `nxt > max(vistos ∪ retirados)`, y la acuñación arranca siempre del high-water mark declarado. Un
  rango que reaparece tras haber sido retirado acuña `d03`, no reutiliza `d02`. La contradicción de
  la rev. 2 está genuinamente cerrada.
- **Ninguna entrada hereda identidad equivocada** por la vía normal: la herencia exige igualdad
  exacta de `pp`, y `detectar` produce rangos disjuntos.

Dos problemas reales, los dos reproducidos:

- **`pp` no canónico bloquea `--force` para siempre, con un mensaje que miente.** `por_pp` se indexa
  por la **cadena** `pp`, no por el rango. El manifiesto es «el gate editable del letrado» y su
  espejo MD invita a «ajusta pp/tipo/role». Si el letrado escribe `01-03` en vez de `1-3` —mismo
  rango— la herencia falla, el chequeo de solape sí casa, y `--force` aborta con «el segmento 1-3 no
  iguala ninguna entrada anterior y **solapa** con ['01-03']». Reproducido. Lo mismo con `1 - 3`.
  **→ H-06.**
- **El manifiesto mixto se resuelve en silencio, que es justo lo que la decisión 4 dice no hacer.**
  Bajo `--force`, `validar_identidad(previo, exigir_doc_id=False)` hace `continue` sobre las entradas
  sin `doc_id`; quedan fuera de `por_pp`, invisibles al chequeo de solape, y se les acuña identidad
  nueva sin aviso ni registro. Reproducido: previo `[d01/1-3, (sin id)/5-9]` → `['d01','d02']`,
  `acunados=['d02']`. El plan justifica el fail-closed de la decisión 4 con «No se acuñan
  identidades en silencio»; aquí lo hace. Y §11 exige que el mixto quede «definido explícitamente».
  **→ H-07.**
- **`retirados` con un `doc_id` que también está en `segmentos`:** correcto, aborta
  (`validar_identidad`). Atacado y aguantó.

### 5. ¿Es correcta la publicación por generación bajo fallo parcial?

**«No se publica ninguna» es cierto. «La generación anterior queda íntegra» no lo es, y hay un
residuo que nadie audita.**

- **Fallo al archivar el 3.º de 15.** El bucle `p.replace(archivo / p.name)` no es transaccional: 2
  ficheros quedan en `99_Versiones anteriores/`, 13 en su sitio. Nada se publica (**cierto**), pero la
  generación anterior queda **partida entre dos ubicaciones y sin registro de la partición** — y
  §8.8(a) del spec y el test del plan afirman «la generación anterior está **íntegra** en
  `99_Versiones anteriores/`». El propio test está escrito rodeando el hueco: inyecta el fallo en el
  `.md`, que es el índice 1 de `_rutas_de`, de modo que **el PDF ya está archivado** cuando corren
  los asertos, y el test no lo comprueba. **→ H-09.**
- **Fallo entre PDF y MD en la publicación: sin rollback.** El PDF nuevo queda publicado bajo un slug
  cuya fila declara el sha viejo — **exactamente el defecto con el que abre §7** («un fallo a media
  generación deja la fila declarando un sha que ya no corresponde a esos bytes»). El guard lo
  **detecta** (salida 3), no lo previene. Es una mitigación real, pero §7 promete prevención.
  **→ H-14.**
- **`_staging` residual sí puede publicarse.** `shutil.rmtree(staging, ignore_errors=True)` calla un
  sharing violation de Windows (cliente de Drive, antivirus, visor abierto), y el bucle final publica
  **todo lo que quede en staging sin filtrar por el manifiesto** — el whitelist de la decisión 10 se
  aplica al archivar y se abandona al publicar. Reproducido:

  ```
  carpeta_bundle despues: ['b__d02_VIEJO.md', 'b__d02_VIEJO.pdf', 'b__d02_VIEJO.txt',
                           'b__d03_VIEJO.md', 'indice.json']
    audita   -> ['b__d02_VIEJO.pdf']
    INVISIBLE-> ['b__d02_VIEJO.md', 'b__d02_VIEJO.txt', 'b__d03_VIEJO.md']
  ```

  El `.pdf` rancio es ruidoso (el guard lo caza). Los `.md`/`.txt` rancios aterrizan en la carpeta del
  bundle —no en `03_MD/` ni en `raw_text/`— y **ningún guard los mira nunca**, ni en esta corrida ni en
  ninguna futura: basura silenciosa, un Markdown de un documento jurídico junto a los PDF vigentes,
  indistinguible de un artefacto actual. **→ H-10.**
- **Un manifiesto con `segmentos: []` vacía el bundle en silencio y sale 0.** Nada exige ≥1 segmento:
  `validar_manifiesto` y `validar_identidad` pasan con la lista vacía, `materializar` devuelve `[]`,
  `publicados` queda vacío y el barrido de la decisión 10 **archiva todos los PDF del bundle**; no se
  publica nada, la cobertura no trae filas y el guard no ve ni ficheros ni filas. Exit 0.
  Reproducido. **→ H-11.**
- **Atacado y aguantó:** el `glob("*.pdf")` no ve `_staging` (es un subdirectorio, y el glob no es
  recursivo), `dict.fromkeys` deduplica bien, y ningún slug a punto de publicarse se archiva por
  error. Verificado.

### 6. ¿La fusión por `doc_id` colapsa algo que no debe?

**Los dos primeros casos aguantan. El tercero es una regresión que el cambio introduce.**

- Dos bundles distintos con segmentos que comparten `doc_id`: **no colisionan** (la clave lleva
  `rel_path`). Atacado y aguantó.
- Documento suelto sin `doc_id`: conserva `(rel_path, slug)`. Verifiqué que
  `test_fusionar_cobertura_conserva_n_segmentos_mismo_bundle` sigue dando 3.
- **Filas reconstruidas del MD conviviendo con filas nuevas del mismo segmento: duplican, y hoy no.**
  `reconstruir_cobertura_desde_md` emite `doc_id=""` (no puede saberlo) con el slug del stem del MD.
  La fila nueva del mismo documento lógico lleva `doc_id="d01"`. Claves distintas → dos filas.
  Reproducido:

  ```
  HOY  (rel_path, slug): 1 fila(s)
  PLAN (rel_path, doc_id|slug): 2 fila(s)
      slug=bundle__aabbccdd__d01_DOC_ARRAS doc_id=''   sha=(vacio)  nota='fila reconstruida del MD…'
      slug=bundle__aabbccdd__d01_DOC_ARRAS doc_id='d01' sha=cccccccc nota=''
  ```

  Dos filas **con el mismo slug**, una rancia y con sha vacío: la clase de defecto que la spec existe
  para eliminar, entrando por la puerta de la reconstrucción. El guard no la ve (la reconstruida se
  salta por `not c.doc_id`). Alcance: casos sin `_cobertura.json`. `test_fusionar_sin_doc_id_sigue_
  indexando_por_slug` usa dos documentos sueltos **distintos**, así que no ejerce el caso mixto.
  **→ H-05.**

### 7. ¿Los tests del plan matan a sus mutantes?

**Las siete mutaciones declaradas matan a su test. Pero hay DOS mutantes que sobreviven a la suite
entera, y los dos están en propiedades que §8 exige explícitamente.** La respuesta del plan a N-M-1
es correcta donde apunta; el problema es lo que quedó sin apuntar.

Las mutaciones declaradas, todas comprobadas:

| tarea | mutación declarada | ¿mata? |
|---|---|---|
| 1 | quitar `validar_doc_id` de `_slug_seg` | **sí** (DID NOT RAISE) — pero no prueba contención, ver H-08 |
| 2 | `if anterior is not None:` → `if False:` | **sí**, pero por **excepción de solape**, no por el aserto de herencia |
| 3 | `_clave_cobertura` → siempre `(rel_path, slug)` | **sí** — quedan 2 filas |
| 4 | comentar `sm.preflight_manifiestos` | **sí** — `apply` termina en exit 0, no lanza `typer.Exit` |
| 5 | mover el archivado tras la publicación | **sí** (mata 4 tests) |
| 6 | quitar el `try/except` de `append_event` | **sí** — `segmentos` queda vacío |
| 7 | quitar el bucle fichero → fila | **sí** — `fallos` vacío |
| 8 | revertir `_slug_seg` → «6 PDFs y 6 filas» | muere, **pero no así**: salen 3/3/9 (H-16) |

**N-M-1 está cubierto donde el plan dice.** Construí el mutante que §8.6 pide de verdad —«acuña
siempre»— y muere: `doc_ids=['d03','d04'] != ['d01','d02']`. Salvedad: la mutación **declarada**
(`if False`) no ejerce «acuña siempre» —aborta antes de llegar a acuñar, por el chequeo de solape—,
así que el paso del plan no comprueba lo que §8.6 nombra. El test sí. Imprecisión del paso, no
vacuidad del test.

**Mutante superviviente 1 — §8.4 «`retirados` acumula» no lo comprueba nadie.** Reproducido: cambiar

```python
"retirados": list(previo.get("retirados") or []) + [e["doc_id"] for e in retirados_entradas]
```

por solo `[e["doc_id"] for e in retirados_entradas]` —es decir, **tirar los tombstones previos en cada
reconciliación**— deja los dos tests que tocan `retirados` en verde:

```
correcto               retirar_el_maximo=PASA · entrada_desaparecida=PASA
MUTANTE (no acumula)   retirar_el_maximo=PASA · entrada_desaparecida=PASA
```

`test_retirar_el_maximo_no_permite_reutilizarlo` no asserta el `retirados` de salida (solo `nuevos` y
`next_doc_id`), y `test_entrada_desaparecida…` parte de `retirados=[]`. El escenario que los mata
—previo **con** un tombstone anterior **y** una retirada nueva— no lo cubre ningún test:

```
   correcto  retirados -> ['d02', 'd03']
   MUTANTE   retirados -> ['d03']
   perdido d02 del ledger -> validar_identidad PASA: d02 REUTILIZABLE
```

Es **N-B0-2 por la puerta de atrás**: perdido el tombstone, `validar_identidad` deja de vetar la
reutilización de ese `doc_id` y el *fallback* de `_next_doc_id_de` (que suma `retirados` al máximo
cuando el manifiesto no declara `next_doc_id` — caso real: manifiesto editado a mano) recalcula un
high-water **más bajo**. La propiedad que la spec pone por escrito en §8.4 es exactamente la que no
tiene test. **→ H-22.**

**Mutante superviviente 2 — §8.8(a) solo asserta los `.md`.** El spec pide literalmente «Se asertan
bytes de **las tres representaciones** y la cobertura antes y después». El test comprueba una:

```python
md_previos = {p.name: p.read_bytes() for p in (sm_dir / "03_MD").glob("*.md")}   # solo .md
...
assert {p.name: p.read_bytes() for p in archivo.glob("*.md")} == md_previos      # solo .md
```

Implementación mínima que pasa: `materializar(..., carpeta_salida=carpeta_bundle)` en vez de
`carpeta_salida=staging` —o sea, **sin publicación por generación para el PDF**—. Traza:
`emitido.replace(destino_pdf)` sobrescribe *in situ* los PDF de la generación anterior (mismo
`doc_id`, mismo tipo ⇒ mismo slug), esos bytes se pierden sin archivar; los MD/txt viejos sí se
archivan íntegros; la publicación revienta igual; el guard cierra con **exit 3** ✓ y el aserto de los
`.md` pasa ✓. **Verde con la generación anterior de PDF destruida** — que es justo el precio que §7
declara («`emitido.replace(destino_pdf)` sobrescribe») y el motivo por el que existe el staging.
Tampoco se asserta la cobertura. **→ H-23.**

**Vacuidad en el guard, y la regla que el plan se salta.** §8 se impone: «Los asertos sobre mensajes
usan frases con espacios, **nunca subcadenas que el nombre del test pueda inyectar** en la salida
capturada». **El plan la incumple en 10 de sus 11 asertos de mensaje**, y produce dos problemas:

- `test_guard_detecta_la_fila_sin_fichero` afirma `any("MD" in f)` y `any("raw_text" in f)` sobre
  mensajes que **embeben la ruta completa**: `"MD"` casa con el componente `03_MD` y `"raw_text"` con
  la carpeta `raw_text`, no con la etiqueta. Un mutante que etiquete **mal las tres representaciones**
  sobrevive:

  ```
  implementacion correcta  any('MD')=True  any('raw_text')=True  -> test PASA
  MUTANTE (todo 'PDF')     any('MD')=True  any('raw_text')=True  -> test PASA
  ```

- La inyección por nombre de test que la regla prohíbe **ocurre literalmente**: el tmpdir de
  `test_guard_detecta_el_sha_que_no_casa` es `test_guard_detecta_el_sha_que_0` —contiene `"sha"`— y
  las rutas van dentro de los mensajes, así que `any("sha" in f)` casaría con **cualquier** fallo de
  ese test. Hoy es inerte solo por suerte (bajo su mutación la lista sale vacía), pero es el patrón
  exacto que la spec veta. Medido. **→ H-12.**

**Y el formato del `doc_id` es más laxo de lo que §3.1 promete.** `re.compile(r"^d\d{2,}$").match`
acepta `"d01\n"` (el `$` casa antes del salto final) y dígitos Unicode (`"d١٢"`, con `int(...)==12`).
Ninguno está en el `parametrize`. Un `doc_id` con salto de línea pasa la validación, entra en el
nombre del fichero y revienta como `OSError` **dentro** de `materializar` — rompiendo «se valida antes
de cualquier I/O». Medido. **→ H-24.**

### 8. ¿Alguien más depende de la forma del slug?

**Barrido propio de todo el repo: la afirmación aguanta para código ejecutable. No aguanta para dos
contratos documentados.**

Nadie fuera de `core/split_documental.py` y `core/sala_maquina.py` parsea la forma del slug. Leí
enteros los dos ficheros citados y son honestamente opacos:
`.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:209` concatena `f"{fila['slug']}.md"`
leído de la cobertura, sin split ni regex; `scripts/detectar_ocr_ciego.py:83` toma `md.stem` como
token. Ningún `glob` del repo usa un patrón tipo `*__seg*`; todos son `*.md` / `*.pdf`. Revisados y
limpios: `streamlit_app.py`, `plugins/`, `plugin-src/`, `prompts/`, `.claude/commands/`,
`_skills_ARCHIVO/`, `verificar_sala.py`, `manifiesto_a_catalogo.py`, y los `output_slug` de
`sala_lectura.py` / `extractor.py` / `ocr_textless_pdfs.py` (todos slug **padre**, que no cambia).

*(La cita `preclasificar.py:209` del spec §1.2 es correcta; comprobé la línea.)*

Lo que sí queda falso y **no está en la lista de ficheros del plan** —dos documentos que declaran el
contrato de nombres—:

- `.claude/skills/organizar-sala-maquina/SKILL.md:78-81`, el bloque de layout que un agente de Cowork
  lee para saber qué encontrará en disco. La línea 80 dice `03_MD/ {slug__sha8}.md … (uno por
  documento lógico)`: tras el cambio los MD de segmento **no llevan sha8**.
- `docs/superpowers/specs/2026-07-14-split-sala-maquina-design.md:113` (`# {bundle_sha8}__seg{NN}_
  {TIPO}__{seg_sha8}`), `:241`, `:286-287` y `:344` («Nombre `seg_slug` (resuelve colisión de stem
  #47)»), que es el contrato de salida al que apunta `docs/MEJORAS_FUTURAS.md:3104`.

**→ H-13.**

### 9. ¿Es EJECUTABLE el plan tal como está escrito?

**Las Tareas 1–7 sí. La Tarea 8 no, y el cableado de tests viola la restricción global nº 1 del
propio plan.**

Lo que está bien y verifiqué una por una: **las 14 citas de línea son exactas** (`DocLogico:61-71`,
`construir_manifiesto:220-229`, `escribir_manifiesto:232-248`, `validar_manifiesto:261-270`,
`_slug_seg:280-283`, `materializar:286-322`, `DocCobertura:155-169`, `fusionar_cobertura:323-356`,
`_escribir_md:502-514`, `_split_o_md:549-608` y `:592-601`, `apply:290-306`,
`test_split_documental.py:203-204`, `test_split_sala_maquina_e2e.py:90-94`). No hay referencias
adelantadas: ninguna tarea usa un símbolo que otra posterior cree. Las firmas casan entre tareas. Los
símbolos que el plan asume existen todos con la firma asumida. El cuerpo nuevo de `_split_o_md` solo
usa variables realmente en ámbito. `shutil` está bien señalado como import nuevo. `#113` es el número
correcto (`MEJORAS_FUTURAS.md` acaba en `## 112`). El blast radius de `monkeypatch.setattr(Path,
"replace", …)` es seguro (el predicado solo casa con la pata de publicación; `write_md` usa
`write_text`). `_sello_reproceso()` produce `2026-08-02_101010` exactamente como esperan los tests
(verificado ejecutando `now_iso`).

Los bloqueantes:

- **La medición read-only de la Tarea 8 no importa.** `from core.config import CASOS_ROOT` →
  `ImportError` (ejecutado). No existe tal nombre: `core/config.py:31` define
  `Settings.casos_root`, y todo el repo usa `from core.config import settings`. Además el
  `rglob('_cobertura.json')` recorrería **el Drive entero**, no los 5 casos. **→ H-15 (B0).**
- **La comprobación de vacuidad de la Tarea 8 no es seguible.** «revertir temporalmente `_slug_seg` a
  la forma vieja […] con su llamada» esconde una refactorización multi-sitio: tras la Tarea 1 el slug
  se calcula en el bucle de pre-validación, **antes** de que exista `seg_sha`; y `_split_o_md` llama a
  `_slug_seg` dos veces más para el archivado, una de ellas sobre una generación **anterior** cuyo sha
  se desconoce. La predicción «6 PDFs y 6 filas» tampoco se sostiene, porque el barrido de la
  decisión 10 archivaría los sobrantes. **→ H-16.**
- **Los tests nuevos escriben en el `CASOS_ROOT` REAL.** `core/sala_maquina.py:26` y
  `scripts/sala_maquina.py:18` importan `append_event` **por separado**. El helper `_caso` parchea solo
  `cli.append_event`; el `append_event(case_id, "split_documental", …)` de `_split_o_md`
  (`core/sala_maquina.py:602`) va al real, y `core/intake_log` resuelve la ruta con su propio
  `caso_path` → `settings.casos_root`. Verificado ejecutando:

  ```
  settings.casos_root = C:\tmp\FAKE_CASOS_ROOT
  log_path("W-TEST99") = C:\tmp\FAKE_CASOS_ROOT\W-TEST99\00_Input\_intake_log.jsonl
  ```

  Los dos tests que corren `cli.apply` de punta a punta sobre un bundle
  (`test_apply_sale_con_3_…` y `test_un_fallo_a_media_publicacion_…`) crearían
  `<CASOS_ROOT>/W-TEST99/00_Input/_intake_log.jsonl` **en el Drive**, en cada corrida de la suite por
  defecto. El autor conoce las dos ligaduras —la Tarea 6 parchea `sm.append_event` y la fixture de la
  Tarea 8 parchea ambas—: a `_caso` simplemente le falta. Contradice la restricción global nº 1
  («Ningún caso real se toca»). **→ H-17.**
- **Todo «Expected: PASS» que incluya `tests/test_split_sala_maquina_e2e.py` es vacuo.** Ese fichero
  declara `pytestmark = pytest.mark.slow` (línea 17) y `tests/conftest.py` omite `slow` salvo
  `--runslow`, que el plan **nunca pasa**. Consecuencia: la corrección del manifiesto que la Tarea 2
  ordena en ese fichero **no se ejecuta nunca** y el implementador verá verde. **→ H-18.**
- **La Tarea 1 deja el árbol rojo, invisiblemente.** Tras la Tarea 1, `materializar` llama a
  `validar_doc_id(None)` sobre el manifiesto sin `doc_id` de
  `test_split_sala_maquina_e2e.py:90-94` → error aislado → `assert len(seg_rows) == 2` falla. Solo se
  repara en la Tarea 2, y por H-18 nadie lo vería. **→ H-19.**
- **`except split.ManifestValidationError` no cubre un manifiesto corrupto.** `leer_manifiesto` es un
  `json.loads` pelado; un `_segmentacion.json` truncado lanza `JSONDecodeError`, que **no** es
  `ManifestValidationError`, y escapa del `try` del CLI como traceback en vez de salida 2. Siendo el
  fichero que el letrado edita a mano, el JSON roto es el fallo más probable y es el único que el
  preflight no atrapa. **→ H-20.**
- **Menor, no determinista:** «borrar la línea `previa = …` conservando su comentario donde estaba la
  lectura» — el comentario real es un bloque de 4 líneas (`:301-304`) y el plan aporta otro de 2 para
  la ubicación nueva; dos implementadores producirán dos diffs. Y la Tarea 8 pide escribir «el hash
  del squash» y `(PR #NNN)` **antes** de que el PR exista.

### 10. ¿Los límites declarados están declarados o disimulados?

Ocho de las diez decisiones y las tres entradas de `#113` están honestamente declaradas: la 1, 2, 3,
5, 6, 7, 8 y 9 dicen lo que hacen y por qué, y la decisión 10 va acompañada del razonamiento correcto
(lo verifiqué: sin ella `--force` sobre legacy aborta con 3 — escenario C).

Dos se quedan cortas:

- **Decisión 4 / `#113` punto 3** declara el coste como «solo se reprocesa con `--force`», y omite que
  eso **cancela `--solo`** para ese bundle, que es la herramienta construida para el reproceso acotado
  (D1 de `MEJORAS #90`) y que el CLI prohíbe combinar con `--force`. El coste real es «reprocesar el
  caso entero», no «usar otra bandera». **→ H-03.**
- **Decisión 8** («el guard no audita el daño histórico») está bien razonada, pero el límite que no se
  declara es el complementario: **el guard no audita nada que no sea un `.pdf`**, ni la rama
  passthrough. Eso no es una frontera elegida, es un hueco (H-01, H-10).

Y una cifra que ya no es cierta: **spec §9 declara «base: 2612 passed, 77 skipped, 7 xfailed»**. Medido
en el commit anclado: **2630 passed, 77 skipped, 7 xfailed** (2714 total, 0 failures). Los skips y los
xfail casan; los passed van 18 por debajo. El Paso 0 del plan ya ordena medir de nuevo y «no contra el
número que diga ningún documento», así que el plan está bien; la cifra del spec es la que sobra.
**→ H-21.**

---

## 2. Hallazgos

| ID | Sev. | Hallazgo | Dónde |
|---|---|---|---|
| **H-01** | **B0** | Transición bundle → passthrough: la rama passthrough no archiva ni publica. Con `--force` deja huérfanos → salida 3 **sin salida dentro de la herramienta** (la decisión 10 vive en la otra rama); sin `--force` conserva la generación vieja en silencio con el guard ciego — el defecto que la spec existe para eliminar | `core/sala_maquina.py:562-579`; plan Tareas 5 y 7 |
| **H-15** | **B0** | La medición read-only de la Tarea 8 no importa: `from core.config import CASOS_ROOT` → `ImportError`. Además recorrería el Drive entero | plan Tarea 8, Step 3 |
| **H-17** | **A** | Los tests nuevos escriben en el `CASOS_ROOT` real (`W-TEST99/00_Input/_intake_log.jsonl`): a `_caso` le falta parchear `sm.append_event`. Viola la restricción global nº 1 del plan | plan Tarea 4 `_caso`; `core/sala_maquina.py:26,602` |
| **H-02** | **A** | `reforzar` no tiene preflight ni `--force`: un manifiesto legacy lo lleva a salida 3 **después de escribir**, sin válvula propia | plan Tarea 7; `scripts/sala_maquina.py:338-387` |
| **H-03** | **A** | `apply --solo` no puede alcanzar un bundle legacy (exit 2) y `--solo`+`--force` está prohibido: el único remedio es `--force` de todo el caso. `#113` no lo declara | decisión 4; `scripts/sala_maquina.py:283-289` |
| **H-04** | **A** | «Cero bytes escritos» es falso: `_atomizar_correo` escribe `01_Procesado/Emails/` y una línea en `00_Input/_intake_log.jsonl` antes del preflight. Los tests lo parchean, así que ninguno puede detectarlo | spec §4 y §9; `scripts/sala_maquina.py:293` |
| **H-05** | **A** | Regresión de la fusión: fila reconstruida del MD + fila nueva del mismo segmento producen **dos** filas con el mismo slug donde hoy hay una | plan Tarea 3 `_clave_cobertura` |
| **H-06** | **A** | `pp` no canónico (`01-03`, `1 - 3`) rompe la herencia y bloquea `--force` para siempre, con un mensaje que dice «solapa» sobre el mismo rango | plan Tarea 2 `reconciliar_manifiesto` |
| **H-07** | **A** | Manifiesto mixto bajo `--force`: acuña identidades en silencio, contra la propia decisión 4 y contra §11 | plan Tarea 2 `validar_identidad` |
| **H-08** | **A** | «Cinturón y tirantes» de §3.1 es falso: `_destino_en_bundle` **no** caza el `doc_id` que ejecutó la 2.ª revisión (`..\..\fuera`), porque el prefijo `parent_slug__` absorbe un `..`. El test ejerce una forma que nunca ocurre | spec §3.1; plan Tarea 1 |
| **H-09** | **A** | «La generación anterior queda íntegra en `99_Versiones anteriores/`» es falso si el archivado falla a medias: queda partida entre dos ubicaciones, sin registro. El test está escrito rodeando el hueco | spec §8.8(a); plan Tarea 5 |
| **H-14** | **A** | La publicación no tiene rollback: el defecto «fila con sha que no casa» que §7 dice arreglar se **detecta**, no se **previene** | spec §7; plan Tarea 5 |
| **H-18** | **A** | Todo «Expected: PASS» con `test_split_sala_maquina_e2e.py` es vacuo: el fichero es `slow` y el plan nunca pasa `--runslow`. La corrección de manifiesto de la Tarea 2 no se ejecuta nunca | plan Tareas 2, 5, 8 |
| **H-22** | **A** | **Mutante superviviente:** «no acumular tombstones previos» pasa toda la suite. §8.4 exige «`retirados` acumula» y ningún test lo asserta; el efecto es reabrir N-B0-2 (un `doc_id` retirado vuelve a ser reutilizable) | plan Tarea 2 |
| **H-23** | **A** | **Mutante superviviente:** el test de custodia §8.8(a) solo asserta los `.md`, así que una implementación **sin staging para el PDF** pasa en verde habiendo destruido los PDF de la generación anterior. §8.8 pedía las tres representaciones **y** la cobertura | plan Tarea 7 |
| **H-10** | **M** | El `_staging` residual se publica sin filtrar; los `.md`/`.txt` rancios caen en la carpeta del bundle y **ningún guard los mira nunca** (solo audita `*.pdf`) | plan Tareas 5 y 7 |
| **H-24** | **M** | `re.match(r"^d\d{2,}$")` acepta `"d01\n"` y dígitos Unicode: pasa la validación y revienta como `OSError` **dentro** de `materializar`, contra el «se valida antes de cualquier I/O» de §3.1. `re.fullmatch(r"d[0-9]{2,}")` lo cierra | plan Tarea 1 |
| **H-11** | **M** | Un manifiesto con `segmentos: []` pasa la validación, archiva todos los PDF del bundle, no publica nada y sale 0 | plan Tarea 2 |
| **H-12** | **M** | Vacuidad en el guard: `any("MD" in f)` / `any("raw_text" in f)` casan con **componentes de ruta**, no con la etiqueta; un mutante que etiquete mal las tres sobrevive. El plan incumple la regla de §8 sobre subcadenas en 10 de 11 asertos, y la inyección por nombre de test que esa regla veta **ocurre literalmente** (tmpdir `test_guard_detecta_el_sha_que_0` contiene `"sha"`) | plan Tarea 7 |
| **H-13** | **M** | Dos contratos documentados quedan falsos y no están en la lista de ficheros: `organizar-sala-maquina/SKILL.md:78-81` y el spec `2026-07-14…:113,241,286-287,344` | — |
| **H-16** | **M** | La comprobación de vacuidad de la Tarea 8 es una refactorización multi-sitio descrita en un paréntesis («con su llamada», en singular, cuando hay tres), y su predicción «6 PDFs y 6 filas» es **falsa**: medido, salen **3 PDFs, 3 filas, 9 archivados**. La propiedad «sustituye en vez de añadir» la entrega la decisión 10, no el `doc_id`, y el test solo muere por un aserto de **nombre** en su última línea | plan Tarea 8, Step 2 |
| **H-19** | **M** | La Tarea 1 deja el árbol rojo hasta la Tarea 2, y por H-18 nadie lo vería | plan Tareas 1-2 |
| **H-20** | **M** | Un `_segmentacion.json` corrupto lanza `JSONDecodeError`, que escapa del `except ManifestValidationError` como traceback en vez de salida 2 | plan Tarea 4 |
| **H-21** | **M** | La base de la suite del spec §9 (2612) está desfasada: medida, 2630 passed / 77 skipped / 7 xfailed | spec §9 |

**2 B0 · 13 A · 9 M.**

Los dos `B0` son de naturaleza distinta: **H-01** es un defecto de diseño de la pieza A (un caso real
puede quedar sin poder procesarse, y por el otro lado el defecto original se reintroduce en silencio);
**H-15** es un fallo mecánico de un paso del plan y se arregla con una línea. De los `A`, los que a mi
juicio pesan más para volver a mirar son **H-22** y **H-23**: son las dos únicas propiedades de §8 con
mutante vivo, y las dos protegen bytes o identidad, no comodidad.

---

## Verificado ejecutando

Todo bajo `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider` y `--basetemp` fuera del árbol. Trabajé
sobre una copia extraída con `git archive 4d4d23a` a un directorio temporal, **nunca sobre el
worktree**; el árbol objetivo se comprobó limpio al empezar y al terminar (`4d4d23a`, `git status
--porcelain --untracked-files=all` → 0 líneas). No escribí nada en `G:` ni ejecuté nada contra un caso
real.

1. **Anclaje.** `git rev-parse a7f168c:<los dos ficheros>` == `4d4d23a:<idem>` → byte-idénticos
   (`e5453cd…` y `c022531…`). `git log a7f168c..4d4d23a` = 2 commits que solo añaden el propio encargo
   y su fila en `docs/INDICE.md`.
2. **Base de la suite** (`--junit-xml`, porque el resumen de pytest no se captura por tuberías en
   Windows): `tests=2714 failures=0 errors=0 skipped=84`, de los cuales `xfailed=7` y skips reales 77
   → **2630 passed**. Suite verde en el commit anclado.
   *Trampa que pisé y dejo escrita: con un `--basetemp` largo,
   `test_migrar_nombres_informe.py::test_resumen_cuenta_por_estado` falla (`assert 2 == 0`) por el
   presupuesto de MAX_PATH. Con `--basetemp=C:/tmp/fdbase` pasa. No es un fallo del repo; es del
   arnés. Quien re-mida esta base debe usar una ruta corta.*
3. **`probe_traversal.py`** — `_destino_en_bundle` aislado sobre cinco `doc_id`: `..\..\fuera` y
   `../fuera` **no se cazan** (resuelven dentro de la carpeta); `..\..\..\..\..\..\Windows\Temp\pwn` y
   `d01/../../fuera` sí. → H-08.
4. **`probe_guard.py`** — `verificar_integridad_bundles` copiado **literal** del plan, tres escenarios:
   passthrough con huérfanos → EXIT 3; mismo disco fuera de alcance → ok; legacy sin archivar → EXIT 3
   (confirma que la decisión 10 es necesaria). → H-01.
5. **`probe_recon.py`** — Tareas 2 verbatim, cinco entradas no cubiertas + los dos mutantes de §8.6.
   `pp` no canónico aborta; mixto acuña en silencio; tombstones y high-water correctos; `acuna_siempre`
   muere. → H-06, H-07, punto 7.
6. **`probe_fusion.py`** — clave de hoy vs. clave del plan sobre fila reconstruida + fila nueva: 1 fila
   → 2 filas. → H-05.
7. **`probe_staging.py`** — bucle final de `publicar_segmentos` verbatim: los `.md`/`.txt` rancios
   acaban en `carpeta_bundle` y quedan fuera del `glob("*.pdf")` del guard. → H-10.
8. **`probe_vacio.py`** — manifiesto `segmentos: []` pasa `validar_manifiesto` y `validar_identidad`.
   → H-11.
9. **`probe_handle.py`** — `_try_pypdf` seguido de `Path.replace` sobre el mismo PDF (1 y 40 páginas):
   `replace OK` en ambos. El handle se libera. (Refutación, ver §5.)
10. **Vacuidad del guard** — mutante que etiqueta mal las tres representaciones: `any("MD")` y
    `any("raw_text")` siguen True. → H-12.
11. **`probe_tombstone.py`** — Tarea 2 verbatim + los asertos verbatim de los dos tests que tocan
    `retirados`, contra el mutante «no acumula»: **PASA los dos**. Y el escenario no cubierto
    (tombstone previo + retirada nueva) da `['d03']` en vez de `['d02','d03']`, tras lo cual
    `validar_identidad` acepta reutilizar `d02`. → H-22.
12. **Anclas del regex** — `re.match(r"^d\d{2,}$")` acepta `"d01\n"` y `"d١٢"` (`int(…)==12`);
    `re.fullmatch(r"d[0-9]{2,}")` rechaza ambos. → H-24.
13. **Nombre del tmpdir de pytest** — `test_guard_detecta_el_sha_que_no_casa` → tmpdir
    `test_guard_detecta_el_sha_que_0`, que **contiene `"sha"`**; el de la fila sin fichero no contiene
    `"MD"`. Es la inyección por nombre de test que §8 prohíbe, ocurriendo. → H-12.
14. **`from core.config import CASOS_ROOT`** → `ImportError` (ejecutado). → H-15.
15. **`log_path("W-TEST99")` con `CASOS_ROOT` a un temporal** → confirma que resuelve bajo
    `settings.casos_root`. → H-17.
16. **`now_iso()` → `_sello_reproceso`** → `2026-08-02_112123`, formato exacto que los tests esperan.
17. `tests/test_migrar_nombres_informe.py` completo con basetemp corto → 17 passed.
18. **Simulación de aceptación con `_slug_seg` revertido** (una de las lentes, arnés propio fuera del
    repo): `PDFs 3 · MDs 3 · raw_text 3 · filas 3 · archivados 9`; el test solo muere en la última
    línea, por el `glob(f"{parent}__d01_*.md")`. → H-16.

## Verificado leyendo

Enteros: `core/split_documental.py` (323 l.), `scripts/sala_maquina.py` (391 l.),
`.claude/skills/organizar-sala-lectura/scripts/preclasificar.py` (403 l.), `scripts/detectar_ocr_ciego.py`,
el spec rev. 3 (§0 y §3–§9, y §10–§13 en diagonal por contexto) y el plan entero (2077 l.).

Por regiones, con las líneas citadas comprobadas una a una: `core/sala_maquina.py` (`DocPlan`,
`DocCobertura`, `plan`, `reconstruir_cobertura_desde_md`, `acotar_plan`, `render_cobertura`,
`fusionar_cobertura`, `cobertura_desde_dicts`, `destino_seguro`, `_sala_maquina_dir`, `_escribir_md`,
`_calidad`, `_anotar`, `_split_o_md`, `_ocr_y_extraer`, `ejecutar`, `inventariar`),
`core/intake_log.py` (`append_event`, `log_path` y sus imports), `core/utils.py` (`now_iso`,
`output_slug`), `core/extractor.py:104-118`, `tests/conftest.py` (marcador `slow`),
`tests/test_sala_maquina.py:199-286`, `tests/test_split_documental.py:174-221`,
`tests/test_split_sala_maquina_e2e.py`, `.claude/skills/organizar-sala-maquina/SKILL.md:76-82`,
`docs/superpowers/specs/2026-07-14-split-sala-maquina-design.md:113,241,286-287,344`.

## Lo que intenté refutar y NO pude

Esto aguantó, y cuenta tanto como lo de arriba:

- **La decisión central del guard (alcance desde el plan, no desde las filas) resuelve N-B0-3.**
  Confirmé leyendo `ejecutar:732-733` que la fila de error sale con el slug físico y `parent_slug=""`,
  y que por tanto un alcance derivado de filas saldría vacío. El del plan no. En `apply`, `--solo`,
  `--force`, camino imagen y passthrough el alcance sale no vacío.
- **La decisión 10 es necesaria y suficiente para lo que dice cubrir.** Reproduje el escenario sin
  ella (salida 3 sobre legacy) y con ella (limpio). El razonamiento del plan es correcto.
- **El ledger monotónico, tal como está diseñado, cierra de verdad la contradicción de la rev. 2.**
  Retirar el máximo y acuñar después no lo reutiliza; los tombstones se acumulan; `next_doc_id` nunca
  decrece. Ataqué con `next_doc_id` ausente, con `retirados` altos y con rangos que reaparecen:
  correcto en los tres. *(El diseño aguanta; lo que no hay es test que lo sostenga — H-22.)*
- **La fusión por `doc_id` no colapsa dos bundles distintos** que compartan `doc_id`, ni los N
  segmentos de un bundle, ni las dos rutas byte-idénticas. Los tres tests existentes siguen válidos.
- **`glob("*.pdf")` no ve `_staging`** (subdirectorio, glob no recursivo), `dict.fromkeys` deduplica
  bien y ningún slug a punto de publicarse se archiva por error. Ataqué esta línea a fondo y está
  limpia.
- **`_try_pypdf` libera el handle**, así que el fallo de publicación de H-14 no es rutinario en
  Windows por esa vía (era mi hipótesis; la medí y cayó).
- **Nadie fuera de los dos módulos parsea el slug** — barrido propio de todo el repo, incluidas
  skills, plugins, `plugin-src/`, `prompts/`, comandos y el archivo de skills. La afirmación del plan
  aguanta para código ejecutable.
- **Las 14 citas de línea del plan son exactas**, y no hay una sola referencia adelantada entre tareas.
  Busqué específicamente firmas incoherentes y variables fuera de ámbito en el `_split_o_md` nuevo: no
  las hay.
- **El sha de la cobertura se mide sobre los bytes que se publican.** No encontré ningún camino en el
  que diverjan salvo la publicación parcial de H-14.
- **`_sello_reproceso`, `#113` como número libre, `Segmento` posicional, `ResultadoEscalera(salida,
  "redo")`, el blast radius de parchear `Path.replace`**: todos comprobados, todos correctos.
- Una pista que perseguí y resultó ser **mía, no del objeto**: en el encargo de una de mis lentes
  escribí «`core/anon/preclasificar.py`», ruta que no existe. El spec cita `preclasificar.py:209` sin
  ruta y **la línea es correcta**. No es un hallazgo.

## NO VERIFICADO

- **No ejecuté ni un solo test del plan contra una implementación real**: no existe todavía. Lo que
  digo sobre los tests sale de (a) leer su código, (b) copiar verbatim a un arnés fuera del repo el
  código de producción que el plan escribe y correr los mutantes contra los asertos verbatim de los
  tests. Eso es sólido para la lógica pura (identidad, ledger, reconciliación, fusión, guard) y **más
  débil para lo que pasa por el CLI y el disco**: H-23 y el mutante de `preflight` están **trazados**
  contra el código real, no ejecutados de punta a punta. Las conclusiones son sobre el **plan como
  está escrito**.
- **No construí el mutante mínimo para los diez ítems de §8 de forma exhaustiva.** Probé 13 mutantes
  entre las cuatro lentes y yo; dos sobrevivieron (H-22, H-23). No afirmo que no haya más.
- **No re-censé `G:`** (el encargo lo prohíbe) y **no comprobé cuáles de los 5 casos reales carecen de
  `_cobertura.json`**, que es lo que determina el alcance real de H-05. Tampoco medí con qué
  frecuencia se da en el corpus real la transición N→1 de H-01: establecí que los dos mecanismos
  existen en el código y son plausibles tras un re-OCR, no que hayan ocurrido.
- **No verifiqué el censo del §2 del spec** (5 grupos duplicados, 21 ficheros excedentes, 2 casos).
  Queda como el autor lo dejó.
- **No revisé la pieza B** (§10–§12) ni el §13, salvo en diagonal para entender el contexto.
- **No corrí la suite con `--runslow`**, así que la base de 2630 excluye los tests `slow`. La cifra es
  comparable con la del Paso 0 solo si este se mide igual — que es justamente parte de H-18.
- **No probé en un segundo entorno.** Todo se midió en esta máquina (Windows 11, Python 3.14.4, venv
  del repo). El `_try_pypdf` que libera el handle y el `resolve()` que absorbe el `..` son
  observaciones de esta versión de pypdf y de este Python.
<!-- informe-literal:fin:qzwx -->

## 2. Evidencia verificada al adjudicar

Lo que comprobé **yo** contra la fuente antes de adjudicar, con ruta y línea. No es la evidencia del
revisor: es la que sostiene mi veredicto sobre cada hallazgo suyo.

### 2.1 Ejecutado

| # | Qué ejecuté | Resultado | Sostiene |
|---|---|---|---|
| E1 | `from core.config import CASOS_ROOT` | `ImportError: cannot import name 'CASOS_ROOT'`; el nombre real es `settings.casos_root` (`WindowsPath`) | H-15 |
| E2 | `re.compile(r"^d\d{2,}$").match(s)` sobre `d01`, `d01\n`, `d١٢`, `D01`, `d1` | acepta `'d01\n'` **y** `'d١٢'` (con `int(...) == 12`); `re.fullmatch(r"d[0-9]{2,}")` rechaza los dos | H-24 |
| E3 | `_destino_en_bundle` verbatim del plan sobre tres `doc_id` de traversal | `..\..\fuera` → `…\bundle-slug\fuera_X.pdf` = **NO se caza** (el prefijo `bundle-slug__` absorbe el primer `..`); `../fuera` tampoco; `d01/../../fuera` **sí** | H-08 |
| E4 | El regex real de G7 (`tests/test_docs_gobernanza.py:278-283`) contra el encabezado que el propio encargo proponía | `(Claude Code (sesión independiente), 2026-08-02)` **FALLA**: el grupo `revisor` es `[^,)]+` y no admite el paréntesis anidado. `Claude Code [sesión independiente]` pasa | — (defecto del encargo, no del objeto) |
| E5 | Suite completa en el commit anclado, `--basetemp=C:/tmp/fdbase`, `--junit-xml` | ver §2.3 | H-21 |

### 2.2 Leído, con la línea comprobada

| # | Qué abrí | Qué dice | Sostiene |
|---|---|---|---|
| L1 | `core/sala_maquina.py:559-579` | la rama passthrough degrada **a propósito** cuando `detectar` lanza, escribe el MD en `d.slug` y devuelve una fila sin `parent_slug` ni `doc_id`; toda la maquinaria nueva del plan (reconciliación, staging, `publicar_segmentos`, barrido de la decisión 10) vive en la **otra** rama | H-01 |
| L2 | `core/split_documental.py:25,144-158` | el delimitador de segmento exige `len(txt.strip()) < 10`: diez caracteres de ruido de OCR en la hoja en blanco colapsan N→1 | H-01 |
| L3 | `scripts/sala_maquina.py:338-387` | `reforzar` llama a `sm.ejecutar(..., vision=True)` **sin** `force`, y el plan solo cablea el preflight en `apply` | H-02 |
| L4 | `scripts/sala_maquina.py:283-289` + `core/sala_maquina.py:259-287` | `--solo` y `--force` se rechazan combinados; `acotar_plan` fuerza `skip=False`, así que el bundle pedido entra en el preflight con `force=False` | H-03 |
| L5 | `scripts/sala_maquina.py:293` y `:224` | `_atomizar_correo` corre **antes** del punto donde el plan inserta el preflight, y `_registrar_atomizado` añade una línea a `00_Input/_intake_log.jsonl` | H-04 |
| L6 | `core/sala_maquina.py:26` y `:602`; `scripts/sala_maquina.py:18` | `core.sala_maquina` importa `append_event` por su cuenta; el helper `_caso` del plan solo parchea `cli.append_event`, de modo que el evento `split_documental` iría al `CASOS_ROOT` real | H-17 |
| L7 | `core/sala_maquina.py:219-251` (`reconstruir_cobertura_desde_md`) + Tarea 3 del plan | la fila reconstruida sale con `doc_id=""` y el slug del stem del MD; con la clave nueva, una fila reconstruida y una fila fresca del mismo segmento dejan de colapsar | H-05 |
| L8 | Tarea 2 del plan (`reconciliar_manifiesto`) | `por_pp` se indexa por la **cadena** `pp`, no por el rango; y `validar_identidad(..., exigir_doc_id=False)` hace `continue` sobre las entradas sin `doc_id`, que quedan fuera de `por_pp` | H-06, H-07 |
| L9 | Tarea 5 del plan (`publicar_segmentos`) | el bucle de archivado no es transaccional y el bucle final publica **todo** lo que quede en staging sin filtrar por el manifiesto | H-09, H-10 |
| L10 | Tarea 2 del plan + sus dos tests de `retirados` | ninguno de los dos asserta el `retirados` de salida con un tombstone previo: el mutante «no acumula» los deja verdes | H-22 |
| L11 | Tarea 7 del plan, `test_un_fallo_a_media_publicacion…` | asserta **solo** los `.md`; §8.8 del spec exige «los bytes de las tres representaciones y la cobertura antes y después» | H-23 |
| L12 | Tarea 7 del plan, `test_guard_detecta_la_fila_sin_fichero` | `any("MD" in f)` y `any("raw_text" in f)` casan con los componentes de ruta `03_MD` y `raw_text`, no con la etiqueta | H-12 |
| L13 | `tests/conftest.py:35-41` + `tests/test_split_sala_maquina_e2e.py:17` | los `slow` se saltan salvo `--runslow`, que el plan nunca pasa | H-18, H-19 |
| L14 | `.claude/skills/organizar-sala-maquina/SKILL.md:78-81` | el bloque de layout promete `03_MD/ {slug__sha8}.md … (uno por documento lógico)`: falso para los segmentos tras el cambio | H-13 |
| L15 | `docs/superpowers/specs/2026-07-14-split-sala-maquina-design.md:113,241,286-287,344` | las cuatro citas existen y documentan el contrato de nombres viejo | H-13 |
| L16 | Tarea 4 del plan (`preflight_manifiestos`) + `core/split_documental.py:251-253` | `leer_manifiesto` es un `json.loads` pelado: un JSON truncado lanza `JSONDecodeError`, que no es `ManifestValidationError` | H-20 |
| L17 | Tarea 2 del plan (`validar_identidad`) | nada exige ≥1 segmento; con `segmentos: []` pasan las dos validaciones | H-11 |

### 2.3 La base de la suite

Medida por mí en el commit anclado, con `--basetemp` corto (con ruta larga,
`test_migrar_nombres_informe.py::test_resumen_cuenta_por_estado` falla por presupuesto de `MAX_PATH`
y **no es un fallo real** — la trampa que el revisor dejó escrita y que confirmo):

```text
tests=2714  failures=0  errors=0  skipped=84      (84 = 77 skips reales + 7 xfailed)
=> 2630 passed
```

Medido con `--basetemp=C:/tmp/fdbase` y `--junit-xml`, sobre el commit anclado y **antes** de
tocar nada. El spec §9 declaraba **2612 passed**: la cifra está desfasada en 18, y los skips y los
xfail sí casan. Confirma **H-21**.

## 3. Lo que esta acta NO cubre

Se declara en vez de darse por bueno (`docs/DEAD_ENDS.md`: un revisor que no corre no refuta):

- **No se re-censó `G:`** — el censo del §2 del spec (5 grupos duplicados, 21 ficheros excedentes en
  2 casos) queda como estaba, sin verificación independiente en esta ronda.
- **No se comprobó qué casos reales carecen de `_cobertura.json`**, que es lo que fija el alcance
  real de **H-05**.
- **H-23 está TRAZADO contra el código, no ejecutado de punta a punta**: lo confirmado es el hueco de
  cobertura del test frente a lo que §8.8 exige por escrito, no la ejecución del mutante concreto.
- **No se midió la frecuencia real de la transición N→1** de **H-01**: lo establecido es que sus dos
  mecanismos existen en el código y son plausibles tras un re-OCR, no que hayan ocurrido.
- **El recuento «10 de 11 asertos» de H-12** no lo he recontado; lo verificado es la vacuidad de los
  dos asertos concretos.
- **No se revisó la pieza B** (§10–§12 del spec), fuera de alcance por encargo.
