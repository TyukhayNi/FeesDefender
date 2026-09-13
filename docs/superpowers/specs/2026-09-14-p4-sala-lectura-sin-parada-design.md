---
tipo: spec
estado: vigente
creado: 2026-09-14
objeto: core/sala_lectura.py
rev: "1"
---

# P4 — La sala de lectura se monta con lo que no sabe clasificar

**Qué se construyó, qué se midió y por qué la propuesta literal de P4 **no** se hizo.**
Acta de la ronda adversarial: [`…-r1-adversarial-review.md`](2026-09-14-p4-sala-lectura-sin-parada-r1-adversarial-review.md).
Fila **#32** de `PLAN.md`. Origen: `handoff-2026-09-10-consulta-apertura-menos-decisiones.md` §P4.

## 1. La premisa de P4 no se sostiene, y eso se midió antes de construir

El handoff pedía: «unificar los dos [constructores] en la regla de la skill vacía el residuo
obligatorio». Medido sobre **1.352 documentos de los diez expedientes con catálogo**
(`indice_documental.yaml` del Drive, lectura pura):

| Escenario | Resultado |
|---|---|
| **A — el motor, antes** | 770 / 1.352 = **57,0 %** al residuo → parada |
| **B — la regla de la skill** (`preclasificar.clasificar_por_patron`) | **90,5 %** a `07. RECLAMACIONES`, y **0** de las 123 fotos en `00. FOTOS` |
| **C — unión de las dos reglas** | 54,4 % — rescata **34** documentos de 1.352 |

**B es peor que A, y la razón es estructural.** `clasificar_por_patron` detecta fotos solo por
`screenshot|captura`; el motor las detecta **por extensión** (`_es_imagen`). La skill puede
permitírselo porque tiene un LLM leyendo detrás y un gate de aprobación humana; el motor no
tiene ninguno de los dos. En W-048UOL son 18 `.jpeg` que pasarían de fotos a reclamaciones.

**Y C apenas mueve la aguja porque el residuo no lo causa la regla.** Los nombres del 55 %
restante no llevan la señal —`CaseDossierReport - …-V.pdf`, `DEVOLUCIO CLAUS.pdf`—: eso se
resuelve leyendo contenido, no con más patrones. Añadir patrones a una regla que mira nombres
no puede arreglar que el nombre no diga nada.

**Decisión de Nikolai (2026-09-14), tras ver estos números:** construir las dos piezas que sí
quedaban en pie, **dentro** de `core/sala_lectura.py` —alinear no es ampliar, y la medición
añade que las dos reglas *no deben* converger: un módulo compartido sería una abstracción
sobre una convergencia que no existe—.

## 2. Las dos piezas

### 2.1 `[APER-61]`: la identidad se enruta por PARTE

`_KEYWORDS` mandaba `dni`/`nie`/`pasaporte`/`nota simple`/`titularidad` a `06. PBC` y la
`hoja de visita` a `01. ACTIVACIÓN`. El runbook dice lo contrario, y esa tabla era la **causa
codificada** del síntoma que `[APER-61]` describe: «`03. OFERTAS` con 1 documento y `06. PBC`
con 28». Un test congelaba el error (`"Nota simple registral.pdf" → "06. PBC"`) y se corrigió
contra el runbook, que es la fuente.

**Medido con el código real de los dos lados: 87 documentos cambian de categoría** — 59 de
`06. PBC` a `01. ACTIVACIÓN`, 26 que salen del residuo (24 son Anexos 1 y 2 que la tabla
vieja no reconocía) y 2 que entran, los dos falsos positivos de substring que el límite de
palabra elimina.

**La frontera del token, con las dos mitades medidas.** El match era `substring in`, así que
un token casaba dentro de otra palabra (`Compa·nie·s` → PBC, `c·arras·co` → arras). Pero
exigir palabra entera rompía `oferta2.pdf`, `ofertas recibidas.pdf` y `PBC1 JOSEP GIRBAU.pdf`,
verdaderos positivos reales. La frontera es el **límite izquierdo y solo el izquierdo**: un
token identifica una palabra por su *inicio* y tolera plural, numeración y flexión.

