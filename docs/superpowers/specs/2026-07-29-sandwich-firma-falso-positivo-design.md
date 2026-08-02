# Diseño — La firma no es una respuesta intercalada: falso positivo de `_sandwich` que bloquea la Capa B

> **Estado:** **rev. 2** (2026-07-29), tras revisión adversarial de Codex con veredicto **NO-SHIP**
> sobre la rev. 1. **La decisión de la rev. 1 era insegura y se ha sustituido** (§3, §4 y §9).
> **Alcance:** un detector de `core/email_atomize/inline.py`. No toca la atribución, ni el recorte
> del cuerpo, ni la enumeración.
> **Disparador:** hallado midiendo la verificación en vivo de `MEJORAS #98` sobre una etiqueta real
> de Gmail (caso `W-02TH0W`): un hilo de 4-5 mensajes producía **una sola ficha**.
> **Fuera de alcance:** la ficha de identidad cierta para intercaladas reales (backlog, §7), el
> contenido de los adjuntos en MD (`MEJORAS #87`), el consumo por la sala de lectura (`#86`).

## 1. El defecto

`segmentar_html` decide si un correo HTML es una **respuesta intercalada** con `_sandwich`
(`inline.py:746-757`): recorre la secuencia de trozos que produce `_QuoteHTMLParser` —`"Q"` por
contenedor de cita, `"A"` por texto fuera de la cita— y devuelve `True` si aparece una `"A"` entre
dos `"Q"`. Si es `True`, devuelve `Segmentacion(..., ancestros=[])`: **cero ancestros**.

Y el bucle de reconstrucción de Capa B itera sobre `seg_total.ancestros` (`inline.py:948`). Con la
lista vacía, **nada de la Capa B llega a ejecutarse**: ni el body-scan del remitente, ni la forma
c′, ni el desanidado del interior reenviado. Los mensajes citados no reciben ficha, y el portador
solo deja una fila `info` con motivo `intercalada_no_segmentada` en `_revision/cola.md`.

El cuerpo, en cambio, **sí se recorta**, porque esa decisión la toma otro detector
(`_segmenter.cortar_autor`, vía `bodies.extraer_cuerpo`) que en estos correos dice, correctamente,
que **no** hay intercalada: son top-posts limpios.

Resultado: los mensajes citados no están como ficha (los bloqueó `_sandwich`) **ni** dentro del
cuerpo del portador (se recortó legítimamente). Solo sobreviven en el `.eml` crudo, que es
justamente lo que el árbol de MD existe para no tener que leer.

## 2. La causa, medida

`_intercalada_plain` (`inline.py:574-587`), el detector equivalente sobre texto plano, **excluye**
las líneas que son marcador de cita (`_marca_linea`) o etiqueta de cabecera (`_RE_ANYLABEL`) antes
de considerarlas texto de autor. **`_sandwich` no excluye nada**: cuenta como autor cualquier trozo
de texto que no esté dentro del contenedor de cita.

**Pero la ausencia de esas dos guardas no explica el fallo.** Verificado: de los trozos que
disparan el sándwich en los casos medidos, **ninguno** habría sido excluido por `_marca_linea` ni
por `_RE_ANYLABEL`. Lo que los dispara es **la firma**: la de E&V va en HTML con cada línea en su
propio elemento y, en los hilos de Gmail, queda **entre** dos contenedores de cita.

### 2.1. Tres detectores distintos, y hay que no confundirlos

La rev. 1 mezcló dos. Son tres y miden cosas diferentes:

| Detector | Dónde | Sobre qué | Gobierna |
|---|---|---|---|
| `_sandwich` (DOM) | `inline.py:746` | la estructura HTML | si la Capa B segmenta |
| `cortar_autor` | `_segmenter.py:23` | la base MIME (plano preferente) | si el cuerpo se recorta |
| `_intercalada_plain` | `inline.py:574` | texto con líneas `>` | (lo usa el camino de texto plano) |

### 2.2. Cifras, con el detector que corresponde

Enfrentando el DOM contra `cortar_autor` (el que gobierna el cuerpo), solo lectura:

| | W-02VND1 (277 `.eml`) | Prueba `W-02TH0W` (29 `.eml`) |
|---|---|---|
| Coinciden en «no hay intercalada» | 237 | 21 |
| `cortar_autor` ve intercalada → el cuerpo se conserva íntegro | 15 | 1 |
| Sin HTML | 25 | 0 |
| **DOM sí / `cortar_autor` no → Capa B bloqueada** | **0** | **7** |

Y el desglose que decide el diseño — de los portadores en que **el DOM ve intercalada**, qué
envuelve a los trozos que lo disparan:

| | W-02VND1 | `W-02TH0W` |
|---|---|---|
| El DOM ve intercalada | **1** | 7 |
| **Todos** los trozos disparadores están bajo un contenedor de firma | 0 | **5** |
| Algún trozo **no** es firma → el veto es correcto | **1** | 2 |

Contenedor observado: `class="gmail_signature"` (15 apariciones). Y **`W-02VND1` contiene un
contraejemplo real** (el `.eml` en posición 145 al ordenar por ruta): DOM `True`, `cortar_autor`
`True`, y con texto de autor que **no** es firma entre las citas. Ahí el veto debe seguir puesto.

> **Errata 1 (2026-07-29, al construir — la fila «5» de arriba es incorrecta).** Aplicando la regla
> de §3 al corpus y leyendo el **veredicto** resultante, no la envoltura de los trozos, los
> portadores que cambian de veredicto son **3, no 5**; y los que conservan el veto, **4, no 2**.
> Confirmado dos veces: con una subclase del parser real y, después, con el código integrado
> (`segmentar_html` de verdad: 24 portadores con HTML, 7 vetados antes, **4 vetados después**,
> 3 trazas emitidas). La cifra es insensible al conjunto de marcadores —`gmail_signature` sola,
> `+signature` y `+firma` dan los mismos 3—.
>
> **Por qué la fila estaba mal:** de los 4 que conservan el veto, 2 no tienen contenedor de firma
> (los que esta tabla ya preveía) y **2 sí lo tienen** bajo `gmail_signature` pero **además**
> tienen texto de autor entre la segunda y la tercera cita (forma `A S5 Q S3 Q S20 A3 Q3`): el
> sándwich les dispara desde ahí, no desde la firma. «Todos los trozos disparadores son firma» se
> midió sobre parte de la secuencia, no sobre toda. **La decisión de §3 no se toca**: que los 4
> correctos sigan vetados es precisamente lo que había que demostrar.
>
> **Y DOS defectos que esta medición destapó, ausentes de la spec — los dos en la única dirección
> en la que §3 afirma que la regla no puede fallar:**
>
> 1. Una firma **sin cerrar al final del documento** deja el contador de profundidad de firma por
>    encima de 0, marca como firma **todo** el texto de autor posterior y la exclusión **levanta un
>    veto correcto**. Resuelto con un guard fail-closed: si la firma no está balanceada, sus trozos
>    vuelven a contar como autor, y se declara `motivo="firma_sin_cerrar"` cuando el desbalance es
>    lo que sostiene el veto.
> 2. Peor, porque el guard **no lo ve**: el ámbito de la firma podía **fugarse fuera de su
>    elemento**. Si la firma se abre dentro de un contenedor que cierra antes que ella, su entrada
>    queda huérfana en la pila de etiquetas; el contador sigue alto fuera de la firma y un cierre
>    suelto posterior lo devuelve a 0, con lo que el guard vuelve a considerar la firma fiable
>    mientras hay texto de autor marcado como firma. Reproducido, y el veto correcto se levantaba
>    con 2 ancestros. Resuelto dando por cerradas las entradas huérfanas **solo en la dimensión de
>    firma**, sin tocar la de contenedor: cambiarla movería la segmentación de correos que hoy
>    funcionan y la Capa A tiene que quedar byte-idéntica. Lo encontró la revisión de rama.
>
> **Frecuencia real, corregida:** una primera medición dijo «20 de 271 correos cierran con la firma
> abierta». **Es falsa**: se midió con un conjunto de marcadores más ancho (`signature`, `firma`)
> que el que se implementa (`gmail_signature`). Con el predicado que se envía y los dos arreglos
> puestos, el desbalance aparece en **1 de 271** (0 de 24 en la prueba, 1 de 247 en W-02VND1) y en
> ninguno llega a disparar. Los dos defectos estaban **armados y callados**. Ninguno de los dos
> arreglos cuesta un portador: 3 desbloqueados antes y después de ambos.

