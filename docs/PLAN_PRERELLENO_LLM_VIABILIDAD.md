---
estado: revisar
dueño: Nikolai Tyukhay
---

> **Nota de auditoría (2026-07-18, corregida):** el diseño de este plan (motor
> determinista `core/viabilidad.py` + clasificador Haiku/extractor Sonnet vía
> API sobre docs anonimizados + botón Streamlit) **no es el camino que se
> construyó**. El prerelleno vivo es la skill `viabilidad-prerelleno` (Claude
> en sesión lee `00_Input/` crudo directamente, sin API ni pipeline de
> anonimización previo).
>
> Corrección: `core/scorer.py` y `core/viability.py` **no son código muerto**.
> Se importan y se ejecutan desde `core/pipeline.py::run` (import en la
> línea 14; llamadas `scorer.score(case_id)` y `viability.analyze(case_id)` en
> las líneas 89-90), que a su vez está cableado en `streamlit_app.py` (pestaña
> "Ejecutar pipeline", botón que invoca `pipeline.run(...)`) y cubierto por
> `tests/test_pipeline.py` (suite verde). Lo que **no** se construyó es el
> diseño de pre-relleno por LLM de ESTE plan (clasificador Haiku + extractor
> Sonnet sobre docs anonimizados, Fases 2-5 más abajo): ese camino quedó sin
> implementar y el flujo recomendado hoy para pre-rellenar viabilidad es la
> skill `viabilidad-prerelleno`. Por eso el estado es `revisar` (pendiente de
> que Nikolai ratifique si el plan se archiva formalmente o se retoma en algún
> punto) y no `historico` — la pieza de código que este plan iba a sustituir
> sigue viva y en uso, aunque el plan en sí no avanzó de la fase de diseño.
>
> Cita de origen del hallazgo "flujo vivo es la skill": `PLAN.md`, sección
> `[APARCADO-INTAKE-CRM-A-LLM]` (hallazgos del re-brainstorming 2026-07-10),
> no la línea 51 citada originalmente.

# Plan — Pre-relleno LLM del informe de viabilidad

> **Estado**: planificación cerrada, implementación pendiente.
> **Trazado en**: sesión 22, 2026-05-19.
> **Estimación total**: 9-12 sesiones (~3-4 semanas de trabajo, consistente con
> la estimación de la memoria `project_plantillas_viabilidad.md` punto 3).
> **Recomendación operativa**: arrancar únicamente por **Fase 1**; resto en
> escalera cuando haya ventana. Cada fase entrega valor por sí sola.

---

## 1. Objetivo

Pre-rellenar automáticamente el `Informe viabilidad - <case_id>.xlsx` usando un
LLM que analice los documentos del Drive de Engel & Völkers volcados en el
intake (`01_Drive EV/`). El equipo (Administración + abogado) revisa el output
del LLM y lo integra manualmente en el informe vivo, manteniendo el control
humano explícito.

## 2. Decisiones cerradas (sesión 22, 2026-05-19)

- **D1 — Camino de trabajo**: cuestionario → derivación a ficha. El LLM
  responde las 82 preguntas de `cuestionario_viabilidad.yaml`; reglas
  deterministas en `core/viabilidad.py` derivan los scores de los 14 hitos de
  `informe_viabilidad.yaml`. NUNCA escribe directamente en el XLSX que edita
  la Administración.
- **D2 — Disparo**: botón manual «🤖 Pre-rellenar viabilidad con IA» en la UI
  Streamlit del caso. Reversible, controlable, sin sorpresas en coste API.
- **D3 — Triaje de documentos**: clasificador LLM previo etiqueta cada doc
  del Drive por rol probatorio antes de invocar al extractor sobre el subset
  relevante. Más robusto a nombres caóticos que una whitelist por patrón.
- **D4 — Modelo**: Claude Haiku 4.5 para clasificador + Claude Sonnet 4.6 para
  extractor, ambos vía API, sobre docs anonimizados con el pipeline SaRS1
  (`core/anon/api.py` → `08_Para frontier/`). Razones:
  - Calidad de extracción jurídica indispensable para confianza del equipo;
    Ollama local en CPU no alcanza el listón hoy en español jurídico.
  - Pipeline anon ya construido y testeado (SaRS1 H1-H7, primer fixture
    gold-standard del proyecto).
  - Coste marginal: ~0,30-0,50 €/caso (clasificador) + 1-2 €/caso (extractor)
    vs. 1-2h de Administración a coste interno.
  - Trazabilidad RGPD limpia (memoria `project_cumplimiento_ria_rgpd.md`).
  - Ollama queda como optimización futura para sustituir Haiku en clasificación
    cuando haya un modelo local que iguale calidad.
