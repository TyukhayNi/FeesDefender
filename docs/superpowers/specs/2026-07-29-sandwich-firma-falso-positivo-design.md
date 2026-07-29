# Diseño — La firma no es una respuesta intercalada: falso positivo de `_sandwich` que bloquea la Capa B

> **Estado:** rev. 1 (2026-07-29). Spec **corta** a propósito: el cambio es pequeño, pero decide
> si un cuarto de los portadores de un caso se atomiza o no.
> **Alcance:** un detector de `core/email_atomize/inline.py`. No toca la atribución, ni el recorte
> del cuerpo, ni la enumeración.
> **Disparador:** hallado midiendo la verificación en vivo de `MEJORAS #98` sobre una etiqueta real
> de Gmail (caso `W-02TH0W`): un hilo de 4-5 mensajes producía **una sola ficha**.
> **Fuera de alcance:** la ficha de identidad cierta para intercaladas reales (queda en backlog,
> ver §6), el contenido de los adjuntos en MD (`MEJORAS #87`), el consumo por la sala de lectura
> (`#86`).

## 1. El defecto

`segmentar_html` decide si un correo HTML es una **respuesta intercalada** con `_sandwich`
(`inline.py:746-757`): recorre la secuencia de trozos que produce `_QuoteHTMLParser` —`"Q"` por
contenedor de cita, `"A"` por texto fuera de la cita— y devuelve `True` si aparece una `"A"` entre
dos `"Q"`. Si es `True`, devuelve `Segmentacion(..., ancestros=[])`: **cero ancestros**.

Y el bucle de reconstrucción de Capa B itera sobre `seg_total.ancestros` (`inline.py:946`). Con la
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

Medición sobre correo real, solo lectura, con los dos detectores enfrentados:

| | W-02VND1 (277 `.eml`) | Prueba `W-02TH0W` (29 `.eml`) |
|---|---|---|
| Los dos coinciden en «no hay intercalada» | 237 | 21 |
| El de plano ve intercalada → el cuerpo se conserva íntegro | 15 | 1 |
| Sin HTML | 25 | 0 |
| **Discrepancia: DOM sí, plano no → Capa B bloqueada** | **0** | **7 (24 %)** |

Y **qué son** los 21 trozos que el DOM contó como texto de autor entre las dos primeras citas de
esos 7 portadores:

| | trozos |
|---|---|
| Firma o pie legal (`Best regards`, `Senior Consultant`, `ENGEL & VÖLKERS`, `EV MMC SPAIN`, teléfono, `www.…`) | 14 |
| Línea de atribución o de cita | 0 |
| Resto | 7 — los siete son la **línea del nombre** de la misma firma |

**Los 21 son firma. Ni uno es texto real de autor.** La firma de E&V va en HTML con cada línea en
su propio elemento, y en los hilos de Gmail queda **entre** contenedores de cita, así que dispara
el sándwich.

Dos consecuencias para el diseño:

1. **No es sistémico: depende del cliente de correo.** Cero en W-02VND1 (Apple Mail / Outlook), 24 %
   en el caso de Gmail. Ni urgente para Tibidabo ni despreciable en Valencia.
2. **En 306 correos reales, `_sandwich` ha producido 7 falsos positivos y 0 verdaderos positivos.**
   Los 16 casos de intercalada real los detectó el de texto plano, no él.

## 3. Decisión

**El veredicto del DOM exige corroboración del texto aplanado, y cuando se descarta se anota.**

Concretamente, en `segmentar_html`: si `_sandwich(seq)` dice intercalada **pero** el detector de
texto plano sobre el aplanado (`_intercalada_plain(_html_a_texto(html))`) dice que no, **el
veredicto del DOM se descarta** y la segmentación sigue su curso normal.

Tres razones:

- Es donde la pregunta es verificable línea a línea, y donde ya viven las guardas de marcador y
  etiqueta que a `_sandwich` le faltan.
- No debilita la atribución: al descartar el veto, el segmento pasa por el camino **normal** de
  Capa B, con todas sus guardas (anclaje obligatorio, guarda de ambigüedad, tope a
  `media-reconstruida` para lo levantado del cuerpo). No se inventa ningún remitente.
- La medición dice que ese veto no ha acertado nunca en 306 correos, mientras cuesta un cuarto de
  los portadores de un caso.

**Y no se silencia: se registra.** Cada descarte añade un puntero `estilo="sandwich_descartado"`,
`confianza="info"` a `_revision/`, con el portador. Si algún día el veto era correcto, se verá en la
cola en vez de desaparecer — es la diferencia entre corregir un detector y taparlo.

