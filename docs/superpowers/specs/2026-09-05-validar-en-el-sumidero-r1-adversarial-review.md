---
tipo: revision-adversarial
objeto: "diseno «validar en el sumidero» (rev. 1), para cerrar MEJORAS #153 y #154"
objeto_rev: "rama claude/aprendizajes-en-codigo, commit 37726c8"
commit: "37726c8"
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: q9wm
sha256_informe: 8a6f3f384a72d735d3ac20c1072085ebf23f9abb31b40c28d72fafede33660c7
adjudicado_en: docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-design.md §3
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1 sobre un DISEÑO.** El §0 es el mandato literal, el §1
> conserva la voz del revisor sin una coma cambiada, el §2 es la evidencia que verifiqué por mi
> cuenta y el §3 mi adjudicación.
>
> **Dónde vive la adjudicación:** en la **rev. 2 del propio diseño**
> (`2026-09-05-validar-en-el-sumidero-design.md`), que es la forma preferente que manda
> `CLAUDE.md` — la decisión pertenece al documento que la decisión modificó. Aquí, en el §3, va
> solo el mapa hallazgo → dónde se remedió, para que se pueda contrastar sin leer el diseño
> entero.
>
> **Esta es la primera de las dos rondas** que la pieza compra por radio de daño: decide dónde
> se deposita un expediente con PII. La segunda va sobre el diff.
>
> **Contexto de autoridad, que conviene que conste:** Nikolai se fue a dormir dejando encargado
> el trabajo y pidiendo expresamente que las decisiones que le consultaría a él se le
> consultaran a Codex. Por eso el **alcance** de la rev. 2 —estrecho, sin tocar de noche la
> máquina de copias operativas— lo decidió Codex en una consulta aparte, y así está declarado
> en la propia rev. 2. No es una decisión mía disfrazada de técnica.

## 0. Mandato, literal

# MANDATO — Revisión adversarial R1 sobre un DISEÑO (FeesDefender)

## Higiene, primero

Tu directorio de trabajo debe contener **solo este `MANDATO.md`**. Si encuentras cualquier
otro fichero (informes, logs, salidas), **no lo leas** y decláralo en la primera línea de tu
informe.

## Rol

Eres el revisor adversarial. Tu trabajo es **encontrar defectos en el diseño**, no aprobarlo.
El autor (Claude) adjudicará cada hallazgo contra la fuente. Un hallazgo concreto y falsable
vale mucho más que una observación general. No hace falta que seas amable.

**Nikolai, el dueño del proyecto, se ha ido a dormir y ha pedido expresamente que las
decisiones que le consultaría a él te las consulte a ti.** Así que si el diseño tiene una
decisión mal tomada —no un bug, una decisión— dilo con esa etiqueta.

## Objeto

Copia congelada en un directorio **hermano** al tuyo: `../rev-fd-sumidero-r1-0055-obj/`.

El objeto de esta ronda es **el diseño**:

```
docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-design.md
```

El código que el diseño va a modificar, para que puedas contrastar sus afirmaciones:

```
core/case_manager.py          (ensure_case: el sumidero)
core/casos/case_locator.py    (destino_de_alta, path_for_ciudad, buscar, _root)
core/utils.py                 (exigir_sin_caracteres_de_ruta, validate_case_id)
streamlit_app.py              (la puerta que NO se va a tocar; ~líneas 1970-2170)
```

No hay `.git`: no puedes acreditar genealogía, solo contenido. **Calcula el `sha256` de los
ficheros que revises al abrir y al cerrar** y hazlo constar. Si necesitas escribir algo,
escríbelo en TU directorio, nunca bajo `../rev-fd-sumidero-r1-0055-obj/`.

## Qué sostiene el diseño, y dónde atacarlo

Sostiene que basta **una** comprobación en `ensure_case`, justo antes del `mkdir`, con dos
mitades (gramática de un solo componente + contención del destino resuelto bajo la raíz),
para cerrar dos defectos preexistentes: la UI de Streamlit que compone su propio `case_id` y
reproduce el caso `s/n`, y el override de ruta que permite escapar de `CASOS_ROOT`.

Ataca esto en particular, y no te limites a esto:

1. **¿Es `ensure_case` de verdad el único sumidero?** Su propio comentario lo afirma. Busca
   otros caminos que **creen** el árbol de un caso: `mkdir`, `makedirs`, `shutil.copytree`,
   `rclone`, `move_to_city`, el checkout/checkin, el intake por lotes. Si hay otro, el
   diseño está mal en su premisa central.
2. **¿La contención bajo `_root()` rompe algo?** `CASOS_ROOT` es una env var y hay un modo
   «local» documentado en que apunta al Desktop tras un *checkout*. Mira `CaseWorkspace` y
   `core/casos/*` y dime si algún camino legítimo materializa un caso **fuera** de la raíz
   configurada. Si lo hay, la mitad (b) del diseño bloquea trabajo legítimo.
3. **¿Es `resolve()` la primitiva correcta en Windows?** Piensa en rutas UNC, en `G:` (Drive
   Stream, un filesystem virtual), en enlaces/junctions, y en que `resolve()` toca el disco.
   ¿Puede lanzar, colgarse o mentir? ¿Sería mejor `os.path.normpath` + comparación, o
   `PurePath.is_relative_to` sin resolver?
4. **El orden de las dos mitades y el momento.** El diseño valida sobre `case_dir` **ya
   resuelto**, después de `destino_de_alta`/`path_for_ciudad`. ¿Se puede haber hecho ya daño
   antes de ese punto? ¿`buscar()` puede devolver algo fuera de la raíz y con eso la
   contención rechazar un caso que YA existe legítimamente?
5. **¿Falta un tercer defecto de la misma familia?** El diseño dice que el patrón —«la guarda
   está en el envoltorio y el otro llamador la rodea»— se ha manifestado tres veces en dos
   días. Si ves una cuarta manifestación en el código que revisas, es el hallazgo más
   valioso que puedes devolver.
6. **¿El alcance es honesto?** El §7 declara qué no cierra. ¿Se deja fuera algo que en
   realidad es parte inseparable de esto?

## Puedes EJECUTAR, y eso cambia la ronda

El **Python de sistema** tiene `pytest`, `filelock`, `yaml`, `dotenv`, `typer`, `httpx` y
`mcp`:

```
C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe
```

Avisos que te ahorran falsos rojos:

- `--basetemp` **relativo dentro de tu propio workdir** y **corto** (tu sandbox no puede
  crear `C:\t\...`; y MAX_PATH tumba tests que están bien).
- **No mutes el objeto.** Si necesitas correr, copia a tu workdir.
- No tienes `pytest-randomly`; si algo exige dos semillas, declara **SIN VERIFICAR**.
- Dos tests de `tests/test_crm_dedup_incertidumbre.py` fallan por falta de
  `SUDESPACHO_LEGACY_HOST` en `.env`. Defecto conocido y ajeno: no lo atribuyas.
- Sondas de comportamiento de `pathlib` en Windows (p. ej. qué hace `Path("C:/a") / "D:/b"`,
  o `resolve()` sobre una ruta inexistente) son **bienvenidas**: el diseño se apoya en ellas.

## Qué tiene que devolver tu informe

Escribe `INFORME.md` en tu directorio, con:

1. **Un hallazgo por bloque**: severidad (`CRÍTICO` / `ALTO` / `MEDIO` / `BAJO`), si es
   **defecto** o **decisión mal tomada**, qué afirmación del diseño falsa, el escenario
   concreto, y qué lo demostraría. Si lo ejecutaste, pega la salida.
2. Lo que revisaste y **no** encontraste defectuoso, una línea por pieza.
3. Lo que **no pudiste verificar**, y por qué. Un revisor que no corre no refuta.
4. El `sha256` de los ficheros revisados, al abrir y al cerrar.
5. **En la ÚLTIMA línea, el veredicto, exactamente una de estas cuatro palabras y nada más:**

```
SHIP
SHIP-CON-RESERVAS
NO-SHIP
SIN-VERIFICAR
```

Si dudas entre dos, elige la más conservadora y explica por qué arriba.

## 1. Informe recibido, literal

> Voz del revisor, sin una coma cambiada. El digest del frontmatter se computa sobre
> este bloque canonicalizado, que es lo que recomputa el guard G8.

<!-- informe-literal:inicio:q9wm -->
Higiene inicial: el directorio de trabajo contenía únicamente `MANDATO.md`; no había informes, logs ni salidas previas.

# Revisión adversarial R1 — Validar en el sumidero

Objeto: `../rev-fd-sumidero-r1-0055-obj/docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-design.md`. Revisión de contenido congelado, sin acreditación de genealogía: no hay `.git`. El autor adjudica los hallazgos contra la fuente.

El diseño corta los ejemplos concretos de `s/n` y de ID absoluto que llegan a `ensure_case`, pero no demuestra la frontera que anuncia. Encontré cuatro problemas sustantivos y una carencia en el contrato de pruebas. Recomiendo NO-SHIP por los primeros cuatro, no por falta de ejecución ni por los fallos iniciales del montaje de pytest.

## Método y significado de las reproducciones

Se calcularon hashes de todo el objeto antes de consultar su contenido y al terminar. No se ejecutó código desde el objeto ni se escribió bajo él. Se copiaron `core`, `scripts`, `tests` y `pyproject.toml` al directorio del revisor. `preparar_sonda.py` insertó **solo en la copia** una transcripción de §3 antes del primer `case_dir.mkdir`: llamar a `exigir_sin_caracteres_de_ruta`, rechazar exactamente `.`/`..`, y exigir `case_dir.resolve().is_relative_to(_root().resolve())`. No es un diff del autor ni una implementación entregable. Las reproducciones prueban las reglas expresas del diseño con el resto del código real.

