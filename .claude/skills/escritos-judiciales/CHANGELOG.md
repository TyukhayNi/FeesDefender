# CHANGELOG — `escritos-judiciales`

> Registro de cambios de la skill, en orden cronológico inverso (lo más reciente arriba).
> Formato ligero: fecha (AAAA-MM-DD) + qué cambió, una línea por cambio.

## 2026-07-03 — Formato v1.1 (decisiones de Nikolai 02-03/07)

- **Numeración de párrafos: número volado alineado por el punto.** En `hechos-cont`
  (bullets, `sub()`, `pDoc()` y la extensión OOXML/python-docx) se sustituye la
  francesa fija `left=0/hanging=425` por `lvlJc=right` + `suff=tab` + `left=0
  hanging=113` (0,2 cm), en el nivel de `numbering.xml` y en el `pPr` de cada
  párrafo. Motivo: con francesa fija el hueco número→texto varía con el nº de
  cifras y se rompe con 3 cifras (validado con 111 párrafos, W-02VND1 v24). +
  ítem de checklist de verificación visual con ordinales de 1/2/3 cifras.
- **Índice documental (`idx-docs`): mismo esquema volado**; separador tras
  `DOCUMENTO Nº XX` = dos puntos (`: `).
- **Regla universal nueva: prohibido el guion largo (em dash «—»)** en ninguna
  parte del escrito (cuerpo, encabezamiento, índice, notas al pie, otrosíes);
  capa dura al generar, `pase-de-estilo` solo como segunda red. + ítem de checklist.
- **Eliminada la tabla de cabecera** («Mi ref.» / «Juzgado»): el escrito arranca
  directamente con el encabezamiento al órgano. No reintroducir desde modelos
  antiguos.
- **Nomenclatura del órgano alineada con `CONVENCIONES_DESPACHO.md` §9** (reforma
  de Tribunales de Instancia): el encabezamiento nombra la **Sección** del
  Tribunal de Instancia (Civil por defecto en honorarios; puede ser Civil y de
  Instrucción, o cualquier otra sección por materia), no «JUZGADO DE PRIMERA
  INSTANCIA». + ítem de checklist.
- Frontmatter `version: "1.1"`. *Evidencia*: HANDOFF Cowork 2026-07-03.

## 2026-06-17 — Estilo de la casa (enganche)

- Puntero al contrato de estilo `data/_estilo/contrato_estilo.md` (capa 1) al inicio de «Patrones lingüísticos obligatorios» + ítem `pase-de-estilo` (capa 2) en el checklist de entrega. Añadida la convivencia obligatoria con `verificacion-anclada-fuente` (source-locked) antes de hornear citas/cifras en el `.docx` (único hueco que faltaba entre las productoras). *Evidencia*: `[ESTILO-DE-LA-CASA]` (PLAN.md / STATUS.md), commit `f65f371`.

## 2026-06-12 — Registro en expediente + mejora continua

- **Fase 0** (detección de `00_Input/_caso.md`: estructurado vs ad-hoc) y **guardado/registro** del `.docx` con `scripts/registrar_outputs.py` (manifiesto `<destino>/_index.md` + Navegación de `_caso.md`); destino por tipo de escrito.
- Telemetría de uso (`scripts/registrar_uso.py`), checklists pre/post (`templates/`) y revisión programada (`scripts/programar_revision.py`, escrito +15 días).
- Frontmatter `version: "1.0"`.

## 2026-06-03 — Inicio del registro

- Se inicia el registro de cambios. Skill que genera escritos procesales civiles en `.docx` (demandas, contestaciones, recursos, requerimientos, escritos de trámite) con el formato estándar del despacho, listo para firma.
