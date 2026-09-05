---
tipo: revision-adversarial
objeto: "diseño «_caso.md: actualizar conserva lo que no es del registrador» (rev. 1), para cerrar MEJORAS #146"
objeto_rev: "1"
commit: "41a3141"
ronda: "1"
revisor: Claude Code (sesión independiente)
veredicto: LISTA-CON-CAMBIOS
marcador_nonce: kqzw
sha256_informe: 95a18400d1f1c292c1a90d61dda92e6d57246f52bc95cfbd2502cf33d482fe1b
adjudicado_en: docs/superpowers/specs/2026-09-05-caso-md-preservar-al-actualizar-design.md §8
adjudicador: Claude Code
independencia_adjudicacion: "más débil — autor y revisor son el mismo modelo (AGENTS.md §Revisor sustituto)"
---

> **Acta de revisión adversarial R1 sobre un DISEÑO.** El §0 es el mandato literal, el §1
> conserva la voz del revisor sin una coma cambiada, el §2 es la evidencia que verifiqué por mi
> cuenta y el §3 el mapa hallazgo → dónde se remedió.
>
> **Dónde vive la adjudicación:** en la **rev. 2 del propio diseño**
> (`2026-09-05-caso-md-preservar-al-actualizar-design.md`, §8), que es la forma que manda
> `CLAUDE.md`: la decisión pertenece al documento que la decisión modificó.
>
> **Revisor sustituto, y su independencia es MÁS DÉBIL.** Codex no tiene cupo (2026-09-05). El
> revisor fue un subagente de Claude Code lanzado sin el contexto de autoría, con el objeto anclado
> a un commit y este mandato, y nada más (`AGENTS.md` §«Revisor sustituto»). Autor y revisor son el
> mismo modelo y comparten puntos ciegos; lo que compensa es que ejecutó sondas contra un
> `CASOS_ROOT` temporal en vez de creer al diseño, y que la adjudicación volvió a abrir la fuente
> para los cinco hallazgos que cambian el diseño. Se registra como `revisor: Claude Code (sesión
> independiente)`, nunca como «Codex».
>
> **Esta es la primera de las dos rondas** que la pieza compra por radio de daño: escribe el
> fichero que guarda el lock de checkout y cierra un defecto que destruye una nota del abogado. La
> segunda va sobre el diff.
>
> **Higiene del workdir:** el directorio se creó vacío para esta ronda (`revision-146-r1-diseno-1050`)
> y el revisor lo declaró limpio en su primera línea. El digest se recalculó al recibir el informe
> (`95a18400…`) y coincide con el declarado. El revisor anotó que durante la ronda apareció en el
> worktree un fichero de tests sin trackear —los mutantes que yo escribía en paralelo— y que no lo
> leyó; el commit revisado no lo contiene.

## 0. Mandato, literal

# MANDATO — Revisión adversarial R1 sobre un DISEÑO (FeesDefender, MEJORAS #146)

## Higiene, primero

- Trabajas en **solo lectura**. No editas, no creas ni borras nada dentro del repo. No haces `git checkout`, `stash`, `commit` ni ningún comando que mueva el árbol.
- Tu único fichero de salida es `INFORME.md` en el directorio de trabajo que se te indica. Si al llegar encuentras allí cualquier fichero distinto de `MANDATO.md`, **no lo leas** y decláralo en la primera línea del informe.
- Fecha del sistema: 2026-09-05. Escribe en castellano.
- No has visto la conversación del autor y no debes buscarla. Solo tienes el objeto anclado a un commit y este mandato.

## Objeto

- Repo: `C:\Users\tnm33\Dev\FeesDefender\.claude\worktrees\mejoras-apertura-expedientes-c1945d` (worktree; **no** salgas de él a la raíz del repo).
- Commit: `41a3141`.
- Documento revisado: `docs/superpowers/specs/2026-09-05-caso-md-preservar-al-actualizar-design.md` (rev. 1).
- Código que el diseño describe y va a modificar: `core/case_manager.py` (`_write_case_index`, `register_expediente`, `register_drive_ev`, `cache_drive_folder_info`, `ensure_case`, `_atomic_write_caso_md`), `core/utils.py` (`read_md`, `write_md`, `build_frontmatter`), `core/casos/case_locator.py` (`read_case_meta`), `core/repository_checkout.py`, `scripts/remove_expediente_link.py`, `docs/MEJORAS_FUTURAS.md` entrada 146.

## Qué se te pide

