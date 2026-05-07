# Mejoras futuras del módulo `core/anon/`

Bugs latentes y mejoras detectadas durante la absorción del Anonimizador
de Expedientes Seguros (2026-05-07). Ninguna es bloqueante para
producción; todas se identificaron y dejaron documentadas durante la
integración para no introducir cambios al margen del refactor.

Orden por prioridad operativa (no técnica).

---

## 1. OCR automático en `anonimizar_caso`

**Estado actual.** Si un PDF de `00_Input/` carece de capa de texto,
`anonimizar_documento` devuelve `ok=False` con `alertas=["OCR_REQUERIDO"]`
y el documento queda pendiente. El usuario debe ejecutar `core.anon.ocr_pdf`
manualmente y reintentar.

**Mejora propuesta.** Añadir flag `auto_ocr: bool = False` a
`anonimizar_caso`. Si está activo y se detecta `PDFSinTextoError`, aplicar
`ocr_pdf` sobre una copia temporal y reintentar la extracción. Si OCR
falla también, marcar el documento como error real.

**Justificación de no aplicarlo ahora.** Aplicar OCR siempre es lento
(30s+/PDF de 50 págs) y un único PDF escaneado pesado puede congelar la
UI 10 minutos sin progreso. Mejor decidirlo explícitamente cuando
sepamos qué % de documentos del CRM lo necesitan.

**Coste estimado.** ~30 líneas en `api.py` + 2 tests.

---

## 2. Separación previa con `separar_pdf_pipeline`

**Estado actual.** Cada PDF de `00_Input/` se procesa como un único
documento. La función `separar_pdf_pipeline` está implementada y testada
pero NO se invoca desde la fachada.

**Mejora propuesta.** Detectar PDFs con marcadores de múltiples
documentos (>5 páginas + presencia de `DOC N`, `DEMANDA + DOC` en sus
primeras líneas) y separarlos automáticamente antes de anonimizar.

**Justificación de no aplicarlo ahora.** La mayoría de PDFs del CRM ya
vienen como pieza individual. La separación es valiosa principalmente
para expedientes que llega desde el juzgado en un único PDF fundido.
Si esto se vuelve frecuente, es trivial enchufar `separar_pdf_pipeline`
en `anonimizar_caso`.

---

## 3. Bug latente: span de sustitución en `anonimizar_por_contexto`

**Síntoma.** En docs comprimidos (cédula con partes procesales en líneas
contiguas sin puntuación), el regex contextual `_NOMBRE` con
`re.IGNORECASE` puede capturar hasta 4 palabras incluyendo la primera
palabra de la siguiente parte:

```
Demandante: DON IVAN PETROV SOKOLOV
Demandado: DOÑA MARIA GARCIA LOPEZ
```

El regex captura `IVAN PETROV SOKOLOV Demandado` (4 palabras). Tras
`limpiar_nombre`, el mapa guarda solo `IVAN PETROV SOKOLOV`, pero la
sustitución usa el span original con `m.start(1)` y `m.end(1)`. Resultado:
"Demandado" desaparece del texto.

**En docs reales no se manifiesta.** Las cédulas suelen tener puntuación
final entre partes (`DON IVAN PETROV.` con punto). Solo en formato
comprimido sin separadores se materializa.

**Solución técnica.** En `anonimizar.py::anonimizar_por_contexto` (L.1062-1064
del archivo actual), recalcular `m.end(1)` tras `limpiar_nombre` cortando
la captura por la última palabra válida del nombre limpio. Cambio
mediano (~15 líneas).

**Verificable** con un test que use input comprimido sin puntuación
entre partes. Hoy se evita en `tests/test_anon_basic.py` añadiendo
puntos al test (formato realista de cédulas).

---

## 4. Asimetría masculino/femenino en `PALABRAS_EXCLUIDAS`

**Síntoma.** El conjunto incluye `DEMANDANTE` y `DEMANDADA` (femenino)
pero NO `DEMANDADO` (masculino). Idem `EJECUTANTE`/`EJECUTADA` sin
`EJECUTADO`. En docs reales, `limpiar_nombre` no elimina la palabra
masculina del final del nombre capturado, lo que **agrava** el bug 3
cuando la captura llega hasta la palabra siguiente.

