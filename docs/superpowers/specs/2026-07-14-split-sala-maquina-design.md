---
estado: vigente
dueño: Nikolai (arquitectura) + Claude Code (implementación)
disparador: caso real inminente — expediente judicial escaneado (+200 pp) con múltiples documentos concatenados (cédulas, autos, demanda + adjuntos: emails, contratos, poderes, escrituras), escaneado con HOJA EN BLANCO insertada entre documentos como separador
banco_de_pruebas: bundle judicial escaneado del caso en curso (a fijar como fixture) + W-02VND1 (golden fixture existente)
depende_de: Cluster A (cobertura acumulativa + --vision + reforzar sobre core/sala_maquina.py y scripts/sala_maquina.py) — mismos ficheros, implementación SECUENCIADA tras su merge
---

# SPEC — Split de bundles multi-documento en la Sala de máquina

> ⚠️ **El contrato de NOMBRES de este documento está SUPERADO desde el 2026-08-02.** Donde aquí se lee
> `{bundle_sha8}__seg{NN}_{TIPO}__{seg_sha8}` (líneas 113, 241, 286-287 y 344), el motor produce hoy
> `{parent_slug}__{doc_id}_{TIPO}` — sin el sha del segmento. El sha seguía al artefacto **derivado**,
> así que re-OCR-izar renombraba todo y el reproceso **añadía** una generación en vez de sustituirla.
> Contrato vigente: `2026-08-01-identidad-segmento-bundle-design.md` (rev. 4, pieza A). **El resto de
> este documento sigue vigente** —corte por hoja en blanco, manifiesto editable, `separar.py` como
> librería— y su historia no se reescribe: describe lo que se decidió el 2026-07-14.

**Versión:** 1.0 (diseño cerrado; anclado al código real de FeesDefender)
**Fecha:** 2026-07-14
**Naturaleza:** documento de DISEÑO. El siguiente paso es `writing-plans`, NO construir.
**Origen:** materializa la pieza de split (1→N) del §F/§G.6 de `docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md`
(diferida en el spec `2026-07-09-organizar-sala-maquina-design.md` §15.6), enganchándola en la
Sala de máquina entre OCR y MD.

---

## 0. Problema que resuelve

La Sala de máquina actual (`core/sala_maquina.py`) trata **cada fichero de `00_Input/` como UN
documento**: PDF con texto → `_try_pypdf` → un MD; PDF escaneado → OCRmyPDF → un MD. Un **bundle**
—un solo PDF escaneado de +200 páginas con muchos documentos concatenados (encargo, facturas,
arras, correos, PBC en los casos de honorarios; cédulas, autos, demanda + adjuntos en los
expedientes judiciales)— produce **un único MD gigante, inútil para el análisis**: no se puede
citar por documento, ni clasificar por categoría E&V, ni cronologizar, ni anclar prueba.

El caso disparador es un **expediente judicial escaneado**. Nikolai ha instaurado una convención
en el escaneo: **se inserta una hoja en blanco entre documentos** como separador físico. Esa hoja
en blanco es una señal de corte **deliberada, controlada por el letrado y agnóstica al tipo de
bundle** — sirve igual para el expediente judicial y para el bundle de honorarios E&V.

El motor de split maduro ya existe (`core/anon/separar.py`), pero (a) está **congelado**
(`core/anon/` no se toca: regla de oro del proyecto) y **tuneado a lo judicial** por marcadores
textuales, y (b) **NO corta por hoja en blanco** — una página sin texto da `tipo=None` y su
lógica la *absorbe* en el segmento actual, es decir, se comería justo la señal que el escaneo crea.

Este spec engancha el split en la Sala de máquina **partiendo cada bundle en sus N documentos
lógicos ANTES de generar los MD**, con la hoja en blanco como señal de corte primaria y sin tocar
`core/anon/`.

---

## 1. Alcance

**Incluye:**
- Modelo de **documento lógico** con tres destinos por fichero físico: passthrough (1→1),
  split (1→N), merge (N→1) — ver §3.
- **Detección de segmentos** por hoja en blanco (primario) + marcadores textuales (clasificador
  y fallback), en una **capa nueva fuera de `core/anon/`** (§4).
- **Gate Preview→Apply** vía **manifiesto editable** (§5): `plan` propone → el letrado ajusta →
  `apply` materializa.
- **Corte** (split 1→N) y **passthrough** (1→1) en `apply`; escritura de N PDFs a
  `02_Documentos/`, un MD por documento lógico, filas de cobertura, `indice.json` por bundle y
  evento de log.
