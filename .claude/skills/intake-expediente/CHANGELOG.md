# Changelog — intake-expediente

## 1.1 — 2026-06-22
- **Gate único de clasificación (Paso 2):** antes de mover nada, propone por chat la
  clasificación de cada fichero (fuente `00_Input/<sub>` + nombre canónico + evento, con
  duplicados/0-byte/sin-fecha marcados) y **espera OK**; tras la aprobación ejecuta de una
  pasada **sin más preguntas**.
- **Autonomía:** sin preguntas de aclaración por-fichero; defaults pre-decididos (el original
  en `_ingest/` se deja intacto, no se pregunta ni se borra). Nota: el diálogo de permiso
  por-llamada del conector MCP es ajuste del cliente ("Permitir siempre"), no de la skill.

## 1.0 — 2026-06-22
- Versión inicial. Deposita ficheros en `00_Input/<fuente>/` vía el conector
  `expedientes-xl` (server-side) y dispara el evento `upload_*` en `_intake_log.jsonl`
  con SHA-256 por fichero, mediante el helper puro `scripts/traza.py`. Dedup de aviso
  sobre el log. El `IntakeManifest` (`_intake_hashes.json`) NO se reimplementa: se
  reconcilia en local con `core/`. No procesa por fuente (MIME/OCR) — eso es el pipeline.
