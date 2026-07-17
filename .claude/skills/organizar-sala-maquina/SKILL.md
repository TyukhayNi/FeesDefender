---
name: organizar-sala-maquina
description: >-
  Construye la «sala de máquina» de un expediente FeesDefender: convierte el
  crudo de 00_Input en PDFs BUSCABLES (OCR con OCRmyPDF, local, sin tope de
  páginas) y espejos Markdown legibles bajo
  01_Procesado/02_Sala de máquina/{01_OCR,03_MD}, con red de calidad
  (_cobertura.md marca lo dudoso) y trazabilidad SHA-256. Ejecución LOCAL
  (requiere OCRmyPDF+Tesseract); desde Cowork solo se dirige/revisa. Úsala
  cuando el usuario diga «pasa el OCR del caso», «saca el texto/los MD del
  expediente», «procesa los documentos», «monta la sala de máquina». NO
  organiza la sala de lectura (la SUGIERE al terminar; eso es
  organizar-sala-lectura), NO da de alta ni hace intake
  (abrir-caso/intake-expediente), NO valora viabilidad (triaje-viabilidad), NO
  anonimiza.
metadata:
  rol: procesado
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.2"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: experimental
  orchestrates: []
  requires: []
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# organizar-sala-maquina

Convierte el crudo de `00_Input/` de un expediente FeesDefender en la **sala de
máquina**: PDFs **buscables** (OCR con OCRmyPDF, sin tope de páginas) y sus
espejos en **Markdown** legible, con una red de calidad que marca lo dudoso en
vez de fallar en silencio. Es la capa de **máquina** del pipeline documental —
produce material para que el motor de análisis (scorer, viabilidad) y el propio
abogado puedan leer texto donde antes solo había un escaneado ciego. **Ejecución
LOCAL** (necesita OCRmyPDF/Tesseract instalados en el PC); Cowork dirige y
revisa, no ejecuta OCR.

## Cuándo se activa

- Disparadores: «pasa el OCR del caso», «saca el texto/los MD del expediente»,
  «procesa los documentos», «monta la sala de máquina», «hay escaneados que no
  se leen».

**NO se activa cuando:**

- Hay que **organizar la sala de lectura** (vista humana, clasificación E&V,
  nombre canónico) → `organizar-sala-lectura` (esta skill la **sugiere** al
  terminar, no la ejecuta).
- Hay que **dar de alta el caso o depositar ficheros nuevos** en `00_Input/` →
  `abrir-caso` / `intake-expediente`.
- Hay que **valorar la viabilidad** de la reclamación → `triaje-viabilidad`.
- Hay que **anonimizar** el expediente → fuera de alcance (motor `core/anon/`
  aparte; ver Gotchas).

## Entrada y montaje

- Trabaja sobre el **expediente en disco** (Drive del despacho montado como
  `G:` u otra raíz local con el layout estándar `00_Input/`…`01_Procesado/`).
- **Lee** de `00_Input/` (todas las fuentes), **excluyendo
  `90_Notas personales/`** (zona del abogado: ningún módulo la lee ni la
  escribe).
- **Escribe** en `01_Procesado/02_Sala de máquina/` y
  `01_Procesado/_revisar/_cobertura.md`. El caso se identifica por **nombre de
  carpeta** (`case_id`): `core.config.caso_path` lo resuelve tanto en layout
  plano como subdividido por ciudad (`CASOS/<ciudad>/<caso>/`).

## Qué produce

```
<Expediente>/
├── 00_Input/                              ← crudo, NO se toca
└── 01_Procesado/
    ├── 02_Sala de máquina/
    │   ├── 01_OCR/      {slug__sha8}.pdf      PDFs BUSCABLES (custodia)
    │   ├── 03_MD/       {slug__sha8}.md       markdown legible + frontmatter
    │   └── raw_text/    {slug__sha8}.txt      texto intermedio (idempotencia)
    └── _revisar/
        └── _cobertura.md                     worklist de revisión (ok/low/empty)
```

Cada `.md` lleva frontmatter trazable (`case_id`, `source_path`, `extractor`,
`chars`, `ocr`, `ocr_quality`, `text_sha256`). El evento `procesado_sala_maquina`
queda en `00_Input/_intake_log.jsonl` (sha256 por fichero — cadena de custodia).

## Procedimiento

1. **Preview.** Dispara `python -m scripts.sala_maquina plan "<case_id>"`.
   Muestra, sin escribir nada: cuántos documentos nuevos por ruta (`pdf` /
   `imagen` / `nativo` / `sin_soporte`) y cuántos se saltan por `sha256` ya
   procesado.
