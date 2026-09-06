---
titulo: "El arnés de tests: paralelismo, doctrina y las dos técnicas que faltaban"
fecha: 2026-09-06
estado: implementado
rev: "2"
relacionado: "PLAN fila #22"
---

# El arnés de tests: paralelismo, doctrina y las dos técnicas que faltaban

> **Rev. 2 (2026-09-06), tras la R1 adversarial de Codex sobre el diff (`NO-SHIP`, 6 hallazgos
> numerados + 2 de secciones; **8 confirmados, 0 refutados**). Adjudicación en el **§4**.**
>
> Este plan **no existía cuando el trabajo empezó**, y decirlo es parte de él: decidí no escribirlo
> «para no meter ceremonia» cuando no había nada que adjudicar. La R1 devolvió ocho hallazgos, y una
> adjudicación de ocho puntos que vive solo en un mensaje de commit no está donde el contrato de
> gobernanza la busca. El plan se escribe *después*, para sostener la adjudicación — que es
> exactamente la función que el §5 del contrato le asigna.
>
> Radio de daño: no decide quién escribe sobre qué copia ni puede destruir datos de cliente →
> **una ronda**, sobre el diff (§4).

## 1. Por qué, y el número que lo decidió

La regla de las dos semillas —que existe porque una vez costó **ocho rojos que tres merges no
vieron**— costaba **743 s (12,4 min)** por aceptación. Una regla que cuesta doce minutos se salta
bajo presión: no era indisciplina, era el precio.

Dos objetivos, y todo se ordena por ellos: **ganar robustez** y **bajar el tiempo de escribir tests
de código nuevo**.

El momento tampoco fue casual: `main` limpia, 0 PRs abiertos, 0 ramas vivas. Cambiar el suelo bajo
los pies de quien trabaja solo es barato cuando no hay nadie encima.

## 2. Qué se cambia

**Paralelismo.** `pytest-xdist` en los sitios donde corre la suite **completa** —`session_close`,
`/tests` sin argumento, `/status`— y en ningún otro. `-n auto` **no** va en `addopts`, y eso está
medido: sobre un fichero suelto arrancar los workers cuesta más de lo que ahorra (17,0 s contra
11,9 s). Codex lo extendió a subconjuntos de 7 y 14 ficheros y la serie gana en los tres: no hay
punto de cruce a esa escala, así que la decisión se refuerza en vez de refutarse.

**`--dist loadgroup` acompaña siempre a `-n auto`.** Sin él las marcas `xdist_group` son decorado.
Ver §4, H-01.

**Doctrina en `CLAUDE.md` §Tests**: las dos semillas para aceptar, la prohibición de debilitar un
test para poner verde, y el bucle interno en serie.

**`hypothesis`**: 10 property tests sobre tres funciones puras de `core/utils.py` cuyo docstring ya
**afirmaba** una propiedad universal, más el arnés de mutación que las prueba
(`tests/_mutantes_propiedades_utils.py`, 12 mutantes).

**Un defecto de producción, encontrado por el camino.** `normalize_es_phone("0034 +34 600 111 222")`
devolvía `"+34600111222"` — con el `+34` que el CRM rechaza y que la función existe para quitar. Un
solo paso de limpieza donde hacen falta varios. Tres ficheros de tests de ejemplo la cubrían y
ninguno lo vio.

## 3. Lo medido

| | Antes | Después |
|---|---|---|
| Suite completa | 371 s | **94 s** |
| Aceptación con dos semillas | 743 s | **198 s** (la verja las corre sola) |
| `--runslow` en paralelo | — | 136 s, verde |
| Suite final | 4.656 | **4.670 / 0 fallos / 0 errores / 88 skip** |

El delta de conteo (+14 sobre el punto de partida) está explicado entero: 10 property tests, 4 del
guard de aislamiento.

