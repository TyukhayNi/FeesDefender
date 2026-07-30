# Diseño — El historial citado no atribuible, localizable sin tocar la Capa A

> **Estado:** rev. 1 (2026-07-30). Aprobado por Nikolai en brainstorming.
> **Origen:** `MEJORAS #105`, que ya traía la decisión de arquitectura (opción B de tres). Esta spec
> la concreta, la corrige donde la medición del 2026-07-29 la contradijo, y arregla un choque con la
> idempotencia del motor que `#105` no vio.
> **Disparador:** decisión de Nikolai el 2026-07-30, tras medir el hilo de `MEJORAS #109` — que es
> la pieza que dejó esta como «lo que de verdad responde al requisito `#108`».
> **Alcance:** un artefacto nuevo por portador y su cableado. No toca el recorte del cuerpo, ni la
> atribución, ni la Capa A.

## 1. El defecto

Dos decisiones defendibles por separado que juntas pierden contenido:

- `bodies.extraer_cuerpo` **recorta la cita** para que cada ficha sea un mensaje y no historial
  repetido veinte veces (`cuerpo_recortado_cita: true` lo declara);
- la Capa B solo promueve una cita a ficha propia si puede **atribuir el remitente** desde una
  cabecera parseable, y no inventa remitentes.

Cuando ninguna de las dos ocurre, ese texto no está **ni** como ficha **ni** dentro del cuerpo del
portador: solo en el `.eml` crudo, que es justamente lo que el árbol de MD existe para no leer.

**Los números, medidos el 2026-07-29** sobre una etiqueta real (29 `.eml` en un scratch): de 28 atoms
de Capa A, 9 con el cuerpo recortado; **51.721 caracteres de texto plano, 10.728 llegan al `.md`,
40.993 fuera (79 %)**. Pero por **frase sustancial** (≥8 palabras), de 365 frases cortadas **332
(90 %) ya existen en otra ficha** —el mismo historial citado por varios portadores— y solo **33 (9 %)
no existen en ningún sitio**, 31 de ellas de un solo hilo.

**El caso que lo promovió**, medido al cerrar `MEJORAS #109`: un hilo de 5 mensajes del que **solo 1
llegó como `.eml`**. Los otros 4 vivían como 278 líneas citadas sin ninguna cabecera; `cortar_autor`
retiró **1493 de 1748 palabras** del cuerpo de la ficha; y la Capa B no corrió porque `_sandwich`
vetaba el portador — **con razón**. Resultado: 1493 palabras en ningún artefacto.

## 2. Objetivos y no-objetivos

**Objetivo:** que ese texto sea **localizable** desde el árbol de MD, sin atribuirlo a nadie.

**No-objetivos, y no son matices:**

- **No atribuir.** Ahí vive la misatribución, que en un corpus probatorio es peor que perder texto:
  un hueco se ve, una atribución falsa no. Nada de este artefacto afirma quién escribió qué.
- **No reconstruir el hilo.** Tener el texto no da la conversación; eso es `MEJORAS #106`.
- **No tocar la Capa A.** Ninguna ficha existente se reescribe.

## 3. Decisiones

Las cuatro se cerraron en el brainstorming del 2026-07-30.

| # | Decisión | Por qué |
|---|---|---|
| 1 | **Fichero hermano** `mensajes/<atom>.historial.md` | Ya elegida en `#105` (su opción B). Deja el historial al lado de su ficha y no reescribe ningún `.md` |
| 2 | **Verbatim, marcando los duplicados** (no filtrarlos) | Un filtro que se equivoque **oculta prueba sin que nadie lo note**; la redundancia solo cuesta ruido. Y marcar da el beneficio del filtro sin su riesgo |
| 3 | **La fuente es lo que `cortar_autor` recortó** (`Cuerpo.resto_citado`), no los bloques del segmentador | Medido: en el portador del hilo el historial vivía en el **texto plano**, mientras los `blockquote` HTML de otros tres portadores del mismo corpus estaban **vacíos**. La fuente estructurada se queda a cero justo donde hace falta |
| 4 | **Se escribe siempre que haya texto recortado**, incluso si no aporta ni una frase exclusiva | «0 exclusivas» es una afirmación **falsable** y auditable, y es exactamente la respuesta a «¿me estoy perdiendo algo en este portador?». Con el fichero ausente, esa respuesta no existe en ningún sitio |

**Decisión de formato, mía y señalada como tal para que se pueda revocar:** el texto va **verbatim de
verdad**, en un bloque intacto, y las anotaciones van **al lado** en un índice — no intercaladas como
prefijos por línea. Un bloque verbatim se audita carácter a carácter contra el `.eml`; uno con
prefijos inyectados, ya no. El índice **repite la frase** (columna `frase`): sin ella, una tabla de
números y estados no dice nada sin cotejarla a mano con el bloque, y el caso de uso principal —«¿qué
hay aquí que no esté en ninguna otra ficha?»— se responde leyendo solo esa columna.

