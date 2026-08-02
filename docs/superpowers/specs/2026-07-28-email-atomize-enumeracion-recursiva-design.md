# Diseño — Enumeración recursiva del atomizador de correo (`MEJORAS #98`) y poda que no borra a ciegas

> **Estado:** **rev. 2** (2026-07-29), tras revisión adversarial de Codex con veredicto **NO-SHIP**
> y 6 bloqueantes, todos aceptados y resueltos (§11). La rev. 1 (2026-07-28) fue aprobada en chat
> antes de escribirse.
> **Alcance:** **motor** (`core/email_atomize/`), a diferencia del PR anterior, que era cableado.
> **Origen:** `MEJORAS #98`, más un segundo defecto de la misma familia hallado al diseñar
> (el `except OSError` silencioso de `iter_avistamientos`).
> **Fuera de alcance:** `--extraer-adjuntos` a default `True` (casilla 3 de
> `[SIGUIENTE-CABLEADO-CORREO]`, que este trabajo **desbloquea** pero no toca), poda de
> `adjuntos/` y publicación atómica (`MEJORAS #99`), OCR de adjuntos (`#87`), consumo por la
> sala de lectura (`#86`).
> **Antecedente directo:** `docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-design.md`
> y su plan `docs/superpowers/plans/2026-07-28-cableado-atomize-sala-maquina.md`, del que este
> diseño **retira** deliberadamente una parte (§5).
> **Disciplina:** brainstorming → spec → plan → TDD → revisión adversarial.

## 1. Contexto

### 1.1. El defecto de `#98`, con el layout real

`core/email_atomize/extract.py::iter_avistamientos` enumera con `base.glob("*.eml")`: **solo el
nivel superior**. Y `core/email_export.py::_escribe_mensaje`, cuando se exporta con
`--extraer-adjuntos` y el mensaje **trae adjunto**, crea una subcarpeta y escribe ahí el `.eml`
junto a sus adjuntos sueltos, **sin dejar copia en el nivel superior** (`return` temprano,
`email_export.py:1123-1131`).

Consecuencia con 10 correos exportados, 6 con adjunto:

```
00_Input/<lote>/
    2026-03-02_oferta.eml          ← visible
    2026-03-05_respuesta.eml       ← visible
    …                              ← 4 sin adjunto, visibles
    2026-03-04_arras/              ← INVISIBLE para el atomizador
        2026-03-04_arras.eml
        contrato_arras.pdf
    …                              ← 6 subcarpetas, 6 mensajes perdidos
```

El informe dice «4 mensajes» y nadie tiene con qué contrastar ese 4. Los perdidos son
**exactamente los que llevan documento adjunto**, que en un expediente de honorarios es donde
está la prueba.

### 1.2. Medición: el bug está armado y nunca ha disparado

Verificado sobre el único caso con correo masivo del repo, **W-02VND1**: `03_Email` tiene **277
`.eml` en el nivel superior y 277 recursivos** — cero en subcarpeta. Sus dos subcarpetas de primer
nivel son del **rescate de enlaces de Drive** (`<stem>/_enlaces/` con PDFs), no de
`--extraer-adjuntos`. Y los `.eml` rescatados de un enlace se depositan **a primer nivel**
(`_deposita_mensaje_rescatado`, `email_export.py:536-556`), así que `_enlaces/` no aporta correo.

Dos consecuencias de diseño:

1. **El único productor de `.eml` en subcarpeta es `--extraer-adjuntos`.** No hay que excluir
   ninguna subcarpeta: la enumeración recursiva no recoge basura, porque no hay basura que
   recoger.
2. **No existen datos reales sobre los que verificar el arreglo** (§7).

### 1.3. Segundo defecto, misma familia: el fallo de lectura silencioso

`iter_avistamientos` hace `except OSError: continue` (`extract.py:54-57`). Un `.eml` que no se
pueda leer **desaparece sin nota**, igual que uno invisible. Y aguas abajo, la poda de
idempotencia (`pipeline.py:121-124`) borra los `mensajes/*.md` que no estén en el conjunto
esperado.

Sobre `G:` esto no es teórico: `CASOS_ROOT` es Drive **Stream con caché**, no Mirror (memoria
`project-ocr-pipeline-drive-mirror`), así que un fichero presente pero no hidratado puede fallar
la lectura. Escenario: de 10 correos, 3 no se leen esa mañana → el motor ve 7 → **borra las
fichas de los otros 3** creyendo que se retiraron → informe `ok`.

**La guarda del PR anterior NO lo caza**, porque compara conteos de disco (`glob` vs `rglob`) y
ahí los dos dan 10. Es el mismo daño por otra puerta.

