---
tipo: revision-adversarial
objeto: "diff origin/main...81082a6 del PR #286 — «_caso.md: actualizar conserva lo que no es del registrador» (MEJORAS #146)"
objeto_rev: "2"
commit: "81082a6"
ronda: "2"
revisor: Claude Code (sesión independiente)
veredicto: LISTA-CON-CAMBIOS
marcador_nonce: qzvk
sha256_informe: bf72102401afb750d287c5031d7d6a2c1ff20fb8ac63dacc398395c23a063c77
adjudicado_en: docs/superpowers/specs/2026-09-05-caso-md-preservar-al-actualizar-design.md §9
adjudicador: Claude Code
independencia_adjudicacion: "más débil — autor y revisor son el mismo modelo (AGENTS.md §Revisor sustituto)"
---

> **Acta de revisión adversarial R2 sobre el DIFF.** Segunda y última ronda de la pieza (radio de
> daño: escribe el fichero del lock y cierra un defecto que destruía una nota). El §0 es el mandato
> literal, el §1 la voz del revisor sin una coma cambiada, el §2 mi evidencia y el §3 el mapa.
>
> **Dónde vive la adjudicación:** en la **rev. 3 del diseño**
> (`2026-09-05-caso-md-preservar-al-actualizar-design.md`, §9).
>
> **Revisor sustituto, independencia MÁS DÉBIL.** Codex sin cupo; subagente de Claude Code sin el
> contexto de autoría (`AGENTS.md` §«Revisor sustituto»). Lo que compensa: ejecutó los 27 tests de
> HEAD contra una copia de `origin/main` y midió cuál mataba qué, y las tres sondas de código
> reproducen el defecto con salida literal. Se registra como `revisor: Claude Code (sesión
> independiente)`, nunca como «Codex».
>
> **Higiene del workdir:** un primer intento de esta ronda (workdir `…-r2-diff-1245`) murió por
> límite de uso dejando solo sondas y sin informe; se abrió un workdir nuevo (`…-r2-diff-1520`)
> con el mandato actualizado al HEAD `81082a6`, que el revisor declaró limpio en su primera línea.
> El digest se recalculó al recibirlo (`bf721024…`) y coincide.

## 0. Mandato, literal

# MANDATO — Revisión adversarial R2 sobre el DIFF (FeesDefender, MEJORAS #146)

## Higiene, primero

- **Solo lectura.** No editas, creas ni borras nada dentro del repo. Nada de `git checkout`, `stash`, `commit`, `merge`, `rebase`.
- Tu único fichero de salida es `INFORME.md` en el directorio de trabajo indicado. Si encuentras allí cualquier fichero distinto de `MANDATO.md`, no lo leas y decláralo en la primera línea.
- Fecha del sistema: 2026-09-05. Escribe en castellano.
- No has visto la conversación del autor ni la ronda anterior más allá de lo que hay en el repo; no debes buscarlas.

## Objeto

- Repo (worktree, solo lectura): `C:\Users\tnm33\Dev\FeesDefender\.claude\worktrees\mejoras-apertura-expedientes-c1945d`, HEAD `81082a6` (compruébalo con `git log -1 --format=%h`).
- Diff revisado: `git diff origin/main...HEAD` (base `2b32c32`). Nueve ficheros (el último commit, `81082a6`, comparte el escritor atómico con `_atomic_write_caso_md` para que el censo de `tests/test_escritura_censo.py` no suba): `core/case_manager.py`, `core/config.py`, `plugins/expedientes_xl/tiers.py`, `tests/test_caso_md_preservar_al_actualizar.py`, `CLAUDE.md`, `docs/RUNBOOK_APERTURA_EXPEDIENTE.md`, `docs/MEJORAS_FUTURAS.md`, y dos documentos nuevos en `docs/superpowers/specs/`: el diseño `2026-09-05-caso-md-preservar-al-actualizar-design.md` (rev. 2, con la adjudicación de la R1 en su §8) y el acta `…-r1-adversarial-review.md`.
- Contrato que el diff dice cumplir: el §3 y el §5 del diseño rev. 2. Léelos primero. Después ataca el código, no el diseño: **esta es la ronda sobre el diff**.

## Qué se te pide

Nada se da por bueno sin abrir el fichero y, cuando sea ejecutable, sin ejecutarlo. Puedes correr Python con `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe` desde el worktree, con `CASOS_ROOT` apuntando a un directorio temporal **fuera del repo** (bajo tu workdir o `$env:TEMP`); nunca contra `data/CASOS/`, `G:` ni `H:`. Puedes correr `pytest` sobre ficheros concretos de `tests/`.

Lentes, en orden de daño:

1. **Pérdida o corrupción de datos que el diff introduce.** Construye `_caso.md` adversos y pásalos por `register_expediente`, `register_drive_ev`, `cache_drive_folder_info`: frontmatter con claves ajenas en top-level y en `meta`; `sudespacho_expedientes` con entradas sin `id`, con `id` numérico vs. cadena (`648` vs `"648"`), duplicadas, con estado D8; cuerpo con la sección `## Expedientes sudespacho` al final sin `## Navegación` detrás, con dos secciones de expedientes, con la línea `- Drive E&V team:` repetida, con `## Navegacion` sin tilde, con líneas en blanco de más, con CRLF, vacío, solo frontmatter; `_caso.md` sin `meta`; `meta` que no es un dict. Para cada uno: ¿qué se pierde, qué se duplica, qué queda mal formado? Compara con el comportamiento en `origin/main` cuando aporte.
2. **La fusión por entrada (`_fusionar_expedientes`).** ¿Puede colapsar dos expedientes distintos? ¿Puede resucitar uno borrado? ¿Qué pasa con `remove_expediente_link` seguido de un registrador cuyo `meta` aún trae la entrada retirada (los registradores construyen `CaseMeta` desde `meta`, no desde top-level)? Ejecuta ese caso.
3. **La reescritura por fragmentos (`_actualizar_cuerpo`).** Idempotencia; que no toque ninguna línea fuera de los tres fragmentos (demuéstralo con un cuerpo que tenga texto en todas las secciones); comportamiento ante los anclajes ausentes o repetidos; el límite de la sección `(c)` cuando el siguiente encabezado es `#` de nivel 1 o `###`.
4. **Atomicidad y temporales.** `_escribir_indice_atomico`: PID en el nombre, `os.replace`, limpieza en fallo. ¿Queda el temporal si falla `os.replace`? ¿Puede el temporal colisionar con el de `_atomic_write_caso_md` en el mismo proceso? ¿Está el patrón `._caso.*.tmp` en todos los registros que los guards exigen (`MERGE_EXCLUSIONS`, `PROTOCOL_EDIT`, y lo que `tests/test_apertura_v1_control_files.py` y `tests/test_expedientes_xl_tiers.py` comprueben)?
5. **El cambio de parser en los registradores** (`text.split("---", 2)` → `read_md`). ¿Hay algún `_caso.md` que el parser viejo aceptara y `read_md` no, o al revés, con efecto distinto de «cae a creación»? Busca otros consumidores del fichero que sigan con `split` y di si la divergencia importa.
6. **Los tests.** ¿Cada mutante del §5 del diseño tiene su test y el test muere de verdad con el código de `origin/main`? Compruébalo al menos para M1, M4, M5-bis, M11, M12, M13 y M14 **ejecutando** los tests contra el código de `origin/main` (p. ej. `git show origin/main:core/case_manager.py` a un fichero temporal e importarlo con `CASOS_ROOT` temporal, o cualquier técnica que no escriba en el repo). ¿Hay algún test que pase por razones distintas de las que su docstring afirma? ¿Falta el mutante de algo que el diff hace?
7. **Documentos.** El acta: frontmatter con los diez campos, marcadores con nonce, digest que recomputa igual (canonicalización UTF-8/LF/un salto final), `adjudicado_en` que resuelve. El diseño: ¿el §8 cumple el encabezado canónico y la ficha de seis líneas del contrato `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` §5? ¿Alguna afirmación del diseño rev. 2, de `CLAUDE.md`, del runbook o del banner de `#146` dice más de lo que el código hace?

## Formato del informe

`INFORME.md`:
1. Primera línea: higiene del workdir.
2. Hallazgos `H-01`, `H-02`… por severidad (CRÍTICO / ALTO / MEDIO / BAJO): título, severidad, evidencia (`fichero:línea`, salida de la sonda), por qué importa, remedio breve.
3. Lo verificado y correcto, con evidencia (incluida la tabla de qué mutantes ejecutaste contra `origin/main` y su resultado).
4. Lo que no pudiste verificar y por qué.
5. Veredicto: `SHIP` · `LISTA-CON-CAMBIOS` · `REQUIERE-REVISION` · `NO-SHIP` · `NO-EJECUTABLE`, con una frase.

Al terminar, calcula el `sha256` del informe canonicalizado (UTF-8, `\r\n`→`\n`, sin saltos al borde, un único `\n` final) y devuelve en tu respuesta final SOLO: ruta, sha256, veredicto y recuento por severidad.

## 1. Informe recibido de Claude Code (sesión independiente), sin modificar

