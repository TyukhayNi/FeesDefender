---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-08-24-apertura-v1-plan1-modo-v1.md
objeto_rev: "1"
commit: d4b47774b42436d1bd6e4ff0ced1e3cf235787b2
ronda: "6"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: q7vx
sha256_informe: 7594d41daf49ca1b079c30ae813d105283123d92bf0209bb9f89436e43b43253
adjudicado_en: docs/superpowers/plans/2026-08-24-apertura-v1-plan1-modo-v1.md §6
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R6.** El §1 conserva literalmente la voz del revisor. La
> adjudicación vive en el §6 del objeto, no aquí.
>
> **Por qué esta ronda va sobre el PLAN y no sobre la spec.** El §23 de la spec detuvo el bucle de
> revisión del diseño: cinco rondas, 23 hallazgos y cero líneas de código. R6 es la primera que
> revisa **código ejecutado**, no prosa — el diff del Plan 1.
>
> **Objeto:** el diff `bb115de..d4b4777`, cuatro ficheros y 265 líneas, que implementa `--modo v1`
> y sus puertas negativas. La afirmación atacada es la central del plan: que tras el diff «ser una
> ejecución V1» es un hecho comprobable que rechaza lo que V1 no admite **antes de cualquier
> efecto**.
>
> **Montaje del revisor.** Dos copias externas por `git archive` —el commit base y el head—, sin
> `.git` y sin red: solo lectura **por construcción**, no por promesa. La evidencia de no-mutación
> es el SHA-256 canónico de los dos árboles y del `DIFF.patch` al abrir y al cerrar, recalculado
> también por el adjudicador de forma independiente.
>
> **Lo que esta ronda le costó al adjudicador, dicho aquí porque es el dato:** de los nueve
> hallazgos, **cinco son defectos que yo introduje o dejé pasar el mismo día**, y uno de ellos
> —H6-07— refuta una afirmación que yo había dado por probada en el propio plan y por chat.

## 0. Mandato (literal, tal como se entregó)