## 2. Objetivos y no-objetivos

**Objetivos.**

1. Que el atomizador vea **todos** los `.eml` de sus carpetas fuente, incluidos los que
   `--extraer-adjuntos` deja en subcarpetas.
2. Que la llave del registro de procesados sea **única** (hoy es el nombre del fichero, que con
   subcarpetas colisiona) — es lo que `MEJORAS #86` planea leer para saber qué está cubierto.
3. Que un fallo de lectura sea **declarado** y **nunca** derive en poda: no se borran fichas a
   partir de una foto incompleta.
4. Que la Capa A siga **byte-idéntica** y ningún `MSG-`/`ATT-` se renumere.

**No-objetivos.**

- No se enciende `--extraer-adjuntos` por defecto. Este trabajo lo **desbloquea**; la decisión es
  aparte, y su gate es la corrida real de §7.
- No se toca la poda de `adjuntos/` ni la atomicidad de la publicación (`MEJORAS #99`).
- No se cambia el layout que escribe `email_export` (era la salida 3 de `#98`, descartada).

## 3. Decisión y alternativas descartadas

`MEJORAS #98` dejó tres salidas abiertas. Se elige la **1**.

| Salida | Veredicto |
|---|---|
| **1. Enumeración recursiva en el motor** + `eml_origen` como ruta relativa | **Elegida.** Arregla la causa donde está. La ruta relativa de un fichero de nivel superior **es** su nombre, así que nada de lo existente cambia |
| 2. Que el llamante pase el conjunto exacto de carpetas | **No.** `atomize_dir` ya acepta una secuencia de fuentes, pero reparte la responsabilidad entre llamantes (el CLI manual `scripts/atomize_emails.py` seguiría ciego) y **no arregla la llave**: dos `.eml` homónimos en subcarpetas distintas siguen colisionando en `eml_procesados` |
| 3. Que `email_export` no use subcarpetas | **No.** Cambia un layout de intake ya desplegado en casos reales y tira la agrupación adjunto-junto-a-su-mensaje, que tiene valor para el letrado. Es además la más cara |

## 4. Arquitectura

Cuatro piezas. Las dos primeras cierran `#98`; la tercera cierra §1.3; la cuarta retira el andamio
que sobra.

### 4.1. Enumeración recursiva

`iter_avistamientos` pasa de `base.glob("*.eml")` a `base.rglob("*.eml")`, con el mismo `sorted()`
que ya tiene (orden determinista, requisito de la idempotencia).

Se conserva a propósito la **ceguera a `.EML` en mayúsculas**: el nombre lo compone siempre
`email_export.eml_filename`, y el conteo del llamante debe medir lo mismo que el motor (§4.4).

### 4.2. `eml_origen` pasa a ser la ruta relativa a la carpeta fuente

Hoy `eml_origen = eml.name`. Pasa a `eml.relative_to(base).as_posix()` →
`2026-03-04_arras/2026-03-04_arras.eml`.

**Byte-identidad: qué se promete exactamente (rebajado en rev. 2).** Para un `.eml` del nivel
superior, `relative_to(base)` es el propio nombre; y como hoy **no existe ni un `.eml` en
subcarpeta** (§1.2), `sorted(rglob("*.eml"))` devuelve **exactamente la misma lista** que
`sorted(glob("*.eml"))` — mismo orden, mismos avistamientos. De ahí que el frontmatter de los 277
atoms de W-02VND1, y de cualquier caso actual, salga idéntico, y que ningún `MSG-`/`ATT-` se
renumere (`msg_id_for` acuña por `Message-ID` y solo incrementa, `ids.py:37-46`).

Lo que **no** se puede prometer, y la rev. 1 prometía de más: la byte-identidad vale **mientras el
conjunto de avistamientos no cambie**. Si un mismo `Message-ID` llega a existir a la vez arriba y
en subcarpeta, `colapsar` (`dedup.py:29-52`) **siempre añade la procedencia nueva** —y `procedencia`
va en el frontmatter (`render.py:42`)—, y si la copia nueva trae más bytes se adopta como canónica,
con lo que pueden cambiar `eml_origen`, `profundidad`, `ruta_anidacion`, el `sha256` y hasta el
nombre del `.md`.

Cuán alcanzable es ese layout mixto, medido: **el dedup por `Message-ID` del export ignora
`--force`** (`force` solo vacía el caché `_exported_ids.json`, mientras `vistos` se recalcula
siempre desde disco/M9 — `email_export.py:982-1003`), así que un re-export con
`--extraer-adjuntos` **no** crea una segunda copia de un mensaje ya presente. Las vías reales son
una copia manual o un export sin `case_id` sobre un destino que ya tenía copia plana.

