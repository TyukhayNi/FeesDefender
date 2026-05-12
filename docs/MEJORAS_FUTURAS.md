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

---

## 11. Bug latente: wrapper `ocr_pdf` invoca `ocrmypdf.ocr` con firma incorrecta

**Detectado.** 2026-05-12 durante la apertura del hilo H1 del plan SaRS1
(primera ejecución real del wrapper en producción).

**Síntoma.** `core/anon/ocr.py` L104 invoca `ocrmypdf.ocr(**args)` pasando
`input_file` y `output_file` como **kwargs**. La API actual de ocrmypdf
(probado con la versión instalada en el entorno del despacho a
2026-05-12) exige el input como **primer argumento posicional**
(`input_file_or_options`). El call site lanza:

```
TypeError: ocr() missing 1 required positional argument: 'input_file_or_options'
```

Capturado por el wrapper como `OCRError("Fallo no recuperable de
ocrmypdf: ...")`.

**Causa raíz.** El wrapper nunca tuvo tests de integración (solo el
único call site interno, que nunca se ejercitó en CI porque ningún
fixture de tests contenía PDFs sin capa de texto). Bug latente desde la
absorción del Anonimizador (2026-05-07).

**Workaround usado para H1.** Invocar `ocrmypdf` por línea de comandos
directamente (`python -m ocrmypdf -l spa --skip-text --deskew --optimize 1
--rotate-pages --invalidate-digital-signatures INPUT OUTPUT`), que es
exactamente como el Anonimizador original lo hacía (ver docstring de
`core/anon/ocr.py` líneas 3-8).

**Solución técnica.** Cambio quirúrgico en `core/anon/ocr.py` L88-104:

```python
# Antes:
args: dict = {"input_file": str(ruta_entrada), "output_file": str(ruta_salida), ...}
result = ocrmypdf.ocr(**args)

# Después:
args: dict = {"language": idiomas, ...}  # quitar input_file y output_file
result = ocrmypdf.ocr(str(ruta_entrada), str(ruta_salida), **args)
```

**Test smoke imprescindible.** Añadir `tests/test_anon_ocr.py` con al
menos un test que:

1. Skip si `ocrmypdf` no instalado o `tesseract` no en PATH.
2. Generar PDF mínimo sin capa de texto (PIL + reportlab) en un
   `tmp_path`.
3. Llamar `ocr_pdf(...)` con `idiomas="spa"`.
4. Asertar que el output existe y `pypdf.PdfReader(output).pages[0].extract_text().strip()` no es vacío.

**Coste estimado.** 20 minutos (fix + test + verificación end-to-end).

**Prioridad.** Alta — el módulo no es usable sin este fix. Cualquier caso
que llegue al despacho en papel (volumen estimado ~30% del flujo
extrajudicial E&V) cae en este path.

---

## 12. Bug latente: `validate_case_id` no admite categoría OTROS

**Detectado.** 2026-05-12 durante el hilo H4 del plan SaRS1 (primera
ejecución real de `anonimizar_caso` / `anonimizar_documento` sobre un
caso de categoría OTROS).

**Síntoma.** `core/utils.py::validate_case_id` (regex `_CASE_ID_NEW` en
L41-43) exige `\(W-[A-Z0-9]+\)` en el grupo de referencia del case_id.
Para casos de categoría OTROS la convención del despacho es
`(SIN REFERENCIA)` (no hay referencia W-XXXXXX porque el caso no
proviene de captación inmobiliaria). Resultado: cualquier case_id como
`SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros` revienta
con `ValueError: Formato de case_id no reconocido`.

**Causa raíz.** La regex no se actualizó cuando la categoría OTROS se
añadió a `core/config.py::TIPOS_CASO_OTROS` (s9, 2026-05-11). Bug latente
desde entonces porque ningún caso OTROS había llegado al motor de
anonimización aún.

**Workaround usado para H4.** Monkey-patch local en el script ad-hoc del
hilo (`%TEMP%\h4_sars1_anon.py`): sustituir `core.anon.api.validate_case_id`
por una identidad que solo asegura no-vacío. Sin tocar el código del
proyecto.

**Solución técnica.** Cambio quirúrgico en `core/utils.py::_CASE_ID_NEW`:

```python
# Antes:
_CASE_ID_NEW = re.compile(
    r"^[A-Z][a-zA-Z][A-Z]{2}\d+\s+-\s+.+\(W-[A-Z0-9]+\)\s+-\s+.+$"
)

# Después:
_CASE_ID_NEW = re.compile(
    r"^[A-Z][a-zA-Z][A-Z]{2}\d+\s+-\s+.+"
    r"\((?:W-[A-Z0-9]+|SIN\s+REFERENCIA)\)"
    r"\s+-\s+.+$"
)
```

**Test smoke imprescindible.** Añadir a `tests/test_utils.py` (o crear
si no existe) un caso con case_id de categoría OTROS, verificando que
`validate_case_id` lo acepta.

**Coste estimado.** 10 minutos (fix + test + verificación suite).

**Prioridad.** Media — afecta a todos los casos OTROS que pasen por el
motor de anonimización. Hay workaround claro vía script ad-hoc, pero
romper el comando estándar `python -m scripts.anonimizar_caso` para una
categoría legítima del proyecto es regresión arquitectónica. Tratar en
hilo dedicado, no en H4.
