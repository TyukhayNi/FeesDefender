---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# Identidad sin teclado — `MEJORAS #224` cerrada, `#227` de vuelta al diseño

Pieza **P7** de la fila #28 de `PLAN.md` (`[SIGUIENTE-APERTURA-MENOS-DECISIONES]`), promovida el
2026-09-11 desde el handoff de la consulta sobre la apertura.

Empezó como dos cosas y sale como una. **`MEJORAS #224` entra; `MEJORAS #227` vuelve al diseño**,
por decisión de Nikolai del 2026-09-11 tras leer la R2. El porqué está en el §5, y no es «faltaba
tiempo»: es que dos rondas encontraron **la misma propiedad** rota de seis formas distintas.

## 1. `MEJORAS #224` — la dirección sale del nombre de la carpeta

`--direccion` era el **único** de los seis flags de identidad sin fuente: se tecleaba. El
2026-09-10, abriendo un caso, se tecleó sin el acento que la dirección lleva, y nadie podía avisar
porque no había con qué comparar. El `case_id` se propaga a la carpeta del despacho, a
`Referencia_Cliente` del CRM y a la etiqueta de Gmail, así que corregirlo después es el renombrado
cross-sistema que `[APER-04]` manda evitar.

**La pieza ya estaba construida y nadie la encadenaba.** `intake_drive.parse_ev_folder_name` existe
desde hace meses, con sus tests, y `streamlit_app.py:1676` ya lo consumía para el auto-fill de la
UI. Lo que faltaba era que `abrir_caso.py` lo llamara. Esto no construyó un parser: cableó el que
había, que es lo que la entrada del backlog insinuaba al decir «el dato existe y ya se lee».

**Una frontera que `#224` no pedía.** Además de rendirse cuando el nombre no trae W-code —hay
carpetas con nombre libre bajo `PROPIEDADES/1. ACTIVAS`—, se rinde **cuando el W-code del nombre no
es el del caso**. El parser ya devolvía el W-code, así que comparar es gratis, y el coste de no
hacerlo es estampar el inmueble de otro expediente en los tres sistemas.

Ninguna de las dos rendiciones levanta error propio: devuelven `None` y lo caza el chequeo de
flags que ya existía, de modo que **la pieza no puede bloquear ninguna invocación que hoy
funcione**.

## 2. Cómo se dimensionó, y por qué estuvo mal

Lo dimensioné en **1 ronda**: «escribe `_caso.md` bajo el mutex del caso, sin tocar el mutex ni
`core/anon/`». La R1 demostró que la otra mitad de la pieza **destruía una nota del letrado**, de
modo que por la tabla del 2026-08-26 —«puede destruir o corromper datos de cliente»— eran **2
rondas** desde el principio.

**La lección no es «dimensiona más alto por si acaso».** Es que miré *qué fichero* se tocaba y no
*qué podía perderse al tocarlo*. El radio de daño no lo fija el fichero: lo fija lo que hay dentro.

## 3. Adjudicación de la revisión adversarial (Codex, 2026-09-11) — NO-SHIP, parcial

- **Objeto revisado:** diff `eb8ac09..7872dcf` — `abrir_caso.py`, `case_manager.py` y sus tests
- **Ronda:** R1 de 2
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` sin `.git`, solo lectura
- **Informe recibido:** 2026-09-11, `C:/t/rev-p7-083941/wd/INFORME.md`, 37602 bytes
- **Hallazgos:** 8 — 1 ALTO, 4 MEDIOS, 3 BAJOS; **8 confirmados, 0 refutados**
- **Remediado en:** este §3 (H-06) y el §5 (el resto, retirado con la pieza)

Acta con el informe literal y su digest:
`docs/superpowers/plans/2026-09-11-identidad-sin-teclado-r1-adversarial-review.md`.

**H-01, ALTO, y era destrucción de datos del expediente.** `update_meta` buscaba la línea con
`startswith` sobre **todo** el cuerpo y se quedaba con la primera coincidencia. El escenario del
revisor, ejecutado: el abogado escribe `- Cuantía: comprobar oferta, NO BORRAR` en su sección, y
una actualización de cuantía **la reemplazaba**, dejando además la línea real de `## Sede` en
`_(pendiente)_` y devolviendo `cuerpo=['cuantia']`. Un «OK» sobre un expediente mutilado, y
exactamente lo que `MEJORAS #146` protege.

**Y mi test no lo veía porque medía otra población:** puse la nota a mano *sin* un prefijo que
coincidiera. Es el mismo modo de fallo que [[feedback-el-control-positivo-mide-otra-poblacion]].

