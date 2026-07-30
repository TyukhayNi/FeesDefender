---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-20
---

# Flujo de trabajo git — FeesDefender

> **Fuente única del flujo git y del protocolo de cierre.** `CLAUDE.md`, `STATUS.md` y el
> comando `/cierre` enlazan aquí; no repiten el procedimiento. Pensado también como manual
> llano para quien aún está cogiendo git.

## 1. El modelo en llano

- **Repositorio local** = la carpeta `C:\Users\tnm33\Dev\FeesDefender`. Esa carpeta, con su
  historial, ES el repo en tu ordenador. No hay otra copia "original" oculta con otro nombre.
- **`origin`** = la copia en GitHub (`github.com/TyukhayNi/FeesDefender`), la compartida.
  `push` sube tu trabajo; `pull` baja lo de otros.
- **`main`** = una **rama** (la versión buena/oficial), **no un lugar**. Existe por duplicado:
  `main` (local) y `origin/main` (GitHub), que se sincronizan. **`main` está protegida:** no
  admite escritura directa; todo entra por PR.
- **Rama** = una línea de trabajo paralela que nace de `main`. Las ramas son **globales al
  repo** (todos los worktrees las ven).
- **Worktree** = una carpeta de trabajo con **una** rama abierta (una mesa con un documento
  encima). La misma rama no puede estar abierta en dos worktrees a la vez.

**Regla de oro:** una mesa = una tarea = una rama; **la raíz compartida vive SIEMPRE en
`main`**, quieta. El trabajo ocurre en ramas/worktrees, nunca en la raíz sobre `main`.

## 2. Al abrir una sesión

- **Si Claude Code ya te puso en un worktree** (lo normal; lo ves en `.claude/worktrees/…`)
  → no haces nada de git: ya estás aislado.
- **Si estás en la raíz y sobre `main`** → abre una rama antes de tocar nada:
  `git switch -c <tipo>/<tema>` (p. ej. `docs/flujo-git`, `feat/split-f2`).
- Saber dónde estás: `git branch --show-current` y `git status -sb`.
- Comprobaciones del proyecto (atajo `/status`): `git log --oneline -5`,
  `python -m pytest -q --tb=no`, `python -m scripts.sync_sudespacho check-legacy`.

## 3. Durante la sesión

- Cambios en `core/` → siempre con tests en `tests/`.
- **Commits acotados:** `git add <rutas>` — **NUNCA `git add -A`** (en el árbol compartido
  arrastra ficheros de otras sesiones).
- Mensaje: `tipo(scope): descripción en imperativo` (convención en `docs/ARQUITECTURA.md`).

## 4. Cierre de sesión (lo ejecuta `/cierre`)

`main` está protegida → el cierre va por **rama → PR**, nunca commit directo a `main`.

1. **Recopilar:** `python -m scripts.session_close` (tests + AVISOS: STATUS>400,
   PLAN ✅-sin-colapsar, ledger>30, trabajo-sin-publicar, PLAN↔git). Leer todos los avisos.
2. **Presentar en el chat** (sin tocar ficheros): tests; dead ends nuevos; el **bloque de
   cierre** para `docs/bitacora/AAAA.md` (reciente primero, **no** STATUS); ítems de `PLAN.md`
   a marcar `✅ + hash del PR` y colapsar al ledger; memoria; mensaje de commit.
3. **Tras tu OK:** editar docs → commit acotado → `git push -u origin <rama>` →
   `gh pr create` → esperar `leak-scan` verde. (El PR lo mergea Nikolai.)
4. **Integrar y podar** (cuando el PR se mergea): `gh pr merge <n> --squash --delete-branch`
   → podar local (`git switch main`, `git pull --ff-only`, `git branch -d/-D`) → retirar el
   worktree (`git worktree remove` desde la raíz + `git worktree prune`) → **devolver la raíz
   a `main`**.

> `leak-scan` es el **único** check del CI — **no corre pytest**. Por eso `session_close`
> (pytest local) es la red real; córrelo antes de mergear, sobre todo si tocas guards o `.py`.

> **Gotcha del paso 4 (visto 2026-07-28, PR #151):** lanzado desde un worktree,
> `gh pr merge --squash --delete-branch` **falla su paso local** con
> `fatal: 'main' is already used by worktree at 'C:/Users/tnm33/Dev/FeesDefender'` —
> intenta volver a `main`, que la tiene tomada la raíz compartida. **El merge ya ha entrado
> en GitHub**: NO relanzarlo. Comprobar con `gh pr view <n> --json state,mergeCommit` y, si
> dice `MERGED`, borrar la rama remota aparte (`git push origin --delete <rama>`) y seguir
> con la poda local.

## 5. Poda e higiene (lo que más se olvida)

- **Podar es el paso 4 del cierre, no un fleco para luego.** Rama mergeada = rama podada.
- **Verificar antes de borrar:** el **squash-merge engaña a git** (una rama mergeada por
  squash no aparece como "merged"; `git branch -d` la rechaza). Antes de `-D`: comprueba que
  su contenido está en `main` (`gh pr list --head <rama> --state all` → ¿MERGED?). Rama con
  commit propio fuera de `main` → **se rescata** (cherry-pick + PR), no se borra.
- **La raíz compartida siempre en `main`.** Si la ves en otra rama o "rebasing", una sesión
  la dejó sucia → devolverla a `main`.

## 6. Recuperación (repo roto)

Ante cualquier lío: **mirar → entender → acción reversible → verificar.** Nunca forzar a ciegas.

- `git status` primero (¿rebase en curso? ¿ficheros sin resolver? ¿en qué rama?).
- Rebase a medias no deseado → `git rebase --abort` (vuelve al estado previo, sin pérdida).
- Terminal en un directorio raro (`C:\WINDOWS\system32`) → los git dan "not a git repository";
  `cd` al repo y repetir (no se ejecutó nada).
- No borrar en caliente un worktree que es el *cwd* vivo de una sesión (Windows lo bloquea);
  el directorio se borra tras cerrar esa sesión. **Si el `git worktree remove` de la Fase 4 ya
  se lanzó, el registro está limpio y `git worktree prune` es un no-op** — `prune` solo retira
  entradas cuyo directorio ya no existe, y aquí lo que sobra es el directorio, no la entrada.
  Que ese `remove` acabe en `Permission denied` es lo NORMAL al cerrar una sesión-en-worktree,
  no un fallo: desregistra y vacía el contenido, y solo deja la carcasa. Detalle y señales:
  `DEAD_ENDS.md` §«Worktree muerto como *cwd* de sesión».

---

Fundamento y gobernanza: `docs/GOBERNANZA_FUENTES_VERDAD.md`. Callejones: `docs/DEAD_ENDS.md`.
Guardarraíles del cierre: `scripts/session_close.py`.