**Dos reglas para que ese caso no mute prueba en silencio:**

1. **Desempate determinista, no orden de enumeración.** A igualdad de bytes gana la copia de
   **menor profundidad de ruta** y, en empate, el orden lexicográfico POSIX — nunca «la primera que
   llegó», que con `rglob` depende del layout.
2. **Una copia de menor fidelidad no cambia el canónico.** Solo un `raw` estrictamente mayor puede
   sustituir origen/profundidad/ruta, que es la regla actual; se conserva y se hace explícita.

La `procedencia` **sí** gana una entrada en ese caso, y eso es correcto: es el registro de dónde se
ha visto el mensaje, no una reatribución. Queda declarado como el único camino por el que el
frontmatter de un atom existente cambia.

`as_posix()` es deliberado: el separador debe ser estable entre Windows y cualquier otra máquina,
porque este valor se persiste en `_registro.json` y en el frontmatter.

Alcanza a los tres consumidores del valor, sin cambios en ellos:
`dedup.colapsar` (procedencia), `render.render_md` (frontmatter, `render.py:39`) y
`Registro.marcar_procesado` (`eml_procesados`).

**Limpieza pequeña incluida:** `_ruta_de(raw, eml_origen)` recibe un segundo parámetro que **no
usa** (verificado). Se retira: es privado, tiene un solo llamante, y un parámetro que miente es
peor que uno que falta.

### 4.3. Foto incompleta: híbrido según si el fallo es transitorio o permanente

La rev. 1 solo miraba fallos de **lectura** y solo apagaba la poda. La revisión demostró que hay
más caminos por los que el conjunto esperado sale incompleto y, por tanto, la poda borra fichas
cuyo mensaje no ha desaparecido:

- **lectura** de un `.eml` (`extract.py:54-57`, `except OSError: continue`) — y también el fallo al
  **enumerar un directorio**, que `rglob` puede silenciar;
- **construcción** de un mensaje de Capa A (`pipeline.py:104-109` captura y sigue);
- **reconstrucción** de Capa B de un portador (`pipeline.py:183-188`, ídem).

Los tres dejan mensajes fuera de `esperados`; los tres son la misma familia. Pero **no tienen la
misma naturaleza**, y de ahí la regla (decisión de Nikolai, 2026-07-28):

| Clase de fallo | Naturaleza | Qué hace el motor |
|---|---|---|
| **Lectura / enumeración** | **Transitorio.** Sobre `G:` (Drive Stream con caché) un fichero presente puede no estar hidratado; re-correr suele resolverlo | **Fail-closed: no publica nada.** Ni `mensajes/`, ni agregados, ni `_revision/`, ni vistas, ni `reg.save()`. La última publicación completa queda **intacta** |
| **Construcción A / Layer B** | **Permanente.** Un `.eml` corrupto no se arregla re-corriendo | **Publica lo bueno pero NO poda.** Así no se borra la ficha del que no se pudo construir, y un solo correo roto no bloquea el caso para siempre |

**Por qué no fail-closed en los dos casos** (que es lo que pedía el revisor): un `.eml`
permanentemente corrupto dejaría el caso **sin poder atomizarse nunca más**, hasta que alguien
retirase el fichero a mano. El precio del híbrido es que en la rama permanente el árbol puede
quedar mixto (fichas rancias en `mensajes/` frente a agregados reescritos sin ellas); se declara en
el evento y en una nota, en vez de fingir que no pasa.

**Cómo se implementa, sin necesidad de la publicación atómica de `#99`:** el pipeline ya construye
`mensajes` **en memoria** antes de escribir nada (`pipeline.py:93-116`). La decisión se toma ahí,
antes de la primera escritura — no es un rollback, es no empezar.

**Contadores tipados en `AtomizeReport`** (el revisor tenía razón en que `eml_leidos` no tenía
fuente de verdad: `report.mensajes` no sirve, porque el dedup y los anidados rompen la igualdad
«ficheros leídos = atoms»):

```python
eml_enumerados: int = 0      # .eml que la enumeración produjo
eml_leidos: int = 0          # de esos, los que se abrieron sin error
fallos_lectura: list[str] = []   # ruta: motivo (incluye fallos de enumeración de directorio)
```

`errores` sigue siendo el cajón de las demás clases (construcción, Layer B, `vistas.yaml`), así que
la causa queda **mecánicamente distinguible**: `fallos_lectura` no vacío ⇒ rama transitoria.

