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

**Estado: diseñada aquí, sin construir.**

El defecto que cierra no es de una herramienta, es de todas: cada una dice «OK» de **su paso**, no
del expediente. El handoff contó ocho falsos «OK» en un solo día. Mientras nada cierre el lazo
sobre el expediente, el verificador es el letrado, y eso es «estar encima».

**Forma:** comando **de solo lectura**, sin mutex de escritura, que no repara nada. Cada
comprobación emite `ok | pendiente | fallo` al `estado.json` y al evento forense. `pendiente` no
es `fallo`: un caso a medias tiene que poder verificarse sin que el informe grite.

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

## 6. Lo que no entra en esta fila

P1 (secuencia V2+V3: plan propio y dos rondas), P3 (`MEJORAS #225`, espera la decisión de Nikolai
sobre el histórico), P4 (`[APER-70]`, espera decidir qué constructor de la sala sobrevive), P6
(depende de P2 y de la capa base) y P8 (proceso, decisión de Nikolai). Siguen en el handoff, con
su §8 diciendo por qué.
