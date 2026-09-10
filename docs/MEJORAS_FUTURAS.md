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

**Evaluado y NO adoptado: `firecrawl/pdf-inspector` (2026-08-03).** Librería Rust (MIT, bindings PyO3
con wheels `win_amd64`) que clasifica PDFs y extrae texto **sin OCR**, con conversión a Markdown
estructurado. Su benchmark publicado —200 PDFs de opendataloader-bench, **con OCR desactivado**— le da
0,875 global frente a **0,589 de markitdown**, y 0,788 en encabezados frente a **0,000**.

**Por qué no se adopta, medido contra el censo de `#114`:**

1. **El claim es cierto e irrelevante aquí.** markitdown **no está en el código** de FeesDefender: solo
   se cita en esta §24 como candidato y en `PLAN_PRERELLENO_LLM_VIABILIDAD.md` como «pendiente bench».
   Y batir a markitdown en estructura de PDF es ganar por incomparecencia: markitdown usa
   `pdfminer.six` a pelo. **Docling —el motor que sí usamos— no está en la tabla.**
2. **Mejora los documentos cuyo MD casi nadie necesita.** Donde daría encabezados y tablas es en los
   **159 `pypdf`** del censo (digitales), que son justo los que se leen bien en crudo.
3. **No hace OCR** (declarado en su `docs/python.md`): no toca los **42 escaneados (8,5 %)**, que son
   donde el MD es la única vía y donde está el peso probatorio (hoja de encargo, hoja de visita).
4. **v0.2.6, publicada el 2026-07-31**, 22 PRs abiertos. Parser único `lopdf`, sin callo medido sobre
   PDFs de LexNET/juzgados. Y cambiar el extractor obliga a subir `EXTRACTOR_VERSION` → reextracción
   de todos los casos.

**Lo único que quedaría vivo** es `detect_pdf()` (10-50 ms) como triaje pre-OCR, porque devuelve
`mixed` + **lista de páginas** que necesitan OCR — pero compite con
[`core/pdf_paginas.py`](../core/pdf_paginas.py), que ya da el discriminante de página ciega con `pypdf`
y **sin dependencia nueva**. **Disparador para reabrir:** un caso real donde la pérdida de estructura
en un PDF digital (tabla de comisiones, escritura a dos columnas) rompa la lectura; y entonces el
bake-off es **contra Docling**, no contra markitdown.

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

> ✅ **Los dos costes de esa anotación, CERRADOS el 2026-08-04** (los dos eran de velocidad de
> montaje, que es la prioridad que fijó Nikolai ese día):
>
> - **El rehash completo**, con `sm.inventariar_cacheado` y la caché persistida en el estado. **No se
>   hizo leyendo `_intake_hashes.json`, como decía esta anotación**, y conviene que quede el porqué:
>   el manifiesto M9 está indexado **sha → rutas**, no ruta → sha, así que no es la caché que hace
>   falta; **no guarda `size` ni `mtime`**, luego no hay con qué validar que su hash siga vigente —y
>   dar por bueno un hash sin validarlo debilita la cadena de custodia por la que el sha existe—; y
>   está incompleto, como la propia anotación reconocía. La caché nueva se invalida por
>   `(size, mtime_ns)` y falla al lado seguro: si el mtime baila —lo hace, en `G:`, al rehidratar— se
>   rehashea. Más lento, nunca incorrecto.
> - **Los ~169 reintentos sin límite**, en `#84`.
>
> Lo que esa anotación decía sobre el **registro único de caso** sigue en pie: nada de esto lo
> construye. La caché es un fichero de estado por caso, no el registro de `§H`.
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

### 55.1 El caso de tensión que acota qué debe hacer la «explosión»: correo → correos anidados → zips de WhatsApp

**Trazado contra código el 2026-08-03**, a partir de dos preguntas de Nikolai: un correo con un zip de
WhatsApp adjunto, y luego un correo con **varios correos adjuntos**, cada uno con su zip. No es un caso
confirmado en un expediente: se traza para que la «explosión» de esta entrada se diseñe con él delante.
**No promovido a `PLAN.md`** — falta el caso real.

**Lo que ya funciona, y bien.** El aplanado de correos anidados es sólido:
`email_export.iter_nested_originals` desciende **a las hojas**, byte-fiel (rebana el crudo y decodifica el
transfer-encoding), con `_nested_con_fallback` comparando el multiset de `Message-ID` contra `msg.walk()`
y cayendo a re-serializado **con aviso** en vez de perder un mensaje. La atomización conserva la
**genealogía**: `Avistamiento` lleva `profundidad` y `ruta_anidacion`, y `dedup.py` funde por `Message-ID`
preservando procedencias. Los N correos adjuntos se recuperan enteros y ordenados.

**Dónde se rompe, y son tres cortes distintos:**

1. **Bifurcación MIME, no declarada en ningún sitio.** «Email con emails adjuntos» tiene dos formas: partes
   `message/rfc822`, que el aplanado ve recursivo; y **ficheros `.eml` adjuntos con MIME genérico**
   (`application/octet-stream`), que **no** son `message/rfc822` y que `extract.py:117` descarta por el
   fast-path. Estos solo aparecen si `--extraer-adjuntos` los escribe a disco y `enumerar_rutas_eml` los
   recoge (el arreglo de `#98`). Con el flag en `False` —el default— son **invisibles**.
2. **El zip no lo abre nadie.** `clasificar_ruta(".zip")` → **`sin_soporte`** en la sala de máquina; y
   `adjuntos_contenido/router.py:13` lo excluye explícitamente (`_EXT_OMITIDO = {".emz", ".zip"}`). En la
   muestra de `#87`, de 15 adjuntos únicos **8 eran `.zip`**, todos con ficha
   `(pendiente; OCR en fase 2)`.
3. **El motor que sabe abrirlo existe y nadie lo llama.** `core/whatsapp_intake.py` descomprime **verbatim**
   a su propio lote (`_chat.txt` + media + el zip original), dedup por hash del zip, evento
   `upload_whatsapp`, y `whatsapp_export.parse_chat` + `referencias_adjuntos` **casan cada media con el
   mensaje que lo cita** (con `safe_zip_members` contra zip-slip). Incluso la detección sin escribir ya
   está: `ChatPreview` da mensajes, rango de fechas y **adjuntos faltantes**. Pero es glue de UI: nada lo
   encadena a un adjunto de correo.

**Dos exigencias que este caso añade al diseño de la explosión:**

- **Enrutado por tipo de zip, no descompresión genérica.** Un export de WhatsApp no es un zip cualquiera:
  descomprimirlo a pelo deja el `_chat.txt` suelto y los media huérfanos, perdiendo justo lo que
  `whatsapp_intake` sabe hacer. El router debe preguntar *¿trae un `_chat.txt` parseable?* (`ChatPreview`,
  read-only) → `whatsapp_intake`; si no → descompresión genérica.
- **Dedup entre exports del mismo chat, que hoy no existe.** `whatsapp_intake` deduplica **por hash del
  zip**: dos exports del mismo chat en fechas distintas tienen hash distinto y entran los dos. Y los
  mensajes de WhatsApp **no tienen `Message-ID`**, así que el dedup del atomizador de correo no aplica y
  `parse_chat` no reconcilia entre exports. Con cinco correos trayendo cinco exports del mismo chat —el
  patrón «cada consultor manda su copia»— el mismo mensaje se contaría hasta cinco veces. Para una
  cronología probatoria eso es **peor que no tenerlo**. Es la «duplicación cross-fuente» que `#54` declara
  obligatoria, convertida aquí en cross-**lote** dentro de una sola fuente.

**Mitigación manual mientras tanto:** comprobar el `Content-Type` de los adjuntos, atomizar (eso funciona),
y dar de alta **un solo** export —el más completo según `ChatPreview`— anotando en `_caso.md` de qué correo
vino, porque esa relación no la guarda nadie.

#### ✅ Cortes 2 y 3 CERRADOS el 2026-08-04 (promovido por decisión de Nikolai)

Los `.zip` adjuntos ya tienen contenido. `core/adjuntos_contenido/zips.py`, enrutado por TIPO de zip
como exigía esta entrada: se pregunta primero si trae un chat parseable y solo si no, descompresión.
La detección es **más estricta** que `whatsapp_intake._find_chat_txt`, que cae a «cualquier `.txt`»:
aquí hace falta que `parse_chat` saque al menos un mensaje. Sin eso, un zip con un `.txt` cualquiera
se clasificaría como conversación de WhatsApp — comprobado por mutación (relajar el criterio pone en
rojo cinco tests del camino genérico).

**El dedup entre exports: NO se ha construido, y esta entrada tenía razón en que no debía hacerse a
la ligera.** La salida fue no fundir y hacer el solape visible:

- `huella_chat` identifica el **chat** por su primer mensaje, así que dos exports del mismo chat la
  comparten aunque su sha256 difiera — que es exactamente lo que `whatsapp_intake` no puede
  deduplicar, porque su dedup es por hash del zip, como decía esta entrada.
- Cuando dos adjuntos del caso comparten huella, cada `.contenido.md` **nombra al otro** y dice
  «no se han fundido; al construir una cronología, contar UNO solo». El conteo quíntuple que esta
  entrada temía solo puede nacer en quien construya la cronología, y ahora ese alguien tiene el aviso
  delante en vez de cinco documentos que parecen cinco conversaciones.
- Límite del método, declarado en el docstring: un export recortado por fecha no empieza por el primer
  mensaje del chat y su huella no coincidirá. Falso **negativo** (dos copias parecerán chats
  distintos), nunca falso positivo.

**Zip genérico:** sus miembros con texto pasan por el mismo router, así que un PDF dentro de un zip ya
usa el motor de la sala de máquina (`#87`). Tres topes, los tres declarados en la nota del artefacto:
profundidad 1 (un zip anidado se lista, no se abre), `MAX_MIEMBROS`, `MAX_BYTES_MIEMBRO`.

**Lo que sigue abierto de esta entrada:**

- **El corte 1** (la bifurcación MIME no declarada: `.eml` adjuntos con `application/octet-stream`
  invisibles con `--extraer-adjuntos` en su default `False`). Intacto.
- **La reconciliación de verdad** entre exports del mismo chat, que es lo que haría falta para una
  cronología unificada de WhatsApp. Sigue sin construirse, y ahora al menos el solape es visible para
  quien lo intente.
- **El alta como lote** (`whatsapp_intake.deposit_export`) desde un adjunto de correo: aquí el export
  se **lee**, no se ingesta. Ingestarlo escribiría en `00_Input` y eso es la decisión de layout de
  `#54`, no un efecto colateral del contenido de un adjunto.
- **La mitigación manual de arriba deja de ser necesaria para leer**, pero sigue siéndolo para
  ingestar: si quieres el chat como lote del caso, sigue siendo un solo export elegido a mano.

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
- **`.doc` binario → `sin_soporte`.** **[RESUELTO 2026-09-05]** — ruta `ofimatica` en
  `clasificar_ruta` (`.doc`, `.dot`, `.odt`, `.ott`, `.ppt`, `.pps`, `.pptx`, `.odp`):
  `core/ofimatica_a_pdf.convertir` (LibreOffice headless con perfil efímero, verificado por
  resultado) → PDF buscable persistido en `01_OCR/` → camino PDF; sin LibreOffice la fila es
  `sin_soporte` con la causa en la nota y `plan`/`apply` avisan antes. Plan y adjudicación:
  `docs/superpowers/plans/2026-09-05-accion-10-ofimatica-en-la-sala-de-maquina.md`.
  Texto original: añadir conversión LibreOffice headless (`soffice --convert-to`) aguas
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

### ✅ CERRADO el 2026-08-04 — se construyeron (a) **y** (b), porque (a) sin (b) es peligrosa

La entrada planteaba (a) tope o (b) visibilidad como alternativas y esperaba que Nikolai eligiera. Al
construirlo se ve que **no son alternativas**: el tope solo es seguro si además se ve.

- **(a) Contador con tope.** `intentos` en `_sala_maquina_state.json` y `sm.MAX_INTENTOS = 3`;
  `plan()` acepta `agotados` y los marca `skip`. El contador **se borra al primer éxito**, para que un
  fallo transitorio no deje deuda acumulada.
- **(b) Visibilidad, y por qué es obligatoria.** El tope tiene un footgun: si falta el motor de OCR
  —`#91`, que sigue sin preflight en este camino— **fallan todos** los documentos y **agotan todos** el
  contador; desde ahí el caso se procesaría «en verde» saltándose el expediente entero. Por eso
  `apply` imprime en **cada** corrida cuántos hay agotados y sugiere sospechar del motor si son todos,
  y `plan` los cuenta en su preview. Vía de escape: `--force` o `--solo <ruta>`.
- **Lo que NO se hizo:** el estado `descartado` en la cobertura que proponía (a). La fila previa del
  documento fallido ya sobrevive en `_cobertura.md` como `empty`/`low` vía `fusionar_cobertura`, así
  que un estado nuevo sería un segundo hogar del mismo hecho.
- **El resto de esta entrada, resuelto por otra vía:** la falta de `_cobertura.json` en W-02VND1 ya la
  cubre `_cobertura_previa`, que reconstruye las filas del frontmatter de `03_MD/` y **avisa de que la
  reconstrucción es parcial** (los `sin_soporte` no dejan MD).
- **Y una consecuencia que sube la prioridad de `#91`:** con el tope puesto, la ausencia de preflight
  del motor pasa de molestia a fallo silencioso posible. Las tres mitigaciones lo hacen ruidoso, no
  imposible.

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

### ✅ CERRADO el 2026-08-04 — y el agujero grande no era el que esta entrada describe

Promovido por **decisión explícita de Nikolai** (disparador válido de `CLAUDE.md`), con
prioridad de **fidelidad del contexto para el LLM y para el humano**. Al abrirlo apareció algo
que esta entrada no contemplaba y que dominaba todo lo demás:

**Nadie ejecutaba el pipeline.** `git grep` sobre `core/`, `scripts/`, `streamlit_app.py` y
`.claude/skills`: **cero llamadores** de `core.adjuntos_contenido` fuera de su propio paquete. La
única vía era `python -m core.adjuntos_contenido <case_id>`, a mano, y no la mencionaba ninguna
skill ni el RUNBOOK. O sea: el motor divergente que esta entrada describe **no llegaba a correr**.
El contenido de los adjuntos no existía en el árbol de ningún caso. Misma clase de defecto que
`#113` y que el cableado del correo (PR #151): piezas construidas y ninguna llama a la siguiente.

Tres piezas, en orden de fidelidad por esfuerzo:

1. **Cableado.** `sala_maquina apply` llama a `contenido.procesar_dir` después de atomizar (los
   adjuntos solo existen en disco tras atomizar) y antes del OCR (si la corrida larga muere, el
   rastro ya está escrito). Se le pasa la RUTA, no el `case_id`: `procesar_caso` re-localizaría el
   caso y en un checkout apuntaría al árbol equivocado. Evento nuevo `contenido_adjuntos`
   (vocabulario 27 → 28). `plan` cuenta los adjuntos sin procesarlos.
2. **La ficha deja de mentir.** Decía `## Descripción

(pendiente; OCR en fase 2)`, y
   `_escribe_adjunto` la reescribe en CADA corrida: como `apply` atomiza siempre, cualquier
   actualización de la ficha por `adjuntos_contenido` quedaba **pisada** a la corrida siguiente.
   La salida no era actualizarla mejor: es que **nunca sea el hogar del contenido**. Ahora nombra
   su `.contenido.md` y explica qué significa que no esté. Un puntero es inmune al clobber.
3. **El motor** (esta entrada). `sala_maquina.texto_de_pdf`: el motor de la sala de máquina sin sus
   artefactos. Cierra el `sin_texto` de los escaneados de >30 páginas, mira las páginas ciegas de
   `#90`, y —lo más sucio de lo que había— quita la etiqueta `confianza: alta` que se ponía «porque
   el motor no fue Docling» a documentos con el cuerpo perdido. `ocr_aplicado` pasa a ser un flag
   explícito. `CONTENIDO_VERSION` 1 → 2, o los adjuntos ya procesados conservarían el texto viejo.

**Dónde vive el adaptador, y por qué no en un módulo nuevo.** La escalera, el discriminante de
página ciega y `ocr_quality` ya viven en `core/sala_maquina.py`. Un `core/ocr_texto.py` habría
creado una **tercera** superficie en vez de unificar dos. Con el adaptador dentro, la convergencia
que queda —que `_ocr_y_extraer` lo use también, en vez de duplicar el enrutado— es un refactor
**local** dentro de un módulo, y no se ha hecho aquí a propósito: ese camino lleva el split, las
notas de custodia y la lógica de `#90`, con ~2.860 tests alrededor.

**Lo que sigue abierto, y conviene no confundirlo con esto:**

- **Los `.zip` siguen excluidos** del router (`_EXT_OMITIDO`). Eran **8 de los 15** adjuntos únicos
  de la muestra de esta entrada, así que la cifra que más se cita de `#87` **no la arregla `#87`**:
  es `#55.1`, y necesita enrutado por tipo de zip (un export de WhatsApp no es un zip cualquiera:
  `whatsapp_intake` sabe abrirlo y nadie lo encadena) más un dedup entre exports del mismo chat
  que hoy no existe.
- **La convergencia de `_ocr_y_extraer`** sobre `texto_de_pdf`.
- **El coste en tiempo del cableado**: `apply` procesa ahora adjuntos que antes no procesaba. La
  caché por sha256 hace que se pague una vez por adjunto, pero la primera corrida de un caso grande
  crece. Es un intercambio deliberado de velocidad por fidelidad, y por primera vez se puede medir:
  el `_tiempos.jsonl` de la misma sesión lo registra.

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

### Medición del 2026-09-08 — 10 adjuntos reales de procuradores, y la red FUNCIONA

Pedida por Nikolai para decidir si los adjuntos del intake de procuradores debían mandarse a
**Mistral OCR en la nube** (`PLAN.md` §MOTOR-DOCUMENTAL los lista como opción). Corpus: **10 PDFs
bajados de `procesal@`** —tres `LXN*`, dos `AcuseMensajeLexnet*`, dos `Env_*`, un traslado de 91
páginas, un `Diligencia` escaneado y un ordinario—, medidos con **las funciones del propio repo**
(`pdf_paginas.perfilar_paginas`, `paginas_ciegas`, `sala_maquina.ocr_quality`,
`calidad_por_pagina`) y con `anon.ocr.ocr_pdf_escalera`.

| | |
|---|---|
| **8 de 10 no necesitan OCR** | los PDFs de LexNET **traen capa de texto limpia**: 1.061–2.511 char/pág, gibberish 0,01–0,09 |
| El escaneado íntegro (`Diligencia`, 2 pp.) | la escalera lo **recupera entero**: 0 → **3.003** chars, gibberish 0,013, ciegas 2→0, `empty`→`ok`, **28,4 s**, peldaño `redo` |
| El traslado (91 pp., 7 ciegas) | ciegas **7 → 2**, por-página **`low` → `ok`**, +12.257 chars, **285 s**, `degradado=False` |

**La señal por página de la pieza (b) hizo exactamente su trabajo:** el traslado puntuaba `ok` a
nivel de documento —210.357 caracteres diluyen 7 páginas mudas entre 91— y **solo
`calidad_por_pagina` lo marcó `low`**. Eso es la tesis de esta entrada, verificada en un documento
real que no se eligió para eso.

**Las 2 páginas residuales, discriminadas hasta el final** (porque «quedan 2 ciegas» no es una
conclusión): la 29 tiene **84 chars** y es una página corta legítima; la 31 da **2 chars**. Sobre la
31 se descartaron dos hipótesis por medición, las dos mías:

1. *«Es un problema de resolución»* (900 px de ancho contra 1.200 de sus vecinas, ~110 dpi).
   **Falso:** `ocrmypdf` con `oversample=400` devuelve **los mismos 2 chars**.
2. *«Tiene 15,6 % de tinta, luego hay texto que el OCR no leyó»*. **Falso, y el error es de
   método: la cobertura de tinta no distingue texto de fotografía.** El histograma sí:

   | | extremos (blanco/negro) | grises medios | chars |
   |---|---|---|---|
   | pág. 30 (control, es texto) | 17,6 % | 18,8 % | 1.169 |
   | **pág. 31** | **5,9 %** | **52,6 %** | 2 |

   Un escaneo de texto es **bimodal**; la 31 es **tono continuo** — es una **fotografía**. Que
   Tesseract devuelva 2 caracteres ahí es **correcto**, y `degradado=False` con `ok` es el veredicto
   acertado, no un silencio.

**Conclusión, y cierra una decisión abierta:** en este corpus **el OCR local lee todo lo legible**.
No hay caso medido para mandar los adjuntos a un OCR en la nube, así que **no hace falta ampliar la
excepción de RGPD** de «texto del correo» a «documentos judiciales de clientes», ni poner el DPA de
Scaleway en el camino crítico. Si algún día aparece el caso, la puerta de entrada es un número y ya
existe: el `_cobertura.md` que genera la sala de máquina.

**Lo que esta medición NO dice:** nada sobre corpus distintos de éste. Las cuentas anuales de
W-02VND1 —el caso vivo con 81-83 % de pérdida que promovió esta entrada— son otra población, y su
número sigue siendo el de arriba. Reproducible: los PDFs se bajaron con un script del scratchpad,
porque **bajar adjuntos no existe en el código** (`MEJORAS #181`).

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

> ⚠️ **La justificación de arriba caducó el 2026-08-04, y esto ya NO es solo conveniencia.** Al cerrar
> `#84` se puso tope de intentos a los documentos que no se resuelven. Con el tope, un motor de OCR
> ausente ya no cuesta una corrida lenta: **fallan todos los documentos, agotan todos el contador, y a
> partir de la tercera corrida el caso se procesa saltándose el expediente entero**. Las mitigaciones
> puestas (margen de 3, recuento de agotados impreso en cada corrida sugiriendo sospechar del motor, y
> `--force`/`--solo`) lo hacen **ruidoso**, no imposible: siguen dependiendo de que alguien lea la
> salida. El preflight es lo que lo haría imposible. Sigue sin disparador formal —nadie está
> bloqueado—, pero su coste de oportunidad cambió de signo.

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

## 93. Ciclo de vida del lock de la biblioteca: no se escribió en el checkout y el checkin aborta al cerrar  [B RESUELTO 2026-08-25 · A ABIERTO]

> **[B RESUELTO 2026-08-25]** — y **no con el remedio que esta entrada proponía**, que era
> tratar `disponible → disponible` como no-op idempotente en CP11 y salir en VERDE. Eso
> arreglaba el traceback y **empeoraba el defecto A-2c**: el evento `case_checkin` ya estaría
> registrado, así que un checkin reentrante pasaría de morir ruidosamente a **duplicar la
> traza de custodia en silencio**. El orden era el defecto, no la excepción.
>
> Lo que se hizo, **tras dos intentos y una revisión adversarial (R9)**: `cmd_checkin`
> comprueba la transición en **CP3-bis, justo antes de la primera escritura al Drive**.
> Tres salidas: **0** reentrancia (ya cerrado, nada que hacer) · **2** anomalía detectada
> al entrar —«abortado sin efectos», que es lo que la tabla de códigos del módulo
> define— · **4** solo si el estado cambia *durante* la corrida, cuando ya hay trabajo
> hecho. Once operaciones rclone en el camino verde, una más: la lectura de CP3-bis.
>
> **El primer intento propio validaba a media corrida y tenía dos defectos que midió R9.**
> Uno CRÍTICO: la reentrancia se detectaba tan tarde que el segundo checkin llegaba a
> **subir trabajo nuevo al canon sin lock** —`plan_merge` clasifica `COPY_LOCAL`
> cualquier fichero local ausente del baseline y del Drive— y luego devolvía 0 diciendo
> «nada que hacer» (H9-02). Y uno ALTO: adelantar la lectura del `_caso.md` ensanchaba
> la ventana en la que otro escritor puede tocar el frontmatter y el push final lo pisa
> desde una foto vieja (H9-03). CP11 conserva por eso su propia relectura pegada al push.
>
> **El Fallo A sigue ABIERTO** — que el checkout falle en alto si el write-then-verify del
> lock no confirma, y la distinción `sin_lock` / `disponible`. Es el mismo problema que los
> defectos A-1 y va con ellos (Fase 2b, aparcada: ver `PLAN.md` fila #3).

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

**Nota al cerrar la Fase 1 dual (2026-08-25). La Fase 1 NO cierra nada de esta entrada, y conviene
decirlo así en vez de dejarlo implícito.** Los dos fallos viven en `scripts/repository_cli.py`, que la
Fase 1 no toca; siguen reproducidos en `xfail(strict=True)` en `tests/test_repository_cli_defectos.py`
—verificados vivos: 7 `xfailed`, 0 `xpassed` **ese día; son SEIS desde que
`MEJORAS #93-B` cerró A-2c, remedido el 2026-09-03**— y su arreglo es la Fase 2.

Lo que sí cambia son las **consecuencias del Fallo A**, y a peor. `estado_de_fm` devolvía `disponible`
ante el campo ausente para **un** consumidor —el propio frontal—; desde la Fase 1 ese mismo silencio lo
consume también `CaseCatalog.estado_compartido`, y por él el `CaseWorkspaceResolver`, que es quien
decide **si un motor puede escribir**. Un `_caso.md` sin `estado_repositorio` ya no produce solo un
checkin confuso: produce un `drive_active` con todas las capacidades sobre un caso que quizá esté
prestado. El registro privado cierra el hueco **por la otra punta** —una copia local conocida se ve
aunque el canon calle— pero solo en la máquina que la registró.

Corolario para quien ejecute la Fase 2: la parte (A) de esta entrada dejó de ser «higiene del lock» y
es la premisa del resolver. Si se decide distinguir `sin_lock` de `disponible`, hay que decidir a la
vez qué modo resuelve el resolver ante `sin_lock` — y el lado seguro es **no** conceder `drive_active`.
Hermana: `MEJORAS #111` no aplica aquí; la relacionada es `#95` (ventana de carrera del lock).

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

## 96. El guard de escritura se dispara sobre la copia PRESTADA, y ahí no protege de nada  [RESUELTO 2026-08-25]

> **[RESUELTO 2026-08-25]** `case_manager.es_copia_prestada()` pregunta al **registro privado
> de workspaces** (Fase 1) si la ruta resuelta consta como copia local de esta máquina, y
> `guard_escritura` no desvía en ese caso. Sobre el Drive nada cambia.
>
> **El discriminante que NO vale, y que era el primer intento: la presencia de
> `MANIFEST_CHECKOUT.json`.** Parecía la marca inequívoca de copia prestada, y abría un
> agujero de autorización: `cmd_checkout` sube además una copia del manifiesto **al
> Drive** («debe sobrevivir a la muerte del Desktop», §3.3), así que mientras un caso está
> prestado el fichero está en **las dos copias**. Discriminar por él desactivaba el guard
> sobre el **canon** y justo **mientras otro lo tenía tomado**. Lo encontraron por separado
> el autor y la revisión R9 (H9-01, CRÍTICO). Hay test que lo caza y un mutante que lo
> revive y muere por él.
>
> **Lo que NO cubre, declarado:** un checkout anterior al registro y **sin adoptar** no
> consta, así que sigue desviando. Es deliberado —el sistema no adivina sobre qué copia
> está— y la vía de desbloqueo existe y es explícita: `core.casos.workspace_adopcion`.
>
> El *hallazgo menor* del final de esta entrada (`90_Notas personales/` creada vacía en la
> copia local) **sigue abierto**: es inocuo y no se tocó.

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

**100.3 — El disparador ha saltado, y por el crudo, no por el procesado (2026-07-30).** Nikolai
reporta que **no puede abrir los ficheros** de
`00_Input/01_Drive EV/OFERTAS/OFERTA 3 - SANTES CREUS - ALEX RUIZ/` en BaRS8 `W-02XOR7`. Medido: el
`.docx` de arras da **291** caracteres y el PDF del contrato de oferta firmado **280**. Esto cierra la
comprobación que §100.2 dejaba pendiente («Word comparte el límite de Excel, pero no lo he probado en
vivo»): **confirmado en vivo sobre un `.docx` de 291**. Con esto se cumplen los dos disparadores de
promoción a la vez — fichero que no abre, y decisión de Nikolai («hay que tomar nota de mejorar
FeesDefender»).

**La medición completa del caso, que da la escala real.** De 571 ficheros de BaRS8 (excluido
`90_Notas personales`), **141 pasan de 260 caracteres (24,7 %)** y **256 pasan del presupuesto
`RUTA_OFFICE_MAX = 240`**. Reparto del gasto antes de llegar a contenido: 67 caracteres del prefijo
`G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\Barcelona` + 81 del nombre de la carpeta
de caso = **149, el 57 % del MAX_PATH consumido antes de `00_Input`**, y solo ~111 para todo el árbol
interno más el nombre del fichero. Los peores del caso llegan a **301** (`KO OFERTA 2`) y hay 19
`.opus` a 297 en `CHATS WHATSAPP/WhatsApp Chat - Propi Natividad Bello Santes Creus 13 Montcada/`,
carpeta cuyo nombre repite la dirección que ya está en el nombre del caso.

**El puente que hoy salva la papeleta, y por qué no basta.** Los cinco ficheros de `OFERTA 3` tienen
copia en la sala de lectura con nombre canónico corto y **hash idéntico**, entre 219 y 242
caracteres, así que sí se abren desde ahí. Es la misma «suerte, no garantía» que ya señalaba §100.1:
dos de esas cinco copias (242 y 241) **ya exceden el presupuesto de 240** y solo se salvan porque el
límite duro de Office es 260. La salida 1 dejaría de depender de la suerte.

**Salidas posibles** (ninguna elegida):
1. **Presupuesto compartido**: subir `RUTA_OFFICE_MAX` a constante de `core/config.py` y aplicarla al
   nombrar en sala de lectura y sala de máquina (truncando el descriptor, que ahí sí es libre y no
   viaja en la llave de merge del checkin, al contrario que el nombre del informe).
2. **Auditoría periódica**: un `scripts/audit_rutas_largas.py` que liste lo que pasa del presupuesto
   por caso. Cero riesgo, no arregla nada por sí solo.
3. **Acortar los nombres de las carpetas de caso**, que son el tramo común de 160+ caracteres. El más
   efectivo y el más caro: rompe la llave de `checkout`/`checkin` y las referencias en bitácora.
4. **Ninguna de las tres arregla el crudo** (§100.1: `00_Input` es espejo intocable). Para el crudo
   las únicas salidas reales son la 3 —acortar la carpeta de caso, que es tramo común y sí recorta
   los 301— o **documentar el puente**: que la sala de lectura garantice copia bajo presupuesto de
   todo el crudo y que el manual diga que el crudo largo se abre desde ahí, nunca desde `00_Input`.

**Prioridad.** ~~Baja~~ → **MEDIA-ALTA: promovible ya.** Los dos disparadores se han cumplido
(2026-07-30). Falta solo la decisión de Nikolai sobre **qué salida** se toma, porque la 3 es la única
que arregla el crudo y es también la más cara.

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

---

## 110. La sala de lectura bautiza con la terminología proscrita (`vendedor` / `comprador`)

**Detectado 2026-07-30** en BaRS8 `W-02XOR7`, de rebote al buscar rutas cortas para los ficheros de
`OFERTA 3` (ver `#100.3`). Los nombres canónicos que genera `organizar-sala-lectura` sustituyen el
nombre de la parte por su rol, y el rol que escribe es el **prohibido** por la doctrina del despacho:

- `2025-11-27_n_vendedor_i_c_vendedor_contracte_d_oferta_de_comp.pdf` ← `N. BELLO i C. ÀVILA-Contracte d'oferta…pdf`
- `0000-00-00_oferta_santes_creus_15_comprador_1.pdf` ← `OFERTA SANTES CREUS 15_Bàrbara & Joan (1).pdf`
- `2024-10-09_p_vendedor_d_n_i.pdf`, `0000-00-00_anexo_1_vendedor.pdf`, `0000-00-00_nie_comprador_2.jpg`

No es un caso aislado: en `indice_documental.yaml` de BaRS8 el patrón aparece de forma sistemática en
`nombre_canonico`. La sustitución del nombre propio por el rol está **bien** (evita PII en la ruta);
lo que está mal es el rol elegido.

**Es divergencia implementación ↔ especificación, no un olvido de doctrina.** El plan de la propia
skill lo impone: `docs/superpowers/plans/2026-06-18-organizar-sala-lectura-y-triaje-drive.md:315` —
«Terminología: propietario / buscador (nunca vendedor/comprador), aun cuando el documento diga otra
cosa». Y lo repiten `#2407` de este mismo fichero, `CLAUDE.md` §«Reglas que nunca se rompen» y la
regla de oro 5 de `viabilidad-prerelleno`. El plan de la sala de lectura (`:367`) contempla además el
rol `tercero`, que tampoco aparece en los nombres generados.

**Por qué importa más de lo que parece.** Estos nombres no se quedan en el disco: viajan a
`_MANIFIESTO.md`, a `nombre_canonico` de `indice_documental.yaml`, y de ahí a las citas `[doc: …]` de
los informes de viabilidad — texto que lee el CFO y que, reescrito, acaba en un escrito procesal. Un
expediente que llama «vendedor» al propietario contradice el escrito que se redacta encima de él, y
obliga a normalizar a mano en cada cita (es lo que ha habido que hacer hoy en `W-02XOR7`).

**Coste.** El mapeo de rol vive en la generación del descriptor: cambiarlo es barato. Lo caro es la
retroactividad — renombrar rompe `nombre_canonico` en los `indice_documental.yaml` ya emitidos y las
citas ya escritas en informes. Salidas: (a) arreglar solo para casos nuevos y dejar los existentes;
(b) arreglar y migrar con tabla de equivalencias, como se hizo con el nombre del informe en `#100`;
(c) dejar de inferir rol y conservar iniciales o hash, que elimina el problema de raíz pero pierde
legibilidad.

**Prioridad.** Media. No rompe nada técnico y el trabajo sigue saliendo, pero es deuda de doctrina
en artefactos que se citan, y la doctrina está escrita en el plan de la propia skill.
**Disparador de promoción:** primera vez que un nombre con `vendedor`/`comprador` se cite tal cual en
un escrito procesal, o que se toque el generador de descriptores por otro motivo (arreglar entonces
de paso).

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

  > ❌ **ESTA AFIRMACIÓN ERA FALSA, y de ella salió la mitad del arreglo (medido el 2026-08-04).**
  > Es cierta de `intake_judicial`, que usa `pull_expediente_v2`, y **falsa de `pull`, `sync_all` y
  > `scheduled_sync`**, que usaban `pull_expediente` (v1) → `00_Input/sudespacho_<id>/`. Se escribió
  > verificando un camino y generalizando a los otros tres. Ver el hueco 2-bis, abajo.
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

   ✅ **CERRADO el 2026-08-04**, y eran **cinco** call sites, no tres: `pull`, `intake_judicial`,
   `sync_all`, `scheduled_sync` y —el peor— el **checkbox del intake judicial de Streamlit**, cuya
   etiqueta decía «Encadenar pipeline (anon → MD → frontier)» y cuyo spinner decía «Ejecutando
   pipeline (OCR → MD → anon)»: tres descripciones distintas de lo mismo y ninguna cierta, en la
   superficie que usan Paola y Ana. Retirados los cinco, junto con
   `--anonimizar`/`--politica`/`--tipo-proc`, que solo existían para alimentar el flag. Cada comando
   **señaliza** ahora qué correr (`scripts.sala_maquina apply`, y `scripts.anonimizar_caso` donde
   antes encadenaba anon): retirar el flag sin decir con qué se sustituye habría cambiado una promesa
   falsa por un silencio. **El botón «Ejecutar pipeline» del tab de análisis se conserva**: es la
   superficie honesta del motor viejo, como `scripts/run_pipeline.py`; retirar ese motor es otra
   decisión y no se ha tomado.

2-bis. **Y el defecto gordo, que no estaba en esta entrada: tres de los cuatro comandos usaban el
   pull v1.** `pull`, `sync_all` y `scheduled_sync` llamaban a `pull_expediente`, que escribe en
   `00_Input/sudespacho_<id>/`. Tres consecuencias, verificadas contra código el 2026-08-04:

   - **`is_legacy_intake_v1` declara ese layout congelado** y `pull_expediente_v2` devuelve
     `blocked_legacy_v1` sin escribir nada. O sea: **un `pull` inutilizaba el caso para
     `intake_judicial`**. Y la carpeta nace de un `mkdir` **antes** de bajar el primer byte, así que
     bastaba un pull que fallara o que se saltara por marcador.
   - Queda **fuera de las fuentes que declara `organizar-sala-lectura`** (`01_Drive EV`, `05_CRM` +
     cajones legacy).
   - **Se salta el guard de escritura del caso prestado.** `_pendiente_checkin` solo aparece en v2
     (`sync_sudespacho.py:1481`), así que un pull v1 sobre un caso en checkout escribía en el árbol
     vivo — exactamente la ruta de pérdida de datos que cerraron los PR #156/#160, con este call site
     sin cubrir.

   ✅ **CERRADO el 2026-08-04**: los tres pasan a `pull_expediente_v2`. `--force` y `--incremental`
   desaparecen (v2 es idempotente por hash del manifiesto M9 y su docstring ya lo declaraba). Un caso
   ya envenenado deja de hundirse más en cada pull: se reporta bloqueado con la migración manual, y en
   los dos barridos no aborta el recorrido. **`pull_expediente` (v1) NO se retira**:
   `scripts/bulk_pull_expedientes.py` lo usa y tiene tests propios; queda marcado legacy en su
   docstring y avisado en el script. **Migrar ese script es lo único que queda vivo de este punto**, y
   no urge: su fuente es el listado paginado del frontal heredado.

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

### Estado (2026-08-04)

- **(b) HECHA**, con el alcance ampliado que se describe en los puntos 2 y 2-bis: retirado el flag en
  los cinco call sites y migrados los tres comandos al pull v2. +15 tests
  (`tests/test_guard_sync_cli_pull_v2.py`), con **prueba de mutación** del guard estructural:
  reintroducir `pipeline.run(` en `scheduled_sync` y una llamada a `pull_expediente(` en
  `sync_sudespacho` pone en rojo las asserts que les corresponden, y `pull_expediente_v2(` no las
  dispara por falso positivo.
- **(a) SIGUE PENDIENTE** — `abrir_caso` no acepta `--fuente crm`.
- **(3) SIGUE PENDIENTE** — sala de máquina → sala de lectura no encadena.
- **Nuevo pendiente que destapa el arreglo:** `scripts/bulk_pull_expedientes.py` sigue en v1 (ver 2-bis).
- **Lo que la corrección deja peor a corto plazo, dicho sin adornos:** los casos que ya tienen
  `00_Input/sudespacho_*/` (el `is_legacy_intake_v1` cita **BaRR3 y MaRS15**) pasan de «el pull
  funcionaba y hundía el caso» a «el pull no funciona y lo dice». Es lo correcto —el guard existía y lo
  que fallaba era que el CLI no lo cruzaba— pero **hasta migrarlos a mano no se les puede bajar el
  CRM**. La migración (borrar `sudespacho_*/` + repetir el pull) es destructiva sobre documentos ya
  descargados, así que **no se automatiza aquí**: pide Preview→Apply (principio M7) y es trabajo
  aparte. No se promueve a `PLAN.md` sin que Nikolai lo mire: hay que censar antes cuántos casos
  reales están en v1, y ese censo se hace contra `G:`, no contra el repo.

### 113.1 Los dos barridos son el mismo programa escrito dos veces

**Verificado el 2026-08-04** al migrarlos: `sync_sudespacho sync_all` y `scheduled_sync` hacen lo mismo
—recorrer los casos, leer `sudespacho_expedientes` del frontmatter, pull de cada uno— con dos
implementaciones distintas: el primero lista con `case_manager.list_cases()` y parsea el frontmatter en
línea; el segundo usa `case_locator.list_cases` y su propio `_read_expedientes`. La diferencia real es
solo la envoltura (logging a fichero, código de salida, keep-alive de `gdrive_ev`).

**Por qué importa:** todo arreglo en esa zona hay que hacerlo por duplicado, y este mismo cambio lo pagó.

**Mejora propuesta.** Que `scheduled_sync` sea una envoltura de la función de barrido, no una copia.
**Disparador:** el siguiente cambio que toque el barrido. Sin él, no urge.

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

### 114.1 `01_OCR/` no es el único sin lector: `raw_text/` tampoco, y además está duplicado

**Verificado el 2026-08-03**, al preguntar Nikolai por qué la sala de máquina en sentido amplio está
partida en intake → OCR → raw → MD y si eso no repite ficheros.

**`raw_text/` no lo lee nadie.** Lo escribe `_escribir_md` junto al MD
([`sala_maquina.py:753-757`](../core/sala_maquina.py:753)); lo único que lo mira es el **guard de
integridad de bundles** (`:589`), para comprobar que el fichero existe. Buscado en `core/`, `scripts/` y
`.claude/`: **ningún consumidor de su contenido**. Es el MD **menos el frontmatter**, y quitar el
frontmatter cuesta un `re.sub` de una línea —`preclasificar.py:212` ya lo hace—. En el censo de
duplicados del spec de identidad de segmento son **7 de los 21 ficheros excedentes**.

**Y hay dos `raw_text` distintos**, o sea duplicación de *concepto* y no solo de fichero:
`01_Procesado/raw_text/` (del extractor antiguo, [`extractor.py:342`](../core/extractor.py:342)) y
`01_Procesado/02_Sala de máquina/raw_text/`.

**Matiz que evita el recorte fácil.** De las cuatro capas, **tres son funciones que ningún artefacto
único sirve a la vez**: el crudo es prueba y cadena de custodia; `01_OCR/` es la página original *con*
capa de texto, luego sirve para lo **visual y procesal** (¿firmada?, ¿sellada?, ¿copia u original?, cita
por página); `03_MD/` es el texto para el modelo. La capa injustificada es **`raw_text/`**, no el número
de capas. Vassal tiene la misma estratificación (`raw/` + `mirrors/` + copias de trabajo) y no acumula
huérfanos porque su `index.yaml` es el vínculo: **la ruta no es la identidad**.

**Mejora propuesta.** (a) **Colapsar `raw_text/` en `03_MD/`** — elimina un tercio de los excedentes por
construcción y una duplicación conceptual entera, sin esperar a F1. (b) Retirar el `raw_text` del
extractor antiguo o declararlo legacy. (c) `01_OCR/`: darle consumidor (lo visual del triaje y la
viabilidad) o dejar de producirlo — hoy es el artefacto más caro y con cero lectores.

**Coste estimado.** (a) bajo y aislado. (c) es decisión, no código.

### 114.2 `texto_espejo_md` devuelve al primer match: de un bundle solo se lee el primer segmento

**Verificado el 2026-08-03.** `texto_espejo_md`
(`.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:195-213`) recorre `_cobertura.json`
buscando la fila cuyo `parent_sha256` (o `sha256`) case con el sha del crudo, y **retorna en el primer
match**. Para un documento suelto es correcto. Para un **bundle** —un LexNET con demanda + N anexos— un
único fichero de `00_Input` produce N filas, así que el preclasificador lee el MD de `d01` y **ninguno de
los demás**.

**Por qué importa poco y a la vez importa.** Para *clasificar* puede bastar: la portada de la demanda
decide la categoría. Pero es **truncación silenciosa** —nada la declara— y significa que los anexos
escaneados no influyen en dónde acaba el documento ni en su fecha canónica.

**Mejora propuesta.** Recoger **todas** las filas del bundle y concatenar (o al menos declarar en el
reporte que se leyó 1 de N). Encaja en el contrato `mejor_texto()` de esta entrada: la escalera debería
recibir un documento **lógico**, no un fichero físico.

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

### 115.1 El mismo patrón en `viabilidad-prerelleno`, dentro de un solo fichero

**Verificado el 2026-08-03.** No hacen falta tres documentos para que la entrada de una skill sea
ambigua: basta un `SKILL.md`. En `viabilidad-prerelleno`, su **`description`** (líneas 5-6) dice que
«lee la documental no anonimizada de **`00_Input`**» y no menciona la sala de máquina; su **regla de oro
8** (línea 52), cuarenta líneas más abajo, añade la escalera `03_MD` → crudo. La `description` es lo
único que se carga siempre y lo que dispara la skill.

**Menos grave que en `triaje-viabilidad`** —aquí las dos definiciones no se contradicen, una es
superconjunto de la otra— pero es el mismo mecanismo de deriva, y la asimetría tiene efecto: quien
dispare por `description` no espera que la skill se apoye en artefactos de `01_Procesado`.

**Y el punto donde muerde.** La regla 8.1 justifica fiarse del MD porque «su calidad ya fue verificada
(densidad de texto, sin gibberish)» y añade que releer el crudo «sería releer lo mismo por una vía más
lenta» — o sea, **le dice al modelo que no vuelva al crudo**. `#90` demostró que esa verificación puede
devolver `ok` sobre páginas cuyo cuerpo se perdió bajo el sello. Con los peldaños (a) y (b) construidos
el riesgo baja para corridas nuevas, pero **un caso procesado antes conserva la cobertura vieja**: la
skill hereda un `ok` caducado sin forma de notarlo. Ya recogido como dependencia en `PLAN.md` (fila #3,
pieza 3: «`estado: ok` puede ser mentira»); se anota aquí el consumidor concreto.

**Mejora propuesta.** Que la `description` declare la entrada real (una frase), y que la regla 8.1 admita
la excepción: si la cobertura del caso es anterior al arreglo de `#90`, no fiarse del `ok`.

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

## 117. Límites declarados de la identidad persistente del segmento (pieza A)

*Abierta 2026-08-02 al construir la pieza A de
`docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md` (rev. 4). No son bugs: son
las fronteras que la pieza A deja dibujadas a propósito, escritas para que nadie las descubra al
pisarlas. Se numera **117** y no 113 porque #113-#116 se ocuparon el 2026-08-02 (PR #190 y #191)
mientras la pieza A se construía sobre una `main` anterior.*

### Las fronteras del motor

1. **El preflight valida identidad, no rangos.** Los rangos exigen el nº de páginas del buscable, que
   en un escaneado no existe antes del OCR: pasar `total_pag=0` marcaría como «fuera de rango» todo
   manifiesto válido. Se siguen validando dentro de `_split_o_md`, con el total real. Consecuencia: un
   manifiesto con rangos imposibles muere documento a documento, no en el preflight.
2. **La reconciliación de `--force` sobre un escaneado tampoco es preflightable** (su manifiesto
   propuesto sale de `detectar`, que exige el buscable). La cubren el aislamiento por documento y el
   guard bidireccional, que aborta con **salida 3**.
3. **Un manifiesto legacy sin `doc_id` aborta la corrida normal** de ese bundle. Se eligió fail-closed
   porque acuñar identidades en silencio congelaría la identidad equivocada si un `--force` histórico
   renumeró los `seg`. **Hay dos salidas, y conviene saber las dos:** `apply --force` sobre el caso
   entero, **o** borrar el `_segmentacion.json` de ese bundle y lanzar `apply --solo <ruta>`, que
   reconcilia contra `previo=None` y acuña identidades nuevas. La segunda es la acotada, y hace falta
   saberla porque `--solo` **no se combina con `--force`** (`scripts/sala_maquina.py:283-289`).
4. **«Cero bytes escritos» del preflight es «cero artefactos de Sala de máquina».** `apply` atomiza el
   correo antes (`scripts/sala_maquina.py:293`), lo que crea `01_Procesado/Emails/` y añade una línea
   a `00_Input/_intake_log.jsonl`. Mover el preflight delante de la atomización haría cierta la frase
   original; no se hace en esta pieza. Ningún test puede cazarlo, porque todos doblan la atomización.
5. **El guard detecta, no previene.** La publicación por *staging* estrecha muchísimo la ventana, pero
   no hay rollback: si se rompe entre el PDF y el MD, el estado incoherente existe y lo que hace el
   guard es cerrar la corrida en rojo con el segmento nombrado.

### El daño de la pieza B que la pieza A va a tocar (medido, 2026-08-02, read-only)

Corrido `verificar_integridad_bundles` sobre los 5 casos con sala de máquina, sin escribir nada:

| caso | filas | bundles | huérfanos sin fila |
|---|---:|---:|---|
| `W-02VND1` | 188 | 7 | **3** — `completo__c170a0f5__seg01/02/03`, esquema viejo |
| `W-02VUDR` | 225 | 10 | **4** — el poder notarial, con **seg01 y seg02 duplicados** (dos sha cada uno) |
| `W-02T3XO` | 30 | 0 | 0 |
| `W-02TH0W` | 54 | 0 | 0 |
| `W-02XOR7` | — | — | **sin `_cobertura.json`**: no medible sin reconstruir |

Son parte del censo de la pieza B (5 grupos duplicados, 21 ficheros excedentes). **Lo que importa
saber:** el barrido de generación ajena de `publicar_segmentos` **no depende de `--force`**, así que
esos 7 ficheros se archivarán solos la primera vez que se republique su bundle, con o sin la bandera.
El guard solo abortaría si la corrida muriese **antes** de publicar ese bundle. No hay bloqueo
operativo previsto, pero **la pieza A va a tocar daño de la pieza B** y eso debe constar antes de que
ocurra, no después.

*(Y una trampa del arnés, apuntada donde se busca: `settings.casos_root` en un **worktree** resuelve a
`data/CASOS` del propio worktree, porque los worktrees no heredan `.env`. La primera corrida de esta
medición dijo «no encontrado» en los cinco casos. Que dijera eso y no «0 discrepancias» es la
diferencia entre un nulo honesto y un falso verde.)*

## 118. El acta de una revisión archiva el digest del INFORME, pero no el del OBJETO revisado

*Abierta 2026-08-02. Hallazgo de la sesión revisora de la ronda 1 de la pieza A, suscrito al
adjudicar. **No se toca desde aquí:** es el contrato de revisión adversarial, y `CLAUDE.md` reserva
revisar el propio contrato de revisión para Codex — el sesgo compartido es justo el riesgo.*

`G8` recomputa el `sha256_informe` y compara, de modo que alterar el informe archivado pone la suite
en rojo. Pero el acta declara el objeto revisado como `commit: <hash>` **sin digest**, y nada
comprueba que el revisor mirase de verdad ese commit. Un revisor anclado por error a otro commit
—o a un working tree sucio— produce un acta **perfectamente válida**: la cadena de custodia cubre lo
que dijo el revisor, no sobre qué lo dijo.

En la ronda 1 de la pieza A el anclaje se verificó a mano (`git rev-parse` de los dos ficheros contra
`a7f168c` y contra el tip), y esa verificación **no deja rastro comprobable** en el acta.

### DECIDIDO 2026-08-03: se reduce a una frase del mandato; el campo y el guard quedan aparcados

> La formulación original de esta entrada —«que el acta gane un `sha256_objeto` y que `G8` lo
> recompute como hace con el informe»— **invitaba a construir la variante que no sirve**. Se conserva
> arriba el diagnóstico, que es correcto, y se sustituye la propuesta.

**1. Recomputar el digest desde el commit anclado sería un guard vacuo.** `G8` calcularía
`sha256(git show <commit>:<objeto>)` y lo compararía con un campo que el autor rellenó de la misma
forma: la comprobación no dice nada sobre qué leyó el revisor. Es la clase de defecto que este
proyecto ya tiene censada en **`MEJORAS #107`** (test vacuo). Solo tiene valor si el **revisor**
declara el digest a partir de los bytes que leyó de verdad y el guard lo contrasta con el commit.

**2. Y entonces cubre un caso, no el que el párrafo de arriba evoca.**

| caso | ¿lo detecta el digest? |
|---|---|
| Declaró el commit X y leyó otros bytes (típicamente un **working tree sucio**) | **Sí.** Riesgo real: las sesiones trabajan en worktrees con cambios sin commitear |
| **Anclaje equivocado**: declara y lee el commit que no debía | **No, y ningún esquema de digest puede** — no hay inconsistencia que detectar |

El segundo es el que la redacción original sugiere («un revisor anclado por error a otro commit») y
es justamente el que **no** se cierra por aquí. Ése lo cierra el encargo, no el acta.

**3. El alcance del «objeto» no está resuelto y no es menor.** El objeto no es un fichero: el acta de
la ronda 1 de la pieza A declara `objeto` y `objeto_secundario`, y la revisión leyó además cinco
ficheros de test y cuatro de `core/`. Un digest de lo declarado deja fuera la mayor parte de lo
revisado; un digest de «todo lo que abrió» no es enumerable ni recomputable. Si algún día se hace,
tiene que ser **por fichero declarado** y decir explícitamente que no cubre el resto.

**Qué se hace, entonces:**

- **AHORA, y cuesta una frase: al próximo encargo, no al contrato.** Que el mandato incluya «declara
  el commit y el `sha256` de cada fichero que abriste». El revisor honesto lo cumple, el descuidado
  se delata, y no hace falta campo, guard ni retrofit. **No es teoría:** es lo que la sesión revisora
  hizo por su cuenta en la ronda 1 —comprobó los blobs contra `a7f168c` y contra el tip— y fue eso lo
  que le permitió refutar en un movimiento un diagnóstico ajeno que era falso.
  **Como práctica primero y doctrina después:** meterlo hoy en `AGENTS.md` o en el §del contrato es
  editar el contrato de revisión, con el gate del punto siguiente; aplicarlo en un encargo concreto
  es una instancia y no lo necesita. Si en dos o tres rondas demuestra que sirve, sube a doctrina.
- **APARCADO con disparador: el campo `sha256_objeto` + su comprobación en `G8`.** Disparador,
  cualquiera de los dos: (a) que aparezca un acta cuyo digest declarado no cuadre con su commit
  —señal de que el fallo es real y no hipotético—; (b) que Codex, con cupo, lo quiera.
- **Gate de quién lo toca:** sigue en pie lo de la cabecera. Es el contrato de revisión adversarial y
  `CLAUDE.md` reserva su revisión a Codex (cupo el **2026-08-08**). Revisor sustituto **no cabe**
  aquí: el cambio toca el mecanismo que existe para detectar el sesgo del autor, y ahí el sesgo
  compartido es el riesgo entero.

**Nota de independencia, que corresponde dejar escrita.** Media autoría de este hallazgo es de la
sesión que ahora lo reformula. Decidir construirlo era la opción cómoda; lo que se decide es que su
versión elaborada no compra lo que promete, que una frase en el encargo compra casi todo, y que el
resto espera cinco días a un revisor que no comparta los mismos puntos ciegos.

## 119. `STATUS.md` se contradice sobre cuántos tags del CRM se auditaron: 96 vs 87

**Detectado el 2026-08-03** al retirar el aviso de re-clonado de `STATUS.md`. No es una cifra
rancia —esas se corrigieron ese mismo día, PR #192— sino **dos afirmaciones incompatibles sobre el
mismo hecho, ambas vivas y ambas de la misma fecha**:

| Dónde | Qué dice |
|---|---|
| `STATUS.md`, tabla *Estado general* | «Tags CRM verificados ✅ — **96 extrajudicial auditados + 10 nuevos mapeados** (2026-05-06)» |
| `STATUS.md`, §*Creación expediente en sudespacho* | «Tags CRM mapeados ✅ — **87 tags auditados**, IDs constantes en `sudespacho_create.py`» |

**Por qué no se arregló al detectarlo, que es lo que hay que entender antes de tocarlo.** No se
puede dirimir desde el repo, y **el código no sirve de árbitro** porque mide otra cosa: lo que
`core/sudespacho_create.py` contiene son los tags **mapeados** —medido el 2026-08-03: **13
`TAG_VERDE` + 4 `TAG_LILA` + 7 `TAG_AZUL` = 24 constantes**—, no los **auditados** del catálogo del
CRM, que es a lo que se refieren el 96 y el 87. Inventar un número para que cuadre habría sido peor
que la contradicción.

**Hipótesis de reconciliación, sin confirmar:** que 87 y 96 sean dos momentos de la misma auditoría
(87 antes, +9 después) o que 96 sea el catálogo completo y 87 los efectivamente revisados. Las dos
son plausibles y ninguna está anclada.

**Cómo se dirime, y es más barato de lo que parece.** El atlas del CRM registra un endpoint de
lectura que no requiere UI:

```
GET /api/tags/{id}    → "Retrieves the collection of Tags", auth apiKey, 2 params
```

(`docs/CRM_SUDESPACHO_ATLAS.md` §Tag, junto a `POST`/`PUT`/`DELETE`.) **Cautela:** el path declara
`{id}` pero la descripción dice «collection» — en esta API el segmento suele ser el **tipo de
elemento** (`{element}` en el resto de la familia), así que la primera llamada es de descubrimiento.
Con la colección en mano se cuenta, se compara contra las 24 constantes de `sudespacho_create.py` y
se deja **una sola** cifra en `STATUS.md`, con su fecha de medición, según la forma que ese fichero
adoptó el 2026-08-03.

**Prioridad: baja.** Ningún módulo consume esos dos números —son prosa histórica de mayo— y el
sistema de tags funciona: `tag_defaults_for_tipo_caso` resuelve por las 24 constantes, no por el
recuento. El coste de dejarlo es que `STATUS.md`, que se declara «fuente de verdad única», contiene
una contradicción interna sobre un dato del CRM.

**Disparador de promoción:** que haya que tocar el catálogo de tags (alta de un tipo de caso nuevo,
cambio de color en el CRM) — ahí conviene partir de un censo real, no de dos cifras que no cuadran.
O decisión de Nikolai.

**Coste estimado.** Bajo: una llamada de descubrimiento, un recuento y una línea en `STATUS.md`.
Lo caro sería auditar los 96 tags a mano por la UI, y eso no hace falta para cerrar esto.

## 120. El registro de ocurrencias del pull CRM escribe en un caso prestado sin pasar el guard

> **[ABSORBIDO → `PLAN.md` fila #15, V1]** (2026-08-24). El disparador se cumplió el mismo día en
> que se escribió: la rev. 5 de la spec de apertura integral **mete el pull de Sudespacho en V1**,
> y el gate de workspace de H3-01 es criterio de esa vertical. Deja de ser backlog: V1 no puede
> cerrarse con esta escritura saltándose el guard. Se conserva aquí la medición; el estado de
> ciclo de vida vive en `PLAN.md`.

*Origen: verificación de la evidencia de H3-03 al adjudicar la revisión adversarial R3 de la
apertura integral (2026-08-24). El revisor lo aportó como evidencia de otro hallazgo; como defecto
propio no estaba levantado.*

En `core/sync_sudespacho.py`, `pull_expediente_v2` persiste el registro de ocurrencias
(`ocurrencias.save()`, `:1467-1479`) **antes** de llamar a `guard_escritura` (`:1486`). El orden es
deliberado y está razonado en el propio código (N2: el universo de lo que el CRM enumera debe
sobrevivir a un fallo de descarga posterior, o la puerta de integridad de la vista procesal no
comprueba nada). El efecto colateral no está declarado: si el caso está `prestado` o en
`conflicto`, esa escritura de protocolo alcanza la ruta canónica del Drive **sin pasar el guard y
sin declararse `es_protocolo=True`**, que es el mecanismo previsto para las escrituras del propio
protocolo.

**Por qué no es un hallazgo de la revisión.** Como evidencia de «el protocolo durable no permite
recuperar efectos cruzados» es débil: no habla de recuperación. Como defecto de la disciplina del
guard es real y verificable, y por eso baja aquí en vez de quedarse en la adjudicación.

**Prioridad: baja.** El fichero de ocurrencias es del protocolo, no prueba del expediente, y su
contenido es reconstruible desde el CRM. Lo que se pierde es la propiedad de que *toda* escritura
en un caso prestado pase por el guard — la que hace auditable el checkout.

**Disparador de promoción: CUMPLIDO** el 2026-08-24 —la primera de las tres vías previstas, «que se
toque `pull_expediente_v2` por otra razón»—. Las otras dos siguen valiendo si esto se reabriera:
que la Fase 2 de la arquitectura dual arregle el lock, o que un checkout real recoja un
`_registro_ocurrencias` con huellas de una corrida ajena.

**Coste estimado.** Bajo: llamar al guard con `es_protocolo=True` y un test que fije la
exención de forma explícita en vez de por omisión.

---

## 121. El criterio «ninguna ruta crea carpetas fantasma» no tiene barrido que lo demuestre

**Disparador:** ninguno todavía — lo levantó la **R8/H8-08** al adjudicar el cierre de la Fase 1
dual (2026-08-25). No bloquea nada hoy; es una **afirmación más ancha que su prueba**, que es
justo la clase de deuda que este backlog existe para no perder.

**Estado actual.** El criterio de salida (2) de la Fase 1 dice: *ninguna ruta del código crea un
directorio bajo `CASOS_ROOT` para una identidad que el catálogo no conoce*. Lo que hay para
sostenerlo son dos piezas, y ninguna es universal:

- **El plano 2 del arnés contractual** (`tests/_matriz_contractual.py`) compara `CASOS_ROOT`
  alrededor de la copia de trabajo antes y después. Pero solo observa **lo que la matriz
  ejecuta**: hoy, los tres comandos de `sala_maquina`. Un escritor al que la matriz no llame es
  invisible para él.
- **`tests/test_guard_localizador.py`** mantiene a cero el censo de `path_for(..., strict=False)`.
  Cuenta llamadas AST a **esa** escotilla; no ve a quien componga `settings.casos_root / algo` a
  mano, ni a quien use otra API.

El revisor propuso la comprobación que lo demuestra, y es concluyente: añadir en una copia una
función de producción **no invocada** que haga `(settings.casos_root / 'W-FANTASMA').mkdir()`.
La matriz y el guard siguen verdes. No existe inventario de **escritores**.

**Mejora propuesta.** Un guard AST hermano del del localizador, que enumere los sitios de
producción donde se llama a `mkdir`/`write_text`/`open(..., 'w')` sobre una expresión derivada de
`settings.casos_root`, `caso_path(...)` o `path_for(...)`, y fije el censo con la misma polaridad
—**solo puede encoger**—. La parte difícil no es el AST: es decidir qué cuenta como «derivada»
sin producir tantos falsos positivos que alguien lo desactive. Empezar por el caso literal
(`settings.casos_root / X` seguido de `.mkdir`) ya cerraría el hueco que el revisor demostró.

**Justificación de no aplicarlo ahora.** La Fase 1 se cierra con el criterio **acotado por
escrito** en `PLAN.md` («se cumple para los caminos ejercitados, no universalmente») en vez de
afirmado entero, que es la corrección honesta y cuesta una frase. El barrido es trabajo con
diseño propio —la heurística de «derivada de» es la pieza cara— y hacerlo bajo el plazo de una
remediación es cómo se compran guards que nadie mantiene.

**Coste estimado.** ~2 h el guard literal con su prueba de mutación; +2-3 h si se persigue la
derivación indirecta (variable intermedia, atributo de dataclass, retorno de helper).

---

## 122. El `client_id` compartido de rclone deja de funcionar en 2026 — y el perfil expuesto no es este

**Disparador:** ninguno inmediato, pero **plazo externo con fecha**. Lo levantó el handoff de la
migración al perfil `procesal@` (`docs/superpowers/handoffs/handoff-2026-08-14-migracion-procesal-continuacion-tnm33.md`,
§3) al instalar rclone allí, y quedó como «candidato a este backlog» sin escribirse. Verificado
contra la fuente el 2026-08-25: rclone lo dice como **obligación, no como consejo** —
«*This shared client_id is being retired and will stop working during 2026. To avoid interruption
you must create and use your own client_id*» (https://rclone.org/drive/#making-your-own-client-id).

**Estado actual, medido el 2026-08-25 y no supuesto.** El aviso del handoff daba a entender una
deuda general; no lo es. En `tnm33` los **dos** remotes —`gdrive_ev` y `gdrive_tl`— tienen
`client_id` **propio** (72 caracteres, el formato de un cliente OAuth real, no el compartido de
rclone). rclone v1.73.5. Medido sin volcar la configuración: se comprueba **si el campo está
vacío**, nunca su valor ni el `client_secret` adyacente (`docs/DEAD_ENDS.md`, `rclone config show`
expone secretos).

**Lo que queda sin verificar, y es el hueco entero.** El remote `gdrive_tl` del perfil
`Nikolai Tyukhay 1` se configuró el 2026-08-14 por OAuth desde cero, y su `rclone.conf` **no es
legible desde `tnm33`** (`Permission denied` sobre el perfil ajeno, comprobado). Si ese remote
quedó con el campo vacío, es el único punto de la máquina que dejará de funcionar durante 2026. La
comprobación solo puede hacerse **desde ese perfil**, y es una línea.

**Radio si se cumple el plazo sin actuar.** rclone es el motor del checkout/checkin del
repositorio de casos y de los `pull` del Drive: 15 ficheros de producción lo mencionan —mención,
no llamada medida— más las skills `checkout-caso` y `checkin-caso`, cuyos `.cmd` lo invocan
directo. Un remote sin `client_id` propio deja de autenticar y con él cae la vía de préstamo de
expedientes de ese perfil.

**Mejora propuesta.** No es «crear un `client_id`»: ya existe uno que sostiene los dos remotes de
`tnm33`. Los pasos, en orden de coste creciente: (1) desde el perfil procesal, comprobar si
`client_id` de `gdrive_tl` está vacío; (2) si lo está, **reutilizar el proyecto de Google Cloud que
ya usan los remotes de `tnm33`** —copiar `client_id`/`client_secret` al remote y reautorizar—, que
es configuración, no montar un proyecto; (3) dejar constancia de **dónde vive ese proyecto**, dato
que hoy no consta en ninguna parte del repo y que convierte el paso (2) en arqueología si se
pierde. Ojo al pasar el `client_secret` entre perfiles: por variable de entorno o LastPass, nunca
por `C:\Users\Public` (regla 7 del handoff v5) ni por el chat.

**Justificación de no aplicarlo ahora.** El perfil expuesto es el **secundario**, su único remote
es `gdrive_tl`, y el paso que decide si hay algo que arreglar no se puede ejecutar desde aquí. Ir
más lejos sería crear un `client_id` nuevo sin saber si hace falta, duplicando proyectos de Google
Cloud para el mismo despacho — que es la clase de trabajo que parece diligencia y deja dos cosas
que mantener donde había una.

**Coste estimado.** ~10 min la comprobación (1) desde el perfil procesal; ~15 min el (2) si el
campo está vacío; el (3) es una línea en `docs/INTEGRACION_SUDESPACHO.md` o donde se documente la
config de rclone. Solo si el proyecto existente no se localiza: +1 h para crear uno y reautorizar
los tres remotes.

---

## 123. La poda del worktree no puede cerrarse al cerrar: `.claude/worktrees/` acumula carcasas

**Disparador:** medido el 2026-08-25 al podar el worktree del 67º cierre. `.claude/worktrees/`
tenía **10 directorios y `git worktree list` reconocía 1** (más la raíz). No bloquea nada —las
carcasas están vacías— pero es una acumulación silenciosa en el árbol de trabajo, y su causa no es
la que parece.

**Estado actual.** `git worktree remove <ruta>` ejecutado **desde dentro** de ese worktree falla en
Windows con `Permission denied`; `rmdir` y `rm -rf` fallan con `Device or resource busy`. Lo que
ocurre es que git **sí borra el contenido y sí desregistra** el worktree, y solo no puede quitar el
**directorio raíz**, porque el proceso que lo tiene como directorio de trabajo lo retiene. Queda
una carcasa de 0 ficheros que git ya no conoce.

**Y aquí está el hallazgo que cambia el remedio: no es descuido, es estructural.** Del censo de 10,
al barrer quedaron exactamente **2 sin borrar**, y son **los dos que tenían sesión viva encima**.
Los 8 restantes se fueron sin resistencia. Es decir: **en el momento del cierre la limpieza es
imposible por construcción** —la sesión que debe borrar el directorio es la que lo está
ocupando—, y solo es posible **después**, cuando ese proceso ya no existe. Prueba independiente
recogida el mismo día: el único huérfano con contenido llevaba un `.claude/settings.local.json`
escrito a las 14:34 cuyo permiso concedido era, literalmente, `rmdir` de su propio worktree — otra
sesión había chocado con la misma pared unas horas antes y tampoco pudo terminar.

**Consecuencia para el protocolo.** `docs/FLUJO_GIT.md §4` manda `git worktree remove` «desde la
raíz, nunca desde dentro», que es correcto pero **no se puede cumplir cuando el agente que cierra
vive dentro del worktree que poda**. El paso queda por definición a medias, y `scripts/session_close`
no lo comprueba: sus avisos cubren `STATUS`/`PLAN`, trabajo sin publicar y coherencia `PLAN`↔git,
pero **no** «¿queda un directorio en `.claude/worktrees/` que git no reconozca?».

**Mejora propuesta.** Dos piezas, y la primera sola ya cierra el 90 %:

1. **Barrido en la APERTURA, no en el cierre.** Un aviso —o una poda directa, que es segura— al
   abrir sesión: listar `.claude/worktrees/`, cruzar con `git worktree list --porcelain`, y para
   cada huérfano **vacío** borrarlo; para cada huérfano **con contenido**, avisar y no tocar. La
   asimetría importa: un huérfano con ficheros puede ser trabajo sin publicar de una sesión que
   murió, y ahí borrar es la operación equivocada.
2. **Aviso en `session_close`**, en la misma familia que los actuales: «quedan N carcasas en
   `.claude/worktrees/`; se limpian en la próxima apertura». No debe intentar borrar la propia
   —fallará siempre— sino **dejar dicho que el paso no terminó**, que es justo lo que hoy no consta.

**Cuidado documentado, aprendido al barrer.** El barrido debe tratar `.claude/settings.local.json`
como lo que es —caché de permisos— pero **no darlo por muerto**: al barrer con `rm -rf` se borró el
de una sesión **viva**, que perderá los permisos que ya tenía concedidos. Un barrido de apertura
solo debería tocar directorios **completamente vacíos**, y dejar el resto al aviso.

**Justificación de no aplicarlo ahora.** El síntoma es cosmético: carcasas de 0 ficheros en una
carpeta ignorada. Lo que lo hace digno del backlog no es el residuo sino el **paso de protocolo que
no se puede cumplir** — y arreglar eso toca `session_close` y `FLUJO_GIT.md §4`, que es trabajo con
diseño propio y no se hace de paso al cerrar una sesión.

**Coste estimado.** ~1 h el barrido de apertura con su test (la parte fina es la guarda de
«vacío»); ~30 min el aviso de `session_close`; +15 min la frase de `FLUJO_GIT.md §4` que reconozca
que el paso se completa en la apertura siguiente.

### 123-bis. La poda tiene DOS mitades, y el protocolo solo nombra una

**Añadido el 2026-08-25, con la medida que lo destapó.** Mismo residuo que arriba —trabajo cerrado
que nadie retira— pero en las **ramas**, no en los directorios. Va aquí y no en entrada nueva
porque comparte causa, remedio y el momento en que se puede aplicar.

**Lo medido, al barrer lo acumulado en una sola sesión:** **14 borrados sobre 9 ramas distintas**,
todas con su PR en `MERGED`. El desglose es lo interesante:

| | ramas |
|---|---|
| Rancias en **local** | 8 (PRs #214-#219, #226, #227) |
| Rancias en **remoto** | 6 (PRs #208, #214-#218) |
| **En los dos lados a la vez** | **5** (#214, #215, #216, #217, #218) |
| Solo en local | 3 (#219, #226, #227) |
| Solo en remoto | 1 (#208) |

Que solo 5 de 9 coincidan es el hallazgo: **la poda se hace a medias con frecuencia, y no siempre
por el mismo lado**. Tres ramas se quedaron vivas solo en local (alguien borró en `origin` al
mergear y no en su clon) y una solo en remoto (al revés). No es un descuido puntual: es lo que pasa
cuando el merge lo hace una máquina y la poda otra.

**Por qué ocurre.** `FLUJO_GIT.md §4` nombra `gh pr merge --delete-branch` y el `git branch -d`
local, que cubren el caso feliz —merge y poda en la misma sesión, en la misma máquina—. Fuera de
ese caso no hay nada: si el `--delete-branch` no corre (merge desde la web, desde el móvil, o un
`--squash` lanzado sin la bandera), o si la sesión que mergea no es la que tenía el clon, queda
media rama viva **y nadie vuelve a mirar**. `session_close` tampoco lo comprueba: su aviso
`PLAN.md`↔git mira lo contrario —ítems que citan ramas que git ya no conoce—, no ramas que git
conoce y ya no cita nadie.

**Mejora propuesta**, hermana de la de arriba y con la misma forma: en el barrido de **apertura**,
censar `git branch` y `git ls-remote --heads origin`, cruzar cada una con `gh pr list --head <rama>
--state all` y **listar** (no borrar sin más) las que estén en `MERGED`. La puerta debe ser el
estado del PR **comprobado en el momento**, no un censo previo. Nunca tocar `main` ni una rama con
worktree vivo, y **registrar el SHA antes de borrar**: revivir una rama es
`git push origin <sha>:refs/heads/<rama>`, pero solo si alguien apuntó el SHA.

**Y una lección de método del propio barrido, que casi lo estropea.** Un `push --delete` falló por
un timeout de red y mi primera reacción fue suponer que el fallo era de mi `grep`, no del borrado.
No lo era: la rama seguía viva y el informe habría dicho «seis borradas» con una intacta. Lo
destapó comprobar contra `origin` en vez de contra la salida que yo mismo había parseado. Quien
implemente el barrido: **verificar el resultado contra el remoto, no contra el código de salida del
comando** — es la misma regla de `INTEGRACION_SUDESPACHO.md §14.6`, verificar por resultado y nunca
por status.

**Justificación de no aplicarlo ahora.** Igual que arriba: el residuo es inerte y el trabajo tiene
diseño propio. Con un matiz que lo hace **menos** urgente que el barrido de directorios: una rama
rancia no estorba a nadie hasta que hay tantas que el censo deja de leerse, mientras que las
carcasas de worktree ensucian un directorio que se mira a diario.

**Coste estimado.** ~45 min sobre el barrido de apertura una vez exista (reutiliza su esqueleto);
la parte cara no es el cruce sino decidir si **lista** o **borra**, y para el remoto la respuesta
prudente es listar.

---

### 124. `es_copia_prestada` es INERTE en producción, y nueve tests verdes lo defienden

**Añadido el 2026-08-26, con la medición que lo destapó.** Lo encontró la **R16** revisando el
diseño del Plan 3A-bis, y **no es de ese plan**: es un defecto vivo de la capa de la Fase 1 dual /
`MEJORAS #96`, anterior a él. Se anota aquí, con su medida, en vez de arreglarlo de paso dentro de
una tanda que no le corresponde.

**Qué debería hacer.** `core/case_manager.es_copia_prestada(case_id)` es la **primera rama** de
`guard_escritura`: si la ruta resuelta del caso es una copia local conocida y no el canon, la
bandeja no aplica y la escritura procede al árbol local (`MEJORAS #96`).

**Qué hace.** Devuelve `False` siempre. La condición no puede ser verdad, por dos hechos que se
tocan:

- `case_locator.buscar()` mira **solo** bajo `CASOS_ROOT` —plano, por ciudad, y por ciudad de
  reserva (`core/casos/case_locator.py:121-143`)—. Nunca devuelve una ruta fuera del catálogo, y
  **no consulta el registro de workspaces**.
- El registro **solo** contiene rutas fuera del catálogo: el resolver rechaza registrar una bajo él
  (`WORKSPACE_UNDER_CATALOG_ROOT`, `core/casos/workspace_model.py:225`).

Se compara una ruta que siempre está en el catálogo contra un conjunto que nunca contiene rutas del
catálogo.

**Medido el 2026-08-26**, con una copia local real registrada fuera del catálogo, como manda el
contrato:

```
buscar() devuelve      : <CASOS_ROOT>/BaXX1 - … - (W-SONDAEC) - NEGATIVA_OFERTA
copia local registrada : <TEMP>/Desktop/BaXX1 - … - (W-SONDAEC) - NEGATIVA_OFERTA
es_copia_prestada      : False
```

El revisor lo midió por su cuenta y obtuvo lo mismo (`PROBE_B_ES_COPIA False`).

**Y el docstring de la propia función contiene las dos mitades de la prueba, tres párrafos aparte.**
Dice *«El canon nunca está ahí: el resolver rechaza registrar una ruta bajo el catálogo»* — como
razón para **confiar** en el registro, sin notar que lo que se compara contra el registro es
siempre el canon. **Escribir la razón correcta no es comprobarla.**

**Por qué la suite no lo caza, que es la mitad interesante.** `tests/test_guard_copia_prestada.py`
tiene nueve tests verdes sobre esta rama. Pasan porque su helper `_registrar_como_copia_local`
(`:81-87`) da de alta `local_path=caso_path(case_id)` —**el canon**— llamando a `registro.alta`
directamente, **sin pasar por el resolver que lo prohíbe**. La fixture fabrica el estado que
producción tiene prohibido, y en ese estado la rama sí funciona.

Es un caso de libro de **«un test puede defender el defecto»**: no es falta de cobertura, es
cobertura al revés. Añadir tests no lo encuentra; hay que preguntar **quién** lo defiende. Y es la
misma forma que la **«resta inerte»** que la prueba de mutación del Task 7 de la Fase 1 ya encontró
en esta misma arquitectura (quitar `MUTATE_CANONICAL` de un modo que nunca la tuvo). Segunda
aparición de la clase, en la capa de al lado.

**Qué se rompe hoy, sin inflarlo.** Con la función siempre `False`, toda escritura sobre un caso que
esta máquina tiene sacado cae por la rama del estado del canon: `prestado` → **desvío a la bandeja**.
No hay pérdida de datos ni corrupción; hay una rama diseñada, probada y **muerta**, y un desvío que
ocurre donde el diseño decía que no debía ocurrir. Lo caro es la **falsa cobertura**: nueve tests
afirman que el discriminante funciona.

**Mejora propuesta.** No es «arreglar la comparación»: es decidir **quién** contesta la pregunta.
El repo ya tiene la pieza que sabe cuál es la copia de trabajo —`CaseWorkspaceResolver`, con
`CaseWorkspace.working_root`— y el guard no la usa. Las opciones, sin elegir aquí:

1. `guard_escritura` recibe (o resuelve) un `CaseWorkspace` y pregunta por `working_root`, en vez de
   comparar una ruta de catálogo contra el registro.
2. `es_copia_prestada` deja de existir y su pregunta se contesta en el resolver, que es donde vive
   el modelo de capacidades.

**Disparador:** la **Fase 2** de la fila #3 (los 6 defectos del frontal), que es donde el resolver
se cablea de verdad; o la **rev. 2 del Plan 3A-bis**, si su regla de sellado necesita distinguir la
copia local — que es exactamente el punto en que R16 lo destapó.

**Condición de cierre, y es dura:** el arreglo **no vale** si los nueve tests siguen pasando con la
fixture actual. Hay que rehacer la fixture para que registre una copia **fuera** del catálogo —el
estado que producción sí produce— y comprobar que la rama muere sin el arreglo. Un guard sin prueba
de mutación no es un guard, y una fixture que fabrica el estado imposible no es una prueba.
---

## 125. Los tres manifiestos `.dxt` de Claude Desktop cablean UN intérprete, y por eso se apagaron los tres a la vez

**Estado:** pendiente. Detectado el 2026-08-31 al reparar los conectores de Claude Code (PR #253).

Los tres conectores que corren en **Claude Desktop** —`expedientes-xl`, `gmail-multiaccount`,
`google-despacho`— arrancan desde su `dxt-build/manifest.json`, y los tres cablean el **mismo**
intérprete literal:

```
"command": "C:\\Users\\tnm33\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe"
```

**Qué pasó, medido.** El 2026-08-23 un `pip install --user mcp` sin pin trajo `mcp 2.0.0` al site
de usuario de ese intérprete. La 2.0 retiró `mcp.server.fastmcp`, que es la API que importan los
cuatro servers del despacho. Consecuencia que no se vio en su momento: **los tres conectores de
Claude Desktop estuvieron caídos del 2026-08-23 al 2026-08-31**, igual que los de Claude Code, y
volvieron solo porque la reparación (`pip install --user "mcp>=1.28,<2"`) tocó ese mismo
intérprete. Nadie lo notó porque el badge del panel de Desktop ya miente por otra razón conocida
(health-check que expira en frío, ver `docs/DEAD_ENDS.md`), así que un conector muerto y un
conector lento se ven igual.

**Por qué NO se arregló en el PR #253.** El `.dxt` empaqueta una **copia** del código y del
manifiesto; cambiar el manifiesto fuente no mueve nada hasta que se **reconstruye el `.dxt` y se
reinstala a mano** en Desktop (borrar la vieja por la papelera del panel + importar el nuevo, con
bump de `manifest.version`). Eso es un paso manual de Nikolai, no del PR, y dejar el fuente
«arreglado» sin desplegar es justo la trampa que `DEAD_ENDS` ya documenta. Además el empaquetador
del plugin declara `dxt-build` «subproducto, no tocar».

**Mejora propuesta.** Que los tres manifiestos dejen de cablear un intérprete concreto y arranquen
por el **wrapper** correspondiente (`plugins/<conector>/run_server.bat`), que desde el PR #253
resuelve el intérprete **por capacidad** (prueba `import mcp.server.fastmcp` y falla ruidosamente)
en vez de por ruta que existe. Con eso los dos frentes —Code y Desktop— comparten una sola
resolución y un solo sitio que arreglar. Atención al detalle que sí cambia entre frentes: el
wrapper **no** redirige en la línea del intérprete (Claude Code cierra la conexión si lo hace), y
Desktop recoge el stderr por su cuenta, así que la pérdida del log propio es asumible.

**Disparador:** la próxima vez que haya que reconstruir cualquiera de los tres `.dxt` por otro
motivo — no merece una reinstalación manual de tres extensiones solo por esto, mientras el pin
`mcp<2` de los `requirements.txt` sostenga la causa raíz.

**Condición de cierre:** los tres manifiestos arrancan por wrapper, `.dxt` reconstruidos y
reinstalados, y verificación **por resultado** (no por el badge): `%APPDATA%\Claude\logs\main.log`
con `[LocalMcpServerManager] Connected to <server> (N tools)` para los tres, o una tool exclusiva
de cada uno respondiendo.


---

## 126. Cuatro entrypoints escriben en el expediente SIN pedir el mutex `[PROMOVIDO → PLAN.md]` `[RESUELTO 2026-09-05 para 3 de 4; el 4º y la UI, declarados]`

> ✅ **Resuelto el 2026-09-05 (PR #292) para TRES de los cuatro:** `export_label_emails`,
> `atomize_emails` y `sync_sudespacho` (`pull`, `intake_judicial`, `sync_all` por caso) sostienen
> el mutex a través de un helper único, `scripts/_mutex_cli.py` (`sostener`, `w_code_de`,
> `w_code_de_ruta`), desde ANTES de la primera escritura —en el export esa escritura es la
> **reserva del lote**, no el motor— y abortan con código 2 y cero bytes si el caso está tomado
> (`sync_all` lo sostiene por caso: el ocupado se salta y se resume, el barrido sigue).
> Diseño rev. 2 con la R1 de Codex adjudicada (§7, 9/9) en
> `docs/superpowers/specs/2026-09-05-mutex-en-los-entrypoints-de-intake-design.md`; la R2 sobre
> el diff, en su §8. Fronteras E7-E14 en `tests/test_entrypoints_mutex.py` (E13 son **dos
> procesos reales** con barrera, `tests/_bootstrap_e13.py`); 14 mutantes muertos.
> **Lo que queda abierto, con nombre:** (a) `scripts/crm_ficha.py`, el cuarto entrypoint, es de
> la sesión hermana y se cierra cuando ella cierre la acción 8; (b) la **UI de Streamlit**
> reserva el lote y exporta correo, y lanza el intake judicial, **sin mutex** (`streamlit_app.py`
> ~782 y ~1071); (c) el **alta de un caso nuevo por `pull`/`intake_judicial`** no tiene identidad
> que sostener: avisa y sigue, y la vía canónica de alta es `abrir_caso`. Y lo que el mutex NO
> da: exclusión, no cancelación (una pérdida de lease a mitad se conoce al salir). Texto original
> conservado como medición:

**Medido el 2026-09-01** durante la apertura de W-02X1WJ. El mutex de sesión **sí** está
cableado en `scripts/abrir_caso.py:649` y `scripts/sala_maquina.py:486`
(`mutex_sesion.sostenido`). Lo que no lo está es todo lo demás que escribe en el árbol del
caso:

```
scripts/export_label_emails.py   0 referencias a mutex_sesion
scripts/atomize_emails.py        0
scripts/sync_sudespacho.py       0
scripts/crm_ficha.py             0
```

**Por qué importa, y por qué no es teórico.** Los dos primeros escriben en `00_Input`, que es
justo lo que `sala_maquina apply` está leyendo durante una corrida de OCR de una hora. El
runbook lo advierte en `[APER-39]` con su coste medido —~1h40 de OCR repetido más huérfanos
que hay que borrar a mano— pero la advertencia vive en prosa, no en código. En esta sesión
la regla la sostuve yo: retuve a mano el export y la atomización tres veces mientras corría
el OCR. Y `sync_sudespacho pull` es el peor de los cuatro, porque el propio `[APER-37]`
manda ejecutarlo **justo antes** del `apply`.

Nótese el contraste que hace el caso: cuando retuve el pull de `--fuente drive_ev`, el mutex
lo habría bloqueado con `CaseBusy` de todas formas. La disciplina manual solo era
load-bearing en los caminos que no lo tienen.

**Mejora propuesta.** `mutex_sesion.sostenido(CaseRef(w_code=…))` en los cuatro entrypoints,
con el mismo tratamiento de `CaseBusy` que ya usa `sala_maquina` (salida 2, mensaje útil, sin
traceback). No toca `case_mutex.py`, que lleva cuatro rondas y 17 mutantes: solo añade
adquirentes.

**Radio de daño:** decide quién puede escribir sobre el árbol del caso → **dos rondas** de
revisión adversarial por la regla de `CLAUDE.md` §«Cuántas rondas».

**Condición de cierre:** los cuatro entrypoints adquieren; un test que lance dos de ellos en
paralelo sobre el mismo W-code y exija `CaseBusy` en el segundo; y un mutante por entrypoint
que, al retirar la adquisición, ponga ese test en rojo.

---

## 127. `--modo v1` es una puerta, no una secuencia: el orden lo sostiene quien ejecuta

**Medido el 2026-09-01.** La apertura completa de W-02X1WJ fueron doce pasos encadenados a
mano: alta CRM judicial → `abrir_caso` → `register_expediente` → `sync_sudespacho pull` →
`sala_maquina apply` → `export_label_emails` → `atomize_emails` → segundo `apply` →
`organizar-sala-lectura`. Las dependencias de orden —`[APER-37]` (atomizar y pullear ANTES
del apply) y `[APER-39]` (no relanzar sin comprobar que la corrida anterior terminó)— las
sostuve recordándolas, no el código.

Esto ya está declarado en el runbook §3: «hoy es una PUERTA, todavía no la secuencia», y el
Plan 5 de la fila #15 de `PLAN.md` es donde vive. Esta entrada **no abre trabajo nuevo**: deja
constancia de una apertura real ejecutada entera a mano, como evidencia de coste para cuando
se priorice ese plan.

**Disparador:** el Plan 5 de V1. No antes.

---

## 128. No hay orquestador de ficha CRM judicial, y ahora hay material para cerrarlo

`[APER-49]` lo declara: `crm_ficha.py` es extrajudicial-only. **Medido el 2026-09-01**: la
ficha judicial de W-02X1WJ (expediente 682) salió de seis llamadas a mano —
`create_expediente_judicial`, `link_ev_mmc_judicial`, `link_contrario_judicial`,
`link_colaborador_judicial`, más la secuencia de `autos`/juzgado.

**Lo que esta sesión aporta y antes no existía:** la secuencia de juzgado quedó **confirmada
en vivo**, incluido el alta de un juzgado nuevo (`POST /api/element_register/juzgados` → 201),
que `INTEGRACION_SUDESPACHO.md §12.5` daba por «previsiblemente» y sin capturar. También
quedaron documentadas dos trampas: la property del nombre es `nombre`, no `Juzgado`, y
`num_asunto`/`juzgado` del expediente salen **vacíos** aunque el cableado sea correcto.

**Mejora propuesta.** `link_juzgado_judicial(exp_id, juzgado_id, num_autos, fase)` en
`core/sudespacho_relations.py` (resolviendo el enum antes de escribir) y `crm_ficha --judicial`
que orqueste las seis llamadas.

**~~Límite conocido, no resoluble aquí~~ — REFUTADO el 2026-09-04.** Este párrafo decía que
«no hay ruta REST de LECTURA de relaciones» y que verificar los vínculos por resultado «solo es
posible por UI». **Falso:** el 405 es de `relation_element`, pero la lectura vive en
`GET /api/related_register/{element}/{id}`, cableada en
`core.sudespacho_relations.get_relaciones()`. El orquestador judicial que pide esta entrada
**puede** verificarse por resultado como ya hace el extrajudicial.

**Disparador:** el siguiente caso que nazca judicial.

---

## 129. La cobertura se llavea por `(slug, rel_path)` y los artefactos por `slug`

**Medido el 2026-09-01, W-02X1WJ.** `Anexo a oferta.pdf` existe **dos veces** en el Drive de
E&V —en `RECLAMACIONES` y en `ARRAS ／ OFERTA`— con sha256 idéntico. El intake depositó las
dos copias (correcto: `00_Input` es espejo fiel). Como el slug se compone de nombre + prefijo
del hash, **ambas rutas producen la misma carpeta de salida**, y la cobertura acabó con
**cuatro filas para dos ficheros**:

```
__d01_ACTUACION_PROCESAL  sha 3f15e25a…  rel …/ARRAS ／ OFERTA…/Anexo a oferta.pdf
__d02_DOC_ARRAS           sha 9da56f94…  rel …/ARRAS ／ OFERTA…/Anexo a oferta.pdf
__d01_ACTUACION_PROCESAL  sha 6ffd5360…  rel …/RECLAMACIONES/Anexo a oferta.pdf
__d02_DOC_ARRAS           sha 05921e33…  rel …/RECLAMACIONES/Anexo a oferta.pdf
```

El OCR no es determinista byte a byte (metadatos, Ghostscript), así que las dos pasadas sobre
el mismo original dieron ficheros distintos y una pareja de filas queda desfasada **por
construcción**. `verificar_integridad_bundles` sale con código 3 y **`--solo` no converge**:
reprocesar una copia hace casar sus dos filas y deja rancias las otras dos; reprocesar la otra
invierte el problema. Se comprobó ejecutando ambas.

**Por qué se repetirá:** en los Drive de E&V el mismo documento en dos carpetas es lo normal,
no la excepción.

**Remedio aplicado en el caso (no es la solución):** poda de las dos filas huérfanas con
respaldo en `_cobertura.json.bak`; `00_Input` intacto.

**Mejora propuesta.** Que la fila de cobertura se funda por `slug` y transporte las
procedencias en lista —`DocLogico` ya tiene `fuentes: list[str]`, la asimetría es solo de la
fila de cobertura—; o que el guard compare por slug contra el sha del artefacto realmente
publicado.

**Condición de cierre:** un test que deposite el mismo sha desde dos rutas y exija que
`verificar_integridad_bundles` devuelva `[]`.

---

## 130. El guard de integridad escribe su diagnóstico donde no se lee

**Medido el 2026-09-01.** `sala_maquina apply` salió con código 3 y el fichero de salida de la
corrida en segundo plano contenía **solo** cuatro avisos de DPI de Ghostscript. La lista de
fallos —lo único que dice qué pasó— se emite con `typer.echo(..., err=True)` y no sobrevivió
al `2>&1` de la invocación. Hubo que reproducir `verificar_integridad_bundles` a mano en un
script aparte para saber que el problema era la entrada #129.

**Por qué importa más que el fallo que oculta:** el código 3 existe precisamente para que el
operador distinga «no empecé» de «terminé mal» (así lo dice el docstring de `_exigir_integridad`).
Un código de salida que distingue pero no explica obliga a reconstruir el diagnóstico cada vez.

**Mejora propuesta.** Persistir el listado junto a `_cobertura.json`
(`_integridad_fallos.txt`, sobrescrito por corrida) además de emitirlo por stderr. Dos líneas.

**Condición de cierre:** provocar el fallo de #129 en un caso de prueba y comprobar que el
fichero existe con las filas, sin depender de cómo se capturó la salida.

---

## 131. `fecha_de_nombre` devuelve la cadena `"0000-00-00"`, que es *truthy* `[PROMOVIDO → PLAN.md]` `[RESUELTO 2026-09-05]`

> ✅ **Resuelto el 2026-09-05 (PR #291), skill `organizar-sala-lectura` v1.15.** Se eligió
> la segunda vía: `fecha_de_nombre` conserva su contrato (la cadena va en nombres canónicos y
> en el manifiesto) y `scripts/preclasificar.py` exporta `SIN_FECHA`, `tiene_fecha(valor)` y
> `candidatos_sin_fecha(filas)`; el Paso 1-bis.d del `SKILL.md` **llama al helper** en vez de
> reescribir el filtro, y un guard exige que lo cite (guard de cita, no de semántica: R1/H-03).
> **R1 de Codex sobre el diff: REQUIERE-REVISION, 6 hallazgos, 6 confirmados** (3 remediados
> aquí; H-05 y H-06 preexistentes fuera de alcance → `#169`). Adjudicación en
> `docs/superpowers/plans/2026-09-05-mejoras-131-centinela-sin-fecha.md`. Condición de cierre
> cumplida por la rama «helper + la skill lo cita». Texto original conservado como medición:

**Medido el 2026-09-01**, montando la sala de lectura de W-02X1WJ. El Paso 1-bis.d de
`organizar-sala-lectura` obliga a consultar el espejo MD antes de escribir `0000-00-00` en un
binario opaco —es el paso que la propia skill marca como **no opcional**, porque saltárselo
dejó 7 binarios sin fechar en W-02VUDR—. Lo implementé con:

```python
sin_fecha = [f for f in filas if not f["fecha"] and f["ext"] in OPACOS]
```

`preclasificar.fecha_de_nombre` devuelve `_SIN_FECHA = "0000-00-00"`, una cadena no vacía. El
filtro dio **0 candidatos** y el paso quedó **completamente desactivado**, en silencio y con
apariencia de éxito. Al corregirlo comparando contra la constante: **47 candidatos, 27 fechas
recuperadas del espejo**.

**Por qué es el sentinel más peligroso del módulo:** falla hacia el lado que parece que
funciona. No hay excepción, no hay aviso, y el informe dice «0 binarios sin fecha», que es
exactamente lo que uno querría leer.

**Mejora propuesta.** Que `fecha_de_nombre` devuelva `None` cuando no hay fecha (y el llamador
formatee), o —si el valor centinela es deliberado por compatibilidad— exportar
`SIN_FECHA` y un `tiene_fecha(valor) -> bool` públicos, y que el `SKILL.md` diga
explícitamente «compara contra `SIN_FECHA`, nunca con `not`».

**Radio de daño:** no destruye datos, pero degrada en silencio el timeline del expediente,
que es el producto entero de la sala de lectura.

**Condición de cierre:** el test que hoy cubre `fecha_de_nombre` afirma también que el valor
de «sin fecha» es falsy, o que existe el helper y la skill lo cita.

---

## 132. El exportador de correo fabrica basenames que colisionan dentro del mismo lote

**Medido el 2026-09-01.** `export_label_emails` deja el mensaje **con** adjuntos en una
subcarpeta y el mensaje **sin** adjuntos plano en la raíz del lote, pero **da a los dos el
mismo** `<fecha>_<asunto_slug>.eml`. En W-02X1WJ eso produjo 6 pares en colisión; no eran
duplicados:

```
0507110a  9.191.442 B  …/2026-01-14_bf_recibido_<asunto>/<mismo nombre>.eml
c5e43cf2     21.889 B  …/2026-01-14_bf_recibido_<asunto>.eml
```

Dos mensajes del mismo hilo el mismo día. El discriminante existe **solo en el nombre de la
carpeta**, que es información que el basename no lleva.

**Consecuencia aguas abajo:** `layout_bundle_hilo` aborta con `ValueError` ante basenames
repetidos —correctamente, es su contrato—, así que la sala de lectura no se puede montar sin
desambiguar antes a mano.

**Mejora propuesta.** Que `eml_filename` añada un discriminante **estable** derivado del
`Message-ID` cuando el nombre ya esté tomado en el lote. Estable, no posicional: un contador
renumera entre corridas y pisa ficheros ya copiados (es la razón que el propio `SKILL.md` da
para prohibirlos en los anexos).

**Condición de cierre:** exportar una etiqueta con dos mensajes del mismo hilo, mismo día,
uno con adjuntos y otro sin, y comprobar que los dos `.eml` tienen nombres distintos.

---

## 133. `agrupar_por_hilo` recibe nombres y devuelve nombres: con colisiones, colapsa en silencio

**Medido el 2026-09-01.** Al agrupar los 58 `.eml` de W-02X1WJ pasé un **conjunto** de nombres
de hilo, como sugiere la firma de la función. Con los 6 basenames en colisión de la entrada
#132, el conjunto los fusionó y la membresía derivada perdió un mensaje de cada par —**y con
él sus adjuntos**: 19 documentos fuera de la sala, entre ellos los dos borradores del acuerdo
transaccional y los dos escaneados de la demanda.

**Cómo se detectó, que es lo que vale:** cuadrando el manifiesto contra un censo independiente
de `00_Input` (`104 filas` vs `105 sha únicos`), no releyendo el código. La misma técnica que
`feedback-migracion-verificar-recall-del-recorrido`.

**Mejora propuesta.** Que el contrato no permita expresar el error: aceptar pares
`(clave, id_único)` o devolver la membresía por índice, de modo que dos ficheros distintos no
puedan colapsar aunque compartan nombre. La función ya protege el caso simétrico
(`layout_bundle_hilo` aborta ante repetidos); esta es la puerta que quedó abierta.

**Condición de cierre:** un test con dos ficheros de distinto sha y mismo basename que exija
dos miembros en el grupo, no uno.

---

## 134. La skill obliga a consultar el espejo MD pero no da con qué extraer la fecha

**Medido el 2026-09-01.** El Paso 1-bis.d manda aplicar «la jerarquía de fecha del Paso 2»
(otorgamiento/firma → otra fecha inequívoca → nombre → `0000-00-00`) al texto del espejo, pero
no existe función que lo haga: cada sesión improvisa un regex. El mío falló de tres formas
distintas sobre documentos reales del expediente:

| Documento | Devolvió | Correcto | Causa |
|---|---|---|---|
| `Escritura.pdf` | `0000-00-00` | 1994-10-25 | mes y año en letra |
| `Update on Mortgage Operation - Caixa.pdf` | `0000-00-00` | 2025-12-02 | fecha en inglés |
| `Nota simple.pdf` | 1992-07-30 | 2025-11-14 | primera fecha del texto ≠ expedición |
| `Caixa Denial…pdf` | 2025-09-25 | 2025-12-04 | primera fecha = la solicitud citada |

Las cuatro hubo que corregirlas a mano tras leer el espejo. De 27 fechas «recuperadas», **23
quedaron marcadas `(*)`** (aproximadas) precisamente porque el heurístico no distingue
otorgamiento de mención.

**Mejora propuesta.** `fecha_del_texto(txt) -> (fecha, confianza)` en `preclasificar.py`:
meses en castellano y en inglés, años en letra, y **prioridad por marcadores de otorgamiento**
(«En … a …», «Fecha de expedición», «Date:») sobre cualquier otra fecha del cuerpo. Se escribe
una vez y se prueba una vez, contra un corpus de estos cuatro documentos.

**Condición de cierre:** los cuatro casos de la tabla, como test.

---

## 135. `--extraer-adjuntos` sigue en `False` por defecto, y eso deja prueba fuera del OCR

Con el default en `False`, los `.eml` adjuntos con MIME genérico (`application/octet-stream`)
son **invisibles** para la sala de máquina: `extract.py:117` los descarta por el fast-path y
solo aparecen si el flag los escribe a disco. Está documentado en el §55.1 de este mismo
fichero como «el arreglo de `#98`».

**Lo que esta sesión añade** es el coste en un caso judicial: en W-02X1WJ el flag activado
extrajo **41 adjuntos** y rescató 3 enlaces. Sin él, los certificados bancarios, los burofaxes
y los dos borradores del acuerdo transaccional se habrían quedado dentro de los `.eml`, sin
OCR y sin espejo MD — es decir, fuera de la sala de lectura y fuera de cualquier búsqueda.

**Nota de higiene:** esta entrada corrige una creencia mía anotada al revés en memoria
persistente («`--extraer-adjuntos` deja ciego al atomizador»). Se comprobó contra el §55.1 el
2026-09-01: el flag **es** el arreglo, no el problema.

**Estado:** ya es la casilla 3 de la fila #11 de `PLAN.md`, declarada «decidible, sin gates»,
a la espera de una decisión de Nikolai porque mueve la superficie de dedup de todo intake
futuro. Esta entrada solo aporta la medición que faltaba.

**Disparador:** la decisión de la fila #11.

---

## 136. Adoptar el CANON como copia local está permitido, y desactiva el desvío del guard `[PROMOVIDO → PLAN.md]`

> ✅ **RESUELTO el 2026-09-02.** Diseño, adjudicaciones de **R22 y R23** y el límite declarado (UNC ↔ letra de unidad, **sin verificar**), en
> [`2026-09-02-mejoras-136-el-canon-no-es-una-copia.md`](superpowers/plans/2026-09-02-mejoras-136-el-canon-no-es-una-copia.md).
> Prueba de mutación reproducible: `python -m tests._mutantes_mejoras_136`.
> **Cobertura de revisión de lo remediado tras R23: ausente.**

**Estado:** pendiente. **Defecto VIVO en `main`**, no latente. Detectado el 2026-09-02 por el
hallazgo **H21-01** de la R21 (revisión del diseño de `MEJORAS #124`) y **reproducido con sonda
propia** el mismo día. Es el defecto del que `MEJORAS #124` era el síntoma visible.

**Qué debería pasar.** El registro privado de workspaces es la lista de **copias locales**. El canon
no puede estar en él: es la invariante que `es_copia_prestada` cita en su docstring para confiar en
el registro, la que sostiene la derivación de «¿es el canon?» en el diseño de `#124`, y la que el
resolver hace cumplir con `WORKSPACE_UNDER_CATALOG_ROOT`.

**Qué pasa.** Esa invariante **no existe en la frontera que escribe el registro**. Solo la aplica
`resolver_por_ruta` (`core/casos/workspace_resolver.py:150-152`), que es un **lector**:

- `WorkspaceRegistry.alta` no comprueba `bajo_catalogo` — solo rechaza reusar la ruta de **otro**
  caso (`core/casos/workspace_registry.py:235-247`).
- `verificar_adopcion` comprueba cinco cosas —directorio, `MANIFEST_CHECKOUT.json`, W-code del
  nombre, canon en `prestado`, lock propio— y **ninguna** es «fuera del catálogo»
  (`core/casos/workspace_adopcion.py:68-105`).
- `adoptar` pasa el `case_dir` tal cual a `registry.alta`, y ésa es la vía del CLI productivo
  (`scripts/repository_cli.py`, subcomando `adoptar`).
- `resolver_por_identidad` consume la entrada **sin revalidar su raíz**
  (`core/casos/workspace_resolver.py:122-136`).

Y la condición es alcanzable porque **el canon también recibe `MANIFEST_CHECKOUT.json`** mientras
está prestado: `cmd_checkout` lo sube al Drive para que sobreviva a la muerte del Desktop (§3.3).
Ese hecho ya estaba escrito —es el argumento con el que se descartó el manifiesto como
discriminante— y nadie lo cruzó con la adopción.

**Medido el 2026-09-02**, con el canon prestado al propio usuario y máquina de quien adopta:

```
verificar_adopcion.ok  : True | checkout propio con manifest y nombre coherente
adoptar(CANON)         : ACEPTADO
registro contiene canon: True
estado del canon       : prestado
es_copia_prestada      : True
dir_intake             : <CANON>\00_Input\03_Email        ← SIN desviar
resolver .mode         : local_checkout
resolver .working_root : <CANON>
```

**Qué se rompe, sin inflarlo.** Tras esa adopción, **todo el intake escribe sobre el canon sin
desviar mientras el canon está prestado**: los cuatro consumidores del guard calculan su destino con
`caso_path`/`localizar`, así que el veredicto «no desvíes» los manda a la copia canónica, que es
justo la que hay que proteger. Además `resolver_por_identidad` devuelve `LOCAL_CHECKOUT` con
`working_root` = canon, o sea que un modo que el contrato define **sin** `MUTATE_CANONICAL` acaba
apuntando al canon: la resta de capacidad queda inerte por la vía del dato, no por la del código.

**Lo que NO es.** No es un fallo del checkout ordinario: `cmd_checkout` escribe la copia local y la
registra desde su propia ruta. La puerta es la **adopción** (§15), que existe para checkouts
anteriores al registro y pide firma humana. Que pida firma humana **no basta**: el comando imprime
lo que no pudo verificar, y «esta carpeta es el canon» no está entre lo que mira.

**Mejora propuesta.** Convertir «ninguna entrada apunta bajo el catálogo» en invariante **de
escritura y de lectura**, no de un solo lector:

1. Rechazo en `WorkspaceRegistry.alta` (la frontera que escribe).
2. Rechazo previo en `verificar_adopcion`, para que el motivo sea legible antes de la firma.
3. Revalidación al cargar y en `resolver_por_identidad`, no solo en `resolver_por_ruta`.
4. La comparación por **identidad física** de la ruta, no solo léxica: junctions y alias 8.3 de
   Windows convierten «no está bajo el catálogo» en una afirmación que la comparación de cadenas no
   sostiene.

**Condición de cierre, y es dura:** un test que ejecute `adoptar(<ruta del canon>)` y exija rechazo,
más un **mutante por cada una de las cuatro puertas** — quitar cualquiera de los cuatro rechazos
debe poner rojo su propio test y solo el suyo. Un guard sin prueba de mutación no es un guard, y
aquí la avería fue exactamente tener el rechazo en **un** sitio y creerlo global.

**Disparador:** la **rev. 2 del plan de `MEJORAS #124`**, que no puede derivar «¿es el canon?» del
modo mientras esta puerta esté abierta. Va **antes** que ella.

---

## 137. `revalidar` pisa la ruta de TODAS las entradas del mismo W-code

**Estado:** pendiente. **Preexistente**, no introducido por `MEJORAS #136`. Detectado el 2026-09-02
por el hallazgo **H23-05** de la R23, con sonda del revisor.

**Qué debería hacer.** `WorkspaceRegistry.revalidar(ref, local_path=…)` sella **una** entrada con el
`ahora` inyectado.

**Qué hace.** Toma `halladas[0]` para deducir el W-code y después reemplaza `local_path` en **todas**
las entradas que casan con el `CaseRef`. Y el registro contrata expresamente que dos entradas del
mismo W-code coexisten —un `checkout` y un `scratch` del mismo caso—, precisamente para que el
resolver pueda ver la ambigüedad en vez de que el registro elija por él.

Medido por el revisor con un checkout y un scratch legítimos del mismo caso:

```
antes
  checkout a -> …\workspace-a
  scratch  b -> …\workspace-b
despues de revalidar(w_code, local_path=a)
  checkout a -> …\workspace-a
  scratch  b -> …\workspace-a
```

La segunda ruta **se pierde** y el registro queda con dos entradas distintas apuntando al mismo
sitio — que es además el estado que `alta` se niega a crear.

**Qué NO se rompe hoy.** No se encontró llamador productivo de `revalidar` fuera de los tests. Por
eso es latente y no urgente, y por eso `MEJORAS #136` lo dejó fuera en vez de ensanchar su PR.

**Mejora propuesta.** Hacer inequívoca la entrada que se revalida —por ruta anterior, por nonce, o
por una clave propia— y modificar **solo** esa. Si el selector casa con más de una, lanzar ambigüedad
**sin escribir**, que es la misma polaridad que el resolver aplica al `AmbiguousCase`.

**Condición de cierre:** un test con checkout + scratch del mismo W-code que exija que la entrada no
seleccionada queda intacta, más un mutante que elimine la desambiguación y muera por él.

**Disparador:** el primer llamador productivo de `revalidar`, o la Fase 2 de la fila #3.

---

## 138. La unicidad de carpeta del registro compara cadenas, no identidad

**Estado:** pendiente. **Preexistente**, no introducido por `MEJORAS #136`. Detectado el 2026-09-02
por el hallazgo **H23-06** de la R23.

**Qué debería hacer.** `WorkspaceRegistry.alta` promete rechazar reutilizar **una carpeta** como
workspace de otro caso (`RutaYaRegistrada`).

**Qué hace.** Compara `os.path.normcase(str(path))` — cadenas. La misma carpeta escrita de dos
formas atraviesa la guarda:

```
samefile                 True
segunda alta             ACEPTADA
entry W-DUPA -> C:\…\duplicate_probe\same_workspace
entry W-DUPB -> duplicate_probe\same_workspace
```

Relativa frente a absoluta, y lo mismo con *junction*, alias 8.3 y el resto de alias físicos. El
resultado es **dos expedientes distintos compartiendo carpeta de trabajo**, que es exactamente lo que
la guarda existe para impedir.

**Es la misma clase que `MEJORAS #136`**, en la guarda de al lado: una propiedad sobre *carpetas*
comprobada sobre *cadenas*. Ahí ya existe la pieza que la contesta bien —`case_catalog.clasificar_bajo`
resuelve físicamente con `os.path.realpath`—, así que el remedio tiene dónde apoyarse.

**Mejora propuesta.** Para rutas que existen, comparar **identidad física**; para destinos que aún no
existen, componentes absolutos normalizados. Es la misma pareja de comparaciones que `#136` dejó
construida.

**Condición de cierre:** tests de relativa/absoluta, *junction* y 8.3 contra `RutaYaRegistrada`, con
un mutante por cada una de las dos comparaciones.

**Disparador:** el primer caso real de dos expedientes compartiendo carpeta, o la Fase 2 de la
fila #3.

## 139. `repository_cli checkin` no cubre la primera publicación de un caso nacido en local

`cmd_checkin` construye su plan de 3 vías desde tres inventarios: local, Drive y baseline
(`MANIFEST_CHECKOUT.json`). Un caso que **nace en local** —el modo `[APER-41]` del runbook, que
apunta `CASOS_ROOT` al Desktop para evitar los cuelgues de `G:`— no tiene ninguno de los dos
últimos: no hubo checkout, así que no hay baseline, y la carpeta de destino **no existe** en
Drive. El propio runbook lo declaraba «un hueco de infraestructura sin resolver».

**Medido el 2026-09-02 en W-02ZIIF**, recorriendo el hueco a mano: la operación degrada a una
copia conservadora y es más simple que el merge, no más compleja — sin baseline que comparar y
con destino vacío, ninguna acción puede ser `PRESERVE_DRIVE`, `DELETE_DRIVE` ni `CONFLICT`, todo
es `COPY_LOCAL`, y el `--backup-dir` queda vacío por construcción porque no hay nada que
sobrescribir. 276 ficheros / 177,4 MiB, `check --one-way` con 274 matching y 0 differences.

**Lo que la automatización tendría que resolver, y no es la copia:**

1. **Los dos ficheros de protocolo caen por la grieta.** `_caso.md` y `_intake_log.jsonl` están en
   `MERGE_EXCLUSIONS`, luego el `check --one-way` **no los verifica**. En un merge da igual (ya
   estaban arriba); en una primera publicación son ficheros nuevos que nadie comprueba. Hoy se
   verificaron releyéndolos del Drive y parseando el JSONL.
2. **El `case_checkin` no tiene checkout que cerrar.** El evento se registra igual (es el cierre
   del ciclo de custodia, no del préstamo), pero `estado_repositorio` ya era `disponible`: hay que
   distinguir «liberar un lock» de «no había lock», y `validar_transicion` no lo contempla.
3. **`drive_remote_path` es una trampa de nombre.** Tienta rellenarlo —el caso ya vive en Drive—
   pero lo consume `sync.pull` como **fuente** de pull (`core/pipeline.py:60`): apuntarlo al hogar
   canónico haría que un pull futuro se trajese el caso sobre sí mismo. Se dejó a `null`.

**Riesgo que justifica construirlo:** mientras el modo local no tenga vía de vuelta automática, un
caso abierto ahí queda en copia única sobre el Desktop por tiempo indefinido. En W-02ZIIF fueron
**seis semanas** con el borrador de contestación y la documental del procurador sin respaldo.

**Disparador:** la próxima apertura en modo local, o una decisión de Nikolai. Sin él, la vía manual
está documentada en `[APER-41]` del runbook y basta.

## 140. `session_close` da rojo falso cuando corre fuera del venv `[RESUELTO]`

En un worktree, `python -m scripts.session_close` resuelve al **Python del sistema** (los worktrees
no tienen `.venv` propio; el venv vive en la raíz del repo). El resultado, medido el 2026-09-02:
**97 errores de colección** —el primero `ModuleNotFoundError: No module named 'yaml'` en
`core/utils.py:11`— presentados como **«[X] Tests fallando - commit abortado»**. La suite estaba
verde: con `.venv\Scripts\python.exe` dio 3.695 recogidos, 0 fallos, 0 errores, 83 skipped.

**Por qué importa aunque falle en la dirección segura.** Es un rojo falso, no un verde falso, así
que no deja pasar nada roto. El coste es de diagnóstico: manda a buscar una rotura inexistente
justo en el paso donde la disciplina del despacho dice «suite roja → parar y avisar antes de tocar
docs», y en el peor caso empuja a saltarse el guard por creerlo averiado.

**Arreglo propuesto, barato:** antes de invocar pytest, comprobar que el intérprete es el del repo
—`sys.prefix` distinto de `sys.base_prefix`, o un `importlib.util.find_spec("yaml")`— y, si no lo
es, abortar con el mensaje correcto («no estás en el venv: usa `.venv\Scripts\python.exe`») en vez
de atribuirlo a los tests. Distinguir «no pude medir» de «medí y salió mal» es la misma regla que
el despacho ya aplica a las revisiones adversariales: un revisor que no corre no refuta, deja **sin
verificar**.

**RESUELTO el 2026-09-02, PR [#258](https://github.com/TyukhayNi/FeesDefender/pull/258)** — en la
misma sesión que lo midió, por decisión de Nikolai. `deps_que_faltan()` sonda las dependencias de
colección (`pytest`, `dotenv`, `yaml`, `slugify`) y una puerta al principio de `main()` aborta con
**salida 2** —distinta del **1** de «medí y salió mal»— antes de lanzar **ningún** subproceso,
incluida la consulta a git que decide el modo.

**Dos desvíos respecto al arreglo propuesto arriba, y por qué.** (1) Se descartó
`sys.prefix != sys.base_prefix`: mide «estoy dentro de un venv», que **no es la propiedad que
decide** si la medición vale — alguien con las dependencias instaladas globalmente está
perfectamente y recibiría una falsa alarma. Lo que se sonda es la importabilidad real. (2) La
puerta va antes de **todo** subproceso, no solo antes de pytest, porque `_anon_tocado()` consulta
git para elegir el modo: si no se puede medir, no se hace nada en absoluto.

8 tests, en RED antes de la implementación, y **cuatro mutantes** —salida 2→1, puerta que nunca
dispara, puerta que dispara siempre, y `find_spec` sin capturar la excepción del padre ausente—
que matan exactamente su frontera. Suite 3.745/0/0 (+87 skip) con dos semillas.

**Y el PR #258 se mergeó con un defecto dentro, corregido acto seguido.** El mensaje componía
`ROOT/.venv/Scripts/python.exe`, que **en un worktree no existe** — y el worktree es justamente el
escenario que dispara la verja: mandaba a usar un intérprete inventado. Lo cazó la **prueba de
aceptación** —correr el comando real con el Python del sistema y leer su salida—, **no los tests**:
`test_el_mensaje_..._nombra_el_interprete` pedía solo `".venv" in salida`, y una ruta equivocada
también lo cumple. El test **defendía el bug** (ver la memoria `feedback-un-test-puede-defender-el-defecto`).

Arreglado con `venv_sugerido()`, que resuelve la raíz real **sin subproceso** —la verja va antes de
cualquiera—: en un worktree `ROOT/.git` es un *fichero* con `gitdir: <repo>/.git/worktrees/<n>`, y
el antecesor `.git` da el repo principal; prueba `Scripts/python.exe` y `bin/python`, y **solo
devuelve lo que existe en disco**, con `None` y un mensaje honesto si no hay ninguno. 6 tests más
—entre ellos el que faltaba: que la ruta sugerida **exista**, no que el texto contenga `.venv`— y
tres mutantes (volver al bug, no comprobar la existencia, ignorar el `gitdir`).

**La lección, que es de método y no de este fichero:** los tests dieron 8/8 verde sobre un mensaje
inservible. Lo que lo destapó fue **ejecutar la cosa y mirar lo que imprime**. Un arreglo cuya mitad
útil es un texto para un humano no está verificado hasta que alguien lee ese texto.
---

## 141. `buscar()` no valida el `case_id`, así que una referencia con `..` escribe fuera del catálogo

**Estado:** pendiente. **Defecto vivo.** Detectado el 2026-09-02 por el hallazgo **H24-01** de la
R24 (revisión de la rev. 2 del diseño de `MEJORAS #124`) y **reproducido con sonda propia**.

**Qué debería pasar.** `case_locator.buscar(case_id)` devuelve la ruta de un caso **dentro** de
`CASOS_ROOT`, o `None`. Todo el modelo dual lo da por sentado: es la premisa de la que cuelga
«el canon está bajo el catálogo».

**Qué pasa.** Compone `root / case_id` sin comprobar que `case_id` sea un **nombre simple**
(`core/casos/case_locator.py:132-143`). En `pathlib`, un componente absoluto **descarta la raíz**, y
`..\algo` sale por el padre. `resolve_ref` devuelve sin modificar la referencia que no reconoce
(`case_locator.py:226-258`), así que nada la sanea por el camino.

**Medido el 2026-09-02**, con una copia local legítima registrada fuera del catálogo:

```
buscar('Caso')            : <CASOS>\Caso              ← el caso normal, bien
es_copia_prestada('Caso') : False

buscar('..\workspace')    : <CASOS>\..\workspace      ← escapa
escapa de CASOS_ROOT      : True
es_copia_prestada         : True
guard: permitido/desviar  : True / False              ← permite SIN desviar
```

**Alcanzable desde un entrypoint real:** `scripts/export_label_emails.py` toma `--ref` como texto
libre, lo pasa por `resolve_ref` y de ahí a `email_dest_dir(case_id)`. `scripts/atomize_emails.py`
tiene el mismo `--ref`.

**Qué se rompe, con la severidad calibrada y sin inflarla.** Son **CLI locales** que corre el
letrado en su portátil, no un servicio expuesto a entrada ajena. El modo de fallo realista es el
**error de operador** —una ruta pegada por error, una referencia con un separador de más— que
deposita documentos **fuera del catálogo** y, de paso, desactiva el desvío del guard porque
`es_copia_prestada` pasa a ser cierta. No se rotula como agujero de seguridad; se rotula como lo que
es: una frontera de entrada sin validar en la función de la que cuelga todo el modelo dual.

**Y tiene una consecuencia documental:** invalida el «teorema» que la rev. 2 del plan de `#124`
afirmaba en su §1 —que `es_copia_prestada` es demostrablemente `False` siempre—. Lo corrige el §9.1
de ese plan.

**Mejora propuesta.** Validar en la frontera: `case_id` es **un único componente de ruta**, no
absoluto, sin separadores ni `..`. Y comprobar la **contención** del resultado bajo `CASOS_ROOT`
antes de devolverlo — la pieza que lo sabe hacer ya existe y está probada,
`case_catalog.clasificar_bajo`, que `MEJORAS #136` dejó con comparación por componentes e identidad
física.

**Condición de cierre:** un test por cada forma —absoluto, `..`, separador embebido— contra
`buscar`, `localizar` y `resolve_ref`, y **un mutante por cada validación** que muera solo por su
test. Que la referencia canónica normal siga funcionando es la mitad que hace falta para que la
guarda no sea inerte.

**Disparador:** cualquier trabajo sobre `#124`, que ya no puede apoyarse en la premisa; o el primer
caso real de un depósito fuera del catálogo.

---

## 142. El `dry-run` del modo `libre` sale con `typer.Exit(0)` DENTRO del bloque de mutex `[RESUELTO 2026-09-03]`

**Medido el 2026-09-03**, al remediar el hallazgo **HA-07** de la R-A del Plan 5 de apertura V1.
Es el mismo defecto en otro sitio, y ese sitio queda fuera del alcance de ese plan.

`scripts/abrir_caso.py` lanza `typer.Exit(code=0)` para el `--dry-run` **dentro** del
`with mutex_sesion.sostenido(...)`. `case_mutex.tomado` (`core/casos/case_mutex.py:615-659`)
distingue dos caminos en su `finally`: **sin** excepción en vuelo, una pérdida del lease **lanza**
`MutexPerdido`; **con** excepción en vuelo, solo la **anota** con `add_note`. Un `Exit(0)` es esa
excepción, así que si el lease se pierde durante un `--dry-run`, el proceso sale **0** y el aviso
queda enterrado en una nota del traceback que nadie mira.

**La propiedad que rompe** es la que R12/H12-04 construyó a propósito: «una pérdida no se evapora».

**Cómo se comprobó:** el revisor de R-A lo reprodujo con el gestor real para el caso del cableado
—`TIPO=Exit EXIT_CODE=0`, la pérdida solo en `__notes__`— y la misma forma está en el camino del
`dry-run`. **SIN VERIFICAR** en ese camino concreto: la sonda se corrió sobre el otro.

**Remedio:** el mismo que el Plan 5 aplica a su rama `v1` — calcular dentro del `with`, salir
fuera. Es un movimiento de tres líneas.

**Disparador de promoción:** cualquier trabajo que toque el cuerpo de `main` en
`scripts/abrir_caso.py` —el Plan 5 lo toca, pero deliberadamente no esta rama—, o el primer caso
real de un `--dry-run` que salga 0 sin haber sostenido la exclusión.

**MEDIDO el 2026-09-03 por la R-B del Plan 5 (L3-04), y mi descripción de arriba era engañosa en lo
que más importa.** No es «el mismo defecto en otro sitio»: el defecto vive **casi solo aquí**. Hay
**9 salidas del proceso** dentro del bloque de mutex alcanzables desde el modo `libre` —8 en las
funciones que invoca (`_despachar_intake`, `_alta_crm`, `_validar_flags`, los `_intake_*`) más el
`--dry-run`—, mientras la rama `v1` que el Plan 5 remedió **apenas podía manifestarlo**, porque sus
etapas capturan `Exception` y devuelven un resultado en vez de lanzar. El revisor lo reprodujo:
exit 0 y cero aviso. Y `libre` es **el modo por defecto y el que usa el equipo a diario**.

**Consecuencia sobre la decisión:** Nikolai aprobó aplazar esto como deuda de radio pequeño sobre mi
descripción. Con la medición delante, el radio no es pequeño y la prioridad sube. Reabrirlo es
decisión suya.

**✅ RESUELTO el 2026-09-03**, por decisión de Nikolai de reabrirlo. Plan
`docs/superpowers/plans/2026-09-03-mejoras-142-exit-bajo-mutex.md`, con su ronda adjudicada
(`NO-SHIP`, 5 hallazgos, 5 confirmados). **Las nueve salidas están fuera:** cuatro eran validación y
corren fuera del lock —después de resolver identidad, para no reordenar el diagnóstico que ve el
operador—, cuatro lanzan `AbortarApertura` y el entrypoint decide, y la del `--dry-run` marca una
bandera y sale fuera del bloque.

**Y el arreglo trajo una pieza que no estaba en el diagnóstico:** convertir los `Exit` en excepciones
de dominio **no basta**, porque siguen en vuelo y el `finally` sigue anotando en vez de lanzar. Lo
que faltaba es que alguien **lea** la nota: el handler la imprime como `[AVISO]`, porque Typer
descarta el traceback.

**El guard vigila la frontera y no los nueve ejemplos:** `tests/test_abrir_caso_exit_bajo_mutex.py`
**deriva** el cierre transitivo de funciones alcanzadas desde el bloque —17— y reconoce las cuatro
formas de terminar (`typer.Exit`, `Abort`, `sys.exit`, `SystemExit`), con una prueba negativa por
forma. Su primera versión mantenía la lista a mano y solo veía `typer.Exit`: la ronda midió que un
`sys.exit` la dejaba verde.

---

## 143. La spec del orquestador sostiene una decisión sobre una cifra irreproducible

**Medido el 2026-09-03**, hallazgo **HA-12** de la R-A del Plan 5.

El **§24 D3** de `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`
justifica la decisión de implementar V1 como **modo** y no como **subcomando** así: «Hay **103
referencias** a `scripts.abrir_caso` en el repo». La cifra no es reproducible y no declara comando,
patrón ni unidad:

```
git grep -o "scripts\.abrir_caso" | wc -l   ->  53
git grep -l "scripts\.abrir_caso" | wc -l   ->  19
```

53 apariciones en 19 ficheros. El token ancho `abrir_caso` da 657 en 64, que cuenta el módulo del
core, los tests y la prosa.

**Por qué importa aunque la decisión no cambie.** 53 referencias siguen siendo demasiadas para
romper la forma documentada del CLI, así que D3 se sostiene. Lo que no se sostiene es **poder
auditarla**: una cifra sin comando no se puede recomputar, y una spec cuyos números no se pueden
recomputar deja de ser fuente y pasa a ser recuerdo. La rev. 1 del Plan 5 la copió a sus
restricciones globales **sin medirla**, que es exactamente cómo se propaga.

**Remedio:** en el §24 D3, sustituir la cifra por el comando y su resultado con fecha, o retirarla
y dejar el argumento cualitativo (que es el que de verdad decide).

**Disparador de promoción:** la próxima revisión de esa spec, o cualquier trabajo que vuelva a
apoyarse en el recuento de referencias del entrypoint.

---

## 144. V1 no cuenta los documentos que el OCR no pudo procesar

> ✅ **CERRADO 2026-09-03 — PR #265 (`c17a9e3`).** `scripts/sala_maquina.apply` devuelve un
> `ResultadoApply` (objeto, no `str | None`) con `status_atomizacion` y `documentos_agotados`, y
> `etapa_sala_maquina` (`scripts/abrir_caso.py`) levanta el pendiente **`ocr_documentos_agotados`**
> con la cuenta y el reintento (`sala_maquina apply --force`, o `--solo <ruta>`), así que el evento
> `apertura_v1_terminada` ya lo dice (clave `pendientes`). **Residuo declarado:** el marcador
> `_apertura_v1.json` sigue registrando solo `estado` + `etapas` (`RondaV1` no tiene campo de
> pendientes): de los «dos registros durables» del texto original, el cierre remedia **uno**; el
> docstring de `ResultadoApply` afirma los dos y hereda el mismo error. 35/35 mutantes muertos por
> su frontera (F37/F38). Texto original conservado como histórico.

**Medido el 2026-09-03 en la corrida real de la Task 11 sobre W-02Q38C**, que es exactamente lo que
una apertura de verdad enseña y una fixture no.

La sala de máquina imprimió:

```
AVISO: 5 documento(s) con 3 intentos agotados se saltan y NO se han vuelto a procesar.
```

Y la secuencia de V1 terminó `preparado_con_pendientes` enumerando **dos** pendientes:
`fuentes_v3_sin_consultar` y `crm_gestor_vacio`. **Los cinco documentos no aparecen en ninguno de
los dos registros durables** — ni en `_apertura_v1.json` ni en el evento `apertura_v1_terminada`.

**Por qué importa, y es de prueba documental.** El evento forense es lo único que queda de una
apertura dentro de seis meses. Quien lo lea verá «preparado con pendientes» con dos pendientes
ajenos a la documental y concluirá que los documentos del caso están procesados. Cinco no lo están,
y llevan tres intentos fallidos: son justo los que alguien tendría que mirar a mano.

**La causa, y es de diseño mío.** `etapa_sala_maquina` mapea el status de la **atomización** a un
pendiente (`atomizacion_parcial`) y nunca el del **OCR**. `scripts/sala_maquina.py:apply` devuelve
solo `status_atomizacion`; el contador de agotados existe (`MEJORAS #84`) y se imprime, pero no
viaja al llamador. El estado de V1 se deriva de una lista de pendientes que no incluye todo lo
pendiente — la misma familia que los defectos que R-B y R-C encontraron el mismo día.

**Remedio.** Que `apply` devuelva también los agotados (o un resultado con los dos datos, que es
mejor que un segundo valor de retorno), y que `etapa_sala_maquina` levante un pendiente
`ocr_documentos_agotados` con la cuenta. Con su mutante: el arnés de mutación del Plan 5 no cubre
esto porque la frontera no existe todavía.

**Disparador de promoción.** La próxima apertura real —cualquier caso con documentos que el motor no
resuelva—, o el primer informe de viabilidad que se redacte sobre un expediente cuyo estado decía
«preparado» con documental sin procesar. Es barato: el dato ya está calculado.

---

## 145. Un LECTOR del lock puede hacer que el titular PIERDA su mutex (Windows) `[RECLASIFICADO 2026-09-03: es de PRODUCCIÓN]`

> **Al día 2026-09-07: la mitad de TEST está cerrada (PR #302, `3420d4d`); la de PRODUCCIÓN, no.**
>
> `test_RENUEVA_mientras_el_cuerpo_corre` **fabricaba** la carrera que denunciaba: esperaba
> al latido abriendo el `.lock` unas cincuenta veces por segundo, justo el fichero que el
> renovador reemplaza con `os.replace`. Ya no lo mira — la señal la da el propio `renovar`
> y la única lectura va **bajo el guard**—, y la propiedad se reparte en dos porque un
> plazo de pared no puede probar las dos: el **mecanismo** en ese test y la **puntualidad**
> en `test_el_renovador_DESPIERTA_dos_veces_por_lease`, contra la constante y sin reloj.
> Seis mutantes, `python -m tests._mutantes_renovacion_mutex`.
>
> **El defecto de producción sigue vivo y con su precio intacto** (dos rondas; `case_mutex.py`
> declarado intocable por el Plan 5), así que su disparador **no cambia**. Lo que sí cambia,
> y se declara aquí para que nadie lo descubra por sorpresa: **ya no lo va a levantar un rojo
> de la suite.** Es deliberado — el rojo no lo levantaba el defecto, lo levantaba el test
> provocándoselo—, y el disparador escrito abajo nunca fue ese rojo.
>
> Cierra además **`#171`**, que describía este mismo rojo atribuyéndolo a la carga de los 12
> workers. Dos entradas de este fichero explicaban el mismo síntoma con causas incompatibles y
> nadie las cruzó: la medición del 07 desmiente la de `#171` y confirma la sonda de aquí.

**Medido el 2026-09-03**, cerrando `MEJORAS #144`. En la suite completa con semilla `31337`:

```
PermissionError: [Errno 13] Permission denied: '<basetemp>/test_RENUEVA_mientras_el_cuerp0/locks/W-MUTEX1.lock'
MutexIlegible: [MUTEX_ILEGIBLE] — el mutex del caso existe y no se puede interpretar — caso W-MUTEX1
FAILED tests/test_case_mutex.py::TestElGestorRenueva::test_RENUEVA_mientras_el_cuerpo_corre
```

**Qué se midió, y descarta las dos explicaciones fáciles:**

- **No es dependencia de orden.** La misma semilla `31337`, sobre el mismo árbol, dos repeticiones
  más: **verde las dos, 0 fallos**. El orden lo fija la semilla; si el resultado cambia, la causa es
  de **tiempos**.
- **No es el test.** `tests/test_case_mutex.py` **solo**, con esa misma semilla: 44 verdes.

**Hipótesis, y está SIN VERIFICAR:** el hilo de latido (`heartbeat`) de una sesión de mutex sigue
teniendo abierto el `.lock` cuando pytest intenta limpiar su `tmp_path`. En Windows un fichero
abierto no se puede borrar, y el `PermissionError` sale del `filelock`/`msvcrt.locking` que
`case_mutex` usa por diseño. El `join(timeout=5)` del `finally` puede vencer sin que el hilo haya
soltado el descriptor.

**RECLASIFICADO, y mi primera versión de esta entrada estaba equivocada.** Escribí «es higiene de
TEST, no de producción». **Es de producción.** Lo que me hizo mirar fue que el fallo traía DOS cosas
y no una: el `PermissionError` y un `MutexIlegible`, que significa «el lock existe y no se puede
interpretar». Eso no es la limpieza de un directorio temporal.

**La anatomía lo explica.** El fichero `.lock` **contiene el estado JSON**; el bloqueo del sistema
vive en un hermano `.lock.guard`, a propósito, porque `os.replace` sustituye el inodo
(`core/casos/case_mutex.py:360-362`). Así que el estado se **publica** con `os.replace` y se **lee**
con un `read_text` normal — y en Windows esas dos operaciones chocan.

**Medido con una sonda propia** (tres lectores y un escritor, 3 segundos):

```
lecturas OK             : 27570
lector PermissionError  :   326   (~1,2 % de las lecturas)
escritor PermissionError:  2389
```

**Las dos direcciones fallan, y cada una con su consecuencia:**

1. **El lector** recibe `PermissionError` y `leer_estado` lo convierte en `MutexIlegible`
   (`:320-332`), cuyo contrato es «un lock ilegible es evidencia»: una alarma de corrupción sobre un
   lock sano.
2. **El escritor** —el latido renovando el lease— falla, y `tomado` trata **cualquier** excepción de
   `renovar` como pérdida de titularidad (`:603-611`: `sesion.marcar_perdido(exc); return`). Con lo
   cual **un proceso que solo COMPRUEBA si el caso está ocupado puede hacer que el dueño legítimo
   pierda su mutex**, y el dueño acaba viendo «se perdió la exclusión, puede haber trabajo a medias»
   sobre una corrida sana.

**Los dos son falsas alarmas producidas por un uso concurrente correcto** — justo lo que esta
primitiva existe para hacer fiable.

**Lo que NO está medido: la frecuencia real en producción.** La sonda es un bucle apretado a
propósito. Con el latido renovando cada pocos segundos y lecturas ocasionales la ventana es mucho
más estrecha, y que esto se manifieste como un test intermitente y no como una incidencia diaria
apunta a eso. El **mecanismo** está confirmado; su tasa real, no.

**Por qué importa igual:** la regla de este repo es correr **dos semillas** antes de cerrar. Un test
que falla una de cada tres corridas hace que esa regla dé rojos que no significan nada, y un rojo
que no significa nada enseña a ignorar los rojos.

**Lo medido el 2026-09-07, que descarta la lectura fácil del síntoma.** «Bajo carga el hilo de
renovación no llega a tiempo» **no** explica el rojo. Con 24 procesos ocupados sobre 4 CPUs —6x de
sobresuscripción— y 8 corridas instrumentadas: el primer latido llega a **1,00-1,03 s** de su
periodo de 1 s (nunca tarde) y el presupuesto del bucle de espera **crece** con la carga, de 3,05 s
en reposo a 3,77-4,09 s saturado. O sea que el margen **mejora** cuando la máquina sufre; el test
aislado bajo esa misma carga dio 12/12 verdes. Lo que queda es que el renovador **muera**, que es
esta entrada. Confirmado por inyección: un solo `os.replace` fallido del `.lock` produce
**exactamente** el rojo reportado —«el renovador no latió en 3 s»— con la causa real
(`PermissionError`) enterrada en `sesion._causa`, o sea que el mensaje del test acusaba al reloj de
un fallo que no era del reloj.

**Remedio, y el precio no está en el código:** un reintento acotado ante `PermissionError` en
`leer_estado` y alrededor del `os.replace` de `_escribir_estado` — una violación de compartición en
Windows es transitoria por naturaleza y hay que distinguirla de un fichero de verdad ilegible, que
es evidencia y no se puede tragar. Serán quince líneas.

**Lo que cuesta es que toca la primitiva de exclusión.** Por radio de daño son **dos rondas**
(decide quién puede escribir sobre qué copia), y el Plan 5 la declara intocable porque editarla
reabre sus cuatro rondas y sus diecisiete mutantes. Ese es el precio real: no el diff, la garantía.

**Lo que NO se hace aquí, y por qué:** `core/casos/case_mutex.py` tiene cuatro rondas de revisión y
diecisiete mutantes, y el Plan 5 lo declara intocable — editarlo es reabrirlas. Esta entrada existe
para que quien lo abra con un motivo lo arregle entonces, con su presupuesto de rondas.

**Disparador de promoción.** Ya no es «el siguiente rojo del test». Al reclasificarse es **la
primera vez que una apertura real informe de una pérdida de exclusión que no se explique por otro
proceso**: desde fuera eso es indistinguible de esta carrera, y en un despacho donde nadie trabaja
en paralelo sería casi con seguridad esto.

---

## 146. Escribir una nota a mano en `_caso.md` la destruye en el siguiente pull

> ✅ **CERRADO 2026-09-05.** `_write_case_index` distingue crear de actualizar y, al actualizar,
> **conserva** el cuerpo, las claves top-level ajenas (`bucket_override`), las claves de `meta`
> que el modelo no conoce (`proyeccion_local`), los wikilinks de `registrar_outputs` y el estado
> D8 de `update_pull_state` en `sudespacho_expedientes` (fusión por entrada); reescribe **solo**
> la línea de estado, la de IDs de Drive E&V y la sección `## Expedientes sudespacho`, y escribe
> atómicamente en las dos ramas. Diseño rev. 2 con la adjudicación de la R1 (revisor sustituto,
> 10/10 confirmados) en `docs/superpowers/specs/2026-09-05-caso-md-preservar-al-actualizar-design.md`;
> acta `…-r1-adversarial-review.md`; 16 mutantes en `tests/test_caso_md_preservar_al_actualizar.py`.
> La regla de `CLAUDE.md` y `[APER-54]` pasan a «preferente», no «único sitio seguro». Lo que la
> pieza NO cubre —escritores que no pasan por el sumidero— está en el §6 del diseño y en `#167`.

**Reproducido por resultado el 2026-09-04.** Sonda: `_caso.md` con una nota del abogado en el
cuerpo → una llamada a `_write_case_index` → la nota ya no está y el fichero se ha reescrito
entero. No es lectura de código: es la salida de la sonda.

**La causa.** `register_drive_ev` (`core/case_manager.py:515`) **no muta** el fichero: lo
**reconstruye** llamando a `_write_case_index`, que arma el cuerpo desde cero a partir de
`CaseMeta` y nunca lee lo que había. **Y no es un sitio, son CUATRO** llamadores, todos en
`core/case_manager.py` y contados por AST el 2026-09-04: `register_expediente()`,
`ensure_case()`, `register_drive_ev()` y `cache_drive_folder_info()`. El
comentario de la línea 684 ya avisa —«nunca `_write_case_index` (que reconstruye y podría
descartar campos)»— para *otro* consumidor, y ese aviso no llegó a los registradores.

**Por qué importa, y por qué se registra ahora.** No necesita carrera: basta un pull de Drive, que
es lo normal en una apertura. Lo que se pierde es una **nota del abogado sobre un expediente**, sin
aviso y sin dejar rastro de que existía. Se midió el 2026-08-26 (72º cierre, tabla de las tres
pérdidas) y la **instrucción operativa que salió de ahí —«que nadie escriba notas en `_caso.md`»—
nunca llegó al repo**: vivía en un bloque de cierre que no se commiteó y que estuvo a punto de
borrarse con su worktree. Se ha llevado ahora a `CLAUDE.md` y al runbook (`[APER-54]`).

**Remedio.** Que los registradores **muten** el frontmatter y conserven el cuerpo, en vez de
reconstruir; o que `_write_case_index` lea el fichero existente y preserve todo lo que no sea suyo
—cuerpo y claves de frontmatter ajenas a `CaseMeta`, que se pierden por la misma razón (es la
segunda fila de aquella tabla)—. Con su mutante: un test que escriba una nota, llame al registrador
y exija que siga ahí; hoy no existe ninguno, y esa ausencia es la que dejó pasar el defecto.

**Disparador de promoción.** La primera nota perdida de verdad, o el arreglo del grupo **B0-2** de
la Fase 2 de la fila #3, que toca la misma familia (escrituras que reconstruyen en vez de añadir) y
puede pagar los dos de una vez. Mientras tanto, lo que protege es la instrucción, no el código.

---

## 147. La dedup es por `(ruta, sha256)` del crudo, así que el mismo documento entra dos veces

**Medido el 2026-09-04 sobre W-02Q38C**, contando por contenido y no por nombre: de **51** espejos
MD de la sala de máquina, **49** contenidos distintos. Tres documentos tienen doble espejo, y llegan
ahí por **dos vías distintas** que conviene no confundir:

| Vía | Ejemplo medido | `sha256` del PDF | Lo que falla |
|---|---|---|---|
| **A. Mismo fichero en dos carpetas de E&V** | `Certificado titularidad Bancaria…` en `ARRAS/` y en `OFERTAS/OFERTA 1 …/` | **el mismo** (`2323df1b…`) | El intake **sí** ve el hash, pero la clave es `(ruta, sha256)` y las rutas difieren; la sala de máquina slugifica por **nombre de fichero**, así que produce dos MD con `text_sha256` idéntico (`9def49d0…`) |
| **B. Re-subida del mismo documento** | `Nota simple Actualizada 27／04／2026.pdf` y `NS ACTUALIZADA 06／05／26.pdf` | **distinto** | El PDF se regeneró (re-descarga del Registro) y la dedup por `sha256` no puede verlo. El contenido es idéntico y, en la nota simple, lo demuestra que ambos llevan el **mismo C.S.V.** (no se transcribe: es la llave de descarga del documento en la sede de registradores) |

**La frontera, que no es «dos ficheros con el mismo nombre».** La identidad de un documento del
expediente **no son sus bytes ni su ruta**: es su contenido, y en los documentos con sello
electrónico viene con un identificador propio y estable (C.S.V. del Registro, CSV de la sede, número
de protocolo notarial). Hoy no se mira ninguno de los tres niveles.

**Qué cuesta, acotado por la misma medición.** No corrompe nada —el crudo debe conservar las dos
copias, es el Drive del cliente— y **la sala de lectura NO hereda el defecto**: la de W-02Q38C tiene
**41 ficheros y 41 contenidos distintos**, así que ahí el duplicado ya se colapsa. Lo que se paga es
en la **sala de máquina**: OCR y espejo repetidos por documento duplicado, y el mismo hecho contado
dos veces en el corpus MD que lee el LLM de viabilidad. Y **falsea el recuento** de lo que una
corrida trae: la vía B es la que hizo escribir en la bitácora del 75º cierre que la corrida había
traído «2 documentos que el expediente no tenía» — corregido allí mismo.

> Esa acotación es el resultado de medirlo, no de razonarlo: la primera redacción de esta entrada
> decía «entradas duplicadas en la sala de lectura», y el conteo lo desmintió el mismo día.

> **Vía A `[RESUELTA 2026-09-06]`** (acción 11 de la fila 21): `core/sala_maquina.plan` marca como
> `duplicado_de` toda copia con el mismo `sha256` que un fichero anterior del inventario y
> `ejecutar` no la procesa: fila de custodia propia (método `duplicado`, estado heredado del
> titular, nota con la ruta del espejo único) y el titular anota «también en …». Sin OCR ni
> espejo repetidos; `plan` cuenta los duplicados aparte. La llave es el `sha256` del crudo, no
> `text_sha256`: para la vía A son equivalentes y el hash del crudo se conoce ANTES de pagar el
> OCR. Plan y adjudicación:
> `docs/superpowers/plans/2026-09-06-accion-11-dedup-via-a-sala-de-maquina.md`. **Las vías B y
> C siguen abiertas** con el disparador de abajo.

**Remedio, por capas y en este orden.** (1) La vía A es barata y cierta: la sala de máquina puede
llavear por `text_sha256` y emitir **un** espejo con las dos procedencias anotadas. (2) La vía B
necesita una noción de identidad documental — extraer C.S.V./CSV/protocolo cuando exista y usarlo
como llave, cayendo a un hash del texto normalizado cuando no. (3) Que el espejo único anote sus
**N procedencias**, porque hoy la información de que el documento vive en dos carpetas de E&V se
pierde al colapsar. Con su mutante en cada capa: dos ficheros de contenido idéntico y rutas
distintas deben producir **un** espejo, y el test tiene que morir si vuelven a ser dos.

**Disparador de promoción.** Un caso donde el duplicado cambie una conclusión —un hito de viabilidad
contado dos veces, o un importe que aparezca duplicado en un escrito— o el arreglo de `MEJORAS #129`
(`la cobertura se llavea por (slug, rel_path) y los artefactos por slug`), que toca exactamente la
misma clave y puede pagar la vía A de paso.

## 148. `abrir_caso` compone el `case_id` sin pasarlo por la guarda que lo valida

> ✅ **CERRADO 2026-09-04 — PR #278.** `componer_case_id` valida los **tres** campos que
> concatena (`--codigo-caso`, `--direccion`, `--sufijo`) y el CLI traduce el `ValueError` a un
> error que nombra al culpable, sin crear esqueleto.
>
> **Y la guarda salió ESTRECHA, que es la lección.** La primera versión llamaba a
> `validate_case_id` entero y rompió cinco fixtures con códigos sintéticos (`BaTEST`, sin
> dígitos): una guarda **más ancha que el defecto medido**. La frontera era la gramática de
> **rutas**, no el formato canónico del `case_id`. Se extrajo
> `core.utils.exigir_sin_caracteres_de_ruta` con hogar único, del que `validate_case_id` también
> tira. La tentación de arreglar los fixtures en vez del diagnóstico era el error de verdad.

**Medido el 2026-09-04 abriendo W-02JSVZ**, cuya dirección operativa en E&V lleva un «**s/n**»
(finca rústica sin número). Con `--direccion` copiada literal de la tabla de Bad Debt, la corrida
terminó diciendo:

```
OK Caso abierto: BaRS8 - <via> s/n <cp> <municipio> (W-02JSVZ) - BD
```

y lo que había en disco eran **dos** carpetas anidadas: `BaRS8 - <via> s\` conteniendo
`n <cp> <municipio> (W-02JSVZ) - BD`, con los 170 ficheros del pull dentro. El `/` de «s/n» se
comportó como separador de rutas. Ningún aviso, código de salida 0, y el `case_id` que el CLI
imprime **no nombra a ninguna carpeta**.

**La guarda existe y no puede haber disparado.** `core.utils.validate_case_id` rechaza exactamente
esto: `_WIN_FORBIDDEN = re.compile(r'[\/:*?"<>|]')` (`core/utils.py:105`), con mensaje propio. Pero
sus únicos llamadores son `core/anon/api.py` y `scripts/init_caso.py`. **`abrir_caso` —el único
sitio que COMPONE el `case_id` desde lo que teclea el usuario— no la llama nunca**, ni en
`core.abrir_caso.componer_case_id` ni en `scripts/abrir_caso.py`. Y el docstring de
`componer_case_id` (`core/abrir_caso.py:30`) afirma «Formato validado por
core.utils.validate_case_id»: enuncia una validación que en esta vía no ocurre.

**Cuándo se descubre, que es lo caro.** No en el alta: en el comando *siguiente*. El intake
incremental `--case-id W-02JSVZ` falló con `[ERROR] Caso no encontrado`, porque
`case_locator.resolve_ref` no puede reconstruir un caso partido en dos. Entre una cosa y otra caben
170 ficheros depositados en una ruta sombra y —si nadie mira— un `apply` de OCR sobre ella.

**La frontera, que no es «sanear la dirección».** Es que **todo campo de identidad que acabe siendo
una ruta tiene que atravesar la gramática de rutas, no solo la del `case_id`**. Aquí las dos
gramáticas ya están escritas y son la misma función; lo que falta es la llamada. El mismo hueco
cubre `--sufijo` y `--codigo-caso`, que también se concatenan sin mirar, y no lo tapa validar
únicamente `--direccion`.

**Remedio.** `componer_case_id` devuelve `validate_case_id(f"...")` en vez de la f-string cruda —un
solo punto, porque todas las vías de `abrir_caso` pasan por ahí— y el CLI traduce el `ValueError` a
un error legible que nombre el campo culpable. Su mutante: `--direccion "a/b"` debe abortar **antes**
de `ensure_case`, y el test tiene que morir si la corrida vuelve a terminar en 0. Segunda capa,
independiente: `ensure_case` comprueba que la carpeta que acaba de crear se llama como el `case_id`
que le pasaron — hoy nadie compara el nombre pedido con el nombre obtenido.

**Disparador de promoción.** Ya está disparado: pasa con cualquier dirección con `s/n`, que en el
corpus de E&V es común (fincas rústicas, castillos, naves). Se remedió a mano borrando el árbol y
repitiendo el alta con «**sn**» en lugar de «s/n» —la grafía que E&V usa en su propia factura—,
pero el siguiente que copie la dirección de la tabla vuelve a pisarlo.

## 149. Los ficheros de protocolo que el registro NO declara entran en el inventario probatorio  `[RESUELTO 2026-09-05 — por UBICACIÓN, no por nombre]`

> ✅ **Resuelto el 2026-09-05 (PR #290), implementando el diseño rev. 2
> (`docs/superpowers/specs/2026-09-05-ficheros-de-protocolo-por-ubicacion-design.md`, PR #287).**
> El remedio NO fue declarar los cuatro nombres —eso es lo que se revirtió el 2026-09-04— sino
> cambiar el contrato: `core/intake_control.py` registra pares **(directorio, nombre)** y una sola
> pregunta, `es_fichero_de_protocolo(rel_path)`, sobre la ruta relativa a `00_Input/`. Los nueve
> consumidores preguntan por la ruta; los tres alias por basename se retiran;
> `config.INTAKE_CONTROL_FILES` queda **derivado y sin lectores** (guard por AST). Los cuatro
> ficheros de abajo salen de la red de calidad; un `_inventory.json` dentro de un lote es un adjunto
> y ENTRA en inventario, albarán, sala de máquina y ledger. La migración compara por hash **tres
> veces** (plan, fase 1, `unlink()`) y el homónimo anidado viaja al lote con su entrada M9. Trece
> mutantes, uno por frontera, muertos. **Las rondas:** R1 sobre el diseño (§8 del diseño) y R2 sobre
> el diff (§9), por radio de daño. `MEJORAS #54 T1` («lista única» por nombre) queda **sustituida**
> por este registro. Texto original conservado como medición:

> 🔴 **ABIERTA, y el arreglo del 2026-09-04 se REVIRTIÓ el mismo día** (`4cd71dd`). Se cerró
> declarando los cuatro nombres en `INTAKE_CONTROL_FILES` y la **R1 adversarial lo tumbó con un
> hallazgo CRÍTICO**: `scripts/migrar_layout_intake.py:122` hace `hijo.unlink()` **sin comparar
> bytes ni hash**, y con los cuatro declarados un `03_Email/_ficha_crm.yaml` que sea un adjunto
> legítimo pasa a tratarse como estado de canal y **se borra** si existe el de la raíz. El
> revisor lo reprodujo: los dos contenidos sobreviven en base y el segundo desaparece en head.
>
> Dos más de la misma causa: `core/intake_lotes.py:197` excluye por basename **a cualquier
> profundidad** (`rglob`), así que un adjunto llamado así desaparece del manifiesto del lote; y la
> migración mueve el homónimo anidado dejando las referencias forenses de M9 apuntando a una ruta
> inexistente.
>
> **La causa es una y estaba escrita en esta misma entrada:** «excluir `_manifiesto.yaml` por
> *basename* excluye cualquier fichero así llamado en cualquier sitio… Lo correcto es excluirlo
> solo en la raíz de un lote, o sea una línea **más** una comprobación de ruta». Se implementó
> solo la línea. **El contrato es por UBICACIÓN, no por nombre**, y eso toca cinco consumidores
> (`intake_drive`, `intake_manual`, `inventory`, `email_export`, `migrar_layout_intake`).
>
> **Presupuesto corregido: dos rondas, no una.** La pieza puede destruir prueba del cliente, luego
> por radio de daño le tocan dos. Al revertir, el diff volvió a la categoría de una.
>
> Informe literal y adjudicación: `docs/superpowers/specs/2026-09-04-apertura-w02jsvz-pipeline-r1-adversarial-review.md`.

**Medido el 2026-09-04 en la corrida de apertura de W-02JSVZ, con el código de hoy.** El
`_cobertura` de la sala de máquina trae dos entradas `sin_soporte` que no son documentos del caso:

```
_intake_hashes.json
2026-09-04_email_01/_manifiesto.yaml
```

Y trae, correctamente, **ninguna** de `.pulled`, `_exported_ids.json` ni `_resolved_links.json`. Esa
asimetría es el hallazgo: `_es_control` (`core/sala_maquina.py:1181`) funciona —deriva de
`config.INTAKE_CONTROL_FILES` en vez de duplicar la lista, que es lo que arregló la R-B del Plan 5—
y lo que se cuela es **exactamente lo que nadie declaró en el registro**.

**Los cuatro que faltan, y quién los escribe.** Ninguno es de un tercero: los produce este mismo
repo, en `00_Input/`, por prescripción del propio runbook.

| Fichero | Quién lo escribe | Medido |
|---|---|---|
| `_intake_hashes.json` | el intake | W-02JSVZ, 2026-09-04 (esta corrida) |
| `<lote>/_manifiesto.yaml` | `core.email_export`, uno por lote | W-02JSVZ, 2026-09-04 (esta corrida) |
| `_ficha_crm.yaml` | a mano, §9 del `RUNBOOK_APERTURA_EXPEDIENTE` | W-02Q38C (`ficha_crm__f53e4101 · sin_soporte`) |
| `_ocurrencias_crm.json` | la vista procesal | W-02Q38C |

Los dos últimos se midieron sobre un `_cobertura` anterior al arreglo, así que como *evidencia de
hoy* valen los dos primeros; pero ninguno de los cuatro está en `INTAKE_CONTROL_FILES` ni casa con
el único prefijo declarado (`.apertura_v1.`), luego los cuatro se cuelan igual. No se afirma más de
lo medido: los dos primeros, verificados hoy; los dos últimos, por lectura del registro.

**La frontera, y es la lección que la entrada de `_apertura_v1.json` dejó a medias.** El comentario
de `config.py:569` cuenta que ese fichero se declaró porque «sin declararlo entraba en el inventario
probatorio y salía como `sin_soporte`, en la MISMA corrida que lo escribía». Se remedió **el
ejemplo**, no **la propiedad**: la propiedad es que *todo fichero de protocolo que el propio repo
deposite bajo `00_Input/` tiene que estar en el registro*, y hay cuatro más en esa situación. Un
`sin_soporte` sobre un fichero de control no es un aviso inocuo — es ruido en la **red de calidad**,
que es justo donde se mira lo que el OCR no pudo leer, y entrena a ignorarla.

**Remedio.** Declarar los cuatro en `INTAKE_CONTROL_FILES`. Su mutante: una corrida sobre un caso
con lote de correo y `_ficha_crm.yaml` no debe producir **ninguna** fila `sin_soporte` cuyo origen
empiece por `_` o cuyo basename empiece por `_`, y el test tiene que morir si vuelve a producirla.
Y la capa que cierra la familia en vez del caso: un test que recorra los ficheros que el repo
escribe en `00_Input/` —los literales que aparecen en `email_export`, en el intake y en el runbook—
y exija que cada uno esté en el registro. Sin eso, el quinto fichero de protocolo que alguien añada
vuelve a colarse y nadie lo verá hasta que salga en un `_cobertura`.

**Disparador de promoción.** Ya está disparado: pasa en toda apertura con intake de correo, que son
todas. Barato y de una línea; lo que cuesta es el test de la familia.


## 150. `crm_ficha` declara ERROR sobre una escritura que SÍ entró: el CRM desescapa `&amp;`

> ✅ **CERRADO 2026-09-04 — PR #278.** `_mismas_notas` desescapa las dos partes y compara por
> **igualdad** (no por inclusión: un `in`/`startswith` habría dejado pasar unas notas truncadas
> por el servidor, perdiendo justo la cobertura por la que la verificación existe). Los dos
> mutantes fijan las dos mitades.

**Medido el 2026-09-04 sobre el expediente 637 (W-02JSVZ).** `python -m scripts.crm_ficha
--case-id W-02JSVZ --yes` escribió la ficha entera y terminó en **exit 1**:

```
OK Notas actualizadas
Verificación: expediente 637 Numero_Expediente=77
  [FALTA] Notas: el CRM devuelve un contenido distinto del escrito
[ERROR] La lectura DESMIENTE la escritura: no consta -> Notas.
```

La lectura no desmentía nada. Releído el campo por API y comparado contra el `_ficha_crm.yaml`:

```
escrito: 5158  guardado: 5142
iguales: False
iguales tras deshacer &amp;: True
```

Las 16 diferencias son cuatro `&amp;` que el CRM **decodifica a `&`** al guardar
(`pitch&amp;putt` → `pitch&putt`, `E&amp;V` → `E&V`). El contenido está íntegro: mismo principio,
mismo final, mismos 5.142 caracteres útiles.

**Por qué esto es peor que un bug cosmético.** El verificador de `crm_ficha` es la pieza que
implementa «verificar por resultado, nunca por status», y su mensaje —«los OK de arriba se apoyaban
en el status»— es correcto como doctrina. Pero aquí produce un **rojo sobre un éxito**, y lo produce
**siempre** que las notas escriban «E&amp;V» en HTML bien formado, o sea en casi toda ficha de este
cliente. Un guardián que grita en el caso normal se desactiva solo: el operador aprende que el rojo
de Notas no significa nada, y el día que la escritura falle de verdad no lo va a distinguir. Es la
enfermedad simétrica de la familia que este repo ya persigue.

**Lo que NO hay que hacer:** dejar de escapar `&` en el YAML. El campo es HTML y `&` suelto es HTML
inválido; el problema no es el dato, es la igualdad con que se compara.

**Remedio.** Comparar el campo `Notas` **normalizando entidades HTML en los dos lados** antes de
decidir (`html.unescape` sobre escrito y guardado), y solo entonces declarar la discrepancia.
Dos mutantes, porque hacen falta los dos: (1) unas notas con `&amp;` que el CRM devuelve
desescapadas deben verificar **ok**, y el test muere si vuelve a dar `[FALTA]`; (2) unas notas
realmente **truncadas** por el servidor deben seguir dando `[FALTA]` — si la normalización se hace
con un `in` o un `startswith` en vez de una igualdad sobre texto normalizado, el segundo mutante
sobrevive y se pierde justo la cobertura que esta pieza existe para dar.

**Disparador de promoción.** Ya está disparado, y es de coste alto por frecuencia: hoy `crm_ficha`
sale con exit 1 en cada apertura, así que ni sirve para encadenar en un script ni se puede leer su
código de salida como señal.

## 151. La sala de lectura: `organizar` no puede terminar un caso, y destruye la clasificación a mano

> ✅ **CERRADO 2026-09-04 — PR #278**, cuatro de los seis remedios, y en el orden de daño que
> esta entrada proponía: (a) ruta MD + resolución de bundles partidos, que reparó
> `preparar-residuo` y los 140 enlaces muertos del índice; (b) `_write_worklist` fusiona en vez de
> reconstruir; (c) `organizar` encadena `catalogo` y `aplicar`, así que el ciclo **converge**; (e)
> la CLI resuelve el W-code. Con sus mutantes, y todos rojos antes.
>
> **Siguen abiertos los dos que no son baratos:** (d) que una sala poblada con 0 acciones sobre un
> catálogo vacío *falle* en vez de felicitarse —hoy ya no puede ocurrir por (c), así que es
> cinturón y tirantes— y (f) la **estructura plana**, que toca el layout de `poblar` y del índice y
> espera la decisión sobre el pivote a la skill. Y con ella el tercer defecto de `MEJORAS #67`.
>
> **La R1 adversarial encontró OCHO defectos más en esta misma pieza, y los ocho eran míos**
> (`65f543a`): `organizar` no incorporaba documentos nuevos si ya había catálogo; una fila obsoleta
> de la worklist pisaba una clasificación vigente; la CLI entregaba solo el primer segmento de un
> bundle; un MD canónico obsoleto tapaba los segmentos actuales; los enlaces «ver texto» seguían
> muertos **justo** para los bundles partidos que esta pieza había medido; un `Tipo` inválido
> volvía el documento invisible; una `Fecha` vaciada a propósito se reponía (familia del `H-09`);
> y el glob no exigía gramática ni ordenaba por número. Nueve mutantes en
> `tests/test_sala_lectura_r1_adversarial.py`, los nueve rojos antes. Informe y adjudicación:
> `docs/superpowers/specs/2026-09-04-apertura-w02jsvz-pipeline-r1-adversarial-review.md`.
>
> **El diagnóstico del §«frontera» se confirmó al arreglarlo:** las guardas existían en el
> envoltorio —`clasificar` del CLI ya rebuildeaba el catálogo, `rellenar_worklist` ya respetaba las
> celdas rellenas— y `organizar` las rodeaba llamando al core. No faltaban guardas: faltaba que el
> otro llamador pasara por ellas.

**Medido el 2026-09-04 montando la sala de lectura de W-02JSVZ (167 documentos, 99 de residuo).**
El runbook §7 ofrece `scripts.sala_lectura organizar` como el comando todo-en-uno y advierte, aparte,
de «no usar el CLI deprecado `core/sala_lectura.py` directamente» por los tres defectos latentes de
`MEJORAS #67`. **Esa advertencia nombra la cosa equivocada:** `scripts/sala_lectura.py:117` es un
paso-a-través de dos líneas a `core.sala_lectura.organizar`, así que la vía sancionada *es* el
módulo del que avisa. Los tres defectos dejaron de ser latentes y aparecieron dos más.

**1. `organizar` omite dos de los cinco pasos de su propia secuencia.** La secuencia documentada es
`catalogo → clasificar → [worklist] → aplicar → poblar → render`. `core.sala_lectura.organizar` es
`clasificar_caso → (parar si residuo) → render_indices → poblar_sala_lectura`: sin `catalogo` y sin
`aplicar`. Consecuencia sobre un caso recién abierto:

```
$ sala_lectura organizar   → "Sala de lectura organizada. Acciones: {}"    (indice_documental.yaml = 0 KB)
$ sala_lectura catalogo    → "Catálogo: 167 entradas"                      (103 KB)
$ sala_lectura organizar   → "Detenido: 99 doc(s) en revision."
```

La primera línea es el defecto: **declaró organizada una sala vacía**, con éxito y sin aviso, porque
clasificó un índice que no existía. Un inventario vacío que no activa nada es indistinguible de «no
había nada que hacer».

**2. Y al volver a correrlo, borra la worklist rellenada a mano.** `clasificar_caso` **reconstruye**
`_clasificar.md` con `path.write_text(...)` y las columnas Tipo/Parte/Descripcion en blanco. Así que
el ciclo que el propio mensaje del CLI recomienda —«Rellena la worklist y vuelve a correr
`organizar`»— **destruye lo que acabas de rellenar**: medido, 99 filas clasificadas a mano se
perdieron en la corrida siguiente, y el `aplicar` posterior devolvió `Aplicadas: 0`. El ciclo que el
CLI propone no converge nunca. La secuencia que sí funciona es rellenar y llamar `aplicar` →
`poblar` → `render` **sin volver a pasar por `organizar`** (así salieron `Aplicadas: 99`,
`COPY: 147, SKIP_DEDUP: 20`, 140 documentos en la sala).

**3. La ruta MD apunta al motor jubilado, y eso mata los enlaces del índice.** `_md_path`
(`core/sala_lectura.py:244`) construye `01_Procesado/MD/<slug>.md`; la sala de máquina escribe en
`01_Procesado/02_Sala de máquina/03_MD/`. `01_Procesado/MD/` está vacío, luego:

- `preparar-residuo` responde «**Sin residuo con texto extraído. Nada que preparar**» con 99
  documentos en residuo y 176 espejos MD en disco. Es un «no hay» que en realidad es «miré donde no
  está» — el `if not md.exists(): continue` se los come en silencio.
- Los **140** enlaces «ver texto» de `INDICE.md` apuntan a `../MD/…` y están **todos muertos**, en
  el índice que es justo lo que lee el abogado.

Medido cuánto arregla mover solo el directorio: de los 99, **88 casan por nombre** con un MD real y
**11 no**, y los 11 son bundles que el split partió (`165.pdf`, `Contrato Golf 14jul17.pdf`,
`Anexo contrato restaurante 18jun20.pdf`, `20260709104308879.pdf`…): el padre no tiene MD propio,
su texto vive en los hijos `…__d01_…md`, `…__d02_…md`. Luego el arreglo es de **dos** piezas —
directorio nuevo, y resolución por `glob('*__<hash8>*.md')` para los partidos—, no de una.

**4. La sala sale en subcarpetas por fuente.** `Sala lectura/Drive E&V/` (103) y
`Sala lectura/Email/` (35), cuando la skill v1.3 fija estructura **PLANA** y la categoría en
`INDICE.md`. Tercer defecto de `#67`, confirmado en vivo.

**5. `sala_lectura` no resuelve el W-code.** `abrir_caso` y `sala_maquina` aceptan `W-02JSVZ`;
`sala_lectura` llama a `config.caso_path` (o sea `path_for`) sin pasar por `resolve_ref` y aborta con
`LocalWorkspaceMissing`. Y en el camino **deriva una ciudad equivocada** (`city='Valencia'` para un
caso de Barcelona), que es el mismo error con otra cara: resolver una referencia que no entiende en
vez de rechazarla.

**La frontera.** No son cinco defectos, es uno: **el módulo está marcado como jubilado y sigue
siendo la única implementación**, así que nadie lo arregla y nadie lo sustituye. El pivote a la
skill se decidió pero no se hizo (ver memoria `project-sala-lectura-prompt-driven`, «el PIVOTE a
local sin decidir»). Mientras el CLI sea la vía real, sus defectos son defectos de producción, no
deuda de un módulo muerto.

**Remedio, por orden de daño.** (a) Ruta MD + resolución de bundles: repara `preparar-residuo` y 140
enlaces, y es lo más barato. (b) Que `clasificar_caso` **no pise** celdas ya rellenas — su mutante:
una worklist con 99 filas clasificadas debe seguir teniendo 99 tras `organizar`, y el test muere si
vuelven a quedar en blanco. (c) Que `organizar` encadene `catalogo` al principio y `aplicar` tras la
worklist, o que deje de llamarse todo-en-uno. (d) Que una sala poblada con 0 acciones sobre un
catálogo vacío **falle** en vez de felicitarse. (e) `resolve_ref` en el CLI. (f) Estructura plana.

**Disparador de promoción.** Disparado: es el montaje de la sala de lectura de cualquier caso, y hoy
solo termina si quien lo corre sabe saltarse el comando que el runbook recomienda. Actualizar el §7
del `RUNBOOK_APERTURA_EXPEDIENTE` con la secuencia que sí converge es lo primero, y no cuesta código.

## 152. Dos tests exigen `.env`, así que la suite da rojo falso en cualquier worktree

> ✅ **RESUELTA el 2026-09-05 en la rama a la que se cedió** (`claude/beautiful-gates-438572`,
> autorrelleno de fichas de colaborador desde la firma del correo). La cesión funcionó: el arreglo
> cae dentro de la función que esa rama reescribía, y hacerlo allí evitó la tirita a mitad de
> refactor. **Los dos tests reciben ahora `client=MagicMock()`** y pasan **sin `.env`**: 21/21
> verdes desde un worktree limpio.
>
> **Y la propiedad sigue protegida, que es lo que importaba:** mutando la guarda para que el
> respaldo por email corra con el criterio del NIF caído, **los dos tests vuelven a fallar**. No se
> arregló la configuración a costa de vaciar el test.
>
> **De paso, un defecto que la entrada no había visto.** La última línea del segundo test era
> `respaldo.assert_not_called(), "mensaje"` — una **tupla**, no un `assert`. El método sí se llamaba
> y sí levantaba, así que el test funcionaba, pero su mensaje no se mostraba **nunca**: al fallar no
> decía qué propiedad se había roto. Convertida en un `assert` de verdad.
>
> **Lo que esto NO arregla, y conviene no leerlo de más:** el `leak-guard` de pre-commit sigue
> ciego en los worktrees (`#161`). Son dos problemas distintos con la misma raíz —los artefactos
> gitignored que un worktree no hereda—, y sólo se cierra el de los tests.

**Medido el 2026-09-04.** La suite corrida desde el worktree
(`.claude/worktrees/nuevo-caso-bad-debt-ffe40e`) devuelve exit 1 con dos fallos, y desde la raíz del
repo la misma selección va verde:

```
worktree: ..F.F................  → FAILED tests/test_crm_dedup_incertidumbre.py::TestUnaConsultaCaidaNoEsAusencia::test_el_colaborador_tampoco
                                   FAILED tests/test_crm_dedup_incertidumbre.py::test_el_respaldo_del_colaborador_no_corre_si_el_NIF_no_se_pudo_mirar
raíz:     .....................  → 21 passed
```

**La causa, y no es que el guard esté mal.** Los dos tests parchean `_buscar_registros` y esperan
que `ensure_colaborador_vinculado` levante `IdentidadSinComprobar` cuando el NIF no se pudo mirar.
Pero esa función construye `SudespachoLegacyClient()` (`core/sudespacho_relations.py:2125`) **antes**
de llegar a lo parcheado, y el constructor exige `SUDESPACHO_LEGACY_HOST` del `.env`
(`sync_sudespacho_legacy.py:393`). Sin `.env` explota con `SudespachoLegacyError`, que
`pytest.raises(IdentidadSinComprobar)` no atrapa. Con `.env` la construcción es **inerte** —solo
lee configuración, no abre red— y el test ejerce exactamente lo que dice ejercer. Luego el guard es
correcto: lo que falla es la **hermeticidad**.

**Por qué importa más de lo que parece.** `.env` está gitignored y un worktree no lo hereda; eso ya
lo dice `[APER-01]` del runbook de apertura, pero **para el pipeline**, no para los tests. Y el
flujo estándar del repo es «una mesa = una tarea = una rama», o sea worktree. Así que el gate de
«suite verde» del cierre sale rojo por construcción en el sitio donde se trabaja, con dos fallos que
no tienen nada que ver con lo que se acaba de cambiar. Es el patrón que enseña a ignorar el rojo, y
ya costó una investigación aquí para descartar que fuera del diff.

**Remedio.** Que los dos tests no dependan de la configuración real: parchear
`core.sudespacho_relations.SudespachoLegacyClient` (o inyectar el `client`, que la firma ya acepta)
en vez de dejar que se construya desde el entorno. Dos mutantes, y hacen falta los dos: (1) sin
`.env`, los dos tests deben pasar — el test muere si vuelven a fallar por configuración ausente; y
(2) con el respaldo por email **sí** llamado, el test debe seguir fallando — si al desacoplar el
cliente se pierde el `respaldo.assert_not_called()`, se pierde justo la propiedad que H-04 protege.

**Disparador de promoción.** Disparado y recurrente: sale en cada corrida de la suite desde un
worktree. La alternativa barata mientras no se arregle —correr la suite desde la raíz— es la que ya
prescribe `[APER-01]`, pero conviene decirlo también en el §11 del runbook, que es donde se mira al
cerrar.


## 153. La puerta PRINCIPAL de alta no valida nada: la UI reproduce el caso `s/n`

> ✅ **CERRADO 2026-09-05.** Validado **en el sumidero** (`ensure_case`), no en la
> puerta: así queda cubierta también la que nadie ha escrito todavía. Diseño en
> `docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-design.md` (rev. 2) y la R1 que lo falsó, con su informe literal, en `docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-r1-adversarial-review.md`.
>
> **Lo que NO cierra, y se dice:** que sea imposible sacar un expediente de
> `CASOS_ROOT` por otras vías. Hay tres puertas más, abiertas como `#155`, `#156` y
> `#157` con la evidencia ejecutada de la R1.

> 🔴 **ABIERTA.** Levantado por la R1 adversarial del 2026-09-04 (`docs/superpowers/specs/2026-09-04-apertura-w02jsvz-pipeline-r1-adversarial-review.md`).
> **Preexistente**: no lo introdujo el diff de `MEJORAS #148`, lo dejó al descubierto.

`MEJORAS #148` arregló `componer_case_id`, que es la vía del **CLI de seis flags**. Pero
`streamlit_app.py:1977-1994` **compone `_case_id_auto` con su propia interpolación** y pasa
`final_case_id` directo a `case_manager.ensure_case` (`:338-343`), sin pasar por
`componer_case_id` ni por `exigir_sin_caracteres_de_ruta`. Con una dirección que lleve `s/n`,
Windows interpreta el `/` como separador, se crean dos componentes bajo la ciudad y **la UI
muestra «Caso local disponible»**. El revisor lo reprodujo sobre head:

```text
FAILED test_case_creation_rejects_multicomponent_case_id
E Failed: DID NOT RAISE ValueError
```

**Por qué esto va POR DELANTE de lo que ya se arregló.** El CLI de seis flags lo uso yo; la UI de
Streamlit es la que usan **Paola y Ana**, que no tocan código. Arreglar la puerta de servicio y
dejar abierta la principal es el orden equivocado, y solo se vio porque el mandato de la R1
declaraba esta duda como no verificada: «¿queda alguna vía que componga una ruta de caso desde
entrada del usuario sin pasar por `componer_case_id`?». La respuesta fue sí.

**Remedio.** El sumidero es único: `ensure_case`. Validar **ahí** —no en cada puerta— es lo que
cierra la familia en vez del ejemplo, y de paso cubre cualquier llamador futuro. Su mutante: una
dirección con `/` desde la composición real de Streamlit debe abortar **antes** de `ensure_case`
y no dejar ninguna carpeta parcial; el test muere si vuelve a crearse el esqueleto.

**Disparador de promoción.** Disparado: cualquier finca rústica con `s/n` dada de alta desde la UI.


## 154. El override de ruta permite escapar de `CASOS_ROOT`

> ✅ **CERRADO 2026-09-05.** Validado **en el sumidero** (`ensure_case`), no en la
> puerta: así queda cubierta también la que nadie ha escrito todavía. Diseño en
> `docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-design.md` (rev. 2) y la R1 que lo falsó, con su informe literal, en `docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-r1-adversarial-review.md`.
>
> **Lo que NO cierra, y se dice:** que sea imposible sacar un expediente de
> `CASOS_ROOT` por otras vías. Hay tres puertas más, abiertas como `#155`, `#156` y
> `#157` con la evidencia ejecutada de la R1.

> 🔴 **ABIERTA.** Levantado por la R1 adversarial del 2026-09-04 (`docs/superpowers/specs/2026-09-04-apertura-w02jsvz-pipeline-r1-adversarial-review.md`).
> **Preexistente.** Familia de `MEJORAS #141` (`buscar()` no valida el `case_id`, así que una
> referencia con `..` escribe fuera del catálogo): mismo agujero, otra puerta.

`streamlit_app.py:1983-1994` acepta un override de ruta del usuario; `destino_de_alta` y
`path_for_ciudad` (`core/casos/case_locator.py:132-158, 261-267`) **concatenan sin exigir un
componente relativo ni verificar contención**. Una ruta absoluta descarta la raíz y un `..` la
atraviesa; después `ensure_case` hace `mkdir(parents=True)` y deposita el expediente ahí. El
revisor midió que la composición pura devuelve `C:\Windows` para un `case_id` absoluto:

```text
FAILED test_case_creation_rejects_parent_traversal
E Failed: DID NOT RAISE ValueError
```

**Lo que NO hace falta** es imponer el formato canónico del `case_id` —eso ya se midió como una
guarda demasiado ancha en `#148`—. Lo que falta es la **contención**: que el destino resuelto esté
bajo `CASOS_ROOT`, comprobado con `Path.resolve()` y no con comparación de cadenas.

**Remedio.** La misma comprobación en el sumidero que `#153`, y con los dos mutantes que hacen
falta: una ruta absoluta y un `..` abortan sin crear nada, **y** un `case_id` legítimo con
paréntesis, comas y acentos sigue pasando — endurecer de más aquí rompe el alta de casos que ya
existen en el catálogo.

**Disparador de promoción.** Se promueve **junto a `#153`**: comparten sumidero y arreglarlos por
separado es hacer dos veces el mismo trabajo. Riesgo bajo por frecuencia (hay que teclear el
override a mano) y alto por consecuencia (expediente con PII fuera del árbol gobernado).


## 155. `move_to_city` mueve el expediente completo fuera de `CASOS_ROOT`

> 🔴 **ABIERTA.** Destapada por la R1 adversarial del 2026-09-05 (`docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-r1-adversarial-review.md`, H-01), **con
> reproducción ejecutada**. Es la puerta que falsó la premisa central de `#153`/`#154`.

`core/casos/case_locator.py:270-319`. `move_to_city` valida **solo la longitud del motivo**;
compone el destino con `path_for_ciudad(case_id, ciudad_destino)`, hace
`dest.parent.mkdir(parents=True)` y `shutil.move(src, dest)`. No pasa por `ensure_case`, no
valida la ciudad y no comprueba contención. El revisor lo corrió:

```json
{"test": "move", "dest": "...\\p\\move\\FUERA\\EV-2026-001", "outside": true,
 "payload": "CANARIO", "source_exists": false, "buscar": null}
```

El árbol entero sale de la raíz, **el origen desaparece** y `buscar` pierde el caso. Con el
canario dentro: los bytes del expediente se van con él.

**Mi error, que conviene que conste porque es el patrón:** yo encontré esta función antes de que
volviera el informe y la **archivé como no explotable** porque la UI ofrece la ciudad en un
`selectbox` de catálogo cerrado (`streamlit_app.py:1436`). El revisor lo rebate en una línea:
*el catálogo está en el envoltorio; no protege la API de core*. Usé como garantía exactamente la
clase de cosa que `#153` venía a arreglar.

**Remedio.** La misma pareja que `ensure_case`: `exigir_componente_de_ruta(ciudad_destino)` +
pertenencia a `_CITY_NAMES` + contención léxica y física del destino, **antes** del `shutil.move`.
Su mutante: `move_to_city(case, '../FUERA', motivo, actor)` aborta, **el origen sigue existiendo**
y el exterior queda vacío — la aserción sobre el origen es la que importa, porque el daño de un
`move` es que no hay copia que recuperar.

**Disparador de promoción.** Riesgo bajo por frecuencia (la UI cierra el catálogo) y **alto por
consecuencia**: mueve, no copia. Se promueve **junto a `#156`**, que comparte la falta de contrato
en el destino.


## 156. `reservar_lote` / `caso_path` admiten un directorio absoluto externo como si fuera un caso

> 🔴 **ABIERTA.** R1 adversarial del 2026-09-05 (`docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-r1-adversarial-review.md`, H-01, segundo contraejemplo), con
> reproducción ejecutada.

`core/casos/case_locator.py:43-46` acepta **cualquier directorio absoluto existente** como si
fuera un caso, y **no exige `_caso.md`**. Con eso,
`reservar_lote(str(directorio_exterior), 'manual', 'sonda')` (`core/intake_lotes.py:89-98`) crea
`00_Input/<lote>` **fuera de la raíz**, sin pasar por `ensure_case`:

```json
{"test": "intake_absolute", "outside": true, "lote_exists": true, "index": false}
```

No es un alta completa —no hay `_caso.md`— y esa distinción **no devuelve la contención**: hay un
árbol de intake de un caso fantasma fuera del árbol gobernado.

**La frontera, y por eso no es trivial:** aceptar una ruta absoluta es **deliberado** en el modo
local (`CASOS_ROOT` al Desktop tras un *checkout*), así que el remedio no es prohibirlo: es
**exigir que sea un caso** (que tenga `_caso.md`) o que esté registrado como copia prestada. Es
decir, distinguir *checkout legítimo* de *escape accidental*, que es literalmente lo que el
revisor pidió.

**Remedio.** Que `caso_path`/`localizar` exijan la marca de caso (`00_Input/_caso.md`) o
pertenencia al `WorkspaceRegistry` antes de devolver un directorio de fuera. Dos mutantes: un
directorio externo **sin** `_caso.md` se rechaza, y una copia prestada **registrada** sigue
funcionando — sin el segundo, el arreglo rompe el modo local.

**Disparador de promoción.** Junto a `#155`. Y ojo: toca la resolución de qué copia es la
operativa, así que por radio de daño son **dos rondas**.


## 157. Una junction preexistente en un hijo del caso saca los bytes del árbol gobernado

> 🔴 **ABIERTA.** R1 adversarial del 2026-09-05 (`docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-r1-adversarial-review.md`, H-04), demostrada con una **junction
> real de Windows**. Límite declarado del arreglo de `#153`/`#154`, no un descuido.

Con `CASOS/EV-2026-002/` como directorio normal y su `00_Input` como *junction* hacia fuera
—creada **antes** del alta—, la contención de `ensure_case` pasa (el directorio del caso sí está
contenido), `mkdir(exist_ok=True)` acepta el hijo enlazado, y `_write_case_index` deposita el
`_caso.md` **fuera**:

```json
{"test": "junction_case",  "result": "ValueError", "out_empty": true}
{"test": "junction_child", "case_inside": true, "outside_index": true}
```

La primera línea es el control hermano: una junction **en el propio caso** sí se rechaza. Al
ponerla **en un hijo**, el índice acaba fuera. **No es un TOCTOU**: no hace falta cambiar ningún
enlace entre la comprobación y la escritura.

**Por qué no se arregla con una comprobación más.** `ensure_case` valida **un** directorio y
escribe en **nueve** descendientes. Contenerlos todos es un contrato distinto: o se comprueba
cada destino antes de cada escritura —y entonces la costura natural es
`core/casos/escritura.py`, que ya lo hace con `_bajo` para las escrituras *dentro* de un caso—, o
se declara que el árbol de un caso no puede contener enlaces y se verifica al abrirlo.

**Remedio propuesto:** enrutar las escrituras del alta por la costura de `escritura.py`, que ya
tiene la propiedad, en vez de añadir una comprobación nueva. Su mutante: el escenario de arriba
aborta **antes** de escribir fuera y **sin dejar andamiaje parcial**.

**Disparador de promoción.** El más bajo de los tres: exige una junction preexistente en el árbol
de casos, que hoy nadie crea. Se registra porque está **medido** y porque el arreglo de
`#153`/`#154` declara expresamente no cubrirlo.


## 158. La cuarta puerta al sumidero: `intake_manual` confía en el `lote` que le pasan

> 🔴 **ABIERTA.** R2 adversarial del 2026-09-05 (`docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-r2-adversarial-review.md`, H-06), **preexistente** — no la
> introdujo el arreglo de `#153`/`#154`, la destapó. Verificada contra la fuente el mismo día.

`core/intake_manual.py` tiene tres funciones de depósito y **las tres validan la mitad
relativa y ninguna la absoluta**:

| Función | Qué valida | Qué acepta sin mirar |
|---|---|---|
| `save_file` | que `filename` no lleve separadores, y que el caso **exista** | `lote` |
| `extract_zip` | que el caso exista, y `safe_zip_extract` contra `lote` | `lote` |
| `save_file_en_lote` | `rel` contra `lote`, con `resolve()` y todo | `lote` |

En las tres, `lote` entra como argumento y sale como `dest = lote / rel`. Un `lote` absoluto
apunta a donde quiera: `pathlib` descarta el lado izquierdo, así que ni siquiera hace falta un
`..`. La guarda de nombre y la de existencia del caso dan la **apariencia** de camino cerrado.

**Es exactamente la forma del defecto que ya está anotado como propio:** la guarda vive en el
envoltorio y el otro llamador no pasa por ella. Aquí está incluso escrito en el docstring de
`save_file_en_lote` — «el caller ya validó la existencia del caso al abrir el lote con
`abrir_lote_manual`/`reservar_lote`, que aplica el guard §6)». Eso es una **premisa sobre el
llamador**, no una comprobación; y `save_file`, cuando recibe `lote=None`, sí llama a
`abrir_lote_manual` —o sea que la vía buena existe— pero cuando lo recibe, no comprueba nada.

**Remedio.** Una sola línea en cada una de las tres, antes del primer `mkdir`: que `lote` esté
contenido en `caso_path(case_id)` —o en la copia operativa que resuelva `CaseWorkspace`—, con
`_contenido_en` de `core/case_manager.py`, que ya tiene la propiedad y ya documenta por qué no
usa `case_mutex._bajo`.

**Su mutante:** quitar esa línea y pasar `lote=Path(tmp_path)/"FUERA"` a cada una de las tres
tiene que dejar el fichero fuera del árbol de casos — hoy lo deja, y los tests actuales pasan.

**Disparador de promoción.** Junto a `#155`/`#156`/`#157`, que son las otras puertas del mismo
sumidero. Por sí sola no urge: hoy los tres callers vivos (`streamlit_app`, el CLI de intake
manual, `intake_lotes`) pasan lotes que ellos mismos han abierto. Lo que la hace registrable es
que **el contrato no lo dice y nada lo impide**.


## 159. `case_mutex._bajo` rechaza a los hijos de una raíz anclada

> 🔴 **ABIERTA.** R2 adversarial del 2026-09-05 (H-02), medida. Es el motivo de que
> `core/case_manager._contenido_en` exista en vez de reutilizar `_bajo`, y así está dicho en su
> docstring.

`core/casos/case_mutex._bajo` decide contención con `c.startswith(r + os.sep)`. Cuando la raíz
**ya termina en separador** —una unidad (`C:\`) o un recurso UNC (`\server\share\`)— eso exige
dos separadores seguidos y devuelve `False` para **todo** descendiente legítimo:

```
_bajo(Path('C:/CASOS/EV-2026-001'),      Path('C:/'))              -> False
_bajo(Path('//server/share/CASOS/EV'),   Path('//server/share/'))  -> False
```

Con `CASOS_ROOT` apuntado a la raíz de una unidad o a un recurso de red —los dos configurables
hoy por `.env`— el mutex del caso consideraría que ningún caso está bajo su raíz.

**Por qué no se arregló de noche, junto al resto.** Lo consume el **mutex del caso**, cuyo radio
de daño es «quién puede escribir sobre qué copia»: por presupuesto de rondas son **dos**, una de
diseño y una de diff, y esta pieza entró como remediación de una R2 ya cerrada. Cambiar la
semántica de contención del mutex a las 3 de la mañana, sobre una propiedad que no falla en
ninguna configuración viva, es precisamente lo que el techo de rondas existe para impedir.

**Remedio.** Sustituir el cuerpo de `_bajo` por `os.path.commonpath`, que no tiene el caso
especial, y **borrar `_contenido_en`** dejando un solo hogar para la propiedad — el mismo patrón
que cerró el punto 4 de este encargo con `_MD_SUBDIR`. Sus mutantes: los dos casos anclados de
arriba en verde, y los dos negativos (`D:/CASOS/EV` bajo `C:/CASOS`, `C:/CASOS_x/EV` bajo
`C:/CASOS`) que impiden que el arreglo se vuelva permisivo. Los cuatro ya están escritos en
`tests/test_ensure_case_sumidero_r2.py::test_la_contencion_acepta_los_hijos_de_una_raiz_anclada`,
apuntados a `_contenido_en`: al unificar, se reapuntan a `_bajo`.

**Disparador de promoción.** Que alguien configure `CASOS_ROOT` en la raíz de una unidad o en un
UNC. Mientras `CASOS_ROOT` sea una subcarpeta —lo que es en las tres máquinas— la propiedad no
se ejerce.


## 160. `ensure_colaborador_vinculado` necesita credenciales ANTES de poder fallar cerrado

> ✅ **RESUELTA el 2026-09-05** en `claude/beautiful-gates-438572`, junto con la `#152`, que es el mismo defecto visto desde el lado del test: los dos tests inyectan ahora el `client` en vez de dejar que se construya desde el entorno. La función **no** cambió: el acoplamiento con el `.env` sigue ahí para cualquier otro llamador que no inyecte cliente, y eso es deliberado — arreglarlo de verdad es tocar la construcción del cliente legacy, que no es de esta rama.

> 🔴 **ABIERTA.** Medido el 2026-09-05 al correr la suite **desde un worktree**, que es el
> flujo estándar del repo (`docs/FLUJO_GIT.md`) y **no hereda `.env`**. Preexistente: entró con
> el PR #272 (`ecc21ac`) y no la toca ninguna rama en curso mía.
> ⚠️ **Módulo de la sesión hermana** (alta de colaborador en el CRM): avisada, no tocado.

Dos tests de `tests/test_crm_dedup_incertidumbre.py` fallan en cualquier clon sin `.env`:

```
tests/test_crm_dedup_incertidumbre.py::TestUnaConsultaCaidaNoEsAusencia::test_el_colaborador_tampoco
tests/test_crm_dedup_incertidumbre.py::test_el_respaldo_del_colaborador_no_corre_si_el_NIF_no_se_pudo_mirar
E   core.sync_sudespacho_legacy.SudespachoLegacyError: Falta SUDESPACHO_LEGACY_HOST en .env.
```

**No es un fallo del test: es la forma de la función.** `core/sudespacho_relations.py:2123-2125`
construye el cliente **antes** del `try`, así que `ensure_colaborador_vinculado` exige
credenciales para llegar a la comprobación de identidad. Su hermana `ensure_contrario_vinculado`
no falla en el mismo entorno, y las dos tienen el mismo parámetro `client=None`: la asimetría es
**cuándo** se materializa el cliente, no la firma.

**Por qué importa más que un test rojo.** La propiedad que esos dos tests fijan es del PR #272 y
es buena —*«un 500 tiene que constar, no colapsar en no existe»*—, pero en un entorno sin `.env`
la función levanta un **error de configuración** donde la propiedad pide `IdentidadSinComprobar`.
Los dos fallan cerrado, así que no hay pérdida de datos; lo que se pierde es la **capacidad de
distinguir** «no pude mirar la identidad» de «no pude mirar nada porque no hay credenciales».
Es la familia de `feedback-no-lo-se-no-es-no-hay` en el nivel de la causa.

Y el efecto práctico: **la suite no es verde en un worktree limpio**, o sea que el instrumento
con el que se decide si una rama entra a `main` depende de un fichero que el worktree no tiene.
Eso convierte dos rojos permanentes en ruido de fondo, que es cómo se pierden los rojos de
verdad.

**Remedio.** Mover la construcción del cliente **después** de resolver la identidad, o
—equivalente y más barato— hacerla perezosa: `_resolver_colaborador` ya recibe `client`, así que
basta que el cliente se materialice en el primer uso real. Su mutante: los dos tests de arriba
tienen que pasar **sin `.env`** y seguir levantando `IdentidadSinComprobar`, no
`SudespachoLegacyError`.

**Disparador de promoción.** Inmediato en cuanto la sesión hermana toque ese módulo: es una
línea movida dentro de la función que está reescribiendo, y arreglarlo desde fuera sería pisarla.


## 161. El `leak-guard` de pre-commit es INERTE en todo worktree, y por eso dejé pasar PII  [PROMOVIDO → PLAN.md] `[RESUELTO 2026-09-05 — vías (1)+(2); la (3) queda diferida]`

> ✅ **Resuelto el 2026-09-05 (PR #289), con las vías (1) y (2) de abajo, decididas por
> Nikolai ese día.** `cargar_blocklist` lee ahora la **unión** de dos raíces: el árbol que se
> commitea y el **checkout principal** del mismo repo — el primero de `git worktree list`, aceptado
> solo **verificado por resultado** (`resolver_blocklist` / `_resolver_principal` en
> `scripts/precommit_leak_guard.py`). Y cuando la lista sale vacía en las dos, `main` lo **declara
> en STDERR** con el estado observado de cada ruta y la frase «NO se ha ejecutado»; el hook va
> con `verbose: true` porque pre-commit **no muestra** la salida de un hook que pasa si no lo es.
> Tests con repos git **reales** (principal + worktree, gitdir separado, bare), aislados de la
> config de la máquina (`tests/test_precommit_leak_guard.py`, bloque «MEJORAS #161»), incluido el
> mutante de abajo: término conocido commiteado desde un worktree sin lista → ahora **bloquea**.
> Efecto lateral buscado: `tests/test_no_pii_en_tests.py` deja de saltarse en los worktrees.
> **R1 de Codex sobre el diff: NO-SHIP, 8/8 confirmados, remediados** — adjudicación en
> `docs/superpowers/plans/2026-09-05-mejoras-161-blocklist-desde-la-raiz-comun.md` §4.
> **Lo que NO se hizo:** fallar cerrado (vía 3). Sigue siendo la doctrina de la casa, pero solo
> tiene sentido cuando no encontrar la lista sea una anomalía, y hasta este PR era el caso normal.
> Disparador para promoverla: que el aviso aparezca en una máquina que SÍ debería tener la lista.
>
> Lo de abajo es el texto original, conservado como medición.

> 🔴 **ABIERTA y con daño real, no hipotético.** Medido el 2026-09-05: una dirección de inmueble
> de la blocklist llegó a GitHub en el commit `eee9a7e` con el hook **en verde**. Lo paró
> `leak-scan` en CI, que sí tiene la lista.

`scripts/precommit_leak_guard.py::cargar_blocklist` lee los términos de dos artefactos
**gitignored**: `data/_saneado/replacements.txt` y `data/_config/pii_blocklist.txt`. Un worktree
recién creado **no tiene ninguno de los dos** — por definición, porque están gitignored. Y el
docstring dice lo que pasa entonces: *«Vacío si no hay ninguno.»*

Con la lista vacía el bucle de comprobación no itera, así que el guard **pasa en verde sin haber
comprobado nada**. Medido en las dos raíces la misma noche:

```
<raíz del repo>          data/_config/pii_blocklist.txt -> existe, 12 líneas (70 términos)
<worktree>               data/_config/pii_blocklist.txt -> NO existe          (0 términos)
```

**Y el flujo estándar del repo es el worktree.** `docs/FLUJO_GIT.md` manda «una mesa = una tarea =
una rama», o sea que **la mayoría de los commits del proyecto se hacen donde el guard no puede
ver nada**. El verde del hook no significa «no hay PII»: significa «no tengo con qué mirar».

**Es exactamente la familia que este repo ya tiene documentada** —una guarda que no puede dar el
otro valor— y aquí en su forma más cara, porque el instrumento inerte es justo el que protege el
dato del cliente.

**Remedio, y la elección importa.** Fallar cerrado es la doctrina de la casa, pero convertirlo hoy
en bloqueo dejaría sin poder commitear a **todas** las sesiones con worktree hasta que alguien
copie la lista, incluida la que está trabajando ahora mismo. Propuesta en dos tiempos:

1. **Ya:** que `cargar_blocklist` **avise en STDERR** cuando devuelve cero términos, diciendo la
   ruta que buscó y que la comprobación de PII **no se ha ejecutado**. Un guard que no puede
   mirar tiene que decirlo; hoy calla.
2. **Con decisión de Nikolai:** o bien fallar cerrado, o bien que el hook resuelva la lista desde
   la **raíz común** (`git rev-parse --git-common-dir` da el `.git` compartido, y de ahí se llega
   al checkout principal), que es lo que la haría funcionar en worktrees sin copiar nada.

**Su mutante:** vaciar la blocklist y commitear un término conocido — hoy pasa en verde y en
silencio; con (1) pasa pero **lo dice**; con (2) lo caza.

**Disparador de promoción.** Inmediato: es la única guarda de PII que corre antes de que el dato
salga de la máquina, y está probado que no corre.

---

---

## 162. Documento de identidad y domicilio del colaborador desde los contratos del Drive

**Estado:** esperando decisión de Nikolai. **No empezar.**

Los contratos de los consultores llevan documento de identidad y domicilio de empleados
de E&V que **no son parte de ningún caso**. La cuenta `@ev` accede a ellos por el rol en
la empresa; volcarlos al CRM del despacho es un tratamiento con otra finalidad y otro
responsable, y esa valoración es de Nikolai.

Y puede ser innecesario: si lo que se busca es **identificar** al colaborador, el email
ya lo hace; el NIF sólo hace falta para facturarle o demandarle.

**Si se promueve:** preguntar primero **para qué colaboradores y con qué finalidad**. No
construir un extractor masivo de documentos y domicilios.

**Disparador:** petición expresa de Nikolai con esas dos respuestas.

---

## 163. El cargo del colaborador no tiene dónde vivir en el CRM

`core/email_firmas.py` **ya extrae** el cargo y sale en el informe de
`scripts.crm_colaboradores_firmas report`, pero no se escribe: el contrato de
`colaboradores` no tiene property de cargo y `tipo` es un `Select` cerrado
(§10.8 de `INTEGRACION_SUDESPACHO.md`).

**Disparador:** que sudespacho añada un campo, o decisión de Nikolai de usar `notas`.
Si llega el campo, sólo hay que añadir el par a `_COMPLETABLES_COLABORADOR` y a
`_AL_YAML`.

---

## 164. `scripts/crm_ficha.py` sigue siendo extrajudicial-only

`[APER-49]`. La pieza C sirve a las dos jurisdicciones (las dos pasan por
`_resolver_o_crear_colaborador`), pero el CLI que la dispara hardcodea
`_ELEMENT_EXTRAJUDICIAL`. Para un caso judicial hay que llamar a mano.

**Hueco previo a este trabajo**, anotado para que no se lea como cerrado. `MEJORAS #128`
ya cubre este mismo `[APER-49]` con más detalle (juzgado, `link_colaborador_judicial`,
etc.); esta entrada no lo duplica, añade el dato nuevo de esta sesión: la pieza que
faltaba para colaboradores (el resolvedor compartido `_resolver_o_crear_colaborador`) ya
existe, así que del lado de colaboradores lo único que falta es cablear el CLI.

---

## 165. `core/email_firmas.py` no detecta el mojibake por charset mal declarado

**Detectado en la Task 9, declarado fuera de alcance.** `extraer_de_eml`
(`core/email_firmas.py:580-584`) envuelve `parte.get_content()` en un `except Exception`
que marca `NO_LEIBLE` ante "charset roto, base64 truncado…". Pero `get_content()`
decodifica con `errors="replace"` y, si el `Content-Type` declara un charset
válido-pero-equivocado (los bytes son UTF-8 y la cabecera dice `iso-8859-1`, o al revés),
la decodificación **no lanza**: produce texto con acentos rotos o con el carácter de
reemplazo `�` y lo devuelve como si fuera válido. El `.eml` se procesa como legible,
la firma se lee sobre texto corrompido y ningún veredicto avisa. Es la misma familia que
el defecto ya anotado en el comentario de las líneas 570-578 del mismo fichero
(`BytesParser` tampoco lanza ante basura sin cabeceras), pero por una vía distinta.

Es una rama defensiva sin caso real que la dispare todavía: los `.eml` de E&V vistos hasta
ahora declaran `charset="utf-8"` y lo son.

**Disparador:** el primer `.eml` real cuyo informe de firmas salga con acentos rotos o con
`�`, o una decisión de blindar `extraer_de_eml` de forma preventiva (por ejemplo,
detectar `�` en `cuerpo` tras decodificar, o contrastar el `charset` declarado con
una detección independiente antes de confiar en él).

---

## 166. El cargo se lee por posición, y en el corpus real falla en las dos firmas que lo traen

**Medido el 2026-09-05 corriendo `crm_colaboradores_firmas report` contra W-02Q38C**, que es
justamente lo que ninguna fixture sintética podía enseñar: de las cuatro firmas del
expediente, **las dos que llevan cargo escrito salen con el cargo vacío**, y por dos causas
distintas.

El cargo **no tiene etiqueta** en ninguna plantilla corporativa de E&V, así que `_cargo_de`
lo deduce por posición: es la primera línea no vacía después de la línea del nombre, y la
línea del nombre se reconoce porque va **enteramente en negrita** (en el `text/plain` los
asteriscos son la negrita HTML degradada). Las dos causas medidas:

- **Una plantilla escribe el nombre sin negrita.** Sin línea en negrita no hay ancla, y el
  cargo —que está justo debajo— no se lee.
- **En la otra, la línea del nombre queda fuera de la ventana del bloque.** El bloque se
  ancla en la línea de la dirección y mira 12 líneas hacia atrás; en esa firma el nombre y
  el cargo están más arriba, separados de la dirección por la razón social, la dirección
  postal partida en varias líneas con enlaces de mapas interleaved, y los teléfonos.

**Qué NO es:** un riesgo para los datos del cliente. El cargo **no se escribe en el CRM**
—no existe esa property, ver `#161`— y sólo sale en el informe que un humano confirma.

**Qué sí es:** el informe dice `FIRMA_SIN_CAMPO` en el cargo, y ese veredicto significa «hay
firma y no trae ese campo» cuando la verdad es «no supe leerlo». Mitigado el 2026-09-05
escribiéndolo en la leyenda del propio informe, que es donde se lee; la mitigación es
honesta pero no arregla la lectura.

**Disparador:** que a Nikolai le importe el cargo en el informe, o que aparezca un campo de
cargo en el CRM (ver `#161`) y el dato deje de ser sólo informativo. Dos vías posibles, en
orden de esfuerzo: ensanchar la ventana hacia atrás sólo para la búsqueda del cargo, o
reconocer la línea del nombre por algo que no sea la negrita (por ejemplo, casarla contra
el nombre que ya se conoce del `From:` o de la ficha del CRM, que es un dato que el módulo
tiene a mano en el CLI aunque no dentro de `core/email_firmas.py`).

---

---

## 167. `case_locator._update_ciudad_metadata` escribe `_caso.md` en sitio y reordena el frontmatter

**Levantado por la R1 adversarial del diseño de `MEJORAS #146` (H-08, 2026-09-05), al censar
todos los escritores de `_caso.md`.** Es el único escritor de producción que ni pasa por
`_write_case_index` ni por `_atomic_write_caso_md`.

**Qué pasa.** `core/casos/case_locator.py::_update_ciudad_metadata` parte el fichero con
`text.split("---", 2)`, hace `yaml.dump(fm, allow_unicode=True, default_flow_style=False)` **sin
`sort_keys=False`** —el default de PyYAML ordena alfabéticamente— y escribe con `write_text` en
sitio. Consecuencias, por lectura de código (sin sonda): (1) cada reasignación de ciudad
**reordena** todas las claves del frontmatter, así que el `diff` del `_caso.md` tras un
`move_to_city` es el fichero entero y no la línea `ciudad`; (2) un corte a mitad deja el índice
truncado, el mismo agujero que `#146` acaba de cerrar en el sumidero; (3) el cuerpo se conserva,
así que no destruye la nota.

**Remedio.** Que `_update_ciudad_metadata` use `_atomic_write_caso_md` con un mutador que toque
`fm["ciudad"]` y `fm["meta"]["ciudad"]`, que es exactamente lo que ya hace `ensure_case` sobre un
caso existente. Su mutante: reasignar la ciudad de un caso con `bucket_override` y una nota, y
exigir que el orden de claves y la nota no cambien y que no quede temporal.

**Por qué no entra en `#146`.** `move_to_city` es otra pieza con otro radio de daño —mueve el
expediente entero— y tiene su propia entrada abierta (`#155`); tocarla de paso sería remediar
fuera del alcance revisado.

**Disparador de promoción.** La primera reasignación de ciudad sobre un caso con edición manual
del frontmatter, o el cierre de `#155`.

## 168. `email_export.export_label` con un destino EXTERNO llamado como lote registra en el M9 del caso una ruta que no existe  `[RESUELTO 2026-09-06 — y la frontera era más ancha de lo reportado]`

> Medido por Codex en la **R2 de `MEJORAS #149`** (2026-09-05), fuera del alcance de ese diseño y
> **preexistente**: con `case_id` y un `dest` que no está bajo el `00_Input/` del caso pero cuyo
> nombre casa `PATRON_LOTE`, `export_label` escribe el manifiesto en ese destino externo y
> registra `<lote>/doc.eml` en el `_intake_hashes.json` **del caso**, aunque esa ruta no existe en
> su `00_Input/`; `report.errors == []`. El docstring exige que el destino esté bajo el Input del
> caso pero **no lo valida**, y la traza usa `dest.parent` como raíz (`email_export.py:1247`).

**La frontera:** un `dest` es «lote de este caso» si está **físicamente** bajo el `00_Input/` del
caso resuelto, no si su nombre lo parece. Es la misma familia que `#149` (el nombre no es la
ubicación) trasladada al escritor.

**Remedio:** validar por resultado en `export_label` —`dest.resolve()` bajo `caso_path(case_id) /
"00_Input"`— y, si no, o bien no registrar en el M9 del caso (uso suelto) o bien fallar cerrado
nombrando las dos rutas. Su mutante: destino externo `…/2026-09-05_email_01` con `case_id` → hoy
entra en el M9; con el remedio, no.

> **✅ RESUELTO el 2026-09-06** (acción 6a, arrastrado por vecindad de código), **y la frontera
> resultó ser más ancha que el defecto reportado.** Aquí estaba descrito el destino *totalmente
> externo*; la **R1 de Codex (H-02)** demostró que cerrarlo no cerraba la clase: `_emit_traza`
> calcula las rutas del manifiesto contra `dest.parent`, así que un lote **anidado** bajo
> `00_Input/subcarpeta/` pasaba el guard nuevo y registraba rutas igual de inexistentes; y una
> junction externa con nombre de lote apuntando dentro registraba el nombre lógico.
>
> La propiedad real, en `core/email_export._es_lote_del_caso`: **un lote es un hijo DIRECTO del
> `00_Input` del caso cuyo nombre lógico es su ubicación física**. Resolver para validar y volver al
> nombre lógico para registrar no basta. Séptima aparición documentada de *remediar el ejemplo en
> vez de la frontera*.
>
> Adjudicación: §6 del plan
> [`2026-09-06-accion-6a-filtro-de-ruido-email-export.md`](superpowers/plans/2026-09-06-accion-6a-filtro-de-ruido-email-export.md).
> Mutantes `M08`, `M09`, `M14` y `M15` en `tests/_mutantes_accion_6a.py` — el `M15` (alias
> entrante) **declarado SIN COBERTURA**, porque montar una junction en un test exige privilegios
> que el CI no tiene.

## 169. El centinela `0000-00-00` se ordena y filtra como «un día muy antiguo» en las vistas de correo y en el motor deprecado de la sala

> Medido por Codex en la **R1 de `MEJORAS #131`** (2026-09-05), preexistente y fuera del alcance de
> esa pieza (que solo tocó la skill). Dos sitios, la misma familia: **el valor que significa
> «no sé la fecha» se compara lexicográficamente como si fuera una fecha**.
>
> - `core/email_atomize/vistas.py:53,87-94` (`_seleccion_tematica`): con `hasta='2025-01-02'` un
>   mensaje con `fecha_iso='0000-00-00'` **entra** en el rango; con `desde='2024-01-01'` **sale**.
>   Una fecha desconocida no demuestra pertenencia a «antes de» ni exclusión por «después de»;
>   hace falta una política explícita de desconocidos. Y `render.py:120` y
>   `email_export.py:1356,1417` lo ordenan primero, como el mensaje más antiguo del hilo.
> - `core/sala_lectura.py:673-692` (motor **deprecado** por la skill): `render_indices` ordena
>   `0000-00-00` y `2024-03 (*)` por delante de `2025-01-01` y pierde la marca `(*)` — el
>   criterio solo pregunta `fecha_doc is None`. También `core/whatsapp_atomize/corpus.py:37` y
>   `render.py:80`, por inspección estática.

**La frontera:** «desconocido» no es un valor del eje temporal. Ordenar: los desconocidos van
**al final** (como ya hace `indices_desde_manifiesto`); filtrar por rango: los desconocidos se
**declaran** (se listan aparte), ni entran ni salen en silencio. `tiene_fecha` de la skill es la
pregunta correcta; los motores de `core/` no la tienen.

**Remedio:** una función de comparación única para fechas ISO con centinela (`clave_orden_fecha`)
en `core/` y una política de rango en `vistas._seleccion_tematica` con un tercer cubo
`sin_fecha`. El motor deprecado no se toca: se anota.

**Disparador de promoción.** Un caso real en que la vista temática de correo omita o incluya un
mensaje sin `Date` en un rango, o que el orden del hilo ponga primero el mensaje sin fecha y eso
confunda una lectura. Hoy no consta.

## 170. Un export a destino EXTERNO marca igualmente el `gmail_id` en el índice del caso

> Medido por Codex en la **R1 de la acción 6a** (2026-09-06), **preexistente** y declarado por él
> como no-regresión de ese diff. Va aquí para que no se pierda.

**Qué pasa.** `export_label` con `case_id` y un `dest` fuera del `00_Input` del caso ya no registra
en el manifiesto (`MEJORAS #168`), pero **sí** escribe el `gmail_id` en el `_exported_ids.json`
**del canal del caso**. Consecuencia: una corrida posterior al lote interno legítimo **salta** ese
mensaje por idempotencia de canal, escribe 0 ficheros y elimina el lote vacío. El correo acaba fuera
del expediente y el sistema cree haberlo exportado.

**La frontera:** el índice de canal responde «¿ya bajé esto *para este caso*?», y hoy responde que
sí cuando los bytes se fueron a otro sitio. El aviso de `#168` no lo remedia — solo dice que no se
trazó.

**Remedio candidato:** no tocar el índice del caso cuando el destino no es un lote suyo, o llevar el
índice al lote y no al caso. Su mutante: exportar a externo y después al lote interno; hoy la
segunda corrida escribe 0.

**Disparador de promoción.** Un caso real en que alguien exporte a un directorio suelto con
`--ref` y luego repita al expediente. Hoy ningún llamador ordinario lo hace: `export_label_emails`
deriva `dest` del caso.

## 171. `test_case_mutex::test_RENUEVA_mientras_el_cuerpo_corre` es intermitente bajo `-n auto`

> ✅ **CERRADA el 2026-09-07 (PR [#302](https://github.com/TyukhayNi/FeesDefender/pull/302),
> `3420d4d`).** El disparador se consumió: volvió a salir al día siguiente, en la suite de la rama
> del PR #301, y una segunda vez deja de ser anécdota. El remedio es el que esta entrada proponía
> —medir la renovación **por evento observado** y no por tiempo transcurrido—, y no la otra salida
> que ofrecía: nada se marcó `serial` ni se subió ningún umbral.
>
> **Pero su diagnóstico era falso, y conviene que quede escrito.** Esta entrada decía que «con 12
> workers compitiendo por CPU y por E/S, la ventana de renovación puede pasarse sin que haya
> defecto en el código». **Medido el 2026-09-07** con 24 procesos ocupados sobre 4 CPUs (6x de
> sobresuscripción), 8 corridas instrumentadas: el primer latido llega a **1,00-1,03 s** de su
> periodo de 1 s —nunca tarde— y el presupuesto del bucle de espera **crece** con la carga (3,05 s
> en reposo, 3,77-4,09 s saturado). Bajo carga el margen **mejora**. El test aislado bajo esa misma
> carga, 12/12 verdes.
>
> **La causa verdadera estaba escrita en este mismo fichero desde el 2026-09-03: `MEJORAS #145`.**
> El bucle de espera abría el `.lock` unas cincuenta veces por segundo, justo el fichero que el
> renovador reemplaza con `os.replace`; en Windows esas dos operaciones chocan, el escritor muere y
> `tomado` lo lee como pérdida de titularidad. **El test fabricaba la carrera que denunciaba.** Dos
> entradas de este backlog describían el mismo rojo con causas incompatibles y nadie las cruzó.
>
> Lo construido: la propiedad se reparte en dos —el mecanismo por evento, la **puntualidad** contra
> la constante de producción y sin reloj—, `tests/_espera_mutex.py` deriva el presupuesto del
> periodo de latido, y seis mutantes mueren cada uno por su frontera
> (`python -m tests._mutantes_renovacion_mutex`). La mitad de **producción** de `#145` sigue
> abierta con su precio de dos rondas.

> Medido el 2026-09-06 durante el cierre de la acción 6a: rojo con la semilla 777 en una corrida y
> **verde al repetir la MISMA semilla**, verde con 31337 y verde 5/5 aislado. No lo causa el diff de
> esa sesión, que no toca `core/case_mutex.py` ni nada de lo que dependa.

**Qué pasa.** El test verifica que el gestor **renueva** el lease mientras el cuerpo corre, y eso lo
mide contra el reloj. Con 12 workers de `pytest-xdist` compitiendo por CPU y por E/S, la ventana de
renovación puede pasarse sin que haya defecto en el código.

**Por qué importa aunque sea «solo un flaky».** La regla de aceptación de esta casa son **dos
semillas verdes**, y un test que falla por carga y no por orden hace que esa regla dé un rojo que no
significa nada. Un rojo que no significa nada es, a la larga, un rojo que se ignora — y entonces la
verja deja de serlo.

**Remedio candidato:** que el test mida la renovación por **evento observado** (contar renovaciones
efectivas) en vez de por tiempo transcurrido, o marcarlo `serial` con su porqué escrito. Lo segundo
es más barato y más honesto que subir el umbral hasta que deje de fallar.

**Disparador de promoción.** Que vuelva a salir en un cierre. Si aparece una segunda vez, deja de
ser anécdota.

---

## 172. El guard de los wrappers MCP no mira el artefacto que se ejecuta `[RESUELTO 2026-09-07]`

> ✅ **Resuelto el 2026-09-07.** `tests/test_plugin_desplegado.py` compara lo INSTALADO contra un
> commit canónico (`origin/main`, fijado a un SHA), fichero a fichero **y en las dos direcciones**,
> por versión en **tres sitios** (registro, manifiesto instalado y canónico) y cubriendo también los
> **metadatos de arranque** (`.mcp.json`, `.claude-plugin/plugin.json`), en **todas** las entradas
> del registro. Con `skip` explicado donde el plugin no está instalado.
>
> En su primera corrida encontró un segundo desfase que nadie sabía: `tiers.py` desplegado sin
> `_apertura_v1.json` ni los temporales de escritura atómica en `PROTOCOL_EDIT` (`MEJORAS #149`,
> `#146`). Y al arreglarlo salió que **`claude plugin update` compara por VERSIÓN, no por
> contenido**: con la versión igual dice «already at the latest version» y no copia nada, así que un
> redespliegue puede parecer hecho sin estarlo. **Ojo al alcance, que la R1 corrigió:** eso explica
> un desfase *dentro* de una misma versión, no el salto 0.4.0 → 0.4.1, donde las versiones sí
> diferían y `update` habría copiado. De ese otro solo está acreditado el `lastUpdated 2026-07-20`
> del registro — que nadie ejecutó la actualización—; su duración y la continuidad de la avería son
> inferencia, no medición. Procedimiento corregido en `plugin-src/README.md`.
>
> **La primera versión de este guard no valía, y lo dijo la R1 adversarial** (`REQUIERE-REVISION`,
> 8 hallazgos, 8 confirmados): omitía `.mcp.json` —vaciarlo a `{}` pasaba en verde con el
> manifiesto ya sin declarar ningún MCP (H-01)—, auditaba solo la primera entrada del registro
> (H-02) y elegía la primera referencia que resolviera, con lo que una `main` local rancia ocultaba
> lo que ya estaba en `origin/main` (H-03). Arnés final: **7/7 muertos** —fichero alterado, ausente
> y sobrante, versión del registro, `.mcp.json` vaciado, `plugin.json` vaciado y segunda
> instalación rota en segundo lugar—, con restauración verificada por hash.
>
> **Sigue SIN VERIFICAR, y se declara:** que Claude Code elija de verdad la instalación que el
> guard audita cuando hay varias, y la frescura de `origin/main` respecto al remoto sin `fetch`.

> Medido el 2026-09-07: `feesdefender@despacho-tyukhay` llevaba instalado en **0.4.0 desde el
> 2026-07-20**. La reparación del 2026-08-31 (PR #253) estaba en `dist/plugin` como 0.4.1 y **nunca
> se instaló**: durante cinco semanas Claude Code arrancó los wrappers de junio y julio mientras la
> suite daba verde sobre los de agosto.

**Qué pasa.** `tests/test_mcp_wrappers.py` recorre `ROOT/plugins/*/run_server.bat` — la SSOT. Lo que
arranca Claude Code vive en `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. Son
ficheros distintos, y el 2026-09-07 la distancia era ésta: el `email_export_mcp` desplegado tenía
**136 bytes** (2 líneas, del 23-06) contra los 4.178 de la SSOT, y el `expedientes_xl` **2.634**
(del 19-07) contra 5.047.

**Qué rompía de verdad, separando lo medido de lo heredado.** De `email-export` (caído con
`CONNECTION_CLOSED`) hay **una causa medida**: el wrapper de junio lanza `%~dp0server.py` sin
`--repo-root` y **el bundle no lleva `core/`** (comprobado: `0.4.0/` solo contiene
`email_export_mcp`, `expedientes_xl` y `skills`), así que el server muere importando
`core.email_export` antes de contestar `initialize`. Lo que **NO** es causa: el intérprete cableado
—existe y tiene `mcp 1.29.1`, o sea que el pin `<2` aguanta y la avería de agosto por `mcp 2.0` no
es ésta—.

**Y una regla de oro que hoy no se reprodujo.** El wrapper de `expedientes_xl` 0.4.0 **también**
lleva `2>>"%LOG%"` en su línea de lanzamiento, y el 2026-09-07 **conectó y sirvió tools** en Claude
Code 2.1.231 (`list_dir` devolvió el contenido de la unidad) antes de actualizar el plugin. Eso no
refuta el experimento del 2026-08-31 —dos `.bat` idénticos salvo el `2>>`, el que redirigía daba
`CONNECTION_CLOSED`—, pero sí dice que la regla **no explica por sí sola** lo que se ve hoy, y que
atribuirle la caída de `email-export` sería atribuir sin medir. **Antes de que nadie use el `2>>`
como explicación de nada, hay que volver a medirlo** contra la versión actual del cliente. Seguir
respetando la regla mientras tanto no cuesta nada; apoyarse en ella, sí.

**Por qué importa.** El guard se escribió el 2026-08-31 exactamente para que los conectores no se
apagaran otra vez en silencio, y **no puede ver el artefacto que se apaga**. Aunque hubiera estado
verde del todo no habría cazado nada: el fallo no está en la fuente, está en el paso de despliegue,
y ese paso no lo vigila nadie. Es la forma «tres copias» de un defecto que esta casa ya conoce —
SSOT ✅, build ✅, instalado ❌— y la única de las tres que le importa al usuario es la última.

**Remedio candidato.** Un guard que compare **lo instalado** contra la SSOT: leer
`~/.claude/plugins/installed_plugins.json`, localizar el `installPath` de
`feesdefender@despacho-tyukhay` y exigir que sus `run_server.bat` coincidan con
`plugins/*/run_server.bat` módulo fin de línea. Con `skip` **ruidoso y explicado** si el plugin no
está instalado en esa máquina: un `skip` mudo aquí reproduce el problema en vez de cerrarlo. Y
cuidado al elegir la aserción — la propiedad no es «los bytes coinciden» sino «lo que corre es lo
que revisé», así que la versión instalada forma parte de lo que hay que afirmar.

**Disparador de promoción.** La próxima vez que un conector caiga sin que la suite se entere. Mejor
aún, antes: cada despliegue del plugin es una ocasión nueva de desincronizarse.

---

## 173. El veredicto del guard de wrappers depende de si Google Drive está montado `[RESUELTO 2026-09-07]`

> ✅ **Resuelto el 2026-09-07.** El gate de montaje de `plugins/expedientes_xl/run_server.bat` gana
> una costura (`FEESDEFENDER_PROBE_G`/`_H`/`_MAXTRIES`, defaults de producción intactos) y el guard
> de comportamiento la fija abierta, así que deja de depender de Drive. La comprobación de que la
> costura es de carga es un **experimento diferencial** de tres corridas idénticas salvo una sonda:
> ninguna corrida suelta prueba nada —en una máquina con los drives montados un override ignorado se
> ve igual que uno respetado—, pero la diferencia sí. Eso lo levantó el arnés, no el diseño: la
> primera versión apuntaba las dos sondas a la vez y **sobrevivía** a borrar el override de
> `PROBE_G`, porque el gate es un AND y bastaba con `PROBE_H`.
>
> **Con qué alcance, que la R1 acotó (H-08):** el diferencial prueba la propiedad con el montaje
> **estable** durante las tres corridas. No prueba independencia del montaje *en general* —las tres
> ocurren en instantes distintos, y un montaje que apareciera y desapareciera entre ellas podría dar
> verde con una sonda ignorada; el revisor lo reprodujo en simulación—. La garantía que no depende
> de ningún montaje es el guard de los defaults, que no ejecuta nada.
>
> **La R1 encontró además tres defectos reales en la primera versión:** el guard de defaults solo
> comprobaba las subcadenas `G:` y `H:`, así que un default movido a `G:\nonexistent` pasaba (H-04);
> el contador de esperas contaba la subcadena `ping` y un `--basetemp=shipping` daba falso rojo,
> mientras `<=1` dejaba vivo el mutante `tope+1` (H-05); una ruta con `!` se deformaba por la
> expansión retardada (H-06); y `set /a` sobre el entorno **ejecutaba** el valor — con
> `1 & echo X` el wrapper escribía en **stdout**, que es el pipe JSON-RPC (H-07). Arnés final:
> **9/9 muertos**, incluidos los dos que sobrevivieron a la R1.

> Medido el 2026-09-07 en las dos direcciones, el mismo día y sin tocar una línea de código: con
> G:/H: caídos, `tests/test_mcp_wrappers.py` da **1 rojo**; con los drives montados, **23/23
> verdes**.

**Qué pasa.** `test_sin_interprete_capaz_el_wrapper_FALLA_RUIDOSAMENTE` envenena la resolución del
intérprete y exige que el wrapper muera nombrando `FEESDEFENDER_PYTHON` o `FEESDEFENDER_ROOT`. Pero
`plugins/expedientes_xl/run_server.bat` tiene **una puerta anterior** que el test no controla: el
`poll-until-mount` de G: y H:. Sin montaje el wrapper muere ahí, con «abre Google Drive y reinicia»
—accionable, pero fuera de la lista blanca de dos cadenas—. Y como el test vacía el `PATH`,
desaparece `ping`: la espera de ~50 s se convierte en 25 vueltas instantáneas y el stderr se llena
de «"ping" no se reconoce».

**Por qué importa.** No es solo un rojo molesto. **El verde tampoco significa lo mismo según el
día**: con Drive abajo el test no prueba nada sobre la resolución del intérprete, que es justo lo
que dice medir. Un instrumento cuyo valor depende de una variable que no controla no está midiendo
la propiedad, está midiendo el ambiente.

**Remedio candidato — y cuál NO.** El arreglo fácil es añadir la tercera cadena a la lista blanca.
**Eso sería arreglar el ejemplo por tercera vez**: el propio docstring del test cuenta que la
primera versión exigía UNA palanca y la ampliaron a DOS cuando `email-export` la puso roja por morir
antes. La frontera es que **el test controle toda precondición capaz de desviar al wrapper de la
propiedad que mide**: dar al gate del montaje una costura de prueba —que `PROBE_G`/`PROBE_H` admitan
override por entorno, con el valor de producción como default— y que el test la fije.

**Disparador de promoción.** Que el rojo reaparezca en un cierre, o que se toque
`run_server.bat` por cualquier otro motivo.

---

## 174. El `display_name` del `.dxt` de expedientes-xl lleva `/` y `:`

> Observado el 2026-09-07: Claude Desktop mostró
> `MCP expedientes-xl (Drive como disco G:/H:): path escape: "expedientes-xl (Drive como disco G:/H:)"`.

**Qué se sabe, y qué no.** Medido: el texto entrecomillado en el error coincide **literalmente** con
el `display_name` de `plugins/expedientes_xl/dxt-build/manifest.json` —`expedientes-xl (Drive como
disco G:/H:)`—, y ese nombre contiene `/` y `:`. Medido también: la cadena «path escape» **no sale
de nuestro código** (grep en todo el repo: cero coincidencias), así que la emite el cliente. **NO
medido:** que el cliente esté tratando ese nombre como ruta y que su propio validador lo rechace por
eso. No tengo su código; es inferencia, y como inferencia queda anotada.

**Remedio candidato.** Renombrar el `display_name` a algo sin `/` ni `:` —«expedientes-xl (Drive
como disco local)»— y reconstruir/reinstalar el `.dxt`. Es barato y falsable, pero **hay que hacerlo
como experimento, no como arreglo**: si se cambia el nombre a la vez que se reconstruye y se
reinstala, que el aviso desaparezca apoya la hipótesis y no identifica la causa, porque han cambiado
tres cosas. Cambiar **solo** el nombre, bajo procedimiento controlado, es lo que la distingue. Lo
señaló la R1 adversarial de `#172`/`#173`.

**Disparador de promoción.** Va junto a `MEJORAS #125` (los tres manifiestos `.dxt` cablean un
intérprete). Ninguna de las dos merece por sí sola una reinstalación manual de tres extensiones;
juntas sí, la próxima vez que haya que reconstruir cualquiera de los `.dxt`.

---

## 175. La regla de oro del `2>>` no se reprodujo, y hasta volver a medirla no explica nada

> Observado el 2026-09-07 al diagnosticar la caída de los dos conectores MCP.

**Qué dice la regla.** Desde el 2026-08-31, la cabecera de los wrappers y `test_mcp_wrappers.py`
sostienen que **redirigir en la línea que lanza el server** (`... 2>>"%LOG%"`) da
`CONNECTION_CLOSED` en Claude Code: el server muere en `stdout.flush()` con `OSError 22` sin haber
recibido `initialize`. El experimento que la respalda fue **controlado**: dos `.bat` idénticos
salvo el `2>>`.

**Qué se midió el 2026-09-07.** El wrapper **0.4.0** de `expedientes_xl` —el que estaba realmente
desplegado— lleva `2>>"%LOG%"` en su línea de lanzamiento (línea 47) y ese día **conectó y sirvió
tools** en Claude Code 2.1.231: `list_dir` devolvió el contenido de la unidad. La conexión se
verificó por resultado, no por que el conector apareciera en la lista.

**Qué NO significa eso.** No refuta el experimento de agosto, que fue controlado y este no lo es
(no se repitieron los dos `.bat` idénticos contra el cliente actual). Lo que significa es que la
regla **ya no explica lo que se ve**, y por tanto **no puede usarse como explicación de una caída**
hasta remedirla. En concreto, atribuirle la caída de `email-export` habría sido atribuir sin medir:
su causa medida es otra —lanza `%~dp0server.py` **sin `--repo-root`** y el bundle **no lleva
`core/`**, así que muere importando `core.email_export` antes de contestar `initialize`—.

**Qué hacer.** Repetir el experimento de control contra la versión actual del cliente: dos
wrappers idénticos salvo el `2>>`, arrancados por Claude Code, y ver cuál conecta. Según salga:
confirmar la regla, acotarla a versiones del cliente, o retirarla.

**Mientras tanto, seguir respetándola.** No cuesta nada —el stderr del server lo recoge el
cliente— y el coste de equivocarse en el otro sentido es un conector muerto en silencio. Lo que no
vale es **apoyarse** en ella para explicar nada.

**Disparador de promoción.** Que vuelva a caer un conector con `CONNECTION_CLOSED`, o que haya que
tocar la línea de lanzamiento de cualquier wrapper por otro motivo.

---

## 176. F3 verifica el relate por el lado del correo, que es una vista por copia

> Medido el 2026-09-07 con escrituras contra los expedientes de prueba 636 y 683.

`core/procurador_relate.py` verifica el relate **releyendo `findRelations(uid, account)`**
(§4 del spec de F3). Esa lectura devuelve las relaciones de **esa copia** del correo, y un mismo
Message-ID tiene **N filas `mail`, una por cuenta** (tres copias medidas: ctas 11, 13, 15). La
relación que el relate escribe es **global**.

Resultado medido: relacionada la copia de la cuenta 15 con `expedientes_judiciales:683`,
relacionar la copia de la cuenta 2 con el **mismo** miembro devolvió `ok=False` y
*«el CRM respondió 200 pero la relectura no lo verifica; ¿existe el miembro?»* — con la relación
escrita y el miembro existiendo. El expediente no se movió de dos correos y el `mail_id` fue el
mismo (439232) desde las dos cuentas.

**Arreglo:** verificar por `GET /api/related_register/{elemento}/{id}` → bloque `mail`, que ya
está cableado en `core.sudespacho_relations.get_relaciones` (`INTEGRACION_SUDESPACHO §15.5`).

**Disparador de promoción.** Cablear `archivar()` a la bandeja (F3 en producción): mientras nadie
lo llame, el falso negativo no daña a nadie.

---

## 177. Dos mensajes de error de F3 apuntan a la causa equivocada

> Mismo barrido del 2026-09-07 que `#176`.

1. **`resolver_cuenta()` → `None`** cubre dos estados distintos: «no hay fila `mail`» y «hay más
   de una cuenta». Su motivo dice *«¿no indexado todavía?»*, y en el segundo caso el correo está
   indexado **tres veces**. El mensaje manda al operador a esperar un paso del webmail que no
   arregla nada.
2. **El error del relate** dice *«¿existe el miembro?»* cuando lo que pasa es que la relectura es
   por copia (`#176`). Un reintento guiado por ese diagnóstico no converge nunca.

Los dos fallan **cerrado** (van a revisión), así que no corrompen nada: el defecto es el
diagnóstico, y el coste es tiempo humano buscando en el sitio equivocado.

**Disparador de promoción.** El mismo que `#176`, o la primera vez que alguien pierda un rato con
uno de los dos mensajes.

---

## 178. La guarda anti-duplicado del adjuntar filtra por NOMBRE, y el CRM sí duplica

> Medido el 2026-09-07 sobre `extrajudiciales/636`: censo 3 → 4 → 5.

`relate/attachments` **no es idempotente**. El mismo `att_id`, el mismo nombre final y el mismo
`mail_id`, posteados dos veces, dejan **dos documentos**; los dos POST contestaron
`{"status":"success","errors":[]}`.

Eso convierte la guarda por censo de `adjuntar` (`pendientes = [… if n not in antes]`) en
**portante**: sin ella se duplica un documento en el expediente de un cliente. Y deja su hueco a
la vista — **filtra por nombre final**, así que si F4 propone dos nombres distintos para el mismo
adjunto (o alguien renombra), el mismo documento entra dos veces.

**Arreglo:** filtrar además por `att_id` ya subido, no solo por nombre. Requiere que el censo
del gestor documental exponga la procedencia del documento, que está sin comprobar.

**Disparador de promoción.** Que F4 entre en juego (es quien compone `nombre_final`), o el primer
duplicado observado en un expediente real.

---

## 179. Las relaciones que hace Ana son un set de evaluación gratis para el matcher de F1

> Observado el 2026-09-07 al medir qué correos de `procesal@` están en el CRM.

De 32 correos de `procesal@` de cuatro días, **23 estaban relacionados con su
`expedientes_judiciales`**, cada uno con el miembro que **Ana eligió a mano** (`id_creador=23` en
las 23 filas). Eso es verdad de campo etiquetada por la persona cuyo criterio es el patrón, y se
renueva cada día.

F1 se validó en junio contra 20 correos con un dataset construido a mano
(`scripts/eval_matcher_batch.py`). Aquí hay un arnés que no cuesta montar: correr el matcher sobre
los correos **ya relacionados**, comparar su propuesta con el expediente que Ana eligió, y sacar
acierto por lote. Mide si el robot acierta **antes** de darle la escritura.

**Cuidado con el sesgo:** solo cubre los correos que Ana **sí** archivó. Los que deja pendientes
—9 de 32 en la muestra, incluido uno en SPAM— no tienen etiqueta, y son justo los raros.

**Disparador de promoción.** Antes de dejar que F3 escriba en el CRM sin confirmación humana por
ítem. Mientras la bandeja pida visto bueno, el arnés es deseable y no urgente.

---

## 180. En un worktree, TODO script que use credenciales falla, y no dice por qué

> Medido el 2026-09-07 y el 2026-09-08, al promover los sondeos del módulo de correo.

`core/config.py` hace `load_dotenv(_PROJECT_ROOT / ".env")` sobre la raíz del árbol en el que
corre. **Un worktree no tiene `.env`** —está gitignored, y lo gitignored no viaja—, así que
cualquier script que necesite `SUDESPACHO_API_KEY` u otra credencial arranca sin ella y muere con
un error de red o de autenticación que **no menciona el `.env`**. Es el mismo mecanismo que dejó
inerte la blocklist del `leak-guard` (`#161`), aplicado a las credenciales.

Ayer costó pasar la ruta absoluta a mano en cada sondeo; `scripts/diag_expediente_648.py` tiene el
mismo defecto latente, y por definición lo tiene **cualquier** script del repo que dependa de
`core.config` para las credenciales.

**Lo remediado (el ejemplo):** `scripts/_sondeo_crm.resolver_env` busca el `.env` en este árbol y,
si no está, en el checkout principal (`git worktree list`), y **devuelve de dónde cargó** — un
cargador que no lo dice no distingue «no había» de «no pude mirar». Sus dos sondeos lo imprimen y
abortan con un mensaje claro si no hay `.env`.

**Lo NO remediado (la frontera):** el sumidero es `core/config.py`, por donde pasan todos. Mientras
la carga viva ahí sin fallback, cada script nuevo hereda el defecto y hay que acordarse.

**Por qué no se arregla ya:** tocar `core/config.py` cambia el arranque de **todo** el repo
—`streamlit_app`, los pipelines, los tests— y merece su propio diseño y su ronda. No es un cambio
de una línea disfrazado de trivial.

**Disparador de promoción.** El próximo script que necesite credenciales y vaya a correr en un
worktree, o la próxima vez que alguien pierda tiempo con un error de autenticación que resulte ser
esto.

---

## 181. Bajar los adjuntos de un correo no existe en el código, y es prerequisito de tres cosas

> Medido el 2026-09-08, al intentar medir el OCR sobre adjuntos reales.

`core/gmail_source.py` **no menciona adjuntos**: baja cabeceras y cuerpo y nada más. La API de Gmail
exige una llamada aparte (`users.messages.attachments.get`) que **nadie hace**.

Y hay una ruta declarada de punta a punta que por eso llega siempre vacía:
`EmailMessage.attachment_texts` existe (`core/procurador_runner.py:44`),
`procurador_runner.py:84` se lo pasa a `extract_signals`, `procurador_intake.py:291` lo consume…
y **ningún productor lo rellena**. Es la tercera pieza construida sin encadenar de esta semana.

**Bloquea tres cosas distintas**, y conviene no confundirlas:

1. **F4** (renombrado por contenido): `propose_attachment_name` —que existe en
   `core/procurador_intake.py:533`, también sin llamador— pide `attachment_text`, y sin bytes no hay
   texto.
2. **El OCR de los adjuntos**, local o de cualquier otro tipo.
3. **Cualquier decisión sobre mandarlos a un tercero**: no se puede mandar lo que no se baja. La
   medición de `MEJORAS #90` del 2026-09-08 hubo que hacerla con un script del scratchpad.

**Cuidado al construirlo, porque son bytes de cliente:** los adjuntos no se depositan en el árbol
del repo, y el destino natural es el `00_Input` del expediente por la vía de intake que ya existe
—con su evento y su `sha256`— o un temporal fuera del repo si es solo para extraer texto. Uno de los
10 adjuntos de la medición pesaba **13,5 MB**, así que el tope y el streaming no son teóricos.

**Disparador de promoción.** Cuando se aborde F4, o el primer intento de OCR-izar adjuntos desde el
flujo real en vez de a mano.

---

## 182. El CRM guarda 541 renombrados hechos a mano: el set de evaluación de F4 ya existe

> Medido el 2026-09-08, censando 4.000 documentos de `gdocu` para decidir la D3 del cableado de F3.

El elemento `gdocu` guarda **`nombreoriginal` Y `nombrefinal`**. De 4.000 documentos, **541 tienen
un `nombreoriginal` de máquina** (`LXN…`, `Env_…`, `AcuseMensajeLexnet…`) **y un `nombrefinal`
compuesto por una persona**. Eso es exactamente la tarea de F4 —proponer el nombre de un adjunto—
**ya resuelta 541 veces, con la respuesta guardada al lado del enunciado**.

Es el hermano de `MEJORAS #179` (las relaciones de la secretaria como set de evaluación del matcher
de F1), para la otra mitad del trabajo.

**Cómo se usa:** correr el propuesto de F4 sobre los 541 `nombreoriginal` y comparar con su
`nombrefinal`. Con el añadido de que el adjunto **también está** en el gestor documental, así que se
le puede dar el contenido real y no solo el nombre.

**Dos cautelas medidas, y la segunda decide el criterio de acierto:**

1. **62 % de los documentos NO se renombran** porque llegaron ya con nombre descriptivo. El set son
   los 541, no los 4.000: F4 no debe aprender «renombra siempre».
2. **La convención es inconsistente.** `JUSTIF PROCU` (100) y `JUST PROCU` (87) designan lo mismo;
   el probatorio se escribe `D NN` (85 + ~22×7) y `DOC NN` (~23×10). Así que **la métrica no puede
   ser la igualdad literal** — sería injusta con una propuesta correcta escrita con la otra
   variante. Lo que tiene sentido medir es el **prefijo de tipo** acertado, y dejar la descripción a
   corrección humana.

**Y el catálogo de prefijos, censado y no inventado:** `DIOR` 305 · `JUSTIF PROCU` 100 ·
`JUST PROCU` 87 · `D XX` 85 · `PROCU` 65 · `ESCR PROCU` 63 · `ESCR CRIO` 55 · `DECR` 52 ·
`AUTO` 51 · `FRA PROCU` 50 · `PROV` 25. El campo `categoria` viene **vacío**: el tipo vive en el
nombre, no en un enum.

**Disparador de promoción.** Cuando se aborde F4. Antes no: sin el propuesto no hay nada que
evaluar.

---

## 183. En un worktree el intake de procuradores descarta TODOS los correos, en silencio

> Medido el 2026-09-09, al escribir los tests de la rebanada 1 del cableado de F3.

`core.procurador_intake.cargar_procuradores_conocidos` lee `data/_config/procuradores_conocidos.yaml`
—**gitignored**— y su docstring lo dice: *«Ausente o ilegible → (set(), set())»*.

**Medido en este worktree: 0 dominios, 0 emails.** La raíz principal sí tiene el YAML; el worktree
solo tiene el `.example`, que **no se lee**. Consecuencia: `is_procurador_email()` devuelve `False`
para todo, y `procurador_runner.process_email` descarta **cada** correo con
`motivo="remitente_no_procurador"`.

**Por qué es peor que el caso hermano de la blocklist (`#161`):** allí el vacío producía un **verde
falso** en un guard. Aquí produce un **descarte falso con un motivo que parece una clasificación
legítima** — «este remitente no es un procurador» se lee como una decisión, no como «no tenía
catálogo con el que decidir». Nadie audita un descarte razonado.

**Es la misma frontera que `#180`** (el `.env` que no viaja a los worktrees): un artefacto
gitignored del que depende el comportamiento, y cuyo estado vacío es indistinguible de una
respuesta.

**Remedio, dos piezas y la primera es la que importa:**

1. **Que el vacío se OIGA.** Igual que el `leak-guard` cuenta sus términos: exponer cuántas entradas
   cargó y de dónde, y que `run_intake` lo diga al arrancar. Un contador es lo que separa «miré y no
   es procurador» de «no tenía con qué mirar».
2. **Buscar también en el checkout principal**, como hace `scripts/_sondeo_crm.resolver_env` con el
   `.env` (`git worktree list`). Cuesta poco y quita la asimetría worktree/raíz.

**Lo que NO se hace:** leer el `.example` como respaldo. Un catálogo de ejemplo respondiendo
preguntas de producción es peor que no tener catálogo.

**Disparador de promoción.** La primera vez que alguien corra el intake desde un worktree y lea
«remitente_no_procurador» como un hecho, o cuando se cablee `archivar_confirmado` (rebanada 2),
porque entonces el silencio afecta a una escritura.

---

## 184. Los dos sondeos del módulo de correo están al 0 % de cobertura

> Medido por `session_close` el 2026-09-09, al cerrar la sesión que los promovió.

`scripts/sondeo_copias_mail.py` y `scripts/sondeo_join_gmail_crm.py` tienen **0 % de líneas
cubiertas**. Su helper compartido `scripts/_sondeo_crm.py` está al **100 %** con 10 mutantes
muertos, pero los cuerpos de los sondeos —`censo()`, `detalle()`, `main()`— no los ejecuta ningún
test.

**Por qué importa más de lo que parece:** son las herramientas que **reproducen las mediciones que
acaban citadas en los specs**. Un sondeo roto no da un error: da **un número**, y ese número entra
en un documento. Toda esta sesión giró alrededor de instrumentos que no podían dar el otro valor.

**Es abordable, y por eso es deuda y no limitación:** `censo(t, …)` y `detalle(t, …)` **reciben el
transporte**, así que se prueban con el `FakeTransport` que ya existe en
`tests/test_procurador_relate.py`. Lo que merece test:

- `censo`: que la distribución salga de las páginas que devuelve el fake; que **pare** cuando una
  página da HTTP != 200; que el mensaje del control diga «no acredita nada» con cero multicopia y
  «SÍ, mide» con al menos uno.
- `detalle`: que un censo ilegible (`filas_mail_por_uid` → `None`) se reporte como
  **indeterminado** y no como «no hay filas».
- `main`: que sin `.env` aborte con código 2 en vez de dar un error de red confuso.

**Lo que NO hace falta:** cubrir la paginación real ni la red. El valor está en las ramas de
decisión, que son puras.

**Disparador de promoción.** La próxima vez que se cite una cifra de estos sondeos en un spec o en
la bitácora, o antes de que alguien que no sea su autor los use para decidir algo.

## 185. El atlas del CRM mide su cobertura contra `/api/elements`, que oculta 28 elementos

**Medido el 2026-09-08.** `GET /api/elements` devuelve **89 elementos**, y `poderes` **no está entre
ellos** — pese a que el elemento responde con normalidad a `element_registries`, `element_register`,
`view/config/{element}/fields`, `view/config/{element}/relations`, `view/enums/*` y
`related_register`, y a que el fichero tiene 85 registros vivos en el tenant.

`core/crm_atlas.fetch_elements` construye la lista de la Fase B llamando a `/api/elements`
(`crm_atlas.py`, la llamada a `/api/elements` dentro de `fetch_elements`). Por tanto:

- el atlas **no tiene ni tendrá** ficha de `poderes` por regenerarlo;
- su cabecera dice **«Fase B (esquema por elemento) ⚠️ 87/89 (2 degradados)»**, que se lee como
  cobertura casi total y **mide otra cosa**: la cobertura sobre la lista que el CRM confiesa.

**Cuánto falta, medido sin llamadas nuevas** — cruzando los elementos que el propio atlas ya cita en
sus líneas `Relaciones · parent: … · children: …` contra los 89 con ficha, salen **105 citados** y
por tanto **28 sin ficha**:

```
poderes, mandatos, proyectos, rgpdlopd, plantillas, templates, usuarios, mail, conceptos,
remesas, signatures_documents, tracking, lesionados, panels, reports, grupos, gruposcontables,
pagos_proveedores, cron, gdoculogdescargas, conceptos_varios, conceptos_finance,
conceptos_recibidas, conceptos_recibidas_gastos, conceptos_recibidas_honorarios,
catalogo_conceptos_provision, cuentascontables_configuracion, tarifas_conceptos_honorario
```

O sea que el denominador real es **117 como mínimo**, y «89» no es la superficie: es lo que
`/api/elements` admite.

⚠️ **Precisión sobre lo que esto demuestra y lo que no:** son 28 **nombres citados sin ficha**. Que
un elemento sin ficha *responda* solo está comprobado en **uno**, `poderes` (esquema, enums,
relaciones, listado, detalle y escritura — §16 de `INTEGRACION_SUDESPACHO.md`). De los otros 27 se
sabe que el CRM los declara como relaciones válidas de otros elementos, y nada más. No llamarlos
«operativos verificados» hasta sondearlos: es justo la clase de salto que esta entrada denuncia.

**Por qué importa más de lo que parece:** el atlas existe para no descubrir endpoints a mano
(`CLAUDE.md`: «consultarlo ANTES de descubrir un endpoint a mano»). Un elemento ausente del atlas
invita a concluir que no existe, que es exactamente el error contra el que avisa
`feedback-no-lo-se-no-es-no-hay`: **«no está en el atlas» tiene que poder leerse como «no pude
mirar», no como «no hay»**. En esta sesión el elemento ausente resultó tener 85 registros, 87
documentos y 16 poderes caducados que nadie veía.

**Vías posibles, sin decidir:**

1. **Ampliar la semilla de la Fase B**: unir a `/api/elements` los nombres que aparecen en las
   relaciones ya descubiertas (`parent`/`children`), que es un cierre transitivo barato y no
   necesita ninguna llamada nueva para arrancar. Sondear cada uno con `view/config/{e}/fields`, que
   es lo que la Fase B ya hace.
2. **Corregir el rótulo de cobertura** para que declare su denominador: «87 de los 89 que
   `/api/elements` lista; hay ≥28 elementos operativos fuera de esa lista».
3. **Dejarlo y documentar el punto ciego** — que es lo que se ha hecho de momento, en
   `INTEGRACION_SUDESPACHO.md` §16.1.

La (2) es barata y quita el falso sentido de completitud; la (1) es la que de verdad cierra el hueco
y necesita medir cuántos de los 28 responden.

**Disparador para promoverla:** que haga falta el esquema de alguno de esos 28. Hoy solo hacía falta
`poderes`, y ese ya está escrito a mano en el §16.

## 186. Un término de blocklist homógrafo de palabra común pone la suite roja sin ningún commit, y no hay forma de declararlo

**Medido el 2026-09-09**, cuando `test_no_pii_en_tests` se puso rojo en `main` sin que nadie hubiera
tocado código.

El matcher de `escanear()` es `(?<!\w) + re.escape(termino) + (?!\w@)` con `IGNORECASE`. La frontera
de palabra está **bien** puesta —no es el defecto del `\bNIE\b` que cazaba «intervi**nie**ntes»—,
pero un término de la lista cuya forma sin tilde coincide con una palabra común del castellano
muerde cualquier prosa que la use. En este caso: un comentario de `core/email_firmas.py` que enumera los
idiomas de las frases de atribución de correo, puesto por el **PR #282 el 2026-09-05**, y su gemelo
en el test.

**Y no hay exención posible, por diseño.** El propio guard lo dice al bloquear: *«`leak-guard:allow`
en la línea exime SOLO las detecciones por FORMA (DNI/NIE/IBAN); un término de la blocklist no
admite exención por anotación»*. Es deliberado y defendible —una escotilla por anotación sobre
nombres reales es justo lo que no se quiere—, pero deja **una sola salida**: cambiar la prosa, o
`--no-verify`. Para un falso positivo estructural, eso es poco.

### Lo que de verdad no estaba escrito: el veredicto no es función del commit

La blocklist vive en **dos artefactos gitignored** —`data/_saneado/replacements.txt` y
`data/_config/pii_blocklist.txt`—, y el segundo se amplió el 2026-09-09 a las 13:34 con el término
en cuestión. Por tanto:

> **El mismo árbol daba verde a las 12:00 y rojo a las 16:00**, en `main` y en todo worktree, sin un
> solo cambio versionado. Un verde medido antes de que alguien amplíe la lista **no acredita nada**
> después, y un rojo no implica que el commit lo haya causado.

Eso **no** es un fallo del diseño de `MEJORAS #161` (que hizo que la lista se resolviera desde el
checkout principal, y por tanto que el guard por fin corriera en los worktrees): es su consecuencia
buscada. Lo que falta es la contrapartida — **ampliar la blocklist es un cambio que puede romper la
suite de todo el mundo, y hoy nada lo advierte ni lo deja trazado.**

### La otra mitad del coste fue de método, y es mía

Diagnosticarlo llevó veinte minutos de arqueología —historia del fichero, del matcher, copias
externas de dos commits— **y el mensaje del propio guard lo explicaba en una línea**. No lo vi
porque nunca corrí el guard: corrí `pytest`, leí el aserto del test, y me fui a la fuente. El test
imprime *qué* término y *en qué* fichero; el **hook** imprime *por qué no puedes eximirlo*. Son
dos instrumentos con salidas distintas sobre el mismo defecto, y elegí el que no contestaba mi
pregunta. Lección reutilizable: **ante un guard en rojo, correr el guard**, no solo su test.

### Vías posibles, sin decidir

1. **Declarar la dependencia en el cierre**: que `session_close` imprima `sha256` y fecha de las dos
   fuentes de la blocklist junto al conteo de la suite. No arregla nada, pero convierte veinte
   minutos de arqueología en una línea, y hace comparables dos verdes de días distintos. Es la más
   barata de las cuatro.
2. **Marcar en la propia blocklist los términos ambiguos** (un sufijo tipo `#comun`) y exigirles
   contexto —mayúscula inicial, vecindad de un nombre de pila— en vez de coincidencia desnuda. Es la
   que ataca la causa; cuesta decidir quién mantiene esa marca.
3. **Un aviso al añadir un término**: comprobarlo contra un diccionario y avisar si es palabra
   común, en el momento en que alguien tiene el contexto para decidirlo.
4. **Nada, y que el mensaje del guard baste** — que es lo que hay hoy, y hoy ha costado veinte
   minutos a una sesión y ha bloqueado el cierre de todas las demás.

**Un nit, de paso, que no justifica por sí solo una entrada:** el comentario junto a la constante
(`_ALLOW = "leak-guard:allow"  # anotación de exención por línea`, `precommit_leak_guard.py:297`) no
dice que la exención sea solo por forma. El mensaje de bloqueo y `docs/SEGURIDAD_DATOS.md` sí lo
acotan bien; es solo esa línea la que se lee más amplia de lo que es.

**Remediado de momento, sin cerrar nada:** los dos comentarios pasan a citar el idioma por su código
ISO 639-1, con una nota en el módulo que explica por qué y advierte de no revertirlo. Eso desbloquea
la suite; las cuatro vías siguen abiertas.

**Disparador para promoverla:** el segundo término homógrafo, o el primer rojo sin commits nuevos que
vuelva a costar más de diez minutos de diagnóstico.
### Y oscila en los DOS sentidos: rojo a las 17:00, verde a las 17:30 (medido aparte)

Confirmación independiente desde otra sesión el mismo 2026-09-09, que añade la mitad que
faltaba: la de arriba documenta **verde → rojo** (12:00 → 16:00); esto es **rojo → verde**.

- **~17:00** — la suite completa deja el guard en rojo con las dos detecciones de siempre.
  Verificado en un **checkout limpio de `main`**: fallaba igual sin el commit de la rama, o
  sea preexistente y ajeno al PR que lo encontró (#308).
- **~17:30** — `1 passed`, y **no por un `skip`**: la lista se resuelve (82 términos) y
  `escanear()` devuelve **0 hallazgos** sobre esos dos mismos ficheros.
- Y **nada de lo obvio había cambiado**: el gentilicio sigue en `core/email_firmas.py` (1
  ocurrencia), el término sigue apareciendo en lo que devuelve `cargar_blocklist()` y es
  **exactamente** esa palabra (una sola, 6 caracteres), y el código del escáner en ese
  worktree no se tocó.

**Lo que ese último punto destapa, y es nuevo:** si el término sigue en lo que
`cargar_blocklist()` devuelve y aun así `escanear()` ya no lo caza, entonces **la lista que
el test carga y la que el escáner usa efectivamente no son la misma cosa** — coherente con
que la blocklist viva en dos artefactos (`replacements.txt` y `pii_blocklist.txt`) y con que
uno se ampliara ese día. No se ha determinado cuál de los dos cambió entre las 17:00 y las
17:30, y **no se volcó ninguno para averiguarlo**, porque volcar la lista completa está
prohibido (`SEGURIDAD_DATOS.md`, precedente de `rclone config show`). Queda como *no lo sé*,
que no es *no hay*.

**Refuerza la vía 1** de las cuatro de arriba, y le añade un requisito: que el sello del
cierre declare el `sha256` **de los dos** ficheros, no solo de uno — con uno solo, este
episodio habría seguido siendo inexplicable.

**Nota de método, del otro lado.** El primer intento de documentar esto citaba literal la
salida del test, y el hook **bloqueó el commit de la entrada que describía su propio falso
positivo**: hay que escribirla sin nombrar el término. Y el hook **no** escanea mensajes de
commit, así que el término sí llegó al mensaje del commit que la introdujo. Sin consecuencia
—es un gentilicio—, pero es un hueco de cobertura.

## 187. El aviso de «cabecera de la bitácora rancia» se declaró promovido el 2026-08-26 y nunca se construyó — sexta reincidencia

> **Séptima reincidencia, medida el 2026-09-09.** El bloque del **93º cierre** entró en `main`
> (`35e5ea5`) con la cabecera todavía en el **92º**: la resolución del conflicto tomó la bitácora
> de `main` e insertó el bloque nuevo encima, sin tocar la cabecera — el mismo modo de fallo, ahora
> por la vía del merge. **No lo cazó el autor: lo cazó la sesión hermana** que había escrito el 92º.
> **El disparador que esta entrada declara —«la séptima vez»— queda por tanto cumplido.**

**Medido el 2026-09-09.** La bitácora tiene una nota, escrita al cerrar el 72º, que dice
literalmente: *«**Promovido: aviso en `session_close`** — comparar la fecha y el ordinal de esta
línea con el **primer bloque `## AAAA-MM-DD`** del fichero, y avisar si no coinciden. Es una
comparación de dos cadenas, y las dos están en el mismo fichero.»*

**No existe.** `grep` de `session_close.py` no devuelve ninguna lectura de la línea de cabecera,
ningún test la cubre, y no hay fila en `PLAN.md` ni entrada aquí. Un lector de esa nota concluye
razonablemente que el control está puesto.

**Y el defecto que iba a vigilar volvió a ocurrir el 2026-09-09**, sexta vez: la sesión que escribió
el 90º cierre dejó su bloque y **no tocó la línea de cabecera**, que se quedó en el 89º. La repuso el
91º al detectarla.

**Lo que esto mide no es el descuido, es la nota.** La propia nota ya razonaba, con dos casos
delante, que *«un aviso escrito para el humano que lo lea después no sustituye a un guard»* — y
acto seguido el remedio se dejó **como prosa en el mismo fichero que denunciaba**. Tercera medida
de la misma propiedad, y esta vez sobre el remedio en lugar de sobre el síntoma: **«promovido» en
una nota no es promovido**; promover es tener número aquí o fila en `PLAN.md`, que es lo que
`session_close` sabe leer.

**Lo que hay que construir, que sigue siendo pequeño:** leer la primera línea `**Última
actualización:**` y el primer encabezado `## AAAA-MM-DD` de `docs/bitacora/AAAA.md`, extraer fecha y
ordinal de cada uno, y avisar si difieren. Va donde están los otros cinco avisos, no bloquea, y su
test es un fichero sintético con las dos cadenas descuadradas — más un **control positivo**, o el
verde no acreditará nada.

**Ojo al alcance real:** el mismo fichero conserva **once** líneas de cabecera (`Última
actualización` + diez `Línea del Nº, conservada`), así que el aviso debe comparar contra la primera,
no contra cualquiera. Y las anomalías históricas de numeración de la cola del fichero —cuatro
cabeceras que dicen «2º cierre» y ningún «3º»— están documentadas y **no se renumeran**: un aviso que
verifique contigüidad de ordinales daría rojo permanente sobre ellas.

**Disparador para promoverla:** la séptima vez, o cualquier sesión que ya esté tocando los avisos de
`session_close`. Enlaza con `#186` (1), que también propone que el cierre declare lo que no puede
deducirse del commit.

## 188. El intake de correo dice «OK Caso abierto» dejando el material sin OCR y sin avisar

> Medido el 2026-09-09 en la apertura de `W-04A6LI`, ejecutando el comando, no leyendo el código.

`scripts/abrir_caso.py` en modo `libre` con `--fuente email` deposita el lote y termina así, literal:

```
Email: etiqueta '…' exportada a …\00_Input\2026-09-09_email_01
CRM omitido (--crm skip): referencia pendiente + TODO
OK Caso abierto: <case_id>
```

En ese momento el expediente tenía **43 `.eml` y 18 adjuntos en crudo**: sin atomizar, sin
`.contenido.md` y sin espejo en la sala de máquina. La corrida sale con **código 0** y la última
línea dice «OK». No encadena `sala_maquina apply`, no lo sugiere y **no deja pendiente durable**
—ni evento, ni marcador, ni aviso—.

**El OCR del correo no falta: está cableado.** Dentro de `apply` el orden lo garantiza el código
(`scripts/sala_maquina.py`, `_atomizar_correo` → `_procesar_adjuntos` → `_construir_plan` → OCR) y
lo vigila `test_atomiza_antes_de_construir_el_plan_de_ocr`. Un `.eml` en `00_Input` recibe OCR
igual que un PDF del Drive, y sus adjuntos también porque `--extraer-adjuntos` (default desde el
PR #299) los deja como ficheros sueltos ahí dentro. Lo que falta es que **alguien vuelva a
llamar a `apply`**, y eso hoy es memoria del operador.

**Por qué es caro y no molesto.** El daño no se ve: no hay traza roja. Se manifiesta semanas
después como una **ausencia que se disfraza de «no hay»** — se busca en el expediente un documento
que llegó como adjunto de correo, no aparece porque nadie extrajo su texto, y se concluye que no
está. Es el mismo defecto de `feedback-no-lo-se-no-es-no-hay`, con la agravante de que la
herramienta ha dicho «OK». Y afecta igual a la sala de lectura y a la viabilidad, que trabajarían
sobre un expediente incompleto creyéndolo completo.

**Lo que NO es la solución.** Encadenar `apply` desde `libre` reintroduce en la secuencia lo que la
puerta de V1 excluye a propósito (`--fuente email` llama a Gmail, que es de V3), y el
descubrimiento de correo está **diferido a V3 por decisión de Nikolai del 2026-08-24**
(`PLAN.md`). Esta entrada no pide adelantar V3.

**Lo que sí:** que un intake que ha depositado algo **no pueda terminar diciendo «OK» a secas**.
Declararlo, no desplazarlo: el pendiente ya existe como vocabulario en V1
(`etapa_no_ejecutada:<etapa>`, `EstadoV1.preparado_con_pendientes`), así que la pieza es reusar ese
vocabulario en `libre` en vez de inventar uno. Mínimo viable: si el intake depositó ficheros,
imprimir el paso que falta y registrarlo en `_intake_log.jsonl`, de modo que la ausencia quede
**escrita** y no dependa de que el operador se acuerde.

**Hermano mayor, peor por radio de daño.** El `RUNBOOK` deja anotado que la UI de Streamlit
exporta correo y lanza el intake judicial **sin sostener el mutex del caso**. Eso puede corromper,
no solo omitir. Si se gasta esfuerzo en cableado, va antes que esto.

**Disparador de promoción.** La primera vez que alguien que no sea yo corra el intake de correo de
un caso —Paola o Ana por la UI, o una sesión que no haya leído este runbook—, o la primera vez que
se busque en un expediente un documento llegado por correo y no aparezca.

## 189. `layout_bundle_hilo` llavea por basename, y `email_export` no lo hace único dentro del lote

> Medido el 2026-09-09 montando la sala de lectura de `W-04A6LI`. Bloqueó el bundle por hilo.

`layout_bundle_hilo` (`.claude/skills/organizar-sala-lectura/scripts/preclasificar.py`) usa el
**nombre de fichero** como llave del grupo y **aborta con `ValueError`** si se repite. Su docstring
justifica que eso es tolerable porque el choque solo puede venir de **dos lotes distintos**:
«`_ruta_unica` solo desambigua dentro de su propio lote».

**Esa premisa es falsa.** `email_export` desambigua la **carpeta contenedora**, no el nombre del
`.eml`: un mensaje con adjuntos va a su propia subcarpeta (`…`, `…_2`, `…_3`, `…_4`) y el `.eml`
de dentro conserva el nombre pelado. Medido en el lote `2026-09-09_email_01` de `W-04A6LI`, **un
solo lote**:

| basename | veces | parents |
|---|---|---|
| `2026-07-03_gracias_por_rellenar_este_formulario_pbc_comunicacion_intern.eml` | **4** | `…`, `…_2`, `…_3`, `…_4` |
| `2026-08-14_pbc_referencia_w_04a6li_<dir>.eml` | 3 | `…`, `…_2`, `…_3` |
| `2026-08-17_pbc_referencia_w_04a6li_<dir>.eml` | 3 | idem |
| `2026-09-09_requerimiento_de_restitucion_honorarios_de_intermediacion_in.eml` | 3 | raíz, `…`, `…_2` |
| `2026-06-30_arras_con_abogado_por_parte_compradora_w_04a6li.eml` | 2 | raíz, `…` |

Cinco de nueve hilos del caso, uno de ellos el del **requerimiento**. Con los basenames
repetidos no hay forma de resolver el fichero de origen desde el grupo, así que la sala de
`W-04A6LI` se montó con los `.eml` **PLANOS** y el discriminante `sha256[:6]` — desviación
declarada en su `_plan/`.

**Dos frentes, y el segundo es la frontera.** (1) `layout_bundle_hilo` puede llavear por **ruta
relativa** en vez de por basename: la ruta sí es única por construcción, y `agrupar_por_hilo` ya
agrupa por la descripción del nombre, así que la llave y el agrupador son cosas distintas que hoy
comparten valor por accidente. (2) Y la propiedad de la que esto es un ejemplo: **el export
promete unicidad de un identificador y entrega unicidad de otro**. Cualquier consumidor que
llavee por nombre hereda el mismo defecto — `senales_gate` lo demuestra al reportar estos cinco
casos como «casi-duplicado: mismo nombre de origen con N sha256 distintos», que es un
diagnóstico equivocado sobre una detección correcta.

**Coste de no arreglarlo:** los hilos de correo no se agrupan y la sala pierde la lectura por
conversación. No hay pérdida de información (el manifiesto llavea por `sha256`) ni riesgo de
sobrescritura; `plano_existente=True` ya contempla convivir con hilos materializados planos, así
que arreglarlo después no obliga a re-montar nada.

**Disparador de promoción.** El próximo caso con correo cuya lectura por hilo importe —o antes,
si se toca `layout_bundle_hilo` por cualquier otro motivo, porque el cambio de llave es de una
línea y el test que lo fija es el que falta.

## 190. La sala de máquina identifica por BYTES y la de lectura filtra por EXTENSIÓN, en silencio

> Medido el 2026-09-09 en `W-04A6LI`: 4 documentos reales del Drive fuera del catálogo.

Dos componentes del mismo expediente deciden «esto es un documento» por criterios distintos:

- **Sala de máquina:** auto-detecta por **firma de bytes** desde el PR #55 (`[APER-21]` del
  runbook). Un fichero del Drive E&V cuyo nombre no tiene punto se OCR-iza igual.
- **Sala de lectura:** `core/inventory.py:95` hace
  `if path.suffix.lower() not in _RELEVANT_EXTS: skipped.append(...)`. **Sin extensión no hay
  fila**, y por tanto no hay entrada en `indice_documental.yaml` ni copia en la sala.

**Y la omisión no se dice.** `core/sala_lectura.py:851` solo lee `inv["skipped"]` dentro de
`if not catalogo_documental.load_catalog(case_id)` — o sea, únicamente cuando el catálogo queda
**vacío**, para distinguir `sin_extension_relevante` de `input_vacio`. Con catálogo no vacío
—el caso normal— el `skipped` no se cuenta, no se imprime y no queda en ningún evento.

**Los cuatro de `W-04A6LI`**, todos con espejo MD y texto útil, todos invisibles para la sala:

| Fichero en `00_Input/01_Drive EV/` | Lo que contiene | chars |
|---|---|---|
| `certificado Ayuntam pago tributos` | certificado municipal de estar al corriente de tributos, firmado el 30-07-2026 | 1.407 |
| `FACTURA AGUA` | factura de agua de 27-05-2026 | 590 |
| `FACTURA AGUA 2` | factura de agua de 24-02-2026 | 621 |
| `facturas luz listado 2` | histórico de facturación eléctrica del inmueble | 430 |

No es un caso raro: E&V sube ficheros desde el móvil sin extensión con normalidad. En este
expediente eran **documentación de suministros y de tributos del inmueble** — la que acredita
la actividad de la agencia sobre la finca.

**Dos arreglos, y son independientes.** (1) Que `inventory.scan` decida por firma de bytes
cuando no hay extensión, reusando lo que la sala de máquina ya tiene: entonces las dos salas
ven lo mismo. (2) Y, con arreglo o sin él, **que `skipped` se diga siempre**: contar los
omitidos y enumerarlos, en pantalla y en un evento de `_intake_log.jsonl`. La segunda es la
que importa, porque el criterio de relevancia puede seguir siendo discutible mientras el
silencio no lo es — la frontera es la misma de `MEJORAS #188`: **una ausencia que se disfraza
de «no hay»**.

**Disparador de promoción.** La primera vez que se monte una sala de lectura de un caso cuya
prueba llegue por foto de móvil sin extensión; o antes, si se toca `inventory.scan`, porque
enumerar `skipped` son tres líneas y el test que lo fija es el que falta.
## 191. El intake judicial no modela la fase procesal: ni bucket ni rol para la prueba y el juicio

> Medido el 2026-09-08 montando `W-02VEKE` (expediente judicial CRM #540, 76 documentos;
> autos de 2025, audiencia previa ya celebrada, testigos citados, juicio pendiente).

**Lo que se midió.** `intake-judicial --full` escribió 72 documentos de 76 (4 solapados, 0
errores) y los repartió en dos cajones: `01_Demanda` = 31 y `99_Otros` = 45. El bucket
`02_Contestacion` **no llegó a crearse**.

En `99_Otros` acabó todo lo que hace falta para preparar un juicio: las dos minutas de prueba
(la propia y la del contrario), la minuta de audiencia previa, la solicitud de prueba, las dos
citaciones de testigos, las diligencias que fijan y suspenden la vista, la grabación de la
audiencia previa (`.mkv`, 150 MB), el decreto de admisión, la sentencia de un pleito conexo y
la apelación — junto al burofax extrajudicial de 2024.

**La frontera, no el ejemplo.** `_VALID_BUCKETS` (`core/case_manager.py`) tiene seis buckets y
los cinco con nombre son todos de la fase de **alegaciones** (`01_Demanda`, `02_Contestacion`,
`03_Monitorio_Demanda`, `04_Monitorio_Oposicion`, `05_Diligencias_Preliminares`). Y
`core/judicial_classifier.py` define exactamente dos roles, `ROLE_DEMANDA` y
`ROLE_CONTESTACION`. **El modelo se acaba donde acaba la contestación**: de la audiencia previa
en adelante no hay ni vocabulario ni destino. No es que falte un id de carpeta — es que la fase
de prueba y juicio no existe como categoría en ningún punto del intake.

**Y la señal que sí existe se descarta.** En esta corrida el clasificador acertó
—`contestacion: ok -> CONTESTACION DDA`— y el fichero se depositó en
`99_Otros/contestacion_dda.pdf`. El bucket lo resuelve `crm_branch_path` por la **carpeta del
CRM** (aquí `306|CIVIL`, porque el procurador no archiva por fase) y el rol lo resuelve el
**nombre del documento**; las dos señales no se cruzan en ningún punto del código. El intake
sabía el rol y archivó como si no lo supiera. Hay escape manual (`bucket_override`, D11), pero
exige que el letrado descubra el problema.

**Esto no es nuevo, y ahí está lo relevante.** El 40º cierre (2026-07-27) ya lo midió en
`W-02MA0R` / CRM 487 con la formulación correcta: «el CRM no archiva por fase procesal —38 de 70
en un cajón genérico CIVIL, así que ningún mapeo de `id_carpeta` lo desenreda— y la señal útil
es el **lote de presentación** (`modified_at`), no la carpeta». La respuesta diseñada es la
**vista procesal de `05_Procedimiento`** (`PLAN.md` fila #9, spec v3.1 con dos revisiones
adversariales de Codex consumidas, piezas 1-2 mergeadas). Lo que este caso añade no es el
diagnóstico: es el **corpus** que le faltaba a la pieza 3 y un caso real con la vista encima.

**Remedio candidato, dentro de esa vista y no aparte.** (1) Vocabulario de fase para lo
posterior a la contestación; (2) cruzar rol y bucket: un rol resuelto `ok` manda sobre la
carpeta del CRM, o al menos se avisa cuando discrepan; (3) `modified_at` como eje, que es la
señal que el 40º cierre ya identificó. Ampliar `CARPETA_ID_TO_PATH` **no** vale: los tres ids
nuevos de este expediente (`305` DECLARATIVO, `306` CIVIL, `63` RGPD) los resuelve ya la
heurística de label, y los resuelve a `99_Otros` correctamente — el cajón no está mal mapeado,
está mal concebido para esta fase.

**Disparador de promoción.** Ya disparado: caso real en fase de juicio con la prueba
indiferenciada. Va contra `PLAN.md` fila #9, no como entrada independiente.

---

## 192. `abrir_caso` INVENTA `referencia_crm` copiando el `case_id`, y el invento dispara después la alarma de desalineación

> Medido el 2026-09-08 en `W-02VEKE`, un caso que ya existía en el CRM antes de abrirse en Drive.

**Lo que hace.** `scripts/abrir_caso.py:1081` llama a `ensure_case(..., referencia_crm=ident.case_id)`.
El campo que dice ser «la referencia del CRM» se rellena **siempre** con el nombre local recién
construido, sin consultar al CRM. Con `--crm api` el alta crea la referencia con ese mismo texto y
las dos coinciden, así que el campo es correcto por construcción. **Con `--crm skip` —el caso que ya
está en el CRM— el campo queda falso.**

Medido en este caso: `_caso.md` quedó con `referencia_crm: BaRS10 - … - Negativa arras`, mientras el
CRM dice `BaRS10 - … - Negativa con oferta aceptada` para los dos expedientes (#464 y #540).

**Lo que NO es.** No es un falso verde de la guarda. `verify_expediente_referencia` funciona:
medida con los dos valores da `match=False` con lo que hay en `_caso.md` y `match=True` con la
referencia real. Control positivo y negativo, los dos. El «Referencia CRM coincide» que imprimió
el pull fue **correcto**, porque se le pasó la referencia real por `--referencia`.

**La consecuencia real es la contraria de la temida:** el sistema generará una **falsa alarma
recurrente sobre su propio dato**. El primer pull que se corra sin `--referencia` comparará el CRM
contra el valor inventado y sacará el «Referencia desalineada CRM <-> caso local», invitando a
abortar y revisar `_caso.md` por un desajuste que escribió el propio alta.

**Y `--referencia` no lo arregla.** `ensure_case` fija `referencia_crm` solo si el índice es nuevo
(`is_new`), coherente con su contrato de no sobrescribir. Así que el flag sirve para la validación
de esa corrida y **no repara el dato**, que queda mal para siempre. En este caso se repuso a mano
con el escritor atómico y se verificó contra el CRM (`match=True` en #464 y #540) — tanto el
frontmatter (raíz y `meta`) como la línea del cuerpo, que `_actualizar_cuerpo` no regenera.

**Remedio candidato.** Con `--crm skip`, no inventar: leer la referencia del CRM por W-code (una
llamada REST por elemento; `_rest_search_expedientes` ya lo hace y devolvió los dos ids sin más
dato que el W-code) y, si no se puede leer, **dejar el campo vacío** en vez de rellenarlo con un
derivado. Un campo vacío es honesto y la guarda ya sabe tratarlo (`expected_referencia=None`);
un campo inventado es peor que ninguno porque se presenta como dato del CRM. Alternativa mínima:
que `ensure_case` acepte reponerlo cuando el llamador lo pasa explícito.

---

## 193. La plantilla del `case_id` no puede reproducir la referencia del CRM, y eso deja ciego el dedup exacto

> Medido el 2026-09-08 en `W-02VEKE`.

**El choque.** `core/abrir_caso.py:56` compone `f"{codigo} - {direccion} ({w_code}) - {sufijo}"`.
Las referencias que este tenant tiene en el CRM llevan un separador **extra** antes del paréntesis
—`BaRS10 - <via> - (W-02VEKE) - …`— que la plantilla no genera. No hay valor de `--direccion`
que lo reproduzca salvo colgando un guion al final de la dirección.

**Por qué importa.** `find_expediente_judicial_by_referencia` (y su gemela extrajudicial) exigen
coincidencia **exacta tras normalizar espacios, acentos y case**; un separador de más no lo salva.
Son las funciones que se consultan «antes de crear un expediente para detectar duplicados», así que
para todo caso cuya referencia venga del CRM ese dedup devuelve `None` y **no protege**: un alta
futura podría crear un judicial duplicado. El dedup por W-code
(`list_expedientes_judiciales_candidatos`, filtro `like`) sí funciona y es el que localizó #464 y
#540 en este caso.

**Y hay un choque de nombres debajo.** `core/config.py` manda que el descriptor del `case_id` salga
**siempre** del `tipo_caso` canónico («si no, hay que renombrar cross-sistema»). Aquí el tipo
canónico es `NEGATIVA_ARRAS` -> sufijo `Negativa arras`, y el CRM dice `Negativa con oferta
aceptada`. Esa regla está escrita suponiendo que **el alta local es la primera**; cuando el CRM va
delante hay dos fuentes y una tiene que ceder, y ceder por el lado del CRM significa renombrar la
referencia de un expediente judicial vivo. Se resolvió usando el sufijo canónico y dejando la
referencia real en `referencia_crm` (ver `#192`), pero la regla no tiene caso escrito para esto.

**Remedio candidato.** Que el dedup «antes de crear» use el **W-code** y no la referencia completa
—es la clave estable, y ya existe la función—, dejando el match exacto para lo que de verdad
necesite igualdad textual. Y escribir en `config.py` qué manda cuando el CRM va primero.

---

## 194. Un `/` en el nombre del documento del CRM parte el slug y el fichero pierde su identidad

> Medido el 2026-09-08 en `W-02VEKE` (expediente judicial CRM #540).

**Lo que se midió.** Dos documentos del gestor documental llegaron a `05_CRM/99_Otros` llamados
`26_10_30_hs.pdf` y `2026_11_30_hs.pdf`. Sus nombres en el CRM son:

- `DIOR-POR CONSTESTADA DDA+FIJA AUD PREVIA 24/3/26, 10:30 HS`
- `DIOR-SUSPENDE AUD Y SEÑALA NVA VISTA  30/04/2026, 11:30 HS`

El slug conservó **solo el fragmento posterior a la última barra** y descartó todo lo anterior.
Son las dos resoluciones que **fijan y suspenden la audiencia previa**: el fichero que dice qué
día hay vista se llama `26_10_30_hs.pdf`.

**La frontera.** Es el mismo defecto que `[APER-56]` —el `/` en `--direccion` partía la carpeta
del caso en dos— pero en otro sitio: allí lo sufría el nombre de la **carpeta**, aquí el del
**documento**. `[APER-56]` se cerró con `MEJORAS #148` validando los campos del **alta**
(`--codigo-caso`, `--direccion`, `--sufijo`); el nombre que llega del CRM no pasa por esa
validación, y no puede: no es un campo que escriba el operador, es un dato remoto. Lo que hace
falta aquí no es abortar —el documento hay que bajarlo igual— sino **normalizar la barra en vez
de tratarla como separador de ruta**.

Y hay un agravante de fecha: en un procedimiento español las resoluciones llevan la fecha con
barras (`24/3/26`, `30/04/2026`) **por convención**, así que este caso no es raro. Cualquier
señalamiento, plazo o vencimiento que el juzgado nombre con fecha entra por esta puerta.

**Remedio candidato.** En `_safe_stem_ext` (o donde se compone el slug del documento del CRM),
sustituir `/` y `\` por un separador inocuo **antes** de cualquier tratamiento del nombre, en vez
de dejar que la última barra actúe como frontera. El `_` es suficiente: `dior_por_contestada_
dda_fija_aud_previa_24_3_26_10_30_hs.pdf` es feo y es legible, y sobre todo dice qué es.

**Cómo comprobar que el remedio funciona, sin fiarse del verde.** Un test con un nombre sin
barra pasa hoy y pasaría después: no prueba nada. El test tiene que llevar la barra dentro y
afirmar que el stem conserva el prefijo — y hay que **verlo rojo** contra el código actual antes
de arreglarlo.

**Disparador de promoción.** Bajo: los ficheros están en el expediente y su contenido es
correcto; solo el nombre es ilegible. Sube si alguna vez hay que localizar un señalamiento por
nombre en un caso con muchas resoluciones, o si se construye la vista procesal (`MEJORAS #191`),
que ordena por lote y presentaría estos dos sin identidad.

---

## 195. `node_modules` no está en `.gitignore`, y dos skills lo necesitan para funcionar

> Medido el 2026-09-08 al generar los entregables de `preparacion-juicio-oral`.

**Lo que se midió.** La skill `preparacion-juicio-oral` declara `docx: ^9.7.1` en su
`package.json` y **no trae `node_modules`** (se vendorizó a propósito sin él, 2026-06-12). Sus
cuatro generadores `gen_*.js` no corren sin esa dependencia. Y
`git check-ignore .claude/skills/preparacion-juicio-oral/node_modules` devuelve **no ignorado**:
un `npm install` en la carpeta de la skill mete miles de ficheros al índice de git.

O sea: la skill no funciona sin instalar, e instalar en el sitio natural contamina el repo. Hoy
se resuelve por disciplina del operador —instalar fuera del árbol y apuntar `NODE_PATH`—, que es
justo la clase de cosa que se olvida.

**Remedio candidato.** Dos líneas independientes, y las dos merecen la pena:

1. **`node_modules/` a `.gitignore`** (patrón global, no por skill). Barato y sin discusión: es
   una red, no una solución.
2. **Que la skill diga cómo se instala.** Su `flujo.md` describe siete fases y ninguna menciona
   la dependencia; la Fase 3 empieza directamente en «genera `CONCLUSIONES_[REF].docx]`». Basta
   una línea en la Fase 0 con el comando y el `NODE_PATH`, o un script que lo prepare.

**Ojo con el alcance:** comprobar si le pasa lo mismo a las otras skills con `package.json`
(`preparacion-audiencia-previa` al menos comparte generadores). El punto 1 las cubre a todas; el
2 hay que escribirlo en cada una.

**Disparador de promoción.** Ya disparado en su forma leve: hizo falta para el juicio de
`W-02VEKE` y se resolvió instalando fuera del árbol. La entrada existe para que la próxima vez
no haya que descubrirlo — y para que nadie cierre el hueco con un `npm install` dentro del repo.

---

## 196. El pipeline deja `empty` un PDF que `ocrmypdf --skip-text` lee con 12.246 caracteres

> Medido el 2026-09-09 en `W-02VEKE`, montando su sala de lectura. Tres documentos, mismo
> motor (OCRmyPDF), resultados muy distintos según quién lo invoque.

**La medición.** El informe de actividades del CRM (`D 05` de la demanda) pasó por
`sala_maquina apply` y quedó en `_cobertura.json` como **`estado: empty`, 20 caracteres**,
con la nota «sin texto o residual». El mismo fichero, copiado al scratchpad e invocado a
mano con `ocrmypdf -l spa --skip-text --sidecar`, devuelve **12.246 caracteres** de texto
correcto (el reporte de LeadHub: 42 exposiciones finalizadas, 3 visitas, la tabla de
actividades con consultor, contacto y fecha).

No es un caso aislado. Los otros dos informes del CRM del mismo expediente:

| documento | pipeline (`_cobertura.json`) | `ocrmypdf` directo |
|---|---|---|
| `d_05_crm_informe_actividades_propiedad` | **20** (`empty`) | **12.246** |
| `d_03_crm_ficha_propiedad_acacies` | 1.583 (`ok`) | 6.140 |
| `d_07_crm_comprador_actividades` | 989 + 3.764 (`ok`, 2 segmentos) | 4.956 |

Los tres son **capturas de pantalla del CRM impresas a PDF**: página larga, tipografía
pequeña, mucha tabla. La invocación directa fue `-l spa --skip-text`, sin `--oversample`
ni nada especial.

**Por qué importa más de lo que parece.** `texto_espejo_md` devuelve `None` cuando el
estado es `empty` —por diseño, «no hay texto útil que ofrecer»—, así que el documento
queda invisible aguas abajo: la sala de lectura lo clasifica **a ciegas por el nombre** y
sin fecha, y ningún análisis posterior ve su contenido. En este caso ese documento es la
prueba de la gestión eficaz de la agencia (las 42 exposiciones), que es hecho no
controvertido del pleito pero cuya acreditación documental es justo ese informe.

**Lo que NO se sabe todavía, y hay que medirlo antes de tocar nada.** No sé qué hace
distinto el pipeline. Hipótesis a discriminar, en orden de coste:

1. **Los peldaños de la escalera** (`MEJORAS #90` (a)/(b)): el pipeline decide por página
   entre `pypdf` y OCR, y puede estar dando por buena una capa de texto vacía sin llegar a
   OCRizar. El indicio: la nota del `_cobertura` es «sin texto o residual», que es el
   veredicto DESPUÉS de intentarlo.
2. **Los flags**: si el pipeline usa `--force-ocr` o `--redo-ocr` en vez de `--skip-text`.
   Ojo: `--force-ocr` es el que la sesión del 2026-07-14 midió que infla 3-10× y destruye
   la capa de texto real.
3. **El umbral de `empty`**: que el OCR sí produzca texto y el umbral lo descarte.

El experimento que lo separa es baratísimo: correr `apply --solo` sobre ESE fichero con
log de la orden `ocrmypdf` efectiva, y compararla carácter a carácter con la mía. Hasta
tenerlo, cualquier arreglo sería a ciegas.

**Cautela sobre el alcance.** Esto NO contradice la medición del 2026-09-08 («el OCR local
lee todo lo legible»), que se hizo con **invocación directa**, igual que la mía aquí. Si la
diferencia está en el pipeline, las dos mediciones son compatibles y lo que falla es la
capa de arriba, no el motor.

**Disparador de promoción.** Alto si se confirma la hipótesis 1 o 2: afecta a **todos** los
documentos escaneados de todos los casos, y el modo de fallo es silencioso (`empty` se lee
como «este documento no tiene texto», no como «no supe leerlo»). Mientras no se mida, queda
aquí con el dato de las tres filas.

---

## 197. `senales_gate` marca el audio y el vídeo como «binario opaco sin espejo MD», y eso inutiliza el gate en cualquier caso con WhatsApp

> Medido el 2026-09-09 montando la sala de lectura de `W-02VEKE`: **132 señales, de las que
> 129 eran audio, vídeo, imagen o zip**. Razón señal/ruido **2:132**.
>
> **Segunda población, en otro caso y por otra sesión** (aportada el 2026-09-09 por la sesión
> «Inventario de demanda Sergio», sobre `W-02USSI`): **292 señales — 170 «bundle sin parte», 89
> «binario opaco sin espejo» y solo 12 útiles** (W-codes ajenos). De esas 89, **67 son audio**.
> Razón señal/ruido **12:292**.
>
> Dos casos distintos, dos sesiones distintas, el mismo defecto: el gate no es ruidoso *en este
> expediente*, es ruidoso **por construcción**. Y la segunda medición añade un ángulo que la
> primera no tenía — la señal «bundle sin parte» aporta 170 de las 292, así que **agregar por
> tipo antes de presentar no basta**: hay al menos dos señales que hay que acotar, no una.

**El defecto.** `senales_gate` (`scripts/preclasificar.py`, señal (c)) marca toda fila cuya
extensión esté en `_EXT_OPACAS` y no tenga espejo MD en `_cobertura.json` con estado
`ok`/`low`. Y `_EXT_OPACAS` incluye `mp4`, `mov`, `avi`, `mkv`, `m4a`, `ogg` y `opus`.

Esas extensiones **no pueden tener espejo MD**: la sala de máquina las marca `sin_soporte`
por diseño (no hay transcripción de audio en el pipeline). Así que la señal dispara siempre
para todos ellas, y no dice «esto es ambiguo» sino «esto es un audio».

**El efecto medido en W-02VEKE**: 291 filas activas, de las que 120 son `.opus` de tres
exports de WhatsApp más 4 `.mp4`, 1 `.m4a`, 1 `.mkv` y 6 `.jpg`. Resultado: **132 señales**
en un caso donde lo genuinamente ambiguo eran **dos** (un expose de otro W-code adjuntado
en un chat, y el documento de `MEJORAS #196`). Con la razón señal/ruido a 2:132, el gate
deja de ser un filtro: o se lee entero —y son 132 líneas por revisar a mano— o se ignora,
que es lo que hará cualquiera a la segunda vez.

Y el propio SKILL.md avisa de este modo de fallo para el verify —«≥5 problemas homogéneos
del mismo tipo: la hipótesis por defecto es bug del check, no de los datos»— pero el gate
no lleva esa salvaguarda, ni agrega por tipo antes de presentar.

**Remedio candidato.** Separar «opaco **sin texto propio**» de «opaco **que debería tener
espejo y no lo tiene**». Solo el segundo es señal:

- **audio/vídeo** (`opus`, `m4a`, `ogg`, `mp4`, `mov`, `avi`, `mkv`): nunca señal por falta
  de espejo. Si acaso, un contador informativo («120 medias sin transcribir»).
- **PDF, imagen y ofimática**: siguen siendo señal si no tienen espejo — ahí la ausencia sí
  indica que se clasificó a ciegas.

Y, con o sin ese cambio, **agregar las señales por tipo** antes de presentar la propuesta:
un «131 × binario opaco sin espejo (129 de ellos audio/vídeo)» es accionable; 131 líneas
sueltas no.

**Cómo comprobar el remedio sin engañarse.** El test tiene que llevar dentro un `.opus`
**y** un `.pdf`, los dos sin espejo, y afirmar que sale **una** señal y no dos — y hay que
verlo **rojo** contra el código actual antes de arreglarlo. Un test con solo el `.pdf` pasa
hoy y pasaría después: no prueba nada.

**Un tercer dato, del mismo montaje y sobre otro helper del mismo paso** (medido el
2026-09-09 sobre el plan persistido de `W-02VEKE`): `emparejar_exports_whatsapp` devolvió
**0 de 3**. Exige que el basename sea exactamente `_export_original.zip` —el que deja
`whatsapp_intake.deposit_export`— y los tres exports del caso se llaman
`Chat de WhatsApp con <nombre>.zip` y `WhatsApp Chat - <nombre>.zip`, que es como los
nombra la exportación de E&V. **La sesión «Inventario de demanda Sergio» midió 0 de 5 en
`W-02USSI`**, con el agravante de que allí los chats son `_chat.docx` y falla también la
segunda condición.

Lo que hace este dato incómodo es cómo apareció: en `W-02VEKE` los tres exports **sí**
quedaron excluidos y con su `duplicado_de`, así que el resultado final fue correcto — porque
**los excluí a mano** en el script de la corrida. El helper estaba inerte y su inercia no
dejó rastro: hice su trabajo sin notar que no lo hacía él. Dos casos, dos sesiones, cero
emparejamientos automáticos, y en uno de los dos el defecto quedó tapado por trabajo manual.
Ver [[feedback-guarda-inerte-comprobar-el-otro-valor]].

**Entrada hermana, y por qué NO se fusionan.** La causa en el censo es **`MEJORAS #205`**
(«Ruta `audio` en la sala de máquina», PR #311): `clasificar_ruta`
(`core/sala_maquina.py:47`) no conoce el audio, así que un `.opus` cae al `else` del despacho
y sale `sin_soporte` — 67 de los 73 `sin_soporte` de `W-02USSI` son audio, el 92%. Esta
entrada describe el **síntoma en el gate**, y **sigue siendo necesaria aunque la #205 se
construya**: las imágenes y los zips no van a tener espejo nunca, así que la señal seguiría
disparando. Cablear el audio reduce el ruido; no lo cierra.

El tercer dato de arriba, sobre `emparejar_exports_whatsapp`, vive en **`MEJORAS #206`** del
mismo PR, con el modo de fallo que aporta este caso: un helper cuya única señal de que no
funciona es que **no hay señal**.

**Disparador de promoción.** Medio. No corrompe datos ni bloquea: degrada el gate a ruido.
Sube en cuanto haya un segundo caso con export de WhatsApp, que es el flujo normal de los
expedientes de E&V.

## 198. `drive_accesible` está definida dos veces, con la misma condición y en dos sitios

**Qué pasa.** La decisión «¿se puede confiar hoy en el estado compartido del canon?» —que es
lo que el resolver del workspace recibe como `drive_accesible`— está escrita dos veces:

- `scripts/sala_maquina.py::_drive_accesible` (desde su Task 10)
- `core/procedimiento/sede.py::drive_accesible` (desde la pieza 4a, 2026-09-09)

Las dos leen `FEESDEFENDER_OFFLINE` y las dos devuelven lo mismo. La segunda se escribió a
sabiendas, porque la primera vive en un módulo de `scripts/` y un paquete de `core/` no puede
importar de ahí; y se **fijó con un test de no-drift**
(`tests/test_procedimiento_fachada.py::test_drive_accesible_no_DIVERGE_de_la_de_sala_de_maquina`)
en vez de dejarlas divergir en silencio.

**Por qué importa aunque hoy estén de acuerdo.** Dos definiciones de la misma decisión es
exactamente cómo nacen las divergencias, y el docstring de `WorkspaceRegistry` lo dice de otra
igual («dos definiciones de "bajo el catálogo" es como nacen las divergencias, y ésta ya había
nacido»). El test de no-drift avisa, pero no impide que alguien cambie una y actualice el test.

**Remedio.** Promoverla a un sitio común del que puedan tirar los dos —el candidato natural es
`core/casos/` , junto al resolver que la consume— y dejar en `sala_maquina` un alias. Es un
cambio de una línea en cada lado, pero toca un módulo ya revisado y mergeado, así que no entra
de rebote en el diff de otra pieza.

**Lo que NO hay que hacer, y está medido en el docstring de `sala_maquina`:** añadirle una
segunda condición del tipo «…o la raíz del catálogo no está montada». Se intentó, y produce
divergencia de fuente de verdad con `case_locator._root()` más un falso negativo en cualquier
clon o worktree sin `CASOS_ROOT` — donde **toda** invocación se iría a offline en silencio.

**Disparador de promoción.** Bajo. Hoy las dos coinciden y el drift está atado por un test. Sube
si aparece un tercer consumidor, porque entonces la duplicación deja de ser de dos.

## 199. `sync_sudespacho pull|intake-judicial` con un W-code CREA carpeta sombra en el Drive

**Medido el 2026-09-08 abriendo W-02USSI, sobre el Drive real del despacho.** El caso ya
existía, correctamente materializado en `CASOS\Barcelona\BaRS6 - … (W-02USSI) - Negativa
escritura`, con `meta.id_go: W-02USSI` en su `_caso.md`. Estos dos comandos:

```powershell
python -m scripts.sync_sudespacho pull --case W-02USSI --expediente 519 --element extrajudiciales
python -m scripts.sync_sudespacho intake-judicial --case W-02USSI --expediente 622 --full
```

**crearon `CASOS\W-02USSI`** —carpeta plana, hermana de `_ARCHIVO` y de las ciudades— y
depositaron ahí los 31 documentos del gestor documental, con su `_caso.md` (`case_id:
W-02USSI`, `id_go: null`), su `_intake_hashes.json`, su `_intake_log.jsonl` y su plantilla
de informe de viabilidad. **Los dos comandos salieron con código 0 e imprimieron
`documents_written: 9` y `22`.** El caso real quedó con `05_CRM` vacío.

**Por qué.** `case_locator.buscar(case_id)` resuelve **solo por nombre de carpeta**: prueba
`root/case_id`, luego `root/<ciudad>/case_id`, y devuelve `None`. **No mira `id_go`.**
`ensure_case` materializa en `destino_de_alta(case_id)`, que es `buscar(...) or root/case_id`
→ con un W-code el `or` gana y nace la carpeta plana. Los dos entrypoints de
`sync_sudespacho` pasan `--case` **crudo** a `ensure_case`, sin `resolve_ref` de por medio.

`scripts/export_label_emails.py` **no** tiene el defecto: hace `resolve_ref(args.ref)`
antes de tocar nada, y por eso su `--ref W-XXXXXX` sí funciona.

**El aviso que lo delata ya existe, y es el único síntoma antes del daño.** El
`intake-judicial` imprimió:

> `[aviso] este caso no declara W-code, así que el intake judicial NO va bajo el mutex`

Es falso sobre el caso real —declara `id_go`— y cierto sobre la carpeta que el propio
comando estaba a punto de crear: `_mutex_cli.w_code_de` usa `resolve_ref` (que no encontró
nada) mientras `ensure_case` usaba `buscar` (que tampoco, y creó). **Las dos funciones
discrepaban, y la discrepancia se imprimió como un aviso de mutex.** El segundo pull, ya con
el `case_id` completo, no lo imprimió.

**Familia conocida, arreglada en otro sitio.** El docstring de `destino_de_alta` nombra
literalmente este fallo —«devolver siempre la flat haría que un alta sobre un caso que ya
vive en su ciudad creara un duplicado plano al lado — el defecto CRÍTICO que R6 encontró en
el `--force` del `--modo v1`, una carpeta sombra con el W-code duplicado»— y lo cerró **para
`abrir_caso`**. `sync_sudespacho` se quedó fuera. Es el patrón de
`feedback-remediar-la-frontera-no-el-ejemplo`: se remedió el ejemplo (`abrir_caso`), no la
frontera (todo llamador de `ensure_case` con una referencia de usuario).

**Qué hacer.** La frontera, no el ejemplo: **`ensure_case` no debe aceptar una referencia sin
resolver.** Dos vías, la segunda es la buena:

1. Parche: `resolve_ref` en `pull` e `intake_judicial` antes de `ensure_case`. Arregla estos
   dos y deja la frontera abierta para el siguiente llamador.
2. Frontera: que `ensure_case` (o `destino_de_alta`) **falle en vez de crear** cuando la
   referencia tiene forma de W-code y no resuelve a ningún caso. Un alta legítima por W-code
   no existe: la vía de alta es `abrir_caso`, que sí trae identidad completa. Y añadir el
   guard: `buscar()` con algo que casa `^W-[A-Z0-9]{5,6}$` es un error de programación, no un
   caso nuevo.

**El guard de este CLI ya existe, está verde, y no puede dar el otro valor.**
`tests/test_guard_sync_cli_pull_v2.py::test_pull_deposita_en_05_crm_y_no_crea_el_layout_congelado`
corre el motor v2 real y comprueba el destino del pull — exactamente la propiedad que aquí
falló. Pasa porque su fixture elimina las dos condiciones necesarias a la vez:

- invoca `["pull", "--case", CASE_ID]` con el **case_id canónico**, nunca un W-code;
- y monta el caso **plano** en `tmp_casos_root / CASE_ID`, así que `buscar()` acierta en su
  primera rama (`root/case_id`) y la rama por ciudad —la que devuelve `None` y dispara el
  `or`— no se ejecuta nunca.

Es el patrón de `feedback-guarda-inerte-comprobar-el-otro-valor`: un guard que mide la
propiedad correcta sobre el único escenario en que no puede romperse. **La regresión tiene
que variar las dos cosas**: caso bajo `tmp_casos_root/<ciudad>/<case_id>` + `--case <w-code>`
→ assert que `tmp_casos_root/<w-code>` **no existe** y que el `05_CRM` del caso real tiene
los documentos. Y que **mida el disco, no el código de salida**: los dos comandos informaron
éxito con `documents_written` correcto — escribieron, y escribieron donde no tocaba.

**Coste real de este incidente.** Ninguno irreversible. La sombra se apartó renombrándola a
`_SOMBRA_W-02USSI_pull_mal_dirigido_2026-09-08` (el prefijo `_` la saca del espacio de
nombres de `buscar`), los 31 documentos se volvieron a bajar contra el `case_id` completo y
se verificó por contenido; **Nikolai borró la sombra del Drive el mismo 2026-09-08**, con lo
que se fue también su `_intake_log.jsonl` huérfano. Lo que queda es el defecto, no rastro
sucio.

**Disparador de promoción.** La próxima apertura de un caso que ya esté dado de alta en el
CRM antes de existir en el Drive — es decir, todas las que vienen de una reclamación
extrajudicial previa. Es el camino normal, no el raro.

---

## 200. El informe de viabilidad de E&V ya está en `00_Input` y `viabilidad-prerelleno` no lo sabe

**Medido el 2026-09-08 abriendo W-02USSI.** El fichero que E&V nombra
`<REF> - RECLAMACIÓN HONORARIOS PROFESIONALES.xlsx`, que vive en la subcarpeta
`_RECLAMACION` de la carpeta de la propiedad y entra al intake como
`00_Input/01_Drive EV/_RECLAMACION/…`, **es el informe de viabilidad** — el que rellena
Nikolai o su equipo, y el **ancestro** del informe de viabilidad de FeesDefender. Su primera
celda dice literalmente `INFORME DE VIABILIAD`.

Tres hojas, y cada una es el ancestro de una pieza distinta de FD:

| Hoja de E&V | Equivalente en FD |
|---|---|
| `INFORMACION` (REF, fecha, director/asesor captador y buscador, motivos de impago, precio, total honorarios, total deuda, semáforo JURÍDICO/FINANZAS, **`DATOS OPERACIÓN`**, `ACTIVIDADES`) | `Informe viabilidad - <W-code>.xlsx` |
| `PREGUNTAS` (guion de entrevista: captación, comercialización, visita, oferta, comunicación interna, agencia-vendedor, arras, team leader) | `_cuestionario_viabilidad.xlsx` |
| `DOCUMENTOS` (fichas y actividades GO3, exposés, reporte de visitas, las 4 comunicaciones de la oferta, negociación de arras) | ramo documental / `indice_documental.yaml` |

**La filiación está en el código, no en la palabra.** Las claves de hito que admite la skill
—`CUANTIA, ENCARGO, IDENT_PROPIETARIO, TITULARIDAD, HOJA_VISITA, OFERTA, IDENT_BUSCADOR,
ARRAS_ARRENDAMIENTO, RECON_HON_ARRAS, ESCRITURA, RECON_HON_ESCRITURA, RECLAMACION_JURIDICO,
RESPUESTA_RECLAMACION, OFERTA_VINCULANTE_CONFIDENCIAL`
(`.claude/skills/viabilidad-prerelleno/SKILL.md:141`, mismo orden en
`scripts/render_informe.py:41`)— son **fila por fila** el bloque `DATOS OPERACIÓN` de esa
hoja. El esquema de FD está calcado de ahí.

**El hueco.** La skill declara leer «toda la documental no anonimizada de `00_Input/`» y trata
los hitos de existencia documental como la pregunta «¿existe este documento concreto?»
(`SKILL.md:46`). No sabe que **un fichero del propio `00_Input` ya trae las respuestas del
consultor a esos mismos hitos**, con su score y su fecha. Resultado: re-deriva desde cero lo
que E&V ya contestó, y la única fuente del expediente que habla en las palabras del consultor
—la hoja `PREGUNTAS`— se lee como un `.xlsx` cualquiera.

**Y el repo no lo documenta en ninguna parte.** `grep -rn "RECLAMACI.N HONORARIOS
PROFESIONALES"` sobre `*.md` y `*.py` no devuelve **nada** (medido). Ni `SKILL.md`, ni
`CONVENCIONES_DESPACHO.md`, ni el runbook. El coste de no documentarlo se pagó el mismo día:
con el fichero ya dentro del intake que yo había corrido, declaré «el informe de viabilidad no
existe» porque busqué `name contains 'viabilidad'` y E&V no lo nombra así (memoria
`feedback-el-nombre-de-una-cosa-no-es-la-cosa`).

**Qué hacer.** Por orden de coste:

1. **Documentar la filiación** en `SKILL.md` de `viabilidad-prerelleno` y en el
   `RUNBOOK_APERTURA_EXPEDIENTE` (§8): este fichero es el informe, se llama así, vive en
   `_RECLAMACION/`, y se lee **primero**. Barato y cierra el fallo de nombrado.
2. **Cablearlo como fuente prioritaria** del pre-relleno: leer `INFORMACION` para cabecera
   (ref, fecha, los cuatro consultores por rol) y `DATOS OPERACIÓN` para los scores de hito,
   y usarlo como semilla en vez de partir de cero.
3. **Con dos cautelas medidas, no supuestas.** (a) El fichero **se copia del caso anterior**:
   en W-02USSI el bloque `DATOS OPERACIÓN` traía fechas de **2020-2022** sobre una operación
   íntegramente de 2025, y las cifras económicas leían 0 frente a 75.020 € reclamados. La
   cabecera era fiable; el bloque de hitos, no. Así que **sembrar no es creer**: cada score
   heredado tiene que cruzarse contra el ramo, y una fecha que no cabe en la cronología es una
   bandera a `AVISOS LLM`, no un dato. (b) La hoja `PREGUNTAS` puede estar **en blanco** sin
   que eso signifique que no hubo entrevista: en este caso la call se hizo (actuación CRM
   15306) y no se grabó, y el relato llegó meses después por correo.

**Disparador de promoción.** El próximo pre-relleno de viabilidad. El punto 1 se puede hacer
ya y no depende del 2.

---

## 201. Un `.rtf` con surrogates deja el espejo a 0 bytes, y `empty` no distingue «no tiene texto» de «no pude leerlo»

**Medido el 2026-09-08 en la sala de máquina de W-02USSI.** El mismo documento —la petición
inicial de monitorio, un `.rtf` de 1,7 MB— entró al caso por tres vías (el gestor documental
del CRM y dos adjuntos de correo). La copia del CRM se procesó bien: espejo de **26.318
bytes**. Las dos del correo salieron a **0 bytes** con esta nota en `_cobertura.json`:

```
fallo al procesar: 'utf-8' codec can't encode characters in position 10925-10930:
surrogates not allowed
```

Dos defectos, y el segundo es el que importa.

**(1) El extractor de `.rtf` muere ante surrogates sueltos.** Un par subrogado mal formado
—típico de emoji o de caracteres pegados desde Word/Outlook— revienta el `encode` al escribir
el espejo. LibreOffice headless convierte **el mismo fichero** a `.txt` sin protestar
(comprobado a mano en este caso), así que no es un `.rtf` corrupto: es el camino de escritura
del espejo, que necesita `errors="replace"` o `surrogatepass` — el mismo gotcha de encoding
que `CLAUDE.md` ya recoge para `subprocess.run` en Windows, aplicado al sitio equivocado.

**(2) Y el grave: `estado: "empty"` mezcla dos cosas que no son la misma.** En este caso el
recuento fue `ok 365 / sin_soporte 73 / empty 28 / low 5`, y dentro de esos 28 `empty`
convivían:

- una foto de WhatsApp, un sticker, un `_firma_image001.png` → **no tienen texto**, y `empty`
  es la respuesta correcta;
- y la demanda del caso → **sí tiene texto y no se pudo leer**.

Son estados distintos con consecuencias distintas: el primero no hay que arreglarlo nunca, el
segundo hay que re-correrlo. Hoy solo los separa leer la prosa del campo `nota`, y quien mira
el resumen ve un número que no distingue. **Hace falta un estado propio** —`fallo` o
`error_extraccion`— que salga en el recuento y en el pendiente de la apertura, al lado de
`ocr_documentos_agotados`, que ya existe justamente para «su texto NO está en el corpus».

**Por qué esta vez no dolió, y por qué no cuenta como que el sistema aguantó.** Aguantó **la
redundancia del intake, no el pipeline**: la copia del CRM sí extrajo, así que el corpus tiene
la demanda. Lo mismo pasó con otros dos documentos nucleares del caso, y por eso se ve el
patrón: `doc_09_carta_desistimiento.pdf` salió con **3 bytes** de texto pero el
`DESISTIMIENTO VENDEDOR.jpg` de la carpeta `_RECLAMACION` de E&V se OCR-izó a **3.335 bytes**;
y `doc_02_encargo_de_venta_firmado.pdf` salió `low` (1 de 2 páginas ciegas) mientras la copia
del encargo que venía **en el export de WhatsApp** extrajo **9.151 caracteres**. Tres
documentos críticos, tres rescates por una vía distinta de la esperada. **Si el caso hubiera
llegado por una sola fuente, los tres estarían mudos y el resumen habría dicho `empty`.**

**Qué hacer.** (a) `errors="replace"` (o `surrogatepass`) en la escritura del espejo de la
ruta `.rtf`, con un test que le dé de comer un `.rtf` con un surrogate suelto y compruebe que
el espejo **no** sale a 0 bytes; (b) estado propio para el fallo de extracción, contado
aparte de `empty` y elevado a pendiente de la apertura; (c) el aviso correlativo en
`_cobertura`: un documento cuyo espejo mide 0 bytes **y** cuya nota empieza por «fallo al
procesar» no puede presentarse con el mismo rótulo que un sticker.

**Disparador de promoción.** Cualquier caso cuyo documento nuclear llegue por una sola vía
—es decir, uno abierto solo desde el CRM, sin Drive de E&V ni WhatsApp—. Ahí el defecto (2)
deja de ser cosmético.

---

## 202. `verificacion-anclada-fuente/SKILL.md` lleva 359 bytes NUL commiteados, y ninguna verja lo mira

**Medido el 2026-09-08.** El fichero tiene **31.888 bytes**: 480 líneas de contenido legítimo
y, después de la última —«…Verifíquense los outputs contra la jurisdicción aplicable antes de
actuar.»—, **359 bytes `\x00` de relleno**. Está trackeado (blob `64f730f`), sin
`.gitattributes` que lo marque como binario.

El texto **decodifica bien como UTF-8** (31.304 caracteres), así que la skill no está
mutilada: lo que hay es una cola de basura, probablemente de una escritura truncada y
rellenada.

**El daño no es estético.** `file` lo clasifica como `data` y **`grep` lo trata como binario**,
así que la skill es **invisible a cualquier búsqueda por contenido** sobre `.claude/skills/`.
Medido en la misma sesión: el comando que leyó el `SKILL.md` de las otras veinte skills
devolvió `Binary file … matches` sobre esta, y hubo que rodearlo decodificando en Python y
quitando los NUL a mano. Una skill que no se puede `grep` es una skill que no se audita: no
sale en los barridos de cobertura, ni en los cruces de encadenamiento entre skills, ni en un
`grep` de un término que se quiera retirar del despacho.

**Y el hueco de fondo, que es el que hay que cerrar:** **ninguna verja comprueba hoy que un
`SKILL.md` sea legible como texto.** `scripts/check_skills.py` compara mtimes contra
`dist/skills/*.skill` (caducidad del empaquetado), no la sanidad del fuente. Así que este
fichero pudo entrar, commitearse y sobrevivir sin que nada protestara.

**Qué hacer.** (a) Reescribir el fichero sin la cola: leer, `.replace("\x00", "")`, escribir
en UTF-8 sin BOM con `[System.IO.File]::WriteAllText` (regla de encoding de `CLAUDE.md`);
verificar después con `file` y con un `grep` de un término del cuerpo. (b) El guard, que es lo
que impide la reincidencia: un test que recorra `.claude/skills/**/SKILL.md` y afirme, por
cada uno, que **no contiene `\x00`**, que decodifica como UTF-8 y que su frontmatter parsea.
Es barato y cubre de golpe una familia —caracteres de control, BOM, truncamiento— que hoy no
mira nadie. (c) Comprobar de paso si el empaquetado (`scripts/package_skill.py`) y el
importador del servidor toleran el NUL o lo estaban tolerando por suerte.

**Disparador de promoción.** Cualquier trabajo que toque `verificacion-anclada-fuente`, o el
próximo barrido de las skills — momento en que este fichero volverá a no aparecer.

---

## 203. `id_carpeta 304` sin mapear: los documentos del gestor documental judicial caen en `99_Sin categoria`

**Medido el 2026-09-08 abriendo W-02USSI.** `core/config.py::CARPETA_ID_TO_PATH` tiene
**cuatro** entradas:

```python
"1":   "General",
"307": "Civil/1ª Instancia/Declarativo/Demanda",
"308": "Civil/1ª Instancia/Declarativo/Oposicion",
"380": "Civil/Preliminares/Demanda",
```

La carpeta del gestor documental donde vive **toda la documental de la demanda** del
expediente judicial de este caso es `id_carpeta = 304`, etiqueta `DEMANDA` — leído del CRM
sobre el documento 38103: `carpeta value='304'`, `id_carpeta value='304' label='DEMANDA'`.
**No está mapeada.**

Consecuencia medida: de los 32 documentos del caso, los **23 del judicial** cayeron en
`00_Input/05_CRM/99_Sin categoria/622/` y los **9 del extrajudicial** en
`00_Input/05_CRM/99_Otros/`. **Ninguno** en el árbol `CRM_TREE`. Con `documents_written`
correcto y código de salida 0 en las dos corridas: el pull no falla, clasifica al cajón de
sastre.

**Por qué importa más de lo que parece.** No es cosmético ni es «un caso»: `304` es la carpeta
DEMANDA de los expedientes **judiciales**, o sea la de todos los casos que llegan a
contenciosa. Y cualquier consumidor que resuelva un documento por su ruta canónica —una skill
que busque el encargo en `Civil/1ª Instancia/…/Demanda`— no lo encuentra. Es la razón por la
que el diseño de `demanda-honorarios-ev` resuelve **por censo y por rol, nunca por ruta**
(spec del 2026-09-08, §6).

**Qué hacer, y qué NO hacer.** **No añadirlo unilateralmente.** El propio comentario de
`config.py` fija la **regla de doble verificación** («usuario en CRM UI + Claude vía REST»)
porque la etiqueta-hoja es ambigua entre ramas: `CRM_TREE` tiene
`Civil/1ª Instancia/Declarativo/Demanda` —ya ocupada por `307`— y
`Civil/1ª Instancia/Monitorio/Demanda`, y `DEMANDA` casa con las dos. El endpoint de árbol
`/api/folders/gdocu/{parent}` no devuelve la jerarquía (dead end §13.3), así que la rama solo
se cierra mirándolo en la UI. **Pendiente: que Nikolai confirme en el CRM a qué rama
corresponde `304`.** Con eso, una línea.

**Y el aviso que sí falta:** el evento `category_unknown` de `_intake_log.jsonl` existe
justamente para descubrir estos IDs, pero **nadie lo lee**. Los 32 documentos de este caso lo
emitieron y el operador no vio nada: la salida del pull dice `by_carpeta:
{"99_Sin categoria/622": 23}` sin señalar que eso **es** el síntoma. Merece un aviso explícito
en la salida del CLI: «N documento(s) sin categoría — `id_carpeta` no mapeado: 304».

**Disparador de promoción.** La próxima apertura de un caso con expediente judicial, que es
casi cualquiera que venga de una reclamación extrajudicial previa.

---

## 204. `cendoj-descarga`: un ECLI «normalizado» hace que la cita parezca inexistente

**Medido el 2026-09-09 verificando las siete citas de la demanda de W-02USSI.** CENDOJ
publica algunos ECLI de Audiencia Provincial **con un espacio dentro del código de órgano**:

```
ECLI:ES:AP B:2002:12928        <- así lo publica el CGPJ (SAP Barcelona, 18-12-2002)
ECLI:ES:APB:2002:12928         <- la forma «normalizada», que NO encuentra nada
```

Busqué por la segunda porque el escrito traía la primera y la tomé por errata. La búsqueda
devolvió **cero resultados y ningún error**, que es lo peligroso: se lee como «esta cita no
existe». Por **ROJ** (`SAP B 12928/2002`) salió a la primera, con el ECLI oficial confirmando
el espacio.

**El fallo no es de CENDOJ, es del método.** El Paso 3 de la skill pone la búsqueda por ECLI
como «Caso A — búsqueda directa. Devuelve siempre 1 resultado», y el ROJ como Caso B
alternativo. Con eso, un vacío por ECLI no tiene salida prevista, y la conclusión natural —la
equivocada— es la ausencia.

**Qué hacer.** (a) En el Paso 3, regla explícita: **un resultado vacío por ECLI nunca es
ausencia hasta haber reintentado por ROJ**; y no reescribir el ECLI que aporta la fuente —se
pega tal cual. (b) Una línea en la tabla de «Errores frecuentes»: `Búsqueda por ECLI sin
resultados` → `ECLI con espacio en el código de órgano (frecuente en AP antiguas)` →
`reintentar por ROJ; no normalizar el ECLI`. (c) Y el corolario general, que vale más que el
caso: **antes de declarar que una cita no existe, agotar la segunda llave.** Familia de
`feedback-no-lo-se-no-es-no-hay`.

**Disparador de promoción.** La próxima verificación de citas que incluya una AP anterior a
~2005, donde esta forma del ECLI es frecuente.
## 205. Ruta `audio` en la sala de máquina: 67 de los 73 `sin_soporte` son notas de voz

**Medido el 2026-09-09 sobre W-02USSI.** El censo tiene **471 documentos** y **73 en
`sin_soporte` (15,5%)**. De esos 73, **67 son audio o vídeo** — 65 `.opus` y 2 `.mp4`,
44,2 MB, ≈5,4 h de habla —, o sea el **92% del sin-soporte y 14,2 de los 15,5 puntos**.
Los 6 restantes son 5 `.zip` y 1 `.vcf`. Sus filas salen todas con `tipo: ''`,
`estado: 'sin_soporte'`, `chars: 0` y la nota genérica `sin soporte para esta extensión`.

`clasificar_ruta` (`core/sala_maquina.py:47`) enruta por extensión a `pdf` | `imagen` |
`nativo` | `ofimatica` | `sin_soporte`. Las extensiones de audio no están en ninguna lista,
así que caen al `else` del despacho (`core/sala_maquina.py:1406`) y **nunca se intenta nada**.

**Por qué importa más que un porcentaje.** El habla no es un formato secundario en este
dominio: en W-02USSI las notas de voz son de los chats con la parte compradora y con la
agente colaboradora, y la primera que se transcribió —25-07-2025, dos días después del
desistimiento— ya trae material del fondo del asunto que **no está en ningún documento
escrito del ramo**. Mientras la ruta no exista, la sala de lectura clasifica esos 67 «a
ciegas por nombre» y el `CRONOLOGIA.md` no los ve. Es el mismo agujero que `MEJORAS #61`
cerró para los `.doc`, en un formato donde el contenido pesa más.

**Es feasible hoy, y está medido.** Con `faster-whisper` 1.2.1 (CTranslate2 4.8.2 + PyAV
18.1.0) en un venv aislado: **no necesita el binario `ffmpeg`** —PyAV trae sus propias libs y
abre el `.opus` directo— **ni `torch`**. Modelo `small`, `device="cpu"`, `compute_type="int8"`,
`language="es"`, `vad_filter=True`: 137,9 s de audio → 2.096 caracteres en **79,7 s (×1,7
tiempo real)**, `language_probability` 1,00, carga del modelo 25 s. Extrapolado a las 5,4 h:
≈3,2 h de CPU. La calidad en castellano es utilizable tal cual; los nombres propios y los
tecnicismos salen mal («GuruFax» por «burofax»), que es exactamente el perfil que hay que
declarar y no maquillar.

**Forma correcta de la pieza — y esto es la decisión de diseño, no un detalle.** Se modela
sobre `ofimatica`, **no** sobre `--vision`. Son dos patrones distintos y confundirlos cuesta
un seam inútil:

- `--vision` necesita **la sesión Claude**, que el CLI no puede invocar por sí mismo. De ahí
  el stub `_transcribir_vision` con `_es_stub`, `vision_cableada()` y el preflight
  `_exigir_vision_cableada` que **aborta en alto** (`scripts/sala_maquina.py:283`).
- El ASR corre **entero en local, dentro del proceso**. No hay nada que inyectar. Es una
  **dependencia externa opcional**, igual que `soffice`: presente → se usa; ausente → el
  documento sale `sin_soporte` **con la causa real en la nota**, y el CLI avisa antes de
  procesar (patrón `_avisar_si_falta_soffice`, `scripts/sala_maquina.py:270`).

Piezas: (a) `core/audio_a_texto.py` espejo de `core/ofimatica_a_pdf.py` — `EXTS_AUDIO`,
`ENV_MODELO` (`FEESDEFENDER_ASR_MODELO`), `asr_disponible()`, `transcribir(src) -> str`;
(b) `_EXTS_AUDIO` y el `return "audio"` en `clasificar_ruta`; (c) la rama `elif d.ruta ==
"audio"` con `_audio_y_extraer`, que escribe el MD y su fila de cobertura como las demás;
(d) el aviso de preflight; (e) `faster-whisper` como **extra opcional**, nunca dependencia
dura de la suite.

**Dos cosas que la implementación no puede perder.** Primera: el MD debe llevar los
**segmentos sellados en tiempo** (`[mm:ss–mm:ss]`), porque en un escrito una nota de voz se
cita por minuto y segundo, no por página; y en cabecera el modelo, la duración y el
`language_probability`, para que se sepa **con qué instrumento** se leyó. Segunda: la
transcripción **no da la fecha de envío**. Esa vive en el cuerpo del chat (`<adjunto: …>`), y
la fecha incrustada en el nombre (`AUDIO-2025-07-25-11-54-55`) es la de **captura**, que la
skill `organizar-sala-lectura` ya obliga a no confundir con la de envío. La ruta de audio
resuelve el *texto*; el *cuándo* sigue siendo del chat.

**Y una honestidad de alcance:** `estado` para una transcripción no puede reusar
`ocr_quality` sin pensarlo. Un audio de 3 minutos con 2.000 caracteres es normal; un PDF de
una página con 2.000 caracteres también, pero los umbrales no son los mismos y un audio de
silencio devolvería `empty` cuando lo correcto es «no había habla». Hay que decidir el
criterio explícitamente, no heredarlo.

**Y una regla que hereda de MEJORAS #207, descubierta en la misma sesión:** un audio que **no
se pudo leer** no es un audio sin habla. La ruta debe comprobar que el origen sigue montado
antes de dar por fallido un fichero, y no debe producir un espejo vacío en un fallo de lectura
— si no, una caída del Drive a mitad de tanda deja 38 documentos con veredicto de un problema
que no era suyo.

**Disparador de promoción.** Ya está disparado: W-02USSI tiene 67 documentos ilegibles y la
demanda está sin presentar. Lo urgente del caso se cubre fuera del pipeline (transcripción en
scratchpad, fuera del repo, que es donde debe estar el dato real); lo que esta entrada pide es
que la **próxima** apertura no repita el trabajo a mano.

---
## 206. `emparejar_exports_whatsapp` solo conoce el nombrado de UN canal: 0 de 5 exports apartados

**Medido el 2026-09-09 sobre W-02USSI.** El Paso 1-bis.a0 de `organizar-sala-lectura` llamó a
`emparejar_exports_whatsapp` sobre las 441 rutas del intake y devolvió
**`exports_crudos_whatsapp: 0`**. En el corpus hay **5 `.zip` de export de WhatsApp, 152,3 MB**,
y los cinco se quedaron con **fila propia** entre los 410 únicos:

| bytes | ruta bajo `00_Input/` |
|---|---|
| 130.391.552 | `01_Drive EV/_RECLAMACION/WHATSAPP/WhatsApp Chat - Sofia Mata CB.zip` |
| 10.564.096 | `01_Drive EV/_RECLAMACION/WHATSAPP/WhatsApp Chat - Oferta Soria 32-34.zip` |
| 10.564.089 | `2026-09-08_email_01/…_oferta_soria_32_34/WhatsApp Chat - Oferta Soria 32-34.zip` |
| 871.424 | `01_Drive EV/_RECLAMACION/WHATSAPP/WhatsApp Chat - Joan C_ Soria.zip` |
| 871.402 | `2026-09-08_email_01/…_joan_c_soria/WhatsApp Chat - Joan C_ Soria.zip` |

**Por qué no salta, y las dos condiciones fallan por separado** (`preclasificar.py:106`). El
helper marca un `.zip` como crudo solo si **(1)** su basename es exactamente
`_export_original.zip` **y (2)** hay un `_chat.txt` en su mismo directorio. Aquí:

1. Los zips se llaman `WhatsApp Chat - <nombre>.zip` — el nombrado de **E&V** (espejo
   `01_Drive EV/`) y el del **lote de correo**, no el que deja `whatsapp_intake.deposit_export`.
2. Los chats extraídos son **`_chat.docx`**, no `_chat.txt`: E&V exportó a Word. Así que
   aunque el zip se llamara bien, el hermano no se encontraría.

**Esto no es un bug del helper: es su supuesto, y el supuesto es de un solo canal.** El
docstring lo dice a propósito — «un `.zip` con OTRO nombre (documentación aportada) se conserva
aunque comparta carpeta con un chat» — y esa conservadurismo es correcta. El hueco es que la
detección se ancló al nombrado de `whatsapp_intake`, y **el mismo export llega por tres vías**:
el intake propio, el espejo del Drive de E&V y el lote de correo. Dos de las tres no pasan por
`whatsapp_intake` y por tanto nunca llevan ese nombre.

**La frontera de la que esto es ejemplo** (y es la que hay que cerrar, no el caso): *un detector
de «crudo ya extraído» que identifica el crudo por el nombre que le pone UN productor*. El mismo
error, con otra cara, produjo el `casi-duplicado` que sí saltó: los pares de 871.424/871.402 y
10.564.096/10.564.089 bytes son **el mismo chat re-comprimido**, llegado por dos canales, con
`sha256` distinto — así que `dedup_por_sha` tampoco los une.

**Coste real medido.** Los 5 quedan `sin_soporte` en el censo (`chars: 0`), son 5 de las 73
filas sin soporte, y sin apartar entran al plan de copia con `0000-00-00` — que es exactamente
la basura de cronología que el helper existe para evitar. Y el de Sofia Mata son **130 MB** que
se copiarían a la sala para nada: su contenido ya está extraído, fichero a fichero, en el
directorio hermano.

**Qué hacer.** Reconocer el crudo por **lo que es, no por cómo se llama**: un `.zip` es export
crudo de WhatsApp si en su mismo directorio —o en un subdirectorio con su mismo nombre sin
extensión, que es la forma del espejo de E&V— existe un chat extraído (`_chat.txt` **o**
`_chat.docx`). Con eso los 5 se apartan y se anotan `duplicado_de` su chat, sin borrar nada.
Y hay que **verificarlo con un control positivo**: un test cuyo fixture use el nombrado de E&V
y `_chat.docx`, porque el fixture actual usa el del intake y por eso el hueco pasó verde.
Ampliar de paso `dedup_por_sha` no sirve aquí: el re-comprimido cambia los bytes; lo que une a
esos pares es el chat del que son crudo, no su hash.

**Segundo caso, medido por otra sesión el mismo día, y el defecto ahí quedó ENMASCARADO.** En
W-02VEKE el helper devolvió **0 de 3**: los exports se llaman `Chat de WhatsApp con
<nombre>.zip` y `WhatsApp Chat - <nombre> EV <localidad>.zip`, ninguno `_export_original.zip`.
Lo relevante es cómo acabó pareciendo correcto: los tres **sí** salieron excluidos con su
`duplicado_de` porque **quien montaba la sala los excluyó a mano** en el script de la corrida.
El helper estaba inerte, su inercia **no dejó rastro**, y el resultado correcto tapó el
defecto — alguien hizo su trabajo sin notar que él no lo hacía.

Así que el recuento no es «0 de 5 en un caso» sino **0 de 8 en dos casos y dos sesiones, cero
emparejamientos automáticos**, y en uno de los dos el fallo era invisible desde el resultado.
Eso sube la entrada de categoría: no es un hueco de cobertura de nombres, es un helper cuya
única señal de que no funciona es que **no hay señal**. Un contador de «N exports apartados»
en el informe del paso 1-bis lo habría delatado el primer día — el informe dice hoy
`exports_crudos_whatsapp: 0` y eso se lee igual que «no había ninguno».

**La misma frontera, en otro campo: el formato de FECHA que documenta el `SKILL.md` es más
estrecho que el real.** `organizar-sala-lectura/SKILL.md:279` dice que la línea del adjunto
lleva `[DD/MM/AAAA, HH:MM]`. Medido sobre el export de W-02USSI, lleva **`[26/6/25,
12:07:45]`**: día de 1-2 dígitos, mes de **1**, año de **2**, y segundos que el contrato no
menciona.

**Hoy no rompe nada, y conviene decirlo así:** ningún regex de `core/`, `scripts/` ni de las
skills se ancla a `\d{2}/\d{2}/\d{4}`; las dos implementaciones que se escribieron contra
esto —en dos sesiones distintas y sin coordinarse— usaron `\d{1,2}/\d{1,2}/\d{2,4}`, que
admite las dos formas. El defecto es del **contrato documentado**: quien escriba el matcher
leyendo el `SKILL.md` en vez de mirar un export produce un regex que no casa **ni una** línea,
y el modo de fallo es el mismo de esta entrada — silencio, no error. Remedio de una línea:
que el `SKILL.md` documente `[D/M/AA, HH:MM(:SS)]` y diga que **el ancho varía por export**.

**Y el método SÍ funciona, con control positivo en dos casos.** Recuperar la fecha de envío
desde el cuerpo del chat en vez de del nombre del fichero dio **67 de 67** en W-02USSI y
**118 de 118** en W-02VEKE (117 `.opus` + 1 `.m4a`), en otro export y otro volumen:
**185 de 185**.

**La población, que hay que decirla o el número engaña:** son los adjuntos de **audio y
vídeo**, no todos los adjuntos del chat — de los PDF, imágenes y ofimática de esos mismos
exports no se ha medido nada. En W-02USSI está además cerrado **en los dos sentidos** (los
chats citan exactamente 11 y 56 adjuntos de audio/vídeo, todos inventariados: ni uno citado
sin fichero ni un fichero sin cita) y con control positivo sobre la comparación de fechas —
desplazando artificialmente la del nombre un día, el comparador responde `false` en 67/67, así
que el «cero discrepancias» no es una guarda inerte. Lo que falla es el formato documentado,
no la regla.

*(Las dos cifras se afinaron entre sesiones: la de W-02VEKE nació de un `grep -c opus` que
contaba 118 porque la línea 118 era **la propia nota** que decía que los `.opus` no estaban
fechados. El total sale igual por casualidad —117 `.opus` más un `.m4a`—, y esa casualidad es
justo la que convierte un recuento mal hecho en un número que nadie revisa.)*

**Disparador de promoción.** Cualquier caso cuyo WhatsApp llegue por el espejo del Drive de E&V
o por lote de correo, que son la mayoría — W-02USSI ya lo hizo por las dos, y W-02VEKE por una
tercera vía de nombrado.

---
## 207. El presupuesto de reintentos se gasta en una causa que no es del documento

**Medido el 2026-09-09, en vivo, sobre W-02USSI.** Una tanda larga de transcripción que leía
`.opus` desde `G:` iba por el fichero 18 de 56 cuando **`G:` (Drive Stream) se colgó**. Los 38
restantes fallaron uno a uno con `FileNotFoundError`. Al comprobarlo después: el directorio
respondía `Permission denied`, `Test-Path "G:\"` daba **`Access to the path 'G:\' is denied`**,
la raíz de `CASOS` listaba **0 entradas**, había **cuatro procesos `GoogleDriveFS`** y hasta
`Get-PSDrive -PSProvider FileSystem` **se colgaba 120 s**. No era el fichero: era el volumen.

**El síntoma miente sobre la causa.** Un `FileNotFoundError` por fichero se lee como ruta mala
o fichero ausente. Lo que había pasado es global, y la prueba es que **los 18 que sí se
procesaron tampoco eran visibles después** — ni los que fallaron ni los que no.

**Qué hace hoy la sala de máquina en esa situación** (verificado en el código, no supuesto):

1. `core/sala_maquina.py:1408` captura **cualquier** excepción por documento y escribe la fila
   `tipo: "error"`, `estado: "empty"`, `chars: 0`, `nota: "fallo al procesar: …"`. El
   comentario —«cualquier fallo del documento: no tumbar el lote»— es correcto para un PDF
   corrupto y es justo lo que no conviene cuando la causa es del volumen.
2. **Nada distingue una causa global de una del documento.** No hay comprobación de que el
   origen siga montado; el único `except OSError` cercano (`:1479`) trata la desaparición de un
   fichero como carrera entre el `rglob` y el `stat`, no como caída del montaje.
3. **Lo que sí está bien y hay que decirlo:** `_exitosos_por_bundle`
   (`scripts/sala_maquina.py:333`) marca hecho un documento **solo si salió `ok`/`low`**, así
   que un fallo **no** se cachea como éxito y **se reintenta** en la corrida siguiente. El
   censo no queda envenenado de forma inmediata.

**El hueco, entonces, es estrecho y es este:** `scripts/sala_maquina.py:962` suma **`+1` al
contador de intentos de cada documento que se procesó y no salió bien**, y con
`MAX_INTENTOS = 3` (`core/sala_maquina.py:214`) el sha pasa a `agotados` y **se salta hasta que
alguien use `--force`**. Es decir: **tres caídas del Drive gastan el presupuesto de reintentos
de documentos que nunca fueron ilegibles.** El tope existe para que nada bucle, y su docstring
ya advierte del riesgo —«saltarse algo en silencio es el defecto que este tope podría
introducir si nadie lo cuenta»—; el CLI **cumple** esa parte y avisa (`:806`, `:907`). Lo que no
está cubierto es que **el intento se cobre a quien no tiene la culpa**. Hoy, en W-02USSI, 38
documentos van con 1 de 3.

**La frontera de la que esto es ejemplo:** *aislar el fallo por unidad de trabajo supone que la
causa es de esa unidad.* Cuando la causa es del entorno compartido —el volumen, la red, el
binario externo—, el aislamiento convierte un fallo en N veredictos. Mismo patrón que el aviso
de `soffice` (`:270`), que precisamente se resolvió al revés y bien: **se comprueba la
dependencia ANTES de procesar**, y se avisa una vez en vez de N notas por documento.

**Qué hacer.** (a) Un centinela de salud del origen —`00_Input` existe y no está vacío— que se
consulte **antes de cobrar un intento**; si el origen no responde, la corrida **para y lo
declara**, en vez de recorrer el resto marcando fallos. (b) Que el contador solo suba cuando el
origen esté vivo. (c) Que la nota del censo diga **cuál de las dos causas** fue, porque hoy
`fallo al procesar: [Errno 2]…` no permite distinguirlas al leer el `_cobertura.json` después.
(d) Heredarlo en la ruta `audio` de **MEJORAS #205**: un audio que no se pudo leer no es un
audio sin habla. Ya está implementado y probado fuera del repo, en el script de reanudación de
esta sesión, con las tres reglas: comprobar el volumen antes de rendirse, no producir salida
en un fallo de lectura, e idempotencia por existencia de la salida.

**Disparador de promoción.** La próxima corrida de `sala_maquina apply` sobre un caso grande en
`G:` — que es el caso normal, no el excepcional.

---
## 208. `WorkspaceRegistry` no tiene modo de lectura no mutante, y por eso un lector necesita un preflight

**Qué pasa.** `WorkspaceRegistry._leer` (`core/casos/workspace_registry.py:170-180`) pone en
**cuarentena** un JSON ilegible antes de lanzar: lo renombra a `<fichero>.corrupto.<fecha>` con
`os.replace`. Para su módulo es la decisión correcta —preserva la evidencia y no borra nunca— pero
significa que **una lectura provoca una escritura**, y eso rompe el contrato de cualquier consumidor
que declare no escribir.

Lo destapó la R1 del diff de la vista procesal 4a (su H-05), demostrándolo: con el arranque de la
fachada arreglado, resolver un caso para un informe renombraba el registro sin haber llegado siquiera
a exigir `READ_CASE`.

**Cómo está mitigado hoy, y qué no cubre.** `core/procedimiento/sede.py::registro_legible` comprueba
los `*.json` del registro **antes** de que el resolver los lea, y falla con un mensaje que dice qué
pasa y qué hacer. Cubre el caso práctico —un registro corrupto que ya está ahí— y **no cierra la
ventana**: entre el preflight y la lectura real del resolver, el fichero puede corromperse y la
cuarentena ocurriría igual.

**Remedio.** Un modo de lectura no mutante en `WorkspaceRegistry` —un `cargar(..., cuarentena=False)`
o un `inspeccionar()` que informe sin mover bytes— y que los lectores lo usen. Con eso el preflight
duplicado de `sede.py` sobra y desaparece la ventana.

**Lo que NO hay que hacer:** quitarle la cuarentena. Es correcta para quien escribe, y un registro
ilegible es evidencia que no se borra. Lo que falta es poder **leer sin ejercerla**.

**Disparador de promoción.** Bajo. La ventana es estrecha y el preflight cubre lo que pasa en la
práctica. Sube si aparece un segundo consumidor de solo lectura, porque entonces el preflight habría
que duplicarlo otra vez.

---

## 209. Crear actuaciones en el CRM no tiene helper: la receta vive en prosa y se reescribe a mano cada vez

**Qué pasa.** El 2026-09-10 se creó a mano, con `urllib` en un heredoc, una actuación
`TA - CONTROL DICTADO SENTENCIA` colgada del expediente judicial de `W-02VEKE`, y se corrigió su
cuantía. Funcionó, y quedó documentado en `INTEGRACION_SUDESPACHO.md §15.6`. Pero **no hay ni una
función en `core/` que lo haga**: `core/sudespacho_create.py` crea expedientes, clientes,
contrarios y colaboradores; `core/sudespacho_relations.py` vincula; **actuaciones no está**.

**Por qué importa ahora y no antes.** Nikolai avisó ese mismo día de que va a pedir crear
actuaciones **cada vez más**, y nombró el destino: la **F3 del intake de procuradores**, que tiene
que crear la actuación **derivada de la notificación recibida**. Es decir, esto deja de ser un
gesto manual y pasa a ser un paso de pipeline.

**Los cinco pasos que el helper tiene que encapsular** —y cada uno es un sitio donde equivocarse:

1. **Resolver `(elemento, id)` del expediente**, no el número a secas. En `W-02VEKE`, `464` es de
   `extrajudiciales` y `540` de `expedientes_judiciales`, y `GET expedientes_judiciales/464`
   devuelve **200 con un expediente de otro caso**. El par correcto está en `_caso.md`, bajo
   `sudespacho_expedientes`.
2. **Aprender el `id_predefinido`** filtrando una instancia real por su asunto literal: el
   catálogo de predefinidas **no se expone como elemento REST**. Medido: `TA - CONTROL DICTADO
   SENTENCIA` → `84`.
3. **`profesional_asignado` es el username** (`ana.velastegui`), no el id de `empleados`.
4. `POST element_register/actuaciones`.
5. `POST relation_element/{elemento}/{exp}` con `["right.actuaciones.{id}"]` — **sin esto la
   actuación queda huérfana y el paso 4 devuelve `201` igual**.

**Y el verificador, que es la mitad del valor.** La comprobación válida es releer **del lado del
expediente** con el filtro `associated`; filtrar por el `id` de la actuación devuelve **404**
aunque exista. Un helper que devuelva el id sin comprobar la vinculación reproduce exactamente el
modo de fallo que documenta el §15.2.

**Forma candidata.** `core/sudespacho_actuaciones.py` con dos funciones puras y una de IO:
`resolver_predefinida(asunto) -> id | None` (lectura), `crear_actuacion(exp_elemento, exp_id, ...)
-> Actuacion` (los dos POST más la relectura de verificación, devolviendo el estado real de la
vinculación y no solo el id), y un DTO con los campos que el CRM acepta de verdad. Cablearlo
después en F3.

**Cómo comprobarlo sin engañarse.** El test tiene que cubrir el caso en que **el segundo POST
falla y el primero no**: hoy eso deja basura en el CRM sin que nadie se entere. Y un test que
muerda la confusión de elementos: pedir `expedientes_judiciales` con un id que solo existe en
`extrajudiciales` **no** debe dar por bueno el registro que vuelva.

**Disparador de promoción.** Alto en cuanto se retome **F3 del intake de procuradores** —es su
prerequisito real, no un adorno—, o en cuanto la creación manual se repita una tercera vez. Hasta
entonces la prosa del §15.6 basta para hacerlo a mano sin volver a descubrir las trampas.

---

## 210. `transcribir_audio` sale con código 0 cuando le falta su dependencia, e imprime el resumen como si hubiera transcrito

**Medido el 2026-09-10**, con un juicio a hora y media y quince audios que hacían falta para la
vista. `python -m scripts.transcribir_audio <carpeta> -s <salida>` con el intérprete del venv del
repo —que **no** tiene `faster-whisper`, porque vive en el venv dedicado `~/.venvs/asr`— imprimió:

```
ModuleNotFoundError: No module named 'faster_whisper'
15 fichero(s) · modelo large-v3-turbo · diarización no
[exited with code 0]
```

**Tres cosas mal en cuatro líneas.** El traceback va a stdout/stderr pero **no cambia el código de
salida**; la línea de resumen dice «15 fichero(s)» cuando se generaron **cero**; y `exit 0` hace
que cualquier `&&` posterior —o un paso de pipeline— dé el trabajo por hecho. Lo que delató el
fallo no fue el código de salida: fue contar los `.md` de la carpeta de salida y encontrar 0.

**Es la familia de [[feedback-no-lo-se-no-es-no-hay]] aplicada al código de salida**, y el propio
repo ya la remedió una vez en `preparar-residuo` con la decisión escrita: *«el estado "no pude
mirar" sale con código distinto de 0. Un aviso con salida 0 es la versión engañosa»*. Aquí no se
instaló. Ver también [[feedback-verificar-por-resultado-en-mi-herramienta]].

**Remedio.** Tres líneas, y las tres importan:

- El `ImportError` de `faster_whisper` sale con **código propio distinto de 0** y con el mensaje
  orientado a la causa: *«falta faster-whisper; este script se corre con `~/.venvs/asr/Scripts/python.exe`,
  ver `docs/INSTALACION_ASR.md §2`»*. Hoy el remedio está en la doc y el script no lo dice.
- La **línea de resumen se emite al final y con lo realmente producido**, no con lo enumerado al
  principio: «15 enumerados, 0 transcritos» en vez de «15 fichero(s)».
- Si `transcritos == 0` y `enumerados > 0`, **salida distinta de 0** aunque no haya habido
  excepción.

**Cómo comprobarlo sin engañarse.** El test tiene que invocar el script con un intérprete o un
entorno **sin** la dependencia y afirmar que el código de salida **no es 0**; verlo rojo contra el
código actual antes de arreglarlo. Un test que solo compruebe el camino feliz pasa hoy y pasaría
después.

**Disparador de promoción.** Alto en cuanto la transcripción se encadene a otro paso
(`MEJORAS #205`, ruta `audio` en la sala de máquina): ahí un `exit 0` mentiroso deja el expediente
sin transcripciones y con el pipeline diciendo que fue bien. Suelto y a mano, se nota enseguida.

---

## 211. `registrar_outputs` no actualiza la fila que ya existe en el `_index.md`, y devuelve éxito igual

**Medido el 2026-09-10.** Tras sustituir `05_Procedimiento/CONCLUSIONES_W-02VEKE.docx` por la
versión usada en la vista —118.378 bytes frente a 19.793, otro `sha256`— se volvió a registrar con
`registrar_outputs.py` pasándole `estado: "presentado"`, la fecha del día y las fuentes nuevas. El
script imprimió sus dos líneas de éxito y **no tocó la fila**: el `_index.md` seguía diciendo

```
| `CONCLUSIONES_W-02VEKE.docx` | conclusiones | actora | 2026-09-09 | … | borrador |
```

para un fichero que ya era el definitivo. Hubo que editar la fila **a mano**.

**Por qué es más grave de lo que parece.** El `_index.md` es el manifiesto del que se lee «qué hay
en esta fase del expediente», y aquí afirmaba `borrador` de un documento presentado en juicio. Es
[[feedback-corregir-el-doc-y-no-su-indice]] con el agravante de que **el registrador es justo la
herramienta que existe para que el índice no quede rancio**, y su idempotencia por nombre lo
convierte en lo contrario: un no-op silencioso.

**El modo de fallo, en una frase:** idempotencia por **clave** (el nombre) cuando el contenido ya
ha cambiado, sin comparar el `sha256` ni avisar.

**Remedio candidato.** Al encontrar la fila, comparar: si el `sha256` del fichero difiere del
registrado —o si difieren `estado`/`fuentes`/`meta`—, **actualizar la fila y decirlo**
(`[registrar_outputs] fila actualizada: CONCLUSIONES_W-02VEKE.docx (borrador → presentado)`). Si
todo coincide, el no-op actual es correcto, pero también debería decirse. Requiere que el índice
guarde el `sha256`, que hoy no está en la tabla: eso es parte del arreglo, no un extra.

**Cómo comprobarlo sin engañarse.** Registrar dos veces el **mismo nombre con contenido
distinto** y afirmar que la segunda deja la fila con el estado nuevo; verlo rojo contra el código
actual. Un test que registre dos veces el mismo fichero idéntico pasa hoy.

**Disparador de promoción.** Medio-alto: cualquier documento que se rehaga tras su primer
registro —conclusiones, minutas, escritos que van por versiones— deja el índice mintiendo. Y
`preparacion-juicio-oral` y `escritos-judiciales` **registran por nombre canónico estable**, que
es exactamente el caso que lo dispara.

---
## 212. Generar un documento desde plantilla del CRM no vive en `core/`: se improvisa cada vez

**Qué pasa.** El 2026-09-10 se generó la respuesta al requerimiento del W-04A6LI desde la
plantilla 243 del CRM y se subió al gestor documental del expediente 638, todo por API y todo
con **scripts de scratchpad** que se tiran al cerrar la sesión. En el repo no queda nada: ni el
render, ni el injerto del cuerpo en el RTF, ni el alta del letrado contrario.

Lo que falta, concretamente:

- **`core/crm_documentos.py`** (o el módulo que corresponda): `catalogo_plantillas(element)`,
  `renderizar(id_plantilla, element, id_elemento) -> bytes RTF` y
  `subir_al_gestor(ruta, exp_id, element, asunto)` encadenando el flujo de tres pasos del §17,
  con la verificación por sha256 de ida y vuelta ya dentro (hoy la escribí a mano cada vez).
- **`link_abogado_contrario(exp_id, abg_id)`** y `ensure_abogado_contrario_vinculado(...)` en
  `core/sudespacho_relations.py`, que hoy solo cubre `clientes_contrarios`, `clientes_propios`,
  `procuradores_propios` y `colaboradores`. Sin el vínculo, la plantilla genera el
  encabezamiento **en blanco**, que es un fallo silencioso.
- Un lector paginado que entienda **las dos formas de respuesta** de esta API
  (`items`/`itemsPerPage` y `elementRegistries`/`maxResults`) y que cruce lo leído contra el
  `totalItems` declarado. El que escribí a mano devolvió **0 sobre una tabla de 332** sin dar
  error; ese defecto es reproducible y merece un test.

Contrato ya documentado y medido: `INTEGRACION_SUDESPACHO.md` **§10.11** (plantillas de
documento), **§10.12** (`abogados_contrarios`) y **§17** (subida en tres pasos).

**Por qué no es cosmético.** El coste real de esta sesión no fue redactar: fue redescubrir. La
subida estaba en la §17 desde el día anterior y aun así tropecé con el mismo
`500 Missing mandatory properties` que la §17 documenta. Un módulo con su test convierte eso en
una llamada.

**Disparador de promoción.** Medio. Sube en cuanto haya un **segundo** asunto que necesite
generar un documento desde plantilla, o si se quiere encadenar «generar → subir → enviar
certificado» sin intervención manual. Mientras sea uno al mes, el scratchpad cuesta menos que
el módulo.

**Misma frontera que `MEJORAS #209`** («crear actuaciones en el CRM no tiene helper: la receta vive en prosa y se reescribe a mano cada vez»), que entró el mismo día por el PR #316. Son dos ejemplos de una sola propiedad mal cerrada: **el contrato del CRM se documenta y no se encapsula**, así que cada operación nueva se reescribe a mano contra la prosa. Si se aborda una, abordar la frontera: un módulo por familia de operación, no un helper por caso.

---

## 213. La guarda de alineación CRM ↔ caso compara por IGUALDAD EXACTA, y la convención del campo ya no es el `case_id`

> **El dato del 638 ya está repuesto (2026-09-10, decisión de Nikolai: vía (e)).**
> `PUT /api/element_register/extrajudiciales/638 {"Referencia_Cliente": "<case_id>"}` → HTTP 200, y
> verificado **por relectura de los 27 campos**: la referencia vale el `case_id`, **cero campos
> colaterales cambiados** (`Notas` intacta, 2.389 caracteres antes y después — el `PUT` parcial de
> §10.7 se cumplió). Con eso vuelven a verde las cuatro consecuencias medidas:
> `verify_expediente_referencia` → `match=True`; `find_expediente_by_referencia` → `'638'`; y el
> expediente vuelve a salir buscando `Calle 31`, `VaRS3` y `Devolucion honorarios`. El `_caso.md`
> deja de mentir sin haberlo tocado.
>
> **Lo que sigue vivo de esta entrada, y es lo que importa:** (1) el **retoque manual** de las dos
> apariciones del campo en cada documento que se genere de la plantilla 243 — mientras nadie lo
> haga, la carta vuelve a decir «el inmueble sito en VaRS3 - Calle 31, 6 (W-04A6LI) - Devolucion
> honorarios»; y (2) **(a)**, que la guarda sepa comparar por W-code, que no era el arreglo de este
> caso. Editar la plantilla queda **descartado**.

> Medido el 2026-09-10 sobre el extrajudicial **638** (`W-04A6LI`), preguntando «por qué este
> expediente no tiene referencia canónica». **El campo no estaba vacío: tenía `W-04A6LI` pelado.**

**Qué pasa.** `Referencia_Cliente` del 638 vale `'W-04A6LI'`, no
`'VaRS3 - Calle 31, 6 (W-04A6LI) - Devolucion honorarios'`. No lo hizo el código: ni
`abrir_caso.crm_payload` (`core/abrir_caso.py:285`) ni la UI (`streamlit_app.py:2440`) envían otra
cosa que el `case_id`, y el alta del 93º cierre fue por la vía V1. **Se acortó a mano el
2026-09-10, y por una razón buena**, escrita en `INTEGRACION_SUDESPACHO.md` §10.11: la plantilla
243 (`BUROFAX - ENGEL - DEVOLUCION HONORARIOS - VENTAS`) vuelca
`[extrajudiciales->Referencia_Cliente]` **a la vez** en la línea `REF:` y en la frase «el inmueble
sito en …», así que con el `case_id` dentro la carta decía «el inmueble sito en VaRS3 - Calle 31, 6
(W-04A6LI) - Devolucion honorarios». La §10.11 zanjó: «se deja el `W-XXXXXX`».

**El problema no es el acortado: es que nada más se enteró.** Medido en vivo contra el CRM:

| Comprobación | Resultado |
|---|---|
| `verify_expediente_referencia(638, 'extrajudiciales', expected=case_id)` | `match=False`, `found=True` |
| `_rest_search_expedientes('extrajudiciales', case_id)` | `[{'id': '638', 'label': 'W-04A6LI'}]` — **sí lo encuentra** |
| `find_expediente_by_referencia(case_id)` | `None` — `_match_in_results` exige label idéntico |
| `wcode_match('W-04A6LI', case_id)` | `True` |
| `buscar_expedientes_duplicados(w_code='W-04A6LI')` | bloquea igual: ancla en el W-code |

Consecuencias, por orden de coste:

1. **Falsa alarma perpetua.** `scripts/sync_sudespacho.py:210` imprimirá «⚠️ Referencia
   desalineada CRM ↔ caso local» en **cada** pull del 638, y `scripts/audit_referencias_casos.py`
   sale con **código 1** por este caso. Una guarda que grita sobre una decisión deliberada se
   contesta por rutina y deja de proteger — el mismo modo de fallo que el `--force` rutinario que
   describe `buscar_expedientes_duplicados`.
2. **El `_caso.md` miente.** Sigue con `referencia_crm: VaRS3 - Calle 31, 6 (W-04A6LI) -
   Devolucion honorarios`, que no es lo que el CRM dice. Es **otra instancia de `#192`** (el campo
   que dice ser «la referencia del CRM» se rellena con el nombre local y nunca se relee), esta vez
   con el CRM moviéndose *después* del alta en vez de antes.
3. **`find_expediente_by_referencia` queda ciego** para este expediente. Hoy no tiene llamador de
   producción fuera del módulo, así que es latente, no activo.

**El censo, para no exagerarlo.** De los **611** extrajudiciales del tenant: 398 llevan el W-code
dentro de una referencia larga, **1 lo lleva pelado** (el 638), 50 no tienen referencia y 162 no
tienen W-code (asuntos no-FeesDefender, `PRUEBA - BORRAR`, referencias `BCN-RS-…` del CRM de E&V).
El acortado es **un caso**, no una convención implantada. Y ahí está la decisión pendiente.

**La frontera, no el ejemplo:** un mismo campo sirve a dos consumidores con exigencias
incompatibles — la **plantilla**, que lo intercala en prosa y quiere el código corto, y la
**guarda de alineación**, que lo compara con el nombre de la carpeta y quiere el `case_id` entero.
Cualquier remedio que arregle solo el 638 deja la colisión viva para el segundo burofax que se
genere.

**El mecanismo, con la plantilla delante** (medido el 2026-09-10, `GET
/api/templates/rtf/detail/243` → RTF de 1.631.790 bytes, y el render read-only de la 243 sobre el
638). El marcador `[extrajudiciales->Referencia_Cliente]` aparece **dos veces** en el cuerpo de la
plantilla, y la segunda es la que muerde:

```
[1]  REF: [expedientes_judiciales.referencia_cliente] - [extrajudiciales->Referencia_Cliente]
[2]  …por la mediación en el contrato de compra del inmueble sito en
     [expedientes_judiciales.referencia_cliente] [extrajudiciales.Referencia_Cliente]
     (en adelante, el "Inmueble")…
```

Renderizado hoy contra el 638, las dos salen `W-04A6LI` (y el marcador judicial sale vacío por ser
un extrajudicial, de donde el guion suelto del `REF:`). **Quien escribió la plantilla usó el campo
de la referencia como si fuese la dirección del inmueble**: no es que el `REF:` se contamine, es que
la frase del cuerpo nombra la finca con ese campo. De ahí que el `case_id` entero, que es lo
correcto como llave, se leyera como una barbaridad dentro de la carta.

**Lo que cuesta el campo corto, medido.** `_rest_search_por_texto('extrajudiciales', …)` busca solo
sobre `Referencia_Cliente`, luego el 638 dejó de ser localizable en el CRM por cualquier cosa que no
sea su W-code:

| Se busca | ¿sale el 638? |
|---|---|
| `Calle 31` | **no** |
| `VaRS3` | **no** |
| `Devolucion honorarios` | **no** |
| `W-04A6LI` | sí |

Para quien busque en la UI por calle, por equipo o por tipo de asunto, ese expediente se ha vuelto
invisible. Ese es el precio real, y es mayor que el aviso ruidoso del pull.

**Remedios candidatos.**

- **(b) Editar la plantilla — DESCARTADO por Nikolai el 2026-09-10.** El RTF es un fichero
  (`downloadUrlRtfFile` en S3) y sería editable, pero no se tocan las plantillas del cliente. Queda
  escrito para que nadie lo vuelva a proponer como si fuese gratis.
- **(e) Retocar el DOCUMENTO, no la llave** — la vía que queda abierta y la más barata.
  `Referencia_Cliente` vuelve al `case_id` (una escritura sobre el 638) y las dos apariciones se
  corrigen a mano en el `.docx` renderizado. El flujo ya exige retoques manuales por documento
  —los `XX` de precios y porcentajes, el `[XX]` de la ciudad, el borrado del comentario de Word
  `{\*\annotation}`—, así que son **dos reemplazos más sobre un documento que ya se abre a mano**.
  A cambio: la guarda y la auditoría vuelven a verde solas, el `_caso.md` deja de mentir, y el
  expediente vuelve a ser buscable por calle. Es el remedio recomendado.
- **(a) Que la guarda compare por W-code.** `wcode_match` ya existe en el módulo y ya lo usa el
  dedup; `verify_expediente_referencia` devolvería un tercer estado —`match_wcode`— y el pull lo
  imprimiría como «coincide por W-code; la referencia del CRM es más corta». **Vale la pena aunque
  se aplique (e)**: no es el arreglo de este caso, es que la guarda hoy solo sabe decir «idéntica»
  o «desalineada», y la referencia del CRM puede divergir legítimamente del nombre de la carpeta
  (sufijos distintos, ya visto en el 464/540 de `W-02VEKE`).
- **(c) `Referencia_Propia`** está vacía en el 638 y es `TextCorto`: sería el sitio natural de la
  dirección para la plantilla, pero la 243 **no la lee** (0 ocurrencias del marcador en el RTF), así
  que sin editar la plantilla —descartado— no sirve. Anotado para no volver a mirarlo.
- **(d) Reponer el `_caso.md`.** Con (e) se resuelve por sí solo: si el campo del CRM vuelve al
  `case_id`, lo que dice el `_caso.md` pasa a ser verdad sin tocarlo. Si se decidiera dejar el campo
  corto, entonces hay que reponerlo —o vaciarlo, que es la salida honesta de `#192`.

**Cómo comprobarlo sin engañarse.** El control positivo y el negativo están los dos a mano:
`verify_expediente_referencia` sobre el 638 con `expected=case_id` debe dar `False` hoy y `True`
tras (e); y sobre cualquiera de los 398 con referencia larga debe seguir dando `match=True`. Un test
que solo mire el 638 aprueba un comparador que haya dejado de comparar.

**Disparador de promoción.** Para (e), inmediato: es una escritura y dos reemplazos, y mientras no
se haga hay un expediente vivo no buscable por dirección. Para (a), medio: sube con el **segundo**
burofax desde plantilla —el flujo que `#212` quiere encapsular— o con el primer expediente cuya
referencia del CRM divirja del nombre de la carpeta por sufijo.

## 214. Todo lo que se escribe en `G:` sale rellenado con ceros a múltiplo de 512, y el `sha256` forense deja de ser el del original

> Medido el 2026-09-10 abriendo `W-048UOL`, al cruzar por hash un `.zip` de la reclamación contra
> el material ya bajado por `drive_ev`: **7 de 7 ficheros salieron «nuevos» y cuatro de ellos eran
> el mismo documento**.

**Qué pasa.** Los ficheros que el intake deposita en `CASOS` (Google Drive for Desktop, `G:`)
llevan **bytes de relleno a cero** hasta el siguiente múltiplo de 512. El contenido útil está
intacto —el prefijo es byte-idéntico al original y el PDF termina en su `%%EOF` antes del
relleno—, pero el fichero **no es byte-idéntico** al de origen.

| Documento (`W-048UOL`) | Tamaño en Drive E&V | Tamaño en el caso | Relleno |
|---|---|---|---|
| oferta aceptada | 2.747.021 | 2.747.392 | 371 |
| certificado bancario | 218.388 | 218.624 | 236 |
| justificante de transferencia | 21.644 | 22.016 | 372 |
| factura | 129.987 | 130.048 | 61 |

**No es de esta corrida y no es un artefacto de lectura.** Copiado de `G:` a `C:` conserva el
tamaño rellenado, y el barrido da `30/34` en `W-048UOL`, `242/324` en `W-02VEKE` y `170/237` en
`W-02JSVZ`. En casos antiguos (`BaRR3 …`) los tamaños son libres: 36 de 44 no son múltiplo de 512,
o sea que el instrumento **sí puede dar el otro valor**.

**El comentario de `core/intake_drive.py:233` ya vio el síntoma y lo leyó de menos.** Dice que
Drive Desktop «reescribe metadatos y `stat()` devuelve un tamaño ligeramente superior» (observado
+128, +268 en la sesión 21) y concluye que basta suprimir la verificación con `--ignore-size
--ignore-checksum --inplace`. Lo que falta en esa lectura: los bytes **están en el fichero**, no
solo en el `stat()`.

**Consecuencias, por orden de coste.**
1. **El dedup por `sha256` entre fuentes no ve los duplicados.** Es lo que lo destapó: cuatro
   documentos del `.zip` eran los mismos que ya estaban en el caso y el intake los habría
   depositado otra vez. La detección de `#211`/acción 11 funciona *dentro* de una fuente, donde
   todos comparten el mismo relleno.
2. **La cadena de custodia por hash no cuadra contra el original del cliente.** El `sha256` que
   guarda `_intake_log.jsonl` es el del fichero rellenado; el que da la API de Drive de E&V es el
   del original. Acreditar «es el mismo documento» exige explicar el relleno.
3. Alcance: **todo** caso escrito por esta vía, no solo los nuevos.

**Vías, sin decidir.** (a) Comparar por **prefijo** (hash del contenido hasta el tamaño de origen)
allí donde hoy se compara por sha; (b) escribir en local y publicar a Drive por `rclone` contra la
API en vez de por el filesystem montado; (c) truncar tras copiar —hay que medir si Drive Desktop
vuelve a rellenar—. Antes de nada, **medir si el relleno lo pone Drive Desktop o el `--inplace`**:
el comentario culpa al primero y nadie lo ha probado con y sin el flag.

## 215. [DUPLICADA de `#67.b` + `#67.c`] La medición de W-048UOL: 32 documentos en el catálogo, 15 en la sala

> **No es una entrada nueva y la abrí sin mirar el backlog, que es el error.** El defecto ya
> estaba escrito y con el fix propuesto: **`#67.b`** (colisión de `nombre_canonico`, fix
> «sufijar con `__<sha8>`») y **`#67.c`** (`poblar` escribe subcarpetas por fuente, fix «que
> escriba plano salvo bundles»). Lo que aporta esta entrada es **la medición**, no el
> diagnóstico.
>
> **El arreglo entra por la rama de W-02YZO4** (`7c4a97a`, que cita `#67.b`, `#67.c` y `#36`),
> no por aquí: dos sesiones escribimos el mismo par de arreglos a la vez sobre el mismo
> fichero, y la suya trae además la **poda del cascarón** de las carpetas por fuente y un test
> de **migración** del layout viejo. Mi diff se retiró antes de abrir PR para que no hubiera
> dos.

**La medición, que es lo que se conserva.** En W-048UOL (2026-09-10), tras `organizar`:
`indice_documental.yaml` declaraba **32 documentos** y en `Sala lectura/` había **15 ficheros**,
repartidos en dos carpetas de fuente (`Drive E&V/`, `Manual/`). Diecisiete imágenes —once fotos
de las escrituras de la sociedad, cuatro documentos de identidad y dos de la oferta— compartían
**dos únicos nombres** (`2026-03-16_foto_fotografia.jpeg` y `2026-03-17_foto_fotografia.jpeg`),
porque el clasificador describe toda imagen como «Fotografía» y la fecha era la misma. Cada copia
pisaba a la anterior.

**Dos cosas que la medición añade al diagnóstico ya escrito:**

- **El resumen declara éxito sobre la pérdida.** `organizar` imprimió
  `Acciones: {'COPY': 31, 'SKIP_DEDUP': 1}` con 15 ficheros en disco: `COPY` cuenta **copias
  intentadas**, no ficheros escritos. Mientras eso no cambie, ninguna corrida futura avisará.
- **No se pierde información, se pierde el acceso.** El `INDICE.md` conserva las 32 entradas y
  enlaza al original de `00_Input` y a su MD. Lo que engaña es la carpeta poblada, que aparenta
  ser el expediente y muestra la mitad.

**Y una decisión de contrato que hay que cerrar de paso**, porque hoy hay dos literales vivos y
distintos: la skill `organizar-sala-lectura` v1.3 (Paso 2) manda desambiguar con `_2`/`_3`,
mientras `#67.b` manda `__<sha8>`. El sufijo por hash es el que aguanta que el grupo **crezca**
—un `_2` puede pasar a `_3` y dejar sin referente la cita del letrado a un fichero—, así que el
literal que sobra es el de la skill. Que lo corrija el PR que implemente el arreglo.

## 216. El representante del dedup puede esconder el documento nuclear: el encargo firmado no aparece en el índice

> Medido el 2026-09-10 en `W-048UOL`, buscando la hoja de encargo en el índice de la sala.

**Qué pasa.** Dos ficheros de la carpeta de E&V son **byte-idénticos**: uno se llama
`Contracte Signat.pdf` (dentro de `ACTIVACIÓN`) y el otro `Oferta Signada i Acceptada.pdf` (dentro
de `OFERTA`). El dedup por `sha256` deja **un** representante, y le tocó el segundo nombre. El PDF
contiene **dos documentos lógicos** —el encargo de venta en exclusiva y la oferta de compra—, así
que el índice presenta el encargo bajo el rótulo de la oferta y la cadena `Contracte Signat` **no
aparece en `INDICE.md`**.

Técnicamente correcto: el fichero está, su texto partido está en los MD (`__d01`, `__d02`), y la
nota del `_cobertura.json` dice literalmente «2 documentos lógicos». Operativamente, quien busca
la hoja de encargo —la pieza de la que cuelga toda la reclamación— no la encuentra por su nombre.

**Vía.** Que la entrada del índice del representante **enumere los nombres de origen alias** (los
`alias_de` ya están en el `_cobertura.json`), en vez de dejarlos solo en la nota interna. Barato y
suficiente: no cambia el dedup, cambia lo que el índice dice de él.
