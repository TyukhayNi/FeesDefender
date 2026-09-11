---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# Tres piezas para que la apertura pregunte menos (`PLAN.md` fila #28)

> Plan corto, no spec: los contratos que tocan estas tres piezas **ya están escritos**. Existe
> como documento propio por dos razones concretas. Una, el §5 P2 necesita diseño antes de
> codificarse y no cabe en una fila de tabla. Dos, **las adjudicaciones de las rondas
> adversariales necesitan un hogar**: el contrato de gobernanza las quiere embebidas en el
> documento que la decisión modificó, y una pieza que solo vive en una fila de `PLAN.md` no lo
> tiene.

De dónde sale: propuestas **P5**, **P7** y **P2** de
`docs/superpowers/handoffs/handoff-2026-09-10-consulta-apertura-menos-decisiones.md` (consumido),
promovidas por decisión de Nikolai el 2026-09-11 sobre la medición de las siete aperturas del
2026-09-10.

## 1. El hilo que une las tres

De las doce entradas humanas de una apertura, **cuatro son del letrado** —tipo provisional,
cuantía y base, quién es el deudor, y el veredicto de viabilidad— y **ocho son derivables o
verificables por código**. P5 y P7 quitan tres de esas ocho. P2 cierra el lazo sobre las demás.
Ninguna toca lo jurídico.

Presupuesto de rondas por la regla del 2026-08-26: ninguna decide quién escribe sobre qué copia
ni puede destruir datos de cliente → **una ronda cada una, sobre el diff**.

## 2. P5 — El generador de viabilidad escribe las 88 filas

**Estado: ✅ construida.** `render_informe.py` recorre `build_id_row_map(preg)` entero.

El defecto no era «faltan marcas»: el `SKILL.md` **ya contrataba** que las no resueltas salieran
con `sí`, y lo que fallaba es que el marcado **delegaba la exhaustividad en quien redacta el
JSON**. Un modelo al que se le pide enumerar 88 entradas enumera 51. Ahora el generador es
exhaustivo por construcción y el JSON aporta solo lo que sabe.

`MEJORAS #228` (semáforo `E22` FINANZAS) **no** entró: al medirlo, la fila 22 tiene dos bloques
combinados (`E22:F22` + `G22:H22`) donde la 21 tiene uno (`E21:H21`), así que «replicar las tres
reglas de E21 en E22:H22» no es el copia-pega que el backlog describía. No es imposible cablearlo
—`E22:H22` vale como rango de formato condicional aunque no sea un bloque—, pero hay una decisión
de layout por delante y la verificación propia de un binario versionado. Va en su propio PR.

## 3. Adjudicación de la revisión adversarial (Codex, 2026-09-11) — LISTA-CON-CAMBIOS, remediado