**Detalle que decide si esto funciona, y es fácil de perder:** las frases del historial vienen
**marcadas con `>`**, y las de las fichas no. La normalización de comparación (`normaliza_cuerpo`)
quita las marcas de cita solo **al principio de línea**; si las frases se aplanan a una sola línea
*antes* de quitarlas, los `>` quedan a mitad de cadena, no se limpian, y **ninguna frase casa nunca**
— el fichero saldría con «100 % exclusivas» siempre. El orden correcto es: quitar marcas de cita →
aplanar → normalizar.

## 4. Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| **Una sección dentro del atom** (opción A de `#105`) | Reescribe **todos** los `.md` existentes: rompe la byte-identidad de Capa A y la comparación con los `_entregas/` ya sellados |
| **Escribir solo las frases que no existen en otra ficha** | Es un filtro, y un filtro que falla oculta prueba en silencio. Medido: dejaría 33 frases de 365 — atractivo, y por eso peligroso |
| **Anotar los duplicados intercalados en el texto** | El texto deja de ser verbatim y no se puede auditar contra el crudo |
| **Tomar el historial de los bloques del segmentador** (`ancestros` + `citas_vetadas`) | Depende de que el cliente meta la cita en un contenedor. Medido: tres portadores con `blockquote` **genuinamente vacíos**, con el historial en la parte de texto plano |
| **No hacer nada y confiar en los punteros de `#109`** | Los punteros llevan **200 caracteres** de extracto y solo existen para portadores **vetados**. Aquí el alcance es todo portador con cuerpo recortado, y el texto va entero |

## 5. Arquitectura

### 5.1. Módulo nuevo `core/email_atomize/historial.py` (puro, sin I/O)

- `frases_sustanciales(texto: str) -> list[str]` — parte en frases y conserva las de **≥8 palabras**,
  que es la unidad sobre la que `#105` midió el 90 %. **No existe partidor de frases en el repo**: se
  escribe aquí, y es el único sitio que decide qué es una frase.
- `indice_frases(mensajes: list) -> dict[str, list[str]]` — de frase **normalizada**
  (`normaliza_cuerpo`, el normalizador único que ya usan los fingerprints) al `MSG-id` de las fichas
  que la contienen. Se construye desde los cuerpos de **todas** las fichas publicadas, A y B.
- `render_historial(portador_msg_id, nombre_ficha, resto_citado, indice) -> str` — el contenido del
  `.md`. Excluye del índice al **propio portador**: una frase no cuenta como «ya presente en otra
  ficha» por estar en la suya.

### 5.2. Cableado en `pipeline.py`, tres puntos

1. `_construir_mensaje` llama a `B.extraer_cuerpo(col.raw, conservar_resto=True)`.
   **Verificado que es seguro:** `conservar_resto` es **puramente aditivo** — `texto=autor` se calcula
   igual con el flag o sin él (`bodies.py:60-85`), así que ninguna ficha se mueve.
2. El pipeline guarda `{msg_id: resto_citado}` en un **dict local**, no en `RegistroMensaje`. Un campo
   nuevo en el modelo tienta a emitirlo en el frontmatter, y eso reescribiría la Capa A.
3. Tras conocer las fichas A **y** B se construye el índice y se escribe un fichero por portador con
   `resto_citado` no vacío.

### 5.3. El choque con la idempotencia, que `#105` no vio

`pipeline.py:175-177` poda el árbol así:

```python
esperados = {R.nombre_md(m) for m in mensajes}
for p in (out / "mensajes").glob("*.md"):
    if p.name not in esperados:
        p.unlink()
```

Un `<atom>.historial.md` en `mensajes/` **se autodestruye en la corrida siguiente**: el glob lo coge y
su nombre no está en `esperados`. La propuesta de `#105` tal cual no sobrevive a su propia
idempotencia.

**Arreglo:** `esperados` pasa a ser *nombres de ficha* ∪ *nombres de historial escritos en esta
corrida*. Con eso el historial persiste, pero uno **huérfano** —portador desaparecido, o portador que
ya no tiene texto recortado— **sigue podándose**. La convergencia que esa poda protege no se debilita:
se extiende al artefacto nuevo.

### 5.4. Entregas selladas

**No hay que hacer nada:** `SET_ENTREGABLE` incluye `"mensajes"` como **directorio** y `sellar` hace
`copytree` (`entregas.py:15,47-54`), así que los historiales entran en la entrega y en su lista de
sha256 automáticamente.

## 6. Formato del fichero

`mensajes/<nombre del atom sin .md>.historial.md`. **Sin frontmatter YAML con `capa:`** — así ningún
consumidor que filtre fichas por `capa` lo confunda con un atom.

````markdown
<!-- GENERADO por core.email_atomize — NO editar a mano. -->
# Historial citado de MSG-00002 — SIN ATRIBUIR

Historial que `cortar_autor` retiró del cuerpo de `2026-07-28_1000_asunto_MSG-00002.md`, VERBATIM.
**Nada de lo que hay aquí está atribuido a un remitente:** no se pudo leer una cabecera de cita
fiable, y el motor no inventa remitentes.

