---
description: Ancla una consulta a su premisa — verifica lo que la pregunta da por supuesto ANTES de contestarla
argument-hint: la pregunta, tal cual (incluida la afirmación que trae dentro)
allowed-tools: Bash, Read, Grep, Glob, WebFetch, WebSearch
---

Consulta recibida: $ARGUMENTS

**No la contestes todavía.** Este comando es el gemelo de `/encargo` para preguntas. Allí la
creencia falsa produce **trabajo duplicado**; aquí produce algo más difícil de detectar: una
**respuesta correcta e inútil**, porque contesta con rigor una pregunta mal planteada. Nadie
audita una respuesta bien argumentada.

Medido el 2026-08-03, en una sola sesión de consulta: **tres premisas falsas, y las tres veces
el dato estaba en el repo** (59º cierre).

## Paso 1 — Separa la pregunta de su premisa

Del texto de arriba, enuncia por separado:

- **Lo que se pregunta** (la duda real).
- **Lo que la pregunta afirma de paso**: que usamos X, que el sistema no hace Y, que una
  herramienta ajena se comporta de tal modo, que algo está parcheado / roto / pendiente. Y
  **de dónde parece venir** esa afirmación: una lectura, un README ajeno, un recuerdo, una
  observación indirecta.

**Si la pregunta no afirma nada verificable, dilo en una línea y pasa al Paso 4.** No conviertas
toda consulta en un interrogatorio: la ceremonia sin aporte se paga y no compra nada (mismo
razonamiento que hizo condicional el gate de `preclasificar`, 2026-07-21).

## Paso 2 — Verifica la premisa contra la fuente, no contra la prosa

Según de qué sea la afirmación:

**Si es sobre nuestro código** → al código, no a `PLAN.md`, `STATUS.md`, la bitácora ni
`MEJORAS_FUTURAS.md`. Esos **describen**; el código **es**.

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
git grep -n "<símbolo o dependencia>" -- core scripts tests
```

Caso medido: «¿pdf-inspector es mejor que markitdown? revísalo contra FeesDefender». markitdown
**no está en el código** — solo citado en `MEJORAS #24` como candidato y en un plan como
«pendiente bench». La comparación era cierta y **no decía nada** sobre este repo.

**Si es sobre una herramienta ajena** → a sus ficheros, y **cita literal**. No contestes de
memoria ni por el README de portada.

Caso medido: «¿por qué Vassal no guarda el crudo?». Sí lo guarda —
`«Оригинальные файлы сохраняются в .vassal/raw/»`, y su `intake` **copia** y luego **vacía la
bandeja de entrada**. La premisa venía de una observación real mal interpretada: la bandeja
aparece vacía y el original está oculto.

**Si es un benchmark o una cifra de un tercero** → tres preguntas antes de citarlo: **quién lo
publica** (¿el proveedor de lo que vende?), **en qué condiciones** (hoy: 200 PDFs *con OCR
desactivado*, o sea el terreno donde el candidato juega y el resto no), y **está en la tabla lo
que nosotros usamos** (no lo estaba: Docling ausente).

**Si es sobre el estado del proyecto** («esto está parcheado», «esto no lo lee nadie») → **mide**.
Contar es barato y cambia la respuesta.

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
git grep -c "" -- tests | Measure-Object -Sum Count      # peso real de los tests
```

Caso medido: «con lo parcheado que está, ¿no es más fácil una v2?». Al medirlo: **43.846 líneas
de tests (2.617)**, 31 callejones documentados, y **cada defecto levantado ese día ya estaba
medido y adjudicado**. Lo que se leía como parche era la **legibilidad de la propia deuda**.

## Paso 3 — Si la premisa no se sostiene, contéstala PRIMERO

A diferencia de `/encargo`, aquí no te paras: **reordenas**. Abre por la premisa y luego contesta
la pregunta, si es que sigue teniendo sentido.

- Premisa falsa → dilo y explica qué la produjo (una observación real mal leída suele estar
  detrás; decirlo evita que vuelva).
- Premisa cierta pero **irrelevante** → esto es lo más fácil de dejar pasar. Si la comparación es
  cierta y no aplica, la respuesta útil es *por qué no aplica*, no el veredicto.
- Premisa **incompleta** → complétala con el dato antes de opinar.

Y no adornes la corrección: una frase, el dato, y sigue. La premisa era de quien pregunta, no un
error que haya que enmarcar.

## Paso 4 — Contesta, y deja el rastro

Responde a lo que se pregunta, con la fuente pegada a cada afirmación (`file:line` para el
código, cita literal para lo ajeno).

Abre tu respuesta con una línea de anclaje, para que quede en el transcript:

> **Premisa:** <lo que la pregunta daba por supuesto> — <confirmada | falsa | cierta pero no
> aplica | incompleta>, comprobado con `<comando o fichero>`.

**Y al cerrar la consulta, decide si algo de lo hallado es durable.** Una consulta que destapa un
defecto medido tiene el mismo deber que una sesión de código: entrada en `MEJORAS_FUTURAS.md` con
la medición y su disparador, y **nada a `PLAN.md` sin disparador concreto** (regla de promoción de
`CLAUDE.md`). Si no lo escribes, la próxima consulta lo vuelve a descubrir.
