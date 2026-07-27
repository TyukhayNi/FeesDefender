---
tipo: handoff
estado: consumido
creado: 2026-07-27
origen: sesión Cowork (chat) — diagnóstico manual de core/anon/ocr.py + core/sala_maquina.py durante caso W-02MA0R
destino: sesión Claude Code — verificar contra el código real y decidir si se incorpora a docs/MEJORAS_FUTURAS.md
consumido_por: "PR #134 — docs(mejoras): #90/#91 (huecos de OCR en sala de máquina) tras verificar el handoff [SM-OCR-01..03]"
---

# HANDOFF — Tres huecos de OCR detectados en sala de máquina (motor)

> Andamio de traspaso (efímero). El contenido durable (si se confirma) va a
> `docs/MEJORAS_FUTURAS.md`, no a este fichero. Marcar `estado: consumido` +
> `consumido_por:` cuando la sesión de Claude Code decida qué hacer con esto.

## Veredicto de la revisión (2026-07-27, sesión Claude Code)

Los tres hallazgos se releyeron contra el estado actual de `core/anon/ocr.py` y
`core/sala_maquina.py` (sin drift: las citas de línea del handoff son exactas) y
se verificaron **en vivo** contra ocrmypdf 17.4.2 y las propias funciones del
repo, no solo por lectura.

| Hallazgo | Veredicto | Destino |
|---|---|---|
| `[SM-OCR-01]` sanidad de Tesseract/tessdata | **Parcialmente refutado** — `scripts/health_check.py` sí comprueba binarios (104-118) e idiomas `spa/cat/rus` (121-142), y `ocr_disponible()` no es el preflight de la sala de máquina (único consumidor: `core/anon/api.py:263`). Resto real: `apply` no tiene preflight del motor OCR. | `MEJORAS_FUTURAS.md` **#91** |
| `[SM-OCR-02]` `--skip-text` y falso `ok` | **CONFIRMADO y agravado.** Confirmado el diagnóstico de Nikolai: es el más serio de los tres. Corrección: `--skip-text` opera por página (no por documento); el hueco es *sub*-página. Agravante no visto en el handoff: un escaneo con sello LexNET (~228 char/pág) supera `_texto_suficiente` y **nunca llega a OCRmyPDF**. Medido: `--skip-text` 31 chars vs `--redo-ocr` 295 sobre la misma página; `ocr_quality` devuelve `ok` a 8/20/40 págs con cero cuerpo recuperado. | `MEJORAS_FUTURAS.md` **#90** |
| `[SM-OCR-03]` `DecompressionBombError` (PIL) | **REFUTADO.** Premisa falsa (PIL sí se usa: `core/anon/imagen_a_pdf.py:43`, `core/local_organizer.py:179`; guardarraíles activos en Pillow y en ocrmypdf `--max-image-mpixels`) y consecuencia falsa (falla ruidoso: `sin_soporte`/`empty` con nota en `_cobertura.md`, no silencioso). | Descartado — motivo registrado al cierre de **#90** |

Nada promovido a `PLAN.md`. El disparador de #90 se deja explícitamente
condicionado al paso 0 (detector read-only), porque el fallo es silencioso por
construcción y esperar "un caso real que lo dispare" no funcionaría.

## Encargo (prompt de arranque)

ENCARGO: antes de tocar `docs/MEJORAS_FUTURAS.md`, relee tú mismo, en el estado
ACTUAL del repo (puede haber cambiado desde 2026-07-27), estos dos ficheros
completos:
- core/anon/ocr.py
- core/sala_maquina.py

Para cada uno de los tres hallazgos [SM-OCR-01], [SM-OCR-02], [SM-OCR-03] (ver
abajo):
1. Confirma si el código citado sigue existiendo tal cual (líneas, nombres de
   función, comportamiento por defecto) o si ya cambió/se arregló.
2. Si sigue vigente, decide si merece entrada en `docs/MEJORAS_FUTURAS.md` con
   el formato ya usado ahí (`## N. Título`, `**Estado actual.**`,
   `**Mejora propuesta.**`, `**Justificación de no aplicarlo ahora.**`,
   `**Coste estimado.**`) — mira las entradas existentes para calibrar el tono
   y el nivel de detalle.
3. Si el hallazgo [SM-OCR-02] (el de `--skip-text` a nivel de página) te parece
   más grave que los otros dos, dilo explícitamente — es el más serio porque
   puede producir un falso "ok" en la cobertura sin que nadie lo note.