Atacar el diseño. **Nada se da por bueno sin abrir el fichero**: cada afirmación del diseño que cite una línea, una función o una medición la compruebas tú en el código del commit y anotas `fichero:línea`. Si el diseño dice «el grep no encuentra ningún consumidor del cuerpo», corres tú el grep y dices qué sale. Si dice que hoy los campos del lock sobreviven, lo demuestras o lo desmientes con una sonda (puedes ejecutar Python **contra un directorio temporal fuera del repo**, nunca contra `data/CASOS/` ni contra `G:`).

Lentes, en orden de daño:

1. **Pérdida de datos que el diseño introduciría.** ¿Hay algún camino en que la «actualización preservadora» del §3.1 borre o corrompa algo que hoy sobrevive? Piensa en `meta` con claves que sean `None` en el `CaseMeta` reconstruido pero con valor en lo persistido (`{**persistido, **asdict(meta)}` pisa con `None`), en el orden de precedencia entre `fm` y `propias`, en `sudespacho_expedientes` duplicado en dos niveles, en el lock de checkout (`estado_repositorio`, `checkout_*`) y en `bucket_override`.
2. **La detección «nadie lo tocó» (§3.1.4 y §3.3).** ¿Es correcta la comparación? ¿Qué pasa con `\r\n`, con espacios de borde, con un cuerpo vacío, con un `meta` persistido incompleto (sin `titulo`, sin `case_id`), con una plantilla que cambia entre versiones? ¿Puede la regla regenerar un cuerpo que sí tenía una edición humana? ¿Puede congelar uno que no la tenía y hacer que el índice mienta sobre los expedientes?
3. **Frontera y alcance (§2, §6).** ¿Cierra la propiedad o solo los tres ejemplos? ¿Queda algún escritor de `_caso.md` fuera de `_write_case_index` y `_atomic_write_caso_md` que reconstruya? Lista todos los que escriben `_caso.md` (`grep -rn "_caso.md" core scripts streamlit_app.py`) y clasifícalos.
4. **Interacción con la biblioteca de casos.** `repository_checkout`, `MERGE_EXCLUSIONS`, el `_caso.md` de la copia del Drive durante un checkout: ¿el diseño rompe alguna invariante que ellos den por sentada?
5. **Atomicidad y concurrencia (§3.1.5).** ¿La escritura atómica propuesta es equivalente a la de `_atomic_write_caso_md`? ¿Qué pasa si dos registradores corren a la vez (hoy también pasa; di si el diseño lo empeora)?
6. **Mutantes (§5).** ¿Los diez matan el defecto y protegen contra endurecer de más? ¿Falta alguno? ¿Alguno pasaría en verde con el código actual sin que el diseño lo declare como positivo?
7. **Enunciados más anchos que lo que la función puede prometer.** Señala cualquier frase del diseño que prometa más de lo que el código propuesto puede garantizar.

## Formato del informe

`INFORME.md`, y nada más. Estructura:

1. Primera línea: higiene del workdir (`limpio` o qué encontraste).
2. Hallazgos numerados `H-01`, `H-02`… en **orden de severidad** (CRÍTICO / ALTO / MEDIO / BAJO), cada uno con: título, severidad, **evidencia** (`fichero:línea`, salida de la sonda si la hubo), por qué importa, y remedio propuesto (breve).
3. Lo que verificaste y **resultó correcto** (con evidencia), para que se sepa qué se miró.
4. Lo que **no pudiste verificar**, y por qué. Nunca lo des por bueno ni por malo.
5. Veredicto, uno de: `SHIP` · `LISTA-CON-CAMBIOS` · `REQUIERE-REVISION` · `NO-SHIP` · `NO-EJECUTABLE`. Una frase que lo justifique.

Al terminar, calcula el `sha256` del fichero canonicalizado (UTF-8, finales `LF`, un único salto final) y devuélvelo junto con la ruta. En tu respuesta final devuelve **solo**: la ruta, el `sha256`, el veredicto y el número de hallazgos por severidad. El contenido del informe lo leeré del fichero.

## 1. Informe recibido de Claude Code (sesión independiente), sin modificar

<!-- informe-literal:inicio:kqzw -->
Higiene del workdir: **limpio** (solo `MANDATO.md` al llegar). Repo en `41a3141` (`git log -1` lo confirma; `git diff --stat 556b8b2 41a3141` sobre los cuatro ficheros del objeto está vacío, así que las líneas del diseño citadas «sobre `556b8b2`» valen sobre este commit). Durante la revisión apareció en el worktree un fichero **untracked** `tests/test_caso_md_preservar_al_actualizar.py` (mtime 10:52:43, posterior al mandato): no forma parte del commit revisado y **no lo he leído**. Las sondas corrieron con `CASOS_ROOT` bajo `…\scratchpad\revision-146-r1-probes\CASOS` (borrado al terminar), con el intérprete de `.venv` y el `core` del worktree (`core.__file__` verificado). Ninguna escritura en el repo, `data/CASOS/`, `G:` ni `H:`.

