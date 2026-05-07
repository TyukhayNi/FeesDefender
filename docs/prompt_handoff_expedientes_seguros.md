
# PROMPT PARA EXPEDIENTES SEGUROS — HANDOFF DE ABSORCIÓN EN FEESDEFENDER

El proyecto **Expedientes Seguros** desaparece como proyecto independiente y se absorbe íntegramente en FeesDefender. Esto no es una integración puntual del anonimizador — es la disolución completa de Expedientes Seguros: su gestión de expedientes, su pipeline de procesamiento documental y sus herramientas de anonimización pasan a ser módulos nativos de FeesDefender.

Necesito que me proporciones toda la información técnica necesaria para ejecutar esta absorción. La integración será completa: importando las funciones directamente, sin ventanas CMD, sin menús interactivos, con feedback en tiempo real a Streamlit. Sé exhaustivo y técnicamente preciso. Si algo no está claro en el código, dímelo explícitamente.

---

## CONTEXTO

**Expedientes Seguros** es un proyecto Python independiente que gestiona un pipeline de procesamiento documental para expedientes jurídicos: OCR de documentos escaneados, separación automática en piezas documentales, anonimización de PII y generación de ficheros `.md` listos para análisis con LLMs. Su estructura de datos vive en `G:\Unidades compartidas\DESPACHO - PRODUCCION\Expedientes Seguros\Expedientes\`, con una carpeta por expediente que contiene subcarpetas `_originales/`, `_ocr/`, `_separados/`, `_anonimizados/`, `_para_IA/` y un `expediente.json` de metadatos gestionado por `gestionar_expediente.py`.

**FeesDefender** es una aplicación Python/Streamlit para gestión de honorarios de intermediación inmobiliaria. Arquitectura de 3 capas: UI (Streamlit) → Core (módulos Python en `core/`) → Datos (carpetas de caso en `data/CASOS/`). Ya tiene su propio sistema de gestión de expedientes (`case_manager.py`, `_caso.md`) y sus propias carpetas de caso.

La absorción implica que **la estructura de datos de Expedientes Seguros desaparece** — no hay migración de esquema, hay sustitución. Los expedientes de Expedientes Seguros dejan de existir como entidad separada y sus funciones pasan a ejecutarse sobre las carpetas de caso de FeesDefender.

Cada caso de FeesDefender tiene las siguientes subcarpetas de **nivel raíz**:

```
00_Input/
01_Procesado/
02_Analisis/
03_Decision/
04_Output predemanda/
05_Procedimiento/
06_Anonimizado/
07_AI cowork/
90_Notas personales/
```

Dentro de `00_Input/` existen las siguientes **subcarpetas de intake**:

```
01_Drive EV/          ← carpeta W-XXXXXX del Drive engelvoelkers.com (intake automatizado via rclone)
02_Whatsapp/          ← conversaciones exportadas manualmente
03_Email/             ← hilos de correo exportados manualmente
04_Manual/            ← cualquier documento que no proceda de las fuentes anteriores
05_Demanda judicial/  ← demanda + docs judiciales subidos manualmente desde la UI
sudespacho_{id}/      ← pull CRM sudespacho (nombre dinámico, creado por el sistema)
```

El anonimizador debe leer de `00_Input/` y sus subcarpetas de documentos: `01_Drive EV/`, `04_Manual/`, `05_Demanda judicial/`, y cualquier `sudespacho_*/`. Se excluyen `02_Whatsapp/` y `03_Email/` — son Flujo B (comunicaciones), fuera de scope en esta fase. El output va a `06_Anonimizado/`.

La integración debe exponer una función orquestadora limpia que Streamlit pueda llamar con un callback de progreso. El usuario no verá ningún menú interactivo — tipo de procedimiento y opciones de revisión se pasan como parámetros.

---

## SECCIÓN 1 — FLUJOS DE INTAKE

Hay dos flujos distintos que convergen en el anonimizador:

**Flujo A — Documentos** (PDFs judiciales, contratos, imágenes escaneadas, DOCX): `imagen_a_pdf.py` → OCR (ocrmypdf) → `separar.py` → `anonimizar.py` → `renombrar.py`

**Flujo B — Comunicaciones** (WhatsApp exportado, emails .eml/.msg): no necesitan OCR ni separación — se parsean directamente a texto y pasan a `anonimizar.py`. Este flujo se implementará en fase posterior. Para esta integración nos centramos en el Flujo A.

Para el Flujo A, dime:

- ¿`imagen_a_pdf.py` es autocontenido o depende de funciones de otros módulos del proyecto?
- ¿Qué ocurre exactamente si la imagen de entrada es RGBA o tiene transparencia? ¿Cómo se gestiona?
- ¿El DPI de 200 es configurable o está hardcodeado? Si está hardcodeado, ¿dónde exactamente?
- ¿Hay algún caso de imagen que `imagen_a_pdf.py` no maneje actualmente y que debería manejar?
- Para HEIC/HEIF: ¿pillow-heif tiene que estar instalado manualmente o hay fallback?

---

## SECCIÓN 2 — OCR

He confirmado en `1_OCR.bat` que el comando exacto es:

```
python -m ocrmypdf -l spa+cat+rus --skip-text --deskew --optimize 1 --rotate-pages -v 1 "<input>" "<output>"
```

Confirma:

- ¿`--skip-text` es el flag correcto para PDFs que ya tienen capa de texto? ¿O debería ser `--redo-ocr` en algún caso?
- ¿`-v 1` produce output en stdout o stderr? ¿Qué información concreta emite ese nivel de verbosidad?
- ¿Qué código de retorno emite ocrmypdf cuando no hay páginas que procesar (PDF ya tiene texto completo)?
- ¿Cómo se detecta que el OCR falló parcialmente (algunas páginas sin texto) vs. completamente?
- He visto en `procesar_carpeta.py` que hay un fallback: si `rc != 0`, se usa el PDF original. ¿Es siempre seguro este fallback o hay casos donde el PDF original es inutilizable?
- ocrmypdf no está en PATH — debe llamarse como `python -m ocrmypdf`. ¿Hay algún caso donde esto no funcione (entornos virtuales, instalaciones específicas)?

---

## SECCIÓN 3 — SEPARADOR (`separar.py`)

He leído el código y tengo las siguientes preguntas:

- `TIPOS_SUPER_ABSORBENTES = {'DEMANDA', 'SENTENCIA', 'CONTESTACION', 'OPOSICION'}`: ¿estos tipos absorben cualquier segmento siguiente sin `num_doc` en portada, o solo los que no tienen marcador explícito de ningún tipo?
- `TIPOS_ABSORBE_SIN_NUMERO = {'DOC_CONTRATO', 'DOC_FACTURA', 'DOC_EMAIL', 'DOC_ANEXO', 'DOC_TRADUCCION'}`: ¿cuál es la diferencia de comportamiento exacta entre este grupo y `TIPOS_SUPER_ABSORBENTES`?
- `MAX_PAGINAS_SIN_MARCADOR = 60`: ¿qué ocurre exactamente cuando se supera este límite? ¿Se fuerza un corte o se emite una advertencia?
- `--sin-confirmacion` como tercer argumento: ¿qué valor exacto debe pasarse? ¿`"S"`, `"SI"`, `"True"`, o cualquier valor truthy?
- La función `separar_pdf()`: ¿cuál es su firma exacta? ¿Qué devuelve? ¿Lanza excepción o devuelve código de error si el PDF no tiene capa de texto?
- ¿Cómo detecta `separar.py` que un PDF no tiene capa de texto (no ha pasado por OCR)? ¿Lanza excepción o devuelve lista vacía?
- ¿El separador escribe los PDFs directamente a disco o devuelve estructuras en memoria que el llamador puede escribir?
- Para la integración necesito poder pasar un callback de progreso (ej: `on_page_processed(n, total)`). ¿Hay algún punto natural en el código donde enchufar esto?

---

## SECCIÓN 4 — MOTOR DE ANONIMIZACIÓN (`anonimizar.py` v3.10)

Esta es la pieza más crítica. Necesito entender exactamente cómo exponer su lógica de forma programática.

### 4.1 — Clase `MapaEntidades`

- Campos exactos: `mapa` (nombre→etiqueta), `mapa_inverso` (etiqueta→nombre_real), `contadores` (defaultdict por tipo), `dudosos` (list), `protegidos` (set)
- ¿`MapaEntidades` es serializable directamente a JSON con `json.dumps()`? ¿O tiene campos que requieren conversión previa (ej: defaultdict)?
- Requisito clave de integración: para un caso con múltiples documentos, la misma persona debe recibir el mismo token `PERSONA_01` en todos los documentos. Esto requiere un `MapaEntidades` compartido por caso. ¿Cómo se pasa un `MapaEntidades` preexistente a la función `procesar()`? ¿Tiene un parámetro para recibirlo?
- ¿`MapaEntidades` tiene método `merge()` o `update()` para combinar el mapa de un documento con el mapa acumulado del caso?

### 4.2 — Función `procesar()`

- Firma exacta con todos los parámetros y tipos
- ¿Qué devuelve? ¿`(texto_anonimizado: str, mapa: MapaEntidades)` o escribe directamente a fichero?
- ¿Hay separación entre la lógica de anonimización (pura, sobre texto) y la lógica de I/O (leer PDF/DOCX, escribir .md)?
- Si no existe esta separación, ¿cuál sería el mínimo cambio para extraer una función `anonimizar_texto(texto: str, mapa: MapaEntidades, tipo_proc: str) -> (str, MapaEntidades)`?

### 4.3 — Partes interactivas a eliminar

He identificado dos funciones interactivas que deben eliminarse en la versión integrada:

- `pedir_tipo_procedimiento()`: usa `msvcrt.getwch()` — espera input de teclado
- `revisar_interactivo`: usa `input()` para fragmentos dudosos

Para la integración, `tipo_proc` y `hacer_revision` deben ser parámetros. Confirma:

- ¿Hay más usos de `msvcrt`, `input()`, `print()` con propósito de interacción que deba eliminar?
- ¿`pedir_tipo_procedimiento()` tiene valores por defecto si no se llama (ej: `ORDINARIO`)?
- Si `revisar_interactivo=False`, ¿los fragmentos dudosos simplemente se incluyen en el mapa sin preguntar?

### 4.4 — Extractor LTChar para PDFs OCRmyPDF

- ¿El extractor LTChar maneja correctamente PDFs mixtos (algunas páginas OCR + algunas con texto nativo)?
- ¿`pagina_girada()` (v3.10) modifica el texto antes de pasarlo al anonimizador, o solo detecta y marca la página?
- Ratio de detección de página girada: `n_lineas > 50 and n_chars < 900` — ¿este umbral está calibrado para A4 a 200 DPI?

### 4.5 — Formato `_mapa.json`

He leído el código y veo que exporta `mapa_inverso` (etiqueta→valor_real), no `mapa`. Confirma el formato exacto:

```json
{
  "generado": "2024-01-15T10:30:00",
  "mapa": {
    "PERSONA_01": "Ivan Petrov Sokolov",
    "DNI_01": "12345678A"
  }
}
```

¿Es esto correcto? ¿Hay campos adicionales en el JSON de salida?

### 4.6 — `dudas_acumuladas.json`

El fichero actual está vacío (solo esqueleto). ¿Cuál es el formato exacto de cada entrada de duda? ¿Qué campos tiene un objeto de duda cuando `revisar_interactivo=True` y el usuario toma una decisión?

### 4.7 — Argumento `--pipeline`

He visto que `procesar_carpeta.py` pasa `--pipeline` como argumento. ¿Qué comportamiento activa exactamente este flag? ¿Suprime todo output a stdout? ¿Cambia alguna lógica de anonimización?

### 4.8 — Score thresholds

- Presidio general: 0.35, PERSON: 0.65. ¿Estos valores son constantes en el código o hay parámetro para ajustarlos?
- ¿Hay umbral diferente para otros tipos de entidad (LOCATION, ORG)?

### 4.9 — Modelo NER para idiomas

¿Qué modelo de spaCy/Presidio se usa para reconocimiento de entidades en ruso? Este despacho procesa documentos en español, catalán y ruso. ¿Hay un recognizer custom o se delega todo en Presidio con un modelo genérico? ¿El modelo cubre NER cirílico?

### 4.10 — Formato exacto del `.md` de salida

¿Cuál es el formato del fichero `.md` que produce `anonimizar.py`? ¿Tiene frontmatter YAML (título, fecha, tipo documental)? ¿Cómo está estructurado el cuerpo: por páginas, por secciones, texto corrido? FeesDefender necesitará parsear estos ficheros para mostrarlos en la UI y subirlos al Drive.

---

## SECCIÓN 5 — DEANONIMIZADOR (`deanonimizar.py`)

- Firma exacta de la función principal de reversión
- Usa `str.replace()` y no regex: ¿esto garantiza orden determinista de sustitución? ¿Hay riesgo de sustituciones anidadas (ej: si un token contiene otro token)?
- Búsqueda del `_mapa.json`: (1) misma carpeta, (2) `_anonimizados/` si el `.md` viene de `_para_IA/`. ¿Hay algún tercer fallback?
- `nombre_base = ruta.stem.replace("_anonimizado", "")`: ¿qué ocurre si el nombre del fichero tiene `_anonimizado` en medio (no como sufijo)?
- Actualización del header: regex `r'> \*\*Documento anonimizado\*\*.*\n'`. ¿Qué texto pone en su lugar? ¿`> **Documento restaurado**`?
- Para la integración: necesito una función `deanonimizar_texto(texto: str, mapa_path: Path) -> str` que no toque el sistema de ficheros. ¿Existe o hace falta crearla?
- ¿El deanonimizador maneja el caso donde el mapa tiene entradas que ya no aparecen en el texto (tokens no encontrados)?

---

## SECCIÓN 6 — RENOMBRADOR (`renombrar.py`)

He leído el código completo. Para la integración necesito:

- `renombrar_expediente(carpeta_expediente: Path)` renombra los `.md` en `_anonimizados/` y `_para_IA/` en tripleta. ¿Esta función es idempotente? ¿Qué ocurre si se llama dos veces sobre el mismo expediente?
- `mejor_fecha()` descarta fechas dentro de los últimos 30 días (`umbral_reciente = hoy - timedelta(days=30)`). ¿Es configurable este umbral? Para documentos muy recientes (ej: demandas presentadas esta semana), ¿esto provoca que siempre queden sin prefijo de fecha?
- El renombrador trabaja sobre `_anonimizados/` y `_para_IA/`. En FeesDefender usamos `06_Anonimizado/` como única carpeta de salida. ¿Es seguro llamar a `renombrar_expediente()` pasando la carpeta `06_Anonimizado/` directamente, aunque no tenga exactamente la estructura `_anonimizados/` + `_para_IA/`?
- ¿`renombrar_expediente()` devuelve el número de ficheros renombrados o la lista de ficheros con sus nombres nuevos?

---

## SECCIÓN 7 — GESTIÓN DE EXPEDIENTE (`gestionar_expediente.py`)

Este módulo queda obsoleto tras la absorción, pero necesito entender sus dependencias para no romper otros módulos al eliminarlo.

- `buscar_expediente_json()`: sube exactamente 4 niveles (lo he contado en el código, aunque `CLAUDE.md` dice 5). Confirma: ¿4 o 5?
- `DRIVE_BASE` está hardcodeado como `G:\Unidades compartidas\DESPACHO - PRODUCCION\Expedientes Seguros\Expedientes`. ¿`anonimizar.py` llama directamente a `gestionar_expediente.py` para escribir el log? Si es así, ¿cómo override esta ruta para FeesDefender?
- Formato exacto de `expediente.json` — he inferido:

```json
{
  "referencia": "VaRS5 - Cr Denia-Javea 14",
  "creado": "07/05/2024 10:30",
  "creado_por": "tnm",
  "carpeta": "G:\\...\\VaRS5 - ...",
  "fases": {
    "ocr": "2024-05-07T10:31:00",
    "separacion": "2024-05-07T10:32:00",
    "anonimizacion": [
      {"archivo": "demanda.pdf", "fecha": "2024-05-07T10:33:00"}
    ]
  }
}
```

¿Es correcto? ¿Hay más campos?

- `actualizar_fase()`: ¿este método es thread-safe? En FeesDefender procesamos documentos secuencialmente, pero quiero saberlo.
- `modo_crear()` usa `msvcrt.getwch()` — ¿hay forma de llamar la lógica de creación de estructura de carpetas sin pasar por el menú interactivo?

---

## SECCIÓN 8 — ORQUESTADOR (`procesar_carpeta.py`)

Este módulo queda obsoleto como script, pero su lógica de orquestación se reescribirá en `core/intake_anonimizador.py`. Necesito entenderlo a fondo.

- `DRIVE_EXPEDIENTES` hardcodeado: `Path(r"G:\Unidades compartidas\DESPACHO - PRODUCCION\Expedientes Seguros\Expedientes")`. ¿Hay forma de parametrizarlo sin modificar el módulo?
- `EXTS_VALIDAS`: `{".pdf"} | {".jpg",".jpeg",".png",".tif",".tiff",".bmp",".heic",".heif"} | {".doc",".docx"}`. ¿Está completa esta lista? ¿Falta `.odt`?
- Política `REPROCESAR`: borra `_ocr`, `_separados`, `_anonimizados`, `_para_IA` pero mantiene `_originales`. ¿Es seguro llamar a `REPROCESAR` si el pipeline anterior terminó a medias?
- `run_cmd()` usa `subprocess.run(..., capture_output=True, text=True, encoding="utf-8", errors="replace")`. Para la integración quiero capturar este output y pasarlo a un callback. ¿Puedo reemplazar `run_cmd()` con una versión que emita líneas a un generador?
- LibreOffice: `soffice.com --headless --convert-to pdf`. Este no está en `verificar_entorno.py`. ¿Es una dependencia crítica o solo necesaria cuando hay `.doc`/`.docx`? ¿Qué ocurre exactamente si LibreOffice no está instalado y llega un `.docx`?
- `sanear()`: reemplaza `[\\/:*?"<>|·]` por `-`, strip, trunca a 200 chars. ¿Esto es para el nombre de la carpeta del expediente o para el nombre de los ficheros de salida?
- OCR fallback: `pdf_actual = ocr_pdf if rc == 0 else pdf_para_ocr`. Si el OCR falla completamente (`rc != 0`), el PDF sin capa de texto pasa al separador. ¿El separador maneja graciosamente un PDF sin texto o lanza excepción?
- ¿`procesar_carpeta.py` tiene una función pública con la que pueda llamar el procesamiento de un solo fichero (no de una carpeta entera)?

---

## SECCIÓN 9 — ENCODING E INTER-PROCESS COMMUNICATION

He visto en `_avanzado/0_PIPELINE_launcher.py` que el fichero temporal se lee en cp1252:

```python
Path(tmp_file).read_text(encoding='cp1252')
```

FeesDefender usa UTF-8 en todos sus ficheros. Para la integración nativa (sin subprocess), esto no es un problema — no hay fichero temporal. Pero confirma:

- ¿Hay algún otro lugar en el código donde se asuma una encoding distinta de UTF-8?
- ¿Los `.md` de salida se escriben siempre en UTF-8?
- ¿Los `_mapa.json` se escriben con `ensure_ascii=False` o con caracteres unicode escapados?
- ¿El log acumulativo (`anonimizador.log`) se escribe en UTF-8 o cp1252?

---

## SECCIÓN 10 — DEPENDENCIAS NO DOCUMENTADAS

He comparado `verificar_entorno.py` con `procesar_carpeta.py` y encontré que LibreOffice está completamente ausente de la verificación. Para FeesDefender necesito un verificador de dependencias completo.

Confirma la lista completa de dependencias del sistema (no solo Python):

- **Python**: `pdfminer.six`, `pypdf`, `python-docx`, `spaCy` + 3 modelos, `presidio-analyzer`, `presidio-anonymizer`, `ocrmypdf`, `Pillow`, `pillow-heif`
- **Sistema**: Tesseract 5.x (spa+cat+rus), Ghostscript, LibreOffice
- ¿Falta alguna otra dependencia de sistema?
- ¿`pillow-heif` requiere alguna dependencia de sistema (ej: libheif)?
- ¿Ghostscript está en PATH o se llama mediante ruta absoluta? ¿`ocrmypdf` lo localiza automáticamente?

---

## SECCIÓN 11 — API PÚBLICA QUE NECESITO

Para la integración, necesito que me propongas la API mínima que debo exponer (o que ya existe) en cada módulo. Quiero funciones puras sin efectos de I/O, con la lógica desacoplada de la CLI.

Para cada función, dame: firma completa con tipos, qué devuelve, qué excepciones puede lanzar, y si ya existe o hay que crearla.

Funciones que necesito:

```python
# 1. Convertir imagen a PDF en memoria o disco
def imagen_a_pdf(ruta_imagen: Path, ruta_salida: Path) -> Path: ...

# 2. Ejecutar OCR sobre PDF
def ocr_pdf(ruta_entrada: Path, ruta_salida: Path,
            on_progress=None) -> tuple[Path, int]: ...
# devuelve (ruta_resultado, return_code)

# 3. Separar PDF en documentos
def separar_pdf(ruta_pdf: Path, carpeta_salida: Path,
                sin_confirmacion: bool = True) -> list[Path]: ...

# 4. Anonimizar texto (función pura)
def anonimizar_texto(texto: str, mapa: MapaEntidades,
                     tipo_proc: str = "ORDINARIO",
                     hacer_revision: bool = False) -> tuple[str, MapaEntidades]: ...

# 5. Cargar mapa existente desde JSON
def cargar_mapa(ruta_json: Path) -> MapaEntidades: ...

# 6. Guardar mapa a JSON
def guardar_mapa(mapa: MapaEntidades, ruta_json: Path) -> None: ...

# 7. Deanonimizar texto (función pura)
def deanonimizar_texto(texto: str, mapa: MapaEntidades) -> str: ...

# 8. Renombrar con prefijo de fecha
def renombrar_con_fecha(ruta_md: Path) -> Path: ...
```

¿Alguna de estas ya existe en la forma indicada? ¿Cuál requeriría refactoring mayor vs. menor?

---

## SECCIÓN 12 — MAPA COMPARTIDO POR CASO

Este es el requisito arquitectónico más crítico y necesito la respuesta más detallada.

En FeesDefender, un caso puede tener 50 documentos. Si Ivan Petrov aparece en el documento 1 como `PERSONA_01` y en el documento 15 como `PERSONA_04`, la IA no puede correlacionar que es la misma persona.

Necesito:

- Un `MapaEntidades` persistido en `06_Anonimizado/_mapa_caso.json` que se carga antes de procesar cada documento y se guarda después
- Cuando se procesa el documento N, el mapa ya contiene todas las entidades de los documentos 1..N-1
- El mismo nombre real → mismo token, siempre

Preguntas concretas:

- ¿`MapaEntidades.__init__()` acepta un dict inicial para pre-popularlo con entidades ya conocidas?
- ¿La lógica de asignación de tokens (`PERSONA_01`, `PERSONA_02`, ...) funciona correctamente con un mapa pre-poblado (los contadores arrancan desde donde lo dejaron)?
- ¿Hay riesgo de colisión si el mapa pre-poblado tiene `PERSONA_05` y el documento nuevo genera `PERSONA_05` para una persona distinta?
- ¿El proceso de matching de nombres es sensible a variaciones de escritura? Si en el documento 1 aparece `IVAN PETROV SOKOLOV` (mayúsculas) y en el 15 aparece `Ivan Petrov Sokolov` (tipo título), ¿se asigna el mismo token?
- ¿Cómo gestiona el matcher variantes que implican transliteración del cirílico (Иван Петров → Ivan Petrov / Iván Petrov) o abreviaturas de nombre patronímico (PETROV I.S. vs Ivan Sokolovich Petrov)? En contexto de despacho con clientela de origen ruso, esta casuística es la regla, no la excepción.
- ¿Cómo se serializa `contadores` (defaultdict) a JSON y se deserializa?

---

## SECCIÓN 13 — MANEJO DE ERRORES Y ROBUSTEZ

Para un pipeline de producción en un despacho necesito saber exactamente cómo falla cada módulo.

- ¿`anonimizar.py` tiene logging estructurado (ej: Python `logging`) o solo `print()`?
- Si Presidio falla (ej: modelo spaCy no cargado), ¿el anonimizador aborta o pasa a la siguiente fase?
- Si OCR falla en una página específica, ¿el pipeline continúa con las páginas restantes?
- Si el separador no detecta ningún marcador documental, ¿devuelve el PDF completo como un único documento o devuelve lista vacía?
- ¿Qué ocurre si se intenta anonimizar un PDF completamente en blanco (0 caracteres de texto)?
- ¿Hay timeouts configurados en algún módulo? ¿OCRmyPDF tiene timeout propio?
- ¿El pipeline es atómico por documento? Es decir, si falla la anonimización del documento 3 de 5, ¿se conservan los documentos 1 y 2 ya procesados?
- Si el pipeline se interrumpe entre la fase de OCR y la de separación (corte de alimentación, kill del proceso), ¿quedan PDFs intermedios en disco o en `%TEMP%`? ¿Hay cleanup automático al reiniciar, o puede haber conflicto al reprocesar el mismo caso?

---

## SECCIÓN 14 — IDEMPOTENCIA

En FeesDefender el pipeline puede re-ejecutarse sobre un caso ya procesado.

- La política `SALTAR` de `procesar_carpeta.py` usa un marcador. ¿Cuál es exactamente ese marcador? ¿Un fichero `.done`? ¿Una clave en `expediente.json`?
- Si tengo 5 documentos en `06_Anonimizado/` y añado 2 nuevos a `00_Input/`, ¿la política `SALTAR` procesa solo los 2 nuevos o salta todo el caso?
- ¿`renombrar.py` es idempotente? `tiene_prefijo_fecha()` detecta `^\d{8}\s*-\s*` — ¿cubre todos los casos posibles de nombre ya renombrado?

---

## SECCIÓN 15 — TESTING Y VALIDACIÓN

- `crear_prueba.py` genera `test_prueba.docx` con datos PII conocidos (Ivan Petrov Sokolov, DNI 12345678A, IBAN ES91 2100 0418 4502 0005 1332, email ivan.petrov@correo.es). ¿Hay un test automatizado que verifique que estos datos quedan anonimizados correctamente?
- ¿Existe algún test de round-trip (anonimizar → deanonimizar → verificar que el texto original se recupera exactamente)?
- ¿Hay tests de regresión para el separador que cubran los casos DEMANDA super-absorbente?
- Para la integración en FeesDefender necesito un test de integración. ¿Puedes proporcionar el contenido mínimo de un PDF de prueba (texto) que ejercite todos los tipos documentales del separador?

---

## SECCIÓN 16 — MEJORA CONTINUA (`dudas_acumuladas.json`)

El fichero está actualmente vacío. Cuando esté en producción y acumule datos:

- ¿Cuál es el formato exacto de cada entrada? Dame un ejemplo real o construido de cómo quedaría una entrada cuando el usuario decide en `revisar_interactivo` que un fragmento SÍ es un nombre propio vs. que NO lo es.
- ¿Este fichero crece indefinidamente o hay rotación/archivado?
- En la integración con FeesDefender, ¿debo mantener este fichero en la ruta actual (`_herramientas/dudas_acumuladas.json`) o puede moverse a la carpeta de datos del caso?

---

## SECCIÓN 17 — CAMBIOS MÍNIMOS NECESARIOS

Dame una lista exhaustiva, ordenada por impacto, de los cambios que hay que hacer en los ficheros de Expedientes Seguros para que la absorción funcione sin modificar la lógica de anonimización. Los `.bat` y el uso standalone dejan de ser requisito — no necesito backward compatibility.

Para cada cambio: fichero, línea aproximada, cambio actual → cambio propuesto.

Anticipo como mínimo:

1. Eliminar/condicionar `msvcrt.getwch()` en `pedir_tipo_procedimiento()` y `modo_crear()`
2. Eliminar/condicionar `input()` en `revisar_interactivo`
3. Parametrizar `DRIVE_EXPEDIENTES` en `procesar_carpeta.py`
4. Parametrizar `DRIVE_BASE` en `gestionar_expediente.py`
5. Exponer función `anonimizar_texto()` pura
6. Hacer `MapaEntidades` serializable/deserializable a JSON
7. Añadir LibreOffice a `verificar_entorno.py`

¿Hay más?

---

## SECCIÓN 18 — PREGUNTAS FINALES

1. ¿Hay algún estado global en `anonimizar.py` (variables de módulo, singletons de spaCy/Presidio) que deba inicializarse una sola vez al arrancar FeesDefender y no por cada documento?
2. ¿Los modelos de spaCy se cargan en cada llamada a `procesar()` o se cachean? ¿Cuánto tiempo tarda la carga inicial?
3. ¿Hay algún aspecto del pipeline que hayas visto que podría causar problemas en un entorno donde Google Drive se monta como unidad de red (latencia de I/O, bloqueos de ficheros, problemas con rutas largas en Windows)?
4. ¿Hay algo en el código que sepa que podría romperse en la transición de uso standalone (BAT → CMD) a uso embebido (importado por Python/Streamlit)?
5. ¿Cuál es el tamaño típico de memoria RAM que consume el pipeline completo con los modelos spaCy + Presidio cargados?

---

## SECCIÓN 19 — ABSORCIÓN TOTAL: EXPEDIENTES SEGUROS DESAPARECE COMO PROYECTO INDEPENDIENTE

No se trata de conectar dos proyectos ni de integrar una herramienta puntual. El proyecto **Expedientes Seguros** se disuelve en su totalidad y su código y datos pasan a ser parte nativa de FeesDefender. Esto incluye tanto el pipeline de anonimización (`_herramientas/`) como la gestión de expedientes (`gestionar_expediente.py`, `expediente.json`, estructura de carpetas en `Expedientes Seguros\Expedientes\`).

A partir de este momento:

- Los ficheros `.bat`, `.vbs` y el launcher Python dejan de mantenerse. No necesito que sobrevivan.
- `gestionar_expediente.py` queda completamente obsoleto — FeesDefender tiene su propio `case_manager.py` y `_caso.md`. La gestión del ciclo de vida del expediente, el logging de fases y la estructura de carpetas la hace FeesDefender. No necesito ninguna función de este módulo.
- La carpeta `Expedientes Seguros\Expedientes\` deja de crecer. Los nuevos expedientes se crean exclusivamente en la estructura de casos de FeesDefender (`data/CASOS/`).
- `procesar_carpeta.py` queda obsoleto como script — su lógica de orquestación se reescribe en `core/intake_anonimizador.py` dentro de FeesDefender.
- La estructura `_originales/`, `_ocr/`, `_separados/`, `_anonimizados/`, `_para_IA/` de Expedientes Seguros no existe en FeesDefender. El mapping es:
  - **Input:** `00_Input/` y sus subcarpetas de documentos: `01_Drive EV/`, `04_Manual/`, `05_Demanda judicial/`, `sudespacho_*/` (se excluyen `02_Whatsapp/` y `03_Email/` — son Flujo B, fase posterior)
  - **Output:** `06_Anonimizado/` — aquí van los `.md` + `_mapa.json` + `_mapa_caso.json`
  - No hay carpeta `_ocr/` ni `_separados/` — son temporales en memoria o en `%TEMP%`
- `expediente.json` y `anonimizador.log` de Expedientes Seguros no se crean — FeesDefender tiene su propio sistema de metadatos (`_caso.md`) y logging.
- `dudas_acumuladas.json` se mueve a `data/` de FeesDefender (¿fuera de `.gitignore`? — decidir).

Con este contexto, preguntas adicionales:

### 19.1 — Núcleo puro vs. infraestructura

Expedientes Seguros tiene dos capas diferenciadas: el **núcleo de procesamiento** (`_herramientas/`) y la **infraestructura de gestión** (`gestionar_expediente.py`, estructura de carpetas, logs). FeesDefender ya tiene su propia infraestructura de gestión, así que lo que necesito importar es únicamente el núcleo. Clasifica explícitamente cada fichero de `_herramientas/`:

| Fichero | Categoría | Destino en FeesDefender |
|---|---|---|
| `anonimizar.py` | ¿Núcleo puro / Mixto / Infraestructura? | `core/anon/anonimizar.py` |
| `separar.py` | ¿? | `core/anon/separar.py` |
| `deanonimizar.py` | ¿? | `core/anon/deanonimizar.py` |
| `imagen_a_pdf.py` | ¿? | `core/anon/imagen_a_pdf.py` |
| `renombrar.py` | ¿? | `core/anon/renombrar.py` |
| `gestionar_expediente.py` | ¿? | OBSOLETO |
| `procesar_carpeta.py` | ¿? | OBSOLETO (reemplazado) |
| `verificar_entorno.py` | ¿? | Integrar en health-check de FeesDefender |
| `crear_prueba.py` | ¿? | Convertir en fixture de tests |

Para cada fichero clasificado como "Mixto": ¿cuáles son exactamente las líneas de código que mezclan lógica pura con I/O o con paths hardcodeados? Quiero saber el coste exacto de extirpar la infraestructura y quedarme solo con el núcleo.

### 19.2 — Dependencias internas entre módulos

- ¿`anonimizar.py` importa directamente `gestionar_expediente.py`? ¿En qué líneas? Si es así, ¿qué funcionalidad concreta necesita de él (solo el log, solo la búsqueda de `expediente.json`, ambas cosas)?
- ¿`separar.py` tiene alguna dependencia de `gestionar_expediente.py` o de `procesar_carpeta.py`?

Necesito saber si puedo copiar `anonimizar.py` y `separar.py` a FeesDefender y eliminar sus imports de módulos de Expedientes Seguros sin romper nada, o si hay dependencias que hay que resolver primero.

### 19.3 — Acoplamiento a rutas del sistema de ficheros

Identifica todas las líneas en `anonimizar.py` y `separar.py` donde se construye o asume una ruta de fichero específica (rutas relativas a `__file__`, rutas absolutas hardcodeadas, búsquedas hacia arriba en el árbol de directorios). Estas son las líneas que hay que parametrizar o eliminar para que los módulos sean agnósticos a su ubicación en el disco.

### 19.4 — `dudas_acumuladas.json` en el nuevo esquema

En Expedientes Seguros, este fichero vive junto al código (`_herramientas/`). En FeesDefender el código va en `core/` y los datos en `data/`. ¿Tiene sentido que `dudas_acumuladas.json` sea global al despacho (una sola instancia en `data/`) o debería haber una instancia por caso (en `data/CASOS/<caso>/`)? ¿Cómo lo tienes pensado actualmente?

### 19.5 — Estrategia de migración de casos ya procesados

Cuando hagamos el corte, habrá expedientes ya procesados en la estructura de Expedientes Seguros (`Expedientes Seguros\Expedientes\<ref>\_anonimizados\`). Dos preguntas:

- ¿Existe alguna utilidad en el código actual que permita exportar o listar todos los resultados ya producidos (`.md`, `_mapa.json`) de un expediente? ¿O hay que recorrer el árbol de carpetas manualmente?
- ¿La migración es tan simple como copiar los `.md` y `_mapa.json` a `06_Anonimizado/` del caso correspondiente en FeesDefender, o hay dependencias en `expediente.json` que los `.md` asuman como existentes (rutas, referencias cruzadas, etc.)?

---

Responde sección a sección. Si algo no lo sabes con certeza, dímelo explícitamente — prefiero un "no implementado" honesto a una suposición.