Intérprete de ejecución: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`, Python 3.14.4, Windows AMD64. Se usó `PYTHONDONTWRITEBYTECODE=1`. Todos los datos son sintéticos. `FUERA` significa fuera del `CASOS_ROOT` de prueba, **dentro del directorio del revisor**. No se usaron CRM, Drive, rclone ni servicios reales. Los fixtures de las sondas no incluyen plantillas Excel: el código emitió avisos de plantilla ausente y omitió esas copias; el esqueleto y `_caso.md` sí se materializaron.

Artefactos reproducibles: `preparar_sonda.py`, `sonda.py`, `sonda-salida.txt`, `pytest-salida.txt` y `pytest-separado.txt`. La sonda usa carpetas nuevas en `p/`; para repetirla debe utilizarse otra copia limpia del montaje, pues conserva sus evidencias en disco.

## H-01 — ALTO — Decisión mal tomada: convertir «única alta nominal» en «único depósito del árbol»

**Afirmación falsa:** §2 dice que por `ensure_case` pasan todas las puertas y que con validarlo quedan cubiertas las futuras. §3 deja intactos los constructores nominales porque «crear es del llamador». Hay otros llamadores que materializan destinos, y uno mueve el expediente completo.

**Fuente:** `core/casos/case_locator.py:270-319`: `move_to_city` solo valida la longitud de `motivo`; compone `dest` con `path_for_ciudad`, hace `dest.parent.mkdir(parents=True)` y `shutil.move(src, dest)`. No llama a `ensure_case`, no valida `ciudad_destino` ni comprueba contención. El catálogo cerrado está en el envoltorio Streamlit (`streamlit_app.py:1436-1456`). La presencia de un catálogo en ese formulario no protege la API de core.

**Escenario y demostración ejecutada:** crear `EV-2026-001`, depositar un canario en su `00_Input` y llamar `move_to_city(case_id, '../FUERA', 'Motivo sintetico', 'revisor')`. Con las dos mitades de la nueva guarda ya activas en la copia, la operación mueve el árbol entero fuera de la raíz, actualiza metadatos y termina sin excepción. El origen desaparece y `buscar` pierde el caso. Extracto literal de `sonda-salida.txt`:

```json
{"test": "move", "dest": "C:\\t\\rev-fd-sumidero-r1-0055\\p\\move\\FUERA\\EV-2026-001", "outside": true, "payload": "CANARIO", "source_exists": false, "buscar": null}
```

**Segundo contraejemplo a la frontera de depósito:** `reservar_lote(str(directorio_exterior_existente), 'manual', 'sonda')` crea `00_Input/<lote>` fuera de raíz sin pasar por `ensure_case`. `core/intake_lotes.py:89-98` utiliza `caso_path` y `dir_intake`; `core/casos/case_locator.py:43-46` admite cualquier directorio absoluto existente como si fuera caso. No exige `_caso.md`. Aquí no se creó un alta completa, sino el árbol de intake de un caso fantasma; esa distinción no devuelve la contención prometida.

```json
{"test": "intake_absolute", "outside": true, "lote_exists": true, "index": false}
```

**Qué lo refutaría:** que esos caminos rechacen el destino antes de crear o trasladar bytes, o que el diseño limite explícitamente su garantía al alta nominal por `ensure_case` y deje de sostener que este es el sumidero de todo depósito. Para sostener la garantía general hace falta censar y proteger los escritores, separando además checkout legítimo de escape accidental. Añadir más validación dentro de `ensure_case` no cambia estas reproducciones.

## H-02 — ALTO — Defecto: el ID vacío convierte CASOS_ROOT en un expediente

**Afirmación falsa:** §3(a) promete «un solo componente de ruta». El helper reutilizado únicamente rechaza la expresión `[\\/:*?"<>|]`; acepta `''` (`core/utils.py:119-134`). Añadir solo `.`/`..` no cubre el componente vacío. `is_relative_to` incluye la igualdad, por lo que §3(b) también lo acepta.

**Escenario:** con una raíz existente, `ensure_case('')` obtiene la propia raíz desde `buscar('')`, supera ambas mitades, crea todas las subcarpetas estándar directamente en `CASOS_ROOT` y escribe allí `00_Input/_caso.md`. No requiere enlaces, carreras ni acceso a otro volumen. El override vacío de la UI usa su valor automático, por lo que este es un defecto de la API que el diseño promete cerrar para todo llamador, no un repro del formulario vacío.

**Demostración ejecutada:**

```json
{"test": "grammar", "case_id": "", "result": "ACCEPT", "root_index": true, "resolved": ".", "children": ["00_Input", "01_Procesado", "02_Analisis", "03_Decision", "04_Output predemanda", "05_Procedimiento", "06_Anonimizado", "07_AI cowork", "90_Notas personales"]}
```

**Qué lo refutaría:** rechazo antes de cualquier escritura, con raíz y árbol exactamente iguales a los de entrada. El contrato debe exigir un componente no vacío y que el destino del caso no sea la propia raíz. `validate_case_id` ya tenía una comprobación de vacío separada, pero el diseño reutiliza solo la otra mitad (`core/utils.py:144-147`).

## H-03 — ALTO — Defecto: la gramática ignora ciudad y permite volver a fabricar una ruta sombra

**Afirmación falsa:** §2 anuncia corregir la propiedad, no solamente el ejemplo; §3 valida solo el ID y acepta cualquier destino contenido. `ciudad` también compone el destino y puede introducir niveles que el localizador no sabe recorrer.

**Fuente:** `ensure_case` acepta `ciudad` sin validarla (`core/case_manager.py:340-342`); `path_for_ciudad` concatena los tres términos (`core/casos/case_locator.py:261-267`). `buscar` solo reconoce raíz plana y las ciudades enumeradas (`:132-143`). El CLI sí valida `ciudad in CIUDADES` (`scripts/abrir_caso.py:975,1000`); el core no. Es otra manifestación concreta de **«guarda en el envoltorio, otro llamador la rodea»**.

**Escenario:** `ensure_case('EV-2026-001', ciudad='Barcelona/subcarpeta')`. El ID es válido para la gramática propuesta y el destino resuelto está dentro de raíz. Se crea `CASOS/Barcelona/subcarpeta/EV-2026-001/00_Input/_caso.md`. Inmediatamente `buscar('EV-2026-001')` devuelve `None`. Repetir el alta sin ciudad crea un segundo expediente plano. Lo mismo merece control para una ciudad desconocida de un solo componente: contención y localización son propiedades diferentes.

**Demostración ejecutada:**

```json
{"test": "city", "inside": true, "buscar": null, "index": true}
{"test": "city_again", "duplicate": true}
```

**Qué lo refutaría:** que toda alta exitosa devuelva un destino recuperable por el localizador bajo la misma identidad, y una segunda alta no genere otra raíz. Hay que contratar la ciudad como parte del destino: rechazar subrutas y decidir qué catálogo de ciudades admite core, incluyendo el fallback legítimo. No exige formato canónico para el ID ni tocar la UI.

## H-04 — ALTO — Defecto: resolver la raíz del caso no contiene sus escrituras en hijos enlazados

**Afirmación falsa:** §3(b) presenta la resolución como defensa frente a enlaces y §7 no limita esa defensa a enlaces en los ancestros de `case_dir`. La operación valida un directorio y escribe en muchos descendientes sin comprobarlos.

**Escenario:** existe `CASOS/EV-2026-002/` como directorio normal, con `00_Input` como junction hacia `FUERA/`, ya presente antes de entrar. `case_dir.resolve()` está dentro de raíz. `mkdir(exist_ok=True)` acepta el hijo enlazado; `_ensure_crm_tree_dirs` crea `05_CRM` fuera y `_write_case_index` deposita `_caso.md` allí (`core/case_manager.py:349-388`, `core/utils.py:211-214`). No hace falta cambiar ningún enlace entre la comprobación y la escritura: **no es un TOCTOU**.

**Demostración ejecutada con junction real de Windows:**

```json
{"test": "junction_setup", "rc": 0, "error": ""}
{"test": "junction_resolve", "lexical": true, "physical": false}
{"test": "junction_case", "result": "ValueError", "out_empty": true}
{"test": "junction_child", "case_inside": true, "outside_index": true}
```

Las primeras líneas son el control hermano: una junction **en el propio caso** sí es rechazada y deja el exterior vacío. Al colocarla **en `00_Input`** el índice termina fuera. Sustituir `case_dir` por su valor resuelto antes de escribir no arreglaría este caso: la raíz real ya era correcta.

**Qué lo refutaría:** el mismo escenario debe abortar antes de escribir en el exterior y antes de dejar andamiaje parcial, o el diseño debe retirar expresamente la garantía contra estos enlaces preexistentes y justificar esa decisión. Si el propósito incluye contención física de todo lo que escribe `ensure_case`, una única comprobación del directorio padre es insuficiente. El TOCTOU posterior sería otra limitación, separada y todavía no verificada.

## H-05 — MEDIO — Defecto: los mutantes de §6 no ejercen la mitad de contención

**Afirmación que no queda contratada:** §3 sostiene que hacen falta dos propiedades independientes; §6 solo contiene negativos que rechaza (a): `/`, `\`, `:` y `.`/`..`. Los dos positivos pasan también si se elimina (b). La tabla permite que una implementación sin contención cumpla todos los resultados previstos.

**Demostración:** análisis de cada fila contra `core/utils.py:105,128` y el rechazo adicional de puntos. No ejecuté una campaña de mutación eliminando (b); sí ejecuté un testigo independiente de (b), `case_id='Enlace'` con junction exterior, que supera la gramática y es rechazado por contención. Ese testigo no figura en §6.

**Qué lo refutaría:** incorporar un negativo con ID de un componente permitido cuyo destino salga de raíz (junction en caso/ciudad, o ciudad absoluta), y comprobar que falla por contención y sin escrituras. El argumento de §3 «(a) sola dejaría pasar una ruta absoluta si algún día pathlib…» es incorrecto: el helper rechaza sus separadores y dos puntos antes de cualquier semántica de unión. El papel real de (b) debe explicarse con ciudades y alias, no con un cambio hipotético de pathlib.

## Respuestas a los seis ataques del mandato

1. **¿Único sumidero? No.** H-01 prueba traslado completo e intake parcial. También `cmd_checkout` toma `args.local`, hace `local.mkdir` y `rclone copy` (`scripts/repository_cli.py:529-604`), y checkin publica mediante rclone (`:661-665,744-759`). Son caminos diferentes. Los `copytree` de `core/email_atomize/entregas.py:37-54` copian entregables a `_entregas`, no son por sí solos prueba de un segundo alta canónica; no los he inflado a hallazgo.
2. **¿Rompe local? No he reproducido una regresión de ensure_case por esa condición.** Con `CASOS_ROOT` local y caso bajo ciudad, la segunda llamada retorna la misma ruta: `{"test": "existing_city", "same": true}`. Pero sí existen materializaciones legítimas fuera de la raíz configurada: checkout usa `args.local`, y el resolver puede devolver `entrada.local_path` (`core/casos/workspace_resolver.py:142-144`). `ubicacion.py:70-84` exige que un workspace local esté fuera del catálogo. Esos caminos no llaman al alta; por tanto no son prueba de que la guarda propuesta los bloquee. Sí refutan usar esa guarda como política universal para todos los depósitos. El contrato dual §7.3 permite el override de `CASOS_ROOT` a los componentes legacy y lo distingue de la selección de workspace ya migrada. §5.2 del diseño debe conservar esa distinción.
3. **¿resolve o normpath? Mantener una comprobación física para la propiedad física.** La sonda real demostró `lexical=true`, `physical=false` ante una junction estable; `normpath` o `PurePath.is_relative_to` sin resolución perderían esa protección. La unión Windows probada devuelve `D:\b` para `Path('C:/a') / 'D:/b'`. La construcción UNC pura conserva `\\srv\share\a\Caso`; no se contactó ese servidor. `resolve(strict=False)` es una resolución hasta donde puede llegar, no un certificado de que todos los componentes fueron inspeccionados; la documentación lo explica así. En 3.14 `realpath(..., strict=ALLOW_MISSING)` distingue ausencia de otros errores, pero el proyecto declara Python >=3.11: no se puede imponer esa API sin decidir compatibilidad. Véanse [Path.resolve](https://docs.python.org/3.14/library/pathlib.html#pathlib.Path.resolve) y [os.path.realpath](https://docs.python.org/3.14/library/os.path.html#os.path.realpath). Sin sondeo en G:/UNC reales, no afirmo latencia aceptable, bloqueo, ni un escape por resolución incompleta. El riesgo probado es H-04.
4. **¿Orden y daño previo?** Antes de la línea 343 no identifiqué creación del árbol dentro de `ensure_case`: hay comprobaciones de mutex, búsquedas, lectura de metadatos y elección de destino. `destino_de_alta` no escribe, pero su docstring «no toca el disco» es demasiado fuerte: llama `buscar`, que ejecuta `is_dir`. Validar gramática antes de buscar evita consultar rutas arbitrarias, incluidas UNC, antes del rechazo. En modo v1 hay otra búsqueda previa en `:318`. La UI también ejecuta `get_case_status` antes del botón y, en alta incoherente confirmada, escribe un audit log antes del alta (`streamlit_app.py:1999,2141-2150`): «sin efectos de ningún tipo» no se puede prometer solo con esa guarda. No confundí ese log con una carpeta parcial del caso. `buscar` puede devolver un directorio externo por ID absoluto o junction; está probado el rechazo posterior, pero no encontré evidencia de una instalación legítima que necesite ese alias para llamar a ensure_case. No lo doy por una regresión demostrada.
5. **¿Cuarta manifestación? Sí.** La ciudad se valida en el CLI y en el selectbox, pero ambas operaciones de core que la usan para depositar la aceptan libremente. H-01 y H-03 muestran dos consecuencias de esa misma guarda en el envoltorio. El intake de H-01 añade el bypass de gramática mediante un directorio absoluto preexistente.
6. **¿Alcance honesto? Insuficiente.** Separar la estructura plana de la sala de lectura (#67) y el contrato de #149 no resulta defectuoso por sí mismo. Lo inseparable de la afirmación actual es definir qué materialización protege, cuáles son los componentes del destino y qué enlaces cubre. H-01/H-03 no se arreglan repitiendo que nombrar no es crear; H-04 no es una carrera remota ni un ataque a otro subsistema. Se puede reducir el objetivo a los dos ejemplos de alta, pero habría que retirar la garantía universal y declarar expresamente lo pendiente.

## Revisado sin defecto encontrado en estas propiedades

- `ensure_case`: la guarda transcrita rechaza `s/n`, `..\..\escape`, ID absoluto, `.` y `..`, dejando cada raíz de sonda vacía.
- `exigir_sin_caracteres_de_ruta`: preserva paréntesis, comas, acentos y el caso hermano proporcionado por el diseño; no obliga a formato canónico.
- `destino_de_alta`/`path_for_ciudad`: no materializan directorios por sí mismos; la búsqueda conserva la ubicación de un caso ya existente en ciudad.
- `buscar`/`caso_path`: para un ID ordinario ausente, la estrictez impide que reservar lote lo convierta automáticamente en un caso nuevo; el contraejemplo de H-01 necesita un directorio exterior ya existente.
- `_root`: usa la misma fuente de configuración que los constructores de alta; no vi una segunda raíz escondida dentro de esa operación.
- `CaseWorkspaceResolver`: los tests seleccionados cubren local, canon, bloqueo, nonce, scratch y offline sin fallos tras separar correctamente los temporales.
- `resolve` sobre junction estable en el propio destino: detecta el escape que una comparación exclusivamente léxica acepta.
- UI de alta: el mensaje de éxito y el alta CRM vienen después de `ensure_case`; una excepción allí corta esa continuación. No ejecuté Streamlit completo.

## Ejecución, límites y SIN VERIFICAR

La primera corrida seleccionó 109 tests y tuvo 22 fallos de `test_workspace_resolver.py`: `WorkspaceRegistry` detectaba el registro temporal bajo el project_root de la copia (`workspace_registry.py:157-160`). No es hallazgo contra el diseño. Se copió el mismo código y tests a `c/` y se dejaron los temporales en `b2/`, ambos bajo el workdir del revisor. No se modificó la lógica del registro ni los tests para conseguir verde.

Comando desde `c/`, con el intérprete indicado y `CASOS_ROOT` sintético:

```text
python -m pytest -p no:cacheprovider --basetemp=../b2 -o addopts='' tests/test_case_manager.py tests/test_case_locator.py tests/test_intake_lotes.py tests/test_workspace_resolver.py -q --tb=short
........................................................................ [ 66%]
.....................................                                    [100%]
109 passed in 10.27s
PYTEST_EXIT=0
```

`sonda.py` terminó con código 0; sus salidas muestran los comportamientos, no una aprobación del diseño. La tabla §6 pasó en las sondas, y los contraejemplos adicionales también se materializaron. No se atribuyen los fallos conocidos de CRM: ese módulo de tests no se ejecutó.

- **SIN VERIFICAR:** catálogo real de 27 casos y medición de §5.1. No se accedió a los expedientes reales.
- **SIN VERIFICAR:** Drive Stream G:, UNC conectado, fallos de permisos/hidratación y tiempos de resolución; no hubo pruebas sobre esos sistemas.
- **SIN VERIFICAR:** carreras TOCTOU, bucles de enlaces en distintas versiones Python y equivalencias Volume GUID/UNC/8.3. La junction estática local sí se ejecutó.
- **SIN VERIFICAR:** checkout/checkin contra rclone real, sus efectos remotos y la integración completa de Streamlit. Se inspeccionaron sus caminos, no se simularon como ejecución E2E.
- **SIN VERIFICAR:** suite completa, pruebas de Excel y ejecución con dos semillas; no está instalado pytest-randomly. Los 109 tests no se extrapolan al resto.
- **SIN VERIFICAR:** implementación final del autor: solo hay diseño. Se revisó una transcripción mínima para intentar refutar sus reglas.
- El barrido de `core/**/*.py`, `scripts/**/*.py` y `streamlit_app.py` buscó primitivas de creación/traslado y referencias a workspace. No equivale a revisión semántica completa de cada fichero. No se afirma cobertura completa de plugins, helpers archivados ni servicios externos.
- La búsqueda con `rg` no estuvo disponible y se sustituyó por un lector Python que registra archivos abiertos. Se intentó abrir `tests/test_repository_frontal.py`, que no existe en la copia: no se atribuye cobertura a ese nombre.

## Integridad y hashes

Los hashes de apertura preceden a las lecturas y a la copia ejecutable; los de cierre se calculan sobre el objeto original, nunca sobre las copias modificadas por la sonda. Se incluye cada archivo abierto por lectura o barrido, además de los tests y fixtures ejecutados. Los archivos solo barridos se identifican como tales: el hash acredita contenido estable, no profundidad de revisión. Las habilidades externas del entorno se enumeran separadamente como instrucciones de proceso, no como objeto revisado: `using-superpowers`, `verification-before-completion` y `systematic-debugging`.

La tabla siguiente y el resultado de comparación se incorporan automáticamente desde los manifiestos de apertura y cierre; ambos manifiestos quedan junto al informe.

Comparación integral: **1175 archivos de apertura y 1175 de cierre; 0 modificados, 0 añadidos y 0 eliminados**. Se registran abajo 198 archivos abiertos o ejecutados del objeto. Lectura dirigida significa lectura de funciones/pasajes relevantes, no necesariamente del fichero completo.

| Archivo relativo al objeto | Cobertura | SHA256 apertura | SHA256 cierre |
| --- | --- | --- | --- |
| `AGENTS.md` | Lectura dirigida | `f4cfbe9c35ea45ee324cfef29450116135dab2945686086fb6444e5301d6698b` | `f4cfbe9c35ea45ee324cfef29450116135dab2945686086fb6444e5301d6698b` |
| `CLAUDE.md` | Lectura dirigida | `78bdd63acfd1b0bc198a36449fb4e86674dcfc4673698460568bd45df2384abf` | `78bdd63acfd1b0bc198a36449fb4e86674dcfc4673698460568bd45df2384abf` |
| `PLAN.md` | Barrido léxico | `6fc1c67bfed33a14908941c12b1b75a2e1c886bea5f65ffd8aed4fc91fd4fdc3` | `6fc1c67bfed33a14908941c12b1b75a2e1c886bea5f65ffd8aed4fc91fd4fdc3` |
| `STATUS.md` | Barrido léxico | `89fc87b27c7c4597d965ab65e7036f5b35eba9319bd8cb22ae4fa0224151aef0` | `89fc87b27c7c4597d965ab65e7036f5b35eba9319bd8cb22ae4fa0224151aef0` |
| `core/__init__.py` | Barrido léxico | `512b9796234d30cdfa3bb3bc056b82a1e13a4633ffa854ab02974ba1d6da11e4` | `512b9796234d30cdfa3bb3bc056b82a1e13a4633ffa854ab02974ba1d6da11e4` |
| `core/abrir_caso.py` | Barrido léxico | `873c0c2e3cb6458a6cc88476273c8b2f1fdbeef6e4a76991ac118cb7711fc9aa` | `873c0c2e3cb6458a6cc88476273c8b2f1fdbeef6e4a76991ac118cb7711fc9aa` |
| `core/adjuntos_contenido/__init__.py` | Barrido léxico | `4c42235933f559674306d600409126703ad8237bdcad0a1abef4d9fd38896271` | `4c42235933f559674306d600409126703ad8237bdcad0a1abef4d9fd38896271` |
| `core/adjuntos_contenido/__main__.py` | Barrido léxico | `7657d1f84276c82aa45e5736d673cff0cfa15c1712af325de175b7583463ec74` | `7657d1f84276c82aa45e5736d673cff0cfa15c1712af325de175b7583463ec74` |
| `core/adjuntos_contenido/descubrir.py` | Barrido léxico | `7916a18293d9a18da42a975b3eee8ff6d5929ec6e9d7c05ac41e9066fc1f8a27` | `7916a18293d9a18da42a975b3eee8ff6d5929ec6e9d7c05ac41e9066fc1f8a27` |
| `core/adjuntos_contenido/estado.py` | Barrido léxico | `4c9a51b8dbeeb6093477de3c71f3d2d45e1cd45830f4f4c6d6b3bf9532ffe802` | `4c9a51b8dbeeb6093477de3c71f3d2d45e1cd45830f4f4c6d6b3bf9532ffe802` |
| `core/adjuntos_contenido/model.py` | Barrido léxico | `5a158b3f8e4bebb4d90f6d2194d6acf0db02b04fccb0964eec942e93c76947da` | `5a158b3f8e4bebb4d90f6d2194d6acf0db02b04fccb0964eec942e93c76947da` |
| `core/adjuntos_contenido/pipeline.py` | Barrido léxico | `6058d0cadddb195198f3b19680f295529c3b56848f1799fca13db7d0472d51e5` | `6058d0cadddb195198f3b19680f295529c3b56848f1799fca13db7d0472d51e5` |
| `core/adjuntos_contenido/render.py` | Barrido léxico | `a12bc4c3d45c4f967134e40af79d02dafac08d7da9b222534dc8fbdd6401d7ca` | `a12bc4c3d45c4f967134e40af79d02dafac08d7da9b222534dc8fbdd6401d7ca` |
| `core/adjuntos_contenido/resumen.py` | Barrido léxico | `23ce61326c5a97127044d5e21e51e24f89a8a47896c7678bd833403fe5f44325` | `23ce61326c5a97127044d5e21e51e24f89a8a47896c7678bd833403fe5f44325` |
| `core/adjuntos_contenido/router.py` | Barrido léxico | `ccc1d8fddd85a82ecdba181b5ceb4bd95ff748abc7bfd2735a3aa68a30519c6b` | `ccc1d8fddd85a82ecdba181b5ceb4bd95ff748abc7bfd2735a3aa68a30519c6b` |
| `core/adjuntos_contenido/zips.py` | Barrido léxico | `ca1be6017c61e8521d520f1685f553441f935076e9ea1dae2a77d694b9b56893` | `ca1be6017c61e8521d520f1685f553441f935076e9ea1dae2a77d694b9b56893` |
| `core/anon/__init__.py` | Barrido léxico | `7fb2c3cecfcacba6043e3ea47a104c1200044cfbfe1e98d8954fb280f002d921` | `7fb2c3cecfcacba6043e3ea47a104c1200044cfbfe1e98d8954fb280f002d921` |
| `core/anon/anonimizar.py` | Barrido léxico | `0b296625d7772e00cd15444b926ba46bd447c45d57e00f11ab3494fbbd1779db` | `0b296625d7772e00cd15444b926ba46bd447c45d57e00f11ab3494fbbd1779db` |
| `core/anon/api.py` | Barrido léxico | `5ea44e7b92cbb83b2ca654cb2897c3ee0e77033449726e00494a61979ca23fcd` | `5ea44e7b92cbb83b2ca654cb2897c3ee0e77033449726e00494a61979ca23fcd` |
| `core/anon/deanonimizar.py` | Barrido léxico | `76c7165da124b15acd9b97d9424a1b06bf2edc7242d0df6b0e726ff2b72d73b9` | `76c7165da124b15acd9b97d9424a1b06bf2edc7242d0df6b0e726ff2b72d73b9` |
| `core/anon/exceptions.py` | Barrido léxico | `a4a8361136f6b88d30ca6953b66131d535496f4c298e791e5c9445920ccab753` | `a4a8361136f6b88d30ca6953b66131d535496f4c298e791e5c9445920ccab753` |
| `core/anon/imagen_a_pdf.py` | Barrido léxico | `661048c61c1fdf97739481f3ec120c5273c1e4ef19cc49258a47e9a492621587` | `661048c61c1fdf97739481f3ec120c5273c1e4ef19cc49258a47e9a492621587` |
| `core/anon/mapa_caso.py` | Barrido léxico | `d55af2e14e47fdeb62e3910111a3d4bdba37874a121f2d74b5dd395f9667e730` | `d55af2e14e47fdeb62e3910111a3d4bdba37874a121f2d74b5dd395f9667e730` |
| `core/anon/nlp_engine.py` | Barrido léxico | `47a7574e756a1d1770261d8025871573e02d13457087cecc0e67dc7f3c2f464d` | `47a7574e756a1d1770261d8025871573e02d13457087cecc0e67dc7f3c2f464d` |
| `core/anon/ocr.py` | Barrido léxico | `a390d92f0b79ecc2a6e3db13f117a8bbb66b5acf8e358162cefd96dde91eb074` | `a390d92f0b79ecc2a6e3db13f117a8bbb66b5acf8e358162cefd96dde91eb074` |
| `core/anon/pdf_lineas.py` | Barrido léxico | `a536812978ce6b0781c4f443541732877e65541aed195737be5bf42b22e8482d` | `a536812978ce6b0781c4f443541732877e65541aed195737be5bf42b22e8482d` |
| `core/anon/renombrar.py` | Barrido léxico | `7a1d9c99cb9e54802b7fc45c638a405ab5115e1cef2d0f5d1f93d95b089b853a` | `7a1d9c99cb9e54802b7fc45c638a405ab5115e1cef2d0f5d1f93d95b089b853a` |
| `core/anon/separar.py` | Barrido léxico | `f8dfe316f0f481318728ac0adb3414457c6bfd7cef97a68965f2de0af27a0098` | `f8dfe316f0f481318728ac0adb3414457c6bfd7cef97a68965f2de0af27a0098` |
| `core/apertura_v1.py` | Barrido léxico | `7cea2191811cc52b6baadcda0f37beabb8e4c9129abf132865dcc9dffd20966f` | `7cea2191811cc52b6baadcda0f37beabb8e4c9129abf132865dcc9dffd20966f` |
| `core/apertura_v1_estado.py` | Barrido léxico | `b817ad4e0892aa7ce17c85990d0582f06b076ee3eb6fb7bd1a4827aaa2d8d58e` | `b817ad4e0892aa7ce17c85990d0582f06b076ee3eb6fb7bd1a4827aaa2d8d58e` |
| `core/case_manager.py` | Lectura dirigida | `0dfd269d0240900356fbb462fd633f0cfb3c329f36bad57fa4a6952f5e0f58c2` | `0dfd269d0240900356fbb462fd633f0cfb3c329f36bad57fa4a6952f5e0f58c2` |
| `core/casos/__init__.py` | Barrido léxico | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `core/casos/case_catalog.py` | Lectura dirigida | `774d1b79001774e4f3ef8d5ef10d1777d4bb17aad8ec3edb28573c1d5dbd8b56` | `774d1b79001774e4f3ef8d5ef10d1777d4bb17aad8ec3edb28573c1d5dbd8b56` |
| `core/casos/case_locator.py` | Lectura dirigida | `3ca55e5febe1cdaf18448553bd13cf5d714a7ebebfeb15c52d521f6758b3c71d` | `3ca55e5febe1cdaf18448553bd13cf5d714a7ebebfeb15c52d521f6758b3c71d` |
| `core/casos/case_mutex.py` | Barrido léxico | `0ade763185f0d11f881dce01afb914b21f3da9379b87204306018018c0570b53` | `0ade763185f0d11f881dce01afb914b21f3da9379b87204306018018c0570b53` |
| `core/casos/escritura.py` | Lectura dirigida | `a7385c7e9bd65febedcc3903b48ca2050a12e842b4405ba1c22eb560f6864ef4` | `a7385c7e9bd65febedcc3903b48ca2050a12e842b4405ba1c22eb560f6864ef4` |
| `core/casos/mutex_sesion.py` | Barrido léxico | `2ac19276dac9a8358638d80b7f5ef5ee29ab330845ffa8b5c35ce91ae161d4a7` | `2ac19276dac9a8358638d80b7f5ef5ee29ab330845ffa8b5c35ce91ae161d4a7` |
| `core/casos/ubicacion.py` | Lectura dirigida | `06915b0f178ed20e174340659c3163bcf097d72f7e13b1bae1b30f1a34d6956b` | `06915b0f178ed20e174340659c3163bcf097d72f7e13b1bae1b30f1a34d6956b` |
| `core/casos/workspace_adopcion.py` | Barrido léxico | `6ff97af98232b8e98e30b262aadd249e33c5236c5c34c116abc941c91c39b235` | `6ff97af98232b8e98e30b262aadd249e33c5236c5c34c116abc941c91c39b235` |
| `core/casos/workspace_model.py` | Lectura dirigida | `63c13355811766506eab61f0bf34a3a2a1a23cd29382a4a2ada6e94c29fdefca` | `63c13355811766506eab61f0bf34a3a2a1a23cd29382a4a2ada6e94c29fdefca` |
| `core/casos/workspace_registry.py` | Lectura dirigida | `ef03d8b59875b4aee10ad7486f6e9cbec5737b3ceeb48e2092a5e008fc1b1e0b` | `ef03d8b59875b4aee10ad7486f6e9cbec5737b3ceeb48e2092a5e008fc1b1e0b` |
| `core/casos/workspace_resolver.py` | Lectura dirigida | `bae8d436b314e5ca7ce5af5100672758c7eb722f75e00855f17963d7a2a22436` | `bae8d436b314e5ca7ce5af5100672758c7eb722f75e00855f17963d7a2a22436` |
| `core/catalogo_documental.py` | Barrido léxico | `b2720bffa3a697a12e9678ab6ead81b4e873d993fbfb3d7c5d8963c8039b83e4` | `b2720bffa3a697a12e9678ab6ead81b4e873d993fbfb3d7c5d8963c8039b83e4` |
| `core/ciudades.py` | Barrido léxico | `06b6462631001e216f76fbdbd92b27a60ec68bc332367089add277e30bfcd06e` | `06b6462631001e216f76fbdbd92b27a60ec68bc332367089add277e30bfcd06e` |
| `core/config.py` | Lectura dirigida | `b1ac9e68320dca7a08217570093216d7403b598c37fce40f6250a3f443bf878d` | `b1ac9e68320dca7a08217570093216d7403b598c37fce40f6250a3f443bf878d` |
| `core/conjunto_detector.py` | Barrido léxico | `8d6de53413977bbedd1e526aeb773e329c8a342b1f7d1d648951f7c09b1c72d3` | `8d6de53413977bbedd1e526aeb773e329c8a342b1f7d1d648951f7c09b1c72d3` |
| `core/crm_atlas.py` | Barrido léxico | `3d3f0b18d8abc25d78bebdf91fa836d900a773ed093551d2db08db0d6e087004` | `3d3f0b18d8abc25d78bebdf91fa836d900a773ed093551d2db08db0d6e087004` |
| `core/crm_ficha.py` | Barrido léxico | `7c955112ef03848975126a23bdf5a75805ae4038b25d0cbb6d4d2cf12eba1816` | `7c955112ef03848975126a23bdf5a75805ae4038b25d0cbb6d4d2cf12eba1816` |
| `core/crm_ficha_validacion.py` | Barrido léxico | `5ff7ad48cd0b20375a48a5550305201a1b17d193a203e1a2e53da9c7081320e9` | `5ff7ad48cd0b20375a48a5550305201a1b17d193a203e1a2e53da9c7081320e9` |
| `core/demanda_generator.py` | Barrido léxico | `78e9192d0d585abafda08b7cdf257018625e5376c881c41dc5b801714bd7dc8e` | `78e9192d0d585abafda08b7cdf257018625e5376c881c41dc5b801714bd7dc8e` |
| `core/email_atomize/__init__.py` | Barrido léxico | `2f28e9003efe920923d17bb11e4f2d87944ec098771294a8ede080716b17fa07` | `2f28e9003efe920923d17bb11e4f2d87944ec098771294a8ede080716b17fa07` |
| `core/email_atomize/_segmenter.py` | Barrido léxico | `0f19947796b46fdaecf83f97085a0861d8c0098e4f9f979df144dddf7e65a330` | `0f19947796b46fdaecf83f97085a0861d8c0098e4f9f979df144dddf7e65a330` |
| `core/email_atomize/attachments.py` | Barrido léxico | `e7509df3952e8a42ff7b2c7b4258580e8d51252a00a66afb842a84bad6b36d4b` | `e7509df3952e8a42ff7b2c7b4258580e8d51252a00a66afb842a84bad6b36d4b` |
| `core/email_atomize/bodies.py` | Barrido léxico | `e025265773b6b111ea5b78b2679eaf82cc53d9e231473ecf77cd8a98a980285a` | `e025265773b6b111ea5b78b2679eaf82cc53d9e231473ecf77cd8a98a980285a` |
| `core/email_atomize/contaminacion.py` | Barrido léxico | `ed10d3f595518c0312622b33202f6d1bbd55029131adaff441fb4e784b59fee0` | `ed10d3f595518c0312622b33202f6d1bbd55029131adaff441fb4e784b59fee0` |
| `core/email_atomize/corpus.py` | Barrido léxico | `2324568b7ca978c8fc410a99efe7b5faa17669f1fb36ad5c451ec3cc4b35f974` | `2324568b7ca978c8fc410a99efe7b5faa17669f1fb36ad5c451ec3cc4b35f974` |
| `core/email_atomize/dedup.py` | Barrido léxico | `8a5b67543758500f4d0ea310b878823eeab4ba1700316c0db653877abe75f6a0` | `8a5b67543758500f4d0ea310b878823eeab4ba1700316c0db653877abe75f6a0` |
| `core/email_atomize/entregas.py` | Lectura dirigida | `8c766524b2c4a379820b0aaefcddec2ea05c32264bfb0d9510324f937cd73042` | `8c766524b2c4a379820b0aaefcddec2ea05c32264bfb0d9510324f937cd73042` |
| `core/email_atomize/extract.py` | Barrido léxico | `6ffa66523f3b7f42c6c1bb9918161ee62cc563e4187e9a9ce70934bd6cb0bd7a` | `6ffa66523f3b7f42c6c1bb9918161ee62cc563e4187e9a9ce70934bd6cb0bd7a` |
| `core/email_atomize/headers.py` | Barrido léxico | `68cc66de258c7821acc6053fe9d5859e4aaf9b5e48411a4cc05053aeb8a7b08f` | `68cc66de258c7821acc6053fe9d5859e4aaf9b5e48411a4cc05053aeb8a7b08f` |
| `core/email_atomize/historial.py` | Barrido léxico | `cc2635abe2dce2d98d7f96b355fa9d509bc8de9319382df9070d30333539b5c4` | `cc2635abe2dce2d98d7f96b355fa9d509bc8de9319382df9070d30333539b5c4` |
| `core/email_atomize/identidades.py` | Barrido léxico | `73955081707be0fa708125047918506b9b9f0ab2bc8071092ebaa4610d8cfd38` | `73955081707be0fa708125047918506b9b9f0ab2bc8071092ebaa4610d8cfd38` |
| `core/email_atomize/ids.py` | Barrido léxico | `eed1d59378e65b2a90682e528eda5f1a20114d6dc18c858a9d11ed92069532e0` | `eed1d59378e65b2a90682e528eda5f1a20114d6dc18c858a9d11ed92069532e0` |
| `core/email_atomize/inline.py` | Barrido léxico | `a6f638eaac9ff319448c80f61e7717d53be5a85428a389b142c05ec22cb63023` | `a6f638eaac9ff319448c80f61e7717d53be5a85428a389b142c05ec22cb63023` |
| `core/email_atomize/model.py` | Barrido léxico | `e1faf5f64ee7f8e464bd2f25efc495d1bba7264e0795077332b0fde71d22adb2` | `e1faf5f64ee7f8e464bd2f25efc495d1bba7264e0795077332b0fde71d22adb2` |
| `core/email_atomize/pipeline.py` | Barrido léxico | `c74d91a384a92b2c78cdc700bcabab1dcabbf4563056166f4ca98672be748358` | `c74d91a384a92b2c78cdc700bcabab1dcabbf4563056166f4ca98672be748358` |
| `core/email_atomize/render.py` | Barrido léxico | `b837014d539acf58aa16dcc8bdc1e893faa0481604c5779e25e3def67c71044d` | `b837014d539acf58aa16dcc8bdc1e893faa0481604c5779e25e3def67c71044d` |
| `core/email_atomize/vistas.py` | Barrido léxico | `174be455af3e0a73ca255b5bbdff5e2f14807d67875622de50701f70a3a022f4` | `174be455af3e0a73ca255b5bbdff5e2f14807d67875622de50701f70a3a022f4` |
| `core/email_export.py` | Barrido léxico | `7e0af03ec3e4ca12934d02b8c1960943cf42f6962236ab77ce3520cd07137efe` | `7e0af03ec3e4ca12934d02b8c1960943cf42f6962236ab77ce3520cd07137efe` |
| `core/extractor.py` | Barrido léxico | `839444880695a803d025ba70312520e4198a5b1af5e5d727444df0718a4b7f11` | `839444880695a803d025ba70312520e4198a5b1af5e5d727444df0718a4b7f11` |
| `core/gmail_source.py` | Barrido léxico | `bf16fb73cadb967218c97e7b0b06da9ac7ea11870f9987ac5f31f6c210c2b52d` | `bf16fb73cadb967218c97e7b0b06da9ac7ea11870f9987ac5f31f6c210c2b52d` |
| `core/intake_drive.py` | Lectura dirigida | `37867ee99db1040353231e147fcbb82d0279a6af63445eef78b5a2696018edf6` | `37867ee99db1040353231e147fcbb82d0279a6af63445eef78b5a2696018edf6` |
| `core/intake_log.py` | Barrido léxico | `54e706542a336aa55339233cac8a789f938a8191c614ba37dc33c6d31ac46497` | `54e706542a336aa55339233cac8a789f938a8191c614ba37dc33c6d31ac46497` |
| `core/intake_lotes.py` | Lectura dirigida | `16a67ad072150e687d820dfa615e1431b57280234d13df697833ec6ad25ec016` | `16a67ad072150e687d820dfa615e1431b57280234d13df697833ec6ad25ec016` |
| `core/intake_manifest.py` | Barrido léxico | `f51e32d3cee495c53d4b5e8f37ac77ad4c24250fb270e12325144ea9cab7f769` | `f51e32d3cee495c53d4b5e8f37ac77ad4c24250fb270e12325144ea9cab7f769` |
| `core/intake_manual.py` | Lectura dirigida | `44902f1930a50f211ce8e24586072ad92feaece9a68deb51d80d9ed9985917b5` | `44902f1930a50f211ce8e24586072ad92feaece9a68deb51d80d9ed9985917b5` |
| `core/intake_utils.py` | Barrido léxico | `29f37227f2fc7647b83078c3e87e7c90ef09349b64d2589a6c30722b9e9cae90` | `29f37227f2fc7647b83078c3e87e7c90ef09349b64d2589a6c30722b9e9cae90` |
| `core/inventory.py` | Barrido léxico | `f95f155ca3992f7cf1d805a200644959d87b0b228df6ac9a81ca8a440c61f48f` | `f95f155ca3992f7cf1d805a200644959d87b0b228df6ac9a81ca8a440c61f48f` |
| `core/judicial_classifier.py` | Barrido léxico | `545001589b9f4ddf8f823b513c5f3e4cea81a9b6d0a91709f7ba2335ff862178` | `545001589b9f4ddf8f823b513c5f3e4cea81a9b6d0a91709f7ba2335ff862178` |
| `core/judicial_intake.py` | Barrido léxico | `d92a25412b2e686896896d2a4c924c4dc5e3d8eac856ceb5e8d62d143600eb43` | `d92a25412b2e686896896d2a4c924c4dc5e3d8eac856ceb5e8d62d143600eb43` |
| `core/keepalive.py` | Barrido léxico | `1da974ed723421abc990689cb96934177c6a399ec374902551e2c127eeb210db` | `1da974ed723421abc990689cb96934177c6a399ec374902551e2c127eeb210db` |
| `core/linker.py` | Barrido léxico | `d51e58c36ffa86cc9f54b6914148492811fd3880a5a8537f6d9ed96fe3c18e22` | `d51e58c36ffa86cc9f54b6914148492811fd3880a5a8537f6d9ed96fe3c18e22` |
| `core/llm.py` | Barrido léxico | `5b05be6699a8b6cf45ef52517768b6ae22fe8c7fd8d5e4fe173b25d95304cc87` | `5b05be6699a8b6cf45ef52517768b6ae22fe8c7fd8d5e4fe173b25d95304cc87` |
| `core/llm_cloud.py` | Barrido léxico | `b3584e87c153a89a7bcf29271cc1031ea9e74c8589e1bbc9e9035b3ead4eced3` | `b3584e87c153a89a7bcf29271cc1031ea9e74c8589e1bbc9e9035b3ead4eced3` |
| `core/llm_local.py` | Barrido léxico | `1d91b4b38bdfa71936513018f71c4ce49ed87b77e6a2a21980a62dca45279efb` | `1d91b4b38bdfa71936513018f71c4ce49ed87b77e6a2a21980a62dca45279efb` |
| `core/local_organizer.py` | Barrido léxico | `21e6da3d4554f2f79f78c0660d259ece2833ef2f74c9bcac1993a7fb80f9f563` | `21e6da3d4554f2f79f78c0660d259ece2833ef2f74c9bcac1993a7fb80f9f563` |
| `core/markdown_generator.py` | Barrido léxico | `14ffba5b2e67064923ded5179318a33abbafbe2801b75b9012b0654b2db0206f` | `14ffba5b2e67064923ded5179318a33abbafbe2801b75b9012b0654b2db0206f` |
| `core/migrar_layout.py` | Barrido léxico | `d54953e332c85f62491e87bac13609fa13d032f756b227340f073e86738ae8f0` | `d54953e332c85f62491e87bac13609fa13d032f756b227340f073e86738ae8f0` |
| `core/migrar_nombres_informe.py` | Barrido léxico | `ab9266575aae4af7dc43d9384cf3da64a129fd88a232eb21146e66836ee52826` | `ab9266575aae4af7dc43d9384cf3da64a129fd88a232eb21146e66836ee52826` |
| `core/ocr_per_page.py` | Barrido léxico | `d1c662dcc3b94594e970c5272910858fe3863d360e4c1755831ff3092fc34bb7` | `d1c662dcc3b94594e970c5272910858fe3863d360e4c1755831ff3092fc34bb7` |
| `core/ocurrencias_crm.py` | Barrido léxico | `f3e2d9eb7290d7e5089de4891601f621549e1efe13298ea983fc8127386b8020` | `f3e2d9eb7290d7e5089de4891601f621549e1efe13298ea983fc8127386b8020` |
| `core/pdf_paginas.py` | Barrido léxico | `92cb27bc144c8f66c866ecd8cae13aa14a929a559e11a7e04210bf63aa20e967` | `92cb27bc144c8f66c866ecd8cae13aa14a929a559e11a7e04210bf63aa20e967` |
| `core/pipeline.py` | Barrido léxico | `a8046df5bcbebe08804a1221415a7a4c8902f4d6f88d46caf21e622f127ce436` | `a8046df5bcbebe08804a1221415a7a4c8902f4d6f88d46caf21e622f127ce436` |
| `core/procurador_intake.py` | Barrido léxico | `03a624a318c3a722546bd4f3552354790b22dbd67fbe2731a3dbe09681ffed7c` | `03a624a318c3a722546bd4f3552354790b22dbd67fbe2731a3dbe09681ffed7c` |
| `core/procurador_review.py` | Barrido léxico | `58ffc88e223c7fdc320b0118aeaf87bc6825f378cd366794618f809a9b241958` | `58ffc88e223c7fdc320b0118aeaf87bc6825f378cd366794618f809a9b241958` |
| `core/procurador_runner.py` | Barrido léxico | `23283113fd2037ea7fca73e4f6d3547d705900702333564e83f57f903841c68f` | `23283113fd2037ea7fca73e4f6d3547d705900702333564e83f57f903841c68f` |
| `core/procurador_search.py` | Barrido léxico | `b33af7cac30a879ba676e9e7f2f3a841d371fc20d7a8bed45283bcc499e5d700` | `b33af7cac30a879ba676e9e7f2f3a841d371fc20d7a8bed45283bcc499e5d700` |
| `core/repository_checkout.py` | Barrido léxico | `8232b9336d99ff13a8eda50a1b0e1dfea7a85a65f323f207dc150b0128c3f963` | `8232b9336d99ff13a8eda50a1b0e1dfea7a85a65f323f207dc150b0128c3f963` |
| `core/sala_lectura.py` | Barrido léxico | `f34d1deb6a4c164fde17aff2d0ea74ac18f2b42dd0f1094902961b4a7fb4e35d` | `f34d1deb6a4c164fde17aff2d0ea74ac18f2b42dd0f1094902961b4a7fb4e35d` |
| `core/sala_maquina.py` | Barrido léxico | `2a159783be6f5d8ba6e9ccd8f0c9141c5e0e3ac1581eeb3bccb7544e4bb164fb` | `2a159783be6f5d8ba6e9ccd8f0c9141c5e0e3ac1581eeb3bccb7544e4bb164fb` |
| `core/scorer.py` | Barrido léxico | `ec0ffcc91a35bfdc7b6698d2e5b4044f88a18a1582ded1298c28f1e423f73334` | `ec0ffcc91a35bfdc7b6698d2e5b4044f88a18a1582ded1298c28f1e423f73334` |
| `core/share_drive.py` | Barrido léxico | `16a8c694c5099d7135ccea846574367a0e7cf918b5c949097c84bbd6898d3362` | `16a8c694c5099d7135ccea846574367a0e7cf918b5c949097c84bbd6898d3362` |
| `core/split_documental.py` | Barrido léxico | `af61e6658539f20bc0004c27d1a46475ea646228f5abbc2e333a79756a9f1785` | `af61e6658539f20bc0004c27d1a46475ea646228f5abbc2e333a79756a9f1785` |
| `core/sudespacho_create.py` | Barrido léxico | `cdb511008aec137ba37477bbaee1f5939e8ce20dec38fc3700ac7e9418630ce0` | `cdb511008aec137ba37477bbaee1f5939e8ce20dec38fc3700ac7e9418630ce0` |
| `core/sudespacho_relations.py` | Barrido léxico | `229b14d5f35d3e49da91f1a0e2d98c592e8d9ef8bb20518b027ef8044bb63e69` | `229b14d5f35d3e49da91f1a0e2d98c592e8d9ef8bb20518b027ef8044bb63e69` |
| `core/sync.py` | Lectura dirigida | `287146049fe2178d682115af45c0e961367266c87848143ffcf1ff97db823869` | `287146049fe2178d682115af45c0e961367266c87848143ffcf1ff97db823869` |
| `core/sync_sudespacho.py` | Barrido léxico | `22ee7022303aaa919f3dc79bd0642b73685f9cfe2a82fb84f3cd7aef41c1455a` | `22ee7022303aaa919f3dc79bd0642b73685f9cfe2a82fb84f3cd7aef41c1455a` |
| `core/sync_sudespacho_legacy.py` | Barrido léxico | `ad994b121aa0bbbf2c505cc370fcb4c7ed7c53d2132a50fa365ae791ec89fa7b` | `ad994b121aa0bbbf2c505cc370fcb4c7ed7c53d2132a50fa365ae791ec89fa7b` |
| `core/utils.py` | Lectura dirigida | `58a3eb59fddab37390e349763afe2d851e63868730c5df8e762e726934789721` | `58a3eb59fddab37390e349763afe2d851e63868730c5df8e762e726934789721` |
| `core/viability.py` | Barrido léxico | `2d1a309cd8032c873080e0bb7b676017b1c343bd46b177d85d0e41db4e1f9029` | `2d1a309cd8032c873080e0bb7b676017b1c343bd46b177d85d0e41db4e1f9029` |
| `core/whatsapp_atomize/__init__.py` | Barrido léxico | `b06adb08645b237cfab9449038692cfd5b78cc3f22ae8fa863ddfcebb30f07b2` | `b06adb08645b237cfab9449038692cfd5b78cc3f22ae8fa863ddfcebb30f07b2` |
| `core/whatsapp_atomize/adjuntos.py` | Barrido léxico | `4450f52c88834c0f7b65c40462624bb3f137c19458badaff4fa9aa91dbaf8f6d` | `4450f52c88834c0f7b65c40462624bb3f137c19458badaff4fa9aa91dbaf8f6d` |
| `core/whatsapp_atomize/corpus.py` | Barrido léxico | `2456f68461c0ceff66c592955cc557b6b823456154321add4ff2a9c6119f7f36` | `2456f68461c0ceff66c592955cc557b6b823456154321add4ff2a9c6119f7f36` |
| `core/whatsapp_atomize/identidades.py` | Barrido léxico | `fe500b91a2ad0ad0f5a579e259b6a7b4c59522211c7338e30a8004c90df15a09` | `fe500b91a2ad0ad0f5a579e259b6a7b4c59522211c7338e30a8004c90df15a09` |
| `core/whatsapp_atomize/ids.py` | Barrido léxico | `a19640492314ba0178e3bf3db1645fb322bef57d45e466b8455f9a87320b1d90` | `a19640492314ba0178e3bf3db1645fb322bef57d45e466b8455f9a87320b1d90` |
| `core/whatsapp_atomize/model.py` | Barrido léxico | `5ca18eddc916bf0f13110e3482f6b9b3213128a5aa0b4838489f5d96573ad7ca` | `5ca18eddc916bf0f13110e3482f6b9b3213128a5aa0b4838489f5d96573ad7ca` |
| `core/whatsapp_atomize/pipeline.py` | Barrido léxico | `dc11c297e98068c0a48f5bcfa608f826f35b2dbbfaf6531e9d09ff78cab1cd34` | `dc11c297e98068c0a48f5bcfa608f826f35b2dbbfaf6531e9d09ff78cab1cd34` |
| `core/whatsapp_atomize/propuesta_identidades.py` | Barrido léxico | `203d4f28229c5fd1008d124dad32fbe41233cb5eaf751eedcd692272d0b57703` | `203d4f28229c5fd1008d124dad32fbe41233cb5eaf751eedcd692272d0b57703` |
| `core/whatsapp_atomize/reconstruccion.py` | Barrido léxico | `6bdd0fa2b7e55e7bd6bdcee25d0bc12d9266821e98b690637d8258c68da09a73` | `6bdd0fa2b7e55e7bd6bdcee25d0bc12d9266821e98b690637d8258c68da09a73` |
| `core/whatsapp_atomize/render.py` | Barrido léxico | `65e328048140e411fa50a920b3b2260deae93cca896a64a96c981afd7bd99042` | `65e328048140e411fa50a920b3b2260deae93cca896a64a96c981afd7bd99042` |
| `core/whatsapp_export.py` | Barrido léxico | `bc6e074207a8c29a6c71dffb7f63ec56d0bd3eb8602989ae0455f509daa4f44e` | `bc6e074207a8c29a6c71dffb7f63ec56d0bd3eb8602989ae0455f509daa4f44e` |
| `core/whatsapp_intake.py` | Barrido léxico | `0553ac2fc1e8144a71e8ada62fe3e7ae844b7f2c27c1ae2e8196606c1eb20dd8` | `0553ac2fc1e8144a71e8ada62fe3e7ae844b7f2c27c1ae2e8196606c1eb20dd8` |
| `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md` | Lectura dirigida | `18237e593a140edf4188c1680105070965d980932b3115b000528180fe7ee619` | `18237e593a140edf4188c1680105070965d980932b3115b000528180fe7ee619` |
| `docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-design.md` | Lectura dirigida | `51f332183b898f62bcd9d8b62146a679708723255045963dccfa1d999c20e031` | `51f332183b898f62bcd9d8b62146a679708723255045963dccfa1d999c20e031` |
| `pyproject.toml` | Lectura dirigida | `bb892fe7f7da0c6d5f33827fe4b8b31d030f025c2e4d7e1ce738bf0f9a225a1a` | `bb892fe7f7da0c6d5f33827fe4b8b31d030f025c2e4d7e1ce738bf0f9a225a1a` |
| `scripts/__init__.py` | Barrido léxico | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `scripts/_debug_csrf.py` | Barrido léxico | `4390ff2f2abe29131d4bb45913cfca41376b101feb218a668adbc42628113143` | `4390ff2f2abe29131d4bb45913cfca41376b101feb218a668adbc42628113143` |
| `scripts/_verify_pull_649.py` | Barrido léxico | `84d7233b611ebdf3e9d4636777d1054600829022e7ee19e133f439ad7bca6137` | `84d7233b611ebdf3e9d4636777d1054600829022e7ee19e133f439ad7bca6137` |
| `scripts/abrir_caso.py` | Lectura dirigida | `bcb937066b9211dfa903a08d0ff14635c9e10ddb5d90b19a1c178a6029804375` | `bcb937066b9211dfa903a08d0ff14635c9e10ddb5d90b19a1c178a6029804375` |
| `scripts/anonimizar_caso.py` | Barrido léxico | `59849fa77121a696c47e9b5256497f74f7a3f294a08a44d3b0131e0b0b2c7d08` | `59849fa77121a696c47e9b5256497f74f7a3f294a08a44d3b0131e0b0b2c7d08` |
| `scripts/atomize_emails.py` | Barrido léxico | `638281cb16415a520bce39129a894fa107320d0670da885c33dc2ba2f9ccf26b` | `638281cb16415a520bce39129a894fa107320d0670da885c33dc2ba2f9ccf26b` |
| `scripts/atomize_whatsapp.py` | Barrido léxico | `5ecd56eaa7c71940bc0b5486ee6d6ae35cc977ad26c9b2da85e179319ac7c0e1` | `5ecd56eaa7c71940bc0b5486ee6d6ae35cc977ad26c9b2da85e179319ac7c0e1` |
| `scripts/audit_correos_no_separados.py` | Barrido léxico | `dd9633a079619390737868e6458d476d5bcda5c7220c46a09afb25b367a67e10` | `dd9633a079619390737868e6458d476d5bcda5c7220c46a09afb25b367a67e10` |
| `scripts/audit_ev_folder_names.py` | Barrido léxico | `c8ca50dd850dea887ebfddebae7157e2a884a270a1958440de4114b7a7324a4d` | `c8ca50dd850dea887ebfddebae7157e2a884a270a1958440de4114b7a7324a4d` |
| `scripts/audit_judicial_tags.py` | Barrido léxico | `58e38b6953c89e786033240820fab4eda3fc4a8960cd9de6031b4a3257d9782f` | `58e38b6953c89e786033240820fab4eda3fc4a8960cd9de6031b4a3257d9782f` |
| `scripts/audit_referencias_casos.py` | Barrido léxico | `eec0707649b02177aa43356d0b405a1909a0678f8b6d9d6f29d095184b2d19ac` | `eec0707649b02177aa43356d0b405a1909a0678f8b6d9d6f29d095184b2d19ac` |
| `scripts/bulk_pull_expedientes.py` | Barrido léxico | `5119931a77d5042fcd54d4e37f22f298176db30f97557cf74165d59cbe1585f8` | `5119931a77d5042fcd54d4e37f22f298176db30f97557cf74165d59cbe1585f8` |
| `scripts/capturar_delta.py` | Barrido léxico | `77bd9c6ef853bcd804f6abdeb4bb02741c9e899a4ce60b12361207a53a347969` | `77bd9c6ef853bcd804f6abdeb4bb02741c9e899a4ce60b12361207a53a347969` |
| `scripts/check_skills.py` | Barrido léxico | `b04df7406b6d092fba03b5eee64c81f20eed45901617e6ffcf4c493c5a9d1032` | `b04df7406b6d092fba03b5eee64c81f20eed45901617e6ffcf4c493c5a9d1032` |
| `scripts/clasificacion_localizador.py` | Barrido léxico | `bf481373529d846e71fcefaa99693da7ea298f6d5fb69b09e180201f9b4ba4e1` | `bf481373529d846e71fcefaa99693da7ea298f6d5fb69b09e180201f9b4ba4e1` |
| `scripts/create_judicial_tags.py` | Barrido léxico | `8e80e5c7d6e857c157bb0ed365cdafa4fc3093ee9b9649780e44c033297658a8` | `8e80e5c7d6e857c157bb0ed365cdafa4fc3093ee9b9649780e44c033297658a8` |
| `scripts/crm_atlas.py` | Barrido léxico | `0b82b3a5f7f0a9a947bdf3b923bd5df5407f77afebb673cf0a40b163b3651af1` | `0b82b3a5f7f0a9a947bdf3b923bd5df5407f77afebb673cf0a40b163b3651af1` |
| `scripts/crm_ficha.py` | Barrido léxico | `8cfe0c7c44577a02b9e39449335de0f3abac6a2183df4ed9d03c5e3bde255422` | `8cfe0c7c44577a02b9e39449335de0f3abac6a2183df4ed9d03c5e3bde255422` |
| `scripts/crm_ficha_validar.py` | Barrido léxico | `502810adfe950bfa994b7aadf3ec854e3a6dabc33cc41e80b5943c24d1d96010` | `502810adfe950bfa994b7aadf3ec854e3a6dabc33cc41e80b5943c24d1d96010` |
| `scripts/detectar_conjuntos.py` | Barrido léxico | `c10dd1599959be906adaddfcc2c09d1ba59673a263701834ec875f4732063069` | `c10dd1599959be906adaddfcc2c09d1ba59673a263701834ec875f4732063069` |
| `scripts/detectar_ocr_ciego.py` | Barrido léxico | `254fab89d4079bc2655b36bf3fe2f931154f27f8182e9edf56b7d1b08f49c376` | `254fab89d4079bc2655b36bf3fe2f931154f27f8182e9edf56b7d1b08f49c376` |
| `scripts/diag_cliente_propio.py` | Barrido léxico | `6f0f79f36ce68ee9b13e7603929828fa9b46396ffb10c92ba5ad023027817c78` | `6f0f79f36ce68ee9b13e7603929828fa9b46396ffb10c92ba5ad023027817c78` |
| `scripts/diag_drive_autofill.py` | Barrido léxico | `847dae71cd2eca2d7c4c63bd05459ec0f5bd9144c482ffc7e80413f1fef113ff` | `847dae71cd2eca2d7c4c63bd05459ec0f5bd9144c482ffc7e80413f1fef113ff` |
| `scripts/diag_expediente_648.py` | Barrido léxico | `ec453e47405e891299730f78fb5617aef9401b5919f7a211c2e51e038d3d7ab0` | `ec453e47405e891299730f78fb5617aef9401b5919f7a211c2e51e038d3d7ab0` |
| `scripts/diag_num_extrajudicial.py` | Barrido léxico | `e3d07ed2685f0b0087d5ca3a4a07a65a3d9188e47e0c913306c6b71ca16c4c56` | `e3d07ed2685f0b0087d5ca3a4a07a65a3d9188e47e0c913306c6b71ca16c4c56` |
| `scripts/diag_presigned_download.py` | Barrido léxico | `8f5cdb806adab0141e2c51c607030480e3b1239148340fb8dbed17b323f8449d` | `8f5cdb806adab0141e2c51c607030480e3b1239148340fb8dbed17b323f8449d` |
| `scripts/eval_matcher_batch.py` | Barrido léxico | `ea76cac1fdc6fb1c3095710ac762d4785d7b2893a1842ef7994a03be26513dfa` | `ea76cac1fdc6fb1c3095710ac762d4785d7b2893a1842ef7994a03be26513dfa` |
| `scripts/export_label_emails.py` | Barrido léxico | `761cb046a5d952980887a548784cd55464914a95f775dade4b6f0f162d9e96e3` | `761cb046a5d952980887a548784cd55464914a95f775dade4b6f0f162d9e96e3` |
| `scripts/health_check.py` | Barrido léxico | `89bb56b8bcd8f60e3542d47d5eec4f0207569888df872b0c1338ed462f03dd9f` | `89bb56b8bcd8f60e3542d47d5eec4f0207569888df872b0c1338ed462f03dd9f` |
| `scripts/init_caso.py` | Barrido léxico | `71cf2311290ddebb9b9996e7e4d39ded584b5f6656b0d9f45f8ff367f4b69328` | `71cf2311290ddebb9b9996e7e4d39ded584b5f6656b0d9f45f8ff367f4b69328` |
| `scripts/intake_procuradores.py` | Barrido léxico | `e3e5a40bcbab94b5966ccdbfa02f91a30cb9ffccdf5d0e7c6580680cae0144cd` | `e3e5a40bcbab94b5966ccdbfa02f91a30cb9ffccdf5d0e7c6580680cae0144cd` |
| `scripts/inventario_localizador.py` | Barrido léxico | `1ed39f7bde8c01806cb3a924289a17c96e5ffa3c8da7fc56583ab6fd17b03b81` | `1ed39f7bde8c01806cb3a924289a17c96e5ffa3c8da7fc56583ab6fd17b03b81` |
| `scripts/limpieza_post_audit.py` | Barrido léxico | `f022ed97a6d2cef1cce81b42683028044c7da9252ad408d02dea786452feaf3c` | `f022ed97a6d2cef1cce81b42683028044c7da9252ad408d02dea786452feaf3c` |
| `scripts/migrar_layout_intake.py` | Barrido léxico | `858cba5db99119328a6f6f5a17150ca334a2f54ed8cfb4191949e18c4612119e` | `858cba5db99119328a6f6f5a17150ca334a2f54ed8cfb4191949e18c4612119e` |
| `scripts/migrar_nombres_informe.py` | Barrido léxico | `e25fc001f1007f341b61bd7505a479169002d5a9c8c210b9e7dd40ff10cdf9ec` | `e25fc001f1007f341b61bd7505a479169002d5a9c8c210b9e7dd40ff10cdf9ec` |
| `scripts/migrate_05crm_buckets.py` | Barrido léxico | `92d9c1f976c9686fa7c734e9f0614ad7e8232c50720f3ff226b7dcf6e9953cf9` | `92d9c1f976c9686fa7c734e9f0614ad7e8232c50720f3ff226b7dcf6e9953cf9` |
| `scripts/migrate_to_city_structure.py` | Barrido léxico | `f4ecbfd5956089a3b8d4ee78e055298f04cf1e52018318fa5736e0981a1aa7c4` | `f4ecbfd5956089a3b8d4ee78e055298f04cf1e52018318fa5736e0981a1aa7c4` |
| `scripts/motor_mejora.py` | Barrido léxico | `8acd6b3cea3c5a5fd8b882e4134fec687a2d150e710f6fb2ef7b24dbce6882db` | `8acd6b3cea3c5a5fd8b882e4134fec687a2d150e710f6fb2ef7b24dbce6882db` |
| `scripts/ocr_textless_pdfs.py` | Barrido léxico | `ca741b9b0a1c33ca4a2831295805563e45c63a8c73e0c752fb570d846f9d81b5` | `ca741b9b0a1c33ca4a2831295805563e45c63a8c73e0c752fb570d846f9d81b5` |
| `scripts/organizar_local.py` | Barrido léxico | `c03525cda0b89e36e3f1028ecc15b4ead4d0e550984f279552f66054dd6bffbc` | `c03525cda0b89e36e3f1028ecc15b4ead4d0e550984f279552f66054dd6bffbc` |
| `scripts/package_plugin.py` | Barrido léxico | `c38dd57c12e955c8cf0ad04c930921f3ac16e9aa715ca244c2d1c99671c6dac3` | `c38dd57c12e955c8cf0ad04c930921f3ac16e9aa715ca244c2d1c99671c6dac3` |
| `scripts/package_skill.py` | Barrido léxico | `9a722af1db82c7f9452957174a3748c0ebbedbf97407dedd7137f8f4513b39e8` | `9a722af1db82c7f9452957174a3748c0ebbedbf97407dedd7137f8f4513b39e8` |
| `scripts/precommit_leak_guard.py` | Barrido léxico | `6228e70a3677af7a038e8fd878f8d225be29814bfbdee307880c2b77adea4c46` | `6228e70a3677af7a038e8fd878f8d225be29814bfbdee307880c2b77adea4c46` |
| `scripts/probe_gdocu.py` | Barrido léxico | `3ac89d6b0f3e99b3783cda500c47f8022670bccb0b10074f0291bc6cb1e132db` | `3ac89d6b0f3e99b3783cda500c47f8022670bccb0b10074f0291bc6cb1e132db` |
| `scripts/probe_gdocu_fecha.py` | Barrido léxico | `5f67c272f298af134c540fa83ed54c4b71171dbf9ddf8170d99df95d1936b762` | `5f67c272f298af134c540fa83ed54c4b71171dbf9ddf8170d99df95d1936b762` |
| `scripts/probe_gdocu_tree.py` | Barrido léxico | `1c65281abe864de1da12b5d3810b7052608a536b6d43460b36ecef583daeb1fa` | `1c65281abe864de1da12b5d3810b7052608a536b6d43460b36ecef583daeb1fa` |
| `scripts/redate_whatsapp_anexos.py` | Barrido léxico | `d6a20786c01c36f75b67de064603dccae6f691a03aab336bde2249ac6253ccb3` | `d6a20786c01c36f75b67de064603dccae6f691a03aab336bde2249ac6253ccb3` |
| `scripts/regen_fixture_sars1.py` | Barrido léxico | `bfc4d9f24c23d702408e02189465486c5344075bb93c57898acf8e1030b2ff00` | `bfc4d9f24c23d702408e02189465486c5344075bb93c57898acf8e1030b2ff00` |
| `scripts/remove_expediente_link.py` | Barrido léxico | `88cf2bc1acaf321883c9ad6845f3dfe4673f658b658664ff6f695bb4c7e7331c` | `88cf2bc1acaf321883c9ad6845f3dfe4673f658b658664ff6f695bb4c7e7331c` |
| `scripts/render_plantillas.py` | Barrido léxico | `fb50eb6255ecdfbc119feefbb8204de2535735a25cc91a1584ec68b1324f89ec` | `fb50eb6255ecdfbc119feefbb8204de2535735a25cc91a1584ec68b1324f89ec` |
| `scripts/repository_cli.py` | Lectura dirigida | `433ba204a159a2f6a2a16115cffbd2b540a1ff34825bc16b5655b631d49b6d49` | `433ba204a159a2f6a2a16115cffbd2b540a1ff34825bc16b5655b631d49b6d49` |
| `scripts/run_pipeline.py` | Barrido léxico | `e541f3a231ff8ad421e40bab8d0f090f535fa6a7a8941929dc7f4cfebf29f3ec` | `e541f3a231ff8ad421e40bab8d0f090f535fa6a7a8941929dc7f4cfebf29f3ec` |
| `scripts/sala_lectura.py` | Barrido léxico | `a92574148df8fd7bfe3e9a5bae0d91c658fb1600c76bfe439a8778bd6a1ed033` | `a92574148df8fd7bfe3e9a5bae0d91c658fb1600c76bfe439a8778bd6a1ed033` |
| `scripts/sala_maquina.py` | Barrido léxico | `368f8d57cab6dbc66b4ea004e74b53f2c9d4423ab4d45e3046fff57453ba588c` | `368f8d57cab6dbc66b4ea004e74b53f2c9d4423ab4d45e3046fff57453ba588c` |
| `scripts/scheduled_sync.py` | Barrido léxico | `2d8c1b4d6ff9a6054d8c3211468f3e4cf5d7cc287d4a1fa63d3b83cac7b533bd` | `2d8c1b4d6ff9a6054d8c3211468f3e4cf5d7cc287d4a1fa63d3b83cac7b533bd` |
| `scripts/session_close.py` | Barrido léxico | `7ed9759325e1b0a93609adca04bb4772f712c66365ecce438a2e775b4121c6cf` | `7ed9759325e1b0a93609adca04bb4772f712c66365ecce438a2e775b4121c6cf` |
| `scripts/sync_skill_helpers.py` | Barrido léxico | `2c2dd429b78192b7250689b3160e7779b03010899c116df52b8eb42d50a10731` | `2c2dd429b78192b7250689b3160e7779b03010899c116df52b8eb42d50a10731` |
| `scripts/sync_sudespacho.py` | Barrido léxico | `e6f84972c2e900fd60b5e6269902675117f5a1f78be523ca27f3973447d4b0f5` | `e6f84972c2e900fd60b5e6269902675117f5a1f78be523ca27f3973447d4b0f5` |
| `scripts/sync_taxonomia_skills.py` | Barrido léxico | `08705862a6b15e908a3f55febfe865c83d9dde66fe9dd66fd63c1460a7a987c6` | `08705862a6b15e908a3f55febfe865c83d9dde66fe9dd66fd63c1460a7a987c6` |
| `scripts/test_apikey_write.py` | Barrido léxico | `d45d88ffd2889c3bbd4b7db2872704fa839af38aa2dd6a1b45924845f01e2b7e` | `d45d88ffd2889c3bbd4b7db2872704fa839af38aa2dd6a1b45924845f01e2b7e` |
| `scripts/test_matcher_real.py` | Barrido léxico | `83c74edc08f5efbc0d26da39117bc5826b5ca45825c2ae6a08af6d4bce0439b6` | `83c74edc08f5efbc0d26da39117bc5826b5ca45825c2ae6a08af6d4bce0439b6` |
| `scripts/validate_skills.py` | Barrido léxico | `c82edffb281668c8d263f649793ef06e20cc4fcedb99c9e586ffcb556f5bf359` | `c82edffb281668c8d263f649793ef06e20cc4fcedb99c9e586ffcb556f5bf359` |
| `scripts/verify_city_layout.py` | Barrido léxico | `d5ea07ea0c8a40dc2453797baa6d19489beb96a99647414078d06a28e67c6aca` | `d5ea07ea0c8a40dc2453797baa6d19489beb96a99647414078d06a28e67c6aca` |
| `streamlit_app.py` | Lectura dirigida | `855540a3c89a5c1f8a54d50d1633117326466cf9e25487349b2682f1aa104542` | `855540a3c89a5c1f8a54d50d1633117326466cf9e25487349b2682f1aa104542` |
| `tests/__init__.py` | Test/fixture leído o ejecutado | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `tests/_barrera.py` | Test/fixture leído o ejecutado | `63accccfdb4e4ec35711105538c6dc2149c9f2558a5cc3ebafd450d62288270f` | `63accccfdb4e4ec35711105538c6dc2149c9f2558a5cc3ebafd450d62288270f` |
| `tests/conftest.py` | Test/fixture leído o ejecutado | `52909c1473a0701456ec252fab07d04e159aba7e8d81125f3394d00a1f6f6413` | `52909c1473a0701456ec252fab07d04e159aba7e8d81125f3394d00a1f6f6413` |
| `tests/test_case_locator.py` | Test/fixture leído o ejecutado | `b00a7add1b99231f3a7cceadddbcfdd0a9134a0b0f3810f04c08f5b7a34cfa7a` | `b00a7add1b99231f3a7cceadddbcfdd0a9134a0b0f3810f04c08f5b7a34cfa7a` |
| `tests/test_case_manager.py` | Test/fixture leído o ejecutado | `a6bbb09624365b46102bf27a9c2def729ac651044b4fdc8cc3f1577f18227324` | `a6bbb09624365b46102bf27a9c2def729ac651044b4fdc8cc3f1577f18227324` |
| `tests/test_intake_lotes.py` | Test/fixture leído o ejecutado | `d7da53982d00b9a12a45cba183a2e4b2e96b227254e33087d134c5966915208c` | `d7da53982d00b9a12a45cba183a2e4b2e96b227254e33087d134c5966915208c` |
| `tests/test_repository_checkout.py` | Barrido léxico | `88edebce04a6f01a5fb523e9becf550f04caa59111bd13aa4a10f20cb3b85dbf` | `88edebce04a6f01a5fb523e9becf550f04caa59111bd13aa4a10f20cb3b85dbf` |
| `tests/test_workspace_registry.py` | Barrido léxico | `465e92d03c57e5ef5b544a0e8f676298b09cc9209a05a4320296c8f08bde0d68` | `465e92d03c57e5ef5b544a0e8f676298b09cc9209a05a4320296c8f08bde0d68` |
| `tests/test_workspace_resolver.py` | Test/fixture leído o ejecutado | `7d4a79798aa2aa18d79f6314a4ad992e706e08cd64f866a0f2546e5c8f7e96a9` | `7d4a79798aa2aa18d79f6314a4ad992e706e08cd64f866a0f2546e5c8f7e96a9` |

### Huellas de los artefactos de ejecución del revisor

Estos hashes no sustituyen los del objeto. Identifican la transcripción y las salidas que soportan los hallazgos.

| Artefacto | SHA256 |
| --- | --- |
| `preparar_sonda.py` | `9f1d2eca89b43eb4258adba82dd081a890a5e1f2521497f9c26d49ee06740ca2` |
| `sonda.py` | `0ef6889de105996b5ba9df063c47098093de68c7ec269ed9d9b9847bd1d4fddd` |
| `sonda-salida.txt` | `467582568b2a6f43d395e2d63f7c9491e5762d489e697ca442773f6bc335f7df` |
| `pytest-salida.txt` | `49bc50cf4d28f0681964b71d077ed108cb29797c54cc02f8b664e9cf3eb02407` |
| `pytest-separado.txt` | `411eb58ffc5ffef174db01ac8c4718a34488e750b822e1fb4ce158614f59d401` |
| `hashes-apertura.csv` | `497370a22f8a912284a8f19bf640e5a3e0e3f43b6f55e29fba9c0e93cdcab8bb` |
| `hashes-cierre.csv` | `497370a22f8a912284a8f19bf640e5a3e0e3f43b6f55e29fba9c0e93cdcab8bb` |
| `core/case_manager.py` | `06cb812d97c4d7bfc7b1d3d3852afea86e1aa05b5a3bc1ac033ab0c72aefe1f9` |
| `c/core/case_manager.py` | `06cb812d97c4d7bfc7b1d3d3852afea86e1aa05b5a3bc1ac033ab0c72aefe1f9` |

El veredicto se apoya en escapes, contaminación de raíz y duplicación reproducidos, aun cuando los tests existentes seleccionados pasan. La adjudicación corresponde al autor.

NO-SHIP
<!-- informe-literal:fin:q9wm -->

## 2. Evidencia verificada por mí

Antes de que volviera el informe yo ya había encontrado, leyendo, dos de las cinco cosas — y
conviene decir cuáles, porque la coincidencia no las hace menos suyas: el revisor las **ejecutó**
y yo solo las había leído.

- **`move_to_city` como segundo sumidero (H-01).** Lo localicé con `git grep` de
  `mkdir(parents=True` y leí `case_locator.py:270-319`. **Pero mi conclusión fue la equivocada:**
  vi que la UI ofrece la ciudad en un `selectbox` de catálogo cerrado (`streamlit_app.py:1436`,
  con su «Catálogo cerrado. Para añadir una ciudad nueva, hablar con Nikolai») y **lo archivé
  como "considerado y no explotable"**. El revisor lo rebate en una línea que es la tesis de mi
  propio diseño: *el catálogo está en el envoltorio; no protege la API de core*. Usé como
  garantía exactamente la clase de cosa que este documento viene a arreglar.
- **La primitiva de contención (H-05 parcial).** Encontré `_bajo`/`_normal` en
  `case_mutex.py:182` y que `escritura.py:88` ya las usa, con su docstring diciendo que son
  léxicas «así que da lo mismo con el directorio creado o sin crear». De ahí salió el cambio de
  `resolve()` a léxico en la rev. 2 — **y ese cambio resultó estar mal**, ver el §3.

Verificado por mí en la fuente, con salida real:

```
H-02: exigir_sin_caracteres_de_ruta('') -> ''
H-02: validate_case_id('') SI lanza -> El case_id no puede estar vacío.
H-02: Path(root).is_relative_to(root) -> True
H-03: ensure_case no contiene ninguna comprobacion de CIUDADES
```

O sea: el «no vacío» **existía** en `validate_case_id` y quedó atrás al extraer media guarda el
día anterior; y `is_relative_to` incluye la igualdad, así que la raíz se cuela por los dos lados.

**Integridad del objeto:** el revisor dio los hashes al abrir y al cerrar, copió `core`,
`scripts` y `tests` a su propio directorio para ejecutar, y declaró expresamente no haber
escrito bajo el objeto.

## 3. Adjudicación

**Veredicto del revisor: `NO-SHIP`. Lo acepto entero. Cinco hallazgos, cinco confirmados, cero
refutados.** El diseño estaba mal en su **premisa central**, no en un detalle.

| # | Sev. | Qué falsó | Remediado en la rev. 2 |
|---|---|---|---|
| H-01 | ALTO (decisión) | `ensure_case` no es el único sumidero de depósito: `move_to_city` mueve el árbol fuera con `shutil.move`, y `reservar_lote`/`caso_path` admiten un directorio absoluto externo | §2: se **retira la garantía universal**; se declara que la pieza cubre el *alta nominal* y nada más. `#155` y `#156` abiertas |
| H-02 | ALTO | `ensure_case('')` convierte `CASOS_ROOT` en un expediente | §3(a): `exigir_componente_de_ruta` añade el **no vacío** que la extracción parcial había perdido |
| H-03 | ALTO | La gramática valida el `case_id` y **olvida `ciudad`**, que también compone el destino | §3(b): contrato nuevo — **el alta tiene que ser LOCALIZABLE**, validando contra `_CITY_NAMES`, el mismo conjunto que recorre `buscar` |
| H-04 | ALTO | La contención no cubre una junction preexistente en un **hijo** del caso | §3(c): **límite declarado**, no disimulado. `#157` abierta |
| H-05 | MEDIO | Mi tabla de mutantes no ejercitaba la mitad de contención: una implementación sin ella la superaba entera | §6: mutantes 4, 5 y 6 nuevos, cada uno muere si se quita la propiedad que le toca |

### Lo que el revisor NO pudo hacer, y que por tanto queda sin verificar por él

Las dos semillas aleatorias (su entorno no tiene `pytest-randomly`) y la suite completa limpia.
Esa cobertura la aporta el autor y se dice así, no se presenta como revisada.

### Y un error que la remediación destapó por su cuenta, que ninguna ronda pidió

**La rev. 2 sustituyó `resolve()` por la primitiva léxica `_bajo`, y eso fue una regresión sobre
la propiedad.** Lo desmintió el mutante 6 al implementarlo: `raiz/Enlace` es **léxicamente** hija
de `raiz` aunque la junction lleve los bytes fuera, así que la contención léxica **no contiene**.
Reusé una primitiva llamada «contención» sin comprobar que diera la contención que necesitaba —
el mismo error que este diseño viene a arreglar, cometido un nivel más arriba y por la vía de
querer no duplicar código.

**Arreglo:** las **dos** mitades. Léxica para `..` y absolutas, que funciona sin que el destino
exista; y física sobre el **ancestro existente más cercano**, con los dos lados resueltos —la
raíz también puede ser un enlace, `G:` es Drive Stream—, que es la que caza los enlaces. Está en
el código con su comentario, y el límite de H-04 sigue declarado.

Esto no es un hallazgo de la R1 y no se le atribuye: es un defecto **mío**, de la remediación,
encontrado por el mutante que la R1 obligó a escribir. Que es exactamente para lo que sirve
exigir que cada propiedad tenga un mutante propio.