```text
# Mandato de revisión adversarial — R6 sobre el Plan 1 de Apertura V1 (diff de código)

Eres el **revisor adversarial**. Tu trabajo es **encontrar defectos**, no validar. No eres el
juez: la adjudicación la hace otro. Un hallazgo que no puedas anclar a una línea concreta del
objeto no vale.

## Objeto

Dos copias de solo lectura del repositorio FeesDefender, en el directorio hermano `objeto/`
(fuera de tu workdir, que es el único sitio escribible):

- `objeto/base/` — árbol en el commit `bb115de` (**antes** del cambio).
- `objeto/head/` — árbol en el commit `d4b4777` (**después** del cambio).
- `objeto/DIFF.patch` — el diff completo `bb115de..d4b4777`, 265 líneas, 4 ficheros.

No hay `.git`: es deliberado. Usa `diff -ru`, `grep -rn` y la lectura directa.

**Evidencia de no-mutación.** SHA-256 canónico (por ruta relativa POSIX + bytes, ordenado):

- `objeto/base` = `abfd8e4485fdc4f892ad245a75e49b26f50efbe32a5619660e7bbde3a222138c`
- `objeto/head` = `a4b0c08fff7b5f34a4bd7d4f9055bb581553ad2fe34c55f89020960205106a14`
- `objeto/DIFF.patch` = `a2825f8ee61c393be6859123672663269f2a65b4d60d9fe55b2be279938f109e`

Recalcula estos tres al **abrir** y al **cerrar** y declara ambos valores en tu informe. Si
difieren, dilo: es una mutación y anula la revisión.

## Qué se ha construido y qué contrato dice cumplir

El cambio implementa el **Plan 1** de la primera vertical («V1») del contrato de apertura
integral de expedientes. Las dos fuentes normativas están **dentro del objeto**, léelas:

- Plan ejecutado: `objeto/head/docs/superpowers/plans/2026-08-24-apertura-v1-plan1-modo-v1.md`
- Spec canónica: `objeto/head/docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`
  (interesan sobre todo §21 —alcance de V1—, §23, §24 D3 y §25).
- Reglas del repositorio: `objeto/head/CLAUDE.md`.

**La afirmación central que debes atacar:** que tras este diff, «ser una ejecución V1» es un
hecho **comprobable** del CLI (`--modo v1`) que **rechaza, antes de cualquier efecto**, todo lo
que V1 no admite. El propio historial de este diseño dice que su modo de fallo recurrente es
*nombrar una propiedad deseada y llamarlo contrato* (§23 de la spec). Búscalo aquí.

## Preguntas que quiero contestadas, todas ancladas a línea

1. **¿La puerta corre de verdad antes de cualquier efecto?** Recorre `main()` en
   `objeto/head/scripts/abrir_caso.py` y busca **cualquier** efecto —lectura remota, escritura en
   disco, creación de directorio, llamada a la API de Drive o del CRM, lectura de `.env`,
   side-effect de import— que pueda ocurrir **antes** de que se evalúe `validar_modo`. Incluye
   los efectos a nivel de **importación de módulo** y los de **callbacks de Typer**, no solo los
   del cuerpo de `main`.
2. **¿El modo `libre` conserva el comportamiento byte a byte?** El plan lo exige. Compara
   `base` y `head` y di si alguna invocación que antes funcionaba ahora cambia de comportamiento,
   de código de salida o de salida por consola.
3. **¿Las puertas son las correctas y están completas?** V1 admite `--crm skip` y
   `--fuente drive_ev`. ¿Hay **otras** banderas de `main` que, combinadas con `--modo v1`,
   producirían un efecto que V1 prohíbe y que la puerta no mira? Revisa una por una la firma de
   `main` (por ejemplo `--dry-run`, `--force`, `--yes`, `--case-id`, `--extraer-adjuntos`,
   `--cuantia`, `--folder-id`). Si encuentras una, di **qué efecto concreto** produce y por qué
   contradice el alcance de V1 según §21 de la spec.
4. **¿Los tests prueban lo que dicen probar?** Lee
   `objeto/head/tests/test_abrir_caso_modo_v1.py`. Señala cualquier aserción vacua, tautológica,
   o que pasaría igual con la implementación rota. En particular:
   ¿`test_v1_aborta_antes_de_crear_el_esqueleto` distingue de verdad «abortó antes» de «abortó
   después pero no dejó rastro»? ¿`test_modo_libre_conserva_el_comportamiento` puede fallar
   alguna vez?
5. **¿El arnés de los tests esconde un defecto?** Los tests de CLI parchean
   `cli.case_manager.ensure_case`, `cli._despachar_intake` y `cli._alta_crm`. ¿Ese parcheo oculta
   algún camino real? ¿Existe algún camino de `main` que llegue a un efecto **sin** pasar por
   esos tres nombres?
6. **¿La documentación afirma más de lo que el código hace?** Compara el bloque «Modo V1»
   añadido a `objeto/head/docs/RUNBOOK_APERTURA_EXPEDIENTE.md` con lo que `validar_modo`
   realmente garantiza. Cualquier promesa no respaldada por código es un hallazgo.
7. **¿El bloque de erratas del plan es exacto?** El ejecutor añadió una sección «Erratas del
   plan» al plan. Verifica sus tres afirmaciones contra el código y los tests. Si alguna es
   falsa o se atribuye un mérito que no le corresponde, es un hallazgo.
8. **Lo que NO está y debería.** ¿Falta alguna prueba negativa evidente? ¿Hay algún modo de
   invocar el CLI que un lector del runbook creería V1 y no lo es?

## Reglas de tu informe

- **Un hallazgo por bloque**, con: `ID` (`H6-01`, `H6-02`…), **severidad** (CRÍTICO / ALTO /
  MEDIO / BAJO), **fichero:línea** del objeto, **cita literal** del código o del documento, **por
  qué es un defecto** contra la fuente que cites, y **qué lo demostraría** (un comando, un test).
- Si no puedes verificar algo, escribe **SIN VERIFICAR** y di qué te faltó. **No lo declares
  refutado.** Un revisor que no corre no refuta.
- **Veredicto final obligatorio**, exactamente uno de: `SHIP`, `REQUIERE-REVISION`, `NO-SHIP`.
- No propongas reescrituras completas: señala el defecto y su prueba.
- No escribas nada fuera de tu workdir. No toques `objeto/`.

Escribe el informe completo en `INFORME_R6.md` dentro de tu workdir, y devuelve como último
mensaje un resumen con el recuento por severidad, el veredicto y los tres SHA-256 recalculados.
```

