---
tipo: spec
estado: en-revision
creado: 2026-09-05
objeto: "MEJORAS #146 — los registradores de `_caso.md` reconstruyen el fichero y destruyen lo que no es suyo"
rev: "3"
---

# `_caso.md`: actualizar conserva lo que no es del registrador

> **Rev. 3 (2026-09-05), tras la R2 adversarial sobre el diff: `LISTA-CON-CAMBIOS`, ocho
> hallazgos, los ocho confirmados.** Tres tocan el código y los tres eran defectos que el propio
> diff introducía: la fusión por entrada reañadía en cada pasada las entradas sin `id` (la lista
> doblaba con cada pull), la sección (c) se extendía hasta el siguiente `## ` y destruía un `#` o un
> `###` escrito a mano, y el mismo objeto lista en dos claves salía como ancla YAML. Los cinco
> restantes son rotulado del §5 y referencias. Adjudicación en el **§9**; voz del revisor en el
> acta `…-r2-adversarial-review.md`.
>
> **Rev. 2 (2026-09-05), tras la R1 adversarial sobre la rev. 1: `LISTA-CON-CAMBIOS`, diez
> hallazgos, los diez confirmados.** Lo que cambia es el **§3.3**: la rev. 1 decidía si
> regenerar el cuerpo entero comparándolo con la plantilla («nadie lo tocó»), y el revisor
> demostró con sondas que esa regla **congela** el cuerpo en cuanto pasa por él cualquier
> escritor que no sea un registrador —y en el repo ya hay dos— dejando un índice que lista lo
> desvinculado y omite lo vinculado. La rev. 2 no detecta nada: el registrador reescribe **solo
> los tres fragmentos que derivan de lo que él escribe** y conserva todo lo demás línea a línea.
> Adjudicación completa en el **§8**; la voz del revisor, literal, en el acta hermana
> `…-r1-adversarial-review.md`.
>
> **Rev. 1 (2026-09-05).** Diseño para cerrar `MEJORAS #146`. Origen: acción 2 del informe de
> Codex «Acciones para mejorar el alta de expedientes» (2026-09-05, lectura estática sobre
> `9ec96f7`; vive fuera del repo, en el directorio de visualizaciones de Codex), contrastada
> contra `main` en `556b8b2`: el defecto seguía vivo.

## 1. El problema, medido

`_write_case_index(case_dir, meta)` (`core/case_manager.py`) **construye** el `_caso.md` entero
a partir de un `CaseMeta`: el cuerpo, desde una plantilla; el frontmatter, con diez claves fijas
(`case_id`, `tipo`, `fase`, `fecha`, `estado`, `ciudad`, `referencia_crm`,
`sudespacho_expedientes`, `drive`, `meta`). Nunca lee lo que había, y escribe **en sitio** con
`write_md` (`write_text` trunca antes de escribir).

Lo llaman cuatro funciones, contadas por `grep` el 2026-09-05 sobre `556b8b2` y confirmadas
por la R1:

| Llamador | Cuándo corre |
|---|---|
| `ensure_case` | solo si `_caso.md` **no existe** (`is_new`) |
| `register_expediente` | tras cada alta CRM, y en `sync_sudespacho` |
| `register_drive_ev` | en **cada pull de Drive** cuyos IDs cambien (`intake_drive.pull_drive_ev`) |
| `cache_drive_folder_info` | tras resolver la carpeta E&V por API |

La primera es la creación y no destruye nada. Las otras tres actualizan un fichero que ya existe
y al reconstruirlo pierden **cuatro cosas**, las cuatro reproducidas por sonda en la R1:

1. **El cuerpo escrito a mano** (`MEJORAS #146`): una nota del abogado, una llamada a
   `register_drive_ev`, la nota ya no está.
2. **Las claves del frontmatter que no están entre las diez.** `bucket_override`, que el propio
   `read_bucket_overrides` documenta como campo que el abogado edita a mano, no sobrevive a un
   pull.