<!-- informe-literal:inicio:qzvk -->
Higiene del workdir: **limpio** (solo `MANDATO.md` al llegar). Repo en `81082a6` (`git log -1 --format=%h`), `git status` limpio antes y después; base `2b32c32` (`merge-base`), nueve ficheros en el diff. Sondas en `probes/` de este workdir con `CASOS_ROOT` bajo `probes/CASOS*`, intérprete `.venv` y `core` del worktree (`core.__file__` verificado en cada sonda); la comparación con `origin/main` se hizo sobre una copia `git archive origin/main` en `probes/main_copy/` (sin tocar el árbol). `pytest` corrió con `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1` y `--basetemp` fuera del repo; lo único que `git status --ignored` muestra son `__pycache__`/`.pytest_cache` ya ignorados. Ninguna escritura en el repo, `data/CASOS/`, `G:` ni `H:`.

# Revisión adversarial R2 — DIFF `origin/main...81082a6` (MEJORAS #146)

revisor: Claude Code (sesión independiente) · fecha: 2026-09-05 · objeto: diff `2b32c32..81082a6`, contrato §3 y §5 del diseño rev. 2

## 1. Hallazgos

### H-01 · MEDIO · `_fusionar_expedientes` no es idempotente: el espejo `meta.sudespacho_expedientes` que el propio sumidero escribe vuelve como «nuevos», y una entrada sin `id` se DUPLICA en cada registrador (crecimiento exponencial)

**Evidencia.** `core/case_manager.py:259-280`: toda entrada de `nuevos` que no sea dict con `id` conocido se añade (`:279 salida.append(n)`), sin comprobar si ya está. Los registradores construyen `CaseMeta` desde `fm["meta"]` (`register_drive_ev` `:793-808`, `cache_drive_folder_info` `:906-920`), y desde la primera actualización ese espejo **es** la lista fusionada (`:348`), así que todo lo que no tenga `id` vuelve a entrar como nuevo en cada pasada. Sonda `probes/p3_main_vs_head.py`:

```
[head] L2.c-bis (una entrada {"element": "extrajudiciales"} en top y en meta) + register_drive_ev x4:
       top len = 2 -> 4 -> 8 -> 16
[head] L2.c   (una entrada sin id solo en top-level) + register_drive_ev x3: 1 -> 2 -> 4
[main] L2.c   -> 0 (la entrada se perdía: el R1/H-02 de siempre)   [main] L2.c-bis -> KeyError: 'id'
```

Sonda `p1_adversos.py` caso B: con `[{sin id}, {id:648 D8}, {id:"648"}, "basura", None]` los tres registradores dejan **8** entradas (las sin `id`, la cadena y el `None` duplicados) y la sección (c) pinta dos veces `ID ? → 00_Input/sudespacho_?/`.

**Segundo ejemplo de la misma frontera** (`p2_fusion_cuerpo.py` L2.b, `p3` L2.b): un mutador que retira una entrada **solo** del top-level deja el espejo rancio, y el siguiente `register_drive_ev` la **resucita** (`top ids=['700', '648']`). Hoy no ocurre porque `remove_expediente_link.py` y `limpieza_post_audit.py` limpian también el espejo (verificado, `scripts/remove_expediente_link.py`, `scripts/limpieza_post_audit.py:171-175`), y en `origin/main` el espejo también ganaba; pero el §3.2 convierte «el espejo se mantiene en sincronía» en un invariante del que depende la corrección sin declararlo.

**Por qué importa.** Es un defecto que el diff **introduce** (en `main` la entrada malformada se perdía o abortaba; no crecía). El disparador es una entrada sin `id`, que ningún escritor del core produce, pero `_caso.md` está declarado editable a mano desde Cowork (`tiers.PROTOCOL_EDIT`) y el diseño hace la plantilla «total sobre lo persistido» precisamente para tolerar entradas malformadas (§3.1, M12). Tolerarlas y a la vez duplicarlas en cada pull convierte un fichero con una entrada rara en uno que dobla de tamaño con cada `pull_drive_ev`; a los 20 pulls son ~10⁶ entradas y todo lector de `_caso.md` (catálogo, lock, `get_case_status`) se degrada. No lo subo a ALTO porque hace falta la entrada malformada y ningún flujo la crea; no lo bajo porque es autoamplificante y la R1 calibró como MEDIO la pérdida silenciosa equivalente (H-02).

**Remedio.** Hacer la fusión idempotente sobre su propia salida: (a) no añadir una entrada de `nuevos` que ya esté en `salida` por igualdad (`if n in salida: continue`), o (b) solo fusionar entradas con `id` y descartar/normalizar las demás en el sumidero (una entrada sin `id` no es un vínculo CRM). Mutante: entrada sin `id` + dos registradores → la longitud de `sudespacho_expedientes` no cambia. Y declarar en §3.2 que el registrador **no puede borrar** por esta vía y que cualquier escritor que retire una entrada debe retirarla de los dos niveles (o mejor: que el sumidero no lea el espejo como entrada nueva).