- **Contrato de salida** que expone los documentos lógicos para la Sala de lectura (§9).
- Idempotencia por `sha256` del bundle; `00_Input/`/`90_Notas personales/` intocables.

**No incluye (diferido, con costura lista):**
- **Merge (N→1) en `apply`** y su **auto-detección** (`conjunto_detector`): el manifiesto y el
  modelo de datos son **merge-ready**, pero la primitiva de concatenar y la auto-detección quedan
  como **extensión aditiva** (§3.3, §12). `conjunto_detector` sigue aparcado.
- **Cableado de `organizar-sala-lectura`** para consumir documentos lógicos en vez de `00_Input/`
  crudo: este spec **define el contrato** (§9); el consumo es un **follow-on** a esa skill.
- **Registro único `index.yaml` / id `doc-NNN`** (motor §H), **anonimización** (`06_`),
  **reorganización de flota**, **renombrado** `Sala lectura`→`01_Sala de lectura`.
- Cualquier edición de `core/anon/` (regla de oro).

**Entorno:** ejecución **local** (Claude Code / CLI con OCRmyPDF); Cowork = director/revisor.

---

## 2. Decisiones cerradas (brainstorming 2026-07-14)

| # | Decisión | Resolución |
|---|---|---|
| D1 | **Señal de corte primaria** | **Hoja en blanco** (chars≈0 ∧ baja cobertura de tinta). Deliberada, controlada por el letrado, agnóstica al tipo de bundle, y **esquiva el congelado** (para *encontrar* el límite no hace falta ningún marcador). |
| D2 | **Marcadores textuales** | Degradados a **clasificador** de cada segmento ya cortado (`separar.detectar_tipo`) + **fallback** de corte cuando el bundle NO trae hojas en blanco. |
| D3 | **Marcadores E&V (hueco del congelado)** | **Inyección aditiva** vía parámetro opcional `tipos_extra` (default `None` = comportamiento idéntico; no toca regex/listas/thresholds de `core/anon/`) + **clasificación post-split**. Marcadores E&V (arras, PBC, reserva, reclamación, activación) viven en la capa nueva. |
| D4 | **Regla de la hoja en blanco** | **Entre dos hojas en blanco, todo es UN documento lógico**, aunque cambie el tipo por dentro. La señal humana manda; los marcadores **etiquetan**, no vuelven a cortar dentro del segmento. |
| D5 | **Placement** | **Entre OCR y MD** (§F del motor): OCR el bundle completo → detectar → cortar el buscable → MD por segmento. |
| D6 | **Gate** | **Manifiesto editable** (`plan` propone → letrado ajusta → `apply` corta). Equivalente no interactivo de `revisar_segmentos_interactivo`. |
| D7 | **`conjunto_detector` (merge N→1)** | **Aparcado.** Eje inverso, depende de metadatos CRM y del registro único inexistente. |
| D8 | **Registro bundle↔segmento** | **Mínimo, reusando lo que hay:** `indice.json` por bundle (formato `separar.generar_indice`) + filas de `_cobertura.md` con `parent_slug`/`role_in_bundle`/páginas + evento de log. `index.yaml` **NO** se construye; campos listos para el motor. |
| D9 | **Merge en este spec** | **Manifiesto merge-ready; `apply` hace split+passthrough ahora.** Merge (N→1) apply + auto-detección = extensión aditiva. |
| D10 | **Sala de lectura** | **Contrato definido aquí; consumo = follow-on** a `organizar-sala-lectura`. |
| D11 | **Capa nueva, no `core/anon`** | La lógica nueva vive en `core/split_documental.py`. `core/anon/separar.py` se reutiliza **como librería** (piezas mecánicas), nunca se edita. |

---

## 3. Modelo de datos — el documento lógico

El motor no procesa ficheros físicos: procesa **documentos lógicos**. El mapeo físico→lógico tiene
tres destinos, y un lote heterogéneo (unos se parten, otros se juntan, otros ni se tocan) es el
caso normal — cada fichero cae en su destino de forma independiente.

### 3.1 Los tres destinos

| Destino | Caso | Operación en `apply` | Estado en este spec |
|---|---|---|---|
| **passthrough (1→1)** | doc normal, 1 segmento | ninguna: MD del buscable de `01_OCR/` o del nativo | ✅ incluido |
| **split (1→N)** | bundle con hojas en blanco / multi-doc | cortar con `pypdf` → N PDFs en `02_Documentos/` | ✅ incluido |
| **merge (N→1)** | varios ficheros = 1 doc (contrato en 3 PDFs, fotos página-a-página, cabecera+prueba) | concatenar con `PdfWriter` → 1 PDF en `02_Documentos/` | ⏸️ diferido (merge-ready, D9) |