### 2.2 La parada deja de ser una verja

`organizar` abortaba antes de `render_indices` y `poblar_sala_lectura` en cuanto quedara un
documento sin clasificar. Con residuo, **no se montaba ninguna sala**: en W-030TZY el letrado
tuvo que clasificar **80** documentos a mano y en W-02NHNC **21**, *antes de que existiera
nada que leer* (`RUNBOOK [APER-67]`). Ahora el residuo recibe `08. PENDIENTE DE CLASIFICAR`
—categoría de `TAXONOMIA_EV` desde siempre— con confianza `0.0`, y la sala se monta entera.

`detenido_por_residuo` **se retira** en vez de quedarse en `False`: dejarla diría «no me
detuve» ocultando que ya no puede detenerse. Un `KeyError` localiza al llamador.

### 2.3 Lo que esto NO es

**La clasificación no mejora.** El 55,2 % de los nombres sigue sin permitir afirmar una
categoría y acaba en `08` en vez de en una parada. La ganancia es que la sala pasa de **no
existir** a existir, con los 1.352 documentos nombrados y fechados, y el letrado corrige
leyendo — que es lo que el handoff pedía. Un `08` con el 55 % sería «un índice que calla» si
la alternativa fuese una sala clasificada; la alternativa real era **ninguna sala**.

## 3. La frontera que el diff destapó: qué cuenta como «decidido»

Cinco caminos preguntaban «¿esto ya está clasificado?» y cada uno lo decidía por su cuenta:
por confianza (`clasificar_caso`, `aplicar_clasificacion`), por `Tipo in TAXONOMIA_EV`
(`_hashes_residuo`), por `not tipo_documental` (el CLI y tres helpers de test). **Mientras el
residuo salía sin tipo, las cinco formas coincidían por accidente.** Con el residuo marcado
`08` dejan de coincidir, porque `08` **sí** está en la taxonomía.

La pregunta vive ahora en `sala_lectura.es_decision(tipo)`, un solo sitio.

## 4. Adjudicación de la revisión adversarial (Codex, 2026-09-14) — NO-SHIP, remediado

- **Objeto revisado:** el diff `c407fcb..2c9333f` (dos copias `git archive`, sin `.git`)
- **Ronda:** 1 de 1 — el radio de daño de la pieza es «todo lo demás», una ronda sobre el diff
- **Revisor:** Codex CLI `0.153.4`, `model_reasoning_effort=high`
- **Informe recibido:** `docs/superpowers/specs/2026-09-14-p4-sala-lectura-sin-parada-r1-adversarial-review.md` §1
- **Hallazgos:** 7 (2 `ALTO`, 4 `MEDIO`, 1 `BAJO`) — **7 confirmados, 0 refutados**
- **Remediado en:** `55d784d`

**Los dos ALTOS son regresiones de este mismo diff, y comparten frontera con los MEDIOS.**
Apliqué `es_decision` a lo que se **escribe** y no a lo que se **lee**:

| | Hallazgo | Adjudicación |
|---|---|---|
| **H-01** | `ALTO` — un `08` con confianza `1.0` (el estado que producía el código base) queda congelado: `clasificar_caso` lo salta, `solo_residuo` lo protege de su corrección, y al no estar en el residuo **desaparece de la worklist** | **CONFIRMADO.** Reproducido con test. Las dos guardas preguntan ahora `es_decision`: el estado heredado se normaliza solo, sin migración |
| **H-02** | `ALTO` — el reintento escribía `fecha_doc` incondicionalmente, así que `organizar` **pisaba la fecha del letrado** y materializaba la copia con otra | **CONFIRMADO, y es regresión mía**: la introduje al fechar el residuo para matar el mutante M10. Ahora solo se infiere si `fecha_fuente is None`, que distingue «nunca se calculó» de «hay una decisión» |
| **H-03** | `MEDIO` — `_hashes_residuo` ofrecía el documento y `rellenar_worklist` rechazaba la respuesta, tratando la celda `08` como intocable | **CONFIRMADO.** «Celda presente» dejó de ser «decisión tomada» para el selector y tenía que dejar de serlo para el escritor |
| **H-04** | `MEDIO` — `Anexo 2 compradores.pdf` → `06. PBC`, contra el ejemplo **literal** del runbook; `DNI comprador.pdf` → `01. ACTIVACIÓN` en vez de `03. OFERTAS` | **CONFIRMADO, y es un falso positivo NUEVO que introduje.** Un defecto para una parte *desconocida* no puede prevalecer sobre una parte *conocida*. La regla de parte se limita a la familia de la identidad: `requerimiento al comprador` sigue siendo reclamación |
| **H-05** | `MEDIO` — `Anexo 10.pdf` casaba `anexo 1`; los Anexos 10-19 y 20-29 se volvían la excepción de PBC | **CONFIRMADO.** Sufijo léxico y continuación de un identificador numérico no son la misma cosa: un token que termina en dígito no tolera otro dígito. `oferta2` y `PBC1` se conservan |
| **H-06** | `MEDIO` — M03 y M04 eran mutaciones **compuestas**: retiraban dos tokens y morían por uno | **CONFIRMADO**, y lo midió con sus propios mutantes X1/X2. Separados en M03a/M03b/M04a/M04b. Y el ejemplo del Anexo 1 llevaba «PBC» dentro: el defecto estaba en la **entrada de prueba** |
| **H-07** | `BAJO` — 57 % y 55 % para la misma muestra sin decir que son antes y después | **CONFIRMADO.** Las dos son ciertas y estaban mal etiquetadas |

**Su crítica al superviviente declarado se acepta entera.** Yo lo justifiqué con «solo cambia
TEXTO, no una decisión», y él respondió que al retirar la parada **ese aviso es el único canal
por el que el letrado se entera de que queda trabajo** — antes se lo decía el propio bloqueo.
Tiene test (`test_el_cli_organizar_dice_cuantos_pendientes…`) y mutante (M31).

**Lo que NO acepté sin matizar:** su punto 3 dice que «los cero movimientos de una muestra no
acreditan inmovilidad universal». Tiene razón en la forma, y la afirmación se reescribió: lo
que sostiene la seguridad *por construcción* es que `poblar_sala_lectura` copia antes de
borrar y protege los destinos nuevos, no que mi muestra diera cero.

### 4.1 Dos defectos del propio arnés, encontrados al ampliarlo

1. **El `try` que restaura empezaba después de mutar.** Un `OSError` transitorio al escribir
   —un handle ajeno de Windows— abortaba el arnés **dejando el árbol mutado**. La restauración
   se arma ahora antes, con reintentos, y el fallo final grita que hay que comprobar el árbol.
2. **El arnés leía `rc=4` de pytest («test no encontrado») como «el test YA estaba rojo».**
   Eso mandó a investigar un defecto inexistente; la causa real era M04b apuntando al fichero
   equivocado. «No existe» y «está rojo» son dos defectos distintos, con remedios distintos, y
   ahora se dicen distinto. **Mi primer diagnóstico —un `.pyc` rancio— era incorrecto**, y el
   comentario que lo afirmaba se corrigió: una causa escrita en un comentario que nadie volvió
   a medir es exactamente lo que cierra una discusión en falso.

## 5. Lo que queda fuera, con nombre

- **El `08` del 55 % sigue necesitando lectura.** La vía es `preparar-residuo` +
  Claude-en-sesión, que ya existe. Lo que P4 no hace es automatizarla.
- **La parte de un nombre opaco no se infiere.** `DNI Mercedes Loyo.pdf` va al lado del
  vendedor porque es la mayoría, no porque se sepa. El aviso de `[APER-61]` sigue siendo la
  comprobación: si `03. OFERTAS` aparece casi vacío en un caso con oferta aceptada, la
  identidad del comprador está mal enrutada.
- **La re-importación de los `.skill` caducados** (fila #14 de `PLAN.md`) es acción manual de
  Nikolai y sigue pendiente. P4 tocaba el motor, no la skill.
