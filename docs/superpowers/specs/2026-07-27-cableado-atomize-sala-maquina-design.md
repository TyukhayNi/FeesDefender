# Diseño — Cableado de la atomización de correo en la sala de máquina

> **Estado:** diseño aprobado por Nikolai 2026-07-27 (brainstorming).
> **Alcance:** **cableado, no motor.** Quién llama a quién en el pipeline de correo.
> **Origen:** `PLAN.md` → `[SIGUIENTE-CABLEADO-CORREO]` (resto de `MEJORAS #68`), promovido por
> decisión explícita de Nikolai el 2026-07-27.
> **Fuera de alcance (otros ítems, no este PR):** OCR/extracción de adjuntos de correo
> (`MEJORAS #87`), consumo de las fuentes atomizadas por la sala de lectura (`MEJORAS #86`),
> `--extraer-adjuntos` a default `True` (tercera casilla del bloque del PLAN).
> **Disciplina:** brainstorming → spec → plan → TDD → revisión adversarial.

## 1. Contexto

Las piezas del pipeline de correo están construidas y ninguna llama a la siguiente. El motor
`core/email_atomize/` (Capas A + B + capa de caso, completo en `main`) solo lo invocan hoy:

- el CLI manual `scripts/atomize_emails.py`, y
- `scripts/audit_correos_no_separados.py`, que importa un helper para auditar.

`core/sala_maquina.py` no lo menciona en absoluto; `scripts/abrir_caso.py` tampoco. Si el operador
no se acuerda de lanzar la atomización a mano, todo lo que cuelga de ella se comporta como si no
existiera.

### 1.1. Corrección de un supuesto heredado

El bloque del `PLAN.md` justifica el orden diciendo que hay que **atomizar antes de la sala de
máquina «o el OCR queda incompleto»**. Verificado contra el código, eso **no es cierto para el
atomizador**:

- `core/sala_maquina.py::inventariar` recorre **solo** `<caso>/00_Input/` (`sala_maquina.py:551`).
- `core.email_atomize.pipeline.atomize_dir` escribe en `<caso>/01_Procesado/Emails`
  (`pipeline.py:297`), árbol que la sala de máquina no mira.
- El `.eml` sí entra al inventario (ext «nativo»), pero `core.extractor._try_email` extrae
  cabeceras + cuerpo y **no recorre adjuntos**.

Es exactamente lo que ya dejó anotado `MEJORAS #55`: *«poner atomize "antes" NO mete los átomos en
el OCR/MD de forma automática»*. La frase del PLAN es cierta para el `--extraer-adjuntos` del
intake (resuelto en `07b0377`, escribe los adjuntos sueltos en `00_Input`), no para el atomizador.

**Consecuencia para este diseño:** el cableado se justifica por lo que sí compra, no por cerrar el
hueco del OCR — que sigue abierto y con dueño (`MEJORAS #87`).

## 2. Objetivos y no-objetivos

**Objetivos.**

1. Que el orden **intake → atomización → sala de máquina** lo garantice el código, no la memoria
   del operador.
2. Que `<caso>/01_Procesado/Emails` esté siempre fresco cuando la sala de máquina ha corrido, de
   modo que el consumidor de la sala de lectura pueda apoyarse en él sin comprobar nada.
3. Que el **detector de contaminación cruzada por W-code** (`core/email_atomize/contaminacion.py`,
   commit `20465ef`) corra en toda corrida y su aviso sea visible. Hoy solo se dispara si alguien
   lanza el CLI a mano; el patrón que detecta ya ha mordido tres veces (W-02XOR7, W-02VUDR y el
   caso anotado en `MEJORAS #68`).
4. Dar rastro forense a la atomización, que hoy **no emite ningún evento** en `_intake_log.jsonl`
   pese a reescribir un árbol entero de `01_Procesado/`.

**No-objetivos (explícitos, para que nadie lea este PR como el cierre del frente de correo).**

- **El adjunto que llega solo por correo sigue sin llegar al OCR.** Este PR no cambia una línea de
  lo que la sala de máquina inventaría.
- No se toca el motor `core/email_atomize/` — ni su lógica, ni sus salidas, ni sus IDs congelados.
- No se toca la invariante «`00_Input` es crudo y es la única fuente de la sala de máquina».
- No se encadena nada en `scripts/abrir_caso.py` (opción (i) del PLAN, descartada en el
  brainstorming a favor de (ii)).

## 3. Decisión: dónde vive el disparo

El PLAN dejaba tres opciones abiertas. Se elige **(ii) `organizar-sala-maquina`**, y dentro de ella,
el orquestador CLI:

| Opción | Veredicto |
|---|---|
| (i) `abrir_caso` lo encadena | **No.** La apertura corre una vez; la sala de máquina se re-lanza. Atar el paso a la apertura deja sin cubrir todo caso reprocesado. |
| (ii) `organizar-sala-maquina` antes de su OCR | **Sí.** Es donde el orden importa y donde el operador ya está. |
| (iii) fachada `procesar_expediente()` | **No.** Añade una capa sin resolver quién la llama: mueve el problema, no lo cierra. |

Dentro de (ii), el disparo va en **`scripts/sala_maquina.py::apply`**, no en el SKILL.md ni en
`core/sala_maquina.py`:

- **No en el SKILL.md.** Un paso descrito en prosa que un modelo debe recordar ejecutar es el mismo
  mecanismo que falla hoy. El bloque del PLAN pide garantía mecánica; la prosa no lo es.
- **No en `core/sala_maquina.py`.** El motor de OCR no debe saber qué es un correo. Encadenar dos
  pipelines es orquestación, y la orquestación vive en `scripts/` (regla de las 3 capas del
  `CLAUDE.md`: la lógica en el core, el orquestador fino).

## 4. Arquitectura

```
apply(case_id, vision, force)
  ├─ _resolver_caso(case_id)            (existente)
  ├─ _exigir_vision_cableada()          (existente, solo si --vision)
  ├─ _atomizar_correo(case_id)          ← NUEVO
  ├─ _construir_plan(case_dir, force)   (existente)
  └─ sm.ejecutar(...)                   (existente)
```

### 4.1. `_atomizar_correo(case_id) -> AtomizeReport | None`

Función privada del CLI. Reutiliza `core.email_atomize.pipeline` sin envolverlo en abstracción
nueva.

```
fuentes = P.emails_src_dirs(case_id)
si ningún .eml bajo esas fuentes:  → devuelve None, no toca disco, no emite evento
intenta:  report = P.atomize_case(case_id)
excepto:  imprime el fallo, devuelve None, la corrida SIGUE
imprime resumen + notas destacadas + errores
emite evento atomizado_email
devuelve report
```

**Tres reglas de comportamiento:**

**(a) No-op estricto sin correo.** La condición de no-op es **que no haya ningún `.eml`** bajo las
fuentes, no que la lista de fuentes esté vacía: `emails_src_dirs` devuelve carpetas de lote y un
lote `email` puede existir vacío (o quedarse vacío tras un borrado de ruido, que es justo el
remedio aplicado en W-02VUDR). Importa porque `atomize_dir` hace
`mkdir(parents=True, exist_ok=True)` de `mensajes/` y `adjuntos/` **incondicionalmente**
(`pipeline.py:88-89`): llamarlo a ciegas sembraría dos carpetas vacías en todo caso sin correo, y
la sala de máquina se usa en casos que no tienen ninguno. El conteo es un `rglob("*.eml")` sobre
las fuentes, coherente con lo que el propio motor recorre.

**(b) Idempotencia heredada, sin estado propio.** El motor ya es idempotente y está verificado en
vivo (dos corridas seguidas sobre W-02VND1 → 0 cambios). No se añade un segundo `_state.json` ni
ningún registro paralelo: duplicar el control de idempotencia es crear dos verdades que pueden
divergir.

**(c) Falla blando.** Una excepción del motor se captura, se reporta y **no aborta el OCR**.
Fundamento: el OCR hoy no depende de la atomización (§1.1), una corrida de sala de máquina puede
durar ~1h40, y el propio motor ya profesa que «un email entre 125 no tumba la corrida». Los
`report.errores` por mensaje se imprimen pero tampoco abortan.

### 4.2. Visibilidad de las notas de contaminación

`report.notas` es donde `contaminacion.py` deposita el aviso de W-code ajeno. Se imprimen
**destacadas y al principio** de la corrida, no sepultadas al final de una hora de log de OCR. El
aviso avisa; no excluye nada (decisión ya tomada en `20465ef`: borrar es del letrado).

### 4.3. Evento forense

Alta de `atomizado_email` en `INTAKE_EVENTS` (`core/intake_log.py:42`). Se emite **solo si hubo
atomización real** — nunca en el no-op de (a) ni cuando el motor lanzó.

```json
{"event": "atomizado_email",
 "details": {"mensajes": 413, "adjuntos_unicos": 162, "reconstruidos_b": 136,
             "citas_a_revision": 43, "upgrades": 8,
             "notas": ["…W-code ajeno…"], "errores": []}}
```

Se emite **antes** de arrancar el OCR, no al terminar la corrida: si la corrida larga se cae a
media, el rastro de lo que la atomización hizo en disco ya está escrito.

