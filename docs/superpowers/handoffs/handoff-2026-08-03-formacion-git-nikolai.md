---
tipo: handoff
estado: activo
creado: 2026-08-03
origen: sesión de consulta del 2026-08-03 — lectura del histórico del último mes (cierres 16º-55º, 228 commits) y diagnóstico de dónde se va el tiempo
destino: Nikolai, en sesiones propias fuera de Claude Code; y las sesiones de Code que ejecuten las filas de `PLAN.md` que salen de aquí
---

# Handoff — Plan de formación: git verificable + encargo anclado

**Andamio efímero, no fuente de verdad** (`GOBERNANZA_FUENTES_VERDAD §5`). Este fichero
existe para *arrancar*, no para consultarse dentro de un año. Lo que sobreviva a los
ejercicios se promueve a `docs/FLUJO_GIT.md`, que es el hogar declarado del «manual llano
del modelo git»; entonces esto pasa a `consumido` con su `consumido_por`. **Lo durable no se
escribe hoy:** documentar una lección antes de aprenderla es cómo se fabrica prosa que nadie
comprueba.

El estado de ciclo de vida de las acciones que salen de aquí vive en **`PLAN.md`**, no en
este fichero.

## El diagnóstico que lo motiva (medido el 2026-08-03)

Ventana de los datos: del 2026-07-05 al 2026-08-02 —**228 commits, 40 cierres** (~2,5
sesiones/día)—, medida el 2026-08-03 sobre el último commit de esa ventana (`42d2b39`).

| | |
|---|---|
| Commits que tocan `core/`, `scripts/` o `streamlit_app.py` | **57 de 228 (25 %)** |
| Commits solo de documentación/config | 150 (66 %) |
| Líneas añadidas: `docs/` frente a `core/` | **+63.667 vs +6.741 — 9,4 a 1** |