# Revisión adversarial R1 — diseño `2026-09-05-caso-md-preservar-al-actualizar-design.md` (rev. 1)

revisor: Claude Code (sesión independiente) · fecha: 2026-09-05 · objeto: commit `41a3141`

## 1. Hallazgos

### H-01 · ALTO · La regla «nadie lo tocó» congela el cuerpo ante cambios que no son una nota, y a partir de ahí el índice miente sobre los expedientes

**Evidencia.** Implementé el §3.1 literal (plantilla extraída de `core/case_manager.py:111-143`, comparación `strip()` contra la plantilla con el `meta` persistido) y lo ejecuté:

- **D1** (nota + `register_drive_ev` + `register_expediente`): `decision: conservado | 648 en fm: True | 648 en cuerpo: False`. Tras la primera nota, **ningún** expediente ni ID de Drive posterior vuelve a aparecer en el cuerpo. El diseño lo acepta implícitamente, pero M2 (§5) solo exige «la nota sigue y el expediente está en el frontmatter»: no fija que el cuerpo deje de listarlo, así que la conducta declarada no queda pinada por ningún test.
- **D3** (mutador de frontmatter al estilo `scripts/remove_expediente_link.py:57-81`, que borra una entrada de `sudespacho_expedientes` y de su espejo en `meta`): `tras quitar 648 del fm, el cuerpo aún lista 648: True` → siguiente `register_drive_ev`: `decision: conservado | cuerpo lista 648 (borrado): True | cuerpo lista Drive E&V: False`. El cuerpo generado ya no coincide con la plantilla del `meta` persistido (le sobra una línea), la regla lo clasifica como «tocado» y **lo congela con un expediente que ya no está vinculado**. Mismo efecto con `scripts/limpieza_post_audit.py:153-178` y con cualquier `update_pull_state` que cambie `element` (`:1469-1470`).
- **D9** (wikilink que inserta `registrar_outputs.py` en `## Navegación`, ver H-04): `decision: conservado | wikilink sobrevive: True | 648 en cuerpo: False`. Cualquier caso al que la skill `cendoj-descarga` haya registrado una sentencia queda congelado, sin que nadie haya escrito una «nota».

**Por qué importa.** El §3.4 rechaza «conservar siempre el cuerpo» porque «deja el cuerpo rancio en el caso normal … y el cuerpo es la vista humana del índice». Pero con la regla propuesta el caso normal se vuelve rancio en cuanto pasa por él cualquier escritor que no sea un registrador —y en el repo ya hay dos (D3, D9)—, y además rancio **en la dirección peligrosa**: lista lo desvinculado y omite lo vinculado. Es la pregunta de la lente 2 («¿puede congelar uno que no la tenía y hacer que el índice mienta?») con respuesta afirmativa y reproducida. El §3.3 solo declara el punto ciego de la plantilla legacy; estos dos no están declarados.

**Remedio.** (a) Detección por huella, no por reconstrucción: al generar el cuerpo, escribir su `sha256(cuerpo.strip())` en el frontmatter (p. ej. `meta.cuerpo_generado_sha256`); «nadie lo tocó» es `sha(actual) == guardado`; sin clave guardada (legacy), caer a la comparación con la plantilla. Elimina el falso «tocado» de D3 (la huella no depende del `meta`) y no toca ficheros existentes. (b) Para D9 y para no congelar de más, **marcadores introducidos perezosamente**: cuando el cuerpo está intacto se regenera *con* marcadores alrededor de las secciones generadas; en adelante se regeneran solo esas y se conserva el resto. No exige migración —el §3.3 seguiría valiendo para lo legacy— y devuelve al «caso normal» la propiedad que el §3.4 dice querer. (c) En cualquier caso, M2 debe afirmar explícitamente lo que el diseño decida sobre el cuerpo.

### H-02 · MEDIO · La propiedad del §2 no cierra el frontmatter: el estado D8 que escribe `update_pull_state` en `sudespacho_expedientes` sigue destruyéndose

**Evidencia.** `update_pull_state` (`core/case_manager.py:1401-1492`) muta **solo** la lista top-level `fm["sudespacho_expedientes"]`; el espejo `meta.sudespacho_expedientes` no se toca. `register_drive_ev` (`:599`, `:613-614`) y `cache_drive_folder_info` (`:714`, `:727-728`) reconstruyen el `CaseMeta` desde `fm["meta"]`, así que su `meta.sudespacho_expedientes` es el **espejo rancio**, y la clave top-level `sudespacho_expedientes` está entre las diez «propias» del §3.1.2, que pisan lo persistido.

