# Plan multi-hilo — SaRS1 (Castelar 37-39, Santander) / Procesamiento documental + bucle de mejora continua

> Documento maestro de un desarrollo distribuido en 7 hilos de Cowork. Cada hilo es autocontenido: incluye contexto mínimo, pre-condiciones, pasos, comandos, criterios de aceptación y entregables. Al abrir un hilo nuevo, leer **§3 Bibliografía de apertura** y el hilo correspondiente. No es necesario releer hilos previos si los criterios de aceptación quedaron marcados.

> Última actualización: 2026-05-12. Autor: Nikolai Tyukhay + Claude (Cowork).

---

## 0. Contexto y objetivo

El caso `SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros` es una demanda recibida en papel por el cliente Engel & Völkers Spain, S.L.U., escaneada en bloque en dos PDFs agregados sin capa OCR (`Demanda_Std_1_compressed.pdf`, `Demanda_Std_2_compressed.pdf`). El cliente actúa como demandado. Expediente CRM judicial **659** en sudespacho.net.

El objetivo final del desarrollo es disponer de los `.md` anonimizados en `06_Anonimizado/` para entregárselos a Claude frontier, que producirá un borrador de contestación a la demanda. Tras el borrador, una pasada de deanonimización devolverá el documento con datos reales para revisión final y firma.

En paralelo, esta sesión inaugura el **primer fixture gold-standard del proyecto** en `tests/fixtures/anon/SaRS1/`. La revisión forense del output (fase 5) genera una tabla de errores que alimenta `docs/MEJORAS_FUTURAS.md` y queda fijada como regresión controlada para futuras mejoras del motor.

Pilar arquitectónico que no se rompe en ninguna fase: los documentos no anonimizados nunca pasan por LLM con acceso a internet. Las fases 1-6 operan con motores deterministas (Tesseract, regex de split, Presidio + spaCy NER local). Claude frontier solo recibe `.md` ya anonimizados (fase 6 de cierre).

---

## 1. Decisiones tomadas (referencia rápida)

| # | Decisión | Origen |
|---|---|---|
| D1 | Cliente correcto: **ENGEL & VÖLKERS SPAIN, S.L.U.** (ID 27), no EV MMC SPAIN (ID 2). Rectificación pendiente en `_caso.md` local (hilo 1). | Mensaje usuario 2026-05-12 |
| D2 | Posición procesal: **DEMANDADO**. CRM ya rectificado manualmente. En `CaseMeta` no se persiste posición; se anota en body del `_caso.md` como observación. | Mensaje usuario 2026-05-12 |
| D3 | Pull del expediente 659 desde CRM **no se ejecuta** (bug `presigned_download_url` + intake manual ya completo). | STATUS §`[CRITICO-PRESIGNED-DOWNLOAD-BUG]` + usuario |
| D4 | Subida al CRM tras procesamiento: **manual** vía UI sudespacho.net (drag-and-drop en gdocu). No hay endpoint REST de upload. Construirlo sería proyecto aparte. | Auditoría 2026-05-12 |
| D5 | Política de anonimización primera pasada: `SALTAR` (idempotente). Si la verificación detecta sistemáticos, relanzar afectados con `REPROCESAR`. | Plan 2026-05-12 |
| D6 | Adaptación de `core/anon/deanonimizar.py` para que lea `_mapa_caso.json` además del legacy `<doc>_mapa.json`. Sesión técnica dedicada (hilo 3). | Auditoría 2026-05-12 |
| D7 | Este caso inaugura `tests/fixtures/anon/SaRS1/` como primer fixture gold-standard del proyecto. | Plan 2026-05-12 |
| D8 | Mejoras detectadas en revisión forense se documentan en `docs/MEJORAS_FUTURAS.md`, **no se parchean en código durante esta sesión** (memoria persistente `feedback_anon_logica_intacta.md`). Excepción: correcciones puntuales del `_mapa_caso.json` para limpiar el material que verá Claude. | Memoria del proyecto |
| D9 | Idioma OCR primera pasada: `spa`. Ampliar a `rus` o `cat` solo si hay anexo identificado en esos idiomas. | Plan 2026-05-12 |
| D10 | Originales de `04_Manual/` se conservan intactos. OCR y split escriben a subcarpetas `_ocr/` y `_split/` paralelas. | Plan 2026-05-12 |

---

## 2. Mapa de hilos

| Hilo | Título | Tiempo estimado | Prerequisito | Entregable |
|---|---|---|---|---|
| H1 | Apertura, corrección `_caso.md`, diagnóstico de PDFs, OCR | 30-45 min | — | PDFs en `00_Input/04_Manual/_ocr/`, `_caso.md` corregido |
| H2 | Split por tipo documental + revisión humana | 30-45 min | H1 cerrado | PDFs en `00_Input/04_Manual/_split/`, una pieza por tipo lógico |
| H3 | Adaptación técnica de `core/anon/deanonimizar.py` | 45-60 min | Independiente (puede solaparse con H2) | PR mergeada con `_localizar_mapa` extendido + tests |
| H4 | Anonimización + generación de markdown | 20-40 min | H2 + H3 cerrados | `06_Anonimizado/*.md` + `_mapa_caso.json` |
| H5 | Verificación forense + creación del fixture gold-standard | 45-90 min | H4 cerrado | `07_AI cowork/_revision_anon_SaRS1.md`, `tests/fixtures/anon/SaRS1/`, entradas en `MEJORAS_FUTURAS.md`, `_mapa_caso.json` corregido manualmente |
| H6 | Subida manual al CRM + entrega a Claude frontier | 30-60 min | H5 cerrado | Documentos en gdocu del expediente 659, borrador anonimizado recibido de Claude en `08_Borradores/` |
| H7 | Deanonimización del borrador + documento final | 15-30 min | H6 cerrado + Claude ha devuelto borrador | Documento final con datos reales en `04_Output predemanda/contestacion_demanda_SaRS1.docx` |