- **D5 — Output**: artefactos en `02_Analisis/_llm/` (regenerable) +
  `02_Analisis/Informe viabilidad LLM - <case_id>.xlsx` (output paralelo al
  informe humano, nunca lo sobrescribe).

## 3. Pendiente de Fase 0 (decisiones a cerrar antes de Fase 1)

- **[PENDIENTE]** Inclusión de `BAD_DEBT` en `INFORME_VIABILIDAD_TIPOS`
  (mismo pendiente que `[SIGUIENTE-VIABILIDAD-BAD-DEBT]`). Si entra, definir
  si reutiliza el cuestionario actual o requiere uno adaptado al devengo de
  honorarios. Ver memoria `project_plantillas_viabilidad.md` punto 0.
- **[PENDIENTE]** Modelo del clasificador (Fase 2): confirmar Haiku por
  defecto o abrir flag `.env` para Ollama. El clasificador es la pieza con
  menor sensibilidad jurídica — un falso negativo se compensa porque el
  extractor del paso siguiente ve también los docs marcados como `otros` con
  menor prioridad.
- **[PENDIENTE]** Prioridad de arreglar los bugs latentes del pipeline anon
  que tocan este flujo:
  - `core/anon/ocr.py::ocr_pdf` (kwargs vs posicionales —
    `MEJORAS_FUTURAS.md §11`). Sin éste, casos con PDFs sin OCR fallan.
  - `core/utils.py::_CASE_ID_NEW` rechazando `(SIN REFERENCIA)`
    (`MEJORAS_FUTURAS.md §12`). Sin éste, casos OTROS sin ID GO fallan.

No bloquean Fase 1 si el primer caso de validación es uno con OCR ya hecho y
con ID GO formal, pero hay que resolverlos antes de generalizar.

---

## 4. Fases de implementación

### Fase 1 — Pre-procesado del Drive E&V por caso

**Esfuerzo**: 2 sesiones (~8-12 h) + un caso real de validación.

**Entrega**: nuevo módulo `core/viabilidad/intake.py`. Responsabilidad: tomar
un caso ya pulled (`01_Drive EV/` lleno) y dejar los documentos listos para
LLM en `02_Analisis/_llm/`.

**Pipeline** (reutilizando piezas existentes):

1. **Listar y filtrar**. Recoger todos los `.pdf`, `.docx`, `.eml`, `.msg`
   del Drive E&V. Filtrar fotos (`.jpg`, `.png` salvo si vienen sueltas — DNIs
   escaneados), presentaciones (`.ppt`, `.pptx`) y plantillas vacías de E&V.
2. **OCR condicional**. Para cada PDF, detectar capa de texto. Si está
   ausente, encolar a `ocrmypdf` (mismo wrapper que SaRS1 — `core/anon/ocr.py`,
   una vez corregido el bug de Fase 0). Output a `02_Analisis/_llm/01_ocr/`.
3. **Conversión a Markdown**. Todos los formatos a `.md` con frontmatter
   mínimo (path original, hash SHA-256, tipo MIME). Usar `markitdown` o
   `unstructured` — pendiente bench rápido. Output `02_Analisis/_llm/02_md/`.
4. **Anonimización**. Llamar al motor `core/anon/api.py::anonimizar_caso` con
   listado explícito (requiere `MEJORAS_FUTURAS §22` cerrado o, mientras
   tanto, script ad-hoc como SaRS1 H4). Output `02_Analisis/_llm/03_anon/` +
   `_mapa_caso.json`.

**Idempotencia**: cada paso comprueba hash del input antes de reprocesar.
`02_Analisis/_llm/` se considera output regenerable (a diferencia de
`06_Anonimizado/` del flujo SaRS1, que es entrega manual al frontier).

**Valor independiente del LLM**: una vez tienes los docs anonimizados, ya
puedes llevártelos manualmente a una sesión Claude.ai con tu perfil personal
y obtener un primer análisis sin esperar a `core/viabilidad/`. Es exactamente
lo que SaRS1 H6 demostró que funciona.

