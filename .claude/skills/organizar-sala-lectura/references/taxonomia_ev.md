# Taxonomía E&V + reglas de nombre canónico

Cárgala al clasificar (paso 2 del procedimiento) y al construir el nombre canónico.

## Las 8 categorías (carpetas de `01_Procesado/Sala lectura Drive EV/`)

Set cerrado (igual que `TAXONOMIA_EV` del motor local). El clasificador debe
devolver EXACTAMENTE una:

- `00. FOTOS` — imágenes (.jpg .jpeg .png .heic .webp .gif .bmp .tiff).
- `01. ACTIVACIÓN` — encargo, captación, exclusiva, exposé, hoja de visita. **+
  identidad del lado VENDEDOR** (ver «Enrutado de identidad por parte»).
- `03. OFERTAS` — oferta, contraoferta. **+ identidad/KYC del lado COMPRADOR** (ver
  «Enrutado de identidad por parte»).
- `04. ARRAS - ARRENDAMIENTOS` — arras, reserva, señal, arrendamiento, alquiler.
- `05. FACTURACIÓN - FINANZAS` — factura, honorarios, abono, minuta, justificante de pago.
- `06. PBC` — **SOLO los Anexos 1 y 2 de los vendedores** (los anexos PBC/KYC
  formales de E&V). Ya **NO** es el cajón genérico de identidad (ver enrutado abajo).
- `07. RECLAMACIONES` — burofax, requerimiento, reclamación, incumplimiento.
- `08. PENDIENTE DE CLASIFICAR` — todo lo ambiguo o ilegible. NUNCA forzar a otra categoría.

(No existe el `02`; se respeta la numeración de E&V.)

## Enrutado de identidad / PBC por PARTE

La identidad/PBC **no va toda a `06. PBC`**. Se enruta según a qué parte pertenece, y
**la parte se decide LEYENDO el documento**, no por el nombre del fichero:

- **Lado VENDEDOR** — identidad del propietario y de la sociedad vendedora: nota
  mercantil, nota simple / titularidad, titular real, poderes del vendedor, catastro
  → **`01. ACTIVACIÓN`**.
  - **EXCEPCIÓN:** los **Anexos 1 y 2 de los vendedores** (anexos PBC/KYC formales de
    E&V) → **`06. PBC`**. Esta carpeta sobrevive **solo** para estos anexos.
- **Lado COMPRADOR** — identidad / KYC de compradores → **`03. OFERTAS`**.
  - Si hay **más de una oferta**, crea subcarpetas por oferta dentro de `03. OFERTAS/`
    y mete la PBC de cada comprador en la subcarpeta de **su** oferta:

```
03. OFERTAS/
├── Oferta 1/
│   ├── 2024-05-02_oferta-de-compra.pdf
│   └── 2024-05-02_kyc-comprador.pdf      ← identidad del comprador de esa oferta
└── Oferta 2/
    └── ...
```

## Cómo clasificar

1. Imagen por extensión → `00. FOTOS`.
2. **Identidad/PBC → enrútala POR PARTE** (sección anterior); no la mandes a
   `06. PBC` por defecto. Solo los Anexos 1 y 2 del vendedor van a `06. PBC`.
3. Si el contenido o el nombre casan con los keywords de una categoría → esa categoría.
4. En duda → `08. PENDIENTE DE CLASIFICAR`. Mejor un pendiente honesto que un misrouting.

## Nombre canónico

`AAAA-MM-DD_descripcion.ext`

El **tipo NO va en el nombre**: ya lo indica la carpeta canónica donde se archiva el
fichero (`01. ACTIVACIÓN/`, `07. RECLAMACIONES/`, …), así que repetirlo en el nombre
sería redundante.

- `descripcion`: slug ≤50 car., minúsculas, guiones, **SIN PII** (sin nombres de
  personas, DNI/NIE, direcciones). Describe el documento, no a las partes
  (p. ej. `hoja-encargo`, `nota-mercantil`, `titular-real`, `kyc-comprador`, `burofax`).
- `AAAA-MM-DD`: fecha del documento; si no consta, `0000-00-00`.

Ejemplos (cada uno dentro de su carpeta de tipo): `2024-03-12_hoja-encargo.pdf` (en
`01. ACTIVACIÓN/`), `2024-05-02_burofax.pdf` (en `07. RECLAMACIONES/`),
`2024-04-10_nota-mercantil.pdf` (identidad del vendedor → `01. ACTIVACIÓN/`).