## 1. Informe recibido de Codex, sin modificar

Bloque delimitado por el nonce `q7vx`, con digest `sha256_informe` en el frontmatter. Se recibió
en un fichero fuera del repo (`…/fd-r6/informe/INFORME_R6.md`) y se pega aquí sin una sola
edición: yo soy la parte revisada, así que sin el original archivado nadie puede contrastar qué
dijo el revisor con qué decidí yo que dijo.

<!-- informe-literal:inicio:q7vx -->
# Informe de revisión adversarial R6 — Plan 1 de Apertura V1

## Objeto, método y evidencia de no mutación

Objeto revisado: diff `bb115de..d4b4777`, entregado como dos árboles sin `.git` y
`DIFF.patch`. La comparación de hashes por fichero confirma que el objeto cambia solo estos cuatro
ficheros: añade `tests/test_abrir_caso_modo_v1.py` y modifica
`scripts/abrir_caso.py`, `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` y
`docs/superpowers/plans/2026-08-24-apertura-v1-plan1-modo-v1.md`.

El SHA-256 canónico de árbol se calculó ordenando los ficheros por ruta relativa POSIX y
alimentando el hash, para cada fichero, con los bytes UTF-8 de esa ruta seguidos de los bytes del
fichero. Los valores de apertura y cierre son idénticos:

| Objeto | Apertura | Cierre | Esperado | Resultado |
|---|---|---|---|---|
| `objeto/base` (1.055 ficheros) | `abfd8e4485fdc4f892ad245a75e49b26f50efbe32a5619660e7bbde3a222138c` | `abfd8e4485fdc4f892ad245a75e49b26f50efbe32a5619660e7bbde3a222138c` | `abfd8e4485fdc4f892ad245a75e49b26f50efbe32a5619660e7bbde3a222138c` | coincide |
| `objeto/head` (1.056 ficheros) | `a4b0c08fff7b5f34a4bd7d4f9055bb581553ad2fe34c55f89020960205106a14` | `a4b0c08fff7b5f34a4bd7d4f9055bb581553ad2fe34c55f89020960205106a14` | `a4b0c08fff7b5f34a4bd7d4f9055bb581553ad2fe34c55f89020960205106a14` | coincide |
| `objeto/DIFF.patch` | `a2825f8ee61c393be6859123672663269f2a65b4d60d9fe55b2be279938f109e` | `a2825f8ee61c393be6859123672663269f2a65b4d60d9fe55b2be279938f109e` | `a2825f8ee61c393be6859123672663269f2a65b4d60d9fe55b2be279938f109e` | coincide |

No hubo mutación del objeto. Toda ejecución se hizo sobre copias bajo `informe/scratch/`.

## Hallazgos

### H6-01 — ALTO — La importación lee `.env` antes de que exista la puerta

- **Fichero:línea:** `objeto/head/scripts/abrir_caso.py:32`; `objeto/head/core/config.py:16-18`.
- **Cita literal:** `from core import abrir_caso as brain` y
  `load_dotenv(_PROJECT_ROOT / ".env", override=False)`.
- **Fuente contrariada:** el plan promete que la validación es «antes de cualquier efecto»
  (`docs/superpowers/plans/2026-08-24-apertura-v1-plan1-modo-v1.md:5-7`) y D3 la sitúa antes de
  toda lectura remota (`docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1682-1684`).
- **Por qué es defecto:** importar `scripts.abrir_caso` importa `core.abrir_caso`, que importa
  `core.config`, que lee `.env` y puede mutar `os.environ`. Esto sucede antes de construir Typer,
  parsear `--modo` y ejecutar `validar_modo` en `scripts/abrir_caso.py:421`. La primera sentencia
  de `main` no puede ordenar efectos de importación.
- **Qué lo demuestra:** en la copia, parchear `dotenv.load_dotenv` para lanzar
  `RuntimeError("dotenv-before-gate")` y ejecutar `import scripts.abrir_caso` terminó en esa
  excepción, con traza `abrir_caso.py:32 → core/abrir_caso.py:12 → core/config.py:18`. Un test
  contractual debe importar el módulo en un proceso limpio con un spy de `load_dotenv` y exigir
  cero llamadas antes de una combinación V1 inválida; hoy falla.

