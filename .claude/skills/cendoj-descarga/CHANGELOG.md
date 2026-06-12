# CHANGELOG — `cendoj-descarga`

> Registro de cambios de la skill, en orden cronológico inverso (lo más reciente arriba).
> Formato ligero: fecha (AAAA-MM-DD) + qué cambió, una línea por cambio.

## 2026-06-12 — Registro de jurisprudencia en el expediente

- **Paso 7-bis**: si la descarga es para un expediente, el PDF se copia a `05_Procedimiento/Jurisprudencia/` y se registra con `scripts/registrar_outputs.py` (`tipo: jurisprudencia`, `fuentes=[ROJ]`, `meta.ecli=ECLI`).
- Telemetría de uso (`scripts/registrar_uso.py`). Frontmatter `version: "1.0"`.

## 2026-06-03 — Inicio del registro

- Se inicia el registro de cambios. Skill para localizar y descargar sentencias y autos oficiales del CENDOJ (CGPJ) a partir de referencias parciales (ROJ, ECLI, tribunal/sección/fecha) o de bases privadas (Sepin, Lefebvre, vLex, Iberley).
