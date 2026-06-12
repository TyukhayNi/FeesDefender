# PLAN — Intake automático de correos de procuradores → Sudespacho

> **Para retomar en un hilo nuevo. Documento autocontenido.** Diseño cerrado con
> Nikolai el 2026-06-12 (sesión de diseño larga, sobre maquetas). Implementación
> pendiente (Claude Code). Identificador de backlog: `[SIGUIENTE-INTAKE-PROCURADORES-EMAIL]`.
>
> **RGPD — excepción consciente y ACOTADA a este flujo:** este intake usa una **LLM
> en la nube (Mistral, UE)**, aceptando exponer PII porque da mejor resultado que
> scripts puros. NO deroga la regla general del despacho (nada de LLM cloud con
> datos de caso) para el resto de FeesDefender (pipeline, anonimizador, etc.).

---

## 1. Objetivo

Archivar automáticamente en el CRM **Sudespacho** los correos que llegan al
despacho relacionados con procedimientos: (a) **notificaciones de procuradores**
y (b) **contestaciones a correos que el despacho envía desde un expediente**
(p. ej. testigos). Cada correo queda **relacionado con su expediente** en el
módulo de correo del CRM y, cuando procede, sus **adjuntos** se suben al gestor
documental con un **nombre legible**. Todo pasa por una **red de seguridad** con
confirmación humana antes de escribir en el CRM.

Es el sentido inverso del intake actual (correo→CRM, no CRM→local). Encaja con
`docs/PLAN_INTAKE_CRM_COMPLETO.md`.

## 2. Alcance

**Entra:**
- Notificaciones de procuradores (dominios conocidos: `@procuradores-a.example`,
  `@procuradores-b.example`, `proc-a@example.invalid`,
  `@procuradores-c.example`, `proc-f@colegio-proc.example`, `@procuradores-d.example`,
  `@procuradores-e.example`; ampliable).
- Contestaciones a correos enviados desde el CRM (señal: pertenencia al **hilo**
  del correo saliente ya relacionado, o referencia citada en la plantilla).

**No entra (ruido):** alertas automáticas (Google), publicidad, correos internos
sin relevancia procesal.

## 3. Arquitectura

Un **proceso/robot independiente** (no el servidor MCP `gmail-ro`, que es para
consultas interactivas). Corre en local, periódicamente. Reutiliza:
- La conexión a Sudespacho de FeesDefender (`core/sync_sudespacho.py`,
  `SudespachoConfig.from_env()` → API Key en variable de entorno de usuario
  `SUDESPACHO_API_KEY`, cabecera `x-api-key`). **La API Key nunca pasa por el LLM.**
- El motor de extracción/OCR existente (Docling) para leer el contenido de los
  adjuntos.
- El patrón de aprendizaje del organizador local (`core/local_organizer.py`).

Nuevo módulo sugerido: `core/procurador_intake.py` + UI en `streamlit_app.py`.

## 4. Flujo paso a paso

0. **Disparador:** cada X minutos sobre correos entrantes no procesados.
1. **Filtro:** quedarse con notificaciones de procuradores + contestaciones a
   correos del CRM. Lo demás (ruido, remitente desconocido) **no se borra**: se
   enruta a la vista **"Descartados"** que revisa la secretaria (§6, §16.11).
2. **Anti-duplicado (antes de tocar nada):** comprobar si el correo ya está
   relacionado (`GET /api/mail/element_registries`). Los enviados desde el
   expediente ya constan → no se duplican. El mismo correo en los 4 buzones de los
   abogados (procesal@ reenvía a ana.velastegui@, sergio.pinol@,
   nikolai.tyukhay@, paola.barreto@) se trata **una sola vez**.
3. **Entender (LLM Mistral):** de asunto + cuerpo (+ contenido de adjuntos)
   extrae señales y un veredicto (¿trae actuación/documento a archivar?).