### H6-02 — CRÍTICO — `--force` permite a V1 crear una sombra con W-code duplicado

- **Fichero:línea:** `objeto/head/scripts/abrir_caso.py:415,487-492,520-524` y
  `objeto/head/core/abrir_caso.py:101-111`.
- **Cita literal:** `force: bool = typer.Option(False, "--force")`,
  `force=force` y `if w_dup and not force:`.
- **Fuente contrariada:** la política canónica dice que un W-code existente entra por
  `--case-id` y que `--force` «nunca permite crear una sombra plana ni saltarse una discrepancia
  de referencia» (spec `:182-188`; criterio 33, `:959-961`).
- **Por qué es defecto:** `validar_modo` solo recibe `modo`, `crm` y `fuente` (`:357`); no ve
  `force`. Una invocación `--modo v1 --crm skip --fuente drive_ev --force` con un W-code ya
  presente evita `ColisionCaso`, construye un `case_id` distinto, llega a `ensure_case` y después
  al pull. Eso bifurca identidad y custodia precisamente donde V1 exige una identidad canónica
  única. La puerta central no rechaza un efecto expresamente prohibido por V1.
- **Qué lo demuestra:** el probe ejecutado en la copia creó un candidato previo
  `BaOLD - Anterior (W-DUP01) - Bad debt`, invocó V1 con el mismo W-code y `--force`, y obtuvo
  `exit_code == 0` más una llamada a `ensure_case` para `BaNEW ... (W-DUP01) ...`. Debe existir un
  test CLI negativo que espere salida 1 y cero llamadas a `ensure_case`, Drive e intake.

### H6-03 — ALTO — `--dry-run` pasa la puerta, muta y termina una secuencia que no puede ser V1

- **Fichero:línea:** `objeto/head/scripts/abrir_caso.py:110-114,416,520-536`.
- **Cita literal:** `intake_drive.pull_drive_ev(...)`, seguido solo después por el uso de
  `dry_run`; y `if dry_run: ... raise typer.Exit(code=0)` después de `ensure_case` e intake.
- **Fuente contrariada:** V1 es la secuencia identidad → esqueleto → Drive y Sudespacho → intake
  con custodia → atomización → sala de máquina (spec `:1286-1314`), y D3 atribuye al modo el orden
  completo (`:1690-1693`). El runbook afirma que estar en el modo «ES ser una ejecución V1»
  (`docs/RUNBOOK_APERTURA_EXPEDIENTE.md:127-132`).
- **Por qué es defecto:** `validar_modo` no recibe `dry_run`. Con `--dry-run`, el CLI crea el
  esqueleto, y para Drive hace el pull real antes de consultar `dry_run`; luego sale 0 antes del
  alta/log final y, cuando existan los planes posteriores, antes del resto del orden V1. Es una
  ejecución effectful e incompleta que el discriminante etiqueta como V1.
- **Qué lo demuestra:** el probe llamó `_intake_drive_ev(..., dry_run=True)` con un spy y verificó
  que `pull_drive_ev` fue llamado. Falta un test negativo de CLI que combine `--modo v1` y
  `--dry-run` y exija rechazo antes de `ensure_case`/Drive, o una fuente contractual que admita y
  defina expresamente esa semántica.

### H6-04 — ALTO — V1 admite `drive_ev` sin `--folder-id` y escribe antes de fracasar

- **Fichero:línea:** `objeto/head/scripts/abrir_caso.py:218-225,397,520-533` y
  `objeto/head/core/intake_drive.py:185-198,257-264`.
- **Cita literal:** para `drive_ev`, `_validar_flags` declara `"drive_ev": []`; después
  `target_dir.mkdir(parents=True, exist_ok=True)` precede a
  `"--drive-root-folder-id", folder_id`.
- **Fuente contrariada:** V1 incluye materializar Drive E&V (`spec:1299-1300`), mientras el
  preflight exige resolver antes de escribir y no inicializar ante lectura fallida o identidad no
  probada (`spec:150-180`).
