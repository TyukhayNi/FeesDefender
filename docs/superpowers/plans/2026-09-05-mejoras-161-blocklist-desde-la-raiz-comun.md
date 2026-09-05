---
tipo: plan
objeto: "MEJORAS #161 — el leak-guard resuelve la blocklist desde la raíz común y declara su ausencia"
estado_remediacion: remediado
creado: 2026-09-05
---

# `MEJORAS #161` — un guard que no puede mirar tiene que decirlo, y ahora además puede mirar

> **Qué es esto.** El defecto no tenía plan propio: es la fila #20 de `PLAN.md`, promovida el
> 2026-09-05 con el disparador ya **consumado** (una dirección de inmueble de la blocklist llegó a
> GitHub con el hook en verde; la paró `leak-scan` en CI). Este documento existe porque la
> adjudicación de la revisión adversarial tiene que vivir en el documento que la decisión modificó,
> y el corpus de los guards **G7/G8** es `docs/superpowers/` — una adjudicación en
> `MEJORAS_FUTURAS.md` o en `PLAN.md` quedaría sin comprobar.
>
> **Una ronda, por radio de daño** (`CLAUDE.md` §«Cuántas rondas»). La pieza es una guarda de
> lectura: no decide quién escribe sobre qué copia ni puede destruir datos de cliente. Lo que
> protege es el dato del cliente, y por eso está en la cola; pero el criterio de rondas mira el
> daño que la pieza **puede causar**, no el que evita.

---

## 1. El defecto, medido

`scripts/precommit_leak_guard.py::cargar_blocklist` leía los términos de dos artefactos
**gitignored**: `data/_saneado/replacements.txt` y `data/_config/pii_blocklist.txt`. Un worktree
recién creado no tiene ninguno; el flujo estándar del repo es el worktree (`docs/FLUJO_GIT.md`).
Con la lista vacía el bucle no itera y el hook devuelve 0 **sin haber comprobado nada**:

```
<raíz del repo>   data/_config/pii_blocklist.txt -> existe, 12 líneas (70 términos)
<worktree>        data/_config/pii_blocklist.txt -> NO existe          (0 términos)
```

Medido de nuevo hoy, desde este worktree y ANTES del cambio: `cargar_blocklist(worktree)` → `[]`.
Y el hook no lo decía. Es la familia del **instrumento que no puede dar el otro valor**
(`docs/DEAD_ENDS.md`, `MEJORAS #161`), en la guarda que protege el dato del cliente.

## 2. La decisión y el diseño

Nikolai eligió el 2026-09-05 las vías **(1)+(2)** de las tres que la fila #20 planteaba, y
**difirió la (3)**:

| Vía | Qué hace | Estado |
|---|---|---|
| (1) Avisar | si la lista sale vacía en todas las raíces, `main` imprime en STDERR que la comprobación **NO se ha ejecutado** y las rutas donde buscó | ✅ hecha |
| (2) Checkout principal | `cargar_blocklist` lee la **unión** del árbol dado y del checkout principal del mismo repo — el primero de `git worktree list`, aceptado solo **verificado por resultado** (la primera versión tomaba el padre de `--git-common-dir`; la R1 demostró que eso no es un checkout en `--separate-git-dir`, bare ni submódulo) | ✅ hecha |
| (3) Fallar cerrado | devolver 1 cuando no hay lista | ⏸ diferida: hoy dejaría sin commitear a toda sesión con worktree cuya raíz tampoco tenga la lista. Disparador para retomarla: que el aviso aparezca en una máquina que **sí** debería tener la lista |

**Piezas** (`scripts/precommit_leak_guard.py`, estado tras la remediación del §4):

- `_git(repo, *args)`: consulta a git con `cwd=repo`, `timeout=10` y el entorno **sin**
  `GIT_DIR`/`GIT_COMMON_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE` — el repositorio lo fija el árbol
  revisado, no una variable heredada. `None` si git no está, falla o tarda. Nunca lanza.
- `_resolver_principal(repo) -> (Path | None, motivo)`: el primer árbol de
  `git worktree list --porcelain`, aceptado solo si es un árbol de trabajo distinto de `repo` que
  comparte `--git-common-dir` con él. Bare, `.git` separado, submódulo, «este árbol ES el
  principal» y «no se pudo consultar git» devuelven `None` **con el motivo**.
- `resolver_blocklist(repo) -> Blocklist`: **una** resolución por invocación — términos (unión de
  las raíces), raíces, `(ruta, estado observado)` por artefacto y el motivo del principal. La usan
  el aviso y `escanear`, que acepta la `Blocklist` ya resuelta.
- `cargar_blocklist` / `raices_blocklist` / `rutas_blocklist`: vistas finas sobre la misma
  resolución; `cargar_blocklist` conserva su firma (la usa `tests/test_no_pii_en_tests.py`).
