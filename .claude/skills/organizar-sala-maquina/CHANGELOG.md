# Changelog — organizar-sala-maquina

Formato: una entrada por versión, la más reciente arriba. Cada entrada cita la
**evidencia** que motivó el cambio (uso real, delta borrador↔firmado, decisión
del letrado) — cultura source-locked del despacho.

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