### H-02 · MEDIO · La sección (c) se corta en el siguiente `## `, así que un `# Título de nivel 1` (y un `###`) escrito a mano tras ella se DESTRUYE en la siguiente actualización, y `CLAUDE.md`/runbook prometen que «fuera de la sección, no» se pierde nada

**Evidencia.** `core/case_manager.py:247`: `fin = next(... if lineas[i].startswith("## "))`. Un `# ` de nivel 1 y un `### ` no casan. Sonda `p2_fusion_cuerpo.py` L3.a (cuerpo con texto a mano en TODAS las secciones y, entre la sección (c) y `## Navegación`, un `### Detalle del abogado` con párrafo y un `# Notas nivel 1` con párrafo) + `register_drive_ev`:

```
OK   'Intro escrita a mano.'   OK 'Testigo: Mengano'   OK 'Comentario sede.'   OK 'Otro origen: WhatsApp'
PERDIDO 'Esto lo escribi yo bajo un ###.'   PERDIDO '# Notas nivel 1'   PERDIDO 'Y esto bajo un # nivel 1.'
OK   '[[STS_1_2026]]'          OK 'Texto final.'
```

`CLAUDE.md:161`: «Una nota **dentro** de esos tres fragmentos sí se pierde; fuera, no». `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:38`: «Lo que escribas dentro de esa sección sí se pierde…; fuera de ella, no». Diseño §3.3 (`:151`): «hasta el siguiente `## ` o el final» (fiel al código) y `:153-154`: «Todo lo demás… se conserva línea a línea».

**Por qué importa.** Un `#` de nivel 1 cierra la sección `##` en cualquier lector Markdown: para el abogado ese texto está **fuera** de la sección generada, y el aviso `<!-- sección generada… -->` no le dice que el registrador la extiende hasta el próximo `##`. Es exactamente la pérdida de nota a mano que `#146` cierra, en su único hueco. (El `###` es discutible —Markdown lo subordina al `##`— pero el aviso tampoco lo dice.) En `main` se perdía todo el cuerpo, así que el diff mejora; lo que falla es que la promesa escrita es más ancha que el código.

**Remedio.** Límite de la sección = siguiente encabezado de nivel ≤ 2: `re.match(r"^#{1,2}\s", ln)` (y decidir explícitamente si `###` corta; si no corta, decirlo en el aviso y en `CLAUDE.md`). Mutante: `# Notas` con párrafo entre la sección (c) y `## Navegación` + registrador → sobrevive. Ajustar `CLAUDE.md:161` y runbook `:38` a lo que el código haga.

### H-03 · BAJO · El diff introduce anclas/alias YAML (`&id001` / `*id001`) en el frontmatter de `_caso.md`, y el §6 dice que el formato del frontmatter no se toca

**Evidencia.** `_actualizar_indice` (`:341-350`) pone el **mismo objeto lista** `expedientes` en `propias["sudespacho_expedientes"]` (`:292`) y en `meta_dict["sudespacho_expedientes"]` (`:348`); `yaml.safe_dump` lo serializa como ancla + alias. Sonda `p3`: `[head] ANCLA YAML tras register_expediente: '&id' in fm: True` · `[main] … False` (en `main` `asdict(meta)` copiaba la lista y los dos niveles eran objetos distintos). Salida real (`p1` caso A): `sudespacho_expedientes: &id001` … `meta: … sudespacho_expedientes: *id001`. Diseño §6 `:236-237`: «**No toca:** … el formato del frontmatter».

**Por qué importa.** `_caso.md` es la vista humana del índice y el carve-out editable desde Cowork; `*id001` en `meta` no es legible ni editable a mano con independencia del top-level, y cualquier lector YAML sin alias (o una edición manual que rompa el ancla) deja el fichero sin `meta.sudespacho_expedientes`. PyYAML `safe_load` lo resuelve, así que los lectores del repo no se rompen (verificado: todos usan PyYAML). Es un cambio de formato no declarado, no una pérdida.

**Remedio.** `meta_dict["sudespacho_expedientes"] = copy.deepcopy(expedientes)` (o `list(dict(e) for e in …)`); mutante: tras un registrador, `"&id" not in index.read_text()`.

### H-04 · BAJO · Tres etiquetas del §5 son falsas medidas contra `origin/main`: M14 y M15 **pasan** con `main` sin estar marcados (+); M16 está marcado (+) y **muere** con `main`; y el docstring del test dice «M6-M10 son POSITIVOS»

