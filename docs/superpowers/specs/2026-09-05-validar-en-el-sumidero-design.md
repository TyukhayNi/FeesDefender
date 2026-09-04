---
estado: rev3-remediado-r2
autor: Claude Code
fecha: 2026-09-05
revision: 3
cierra: MEJORAS #153, MEJORAS #154
abre: MEJORAS #155, MEJORAS #156, MEJORAS #157, MEJORAS #158, MEJORAS #159
rondas_previstas: 2
motivo_dos_rondas: "la pieza decide DONDE se deposita un expediente con PII"
r1: docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-r1-adversarial-review.md
r2: docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-r2-adversarial-review.md
---

# Validar en el sumidero, no en cada puerta

> **Rev. 3 (2026-09-05), tras la R2 adversarial sobre el diff: `NO-SHIP`, seis hallazgos, los seis confirmados.** Tres eran defectos que introdujo el propio arreglo. Lo que cambia en este documento es el **§3(c)**: describía la contención como léxica y con la primitiva equivocada, y son **dos mitades** con la léxica en `_contenido_en`. La adjudicación completa, en el **§8**; la voz del revisor, en el acta hermana `…-r2-adversarial-review.md`.

> **Rev. 2 (2026-09-05), tras la R1 adversarial que dio `NO-SHIP` con cinco hallazgos, los
> cinco confirmados contra la fuente.** La rev. 1 sostenía que **una** comprobación en
> `ensure_case` cerraba los dos ítems y cubría «cualquier puerta futura». Eso era falso y
> el revisor lo demostró ejecutando: `move_to_city` mueve el árbol completo fuera de la raíz
> con `shutil.move`, y mi defensa —que la UI ofrece un catálogo cerrado de ciudades— era
> justo el error que este documento denuncia: **el catálogo está en el envoltorio y no
> protege la API de core**. Usé como garantía la misma clase de cosa que vengo a arreglar.
>
> **Alcance de la rev. 2, decidido por Codex el 2026-09-05** en ausencia de Nikolai y por
> encargo expreso suyo: **estrecho**. Se arregla el alta nominal; se **retira la garantía
> universal**; y las otras puertas se registran como pendientes explícitos y vinculados, sin
> tocarlas de noche. Su condición, que se cumple en el §6: *«la ronda 2 debe demostrar
> también la contención, con pruebas que fallen al eliminarla.»*

## 1. El problema, medido

`MEJORAS #148` arregló `componer_case_id`, la vía del **CLI de seis flags**. La R1 del
2026-09-04 destapó que no es la única puerta, y que la otra es la que se usa a diario:

- **`MEJORAS #153`** — `streamlit_app.py` compone `_case_id_auto` con su propia interpolación
  y pasa `final_case_id` directo a `ensure_case`. Con una dirección que lleve `s/n`, el `/`
  actúa de separador y la UI dice «Caso local disponible».
- **`MEJORAS #154`** — el **override de ruta del formulario de alta** permite escapar de
  `CASOS_ROOT`: `destino_de_alta` es `buscar(case_id) or (_root() / case_id)` y el operador
  `/` de `pathlib` **descarta el lado izquierdo** ante una ruta absoluta.

**Quién usa cada puerta fija el orden:** el CLI lo usa Nikolai; la UI la usan Paola y Ana.

## 2. La frontera — y qué garantía se puede dar de verdad

La propiedad mal cerrada, cuarta manifestación en dos días, es siempre la misma:

> **La guarda está en el envoltorio y el otro llamador la rodea.**

Su remedio es ponerla en el **sumidero**, no en los compositores. Pero la rev. 1 confundió dos
cosas distintas, y la R1 lo separó bien:

- **`ensure_case` es el sumidero del ALTA NOMINAL.** Verificado por `git grep` de
  `mkdir(parents=True` en `core/`, `scripts/` y `streamlit_app.py`: el único que materializa el
  árbol de un caso nuevo es `core/case_manager.py:343`.