## 3. Decisión

**Los trozos de texto que viven dentro de un contenedor de firma no cuentan como «texto de autor»
a efectos del veto de `_sandwich`.**

Concretamente: `_QuoteHTMLParser` marca cada trozo con si está o no bajo un ancestro cuyo `class` o
`id` identifique una firma (`gmail_signature` es el observado; el predicado se escribe sobre el
atributo, no sobre el texto), y `_sandwich` **ignora esos trozos** al buscar el sándwich. Nada más
cambia: el trozo sigue enrutándose igual, el cuerpo sigue decidiéndose con su detector, y cualquier
trozo que **no** sea firma mantiene el veto intacto.

Tres razones:

- **Es estructural, no lexical.** Depende de cómo el cliente de correo marca su firma, no de un
  diccionario de palabras. La rev. 1 barajó una lista de términos (`Best regards`, `ENGEL`…) y se
  descartó porque mi propio clasificador dejó escapar 7 de 21 trozos: eran solo el **nombre** de la
  persona.
- **No puede levantar un veto correcto.** Solo resta trozos de firma del recuento; si queda un
  trozo de autor real, el sándwich sigue dando `True`. Medido: en `W-02VND1` la regla **no cambia
  nada** —su único caso conserva el veto— y en `W-02TH0W` arregla 5 y conserva 2.
- **Deja rastro.** Cuando la exclusión cambia el veredicto, el informe lo anota (§5): no se silencia
  un detector, se corrige y se declara.

## 4. Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| **Corroborar el veredicto del DOM con el texto aplanado** (era la decisión de la rev. 1) | **Insegura y falsa en su premisa.** `_html_a_texto` no genera líneas `>` —medido: 0 de 176 líneas que `_es_linea_citada` reconozca— y `_intercalada_plain` las necesita, así que el corroborador da **0 positivos en 281 correos con HTML**: corroborar equivale a **retirar el veto siempre**, no a conservar el detector como afirmaba la rev. 1. Y hay un contraejemplo real en `W-02VND1` (`.eml` 145) donde levantaría un veto correcto sobre una intercalada auténtica |
| **Lista de palabras de firma** | Frágil por definición, y ya falló: 7 de 21 trozos se escaparon por ser el nombre de la persona. El coste de un fallo es bloquear o desbloquear un caso entero |
| **Exigir que la `"A"` sea sustanciosa** (≥N palabras) | Umbral arbitrario sin dato que lo fije, y las intercaladas reales suelen ser cortas («de acuerdo», «esto no») — justo lo que quedaría fuera |
| **Retirar `_sandwich`** | Con la regla de §3 el detector sigue haciendo su trabajo en los 3 casos donde acierta (1 + 2 medidos). Retirarlo los perdería |
| **Que el cuerpo no se recorte cuando el DOM ve intercalada** | Conserva el texto pero **sin fichas** —no da la cronología— y reescribe el `.md` de todo atom donde dispare, rompiendo la byte-identidad de Capa A por una causa que es un falso positivo |

## 5. Qué cambia y qué no

**Cambia:** 5 portadores de la muestra de Gmail vuelven a segmentarse y sus mensajes citados entran
por el camino **normal** de Capa B, con todas sus guardas. Los IDs nuevos se acuñan al final del
contador: **no se renumera nada**.

**Impacto material, sin inflarlo:** segmentar no equivale a producir ficha. Según la revisión
adversarial, de esos 5 solo **2** generan candidatos (4 fichas nuevas `alta-reconstruida`, 0
upgrades); los otros 3 tienen bloques citados que el parser deja vacíos y solo producen punteros de
confianza baja. **Ese reparto se confirma en la verificación en vivo (§8), no antes.**