**Notas y evento.** En la rama transitoria, `publicado: false` en el payload y nota a stderr:
```
ATOMIZACIÓN NO PUBLICADA: N .eml no se pudieron leer (Drive sin hidratar?).
El árbol anterior queda intacto. Re-lanza cuando estén disponibles.
```
En la rama permanente, `poda_omitida: true` y nota:
```
poda de mensajes/ OMITIDA: N mensajes no se pudieron construir; el árbol
conserva fichas cuyo mensaje no se ha reconstruido en esta corrida.
```
Las `notas` las escupe el cableado a stderr con prefijo `NOTA:` **antes** del OCR, así que el
operador lo ve a tiempo para abortar.

**Por qué esto vive en el motor y no en el cableado:** el motor es el único que sabe qué ficheros
abrió y qué mensajes construyó de verdad. El cableado solo puede comparar números de disco, que es
lo que hacía la guarda de ayer y lo que no cazaba ninguno de estos tres caminos.

### 4.4. Se retira el andamio de la discrepancia, y el conteo se simplifica

Con la enumeración recursiva, `n_rec > n_top` **no puede darse**: el motor ve todo lo que hay en
disco. Por tanto:

- `contar_eml(fuentes)` pasa a devolver **un solo `int`** (recursivo, el mismo criterio del motor),
  no una tupla. Sigue siendo necesario para el no-op («¿hay correo?»).
- Desaparecen del CLI el banner `_AVISO_EML_INVISIBLE`, la guarda
  `if n_rec > n_top and out.exists()` y la rama `status: "noop"`-por-discrepancia.
- El payload del evento cambia sus dos claves de conteo, y con provecho: `eml_en_disco` (lo que la
  enumeración produjo) y `eml_leidos` (lo que el motor abrió), más `publicado` y `poda_omitida`
  (§4.3). Que los dos conteos difieran es la huella de §1.3, auditable **desde el log solo**.
  Sustituyen a `eml_nivel_superior`/`eml_totales`, que medían una discrepancia que ya no existe.
- **Versionado del payload (rev. 2, a raíz de la revisión).** Sustituir claves en un log
  append-only deja dos formas bajo el mismo tipo de evento: una auditoría futura que lea
  `eml_en_disco` no la encontrará en las entradas de ayer. Se añade por eso `details_schema: 2`.
  **No** se conservan las claves viejas: emitir `eml_nivel_superior` cuando el concepto ha
  desaparecido es publicar un dato sin significado. Sin `details_schema`, forma 1.
  Ningún consumidor productivo se rompe — verificado: `core/abrir_caso.py:159-166` y
  `.claude/skills/intake-expediente/scripts/traza.py:50-69` recorren todos los eventos y solo miran
  `details.files`, que este evento no lleva; `read_events` no valida schema (`intake_log.py:204-230`).

### 4.5. La llave del registro lleva la fuente; el frontmatter no

La ruta relativa **a cada carpeta fuente** no basta como llave: `2026-07-20_email_01/sub/a.eml` y
`03_Email/sub/a.eml` producen los dos la cadena `sub/a.eml`, y `marcar_procesado` colapsa por
igualdad (`ids.py:77-91`), así que el objetivo 2 del §2 no se cumpliría. Lo encontró la revisión.

Se separan los dos usos, que hasta ahora eran el mismo valor:

- **`eml_origen`** (probatorio, va al frontmatter): ruta relativa **a su carpeta fuente**. Para el
  nivel superior sigue siendo el nombre pelado → la byte-identidad de §4.2 se mantiene.
- **`eml_key`** (llave del registro, no va al frontmatter): `f"{fuente.name}/{eml_origen}"`. Los
  nombres de las fuentes son únicos por construcción (lotes `AAAA-MM-DD_email_NN` + `03_Email`), así
  que la llave lo es. Es lo que consume `marcar_procesado`.

**Corrección (revisión final de rama):** la afirmación original de este párrafo — «la primera
corrida tras el cambio reescribe la lista con llaves nuevas» — era **falsa**. `marcar_procesado`
solo apilaba (dedup por igualdad exacta de string) y `save()` nunca purgaba: sobre un caso real
(`_registro.json` con 277 llaves en la forma vieja, solo el nombre de fichero) la primera corrida
tras este cambio habría **añadido** 277 llaves nuevas en forma `<fuente>/<eml_origen>` y
**conservado** las 277 viejas, para siempre, en dos formas mutuamente incompatibles. Ninguna de las
tres revisiones anteriores de esta spec lo capturó porque los tests partían todos de un
`_registro.json` vacío.

