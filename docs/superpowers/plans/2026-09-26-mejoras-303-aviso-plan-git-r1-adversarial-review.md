---
tipo: revision-adversarial
objeto: diff ca250a4..8cebec4 de MEJORAS #303 (scripts/session_close.py y tests/test_session_close_aviso.py), contra el plan docs/superpowers/plans/2026-09-26-mejoras-303-aviso-plan-git.md
objeto_rev: "1"
commit: 8cebec4
ronda: "1"
revisor: Codex
modelo: gpt-6-sol
esfuerzo: high
velocidad: default
veredicto: LISTA-CON-CAMBIOS
marcador_nonce: bhxg
sha256_informe: 5b5ffda5ccc3da57191844b77ff3f48ae3663bae50715753d7a94ca354e63d6d
adjudicado_en: docs/superpowers/plans/2026-09-26-mejoras-303-aviso-plan-git.md §7
---

# Acta — R1 adversarial sobre el DIFF de MEJORAS #303 (el aviso «PLAN.md ↔ git»)

Objeto: el diff `ca250a4..8cebec4`, que arregla el aviso de `scripts/session_close.py` según el plan
de la pieza. **Una ronda**: toca `scripts/`, no escribe datos de cliente ni decide qué cuenta como
revisado. Fila ordinaria de la política: `gpt-6-sol` · `high` · `default`, y **segunda fila del
ledger de calibración de la #38**.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.4` (binario `13995fba801849b0`), `gpt-6-sol` · `high` — **releídos** del `turn_context` del rollout y de la cabecera del `_stdout.log`; velocidad `default` **afirmada** desde el lanzador, no acreditada |
| Objeto | `base/` (`ca250a4`) y `head/` (`8cebec4`), copias `git archive` fuera del repo, más `diff.patch`, `commits.txt` y `ramas.txt` |
| `sha256` del objeto | **idéntico al abrir y al cerrar**: 2.861 ficheros, comparados por él y por mí contra una huella mía tomada antes de lanzar |
| `sha256` del informe | `5b5ffda5ccc3da57191844b77ff3f48ae3663bae50715753d7a94ca354e63d6d` |
| Tiempos | lanzado a las 14:36:43; `INFORME.md` a las 14:44:46; `exec` salió a las 14:45:22 con `exit=0` |
| Veredicto | `LISTA-CON-CAMBIOS` — 4 hallazgos: 1 `media`, 3 `baja` |

## 0. Mandato, literal

# Mandato — R1 adversarial sobre el diff de MEJORAS #303 (FeesDefender)

## 0. Higiene y reglas

- Tu directorio de trabajo debe contener solo: `MANDATO.md`, `base/`, `head/`, `diff.patch`,
  `commits.txt` y `ramas.txt`. Si hay cualquier otro fichero, **no lo leas** y decláralo en la
  primera línea del informe.
- `base/` es el commit `ca250a4` (main) y `head/` es `8cebec4` (la rama del cambio), extraídos con
  `git archive`, sin `.git`. Son de **solo lectura**: si necesitas ejecutar o modificar algo, copia a
  una carpeta tuya dentro de tu directorio de trabajo. Calcula el SHA-256 de todos los ficheros de
  `base/` y `head/` al abrir y al cerrar, y di si coinciden.
- Python con las dependencias del repo:
  `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe` (tiene pytest; **no** tiene
  pytest-randomly, así que no hacen falta semillas). Usa `--basetemp` con una ruta **relativa**
  dentro de tu directorio de trabajo.
- No accedas a red, al CRM, a Drive ni al repositorio real.

## 1. Objeto