- **Por qué es defecto:** `validar_modo` no recibe `folder_id`. Si el llamador aporta `--team-id`
  y los datos de identidad pero omite `--folder-id`, no se intenta autoderivación, la validación de
  fuente no exige ese dato, se alcanza `ensure_case` y el pull recibe `None`. El pull crea el
  destino local antes de construir un comando rclone con `None`. La ausencia de un dato necesario
  se detecta, si acaso, después de mutar.
- **Qué lo demuestra:** el probe V1 sin `--folder-id`, con `--team-id TID`, terminó en salida 0
  bajo spies y registró exactamente `ensure_case` seguido de `_intake_drive_ev(..., None, "TID")`.
  Un test real debe esperar salida 1 y cero llamadas/escrituras cuando falta `--folder-id`.

### H6-05 — BAJO — El callback eager de `--help` produce salida antes de validar una V1 inválida

- **Fichero:línea:** `objeto/head/scripts/abrir_caso.py:384,400-403,419-425`.
- **Cita literal:** `@app.command()` y `modo: str = typer.Option("libre", "--modo", ...)`; la
  llamada a `validar_modo` solo vive dentro de `main`.
- **Fuente contrariada:** el plan y el runbook dicen que V1 inválida se rechaza antes de cualquier
  efecto (`plan:5-7`; runbook `:127-132`).
- **Por qué es defecto:** Click/Typer procesa la ayuda eager antes de invocar `main`. Por tanto,
  la invocación que se presenta como V1 pero pide a la vez `--crm api --fuente email --help`
  imprime toda la ayuda y sale 0 sin evaluar la puerta. El efecto se limita a consola, por eso la
  severidad es baja, pero el absoluto y la cobertura de callbacks son falsos.
- **Qué lo demuestra:** `python -m scripts.abrir_caso --modo v1 --crm api --fuente email --help`
  produjo `exit=0`, ayuda completa y ningún `[ERROR] --modo v1`. Falta una decisión explícita sobre
  si los callbacks eager quedan fuera del contrato; hoy el documento no hace esa salvedad.

### H6-06 — MEDIO — El modo `libre` no conserva el comportamiento byte a byte

- **Fichero:línea:** `objeto/head/scripts/abrir_caso.py:400-403`.
- **Cita literal:** la nueva opción añade a la ayuda
  `libre|v1. ... [default: libre]`.
- **Fuente contrariada:** el plan exige «El modo `libre` conserva el comportamiento actual byte a
  byte» (`plan:7`) y repite que cualquier cambio es regresión (`plan:72`). El runbook dice
  «el comportamiento es el de siempre» (`runbook:131-132`).
- **Por qué es defecto:** una invocación preexistente que funcionaba, `--help`, conserva salida 0
  pero cambia su salida. En la comparación real, la ayuda pasó de 2.640 a 3.040 caracteres y añadió
  cinco líneas. Añadir un flag hace este cambio casi inevitable; precisamente por eso la promesa
  byte a byte es una condición falsa, no una garantía conseguida.
- **Qué lo demuestra:** comparar en memoria la salida de
  `python -m scripts.abrir_caso --help` sobre base y head dio `equal=False`, ambos exit 0. Un test
  golden base/head lo haría rojo; si la ayuda se declara excepción, la fuente debe decirlo.

### H6-07 — ALTO — El test de orden solo protege tres nombres y deja verde una puerta tardía

- **Fichero:línea:** `objeto/head/tests/test_abrir_caso_modo_v1.py:86-101`; caminos no cubiertos en
  `objeto/head/scripts/abrir_caso.py:327-339,441-469,487`.
- **Cita literal:** el arnés solo parchea `ensure_case`, `_despachar_intake` y `_alta_crm`, y luego
  afirma `list(casos_root.iterdir()) == []`.
- **Fuente contrariada:** el plan dice que el orden queda «demostrable» (`plan:80-82`) y la errata
  se atribuye haber contratado «antes de cualquier efecto» por mutación (`plan:29-33`). D3 incluye
  expresamente autoderivación y lecturas remotas (`spec:1682-1689`).