## 4. Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| **Lista de palabras de firma** (`Best regards`, `ENGEL`, teléfonos…) para excluir esos trozos | Es exactamente lo que falló al clasificar: 7 de 21 trozos se escaparon de mi propia lista por ser solo el **nombre** de la persona. Una heurística que depende de un diccionario de firmas se rompe con cada plantilla nueva, y aquí el coste de un fallo es bloquear un caso entero |
| **Exigir que la `"A"` sea sustanciosa** (≥N palabras, o ≥N caracteres acumulados) | Umbral arbitrario sin dato que lo fije, y las respuestas intercaladas reales suelen ser cortas («de acuerdo», «esto no»), justo lo que quedaría fuera |
| **Retirar `_sandwich`** | Tentador con 0 aciertos en 306 correos, pero ausencia de verdaderos positivos en dos casos no es prueba de que nunca acierte. Corroborar conserva el detector y lo vuelve auditable |
| **Que el cuerpo no se recorte cuando el DOM ve intercalada** | Era mi primera hipótesis y es peor: conserva el texto pero **sin fichas**, no da la cronología, y reescribe el `.md` de todo atom donde dispare, rompiendo la byte-identidad de Capa A por una causa que resulta ser un falso positivo |

## 5. Qué cambia y qué no

**Cambia:** en los casos con hilos de Gmail, los portadores afectados vuelven a segmentarse y sus
mensajes citados reciben **ficha propia con su remitente**, por el camino normal de Capa B. Los IDs
nuevos se acuñan al final del contador: **no se renumera nada**.

**No cambia:** el recorte del cuerpo (su detector no se toca), la Capa A (byte-idéntica: no se
reescribe ninguna ficha existente), la atribución (mismas guardas), ni el comportamiento en
W-02VND1 (0 discrepancias medidas → 0 fichas nuevas allí).

## 6. Contrato de tests

1. **Firma entre citas no es intercalada:** HTML con `blockquote` + bloque de firma en `<div>`s +
   `blockquote` → `segmentar_html` devuelve `respuesta_intercalada=False` y `ancestros` no vacío.
   Es el caso medido, con la firma real de E&V como fixture.
2. **Intercalada de verdad sigue vetada:** HTML con `blockquote` + una frase de autor de varias
   palabras que **no** es firma ni etiqueta + `blockquote`, donde el aplanado también la ve →
   `respuesta_intercalada=True`, `ancestros=[]`. Sin este test, el arreglo sería «desactivar el
   detector».
3. **El descarte se anota:** cuando el veredicto del DOM se descarta, aparece el puntero
   `sandwich_descartado` en la salida de revisión.
4. **Contra el motor real, end-to-end:** un `.eml` con la forma del caso medido produce **más de una
   ficha** (hoy produce una), y el remitente de cada ficha nueva es **literal** en el `.eml` fuente
   — cero misatribución, verificado sobre el fichero, no sobre un doble.
5. **No regresión de Capa A:** el `.md` del portador es byte-idéntico antes y después (el recorte
   del cuerpo no se toca).
6. **Los 16 casos de intercalada real de la medición** (15 de W-02VND1 + 1 de la prueba) siguen con
   el cuerpo íntegro: su detector es el de plano y no se modifica.

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| Que un correo genuinamente intercalado cuya alternancia se pierda al aplanar pase el veto y se segmente mal | Las guardas por segmento de Capa B siguen puestas (anclaje obligatorio, ambigüedad, tope de confianza). Y el puntero `sandwich_descartado` deja el rastro para poder auditarlo |
| Que aparezcan fichas nuevas de golpe en casos ya atomizados | Es el arreglo funcionando: son mensajes que estaban perdidos. IDs al final, sin renumerar. Conviene correrlo primero en un caso pequeño y mirar las fichas nuevas una a una |
| Que la medición (2 casos, 306 correos) no represente otros clientes de correo | Por eso se corrobora en vez de retirar el detector, y por eso el descarte se anota |

## 8. Verificación en vivo

Sobre la copia local del caso `W-02TH0W` ya exportada al Escritorio (29 `.eml`, 7 portadores
afectados): atomizar antes y después, y comprobar (a) cuántas fichas nuevas aparecen, (b) que el
remitente de cada una es literal en su `.eml`, (c) que las fichas que ya existían son
byte-idénticas. **No** se ejecuta sobre `G:` sin autorización expresa.