| # | Sev. | Adjudicación | Dónde acabó |
|---|---|---|---|
| H-01 | ALTO | **CONFIRMADO**, reproducido | §5: la pieza se retira |
| H-02 | MEDIO | **CONFIRMADO** — sección dentro de un bloque cercado, o duplicada | §5 |
| H-03 | MEDIO | **CONFIRMADO** — campos con otro hogar aceptados sin avisar | §5 |
| H-04 | MEDIO | **CONFIRMADO** — índice truncado normalizado en silencio | §5 |
| H-05 | MEDIO | **CONFIRMADO** — «Alta CRM falló» con el alta hecha; reintento estéril | §5 |
| H-06 | BAJO | **CONFIRMADO** — `.upper()` en vez de `CaseRef.normalizar`: `--w-code " W-X "` daba falsa discrepancia | **Remediado en `#224`**, con test; la R2 lo dictaminó **REAL** y su mutante muere |
| H-07 | BAJO | **CONFIRMADO**, y son tres errores de prosa míos | Ver abajo |
| H-08 | BAJO | **CONFIRMADO** — `write_md` pierde comentarios YAML y espacios de borde | §5 |

**H-07 merece su párrafo porque no es sobre el código.** Tres cosas, todas mías:

1. El docstring de un test de conservación **invertía los colores**: decía «mientras siga rojo»
   sobre un test que pasa, y que precisamente por pasar acredita lo que dice acreditar.
2. Corregí la cita falsa de `#184` en el backlog **y la dejé intacta en el código y en los tests**
   — [[feedback-corregir-el-doc-y-no-su-indice]], literal, en la misma sesión en que la corregía.
3. «`ensure_case` solo fija los campos cuando CREA» era demasiado amplio: **sí** actualiza
   `tipo_caso`, `direccion`, `id_go` y `ciudad` en un caso existente, y su propio docstring lo
   dice. El defecto es de `cuantia` y `referencia_crm`, no de la función entera.

**Una limitación de esta ronda que es culpa de mi mandato.** El §4 permitía copias y temporales y
la última línea decía «no escribas ningún otro fichero». El revisor resolvió el conflicto de forma
conservadora —correctamente— y **no ejecutó pytest**, declarando su control positivo SIN VERIFICAR.
Dos instrucciones en conflicto le costaron la mitad del valor a la ronda.

## 4. Adjudicación de la revisión adversarial (Codex, 2026-09-11) — NO-SHIP, parcial

- **Objeto revisado:** diff `eb8ac09..c2a2c54` — el mismo, ya remediado tras la R1
- **Ronda:** R2 de 2 (presupuesto agotado)
- **Revisor:** Codex (CLI 0.153.4), con su propio informe de R1 entregado con `sha256`
- **Informe recibido:** 2026-09-11, `C:/t/rev-p7-r2-085933/wd/INFORME.md`, 40683 bytes
- **Hallazgos:** 9 nuevos + dictamen de las 8 remediaciones; **todos confirmados, 0 refutados**
- **Remediado en:** este §4 (H2-06) y el §5 (el resto, retirado con la pieza)

Acta: `docs/superpowers/plans/2026-09-11-identidad-sin-teclado-r2-adversarial-review.md`.

**Se le pidió lo que casi nunca se pide, y es lo que más devolvió:** dictaminar si cada remediación
de la R1 era **real, cosmética o incompleta**, reproduciendo el escenario original. Veredicto:
**6 de 8 incompletas**, 2 reales (H-06 y H-08).

**H2-06, ALTO, y es una regresión que abrió mi propio arreglo.** `--cuantia` tenía default `0.0` en
Typer. Al remediar H-05 hice que la guarda de idempotencia repusiera la cuantía, y con eso
**repetir el comando sin el flag** entraba por esa guarda y **sobrescribía con cero una cuantía ya
conocida**, fabricando discrepancia con el CRM —que conservaba la buena—. Medido de punta a punta:
`before=73140.5`, `after=0.0`, `crm_amounts=[73140.5]`.

El defecto original solo dejaba el dato sin escribir; éste lo destruía. **Remediado y con test**
(`--cuantia` pasa a `None` por defecto: «el flag no vino» y «el flag vino con cero» son cosas
distintas, y un default no es una orden de escribir).

> **Corrección del 2026-09-11.** Aquí decía «**se conserva aunque la pieza se retire**», y era
> falso: la remediación se fue entera con el PR #338 cerrado, sus cinco tests incluidos. Verificado
> por contenido — `git show origin/main:scripts/abrir_caso.py` seguía diciendo
> `typer.Option(0.0, "--cuantia")`. No era un defecto vivo mientras no hubiera `update_meta`, pero
> sí una mina para el segundo intento. **Vuelve con `MEJORAS #227`**, en
> `docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-design.md` §6.1.

**H2-08 es el que habla de mi instrumento, no del código.** Tres de mis tests **pasan ejecutando la
conducta que prohíben**, medido con mutantes dirigidos:

- un doble `boom` cuyo `AssertionError` `CliRunner` convierte en el `exit 1` que el test espera, de
  modo que el test **no acredita** «no se llamó»;
- un test de «no se crea nada» que comprueba el tipo de excepción y **no mira el árbol**;
- seis parametrizaciones que comprueban el nombre del campo y un prefijo fijo, y **sobreviven** a
  un mensaje que ya no nombra la vía sancionada.

Es [[feedback-el-arnes-de-mutacion-tiene-sus-propios-defectos]] aplicado a mis propios tests: un
verde que no puede ponerse rojo por la causa que dice vigilar.

**Lo que la R2 sí verificó y la R1 no pudo:** cuatro corridas de pytest (`head` y `base`, semillas
777 y 31337). `head` 81/81 verdes con las dos; `base` con los tests de `head`, **32 rojos** con las
dos. Y confirmó que mis cuatro tests verdes sobre `base` son **correctamente de conservación**, no
controles positivos disfrazados.

## 5. `MEJORAS #227` vuelve al diseño — la decisión, y su fundamento

**Decisión de Nikolai, 2026-09-11:** `#224` entra; `update_meta` sale de esta pieza y se rediseña.

**El fundamento no es el número de hallazgos, es que son el mismo.** R1 y R2 encontraron seis
formas distintas de que fallara **una sola propiedad**: localizar un fragmento de Markdown con
heurísticas de líneas. Preámbulo que se come una sección `###`; encabezados con la sangría que
CommonMark permite; cercas de distinto carácter o longitud; cercas sin cerrar; inserción fuera del
ámbito que se acababa de validar; duplicación de la línea al repetir. Cada ronda remedié **el caso
del informe** y no **la propiedad de la que era ejemplo** — que es literalmente lo que
[[feedback-remediar-la-frontera-no-el-ejemplo]] describe, y lo que las cuatro rondas del mutex de
V1 midieron.

Y el coste de equivocarse no es un dato mal puesto: es **una nota del letrado destruida**.

**El diseño alternativo, que elimina la clase entera en vez de parchearla:** no **localizar**, sino
**comparar**. El cuerpo canónico de un `_caso.md` lo genera `_cuerpo_del_indice` a partir de la
`meta`. Si el cuerpo del fichero **es exactamente** el que ese generador produciría para la `meta`
anterior, se puede reescribir entero sin riesgo. Si difiere en cualquier cosa —hay notas, hay
secciones ajenas, hay formato a mano—, **no se toca el cuerpo**: se escribe el frontmatter y se
declara en el informe.

Eso convierte un problema de *parsing* en una **igualdad de cadenas**, y hace imposible por
construcción destruir algo que el generador no escribió. El precio es que en un `_caso.md` con
notas la cuantía solo llega al frontmatter — y ese precio hay que medirlo antes de pagarlo, porque
hoy el único lector de `meta.cuantia` es la línea del cuerpo.

**Presupuesto cuando se retome: 2 rondas**, una sobre el diseño y otra sobre el diff. Esta vez
dimensionado por lo que puede perderse, no por qué fichero se toca.

**Lo que queda vivo en el backlog:** `MEJORAS #227` sigue abierta, con las dos rondas archivadas y
esta propuesta de diseño anotada. `#184` y `#192` siguen abiertas y **no** las cierra nada de esto,
como ya quedó corregido en la propia entrada.

## 6. Verificación de lo que sí entra

- `tests/test_abrir_caso_cli.py` + `tests/test_abrir_caso_modo_v1.py`: **76 verdes**.
- **7 tests nuevos** para `#224`, con **4 rojos de control positivo** contra el código sin la pieza,
  más el de H-06, que la R2 mató con un mutante dirigido (restaurar `.upper()`).
- El test de la carpeta sin W-code exige que la salida **diga de qué nombre** no pudo derivar: el
  error genérico «faltan flags» ya salía antes y por sí solo no acreditaría nada.
- Suite completa con las dos semillas: se mide en la rama antes de mergear.

**Cobertura adversarial de lo que entra, dicha con precisión:** `#224` fue revisado en dos rondas,
pero **dentro de un objeto mayor**. Su único hallazgo propio (H-06) está remediado y la R2 lo
dictamina **REAL**. Las afirmaciones 1 a 5 del mandato —flag explícito gana, se rinde sin W-code,
se rinde con W-code ajeno, no bloquea invocaciones que hoy funcionan, y la API de Drive se consulta
solo cuando hace falta— quedaron **verificadas en código y sonda**, con un matiz anotado: el aviso
es impreciso cuando hay W-code pero el prefijo está vacío. No es «`#224` pasó dos rondas limpias».
