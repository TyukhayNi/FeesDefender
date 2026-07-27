# Diseño — Cableado de la atomización de correo en la sala de máquina

> **Estado:** rev. 2 (2026-07-27), tras revisión adversarial de Codex + pasada propia.
> Decisiones de alcance de la rev. 2 aprobadas por Nikolai.
> **Alcance:** **cableado, no motor.** Quién llama a quién en el pipeline de correo.
> **Origen:** `PLAN.md` → `[SIGUIENTE-CABLEADO-CORREO]` (resto de `MEJORAS #68`), promovido por
> decisión explícita de Nikolai el 2026-07-27.
> **Fuera de alcance (otros ítems, no este PR):** saneamiento del motor (`MEJORAS #99`), trampa de
> `--extraer-adjuntos` (`MEJORAS #98`), OCR/extracción de adjuntos (`MEJORAS #87`), consumo por la
> sala de lectura (`MEJORAS #86`), `--extraer-adjuntos` a default `True` (casilla 3 del bloque —
> **bloqueada por `#98`**).
> **Revisión adversarial:** `2026-07-27-cableado-atomize-sala-maquina-adversarial-review.md`
> (hallazgos, adjudicación y evidencia). `agy` no pudo correr: cupo de Gemini agotado.
> **Disciplina:** brainstorming → spec → plan → TDD → revisión adversarial.

## 1. Contexto

Las piezas del pipeline de correo están construidas y ninguna llama a la siguiente. El motor
`core/email_atomize/` (Capas A + B + capa de caso, completo en `main`) solo lo invocan hoy el CLI
manual `scripts/atomize_emails.py` y `scripts/audit_correos_no_separados.py`. `core/sala_maquina.py`
no lo menciona; `scripts/abrir_caso.py` tampoco. Si el operador no se acuerda de lanzarlo a mano,
todo lo que cuelga de él se comporta como si no existiera.

### 1.1. Corrección de un supuesto heredado

El bloque del `PLAN.md` justifica el orden diciendo que hay que **atomizar antes de la sala de
máquina «o el OCR queda incompleto»**. Verificado contra el código, eso **no es cierto para el
atomizador**:

- `core/sala_maquina.py::inventariar` recorre **solo** `<caso>/00_Input/` (`sala_maquina.py:645`
  tras fusionar el PR #147; era `:551` antes de la escalera de OCR).
- Ninguna escritura de `core/email_atomize/` sale de su `out_dir`
  (`<caso>/01_Procesado/Emails`, `pipeline.py:297`), árbol que la sala de máquina no mira.
- El `.eml` sí entra al inventario (ext «nativo»), pero `core.extractor._try_email`
  (`extractor.py:173-194`) extrae `From/To/Date/Subject` + `msg.get_body(...)` y **no recorre
  adjuntos**: no hay `walk()` ni `iter_attachments()`.

Es lo que ya dejó anotado `MEJORAS #55`. La frase del PLAN es cierta para el `--extraer-adjuntos`
del intake, que sí deposita binarios en `00_Input`, **no** para el atomizador.

**Matiz aceptado de la revisión:** hay una mejora *indirecta*. Mostrar la contaminación cruzada
antes del OCR permite al operador abortar, limpiar `00_Input` y reintentar — lo que mejora la
corrección del corpus OCR. No hay gate ni exclusión automática, así que no es cobertura: es
oportunidad de intervención.

### 1.2. Hallazgo de la revisión: `--extraer-adjuntos` deja ciego al atomizador

**Bug latente en `main`, descubierto por la revisión de Codex y verificado.** Dos hechos que juntos
abren un agujero silencioso:

- `iter_avistamientos` enumera con `base.glob("*.eml")` — **nivel superior, no recursivo**
  (`extract.py:53`).
- `_escribe_mensaje`, cuando `extract_attachments=True` **y** el mensaje trae adjuntos, escribe el
  `.eml` dentro de una **subcarpeta** (`email_export.py:1123-1132`).

Consecuencia: los mensajes exportados con `--extraer-adjuntos` — **exactamente los que tienen
adjuntos** — son invisibles para el atomizador. Sin error, sin nota: simplemente no aparecen.
Tampoco los mira el detector de contaminación.

Esto **no lo causa este PR** y no se arregla aquí (es motor). Se documenta en `MEJORAS #98` y
**bloquea la casilla 3** del bloque del PLAN: pasar `--extraer-adjuntos` a default `True`
generalizaría la ceguera a todos los casos con adjuntos.

Lo que este PR sí hace es **dejar de ocultarlo**: §4.2.

## 2. Objetivos y no-objetivos

**Objetivos.**

1. Que el orden **intake → atomización → sala de máquina** lo garantice el código, no la memoria
   del operador.
2. Que el resultado de la atomización quede **declarado y auditable** tras cada `apply`: estado
   explícito (`ok` / `parcial` / `fallo` / `noop`) en el log de custodia.
3. Que el **detector de contaminación cruzada por W-code** (`core/email_atomize/contaminacion.py`,
   `20465ef`) corra en toda corrida y su aviso sea visible antes del OCR.
4. Que la discrepancia de enumeración de §1.2 deje de ser silenciosa.

**Rebaja explícita respecto de la rev. 1 (hallazgo H-09 de la revisión).** La rev. 1 prometía que
`01_Procesado/Emails` quedaría *«siempre fresco y consumible sin comprobar nada»*. **Esa promesa no
es entregable sin tocar el motor**, porque el motor no converge cuando se retiran entradas: no poda
`adjuntos/` (§9.2) y no publica de forma atómica (§9.3). Mantener el no-objetivo «no tocar motor» y
la promesa de frescura a la vez era una contradicción interna de la spec. Se elige mantener el
alcance y **rebajar la promesa**: el consumidor **debe** comprobar el estado declarado; no se
garantiza convergencia del árbol hasta `MEJORAS #99`.

**No-objetivos.**

- **El adjunto que llega solo por correo sigue sin llegar al OCR.** Este PR no cambia una línea de
  lo que la sala de máquina inventaría.
- No se toca el motor `core/email_atomize/`: ni su enumeración, ni su poda, ni su publicación.
- No se toca la invariante «`00_Input` es crudo y es la única fuente de la sala de máquina».
- No se encadena nada en `scripts/abrir_caso.py` (opción (i) del PLAN, descartada).

## 3. Decisión: dónde vive el disparo

Se elige **(ii) `organizar-sala-maquina`**. Esta decisión **sobrevivió intacta a las dos revisiones
adversariales**: ningún hallazgo ataca la ubicación, solo el contrato.

| Opción | Veredicto |
|---|---|
| (i) `abrir_caso` lo encadena | **No.** La apertura corre una vez; la sala de máquina se re-lanza. Deja sin cubrir todo caso reprocesado. |
| (ii) `organizar-sala-maquina` antes de su OCR | **Sí.** Donde el orden importa y donde el operador ya está. |
| (iii) fachada `procesar_expediente()` | **No.** Añade una capa sin resolver quién la llama. |

Dentro de (ii), en **`scripts/sala_maquina.py::apply`**, no en el SKILL.md (la prosa es el mecanismo
que falla hoy) ni en `core/sala_maquina.py` (el motor de OCR no debe saber qué es un correo;
encadenar pipelines es orquestación).

## 4. Arquitectura

```
apply(case_id, vision, force)
  ├─ _resolver_caso(case_id)            → (case_id, case_dir) ya resueltos
  ├─ _exigir_vision_cableada()          (solo si --vision)
  ├─ _atomizar_correo(case_id, case_dir)  ← NUEVO
  ├─ _construir_plan(case_dir, force)
  └─ sm.ejecutar(...)
```

### 4.1. Enumeración: un solo criterio, el del motor

**El pre-scan usa el mismo enumerador que el motor**: `glob("*.eml")` por carpeta fuente, **no
`rglob`** (la rev. 1 decía `rglob` «coherente con lo que el motor recorre», y era falso — §1.2).
Alinear el conteo *hacia abajo*, a lo que el motor realmente procesará, es lo que mantiene honesto
el no-op y el evento.

```
fuentes = P.emails_src_dirs(case_id)
n_top = suma de len(glob("*.eml")) por fuente     # lo que el motor VERÁ
n_rec = suma de len(rglob("*.eml")) por fuente    # lo que realmente HAY
```

El predicado vive en **`core/email_atomize/pipeline.py`** (`contar_eml(fuentes) -> (n_top, n_rec)`),
no en el CLI: es lógica, la regla de las 3 capas la quiere en el core, y así `plan` y `apply`
comparten una sola verdad en vez de dos implementaciones que derivan.

### 4.2. Aviso de correo invisible

Si `n_rec > n_top`, se emite un **aviso destacado** — en `apply`, en `plan` y en el payload del
evento:

```
AVISO: N .eml viven en subcarpetas y el atomizador NO los verá (MEJORAS #98).
Causa típica: exportación con --extraer-adjuntos. Son justo los mensajes con adjuntos.
```

Es la respuesta en alcance a §1.2: no arregla la ceguera, pero la vuelve ruidosa. Sin esto, el
cableado *propagaría* el agujero con apariencia de éxito.

### 4.3. Cuándo NO se atomiza (no-op), y cuándo sí aunque no haya correo

El no-op de la rev. 1 (`si no hay .eml, no hacer nada`) dejaba salida rancia: si un caso tuvo
correos atomizados y luego se borran todos —**el remedio exacto que se aplicó en W-02VUDR contra la
contaminación**— el consumidor seguiría viendo los mensajes viejos tras un `apply` con éxito
(hallazgo H-02).

Regla corregida:

| `n_top` | ¿existe `01_Procesado/Emails`? | Acción | `status` |
|---|---|---|---|
| 0 | no | no se llama al motor, no se toca disco | `noop` |
| 0 | **sí** | **se llama al motor** para que pode `mensajes/` | `ok` |
| > 0 | cualquiera | se llama al motor | `ok` / `parcial` |

El caso `n_top == 0` con árbol existente **debe** ejecutarse: es la única vía en alcance para que la
retirada de correos se refleje. Queda documentado que la reconciliación es **parcial** — el motor no
poda `adjuntos/` (§9.2), así que los binarios y sidecars huérfanos permanecen y `adjuntos_contenido`
los seguirá recogiendo (`descubrir.py:13`). Cierre completo: `MEJORAS #99`.

El no-op estricto sigue siendo necesario en la primera fila porque `atomize_dir` hace `mkdir` de
`mensajes/` y `adjuntos/` **incondicionalmente** (`pipeline.py:88-89`): llamarlo a ciegas sembraría
carpetas vacías en todo caso sin correo.

### 4.4. Fallo: blando para el OCR, duro para el registro

Una excepción del motor **no aborta el OCR** (decisión de Nikolai: el OCR no depende de la
atomización y una corrida dura ~1h40). Pero, a diferencia de la rev. 1, **sí se emite evento**, con
`status: "fallo"`.

Fundamento (hallazgos H-05 propio y H-04/H-05 de Codex, convergentes): el motor publica por
escrituras directas sucesivas y guarda `_registro.json` en la **última** línea (`pipeline.py:170`,
`ids.py:93-96`, sin temporal ni `replace`). Una excepción a media escritura deja el árbol mutado y
el registro sin salvar. Como `load_registro` degrada un JSON truncado a registro vacío en silencio
(`ids.py:104-107`) y los IDs se asignan por contador incremental (`ids.py:37-46`), la corrida
siguiente puede **renumerar** `MSG-`/`ATT-`, contra la invariante «re-ejecutar NUNCA renumera». Un
MSG-id ya citado en `_revision/cola.md`, en un `_entregas/` sellado o en una nota del letrado pasaría
a apuntar a otro mensaje.

La fragilidad es del motor y preexistente, pero **hoy es ruidosa**: el CLI manual escupe el traceback
y el operador para. El fallo blando la volvería silenciosa. Emitir el evento de fallo es lo que
impide que este PR degrade una avería visible en una invisible. Además, el aviso sale como **banner
destacado al principio**, no como una línea sepultada bajo una hora de log de OCR.

### 4.5. Evento forense

Alta de `atomizado_email` en `INTAKE_EVENTS` (`intake_log.py:42`). Se emite **siempre que se haya
llamado al motor**, con éxito o con fallo; nunca en el `noop`.

```json
{"event": "atomizado_email",
 "details": {"status": "ok",
             "mensajes": 413, "adjuntos_unicos": 162, "reconstruidos_b": 136,
             "citas_a_revision": 43, "upgrades": 8,
             "eml_nivel_superior": 277, "eml_totales": 277,
             "notas": ["…W-code ajeno…"], "errores": []}}
```

- `status`: `ok` | `parcial` (el motor terminó pero `errores` no está vacío) | `fallo` (excepción).
- `eml_nivel_superior` / `eml_totales`: los dos conteos de §4.1. Que difieran es la huella de §1.2.
- Se emite **antes** de arrancar el OCR: si la corrida larga muere, el rastro ya está en disco.
- **Si `append_event` falla**, se captura y se avisa; nunca se aborta el OCR por un fallo de log.

### 4.6. Resolución del caso: una sola vez

`_atomizar_correo` recibe el `case_dir` **ya resuelto** por `_resolver_caso` y compone las rutas
desde él, en vez de dejar que `atomize_case` vuelva a localizar el caso. `caso_path` es un wrapper
exacto de `path_for` (`config.py:547-550`), así que hoy no hay divergencia; pero resolver tres veces
(conteo, fuentes, salida) es superficie gratuita. Se usa `atomize_dir(fuentes, out)` con las rutas
derivadas de `case_dir`, no `atomize_case(case_id)`.

### 4.7. `plan` y `reforzar` no atomizan

- **`plan`** es preview: no reescribe `01_Procesado/Emails`. Emite la línea informativa con el mismo
  `contar_eml` de §4.1 (`correo: N .eml (se atomizarán en apply)`, callando si `N == 0`) y **el aviso
  de §4.2 si procede**. *(Matiz: `plan` ya escribe el manifiesto de segmentación, un gate editable
  deliberado; no es precedente para atomizar en un preview.)*
- **`reforzar`** re-procesa dudosos ya conocidos de la cobertura. La atomización no le aporta nada.

## 5. Alternativas descartadas

**Ampliar el alcance y arreglar el motor en este PR** (enumeración recursiva + poda de adjuntos +
publicación atómica). Cumpliría la promesa original de frescura, pero deja de ser cableado, toca
código con IDs congelados verificados en vivo sobre W-02VND1, y multiplica riesgo y tamaño de
revisión. Descartado por Nikolai: va a `MEJORAS #99`.

**Parar el cableado y sanear el motor primero.** Más limpio conceptualmente, pero deja el orden
dependiendo de la memoria del operador varias sesiones más y el detector de contaminación sin correr
solo. Descartado.

**Que la sala de máquina inventaríe `01_Procesado/Emails/adjuntos/`.** Cerraría el hueco del adjunto
solo-email, pero amplía una invariante declarada y se solapa con `MEJORAS #86`/`#87`.

**`--extraer-adjuntos` a default `True`.** Ahora además **bloqueado por `#98`**: generalizaría la
ceguera de §1.2.

**Flag `--sin-atomizar`.** YAGNI: la atomización es idempotente y barata frente al OCR que la sigue,
y un flag para saltarse el paso reabre la puerta que este bloque cierra.

## 6. Contrato de tests

Los 7 tests de la rev. 1 doblaban el motor, y la revisión demostró un defecto real que los pasaba
los 7: un lote con `mensaje_con_adjunto/mensaje.eml` (el layout de `--extraer-adjuntos`) donde el
pre-scan con `rglob` contaba 1 y el motor real encontraba 0. El contrato se amplía con **tests de
frontera contra el motor real**, no solo dobles.

**Con doble del motor** (`tests/test_sala_maquina_cableado_atomize.py`):

1. **Orden real:** la atomización se invoca antes de que se construya el plan de OCR (secuencia
   registrada, no un «se llamó»).
2. **No-op:** sin `.eml` y sin árbol previo → el motor no se invoca, no se crean `Emails/mensajes` ni
   `Emails/adjuntos`, no se emite evento.
3. **Reconciliación:** sin `.eml` **pero con árbol previo** → el motor **sí** se invoca, `status: ok`.
4. **Fallo blando:** el motor lanza → banner visible, evento con `status: fallo`, `sm.ejecutar` se
   invoca igual.
5. **`parcial`:** el motor termina con `errores` no vacío → `status: parcial`.
6. **Payload atado al dataclass real:** el doble devuelve una instancia real de `AtomizeReport`, no
   un `SimpleNamespace`; así un campo mal escrito en el payload rompe el test.
7. **`plan` no atomiza** (y emite la línea informativa). **`reforzar` no atomiza.**
8. **`case_dir` resuelto una sola vez:** no hay re-localización del caso dentro del helper.

**Contra el motor real** (`.eml` sintéticos mínimos en `tmp_path`):

9. **`.eml` anidado en subcarpeta:** `n_rec > n_top` → salta el aviso de §4.2 y los conteos del
   evento difieren. Es el test que la rev. 1 no tenía y que habría cazado el defecto.
10. **Transición a cero fuentes:** atomizar con correo → borrar el último `.eml` → `apply` →
    `mensajes/` queda podado. **Se documenta en el propio test** que `adjuntos/` NO se poda
    (comportamiento conocido, `MEJORAS #99`), para que el día que se arregle el test lo señale.
11. **Evento real:** vía `append_event` sin parchear, para verificar que `atomizado_email` es un
    evento válido y el payload es JSON-serializable.

**Test existente a actualizar:** `tests/test_intake_log.py:334` fija `len(INTAKE_EVENTS) == 26`;
pasa a 27. (El nombre de la función dice «24» — deriva preexistente, no la toco aquí.)

No se cubre en tests: exclusión mutua entre corridas concurrentes. Se documenta como hueco conocido
en §9.4 en vez de fingir que el contrato lo cubre.

## 7. Documentación a actualizar

- `.claude/skills/organizar-sala-maquina/SKILL.md` — hoy no menciona la atomización ni una vez.
- `PLAN.md` — casillas 1 y 2 del bloque, con el hash del PR; **casilla 3 marcada como bloqueada por
  `#98`**; corrección del supuesto de §1.1.
- `docs/MEJORAS_FUTURAS.md` — **`#98` nuevo** (trampa de `--extraer-adjuntos`), **`#99` nuevo**
  (saneamiento del motor), y actualización de `#55` y `#68` (el registro actual presenta `07b0377`
  como «la mitad resuelta»; es una trampa armada).
- `docs/ARQUITECTURA.md` si describe el orden del pipeline documental.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Que el PR se lea como «el frente de correo está cerrado» | §2 no-objetivos + §9, explícitos también en PLAN y MEJORAS |
| Que el cableado propague en silencio la ceguera de §1.2 | Aviso de §4.2 y los dos conteos en el evento |
| Que el consumidor asuma frescura | Rebaja explícita del objetivo 2 + `status` obligatorio en el evento |
| Re-leer los `.eml` en cada `apply` sobre `G:` | Coste marginal frente al OCR que sigue |
| El evento nuevo rompe un consumidor del log | **Corregido respecto de la rev. 1:** el consumidor localizado (`abrir_caso.py:159-166`) **no** filtra por evento — recorre todos y agrega `details.files[].sha256`. El evento nuevo es inocuo porque su payload **no lleva `files`**, no porque exista filtrado. Cualquier cambio futuro del payload debe respetar eso |

## 9. Defectos conocidos del motor (fuera de alcance, con dueño)

Se dejan escritos aquí porque acotan lo que este PR puede prometer.

**9.1. Enumeración no recursiva** (`extract.py:53`) → `MEJORAS #98`. Detallado en §1.2.

**9.2. Sin poda de `adjuntos/`.** La poda de idempotencia cubre solo `mensajes/*.md`
(`pipeline.py:121-124`); los binarios y sidecars de un correo retirado permanecen, y
`core/adjuntos_contenido/descubrir.py:13` recorre **todos** los sidecars sin contrastarlos con
`INDICE_ADJUNTOS.md`. Un adjunto borrado —incluso de otro expediente— se sigue procesando aguas
abajo. → `MEJORAS #99`.

**9.3. Publicación no atómica.** Escrituras directas sucesivas y `reg.save()` al final
(`pipeline.py:170`), con `write_text` sin temporal ni `replace` (`ids.py:93-96`) y degradación
silenciosa del registro truncado (`ids.py:104-107`). Riesgo: renumeración de IDs congelados.
→ `MEJORAS #99`.

**9.4. Sin exclusión mutua.** No hay lock ni snapshot entre el conteo, la lectura del atomizador y
el inventario del OCR. Dos `apply` simultáneos sobre el mismo caso pueden cargar el mismo contador
de `_registro.json`; un intake concurrente puede depositar un `.eml` entre la atomización y el
inventario. La concurrencia sobre el mismo caso ya ha ocurrido en este proyecto. Este PR **no** la
resuelve y **no** la empeora en lo esencial (ya existía para el OCR). → `MEJORAS #99`.