La unidad de salida es **siempre** el documento lógico: **1 PDF + 1 MD + 1 fila de cobertura**,
sea cual sea su origen. Cortar y concatenar son la misma máquina (`pypdf`) en direcciones opuestas.

### 3.2 Estructura del documento lógico (dataclass, en `core/split_documental.py`)

```
DocLogico:
  slug: str            # {bundle_sha8}__seg{NN}_{TIPO}__{seg_sha8}  (Windows-path-safe)
  seg_sha256: str      # sha de los BYTES del PDF materializado (cortado/concatenado/copiado)
  destino: str         # 'passthrough' | 'split' | 'merge'
  tipo: str            # clasificación (CEDULA_EMPLAZAMIENTO, AUTO, DEMANDA, DOC_CONTRATO, ...)
  parent_slug: str     # slug del bundle de origen (= su propio slug si passthrough)
  parent_sha256: str   # sha del fichero físico de origen (ancla de idempotencia)
  role_in_bundle: str  # 'documento' (segmento normal) | 'head'/'attachment' (reservado, merge)
  paginas: str | None  # "1-4" (rango en el bundle; None si nativo/passthrough sin páginas)
  fuentes: list[str]   # rel_paths físicos que lo componen (1 salvo merge)
```

`role_in_bundle`, `fuentes` (lista) y `parent_*` son los campos **merge-ready**: hoy un split
rellena `fuentes=[bundle]` y `role='documento'`; un merge futuro rellenaría `fuentes=[a,b,c]`.

### 3.3 Merge-ready sin construir el merge (D9)

El schema del manifiesto (§5) admite declarar uniones; `apply` **hoy** solo materializa split y
passthrough. Añadir merge más tarde es **aditivo**: (a) una rama `elif destino == 'merge'` en
`apply` que concatene `fuentes` con `PdfWriter` (primitiva que `separar_pdf` ya usa), y (b) opcional,
la auto-población de propuestas de merge desde `conjunto_detector`. Ni el modelo de datos ni el
manifiesto cambian. **No hay callejón sin salida.**

---

## 4. Detección de segmentos — capa nueva FUERA de `core/anon/`

Módulo nuevo **`core/split_documental.py`** (`core/anon/` intacto). Reutiliza `separar.py`
**como librería**, nunca lo edita.

### 4.1 Corte primario — hoja en blanco

- **Definición robusta de hoja en blanco:** una página es separador si **(chars OCR < ε)** *Y*
  **(cobertura de tinta del ráster < δ)**. Las dos condiciones son necesarias:
  - Solo-chars daría **falsos positivos**: una foto/plano escaneado da ~0 chars pero **no** es
    separador → la cobertura de tinta lo rescata (tinta alta ⇒ no es blanco).
  - Solo-tinta daría **falsos positivos**: una página con una firma tenue o membrete ligero.
- **Cribado barato primero:** el conteo de chars por página es gratis vía `pypdf` sobre el PDF
  buscable. **Solo las páginas candidatas** (chars < ε) se rasterizan con `pypdfium2` (dep ya
  presente por `--vision`) para medir la tinta → coste de ráster acotado a las pocas páginas
  vacías-de-texto, no a las 200.
- **Umbrales** (`ε`, `δ`) como constantes del módulo, documentadas y testeables; valores iniciales
  a calibrar con el fixture real (§14). `δ` = fracción de píxeles no-blancos tras binarizar.
- **Descartar el separador:** las hojas en blanco **no** se emiten como documento lógico (son
  delimitador, no contenido). Se registran en `indice.json` como `delimitador` (auditoría).
- **Colapso:** blancos consecutivos, iniciales o finales no crean segmentos vacíos.
- **Regla D4:** entre dos blancos, todo es UN documento — **no** se re-corta por marcadores dentro
  del segmento.

### 4.2 Clasificación de cada segmento (marcadores como etiqueta)

Sobre las primeras líneas de cada segmento se llama a **`separar.detectar_tipo`** (reúso directo):
los marcadores judiciales ya cubren cédula/auto/decreto/demanda/contestación/oposición/sentencia/
email/contrato/factura/poder/escritura — el grueso del expediente judicial disparador. Para los
bundles de honorarios E&V se **inyectan marcadores extra** (arras, PBC, reserva, reclamación,
activación, ofertas) definidos en `core/split_documental.py` y pasados como `tipos_extra` (D3).