Hilos H1, H2 y H3 admiten paralelización: H3 es trabajo de código en el repo, independiente del caso concreto. H1 → H2 → H4 → H5 → H6 → H7 es la ruta crítica.

---

## 3. Bibliografía de apertura (qué leer al iniciar cualquier hilo)

Al abrir un hilo nuevo en Cowork, leer en este orden antes de tocar nada:

1. `G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes\STATUS.md` — fuente de verdad del proyecto.
2. Este documento, sección del hilo correspondiente.
3. La memoria persistente del proyecto (cargada automáticamente al arrancar Cowork) — especialmente las entradas `feedback_anon_logica_intacta.md`, `feedback_powershell_cd.md`, `feedback_doble_check.md`.
4. Solo para hilos H3, H4, H5: `docs/MEJORAS_FUTURAS.md`.
5. Solo para hilo H4: `docs/INTEGRACION_SUDESPACHO.md` no es necesario aquí (no se toca CRM en esta fase).

Checklist de apertura común (PowerShell, una sola vez al inicio):

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
git log --oneline -5
python -m pytest -q --tb=no
```

Tests verdes esperados: 470/470 a fecha 2026-05-12 (o el número actualizado en STATUS.md).

---

## 4. Hilo 1 — Apertura, corrección `_caso.md`, diagnóstico de PDFs, OCR

### 4.1 Objetivo

Dejar el caso SaRS1 con el `_caso.md` alineado a la realidad del CRM (cliente y posición) y los dos PDFs originales con capa de texto OCR escrita a `00_Input/04_Manual/_ocr/`. No se toca el contenido de los PDFs originales.

### 4.2 Pre-condiciones

Tests verdes. PDFs presentes en `04_Manual/`. Expediente 659 vinculado al case_id local en el frontmatter (ya está).

### 4.3 Paso a paso

**Paso 1.1 — Corregir `_caso.md`.** Editar el frontmatter del fichero `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\00_Input\_caso.md`:

- Campo top-level `cliente:` y `meta.cliente:` → `ENGEL & VÖLKERS SPAIN, S.L.U.`
- Añadir `meta.cliente_propio_clave: ENGEL_VOLKERS_SPAIN` y `meta.cliente_propio_id: '27'` para trazabilidad.
- Bajo `meta.observaciones:` (crear el bloque si no existe) añadir una línea: `posicion_procesal: DEMANDADO (rectificado en CRM el 2026-05-12; CaseMeta no persiste posicion explícita por diseño).`
- Actualizar `meta.actualizado_en` a la fecha-hora actual.

La edición se hace con el Edit tool de Cowork sobre el path Windows. No tocar el campo `case_id` ni `sudespacho_expedientes[0].id` (659).

**Paso 1.2 — Verificación de coherencia local↔CRM.** Ejecutar:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
python -c "from core.sudespacho_relations import verify_expediente_referencia; r = verify_expediente_referencia('659', 'judiciales', expected_referencia='SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros'); print(r)"
```

Si devuelve `match` o `crm_unreachable`, OK. Si devuelve `mismatch`, anotar la divergencia y resolverla manualmente en CRM antes de seguir.

**Paso 1.3 — Diagnóstico de los dos PDFs.** Script ad-hoc para conocer páginas, capa de texto e idioma estimado. Ejecutar (PowerShell, una sola línea):

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
python -c "import pypdf, pathlib; base=pathlib.Path(r'G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\00_Input\04_Manual'); [print(p.name, '|', len(pypdf.PdfReader(str(p)).pages), 'pp', '|', 'texto?', any(pypdf.PdfReader(str(p)).pages[i].extract_text().strip() for i in range(min(3, len(pypdf.PdfReader(str(p)).pages))))) for p in base.glob('Demanda_Std_*.pdf')]"
```

Reporta páginas y si hay texto extraíble en las 3 primeras páginas. Si **`texto? False`** en ambos, hace falta OCR (caso esperado).

**Paso 1.4 — OCR vía `core/anon/ocr.py`.** Crear subcarpeta `_ocr/` y aplicar OCR con idioma `spa`:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
$base = "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\00_Input\04_Manual"
New-Item -ItemType Directory -Force -Path "$base\_ocr" | Out-Null
python -c "from core.anon.ocr import ocr_pdf; from pathlib import Path; base=Path(r'$base'); [ocr_pdf(p, base / '_ocr' / p.name.replace('_compressed','_ocr'), idiomas='spa') for p in base.glob('Demanda_Std_*.pdf')]"
```

Tiempo: ~5-15 min por PDF según páginas. `ocrmypdf` usa Tesseract con idioma español. Output: `_ocr/Demanda_Std_1_ocr.pdf`, `_ocr/Demanda_Std_2_ocr.pdf`.

### 4.4 Criterios de aceptación

1. `_caso.md` editado y guardado, `meta.cliente` reza `ENGEL & VÖLKERS SPAIN, S.L.U.`, `meta.cliente_propio_clave` reza `ENGEL_VOLKERS_SPAIN`, observación de posición DEMANDADO añadida.
2. `verify_expediente_referencia` devuelve `match` o `crm_unreachable`.
3. `00_Input/04_Manual/_ocr/` contiene dos PDFs con capa de texto (verificable con `pypdf` extrayendo texto sin error).
4. PDFs originales `Demanda_Std_*_compressed.pdf` siguen intactos.

### 4.5 Entregables que quedan en disco

- `_caso.md` corregido.
- `00_Input/04_Manual/_ocr/Demanda_Std_1_ocr.pdf`.
- `00_Input/04_Manual/_ocr/Demanda_Std_2_ocr.pdf`.

