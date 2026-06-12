# Estructura de carpetas — Expediente de litigio civil (particular)

El expediente de un particular usa **la misma estructura que un asunto E&V**
(`CASO_SUBDIRS`), montada por el scaffolder canónico compartido `scaffold_caso.py`.
La diferencia es solo el `_caso.md` (mínimo, `tipo_expediente: particular`, sin
campos E&V) y que `00_Input` no lleva las subcarpetas de intake automático de E&V
(solo intake manual). Las skills procesales no distinguen E&V de particular: leen
y escriben igual.

## Árbol base

```
<ruta destino>/
├── 00_Input/
│   └── _caso.md            ← maestro del expediente (tipo_expediente: particular)
├── 01_Procesado/           ← documental tratada / extraída
├── 02_Analisis/
│   ├── PREPARACION_[TIPO].md   ← maestro estratégico (única fuente de verdad)
│   └── HECHOS_[TIPO].md        ← redacción literal por Hecho
├── 03_Decision/
├── 04_Output predemanda/   ← requerimientos extrajudiciales
├── 05_Procedimiento/       ← escritos generados (demanda, contestación…); se registran en _caso.md
├── 06_Anonimizado/
├── 07_AI cowork/
└── 90_Notas personales/    ← work-product interno; NUNCA se aporta ni se registra
```

## Reglas

1. **`_caso.md` es el maestro del expediente.** Lo crea el scaffolder; los escritos generados se registran en su sección `## Navegación` y en `05_Procedimiento/_index.md` (vía `registrar_outputs.py`).
2. **Maestros estratégicos en `02_Analisis/`.** `PREPARACION_[TIPO].md` (decisiones) y `HECHOS_[TIPO].md` (redacción literal por Hecho).
3. **Documental con `DOC_NN_descriptor`.** Numeración correlativa coincidente con el índice documental del escrito; intake en `00_Input/`, tratada en `01_Procesado/`.
4. **`90_Notas personales/` no se aporta nunca** y no se registra: borradores, transcripciones, modelos y notas internas.
5. **Escritos en `05_Procedimiento/`** con versionado correlativo si procede (`_v2`, …); nunca sobrescribir una versión cerrada (Word bloquea el fichero abierto → guardar `_v2` y avisar).

## Sobre la fase procesal previa

La estructura es fija (no se renombran carpetas por fase). El antecedente procesal
—monitorio previo, requerimiento extrajudicial, sentencia de primera instancia en
apelación, etc.— se archiva como documental en `00_Input/` (intake manual) y se
referencia desde `PREPARACION_[TIPO].md`, no mediante carpetas `01_/02_` renombradas.