- **P5 (hoy)**: tras `register_expediente` + `update_pull_state(last_sync, doc_ids, by_carpeta)`: top-level `['by_carpeta','doc_ids','documents_total_crm','element','id','input_dir','last_sync']`, espejo `['element','id','input_dir']`. Tras `register_drive_ev`: top-level `['element','id','input_dir']`; `doc_ids sobrevive: False | last_sync sobrevive: False`.
- **D4 (diseño simulado)**: `decision: regenerado | doc_ids sobrevive en top-level: False`. El §3.1 lo hereda intacto.
- **P5b (hoy)**: entrada creada por `update_pull_state` sin `register_expediente` previo → tras `register_drive_ev` la lista queda `[]` y `get_case_status(...)["expedientes"] == []`: **el vínculo entero desaparece**.

**Por qué importa.** El §2 enuncia «toda escritura … conserva lo que no es del escritor», y este es dato escrito por otro módulo en el mismo fichero que el sumidero seguirá pisando. El §3.1.3 justifica la precedencia de `asdict(meta)` con que «los registradores ya han coalescido desde lo persistido»: para el espejo es cierto; para la clave top-level, dos de los tres registradores no coalescen de ahí. No lo subo a ALTO porque el daño práctico hoy es acotado: `read_pull_state` no tiene llamadores de producción (`grep` sobre `core/`, `scripts/`, `streamlit_app.py`: solo su definición) y los flujos reales (`sync_sudespacho.py:170,251`, `abrir_caso.py:726`) llaman a `register_expediente` antes del pull, así que P5b no ocurre hoy en producción. Pero la propiedad que el diseño promete es falsa para una de las diez claves.

**Remedio.** En el sumidero, fusionar `sudespacho_expedientes` **por entrada**: para cada `id`, `{**persistida, **nueva}`, y conservar las entradas persistidas que la nueva lista no trae salvo que el registrador declare un borrado (hoy ninguno borra por esta vía; `remove_expediente_link` va por `_atomic_write_caso_md`). Espejo `meta.sudespacho_expedientes` = resultado. Mutante: `register_expediente` → `update_pull_state(doc_ids=…)` → `register_drive_ev` → `read_pull_state(...)["doc_ids"]` sigue. Hoy y con el §3.1 tal cual, ese test muere.

### H-03 · MEDIO · Un `_caso.md` sin frontmatter parseable deja de autorrepararse y pasa a congelarse corrupto; la creación sigue escribiendo en sitio

**Evidencia.** **D6**: truncado el fichero al primer tercio (simula el corte «a mitad» que el propio §3.1.5 describe, que con el diseño sigue siendo posible **en la creación**, que el §3.1 deja «como hoy»): `read_md` (`core/utils.py:262-270`, `_FM_RE` exige el cierre `---\n`) devuelve `({}, texto_entero)`; el §3.1 hace `{**{}, **propias}`, compara el «cuerpo» —que es el fichero truncado con su frontmatter dentro— con la plantilla, no coincide → `decision: conservado | body empieza: '---\ncase_id: EV-2026-001\ntipo: caso_index…'`. Resultado: frontmatter nuevo + un segundo frontmatter truncado embebido en el cuerpo, **congelado para siempre** por H-01. Hoy ese fichero se reconstruye limpio en la siguiente llamada.

**Por qué importa.** El diseño convierte un fallo recuperable en uno persistente, justo en el escenario que cita como motivación de la atomicidad. Y los registradores parsean con `text.split("---", 2)` (`:184-188`, `:593-597`, `:708-712`) mientras el sumidero parseará con `_FM_RE`: dos gramáticas para el mismo fichero en la misma operación.

**Remedio.** (1) Escritura atómica también en la creación (cuesta una línea). (2) En el camino «existe», si `read_md` no devuelve frontmatter (`fm == {}`) tratarlo como **creación** —o abortar con error explícito—, nunca como «cuerpo tocado». (3) Un solo parser: que los registradores usen `read_md`. Mutante: fichero truncado + registrador → fichero íntegro con un solo frontmatter.

### H-04 · MEDIO · «Ningún consumidor del cuerpo» es falso dentro del repo: `registrar_outputs.py` lee y escribe `## Navegación`, y hoy los registradores también destruyen eso