4. **Buscar expediente** (ver §5).
5. **Red de seguridad** (ver §6): nada se escribe sin confirmación humana.
6. **Ejecutar lo confirmado** (ver §7): relacionar correo + adjuntar ficheros.
7. **Marcar y registrar:** correo marcado como procesado + apunte en log de
   auditoría (correo, expediente, carpeta, confianza, **quién confirmó**, cuándo).

## 5. Emparejamiento correo → expediente

- **Llave principal = "Su ref"** que el procurador rotula como *Su ref / S/R / Su
  Rfa / Referencia*. **ES el identificador del expediente en el CRM =
  `num_expediente / serie_expediente`**, donde `serie` = **año de creación** del
  expediente. Ej. `13/2026` → num_expediente=13, serie=2026. Match casi exacto:
  buscar el expediente con ese num+serie. (NO confundir con "Mi ref / M/R" del
  procurador.)
- **Multi-señal de respaldo:** contrario, cliente, `juzgado`, `num_asunto`
  (nº autos), `tipo_procedimiento`. Normalizar la referencia (frágil a
  espacios/acentos — ver `[SIGUIENTE-DEDUP-GUARD-ROBUSTO]` en `PLAN.md`).
- **Contestaciones:** por el **hilo** del correo saliente ya relacionado.
- **Sin match:** a bandeja "sin expediente" (nunca inventar).

Campos del expediente (catálogo real `/api/view/config/expedientes_judiciales/fields`):
`num_expediente`, `serie_expediente`, `referencia_procurador`, `juzgado`,
`num_asunto` (autos), `NIG`, `tipo_procedimiento`, `posicion_procesal`, `cuantia`,
`profesional_asignado`, `tags`. Cliente y contrario son **registros relacionados**,
no campos escalares.

## 6. Red de seguridad (bandeja de revisión)

UI nueva en la app **Streamlit** de FeesDefender ("Bandeja de correos"), con
**login ligero por persona** (alimenta el "quién confirmó" y permite filtrar).
El robot **no escribe en el CRM** hasta que una persona confirma.

Cabecera de triaje: recuentos (alta / dudoso / sin expediente), filtros (por
procurador, buscador), opción de **confirmar en bloque** los de confianza alta
(decidir si se activa de inicio; empezar revisando todo).

**Tres estados de tarjeta:**
- 🟢 **Confianza alta:** match exacto por Su ref. Muestra los datos del expediente
  (nº/serie, contrario, juzgado, nº autos, procedimiento) con **check verde por
  cada dato que coincide con el correo** + recuento ("5 datos coinciden"). El
  expediente se puede **cambiar** (buscador colapsado, enlace "cambiar"). Carpeta
  en desplegable. Adjuntos con casilla "Subir". Cuerpo del correo compacto
  (1 línea + "ver completo"). Botones: Confirmar / Descartar.
- 🟡 **Dudoso:** match por señal débil (p. ej. hilo de una contestación). Buscador
  de expediente **abierto** de inicio, **sin checks verdes**, aviso "verifica".
  Botón "Guardar y confirmar".
- 🔴 **Sin expediente:** no hay match. Bloque "**datos detectados en el correo**"
  (Su ref, contrario, juzgado, autos, tipo) para ayudar a localizarlo. Buscador
  vacío (judicial / extrajudicial / clientes). Carpeta y "Asignar y confirmar"
  **deshabilitados** hasta elegir expediente.