- `aviso_blocklist_vacia(bl)` + la rama en `main`: se imprime **antes** de escanear, no toca el
  código de salida y solo afirma lo observado (estado por ruta, cómo acabó la resolución).
- `.pre-commit-config.yaml`: el hook lleva `verbose: true`, porque pre-commit solo muestra la
  salida de un hook que devuelve 0 si el hook es verbose. Sin eso el aviso no llegaba a nadie.

**Lo que NO cambia:** `RUTAS_VETADAS`, `escanear_formas`, límites de palabra, binarios, el CI
(`leak-scan.yml` escribe la lista en el propio checkout, que es su principal).

**Efecto lateral buscado:** `tests/test_no_pii_en_tests.py` se saltaba en los worktrees; ahora
encuentra la lista y **corre**.

## 3. Tests y mutantes

Los tests (`tests/test_precommit_leak_guard.py`, bloque «MEJORAS #161») fabrican **repositorios
git reales** —principal + worktree, `--separate-git-dir`, bare—, no un mock de git: la frontera es
«qué contesta git», y un mock la habría contratado contra mi propia suposición. Y **aíslan a git
de la máquina** (fixture `git_aislado`, tras la R1): los cinco canales de configuración (sistema,
global, plantilla, entorno `GIT_CONFIG_*`, identidad) y el techo de descubrimiento
(`GIT_CEILING_DIRECTORIES`), porque la primera versión heredaba `commit.gpgsign=true` de esta
máquina y suponía que el temporal de pytest no colgaba de ningún repo.

| Test | Frontera |
|---|---|
| `test_worktree_resuelve_la_blocklist_desde_el_principal` | worktree sin gitignored → lee el principal, y lo dice («resuelto: …») |
| `test_principal_no_se_lee_dos_veces` | checkout principal → una sola raíz, motivo «este árbol ES el principal» |
| `test_fuera_de_git_solo_la_raiz_dada` | sin repo (construido con techo) → no rompe, no inventa raíz, motivo «no se pudo consultar git» |
| `test_union_de_terminos_de_ambas_raices` | la lista local no enmascara la del principal |
| `test_git_dir_separado_no_se_toma_la_carpeta_de_metadatos_por_checkout` | **H-02**: el padre de los metadatos no entra como raíz; la lista ajena que viva ahí no se carga |
| `test_repo_bare_no_inventa_checkout` | bare → una raíz, motivo «bare» |
| `test_git_dir_ajeno_en_el_entorno_no_redirige` | `GIT_DIR` a otro repo se ignora |
| `test_mutante_161_termino_conocido_commiteado_desde_worktree_bloquea` | **el mutante de `MEJORAS #161`**: antes verde y en silencio, ahora exit 1 |
| `test_sin_blocklist_en_ninguna_raiz_main_lo_declara` | aviso con rutas, estados y «NO se ha ejecutado»; exit 0 |
| `test_con_blocklist_main_no_avisa` | el aviso no sale cuando hay lista |
| `test_aviso_distingue_no_existe_de_existe_sin_terminos` | **H-04**: estado observado por ruta, en todas las rutas; sin «tampoco la tiene» |
| `test_main_resuelve_la_blocklist_una_sola_vez` | **H-03**: una resolución por invocación |
| `test_escanear_usa_la_blocklist_que_le_pasan` | `escanear` no re-resuelve si le dan la lista |
| `test_hook_leak_guard_es_verbose_para_que_el_aviso_se_vea` | **H-01**: guard sobre `.pre-commit-config.yaml` |
| `test_sin_blocklist_solo_rutas` (preexistente, ahora con `fuera_de_git`) | **H-06**: el estado «fuera de git» se construye |

**Mutantes ejecutados a mano (2026-09-05), nueve, cada uno muerto por su frontera:** aceptar el
candidato de `worktree list` sin verificar (1 test lo mata); volver al padre del common-dir, o
sea el código original (4); no limpiar el entorno (1); `main` resuelve dos veces (1); estado de
ruta fijo, uno por fichero (1 y 1); `main` nunca avisa (1); bare no detectado (1). **Regla que
salió de aquí:** un mutante «superviviente» se comprueba primero contando las líneas que el `sed`
mutó — el primero de H-04 sobrevivió porque no había mutado nada.

**Reproducidos contra el código remediado los contraejemplos del revisor:** firma inyectada por
`GIT_CONFIG_COUNT` → 23/23; `--basetemp` dentro de este worktree → 23/23; `pre-commit run` sin
`-v` → el aviso se ve; gitdir separado / bare / `GIT_DIR` ajeno → tests propios.

**Medido en vivo desde este worktree:** `raices_blocklist` → el worktree y
`C:\Users\tnm33\Dev\FeesDefender`; `cargar_blocklist` → **70 términos**. Los dos commits de esta
rama pasaron el hook **con la lista cargada**, que es la primera vez que eso ocurre desde un
worktree.

## 4. Adjudicación de la revisión adversarial (Codex, 2026-09-05) — NO-SHIP, remediado

- **Objeto revisado:** el diff `3ca97ee..0f8a373` (primera versión del cambio)
- **Ronda:** R1 (diff) — la única, por radio de daño
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-05-mejoras-161-r1-adversarial-review.md`
- **Hallazgos:** 8 — 2 ALTOS, 3 MEDIOS, 3 BAJOS; **8 confirmados, 0 refutados** (2 preexistentes en `main`)
- **Remediado en:** commit `e635e83`

**Independencia: plena** — revisor Codex, adjudicador Claude Code, autor distinto del revisor.
Cada hallazgo se contrastó contra la fuente; la evidencia que reproduje está en el §2 del acta.

| # | Sev. | Hallazgo (frontera, no ejemplo) | Veredicto | Remedio |
|---|---|---|---|---|
| H-01 | ALTO | El aviso no LLEGA: pre-commit solo muestra la salida de un hook que devuelve 0 si el hook es `verbose` (`run.py:217`). (P2) era cosmética | ✅ confirmado | `verbose: true` en el hook + guard `test_hook_leak_guard_es_verbose…`; reproducido el aviso a través de `pre-commit run` sin `-v` |
| H-02 | ALTO | Inferir el checkout del **padre de unos metadatos** es una convención, no una propiedad de git: falla en `--separate-git-dir`, bare y submódulo, y puede cargar una lista **ajena** | ✅ confirmado | `_resolver_principal`: primer árbol de `git worktree list`, aceptado solo **verificado por resultado** (árbol de trabajo + mismo common-dir); si no, «no determinado» y se dice. Entorno sin `GIT_DIR`/`GIT_COMMON_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE`. 3 tests nuevos (gitdir separado, bare, `GIT_DIR` ajeno) |
| H-03 | MEDIO | Dos cargas independientes (aviso y escaneo): un fallo transitorio entre ambas dejaba pasar el término **sin aviso** | ✅ confirmado | Una resolución por invocación (`resolver_blocklist` → `Blocklist`), compartida por aviso y `escanear`; test que cuenta las llamadas |
| H-04 | BAJO | El aviso afirmaba una causa que no comprobó («el principal tampoco la tiene») | ✅ confirmado | Estado **observado** por ruta y motivo de la resolución del principal; test que distingue «no existe» de «existe, 0 términos utilizables» |
| H-05 | MEDIO | La fixture heredaba la configuración git de la máquina (`commit.gpgsign=true` con clave SSH): 128 en cualquier sandbox | ✅ confirmado | `git_aislado`: cierra los **cinco canales** de configuración (sistema, global, plantilla, entorno `GIT_CONFIG_COUNT/PARAMETERS`, identidad). Reproducción del revisor (firma inyectada): 23/23 |
| H-06 | MEDIO | «Fuera de git» se **suponía** del temporal, no se construía: con `--basetemp` dentro de un repo con lista, 3 fallos | ✅ confirmado | Fixture `fuera_de_git` con `GIT_CEILING_DIRECTORIES`; aplicada también al test preexistente. Reproducción: 23/23 |
| H-07 | BAJO | Docstring promete bloquear NIF que `_patrones_forma` excluye a propósito (**preexistente**) | ✅ confirmado | Docstring corregido |
| H-08 | BAJO | El mensaje recomienda `leak-guard:allow` para un bloqueo por VALOR, donde no exime (**preexistente**) | ✅ confirmado | Mensaje corregido: la anotación solo exime detecciones por forma |

**Lo que el revisor midió y cambia el diseño, no solo el código:** en `--separate-git-dir` ni
`--git-common-dir` ni `git worktree list` identifican el checkout principal desde un worktree
enlazado (lo comprobé yo: `worktree list` reporta los metadatos como «worktree»). No hay comando
que lo resuelva, así que la propiedad correcta no es «encontrar el principal» sino **«no leer
nunca como checkout algo que no se ha verificado que lo sea, y declarar cuando no se pudo»**.

**Mutantes tras la remediación (9, cada uno muerto por su frontera):** aceptar el candidato sin
verificar (1 test), volver al padre del common-dir (4), no limpiar el entorno (1), resolver dos
veces (1), estado de ruta fijo × 2 ficheros (1 cada uno), no avisar (1), bare no detectado (1).
**Un falso superviviente:** el primer mutante de H-04 «sobrevivió» porque el `sed` no había mutado
nada; desde entonces cada mutante comprueba el número de líneas mutadas antes de correr.

**No remediado, con razón escrita:** `test_no_pii_en_tests.py` escanea también gitignored bajo
`tests/`/`core/` (contrato del test, preexistente); un subdirectorio del worktree omite la lista
local (los consumidores pasan la raíz por `__file__`); el CI ya fallaba con secret vacío
(preexistente). **Cobertura de la remediación: sin revisión adversarial** — una ronda por radio de
daño; se reprodujeron los contraejemplos del revisor y hay mutantes, pero nadie ajeno ha atacado
el árbol remediado.
