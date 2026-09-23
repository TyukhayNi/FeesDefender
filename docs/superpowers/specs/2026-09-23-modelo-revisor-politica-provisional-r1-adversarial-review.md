---
tipo: revision-adversarial
objeto: diff b3da01d..b07dac6 (CLAUDE.md, AGENTS.md, PLAN.md, docs/INDICE.md, docs/MEJORAS_FUTURAS.md, docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md)
objeto_rev: "1"
commit: b07dac6
ronda: "1"
revisor: Codex
modelo: gpt-6-sol
esfuerzo: high
velocidad: default
veredicto: REQUIERE-REVISION
marcador_nonce: kzqw
sha256_informe: fd9ee4aa335a2df08bd3fe1625b6eb985674443def36558106275a6a3773dec8
adjudicado_en: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §15
---

# Acta — R1 adversarial sobre el diff de la política de modelo del revisor

Objeto: el **diff** `b3da01d..b07dac6` de la rama `claude/adversarial-review-governance-205d5d`,
que adopta la política provisional de con qué modelo corre la revisión adversarial. Es un diff que
**modifica el propio contrato de revisión**, que no está exento nunca, y por eso esta ronda no es
opcional ni podía cubrirla un revisor sustituto.

## Con qué corrió, y qué está acreditado de eso

`gpt-6-sol` con esfuerzo `high`, releídos del `turn_context` de
`rollout-2026-09-23T13-41-*-01a0ce13-62bb-7100-9213-4de52625973e.jsonl` y coincidentes con la
cabecera del `_stdout.log`. La **velocidad** (`service_tier="default"`) se **afirma** desde la línea
de órdenes del lanzamiento: no consta en el rollout ni en la cabecera, tal como declara el §4.
117.071 tokens. Es la **primera aplicación real** de la política que el propio diff introduce.

