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
acceso se solapa con `docs/PLAN_DESPLIEGUE_EV.md` (backup off-site cifrado con
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