**Evidencia.** `.claude/skills/_shared/registrar_outputs.py:149-174` (helper canónico, copiado a `.claude/skills/cendoj-descarga/scripts/registrar_outputs.py`) lee el texto de `00_Input/_caso.md`, comprueba `[[wikilink]] not in text` y **inserta** líneas bajo `## Navegación` con escritura atómica; su docstring (`:12,17`) lo declara. Tiene tests (`tests/test_skill_registrar_outputs.py`). **D10 (hoy)**: wikilink insertado + `register_expediente` → `wikilink sobrevive HOY: False`. Además `plugins/expedientes_xl/tiers.py:32` y su `README.md:61` declaran `_caso.md` como *carve-out* editable desde Cowork por MCP: otro escritor del cuerpo fuera del `grep`.

**Por qué importa.** El §3.3 concluye «el frontmatter sigue siendo la fuente de verdad para **todo lector del repo**» a partir de un `grep` cuyo alcance declarado es `core/`, `scripts/` y `streamlit_app.py`; la conclusión es más ancha que la medición, y la tabla del §1 («pierden tres cosas») omite una cuarta pérdida real y reproducida. La consecuencia para el diseño es H-01/D9: esos ficheros quedan congelados.

**Remedio.** Ampliar el censo a `.claude/skills/` y `plugins/`, añadir la pérdida al §1 y un mutante «wikilink de `registrar_outputs` + registrador → sigue» (M1-M5 no lo cubren porque el wikilink no está al final del cuerpo). Y decidir con H-01 si el cuerpo con wikilinks debe seguir reflejando expedientes nuevos.

### H-05 · MEDIO · La plantilla no es total: una entrada sin `input_dir` aborta el registrador, y el diseño la ejecuta en cada actualización

**Evidencia.** `core/case_manager.py:116`: `e['input_dir']` sin `.get`. `update_pull_state` crea entradas `{id, element, linked_at, doc_ids, by_carpeta, errors}` (`:1456-1468`) **sin** `input_dir`. **P5c (hoy)**: `update_pull_state("649", element=…)` + `register_expediente("650", …)` → `KeyError: 'input_dir'`. **D8 (diseño)**: idéntico, y ahora la plantilla corre dos veces por actualización (una para comparar, otra para regenerar), así que una sola entrada malformada persistida convierte en fatal cada registrador sobre ese caso.

**Remedio.** `_cuerpo_del_indice` total sobre lo persistido: `e.get("input_dir") or f"sudespacho_{e.get('id')}"`, `e.get("element", "?")`. Mutante con la entrada de P5c.

### H-06 · BAJO · «Se conserva byte a byte» promete lo que `read_md`/`write_md` no pueden dar

**Evidencia.** **P6**: `write_md` en Windows escribe **CRLF** (`Path.write_text` sin `newline`; `contiene CRLF: True`). **D5**: fichero LF-only (editado desde Cowork/Linux o por el Drive) con nota → `decision: conservado | nota sobrevive: True | cuerpo byte a byte idéntico: False | CRLF tras escribir: True`. Además `write_md` hace `body.strip()` (`core/utils.py:257`): los saltos de borde no sobreviven. La comparación con `strip()` sí es correcta frente a `\r\n` (la lectura en modo texto normaliza), y un cuerpo vacío se clasifica como «tocado» (conservar vacío: lado seguro).

**Remedio.** Redactar «conserva el texto del cuerpo (normalizado en finales de línea y espacios de borde)». Si se quiere byte a byte de verdad, leer/escribir con `newline=""` y no hacer `strip()` del cuerpo conservado.

### H-07 · BAJO · El temporal `._caso.<pid>.tmp` no está en `MERGE_EXCLUSIONS`; M10 solo cubre el camino feliz y hoy pasa en verde sin declararse positivo

**Evidencia.** **D12**: `esta_excluido("00_Input/._caso.1234.tmp") → False`, mientras `.apertura_v1.*.tmp` sí está (`core/config.py:392-400`). Un corte duro (kill, apagado) entre `write_md(tmp)` y `os.replace` deja el temporal, y el checkin lo trata como contenido del expediente. Hoy solo lo produce `_atomic_write_caso_md` (`:1343`); el diseño lo produce **en cada pull de Drive** que cambie IDs. M10 («no queda tmp residual») pasa con el código actual porque hoy no hay tmp, y el §5 no lo lista entre los positivos (dice «M6-M9»); tampoco hay mutante del camino de fallo (`write_md` lanza → tmp borrado), que `_atomic_write_caso_md:1347-1353` sí cubre.

**Remedio.** Añadir `._caso.*.tmp` a `MERGE_EXCLUSIONS`; mutante de fallo (monkeypatch de `write_md` que lanza → no queda tmp); clasificar M10 como positivo.

### H-08 · BAJO · El enunciado del §2 («toda escritura») es más ancho que la guarda (`_write_case_index`)