> **Errata 2 (2026-07-29, medida en la verificación en vivo del §8 — este párrafo promete de más).**
> No hay **ninguna** ficha nueva: **0**, no 4. El reparto real es 3 portadores desbloqueados (ver
> Errata 1) y **0 de los 3** genera candidato. La corrida sobre el corpus real dejó el árbol con los
> mismos 35 mensajes y los mismos 7 reconstruidos B que antes; el **único** fichero que cambió en
> todo el árbol fue `_revision/cola.md`. 0 upgrades, eso sí se cumplió.
>
> **Y el motivo, medido, va más allá de «no hay cabecera de donde atribuir»:** los `<blockquote>`
> de esos 3 portadores están **genuinamente vacíos**. Cada uno tiene 2 blockquotes, ambos con **0
> palabras**; `autor` acumula **todo** el texto del documento (279/216/216 palabras = `tokens_total`,
> así que no se pierde ni se enruta mal nada); no hay **ninguna** marca de cita (`escribió:`,
> `De:`, `From:`) en ese texto; y no aparece **ningún** `gmail_quote`. **Esos 3 correos no esconden
> historial citado: no tienen ninguno.** Sus blockquotes son cáscaras vacías de la plantilla HTML.
>
> | | antes | después |
> |---|---|---|
> | Filas de esos 3 portadores en `_revision/cola.md` | 3 (`intercalada_no_segmentada`) | 3 trazas + **6 punteros `sin_cabecera`** |
> | Extracto de esos punteros | — | **vacío (0 caracteres)** |
> | Mensajes citados recuperados | 0 | **0** |
> | Fichas nuevas | 0 | **0** |
>
> Las «9 citas» que una primera versión de esta errata anunciaba eran **6**: las otras 3 filas
> `html_quote` de la cola son preexistentes, de portadores ajenos. Y no llevan texto.
>
> **Lo que esto significa, sin adornarlo.** El arreglo es correcto —`_sandwich` clasificaba mal, y
> un correo cuyo único texto entre citas es su firma **no** es una respuesta intercalada— pero en
> este corpus **no recupera ningún contenido**. El motor sigue negándose a fabricar un remitente,
> que es lo que importa: la prime directive aguanta.
>
> **Y una consecuencia que hay que mirar, porque toca la premisa del §1:** el síntoma que abrió esta
> spec —un hilo de 4-5 mensajes que producía una sola ficha— **no lo explican estos 3 portadores**,
> que no tenían nada citado. Los otros 4 conservan el veto y son intercaladas auténticas. Dónde
> están los mensajes que faltaban en aquel hilo queda **abierto**, y el candidato natural es
> `MEJORAS #107` (historial citado sin atribuir), no este falso positivo. Anotado en
> `docs/MEJORAS_FUTURAS.md`.

**No cambia:** el recorte del cuerpo (su detector no se toca), la Capa A (byte-idéntica: no se
reescribe ninguna ficha existente), la atribución (mismas guardas), ni **nada en `W-02VND1`** (0
portadores afectados).

### 5.1. Traza, dedup y sellos

Tres cosas que la rev. 1 dejó sin cablear y que la revisión reclamó:

- **Transporte de la traza.** `Segmentacion` gana un contador `firma_excluida: int` (trozos de firma
  descartados del veto). `reconstruir` lo convierte en un puntero
  `estilo="firma_excluida_del_veto"`, `confianza="info"`, por el mismo camino por el que hoy emite
  el puntero de `motivo` (`inline.py:942`), de modo que `render_revision` lo escriba en
  `_revision/`. **Solo se emite cuando la exclusión cambió el veredicto**, no en cada correo con
  firma.
- **Dedup de las fichas nuevas.** Pasan por el índice de Capa A y el puente de `upgrades` que ya
  existen (`pipeline.py:201`). Expectativa medida a confirmar: 4 fichas nuevas, 0 upgrades. Si
  aparecieran upgrades, significa que esas citas eran copias de mensajes que ya son ficha, y eso es
  también un resultado válido — pero hay que verlo.
- **Los sellos anteriores son inmutables.** Una entrega ya sellada (`_entregas/…/_SELLO.md`) es un
  snapshot append-only: re-atomizar **no** la corrige. Tras revisar las fichas nuevas hay que
  **sellar una entrega nueva**, no dar por actualizada la anterior.

