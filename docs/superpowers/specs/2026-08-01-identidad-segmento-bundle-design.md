# Diseño — La identidad de un segmento de bundle: que el reproceso sustituya en vez de añadir

> **Estado:** **rev. 3** (2026-08-01), tras **dos** revisiones adversariales de Codex, ambas
> **NO SHIP** (rev. 1: 2 B0 + 5 A + 3 M; rev. 2: 4 B0 + 5 A + 2 M). La rev. 2 cambió la decisión
> central —del ordinal `seg` a un `doc_id` persistente— y la rev. 3 **parte el trabajo en dos
> piezas** y corrige el ciclo de vida de ese `doc_id`, que la rev. 2 dejó sin contrato seguro.
> Adjudicación de las dos pasadas en §13.
> **Disparador:** destapado al ejecutar D1 de `MEJORAS #90` (fila #1 de `PLAN.md`, punto (f)) y
> medido en los 5 casos con sala de máquina: el defecto **ya estaba vivo antes de D1**.
> **Fuera de alcance:** D1 (cerrada por falta de rendimiento el 2026-08-01) y la pérdida de texto del
> reproceso (`MEJORAS #111`).
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
| Estado | **Construible ya** | **BLOQUEADA** hasta la Fase 2 de la fila #3 |

El corte lo propuso la 2ª revisión (N-M-2) y lo decidió Nikolai: son dos superficies con modos de
fallo y despliegues distintos. Cambiar el motor es permanente y reversible por git; migrar datos
reales bajo protocolo de préstamo, no.

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

Además del formato, **cada destino final se valida con `destino_seguro` contra `carpeta_bundle`**.
Cinturón y tirantes, porque el coste es una línea y el fallo es escribir fuera del expediente.

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
cero, **cero bytes escritos**. El aislamiento por documento de `ejecutar` queda intacto.

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

## 7. Custodia: publicar por generación, y un guard que mire en los dos sentidos

Sacar el sha del nombre tiene un precio: `emitido.replace(destino_pdf)` sobrescribe, y la fila de
cobertura guarda el sha del **propio segmento** (`sala_maquina.py:600`), de modo que un fallo a
media generación deja la fila declarando un sha que ya no corresponde a esos bytes.

1. **Publicación por generación.** Las tres representaciones (PDF, MD, `raw_text`) se escriben a
   *staging* dentro de la carpeta del bundle y se publican por renames al final. La generación
   anterior se mueve a `99_Versiones anteriores/reproceso_<fecha>/` **como conjunto**: si el
   archivado no puede completar las tres, no se publica ninguna.
2. **El fallo del evento no descarta el trabajo.** `_split_o_md` devuelve sus filas aunque
   `append_event` (`:602`) falle. Hoy, una excepción ahí sube a `ejecutar:732` y **se pierden las
   filas de todos los segmentos** del bundle.
3. **Guard bidireccional, y aborta.** No basta con recorrer las filas: en el fallo real no hay filas
   de segmento —`ejecutar:732` emite **una** fila de error con el slug del documento **físico**—, y
   con `--force` además `previa=[]`. El guard de la rev. 2 estaba **ciego justo en el caso para el
   que se escribió**. Ahora:
   - fila → fichero: las **tres** representaciones existen y su sha casa con el declarado;
   - fichero → fila: todo `02_Documentos/<parent>/*.pdf` tiene fila;
   - discrepancia → **salida distinta de cero**, nombrando segmento y representación. No un aviso.

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

## 9. Criterio de salida — Pieza A

- Los tests 2, 6, 7 y 8 pasan y **mueren al retirarles su arreglo** (mutación verificada, incluida la
  de «acuñar siempre»).
- Preflight: manifiesto inválido aborta desde la CLI con exit ≠ 0 y cero bytes escritos.
- Suite verde (base: 2612 passed, 77 skipped, 7 xfailed).
- Ningún caso real tocado.

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

Manda el registro, no la fecha (decisión de Nikolai). En `W-02VND1` eso conserva la del 23/07,
anterior a D1, lo que evita importar la pérdida de texto de `MEJORAS #111`. Casos legacy sin
`_cobertura.json`: **no migrables automáticamente** — hoy cuesta cero, `W-02XOR7` es el único y no
tiene segmentos.

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

## 13. Adjudicación de las revisiones adversariales

Handoffs: `docs/superpowers/handoffs/handoff-2026-08-01-identidad-segmento-codex-review.md` (1ª) y
`…-review-2.md` (2ª).

**1ª pasada (NO SHIP, sobre rev. 1):** B0-2 dirimente, cambió la decisión central. Cerrados en la
rev. 2 y confirmados por la 2ª pasada: B0-2, A-2, A-3, M-1, M-3. Quedaron **a medias** —y la 2ª
pasada tuvo razón en decirlo— B0-1, A-1, A-4, A-5 y M-2.

**2ª pasada (NO SHIP, sobre rev. 2):**

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
