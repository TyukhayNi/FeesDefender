# Diseño — Enumeración recursiva del atomizador de correo (`MEJORAS #98`) y poda que no borra a ciegas

> **Estado:** rev. 1 (2026-07-28), aprobada por Nikolai en chat antes de escribirse.
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

**Por qué la Capa A no cambia un byte:** para un `.eml` del nivel superior, `relative_to(base)` es
el propio nombre. Como hoy **no existe ni un `.eml` en subcarpeta** (§1.2), el frontmatter
`eml_origen:` de los 277 atoms de W-02VND1 —y de cualquier otro caso— sale idéntico. Los mensajes
antes invisibles entran como atoms nuevos, con IDs **al final** del contador: `msg_id_for` acuña
por `Message-ID` y solo incrementa (`ids.py:37-46`), así que no hay renumeración.

`as_posix()` es deliberado: el separador debe ser estable entre Windows y cualquier otra máquina,
porque este valor se persiste en `_registro.json` y en el frontmatter.

Alcanza a los tres consumidores del valor, sin cambios en ellos:
`dedup.colapsar` (procedencia), `render.render_md` (frontmatter, `render.py:39`) y
`Registro.marcar_procesado` (`eml_procesados`).

**Limpieza pequeña incluida:** `_ruta_de(raw, eml_origen)` recibe un segundo parámetro que **no
usa** (verificado). Se retira: es privado, tiene un solo llamante, y un parámetro que miente es
peor que uno que falta.

### 4.3. Fallo de lectura: declarado, y sin poda a ciegas

Dos cambios acoplados, porque uno sin el otro no sirve:

**(a) Declararlo.** `iter_avistamientos(base, *, fallos: list[str] | None = None)`: en el
`except OSError as exc`, en vez de `continue` a secas, si `fallos is not None` se le añade
`f"{ruta_relativa}: {exc}"`. `atomize_dir` pasa una lista, y sus entradas van a
`report.errores` con prefijo `lectura fallida:`. Efecto inmediato y gratis: el evento forense
`atomizado_email` sale **`status: "parcial"`**, porque el cableado ya deriva `parcial` de
`report.errores` no vacío.

**(b) No podar.** La poda de `mensajes/*.md` (`pipeline.py:121-124`) se ejecuta **solo si no hubo
fallos de lectura**. Si hubo, se salta y se añade una **nota** al informe:

```
poda de mensajes/ OMITIDA: N .eml no se pudieron leer; el árbol conserva
fichas cuyo origen no se ha visto en esta corrida.
```

Las `notas` sí las escupe el cableado a stderr con prefijo `NOTA:` antes del OCR, así que el
operador lo ve a tiempo. El coste asumido es un árbol que puede conservar fichas huérfanas —
preferible a borrar prueba derivada por una foto incompleta, y coherente con que `adjuntos/` ya no
se poda (`#99`).

**Por qué esto vive en el motor y no en el cableado:** el motor es el único que sabe qué ficheros
abrió de verdad. El cableado solo puede comparar números de disco, que es lo que hizo ayer y lo que
no cazaba este caso.

### 4.4. Se retira el andamio de la discrepancia, y el conteo se simplifica

Con la enumeración recursiva, `n_rec > n_top` **no puede darse**: el motor ve todo lo que hay en
disco. Por tanto:

- `contar_eml(fuentes)` pasa a devolver **un solo `int`** (recursivo, el mismo criterio del motor),
  no una tupla. Sigue siendo necesario para el no-op («¿hay correo?»).
- Desaparecen del CLI el banner `_AVISO_EML_INVISIBLE`, la guarda
  `if n_rec > n_top and out.exists()` y la rama `status: "noop"`-por-discrepancia.
- El payload del evento cambia sus dos claves de conteo, y con provecho:
  `eml_en_disco` (lo que hay) y `eml_leidos` (lo que el motor abrió). Que difieran es la huella
  de §1.3, auditable **desde el log solo**. Sustituyen a `eml_nivel_superior`/`eml_totales`, que
  medían una discrepancia que ya no existe. El log es append-only: las entradas viejas conservan
  sus claves, y no hay consumidor productivo que las lea (verificado en el PR anterior:
  `core/abrir_caso.py:159-166` y `.claude/skills/intake-expediente/scripts/traza.py:50-69`
  recorren todos los eventos y solo miran `details.files`, que este evento no lleva).

El no-op sobrevive intacto: `n == 0` y sin árbol previo → no se llama al motor (evitar el `mkdir`
incondicional de `mensajes/`/`adjuntos/`); con árbol previo sí se llama, para que la retirada
genuina de correo se refleje.