### 4.6 Cierre del hilo

Actualizar la línea correspondiente del **mapa de hilos** (§2) marcando H1 como cerrado, con la fecha. No es necesario commitear cambios al repo (los originales del caso no van a git, están bajo `data/CASOS/` que está en .gitignore).

---

## 5. Hilo 2 — Split por tipo documental + revisión humana

### 5.1 Objetivo

Trocear los dos PDFs OCR-izados en piezas lógicas por tipo documental (cédula de emplazamiento, decreto de admisión a trámite, demanda, anexos), aplicando los 16 marcadores de `core/anon/separar.py`. Tras la ejecución automática, revisión humana y corrección manual si procede.

### 5.2 Pre-condiciones

H1 cerrado. `_ocr/` con los dos PDFs.

### 5.3 Paso a paso

**Paso 2.1 — Ejecución automática del split.** Crear subcarpeta `_split/` y lanzar `separar.py`:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
$base = "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\00_Input\04_Manual"
New-Item -ItemType Directory -Force -Path "$base\_split" | Out-Null
python -c "from core.anon.separar import separar_pdf_pipeline; from pathlib import Path; base=Path(r'$base'); [separar_pdf_pipeline(p, base / '_split') for p in (base / '_ocr').glob('Demanda_Std_*_ocr.pdf')]"
```

Nota técnica: la signatura exacta de `separar_pdf_pipeline` puede variar. El hilo H2 debe primero leer `core/anon/separar.py` y confirmar la API real (un Read del fichero antes de ejecutar). El comando anterior es orientativo.

**Paso 2.2 — Revisión humana del resultado.** Listar `_split/` y abrir cada PDF resultante:

```powershell
Get-ChildItem "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\00_Input\04_Manual\_split" | Format-Table Name, Length
```

Verificar que existe al menos una pieza de cada tipo esperado: `CEDULA_EMPLAZAMIENTO`, `DECRETO`, `DEMANDA`. Si la demanda lleva anexos numerados, deberían quedar agrupados bajo la pieza DEMANDA (super-absorbente) o como `DOC_ANEXO_*` separados.

**Paso 2.3 — Corrección manual si procede.** Si el split ha fallado en alguna costura (por ejemplo cédula y decreto unidos en un mismo PDF), trocear manualmente con `pdftk` o `pypdf` indicando rangos de página. Anotar el incidente para H5 (alimentará `MEJORAS_FUTURAS.md`).

### 5.4 Criterios de aceptación

1. `_split/` contiene al menos un PDF por cada pieza lógica realmente presente en los originales.
2. Cada PDF abre sin error y se corresponde con el tipo documental indicado en su nombre.
3. No quedan páginas huérfanas (un script puede comprobar que la suma de páginas en `_split/` coincide con la suma de páginas en `_ocr/`).
4. Anotaciones de errores de split (si los hubo) registradas en `07_AI cowork/_revision_anon_SaRS1.md` (crear el fichero si no existe).

### 5.5 Entregables

- `00_Input/04_Manual/_split/CEDULA_EMPLAZAMIENTO_*.pdf` (y/o nombres equivalentes generados por el módulo).
- `00_Input/04_Manual/_split/DECRETO_*.pdf`.
- `00_Input/04_Manual/_split/DEMANDA_*.pdf`.
- `00_Input/04_Manual/_split/DOC_*` opcionales.
- `07_AI cowork/_revision_anon_SaRS1.md` (esqueleto inicial, ver Anexo A).

---

## 6. Hilo 3 — Adaptación técnica de `core/anon/deanonimizar.py`

### 6.1 Objetivo

Extender `_localizar_mapa` en `core/anon/deanonimizar.py` para que reconozca el `_mapa_caso.json` que produce la fachada nueva `core/anon/api.py::anonimizar_caso`. Hoy solo busca `<doc>_mapa.json` por documento o un legacy `_anonimizados/`, lo que rompe la deanonimización para cualquier output generado por FeesDefender post-2026-05-07.

### 6.2 Pre-condiciones

Tests verdes (470/470). Independiente de H1 y H2 — se puede ejecutar en paralelo. Repo limpio en la rama de trabajo.

### 6.3 Paso a paso

**Paso 3.1 — Análisis previo.** Leer:
- `core/anon/deanonimizar.py` completo (función `_localizar_mapa` líneas ≈59-78 y CLI ≈132-157).
- `core/anon/mapa_caso.py` para entender estructura de `_mapa_caso.json`.
- `core/anon/api.py::anonimizar_documento` para entender cómo se referencia el mapa en el frontmatter del `.md` generado (campo tipo `mapa_caso_path` o similar).

**Paso 3.2 — Diseño.** Modificar `_localizar_mapa(ruta_md)` para que devuelva el primer mapa que encuentre buscando en este orden:

1. `<ruta_md>.parent / f"{ruta_md.stem.removesuffix('_anonimizado')}_mapa.json"` (comportamiento actual, prioridad alta para retrocompatibilidad).
2. Carpeta hermana `_anonimizados/` legacy (comportamiento actual).
3. **Nuevo**: si la ruta del `.md` contiene `06_Anonimizado` en su path, buscar `06_Anonimizado/_mapa_caso.json` en el ancestro inmediato.
4. **Nuevo (fallback)**: leer frontmatter YAML del `.md` y, si tiene campo `mapa_caso_path` o `mapa_entidades`, usarlo.

Mantener `_mapa.json` por documento con prioridad sobre `_mapa_caso.json` por compatibilidad hacia atrás (Expedientes Seguros).

**Paso 3.3 — Tests dedicados.** Nuevo fichero `tests/test_deanonimizar_mapa_caso.py`. Cobertura mínima:

1. `.md` con `_mapa.json` adyacente → usa el adyacente (regresión legacy).
2. `.md` sin `_mapa.json` adyacente, dentro de `<caso>/06_Anonimizado/`, con `_mapa_caso.json` en esa carpeta → usa el del caso.
3. `.md` con `mapa_caso_path` en frontmatter → usa el path indicado.
4. `.md` sin ningún mapa accesible → devuelve `None` (comportamiento actual).
5. Test de integración: anonimizar texto con `MapaEntidades` compartido → guardar como `_mapa_caso.json` → deanonimizar `.md` resultante → texto reconstruido coincide con original.

**Paso 3.4 — Documentación.** Añadir nota en docstring de `_localizar_mapa` enumerando los 4 niveles. Actualizar `docs/ARQUITECTURA.md` si la tabla de dependencias menciona `deanonimizar.py`.

**Paso 3.5 — Verificación end-to-end** (smoke, sin commitear todavía):

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
python -m pytest tests/test_deanonimizar_mapa_caso.py -v
python -m pytest -q --tb=no
```