El diff `ca250a4..8cebec4` (`diff.patch`, `commits.txt`): arregla el aviso «PLAN.md ↔ git» de
`scripts/session_close.py` (MEJORAS #303). El plan con lo medido, el diseño y lo que declara no
cubierto está en `head/docs/superpowers/plans/2026-09-26-mejoras-303-aviso-plan-git.md`; la entrada
del backlog, en `head/docs/MEJORAS_FUTURAS.md` (#303). Revisa el código contra ese plan.

Un dato que no está en el objeto: `_ramas_conocidas()` consulta git y en tu copia no hay `.git`, así
que devuelve un conjunto vacío. `ramas.txt` lista las ramas que git conocía al montar el objeto (una
por línea): pásalas como `ramas_conocidas` si mides el aviso sobre `head/PLAN.md` o `base/PLAN.md`.

## 2. Qué te pido, numerado

1. **El reconocedor de ramas** (`_PREFIJOS_RAMA`, `_RE_RAMA`). ¿Reconoce las ramas reales de este
   repo —`claude/<nombre-con-hash>`, `docs/cierre-117`, `feat/…`, `codex/…`— escritas como se
   escriben en `PLAN.md` (entre backticks, entre paréntesis, al final de una frase con punto), y deja
   fuera las rutas? Busca falsos positivos y falsos negativos con ejemplos concretos, y dictamina si
   el lookbehind y el lookahead hacen lo que dice su comentario.
2. **La distinción ruta/rama** (`_RE_EXTENSION`, el parámetro `es_ruta`, `_es_ruta_del_repo`). ¿Es
   correcta y suficiente? ¿Qué ramas legítimas descarta como rutas, y qué rutas deja pasar como
   ramas?
3. **El troceo por filas de tabla.** ¿Cada fila es su propio ítem, el separador no lo es, y lo que va
   fuera de la tabla sigue siendo el ítem del encabezado? Revisa casos de borde: separadores de
   alineación (`:---:`), filas dentro de citas (`> |`), filas sin celda inicial, tablas dentro de un
   bloque de código cercado.
4. **Contratos que no deben cambiar.** El tipo de retorno; los seis tests previos del aviso,
   intactos; el llamador sin `es_ruta` y la compatibilidad con los tests que doblan la función con
   dos argumentos. ¿Cambia algo más del comportamiento de `session_close` fuera de este aviso?
5. **La medición del §4 del plan** (de 49 avisos a 1, y a 0 tras retirar la nota). ¿Se reproduce
   sobre `head/PLAN.md` con el código de `head/`, y qué da el código de `base/` sobre `base/PLAN.md`?
   Ten en cuenta que las ramas que git conoce hoy no son las del momento en que se midió.
6. **Los tests nuevos** (`test_303_*` en `head/tests/test_session_close_aviso.py`). ¿Prueba cada uno
   lo que su nombre dice? ¿Alguno pasaría con una implementación equivocada? Si puedes, introduce en
   una copia tuya una variante defectuosa concreta del código y di qué test la detecta y cuál no.
7. **El §5 del plan** («lo que no cubre»). ¿Alguno de esos límites es en realidad un defecto que
   merece remedio ahora?

## 3. Formato del informe

Escribe `INFORME.md` en tu directorio de trabajo, en castellano. Por cada hallazgo: identificador
(H-01, H-02…), **severidad** (alta · media · baja) y **coste del remedio** (trivial · acotado ·
estructural), dónde (fichero:línea en `head/`), la evidencia reproducible y el remedio que propones.
Añade una sección «Lo que intenté refutar y no pude» y otra «SIN VERIFICAR».

No encontrar defectos es un resultado legítimo: si es tu conclusión, dilo, con la evidencia de lo
que probaste. Termina el informe con una línea que contenga solo el veredicto, uno de: SHIP,
LISTA-CON-CAMBIOS, REQUIERE-REVISION, NO-SHIP.

Como último mensaje, da la ruta de `INFORME.md` y su SHA-256 calculado sobre el contenido en UTF-8,
con saltos LF y un único salto final.

## 1. Informe recibido, sin modificar (Codex, 2026-09-26)

<!-- informe-literal:inicio:bhxg -->
Higiene: al abrir había `_stdout.log` además de los seis elementos autorizados; no lo leí. `scratch/` e `INFORME.md` los creé para esta revisión.

# R1 adversarial — MEJORAS #303

Objeto: `ca250a4..8cebec4`, contrastado con el plan de `head/docs/superpowers/plans/2026-09-26-mejoras-303-aviso-plan-git.md`. Ejecuté únicamente código copiado en `scratch/`; `base/` y `head/` se leyeron como árboles de consulta. `ramas.txt` se pasó como `ramas_conocidas` en las mediciones. No consulté red, CRM, Drive ni el repositorio real.

## Hallazgos

### H-01 — Una tabla citada vuelve a mezclar filas

- **Severidad:** media. **Coste del remedio:** acotado.
- **Dónde:** `head/scripts/session_close.py:204-218`.
- **Evidencia reproducible:** con `## Cola\n> | 1 | sin commitear \`claude/a-111\` |\n> | 2 | cerrada \`claude/b-222\` |\n` y `ramas_conocidas={'main'}`, el resultado es `[('Cola', ['claude/a-111', 'claude/b-222'])]`. La segunda rama hereda la frase de la primera, porque `> |` cae en `buf` en lugar de cerrar cada fila. Una sola fila `> | 1 | ...` también sale titulada `Cola`, no `Cola — fila 1`. Markdown admite una tabla dentro de una cita; la regla anunciada «cada fila es su propio ítem» no se cumple ahí. No hay filas `> |` en los dos `PLAN.md` entregados.
- **Remedio:** reconocer el prefijo de cita al detectar la fila y separar cada fila citada sin hacer que la prosa de la cita herede sus frases. Añadir un test con dos filas citadas, una histórica y otra con rama podada.

### H-02 — La extensión confunde rutas borradas y ramas válidas

- **Severidad:** baja. **Coste del remedio:** acotado.
- **Dónde:** `head/scripts/session_close.py:59-64,198-200`.
- **Evidencia reproducible:** `docs/cierre-117.md` es un nombre de rama válido (`git check-ref-format --branch` devuelve 0), pero `Rama de trabajo: \`docs/cierre-117.md\`. Sin commitear.` devuelve `[]` aun con `es_ruta=lambda _: False`. A la inversa, `Sin commitear: \`docs/fichero-borrado.markdown\`.` devuelve `[('P', ['docs/fichero-borrado.markdown'])]`: el sufijo alfabético de ocho letras escapa al límite `{1,5}`, y el archivo borrado ya no existe para `_es_ruta_del_repo`. El plan declara el caso de ruta borrada **sin** extensión, pero no estos dos casos.
- **Remedio:** documentar la ambigüedad real entre nombres de rama y ruta y decidir una regla para las menciones explícitas a «rama» frente a las rutas documentales. Si se conserva el filtro por extensión, ampliar sus pruebas y su descripción para que no prometa cubrir cualquier extensión de letras. Un mero cambio a `+` arregla `.markdown`, pero agranda el falso negativo de ramas con sufijo alfabético.

### H-03 — Una fila sin primera celda pierde su identidad en el aviso

- **Severidad:** baja. **Coste del remedio:** trivial.
- **Dónde:** `head/scripts/session_close.py:214-216`.
- **Evidencia reproducible:** `## Cola\n| | sin commitear en \`claude/a-111\` |\n` devuelve `[('Cola — fila ', ['claude/a-111'])]`. La fila es independiente, pero el título queda vacío y no permite localizarla si hay varias filas así.
- **Remedio:** usar un identificador de reserva, como la línea física, cuando la primera celda esté vacía, y probar dos filas sin número.

### H-04 — Los diez tests nuevos dejan pasar una pérdida de filas indentadas

- **Severidad:** baja. **Coste del remedio:** trivial.
- **Dónde:** `head/tests/test_session_close_aviso.py:196-234` y `head/scripts/session_close.py:210`.
- **Evidencia reproducible:** en una copia cambié solo `ln.lstrip().startswith('|')` por `ln.startswith('|')`. Los diez `test_303_*` siguen verdes (`10 passed`), porque todas sus filas arrancan en la columna cero. Con `## Cola\n  | 7 | sin commitear en \`claude/indent-111\` |\n`, el código entregado devuelve `Cola — fila 7`; el mutante devuelve `Cola`. Como control, al suprimir `and not es_ruta(r)` en otra copia fallan los tests `un_directorio_que_existe_no_es_una_rama` y `sin_predicado_una_ruta_que_existe_en_el_repo_no_es_una_rama` (`2 failed, 8 passed`).
- **Remedio:** añadir un caso de fila indentada y otro de tabla citada. Probar el separador `:---:` de forma directa: por el tipo de retorno, procesarlo como fila sin frase no produciría salida y un aserto de `[]` no detectaría el defecto.

## Contraste de los siete puntos del mandato

1. **Reconocedor.** Reconoce `claude/x-123abc` entre backticks, `(docs/cierre-117)`, `feat/cosa.` al fin de frase y `codex/a-1`; la puntuación final se elimina con `rstrip('./')`. El lookbehind excluye `.claude/skills`, `core/docs/x` y `xclaude/y`. El lookahead impide aceptar solo el primer segmento de `docs/superpowers/plans/x.md`: la búsqueda da `[]`. Las dos afirmaciones del comentario son correctas para esos ejemplos. Nombres git válidos de varios segmentos (`feat/equipo/x`) y con caracteres no ASCII (`claude/niño`) no se reconocen; el primer límite está declarado en §5 y ninguno aparece en `ramas.txt`. `git check-ref-format --branch` aceptó ambos.
2. **Ruta/rama.** `docs/INDICE.md` se excluye por extensión, `docs/superpowers` por existencia en el árbol, y `docs/cierre-117` sigue siendo rama candidata. La clasificación no es completa: véase H-02. Una ruta borrada sin extensión, como `docs/carpeta-que-ya-no-existe`, sigue saliendo como rama; el plan lo reconoce. Una rama que coincida literalmente con un directorio existente también se descartaría por `es_ruta`.
3. **Tablas.** En filas normales, la frase de una fila no arma otra; la prosa y las notas fuera de las filas conservan el título del encabezado. `_RE_SEPARADOR_TABLA.match()` aceptó `|---|`, `|:---:|---:|` y `| :---: | ---: |`; en cualquier caso, esos separadores carecen de frase de pendiente y no producen aviso. Las citas y la celda inicial vacía se detallan en H-01 y H-03. Una tabla dentro de ` ``` ` se trocea y puede generar un aviso falso, tal como declara §5.
4. **Contratos.** El retorno sigue siendo `list[tuple[str, list[str]]]`. Los seis tests anteriores del aviso son idénticos en `base/` y `head/`; también lo es el resto del fichero de tests fuera de la inserción #303. Los 43 tests del fichero pasaron en copia. `_avisar_plan_desfasado()` sigue llamando con dos argumentos, y los dos dobles de dos argumentos pasan. El resto de `scripts/session_close.py` a partir de la sección de higiene permanece idéntico; el diff solo cambia este aviso dentro del script.
5. **Medición §4.** Con `base/scripts/session_close.py` sobre `base/PLAN.md`, hay **1 ítem con 56 tokens**, todos `docs/…`; con `head/scripts/session_close.py` sobre `head/PLAN.md`, **0**. Al reponer solo la mención antigua de `claude/verificar-pull-hash` en el texto de `head/PLAN.md`, el código de `head/` devuelve **1** aviso para esa rama. Así se reproducen el paso a uno y el paso a cero, pero **49 no es el resultado del par base entregado**. El plan refiere una medición histórica sobre otro estado de `main`; ese estado y sus refs no están en el objeto.
6. **Tests nuevos.** Los de ruta `.md`, rama `claude`, rama `docs`, directorio existente y prefijo `.claude` cubren sus casos concretos. Los de frase entre filas y número de fila detectan mezcla de filas o pérdida del título. `lo_que_va_fuera_de_la_tabla_no_hereda...` detecta que una frase de otra fila se propague a la nota; `...sigue_siendo_el_item_del_encabezado` comprueba el título, aunque también pasaría sin trocear la tabla. `sin_predicado...` sí ejercita el predicado por defecto, pero depende de que `docs/superpowers` exista en el árbol de pruebas. H-04 demuestra una variante defectuosa que los diez dejan pasar.
7. **Límites §5.** Las ramas con más de un segmento, la ruta borrada sin extensión y la heurística de «sin commitear» son límites expresos de este aviso no bloqueante; no encontré evidencia en los árboles entregados de que exijan ampliar ahora el diseño. La tabla en un bloque cercado también es un falso aviso reproducible, pero no hay una así con frase y rama en `PLAN.md`; puede quedar documentada. El caso de tabla citada de H-01 sí contradice la regla general de granularidad y merece prueba y remedio en esta ronda. H-02 completa la declaración de límites de la clasificación.

## Lo que intenté refutar y no pude

- La aceptación de las formas de rama usadas en el repo y la exclusión de rutas anidadas: pasaron los ejemplos anteriores.
- El separador de alineación y la independencia de las filas normales: pasaron las sondas y los tests pertinentes.
- La medición de uno y cero en §4: se reprodujo al reponer la nota retirada y al medir `head/PLAN.md` intacto.
- La compatibilidad de retorno, llamada con dos argumentos y seis pruebas anteriores: 43/43 tests del fichero pasaron en la copia.

## SIN VERIFICAR

- El recuento histórico **49** y los **400 PRs** citados en el plan: el objeto solo permite medir el `base/PLAN.md` entregado (56); no se consultó la historia git ni otra versión de `main`.
- La suite completa del repositorio y el comportamiento con un git vivo: no se ejecutaron. Solo corrí `head/tests/test_session_close_aviso.py` copiado, con `--basetemp=scratch/repro/pytest-temp` y sin `pytest-randomly`.
- La adjudicación de estos hallazgos contra la fuente corresponde a Claude.

## Integridad de los árboles

Al abrir: 1.430 archivos en `base/`, 1.431 en `head/`; SHA-256 del manifiesto UTF-8 de rutas y hashes: `400feff293612c1870bbd1c541573dbd7e02189c757204cf5a05b0df9b912bf2`. Al cerrar: el mismo digest; coinciden los 2.861 hashes individuales de apertura y cierre.

LISTA-CON-CAMBIOS
<!-- informe-literal:fin:bhxg -->

## 2. Evidencia verificada por mí al adjudicar

- **Digest.** Recomputado sobre el `INFORME.md` entregado (UTF-8, LF, un único salto final):
  `5b5ffda5ccc3da57191844b77ff3f48ae3663bae50715753d7a94ca354e63d6d`, **el mismo que declara el
  revisor en su último mensaje** (`_ultimo_mensaje.txt`). El fichero venía ya en LF con un solo
  salto, así que el digest del crudo y el del canónico coinciden: la cadena se verifica contra la
  salida del revisor, no solo contra sí misma.
- **La ronda terminó, y así se supo.** Dos vigías armados antes de lanzar, con las dos salidas
  —fin y muerte—. Uno de ellos saltó en falso al principio: el `Monitor` corre en bash y mi script
  era de PowerShell, así que murió por su propia sintaxis (código 2) sin mirar nada; se comprobó en
  el acto que Codex seguía vivo y se re-armó. Señal de fin: el `_exit.txt` del lanzador (`exit=0`,
  14:45:22) y el `-o` (14:45:22); `INFORME.md` cerrado a las 14:44:46; ningún `codex.exe` vivo
  sobre el directorio después. Ninguna de las cuatro muertes conocidas en el log.
- **Modelo y esfuerzo, releídos:** `gpt-6-sol` · `high` en el `turn_context` de
  `rollout-2026-09-26T14-36-43-01a0ddb7-c58e-7621-b13b-9e30fb43aeea.jsonl` (`originator:
  codex_exec`, CLI `0.155.0-alpha.16.4`) y en la cabecera del `_stdout.log`. Binario elegido por
  tener `codex-code-mode-host.exe` al lado (`13995fba801849b0`) y **sondado antes** con los tres
  flags (`C:\t\sonda-sol-303-1434`): `VIVO`. La velocidad `default` se **afirma** desde el lanzador
  conservado (`C:\t\mejoras-303-r1-1435-lanzador\_lanzar.ps1`); no se puede releer.
- **El objeto no se tocó, y lo mido yo, no solo él.** Antes de lanzar tomé mi propia huella de los
  2.861 ficheros de `base/` y `head/`, fuera del directorio del revisor; al cerrar, **cero
  diferencias**. Coincide con su comprobación (1.430 + 1.431, el mismo digest de manifiesto al abrir
  y al cerrar).
- **La línea de higiene del informe:** el `_stdout.log` que dice haber encontrado al abrir es la
  redirección de su propia salida que hace el lanzador (se crea al arrancar `exec`), no un fichero
  ajeno. Hizo bien en no leerlo.
- **Tokens y cupo, para la calibración** (releídos del rollout): 1.171.939 tokens totales, de los
  que 1.088.256 son entrada en caché; **entrada nueva + salida = 83.683**, la misma medida que la
  fila 1 del ledger. El contador semanal de la cuenta pasó del **75 % al 76 %** entre el primer y el
  último evento (12:37:02 → 12:45:20 UTC), **con otra ronda de otra sesión corriendo a la vez**
  (`C:\t\git-voz-alta-r1-1436`, `gpt-6-astra`·`medium`, y su sonda): el Δ es de la cuenta, no de
  esta ronda.
- **Los cuatro hallazgos, reproducidos contra la fuente y no contra el informe:**
  - **H-01.** El bucle de `_plan_items_desfasados` miraba `ln.lstrip().startswith("|")`: una fila
    `> | 1 | …` empieza por `>` y caía en el bloque del encabezado.
  - **H-02.** `_RE_EXTENSION` era `\.[A-Za-z]{1,5}$`: `.markdown` (ocho letras) y `.ps1` (con un
    dígito) no casaban, y un fichero borrado con esas extensiones salía como rama; al revés,
    `docs/cierre-117.md` es un nombre de rama válido y se descarta como ruta.
  - **H-03.** `"| | x |".strip().strip("|").split("|", 1)[0].strip()` da `""`: el título quedaba
    `«Cola — fila »`.
  - **H-04.** Ninguna fila de los diez tests empezaba con sangría, así que cambiar `lstrip()` por
    nada no ponía ningún test en rojo.
- **Y la cifra que no pudo reproducir:** el 49 del plan se midió sobre `4209582`, el `main` de antes
  del #398 y del #400; sobre `ca250a4`, el `base/` que recibió, el mismo aviso da 56, todas rutas
  `docs/…`. El plan decía «el `PLAN.md` de `main` del 2026-09-26» sin el commit, y lo corrige.
- **Adjudicación:** `docs/superpowers/plans/2026-09-26-mejoras-303-aviso-plan-git.md` §7.