**Evidencia.** Censo de escritores de `_caso.md` (`grep -rn "_caso.md" core scripts streamlit_app.py` + skills/plugins), clasificado:

| Escritor | Primitiva | Cuerpo | Atómico |
|---|---|---|---|
| `_write_case_index` ← `ensure_case`(solo `is_new`, `:493`), `register_expediente` (`:215`), `register_drive_ev` (`:620`), `cache_drive_folder_info` (`:734`) | `write_md` en sitio | **reconstruye** | no |
| `_atomic_write_caso_md` (`:1300`) ← `escribir_lock`/`liberar_lock`/`cancelar_checkout`/`marcar_conflicto` (`:855-904`), `ensure_case` existente (`:530`), `update_pull_state` (`:1491`), `scripts/remove_expediente_link.py:81`, `scripts/limpieza_post_audit.py:178` | tmp + `os.replace` | conserva | sí |
| `core/casos/case_locator._update_ciudad_metadata` (`:322-341`) | `write_text` en sitio, `yaml.dump` (**`sort_keys` por defecto → reordena claves**) | conserva | **no** |
| `scripts/migrate_05crm_buckets.py:339` | `write_md` en sitio | conserva | no |
| `scripts/repository_cli._push_caso_md` (`:1165-1177`) | `write_md` a tmp + rclone (copia Drive) | conserva | n/a |
| `.claude/skills/_shared/registrar_outputs.py:149-174` (+ copia en `cendoj-descarga`) | texto + `os.replace` | **inserta** | sí |
| `.claude/skills/_shared/scaffold_caso.py:105-117` | crea si no existe | crea | — |
| `plugins/expedientes_xl` (carve-out `tiers.py:32`) | MCP desde Cowork | libre | — |

Solo la primera fila reconstruye; el diseño la cubre entera. Pero «toda escritura sobre un `_caso.md` que ya existe conserva…» no lo garantiza nada para las demás filas: hoy es verdad por conducta, no por guarda, y `_update_ciudad_metadata` sigue escribiendo en sitio y sin atomicidad, justo lo que el §3.1.5 dice arreglar «de paso». El propio repo avisa contra esto en `core/case_manager.py:371-378`.

**Remedio.** Redactar el §2 como propiedad **del sumidero** («toda escritura que pase por `_write_case_index`»), poner el censo en el §6 y, si se quiere ancho de verdad, un guard-test que falle ante un `write_md(`/`write_text(` sobre `_caso.md` fuera de las dos primitivas.

### H-09 · BAJO · Deriva de líneas en el §1 aunque el fichero no ha cambiado

**Evidencia.** `git diff --stat 556b8b2 41a3141 -- core/case_manager.py` vacío, y sin embargo: «`:203-206`» → el filtro por `fields(CaseMeta)` está en `:204-209`; «`:615-616`» → `:613-614`; «`:729-730`» → `:727-728`; «`_atomic_write_caso_md` (`:1307`)» → `def` en `:1300` (1307 es docstring). Correctas: `:109`, `:215`, `:493`, `:620`, `:734`, `:789`, `:1174`, `intake_drive.py:322`.

**Remedio.** Citar por símbolo o corregir.

### H-10 · BAJO · Mutantes que faltan para que la guarda no se endurezca ni se afloje de más

Además de los de H-01 (M2 afirmando el cuerpo), H-02 (D8 sobrevive), H-03 (truncado), H-04 (wikilink), H-05 (entrada sin `input_dir`), H-07 (fallo + tmp):

- **`proyeccion_local`** como instancia concreta de M5: es la clave ajena a `CaseMeta` con consecuencia real. **P4 (hoy)**: `antes: es_proyeccion_local = True` → tras `register_drive_ev`: `False`. Un pull de Drive sobre la copia local prestada la convierte hoy en un expediente más del catálogo (`case_locator.py:187-195, :369-374`). El diseño lo arregla sin nombrarlo; el test debería nombrarlo.
- **Idempotencia de bytes**: dos actualizaciones iguales seguidas producen el mismo fichero (protege el `mtime` de M9 y evita que el orden de claves —`{**fm, **propias}` conserva posiciones— derive).
- **Positivo de coalescencia**: `meta` persistido con clave ajena y con `None` en un campo del lock → tras actualizar, la ajena sigue y el lock queda coalescido (mi **D11**: `ajena: valor-ajeno | estado_repositorio: disponible`).

## 2. Verificado y correcto