Suite global debe seguir verde. Si rojo, no avanzar.

### 6.4 Criterios de aceptación

1. Tests nuevos verdes (mínimo 5).
2. Suite global ≥ 475/475 verde.
3. `_localizar_mapa` documentada con los 4 niveles.
4. Sin cambios en signatura pública de `deanonimizar()` ni en CLI.
5. Commit con mensaje sugerido: `feat(anon): deanonimizar.py reconoce _mapa_caso.json de la fachada nueva`.

### 6.5 Entregables

- `core/anon/deanonimizar.py` modificado.
- `tests/test_deanonimizar_mapa_caso.py` nuevo.
- `docs/ARQUITECTURA.md` actualizada si procede.
- Commit pusheado a remoto.

---

## 7. Hilo 4 — Anonimización + generación de markdown

### 7.1 Objetivo

Aplicar el motor `core/anon/api.py::anonimizar_caso` sobre las piezas separadas y generar los `.md` anonimizados en `06_Anonimizado/` con un `_mapa_caso.json` compartido.

### 7.2 Pre-condiciones

H2 cerrado (split correcto, piezas en `_split/`). H3 cerrado (deanonimización adaptada — no estrictamente bloqueante para anonimizar, pero sí para fase 7).

### 7.3 Paso a paso

**Paso 4.1 — Mover piezas a una ubicación que el motor escanee.** La fachada `anonimizar_caso` recorre `00_Input/` recursivamente y procesa los PDFs procesables (ver `core/anon/api.py::anonimizar_caso` líneas ≈363-451). Hay dos opciones:

- Opción A (recomendada): mover los PDFs de `_split/` a `00_Input/04_Manual/_split/` (ya están ahí desde H2) y dejar que el motor los recoja. Verificar que NO procese también los `_ocr/` ni los `_compressed.pdf` originales para evitar duplicados — si lo hace, mover originales y OCR fuera de `00_Input/` temporalmente (a una subcarpeta `.archivo/` que el motor ignora) o ajustar el patrón de glob.
- Opción B: aplicar `anonimizar_documento` por pieza, controlando el listado manualmente.

Decidir y dejar la decisión anotada en `07_AI cowork/_revision_anon_SaRS1.md`.

