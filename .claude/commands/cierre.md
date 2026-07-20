---
description: Cierre de sesión — bitácora + PLAN + tests + memoria + rama/PR + poda
allowed-tools: Bash, Read, Edit, Write
---

Protocolo de cierre según `docs/FLUJO_GIT.md` §4. **`main` está protegida:** NUNCA
commit/push/merge directo a `main`; el trabajo entra por **rama → PR**.

## Fase 1 — Recopilar (sin tocar nada)

1. `python -m scripts.session_close` — pytest (rápido; completo si toca `core/anon/`) + los
   AVISOS (STATUS>400, PLAN ✅-sin-colapsar, ledger>30, trabajo-sin-publicar, PLAN↔git).
   **Leer todos los avisos**, no solo "tests verdes". (El `leak-scan` del CI NO corre pytest.)
2. Estado git: `git branch --show-current`, `git status -sb`, `git worktree list`.
3. Leer las ~15 primeras líneas de `docs/bitacora/AAAA.md` (patrón del bloque de cierre).

## Fase 2 — Presentar en el chat (sin tocar ficheros)

- Tests: ¿alguno nuevo o modificado? ¿estado esperado?
- Dead ends nuevos → propuesta de entrada para `docs/DEAD_ENDS.md`.
- ¿Algún fichero modificado activa la tabla de dependencias de `docs/ARQUITECTURA.md`?
- **Bitácora:** borrador del bloque (fecha ISO + resumen + `[SIGUIENTE]`) para
  `docs/bitacora/AAAA.md` (reciente primero) — **NO** para `STATUS.md`.
- **PLAN.md:** ítems a marcar `✅ + hash del PR` y colapsar al ledger `## Cerrados`; retirar
  la prosa de rama/worktree (git es su hogar).
- Memoria: ¿hay decisión de arquitectura o patrón nuevo que guardar?
- Commit: mensaje `tipo(scope): …`.

## Fase 3 — Tras el "sí" del usuario

- Editar `docs/bitacora/AAAA.md`, `PLAN.md`, y `DEAD_ENDS.md`/`ARQUITECTURA.md` si aplica.
- Commit ACOTADO: `git add <rutas>` (**NUNCA `-A`**) + `git commit -m "<mensaje>"`.
- Publicar: `git push -u origin <rama>` → `gh pr create` → esperar `leak-scan` verde.
  Nunca `push`/`commit` sobre `main`.

## Fase 4 — Integrar y podar (cuando el PR se mergea)

- `gh pr merge <n> --squash --delete-branch` (lo aprueba Nikolai).
- Podar local: `git switch main` → `git pull --ff-only` → `git branch -d <rama>`
  (si squash: `-D` **tras verificar** que el contenido está en `main`).
- Worktree creado por Code: `git worktree remove <ruta>` (desde la raíz, nunca desde dentro)
  + `git worktree prune`.
- **Devolver la raíz compartida a `main`.**

## Reglas

- `main` protegida: nada directo. Rama → PR → merge → poda.
- Fecha ISO `AAAA-MM-DD`. Suite roja → parar y avisar antes de tocar docs.
- Antes de borrar una rama: `gh pr list --head <rama> --state all` (¿MERGED?). Nunca `-D` a
  ciegas; rama con trabajo propio fuera de `main` → rescatar (cherry-pick + PR), no borrar.
- Modelo completo y recuperación: `docs/FLUJO_GIT.md`.