### Fase 2 — Clasificador de documentos

**Esfuerzo**: 1 sesión (~4-6 h con prompt + tests + revisión sobre 3-4 casos
reales para tarar).

**Entrega**: nuevo módulo `core/viabilidad/clasificador.py`. Para cada `.md`
anonimizado, asigna rol probatorio.

**Taxonomía cerrada** (alineada con `fuentes_probables_validas` del
cuestionario):

`encargo`, `oferta`, `arras`, `escritura`, `hoja_visita`, `exposes`, `dni`,
`nota_simple`, `email`, `whatsapp`, `entrevista`, `crm`, `otros`.

**Prompt al modelo**: nombre del fichero + primeras 800 palabras del `.md`
→ JSON con `{rol, confianza, justificacion_corta}`. Output
`02_Analisis/_llm/_clasificacion.json` con un objeto por documento.

**Modelo**: Haiku por defecto, configurable a Ollama vía `.env`. Decisión
final pendiente de Fase 0 punto 2.

### Fase 3 — Extractor de respuestas al cuestionario

**Esfuerzo**: 3-4 sesiones (~15-20 h). La parte más cara es iterar prompts
sobre 3-5 casos reales hasta que las 82 respuestas sean consistentes.

**Entrega**: nuevo módulo `core/viabilidad/extractor.py`. Núcleo del
horizonte 3 que la memoria `project_plantillas_viabilidad.md` estima en 3-4
semanas.

**Por cada pregunta del `cuestionario_viabilidad.yaml`**:

1. **Filtrar docs candidatos** según `fuente_probable` de la pregunta cruzado
   con `_clasificacion.json`. Ej.: pregunta `cap_08` (¿se firmó el encargo?)
   → solo docs clasificados como `encargo` o `crm`.
2. **Construir prompt estructurado** con: texto de la pregunta +
   `objetivo_probatorio` + `tipo_respuesta` esperada (boolean, fecha, enum,
   texto_libre) + opciones si aplica + docs candidatos como contexto.
3. **Invocar Sonnet** pidiendo JSON:
   `{respuesta, cita_textual, ruta_documento, paginas, confianza_0_1, observaciones}`.
4. **Validar el output** contra el `tipo_respuesta` declarado. Reintento con
   corrección si no parsea.
5. **Persistir** en `02_Analisis/_cuestionario_respuestas.json`.

**Anti-alucinación crítica**: prompts incluyen instrucción literal de la
regla del proyecto («solo cita lo que está en contexto, devuelve
`pendiente`/`null` si la información no aparece en los documentos
proporcionados»). Mismo patrón que el prompt SaRS1 H6 ya validado.

**Presupuesto de tokens**: las preguntas de captación (`cap_*`) suelen
necesitar el encargo completo (~5-15k tokens). Las de visita/oferta/escritura,
los docs específicos (~3-8k cada uno). Total por caso típico: ~150-300k
tokens de input → 1-2 € con Sonnet 4.6.

### Fase 4 — Derivación a ficha + render XLSX

**Esfuerzo**: 1-2 sesiones (~8-10 h).

**Entrega**: nuevo módulo `core/viabilidad/derivacion.py`. Lee
`_cuestionario_respuestas.json` + `informe_viabilidad.yaml`. Por cada hito,
aplica la `regla_derivacion` declarada y produce un dict de scores propuestos.

**Render del XLSX paralelo**:
`02_Analisis/Informe viabilidad LLM - <case_id>.xlsx`. Mismo layout que el
editado por la Administración, con dos columnas adicionales por hito:
«Confianza» y «Cita». Hoja oculta `_llm_meta` con modelo usado, fecha de
generación, hash del cuestionario YAML y coste estimado.

**Importante**: este XLSX **nunca** sobrescribe el
`Informe viabilidad - <case_id>.xlsx` que edita la Administración. Coexisten.
La integración (copiar valores de uno al otro tras revisión humana) se hace
manualmente con copy/paste o, en fase futura, con un script
`merge_llm_review.py`.

### Fase 5 — UI Streamlit

**Esfuerzo**: 1 sesión (~6-8 h).