- **Objeto revisado:** diff `c3fdffa..038a034` — `render_informe.py`, `SKILL.md`, `CHANGELOG.md` y `tests/test_render_informe_viabilidad.py`
- **Ronda:** R1 (única; radio de daño = no escribe en el CRM ni destruye datos del expediente)
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` sin `.git`, solo lectura, con intérprete completo
- **Informe recibido:** 2026-09-11, `C:/t/rev-p5-viabilidad-080800/wd/INFORME.md`, 25684 bytes
- **Hallazgos:** 5 numerados (2 MEDIOS, 2 BAJOS, 1 NOTA) + 4 en el apartado B — **9 confirmados, 0 refutados**
- **Remediado en:** este §3 y el diff de la pieza P5

Acta con el informe literal y su digest:
`docs/superpowers/plans/2026-09-11-apertura-menos-decisiones-r1-adversarial-review.md`.

**Ninguno se refutó, y eso conviene decirlo tal cual.** Adjudiqué los nueve contra la fuente —el
código, la plantilla y `git`—, no contra el informe, y los nueve resistieron la comprobación.

| # | Severidad | Hallazgo | Adjudicación | Remedio |
|---|---|---|---|---|
| H-01 | MEDIO | El ejemplo del `SKILL.md` cambiaba `vue_01` a `{"pendiente": "no"}`, y `vue_01` es testifical | **CONFIRMADO** contra `cuestionario_viabilidad.yaml:691`: `fuente_probable: [entrevista, email]` | El ejemplo ya no lleva ninguna testifical, y se dice por qué |
| H-02 | MEDIO | El `pendiente` explícito se escribía **sin validar**, y la validación de la plantilla no protege | **CONFIRMADO y medido**: `allowBlank=True`, `showErrorMessage=False`; con `{"pendiente": ""}` salían **87 de 88** y el comando decía «OK» | `marca_pendiente()` valida contra `sí`/`no` (acepta `si` sin tilde como grafía); lo inválido se avisa y se deriva |
| H-03 | BAJO | El `CHANGELOG` decía «2 rojos» de control positivo y eran 3 | **CONFIRMADO**: el tercero enrojece por marcas **ausentes**, no por un literal inválido | Re-medido con las dos semillas: **18 de 26** sobre `origin/main`, y se dice por qué enrojece cada clase |
| H-04 | BAJO | El objeto traía **tres ficheros más** de los declarados | **CONFIRMADO, y era un defecto de flujo, no de alcance** | Ver abajo |
| H-05 | NOTA | «siempre en `tmp_path`» no cubre los temporales que openpyxl crea al serializar | **CONFIRMADO como hecho**; no es el árbol de producción, pero la frase se leía como si lo cubriera todo | Docstring precisada |
| B-1 | — | `respuestas.get(qid) or {}` convirtió en silencio un `AttributeError`: `cap_01: false` pasaba a generar un informe sin esa respuesta | **CONFIRMADO** — tolerancia nueva que yo introduje, no heredada | Avisa por `stderr` en vez de callar |
| B-2 | — | Escribir M de las 88 amplía el riesgo de `MergedCell` a filas que antes no se tocaban | **CONFIRMADO**; no afecta al asset canónico | El bloque escribe por `set_rc`, hermano de `set_cell`: avisa y salta |
| B-3 | — | El mapa colapsa IDs duplicados sin avisar, y la promesa «cuestionario entero» depende de esa unicidad | **CONFIRMADO como riesgo latente** (el asset tiene 88 IDs únicos, medido) | Test que cuenta filas con ID contra IDs distintos, **sin** usar el helper de oráculo |
| B-4 | — | El test de dominio elegía la validación por `"M" in sqref` y solo veía valores derivados | **CONFIRMADO, y es el hallazgo sobre mi propio instrumento**: el revisor lo mató con un mutante que escribía fuera de dominio ante cualquier explícito, **y el test siguió verde** | Exige `type == "list"`, rango de la columna M, y que las 88 filas caigan dentro; más seis tests de overrides |

**H-04 merece su párrafo, porque no es un hallazgo sobre el código.** La rama de P5 arrastraba los
cuatro ficheros del PR de gobernanza. La causa: `git checkout main -q 2>/dev/null` **falló** —la
raíz estaba en otra rama— y el `2>/dev/null` se comió el error, así que la rama nueva salió de la
de gobernanza. Es el mismo modo de fallo que la casa ya tiene escrito para
`$LASTEXITCODE` detrás de un `Select-Object`: **silenciar el error de un comando cuyo éxito se da
por supuesto**. Un revisor que no podía ver `git` lo detectó comparando contenido. Remediado con
`git rebase --onto origin/main`, y comprobado por `git diff --stat origin/main...HEAD`: cinco
ficheros, los declarados.

**Lo que el revisor dejó SIN VERIFICAR y sigue sin verificar:** las mediciones históricas de
producción (51/88 y 70/88), la genealogía de commits —no tenía `.git`—, el comportamiento visual
de Excel, y la suite completa del repositorio, de la que solo corrió el fichero nuevo. La suite
entera la corrió el autor.

**Lo que sigue sin cubrir, dicho aquí para que no se dé por hecho:** el inventario del §4 de su
informe lista huecos que **no** se han cerrado —entre otros, el JSON sin clave `preguntas`,
plantillas alternativas vía `--plantilla` con valores previos en M, y que el ejemplo del
`SKILL.md` se ejecute como test—. Ninguno es una regresión medida sobre el asset canónico; son
cobertura ausente, y como tal quedan declarados.

## 4. P7 — Identidad sin teclado (`MEJORAS #224`, `#227`)