3. **Las claves de `meta` ajenas a `CaseMeta`.** Los tres registradores filtran `meta` por
   `dataclasses.fields(CaseMeta)` antes de reconstruir. La instancia con consecuencia real es
   **`proyeccion_local`**: la marca que distingue una copia prestada de un expediente del
   catálogo (`case_locator`). Un pull sobre la copia local la borra y la copia pasa a ser «un
   caso más».
4. **Lo que otros módulos escriben en el cuerpo.** `.claude/skills/_shared/registrar_outputs.py`
   inserta wikilinks bajo `## Navegación` (con tests propios); un `register_expediente`
   posterior los destruye. Y el plugin `expedientes-xl` declara `_caso.md` como carve-out
   editable desde Cowork (`tiers.PROTOCOL_EDIT`): otro escritor del cuerpo.

Y una quinta, dentro del propio frontmatter: **`update_pull_state`** guarda el estado D8 del pull
(`last_sync`, `doc_ids`, `by_carpeta`, `errors`) **solo** en la lista top-level
`sudespacho_expedientes`; `register_drive_ev` y `cache_drive_folder_info` reconstruyen esa lista
desde el espejo `meta.sudespacho_expedientes`, que no lo tiene, y el estado desaparece (R1/H-02,
sonda P5). Hoy no ocurre en producción porque los flujos reales llaman a `register_expediente`
antes del pull, pero la propiedad es falsa para una de las diez claves.

Lo que **sí** sobrevive hoy, y hay que no romper: los campos del lock de checkout
(`estado_repositorio`, `checkout_*`), porque están en `CaseMeta` y los registradores los
coalescen desde el `meta` persistido (R1, sonda P3).

El repo ya tiene la primitiva correcta: `_atomic_write_caso_md` lee `fm + body`, aplica un
mutador al frontmatter y escribe atómicamente **conservando el cuerpo**. El comentario que la
precede avisa de que se use esa y «nunca `_write_case_index`». El aviso está escrito para el lock
y no llegó a los registradores.

## 2. La frontera

**Toda escritura que pase por `_write_case_index` sobre un `_caso.md` que ya existe conserva lo
que no es del registrador:** las líneas del cuerpo que él no genera, las claves de frontmatter
que otro módulo o el abogado añadieron, las claves de `meta` que el modelo no conoce y el estado
que otros escritores guardan dentro de `sudespacho_expedientes`. La propiedad, no el ejemplo: el
ejemplo es la nota perdida; la propiedad es que **reconstruir no es actualizar**.

La guarda va **en el sumidero** —`_write_case_index`—, no en cada registrador. Es la misma
lección que `MEJORAS #153`: una guarda en el envoltorio la rodea el siguiente llamador. Con la
guarda en la función que escribe, el cuarto registrador que alguien añada hereda la propiedad
sin saberlo.

**Y es una propiedad del sumidero, no del fichero** (R1/H-08). Hay otros escritores de
`_caso.md` que no reconstruyen (censo en el §6); a ellos este diseño no les añade ni les quita
nada.

## 3. Diseño

### 3.1. `_write_case_index` distingue crear de actualizar

- **No existe**, o existe pero `read_md` no le encuentra frontmatter **y el texto empieza por
  `---`** (un fichero truncado a mitad de escritura, R1/H-03) → **creación**: frontmatter de diez
  claves y cuerpo de plantilla, como hoy. Un truncado no tiene nada que conservar y hoy ya se
  reconstruye limpio. **Si el texto no empieza por `---`** es un cuerpo escrito sin frontmatter
  (R2/H-07), y se actualiza como cuerpo con frontmatter vacío: gana el frontmatter y conserva el
  texto.