**Migración real (implementada):** `eml_procesados` es estado DERIVADO, no identidad congelada
(todo mensaje publicado pasa por `marcar_procesado` en cada corrida), así que se puede
reconstruir. `Registro.resolver_procesados(*, foto_completa)`, invocada por `atomize_dir` con la
MISMA condición que gobierna la poda de `mensajes/` (`report.publicado and not report.errores`):
con la foto completa la lista se reconstruye desde cero — purga la forma vieja y refleja retiradas
genuinas —; con la foto parcial (algún mensaje no se pudo construir/reconstruir esta corrida) se
sigue apilando sobre lo que había, porque el rebuild dropearía la llave de un `.eml` cuyo mensaje
no llegó a marcarse hoy aunque el fichero sigue existiendo. Lo que `MEJORAS #86` planea leer pasa a
ser fiable en el caso común (foto completa), que era el objetivo.

El no-op sobrevive intacto: `n == 0` y sin árbol previo → no se llama al motor (evitar el `mkdir`
incondicional de `mensajes/`/`adjuntos/`); con árbol previo sí se llama, para que la retirada
genuina de correo se refleje.

## 5. Lo que este diseño retira del PR anterior, y por qué es seguro

El PR #151 puso una protección **indirecta**: «si los conteos de disco no cuadran, no toques el
árbol». Era la única disponible sin tocar el motor. Con `#98` cerrado, su premisa desaparece y
quedaría (a) código que no puede dispararse y (b) un banner cuyo texto —«el atomizador NO los
verá»— pasaría a ser **falso**, que es peor que no tener aviso.

La protección **no se pierde: se muda y se vuelve precisa** (§4.3). Cobertura comparada, con los
caminos que añadió la revisión:

| Escenario | Guarda de ayer | Guarda nueva |
|---|---|---|
| `.eml` en subcarpeta (`#98`) | detecta | **no aplica: ya no hay invisibles** |
| `.eml` presente pero ilegible (Drive sin hidratar) | **no detecta** | fail-closed: no publica |
| Fallo al enumerar un directorio | **no detecta** (el `try` solo rodea `read_bytes`) | fail-closed: se cuenta como fallo de lectura |
| Mensaje que falla al construirse / portador de Layer B que falla | **no detecta** | publica sin podar |
| Retirada genuina de correo | reconcilia (correcto) | reconcilia (correcto) |
| `.EML` en mayúsculas | **no detecta** (ambos conteos lo omiten) | **no detecta** (ceguera deliberada y simétrica) |
| Carpeta fuente que `emails_src_dirs_de_caso` no devuelve (lote que no casa `PATRON_LOTE`) | **no detecta** | **no detecta** |

Las dos últimas filas son la corrección de la rev. 1, que afirmaba «el motor ve todo lo que hay en
disco». Lo correcto es: **todos los `*.eml` enumerables dentro de las fuentes declaradas**. Ninguna
de las dos la cubría la guarda vieja tampoco, así que retirarla no pierde cobertura — que es lo que
esta tabla tenía que demostrar.

## 6. Contrato de tests

**Motor — nuevos** (`tests/test_email_atomize_extract.py` y `tests/test_email_atomize_pipeline.py`):

1. **Recursivo:** un lote con 1 `.eml` arriba y 1 en `subcarpeta/` produce **2 atoms**.
2. **`eml_origen` del nivel superior es el nombre pelado** — es la prueba de la byte-identidad de
   todo lo existente.