**Estado: `#224` ✅ construida; `#227` en curso.**

`#224` resultó ser **cableado, no construcción**: `intake_drive.parse_ev_folder_name` existe desde
hace meses, con sus tests, y `streamlit_app.py:1676` ya lo consumía para el auto-fill de la UI.
Lo que faltaba era que `abrir_caso.py` lo llamara. Es un ejemplar exacto de «pieza construida que
nadie encadena»: el backlog decía «el dato existe y ya se lee», y la realidad era más fuerte.

Sobre lo que `#224` pedía se añadió una frontera que no pedía: **si el W-code del nombre de la
carpeta no es el del caso, no se deriva**. El parser ya devolvía el W-code, así que comparar es
gratis, y el `case_id` se propaga a la carpeta del despacho, a `Referencia_Cliente` del CRM y a la
etiqueta de Gmail — una dirección tomada de la carpeta de otro expediente queda estampada en los
tres. Ninguna de las dos rendiciones levanta error propio: devuelven `None` y lo caza el chequeo
de flags que ya existía, así que la pieza **no puede bloquear ninguna invocación que hoy
funcione**.

## 5. P2 — `verificar_apertura`: el «OK» del expediente, en código

**Estado: CONSTRUIDA el 2026-09-11 — las 9 comprobaciones.**
`core/verificar_apertura.py` + `core/verificar_apertura_fuentes.py` + `scripts/verificar_apertura.py`.

El defecto que cierra no es de una herramienta, es de todas: cada una dice «OK» de **su paso**, no
del expediente. El handoff contó ocho falsos «OK» en un solo día. Mientras nada cierre el lazo
sobre el expediente, el verificador es el letrado, y eso es «estar encima».

**Forma:** comando **de solo lectura**, sin mutex de escritura, que no repara nada. Cada
comprobación devuelve `ok | pendiente | fallo`. `pendiente` no es `fallo`: un caso a medias tiene
que poder verificarse sin que el informe grite.

> **Corregido al construirlo (R1, H-12):** este párrafo decía «emite … al `estado.json` y al
> evento forense», en presente, y **no se persiste nada** — el revisor midió cero escrituras. La
> decisión de no escribir, con su porqué, está en el apartado (b) de abajo; lo que aquí quedaba
> era un contrato en presente que el código no cumple. La salida es stdout, en texto o en JSON.

| # | Comprobación | Contra qué se contrasta | De dónde sale |
|---|---|---|---|
| 1 | Censo remoto contra local | `rclone lsf` del remoto vs. ficheros de `01_Drive EV`, excluyendo los de protocolo | `[APER-65]` |
| 2 | Hash de cada fichero | `sha256Checksum` que declara Drive, **cuando existe** | `MEJORAS #225` |
| 3 | Cobertura contra catálogo | filas de `_cobertura.json` menos hijos de bundle = entradas del catálogo | `[APER-60]`, con la corrección del 102º |
| 4 | Los cuatro artefactos de la sala | presencia de `INDICE.md`, `CRONOLOGIA.md`, `_MANIFIESTO.md`, `indice_documental.yaml` | `MEJORAS #221` |
| 5 | Viabilidad completa | las 88 filas con respuesta **o** marca de pendiente | P5 |
| 6 | Ficha y relaciones del CRM | relectura por API, no el status del alta | `MEJORAS #239` |
| 7 | Actuación asociada | leída **por el lado del expediente**, no por el del elemento | `MEJORAS #209` |
| 8 | Cero W-codes ajenos | `grep` sobre los espejos `03_MD` | `MEJORAS #235` |
| 9 | Cuantía coherente | `_caso.md` = CRM | `MEJORAS #227` |

**Regla que gobierna las nueve: verificar por resultado, nunca por status.** Ninguna comprobación
puede apoyarse en el código de salida de la herramienta que produjo el artefacto; todas leen el
artefacto.