- **Existe con frontmatter** → **actualización preservadora**:
  1. `fm, body = read_md(index)`.
  2. **Frontmatter:** `fm_nuevo = {**fm, **propias}`, donde `propias` son las diez claves de
     siempre **menos `sudespacho_expedientes`**, que se fusiona por entrada (§3.2). Lo ajeno
     (p. ej. `bucket_override`) queda donde estaba, en su posición.
  3. **`meta`:** `{**(fm.get("meta") or {}), **asdict(meta)}`, con `sudespacho_expedientes` =
     la lista fusionada. Las claves de `CaseMeta` las manda el dataclass —que los registradores
     ya han coalescido desde lo persistido—; las que `CaseMeta` no conoce (`proyeccion_local`)
     se conservan.
  4. **Cuerpo:** actualización **quirúrgica** (§3.3).
- **Las dos ramas escriben atómicamente**: temporal `._caso.<pid>.tmp` en el mismo directorio y
  `os.replace`, como `_atomic_write_caso_md`; si la escritura del temporal falla, se borra y se
  propaga la excepción. Hoy `write_md` escribe en sitio y un corte deja el índice truncado; la
  R1 señaló (H-03) que dejar la creación «como hoy» dejaba ese agujero abierto justo en el
  escenario que motiva la atomicidad.

La plantilla del cuerpo se extrae a una función pura `_cuerpo_del_indice(meta) -> str`, que es
la misma que usa la creación, y es **total** sobre lo persistido (R1/H-05): una entrada de
`sudespacho_expedientes` sin `input_dir` —las crea `update_pull_state`— se pinta con
`sudespacho_<id>`, y sin `element`, con `?`. Hoy `e['input_dir']` aborta el registrador con
`KeyError` en cuanto una entrada así exista.

### 3.2. `sudespacho_expedientes` se fusiona por entrada

La lista top-level es el hogar del estado D8 de `update_pull_state`; el espejo `meta.…` no lo
tiene. Al actualizar: se parte de las entradas **persistidas** en top-level, en su orden; cada
entrada nueva con el mismo `id` se aplica encima (`{**persistida, **nueva}`); las nuevas sin
`id` persistido se añaden al final; las persistidas que la lista nueva no trae **se conservan**
(ningún registrador borra por esta vía: `remove_expediente_link` va por `_atomic_write_caso_md`).
El espejo `meta.sudespacho_expedientes` pasa a ser **una copia** del resultado (R2/H-03: el mismo
objeto en las dos claves salía como ancla YAML), así que después de la primera actualización
los dos niveles coinciden. **Y la fusión es idempotente sobre su propia salida** (R2/H-01): como
los registradores construyen `CaseMeta` desde el espejo, una entrada sin `id` volvía como «nueva»
en cada pasada y la lista doblaba con cada pull; ahora lo que ya está en la salida no se repite.
Consecuencia declarada: cualquier escritor que retire una entrada debe retirarla de los dos
niveles (los dos que existen, `remove_expediente_link` y `limpieza_post_audit`, ya lo hacen).

### 3.3. Cuerpo: el registrador reescribe solo lo que deriva de lo que escribe

La rev. 1 regeneraba el cuerpo entero si «nadie lo había tocado», comparándolo con la plantilla.
La R1 (H-01) reprodujo dos formas de que esa regla **congele** el cuerpo sin que nadie haya
escrito una nota: un mutador del frontmatter que quita un expediente (`remove_expediente_link`,
`limpieza_post_audit`) deja el cuerpo listando lo desvinculado, y desde ahí ya no coincide con
ninguna plantilla; y un wikilink de `registrar_outputs` lo marca como «tocado» para siempre. En
los dos casos el índice acaba **mintiendo en la dirección peligrosa**.

La rev. 2 no clasifica el cuerpo. El registrador es dueño de **exactamente tres fragmentos**, los
que la plantilla deriva de los campos que los registradores escriben, y no toca nada más:

| Fragmento | Forma por la que se localiza | Si no está y hay dato | Si está y ya no hay dato |
|---|---|---|---|
| (a) la línea de estado | `Caso \`<case_id>\` — estado **…**.` | no se inserta | — |
| (b) los IDs de Drive E&V | línea que empieza por `- Drive E&V team:` | se inserta tras la línea `- Remoto rclone:` si existe; si no, no se inserta | se retira |
| (c) la sección de expedientes | desde `## Expedientes sudespacho` hasta el siguiente **encabezado de cualquier nivel** (`#`…`######`) o el final (R2/H-02: cortar solo en `## ` destruía un `# Notas` o un `### Detalle` escrito a mano) | se inserta antes de `## Navegación` (o `## Navegacion`); si no hay, al final | se retira |

Todo lo demás —título, partes, sede, `## Navegación` con sus wikilinks, notas al final,
placeholders rellenados a mano— se conserva **línea a línea**. La sección (c) lleva, al
generarse, una línea `<!-- sección generada por el registrador: no editar a mano -->`, porque su
contrato es el contrario al del resto del cuerpo y hay que decirlo donde se lee.

Consecuencias, declaradas: (1) el dato está siempre en el frontmatter; el cuerpo lo **refleja**
en esos tres sitios y ya no puede quedar rancio por una actualización; (2) una edición manual
**dentro** de uno de los tres fragmentos se pierde en la siguiente actualización, y el comentario
de (c) lo avisa; (3) un cuerpo legacy sin ninguno de los anclajes queda como está, y el
frontmatter sigue siendo la verdad para todo lector que no sea humano.

Los finales de línea y los espacios de borde no se prometen byte a byte (R1/H-06): `read_md`
normaliza `\r\n` al leer y `write_md` recorta el cuerpo y escribe con el final de línea de la
plataforma. Lo que se conserva es **el texto**.

### 3.4. Los registradores no cambian de forma

`register_expediente`, `register_drive_ev` y `cache_drive_folder_info` siguen coalesciendo los
campos conocidos y llamando a `_write_case_index`. No se reescriben para usar
`_atomic_write_caso_md`: la propiedad tiene que vivir en el sumidero, y reescribir tres
llamadores para dejar el sumidero destructivo sería remediar el ejemplo. **Lo único que cambia
en ellos es el parser**: leían el frontmatter con `text.split("---", 2)` y el sumidero usa
`read_md` (R1/H-03). Al implementar M13 la divergencia mordió: un `_caso.md` truncado reventaba
en el registrador con `ValueError` antes de llegar al sumidero que sabe reconstruirlo. Los tres
pasan a `read_md`, que en un fichero bien formado devuelve lo mismo.

### 3.5. Alternativas descartadas

- **Regenerar el cuerpo entero si «nadie lo tocó»** (rev. 1). Congela ante escritores legítimos
  del frontmatter y del cuerpo (H-01). Descartada por medición.
- **Huella `sha256` del cuerpo generado guardada en `meta`** (remedio (a) de la R1). Arregla el
  falso «tocado» del mutador de frontmatter pero sigue congelando tras un wikilink, y necesita un
  fallback para lo legacy. La reescritura por fragmentos no necesita ni huella ni fallback.
- **Marcadores alrededor de las secciones generadas, introducidos perezosamente** (remedio (b)).
  Equivalente en efecto a la rev. 2, pero exige que la primera pasada acierte en clasificar el
  cuerpo legacy (el mismo problema de la rev. 1) para poner los marcadores. Localizar los
  fragmentos por su forma no lo exige.
- **Conservar siempre el cuerpo al actualizar.** Deja el cuerpo rancio en el caso normal.
- **Reescribir los tres registradores sobre `_atomic_write_caso_md`.** Remedia los tres ejemplos
  y deja el sumidero destructivo para el cuarto; ver §2.

## 4. Radio de daño y rondas

La pieza escribe el fichero que guarda el lock de checkout y los vínculos CRM de un expediente, y
el defecto que cierra **destruye una nota del abogado**. Por la regla del 2026-08-26 le tocan
**dos rondas**: una sobre el diseño (hecha: §8) y otra sobre el diff. Codex no tiene cupo, así
que ambas las ejecuta el **revisor sustituto** de `AGENTS.md`: una sesión de Claude Code sin el
contexto de autoría, y la adjudicación declara que la independencia es **más débil** porque autor
y revisor son el mismo modelo.