3. **`eml_origen` de una subcarpeta es la ruta relativa con `/`**, no `\`, y no el nombre pelado.
4. **Colapso:** el mismo mensaje presente arriba **y** en subcarpeta produce **un solo atom** (por
   `Message-ID`), con las dos procedencias.
5. **Fallo de lectura declarado:** un `.eml` que lanza `OSError` al leerse deja entrada en
   `fallos_lectura` (no en `errores`) y **no** aborta la corrida con traceback.
6. **Fallo de lectura NO PUBLICA (fail-closed):** árbol previo con 2 fichas + agregados; una fuente
   pasa a ilegible → tras la corrida **las 2 fichas siguen**, `corpus.jsonl` y los índices
   **no se han reescrito** (comparar bytes), `_registro.json` **no se ha tocado**, y el informe trae
   `publicado=False` + la nota. Es el test que demuestra §1.3.
7. **Fallo de construcción SÍ publica pero NO poda:** un `.eml` que hace fallar
   `_construir_mensaje` → los demás atoms se escriben, la ficha del que falló **sobrevive**,
   `poda_omitida=True`. Cubre el camino que la rev. 1 dejaba fuera.
8. **Sin fallos sí poda:** el test de transición a cero existente sigue verde, sin tocarlo (poda
   legítima).
9. **Idempotencia:** dos corridas seguidas sobre un lote con subcarpetas → 0 cambios, 0
   renumeraciones.
10. **`eml_leidos` ≠ `mensajes`:** un lote donde el dedup colapsa dos avistamientos del mismo
    `Message-ID` → `eml_leidos` cuenta ficheros y `mensajes` cuenta atoms, y **no coinciden**. Mata
    la implementación perezosa `eml_leidos = report.mensajes`.
11. **Llave del registro sin colisión:** dos fuentes distintas con el mismo relpath interno
    (`sub/a.eml` en un lote y en `03_Email`, mensajes DISTINTOS) → `eml_procesados` tiene **dos**
    entradas y los dos atoms existen.
12. **Transición top-only → mixta, copia igual y copia mayor:** un atom existente cuyo mensaje
    aparece además en subcarpeta con (a) bytes idénticos → el canónico NO cambia de `eml_origen`
    (desempate por menor profundidad), y (b) más bytes → sí cambia, y el test lo fija como
    comportamiento declarado, no accidental. Es el death test del hallazgo 1 de la revisión.
13. **Todos los `.eml` en subcarpetas** (ninguno arriba): el motor los atomiza todos. Recupera la
    cobertura del caso que se pierde al retirar los tres tests de la guarda.

**Conteo — a modificar** (`tests/test_email_atomize_pipeline.py`): los dos tests de `contar_eml`
asertan hoy una **tupla** y pasan a un `int` —
`test_contar_eml_distingue_nivel_superior_de_recursivo` deja de tener sentido (ya no hay dos
criterios) y se convierte en «cuenta también las subcarpetas»; `test_contar_eml_suma_fuentes_y_tolera_inexistentes`
mantiene su propósito con un solo número.

**Cableado — a modificar** (`tests/test_sala_maquina_cableado_atomize.py`, 19 tests hoy):

**Nota de la revisión:** el test 2 **ya existe casi igual** en
`tests/test_email_atomize_extract.py:17-27` — se amplía ahí en vez de duplicarlo. Y el test de
`colapsar` vigente (`tests/test_email_atomize_dedup.py:6-19`) aserta `raw` y el conjunto de
procedencias pero **no** `eml_origen` ni `profundidad`: los tests 12 y 4 cubren ese hueco.

- **Se retiran 5**, cuya premisa desaparece: `test_noop_con_discrepancia_emite_evento_noop`,
  `test_arbol_previo_con_discrepancia_total_no_llama_al_motor`,
  `test_arbol_previo_con_discrepancia_parcial_no_llama_al_motor`,
  `test_aviso_cuando_hay_eml_en_subcarpetas`, `test_sin_discrepancia_no_hay_aviso`.
- **Se invierte 1:** `test_motor_real_solo_ve_el_nivel_superior` pasa a
  `test_motor_real_ve_las_subcarpetas` y asserta lo contrario (2 atoms, no 1). Es el test que
  fija el arreglo contra el motor real.
- **Se simplifican 2:** `test_plan_no_atomiza_pero_informa_y_avisa` pierde la aserción del banner
  (mantiene la línea informativa y que no escribe en `01_Procesado/Emails`) y **su recuento pasa de
  2 a 3 correos**, porque su fixture tiene 2 arriba y 1 en subcarpeta y ahora se cuentan los tres;
  `test_payload_atado_a_los_campos_reales_del_report` pasa a las claves nuevas
  `eml_en_disco`/`eml_leidos`.
- **Se añade 1:** payload de la rama transitoria — `status: "fallo"`, `publicado: false` y
  `eml_leidos < eml_en_disco` cuando el motor reporta un fallo de lectura. **Corrección de
  coherencia (rev. 2.1):** esta línea decía `"parcial"`, heredado de la rev. 1, donde el fallo de
  lectura publicaba sin podar. Con el fail-closed del §4.3 no se publica nada, y `"parcial"`
  afirmaría una publicación parcial que no ha ocurrido; `"fallo"` es lo que el §4.4 y el plan
  implementan. `"parcial"` queda para la rama permanente (publica con `poda_omitida`).
- El resto (orden, no-op, reconciliación, fallo blando, resolución del caso una sola vez, `plan`,
  `reforzar`) queda **intacto**.

**No se cubre en tests:** la exclusión mutua entre corridas concurrentes (sigue en `#99`) y el
comportamiento real de Drive ante un fichero no hidratado (se simula el `OSError`; el escenario
real se observa, no se provoca).

## 7. Verificación en vivo

El punto débil, y explícito: **no hay datos reales con el layout del bug** (§1.2), y en este motor
ya hubo tres iteraciones en que los fixtures sintéticos pasaron sobre defectos que la corrida real
destapó.

Plan aprobado por Nikolai:

1. **Export real de control.** Re-exportar una etiqueta Gmail **pequeña** con extracción de
   adjuntos a un destino de prueba **fuera de todo expediente** (scratch local, no `G:`).
   Produce el layout auténtico con correos auténticos.
   **Comprobado al escribir esta spec: el CLI `scripts/export_label_emails.py` NO sirve para
   esto** — exige `--ref` y deriva el destino con `email_dest_dir(case_id)`, así que siempre
   escribe dentro del expediente. La vía es llamar al motor directamente:
   `core.email_export.export_label(account, label, <scratch>, case_id=None, extract_attachments=True)`.
   El `case_id=None` es lo que mantiene la prueba fuera del log forense: sin él, `export_label`
   emite `upload_email` y registra hashes en el manifiesto de un caso. Requiere el token de Gmail,
   luego es ejecución **local** (el `.eml` nunca sale del PC).
2. **Atomizar ese destino** con `scripts/atomize_emails.py --src/--out` y comprobar: los mensajes
   con adjunto **aparecen**; su `eml_origen` es la ruta relativa; el remitente de cada uno sale
   **literal** del `.eml` (prime directive: cero misatribución); y una segunda corrida no cambia
   nada.
   **Añadido en la revisión final de rama:** inventariar si algún adjunto extraído es a su vez un
   `.eml` (un mensaje guardado a disco y re-adjuntado como fichero, NO `message/rfc822` —
   `split_eml` sí lo excluye correctamente; `core/email_export.py:1124` lo escribe suelto igual que
   cualquier otro adjunto). Con `--extraer-adjuntos`, ese fichero se convierte en un avistamiento de
   primer nivel (`profundidad 0`, `ruta_anidacion` vacía) indistinguible en `mensajes/` de un correo
   exportado directamente del caso, mientras sigue existiendo como `ATT-` en `adjuntos/`. No hay
   misatribución (sus cabeceras salen de sus propios bytes), pero sí degradación de procedencia en
   un corpus probatorio. Decidir, antes de encender la casilla 3: si esos ficheros se excluyen de la
   enumeración o se marcan de algún modo.
3. **No-regresión sobre el caso nuclear, con autorización expresa en el momento:** re-correr
   W-02VND1 (277 correos, sin subcarpetas) y demostrar Capa A **byte-idéntica** y **0 IDs
   renumerados**, con el patrón de `scripts/_verify_live_it3.py` (snapshot de hashes antes/después).
   Escribe en `G:`; no se ejecuta sin el sí explícito.
   **Alcance de lo que esta corrida demuestra, acotado en rev. 2:** solo «input top-only inalterado
   ⇒ salida idéntica». **No** demuestra la transición top→mixto, ni la copia mayor, ni la colisión
   entre fuentes, ni el fallo con un Layer B superado, ni el error de enumeración de directorio —
   esos cinco viven en los death tests 6, 7, 10, 11 y 12 del §6, y ahí se quedan porque provocarlos
   en vivo exigiría corromper un expediente real.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Que `rglob` recoja `.eml` que no son correo del caso | Medido: el único productor de `.eml` en subcarpeta es `--extraer-adjuntos`; `_enlaces/` no aporta correo (§1.2). Si algún día apareciera otra fuente, el detector de contaminación cruzada por W-code ya corre en toda corrida |
| Que el cambio de `eml_origen` rompa la byte-identidad | Estructuralmente imposible para lo existente (ruta relativa = nombre en el nivel superior) + test 2 + paso 3 de §7 |
| Que saltarse la poda acumule fichas huérfanas | Declarado en la nota y en el `status: "parcial"`; es el intercambio elegido frente a borrar prueba. Cierre completo cuando `#99` haga la publicación atómica |
| Que retirar el andamio de ayer deje un hueco | §5 compara cobertura escenario por escenario: la nueva cubre estrictamente más |
| Que el árbol de un caso ya atomizado gane atoms de golpe al re-correr | Es el arreglo funcionando: los mensajes con adjunto que estaban perdidos aparecen. Los IDs nuevos van al final; nada se renumera |

## 9. Documentación a actualizar

- `docs/MEJORAS_FUTURAS.md`: **`#98` se cierra** (incluidos sus dos motivos para bloquear la
  casilla 3) y se anota el segundo defecto de §1.3 como parte del cierre. `#99` conserva lo suyo.
- `PLAN.md`: bloque `[SIGUIENTE-CABLEADO-CORREO]` — la casilla 3 pasa de ⛔ a **decidible**, con
  el gate de la corrida de §7.
- `.claude/skills/organizar-sala-maquina/SKILL.md`: el gotcha que hoy dice que `apply` avisa de los
  `.eml` invisibles pasa a describir el comportamiento nuevo (los ve; y si falla al leer alguno, lo
  declara y no poda).
