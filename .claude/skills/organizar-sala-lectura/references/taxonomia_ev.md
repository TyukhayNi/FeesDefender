<!-- GENERADO desde data/_prompts/clasificador_ev.md + core/config.py::TAXONOMIA_EV por scripts/sync_taxonomia_skills.py — NO EDITAR A MANO -->

# Taxonomía E&V + criterio de clasificación (generado)

## Las categorías (set cerrado = `TAXONOMIA_EV`)

- `00. FOTOS`
- `01. ACTIVACIÓN`
- `03. OFERTAS`
- `04. ARRAS - ARRENDAMIENTOS`
- `05. FACTURACIÓN - FINANZAS`
- `06. PBC`
- `07. RECLAMACIONES`
- `08. PENDIENTE DE CLASIFICAR`

(No existe el `02`; se respeta la numeración de E&V.)

# Criterio de clasificación E&V — canon (fuente única)

> Canon consumido por `scripts/sync_taxonomia_skills.py` para generar la sección
> de clasificación de las skills. NO editar la copia generada en las skills; editar
> aquí. La lista cerrada de categorías vive en `core/config.py::TAXONOMIA_EV`.

## Enrutado de identidad / PBC POR PARTE
La identidad/PBC NO va toda a `06. PBC`. Se enruta por la parte, decidida LEYENDO el doc:
- Lado VENDEDOR (nota mercantil, nota simple/titularidad, titular real, poderes del
  vendedor, catastro) → `01. ACTIVACIÓN`.
  - EXCEPCIÓN: Anexos 1 y 2 de los vendedores (anexos PBC/KYC formales de E&V) → `06. PBC`.
- Lado COMPRADOR (identidad/KYC de compradores) → `03. OFERTAS` (subcarpeta por oferta si hay varias).

## Jerarquía de fecha del documento
(a) otorgamiento/firma en el cuerpo → (b) otra fecha inequívoca del contenido →
(c) fecha del nombre del fichero → (d) `0000-00-00`.
`mtime` NO es fuente; si se usa como aproximación, marcar `(*)` en CRONOLOGIA y _MANIFIESTO.

## Regla de ambigüedad
Lo ambiguo o ilegible → `08. PENDIENTE DE CLASIFICAR`. NUNCA forzar a otra categoría.

## Nombre canónico
`AAAA-MM-DD_descripcion.ext` — `descripcion`: ≤50 car., minúsculas, **guiones_bajos**,
SIN PII (sin nombres, DNI/NIE, direcciones). Describe el documento, no a las partes.
El tipo NO va en el nombre (la categoría vive en `INDICE.md`, no en carpetas).