**Lo que esta pieza NO cierra**, y por eso `#221` y `#235` siguen en backlog sin marcar:
`verificar_apertura` **detecta desde fuera** que `organizar` mintió y que se coló un W-code ajeno.
No arregla que `organizar` mienta ni que el barrido sea ciego al W-code de dentro del PDF.

**Control positivo obligatorio al construirla.** Una verja que solo puede decir `ok` no verifica
nada: cada una de las nueve necesita un caso sintético en el que **diga `fallo`**, y ese caso va
en el test. Es la lección de la guarda inerte, y aquí el riesgo es el máximo del repo — esta
pieza existe precisamente para que un «OK» signifique algo.

### Lo que la construcción cambió del diseño, y por qué

**(a) Un cuarto estado: `sin_implementar`.** *(Escrito cuando cinco comprobaciones seguían sin
construir; hoy no queda ninguna, pero el estado se conserva y su propiedad tiene test con una
comprobación sintética — una guarda sin caso que la ejerza es una guarda inerte.)* Cinco de las
nueve necesitaban red y no se habían construido. Podrían
haberse dejado fuera de la lista, y entonces el informe diría «9 de 9 correctas» habiendo mirado
cuatro: **exactamente el modo de fallo que esta pieza existe para cerrar, cometido por la pieza
misma**. Así que las nueve se enumeran siempre, `sin_implementar` **no cuenta como comprobada**, y
el resumen dice «4 de 9». El CLI repite el aviso incluso con `--solo-problemas`, que es justo
cuando el operador deja de ver la lista entera.

Esto no es dividir el alcance por comodidad: la costura es real —red contra disco— y las cuatro
locales ya cierran cuatro de los ocho falsos «OK» medidos el 2026-09-10 (`#221`, el `render` con
filas en blanco, la cobertura contra el catálogo y el W-code ajeno), sin un solo doble de red que
pudiera acabar probándose a sí mismo.

**(b) No escribe en `_apertura_v1.json`,** que el diseño contrataba. Dos razones: ese fichero vive
en `00_Input/` y escribirlo **exige el mutex** (`MEJORAS #126`), lo que convertiría un verificador
de solo lectura en un escritor —y dejaría de poder correrse mientras algo trabaja sobre el caso,
que es cuando más falta hace—; y **nadie lo leería**, que es la pieza construida que nadie
encadena. Se cablea cuando exista el consumidor: la ficha de cierre de la acción 12, o V2 leyendo
el resultado para decidir si sigue.

**(c) El control positivo se guarda con un test transversal**, no solo con buena voluntad:
`test_cada_comprobacion_implementada_PUEDE_decir_fallo` recorre las comprobaciones que dicen estar
implementadas y exige que exista un caso que las ponga en `fallo`. **Su mutante está medido**: al
convertir `c9` en «implementada» sin darle su rojo, el test cae con
`assert not ['cuantia_coherente']`. Sin esa medición sería una guarda inerte más, y el fichero
entero existe para no tener ninguna.

### Las cinco de red, construidas el mismo día — y cómo se resolvió su gate

El gate era uno y de diseño: **cómo se inyecta el cliente para que los tests prueben la
comprobación y no el doble.** Es el defecto H-07 de la R1, donde los tests del CLI sustituían
`case_locator.buscar` y por eso no vieron que una forma de invocación anunciada llevaba tiempo
rota.

La respuesta, en `core/verificar_apertura_fuentes.py`: un **puerto estrecho** (`Fuentes`, dos
métodos), un adaptador **tonto** que solo traduce (`DeLaRed`), y un puerto **cerrado** (`SinRed`)
que es **el default**. Sin fuentes explícitas, las cinco salen en `fallo` diciendo que no se pudo
consultar — un verificador cuyo modo por defecto fuera «no preguntar y aprobar» sería peor que no
tenerlo.

**Tres cosas se midieron antes de escribirlas**, y el atlas del CRM las tenía todas (consultarlo
antes de sondear es regla de la casa, y esta vez ahorró el sondeo entero):

