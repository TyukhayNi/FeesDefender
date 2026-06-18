# Taxonomía E&V + reglas de nombre canónico

Cárgala al clasificar (paso 2 del procedimiento) y al construir el nombre canónico
(paso 3).

## Las 8 categorías (carpetas de 02_Sala lectura/)

Set cerrado (igual que `TAXONOMIA_EV` del motor local). El clasificador debe
devolver EXACTAMENTE una:

- `00. FOTOS` — imágenes (.jpg .jpeg .png .heic .webp .gif .bmp .tiff).
- `01. ACTIVACIÓN` — encargo, captación, exclusiva, exposé, hoja de visita.
- `03. OFERTAS` — oferta, contraoferta.
- `04. ARRAS - ARRENDAMIENTOS` — arras, reserva, señal, arrendamiento, alquiler.
- `05. FACTURACIÓN - FINANZAS` — factura, honorarios, abono, minuta, justificante de pago.
- `06. PBC` — DNI, NIE, pasaporte, nota simple, titularidad, prevención de blanqueo.
- `07. RECLAMACIONES` — burofax, requerimiento, reclamación, incumplimiento.
- `08. PENDIENTE DE CLASIFICAR` — todo lo ambiguo o ilegible. NUNCA forzar a otra categoría.

(No existe `02`; se respeta la numeración de E&V.)

## Cómo clasificar

1. Si es imagen por extensión → `00. FOTOS`.
2. Si el contenido o el nombre casan claramente con los keywords de arriba → esa categoría.
3. En duda → `08. PENDIENTE`. Es preferible un pendiente honesto a un misrouting.

## Nombre canónico

`AAAA-MM-DD_tipo_descripcion.ext`

- `tipo` (slug): foto · activacion · oferta · arras · factura · pbc · reclamacion · pendiente.
- `descripcion`: slug ≤50 car., minúsculas, guiones, **SIN PII** (sin nombres de
  personas, DNI/NIE, direcciones). Describe el documento, no a las partes
  (p. ej. `hoja-encargo`, `burofax`, `factura-honorarios`).
- `AAAA-MM-DD`: fecha del documento; si no consta, `0000-00-00`.

Ejemplos: `2024-03-12_activacion_hoja-encargo.pdf`, `2024-05-02_reclamacion_burofax.pdf`.
