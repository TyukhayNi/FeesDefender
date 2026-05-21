---
description: Protocolo de cierre de sesión — STATUS.md + tests + memoria + commit propuesto
allowed-tools: Bash, Read, Edit, Write
---

Ejecuta el protocolo de cierre de sesión según STATUS.md §"Protocolo de cierre".

Fase 1 — Recopilar información (no ejecutar nada destructivo):

1. `python -m pytest -q --tb=no` desde la raíz del repo.
2. `git status` y `git diff --stat`.
3. Lee STATUS.md primeras 80 líneas para conocer el patrón de los resúmenes anteriores.

Fase 2 — Presentar en chat (sin tocar ficheros aún):

Comunica al usuario:
- Tests: ¿alguno nuevo o modificado? ¿estado esperado?
- Dead ends: ¿hubo callejón nuevo? → propuesta de entrada para `docs/DEAD_ENDS.md`.
- Dependencias: ¿algún fichero modificado activa la tabla de `docs/ARQUITECTURA.md`?
- STATUS.md: borrador del texto de la nueva sesión (fecha + resumen + tareas completadas + `[SIGUIENTE]`).
- Memoria: ¿hay decisión de arquitectura o patrón nuevo que guardar?
- Commit: mensaje propuesto.

Fase 3 — Tras "sí" del usuario:

Ejecuta los cambios:
- Edita STATUS.md (insertar nuevo bloque arriba, mover el anterior a "Anterior").
- Edita DEAD_ENDS.md si aplica.
- Edita ARQUITECTURA.md si aplica.
- Ejecuta `git add` + `git commit` con el mensaje aprobado.

Importante:
- No ejecutar `git push` salvo que el usuario lo pida explícitamente.
- Mantener la fecha en formato ISO (`2026-MM-DD`).
- Si la suite no está verde, parar y avisar antes de tocar STATUS.md.