| Lo que había que saber | Lo medido |
|---|---|
| Cómo se llama la propiedad de la cuantía | **`cuantia`**, en los dos elementos. Llega como **cadena**, no como número → C9 compara números, porque `73140` y `73140.00` son la misma cuantía |
| Si la actuación se puede leer por el lado del expediente | **`actuaciones` es hijo** de `extrajudiciales` y `expedientes_judiciales`, así que viene en `related_register`. Confirmado además contra el CRM real |
| Qué forma tiene la respuesta | `element_registries/extrajudiciales` responde con **`items`**, no `hydra:member`. La documentación se contradice en su §15.6 y su §2110 contra su propia recomendación de aceptar las dos; se aceptan las dos |

C2 usa la **Drive API** y no `rclone lsf`: el hash es la mitad de lo que hace falta (`MEJORAS
#225`) y `rclone` no lo publica por esa vía. Una consulta da censo Y hash; dos darían dos fotos de
momentos distintos.

**Lo que un doble no puede acreditar, y por eso hay un test de integración.** Que el CRM responda
con la forma que aquí se parsea solo lo prueba una consulta real:
`test_integracion_el_adaptador_real_habla_con_el_CRM` la hace, en solo lectura, marcada `slow` y
saltada sin `SUDESPACHO_API_KEY` —y entonces la integración queda **SIN VERIFICAR** y así se
declara—. No afirma nada sobre el **contenido** del expediente, que cambia: afirma que el
adaptador devuelve la forma del puerto y que `actuaciones` sigue siendo un bloque de
`related_register`. Si dejara de serlo, C7 empezaría a decir «ninguna actuación» sobre
expedientes que sí la tienen, y nadie sabría por qué.

## 6. Lo que no entra en esta fila

P1 (secuencia V2+V3: plan propio y dos rondas), P3 (`MEJORAS #225`, espera la decisión de Nikolai
sobre el histórico), P4 (`[APER-70]`, espera decidir qué constructor de la sala sobrevive), P6
(depende de P2 y de la capa base) y P8 (proceso, decisión de Nikolai). Siguen en el handoff, con
su §8 diciendo por qué.

## 7. Adjudicación de la revisión adversarial (Codex, 2026-09-11) — NO-SHIP, remediado

