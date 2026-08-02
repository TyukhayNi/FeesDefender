# Mejoras futuras — backlog técnico

Backlog técnico del proyecto. Originalmente limitado a `core/anon/`
(absorción del Anonimizador, 2026-05-07); ampliado a todo el repo desde
que las entradas #26-#29 cubrieron pipeline, intake y política de datos.

Orden por prioridad operativa (no técnica). Ninguna entrada es bloqueante
para producción salvo que se indique.

> **Relación con `PLAN.md`**: las entradas de este fichero son backlog
> (ideas, bugs latentes, mejoras diferidas). Cuando una entrada tiene
> disparador concreto (caso real, bug bloqueante o decisión de Nikolai),
> se **promueve** a `PLAN.md` como tarea accionable. Al promoverla:
> marcar aquí con `[PROMOVIDO → PLAN.md]` y crear entrada en `PLAN.md`
> referenciando el número original (`MEJORAS #NN`).

---

## 1. OCR automático en `anonimizar_caso`

**✅ RESUELTO 2026-05-27 (s26).** Implementado el flag `auto_ocr: bool = False`
en `anonimizar_documento` / `anonimizar_caso` + `--auto-ocr` en el CLI. Ante
`PDFSinTextoError`, aplica `ocr_pdf` sobre una copia temporal y reintenta la
extracción sin tocar el original. Test de integración en `tests/test_anon_ocr.py`.
Verificado sobre BaRS1 (de 14 PDFs `OCR_REQUERIDO` → 5, todos planos/catastro
sin texto real).

**Estado actual (histórico).** Si un PDF de `00_Input/` carece de capa de texto,
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

**✅ RESUELTO 2026-05-27 (s27).** Implementado `_offsets_nombre_limpio` en
`core/anon/anonimizar.py`: tras `limpiar_nombre`, el span de sustitución se
recalcula localizando el nombre limpio dentro de la captura original, en lugar
de usar `m.end(1)` (que borraba las palabras recortadas). Validado contra el
fixture gold SaRS1.

**Síntoma (histórico).** En docs comprimidos (cédula con partes procesales en líneas
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

**✅ RESUELTO 2026-05-27 (s27).** Añadidas las variantes masculinas
(`DEMANDADO`, `EJECUTADO`, `QUERELLADO`, `INVESTIGADO`, `ACUSADO`, `RECURRIDO`,
`APELADO`…) a `PALABRAS_EXCLUIDAS` en `core/anon/anonimizar.py` (≈L211-212).
Combinado con el fix de §3.

**Síntoma (histórico).** El conjunto incluye `DEMANDANTE` y `DEMANDADA` (femenino)
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

## 8. Modelo NER ruso (`ru_core_news_md`) + desactivación condicional del filtro anti-cirílico

**Estado.** Los nombres en cirílico no se detectan por Presidio (la
configuración solo carga `es`, `ca`, `en`). Adicionalmente,
`anonimizar.extraer_texto_pdf` descarta deliberadamente páginas cuyo
ratio de caracteres legibles < 65 % con el comentario *"descarta cirílico
u otros alfabetos no latinos"* (aprox. L.386-389). Resultado: un PDF con
cirílico nativo no solo pierde el etiquetado de nombres — pierde las
páginas enteras antes de que el motor las vea.

**Re-calibración 2026-05-21.** La hipótesis original *"los rusos llegan
transliterados, no es crítico"* fue revisada tras cruzar el handoff
externo de diseño de pipeline (memoria
`project_handoff_anon_20260520.md`) con el perfil real de cliente del
despacho (mayoritariamente particulares ruso-hablantes y ex-URSS). Es el
único agujero del pipeline actual que el flujo manual no puede tapar: un
documento cirílico se pierde en silencio. **Prioridad: alta.**

**Mejora propuesta.** Dos piezas complementarias:

1. **Flag `modo_cirilico: bool = False`** en `anonimizar_documento` /
   `anonimizar_caso`. Si `True`, desactiva el filtro de ratio en
   `extraer_texto_pdf` y carga adicionalmente NER ruso. Comportamiento
   por defecto **inalterado** (cumple `feedback_anon_logica_intacta`).
2. **Carga condicional del modelo ruso** en `nlp_engine.py`. Opciones:
   `ru_core_news_md` (~50 MB, spaCy) o DeepPavlov BERT-Russian (más
   pesado, mejor recall). Empezar por spaCy.

**Coste estimado.** ~25 líneas en `api.py` + ~15 en `nlp_engine.py` +
~10 en `extraer_texto_pdf` (sin tocar la lógica, solo gating del filtro
por flag) + descarga del modelo + 4-5 tests + actualización de
`health_check.py`. 2-3 días de trabajo real.

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

**✅ RESUELTO 2026-05-27 (s26).** Fix quirúrgico en `core/anon/ocr.py`: input/output
como argumentos posicionales y `language` como lista (`idiomas.split("+")`), no
la cadena `"spa+cat+rus"`. Smoke test en `tests/test_anon_ocr.py`. Verificado
end-to-end sobre PDF escaneado real de BaRS1 (865 caracteres extraídos).

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

**✅ RESUELTO 2026-05-27 (s27).** `_CASE_ID_NEW` en `core/utils.py` acepta ahora
`(SIN REFERENCIA)` además de `(W-XXXXXX)`. Test en `tests/test_utils.py`.

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

**✅ RESUELTO 2026-05-27 (s27).** Añadido el patrón `DIRECCION` a
`PATRONES_REGEX` en `core/anon/anonimizar.py` (≈L706-713): marcador de vía
(`calle/avda/plaza/…` con `\b`) + nombre (1-5 palabras, tolerante a typos OCR) +
número con rango opcional (`37-39`). Validado contra el fixture gold SaRS1.

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

**✅ RESUELTO 2026-05-27 (s27).** Tabla `VARIANTES_OCR_CLIENTE` en
`core/config.py` + `_derivar_variantes_cliente(case_id)` en `core/anon/api.py`
(L461): lee el cliente del `_caso.md` y pre-carga las variantes OCR conocidas a
la fase 0 del motor (`variantes_conocidas`), mapeándolas a la etiqueta canónica.

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

**✅ RESUELTO 2026-05-27 (s27).** Patrón `_PATRON_EMAIL_OCR` en
`core/anon/anonimizar.py` (≈L744), pasada **case-sensitive** dentro de
`aplicar_regex` (≈L1285): captura el `@` transcrito como una mayúscula suelta
(`cubriaQdelriomiera.es`) exigiendo TLD conocido, sin tragar URLs públicas en
minúscula. Validado contra el fixture gold SaRS1.

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

**✅ RESUELTO 2026-05-27 (s27).** En `aplicar_regex` (`core/anon/anonimizar.py`
≈L1274-1280), las capturas `CUENTA`/`IBAN` precedidas del rótulo `NIG` (en los 8
caracteres previos) ya no se anonimizan. Validado contra el fixture gold SaRS1.

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

**✅ RESUELTO 2026-06-07 (s31).** Adoptada la opción (1): `neutralizar_case_id`
en `core/utils.py` sustituye el segmento de dirección del case_id por
`[DIRECCION]` conservando prefijo/referencia/categoría (sigue siendo un case_id
válido para `validate_case_id`). `core/anon/api.py::_build_md_anonimizado` la
aplica al escribir el frontmatter, de modo que los `.md` de `06_Anonimizado/`
ya no llevan el domicilio literal. La deanonimización no consume el `case_id`
del frontmatter (localiza el mapa por ruta/`mapa_caso_path`), así que el flujo
H6 deja de requerir el parche manual tipo `_h5b`. Tests en `tests/test_utils.py`
(`TestNeutralizarCaseId`, 9 casos) + fixture gold SaRS1 regenerado (solo cambia
la línea `case_id:` de los 4 `.md`; el `_mapa_caso.json` no cambia).

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

---

## 24. Conversor multi-formato a Markdown (`core/anon/conversor.py`)

**Detectado.** 2026-05-21 al cruzar el handoff externo de diseño de
pipeline (memoria `project_handoff_anon_20260520.md`) con el estado
actual de `core/anon/api.py::EXTS_PROCESABLES = {".pdf", ".docx"}`.

**Síntoma.** La fachada actual ignora XLSX, PPTX, HTML, MSG, JPG, PNG,
HEIC y PDFs con layout complejo (escrituras notariales, sentencias con
columnas múltiples). Los formatos no soportados se quedan fuera del
pipeline o requieren conversión manual previa
(`core.anon.imagen_a_pdf.convertir` existe para imágenes pero no está
integrado en la fachada). En E&V especialmente: cuadros de comisiones
en XLSX, mails exportados en MSG, fotos de propiedades en JPG.

**Mejora propuesta.** Módulo nuevo `core/anon/conversor.py` como capa
previa a `extraer_texto`. Routing por extensión:

- **markitdown** (Microsoft, MIT): DOCX, XLSX, PPTX, HTML, MSG, JPG, PNG.
- **docling** (IBM, MIT): PDFs nativos con layout complejo (escrituras,
  sentencias, contratos jurídicos largos).
- **ocrmypdf** (ya integrado): preprocesador para PDFs escaneados antes
  de docling.
- **`core.anon.imagen_a_pdf.convertir`** (ya integrado): fallback para
  imágenes que markitdown no resuelva bien.

Devuelve `.md` intermedio que entra en el extractor actual sin tocarlo.
Cumple `feedback_anon_logica_intacta` (capa nueva, motor intacto).

**Criterio de disparo.** Implementar cuando aparezca el primer caso
real con prueba en formato no soportado y la conversión manual previa
sea costosa. No por completitud de diseño.

**Coste estimado.** 3-5 días: módulo + routing + tests + integración en
`anonimizar_documento` + actualización de `EXTS_PROCESABLES`.

**Prioridad.** Media — diferido hasta caso real disparador.

---

## 25. Marcado de no-textuales en el `.md` anonimizado

**Detectado.** 2026-05-21 al cruzar el handoff externo de diseño de
pipeline con el comportamiento actual de `extraer_texto_pdf` y
`texto_a_markdown` en SaRS1.

**Síntoma.** El motor actual no distingue firmas, sellos, anotaciones a
mano ni figuras. Las firmas escaneadas aparecen como caracteres OCR
aleatorios en el `.md`. Los sellos del notario o del juzgado se
transcriben parcialmente, mezclando datos del protocolo con texto del
documento. Cuando el `.md` se entrega al frontier, ese ruido reduce la
calidad del razonamiento del modelo (y consume tokens útilmente).

**Mejora propuesta.** Capa sobre docling (cuando esté integrado vía
§24) que detecta tipos de elemento no-textual y reescribe en
`texto_a_markdown` con convención de marcado:

- `[FIRMA]` — firmas detectadas (no transcribir, solo marcar).
- `[SELLO] ... [/SELLO]` — sellos con texto OCR'd dentro (notario,
  protocolo, fecha extraídos).
- `[MANUSCRITO confianza=X]` — anotaciones a mano (TrOCR opcional).
- `[ILEGIBLE]` — regiones detectadas no transcribibles.
- `[FIGURA]` — imágenes no textuales (planos, fotos, gráficos).

Implementación por capas: capa 1 (marcado genérico `[FIGURA]`) sale con
la integración inicial de docling en §24; capa 2 (distinción
firma/sello/manuscrito) se añade después si el volumen lo justifica.

**Criterio de disparo.** Cuando un caso real produzca ruido importante
por sellos o firmas mal transcritos y la limpieza manual del `.md` sea
costosa. SaRS1 no lo disparó (el ruido fue tolerable). Las escrituras
notariales con sellos múltiples sí lo dispararán.

**Coste estimado.** Capa 1: 2-3 días tras §24. Capa 2: +3-5 días.

**Prioridad.** Baja — diferido. Bloqueado por §24 (depende de docling
integrado).

---

## 26. Intake dedicado de entrevistas (transcripción Meet) en `06_Entrevistas/`

**Detectado.** 2026-06-07, al revisar el estado del intake de entrevistas
frente al flujo real (grabación en Google Meet con transcripción automática
en Google Doc).

**Síntoma.** El andamiaje existe pero está sin cablear: `ensure_case` crea
`00_Input/06_Entrevistas/` (`tests/test_legacy_v1_detection.py` L88-94);
`ENTREVISTA_ROLES` (`core/config.py` L455) y la convención
`<YYYY-MM-DD>_<rol>_<apellido>/` (comentario en `core/config.py` L304) están
definidas pero ningún código las consume ni valida; el evento
`upload_entrevista` (`core/intake_log.py` L50) y el source `"entrevista"`
(`core/intake_manifest.py` L260) están declarados pero nunca se emiten. No hay
subida dedicada: hoy la entrevista solo entra si el abogado deja manualmente la
transcripción como `.txt`/`.docx`/`.pdf` dentro de la carpeta, y aun así sin
subcarpeta normalizada, sin validación de rol y sin traza en el log. Además, la
transcripción de Meet vive como **Google Doc en Drive**, formato que el
extractor no lee directamente (requiere exportación previa a `.docx`/`.txt`).

**Causa raíz.** El refactor intake v2 (sesiones 2-7, mayo 2026) cerró las
decisiones de estructura (carpeta + roles + evento + source) pero la
implementación del path de entrevistas quedó fuera del paso 7, que solo cableó
el expander de subida a `05_CRM`. La pieza de entrevistas nunca se conectó.

**Solución técnica.** No requiere transcripción local (Whisper): Meet ya
entrega texto. Dos piezas:

1. **Función de ingesta** (`core/intake_entrevista.py` nuevo, o ampliación de
   `core/intake_manual.py`): dado rol ∈ `ENTREVISTA_ROLES`, apellido, fecha y
   el Doc de Meet, crea `06_Entrevistas/<YYYY-MM-DD>_<rol>_<apellido>/`, coloca
   la transcripción exportada a `.docx`/`.txt`, la registra en el manifest con
   `source="entrevista"` y emite el evento `upload_entrevista`. Validar rol
   contra `ENTREVISTA_ROLES`; saneamiento de path como en
   `save_file_crm_branch`.
2. **Exportación del Google Doc**: vía conector de Drive (descargar el Doc como
   `.docx`/`.txt`) antes de colocarlo. Arranque manual: el abogado exporta el
   Doc (Archivo → Descargar → Word) y lo arrastra a la carpeta.

Una vez el `.docx`/`.txt` está en `00_Input/06_Entrevistas/`, el pipeline
genérico (inventory → extractor → markdown → anon) ya lo procesa y anonimiza
sin cambios. La sensibilidad del habla espontánea queda cubierta por la
anonimización general del pipeline (no es un gap adicional).

**Coste estimado.** ~60-90 líneas (ingesta + validación de rol + emisión de
evento) + expander UI en Streamlit (~40 líneas) + 3-4 tests. La exportación
automática del Google Doc vía conector Drive: +1 día.

**Prioridad.** Media — el flujo manual (exportar Doc + arrastrar a la carpeta)
ya desbloquea el caso hoy; el cableado dedicado aporta normalización de nombre,
validación de rol y traza forense en el log, valioso pero no bloqueante.

---

## 27. Política de retención y cifrado del material en claro (`01_Procesado/` + nombres de fichero con PII)

**Detectado.** 2026-06-07, en revisión de arquitectura: material con PII en
claro persiste en disco sin política de retención ni constancia de cifrado.

**Síntoma.** `core/extractor.py` (L158-174) escribe el texto extraído en claro
a `01_Procesado/raw_text/{slug}.txt` y **nunca lo borra**: no hay paso de purga
tras generar el `.md` anonimizado. `core/inventory.py` (L61-74) preserva el
nombre de fichero original en `name`/`rel_path` y lo propaga a `_inventory.json`
— los nombres pueden contener PII. `.gitignore` (L21-24) excluye `data/CASOS/*`
de git, pero eso no es cifrado en reposo ni política de retención. Resultado:
PII en claro persiste indefinidamente en el disco de trabajo, fuera del control
del flujo de anonimización.

**Causa raíz.** El pipeline se diseñó para producir el material anonimizado,
sin un paso de ciclo de vida del crudo. La capa de cumplimiento (`CUMPLIMIENTO.md`,
RIA/RGPD) está pendiente y todavía no cubre retención ni cifrado del crudo local.

**Solución técnica.** (1) Política explícita de retención: tras generar el `.md`
anonimizado y su `_mapa_caso.json`, ofrecer purga (o purga automática
configurable) de `01_Procesado/raw_text/`, y documentar el plazo de
conservación del crudo. (2) Saneamiento de nombres de fichero con PII (slug
neutro) o exclusión del nombre original del `_inventory.json` expuesto a fases
posteriores. (3) Constancia del requisito de cifrado en reposo y control de
acceso del disco de trabajo local.

Matiz de alcance: el crudo lo genera `core/extractor.py`, no `core/anon/`; esta
mejora es transversal al pipeline. La pieza de cifrado en reposo / control de
acceso se solapa con `docs/superpowers/plans/PLAN_DESPLIEGUE_EV.md` (backup off-site cifrado con
`rclone crypt`, retención de logs de acceso) y pertenece en parte al plan de
cumplimiento RIA/RGPD pendiente; aquí se documenta el delta técnico
(retención/purga del crudo + PII en nombres de fichero).

**Coste estimado.** ~30-50 líneas (paso de purga configurable + saneamiento de
nombres) + 2-3 tests. La parte de cifrado / control de acceso es
organizativa/documental (no código).