> **Tensión y su resolución (regla de oro `core/anon/`):** `separar.detectar_tipo` /
> `detectar_segmentos` leen la global `TIPOS_DOCUMENTO`. Para inyectar sin editar las listas
> congeladas, `separar.py` recibe un parámetro **opcional aditivo** `tipos_extra=None` en
> `detectar_tipo` y `detectar_segmentos` (default `None` ⇒ comportamiento **byte-idéntico** al
> actual; los tests de regresión del anonimizador lo prueban). Esto **no toca** regex, listas ni
> thresholds existentes — solo añade un punto de extensión. Es la vía "parametrizar por inyección
> sin tocar sus listas" sancionada por el encargo. **Alternativa descartada:** reimplementar la
> detección fuera re-derivaría la lógica madura de agrupación/absorción (riesgo de divergencia).

### 4.3 Fallback — sin hojas en blanco

Si el bundle **no** trae hojas en blanco (escaneo antiguo, bundle de otra fuente) → se cae a
**`separar.detectar_segmentos`** (marcadores, con `tipos_extra` E&V) → si eso también da 1 segmento
→ **passthrough** (documento único, camino actual intacto).

### 4.4 Reúso mecánico de `separar.py`

- `extraer_primeras_lineas(pagina, n)` — para clasificar segmentos.
- `separar_pdf(ruta_pdf, segmentos, carpeta_salida, log)` — **cortador atómico Windows-safe**
  (temporal + `replace`, cierre de handles, limpieza en error). No se reimplementa.
- `generar_indice(resultados, ...)` — `indice.json`/`indice.txt` por bundle.
- `detectar_tipo` / `detectar_segmentos` (vía `tipos_extra`) — clasificación y fallback.

---

## 5. Gate Preview→Apply — manifiesto editable

Equivalente no interactivo de `revisar_segmentos_interactivo`, generalizado a **mapa físico→lógico**.

### 5.1 `plan`
Para cada fichero de `00_Input/` (tras OCR, §6) decide destino (§3) y, si es multi-segmento,
escribe un **manifiesto de segmentación editable**:

- **Ubicación:** `02_Sala de máquina/02_Documentos/{bundle_slug}/_segmentacion.json` (+ espejo
  legible `_segmentacion.md` para revisión cómoda).
- **Contenido:** una entrada por documento lógico propuesto:
  ```json
  {
    "fuente": "01_Drive EV/expediente_completo.pdf",
    "bundle_sha256": "…",
    "segmentos": [
      {"seg": 1, "pp": "1-4",   "tipo": "CEDULA_EMPLAZAMIENTO", "role": "documento"},
      {"seg": 2, "pp": "6-12",  "tipo": "AUTO",                 "role": "documento"},
      {"seg": 3, "pp": "14-30", "tipo": "DEMANDA",              "role": "documento"},
      {"seg": 4, "pp": "32-45", "tipo": "DOC_CONTRATO",         "role": "documento"}
    ],
    "delimitadores": [5, 13, 31]
  }
  ```
- **No pisa un manifiesto ya editado:** si el fichero existe, `plan` lo **respeta** (lo reporta),
  salvo `--force`. Así el letrado edita entre `plan` y `apply` sin perder cambios.

### 5.2 Ediciones que el letrado puede hacer sobre el manifiesto
- **Fusionar** dos segmentos (une rangos: el escáner metió un blanco de más).
- **Mover un límite** (`pp` mal detectado).
- **Re-etiquetar** el `tipo` de un segmento.
- **Merge (futuro, D9):** declarar `fuentes: [a.pdf, b.pdf]` en una entrada → concatenar.

### 5.3 `apply`
Consume el manifiesto aprobado → por documento lógico:
- **split:** `separar_pdf` sobre el rango `pp` → PDF en `02_Documentos/{bundle_slug}/`.
- **passthrough:** MD directo del buscable de `01_OCR/` / nativo (sin PDF nuevo).
- Genera MD, fila de cobertura, `indice.json`, evento de log (§7, §8).

---

## 6. Placement en el pipeline (entre OCR y MD)