- **Objeto revisado:** diff `0702f49..b051e96` — `verificar_apertura` (core, CLI y tests)
- **Ronda:** R1 (única; el comando es de solo lectura y no puede destruir nada)
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` sin `.git`, con intérprete completo
- **Informe recibido:** 2026-09-11, `C:/t/rev-p2-103713/wd/INFORME.md`, 34192 bytes
- **Hallazgos:** 13 — 7 ALTOS, 4 MEDIOS, 2 BAJOS; **13 confirmados, 0 refutados**
- **Remediado en:** este §7 y el diff de la pieza

Acta con el informe literal y su digest:
`docs/superpowers/plans/2026-09-11-apertura-menos-decisiones-p2-r1-adversarial-review.md`.

**El mandato puso una sola pregunta en el centro —«¿puede este verificador decir *ok* de un
expediente roto?»— y la respuesta fue que sí, de siete formas.** En un verificador eso no es una
lista de defectos: es el defecto, porque es lo único que la pieza existe para impedir.

### La regla que salió de la ronda

**No poder mirar NO es «no hay nada que ver».** La primera versión trataba cada imposibilidad como
ausencia benigna —un espejo ilegible, una lista con entradas corruptas, una ruta ocupada por un
fichero— y las tres devolvían verde. Ahora toda imposibilidad de leer, toda forma inválida y toda
colisión de tipo son `fallo`, con el motivo. `pendiente` queda para la ausencia legítima: el
productor todavía no ha corrido.

| # | Sev. | Hallazgo | Adjudicación y remedio |
|---|---|---|---|
| H-01 | ALTO | Los lectores descartaban en silencio lo que no fuera un mapa, y el conteo cuadraba | **CONFIRMADO**: `[1, "broken", null]` contra catálogo vacío daba `ok`. Una entrada que no es un mapa es forma inválida, y se dice cuántas y dónde |
| H-02 | ALTO | Cualquier `parent_slug` verdadero descontaba un documento | **CONFIRMADO**: `17`, un slug inexistente o el suyo propio. Un hijo solo cuenta si su padre **existe** en la cobertura |
| H-03 | MEDIO | Igual cardinalidad no acredita que se catalogara lo procesado | **CONFIRMADO, y es límite de los DATOS**: la cobertura identifica por `slug` y el catálogo por `id_doc`, que no comparten clave. Se conserva el alcance y **el título deja de prometer más de lo que mide** |
| H-04 | ALTO | C5 contaba no-vacíos: 88 marcas a `basura`, o 88 copias de la misma pregunta, daban `ok` | **CONFIRMADO**. Se exige dominio (`sí`/`si`/`no`) y unicidad: «las 88 preguntas» es sobre identidades, no sobre filas |
| H-05 | ALTO | Un espejo ilegible salía como «ninguno ajeno»; y solo se recorría el primer nivel | **CONFIRMADO**. Error de lectura → `fallo`; barrido recursivo |
| H-06 | ALTO | `01_Procesado` ocupado por un fichero se leía como «aún no ha corrido» | **CONFIRMADO**: cuatro `pendiente`, cero fallos, salida 0. Colisión de tipo → `fallo` |
| H-07 | ALTO | El W-code corto que la ayuda anuncia no se resolvía | **CONFIRMADO**. Ahora `resolve_ref`, y su test solo sustituye la raíz |
| H-08 | ALTO | La guarda del control positivo leía TEXTO | **CONFIRMADO**, y es el que más importa. Ver abajo |
| H-09 | MEDIO | El W-code propio se elegía por primera aparición | **CONFIRMADO**: en `Relacionado W-04AAAA - Caso (W-TEST01)` el ajeno quedaba exento. Se toma el de **entre paréntesis**; dos son identidad ambigua y se declara |
| H-10 | MEDIO | W-codes partidos por maquetación o con guion Unicode, invisibles | **CONFIRMADO**. El texto se normaliza antes de buscar |
| H-11 | MEDIO | El empate de `mtime` se resolvía por orden alfabético | **CONFIRMADO**, y podía **ocultar el informe malo detrás del bueno**. Sin regla de vigencia se declara `pendiente` |
| H-12 | BAJO | La prosa prometía en presente una salida persistida que no existe | **CONFIRMADO** (cero escrituras medidas). Corregido, y el «cuatro de red» que eran cinco |
| H-13 | BAJO | «Todo en tmp_path» no cubre los temporales de openpyxl | **CONFIRMADO como hecho**. La frase queda acotada |

### H-08 merece su párrafo, porque es sobre el instrumento y no sobre el código

Mi guarda del control positivo buscaba una **cadena literal** en el fichero de tests. El revisor la
sobrevivió de tres formas legítimas —`@pytest.mark.skip`, `xfail(strict=True)` y el ejemplo dentro
de un docstring— y la rompió cambiando unas comillas dobles por simples en un test que seguía
funcionando. **Leer texto no demuestra ejecución, ni resultado, ni siquiera que exista una función
de test.** El mutante que yo maté era real, pero insuficiente para sostener la garantía escrita.

Ahora el registro de expedientes rotos vive **en código** (`CASOS_DE_FALLO`), la guarda lo
**ejecuta** por parametrización, y un segundo test exige que cubra todas las implementadas — sin
esto, añadir una décima comprobación y olvidar su entrada dejaría la parametrización sin ese id,
verde por omisión, que es la forma más silenciosa de que una verja deje de verificar. **Medido:**
el mismo ataque que tumbaba a la anterior (declarar `c9` implementada y documentarla con un test
`@skip`) ahora cae.

### Lo que sigue sin cubrir, dicho para que no se dé por hecho

Que la cobertura y el catálogo contengan **los mismos documentos**, y no solo el mismo número
(H-03): hace falta una correspondencia entre `slug` e `id_doc` que hoy los datos no llevan. Y las
cinco comprobaciones de red, con su gate en la tabla de arriba.

**Verificación:** 63 tests (eran 33), **20 rojos de control positivo** contra el código
pre-remediación, uno por hallazgo. Suite completa con las dos semillas (777 y 31337): **5244
tests, 5151 passed, 0 fallos**, idéntico con las dos.
