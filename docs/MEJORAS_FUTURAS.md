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

---

## 13. FN — Regex de dirección postal española en `aplicar_regex`

**Detectado.** 2026-05-12 durante el hilo H5 del plan SaRS1 (tabla forense,
filas 42 y 49).

**Síntoma.** El motor no etiqueta domicilios postales españoles. Sobre el
caso SaRS1 quedó sin anonimizar el domicilio del actor "Calle Castelar
37-39, Santander" en sus 12 variantes (`Calle Castelar núm. 37-39`,
`CALLE CASTELAR NÚMERO 37-39`, `Castelar n*37-39 bajo`, `Castelar N* 37-39`,
`CAST3ELAR NÚMERO 37-39` — con `3` por `E` por OCR, etc.). Resultado: FN
bloqueante para confidencialidad.

**Causa raíz.** `core/anon/anonimizar.py::aplicar_regex` no incluye un
patrón `DIRECCION`. Presidio no detecta direcciones postales españolas
sin un `PatternRecognizer` dedicado.

**Solución técnica.** Añadir `PatternRecognizer` para `DIRECCION` con
patrón tolerante: `(?:Avd?\.|Calle|C/|Plaza|Pza\.|Pso\.|Pje\.|Travesía|Tr\.|Avenida)\s+[A-ZÁÉÍÓÚÑa-záéíóúñ\d\s\.\-’'`]+?\s+(?:n[uú]m\.?|n[º°*9o]?)?\s*\d+(?:\s*[\-–_/]\s*\d+)?(?:\s+bajo|BAJO)?`. Tolerancia a typos OCR (`CAST3ELAR` por `CASTELAR`) mediante normalización previa o regex permisivo en consonantes.

**Test smoke.** Añadir a `tests/test_anon_basic.py` casos con
direcciones reales españolas, incluyendo variantes mayúsculas/minúsculas
y con/sin separador en el número (37-39, 37/39, 37 - 39).

**Coste estimado.** 30 minutos (patrón + integración + 3-4 tests).

**Prioridad.** **Alta** — la dirección postal es PII recurrente en todo
expediente civil/inmobiliario. La omisión actual es el bloqueante más
grave detectado en H5.

---

## 14. FN — Variantes OCR de clientes propios E&V deben pre-cargarse al mapa

**Detectado.** 2026-05-12 durante el hilo H5 del plan SaRS1 (tabla forense,
filas 43-44; nota N4 de H4).

**Síntoma.** La denominación del cliente "Engel & Völkers" aparece en el
OCR transcrita con variantes degradadas — `Engel £ Vólkers`, `Engel 4
Volkers`, `ENGEL 8 VÓLKERS`, `ENGEL 8 VÓLKERS SPAIN, S.L.` — que el
motor captura en el `mapa_directo` de forma inconsistente o no captura
en absoluto, dejando "ENGEL 8 VÓLKERS SPAIN, S.L." sin anonimizar en
cabeceras de cédula y decreto.

**Causa raíz.** El motor descubre el cliente dinámicamente vía Presidio +
regex, sin información a priori del `_caso.md` (campo `meta.cliente`).
Las variantes OCR no se consolidan automáticamente.

**Solución técnica.** En `anonimizar_caso`, leer del `_caso.md` los
campos `meta.cliente` + `meta.cliente_propio_clave` y pre-cargar al
`MapaEntidades.protegidos` un conjunto de variantes conocidas del
cliente. Para `ENGEL_VOLKERS_SPAIN`: pre-cargar `["Engel & Völkers",
"Engel & Volkers", "Engel Völkers", "Engel Volkers", "ENGEL & VÖLKERS",
"ENGEL Y VÖLKERS", "ENGEL 8 VÖLKERS", "Engel £ Vólkers", "Engel 4
Volkers"]` todas mapeadas a la misma etiqueta canónica antes de la
pasada del motor.

**Coste estimado.** ~30 líneas en `core/anon/api.py` + tabla de variantes
por cliente en `core/config.py::CLIENTES_PROPIOS_EV` + 2 tests.

**Prioridad.** **Alta** — afecta a todos los casos del cliente E&V (~80%
del flujo). Sin esto, la denominación del cliente filtra a Claude
frontier en casi todos los expedientes.

---

## 15. FN — Regex de EMAIL debe tolerar `@` corrompido por OCR

**Detectado.** 2026-05-12 durante el hilo H5 del plan SaRS1 (tabla forense,
filas 46 y 49).

**Síntoma.** El OCR español del despacho transcribe el carácter `@` como
`Q` o `O` por similitud visual. Sobre SaRS1 quedaron sin anonimizar
`cubriaQdelriomiera.es` (email abogado actor) y
`pablo gutierrezOengelvoelkers.com` (email empleado E&V). El regex de
email actual exige `@` literal y no captura estas variantes.

**Causa raíz.** El regex `_EMAIL` (probablemente algo como `[\w.+-]+@[\w-]+\.[\w.-]+`) no admite alternativa OCR.

**Solución técnica.** Extender el patrón a `[\w.+-]+[@QO][\w-]+\.[\w.-]+`
**solo cuando** la cadena tiene cola plausible de dominio (`.es`,
`.com`, `.org`, `.net` etc.) para evitar FP con palabras comunes que
contengan `O` o `Q` entre letras.

**Test smoke.** Casos con `@` real + casos con `Q` y `O` en posición.

**Coste estimado.** 20 minutos.

**Prioridad.** **Alta** — los emails son PII recurrente y la
degradación OCR es generalizada en documentos escaneados con tóner
desgastado.

---

## 16. FN — Coherencia intra-caso: variantes parciales del mismo nombre

**Detectado.** 2026-05-12 durante el hilo H5 del plan SaRS1 (tabla forense,
filas 45, 50, 51).

**Síntoma.** Cuando el motor mapea "DOÑA ADELAIDA PEÑIL GÓMEZ" como
`[NOMBRE_11]` en un documento, las variantes "Adelaida Peñil" (sin
apellido completo), "Sra. Peñil", "Adelaida" en el mismo o en otros
documentos del caso quedan sin etiquetar. Igual con "Mercedes" (de
"MERCEDES CACHO PITA") y "Eduardo Saiz" (de "EDUARDO SAIZ LAVID").

**Causa raíz.** El motor no hace post-procesado de coherencia
intra-caso: no busca substrings/variantes parciales de las entidades
ya descubiertas.

**Solución técnica.** Tras la primera pasada del motor sobre los
documentos del caso, segunda pasada que para cada entidad `nombre =
v1 v2 v3` del `MapaEntidades` busque y etiquete coincidencias parciales
`v1 v2`, `v2 v3`, `v1`, `v3` (token-aware, no substring crudo) en todos
los documentos del caso. Configurable por umbral de tokens mínimos.

**Coste estimado.** ~80 líneas en un módulo nuevo
`core/anon/post_proceso_coherencia.py` + 4-5 tests.

**Prioridad.** Media — afecta a casos con nombres recurrentes en cuerpo
narrativo (más frecuente en documentos largos como demandas con
referencias múltiples a las partes).

---

## 17. FP — Detector de mayúsculas captura cabeceras estructurales como nombres

**Detectado.** 2026-05-12 durante el hilo H5 del plan SaRS1 (tabla forense,
filas 3-39; nota N2 de H4 era el bloque masivo).

**Síntoma.** Cualquier secuencia de 2+ palabras en MAYÚSCULAS dentro de
documentos procesales es candidata a falso positivo. En SaRS1 el motor
etiquetó como nombres ~75 cabeceras estructurales: "ORDEN DEL DÍA",
"COMPETENCIA TERRITORIAL", "LEGITIMACIÓN ACTIVA", "RESPONSABILIDAD
EXTRACONTRACTUAL", "XII. COSTAS", "PRUEBA DE ENTREGA", "ACTIVIDADES
MOLESTAS", "PREVENCIONES LEGALES", "ORDENA EMPLAZAR", "VEINTE DÍAS
HÁBILES", "PLAZO EN QUE DEBE COMPARECER", etc. Resultado: deterioro
masivo de la legibilidad del borrador que produzca Claude frontier.

**Causa raíz.** El detector NER de Presidio + el filtro de mayúsculas
en `anonimizar_por_contexto` (o equivalente) considera nombre propio
cualquier secuencia de mayúsculas con cierta longitud, sin lista negra
estructural.

**Solución técnica.** Lista negra ampliable de prefijos/sufijos
estructurales en `core/anon/anonimizar.py` (ampliar `PALABRAS_EXCLUIDAS`
o crear `CABECERAS_PROCESALES_EXCLUIDAS`). Incluir como mínimo: "HECHOS",
"FUNDAMENTOS DE DERECHO", "ANTECEDENTES DE HECHO", "PARTE DISPOSITIVA",
"ACUERDO", "SUPLICO", "OTROSÍ", "ORDEN DEL DÍA", "PREVENCIONES LEGALES",
"PRIMERO.-", "SEGUNDO.-", ... (hasta DUODÉCIMO o DECIMOQUINTO),
"COMPETENCIA TERRITORIAL", "COMPETENCIA OBJETIVA", "LEGITIMACIÓN
ACTIVA", "LEGITIMACIÓN PASIVA", "RESPONSABILIDAD EXTRACONTRACTUAL",
"COSTAS", "CUANTÍA", "PROCEDIMIENTO ADECUADO". Adicional: regla que
descarte como nombre cualquier cadena que contenga preposiciones de
conexión gramatical ("DE", "DEL", "A", "AL", "EN", "POR", "PARA",
"QUE", "Y", "O") en posición no-final, salvo nombres con
preposiciones reales ("DE LA CRUZ", "DEL VALLE").

**Coste estimado.** 1-2 h (lista + heurística + 8-10 tests con casos
reales).

**Prioridad.** **Alta** — la legibilidad del borrador para Claude
frontier es función directa de este filtro. Sin esto, el output del
motor es semánticamente confuso.

---

## 18. FP — Toponímicos de calles/avenidas confundidos con personas

**Detectado.** 2026-05-12 durante el hilo H5 del plan SaRS1 (tabla forense,
fila 1).

**Síntoma.** El motor etiqueta el nombre de la vía pública en la
cabecera del tribunal — "Pedro San Martín" (avenida pública en
Santander donde está el órgano judicial) — como `[NOMBRE]`. Análogamente
ocurriría con "Calle José Ortega y Gasset", "Plaza Antonio Machado",
etc.

**Causa raíz.** Cuando el detector NER ve un patrón "Nombre Apellido"
plausible no comprueba si está precedido de marcador de vía
(`Avd./Calle/Plaza`).

**Solución técnica.** Pre-procesado: localizar todas las cadenas
matcheando `(?:Avd?\.|Calle|C/|Plaza|Pza\.|Pso\.|Pje\.|Travesía|Tr\.|Avenida)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s\.]+?)(?=\s+(?:n[uú]m\.?|n[º°*9o]?|s\/n|S\/N|\d|,|$))` y marcar las capturas como `protegidos`
antes de pasar al motor NER. Sinergias con mejora 13 (regex DIRECCION).

**Coste estimado.** 30 min.

**Prioridad.** Media — afecta sobre todo a cabeceras de tribunales, no
al cuerpo narrativo.

---

## 19. FP — Regex de CUENTA/IBAN captura el NIG por longitud numérica

**Detectado.** 2026-05-12 durante el hilo H5 del plan SaRS1 (tabla forense,
fila 2; nota N6 de H4).

**Síntoma.** El NIG (Número de Identificación General del procedimiento
judicial) es una cadena de 19 dígitos compactos (en SaRS1:
`3907542120260004548`). El regex de cuenta/IBAN del motor lo captura
como `[CUENTA]` por matching de longitud, cuando en realidad no es PII
bancaria sino un identificador procesal público.

**Causa raíz.** El regex `_CUENTA`/`_IBAN` no distingue por contexto
previo.

**Solución técnica.** Añadir lookbehind en el regex: descartar la
captura si los 5 caracteres anteriores contienen `NIG:` o `nig:`
(case-insensitive). Igual aplicaría a `CCC:`, `código:`, etc.

**Coste estimado.** 15 min.

**Prioridad.** Media — afecta a todos los expedientes judiciales con
NIG visible en cabecera (la mayoría).

---

## 20. MAP — Consolidación tolerante a tildes/diéresis y a variantes parciales

**Detectado.** 2026-05-12 durante el hilo H5 del plan SaRS1 (tabla forense,
filas 52-59; nota N1 de H4).

**Síntoma.** Tras la pasada del motor sobre SaRS1, el mismo abogado
"Juan Cubría Falla" recibió 5 etiquetas distintas (`[NOMBRE_30]`,
`[NOMBRE_43]`, `[NOMBRE_51]`, `[NOMBRE_133]`, `[NOMBRE_139]`) por
variantes con/sin tilde + OCR roto. El mismo despacho "José del Río
Miera" recibió 3 etiquetas (`[NOMBRE_52]`, `[NOMBRE_57]`, `[NOMBRE_60]`).
La propietaria "TERAN FERNANDEZ" recibió 2 (`[NOMBRE_111]`,
`[NOMBRE_130]` — variante recortada). El cliente E&V quedó con 1
etiqueta canónica pero múltiples variantes en `mapa_directo` apuntando
a ella (correcto), si bien la transcripción canónica "Engel £ Vólkers"
es subóptima — debería ser "Engel & Völkers".

**Causa raíz.** El `MapaEntidades` no normaliza por diacríticos al
buscar entidades existentes; cada variante OCR se trata como entidad
nueva.

**Solución técnica.** Antes de asignar etiqueta nueva, normalizar el
candidato con `unicodedata.normalize('NFKD').encode('ascii', 'ignore')`
+ `upper()` y comparar contra todas las etiquetas existentes
normalizadas igual. Si match → reutilizar etiqueta existente y añadir
al `mapa_directo`. Adicional: post-procesado de detección de variantes
parciales tras la pasada del motor (sinergia con mejora 16).

**Coste estimado.** ~50 líneas en `core/anon/mapa_caso.py` + 5 tests de
deduplicación.

**Prioridad.** Media — afecta la legibilidad del borrador (Claude
frontier ve múltiples etiquetas para la misma persona) pero no la
confidencialidad.

---

## 21. OCR — Política automática de re-OCR ante degradación detectada

**Detectado.** 2026-05-12 durante el hilo H5 del plan SaRS1 (tabla forense,
filas 60-61; nota N5 de H4).

**Síntoma.** En SaRS1, las páginas 17-30 del PDF1 (página de firma
digital del abogado actor con tipografía atípica) y las páginas 1-20
del PDF2 (escaneados con tóner desgastado o densidad insuficiente)
producen OCR completamente degradado: secuencias de 2-4 caracteres
aleatorios sin sentido (`Aenar`, `iOJue E Uey`, `III TOTON JN MIYA OZ`,
`jieape X`, etc.). El motor captura ~50 de estas secuencias como
falsos nombres, contaminando el mapa y desperdiciando ciclos de NER.
Adicionalmente, las páginas con contenido sustantivo perdido (acuse
de recibo Correos, comprobantes MASC) quedan ilegibles para Claude
frontier.

**Causa raíz.** El wrapper `core/anon/ocr.py` invoca `ocrmypdf` con
parámetros conservadores (`-l spa --skip-text --deskew --optimize 1
--rotate-pages`). No reintenta páginas con calidad baja con parámetros
agresivos.

**Solución técnica.** Tras la pasada inicial de OCR, métrica por
página de "calidad probable" basada en: (a) longitud media de palabra
(<3 chars → degradado), (b) ratio de palabras de diccionario español
(<30% → degradado), (c) ratio de caracteres no-ASCII (>5% → degradado),
(d) ratio de líneas con >50% de tokens cortos sueltos. Para páginas
marcadas como degradadas, segunda pasada con `--oversample 600
--image-dpi 300 --redo-ocr --tesseract-pagesegmode 6`. Log de
páginas que siguen degradadas tras el reintento como "OCR irrecuperable
— revisión humana requerida".

**Coste estimado.** 2-3 h (métrica + segunda pasada + tests de
integración con PDFs sintéticos degradados).

**Prioridad.** **Alta** — el OCR es la primera línea del pipeline. Una
degradación silente arrastra ruido a todas las fases siguientes y
deteriora la calidad del borrador final.

---

## 22. Refactor — `anonimizar_caso` debería admitir listado explícito de documentos

**Detectado.** 2026-05-12 durante el hilo H4 del plan SaRS1 (Opción B
del plan; documentado en `07_AI cowork/_revision_anon_SaRS1.md` sección
H4).

**Síntoma.** `core/anon/api.py::_listar_documentos` (L318-334) descarta
cualquier path donde alguna parte del path relativo empiece por `_`. Esto
ignora `_ocr/` y `_split/`, lo cual es correcto para la mayoría de
flujos pero **impide** procesar las piezas separadas manualmente (output
de `separar_pdf_pipeline` o de troceo `pypdf` ad-hoc). En SaRS1 esto
obligó a escribir un script ad-hoc en H4 que replica `anonimizar_caso`
con listado explícito.

**Causa raíz.** No hay parámetro opcional para sobrescribir el listado
canónico.

**Solución técnica.** Añadir parámetro `documentos: list[Path] | None =
None` a `anonimizar_caso`. Si `None`, comportamiento actual (vía
`_listar_documentos`). Si lista explícita, usar esa lista. Validar que
cada path está bajo `caso_path(case_id)` por seguridad.

**Coste estimado.** ~20 líneas en `api.py` + 3 tests.

**Prioridad.** Media — `anonimizar_caso` es la fachada estándar y se
usaría en cualquier H4 futuro con piezas de `_split/`. Sin esto, cada
caso con split manual requiere script ad-hoc.

---

## 23. Frontmatter del motor expone `case_id` literal con PII

**Detectado.** 2026-05-12 (sesión 17) durante el sanity check previo a
exposición de `08_Para frontier/` en SaRS1 (documentado en
`07_AI cowork/_revision_anon_SaRS1.md` sección H5b).

**Síntoma.** Los `.md` anonimizados que `core/anon/api.anonimizar_caso`
escribe en `06_Anonimizado/` incluyen frontmatter YAML con varios campos
que el motor llena directamente desde `CaseMeta`:

```yaml
---
case_id: SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros
tipo: documento_anonimizado
fase: 06_Anonimizado
slug: 01_cedula_emplazamiento_01
fecha: '2026-05-12T12:27:58'
tipo_procedimiento: Juicio Ordinario
origen: 01_CEDULA_EMPLAZAMIENTO_01.pdf
origen_sha256: 8059c42206a9550889d1635e826da879ef0bfa4c2e49fecafca9543b260c6b1a
n_entidades: 13
alertas: []
---
```

El campo **`case_id`** lleva incrustada la dirección literal del caso
(parte de la convención `<ciudad><equipo><tipo> - <dirección>
(<referencia>) - <categoría>`). Cuando los `.md` se entregan a un LLM
externo (Claude frontier en H6 del flujo SaRS1), el frontmatter va con
ellos y el modelo lee la dirección PII como contexto, rompiendo el
pilar arquitectónico del proyecto.

**Workaround aplicado en H5b.** Al copiar los `.md` de `06_Anonimizado/`
a `08_Para frontier/`, sustituir el frontmatter completo por uno
neutralizado (`case_id: <anonimizado>` + slug + tipo procedimiento). Los
originales de `06_Anonimizado/` se conservan intactos para uso del
motor de deanonimización en H7.

**Causa raíz.** `core/anon/api.py::anonimizar_documento` (sección que
construye el frontmatter, aprox. L380-420) usa `case_meta.case_id` tal
cual.

**Solución técnica propuesta.** Dos opciones complementarias:

1. **Anonimización del case_id en el frontmatter del motor.** Antes de
   escribir el `.md`, aplicar el motor de anonimización al propio
   `case_id` (la dirección literal se sustituye por una etiqueta del
   mismo mapa, p.ej. `[DIRECCION]`). Recompone como
   `case_id: <ciudad><equipo><tipo> - [DIRECCION] (<ref>) - <categoría>`.
   Conserva trazabilidad estructural sin exposición de PII.
2. **Modo "para frontier" en `anonimizar_caso`.** Flag opcional
   `frontmatter_neutralizado: bool = False`. Si `True`, escribe un
   frontmatter mínimo sin `case_id`/`origen`/`sha256` — solo `slug` y
   `tipo_procedimiento`. Útil para outputs dedicados a LLM externos.

La opción (1) es la correcta para el flujo estándar (sin tocar el flujo
H6 después). La opción (2) puede convivir como modo explícito.

**Coste estimado.** Opción (1): ~15 líneas en `api.py` + 2 tests
(verificar que el case_id post-anonimización sigue siendo válido para
`core.anon.deanonimizar._localizar_mapa`). Opción (2): ~25 líneas + 3
tests.

**Prioridad.** Alta — bloqueante para automatizar el flujo H6 en casos
futuros. Sin esta mejora, cada caso que entregue `.md` a LLM externo
requiere mitigación manual (script tipo `_h5b` que stripea frontmatter).