```
bundle escaneado (00_Input/, 1 PDF, sin capa de texto)
  → [Cluster A] OCRmyPDF sobre el bundle COMPLETO → 01_OCR/{bundle_slug}.pdf   (buscable; custodia del bundle)
  → [NUEVO] split_documental.detectar(...)  (hoja en blanco primario; §4)
       · ≥2 segmentos → GATE manifiesto → apply corta → 02_Documentos/{bundle_slug}/{NN}_{TIPO}__{sha8}.pdf
       · 1 segmento   → passthrough (camino actual)
  → 03_MD/  (N .md, uno por documento lógico — adiós al MD gigante)
```

- **OCR una sola vez** sobre el bundle entero (OCRmyPDF va página a página, sin tope de 30 pp).
- **El corte es sobre el PDF ya buscable** con `pypdf` ⇒ cada segmento **conserva su capa de
  texto** (no se re-OCR-iza).
- **Custodia doble:** el buscable del bundle permanece en `01_OCR/`; los segmentos cuelgan de
  `02_Documentos/`.
- **Digital (PDF con texto, sin OCR):** el detector corre igual sobre la capa de texto + ráster.
- **Gating:** la detección corre en todo PDF, pero barata (§4.1); **solo se corta si ≥2 segmentos**.
  Sin umbral de nº de páginas (un doc suelto da 1 segmento y sigue el camino actual).

---

## 7. Layout en disco

### 7.1 Qué existe hoy vs qué crea este spec

`core/case_manager.py` **solo crea de entrada** `01_Procesado/{Sala lectura, MD, _revisar}`
(línea 271). `02_Sala de máquina/` y sus productos se crean **bajo demanda**: Cluster A crea
`01_OCR/` y `03_MD/`; **este spec añade `02_Documentos/`** (NO existe hoy). Nada se crea eager.

### 7.2 Sala de máquina — subcarpeta por bundle

`02_Documentos/` **solo contiene bundles que se partieron** (destino `split`; en el futuro,
`merge`). Un **passthrough NUNCA aparece aquí**: su MD sale directo del buscable de `01_OCR/` o del
nativo.

```
01_Procesado/02_Sala de máquina/               ← lo crea la Sala de máquina (NO existe hoy)
├── 01_OCR/
│   └── expediente-judicial__a1b2c3d4.pdf              el bundle ENTERO, buscable (custodia)
├── 02_Documentos/                             ← NUEVO (este spec); SOLO bundles partidos
│   └── expediente-judicial__a1b2c3d4/                 1 subcarpeta por bundle partido
│       ├── 01_CEDULA_EMPLAZAMIENTO__e5f6.pdf          1 PDF por documento lógico (segmento)
│       ├── 02_AUTO__7a8b.pdf
│       ├── 03_DEMANDA__9c0d.pdf
│       ├── 04_DOC_CONTRATO__1e2f.pdf
│       ├── 05_DOC_PODER_NOTARIAL__3a4b.pdf
│       ├── _segmentacion.json                         manifiesto editable (el gate, §5)
│       ├── _segmentacion.md                           espejo legible
│       └── indice.json                                relación bundle↔segmentos (+ delimitadores)
├── 03_MD/
│   ├── expediente-judicial__a1b2c3d4__seg01_...__e5f6.md   1 MD por documento lógico
│   ├── ...__seg02_AUTO__7a8b.md
│   └── contrato-suelto__ffff.md                       un passthrough: MD directo, SIN carpeta arriba
└── _revisar/
    └── _cobertura.md                                  1 fila por documento lógico (registro interino)
```

**Por qué subcarpeta y no plano (divergencia menor consciente con el motor §G.6):** el motor prevé
`02_Documentos/` **plano** con la relación bundle↔segmento en el registro único `index.yaml`. Pero
`index.yaml` **no existe** (motor aparcado). Sin ese registro, un caso con varios bundles dejaría
decenas de PDFs sueltos sin saber cuál vino de cuál. La **subcarpeta por bundle es el registro
visual interino** y aloja el manifiesto y el índice del bundle. Cuando el motor traiga `index.yaml`,
**aplanar es mecánico** (el slug ya codifica el `sha8` del bundle padre). Nombre "tipo oración" /
numeración coherentes con el resto del árbol.

### 7.3 Sala de lectura — el bundle es un DOCUMENTO COMPUESTO = subcarpeta fechada (NO se toca aquí; end-state)

