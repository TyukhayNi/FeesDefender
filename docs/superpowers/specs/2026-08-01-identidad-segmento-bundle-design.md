# Diseño — La identidad de un segmento de bundle: que el reproceso sustituya en vez de añadir

> **Estado:** rev. 1 (2026-08-01). Sin revisión adversarial todavía.
> **Alcance:** una función de `core/split_documental.py` y su único llamador, más un script de
> migración re-ejecutable. No toca el manifiesto, ni la segmentación, ni el motor de OCR, ni
> `00_Input`, ni la sala de lectura.
> **Disparador:** destapado al ejecutar D1 de `MEJORAS #90` (fila #1 de `PLAN.md`, punto (f)), y
> medido después en los 5 casos con sala de máquina: el defecto **ya estaba vivo antes de D1**.
> **Fuera de alcance:** el huerfanato que produce `apply --force` (§10.1), la conclusión sobre D1
> (cerrada aparte por falta de rendimiento) y la pérdida de texto del reproceso (entrada propia en
> `docs/MEJORAS_FUTURAS.md`).

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
invariante del proyecto: el pipeline nunca lo toca. Reprocesar un documento suelto produce el mismo
slug y **sobrescribe su MD en el sitio**.

El segmento de bundle es el único artefacto del pipeline cuyo nombre depende de algo que el propio
pipeline reescribe. Esa asimetría *es* el defecto, y por eso el arreglo consiste en eliminarla, no
en limpiar detrás de ella.

### 1.2 Los huérfanos no son inertes

Tres consumidores los ven, y ninguno los trata como lo que son:

| consumidor | qué hace | efecto |
|---|---|---|
| `preclasificar.py:209` (skill `organizar-sala-lectura`) | lee `03_MD/{fila.slug}.md` **guiado por la cobertura** | sirve a la sala de lectura la versión que cite el registro, aunque en disco haya otra más nueva |
| `core/sala_maquina.py:220` (`reconstruir_cobertura_desde_md`) | recorre `03_MD/*.md` en casos sin `_cobertura.json` | **convierte cada huérfano en una fila de cobertura** |
| `scripts/detectar_ocr_ciego.py:80` | ídem, para el cribado | cuenta huérfanos como candidatos |

## 2. Lo medido (2026-08-01, censo read-only sobre los 5 casos con sala de máquina)

| caso | segmentos `(parent, seg)` | con más de un sha | versiones |
|---|---|---|---|
| `W-02VND1` | 15 | **3** | 2 cada uno |
| `W-02VUDR` | 20 | **2** | **3** cada uno |
| `W-02T3XO`, `W-02XOR7`, `W-02TH0W` | 0 | 0 | — |

Total: **5 segmentos duplicados, 12 ficheros huérfanos** entre `02_Documentos/` y `03_MD/`, más los
de `raw_text/`.

**El defecto es anterior a D1.** Los duplicados de `W-02VUDR` están fechados el **2026-07-21**, con
**tres** versiones por segmento, mucho antes de que existiera `apply --solo`. D1 no lo introdujo: lo
hizo visible.

### 2.1 El estado incoherente en que quedó `W-02VND1`

La corrida de D1 del 2026-07-30 se interrumpió, y dejó el caso contradiciéndose a sí mismo:

- `_cobertura.json` y `_revisar/_cobertura.md` citan los segmentos del **23/07** (`991a5d78`,
  `0d51b98b`, `60732e16`);
- `02_Documentos/completo__c170a0f5/indice.json`, **regenerado el 30/07 a las 12:46**, cita los del
  **30/07** (`45806a62`, `07a8cbd0`, `441883cc`).

Los dos registros del mismo caso apuntan a ficheros distintos. Cualquiera de los dos es defendible
por separado; juntos, no.

## 3. Decisión

**La identidad de un segmento pasa a ser posicional:**

```python
def _slug_seg(parent_slug: str, seg: int, tipo: str) -> str:
    return f"{parent_slug}__seg{seg:02d}_{_norm_tipo(tipo)}"
```

Sus tres componentes son estables frente a un reproceso:

- `parent_slug` = `output_slug(rel_path, sha_del_origen)` — el origen vive en `00_Input`, inmutable;
- `seg` y `tipo` salen del **manifiesto**, que `apply` conserva salvo `--force`
  (`sala_maquina.py:583`).

`materializar` **sigue calculando `seg_sha`** y guardándolo en `DocLogico.seg_sha256` y en la fila de
cobertura: la custodia por contenido no se pierde, solo deja de gobernar el nombre. El
`emitido.replace(destino_pdf)` que ya existe sobrescribe en el sitio, que es exactamente lo que hace
un documento suelto.

`TIPO` es decorativo una vez que `{parent_slug}__seg{NN}` identifica. **Se conserva a propósito**:
estos nombres los lee el letrado, y `__seg02_DOC_PODER_NOTARIAL` dice algo que `__seg02` no dice. La
consecuencia de conservarlo está en §10.2.

### 3.1 La unicidad de `seg` pasa a ser portante, y hoy nadie la comprueba

`validar_manifiesto` (`split_documental.py:261`) valida que los rangos estén dentro del documento y
que no solapen, pero **no valida que `seg` no se repita**. Hoy eso es inocuo: si dos entradas
comparten `seg`, sus contenidos difieren, el sha8 desempata y salen dos ficheros. Con identidad
posicional **colisionarían**, y el segundo machacaría al primero **en silencio** — perdiendo un
documento lógico entero.

El manifiesto es editable por el letrado (es su gate), así que la entrada duplicada es alcanzable a
mano. Esta spec añade la comprobación: `seg` repetido → `ValueError` con el número, antes de
materializar nada. Es la contrapartida obligada del cambio, no un extra.

## 4. Alternativas descartadas

**Poda por identidad lógica** — mantener el sha8 y retirar, tras materializar, los artefactos previos
del mismo `(parent, seg)`. Conserva el direccionamiento por contenido y no exige migración, pero
convierte un borrado en consecuencia de una inferencia sobre nombres, añade superficie de fallo nueva
y hay que hacerlo bien también cuando la corrida muere a medias — que es justamente como murió la de
VND1. Nota sobre la clave que proponía `PLAN.md` para esta vía, `parent_sha256`+`role`+`paginas`:
**no sirve**. `role` vale `"documento"` en los 35 segmentos censados, y `paginas` cambia si el
letrado edita el manifiesto. La clave correcta es `seg`.

**Versionar explícitamente** (`superseded_by` en la fila y en el frontmatter). Cero borrado y
trazabilidad total, pero obliga a tocar los tres consumidores de §1.2 y a acertar en todos los
futuros; el que se olvide vuelve a servir el viejo. Traslada el coste al consumidor, que es
precisamente donde el defecto ya muerde.

## 5. Cambio del motor

Superficie: una función y su único llamador. `_slug_seg` no se usa en ningún otro sitio del repo
(verificado por búsqueda: solo `split_documental.py:280` y `:311`, más citas en el plan histórico
`2026-07-14-split-sala-maquina.md`, que es documentación).

1. `_slug_seg` pierde el parámetro `seg_sha256`.
2. `materializar` deja de pasárselo; sigue calculando `seg_sha = file_sha256(emitido)` para
   `DocLogico.seg_sha256`.
3. `validar_manifiesto` rechaza `seg` repetido (§3.1).
4. Nada más cambia: `destino="split"`, `paginas`, `fuentes`, `parent_sha256` y la generación del
   índice se mantienen.

## 6. Migración y saneamiento

Un solo script re-ejecutable, `scripts/migrar_slugs_segmento.py`, con **dry-run por defecto**,
siguiendo el patrón ya establecido por `core/migrar_nombres_informe.py` + CLI (que solo renombra,
nunca abre el contenido, y re-comprueba el destino entre plan y aplicación).

**Regla por grupo `(parent_slug, seg)`:**

| situación | acción |
|---|---|
| un solo sha en disco | renombrar sus artefactos a la identidad nueva |
| varios sha | **sobrevive el que cite `_cobertura.json`** (si no existe, `_cobertura.md`); los demás se mueven con su nombre viejo a `99_Versiones anteriores/migracion_slugs_<fecha>/`; después se renombra el superviviente |
| ninguno coincide con la cobertura, y hay **más de un** candidato | **no decidir**: avisar y dejar el grupo intacto |
| ninguno coincide con la cobertura y queda **un solo** candidato, ya con la identidad nueva | corrida anterior interrumpida a medias: completar los registros (§9) |

La regla de supervivencia la fijó Nikolai el 2026-08-01: **manda el registro, no la fecha del
fichero**. En `W-02VND1` eso conserva la versión del 23/07 —la anterior a D1—, lo que además evita
importar la pérdida de texto medida en el reproceso (§10.3).

Tras mover y renombrar, el script **actualiza el campo `slug` en `_cobertura.json` y regenera
`_revisar/_cobertura.md`** desde él, de modo que los dos registros del caso vuelvan a coincidir con
el disco — incluido el `indice.json` del bundle (§2.1).

## 7. Radio de la migración (medido, no supuesto)

| artefacto | ¿lleva el slug del segmento? | acción |
|---|---|---|
| `02_Documentos/<parent>/{slug}.pdf` | sí | renombrar |
| `02_Documentos/<parent>/indice.json`, campo `archivo` | sí | reescribir |
| `03_MD/{slug}.md` | sí | renombrar |
| `raw_text/` | **sí — 18 ficheros en `W-02VND1`** | renombrar |
| `_cobertura.json` (campo `slug`) | sí | reescribir |
| `_revisar/_cobertura.md` | sí | regenerar desde el JSON |
| `_segmentacion.json` (manifiesto) | no — `seg`/`pp`/`tipo`/`role`, sin slug | no se toca |
| `_sala_maquina_state.json` | no — solo shas de origen | no se toca |
| `01_OCR/` | no — 167 ficheros, 0 con `__seg` | no se toca |
| `00_Input/` | no | **nunca** se toca |
| `01_Procesado/Sala lectura/` | **no** — nombres canónicos, no slugs | no se toca |

La única referencia a un slug de segmento fuera de `02_Sala de máquina/` en todo `01_Procesado` de
`W-02VND1` es `_revisar/_cobertura.md`.

## 8. Contrato de tests

**El test que fija el arreglo falla hoy**: materializar el mismo bundle dos veces con bytes de
segmento distintos debe dejar **un PDF y un MD por segmento**, y **N** filas de cobertura, no 2N.

Motor:
1. `_slug_seg` puro: mismo `(parent, seg, tipo)` → mismo slug, con contenido distinto.
2. E2E de sala de máquina: doble materialización → 1 artefacto por segmento (el de arriba).
3. `DocLogico.seg_sha256` sigue reflejando el contenido nuevo tras el reproceso (la custodia no se
   pierde al sacarla del nombre).
4. Manifiesto con `seg` repetido → `ValueError` antes de materializar. Sin la comprobación, el
   segundo segmento machaca al primero y el test lo enseña (§3.1).

Migración:
5. Dry-run no modifica nada en disco.
6. Grupo de un solo sha → renombrados los tres artefactos con nombre (`.pdf`, `.md`, `raw_text/`) y
   reescritas las tres referencias (`indice.json`, `_cobertura.json`, `_cobertura.md`).
7. Grupo duplicado → sobrevive el que cita la cobertura; los demás quedan en
   `99_Versiones anteriores/` **con su nombre viejo**.
8. Grupo sin coincidencia con la cobertura **y con más de un candidato** → intacto, con aviso.
9. **Reanudación** (§9): grupo cuyo superviviente ya está renombrado y cuya cobertura todavía cita el
   nombre viejo → la segunda pasada lo completa en vez de declararlo ambiguo.
10. Idempotencia: segunda pasada sobre un caso ya migrado = 0 cambios.
11. Colisión (el destino ya existe con contenido distinto) → aborta ese grupo, avisa, y no toca el
    resto del caso.
12. Guard de coherencia: tras migrar, toda fila de `_cobertura.json` cita un fichero que existe.

Los asertos sobre mensajes usan frases con espacios, nunca subcadenas que el nombre del test pueda
inyectar en la salida capturada (regla heredada del 47º cierre).

## 9. Riesgos y guardarraíles

- **Escribe en el Drive.** Dry-run por defecto; respaldo antes de mover; `00_Input` intacto.
- **Checkout abierto**: el script salta el caso cuyo `_caso.md` no esté `disponible`, con aviso. Es
  la misma cautela que se aplicó a D1.
- **El Drive sincroniza durante la corrida**: se re-comprueba el destino entre el plan y la
  aplicación, como ya hace `migrar_nombres_informe`.
- **Fallo a medias, y aquí la primera redacción de esta spec se equivocaba.** El orden es
  mover-los-perdedores → renombrar-el-superviviente → reescribir los registros. Si se interrumpe
  **entre el renombrado y la reescritura**, la cobertura cita un nombre que ya no existe y la regla
  «sobrevive el que cite la cobertura» no encuentra a nadie: con la regla escrita a secas, la
  re-ejecución **no converge, se planta**. Por eso la tabla de §6 distingue el caso: si tras el
  filtro queda **un solo** candidato y ya lleva la identidad nueva, es una corrida interrumpida y se
  completan los registros. Si quedan varios y ninguno casa, se avisa y no se toca — ahí sí falta
  información para decidir.

## 10. Residuos declarados

1. **`apply --force` sigue dejando huérfanos.** Regenera el manifiesto y escribe cobertura fresca
   (`previa=[]`), así que los artefactos de la corrida anterior quedan en disco sin fila que los
   cite. Es la misma clase de fuga por otra puerta, no la arregla esta spec, y el script de
   migración la limpia si se vuelve a dar.
2. **Editar `tipo` en el manifiesto renombra el segmento** y deja el anterior huérfano, porque `TIPO`
   va en el nombre (§3). Es un acto deliberado del letrado, es raro, y lo limpia una re-ejecución del
   script. Se acepta a cambio de que los nombres sigan siendo legibles.
3. **El reproceso puede perder texto.** Medido el 2026-08-01 en los tres segmentos de `W-02VND1` que
   sí se reprocesaron: seg01 +0 chars, seg02 −6, seg03 +288 (+0,18 %), y en seg03 **77 palabras
   únicas del original no aparecen en la versión nueva** (1,2 %), entre ellas cifras y fechas. Esto
   **contradice** lo que afirma el §(c2) de `PLAN.md` («el 100 % de las palabras del original
   sobrevive»). No es objeto de esta spec —tiene entrada propia en `docs/MEJORAS_FUTURAS.md`— pero sí
   es el motivo por el que la regla de supervivencia de §6 conserva la versión del registro.

## 11. Criterio de salida

- El test de doble materialización pasa, y retirarle el arreglo lo mata.
- Suite verde.
- Dry-run de la migración sobre los 5 casos: lista 35 segmentos, 5 grupos duplicados, 0 grupos sin
  coincidencia con la cobertura.
- Tras aplicar: censo de duplicados **0**; `_cobertura.json`, `_cobertura.md` e `indice.json` del
  bundle citan los mismos ficheros; segunda pasada del script = 0 cambios.
- `00_Input` con los mismos sha antes y después.
