---
estado: ejecutado
dueño: Nikolai Tyukhay
fecha: 2026-08-25
---

# Integridad del cierre del checkin — `MEJORAS #96` y `#93-B` + defecto A-2c

> **Qué es esto y qué NO es.** No es la Fase 2 de la arquitectura dual: la Fase 2 quedó
> **aparcada con disparador escrito** el 2026-08-25 (`PLAN.md` fila #3), tras medir que
> **abrir un expediente nunca presta nada** —`scripts/abrir_caso.py` tiene cero referencias
> al subsistema de préstamo— y que, con tres abogados que no trabajan en paralelo, tres de
> sus cinco defectos restantes protegen de una concurrencia que no se produce.
>
> Esto es la **extracción** de lo que sí había mordido en la vida real: los dos únicos
> defectos del préstamo con incidente medido.

## 1. Los dos defectos, y qué se hizo

### 1.1. `MEJORAS #96` — el guard se disparaba sobre la copia prestada

`guard_escritura` decidía por el `estado_repositorio` del `_caso.md` **local**. Sobre una
copia prestada eso desviaba documentos a `_pendiente_checkin/`, fuera de `00_Input`, que es
lo que recorre el motor de OCR: se depositaban documentos, el OCR no veía ninguno y la
corrida se reportaba correcta. Medido el 2026-07-27 sobre `W-02MA0R`.

**Discriminante:** el **registro privado de workspaces** (Fase 1) — ¿consta esta ruta como
copia local de esta máquina? El canon nunca está ahí. Falla cerrado: cualquier duda desvía.

**El discriminante que se descartó, porque abría un agujero:** la presencia de
`MANIFEST_CHECKOUT.json`. `cmd_checkout` sube una copia del manifiesto **al Drive** (§3.3,
«debe sobrevivir a la muerte del Desktop»), así que mientras un caso está prestado el
fichero está en **las dos copias**; discriminar por él desactivaba el guard sobre el canon
justo mientras otro lo tenía tomado.

### 1.2. `MEJORAS #93-B` + A-2c — el orden del cierre

`cmd_checkin` validaba la transición de estado **al final** (CP11), después de inventariar,
copiar, verificar, registrar el evento forense e integrar la bandeja. Tres síntomas de un
solo error de sitio: un **traceback** con todo el trabajo bien hecho (medido sobre
`W-02VND1`: 431 ficheros, 0 diferencias, y CP11 completado a mano), un checkin reentrante
que dejaba **dos** `case_checkin` en el registro de custodia, y —el que encontró R9— un
reentrante que llegaba a **subir trabajo nuevo al canon sin lock**.

**Ahora:** CP3-bis, justo **antes de la primera escritura**. `0` reentrancia · `2` anomalía
sin efectos · `4` solo si el estado cambia durante la corrida. CP11 conserva su relectura
pegada al push.

### 1.3. Verificación

Los `xfail` del frontal pasan de **7 a 6**: A-2c se retira de
`tests/test_repository_cli_defectos.py` y su caracterización **verde** vive en
`tests/test_checkin_reentrante.py` — el mismo trato que recibió el octavo defecto en el
PR #160. Suite con dos semillas (777 y 31337): **3.395 tests, 0 fallos, 6 `xfailed`**.

## 2. Adjudicación de la revisión adversarial R9 (Codex, 2026-08-25) — NO-SHIP, remediado

- **Objeto revisado:** el diff de estos dos arreglos contra `origin/main`, 679 líneas.
- **Ronda:** R9, la primera de este trabajo; revisa **código**, no prosa.
- **Revisor:** Codex por CLI sobre dos copias externas `git archive` sin `.git`; adjudica Claude Code contra la fuente.
- **Informe recibido:** `docs/superpowers/specs/2026-08-25-checkin-integridad-r9-adversarial-review.md`, `sha256` `8e4f653825dcaf2a553f267363a680015cc9cb01fce39d4d4170b208cd449bd0`, recomputado al archivarlo y **coincide**.
- **Hallazgos:** 8 — 2 CRÍTICOS, 1 ALTO, 5 MEDIOS. **8 confirmados, 0 refutados.**
- **Remediado en:** el commit que acompaña a esta adjudicación, con test por hallazgo.

### Por qué esta ronda valió la pena

**Dos de los ocho eran vías de escritura sobre el canon de un caso prestado**, que es
exactamente lo que todo este subsistema existe para impedir. Y uno de los dos **lo había
introducido yo con el arreglo**.

| # | Sev. | Hallazgo | Veredicto | Remedio |
|---|---|---|---|---|
| H9-01 | CRÍTICO | El manifiesto que marca «copia local» se sube al canon y apaga allí el guard | **CONFIRMADO** | Discriminante = registro de workspaces; test que lo caza + mutante que lo revive |
| H9-02 | CRÍTICO | El reentrante sube trabajo nuevo sin lock y luego devuelve 0 | **CONFIRMADO** | CP3-bis antes de la primera escritura; test con fichero post-cierre |
| H9-03 | ALTO | CP11 sube una foto obsoleta del `_caso.md` tras una ventana ensanchada | **CONFIRMADO** | CP11 recupera su relectura pegada al push |
| H9-04 | MEDIO | El diagnóstico revienta con `meta` no-dict y llama reentrancia a un estado corrupto | **CONFIRMADO** | `isinstance` + exigir estado `disponible`, no solo la marca |
| H9-05 | MEDIO | El código 4 contradice el contrato publicado del módulo | **CONFIRMADO** | `2` al entrar («abortado sin efectos»); `4` solo tras trabajar |
| H9-06 | MEDIO | Los controles del canon omiten el estado que produce el checkout real | **CONFIRMADO** | Control con manifiesto presente sobre canon prestado |
| H9-07 | MEDIO | «No toca el Drive» solo comprobaba que no apareciera `check` | **CONFIRMADO** | Comparación byte a byte del Drive + escrituras por destino |
| H9-08 | MEDIO | El test reescrito no fijaba **cuándo** ocurre la comprobación | **CONFIRMADO** | Aserto de que no hay `copy` ni `check` antes del diagnóstico |

### Convergencia, y lo que dice del método

**H9-01 lo encontré yo por mi cuenta mientras la revisión corría**, siguiendo el punto que
el propio mandato le señalaba al revisor: «¿puede el manifiesto existir sobre la copia
canónica?». Que dos caminos independientes lleguen al mismo crítico no exime a ninguno —lo
que exime es la medición—, pero sí dice que la pregunta estaba bien puesta en el mandato.
Lo que **no** vi yo son H9-02 y H9-03, que son consecuencia de mi propio arreglo.

### Lo que aporta el adjudicador y el revisor no vio

El remedio de H9-05 **sale de la tabla de códigos del propio módulo**, no de una decisión
nueva: `2` ya estaba definido como «abortado sin efectos (caso no disponible, carrera de
lock perdida, ruta local ausente)». El primer arreglo usaba `4` sin mirar esa tabla. El
revisor señaló la contradicción; el código correcto ya estaba escrito diez líneas más
arriba en el mismo fichero.

### Lo que sigue SIN VERIFICAR, y se declara

- **El revisor no pudo ejecutar ni un test**: la copia externa no trae el entorno virtual
  (`ModuleNotFoundError: dotenv`). Sus ocho reproducciones son **análisis de fuente**, no
  ejecución, y él lo declara. Las corridas —dos semillas, 3.395 tests— son del adjudicador.
- **El coste de `es_copia_prestada` por escritura.** Añade una lectura del registro por cada
  llamada al guard. No se midió sobre un intake real; en la suite no se nota.
- **La rama de `4` tras trabajar** (el estado cambia a media corrida) no tiene test propio:
  exige un interleaving con el doble, y es territorio de A-1, que está aparcado.