Este spec **no toca `organizar-sala-lectura`** (D10, consumo = follow-on §9). Su convención real
(verificada en `SKILL.md` §"Documentos compuestos" y en la guarda "Estructura plana"): la sala es
**plana para documentos sueltos** (la categoría vive en `INDICE.md`, no en carpetas), **pero los
documentos compuestos (bundles) abren SUBCARPETA fechada** `AAAA-MM-DD_descripción/` con
principal + anexos, agrupados por `parent_id`/`orden` del `_MANIFIESTO.md`. Los bundles canónicos
que ya usan esta subcarpeta: **WhatsApp** (chat + `media/`), **email `.eml`** (cuerpo + adjuntos
MIME), **clúster CRM** (subida en lote).

**Un bundle partido encaja EXACTO en ese modelo:** es un documento compuesto cuyos miembros son sus
segmentos. **NO se disuelve en documentos planos** — aterriza como una **subcarpeta fechada** cuyos
miembros son los segmentos, cada uno con su propia fecha y nombre canónico, agrupados por el
`parent_id`. El `parent_slug`/`role_in_bundle` del split (§3.2) mapea **directamente** al
`parent_id`/`orden` que la Sala de lectura ya usa para compuestos.

```
01_Procesado/Sala lectura/                     ← convención real (plana + compuestos en subcarpeta), NO la toca este spec
├── 2023-05-20_expediente-judicial/                   BUNDLE PARTIDO = documento compuesto (subcarpeta fechada)
│   ├── 2023-04-12_cedula-emplazamiento.pdf                  miembro (su propia fecha)
│   ├── 2023-05-03_auto-admision.pdf
│   ├── 2023-05-20_demanda.pdf
│   ├── 2023-02-10_contrato-arrendamiento.pdf
│   └── 2023-02-10_poder-notarial.pdf
├── 2023-06-01_factura-suelta.pdf                     documento suelto (passthrough) = plano en la raíz
├── INDICE.md                                          categoría E&V (por miembro) vive aquí
├── CRONOLOGIA.md
└── _MANIFIESTO.md                                     parent_id/orden del bundle ↔ sus segmentos
```

**Contraste de las dos salas:** subcarpeta por bundle en la **Sala de máquina** (taller, agrupa por
origen para trazabilidad/regeneración) **y** subcarpeta por bundle en la **Sala de lectura** (como
documento compuesto, su convención ya existente); un **passthrough** es plano en ambas. El puente
entre las dos salas es el contrato de `_cobertura.md` + `parent_slug`/`role_in_bundle` (§9). El
nombramiento interno exacto (principal vs anexo, o miembros-pares) lo decide el follow-on, dueño de
la convención de la Sala de lectura.

---

## 8. Contratos de datos