## 6. Contrato de tests

Reescrito tras la revisión: los tests 2 y 4 de la rev. 1 no mataban el camino inseguro.

1. **Firma entre citas no es intercalada.** HTML `blockquote` + `<div class="gmail_signature">` con
   varias líneas en `<div>`s + `blockquote` → `respuesta_intercalada=False` y `ancestros` no vacío.
2. **Intercalada real, ORDINARIA, sigue vetada.** HTML `blockquote` + `<div>` con una frase de autor
   que no es firma ni etiqueta + `blockquote`, **sin `>` literales ni artificios**: es la forma en
   que llega de verdad. → `respuesta_intercalada=True`, `ancestros=[]`. Sin este test el arreglo
   sería «desactivar el detector», y con la forma que pedía la rev. 1 (que el aplanado «también la
   viera») el test era **inconstruible**, porque el aplanado nunca ve citas.
3. **Un trozo de autor entre firmas mantiene el veto.** `blockquote` + firma + frase de autor +
   firma + `blockquote` → sigue `True`. Es el caso de los 2 portadores que conservan el veto.
4. **Emparejamiento remitente ↔ cuerpo, contra el motor real.** Un `.eml` con la forma medida
   produce **más de una ficha**, y para cada ficha nueva se fija **qué remitente va con qué cuerpo**
   —no basta con que el email aparezca en el `.eml`—. La revisión construyó un adversario en el que
   el remitente era literal y el cuerpo pertenecía a otro autor: ese es el fallo que este test debe
   matar.
5. **Capa A byte-idéntica contra un golden.** Hash de las fichas de Capa A **capturado antes del
   cambio** y comparado después. Comparar dos corridas posteriores al cambio no vale: una mutación
   determinista que ya ocurra en la primera pasaría inadvertida.
6. **La traza se emite una vez, para el portador correcto**, y el portador deja de aparecer con
   `intercalada_no_segmentada`.
7. **Regresión separada de `cortar_autor`:** los 16 casos de intercalada real medidos (15 de
   `W-02VND1` + 1 de la prueba) conservan el cuerpo íntegro. Se conserva como regresión de ese
   detector, **no** como protección de este arreglo — el cuerpo lo decide otro camino.

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| Un cliente que no envuelva su firma en un contenedor identificable → el falso positivo persiste ahí | Aceptado y declarado. La regla no puede fallar en la dirección peligrosa: si no reconoce la firma, el veto se mantiene y lo que se pierde es la promoción, no la corrección |
| Una intercalada real cuyos trozos de autor estén, todos, dentro de un contenedor de firma | Estructuralmente improbable (sería texto de respuesta metido dentro del bloque de firma) y detectable: el puntero de traza deja el rastro |
| Fichas nuevas de golpe en casos ya atomizados | Es el arreglo funcionando; IDs al final, sin renumerar. Se corre primero en la muestra pequeña y se miran una a una (§8) |
| Que la muestra (2 casos, 306 correos, un solo contenedor de firma observado) no represente otros clientes | Por eso la regla es aditiva y se anota; y por eso el impacto se confirma en vivo antes de tocar un caso grande |

## 8. Verificación en vivo

Sobre la copia local del caso `W-02TH0W` ya exportada al Escritorio (29 `.eml`, 7 portadores con
veto, 5 candidatos a arreglo): atomizar antes y después y comprobar (a) cuántas fichas nuevas
aparecen y si el reparto 2-de-5 se cumple, (b) que en cada ficha nueva el **remitente va con su
cuerpo**, (c) que las fichas que ya existían son byte-idénticas, (d) que el puntero de traza está.
**No** se ejecuta sobre `G:` sin autorización expresa; y en `W-02VND1` la regla no debería cambiar
nada, lo que es en sí una comprobación.

