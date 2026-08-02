---
description: Ancla un encargo a estado verificable — comprueba contra git ANTES de tocar nada y para si discrepa
argument-hint: qué quiero + qué creo que ya está hecho (y de dónde lo saco)
allowed-tools: Bash, Read, Grep
---

Encargo recibido: $ARGUMENTS

**No empieces a trabajar todavía.** Este comando existe porque el mismo encargo se ha
disparado por duplicado tres o cuatro veces, y —lo caro— porque una vez se declaró
duplicado un trabajo que no lo estaba (50º cierre: «no dupliqué trabajo, lo declaré
duplicado»). Los dos fallos son simétricos y hay que cerrar los dos.

## Paso 1 — Separa el encargo de la creencia

Del texto de arriba, extrae y enuncia por separado:

- **Lo que se pide** (la acción).
- **El estado que el encargo da por supuesto** (que algo está hecho, pendiente, mergeado,
  bloqueado, decidido…) y **de dónde sale esa creencia**: `PLAN.md`, `STATUS.md`, un número
  de PR, la bitácora, o la memoria de Nikolai.

Si el encargo no afirma ningún estado, dilo y pasa al Paso 4.

## Paso 2 — Verifica ese estado contra git, no contra prosa

`PLAN.md`, `STATUS.md`, la bitácora y la memoria **describen** el estado; git **es** el
estado. Verifica con las tres vías, en este orden:

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
git log --oneline -15
```

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
gh pr list --state all --limit 15
```

Y, cuando la creencia sea «X ya está en main», **verifícalo por CONTENIDO**, que es la única
prueba que el squash no rompe:

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
git show origin/main:<fichero> | Select-String "<frase o símbolo concreto>"
```

Reglas de esta verificación, todas compradas con incidentes reales:

- **`git branch --merged` y la ausencia de rama NO son prueba**: el squash rompe la
  ascendencia (`DEAD_ENDS §9`).
- **Un `git diff` no vacío no significa que lo tuyo no entró**: puede ser una edición ajena
  al mismo párrafo (PR #178).
- **La salida de `gh pr merge` no es la verdad** sobre si un PR está mergeado; lo es
  `gh pr view <n> --json state,mergeCommit`.
- **No delegues esta lectura a un subagente** cuando lo que se comprueba es si algo está
  mergeado: si lo está o no, lo dice git, y una lectura de segunda mano es justo lo que
  falló antes.

## Paso 3 — Si discrepa, PÁRATE

Si lo que encuentras no coincide con el estado que el encargo supone, **no sigas**. Informa
en tres líneas: qué creía el encargo, qué dice git, y con qué comando lo comprobaste.
Pregunta antes de continuar.

Las dos salidas cómodas están prohibidas:

- **No lo ejecutes «por si acaso»** → eso produce el trabajo duplicado.
- **No lo descartes «por si acaso»** → eso produce trabajo no hecho, y en silencio, que es peor
  porque nadie audita lo que se dio por hecho.

## Paso 4 — Solo entonces, trabaja

Con el estado ya anclado, ejecuta el encargo siguiendo las reglas del proyecto: rama + PR
(`main` está protegida), tests acompañando cualquier cambio en `core/`, y revisión
adversarial antes de mergear si es diseño o diff no trivial (`CLAUDE.md`).

Abre tu respuesta con una línea de anclaje, para que quede en el transcript:

> **Anclado:** <estado verificado> — comprobado con `<comando>` el <fecha>.