**Evidencia.** El fichero `tests/test_caso_md_preservar_al_actualizar.py` de HEAD ejecutado contra la copia de `origin/main` (`probes/main_copy`, `pytest -p no:randomly`): 7 PASSED / 20 FAILED. Tabla completa en §2. En concreto: `test_m14_…` **PASSED** en `main` (allí `register_drive_ev` reconstruía el cuerpo desde `meta`, que ya no tenía el 648; el mutante mata la **rev. 1**, no `main`), `test_m15_…` **PASSED** (reconstruir dos veces es determinista), `test_m16_…` **FAILED** (asserta que `clave_ajena` sobrevive, que es la propiedad de M5). Diseño §5 `:205-206`: «Los marcados (+) son positivos: pasan también con `556b8b2`». `tests/…:9-10`: «M1-M5 mueren…; M6-M10 son POSITIVOS», pero M10-bis y M10-ter mueren en `main`.

**Por qué importa.** El §5 existe para que se sepa qué protege contra endurecer de más y qué mata el defecto; tres filas dicen lo contrario de lo medido. No afecta al código.

**Remedio.** Marcar M14 y M15 como (+) (o redactar «mata la rev. 1»), quitar el (+) a M16 o partirlo (la parte positiva es `estado_repositorio is None`), y actualizar el docstring del test con la lista real.

### H-05 · BAJO · El diseño (§6, §8) y el acta (§3) remiten el escritor no atómico a `MEJORAS #162`, que es otra cosa; la entrada creada por el diff es `#167`

**Evidencia.** Diseño `:249` y `:287`, acta `:250`: «`MEJORAS #162`». `docs/MEJORAS_FUTURAS.md:7260`: «## 162. Documento de identidad y domicilio del colaborador desde los contratos del Drive». La entrada nueva del diff: `:7367` «## 167. `case_locator._update_ciudad_metadata` escribe `_caso.md` en sitio…», y el banner de `#146` (`:6495`) sí dice `#167`.

**Remedio.** Sustituir `#162` por `#167` en los tres sitios (el acta es el archivo de la voz del revisor solo en su §1; el §3 es del adjudicador y puede corregirse).

### H-06 · BAJO · El §6 del diseño dice «No toca: … los tres registradores» y el diff los toca (y el §3.4 lo declara)

**Evidencia.** Diseño `:236-237` vs `:168-177` (§3.4: «Lo único que cambia en ellos es el parser») y el diff sobre `register_expediente:378-384`, `register_drive_ev:788-791`, `cache_drive_folder_info:901-904`. Contradicción interna del documento que define el alcance revisado.

**Remedio.** «No toca la forma de los tres registradores (solo su parser, §3.4)».

### H-07 · BAJO · «Un fichero sin frontmatter parseable no tiene nada que conservar» es más ancho que el código: un `_caso.md` con frontmatter vacío o no-dict **y cuerpo escrito** va a creación y pierde el cuerpo