> **EJECUTADA el 2026-07-29** sobre la copia local, con autorización expresa de Nikolai y sin tocar
> `G:`. Resultado, punto por punto:
>
> - **(a) fichas nuevas: 0** — no las 4 que preveía el §5. Ver **Errata 2**. El reparto real es
>   3 portadores desbloqueados y ninguno genera candidato; lo que aparece son 9 citas en la cola de
>   revisión con su extracto, donde antes no había nada.
> - **(b) remitente ↔ cuerpo: NO EJERCITADO en vivo**, porque sin fichas nuevas no hay nada que
>   emparejar. Se ejercita en el test 4 del §6 contra el motor real con un portador sintético que
>   **sí** trae cabecera dentro del cuerpo citado: dos fichas, cada una con su cuerpo, y
>   `reconstruido_de` verificado. Queda declarado como cobertura de test, no de corpus.
> - **(c) fichas existentes byte-idénticas: SÍ.** De 73 ficheros del árbol, 0 borrados, 0 nuevos y
>   **uno solo** con hash distinto: `_revision/cola.md`. `mensajes` 28→28, `mensajes_fp` 7→7,
>   `adjuntos` 15→15, contadores idénticos: cero renumeraciones.
> - **(d) puntero de traza: SÍ**, exactamente 3 filas `firma_excluida_del_veto` / `info` /
>   `trozos_firma=28`, una por portador desbloqueado, y **0** portadores desbloqueados que sigan
>   declarados `intercalada_no_segmentada`. Los 4 cuyo veto es correcto **sí** siguen declarados.
> - **(e) upgrades: 0**, como esperaba el §5.1.
>
> **Contraprueba de `W-02VND1`: la regla no cambia nada, confirmado.** 247 portadores con HTML,
> **1 vetado antes y 1 después**, **0 trazas**. Se midió con `segmentar_html` integrado en vez de
> re-atomizar el árbol: con `firma_excluida = 0` en los 247 la Capa B es idéntica por construcción,
> y re-correr solo habría añadido a esa copia local los gemelos NFD de `MEJORAS #99.5` — ruido, sin
> información nueva sobre este cambio.

## 9. Adjudicación de la revisión adversarial (Codex, 2026-07-29) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-07-29-sandwich-firma-falso-positivo-design.md` rev. 1, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** no capturado — llegó por chat, antes del contrato de actas
- **Hallazgos:** 3 confirmados · 0 rebajados · 0 refutados · 1 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento; el escalado, en `MEJORAS #107`

El escalado es el hallazgo suyo fuera del alcance de esta spec (el cuarto test vacuo), que abajo se
anota y tiene entrada propia en el backlog.

**Los tres bloqueantes se aceptan; el primero obligó a cambiar la decisión.**

| # | Bloqueante | Verificación propia | Dónde queda |
|---|---|---|---|
| 1 | Corroborar con el aplanado levanta vetos correctos y admite una misatribución reproducible | **CONFIRMADO**: `_html_a_texto` da 0 líneas citadas de 176; el corroborador da **0 positivos en 281 correos**; el contraejemplo existe (`W-02VND1`, `.eml` 145) | §3 sustituida por la exclusión estructural; §4 registra la alternativa como descartada |
| 2 | Las cifras medían `cortar_autor`, no el corroborador propuesto | **CONFIRMADO**, y era un error de método mío | §2.1 separa los tres detectores; §2.2 rehace las tablas |
| 3 | Los tests 2 y 4 no matan el camino inseguro | CONFIRMADO por lectura | §6 reescrito: test 2 con intercalada ordinaria, test 4 fija remitente↔cuerpo, test 5 con golden previo |

**Matices donde no seguí al revisor:** propuso que **todos** los trozos disparadores eran firma; mi
medición dice que en 5 de 7 portadores lo son y en 2 no, y en `W-02VND1` su único caso tampoco. Uso
mi cifra, que es la conservadora y refuerza conservar el detector.

**Hallazgo suyo fuera del alcance de esta spec, anotado para no perderlo:**
`tests/test_email_atomize_inline.py:182` (`test_seg_html_token_conservacion_no_inventa`) solo
comprueba que un atributo sea `bool` — pasaría aunque se eliminara del todo la conservación de
tokens. Es un cuarto test vacuo de la misma familia que los otros tres de esta sesión y merece
entrada propia en `docs/MEJORAS_FUTURAS.md`.
