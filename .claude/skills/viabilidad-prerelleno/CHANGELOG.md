# CHANGELOG — `viabilidad-prerelleno`

> Registro de cambios de la skill, en orden cronológico inverso (lo más reciente arriba).
> Formato ligero: fecha (AAAA-MM-DD) + qué cambió, una línea por cambio.

## 2026-09-11 — El semáforo de FINANZAS existe (`MEJORAS #228`)

- `assets/plantilla_informe_viabilidad.xlsx`: `E22` gana el desplegable
  `verde/amarillo/rojo` y las tres reglas de formato condicional sobre **`E22:H22`**, con los
  mismos colores y el mismo alfa `FF` que `E21`. Se **añadió**, sin regenerar nada.
- El rango cubre los **dos** bloques combinados de la fila 22 (`E22:F22` + `G22:H22`), donde la 21
  tiene uno solo. Con un rango más corto, la mitad derecha se habría quedado sin color al lado de
  la izquierda pintada.
- `references/modelo_xlsx.md`: su línea de VIABILIDAD describía `E22` **como si ya tuviera**
  semáforo. Corregida, y con el aviso del rango.
- *Evidencia*: el CFO lee el semáforo por el color; un `amarillo` en texto plano junto a un
  JURÍDICO en verde se lee como «finanzas sin valorar», que es lo contrario de lo que dice.
  Verificado por lectura del binario antes y después (hojas, validaciones, protección, merges,
  TOTAL y las reglas de `E21`: nada cambió salvo lo añadido). 4 tests, **3 rojos de control
  positivo** contra la plantilla anterior.
- **No se endureció `E21`**: su validación acepta en silencio un literal fuera de la lista, y
  `E22` replica ese comportamiento en vez de mejorarlo. El hecho queda escrito en `MEJORAS #228`.
- **Tail: re-empaquetar y re-importar el `.skill` en Cowork** (fila #14 de `PLAN.md`).

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
  handoff del 2026-09-10. Cubierto por `tests/test_render_informe_viabilidad.py`, contra la plantilla
  real de `assets/`. **Control positivo, medido con las dos semillas (777 y 31337): 18 de los 26
  rojos** sobre `origin/main`, mismo resultado con las dos. Los del conteo, los del dominio de la
  columna —que enrojece por las marcas **ausentes**, porque la validación de Excel permite blancos,
  no por un literal inválido— y los catorce de la remediación de la R1. Los 8 verdes restantes son
  tests de conservación: pasaban antes y siguen pasando, y la R1 comprobó uno por uno que cada uno
  se pone rojo contra un mutante dirigido.
- `render_informe.py`: el `pendiente` explícito del JSON se **valida** contra `sí`/`no` (aceptando
  `si` sin tilde como grafía). Lo midió la R1: con `{"pendiente": ""}` la hoja salía con 87 de 88 y
  el comando decía «OK». La validación de la plantilla no cubre eso — es `list "sí,no"` pero con
  `allowBlank=True` y `showErrorMessage=False`.
- `render_informe.py`: el bloque de PREGUNTAS escribe por `set_rc` (hermano de `set_cell`), así que
  una celda combinada avisa y salta en vez de lanzar `AttributeError`; y una entrada del JSON que no
  sea un objeto se avisa en vez de reventar o de tragarse en silencio.
- **`MEJORAS #228` (semáforo `E22` FINANZAS) NO entra aquí**: al medirlo, la fila 22 resultó tener
  un layout distinto del de la 21 (`E22:F22` + `G22:H22`, dos bloques, contra el `E21:H21` único),
  así que no es el copia-pega que el backlog describía. No es **imposible** cablearlo sin tocar los
  merges —`E22:H22` vale como rango de formato condicional aunque no sea un bloque combinado—: lo
  que hay por delante es una decisión de layout y una verificación propia del binario. Va en su
  propio PR, con la medición anotada en la entrada.
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