**Evidencia.** `_write_case_index:332`: `if isinstance(fm_previo, dict) and fm_previo:` → si no, creación. Sonda `p1` casos J (`---\n---\n` + «# Titulo mio / Nota importante.») y K (frontmatter que es una lista YAML + misma nota): tras el registrador el cuerpo es la plantilla y la nota **no está**. Diseño §3.1 `:99-102`.

**Por qué importa.** Es conducta heredada (`main` reconstruía siempre) y el caso es raro (`ensure_case` siempre escribe frontmatter), pero el diseño lo justifica con una afirmación falsa cuando hay cuerpo. La R1 propuso «abortar con error explícito» como alternativa; el diseño eligió reconstruir sin declarar el precio.

**Remedio.** O redactar el §3.1 («se reconstruye, y si había cuerpo se pierde: no se puede distinguir de un truncado»), o conservar el cuerpo cuando `read_md` devolvió `{}` **y** el texto no empieza por `---` (un cuerpo sin frontmatter no es un truncado).

### H-08 · BAJO · La divergencia de parsers sigue viva fuera de los tres registradores, y en `scripts/sync_sudespacho.py:337` sin guarda: un `_caso.md` truncado revienta el bucle de `sync_all` antes de llegar al sumidero que lo repararía

**Evidencia.** Consumidores que siguen con `text.split("---", 2)`: `core/case_manager.py:842, 870, 956, 1390`, `core/casos/case_locator.py:174, 215, 332`, `scripts/scheduled_sync.py:128`, `scripts/sync_sudespacho.py:337`, `scripts/verify_city_layout.py:42`. Todos menos `sync_sudespacho.py:337` (dentro de `sync_all`, `:303`) envuelven el `split` en `try/except` o comprueban `len(parts)`. Divergencias de gramática entre `split` y `_FM_RE` (`core/utils.py:242`): fichero truncado (split → `ValueError`; `read_md` → `{}`), cierre `----`, BOM (los dos fallan igual). Para un fichero bien formado devuelven lo mismo (verificado con los 27 tests y las sondas).

**Por qué importa.** Fuera del alcance declarado (§3.4 solo promete los tres registradores) y heredado; se anota porque el argumento del diff («el registrador tolera el truncado y el sumidero lo reconstruye») no alcanza al flujo real `sync_all`, que muere una línea antes de llamar a `register_expediente`.

**Remedio.** `try/except` o `read_md` en `sync_sudespacho.py:337`; opcionalmente un guard que prohíba `split("---", 2)` sobre `_caso.md` fuera de `read_md`.

## 2. Verificado y correcto

**Mecanismo central (lente 1).** `p1_adversos.py`, once ficheros adversos por los tres registradores en cadena:

| Caso | Resultado |
|---|---|
| A. claves ajenas top-level (`bucket_override`, `zzz_ajena`) y en `meta` (`proyeccion_local`, `otra`) | las cuatro sobreviven, en su posición; `read_bucket_overrides` y `_es_proyeccion_local` las ven |
| B. `648` numérico vs `"648"` | tratados como el mismo (`str(id)`), coherente con `_find_expediente_entry`; el estado D8 (`last_sync`, `doc_ids`) sobrevive y `read_pull_state` lo lee. (La duplicación de lo que no tiene `id` es H-01) |
| C. sección (c) al final sin `## Navegación` detrás + `## Navegacion` sin tilde | la sección se sustituye en su sitio, `## Navegacion` intacto; la nota **dentro** de la sección se pierde (declarado) |
| D. dos secciones (c) + dos líneas `- Drive E&V team:` | se gestiona la primera de cada; la segunda sección queda como texto ajeno (rancia, sin aviso). Un registrador sin IDs de Drive **retira** la línea (frontmatter manda) |
| E. CRLF + líneas en blanco de más + texto final | texto conservado, blancos conservados (máx. 5 → 5), CRLF de plataforma en disco antes y después (`p2` L4.a: `write_text` escribe CRLF en Windows; lo prometido es el texto, §3.3) |
| F. solo frontmatter | sección (c) al final; (a)/(b) no se insertan sin anclaje (declarado) |
| G. sin `meta` | funciona; `fecha`/`creado_en` quedan `''` porque los registradores parten de `meta` vacío — **heredado**, idéntico en `main` |
| H. `meta` cadena / lista | los **tres registradores** revientan (`TypeError`/`AttributeError`) **antes** del sumidero, en `meta_dict.get` — código no tocado por el diff, idéntico en `main`; la guarda `isinstance` del sumidero (`:345`) no es alcanzable por esta vía |
| I. fichero de 0 bytes / M13 truncado | creación limpia, un solo frontmatter |
| J/K. frontmatter vacío o lista + cuerpo | creación → cuerpo perdido (H-07; heredado) |

**Cuerpo por fragmentos (lente 3).** `p2` L3.a: texto a mano en título, Partes, Sede, Fuente documental, Navegación y una sección final sobreviven a `register_drive_ev`; la línea Drive E&V se inserta tras `- Remoto rclone:` y la sección (c) antes de `## Navegación` (salvo H-02). L3.b: tres ciclos «vaciar expedientes+IDs → registrador → añadir → registrador»: el cuerpo vuelve **idéntico** al de la creación en cada ciclo (`cuerpo == baseline: True`, máx. blancos 2): la retirada de (b) y (c) no deja huecos y la inserción no los acumula. L3.c: línea de estado repetida → solo la primera se actualiza; otra con distinto `case_id` no se toca. M15 (bytes idénticos con el mismo `meta`) verde en HEAD.

**Fusión (lente 2).** `p2` L2.a: `scripts/remove_expediente_link.py` real (limpia top y espejo) + `register_drive_ev` → el 648 **no** resucita y el cuerpo deja de listarlo. L2.d: mismo `id` en `extrajudiciales` y `expedientes_judiciales` colapsa en una entrada — heredado (`register_expediente` ya deduplicaba por `id`, `update_pull_state` también).

**Atomicidad (lente 4).** `p2` L4.b: `os.replace` monkeypatched a `PermissionError` → excepción propagada, original íntegro, sin `._caso.*`. M10-bis (`write_md` lanza tras escribir basura en el temporal) verde. L4.c: un solo escritor `_escribir_indice_atomico` con `._caso.{os.getpid()}.tmp`, `_atomic_write_caso_md` delega en él (`:1537`); en el mismo proceso las llamadas son secuenciales, así que el mismo nombre no colisiona (dos hilos o un registrador anidado en un mutador sí compartirían nombre: heredado del patrón original). L4.d: `write_md` crea `00_Input` si falta; sin residuo. `._caso.*.tmp` está en `MERGE_EXCLUSIONS` (`core/config.py:405`) y `PROTOCOL_EDIT` (`tiers.py:39`); `test_carveout_espeja_merge_exclusions`, `test_apertura_v1_control_files.py` (que solo cubre `FICHEROS_CONTROL` de V1, no `_caso`), `test_pull_state_atomic.py` (glob `._caso.*.tmp` `:194,234`) y `test_escritura_censo.py` (techo 88) **verdes**: 169 passed en `tests/test_caso_md_preservar_al_actualizar.py test_apertura_v1_control_files.py test_expedientes_xl_tiers.py test_escritura_censo.py test_pull_state_atomic.py test_intake_drive.py test_skill_registrar_outputs.py`.

**Parser (lente 5).** Ver H-08; en ficheros bien formados `read_md` y `split` coinciden (27 tests + sondas). M9 existe y sigue válido (`tests/test_intake_drive.py:356`, pasa en HEAD).

**Mutantes contra `origin/main` (lente 6).** Fichero de tests de HEAD sobre la copia de `origin/main`:

| Test | §5 dice | En `main` | Veredicto |
|---|---|---|---|
| M1 ×3 (`test_la_nota_del_abogado_sobrevive…`) | mata | FAILED | mata ✓ |
| M2, M2-bis | mata | FAILED | ✓ |
| M3 | mata | FAILED | ✓ |
| M4 ×3 | mata | FAILED | ✓ |
| M5 ×3, M5-bis | mata | FAILED | ✓ |
| M6 | (+) | PASSED | ✓ |
| M7 ×2 | (+) | PASSED | ✓ |
| M8 | (+) | PASSED | ✓ |
| M10 | (+) | PASSED | ✓ |
| M10-bis, M10-ter | (+) en la fila M10 | FAILED | matan (bien); la fila los mezcla con el positivo |
| M11, M11-bis | mata | FAILED | ✓ |
| M12 | mata | FAILED | ✓ |
| M13 | mata | FAILED | ✓ |
| **M14** | mata | **PASSED** | **no mata `main`** (H-04) |
| **M15** | mata | **PASSED** | **no mata `main`** (H-04) |
| **M16** | (+) | **FAILED** | **no es positivo** (H-04) |

Ningún test pasa por una razón distinta de la que su docstring afirma (revisados uno a uno; M13 trunca dentro del frontmatter, M10-bis parchea el `write_md` que el sumidero usa de verdad). **Mutantes que faltan de lo que el diff hace:** idempotencia de la fusión con entradas sin `id` (H-01); `#`/`###` tras la sección (H-02); ausencia de anclas YAML (H-03); retirada completa de (b) y (c) cuando ya no hay dato (L3.b lo cubre por sonda, ningún test); `648` vs `"648"` en la fusión; truncado con `register_expediente`/`cache_drive_folder_info` (M13 solo usa `register_drive_ev`); `## Navegacion` sin tilde.

**Documentos (lente 7).** Acta: frontmatter con las diez claves del contrato §4 (`_CLAVES_ACTA`) más `adjudicador` e `independencia_adjudicacion`; **exactamente un** par de marcadores `informe-literal:inicio/fin:kqzw`, el nonce no aparece dentro del bloque; digest recomputado (UTF-8, LF, un salto final) `95a18400d1f1c292c1a90d61dda92e6d57246f52bc95cfbd2502cf33d482fe1b` = declarado; `adjudicado_en` resuelve a `…design.md §8`, que existe. Diseño §8: encabezado canónico (revisor sin coma, fecha, `LISTA-CON-CAMBIOS, remediado`) y ficha de seis líneas; tabla hallazgo→veredicto→remedio y prosa de la divergencia (H-01 con remedio distinto, razonada). `tests/test_docs_gobernanza.py` (G7/G8 y resto): 46 passed. `CLAUDE.md`, runbook y banner de `#146` describen lo que el código hace salvo lo dicho en H-02 (frontera `#`) y H-05 (`#162`); «16 mutantes» = 16 filas del §5 (27 tests).

## 3. No verificado

- `os.replace` sobre `G:` (Drive for Desktop) y el `_caso.md` de la copia del Drive durante un checkout: sin acceso, y fuera del alcance declarado (§6).
- Cuántos `_caso.md` reales tienen entradas sin `id`, cuerpo con `#`/`###` tras la sección, o alias YAML tras esta versión: `data/CASOS/` fuera del alcance. El impacto real de H-01/H-02 depende de eso.
- Cómo renderiza Cowork/`expedientes-xl` un frontmatter con `*id001` (H-03): solo puedo afirmar que PyYAML lo resuelve.
- Concurrencia entre dos escritores (§6 la remite a `MEJORAS #126`); dos hilos en un proceso compartirían el nombre del temporal.
- La suite completa en orden aleatorio: corrí 7 + 1 ficheros con `-p no:randomly`; el resto de la suite y las dos semillas no se ejecutaron.

## 4. Veredicto

**LISTA-CON-CAMBIOS.** El sumidero hace lo que el §3 promete en el caso normal —20 de los 27 tests mueren con `origin/main` y las sondas confirman que cuerpo, claves ajenas, wikilinks, estado D8 y lock sobreviven con escritura atómica—, pero la fusión por entrada no es idempotente sobre su propio espejo y duplica exponencialmente cualquier entrada sin `id` (H-01, introducido por el diff), la frontera de la sección (c) destruye texto bajo un `#` de nivel 1 que `CLAUDE.md` promete conservar (H-02), y el frontmatter gana anclas YAML no declaradas (H-03); los tres son arreglos de una línea con su mutante, y el resto es rotulado de tests y referencias cruzadas.

Recuento: CRÍTICO 0 · ALTO 0 · MEDIO 2 · BAJO 6.
<!-- informe-literal:fin:qzvk -->

## 2. Evidencia verificada por mí al adjudicar

Los tres hallazgos de código los comprobé sobre mi propio diff antes de tocar nada:

| Hallazgo | Qué comprobé | Dónde |
|---|---|---|
| H-01 | en `_fusionar_expedientes`, toda entrada de `nuevos` sin `id` conocido caía en `salida.append(n)` sin mirar si ya estaba; y `_actualizar_indice` escribe la lista fusionada también en `meta`, que es de donde `register_drive_ev` y `cache_drive_folder_info` construyen el `CaseMeta` siguiente | `core/case_manager.py`, `_fusionar_expedientes` y `_actualizar_indice` |
| H-02 | `fin = next(... if lineas[i].startswith("## "))`: un `# ` o un `### ` no cortaban la sección | `core/case_manager.py`, `_actualizar_cuerpo` |
| H-03 | `meta_dict["sudespacho_expedientes"] = expedientes` y `_frontmatter_del_indice(meta, expedientes)` compartían el mismo objeto lista; `yaml.safe_dump` emite ancla y alias para objetos repetidos | `core/case_manager.py`, `_actualizar_indice` |
| H-07 | `if isinstance(fm_previo, dict) and fm_previo:` era la única puerta a la actualización; todo lo demás iba a creación, cuerpo incluido | `core/case_manager.py`, `_write_case_index` |
| H-08 | `sync_all` hacía `_, fm_raw, _ = text.split("---", 2)` sin `try` | `scripts/sync_sudespacho.py` |

Los de rotulado (H-04, H-05, H-06) los comprobé contra el texto del diseño y del test; el revisor
además ejecutó los tests contra `origin/main` y su tabla es la que adopta el §5 de la rev. 3.

Digest del informe recalculado al recibirlo: `bf72102401afb750d287c5031d7d6a2c1ff20fb8ac63dacc398395c23a063c77`
(UTF-8, `LF`, un único salto final), igual al declarado.

## 3. Mapa hallazgo → remedio (la adjudicación completa está en el §9 del diseño)

| # | Sev. | Veredicto | Dónde se remedia |
|---|---|---|---|
| H-01 | MEDIO | confirmado | `_fusionar_expedientes` idempotente; §3.2; M17 |
| H-02 | MEDIO | confirmado | frontera de la sección en cualquier encabezado; §3.3; M18; `[APER-54]` |
| H-03 | BAJO | confirmado | `copy.deepcopy` del espejo; M19 |
| H-04 | BAJO | confirmado | §5 y docstring del test |
| H-05 | BAJO | confirmado | `#162` → `#167` en diseño §6/§8 y en el §3 del acta R1 |
| H-06 | BAJO | confirmado | §6 |
| H-07 | BAJO | confirmado | cuerpo sin frontmatter se conserva; §3.1; M20 |
| H-08 | BAJO | confirmado | `scripts/sync_sudespacho.py` con `read_md`; §6 |

Recuento: 8 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar. Lo no
verificado por el revisor (§3 de su informe) sigue sin verificar y está en el §9 del diseño.