**Paso 4.2 — Lanzar anonimización.** Comando estándar con política SALTAR:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
python -m scripts.anonimizar_caso "SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros" --tipo "Juicio Ordinario" --politica SALTAR
```

Tiempo: ~3-8 minutos por documento procesado (Presidio + spaCy en CPU). Primera ejecución carga el singleton NLP (~1.5 GB RAM); ejecuciones subsiguientes en la misma sesión Python son inmediatas.

**Paso 4.3 — Inspección del log.** Verificar que `07_AI cowork/_anonimizador_log.md` tiene una entrada nueva con timestamp del lanzamiento, política `SALTAR`, conteos coherentes (documentos procesados = piezas en `_split/`).

**Paso 4.4 — Listado de output.** Confirmar contenido de `06_Anonimizado/`:

```powershell
Get-ChildItem "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\06_Anonimizado" | Format-Table Name, Length
```

Esperado: un `.md` por pieza + `_mapa_caso.json`.

### 7.4 Criterios de aceptación

1. `06_Anonimizado/` existe con al menos un `.md` por pieza presente en `_split/`.
2. `_mapa_caso.json` existe y es JSON válido.
3. Log `07_AI cowork/_anonimizador_log.md` registra la ejecución con `procesados>0, errores=0`.
4. Frontmatter de cada `.md` incluye `origen_sha256`, `case_id`, `tipo_proc`, `politica`, fecha.

### 7.5 Entregables

- `06_Anonimizado/*.md`.
- `06_Anonimizado/_mapa_caso.json`.
- Nueva entrada en `07_AI cowork/_anonimizador_log.md`.

---

## 8. Hilo 5 — Verificación forense + creación del fixture gold-standard

### 8.1 Objetivo

Revisar exhaustivamente el output de H4, registrar todos los errores categorizados en tabla, corregir manualmente el `_mapa_caso.json` para limpiar el material que verá Claude, fijar el caso como primer fixture gold-standard del proyecto, y alimentar `docs/MEJORAS_FUTURAS.md` con las mejoras detectadas.

Este es el hilo más manual y más importante del bucle de mejora continua. No tiene atajos.

### 8.2 Pre-condiciones

H4 cerrado. Tiempo dedicado sin interrupciones (estimar 45-90 min).

### 8.3 Paso a paso

**Paso 5.1 — Tabla de revisión.** Abrir `07_AI cowork/_revision_anon_SaRS1.md` (creado en H2) y, por cada `.md` de `06_Anonimizado/`, completar la tabla del Anexo A. Categorías de error:

- **FN** (falso negativo): PII que se ha colado sin etiquetar. Crítico para confidencialidad. Bloqueante.
- **FP** (falso positivo): operador jurídico, ley, juzgado u otro elemento no-PII anonimizado por error. No bloqueante pero deteriora la lectura.
- **MAP** (error de mapeo): la misma entidad recibe dos etiquetas distintas en documentos distintos (rotura de coherencia del mapa compartido) o etiquetas distintas reciben el mismo valor en el mapa.
- **SPLIT** (error de split, retroactivo): la pieza está cortada incorrectamente, una pieza incluye texto de otra, falta una pieza, sobra una pieza.
- **OCR** (error de OCR): texto ilegible, caracteres mal reconocidos, columnas mezcladas.

Cada fila de la tabla: documento, página o sección, categoría, texto original (cuidado: aquí sí estás manejando PII, no copies fuera del documento), etiqueta esperada, comentario, prioridad sugerida (alta/media/baja).

**Paso 5.2 — Corrección del `_mapa_caso.json`.** Para cada FN: añadir manualmente la entrada al mapa con etiqueta nueva (`[NOMBRE_N+1]` siguiendo la numeración existente). Para cada FP: eliminar la entrada del mapa.

Como `REPROCESAR` recoge el mapa pero no rehace los `.md` que ya tienen el SHA-256 correcto, hay dos caminos:

- **Quirúrgico** (recomendado si los errores son pocos): editar manualmente los `.md` para reflejar la corrección. Más rápido para volúmenes pequeños.
- **Reproceso completo**: lanzar `python -m scripts.anonimizar_caso "<case_id>" --politica REPROCESAR`. Regenera todos los `.md` desde cero usando el mapa actualizado. Caveat: las entidades nuevas que el motor detecte en esta segunda pasada pueden recibir etiquetas con numeración alta (`[NOMBRE_50]` aunque sea la primera vez que aparece esa persona) por preservación de contadores.

Anotar en la tabla cuál de los dos caminos se eligió y por qué.

**Paso 5.3 — Verificación post-corrección.** Releer 1-2 `.md` corregidos para confirmar que la PII desapareció y que los operadores jurídicos volvieron a su forma original.

**Paso 5.4 — Creación del fixture gold-standard.** Crear directorio y copiar:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
New-Item -ItemType Directory -Force -Path "tests\fixtures\anon\SaRS1\input" | Out-Null
New-Item -ItemType Directory -Force -Path "tests\fixtures\anon\SaRS1\expected" | Out-Null

# Originales OCR-izados (input del split + anon)
Copy-Item "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\00_Input\04_Manual\_ocr\*.pdf" "tests\fixtures\anon\SaRS1\input\"

# Output anonimizado corregido (expected)
Copy-Item "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\06_Anonimizado\*.md" "tests\fixtures\anon\SaRS1\expected\"
Copy-Item "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\06_Anonimizado\_mapa_caso.json" "tests\fixtures\anon\SaRS1\expected\"

# Tabla de revisión (documentación del fixture)
Copy-Item "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\07_AI cowork\_revision_anon_SaRS1.md" "tests\fixtures\anon\SaRS1\REVISION.md"
```

Caveat de privacidad: estos PDFs y `.md` contienen PII real (incluso anonimizados, el mapa la incluye). El directorio `tests/fixtures/anon/SaRS1/` debe estar **en `.gitignore`** o documentado como fixture local. Verificar la política antes de commitear. Alternativa: el fixture vive solo en local y se referencia por path absoluto en el test, con `pytest.skip()` si no está presente.

**Paso 5.5 — Test de regresión sobre el fixture.** Nuevo fichero `tests/test_anon_regresion_SaRS1.py`. Test mínimo:

1. Skip si el fixture no existe localmente.
2. Cargar los PDFs de `tests/fixtures/anon/SaRS1/input/`.
3. Anonimizar con la fachada actual (política `REPROCESAR` para forzar recálculo).
4. Comparar output con `tests/fixtures/anon/SaRS1/expected/`. Asertar igualdad página por página, mapa por entrada.

Si la regresión falla en el futuro tras un cambio en el motor, el desarrollador deberá: o bien arreglar la regresión, o bien actualizar el `expected/` con justificación documentada en el commit.

**Paso 5.6 — Alimentación de `docs/MEJORAS_FUTURAS.md`.** Por cada error categorizado en la tabla, generar una entrada nueva en `MEJORAS_FUTURAS.md` siguiendo la estructura existente. Agrupar por categoría (FN/FP/MAP/SPLIT/OCR). Cada entrada debe incluir: descripción del problema, ejemplo concreto del caso SaRS1 (sin PII identificable — generalizar), prioridad sugerida, esfuerzo estimado.

**Paso 5.7 — Actualizar STATUS.md.** Añadir al "Estado general" una línea sobre el fixture gold-standard SaRS1 y al "Última actualización" un resumen del hilo.

### 8.4 Criterios de aceptación

1. `07_AI cowork/_revision_anon_SaRS1.md` con tabla completa (al menos columna comentario "OK" en todas las filas verificadas).
2. `_mapa_caso.json` corregido. Falsos negativos eliminados de los `.md`, falsos positivos restaurados.
3. `tests/fixtures/anon/SaRS1/` creado con input + expected + REVISION.md.
4. `tests/test_anon_regresion_SaRS1.py` verde (o skip controlado si el fixture es local-only).
5. `docs/MEJORAS_FUTURAS.md` actualizado con al menos una entrada nueva por categoría de error encontrada.
6. STATUS.md actualizado.

### 8.5 Entregables

- Tabla de revisión completa.
- `_mapa_caso.json` corregido + `.md` corregidos.
- Fixture gold-standard.
- Test de regresión.
- `MEJORAS_FUTURAS.md` enriquecido.
- STATUS.md actualizado.
- Commit con mensaje: `feat(anon): primer fixture gold-standard SaRS1 + tabla de revisión forense`.

---

## 9. Hilo 6 — Subida manual al CRM + entrega a Claude frontier

### 9.1 Objetivo

Subir los PDFs OCR-izados y separados al gestor documental del expediente 659 en sudespacho.net, y entregar los `.md` anonimizados a Claude frontier para que produzca un borrador de contestación a la demanda.

### 9.2 Pre-condiciones

H5 cerrado. PHPSESSID válida si el flujo de upload manual del CRM la exige.

### 9.3 Paso a paso

**Paso 6.1 — Subida manual al CRM.** Abrir `https://tnm.sudespacho.net/tnm/gestion/expedientes-judiciales/659` en navegador. Ir al gestor documental (gdocu). Subir manualmente los PDFs de:

- `00_Input/04_Manual/_ocr/` (los dos originales OCR-izados, como referencia íntegra del escaneo recibido).
- `00_Input/04_Manual/_split/` (las piezas separadas por tipo documental, organizadas en la carpeta del gestor según la taxonomía del despacho — típicamente Civil → 1ª Instancia → Declarativo → Cédula / Decreto / Demanda / Anexos).

Anotar en `07_AI cowork/_revision_anon_SaRS1.md` qué se subió y dónde quedó.

**Paso 6.2 — Preparación del prompt para Claude frontier.** Redactar prompt para una conversación nueva de Claude.ai web (o Cowork con perfil distinto que no toque el repo de FeesDefender). Estructura sugerida:

> Tengo este caso: demanda recibida por mi cliente Engel & Völkers Spain, S.L.U., como parte demandada. Te paso los documentos anonimizados (cédula de emplazamiento, decreto de admisión a trámite, demanda y anexos). Necesito que prepares un borrador de contestación a la demanda con la estructura procesal estándar de la Sala 1ª del Tribunal Supremo: hechos, fundamentos jurídicos, alegaciones a las pretensiones del actor, suplico. Conserva las etiquetas anonimizadas tal como aparecen ([NOMBRE_1], [DIRECCION_1], etc.) — no las sustituyas por valores inventados. Devuélveme el borrador en formato markdown.

Adjuntar los `.md` de `06_Anonimizado/` al chat.

**Paso 6.3 — Recepción del borrador.** Cuando Claude devuelva el borrador anonimizado, guardarlo en:

```
G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\08_Borradores\contestacion_demanda_SaRS1_v1_anonimizado.md
```

Crear la carpeta `08_Borradores/` si no existe. Es una carpeta nueva no contemplada en `core/config.py::INPUT_SUBDIRS` (esto solo afecta a borradores, no al intake). Decisión: dejarla local en el caso, sin cablear en core, hasta que el flujo borrador-iterativo se estabilice.

### 9.4 Criterios de aceptación

1. CRM 659 / gdocu contiene los PDFs OCR-izados y separados, organizados en la rama Civil correspondiente.
2. Anotación en `_revision_anon_SaRS1.md` con rutas y timestamps.
3. Borrador anonimizado de Claude guardado en `08_Borradores/contestacion_demanda_SaRS1_v1_anonimizado.md`.

### 9.5 Entregables

- Documentos en CRM.
- Borrador anonimizado en local.

---

## 10. Hilo 7 — Deanonimización del borrador + documento final

### 10.1 Objetivo

Convertir el borrador anonimizado de Claude en el documento final con datos reales, listo para revisión jurídica y firma.

### 10.2 Pre-condiciones

H3 cerrado (deanonimización adaptada al `_mapa_caso.json`). H6 cerrado (borrador recibido).

### 10.3 Paso a paso

**Paso 7.1 — Deanonimización.**

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
python -m core.anon.deanonimizar "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\08_Borradores\contestacion_demanda_SaRS1_v1_anonimizado.md"
```

Output: `contestacion_demanda_SaRS1_v1_deanonimizado.md` en la misma carpeta.

**Paso 7.2 — Revisión jurídica del borrador.** Lectura completa. Anotar correcciones de fondo en el `.md`. Validar fundamentos jurídicos, encajes procesales, ausencia de PII no resuelta (si la deanonimización ha dejado alguna etiqueta sin sustituir significa que la entidad no estaba en el mapa — investigar).

**Paso 7.3 — Conversión a `.docx` con el skill `escritos-judiciales`.** Una vez el `.md` está limpio, generar `.docx` final con el formato Sala 1ª TS del despacho (Times New Roman 12, márgenes 2,5 cm, interlineado 1,5, párrafos numerados, etc.). Esto se hace en una sub-sesión de Cowork con el skill activado.

Output: `04_Output predemanda/contestacion_demanda_SaRS1.docx` (o similar).

### 10.4 Criterios de aceptación

1. `contestacion_demanda_SaRS1_v1_deanonimizado.md` sin etiquetas `[...]` sin resolver.
2. Revisión jurídica realizada (signed-off por Nikolai).
3. `.docx` final generado con formato del despacho.

### 10.5 Entregables

- `08_Borradores/contestacion_demanda_SaRS1_v1_deanonimizado.md`.
- `04_Output predemanda/contestacion_demanda_SaRS1.docx`.
- Caso listo para presentación procesal.

---

## 11. Anexo A — Plantilla de la tabla de revisión forense

Archivo destino: `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros\07_AI cowork\_revision_anon_SaRS1.md`.

Contenido inicial sugerido:

```markdown
# Revisión forense anonimización — SaRS1

> Tabla de errores detectados en la primera pasada del motor `core/anon/api.py::anonimizar_caso`.
> Sirve de input para `docs/MEJORAS_FUTURAS.md` y de base para el fixture gold-standard.

## Metadatos de la ejecución

- Caso: SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros
- Fecha ejecución H4: <YYYY-MM-DD HH:MM>
- Política: SALTAR
- Tipo procedimiento: Juicio Ordinario
- Documentos procesados: <N>
- Versión del motor (commit): <git rev-parse --short HEAD>

## Errores

| # | Documento | Pág/Sec | Categoría (FN/FP/MAP/SPLIT/OCR) | Texto original (cuidado PII) | Etiqueta esperada / valor esperado | Comentario | Prioridad |
|---|-----------|---------|----------------------------------|------------------------------|------------------------------------|-----------|-----------|
| 1 | | | | | | | |

## Decisiones tomadas

- Camino de corrección: <quirúrgico / reproceso completo>.
- Motivo: <...>.

## Resumen para `MEJORAS_FUTURAS.md`

- <una línea por mejora propuesta, agrupada por categoría>.
```

---

## 12. Anexo B — Snippets PowerShell habituales

Variable común al inicio de cualquier hilo:

```powershell
$proj  = "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
$caso  = "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros"
cd $proj
```

Listado rápido del estado del caso:

```powershell
Get-ChildItem "$caso\00_Input\04_Manual" -Recurse -File | Select Name, Length, LastWriteTime
Get-ChildItem "$caso\06_Anonimizado" -ErrorAction SilentlyContinue | Select Name, Length, LastWriteTime
```

Reanonimizar forzando reproceso completo:

```powershell
cd $proj
python -m scripts.anonimizar_caso "SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros" --tipo "Juicio Ordinario" --politica REPROCESAR
```

Verificación local↔CRM:

```powershell
cd $proj
python -c "from core.sudespacho_relations import verify_expediente_referencia; print(verify_expediente_referencia('659', 'judiciales', expected_referencia='SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros'))"
```

---

## 13. Anexo C — Decisiones pendientes y riesgos abiertos

**Pendiente C1 — Política del directorio `tests/fixtures/anon/SaRS1/` respecto a git.** Contiene PII real (incluso anonimizada, vía el mapa). Tres opciones: (a) añadir a `.gitignore` y mantener fixture local-only, (b) borrar PII real del mapa antes de commitear y commitear con datos sintéticos equivalentes, (c) crear un fixture sintético separado inspirado en SaRS1 pero sin PII. Decidir en H5.

**Pendiente C2 — Upload a CRM vía REST.** Hoy se hace manual (D4). Si se acumulan muchos casos, justificará abrir un hilo dedicado para capturar HAR del upload SPA y construir un endpoint en `core/sudespacho_upload.py`. No urgente.

**Pendiente C3 — Persistencia de `posicion` en `CaseMeta`.** Hoy se deriva del `tipo_caso`, lo cual es ambiguo para la categoría OTROS donde la posición es libre. Plantear en sesión futura añadir campo `posicion` al frontmatter del `_caso.md` y al modelo `CaseMeta`. No bloqueante.

**Pendiente C4 — Capa de feedback en UI Streamlit.** El bucle de mejora actual es artesanal. La mejora 7 de `MEJORAS_FUTURAS.md` (UI de edición manual del mapa) cerraría esta lacuna. Estimación ≈150 líneas Streamlit. No bloqueante para este caso pero candidata firme para sesión dedicada tras H5.

**Riesgo R1 — Detección errónea de tipo documental en split.** Si los marcadores hardcodeados de `core/anon/separar.py` no reconocen el formato concreto del juzgado de Santander, el split puede fragmentar mal. Mitigado por revisión humana en H2.

**Riesgo R2 — Numeración de etiquetas tras `REPROCESAR`.** Como `REPROCESAR` preserva contadores del mapa, una segunda pasada puede generar etiquetas con números altos para entidades nuevas. No es bloqueante pero deteriora legibilidad. Documentar como mejora futura.

**Riesgo R3 — Capa de OCR insuficiente.** Si los PDFs originales tienen calidad de escaneo baja (cliente fotografía con móvil en lugar de escáner), el OCR `spa` puede dejar texto ilegible. Mitigación: revisión en H1 paso 1.3 y, si procede, repetir con `--oversample 600` o `--rotate-pages`.

---

## 14. Trazabilidad

Cada hilo cierra escribiendo en este documento, en la tabla §2, la fecha de cierre y un enlace al commit (si aplica). Esto convierte el documento en bitácora del desarrollo.

| Hilo | Estado | Fecha cierre | Commit/Notas |
|---|---|---|---|
| H1 | Cerrado | 2026-05-12 | `_caso.md` corregido (cliente E&V Spain ID 27 + observación DEMANDADO). `verify_expediente_referencia` → `match: True`. Diagnóstico: 35 pp + 39 pp, sin capa de texto. OCR `spa` aplicado vía `python -m ocrmypdf` (workaround por bug `ocrmypdf.ocr(**args)` documentado en `MEJORAS_FUTURAS.md §11`). Originales intactos. Side-fix: corregido orden de argumentos de `verify_expediente_referencia` en §4.3 y §12 del plan. Señales OCR para H5: docs con `lots of diacritics` (doc 1 pp 3,13,29,30,35; doc 2 pp 2,9,30,33); doc 2 pp 20-21 saltadas (`too few characters`); varias páginas sin rotar por baja confianza. |
| H2 | Cerrado | 2026-05-12 | Split automático insuficiente (2 piezas vs 4 lógicas). PDF1: cédula+decreto absorbidos por DEMANDA (`TIPOS_SUPER_ABSORBENTES`) porque el OCR transcribió "CÉDULA DE EMPLAZAMIENTO" como `"_ 1 Sección Civil..."` y "DECRETO" solo aparece en texto corrido. PDF2: cero marcadores → fallback `DOCUMENTO`. Troceo manual aplicado con `pypdf.PdfWriter` (script ad-hoc temporal en `%TEMP%`, no versionado): PDF1 → `01_CEDULA_EMPLAZAMIENTO_01.pdf` (pp 1-2) + `02_DECRETO_01.pdf` (pp 3-5) + `03_DEMANDA_01.pdf` (pp 6-35). PDF2 → `01_DOC_ANEXO_01.pdf` (pp 1-39) como bloque único (decisión informada: OCR muy degradado en pp 1-20, troceo por DOC numerado sería frágil; calidad del output anonimizado no se ve afectada por el mapa compartido). Sanity check páginas: 74/74 OK. 4 criterios §5.4 marcados. Esqueleto de `07_AI cowork/_revision_anon_SaRS1.md` creado con plantilla Anexo A + bitácora del split + 2 incidencias SPLIT documentadas para H5. Caso vive en `data/CASOS/` (.gitignore) — solo se versiona la actualización de este plan. |
| H3 | Cerrado | 2026-05-12 | Commit `d22febd`. `core/anon/deanonimizar.py::_localizar_mapa` extendida a 4 niveles (legacy adyacente, legacy `_para_IA`, mapa de caso `06_Anonimizado/_mapa_caso.json`, fallback por frontmatter `mapa_caso_path`/`mapa_entidades`). Helper aislado `_mapa_desde_frontmatter` con import diferido de `core.utils.read_md`. Firma pública y CLI intactas. `tests/test_deanonimizar_mapa_caso.py` con 13 tests dedicados (regresión nivel 1, prioridad legacy>caso, `_para_IA`, mapa de caso, subcarpeta, frontmatter absoluto+alias+relativo, helper sin frontmatter, None sin mapa, None frontmatter inexistente, round-trip e2e, FileNotFoundError sin mapa) — todos verdes. `docs/ARQUITECTURA.md` con 2 filas nuevas en tabla de dependencias (`mapa_caso.py` constantes ↔ `deanonimizar.py`, `api.py` frontmatter ↔ `_mapa_desde_frontmatter`). Suite global verde (483/483). Sin tocar regex/listas/thresholds del motor (memoria `feedback_anon_logica_intacta`). |
| H4 | Cerrado | 2026-05-12 | **Opción B** (Opción A inviable: `_listar_documentos` ignora `_split/` por regla "parte path empieza por `_`", api.py L318-334). Script ad-hoc en `%TEMP%\h4_sars1_anon.py` (no versionado, mismo patrón que el troceo manual de H2) replicando `anonimizar_caso` con listado explícito de las 4 piezas de `_split/`. 4 procesados / 0 errores en ~5 min. Entregables: `06_Anonimizado/{01_cedula_emplazamiento_01,02_decreto_01,03_demanda_01,01_doc_anexo_01}.md` + `_mapa_caso.json` + entrada en `_anonimizador_log.md` con timestamp `2026-05-12T12:28:06`. Conteo de entidades nuevas: cédula 13, decreto 10, demanda 35, anexo 126. Versión del motor: commit `d22febd` (sin cambios; H4 no toca código). **Side-fix documentado**: destapado segundo bug latente — `core/utils.py::_CASE_ID_NEW` rechaza case_ids con `(SIN REFERENCIA)` (categoría OTROS). Workaround: monkey-patch local en el script ad-hoc. Bug registrado como punto 12 en `docs/MEJORAS_FUTURAS.md`. Las 7 notas sueltas observadas al ojear el output (N1-N7: 1 MAP duplicación tildes, 4 FP nominales/estructurales, 1 OCR degradado en PDF2, 1 FP regex NIG-como-IBAN) anotadas en `07_AI cowork/_revision_anon_SaRS1.md` para procesamiento sistemático en H5. |
| H5 | Cerrado | 2026-05-12 | **Sin commit pendiente hasta que el usuario ejecute los dos scripts ad-hoc del expediente y confirme suite verde.** Tabla forense completa en `07_AI cowork/_revision_anon_SaRS1.md` (63 filas: 8 FN bloqueantes, 38 FP, 8 MAP, 2 SPLIT ya resueltos en H2, 2 OCR no recuperables). 3 decisiones fijadas: D-H5-1 fixture local-only en `.gitignore` (opción a del Pendiente C1, ahora cerrado), D-H5-2 camino quirúrgico vía script auxiliar Python (`REPROCESAR` regeneraría los mismos FP sin tocar regex/listas/thresholds del motor — D8 + memoria `feedback_anon_logica_intacta`), D-H5-3 OCR del PDF2 pp 1-20 marcado "no recuperable en H5" + entrada alta prioridad en `MEJORAS_FUTURAS.md` (opción ii). Script `07_AI cowork/_h5_sars1_corregir_mapa.py` (no versionado, mismo patrón H2/H4): backup `.bak.h5` + reconstrucción de `_mapa_caso.json` (155→~50 etiquetas, eliminación FP + consolidación MAP + adición FN) + sustituciones en los 4 `.md` + log `_h5_correccion_log.txt`. Script auxiliar `07_AI cowork/_h5_sars1_crear_fixture.ps1` para el fixture (copia input + expected snapshot motor pre-H5 + expected_corregido post-H5 + REVISION.md). `tests/test_anon_regresion_SaRS1.py` con `pytestmark = pytest.mark.skipif` colectivo si fixture no presente. `.gitignore` actualizado con regla `tests/fixtures/anon/`. `docs/MEJORAS_FUTURAS.md` enriquecido con 10 entradas nuevas (puntos 13-22) cubriendo FN/FP/MAP/OCR + refactor `anonimizar_caso` para listado explícito de documentos. STATUS.md actualizado con cierre de H5 + apertura de H6. Commit sugerido (ejecutar tras scripts del usuario): `feat(anon): primer fixture gold-standard SaRS1 + tabla de revisión forense`.
| H6 | Pendiente | | |
| H7 | Pendiente | | |
