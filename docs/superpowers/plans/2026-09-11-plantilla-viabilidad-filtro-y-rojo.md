---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# El filtro del guion y el rojo del semáforo (`MEJORAS #242`, `#243`)

Las dos entradas que destapó la R1 de `MEJORAS #228`, cerradas juntas porque son el **mismo
artefacto binario** y el **mismo módulo de tests**: separarlas obligaba a tocar el `.xlsx` dos
veces, y cada toque de un binario es una oportunidad de perder algo sin verlo.

## 1. Qué se cambió, y qué se midió antes de cambiarlo

**`#243` — el filtro llegaba a la fila 88 y los 88 IDs llegan a la 103.** Doce preguntas —`tl_01`,
cinco `esc_*` y seis `rec_*`, o sea Team leader, Escritura y Reclamación— quedaban fuera del ámbito
del `autoFilter` que produce el guion de entrevista. Le quitaba la mitad del sentido a la pieza P5
del mismo día, que hizo que las 88 filas salieran marcadas.

La entrada pedía medir **si el rango corto protegía algo**, porque hay filas de sección
intercaladas. **No protegía**: ya había **ocho** dentro del rango (5, 29, 32, 44, 54, 58, 66, 83),
así que las tres que entran (89, 91, 97) no son una clase nueva de fila.

Y el rango vive en **dos** sitios: el `autoFilter` de la hoja y el nombre definido oculto
`_xlnm._FilterDatabase` del libro. Cambiar uno y no el otro deja el filtro a medias — tiene su
propio test y su propio mutante.

**`#242` — `E21` se veía ROJO estando en blanco.** Tenía un relleno sólido `FFFF0000` en su estilo
base, **bajo** el formato condicional: sin valor no se activa ninguna regla y lo que se ve es el
relleno. Un informe **sin valorar** enseñaba JURÍDICO en rojo puro, que ni siquiera es el rojo del
semáforo (`FFC7CE`). `E22` no lo tenía, así que las dos filas vacías se veían distinto.

Medido antes de quitarlo: era la **única** celda del libro con ese relleno, ningún documento del
repo le atribuye función, y el `xf` afectado (índice 104) lo usa **una sola celda**.

## 2. Cómo se tocó el binario, que es la mitad del trabajo

**A nivel de zip, no con openpyxl.** Cada entrada se copia byte a byte y solo se sustituyen tres
cadenas, en `sheet2.xml`, `workbook.xml` y `styles.xml`. Comprobado releyendo el zip resultante:
**9 entradas idénticas, 3 modificadas, ninguna otra**.

Un round-trip de openpyxl **regenera el libro entero**, que es literalmente lo que
`modelo_xlsx.md` prohíbe; que el cambio anterior (`MEJORAS #228`) saliera bien lo acreditó un
revisor comparando el zip **después**, no el método. Esto lo acredita por construcción.

El relleno 7 se queda en la tabla de `fills` aunque ya no lo use nadie: quitarlo renumeraría todos
los demás.

## 3. Adjudicación de la revisión adversarial (Codex, 2026-09-11) — LISTA-CON-CAMBIOS, remediado