- **Por qué es defecto:** antes de esos tres nombres existen `get_drive_folder_info` y
  `get_shared_drive_name` (Drive remoto), resolución/lectura de `_caso.md` y `list_cases` (disco).
  El fixture suministra `team_id`, `codigo_caso` y `sufijo`, así que evita a propósito la rama
  remota. Además, la importación que lee `.env` ocurre al recoger el test. El test sí distingue
  llegar a los tres bombs —incluso si no queda rastro—, pero no distingue abortar después de
  cualquiera de los efectos anteriores.
- **Qué lo demuestra:** en una copia mutante se desplazó la puerta desde el inicio de `main` hasta
  después de resolución/autoderivación, pero aún antes de `ensure_case`: los **14 tests** del
  fichero siguieron verdes. Al moverla después de `ensure_case`, el test sí quedó rojo; el fallo
  mostró `<Result AssertionError('no debia llegar...')>`. Por tanto la errata describe con
  exactitud esa mutación concreta, pero se atribuye una propiedad más ancha que la mutación y el
  arnés no prueban. Faltan bombs separados para dotenv/import, autoderivación Drive, resolución de
  `--case-id` y listado local.

### H6-08 — MEDIO — `test_modo_libre_conserva_el_comportamiento` pasa con salida 1

- **Fichero:línea:** `objeto/head/tests/test_abrir_caso_modo_v1.py:122-133`.
- **Cita literal:** sus únicas aserciones son
  `assert "Modo desconocido" not in res.output` y
  `assert "--modo v1" not in res.output`.
- **Fuente contrariada:** el propio docstring promete «Sin `--modo`, nada cambia» (`:123`) y el
  plan exige equivalencia byte a byte (`plan:7,72`).
- **Por qué es defecto:** no comprueba `exit_code`, las llamadas esperadas, ni la salida previa.
  Cualquier fallo que no use esas dos frases pasa. Tampoco puede detectar el cambio real de ayuda
  de H6-06.
- **Qué lo demuestra:** un probe sustituyó `validar_modo` por una versión rota que devuelve
  `["BROKEN"]` en modo libre. El CLI salió 1 y las dos aserciones copiadas del test pasaron. El test
  debe comparar al menos exit, secuencia observable y salida contra base o contra un golden.

### H6-09 — ALTO — El runbook presenta como V1 ejecutable un modo que el propio plan dice que no corre V1

- **Fichero:línea:** `objeto/head/docs/RUNBOOK_APERTURA_EXPEDIENTE.md:127-132`; contradicción
  explícita en `objeto/head/docs/superpowers/plans/2026-08-24-apertura-v1-plan1-modo-v1.md:58-59,549-553`.
- **Cita literal:** el runbook dice «La primera vertical se ejecuta con» y «estar en él ES ser una
  ejecución V1»; el plan dice «Este plan no cablea nada. No hace que V1 corra» y que no llama al
  pull de Sudespacho, atomización ni sala de máquina.
- **Fuente contrariada:** D3 hace al modo dueño de Drive → Sudespacho → intake → atomización → sala
  y rondas (`spec:1673-1693`); §21 define ese mismo alcance (`spec:1286-1314`).
- **Por qué es defecto:** incluso con `crm=skip`, `fuente=drive_ev` y sin las banderas defectuosas
  anteriores, el código termina tras el antiguo `ensure_case → intake → _alta_crm(skip)`
  (`scripts/abrir_caso.py:520-540`). No contiene llamadas al pull de Sudespacho, atomización, sala,
  estado, workspace o mutex. El plan puede legítimamente entregar solo el discriminante; el
  runbook operativo no puede llamar a ese resultado «ejecutar V1» antes del Plan 5.
- **Qué lo demuestra:** un test de fases con spies para Drive, Sudespacho, atomización y sala debe
  exigir una llamada ordenada a cada una; hoy ni siquiera hay nombres que parchear en este módulo.
  Hasta ese cableado, el runbook debe poder distinguir «modo reservado/reconocible» de «secuencia
  V1 ejecutable».

## Cobertura de las preguntas del mandato

1. **Puerta antes de todo efecto:** no. Dentro del cuerpo de `main` es la primera sentencia y corta
   correctamente `crm`/`fuente`, pero `.env` se lee al importar (H6-01) y `--help` se resuelve por
   callback antes de `main` (H6-05).
