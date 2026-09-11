# CHANGELOG — `viabilidad-prerelleno`

> Registro de cambios de la skill, en orden cronológico inverso (lo más reciente arriba).
> Formato ligero: fecha (AAAA-MM-DD) + qué cambió, una línea por cambio.

## 2026-09-11 — El filtro llega a las 88 preguntas y el semáforo en blanco se ve neutro (`MEJORAS #242`, `#243`)

- `assets/plantilla_informe_viabilidad.xlsx`: el `autoFilter` de `PREGUNTAS` pasa de `B3:M88` a
  **`B3:M103`**, y con él el nombre definido oculto `_xlnm._FilterDatabase`. Los 88 IDs llegan a la
  fila 103: **12 preguntas** —`tl_01`, los seis `esc_*` y los cinco `rec_*`— quedaban fuera del
  filtro que produce el guion de entrevista, así que marcar las 88 filas (la pieza P5 del mismo
  día) servía a medias.
- **El rango corto era un residuo, medido**: acababa exactamente en la última fila de la sección 8,
  y las secciones 9-11 se añadieron después sin ampliarlo. No protegía las filas de sección: ya
  había **siete** dentro del rango (29, 32, 44, 54, 58, 66, 83) y el cambio añade tres más del
  mismo tipo.
- `E21` (JURÍDICO) pierde el relleno sólido `FFFF0000` de su estilo base. Estaba **bajo** el
  formato condicional, así que con la celda vacía no se activaba ninguna regla y quedaba el rojo:
  un informe **sin valorar** enseñaba JURÍDICO en rojo puro, que ni siquiera es el rojo del
  semáforo (`FFC7CE`). `E22` no lo tenía, así que las dos filas vacías se veían distinto.
- **Ese rojo no cumplía ninguna función documentada**, medido: era la **única** celda del libro con
  ese relleno, ningún documento lo menciona y `render_informe.py` declara no tocar `E21`/`E22`.
- **Se cambió a nivel de zip, no con openpyxl**: cada entrada se copia byte a byte y solo se
  sustituyen tres cadenas en `sheet2.xml`, `workbook.xml` y `styles.xml`. Comprobado por lectura:
  **9 entradas idénticas, 3 modificadas**, ninguna otra. El `xf` tocado (índice 104) lo usa **una
  sola celda**, `E21`, así que el cambio no alcanza a ninguna otra; y el relleno 7 se queda en la
  tabla porque quitarlo renumeraría todos los demás.
- 5 tests nuevos, **3 rojos antes del cambio** y **4 mutantes dirigidos, los 4 muertos**: devolver
  el rojo, acortar el filtro, acortar **solo** el nombre definido, y apuntar `E21` al estilo 0 —que
  quita el relleno llevándose por delante el borde y la alineación—.

**Sigue sin verificarse, y no lo puede hacer una máquina:** que el desplegable se despliegue en
Excel y que la alerta salte al teclear un valor fuera de la lista.

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
- **`E22` replica `E21` de verdad**, y eso costó una corrección: la primera versión puso
  `showErrorMessage=False` afirmando que replicaba a `E21`, cuando `E21` tiene **`True`** — medí
  esa opción en la validación de la hoja PREGUNTAS y la extrapolé sin volver a mirar. También le
  faltaba la **fuente** (negrita con color) que llevan los `dxf` de `E21`, así que con `amarillo`
  en las dos, JURÍDICO salía en marrón y negrita y FINANZAS en negro normal. Las dos cosas
  corregidas el mismo día, con la fuente **copiada** del original en vez de reescrita.
- **Dos defectos preexistentes que la revisión destapó y NO se arreglan aquí**: `E21` en blanco se
  ve **rojo puro** por un estilo fijo bajo el condicional (`MEJORAS #242`), y el `autoFilter` de
  PREGUNTAS es `B3:M88` mientras los IDs llegan a la fila 103, así que el filtro que produce el
  guion de entrevista **deja 12 preguntas fuera** (`MEJORAS #243`) — lo que le quita la mitad del
  sentido a marcar las 88.
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