**Solución.** Añadir las variantes masculinas:
`DEMANDADO`, `EJECUTADO`, `QUERELLADO`, `DENUNCIADO`, `INVESTIGADO`,
`ACUSADO`, `RECURRIDO`, `APELADO`.

**Coste.** 1 línea en `anonimizar.py` (la lista existe en L.198-265 del
archivo actual). Mejor combinarlo con el fix del bug 3 para una
verificación end-to-end limpia.

---

## 5. Singleton NLP — done, pero cache invalidation pendiente

**Estado.** Implementado en `core/anon/nlp_engine.py` y aplicado en
`anonimizar_con_presidio`. Tras Fase 4: una sola carga de modelos por
proceso Streamlit / pytest.

**Mejora pendiente.** No hay forma de invalidar el cache si los modelos
spaCy se actualizan en disco. Para reload tras `python -m spacy download`
de una versión nueva, hace falta reiniciar Streamlit. Aceptable.

---

## 6. Detección automática de tipo de procedimiento desde sudespacho.net

**Estado.** El usuario debe pasar `tipo_proc` (default "Juicio Ordinario").
La función `detectar_tipo_procedimiento` en `anonimizar.py` ya existe
pero solo busca en el texto extraído del PDF.

**Mejora.** Cuando un caso tenga registro CRM (campo
`sudespacho_expedientes` en `_caso.md`), leer de allí el tipo
procedimiento real y usarlo automáticamente. La integración con
sudespacho ya está madura.

**Coste.** ~10 líneas en `api.py::anonimizar_caso`.

---

## 7. UI para edición manual del mapa por caso

**Estado.** El `_mapa_caso.json` se gestiona programáticamente. Si el
usuario detecta una mala anonimización (e.g. un nombre del despacho
real anonimizado por error), no hay forma de corregirlo desde la UI —
hay que editar el JSON a mano.

**Mejora.** Pestaña Streamlit "Anonimización" con vista del mapa,
botones para forzar / desproteger entidades, y reproceso parcial.

**Coste.** Estimado ~150 líneas Streamlit + 2 tests. Nice-to-have.

---

## 8. Modelo NER ruso (`ru_core_news_md`)

**Estado.** Los nombres en cirílico no se detectan por Presidio (la
configuración solo carga `es`, `ca`, `en`). En la práctica los documentos
rusos del despacho llegan transliterados a latín por requisito de la
administración española, así que no es crítico. Si en el futuro entran
escrituras notariales rusas originales, conviene añadir el modelo.

**Coste.** Añadir un entry al `configuration` en `nlp_engine.py` +
descargar `ru_core_news_md` (~50 MB) + actualizar `health_check.py`.

---

## 9. Custom recognizers de Presidio (DNI español, IBAN)

**Estado.** El sistema usa los reconocedores estándar de Presidio + una
fase regex local en `aplicar_regex` con patrones para DNI, NIE, NIF,
IBAN, teléfono español, email. Funciona bien.

**Mejora.** Migrar los regex locales a `PatternRecognizer` de Presidio
para tenerlos integrados con el motor NER (mejor scoring, menos
duplicación). Trabajo de medio día, baja prioridad.

---

## 10. `dudas_acumuladas.json` — política de uso

**Estado.** El fichero es valor del despacho — fragmentos de texto real
que ayudan a calibrar el detector. Vive en
`G:\...\Expedientes Seguros\Anonimizador\_herramientas\dudas_acumuladas.json`
en el proyecto origen.

**Decisión pendiente.** En FeesDefender la fachada **no** está usando
todavía el flujo interactivo (que es lo que alimenta el JSON). Cuando
añadamos UI de revisión manual (mejora 7), conviene también:

- Mover `dudas_acumuladas.json` a `data/dudas_acumuladas.json` (única
  instancia por despacho).
- Añadir `data/dudas_acumuladas.json` al `.gitignore` (contiene fragmentos
  de docs reales).
- Documentar en STATUS.md que se sube a Claude/ChatGPT cada N expedientes
  para análisis y mejora.