**Vista de "Descartados" (revisión de la secretaria) — APROBADO 2026-06-12:**
El filtro del paso 1 (§4) y la detección de ruido **NO hacen hard-drop**. Todo
correo que el robot descarte (clasificado como ruido, remitente no reconocido, o
sin actuación a archivar) **no desaparece**: se enruta a una **vista secundaria
"Descartados"** —pestaña aparte de la bandeja principal, colapsada y de baja
prioridad— para que **la secretaria la revise** y rescate cualquier falso
descarte (botón "Recuperar → enviar a bandeja", que reabre el triaje normal de
3 tarjetas sobre ese correo). Cada fila muestra remitente, asunto, fecha y
**motivo del descarte** (p. ej. "marcado ruido por LLM", "remitente no es
procurador conocido", "sin Su ref ni hilo"). El objetivo es que **ningún correo
se pierda sin posibilidad de auditarlo**, sin saturar la bandeja principal con
ruido.

*Motivo (s39, 2026-06-12):* al medir F1 sobre correos reales se detectó un
**falso positivo de `es_ruido`** que habría descartado silenciosamente una
actuación real. Se mitigó haciendo `es_ruido` **advisory** en el matching (no
bloquea la búsqueda si hay Su ref resoluble; viaja como señal `es_ruido_advisory`),
pero el filtro del paso 1 sigue siendo una decisión automática con poder de
descarte → de ahí esta vista de seguridad. Regla: el descarte automático es
**reversible y auditable**, nunca definitivo.

**Buscador-selector (combobox) de expediente:** prerrelleno con el match; al
escribir busca en el CRM por referencia/contrario/cliente/autos y lista
candidatos (nº/serie · contrario · juzgado · autos). Al cambiar de expediente, se
refrescan los datos y las carpetas. Reutiliza/amplía la búsqueda por referencia ya
existente en FeesDefender.

**Enlace "abrir en el CRM":** navegación normal → abre el expediente en la sesión
del CRM de quien pincha (su propio login en el navegador), no comparte sesión.

## 7. Escritura en el CRM (contrato)

El módulo de correo del CRM es **Roundcube**, servido por un microservicio aparte
**`nest-mail-commons-pro.sudespacho.biz`** (OpenAPI en `/api-json`), distinto del
`api-crm-commons-pro`.

- **Relacionar correo ↔ expediente:** modelo `MailRelationInput =
  { element, elementId, mail }` (element=`expedientes_judiciales` /
  extrajudiciales / clientes; elementId=ID expediente; mail=identificador del
  correo). Se setea `mailRelations: [MailRelationInput]` vía **`PUT /api/mail/{id}`**
  (body tipo `MailSend`/`MailUpdate`).
- **Adjuntar al gestor documental:** `attachmentGdocu: [{ identifier }]` en el
  mismo PUT, o subida directa. Subida de fichero por **URL prefirmada**:
  `GET /api/documents/presigned-upload-attachment-url` (nest-mail) o
  `GET /api/documents/presigned_urls/{service}/upload/{n}` (api-crm) → PUT bytes a
  S3 → registrar. Alternativa de bajo nivel: `POST /api/documents` /
  `POST /api/documents/single-document/import` (api-crm).
- **Atribución (APROBADO):** una sola API Key, dada de alta como usuario
  **"Robot intake / Archivo automático"**. El "quién confirmó" vive en nuestro
  log. Si hay campo de nota, escribir "confirmado por X". NO una clave por persona.
- **PENDIENTE confirmar al construir:** ¿`nest-mail` acepta `x-api-key` o exige
  el JWT de sesión web (`api-auth-commons-pro/api/authenticate/refresh`)? Si exige
  JWT, resolver el flujo de auth para ese microservicio.

## 8. Carpetas del gestor documental

El desplegable es **espejo de las carpetas de ESE expediente**. Se rellena en
vivo con las carpetas **en uso** (`GET /api/element_registries/gdocu?...associated`)
+ el árbol estándar (`CRM_TREE` en `config.py`). Al cambiar de expediente, se
recarga. **Limitación conocida:** la API no expone carpetas **vacías**
(`/api/folders/gdocu/{parent}` = dead end). Mapa de IDs globales en
`CARPETA_ID_TO_PATH` (1=General, 306=Civil, 307=Demanda, 308=Oposición,
380=Preliminares/Demanda; ampliable). Por defecto **General** si nada claro.

## 9. Renombrado de adjuntos

Aplica a los **adjuntos que van al gestor documental** (el correo en sí se
*relaciona* en Roundcube, no se renombra como fichero).

**Convenciones** (separador `" - "`; extensión REAL y BLOQUEADA — el usuario solo
edita el nombre):
- **Actuaciones procesales:** `<fecha ISO> - <tipo> - <contenido>.<ext>`
  - `2026-06-12 - Auto - nombramiento administrador.pdf`
  - `2026-06-10 - Just Escr - contestacion demanda.pdf`
- **Documentos de prueba (demanda/contestación), numerados:**
  `D <NN> - <fecha ISO> - <contenido>.<ext>` (el número manda para ordenar)
  - `D 01 - 2026-01-02 - contrato arrendamiento.pdf`
  - `D 02 - 2026-02-15 - burofax reclamacion.pdf`

**Vocabulario de tipos + abreviaturas (visor con poco espacio):**

| Tipo | Abrev. | Tipo | Abrev. |
|---|---|---|---|
| Auto | `Auto` | Recurso | `Rec` |
| Sentencia | `Sent` | Acta | `Acta` |
| Decreto | `Decr` | Tasación de costas | `Tasac` |
| Diligencia de ordenación | `DiOr` | Testimonio | `Test` |
| Providencia | `Prov` | Notificación | `Notif` |
| Cédula | `Ced` | Grabación | `Grab` |
| Oficio | `Ofi` | Otros | `Otros` |
| Mandamiento | `Mand` | Escrito (nuestro) | `Escr` |
| Justificante de presentación | `Just Escr` | Escrito parte contraria | `Escr-Crio` |

**Qué lee Mistral para nombrar:** PRIMERO el **contenido del adjunto** (texto
extraído; OCR Docling si está escaneado) → el nombre describe lo de dentro y no
hace falta abrir el fichero; SEGUNDO el cuerpo del correo como contexto; el
filename original solo como pista débil. Devuelve `{ fecha, tipo, descripcion,
confianza }` (+ nº de documento si es probatorio). **El código ensambla el
nombre** (determinista).

**Normalización de la descripción:**
1. Quitar artículos, preposiciones y conjunciones (a, de, del, la, el, los, las,
   un, una, en, con, por, para, y, e, o, u, que, al…).
2. **Quitar tildes de vocales, conservar la ñ** (no convertir "año"→"ano").
3. Conservar nombres propios, números y referencias.
4. Acotar ~40 car. Saneado Windows-safe (reusa `_sanitize`).

Ej.: "contestación a la demanda" → `contestacion demanda`; "nombramiento de
administrador" → `nombramiento administrador`.

**Reglas:** sin fecha → fecha de recepción + revisión; sin tipo → `Otros` +
revisión; colisión en misma carpeta → sufijo `__2`; logotipo del procurador →
casilla "Subir" **desmarcada** por defecto; el CRM conserva `nombreoriginal` y el
nuevo va en `documentName`/`nombrefinal` (cadena de custodia).

## 10. Aprendizaje y memoria del renombrado (FeesDefender conserva la experiencia)

**Requisito de Nikolai:** FeesDefender debe **quedarse con la experiencia de
renombrado** y mejorarla con el uso.

- Cada **corrección humana** en la bandeja (cambiar nombre, tipo, carpeta o
  expediente) se persiste como **señal de aprendizaje** en un store local de
  FeesDefender, extendiendo el patrón del organizador
  (`data/_aprendizaje/correcciones.jsonl`). Sugerido: `correcciones_intake.jsonl`
  (o reusar el mismo store con un campo `fuente: "procurador_intake"`).
- Cada señal guarda: remitente/procurador, tipo de actuación detectado, texto
  base, propuesta del robot y **corrección del humano** (nombre/tipo/carpeta).
- En la siguiente ejecución, esas correcciones alimentan el prompt de Mistral
  como **few-shot** (ejemplos cercanos), de forma que el robot **acierta cada vez
  más** en patrones recurrentes (un procurador concreto, un tipo de resolución,
  una carpeta habitual). No memoriza correos sueltos: aprende **patrones**.
- El store es **local** (señales/metadatos): coherente con el control de datos.
- Métricas de calidad (aciertos vs correcciones) en `data/_aprendizaje/`, como ya
  hace el organizador, para medir mejora y decidir cuándo auto-aprobar confianza
  alta.

## 11. Grabaciones (enlaces de descarga)

Las grabaciones de vistas llegan como **enlace** en el cuerpo
(`we.tl` / `wetransfer.com`; prever también Drive/Dropbox/Swisstransfer).
- Detectar el enlace → **descargar cuanto antes** (los WeTransfer **caducan**
  ~7 días → prioridad).
- Subir al gestor documental vía presigned URL como `… - Grab - …`. Si el vídeo
  excede el límite del CRM, guardar en carpeta Drive + enlazar.
- **Fallback:** si la descarga falla/caduca/host desconocido → la tarjeta lo marca
  como "descarga manual" con el enlace. (WeTransfer puede cambiar/bloquear la
  descarga automática; construir defensivo.)

## 12. Motor LLM

- **Mistral AI (Francia):** datos en UE, opción **retención cero**; modelos
  pequeños (Ministral 8B / Mistral Small) baratos y sobrados para extraer
  señales + clasificar + nombrar. Coste esperado: céntimos-pocos €/mes.
- **Conector LLM intercambiable** (capa fina): cambiar modelo/proveedor = 1 línea.
- Alternativa de soberanía UE: **OVHcloud AI Endpoints** (modelos abiertos en
  infra francesa).
- Al construir: confirmar precio/nombre de modelo vigente y **activar retención
  cero**.

## 13. Credenciales / conexión

- Sudespacho: `SUDESPACHO_BASE_URL=https://api-crm-commons-pro.sudespacho.biz`,
  `SUDESPACHO_API_KEY` (variable de entorno de **usuario** de Windows, NO en
  `.env`), cabecera **`x-api-key`** (NO `Authorization`, reservado a JWT web).
  La lee `core/sync_sudespacho.py` en runtime; **nunca pasa por el LLM/chat**.
- Gmail: tokens en `C:\Users\tnm33\.gmail-mcp\` (los del servidor `gmail-ro`).
- Mistral / nest-mail: secretos en entorno, nunca en repo.

## 14. Pegas técnicas detectadas (a resolver al construir)

- `get_expediente(444)` con `EXPEDIENTE_DEFAULT_PROPERTIES` → **HTTP 500 "Array to
  string conversion"**: alguna propiedad array rompe; elegir properties con
  cuidado / excluir la ofensora.
- `list_gdocu_folders(444)` devolvió **vacío**: revisar params (element/member)
  para listar las carpetas en uso de un expediente.
- **Auth de `nest-mail`** (relate/adjuntar): confirmar si `x-api-key` basta o
  exige JWT de sesión.
- **WeTransfer:** descarga automática frágil (caducidad + posibles cambios).

## 15. Fases de construcción (incremental)

- **F1 — Matcher (read-only):** dado un correo, Mistral + búsqueda por referencia
  → expediente + confianza + carpeta sugerida + nombres propuestos. Sin escribir
  nada. Validar contra correos reales (vía `gmail-ro` para el set de prueba).
- **F2 — Bandeja (Streamlit): ✅ COMPLETA** (2026-06-12, branch
  `feat/intake-procuradores-f2-ui`). Las 3 tarjetas 🟢/🟡/🔴 + login por persona
  (`set_actor`) + combobox de reasignación (REST) + vista Descartados con Recuperar,
  orquestando el core. CLI thin `scripts/intake_procuradores.py` sobre `fetch_and_run`.
  `search_expedientes` migrado a REST (autocomplete legacy vacío en CRM real, `DEAD_ENDS.md`).
  Confirmaciones simuladas (dry-run). **⚠️ Requisito duro de diseño (ver §18.9):**
  el log de auditoría debe capturar **desde F2** la terna *propuesta-del-robot vs.
  acción-confirmada vs. quién-y-cuándo* por cada ítem. Sin ese registro el check 2
  (§18) no tiene contra qué comparar. Diseñarlo dentro del modelo de datos de la
  bandeja, **no atornillarlo después**.
- **F3 — Escritura en el CRM:** resolver auth de nest-mail; relate + adjuntar en
  un expediente de prueba; verificar marcado en Roundcube. Activar tras validar.
  Mismo requisito duro de traza que F2.
- **F4 — Renombrado + OCR + aprendizaje:** contenido del adjunto → nombre;
  store de correcciones + few-shot.
- **F5 — Grabaciones:** descarga de enlaces + fallback manual.
- **F6 — Control de calidad del archivo (check 2):** la capa de auditoría por
  excepción descrita en §18 (auto-chequeo determinista + cola de Paola + resumen
  semanal a Nikolai). **Depende de F2/F3** (consume la terna de traza). Diseño
  cerrado con Nikolai el 2026-06-12.

## 16. Decisiones cerradas (2026-06-12)

1. Alcance: notificaciones de procuradores **+** contestaciones a correos del CRM.
2. Llave = Su ref (= num/serie, serie=año); multi-señal de respaldo.
3. Red de seguridad con confirmación humana **antes** de escribir; 3 tarjetas.
4. Login por persona en Streamlit; atribución CRM = usuario API "Robot intake".
5. Carpeta = espejo del expediente (desplegable editable, recarga al cambiar).
6. Renombrado: convenciones, abreviaturas, normalización (sin stopwords, sin
   tildes salvo ñ); Mistral lee el **contenido**; extensión bloqueada.
7. Documentos de prueba: `D <NN> - fecha - contenido` (número delante).
8. FeesDefender conserva la experiencia de renombrado (aprendizaje persistente).
9. Motor LLM = Mistral (UE), conector intercambiable.
10. RGPD: excepción acotada SOLO a este flujo.
11. **Descarte reversible y auditable (2026-06-12):** el filtro/ruido no hace
    hard-drop; lo descartado va a una **vista "Descartados"** que revisa la
    secretaria, con "Recuperar → bandeja". Ningún correo se pierde sin auditar
    (ver §6). `es_ruido` es advisory, no veredicto.

## 17. Pendientes / a decidir

- ¿Confirmar en bloque los de confianza alta de inicio, o revisar todo al principio?
  (El descarte automático ya está resuelto: vista "Descartados" revisable por la
  secretaria — §6 y §16.11.)
- ¿Auth de nest-mail (x-api-key vs JWT)?
- Límite de tamaño del CRM para grabaciones (¿Drive + enlace?).
- Catálogo de carpetas: ir cerrando `CARPETA_ID_TO_PATH` con descubrimiento.

---

## 18. Control de calidad del archivo (check 2)

> Diseño cerrado con Nikolai el 2026-06-12. Es la **fase F6** (§15), dependiente
> de F2/F3. Coherente con *El Auditor*: solo lectura, reporta no conformidades a
> Nikolai, traza desde el día uno. Extiende el log de auditoría (§4 paso 7) y el
> store de aprendizaje (§10).

### 18.1 Modelo: control por excepción en tres capas

El archivo NO se revisa dos veces entero. El tiempo de empleados se concentra
donde hay riesgo:

1. **Capa 1 — Ana Velástegui (secretaria) confirma todo.** Es la bandeja de
   revisión (F2). 100% humano. Sin cambios.
2. **Capa 2 — auto-chequeo del programa.** Repasa lo archivado sin consumir tiempo
   humano y aparta lo sospechoso.
3. **Capa 3 — Paola Barreto adjudica solo lo apartado** (a diario) + una muestra
   aleatoria. Nikolai lee un resumen semanal de solo lectura.

Beneficio lateral: cada corrección humana es señal de aprendizaje de primera
calidad (§10), y la tasa de error medida es lo que autoriza, más adelante, a
auto-aprobar la confianza alta sin confirmación de Ana (menos tiempo de empleados).

### 18.2 Qué vigila el auto-chequeo (capa 2)

Prioridad a lo determinista e independiente del criterio humano (sin LLM), que es
donde está el valor real:

- **Invariante de referencia:** *Su ref* extraída del correo ≠ num/serie del
  expediente donde se relacionó → candidato a **expediente equivocado** (error más
  grave y difícil de ver a ojo).
- **Coherencia de campos:** juzgado / nº autos del correo que no casan con los
  campos del expediente.
- **Cobertura:** correos de procurador en los buzones sin apunte de "procesado"
  → hueco. Independiente de la calidad del archivo; es el riesgo de
  responsabilidad puro.
- **Carpeta por defecto:** documento caído en "General" (fallback) siendo una
  actuación clasificable.
- **Adjuntos:** nº de adjuntos del correo ≠ subidos, descontando logos/firmas.

El LLM se reserva para lo semántico (¿el nombre/carpeta encaja con el contenido?)
y solo sobre el subconjunto ya marcado o muestreado — una segunda pasada de LLM
"que relee" añade poco porque comparte el sesgo de la primera.

### 18.3 Cola de Paola (diaria) — pestaña "Control de archivo" en Streamlit

NO un informe: Paola corrige, así que necesita una pestaña operativa donde ya
trabaja. Cola corta, priorizada:

1. Rupturas de invariante (expediente equivocado).
2. Huecos de cobertura.
3. **Documentos importantes / con plazo → revisión del 100%** (ver §18.4).
4. Divergencias: Ana sobrescribió un match de confianza alta, o confirmó un
   "dudoso / sin expediente".
5. Muestra aleatoria **~10%** del resto (lo que parece correcto) — para medir la
   tasa real de error, no para cazar fallos concretos. Bajable cuando la tasa se
   confirme baja.

Cada ítem se muestra lado a lado: **correo → propuesta del robot → acción de Ana
→ invariante roto**. Paola da el visto bueno o corrige en el sitio (expediente /
carpeta / nombre). Cada corrección alimenta el store de aprendizaje (§10) y cuenta
para la métrica. Si un día la cola está limpia, son dos minutos.

### 18.4 Documentos importantes (revisión 100%)

Sentencias, autos, emplazamientos, traslados **y cualquier correo donde se
mencione o se deduzca un plazo, sea del tipo que sea** (una diligencia de
ordenación o una notificación normal también abren plazo). El programa debe pecar
de marcar de más: un falso positivo cuesta segundos a Paola; un plazo que se
escapa cuesta un caso.

### 18.5 Tres velocidades de revisión

La regla de fondo: **el hueco de revisión nunca puede ser mayor que el margen del
plazo más corto** que pueda venir en un correo.

- **Continua:** "¿hay un correo de procurador sin procesar?" — lo más peligroso,
  no espera a la noche.
- **Mismo día:** lo que trae plazo (§18.4) — vía rápida + aviso el mismo día en que
  se archiva. Reacción en horas, no en un día.
- **Día hábil siguiente:** todo lo demás — cola matinal de Paola. Hueco máximo
  ~1 día laborable, suficiente para lo que no tiene plazo.

### 18.6 Resumen semanal (Nikolai) — solo lectura

Tarea programada → llega a `procesal@tyukhay.legal` (o donde se decida). Nikolai
supervisa, no opera. Contiene:

- Tasa de error de la semana (ítems corregidos por Paola / total archivado) y
  tendencia.
- Nº de excepciones por tipo, y cuántas siguen sin resolver o son de alta
  gravedad.
- Huecos de cobertura no cerrados (correos que nadie procesó).
- Quién archivó / quién revisó cada día y si algún día quedó sin revisar.
- Veredicto en una línea: ¿el archivo fue de fiar este periodo, sí/no?

Cuando la tasa de error baje y se estabilice → habilita auto-aprobar la confianza
alta sin confirmación de Ana.

### 18.7 Suplencias / ausencias

- **Dos papeles que cubrir, nunca cero de ninguno:** archivador (Ana) y revisor
  (Paola).
- **Independencia:** quien archiva un lote no lo revisa. Si Ana está fuera y
  archiva Paola, esos días la revisión pasa a Nikolai o Sergio.
- **Sin reasignación anticipada** (calendario de ausencias descartado por ahora):
  el trabajo no procesado se queda en la cola y, pasado su plazo sin que nadie lo
  toque, **escala solo hacia Nikolai**. El aviso por antigüedad sustituye al
  calendario — reacciona en vez de anticipar, pero la red de seguridad se mantiene.

### 18.8 Trazabilidad ("quién hace qué")

- **Login propio por persona en Streamlit. NADA de cuentas compartidas** (o el
  rastro se rompe). Cada acción queda sellada: "archivado por X / revisado por Y,
  fecha y hora".
- Las **suplencias se trazan solas:** el login recoge quién hizo, no quién debería
  — si cubre Paola o Sergio, queda su nombre sin que nadie lo declare.
- **Regla de independencia automática:** el programa compara el sello del
  archivador con el del revisor y no deja que coincidan en el mismo ítem.
- **Las omisiones (lo que nadie hizo) NO las ve el login** → las caza la cola por
  antigüedad + escalado a Nikolai.
- Sin calendario, el resumen semanal dice quién revisó y si algún día quedó sin
  revisar; **el "porqué" del hueco lo interpreta Nikolai** al leerlo.

### 18.9 Requisito duro de diseño (condiciona F2/F3)

La traza debe capturar, **desde F2/F3**, la terna **propuesta-del-robot vs.
acción-confirmada vs. quién-y-cuándo**. Sin ese registro el check 2 no tiene
contra qué comparar. **Diseñar dentro de F2/F3, no atornillar después.** Es el
punto que condiciona el modelo de datos de la bandeja antes de construirla.

### 18.10 Decisiones cerradas (2026-06-12)

1. Control por excepción en tres capas (Ana 100% → auto-chequeo → Paola
   excepciones + muestra → Nikolai resumen).
2. Auto-chequeo prioriza invariantes deterministas + cobertura; LLM solo para lo
   semántico del subconjunto marcado.
3. Cola de Paola diaria en Streamlit, priorizada; muestra aleatoria 10% (ajustable).
4. Importantes = sentencias/autos/emplazamientos/traslados **+ todo lo que tenga
   plazo**; revisión 100%; sobre-marcar mejor que omitir.
5. Tres velocidades: continua (no procesado) / mismo día (plazo) / día siguiente
   (resto). Hueco < margen del plazo más corto.
6. Resumen semanal a Nikolai, solo lectura, estilo *El Auditor*.
7. Suplencias: nunca cero revisores; archivador ≠ revisor del mismo lote; sin
   reasignación anticipada, escalado automático a Nikolai por antigüedad de cola.
8. Trazabilidad por login propio por persona; sin cuentas compartidas; omisiones
   por cola, no por login.
9. **Calendario de ausencias = MEJORA FUTURA** (solo si los avisos llegan tarde o
   demasiado a menudo durante ausencias).
10. Requisito duro: traza propuesta-vs-acción-vs-quién desde F2/F3.

### 18.11 Pendientes / a decidir al construir

- Plazos concretos de la cola antes de escalar (definir las X horas/días por tipo).
- Mecanismo de aviso del "mismo día" para plazos (¿correo? ¿notificación en la
  bandeja?).
- Tamaño definitivo de la muestra aleatoria (default 10%).
- Cadencia del resumen (default semanal; Nikolai puede pasarlo a diario).
- Lista de "tipos con plazo" + detección de plazo explícito en el cuerpo del LLM.
