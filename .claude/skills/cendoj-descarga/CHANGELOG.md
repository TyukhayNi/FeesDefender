# CHANGELOG — `cendoj-descarga`

> Registro de cambios de la skill, en orden cronológico inverso (lo más reciente arriba).
> Formato ligero: fecha (AAAA-MM-DD) + qué cambió, una línea por cambio.

## 2026-06-15 — Correcciones de sesión real + conversión/consolidado (v1.1)

- **Sesión real (W-02OMTG):** hash de 32 caracteres y extracción del `href` completo; validación de contenido en el JS de descarga (`NO-PDF` ante HTML de CAPTCHA o blob pequeño); verificación por ruta exacta en lugar de `glob` (montaje VirtioFS).
- **Paso 6-bis (CAPTCHA «Control > Descargas masivas»):** no se resuelve (política anti-bot); handoff al usuario. Filas nuevas en la tabla de errores frecuentes.
- **Verificación (Paso 8):** notas sobre encoding CIDFont, contraste de materia, holding/vigencia y divergencia ROJ vs año. Referencias privadas tratadas como LEADS.
- **Paso 8-bis (conversión PDF → Markdown)** y **Paso 9 (índice consolidado)**, con helpers nuevos `scripts/parse_pdf_to_md.py`, `scripts/consolidate_search_results.py` y `scripts/batch_pdf_to_md.sh`.
- **Paso 7:** se conserva el archivado en el expediente + registro (`registrar_outputs.py`); se añade como *nota opcional* la subida a Drive por tamaño (<150 / 150-300 / >300 KB). Frontmatter `version: "1.1"`.

## 2026-06-12 — Registro de jurisprudencia en el expediente

- **Paso 7-bis**: si la descarga es para un expediente, el PDF se copia a `05_Procedimiento/Jurisprudencia/` y se registra con `scripts/registrar_outputs.py` (`tipo: jurisprudencia`, `fuentes=[ROJ]`, `meta.ecli=ECLI`).
- Telemetría de uso (`scripts/registrar_uso.py`). Frontmatter `version: "1.0"`.

## 2026-06-03 — Inicio del registro

- Se inicia el registro de cambios. Skill para localizar y descargar sentencias y autos oficiales del CENDOJ (CGPJ) a partir de referencias parciales (ROJ, ECLI, tribunal/sección/fecha) o de bases privadas (Sepin, Lefebvre, vLex, Iberley).
