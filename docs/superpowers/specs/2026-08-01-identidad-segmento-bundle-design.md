# Diseño — La identidad de un segmento de bundle: que el reproceso sustituya en vez de añadir

> **Estado:** **rev. 2** (2026-08-01), tras revisión adversarial de Codex con veredicto **NO SHIP**
> sobre la rev. 1 (2 B0 + 5 A + 3 M). **La decisión central de la rev. 1 era insegura y se ha
> sustituido**: la identidad ya no es el ordinal `seg`, sino un `doc_id` persistente (§3). La
> adjudicación de los diez hallazgos está en §12.
> **Alcance:** `core/split_documental.py`, el contrato del manifiesto, el aislamiento de errores de
> `core/sala_maquina.ejecutar`, y un script de migración re-ejecutable. No toca el motor de OCR, ni
> `00_Input`, ni la sala de lectura, ni el log forense.
> **Disparador:** destapado al ejecutar D1 de `MEJORAS #90` (fila #1 de `PLAN.md`, punto (f)), y
> medido después en los 5 casos con sala de máquina: el defecto **ya estaba vivo antes de D1**.
> **Fuera de alcance:** la conclusión sobre D1 (cerrada por falta de rendimiento el 2026-08-01) y la
> pérdida de texto del reproceso (`MEJORAS #111`).

## 1. El defecto

La identidad de un documento lógico extraído de un bundle la fija `_slug_seg`
(`core/split_documental.py:280`):

```python
def _slug_seg(parent_slug: str, seg: int, tipo: str, seg_sha256: str) -> str:
    return f"{parent_slug}__seg{seg:02d}_{_norm_tipo(tipo)}__{seg_sha256[:8]}"
```

`seg_sha256` es el sha del **PDF del segmento ya recortado** (`materializar`,
`split_documental.py:310-313`), es decir, de un artefacto **derivado**. Basta con que el bundle
padre se re-OCR-ice para que los bytes del recorte cambien, y con ellos el sha, el slug, y por tanto
el nombre de todos los artefactos del segmento. Los anteriores no se retiran: **nada poda**.

`fusionar_cobertura` (`core/sala_maquina.py:344`) indexa por `(rel_path, slug)`, así que la fila
nueva no sustituye a la vieja: se añade al lado.

### 1.1 La asimetría, que es lo que señala el arreglo

Un documento **suelto** no sufre esto. Su slug es `output_slug(rel_path, sha)` con el sha del
**fichero de origen en `00_Input`** (`sala_maquina.py:188`), y ese fichero es inmutable por
invariante del proyecto. Reprocesar un documento suelto produce el mismo slug y **sobrescribe su MD
en el sitio**.

El segmento de bundle es el único artefacto del pipeline cuyo nombre depende de algo que el propio
pipeline reescribe.

### 1.2 Los huérfanos no son inertes

| consumidor | qué hace | efecto |
|---|---|---|
| `preclasificar.py:209` (skill `organizar-sala-lectura`) | lee `03_MD/{fila.slug}.md` **guiado por la cobertura** | sirve la versión que cite el registro, aunque en disco haya otra más nueva |
| `core/sala_maquina.py:220` (`reconstruir_cobertura_desde_md`) | recorre `03_MD/*.md` en casos sin `_cobertura.json` | **convierte cada huérfano en fila de cobertura** |
| `scripts/detectar_ocr_ciego.py:80` | ídem, para el cribado | cuenta huérfanos como candidatos |

## 2. Lo medido (2026-08-01, censo read-only sobre los 5 casos con sala de máquina)

| caso | grupos `(parent, seg)` | duplicados | versiones | PDF | MD | raw_text |
|---|---:|---:|---|---:|---:|---:|
| `W-02VND1` | 15 | **3** | 2, 2, 2 | 18 | 18 | 18 |
| `W-02VUDR` | 20 | **2** | 3, 3 | 24 | 24 | 24 |
| `W-02T3XO`, `W-02XOR7`, `W-02TH0W` | 0 | 0 | — | 0 | 0 | 0 |

**Excedentes: 7 PDF + 7 MD + 7 `raw_text` = 21 ficheros**, sobre 5 grupos lógicos duplicados.
(La rev. 1 decía «12 huérfanos entre `02_Documentos` y `03_MD`»: **era erróneo**, son 14 ahí y 21 en
total. Recontado de forma independiente al adjudicar el hallazgo M-3.) Todo `raw_text` usa `.txt`.

**El defecto es anterior a D1.** Los duplicados de `W-02VUDR` están fechados el **2026-07-21**, con
tres versiones por segmento, mucho antes de que existiera `apply --solo`.

### 2.1 El estado incoherente en que quedó `W-02VND1`

- `_cobertura.json` y `_revisar/_cobertura.md` citan los segmentos del **23/07**;
- `02_Documentos/completo__c170a0f5/indice.json`, **regenerado el 30/07 a las 12:46**, cita los del
  **30/07**.

Los dos registros del mismo caso apuntan a ficheros distintos.

## 3. Decisión: `doc_id` persistente, acuñado una vez

**La identidad de un documento lógico es un `doc_id` que vive en el manifiesto, se acuña una sola
vez y se conserva a través de las regeneraciones.** El slug pasa a ser:

```python
def _slug_seg(parent_slug: str, doc_id: str, tipo: str) -> str:
    return f"{parent_slug}__{doc_id}_{_norm_tipo(tipo)}"
```

`doc_id` es `d01`, `d02`… acuñado correlativamente **en la primera construcción** del manifiesto y
**nunca reasignado**. `materializar` sigue calculando `seg_sha` y guardándolo en
`DocLogico.seg_sha256` y en la fila de cobertura: la custodia por contenido no se pierde, solo deja
de gobernar el nombre.

`TIPO` se conserva en el nombre por legibilidad —estos ficheros los lee el letrado—, y ahora es
**inocuo** que cambie: el `doc_id` es quien identifica, así que un `tipo` editado es un renombrado
detectable, no una identidad nueva.

### 3.1 Por qué NO el ordinal `seg` (lo que proponía la rev. 1)

`seg` se **regenera**. Con `--force`, `usar_previo = manifiesto_existe(...) and not force`
(`sala_maquina.py:583`) es falso y `construir_manifiesto` reconstruye la lista desde `detectar`. Si
la segmentación cambia —y cambia justamente cuando se re-OCR-iza, que es el caso de uso— `seg02`
puede pasar a designar **otro documento**. Con el mismo `TIPO`, el slug coincide y el documento
anterior **se sobrescribe sin dejar huérfano ni rastro**: la rev. 1 convertía un defecto ruidoso
(ficheros de más) en uno silencioso (sustitución semántica). Es el hallazgo B0-2, y es dirimente.

### 3.2 El contrato de reconciliación del manifiesto

`--force` deja de **sustituir** el manifiesto y pasa a **reconciliarlo**:

1. Se detecta la segmentación nueva.
2. Cada segmento nuevo se casa con una entrada del manifiesto anterior por **igualdad exacta de
   `pp`**. Igualdad exacta, no solapamiento: el solapamiento admite empates y haría la identidad
   dependiente de un desempate.
3. Casado → **hereda su `doc_id`**. Sin casar → **acuña uno nuevo**, correlativo al máximo existente
   (nunca reutiliza uno retirado).
4. Entrada anterior que no case con ninguna nueva → su `doc_id` queda **retirado**: sus artefactos
   se archivan en `99_Versiones anteriores/` y se declara en el evento. No se borran ni se dejan
   sueltos.

Consecuencia declarada: **los `doc_id` dejan de ir en orden de página** cuando se inserta un
segmento nuevo entre dos existentes. Es el precio de que la identidad sobreviva. El orden de lectura
lo da `pp`, que está en el manifiesto y en la cobertura, no el nombre del fichero.

### 3.3 La unicidad de `seg` sigue haciendo falta, y hoy nadie la comprueba

`validar_manifiesto` (`split_documental.py:261`) valida rangos y solapes, pero **no valida que `seg`
no se repita** — ni, ahora, que `doc_id` no se repita. El manifiesto es editable por el letrado, así
que la entrada duplicada es alcanzable a mano, y con identidad estable dos entradas iguales
colisionan y una machaca a la otra.

Y **no basta con lanzar `ValueError`**: `ejecutar` captura cualquier excepción por documento
(`sala_maquina.py:732`) y la convierte en una fila `metodo=error, estado=empty`, con la corrida
siguiendo y **exit 0**. Queda rastro en el registro, pero el bundle entero se degrada y el documento
machacado no deja rastro propio. Por eso:

- se define `ManifestValidationError`, específica;
- `ejecutar` la **deja pasar** en vez de absorberla (excepción declarada a su invariante de
  aislamiento: un manifiesto malformado es error del operador sobre el bundle entero, no un fallo de
  un documento);
- la CLI aborta con salida distinta de cero **antes de materializar nada**, nombrando bundle y
  entrada duplicada.

## 4. Alternativas descartadas

**Ordinal `seg` como identidad (rev. 1)** — descartada por §3.1.

**Mantener el sha en el nombre y podar** — conserva el direccionamiento por contenido y no exige
migración, pero convierte un borrado en consecuencia de una inferencia sobre nombres y hay que
acertar también cuando la corrida muere a medias, que es como murió la de VND1. La clave que
proponía `PLAN.md` para esta vía —`parent_sha256`+`role`+`paginas`— **no sirve**: `role` vale
`"documento"` en los 35 segmentos censados y `paginas` cambia si el letrado edita el manifiesto.

**Versionar explícitamente** (`superseded_by`) — cero borrado y trazabilidad total, pero obliga a
tocar los tres consumidores de §1.2 y a acertar en todos los futuros; el que se olvide vuelve a
servir el viejo.

## 5. Custodia: no sobrescribir sin archivar antes

Sacar el sha del nombre tiene un precio que la rev. 1 no contabilizó (hallazgo B0-1). Hoy, un fallo
a mitad de la generación deja el fichero nuevo con nombre nuevo y **el viejo intacto**, así que la
fila de cobertura —que guarda el sha del **propio segmento**, `sala_maquina.py:600`— sigue siendo
verdadera. Con identidad estable, `emitido.replace(destino_pdf)` sobrescribe, y si después falla el
MD o la extracción, **la fila declara un sha que ya no corresponde a esos bytes**: custodia
falsificada, y el guard «la fila cita un fichero que existe» la da por buena.

Dos medidas, y ninguna exige un journal completo del motor:

1. **Archivar antes de sobrescribir.** Si el destino existe y su sha difiere del que se va a
   escribir, su generación completa (PDF + MD + `raw_text`) se mueve a
   `99_Versiones anteriores/reproceso_<fecha>/` **antes** de escribir. Un fallo posterior deja la
   versión anterior recuperable y localizable.
2. **Guard de coherencia por hash, no por existencia.** Al final de `apply`, cada fila de segmento
   se comprueba contra el fichero real: `sha256` de la fila == sha del PDF en disco. Discrepancia →
   aviso ruidoso nombrando el segmento. Esto es lo que convierte B0-1 de silencioso en detectado, y
   de paso mata el criterio vacuo de la rev. 1 (hallazgo M-2).

## 6. Migración y saneamiento

Un solo script re-ejecutable, `scripts/migrar_slugs_segmento.py`, **dry-run por defecto**, siguiendo
el patrón de `core/migrar_nombres_informe.py` (solo renombra, nunca abre contenido, re-comprueba el
destino entre plan y aplicación).

### 6.1 Contrato frente a la cobertura — 0, 1 o N coincidencias

| coincidencias del grupo en `_cobertura.json` | acción |
|---|---|
| **exactamente 1** | esa versión sobrevive; las demás se archivan con su nombre viejo en `99_Versiones anteriores/migracion_slugs_<fecha>/`; después se renombra la superviviente |
| **0** | **no decidir**: avisar y dejar el grupo intacto |
| **N > 1** | **abortar el grupo**: la cobertura reclama dos versiones del mismo documento lógico y no hay regla que elija sin inventar. Resolución manual |

La regla la fijó Nikolai el 2026-08-01: **manda el registro, no la fecha del fichero**. En
`W-02VND1` eso conserva la versión del 23/07 —anterior a D1—, lo que además evita importar la
pérdida de texto medida en el reproceso (`MEJORAS #111`).

Medido: hoy los 5 grupos duplicados tienen **exactamente una** coincidencia, así que el camino N>1
no está ejercitado por dato real. Se especifica igualmente porque `fusionar_cobertura` puede
producirlo (hallazgo A-2).

### 6.2 Casos legacy sin `_cobertura.json`

**No son migrables automáticamente**: se avisa y se dejan intactos. No se infiere el superviviente
desde la tabla humana `_cobertura.md`, que no tiene parser canónico ni contrato de escapado
(hallazgo A-3). Coste real hoy: **cero** — `W-02XOR7` es el único caso sin `_cobertura.json` y no
tiene ningún segmento.

### 6.3 Journal por grupo, y reanudación que no adivina

La rev. 1 proponía reanudar infiriendo la operación previa a partir del estado del disco. No es
suficiente: un fichero con la identidad nueva puede venir de una migración interrumpida, de una
edición manual o de otra sesión, y además PDF, MD y `raw_text` se operan por separado, así que un
fallo puede dejar una representación renombrada y dos no (hallazgo A-4).

Se escribe un **journal por grupo** —fuera del caso, junto al informe de la corrida— con: `doc_id`
destino, sha de origen y de destino de cada representación, fase alcanzada y ruta del archivo de
respaldo. Al reanudar se valida el estado real contra el journal; si no coincide, **falla cerrado**
y no toca nada.

### 6.4 Concurrencia y protocolo de préstamo

`MERGE_EXCLUSIONS` (`core/config.py:391`) **no** incluye `99_Versiones anteriores`, y `GRUPOS_MERGE`
(`config.py:434`) solo cubre el trío de la vista procesal: los renombrados y los retirados irían al
merge de 3 vías fichero a fichero, sin grupo indivisible, de modo que una copia desfasada puede
resucitar un nombre retirado o publicar media generación (hallazgo A-5, confirmado contra la
fuente).

La migración corre **solo sobre la copia canónica, con el lock del protocolo adquirido** y con el
caso en `disponible`. Con el lock puesto no hay copia operativa divergente que mergear, y el
problema no se plantea. Un checkout **posterior** a la migración es inofensivo: ambos lados ya
coinciden.

**Declarado y no resuelto aquí:** si conviene que `99_Versiones anteriores/**` entre en
`MERGE_EXCLUSIONS`, o que la generación de un segmento sea un grupo indivisible de `GRUPOS_MERGE`.
Las dos cosas tienen radio más allá de esta pieza y no se deciden de rebote.

## 7. Radio de la migración (medido, no supuesto)

| artefacto | ¿lleva el slug? | acción |
|---|---|---|
| `02_Documentos/<parent>/{slug}.pdf` | sí | renombrar |
| `02_Documentos/<parent>/indice.json`, campo `archivo` | sí | reescribir |
| `03_MD/{slug}.md` | sí | renombrar |
| `raw_text/{slug}.txt` | **sí — 18 en VND1, 24 en VUDR** | renombrar |
| `_cobertura.json` (campo `slug`) | sí | reescribir |
| `_revisar/_cobertura.md` | sí | regenerar desde el JSON |
| `_segmentacion.json` (manifiesto) | no lleva slug | **sí se toca**: gana `doc_id` por entrada (§8) |
| `_sala_maquina_state.json` | no — solo shas de origen | no se toca |
| `01_OCR/` | no — 167 ficheros, 0 con `__seg` | no se toca |
| `00_Input/` | no | **nunca** |
| `01_Procesado/Sala lectura/` | no — nombres canónicos | no se toca |
| **`_intake_log.jsonl`** | **sí** — los eventos `split_documental` citan slugs (`sala_maquina.py:602-606`) | **NUNCA se reescribe** |

La última fila es doctrina, no omisión: el log es forense y append-only. **Seguirá citando los slugs
viejos para siempre, y eso es correcto** — describe lo que pasó cuando pasó. La migración emite su
propio evento; no reescribe la historia.

## 8. Retrofit del manifiesto

Los manifiestos existentes (`_segmentacion.json`) no tienen `doc_id`. La migración se lo añade:
`doc_id` correlativo por orden de `seg`, congelado en ese momento. A partir de ahí es inmutable y la
reconciliación de §3.2 lo preserva. Un manifiesto sin `doc_id` que llegue al motor después de la
migración se trata como legacy: se acuña al vuelo y se persiste, con aviso.

## 9. Contrato de tests

**El test que fija el arreglo falla hoy**: materializar el mismo bundle dos veces con bytes de
segmento distintos debe dejar **un PDF, un MD y un `raw_text` por documento lógico**, y **N** filas
de cobertura, no 2N. Debe cambiar los bytes de verdad, y comprobar que las tres representaciones y
la fila pertenecen a la **misma generación** (hashes coherentes), no solo que existan.

Motor:
1. `_slug_seg` puro: mismo `(parent, doc_id, tipo)` → mismo slug, con contenido distinto.
2. Doble materialización → un artefacto por documento lógico, con hashes coherentes.
3. `DocLogico.seg_sha256` refleja el contenido nuevo tras el reproceso.
4. **Reconciliación (§3.2)**: `--force` con segmentación idéntica → los `doc_id` se conservan;
   con un segmento partido en dos → el que conserva `pp` hereda y el nuevo acuña; con un segmento
   desaparecido → su `doc_id` se retira y sus artefactos se archivan.
5. **B0-2 explícito**: `--force` que renumera de modo que `seg02` pase a designar otro documento —
   con `doc_id` **no** se sobrescribe; retirando la reconciliación, el test muere.
6. `doc_id` o `seg` repetido en el manifiesto → `ManifestValidationError`, que **atraviesa**
   `ejecutar` y da salida distinta de cero **desde la CLI**, no solo desde la función pura.
7. **Custodia (§5)**: fallo inyectado después de sobrescribir el PDF y antes del MD → la generación
   anterior está en `99_Versiones anteriores/` y el guard de hash **detecta** la discrepancia.

Migración:
8. Dry-run no modifica nada.
9. Grupo con una coincidencia → renombradas las tres representaciones y reescritas las tres
   referencias.
10. Grupo con **cero** coincidencias → intacto, con aviso. Grupo con **N>1** → abortado, con aviso.
11. Caso legacy sin `_cobertura.json` → no migrable, intacto, con aviso.
12. Interrupción tras cada fase (mover, renombrar cada representación, reescribir cada registro) →
    la reanudación valida contra el journal y converge; journal incoherente → falla cerrado.
13. Idempotencia: segunda pasada = 0 cambios.
14. Colisión de destino con contenido distinto → aborta ese grupo, no toca el resto del caso.
15. Migración con checkout abierto o sin lock → se niega a correr.
16. Guard final: ningún slug viejo sobrevive **dentro del radio autorizado**, y el
    `_intake_log.jsonl` conserva los suyos **intactos**.

Los asertos sobre mensajes usan frases con espacios, nunca subcadenas que el nombre del test pueda
inyectar en la salida capturada (regla del 47º cierre).

## 10. Residuos declarados

1. **`apply --force` ya no deja huérfanos silenciosos**, porque reconcilia (§3.2). Lo que sí deja son
   `doc_id` **retirados** con sus artefactos archivados: visible y recuperable, por diseño.
2. **La interacción fina con `GRUPOS_MERGE` / `MERGE_EXCLUSIONS` queda declarada, no resuelta**
   (§6.4). La migración la esquiva corriendo bajo lock sobre el canon.
3. **`_intake_log.jsonl` seguirá citando slugs viejos.** Es correcto y deliberado (§7).
4. **El reproceso puede perder texto** (`MEJORAS #111`). Ajeno a esta spec, pero es el motivo por el
   que §6.1 conserva la versión del registro.

## 11. Criterio de salida

- El test de doble materialización pasa, y retirarle el arreglo lo mata.
- El test de B0-2 (renumeración con `--force`) pasa, y retirar la reconciliación lo mata.
- La duplicidad en el manifiesto aborta **desde la CLI** con salida distinta de cero.
- El guard de hash detecta una generación incoherente inyectada a propósito.
- Suite verde (base actual: 2612 passed, 77 skipped, 7 xfailed).
- Dry-run sobre los 5 casos: 35 grupos, 5 duplicados, 5 con una sola coincidencia, 0 abortados.
- Tras aplicar: 0 excedentes; `_cobertura.json`, `_cobertura.md` e `indice.json` citan los mismos
  ficheros; segunda pasada = 0 cambios; `_intake_log.jsonl` **byte-idéntico**.
- `00_Input` con los mismos sha antes y después.

## 12. Adjudicación de la revisión adversarial (Codex, 2026-08-01, NO SHIP)

Handoff: `docs/superpowers/handoffs/handoff-2026-08-01-identidad-segmento-codex-review.md`.

| ID | Adjudicación | Dónde se resuelve |
|---|---|---|
| B0-1 | **Confirmado** verificando `sala_maquina.py:600` (la fila guarda el sha del propio segmento) | §5, con archivado previo + guard por hash, en vez del journal completo del motor que pedía el informe |
| B0-2 | **Confirmado, y dirimente** — cambia la decisión central | §3, §3.1, §3.2 |
| A-1 | **Confirmado en sustancia; línea mal atribuida** por el revisor: el `except` de `_split_o_md:562` envuelve solo `split.detectar`; quien absorbe es `ejecutar:732` | §3.3 |
| A-2 | Aceptado como hueco de contrato; medido que hoy no hay dato que lo ejercite | §6.1 |
| A-3 | Aceptado | §6.2 |
| A-4 | Aceptado | §6.3 |
| A-5 | **Confirmado** contra `config.py:391` y `:434` | §6.4 |
| M-1 | Aceptado, y amplía el radio: el log forense cita slugs y **no** debe reescribirse | §7 |
| M-2 | Aceptado: el criterio de la rev. 1 era vacuo | §5.2, §9.2, §11 |
| M-3 | **Confirmado recontando de forma independiente**: 21 excedentes, no 12 | §2 |

**Lo que el informe cerraba y no procede:** una frase final sobre «la retirada de Gemini de los
workflows» que no corresponde a este encargo. Se ignora.