## 5. Mutantes

Cada uno es un test en `tests/test_caso_md_preservar_al_actualizar.py`. Los marcados **(+)** son
positivos: pasan también con `556b8b2` y existen para que la guarda no se endurezca de más.

| # | Mutante | Qué debe pasar |
|---|---|---|
| M1 | nota a mano al final + cada uno de los tres registradores | la nota sigue, y el cuerpo fuera de los tres fragmentos es idéntico |
| M2 | nota a mano + `register_expediente` | la nota sigue **y** el expediente está en el frontmatter **y** en el cuerpo |
| M3 | wikilink insertado bajo `## Navegación` (como `registrar_outputs`) + `register_expediente` | el wikilink sigue y el expediente aparece en la sección (c) |
| M4 | clave top-level ajena (`bucket_override`) + cada registrador | la clave sigue con su valor |
| M5 | clave ajena en `meta`, incluida `proyeccion_local` + cada registrador | la clave sigue; `case_locator` sigue viendo la copia como proyección |
| M6 (+) | lock `prestado` con `checkout_*` + `register_expediente` | el lock sigue |
| M7 (+) | cuerpo intacto + `register_expediente` / `register_drive_ev` | el cuerpo lista el expediente / los IDs |
| M8 (+) | `_caso.md` inexistente | idéntico a hoy: diez claves y cuerpo de plantilla |
| M9 (+) | `register_drive_ev` dos veces con los mismos IDs | no reescribe (`test_register_drive_ev_idempotente`) |
| M10 (+) | actualización con éxito | no queda `._caso.*.tmp`; **y** si `write_md` lanza, tampoco queda y el fichero original está íntegro |
| M11 | `register_expediente` → `update_pull_state(doc_ids…)` → `register_drive_ev` | `read_pull_state` sigue viendo `doc_ids` y `last_sync` |
| M12 | entrada de `sudespacho_expedientes` sin `input_dir` (la crea `update_pull_state`) + `register_expediente` | no aborta; la sección (c) la pinta con `sudespacho_<id>` |
| M13 | `_caso.md` truncado a mitad (sin cierre de frontmatter) + registrador | fichero íntegro con un solo frontmatter |
| M14 (+ frente a `main`) | quitar un expediente por mutador de frontmatter (como `remove_expediente_link`) + `register_drive_ev` | la sección (c) **ya no** lista el expediente retirado. Pasa también en `main` (allí se reconstruía todo): mata la **rev. 1**, no `main` (R2/H-04) |
| M15 (+ frente a `main`) | dos actualizaciones iguales seguidas | el fichero es idéntico byte a byte tras la segunda. Mata la rev. 1, no `main` |
| M16 | `meta` con clave ajena **y** `None` en un campo del lock + registrador | la ajena sigue (esta mitad mata a `main`: es M5) y el campo del lock conserva lo persistido (esta mitad es positiva) |
| M17 | entrada sin `id` en top-level y en `meta` + tres pares de registradores | la lista sigue teniendo **una** entrada (R2/H-01) |
| M18 | `### Detalle` y `# Notas` con párrafo entre la sección (c) y `## Navegación` + `register_drive_ev` | los cuatro textos siguen y la sección (c) sigue siendo una (R2/H-02) |
| M19 | `register_expediente` + `register_drive_ev` | el fichero no contiene `&id` ni `*id` (R2/H-03) |
| M20 | cuerpo sin frontmatter (no empieza por `---`) + `register_drive_ev` | el texto sigue y el fichero gana frontmatter (R2/H-07) |
| M21 | entrada persistida con `id: 648` numérico + `register_expediente("648")` | una sola entrada, con su estado D8 |
| M22 | truncado + `register_expediente` / `cache_drive_folder_info` | íntegro (M13 solo probaba `register_drive_ev`) |

## 6. Alcance explícito