4. NO promuevas nada a `PLAN.md` — solo backlog en `MEJORAS_FUTURAS.md`, salvo
   que tú decidas que hay un disparador concreto que lo justifique (revisa la
   regla de promoción en `CLAUDE.md`).
5. Si algún hallazgo te parece equivocado o ya no aplica, descártalo y explica
   por qué en vez de incorporarlo.

Trabaja en rama + PR (main protegida), no toques código de producción — esto es
solo documentación de backlog. Al terminar, marca este handoff `estado: consumido`
con `consumido_por:` apuntando a tu PR.

## Contexto

Durante la preparación de la audiencia previa del caso **W-02MA0R** (fuera de
FeesDefender: expediente ad-hoc, sin estructura `00_Input/`), tuve que OCR'ear a
mano 32 PDFs en un sandbox sin la skill `organizar-sala-maquina` operativa (esa
skill exige el layout FeesDefender). Al comparar mi experiencia manual con
`core/anon/ocr.py` y `core/sala_maquina.py` **del repo real** (leído en sesión de
Cowork, solo lectura), detecté tres huecos. **No verificado con tests ni en vivo
contra un caso FeesDefender real** — es lectura de código, sin ejecutar nada.

## Hallazgos (etiquetas `[SM-OCR-xx]`)

- **`[SM-OCR-01]` Sin verificación de sanidad de Tesseract/tessdata.**
  `core/anon/ocr.py::ocr_disponible()` (línea 129-135) solo comprueba que el
  paquete Python `ocrmypdf` sea importable. No hay chequeo de que el binario
  Tesseract tenga los idiomas `spa+cat+rus` instalados ni sus ficheros de
  soporte (`configs/`, `tessconfigs/`, `pdf.ttf`). Un entorno mal instalado
  falla como `OCRError` genérica (línea 125-126), sin diagnóstico específico.

- **`[SM-OCR-02]` `--skip-text` es el default y opera a nivel de documento, no de
  página — el más serio de los tres.** `ocr.py` línea 100-103: si
  `redo_ocr=False` (el default), siempre se pasa `skip_text=True`. Esto hace que
  ocrmypdf trate como "ya tiene texto" cualquier página con algo de texto
  embebido (un sello, una cabecera) y NO le aplique OCR real al resto de esa
  página. La validación de calidad `ocr_quality()` (línea 88-102) opera sobre
  el documento **entero** (densidad media char/página, ratio de gibberish,
  longitud total) — una sola página mal OCR'eada dentro de un documento largo
  puede diluirse en el promedio y el documento seguir saliendo `ok`.
  Además, el flag `--force` de la skill (`_ocr_y_extraer` en
  `core/sala_maquina.py`, línea 446-485) solo invalida el caché de sha256 para
  reprocesar desde cero — **nunca** pasa `redo_ocr=True` a `ocr_pdf()`. No existe
  hoy ningún mecanismo, automático o manual vía CLI, para forzar OCR de una
  página concreta dentro de un documento ya procesado.

- **`[SM-OCR-03]` Sin manejo de `DecompressionBombError` (PIL) en imágenes
  grandes.** Grep vacío de `PIL`/`MAX_IMAGE_PIXELS`/`pdftoppm` en todo `core/` y
  `scripts/`. Si ocrmypdf revienta por una imagen embebida sobredimensionada,
  cae en el `except Exception` genérico de `ocr.py` (línea 125-126) →
  `OCRError` → el documento queda `empty` en la cobertura. La única mitigación
  indirecta existe si `--vision` está activo Y cableado
  (`sala_maquina.py` línea 460-473): en ese caso se reintenta vía `pypdfium2` +
  transcripción de visión, un camino distinto al que usé yo (`pdftoppm` +
  tesseract directo sobre la página) pero con el mismo espíritu de esquivar el
  renderizador que falla. Sin `--vision` cableado, no hay red de seguridad.

## Qué NO es este handoff

- No es un diagnóstico verificado con tests ni con una corrida real del CLI
  `scripts.sala_maquina` sobre un caso FeesDefender.
- No propone implementación — eso es decisión de quien lo revise.
- No debe promoverse directamente a `PLAN.md`: según la regla de promoción del
  proyecto (`CLAUDE.md` / `docs/GOBERNANZA_FUENTES_VERDAD.md`), primero va a
  `docs/MEJORAS_FUTURAS.md` como backlog, y solo se promueve a `PLAN.md` cuando
  haya un disparador concreto (caso real bloqueado por uno de estos tres huecos).