- **Objeto revisado:** diff `b59bb49..722d063` — la plantilla `.xlsx`, sus tests y su documentación
- **Ronda:** R1 (única por presupuesto)
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` sin `.git`, solo lectura
- **Informe recibido:** 2026-09-11, `C:/t/rev-plantilla-1435/wd/INFORME.md`, 44023 bytes
- **Hallazgos:** 7 — 1 ALTO, 5 MEDIOS, 1 BAJO; **7 confirmados, 0 refutados**
- **Remediado en:** este §3 y el diff de la pieza

Acta: `docs/superpowers/plans/2026-09-11-plantilla-viabilidad-filtro-y-rojo-r1-adversarial-review.md`.

**El descarte primero, que vale tanto como un hallazgo:** comparó los dos `.xlsx` **a nivel de
zip** y confirmó las 9 entradas idénticas y las 3 modificadas, con solo las tres sustituciones
declaradas. Ésa era la amenaza real del cambio.

**Y lo que hizo que la ronda valiera:** no leyó mis tests, **los mutó**. Siete mutaciones del
binario **pasaban los 45 casos del módulo**.

### H-04, ALTO — el módulo aceptaba poner a cero la fórmula de los honorarios

`test_la_plantilla_conserva_sus_invariantes` comprobaba `F39` y ninguna de las otras tres fórmulas
de `INFORMACION`. Cambiar `H14` —`=H13/100*E14*1.21`, la que calcula los honorarios— por `=0`
dejaba **los 45 casos verdes**, y el error se propaga a `H16` y `H18`. Con H13=100.000 y E14=5 la
buena da 6.050 y la mutada 0. **Es el importe que lee el CFO.**

**De qué frontera es esto un ejemplo:** el invariante listaba una fórmula porque alguien escribió
una, no porque hubiera una. **Remediado**: las cuatro, comparadas como conjunto completo, de modo
que una fórmula nueva o desaparecida también se ve.

### H-01, H-02 y H-03 — mis tres guardas medían menos de lo que su nombre decía

| Guarda | Lo que de verdad comprobaba | Mutante que sobrevivía |
|---|---|---|
| el filtro «alcanza a todas» | **solo el último número** del rango | `B3:L103` (saca la columna M, que es la del guion) y `B100:M103` |
| el nombre definido «dice lo mismo» | igualdad de **cadenas**, sin ámbito | `localSheetId="0"` lo atribuye a `INFORMACION` |
| — | nadie miraba la protección | `autoFilter="1"` **prohíbe** usar el filtro |
| el semáforo «no pinta» | `patternType != "solid"` | un `patternFill darkGrid` rojo **también pinta** |
| `E21` «no perdió su estilo» | `font.b or font.sz`, verdadero con **cualquier** fuente | `fontId` 1→0: de Arial 8 a Calibri 11 |

Las tres son la misma forma: **una guarda que no puede dar el otro valor**. El de la fuente es
literal — `font.b or font.sz` es verdad para toda fuente que exista.

**Remediado**: el filtro se comprueba como **rectángulo** (inicio, columnas, y que toda fila con ID
caiga dentro, y que la columna M esté cubierta); el nombre definido, por **ámbito** y `hidden`; la
protección, con su propio test; «no pinta» pasa a ser **sin relleno** y se comprueba el bloque
`E:H` **entero** de las dos filas; y el estilo de `E21` se compara contra su **perfil medido**
—Arial 8, los cuatro bordes, centrado, formato— y no contra una verdad lógica.

El perfil sale de **leer el fichero**, no de mi memoria: la última vez que escribí de memoria una
lista así (los merges del semáforo, `MEJORAS #228`) omití una entrada.

### H-06 y H-07 — dos errores de prosa míos, y el segundo es el de siempre

- **H-06**: dije «siete filas de sección dentro del rango» y son **ocho** (olvidé la 5), y cambié
  los subtotales: son **cinco** `esc_*` y **seis** `rec_*`, no seis y cinco. El total, doce, sí
  estaba bien. Corregido en el CHANGELOG y en `#243`.
- **H-07**: escribí «**el rango corto era un residuo, medido**: acababa en la última fila de la
  sección 8 y las secciones 9-11 se añadieron después». Lo primero es un hecho; lo segundo es una
  **inferencia** que las dos copias no acreditan — las dos ya traen las once secciones y nada en
  ellas fecha cuándo entraron. Lo mismo con «ese rojo no cumplía ninguna función»: que nadie lo
  documentara prueba que **hoy nadie puede saberlo**, no que nunca la tuviera.

  Es [[feedback-no-lo-se-no-es-no-hay]] otra vez, y en la forma que más engaña: **una inferencia
  plausible presentada con la palabra «medido» al lado**. Corregido en los dos sitios, y lo que
  decide el cambio se sostiene sin la historia.

### H-05 — deuda preexistente, al backlog y no «de paso»

`PREGUNTAS` tiene **cinco** `<selection>` en su `<sheetView>` y el esquema admite cuatro. Idéntico
en las dos copias: ni lo introduje ni lo toqué. Va a **`MEJORAS #248`**. Arreglarlo aquí habría
sido una cuarta modificación del binario metida dentro de una auditoría, sin ronda propia y sin que
nadie la hubiera pedido.

### El resultado del control positivo, tras remediar

**11 mutantes, 11 muertos**: los 4 míos y los **7 que el revisor midió vivos**. Cada uno mata el
test que dice vigilar, y la plantilla se restaura por `sha256` tras cada corrida.

## 4. Lo que sigue sin verificarse

**Y no lo puede hacer una máquina:** abrir el `.xlsx` en Excel y ver que el desplegable del
semáforo se despliega, que la alerta salta al teclear un valor fuera de la lista, y que el filtro
de `PREGUNTAS` se aplica sobre las 101 filas. El revisor no pudo abrir Excel y su lectura viene del
XML. **Queda pedido a Nikolai.**

Tampoco se corrieron las dos semillas en el entorno del revisor (su Python de sistema no trae
`pytest-randomly`); eso lo cubre el autor antes de mergear, no el acta.