- **Toca:** `_write_case_index` y la extracción de la plantilla del cuerpo, en
  `core/case_manager.py`; `core/config.MERGE_EXCLUSIONS` y `plugins/expedientes_xl/tiers.PROTOCOL_EDIT`,
  que ganan `._caso.*.tmp` (R1/H-07: hoy el temporal de `_atomic_write_caso_md` tampoco estaba
  excluido, y el diseño lo produce en cada pull); tests nuevos. Cierre de `MEJORAS #146`. La
  regla de `CLAUDE.md` («NO se escriben notas en `_caso.md`… vigente hasta que cierre
  `MEJORAS #146`») y `[APER-54]` del runbook pasan a decir que la nota ya no se pierde,
  manteniendo `90_Notas personales` como sitio preferente porque ningún módulo del core lo lee.
- **No toca:** la lógica de `_atomic_write_caso_md` (pasa a delegar la escritura en el escritor
  atómico compartido, para que el censo de `test_escritura_censo.py` no suba), el camino de
  `ensure_case` sobre caso existente, la **forma** de los tres registradores (solo su parser,
  §3.4), el formato del frontmatter, ni ningún `_caso.md` existente. **Sí toca**, fuera del
  alcance de la rev. 1 y declarado por la R2 (H-08): el `split("---", 2)` sin guarda de
  `scripts/sync_sudespacho.py::sync_all`, que reventaba el bucle entero ante un `_caso.md`
  truncado una línea antes de llamar al sumidero que lo repararía.
- **No cubre:** la concurrencia entre dos escritores del mismo `_caso.md` (`MEJORAS #126` y el
  mutex); el `_caso.md` de la copia del Drive durante un checkout (`repository_checkout`); y los
  escritores del censo de abajo que no pasan por el sumidero.

**Censo de escritores de `_caso.md`** (R1/H-08, sobre `core/`, `scripts/`, `streamlit_app.py`,
`.claude/skills/` y `plugins/`):

| Escritor | Primitiva | Cuerpo | Atómico |
|---|---|---|---|
| `_write_case_index` ← los cuatro llamadores del §1 | `write_md` en sitio → **este diseño** | reconstruye → **conserva** | no → **sí** |
| `_atomic_write_caso_md` ← lock, `ensure_case` existente, `update_pull_state`, `remove_expediente_link`, `limpieza_post_audit` | tmp + `os.replace` | conserva | sí |
| `case_locator._update_ciudad_metadata` | `write_text` en sitio, `yaml.dump` con `sort_keys` por defecto (**reordena claves**) | conserva | **no** → `MEJORAS #167` |
| `scripts/migrate_05crm_buckets.py` | `write_md` en sitio | conserva | no |
| `scripts/repository_cli._push_caso_md` | `write_md` a temporal + rclone | conserva | n/a |
| `.claude/skills/_shared/registrar_outputs.py` (+ copia en `cendoj-descarga`) | texto + `os.replace` | inserta wikilinks | sí |
| `.claude/skills/_shared/scaffold_caso.py` | crea si no existe | crea | — |
| `plugins/expedientes_xl` (carve-out) | MCP desde Cowork | libre | — |

## 7. Lo que la R1 no pudo verificar, y sigue sin verificar

`os.replace` sobre `G:` (Drive for Desktop) —equivalencia de código con `_atomic_write_caso_md`,
no medida en esa unidad—; cuántos `_caso.md` reales tienen notas, wikilinks o cuerpo legacy
(`data/CASOS/` fuera del alcance del revisor); y el informe origen de Codex, que vive fuera del
repo.

## 8. Adjudicación de la revisión adversarial (Claude Code sesión independiente, 2026-09-05) — LISTA-CON-CAMBIOS, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-09-05-caso-md-preservar-al-actualizar-design.md` rev. 1, commit `41a3141`
- **Ronda:** 1
- **Revisor:** Claude Code (sesión independiente), solo lectura, con sondas ejecutadas contra un `CASOS_ROOT` temporal
- **Informe recibido:** `2026-09-05-caso-md-preservar-al-actualizar-r1-adversarial-review.md`
- **Hallazgos:** 10 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento

**Independencia, declarada más débil.** Codex no tiene cupo; el revisor fue una sesión de Claude
Code sin el contexto de autoría (`AGENTS.md` §«Revisor sustituto»). Autor y revisor son el mismo
modelo, con los mismos puntos ciegos. Lo que compensa aquí es que **nueve de los diez hallazgos
vienen con sonda ejecutada**, y yo he verificado los cinco que cambian el diseño abriendo la
fuente antes de adjudicar. El digest del informe se recalculó al recibirlo y coincide.

| # | Sev. | Hallazgo | Veredicto | Dónde se remedia |
|---|---|---|---|---|
| H-01 | ALTO | «nadie lo tocó» congela el cuerpo tras un mutador de frontmatter o un wikilink, y el índice miente | **confirmado** (sondas D1/D3/D9) | §3.3: reescritura por fragmentos; sin detección. **Remedio distinto del propuesto**, razonado en §3.5 |
| H-02 | MEDIO | el estado D8 de `update_pull_state` en top-level se pierde con dos de los tres registradores | **confirmado** (`update_pull_state` muta solo `fm["sudespacho_expedientes"]`; sonda P5) | §3.2: fusión por entrada; M11 |
| H-03 | MEDIO | un `_caso.md` sin frontmatter parseable se congelaría corrupto; la creación seguía en sitio | **confirmado** (`_FM_RE` exige el cierre `---\n`) | §3.1: `fm == {}` → creación; atómica en las dos ramas; M13 |
| H-04 | MEDIO | «ningún consumidor del cuerpo» era falso: `registrar_outputs` inserta wikilinks y el plugin lo declara editable | **confirmado** (`_insertar_wikilinks`, `tiers.PROTOCOL_EDIT`) | §1 punto 4; §3.3 los conserva; M3 |
| H-05 | MEDIO | la plantilla no es total: `e['input_dir']` aborta con las entradas de `update_pull_state` | **confirmado** (`e['input_dir']` sin `.get`; entradas D8 sin `input_dir`) | §3.1: plantilla total; M12 |
| H-06 | BAJO | «byte a byte» promete lo que `read_md`/`write_md` no dan | **confirmado** | §3.3 último párrafo; M1 compara texto |
| H-07 | BAJO | `._caso.*.tmp` no está en `MERGE_EXCLUSIONS`; M10 pasaba hoy sin declararse positivo; sin mutante del fallo | **confirmado** (`MERGE_EXCLUSIONS` solo excluye `.apertura_v1.*.tmp`) | §6; M10 positivo con camino de fallo |
| H-08 | BAJO | el §2 prometía «toda escritura» y la guarda cubre un sumidero | **confirmado** (censo: `_update_ciudad_metadata` escribe en sitio y reordena) | §2 y §6 (censo); `MEJORAS #167` para el escritor no atómico |
| H-09 | BAJO | deriva de líneas en el §1 | **confirmado** | el §1 cita por símbolo |
| H-10 | BAJO | faltan mutantes (`proyeccion_local`, idempotencia de bytes, coalescencia positiva) | **confirmado** | M5, M15, M16 |

**La divergencia que hay que razonar es la de H-01.** El revisor propuso una huella `sha256` del
cuerpo generado más marcadores introducidos perezosamente. Las dos siguen necesitando decidir si
un cuerpo legacy fue tocado, que es la pregunta que la rev. 1 respondía mal. Reescribir solo los
tres fragmentos que el registrador deriva de sus propios campos elimina la pregunta: no hay nada
que clasificar y nada que congelar. El precio, declarado en el §3.3, es que una edición manual
**dentro** de uno de esos tres fragmentos se pierde, y por eso la sección (c) lo avisa en su
propio texto. Cuenta como confirmado con remedio distinto, que el contrato de gobernanza admite.