- **MD del segmento (`03_MD/{seg_slug}.md`):** frontmatter de `markdown_generator` +
  `source_path` = **bundle**, `parent_slug`, `role_in_bundle`, `paginas`, `tipo` (clasificado),
  `ocr_quality`, `seg_sha256`, `text_sha256`. Nombre `seg_slug` (resuelve colisión de stem #47).
- **`_cobertura.md`:** **una fila por documento lógico** (no por fichero físico): `documento
  (seg_slug) | origen (bundle rel_path) | páginas | tipo | parent_slug | role | método | estado
  (ok/low/empty) | chars | ocr | nota`. Es, en el interim (sin `index.yaml`), **el registro de
  documentos lógicos** que consume la Sala de lectura (§9).
- **`indice.json` por bundle:** formato `separar.generar_indice` + `delimitadores` (páginas en
  blanco descartadas) + `bundle_sha256`.
- **`_intake_log.jsonl`:** evento `split_documental` (nuevo en `INTAKE_EVENTS`):
  `details = {bundle: rel_path, bundle_sha256, n_segmentos, segmentos: [{seg_slug, seg_sha256,
  tipo, paginas}], delimitadores}`. El `procesado_sala_maquina` de Cluster A se mantiene.

---

## 9. Contrato de salida para la Sala de lectura (D10)

**El bundle aterriza como DOCUMENTO COMPUESTO — una subcarpeta fechada con sus N segmentos como
miembros** (layout concreto en §7.3), reutilizando la convención de compuestos que la Sala de
lectura ya aplica a WhatsApp/email/CRM. Ese es el objetivo: sin split, `organizar-sala-lectura`
tendría una entrada opaca de 200 pp; con split, ve la cédula, el auto, la demanda, el contrato, el
poder… **cada uno como miembro con su propia fecha, nombre canónico `AAAA-MM-DD_descripción` y
categoría E&V**, agrupados bajo el bundle por `parent_id`.

**Contrato que este spec expone (estable):**
- Cada documento lógico = un PDF (`02_Documentos/{bundle}/…` si split; `01_OCR/…` o nativo si
  passthrough) + una **fila en `_cobertura.md`** con `tipo`, `paginas`, `parent_slug`, `role`.
- `_cobertura.md` (una fila = un doc lógico) es la **enumeración autoritativa** de documentos
  lógicos en el interim (hasta `index.yaml`).

**Follow-on (fuera de este spec):** enseñar a `organizar-sala-lectura` a **consumir la enumeración
de documentos lógicos** (`_cobertura.md`) en vez de recorrer `00_Input/` crudo, **emitiendo un
bundle partido como documento compuesto** (subcarpeta fechada + `parent_id`). Es un follow-on
**pequeño**: la Sala de lectura **ya tiene** el mecanismo de compuestos (WhatsApp/email/CRM) y el
split ya entrega `parent_slug`/`role_in_bundle` — solo hay que mapear y añadir "bundle partido"
como señal determinista de agrupación. Toca el fichero de esa skill → handoff en spec aparte.

> **Brecha explícita:** mientras ese follow-on no se haga, `organizar-sala-lectura` seguirá leyendo
> `00_Input/` y vería el bundle crudo. Este spec deja el material y el contrato listos; el círculo
> de punta a punta lo cierra el follow-on. Documentado como deuda consciente (§13).

---

## 10. Idempotencia y reejecución

- **Estado por `sha256` del bundle** (patrón `_sala_maquina_state.json`): bundle sin cambios +
  segmentos ya materializados → **skip**. El `seg_sha256` (bytes del PDF cortado) es determinista
  dado bundle+rangos → dedup automática.
- **`plan` no pisa un manifiesto editado** sin `--force` (§5.1): el ajuste del letrado sobrevive a
  un `plan` repetido.
- **`00_Input/` y `90_Notas personales/` intocables** — guard `destino_seguro` (M5) ya existente
  cubre todos los writers; los nuevos destinos (`02_Documentos/`) pasan por él.
- **Nunca borra** productos previos; añade/actualiza. `--force` regenera (invalida cache + re-pisa
  manifiesto). `--dry-run`/`plan` sin efectos.
- Escritura **atómica** heredada de `separar_pdf`.

---

## 11. Manejo de errores (sin fallo silencioso)

| Fallo | Comportamiento |
|---|---|
| Bundle que revienta `pypdf`/render | se marca `error` en cobertura; **no** tumba el lote (aislamiento por bundle, `try/except`) |
| Detección da 0 segmentos útiles (todo blanco) | passthrough del bundle completo + nota; nunca PDF vacío (guard `PDFVacioError` de `separar_pdf`) |
| Segmento imagen-only (foto/plano, pocos chars) | se emite como **documento real**, flag `low`/`empty` para `--vision` (como hoy); **NO** se descarta |
| Hoja en blanco con mota/ruido (chars≈0, tinta baja) | tratada como delimitador (correcto) |
| Manifiesto editado a mano con rango inválido (`pp` fuera de rango, solapado) | `apply` valida y falla claro señalando la entrada; no corta parcial |
| Bundle sin hojas en blanco | fallback a marcadores; si 1 → passthrough |
| Rango degenerado (`fin <= inicio`) | `PDFVacioError` de `separar_pdf`, reportado |

---

## 12. Composición con Cluster A (dependencia explícita)

Cluster A está editando **`core/sala_maquina.py`** y **`scripts/sala_maquina.py`** (cobertura
acumulativa + `--vision` + reforzar). Este spec **toca los mismos ficheros**:
- `core/sala_maquina.py`: insertar el paso split en `ejecutar`/`_ocr_y_extraer` (entre producir el
  buscable y escribir el MD); la cobertura pasa a ser **una fila por documento lógico**.
- `scripts/sala_maquina.py`: sub-gate del manifiesto en `plan`/`apply`.

**Por tanto: la IMPLEMENTACIÓN se secuencia DESPUÉS de que Cluster A mergee** (mismos ficheros →
no en paralelo; ver `[[feedback-concurrent-sessions-shared-worktree]]`). Mitigación de acoplamiento:
**el grueso de la lógica nueva vive aislado en `core/split_documental.py`**, de modo que el enganche
en los ficheros de Cluster A sea mínimo y bien identificado (una llamada + el cambio de granularidad
de cobertura), y el merge/rebase sea limpio. Cada documento lógico pasa por el OCR/MD/visión/
cobertura **ya existentes**; el split solo se sitúa antes del MD por-documento.

---

## 13. Decisiones diferidas / deuda consciente (no bloquean F1)

1. **Merge (N→1) en `apply` + auto-detección (`conjunto_detector`)** — merge-ready hoy (§3.3); el
   apply concatenador y la auto-población son extensión aditiva.
2. **Consumo por `organizar-sala-lectura`** (D10, §9) — follow-on; brecha explícita mientras tanto.
3. **Registro único `index.yaml` / id `doc-NNN`** — motor §H; hoy `_cobertura.md` + `indice.json`
   hacen de registro interino.
4. **`02_Documentos/` plano vs subcarpeta por bundle** (§7) — interim subcarpeta; aplanado futuro
   mecánico (el slug ya codifica el parent).
5. **Reocr por calidad / audit completo** — motor §G.7/§D.2.
6. **Calibración de `ε`/`δ`** del detector de blanco — con el fixture real (§14).

---

## 14. Fases (build incremental, tests por fase)

> Prerrequisito global: **Cluster A mergeado** (§12). Rebase antes de F1.

- **F0 — fixture.** Congelar el bundle judicial escaneado real como golden fixture (patrón
  `scripts/regen_fixture_*`), con su verdad-terreno de límites (páginas de corte esperadas) y
  tipos. Calibrar `ε`/`δ` (§4.1) contra él y contra páginas-imagen reales (foto/plano) para fijar
  el umbral que **no** confunde imagen con blanco.
- **F1 — detector + cerebro (walking skeleton).** `core/split_documental.py`: detección por hoja en
  blanco (§4.1), clasificación (§4.2, con `tipos_extra`), fallback (§4.3), modelo `DocLogico`
  (§3.2), construcción del manifiesto (§5.1). Parámetro aditivo `tipos_extra` en `separar.py`
  (§4.2) **con test de regresión byte-idéntico** del anonimizador. Un bundle real → manifiesto
  propuesto (sin cortar aún).
- **F2 — apply (split + passthrough) + cobertura + layout.** Corte a `02_Documentos/` (reúso
  `separar_pdf`), MD por segmento, `_cobertura.md` a granularidad de doc lógico, `indice.json`,
  evento de log, guard `00_Input`. Enganche mínimo en `core/sala_maquina.py`/`scripts/sala_maquina.py`
  (§12). Idempotencia por sha del bundle + respeto del manifiesto editado. Corrida E2E sobre el
  fixture (medir "de 1 MD gigante a N MD por documento").
- **F3 — gate + CLI + contrato de salida.** `plan`/`apply` con el sub-gate del manifiesto,
  `--force`, `--dry-run`; espejo `_segmentacion.md`; validación de manifiesto editado a mano (§11);
  documentar el contrato de salida (§9) para el follow-on de la Sala de lectura.

---

## 15. Tests

- **Unit (core, puro / con fixtures de PDF):**
  - Detector de blanco: página vacía real ⇒ delimitador; foto/plano (0 chars, tinta alta) ⇒ **no**
    delimitador; página con firma tenue ⇒ **no** delimitador; blancos consecutivos/iniciales/
    finales ⇒ colapsan sin segmentos vacíos.
  - Segmentación: bundle con N blancos ⇒ N+1 segmentos con rangos correctos; regla D4 (cambio de
    tipo dentro de un segmento **no** corta).
  - Clasificación: cada segmento recibe el `tipo` esperado (judicial + E&V inyectado).
  - Fallback: bundle sin blancos ⇒ marcadores; sin marcadores ⇒ passthrough.
  - Manifiesto: construcción, no-pisado si existe, validación de rangos inválidos/solapados.
  - `DocLogico` slug/sha deterministas.
- **Regresión `core/anon/` (crítico):** `detectar_tipo`/`detectar_segmentos` con `tipos_extra=None`
  ⇒ salida **byte-idéntica** a la actual sobre los fixtures del anonimizador. Prueba que la regla de
  oro se respeta.
- **Integración:** bundle escaneado real → OCR → split → N PDFs buscables + N MD + cobertura;
  passthrough (doc suelto) → 1 MD, sin PDF nuevo; reejecución idempotente (skip por sha);
  manifiesto editado (fusión de 2 segmentos) respetado por `apply`; `--force` regenera; bundle que
  revienta aislado sin tumbar el lote.
- **Merge-ready (no ejecuta merge):** test de que el schema del manifiesto y `DocLogico` admiten
  `fuentes` múltiples sin romper (guardarraíl del callejón, D9).