2. **`libre` byte a byte:** no (H6-06). Los 70 tests preexistentes de `abrir_caso` pasan, por lo que
   no se demostró otra regresión ordinaria; la promesa absoluta cae ya con `--help`.
3. **Banderas de `main`:**
   - `--force`: defecto crítico en caso nuevo (H6-02).
   - `--dry-run`: aceptado, effectful e incompatible con ser una secuencia V1 completa (H6-03).
   - `--folder-id`: su ausencia no se valida y alcanza efectos (H6-04).
   - `--case-id`: sí pertenece a V1; el criterio 35 lo conserva (`spec:1410-1412`).
   - `--yes`: con `crm=skip` no alcanza el gate CRM; para código de equipo repetido está admitido
     expresamente (`spec:182-185`). No se halló un efecto V1 prohibido distinto de la vía
     `--force`.
   - `--extraer-adjuntos`: con la única fuente V1 (`drive_ev`) no se usa; no produce el efecto de
     email, aunque tampoco se rechaza como flag ajeno.
   - `--cuantia`: `_alta_crm` retorna en `skip` antes de construir payload (`scripts/abrir_caso.py:276-292`);
     no se halló efecto monetario en V1, aunque el flag irrelevante se acepta.
   - `--team-id`: es necesario o se deriva por Drive; el camino de derivación está después de la
     puerta del cuerpo, pero no lo cubre el test de orden.
4. **Tests:** la matriz pura de `crm`/`fuente` sí prueba sus reglas. El test de aborto protege los
   tres bombs, no todo efecto (H6-07), y el de libre puede pasar con implementación rota (H6-08).
5. **Arnés:** sí esconde caminos reales: importación, autoderivación Drive, resolución de caso y
   listado local no pasan por ninguno de los tres nombres parcheados (H6-01/H6-07).
6. **Documentación:** promete preefecto total, equivalencia libre y V1 ejecutable; las tres
   exceden el código (H6-01, H6-05, H6-06 y H6-09).
7. **Erratas:**
   - La sustitución de `assert default or True` por inspección del default es real y puede fallar si
     cambia `api` a `skip` (`tests/test_abrir_caso_modo_v1.py:41-50`).
   - `honorarios` sí produce `ValueError: Tipo de caso desconocido`; se reprodujo, y el fixture
     actual usa `BAD_DEBT` (`:77-83`).
   - La aritmética correcta es 11 tras Task 3 y 14 al final; pytest recoge 14.
   - La mutación bajo `ensure_case` sí deja el test rojo y muestra el `AssertionError`; lo que no es
     exacto es atribuirle prueba de *cualquier* efecto (H6-07). **SIN VERIFICAR:** que el ejecutor
     histórico hiciera literalmente `git checkout` después de su ensayo; el objeto no contiene
     `.git` ni bitácora de esa acción. El resultado técnico declarado sí se reprodujo en scratch.
8. **Pruebas negativas ausentes:** `--force` con W-code duplicado, V1 + `--dry-run`, falta de
   `--folder-id`, importación con spy de dotenv, callback eager y mutación de la puerta detrás de
   autoderivación/resolución. Un lector del bloque añadido al runbook también puede reutilizar el
   `--force` del comando inmediatamente anterior (`runbook:121-145`) y creer que sigue en V1.

## Ejecuciones de verificación

- Suite focal en head: **84/84 pasan**
  (`tests/test_abrir_caso_modo_v1.py`, `tests/test_abrir_caso.py`,
  `tests/test_abrir_caso_cli.py`).
- Suite completa sobre copia, con alias de ruta corta apuntando físicamente al workdir:
  **2.809 passed, 77 skipped, 7 xfailed, 0 failed**; 2.893 tests recogidos. La primera corrida con
  ruta larga tuvo un fallo de presupuesto de ruta en `test_resumen_cuenta_por_estado`; el mismo
  test falló igual en base y head y desapareció al cumplir el `--basetemp` corto que exige el plan.
- Probes adversariales: **4/4 pasan**, demostrando `--force`, falta de `folder_id`, pull bajo
  `dry_run` y vacuidad del test libre.
- Mutación «puerta tras identidad/autoderivación»: **14/14 pasan** (mutante sobreviviente).
- Mutación «puerta tras `ensure_case`»: el test de aborto falla, como afirma parcialmente la
  errata.