**No cuenta como fila de la calibración** (fila #38 de `PLAN.md`): un texto normativo no es un
objeto representativo de un encargo ordinario.

## Cadena de custodia

- Informe recibido en `C:	ev-modelo-revisor-133442\informe\INFORME.md`.
- `sha256` **declarado por el revisor**: `fd9ee4aa335a2df08bd3fe1625b6eb985674443def36558106275a6a3773dec8`.
- `sha256` **recomputado al recibir**, sobre el fichero crudo y sobre el bloque canonicalizado
  (UTF-8, `LF`, un solo salto final): **el mismo número en los tres casos**. El fichero venía en LF
  con un único salto final, así que crudo y canónico coinciden.
- **No-mutación del objeto:** el revisor declaró el `sha256` de `diff.patch` al abrir y al cerrar,
  `d452ff28…9bd3`, y coincide con el que este lado calculó antes de lanzar. Las copias no llevan
  `.git`, así que **no acredita genealogía** —lo dijo él mismo—: prueba contenido, no que `base/` y
  `head/` sean esos commits.
- **Higiene declarada por el revisor en su primera línea:** encontró `informe/_stdout.log` y no lo
  leyó. Los directorios `pytest_tmp` y `pytest_tmp_g789` los creó al correr los guards, dentro de su
  directorio de trabajo, y declaró que el borrado recursivo se lo rechazó su propio control.

## 0. Mandato, literal

<!-- mandato-literal:inicio:kzqw -->
# Revisión adversarial — R1 sobre el diff que cambia el contrato de revisión (FeesDefender)

Eres el revisor adversarial. Trabajas en **solo lectura** sobre el objeto que tienes en este
directorio. **No escribes en ningún repositorio**: lo que necesites ejecutar va sobre las copias
que ya están aquí, y tu salida es un único fichero, `INFORME.md`, en tu directorio de trabajo.

## §0-bis. Por qué este mandato está redactado así

Se te pide **auditar la completitud y la exactitud de un texto normativo**, no eludir un control ni
demostrar una evasión. Si alguna pregunta te suena a otra cosa, interprétala como auditoría y dilo.

**Dónde está cada cosa.** Tu **directorio de trabajo** es `C:	
ev-modelo-revisor-133442\informe`
y es lo único que puedes escribir; al empezar está **vacío**. El **objeto** vive en el directorio
**padre**, `C:	
ev-modelo-revisor-133442\`, que es de **solo lectura** por construcción: ahí
están `MANDATO.md`, `base/`, `head/`, `diff.patch`, `INFORME_FUENTE.md` y `sondas/`. Escribe
`INFORME.md` en tu directorio de trabajo, no en el padre.

**Higiene:** si encuentras en tu directorio de trabajo cualquier fichero que no hayas escrito tú, o
en el padre alguno que no esté en la lista de arriba, **no lo leas** y decláralo en la primera línea
de tu informe.

**Prueba de no-mutación:** calcula el `sha256` de `diff.patch` al abrir y al cerrar, y declara los
dos. Sustituye al `git status` —las copias no traen `.git`—, y por eso mismo **no puedes acreditar
la genealogía** de `base/`/`head/`: verificas contenido, no que sean esos commits. Dilo así.

## Objeto

Un diff **solo de documentación** del repo FeesDefender, anclado a commits:

- **base:** `b3da01d3f02d075b34930f4e2713a8853bcedb3d` (rama `main`)
- **head:** `b07dac6ca52ddc987202e1ad86cb2c34d32c9223` (rama `claude/adversarial-review-governance-205d5d`)
- `base/` y `head/` son las copias extraídas de esos dos commits; `diff.patch` es el diff entre
  ellos. **Nota de forma:** `git archive` extrae en CRLF y el repo vivo tiene LF, así que los
  `sha256` de un fichero de `base/`/`head/` **no coinciden** con los de `git show`. No es mutación.

Ficheros tocados: `CLAUDE.md`, `AGENTS.md`, `PLAN.md`, `docs/INDICE.md`,
`docs/MEJORAS_FUTURAS.md` y
`docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`.

**Qué hace el diff:** adopta una **política provisional de con qué modelo corre la revisión
adversarial** (`gpt-6-sol`·`high` habitual, `gpt-6-sol`·`medium` para comprobar correcciones,
`gpt-6-astra`·`medium`/`high` para fronteras de daño), fija que el modelo va **explícito en la
invocación** y no heredado, añade tres campos al frontmatter del acta (`modelo`, `esfuerzo`,
`velocidad`) y abre una **calibración de cinco encargos** en `PLAN.md`.

**Este diff modifica el propio contrato de revisión**, que por regla de la casa no está exento
nunca. De ahí esta ronda.

## Materiales

- `..\INFORME_FUENTE.md` — el informe de consumo del 2026-09-23 sobre el que se decidió la política.
  **Es la fuente de las cifras que el diff cita.** Contrástalas contra él, una a una.
- `..\sondas\` — logs literales de las sondas que se corrieron el 2026-09-23 contra la CLI de Codex, y
  el extracto de `turn_context` de los rollouts de ese día. Son la evidencia de las afirmaciones
  sobre lanzadores, binarios y `service_tier`.
- `..\head	ests	est_docs_gobernanza.py` — los guards G7/G8/G9 que comprueban actas y adjudicaciones.
  Puedes correrlos: el Python de sistema
  (`C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`) trae `pytest` y `yaml`. Usa
  `--basetemp` **dentro de tu directorio de trabajo** (el objeto no es escribible), `-p no:cacheprovider` y
  `PYTHONDONTWRITEBYTECODE=1`. No tiene `pytest-randomly` ni `pytest-xdist`: si algo no corre por
  eso, decláralo **SIN VERIFICAR**, no lo deduzcas.

## Los seis puntos, ordenados por daño

**1. La política es inejecutable, o se ejecuta distinto de lo que dice.** `head/CLAUDE.md`
§«Con qué modelo se revisa» manda lanzar con
`-m gpt-6-sol -c model_reasoning_effort="high" -c service_tier="default"`. Dictamina, contra
`sondas/` y contra el propio texto: ¿es `"default"` lo que hay que poner para obtener **velocidad
estándar**, o solo lo que la CLI acepta sin avisar? ¿Queda claro que `"standard"` no existe y que
falla **hacia delante**? ¿La afirmación sobre el binario npm está bien acotada —es la **versión**,
es la **cuenta**, o el texto atribuye a una lo que prueba de la otra? Un texto que mande una
invocación que no produzca el modelo que promete es el fallo más caro de este diff, porque no falla:
corre.

**2. Una garantía se ha debilitado sin que nadie lo quisiera.** El diff afirma que **no cambia**:
independencia del revisor, repo en solo lectura, pruebas sobre copias, informe externo con
`sha256`, adjudicación de Claude contra la fuente, cobertura **AUSENTE** si la ronda no termina, la
tabla de rondas y el techo de dos con autorización expresa de Nikolai. **Recorre esa lista contra
`head/AGENTS.md` y contra el §2–§6 del contrato** y di si alguna quedó fuera, dicha más débil, o
contradicha en otro punto del diff. Enumera también lo que la lista **no** menciona y sí está en el
contrato: un inventario incompleto presentado como completo es el defecto, no la omisión en sí.

**3. La regla que enlaza rondas y modelo, ¿es verdadera?** El diff dice: «una pieza de la fila de
**2 rondas** es, por construcción, una pieza de Astra; al revés no». Compruébalo contra la tabla de
rondas real de `head/CLAUDE.md` y contra las cuatro filas de modelo. ¿Hay alguna pieza de 2 rondas
que no caiga en ninguna fila de Astra? ¿Y el caso que este mismo diff es —el **contrato de
revisión**, que nunca está exento pero no aparece en ninguna fila de Astra— queda gobernado o queda
huérfano?

**4. La calibración no puede medir lo que dice medir.** Fila #38 de `head/PLAN.md` y su bloque
`[SIGUIENTE-MODELO-REVISOR]`. Ataca el diseño de la medición: ¿es rellenable la columna «omisiones
relevantes», o solo se rellena cuando ya es tarde? ¿«Δcupo con la concurrencia declarada» atribuye
algo, o es un número que no se puede leer? ¿La definición de «encargo ordinario» excluye
precisamente los casos donde Sol fallaría, y por tanto la calibración está sesgada a confirmar?
¿Cinco es un número que decide algo, o un ritual? Di qué conclusión **no** podrá sostenerse con ese
ledger aunque se rellene entero.

**5. El contrato del acta, rev. 11.** En
`head/docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`: los tres
campos nuevos del §4 y la regla del §5 («la ficha no los repite; solo si el informe no se capturó
van en `Revisor:`»). ¿Rompen o dejan ciego algún guard —corre G7/G8/G9 sobre `head/`—? ¿Hay un caso
sin hogar: ronda con acta pero sin adjudicación, adjudicación sin acta, acta de revisor sustituto?
¿La distinción entre los dos campos **releídos** y el **afirmado** está dicha donde la va a leer
quien rellena el acta, o solo donde la lee quien la diseña? ¿Y la decisión de **no** añadir guard
está bien argumentada, o es una racionalización de no hacerlo?

**6. Cifras y atribuciones.** Cada número del diff contra `INFORME_FUENTE.md` y `sondas/`: 60
revisiones sustantivas, 94,5 %, 0 %→100 % en dos días, 21/09 12:06 → 23/09 12:08, «una quinta parte»
de tarifa, seis rondas ese día, 8.316 tokens de la sonda, versiones `0.154.0` y `0.155.0-alpha.9.2`.
Marca las que el material **no** sostenga, las que lo sostengan con otro alcance, y las que el diff
presente como medidas siendo deducidas.

## Qué te pido de vuelta

- Contesta **punto por punto**, en una sección por punto, en este orden.
- Numera los hallazgos `H-NN`, cada uno con: **evidencia anclada a fichero y línea**, **severidad**
  (`alta` · `media` · `baja`) y **coste del remedio** que propones (`trivial` = una línea o un
  literal · `acotado` = una sección y su comprobación · `estructural` = cambia una frontera, un
  contrato o un formato que otros leen). Si el remedio que ves es estructural, dilo aunque el
  defecto sea pequeño.
- Una sección **`## Lo que intenté refutar y NO pude`**, con el ataque descrito. Un «aquí no
  encuentro nada» con el ataque detrás vale; sin él, no.
- **Volver limpio es un resultado legítimo.** Si has atacado el objeto y nada impide mergearlo,
  dilo. No se espera de ti un número mínimo de hallazgos y no hay lectura desfavorable de un
  informe corto.
- **Si el objeto te desborda al esfuerzo con el que estás corriendo, dilo y di en qué punto.** Es
  información útil, no una falta.
- **Veredicto en la última línea**, exactamente una palabra del conjunto cerrado:
  `SHIP` · `LISTA-CON-CAMBIOS` · `REQUIERE-REVISION` · `NO-SHIP` · `NO-EJECUTABLE` · `SIN-VEREDICTO`.
- Al terminar, imprime la **ruta** y el **`sha256`** de `INFORME.md` (UTF-8, finales `LF`, un único
  salto final).
<!-- mandato-literal:fin:kzqw -->

## 1. Informe recibido, sin modificar (Codex, gpt-6-sol · high)

<!-- informe-literal:inicio:kzqw -->
Higiene: encontré `informe/_stdout.log` antes de trabajar; no lo leí. En el padre no encontré entradas ajenas a la lista autorizada. Los directorios `pytest_tmp` y `pytest_tmp_g789` los creó esta revisión al ejecutar los guards; permanecen porque la eliminación recursiva fue rechazada por el control automático.

# Revisión adversarial R1 — política de modelo del revisor

**Alcance.** He contrastado `base/`, `head/`, `diff.patch`, `INFORME_FUENTE.md` y las seis sondas autorizadas. Las copias carecen de `.git`: compruebo contenido, **no puedo acreditar su genealogía** ni que procedan de los commits declarados. `diff.patch` tenía al abrir SHA-256 `D452FF280A1DADB0D3D2ECA4C16159879E4976A0CC1C58D12826B01C189B9BD3`; al cerrar se declara de nuevo abajo. No he ejecutado las CLI históricas ni he leído `_stdout.log`.

## 1. Ejecutabilidad de la política

**H-01 — `default` no está demostrado como velocidad estándar. Severidad: media. Coste: acotado.** `head/CLAUDE.md:119,150-179` ordena velocidad estándar y prescribe `-c service_tier="default"`. `sondas/05_service_tier_default.log:1-19` demuestra que **esa invocación termina sin aviso**; `sondas/05_service_tier_standard.log:15-20` demuestra que `standard` se omite con aviso y la ejecución continúa. Ninguno muestra el tier efectivo ni la petición enviada. El aviso dice «no anunciado como compatible **para `gpt-6-sol`**», alcance menor que «`standard` NO existe» (`head/CLAUDE.md:170`). Es defendible usar `default` como literal operativo observado, pero no afirmar que esta sonda acredita Standard efectivo. **Remedio:** acotar «no existe» a Sol en esta CLI, llamar a `default` «aceptado sin aviso» y distinguir expresamente esa comprobación de una medición de velocidad efectiva; si se quiere prometer Standard, aportar una fuente o sonda que lo pruebe. El fallo de `standard` es **hacia delante**, como dice el diff: avisa y sigue.

**H-02 — la causa atribuida al binario excede la comparación hecha. Severidad: baja. Coste: trivial.** `head/CLAUDE.md:164-169` dice «el binario decide si Sol existe»; `sondas/01_npm-0.154.0_gpt-6-sol_RECHAZADO.log:2,15-18` muestra el 400 de cuenta ChatGPT en v0.154.0 y `sondas/02_app-0.155.0-alpha.9.2_gpt-6-sol_VIVO.log:2,15-18` muestra `VIVO` y 8.316 tokens en v0.155.0-alpha.9.2. `sondas/03_lanzador_en_uso_2026-09-23.ps1:8-10,24-27` sí identifica `codex.cmd` como el lanzador observado. Las sondas cambian **instalación y versión** a la vez; no aíslan si la causa es la versión, la ruta, metadatos del cliente o una condición de la cuenta. El error menciona el tipo de cuenta, pero el éxito posterior impide concluir que esa cuenta sea incompatible con Sol en general. **Remedio:** decir «en estas dos sondas, el npm 0.154.0 rechazó y el de la app 0.155.0-alpha.9.2 corrió; verificar con el binario elegido», sin causalidad más fuerte.

## 2. Garantías que se declaran intactas

**No encuentro debilitamiento directo** de los siete elementos enumerados en `head/CLAUDE.md:142-148`: independencia, repo en solo lectura y pruebas en copias, informe externo con hash, adjudicación de Claude contra fuente, cobertura AUSENTE si no termina, tabla de rondas y autorización expresa de Nikolai para una tercera. `head/AGENTS.md:49-65,93-100` y `head/CLAUDE.md:70-111` los mantienen. La exigencia nueva de que el autor relea modelo y esfuerzo (`head/AGENTS.md:78-84`) refuerza, en vez de trasladar al revisor, la prueba de identidad.

**H-03 — «lo que NO cambia» se presenta como inventario completo sin serlo. Severidad: baja. Coste: acotado.** `head/CLAUDE.md:142-148` lo llama «la mitad que importa», pero el mismo contrato conserva además el **vigía armado antes de lanzar, que distingue fin y muerte** (`head/CLAUDE.md:29-39`; contrato `head/docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md:202-231`), el **mandato numerado y anclado a commit**, hallazgos con dos ejes y posibilidad de volver `SHIP` (`head/AGENTS.md:66-92`), la **voz literal en acta separada de la adjudicación**, con nonce y digest (`head/CLAUDE.md:40-49`; contrato `:67-77,175-190`), y las condiciones y límites del **revisor sustituto** (`head/AGENTS.md:102-124`). No veo que el diff suprima esas reglas; el defecto es insinuar que la lista nueva agota las garantías invariantes. **Remedio:** llamarla «resumen no exhaustivo» y remitir expresamente a esos apartados, o completar el inventario.

## 3. Enlace entre rondas y modelo

La implicación «2 rondas ⇒ Astra» resiste este ataque: la fila de 2 rondas de `head/CLAUDE.md:75-79` cubre decisiones sobre quién puede escribir y destrucción o corrupción de datos de cliente; las filas Astra de `:132-133` cubren permisos, escritura sobre datos de cliente y, según el mecanismo, concurrencia/estados parciales. No encuentro una pieza de esa fila de 2 que necesariamente caiga fuera de ambas filas Astra. La implicación inversa falla correctamente: un diff con concurrencia puede ir a Astra y seguir siendo de una ronda.

**H-04 — el propio contrato de revisión carece de asignación inequívoca de modelo. Severidad: media. Coste: estructural.** `head/CLAUDE.md:78-85` exime los cambios de documentación salvo, entre otros, **el propio contrato de revisión**; por ello este diff pide una ronda. Las cuatro filas de `head/CLAUDE.md:128-140` no nombran cambios del contrato: las filas Astra son de permisos/datos/envíos y concurrencia, mientras que la fila Sol exige un objeto «acotado». Un cambio de gobernanza puede afectar a todas las revisiones sin tocar esas fronteras técnicas; queda a una apreciación tácita si es «acotado» o si se eleva a Astra por «incertidumbre». **Remedio:** fijar en la tabla o en una regla de precedencia la ruta de revisión del propio contrato y de cambios de política de revisión, incluido el esfuerzo; esto modifica la frontera normativa, aunque ocupe una línea.

## 4. Capacidad probatoria de la calibración

**H-05 — las cinco filas no pueden sostener equivalencia de calidad ni validar la regla de enrutamiento. Severidad: media. Coste: estructural.** `head/PLAN.md:3493-3509` toma solo encargos ordinarios de una ronda y excluye fronteras de escritura, datos de cliente y concurrencia. `head/CLAUDE.md:187-193` propone reusar objetos con defectos confirmados, pero no fija pares comparables Sol/Astra, denominador de defectos conocidos, ventana de seguimiento, umbral de aceptación ni regla que haga decisivo el quinto caso. `head/PLAN.md:3522-3524` reconoce que «omisiones relevantes» solo se rellena si otra ronda, la suite o producción descubre después el defecto; una casilla vacía no es evidencia de ausencia. Así, cinco filas completas pueden describir hallazgos conocidos y algunos fallos tardíos, pero **no permiten concluir que Sol encuentre lo mismo que Astra, que su tasa de omisiones relevantes sea aceptable, ni que las filas críticas estén bien reservadas**. La política admite provisionalidad (`head/CLAUDE.md:121-126,195-200`), pero `head/PLAN.md:3493-3496` promete decidir «confirmar, ajustar o volver» justo al quinto sin definir con qué prueba. **Remedio:** separar un ledger operativo de consumo de una prueba de calidad; para esta última, fijar antes objetos ciegos con defectos adjudicados, comparación o patrón de referencia, seguimiento y criterio de decisión. Mantener provisional la conclusión que esos datos no puedan sostener.

**H-06 — Δcupo no atribuye consumo a la ronda aunque se declare concurrencia. Severidad: baja. Coste: acotado.** `head/PLAN.md:3503,3517-3519` dice que el contador es de la cuenta; `INFORME_FUENTE.md:32-41` confirma que las muestras del cupo compartido no se pueden atribuir a una tarea con actividad simultánea. Anotar nombres de tareas concurrentes permite interpretar el dato, pero no descontar su parte ni estimar ahorro causado por cambiar modelo. **Remedio:** etiquetar Δcupo como cambio observado de cuenta, registrar hora de inicio/fin y actividad concurrente, y evitar usarlo como coste causal por encargo. La tarifa «una quinta parte» es una relación condicional de créditos, no una predicción de cupo.

## 5. Acta rev. 11 y guards

Ejecuté G7/G8/G9 de `head/tests/test_docs_gobernanza.py` con `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider` y `--basetemp` dentro de `informe/`: **31 passed, 15 deselected**. Esto comprueba que el corpus actual satisface los guards seleccionados; no acredita los campos nuevos. La distinción entre `modelo`/`esfuerzo` **releídos** y `velocidad` **afirmada** sí está junto a la plantilla que rellena el autor (`head/docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md:115-162`) y también en `head/PLAN.md:3511-3516`.

**H-07 — «ningún guard» es una elección defendible solo para la verdad del dato, no para su presencia. Severidad: baja. Coste: acotado.** El contrato `head/docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md:159-162` razona que un guard local no puede verificar el rollout externo; es cierto. Pero `head/tests/test_docs_gobernanza.py:397-398,793-800` no incluye `modelo`, `esfuerzo` ni `velocidad` entre claves obligatorias, y G9 solo contrasta veredicto (`:939-965`). Una acta nueva sin cualquiera de los tres seguiría verde. La frase «presencia enseñaría a rellenarlo, no a releerlo» descarta un control útil por no resolver por sí solo toda la verdad del campo. **Remedio:** si los campos son obligatorios, comprobar presencia y vocabulario en G8 para nuevas actas, manteniendo explícita la verificación humana contra rollout y script. No atribuir al guard prueba de ejecución real.

**H-08 — el acta del revisor sustituto no tiene método de lectura definido. Severidad: media. Coste: estructural.** `head/AGENTS.md:102-124` permite una sesión independiente de Claude Code cuando Codex no puede correr, salvo para revisar el propio contrato. El §4 rev. 11 ordena releer `modelo` y `esfuerzo` del `turn_context` de un `rollout-*.jsonl` y de `_stdout.log` (`head/docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md:139-155`), artefactos descritos para Codex. No fija fuente equivalente para Claude Code ni valor explícito si alguno no se puede comprobar. La excepción del §5 solo trata **informe no capturado** (`:259-264`), no un informe capturado por sustituto. **Remedio:** definir procedencia y valores permitidos para el sustituto en el mismo contrato, conservando `revisor: Claude Code (sesión independiente)` y la independencia más débil; no inventar un rollout de Codex.

**H-09 — el enlace acta/adjudicación tiene una ceguera heredada que rev. 11 deja sin resolver. Severidad: baja. Coste: estructural.** Con acta y nonce, G8 exige que `adjudicado_en` apunte a un fichero y a una sección existentes (`head/tests/test_docs_gobernanza.py:810-823`), pero no que esa sección contenga la adjudicación de **esa ronda**. G7 valida adjudicaciones que encuentre, sin exigir que exista una para cada acta (`:519-559`; contrato `head/docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md:318-321`). Por tanto, un acta que señale una sección cualquiera puede pasar sin adjudicación; en sentido inverso, el §5 permite `Informe recibido: no capturado` y ficha sin acta (`:249-266`), que sí tiene hogar y debe quedar como cobertura no capturada. No es una regresión creada por los tres campos, sino un límite relevante al juzgar qué prueban estos guards. **Remedio:** si se quiere cerrar esa frontera, ligar identidad de ronda, acta y encabezado de adjudicación con un predicado nuevo; eso cambia el contrato y el recorte declarado, por eso el coste es estructural.

## 6. Cifras y atribuciones

**H-10 — seis rondas «lanzadas por esos scripts» no quedan individualmente acreditadas. Severidad: baja. Coste: trivial.** `head/CLAUDE.md:152-156` y `head/docs/MEJORAS_FUTURAS.md:12641-12647` atribuyen las seis rondas a los lanzadores sin flags. `sondas/04_turn_context_2026-09-23.md:15-20` lista seis rollouts `gpt-6-astra`/`xhigh`, pero su propia nota `:8-9` los llama anteriores a 12:15 aunque el sexto comienza a **12:15:03**. `sondas/03_lanzador_en_uso_2026-09-23.ps1:26-27` muestra **un** lanzador sin flags, no el vínculo individual de los seis rollouts con todos los `_lanzar_codex_rama_*.ps1`. **Remedio:** decir «seis rollouts listados con Astra/xhigh; el lanzador conservado no pasa flags» y reservar la atribución a los seis lanzamientos para cuando consten las seis líneas de comando o sus logs.

**H-11 — el 94,5 % y las 60 revisiones se comprimen en una frase que puede cambiar su denominador. Severidad: baja. Coste: trivial.** `head/CLAUDE.md:122-125` yuxtapone «60 revisiones sustantivas, todas con Astra —el 94,5 % de los tokens registrados». `INFORME_FUENTE.md:13,17-28` precisa que las 60 incluyen intentos interrumpidos y que 94,5 % es la proporción de **todos los tokens de las 88 sesiones** atribuida a Astra, incluidas sondas y subagentes; no es la cuota de tokens de esas 60 revisiones. **Remedio:** separar las dos métricas y explicitar ambos alcances.

Las demás cifras pedidas sí casan con su fuente y alcance: 0 % el 21/09 12:06 y 100 % el 23/09 12:08 son **muestras de cuenta**, no gasto imputable a estas rondas (`INFORME_FUENTE.md:32-41`); «una quinta parte» resulta de las tres tarifas 250:50, 25:5 y 1.250:250 **a igual mezcla de tokens**, deducción aritmética, no medición de ahorro (`:76-85`); 8.316 tokens y las versiones 0.154.0/0.155.0-alpha.9.2 figuran literalmente en `sondas/01...:2`, `sondas/02...:2,17-18`. La relación temporal entre las dos muestras de cupo es de unas 48 horas y dos minutos: «en dos días» es un redondeo razonable.

## Lo que intenté refutar y NO pude

- Ataqué la implicación 2 rondas ⇒ Astra con las fronteras exactas de `head/CLAUDE.md:77,132-133`; no encontré contraejemplo obligado. Mi objeción es la clasificación del contrato mismo, no esa implicación.
- Busqué en §4 si los campos nuevos confundían prueba con declaración; `head/docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md:125-127,147-155` sí lo distingue a la vista de quien rellena el acta.
- Contrasté las cifras de cupo y tarifa contra `INFORME_FUENTE.md:32-41,76-85`; el texto no promete ahorro real ni equivalencia de calidad (`head/CLAUDE.md:195-200`).
- Corrí los guards pertinentes y no obtuve fallo del corpus actual: 31 pasaron. Su verde no refuta las cegueras descritas.

**Cierre de integridad.** SHA-256 de `diff.patch` al abrir: `D452FF280A1DADB0D3D2ECA4C16159879E4976A0CC1C58D12826B01C189B9BD3`. SHA-256 al cerrar: `D452FF280A1DADB0D3D2ECA4C16159879E4976A0CC1C58D12826B01C189B9BD3`. La revisión se pudo completar al esfuerzo disponible; no declaro puntos desbordados.

REQUIERE-REVISION
<!-- informe-literal:fin:kzqw -->

## 2. Evidencia verificada al adjudicar

Cada hallazgo se contrastó contra la fuente, no contra el informe. Lo que cambió una afirmación del
diff:

- **H-10, y salió peor de lo que el revisor pudo ver.** Él señaló que la atribución de «seis
  rondas» a los lanzadores no estaba acreditada individualmente, y que la nota de
  `sondas/04` decía «anteriores a las 12:15» con el sexto empezando a las **12:15:03**. Al
  releer los `session_meta` —dato que mi fichero de evidencia **no le di**— aparece más: de los
  seis rollouts, **cinco** son `originator: codex_exec` con `cwd` en `Dev\_revisiones_codex`, y el
  sexto (12:11:25) es `codex_work_desktop` con `cwd` en `Documents\Codex6-09-23\est` — **la
  sesión que escribió el informe de consumo sobre el que se decidió todo esto**. No era una ronda.
  Corregido a **cinco lanzamientos por CLI**, y dicho que son lanzamientos y no necesariamente
  rondas distintas (dos arrancan con siete segundos de diferencia). De paso el sexto prueba algo
  que el diff no decía: **la app hereda el mismo defecto** que la CLI.
- **H-11.** `INFORME_FUENTE.md:13,17-28` confirma las dos cosas: las 60 revisiones **incluyen
  intentos interrumpidos**, y el 94,5 % es la cuota de Astra sobre **las 88 sesiones**, sondas y
  subagentes incluidos — no sobre esas 60. El diff las había yuxtapuesto en una frase.
- **H-01.** El aviso literal de `sondas/05_service_tier_standard.log` dice `for model 'gpt-6-sol'`:
  mi «`standard` NO existe» medía en un sitio y afirmaba de otro. Y ninguna de las dos sondas
  enseña el tier efectivo, así que `default` es **el literal aceptado sin aviso**, no «Standard
  acreditado».
- **H-02.** Las dos sondas cambian instalación **y** versión a la vez. Se puede descartar la cuenta
  —la misma corrió Sol dos minutos después— y no se puede aislar versión de ruta.
- **H-04.** Comprobado contra `CLAUDE.md:78-85` y la tabla de modelo: el contrato de revisión está
  nombrado entre lo que **nunca** queda exento de ronda, y no aparecía en ninguna fila de modelo.
  El hueco era real.
- **H-07.** Comprobado en `tests/test_docs_gobernanza.py`: `_CLAVES_ACTA` no incluye los tres campos
  nuevos, así que un acta sin ninguno pasa en verde. Mi argumento confundía *verdad* con
  *presencia*.
- **G7/G8/G9 sobre el corpus:** 46/46 en verde en este lado (el revisor corrió 31 con 15
  deseleccionados; la diferencia es el `-k` de su selección, no una discrepancia).
