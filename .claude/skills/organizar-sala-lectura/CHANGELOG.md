# Changelog — organizar-sala-lectura

## 1.1 — 2026-06-18
- Enrutado de identidad/PBC **por parte**: vendedor → `01. ACTIVACIÓN`; comprador →
  `03. OFERTAS` (subcarpeta por oferta si hay varias). `06. PBC` sobrevive **solo**
  para los Anexos 1 y 2 del vendedor (ya no es el cajón genérico de identidad).
- **Gate humano único (Paso 2.5):** propuesta visual (tarjeta/HTML) antes de copiar,
  con panel "requiere tu visto bueno" y enlace al original por fila; ejecuta solo tras OK.
- **Autonomía:** sin preguntas de permiso por-fichero; el diálogo por-llamada es ajuste
  del cliente Cowork. Un solo gate (la propuesta).
- **Enlaces:** la propuesta enlaza al original; los índices, a la copia canónica.
- (Slug de tipo en el nombre canónico: verificado que es decorativo; decisión de
  quitarlo pendiente de OK, no aplicada.)

## 1.0 — 2026-06-18
- Versión inicial. Lee `00_Input/01_Drive EV/` y copia (no destructivo) a
  `01_Procesado/Sala lectura Drive EV/` con taxonomía E&V, nombres canónicos e
  INDICE/CRONOLOGIA/manifiesto. Salida fuera de `00_Input` (no se re-ingiere ni la
  pisan los re-pulls). Alcance: solo `01_Drive EV`. Taxonomía alineada al canónico
  `TAXONOMIA_EV` (incluye `08. PENDIENTE DE CLASIFICAR`). El `_MANIFIESTO.md` guarda
  **sha256** (de los bytes, no el md5 del conector) + ruta original por documento,
  para dejar abierto el puente de reconciliación con el catálogo único.
