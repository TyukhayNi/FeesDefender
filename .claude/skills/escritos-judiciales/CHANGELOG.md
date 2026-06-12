# CHANGELOG — `escritos-judiciales`

> Registro de cambios de la skill, en orden cronológico inverso (lo más reciente arriba).
> Formato ligero: fecha (AAAA-MM-DD) + qué cambió, una línea por cambio.

## 2026-06-12 — Registro en expediente + mejora continua

- **Fase 0** (detección de `00_Input/_caso.md`: estructurado vs ad-hoc) y **guardado/registro** del `.docx` con `scripts/registrar_outputs.py` (manifiesto `<destino>/_index.md` + Navegación de `_caso.md`); destino por tipo de escrito.
- Telemetría de uso (`scripts/registrar_uso.py`), checklists pre/post (`templates/`) y revisión programada (`scripts/programar_revision.py`, escrito +15 días).
- Frontmatter `version: "1.0"`.

## 2026-06-03 — Inicio del registro

- Se inicia el registro de cambios. Skill que genera escritos procesales civiles en `.docx` (demandas, contestaciones, recursos, requerimientos, escritos de trámite) con el formato estándar del despacho, listo para firma.