2. **(GATE Preview→Apply.)** Presenta el recuento al abogado y **espera OK**
   antes de ejecutar. Si el caso es grande o hay muchos `sin_soporte`,
   avísalo explícitamente antes de pedir confirmación.
3. **(tras OK) Apply.** Dispara
   `python -m scripts.sala_maquina apply "<case_id>"`. Enruta cada documento
   nuevo (PDF con capa de texto → `pypdf` sin OCR; PDF escaneado/imagen/`.heic`
   → OCRmyPDF → PDF buscable en `01_OCR/`; nativo `.eml`/`.docx`/`.txt`/… →
   extracción determinista) y escribe `03_MD/`, `raw_text/` y
   `_revisar/_cobertura.md`.
   - **`--vision`** (opcional, off por defecto): refuerza con transcripción de
     visión los documentos que salieron `low`/`empty` tras el OCR. **Requiere un
     transcriptor cableado** (lo inyecta el flujo de la skill / la sesión Claude);
     el CLI pelado **aborta con aviso claro** si se pide `--vision` sin cablearlo,
     en vez de simular el intento. Úsalo solo si el abogado lo pide (páginas
     manuscritas, tablas complejas).
   - **`--force`**: ignora el estado idempotente y regenera todo (usar solo si
     cambió el motor OCR o se sospecha una corrida corrupta).
4. **Reporta:** nº de documentos por ruta, nº de saltados por `sha256`, nº que
   requieren revisión humana (`low`/`empty`, con motivo, listados primero en
   `_cobertura.md`).
5. **(opcional) Reforzar dudosos.** Si tras el `apply` quedan `low`/`empty` con
   páginas renderizables y hay transcriptor cableado, dispara
   `python -m scripts.sala_maquina reforzar "<case_id>"`: re-procesa **solo** esos
   documentos con visión y reescribe MD + estado + cobertura de forma persistente
   (ya no hace falta transcribir a mano como antes). Sin transcriptor cableado,
   aborta con aviso.
6. **Handoff (puntero, no se ejecuta):** sugiere correr `organizar-sala-lectura`
   sobre el mismo caso como siguiente paso — esta skill deja el material
   legible, no lo clasifica para lectura humana.

## Gotchas

- **Ejecución LOCAL, no en Cowork.** Requiere OCRmyPDF + Tesseract
  (`spa+cat+rus`) + Ghostscript instalados en el PC (ya lo están en el entorno
  del despacho). Desde Cowork solo se dirige (leer `_cobertura.md`, pedir la
  corrida) o se revisa el resultado — el conector de Drive no ejecuta binarios.
- **Idempotente por `sha256`.** Cada re-corrida de `apply` solo procesa
  documentos nuevos (`_sala_maquina_state.json`); los ya resueltos (`ok`/`low`)
  se saltan. Un documento que falló (p. ej. PDF cifrado) **no** se marca como
  resuelto — se reintenta en la siguiente corrida normal, sin necesitar
  `--force`.
- **Cobertura ACUMULATIVA entre corridas.** `_cobertura.md` es una vista derivada
  del registro estructurado `_cobertura.json`; una corrida incremental **fusiona**
  el delta con lo previo en vez de machacarlo — las filas de corridas anteriores no
  se pierden. `--force` da foto fresca del inventario actual (simétrico con el
  estado).
- **`00_Input/` y `90_Notas personales/` intocables.** Invariante forzada por
  `core.sala_maquina.destino_seguro`: cualquier intento de escribir ahí lanza
  `ValueError` en vez de corromper el crudo.
- **Hueco de escaneados largos, cerrado.** El pipeline general capa el OCR de
  Docling a 30 páginas (anti-OOM); esta skill usa OCRmyPDF página a página, sin
  ese tope — un escaneado de 80 páginas ya no sale `.md` vacío en silencio.
- **Sin fallo silencioso.** Todo lo dudoso (`low`/`empty`/gibberish) se persiste
  igual y queda en `_cobertura.md`, ordenado con los casos a revisar primero —
  nunca desaparece del inventario sin dejar rastro.
- **No anonimiza.** El MD queda en claro (regla de deuda consciente del
  despacho, revisitar cuando se reinstaure el muro `06_`); no mandes estos MD
  fuera del entorno de trabajo del despacho sin pasar por el pipeline de
  anonimización si el destino lo exige.