No es que la gobernanza sea desperdicio: las revisiones adversariales del mes compraron
defectos caros y vivos (la invariante que habría autorizado modificar un expediente real de
cliente; tres rutas de pérdida de datos en #156, #160 y #175). Es que **la maquinaria de
proceso crece más rápido que la máquina**, y el sitio donde una hora de Nikolai rinde más ha
cambiado.

**Objetivo del plan, en una frase:** que Nikolai deje de depender de la palabra de Claude
para saber en qué estado está el repo, y que ningún encargo vuelva a ejecutarse dos veces ni
a descartarse por error.

---

## Bloque 1 — Git: el modelo mental, no los comandos

**Por qué primero:** 94 menciones de «worktree» en la bitácora del mes, cuatro secciones de
`DEAD_ENDS` dedicadas a modos de fallo de git, y una sesión entera perdida por declarar
duplicado un trabajo que no lo estaba (50º cierre).

### Laboratorio (5 min, una sola vez)

```powershell
git clone --no-hardlinks "C:\Users\tnm33\Dev\FeesDefender" "$env:TEMP\git-sandbox"
```

Clon local: historia real, riesgo cero. **Regla única: nunca `git push` desde ahí.** Lo que
se rompa se arregla borrando la carpeta.

### Sesión 1 (90 min) — Una rama es un fichero de 41 bytes

**Leer:** Pro Git, cap. 3.1 «Las ramas en pocas palabras» (gratis, en castellano, 20 min).

**Hacer**, en el sandbox:

```powershell
git switch -c prueba; Get-Content .git\refs\heads\prueba; git rev-parse HEAD
```

Las dos últimas salidas son el mismo SHA. Ahí está el modelo entero: **una rama no contiene
commits, apunta a uno.**

**Lo tienes cuando** puedas explicar por qué crear una rama es instantáneo aunque el repo
pese 200 MB.

### Sesión 2 (90 min) — El squash rompe la ascendencia ⭐

La que más ha costado. En el sandbox:

```powershell
git switch -c experimento; "ensayo" | Out-File -Encoding utf8 prueba.txt; git add prueba.txt; git commit -m "prueba"; git switch main; git merge --squash experimento; git commit -m "squash del experimento"
```

Y ahora las dos órdenes que se contradicen:

```powershell
git branch -d experimento
```

La **rechaza** («not fully merged»). Y sin embargo:

```powershell
git diff --stat main experimento
```

**Vacío**: el contenido sí está. Las dos cosas son ciertas porque **`git branch -d` mide
ascendencia, no contenido**, y el squash creó un commit sin memoria del original. Es la causa
raíz del incidente del 50º cierre y la razón de que `DEAD_ENDS §9` obligue a verificar por
contenido.

**Lo tienes cuando** puedas decir sin dudar por qué «git dice que la rama no está mergeada»
no significa que tu trabajo no esté en `main`.

> Haz las sesiones 1 y 2 **seguidas**: son una sola idea (la rama es un puntero → por eso el
> squash rompe la ascendencia).

### Sesión 3 (90 min) — Worktrees, y verificar por contenido

**Leer:** `git help worktree`, secciones DESCRIPTION y COMMANDS (15 min). *(Es la fuente
buena; el capítulo de Pro Git citado en la conversación inicial no era el correcto.)*

**Hacer**, en el sandbox — reproduce el `Caso A` de `DEAD_ENDS §9`:

```powershell
git worktree add ..\wt-prueba main
```

Falla con `'main' is already used by worktree at ...`. **Ésa es la causa exacta** de que
`gh pr merge --delete-branch` aborte mientras el merge sí se hizo.

**Luego, sobre el repo real y en solo lectura**, en PowerShell:

```powershell
git show "origin/main:.claude/commands/encargo.md" | Select-String "por si acaso"
```

**El matiz que ahorra un susto, y que pasó de verdad el 2026-08-03:** esa misma comprobación
lanzada desde Git Bash respondió que **el fichero no existía**. Era falso — Bash convirtió
`origin/main:.claude/...` en `origin\main;.claude\...`. Si se hubiera creído esa salida, se
habría reportado que el merge no llegó. **La herramienta de verificación también miente:
cuando el resultado sorprenda, comprobarlo por una segunda vía antes de concluir.**

### La tarjeta de cinco comandos (el contenido durable de este bloque)

| Pregunta | Comando |
|---|---|
| ¿Este PR está mergeado? | `gh pr view N --json state,mergeCommit` |
| ¿Mi cambio está en `main`? | `git show "origin/main:<fichero>" \| Select-String "<mi frase>"` |
| ¿Esta rama aporta algo aún? | `git diff --stat origin/main <rama>` (vacío = ya está) |
| ¿Qué worktrees tengo vivos? | `git worktree list` |
| ¿Falló de verdad ese comando? | `$out = <cmd> 2>&1` y leer `$LASTEXITCODE` **acto seguido** |

**Al terminar el bloque 1, esta tabla se promueve a `docs/FLUJO_GIT.md`** (§1 «El modelo en
llano» o §5 «Poda e higiene», donde encaje mejor una vez hechos los ejercicios).

---

## Bloque 2 — El encargo anclado (30 min)

**La mitad mecánica ya está hecha:** `/encargo` construido y mergeado (`44a1c9d`, PR #194).
Queda el hábito.

### Los dos modos de fallo, que son simétricos

| | Consecuencia | Caso real |
|---|---|---|
| **Falso pendiente** | Trabajo duplicado | PR #173: llegó con 4 puntos y el #171 ya había cerrado 3 |
| **Falso duplicado** | Trabajo **no hecho**, en silencio | 50º cierre: «no dupliqué trabajo, lo declaré duplicado» |

El segundo es el caro: nadie audita lo que se dio por hecho. Cualquier remedio que solo
prevenga el primero empeora el segundo.

### Plantilla, para cuando no se use `/encargo`

```
ENCARGO: <qué quiero>
ESTADO QUE CREO: <lo que asumo> — fuente: <PLAN.md fila #N / PR #NNN / lo recuerdo>
ANTES DE TOCAR NADA: verifícalo contra git. Si discrepa, PÁRATE y dímelo.
No lo ejecutes por si acaso, ni lo descartes por si acaso.
```

### El cambio de hábito, que es lo único que queda

Abrir la sesión preguntando el estado **según git**, no según `PLAN.md`. `PLAN.md` describe;
git es. Cuando discrepen, gana git y se corrige el documento.

---

## Bloques 3-6 — refuerzo (semanas 3-4)

**3. Leer una medición: unidad, muestra, comparación.** *(0 min de estudio; es un reflejo.)*
Tres preguntas ante cualquier cifra: **¿en qué unidad? ¿sobre qué muestra? ¿contra qué se
compara?** Evidencia del mes: el error de chars-vs-bytes sostuvo una línea de trabajo entera;
`MEJORAS #111` se abrió como hallazgo grave y **quedó refutada al medirla**; la fila #1 de la
cola se cerró sin rendimiento. Lo más rentable de la lista y no cuesta nada.

**4. Qué prueba un test, y qué es una prueba de mutación.** *(45 min.)* Concepto, no
herramienta: **verde no prueba nada**. Pregunta por defecto ante «ya está cubierto por
tests»: **«¿mordió la mutación?»**. En el 55º cierre la primera pasada no mordió y el defecto
era el test, no el guard.

**5. Presupuesto explícito de proceso.** *(Una decisión, no estudio.)* → fila propia en
`PLAN.md`.

**6. Ciclo de vida de una skill hasta el despliegue.** *(Una tarde.)* → fila propia en
`PLAN.md`. Leer `docs/MEJORA_CONTINUA_SKILLS.md`. **Trampa ya documentada:** empaquetar desde
la raíz, nunca desde un worktree que se poda, y verificar la versión *dentro* del zip.

---

## Cómo se sabrá si sirvió (revisar el 2026-09-03)

| Métrica | 2026-08-03 | Objetivo |
|---|---|---|
| Sesiones perdidas por trabajo duplicado o mal declarado como hecho | 3-4 al mes | **0** |
| Veces que se pregunta a Claude «¿esto está mergeado?» en vez de comprobarlo | siempre | **0** |
| Skills construidas pero no desplegadas en Cowork | 6 pendientes | **0** |
| Cierres consecutivos sin código de producción | 4 | el número que fije la fila del presupuesto |

Las cuatro son contables y ninguna depende de la opinión de Claude, que es el punto del plan.

## Qué hace falta para cerrar este handoff

Pasa a `estado: consumido` cuando (a) estén hechas las tres sesiones del bloque 1, y (b) la
tarjeta de cinco comandos esté promovida a `docs/FLUJO_GIT.md` — que será el
`consumido_por`. Los bloques 3-6 no lo bloquean: viven en `PLAN.md` o son hábitos sin
artefacto.
