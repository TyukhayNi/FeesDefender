# Changelog — organizar-sala-maquina

Formato: una entrada por versión, la más reciente arriba. Cada entrada cita la
**evidencia** que motivó el cambio (uso real, delta borrador↔firmado, decisión
del letrado) — cultura source-locked del despacho.

## 1.2 — 2026-07-18

- **Reclasificación de `rol`: `output` → `procesado`.** La skill no produce un entregable
  jurídico (lo que denota `output`, p. ej. escritos `.docx`) sino artefactos internos de
  procesado (PDFs OCR + espejos MD). Se estrena el rol `procesado` del eje de pipeline de datos
  del expediente. Taxonomía a revalidar con el grafo de ecosistema (`docs/MEJORAS_FUTURAS.md`
  #50). Sin cambios de comportamiento.

## 1.0 — 2026-07-09

- Versión inicial. Envuelve el motor `core/sala_maquina.py` +
  `scripts/sala_maquina.py` (F1+F2, 49 tests verdes): OCR con OCRmyPDF sin tope
  de páginas, espejo Markdown, red de calidad `_cobertura.md`, idempotencia por
  sha256, guard `00_Input`/`90_Notas personales` intocables. Handoff (puntero)
  a `organizar-sala-lectura`. Diseño: `docs/superpowers/specs/2026-07-09-organizar-sala-maquina-design.md`.
