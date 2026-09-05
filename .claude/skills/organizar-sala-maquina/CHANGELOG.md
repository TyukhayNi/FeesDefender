# Changelog — organizar-sala-maquina

Formato: una entrada por versión, la más reciente arriba. Cada entrada cita la
**evidencia** que motivó el cambio (uso real, delta borrador↔firmado, decisión
del letrado) — cultura source-locked del despacho.

## 1.6 — 2026-09-06

- **Un fichero, un espejo (MEJORAS #147, vía A).** El mismo documento (mismo `sha256`) en dos
  carpetas del cliente ya no produce dos OCR ni dos MD: el primero del inventario es el titular
  del espejo y la copia sale en `_cobertura.md` con método `duplicado`, el estado del titular y
  la ruta del espejo único en la nota; el titular anota «también en …». **Evidencia:** W-02Q38C,
  51 espejos para 49 contenidos, y el 75º cierre contó como «nuevos» dos documentos que el
  expediente ya tenía. Lo que NO cubre: el mismo documento re-descargado con bytes distintos
  (vía B, sigue en `MEJORAS #147`).
- **Para quien dirige la skill:** el preview puede mostrar `duplicados: N`; no hace falta hacer
  nada con ellos, pero al leer la sala de lectura conviene saber que ese documento vive en más de
  una carpeta de E&V (la nota del titular lo dice).

## 1.5 — 2026-09-05

- **Los `.doc` dejan de ser ilegibles: ruta `ofimatica`.** `.doc`, `.dot`, `.odt`, `.ott`,
  `.ppt`, `.pps`, `.pptx` y `.odp` se convierten a PDF con LibreOffice headless
  (`core/ofimatica_a_pdf.py`) y siguen el camino PDF: buscable persistido en `01_OCR/`, MD en
  `03_MD/`, método `ofimatica` en `_cobertura`. Sin LibreOffice, la fila es `sin_soporte` **con
  la causa en la nota** y `plan`/`apply` avisan antes de la corrida. **Evidencia:** en W-02MA0R
  la demanda del ordinario existía solo como `.doc` y ningún LLM podía leerla (`MEJORAS #61`,
  acción 10 del informe de Codex sobre el alta). Plan y adjudicación:
  `docs/superpowers/plans/2026-09-05-accion-10-ofimatica-en-la-sala-de-maquina.md`.
- **Lo que cambia para quien dirige la skill:** el preview puede mostrar una línea `ofimatica: N`
  y un aviso «LibreOffice (soffice) no encontrado» — en ese caso, o se instala antes de `apply`,
  o se acepta que esos documentos queden ilegibles y se le dice al abogado.
- El `version` del frontmatter decía `1.3` desde la 1.4: se alinea aquí con el changelog.

## 1.4 — 2026-08-02

- **El MD de un segmento ya no lleva sha8 en el nombre (PR #193).** El bloque de layout
  prometía `03_MD/{slug__sha8}.md` «uno por documento lógico», y eso dejó de ser cierto: el
  segmento de un bundle se nombra ahora por su **identidad persistente**,
  `{bundle}__{dNN}_{TIPO}.md`. El documento suelto sigue con `{slug__sha8}`. **Evidencia:** el
  sha seguía a un artefacto derivado —el PDF ya recortado—, así que re-OCR-izar renombraba todo
  y el reproceso **añadía** una generación en vez de sustituirla; medido, 5 documentos
  duplicados y 21 ficheros excedentes en 2 casos reales. Contrato:
  `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md` (rev. 4).
- **Lo que esto cambia para quien dirige la skill desde Cowork:** nada en el flujo, pero al leer
  `02_Documentos/<bundle>/` los nombres ya no cambian entre corridas — si ves dos versiones del
  mismo documento, es daño anterior al PR #193 y se archiva solo al republicar el bundle.

## 1.3 — 2026-07-21

- **Split de bundles multi-documento (Fase F2, PR #109).** Un PDF que reúne varios
  documentos (un *bundle*) se parte por HOJA EN BLANCO sobre el PDF ya buscable —entre el
  OCR y el MD— generando un MD por documento lógico en vez de un MD gigante. `plan`
  pre-detecta los bundles y deja un `_segmentacion.md` editable; el letrado lo ajusta y
  `apply` corta (respeta el editado; `--force` lo regenera). Los segmentos aterrizan en
  `02_Documentos/{bundle}/` con su propio MD; la cobertura y el estado idempotente pasan a
  granularidad de documento lógico. Passthrough robusto si la detección falla (no pierde el
  documento). Consumo por `organizar-sala-lectura` como documento compuesto = follow-on
  (`MEJORAS #79`). Evidencia: sesión VALERO (bundles escaneados corridos: cédula/auto/factura
  y encargo/arras/facturas E&V). Plan `docs/superpowers/plans/2026-07-14-split-sala-maquina.md`.

## 1.2 — 2026-07-18

- **Reclasificación de `rol`: `output` → `procesado`.** La skill no produce un entregable
  jurídico (lo que denota `output`, p. ej. escritos `.docx`) sino artefactos internos de
  procesado (PDFs OCR + espejos MD). Se estrena el rol `procesado` del eje de pipeline de datos
  del expediente. Taxonomía a revalidar con el grafo de ecosistema (`docs/MEJORAS_FUTURAS.md`
  #50). Sin cambios de comportamiento.

## 1.0 — 2026-07-09

- Versión inicial. Envuelve el motor `core/sala_maquina.py` +
  `scripts/sala_maquina.py` (F1+F2, 49 tests verdes): OCR con OCRmyPDF sin tope
  de páginas, espejo Markdown, red de calidad `_cobertura.md`, idempotencia por
  sha256, guard `00_Input`/`90_Notas personales` intocables. Handoff (puntero)
  a `organizar-sala-lectura`. Diseño: `docs/superpowers/specs/2026-07-09-organizar-sala-maquina-design.md`.