**Entrega**: botón «🤖 Pre-rellenar viabilidad con IA» en la página del
caso, dentro de la sección de análisis. Validaciones previas: caso pulled,
tipo en `INFORME_VIABILIDAD_TIPOS`, presupuesto de coste estimado mostrado
antes del click.

**Flujo UI**:

1. Spinner por fase (intake → clasificación → extracción → derivación). Cada
   fase emite eventos al `intake_log` del caso para auditoría.
2. Al terminar, muestra resumen: nº de preguntas respondidas con alta
   confianza (≥0,8), pendientes (`null`/baja confianza), y coste API real.
3. Botón «Abrir Informe LLM» que linka al `.xlsx` generado vía `computer://`.
4. Disclaimer fijo: «Output sin validación humana. Revisa cada celda antes
   de usar como base para reclamación.»

Tooltip en todo campo (regla `feedback_ui_tooltips.md`).

### Fase 6 — Validación gold-standard (continua)

**Esfuerzo**: continuo, sin sesión dedicada.

**Entrega**: reutilizar el fixture pattern de SaRS1 H5. Por cada nuevo caso
que pase por el pipeline, snapshot del output LLM en
`tests/fixtures/viabilidad/<case_id>/` (local-only, en `.gitignore` como
SaRS1). Permite detectar regresiones cuando se actualicen prompts o modelos.

Las correcciones humanas que la Administración haga sobre el
`Informe viabilidad LLM - <case_id>.xlsx` se capturan en un
`_corrections.json` que alimenta el bucle de mejora de prompts. Esto es el
equivalente al `_revision_anon_SaRS1.md` pero para extracción jurídica.

---

## 5. Resumen de esfuerzo y secuencia

| Fase | Esfuerzo | Bloquea a | Dependencias externas |
|------|----------|-----------|------------------------|
| 0 | 1 sesión | 1, 3 | Decisión BAD_DEBT, fix bugs OCR y validate_case_id |
| 1 | 2 sesiones | 2, 3 | Fase 0 |
| 2 | 1 sesión | 3 | Fase 1 |
| 3 | 3-4 sesiones | 4, 6 | Fases 1+2 |
| 4 | 1-2 sesiones | 5 | Fase 3 |
| 5 | 1 sesión | uso real | Fase 4 |
| 6 | continua | — | uso real |

---

## 6. Riesgos críticos a vigilar

- **Calidad OCR del Drive E&V**. Casos como SaRS1 destaparon páginas con OCR
  no recuperable. Las respuestas LLM sobre esas páginas serán basura — el
  extractor debe propagar la señal de calidad OCR al `confianza` final.
- **Variabilidad de nomenclatura de documentos**. E&V no tiene convención de
  nombres uniforme. El clasificador de Fase 2 es el punto frágil — necesita
  tarado real sobre múltiples equipos (Madrid, Barcelona, Marbella, Sevilla)
  para no sesgar a uno solo.
- **Coste creciente con casos grandes**. Casos con muchos emails
  (`03_Email/`) pueden disparar el coste. Mitigación: en Fase 2 marcar emails
  como bloque consolidado (chunk de 30k tokens máx) en lugar de uno por
  mensaje.
- **Anonimización del case_id en frontmatter**. La entrada §23 de
  `MEJORAS_FUTURAS` (descubierta en SaRS1 H5b) sigue sin resolverse — el
  motor expone el case_id literal con dirección PII en el frontmatter de los
  `.md` anonimizados. Para enviar al frontier hay que neutralizarlo aquí
  también.

---

## 7. Referencias

- Memoria `project_plantillas_viabilidad.md` (estado de las plantillas YAML
  + horizonte 3 estimado en 3-4 semanas).
- Memoria `project_sars1_anon_pipeline.md` (plan H1-H7 que validó la cadena
  OCR → split → anon → frontier sobre caso real).
- `data/_plantillas/cuestionario_viabilidad.yaml` (82 preguntas con
  `respalda: [hito_id]` y `fuente_probable`).
- `data/_plantillas/informe_viabilidad.yaml` (14 hitos con
  `regla_derivacion` canónica).
- `docs/MEJORAS_FUTURAS.md` §11, §12, §22, §23 (bugs y refactors que tocan
  este pipeline).
- `core/anon/api.py::anonimizar_caso` (motor de anonimización reutilizable).
- `08_Para frontier/` (drop zone canónica del LLM externo, contrato definido
  en SaRS1 H6).
