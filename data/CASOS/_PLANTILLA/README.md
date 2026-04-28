# Plantilla de caso

Estructura canónica de un expediente. **No tocar.** El sistema la copia /
recrea cuando se invoca `core.case_manager.ensure_case(case_id)`.

```
{case_id}/
├── 00_INPUT/                  # Documentos originales (sincronizados desde Drive)
├── 01_PROCESADO/              # Texto extraído + .md por documento
├── 02_ANALISIS/               # hechos_atomicos / prueba_indexada / contradicciones / scoring
├── 03_DECISION/               # viabilidad / decision_litigar
├── 04_OUTPUT_PREDEMANDA/      # requerimiento previo / borrador de demanda
├── 05_PROCEDIMIENTO/          # Escritos posteriores y resoluciones
├── 06_AI_COWORK/              # Notas de trabajo con LLM, logs de pipeline
└── 90_NOTAS_PERSONALES/       # Zona del abogado, NO la toca el sistema
```