- `docs/ARQUITECTURA.md`: la fila de `core/email_atomize/` gana el contrato nuevo
  (`eml_origen` = ruta relativa; `eml_procesados` con rutas).
- `core/intake_log.py`: el comentario de schema de `atomizado_email` (claves de conteo nuevas).

## 10. Lo que sigue abierto (con dueño)

- **`MEJORAS #99`** — poda de `adjuntos/`, publicación atómica y exclusión mutua. La nota de poda
  omitida de §4.3b es un parche honesto, no el cierre.
- **`MEJORAS #87`** — el contenido/OCR de los adjuntos sigue fuera de la sala de máquina.
- **`MEJORAS #86`** — el consumo del árbol atomizado por la sala de lectura; se beneficia de que
  `eml_procesados` deje de ser ambiguo (su requisito de entrada 1).
- **Casilla 3** del bloque del PLAN: decidible tras §7, en su propio PR.

## 11. Adjudicación de la revisión adversarial (Codex, 2026-07-29) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-07-28-email-atomize-enumeracion-recursiva-design.md` rev. 1, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** no capturado — llegó por chat, antes del contrato de actas
- **Hallazgos:** 6 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento

Los 6 son los bloqueantes de la tabla. De las dos divergencias de abajo, la segunda (claves del
evento: versionar en vez de duplicar) es de **remedio** y no resta del recuento, contrato §5. **La
primera no lo es:** «`_enlaces/` no puede contener `.eml`» refuta por medición una premisa fáctica de
la tabla del revisor. No suma a `refutados` porque no era uno de los seis bloqueantes, sino una
afirmación de apoyo — pero decir que «las dos son de remedio» era falso y dejaba al autor más
deferente de lo que fue.

**Y el párrafo «Lo que la revisión dejó como UNVERIFIED»** de más abajo es un hueco de cobertura del
revisor, no un hallazgo: por eso la ficha dice `0 sin verificar` y el hueco consta aquí.

`agy` no pudo correr (cupo de Gemini agotado), así que la revisión la hizo Codex en solo lectura.
**Los 6 bloqueantes se aceptan.** Dónde queda cada uno:

| # | Bloqueante | Resuelto en | Matiz que verifiqué yo |
|---|---|---|---|
| 1 | La Capa A puede mutar por selección canónica y por `procedencia` | §4.2 | Real, pero **no afecta a nada existente**: sin subcarpetas `sorted(rglob)` da la misma lista que `sorted(glob)`. Y el layout mixto **no** se alcanza por re-export: el dedup por `Message-ID` ignora `--force` (`email_export.py:982-1003`) |
| 2 | Un fallo publica un árbol mixto; la guarda no cubre construcción ni Layer B | §4.3 | Confirmado leyendo `pipeline.py:104-109` y `:183-188`. **No** se adopta el fail-closed universal que pedía: un `.eml` permanentemente corrupto bloquearía el caso para siempre → híbrido por naturaleza del fallo (decisión de Nikolai) |
| 3 | `eml_leidos` sin fuente de verdad tipada | §4.3 | Correcto: `report.mensajes` no vale porque el dedup rompe la igualdad. Contadores tipados + test 10 |
| 4 | `eml_procesados` sigue colisionando entre fuentes | §4.5 | Correcto y el objetivo 2 del §2 no se cumplía. `eml_origen` (frontmatter) y `eml_key` (registro) se separan |
| 5 | Faltan death tests | §6 (tests 5-13) | Correcto, incluida la cobertura que se pierde al retirar los tres tests de la guarda |
| 6 | Fallos al enumerar un directorio fuera de la guarda | §4.3 y tabla del §5 | Correcto; se cuentan como fallo de lectura (rama transitoria) |

**Dos puntos donde no seguí al revisor:**

- **`_enlaces/` no puede contener `.eml`.** Su tabla lo daba por posible; está descartado por
  medición: los `.eml` rescatados de un enlace se depositan **a primer nivel**
  (`_deposita_mensaje_rescatado`, `email_export.py:536-556`).
- **Claves del evento: versionar, no duplicar.** Proponía conservar `eml_nivel_superior`/`eml_totales`
  por compatibilidad. Emitir una clave cuyo concepto ha desaparecido es publicar un dato sin
  significado; se resuelve igual con `details_schema: 2` (§4.4).

**Lo que la revisión dejó como UNVERIFIED y sigue así:** la semántica de `Path.rglob` ante enlaces
simbólicos de directorio, porque el repo solo fija Python `>=3.11` y no una versión concreta. No se
apoya ninguna decisión en ese comportamiento: los fallos de enumeración caen en la rama transitoria
de §4.3 sea cual sea su causa.