**Lo que el revisor verificó y resultó correcto** —las tres pérdidas de hoy, la supervivencia del
lock, los cuatro llamadores, las diez claves, `_atomic_write_caso_md`, la equivalencia de la
escritura atómica, las lentes 4 y 5 y el §4— está en el §2 del acta. **Lo que no pudo verificar**
está en el §7 de este documento.

## 9. Adjudicación de la revisión adversarial del diff (Claude Code sesión independiente, 2026-09-05) — LISTA-CON-CAMBIOS, remediado

- **Objeto revisado:** diff `origin/main...81082a6` (nueve ficheros; base `2b32c32`), commit `81082a6`
- **Ronda:** 2
- **Revisor:** Claude Code (sesión independiente), solo lectura, con sondas ejecutadas (once `_caso.md` adversos por los tres registradores; el fichero de tests de HEAD corrido contra una copia de `origin/main`)
- **Informe recibido:** `2026-09-05-caso-md-preservar-al-actualizar-r2-adversarial-review.md`
- **Hallazgos:** 8 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 3 de este documento y el commit que la acompaña (código, tests, runbook)

**Independencia, declarada más débil**, como en la R1 (mismo modelo, sin contexto de autoría). Lo
que compensa: el revisor ejecutó los mutantes contra `origin/main` y midió cuál mataba qué, y las
tres sondas de los hallazgos de código reproducen el defecto con salida literal. Yo he comprobado
los tres contra mi propio código antes de remediar: la rama `salida.append(n)`, el
`startswith("## ")` y la lista compartida entre `propias` y `meta_dict`. El digest se recalculó al
recibirlo y coincide.

| # | Sev. | Hallazgo | Veredicto | Dónde se remedia |
|---|---|---|---|---|
| H-01 | MEDIO | la fusión reañadía en cada pasada las entradas sin `id` (2 → 4 → 8 → 16), un defecto **introducido por el diff** | **confirmado** | `_fusionar_expedientes`: lo que ya está en la salida no se repite; §3.2; M17 |
| H-02 | MEDIO | la sección (c) acababa en el siguiente `## ` y destruía un `#`/`###` a mano que `CLAUDE.md` prometía conservar | **confirmado** | `_RE_ENCABEZADO_MD`: cualquier encabezado cierra la sección; §3.3; M18; `[APER-54]` |
| H-03 | BAJO | anclas YAML por compartir la lista entre dos claves; el §6 decía no tocar el formato | **confirmado** | `copy.deepcopy`; §3.2; M19 |
| H-04 | BAJO | M14 y M15 pasan en `main` (matan la rev. 1); M16 no era positivo; el docstring del test mentía | **confirmado** | §5 rotulado; docstring del test |
| H-05 | BAJO | `MEJORAS #162` donde debía decir `#167` (diseño §6 y §8, acta §3) | **confirmado** | corregido en los tres sitios |
| H-06 | BAJO | el §6 decía «no toca los tres registradores» y el §3.4 declaraba el cambio de parser | **confirmado** | §6 |
| H-07 | BAJO | un cuerpo sin frontmatter (que no empieza por `---`) iba a creación y perdía el texto | **confirmado** (heredado, pero el §3.1 lo justificaba con una frase falsa) | §3.1: se conserva el cuerpo; M20 |
| H-08 | BAJO | `sync_all` parsea `_caso.md` con `split` sin guarda y muere antes del sumidero | **confirmado** (fuera del alcance de la rev. 1) | `scripts/sync_sudespacho.py` pasa a `read_md`; §6 |

**Sin verificar por el revisor, y sigue así:** `os.replace` sobre `G:`; cuántos `_caso.md` reales
tienen entradas sin `id`, encabezados tras la sección o alias YAML; cómo renderiza Cowork un alias
YAML (ya no se produce); dos hilos en un proceso compartirían el nombre del temporal (heredado del
patrón original). La suite completa corrió aparte, con dos semillas, antes del merge.