**Prioridad.** Alta — PII en claro sin política de retención en disco es
exposición GDPR directa; coherente con la prioridad de las entradas que tocan
confidencialidad (#13, #14, #23).

---

## 28. Fecha del documento en el nombre en formato ISO (AAAA-MM-DD) + ensamblado con remitente/tipo

**Detectado.** 2026-06-07, en revisión de arquitectura.

**Síntoma.** `core/anon/renombrar.py` produce un prefijo de fecha `YYYYMMDD`
**sin guiones** (`strftime("%Y%m%d")`, L135 y L252) y ensambla solo
`<YYYYMMDD> - <stem>`, sin remitente ni tipo de documento. `tiene_prefijo_fecha`
valida el formato sin guiones (`^\d{8}\s*-\s*`, L106). El motor de detección de
fecha (`extraer_fechas`, `mejor_fecha`) ya existe y funciona.

**Causa raíz.** El renombrador se portó de Expedientes Seguros con su formato
de prefijo original; nunca se adoptó el formato ISO con guiones ni se amplió el
ensamblado del nombre con otras piezas (remitente/tipo).

**Solución técnica.** (1) Cambiar el formato del prefijo a ISO con guiones
(`strftime("%Y-%m-%d")`) y actualizar `tiene_prefijo_fecha` al patrón
`^\d{4}-\d{2}-\d{2}\s*-\s*`. (2) Opcional: componer el nombre final como
`<AAAA-MM-DD> - <remitente> - <tipo> - <stem>` cuando esos campos estén
disponibles. Cumple `feedback_anon_logica_intacta`: solo toca el formato de
nombre en `renombrar.py`, no la lógica de detección (regex/listas/thresholds
del Anonimizador). No cruza con #2 (separar_pdf, troceo a nivel de contenido)
ni con #14 (variantes de cliente en el mapa).

**Coste estimado.** ~10-15 líneas (cambio de formato + regex) + migración
opcional de nombres ya generados con el formato antiguo + 2 tests. El ensamblado
remitente/tipo: +30-40 líneas si se implementa.

**Prioridad.** Baja — mejora organizativa/cosmética; no afecta confidencialidad.
Coherente con la prioridad de #9 y #25.

**Decisión 2026-06-10 (Cowork, aprobada por Nikolai).** Se confirma el cambio a
ISO con guiones (D1). **Alcance acotado (D2):** el prefijo de fecha y el
ensamblado con remitente/tipo se aplican **solo** en `06_Anonimizado/` y en
vistas derivadas (`INDICE.md`); **nunca** en `01_Procesado/` ni en ningún nombre
de fichero con PII en claro (cruza con #27 — un nombre con remitente real es PII).
La **identidad** del documento es `id_doc`/`hash` del catálogo
`indice_documental.yaml`, no el nombre: renombrar es seguro porque ningún
consumidor de identidad depende del nombre (el slug del pipeline es stem-only,
`extractor.py:214` / `markdown_generator.py:30`; el organizador Ollama que
indexaba por slug quedó descartado). Bundles en #29. Registro completo en
`PLAN.md` → `[SIGUIENTE-REORG-05CRM]`.

---

## 29. Bundles cabecera-anexo por metadato (`parent_id` en `indice_documental.yaml`)

**Detectado / decidido.** 2026-06-10 (Cowork, aprobado por Nikolai). Hoy **no
existe** modelado de la relación cabecera↔anexo en ningún sitio: no hay
`parent_id`, `role_in_bundle` ni equivalente en código ni en frontmatter (grep
repo-wide vacío; los `parent_id` que aparecen son del árbol de carpetas del CRM,
concepto distinto). `separar.py` trocea un PDF concatenado en segmentos
**hermanos** por tipo (incluido `DOC_ANEXO`) sin relación padre-hijo;
`linker.py` enlaza por coincidencia de stem en el cuerpo (wikilinks),
insuficiente y semánticamente débil para expresar jerarquía probatoria.

**Solución decidida.** Modelar el bundle como **metadato, no como subcarpeta
física**: añadir al esquema de `indice_documental.yaml` los campos `parent_id`
(id_doc de la cabecera; `null` si el documento es suelto) y `orden_en_bundle`
(int, orden de aparición/relación, no alfabético). El `INDICE.md` derivado
renderiza los anexos indentados bajo su cabecera. Razones: (i) el catálogo ya es
la fuente de verdad canónica decidida (`[SIGUIENTE-CATALOGO-DOCUMENTAL]`); (ii)
ancla por `id_doc`/hash → **sobrevive a renombrado y a la anonimización**; (iii)
no toca la separación funcional crudo/anonimizado que protege el secreto
profesional; (iv) una subcarpeta física rompería idempotencia, colisionaría
stems en `linker`, y mezclaría fechas (un anexo de febrero metido en la carpeta
de una cabecera de marzo descoloca a `renombrar.py`, que fecha por contenido —
la unidad probatoria pesa más que la fecha individual del anexo).

**Relación con el detector de conjunto.** La asignación de `parent_id` la puede
**proponer automáticamente** el detector de conjunto descrito en `PLAN.md`
→ `[SIGUIENTE-REORG-05CRM]` (lote por timestamp de modificación del CRM +
nomenclatura tipo `D NN`); los clústeres de baja confianza →
`pendiente_revision`, sin adivinar.

**Coste estimado.** Esquema + render: ~40-60 líneas + 2-3 tests. La autodetección
(detector de conjunto) se contabiliza aparte y tiene su propio requisito previo
(traer la fecha de modificación del CRM, hoy no disponible — ver `PLAN.md`).

**Prioridad.** Media — habilita navegación por unidad probatoria; depende del
catálogo `indice_documental.yaml`. Implementación: Claude Code.

**Estado 2026-06-10 (sesión 35, segunda tanda de `[SIGUIENTE-REORG-05CRM]`).**
El **detector de conjunto (D9)** ya está implementado (`core/conjunto_detector.py`):
clusteriza por `modified_at` idéntico ∩ patrón de prueba `D NN`, ancla a la
cabecera (odd-one-out sin patrón) y propone bucket. Por ahora **solo emite
propuestas** (eventos `conjunto_detectado` / `pendiente_revision`); la
**persistencia de `parent_id`/`orden_en_bundle` queda diferida a este #29 + el
catálogo `[SIGUIENTE-CATALOGO-DOCUMENTAL]`** (decisión de Nikolai: no construir
el catálogo a medias). Cuando exista `indice_documental.yaml`, conectar
`log_bundle_proposals` → escritura de `parent_id` para las propuestas de alta
confianza.

---

## 30. El core reconoce el manifiesto `<subdir>/_index.md` y resuelve los wikilinks de Navegación

**Disparador.** Las skills procesales (`escritos-judiciales`, `cendoj-descarga`,
`preparacion-audiencia-previa`, `preparacion-juicio-oral`) ya escriben work-product
en las subcarpetas del expediente y lo registran con el helper canónico
`.claude/skills/_shared/registrar_outputs.py`: (a) un manifiesto `<destino>/_index.md`
(p. ej. `05_Procedimiento/_index.md`, `05_Procedimiento/Jurisprudencia/_index.md`,
`04_Output predemanda/_index.md`) y (b) wikilinks en la sección `## Navegación` de
`00_Input/_caso.md`. Hoy el core (`case_manager`/`linker`) **no lee** esos manifiestos
ni resuelve esos wikilinks de forma general.

**Pendiente.** Que el core: (i) reconozca y liste `<subdir>/_index.md` al inventariar
el expediente (no solo `05_Procedimiento`, sino cualquier subdir de `CASO_SUBDIRS`);
(ii) resuelva los wikilinks de `## Navegación` para todos los `tipo` registrados
(demanda, contestación, recurso, requerimiento, jurisprudencia, minuta_ap,
solicitud_prueba, conclusiones, interrogatorio, orden_vista, cuadro_hechos); y
(iii) decida si el manifiesto se normaliza a `_index.json` para consumo programático.

**Relación.** Generaliza el aviso de la skill de audiencia previa
(`references/manifiesto_y_registro.md`), que ya pedía esto solo para
`05_Procedimiento`. Sustituye/absorbe ese aviso puntual.

**Prioridad.** Media — el registro ya funciona end-to-end desde las skills; esto
mejora la lectura del expediente desde el core. Implementación: Claude Code.

---

## 31. Combobox F2 — búsqueda por contrario y por nº de autos (`num_asunto`)

- **Combobox F2 — búsqueda por contrario:** no resuelta por las vías REST probadas (relación inversa contrario→expedientes; ver DEAD_ENDS). Punto de reentrada: tantear `GET /api/related_registers` (sin probar; la entrada de DEAD_ENDS indica que acepta GET para "listado de relaciones"). Si no devuelve el inverso, quedaría scraping del frontal legacy. Disparador: caso real que lo necesite.
- **Combobox F2 — búsqueda por nº de autos (`num_asunto`):** trivial de añadir a `_SEARCH_PROPS_BY_ELEMENT` cuando el campo deje de estar vacío en el tenant. Disparador: que se empiece a poblar `num_asunto`.

## 32. Gobernanza de skills — superestructura diferida (Ola 1 ejecutada 2026-06-16)

Tras la homogeneización de skills (PLAN.md, «Alcance REVISADO 2026-06-16»), se
ejecutaron solo corrección (Ola 1) + mínimo reutilizable (plantilla +
`validate_skills.py` modo aviso). Lo siguiente queda **diferido**; **disparador
para reabrir**: más skills, más manos, o una inconsistencia que cueste algo real.

- **Charter** `_shared/ARQUITECTURA_SKILLS.md` (referencia, no duplica `MEJORA_CONTINUA_SKILLS.md`).
- **`scripts/new_skill.py`** (scaffolder que instancia `_shared/_plantilla-skill/`).
- **`inventario_skills.json` + `INVENTARIO.md`** (termómetro de conformidad).
- **`validate_skills.py` en modo bloqueante** (pre-commit + CI) y regla blanda en `CLAUDE.md`.
- **Retrofit masivo de identidad** (`metadata` con ejes `rol`/`naturaleza` + `license`) de las 7 skills sin él (`cendoj-descarga`, `escritos-judiciales`, `preparacion-litigio-civil`, `preparacion-audiencia-previa`, `preparacion-juicio-oral`, `engel-volkers`, `viabilidad-prerelleno`). Se alinean **al tocar cada una**, no en barrido. Estado medible con `python scripts/validate_skills.py`.
- **Generalizar jurisprudencia+cosecha a `_shared/`**: se queda en `oposicion-alegacion-nulidad` hasta que una 2.ª skill lo necesite.
- **Salvaguarda ACL** (decisión 3 del PLAN): verificar **una vez** que el Shared Drive `Biblioteca_Skills/` excluye de hecho a los miembros de E&V (p. ej. Marta Reynares). Si los incluye, mover a carpeta restringida.

## 33. Bug latente: frontmatter YAML inválido en `preparacion-juicio-oral`

Detectado por `scripts/validate_skills.py` (2026-06-16). La `description` del
frontmatter es un escalar **sin comillas** que contiene `(no escritos procesales):
documento` — el `:` interno la hace **YAML inválida** para un parser estricto
(`mapping values are not allowed here`). El cargador de skills lo tolera (la skill
está en uso), pero cualquier herramienta que parsee el frontmatter con PyYAML
falla. Arreglo: entrecomillar la `description` o pasarla a bloque `>-`. Se aplica
**al hacer el retrofit de identidad de esa skill** (#32) o antes si una herramienta
lo necesita.

## 34. Sala de lectura como skill-Cowork multiusuario (autonomía Paola/Ana)

**Anotado 2026-06-17** (brainstorming sala de lectura F4–F6, decisión de Nikolai
de dejar la idea registrada). La organización de la sala de lectura se construye
ahora como `core/sala_lectura.py` **Python local** (spec
`docs/superpowers/specs/2026-06-17-sala-lectura-f4f6-design.md`), disparable por
Nikolai vía CLI + sesión Claude Code y por un botón Streamlit que **no cierra el
residuo sin una sesión de Claude**. Consecuencia: hoy **solo Nikolai** puede
disparar la organización completa (Claude Code corre en su PC, contra el disco
local; Paola/Ana solo usan Streamlit y Cowork no ve el disco local).

**Idea diferida.** Para que Paola/Ana disparen el equivalente a la "opción 1" de
forma autónoma, reescribir la organización como una **skill que corre en Cowork**
(servidor claude.ai), con los ficheros del caso accesibles desde **Google Drive**
(donde ya viven los expedientes jurídicos, `CASOS_ROOT`). El despacho ya ejecuta
skills así (`viabilidad-prerelleno`, `escritos-judiciales`, etc.).

**Coste / por qué no se hace ya:** (i) hay que llevar la lógica probada del `core/`
(dedup por hash, idempotencia, skip OCR, catálogo YAML) dentro de la skill y
correrla en el sandbox de Cowork trayendo los ficheros desde Drive — más lento y
frágil; (ii) **extiende la excepción RGPD** (lectura en claro por LLM) de "solo
Nikolai" a varias personas y más volumen → la conversación del DPA pasa a ser la
pieza seria; (iii) bifurca la arquitectura (core local para Nikolai + skill para
Cowork, o migración completa).

**Disparador para reabrir:** el DPA resuelto **y** una necesidad real de que
Paola/Ana organicen casos sin intervención de Nikolai. Relacionado con la fase
"clasificador por conector" del spec (Scaleway/Claude API sustituyendo a
Claude-en-sesión para el residuo).

## 35. Bundles de WhatsApp en la sala de lectura (chat + media/) — [SUPERADO 2026-06-25 por `core/whatsapp_atomize`]

> **SUPERADO 2026-06-25.** El motor `core/whatsapp_atomize` (spec
> `docs/superpowers/specs/2026-06-25-whatsapp-atomize-design.md`) produce la sala de WhatsApp
> con creces: chat numerado citable + atoms de enterrados + adjuntos dedup por sha256 con ficha
> (`INDICE_ADJUNTOS.md`) + CRONOLOGIA cross-chat + corpus. Sustituye la idea del bundle plano.

**Detectado 2026-06-17** (review final sala-lectura F4–F6). El spec
`docs/superpowers/specs/2026-06-17-sala-lectura-f4f6-design.md` §7 prevé que en
la sala de lectura los chats de WhatsApp se agrupen como bundle (chat `.txt`/`.md`
+ multimedia en subcarpeta `media/`). La implementación de F4 (`core/sala_lectura.py::poblar_sala_lectura`)
solo materializa bundles para el CRM (vía `conjunto_detector.detect_bundles`, que
opera sobre `GdocuDocInfo`). Los chats de WhatsApp y su multimedia se copian
**planos** a `Sala lectura/WhatsApp/`. Funcional, pero no agrupa chat↔media.
**Disparador:** un caso real con export de WhatsApp + adjuntos que moleste navegar
plano. **Solución:** detector análogo para WhatsApp (el chat es la cabecera, los
ficheros de media sus adjuntos), reaprovechando el patrón de `_bundle_map`.

## 36. Guarda de colisión de nombre canónico en la sala de lectura

**Detectado 2026-06-17** (review Task 9 sala-lectura). `poblar_sala_lectura`
copia con `nombre_canonico` = `<fecha>_<tipo>_<descripcion><ext>`. Dos documentos
DISTINTOS (distinto hash) que produzcan el mismo nombre canónico (misma fecha,
mismo tipo, descripción que sluga igual a 50 car.) colisionan en el mismo destino
y el segundo `shutil.copy2` **sobrescribe** al primero silenciosamente. El dedup
por hash NO protege (solo cubre contenido idéntico). Raro pero posible. **Solución:**
guarda de colisión en `poblar_sala_lectura` (sufijo `_2`/`_3` por destino ya usado
en la corrida, determinista respetando idempotencia) o fragmento de hash en el
nombre. **Disparador:** primera colisión observada en un caso real.

## 37. Clasificador LLM del residuo de intake (autorrelleno de la worklist `_clasificar.md`) [PROMOVIDO → PLAN.md]

> **[PROMOVIDO → PLAN.md] 2026-06-18.** Disparador concreto (petición de Nikolai).
> Tarea accionable en `PLAN.md` → `[SIGUIENTE-RESIDUO-LLM]` (`MEJORAS #37`).

**Disparador.** 2026-06-18, petición de Nikolai (Cowork): poder dejar documentos
sueltos en una carpeta e ir "procesándolos y clasificándolos con un prompt", al no
verse práctico el intake vía uploader de Streamlit.

**Estado actual (no es un gap de carpeta).** La carpeta de drop manual **ya existe**:
`00_Input/04_Manual` (mapeada a `fuente: manual` en `core/catalogo_documental.py`
`_SOURCE_MAP`). El patrón "soltar en carpeta + procesar" tampoco depende del uploader:
el orquestador headless (`scripts/run_pipeline.py` → `core/sala_lectura.py`) hace
inventario de `00_Input` → catálogo (`indice_documental.yaml`, una entrada/doc con
hash) → `clasificar_caso` (clasificación **determinista**: por nombre de fichero
`_categoria_por_nombre` + detección de imágenes, con `UMBRAL_CONFIANZA_AUTOMOVE`) →
el residuo no resuelto se vuelca a `01_Procesado/_revisar/_clasificar.md` (worklist
que hoy rellena el letrado a mano) → `aplicar_clasificacion` la vuelca al catálogo.
El uploader de Streamlit es solo **una** forma de disparar esto.

**Gap real.** El hueco que Nikolai quiere automatizar es justo el paso humano: rellenar
la worklist del residuo. Hoy todo lo que el clasificador determinista no resuelve por
nombre exige intervención manual del letrado.

**Solución propuesta.** Paso opcional `clasificar_residuo_llm(case_id)` que, sobre las
entradas en residuo, lea el `.md`/texto extraído de cada documento y **autorrellene**
las columnas de `_clasificar.md` (tipo documental, fecha, parte, descripción) con
criterio LLM, dejando al letrado solo validar antes de `aplicar_clasificacion`.
Respeta la arquitectura: la lógica vive en el core, el LLM ocupa exactamente el slot
humano de la worklist (no inventa estructura nueva), y `aplicar_clasificacion` sigue
siendo el único camino al catálogo canónico. El prompt clasifica solo lo que ve
(regla de la casa: no inventar). Infraestructura ya disponible: `core/llm_cloud.py`
y el `docs/superpowers/plans/PLAN_PRERELLENO_LLM_VIABILIDAD.md`.

**Descartado.** Generar un índice/clasificación paralelo desde Cowork al margen de
`indice_documental.yaml` reproduce la divergencia PC↔nube que el proyecto ya eliminó
al sacar la bitácora de Drive (dos fuentes de verdad documentales que se contradicen).

**Restricciones.** (i) Implementación en **Claude Code** (toca `core/`, no se puede
desde Cowork). (ii) Cowork solo monta `04_Manual` + el repo, no la raíz del caso ni
`01_Procesado`, así que el disparo y la escritura del catálogo ocurren en local.
(iii) Extiende la **excepción RGPD** de lectura en claro por LLM (cruza con #34 y #27):
si se corre vía conector/API en vez de Claude-en-sesión, la conversación del DPA es
la pieza seria.

**Coste estimado.** ~60-90 líneas (`clasificar_residuo_llm` + prompt + parseo a las
columnas de la worklist) + 3-4 tests. Reaprovecha `llm_cloud.py` y el esquema de
worklist ya existente en `sala_lectura.py`.

**Prioridad.** Media — el flujo manual (drop en `04_Manual` + `run_pipeline` +
rellenar worklist) ya desbloquea el caso hoy; el autorrelleno LLM ahorra el paso
manual del residuo. Relacionado con #34 (sala de lectura multiusuario / DPA) y con la
fase "clasificador por conector" del spec
`docs/superpowers/specs/2026-06-17-sala-lectura-f4f6-design.md`. Implementación: Claude Code.

---

## 38. `clasificar_residuo_llm`: permitir sobrescribir la fecha de baja calidad (`mtime`)

**Detectado.** 2026-06-18, al probar #37 sobre el caso real BaRS1 ([inmueble]).

**Síntoma.** `clasificar_caso` pre-rellena la columna **Fecha** de la worklist del
residuo con el `mtime` del fichero (`fecha_fuente=mtime`) cuando no hay fecha en el
nombre. Como `rellenar_worklist` **no pisa celdas no vacías** (regla correcta: no
machacar lo ya puesto), la fecha de **contenido** que el LLM/Claude extrae del
documento (más fiable) **nunca se aplica**: el catálogo queda con la fecha `mtime`.
Observado en BaRS1: "TITULAR REAL 2021" (acta de 2021-09-29) quedó fechado
2024-06-04 (mtime de Drive).

**Solución propuesta.** Permitir que el autorrelleno **sobrescriba la Fecha solo
cuando su origen sea `mtime`/`desconocida`** (baja calidad) y el LLM aporte una fecha
de contenido con confianza suficiente; **nunca** pisar una fecha de contenido ya
puesta (humano o regla ISO del nombre). Alternativa más simple: que `clasificar_caso`
**no** pre-rellene la Fecha del residuo (dejarla vacía) y que la ponga el LLM/humano;
requiere propagar `fecha_fuente` a la worklist o un marcador de "fecha provisional".

**Coste estimado.** ~10-15 líneas + 1-2 tests.

**Prioridad.** Baja — el `mtime` es un fallback razonable y el letrado puede corregir
la fecha en la worklist antes de `aplicar_clasificacion`.

---

## 39. Robustez/rendimiento del OCR (Docling/RapidOCR)

**Contexto.** 2026-06-18, BaRS1: `extractor.extract_all` segfaulteaba (`std::bad_alloc`
en RapidOCR) al OCR-izar un PDF largo. Resuelto **parcialmente** (`2eeec1a`): pypdf
primero para PDFs con capa de texto, OCR solo para escaneados con guarda
`MAX_OCR_PAGINAS`. Quedan dos flecos:

**(1) Robustez (el crash no capturable).** Un PDF **escaneado** con una página de
muy alta resolución puede disparar `bad_alloc` aunque esté dentro del límite de
páginas (el OOM es por tamaño de imagen, no solo por nº de páginas). Al ser un crash
de C++, no lo captura `try/except` y mata `extract_all`. **Fix robusto:** ejecutar
Docling en un **subproceso** con límite de tiempo/memoria; si crashea, el padre lo
captura, marca el doc (`OCR_REQUERIDO`) y continúa. Complemento: bajar `images_scale`
/ cap de resolución en `PdfPipelineOptions`.

**(2) Rendimiento.** Los docs que sí necesitan OCR son lentos en CPU (BaRS1: 12 docs
≈60 min). Opciones: paralelizar por proceso, bajar DPI, o GPU.

**Prioridad.** Media — el crash observado ya no ocurre con el flujo real; el riesgo
residual es un escaneado de una sola página gigante. La lentitud del OCR es molesta
en casos con muchos escaneados.

## 40. Copia binaria desde Cowork → volver Cowork constructor completo de la sala

**✅ RESUELTO 2026-06-23 (vía 1, conector `expedientes-xl`).** Confirmado end-to-end en el
intake del zip W-01VG51 (5 PDFs, 11 MB) al expediente W-02VND1 desde Cowork: `extract_archive`
(zip), `copy_path`/`copy_dir` (binarios de 5 MB), `hash_path` (sha256), `delete_path`,
`append_text` y `write_file_base64` operan server-side sobre `G:\…\EXPEDIENTES - TYUKHAY LEGAL`.
Cowork ya deposita binarios y, en principio, puede montar la sala completa sin Claude Code.
**Cerrado del todo 2026-07-19 (fase 2):** la skill `organizar-sala-lectura` v1.8 migró al
consolidado y ya usa `copy_path`/`copy_dir` server-side (antes seguía con el reparto viejo
"solo texto") → Cowork-en-PC monta la sala completa (texto **y** binarios) sin Claude Code.
El `CLAUDE.md` y `docs/DESPLIEGUE_MCP_DRIVE_DISCO.md` (bundle Code) quedan alineados.
**Residuo abierto:** no hay extracción de texto/OCR de PDF server-side (datar escaneados sigue
siendo del pipeline local) → ver #42.

**Problema (confirmado 2026-06-22, re-aplicación BaRS1/[inmueble]; ver `DEAD_ENDS.md`).**
Desde Cowork no se pueden copiar binarios (PDF, fotos, vídeos, `.xlsx`) a la Sala lectura
del despacho. El MCP local `expedientes` (`@modelcontextprotocol/server-filesystem`) no
expone copia: `write_file` es solo texto, no hay `copy_file` y `move_file` es destructivo;
y el conector de Drive en la nube disponible en Cowork es la cuenta de E&V
(`@engelvoelkers.com`), que no ve la Drive del despacho «EXPEDIENTES - TYUKHAY LEGAL». Hoy,
por tanto, Cowork solo amplía la sala en TEXTO; los binarios los copia el motor local
(Claude Code / `scripts/sala_lectura.py` sobre `G:` vía `shutil`).

**Vías (cualquiera vuelve Cowork constructor completo, sin Claude Code):**
1. **Dar copia binaria al MCP `expedientes`**: sustituir/extender el `server-filesystem`
   por uno que exponga una herramienta `copy_file` (copia byte a byte dentro de `G:`).
   Es la opción limpia: Cowork-en-PC leería rápido y copiaría binarios en el mismo Drive.
2. **MCP a medida mínimo** con una sola tool `copy_path(src, dst)` sobre `G:`.
3. **Conector de Drive del despacho** (no el de E&V) montado en Cowork: su `copy_file`
   server-side copiaría binarios por `fileId` — pero es per-fichero (lento) y duplica el
   acceso que ya da el MCP local.

**Disparador de promoción a `PLAN.md`:** que el equipo (Paola/Ana) necesite montar/ampliar
salas con binarios desde Cowork sin pasar por Claude Code, o decisión explícita de Nikolai.

**Prioridad.** Media. Hoy el motor local cubre el caso; esto es comodidad/autonomía de
equipo. Relacionado: #34 (sala como skill-Cowork multiusuario).

## 41. Plugin nativo de Cowork para empaquetar las skills del despacho

**Idea (anotada 2026-06-22).** Cowork no carga los plugins de Claude Code (sistemas de
plugins separados, verificado: un plugin instalado por CLI se ve en el tab Code, no en
Cowork). Hoy las skills entran en Cowork por **re-import manual del `.skill`**, una a una.
Un **`.plugin` nativo de Cowork** (tooling `create-cowork-plugin`) empaquetaría varias
skills del despacho como **un único bloque versionado**, instalable de una vez.

**Ventajas (escalan con nº de skills × nº de usuarios Cowork):**
- Una instalación/actualización **versionada** en vez de N imports manuales.
- Más simple para **Paola/Ana** (instalar un plugin vs navegar la UI de importación de skills).
- **Menos drift** de versiones entre el equipo; actualización **atómica** de todo el set.

**NO resuelve (para no sobrevenderlo):**
- El conector `expedientes-xl` **sigue yendo por `claude_desktop_config.json`** (host-side;
  un plugin de Cowork no alcanza el disco local). Los prerequisitos por máquina (Drive
  montado + `pip install mcp`) son irreductibles.
- Es un **tercer formato a mantener** (junto al plugin de Claude Code en `despacho-plugins`
  y los `.skill` sueltos).

**Disparador de promoción a `PLAN.md`:** ≥3 skills activas en Cowork usadas de forma
habitual por el equipo (Paola/Ana) Y que los imports manuales + el drift de versiones
empiecen a doler; o decisión explícita de Nikolai.

**Prioridad.** Baja-media. Hoy (1 skill nueva, sobre todo Nikolai) es marginal. Relacionado:
#34 (sala como skill-Cowork multiusuario) y #40 (copia binaria desde Cowork — ya cubierta
por el conector `expedientes-xl` de la sesión 2026-06-22).

## 42. Extracción de texto/OCR de PDF server-side en `expedientes-xl`

**Contexto (2026-06-23, intake [inmueble] W-02VND1).** Con #40 resuelto, Cowork ya mueve
binarios al Drive, pero **no puede leer el contenido de un PDF**: `expedientes` `read_media_file`
acepta solo image/audio (rechaza PDF), y el shell está aislado del Drive (no hay `pdftotext`
sobre el mount). Consecuencia: al hacer intake de PDFs **escaneados** no se pueden datar ni
indexar en Cowork; se depositan `sin-fecha_...` y la datación queda para el pipeline local /
`organizar-sala-lectura`. En el intake del zip W-01VG51 esto dejó 5 PDFs sin fecha (incluido
`Z02NT34N`, núcleo probatorio de comercialización previa).

**Mejora propuesta.** Añadir a `expedientes-xl` una tool server-side de extracción de texto
que **no pase bytes por el modelo**: `extract_pdf_text(path) -> str` (capa de texto vía pypdf)
y, para escaneados, `ocr_pdf(path, idiomas) -> str` (reusar `core/anon/ocr.py` /
`extractor`). Devuelve solo el texto necesario para datar/clasificar. Así el intake y la sala
de Cowork podrían fijar `AAAA-MM-DD` e identificar el documento sin Claude Code.

**Disparador de promoción a `PLAN.md`:** que el volumen de intake desde Cowork con escaneados
sin datar empiece a doler, o decisión explícita de Nikolai. Relacionado: #28 (fecha ISO en el
nombre), #39 (robustez OCR), #1/#11/#21 (OCR del pipeline), #40.

**Prioridad.** Media — hoy el pipeline local cubre la datación; esto da autonomía a Cowork.

## 43. `intake-expediente`: pasada única y gate sin rama de OCR  [PROMOVIDO → PLAN.md]

*Promovido 2026-06-23 por decisión de Nikolai (Cowork): agilizar el intake y reducir los
diálogos de permiso por-llamada del conector. Ver `PLAN.md` → `[SIGUIENTE-INTAKE-EXPEDIENTE-AGIL]`.*

**Contexto (2026-06-23, mismo intake).** El flujo gastó llamadas y un round-trip evitables:
(a) extraje a un tmp de inspección y luego copié los originales **uno a uno**; (b) copié los
PDFs al mount para leerlos con `pdftotext` — imposible, mount aislado (ver `DEAD_ENDS.md`);
(c) el gate ofreció "extraer fechas", rama fuera de capa e inviable en Cowork. Cada `copy_path`/
`hash_path`/`delete_path` dispara además, si no se ha activado "Permitir siempre", un **diálogo
de permiso** en Cowork: menos llamadas = menos diálogos.

**Mejora propuesta (skill `.claude/skills/intake-expediente/`).**
1. **Una pasada**: extraer a staging para listar/`hash_path`, y tras el OK copiar con
   `copy_dir` cuando todo va a una misma `<fuente>` (en vez de N `copy_path`).
2. **Gate sin OCR**: para escaneados, proponer `sin-fecha_...` por defecto y **no** ofrecer
   datación/OCR en Cowork; remitir la datación al pipeline local (hasta que exista #42).
3. **Regla dura**: nunca copiar binarios al mount para leerlos con bash (no se ven).

Cambios de texto en la skill (descripción de procedimiento + gotchas); sin tocar `traza.py`.
Editar en `.claude/skills/` (fuente única) y re-empaquetar el `.skill`.

**Prioridad.** Media-baja — calidad/coste del intake; no bloqueante.

---

## 44. Aplanado de emails anidados: revisión adversarial y residuales

**Contexto (2026-06-24, Parte 1 del rescate de correos).**
`core.email_export.iter_nested_originals` recupera los `.eml` que viajan como adjunto
`message/rfc822` **rebanando los bytes crudos** (no `as_bytes()`, que normaliza CRLF→LF
y repliega cabeceras), para que el hijo sea byte-original. Una revisión adversarial
(3 lentes) sobre el aplanado encontró 3 HIGH + 2 MEDIUM + varios LOW/NIT; **todas las
HIGH/MEDIUM y las LOW 44.1/44.2 se corrigieron en el mismo commit** (con tests). Lo que
sigue son los residuales aceptados (44.3–44.5).

**✅ RESUELTAS en el commit (referencia):**
- *Split anclado a inicio de línea* (`_split_mime_parts`, RFC 2046): un `--boundary`
  citado a mitad de línea ya NO trunca el `.eml` ni descarta hijos posteriores.
- *Separador de cabeceras por posición* (`_split_headers_body`): tolera line-endings
  mezclados (padre `\n\n` con hijo `\r\n\r\n`).
- *Robustez*: una excepción en `_aplana_anidados` se registra en `report.errors` y NO
  aborta la corrida (un email entre 125 no la tumba).
- *`force=True` re-aplana* los hijos borrados aunque el padre siga en disco.
- *Procedencia (`forwarded_in`) reconstruida desde disco* en `_emit_traza`: determinista
  (independiente del orden en que Gmail listó padre vs. suelto) y cubre el backfill.
- **44.1 (red de seguridad anclada al parser)**: `_nested_con_fallback` devuelve el
  rebanado byte-fiel cuando recupera **el mismo multiset de `Message-ID`** que ve el parser
  (`msg.walk()`); solo cae al fallback re-serializado + aviso si difieren. **Corregido tras
  la reextracción real de W-02VND1 (2026-06-24):** el primer intento usaba "boundary
  repetido entre niveles" como disparador, pero eso resultó **demasiado agresivo** — el
  `boundary` SÍ se repite en datos reales (3 padres `jdb_*`, 126 anidados de Apple Mail/
  Outlook/Nodemailer, que reutilizan tokens entre mensajes **primos**), y el rebanado
  byte-fiel los recuperaba CORRECTAMENTE (mids idénticos al parser, 0 ilegibles), pero el
  trigger los re-serializaba sin necesidad. La coincidencia de mids es el disparador
  correcto. *Residual:* si un anidado reutilizara el `boundary` de un **ancestro directo**,
  el rebanado podría truncar el cuerpo conservando el `Message-ID` (la coincidencia de mids
  no lo detectaría); no observado en datos reales (las colisiones son entre primos, no
  ancestro↔descendiente). Fix completo si se materializa: parser con pila de boundaries por
  nivel de anidamiento.
- **44.2 (hijo sin `Message-ID`)**: dedup de respaldo por SHA-256 del contenido
  byte-original dentro de `_aplana_anidados`, de modo que el mismo bloque sin `Message-ID`
  reenviado por dos vías en una corrida no se multiplique.

**Residuales aceptados (no abordados):**

**44.3 — Padre SIN `Message-ID` + `force=True` no es idempotente.** Si el correo padre
carece de `Message-ID` (los mensajes de Gmail siempre lo traen, así que es casi imposible
en producción) y se re-exporta con `force=True`, el padre se reescribe vía `_ruta_unica`
(`_2`, `_3`…) y re-dispara el aplanado en cada corrida. Es comportamiento preexistente del
`export_label` para cualquier mensaje sin `Message-ID`. La dedup de respaldo por SHA (44.2)
colapsa los **hijos** sin `Message-ID` dentro de una misma corrida, pero `vistos` se
reconstruye cada corrida solo desde los `Message-ID` del disco (no desde SHAs), así que
cross-corrida + `force=True` un hijo sin `Message-ID` puede reescribirse. En la práctica no
ocurre: los mensajes de Gmail siempre traen `Message-ID`. *Mitigación si se materializa:*
gatear por el `gmail_id` del índice persistente (estable), o sembrar `vistos` también con
SHAs de los `.eml` sin `Message-ID` ya en disco.

**44.4 — Pico de memoria ~12× el tamaño del padre.** El rebanado hace copias sucesivas
(`split`, `headers + b"\r\n\r\n"`, `b64decode`) y recursiona; un padre de ~13 MB midió un
pico de ~165 MB. Tolerable para un padre, pero `export_label` baja en paralelo
(`max_workers=8`): varios padres grandes simultáneos multiplican el pico. *Mitigación si
aparece presión de memoria:* serializar `_aplana_anidados` fuera del pool de descarga y/o
liberar `raw_bytes` antes de recursionar.

**44.5 — `split_eml` ya no extrae sueltos los adjuntos internos de un `.eml` anidado.**
Cambio de comportamiento vs. la versión `msg.walk()`: ahora `message/rfc822` se trata como
hoja, así que un PDF que viaja DENTRO de un email anidado NO se extrae como fichero suelto
por `split_eml`. Con el aplanado por defecto (`flatten_nested_emails=True`) el hijo se
deposita a primer nivel con su PDF embebido (ningún byte se pierde). Solo con
`--no-aplanar-emails` + `--extraer-adjuntos` el PDF interno queda únicamente embebido en el
padre. Intencional (decisiones del plano); se documenta por si alguien dependía del
comportamiento previo.

**Prioridad.** Muy baja — ninguna observada en datos reales; ninguna implica pérdida de
prueba (a lo sumo duplicación o copia re-serializada marcada para revisión).

---

## 45. Rescate de enlaces a Drive (Parte 2): residuales tras revisión adversarial

**Contexto (2026-06-24, Parte 2 del rescate de correos).**
`core.email_export` (capa pura `extract_drive_links` + glue `_resuelve_enlaces`) descarga
byte-fieles los binarios enlazados a Drive en el cuerpo del correo. Una revisión
adversarial (3 lentes) encontró 1 HIGH + 3 MEDIUM + varios LOW/NIT; **todas se corrigieron
en el mismo commit con tests** salvo los dos residuales de abajo.

**✅ RESUELTAS en el commit:** host de descarga directa `drive.usercontent.google.com/
download?id=` clasificado (antes se perdía en silencio); filtro de firma conjuntivo §4
(`<img src>` AND imagen AND pequeña/inaccesible; las imágenes por `<a href>` nunca se
filtran como firma); `md5Checksum` ausente → se deposita con `md5_ok=False` +
`integridad="sin_md5_drive"` (transparencia forense); binario `drive_link` se clasifica por
su ubicación `_enlaces/` también en el backfill (no se reclasifica como adjunto-email); tope
anti-OOM por tamaño declarado (`_MAX_DOWNLOAD_BYTES=200 MB` → manual); `_es_eml_bytes`
endurecido (exige `Message-ID` y descarta magics binarios para no confundir `.txt`/`.csv`
con correo); `force` re-descarga un binario `_enlaces` borrado (verifica que el cache sigue
en disco); evento `upload_drive_link` idempotente (no re-emite si todo viene cacheado);
`links_resolved` no se infla en dedup de `.eml`.

**Residuales aceptados:**

**45.1 — URL de Drive hard-wrapped en `text/plain` (salto de línea real, no soft-break QP)
trunca el `file_id`.** El soft-break QP se resuelve (policy.default lo decodifica antes del
regex); pero un cliente que parte una URL larga con un `\n` literal en `text/plain` deja
`_RE_PLAIN_URL` capturando solo el prefijo del id. *No se pierde la prueba:* el id parcial va
a `get_drive_file_info` → 404 → `manual_permission` → queda en la worklist del evento
`upload_drive_link` para revisión manual. *No se aborda* porque reensamblar URLs partidas en
texto plano es heurístico y arriesgado (podría unir líneas no relacionadas). Poco frecuente
(el plano asume HTML+QP como vía principal).

**45.2 — `download_drive_media` carga el fichero entero en memoria (`r.content`).** El tope
`_MAX_DOWNLOAD_BYTES` (45.✅) ya evita el OOM rechazando binarios enormes a manual, pero los
ficheros por debajo del tope aún se materializan en RAM (y el pool `max_workers=8` puede
solapar varios). *Mejora si se materializa:* `httpx.stream('GET', …)` volcando por chunks a
un temporal con md5/sha256 incrementales, en vez de `.content`. Refactor de ~30-40 líneas;
no urgente con el tope en su sitio.

**Prioridad.** Baja — ninguna implica pérdida silenciosa de prueba (45.1 cae a worklist;
45.2 está acotada por el tope de tamaño).

---

## 46. email_atomize Fase 4 (`media-reconstruida`): residuales tras revisión final

**Contexto (2026-06-25).** Se añadió el peldaño `media-reconstruida` a `core/email_atomize`
(promueve a atom capa B propio las citas con `De:`+fecha legibles pero sin estructura DOM/`>`,
marcadas "por verificar"). Spec: `docs/superpowers/specs/2026-06-25-email-atomize-media-reconstruida-design.md`;
plan: `docs/superpowers/plans/2026-06-25-email-atomize-media-reconstruida.md`. Implementado vía
subagentes con doble revisión por tarea + revisión final holística (SHIP). Dos desviaciones TDD
ya integradas (endurecimiento de la guarda de ambigüedad multi-cabecera; `_cuerpo_sin_cabecera`
que alinea el cuerpo de la cita en texto plano con el path HTML para que dispare el dedup). Estos
residuales quedaron como follow-up no bloqueante:

**46.1 — Helper de saneado de celda Markdown (DRY).** El patrón
`(x or "").replace("|"," ").replace("\n"," ").strip()[:N]` se repite en `render.py` (cola.md
línea ~144; reconstruidos.md ext/asunto líneas ~182-183). Extraer `_celda(txt, limit=None)` para
centralizar y evitar deriva (una columna futura que olvide escapar `|` rompería la tabla).

**46.2 — `candidata` `media-reconstruida` ausente de `identidades_vigiladas.md`.** Una cita atribuida a una
identidad *candidata* (no vigilada; p.ej. `per01b@example.invalid`) se promueve y queda
`en_revision`, pero `render_revision` filtra `identidades_vigiladas.md` solo por `watched`/vigiladas, así que
no aparece en la vista probatoria. Decidir si `identidades_vigiladas.md` debe listar `watched ∪ candidatas`.
*Disparador:* un atom candidata real en W-02VND1 que haya que revisar. (Documentado en el plan.)

**46.3 — `_pasada_segmentos` siembra `body=list(anclaje)`.** Los segmentos `outlook_es`/`fwd_line`
en texto plano llevan las líneas de cabecera dentro de `seg.texto`, a diferencia del path HTML
(blockquote ya puro). `_cuerpo_sin_cabecera` lo corrige en tiempo de reconstrucción; el arreglo
limpio a largo plazo es no sembrar `body` con las etiquetas del anclaje en el segmentador plano
(elimina el re-strip downstream). Diferido: el puente actual funciona y está cubierto por tests.

**46.4 — Ramas de banner inalcanzables.** Tras la Fase 4, `"> AUTORÍA POR RECONSTRUIR — sin
verificar"` (`render.py` ~84) y el `else` de la línea `De` de lectura (~111) son inalcanzables
para todo atom acuñado (capa B solo lleva `alta-reconstruida` o `media-reconstruida`). Son
fallbacks defensivos pre-existentes; documentarlos como intencionales o añadir un assert
`confianza ∈ {alta-reconstruida, media-reconstruida}` para capa B.

**Pendiente de verificación (no es mejora, es gate §9 de la spec):** la verificación adversarial
sobre datos reales de W-02VND1 (re-ejecutar `atomize_case`, auditar cada `media-reconstruida`
contra su `.eml`, reconciliar los 36 del informe, PersonaUno/Ignacio) sigue **fuera de alcance**
hasta autorización para escribir en `G:`. El código del motor ya promueve; falta la corrida real.

**Prioridad.** Baja (46.1/46.3/46.4 son limpieza; 46.2 espera disparador).

**RESULTADO DE LA CORRIDA EN VIVO sobre W-02VND1 (2026-06-25, autorizada por Nikolai).**
`atomize_case('W-02VND1')` corrió limpio e idempotente (2 corridas → 0 cambios; `_registro.json`
estable, `mensajes_fp`=103). **Capa A byte-idéntica** (verificado contra manifiesto SHA-256 previo
de los 277). Efecto único F3→F4: **13 atoms Capa B `alta-reconstruida` mejoraron su cuerpo** —
`_cuerpo_sin_cabecera` podó la cabecera Outlook embebida en el blockquote (incl. PersonaUno
MSG-00315, etc.); contenido íntegro, solo se quitó el prefacio De:/Enviado:. **Pero 0
`media-reconstruida` promovidos.** Diagnóstico (de la propia `cola.md`, 84 no promovidos): **el
binding constraint es el PARSEO DE ANCLAJE, no la regla F4** — (a) **76 segmentos `sin_cabecera`
con remitente vacío**: el parser HTML gmail_quote/apple del motor no extrae remitente → se niega
correctamente a inventarlo (prime directive; son los "~77 headerless" del spec). La auditoría
tolerante `audit_correos_no_separados.py` **sobre-atribuyó** remitentes con regex que el motor
rechaza → su "36" era optimista (reconciliado: 7 ya eran atoms, 29 sin atom pero bloqueados aguas
arriba). (b) **6 segmentos `fwd_line` con remitente válido extraído (`per01c@example.invalid`, `per01a@example.invalid`,
`per03@example.invalid`) pero `sin_fecha`** → el único filón recuperable: si `_parse_fecha` parsease su
fecha ("Enviado el: …"), promoverían a `media-reconstruida`. **Follow-up de mayor valor (PersonaUno):
endurecer el parseo de fecha de los bloques `fwd_line` "Enviado el:"** (+ a futuro, extracción de
remitente en gmail_quote/apple para reducir los 76). Spec aparte; F4 ya está bien y no es el cuello
de botella. **Lección (otra vez): verificar SIEMPRE sobre datos reales** — la auditoría tolerante
prometió 36; el motor estricto, correctamente, promueve 0.

**✅ RESUELTO el filón de PersonaUno (F4.1, 2026-06-25, commits `ddd67e0`+`1c87d72`; spec
`2026-06-25-email-atomize-enviado-el-fix-design.md`).** Depuración sistemática: las 3 regex de
etiqueta casaban `enviado\s*:` pero Outlook ES emite **"Enviado el:"** → `_RE_LABEL` no parseaba la
fecha Y `_RE_ANYLABEL` truncaba el anclaje (Enviado/Para/Asunto se perdían tras `De:`). Fix: sufijo
opcional `(?:\s+el)?` + `enviat` (CA) en las 3 regex + `enviat` en el lookup de `_parse_label`;
aditivo, prime directive intacto, 126 tests del motor verdes. **Corrida en vivo F4.1 sobre W-02VND1:
366→372 atoms, los 6 `fwd_line` promovieron a `media-reconstruida`** (2 directos `per01a@example.invalid`
—"[PAIS_EXTRANJERO]", "CAPEX_for_His_Excellency" al [MINISTERIO_EXTRANJERO] de [PAIS_EXTRANJERO]—, 1 `per01c@example.invalid`, 3 PersonaTres); cola
84→78; Capa A byte-idéntica (0 cambiados, +6 añadidos); idempotente. Pendiente del gap aguas arriba:
los **76 `sin_cabecera`** (extracción de remitente en gmail_quote/apple) — sigue fuera de alcance.

**Iteración 1 del gap `sin_cabecera` (remitente coma) — HECHA pero 0 recuperados en W-02VND1**
(2026-06-25, spec `2026-06-25-email-atomize-remitente-coma-fix-design.md`, commit `10a022f`). Fix
correcto y blindaje válido (`_addr_o_nombre` prefiere el `<addr>` literal → robusto a "Apellido,
Nombre <addr>"; 130 tests motor verdes, Capa A byte-idéntica), **pero la corrida en vivo añadió 0
atoms**: las citas E&V bloqueadas NO tienen forma de coma en una línea. **Causa raíz real del grueso
(diagnóstico verificado):** son segmentos `html_quote` con `de=''` donde la cabecera del remitente
está **dentro del CUERPO del quote**, no en el anclaje ni al inicio: (a) atribución Apple "El <fecha>,
<Nombre> <addr> escribió:" embebida en el cuerpo; (b) "Inicio del mensaje reenviado:" + "De: … Fecha:
… CEST" (Apple Mail); (c) valores envueltos (`De:` ↵ nombre ↵ `<` ↵ email ↵ `>`). El motor solo
atribuye desde el anclaje del segmento o un bloque `De:/From:` AL INICIO del cuerpo. **Lección: medir
la FORMA de las citas bloqueadas antes de elegir el fix** (la iteración 1 se eligió sin verificar la
forma → 0 rendimiento, aunque el fix es correcto).

**Iteración 2 (body-scan de remitente) — HECHA y verificada en vivo** (2026-06-25, spec
`2026-06-25-email-atomize-bodyscan-remitente-design.md`, commits `5d01efa`+`1bdb30c`+`bcf3712`).
Diseño por workflow adversarial (3 diseños + 3 jueces); base minimal-hook + grafts. Función pura
`_atribucion_en_cuerpo` (escanea el INICIO del cuerpo: atribución Apple / bloque De: tras "Inicio
del mensaje reenviado:" / valores envueltos) con guardas G1-G5 (sin `<addr>`→cola; >1 atribución→cola;
unidad Apple con !=1 `<addr>`→cola); tope `media-reconstruida` a todo lo levantado del cuerpo.
**Dos huecos de misatribución HALLADOS por revisión adversarial y cerrados** (el `<addr>` debe ligarse
a la UNIDAD de atribución `El…escribió:`, no al primer `<addr>` del cuerpo — afectaba tanto a
`_atribucion_en_cuerpo` como al `_parse_apple` compartido del path HTML/alta, **hueco pre-existente**).
Verificación final adversarial = SHIP (27 ataques, 0 misatribución). **Corrida en vivo W-02VND1:
372→403 atoms, media-reconstruida 6→37 (+31), cola 78→43, Capa A byte-idéntica, las 89 alta intactas,
idempotente.** Recuperados: PersonaUno (6)+per01c, PersonaCuatro (11), PersonaTres (11), Marta
PersonaSeis (3), Nikolai (3), Isabel, Tecnitasa.

**CORRECCIÓN CLAVE sobre el "listado de 36" (la auditoría sobre-contaba):** reconciliado por asunto,
**la mayoría de los 36 YA EXISTÍAN como atoms Capa A** — correos directos de los consultores E&V
(Eva/Marta/Nikolai/Isabel) que REENVIABAN a PersonaUno (p.ej. "Rescisión de contrato"=MSG-00131 de=eva;
"[PAIS_EXTRANJERO] docs"=MSG-00144/5/6; "Estudio acciones penales"=MSG-00161/2/3; "Fin [PAIS_EXTRANJERO]"=MSG-00180/1/3;
"Primer ofendido"=MSG-00191/215). `audit_correos_no_separados.py` detectaba la CITA de PersonaUno dentro
y cruzaba por `(de=PersonaUno, día)` → no hallaba atom de PersonaUno ese día → falso "no separado"; pero el
PORTADOR sí es atom (de=consultor). Lo "no separado" era la autoría de PersonaUno CITADA dentro, que la
iteración 2 ahora extrae como atom propio donde hay `<addr>` verificable. Único genuinamente ausente:
"Firmada para C. & Lucas Fox" (PersonaUno 2024-11-02, solo cita, sin `<addr>` → cola).

**Iteración 3 (Gap 2 — interior reenviado + parse c′) — HECHA** (2026-06-25, spec
`2026-06-25-email-atomize-interior-reenviado-cprime-design.md`). Promueve a atom propio (capa B
`media-reconstruida`, motivo `interior_reenviado`, `en_revision`) el correo REENVIADO enterrado en el
CUERPO de un segmento ya reconstruido, acotado por marcador EXPLÍCITO (`_RE_FWD_MARK`, tolerante a
guiones/nbsp de cierre que el `_RE_FWD_INTRO` de it.2 no captaba), parseando la **forma c′** (`De:`
nombre/bare + `<addr>` envuelto) con un lookahead acotado a la franja `De:`→primera-etiqueta
(`_addr_remitente_cprime`) + poda dedicada del cuerpo (`_cuerpo_interior`). Guardas: G-MARK, G-FRANJA
(tope obligatorio), G-UNICIDAD (1 `<addr>` en la franja), G-DELEGACION, G-APILAMIENTO (1 nivel, no
recursión), G-NO-DUP-EXT (de+fecha, no de-inequality — preserva el testigo Eva-reenvía-su-propio-correo).
Diseño vía **workflow adversarial** (3 diseños × 3 jueces, todos REWORK → síntesis con grafts) +
**verificación adversarial** (2 revisores + 5 ataques sobre el motor real). **El ataque `delegacion-relay`
ROMPIÓ la atribución y se CORRIGIÓ:** `_RE_DELEGACION` solo cubría el path c′, no el inline (`De: X en
nombre de Y <relay>` afirmaba el relay) → guarda unificada sobre la franja en `_interior_reenviado` +
`p.p.`/`p.o.`/`vía` añadidos. Retirada la rama Apple del desanidado (no ocurre en el corpus; evitaba un
hueco de poda). **Solo `inline.py` + 2 tests; Capa A byte-idéntica; +26 tests, 179 `email_atomize` verdes.**
**Auditoría read-only sobre W-02VND1: 12 interiores distintos, todos con `<addr>` LITERAL, 0 inventados**
— PersonaUno ×5 (CAPEX/[PAIS_EXTRANJERO] docs/Rescisión/Estudio acciones penales/FYI), PersonaDos ×2 (Referencia
+ Acuerdo Transaccional), **Eva→Consulado [PAIS_EXTRANJERO] 7-jul "Contraoferta" (testigo MSG-00305) RECUPERADO**,
PersonaTres, Nikolai ×2, Marta. **Corrida en vivo sobre G: HECHA (2026-06-25, autorizada): 403→413 atoms,
media-reconstruida 37→47, 8 upgrades, 0 errores; Capa A 277 byte-idéntica (hash before/after), 0 fp
renumerados; idempotente (2ª corrida = 0 cambios); 12 interiores literales, 0 inventados; testigo MSG-00305
+ PersonaUno ×4 + Ignacio "Referencia" presentes en el corpus.**

**Residuales de it.3 (no bloqueantes):**
- **Duplicado cross-path (over-count, NO misatribución).** Si un correo aparece como atom `fwd_line` de
  texto plano (cuerpo Layer-B con cabecera embebida) Y como interior `html_quote` (cuerpo limpio), los
  `cuerpo_sha` difieren → 2 atoms (verificado: PersonaUno CAPEX). Ambos correctos + `en_revision`. Dedup
  cross-path exige tocar `_pase_layer_b` (pipeline) → diferido. Coherente con near-dups preexistentes de it.2.
- **Delegación del EXTERIOR/anchor** (no del interior) sigue sin filtrar — comportamiento preexistente del
  path Layer B (`_parse_apple`/`_parse_label`), fuera de alcance de it.3. Disparador: caso real con relay
  como atribución de primer nivel.
- Los ~43 restantes en cola son mayormente `sin_cabecera` sin `<addr>` (no recuperables sin inventar — prime
  directive).

---

## 47. Bug latente: colisión de slug en `raw_text/` y `MD/` (stem-only)

**✅ RESUELTO 2026-06-25.** `output_slug(rel, sha)` = `slug__SHA8` en `core/utils.py`
(usado por `extractor`, `markdown_generator` y `sala_lectura`) + `_migrate_legacy_slugs`
en `extractor` (renombra cachés viejas de stem único sin re-OCR; los colisionados se
re-extraen). 7 tests en `tests/test_extractor_slug_colision.py`. Migración del caso vivo
W-02VND1 hecha: 487 MD, 0 colisiones, **los 4 chats de WhatsApp recuperados** (3 estaban
ausentes). Detalle en `STATUS.md`.

**Síntoma (corrección).** El extractor escribe la salida como `01_Procesado/raw_text/{slug}.txt`
y el generador de markdown como `01_Procesado/MD/{slug}.md`, donde
`slug = slugify(Path(rel_path).stem)` — **solo el nombre base, sin la carpeta de origen**
([extractor.py:291](../core/extractor.py:291), [markdown_generator.py:30](../core/markdown_generator.py:30)).
En cambio, el caché de extracción `_extract_state.json` se indexa por `rel_path` completo (único).
Resultado: dos ficheros de origen distintos con el mismo *stem* (mismo nombre en carpetas distintas, o
el mismo documento espejado en `01_Drive EV/` y en `05_CRM/`) colapsan al **mismo** `{slug}.txt`/`{slug}.md`
y se **pisan en silencio**: solo sobrevive el último escrito.

**Evidencia empírica.** Reproceso de `BaRS1 - [inmueble] - (W-02VND1)` el 2026-06-25:
`_extract_state.json` registra **491 documentos** pero en disco quedan **481 `.md`/`.txt`** → 8 slugs
colisionados que afectan a 18 documentos. (Los `.eml` no colisionan porque la atomización los numera
`MSG-XXXXX`.) De las 8 colisiones, 7 son benignas (mismo documento en dos formatos `.docx`+`.pdf` /
`.html`+`.md`, o el mismo PDF duplicado entre `01_Drive EV/` y `03_Email/.../_enlaces/`: Nota simple,
Nota mercantil, Poderes PersonaTres, Poderes Jaime, Contrato honorarios, INDICE_PRUEBAS, BORME Gasteiz).

**Colisión GRAVE con pérdida de prueba — el disparador real.** Los cuatro exports de WhatsApp se llaman
`_chat.txt` (`02_Whatsapp/.../<parte>/_chat.txt`), y `slugify("_chat") == "chat"` para todos → colapsan
al **mismo `chat.md`**. En W-02VND1 son 4 conversaciones distintas y nucleares (PersonaUno, Toni
PersonaTres, PersonaOcho, PersonaSiete); **solo 1 sobrevive en la sala de lectura, las otras 3 desaparecen**. El
defecto no es teórico: hoy está ocultando prueba en un caso real. Esto lo convierte en candidato a
**promoción a `PLAN.md`** (disparador = caso real, regla de promoción del proyecto).

**Dos consecuencias, ambas de corrección.**
1. **Pérdida de datos.** El texto de un documento sobrescribe el de otro; los consumidores
   (`scorer`, `viability`, `sala_lectura`) leen `MD/` y obtienen el contenido equivocado o pierden uno.
2. **Envenenamiento del caché.** En la corrida siguiente, el doc A pasa el skip (su SHA coincide y
   `out.exists()` es `True`), pero `out` contiene el texto de B → A queda servido con el contenido de B
   de forma permanente, sin reextraer nunca.

**Mejora propuesta.** Hacer el nombre de salida libre de colisiones de forma determinista. Opción
preferida: sufijar el slug con un prefijo del SHA-256 del origen, `{slug}__{sha8}.txt` / `.md`. Es estable,
corto (esquiva el límite de 260 caracteres de ruta de Windows, a diferencia de slugificar el `rel_path`
entero) y ata la salida a la identidad del origen. Alternativa más simple: detectar colisión al escribir y
desambiguar con contador.

**Consumidores a tocar si se cambia el naming.** `sala_lectura._md_path` deriva la ruta por
`slugify(stem)` ([sala_lectura.py:244](../core/sala_lectura.py:244)) — mismo defecto, hay que alinearlo.
`scorer`/`viability` recorren `MD/` por *glob* (tolerantes al nombre, no hay que tocarlos). Hace falta una
migración puntual de las salidas ya generadas (renombrado) o aceptar una reextracción.

**Justificación de no aplicarlo ahora.** No bloquea: los ~10 documentos pisados conservan *algún* texto y
el expediente lo leen personas; el material crítico (los `.eml` atomizados) no colisiona. Pero es un bug de
corrección que conviene cerrar **antes** de apoyar análisis automatizado sobre `MD/`.

**Coste estimado.** ~15-20 líneas (helper de slug compartido en `extractor`/`markdown_generator` +
`sala_lectura`) + migración de salidas existentes + 1 test de colisión.

## 48. Motor documental unificado (split/OCR/MD) + empaquetado como conector  [PROMOVIDO → PLAN.md]

**Desarrollo completo en [`docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md`](superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md).** Entrada
paraguas que consolida el diagnóstico del flujo split/OCR/MD y fija el objetivo rector de
**empaquetar el motor como un conector reutilizable** por el despacho.

**Qué consolida (entradas relacionadas, no duplicar).** #21 (re-OCR por degradación), #24
(conversor multi-formato a MD), #39 (robustez OCR Docling/RapidOCR), #42 (OCR server-side en
`expedientes-xl`), #43 (intake sin rama de OCR), #41 (plugin de skills). Este #48 es la vista
arquitectónica única de la que esas son piezas.

**Diagnóstico (resumen; detalle y `file:line` en el doc).**
- **Incoherencias:** tres motores de OCR desacoplados con idiomas distintos (Docling interno en
  el pipeline · RapidOCR por página solo vía script manual · OCRmyPDF `spa+cat+rus` en la
  anonimización, que re-OCR-iza el original); **hueco de >30pp** (escaneados largos salen
  vacíos y se rescatan a mano); **banda muerta de umbrales** (100 en extractor vs 50 en el
  script → nadie OCR-iza los de 50–99 chars); docstring de `extractor.py` contradice el código;
  `separar.py` desenganchado del pipeline.
- **Imágenes:** tres tratos incompatibles (tirada / cola de visión / ignorada) según el módulo;
  las de iPhone (`.heic`) se caen ya en el inventario (`inventory._RELEVANT_EXTS` no las lista).
- **Faltas:** registro de cobertura por documento (la clave — hoy falla en silencio), control de
  calidad del OCR, clasificación documental, reensamblado multi-parte, PDFs protegidos/firmados,
  tablas, detección de idioma, punto de revisión humano, transcripción de audio/vídeo.

**Prerrequisitos de empaquetado.** Fachada única (`procesar_expediente(entrada, salida) → informe`),
desacople de rutas/entorno, preflight de capacidades, salida estructurada JSON, aislamiento por
subproceso, versión/modelos pinneados, sin fuga de datos + preservar `core/anon`.

**Disparador de promoción.** Decisión explícita de Nikolai de empaquetar el motor como plugin
(regla de promoción del proyecto). Tarea accionable en `PLAN.md` → `[SIGUIENTE-MOTOR-DOCUMENTAL]`.

**Ampliación 2026-07-03 (aprendizajes de Vassal Litigator).** Diseño de organización ampliado con
`github.com/strigov/vassal-litigator`: registro ÚNICO de caso estilo `index.yaml`, espejos MD que
replican la jerarquía de origen (con `mirror_stale`), y `reocr` condicional por `ocr_quality` (funde el
hueco de >30pp). Decisiones de layout: `01_Procesado/01_Sala de lectura/` (humano) + `02_Sala de máquina/`
(máquina, productos numerados) e id **dual** (`sha8` + `doc-NNN`). Ver §G/§H/§I de `docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md`.

**Ampliación 2026-07-03 (dos botones de operación).** `reorganizar_caso` (migración de casos antiguos al
layout nuevo, por flota, con sello `layout_version` + `--force` del pipeline, patrón `plan`/`apply` con
journal reversible) y `rebuild_plugin` (repackage mecánico de skills/conectores + señalización semántica de
skills con prosa afectada + hook de drift no-silencioso). Ver §J/§K de `docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md`.

**Decisiones estratégicas + principios (2026-07-04).** (1) plugin-first (Streamlit parqueado, distribución
vía plugin); (2) Ollama/LLM local descartado → motor OCR **OCRmyPDF + `ocr_per_page` torch** como reocr;
(3) regla PII relajada temporalmente, anonimización resecuenciada al **último eslabón** con **gate de
reinstauración del muro `06`**. Además **9 principios rectores de ejecución** (M1–M9): golden fixture,
registro-primero, walking skeleton, fachada, `00_Input` intocable, medir-antes, Preview→Apply, preflight y
doctor de dependencias. Roadmap resecuenciado F(-1)→F-final. Ver §L/§M de `docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md`.

**Motor en dos cajas + MinerU (2026-07-04).** El motor vive tras la junta (registro+`ocr_quality`), así que es
decisión **aplazada e intercambiable**: Caja 1 (PDF buscable) = OCRmyPDF fijado; Caja 2 (extractor→MD) =
bake-off en F3 con **MinerU** (opendatalab, local/CPU/determinista, tablas+manuscrito, sin PII) como favorito
frente a Docling, con gate hardware/catalán/licencia. Si MinerU cumple, elimina la necesidad de Claude visión. Ver §F.

**Estudio de mercado 2026 + aparcado (2026-07-04).** No hay turnkey que cumpla RGPD-local + es/ca/ru +
presupuesto. Corrección de licencia: **Docling (MIT)** por defecto sobre MinerU (AGPL-3.0) para el
extractor→MD. Añadida **opción Mistral OCR cloud (UE) + ZDR + DPA** como motor de la fase de construcción
(coste irrelevante ~$1-2/1.000; el punto es RGPD del crudo). Cola dura (manuscrito) → Azure contenedor
desconectado / Mistral self-host, post-anonimización. **Este plan queda APARCADO**; foco actual: skills con
código (`ocr-a-md` sobre el scaffold). Ver §F de `docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md`.

**Justificación de no aplicarlo ahora.** Es un refactor arquitectónico grande; primero se
memoriza el diseño. El orden sugerido de ejecución (saneamiento barato → registro de cobertura →
fachada → motor OCR único → conector → resto de faltas) está en el doc.

**Anotación 2026-07-23 (W-02VND1).** Medido en vivo durante el intake de la querella penal del
caso: `sala_maquina apply` sobre un `00_Input/` de 2,6 GB/715 ficheros tardó varios minutos para
depositar solo 43 PDFs nuevos. Dos causas concretas, verificadas en código: `core/sala_maquina.py::
inventariar()` rehashea `00_Input/` entero en cada corrida en vez de leer `00_Input/_intake_hashes.json`
(`core/intake_manifest.py::IntakeManifest`, ya poblado por la mayoría de fuentes — `core/intake_drive.py`
es la excepción, no registra en él); y ~169 documentos no resueltos desde una corrida anterior se
reintentan (con OCR real) en cada `apply` sin límite (detalle en #84). Confirma en código el "registro
ÚNICO de caso" que este #48 ya diseñaba (ampliación 2026-07-03) y que sigue aparcado. La misma carencia
apareció el mismo día, independientemente, en la revisión adversarial de
`docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md` (hallazgo P0.1:
`corpus.jsonl` de `email_atomize` tampoco reconcilia contra el inventario real de `00_Input`). No
promuevo — solo dejo la evidencia para cuando se decida desaparcar.
---

## 85. Endurecimiento del robot CENDOJ (`cendoj-descarga`)

> *Renumerada el 2026-07-26 (D4 de la revisión adversarial de gobernanza). Nació como `#48`,
> número que ya ocupaba el **motor documental** (arriba, `:1700`): la colisión rompía la llave
> `MEJORAS #NN` que exige la regla de promoción de `CLAUDE.md`, y `Ctrl+F "## 48"` caía aquí.
> Se renumeró esta (6 refs, todas internas al fichero) y no el motor documental, que está
> anclado en `CLAUDE.md:220` y `PLAN.md`. Referencias antiguas a «#48.A–D» son de esta entrada;
> las que hablen de motor documental / registro único de caso son del `#48` real.*

**Disparador.** Petición de Nikolai (2026-06-30) de mejorar el robot de búsqueda
en CENDOJ; rama dedicada `claude/cendoj-search-robot-yt67sz`. Se registran como
backlog cuatro sub-frentes con disparador propio; cada uno es promovible a
`PLAN.md` por separado (referencia `MEJORAS #85.X`). El techo del **CAPTCHA**
«Control > Descargas masivas» es estructural (política anti-bot, no se resuelve);
ninguna mejora lo elimina, solo reducen el volumen de descargas que lo dispara y
mejoran la recuperación cuando aparece.

Estado de partida: skill `cendoj-descarga` v1.1 (`SKILL.md` como manual operativo)
+ subagente `cendoj-bot.md` (model sonnet) + 7 helpers en `scripts/`. Todo sobre
`mcp__Claude_in_Chrome` (el sandbox bash no alcanza `poderjudicial.es`).

### 85.A — Sustituir clics por coordenadas fijas por selectores/JS (robustez)

**Síntoma.** El flujo navega por **coordenadas absolutas**: cierre del modal de
aviso legal (`coord. ≈ 1002, 47`, [SKILL.md:50](../.claude/skills/cendoj-descarga/SKILL.md))
y apertura del desplegable jerárquico `Localización` (`coord. ≈ 550-890, 357`,
[SKILL.md:64-68](../.claude/skills/cendoj-descarga/SKILL.md)). Cualquier cambio de
resolución, zoom del navegador o reflow del layout de CENDOJ desplaza el objetivo y
el clic cae en vacío o en el control equivocado — **fallo silencioso**: el robot
sigue como si hubiera filtrado por provincia cuando no lo ha hecho, y devuelve
resultados de toda España. El botón `Buscar` ya se migró a
`document.querySelector('button[type="submit"]').click()`
([SKILL.md:74-78](../.claude/skills/cendoj-descarga/SKILL.md)); el modal y el
dropdown siguen por coordenadas.

**Mejora propuesta.** Reescribir cierre de modal y selección de localización/sección
con localizadores estables por DOM (`querySelector` sobre `id`/`name`/texto del
`label`, `.click()` sobre el checkbox de la provincia, expandir CCAA por el nodo del
árbol que contiene el texto). Patrón ya validado en el submit. Documentar en el
manual la regla general «cero coordenadas para acciones de formulario; coordenadas
solo como último recurso para el gesto de user-activation previo a la descarga»
(ese clic neutro en viewport, [SKILL.md:144](../.claude/skills/cendoj-descarga/SKILL.md),
sí debe seguir siendo posicional). Añadir verificación post-condición: tras filtrar,
leer por JS el estado del checkbox/campo y abortar con mensaje claro si no quedó
aplicado, en vez de continuar a ciegas.

**Coste estimado.** Edición de `SKILL.md` (Pasos 2-3) + snippets JS; sin código
Python. El subagente ejecuta JS, no hay test automatizable salvo en sesión real.

> **Posiblemente superado por #49 (vía Apify):** si se adopta el actor `legaltech/cendoj`,
> desaparece el navegador y, con él, los clics por coordenadas — esta entrada quedaría sin objeto.

### 85.B — Discriminar candidatos por JS del listado, sin abrir PDFs

**Síntoma.** Cuando hay varios resultados con la misma fecha, el Paso 5
([SKILL.md:111-119](../.claude/skills/cendoj-descarga/SKILL.md)) propone *abrir cada
PDF* para leer hechos/ratio (caro, lento y **dispara el CAPTCHA** porque consume
descargas) o relanzar una búsqueda de texto libre. Pero la propia página de
resultados ya muestra en el listado, bajo cada ROJ, los metadatos discriminantes:
`ECLI`, `Nº Resolución`, `Ponente`, `Nº Recurso`.

**Mejora propuesta.** Extender el JS de extracción (hoy solo captura `roj` + `href`,
[SKILL.md:103-107](../.claude/skills/cendoj-descarga/SKILL.md)) para que recoja
también ese bloque de metadatos por resultado, y casarlo programáticamente contra el
*lead* (la referencia privada) por ECLI > Nº Recurso > Nº Res + Ponente, antes de
descargar nada. Solo se baja el hash que casa. Reduce descargas (→ menos CAPTCHA),
elimina la apertura especulativa de PDFs y deja traza del criterio de match. Mantener
la apertura del PDF únicamente como desempate final cuando el listado no basta.

**Coste estimado.** Edición de `SKILL.md` (Pasos 4-5) con el JS ampliado; sin Python.

> **Posiblemente superado por #49 (vía Apify):** el dataset del actor ya trae
> `roj`/`ecli`/`resolutionNumber`/`appealNumber`/`summary` por resultado, lista la discriminación
> sin scrapear el listado a mano (con el matiz de que `ponente` llega anonimizado a iniciales).

### 85.C — Verificación automatizada metadatos-vs-lead (helper nuevo)

**Síntoma.** La verificación (Paso 8, [SKILL.md:211-239](../.claude/skills/cendoj-descarga/SKILL.md))
es `pdftotext | grep` **a ojo**: el operador compara mentalmente ROJ/ECLI/Nº Res/
Ponente del PDF contra lo pedido. Es el paso donde se cuela el error «parece la
buena y no lo es», precisamente el que rompe el rigor de cita en un escrito
procesal. Además choca con el encoding CIDFont (ver 85.D), que vacía el `grep`.

**Mejora propuesta.** Helper nuevo `scripts/verificar_sentencia.py` que reciba la
referencia esperada (ROJ/ECLI/Nº Res/fecha/ponente) y el PDF descargado, parsee el
**bloque de cabecera de metadatos** que CENDOJ imprime en la primera página (es texto
seleccionable aunque el cuerpo sea CIDFont) y emita un informe por campo:
`PASS` / `FAIL` / `DIVERGENCIA` (esta última para el caso legítimo ROJ-año ≠ Nº-res-año,
[SKILL.md:230](../.claude/skills/cendoj-descarga/SKILL.md), que se reconcilia por ECLI
y se documenta, no se «corrige»). Reutiliza el parser de cabecera de
`parse_pdf_to_md.py`. Salida apta para volcar al consolidado (Paso 9) y al ledger
(85.D). No sustituye la lectura humana de hechos+ratio (Paso 5 / nota
[SKILL.md:373](../.claude/skills/cendoj-descarga/SKILL.md)): verifica **identidad**,
no idoneidad temática.

**Coste estimado.** ~80-120 líneas Python + tests con PDFs de muestra (los ya
presentes en `oposicion-alegacion-nulidad/references/jurisprudencia/`) + edición del
Paso 8 del manual para invocarlo.

> **Referencia de diseño (2026-06-30):** `ricardodevis/verificador-legal` (Apache-2.0,
> plugin Cowork / Claude Managed Agents) implementa justo este patrón a mayor escala:
> auditor multi-agente que verifica ECLI/ROJ/ponente/fecha contra fuentes oficiales,
> **detecta alucinaciones** (fecha imposible, ponente que no consta en nóminas públicas)
> y **valida la cita literal entrecomillada** contra el texto oficial. No es drop-in
> (la descarga de PDF figura como roadmap v2.0) pero es el modelo conceptual de 85.C y
> encaja con `verificacion-anclada-fuente`. Estudiarlo al construir el helper.

### 85.D — OCR fallback ante CIDFont + ledger de lote reanudable

**Síntoma (dos partes).**
1. **CIDFont.** `pdftotext` devuelve 0 coincidencias con el encoding propio de CENDOJ
   ([SKILL.md:224](../.claude/skills/cendoj-descarga/SKILL.md)); el manual sugiere OCR
   «opcionalmente» pero `batch_pdf_to_md.sh` no lo aplica solo, así que la conversión
   a `.md` y el `grep` de materia quedan vacíos sin aviso accionable.
2. **Sin estado de lote.** Las referencias entran como texto libre y no hay *ledger*
   de progreso. Si el CAPTCHA corta a mitad de un lote de 15 (Paso 6-bis,
   [SKILL.md:149-156](../.claude/skills/cendoj-descarga/SKILL.md)), se pierde el rastro
   de qué quedó localizado/descargado/pendiente; al reanudar se re-trabaja a mano.

> **Intel externa (2026-06-30, no verificada por nosotros):** el README de
> `DerechoVirtual/mcp-cendoj-sentencias` (MIT) afirma que el control «Descargas masivas»
> del CENDOJ es **por sesión (no por IP) y salta sobre la 6.ª-7.ª descarga**. Si se
> confirma en sesión real, afina la regla de ritmo: mantener **≤5 descargas por sesión**
> y, llegado el límite, abrir sesión nueva (no esperar) reinicia el contador. ⚠️ Ese
> repo logra «sin CAPTCHA» con **multi-sesión paralela + tool `resolver_captcha()`** —
> evasión que el despacho **NO adopta** (política anti-bot, [SKILL.md:153](../.claude/skills/cendoj-descarga/SKILL.md));
> aquí solo se aprovecha el dato del umbral para espaciar mejor, no para esquivar.

**Mejora propuesta.**
1. En `batch_pdf_to_md.sh`: detectar texto vacío/ilegible tras `pdftotext` y disparar
   automáticamente OCR (`ocrmypdf` o `pdftoppm` + Tesseract, ya en el entorno) sobre
   copia temporal antes de `parse_pdf_to_md.py`; marcar en el `.md` si el contenido
   proviene de OCR. (Relacionado con #1 y #39, mismo patrón de OCR-bajo-demanda.)
2. Un *ledger* JSON por encargo (`_cendoj_lote.json`): una fila por referencia con
   estado (`pendiente`/`localizada`/`descargada`/`verificada`/`no_localizada`), ROJ/ECLI
   resueltos y ruta del PDF. El subagente lo escribe incrementalmente; al reanudar tras
   CAPTCHA, retoma solo las `pendiente`. Conecta con la telemetría existente
   (`registrar_uso.py`) y con el consolidado (Paso 9).

**Coste estimado.** ~15 líneas en `batch_pdf_to_md.sh` (rama OCR) + ~60-80 líneas para
el ledger + edición de Pasos 6-bis/8-bis/9 del manual. Idempotencia: el ledger nunca
re-descarga lo ya `verificado`.

**Justificación de no aplicarlo ahora (toda la #85).** Decisión de Nikolai (2026-06-30):
en esta sesión solo se documenta el backlog; la implementación se aborda después,
priorizando 85.A y 85.B (mayor retorno: matan fallos silenciosos y bajan el volumen
que dispara el CAPTCHA) y luego 85.C (blinda el rigor de cita). 85.D es el de menor
urgencia salvo que un encargo grande haga del CAPTCHA un cuello real.

> **Actualización 2026-06-30:** investigado el actor de Apify `legaltech/cendoj` (ver
> #49). Pasa la prueba decisiva (devuelve la URL del PDF **oficial** del CGPJ). Si se
> adopta, **supera 85.A y 85.B** y reordena la prioridad: la vía Apify pasa a ser el
> descubrimiento primario y el navegador queda como fallback. 85.C y 85.D siguen vigentes.

---

## 49. Vía Apify MCP (`legaltech/cendoj`) como capa de descubrimiento del robot CENDOJ

**Disparador.** Nikolai aporta (2026-06-30) el actor de Apify `legaltech/cendoj` (vía
MCP) como alternativa a la navegación real, a raíz de un tutorial de
legaltechnologybootcamp. Investigada su ficha técnica (Input/Output/Pricing): **pasa la
prueba decisiva** — devuelve la URL del **PDF oficial del CGPJ**, no un sustituto
scrapeado — y reconfigura los frentes #85.A/B.

**Qué es.** Actor de Apify (MCP `https://mcp.apify.com/`) que automatiza la búsqueda en
CENDOJ server-side y devuelve un dataset JSON estructurado. Mantenedor de comunidad
(Miguel González); muy activo (modificado pocas horas antes de la consulta); 157
usuarios totales, 9 activos/mes; máx. **200 resultados** y **4 términos** por
ejecución. **Coste de dos vectores**: `$1.00 / 1.000 resultados` de búsqueda **+ proxy
residencial ES facturado por GB** al extraer texto (CENDOJ bloquea las IP de datacenter,
así que el proxy residencial no es opcional). Forma parte de una familia legaltech
(`tribunal-constitucional`, `tjue`, `aepd`).

**Lo que resuelve (y por qué cambia #48).**
- **Input estructurado**: `searchTerms` con booleanos `AND/OR/NOT/NEARn` (sintaxis EN o
  CENDOJ, traducción automática) + filtros `jurisdictions`, `organoTypes` (códigos
  opacos, p. ej. `11`=Sala Civil TS, `37`=AP, `42`=JPI; la ficha trae **tabla de
  referencia completa**), `resolutionTypes`, `locations`, `dateFrom/dateTo`,
  `sortOrder`, `maxResults`. → **Obsoleta 85.A** (cero navegador, cero coordenadas) y
  supera la cascada de texto libre del manual actual.
- **Output por resolución**: `roj`, `ecli`, `resolutionNumber`, `appealNumber`,
  `municipality`, `organo`, `resolutionDateISO`, `summary`, **`pdfUrl` (PDF oficial del
  CGPJ, `action=contentpdf`)** y `documentUrl` (visor estable `openDocument`, sin `&`).
  → **Resuelve 85.B**: discriminación por metadatos casables (ECLI/ROJ/Nº recurso/Nº
  res) sin abrir PDFs.
- **Extracción de texto bajo demanda** en 2.ª ejecución (`pdfUrls`, máx. 50) para
  leer/analizar sin descarga manual. El actor **respeta el no-descarga-masiva** del
  CGPJ (solo metadatos + texto selectivo).
- **Modo párrafos** (`paragraphs` 1-20 + `paragraphTerms`): en vez del texto íntegro,
  devuelve solo N pasajes relevantes priorizando los **Fundamentos de Derecho**. Pensado
  para análisis con LLM con menos tokens; encaja con el triaje y la lectura inicial del
  despacho (no sustituye la lectura del PDF oficial para citar).

**Caveats que NO desaparecen (rigor del despacho).**
1. **El artefacto de cita sigue siendo el PDF oficial.** Se usa `pdfUrl` para bajar el
   PDF del CGPJ y se mantienen la verificación (Paso 8) y el archivado en expediente
   (Pasos 7/7-bis). El `summary` y el `text` del actor son ayudas de descubrimiento,
   **no** fuente de cita.
2. **Anonimización forzada del actor.** El campo `ponente` llega como iniciales
   («P.J.V.T.») y el `text` extraído anonimiza ponente/letrados/procuradores —**más**
   que el propio PDF del CGPJ. Consecuencia: el `ponente` deja de ser clave de
   discriminación fiable (usar ECLI/ROJ/Nº recurso/Nº res, que sí llegan completos); y
   el `text` no sirve para citar literal (para eso, el PDF oficial vía `pdfUrl`).
3. **CAPTCHA no eliminado, pero mitigado.** La búsqueda no descarga; al bajar los PDFs
   oficiales al expediente sigues ante el muro anti-bot, pero con el `pdfUrl`/ROJ
   exactos bajas muchos menos y más certeros → menos CAPTCHA. Para muchos análisis, el
   `text` (máx. 50) evita descargar.
4. **Dependencia de terceros / bus factor.** Mantenedor único de comunidad, 9 usuarios
   activos/mes. Conservar el robot de navegador (skill actual) como **fallback** si el
   actor cae o cambia su API.
5. **Deontológico + coste de proxy.** CENDOJ bloquea las IP de datacenter, así que el
   actor scrapea por **proxy residencial ES obligatorio**, facturado por GB. Mitiga que
   devuelve URLs oficiales y respeta el no-masivo, pero es una decisión consciente del
   despacho (no un detalle técnico) y añade un coste por GB al precio por resultado.
6. **Gotcha MCP `&amp;`.** El `pdfUrl` llega con los `&` escapados al leerlo por MCP;
   para enlaces clicables usar `documentUrl`; para reenviar a `pdfUrls`, pasar el
   `pdfUrl` tal cual (el actor lo decodifica).
7. **Encaje organizativo.** Es capacidad de **Cowork/claude.ai** (la investigación
   CENDOJ es tarea Cowork por `CLAUDE.md`, y el conector MCP de Apify vive server-side),
   no de Claude Code local. El token personal de Apify se gestiona **fuera del repo y
   fuera del chat** (regla de secretos del proyecto).

**Relación con #85.** Si se adopta: **85.A y 85.B quedan superados** (no hay navegador
que endurecer; la discriminación viene en el dataset). **85.C gana valor**: el «lead»
puede ser la propia salida del actor y la verificación contrasta el PDF oficial contra
ROJ/ECLI/Nº recurso ya estructurados. **85.D sigue aplicando** a los PDFs que se bajen
y al estado del lote. El robot pasa de «navegador frágil» a **híbrido: descubrimiento
por actor → descarga + verificación del PDF oficial → archivado en expediente**.

**Convergencia de diseño (señal a favor).** Un servidor MCP independiente,
`DerechoVirtual/mcp-cendoj-sentencias` (MIT), expone tools (`buscar_por_cita` por
ECLI/ROJ, `leer_sentencias` con `parrafos`/`terminos`/`guardar_pdf`) que **coinciden en
forma** con el Input/Output del actor de Apify y con el modo párrafos — dos
implementaciones distintas llegando al mismo diseño refuerza que es la forma correcta.
Diferencia clave: ese MCP «resuelve» el CAPTCHA (multi-sesión + tool `resolver_captcha`),
vía que el despacho **descarta**; el actor de Apify respeta el no-descarga-masiva, así
que está **mejor alineado** con la política del despacho que el MCP más capaz del topic.

**Coste estimado.** Sin código Python nuevo de búsqueda (lo hace el actor). Trabajo:
(a) configurar el conector MCP de Apify en Cowork (token personal); (b) reescribir
Pasos 2-5 de `cendoj-descarga/SKILL.md` (vía Apify primaria + navegador como fallback)
e incorporar al manual la tabla de `organoTypes` y la guía de operadores booleanos;
(c) dejar intactos los Pasos 7-8 (descarga oficial + verificación + archivado).

**Justificación de no aplicarlo ahora.** Sesión de solo-propuesta. Antes de integrar:
(1) **decisión deontológica explícita** de Nikolai sobre el proxy residencial; (2)
**prueba real en Cowork** de 1-2 consultas de un caso vivo comparando actor vs.
navegador (cobertura, exactitud de metadatos, que el `pdfUrl` baje el PDF oficial
correcto); (3) confirmar la gestión del token Apify. Promovible a `PLAN.md` cuando esas
tres se cierren.

## 50. Sección "Relación con el ecosistema" en TODAS las skills del despacho (grafo único + generación)

**Disparador.** Decisión de Nikolai (2026-07-09), a raíz del spec de `abrir-caso`
(`docs/superpowers/specs/2026-07-09-abrir-caso-design.md`), que estrena una sección
"Relación con el ecosistema de skills" (posición en el flujo, solapes, infra compartida,
handoff sugerido). Nikolai quiere que **todas** las skills del flujo la tengan.

**Problema que ataca.** Hoy la relación entre skills es tácita → solapes confusos
(el caso vivo: `intake-expediente` vs `abrir-caso`) y handoffs que Claude no ve. Pero
escribir esa sección **a mano en cada `SKILL.md`** es una trampa de drift: relaciones
bidireccionales copiadas en N ficheros = N sitios que envejecen — justo lo que combate
`docs/GOBERNANZA_FUENTES_VERDAD.md` ("un hecho, un hogar").

**Propuesta (robusta + eficiente) — grafo único + secciones generadas.** Reutiliza el
patrón que el repo ya tiene para el drift de helpers (`sync_skill_helpers.py`) y de
taxonomía (`test_gobernanza_taxonomia.py`):

1. **SSOT del grafo:** `docs/ecosistema_skills.yaml` (o bloque estructurado en
   `docs/ARQUITECTURA_RELACIONES.md`). Cada skill declara **solo sus aristas salientes**:
   `precede`, `solapa_con`, `comparte_infra`, `delega_en`. El inverso (`sigue_a`) lo
   **deriva el generador** — nunca se escribe dos veces.
2. **Generador** `scripts/sync_skill_ecosistema.py` (gemelo de `sync_skill_helpers.py`):
   inyecta un bloque `## Relación con el ecosistema` en cada `SKILL.md` entre centinelas
   `<!-- ECOSISTEMA:START/END -->`, idempotente y byte-estable (aristas ordenadas); las
   ediciones fuera del bloque sobreviven.
3. **Guardarraíl** `--check` + test `tests/test_skill_ecosistema_sync.py`, cableado a
   pre-commit/CI (como el drift de helpers). Se salta si no hay grafo (como el guard de PII).
4. **Plantilla:** añadir el bloque-centinela a `_plantilla-skill` → las skills nuevas lo
   heredan por defecto (encaja con el `requires` de estilo/verificación).
5. **Bonus:** el generador puede renderizar un Mermaid del grafo entero para
   `ARQUITECTURA_RELACIONES.md`.

**Por qué embebido y no referencia.** El bloque va **dentro** del `SKILL.md` (no un enlace
al doc del repo) para que viaje dentro del `.skill` a Cowork, donde no hay repo en runtime.

**Alcance (eficiencia).** El grafo cubre las skills del **flujo del despacho** (abrir-caso,
organizar-sala-máquina, organizar-sala-lectura, triaje-viabilidad, viabilidad-prerelleno,
preparacion-litigio-civil, escritos-judiciales, preparacion-audiencia-previa,
preparacion-juicio-oral, oposicion-alegacion-nulidad, contestacion-honorarios-art20-lau).
Las utilidades transversales (`docx`, `pdf`, `xlsx`, `cendoj-descarga`, `pase-de-estilo`,
`verificacion-anclada-fuente`) llevan a lo sumo una etiqueta "utilidad transversal" o
quedan fuera — no forzar aristas donde no las hay.

**Orden de trabajo (otra sesión).** (1) esquema de nodo cerrado → (2) `ecosistema_skills.yaml`
→ (3) generador + `--check` → (4) bloque en `_plantilla-skill` → (5) guard + wiring
pre-commit/CI + AVISO en `validate_skills` → (6) regenerar workflow-skills + Mermaid → (7)
re-empaquetar los `.skill`. **Promovible a `PLAN.md`** por decisión de Nikolai (ya hay
disparador); pendiente solo de agendar la sesión.

**Actualización 2026-07-18 (taxonomía de `rol` ampliada — arreglo acotado).** Al re-empaquetar
las skills de `MEJORAS #54`, el validador (`validate_skills._ROLES`) rechazaba `rol: input`
(usado por `intake-expediente`/`exportar-correos-etiqueta`, fuera de la lista) y `output` estaba
sobrecargado (denotaba tanto entregables jurídicos como artefactos internos de procesado).
Decisión de Nikolai: se añadieron los roles **`input`** (entrada de datos crudos, simétrico de
`output`) y **`procesado`** (transforma el intake en artefactos internos), y se reclasificaron
`organizar-sala-maquina`/`organizar-sala-lectura` de `output`→`procesado` (red anti-regresión en
`tests/test_validate_skills_roles.py`). **Al construir este grafo, la taxonomía de `rol` se
revalida con las 18 skills delante** (posible eje `familia` datos/jurídico y rol `analisis` para
triaje/viabilidad); no se rediseñó ahora para no fijar el modelo sin su consumidor.

## 51. Bug latente: `download_file_content` devuelve el mime de origen tras exportar un Doc nativo

**Descubierto 2026-07-10** durante el mapeo del ecosistema para la (aparcada) F3 de
`google-despacho`; independiente de F3.

**Síntoma.** `plugins/google_despacho_mcp/drive_ops.py` (`download_file_content`, línea ~209)
devuelve `"mime_type": mime` donde `mime` es el `mimeType` de **origen** (p. ej.
`application/vnd.google-apps.document`). Cuando el fichero es un Doc nativo y se ha **exportado**
(a PDF por defecto, o a Office con `keep_editable`), el campo devuelto NO refleja el artefacto
realmente escrito (que es `application/pdf` o el Office correspondiente). Además la función escribe
en `dest_path` tal cual, sin añadir la extensión del formato exportado.

**Impacto hoy.** Latente: el único consumidor que se habría fiado de ese campo era el
`import_drive_folder` de F3, que quedó **APARCADO** (spec §14, PR #27). Ningún flujo vivo lo
consume mal ahora. El `sha256` que devuelve la función SÍ es correcto (se calcula sobre los bytes
escritos).

**Fix propuesto (~2 líneas + test).** Cuando `mime` es nativo (`GOOGLE_NATIVE_PREFIX`), devolver el
`export_mime` efectivo (derivado de `_EXPORT_PDF`/`_EXPORT_OFFICE` según `keep_editable`) en lugar
del nativo; opcionalmente ajustar la extensión de `dest_path` con `_EXPORT_EXT`. Test: exportar un
Doc nativo fake y asertar `mime_type == "application/pdf"` (y `.docx` con `keep_editable`).

**Disparador de promoción.** Que cualquier consumidor nuevo (reapertura de F3, o un flujo que
descargue Docs nativos y ramifique por `mime_type`) lo necesite. Hasta entonces, backlog.

---

## 52. Validar/refrescar enums hardcodeados del CRM contra `/api/view/enums/{el}/{prop}`

**Anotado 2026-07-12** desde el handoff de El Contable (descubrimiento del endpoint de enums).
Referencia: `docs/INTEGRACION_SUDESPACHO.md` §14.4.

**Contexto.** sudespacho expone el descubrimiento de valores de enum por API:
`GET /api/view/enums/{elemento}/{propiedad}` → `{enums:[{id,label}]}` (verificado 2026-07-12, p. ej.
`/api/view/enums/facturas_recibidas/tipo_operaciones_iva`). Hoy el cliente REST del repo lleva varios
enums **hardcodeados** — códigos de posición procesal (`POSICION_*`), IDs de tags, y en el ecosistema
contable listas como `facturas_estado_cobro` / `forma_pago` / `tipo_operaciones_iva`.

**Mejora.** Sustituir/validar esos enums contra el endpoint al arrancar (con caché por proceso), en
lugar de fiarlo a constantes que se desincronizan si el CRM cambia. Detecta drift (código nuevo,
label renombrado) sin re-capturar HAR.

**Justificación de no aplicarlo ahora.** Los enums hardcodeados que usa FeesDefender (posición
procesal, tags) son estables y no han dado problemas; el valor del refresco dinámico es sobre todo
para la rama contable (El Contable), que vive en otro repo. Regla del repo: promover solo con
**disparador concreto** (un caso real que falle por enum desincronizado, o decisión de Nikolai). Hasta
entonces, backlog.

**Disparador de promoción.** Un fallo real por enum obsoleto en algún flujo del CRM de FeesDefender, o
que se decida unificar el cliente REST con el de El Contable.

---

## 53. Fuente `entrevista` en `abrir-caso` (→ `06_Entrevistas`), con formato de notas configurable

**Anotado 2026-07-13** durante el intake real del caso W-02XOR7 (Santes Creus 15). Al depositar la
**grabación de la call de estudio de viabilidad** (mp4 de Meet) + su doc de notas/transcripción de
Gemini, no había ruta soportada para llevarlos a `06_Entrevistas`: acabaron en `04_Manual`.

**Gap.** El CLI `scripts/abrir_caso.py` solo expone `_FUENTES_CLI = (drive_ev, manual, whatsapp,
email)`, y cada fuente escribe en una subcarpeta fija (`brain.FUENTE_A_SUBDIR`): `manual → 04_Manual`.
`06_Entrevistas` existe en el esqueleto (`CASO_SUBDIRS`) pero **ninguna fuente de intake escribe ahí**.
La fuente `entrevista` se **excluyó a propósito** en la F3 de abrir-caso (parte judicial aparcada). Hoy,
para material de entrevista/call con custodia forense (`_intake_log` + SHA-256), el único camino es
`--fuente manual`, cableado a `04_Manual`; colocarlo a mano en `06_Entrevistas` pierde la custodia.

**Mejora propuesta.** Añadir `--fuente entrevista` a `abrir-caso` (espejo del camino `manual`, con
destino `06_Entrevistas` vía `FUENTE_A_SUBDIR["entrevista"] = "06_Entrevistas"` + evento de intake
propio). Acepta carpeta o fichero (grabación + notas + transcripción juntos). **Formato de notas
configurable** al depositar un Doc nativo de Google: por defecto **texto/Markdown** (vía
`read_file_content`, mejor para el pipeline LLM / sala de máquina) con opción a `.pdf`/`.docx`
(`download_file_content` con/sin `keep_editable`); hoy el default de `download_file_content` es PDF y por
eso las notas salieron en PDF. Considerar sub-roles dentro de `06_Entrevistas` (p. ej. audio/vídeo vs
notas/transcripción) análogos a los roles de `--fuente whatsapp`.

**Justificación de no aplicarlo ahora.** Un solo caso lo ha necesitado; `04_Manual` no rompe nada (el
pipeline aguas abajo lee todas las fuentes). Regla del repo: promover solo con **disparador concreto**.

**Disparador de promoción.** Recurrencia de intake de grabaciones/entrevistas de viabilidad (varios
casos), o la reapertura de la parte de abrir-caso que tenía `entrevista` aparcada.

---

## 54. Modelo de layout de `00_Input`: subcarpeta por lote de intake + metadatos, vs cajones fijos por fuente  [DECIDIDO 2026-07-17 → spec rev 2 en PR #49 mergeado] [PROMOVIDO → PLAN.md 2026-07-17]

**Anotado 2026-07-13** a raíz del intake del W-02XOR7 (Santes Creus 15). El material llegó por **tres
canales a la vez** (etiqueta de Gmail + carpetas del Drive de EV + grabación en Meet) y hubo fricción de
clasificación: los WhatsApp y los correos de las partes venían **dentro** del pull del Drive → cayeron en
`01_Drive EV`, no en `02_Whatsapp`/`03_Email`; la grabación fue a `04_Manual` por no haber ruta a
`06_Entrevistas` (ver #53).

**Diagnóstico.** Hoy `00_Input` codifica **procedencia** (canal) en el árbol con 6 cajones fijos
(`01_Drive EV`…`06_Entrevistas`, `config.CASO_SUBDIRS`), y mezcla implícitamente el eje de **tipo de
contenido**. En realidad hay **tres ejes ortogonales** —procedencia (canal), tipo (WhatsApp/email/PDF/
grabación) y lote de entrega (quién/cuándo)— y un único árbol solo puede codificar uno limpio; los otros
dos deben vivir en **metadatos**. De ahí la fricción.

**Propuesta de Nikolai.** No imponer scaffolding canónico en `00_Input`: **cada intake = su propia
subcarpeta** (por evento de entrega), conservando la estructura tal cual llega.

**Dos modelos candidatos:**

- **A (subcarpeta por lote + manifiesto).** Layout físico = una subcarpeta por evento de intake
  (`00_Input/<fecha>_<fuente>_<lote>/…` verbatim); **procedencia y tipo pasan a metadatos** en un
  `_manifiesto` por lote y/o en `_intake_log.jsonl`. Las herramientas filtran por **metadato, no por
  ruta**. Ventajas: fidelidad (nada se fuerza a un cajón), forense (cada carpeta autodescribe una
  entrega, encaja con el modelo de eventos del `_intake_log`), append-only (un intake nunca pisa otro).
- **B (mantener cajones, enrutar por tipo en el ingest).** Se conservan los 6 cajones pero el ingest
  **normaliza por tipo**: un export de WhatsApp siempre va a `02_Whatsapp` aunque venga por Drive, etc.
  Arregla la misclasificación sin tocar a los consumidores, a costa de routing content-aware en la
  entrada (y de "romper" carpetas de origen que venían agrupadas, p. ej. `_DEMANDA/` del Drive).

**Coste del modelo A (consumidores a migrar).** El layout fijo está cableado en: `scripts/abrir_caso.py`
+ `core.abrir_caso.FUENTE_A_SUBDIR`; `core.whatsapp_intake` (roles bajo `02_Whatsapp`,
`config.WHATSAPP_SUBDIRS`); `core.email_export` (dest `03_Email`); `core.intake_drive`
(`_DRIVE_EV_INPUT_SUBDIR`); `core.case_manager.dir_intake` + **guard §6 de checkout/checkin**;
`config.CASO_SUBDIRS`; y la skill `organizar-sala-lectura` (aunque ya lee todo `00_Input`). Pasar a lotes
libres obliga a que todos **caminen `00_Input/**` y filtren por manifiesto**. Además **dedup cross-lote**
(por `Message-ID` en correos, `sha256` en binarios) pasa de deseable a **obligatorio** (el mismo email en
dos entregas = dos carpetas). Relacionado con la carencia actual: el intake deduplica *dentro* de cada
fuente, no *entre* fuentes.

**Recomendación.** Es un cambio de arquitectura, no un ajuste al vuelo: **merece brainstorming + spec**
(como gmail-mcp), con la **sala de lectura como banco de pruebas** de la lectura por manifiesto. Decidir
A vs B (o híbrido) es de Nikolai. Encadena con: proceso de correo (hogar canónico = etiqueta Gmail; jubilar
el reenvío manual a `mails.repositorio`; auto-etiquetar por W-code con filtro Gmail, ahora que el MCP de
correo tiene escritura) y con #53.

**Disparador de promoción.** Decisión explícita de Nikolai de rediseñar `00_Input`, o que la fricción
tri-canal / la duplicación cross-fuente vuelva a costar tiempo en otro caso. Hasta entonces, backlog.

---

## 55. Orden del pipeline documental: intake → atomize/explosión → sala de máquina → sala de lectura  [pieza de #54]

**Anotado 2026-07-13** durante el procesado del W-02XOR7. **Orden ideal:** intake →
**atomize/explosión** (romper compuestos: `.eml` → adjuntos + correos anidados como ficheros;
`.zip` → contenido) → **sala de máquina** (OCR/MD de las piezas ya atómicas) → **sala de lectura**
(clasificación humana). Hoy **atomize y máquina no se alimentan** porque viven en árboles distintos.

**Hechos verificados (2026-07-13):**
- `core.sala_maquina` **solo lee `00_Input/`** (excluye `90_Notas personales`).
- El extractor `.eml` de la sala de máquina (`core.extractor._try_email`) saca **solo cabeceras +
  cuerpo**; NO recorre adjuntos (no hay `walk()`/`get_payload` de partes). → un adjunto embebido
  **solo** en un `.eml` (no suelto en `00_Input`) **nunca se OCR/MD-ea** por esta vía.
- `core.email_atomize.atomize_dir` escribe por defecto en **`<caso>/01_Procesado/Emails`**, que la
  sala de máquina **no lee**. → poner atomize "antes" NO mete los átomos en el OCR/MD de forma
  automática.

**Por qué no es un simple reorden.** Encadenarlos exige plumbing: (a) que la sala de máquina lea
también `01_Procesado/Emails` (o el árbol de átomos), o (b) que atomize deposite en un bucket que la
máquina lea dentro de `00_Input` — pero (b) choca con la invariante **«`00_Input` es crudo, no se
toca»** (`destino_seguro`). Es exactamente el tipo de decisión que abre **#54** (dónde entran las
cosas / qué árbol lee cada etapa) → **tratar como parte de #54, no como ajuste al vuelo.**

**Mitigantes hoy (por qué no urge).** La sala de máquina ya OCR/MD-ea los adjuntos que están
**sueltos** en `00_Input` (en W-02XOR7 eran casi todos, por el pull del Drive). Vía alternativa sin
explotar el `.eml`: `core/adjuntos_contenido` (texto de cada adjunto → `<base>.contenido.md`).

**Disparador de promoción.** Se aborda junto con #54 (rediseño de `00_Input` / orden del pipeline), o
antes si aparece un caso con adjuntos probatorios **solo** embebidos en `.eml` que se pierdan en el
OCR/MD. Hasta entonces, backlog. Relacionado: #53, #54 y la doctrina de proceso de correo.

**Actualización 2026-07-27.** El *orden* ya no depende de la memoria del operador: el bloque
`[SIGUIENTE-CABLEADO-CORREO]` del `PLAN.md` encadena la atomización dentro de
`scripts/sala_maquina.py::apply`. Lo que **sigue en pie de esta entrada** es el diagnóstico de fondo
—atomize y máquina viven en árboles distintos y encadenarlos no mete los átomos en el OCR—, que el
cableado confirma en vez de resolver. Los defectos del motor que impiden prometer un árbol
atomizado fiable están ahora acotados en **`#98`** (enumeración no recursiva) y **`#99`**
(convergencia bajo borrados + publicación atómica).

**Actualización 2026-07-28 (PR #151, `c845a01`).** El **orden** ya lo garantiza el código:
`scripts/sala_maquina.py::apply` atomiza antes del OCR. Lo que este ítem seguía
prometiendo y **sigue sin cumplirse** es lo otro: que los átomos ENTREN al OCR. La sala
de máquina continúa leyendo solo `00_Input`, así que el contenido de los adjuntos
atomizados sigue fuera (`MEJORAS #87`), y el consumo del árbol atomizado por la sala de
lectura es `MEJORAS #86`. La parte de este ítem que era «encadenar» está cerrada; la que
era «alimentar» no.

---

## 56. Mejora del proceso de sala de lectura: motor determinista + tool MCP, cronología + nombres que hablan  [pieza de #54/#55] [DESCARTADO 2026-07-23 — ver #75 / PR #124]

**Anotado 2026-07-13** tras montar la sala del W-02XOR7. La corrida costó ~10 min (un subagente re-leyó
los 169 ficheros de `00_Input`) **pese a existir ya los MD/`raw_text` de la sala de máquina**. Un script
ad-hoc determinista lo rehízo en **segundos**, pero con bugs (acentos en el match de carpeta → `06. PBC`
vacío; formato de 7 columnas del `_MANIFIESTO`; sin dedup por contenido; descripciones = slug del nombre
→ **mudas** cuando el original es opaco). Un `core` testeado los evita.

**Propósito de la sala (NO se cuestiona):** es donde el abogado **lee por orden de fechas** documentos con
**nombres que hablan** (entender el doc sin abrirlo). El esqueleto es **cronológico** (`CRONOLOGIA`), no
por categoría.

**Objetivos:** (1) montarla **más rápido**; (2) **reducir `0000-00-00`** (la fecha ordena la sala → campo
de máximo valor); (3) **nombres que hablan**.

**Arquitectura decidida (brainstorming 2026-07-13):**
- **`core.sala_lectura` determinista y testeado** (revivir/adaptar el deprecado 2026-06-18) que
  **consume la salida de la sala de máquina** (`_cobertura.md` + `raw_text/` + los sha256 ya calculados)
  en vez de re-explorar/re-hashear `00_Input`. Dedup por sha reutilizando hashes de la máquina; bundles
  (WhatsApp/`.eml`) deterministas en core.
- **Expuesto como tool MCP `build_sala_lectura(caso)` en el plugin FeesDefender** (junto a
  `expedientes-xl`): corre **local** (PC, donde viven G:/OCR/core) pero **invocable desde Cowork** por el
  puente `.dxt` — patrón de `google-despacho`/`gmail`/`expedientes`. "Cowork construye" = dispara el motor
  local. **Un solo motor**, sin mantener vía LLM paralela.
- **La skill pasa a orquestador fino:** llama a la tool + resuelve solo el residual + presenta el gate.

**Producción de los 3 campos (principio: determinista donde ya habla/ya tiene fecha; LLM solo el residual):**
- **Categoría → FACETA barata heredada** de la carpeta-oráculo del Drive EV. Columna en manifiesto/catálogo
  + vista agrupada opcional en INDICE. **Degradada de esqueleto a etiqueta**; sin gate, sin routing
  PBC-por-parte fino. Ningún consumidor vivo ramifica sobre ella (scorer = código muerto). Único uso real:
  armar la documental de la demanda por tipo. **Nunca pasa por LLM.**
- **Fecha → determinista sobre `raw_text`:** fórmula de firma ("En X a N de MES de AAAA"), cabecera `Date`
  de emails, timestamp de WhatsApp, fecha registral/nota simple, fecha en nombre. Residual ambiguo (varias
  fechas) → pasada LLM.
- **Descripción que HABLA → determinista** cuando el tipo/nombre/**asunto del email** ya habla (encargo,
  nota simple, oferta, DNI, anexo PBC, catastro, CEE, "reclamación honorarios"…). Content-derived para el
  residual opaco (`753`, `25-0020`, `CNT…`, `(sin asunto)`, `detalle_transferencia`). **Siempre sin PII**
  (describe el documento, no a las partes).

**Eficiencia clave:** fecha + descripción del residual se resuelven en **una sola pasada LLM** sobre el
puñado opaco/ambiguo (lee su `raw_text`, devuelve `{fecha, descripcion}` sin PII). El grueso (los que ya
hablan/tienen fecha) es determinista e instantáneo → cumple el objetivo de velocidad.

**Flecos menores:** dedup por **contenido** (docx + su `.docx.pdf`; `Nota Simple` ×2 casi idénticas con sha
distinto) — opcional, por hash de texto normalizado. Tests que cubran el bug de acentos en el match de
carpeta y el formato de 7 columnas del `_MANIFIESTO` (que exige `manifiesto_a_catalogo.py`).

**Disparador de promoción.** Decisión de Nikolai de invertir en el `core.sala_lectura` + tool MCP, o
recurrencia del coste de montar salas grandes. Relacionado: #54 (layout `00_Input`), #55 (orden del
pipeline: la máquina alimenta la lectura), plugin FeesDefender / `expedientes-xl`.

**Anotación 2026-07-23 — DESCARTADO.** La decisión-madre `#56 vs #75` (ver #75) se resolvió: en
`docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-design.md` (PR #124, mergeado a
`main` en `55df077`) Nikolai descarta explícitamente revivir `core/sala_lectura.py` como motor
determinista + tool MCP, a favor de un script pequeño embebido en la propia skill (§3 de esa spec).
Consecuencia: `core/inventory.py`/`core/catalogo_documental.py` (que hoy solo alimentan ese camino
deprecado) quedan sin plan que los reviva — candidatos limpios a retirar, no a fusionar aquí (ver
anotación en #48). Esta entrada queda cerrada/descartada salvo que Nikolai la reabra explícitamente.

---

## 57. Generador de "instrucciones del proyecto" por caso (para proyectos compartidos de claude.ai)

**Anotado 2026-07-13** tras brainstorming sobre BaRS8 (W-02XOR7). Cada caso se lleva como **proyecto
compartido de claude.ai web (plan Team)** que usa el equipo del despacho (Ana, Sergio, Paola). El campo
**"Instrucciones del proyecto"** orienta a Claude en cada chat de ese proyecto. Hoy se rellena a mano y su
80% es boilerplate idéntico entre casos; el 20% específico ya vive en `_caso.md.meta`. **Por ahora se
genera a demanda pidiéndoselo a Claude** (no automatizado); esta entrada guarda el diseño para cuando
convenga automatizarlo.

**Modelo de las 3 superficies del proyecto (verificado con la doc de Anthropic + la UI, 2026-07-13):**
- **Instrucciones** → COMPARTIDO ("Todos en Tyukhay…"), editable por miembros "Can edit"; se carga en cada
  chat. Es la única superficie compartida + siempre presente.
- **Contexto** (knowledge) → COMPARTIDO; adjuntar PDFs/docs (aquí van `INDICE.md`, `CRONOLOGIA.md`, triaje,
  viabilidad — que ya refresca el pipeline, sin mantenimiento a mano).
- **Memoria** → **PRIVADA POR USUARIO** ("Solo tú"), autogenerada, apagable por el admin. **No sirve** para
  estado compartido del equipo; se deja fuera.
- Nota: Cowork de escritorio **no** soporta proyectos compartidos (local, sin sync) → el proyecto es web.

**Decisión de diseño (aprobada):** las Instrucciones son **estáticas** — sin línea de "estado/próxima
acción" ni bitácora a mano (Nikolai no quiere babysitting del campo). "En qué punto está el caso" sale de
los docs de Contexto (que se auto-refrescan) y de la Memoria privada. El generador solo rellena lo
determinista y estable.

**Arquitectura propuesta (generador C-lite, patrón biblioteca):**
- `core/instrucciones_proyecto.py` (cerebro puro) + CLI. Tres piezas:
  - `glosa_tipo_caso(tipo_caso) -> str`: diccionario `tipo_caso → frase` (p. ej. `NEGATIVA_OFERTA` →
    "el propietario acepta la oferta y luego se niega a formalizar; el despacho reclama los honorarios
    devengados por E&V"). Fallback genérico + marca visible si el tipo es desconocido.
  - `construir_instrucciones(meta: dict) -> str`: **pura**, sin I/O; boilerplate fijo (constante del módulo:
    punto de entrada, cómo trabajar, equipo/revisión, convenciones) + campos derivados.
  - CLI `python -m core.instrucciones_proyecto <caso>`: lee `00_Input/_caso.md`, escribe
    `07_AI cowork/_INSTRUCCIONES_PROYECTO.txt` (UTF-8 sin BOM, **contenido = texto pegable puro**, sin
    cabecera "GENERADO" que contamine el pegado) e imprime la ruta.
- **Derivados de `meta`:** identidad/título, `W-XXXXX`, `tipo_caso`→glosa, `ciudad`, `cuantia`, partes;
  `cliente` por defecto **Engel & Völkers** si `meta.cliente` es `null` (todo FeesDefender es E&V); campos
  `null` → "pendiente".
- **Idempotencia:** artefacto derivado → regenerar **sobrescribe** (sin merge). No se edita a mano: si
  cambia `meta`, se regenera. El campo de claude.ai es la copia viva; el `.txt` es semilla + adjunto a
  Contexto.
- **Enganche a `abrir-caso`:** tras el scaffold, `core/abrir_caso.py` invoca el generador → todo caso nuevo
  nace con su `.txt`. CLI standalone para regenerar casos existentes.
- **Boilerplate/equipo** (Ana secretaria / Sergio pasante / Paola abogada / confirmación externa de Nikolai)
  vive en **un solo sitio** (constante del módulo o `data/`).

**Tests:** golden snapshot de `construir_instrucciones` con `meta` de BaRS8 → el texto aprobado; test de
no-divergencia (todo `tipo_caso` de `core/config` tiene glosa); `null`→"pendiente" y `cliente` null→E&V;
CLI escribe en ruta correcta, UTF-8 sin BOM, idempotente.

**Plantilla de oro aprobada (salida esperada para BaRS8, `NEGATIVA_OFERTA`):**

```
CASO: «BaRS8 · Santes Creus 15, Montcada i Reixac (W-02XOR7)». Cliente: Engel & Völkers.
Tipo: «NEGATIVA A OFERTA ACEPTADA» — el propietario acepta la oferta y luego se niega a
formalizar; el despacho reclama los honorarios de intermediación devengados por E&V.
Ciudad: «Barcelona». Cuantía: «pendiente». Partes concretas: «pendientes» (ver _caso.md).
(«Los consultores» que aparezcan en la documental son personal de E&V, no del despacho.)

PUNTO DE ENTRADA
- Empieza SIEMPRE por "00_Input/_caso.md": es el índice del caso y enruta al resto
  (documental, cronología, triaje, viabilidad). No navegues por rutas sueltas ni asumas
  dónde está algo; si no está enlazado ahí, pregunta.

CÓMO TRABAJAR ESTE CASO
- Trabaja anclado a la documental del expediente. No inventes hechos, cifras ni
  jurisprudencia. Si un dato no consta, dilo y márcalo como pendiente.
- "90_Notas personales" es zona del abogado: no la leas ni escribas en ella.
- Comunicaciones al cliente en castellano (en ruso si el cliente es de origen ex-URSS).

EQUIPO Y REVISIÓN (Tyukhay Legal)
- Paola (abogada): trabajo jurídico completo.
- Sergio (pasante): redacta e investiga; todo escrito sale a revisión de Paola o Nikolai.
- Ana (secretaria): organización, intake y logística de comunicaciones; no redacción jurídica.
- Toda acción con efecto externo (enviar, presentar, subir, cerrar) la confirma Nikolai.

CONVENCIONES
- Partes: "propietario / buscador" (no vendedor/comprador), aunque el crudo use esos términos.
- Refiere a terceros por "W-02XOR7" y por su rol; no vuelques nombres, DNI/NIE ni emails en el chat.
- NIG no se usa.
```

Si las *instrucciones del perfil* del despacho ya cargan terminología, higiene PII y "no inventar
jurisprudencia", el bloque CONVENCIONES es podable.

**Pieza separada (NO parte de esta entrada, follow-up propio): hub de `_caso.md`.** Hoy la sección
`## Navegación` de `_caso.md` es un stub fijo que genera `core/case_manager.py` (`[[scoring]] [[viabilidad]]
[[hechos_atomicos]] [[contradicciones]] [[demanda]]`) apuntando a artefactos que aún no existen; editarla a
mano es frágil porque el escritor **regenera el cuerpo entero** desde `meta` (los mutadores de lock sí
preservan el cuerpo; el regenerador no). Para que `_caso.md` sea el **punto de entrada único real** que
enruta a sala de lectura/máquina/triaje/viabilidad, hay que hacer que el escritor del índice incluya esos
enlaces **condicionalmente cuando existan**. Cierra el tema SSOT ("una fuente por hecho": `_caso.md` = hub
de navegación + metadatos; `INDICE.md` = corpus documental). Es un PR aparte y no bloquea el generador.

**Disparador de promoción.** Recurrencia del coste de teclear las instrucciones a mano al abrir casos, o
decisión de Nikolai. Relacionado: `abrir-caso` (`core/abrir_caso.py`, `_shared/scaffold_caso.py`),
#30 (manifiesto + wikilinks de Navegación), #54/#55 (layout y pipeline).

## 58. Fiabilidad de la sala de máquina: cobertura acumulativa + refuerzo por visión  [COMPLETADO → PR #42 (`24e69db`)]

**Anotado 2026-07-14** tras la sesión E2E VALERO (W-02XOR7). Cluster A del roadmap post-VALERO. Tres piezas
acopladas:

- **Bug — `_cobertura.md` se machaca en el `apply` incremental.** `scripts/sala_maquina.py::apply` escribe
  `render_cobertura(cob)` con **solo** los documentos de la tanda; una segunda corrida incremental borra la
  cobertura acumulada y las notas de refuerzo. *Disparador vivo:* al añadir D_02/D_03 a VALERO, la cobertura
  de 35 filas se redujo a 4 y hubo que reconstruirla a mano. *Fix:* `apply` debe **fusionar** el estado
  previo (leer las filas existentes / reconstruir desde el frontmatter de `03_MD/` + los `sin_soporte`)
  antes de renderizar. Es pérdida silenciosa de integridad (se pierde "qué queda por revisar").
- **`--vision` es un stub que falla en silencio.** `core/sala_maquina._transcribir_vision` lanza
  `NotImplementedError`; `_reforzar_con_vision` se traga la excepción y el documento queda `empty` con nota
  "refuerzo vision falló". *Fix:* cablear a un transcriptor real — **preferente la sesión Claude** (criterio
  de Nikolai: sin API de pago; ver `feedback-claude-en-sesion-vs-api-pago`) vía entry-point documentado; y,
  sin cablear, que `apply --vision` **avise ruidosamente** en vez de no-op.
- **Comando `reforzar` persistente.** `sala_maquina reforzar <caso> <doc>` que haga render→visión→reescriba
  MD (frontmatter+`chars`+`text_sha256`), marque el SHA en `_sala_maquina_state.json` y actualice la
  cobertura, de forma coherente. *Disparador:* en VALERO lo hice en 4 pasos manuales.

**Disparador de promoción.** Bugs que mordieron en vivo esta sesión + operación (refuerzo) que hubo que
hacer a mano. Rutas: `scripts/sala_maquina.py`, `core/sala_maquina.py` (`_transcribir_vision`,
`render_cobertura`, `ejecutar`).

## 59. Expediente scratch (caso de trabajo local) + detección E&V por stub `_caso.md`  [PROMOVIDO → PLAN.md]

**Anotado 2026-07-14.** Cluster B del roadmap post-VALERO. Diseño aprobado en
`docs/superpowers/specs/2026-07-14-expediente-scratch-design.md`. Un caso de trabajo **local** ligero con un
`_caso.md` stub mínimo (`meta`: W-code, partes, ciudad, `tipo_caso`, `cliente`=E&V, `estado: scratch`) para
que **todas las skills lo detecten** (modo E&V, terminología, ubicación) sin tocar Drive/CRM, más flags
`--case-dir`/`--casos-root` en el pipeline (elimina el override de entorno) y un comando `promover` a
expediente completo del Drive (reutiliza `core/abrir_caso.py`). Resuelve de raíz el antiguo punto "detección
de modo E&V" (VALERO cayó en "civil genérico" por falta de `_caso.md`). *Disparador:* toda la fricción E2E
de VALERO nació del `_caso.md` ausente. Custodia: el `estado: scratch` es transitorio; documentar en
`SEGURIDAD_DATOS`/`GOBERNANZA` que no sustituye al expediente del Drive para prueba.

## 60. `gen_solicitud`: petición subsidiaria (averiguación de domicilio) + DNI pendiente  [PROMOVIDO → PLAN.md]

**Anotado 2026-07-14.** Cluster C (quick win). `gen_solicitud.py` (ubicación real:
`.claude/skills/preparacion-audiencia-previa/scripts/gen_solicitud.py`) no tiene campo para una petición
subsidiaria por testigo (p. ej. **averiguación de domicilio, art. 156 LEC**) ni manejo de **DNI pendiente**;
hoy hubo que doblar el art. 156 dentro de `citacion` y vaciar `movil`/`email`, y marcar el DNI de un testigo
como `[pendiente de aportar]` a pelo. *Fix:* añadir `averiguacion_domicilio`/`subsidiario` como campo del
`testigo` y `dni` opcional con marca de pendiente que renderice limpio. *Disparador:* AP de VALERO — la
testigo compradora (art. 156 LEC) y la testigo directora de zona (DNI pendiente).

## 61. Ingesta documental robusta: `.doc`, localizador de página en escaneado, extractor de entidades

**Anotado 2026-07-14.** Cluster D (backlog). Tres huecos observados en VALERO:
- **`.doc` binario → `sin_soporte`.** Añadir conversión LibreOffice headless (`soffice --convert-to`) aguas
  arriba en `core/sala_maquina.clasificar_ruta`. (En VALERO había gemelos PDF, sin pérdida.)
  **[PROMOVIDO → PLAN.md 2026-07-27]** — `[SIGUIENTE-DOC-LIBREOFFICE]`. **Disparador:** en W-02MA0R
  (expediente CRM 487) la **demanda del juicio ordinario** existe en el CRM *solo* como
  `ordinario_vuelta_comprador.doc`, **sin gemelo PDF**: cae a `sin_soporte`, no tiene ni MD ni OCR y
  ningún LLM puede leerla. Se acabó el «sin pérdida» que justificaba dejarlo en backlog. Los otros dos
  puntos de esta entrada (localizador de página, extractor de entidades) **siguen en backlog**: no tienen
  disparador.
- **Localizador de página falla en PDF escaneado.** `pdfminer.extract_pages` devolvió `None` al buscar por
  texto un bloque en un escaneo (sin capa de texto); fallback por render+visión o por índice de página.
- **Extractor de "bloque de citación / entidades" con visión** (DNI, IBAN, email, móvil, domicilio) para
  docs con PII OCR-corrupta. *Disparador:* el email de una testigo salió con el «@» transcrito como otra letra por el OCR.

## 62. Entorno Windows (`setup_windows_deps`) + unificar el `.bat` de OCR con el pipeline

**Anotado 2026-07-14.** Cluster E (backlog).
- **`scripts/setup_windows_deps.ps1` vendorizado** — pngquant, tesseract-langs y **jbig2enc** (sin fuente
  limpia en Windows; documentar/vendorizar binario revisado), para evitar el baile scoop + `iex` remoto
  bloqueado que hicimos hoy.
- **Unificar el `.bat` de escritorio con el pipeline** — el `OCR_PDF.bat`/`ocr_pdf.py` del escritorio
  duplicaba el motor (con el bug `--force-ocr` ya corregido a `--skip-text` en la sesión). Un único
  entry-point de arrastrar-y-soltar que invoque el pipeline bueno (`core/sala_maquina`), o documentar que el
  `.bat` es solo herramienta throwaway.

## 63. Sincronización procesal: providencia/DIOR de señalamiento → `00_Input`

**Anotado 2026-07-14.** Cluster F (backlog). El señalamiento de la audiencia previa (art. 429 LEC) no está en
`00_Input` (no hay providencia sincronizada del CRM), así que las skills procesales no pueden leer la fecha/
sala; en VALERO la aportó el usuario ("hoy"). El sync Sudespacho debería depositar la providencia/DIOR en
`00_Input`. Depende de trabajo de integración Sudespacho (`docs/INTEGRACION_SUDESPACHO.md`).

## 64. Split de bundles — deferidos de la revisión de rama de F1 (2026-07-15)

**Anotado 2026-07-15.** De la revisión final (Opus) de la Fase F1 del split (`core/split_documental.py`;
plan `docs/superpowers/plans/2026-07-14-split-sala-maquina.md`). Ninguno bloquea F1; se resuelven en su
fase natural:

- **F0 (calibración con bundle real):** ajustar `UMBRAL_TINTA_BLANCO`/`UMBRAL_CHARS_BLANCO` contra el
  expediente escaneado real, y **añadir un fixture con página imagen** (foto/plano escaneado: pocos chars,
  tinta alta) que pruebe la *sinergia de las dos rejas* — que el ink-gate NO la marque como hoja en blanco.
  Hoy no hay test de ese caso (el helper `build_pdf` es texto-only). Relevante: la querella real trae páginas foto.
- **F2 (integración en `sala_maquina`):** `apply` debe (a) llamar `validar_manifiesto(man, total_pag)` ANTES de
  `materializar` (M-A), y (b) enrutar los passthrough de 1 segmento FUERA de `materializar` (M-C) — ambos ya
  contemplados en el plan (Task 12 `_split_o_md`). Añadir limpieza de PDFs de segmento huérfanos cuando el
  letrado re-edita el manifiesto quitando/re-rangeando un segmento (M-4).
- **Robustez del manifiesto editable (F2):** `_pp_a_rango` da un error críptico ante un `pp` mal formado
  (`"5"` → unpack error); mensaje amigable "rango mal formado, usa 'inicio-fin'" (M-B). `materializar` recibe
  `parent_sha256` por parámetro e ignora `manifiesto["bundle_sha256"]`: documentar que deben coincidir o leer
  del manifiesto (M-D).
- **Eficiencia (revisar solo si F0 lo mide lento):** `detectar` re-parsea el PDF ~3× (pypdf + pypdfium2 +
  pdfminer vía `separar`). Es composición plan-mandated (reúso del módulo congelado), correctness-neutral.

## 65. Conteo de tests estructural: `scripts/test_summary.py` (JUnit XML) cableado en protocolo y comandos

**Anotado 2026-07-16.** El cierre de sesión de hoy quemó ~6 corridas de la suite completa intentando extraer
la línea de resumen de pytest con greps — vía que `DEAD_ENDS.md` (primera entrada, 2026-07-07) declara ROTA
en este entorno (Git Bash/Windows: la línea final no pasa por tuberías), con la solución documentada (JUnit
XML). Fallo de fondo: **el protocolo ordena la vía rota** — `pytest -q --tb=no` crudo está cableado en 5
sitios (`CLAUDE.md` §Tests, `STATUS.md` §protocolos, `.claude/commands/{cierre,status,tests}.md`), así que
cada sesión futura tropieza igual: la instrucción activa gana al conocimiento pasivo de DEAD_ENDS.

Arreglo (micro-PR autocontenido, ~30 min):
1. `scripts/test_summary.py` (+ test): corre pytest UNA vez con `--junit-xml` a temp, parsea
   `tests/failures/errors/skipped` del `<testsuite>` con `xml.etree` e imprime una línea limpia y fiable
   (`1790 passed, 5 failed, 58 skipped — FAILED: nombres…`).
2. Recablear los 5 sitios para invocar `python -m scripts.test_summary` en vez del pytest crudo.
3. Añadir a `CLAUDE.md` la regla de método que faltaba: *operación cara (suite, OCR, pull) → UNA ejecución
   con salida a fichero; el análisis se itera sobre el fichero, nunca re-ejecutando*.

Principio: como con la higiene PII — a un fallo de disciplina se responde con estructura, no con más
disciplina. Disparador ya ocurrido (mordió 2026-07-16); memoria `feedback-pytest-junit-xml-y-dead-ends`.

---

## 66. MCP "Drive como disco" (`expedientes-xl` consolidado) — diferidos V2 y V1.1

**Anotado 2026-07-17.** Tras el V1 completo del servidor consolidado (Tasks 1-18,
spec `docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-design.md` rev 3,
right-sized tras 5 rondas adversariales). El spec §5 ya fija qué queda fuera de V1 y
por qué; esta entrada es el ancla de backlog para cuando aparezca el disparador
concreto de cada pieza (regla de promoción de `CLAUDE.md`: no se construye por
completitud de diseño ni por anticipación).

**Diferido V2 (spec §5, "V2 diferido"):**
- **`move`/`rename`** — doctrina de la casa es copiar, nunca mover (`move_file` de
  `expedientes` ya está marcado destructivo); solo entra si aparece un flujo real que
  lo necesite.
- **`batch_rename`** — si entra, "pelado": dry-run + continue-on-error + informe
  old→new en auditoría, **sin** journal/rollback (falsa transaccionalidad; la doctrina
  de recuperación real de este servidor es re-ejecutar-converge, no deshacer).
- **`create_zip`** — comprimir no tiene disparador hoy (solo `extract_archive` está en
  V1).
- **`du` como tool** — la lógica de volumen ya existe internamente (`guard_tree`, §6.2)
  pero no está expuesta como tool de consulta directa.
- **`verify_manifest`** — duplicaría `rclone check --one-way` del checkin; además el
  `MANIFEST_CHECKOUT.json` llavea por MD5 de rclone, no por SHA-256 (los hashes de este
  servidor) — requeriría decidir primero cuál es la fuente de verdad del hash antes de
  construirlo.
- **Escritura en `H:` + gate de mutación-en-compartido + staging de temporales** — hoy
  `H:` es solo-lectura en V1 porque ningún flujo real escribe en el Drive de E&V (la
  única mutación existente es `permissions.create` vía API en `core/share_drive.py`,
  fuera del ámbito FS de este MCP). El día que exista ese flujo, hace falta además el
  gate de mutación-en-compartido y el staging especial de temporales que el spec §2
  aplaza explícitamente.
- **Cancelación real de workers** — el timeout de `XL_OP_TIMEOUT` hoy solo hace que el
  canal MCP *responda*; la E/S puede seguir en el hilo daemon. Cancelación-que-aborta-E/S
  de verdad no es limpio en Python/Windows y el spec la aplaza a menos que se
  **observe** acumulación real de hilos (hoy mitigado por el semáforo `XL_IO_CAP` +
  timeouts).
- **`confirm_sync` como receta de skill** (ex-#46 del spec, no tool del servidor) — no
  hay señal local fiable de "pendiente de subir" en GDFD (verificado: no existe
  `local-content-checksum`; el estado determinista vive en el protobuf cerrado de
  `operations`). Si un flujo lo exige: skill que, tras escribir, haga polling de
  `google-despacho.get_file_metadata` (`md5Checksum`/`modifiedTime`) con backoff — nunca
  un tool de este servidor.

**Diferido V1.1 (más cercano, no V2):**
- **Consolidar las 3 copias de `_abrible`.** `winio.py`, `fsops.py` y `readops.py`
  definen cada uno su propia función privada `_abrible(p)` (idéntica: prefijo `\\?\`
  solo cuando la ruta roza `MAX_PATH`). Consolidar en `winio._abrible` (o exportarla
  pública) y que `fsops`/`readops` la importen, eliminando la triplicación.
- **Enumeración por fichero de `omitidos` en árboles fríos.** `guard_tree` hoy reporta
  agregados (`n_cold`, `n_total`) y, al abortar, lista solo la raíz del árbol en
  `omitidos=[str(root)]` — no los ficheros COLD individuales. Para un árbol grande,
  saber *cuáles* ficheros son COLD (no solo cuántos) ahorraría una segunda vuelta al
  usuario decidiendo qué hidratar. Requiere que `oracle.subtree_cold_stats` devuelva las
  rutas, no solo el conteo (cambio de forma del oráculo, no solo del guard).
- **`reclasificar_resueltos` también debería podar symlinks a destinos FUERA del sandbox.**
  El fix de la revisión final (commit `9802fd1`) hizo que `iter_tree(..., reclasificar_resueltos=True)`
  pode los symlinks cuyo destino RESUELTO es Tier 0 (anti-fuga de `90_Notas personales`).
  Pero solo comprueba `classify(resuelto) is PROHIBIDA`; NO re-verifica pertenencia al
  sandbox. Un symlink-fichero en workspace que apunte a un destino no-Tier0 *fuera* de
  `G:`/`H:` sigue siendo entregado, así que `search_content` podría leer el contenido de
  un fichero pequeño (< `XL_HYDRATION_MAX_FILE_MB`; los grandes los para `guard_file`→UNKNOWN)
  fuera del sandbox. Disparador de bajísima probabilidad (exige un symlink NTFS de fichero
  creado por admin; los atajos de GDFD son `.lnk`, ya tratados por `resolve_shortcut`).
  Fix barato y completo en el mismo punto: podar también cuando `resolve_within(resuelto)`
  falle (`OutsideSandbox`). Detectado en la revisión final whole-branch como observación
  no-bloqueante adyacente al fix, no introducida por él.

## 89. Que la documentación no se desincronice ni cueste tiempo: 4 medidas contra los líos de edición paralela

**Origen (2026-07-27, sesión del bundle por hilo / PR #131).** Al integrar la rama con `main` —que
había avanzado 4 PRs por sesiones concurrentes— salieron **9 conflictos** y tres colisiones de
identificadores: el **#84** de este mismo documento (dos sesiones cogieron el mismo número), la
**versión 1.13** de `organizar-sala-lectura` (publicada en `main` mientras la rama escribía esa misma
versión) y la **fila 7** de la cola de `PLAN.md`. Ninguna colisión costó "un conflicto": costó
**propagar el renumerado a 7 ficheros** con referencias cruzadas. Además `PLAN.md` afirmaba estado
falso (un PR ya mergeado seguía como "pendiente de merge"; un ítem ya construido, como "spec lista").

**El fallo más caro no fue un conflicto.** La rama arrancó 4 PRs por detrás de `main`, y una
reescritura completa de `construir_indice` **estaba a punto de revertir en silencio** un fix que
`main` ya tenía (fallback `categoria`→`tipo`; 669 filas mal clasificadas en un caso real). No lo cazó
ningún test: se cazó al mirar `main` antes de mergear. Eso es suerte, no proceso.

**Tres causas raíz:** (a) identificadores monótonos asignados **a mano** en ficheros que varias
sesiones editan a la vez; (b) ramas que trabajan sobre **base vieja** y lo descubren al final;
(c) documentación que **repite estado** que git y GitHub ya conocen.

### Medida 1 — Sincronizar con `main` temprano (la única gratis; la que haría primero)

`git fetch && git merge origin/main` **al abrir sesión** y **otra vez antes de reescribir cualquier
función existente**. Elimina la causa (b) entera. Complemento de coste cero: antes de reescribir una
función en bloque, `git log -3 -- <fichero>` sobre `origin/main` — el vector del casi-fallo fue
reescribir en bloque en vez de editar quirúrgicamente. **Coste:** un minuto por sesión, cero código.

### Medida 2 — Quitar los contadores compartidos (no todos cuestan lo mismo)

- **Números de fila de la cola de `PLAN.md`: quitarlos.** La prioridad ya la da el orden de las filas;
  el número no aporta y es colisión garantizada cuando dos sesiones añaden o cierran ítems.
  **Coste real: ~5 min.** Verificar antes que ninguna referencia externa cite "fila N".
- **Versión de skill: validarla contra `origin/main`.** Un guard que falle si la versión que escribes
  **ya existe** en el `CHANGELOG.md` de `origin/main`. Hoy habría avisado en un segundo, en vez de a la
  hora, al mergear. **Coste: ~30 min** (un test o un hook de pre-push).
- **Slug en vez de número para ítems nuevos de este documento: NO es gratis, decidir aparte.** La
  primera versión de esta idea se estimó en "5 minutos"; **es falso**: `MEJORAS #NN` es la **llave de
  referencia** usada en docs, specs, CHANGELOGs y commits, y el guard **G1**
  (`tests/test_docs_gobernanza.py::test_mejoras_futuras_numeracion_unica`) se apoya en el formato
  `## NN.` precisamente porque esa llave debe ser unívoca. Cambiarlo implica decidir la nueva llave y
  migrar las referencias. **Queda como cuestión abierta, no como acción.** Mitigación barata mientras
  no se decida: tomar el número **tras** un `git fetch` (la Medida 1 ya lo cubre).

### Medida 3 — `PLAN.md` deja de narrar el estado que GitHub sabe mejor

Las filas llevan **prioridad, ítem y disparador**; el estado del PR **se consulta, no se transcribe**
(nada de "pendiente de merge" a mano). Misma doctrina que ya fija
`docs/GOBERNANZA_FUENTES_VERDAD.md` para los hechos de git: el hogar del dato es quien lo genera.
**Coste: ~15 min** de limpieza, más la disciplina de no volver a escribirlo.

### Medida 4 — Extender `/status` para que la fidelidad sea un comando, no un acto de fe

Que imprima: cuántos commits lleva la rama **por detrás** de `origin/main`, **qué ficheros tocan en
común** la rama y `main` (aviso temprano de conflicto), PRs abiertos, y **versión de cada skill en la
rama frente a `main`**. Convierte las tres causas en algo observable en un segundo. **Coste: ~1 h.**
Es el que más tiempo ahorra por hora invertida, después de la Medida 1.

### Extra (barato, se repetirá si no se cierra)

Un subagente commiteó en `main` de la **raíz compartida** en vez de en su worktree asignado. Se cierra
con una línea en el prompt de despacho («verifica `git rev-parse --abbrev-ref HEAD`; si no es la rama
asignada, aborta») o con un hook. **Coste: 5 min.**

**Disparador de promoción a `PLAN.md`:** decisión de Nikolai. Las Medidas 1 y 4 no dependen de nada; la
2 y la 3 conviene hacerlas juntas (ambas tocan `PLAN.md`). La cuestión del slug **no se promueve** hasta
decidir la llave de referencia.

**Disparador de promoción.** Cualquiera de estas piezas se promueve a `PLAN.md`
individualmente cuando aparezca su caso real (un flujo que necesite escribir en `H:`,
un caso donde el batch-rename ahorre trabajo manual repetido, una sesión de humo que
mida cola de hilos zombis, etc.) o por decisión explícita de Nikolai — nunca por
anticipación. Ver `docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-design.md`
§5 y §9 para el razonamiento de right-sizing original.

## 67. `core/sala_lectura.py` (CLI deprecado): ruta MD desalineada + colisión de nombres en `poblar`

**Anotado 2026-07-17.** Descubierto abriendo el caso W-02T3XO con el **CLI `scripts/sala_lectura.py`**
(envuelve `core/sala_lectura.py`, marcado DEPRECADO 2026-06-18, superado por la skill
`organizar-sala-lectura` v1.3). Dos defectos del módulo:

- **67.a — Ruta MD desalineada.** `_md_path` (`core/sala_lectura.py:244`) y `_link_md` (`:493`)
  apuntan a `01_Procesado/MD/`, pero la skill `organizar-sala-maquina` escribe los MD en
  `01_Procesado/02_Sala de máquina/03_MD/`. Resultado: `01_Procesado/MD/` queda vacío, los
  enlaces "ver texto" del `INDICE.md` salen rotos y `clasificar_residuo_llm` no encuentra el
  texto. **Fix:** repuntar ambas funciones (y el fallback LLM) a `02_Sala de máquina/03_MD/`
  como fuente única; o formalizar la ruta en `core/config`.

- **67.b — Colisión de nombres canónicos en `poblar` → sobrescritura silenciosa.**
  `_nombre_canonico` (`:563`) = `fecha_tipo_desc`; cuando el clasificador determinista pone
  `descripcion` genérica (p. ej. `fotografia` a todas las imágenes de igual fecha) varios
  documentos generan el MISMO nombre y `poblar_sala_lectura` (`:648`, `shutil.copy2`) los
  sobrescribe sin guardia de unicidad. En W-02T3XO: 26 entradas → 16 ficheros (las 9 imágenes
  de WhatsApp del comprador → 1; 2 DNI → 1; 2 índices de correo → 1). Sin pérdida real
  (originales en `00_Input`, `INDICE.md` enlaza los 26), pero la carpeta plana queda coja de
  prueba. **Fix:** sufijar el nombre canónico con `__<sha8>` en colisión (patrón
  `utils.output_slug`) o guardia de unicidad por nombre en `poblar`. Workaround aplicado al
  caso: descripciones únicas en el catálogo + re-`poblar`.

- **67.c — `poblar` escribe subcarpetas por fuente, no plano.** `poblar_sala_lectura` (`:633`)
  hardcodea `dst_rel = f"{_SALA}/{fuente_dir}/{nombre}"` → crea `Sala lectura/Drive E&V/`,
  `Sala lectura/Email/`, etc. La estructura canónica de la skill `organizar-sala-lectura` v1.3
  es **PLANA** (todos los documentos en la raíz de `Sala lectura/`; la categoría vive en
  `INDICE.md`, no en carpetas; los compuestos van en subcarpeta fechada). **Fix:** que
  `poblar` escriba plano (sin `fuente_dir`) salvo bundles. Workaround aplicado al caso: aplanar
  a mano (mover ficheros a la raíz + borrar subcarpetas de fuente).

**Meta-lección:** el fallo de fondo fue usar el **CLI deprecado** en vez de la skill canónica.
Como el módulo está deprecado, valorar si el fix merece un ciclo core+PR o si basta con jubilar
el CLI y encauzar todo por la skill `organizar-sala-lectura`. **Disparador de promoción:**
próxima apertura de caso que use el CLI local, o decisión de Nikolai de mantenerlo vivo.

## 68. Cableado del pipeline de correo: atomize + OCR de adjuntos no automáticos

> ⚠️ **[PROMOVIDO → `PLAN.md`, 2026-07-27]** — el **resto de 68.a** (encadenar la atomización, que hoy
> nadie invoca: verificado que solo la llaman el CLI manual y un script de auditoría) va al bloque
> `[SIGUIENTE-CABLEADO-CORREO]`, por **decisión explícita de Nikolai**; el disparador que este ítem
> esperaba (adjunto relevante que llegue solo por correo, sin copia en Drive) nunca se materializó.
> La mitad del flag `--extraer-adjuntos` ya está **resuelta** (`07b0377`). El **motor** de OCR de
> adjuntos de 68.b vive en **`MEJORAS #87`**, no en el bloque nuevo: allí solo se cablea quién llama a
> quién. El consumo de las fuentes atomizadas por la sala de lectura es **`MEJORAS #86`**.

**Anotado 2026-07-17** (caso W-02T3XO). El motor `core/email_atomize` (CLI `scripts/atomize_emails.py`)
extrae los adjuntos embebidos de los `.eml` (dedup por sha, filtro decorativo, fichas +
`INDICE_ADJUNTOS.md`, Capa B de autoría), pero **no está cableado** en el flujo:

- **68.a — `atomize_emails` es un paso manual.** Ni `abrir_caso` ni `organizar-sala-maquina`
  lo invocan. Además, el intake llama `email_export.export_label`
  con el default `extract_attachments=False` y **no expone el flag**, así que los adjuntos
  quedan embebidos en el `.eml` hasta que se lanza el motor a mano. **Riesgo:** un adjunto que
  llegue SOLO por correo (sin copia en Drive) no se extrae en el flujo automático. En W-02T3XO
  no hubo pérdida porque las 9 capturas estaban también en `00_Input/01_Drive EV/07. RECLAMACIONES`.
  - ⚠️ **CORRECCIÓN 2026-07-27 (rev. 2): `07b0377` NO es «la mitad resuelta» — es una trampa
    armada. Ver `#98`.** La lectura de abajo se quedó a medio camino: es cierto que con el flag
    activo cada adjunto se escribe suelto en `00_Input/<lote>/`, pero **el `.eml` de ese mensaje se
    va a una SUBCARPETA** (`email_export.py:1123-1132`) y el atomizador solo enumera el nivel
    superior (`extract.py:53`) → **los mensajes con adjuntos dejan de existir para el atomizador**.
    Se gana el binario para el OCR y se pierde el mensaje para la atomización, en silencio.
  - ✅ **PARCIALMENTE RESUELTO 2026-07-27** (`[PROMOVIDO → PLAN.md]` por decisión de Nikolai,
    bloque `[SIGUIENTE-INTAKE-EMAIL-FILTRO]`; commit `07b0377`): el flag ya se expone como
    `--extraer-adjuntos` en `scripts/abrir_caso.py` (default intacto en `False`, porque
    activarlo mueve la superficie de dedup de todo intake futuro). Verificado leyendo
    `email_export._escribe_mensaje`: con el flag activo cada adjunto se escribe como fichero
    suelto en `00_Input/<lote>/`, el árbol que `sala_maquina` sí recorre. *(Lectura incompleta:
    ver la corrección de arriba.)*
    **Corrección de dato:** el call site es `scripts/abrir_caso.py::_intake_email`, no
    `core/abrir_caso`. La otra mitad de 68.a —que la atomización se invoque en cadena y no a
    mano— **quedaba** pendiente cuando se escribió esto; se cerró después: ver el bullet
    siguiente.
  - ✅ **RESUELTA la otra mitad (PR #151, `c845a01`):** `scripts/sala_maquina.py::apply`
    encadena la atomización antes del OCR y declara el resultado en el evento
    `atomizado_email`. Lo que **sigue** abierto de `#68.b` es el **contenido** de los
    adjuntos atomizados (`MEJORAS #87`), no el encadenado.
- **68.b — OCR de adjuntos atomizados = "fase 2" no construida.** Las fichas `.md` de
  `01_Procesado/Emails/adjuntos/` quedan con `Descripción: (pendiente; OCR en fase 2)`. Y
  `organizar-sala-maquina` lee `00_Input`, **no** `01_Procesado/Emails/adjuntos/` → aunque se
  atomice, el **contenido** (texto/OCR) de los adjuntos del correo no entra en la sala de
  máquina/lectura. Hoy el dato solo se mina si existe copia del adjunto en `00_Input` (Drive).
- **Fix:** encadenar `intake → atomize → OCR de adjuntos → sala de máquina/lectura`
  (coherente con `MEJORAS #54/#55`), y construir la fase 2 de OCR de `email_atomize` (o que
  `sala_maquina` procese también `01_Procesado/Emails/adjuntos/`). **Disparador de promoción:**
  caso con adjuntos relevantes que lleguen solo por correo, sin copia en Drive.

## 69. Automatizar el envío de email desde el CRM (deja rastro en el historial del expediente)

**Anotado 2026-07-17.** Documentado el flujo completo de envío de email desde el CRM
(endpoints + payload en `docs/INTEGRACION_SUDESPACHO.md §10.9`): crear borrador
(`POST nest-mail/api/mail/`) → enviar (`PUT …/api/mail/{id}` con `draft:false`) → registrar
(`PUT api-crm-commons/api/element_register/mail/{id}`) → relacionar con el expediente
(`POST …/api/relation_element/extrajudiciales/{exp}`). **Valor:** el email queda en el historial
del expediente, consultable por Ana/Sergio/Paola sin ir en copia; uso frecuente. Candidato a
**tool** (dentro del MCP sudespacho F2/F3, o helper en `core/`). **Pendientes antes de construir:**
(a) confirmar auth de estos endpoints — las XHR del SPA usan **cookie de sesión web**, NO el
`x-api-key` de `core/`; (b) la rama "Email certificado" (no capturada); (c) el payload exacto se
capturó por HAR (los HAR nunca se commitean; contienen credenciales SMTP/IMAP en claro que expone
`GET /api/accounts/{id}`). **Disparador:** decisión de automatizar / uso recurrente. Detalle en
INTEGRACION §10.9 y en la memoria persistente `reference-sudespacho-enviar-email-crm`.

## 70. Workflow de archivo de caso (`core/archivar_caso.py`) + evento `archivado` en `INTAKE_EVENTS`

**Anotado 2026-07-18** (consolidación de las 3 aperturas del 2026-07-17; caso W-046G2R).
Archivar un expediente inviable es hoy una secuencia de 5-6 pasos **manuales**, sin
orquestador ni custodia forense homogénea. (Nota: esta entrada recrea la que la sesión de
W-046G2R creyó haber registrado como "#66"; se perdió en el incidente de escritura sobre la
raíz compartida — el `#66` real es "MCP Drive como disco".)

- **70.a — `archivado` NO está en `INTAKE_EVENTS`** (`core/intake_log.py`, 25 eventos
  verificados 2026-07-18). Hoy la línea de archivo se escribe a mano en `_intake_log.jsonl`
  **sin pasar por `intake_log.append_event`** (que la rechazaría por validación). **Fix
  (quick win):** añadir `archivado` al `frozenset` `INTAKE_EVENTS`. *[Promovido a `PLAN.md`
  como B4 — disparador: decisión de Nikolai 2026-07-18.]*
- **70.b — `core/archivar_caso.py` (workflow completo)** que encadene, idempotente y con
  evento forense: (1) CRM `PUT historico=true` + `referencia_historico` +
  `fecha_alta_hist` (mapa de campos en `INTEGRACION §12`); (2) actuación facturable de cierre (§15); (3) Gmail: mover la
  etiqueta a `03. ARCHIVO/…/<año>/<caso>` + color (`labels.patch`, conserva hilos); (4)
  Drive: mover la carpeta a `CASOS/_ARCHIVO/…/<año>/`; (5) `_caso.md` `estado: archivado` +
  motivo + fecha en **dos niveles** (raíz + `meta`); (6) evento `archivado`. Patrón
  biblioteca (cerebro puro + orquestador fino), como `abrir_caso`.
- **70.c — Enum cerrado de motivos de archivo.** Fijar el conjunto de `referencia_historico`
  admisibles (`MAYÚSCULAS_GUION_BAJO`) para que el motivo no sea texto libre.

**Runbook operativo del archivo:** `docs/RUNBOOK_APERTURA_EXPEDIENTE.md §10`.
**Disparador de promoción de 70.b/70.c:** próximo archivo de caso que justifique el
orquestador, o decisión de Nikolai. (70.a ya promovido, ver arriba.)

## 71. Rotación y saneado de STATUS.md (fase C de gobernanza de planificación)

**Hecho (D1+D3).** Rotados los 126 bloques de cierre a `docs/bitacora/2026.md`
(STATUS 506→268 líneas; aviso E1 en silencio) + convención fijada: los cierres
nuevos van a `docs/bitacora/AAAA.md`, no al top de STATUS (Protocolo de cierre de
`STATUS.md` + `CLAUDE.md §Cierre`). Se descartaron spec y plan por sobreingeniería
(era mover markdown); ejecutado lean directo.

**Diferido (D2) — prosa→puntero.** Colapsar las 3 secciones de STATUS que aún
duplican `ARQUITECTURA.md` (`Arquitectura v2`, `Estructura de carpetas`,
`Arquitectura multi-expediente`) a punteros, con la regla verificar-antes-de-colapsar
(migrar lo único, cero pérdida). Cierra los Drifts #3/#4 de
`GOBERNANZA_FUENTES_VERDAD.md`. **Disparador:** cuando esa prosa muerda (un dato
desincronizado respecto a `ARQUITECTURA.md`/`config.py`).

## 72. Deudas de la gobernanza de la planificación (huecos post-fase-B/C)

Anotados 2026-07-18 al valorar la mejora conjunta de PLAN.md / MEJORAS / STATUS.
Ninguno bloquea; promover por disparador concreto.

- **La cola de PLAN.md se desincroniza sin aviso.** Un ítem mergeado que sigue en la
  tabla de cola priorizada no lo detecta el guardarraíl E1 (solo vigila tamaño /
  ✅-sin-colapsar / ledger>30). Pasó con B5 (PR #74): la fila #1 quedó obsoleta al
  instante y se corrigió a mano. **Disparador:** si una fila de cola vuelve a quedar
  obsoleta sin avisar → extender E1 a "fila cuyo destino ya está en `## Cerrados`".
- **Anclas de la cola frágiles.** Los enlaces de la tabla son slugs largos de GitHub;
  renombrar un encabezado `[SIGUIENTE-*]` rompe el enlace en silencio. **Disparador:**
  un enlace roto detectado → guard de anclas, o enlazar por tag en vez de slug.
- **Asimetría de `MEJORAS_FUTURAS.md`.** PLAN.md tiene cola + ledger + guardarraíl;
  este fichero no: ~2.700 líneas, ~25 entradas resueltas expandidas inline, "orden por
  prioridad operativa" sin mecanismo, y E1 no lo vigila. **Disparador:** cuando MEJORAS
  moleste de leer → mismo tratamiento lean (colapsar las resueltas a un ledger).

## 73. Intake de facturas desde `contabilidad@tyukhay.legal` (proveedores → Facturas recibidas; procuradores → gestor documental del expediente)

Anotado 2026-07-19 (idea de Nikolai). **Hermano del intake de procuradores**; reutiliza el mismo
mecanismo de correo del CRM (SSO del webmail + plugin Roundcube de relate/adjuntar,
`INTEGRACION_SUDESPACHO §10.10` y §14.5). Cruza **FeesDefender** (expedientes) y **El Contable**
(facturas recibidas).

**Flujo previsto.** A `contabilidad@tyukhay.legal` llegan las facturas de **proveedores** y de
**procuradores** (factura en PDF adjunta). El robot las clasifica y enruta:
- **Facturas de proveedores** → módulo **Facturas recibidas** del CRM (contabilidad del despacho).
- **Facturas de procuradores** (gastos del caso, **pagados por el cliente**) → **gestor documental del
  expediente** correspondiente (mismo relate/adjuntar que el intake de procuradores).

**Piezas.** (a) clasificar proveedor-vs-procurador y, si es de procurador, emparejar con el expediente
(matcher tipo F1 por referencia/importe); (b) alta en **Facturas recibidas** (`facturas_recibidas`,
enums en `INTEGRACION_SUDESPACHO §14.4`) — camino **distinto** del plugin Roundcube (es alta de factura
en contabilidad, no un relate); (c) para procuradores, el relate/adjuntar al gestor documental ya está
diseñado (F3 del intake de procuradores).

**Disparador para promover:** decisión de Nikolai de construirlo, o cuando el volumen de facturas
manuales moleste. Hoy: **solo anotado.**

## 74. `expedientes-xl`: descubrimiento del oracle perezoso (badge `failed` cosmético en Claude Desktop)

> ✅ **RESUELTO 2026-07-20 (PR pendiente).** Causa CONFIRMADA (ya no conjetura) y arreglo construido:
> `main()` ahora usa `oracle.LazyOracle`, que difiere `descubrir_cuentas` al primer uso del oráculo
> (dentro de una tool, fuera del handshake); `initialize` responde al instante. TDD: test unit del
> `LazyOracle` (no escanea en construcción / escanea una vez / delega / thread-safe bajo concurrencia) +
> `test_main_no_escanea_las_bd_antes_de_run` en `tests/test_expedientes_xl_wrapper.py`.
> **Evidencia de la causa (esta sesión):** (1) `mcp.log` — el `initialize id=0`→`id=0 result` tardó **8,1 s**
> y **10,8 s** en arranques reales del 19/07; (2) medición directa — `descubrir_cuentas` = **2,2 s en
> caliente** (más en frío, cuando DriveFS aún indexa), bloqueando antes de `.run()`; (3) `server.py:main`
> escaneaba síncrono antes de `build_server(...).run()`. Explica la **intermitencia**: `G:`/`H:` frías al
> arrancar → `failed`; calientes → conecta. **Despliegue:** la extensión `.dxt` corre el código VIVO del
> repo (`-m expedientes_xl.server`, `PYTHONPATH=…\FeesDefender\plugins`), así que basta **mergear a `main` +
> `git pull` en la raíz + reiniciar Claude Desktop** (sin reempaquetar `.dxt`). El bundle de Claude Code
> (copia cacheada del plugin) coge el fix con un `plugin update` aparte.
>
> Bloque histórico (diagnóstico original) conservado abajo.

Anotado 2026-07-19 durante el despliegue del MCP Drive-disco. Con la extensión `.dxt` instalada, el
panel **Ajustes → Desarrollador** de Claude Desktop marca `expedientes-xl` como **`failed`** aunque las
tools **funcionan** (verificado en vivo: `list_dir` G:/H:, poda Tier 0; el panel **Conectores** lo marca
✓). Causa: `main()` de `plugins/expedientes_xl/server.py` hace el **descubrimiento del oracle**
(`oracle_module.descubrir_cuentas` sobre las BD DriveFS de G: **y** H:) **antes** de `build_server(...).run()`
(~2-3 s). El **health-check** de Claude Desktop probablemente expira antes de esa respuesta inicial y marca
`failed`; las llamadas reales a tools (posteriores) sí funcionan. Es **cosmético** (no bloquea), pero
ensucia el panel y puede inducir reinicios innecesarios (parte del dolor de esta sesión).

**Arreglo propuesto (si molesta):** hacer el descubrimiento del oracle **perezoso** — que `main()`
arranque el server (`run()`) de inmediato y difiera `descubrir_cuentas` a un hilo de fondo o a la primera
tool que necesite el oracle (las guardas de hidratación degradan con gracia si el oracle aún no está: la
política ya es fail-closed/COLD ante desconocido). Así `initialize` responde al instante y el health-check
pasa a verde. **No confirmado** que sea el health-check (no se leyó el timeout exacto del panel); verificar
antes de construir. **Disparador:** que el `failed` estorbe de verdad, o al retomar los pasos 5-7 del
despliegue.

## 75. Sala de lectura como consumidor de la capa «procesado» (MD fiables → OCR-soporte → crudo)

> ⚠️ **[PROMOVIDO PARCIALMENTE → `PLAN.md`, 2026-07-27].** El spec que materializaba este ítem se
> **re-tajó en tres slices** tras dos revisiones adversariales (ver
> `docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md`):
> la **granularidad** (un documento por hilo, no por mensaje) se promueve como
> `[SIGUIENTE-SALA-HILOS]` en `PLAN.md`; el **consumo de las fuentes atomizadas** —el corazón de este
> ítem— sigue **sin promover** y vive ahora en **`#86`** con sus requisitos de entrada; la
> **unificación del motor OCR** de adjuntos, en **`#87`**. Este bloque se conserva porque la
> arquitectura y los criterios de copia que cerró Nikolai el 2026-07-19 siguen vigentes como base de
> `#86`.

**Origen (2026-07-19, fase 2 del despliegue MCP).** Al migrar `organizar-sala-lectura` a v1.8, Nikolai
señaló que la **skill re-procesa el crudo** para clasificar, cuando el **motor core deprecado** clasificaba
leyendo los **MD fiables** (`core/sala_lectura.py:13-14` «Claude rellena la worklist leyendo los `MD/` en
claro»; `core/local_organizer.py` sobre `06_Anonimizado/*.md`). La skill (desde v1.3) se desvió a la
extracción del conector de Drive; la v1.8 solo dejó el MD como apoyo condicional. Este ítem **eleva el MD a
fuente primaria** y reorienta la skill.

**Decisión de arquitectura — CERRADA por Nikolai 2026-07-19:** la sala de lectura pasa de *re-procesador del
crudo* a **consumidor/clasificador de la capa «procesado»** (sala de máquina + atomizadores por fuente).
Alinea con el **Motor Documental #48** (registro único de caso) y con la **Cronología Unificada** (capa sobre
los atomizadores); no es un parche a la skill, sino ponerla en la arquitectura de dos capas ya decidida.

**Jerarquía de fuentes de CLASIFICACIÓN — dependencia BLANDA (CERRADA):**
1. **MD fiable** (primaria).
2. **OCR-soporte** (MD dudoso) como pista.
3. **Crudo** (visión/bytes) solo en casos no claros.
Blanda, **no dura**: si no hay MD, cae a crudo. Una dependencia dura (exigir MD) sacaría a la sala de lectura
de **Cowork puro-nube** (el OCR/atomización son locales) y rompería el uso multiusuario nube que la motivó.

**Fuente fiable POR TIPO de fuente:**
- **Email** → `01_Procesado/Emails/` (`core/email_atomize`): mensajes MD + adjuntos deduplicados + su
  `.contenido.md` + autoría/inline (Capa B). **NO** la sala de máquina (trata el `.eml` grueso = 1 MD).
- **WhatsApp** → atomizador WhatsApp (`core/whatsapp_atomize`).
- **Documentos** (PDF/imagen/office) → `01_Procesado/02_Sala de máquina/03_MD/`.
- **Fotos / señal visual** → crudo/nombre (nunca MD).

**Evaluación de fiabilidad — YA montada (no hay que construirla):** la señal vive en el **frontmatter de cada
`03_MD/{slug}.md`** (`core/sala_maquina.py::_escribir_md`): `ocr_quality` (`ok`|`low`|`empty`), `ocr` (bool:
`false`=extracción nativa determinista / `true`=OCR), `chars`, `text_sha256`. La calcula
`ocr_quality(text, n_pags)` (`core/sala_maquina.py:86-100`) con tres señales deterministas y explicables:
`_MIN_CHARS=40` (documento → `empty`), `_MIN_DENSIDAD=40` char/pág (→ `low`), `_MAX_GIBBERISH=0.40` (>40% de
tokens sin vocal, spa/cat/rus incl. cirílico → `low`). **Frontera de la jerarquía:** *fiable* = `ocr_quality
== "ok"` (dos grados: `ocr:false`+`ok` = máxima confianza; `ocr:true`+`ok` = OCR fiable); *soporte* = `low`/
`empty` (listados en `_cobertura.md`, dudosos primero). La señal **viaja EN el MD** → la sala de lectura la
lee directa, sin consultar `_cobertura.json`. **Limitación:** `ocr_quality` mide densidad+ruido, **no
corrección semántica** (un OCR denso con errores de carácter pasa como `ok`) → basta para clasificar
CATEGORÍA; para datos exactos (importes, fechas) ir a la fuente (eso es viabilidad, no la sala).

**Criterio de COPIA a la sala — CERRADO por Nikolai 2026-07-19** (qué fichero queda en
`01_Procesado/Sala lectura/` con nombre canónico; ortogonal a qué se LEE para clasificar):
- PDF **nativo** / `.docx` / `.txt` / **foto** / imagen → **crudo**.
- PDF/imagen **escaneada** → **OCR** (`01_OCR/*.pdf` = original + capa de texto, buscable; superior al
  escaneado ciego sin perder fidelidad visual).
- **Email** → **MD legible** de `email_atomize` + adjuntos originales (el `.eml` es custodia, no lectura).
- **El MD suelto NUNCA sustituye** a un documento visual (firmas/sellos/fotos/tablas).

**Ampliación del `_MANIFIESTO.md`:** procedencia **doble** — `sha256` del original en `00_Input` + `sha256`
del artefacto copiado + de qué se derivó (hoy guarda un solo `sha256`). Custodia intacta: el original nunca
se toca (su `sha256` está en `_intake_log.jsonl`); la sala es vista derivada, no prueba.

**Fuera de alcance / a resolver en el spec:** (a) **granularidad del email** (1 documento por email/hilo vs
por mensaje atómico); (b) **dueño del OCR de adjuntos** (`email_atomize`/`adjuntos_contenido` vs sala de
máquina — evitar partir el bundle-email); (c) **frontera con la Cronología Unificada** (ambas serían
consumidoras de átomos/MD → no duplicar la capa de adaptadores); (d) **orden de pipeline** (atomizadores/
máquina → lectura → viabilidad).

**Relación:** #48 (Motor Documental), Cronología Unificada (`docs/superpowers/specs/2026-06-25-cronologia-
unificada-design.md`), #68 (cableado del pipeline de correo), v1.8 de `organizar-sala-lectura` (MD como
apoyo condicional — este ítem lo eleva a primario).

**Disparador de promoción a `PLAN.md`:** escribir el spec (`writing-plans`) cuando se decida construir. La
**arquitectura y los criterios ya están CERRADOS** (decisión Nikolai 2026-07-19); falta el spec (granularidad
email + frontera Cronología + orden de pipeline).

**Exploración pre-brainstorming (opciones + trade-offs + preguntas para el diálogo):**
`docs/superpowers/2026-07-19-sala-lectura-procesado-exploracion.md`. Hallazgos clave: (1) es
**MATERIALIZACIÓN**, no arquitectura nueva (Cronología §9 y #48 ya la modelan; los atomizadores + sala de
máquina YA están construidos) → el trabajo es el **contrato de consumo a nivel-fichero** + el cableado (#68);
(2) **decisión-madre pendiente:** `#56` (revivir `core.sala_lectura` determinista + tool MCP) **vs** `#75`
(skill prompt-driven que consume MD); (3) el criterio de copia de artefactos derivados **rompe la
idempotencia por sha256 actual** (hay que reescribir el algoritmo de skip, no solo añadir columna al
`_MANIFIESTO`); (4) piloto propuesto W-02VND1 como gate anti-spec-dormido.

**Anotación 2026-07-23 (W-02VND1) — decisión-madre RESUELTA.**
`docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-design.md` (PR #124, mergeado a `main`
en `55df077`) descarta `#56` a favor del camino de esta entrada (skill + script embebido) — ver anotación
en #56. Ese mismo spec queda, a su vez, **pendiente de adjudicar** 3 hallazgos P0 de su propia revisión
adversarial antes de poder implementarse; su hallazgo P0.1 confirma, independientemente y el mismo día, el
mismo hueco de "idempotencia por sha256"/inventario reconciliado señalado en (3) — esta vez en
`email_atomize` (`corpus.jsonl` sin contrato de cobertura contra `00_Input`). W-02VND1, el piloto propuesto
en (4), es también el caso sobre el que hoy se midió en vivo el coste de re-hashear `00_Input` en
`sala_maquina.py` (#48/#84) — misma familia de carencia, un escalón antes en el pipeline.

## 76. Cuestión ABIERTA: ¿reañadir `read_media_file` (lectura visual directa) a `expedientes-xl`?

**Estado: NO decidido — brainstorming (Nikolai + Claude, 2026-07-19). No es un descarte.** El consolidado
retiró `read_media_file` en la migración v1.8 (los binarios no vuelven al modelo; se manejan server-side). Se
debate reañadir una tool que entregue el binario (imagen/PDF/página) al modelo para **visión directa**.

**Clave: son DOS casos de uso distintos y no hay que confundirlos.**
1. **Montar la sala de lectura** (clasificar el intake): aquí manda la jerarquía de #75 (MD fiables →
   OCR-soporte → crudo). Para esto `read_media_file` **no** aporta velocidad (la visión es más lenta que leer
   un MD) ni fiabilidad (el OCR determinista + `ocr_quality` es más fiable que la visión estocástica).
2. **Lectura rápida / hojeo ad-hoc del expediente SIN abrir los ficheros** (consulta ágil del abogado): aquí
   el punto de Nikolai — **sin `read_media_file`, `expedientes-xl` es una herramienta "ciega"** a todo lo
   visual (imágenes, escaneados sin OCR). Para "ver" un documento habría que haber corrido antes la sala de
   máquina (OCR local); la visión directa daría acceso inmediato a cualquier documento, **independiente de la
   sala de máquina**.

**A favor de reañadirlo:**
- **Cobertura de acceso:** leer/ver CUALQUIER documento directamente, sin depender de que exista OCR previo.
- **Independencia de la sala de máquina:** hojear el expediente sin ejecutar OCR local (que no corre en Cowork
  puro-nube).
- En **Cowork puro-nube** (sin OCR local, sin `Read` nativo de Claude Code) es la **única** vía de ver un
  escaneado/foto → hoy ahí el lector es ciego.

**En contra:**
- Para *clasificar* (montar la sala) no aporta velocidad ni fiabilidad; la vía OCR/texto es superior.
- **Vía menos fiable:** visión estocástica, sin artefacto reutilizable, sin `ocr_quality`, sin traza.
- **Mezcla de capas:** `expedientes-xl` es lector de bytes/texto + operador; la interpretación visual vive en
  su capa (OCR). Delegar lo visual es coherente con delegar los `.gdoc`/`.gsheet` a `google-despacho`.
- **RGPD:** reabre "binarios con PII al modelo", cerrado a propósito en el consolidado.
- En **Claude Code (Modo 2)** el `Read` nativo ya da visión → el hueco real es solo **Cowork-vía-`expedientes-xl`**.

**Tensión central (sin resolver):** *cobertura de acceso + independencia de la sala de máquina* (a favor)
vs. *separación de capas + fiabilidad + RGPD* (en contra). Depende de cuánto pese el caso de uso "hojear/leer
rápido el expediente sin OCR previo", sobre todo en Cowork nube.

**Términos medios a estudiar (no decididos):**
- Una tool acotada tipo **`render_page(path, n, dpi_bajo)`** que devuelva SOLO una página a baja resolución
  para hojeo (no el binario completo) → acota coste y superficie PII vs. `read_media_file` pleno.
- Restringir la visión a **bajo demanda explícita** (nunca en barridos/montaje automático) con aviso RGPD.
- Aceptar el hueco y responder con **"corre la sala de máquina"** (mover a local / disparar OCR) como vía
  robusta, dejando la visión fuera.

**Relación:** #75 (jerarquía de fuentes de la sala de lectura), migración v1.8 de `organizar-sala-lectura`
(que retiró `read_media_file`). **Disparador para retomar:** que la lectura ad-hoc de escaneados/fotos sin OCR
previo (esp. en Cowork nube) se vuelva un dolor real, o decisión de Nikolai.

## 77. Gobernanza de handoffs (creación, ubicación única y ciclo de vida)

**Estado: ✅ APROBADA E IMPLEMENTADA (2026-07-19).** Regla escrita en `GOBERNANZA_FUENTES_VERDAD §5` +
puntero en `CLAUDE.md`; 9 handoffs migrados a `docs/superpowers/handoffs/` con `estado:` en el frontmatter
(los 7 stress-tests de Cronología quedan en `specs/cronologia-handoffs/`, excepción documentada); `INDICE
§Handoffs` = vista derivada. (Diagnóstico y regla originales, conservados abajo.)

**Diagnóstico (verificado 2026-07-19):** los ~12 handoffs viven repartidos sin convención —
`docs/superpowers/handoff-YYYY-MM-DD-<tema>.md` (mayoría), `docs/superpowers/specs/cronologia-handoffs/`
(otra nomenclatura `handoff_FXDY_...`), `docs/prompt_handoff_expedientes_seguros.md` (suelto), y alguno en
`scratchpad` (efímero, se pierde). `GOBERNANZA_FUENTES_VERDAD.md` y `CLAUDE.md` **no los mencionan**; la
sección `## Handoffs` de `docs/INDICE.md` cataloga solo 2 de ~12 (incompleta y desactualizada). No hay
ciclo de vida ni distinción handoff (andamio efímero) vs spec/plan (SSOT durable).

**Regla propuesta (proporcionada, YAGNI):**
- **Qué es:** documento **efímero** de traspaso de contexto para arrancar una tarea en otra sesión/agente.
  **No es fuente de verdad**: su contenido durable se promueve a spec/plan/runbook/código.
- **Ubicación única:** `docs/superpowers/handoffs/`. Lo que deba sobrevivir a la sesión va al **repo, nunca
  a `scratchpad`** (scratchpad solo para andamios de usar-y-tirar intra-sesión).
- **Nombre:** `handoff-YYYY-MM-DD-<tema-kebab>.md`.
- **Estado en el frontmatter (hogar único):** `estado: activo | consumido | historico` + `creado`,
  `origen`, `destino`, `consumido_por` (spec/plan/PR/runbook donde acabó su contenido durable).
- **Ciclo de vida:** `activo` (creado, sin consumir) → `consumido` (la tarea arrancó y su contenido durable
  ya vive en su SSOT; se apunta `consumido_por`) → `historico` (se conserva por trazabilidad). El `INDICE`
  §Handoffs pasa a **vista derivada** (lista/enlaza), no hogar del estado. Un `activo` abandonado se borra
  en un cierre; los `consumido/historico` se conservan con su puntero (como el ledger `## Cerrados`).

**Acción de formalización (al aprobar):** (1) escribir la regla en `GOBERNANZA_FUENTES_VERDAD.md` +
puntero en `CLAUDE.md`; (2) crear `docs/superpowers/handoffs/` y migrar los handoffs existentes con su
`estado`; (3) convertir `INDICE.md §Handoffs` en vista derivada completa. Docs-only, rama+PR.

**Disparador:** decisión de Nikolai; encaja de forma natural en la sesión de gobernanza/triaje de `PLAN.md`
(el primer handoff que estrena la nomenclatura es `docs/superpowers/handoffs/handoff-2026-07-19-triaje-plan.md`).

## 78. Split de bundles — merge N→1 en `apply` + auto-detección de conjunto  [follow-on de F2]

**Disparador:** cierre de la Fase F2 (integración del split en la Sala de máquina). Deferido consciente (YAGNI).

Dos refinamientos que F2 dejó fuera:
- **Merge N→1 dirigido por el manifiesto:** hoy el letrado puede fusionar segmentos DENTRO de un bundle
  editando `_segmentacion.md`, pero falta el camino inverso explícito (unir varios PDFs SUELTOS en un mismo
  documento lógico) apoyándose en `role_in_bundle`/`fuentes` de `DocLogico`, que ya está merge-ready.
- **Auto-detección de conjunto (`conjunto_detector`):** detectar que N ficheros sueltos de `00_Input` forman
  un mismo documento (p. ej. páginas fotografiadas por separado) y proponerlos como bundle.

El corte 1→N (el caso real de VALERO) ya lo cubre F2; esto es comodidad.

## 79. Consumo de documentos lógicos (split) por `organizar-sala-lectura`  [follow-on de F2]

**Disparador:** cierre de la Fase F2. La Sala de máquina ya emite un MD por documento lógico bajo
`02_Documentos/{bundle}/`, con `parent_slug`/`tipo`/`paginas` en la cobertura. Falta que
`organizar-sala-lectura` los consuma como **documento compuesto** (subcarpeta fechada) en vez de tratar el
bundle como un solo fichero: leer la cobertura por documento lógico, respetar el `tipo` clasificado y nombrar
canónicamente cada segmento. Contrato de salida documentado en el §9 del spec del split
(`docs/superpowers/specs/2026-07-14-split-sala-maquina-design.md`).

## 80. Verificar dedup de `sync_sudespacho pull` contra documentos ya presentes en «05. Procedimiento»

**Disparador:** ninguno todavía — anotado sin promover, a la espera de un caso real llevado con
el flujo que lo activa.

Contexto: en W-02VUDR, `00_Input/sudespacho_499/demanda/` trajo del CRM una demanda de diligencias
preliminares + 12 anexos (`doc_NN_*`) sin agrupar como bundle (ver `core/conjunto_detector.py`, cuyo
regex `\bD\s*\d+[\s\w]*-` no casa con `doc_NN_`). Se decidió NO construir un detector de bundle para
este patrón (bajo ROI para un solo expediente); la vía elegida es de proceso, no de código: cuando el
despacho redacte el escrito + monte sus anexos en una carpeta de Procedimiento en Drive **antes** de
subirlos al CRM, la versión bien organizada existe desde el origen y el CRM es solo su espejo.

La suposición pendiente de comprobar: que `sync_sudespacho.pull_expediente`/`pull_expediente_v2` no
re-descargue como sueltos esos mismos documentos si ya están presentes en Procedimiento. Hoy el dedup
de `pull_expediente*` es por marcador `.pulled`/`--incremental` **keyed por `doc_id` del CRM**, no por
contenido — no hay comprobación cruzada contra otras rutas del caso. Si en el futuro se da el caso real
(escrito+anexos montados en Procedimiento antes de subir al CRM) y el pull los vuelve a traer sueltos
sin agrupar, esto se promueve a `PLAN.md` con ese caso como disparador; si no, queda como nota.

---

## 81. Bug latente: otros scripts CLI pueden componer rutas sin resolver W-code (`case_locator.resolve_ref`)

**Disparador:** ninguno todavía — anotado tras el fix de PR #117 (2026-07-22), sin promover a
`PLAN.md` a la espera de confirmar cuáles de estos CLI se usan realmente con W-code puro.

Contexto: PR #117 corrigió `scripts/sala_maquina.py` (`plan`/`apply`/`reforzar`), que pasaba
`case_id` directo a `caso_path()`/`path_for()` sin resolver un W-code primero — `path_for` solo
entiende layout flat/ciudad por NOMBRE DE CARPETA, nunca `meta.id_go`. Síntoma real (W-02ZIIF,
2026-07-22): un W-code puro caía al fallback flat inexistente y la corrida seguía en silencio con
plan vacío ("0 documentos" reportado como éxito), creando ahí una carpeta fantasma.

`docs/ARQUITECTURA.md` (fila `core/casos/case_locator.py`) ya señalaba como candidatos a auditar
"toda llamada que componía `settings.casos_root / case_id`" en `core/case_manager.list_cases`,
`core/config.caso_path` y `scripts/{audit_referencias_casos,scheduled_sync,sync_sudespacho}.py` —
nunca se llegó a auditar. Revisión rápida (grep `case_id: str`/`--case`/`--expediente` en
`scripts/*.py` + `resolve_ref\(` en el mismo fichero) añade un candidato no listado ahí:
`scripts/migrar_layout_intake.py` (`case_id: str` como argumento directo, sin `case_locator` en el
fichero). `scripts/sala_lectura.py` (múltiples comandos `--case`) queda fuera de prioridad: es CLI
**deprecado** (`ARQUITECTURA.md` fila `core/sala_lectura.py`, superado por la skill
`organizar-sala-lectura` v1.3).

Pendiente: para cada candidato, confirmar si su contrato documentado es "case_id completo" (p. ej.
`scripts/migrate_05crm_buckets.py` lo dice explícitamente en el `--help` — no es un bug, es diseño)
o si de verdad se usa/se espera usar con W-code puro (candidato real a la misma clase de bug). Si se
confirma un caso real, promover a `PLAN.md` con ese caso como disparador, aplicando el mismo patrón
de fix (`case_id = case_locator.resolve_ref(case_id)` antes de derivar cualquier ruta + fallo en alto
si la ruta resuelta no tiene `00_Input`).

## 82. Split de bundles — `num_doc` de portada fragmentada solo se busca en `lineas[:3]`

**Disparador:** ninguno todavía — anotado tras el fix de `num_doc` fragmentado en
`core/anon/separar.py` (W-02ZIIF, 2026-07-22), sin promover a `PLAN.md` a la espera de un caso real
donde el número quede más allá de la 3ª línea reconstruida.

Contexto: el fix de W-02ZIIF añadió `PATRON_NUM_DOC_FRAGMENTADO` + un fallback en `detectar_tipo`
que une las líneas cortas de portada para reconocer "Documento anexo n.º 2" cuando el marcador y el
número quedan repartidos entre líneas reconstruidas distintas (portada a dos líneas, o interlineado
irregular de origen que fragmenta lo que visualmente es una sola línea). El fallback, igual que el
bucle original que complementa, solo mira `lineas[:3]` — la misma ventana que usa la clasificación de
TIPO (`texto_inicio`/`texto_inicio_titulo`). Si la fragmentación es tan agresiva que el dígito acaba
en la línea 4 o 5 (de las 5 que `extraer_primeras_lineas` ya extrae), ni el bucle original ni el
fallback lo ven, y `num_doc` sigue `None` para esa portada.

Pendiente: si aparece un caso real donde esto importe, extender **solo el fallback** (nunca el bucle
original ni la ventana de TIPO) para considerar las 5 líneas ya disponibles en `lineas`, no solo las
3 primeras. No ampliar la ventana de `texto_inicio`/`texto_inicio_titulo`: esa ventana corta es la que
evita que una mención de "anexo"/"contrato" en el cuerpo de una demanda dispare un tipo falso, y
ampliarla reabriría ese riesgo. Test de referencia: `tests/test_anon_separar.py::TestNumDocPortadaFragmentada`.

---

## 83. Confirmar `POST /api/expedient/convert/{id}` (extrajudicial → judicial)

**Disparador:** ninguno todavía — anotado sin promover. Sería relevante cuando un caso con
ficha extrajudicial YA VIVA escale a judicial (demanda admitida) y se quiera evitar crear un
expediente judicial desconectado del histórico.

**Estado actual.** `docs/INTEGRACION_SUDESPACHO.md §6.2` documenta el endpoint
(`POST /api/expedient/convert/{id}`) pero marcado "pendiente confirmar payload y respuesta
con una conversión real" — nadie lo ha probado en vivo. En W-02ZIIF (2026-07-22) no aplicó
porque el expediente extrajudicial ya se había borrado a mano antes de la escalada a
judicial, así que se creó un judicial nuevo desde cero en su lugar.

**Mejora propuesta.** Probar el endpoint contra un expediente extrajudicial desechable
(mismo patrón usado para confirmar el mecanismo de Juzgado, `INTEGRACION_SUDESPACHO.md
§12.5`): crear un extrajudicial de prueba, invocar `convert`, inspeccionar la respuesta y
el estado resultante, documentar el payload real. Si funciona como cabe esperar, envolver
en `convert_expediente_a_judicial()` (`core/sudespacho_create.py`).

**Justificación de no aplicarlo ahora.** Sin caso real que lo necesite hoy — W-02ZIIF ya
resolvió su escalada creando un judicial nuevo (el extrajudicial ya no existía). Probar un
endpoint sin confirmar contra el CRM real, aunque sea con un expediente desechable, merece
su propia sesión dedicada, no un añadido de paso.

**Coste estimado.** ~30 min de prueba en vivo (patrón ya validado hoy con Juzgado) + un
wrapper pequeño en código si el resultado es limpio.

---

## 84. Bug latente: `sala_maquina apply` reintenta indefinidamente documentos no resueltos (sin límite ni backoff)

**Disparador:** ninguno todavía — anotado en vivo durante el intake de la querella penal de W-02VND1
(2026-07-23): mensajes `[tesseract] Error during processing.` durante una corrida que solo tenía 43
ficheros nuevos que procesar correspondían a documentos antiguos ya fallidos el 9-jul (vía Cowork), no
al lote nuevo — sin promover a `PLAN.md` a la espera de que el letrado decida si conviene un límite
explícito o solo visibilidad. Relacionado: #48 (misma corrida, hallazgo hermano sobre `inventariar()`),
#58 (cobertura acumulativa, mismo mecanismo de estado).

**Estado actual.** `scripts/sala_maquina.py::apply` solo añade un sha a "procesado"
(`_exitosos_por_bundle`, línea 83) si su resultado fue `ok`/`low`; un documento en
`error`/`empty`/`sin_soporte` nunca entra en `_sala_maquina_state.json` → `plan()`
(`core/sala_maquina.py`, línea 152) lo vuelve a marcar `skip=False` en TODA corrida futura sin
`--force`, reintentando OCR real sin límite de intentos ni backoff. En W-02VND1, de ~672 ficheros
antiguos en `00_Input/`, solo 503 shas físicos constan como "procesados" en
`_sala_maquina_state.json` — el resto (documentos genuinamente irrecuperables: cifrados, corruptos,
formatos sin soporte) se reintenta en cada `apply`, indefinidamente.

**Mejora propuesta.** Decidir entre (a) un contador de intentos por sha con tope (p. ej. 3) tras el
cual se marca `descartado` explícito en la cobertura sin más reintentos automáticos, o (b) mantener
el reintento infinito pero hacerlo VISIBLE antes de correr (`plan` podría listar "N documentos con
fallo persistente, reintentados de nuevo"). Revisar también por qué falta `_cobertura.json` en
W-02VND1 (solo existe `_sala_maquina_state.json`) pese a que el código de `apply` sí lo persiste
(línea 179) — probablemente la corrida del 9-jul (vía Cowork) usó una versión del pipeline anterior a
que se introdujera ese fichero, o no se copió al Drive en el checkin correspondiente; sin ese
fichero no hay forma de ver, sin re-ejecutar, cuáles de los ~169 documentos pendientes fallan y por qué.

**Justificación de no aplicarlo ahora.** Sin decisión de Nikolai sobre (a) vs (b); construir
cualquiera de las dos sin esa decisión es apostar el diseño. El caso concreto (W-02VND1) no está
bloqueado por esto — solo es más lento de lo necesario.

**Coste estimado.** (a) contador+tope: ~1h (campo nuevo en `DocCobertura`, chequeo en `plan()`,
test). (b) solo visibilidad: ~30 min (contar en `plan`, sin cambiar `apply`).

## 86. Consumo de las fuentes atomizadas por la sala de lectura (Slice 2 del re-tajo)  [ex-`#75`, parte de consumo]

**Origen.** Es el objetivo original del spec
`docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-design.md`, que el **re-tajo del
2026-07-27** dejó fuera: que `organizar-sala-lectura` deje de releer el `.eml` crudo cuando el caso ya
tiene `core/email_atomize` corrido, y aproveche el dedup de adjuntos, la limpieza de MIME/HTML y la
autoría reconstruida de Capa B. La arquitectura y los criterios de copia siguen siendo los que Nikolai
cerró el 2026-07-19 (`#75`); lo que falta es un spec que resuelva los bloqueantes.

**Requisitos de ENTRADA (no negociables — vienen de dos revisiones adversariales independientes,
adjudicadas en `…-adversarial-review.md`):**
1. **Contrato de cobertura reconciliable.** "Existe `corpus.jsonl`" NO equivale a "todo cubierto".
   La cobertura se lee de `_registro.json.eml_procesados` (`core/email_atomize/ids.py:77-91`), con el
   caveat de que la llave es el **nombre** del fichero y `corpus.jsonl` **no** emite `eml_origen`
   (`corpus.py:21-46`) → mapear un `.eml` cubierto a *su* hilo no tiene llave fuerte hoy.
2. **Capa B y el hilo vacío.** Todos los mensajes reconstruidos llevan `hilo=""` (`model.py:43`;
   `construir_b` no lo fija). Agrupar por `hilo` a ciegas fabrica un pseudo-hilo con conversaciones
   sin relación — misatribución en un expediente probatorio. Derivable en el consumidor vía
   `procedencia[].citado_en` (el portador), sin tocar el atomizador.
3. **Identidad de mensaje.** `MSG-id` está congelado por `Message-ID`, **no por contenido**
   (`ids.py:37-46`), y el contenido puede mutar por upgrade de fidelidad; el conjunto de mensajes de
   un hilo puede además **encoger** entre corridas. Cualquier mecanismo de skip que asuma lo
   contrario está roto de origen (así murió el §7 del spec anterior).
4. **Adjuntos muchos-a-muchos.** Un adjunto deduplicado por sha256 puede pertenecer a varios hilos:
   hace falta política explícita antes de reutilizar el dedup global.

**Material sin adjudicar que hay que revisar al escribir el spec** (de los 28 hallazgos del workflow
que no llegaron a verificarse por el límite de gasto): caché de `adjuntos_contenido` a versionar,
mapeo de confianza del router, adjuntos decorativos excluidos por el camino atomizado, línea meta
inicial de `corpus.jsonl`, ejecutabilidad del script en Modo 3 (nube pura), y `senales_gate` marcando
los adjuntos reutilizados como "binario opaco sin espejo MD".

**Disparador de promoción a `PLAN.md`:** un caso real donde la calidad de clasificación del correo
importe (correspondencia nuclear de activación mal categorizada por leer el `.eml` crudo, del tipo que
ya pasó en W-02VUDR) **o** decisión explícita de Nikolai. **No promover por completitud de diseño:**
el Slice 1 ya entrega la legibilidad, que era el beneficio visible.

## 87. Motor de extracción/OCR unificado para adjuntos de correo (Slice 3 del re-tajo)

**Origen.** El §8 del spec de 2026-07-23, retirado en el re-tajo del 2026-07-27 por ser un proyecto
independiente de la sala de lectura que se había colado dentro.

**El problema real.** `core/adjuntos_contenido` extrae texto de los adjuntos con Docling, un motor
**distinto** del OCRmyPDF que usa `core/sala_maquina.py`. Consecuencia: el mismo documento puede dar
texto de calidad distinta según la puerta por la que entre (suelto en Drive vs. pegado a un correo), y
Docling trae un tope de páginas que trunca en silencio los anexos largos.

**Por qué no fue un cambio de una línea** (ambas revisiones lo confirmaron): `core/anon/ocr.py::ocr_pdf`
es **PDF→PDF** (devuelve un PDF buscable y exige ruta de salida), no un extractor de texto, mientras el
router de `adjuntos_contenido` espera una `Extraccion` textual. Hace falta un **adaptador completo**
(PDF temporal → extracción → limpieza → gestión de fallos → PDF nativo / ya OCRizado → actualización
coherente de `metodo_extraccion`/`ocr_aplicado`), y además Docling es el extractor **primario** de
tipos que `ocr_pdf` no cubre, así que retirarlo sin más dejaría formatos sin cobertura. Súmese la
caché por sha256 a versionar (sin bump, los adjuntos ya procesados conservarían el texto viejo) y el
mapeo de confianza del router, que hoy depende del nombre del motor.

**Corrección de dato para el futuro spec:** la ruta del texto de adjunto **no** es
`adjuntos/<sha>.contenido.md`; el nombre real lo compone `core/adjuntos_contenido/pipeline.py:27-29`.

**Disparador de promoción a `PLAN.md`:** un adjunto largo truncado en silencio que afecte a un caso
real, o una divergencia de texto observada entre los dos caminos. **No** promover por limpieza.

## 88. Threading riguroso de correo por cabeceras RFC (`References`/`In-Reply-To`)

**Estado.** Limitación **aceptada y documentada** en el Slice 1 (spec de 2026-07-23 §5), no un bug.

`agrupar_por_hilo` (`.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:133-155`) agrupa
por **nombre de fichero** —el esquema `asunto_fecha` + sufijos `_N` que escribe `core.email_export`—
y su propio docstring ya lo declara: "heurística de nombre, no de `Message-ID`/`References` — proxy
barato, no sustituto de un threading riguroso si algún día hace falta". Consecuencia: un hilo cuyo
**asunto cambió a mitad** de conversación no se agrupa, y se reparte en varios bundles.

**Mejora propuesta.** Componentes conexos (union-find estilo JWZ) sobre el grafo
`Message-ID`/`References`/`In-Reply-To` leídos con el `email` de la stdlib — compatible con el
requisito de que los scripts de la skill sean self-contained. Resuelve además la partición
conservadora que Codex señaló como P1.2 (cadena A←B←C donde C perdió `References`).

**Coste y cautelas.** Exige leer cabeceras de **todos** los `.eml`, no de un representante por grupo:
barato en Modo 1/2 (filesystem), caro en Modo 3 (cada lectura es una descarga del conector) → habría
que degradar a la heurística de nombre en nube pura. Riesgo inverso: un cliente que referencie un
mensaje ajeno puede **sobre-fusionar** hilos distintos.

**Disparador de promoción:** un caso real donde un hilo con cambio de asunto quede troceado de forma
molesta en la sala. Hasta entonces, la heurística de nombre basta.

---

## 90. OCR ciego bajo el sello: un escaneo con pie de firma sale `ok` en `_cobertura.md` y nadie lo revisa

> **[PROMOVIDO → `PLAN.md`]** (2026-07-27). El paso 0 se ejecutó y encontró pérdida REAL y material en
> un caso vivo: en **W-02VND1** faltaba el **81-83 % del texto de las cuentas anuales 2022/2023/2024**
> depositadas en `04_Manual/MEDIDAS CAUTELARES/`. Disparador concreto cumplido → entrada en `PLAN.md`
> con referencia `MEJORAS #90`. Resultados medidos y corrección del arreglo propuesto, al final.

**Disparador:** ninguno todavía — origen en `docs/superpowers/handoffs/handoff-2026-07-27-sala-maquina-ocr-gaps.md`
(`[SM-OCR-02]`, diagnóstico de lectura hecho en Cowork durante W-02MA0R, un expediente ad-hoc fuera del
layout FeesDefender). A diferencia del handoff, lo de abajo **sí está verificado en vivo** contra
ocrmypdf 17.4.2 y contra las propias funciones del repo. Hallazgos hermanos del mismo handoff:
`[SM-OCR-01]` → #91; `[SM-OCR-03]` (bomba de descompresión PIL) **refutado**, ver el cierre de esta entrada.

**Estado actual.** Un PDF escaneado cuyo único texto embebido es el **pie de firma electrónica**
(LexNET, sellos del juzgado, cabeceras de fax) engaña a los DOS guardarraíles del pipeline, de forma
encadenada y silenciosa:

1. **Nunca llega al OCR.** `core/sala_maquina.py:516-518` decide la ruta con
   `_texto_suficiente(texto, npags)` (`core/extractor.py:125-137`): basta ≥100 caracteres totales y una
   densidad ≥40 char/pág. Un pie de LexNET real ronda los **228 caracteres por página** — 5,7× el umbral.
   El documento se clasifica "PDF digital ya buscable" y se manda por `pypdf`; OCRmyPDF no se invoca jamás.
2. **Y si llegara, `--skip-text` tampoco lo salvaría.** `core/anon/ocr.py:100-103`: con el default
   `redo_ocr=False` siempre se pasa `skip_text=True`, cuya semántica es *"skip OCR on any pages that
   already contain text"* — por página y todo-o-nada. Medido sobre una página construida a imitación de un
   documento LexNET (imagen rasterizada + sello de texto real encima): `--skip-text` devuelve **31
   caracteres** (solo el sello, cuerpo perdido); `--redo-ocr` sobre la misma página devuelve **295**
   (cuerpo recuperado).
3. **Y la red de calidad lo da por bueno.** `ocr_quality` (`core/sala_maquina.py:88-102`) promedia sobre
   el documento entero. Con el sello de 228 char/pág y **cero** cuerpo recuperado, devuelve `ok` para 8,
   20 y 40 páginas. Un documento mixto (36 páginas digitales reales + 4 escaneadas perdidas) también sale
   `ok`. Y `ok` significa que el documento no aparece en la worklist de `_cobertura.md` **ni entra en el
   filtro de `reforzar`**, que solo recoge `low`/`empty` (`scripts/sala_maquina.py:225-226`) — la única
   red de rescate por visión queda inalcanzable justo para el caso que debería rescatar.

Corrección al handoff: `--skip-text` **sí** opera por página (su título decía "a nivel de documento, no de
página"). El hueco real es **sub-página** — una página con cualquier objeto de texto se salta entera,
incluido el escaneo que lleva debajo. Nota adicional: `ocr_pdf` ya acepta `redo_ocr=True`, pero **ningún
llamador lo pasa** — `_ocr_y_extraer` invoca `ocr_pdf(entrada, ocr_out)` a pelo
(`core/sala_maquina.py:457`) y el `--force` del CLI solo invalida el caché de sha y regenera manifiestos
de split, nunca toca el modo de OCR. Hoy es código inalcanzable.

**Mejora propuesta.** En este orden, porque el paso 0 es el que decide si los demás valen la pena:

- **(0) Detector, antes que arreglo.** Auditoría read-only sobre los casos ya procesados: por cada PDF de
  `00_Input/`, marcar como sospechoso el que tenga páginas con imagen a página completa cuyo texto
  extraído sea corto y **casi idéntico entre páginas** (la firma repetida es la huella delatora). Salida:
  lista de documentos y casos afectados. No escribe nada en el expediente.
- **(1) Cambiar el default del motor a `--redo-ocr`.** No es `--force-ocr`: la librería documenta que
  *"existing visible text objects will not be changed"*, solo aplica OCR al texto que vive dentro de
  rásteres. Por tanto no reproduce el bloat de 3-10× ni la destrucción de la capa de texto real que
  obligó a abandonar `--force-ocr` (bitácora 2026-07-14, VALERO).
- **(2) Métrica por página en `ocr_quality`,** no solo la media: marcar `low` si ≥N páginas quedan bajo el
  umbral aunque el promedio pase. Es lo que rompe la dilución del punto 3.
- **(3) Relajar el gate de entrada:** `_texto_suficiente` no debería concluir "digital" cuando el texto
  por página es casi idéntico entre páginas. **[HECHO 2026-07-27, con otra forma]**: `_texto_suficiente`
  se dejó intacto (lo comparte el extractor); en su lugar, un PDF que pasa ese gate pero esconde
  páginas ciegas baja igualmente a la escalera, en modo conservador. El disparo no usa la similitud
  entre páginas sino el discriminante de página ciega, que ya estaba validado en 402 documentos.
  Sin este punto, (1) y (2) no habrían servido de nada: es el eslabón que impide llegar al OCR.

**Justificación de no aplicarlo ahora.** Cambiar el modo de OCR por defecto afecta a todos los
expedientes del despacho: `--redo-ocr` re-procesa páginas que hoy se saltan (corridas más lentas) y deja
`_sala_maquina_state.json` y las coberturas ya persistidas desalineadas con el motor nuevo, con la
pregunta abierta de qué casos re-correr. Sin el paso 0 no sabemos si esto afecta a 0 documentos o a 200,
y esa cifra es justo lo que debe decidir el alcance. Decisión de Nikolai.

**Cautela sobre el disparador.** La regla del proyecto es promover a `PLAN.md` cuando haya un caso real
que lo necesite; aquí ese criterio se muerde la cola, porque **el fallo es silencioso por construcción**:
sale `ok`, no entra en ninguna worklist, y nadie lo nota salvo que eche en falta un documento leyendo el
fondo del asunto. Por eso el paso 0 se propone como diagnóstico barato: convertir un riesgo invisible en
un número. Si el detector encuentra documentos afectados en expedientes vivos, **eso** es el disparador.

**Coste estimado.** (0) detector read-only ~1 h. (1) ~15 min de código, más la decisión de re-corrida.
(2) ~1 h (`ocr_quality` por página + tests). (3) ~30 min. Nada de esto exige tocar el split ni la sala de
lectura.

**Hallazgo hermano refutado (`[SM-OCR-03]`, bomba de descompresión).** El handoff afirmaba "grep vacío de
`PIL`/`MAX_IMAGE_PIXELS` en todo `core/` y `scripts/`" y deducía que una imagen sobredimensionada caería
en el `except Exception` genérico de `ocr.py:125-126` dejando el documento `empty` sin red. Las dos
premisas son falsas: `core/anon/imagen_a_pdf.py:43` importa PIL y llama a `Image.open()` (también
`core/local_organizer.py:179`), con lo que el guardarraíl propio de Pillow (`MAX_IMAGE_PIXELS` =
89.478.485 px) está activo; y ocrmypdf trae el suyo (`--max-image-mpixels`, "treating an image as a
decompression bomb"). Además el fallo, si ocurre, **es ruidoso**: en la ruta imagen lo captura
`core/sala_maquina.py:529` → fila `sin_soporte` con la nota "conversión a PDF falló: …", y en la ruta PDF
queda `empty` con "OCR falló: …". En ambos casos el documento aparece como no-`ok` en `_cobertura.md`,
que es el comportamiento diseñado. Es el opuesto exacto de #90: falla a la vista. No merece entrada.

### Resultado del paso 0 (ejecutado 2026-07-27) — el hueco es real y material

Detector construido y corrido en modo read-only sobre los **5 casos con Sala de máquina**
(`python -m scripts.detectar_ocr_ciego todos`): **402 documentos `ok`, 24 candidatos**. Los candidatos
se midieron re-OCR-izando y comparando contra el `raw_text/` que el expediente tiene hoy — la única
medida honesta, porque el cribado sobre-marca.

| documento (caso) | texto HOY | tras re-OCR | faltaba |
|---|---|---|---|
| Cuentas anuales **2024** (W-02VND1, `MEDIDAS CAUTELARES`) | 10.979 | 65.076 | **83 %** |
| Cuentas anuales **2023** (W-02VND1, ídem) | 10.082 | 53.857 | **81 %** |
| Cuentas anuales **2022** (W-02VND1, ídem) | 10.381 | 55.011 | **81 %** |
| Tasación TECNITASA (W-02VND1) | 46.142 | 62.711 | **26 %** |
| Exposé de propiedad (W-02XOR7) | 9.854 | 13.732 | **28 %** |
| Exposé (W-02VUDR) | 12.490 | 13.889 | **10 %** |

Los cuatro primeros están en un **caso vivo** y los tres primeros son prueba de solvencia en una pieza
de medidas cautelares. Eso es lo que convierte #90 de riesgo teórico en disparador.

**Corrección importante al arreglo propuesto: `--redo-ocr` NO basta.** Los cuatro documentos de
W-02VND1 son **AcroForm** (PDF con formulario rellenable) y ocrmypdf rechaza el modo redo sobre ellos:
`InputFileError: This PDF has a user fillable form. --redo-ocr (or --mode redo) is not currently
possible on such files`. Lo único que recuperó el texto fue `--force-ocr`, justo el modo destructivo
que se abandonó tras VALERO. El arreglo tiene por tanto que ser una **escalera con degradación
explícita**, no un cambio de bandera: (1) `--redo-ocr` por defecto; (2) si falla por AcroForm, aislar
las páginas afectadas y OCR-izarlas aparte (o `--force-ocr` acotado con `--pages`) en vez de rendirse;
(3) si nada funciona, **marcar el documento `low`** para que entre en la worklist y en `reforzar` —
nunca dejarlo `ok`. En los dos Exposés `--redo-ocr` sí funcionó sin más.

### Dos hechos del motor, verificados en vivo al construir el arreglo (2026-07-27)

Conocimiento durable sobre ocrmypdf, no estado del ítem (el estado vive en `PLAN.md`,
`[SIGUIENTE-OCR-CIEGO]`). Los dos salieron de **ejecutar**, no de leer:

1. **`--redo-ocr` es incompatible con `--deskew`** (ocrmypdf 17.4.2: *"not currently compatible with
   --deskew, --clean-final and --remove-background"*), y `deskew=True` es el default de `ocr_pdf`.
   El modo redo era por tanto inalcanzable **dos** veces: ningún llamador lo pasaba y, si lo hubiera
   pasado, habría fallado en la validación de opciones antes de OCR-izar nada. Corolario de diseño:
   como el redo obliga a renunciar al enderezado, conviene reservarlo a los documentos que **traen
   capa de texto**; el escaneo limpio no gana nada con él y sí pierde el `--deskew`.
2. **Extraer una página con `pypdf.PdfWriter` quita el `/AcroForm`** y ocrmypdf la acepta en modo
   redo. Confirmado en un test de integración contra ocrmypdf y Tesseract reales: el documento
   entero se rechaza con *"This PDF has a user fillable form"* y la misma página, aislada, se
   OCR-iza y devuelve el cuerpo. Es lo que hace viable el peldaño 2 sin tocar `--force-ocr`.

Nota de coste, por si alguna vez molesta: el motor abre ahora el mismo PDF varias veces con
`pypdf` (texto, nº de páginas, perfil de páginas ciegas y, tras el OCR, calidad por página). El
gate barato `pdf_paginas.tiene_rasteres` —solo metadato— evita el perfilado en el caso común (PDF
nativo), pero un documento con escaneos sí paga varias lecturas. Frente al coste del OCR es ruido;
si algún día se mide como problema, el arreglo es devolver texto y perfil en una sola pasada.

**Sobre la precisión del detector (leer antes de fiarse de sus cifras).** Es un cribado: de 24
candidatos, 6 resultaron pérdidas reales. Falsos positivos confirmados midiendo: DNIs y capturas de
WhatsApp (venían de `.jpg`, sin capa de texto que saltar → el OCR corrió entero), un poder notarial
(fuente con 0 chars, misma razón) y dos contratos C214 (la fuente tenía 41 chars pero el MD final
tiene 8.766: ocrmypdf sí los OCR-izó). El discriminante «la fuente tiene capa de texto» elimina el
grueso del ruido pero no sustituye a la medición; el detector sirve para **acotar a quién medir**.

---

## 91. `sala_maquina apply` no comprueba el motor OCR antes de una corrida larga

**Disparador:** ninguno — `[SM-OCR-01]` del handoff de 2026-07-27, **parcialmente refutado** al
verificarlo; queda un resto real, menor.

**Estado actual.** Lo refutado primero: el handoff sostenía que no existe chequeo de que Tesseract tenga
`spa+cat+rus`. Sí existe. `scripts/health_check.py` comprueba los binarios del sistema
(`_check_system_binaries`, líneas 104-118: tesseract, ocrmypdf, ghostscript) y los paquetes de idioma
(`_check_tesseract_langs`, líneas 121-142, exige exactamente `{spa, cat, rus}` vía
`tesseract --list-langs`), y está expuesto como `/health-check`. También es inexacto describir
`ocr_disponible()` (`core/anon/ocr.py:129-135`) como el preflight de la sala de máquina: su único
consumidor es `core/anon/api.py:263`, y el camino de sala de máquina no lo llama nunca.

Lo que sí queda en pie: `scripts/sala_maquina.py::apply` (líneas 164-171) tiene preflight para `--vision`
(`_exigir_vision_cableada`, línea 169, que aborta antes de procesar) pero **ninguno para el motor OCR**.
Con Tesseract ausente o sin el paquete de idioma, el aislamiento por documento de `ejecutar`
(`core/sala_maquina.py:511`) hace lo que debe —no tumbar el lote— con el efecto perverso de que la
corrida recorre `00_Input/` entero y termina "correctamente" con la cobertura completa en `empty` /
"OCR falló". En un caso grande eso son horas antes del primer síntoma (referencia de escala: ~672
ficheros en W-02VND1). Compone con #84: al no ser `ok`/`low`, ninguno entra en
`_sala_maquina_state.json`, así que la corrida siguiente los reintenta todos otra vez.

**Mejora propuesta.** En `apply`, simétrico con el preflight de `--vision`: si el plan trae algún
documento por ruta `pdf` o `imagen`, comprobar **una vez** que el binario Tesseract responde y que los
idiomas pedidos están instalados, y abortar con mensaje accionable (remitiendo a `/health-check`) en vez
de procesar el lote. Extraer el chequeo de `health_check.py` a un helper reutilizable en lugar de
duplicar la lógica.

**Justificación de no aplicarlo ahora.** Nadie está bloqueado: el entorno del PC está bien instalado y
`/health-check` ya cubre el diagnóstico cuando se sospecha. Esto es conveniencia —fallar en dos segundos
en vez de en dos horas—, no corrección. Su valor real aparece en máquina nueva o tras un cambio de
entorno.

**Coste estimado.** ~30 min: helper reutilizable extraído de `health_check.py`, llamada desde `apply`, y
un test con el binario mockeado.

## 92. Integridad del manifiesto de intake: entradas de un expediente ajeno + evento de saneamiento

**Anotado 2026-07-27**, a raíz del saneamiento de `W-02MA0R` (acta en el `_snapshot/` del caso).

**Lo que pasó.** El `00_Input/_intake_hashes.json` de `W-02MA0R` acumuló **31 entradas del
expediente CRM 649**, que es otro caso (`BaRR3`, `W-030LFT`) y era el **banco de pruebas** del intake
judicial (`PLAN.md:911`). El log lo fecha: `2026-06-12T16:27:55`, `pull_crm` con
`expediente_id: 649` y `documents_written: 31` **contra la carpeta de este caso**. Los ficheros se
retiraron luego, pero las entradas quedaron porque `reconcile()` conserva a propósito las que no
tienen primary vivo. Resultado: 92 entradas de las que solo 61 eran del caso, con nombres de fichero
de un tercero —incluido un nombre de pila— en el fichero de control de otro expediente.

**Dos huecos, ninguno cerrado:**

1. **Nada detecta que un manifiesto contenga entradas de un expediente no declarado.** Los
   `expediente_id` que el caso reconoce están en `_caso.md` (`sudespacho_expedientes`); comparar
   contra ellos es una comprobación barata que hoy no existe. Es, además, exactamente la puerta de
   integridad que pide `§5.2` del spec de la vista procesal para las ocurrencias
   (`docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md`), así que conviene
   que las dos usen el mismo criterio.

   **No lo cubre `core/email_atomize/contaminacion.py`** (PR #138, 2026-07-27), aunque el nombre lo
   sugiera: ese detector opera sobre **mensajes de correo ya atomizados** y caza W-codes ajenos en
   asuntos y nombres de adjunto — otro canal y otra capa. Este hueco es del canal **CRM** y del
   fichero de control. Sí comparten el principio, y es el correcto: **avisar, nunca excluir en
   silencio** — en un expediente probatorio la decisión de borrar es del letrado.
2. **`INTAKE_EVENTS` no tiene un tipo para el saneamiento de un fichero de control.** El set es
   cerrado (26 tipos) y ninguno encaja: `delete_doc` sería inexacto y haría creer a una auditoría que
   se borraron documentos del caso. Por eso el saneamiento del 2026-07-27 se registró en un acta en
   `_snapshot/` y no en el log. Falta un `saneamiento_manifiesto` (o equivalente) con
   `details = {fichero, entradas_antes, entradas_retiradas, entradas_despues, motivo, respaldo}`.

**Precaución aprendida (vale para cualquier saneamiento con checkout abierto):** operar sobre la
copia del **Drive** y **no** tocar la local. `_intake_hashes.json` no está en `MERGE_EXCLUSIONS`, así
que entra en el merge de 3 vías; con la local igual al baseline y el Drive cambiado, el checkin
acepta el Drive. Tocar la local haría divergir las dos ramas y provocaría un conflicto para nada.

---

## 93. Ciclo de vida del lock de la biblioteca: no se escribió en el checkout y el checkin aborta al cerrar

**Disparador:** ninguno todavía — detectado en vivo el 2026-07-27 al hacer el checkin de W-02VND1 (el
que subió la recuperación de `#90`). Son **dos fallos del mismo ciclo de vida**, y el segundo tapa al
primero. Sin promover a `PLAN.md`: nada está bloqueado hoy, pero con varias sesiones en paralelo esto
es exactamente lo que el lock existe para evitar.

**Estado actual.**

*Fallo A — el checkout no dejó lock.* El `_caso.md` de W-02VND1 en el Drive **no tiene el campo
`estado_repositorio`**, pese a que su `_intake_log.jsonl` sí registra un `case_checkout` el
`2026-07-23T09:08:00`. Es decir: el caso estuvo prestado **cuatro días** y el sistema no lo sabía. Un
segundo usuario habría podido hacer checkout del mismo caso sin que nada se lo impidiera.

Lo que lo hace invisible es una decisión de diseño: `estado_de_fm` (`core/repository_checkout.py`)
devuelve `disponible` **por defecto cuando el campo falta**, así que "nunca se bloqueó" y "se bloqueó y
se liberó" son indistinguibles. Un lock que falla en silencio es peor que no tenerlo, porque induce
confianza.

*Fallo B — el checkin aborta en el último paso.* `scripts/repository_cli.py:658-661` (CP11) hace
`estado_actual = rc.estado_de_fm(fm)` y luego `rc.validar_transicion(estado_actual, "disponible")`.
Con el campo ausente eso es `disponible` → `disponible`, que la tabla no permite
(`TransicionInvalida: desde 'disponible' solo se permite: ('prestado',)`) → **traceback**.

El problema no es que aborte: es **cuándo**. La excepción salta *después* de que el merge haya
terminado en VERDE, de subir la evidencia (línea 605), de registrar el evento `case_checkin` (608) y de
integrar la bandeja (620). Lo verificado el 2026-07-27: `rclone check` por md5 dio **0 diferencias /
431 ficheros coincidentes** y el evento quedó escrito con `copiados=428 renombrados=3
resultado=verde` — el checkin **había funcionado**. Pero el usuario recibe un traceback que parece
decir lo contrario, y el cierre queda a medias (lock sin escribir). Hubo que completar CP11 a mano
invocando `aplicar_lock_liberado` + `_push_caso_md` desde Python.

**Mejora propuesta.**
- **(B, barato)** Tratar la transición `disponible` → `disponible` como no-op idempotente en CP11 en vez
  de excepción: si el caso ya consta disponible, escribir igualmente `ultimo_checkin_timestamp` /
  `ultimo_checkin_auditlog` (que son la traza de auditoría) y salir en VERDE. Un checkin que ya movió
  los bytes y registró el evento **no puede terminar en traceback**.
- **(A, el de fondo)** Que el checkout falle **en alto** si el write-then-verify del lock no confirma
  (ya existe `verificar_nonce` para eso, §2.2: usarlo como gate, no como diagnóstico). Y considerar
  distinguir `sin_lock` de `disponible` en `estado_de_fm`, para que la ausencia del campo sea un aviso
  y no un silencio.
- Al arreglar A, revisar si el checkout escribe el lock ANTES o DESPUÉS de copiar 5 GiB: si es después,
  la ventana de carrera es de ~45 min (ver `#95`).

**Justificación de no aplicarlo ahora.** B es una guarda de una línea, pero toca el cierre del checkin,
que es el camino que mueve los bytes de los expedientes: merece su test propio
(`tests/test_repository_cli.py` ya cubre la orquestación) y no un parche al vuelo. A es más profundo —
decidir si `sin_lock` pasa a ser un estado del modelo afecta a `TRANSICIONES_PERMITIDAS`, que es SSOT en
`config`. Y hoy el caso quedó correctamente `disponible`, así que nadie está bloqueado.

**Coste estimado.** B: ~30 min (guarda + test). A: ~1 h el gate del nonce; +1 h si se añade `sin_lock`
al modelo de estados y se migran las transiciones.

---

## 94. El montaje `G:` no es fiable justo después de escribir: verificar por API, nunca por el montaje

**Disparador:** ninguno — anotado el 2026-07-27 tras tropezar dos veces con lo mismo durante la
verificación del checkin de W-02VND1. No bloquea; es una trampa que hace **fallar la verificación, no
la escritura**, que es la peor clase de trampa.

**Estado actual.** Drive for Desktop (`G:`) es *Stream con caché*, no un espejo. Tras subir un fichero,
la vista del montaje puede quedar temporalmente incoherente con lo que Drive ya tiene:

1. **`OSError: [Errno 22] Invalid argument`** al leer con `Path.read_bytes()` un PDF recién subido, para
   compararlo por hash. El fichero está en Drive y es correcto; el montaje no puede servirlo aún.
2. **`Path.exists()` devuelve `False`** para `_caso.md`, y sin embargo `_pull_caso_md` (rclone, por API)
   lo baja con su contenido real (2.316 bytes, con los `sudespacho_expedientes` del caso). Dos
   comprobaciones independientes por el montaje dijeron "no existe" sobre un fichero que **sí existe**.

La consecuencia es un **falso negativo de verificación**: quien audite un checkin leyendo por `G:`
puede concluir que faltan ficheros o que no coinciden, cuando el problema es la hidratación. La
verificación autoritativa del mismo merge, `rclone check --one-way` (por API, md5), dio **0
diferencias / 431 ficheros coincidentes**.

Es la misma familia que el gotcha ya documentado en `CLAUDE.md` (rclone hacia un destino Drive for
Desktop necesita `--ignore-size --ignore-checksum --inplace` para evitar falsos "corrupted on
transfer"): el montaje miente sobre metadatos recién tocados. Y el MCP `expedientes-xl` ya expone
`hydration_status` precisamente para esto.

**Mejora propuesta.** Fijar la regla como doctrina explícita donde se pueda tropezar con ella —
`docs/SEGURIDAD_DATOS.md` o el runbook de la biblioteca, y un puntero desde `docs/DEAD_ENDS.md`:
**toda verificación de integridad contra el Drive va por API (`rclone check` / `hashsum`), nunca
leyendo el montaje**; el montaje sirve para trabajar, no para auditar. Si en algún flujo hace falta
leer por el montaje justo después de escribir, envolver la lectura en un reintento con espera y tratar
`OSError` / `exists() == False` como "aún no hidratado", no como "no está".

**Justificación de no aplicarlo ahora.** Es documentación de una trampa, no un bug de código: los
flujos del repo que verifican de verdad (el `check` del checkin) ya lo hacen bien por API. El riesgo
es humano —o de un agente auditando a mano, como pasó hoy— y se cierra escribiéndolo donde se lea.

**Coste estimado.** ~20 min de doctrina + puntero en `DEAD_ENDS.md`. El helper de reintento, si algún
día hace falta, ~30 min más.

---

## 95. Rendimiento de checkout/checkin: medido, y el cuello de botella no es el que parece

**Disparador:** ninguno — números tomados en el checkin real de W-02VND1 del 2026-07-27. Es
**diagnóstico medido, no diseño**: la parte (3) toca el lock, el baseline y el merge de 3 vías, así que
exige spec propia. Relacionado: `#93` (mismo subsistema).

**Estado actual (todo medido, no estimado).**

*El checkin de W-02VND1:* **248,783 MiB en 426 ficheros, 44 min 17 s, `ERROR: 0`**, media real
**~96 KiB/s**. Cuidado con el número que imprime rclone al final (22,9 KiB/s): es la tasa instantánea
del último tramo, no la media. Aparte, **205 movimientos server-side (22,230 MiB)** que **no pasaron
por la línea**: es el `--backup-dir` apartando dentro de Google lo que iba a sobrescribir. Gratis.

*El caso completo:* **5.358 ficheros, 5,06 GiB.** Y la asimetría que lo gobierna todo:

| capa | ficheros | peso |
|---|---|---|
| Caso completo | 5.358 | **5.181 MiB** |
| Solo texto (`.md` / `.txt` / `.yaml` / `.json`) | 3.434 | **32,5 MiB** |
| Solo la sala de lectura (texto) | 42 | **1,1 MiB** |

Es decir: **lo que se lee para trabajar pesa el 0,02 % del caso.** Los 5 GiB son grabaciones de
entrevista (613 MiB), media de WhatsApp (260 MiB), adjuntos de correo (179 MiB) y los originales de
`00_Input` (2,65 GiB).

*Y la trampa de dirección:* el **checkout baja** y el **checkin sube**, y en una ADSL doméstica típica
(Orange 20/1) eso son mundos distintos: checkout completo **~43 min** (bajada, 20 Mb); subida
**1 Mb = ~128 KiB/s**, apenas un 33 % mejor que el internet móvil de un tren. Corolario importante:
**a 1 Mb de subida, tocar flags de rclone no sirve** (`--transfers`, `--drive-chunk-size` reparten mejor
un ancho de banda agotado, no lo crean). El único lever que funciona es mover menos bytes.

*Multiplicador del intake:* en este delta, **132,4 MiB de originales en `00_Input` generaron 113 MiB de
derivados** (`01_OCR` 33,2 + `02_Documentos` 79,5). Un intake nuevo cuesta en subida **~2x su tamaño**.
Ojo: esos derivados son el **45 % de este delta** pero solo el **3 % del caso entero** — excluirlos
ayuda al checkin y **no** al checkout.

**Mejora propuesta**, por orden de rentabilidad:

- **(1) Cachear el inventario local — gratis y ajeno al ancho de banda.** `inventario_local`
  (`scripts/repository_cli.py`) calcula el **md5 de los 5.358 ficheros en cada ejecución, incluidos los
  `--dry-run`**. El 2026-07-27 se pagó **tres veces** solo para ver el plan. Cachear por
  `(ruta, tamaño, mtime)` deja los dry-run en instantáneos. Es el único punto que mejora sin depender
  de la red.
- **(2) Checkout parcial.** Traer siempre la capa de texto + índices (32,5 MiB; la sala de lectura,
  1,1 MiB, es instantánea) y los binarios pesados **bajo demanda**. Convierte 43 min en segundos para
  el uso mayoritario: leer y redactar.
- **(3) Separar el lock de la copia (cuestión ABIERTA, no acción).** El checkout mezcla dos cosas: el
  **lock** (lo valioso, sobre todo con sesiones en paralelo) y la **copia de 5 GiB** (para I/O local y
  trabajo sin red). `G:` ya es un filesystem y el pipeline acepta `CASOS_ROOT=G:`. Un *checkout
  solo-lock* sería casi instantáneo y **eliminaría de raíz toda la maquinaria de merge**: el plan de 3
  vías, el baseline y los conflictos existen únicamente porque hay dos copias. El 2026-07-27 esa
  maquinaria produjo 3 conflictos de índices que hubo que resolver a mano antes de poder cerrar.

  **Contraargumentos que hay que responder antes de decidir, no después:** (a) *Stream con caché no
  elimina los bytes, los reparte* — abrir un fichero no cacheado lo descarga entonces; si tocas el 10 %
  del caso ganas 10 a 1, pero si lanzas OCR sobre los 717 ficheros de `00_Input` (2,65 GiB) es empate;
  (b) **desaparece la zona de ensayo**: hoy un pipeline que revienta a medias deja la basura en local y
  se tira, mientras que sobre `G:` el estado a medio escribir ya está subiendo; (c) sin red no se
  trabaja; (d) el montaje no es fiable para verificar (ver `#94`). Ya hay un dato del proyecto que
  apunta a favor: en la apertura de W-02ZIIF se concluyó que **el cuello de botella es la verificación
  humana, no la I/O**.
- **(4) Flags de rclone: solo si hay margen de ancho de banda.** Antes de tocar `--transfers` o
  `--drive-chunk-size`, medir la subida real del enlace. Con 1 Mb contratado no hay nada que ganar.

**Justificación de no aplicarlo ahora.** (1) es la única cerrada y barata, y aun así toca el frontal que
mueve los bytes de los expedientes. (2) y (3) son decisiones de arquitectura de la biblioteca —afectan
al lock, al baseline y al merge de 3 vías— y (3) además tiene contraargumentos sin responder. Ninguna se
promueve por completitud: hoy nadie está bloqueado, y el checkin de W-02VND1 se cerró en VERDE.

**Coste estimado.** (1) ~1 h (caché + invalidación por mtime + test). (2) ~1 día con spec. (3) spec
propia, sin estimar hasta responder los contraargumentos. (4) ~10 min de medición; el ajuste, trivial.

## 96. El guard de escritura se dispara sobre la copia PRESTADA, y ahí no protege de nada

**Anotado 2026-07-27**, al preparar el caso `W-02MA0R` para seguir trabajando en local con el
préstamo abierto. Hermano de `#93` (ciclo de vida del lock): los dos salen del mismo sitio, que el
`_caso.md` local no debería gobernar el lock pero de hecho lo gobierna.

**Lo que pasa.** `case_manager.guard_escritura` decide vía `leer_estado_repositorio(case_id)`, que
lee el `estado_repositorio` del **`_caso.md` LOCAL** (`_read_fm` → `caso_path`). Si ese fichero dice
`prestado`, toda escritura del intake se desvía a `_pendiente_checkin/<origen>/…`, que está **fuera de
`00_Input`**. Y `sala_maquina.inventariar()` recorre `00_Input`. Consecuencia medida: se depositan
documentos nuevos, la sala de máquina **no ve ni uno**, y la de lectura tampoco. El pipeline queda
roto en silencio y la corrida se reporta como correcta.

**Por qué es un error de sitio, no de implementación.** El propósito del guard (DISEÑO_V2 §6) es
proteger **el Drive**: que el pipeline no pise un caso que otro tiene prestado. Sobre una **copia
local prestada** desviar no protege de nada — esa copia entera ya es «pendiente de checkin» por
definición, y el merge de 3 vías sube sus altas como `COPY_LOCAL`. Es una bandeja dentro de la
bandeja.

**Hoy solo funciona por accidente.** El checkout **no baja** el `_caso.md` (está en
`MERGE_EXCLUSIONS`), así que en una copia recién prestada el campo falta, `estado_de_fm` devuelve
`disponible` por defecto y el guard queda inerte. En cuanto alguien copia el `_caso.md` del Drive a
local —lo que hay que hacer si se quiere conservar el pull state, ver `#92`— el guard se activa y
rompe el pipeline. Dos comportamientos opuestos según un fichero que el protocolo dice que **no es
autoridad del lock en local**.

**Mejora propuesta.** Que el guard distinga **dónde** escribe, no solo el estado: sobre `CASOS_ROOT`
apuntando al Drive, desviar; sobre una copia local con `MANIFEST_CHECKOUT.json` presente (marca
inequívoca de copia prestada), no desviar. Alternativa más simple: que `guard_escritura` reciba
explícitamente si el destino es la copia de trabajo, y que los CLI locales lo pasen.

**Justificación de no aplicarlo ahora.** Requiere decidir el criterio de «estoy en una copia
prestada» y tocar un guard que cubre todos los canales de intake. Mientras no se haga, el remedio
manual es quitar los campos de lock del `_caso.md` **local** (el del Drive es la autoridad y se
queda intacto) — hecho en `W-02MA0R` el 2026-07-27, con respaldo en el scratchpad de la sesión.

**Hallazgo menor del mismo sitio:** `ensure_case` crea `90_Notas personales/` en la copia local, y el
checkout la excluye a propósito (D5: zona reservada del abogado, vive solo en Drive). Queda vacía, así
que rclone no la sincroniza y hoy es inocua — pero contradice la intención del checkout.

## 97. El espejo `.agents/skills/` ha divergido de la fuente única `.claude/skills/`

**Detectado 2026-07-27** al decidir qué hacer con los ficheros sin trackear de la raíz.

**El dato.** `.agents/` son **400 ficheros y 11 MB**, un espejo de `.claude/skills/` para Codex.
Pero ya no es un espejo fiel: **`.claude/skills/` tiene 22 skills y `.agents/skills/` tiene 25**
(las 22 coinciden en nombre; sobran 3). `CLAUDE.md` es explícito en que la fuente única de
desarrollo de las skills es `.claude/skills/`, así que ese árbol es una copia que nadie sincroniza
y que ya contradice a su fuente.

**Resuelto de momento (2026-07-27):** `.agents/` pasa a `.gitignore` — commitearlo pondría dos
árboles de skills en git y consagraría la duplicación. Y `AGENTS.md` (que era una copia de
`CLAUDE.md` con «Claude» sustituido por «Codex», con rutas fabricadas del tipo `.Codex/skills/`,
inexistente) queda reducido a un **puntero**, avisando de que no se edite el espejo.

**Lo que sigue sin decidir, y es la pregunta de fondo:** ¿debe existir ese espejo? Tres salidas:
1. **Que no exista.** Si Codex puede leer `.claude/skills/` directamente, el espejo es deuda pura.
   Hay que comprobar si Codex tiene alguna restricción real que lo obligue (no verificado).
2. **Que se genere**, como `dist/`: un script que lo derive de `.claude/skills/` y un guard que
   falle si divergen — mismo patrón que `scripts/sync_skill_helpers.py` ya usa para los helpers.
3. **Que sea un enlace simbólico** a `.claude/skills/`. Barato en NTFS, pero exige admin y se
   rompe en clones desde otras máquinas.

**Y una pregunta previa a las tres:** ¿qué son las **3 skills de más**? Puede que sean trabajo real
que solo vive ahí y que se perdería al ignorar el árbol (está sin trackear, así que hoy ya no tiene
respaldo en git). **Comprobarlo antes de cualquier limpieza.**

**Disparador de promoción:** que Codex trabaje con una skill obsoleta del espejo y produzca algo
incorrecto, o decisión de Nikolai. **Coste:** ~10 min responder qué son las 3 extra; la salida (1)
es gratis si se confirma, la (2) ~1 h con guard y test.

---

## 98. `--extraer-adjuntos` deja CIEGO al atomizador: los `.eml` en subcarpeta no se procesan

> ✅ **CERRADO 2026-07-29 — PR #155 (`03a6f8f`), verificación en vivo del §7 de la spec incluida.**
> Enumeración recursiva en el motor
> (`enumerar_rutas_eml` vía `os.walk`, que no silencia los directorios ilegibles como sí hace
> `rglob`), `eml_origen` = ruta relativa POSIX, llave del registro con la fuente delante, y la
> foto incompleta ya no borra fichas: fallo de lectura/enumeración → **no se publica nada**;
> fallo de construcción → se publica **sin podar**. Se retiró el andamio del PR #151 (banner,
> guarda del CLI y `noop`-por-discrepancia), sin pérdida de cobertura: la tabla del §5 de la
> spec la compara escenario por escenario. Spec:
> `docs/superpowers/specs/2026-07-28-email-atomize-enumeracion-recursiva-design.md`.
> **Sigue fuera:** `.EML` en mayúsculas y una carpeta fuente que `emails_src_dirs_de_caso` no
> devuelva — ninguna de las dos la cubría tampoco la guarda vieja.
>
> **Verificación en vivo — los tres pasos del §7, hechos.** Pasos 1-2 (export real de control de
> una etiqueta pequeña a scratch, fuera de todo expediente): produjo el layout auténtico del bug
> —**18 `.eml` arriba + 11 en subcarpeta**— y el motor los ve todos. De ahí salió, además, el
> falso positivo de `_sandwich` (`[SIGUIENTE-SANDWICH-FIRMA]` del `PLAN.md`). El sub-punto que
> añadió la revisión final de rama queda **medido y negativo**: las 11 subcarpetas traen
> exactamente **1 `.eml` cada una**, así que ningún adjunto extraído es a su vez un `.eml` en este
> corpus. Es un corpus, no una garantía: al generalizar el flag hay que volver a medirlo.
>
> **Paso 3 — no-regresión sobre W-02VND1, ejecutado sobre la copia local, no sobre `G:`.**
> `atomize_case(ref)` es literalmente `atomize_dir(emails_src_dirs(ref), emails_out_dir(ref))`:
> la vía `--ref` solo añade `path_for(resolve_ref(...))`, que esta rama no toca y que no escribe.
> Con `--src`/`--out` sobre la copia local se ejerce el motor entero sin tocar el canónico. La
> copia se verificó fiel por contenido **antes** de correr: 1196 ficheros a cada lado, mismos
> tamaños, una sola diferencia y no es un `.eml` (un `(1).pdf` en `_enlaces/`). Resultado sobre
> 908 ficheros hasheados antes y después:
>
> | criterio | resultado |
> |---|---|
> | byte-identidad de la Capa A | **0 borrados, 0 con hash distinto**; `mensajes/` intacto entero |
> | cero renumeraciones | `mensajes` 277→277, `mensajes_fp` 143→143, `adjuntos` 162→162, `_contadores` `{msg: 420, att: 162}` idénticos |
> | migración de `eml_procesados` (§4.5) | aplicada entera: 242 llaves, **242→0** en forma vieja, **0→242** en forma `03_Email/<nombre>` |
>
> Aparecieron 5 ficheros, y **ninguno lo causa esta rama**: cuatro son gemelos **NFD** de adjuntos
> **NFC** ya presentes, con contenido idéntico (ver `99.5` — la normalización la introdujo el viaje
> por Drive, no el motor), y `_revision/identidades_vigiladas.md` es el nombre que el PR #118
> (`cd70944`) dio a esa vista de `_revision/`, ya en main: el árbol de la línea base es anterior a
> ese renombrado, conserva el fichero con el nombre viejo y el motor no poda `_revision/` (`#99`).
>
> **Lo que este paso NO demuestra** (acotado en la rev. 2 de la spec y sigue vigente): la
> transición top→mixto, la copia mayor, la colisión entre fuentes, el fallo con Layer B superado y
> el error de enumeración de directorio. Viven en los death tests 6, 7, 10, 11 y 12 del §6, porque
> provocarlos en vivo exigiría corromper un expediente real.

**Detectado 2026-07-27** por la revisión adversarial de Codex sobre la spec del cableado de correo
(`docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-adversarial-review.md`), y
verificado abriendo el código. **Bug latente en `main`, no introducido por ese PR.**

**Los dos hechos que abrían el agujero** (diagnóstico de 2026-07-27; el primero ya no describe el
código actual — la enumeración pasó a `os.walk` recursivo, ver el bloque de arriba):

- `core/email_atomize/extract.py:53` **de entonces** — `iter_avistamientos` enumeraba con `base.glob("*.eml")`:
  **solo el nivel superior de cada carpeta fuente**, no recursivo.
- `core/email_export.py:1123-1132` — `_escribe_mensaje`, cuando `extract_attachments=True` **y** el
  mensaje trae adjuntos, crea una subcarpeta y escribe ahí el `.eml` + los adjuntos sueltos.

**Consecuencia.** Todo mensaje exportado con `--extraer-adjuntos` que tenga adjuntos —es decir,
**exactamente los mensajes que motivaron el flag**— es invisible para el atomizador. Sin excepción,
sin error, sin nota: no aparece en `mensajes/`, no entra en `corpus.jsonl`, y el detector de
contaminación cruzada tampoco lo mira. El síntoma es un conteo bajo que nadie tiene con qué
contrastar.

**Corrección del registro.** `PLAN.md` y la entrada `#68` de este mismo fichero presentan el commit
`07b0377` (alta del flag `--extraer-adjuntos` en `scripts/abrir_caso.py`) como «la mitad resuelta»
de `#68.a`. **No lo es: es una trampa armada.** El flag hace llegar los binarios a `00_Input` —eso
sí funciona y es lo que la sala de máquina lee— pero al precio de sacar esos mensajes del radar del
atomizador. Hoy no muerde a nadie porque el default es `False`.

**Bloqueaba** (histórico; ver el arreglo en la nota superior). La casilla 3 del bloque
`[SIGUIENTE-CABLEADO-CORREO]` del `PLAN.md` (pasar `--extraer-adjuntos` a default `True`) no se
podía tocar mientras el motor no viera las subcarpetas: generalizar el flag habría generalizado la
ceguera a todos los casos con adjuntos. Con la enumeración recursiva ya en el motor, la casilla pasa
a **decidible**, con la verificación en vivo (Task 8) como gate.

**Salidas posibles** (histórico — **elegida la 1**, ver la nota superior):
1. **Enumeración recursiva en el motor** (`glob` → `rglob` en `extract.py:53`). Una línea, pero
   cambia el conjunto de entrada del motor: hay que comprobar qué pasa con `eml_origen` (hoy
   `eml.name`, que dejaría de ser único entre subcarpetas) y con el registro de procesados, que
   lleva **nombre de fichero** como llave.
2. **Que el llamante pase el conjunto exacto de carpetas** a `atomize_dir` (ya acepta una secuencia).
   No toca el motor, pero deja la responsabilidad repartida entre llamantes.
3. **Que `email_export` no use subcarpetas** y desambigüe por nombre. Cambia el layout de intake ya
   desplegado; el más caro.

**Prioridad.** Resuelta arriba (opción 1, con desempate determinista del canónico y llave de
registro con la fuente delante). Queda solo la verificación en vivo de la Task 8 antes de decidir
la casilla 3.

---

## 99. Saneamiento del motor `email_atomize`: converger bajo borrados y publicar de forma atómica

**Detectado 2026-07-27** por la revisión adversarial de Codex + pasada propia sobre la spec del
cableado; verificado contra el código. Son las tres razones por las que el cableado **no puede
prometer** que `01_Procesado/Emails` esté fresco y consumible sin comprobar nada, y por las que esa
promesa se rebajó a un `status` declarado en el evento.

**99.1 — No poda `adjuntos/`.** La poda de idempotencia cubre solo `mensajes/*.md`
(`core/email_atomize/pipeline.py:121-124`). Los binarios y sus sidecars de un correo retirado
permanecen indefinidamente. No es residuo invisible: `core/adjuntos_contenido/descubrir.py:13`
recorre **todos** los sidecars de `adjuntos/` sin contrastarlos con `INDICE_ADJUNTOS.md`, así que un
adjunto borrado se sigue procesando aguas abajo — incluido el caso feo de un adjunto que se borró
por ser **de otro expediente**. *Contraejemplo:* `A.eml` trae `contrato.pdf`; se atomiza; se borra
`A.eml`; la corrida siguiente informa `adjuntos_unicos=0` y los dos ficheros siguen ahí.

**99.2 — Publicación no atómica.** El árbol se actualiza por escrituras directas sucesivas
(mensajes → poda → adjuntos → `corpus.jsonl` → índices → `_revision/` → vistas) y `_registro.json`
se guarda en la **última** línea (`pipeline.py:170`) con `write_text`, sin temporal ni `replace`
(`ids.py:93-96`). Un proceso que muere en medio deja una mezcla de generaciones con el registro sin
salvar. Y `load_registro` degrada un JSON truncado a **registro vacío en silencio**
(`ids.py:104-107`). Como los IDs se asignan por contador incremental (`ids.py:37-46`), la corrida
siguiente puede **renumerar** `MSG-`/`ATT-`, contra la invariante que el propio docstring del módulo
declara («Re-ejecutar NUNCA renumera»). Un MSG-id ya citado en `_revision/cola.md`, en un
`_entregas/` sellado o en una nota del letrado pasaría a apuntar a otro mensaje: **misatribución en
un árbol probatorio**. *Fix mínimo:* `try/finally: reg.save()` + escritura por temporal y `replace`.

**99.3 — Sin exclusión mutua.** No hay lock ni snapshot entre el conteo de fuentes, la lectura del
atomizador y el inventario del OCR. Dos `apply` simultáneos sobre el mismo caso pueden cargar el
mismo contador de `_registro.json` y asignar el mismo ID a mensajes distintos antes de que gane el
último escritor; un intake concurrente puede depositar un `.eml` entre la atomización y el
inventario, dejando el árbol atomizado y el estado OCR describiendo generaciones distintas. La
concurrencia sobre el mismo caso ya ha ocurrido en este proyecto (memoria
`feedback-concurrencia-pipelines-y-tiempos-apertura`).

**Nota de honestidad sobre la idempotencia verificada.** Las corridas en vivo sobre W-02VND1 que
declararon «2 corridas → 0 cambios» se hicieron con **entradas inmutables**. Eso demuestra
estabilidad, no **convergencia**: nadie probó qué pasa cuando se retiran entradas, que es justo
donde 99.1 falla.

**99.4 — Un anidado que falla al decodificarse no deja rastro (residual, hallado en la revisión
final de `MEJORAS #98`).** `core/email_export.py::iter_nested_originals` hace
`except Exception: continue` sobre un `message/rfc822` cuyo transfer-encoding no decodifica
(línea ~281): el anidado se pierde en silencio, sin aparecer en `fallos_lectura` (el `.eml`
padre SÍ se leyó bien) ni en `errores` (nada llega a intentar construirse). Es la misma familia
que los dos defectos que `MEJORAS #98` cerró — foto incompleta que activa la poda sin que nada lo
declare —, pero en un punto que ese arreglo no cubre: `core/email_atomize/extract.py` llama
`iter_nested_originals` directamente, no la variante con red de seguridad
`_nested_con_fallback` (que si compara los Message-ID vistos por el rebanado byte-fiel contra
los que ve el parser de Python y reporta la discrepancia). Adoptar `_nested_con_fallback` en
`extract.py`, o una comprobación equivalente, resolvería esto sin duplicar lógica.

**99.5 — Un viaje por Drive renormaliza los acentos del nombre y la siguiente corrida duplica el
adjunto (MEDIDO en la verificación en vivo de `#98`, 2026-07-29).** `_escribe_adjunto`
(`pipeline.py`) nombra el fichero con `att.nombre_original`, que sale **verbatim** de la cabecera
MIME. Cuando ese nombre trae acentos en **NFD** (`e` + tilde combinante), el fichero se escribe en
NFD; pero al subir a Drive y bajar de vuelta con rclone el nombre vuelve **normalizado a NFC**. Como
NTFS trata NFC y NFD como nombres distintos y el motor **no poda `adjuntos/`** (99.1), la corrida
siguiente escribe el gemelo NFD **junto** al NFC: dos ficheros con el mismo contenido, el mismo
`ATT-id` y nombres indistinguibles a la vista.

Medido sobre W-02VND1: 2 adjuntos afectados de 162 → **4 ficheros duplicados** (`.docx` + `.md` de
cada uno). Sin renumeración: el `ATT-id` se acuña por `sha256`, así que la identidad congelada
aguanta; lo que se degrada es el árbol probatorio (un adjunto aparece dos veces) y el `.contenido.md`
de la fase 2, que solo existe para la copia vieja. La prueba de que el motor no es la causa: la
ficha NFC preexistente lleva `nombre_original` en **NFD dentro de su propio texto** — el mismo
proceso no pudo escribir NFC en el nombre y NFD en el contenido, luego el nombre se normalizó
después de escribirlo.

Salidas posibles: normalizar el nombre a NFC al escribirlo (una línea, `unicodedata.normalize`; hay
que comprobar que no cambia el nombre de ningún adjunto ya existente), o que la poda de `adjuntos/`
de 99.1 colapse los gemelos por `sha256`. **Consecuencia práctica hoy:** re-atomizar un caso que ha
pasado por Drive **añade** esos gemelos; contar con ello antes de lanzar una corrida sobre el
canónico y no leerlo como regresión.

**Relación.** `#98` es el otro defecto del motor (enumeración) — **cerrado en el PR #155**; su
verificación en vivo es la que midió 99.4 y 99.5. `#87` (motor de OCR de adjuntos) y `#86` (consumo
por la sala de lectura) dependen de que este árbol sea fiable.

**Disparador de promoción:** que se construya `#86` (un consumidor real del árbol atomizado
convierte 99.1 en pérdida visible), un crash real a media atomización, o decisión de Nikolai.

---

## 100. Rutas del crudo y del procesado que Office no puede abrir (el resto del MAX_PATH)

**Detectado 2026-07-28** al arreglar el nombre del informe de viabilidad (ruta de 269 caracteres en
BaRS8 `W-02XOR7`; Excel se negaba a abrirlo). El arreglo acortó lo que **genera el código**
(`Informe viabilidad - <id_go>.xlsx`, y guardarraíl `_avisar_si_ruta_larga` con presupuesto
`RUTA_OFFICE_MAX = 240` en `core/case_manager.py`). Queda fuera todo lo que el código **no bautiza**.

**El hecho técnico, que conviene no volver a re-descubrir.** El sistema de ficheros NO es el límite:
`LongPathsEnabled = 1` en el registro de esta máquina y `openpyxl` abre sin problema el mismo fichero
de 269 caracteres que Excel rechaza. Quien se rinde en 260 es **Office**, que no es long-path aware.
Diagnosticar esto mirando el explorador o `Test-Path` lleva a la conclusión contraria.

**100.1 — El espejo de `00_Input` es intocable y ya viene pasado.** El crudo de E&V trae sus propios
nombres: en BaRS8 `W-02XOR7` hay un `INFORME VIABILIDAD BaRS8 - … - Negativa oferta aceptada.xlsx`
en `00_Input/01_Drive EV/_DEMANDA/` que da **287 caracteres**. No se puede renombrar por doctrina
(el pipeline nunca escribe en `00_Input`) y porque divergiría del espejo del Drive de E&V. El
migrador (`core/migrar_nombres_informe.py`) lo excluye a propósito vía `_es_raiz_de_caso`.

**Por qué hoy no muerde:** la sala de lectura copia ese mismo fichero con nombre canónico corto
(`01_Procesado/Sala lectura/0000-00-00_informe_viabilidad_bars8_….xlsx`, 242 caracteres, hash
idéntico `B1DFFE4E`), así que existe una ruta legible. Pero es **suerte, no garantía**: nada
comprueba el presupuesto al nombrar en la sala de lectura.

**100.2 — El procesado genera rutas mucho peores.** Medido sobre `CASOS` el 2026-07-28, hay ficheros
de hasta **377 caracteres** en `01_Procesado` (anexos de due diligence de BaRS1, `Sala lectura`, y
segmentos del split en `02_Sala de máquina` de VaRS5, 364). Son `.pdf` y `.md`, que hoy se abren con
visores más tolerantes que Office, por lo que **nadie se ha quejado todavía**. Hay también `.docx`
del espejo de BaRS3 a **345** caracteres: Word comparte el límite de Excel, pero **no lo he probado
en vivo** — es la comprobación pendiente antes de dar por real ese caso.

**Salidas posibles** (ninguna elegida):
1. **Presupuesto compartido**: subir `RUTA_OFFICE_MAX` a constante de `core/config.py` y aplicarla al
   nombrar en sala de lectura y sala de máquina (truncando el descriptor, que ahí sí es libre y no
   viaja en la llave de merge del checkin, al contrario que el nombre del informe).
2. **Auditoría periódica**: un `scripts/audit_rutas_largas.py` que liste lo que pasa del presupuesto
   por caso. Cero riesgo, no arregla nada por sí solo.
3. **Acortar los nombres de las carpetas de caso**, que son el tramo común de 160+ caracteres. El más
   efectivo y el más caro: rompe la llave de `checkout`/`checkin` y las referencias en bitácora.

**Prioridad.** Baja hasta que alguien no pueda abrir un `.docx` o un `.xlsx` del procesado.
**Disparador de promoción:** primer fichero de `01_Procesado` que no abra en Word/Excel, o decisión
de Nikolai.

---

## 101. La bandeja `_pendiente_checkin/` produce ficheros `_reingesta_*` que nadie reconcilia

**Anotado 2026-07-29**, hallazgo M-4 de la revisión adversarial de la arquitectura dual
(`docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md`).
Hermano de `#96`. **Sin promover:** la arquitectura dual retira la bandeja como camino ordinario
(su Fase 2), y estos residuos son el rastro que quedará después.

**Estado actual.** `scripts/repository_cli.py:697-724` (`_integrar_bandeja`, CP10) mueve cada
fichero de la bandeja a su ruta original; cuando **colisiona**, `planificar_integracion_bandeja`
lo deja como `_reingesta_*` para no sobrescribir. Ese fichero:

- **no aparece en el plan de merge** (la bandeja está en `MERGE_EXCLUSIONS`), así que nunca sale
  en el `DELTA_PREVIO.md` que revisa el letrado;
- **no lo cubre la verificación por hash** del CP8, que corre *antes* de la integración;
- **nadie lo reconcilia después**: se queda con nombre de residuo junto al fichero bueno, y en el
  siguiente checkout entra al baseline como un documento normal.

**Mejora propuesta.** Al retirar la bandeja (Fase 2 de la arquitectura dual), barrer los
`_reingesta_*` existentes con un inventario por API y decidir uno a uno; y mientras exista el
mecanismo, listarlos en el DELTA con su bloqueante, igual que se hizo con `VETO_GRUPO` (`#137`).

**Justificación de no aplicarlo ahora.** Hoy no hay ninguno conocido, y la pieza que los genera
está en vías de retirada: arreglarla antes de retirarla es trabajo perdido. Lo que **sí** hay que
evitar es retirar la bandeja y dejar los residuos sin censar.

**Coste estimado.** ~30 min el censo por API; el listado en el DELTA, ~1 h con test.

---

## 102. `errors="replace"` en la lectura del log canónico corrompe evidencia de forma permanente

**Anotado 2026-07-29**, hallazgo M-5 de la misma revisión. **Sin promover** solo porque no se ha
observado daño todavía; es independiente de la arquitectura dual y la sobrevive.

**Estado actual.** `scripts/repository_cli.py:736-767` (`_append_evento_drive`) no hace append: baja
el `_intake_log.jsonl` del Drive, lo lee con
`read_text(encoding="utf-8", errors="replace")`, filtra líneas vacías, reconstruye el fichero con
`"\n".join(lineas) + "\n"` y lo vuelve a subir. Dos consecuencias sobre el fichero que el proyecto
usa como **prueba documental**:

1. Cualquier byte no decodificable como UTF-8 se sustituye por `U+FFFD` **y se persiste así**: la
   siguiente subida ya no contiene el original. La corrupción es silenciosa y acumulativa.
2. El fichero se normaliza (líneas en blanco eliminadas, salto final forzado), de modo que **no es
   append-only en la práctica** aunque el docstring lo afirme. Eso es lo que impide comparar
   prefijos por bytes (ver la spec dual §6.3).

**Mejora propuesta.** Leer en binario y no reescribir: subir solo la línea nueva, o si el remote no
admite append, reconstruir a partir de los **bytes** originales sin decodificar. Y que un log que no
decodifica sea un **error declarado**, no un reemplazo silencioso.

**Justificación de no aplicarlo ahora.** Está en el camino que mueve la custodia de los
expedientes y merece su test propio con el doble de rclone que construye la Fase 0 de la
arquitectura dual. Antes de ese doble, cualquier arreglo aquí es a ciegas.

**Coste estimado.** ~1 h con el doble ya disponible; sin él, no hacerlo.

---

## 103. El `CaseWorkspace` no debe cachearse en `st.session_state`

**Anotado 2026-07-29**, hallazgo M-3 de la misma revisión. Es una **regla a fijar antes de la
Fase 4** de la arquitectura dual, no un bug vivo (el `CaseWorkspace` todavía no existe).

**Estado actual.** `streamlit_app.py` tiene **9** resoluciones vía `caso_path`/`resolve_ref` y
**cero** referencias a `estado_repositorio` o al lock: la UI no sabe hoy que un caso puede estar
prestado. Y el repo ya tiene el gotcha documentado en `CLAUDE.md`: un sentinel de «ya hecho» en
`session_state` marcado antes de validar el éxito deja cacheado un fallo durante toda la sesión.

**Riesgo concreto.** Un `CaseWorkspace` guardado en `session_state` es una **autorización
persistida**: el usuario mantiene la pestaña abierta, otro cierra el checkout desde otra máquina, y
la UI sigue escribiendo con un modo que ya no es cierto. La spec dual §5.3 lo prohíbe («no debe
almacenarse entre ejecuciones como autorización permanente»), pero Streamlit es exactamente el
runtime donde esa regla se rompe sin querer.

**Mejora propuesta.** Al migrar la UI (Fase 4): el workspace se resuelve **por request**, igual que
`intake_log.set_actor`; en `session_state` solo puede vivir la *identidad* del caso seleccionado
(`CaseRef`), nunca el workspace ni sus capacidades. Un test que falle si aparece un `CaseWorkspace`
dentro de `session_state`.

**Coste estimado.** Nada ahora (es una regla); ~30 min el test guardián al llegar a la Fase 4.

---

## 104. La rama Google-native del merge no la ha ejercitado ningún dato real

**Medido el 2026-07-29** al capturar el contrato de rclone para el banco de pruebas de la Fase 0 de
la arquitectura dual. **Sin promover:** no hay nada roto, pero hay una decisión de diseño de primera
clase cuyo comportamiento nadie ha visto funcionar.

**El dato.** Barrido de la unidad canónica (`EXPEDIENTES - TYUKHAY LEGAL`) con
`rclone lsjson -R --files-only --max-depth 6 --fast-list`: **3007 ficheros, CERO entradas
`application/vnd.google-apps*`**. Ni un Google Doc, ni una Sheet, en seis niveles de profundidad.

**Por qué importa.** `parse_inventario_lsjson` mapea la ausencia de `md5` a `hash: None`, y
`plan_merge` trata ese `None` como caso de primera clase: emite `ACCION_PRESERVE_DRIVE` con
`google_native=True` y lo documenta en el docstring del módulo («Google-native (Docs/Sheets sin
MD5): no se puede comparar por hash → se preserva siempre»). Además `_vetar_grupos` cuenta
`PRESERVE_DRIVE` como **bloqueante** de un grupo indivisible. Es decir: hay lógica de merge, de
veto y de semáforo que depende de una condición que **nunca ha ocurrido**.

No es código muerto: ocurriría el día que alguien cree un Doc en la carpeta de un caso desde la UI
de Drive, o que un `.docx` se convierta al subirlo. Y ese día el comportamiento sería estreno en
producción, sobre el camino que mueve expedientes.

**Lo que NO hace falta.** Averiguar la forma exacta creando un Doc en el Drive canónico: sería
mutar el repositorio de expedientes para un experimento. Y es innecesario, porque el contrato del
parser —`(item.get("Hashes") or {}).get("md5") or None`— trata igual las tres variantes posibles
(sin clave `Hashes`, `Hashes: {}`, y `Hashes` sin `md5`).

**Mejora propuesta.**
1. El banco de la Fase 0 emite las **tres** variantes desde una fixture **declarada sintética** y
   asierta `hash is None` en todas, más un test de `plan_merge` que cubra el veto de grupo con un
   miembro native. Eso valida la lógica sin datos reales.
2. Si alguna vez hace falta la forma real, capturarla en una **carpeta de pruebas fuera de
   `CASOS`**, nunca en un expediente, y con `lsjson` de solo lectura.
3. Decidir aparte si conviene **prohibir** los Google-native en las carpetas de caso (una nota en
   el runbook, o una comprobación en el checkin que avise), dado que son incomparables por hash y
   por tanto inmergeables por diseño.

**Justificación de no aplicarlo ahora.** El punto 1 entra gratis en la Fase 0 (ya está en su
plan). El 2 no tiene disparador. El 3 es una decisión de Nikolai, no técnica.

**Coste estimado.** Punto 1: incluido en la Fase 0. Punto 3: ~20 min de doctrina si se decide.

## 105. El historial citado que no se puede atribuir desaparece del árbol de MD

**Medido 2026-07-29** sobre una etiqueta real de Gmail (caso `W-02TH0W`, 29 `.eml` exportados a un
scratch) mientras se verificaba `MEJORAS #98`.

**El mecanismo.** Dos decisiones defendibles por separado que juntas pierden contenido:
`bodies.extraer_cuerpo` **recorta la cita** para que cada ficha sea un mensaje y no historial
repetido veinte veces (`cuerpo_recortado_cita: true` lo declara); y la Capa B solo promueve una cita
a ficha propia si puede **atribuir el remitente** desde una cabecera parseable. Cuando ninguna de las
dos cosas ocurre, ese texto no está ni como ficha ni dentro del cuerpo del portador: solo en el
`.eml` crudo.

**Los números, que son lo que evita discutirlo de oído.** De 28 atoms de Capa A, 9 tenían el cuerpo
recortado. En ellos: **51.721 caracteres de texto plano, 10.728 llegan al `.md`, 40.993 fuera (79 %)**.
Pero medido **por frase sustancial** (≥8 palabras), de 365 frases cortadas **332 (90 %) ya existen en
otra ficha** —eran copias del mismo historial citado por varios portadores— y solo **33 (9 %) no
existen en ningún sitio**, de las cuales **31 salen de un solo hilo** con respuesta intercalada cuyos
mensajes anteriores nunca llegaron como correo propio a la etiqueta.

**Lo que NO hay que hacer:** promover con el contenido adivinado. Ahí vive la misatribución, que en
un corpus probatorio es peor que perder texto (un hueco se ve; una atribución falsa no).

**Propuesta (opción B de tres barajadas).** Un fichero hermano por portador,
`mensajes/<atom>.historial.md`, con el historial citado **verbatim** y una cabecera que declare que
**nada de ahí está atribuido**. Los atoms se quedan **congelados** (no se reescribe ninguna ficha, no
se rompe la byte-identidad de Capa A ni la comparación con los `_entregas/` sellados) y tanto el
letrado como un LLM tienen el hilo al lado de la ficha. Descartada la opción A (una sección dentro
del atom) precisamente porque reescribe todos los `.md` existentes.

> ✅ **CONSTRUIDO 2026-07-30 — PR #175 (`31b5943`).** Spec:
> `docs/superpowers/specs/2026-07-30-historial-citado-localizable-design.md`; plan:
> `docs/superpowers/plans/2026-07-30-historial-citado-localizable.md`. Módulo puro
> `core/email_atomize/historial.py` + tres puntos de cableado en `pipeline.py` + el arreglo de la poda.
> 12 tests, todos con *mutation testing*.
>
> **La propuesta de abajo se mantiene** (fichero hermano, opción B) con **tres correcciones que la
> medición obligó**, y por eso se conserva el texto original debajo:
>
> 1. El contenido va verbatim **marcando** los duplicados, no filtrándolos: por los números de esta
>    misma entrada, filtrar dejaría 33 frases de 365 — atractivo, y por eso peligroso, porque un filtro
>    que falla oculta prueba sin que nadie lo note.
> 2. La fuente es `Cuerpo.resto_citado` (lo que `cortar_autor` recortó) y **no** los bloques del
>    segmentador, que pueden venir vacíos (medido: tres portadores con `blockquote` vacíos y el
>    historial en la parte de texto plano).
> 3. **El choque que esta entrada no vio:** la poda de `pipeline.py` borra todo `mensajes/*.md` ajeno a
>    `esperados`, y corre **dentro de la misma llamada**, así que el fichero hermano se autodestruía
>    antes de que `atomize_dir` retornase. `esperados` pasa a incluir los historiales escritos en la
>    corrida, y un huérfano sigue podándose.
>
> **Deuda declarada:** compartir `mensajes/` y el sufijo `.md` hace que todo consumidor con
> `glob("*.md")` cuente el historial como ficha. En la suite rompieron 4 de ~40; fuera de la suite
> (skills, sala de lectura, `#86`) no hay quien avise. Ver §5.3-bis de la spec.

**Disparador de promoción:** un caso donde el 9 % perdido caiga sobre prueba nuclear, o decisión de
Nikolai. **Coste:** ~2 h con tests. Emparentado con `#106` (sin hilo no basta con tener el texto) y
con `#108`.

## 106. Los mensajes están, la conversación no: falta hilo reconstruible desde el MD

**Anotado 2026-07-29**, mismo banco de pruebas que `#105`. Es la queja de lectura real, y es
distinta de perder contenido.

Abres la ficha de un correo y ves **solo su mensaje**. Los otros cuatro de la cadena existen como
ficheros hermanos, pero **nada dice que sean la misma conversación**: no hay «esto continúa en
MSG-00008». Para leer un hilo hay que saltar entre ficheros adivinando el orden, y eso *se siente*
como contenido perdido cuando lo que hay es contenido **inconexo**.

**El obstáculo técnico, ya conocido:** los atoms de Capa B llevan el campo `hilo` **vacío**
(`model.py`; `construir_b` no lo fija), así que agrupar por `hilo` a ciegas fabricaría pseudo-hilos
juntando conversaciones sin relación — misatribución de contexto. Está anotado como requisito de
entrada 2 de `#86`.

**Vías a valorar cuando se promueva:** derivar el hilo en el consumidor vía
`procedencia[].citado_en` (el portador), que es la vía que `#86` ya apunta y no toca el motor; o
threading riguroso por `References`/`In-Reply-To` (`#88`), más caro y con su propio coste en Modo 3.

**Disparador:** que alguien tenga que reconstruir un hilo a mano para un escrito. **Coste:** depende
de la vía; la del consumidor es la barata.

## 107. Test vacuo: `test_seg_html_token_conservacion_no_inventa` no comprueba la conservación

**Detectado 2026-07-29** por la revisión adversarial de Codex sobre la spec del falso positivo de
`_sandwich`.

`tests/test_email_atomize_inline.py:182` solo comprueba que un atributo sea de tipo `bool`. **Pasaría
aunque se eliminara por completo la conservación de tokens**, que es la invariante que dice que el
segmentador no pierde ni inventa texto al repartir el cuerpo entre autor y ancestros.

Es el **cuarto** test vacuo de la misma familia encontrado en una sola sesión (los otros tres: un
mock que comparaba contra `"<b@x>"` cuando los ids se guardan sin ángulos, un fixture de Layer B que
no acuñaba ningún mensaje B, y un test de fallo permanente que pasaba aunque no se publicara nada).
El patrón merece atención por sí mismo: en este motor los tests de invariantes se escriben mirando la
forma del dato y no el comportamiento.

**Qué hacer:** que el test compare el multiset de tokens del cuerpo de entrada contra la unión de los
tokens repartidos, y falle si difieren. **Coste:** ~30 min. **Disparador:** la próxima vez que se
toque `segmentar_html` (p. ej. al implementar la spec de `#98`-sándwich).

## 108. Requisito: que el árbol atomizado sea contexto suficiente para un LLM

**Formulado por Nikolai el 2026-07-29**, tras leer las fichas de un hilo real y no encontrar la
cadena: *«que el LLM no tenga que leer los `.eml` y pueda leer los `.md` —reenviados, embebidos y
adjuntos incluidos— rápido, robusto y sin perder cadenas enteras.»*

Es un **requisito paraguas**, no una tarea: sirve para no perder de vista para qué existe el árbol
cuando se prioricen las piezas. Estado de cada una, medido:

| Pieza | Estado |
|---|---|
| Mensajes reenviados y embebidos como ficha propia | **Hecho** cuando hay cabecera atribuible (verificado en vivo: en la muestra los reenviados sí tenían ficha, y la Capa B promovió 7 citas más) |
| Historial citado no atribuible, disponible sin atribuir | Falta → **`#105`** |
| Hilo reconstruible desde el `.md` | Falta → **`#106`** |
| Texto/OCR de los adjuntos en `.md` | Falta → **`#87`**. Hoy la ficha de cada adjunto dice literalmente `(pendiente; OCR en fase 2)`; en la muestra eran 15 adjuntos únicos (8 `.zip`, 2 `.pdf`, 1 `.ics`) sin una línea de su contenido en la carpeta |
| Falsos positivos que bloquean la promoción | Spec escrita → `docs/superpowers/specs/2026-07-29-sandwich-firma-falso-positivo-design.md` |

**Regla que se deriva de esto y conviene no olvidar:** «que el LLM lo lea» no se resuelve metiendo
más texto en las fichas. Metió 79 % de caracteres que eran 90 % redundancia. Lo que falta es
**estructura** (hilo), **contenido inaccesible** (adjuntos) y **cerrar los falsos positivos** que
impiden que un mensaje llegue a ser ficha.

---

## 109. El historial citado de un hilo no aparece en ningún artefacto (y con esto queda explicado el hilo de 4-5 mensajes)

**Medido 2026-07-29** al verificar en vivo el arreglo del falso positivo de `_sandwich`
(`docs/superpowers/specs/2026-07-29-sandwich-firma-falso-positivo-design.md`, ver la **Errata 2** de
su §5). No es un defecto confirmado: son **dos hechos medidos y una pregunta abierta**, anotados para
no perderlos.

**Hecho 1 — los 3 portadores que el arreglo desbloquea no tenían nada citado.** De los 24 correos con
HTML del corpus de prueba (caso de Valencia, hilos de Gmail), el arreglo desbloquea 3. En los tres:

| medición | valor |
|---|---|
| `blockquote` en el documento | 2 |
| palabras dentro de cada ancestro | **0 y 0** |
| palabras en `autor` / `tokens_total` | 279/279, 216/216, 216/216 → **no se pierde ni se enruta mal nada** |
| marcas de cita (`escribió:`, `De:`, `From:`) en `autor` | **0** |
| contenedores `gmail_quote` | **0** |

Es decir: sus `blockquote` son **cáscaras vacías** de la plantilla HTML, no citas con contenido. El
arreglo hace que se segmenten —correctamente, porque un correo cuyo único texto entre citas es su
firma no es una respuesta intercalada— y produce 6 punteros `sin_cabecera` con **extracto vacío**.
Recupera **0 contenido**. Queda abierto si esas cáscaras son del cliente de correo o un artefacto de
la exportación; no se ha mirado.

**Hecho 2 — el síntoma del hilo YA ESTÁ EXPLICADO (medido 2026-07-29, tras el merge del PR #164).**
El disparador de la spec fue que Nikolai leyó las fichas de un hilo de 4-5 mensajes y encontró **una**.
Censo de los 29 correos del corpus: 22 hilos, y **uno solo tiene hueco** — 1 `.eml` en disco pero **5
Message-ID en el hilo**, de los que **1 tiene ficha y 4 no**. Es ese. La explicación son **cuatro
eslabones, y tres de ellos son correctos**:

| # | Eslabón | ¿Correcto? |
|---|---|---|
| 1 | De los 5 mensajes del hilo, **solo 1 llegó como `.eml`** al caso. Capa A acuña una ficha por `.eml`, luego 1 ficha es lo máximo que podía dar | **Sí**, y es intake, no motor |
| 2 | Los otros 4 existen solo como **cita en texto plano** dentro de ese único correo: **278 líneas** con `>`, **un solo bloque**, profundidad 1, y **0 cabeceras de cita** (`El … escribió:` 0, `On … wrote:` 0, `De:`/`From:` 0) | — |
| 3 | `cortar_autor` **recorta** ese historial del cuerpo de la ficha: conserva **255 palabras de 1748**. O sea, **1493 palabras de historial salen de la ficha** | **Sí**: la ficha muestra el texto del autor, es el diseño |
| 4 | La Capa B, que es quien convertiría ese historial en fichas propias, **no llega a ejecutarse**: `_sandwich` veta este portador (forma `A4 S5 Q S3 Q S20 A5 Q3`) y devuelve cero ancestros → `reconstruir` da **0 candidatos y 0 punteros** | El **veto es correcto** (hay texto de autor real entre las citas, no solo firma: medido, veta igual contando la firma o excluyéndola) |

**El efecto neto, y es el defecto:** esas **1493 palabras de historial del hilo no aparecen en NINGÚN
artefacto**. No en la ficha (recortadas por diseño), no como fichas propias (la Capa B no corrió), y
**tampoco como puntero** (`reconstruir` no emite ninguno cuando el veto está puesto; la fila
`intercalada_no_segmentada` la pone el *pipeline* y no dice nada de los bloques citados). Solo
sobreviven en el `.eml` crudo — justo lo que el árbol de MD existe para no tener que leer.

**Y esto cierra la pregunta que dejó abierta la spec del sándwich:** su arreglo **no podía** resolver
este hilo. Este portador es uno de los que **conservan el veto con razón**; no es un falso positivo.
Los 3 que el arreglo desbloquea son otros, y no tenían nada citado (Hecho 1).

**Dos piezas, y conviene no confundirlas:**

1. **La pieza grande es `#105`** (historial citado sin atribuir), y esta medición la afila: no es «falta
   una vista de historial», es que el historial **se retira activamente** del único artefacto que lo
   contenía y nada más lo recoge. Sin cabeceras no puede haber ficha —y es correcto que no la haya,
   la prime directive lo exige—, pero el texto tiene que estar **localizable** en algún sitio.
2. ✅ **HECHA — la pieza pequeña.** Cuando `_sandwich` veta, `reconstruir` emite igualmente los
   bloques citados como **punteros** `confianza: baja`, `motivo: cita_en_portador_vetado`, con
   extracto y **sin `de`, sin fecha y sin fingerprint**. `Segmentacion` gana `citas_vetadas`, que va
   **aparte de `ancestros`** a propósito: `ancestros` gobierna la Capa B y con el veto puesto tiene
   que seguir vacío, así que no hay atribución posible. Sin `de` no puede misatribuir; sin
   fingerprint no puede colapsar ni promoverse; no entra en `candidatos`. Una cáscara vacía no
   produce puntero —la forma no es hipotética: tres portadores del corpus medido tenían los dos
   `blockquote` genuinamente vacíos—. 4 tests, los cuatro con *mutation testing*: no conservar las
   citas mata 3; ponerles `de` mata el test anti-misatribución; **mandarlas a `ancestros`** —el error
   peligroso— mata el test de la invariante; y retirar el filtro de vacías mata el suyo.

**Estado.** Las **dos piezas hechas**: la pequeña (punteros del portador vetado, PR #169
`5076823`) y la grande (`#105`, el fichero hermano de historial, PR #175 `31b5943`). Lo que sigue faltando
para el requisito `#108` es **`#106`**: tener el texto no da la conversación — falta el hilo. **Disparador de promoción:** decisión de Nikolai, o el siguiente hilo cuyas fichas
se echen en falta — que volverá a pasar, porque la causa 1 (que el caso solo reciba el último correo
de un hilo) es la normal, no la excepción.

**Límites de la pieza 2, declarados para que nadie los descubra como sorpresa:**

- **Solo el camino HTML.** `segmentar_texto` también descarta sus segmentos al vetar
  (`_intercalada_plain`), y ahí NO se emiten punteros. Deliberado: en ese camino los segmentos
  habría que calcularlos con una pasada cuyo resultado el propio veto declara poco fiable, así que
  los extractos podrían engañar. El defecto medido estaba en el camino HTML.
- **Tampoco en la rama `conservacion_tokens`.** Si el reparto de texto no cuadra, los segmentos son
  justamente lo que no es de fiar; emitir extractos desde un enrutado roto sería peor que no
  emitirlos.
- **Su valor sobre el portador que motivó todo esto está SIN VERIFICAR en dato real.** El corpus de
  prueba se borró (con autorización) inmediatamente después de la medición del hilo, y no se registró
  si los `blockquote` de ese portador vetado llevaban texto o eran cáscaras vacías como los de los
  otros tres. Si eran cáscaras, esta pieza no le añade nada y el historial de ese hilo sigue
  necesitando `#105`. **Cómo cerrarlo cuando se quiera:** re-exportar una etiqueta pequeña a un
  scratch fuera de todo expediente —el mismo procedimiento con el que se creó ese corpus— y mirar los
  punteros `cita_en_portador_vetado` que salgan.

**Medido sobre:** el corpus de prueba `_PRUEBA_98_VaRS3` del Escritorio (correo real de cliente; solo
lectura, y de él no salieron al registro ni asuntos ni direcciones ni cuerpos, solo estructura y
contadores). Con esta medición hecha, **ese corpus ya se puede borrar**: era lo único que lo retenía.

## 111. El reproceso releé lo ilegible, no pierde prueba — la alarma original quedó REFUTADA

**Abierta el 2026-08-01 y MEDIDA el 2026-08-02.** Se numera **111** y no 110 porque el 110 lo ocupa un
PR abierto (#185).

> ⚠️ **Esta entrada afirmaba lo contrario de lo que dice hoy.** Su título era «El reproceso de un PDF
> con capa de texto NO es aditivo: pierde cifras y fechas», y sostenía que seg03 perdía **77 palabras
> únicas de 6.405** y seg02 dos, «cifras, fechas y horas — exactamente lo que no se puede perder en
> prueba documental». **Medido, esa lectura es falsa.** Se conserva el enunciado viejo aquí porque la
> entrada llegó a operar como gate: frenó la pieza A de `MEJORAS #90` mientras estuvo escrita así.

### Lo medido (2026-08-02, read-only, sin re-OCR)

**Punto 2 — ¿afectó a las recuperaciones ya dadas por buenas? NO.** Comparados los 7 documentos de
(c1)/(c2) contra sus originales de `99_Versiones anteriores/recuperacion_ocr_2026-07-27/`, en
**caracteres decodificados** (no bytes — la unidad fue el error de la vez anterior):

| documento | peldaño | chars antes | chars después | palabras ausentes |
|---|---|---|---|---|
| Tasación TECNITASA (2 copias de custodia) | 2 | 47.033 | 64.103 | **0** de 1.786 |
| Cuentas anuales 2022 | 2 | 10.539 | 56.021 | **0** de 281 |
| Cuentas anuales 2023 | 2 | 10.235 | 54.708 | **0** de 281 |
| Cuentas anuales 2024 | 2 | 11.147 | 66.160 | **0** de 281 |
| Exposé W-02XOR7 | 1 | 10.127 | 14.322 | **0** de 583 |
| Exposé W-02VUDR | 1 | 12.864 | 14.384 | **0** de 579 |

Conservación palabra a palabra completa, en los dos peldaños, sin excepción. **Las cuentas anuales y
la tasación que están en el Drive son sólidas y no hay que reverificarlas.**

**Punto 1 — dónde se pierde: no se pierde, se releé.** Las 11 pérdidas con dígito de seg03 son otra
transcripción del mismo trozo ilegible, verificadas emparejando pasajes uno a uno. Los cinco pares
comprobados (valores redactados: son de un caso real):

| zona del documento | el viejo | el nuevo |
|---|---|---|
| sello de registro de salida de un ministerio | fecha y hora con dígitos imposibles (año en el futuro) | la misma franja leída como un número corrido, sin separadores |
| teléfono del membrete del despacho contrario | 12 dígitos | los mismos, con uno menos |
| segundo fragmento del mismo membrete | 6 dígitos sueltos | 10 dígitos, absorbiendo el fragmento contiguo |
| dirección del pie de una notaría | número + basura con contrabarra | número + basura sin contrabarra, y **el nuevo recupera los acentos** del nombre del notario |
| cabecera de un certificado energético en catalán | `Institut Catala d9Energia` | `QUALIFICACIÓ ENERGÈTICA … L'EDIFICI` |

Ninguno de los dos lados es una lectura fiable: son zonas que **no se dejan leer** (sellos, membretes,
logotipos rasterizados). Donde existe pasaje homólogo localizable, **el nuevo es más completo**: en un
documento notarial el viejo partía un DNI en un fragmento truncado más un número suelto flotando, y el
nuevo lo trae **entero y bien formado**. En agregado seg03 pasa de 5.414 a 5.453 tokens únicos y de
24.799 a 24.861 ocurrencias: pierde 66 y gana 105.

**Los 2 de seg02 eran artefacto de medición.** Parecía desaparecer la marca temporal del **sello de
firma electrónica cualificada** de un escrito. El sello está entero: las seis marcas comprobadas (DNI
del firmante ×2, emisor del certificado, hora, huso y fecha) tienen **recuentos idénticos** en ambas
versiones. El nuevo escribe la fecha pegada a su etiqueta, sin espacio, y un tokenizador por espacios
la cuenta como otro token. El segundo «perdido» era ruido de OCR del viejo dentro del mismo sello.

**Punto 3 — ¿es inmune el peldaño 2? La pregunta se disuelve.** Presupone que el peldaño 1 no lo es, y
ninguno de los dos perdió nada. El consejo «para documentos donde las cifras sean críticas conviene
forzar el peldaño 2» era una hipótesis, **se ha medido y no tiene soporte empírico**: puede retirarse
(anotado también en el §(c2) de `[SIGUIENTE-OCR-CIEGO]`).

### Método: el control positivo, sin el cual el cero no valía nada

Siete ceros seguidos son sospechosos. El mismo arnés se corrió contra el caso donde la medición del
2026-08-01 **sí** halló diferencias, y las reprodujo: seg01 = 0, seg02 = 2, seg03 ≈ 66 (frente a los 77
originales; tokenizador algo menos granular, misma magnitud). Sin ese control, los ceros de la tabla de
arriba no serían prueba de conservación sino, posiblemente, de un instrumento roto.

### Lo que SÍ queda como hecho, y es lo aprovechable

**El reproceso no es idempotente a nivel de token, y no puede serlo.** Releer un sello borroso da otra
cosa cada vez que cambia el renderizado de entrada. Consecuencia práctica: **cualquier guard que
asserte identidad byte o token entre dos corridas será vacuo por diseño** y acabará desactivado o
ignorado. Si hace falta un guard de no-regresión sobre el reproceso, tiene que medir otra cosa
(conservación de tokens *de contenido*, presencia de términos ancla, o densidad), no identidad.

### Consecuencias

1. **Se levanta el gate de la pieza A** de `MEJORAS #90`: el reproceso no destruye prueba.
2. **Hallazgo de diseño para esa pieza A**, que sí sigue vivo: el saneamiento previsto conserva «la
   versión que cita el registro», que en `W-02VND1` es la del 23/07 — y en seg03 es **la peor de las
   dos** (un DNI partido frente al mismo DNI entero; nombres propios sin acentuar frente a los mismos
   acentuados). Conviene decidir esa regla a propósito y no por omisión. Spec:
   `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md`.

**Coste consumido.** ~40 min. **Pendiente:** nada de medición. Queda solo el punto 2 de Consecuencias,
que es una decisión de diseño de la pieza A, no una medición.

**Alcance de lo medido, para no sobreleer.** 10 documentos (7 recuperaciones + 3 segmentos) de 3 casos.
Retira la alarma y retira el consejo sin base; **no** autoriza a dar por buena cualquier corrida futura
sin mirarla.

## 112. `test_resumen_cuenta_por_estado` depende en silencio de dónde viva el `basetemp` de pytest

**Medido 2026-08-01.** Correr la suite con `--basetemp` largo —166 caracteres, que es lo que mide el
scratchpad de una sesión de Claude Code— hace fallar
`tests/test_migrar_nombres_informe.py::test_resumen_cuenta_por_estado` con `assert 2 == 0`. Con un
`basetemp` de 37 caracteres pasa. Reproducible en ambos sentidos, no es flakiness ni contaminación
entre módulos.

**Causa.** El test asserta `conteo["fuera_de_presupuesto"] == 0` contra `RUTA_OFFICE_MAX = 240`
(el guardarraíl de longitud de ruta del 43º cierre). Monta sus casos bajo `tmp_path`, así que el
presupuesto que mide **incluye la ruta de la carpeta temporal**. Si esa base es larga, los casos
sintéticos se pasan de 240 y el conteo deja de ser 0 — el test mide el entorno, no el código.

**Por qué importa más de lo que parece.** El síntoma es un fallo que aparece y desaparece según
**quién** corre la suite y desde dónde, que es el modo de fallo más caro de diagnosticar: invita a
teorizar sobre orden aleatorio y a culpar al entorno. Me costó una ronda de diagnóstico y solo se
cerró reproduciéndolo con las dos longitudes.

**Mejora propuesta.** Que el test no dependa de la longitud del `basetemp`: o monta bajo una raíz
corta propia, o parametriza `RUTA_OFFICE_MAX` en la llamada, o asserta sobre la diferencia
—«ninguno de estos dos casos añade `fuera_de_presupuesto` por sí mismo»— en vez de sobre el cero
absoluto. Cualquiera de las tres quita la dependencia oculta sin perder lo que el test comprueba.

**Coste estimado.** ~15 min. No bloquea: la suite pasa con el `basetemp` por defecto y con cualquiera
razonablemente corto.

## 113. El pull del CRM no lo encadena nadie, y su `--run-pipeline` llama al motor jubilado

**Verificado contra código el 2026-08-02**, al preguntarse Nikolai por qué los documentos de un
expediente del CRM no aterrizan solos en crudo → sala de máquina → sala de lectura.

**Lo que sí funciona, y conviene saber que funciona.** Las cuatro piezas existen y encajan:

- `python -m scripts.sync_sudespacho pull --case <id> --expediente <id_crm>` descarga los documentos del
  gestor documental (con `--incremental` y `--force`).
- Aterrizan en el sitio correcto: `case_manager.crm_branch_path` los coloca en
  `00_Input/05_CRM/<bucket>`, buckets planos por rama procesal (reorg del 2026-06-10).
- La sala de máquina los ve sin flags: `sala_maquina.inventariar` recorre **todo** `00_Input`.
- La sala de lectura los declara entre sus fuentes (`01_Drive EV`/`05_CRM` en el `SKILL.md`).

**Los tres huecos.**

1. **`abrir_caso` no acepta `--fuente crm`.** `_FUENTES_CLI = ("drive_ev", "manual", "whatsapp", "email")`
   en `scripts/abrir_caso.py`. Abrir el caso y bajarle el CRM son dos comandos distintos y el segundo
   hay que acordarse.
2. **El único encadenado que existe apunta al motor muerto, y es una trampa activa.** El flag
   `--run-pipeline` del pull llama a `pipeline.run(case, do_sync=False, do_demanda=True)`
   (`scripts/sync_sudespacho.py:196`) — el pipeline viejo: Docling, tope de 30 páginas, salida a
   `raw_text/` + `MD/` legacy. **No es la sala de máquina.** Quien lo use creyendo que procesa el
   expediente produce artefactos del motor que la sala de máquina vino a sustituir. Aparece también en
   `intake_judicial` y en `sync_all`.
3. **Entre sala de máquina y sala de lectura tampoco hay encadenado**: la primera «sugiere» la segunda,
   en prosa, en su `SKILL.md`.

**Por qué importa más de lo que parece.** Es el **mismo defecto** que el bloque
`[SIGUIENTE-CABLEADO-CORREO]` de `PLAN.md` («las cinco piezas del pipeline de correo están construidas y
ninguna llama a la siguiente»), que se resolvió en el PR #151 metiendo la llamada dentro de
`sala_maquina apply`. Se trató como un incidente del correo y no se generalizó: la misma clase de
problema sigue viva en el CRM y no tiene fila.

**Mejora propuesta.** (a) `--fuente crm` en `abrir_caso`, delegando en el pull existente como ya hace con
las otras cuatro fuentes; (b) reapuntar `--run-pipeline` a la sala de máquina **o retirarlo**, que es lo
mínimo — un flag que hace algo distinto de lo que promete es peor que no tenerlo.

**Coste estimado.** Bajo. (b) por sí solo son minutos y cierra la trampa.

## 114. No hay contrato de «dame el mejor texto de este documento», y `01_OCR/` no lo lee nadie

**Verificado en todo el repo el 2026-08-02.**

**La escalera existe una sola vez, y como prosa.** El §8 de `.claude/skills/viabilidad-prerelleno/SKILL.md`
define la vía de lectura correcta: si hay `02_Sala de máquina/03_MD/<slug>.md` con estado `ok` en
`_cobertura.md` → léelo de ahí; si es `low`/`empty` o no existe → lee el crudo de `00_Input`; y anota de
qué vía vino (`[doc: fichero, vía MD]` frente a `[doc: fichero, crudo]`). Está bien pensada. El problema
es que es una instrucción al modelo, no un contrato, y los otros consumidores hacen otra cosa:

| consumidor | qué lee |
|---|---|
| `viabilidad-prerelleno` | la escalera completa |
| `triaje-viabilidad` | «Lee `00_Input/` directo». No toca la sala de máquina (ver `#115`) |
| `organizar-sala-lectura` | lee `00_Input`; su `preclasificar.py` sí abre el MD, pero **para clasificar**, no para leer, y la sala que produce contiene copias del crudo |

**No existe** en `core/` una función tipo `mejor_texto(documento) → (texto, vía, calidad)` que resuelva la
escalera una vez.

**Y el peldaño intermedio no tiene consumidor.** `01_OCR/` (los PDF buscables) aparece en
`core/sala_maquina.py` —que los produce—, en su propia skill, en tests y en documentación. **Cero
lectores.** Es el único artefacto que sirve a la vez para lo textual y para lo **visual** (¿está firmado?,
¿sello?, ¿copia u original?), porque es la página original *con* capa de texto.

**Matiz que acota el valor, medido.** Censo de 4 casos con sala de máquina, 497 documentos: 292 `ok`
(159 `pypdf`, 91 `nativo`, **42 `ocr`**), 139 `empty`, 66 `sin_soporte`. Para **205 de 497 (41 %)** la sala
de máquina no tiene nada que ofrecer, y los 250 digitales se leen bien en crudo: **el MD solo aporta de
verdad en los 42 escaneados (8,5 %)**. Ese 8,5 % no es cualquiera — ver `#115` —, pero conviene no
vender la mejora como más grande de lo que es.

**Mejora propuesta.** Sacar la escalera del `SKILL.md` a `core/` y que los tres consumidores la usen, con
el rastro de vía unificado. Decidir de paso quién debería consumir `01_OCR/` (candidato natural: las
comprobaciones visuales del triaje y de la viabilidad).

**Coste estimado.** Bajo la función; el retrofit de las skills exige re-empaquetar y re-importar en Cowork.

## 115. `triaje-viabilidad`: tres definiciones incompatibles de su entrada, y ninguna política de escaneados

**Verificado el 2026-08-02**, y con la intención de diseño reconfirmada por Nikolai en esa misma sesión.

**Tres respuestas en circulación sobre qué lee la skill**, cada una aguas arriba de la anterior:

| fuente | qué dice que lee |
|---|---|
| `docs/superpowers/specs/2026-06-18-organizacion-sala-lectura-drive-triaje-design.md` §5 | «Lee la sala **ya organizada**», y corre sobre el **Drive del despacho** |
| `.claude/skills/triaje-viabilidad/SKILL.md` v1.1 (lo instalado) | «Lee **`00_Input/` directo** del expediente» |
| Intención de diseño (Nikolai, 2026-07-13 y 2026-08-02) | La carpeta del caso en el **Drive de Engel**, normalmente **sin intake**; como mucho con el intake de Drive hecho y sin salas |

**Y la skill no tiene ni una instrucción sobre escaneados.** Buscado en toda su carpeta: ni render, ni
visión, ni «no evaluable». El `SKILL.md` asume implícitamente que todo documento se deja leer.

**Por qué eso es caro, medido.** El documento que decide el semáforo suele ser un escaneado. De los 42
`ocr` del censo de `#114`, los que llevan peso probatorio son: la **hoja de encargo** de `W-02T3XO`
(6.888 ch) y la de `W-02VUDR` (17.574 ch, junto con los poderes), la **hoja de visita** de `W-02VUDR`
(3.894 ch) —que es la prueba de la intermediación—, los **dos poderes** de EV MMC y los **DNI** de las
partes. **La hoja de encargo está escaneada en 2 de los 3 casos** con documentos escaneados. En los
escenarios reales de uso (Drive de Engel sin intake, o
intake sin salas) no hay OCR corrido ni MD al que caer: el factor nuclear sale `débil — ilegible` de
serie, que es justamente el veredicto que el triaje existe para evitar.

**Consecuencia para `#114`:** añadirle la escalera MD/crudo al triaje **aporta poco**, porque solo aplica
con las salas ya montadas, que es el menos frecuente de los tres escenarios. Lo que falta aquí es otra
cosa.

**Decisiones pendientes (las aparcó Nikolai el 2026-07-13 como «dejar abiertas»; las reabrió el
2026-08-02 al plantear el caso de uso).**

1. **Cuál es el hogar de la skill**: carpeta de Engel sin expediente, `00_Input`, o entrada polimórfica.
   Hoy la `description` dice `00_Input` — o sea que el disparador puede no activarse cuando se la quiere,
   o activarse presuponiendo un expediente que no existe.
2. **Qué hace ante un escaneado sin OCR**: render de páginas + visión (lo que decía la intención de
   diseño, validado en W-02XOR7), marcarlo no evaluable y pedirlo en la lista de documentación, o
   degradar el semáforo. Gobierna el valor entero del triaje, porque cae sobre el factor nuclear.

**Coste estimado.** Las decisiones son de Nikolai; una vez cerradas, el cambio es de `SKILL.md` +
`references/criterios_triaje.md` (+ re-empaquetado), no de código.

## 116. La taxonomía documental E&V no la consume nadie aguas abajo: decidir si se sigue pagando por adelantado

**Verificado contra código y skills el 2026-08-02**, a raíz de la pregunta de Nikolai: *«¿para qué sirve
clasificar los documentos (OFERTAS, PBC, RECLAMACIONES…)? Me parece una pérdida de tiempo.»* No es la
primera vez que sale —el patrón es siempre el mismo: ROI evidente en casos grandes, sensación de peaje
en los pequeños que el letrado ya conoce— pero hasta ahora se había contestado por sensación. Esta
entrada existe para que se pueda decidir con el censo delante.

**Qué es.** `TAXONOMIA_EV` (`core/config.py:564`): 8 categorías, de `00. FOTOS` a
`08. PENDIENTE DE CLASIFICAR`. **No es vocabulario del despacho: es el de E&V**, declarado como
«Taxonomía documental E&V» en `.claude/skills/engel-volkers/SKILL.md:193`.

### Censo de consumidores

| consumidor | qué hace con la categoría |
|---|---|
| `preparacion-litigio-civil` | **nada** (0 referencias) |
| `preparacion-audiencia-previa` | **nada** (1 referencia, incidental) |
| `preparacion-juicio-oral` | **nada** — sus 11 coincidencias son «criterios de **activaci**ón», falso positivo del patrón de búsqueda |
| `triaje-viabilidad` | solo `INDICE.md` como **atajo de navegación**; su `SKILL.md:56` dice explícitamente «verifica siempre contra `00_Input`» — no se fía de la clasificación |
| `viabilidad-prerelleno` | **nada de la taxonomía**: sus 36 coincidencias son los **14 hitos** y las preguntas del cuestionario (ver abajo) |
| scripts de `organizar-sala-lectura` | los suyos propios: `preclasificar.py`, `indices_desde_manifiesto.py`, `manifiesto_a_catalogo.py`, `manifiesto_parser.py` |
| `core/` | `local_organizer.py` (vivo, vía `streamlit_app.py` y `scripts/organizar_local.py`) y `sala_lectura.py` (**DEPRECADO**, superado por la skill) |

**Falsos positivos descartados al medir**, anotados para que nadie repita el grep y concluya otra cosa:
un patrón que incluya `ACTIVACI` captura «criterios de activación», y uno que incluya `OFERTAS`/`ARRAS`
captura el vocabulario **de negocio** (¿cuántas ofertas hizo el buscador?, ¿se firmaron arras?), que
aparece en cualquier skill de honorarios sin tener nada que ver con la taxonomía.

### Los dos hallazgos

**1. Es circular.** La clasificación la consume, casi en exclusiva, la maquinaria que la produce. Y como
las categorías viven en `INDICE.md` y **no en carpetas** —decisión deliberada de
`2026-06-18-sala-lectura-unica-design.md`—, clasificar **no mueve ni un fichero**: produce una vista,
no un orden.

**2. Hay dos vocabularios paralelos y solo uno trabaja.** Los **14 hitos** de `viabilidad-prerelleno`
(`ENCARGO`, `IDENT_PROPIETARIO`, `TITULARIDAD`, `HOJA_VISITA`, `OFERTA`, `ARRAS_ARRENDAMIENTO`,
`RECON_HON_*`, `ESCRITURA`, `RECLAMACION_JURIDICO`…) **sí** los consume maquinaria real: el
cuestionario, el scoring y `render_informe.py`. La taxonomía no. Y son ejes distintos: **el hito es un
hecho que hay que probar; la categoría es un cajón donde archivar.** Se parecen en las palabras y no en
la función. Consecuencia incómoda: **clasificar no alimenta los hitos**, que es lo que produce el
entregable al cliente.

**Ni `06. PBC` se sostiene** como categoría: `references/taxonomia_ev.md` enruta la identidad/PBC **por
parte** (propietario → `01. ACTIVACIÓN`, buscador → `03. OFERTAS`) y deja `06. PBC` como residual.

### Dónde sí rinde (estrecho, pero real)

1. **Es el idioma del cliente, no el nuestro.** Al pedir documentación que falta, «faltan la ACTIVACIÓN
   y las ofertas 2 y 3» es accionable para E&V; «falta el documento del 12/03/2024» no lo es. Es un uso
   de **comunicación**, no de análisis.
2. **Escala.** En un caso de 20 documentos que el letrado ya conoce, valor cero. En `W-02VND1` —188
   documentos solo en la sala de máquina— es lo que convierte «léetelo todo» en «léete las ofertas».
3. **Es el eje que la cronología no da.** `CRONOLOGIA.md` ordena por tiempo; el relato que decide una
   reclamación de honorarios es *encargo → visita → oferta → arras → cierre → impago*, que es una
   secuencia de **categorías**. Dos documentos del mismo día pertenecen a hilos distintos y la fecha no
   lo dice.

### El diagnóstico: el problema no es la taxonomía, es cuándo se paga

Hoy clasificar es una **puerta** que hay que cruzar —con visto bueno humano— antes de poder leer. En un
caso que el letrado ya conoce, eso es un impuesto puro. Que la queja se repita con la misma forma
sugiere que la respuesta no es «mantener» ni «quitar», sino **condicionar**.

**Decisión pendiente (de Nikolai), opciones:**

- **(a) Subproducto en vez de fase.** `preclasificar.py` ya clasifica mecánicamente; que corra sin gate
  y solo se revise lo ambiguo (o nada). Conserva los usos 1 y 2 sin el peaje.
- **(b) Condicionar por tamaño.** Umbral de nº de documentos por debajo del cual no se clasifica.
- **(c) Dejarlo como está**, asumiendo el coste como precio de hablar el idioma de E&V.
- **(d) Retirarla del flujo del despacho** y conservarla solo al comunicarse con E&V.

**No se promueve a la cola:** no hay disparador en el sentido de `CLAUDE.md` (ni caso real bloqueado ni
bug), es una decisión de diseño de proceso. **Coste estimado:** la decisión es de Nikolai; (a) y (b) son
cambios de `SKILL.md` + re-empaquetado, no de código.