### 4.4. `plan` y `reforzar` no atomizan

- **`plan`** es preview. No debe reescribir `01_Procesado/Emails`. En su lugar, con el **mismo
  conteo de (a)**, emite una línea informativa del tipo `correo: N .eml (se atomizarán en apply)`,
  y calla si `N == 0`. *(Matiz honesto: `plan` ya no es del todo read-only —
  escribe el manifiesto de segmentación. Aun así, atomizar en un preview es sorprendente y el
  manifiesto es un gate editable deliberado, no un precedente.)*
- **`reforzar`** re-procesa dudosos ya conocidos de la cobertura. La atomización no le aporta nada.

## 5. Alternativas descartadas

**Que la sala de máquina inventaríe también `01_Procesado/Emails/adjuntos/`** (con dedup por
sha256 contra `00_Input`, que sería barato porque `inventariar` ya hashea). Cerraría de verdad el
hueco del adjunto solo-email, pero amplía una invariante declarada en el docstring del módulo y en
`_ZONAS_VETADAS`, y se solapa de lleno con `MEJORAS #86`/`#87`. Descartada para este PR por
decisión de Nikolai: este bloque es cableado, no motor.

**`--extraer-adjuntos` a default `True`.** Cerraría el hueco sin tocar invariante alguna (los
adjuntos caerían sueltos en `00_Input`, que la máquina ya lee), pero mueve la superficie de dedup
de todo intake futuro. Es la tercera casilla del bloque del PLAN y se decide aparte.

**Flag `--sin-atomizar` en `apply`.** Descartado (YAGNI). La atomización es idempotente y no hace
OCR, así que re-correrla es barato frente a la corrida que la sigue; y un flag para saltarse el
paso reabre justo la puerta que este bloque viene a cerrar.

## 6. Contrato de tests

Fichero nuevo `tests/test_sala_maquina_cableado_atomize.py`, con el motor real sustituido por un
doble (no se atomiza de verdad en la suite):

1. **Orden real.** La atomización se invoca **antes** de que se construya el plan de OCR. Se
   verifica la secuencia registrada, no un simple «se llamó»: el orden es el objeto del PR.
2. **No-op sin correo — dos variantes.** (a) Caso sin lotes `email` ni `03_Email`; (b) caso **con**
   un lote `email` que no contiene ningún `.eml`. En ambas: el motor no se invoca, no se crean
   `Emails/mensajes` ni `Emails/adjuntos`, y no se emite evento. La variante (b) es la que fija la
   regla real y la que un `if not fuentes` ingenuo dejaría pasar.
3. **Falla blando.** El motor lanza → el mensaje sale por pantalla, `sm.ejecutar` se invoca igual,
   la corrida termina con su salida normal.
4. **Evento.** Con atomización real se emite `atomizado_email` con los contadores del report;
   se emite antes que `procesado_sala_maquina`.
5. **`plan` no atomiza.** El motor no se invoca y la línea informativa aparece.
6. **`reforzar` no atomiza.** El motor no se invoca.
7. **Notas visibles.** Una nota de contaminación en el report aparece en la salida.

Suite completa verde como gate (baseline de esta rama: 2424 · 0 fallos · 0 errores · 76 skipped).

## 7. Documentación a actualizar

- `.claude/skills/organizar-sala-maquina/SKILL.md` — hoy no menciona la atomización ni una vez.
  Añadir que `apply` la encadena, y qué significan las notas de contaminación cuando aparecen.
- `PLAN.md` — casillas 1 y 2 del bloque `[SIGUIENTE-CABLEADO-CORREO]`, con el hash del PR. La
  casilla 3 (`--extraer-adjuntos`) queda abierta.
- `docs/MEJORAS_FUTURAS.md` `#55` y `#68` — estado real tras el cableado, y la corrección de §1.1
  para que el supuesto «atomizar antes arregla el OCR» no vuelva a circular.
- `docs/ARQUITECTURA.md` si describe el orden del pipeline documental.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Que el PR se lea como «el frente de correo está cerrado» | §2 no-objetivos, explícito en spec, PLAN y MEJORAS |
| Una corrida de `apply` sobre un caso en `G:` re-lee todos los `.eml` | Coste marginal frente al OCR que la sigue; medido como aceptable en la decisión de descartar el flag |
| El evento nuevo rompe un consumidor del log | `INTAKE_EVENTS` es una lista blanca aditiva; los consumidores filtran por evento conocido |
| Divergencia de resolución del caso entre `_resolver_caso` y `emails_src_dirs` | Ninguna: `core.config.caso_path` delega en `case_locator.path_for`, y ambos caminos pasan por `resolve_ref` |
