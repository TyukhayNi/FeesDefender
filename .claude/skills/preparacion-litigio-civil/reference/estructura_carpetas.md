# Estructura de carpetas tipo — Expediente de litigio civil

## Árbol base

```
[REF_INTERNA] - [TIPO_ESCRITO] - [OBJETO] - [CLIENTE]/
├── 00_PREPARACION/
│   ├── PREPARACION_[TIPO_ESCRITO].md
│   └── HECHOS_[TIPO_ESCRITO].md
├── 01_[FASE_PROCESAL_PREVIA]/
├── 02_[ACTUACION_CONTRARIA]/
├── 03_PRUEBA/
│   ├── DOC_01_[descriptor].pdf
│   ├── DOC_02_[descriptor].pdf
│   └── ...
├── 04_INTERNO/
│   ├── transcripcion_call_viabilidad.md
│   ├── modelo_despacho_[tipo].docx
│   └── notas_estrategia.md
└── 05_BORRADORES/
    ├── PREVIO_v1.docx
    ├── PREVIO_v2.docx
    ├── [TIPO_ESCRITO]_v1.docx
    └── ...
```

## Reglas

1. **Numeración por origen documental, no por tema.** Cada `0X_` corresponde a una fase procesal o fuente probatoria distinta.
2. **Documental con `DOC_NN_descriptor`.** Numeración correlativa coincidente con la del índice documental del escrito.
3. **Carpeta 04_INTERNO no se aporta nunca.** Reservada a borradores, transcripciones, modelos y notas.
4. **Borradores con versionado correlativo** (`v1`, `v2`, `v3`). Nunca sobrescribir versiones cerradas.
5. **Cliente trabajando en un documento del despacho**: conservar la versión de partida (p. ej. `PREVIO_v3.docx`) y reservar las posteriores al cliente.

## Variantes habituales por tipo de escrito

### Demanda con monitorio previo
```
01_MONITORIO/
02_OPOSICION/
03_PRUEBA/
```

### Contestación a demanda
```
01_DEMANDA/
02_REQUERIMIENTOS_PREVIOS/
03_PRUEBA/
```

### Recurso (apelación, casación)
```
01_PRIMERA_INSTANCIA/
02_SENTENCIA/
03_PRUEBA_ADICIONAL/
```

### Procedimiento iniciado sin antecedente procesal
```
01_REQUERIMIENTO_EXTRAJUDICIAL/
02_RESPUESTA_CONTRARIA/
03_PRUEBA/
```

### Requerimiento extrajudicial
```
01_ANTECEDENTES/
02_INTERCAMBIO_PREVIO/
03_PRUEBA/
```
