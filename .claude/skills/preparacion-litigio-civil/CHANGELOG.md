# CHANGELOG — `preparacion-litigio-civil`

> Registro de cambios de la skill, en orden cronológico inverso (lo más reciente arriba).
> Formato ligero: fecha (AAAA-MM-DD) + qué cambió, una línea por cambio.

## 2026-06-12 — Alineación con el expediente del despacho

- Scaffolding alineado a **`CASO_SUBDIRS`** + **`_caso.md` mínimo** (`tipo_expediente: particular`, sin campos E&V) vía el scaffolder canónico compartido `scaffold_caso.py`, común con el core E&V (no divergencia, garantizada por test). Maestros `PREPARACION_/HECHOS_` ahora en `02_Analisis/`.
- Reintegrada la metodología source-locked de la entrada anterior dentro del scaffold alineado (decisión 2.8 + sección 7 «Mapa de prueba» + campo «Anclaje» por Hecho).
- Registro de outputs (`scripts/registrar_outputs.py`), telemetría (`scripts/registrar_uso.py`) y revisión programada. Frontmatter `version: "1.0"`.

## 2026-06-03

- **Anclaje a fuente obligatorio** en la fijación de Hechos, en convivencia con `verificacion-anclada-fuente`: cada Hecho lleva estado 🟢 anclado / 🟡 pendiente de soporte / 🔴 vetado.
- Nueva sección **«Mapa de prueba»** en `PREPARACION_template.md` para los hechos 🟡 (pendientes de documento, con medio de prueba previsto); decisión cerrada 2.8; nuevos ítems en `CHECKLIST_DECISIONES.md`; campo «Anclaje» por Hecho en `HECHOS_template.md`.
- Verificación de jurisprudencia en CENDOJ antes de cerrar la preparación (encadenar `cendoj-descarga`).
- La «puerta» del paso 9 permite cerrar con hechos 🟡 (siempre con prueba prevista y mapa revisado); ningún Hecho en estado 🔴.
- Generador `scripts/scaffold_expediente.py` actualizado en consecuencia (validado). Nota en `reference/recurso.md`: en recurso no hay hechos nuevos, el estado 🟡 no aplica.
- Se inicia el registro de cambios de la skill.