## 5. Lo que este diseño retira del PR anterior, y por qué es seguro

El PR #151 puso una protección **indirecta**: «si los conteos de disco no cuadran, no toques el
árbol». Era la única disponible sin tocar el motor. Con `#98` cerrado, su premisa desaparece y
quedaría (a) código que no puede dispararse y (b) un banner cuyo texto —«el atomizador NO los
verá»— pasaría a ser **falso**, que es peor que no tener aviso.

La protección **no se pierde: se muda y se vuelve precisa** (§4.3b). Cobertura comparada:

| Escenario | Guarda de ayer | Guarda nueva |
|---|---|---|
| `.eml` en subcarpeta (`#98`) | detecta | **no aplica: ya no hay invisibles** |
| `.eml` presente pero ilegible (Drive sin hidratar) | **no detecta** | detecta y no poda |
| Retirada genuina de correo | reconcilia (correcto) | reconcilia (correcto) |

## 6. Contrato de tests

**Motor — nuevos** (`tests/test_email_atomize_extract.py` y `tests/test_email_atomize_pipeline.py`):

1. **Recursivo:** un lote con 1 `.eml` arriba y 1 en `subcarpeta/` produce **2 atoms**.
2. **`eml_origen` del nivel superior es el nombre pelado** — es la prueba de la byte-identidad de
   todo lo existente.
3. **`eml_origen` de una subcarpeta es la ruta relativa con `/`**, no `\`, y no el nombre pelado.
4. **Colapso:** el mismo mensaje presente arriba **y** en subcarpeta produce **un solo atom** (por
   `Message-ID`), con las dos procedencias.
5. **Fallo de lectura declarado:** un `.eml` ilegible (permiso denegado o simulando `OSError` en la
   lectura) deja una entrada `lectura fallida:` en `report.errores` y **no** aborta la corrida.
6. **Fallo de lectura NO poda:** árbol previo con 2 fichas, una fuente pasa a ilegible → tras la
   corrida **las 2 fichas siguen ahí** y el informe trae la nota de poda omitida. Es el test que
   demuestra §1.3.
7. **Sin fallos sí poda:** el test de transición a cero existente sigue verde, sin tocarlo (poda
   legítima).
8. **Idempotencia:** dos corridas seguidas sobre un lote con subcarpetas → 0 cambios, 0
   renumeraciones.

**Conteo — a modificar** (`tests/test_email_atomize_pipeline.py`): los dos tests de `contar_eml`
asertan hoy una **tupla** y pasan a un `int` —
`test_contar_eml_distingue_nivel_superior_de_recursivo` deja de tener sentido (ya no hay dos
criterios) y se convierte en «cuenta también las subcarpetas»; `test_contar_eml_suma_fuentes_y_tolera_inexistentes`
mantiene su propósito con un solo número.

**Cableado — a modificar** (`tests/test_sala_maquina_cableado_atomize.py`, 19 tests hoy):

- **Se retiran 5**, cuya premisa desaparece: `test_noop_con_discrepancia_emite_evento_noop`,
  `test_arbol_previo_con_discrepancia_total_no_llama_al_motor`,
  `test_arbol_previo_con_discrepancia_parcial_no_llama_al_motor`,
  `test_aviso_cuando_hay_eml_en_subcarpetas`, `test_sin_discrepancia_no_hay_aviso`.
- **Se invierte 1:** `test_motor_real_solo_ve_el_nivel_superior` pasa a
  `test_motor_real_ve_las_subcarpetas` y asserta lo contrario (2 atoms, no 1). Es el test que
  fija el arreglo contra el motor real.
- **Se simplifican 2:** `test_plan_no_atomiza_pero_informa_y_avisa` pierde la aserción del banner
  (mantiene la línea informativa y que no escribe en `01_Procesado/Emails`);
  `test_payload_atado_a_los_campos_reales_del_report` pasa a las claves nuevas
  `eml_en_disco`/`eml_leidos`.
- **Se añade 1:** payload con `status: "parcial"` y `eml_leidos < eml_en_disco` cuando el motor
  reporta un fallo de lectura.
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
3. **No-regresión sobre el caso nuclear, con autorización expresa en el momento:** re-correr
   W-02VND1 (277 correos, sin subcarpetas) y demostrar Capa A **byte-idéntica** y **0 IDs
   renumerados**, con el patrón de `scripts/_verify_live_it3.py` (snapshot de hashes antes/después).
   Escribe en `G:`; no se ejecuta sin el sí explícito.

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