- frases sustanciales (≥8 palabras): 41
- ya presentes en otra ficha: 38
- **exclusivas de este fichero: 3**

## Índice de frases

| # | estado | dónde vive | frase |
|---|---|---|---|
| 1 | duplicada | MSG-00007 | Buenos días, adjunto la propuesta revisada… |
| 2 | duplicada | MSG-00007, MSG-00011 | Quedo a la espera de su confirmación para… |
| 3 | **EXCLUSIVA** | — | En cuanto a la cláusula tercera, el plazo… |

## Texto retirado (verbatim)

```text
…el resto_citado, íntegro y sin tocar…
```
````

**Matiz que el propio fichero tiene que declarar, medido al validar los fixtures del plan:** el
`resto_citado` incluye los bloques `De:`/`Enviado:`/`Para:`/`Asunto:` de la cita —van dentro de lo que
`cortar_autor` recorta—, así que el `.historial.md` **contiene texto que parece una atribución sin
serlo**. Alguien podría leer `De: Otro <…>` y creer que el motor atribuyó ese mensaje. La cabecera del
fichero lo dice explícitamente: esos bloques se reproducen **tal cual porque son parte del texto
citado**, y si ese mensaje tuviera cabecera atribuible ya tendría su propia ficha.

## 7. Errores

Un fallo al renderizar el historial de un portador **no** entra en `report.errores`: eso apagaría la
poda del árbol entero (`report.errores` gobierna `poda_omitida`) por una vista derivada. Va a
`report.notas` **nombrando al portador**, de modo que la ausencia queda declarada y no silenciosa.

## 8. Contrato de tests

1. Un portador con texto recortado obtiene su `.historial.md`, y el bloque de texto es **verbatim**
   —comparación byte a byte contra `resto_citado`—.
2. Las frases duplicadas se anotan con el `MSG-id` que las contiene; las exclusivas, como exclusivas;
   **los tres recuentos de la cabecera cuadran con el índice**.
3. Un portador cuyo historial está **100 % duplicado** obtiene igualmente el fichero, con «0
   exclusivas». Es la decisión 4, y su valor es ser falsable.
4. **La poda no se lleva los historiales** —dos corridas seguidas y siguen ahí— **pero sí se lleva un
   historial huérfano** cuyo portador ya no existe. Mata el defecto del §5.3, que es el único que
   rompería la función entera en silencio.
5. Un portador **sin** texto recortado no genera fichero.
6. **La Capa A sigue byte-idéntica** con `conservar_resto=True`. Ya lo cubre
   `test_capa_a_byte_identica_contra_golden`: basta comprobar que sigue verde, y si se pone rojo el
   cambio es inaceptable, no el golden.
7. Una frase que solo existe en la **propia** ficha del portador **no** cuenta como duplicada (el
   índice se excluye a sí mismo).

**Disciplina de esta rama, por el historial del motor:** cada test se somete a *mutation testing* —
qué defecto concreto muere con él. Este motor lleva **cinco tests vacuos** encontrados, uno de ellos
descubierto justamente porque al mutar el código no moría ninguno.

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| El partidor de frases parte mal y el índice queda inútil | El **texto va verbatim aparte**: un índice malo degrada la ayuda, nunca el contenido. Y es la unidad sobre la que ya se midió el 90 % |
| Re-atomizar un caso existente añade hasta 9 ficheros de golpe | Aceptado y declarado (decisión de Nikolai). No reescribe ninguna ficha; contarlo antes de correr sobre un caso con entrega sellada |
| El fichero crece mucho en portadores con historial largo | Es el precio de verbatim. Los recuentos de la cabecera dicen de un vistazo si vale la pena leerlo |
| `normaliza_cuerpo` colapsa dos frases distintas y una se marca como duplicada sin serlo | Solo afecta a la **anotación**, no al texto. Y es el mismo normalizador que gobierna los fingerprints: si colapsara de más, ya habría un problema mayor en el motor |

## 10. Lo que queda fuera, con dueño

- **El hilo** — tener el texto no da la conversación: `MEJORAS #106`.
- **El consumo por la sala de lectura** — `MEJORAS #86`.
- **El camino de texto plano de `citas_vetadas`** y la rama `conservacion_tokens`, límites ya
  declarados de la pieza pequeña de `#109`.
- **Verificación en vivo:** el corpus de prueba se borró con autorización tras medir el hilo, así que
  esta spec **no tiene banco de pruebas real**. Se cierra re-exportando una etiqueta pequeña a un
  scratch fuera de todo expediente — el mismo procedimiento con el que se creó aquel corpus — y
  mirando los `.historial.md` que salgan. Hasta entonces, los números del §1 son de la medición
  anterior y la construcción se valida solo con tests.

## 11. Errata que esta spec corrige de paso

`MEJORAS #109` (tres veces) y la tabla de `MEJORAS #108` apuntan a **`#107`** cuando la pieza grande
es **`#105`**: `#107` es el test vacuo de la conservación de tokens. El error viene del bloque del 46º
cierre, que usó `#107` para tres cosas distintas, y se propagó al escribir `#109`. Se corrige en las
dos entradas.