**Arnés de mutación: 12 mutantes, 12 muertos, 0 mal apuntados.** De ellos, 7 no los mata
`tests/test_utils.py` — **y esa es toda la afirmación**: ver §4, «sección E».

## 4. Adjudicación de la revisión adversarial (Codex, 2026-09-06) — NO-SHIP, remediado

- **Objeto revisado:** el diff `b707df5..34ee6c0`
- **Ronda:** 1 (diff) — la única por radio de daño
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-06-arnes-de-tests-r1-adversarial-review.md`
- **Hallazgos:** 8 — **8 confirmados, 0 refutados**
- **Remediado en:** commit `691f5e4`; esta rev. 2 del plan

**Custodia:** objeto en copias externas con `git archive`; `sha256` de `diff.patch` idéntico al
abrir y al cerrar, y coincidente con el declarado en el mandato. El revisor pudo **ejecutar** la
suite: se instalaron `pytest-xdist`, `hypothesis` y `pytest-randomly` en el Python de sistema
expresamente para esta ronda, porque sin ellos habría sido una revisión de lectura sobre un diff
que consiste enteramente en mediciones.

**El diff remediado (`691f5e4`) NO se ha vuelto a revisar**, y se dice.

### H-01 — ALTO — CONFIRMADO, reproducido en el repo vivo

`tests/test_guard_localizador.py` escribe sondas dentro de `core/` **real** y otros de sus tests
**escanean `core/` entero**. `pytest tests/test_guard_localizador.py -n 4` → 3 rojos.

Mi validación —«conteo idéntico, cero tests serializados»— era **cierta como hecho y falsa como
inferencia**. Las tres corridas verdes de la suite lo fueron por **suerte de reparto**. Y peor que
el rojo: el revisor reprodujo el **verde**, un test pasando sin analizar su propio caso porque leyó
la sonda de otro worker y el número coincidió. Un conteo que cuadra no detecta eso.

**Remedio, y por qué no el evidente:** `pytestmark = pytest.mark.xdist_group(...)` + `--dist
loadgroup`. Renombrar las sondas por worker **no habría bastado**: como el escáner recorre el árbol
entero, el compartido es el **directorio**, no el nombre.

Frontera hecha permanente en `tests/test_guard_aislamiento_paralelo.py`, con las dos mitades
—quien escribe se declara, y todo lanzador pasa el flag—, 4 mutantes, 4 muertos. La búsqueda de
otros ficheros con el mismo patrón (por AST) devolvió **ninguno**: la frontera estaba acotada.

### H-02 — MEDIO — CONFIRMADO (la mitad, encontrada por mí antes del informe)

M06 esperaba un test de menos, por la misma frontera que M05 y M07 —que yo había arreglado uno a
uno—. Y M08 esperaba un test **imposible** de matar: sus ocho entradas se rechazan antes de llegar
a la guarda que el mutante retira. El arnés no lo denunciaba porque exigía que muriera *alguno* de
los esperados, no todos; ahora avisa de los que no mueren, que es como una expectativa imposible se
vuelve visible.

### H-03 — MEDIO — CONFIRMADO, y converge con un defecto que encontré yo

`_corre()` confundía **tres estados en uno**: verde, rojo e **inválido**. Un fichero inexistente
daba `set()`, idéntico a «todo verde»; un `PYTEST_ADDOPTS='-x'` heredado convertía un mutante
`AMBOS` en `SOLO LA PROPIEDAD` — que es la medición estrella del arnés. Ahora se mide por **JUnit
XML**, con el entorno neutralizado y comprobación de ejecución completa.

Y el arnés mutaba **antes** de comprobar que podría restaurar. Eso me mordió el mismo día: una
interrupción a mitad dejó `core/utils.py` en su versión buggy en el árbol de trabajo. Preflight de
git antes de la primera escritura, red `atexit` + señales, y `_restaura` limitado a los ficheros que
muta en vez de `git checkout -- .`.

### H-04 — MEDIO — CONFIRMADO, y el más instructivo

`normalize_es_phone` devolviendo **siempre cadena vacía** pasaba mis dos propiedades: son de
**ausencia** («es idempotente», «no lleva prefijo») y `""` las cumple. Igual con
`exigir_componente_de_ruta` lanzando siempre: «lo que pasa el guard cumple X» se satisface en vacío.
La guarda inerte, escrita por mí en el sitio donde más aviso tenía.

**Y mi primer arreglo también estaba mal**, que es la parte útil: aserté «el último dígito
sobrevive» y hypothesis encontró `'+34+34+340034'` → `''`. Una cadena hecha solo de prefijos
normaliza a vacío y eso es **correcto**. El aserto no era débil: era **falso**. La forma correcta no
era parchear el caso sino enunciar el contrato sobre el dominio donde existe — dado un teléfono
español bien formado, devuelve sus nueve dígitos.

### H-05 — MEDIO — CONFIRMADO

Faltaban `hypothesis` y `pytest_randomly` en `DEPS_DE_COLECCION`. Peor de lo que parece: sin
`hypothesis` la **colección** aborta y la verja lo presenta como «Tests fallando», así que la
distinción que `xdist` venía a comprar —«no pude medir» frente a «está rojo»— se perdía justo en el
caso que más la necesita.

### H-06 — BAJO — CONFIRMADO

Git **no admite comentarios al final de una regla** de `.gitignore`. Mi línea era un patrón literal
que no casa con nada. Lo tapaba por accidente el `.gitignore` con `*` que hypothesis escribe dentro
de su propio directorio — el revisor lo señaló y por eso la severidad es baja, no porque la regla
funcionara.

### Sección E — CONFIRMADO — un sobre-anuncio mío

«N mutantes que solo caza la propiedad» se mide **solo contra `tests/test_utils.py`**, que es lo que
declara `FICHEROS`. Yo lo leí —y lo comuniqué— como si fuera frente a la suite entera. El revisor
probó cinco de ellos contra `test_ensure_case_sumidero*.py` y **los mata también**. La salida del
arnés lo dice ahora explícitamente, y ni él ni yo hemos verificado si M01 es exclusivo globalmente.

### Sección G — CONFIRMADO — la regla que escribí y no hacía cumplir

`CLAUDE.md` exigía dos semillas para aceptar y `session_close` corría **una**, sin semilla fija, y
aun así imprimía «puedes continuar». Seguir el cierre documentado **no acreditaba** la regla que el
propio repo acababa de escribir. La verja las corre ahora, con semillas fijas para que el rojo sea
reproducible.

### Lo que el revisor NO refutó, y conviene no sobrecorregir

- Comparó los JUnit **test a test** entre serie/777, paralelo/777 y paralelo/31337: los mismos 4.663
  identificadores con **idéntico estado individual**. Es una comprobación más fuerte que la mía
  —que solo cuadraba totales— y aguanta.
- El benchmark de subconjuntos (1, 7 y 14 ficheros) **favorece la serie en los tres**: no refuta
  dejar `-n auto` fuera de `addopts`.
- **Refutó la sospecha de estrategias vacuas**: 203 de 400 ejemplos generan el prefijo doble y 400
  de 400 `case_id` son válidos.
- Mis tiempos (371/94, 17,0/11,9) quedan **SIN VERIFICAR** en su entorno —10 workers, Python de
  sistema, caché de `tldextract` fría—, que es lo correcto: no los declara falsos.

### El patrón que atraviesa la sesión, y que vale más que los ocho

**Cinco veces remedié el ejemplo en vez de la frontera** de la que era ejemplo: M05/M07, luego M06,
luego M01/M02/M11. Cada vez amplié el mutante concreto que el informe señalaba y el siguiente volvió
a salir por lo mismo. Lo que fallaba no era el caso: un `esperado` describe **la frontera que el
mutante ataca**, y varios tests pueden vigilarla desde sitios distintos.

Y la instancia más cara fue mía y no del revisor: **la mitad del guard nuevo nació decorada**.
Comprobaba `"--dist loadgroup" in texto`, y la cadena aparecía en el **comentario** que explica por
qué el flag hace falta — el guard pasaba gracias a su propia documentación. Dos funciones más
arriba yo había escrito, ese mismo minuto, que no se busca con `in` sobre la fuente «para no contar
una mención dentro de un comentario». Lo cacé porque muté mi propio guard antes de creérmelo.

## 5. Fase 4 — `syrupy` ✅

Piloto `core/email_atomize/render.py`, elegido midiendo: 4 funciones `render_*` con **159 líneas y
39 asserts** a mano dedicados solo a ellas, la mayor concentración del repo. Snapshot para la
**forma**; los asertos de **contrato** («la firma no aparece», «la cita vetada no entra») se quedan
sin tocar, porque un snapshot congela la salida *defecto incluido* y los aprobaría.

La regla del `--snapshot-update` se escribió **antes** del primer snapshot, y se aplicó también a la
primera generación: leí las 198 líneas archivadas antes de darlas por buenas.

**Que no sean decorado, medido:** tres mutaciones sobre `render.py` ponen rojos **1, 2 y 5**
snapshots, en proporción a su radio — discriminan, no solo se disparan.

## 6. Fase 5 — `diff-cover` ✅

Las dos mediciones que el plan exigía antes de fijar nada:

- **Sobrecoste de `--cov` con `-n auto`: +8 s sobre 74 s (+11%).** Mucho menos de lo temido, y eso
  es lo que lo hizo caber **dentro** de `session_close` en vez de en un comando aparte que nadie
  correría. Va como **aviso**, no como verja: el patrón que este script ya usa para todo lo que no
  es la suite.
- **Umbral: 90%.** Elegido midiendo y no por redondo — sobre este diff daba 93% y se deja una línea
  de holgura. Un umbral pegado a la medición del día se pone rojo con la primera línea
  razonablemente no cubrible, y un aviso que grita siempre se ignora siempre.

**Y el instrumento se justificó dos veces el mismo día, apuntándome a mí:**

1. Primera medición: **68%**. Lo que faltaba era la **rama de fallo de la propia verja** — la que
   dice cómo reproducir un rojo, o sea código que solo corre el peor día. Se probó (extrayendo
   `correr_la_verja` de `main()`, el mismo movimiento que `conftest.py` hizo con
   `restaurar_config_si_secuestrada`) y subió a **93%**.
2. Tras añadir el propio medidor: **62%**. Lo que faltaba era
   `_avisar_cobertura_del_diff` entera: veinte líneas que **producen el número** y que no probaba
   nadie. Si estuviera roto, el aviso mentiría y nadie lo sabría. Probada → **92%**.

En los dos casos la respuesta fue escribir el test, no bajar el umbral. Eso queda escrito en
`CLAUDE.md` como la respuesta por defecto.

## 7. Un defecto que me repetí a mí mismo, y su guard

Al añadir `coverage.xml` al `.gitignore` puse un **comentario al final de la regla** — exactamente
el H-06 que acababa de arreglar, tres líneas más arriba, en el mismo fichero.

El guard existente (`test_ninguna_regla_de_gitignore_es_inerte`) **no podía verlo**: una regla con
comentario no casa con nada, así que ningún fichero trackeado se ve afectado y aquel se queda verde.
Son dos formas distintas de que una regla no muerda. Cerrado con
`test_ninguna_regla_lleva_comentario_al_final_de_la_linea` en ese mismo fichero, con su detector
probado en las dos direcciones y un mutante que lo mata.

Que la clase se repitiera **dentro de la misma sesión en que la documenté** es el argumento de que
un guard hace falta y una nota no basta: el resultado *parece correcto al leerlo*.
