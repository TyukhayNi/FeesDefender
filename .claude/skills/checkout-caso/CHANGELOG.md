# Changelog — checkout-caso

## 1.0 — 2026-07-19
- **Frontmatter canónico** (identidad del despacho): bloque `metadata` (rol `transversal`,
  naturaleza `atomica`, `jurisdiction`/`area`, `version`, autor/organización/contacto, status
  `vigente`) + `license` de primer nivel. Formaliza la versión inicial de la skill (validada
  en producción: pilotos W-02VND1 / W-02THLJ). Sin cambio de comportamiento.
- Nota de compatibilidad con el MCP consolidado: el evento `case_checkout` en
  `_intake_log.jsonl` se escribe con `expedientes-xl:append_text` (nombre de tool estable en
  el consolidado; el movimiento de bytes lo hace rclone, no el MCP).