- **§1, las tres pérdidas de hoy, reproducidas**: nota (**P1**: `nota sobrevive: False`), `bucket_override` (**P2**: `False`), clave ajena en `meta` (**P4**, `proyeccion_local`). Y **lo que sobrevive hoy**: lock `prestado` + `register_expediente` (**P3**: `estado_repositorio: prestado | nonce: abc | user: nik`), como dice el comentario `:199-203`.
- **Cuatro llamadores** de `_write_case_index` (`:215`, `:493`, `:620`, `:734`) y ninguno más en `core/`, `scripts/`, `streamlit_app.py`; **diez claves** en `fm` (`:144-155`); `ensure_case` sobre caso existente usa `_atomic_write_caso_md` (`:516-530`), luego «la primera es la creación y no destruye nada» es cierto.
- **`_atomic_write_caso_md`** hace exactamente lo que el §1 y el §3.1.5 le atribuyen (`:1331-1354`: `read_md`, mutador, tmp en el mismo directorio, `os.replace`, limpieza en excepción). **`write_md` escribe en sitio** (`core/utils.py:255-259`, `write_text` trunca antes de escribir): el «índice truncado» del §3.1.5 es real.
- **§3.1.3**: `{**persistido, **asdict(meta)}` conserva lo ajeno y coalesce lo conocido (**D11**). **§3.1.2**: `{**fm, **propias}` conserva `bucket_override` (mi simulación).
- **M7 y M8** son positivos de verdad con el diseño (**D2**: `decision: regenerado | 648 en cuerpo: True`) y pasan también hoy, como el §5 declara. **M9** existe (`tests/test_intake_drive.py:356`) y sigue válido: el diseño no toca el retorno temprano de `register_drive_ev` (`:602-606`).
- **`register_drive_ev` en cada pull**: `core/intake_drive.py:320-322`, bajo `if returncode == 0`, y por el retorno temprano solo reescribe cuando cambian los IDs.
- **§3.3, plantilla legacy acotada**: `git log -S` sobre las cadenas del cuerpo da dos commits (`5c80bf8` inicial y `2f5d05f`, **2026-04-29**); desde entonces la plantilla no ha cambiado, así que el «tocado» por versión solo afecta a casos creados antes de esa fecha.
- **Lente 4**: `_caso.md` está en `MERGE_EXCLUSIONS` (`core/config.py:392`), los mutadores del lock solo tocan `meta` (`core/repository_checkout.py:162-219`) y nada en `repository_checkout`/`repository_cli` asume forma del cuerpo (`_push_caso_md` lo conserva, `:1176`). El diseño no rompe ninguna invariante de la biblioteca y **mejora** una: la marca `proyeccion_local` de la copia prestada sobrevive.
- **Lente 5**: la escritura del §3.1.5 es equivalente a la de `_atomic_write_caso_md` en el camino «existe»; con dos registradores concurrentes pasa de «posible truncado» a «último gana con fichero íntegro»: no empeora, y el §6 lo remite a `MEJORAS #126` (existe, `MEJORAS_FUTURAS.md:5684`).
- **§4**: la pieza guarda el lock → dos rondas, coherente con `CLAUDE.md`; el revisor sustituto y la declaración de independencia más débil siguen `AGENTS.md:61-84`. **`MEJORAS #146`** (`MEJORAS_FUTURAS.md:6474`) y `[APER-54]` (`RUNBOOK…:30-36`) dicen lo que el diseño les atribuye. `case_manager.py:1173-1176` documenta `bucket_override` como campo editado a mano.

## 3. No verificado

- **`os.replace` sobre `G:` (Drive for Desktop)**: sin acceso permitido; la equivalencia con `_atomic_write_caso_md` es de código, no medida en esa unidad.
- **Cuántos `_caso.md` reales tienen cuerpo legacy, notas o wikilinks** (impacto real del §3.3 y de H-01): `data/CASOS/` fuera de alcance.
- **El informe origen** `2026-09-05-acciones-alta-expediente.md` citado en la cabecera **no existe en el commit** (`git ls-files`): no pude contrastar «acción 2».
- **El fichero untracked** `tests/test_caso_md_preservar_al_actualizar.py`: no leído por mandato.
- **D7** (cierre `---` sin salto, divergencia `split` vs `_FM_RE`): mi sonda no consiguió construir el caso, así que la divergencia de parsers de H-03 queda demostrada solo con el fichero truncado.

## 4. Veredicto

**LISTA-CON-CAMBIOS.** El mecanismo central —guarda en el sumidero, `{**fm, **propias}`, `{**meta_persistido, **asdict(meta)}`, escritura atómica— es correcto y mata el defecto medido; lo que no cierra es la **detección del cuerpo** (H-01, con dos disparadores en el repo no declarados), una de las diez claves propias (H-02), el camino de frontmatter no parseable (H-03) y varios enunciados más anchos que la función (H-04, H-06, H-08); todo es enmendable en la rev. 2 sin cambiar la arquitectura, y la ronda sobre el diff puede verificarlo.

