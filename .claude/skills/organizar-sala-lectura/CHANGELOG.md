# Changelog — organizar-sala-lectura

## 1.0 — 2026-06-18
- Versión inicial. Lee `00_Input/01_Drive EV/` y copia (no destructivo) a
  `01_Procesado/Sala lectura Drive EV/` con taxonomía E&V, nombres canónicos e
  INDICE/CRONOLOGIA/manifiesto. Salida fuera de `00_Input` (no se re-ingiere ni la
  pisan los re-pulls). Alcance: solo `01_Drive EV`. Taxonomía alineada al canónico
  `TAXONOMIA_EV` (incluye `08. PENDIENTE DE CLASIFICAR`). El `_MANIFIESTO.md` guarda
  **sha256** (de los bytes, no el md5 del conector) + ruta original por documento,
  para dejar abierto el puente de reconciliación con el catálogo único.
