# Diseño — La identidad de un segmento de bundle: que el reproceso sustituya en vez de añadir

> **Estado:** **rev. 4** (2026-08-02), tras **tres** revisiones adversariales, las tres **NO SHIP**
> (rev. 1: 2 B0 + 5 A + 3 M · rev. 2: 4 B0 + 5 A + 2 M · rev. 3: 2 B0 + 13 A + 9 M). Las dos primeras
> las hizo Codex; la tercera, **un revisor sustituto** —sesión limpia de Claude Code, mismo modelo que
> el autor— porque Codex está sin cupo hasta el 2026-08-08: su independencia es **más débil** y el
> §14 lo declara. La rev. 2 cambió la decisión central —del ordinal `seg` a un `doc_id` persistente—,
> la rev. 3 **partió el trabajo en dos piezas**, y la **rev. 4** cierra el agujero que la pieza A
> tenía por la puerta del **passthrough** (§6 y §7) y acota tres promesas que no se cumplían.
> Adjudicación de las dos primeras pasadas en §13; de la tercera, en §14.
> **Disparador:** destapado al ejecutar D1 de `MEJORAS #90` (fila #1 de `PLAN.md`, punto (f)) y
> medido en los 5 casos con sala de máquina: el defecto **ya estaba vivo antes de D1**.
> **Fuera de alcance:** D1 (cerrada por falta de rendimiento el 2026-08-01) y el comportamiento del
> reproceso sobre el texto (`MEJORAS #111`, **cuya alarma original quedó REFUTADA al medirla** el
> 2026-08-02: el reproceso relee lo ilegible, no pierde prueba).
>
> ⚠️ **Corrección de estimación.** Esta pieza entró en la cola como esfuerzo **bajo** («retirar la
> fila huérfana o versionar»). No lo es. El contrato incluye identidad, ledger monotónico,
> reconciliación, preflight, archivado, guard bidireccional, journal, retrofit y exclusión. La cola
> de `PLAN.md` queda corregida.

## 0. Las dos piezas

| | **Pieza A — motor y esquema** | **Pieza B — retrofit y saneamiento** |
|---|---|---|
| Qué | `doc_id` con ledger, validación canónica, reconciliación, preflight, custodia y guard | Retrofit de los manifiestos existentes, saneamiento de los 5 grupos duplicados, journal |
| Toca datos reales | **No.** Solo código y tests | **Sí**: los 5 casos del Drive |
| Depende de | Nada externo | Helpers ya cerrados de A **y del lock de exclusión** (§9) |
| Estado | ✅ **CONSTRUIDA** (2026-08-02) | **BLOQUEADA** hasta la Fase 2 de la fila #3 |

El corte lo propuso la 2ª revisión (N-M-2) y lo decidió Nikolai: son dos superficies con modos de
fallo y despliegues distintos. Cambiar el motor es permanente y reversible por git; migrar datos
reales bajo protocolo de préstamo, no.

### 0.1 Relación con el motor documental (`MEJORAS #48`) — leer antes de construir F1

**Anotado 2026-08-02.** Este spec nace de `MEJORAS #90` (fila #1 de `PLAN.md`, punto (f)), no del
plan del motor documental. Pero **las dos colas están diseñando la identidad del documento a la vez
y hasta hoy no se citaban**, que es justo el tipo de deriva que gobierna
`docs/GOBERNANZA_FUENTES_VERDAD.md`.

Lo que hay que saber al cruzarlas:

| | este spec (pieza A, ✅ construida) | `PLAN_MOTOR_DOCUMENTAL.md` §G.3 (F1, sin empezar) |
|---|---|---|
| identificador | `doc_id` = `d` + ≥2 dígitos (`d01`, `d100`) | `doc-NNN` (asa legible) + `sha8` (interno) |
| ámbito | **bundle** — vive en el manifiesto del bundle | **caso** — vive en el registro único (§H) |
| quién lo acuña | `construir_manifiesto` / `siguiente_doc_id`, con `next_doc_id` high-water y `retirados` (tombstones) | el registro de caso |
| lo edita el letrado | **sí** — de ahí `validar_doc_id` antes de cualquier I/O | pendiente de decidir |

**El riesgo concreto:** `doc-NNN` y `dNN` se parecen y no son lo mismo. Quien construya F1 debe
decidir explícitamente si el `doc-NNN` de caso **envuelve** al `doc_id` de bundle (probable:
`doc-014` → bundle, y `d03` identifica el segmento dentro de él) o si lo sustituye — en cuyo caso
hay que migrar el ledger, los tombstones y los nombres de fichero ya acuñados, no reescribir el
esquema y ya. No duplicar un segundo espacio de nombres sin resolver esto.

## 1. El defecto

`_slug_seg` (`core/split_documental.py:280`) nombra el segmento con el sha del **PDF ya recortado**,
un artefacto **derivado**:

```python
return f"{parent_slug}__seg{seg:02d}_{_norm_tipo(tipo)}__{seg_sha256[:8]}"
```

Re-OCR-izar el bundle cambia esos bytes, y con ellos el nombre de todos los artefactos del segmento.
Los anteriores no se retiran: **nada poda**. `fusionar_cobertura` (`core/sala_maquina.py:344`) indexa
por `(rel_path, slug)`, así que la fila nueva se añade al lado de la vieja.

### 1.1 La asimetría

Un documento **suelto** se nombra con `output_slug(rel_path, sha)` sobre el sha del fichero de
`00_Input`, inmutable por invariante. Reprocesarlo **sobrescribe su MD en el sitio**. El segmento de
bundle es el único artefacto cuyo nombre depende de algo que el propio pipeline reescribe.

### 1.2 Los huérfanos no son inertes

| consumidor | qué hace | efecto |
|---|---|---|
| `preclasificar.py:209` | lee `03_MD/{fila.slug}.md` **guiado por la cobertura** | sirve la versión que cite el registro, aunque haya otra más nueva |
| `core/sala_maquina.py:220` | recorre `03_MD/*.md` sin `_cobertura.json` | **convierte cada huérfano en fila** |
| `scripts/detectar_ocr_ciego.py:80` | ídem, para el cribado | cuenta huérfanos como candidatos |

## 2. Lo medido (2026-08-01, censo read-only)

| caso | grupos | duplicados | versiones | PDF | MD | raw_text |
|---|---:|---:|---|---:|---:|---:|
| `W-02VND1` | 15 | **3** | 2, 2, 2 | 18 | 18 | 18 |
| `W-02VUDR` | 20 | **2** | 3, 3 | 24 | 24 | 24 |
| `W-02T3XO`, `W-02XOR7`, `W-02TH0W` | 0 | 0 | — | 0 | 0 | 0 |

**21 ficheros excedentes** (7 PDF + 7 MD + 7 `raw_text`) sobre 5 grupos lógicos. Todo `raw_text` es
`.txt`. El defecto es **anterior a D1**: los de `W-02VUDR` son del 2026-07-21.

`W-02VND1` quedó además **incoherente consigo mismo**: `_cobertura.json` cita los segmentos del
23/07 y el `indice.json` del bundle, regenerado el 30/07, cita los del 30/07.

---

# PIEZA A — Motor y esquema

## 3. Identidad: `doc_id` con formato cerrado y ledger monotónico

La identidad de un documento lógico es un `doc_id` que vive en el manifiesto. El slug:

```python
def _slug_seg(parent_slug: str, doc_id: str, tipo: str) -> str:
    return f"{parent_slug}__{doc_id}_{_norm_tipo(tipo)}"
```

### 3.1 Formato canónico, validado antes de tocar el disco

`doc_id` casa `^d\d{2,}$` y nada más. **Se valida antes de cualquier I/O.**

Esto no es celo: es una superficie que abre esta spec. Hoy el slug es seguro **por construcción** —
`_norm_tipo` colapsa todo lo que no sea `[A-Z0-9]` (`split_documental.py:277`) y `seg` pasa por
`f"{seg:02d}"`, que revienta con un `str`—. Al introducir un campo de manifiesto **editable por el
letrado** directamente en una ruta, aparece el traversal: `destino_seguro` protege `carpeta_bundle`
(`sala_maquina.py:582`) pero **no** el `destino_pdf` que arma `materializar` (`:312`), y la 2ª
revisión lo ejecutó: un `doc_id` con separadores escribió fuera del bundle.

Además del formato, **cada destino final se valida por contención contra `carpeta_bundle`**, porque
el coste es una línea y el fallo es escribir fuera del expediente.

> **Lo que esa segunda comprobación NO es** (corregido en la rev. 4, hallazgo H-08, medido): no es un
> cinturón equivalente al formato. El slug antepone `parent_slug__`, así que un `doc_id` como
> `..\..\fuera` produce `…/bundle/bundle-slug__..\..\fuera_X.pdf`, que **resuelve dentro** de la
> carpeta —el prefijo absorbe el primer `..`— y la contención no lo caza. Sí caza las formas que de
> verdad escapan (`d01/../../fuera` → `…/02_Documentos/fuera_X.pdf`). **El gate real es el formato
> canónico**; la contención cubre el resto del espacio, no la forma concreta que ejecutó la 2ª
> revisión. El test lo ejerce con `d01/../../fuera`, no con `..\..\fuera`, que pasaría por razones
> equivocadas.

### 3.2 Ledger monotónico: `next_doc_id` y tombstones

El manifiesto gana dos campos:

- `next_doc_id`: **high-water mark**, monotónico, nunca decrece. Acuñar = tomar este valor e
  incrementarlo.
- `retirados`: lista de `doc_id` dados de baja (tombstones).

La rev. 2 decía «correlativo al **máximo existente**, nunca reutiliza uno retirado». **Las dos frases
no podían ser verdad a la vez**: si se retira el máximo, el máximo baja y la siguiente acuñación lo
reutiliza — la 2ª revisión lo reprodujo (`retired ['d02']` → nuevo `doc_id='d02'`). Con
`next_doc_id` la contradicción desaparece.

### 3.3 La correspondencia establecida no se reasigna a mano

La unicidad de `doc_id` no basta: el letrado puede **intercambiar** `d01` y `d02` y ambos siguen
siendo únicos, con lo que las identidades semánticas se cruzan en el siguiente `apply`.

Regla, comparando el manifiesto editado contra el anterior:

- editar el `pp` de un `doc_id` a un rango **nuevo** → permitido (es una corrección del letrado, y el
  manifiesto es su gate);
- que el **conjunto** de `pp` no cambie pero sí la correspondencia `doc_id → pp` → es una
  **permutación**: **aborta**;
- `doc_id` repetido, con formato inválido, o presente en `retirados` → **aborta**.

## 4. Preflight: validar todo antes de escribir nada

`validar_manifiesto` valida hoy rangos y solapes, no unicidad. Y **no basta con lanzar una
excepción**: la validación vive dentro de `_split_o_md`, que se invoca documento a documento desde
`ejecutar` (`:684`), y `apply` solo persiste cobertura, estado y evento **después** de que `ejecutar`
retorne (`scripts/sala_maquina.py:299-327`). Si el manifiesto inválido es el segundo bundle, el
primero ya escribió y **sus filas se pierden**.

Por eso la rev. 3 **no** abre un agujero en el aislamiento de `ejecutar` (que era la vía de la
rev. 2): se hace **preflight de todos los manifiestos y reconciliaciones del plan antes de procesar
el primer documento**. `ManifestValidationError` con bundle y entrada culpables, salida distinta de
cero, y **cero artefactos de Sala de máquina escritos**. El aislamiento por documento de `ejecutar`
queda intacto.

> **La promesa, acotada a lo cierto** (rev. 4, hallazgo H-04). Decía «cero bytes escritos» y era
> falso: `apply` **atomiza el correo antes** (`scripts/sala_maquina.py:293`), lo que crea
> `01_Procesado/Emails/` y añade una línea a `00_Input/_intake_log.jsonl`. El preflight en sí no
> escribe nada —verificado—, pero la corrida ya escribió cuando él corre. Lo que se garantiza es lo
> de arriba: **ningún artefacto de Sala de máquina**, que es lo que el preflight existe para
> proteger. Mover el preflight delante de la atomización haría cierta la frase original y **no se
> hace**: es un reorden del CLI que no pertenece a esta pieza. Ningún test puede cazar esto, porque
> todos doblan la atomización a un no-op.

## 5. Reconciliación del manifiesto, con la promesa que de verdad se puede cumplir

`--force` deja de **sustituir** el manifiesto y pasa a **reconciliarlo**:

1. Segmento nuevo que casa con una entrada anterior por **igualdad exacta de `pp`** → hereda su
   `doc_id`.
2. Segmento nuevo sin coincidencia exacta y **sin solape** con ninguna entrada anterior → acuña
   `next_doc_id`.
3. Segmento nuevo sin coincidencia exacta **pero con solape** → **`--force` se detiene** y pide
   reconciliación humana. No hay emparejamiento difuso: el desempate por solape admite empates y
   haría la identidad dependiente de una heurística.
4. Entrada anterior sin coincidencia → su `doc_id` va a `retirados` y sus artefactos se archivan.

**La promesa, rebajada a lo cierto** (hallazgo N-A-3): un split o merge real de límites —`1-6` →
`1-3` + `4-6`— **no conserva ninguna identidad**, porque ningún rango nuevo iguala al viejo. Eso es
correcto: el documento lógico cambió. Lo que `doc_id` garantiza es que **reprocesar sin cambiar la
segmentación conserva la identidad**, que es el caso de uso real (re-OCR). No garantiza identidad a
través de re-segmentaciones, y la spec ya no lo insinúa.

Consecuencia declarada: los `doc_id` **dejan de ir en orden de página** al insertar un segmento. El
orden de lectura lo da `pp`, no el nombre.

**Dos precisiones de la rev. 4, las dos medidas sobre el código de la rev. 3:**

- **El emparejamiento es por RANGO, no por la cadena `pp`** (H-06). Indexar por la cadena hacía que un
  `01-03` escrito por el letrado —mismo rango que `1-3`— rompiera la herencia y, peor, abortara
  `--force` con un mensaje que decía «solapa» sobre un rango idéntico a sí mismo. El manifiesto es un
  fichero que una persona edita: `pp` se normaliza con `_pp_a_rango` antes de comparar.
- **El manifiesto MIXTO se declara, no se acuña en silencio** (H-07). Bajo `--force`, una entrada
  anterior sin `doc_id` no tiene identidad que heredar y su segmento acuña una nueva. Eso es
  correcto, pero **hacerlo callando contradice el fail-closed** que justifica abortar en la corrida
  normal: queda en la **nota de cobertura** de los segmentos afectados —que es la worklist que el
  letrado mira— y en el evento `split_documental` (`legacy_sin_identidad`). Cierra lo que §11 pedía
  «definido explícitamente». También el passthrough que retira un bundle deja su nota y su evento
  (§7.1); ninguna retirada de artefactos ocurre en silencio.

## 6. `doc_id` como campo estructurado, y la fusión por identidad

`DocLogico` y `DocCobertura` ganan `doc_id`. `fusionar_cobertura` indexa:

- fila con `doc_id` no vacío → clave `(rel_path, doc_id)`;
- fila sin `doc_id` (documento suelto) → clave `(rel_path, slug)`, como hoy.

Esto corrige una afirmación **falsa** de la rev. 2, que decía que cambiar `TIPO` pasaba a ser
«inocuo». No lo era: el destino nuevo no existe, así que la regla «si el destino existe, archivar» no
se dispara, y la fusión por slug conservaba **dos filas del mismo `doc_id`** (reproducido:
`['parent__d01_DOC_A', 'parent__d01_DOC_B']`). Con la fusión por `doc_id`, un cambio de tipo es una
fila con slug nuevo → renombrado detectable, y sus tres representaciones se archivan y reescriben
como grupo.

### 6.1 La corrida es AUTORITATIVA sobre los documentos que reprocesa (rev. 4)

Cambiar la clave no basta, y la rev. 3 se quedó ahí. **Una fusión que solo sabe añadir no puede
sustituir**, por muy buena que sea su clave: sobreviven las filas de cualquier generación anterior
cuya clave no coincida con ninguna nueva. Dos formas medidas de que eso ocurra:

- una fila **reconstruida del MD** (`doc_id=""`, porque el frontmatter no lo guarda) conviviendo con
  la fila fresca del mismo documento lógico: **dos filas con el mismo slug**, una de ellas con `sha`
  vacío (H-05);
- un bundle que en el reproceso **deja de serlo** y pasa a passthrough: sus N filas de segmento
  sobreviven junto a la fila nueva del documento suelto (H-01).

Regla, por tanto: **al fusionar, las filas previas de un `rel_path` que esta corrida ha reprocesado
se descartan**; se conservan íntegras las de los `rel_path` que no se tocaron. Es la traducción
exacta del objetivo de esta spec —«el reproceso sustituye»— al registro, y no al solo nombre del
fichero.

```python
fusionar_cobertura(previa, nueva, rel_paths_reprocesados)
```

El conjunto lo pone el llamador desde el **plan** (`{d.rel_path for d in p if not d.skip}`), la misma
fuente que el alcance del guard y por el mismo motivo: cuando un documento falla, sus filas no
existen, y derivar el conjunto de las filas dejaría fuera justo el caso que hay que cubrir.

**Lo que esta regla NO hace:** no toca las filas de documentos no reprocesados (una corrida acotada
sigue siendo acotada), y no poda ficheros — de eso se encarga §7.

## 7. Custodia: publicar por generación, y un guard que mire en los dos sentidos

Sacar el sha del nombre tiene un precio: `emitido.replace(destino_pdf)` sobrescribe, y la fila de
cobertura guarda el sha del **propio segmento** (`sala_maquina.py:600`), de modo que un fallo a
media generación deja la fila declarando un sha que ya no corresponde a esos bytes.

1. **Publicación por generación.** Las tres representaciones (PDF, MD, `raw_text`) se escriben a
   *staging* dentro de la carpeta del bundle y se publican por renames al final. La generación
   anterior se mueve a `99_Versiones anteriores/reproceso_<sello>/` **como conjunto**: si el
   archivado no puede completar las tres, no se publica ninguna.

   > **Acotación de la rev. 4** (H-09): «como conjunto» describe la **publicación**, que sí es
   > todo-o-nada, no el **archivado**, que es un bucle de renames y no es transaccional. Si falla al
   > mover el tercero de quince, catorce quedan movidos y **no se publica nada** —la propiedad que
   > importa se conserva—, pero la generación anterior queda **partida entre dos ubicaciones**. Se
   > declara en vez de prometer atomicidad que no hay; el remedio operativo es que ni una copia ni la
   > otra se pierden y el guard aborta.

   **Solo se publica lo que el manifiesto declara** (H-10). El bucle final vaciaba el *staging* sin
   filtrar, de modo que un residuo de una corrida abortada —que `shutil.rmtree(..., ignore_errors=True)`
   puede no haber podido borrar bajo un *sharing violation* de Windows— se publicaba como si fuera de
   esta generación. Y los `.md`/`.txt` rancios aterrizaban **en la carpeta del bundle**, donde ningún
   guard los miraba nunca. Ahora: del *staging* solo salen los slugs publicados y el índice del
   bundle; lo demás se archiva.
2. **El fallo del evento no descarta el trabajo.** `_split_o_md` devuelve sus filas aunque
   `append_event` (`:602`) falle. Hoy, una excepción ahí sube a `ejecutar:732` y **se pierden las
   filas de todos los segmentos** del bundle.
3. **Guard bidireccional, y aborta.** No basta con recorrer las filas: en el fallo real no hay filas
   de segmento —`ejecutar:732` emite **una** fila de error con el slug del documento **físico**—, y
   con `--force` además `previa=[]`. El guard de la rev. 2 estaba **ciego justo en el caso para el
   que se escribió**. Ahora:
   - fila → fichero: las **tres** representaciones existen y su sha casa con el declarado;
   - fichero → fila: todo `02_Documentos/<parent>/*.pdf` tiene fila, **y la carpeta no contiene
     `.md` ni `.txt`** (rev. 4, H-10: ahí no vive ninguna representación legítima, así que uno
     rancio solo puede venir de una publicación sucia, y nadie lo miraba);
   - discrepancia → **salida distinta de cero**, nombrando segmento y representación. No un aviso.

   **El guard DETECTA; no previene** (rev. 4, H-14). El párrafo que abre este §7 dice que un fallo a
   media generación deja la fila declarando un sha que ya no corresponde: la publicación por
   *staging* estrecha muchísimo esa ventana, pero **no hay rollback**, así que si se rompe entre el
   PDF y el MD el estado incoherente existe y lo que hace el guard es **cerrar la corrida en rojo con
   el segmento nombrado**. Prometer prevención sería falso.

### 7.1 El passthrough también publica (rev. 4, hallazgo H-01 — B0)

Toda la maquinaria de arriba vivía en la rama *split* de `_split_o_md`. La rama **passthrough** —la
que corre cuando `detectar` devuelve un solo segmento, o cuando lanza y el motor degrada a propósito
(`core/sala_maquina.py:559-579`)— escribía su MD suelto y no archivaba nada. Con eso, un bundle que
en un reproceso deja de detectarse como tal:

- con `--force` dejaba sus N PDF de segmento **huérfanos** → el guard aborta con salida 3, y volver a
  lanzar da lo mismo porque la detección sigue degradando: **caso real sin salida dentro de la
  herramienta**;
- sin `--force` conservaba las N filas viejas junto a la nueva: **el defecto que esta spec existe
  para eliminar, reintroducido en silencio y con el guard ciego**.

Y no es hipotético: el delimitador de segmento exige `len(txt.strip()) < 10`
(`core/split_documental.py:25,144-158`), así que **diez caracteres de ruido de OCR** en la hoja en
blanco colapsan N→1.

> **Cita reapuntada (2026-08-02, tras el PR #190).** La rev. 4 escribió aquí «que el reproceso cambia
> el texto de forma no aditiva está medido (`MEJORAS #111`)» cuando esa entrada aún sostenía que el
> reproceso **perdía** cifras y fechas. **Esa alarma quedó REFUTADA al medirla:** lo que hay son
> re-lecturas, no pérdidas — en seg03 el texto pasa de 5.414 a 5.453 tokens únicos, y lo que parecía
> perdido era un DNI que la versión vieja partía y la nueva trae entero. Lo que **sí** sigue medido, y
> es lo único que este párrafo necesita, es que **el texto cambia** entre generaciones (seg01 = 0,
> seg02 = 2, seg03 ≈ 66 tokens de diferencia): basta para que diez caracteres caigan sobre una hoja en
> blanco. Y el mecanismo que ejercita el test —que `detectar` reviente y el motor degrade a
> passthrough a propósito— **no depende de esto en absoluto**.

**Regla:** cuando un documento se resuelve como passthrough y existe carpeta de bundle previa para su
`parent_slug`, esa generación se **archiva entera** —PDF, MD, `raw_text`, `indice.json` y el
manifiesto— en `99_Versiones anteriores/reproceso_<sello>/`, y el `doc_id` de cada entrada retirada
va a `retirados`. Junto con §6.1 (la corrida es autoritativa sobre lo que reprocesa), eso deja el
registro y el disco coincidiendo en la única lectura correcta: **ese `rel_path` ya no tiene
segmentos**.

*(La frecuencia real de esta transición en el corpus no está medida: lo que está establecido es que
sus dos mecanismos existen en el código.)*

## 8. Contrato de tests — Pieza A

**El test que fija el arreglo falla hoy**: materializar dos veces el mismo bundle con bytes distintos
deja **una** representación de cada tipo por documento lógico y **N** filas, no 2N, con los tres
hashes coherentes entre sí y con la fila.

1. `_slug_seg` puro: mismo `(parent, doc_id, tipo)` → mismo slug, con contenido distinto.
2. Doble materialización → un artefacto por representación, hashes coherentes.
3. **Traversal**: `doc_id` con separadores, `..`, espacios o forma no canónica → rechazado **antes**
   de escribir; test real en Windows que comprueba que no aparece nada fuera de `carpeta_bundle`.
4. **Ledger**: retirar el `doc_id` máximo y acuñar después **no** lo reutiliza (`next_doc_id`);
   `retirados` acumula; un `doc_id` de `retirados` en el manifiesto aborta.
5. **Permutación**: intercambiar `d01`/`d02` conservando el conjunto de `pp` → aborta.
6. **Reconciliación**, con el mapa `pp → doc_id` exacto aserido en los cuatro casos de §5:
   idéntica (hereda), rango nuevo disjunto (acuña), solape sin igualdad (**se detiene**), entrada
   desaparecida (retira y archiva). Incluye `1-6 → 1-3 + 4-6`, que la rev. 2 no cubría.
   **Mutación obligatoria:** una implementación que «acuñe siempre» debe **matar** este test — evita
   el vacuo que señaló N-M-1.
7. **Preflight**: manifiesto inválido en el **segundo** bundle → exit ≠ 0 **desde la CLI**, y el
   primero **no ha escrito nada**.
8. **Custodia**: fallo inyectado (a) tras el PDF y antes del MD, (b) en `append_event`. En (a) la
   generación anterior está íntegra en `99_Versiones anteriores/` y el guard **aborta**; en (b) las
   filas del bundle **sobreviven**. Se asertan bytes de las tres representaciones y la cobertura
   antes y después, no solo la existencia de «algún fichero archivado y un aviso».
9. **Guard en los dos sentidos**: PDF de segmento sin fila → aborta; fila sin fichero → aborta;
   fila cuyo sha no casa → aborta.
10. **Fusión por `doc_id`**: cambiar `TIPO` deja **una** fila, no dos.

Los asertos sobre mensajes usan frases con espacios, nunca subcadenas que el nombre del test pueda
inyectar en la salida capturada.

> **Y hay que cumplirla, no solo escribirla** (rev. 4, H-12). El plan de la rev. 1 la incumplía: sus
> asertos `any("MD" in f)` y `any("raw_text" in f)` casaban con los **componentes de ruta** `03_MD` y
> `raw_text` que van dentro del propio mensaje, de modo que un mutante que etiquetara mal las tres
> representaciones sobrevivía. Y la inyección por nombre de test que la regla veta **ocurría
> literalmente**: el tmpdir de `test_guard_detecta_el_sha_que_no_casa` es
> `test_guard_detecta_el_sha_que_0`, que contiene `"sha"`.

### 8.1 Lo que la rev. 4 añade al contrato

Once tests más, cada uno con su mutante nombrado. Los cuatro primeros son los que cerraron un
mutante **vivo** o un `B0`:

| # | Propiedad | Mutante que debe morir |
|---|---|---|
| 11 | **N→1**: un bundle que pasa a passthrough archiva su generación anterior entera, deja la carpeta sin PDF de segmento y **una sola fila** para ese `rel_path` | la rama passthrough sin archivado (el estado de la rev. 3) |
| 12 | **`retirados` acumula**: previo con un tombstone **y** una retirada nueva → los dos en el ledger, y el retirado sigue sin poder reutilizarse | `retirados` que no concatena el previo (H-22: pasaba la suite entera) |
| 13 | **Custodia, las tres representaciones y la cobertura**: bytes de PDF, MD y `raw_text` antes y después, más las filas | `materializar` sin *staging* para el PDF, que destruye la generación anterior y hoy pasaría en verde (H-23) |
| 14 | **Fusión autoritativa**: fila reconstruida del MD + fila fresca del mismo segmento → **una** fila | la fusión que solo añade (H-05) |
| 15 | `pp` no canónico (`01-03`, `1 - 3`) hereda igual que `1-3` | indexar `por_pp` por la cadena |
| 16 | Manifiesto mixto bajo `--force`: acuña **y avisa** (stderr + evento) | acuñar en silencio |
| 17 | `segmentos: []` aborta | validación que acepta la lista vacía y vacía el bundle con exit 0 |
| 18 | `doc_id` con salto de línea o dígitos no ASCII: rechazado **antes** de tocar disco | `re.match` con `$` en vez de `re.fullmatch` ASCII |
| 19 | `_segmentacion.json` corrupto → salida 2, no traceback | `except` que solo captura `ManifestValidationError` |
| 20 | `reforzar` con manifiesto legacy: preflight, salida 2 **sin escribir** | preflight cableado solo en `apply` |
| 21 | *Staging* residual: no se publica lo que el manifiesto no declara | bucle final que vacía el *staging* sin filtrar |

## 9. Criterio de salida — Pieza A

- Los tests 2, 6, 7, 8 y **11-14** pasan y **mueren al retirarles su arreglo** (mutación verificada,
  incluida la de «acuñar siempre» y la de «no acumular tombstones»).
- Preflight: manifiesto inválido aborta desde la CLI con exit ≠ 0 y **cero artefactos de Sala de
  máquina** escritos (§4: la atomización de correo ya ha escrito antes, y eso está declarado).
- Suite verde contra la base **medida al empezar**, no contra una cifra escrita. Medición del
  2026-08-02 sobre el commit `a7f168c`: **2630 passed, 77 skipped, 7 xfailed** (2714 total, 0
  failures), con `--basetemp` corto — con ruta larga,
  `test_migrar_nombres_informe::test_resumen_cuenta_por_estado` falla por presupuesto de `MAX_PATH`
  y **no es un fallo real**. La cifra que esta línea declaraba antes (2612) estaba desfasada en 18
  (H-21).
- Los tests que ejercen el e2e del split se corren **con `--runslow`**: `test_split_sala_maquina_e2e.py`
  está marcado `slow` y `tests/conftest.py` lo salta por defecto, así que sin la bandera el verde es
  vacuo (H-18).
- Ningún caso real tocado — y eso incluye el evento del log: `core.sala_maquina` importa
  `append_event` por su cuenta, así que doblarlo solo en el CLI deja los tests escribiendo en el
  `CASOS_ROOT` real (H-17).

---

# PIEZA B — Retrofit y saneamiento  ⛔ BLOQUEADA

## 10. El bloqueo, y por qué no se resuelve aquí

La rev. 2 sostenía que correr «bajo el lock del protocolo» eliminaba toda copia divergente. **Es
falso, y lo demuestra el propio repo**: `ESTADO_REPO_PRESTADO` significa «hay copia de trabajo
local» (`config.py:357-359`), no es un mutex; `cmd_checkin` no verifica nonce al empezar; y la suite
lleva vivos como `xfail` los defectos `test_defecto_doble_titular` («el write-then-verify no impide
dos titulares») y el rollback que cancela el lock ajeno. Con una copia local stale, `plan_merge`
produce `PRESERVE_DRIVE` para el slug migrado y `COPY_LOCAL` para el viejo: **lo resucita**.

Esos defectos **no son de esta spec**: son los que la **fila #3 de `PLAN.md`** (arquitectura dual del
expediente activo) tiene reproducidos en `xfail` y arregla en su **Fase 2**. Decisión de Nikolai
(2026-08-01): **declarar la dependencia y bloquear solo la pieza B**, en vez de inventar aquí un
segundo mecanismo de exclusión — que es justo lo que la arquitectura dual quiere unificar.

**Gate de desbloqueo:** los defectos del lock cerrados en la Fase 2 de la fila #3 (los `xfail`
correspondientes pasando a verde). Anotado en las dos filas de `PLAN.md`.

## 11. Diseño de la pieza B (para cuando se desbloquee)

**Retrofit del manifiesto** (`doc_id`, `next_doc_id`, `retirados`), con las validaciones que la 2ª
revisión exigió: tipos, unicidad y orden de `seg` primero; **`cobertura.paginas == manifiesto.pp`
para el superviviente** —si un `--force` histórico renumeró, el `segNN` del artefacto puede no
representar el `pp` actual y se congelaría la identidad equivocada—; manifiesto **mixto** (unas
entradas con `doc_id` y otras sin él) definido explícitamente; grupo que no case, abortado.

**Saneamiento**, por grupo, con el contrato 0/1/N que la 1ª revisión pidió y que sobrevivió a la
segunda:

| coincidencias en `_cobertura.json` | acción |
|---|---|
| exactamente 1 | sobrevive esa; las demás a `99_Versiones anteriores/migracion_slugs_<fecha>/` con su nombre viejo; después se renombra la superviviente |
| 0 | no decidir: avisar, intacto |
| N > 1 | abortar el grupo: el registro reclama dos versiones del mismo documento lógico |

Manda el registro, no la fecha (decisión de Nikolai). Casos legacy sin `_cobertura.json`: **no
migrables automáticamente** — hoy cuesta cero, `W-02XOR7` es el único y no tiene segmentos.

> ⚠️ **La justificación de esta regla se cayó, y la regla se queda** (2026-08-02, tras el PR #190).
> La rev. 4 la razonaba así: «en `W-02VND1` eso conserva la del 23/07, anterior a D1, lo que evita
> importar la pérdida de texto de `MEJORAS #111`». **No hay pérdida que evitar** —esa alarma quedó
> refutada al medirla— y, peor para el argumento, la medición dice que en seg03 la del 23/07 es **la
> peor de las dos**: un DNI partido frente al mismo DNI entero, y nombres propios sin acentuar. La
> regla sobrevive porque es una **decisión de Nikolai** sobre quién manda —el registro, no la
> fecha—, no porque la versión que manda sea la mejor.
>
> **Queda abierto, y es de Nikolai, no del motor:** qué hace el saneamiento cuando la versión que el
> registro reclama es la de peor calidad. El archivado de la generación retirada garantiza que la
> otra **no se pierde** (§7.1), solo que no es la operativa. Decisión pendiente, y la pieza B sigue
> bloqueada de todos modos.

**Journal**, con lo que faltaba: ruta determinista y durable (no «junto al informe»), escritura
atómica, `case_id` + `run_id`, versión de esquema, y comandos explícitos de `resume` / `rollback` /
`adopt`. Si falta el journal pero hay marcas de migración parcial, **no se empieza una corrida
nueva**.

## 12. Radio de la migración (medido)

| artefacto | acción |
|---|---|
| `02_Documentos/<parent>/{slug}.pdf`, `03_MD/{slug}.md`, `raw_text/{slug}.txt` | renombrar |
| `02_Documentos/<parent>/indice.json` (campo `archivo`), `_cobertura.json` (campo `slug`) | reescribir |
| `_revisar/_cobertura.md` | regenerar desde el JSON |
| `_segmentacion.json` | gana `doc_id`, `next_doc_id`, `retirados` |
| `_sala_maquina_state.json`, `01_OCR/`, `00_Input/`, `01_Procesado/Sala lectura/` | no se tocan |
| **`_intake_log.jsonl`** | **NUNCA se reescribe** |

La última fila es doctrina: el log es forense y append-only. **Seguirá citando los slugs viejos para
siempre, y eso es correcto** — describe lo que pasó cuando pasó. La 2ª revisión buscó un consumidor
productivo que cruzase esos slugs históricos con la cobertura vigente y **no encontró ninguno**.

## 13. Las dos revisiones adversariales de Codex

Handoffs: `docs/superpowers/handoffs/handoff-2026-08-01-identidad-segmento-codex-review.md` (1ª) y
`…-review-2.md` (2ª). Los dos informes viven entre los handoffs, no como acta, por la decisión de
Nikolai del 2026-07-30 (`docs/GOBERNANZA_FUENTES_VERDAD.md` §5): **no llevan digest** y su
integridad no es comprobable, solo la sostiene el historial de git.

### 13.1. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md` rev. 1, commit `f965716`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `docs/superpowers/handoffs/handoff-2026-08-01-identidad-segmento-codex-review.md` — handoff, **sin digest**
- **Hallazgos:** 10 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento y, lo que quedó a medias, rev. 3

Los 10 son 2 B0 + 5 A + 3 M. B0-2 fue dirimente: cambió la decisión central. Cerrados en la
rev. 2 y confirmados por la 2ª pasada: B0-2, A-2, A-3, M-1, M-3. Quedaron **a medias** —y la 2ª
pasada tuvo razón en decirlo— B0-1, A-1, A-4, A-5 y M-2.

### 13.2. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md` rev. 2, commit `05d985f`
- **Ronda:** 2
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `docs/superpowers/handoffs/handoff-2026-08-01-identidad-segmento-codex-review-2.md` — handoff, **sin digest**
- **Hallazgos:** 11 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 3 de este documento; N-B0-4 deja la **pieza B bloqueada** (§10)

Los 11 son los de la tabla, y los once se sostienen contra la fuente:

| ID | Adjudicación | Dónde se resuelve |
|---|---|---|
| N-B0-1 | **Confirmado**: superficie que abría esta spec; hoy el slug es seguro por construcción | §3.1 |
| N-B0-2 | **Confirmado**: contradicción interna de la rev. 2 («máximo existente» vs. «nunca reutiliza») | §3.2, §3.3 |
| N-B0-3 | **Confirmado, el peor**: el guard estaba ciego en el caso para el que se escribió | §7 |
| N-B0-4 | **Confirmado** con los `xfail` del propio repo | §10 — **bloquea la pieza B** |
| N-A-1 | Aceptado; se resuelve con **preflight**, más limpio que perforar el aislamiento | §4 |
| N-A-2 | Aceptado: la rev. 2 afirmaba en falso que el cambio de `TIPO` era inocuo | §6 |
| N-A-3 | Aceptado: la promesa de persistencia se rebaja a lo que se puede cumplir | §5 |
| N-A-4 | Aceptado | §11 |
| N-A-5 | Aceptado | §11 |
| N-M-1 | Aceptado: los tests 4, 5 y 7 de la rev. 2 admitían implementaciones vacuas | §8.6, §8.8 |
| N-M-2 | **Aceptado y aplicado**: el corte en dos piezas | §0 |

**Y su crítica a mi adjudicación era correcta:** cerré B0-1 con una solución barata que no cubría el
caso de fallo real, y di A-5 por resuelto apoyándome en un mecanismo que no excluye. Las dos estaban
adjudicadas con optimismo.

## 14. Adjudicación de la revisión adversarial (Claude Code [sesión independiente], 2026-08-02) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/plans/2026-08-02-identidad-segmento-bundle-pieza-a.md` (rev. 1) + este spec rev. 3 (§0 y §3-§9), commit `a7f168c`
- **Ronda:** 1
- **Revisor:** Claude Code (sesión independiente) — revisor sustituto, solo lectura
- **Informe recibido:** `2026-08-02-identidad-segmento-bundle-pieza-a-r1-claude-adversarial-review.md`
- **Hallazgos:** 23 confirmados · 1 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 4 de este spec (§3.1, §4, §5, §6.1, §7, §7.1, §8.1, §9) + rev. 2 del plan

### 14.1 La independencia de esta ronda es más débil, y el resultado lo enseña

El revisor **no fue Codex** —sin cupo hasta el 2026-08-08— sino una **sesión limpia de Claude Code**:
el mismo modelo que escribió el objeto. Comparte por tanto sus puntos ciegos y no tiene la tensión de
interés de un revisor externo. Se compensó como manda `AGENTS.md` §«Revisor sustituto», y aun así
**esta ronda no sustituye a una de Codex**.

El dato que lo muestra sin discusión: **de 24 hallazgos no refuté ninguno**. Rebajé uno. Cuando autor
y revisor comparten priors, la coincidencia no es evidencia de acierto — es lo esperable. Por eso el
cambio de diseño que sale de aquí (§14.4, H-01) **debería pasar por Codex** antes de construirse,
aunque el resto se remedie ya.

### 14.2 Adjudicación hallazgo a hallazgo

Cada uno contra la fuente, abriendo el fichero o ejecutando; la evidencia con ruta y línea está en el
§2 del acta.

| ID | Sev. | Adjudicación | Dónde se remedia |
|---|---|---|---|
| H-01 | **B0** | **CONFIRMADO.** Verificado en `core/sala_maquina.py:559-579`: la rama passthrough degrada a propósito, escribe un MD suelto y no llama a nada de la maquinaria nueva, que vive entera en la rama split. Las dos mitades se sostienen: con `--force` los N PDF viejos quedan huérfanos → salida 3 sin salida; sin `--force` la fusión conserva las filas viejas (clave `(rel_path, doc_id)`) junto a la nueva (`(rel_path, slug)`) y **reintroduce el defecto que esta spec existe para eliminar**, con el guard ciego. El disparador es plausible y está en código (`split_documental.py:25,144-158`: diez chars de ruido matan el separador), pero **su frecuencia real no se midió** | **Cambio de diseño** — §6 y §7 de este spec (rev. 4) + plan Tareas 3, 5 y 7 |
| H-15 | **B0** | **CONFIRMADO, mecánico.** Ejecutado: `from core.config import CASOS_ROOT` → `ImportError`; el nombre es `settings.casos_root` | plan Tarea 8, Step 3 |
| H-17 | A | **CONFIRMADO.** `core/sala_maquina.py:26` importa `append_event` por su cuenta y `:602` lo llama; el helper `_caso` solo parchea `cli.append_event`. Los dos tests que corren `cli.apply` de punta a punta escribirían en el `CASOS_ROOT` real, contra la restricción global nº 1 del propio plan | plan Tarea 4 (`_caso`) |
| H-02 | A | **CONFIRMADO.** `reforzar` llama a `ejecutar` sin `force` (`scripts/sala_maquina.py:338-387`) y el plan solo cablea el preflight en `apply`: un manifiesto legacy lo lleva a salida 3 **después** de escribir | plan Tarea 7 |
| H-03 | A | **REBAJADO.** El hecho es cierto y lo verifiqué (`acotar_plan` fuerza `skip=False` → preflight con `force=False` → aborta; y `--solo`+`--force` se rechazan en `scripts/sala_maquina.py:283-289`). Pero su consecuencia —«el único remedio es `--force` de todo el caso»— **es falsa**: borrar el `_segmentacion.json` de ESE bundle deja a `--solo` reconciliar contra `previo=None` y acuñar identidades nuevas, con el barrido de la decisión 10 archivando lo viejo. La vía acotada existe; lo que falta es declararla | `MEJORAS #113` punto 3 |
| H-04 | A | **CONFIRMADO.** `_atomizar_correo` (`scripts/sala_maquina.py:293`) escribe antes del preflight, y `_registrar_atomizado` añade una línea a `00_Input/_intake_log.jsonl`. El preflight en sí no escribe: lo falso es la promesa sobre **la corrida**. **Remedio acotado a redacción** (decisión de Nikolai): mover el preflight delante de la atomización la haría cierta y **no se hace en esta ronda** | §4 y §9 de este spec + docstring de la Tarea 4 |
| H-05 | A | **CONFIRMADO, con el alcance más estrecho de lo que sugiere.** La fila reconstruida sale con `doc_id=""` y la fresca con `doc_id`, así que dejan de colapsar. Matiz que el informe no separa: solo muerde cuando el MD **ya se escribió con el nombre nuevo** y falta `_cobertura.json`; con MD de nombre viejo son dos filas también hoy. **Qué casos reales carecen de `_cobertura.json` sigue sin verificar** | cubierto por el remedio de H-01(b); si no se adopta, plan Tarea 3 |
| H-06 | A | **CONFIRMADO.** `por_pp` se indexa por la cadena `pp`: `01-03` vs `1-3` rompe la herencia y el mensaje dice «solapa» sobre el mismo rango | plan Tarea 2 |
| H-07 | A | **CONFIRMADO.** Bajo `--force`, las entradas sin `doc_id` quedan fuera de `por_pp` y se les acuña identidad sin aviso — justo lo que la decisión 4 dice no hacer | plan Tarea 2 |
| H-08 | A | **CONFIRMADO, ejecutado.** `..\..\fuera` resuelve **dentro** de la carpeta (el prefijo `parent_slug__` absorbe el primer `..`), así que `_destino_en_bundle` no caza la forma que ejecutó la 2ª revisión; `d01/../../fuera` sí. **Remedio: redacción** de §3.1 (el «cinturón y tirantes» no es lo que dice ser) + que el test ejerza una forma que de verdad escape | §3.1 + plan Tarea 1 (solo el test) |
| H-09 | A | **CONFIRMADO.** El bucle de archivado no es transaccional: «la generación anterior queda íntegra» es falso si falla a medias. **Remedio: redacción** — lo que sí se cumple es «no se publica ninguna» | §8.8(a) + plan Tarea 5 |
| H-14 | A | **CONFIRMADO.** El guard **detecta** la fila con sha que no casa; §7 promete **prevenir**. **Remedio: redacción** | §7 |
| H-18 | A | **CONFIRMADO.** `tests/conftest.py:35-41` salta los `slow` salvo `--runslow`, que el plan nunca pasa: todo «Expected: PASS» que incluya el e2e es vacuo y la corrección de manifiesto de la Tarea 2 no se ejecutaría nunca | plan Tareas 2, 5 y 8 |
| H-22 | A | **CONFIRMADO.** Ninguno de los dos tests que tocan `retirados` asserta la acumulación con un tombstone previo: el mutante «no acumula» pasa la suite y reabre N-B0-2 | plan Tarea 2 |
| H-23 | A | **CONFIRMADO como hueco de cobertura**, que es lo que §8.8 exige por escrito («los bytes de las tres representaciones **y** la cobertura»): el test asserta solo los `.md`. El mutante concreto —materializar sin staging para el PDF— está **trazado contra el código, no ejecutado** de punta a punta | plan Tarea 7 |
| H-10 | M | **CONFIRMADO.** El bucle final publica todo lo que quede en staging sin filtrar por el manifiesto, y el guard solo audita `*.pdf`: un `.md` rancio en la carpeta del bundle no lo mira nadie nunca | plan Tareas 5 y 7 |
| H-24 | M | **CONFIRMADO, ejecutado.** `^d\d{2,}$` acepta `'d01\n'` y dígitos árabes (`int(…)==12`); `re.fullmatch(r"d[0-9]{2,}")` cierra los dos | plan Tarea 1 |
| H-11 | M | **CONFIRMADO.** Nada exige ≥1 segmento: con `segmentos: []` se archiva el bundle entero, no se publica nada y sale 0 | plan Tarea 2 |
| H-12 | M | **CONFIRMADO en sustancia:** `any("MD" in f)` y `any("raw_text" in f)` casan con componentes de ruta, no con la etiqueta. **El recuento «10 de 11 asertos» no lo he recontado** y queda sin verificar | plan Tarea 7 |
| H-13 | M | **CONFIRMADO, leído.** `organizar-sala-maquina/SKILL.md:78-81` y `2026-07-14-split-sala-maquina-design.md:113,241,286-287,344` documentan el contrato de nombres viejo y quedan falsos | plan Tarea 8 (lista de ficheros) |
| H-16 | M | **CONFIRMADO.** El paso de vacuidad esconde una refactorización de tres sitios y su predicción «6 PDFs y 6 filas» es falsa | plan Tarea 8, Step 2 |
| H-19 | M | **CONFIRMADO.** La Tarea 1 deja el árbol rojo hasta la 2, y por H-18 nadie lo vería | plan Tareas 1-2 |
| H-20 | M | **CONFIRMADO.** `leer_manifiesto` es un `json.loads` pelado: el JSON truncado —el fallo más probable en el fichero que edita el letrado— escapa como traceback | plan Tarea 4 |
| H-21 | M | **CONFIRMADO, medido por mí** en el commit anclado con `--basetemp` corto: la cifra de §9 (2612) está desfasada | §9 |

### 14.3 Dos defectos que salieron al adjudicar, y no son del revisor

- **El encabezado de adjudicación que el propio encargo proponía no pasa G7.** El grupo `revisor` del
  regex es `[^,)]+` y no admite paréntesis anidados, así que
  `(Claude Code (sesión independiente), 2026-08-02)` falla. Medido contra el regex real
  (`tests/test_docs_gobernanza.py:278-283`). Por eso este encabezado usa
  `Claude Code [sesión independiente]`, con la forma larga en el frontmatter del acta y en la ficha.
- **El guard G2 daba un falso positivo con la ruta del informe, y mi verde previo era falso.** El
  contrato de revisiones exige que el informe viva **fuera** del repo y que el encargo **fije** su
  ruta; G2 leía esa ruta absoluta como una cita a un spec inexistente. Arreglado por patrón —no por
  lista de excepciones— en `tests/test_docs_gobernanza.py`, con test en las dos direcciones. La
  lección operativa: **G2 solo mira ficheros trackeados**, así que correr la suite antes de commitear
  da un verde que no vale.

### 14.4 Reparto de la remediación (propuesta, pendiente de Nikolai)

Nada de esto está construido: la pieza A es un plan. Eso abarata casi todo — 22 de los 24 hallazgos
se cierran editando dos documentos, no tocando código en producción.

| bloque | qué | coste |
|---|---|---|
| **1. Mecánico y de redacción** (H-04, H-08, H-09, H-13, H-14, H-15, H-16, H-19, H-21, H-24, H-11, H-12, H-20, H-06, H-07, H-02, H-03, H-17, H-18, H-22, H-23) | rev. 2 del plan + rev. 4 de este spec | alto en volumen, nulo en riesgo |
| **2. Cambio de diseño** (H-01, y H-05 de rebote) | la rama passthrough archiva la generación anterior, y la fusión pasa a ser **autoritativa por `rel_path` reprocesado** en vez de acumular | cambia §6 y §7 |

**Decisión de Nikolai (2026-08-02): se rediseña y se construye sin esperar a Codex.** Los dos bloques
entran en la rev. 4 de este spec y en la rev. 2 del plan, y la construcción arranca a continuación.
Queda dicho lo que eso implica, porque el registro no debe maquillarlo: **la revisión de Codex, si se
hace, llegará sobre código ya escrito**, invirtiendo el orden que el contrato del proyecto fija para
un cambio de diseño; y el único ojo que ha visto este diseño nuevo es el de un revisor que comparte
modelo con su autor. Es una decisión de ritmo tomada con el coste a la vista, no un descuido.