Recuento: CRÍTICO 0 · ALTO 1 · MEDIO 4 · BAJO 5.
<!-- informe-literal:fin:kqzw -->

## 2. Evidencia verificada por mí al adjudicar

Abrí la fuente en `41a3141` para los cinco hallazgos que cambian el diseño; los otros cinco los
acepto sobre la evidencia del informe, que cita línea y sonda.

| Hallazgo | Qué comprobé | Dónde |
|---|---|---|
| H-02 | `update_pull_state` muta **solo** `fm["sudespacho_expedientes"]` (top-level) y nunca el espejo `meta`; sus entradas nuevas llevan `id, element, linked_at, doc_ids, by_carpeta, errors` y **no** `input_dir` (esto último es también la base de H-05) | `core/case_manager.py`, cuerpo de `_mutate` dentro de `update_pull_state` |
| H-03 | `_FM_RE = ^---\s*\n(.*?)\n---\s*\n` con `DOTALL`: sin el cierre `---\n` devuelve `({}, texto)`, así que un fichero truncado no tiene frontmatter para `read_md` | `core/utils.py`, `_FM_RE` y `read_md` |
| H-04 | `_insertar_wikilinks` inserta bajo `## Navegación`/`## Navegacion` y, si no existe la sección, la crea al final; `update_caso_md` escribe con `_atomic_write` (tmp + `os.replace`) | `.claude/skills/_shared/registrar_outputs.py` |
| H-07 | `MERGE_EXCLUSIONS` excluye `.apertura_v1.*.tmp` y **no** `._caso.*.tmp`; el guard `test_carveout_espeja_merge_exclusions` exige que `PROTOCOL_EDIT ∪ PROTOCOL_APPEND` sea igual al conjunto de exclusiones sin `/`, así que añadir el temporal obliga a tocar los dos registros | `core/config.py`, `plugins/expedientes_xl/tiers.py`, `tests/test_expedientes_xl_tiers.py` |
| H-08 | `_update_ciudad_metadata` parte con `text.split("---", 2)`, hace `yaml.dump(fm, …)` **sin `sort_keys=False`** y escribe con `write_text` en sitio | `core/casos/case_locator.py` |

Y el hecho que sostiene la adjudicación del ALTO: la plantilla de `_write_case_index` deriva de
los campos de `CaseMeta` exactamente **tres** fragmentos que los registradores cambian —la línea
`Caso … — estado …`, la línea `- Drive E&V team: … / folder: …` y la sección
`## Expedientes sudespacho`—; todo lo demás del cuerpo (título, partes, sede, `Drive:`, `Remoto
rclone:`, `## Navegación`) se fija en la creación y ningún registrador lo cambia. Eso es lo que
hace posible el remedio por fragmentos en vez de la detección de la rev. 1.

Digest del informe recalculado al recibirlo: `95a18400d1f1c292c1a90d61dda92e6d57246f52bc95cfbd2502cf33d482fe1b`
(UTF-8, `LF`, un único salto final), igual al declarado por el revisor.

## 3. Mapa hallazgo → remedio (la adjudicación completa está en el §8 del diseño)

| # | Sev. | Veredicto | Dónde se remedia en la rev. 2 |
|---|---|---|---|
| H-01 | ALTO | confirmado, **remedio distinto** | §3.3 reescritura por fragmentos (sin detección «nadie lo tocó»); alternativas del revisor razonadas en §3.5; mutantes M2, M3, M14 |
| H-02 | MEDIO | confirmado | §3.2 fusión de `sudespacho_expedientes` por entrada; M11 |
| H-03 | MEDIO | confirmado | §3.1 `fm == {}` → creación; escritura atómica en las dos ramas; M13 |
| H-04 | MEDIO | confirmado | §1 punto 4; §3.3 conserva `## Navegación`; M3 |
| H-05 | MEDIO | confirmado | §3.1 plantilla total (`.get`); M12 |
| H-06 | BAJO | confirmado | §3.3 último párrafo («el texto», no los bytes) |
| H-07 | BAJO | confirmado | §6 `MERGE_EXCLUSIONS` + `PROTOCOL_EDIT`; M10 con camino de fallo |
| H-08 | BAJO | confirmado | §2 acotado al sumidero; censo en §6; `MEJORAS #162` |
| H-09 | BAJO | confirmado | §1 cita por símbolo |
| H-10 | BAJO | confirmado | M5 (`proyeccion_local`), M15, M16 |

Recuento: 10 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar. Lo que el
revisor declaró **no verificado** (§3 de su informe) sigue sin verificar y está recogido en el §7
del diseño.
