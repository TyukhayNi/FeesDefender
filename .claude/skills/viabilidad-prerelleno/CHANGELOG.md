# CHANGELOG — `viabilidad-prerelleno`

> Registro de cambios de la skill, en orden cronológico inverso (lo más reciente arriba).
> Formato ligero: fecha (AAAA-MM-DD) + qué cambió, una línea por cambio.

## 2026-07-28 — Nombre de salida acortado (MAX_PATH de Office)

- `scripts/render_informe.py`: cuando no se pasa `--salida`, el nombre derivado usa **solo el ID GO**
  (`Informe viabilidad LLM - <id_go>.xlsx`) en vez del `case_id` completo. El fichero ya vive en
  `<case_id>/02_Analisis/`, así que repetir el `case_id` no añadía información y se pasaba de los 260
  caracteres que tolera Office: el informe LLM de `W-02TH0W` medía **298** y Excel no lo abría. Mismo
  criterio que `core.case_manager._compose_informe_filename`.
- `scripts/render_informe.py`: aviso por `stderr` si la ruta de salida supera los 240 caracteres.
- `SKILL.md` §(render): el comando de ejemplo pasa `<id_go>`, no `<case_id>` — es la línea que se
  copia literalmente al ejecutar, así que sin este cambio el acortamiento no llegaba a la práctica.
- *Evidencia*: `[MAXPATH-INFORME]` (PLAN.md), `MEJORAS #100`, entrada de `docs/DEAD_ENDS.md`.
  **Tail: re-empaquetar y re-importar el `.skill` en Cowork** (desde la raíz, no desde un worktree).
