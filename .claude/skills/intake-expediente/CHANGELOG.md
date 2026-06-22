# Changelog — intake-expediente

## 1.0 — 2026-06-22
- Versión inicial. Deposita ficheros en `00_Input/<fuente>/` vía el conector
  `expedientes-xl` (server-side) y dispara el evento `upload_*` en `_intake_log.jsonl`
  con SHA-256 por fichero, mediante el helper puro `scripts/traza.py`. Dedup de aviso
  sobre el log. El `IntakeManifest` (`_intake_hashes.json`) NO se reimplementa: se
  reconcilia en local con `core/`. No procesa por fuente (MIME/OCR) — eso es el pipeline.