- Comparación base/head de `--help`: exit 0 en ambos, salida distinta (2.640 frente a 3.040
  caracteres).

## Recuento y veredicto

- CRÍTICO: 1
- ALTO: 5
- MEDIO: 2
- BAJO: 1

La afirmación central no queda contratada: hay efectos anteriores a la puerta, combinaciones V1
admitidas que violan identidad o preflight y tests que no matan una puerta desplazada detrás de
lecturas. El runbook, además, llama ejecución V1 a una secuencia que el plan declara no cableada.

**Veredicto final: NO-SHIP**
<!-- informe-literal:fin:q7vx -->

## 2. Evidencia verificada al adjudicar (Claude Code, 2026-08-24)

**No-mutación del objeto, comprobada por el adjudicador y no solo declarada por el revisor.** Los
tres SHA-256 canónicos recalculados de forma independiente coinciden con los de apertura:
`objeto/base` = `abfd8e44…2138c`, `objeto/head` = `a4b0c08f…106a14`, `objeto/DIFF.patch` =
`a2825f8e…f109e`. La copia externa hizo su trabajo.

**Reproducciones propias, contra el árbol real del repo y no contra el informe.** Regla de la casa:
un hallazgo se confirma o se refuta contra la fuente, no contra la seguridad con que venga
redactado — y menos aún contra un probe que corrió en el arnés del revisor.

| Hallazgo | Cómo lo reproduje | Resultado |
|---|---|---|
| H6-02 | probe con `W-DUP01` ya presente + `--modo v1 --crm skip --fuente drive_ev --force` | `exit 0` y `ensure_case('BaNEW - Calle Nueva 2 (W-DUP01) - Bad debt')`: **la carpeta sombra existe** |
| H6-07 | mutante «puerta bajo identidad + autoderivación de Drive, aún sobre `ensure_case`» | **14/14 verdes: el mutante sobrevive** |
| H6-08 | `validar_modo` sustituida por `return ["BROKEN"]` | `test_modo_libre_conserva_el_comportamiento` **pasa** con el CLI saliendo 1 |
| H6-03 | lectura de `_intake_drive_ev` (`scripts/abrir_caso.py`) | `pull_drive_ev(...)` se llama **antes** de que `dry_run` se consulte |
| H6-04 | lectura de `_validar_flags` y de `pull_drive_ev` | `"drive_ev": []` en requeridos; `target_dir.mkdir(...)` **precede** al `cmd` con `folder_id` |
| H6-01 | `core/config.py:16-18` | `load_dotenv(...)` a nivel de módulo: se ejecuta al importar, en base y en head |
| H6-05 | `python -m scripts.abrir_caso --modo v1 --crm api --fuente email --help` | `exit 0`, ayuda completa, sin `[ERROR]` |

**Anclaje normativo que decidió las severidades.** El criterio **33** del §14 —«`--force` nunca
crea una carpeta sombra»— está **dentro de los veinticuatro de V1** que enumera el §21.4, y la
política de colisión del §preflight dice que `--force` «solo puede reutilizar el mismo caso
canónico ya resuelto por `--case-id`». Eso es lo que convierte H6-02 en CRÍTICO y no en una
interpretación amplia del revisor.

**Un hueco que encontré yo y el revisor no.** El §21.4, al precisar el criterio 34, exige un
criterio negativo con **un spy que acredite cero llamadas remotas de alta, ficha o relaciones**.
Mis tests parcheaban `_alta_crm` entero, que es más grueso que el contrato: si mañana la llamada
remota se moviera fuera de esa función, el test seguiría verde. Se añade
`test_v1_cero_llamadas_remotas_de_alta`, con el spy sobre
`sudespacho_create.create_expediente`, que es la escritura real.

**Lo que sigue SIN VERIFICAR, dicho como corresponde.** El revisor marcó SIN VERIFICAR que yo
hubiera hecho literalmente `git checkout` tras mi ensayo de mutación, porque el objeto no lleva
`.git`. No lo declaró refutado, y hace bien: no es verificable desde la copia. Lo que sí consta es
que el árbol quedó limpio y la suite verde.