- **NO es el único sitio que deposita bytes de un expediente.** Hay al menos tres más, y
  **esta pieza no los cubre**:
  1. `move_to_city` (`core/casos/case_locator.py:270-319`) **relocaliza** el árbol completo con
     `shutil.move` a `path_for_ciudad(case_id, ciudad_destino)`, sin validar la ciudad ni
     comprobar contención → **`MEJORAS #155`**.
  2. `reservar_lote` / `caso_path` admiten un **directorio absoluto externo** como si fuera un
     caso, sin exigir `_caso.md`, y crean su árbol de intake fuera de la raíz →
     **`MEJORAS #156`**.
  3. Una **junction preexistente en un hijo** del caso (p. ej. `00_Input` → fuera) hace que el
     `_caso.md` acabe fuera aunque el directorio del caso esté contenido → **`MEJORAS #157`**.

**La garantía que este diseño da, enunciada sin inflarla:** un alta por `ensure_case` produce
un caso **contenido y localizable**. **No** afirma que sea imposible sacar un expediente de
`CASOS_ROOT` por otras vías.

## 3. Diseño

Una comprobación en `ensure_case`, **antes del `mkdir`**. Tres propiedades, no dos.

**(a) `case_id` es un componente de ruta válido.**
Nueva `core.utils.exigir_componente_de_ruta(valor, campo)`: **no vacío** + sin
`[\\/:*?"<>|]` + no es `.` ni `..`. Se compone sobre
`exigir_sin_caracteres_de_ruta`, que ya existe.

**Por qué «no vacío» hay que añadirlo, que es el hallazgo H-02:** ayer extraje
`exigir_sin_caracteres_de_ruta` de `validate_case_id` y **dejé atrás su comprobación de
vacío**, que sigue en la función original (`core/utils.py:144-147`). Reutilizar solo la mitad
extraída hacía que `ensure_case('')` pasara las dos mitades —`buscar('')` devuelve la propia
raíz y `is_relative_to` incluye la igualdad— y **convirtiera `CASOS_ROOT` en un expediente**,
con sus nueve subcarpetas y su `_caso.md`. Una extracción parcial que perdió una propiedad.

No se exige el formato canónico del `case_id`: medido el 2026-09-04 como **guarda más ancha
que el defecto**, rompió cinco fixtures con códigos sintéticos (`BaTEST`).

**(b) `ciudad`, si se da, tiene que ser LOCALIZABLE.**
`ciudad in case_locator._CITY_NAMES`, que es `frozenset(CIUDADES) | {"_Sin clasificar"}` y **ya
existe declarado en `case_locator.py:19`** — el mismo conjunto que recorre `buscar`. No se crea
otra lista: si se creara, divergirían, que es la enfermedad de este documento.

**Por qué el contrato es «localizable» y no «un componente», que es el hallazgo H-03:** la
rev. 1 validaba solo el `case_id` y olvidaba que `ciudad` **también compone el destino**.
`ensure_case('EV-2026-001', ciudad='Barcelona/subcarpeta')` pasa la gramática, cae **dentro** de
la raíz, y crea un caso que `buscar` **no encuentra**; un segundo alta genera un duplicado. Con
una ciudad desconocida de un solo componente pasaría lo mismo. **Contención y localización son
propiedades distintas**, y el alta debe garantizar las dos.

**(c) Contención: el destino cae bajo la raíz. Y hacen falta LAS DOS mitades.**

> **Corregido en la rev. 3.** La rev. 2 describía aquí una contención **léxica** implementada
> con `case_mutex._bajo`, y las dos mitades de esa frase resultaron falsas. Se deja escrita la
> historia porque el error tiene forma reutilizable, no por arqueología.

- **LÉXICA** — `core/case_manager._contenido_en`, con `os.path.commonpath`. Compara por
  **componentes** (`CASOS_x` no está bajo `CASOS`) y **no toca el disco**, que es lo correcto
  aquí: el destino **todavía no existe** cuando se valida. Caza `..` y las rutas absolutas.
- **FÍSICA** — resuelve el **ancestro existente más cercano** y comprueba que siga bajo la raíz
  resuelta, con los **dos lados** resueltos (la propia raíz puede ser un enlace: `G:` es Drive
  Stream). Caza las junctions, que la léxica no puede ver. El paseo **se detiene en la raíz**, y
  solo corre `if raiz.exists()`.

