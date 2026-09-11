# CHANGELOG — `viabilidad-prerelleno`

> Registro de cambios de la skill, en orden cronológico inverso (lo más reciente arriba).
> Formato ligero: fecha (AAAA-MM-DD) + qué cambió, una línea por cambio.

## 2026-09-11 — El render marca las 88 filas, no solo las que trae el JSON

- `scripts/render_informe.py`: la hoja `PREGUNTAS` se recorre desde `build_id_row_map(preg)` —el
  cuestionario entero— en vez de desde `d["preguntas"]`. Toda pregunta sin respuesta sale con
  `¿PENDIENTE ENTREVISTA?` (col M) = `sí`, que es lo que filtra el guion de entrevista. Un
  `pendiente` explícito del JSON sigue ganando, y el aviso por `qid` desconocido se conserva.
- `SKILL.md` §3: el contrato ya decía que las no resueltas van a `sí`; lo que fallaba es que el
  marcado dependía de que **el JSON enumerase las 88**. Ahora se dice explícitamente que en
  `preguntas` van solo las que se resuelven, y el ejemplo deja de mostrar una entrada cuyo único
  contenido era `{"pendiente": "sí"}`.
- *Evidencia*: medido dos veces el 2026-09-10 sobre casos reales — **51 de 88** y **70 de 88** filas
  marcadas. `PLAN.md` fila #28 (`[SIGUIENTE-APERTURA-MENOS-DECISIONES]`), pieza P5; propuesta P5 del
  handoff del 2026-09-10. Cubierto por `tests/test_render_informe_viabilidad.py` (8 tests contra la
  plantilla real de `assets/`, con control positivo: 2 de ellos rojos antes del arreglo).
- **`MEJORAS #228` (semáforo `E22` FINANZAS) NO entra aquí**: al medirlo, la fila 22 resultó tener
  un layout distinto del de la 21 (`E22:F22` + `G22:H22`, dos bloques, contra el `E21:H21` único),
  así que no es el copia-pega que el backlog describía. Va en su propio PR, con la medición anotada
  en la entrada.
- **Tail: re-empaquetar y re-importar el `.skill` en Cowork** (fila #14 de `PLAN.md`).

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