**Por qué no basta la léxica, que es lo que decía la rev. 2.** Lo desmintió el mutante 6 al
implementarlo: `raiz/Enlace` es **léxicamente** hija de `raiz` aunque la junction lleve los bytes
fuera. Reusé una primitiva llamada «contención» sin comprobar que diera la contención que
necesitaba — **el mismo error que este diseño viene a arreglar, cometido un nivel más arriba** y
por la vía de querer no duplicar código.

**Por qué tampoco es `_bajo`, que es lo otro que decía la rev. 2.** La R2 lo midió: `_bajo` hace
`c.startswith(r + os.sep)`, así que con una raíz que **ya termina en separador** —`C:\` o un
recurso UNC— exige dos separadores seguidos y rechaza a **todos** sus descendientes legítimos.
No se arregla `_bajo` aquí porque lo consume el **mutex del caso**, cuyo radio de daño es otro y
cuyo presupuesto son dos rondas: queda como `MEJORAS #159`, con el remedio y sus cuatro mutantes
ya escritos.

**Por qué el paseo tiene tope, que es lo que la rev. 2 no tenía.** Sin él, con `CASOS_ROOT`
todavía sin crear —**el primer alta de cualquier máquina nueva**— se sube al padre de la raíz y
se le acusa de escapar por un enlace inexistente. Un alta que crea su propia raíz es legítima
(R2/H-01).

**La rev. 1 proponía `resolve()` + `is_relative_to`**, y su defecto era otro: `resolve()` toca
disco sobre una ruta inexistente. La lección de las tres versiones es la misma dicha tres veces:
**el nombre de una primitiva no acredita la propiedad que promete**; hay que medirla.

**Y la limitación se declara, no se disimula:** (c) contiene los **ancestros** de `case_dir`.
**No** protege de una junction preexistente en un **hijo** (H-04, demostrado con junction real
de Windows). Eso es `MEJORAS #157` y queda **fuera** de esta pieza.

**Lo que NO se toca:** los constructores nominales (`destino_de_alta`, `path_for_ciudad`) siguen
siendo puros —«nombrar no es crear»—, y la UI tampoco. Si hubiera que tocarla, sería otra vez el
ejemplo en vez de la propiedad.

## 4. Radio de daño y rondas

**Dos rondas**: la pieza decide dónde se deposita un expediente con PII. Ronda 1 sobre este
diseño (hecha, `NO-SHIP`, cinco hallazgos, remediados en esta rev. 2) y ronda 2 sobre el diff.

Y queda declarada la corrección de un error propio: el 2026-09-04 clasifiqué el lote anterior
como «una ronda, ninguna puede destruir datos de cliente» y un hallazgo CRÍTICO lo desmintió.
Esta pieza se clasificó **antes** de escribirla.

## 5. Riesgo, y cómo se acota

El riesgo no es que la guarda falle: es que sea **demasiado estricta** y bloquee un alta
legítima. Acotación medida **antes** de implementar:

1. **Medido el 2026-09-05 sobre el catálogo real:** los **27** casos de todas las ciudades son
   un solo componente y ninguno lleva carácter prohibido ni es `.`/`..`.
2. La contención se mide contra `_root()`, que es una env var: en modo local (`CASOS_ROOT` al
   Desktop tras un *checkout*) la raíz es la local, así que la proyección local no se rompe.
3. `_CITY_NAMES` incluye `_Sin clasificar`, así que el fallback legítimo y
   `scripts/migrate_to_city_structure.py` siguen funcionando.
4. **Corrección de la rev. 1:** decía que «(a) sola dejaría pasar una ruta absoluta si algún día
   `pathlib` deja de descartar el lado izquierdo». **Es falso** y el revisor lo señaló: el helper
   rechaza `:` y los separadores **antes** de cualquier semántica de unión. El papel real de (c)
   son las **ciudades y los enlaces**, no una hipótesis sobre `pathlib`.

## 6. Mutantes

La condición de Codex para la ronda 2 era que **la contención se demuestre con pruebas que
fallen al eliminarla**. La tabla de la rev. 1 no lo hacía —era todo negativos de gramática, y
una implementación sin (c) la superaba entera, que es el hallazgo H-05—. Ahora cada propiedad
tiene al menos un negativo que **solo** ella puede rechazar:

| # | Mutante | Debe | Muere si se quita |
|---|---|---|---|
| 1 | `case_id` con `/` («s/n») | abortar **sin dejar carpeta parcial** | (a) |
| 2 | `case_id` `''` | abortar, y la raíz **no** tiene `00_Input` ni `_caso.md` | (a) no-vacío |
| 3 | `case_id` `.` / `..` | abortar | (a) |
| 4 | `ciudad='Barcelona/subcarpeta'` | abortar | **(b)** |
| 5 | `ciudad='Kuala Lumpur'` (un componente, desconocida) | abortar | **(b)** |
| 6 | `case_id` que resuelve fuera de raíz (junction en el propio caso) | abortar, y el exterior queda **vacío** | **(c)** |
| 7 | `case_id` legítimo con paréntesis, comas, acentos y `º` | **pasar** | — |
| 8 | caso existente bajo su ciudad | **pasar** | — |
| 9 | `ciudad='_Sin clasificar'` | **pasar** | — |

Los mutantes 4, 5 y 6 son los que la rev. 1 no tenía: sin ellos, una implementación que
suprimiera (b) o (c) pasaría la tabla entera. El 1, el 2 y el 6 exigen comprobar el **disco**,
no solo la excepción: lo caro del defecto original no fue el error, fue que dejó 170 ficheros en
una ruta sombra.

## 7. Alcance explícito

**Cierra** `#153` y `#154` — el `s/n` desde la UI y el override del formulario de alta.

**Abre**, con la evidencia de la R1: `#155` (`move_to_city` sin contención), `#156`
(`reservar_lote`/`caso_path` con directorio absoluto) y `#157` (junction en un hijo del caso).
Los tres son sumideros reales y **ninguno lo cubre esta pieza**.

**No aborda** el tercer defecto de `MEJORAS #67` (estructura plana de la sala de lectura), ni la
reapertura de `#149`, que necesita su propio contrato por ubicación.

## 8. Adjudicación de la revisión adversarial R2 (Codex, 2026-09-05) — NO-SHIP, remediado

- **Objeto revisado:** diff `9ec96f7..eee9a7e` — validación en el sumidero + los puntos 2, 3 y 4 de los aprendizajes en código
- **Ronda:** 2 de 2 (la R1 fue sobre este mismo diseño)
- **Revisor:** Codex
- **Informe recibido:** 2026-09-05, literal y con su `sha256` en `…-r2-adversarial-review.md`
- **Hallazgos:** 6 recibidos · **6 confirmados** · 0 refutados · 0 escalados
- **Remediado en:** `e8fa35e` y el commit de esta rev. 3

**6 de 6 confirmados, y tres eran míos.** H-01 (la contención física impedía el primer alta con
la raíz sin crear), H-03 (el validador dejaba andamiaje parcial con un espacio final) y H-04 (la
CLI afirmaba «todo el catálogo está clasificado» sin worklist, con salida 0) los **introdujo el
propio arreglo**. H-02 y H-06 son preexistentes y se registran como `#159` y `#158`. H-05 es un
defecto de **prueba**: mis cuatro tests del punto 4 no detectaban un `_link_md` que cruzara los
enlaces, y el revisor lo demostró con un mutante que los dejaba a los cuatro en verde.

**Lo que este diseño cambia por ello:** el §3(c) de arriba, que describía la contención como
léxica y con la primitiva equivocada. El detalle de cada hallazgo, la evidencia que verifiqué por
mi cuenta y el informe literal están en el acta hermana.

**Y la lección que se lleva el presupuesto de rondas.** La primera remediación de H-04 arregló
**el ejemplo** que el informe describía —«la worklist no se ha generado»— cuando el propio
informe señalaba la frontera en la frase siguiente: los brazos del `if` *«son disjuntos sobre sus
dos listas, no exhaustivos sobre el estado documental»*. Con la worklist **presente pero rancia**
volvía a mentir. La segunda deriva la afirmación del **catálogo**, que es la propiedad. Eso es el
corolario de `CLAUDE.md` —*«¿de qué frontera es esto un ejemplo?»*— y es lo que evita la tercera
ronda, no la disciplina de no pedirla.

**No se pide tercera ronda.** El techo lo fija Nikolai y solo él lo levanta.
